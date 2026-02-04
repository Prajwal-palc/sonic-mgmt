"""
VLAN NEGATIVE TEST - Member Port Configuration on Non-Existent VLAN
Author: Shiva
2026

Test ID: VLAN-NEG-ADD-MEMBER-001

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/ztp_standalone.yaml \\
  tests/switching/vlan/test_vlan_negative_member.py \\
  --logs-path ./logs/vlan_negative_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Negative test suite to verify SONiC CLI properly rejects VLAN member port
  configurations when the target VLAN does not exist. Tests both access and
  trunk port scenarios. Current behavior silently accepts invalid configurations;
  expected behavior is to reject with clear error messages consistent with CLICK CLI.

  Test Scenario 1: Configure access port on non-existent VLAN 700
    - Command: switchport access Vlan 700
    - Expected: Error "VLAN does not exist. Create VLAN first using 'vlan <id>'"
    - Current (Bug): Accepts silently, VLAN not created, shows in running-config

  Test Scenario 2: Configure trunk port on non-existent VLAN 700
    - Command: switchport trunk allowed Vlan 700
    - Expected: Error "VLAN does not exist. Create VLAN first using 'vlan <id>'"
    - Current (Bug): Accepts silently, VLAN not created

Pre-requisites:
  - Topology: Single DUT (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Single node topology
        # +--------------------+
        # |    smic_sonic1     |
        # | (192.168.100.197)  |
        # |  Ethernet248       |
        # +--------------------+

  - Test Interface: Ethernet248 (configurable via YAML)
  - No VLANs should exist before test execution
  - Interface IP addresses will be removed before VLAN configuration

Data Sources:
  - DUT Details: testbeds/ztp_standalone.yaml
    - Device: smic_sonic1 (192.168.100.197:22)
    - Credentials: admin/root@123
    - Properties: Single DUT, no topology links

  - Test Scenarios: vlan_negative.md
    - Test commands and expected CLI behavior
    - Error messages: "VLAN does not exist. Create VLAN first using 'vlan <id>'"
    - Validation: show vlan, show running-configuration interface

  - Test Variables: vars/switching/vlan/vars_vlan_negative_member.yaml
    - VLAN ID: 700 (non-existent)
    - Interface: Ethernet248
    - Expected error messages
    - Verification parameters

APIs Used:
  - spytest/apis/switching/vlan.py:
    - get_vlan_list(dut, cli_type) - Get list of configured VLANs
    - delete_vlan(dut, vlan_id, cli_type) - Remove VLAN (cleanup)
    - verify_vlan_config(dut, vlan_list, cli_type) - Verify VLAN presence/absence

  - spytest framework (spytest/__init__.py):
    - st.config(dut, cmd, type, conf, skip_error_check) - Execute config commands
    - st.show(dut, cmd, type, skip_tmpl) - Execute show commands
    - st.log() - Logging
    - st.banner() - Section headers
    - st.warn() - Warnings
    - st.error() - Error messages
    - st.report_pass() - Mark test passed
    - st.report_fail() - Mark test failed and exit

Logs Location:
  ./logs/vlan_negative_<timestamp>/
  - dlog-D1-smic_sonic1.log - Full CLI command/output transcript
  - module_test_vlan_negative_member.log - Module-level logs
  - results.html - HTML test results report
  - summary.txt - Quick test summary
  - consolidated_report.html - Aggregated results

Expected Behavior:
  - CLI should reject invalid VLAN member configurations
  - Error message: "VLAN does not exist. Create VLAN first using 'vlan <id>'"
  - Interface configuration should be rejected
  - VLAN should NOT be created automatically

Current Behavior (Bug):
  - CLI accepts configuration silently (no error message)
  - VLAN is NOT created
  - Interface running-config shows invalid VLAN assignment
  - Inconsistent with CLICK CLI behavior

Test Strategy:
  1. Pre-test cleanup: Remove all VLANs, clear interface configurations
  2. Verify baseline: "show vlan" returns "No VLANs configured"
  3. Remove IP address from test interface (required before VLAN config)
  4. Attempt invalid configuration (access/trunk on non-existent VLAN)
  5. Capture command output and check for error message
  6. Verify VLAN was NOT created
  7. Document current buggy behavior vs expected behavior
  8. Post-test cleanup: Restore DUT to clean state
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api


# Environment variable for YAML override
VAR_FILE_ENV = "VLAN_NEGATIVE_VAR_FILE"

# Default YAML configuration file path
# Path calculation: test_vlan_negative_member.py is in tests/switching/vlan/
# YAML file is in vars/switching/vlan/
# From test file: go up 3 levels to spytest/, then to vars/switching/vlan/
# __file__ = .../spytest/tests/switching/vlan/test_vlan_negative_member.py
# parents[0] = .../spytest/tests/switching/vlan/
# parents[1] = .../spytest/tests/switching/
# parents[2] = .../spytest/tests/
# parents[3] = .../spytest/ (THIS IS WHAT WE NEED)
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_negative_member.yaml"
)


def _set_terminal_length(dut: str, length: int = 0) -> None:
    """Set terminal length to control pagination in show commands.

    Args:
        dut: Device under test
        length: Terminal length (0 = no pagination, disable --more-- prompts)

    Note:
        This prevents show commands from displaying --more-- prompts that
        would cause automation scripts to hang waiting for user input.
    """
    try:
        cmd = f"terminal length {length}"
        st.config(dut, cmd, type="klish", conf=False, skip_error_check=True)
        st.log(f"Set terminal length to {length} on {dut} (pagination disabled)")
    except Exception as e:
        st.warn(f"Failed to set terminal length: {e}")


def _load_yaml_config() -> Dict[str, Any]:
    """Load test configuration from YAML file.

    Returns:
        Dictionary containing test configuration

    Raises:
        FileNotFoundError: If YAML file not found
        ValueError: If YAML structure is invalid
    """
    # Check for environment override
    override_path = st.getenv(VAR_FILE_ENV)
    yaml_path = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not yaml_path.is_file():
        raise FileNotFoundError(
            f"VLAN negative test variable file not found: {yaml_path}\n"
            f"Expected location: {DEFAULT_VAR_FILE}\n"
            f"Override via environment: export {VAR_FILE_ENV}=<path>"
        )

    st.log(f"Loading VLAN negative test configuration from: {yaml_path}")

    with yaml_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    if "testcases" not in config:
        raise ValueError(
            f"YAML file must contain 'testcases' key: {yaml_path}"
        )

    st.log("VLAN negative test configuration loaded successfully")
    return config


@pytest.mark.topology("any")
class TestVlanNegativeMember:
    """Negative test cases for VLAN member port configuration validation.

    Tests verify that SONiC CLI properly rejects attempts to configure
    VLAN member ports (access or trunk) when the target VLAN does not exist.
    Documents current buggy behavior vs expected behavior.
    """

    # Class-level data storage
    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup test suite: Load configuration, prepare DUT, initial cleanup.

        Steps:
            1. Load YAML configuration (test parameters, expected errors)
            2. Get DUT handle from topology
            3. Disable terminal pagination (avoid --more-- prompts)
            4. Perform initial cleanup (remove all VLANs)
            5. Verify baseline state (no VLANs configured)
        """
        st.banner("CLASS SETUP: VLAN Negative Test Suite - Member Port Configuration")

        # Load test configuration from YAML
        config = _load_yaml_config()
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(config.get("defaults", {}))
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # Get topology
        min_topology = cls.data.defaults.get("min_topology", ["D1"])
        topology = st.ensure_min_topology(*min_topology)
        cls.data.topology = topology

        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs found in topology")

        cls.data.dut = cls.data.dut_names[0]
        st.log(f"Test DUT: {cls.data.dut}")

        # Get test parameters
        cls.data.cli_type = cls.data.defaults.get("cli_type", "klish")
        cls.data.test_interface = cls.data.defaults.get("test_interface", "Ethernet248")
        cls.data.nonexistent_vlan_id = str(cls.data.defaults.get("nonexistent_vlan_id", 700))
        cls.data.verify_timeout = int(cls.data.defaults.get("verify_timeout", 30))

        st.log(f"CLI Type: {cls.data.cli_type}")
        st.log(f"Test Interface: {cls.data.test_interface}")
        st.log(f"Non-existent VLAN ID: {cls.data.nonexistent_vlan_id}")

        # Disable terminal pagination to avoid --more-- prompts in show commands
        _set_terminal_length(cls.data.dut, 0)
        st.log("Terminal pagination disabled for all show commands")

        # Initial cleanup: Remove all VLANs
        st.banner("INITIAL CLEANUP: Removing all VLANs")
        cls._cleanup_all_vlans()

        # Clear interface configuration
        cls._cleanup_interface_config(cls.data.test_interface)

        # Verify baseline: No VLANs should exist
        st.banner("BASELINE VERIFICATION: Checking initial state")
        vlan_list = vlan_api.get_vlan_list(cls.data.dut, cli_type=cls.data.cli_type)
        if vlan_list:
            st.error(f"VLANs still present after cleanup: {vlan_list}")
            st.report_fail("msg", "Failed to achieve clean baseline state")

        st.log("✓ Baseline verified: No VLANs configured")
        st.log("Class setup completed successfully")

    @classmethod
    def teardown_class(cls) -> None:
        """Teardown test suite: Final cleanup to restore DUT to clean state.

        Steps:
            1. Remove all VLANs
            2. Clear interface configurations
            3. Verify clean state restored
        """
        st.banner("CLASS TEARDOWN: Final cleanup")

        # Final cleanup
        cls._cleanup_all_vlans()
        cls._cleanup_interface_config(cls.data.test_interface)

        # Verify clean state
        vlan_list = vlan_api.get_vlan_list(cls.data.dut, cli_type=cls.data.cli_type)
        if vlan_list:
            st.warn(f"VLANs still present after teardown: {vlan_list}")

        st.log("Class teardown completed")

    def setup_method(self, method) -> None:
        """Per-test setup: Ensure clean state before each test.

        Args:
            method: Test method being executed
        """
        st.banner(f"TEST SETUP: {method.__name__}")

        # Verify no VLANs exist before test
        vlan_list = vlan_api.get_vlan_list(self.data.dut, cli_type=self.data.cli_type)
        if vlan_list:
            st.warn(f"VLANs present before test: {vlan_list}")
            self._cleanup_all_vlans()

        # Clear interface configuration
        self._cleanup_interface_config(self.data.test_interface)

        st.log("Test setup completed")

    def teardown_method(self, method) -> None:
        """Per-test teardown: Cleanup after each test.

        Args:
            method: Test method that was executed
        """
        st.banner(f"TEST TEARDOWN: {method.__name__}")

        # Cleanup any VLANs that might have been created
        self._cleanup_all_vlans()

        # Clear interface configuration
        self._cleanup_interface_config(self.data.test_interface)

        st.log("Test teardown completed")

    @classmethod
    def _cleanup_all_vlans(cls) -> None:
        """Remove all VLANs from DUT (cleanup helper).

        This method removes all VLANs regardless of whether they were
        created by tests or existed previously.
        """
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        try:
            vlan_list = vlan_api.get_vlan_list(dut, cli_type=cli_type)
            if not vlan_list:
                st.log("No VLANs to cleanup")
                return

            st.log(f"Removing VLANs: {vlan_list}")

            for vlan_id in vlan_list:
                try:
                    vlan_api.delete_vlan(dut, vlan_id, cli_type=cli_type)
                    st.log(f"Removed VLAN {vlan_id}")
                except Exception as e:
                    st.debug(f"Error removing VLAN {vlan_id}: {e}")

            # Verify cleanup
            remaining_vlans = vlan_api.get_vlan_list(dut, cli_type=cli_type)
            if remaining_vlans:
                st.warn(f"Some VLANs could not be removed: {remaining_vlans}")
            else:
                st.log("All VLANs removed successfully")

        except Exception as e:
            st.error(f"VLAN cleanup failed: {e}")

    @classmethod
    def _get_vlans_with_interface(cls, interface: str) -> List[str]:
        """Get list of VLAN IDs that contain the specified interface as member.

        Args:
            interface: Interface name (e.g., Ethernet0)

        Returns:
            List of VLAN IDs (strings) that have this interface as member (access or trunk)

        Note:
            This function queries 'show vlan' output to find which VLANs contain
            the interface. This is needed for smart cleanup - we only remove the
            interface from VLANs it's actually in.
        """
        dut = cls.data.dut
        cli_type = cls.data.cli_type
        vlans_with_interface = []

        try:
            # Get all configured VLANs
            vlan_list = vlan_api.get_vlan_list(dut, cli_type=cli_type)

            if not vlan_list:
                st.log(f"No VLANs found, interface {interface} not in any VLAN")
                return []

            st.log(f"Checking if {interface} is in any of VLANs: {vlan_list}")

            # For each VLAN, check if interface is a member
            for vlan_id in vlan_list:
                try:
                    # Check if interface is untagged member (access port)
                    is_untagged = vlan_api.verify_vlan_config(
                        dut,
                        vlan_list=vlan_id,
                        untagged=interface,
                        cli_type=cli_type
                    )

                    if is_untagged:
                        st.log(f"Found {interface} as untagged member in VLAN {vlan_id}")
                        vlans_with_interface.append(vlan_id)
                        continue

                    # Check if interface is tagged member (trunk port)
                    is_tagged = vlan_api.verify_vlan_config(
                        dut,
                        vlan_list=vlan_id,
                        tagged=interface,
                        cli_type=cli_type
                    )

                    if is_tagged:
                        st.log(f"Found {interface} as tagged member in VLAN {vlan_id}")
                        vlans_with_interface.append(vlan_id)

                except Exception as e:
                    st.debug(f"Error checking VLAN {vlan_id} membership: {e}")
                    continue

            if vlans_with_interface:
                st.log(f"{interface} is member of VLANs: {vlans_with_interface}")
            else:
                st.log(f"{interface} is not in any VLAN")

        except Exception as e:
            st.warn(f"Error getting VLANs with interface {interface}: {e}")

        return vlans_with_interface

    @classmethod
    def _cleanup_interface_config(cls, interface: str) -> None:
        """Remove interface configuration (IP addresses, switchport config).

        Args:
            interface: Interface name (e.g., Ethernet0)

        Note:
            Smart cleanup approach:
            1. Query which VLANs contain the interface
            2. Remove interface from those specific VLANs:
               - Access VLAN: "no switchport access Vlan"
               - Trunk VLANs: "no switchport trunk allowed Vlan <id>" for each VLAN
            3. Remove IP addresses
            4. Exit to exec mode with "end"

            This avoids the "Ambiguous command" error from "no switchport"
        """
        dut = cls.data.dut
        cli_type = cls.data.cli_type

        st.log(f"Cleaning interface configuration: {interface}")

        try:
            # Step 1: Find which VLANs contain this interface
            vlans_with_interface = cls._get_vlans_with_interface(interface)

            # Step 2: Build cleanup commands
            commands = [f"interface {interface}"]

            # Remove access VLAN (always try, safe with skip_error_check)
            commands.append("no switchport access Vlan")
            st.log(f"Will remove access VLAN config from {interface}")

            # Remove trunk VLANs (only for VLANs that actually contain this interface)
            if vlans_with_interface:
                for vlan_id in vlans_with_interface:
                    cmd = f"no switchport trunk allowed Vlan {vlan_id}"
                    commands.append(cmd)
                    st.log(f"Will remove {interface} from trunk VLAN {vlan_id}")
            else:
                st.log(f"{interface} is not in any VLAN, skipping trunk VLAN removal")

            # Remove IP addresses
            commands.append("no ip address")
            commands.append("no ipv6 address")

            # Exit to exec mode (not config mode)
            commands.append("end")

            # Step 3: Execute commands with error suppression
            st.log(f"Executing cleanup commands: {commands}")

            for cmd in commands:
                try:
                    st.config(
                        dut,
                        cmd,
                        type=cli_type,
                        skip_error_check=True
                    )
                except Exception as e:
                    st.debug(f"Command '{cmd}' error (expected): {e}")

            st.log(f"Interface {interface} configuration cleared")

        except Exception as e:
            st.debug(f"Interface cleanup error: {e}")

    def _remove_ip_from_interface(self, interface: str) -> None:
        """Remove IP address from interface before VLAN configuration.

        Args:
            interface: Interface name (e.g., Ethernet0)

        Note:
            This is required before configuring interface as switchport.
            An interface with IP address cannot be added to VLAN.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Removing IP addresses from {interface}")

        try:
            commands = [
                f"interface {interface}",
                "no ip address",   # Remove any IPv4 address
                "no ipv6 address", # Remove any IPv6 address
                "end"              # Exit to exec mode (not config mode)
            ]

            for cmd in commands:
                try:
                    st.config(dut, cmd, type=cli_type, skip_error_check=True)
                except Exception as e:
                    st.debug(f"Command '{cmd}' - {e}")

            st.log(f"✓ IP addresses removed from {interface}")

        except Exception as e:
            st.warn(f"Failed to remove IP from {interface}: {e}")

    def _verify_vlan_not_created(self, vlan_id: str) -> bool:
        """Verify that a VLAN was NOT created.

        Args:
            vlan_id: VLAN ID to check

        Returns:
            True if VLAN does NOT exist, False if it exists
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        # Disable pagination before show command
        _set_terminal_length(dut, 0)

        vlan_list = vlan_api.get_vlan_list(dut, cli_type=cli_type)
        vlan_exists = vlan_id in vlan_list

        if vlan_exists:
            st.error(f"VLAN {vlan_id} was created (unexpected)")
            return False
        else:
            st.log(f"✓ Verified: VLAN {vlan_id} was NOT created (expected)")
            return True

    def _check_error_message(self, output: str, expected_phrases: List[str]) -> bool:
        """Check if error message appears in command output.

        Args:
            output: Command output string
            expected_phrases: List of expected error message phrases

        Returns:
            True if any expected phrase found in output, False otherwise
        """
        if not output:
            return False

        output_lower = output.lower()

        for phrase in expected_phrases:
            if phrase.lower() in output_lower:
                st.log(f"✓ Found expected error phrase: '{phrase}'")
                return True

        return False

    def _get_running_config_interface(self, interface: str) -> str:
        """Get running configuration for specific interface.

        Args:
            interface: Interface name

        Returns:
            Running configuration output as string
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        # Disable pagination to avoid --more-- prompts
        _set_terminal_length(dut, 0)

        cmd = f"show running-configuration interface {interface}"
        output = st.show(dut, cmd, type=cli_type, skip_tmpl=True)

        return str(output) if output else ""

    @pytest.mark.inventory(feature="Regression", testcases=["VLAN-NEG-ADD-MEMBER-001-ACCESS"])
    @pytest.mark.negative
    def test_vlan_access_port_nonexistent_vlan(self) -> None:
        """Test Scenario 1: Access port configuration on non-existent VLAN.

        Test Steps:
            1. Verify VLAN 700 does not exist
            2. Remove IP address from test interface (required)
            3. Configure: interface Ethernet248 → switchport access Vlan 700
            4. Capture command output and check for error message
            5. Verify VLAN 700 was NOT created (show vlan)
            6. Verify interface running-config (document bug behavior)

        Expected Behavior:
            - CLI rejects command with error
            - Error: "VLAN does not exist. Create VLAN first using 'vlan <id>'"
            - VLAN 700 NOT created
            - Interface config unchanged

        Current Behavior (Bug):
            - CLI accepts command silently (no error)
            - VLAN 700 NOT created
            - Interface running-config shows: "switchport access Vlan 700"
            - Inconsistent with CLICK CLI
        """
        dut = self.data.dut
        cli_type = self.data.cli_type
        interface = self.data.test_interface
        vlan_id = self.data.nonexistent_vlan_id

        # Get test case configuration
        testcase = self.data.testcases.get("access_port_negative", {})
        expected_error = testcase.get("expected_error", "VLAN does not exist")

        st.banner("TEST 1: Access Port on Non-Existent VLAN")
        st.log(f"Testing: switchport access Vlan {vlan_id} on {interface}")
        st.log(f"Expected: Error message - '{expected_error}'")

        try:
            # Step 1: Verify VLAN does not exist
            st.banner("STEP 1: Verify VLAN does not exist")
            vlan_list = vlan_api.get_vlan_list(dut, cli_type=cli_type)
            if vlan_id in vlan_list:
                st.report_fail("msg", f"VLAN {vlan_id} already exists - cleanup failed")

            st.log(f"✓ Confirmed: VLAN {vlan_id} does not exist")

            # Step 2: Remove IP address from interface (required before VLAN config)
            st.banner(f"STEP 2: Remove IP address from {interface}")
            self._remove_ip_from_interface(interface)

            # Step 3: Attempt to configure access port on non-existent VLAN
            st.banner(f"STEP 3: Configure access port on non-existent VLAN {vlan_id}")

            # Execute configuration commands
            config_commands = [
                f"interface {interface}",
                f"switchport access Vlan {vlan_id}",
                "end"  # Exit to exec mode (not config mode)
            ]

            st.log(f"Executing commands: {config_commands}")

            # Capture output to check for error messages
            output = ""
            for cmd in config_commands:
                try:
                    result = st.config(
                        dut,
                        cmd,
                        type=cli_type,
                        skip_error_check=True  # Don't fail on errors, we're testing error handling
                    )
                    output += str(result) if result else ""
                except Exception as e:
                    output += str(e)
                    st.log(f"Command '{cmd}' output: {e}")

            st.log(f"Command output captured:\n{output}")

            # Step 4: Check for error message in output
            st.banner("STEP 4: Check for error message")
            expected_phrases = [
                "VLAN does not exist",
                "Create VLAN first",
                "vlan <id>"
            ]

            error_found = self._check_error_message(output, expected_phrases)

            if error_found:
                st.log("✓ EXPECTED BEHAVIOR: Error message displayed")
                test_result = "PASS"
            else:
                st.warn("✗ BUG CONFIRMED: No error message (command accepted silently)")
                test_result = "FAIL - Bug Documented"

            # Step 5: Verify VLAN was NOT created
            st.banner(f"STEP 5: Verify VLAN {vlan_id} was NOT created")
            vlan_not_created = self._verify_vlan_not_created(vlan_id)

            if not vlan_not_created:
                st.report_fail("msg", f"VLAN {vlan_id} was created unexpectedly")

            # Step 6: Check interface running-config (document bug)
            st.banner(f"STEP 6: Check interface running-config")
            running_config = self._get_running_config_interface(interface)
            st.log(f"Interface {interface} running-config:\n{running_config}")

            # Check if invalid VLAN appears in config (bug documentation)
            if f"switchport access Vlan {vlan_id}" in running_config:
                st.warn(
                    f"✗ BUG DOCUMENTED: Invalid VLAN {vlan_id} appears in running-config "
                    f"even though VLAN doesn't exist"
                )
            else:
                st.log("✓ Interface config does not show invalid VLAN")

            # Test result summary
            st.banner("TEST 1 RESULT SUMMARY")
            st.log(f"Test Interface: {interface}")
            st.log(f"Non-existent VLAN: {vlan_id}")
            st.log(f"Error message displayed: {error_found}")
            st.log(f"VLAN created: {not vlan_not_created}")
            st.log(f"Result: {test_result}")

            if error_found:
                st.log("✓ CLI behavior correct - command rejected with error")
                st.report_pass("test_case_passed")
            else:
                st.warn("✗ BUG: CLI accepted invalid configuration without error")
                st.log("Expected: Error 'VLAN does not exist. Create VLAN first...'")
                st.log("Actual: Command accepted silently")
                st.report_fail(
                    "msg",
                    f"BUG: CLI accepted 'switchport access Vlan {vlan_id}' without error. "
                    f"Expected rejection with error message."
                )

        finally:
            # Cleanup
            st.banner("CLEANUP: Test 1")
            self._cleanup_all_vlans()
            self._cleanup_interface_config(interface)

    @pytest.mark.inventory(feature="Regression", testcases=["VLAN-NEG-ADD-MEMBER-001-TRUNK"])
    @pytest.mark.negative
    def test_vlan_trunk_port_nonexistent_vlan(self) -> None:
        """Test Scenario 2: Trunk port configuration on non-existent VLAN.

        Test Steps:
            1. Verify VLAN 700 does not exist
            2. Remove IP address from test interface (required)
            3. Configure: interface Ethernet248 → switchport trunk allowed Vlan 700
            4. Capture command output and check for error message
            5. Verify VLAN 700 was NOT created (show vlan)

        Expected Behavior:
            - CLI rejects command with error
            - Error: "VLAN does not exist. Create VLAN first using 'vlan <id>'"
            - VLAN 700 NOT created
            - Interface config unchanged

        Current Behavior (Bug):
            - CLI accepts command silently (no error)
            - VLAN 700 NOT created
            - Inconsistent with CLICK CLI

        Note:
            Correct command syntax: "switchport trunk allowed Vlan <id>" (capital V)
        """
        dut = self.data.dut
        cli_type = self.data.cli_type
        interface = self.data.test_interface
        vlan_id = self.data.nonexistent_vlan_id

        # Get test case configuration
        testcase = self.data.testcases.get("trunk_port_negative", {})
        expected_error = testcase.get("expected_error", "VLAN does not exist")

        st.banner("TEST 2: Trunk Port on Non-Existent VLAN")
        st.log(f"Testing: switchport trunk allowed Vlan {vlan_id} on {interface}")
        st.log(f"Expected: Error message - '{expected_error}'")

        try:
            # Step 1: Verify VLAN does not exist
            st.banner("STEP 1: Verify VLAN does not exist")
            vlan_list = vlan_api.get_vlan_list(dut, cli_type=cli_type)
            if vlan_id in vlan_list:
                st.report_fail("msg", f"VLAN {vlan_id} already exists - cleanup failed")

            st.log(f"✓ Confirmed: VLAN {vlan_id} does not exist")

            # Step 2: Remove IP address from interface (required before VLAN config)
            st.banner(f"STEP 2: Remove IP address from {interface}")
            self._remove_ip_from_interface(interface)

            # Step 3: Attempt to configure trunk port on non-existent VLAN
            st.banner(f"STEP 3: Configure trunk port with non-existent VLAN {vlan_id}")

            # Execute configuration commands
            # Note: Correct syntax is "switchport trunk allowed Vlan <id>" (capital V)
            config_commands = [
                f"interface {interface}",
                f"switchport trunk allowed Vlan {vlan_id}",
                "end"  # Exit to exec mode (not config mode)
            ]

            st.log(f"Executing commands: {config_commands}")

            # Capture output to check for error messages
            output = ""
            for cmd in config_commands:
                try:
                    result = st.config(
                        dut,
                        cmd,
                        type=cli_type,
                        skip_error_check=True  # Don't fail on errors, we're testing error handling
                    )
                    output += str(result) if result else ""
                except Exception as e:
                    output += str(e)
                    st.log(f"Command '{cmd}' output: {e}")

            st.log(f"Command output captured:\n{output}")

            # Step 4: Check for error message in output
            st.banner("STEP 4: Check for error message")
            expected_phrases = [
                "VLAN does not exist",
                "Create VLAN first",
                "vlan <id>"
            ]

            error_found = self._check_error_message(output, expected_phrases)

            if error_found:
                st.log("✓ EXPECTED BEHAVIOR: Error message displayed")
                test_result = "PASS"
            else:
                st.warn("✗ BUG CONFIRMED: No error message (command accepted silently)")
                test_result = "FAIL - Bug Documented"

            # Step 5: Verify VLAN was NOT created
            st.banner(f"STEP 5: Verify VLAN {vlan_id} was NOT created")
            vlan_not_created = self._verify_vlan_not_created(vlan_id)

            if not vlan_not_created:
                st.report_fail("msg", f"VLAN {vlan_id} was created unexpectedly")

            # Test result summary
            st.banner("TEST 2 RESULT SUMMARY")
            st.log(f"Test Interface: {interface}")
            st.log(f"Non-existent VLAN: {vlan_id}")
            st.log(f"Command: switchport trunk allowed Vlan {vlan_id}")
            st.log(f"Error message displayed: {error_found}")
            st.log(f"VLAN created: {not vlan_not_created}")
            st.log(f"Result: {test_result}")

            if error_found:
                st.log("✓ CLI behavior correct - command rejected with error")
                st.report_pass("test_case_passed")
            else:
                st.warn("✗ BUG: CLI accepted invalid configuration without error")
                st.log("Expected: Error 'VLAN does not exist. Create VLAN first...'")
                st.log("Actual: Command accepted silently")
                st.report_fail(
                    "msg",
                    f"BUG: CLI accepted 'switchport trunk allowed Vlan {vlan_id}' without error. "
                    f"Expected rejection with error message."
                )

        finally:
            # Cleanup
            st.banner("CLEANUP: Test 2")
            self._cleanup_all_vlans()
            self._cleanup_interface_config(interface)
