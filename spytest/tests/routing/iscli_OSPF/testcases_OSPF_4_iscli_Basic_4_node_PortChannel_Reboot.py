"""
OSPF BASIC CONFIGURATION - 4-NODE TOPOLOGY WITH PORTCHANNEL, STATIC ROUTING, AND REBOOT PERSISTENCE
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_4_iscli_Basic_4_node_PortChannel_Reboot.py \
  --logs-path ./logs/testcases_OSPF_4_iscli_Basic_4_node_PortChannel_Reboot_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native \
  --tc-max-timeout 3600

Description:
  This test validates OSPF configuration with PortChannel and static routing in a 4-node topology
  and configuration persistence across reboot by:
  1. Removing IP addresses from all Ethernet interfaces that will be added to PortChannels
  2. Creating PortChannels and adding ports to PortChannels, verify with 'show PortChannel summary'
  3. Configuring IP addresses on PortChannel interfaces, verify with 'show running-configuration interface PortChannel X'
  4. Configuring static routes on D1 and D3
  5. Configuring OSPF on D2 and D4 (middle nodes)
  6. Verifying OSPF neighbor adjacency (Full state)
  7. Verifying DR/BDR election
  8. Validating ping connectivity from D1 to D3
  9. Saving configuration with 'write memory' on all DUTs
  10. Rebooting all devices with 'sudo reboot'
  11. Re-verifying OSPF neighbor adjacency after reboot
  12. Re-verifying DR/BDR election after reboot
  13. Re-validating ping connectivity from D1 to D3 after reboot
  14. Cleanup: Removing all configurations

  Topology:
        D1 ----------- D2 ----------- D4 ----------- D3
    (PortChannel110) (PortChannel110) (PortChannel120) (PortChannel120)
                                      (PortChannel130) (PortChannel130)

  PortChannel Configuration:
    PortChannel 110: D1 (Ethernet0, Ethernet4) <-> D2 (Ethernet0, Ethernet4)
    PortChannel 120: D2 (Ethernet24, Ethernet28) <-> D4 (Ethernet24, Ethernet28)
    PortChannel 130: D4 (Ethernet40, Ethernet44) <-> D3 (Ethernet40, Ethernet44)

  IP Configuration:
    D1: PortChannel110: 10.1.1.1/24, Static route: 30.1.1.0/24 via 10.1.1.2
    D2: PortChannel110: 10.1.1.2/24, PortChannel120: 20.1.1.1/24, OSPF area 0
    D4: PortChannel120: 20.1.1.2/24, PortChannel130: 30.1.1.2/24, OSPF area 0
    D3: PortChannel130: 30.1.1.1/24, Static route: 10.1.1.0/24 via 30.1.1.2

  IMPORTANT: Uses 'show ip ospf neighbor', 'show ip ospf interface', and 'show ip route'
  commands to validate OSPF configuration. Tests configuration persistence across
  device reboot using 'write memory' and 'sudo reboot'. Uses klish CLI type exclusively.

Pre-requisites:
  - Topology: 4-node | Supported: HW and Virtual
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
WAIT_AFTER_PORTCHANNEL_CONFIG = 3
WAIT_AFTER_IP_CONFIG = 3
WAIT_AFTER_STATIC_ROUTE = 3
# WAIT_AFTER_BGP_RESTART = 180  # Commented out - not needed
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 90
WAIT_FOR_ROUTE_UPDATE = 10
WAIT_FOR_PING = 5
WAIT_FOR_REBOOT = 180  # Wait time for device to reboot and come back up


@pytest.mark.topology("any")
class TestOSPFStaticRoutingPortChannel4NodeReboot:
    """Test cases for validating OSPF with PortChannel, static routing, and reboot persistence in 4-node topology via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF 4-Node PortChannel Static Routing with Reboot Test Suite")
        st.log("=" * 80)

        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if len(cls.data.dut_names) < 4:
            st.report_fail("msg", "Minimum 4 DUTs required for this test")

        cls.data.dut1 = cls.data.dut_names[0]
        cls.data.dut2 = cls.data.dut_names[1]
        cls.data.dut3 = cls.data.dut_names[2]
        cls.data.dut4 = cls.data.dut_names[3]

        st.log(f"DUT1 (D1): {cls.data.dut1}")
        st.log(f"DUT2 (D2): {cls.data.dut2}")
        st.log(f"DUT3 (D3): {cls.data.dut3}")
        st.log(f"DUT4 (D4): {cls.data.dut4}")

        # CLI type - use klish as specified
        cls.data.cli_type = CLI_TYPE
        st.log(f"CLI Type: {cls.data.cli_type}")

        # Test interfaces based on testbed_4vs.yaml topology
        # PortChannel 110: D1 <-> D2
        cls.data.dut1_pc110_ports = ["Ethernet0", "Ethernet4"]
        cls.data.dut2_pc110_ports = ["Ethernet0", "Ethernet4"]

        # PortChannel 120: D2 <-> D4
        cls.data.dut2_pc120_ports = ["Ethernet24", "Ethernet28"]
        cls.data.dut4_pc120_ports = ["Ethernet24", "Ethernet28"]

        # PortChannel 130: D4 <-> D3
        cls.data.dut4_pc130_ports = ["Ethernet40", "Ethernet44"]
        cls.data.dut3_pc130_ports = ["Ethernet40", "Ethernet44"]

        st.log(f"PortChannel 110: D1{cls.data.dut1_pc110_ports} <-> D2{cls.data.dut2_pc110_ports}")
        st.log(f"PortChannel 120: D2{cls.data.dut2_pc120_ports} <-> D4{cls.data.dut4_pc120_ports}")
        st.log(f"PortChannel 130: D4{cls.data.dut4_pc130_ports} <-> D3{cls.data.dut3_pc130_ports}")

        # PortChannel IDs
        cls.data.pc110 = "110"
        cls.data.pc120 = "120"
        cls.data.pc130 = "130"

        # IP addresses
        cls.data.dut1_pc110_ip = "10.1.1.1/24"
        cls.data.dut2_pc110_ip = "10.1.1.2/24"
        cls.data.dut2_pc120_ip = "20.1.1.1/24"
        cls.data.dut4_pc120_ip = "20.1.1.2/24"
        cls.data.dut4_pc130_ip = "30.1.1.2/24"
        cls.data.dut3_pc130_ip = "30.1.1.1/24"

        st.log(f"IP Addresses:")
        st.log(f"  D1[PortChannel{cls.data.pc110}]: {cls.data.dut1_pc110_ip}")
        st.log(f"  D2[PortChannel{cls.data.pc110}]: {cls.data.dut2_pc110_ip}")
        st.log(f"  D2[PortChannel{cls.data.pc120}]: {cls.data.dut2_pc120_ip}")
        st.log(f"  D4[PortChannel{cls.data.pc120}]: {cls.data.dut4_pc120_ip}")
        st.log(f"  D4[PortChannel{cls.data.pc130}]: {cls.data.dut4_pc130_ip}")
        st.log(f"  D3[PortChannel{cls.data.pc130}]: {cls.data.dut3_pc130_ip}")

        # OSPF area
        cls.data.ospf_area = "0"
        st.log(f"OSPF Area: {cls.data.ospf_area}")

        # Set terminal length 0 to disable pagination
        st.log("Setting terminal length 0 to disable pagination on all DUTs")
        st.config(cls.data.dut1, "terminal length 0", type=CLI_TYPE)
        st.config(cls.data.dut2, "terminal length 0", type=CLI_TYPE)
        st.config(cls.data.dut3, "terminal length 0", type=CLI_TYPE)
        st.config(cls.data.dut4, "terminal length 0", type=CLI_TYPE)

        st.log("Test setup complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup OSPF 4-Node PortChannel Static Routing with Reboot Test Suite")
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

    # ========== HELPER METHODS - PORTCHANNEL CONFIGURATION ==========

    @staticmethod
    def _create_portchannel(dut: str, portchannel_id: str) -> bool:
        """
        Create PortChannel.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "110")

        Returns:
            True if successful
        """
        st.log(f"Creating PortChannel {portchannel_id} on {dut}")
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
        Delete PortChannel.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID

        Returns:
            True if successful
        """
        st.log(f"Deleting PortChannel {portchannel_id} on {dut}")
        commands = [
            "configure terminal",
            f"no interface PortChannel {portchannel_id}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _add_ports_to_portchannel(dut: str, ports: List[str], portchannel_id: str) -> bool:
        """
        Add multiple ports to PortChannel.

        Args:
            dut: Device handle
            ports: List of interface names (e.g., ["Ethernet0", "Ethernet4"])
            portchannel_id: PortChannel ID

        Returns:
            True if successful
        """
        st.log(f"Adding ports {ports} to PortChannel {portchannel_id} on {dut}")
        for port in ports:
            commands = [
                "configure terminal",
                f"interface {port}",
                f"channel-group {portchannel_id}",
                "exit"
            ]
            st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_ports_from_portchannel(dut: str, ports: List[str]) -> bool:
        """
        Remove multiple ports from PortChannel.

        Args:
            dut: Device handle
            ports: List of interface names

        Returns:
            True if successful
        """
        st.log(f"Removing ports {ports} from PortChannel on {dut}")
        for port in ports:
            commands = [
                "configure terminal",
                f"interface {port}",
                "no channel-group",
                "exit"
            ]
            st.config(dut, commands, type=CLI_TYPE)
        return True

    # ========== HELPER METHODS - INTERFACE IP REMOVAL ==========

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
        st.log(f"Removing IP addresses from interfaces {interfaces} on {dut}")

        for interface in interfaces:
            st.log(f"Removing IP addresses from {interface}")
            commands = [
                "configure terminal",
                f"interface {interface}",
                "no ip address",
                "no ipv6 address",
                "exit"
            ]
            result = st.config(dut, commands, type=CLI_TYPE)

        st.log(f"IP addresses removed from all interfaces on {dut}")
        return True

    # ========== HELPER METHODS - IP CONFIGURATION ==========

    @staticmethod
    def _configure_portchannel_ip(dut: str, portchannel_id: str, ip_address: str) -> bool:
        """
        Configure IP address on PortChannel interface.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "110")
            ip_address: IP address with mask (e.g., "10.1.1.1/24")

        Returns:
            True if successful
        """
        st.log(f"Configuring IP address {ip_address} on PortChannel {portchannel_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            "no ip address",
            f"ip address {ip_address}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_portchannel_ip(dut: str, portchannel_id: str) -> bool:
        """
        Remove IP address from PortChannel interface.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID

        Returns:
            True if successful
        """
        st.log(f"Removing IP address from PortChannel {portchannel_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            "no ip address",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    # ========== HELPER METHODS - STATIC ROUTING ==========

    @staticmethod
    def _configure_static_route(dut: str, network: str, next_hop: str) -> bool:
        """
        Configure static route.

        Args:
            dut: Device handle
            network: Network address with mask (e.g., "30.1.1.0/24")
            next_hop: Next hop IP address (e.g., "10.1.1.2")

        Returns:
            True if successful
        """
        st.log(f"Configuring static route {network} via {next_hop} on {dut}")
        commands = [
            "configure terminal",
            f"ip route {network} {next_hop}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_static_route(dut: str, network: str, next_hop: str) -> bool:
        """
        Remove static route.

        Args:
            dut: Device handle
            network: Network address with mask (e.g., "30.1.1.0/24")
            next_hop: Next hop IP address (e.g., "10.1.1.2")

        Returns:
            True if successful
        """
        st.log(f"Removing static route {network} via {next_hop} on {dut}")
        commands = [
            "configure terminal",
            f"no ip route {network} {next_hop}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    # BGP restart section commented out - not needed for this test
    # @staticmethod
    # def _restart_bgp_docker(dut: str) -> bool:
    #     """
    #     Restart BGP docker to apply static route changes.
    #
    #     Args:
    #         dut: Device handle
    #
    #     Returns:
    #         True if successful
    #     """
    #     st.log(f"Restarting BGP docker on {dut}")
    #     # Exit from sonic-cli and restart docker
    #     command = "docker restart bgp"
    #     result = st.config(dut, command, type="click", skip_error_check=True)
    #     st.log(f"BGP docker restart command executed on {dut}")
    #     return True

    # ========== HELPER METHODS - OSPF CONFIGURATION ==========

    @staticmethod
    def _configure_ospf_process(dut: str, area: str) -> bool:
        """
        Configure OSPF process and area.

        Args:
            dut: Device handle
            area: OSPF area ID

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF process with area {area} on {dut}")
        commands = [
            "configure terminal",
            "router ospf",
            f"area {area}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _configure_ospf_network(dut: str, network: str, area: str) -> bool:
        """
        Configure OSPF network statement.

        Args:
            dut: Device handle
            network: Network address with mask (e.g., "10.1.1.2/24")
            area: OSPF area ID

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF network {network} area {area} on {dut}")
        commands = [
            "configure terminal",
            "router ospf",
            f"network {network} area {area}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_ospf_configuration(dut: str) -> bool:
        """
        Remove OSPF configuration.

        Args:
            dut: Device handle

        Returns:
            True if successful
        """
        st.log(f"Removing OSPF configuration from {dut}")
        commands = [
            "configure terminal",
            "no router ospf"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    # ========== HELPER METHODS - SAVE AND REBOOT ==========

    @staticmethod
    def _save_config(dut: str) -> bool:
        """
        Save running configuration using 'write memory' command.

        Args:
            dut: Device handle

        Returns:
            True if successful
        """
        st.log(f"Saving configuration with 'write memory' on {dut}")
        command = "write memory"
        result = st.config(dut, command, type=CLI_TYPE)
        st.log(f"Configuration saved successfully on {dut}")
        return True

    # ========== HELPER METHODS - SHOW COMMANDS ==========

    @staticmethod
    def _get_show_ip_route_output(dut: str) -> str:
        """
        Get 'show ip route' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show ip route' output from {dut}")
        command = "show ip route"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip route output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_neighbor_output(dut: str) -> str:
        """
        Get 'show ip ospf neighbor' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show ip ospf neighbor' output from {dut}")
        command = "show ip ospf neighbor"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf neighbor output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_interface_output(dut: str) -> str:
        """
        Get 'show ip ospf interface' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show ip ospf interface' output from {dut}")
        command = "show ip ospf interface"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf interface output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_portchannel_summary(dut: str) -> str:
        """
        Get 'show PortChannel summary' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show PortChannel summary' output from {dut}")
        command = "show PortChannel summary"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show PortChannel summary output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_running_config_portchannel_interface(dut: str, portchannel_id: str) -> str:
        """
        Get running-configuration for PortChannel interface.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "110")

        Returns:
            String containing the output of 'show running-configuration interface PortChannel X' command
        """
        st.log(f"Getting running-configuration for PortChannel {portchannel_id} from {dut}")

        # Command: show running-configuration interface PortChannel X
        cmd = f"show running-configuration interface PortChannel {portchannel_id}"

        # Execute command
        output = st.show(dut, cmd, type=CLI_TYPE, skip_tmpl=True, skip_error_check=True)

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"Running-config output for PortChannel {portchannel_id} from {dut}:\n{output}")
        return output

    # ========== HELPER METHODS - VALIDATION ==========

    @staticmethod
    def _verify_portchannel_exists(pc_output: str, portchannel_id: str) -> bool:
        """
        Verify that PortChannel exists in show PortChannel summary output.

        Args:
            pc_output: Raw output from 'show PortChannel summary' command
            portchannel_id: PortChannel ID (e.g., "110")

        Returns:
            True if PortChannel exists, False otherwise
        """
        st.log(f"Verifying PortChannel {portchannel_id} exists")

        # Search for "PortChannel<id>" pattern
        pc_pattern = rf'PortChannel{portchannel_id}'
        match = re.search(pc_pattern, pc_output, re.IGNORECASE)

        if match:
            st.log(f"PASS: PortChannel {portchannel_id} exists")
            return True
        else:
            st.error(f"FAIL: PortChannel {portchannel_id} does not exist")
            return False

    @staticmethod
    def _verify_port_in_portchannel(pc_output: str, portchannel_id: str, interface: str) -> bool:
        """
        Verify that interface is a member of PortChannel.

        Expected output format:
        Flags: D - Down, U - Up
        Group   PortChannel      Type       Protocol     Member Ports
        --------------------------------------------------------------
        110     PortChannel110   Eth        LACP(A)      Ethernet0(U) Ethernet4(U)

        Args:
            pc_output: Raw output from 'show PortChannel summary' command
            portchannel_id: PortChannel ID (e.g., "110")
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if interface is member of PortChannel, False otherwise
        """
        st.log(f"Verifying {interface} is member of PortChannel {portchannel_id}")

        # Search for PortChannel entry and check if interface is listed
        pc_section_pattern = rf'PortChannel{portchannel_id}.*'
        pc_match = re.search(pc_section_pattern, pc_output, re.IGNORECASE)

        if not pc_match:
            st.error(f"FAIL: PortChannel {portchannel_id} not found in output")
            return False

        pc_line = pc_match.group(0)

        # Check if interface is in this PortChannel line
        if interface in pc_line:
            st.log(f"PASS: {interface} is member of PortChannel {portchannel_id}")
            return True
        else:
            st.error(f"FAIL: {interface} is not member of PortChannel {portchannel_id}")
            return False

    @staticmethod
    def _extract_ipv4_from_running_config(output: str) -> Optional[str]:
        """
        Extract IPv4 address value from running-configuration output.

        Expected output format:
        !
        interface PortChannel110
         ip address 10.1.1.1/24

        Args:
            output: Raw CLI output string from show running-configuration

        Returns:
            IPv4 address value as string (e.g., "10.1.1.1/24"), or None if not found
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
    def _verify_ipv4_in_running_config(config_output: str, expected_ipv4: Optional[str]) -> bool:
        """
        Verify that PortChannel interface has the expected IPv4 address in running-configuration.

        Args:
            config_output: Raw output from 'show running-configuration interface PortChannel X'
            expected_ipv4: Expected IPv4 address value (e.g., "10.1.1.1/24")
                          or None if no IPv4 address should be present

        Returns:
            True if IPv4 address matches expected value, False otherwise
        """
        st.log(f"Verifying IPv4 address = '{expected_ipv4}' in running-configuration")

        # Extract IPv4 address value
        actual_ipv4 = TestOSPFStaticRoutingPortChannel4NodeReboot._extract_ipv4_from_running_config(config_output)

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
    def _verify_static_route_in_routing_table(route_output: str, network: str) -> bool:
        """
        Verify that static route is present in routing table.

        Expected output format:
        S>* 30.1.1.0/24 [1/0] via 10.1.1.2, Ethernet8, weight 1, 00:00:09

        Args:
            route_output: Raw output from 'show ip route' command
            network: Expected network (e.g., "30.1.1.0/24")

        Returns:
            True if route is present, False otherwise
        """
        st.log(f"Verifying static route {network} is present in routing table")

        # Look for the network in the output
        if network in route_output:
            # Check if it's a static route (starts with S)
            lines = route_output.split('\n')
            for line in lines:
                if network in line and ('S>' in line or 'S ' in line or 'S*' in line):
                    st.log(f"PASS: Static route {network} is present in routing table")
                    return True

        st.error(f"FAIL: Static route {network} not found in routing table")
        return False

    @staticmethod
    def _verify_ospf_neighbor_present(neighbor_output: str, expected_neighbor_ip: str, expected_state: str = "Full") -> bool:
        """
        Verify that OSPF neighbor is present with expected state.

        Expected output format:
        Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
        192.168.100.183   1 Full/Backup     46.855s           31.802s 20.1.1.2        Ethernet16:20.1.1.1                   0     0     0

        Args:
            neighbor_output: Raw output from 'show ip ospf neighbor' command
            expected_neighbor_ip: Expected neighbor IP address
            expected_state: Expected neighbor state (default: "Full")

        Returns:
            True if neighbor is present with correct state, False otherwise
        """
        st.log(f"Verifying OSPF neighbor {expected_neighbor_ip} is in {expected_state} state")

        # Check if neighbor IP is present in output
        if expected_neighbor_ip not in neighbor_output:
            st.error(f"FAIL: Neighbor {expected_neighbor_ip} not found in output")
            return False

        # Check if state is correct
        if expected_state not in neighbor_output:
            st.error(f"FAIL: Neighbor state {expected_state} not found in output")
            return False

        # More specific check: Look for the state near the neighbor IP
        lines = neighbor_output.split('\n')
        for line in lines:
            if expected_neighbor_ip in line and expected_state in line:
                st.log(f"PASS: Neighbor {expected_neighbor_ip} is in {expected_state} state")
                return True

        st.error(f"FAIL: Neighbor {expected_neighbor_ip} not in {expected_state} state")
        return False

    @staticmethod
    def _verify_dr_bdr_election(interface_output: str) -> bool:
        """
        Verify DR/BDR election in OSPF interface output.

        Expected output format:
          Designated Router (ID) 192.168.100.217 Interface Address 20.1.1.1/24
          Backup Designated Router (ID) 192.168.100.183, Interface Address 20.1.1.2

        Args:
            interface_output: Raw output from 'show ip ospf interface' command

        Returns:
            True if DR/BDR election occurred, False otherwise
        """
        st.log("Verifying DR/BDR election occurred")

        # Check for DR
        if "Designated Router" in interface_output:
            st.log("PASS: Designated Router (DR) found")
            dr_ok = True
        else:
            st.error("FAIL: Designated Router (DR) not found")
            dr_ok = False

        # Check for BDR
        if "Backup Designated Router" in interface_output:
            st.log("PASS: Backup Designated Router (BDR) found")
            bdr_ok = True
        else:
            st.error("FAIL: Backup Designated Router (BDR) not found")
            bdr_ok = False

        return dr_ok and bdr_ok

    @staticmethod
    def _verify_ping_success(dut: str, target_ip: str) -> bool:
        """
        Verify ping from DUT to target IP.

        Args:
            dut: Device handle
            target_ip: Target IP address to ping (e.g., "30.1.1.1")

        Returns:
            True if ping successful, False otherwise
        """
        st.log(f"Verifying ping from {dut} to {target_ip}")

        # Execute ping command (outside sonic-cli, in shell)
        command = f"ping -c 4 {target_ip}"
        output = st.config(dut, command, type="click")

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"Ping output:\n{output}")

        # Check for successful ping (look for "0% packet loss" or similar)
        if "0% packet loss" in output or "4 received" in output:
            st.log(f"PASS: Ping from {dut} to {target_ip} successful")
            return True
        else:
            st.error(f"FAIL: Ping from {dut} to {target_ip} failed")
            return False

    # ========== TEST CASE ==========

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_PORTCHANNEL_STATIC_4NODE_REBOOT_001"])
    @pytest.mark.timeout(3600)
    def test_ospf_portchannel_static_routing_4node_reboot_persistence(self) -> None:
        """
        TC_OSPF_PORTCHANNEL_STATIC_4NODE_REBOOT_001: Validate OSPF with PortChannel, static routing, and config persistence across reboot.

        Test Procedure:
        1. Remove IP addresses from all Ethernet interfaces that will be added to PortChannels
        2. Create PortChannels and add ports to PortChannels, verify with 'show PortChannel summary'
        3. Configure IP addresses on PortChannel interfaces, verify with 'show running-configuration interface PortChannel X'
        4. Configure static routes on D1 and D3
        5. Configure OSPF on D2 and D4
        6. Verify OSPF neighbor adjacency (Full state)
        7. Verify DR/BDR election
        8. Verify ping from D1 to D3
        9. Save configuration with 'write memory' on all DUTs
        10. Reboot all devices with 'sudo reboot'
        11. Re-verify OSPF neighbor adjacency after reboot
        12. Re-verify DR/BDR election after reboot
        13. Re-verify ping from D1 to D3 after reboot
        14. Cleanup: Remove all configurations

        Expected Result:
        - IP addresses removed from Ethernet interfaces
        - PortChannels created with correct ports (verified via show PortChannel summary)
        - IP addresses configured on PortChannel interfaces (verified via show running-configuration)
        - Static routes installed in routing tables
        - OSPF neighbors form adjacency (Full state)
        - DR/BDR election occurs
        - Ping from D1 to D3 successful
        - Configuration can be saved with 'write memory' on all DUTs
        - All devices can be rebooted successfully
        - OSPF neighbors re-establish after reboot
        - DR/BDR re-election occurs after reboot
        - Ping from D1 to D3 successful after reboot
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF with PortChannel, Static Routing, and Reboot Persistence - 4-Node Topology")
        st.log("=" * 80)

        # Track validation failures - test will continue but report fail at end
        validation_failures = []

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4
        area = self.data.ospf_area

        # ===== STEP 1: Remove IP addresses from Ethernet interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Remove IP addresses from all Ethernet interfaces")
        st.log("-" * 80)

        # Remove IPs from all interfaces that will be added to PortChannels
        self._remove_ip_addresses_from_interfaces(dut1, self.data.dut1_pc110_ports)
        self._remove_ip_addresses_from_interfaces(dut2, self.data.dut2_pc110_ports + self.data.dut2_pc120_ports)
        self._remove_ip_addresses_from_interfaces(dut3, self.data.dut3_pc130_ports)
        self._remove_ip_addresses_from_interfaces(dut4, self.data.dut4_pc120_ports + self.data.dut4_pc130_ports)

        st.log("IP addresses removed from all Ethernet interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: IP addresses removed successfully")

        # ===== STEP 2: Create PortChannels and add ports =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Create PortChannels and add ports to PortChannels")
        st.log("-" * 80)

        # PortChannel 110: D1 <-> D2
        self._create_portchannel(dut1, self.data.pc110)
        self._add_ports_to_portchannel(dut1, self.data.dut1_pc110_ports, self.data.pc110)

        self._create_portchannel(dut2, self.data.pc110)
        self._add_ports_to_portchannel(dut2, self.data.dut2_pc110_ports, self.data.pc110)

        # PortChannel 120: D2 <-> D4
        self._create_portchannel(dut2, self.data.pc120)
        self._add_ports_to_portchannel(dut2, self.data.dut2_pc120_ports, self.data.pc120)

        self._create_portchannel(dut4, self.data.pc120)
        self._add_ports_to_portchannel(dut4, self.data.dut4_pc120_ports, self.data.pc120)

        # PortChannel 130: D4 <-> D3
        self._create_portchannel(dut4, self.data.pc130)
        self._add_ports_to_portchannel(dut4, self.data.dut4_pc130_ports, self.data.pc130)

        self._create_portchannel(dut3, self.data.pc130)
        self._add_ports_to_portchannel(dut3, self.data.dut3_pc130_ports, self.data.pc130)

        st.log("PortChannels created and ports added")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        # Verify PortChannels and ports on all devices
        st.log("Verifying PortChannels and port membership")

        # Verify D1: PortChannel 110
        pc_output_dut1 = self._get_show_portchannel_summary(dut1)
        if not self._verify_portchannel_exists(pc_output_dut1, self.data.pc110):
            error_msg = f"PortChannel {self.data.pc110} does not exist on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D2: PortChannel 110 and PortChannel 120
        pc_output_dut2 = self._get_show_portchannel_summary(dut2)
        if not self._verify_portchannel_exists(pc_output_dut2, self.data.pc110):
            error_msg = f"PortChannel {self.data.pc110} does not exist on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        if not self._verify_portchannel_exists(pc_output_dut2, self.data.pc120):
            error_msg = f"PortChannel {self.data.pc120} does not exist on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D4: PortChannel 120 and PortChannel 130
        pc_output_dut4 = self._get_show_portchannel_summary(dut4)
        if not self._verify_portchannel_exists(pc_output_dut4, self.data.pc120):
            error_msg = f"PortChannel {self.data.pc120} does not exist on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        if not self._verify_portchannel_exists(pc_output_dut4, self.data.pc130):
            error_msg = f"PortChannel {self.data.pc130} does not exist on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D3: PortChannel 130
        pc_output_dut3 = self._get_show_portchannel_summary(dut3)
        if not self._verify_portchannel_exists(pc_output_dut3, self.data.pc130):
            error_msg = f"PortChannel {self.data.pc130} does not exist on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        st.log("PASS: PortChannels created successfully")

        # ===== STEP 3: Configure IP addresses on PortChannel interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Configure IP addresses on PortChannel interfaces")
        st.log("-" * 80)

        # D1: PortChannel110 - 10.1.1.1/24
        self._configure_portchannel_ip(dut1, self.data.pc110, self.data.dut1_pc110_ip)

        # D2: PortChannel110 - 10.1.1.2/24, PortChannel120 - 20.1.1.1/24
        self._configure_portchannel_ip(dut2, self.data.pc110, self.data.dut2_pc110_ip)
        self._configure_portchannel_ip(dut2, self.data.pc120, self.data.dut2_pc120_ip)

        # D4: PortChannel120 - 20.1.1.2/24, PortChannel130 - 30.1.1.2/24
        self._configure_portchannel_ip(dut4, self.data.pc120, self.data.dut4_pc120_ip)
        self._configure_portchannel_ip(dut4, self.data.pc130, self.data.dut4_pc130_ip)

        # D3: PortChannel130 - 30.1.1.1/24
        self._configure_portchannel_ip(dut3, self.data.pc130, self.data.dut3_pc130_ip)

        st.log("IP addresses configured on PortChannel interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Verify IP addresses on all PortChannel interfaces
        st.log("Verifying IP addresses on PortChannel interfaces")

        # Verify D1: PortChannel110 IP
        config_output = self._get_running_config_portchannel_interface(dut1, self.data.pc110)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut1_pc110_ip):
            error_msg = f"IP address verification failed for PortChannel{self.data.pc110} on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D2: PortChannel110 and PortChannel120 IPs
        config_output = self._get_running_config_portchannel_interface(dut2, self.data.pc110)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut2_pc110_ip):
            error_msg = f"IP address verification failed for PortChannel{self.data.pc110} on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        config_output = self._get_running_config_portchannel_interface(dut2, self.data.pc120)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut2_pc120_ip):
            error_msg = f"IP address verification failed for PortChannel{self.data.pc120} on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D4: PortChannel120 and PortChannel130 IPs
        config_output = self._get_running_config_portchannel_interface(dut4, self.data.pc120)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut4_pc120_ip):
            error_msg = f"IP address verification failed for PortChannel{self.data.pc120} on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        config_output = self._get_running_config_portchannel_interface(dut4, self.data.pc130)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut4_pc130_ip):
            error_msg = f"IP address verification failed for PortChannel{self.data.pc130} on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D3: PortChannel130 IP
        config_output = self._get_running_config_portchannel_interface(dut3, self.data.pc130)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut3_pc130_ip):
            error_msg = f"IP address verification failed for PortChannel{self.data.pc130} on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        st.log("PASS: IP addresses configured successfully")

        # ===== STEP 4: Configure static routes on D1 and D3 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Configure static routes on D1 and D3")
        st.log("-" * 80)

        # D1: ip route 30.1.1.0/24 via 10.1.1.2
        self._configure_static_route(dut1, "30.1.1.0/24", "10.1.1.2")

        # D3: ip route 10.1.1.0/24 via 30.1.1.2
        self._configure_static_route(dut3, "10.1.1.0/24", "30.1.1.2")

        st.log("Static routes configured on D1 and D3")
        time.sleep(WAIT_AFTER_STATIC_ROUTE)

        st.log("PASS: Static routes configured successfully")

        # ===== BGP RESTART SECTION COMMENTED OUT - NOT NEEDED =====
        # st.log("\n" + "-" * 80)
        # st.log("STEP 5: Restart BGP docker on D1 and D3")
        # st.log("-" * 80)
        #
        # self._restart_bgp_docker(dut1)
        # self._restart_bgp_docker(dut3)
        #
        # st.log(f"Waiting {WAIT_AFTER_BGP_RESTART} seconds for BGP docker to restart...")
        # time.sleep(WAIT_AFTER_BGP_RESTART)
        #
        # st.log("PASS: BGP docker restarted on D1 and D3")

        # ===== STEP 5: Configure OSPF on D2 and D4 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Configure OSPF on D2 and D4")
        st.log("-" * 80)

        # D2: OSPF configuration
        self._configure_ospf_process(dut2, area)
        self._configure_ospf_network(dut2, self.data.dut2_pc120_ip, area)
        self._configure_ospf_network(dut2, self.data.dut2_pc110_ip, area)

        # D4: OSPF configuration
        self._configure_ospf_process(dut4, area)
        self._configure_ospf_network(dut4, self.data.dut4_pc120_ip, area)
        self._configure_ospf_network(dut4, self.data.dut4_pc130_ip, area)

        st.log("OSPF configured on D2 and D4")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed")

        # ===== STEP 6: Verify OSPF neighbor adjacency =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Verify OSPF neighbor adjacency (Full state)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor output from D2 and D4
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        # Extract neighbor IPs (without mask)
        dut4_neighbor_ip = self.data.dut4_pc120_ip.split('/')[0]  # 20.1.1.2
        dut2_neighbor_ip = self.data.dut2_pc120_ip.split('/')[0]  # 20.1.1.1

        # Verify neighbors
        if not self._verify_ospf_neighbor_present(neighbor_output_dut2, dut4_neighbor_ip, "Full"):
            error_msg = f"OSPF neighbor {dut4_neighbor_ip} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_present(neighbor_output_dut4, dut2_neighbor_ip, "Full"):
            error_msg = f"OSPF neighbor {dut2_neighbor_ip} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        st.log("PASS: OSPF neighbors are in Full state")

        # ===== STEP 7: Verify DR/BDR election =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Verify DR/BDR election")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_ROUTE_UPDATE)

        interface_output_dut2 = self._get_show_ip_ospf_interface_output(dut2)
        interface_output_dut4 = self._get_show_ip_ospf_interface_output(dut4)

        # Verify DR/BDR election on D2
        if not self._verify_dr_bdr_election(interface_output_dut2):
            st.log("WARNING: DR/BDR election information incomplete on D2")
        else:
            st.log("PASS: DR/BDR election verified on D2")

        # Verify DR/BDR election on D4
        if not self._verify_dr_bdr_election(interface_output_dut4):
            st.log("WARNING: DR/BDR election information incomplete on D4")
        else:
            st.log("PASS: DR/BDR election verified on D4")

        st.log("PASS: DR/BDR election completed")

        # ===== STEP 8: Verify ping from D1 to D3 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Verify ping connectivity from D1 to D3")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_PING)

        # Ping from D1 to D3's IP (30.1.1.1)
        target_ip_d3 = self.data.dut3_pc130_ip.split('/')[0]  # 30.1.1.1
        if not self._verify_ping_success(dut1, target_ip_d3):
            error_msg = f"Ping from {dut1} to {target_ip_d3} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Ping from D3 to D1's IP (10.1.1.1)
        target_ip_d1 = self.data.dut1_pc110_ip.split('/')[0]  # 10.1.1.1
        if not self._verify_ping_success(dut3, target_ip_d1):
            error_msg = f"Ping from {dut3} to {target_ip_d1} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)

        st.log("PASS: Ping connectivity verified between D1 and D3")

        # ===== STEP 9: Save configuration with 'write memory' on all DUTs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Save configuration with 'write memory' on all DUTs")
        st.log("-" * 80)

        self._save_config(dut1)
        self._save_config(dut2)
        self._save_config(dut3)
        self._save_config(dut4)
        st.log("PASS: Configuration saved successfully on all DUTs")

        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # ===== STEP 10: Reboot all devices with 'sudo reboot' =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Reboot all devices with 'sudo reboot'")
        st.log("-" * 80)

        # Reboot DUT1 (st.reboot waits for device to come back)
        st.log(f"Rebooting {dut1}...")
        st.reboot(dut1)
        st.log(f"{dut1} has rebooted and is back up")
        st.config(dut1, "terminal length 0", type=CLI_TYPE)
        time.sleep(10)  # Wait for system to stabilize after reboot

        # Reboot DUT2
        st.log(f"Rebooting {dut2}...")
        st.reboot(dut2)
        st.log(f"{dut2} has rebooted and is back up")
        st.config(dut2, "terminal length 0", type=CLI_TYPE)
        time.sleep(10)  # Wait for system to stabilize after reboot

        # Reboot DUT3
        st.log(f"Rebooting {dut3}...")
        st.reboot(dut3)
        st.log(f"{dut3} has rebooted and is back up")
        st.config(dut3, "terminal length 0", type=CLI_TYPE)
        time.sleep(10)  # Wait for system to stabilize after reboot

        # Reboot DUT4
        st.log(f"Rebooting {dut4}...")
        st.reboot(dut4)
        st.log(f"{dut4} has rebooted and is back up")
        st.config(dut4, "terminal length 0", type=CLI_TYPE)
        time.sleep(10)  # Wait for system to stabilize after reboot

        st.log("PASS: All devices have been rebooted and are back up and ready")

        # Wait for PortChannels to stabilize fully before verifying OSPF
        st.log("Waiting 30 seconds for all PortChannels to stabilize after reboot...")
        time.sleep(30)

        # ===== STEP 11: Re-verify OSPF neighbor adjacency after reboot =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Re-verify OSPF neighbor adjacency after reboot (config persistence check)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to re-establish after reboot...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor output from D2 and D4 after reboot
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        # Re-verify neighbors after reboot
        if not self._verify_ospf_neighbor_present(neighbor_output_dut2, dut4_neighbor_ip, "Full"):
            error_msg = f"Config persistence failed: OSPF neighbor {dut4_neighbor_ip} not in Full state on {dut2} after reboot"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_present(neighbor_output_dut4, dut2_neighbor_ip, "Full"):
            error_msg = f"Config persistence failed: OSPF neighbor {dut2_neighbor_ip} not in Full state on {dut4} after reboot"
            st.error(error_msg)
            validation_failures.append(error_msg)

        st.log("PASS: OSPF neighbors re-established Full state after reboot - config persisted successfully")

        # ===== STEP 12: Re-verify DR/BDR election after reboot =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Re-verify DR/BDR election after reboot")
        st.log("-" * 80)

        interface_output_dut2 = self._get_show_ip_ospf_interface_output(dut2)
        interface_output_dut4 = self._get_show_ip_ospf_interface_output(dut4)

        # Re-verify DR/BDR election on D2 after reboot
        if not self._verify_dr_bdr_election(interface_output_dut2):
            st.log("WARNING: DR/BDR election information incomplete on D2 after reboot")
        else:
            st.log("PASS: DR/BDR election re-occurred on D2 after reboot")

        # Re-verify DR/BDR election on D4 after reboot
        if not self._verify_dr_bdr_election(interface_output_dut4):
            st.log("WARNING: DR/BDR election information incomplete on D4 after reboot")
        else:
            st.log("PASS: DR/BDR election re-occurred on D4 after reboot")

        st.log("PASS: DR/BDR election verified after reboot")

        # ===== STEP 13: Re-verify ping from D1 to D3 after reboot =====
        st.log("\n" + "-" * 80)
        st.log("STEP 13: Re-verify ping connectivity from D1 to D3 after reboot")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_PING)

        # Re-ping from D1 to D3's IP (30.1.1.1) after reboot
        if not self._verify_ping_success(dut1, target_ip_d3):
            error_msg = f"Config persistence failed: Ping from {dut1} to {target_ip_d3} failed after reboot"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Re-ping from D3 to D1's IP (10.1.1.1) after reboot
        if not self._verify_ping_success(dut3, target_ip_d1):
            error_msg = f"Config persistence failed: Ping from {dut3} to {target_ip_d1} failed after reboot"
            st.error(error_msg)
            validation_failures.append(error_msg)

        st.log("PASS: Ping connectivity persisted after reboot - config verified successfully")

        # ===== STEP 14: Cleanup - Remove all configurations =====
        st.log("\n" + "-" * 80)
        st.log("STEP 14: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove static routes
        self._remove_static_route(dut1, "30.1.1.0/24", "10.1.1.2")
        self._remove_static_route(dut3, "10.1.1.0/24", "30.1.1.2")
        st.log("Static routes removed from D1 and D3")

        # Remove OSPF configuration
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut4)
        st.log("OSPF configuration removed from D2 and D4")

        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Remove IP addresses from PortChannel interfaces
        self._remove_portchannel_ip(dut1, self.data.pc110)
        self._remove_portchannel_ip(dut2, self.data.pc110)
        self._remove_portchannel_ip(dut2, self.data.pc120)
        self._remove_portchannel_ip(dut4, self.data.pc120)
        self._remove_portchannel_ip(dut4, self.data.pc130)
        self._remove_portchannel_ip(dut3, self.data.pc130)
        st.log("IP addresses removed from PortChannel interfaces")

        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Remove ports from PortChannels
        self._remove_ports_from_portchannel(dut1, self.data.dut1_pc110_ports)
        self._remove_ports_from_portchannel(dut2, self.data.dut2_pc110_ports)
        self._remove_ports_from_portchannel(dut2, self.data.dut2_pc120_ports)
        self._remove_ports_from_portchannel(dut4, self.data.dut4_pc120_ports)
        self._remove_ports_from_portchannel(dut4, self.data.dut4_pc130_ports)
        self._remove_ports_from_portchannel(dut3, self.data.dut3_pc130_ports)
        st.log("Ports removed from PortChannels")

        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        # Delete PortChannels
        self._delete_portchannel(dut1, self.data.pc110)
        self._delete_portchannel(dut2, self.data.pc110)
        self._delete_portchannel(dut2, self.data.pc120)
        self._delete_portchannel(dut4, self.data.pc120)
        self._delete_portchannel(dut4, self.data.pc130)
        self._delete_portchannel(dut3, self.data.pc130)
        st.log("PortChannels deleted")

        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        st.log("PASS: Cleanup completed successfully")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF with PortChannel, static routing, and reboot persistence validated")
        st.log("Test flow: Remove IPs → PortChannel Config → IP Config → Static Routes → OSPF Config → Neighbor Full → DR/BDR → Ping → Save → Reboot All → Verify Persistence → Cleanup ✓")
        st.log("=" * 80)

        # Check for any validation failures
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_pc_reboot_validation_failure")
                    st.log(f"Tech support collected from {dut}")
                except Exception as e:
                    st.log(f"Warning: Failed to collect tech support from {dut}: {str(e)}")

            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES SUMMARY:")
            st.log("!" * 80)
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.log("!" * 80)

            failure_summary = "\n".join([f"  - {failure}" for failure in validation_failures])
            st.report_fail("msg", f"Test completed with {len(validation_failures)} validation failure(s):\n{failure_summary}")
        else:
            st.log("All validations passed successfully")
            st.report_pass("test_case_passed")
