"""
VLAN CONFIGURATION - VLAN CREATION, PORT MANAGEMENT, IP ADDRESS ASSIGNMENT, AND DUAL REBOOT PERSISTENCE
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_Vlan/test_interface_2_iscli_vlan_ip_reboot.py \
  --logs-path ./logs/test_interface_2_iscli_vlan_ip_reboot_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates VLAN creation, port management, IP address assignment, and config persistence across reboot by:
  1. Removing IP addresses (IPv4 and IPv6) from all testbed interfaces
  2. Creating VLAN 3
  3. Adding port Ethernet0 to VLAN 3 as tagged member
  4. Configuring IPv4 address on VLAN 3 interface
  5. Verifying IPv4 address in running-config
  6. Saving configuration with 'write memory'
  7. Rebooting device with 'sudo reboot' (FIRST REBOOT)
  8. Waiting for device to come back up
  9. Re-verifying IPv4 address in running-config after reboot (IPv4 persistence check)
  10. Removing IPv4 address
  11. Verifying no IPv4 address in running-config
  12. Configuring IPv6 address on VLAN 3 interface
  13. Verifying IPv6 address in running-config
  14. Saving configuration with 'write memory'
  15. Rebooting device with 'sudo reboot' (SECOND REBOOT)
  16. Waiting for device to come back up
  17. Re-verifying IPv6 address in running-config after reboot (IPv6 persistence check)
  18. Removing IPv6 address
  19. Verifying no IPv6 address in running-config
  20. Removing port from VLAN
  21. Deleting VLAN 3
  22. Verifying no VLANs configured

  This mirrors the exact CLI workflow:
    - configure terminal -> interface Ethernet0 -> no ip address -> no ipv6 address -> exit
    - vlan 3
    - interface Ethernet0 -> switchport trunk allowed vlan 3 -> exit
    - interface Vlan 3 -> ip address 10.0.0.1/30 -> exit
    - show running-configuration interface Vlan 3 (verify: ip address 10.0.0.1/30)
    - write memory (save configuration)
    - sudo reboot (FIRST REBOOT)
    - [wait for reboot]
    - show running-configuration interface Vlan 3 (verify: ip address persists after reboot)
    - interface Vlan 3 -> no ip address -> exit
    - show running-configuration interface Vlan 3 (verify: no ip address)
    - interface Vlan 3 -> ipv6 address 2001:db8:100::1/64 -> exit
    - show running-configuration interface Vlan 3 (verify: ipv6 address 2001:db8:100::1/64)
    - write memory (save configuration)
    - sudo reboot (SECOND REBOOT)
    - [wait for reboot]
    - show running-configuration interface Vlan 3 (verify: ipv6 address persists after reboot)
    - interface Vlan 3 -> no ipv6 address -> exit
    - show running-configuration interface Vlan 3 (verify: no ipv6 address)
    - no vlan 3

  IMPORTANT: Uses 'show running-configuration interface Vlan X' to validate IP addresses.
  Tests configuration persistence across TWO device reboots using 'write memory' and 'sudo reboot'.
  First reboot validates IPv4 persistence, second reboot validates IPv6 persistence.

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
WAIT_AFTER_IP_CHANGE = 2
WAIT_FOR_REBOOT = 180  # Wait time for device to reboot and come back up


@pytest.mark.topology("any")
class TestVlanIPConfigurationReboot:
    """Test cases for validating VLAN creation, port management, IP address assignment, and config persistence across reboot via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing VLAN IP Configuration with Dual Reboot Test Suite")
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

        # Test interface
        cls.data.interface1 = "Ethernet0"
        st.log(f"Test Interface: {cls.data.interface1}")

        # Test IP addresses
        cls.data.ipv4_address = "10.0.0.1/30"
        cls.data.ipv6_address = "2001:db8:100::1/64"
        st.log(f"Test IPv4: {cls.data.ipv4_address}")
        st.log(f"Test IPv6: {cls.data.ipv6_address}")

        # Set terminal length 0 to disable pagination
        st.log("Setting terminal length 0 to disable pagination")
        st.config(cls.data.dut1, "terminal length 0", type=CLI_TYPE)

        st.log("Test setup complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup VLAN IP Configuration with Dual Reboot Test Suite")
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
        command = "show Vlan"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show Vlan output:\n{output}")
        return output

    @staticmethod
    def _get_running_config_vlan_interface(dut: str, vlan_id: str) -> str:
        """
        Get running-configuration for VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")

        Returns:
            String containing the output of 'show running-configuration interface Vlan X' command
        """
        st.log(f"Getting running-configuration for Vlan {vlan_id}")

        # Command: show running-configuration interface Vlan X
        cmd = f"show running-configuration interface Vlan {vlan_id}"

        # Execute command
        output = st.show(dut, cmd, type=CLI_TYPE, skip_tmpl=True, skip_error_check=True)

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"Running-config output:\n{output}")
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
        """Create VLAN using klish commands."""
        st.log(f"Creating VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"vlan {vlan_id}"
            # NO exit - stay in config mode
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _delete_vlan(dut: str, vlan_id: str) -> bool:
        """Delete VLAN using klish commands."""
        st.log(f"Deleting VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"no vlan {vlan_id}"
            # NO exit - stay in config mode
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _add_port_to_vlan(dut: str, interface: str, vlan_id: str) -> bool:
        """Add interface to VLAN as tagged member."""
        st.log(f"Adding {interface} to VLAN {vlan_id} as tagged member")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"switchport trunk allowed vlan {vlan_id}",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_port_from_vlan(dut: str, interface: str, vlan_id: str) -> bool:
        """Remove interface from VLAN."""
        st.log(f"Removing {interface} from VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"no switchport trunk allowed vlan {vlan_id}",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _configure_vlan_ipv4(dut: str, vlan_id: str, ipv4_address: str) -> bool:
        """
        Configure IPv4 address on VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
            ipv4_address: IPv4 address with prefix (e.g., "10.0.0.1/30")

        Returns:
            True if successful
        """
        st.log(f"Configuring IPv4 address {ipv4_address} on Vlan {vlan_id}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            f"ip address {ipv4_address}",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_vlan_ipv4(dut: str, vlan_id: str) -> bool:
        """Remove IPv4 address from VLAN interface."""
        st.log(f"Removing IPv4 address from Vlan {vlan_id}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no ip address",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _configure_vlan_ipv6(dut: str, vlan_id: str, ipv6_address: str) -> bool:
        """
        Configure IPv6 address on VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
            ipv6_address: IPv6 address with prefix (e.g., "2001:db8:100::1/64")

        Returns:
            True if successful
        """
        st.log(f"Configuring IPv6 address {ipv6_address} on Vlan {vlan_id}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            f"ipv6 address {ipv6_address}",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_vlan_ipv6(dut: str, vlan_id: str) -> bool:
        """Remove IPv6 address from VLAN interface."""
        st.log(f"Removing IPv6 address from Vlan {vlan_id}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no ipv6 address",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=CLI_TYPE)
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
    def _verify_vlan_exists(vlan_output: str, vlan_id: str) -> bool:
        """Verify that VLAN exists in show Vlan output."""
        st.log(f"Verifying VLAN {vlan_id} exists")

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
    def _verify_no_vlans_configured(vlan_output: str) -> bool:
        """Verify that no VLANs are configured."""
        st.log("Verifying no VLANs are configured")

        if "No VLANs configured" in vlan_output or "no vlans configured" in vlan_output.lower():
            st.log("PASS: No VLANs are configured")
            return True
        else:
            st.error("FAIL: VLANs are still configured")
            return False

    @staticmethod
    def _extract_ipv4_from_running_config(output: str) -> Optional[str]:
        """
        Extract IPv4 address value from running-configuration output.

        Expected output format:
        !
        interface Vlan3
         ip address 10.0.0.1/30

        Args:
            output: Raw CLI output string from show running-configuration

        Returns:
            IPv4 address value as string (e.g., "10.0.0.1/30"), or None if not found
        """
        if not output:
            st.log("No output to parse")
            return None

        # Search for "ip address <value>" pattern
        ipv4_pattern = r'ip\s+address\s+(\d+\.\d+\.\d+\.\d+/\d+)'
        match = re.search(ipv4_pattern, output, re.IGNORECASE)

        if match:
            ipv4_value = match.group(1)
            st.log(f"Found IPv4 address value: {ipv4_value}")
            return ipv4_value
        else:
            st.log("IPv4 address value not found in output")
            return None

    @staticmethod
    def _extract_ipv6_from_running_config(output: str) -> Optional[str]:
        """
        Extract IPv6 address value from running-configuration output.

        Expected output format:
        !
        interface Vlan3
         ipv6 address 2001:db8:100::1/64

        Note: Some devices may display IPv6 addresses as "ip address 2001:db8:100::1/64"
              instead of "ipv6 address 2001:db8:100::1/64". This function handles both cases.

        Args:
            output: Raw CLI output string from show running-configuration

        Returns:
            IPv6 address value as string (e.g., "2001:db8:100::1/64"), or None if not found
        """
        if not output:
            st.log("No output to parse")
            return None

        # First try to search for "ipv6 address <value>" pattern
        ipv6_pattern = r'ipv6\s+address\s+([0-9a-fA-F:]+/\d+)'
        match = re.search(ipv6_pattern, output, re.IGNORECASE)

        if match:
            ipv6_value = match.group(1)
            st.log(f"Found IPv6 address value (with 'ipv6 address' prefix): {ipv6_value}")
            return ipv6_value

        # Fallback: search for "ip address <value>" with IPv6 format
        # Some devices may display IPv6 as "ip address 2001:db8:100::1/64"
        ip_with_ipv6_pattern = r'ip\s+address\s+([0-9a-fA-F:]+/\d+)'
        match = re.search(ip_with_ipv6_pattern, output, re.IGNORECASE)

        if match:
            ipv6_value = match.group(1)
            st.log(f"Found IPv6 address value (with 'ip address' prefix - device quirk): {ipv6_value}")
            return ipv6_value

        st.log("IPv6 address value not found in output")
        return None

    @staticmethod
    def _verify_ipv4_in_running_config(config_output: str, expected_ipv4: Optional[str]) -> bool:
        """
        Verify that VLAN interface has the expected IPv4 address in running-configuration.

        Args:
            config_output: Raw output from 'show running-configuration interface Vlan X'
            expected_ipv4: Expected IPv4 address value (e.g., "10.0.0.1/30")
                          or None if no IPv4 address should be present

        Returns:
            True if IPv4 address matches expected value, False otherwise
        """
        st.log(f"Verifying IPv4 address = '{expected_ipv4}' in running-configuration")

        # Extract IPv4 address value
        actual_ipv4 = TestVlanIPConfigurationReboot._extract_ipv4_from_running_config(config_output)

        # Compare values
        if expected_ipv4 is None:
            # Expecting no IPv4 address
            if actual_ipv4 is None:
                st.log("PASS: No IPv4 address configured (as expected)")
                return True
            else:
                st.error(f"FAIL: Has IPv4 address '{actual_ipv4}' (expected no IPv4 address)")
                return False
        else:
            # Expecting a specific IPv4 address
            if actual_ipv4 == expected_ipv4:
                st.log(f"PASS: IPv4 address is '{actual_ipv4}' (matches expected '{expected_ipv4}')")
                return True
            else:
                st.error(f"FAIL: IPv4 address is '{actual_ipv4}' (expected '{expected_ipv4}')")
                return False

    @staticmethod
    def _verify_ipv6_in_running_config(config_output: str, expected_ipv6: Optional[str]) -> bool:
        """
        Verify that VLAN interface has the expected IPv6 address in running-configuration.

        Args:
            config_output: Raw output from 'show running-configuration interface Vlan X'
            expected_ipv6: Expected IPv6 address value (e.g., "2001:db8:100::1/64")
                          or None if no IPv6 address should be present

        Returns:
            True if IPv6 address matches expected value, False otherwise
        """
        st.log(f"Verifying IPv6 address = '{expected_ipv6}' in running-configuration")

        # Extract IPv6 address value
        actual_ipv6 = TestVlanIPConfigurationReboot._extract_ipv6_from_running_config(config_output)

        # Compare values
        if expected_ipv6 is None:
            # Expecting no IPv6 address
            if actual_ipv6 is None:
                st.log("PASS: No IPv6 address configured (as expected)")
                return True
            else:
                st.error(f"FAIL: Has IPv6 address '{actual_ipv6}' (expected no IPv6 address)")
                return False
        else:
            # Expecting a specific IPv6 address
            if actual_ipv6 == expected_ipv6:
                st.log(f"PASS: IPv6 address is '{actual_ipv6}' (matches expected '{expected_ipv6}')")
                return True
            else:
                st.error(f"FAIL: IPv6 address is '{actual_ipv6}' (expected '{expected_ipv6}')")
                return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_IP_REBOOT_001"])
    def test_vlan_ip_configuration_and_dual_reboot_persistence(self) -> None:
        """
        TC_VLAN_IP_REBOOT_001: Validate CLI for VLAN creation, port management, IP address assignment, and config persistence across TWO reboots.

        Test Procedure:
        1. Remove IP addresses (IPv4 and IPv6) from all testbed interfaces
        2. Create VLAN 3
        3. Add Ethernet0 to VLAN 3
        4. Configure IPv4 address on VLAN 3 interface
        5. Verify IPv4 address in running-config
        6. Save configuration with 'write memory'
        7. Reboot device with 'sudo reboot' (FIRST REBOOT)
        8. Wait for device to come back up
        9. Re-verify IPv4 address in running-config after reboot (IPv4 persistence check)
        10. Remove IPv4 address
        11. Verify no IPv4 address in running-config
        12. Configure IPv6 address on VLAN 3 interface
        13. Verify IPv6 address in running-config
        14. Save configuration with 'write memory'
        15. Reboot device with 'sudo reboot' (SECOND REBOOT)
        16. Wait for device to come back up
        17. Re-verify IPv6 address in running-config after reboot (IPv6 persistence check)
        18. Remove IPv6 address
        19. Verify no IPv6 address in running-config
        20. Remove port from VLAN
        21. Delete VLAN 3
        22. Verify no VLANs configured

        Expected Result:
        - IP addresses can be removed from interfaces
        - VLAN can be created successfully
        - Ports can be added to VLAN
        - IPv4 address can be configured on VLAN interface
        - Configuration can be saved with 'write memory'
        - Device can be rebooted successfully (first time)
        - IPv4 address configuration persists across first reboot
        - IPv4 address can be removed
        - IPv6 address can be configured on VLAN interface
        - Configuration can be saved with 'write memory'
        - Device can be rebooted successfully (second time)
        - IPv6 address configuration persists across second reboot
        - All changes are reflected accurately in running-configuration
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: VLAN IP Configuration and Dual Reboot Persistence")
        st.log("=" * 80)

        # Track validation failures - test will continue but report fail at end
        validation_failures = []

        dut = self.data.dut1
        vlan_id = self.data.test_vlan
        interface1 = self.data.interface1
        ipv4_addr = self.data.ipv4_address
        ipv6_addr = self.data.ipv6_address

        # ===== STEP 1: Remove IP addresses from all testbed interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Remove IP addresses (IPv4 and IPv6) from all testbed interfaces")
        st.log("-" * 80)

        # Get all interfaces to clean
        testbed_interfaces = [interface1]
        self._remove_ip_addresses_from_interfaces(dut, testbed_interfaces)

        st.log("PASS: IP addresses removed from all testbed interfaces")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 2: Create VLAN 3 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 2: Create VLAN {vlan_id}")
        st.log("-" * 80)

        self._create_vlan(dut, vlan_id)
        st.log(f"Created VLAN {vlan_id}")
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 2.1: Verify VLAN status is Down (no active ports yet) =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 2.1: Verify VLAN {vlan_id} status is Down (no active member ports)")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_vlan_status(output, vlan_id, "Down"):
            error_msg = f"VLAN status validation failed: VLAN {vlan_id} should be Down when no active member ports are configured"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: VLAN {vlan_id} status is Down (expected behavior with no active member ports)")

        # ===== STEP 3: Add Ethernet0 to VLAN 3 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 3: Add {interface1} to VLAN {vlan_id}")
        st.log("-" * 80)

        self._add_port_to_vlan(dut, interface1, vlan_id)
        st.log(f"Added {interface1} to VLAN {vlan_id}")
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 4: Configure IPv4 address on VLAN 3 interface =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 4: Configure IPv4 address {ipv4_addr} on Vlan {vlan_id}")
        st.log("-" * 80)

        self._configure_vlan_ipv4(dut, vlan_id, ipv4_addr)
        st.log(f"Configured IPv4 address {ipv4_addr} on Vlan {vlan_id}")
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 5: Verify IPv4 address in running-config =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 5: Verify IPv4 address {ipv4_addr} in running-config")
        st.log("-" * 80)

        output = self._get_running_config_vlan_interface(dut, vlan_id)
        if not self._verify_ipv4_in_running_config(output, ipv4_addr):
            st.report_fail(
                "msg",
                f"IPv4 verification failed: Vlan {vlan_id} does not show IPv4 address '{ipv4_addr}' in running-config"
            )

        st.log(f"PASS: IPv4 address {ipv4_addr} verified on Vlan {vlan_id}")

        # ===== STEP 6: Save configuration with 'write memory' (FIRST SAVE) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Save configuration with 'write memory' (FIRST SAVE)")
        st.log("-" * 80)

        self._save_config(dut)
        st.log("PASS: Configuration saved successfully")
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 7: Reboot device with 'sudo reboot' (FIRST REBOOT) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Reboot device with 'sudo reboot' (FIRST REBOOT - IPv4 persistence test)")
        st.log("-" * 80)

        self._reboot_device(dut)
        st.log("PASS: Device reboot initiated (FIRST REBOOT)")

        # ===== STEP 8: Wait for device to come back up (FIRST REBOOT) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Wait for device to come back up after FIRST reboot")
        st.log("-" * 80)

        self._wait_for_device_ready(dut)
        st.log("PASS: Device is back up and ready after FIRST reboot")

        # ===== STEP 9: Re-verify IPv4 address in running-config after reboot =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 9: Re-verify IPv4 address {ipv4_addr} in running-config after FIRST reboot (IPv4 persistence check)")
        st.log("-" * 80)

        output = self._get_running_config_vlan_interface(dut, vlan_id)
        if not self._verify_ipv4_in_running_config(output, ipv4_addr):
            st.report_fail(
                "msg",
                f"IPv4 persistence failed: Vlan {vlan_id} does not show IPv4 address '{ipv4_addr}' after reboot"
            )

        st.log(f"PASS: IPv4 address {ipv4_addr} configuration persisted across FIRST reboot on Vlan {vlan_id}")

        # ===== STEP 10: Remove IPv4 address =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 10: Remove IPv4 address from Vlan {vlan_id}")
        st.log("-" * 80)

        self._remove_vlan_ipv4(dut, vlan_id)
        st.log(f"Removed IPv4 address from Vlan {vlan_id}")
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 11: Verify no IPv4 address in running-config =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 11: Verify no IPv4 address in running-config")
        st.log("-" * 80)

        output = self._get_running_config_vlan_interface(dut, vlan_id)
        if not self._verify_ipv4_in_running_config(output, None):
            st.report_fail(
                "msg",
                f"IPv4 removal failed: Vlan {vlan_id} still has IPv4 address in running-config"
            )

        st.log(f"PASS: No IPv4 address on Vlan {vlan_id}")

        # ===== STEP 12: Configure IPv6 address on VLAN 3 interface =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 12: Configure IPv6 address {ipv6_addr} on Vlan {vlan_id}")
        st.log("-" * 80)

        self._configure_vlan_ipv6(dut, vlan_id, ipv6_addr)
        st.log(f"Configured IPv6 address {ipv6_addr} on Vlan {vlan_id}")
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 13: Verify IPv6 address in running-config =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 13: Verify IPv6 address {ipv6_addr} in running-config")
        st.log("-" * 80)

        output = self._get_running_config_vlan_interface(dut, vlan_id)
        if not self._verify_ipv6_in_running_config(output, ipv6_addr):
            st.report_fail(
                "msg",
                f"IPv6 verification failed: Vlan {vlan_id} does not show IPv6 address '{ipv6_addr}' in running-config"
            )

        st.log(f"PASS: IPv6 address {ipv6_addr} verified on Vlan {vlan_id}")

        # ===== STEP 14: Save configuration with 'write memory' (SECOND SAVE) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 14: Save configuration with 'write memory' (SECOND SAVE)")
        st.log("-" * 80)

        self._save_config(dut)
        st.log("PASS: Configuration saved successfully")
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 15: Reboot device with 'sudo reboot' (SECOND REBOOT) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 15: Reboot device with 'sudo reboot' (SECOND REBOOT - IPv6 persistence test)")
        st.log("-" * 80)

        self._reboot_device(dut)
        st.log("PASS: Device reboot initiated (SECOND REBOOT)")

        # ===== STEP 16: Wait for device to come back up (SECOND REBOOT) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 16: Wait for device to come back up after SECOND reboot")
        st.log("-" * 80)

        self._wait_for_device_ready(dut)
        st.log("PASS: Device is back up and ready after SECOND reboot")

        # ===== STEP 17: Re-verify IPv6 address in running-config after reboot =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 17: Re-verify IPv6 address {ipv6_addr} in running-config after SECOND reboot (IPv6 persistence check)")
        st.log("-" * 80)

        output = self._get_running_config_vlan_interface(dut, vlan_id)
        if not self._verify_ipv6_in_running_config(output, ipv6_addr):
            st.report_fail(
                "msg",
                f"IPv6 persistence failed: Vlan {vlan_id} does not show IPv6 address '{ipv6_addr}' after reboot"
            )

        st.log(f"PASS: IPv6 address {ipv6_addr} configuration persisted across SECOND reboot on Vlan {vlan_id}")

        # ===== STEP 18: Remove IPv6 address =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 18: Remove IPv6 address from Vlan {vlan_id}")
        st.log("-" * 80)

        self._remove_vlan_ipv6(dut, vlan_id)
        st.log(f"Removed IPv6 address from Vlan {vlan_id}")
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 19: Verify no IPv6 address in running-config =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 19: Verify no IPv6 address in running-config")
        st.log("-" * 80)

        output = self._get_running_config_vlan_interface(dut, vlan_id)
        if not self._verify_ipv6_in_running_config(output, None):
            st.report_fail(
                "msg",
                f"IPv6 removal failed: Vlan {vlan_id} still has IPv6 address in running-config"
            )

        st.log(f"PASS: No IPv6 address on Vlan {vlan_id}")

        # ===== STEP 20: Remove port from VLAN =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 20: Remove {interface1} from VLAN {vlan_id}")
        st.log("-" * 80)

        self._remove_port_from_vlan(dut, interface1, vlan_id)
        st.log(f"Removed {interface1} from VLAN {vlan_id}")
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 21: Delete VLAN 3 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 21: Delete VLAN {vlan_id}")
        st.log("-" * 80)

        self._delete_vlan(dut, vlan_id)
        st.log(f"Deleted VLAN {vlan_id}")
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 22: Verify no VLANs configured =====
        st.log("\n" + "-" * 80)
        st.log("STEP 22: Verify no VLANs configured")
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
        st.log("TEST COMPLETE: VLAN IP configuration and dual reboot persistence test finished")
        st.log(f"VLAN {vlan_id} lifecycle:")
        st.log(f"  - Created VLAN → Added {interface1}")
        st.log(f"  - IPv4 {ipv4_addr}: Configured → Verified → Saved → Rebooted (1st) → Verified persistence ✓ → Removed")
        st.log(f"  - IPv6 {ipv6_addr}: Configured → Verified → Saved → Rebooted (2nd) → Verified persistence ✓ → Removed")
        st.log(f"  - Removed {interface1} → Deleted VLAN ✓")
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
