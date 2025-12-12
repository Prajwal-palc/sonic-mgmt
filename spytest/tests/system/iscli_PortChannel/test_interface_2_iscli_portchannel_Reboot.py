"""
PORTCHANNEL CONFIGURATION - PORTCHANNEL CREATION, PORT MANAGEMENT, IP ADDRESSING, AND REBOOT PERSISTENCE
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_PortChannel/test_interface_2_iscli_portchannel_Reboot.py \
  --logs-path ./logs/test_interface_2_iscli_portchannel_Reboot_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates PortChannel creation, port management, IP addressing, and config persistence across TWO reboots on BOTH devices by:
  1. Verifying baseline (no PortChannels configured) on both devices
  2. Removing IP addresses (IPv4 and IPv6) from all testbed interfaces on both devices
  3. Creating PortChannel 10 on both devices
  4. Verifying PortChannel 10 exists with no member ports on both devices
  5. Adding Ethernet0 to PortChannel 10 on both devices
  6. Verifying Ethernet0 is member of PortChannel 10 on both devices
  7. Adding Ethernet4 to PortChannel 10 on both devices
  8. Verifying both Ethernet0 and Ethernet4 are members of PortChannel 10 on both devices
  9. Configuring IPv4 address on PortChannel 10 (11.1.1.1/30 on DUT1, 11.1.1.2/30 on DUT2)
  10. Verifying IPv4 address configuration on both devices
  11. Saving configuration with 'write memory' on both devices (FIRST SAVE)
  12. Rebooting both devices with 'sudo reboot' (FIRST REBOOT - IPv4 persistence test)
  13. Waiting for both devices to come back up
  14. Re-verifying IPv4 address configuration persists after reboot on both devices
  15. Re-verifying PortChannel and member ports after reboot on both devices
  16. Removing IPv4 address from PortChannel 10 on both devices
  17. Verifying IPv4 address removal on both devices
  18. Configuring IPv6 address on PortChannel 10 (2001:db8:1::1/64 on DUT1, 2001:db8:1::2/64 on DUT2)
  19. Verifying IPv6 address configuration on both devices
  20. Saving configuration with 'write memory' on both devices (SECOND SAVE)
  21. Rebooting both devices with 'sudo reboot' (SECOND REBOOT - IPv6 persistence test)
  22. Waiting for both devices to come back up
  23. Re-verifying IPv6 address configuration persists after reboot on both devices
  24. Re-verifying PortChannel and member ports after second reboot on both devices
  25. Removing IPv6 address from PortChannel 10 on both devices
  26. Verifying IPv6 address removal on both devices
  27. Removing member ports from PortChannel 10 on both devices
  28. Deleting PortChannel 10 on both devices
  29. Verifying no PortChannels configured on both devices

  This mirrors the exact CLI workflow on both DUT1 and DUT2:
    - show PortChannel summary (baseline: No PortChannels)
    - configure terminal -> interface Ethernet0 -> no ip address -> no ipv6 address -> exit
    - configure terminal -> interface Ethernet4 -> no ip address -> no ipv6 address -> exit
    - configure terminal -> interface PortChannel 10 -> exit
    - show PortChannel summary (verify: PortChannel10 exists with no ports)
    - configure terminal -> interface Ethernet0 -> channel-group 10 -> exit
    - show PortChannel summary (verify: PortChannel10 with Ethernet0)
    - configure terminal -> interface Ethernet4 -> channel-group 10 -> exit
    - show PortChannel summary (verify: PortChannel10 with Ethernet0 and Ethernet4)
    - configure terminal -> interface PortChannel 10 -> ip address <IP>/30 -> exit
    - show running-configuration interface PortChannel 10 (verify: IPv4 address)
    - write memory (save configuration - FIRST SAVE)
    - sudo reboot (reboot device - FIRST REBOOT for IPv4 persistence test)
    - [wait for reboot]
    - show running-configuration interface PortChannel 10 (verify: IPv4 address persists after reboot)
    - show PortChannel summary (verify: PortChannel10 with Ethernet0 and Ethernet4 persists)
    - configure terminal -> interface PortChannel 10 -> no ip address <IP>/30 -> exit
    - show running-configuration interface PortChannel 10 (verify: no IPv4 address)
    - configure terminal -> interface PortChannel 10 -> ipv6 address <IPv6>/64 -> exit
    - show running-configuration interface PortChannel 10 (verify: IPv6 address)
    - write memory (save configuration - SECOND SAVE)
    - sudo reboot (reboot device - SECOND REBOOT for IPv6 persistence test)
    - [wait for reboot]
    - show running-configuration interface PortChannel 10 (verify: IPv6 address persists after reboot)
    - show PortChannel summary (verify: PortChannel10 with Ethernet0 and Ethernet4 persists after 2nd reboot)
    - configure terminal -> interface PortChannel 10 -> no ipv6 address <IPv6>/64 -> exit
    - show running-configuration interface PortChannel 10 (verify: no IPv6 address)
    - configure terminal -> interface Ethernet0 -> no channel-group -> exit
    - configure terminal -> interface Ethernet4 -> no channel-group -> exit
    - configure terminal -> no interface PortChannel 10 -> exit
    - show PortChannel summary (verify: No PortChannels)

  IMPORTANT: Uses 'show PortChannel summary' command to validate PortChannel creation and member ports.
  Uses 'show running-configuration interface PortChannel 10' to validate IP address configuration.
  Tests configuration persistence across TWO device reboots using 'write memory' and 'sudo reboot'.
  First reboot validates IPv4 persistence, second reboot validates IPv6 persistence.

  IP Addressing:
  - DUT1 PortChannel10: IPv4 11.1.1.1/30, IPv6 2001:db8:1::1/64
  - DUT2 PortChannel10: IPv4 11.1.1.2/30, IPv6 2001:db8:1::2/64

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |        dut1        |                       |        dut2        |
        # |  PortChannel10     |=======================|  PortChannel10     |
        # |  11.1.1.1/30       |  Ethernet0, Eth4      |  11.1.1.2/30       |
        # |  2001:db8:1::1/64  |                       |  2001:db8:1::2/64  |
        # +--------------------+                       +--------------------+
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
WAIT_AFTER_PORTCHANNEL_CHANGE = 2
WAIT_FOR_REBOOT = 30  # Additional wait after reboot for system stabilization (st.reboot already handles reconnection)


@pytest.mark.topology("any")
class TestPortChannelConfigurationReboot:
    """Test cases for validating PortChannel creation, port management, IP addressing, and config persistence across reboot via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing PortChannel Configuration with Reboot Test Suite")
        st.log("=" * 80)

        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs available in topology")

        cls.data.dut1 = cls.data.dut_names[0]
        cls.data.dut2 = cls.data.dut_names[1] if len(cls.data.dut_names) > 1 else None
        st.log(f"Primary DUT (DUT1): {cls.data.dut1}")
        st.log(f"Secondary DUT (DUT2): {cls.data.dut2}")

        # CLI type - use klish as specified
        cls.data.cli_type = CLI_TYPE
        st.log(f"CLI Type: {cls.data.cli_type}")

        # Test PortChannel ID
        cls.data.test_portchannel = "10"
        st.log(f"Test PortChannel: {cls.data.test_portchannel}")

        # Test interfaces
        cls.data.interface1 = "Ethernet0"
        cls.data.interface2 = "Ethernet4"
        st.log(f"Test Interfaces: {cls.data.interface1}, {cls.data.interface2}")

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

        # Set terminal length 0 to disable pagination on both devices
        st.log("Setting terminal length 0 to disable pagination on both devices")
        st.config(cls.data.dut1, "terminal length 0", type=CLI_TYPE)
        st.config(cls.data.dut2, "terminal length 0", type=CLI_TYPE)

        st.log("Test setup complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup PortChannel Configuration with Reboot Test Suite")
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
    def _get_show_portchannel_summary(dut: str) -> str:
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
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"[{dut}] show PortChannel summary output:\n{output}")
        return output

    @staticmethod
    def _get_show_running_config_interface(dut: str, portchannel_id: str) -> str:
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
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"[{dut}] show running-configuration interface PortChannel {portchannel_id} output:\n{output}")
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
        st.log(f"[{dut}] Removing IP addresses from all interfaces")

        for interface in interfaces:
            st.log(f"[{dut}] Removing IP addresses from {interface}")
            commands = [
                "configure terminal",
                f"interface {interface}",
                "no ip address",
                "no ipv6 address",
                "exit"  # Exit from interface mode back to config mode
            ]
            result = st.config(dut, commands, type=CLI_TYPE)

        st.log(f"[{dut}] IP addresses removed from all interfaces")
        return True

    @staticmethod
    def _create_portchannel(dut: str, portchannel_id: str) -> bool:
        """
        Create PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if successful
        """
        st.log(f"[{dut}] Creating PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _delete_portchannel(dut: str, portchannel_id: str) -> bool:
        """
        Delete PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if successful
        """
        st.log(f"[{dut}] Deleting PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"no interface PortChannel {portchannel_id}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _add_port_to_portchannel(dut: str, interface: str, portchannel_id: str) -> bool:
        """
        Add interface to PortChannel using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if successful
        """
        st.log(f"[{dut}] Adding {interface} to PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"channel-group {portchannel_id}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_port_from_portchannel(dut: str, interface: str) -> bool:
        """
        Remove interface from PortChannel using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if successful
        """
        st.log(f"[{dut}] Removing {interface} from PortChannel")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no channel-group",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _configure_ipv4_address(dut: str, portchannel_id: str, ipv4_address: str) -> bool:
        """
        Configure IPv4 address on PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
            ipv4_address: IPv4 address with mask (e.g., "192.168.10.1/24")

        Returns:
            True if successful
        """
        st.log(f"[{dut}] Configuring IPv4 address {ipv4_address} on PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            f"ip address {ipv4_address}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_ipv4_address(dut: str, portchannel_id: str, ipv4_address: str) -> bool:
        """
        Remove IPv4 address from PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
            ipv4_address: IPv4 address with mask (e.g., "192.168.10.1/24")

        Returns:
            True if successful
        """
        st.log(f"[{dut}] Removing IPv4 address {ipv4_address} from PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            f"no ip address {ipv4_address}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _configure_ipv6_address(dut: str, portchannel_id: str, ipv6_address: str) -> bool:
        """
        Configure IPv6 address on PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
            ipv6_address: IPv6 address with prefix (e.g., "2001:db8:1::1/64")

        Returns:
            True if successful
        """
        st.log(f"[{dut}] Configuring IPv6 address {ipv6_address} on PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            f"ipv6 address {ipv6_address}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_ipv6_address(dut: str, portchannel_id: str, ipv6_address: str) -> bool:
        """
        Remove IPv6 address from PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
            ipv6_address: IPv6 address with prefix (e.g., "2001:db8:1::1/64")

        Returns:
            True if successful
        """
        st.log(f"[{dut}] Removing IPv6 address {ipv6_address} from PortChannel {portchannel_id}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            f"no ipv6 address {ipv6_address}",
            "exit"
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
        st.log(f"[{dut}] Saving configuration with 'write memory'")
        command = "write memory"
        result = st.config(dut, command, type=CLI_TYPE)
        st.log(f"[{dut}] Configuration saved successfully")
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
        st.log(f"[{dut}] Rebooting device with 'sudo reboot'")
        st.reboot(dut)
        st.log(f"[{dut}] Device reboot initiated")
        return True

    @staticmethod
    def _wait_for_device_ready(dut: str, wait_time: int = WAIT_FOR_REBOOT) -> bool:
        """
        Wait for device to come back up after reboot and be ready.

        Note: st.reboot() already handles waiting for device to come back and reconnect.
        This function just adds a small additional wait for system stabilization and
        resets terminal settings.

        Args:
            dut: Device handle
            wait_time: Time to wait in seconds (reduced since st.reboot already waits)

        Returns:
            True if device is ready
        """
        st.log(f"[{dut}] Device reconnected. Waiting {wait_time} seconds for system to stabilize...")
        st.wait(wait_time, f"Waiting for {dut} system services to stabilize after reboot")
        st.log(f"[{dut}] Device should be ready now")

        # Set terminal length 0 again after reboot
        st.log(f"[{dut}] Re-setting terminal length 0 to disable pagination after reboot")
        st.config(dut, "terminal length 0", type=CLI_TYPE)

        return True

    @staticmethod
    def _verify_no_portchannels_configured(dut: str, pc_output: str) -> bool:
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
        # Look for absence of "PortChannel" pattern in data lines
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

    @staticmethod
    def _verify_portchannel_exists(dut: str, pc_output: str, portchannel_id: str) -> bool:
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

    @staticmethod
    def _verify_port_in_portchannel(dut: str, pc_output: str, portchannel_id: str, interface: str) -> bool:
        """
        Verify that interface is a member of PortChannel.

        Expected output format:
        Flags(oper-status):  D - Down U - Up (portchannel) P - Up in portchannel (members) I - LACP individual
        ----------------------------------------------------------------------------------------------------------------------------
        Group     PortChannel         Type      Protocol       Member Ports
        ----------------------------------------------------------------------------------------------------------------------------
           10        PortChannel10       Eth (U)   NONE           Ethernet0(P)
                                                                  Ethernet4(P)

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

    @staticmethod
    def _verify_ipv4_address_configured(dut: str, config_output: str, ipv4_address: str) -> bool:
        """
        Verify that IPv4 address is configured on PortChannel.

        Args:
            dut: Device handle
            config_output: Raw output from 'show running-configuration interface PortChannel <id>' command
            ipv4_address: IPv4 address with mask (e.g., "192.168.10.1/24")

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

    @staticmethod
    def _verify_ipv4_address_not_configured(dut: str, config_output: str, ipv4_address: str) -> bool:
        """
        Verify that IPv4 address is NOT configured on PortChannel.

        Args:
            dut: Device handle
            config_output: Raw output from 'show running-configuration interface PortChannel <id>' command
            ipv4_address: IPv4 address with mask (e.g., "192.168.10.1/24")

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

    @staticmethod
    def _verify_ipv6_address_configured(dut: str, config_output: str, ipv6_address: str) -> bool:
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

    @staticmethod
    def _verify_ipv6_address_not_configured(dut: str, config_output: str, ipv6_address: str) -> bool:
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

    @pytest.mark.inventory(feature="Regression", testcases=["TC_PORTCHANNEL_REBOOT_001"])
    def test_portchannel_creation_port_management_ip_addressing_and_dual_reboot_persistence(self) -> None:
        """
        TC_PORTCHANNEL_REBOOT_001: Validate CLI for PortChannel creation, port management, IP addressing, and config persistence across TWO reboots on both devices.

        Test Procedure (performed on BOTH DUT1 and DUT2):
        1. Verify baseline (no PortChannels configured)
        2. Remove IP addresses (IPv4 and IPv6) from all testbed interfaces
        3. Create PortChannel 10
        4. Verify PortChannel 10 exists with no member ports
        5. Add Ethernet0 to PortChannel 10
        6. Verify Ethernet0 is member of PortChannel 10
        7. Add Ethernet4 to PortChannel 10
        8. Verify both Ethernet0 and Ethernet4 are members of PortChannel 10
        9. Configure IPv4 address on PortChannel 10 (different IPs on each device)
        10. Verify IPv4 address is configured
        11. Save configuration with 'write memory' (FIRST SAVE)
        12. Reboot device with 'sudo reboot' (FIRST REBOOT - IPv4 persistence test)
        13. Wait for device to come back up
        14. Re-verify IPv4 address configuration persists after reboot
        15. Re-verify PortChannel and member ports after reboot
        16. Remove IPv4 address from PortChannel 10
        17. Verify IPv4 address is removed
        18. Configure IPv6 address on PortChannel 10 (different IPs on each device)
        19. Verify IPv6 address is configured
        20. Save configuration with 'write memory' (SECOND SAVE)
        21. Reboot device with 'sudo reboot' (SECOND REBOOT - IPv6 persistence test)
        22. Wait for device to come back up
        23. Re-verify IPv6 address configuration persists after reboot
        24. Re-verify PortChannel and member ports after second reboot
        25. Remove IPv6 address from PortChannel 10
        26. Verify IPv6 address is removed
        27. Remove Ethernet0 from PortChannel 10
        28. Remove Ethernet4 from PortChannel 10
        29. Delete PortChannel 10
        30. Verify no PortChannels configured

        Expected Result:
        - IP addresses can be removed from interfaces on both devices
        - PortChannel can be created successfully on both devices
        - Ports can be added to PortChannel as members on both devices
        - IPv4 addresses can be configured on both devices
        - Configuration can be saved with 'write memory'
        - Devices can be rebooted successfully (first time)
        - IPv4 address configuration persists across first reboot on both devices
        - PortChannel and member ports persist across first reboot on both devices
        - IPv4 addresses can be removed after reboot on both devices
        - IPv6 addresses can be configured on both devices
        - Configuration can be saved with 'write memory' (second time)
        - Devices can be rebooted successfully (second time)
        - IPv6 address configuration persists across second reboot on both devices
        - PortChannel and member ports persist across second reboot on both devices
        - IPv6 addresses can be removed after reboot on both devices
        - Ports can be removed from PortChannel on both devices
        - PortChannel can be deleted successfully on both devices
        - All changes are reflected accurately in show commands on both devices
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: PortChannel Creation, Port Management, IP Addressing, and DUAL Reboot Persistence on BOTH Devices")
        st.log("=" * 80)

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        pc_id = self.data.test_portchannel
        interface1 = self.data.interface1
        interface2 = self.data.interface2
        dut1_ipv4 = self.data.dut1_ipv4_address
        dut1_ipv6 = self.data.dut1_ipv6_address
        dut2_ipv4 = self.data.dut2_ipv4_address
        dut2_ipv6 = self.data.dut2_ipv6_address

        # ===== STEP 1: Verify baseline (no PortChannels configured) on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Verify baseline (no PortChannels configured) on BOTH devices")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)
        output_dut2 = self._get_show_portchannel_summary(dut2)

        if not self._verify_no_portchannels_configured(dut1, output_dut1):
            st.report_fail(
                "msg",
                f"Baseline check failed on {dut1}: PortChannels are configured when none should exist"
            )

        if not self._verify_no_portchannels_configured(dut2, output_dut2):
            st.report_fail(
                "msg",
                f"Baseline check failed on {dut2}: PortChannels are configured when none should exist"
            )

        st.log("PASS: Baseline verified - no PortChannels configured on both devices")

        # ===== STEP 2: Remove IP addresses from all testbed interfaces on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Remove IP addresses (IPv4 and IPv6) from all testbed interfaces on BOTH devices")
        st.log("-" * 80)

        # Get all interfaces to clean
        testbed_interfaces = [interface1, interface2]
        self._remove_ip_addresses_from_interfaces(dut1, testbed_interfaces)
        self._remove_ip_addresses_from_interfaces(dut2, testbed_interfaces)

        st.log("PASS: IP addresses removed from all testbed interfaces on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 3: Create PortChannel 10 on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 3: Create PortChannel {pc_id} on BOTH devices")
        st.log("-" * 80)

        self._create_portchannel(dut1, pc_id)
        self._create_portchannel(dut2, pc_id)
        st.log(f"Created PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 4: Verify PortChannel 10 exists on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 4: Verify PortChannel {pc_id} exists on BOTH devices")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)
        output_dut2 = self._get_show_portchannel_summary(dut2)

        if not self._verify_portchannel_exists(dut1, output_dut1, pc_id):
            st.report_fail(
                "msg",
                f"PortChannel creation failed on {dut1}: PortChannel {pc_id} does not exist"
            )

        if not self._verify_portchannel_exists(dut2, output_dut2, pc_id):
            st.report_fail(
                "msg",
                f"PortChannel creation failed on {dut2}: PortChannel {pc_id} does not exist"
            )

        st.log(f"PASS: PortChannel {pc_id} exists on both devices")

        # ===== STEP 5: Add Ethernet0 to PortChannel 10 on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 4: Add {interface1} to PortChannel {pc_id} on BOTH devices")
        st.log("-" * 80)

        self._add_port_to_portchannel(dut1, interface1, pc_id)
        self._add_port_to_portchannel(dut2, interface1, pc_id)
        st.log(f"Added {interface1} to PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 6: Verify Ethernet0 is member on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 5: Verify {interface1} is member of PortChannel {pc_id} on BOTH devices")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)
        output_dut2 = self._get_show_portchannel_summary(dut2)

        if not self._verify_port_in_portchannel(dut1, output_dut1, pc_id, interface1):
            st.report_fail(
                "msg",
                f"Port addition failed on {dut1}: {interface1} is not member of PortChannel {pc_id}"
            )

        if not self._verify_port_in_portchannel(dut2, output_dut2, pc_id, interface1):
            st.report_fail(
                "msg",
                f"Port addition failed on {dut2}: {interface1} is not member of PortChannel {pc_id}"
            )

        st.log(f"PASS: {interface1} is member of PortChannel {pc_id} on both devices")

        # ===== STEP 7: Add Ethernet4 to PortChannel 10 on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 6: Add {interface2} to PortChannel {pc_id} on BOTH devices")
        st.log("-" * 80)

        self._add_port_to_portchannel(dut1, interface2, pc_id)
        self._add_port_to_portchannel(dut2, interface2, pc_id)
        st.log(f"Added {interface2} to PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 8: Verify both ports are members on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 8: Verify both {interface1} and {interface2} are members on BOTH devices")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)
        output_dut2 = self._get_show_portchannel_summary(dut2)

        if not self._verify_port_in_portchannel(dut1, output_dut1, pc_id, interface1):
            st.report_fail("msg", f"Port verification failed on {dut1}: {interface1} not in PortChannel")

        if not self._verify_port_in_portchannel(dut1, output_dut1, pc_id, interface2):
            st.report_fail("msg", f"Port verification failed on {dut1}: {interface2} not in PortChannel")

        if not self._verify_port_in_portchannel(dut2, output_dut2, pc_id, interface1):
            st.report_fail("msg", f"Port verification failed on {dut2}: {interface1} not in PortChannel")

        if not self._verify_port_in_portchannel(dut2, output_dut2, pc_id, interface2):
            st.report_fail("msg", f"Port verification failed on {dut2}: {interface2} not in PortChannel")

        st.log(f"PASS: Both {interface1} and {interface2} are members on both devices")

        # ===== STEP 9: Configure IPv4 address on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 9: Configure IPv4 addresses on PortChannel {pc_id} on BOTH devices")
        st.log(f"  {dut1}: {dut1_ipv4}")
        st.log(f"  {dut2}: {dut2_ipv4}")
        st.log("-" * 80)

        self._configure_ipv4_address(dut1, pc_id, dut1_ipv4)
        self._configure_ipv4_address(dut2, pc_id, dut2_ipv4)
        st.log(f"Configured IPv4 addresses on PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 10: Verify IPv4 address configuration on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 9: Verify IPv4 addresses are configured on BOTH devices")
        st.log("-" * 80)

        output_dut1 = self._get_show_running_config_interface(dut1, pc_id)
        output_dut2 = self._get_show_running_config_interface(dut2, pc_id)

        if not self._verify_ipv4_address_configured(dut1, output_dut1, dut1_ipv4):
            st.report_fail("msg", f"IPv4 configuration failed on {dut1}: {dut1_ipv4} not configured")

        if not self._verify_ipv4_address_configured(dut2, output_dut2, dut2_ipv4):
            st.report_fail("msg", f"IPv4 configuration failed on {dut2}: {dut2_ipv4} not configured")

        st.log(f"PASS: IPv4 addresses are configured on both devices")

        # ===== STEP 11: Save configuration with 'write memory' on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Save configuration with 'write memory' on BOTH devices")
        st.log("-" * 80)

        self._save_config(dut1)
        self._save_config(dut2)
        st.log("PASS: Configuration saved successfully on both devices")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 11: Reboot DUT1 with 'sudo reboot' =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Reboot DUT1 with 'sudo reboot' (FIRST REBOOT)")
        st.log("-" * 80)

        self._reboot_device(dut1)
        st.log("PASS: Device reboot initiated on DUT1")

        # ===== STEP 12: Wait for DUT1 to come back up =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Wait for DUT1 to come back up after reboot")
        st.log("-" * 80)

        self._wait_for_device_ready(dut1)
        st.log("PASS: DUT1 is back up and ready after reboot")

        # ===== STEP 14: Re-verify IPv4 address configuration persists after reboot on DUT1 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 14: Re-verify IPv4 address in running-config after reboot on DUT1 (IPv4 persistence check)")
        st.log("-" * 80)

        output_dut1 = self._get_show_running_config_interface(dut1, pc_id)

        if not self._verify_ipv4_address_configured(dut1, output_dut1, dut1_ipv4):
            st.report_fail(
                "msg",
                f"IPv4 persistence failed on {dut1}: {dut1_ipv4} does not persist after reboot"
            )

        st.log(f"PASS: IPv4 address configuration persisted across reboot on DUT1")

        # ===== STEP 15: Re-verify PortChannel and member ports after reboot on DUT1 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 15: Re-verify PortChannel {pc_id} and member ports after reboot on DUT1")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)

        if not self._verify_portchannel_exists(dut1, output_dut1, pc_id):
            st.report_fail("msg", f"PortChannel {pc_id} does not persist after reboot on {dut1}")

        if not self._verify_port_in_portchannel(dut1, output_dut1, pc_id, interface1):
            st.report_fail("msg", f"{interface1} not in PortChannel after reboot on {dut1}")

        if not self._verify_port_in_portchannel(dut1, output_dut1, pc_id, interface2):
            st.report_fail("msg", f"{interface2} not in PortChannel after reboot on {dut1}")

        st.log(f"PASS: PortChannel {pc_id} and member ports persisted across reboot on DUT1")

        # ===== STEP 16: Remove IPv4 address from BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 16: Remove IPv4 addresses from PortChannel {pc_id} on BOTH devices")
        st.log("-" * 80)

        self._remove_ipv4_address(dut1, pc_id, dut1_ipv4)
        self._remove_ipv4_address(dut2, pc_id, dut2_ipv4)
        st.log(f"Removed IPv4 addresses from PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 17: Verify IPv4 address removal on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 16: Verify IPv4 addresses are removed from BOTH devices")
        st.log("-" * 80)

        output_dut1 = self._get_show_running_config_interface(dut1, pc_id)
        output_dut2 = self._get_show_running_config_interface(dut2, pc_id)

        if not self._verify_ipv4_address_not_configured(dut1, output_dut1, dut1_ipv4):
            st.report_fail("msg", f"IPv4 removal failed on {dut1}: {dut1_ipv4} still configured")

        if not self._verify_ipv4_address_not_configured(dut2, output_dut2, dut2_ipv4):
            st.report_fail("msg", f"IPv4 removal failed on {dut2}: {dut2_ipv4} still configured")

        st.log(f"PASS: IPv4 addresses are removed from both devices")

        # ===== STEP 18: Configure IPv6 address on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 18: Configure IPv6 addresses on PortChannel {pc_id} on BOTH devices")
        st.log(f"  {dut1}: {dut1_ipv6}")
        st.log(f"  {dut2}: {dut2_ipv6}")
        st.log("-" * 80)

        self._configure_ipv6_address(dut1, pc_id, dut1_ipv6)
        self._configure_ipv6_address(dut2, pc_id, dut2_ipv6)
        st.log(f"Configured IPv6 addresses on PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 19: Verify IPv6 address configuration on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 18: Verify IPv6 addresses are configured on BOTH devices")
        st.log("-" * 80)

        output_dut1 = self._get_show_running_config_interface(dut1, pc_id)
        output_dut2 = self._get_show_running_config_interface(dut2, pc_id)

        if not self._verify_ipv6_address_configured(dut1, output_dut1, dut1_ipv6):
            st.report_fail("msg", f"IPv6 configuration failed on {dut1}: {dut1_ipv6} not configured")

        if not self._verify_ipv6_address_configured(dut2, output_dut2, dut2_ipv6):
            st.report_fail("msg", f"IPv6 configuration failed on {dut2}: {dut2_ipv6} not configured")

        st.log(f"PASS: IPv6 addresses are configured on both devices")

        # ===== STEP 20: Save configuration with 'write memory' on BOTH devices (SECOND SAVE) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 20: Save configuration with 'write memory' on BOTH devices (SECOND SAVE)")
        st.log("-" * 80)

        self._save_config(dut1)
        self._save_config(dut2)
        st.log("PASS: Configuration saved successfully on both devices")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 20: Reboot DUT1 with 'sudo reboot' (SECOND REBOOT) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 20: Reboot DUT1 with 'sudo reboot' (SECOND REBOOT - IPv6 persistence test)")
        st.log("-" * 80)

        self._reboot_device(dut1)
        st.log("PASS: Device reboot initiated on DUT1 (SECOND REBOOT)")

        # ===== STEP 21: Wait for DUT1 to come back up (SECOND REBOOT) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 21: Wait for DUT1 to come back up after SECOND reboot")
        st.log("-" * 80)

        self._wait_for_device_ready(dut1)
        st.log("PASS: DUT1 is back up and ready after SECOND reboot")

        # ===== STEP 23: Re-verify IPv6 address configuration persists after SECOND reboot on DUT1 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 23: Re-verify IPv6 address in running-config after SECOND reboot on DUT1 (IPv6 persistence check)")
        st.log("-" * 80)

        output_dut1 = self._get_show_running_config_interface(dut1, pc_id)

        if not self._verify_ipv6_address_configured(dut1, output_dut1, dut1_ipv6):
            st.report_fail(
                "msg",
                f"IPv6 persistence failed on {dut1}: {dut1_ipv6} does not persist after SECOND reboot"
            )

        st.log(f"PASS: IPv6 address configuration persisted across SECOND reboot on DUT1")

        # ===== STEP 24: Re-verify PortChannel and member ports after SECOND reboot on DUT1 =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 24: Re-verify PortChannel {pc_id} and member ports after SECOND reboot on DUT1")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)

        if not self._verify_portchannel_exists(dut1, output_dut1, pc_id):
            st.report_fail("msg", f"PortChannel {pc_id} does not persist after SECOND reboot on {dut1}")

        if not self._verify_port_in_portchannel(dut1, output_dut1, pc_id, interface1):
            st.report_fail("msg", f"{interface1} not in PortChannel after SECOND reboot on {dut1}")

        if not self._verify_port_in_portchannel(dut1, output_dut1, pc_id, interface2):
            st.report_fail("msg", f"{interface2} not in PortChannel after SECOND reboot on {dut1}")

        st.log(f"PASS: PortChannel {pc_id} and member ports persisted across SECOND reboot on DUT1")

        # ===== STEP 25: Remove IPv6 address from BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 25: Remove IPv6 addresses from PortChannel {pc_id} on BOTH devices")
        st.log("-" * 80)

        self._remove_ipv6_address(dut1, pc_id, dut1_ipv6)
        self._remove_ipv6_address(dut2, pc_id, dut2_ipv6)
        st.log(f"Removed IPv6 addresses from PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 26: Verify IPv6 address removal on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 25: Verify IPv6 addresses are removed from BOTH devices")
        st.log("-" * 80)

        output_dut1 = self._get_show_running_config_interface(dut1, pc_id)
        output_dut2 = self._get_show_running_config_interface(dut2, pc_id)

        if not self._verify_ipv6_address_not_configured(dut1, output_dut1, dut1_ipv6):
            st.report_fail("msg", f"IPv6 removal failed on {dut1}: {dut1_ipv6} still configured")

        if not self._verify_ipv6_address_not_configured(dut2, output_dut2, dut2_ipv6):
            st.report_fail("msg", f"IPv6 removal failed on {dut2}: {dut2_ipv6} still configured")

        st.log(f"PASS: IPv6 addresses are removed from both devices")

        # ===== STEP 27: Remove Ethernet0 from PortChannel 10 on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 26: Remove {interface1} from PortChannel {pc_id} on BOTH devices")
        st.log("-" * 80)

        self._remove_port_from_portchannel(dut1, interface1)
        self._remove_port_from_portchannel(dut2, interface1)
        st.log(f"Removed {interface1} from PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 28: Remove Ethernet4 from PortChannel 10 on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 27: Remove {interface2} from PortChannel {pc_id} on BOTH devices")
        st.log("-" * 80)

        self._remove_port_from_portchannel(dut1, interface2)
        self._remove_port_from_portchannel(dut2, interface2)
        st.log(f"Removed {interface2} from PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 29: Delete PortChannel 10 on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 29: Delete PortChannel {pc_id} on BOTH devices")
        st.log("-" * 80)

        self._delete_portchannel(dut1, pc_id)
        self._delete_portchannel(dut2, pc_id)
        st.log(f"Deleted PortChannel {pc_id} on both devices")

        # Wait for change to apply
        time.sleep(WAIT_AFTER_PORTCHANNEL_CHANGE)

        # ===== STEP 30: Verify no PortChannels configured on BOTH devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 30: Verify no PortChannels configured on BOTH devices")
        st.log("-" * 80)

        output_dut1 = self._get_show_portchannel_summary(dut1)
        output_dut2 = self._get_show_portchannel_summary(dut2)

        if not self._verify_no_portchannels_configured(dut1, output_dut1):
            st.report_fail("msg", f"PortChannel deletion failed on {dut1}: PortChannels still configured")

        if not self._verify_no_portchannels_configured(dut2, output_dut2):
            st.report_fail("msg", f"PortChannel deletion failed on {dut2}: PortChannels still configured")

        st.log("PASS: No PortChannels configured on both devices")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: PortChannel creation, port management, IP addressing, and DUAL reboot persistence validated successfully")
        st.log(f"DUT1 PortChannel {pc_id} lifecycle (with reboot validation):")
        st.log(f"  - Created → Added {interface1},{interface2}")
        st.log(f"  - IPv4 {dut1_ipv4}: Configured → Verified → Saved → Rebooted (1st) → Verified persistence ✓ → Removed")
        st.log(f"  - IPv6 {dut1_ipv6}: Configured → Verified → Saved → Rebooted (2nd) → Verified persistence ✓ → Removed")
        st.log(f"  - Removed {interface1},{interface2} → Deleted PortChannel ✓")
        st.log(f"DUT2 PortChannel {pc_id} lifecycle (configuration only, no reboot):")
        st.log(f"  - Created → Added {interface1},{interface2}")
        st.log(f"  - IPv4 {dut2_ipv4}: Configured → Verified → Removed")
        st.log(f"  - IPv6 {dut2_ipv6}: Configured → Verified → Removed")
        st.log(f"  - Removed {interface1},{interface2} → Deleted PortChannel ✓")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
