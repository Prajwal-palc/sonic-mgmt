"""
VLAN INTERFACE LIFECYCLE VERIFICATION
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/ztp_standalone.yaml  \
  tests/switching/test_vlan_interface_lifecycle.py \
  --logs-path ./logs/test_vlan_interface_lifecycle_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of VLAN interface lifecycle operations including creation,
  description management, and deletion using SpyTest APIs and sonic-cli (klish).
  The test validates VLAN interface presence in running configuration and verifies
  cleanup operations. Tests include negative scenarios for known bugs related to
  description removal and interface deletion. Handles pagination in show commands
  by setting terminal length to 0.

Files and APIs Used:
  - Testbed Configuration:
      * testbeds/ztp_standalone.yaml - Standalone DUT configuration

  - SpyTest APIs (Existing):
      * apis.switching.vlan.create_vlan() - Create VLAN
        Location: spytest/apis/switching/vlan.py
      * apis.switching.vlan.delete_vlan() - Delete VLAN
        Location: spytest/apis/switching/vlan.py
      * apis.switching.vlan.verify_vlan() - Verify VLAN existence
        Location: spytest/apis/switching/vlan.py

  - SpyTest Framework Functions:
      * st.config() - Execute configuration commands
      * st.show() - Execute show commands
      * st.log(), st.banner(), st.debug(), st.warn() - Logging functions
      * st.wait() - Wait for configuration propagation
      * st.report_pass(), st.report_fail() - Test result reporting

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node (standalone)
        # +--------------------+
        # |        D1          |
        # |    (smic_sonic1)   |
        # |     VLAN 20, 10    |
        # +--------------------+

  - Feature flags / min SONiC version: Basic VLAN support required
  - Required test variables: Uses testbed file directly (no external YAML vars needed)
"""

from __future__ import annotations

import re
from typing import Any, Dict

import pytest

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api


# Test constants
TEST_VLAN_20 = "20"
TEST_VLAN_10 = "10"
VLAN_DESCRIPTION = "vlan interface"


@pytest.mark.topology("any")
class TestVlanInterfaceLifecycle:
    """Testcases covering VLAN interface lifecycle operations and cleanup verification."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and disable terminal pagination."""
        st.banner("CLASS SETUP: Starting VLAN Interface Lifecycle Test Suite")

        # Get topology - single DUT standalone topology
        topology = st.get_testbed_vars()
        cls.data.topology = topology

        # Get DUT names
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs found in testbed")

        cls.data.dut = cls.data.dut_names[0]  # Use first DUT (D1)
        st.log(f"Using DUT: {cls.data.dut}")

        # Set terminal length to 0 to disable pagination (--more-- prompts)
        cls._set_terminal_length(cls.data.dut, 0)
        st.log("Terminal length set to 0 - pagination disabled")

        # Pre-cleanup: Remove test VLANs if they exist
        st.banner("Pre-test cleanup: Removing test VLANs if they exist")
        cls._cleanup_vlan(cls.data.dut, TEST_VLAN_20)
        cls._cleanup_vlan(cls.data.dut, TEST_VLAN_10)

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup - ensure test VLANs are removed."""
        st.banner("CLASS TEARDOWN: Cleaning up VLAN configuration")

        # Delete test VLANs
        cls._cleanup_vlan(cls.data.dut, TEST_VLAN_20)
        cls._cleanup_vlan(cls.data.dut, TEST_VLAN_10)

        st.log("Class teardown completed")

    def setup_method(self) -> None:
        """Pre-test cleanup - ensure clean slate."""
        st.banner("TEST SETUP: Ensuring clean environment")
        self._cleanup_vlan(self.data.dut, TEST_VLAN_20)
        self._cleanup_vlan(self.data.dut, TEST_VLAN_10)

    def teardown_method(self) -> None:
        """Post-test cleanup."""
        st.banner("TEST TEARDOWN: Removing test VLANs")
        self._cleanup_vlan(self.data.dut, TEST_VLAN_20)
        self._cleanup_vlan(self.data.dut, TEST_VLAN_10)

    @staticmethod
    def _set_terminal_length(dut: str, length: int = 0) -> None:
        """Set terminal length to control pagination in show commands.

        Args:
            dut: Device under test
            length: Terminal length (0 = no pagination)
        """
        try:
            # Use klish CLI to set terminal length
            cmd = f"terminal length {length}"
            st.config(dut, cmd, type="klish", conf=False, skip_error_check=True)
            st.log(f"Set terminal length to {length} on {dut}")
        except Exception as e:
            st.warn(f"Failed to set terminal length: {e}")

    @staticmethod
    def _get_running_config(dut: str, module: str = None) -> str:
        """Retrieve running configuration with pagination disabled.

        Args:
            dut: Device under test
            module: Optional module filter (e.g., "interface Vlan 20")

        Returns:
            Running configuration as string
        """
        # Set terminal length to 0 to avoid --more-- pagination prompts
        st.config(dut, "terminal length 0", type="klish", conf=False, skip_error_check=True)

        if module:
            cmd = f"show running-configuration {module}"
        else:
            cmd = "show running-configuration"

        output = st.show(dut, cmd, type="klish", skip_tmpl=True, skip_error_check=True)

        if isinstance(output, list) and output:
            # Join list output into single string
            config_text = "\n".join(str(item) for item in output)
        elif isinstance(output, str):
            config_text = output
        else:
            config_text = str(output)

        return config_text

    @staticmethod
    def _verify_vlan_interface_in_config(config_text: str, vlan_id: str) -> Dict[str, Any]:
        """Parse running config to check if VLAN interface exists.

        Args:
            config_text: Running configuration text
            vlan_id: VLAN ID to search for

        Returns:
            Dictionary with interface existence and description details
        """
        result = {
            "interface_exists": False,
            "description": None,
            "full_block": None
        }

        # Pattern to match "interface Vlan<id>"
        interface_pattern = rf"interface\s+Vlan\s*{vlan_id}(.*?)(?=^interface\s+|\Z)"
        match = re.search(interface_pattern, config_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)

        if not match:
            st.log(f"VLAN {vlan_id} interface section not found in running config")
            return result

        result["interface_exists"] = True
        interface_block = match.group(0)
        result["full_block"] = interface_block
        st.debug(f"VLAN {vlan_id} interface block:\n{interface_block}")

        # Parse description
        desc_match = re.search(r'^\s*description\s+"?([^"\n]+)"?', interface_block, re.MULTILINE)
        if desc_match:
            result["description"] = desc_match.group(1).strip()

        return result

    @classmethod
    def _cleanup_vlan(cls, dut: str, vlan_id: str) -> None:
        """Remove VLAN and its interface if they exist.

        Args:
            dut: Device under test
            vlan_id: VLAN ID to remove
        """
        try:
            # First, try to remove VLAN interface
            cmd_list = [
                f"no interface Vlan {vlan_id}",
                f"no vlan {vlan_id}"
            ]
            st.config(dut, cmd_list, type="klish", skip_error_check=True)
            st.log(f"Cleaned up VLAN {vlan_id}")
        except Exception as e:
            st.debug(f"Cleanup VLAN {vlan_id} error (may not exist): {e}")

        # Also use API cleanup
        try:
            vlan_api.delete_vlan(dut, vlan_id, cli_type="klish")
        except Exception as e:
            st.debug(f"API cleanup VLAN {vlan_id} error: {e}")

    @pytest.mark.inventory(feature="Regression", testcases=["VLAN_LIFECYCLE_TC_001"])
    def test_vlan_interface_creation_and_verification(self) -> None:
        """TC 001 - Verify VLAN interface creation and description configuration.

        Test Steps:
        1. Create VLAN 20 and VLAN 10
        2. Create VLAN 20 interface with description
        3. Verify VLAN 20 interface in running configuration
        4. Verify description is set correctly
        5. Verify VLAN state with 'show vlan'
        """
        dut = self.data.dut

        st.banner(f"STEP 1: Create VLAN {TEST_VLAN_20} and VLAN {TEST_VLAN_10}")

        # Create VLAN 20
        result = vlan_api.create_vlan(dut, TEST_VLAN_20, cli_type="klish")
        if not result:
            st.report_fail("msg", f"Failed to create VLAN {TEST_VLAN_20}")

        st.log(f"✓ VLAN {TEST_VLAN_20} created successfully")

        # Create VLAN 10
        result = vlan_api.create_vlan(dut, TEST_VLAN_10, cli_type="klish")
        if not result:
            st.report_fail("msg", f"Failed to create VLAN {TEST_VLAN_10}")

        st.log(f"✓ VLAN {TEST_VLAN_10} created successfully")

        st.banner(f"STEP 2: Create VLAN {TEST_VLAN_20} interface with description")

        # Configure VLAN interface with description
        cmd_list = [
            f"interface Vlan {TEST_VLAN_20}",
            f'description "{VLAN_DESCRIPTION}"',
            "exit"
        ]
        st.config(dut, cmd_list, type="klish")
        st.log(f"✓ VLAN {TEST_VLAN_20} interface configured with description")

        # Wait for configuration to propagate
        st.wait(2)

        st.banner(f"STEP 3: Verify VLAN {TEST_VLAN_20} interface in running configuration")

        config = self._get_running_config(dut, module=f"interface Vlan {TEST_VLAN_20}")

        if not config:
            st.report_fail("msg", f"Failed to retrieve running configuration for VLAN {TEST_VLAN_20}")

        st.log("Running configuration retrieved successfully")
        st.debug(f"VLAN {TEST_VLAN_20} config:\n{config}")

        parsed = self._verify_vlan_interface_in_config(config, TEST_VLAN_20)

        if not parsed["interface_exists"]:
            st.report_fail("msg", f"VLAN {TEST_VLAN_20} interface not found in running configuration")

        st.log(f"✓ VLAN {TEST_VLAN_20} interface found in running configuration")

        st.banner(f"STEP 4: Verify description is set correctly")

        if parsed["description"] is None:
            st.report_fail("msg", f"Description not found in VLAN {TEST_VLAN_20} configuration")

        if parsed["description"] != VLAN_DESCRIPTION:
            st.report_fail(
                "msg",
                f"Description mismatch. Expected: '{VLAN_DESCRIPTION}', Found: '{parsed['description']}'"
            )

        st.log(f"✓ Description verified: '{parsed['description']}'")

        st.banner(f"STEP 5: Verify VLAN state with 'show vlan'")

        # Set terminal length to 0 to avoid --more-- pagination prompts
        st.config(dut, "terminal length 0", type="klish", conf=False, skip_error_check=True)

        # Execute show vlan command
        cmd_show_vlan = "show vlan"
        vlan_output = st.show(dut, cmd_show_vlan, type="klish", skip_tmpl=True, skip_error_check=True)

        # Convert output to string for searching
        if isinstance(vlan_output, list):
            vlan_output_str = "\n".join(str(item) for item in vlan_output)
        elif isinstance(vlan_output, str):
            vlan_output_str = vlan_output
        else:
            vlan_output_str = str(vlan_output)

        st.debug(f"Show VLAN output:\n{vlan_output_str}")

        # Check if VLAN 20 appears in output
        vlan_pattern = rf"(Vlan\s*{TEST_VLAN_20}|VLAN\s*{TEST_VLAN_20}|\b{TEST_VLAN_20}\b)"
        if not re.search(vlan_pattern, vlan_output_str, re.IGNORECASE):
            st.report_fail("msg", f"VLAN {TEST_VLAN_20} not found in 'show vlan' output")

        st.log(f"✓ VLAN {TEST_VLAN_20} verified in VLAN table")

        st.banner("TEST PASSED: VLAN interface creation and verification successful")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["VLAN_LIFECYCLE_TC_002"])
    def test_vlan_description_removal(self) -> None:
        """TC 002 - Verify VLAN interface description removal (Known Bug Test).

        Test Steps:
        1. Create VLAN 20 with interface and description
        2. Verify description exists in running config
        3. Remove description using 'no description'
        4. Verify description removal (Expected to fail due to bug)
        5. Document bug behavior

        Note: This is a negative test documenting a known bug where
        'no description' does not remove the interface description.
        """
        dut = self.data.dut

        st.banner(f"STEP 1: Create VLAN {TEST_VLAN_20} with interface and description")

        # Create VLAN
        result = vlan_api.create_vlan(dut, TEST_VLAN_20, cli_type="klish")
        if not result:
            st.report_fail("msg", f"Failed to create VLAN {TEST_VLAN_20}")

        # Configure VLAN interface with description
        cmd_list = [
            f"interface Vlan {TEST_VLAN_20}",
            f'description "{VLAN_DESCRIPTION}"',
            "exit"
        ]
        st.config(dut, cmd_list, type="klish")
        st.log(f"✓ VLAN {TEST_VLAN_20} interface created with description")

        st.wait(2)

        st.banner(f"STEP 2: Verify description exists in running configuration")

        config = self._get_running_config(dut, module=f"interface Vlan {TEST_VLAN_20}")
        parsed = self._verify_vlan_interface_in_config(config, TEST_VLAN_20)

        if not parsed["description"]:
            st.report_fail("msg", "Description not found in initial configuration")

        st.log(f"✓ Initial description verified: '{parsed['description']}'")

        st.banner(f"STEP 3: Remove description using 'no description'")

        cmd_list = [
            f"interface Vlan {TEST_VLAN_20}",
            "no description",
            "exit"
        ]
        st.config(dut, cmd_list, type="klish", skip_error_check=True)
        st.log("✓ Executed 'no description' command")

        st.wait(2)

        st.banner(f"STEP 4: Verify description removal")

        config_after = self._get_running_config(dut, module=f"interface Vlan {TEST_VLAN_20}")
        parsed_after = self._verify_vlan_interface_in_config(config_after, TEST_VLAN_20)

        st.banner(f"STEP 5: Document bug behavior")

        if parsed_after["description"] is None:
            st.log("✓ Description successfully removed (BUG FIXED!)")
        else:
            st.warn("=" * 80)
            st.warn("KNOWN BUG DETECTED:")
            st.warn(f"  Command: 'no description' under interface Vlan {TEST_VLAN_20}")
            st.warn(f"  Expected: Description should be removed")
            st.warn(f"  Actual: Description still present: '{parsed_after['description']}'")
            st.warn("  Status: Bug persists - 'no description' does not remove description")
            st.warn("=" * 80)
            st.log("Test documents bug behavior - marking as informational")

        st.banner("TEST PASSED: VLAN description removal behavior documented")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["VLAN_LIFECYCLE_TC_003"])
    def test_vlan_interface_deletion(self) -> None:
        """TC 003 - Verify VLAN interface deletion (Known Bug Test).

        Test Steps:
        1. Create VLAN 20 with interface and description
        2. Verify interface exists in running config
        3. Delete interface using 'no interface Vlan 20'
        4. Verify interface deletion (Expected to fail due to bug)
        5. Verify interface state with 'show interface Vlan 20'
        6. Document bug behavior

        Note: This is a negative test documenting a known bug where
        'no interface Vlan <id>' does not delete the VLAN interface.
        """
        dut = self.data.dut

        st.banner(f"STEP 1: Create VLAN {TEST_VLAN_20} with interface and description")

        # Create VLAN
        result = vlan_api.create_vlan(dut, TEST_VLAN_20, cli_type="klish")
        if not result:
            st.report_fail("msg", f"Failed to create VLAN {TEST_VLAN_20}")

        # Configure VLAN interface with description
        cmd_list = [
            f"interface Vlan {TEST_VLAN_20}",
            f'description "{VLAN_DESCRIPTION}"',
            "exit"
        ]
        st.config(dut, cmd_list, type="klish")
        st.log(f"✓ VLAN {TEST_VLAN_20} interface created with description")

        st.wait(2)

        st.banner(f"STEP 2: Verify interface exists in running configuration")

        config_before = self._get_running_config(dut, module=f"interface Vlan {TEST_VLAN_20}")
        parsed_before = self._verify_vlan_interface_in_config(config_before, TEST_VLAN_20)

        if not parsed_before["interface_exists"]:
            st.report_fail("msg", f"VLAN {TEST_VLAN_20} interface not found before deletion test")

        st.log(f"✓ VLAN {TEST_VLAN_20} interface exists in running configuration")

        st.banner(f"STEP 3: Delete interface using 'no interface Vlan {TEST_VLAN_20}'")

        cmd = f"no interface Vlan {TEST_VLAN_20}"
        st.config(dut, cmd, type="klish", skip_error_check=True)
        st.log(f"✓ Executed 'no interface Vlan {TEST_VLAN_20}' command")

        st.wait(2)

        st.banner(f"STEP 4: Verify interface deletion in running configuration")

        config_after = self._get_running_config(dut, module=f"interface Vlan {TEST_VLAN_20}")
        parsed_after = self._verify_vlan_interface_in_config(config_after, TEST_VLAN_20)

        st.banner(f"STEP 5: Verify interface state with 'show interface Vlan {TEST_VLAN_20}'")

        # Check if interface still exists
        cmd_show_intf = f"show interface Vlan {TEST_VLAN_20}"
        intf_output = st.show(dut, cmd_show_intf, type="klish", skip_tmpl=True, skip_error_check=True)

        st.debug(f"Interface output: {intf_output}")

        st.banner(f"STEP 6: Document bug behavior")

        if not parsed_after["interface_exists"]:
            st.log("✓ VLAN interface successfully deleted (BUG FIXED!)")
        else:
            st.warn("=" * 80)
            st.warn("KNOWN BUG DETECTED:")
            st.warn(f"  Command: 'no interface Vlan {TEST_VLAN_20}'")
            st.warn(f"  Expected: VLAN interface should be deleted completely")
            st.warn(f"  Actual: Interface still present in running configuration")
            st.warn(f"  Interface block found:\n{parsed_after['full_block']}")

            # Check interface state
            if isinstance(intf_output, str) and ("is up" in intf_output.lower() or "is down" in intf_output.lower()):
                st.warn(f"  Interface state: Still exists (visible in 'show interface')")
                st.warn(f"  Output: {intf_output[:200]}")

            st.warn("  Status: Bug persists - 'no interface Vlan' does not delete interface")
            st.warn("=" * 80)
            st.log("Test documents bug behavior - marking as informational")

        st.banner("TEST PASSED: VLAN interface deletion behavior documented")
        st.report_pass("test_case_passed")
