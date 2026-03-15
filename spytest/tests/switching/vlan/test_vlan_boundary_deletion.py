"""
VLAN BOUNDARY AND DELETION NEGATIVE TESTS
Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/ztp_standalone.yaml \
  tests/switching/vlan/test_vlan_boundary_deletion.py \
  --logs-path ./logs/vlan_boundary_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates VLAN creation boundary conditions and deletion protection mechanisms.
  TC_VLAN_CREATE_004 verifies the system rejects invalid VLAN IDs (0 and 4095)
  outside the standard 802.1Q range (1-4094). TC_VLAN_DELETE_002 verifies the
  system prevents deletion of VLANs that have active port members, ensuring
  safe configuration management and preventing traffic blackholing.

Pre-requisites:
  - Topology: Single DUT (standalone) | Supported: HW and Virtual
  - Topology Diagram:
        # Single Device Topology
        # +------------------+
        # |   smic_sonic1    |
        # |   (Standalone)   |
        # |                  |
        # |   Ethernet8      |
        # +------------------+
  - Feature flags / min SONiC version: VLAN support required
  - Required test variables (YAML): spytest/vars/switching/vlan/vars_vlan_boundary.yaml
    - TC_VLAN_CREATE_004.invalid_vlans
    - TC_VLAN_DELETE_002.test_vlan
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api

# Default YAML variable file location
VAR_FILE_ENV = "VLAN_BOUNDARY_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_boundary.yaml"
)


def _load_yaml_config() -> Dict[str, Any]:
    """Load test configuration from YAML file."""
    override_path = st.getenv(VAR_FILE_ENV)
    yaml_file = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not yaml_file.is_file():
        raise FileNotFoundError(f"VLAN boundary variable file not found: {yaml_file}")

    with yaml_file.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    if "testcases" not in config:
        raise ValueError("YAML must contain 'testcases' key")

    return config


@pytest.mark.topology("any")
class TestVlanBoundaryDeletion:
    """Test class for VLAN boundary validation and deletion protection."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """
        Class-level setup: Load configuration and ensure minimum topology.

        Topology requirement: Single DUT (standalone device).
        """
        st.banner("VLAN Boundary & Deletion Tests: Class Setup")

        # Load YAML configuration
        config = _load_yaml_config()
        defaults = config.get("defaults", {})
        testcases = config.get("testcases", {})

        # Ensure minimum topology: Single DUT
        min_topology = defaults.get("min_topology", ["D1:1"])
        topology = st.ensure_min_topology(*min_topology)

        # Store configuration
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.testcases = SpyTestDict(testcases)
        cls.data.topology = topology
        cls.data.cli_type = defaults.get("cli_type", "klish")

        # Get DUT handle
        cls.data.dut = topology.D1

        # Get test interface from testbed global params
        # ztp_standalone.yaml defines: global.params.test_interface = "Ethernet8"
        cls.data.test_interface = st.get_testbed_vars().get("test_interface", "Ethernet8")

        st.log(f"DUT: {cls.data.dut}")
        st.log(f"Test Interface: {cls.data.test_interface}")
        st.log(f"CLI Type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Class-level teardown: cleanup configuration."""
        st.banner("VLAN Boundary & Deletion Tests: Class Teardown")

    def setup_method(self) -> None:
        """Per-test setup."""
        pass

    def teardown_method(self) -> None:
        """Per-test teardown."""
        pass

    def _check_error_in_output(self, output: str, expected_pattern: str) -> bool:
        """
        Check if error pattern exists in CLI output.

        Args:
            output: CLI command output
            expected_pattern: Regex pattern to match error message

        Returns:
            True if error pattern found, False otherwise
        """
        if not output:
            return False

        # Convert output to string and search for pattern
        output_str = str(output)

        # Check if pattern matches (case-insensitive)
        if re.search(expected_pattern, output_str, re.IGNORECASE):
            st.log(f"✓ Found expected error pattern: {expected_pattern}")
            return True

        st.log(f"✗ Expected error pattern NOT found: {expected_pattern}")
        st.log(f"Output was: {output_str}")
        return False

    def _prepare_interface_for_vlan(self, dut: str, interface: str, vlan_id: int) -> bool:
        """
        Prepare interface for VLAN membership by removing L3 config and existing VLAN assignments.

        Args:
            dut: Device handle
            interface: Interface name
            vlan_id: VLAN ID to prepare for

        Returns:
            True if successful
        """
        st.log(f"Preparing interface {interface} on {dut} for VLAN {vlan_id}")

        try:
            commands = []

            # Enter interface configuration mode
            if "Ethernet" in interface:
                intf_num = interface.replace("Ethernet", "")
                commands.append(f"interface Ethernet {intf_num}")
            else:
                commands.append(f"interface {interface}")

            # Execute cleanup commands to clear any existing configuration
            commands.append("no ip address")
            commands.append("no switchport access Vlan")
            # Note: Don't remove specific VLAN from trunk as VLAN may not exist yet

            # Exit interface mode
            commands.append("exit")

            # Execute commands
            st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)

            st.log(f"✓ Interface {interface} prepared for VLAN configuration")
            return True

        except Exception as e:
            st.error(f"Failed to prepare interface {interface}: {e}")
            return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_CREATE_004"])
    @pytest.mark.negative
    def test_vlan_invalid_boundary(self) -> None:
        """
        TC_VLAN_CREATE_004: Verify system rejects invalid VLAN IDs outside 802.1Q boundary.

        Test Steps:
        1. Attempt to create VLAN 0 (below valid range)
        2. Verify appropriate error message
        3. Attempt to create VLAN 4095 (above valid range)
        4. Verify appropriate error message
        5. Confirm valid range is 1-4094
        """
        st.banner("TC_VLAN_CREATE_004: VLAN Boundary Validation Test")

        # Get test configuration
        testcase = self.data.testcases.get("TC_VLAN_CREATE_004")
        if not testcase:
            st.report_fail("msg", "TC_VLAN_CREATE_004 not found in YAML configuration")

        invalid_vlans = testcase.get("invalid_vlans", [])
        valid_range = testcase.get("valid_range", {})

        dut = self.data.dut

        st.log(f"Testing invalid VLAN IDs on {dut}")
        st.log(f"Valid VLAN range: {valid_range.get('min', 1)}-{valid_range.get('max', 4094)}")

        # Test each invalid VLAN ID
        for vlan_test in invalid_vlans:
            vlan_id = vlan_test.get("id")
            description = vlan_test.get("description")
            expected_error_pattern = vlan_test.get("expected_error_pattern")

            st.log(f"\nTesting VLAN {vlan_id}: {description}")
            st.log(f"Expected error pattern: {expected_error_pattern}")

            # Attempt to create invalid VLAN using direct CLI command
            st.log(f"Attempting to create VLAN {vlan_id} (should fail with error)...")

            # Execute VLAN creation command directly to capture error message
            vlan_cmd = [
                f"vlan {vlan_id}",
                "exit"  # Exit config mode immediately
            ]
            output = st.config(
                dut,
                vlan_cmd,
                type=self.data.cli_type,
                skip_error_check=True,
                conf=True
            )

            st.log(f"CLI output: {output}")

            # Check if error pattern is in output
            error_found = self._check_error_in_output(str(output), expected_error_pattern)

            if not error_found:
                st.report_fail(
                    "msg",
                    f"VLAN {vlan_id} creation did not produce expected error message. "
                    f"Expected pattern: '{expected_error_pattern}', Output: '{output}'"
                )

            st.log(f"✓ VLAN {vlan_id} was correctly REJECTED with error message")

            # Verify VLAN was NOT created by checking VLAN list
            vlan_list = vlan_api.get_vlan_list(dut, cli_type=self.data.cli_type)
            if str(vlan_id) in [str(v) for v in vlan_list]:
                # If VLAN exists, try to delete it
                vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type, skip_error_check=True)

                st.report_fail(
                    "msg",
                    f"VLAN {vlan_id} was CREATED despite error message! "
                    f"System failed to validate 802.1Q boundary!"
                )

            st.log(f"✓ Verified: VLAN {vlan_id} was NOT created in VLAN database")

        # Summary
        st.banner("TC_VLAN_CREATE_004: PASSED")
        st.log("✓ Test Summary:")
        st.log(f"  - Tested {len(invalid_vlans)} invalid VLAN IDs")
        st.log("  - All invalid VLAN IDs were correctly rejected")
        st.log("  - System properly validates 802.1Q boundary (1-4094)")
        st.log("  - VLAN creation boundary protection is working correctly!")

        # Exit klish mode to Linux shell before test ends
        st.change_prompt(dut, "normal-user")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_DELETE_002"])
    @pytest.mark.negative
    def test_vlan_delete_with_members(self) -> None:
        """
        TC_VLAN_DELETE_002: Verify system prevents deletion of VLAN with active members.

        Test Steps:
        1. Create VLAN 100
        2. Add Ethernet8 as access port member
        3. Verify VLAN shows as "Up" with member
        4. Attempt to delete VLAN 100 (should fail with error)
        5. Remove member port
        6. Delete VLAN 100 (should succeed)
        """
        st.banner("TC_VLAN_DELETE_002: VLAN Deletion Protection Test")

        # Get test configuration
        testcase = self.data.testcases.get("TC_VLAN_DELETE_002")
        if not testcase:
            st.report_fail("msg", "TC_VLAN_DELETE_002 not found in YAML configuration")

        test_vlan = SpyTestDict(testcase.get("test_vlan", {}))
        expected_error_pattern = testcase.get("expected_error_pattern")

        vlan_id = test_vlan.id
        dut = self.data.dut
        test_interface = self.data.test_interface

        st.log(f"Test Configuration:")
        st.log(f"  DUT: {dut}")
        st.log(f"  Test VLAN: {vlan_id}")
        st.log(f"  Test Interface: {test_interface}")

        try:
            # Step 1: Create VLAN 100
            st.banner("Step 1: Creating VLAN 100")

            if not vlan_api.create_vlan(dut, vlan_id, cli_type=self.data.cli_type):
                st.report_fail("msg", f"Failed to create VLAN {vlan_id}")

            st.log(f"✓ VLAN {vlan_id} created")

            # Step 2: Prepare interface and add to VLAN as access port
            st.banner("Step 2: Adding Ethernet8 as access port member to VLAN 100")

            # Prepare interface (remove IP, clear existing VLAN assignments)
            if not self._prepare_interface_for_vlan(dut, test_interface, vlan_id):
                st.report_fail("msg", f"Failed to prepare {test_interface}")

            # Add interface to VLAN as access port (untagged)
            if not vlan_api.add_vlan_member(
                dut,
                vlan_id,
                test_interface,
                tagging_mode=False,  # Access port (untagged)
                cli_type=self.data.cli_type
            ):
                st.report_fail("msg", f"Failed to add {test_interface} to VLAN {vlan_id}")

            st.log(f"✓ {test_interface} added to VLAN {vlan_id} as access port")

            # Enable interface
            interface_api_commands = []
            if "Ethernet" in test_interface:
                intf_num = test_interface.replace("Ethernet", "")
                interface_api_commands.append(f"interface Ethernet {intf_num}")
            else:
                interface_api_commands.append(f"interface {test_interface}")

            interface_api_commands.append("no shutdown")
            interface_api_commands.append("exit")

            st.config(dut, interface_api_commands, type=self.data.cli_type, skip_error_check=True)

            st.log(f"✓ {test_interface} enabled (no shutdown)")

            # Step 3: Verify VLAN is Up with member
            st.banner("Step 3: Verifying VLAN 100 is Up with member port")

            # Show VLAN configuration
            vlan_output = vlan_api.show_vlan_config(dut, vlan_id, cli_type=self.data.cli_type)
            st.log(f"VLAN {vlan_id} configuration:")
            st.log(f"{vlan_output}")

            # Verify VLAN has the member
            if not vlan_api.verify_vlan_config(
                dut,
                vlan_id,
                tagged=None,
                untagged=[test_interface],
                cli_type=self.data.cli_type
            ):
                st.report_fail("msg", f"VLAN {vlan_id} does not have {test_interface} as member")

            st.log(f"✓ Verified: VLAN {vlan_id} has {test_interface} as access member")

            # Step 4: Attempt to delete VLAN with active member (should fail)
            st.banner("Step 4: Attempting to delete VLAN 100 (should be blocked)")

            # Attempt to delete VLAN using direct CLI command to capture error
            delete_cmd = [
                f"no vlan {vlan_id}",
                "exit"  # Exit config mode immediately
            ]
            st.log(f"Executing: no vlan {vlan_id} (should fail with error)")

            delete_output = st.config(
                dut,
                delete_cmd,
                type=self.data.cli_type,
                skip_error_check=True,
                conf=True
            )

            st.log(f"Delete command output: {delete_output}")

            # Check if error pattern is in output
            error_found = self._check_error_in_output(str(delete_output), expected_error_pattern)

            if not error_found:
                st.report_fail(
                    "msg",
                    f"VLAN {vlan_id} deletion did not produce expected error message. "
                    f"Expected pattern: '{expected_error_pattern}', Output: '{delete_output}'"
                )

            st.log(f"✓ VLAN {vlan_id} deletion was correctly BLOCKED with error message")
            st.log("✓ System is protecting against unsafe VLAN deletion")

            # Verify VLAN still exists
            vlan_list = vlan_api.get_vlan_list(dut, cli_type=self.data.cli_type)
            if str(vlan_id) not in [str(v) for v in vlan_list]:
                st.report_fail("msg", f"VLAN {vlan_id} was deleted unexpectedly despite error message!")

            st.log(f"✓ Verified: VLAN {vlan_id} still exists after blocked deletion attempt")

            # Step 5: Remove member port
            st.banner("Step 5: Removing member port from VLAN 100")

            if not vlan_api.delete_vlan_member(
                dut,
                vlan_id,
                test_interface,
                tagging_mode=False,
                cli_type=self.data.cli_type
            ):
                st.report_fail("msg", f"Failed to remove {test_interface} from VLAN {vlan_id}")

            st.log(f"✓ {test_interface} removed from VLAN {vlan_id}")

            # Verify member was removed
            vlan_output_after = vlan_api.show_vlan_config(dut, vlan_id, cli_type=self.data.cli_type)
            st.log(f"VLAN {vlan_id} configuration after member removal:")
            st.log(f"{vlan_output_after}")

            # Step 6: Delete VLAN (should succeed now)
            st.banner("Step 6: Deleting VLAN 100 (should succeed)")

            if not vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type):
                st.report_fail("msg", f"Failed to delete VLAN {vlan_id} after removing members")

            st.log(f"✓ VLAN {vlan_id} deleted successfully after removing all members")

            # Verify VLAN was deleted
            vlan_list_final = vlan_api.get_vlan_list(dut, cli_type=self.data.cli_type)
            if str(vlan_id) in [str(v) for v in vlan_list_final]:
                st.report_fail("msg", f"VLAN {vlan_id} still exists after deletion!")

            st.log(f"✓ Verified: VLAN {vlan_id} no longer exists")

            # Test Summary
            st.banner("TC_VLAN_DELETE_002: PASSED")
            st.log("✓ Test Summary:")
            st.log(f"  - Created VLAN {vlan_id}")
            st.log(f"  - Added {test_interface} as access member")
            st.log("  - Deletion was BLOCKED while member was active ✓")
            st.log("  - Removed member port")
            st.log("  - Deletion SUCCEEDED after member removal ✓")
            st.log("  - VLAN deletion protection is working correctly!")

            # Exit klish mode to Linux shell before test ends
            st.change_prompt(dut, "normal-user")

            st.report_pass("test_case_passed")

        except Exception as e:
            st.error(f"Test failed with exception: {e}")

            # Cleanup on failure
            try:
                # Try to remove member
                vlan_api.delete_vlan_member(
                    dut,
                    vlan_id,
                    test_interface,
                    tagging_mode=False,
                    cli_type=self.data.cli_type,
                    skip_error_check=True
                )

                # Try to delete VLAN
                vlan_api.delete_vlan(
                    dut,
                    vlan_id,
                    cli_type=self.data.cli_type,
                    skip_error_check=True
                )
            except:
                pass

            # Exit klish mode to Linux shell before test ends
            st.change_prompt(dut, "normal-user")

            st.report_fail("msg", f"TC_VLAN_DELETE_002 failed: {e}")
