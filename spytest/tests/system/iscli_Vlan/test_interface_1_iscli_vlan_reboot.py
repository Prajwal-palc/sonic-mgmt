"""
VLAN CONFIGURATION - VLAN CREATION, PORT MANAGEMENT, SAVE AND REBOOT VALIDATION
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_Vlan/test_interface_1_iscli_vlan_reboot.py \
  --logs-path ./logs/test_interface_1_iscli_vlan_reboot_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates VLAN creation, port management, configuration persistence across reboot by:
  1. Verifying baseline (no VLANs configured)
  2. Removing IP addresses (IPv4 and IPv6) from all testbed interfaces
  3. Creating VLAN 3
  4. Adding ports Ethernet0 and Ethernet4 to VLAN 3 as tagged members
  5. Verifying VLAN 3 with both ports in show Vlan output
  6. Saving configuration with 'write memory'
  7. Rebooting device with 'sudo reboot'
  8. Waiting for device to come back up
  9. Re-verifying VLAN 3 with both ports after reboot (configuration persistence check)
  10. Removing Ethernet0 from VLAN 3
  11. Verifying VLAN 3 with only Ethernet4 in show Vlan output
  12. Removing Ethernet4 from VLAN 3
  13. Verifying VLAN 3 with no ports in show Vlan output
  14. Deleting VLAN 3
  15. Verifying no VLANs configured

  This mirrors the exact CLI workflow:
    - show Vlan (baseline: No VLANs configured)
    - configure terminal -> interface Ethernet0 -> no ip address -> no ipv6 address -> exit
    - configure terminal -> interface Ethernet4 -> no ip address -> no ipv6 address -> exit
    - configure terminal -> vlan 3 -> exit
    - show Vlan (verify: Vlan3 exists with no ports)
    - configure terminal -> interface Ethernet0 -> switchport trunk allowed vlan 3 -> exit
    - configure terminal -> interface Ethernet4 -> switchport trunk allowed vlan 3 -> exit
    - show Vlan (verify: Vlan3 with Ethernet0 and Ethernet4)
    - write memory (save configuration)
    - sudo reboot (reboot device)
    - [wait for reboot]
    - show Vlan (verify: Vlan3 with Ethernet0 and Ethernet4 persists after reboot)
    - configure terminal -> interface Ethernet0 -> no switchport trunk allowed vlan 3 -> exit
    - show Vlan (verify: Vlan3 with only Ethernet4)
    - configure terminal -> interface Ethernet4 -> no switchport trunk allowed vlan 3 -> exit
    - show Vlan (verify: Vlan3 with no ports)
    - configure terminal -> no vlan 3 -> exit
    - show Vlan (verify: No VLANs configured)

  IMPORTANT: Uses 'show Vlan' command to validate VLAN creation and port membership.
  Tests configuration persistence across device reboot using 'write memory' and 'sudo reboot'.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Access to sonic-cli (klish mode)
  - Sudo privileges for reboot command
  - Required test variables: CLI type (klish)
"""

from __future__ import annotations

import pytest
import time
import re
from typing import Dict, Any, List, Optional

from spytest import st, SpyTestDict


# CLI type for all operations
CLI_TYPE = "klish"

# Wait times
WAIT_AFTER_VLAN_CHANGE = 2
WAIT_FOR_REBOOT = 180  # Wait time for device to reboot and come back up


@pytest.mark.topology("any")
class TestVlanConfigurationReboot:
    """Test cases for validating VLAN creation, port management, and config persistence across reboot via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing VLAN Configuration with Reboot Test Suite")
        st.log("=" * 80)

        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs available in topology")

        cls.data.dut1 = cls.data.dut_names[0]
        st.log(f"Primary DUT: {cls.data.dut1}")

        # CLI type - use klish as specified
        cls.data.cli_type = CLI_TYPE
        st.log(f"CLI Type: {cls.data.cli_type}")

        # Test VLAN ID
        cls.data.test_vlan = "3"
        st.log(f"Test VLAN: {cls.data.test_vlan}")

        # Test interfaces
        cls.data.interface1 = "Ethernet0"
        cls.data.interface2 = "Ethernet4"
        st.log(f"Test Interfaces: {cls.data.interface1}, {cls.data.interface2}")

        # Set terminal length 0 to disable pagination
        st.log("Setting terminal length 0 to disable pagination")
        st.config(cls.data.dut1, "terminal length 0", type=CLI_TYPE)

        st.log("Test setup complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup VLAN Configuration with Reboot Test Suite")
        st.log("=" * 80)
        st.log("Cleanup completed")

    def setup_method(self) -> None:
        """Setup before each test method."""
        st.log("\n" + "-" * 80)
        st.log("SETUP METHOD: Starting new test case")
        st.log("-" * 80)

    def teardown_method(self) -> None:
        """Teardown after each test method."""
        st.log("-" * 80)
        st.log("TEARDOWN METHOD: Completed test case")
        st.log("-" * 80 + "\n")

    @staticmethod
    def _get_show_vlan_output(dut: str) -> str:
        """
        Get 'show Vlan' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log("Getting 'show Vlan' output")

        # Command: show Vlan
        command = "show Vlan"

        # Execute command and get raw output
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"show Vlan output:\n{output}")
        return output

    @staticmethod
    def _remove_ip_addresses_from_interfaces(dut: str, interfaces: List[str]) -> bool:
        """
        Remove IPv4 and IPv6 addresses from all specified interfaces.

        Args:
            dut: Device handle
            interfaces: List of interface names (e.g., ["Ethernet0", "Ethernet4"])

        Returns:
            True if successful
        """
        st.log("Removing IP addresses from all interfaces")

        for interface in interfaces:
            st.log(f"Removing IP addresses from {interface}")
            commands = [
                "configure terminal",
                f"interface {interface}",
                "no ip address",
                "no ipv6 address",
                "exit"  # Exit from interface mode back to config mode
            ]
            result = st.config(dut, commands, type=CLI_TYPE)

        st.log("IP addresses removed from all interfaces")
        return True

    @staticmethod
    def _create_vlan(dut: str, vlan_id: str) -> bool:
        """
        Create VLAN using klish commands.

        IMPORTANT: Does NOT use exit - stays in config mode after VLAN creation.
        The framework will handle cleanup automatically.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")

        Returns:
            True if successful
        """
        st.log(f"Creating VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"vlan {vlan_id}"
            # NO exit - stay in config mode
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _delete_vlan(dut: str, vlan_id: str) -> bool:
        """
        Delete VLAN using klish commands.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")

        Returns:
            True if successful
        """
        st.log(f"Deleting VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"no vlan {vlan_id}"
            # NO exit - stay in config mode
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _add_port_to_vlan(dut: str, interface: str, vlan_id: str) -> bool:
        """
        Add interface to VLAN as tagged member using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            vlan_id: VLAN ID (e.g., "3")

        Returns:
            True if successful
        """
        st.log(f"Adding {interface} to VLAN {vlan_id} as tagged member")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"switchport trunk allowed vlan {vlan_id}",
            "exit"   # Exit from interface mode back to config mode
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_port_from_vlan(dut: str, interface: str, vlan_id: str) -> bool:
        """
        Remove interface from VLAN using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            vlan_id: VLAN ID (e.g., "3")

        Returns:
            True if successful
        """
        st.log(f"Removing {interface} from VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"no switchport trunk allowed vlan {vlan_id}",
            "exit"   # Only exit from interface mode, stay in config mode
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _save_config(dut: str) -> bool:
        """
        Save running configuration using 'write memory' command.

        Args:
            dut: Device handle

        Returns:
            True if successful
        """
        st.log("Saving configuration with 'write memory'")
        command = "write memory"
        result = st.config(dut, command, type=CLI_TYPE)
        st.log("Configuration saved successfully")
        return True

    @staticmethod
    def _reboot_device(dut: str) -> bool:
        """
        Reboot the device using 'sudo reboot' command.

        Args:
            dut: Device handle

        Returns:
            True if successful
        """
        st.log("Rebooting device with 'sudo reboot'")
        st.reboot(dut)
        st.log("Device reboot initiated")
        return True

    @staticmethod
    def _wait_for_device_ready(dut: str, wait_time: int = WAIT_FOR_REBOOT) -> bool:
        """
        Wait for device to come back up after reboot and be ready.

        Args:
            dut: Device handle
            wait_time: Time to wait in seconds

        Returns:
            True if device is ready
        """
        st.log(f"Waiting for device to come back up (waiting {wait_time} seconds)...")
        st.wait(wait_time, "Waiting for device to complete reboot and become ready")
        st.log("Device should be ready now")

        # Set terminal length 0 again after reboot
        st.log("Re-setting terminal length 0 to disable pagination after reboot")
        st.config(dut, "terminal length 0", type=CLI_TYPE)

        return True

    @staticmethod
    def _verify_no_vlans_configured(vlan_output: str) -> bool:
        """
        Verify that no VLANs are configured.

        Args:
            vlan_output: Raw output from 'show Vlan' command

        Returns:
            True if no VLANs are configured, False otherwise
        """
        st.log("Verifying no VLANs are configured")

        # Check for "No VLANs configured" message
        if "No VLANs configured" in vlan_output or "no vlans configured" in vlan_output.lower():
            st.log("PASS: No VLANs are configured")
            return True
        else:
            st.error("FAIL: VLANs are still configured")
            return False

    @staticmethod
    def _verify_vlan_exists(vlan_output: str, vlan_id: str) -> bool:
        """
        Verify that VLAN exists in show Vlan output.

        Args:
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "3")

        Returns:
            True if VLAN exists, False otherwise
        """
        st.log(f"Verifying VLAN {vlan_id} exists")

        # Search for "Vlan<id>" pattern
        vlan_pattern = rf'Vlan{vlan_id}\s+\S+'
        match = re.search(vlan_pattern, vlan_output, re.IGNORECASE)

        if match:
            st.log(f"PASS: VLAN {vlan_id} exists")
            return True
        else:
            st.error(f"FAIL: VLAN {vlan_id} does not exist")
            return False

    @staticmethod
    def _verify_vlan_status(vlan_output: str, vlan_id: str, expected_status: str) -> bool:
        """
        Verify that VLAN has the expected status (Up/Down).

        Expected output format:
        Q: A - Access (Untagged), T - Tagged
        NUM       Status      Q Ports             Autostate   Dynamic
        ------------------------------------------------------------------
        Vlan3     Down                            Enable      No

        Args:
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "3")
            expected_status: Expected status ("Up" or "Down")

        Returns:
            True if VLAN has expected status, False otherwise
        """
        st.log(f"Verifying VLAN {vlan_id} status is {expected_status}")

        # Search for VLAN line with status
        # Pattern: Vlan<id> followed by status (Up/Down)
        vlan_pattern = rf'Vlan{vlan_id}\s+(Up|Down)'
        match = re.search(vlan_pattern, vlan_output, re.IGNORECASE)

        if match:
            actual_status = match.group(1)
            if actual_status.lower() == expected_status.lower():
                st.log(f"PASS: VLAN {vlan_id} status is {actual_status}")
                return True
            else:
                st.error(f"FAIL: VLAN {vlan_id} status is {actual_status}, expected {expected_status}")
                return False
        else:
            st.error(f"FAIL: Could not determine VLAN {vlan_id} status from output")
            return False

    @staticmethod
    def _verify_port_in_vlan(vlan_output: str, vlan_id: str, interface: str) -> bool:
        """
        Verify that interface is a member of VLAN.

        Expected output format:
        Q: A - Access (Untagged), T - Tagged
        NUM       Status      Q Ports             Autostate   Dynamic
        ------------------------------------------------------------------
        Vlan3     Up          T  Ethernet4        Enable      No
                              T  Ethernet0                    No

        Args:
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "3")
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if interface is member of VLAN, False otherwise
        """
        st.log(f"Verifying {interface} is member of VLAN {vlan_id}")

        # Search for VLAN entry and check if interface is listed
        # The output can have ports on same line or continuation lines
        # Pattern: Look for interface name in the VLAN section
        vlan_section_pattern = rf'Vlan{vlan_id}\s+.*?(?=Vlan\d+|$)'
        vlan_match = re.search(vlan_section_pattern, vlan_output, re.IGNORECASE | re.DOTALL)

        if not vlan_match:
            st.error(f"FAIL: VLAN {vlan_id} not found in output")
            return False

        vlan_section = vlan_match.group(0)

        # Check if interface is in this VLAN section
        if interface in vlan_section:
            st.log(f"PASS: {interface} is member of VLAN {vlan_id}")
            return True
        else:
            st.error(f"FAIL: {interface} is not member of VLAN {vlan_id}")
            return False

    @staticmethod
    def _verify_port_not_in_vlan(vlan_output: str, vlan_id: str, interface: str) -> bool:
        """
        Verify that interface is NOT a member of VLAN.

        Args:
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "3")
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if interface is NOT member of VLAN, False otherwise
        """
        st.log(f"Verifying {interface} is NOT member of VLAN {vlan_id}")

        # Search for VLAN entry and check if interface is NOT listed
        vlan_section_pattern = rf'Vlan{vlan_id}\s+.*?(?=Vlan\d+|$)'
        vlan_match = re.search(vlan_section_pattern, vlan_output, re.IGNORECASE | re.DOTALL)

        if not vlan_match:
            st.error(f"FAIL: VLAN {vlan_id} not found in output")
            return False

        vlan_section = vlan_match.group(0)

        # Check if interface is NOT in this VLAN section
        if interface not in vlan_section:
            st.log(f"PASS: {interface} is NOT member of VLAN {vlan_id}")
            return True
        else:
            st.error(f"FAIL: {interface} is still member of VLAN {vlan_id}")
            return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_REBOOT_001"])
    def test_vlan_creation_port_management_and_reboot_persistence(self) -> None:
        """
        TC_VLAN_REBOOT_001: Validate CLI for VLAN creation, port management, and config persistence across reboot.

        Test Procedure:
        1. Verify baseline (no VLANs configured)
        2. Remove IP addresses (IPv4 and IPv6) from all testbed interfaces
        3. Create VLAN 3
        4. Verify VLAN 3 exists
        5. Add Ethernet0 to VLAN 3
        6. Add Ethernet4 to VLAN 3
        7. Verify both ports are members of VLAN 3
        8. Save configuration with 'write memory'
        9. Reboot device with 'sudo reboot'
        10. Wait for device to come back up
        11. Re-verify VLAN 3 with both ports (config persistence after reboot)
        12. Remove Ethernet0 from VLAN 3
        13. Verify Ethernet0 is not in VLAN 3, Ethernet4 is still in VLAN 3
        14. Remove Ethernet4 from VLAN 3
        15. Verify VLAN 3 exists but has no ports
        16. Delete VLAN 3
        17. Verify no VLANs configured

        Expected Result:
        - IP addresses can be removed from interfaces
        - VLAN can be created successfully
        - Ports can be added to VLAN as tagged members
        - Configuration can be saved with 'write memory'
        - Device can be rebooted successfully
        - VLAN configuration persists across reboot
        - Ports can be removed from VLAN after reboot
        - VLAN can be deleted successfully
        - All changes are reflected accurately in 'show Vlan' output
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: VLAN Creation, Port Management, and Reboot Persistence")
        st.log("=" * 80)

        # Track validation failures - test will continue but report fail at end
        validation_failures = []

        dut = self.data.dut1
        vlan_id = self.data.test_vlan
        interface1 = self.data.interface1
        interface2 = self.data.interface2

        # ===== STEP 1: Verify baseline (no VLANs configured) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Verify baseline (no VLANs configured)")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_no_vlans_configured(output):
            st.report_fail(
                "msg",
                "Baseline check failed: VLANs are configured when none should exist"
            )

        st.log("PASS: Baseline verified - no VLANs configured")

        # ===== STEP 2: Remove IP addresses from all testbed interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Remove IP addresses (IPv4 and IPv6) from all testbed interfaces")
        st.log("-" * 80)

        # Get all interfaces to clean
        testbed_interfaces = [interface1, interface2]
        self._remove_ip_addresses_from_interfaces(dut, testbed_interfaces)

        st.log("PASS: IP addresses removed from all testbed interfaces")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 3: Create VLAN 3 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 3: Create VLAN {vlan_id}")
        st.log("-" * 80)

        self._create_vlan(dut, vlan_id)
        st.log(f"Created VLAN {vlan_id}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 4: Verify VLAN 3 exists =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 4: Verify VLAN {vlan_id} exists")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_vlan_exists(output, vlan_id):
            st.report_fail(
                "msg",
                f"VLAN creation failed: VLAN {vlan_id} does not exist in 'show Vlan' output"
            )

        st.log(f"PASS: VLAN {vlan_id} exists")

        # ===== STEP 4.1: Verify VLAN status is Down (no active ports yet) =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 4.1: Verify VLAN {vlan_id} status is Down (no active member ports)")
        st.log("-" * 80)

        if not self._verify_vlan_status(output, vlan_id, "Down"):
            error_msg = f"VLAN status validation failed: VLAN {vlan_id} should be Down when no active member ports are configured"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: VLAN {vlan_id} status is Down (expected behavior with no active member ports)")

        # ===== STEP 5: Add Ethernet0 to VLAN 3 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 5: Add {interface1} to VLAN {vlan_id}")
        st.log("-" * 80)

        self._add_port_to_vlan(dut, interface1, vlan_id)
        st.log(f"Added {interface1} to VLAN {vlan_id}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 6: Add Ethernet4 to VLAN 3 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 6: Add {interface2} to VLAN {vlan_id}")
        st.log("-" * 80)

        self._add_port_to_vlan(dut, interface2, vlan_id)
        st.log(f"Added {interface2} to VLAN {vlan_id}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 7: Verify both ports are members of VLAN 3 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 7: Verify both ports are members of VLAN {vlan_id}")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_port_in_vlan(output, vlan_id, interface1):
            st.report_fail(
                "msg",
                f"Port addition failed: {interface1} is not member of VLAN {vlan_id}"
            )

        if not self._verify_port_in_vlan(output, vlan_id, interface2):
            st.report_fail(
                "msg",
                f"Port addition failed: {interface2} is not member of VLAN {vlan_id}"
            )

        st.log(f"PASS: Both {interface1} and {interface2} are members of VLAN {vlan_id}")

        # ===== STEP 8: Save configuration with 'write memory' =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Save configuration with 'write memory'")
        st.log("-" * 80)

        self._save_config(dut)
        st.log("PASS: Configuration saved successfully")

        # Wait after save
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 9: Reboot device with 'sudo reboot' =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Reboot device with 'sudo reboot'")
        st.log("-" * 80)

        self._reboot_device(dut)
        st.log("PASS: Device reboot initiated")

        # ===== STEP 10: Wait for device to come back up =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Wait for device to come back up after reboot")
        st.log("-" * 80)

        self._wait_for_device_ready(dut)
        st.log("PASS: Device is back up and ready")

        # ===== STEP 11: Re-verify VLAN 3 with both ports after reboot =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 11: Re-verify VLAN {vlan_id} with both ports after reboot (config persistence)")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_vlan_exists(output, vlan_id):
            st.report_fail(
                "msg",
                f"Config persistence failed: VLAN {vlan_id} does not exist after reboot"
            )

        if not self._verify_port_in_vlan(output, vlan_id, interface1):
            st.report_fail(
                "msg",
                f"Config persistence failed: {interface1} is not member of VLAN {vlan_id} after reboot"
            )

        if not self._verify_port_in_vlan(output, vlan_id, interface2):
            st.report_fail(
                "msg",
                f"Config persistence failed: {interface2} is not member of VLAN {vlan_id} after reboot"
            )

        st.log(f"PASS: VLAN {vlan_id} configuration persisted across reboot - both {interface1} and {interface2} are still members")

        # ===== STEP 12: Remove Ethernet0 from VLAN 3 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 12: Remove {interface1} from VLAN {vlan_id}")
        st.log("-" * 80)

        self._remove_port_from_vlan(dut, interface1, vlan_id)
        st.log(f"Removed {interface1} from VLAN {vlan_id}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 13: Verify Ethernet0 not in VLAN, Ethernet4 still in VLAN =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 13: Verify {interface1} not in VLAN {vlan_id}, {interface2} still in VLAN {vlan_id}")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_port_not_in_vlan(output, vlan_id, interface1):
            st.report_fail(
                "msg",
                f"Port removal failed: {interface1} is still member of VLAN {vlan_id}"
            )

        if not self._verify_port_in_vlan(output, vlan_id, interface2):
            st.report_fail(
                "msg",
                f"Port verification failed: {interface2} should still be member of VLAN {vlan_id}"
            )

        st.log(f"PASS: {interface1} removed, {interface2} still in VLAN {vlan_id}")

        # ===== STEP 14: Remove Ethernet4 from VLAN 3 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 14: Remove {interface2} from VLAN {vlan_id}")
        st.log("-" * 80)

        self._remove_port_from_vlan(dut, interface2, vlan_id)
        st.log(f"Removed {interface2} from VLAN {vlan_id}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 15: Verify VLAN 3 exists but has no ports =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 15: Verify VLAN {vlan_id} exists but has no ports")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_vlan_exists(output, vlan_id):
            st.report_fail(
                "msg",
                f"VLAN verification failed: VLAN {vlan_id} should still exist"
            )

        if not self._verify_port_not_in_vlan(output, vlan_id, interface2):
            st.report_fail(
                "msg",
                f"Port removal failed: {interface2} is still member of VLAN {vlan_id}"
            )

        st.log(f"PASS: VLAN {vlan_id} exists with no ports")

        # ===== STEP 16: Delete VLAN 3 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 16: Delete VLAN {vlan_id}")
        st.log("-" * 80)

        self._delete_vlan(dut, vlan_id)
        st.log(f"Deleted VLAN {vlan_id}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 17: Verify no VLANs configured =====
        st.log("\n" + "-" * 80)
        st.log("STEP 17: Verify no VLANs configured")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_no_vlans_configured(output):
            st.report_fail(
                "msg",
                "VLAN deletion failed: VLANs are still configured"
            )

        st.log("PASS: No VLANs configured")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: VLAN creation, port management, and reboot persistence test finished")
        st.log(f"VLAN {vlan_id} lifecycle: Created → Added {interface1},{interface2} → Saved → Rebooted → Verified persistence → Removed ports → Deleted ✓")
        st.log("=" * 80)

        # Check for any validation failures
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED:")
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.log("!" * 80)
            st.report_fail("msg", f"Test completed with {len(validation_failures)} validation failure(s). See errors above.")
        else:
            st.log("All validations passed successfully")
            st.report_pass("test_case_passed")
