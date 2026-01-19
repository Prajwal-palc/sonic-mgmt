"""
VLAN CONFIGURATION - VLAN CREATION, PORT MANAGEMENT, AND IP ADDRESS ASSIGNMENT (HARDWARE - DYNAMIC TESTBED)
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs_hardware.yaml \
  tests/system/iscli_Hardware/test_interface_2_iscli_vlan_ip_HW.py \
  --logs-path ./logs/test_interface_2_iscli_vlan_ip_HW_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates VLAN creation, port management, and IP address assignment by:
  1. Dynamically getting the first interface from testbed
  2. Removing IP addresses (IPv4 and IPv6) from the first interface
  3. Creating VLAN 3
  4. Adding the first interface to VLAN 3 as tagged member
  5. Configuring IPv4 address on VLAN 3 interface
  6. Verifying IPv4 address in running-config
  7. Removing IPv4 address
  8. Configuring IPv6 address on VLAN 3 interface
  9. Verifying IPv6 address in running-config
  10. Removing IPv6 address
  11. Removing port from VLAN
  12. Deleting VLAN 3

  This mirrors the exact CLI workflow:
    - configure terminal -> interface Ethernet X -> no ip address -> no ipv6 address -> exit
    - vlan 3
    - interface Ethernet X -> switchport trunk allowed vlan 3 -> exit
    - interface Vlan 3 -> ip address 10.0.0.1/30 -> exit
    - show running-configuration interface Vlan 3 (verify: ip address 10.0.0.1/30)
    - interface Vlan 3 -> no ip address -> exit
    - show running-configuration interface Vlan 3 (verify: no ip address)
    - interface Vlan 3 -> ipv6 address 2001:db8:100::1/64 -> exit
    - show running-configuration interface Vlan 3 (verify: ipv6 address 2001:db8:100::1/64)
    - interface Vlan 3 -> no ipv6 address -> exit
    - show running-configuration interface Vlan 3 (verify: no ipv6 address)
    - no vlan 3

  IMPORTANT: Uses 'show running-configuration interface Vlan X' to validate IP addresses.

  This hardware-focused version dynamically retrieves the FIRST device from the testbed
  and the FIRST interface from that device's topology links, making it portable across
  different testbed configurations without hardcoding interface names.

Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - Dynamic (uses first DUT and first interface from testbed)
        # +--------------------+
        # |       DUT1         |
        # | (First device)     |<-----First Interface from topology
        # |                    |      (Member of VLAN 3)
        # |  Vlan3: 10.0.0.1/30|
        # |  Vlan3: 2001:db8:100::1/64
        # +--------------------+
  - Access to sonic-cli (klish mode)
  - Required test variables: CLI type (klish)
  - Minimum 1 interface available in testbed topology
"""

from __future__ import annotations

import pytest
import time
import re
from typing import Dict, Any, List, Optional

from spytest import st
from spytest.dicts import SpyTestDict


# CLI type for all operations
CLI_TYPE = "klish"

# Wait times
WAIT_AFTER_VLAN_CHANGE = 2
WAIT_AFTER_IP_CHANGE = 2


@pytest.mark.topology("any")
class TestVlanIPConfigurationHW:
    """Test cases for validating VLAN creation, port management, and IP address assignment via CLI (klish mode) on hardware."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters dynamically from testbed."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing VLAN IP Configuration Test Suite (Hardware)")
        st.log("=" * 80)

        # Get DUT handles - use FIRST device from testbed
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs available in topology")

        # Use FIRST device from testbed
        cls.data.dut1 = cls.data.dut_names[0]
        st.log(f"Primary DUT (First device from testbed): {cls.data.dut1}")

        # CLI type - use klish as specified
        cls.data.cli_type = CLI_TYPE
        st.log(f"CLI Type: {cls.data.cli_type}")

        # Test VLAN ID
        cls.data.test_vlan = "3"
        st.log(f"Test VLAN: {cls.data.test_vlan}")

        # Get FIRST interface from testbed topology dynamically
        cls.data.test_interface = cls._get_first_interface_from_testbed()
        st.log(f"Test Interface (First from testbed): {cls.data.test_interface}")

        # Test IP addresses
        cls.data.ipv4_address = "10.0.0.1/30"
        cls.data.ipv6_address = "2001:db8:100::1/64"
        st.log(f"Test IPv4: {cls.data.ipv4_address}")
        st.log(f"Test IPv6: {cls.data.ipv6_address}")

        st.log("Test setup complete")

    @classmethod
    def _get_first_interface_from_testbed(cls) -> str:
        """
        Dynamically retrieve the FIRST interface from the testbed topology.

        This method queries the testbed topology to find the first available
        interface on the primary DUT, making the test portable across different
        testbed configurations.

        Returns:
            str: First interface name (e.g., "Ethernet0")

        Raises:
            Failure if no interfaces found in testbed
        """
        try:
            # Method 1: Try to get DUT links (interfaces connected to other DUTs)
            dut_links = st.get_dut_links(cls.data.dut1)
            st.log(f"DUT links retrieved: {dut_links}")

            if dut_links and len(dut_links) > 0:
                # dut_links returns a list of links, each link is a list [local_port, remote_dut, remote_port]
                # We need to extract just the local port (first element)
                first_link = dut_links[0]

                # Handle different possible formats
                if isinstance(first_link, (list, tuple)) and len(first_link) > 0:
                    first_interface = str(first_link[0])  # Get local interface (first element)
                else:
                    first_interface = str(first_link)

                st.log(f"Found first interface from DUT links: {first_interface}")
                return first_interface

        except Exception as e:
            st.log(f"Note: Could not get DUT links: {str(e)}")

        try:
            # Method 2: Try to get all free ports
            free_ports = st.get_free_ports(cls.data.dut1)
            st.log(f"Free ports retrieved: {free_ports}")

            if free_ports and len(free_ports) > 0:
                first_interface = str(free_ports[0])
                st.log(f"Found first interface from free ports: {first_interface}")
                return first_interface

        except Exception as e:
            st.log(f"Note: Could not get free ports: {str(e)}")

        try:
            # Method 3: Try to get TG links (traffic generator links)
            tg_links = st.get_tg_links(cls.data.dut1)
            st.log(f"TG links retrieved: {tg_links}")

            if tg_links and len(tg_links) > 0:
                # Get the first TG link's DUT-side interface
                first_link = tg_links[0]
                # TG links are typically tuples/lists: (dut, interface)
                if isinstance(first_link, (list, tuple)) and len(first_link) >= 2:
                    first_interface = str(first_link[1])
                else:
                    first_interface = str(first_link)
                st.log(f"Found first interface from TG links: {first_interface}")
                return first_interface

        except Exception as e:
            st.log(f"Note: Could not get TG links: {str(e)}")

        # Fallback: If all methods fail, use default Ethernet0
        st.log("Warning: Could not dynamically retrieve interface from testbed")
        st.log("Falling back to default: Ethernet0")
        return "Ethernet0"

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite - ensure VLAN is deleted."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup VLAN IP Configuration Test Suite")
        st.log("=" * 80)

        try:
            # Try to remove port from VLAN
            cls._remove_port_from_vlan_static(cls.data.dut1, cls.data.test_interface, cls.data.test_vlan)
        except Exception as e:
            st.log(f"Note: Port cleanup: {str(e)}")

        try:
            # Try to delete test VLAN if it exists
            cls._delete_vlan_static(cls.data.dut1, cls.data.test_vlan)
            st.log(f"Cleaned up VLAN {cls.data.test_vlan}")
        except Exception as e:
            st.log(f"Note: VLAN cleanup: {str(e)}")

        st.log("Cleanup completed")

    @classmethod
    def _remove_port_from_vlan_static(cls, dut: str, interface: str, vlan_id: str) -> None:
        """
        Static helper to remove port from VLAN during teardown.

        Args:
            dut: Device handle
            interface: Interface name
            vlan_id: VLAN ID
        """
        try:
            commands = [
                "configure terminal",
                f"interface {interface}",
                f"no switchport trunk allowed vlan {vlan_id}",
                "exit"
            ]
            st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
            time.sleep(1)
        except Exception as e:
            st.log(f"Warning: Failed to remove port from VLAN: {str(e)}")

    @classmethod
    def _delete_vlan_static(cls, dut: str, vlan_id: str) -> None:
        """
        Static helper to delete VLAN during teardown.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
        """
        try:
            commands = [
                "configure terminal",
                f"no vlan {vlan_id}"
            ]
            st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
            time.sleep(1)
        except Exception as e:
            st.log(f"Warning: Failed to delete VLAN {vlan_id}: {str(e)}")

    def setup_method(self) -> None:
        """Setup before each test method."""
        st.log("-" * 80)
        st.log("SETUP METHOD: Starting new test case")
        st.log("-" * 80)

    def teardown_method(self) -> None:
        """Teardown after each test method - ensure VLAN is deleted."""
        st.log("-" * 80)
        st.log("TEARDOWN METHOD: Cleaning up test case")
        st.log("-" * 80)

        try:
            # Remove interface from VLAN if still member
            self._remove_port_from_vlan(self.data.dut1, self.data.test_interface, self.data.test_vlan)
        except Exception as e:
            st.log(f"Note: Port cleanup: {str(e)}")

        try:
            # Delete VLAN if it exists
            self._delete_vlan(self.data.dut1, self.data.test_vlan)
        except Exception as e:
            st.log(f"Note: VLAN cleanup: {str(e)}")

    def _get_show_vlan_output(self, dut: str) -> str:
        """
        Get 'show Vlan' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log("Getting 'show Vlan' output")
        command = "show Vlan"
        output = st.show(dut, command, type=self.data.cli_type, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show Vlan output:\n{output}")
        return output

    def _get_running_config_vlan_interface(self, dut: str, vlan_id: str) -> str:
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
        output = st.show(dut, cmd, type=self.data.cli_type, skip_tmpl=True, skip_error_check=True)

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"Running-config output:\n{output}")
        return output

    def _remove_ip_addresses_from_interface(self, dut: str, interface: str) -> None:
        """
        Remove IPv4 and IPv6 addresses from specified interface.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
        """
        st.log(f"Removing IP addresses from {interface}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip address",
            "no ipv6 address",
            "exit"  # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)
        st.log(f"IP addresses removed from {interface}")

    def _create_vlan(self, dut: str, vlan_id: str) -> None:
        """
        Create VLAN using klish commands.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
        """
        st.log(f"Creating VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"vlan {vlan_id}"
            # NO exit - stay in config mode
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _delete_vlan(self, dut: str, vlan_id: str) -> None:
        """
        Delete VLAN using klish commands.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
        """
        st.log(f"Deleting VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"no vlan {vlan_id}"
            # NO exit - stay in config mode
        ]
        st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)

    def _add_port_to_vlan(self, dut: str, interface: str, vlan_id: str) -> None:
        """
        Add interface to VLAN as tagged member using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            vlan_id: VLAN ID (e.g., "3")
        """
        st.log(f"Adding {interface} to VLAN {vlan_id} as tagged member")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"switchport trunk allowed vlan {vlan_id}",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _remove_port_from_vlan(self, dut: str, interface: str, vlan_id: str) -> None:
        """
        Remove interface from VLAN using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            vlan_id: VLAN ID (e.g., "3")
        """
        st.log(f"Removing {interface} from VLAN {vlan_id}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"no switchport trunk allowed vlan {vlan_id}",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)

    def _configure_vlan_ipv4(self, dut: str, vlan_id: str, ipv4_address: str) -> None:
        """
        Configure IPv4 address on VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
            ipv4_address: IPv4 address with prefix (e.g., "10.0.0.1/30")
        """
        st.log(f"Configuring IPv4 address {ipv4_address} on Vlan {vlan_id}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            f"ip address {ipv4_address}",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _remove_vlan_ipv4(self, dut: str, vlan_id: str) -> None:
        """
        Remove IPv4 address from VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
        """
        st.log(f"Removing IPv4 address from Vlan {vlan_id}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no ip address",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _configure_vlan_ipv6(self, dut: str, vlan_id: str, ipv6_address: str) -> None:
        """
        Configure IPv6 address on VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
            ipv6_address: IPv6 address with prefix (e.g., "2001:db8:100::1/64")
        """
        st.log(f"Configuring IPv6 address {ipv6_address} on Vlan {vlan_id}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            f"ipv6 address {ipv6_address}",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _remove_vlan_ipv6(self, dut: str, vlan_id: str) -> None:
        """
        Remove IPv6 address from VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "3")
        """
        st.log(f"Removing IPv6 address from Vlan {vlan_id}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no ipv6 address",
            "exit"   # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _verify_vlan_exists(self, vlan_output: str, vlan_id: str) -> bool:
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

    def _verify_vlan_status(self, vlan_output: str, vlan_id: str, expected_status: str) -> bool:
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

    def _verify_no_vlans_configured(self, vlan_output: str) -> bool:
        """
        Verify that no VLANs are configured.

        Args:
            vlan_output: Raw output from 'show Vlan' command

        Returns:
            True if no VLANs are configured, False otherwise
        """
        st.log("Verifying no VLANs are configured")

        if "No VLANs configured" in vlan_output or "no vlans configured" in vlan_output.lower():
            st.log("PASS: No VLANs are configured")
            return True
        else:
            st.error("FAIL: VLANs are still configured")
            return False

    def _extract_ipv4_from_running_config(self, output: str) -> Optional[str]:
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

    def _extract_ipv6_from_running_config(self, output: str) -> Optional[str]:
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

    def _verify_ipv4_in_running_config(self, config_output: str, expected_ipv4: Optional[str]) -> bool:
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
        actual_ipv4 = self._extract_ipv4_from_running_config(config_output)

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

    def _verify_ipv6_in_running_config(self, config_output: str, expected_ipv6: Optional[str]) -> bool:
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
        actual_ipv6 = self._extract_ipv6_from_running_config(config_output)

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

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_IP_001_HW"])
    def test_vlan_ip_configuration(self) -> None:
        """
        TC_VLAN_IP_001_HW: Validate CLI for VLAN creation, port management, and IP address assignment on hardware.

        Test Procedure:
        1. Dynamically get first interface from testbed
        2. Remove IP addresses (IPv4 and IPv6) from first interface
        3. Create VLAN 3
        4. Add first interface to VLAN 3
        5. Configure IPv4 address on VLAN 3 interface
        6. Verify IPv4 address in running-config
        7. Remove IPv4 address
        8. Verify no IPv4 address in running-config
        9. Configure IPv6 address on VLAN 3 interface
        10. Verify IPv6 address in running-config
        11. Remove IPv6 address
        12. Verify no IPv6 address in running-config
        13. Remove port from VLAN
        14. Delete VLAN 3
        15. Verify no VLANs configured

        Expected Result:
        - IP addresses can be removed from interface
        - VLAN can be created successfully
        - Port can be added to VLAN
        - IPv4 address can be configured and removed from VLAN interface
        - IPv6 address can be configured and removed from VLAN interface
        - All changes are reflected accurately in running-configuration
        """
        st.log("=" * 80)
        st.log("TEST: VLAN IP Configuration (Hardware - Dynamic)")
        st.log("=" * 80)

        # Initialize validation failure tracking
        validation_failures = []

        dut = self.data.dut1
        vlan_id = self.data.test_vlan
        interface = self.data.test_interface
        ipv4_addr = self.data.ipv4_address
        ipv6_addr = self.data.ipv6_address

        # ===== STEP 1: Remove IP addresses from first interface =====
        st.log("-" * 80)
        st.log(f"STEP 1: Remove IP addresses (IPv4 and IPv6) from {interface}")
        st.log("-" * 80)

        self._remove_ip_addresses_from_interface(dut, interface)
        st.log(f"PASS: IP addresses removed from {interface}")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 2: Create VLAN 3 =====
        st.log("-" * 80)
        st.log(f"STEP 2: Create VLAN {vlan_id}")
        st.log("-" * 80)

        self._create_vlan(dut, vlan_id)
        st.log(f"Created VLAN {vlan_id}")
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 2.1: Verify VLAN 3 exists =====
        st.log("-" * 80)
        st.log(f"STEP 2.1: Verify VLAN {vlan_id} exists")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_vlan_exists(output, vlan_id):
            error_msg = f"VLAN creation failed: VLAN {vlan_id} does not exist in 'show Vlan' output"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: VLAN {vlan_id} exists")

        # ===== STEP 2.2: Verify VLAN status is Down (no active ports yet) =====
        st.log("-" * 80)
        st.log(f"STEP 2.2: Verify VLAN {vlan_id} status is Down (no active member ports)")
        st.log("-" * 80)

        if not self._verify_vlan_status(output, vlan_id, "Down"):
            error_msg = f"VLAN status validation failed: VLAN {vlan_id} should be Down when no active member ports are configured"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: VLAN {vlan_id} status is Down (expected behavior with no active member ports)")

        # ===== STEP 3: Add first interface to VLAN 3 =====
        st.log("-" * 80)
        st.log(f"STEP 3: Add {interface} to VLAN {vlan_id}")
        st.log("-" * 80)

        self._add_port_to_vlan(dut, interface, vlan_id)
        st.log(f"Added {interface} to VLAN {vlan_id}")
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 4: Configure IPv4 address on VLAN 3 interface =====
        st.log("-" * 80)
        st.log(f"STEP 4: Configure IPv4 address {ipv4_addr} on Vlan {vlan_id}")
        st.log("-" * 80)

        self._configure_vlan_ipv4(dut, vlan_id, ipv4_addr)
        st.log(f"Configured IPv4 address {ipv4_addr} on Vlan {vlan_id}")
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 5: Verify IPv4 address in running-config =====
        st.log("-" * 80)
        st.log(f"STEP 5: Verify IPv4 address {ipv4_addr} in running-config")
        st.log("-" * 80)

        output = self._get_running_config_vlan_interface(dut, vlan_id)
        if not self._verify_ipv4_in_running_config(output, ipv4_addr):
            error_msg = f"IPv4 verification failed: Vlan {vlan_id} does not show IPv4 address '{ipv4_addr}' in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IPv4 address {ipv4_addr} verified on Vlan {vlan_id}")

        # ===== STEP 6: Remove IPv4 address =====
        st.log("-" * 80)
        st.log(f"STEP 6: Remove IPv4 address from Vlan {vlan_id}")
        st.log("-" * 80)

        self._remove_vlan_ipv4(dut, vlan_id)
        st.log(f"Removed IPv4 address from Vlan {vlan_id}")
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 7: Verify no IPv4 address in running-config =====
        st.log("-" * 80)
        st.log(f"STEP 7: Verify no IPv4 address in running-config")
        st.log("-" * 80)

        output = self._get_running_config_vlan_interface(dut, vlan_id)
        if not self._verify_ipv4_in_running_config(output, None):
            error_msg = f"IPv4 removal failed: Vlan {vlan_id} still has IPv4 address in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: No IPv4 address on Vlan {vlan_id}")

        # ===== STEP 8: Configure IPv6 address on VLAN 3 interface =====
        st.log("-" * 80)
        st.log(f"STEP 8: Configure IPv6 address {ipv6_addr} on Vlan {vlan_id}")
        st.log("-" * 80)

        self._configure_vlan_ipv6(dut, vlan_id, ipv6_addr)
        st.log(f"Configured IPv6 address {ipv6_addr} on Vlan {vlan_id}")
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 9: Verify IPv6 address in running-config =====
        st.log("-" * 80)
        st.log(f"STEP 9: Verify IPv6 address {ipv6_addr} in running-config")
        st.log("-" * 80)

        output = self._get_running_config_vlan_interface(dut, vlan_id)
        if not self._verify_ipv6_in_running_config(output, ipv6_addr):
            error_msg = f"IPv6 verification failed: Vlan {vlan_id} does not show IPv6 address '{ipv6_addr}' in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IPv6 address {ipv6_addr} verified on Vlan {vlan_id}")

        # ===== STEP 10: Remove IPv6 address =====
        st.log("-" * 80)
        st.log(f"STEP 10: Remove IPv6 address from Vlan {vlan_id}")
        st.log("-" * 80)

        self._remove_vlan_ipv6(dut, vlan_id)
        st.log(f"Removed IPv6 address from Vlan {vlan_id}")
        time.sleep(WAIT_AFTER_IP_CHANGE)

        # ===== STEP 11: Verify no IPv6 address in running-config =====
        st.log("-" * 80)
        st.log(f"STEP 11: Verify no IPv6 address in running-config")
        st.log("-" * 80)

        output = self._get_running_config_vlan_interface(dut, vlan_id)
        if not self._verify_ipv6_in_running_config(output, None):
            error_msg = f"IPv6 removal failed: Vlan {vlan_id} still has IPv6 address in running-config"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: No IPv6 address on Vlan {vlan_id}")

        # ===== STEP 12: Remove port from VLAN =====
        st.log("-" * 80)
        st.log(f"STEP 12: Remove {interface} from VLAN {vlan_id}")
        st.log("-" * 80)

        self._remove_port_from_vlan(dut, interface, vlan_id)
        st.log(f"Removed {interface} from VLAN {vlan_id}")
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 13: Delete VLAN 3 =====
        st.log("-" * 80)
        st.log(f"STEP 13: Delete VLAN {vlan_id}")
        st.log("-" * 80)

        self._delete_vlan(dut, vlan_id)
        st.log(f"Deleted VLAN {vlan_id}")
        time.sleep(WAIT_AFTER_VLAN_CHANGE)

        # ===== STEP 14: Verify no VLANs configured =====
        st.log("-" * 80)
        st.log("STEP 14: Verify no VLANs configured")
        st.log("-" * 80)

        output = self._get_show_vlan_output(dut)
        if not self._verify_no_vlans_configured(output):
            error_msg = "VLAN deletion failed: VLANs are still configured"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: No VLANs configured")

        # ===== TEST COMPLETE =====
        st.log("=" * 80)
        st.log("TEST COMPLETE: VLAN IP configuration validated successfully")
        st.log(f"VLAN {vlan_id} lifecycle:")
        st.log(f"  - Created VLAN → Added {interface}")
        st.log(f"  - Configured IPv4 {ipv4_addr} → Verified → Removed")
        st.log(f"  - Configured IPv6 {ipv6_addr} → Verified → Removed")
        st.log(f"  - Removed {interface} → Deleted VLAN ✓")
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
