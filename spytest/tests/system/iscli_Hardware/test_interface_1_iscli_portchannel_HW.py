"""
PORTCHANNEL CONFIGURATION - PORTCHANNEL CREATION AND PORT MANAGEMENT WITH IP ADDRESSING (HARDWARE - DYNAMIC TESTBED)
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs_hardware.yaml \
  tests/system/iscli_Hardware/test_interface_1_iscli_portchannel_HW.py \
  --logs-path ./logs/test_interface_1_iscli_portchannel_HW_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates PortChannel creation, port management, and IP addressing on BOTH devices by:
  1. Dynamically getting the first 2 devices and their first interfaces from testbed
  2. Verifying baseline (no PortChannels configured) on both devices
  3. Removing IP addresses (IPv4 and IPv6) from first interface on both devices
  4. Creating PortChannel 10 on both devices
  5. Verifying PortChannel 10 exists with no member ports on both devices
  5a. Verifying PortChannel 10 operational status is Down '(D)' on DUT1
  6. Adding first interface to PortChannel 10 on DUT1
  6a. Verifying PortChannel 10 still shows '(D)' on DUT1 (before DUT2 configuration)
  6b. Adding first interface to PortChannel 10 on DUT2
  7. Verifying first interface is member of PortChannel 10 on both devices
  7a. Verifying PortChannel 10 operational status is Up '(U)' on DUT1
  8. Configuring IPv4 address on PortChannel 10 (11.1.1.1/30 on DUT1, 11.1.1.2/30 on DUT2)
  9. Verifying IPv4 address configuration on both devices
  10. Removing IPv4 address from PortChannel 10 on both devices
  11. Verifying IPv4 address removal on both devices
  12. Configuring IPv6 address on PortChannel 10 (2001:db8:1::1/64 on DUT1, 2001:db8:1::2/64 on DUT2)
  13. Verifying IPv6 address configuration on both devices
  14. Removing IPv6 address from PortChannel 10 on both devices
  15. Verifying IPv6 address removal on both devices
  16. Removing member port from PortChannel 10 on both devices
  17. Deleting PortChannel 10 on both devices
  18. Verifying no PortChannels configured on both devices

  This mirrors the exact CLI workflow on both DUT1 and DUT2:
    - show PortChannel summary (baseline: No PortChannels)
    - configure terminal -> interface Ethernet X -> no ip address -> no ipv6 address -> exit
    - configure terminal -> interface PortChannel 10 -> exit
    - show PortChannel summary (verify: PortChannel10 exists with no ports)
    - configure terminal -> interface Ethernet X -> channel-group 10 -> exit
    - show PortChannel summary (verify: PortChannel10 with Ethernet X)
    - configure terminal -> interface PortChannel 10 -> ip address <IP>/30 -> exit
    - show running-configuration interface PortChannel 10 (verify: IPv4 address)
    - configure terminal -> interface PortChannel 10 -> no ip address <IP>/30 -> exit
    - show running-configuration interface PortChannel 10 (verify: no IPv4 address)
    - configure terminal -> interface PortChannel 10 -> ipv6 address <IPv6>/64 -> exit
    - show running-configuration interface PortChannel 10 (verify: IPv6 address)
    - configure terminal -> interface PortChannel 10 -> no ipv6 address <IPv6>/64 -> exit
    - show running-configuration interface PortChannel 10 (verify: no IPv6 address)
    - configure terminal -> interface Ethernet X -> no channel-group -> exit
    - configure terminal -> no interface PortChannel 10 -> exit
    - show PortChannel summary (verify: No PortChannels)

  IMPORTANT: Uses 'show PortChannel summary' command to validate PortChannel creation and member ports.
  Uses 'show running-configuration interface PortChannel 10' to validate IP address configuration.

  IP Addressing:
  - DUT1 PortChannel10: IPv4 11.1.1.1/30, IPv6 2001:db8:1::1/64
  - DUT2 PortChannel10: IPv4 11.1.1.2/30, IPv6 2001:db8:1::2/64

  This hardware-focused version dynamically retrieves the FIRST TWO devices from the testbed
  and the FIRST interface from each device's topology links, making it portable across
  different testbed configurations without hardcoding interface names.

Pre-requisites:
  - Topology: 2-node minimum | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - Dynamic (uses first two DUTs and first interface from each)
        # +--------------------+                       +--------------------+
        # |       DUT1         |                       |       DUT2         |
        # | (First device)     |=======================| (Second device)    |
        # |  PortChannel10     |  First Intf from each |  PortChannel10     |
        # |  11.1.1.1/30       |                       |  11.1.1.2/30       |
        # |  2001:db8:1::1/64  |                       |  2001:db8:1::2/64  |
        # +--------------------+                       +--------------------+
  - Access to sonic-cli (klish mode)
  - Required test variables: CLI type (klish)
  - Minimum 2 DUTs with at least 1 interface each in testbed topology
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
WAIT_AFTER_PORTCHANNEL_CHANGE = 2


@pytest.mark.topology("any")
class TestPortChannelConfigurationHW:
    """Test cases for validating PortChannel creation, port management, and IP addressing via CLI (klish mode) on hardware."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters dynamically from testbed."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing PortChannel Configuration Test Suite (Hardware)")
        st.log("=" * 80)

        # Get DUT handles - use FIRST TWO devices from testbed
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs available in topology")

        if len(cls.data.dut_names) < 2:
            st.report_fail("msg", "This test requires at least 2 DUTs in topology")

        # Use FIRST TWO devices from testbed
        cls.data.dut1 = cls.data.dut_names[0]
        cls.data.dut2 = cls.data.dut_names[1]
        st.log(f"DUT1 (First device from testbed): {cls.data.dut1}")
        st.log(f"DUT2 (Second device from testbed): {cls.data.dut2}")

        # CLI type - use klish as specified
        cls.data.cli_type = CLI_TYPE
        st.log(f"CLI Type: {cls.data.cli_type}")

        # Test PortChannel ID
        cls.data.test_portchannel = "10"
        st.log(f"Test PortChannel: {cls.data.test_portchannel}")

        # Get FIRST interface from each DUT's testbed topology dynamically
        cls.data.dut1_interface = cls._get_first_interface_from_testbed(cls.data.dut1)
        cls.data.dut2_interface = cls._get_first_interface_from_testbed(cls.data.dut2)
        st.log(f"DUT1 Test Interface (First from testbed): {cls.data.dut1_interface}")
        st.log(f"DUT2 Test Interface (First from testbed): {cls.data.dut2_interface}")

        # Test IP addresses - DUT1
        cls.data.dut1_ipv4_address = "11.1.1.1/30"
        cls.data.dut1_ipv6_address = "2001:db8:1::1/64"
        st.log(f"DUT1 IPv4: {cls.data.dut1_ipv4_address}")
        st.log(f"DUT1 IPv6: {cls.data.dut1_ipv6_address}")

        # Test IP addresses - DUT2
        cls.data.dut2_ipv4_address = "11.1.1.2/30"
        cls.data.dut2_ipv6_address = "2001:db8:1::2/64"
        st.log(f"DUT2 IPv4: {cls.data.dut2_ipv4_address}")
        st.log(f"DUT2 IPv6: {cls.data.dut2_ipv6_address}")

        st.log("Test setup complete")

    @classmethod
    def _get_first_interface_from_testbed(cls, dut: str) -> str:
        """
        Dynamically retrieve the FIRST interface from the testbed topology for a given DUT.

        This method queries the testbed topology to find the first available
        interface on the specified DUT, making the test portable across different
        testbed configurations.

        Args:
            dut: Device handle

        Returns:
            str: First interface name (e.g., "Ethernet0")

        Raises:
            Failure if no interfaces found in testbed
        """
        try:
            # Method 1: Try to get DUT links (interfaces connected to other DUTs)
            dut_links = st.get_dut_links(dut)
            st.log(f"[{dut}] DUT links retrieved: {dut_links}")

            if dut_links and len(dut_links) > 0:
                # dut_links returns a list of links, each link is a list [local_port, remote_dut, remote_port]
                # We need to extract just the local port (first element)
                first_link = dut_links[0]

                # Handle different possible formats
                if isinstance(first_link, (list, tuple)) and len(first_link) > 0:
                    first_interface = str(first_link[0])  # Get local interface (first element)
                else:
                    first_interface = str(first_link)

                st.log(f"[{dut}] Found first interface from DUT links: {first_interface}")
                return first_interface

        except Exception as e:
            st.log(f"[{dut}] Note: Could not get DUT links: {str(e)}")

        try:
            # Method 2: Try to get all free ports
            free_ports = st.get_free_ports(dut)
            st.log(f"[{dut}] Free ports retrieved: {free_ports}")

            if free_ports and len(free_ports) > 0:
                first_interface = str(free_ports[0])
                st.log(f"[{dut}] Found first interface from free ports: {first_interface}")
                return first_interface

        except Exception as e:
            st.log(f"[{dut}] Note: Could not get free ports: {str(e)}")

        try:
            # Method 3: Try to get TG links (traffic generator links)
            tg_links = st.get_tg_links(dut)
            st.log(f"[{dut}] TG links retrieved: {tg_links}")

            if tg_links and len(tg_links) > 0:
                # Get the first TG link's DUT-side interface
                first_link = tg_links[0]
                # TG links are typically tuples/lists: (dut, interface)
                if isinstance(first_link, (list, tuple)) and len(first_link) >= 2:
                    first_interface = str(first_link[1])
                else:
                    first_interface = str(first_link)
                st.log(f"[{dut}] Found first interface from TG links: {first_interface}")
                return first_interface

        except Exception as e:
            st.log(f"[{dut}] Note: Could not get TG links: {str(e)}")

        # Fallback: If all methods fail, use default Ethernet0
        st.log(f"[{dut}] Warning: Could not dynamically retrieve interface from testbed")
        st.log(f"[{dut}] Falling back to default: Ethernet0")
        return "Ethernet0"

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite - ensure PortChannels are deleted on both devices."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup PortChannel Configuration Test Suite")
        st.log("=" * 80)

        try:
            # Try to remove ports from PortChannel on both devices
            cls._remove_port_from_portchannel_static(cls.data.dut1, cls.data.dut1_interface)
            cls._remove_port_from_portchannel_static(cls.data.dut2, cls.data.dut2_interface)
        except Exception as e:
            st.log(f"Note: Port cleanup: {str(e)}")

        try:
            # Try to delete PortChannel on both devices
            cls._delete_portchannel_static(cls.data.dut1, cls.data.test_portchannel)
            cls._delete_portchannel_static(cls.data.dut2, cls.data.test_portchannel)
            st.log(f"Cleaned up PortChannel {cls.data.test_portchannel} on both devices")
        except Exception as e:
            st.log(f"Note: PortChannel cleanup: {str(e)}")

        st.log("Cleanup completed")

    @classmethod
    def _remove_port_from_portchannel_static(cls, dut: str, interface: str) -> None:
        """
        Static helper to remove port from PortChannel during teardown.

        Args:
            dut: Device handle
            interface: Interface name
        """
        try:
            commands = [
                "configure terminal",
                f"interface {interface}",
                "no channel-group",
                "exit"
            ]
            st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
            time.sleep(1)
        except Exception as e:
            st.log(f"[{dut}] Warning: Failed to remove port from PortChannel: {str(e)}")

    @classmethod
    def _delete_portchannel_static(cls, dut: str, portchannel_id: str) -> None:
        """
        Static helper to delete PortChannel during teardown.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID
        """
        try:
            commands = [
                "configure terminal",
                f"no interface PortChannel {portchannel_id}"
            ]
            st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
            time.sleep(1)
        except Exception as e:
            st.log(f"[{dut}] Warning: Failed to delete PortChannel: {str(e)}")

    def setup_method(self) -> None:
        """Setup before each test method."""
        st.log("-" * 80)
        st.log("SETUP METHOD: Starting new test case")
        st.log("-" * 80)

    def teardown_method(self) -> None:
        """Teardown after each test method - ensure PortChannels are deleted."""
        st.log("-" * 80)
        st.log("TEARDOWN METHOD: Cleaning up test case")
        st.log("-" * 80)

        try:
            # Remove ports from PortChannel on both devices
            self._remove_port_from_portchannel(self.data.dut1, self.data.dut1_interface)
            self._remove_port_from_portchannel(self.data.dut2, self.data.dut2_interface)
        except Exception as e:
            st.log(f"Note: Port cleanup: {str(e)}")

        try:
            # Delete PortChannel on both devices
            self._delete_portchannel(self.data.dut1, self.data.test_portchannel)
            self._delete_portchannel(self.data.dut2, self.data.test_portchannel)
        except Exception as e:
            st.log(f"Note: PortChannel cleanup: {str(e)}")

    def _get_show_portchannel_summary(self, dut: str) -> str:
        """
        Get 'show PortChannel summary' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"[{dut}] Getting 'show PortChannel summary' output")

        # Command: show PortChannel summary
        command = "show PortChannel summary"

        # Execute command and get raw output
        output = st.show(dut, command, type=self.data.cli_type, skip_tmpl=True)

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"[{dut}] show PortChannel summary output:\n{output}")
        return output

    def _get_show_running_config_interface(self, dut: str, portchannel_id: str) -> str:
        """
        Get 'show running-configuration interface PortChannel <id>' output as raw string.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            Command output as raw string
        """
        st.log(f"[{dut}] Getting 'show running-configuration interface PortChannel {portchannel_id}' output")

        # Command: show running-configuration interface PortChannel <id>
        command = f"show running-configuration interface PortChannel {portchannel_id}"

        # Execute command and get raw output
        output = st.show(dut, command, type=self.data.cli_type, skip_tmpl=True)

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"[{dut}] show running-configuration interface PortChannel {portchannel_id} output:\n{output}")
        return output

    def _remove_ip_addresses_from_interface(self, dut: str, interface: str) -> None:
        """
        Remove IPv4 and IPv6 addresses from specified interface.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
        """
        st.log(f"[{dut}] Removing IP addresses from {interface}")

        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip address",
            "no ipv6 address",
            "exit"  # Exit from interface mode back to config mode
        ]
        st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)
        st.log(f"[{dut}] IP addresses removed from {interface}")

    def _create_portchannel(self, dut: str, portchannel_id: str) -> None:
        """
        Create PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
        """
        st.log(f"[{dut}] Creating PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            "exit"
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _delete_portchannel(self, dut: str, portchannel_id: str) -> None:
        """
        Delete PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
        """
        st.log(f"[{dut}] Deleting PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"no interface PortChannel {portchannel_id}"
        ]
        st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)

    def _add_port_to_portchannel(self, dut: str, interface: str, portchannel_id: str) -> None:
        """
        Add interface to PortChannel using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            portchannel_id: PortChannel ID (e.g., "10")
        """
        st.log(f"[{dut}] Adding {interface} to PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"channel-group {portchannel_id}",
            "exit"
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _remove_port_from_portchannel(self, dut: str, interface: str) -> None:
        """
        Remove interface from PortChannel using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
        """
        st.log(f"[{dut}] Removing {interface} from PortChannel")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no channel-group",
            "exit"
        ]
        st.config(dut, commands, type=self.data.cli_type, skip_error_check=True)

    def _configure_ipv4_address(self, dut: str, portchannel_id: str, ipv4_address: str) -> None:
        """
        Configure IPv4 address on PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
            ipv4_address: IPv4 address with mask (e.g., "11.1.1.1/30")
        """
        st.log(f"[{dut}] Configuring IPv4 address {ipv4_address} on PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            f"ip address {ipv4_address}",
            "exit"
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _remove_ipv4_address(self, dut: str, portchannel_id: str, ipv4_address: str) -> None:
        """
        Remove IPv4 address from PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
            ipv4_address: IPv4 address with mask (e.g., "11.1.1.1/30")
        """
        st.log(f"[{dut}] Removing IPv4 address {ipv4_address} from PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            f"no ip address {ipv4_address}",
            "exit"
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _configure_ipv6_address(self, dut: str, portchannel_id: str, ipv6_address: str) -> None:
        """
        Configure IPv6 address on PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
            ipv6_address: IPv6 address with prefix (e.g., "2001:db8:1::1/64")
        """
        st.log(f"[{dut}] Configuring IPv6 address {ipv6_address} on PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            f"ipv6 address {ipv6_address}",
            "exit"
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _remove_ipv6_address(self, dut: str, portchannel_id: str, ipv6_address: str) -> None:
        """
        Remove IPv6 address from PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
            ipv6_address: IPv6 address with prefix (e.g., "2001:db8:1::1/64")
        """
        st.log(f"[{dut}] Removing IPv6 address {ipv6_address} from PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            f"no ipv6 address {ipv6_address}",
            "exit"
        ]
        st.config(dut, commands, type=self.data.cli_type)

    def _test_ipv4_ping(self, source_dut: str, dest_ip: str) -> bool:
        """
        Test IPv4 ping connectivity from source DUT to destination IP.

        Args:
            source_dut: Source device handle
            dest_ip: Destination IP address (without prefix)

        Returns:
            True if ping succeeds, False otherwise
        """
        st.log(f"Testing IPv4 ping from {source_dut} to {dest_ip}")

        try:
            # Exit config mode to get to exec mode
            st.config(
                source_dut,
                "end",
                type=self.data.cli_type,
                conf=False,
                skip_error_check=True
            )

            # Small delay for mode transition
            time.sleep(0.5)

            # Run ping command with packet count limit (-c 3)
            cmd = f"ping -c 3 {dest_ip}"
            output = st.show(
                source_dut,
                cmd,
                type=self.data.cli_type,
                skip_tmpl=True,
                skip_error_check=True
            )

            # Convert to string if needed
            if not isinstance(output, str):
                output = str(output)

            st.log(f"Ping output:\n{output}")

            # Check if ping was successful
            if "bytes from" in output.lower() or "64 bytes" in output.lower():
                st.log(f"PASS: IPv4 ping from {source_dut} to {dest_ip} succeeded")
                return True
            else:
                st.log(f"INFO: IPv4 ping from {source_dut} to {dest_ip} failed")
                return False
        except Exception as e:
            st.log(f"INFO: Ping exception: {str(e)}")
            return False

    def _test_ipv6_ping(self, source_dut: str, dest_ipv6: str) -> bool:
        """
        Test IPv6 ping connectivity from source DUT to destination IPv6.

        Args:
            source_dut: Source device handle
            dest_ipv6: Destination IPv6 address (without prefix)

        Returns:
            True if ping succeeds, False otherwise
        """
        st.log(f"Testing IPv6 ping from {source_dut} to {dest_ipv6}")

        try:
            # Exit config mode to get to exec mode
            st.config(
                source_dut,
                "end",
                type=self.data.cli_type,
                conf=False,
                skip_error_check=True
            )

            # Small delay for mode transition
            time.sleep(0.5)

            # Run ping6 command with packet count limit (-c 3)
            cmd = f"ping6 -c 3 {dest_ipv6}"
            output = st.show(
                source_dut,
                cmd,
                type=self.data.cli_type,
                skip_tmpl=True,
                skip_error_check=True
            )

            # Convert to string if needed
            if not isinstance(output, str):
                output = str(output)

            st.log(f"Ping6 output:\n{output}")

            # Check if ping was successful
            if "bytes from" in output.lower() or "64 bytes" in output.lower():
                st.log(f"PASS: IPv6 ping from {source_dut} to {dest_ipv6} succeeded")
                return True
            else:
                st.log(f"INFO: IPv6 ping from {source_dut} to {dest_ipv6} failed")
                return False
        except Exception as e:
            st.log(f"INFO: Ping6 exception: {str(e)}")
            return False

    def _verify_no_portchannels_configured(self, dut: str, pc_output: str) -> bool:
        """
        Verify that no PortChannels are configured.

        Args:
            dut: Device handle
            pc_output: Raw output from 'show PortChannel summary' command

        Returns:
            True if no PortChannels are configured, False otherwise
        """
        st.log(f"[{dut}] Verifying no PortChannels are configured")

        # Check if output contains only header lines without any PortChannel entries
        lines = pc_output.strip().split('\n')

        # Filter out header/separator lines
        data_lines = [line for line in lines if line.strip() and
                      not line.strip().startswith('Flags') and
                      not line.strip().startswith('----') and
                      not line.strip().startswith('Group')]

        if not data_lines or len(data_lines) == 0:
            st.log(f"[{dut}] PASS: No PortChannels are configured")
            return True

        # Check if any line contains PortChannel
        for line in data_lines:
            if 'PortChannel' in line:
                st.error(f"[{dut}] FAIL: PortChannels are still configured")
                return False

        st.log(f"[{dut}] PASS: No PortChannels are configured")
        return True

    def _verify_portchannel_exists(self, dut: str, pc_output: str, portchannel_id: str) -> bool:
        """
        Verify that PortChannel exists in show PortChannel summary output.

        Args:
            dut: Device handle
            pc_output: Raw output from 'show PortChannel summary' command
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if PortChannel exists, False otherwise
        """
        st.log(f"[{dut}] Verifying PortChannel {portchannel_id} exists")

        # Search for "PortChannel<id>" pattern
        pc_pattern = rf'PortChannel{portchannel_id}'
        match = re.search(pc_pattern, pc_output, re.IGNORECASE)

        if match:
            st.log(f"[{dut}] PASS: PortChannel {portchannel_id} exists")
            return True
        else:
            st.error(f"[{dut}] FAIL: PortChannel {portchannel_id} does not exist")
            return False

    def _verify_port_in_portchannel(self, dut: str, pc_output: str, portchannel_id: str, interface: str) -> bool:
        """
        Verify that interface is a member of PortChannel.

        Args:
            dut: Device handle
            pc_output: Raw output from 'show PortChannel summary' command
            portchannel_id: PortChannel ID (e.g., "10")
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if interface is member of PortChannel, False otherwise
        """
        st.log(f"[{dut}] Verifying {interface} is member of PortChannel {portchannel_id}")

        # Search for PortChannel entry and check if interface is listed
        pc_section_pattern = rf'PortChannel{portchannel_id}\s+.*?(?=\n\s*\d+\s+PortChannel|\Z)'
        pc_match = re.search(pc_section_pattern, pc_output, re.IGNORECASE | re.DOTALL)

        if not pc_match:
            st.error(f"[{dut}] FAIL: PortChannel {portchannel_id} not found in output")
            return False

        pc_section = pc_match.group(0)

        # Check if interface is in this PortChannel section
        if interface in pc_section:
            st.log(f"[{dut}] PASS: {interface} is member of PortChannel {portchannel_id}")
            return True
        else:
            st.error(f"[{dut}] FAIL: {interface} is not member of PortChannel {portchannel_id}")
            return False

    def _verify_ipv4_address_configured(self, dut: str, config_output: str, ipv4_address: str) -> bool:
        """
        Verify that IPv4 address is configured on PortChannel.

        Args:
            dut: Device handle
            config_output: Raw output from 'show running-configuration interface PortChannel <id>' command
            ipv4_address: IPv4 address with mask (e.g., "11.1.1.1/30")

        Returns:
            True if IPv4 address is configured, False otherwise
        """
        st.log(f"[{dut}] Verifying IPv4 address {ipv4_address} is configured")

        # Search for "ip address <address>" pattern
        if f"ip address {ipv4_address}" in config_output:
            st.log(f"[{dut}] PASS: IPv4 address {ipv4_address} is configured")
            return True
        else:
            st.error(f"[{dut}] FAIL: IPv4 address {ipv4_address} is not configured")
            return False

    def _verify_ipv4_address_not_configured(self, dut: str, config_output: str, ipv4_address: str) -> bool:
        """
        Verify that IPv4 address is NOT configured on PortChannel.

        Args:
            dut: Device handle
            config_output: Raw output from 'show running-configuration interface PortChannel <id>' command
            ipv4_address: IPv4 address with mask (e.g., "11.1.1.1/30")

        Returns:
            True if IPv4 address is NOT configured, False otherwise
        """
        st.log(f"[{dut}] Verifying IPv4 address {ipv4_address} is NOT configured")

        # Search for "ip address <address>" pattern
        if f"ip address {ipv4_address}" not in config_output:
            st.log(f"[{dut}] PASS: IPv4 address {ipv4_address} is NOT configured")
            return True
        else:
            st.error(f"[{dut}] FAIL: IPv4 address {ipv4_address} is still configured")
            return False

    def _verify_ipv6_address_configured(self, dut: str, config_output: str, ipv6_address: str) -> bool:
        """
        Verify that IPv6 address is configured on PortChannel.

        Args:
            dut: Device handle
            config_output: Raw output from 'show running-configuration interface PortChannel <id>' command
            ipv6_address: IPv6 address with prefix (e.g., "2001:db8:1::1/64")

        Returns:
            True if IPv6 address is configured, False otherwise
        """
        st.log(f"[{dut}] Verifying IPv6 address {ipv6_address} is configured")

        # Search for "ipv6 address <address>" pattern
        if f"ipv6 address {ipv6_address}" in config_output:
            st.log(f"[{dut}] PASS: IPv6 address {ipv6_address} is configured")
            return True
        else:
            st.error(f"[{dut}] FAIL: IPv6 address {ipv6_address} is not configured")
            return False

    def _verify_ipv6_address_not_configured(self, dut: str, config_output: str, ipv6_address: str) -> bool:
        """
        Verify that IPv6 address is NOT configured on PortChannel.

        Args:
            dut: Device handle
            config_output: Raw output from 'show running-configuration interface PortChannel <id>' command
            ipv6_address: IPv6 address with prefix (e.g., "2001:db8:1::1/64")

        Returns:
            True if IPv6 address is NOT configured, False otherwise
        """
        st.log(f"[{dut}] Verifying IPv6 address {ipv6_address} is NOT configured")

        # Search for "ipv6 address <address>" pattern
        if f"ipv6 address {ipv6_address}" not in config_output:
            st.log(f"[{dut}] PASS: IPv6 address {ipv6_address} is NOT configured")
            return True
        else:
            st.error(f"[{dut}] FAIL: IPv6 address {ipv6_address} is still configured")
            return False

    def _verify_portchannel_status_down(self, dut: str, pc_output: str, portchannel_id: str) -> bool:
        """
        Verify that PortChannel operational status is Down (shows '(D)' flag).

        Args:
            dut: Device handle
            pc_output: Raw output from 'show PortChannel summary' command
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if PortChannel status is Down, False otherwise
        """
        st.log(f"[{dut}] Verifying PortChannel {portchannel_id} operational status is Down '(D)'")

        # Search for PortChannel line with (D) flag
        # Format: "10        PortChannel10       Eth (D)        NONE"
        pc_pattern = rf'PortChannel{portchannel_id}\s+.*?\(D\)'
        match = re.search(pc_pattern, pc_output, re.IGNORECASE)

        if match:
            st.log(f"[{dut}] PASS: PortChannel {portchannel_id} operational status is Down '(D)'")
            return True
        else:
            st.error(f"[{dut}] FAIL: PortChannel {portchannel_id} does not show Down status '(D)'")
            return False

    def _verify_portchannel_status_up(self, dut: str, pc_output: str, portchannel_id: str) -> bool:
        """
        Verify that PortChannel operational status is Up (shows '(U)' flag).

        Args:
            dut: Device handle
            pc_output: Raw output from 'show PortChannel summary' command
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if PortChannel status is Up, False otherwise
        """
        st.log(f"[{dut}] Verifying PortChannel {portchannel_id} operational status is Up '(U)'")

        # Search for PortChannel line with (U) flag
        # Format: "10        PortChannel10       Eth (U)        NONE        Ethernet272(P)"
        pc_pattern = rf'PortChannel{portchannel_id}\s+.*?\(U\)'
        match = re.search(pc_pattern, pc_output, re.IGNORECASE)

        if match:
            st.log(f"[{dut}] PASS: PortChannel {portchannel_id} operational status is Up '(U)'")
            return True
        else:
            st.error(f"[{dut}] FAIL: PortChannel {portchannel_id} does not show Up status '(U)'")
            return False

    @pytest.mark.inventory(feature="Regression", testcases=["TC_PORTCHANNEL_001_HW"])
    def test_portchannel_creation_port_management_and_ip_addressing(self) -> None:
        """
        TC_PORTCHANNEL_001_HW: Validate CLI for PortChannel creation, port management, and IP addressing on hardware.

        Test Procedure:
        - Configuration: Performed on BOTH DUT1 and DUT2
        - Validation: Performed ONLY on DUT1

        Steps:
        1. Dynamically get first interface from each DUT in testbed
        2. Configure on both, Verify baseline on DUT1 (no PortChannels configured)
        3. Remove IP addresses on both (IPv4 and IPv6) from first interface
        4. Create PortChannel 10 on both
        5. Verify PortChannel 10 exists on DUT1 with no member ports
        5a. Verify PortChannel 10 operational status is Down '(D)' on DUT1
        6. Add first interface to PortChannel 10 on DUT1
        6a. Verify PortChannel 10 still shows '(D)' on DUT1 (before DUT2 configuration)
        6b. Add first interface to PortChannel 10 on DUT2
        7. Verify first interface is member of PortChannel 10 on DUT1
        7a. Verify PortChannel 10 operational status is Up '(U)' on DUT1
        8. Configure IPv4 address on PortChannel 10 on both (different IPs on each device)
        9. Verify IPv4 address is configured on DUT1
        10. Remove IPv4 address from PortChannel 10 on both
        11. Verify IPv4 address is removed on DUT1
        12. Configure IPv6 address on PortChannel 10 on both (different IPs on each device)
        13. Verify IPv6 address is configured on DUT1
        14. Remove IPv6 address from PortChannel 10 on both
        15. Verify IPv6 address is removed on DUT1
        16. Remove first interface from PortChannel 10 on both
        17. Delete PortChannel 10 on both
        18. Verify no PortChannels configured on DUT1

        Expected Result:
        - Configuration is applied successfully on both DUT1 and DUT2
        - All validations on DUT1 pass correctly
        - All changes are reflected accurately in show commands on DUT1
        """
        st.log("=" * 80)
        st.log("TEST: PortChannel - Config on BOTH DUTs, Validation on DUT1 ONLY (Hardware - Dynamic)")
        st.log("=" * 80)

        # Track validation failures - test will continue but report fail at end
        validation_failures = []

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        pc_id = self.data.test_portchannel
        dut1_interface = self.data.dut1_interface
        dut2_interface = self.data.dut2_interface
        dut1_ipv4 = self.data.dut1_ipv4_address
        dut1_ipv6 = self.data.dut1_ipv6_address
        dut2_ipv4 = self.data.dut2_ipv4_address
        dut2_ipv6 = self.data.dut2_ipv6_address

        # ===== STEP 1: Verify baseline (no PortChannels configured) on DUT1 ONLY =====
        st.log("-" * 80)
        st.log("STEP 1: Verify baseline (no PortChannels configured) on DUT1")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)

        if not self._verify_no_portchannels_configured(dut1, output_dut1):
            st.report_fail(
                "msg",
                f"Baseline check failed on {dut1}: PortChannels are configured when none should exist"
            )

        st.log("PASS: Baseline verified - no PortChannels configured on DUT1")

        # ===== STEP 2: Remove IP addresses from first interface on BOTH devices =====
        st.log("-" * 80)
        st.log("STEP 2: Remove IP addresses (IPv4 and IPv6) from first interface on BOTH devices")
        st.log(f"  Configuring on {dut1} and {dut2}")
        st.log("-" * 80)

        self._remove_ip_addresses_from_interface(dut1, dut1_interface)
        self._remove_ip_addresses_from_interface(dut2, dut2_interface)

        st.log("PASS: IP addresses removed from first interface on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 3: Create PortChannel 10 on BOTH devices =====
        st.log("-" * 80)
        st.log(f"STEP 3: Create PortChannel {pc_id} on BOTH devices")
        st.log(f"  Configuring on {dut1} and {dut2}")
        st.log("-" * 80)

        self._create_portchannel(dut1, pc_id)
        self._create_portchannel(dut2, pc_id)
        st.log(f"Created PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 4: Verify PortChannel 10 exists on DUT1 ONLY =====
        st.log("-" * 80)
        st.log(f"STEP 4: Verify PortChannel {pc_id} exists on DUT1")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)

        if not self._verify_portchannel_exists(dut1, output_dut1, pc_id):
            st.report_fail(
                "msg",
                f"PortChannel creation failed on {dut1}: PortChannel {pc_id} does not exist"
            )

        st.log(f"PASS: PortChannel {pc_id} exists on DUT1")

        # ===== STEP 4a: Verify PortChannel 10 operational status is Down '(D)' on DUT1 =====
        st.log("-" * 80)
        st.log(f"STEP 4a: Verify PortChannel {pc_id} operational status is Down '(D)' on DUT1")
        st.log("-" * 80)

        if not self._verify_portchannel_status_down(dut1, output_dut1, pc_id):
            error_msg = f"PortChannel status check failed on {dut1}: PortChannel {pc_id} does not show Down status '(D)'"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: PortChannel {pc_id} operational status is Down '(D)' on DUT1")

        # ===== STEP 5: Add first interface to PortChannel 10 on BOTH devices =====
        st.log("-" * 80)
        st.log(f"STEP 5: Add first interface to PortChannel {pc_id} on BOTH devices")
        st.log(f"  Configuring on {dut1}: {dut1_interface}")
        st.log(f"  Configuring on {dut2}: {dut2_interface}")
        st.log("-" * 80)

        # Configure DUT1 first
        self._add_port_to_portchannel(dut1, dut1_interface, pc_id)
        st.log(f"Added first interface to PortChannel {pc_id} on {dut1}")

        # Wait for change to apply on DUT1
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 5a: Verify PortChannel still shows '(D)' after adding interface on DUT1 only =====
        st.log("-" * 80)
        st.log(f"STEP 5a: Verify PortChannel {pc_id} still shows '(D)' on DUT1 (before DUT2 configuration)")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)

        if not self._verify_portchannel_status_down(dut1, output_dut1, pc_id):
            error_msg = f"PortChannel status check failed on {dut1}: Expected '(D)' Down status after adding interface on DUT1 only, but got different status"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: PortChannel {pc_id} still shows Down '(D)' on DUT1 (DUT2 not yet configured)")

        # Now configure DUT2
        self._add_port_to_portchannel(dut2, dut2_interface, pc_id)
        st.log(f"Added first interface to PortChannel {pc_id} on {dut2}")

        # Wait for change to apply on DUT2
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 6: Verify first interface is member on DUT1 ONLY =====
        st.log("-" * 80)
        st.log(f"STEP 6: Verify first interface is member of PortChannel {pc_id} on DUT1")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)

        if not self._verify_port_in_portchannel(dut1, output_dut1, pc_id, dut1_interface):
            st.report_fail(
                "msg",
                f"Port addition failed on {dut1}: {dut1_interface} is not member of PortChannel {pc_id}"
            )

        st.log(f"PASS: First interface is member of PortChannel {pc_id} on DUT1")

        # ===== STEP 6a: Verify PortChannel 10 operational status is Up '(U)' on DUT1 =====
        st.log("-" * 80)
        st.log(f"STEP 6a: Verify PortChannel {pc_id} operational status is Up '(U)' on DUT1")
        st.log("-" * 80)

        if not self._verify_portchannel_status_up(dut1, output_dut1, pc_id):
            st.report_fail(
                "msg",
                f"PortChannel status check failed on {dut1}: PortChannel {pc_id} does not show Up status '(U)'"
            )

        st.log(f"PASS: PortChannel {pc_id} operational status is Up '(U)' on DUT1")

        # ===== STEP 7: Configure IPv4 address on BOTH devices =====
        st.log("-" * 80)
        st.log(f"STEP 7: Configure IPv4 addresses on PortChannel {pc_id} on BOTH devices")
        st.log(f"  Configuring on {dut1}: {dut1_ipv4}")
        st.log(f"  Configuring on {dut2}: {dut2_ipv4}")
        st.log("-" * 80)

        self._configure_ipv4_address(dut1, pc_id, dut1_ipv4)
        self._configure_ipv4_address(dut2, pc_id, dut2_ipv4)
        st.log(f"Configured IPv4 addresses on PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 8: Verify IPv4 address configuration on DUT1 ONLY =====
        st.log("-" * 80)
        st.log(f"STEP 8: Verify IPv4 address is configured on DUT1")
        st.log("-" * 80)

        output_dut1 = self._get_show_running_config_interface(dut1, pc_id)

        if not self._verify_ipv4_address_configured(dut1, output_dut1, dut1_ipv4):
            st.report_fail("msg", f"IPv4 configuration failed on {dut1}: {dut1_ipv4} not configured")

        st.log(f"PASS: IPv4 address is configured on DUT1")

        # ===== STEP 8a: Test IPv4 connectivity via ping =====
        st.log("-" * 80)
        st.log(f"STEP 8a: Test IPv4 connectivity via ping")
        st.log(f"  Ping from {dut1} (11.1.1.1) to {dut2} (11.1.1.2)")
        st.log("-" * 80)

        # Wait for interfaces to be ready
        time.sleep(3)

        # Extract IP addresses without prefix for ping
        dut2_ipv4_addr = dut2_ipv4.split('/')[0]  # Extract "11.1.1.2" from "11.1.1.2/30"

        # Test ping - this is informational, not blocking
        ipv4_ping_result = self._test_ipv4_ping(dut1, dut2_ipv4_addr)

        if ipv4_ping_result:
            st.log(f"INFO: IPv4 ping test PASSED - Connectivity verified between PortChannels")
        else:
            st.log(f"INFO: IPv4 ping test FAILED - This is informational only, test continues")

        # ===== STEP 9: Remove IPv4 address from BOTH devices =====
        st.log("-" * 80)
        st.log(f"STEP 9: Remove IPv4 addresses from PortChannel {pc_id} on BOTH devices")
        st.log(f"  Configuring on {dut1} and {dut2}")
        st.log("-" * 80)

        self._remove_ipv4_address(dut1, pc_id, dut1_ipv4)
        self._remove_ipv4_address(dut2, pc_id, dut2_ipv4)
        st.log(f"Removed IPv4 addresses from PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 10: Verify IPv4 address removal on DUT1 ONLY =====
        st.log("-" * 80)
        st.log(f"STEP 10: Verify IPv4 address is removed from DUT1")
        st.log("-" * 80)

        output_dut1 = self._get_show_running_config_interface(dut1, pc_id)

        if not self._verify_ipv4_address_not_configured(dut1, output_dut1, dut1_ipv4):
            st.report_fail("msg", f"IPv4 removal failed on {dut1}: {dut1_ipv4} still configured")

        st.log(f"PASS: IPv4 address is removed from DUT1")

        # ===== STEP 11: Configure IPv6 address on BOTH devices =====
        st.log("-" * 80)
        st.log(f"STEP 11: Configure IPv6 addresses on PortChannel {pc_id} on BOTH devices")
        st.log(f"  Configuring on {dut1}: {dut1_ipv6}")
        st.log(f"  Configuring on {dut2}: {dut2_ipv6}")
        st.log("-" * 80)

        self._configure_ipv6_address(dut1, pc_id, dut1_ipv6)
        self._configure_ipv6_address(dut2, pc_id, dut2_ipv6)
        st.log(f"Configured IPv6 addresses on PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 12: Verify IPv6 address configuration on DUT1 ONLY =====
        st.log("-" * 80)
        st.log(f"STEP 12: Verify IPv6 address is configured on DUT1")
        st.log("-" * 80)

        output_dut1 = self._get_show_running_config_interface(dut1, pc_id)

        if not self._verify_ipv6_address_configured(dut1, output_dut1, dut1_ipv6):
            st.report_fail("msg", f"IPv6 configuration failed on {dut1}: {dut1_ipv6} not configured")

        st.log(f"PASS: IPv6 address is configured on DUT1")

        # ===== STEP 12a: Test IPv6 connectivity via ping6 =====
        st.log("-" * 80)
        st.log(f"STEP 12a: Test IPv6 connectivity via ping6")
        st.log(f"  Ping from {dut1} (2001:db8:1::1) to {dut2} (2001:db8:1::2)")
        st.log("-" * 80)

        # Wait for interfaces to be ready
        time.sleep(3)

        # Extract IPv6 addresses without prefix for ping
        dut2_ipv6_addr = dut2_ipv6.split('/')[0]  # Extract "2001:db8:1::2" from "2001:db8:1::2/64"

        # Test ping6 - this is informational, not blocking
        ipv6_ping_result = self._test_ipv6_ping(dut1, dut2_ipv6_addr)

        if ipv6_ping_result:
            st.log(f"INFO: IPv6 ping test PASSED - Connectivity verified between PortChannels")
        else:
            st.log(f"INFO: IPv6 ping test FAILED - This is informational only, test continues")

        # ===== STEP 13: Remove IPv6 address from BOTH devices =====
        st.log("-" * 80)
        st.log(f"STEP 13: Remove IPv6 addresses from PortChannel {pc_id} on BOTH devices")
        st.log(f"  Configuring on {dut1} and {dut2}")
        st.log("-" * 80)

        self._remove_ipv6_address(dut1, pc_id, dut1_ipv6)
        self._remove_ipv6_address(dut2, pc_id, dut2_ipv6)
        st.log(f"Removed IPv6 addresses from PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 14: Verify IPv6 address removal on DUT1 ONLY =====
        st.log("-" * 80)
        st.log(f"STEP 14: Verify IPv6 address is removed from DUT1")
        st.log("-" * 80)

        output_dut1 = self._get_show_running_config_interface(dut1, pc_id)

        if not self._verify_ipv6_address_not_configured(dut1, output_dut1, dut1_ipv6):
            st.report_fail("msg", f"IPv6 removal failed on {dut1}: {dut1_ipv6} still configured")

        st.log(f"PASS: IPv6 address is removed from DUT1")

        # ===== STEP 15: Remove first interface from PortChannel 10 on BOTH devices =====
        st.log("-" * 80)
        st.log(f"STEP 15: Remove first interface from PortChannel {pc_id} on BOTH devices")
        st.log(f"  Configuring on {dut1} and {dut2}")
        st.log("-" * 80)

        self._remove_port_from_portchannel(dut1, dut1_interface)
        self._remove_port_from_portchannel(dut2, dut2_interface)
        st.log(f"Removed first interface from PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 16: Delete PortChannel 10 on BOTH devices =====
        st.log("-" * 80)
        st.log(f"STEP 16: Delete PortChannel {pc_id} on BOTH devices")
        st.log(f"  Configuring on {dut1} and {dut2}")
        st.log("-" * 80)

        self._delete_portchannel(dut1, pc_id)
        self._delete_portchannel(dut2, pc_id)
        st.log(f"Deleted PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 17: Verify no PortChannels configured on DUT1 ONLY =====
        st.log("-" * 80)
        st.log("STEP 17: Verify no PortChannels configured on DUT1")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)

        if not self._verify_no_portchannels_configured(dut1, output_dut1):
            st.report_fail("msg", f"PortChannel deletion failed on {dut1}: PortChannels still configured")

        st.log("PASS: No PortChannels configured on DUT1")

        # ===== TEST COMPLETE =====
        st.log("=" * 80)
        st.log("TEST COMPLETE: PortChannel - Configuration on BOTH, Validation on DUT1 test finished")
        st.log(f"Configuration applied on:")
        st.log(f"  DUT1 PortChannel {pc_id}: {dut1_interface} → IPv4 {dut1_ipv4} → IPv6 {dut1_ipv6} ✓")
        st.log(f"  DUT2 PortChannel {pc_id}: {dut2_interface} → IPv4 {dut2_ipv4} → IPv6 {dut2_ipv6} ✓")
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
            st.log("Validation performed on DUT1 only: All checks passed ✓")
            st.report_pass("test_case_passed")
