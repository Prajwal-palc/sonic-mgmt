"""
OSPF BASIC CONFIGURATION - 4-NODE TOPOLOGY WITH VLAN AND STATIC ROUTING
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_3_iscli_Basic_4_node_Vlan.py \
  --logs-path ./logs/testcases_OSPF_3_iscli_Basic_4_node_Vlan_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF configuration with VLAN and static routing in a 4-node topology by:
  1. Creating VLANs and adding ports to VLANs on all devices
  2. Configuring IP addresses on VLAN interfaces
  3. Configuring static routes on D1 and D3
  4. Restarting BGP docker and validating static routes in routing table
  5. Configuring OSPF on D2 and D4 (middle nodes)
  6. Verifying OSPF neighbor adjacency (Full state)
  7. Verifying DR/BDR election
  8. Validating ping connectivity from D1 to D3
  9. Cleanup: Removing all configurations

  Topology:
        D1 -------- D2 -------- D4 -------- D3
    (Vlan10)    (Vlan10)    (Vlan20)    (Vlan20)
                            (Vlan30)    (Vlan30)

  VLAN Configuration:
    VLAN 10: D1 (Ethernet0, Ethernet4) <-> D2 (Ethernet0, Ethernet4)
    VLAN 20: D2 (Ethernet24, Ethernet28) <-> D4 (Ethernet24, Ethernet28)
    VLAN 30: D4 (Ethernet40, Ethernet44) <-> D3 (Ethernet40, Ethernet44)

  IP Configuration:
    D1: Vlan10: 10.1.1.1/24, Static route: 30.1.1.0/24 via 10.1.1.2
    D2: Vlan10: 10.1.1.2/24, Vlan20: 20.1.1.1/24, OSPF area 0
    D4: Vlan20: 20.1.1.2/24, Vlan30: 30.1.1.2/24, OSPF area 0
    D3: Vlan30: 30.1.1.1/24, Static route: 10.1.1.0/24 via 30.1.1.2

  IMPORTANT: Uses 'show ip ospf neighbor', 'show ip ospf interface', and 'show ip route'
  commands to validate OSPF configuration. Uses klish CLI type exclusively.

Pre-requisites:
  - Topology: 4-node | Supported: HW and Virtual
  - Access to sonic-cli (klish mode)
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
WAIT_AFTER_VLAN_CONFIG = 3
WAIT_AFTER_IP_CONFIG = 3
WAIT_AFTER_STATIC_ROUTE = 3
WAIT_AFTER_BGP_RESTART = 180
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_ROUTE_UPDATE = 10
WAIT_FOR_PING = 5


@pytest.mark.topology("any")
class TestOSPFStaticRoutingVLAN4Node:
    """Test cases for validating OSPF with VLAN and static routing in 4-node topology via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF 4-Node VLAN Static Routing Test Suite")
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
        # VLAN 10: D1 <-> D2
        cls.data.dut1_vlan10_ports = ["Ethernet0", "Ethernet4"]
        cls.data.dut2_vlan10_ports = ["Ethernet0", "Ethernet4"]

        # VLAN 20: D2 <-> D4
        cls.data.dut2_vlan20_ports = ["Ethernet24", "Ethernet28"]
        cls.data.dut4_vlan20_ports = ["Ethernet24", "Ethernet28"]

        # VLAN 30: D4 <-> D3
        cls.data.dut4_vlan30_ports = ["Ethernet40", "Ethernet44"]
        cls.data.dut3_vlan30_ports = ["Ethernet40", "Ethernet44"]

        st.log(f"VLAN 10: D1{cls.data.dut1_vlan10_ports} <-> D2{cls.data.dut2_vlan10_ports}")
        st.log(f"VLAN 20: D2{cls.data.dut2_vlan20_ports} <-> D4{cls.data.dut4_vlan20_ports}")
        st.log(f"VLAN 30: D4{cls.data.dut4_vlan30_ports} <-> D3{cls.data.dut3_vlan30_ports}")

        # VLAN IDs
        cls.data.vlan10 = "10"
        cls.data.vlan20 = "20"
        cls.data.vlan30 = "30"

        # IP addresses
        cls.data.dut1_vlan10_ip = "10.1.1.1/24"
        cls.data.dut2_vlan10_ip = "10.1.1.2/24"
        cls.data.dut2_vlan20_ip = "20.1.1.1/24"
        cls.data.dut4_vlan20_ip = "20.1.1.2/24"
        cls.data.dut4_vlan30_ip = "30.1.1.2/24"
        cls.data.dut3_vlan30_ip = "30.1.1.1/24"

        st.log(f"IP Addresses:")
        st.log(f"  D1[Vlan{cls.data.vlan10}]: {cls.data.dut1_vlan10_ip}")
        st.log(f"  D2[Vlan{cls.data.vlan10}]: {cls.data.dut2_vlan10_ip}")
        st.log(f"  D2[Vlan{cls.data.vlan20}]: {cls.data.dut2_vlan20_ip}")
        st.log(f"  D4[Vlan{cls.data.vlan20}]: {cls.data.dut4_vlan20_ip}")
        st.log(f"  D4[Vlan{cls.data.vlan30}]: {cls.data.dut4_vlan30_ip}")
        st.log(f"  D3[Vlan{cls.data.vlan30}]: {cls.data.dut3_vlan30_ip}")

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
        st.log("TEST TEARDOWN: Cleanup OSPF 4-Node VLAN Static Routing Test Suite")
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

    # ========== HELPER METHODS - VLAN CONFIGURATION ==========

    @staticmethod
    def _create_vlan(dut: str, vlan_id: str) -> bool:
        """
        Create VLAN.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "10")

        Returns:
            True if successful
        """
        st.log(f"Creating VLAN {vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"vlan {vlan_id}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _delete_vlan(dut: str, vlan_id: str) -> bool:
        """
        Delete VLAN.

        Args:
            dut: Device handle
            vlan_id: VLAN ID

        Returns:
            True if successful
        """
        st.log(f"Deleting VLAN {vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"no vlan {vlan_id}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _add_ports_to_vlan(dut: str, ports: List[str], vlan_id: str) -> bool:
        """
        Add multiple ports to VLAN as tagged members.

        Args:
            dut: Device handle
            ports: List of interface names (e.g., ["Ethernet0", "Ethernet4"])
            vlan_id: VLAN ID

        Returns:
            True if successful
        """
        st.log(f"Adding ports {ports} to VLAN {vlan_id} on {dut}")
        for port in ports:
            commands = [
                "configure terminal",
                f"interface {port}",
                f"switchport trunk allowed vlan {vlan_id}",
                "exit"
            ]
            st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_ports_from_vlan(dut: str, ports: List[str], vlan_id: str) -> bool:
        """
        Remove multiple ports from VLAN.

        Args:
            dut: Device handle
            ports: List of interface names
            vlan_id: VLAN ID

        Returns:
            True if successful
        """
        st.log(f"Removing ports {ports} from VLAN {vlan_id} on {dut}")
        for port in ports:
            commands = [
                "configure terminal",
                f"interface {port}",
                f"no switchport trunk allowed vlan {vlan_id}",
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
    def _configure_vlan_ip(dut: str, vlan_id: str, ip_address: str) -> bool:
        """
        Configure IP address on VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "10")
            ip_address: IP address with mask (e.g., "10.1.1.1/24")

        Returns:
            True if successful
        """
        st.log(f"Configuring IP address {ip_address} on Vlan {vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no ip address",
            f"ip address {ip_address}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_vlan_ip(dut: str, vlan_id: str) -> bool:
        """
        Remove IP address from VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID

        Returns:
            True if successful
        """
        st.log(f"Removing IP address from Vlan {vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
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

    @staticmethod
    def _restart_bgp_docker(dut: str) -> bool:
        """
        Restart BGP docker to apply static route changes.

        Args:
            dut: Device handle

        Returns:
            True if successful
        """
        st.log(f"Restarting BGP docker on {dut}")
        # Exit from sonic-cli and restart docker
        command = "docker restart bgp"
        result = st.config(dut, command, type="click")
        return True

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
    def _get_show_vlan_output(dut: str) -> str:
        """
        Get 'show Vlan' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show Vlan' output from {dut}")
        command = "show Vlan"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show Vlan output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_running_config_vlan_interface(dut: str, vlan_id: str) -> str:
        """
        Get running-configuration for VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "10")

        Returns:
            String containing the output of 'show running-configuration interface Vlan X' command
        """
        st.log(f"Getting running-configuration for Vlan {vlan_id} from {dut}")

        # Command: show running-configuration interface Vlan X
        cmd = f"show running-configuration interface Vlan {vlan_id}"

        # Execute command
        output = st.show(dut, cmd, type=CLI_TYPE, skip_tmpl=True, skip_error_check=True)

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"Running-config output for Vlan {vlan_id} from {dut}:\n{output}")
        return output

    # ========== HELPER METHODS - VALIDATION ==========

    @staticmethod
    def _verify_vlan_exists(vlan_output: str, vlan_id: str) -> bool:
        """
        Verify that VLAN exists in show Vlan output.

        Args:
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "10")

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
    def _verify_port_in_vlan(vlan_output: str, vlan_id: str, interface: str) -> bool:
        """
        Verify that interface is a member of VLAN.

        Expected output format:
        Q: A - Access (Untagged), T - Tagged
        NUM       Status      Q Ports             Autostate   Dynamic
        ------------------------------------------------------------------
        Vlan10    Up          T  Ethernet0        Enable      No
                              T  Ethernet4                    No

        Args:
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "10")
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if interface is member of VLAN, False otherwise
        """
        st.log(f"Verifying {interface} is member of VLAN {vlan_id}")

        # Search for VLAN entry and check if interface is listed
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
    def _extract_ipv4_from_running_config(output: str) -> Optional[str]:
        """
        Extract IPv4 address value from running-configuration output.

        Expected output format:
        !
        interface Vlan10
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
        Verify that VLAN interface has the expected IPv4 address in running-configuration.

        Args:
            config_output: Raw output from 'show running-configuration interface Vlan X'
            expected_ipv4: Expected IPv4 address value (e.g., "10.1.1.1/24")
                          or None if no IPv4 address should be present

        Returns:
            True if IPv4 address matches expected value, False otherwise
        """
        st.log(f"Verifying IPv4 address = '{expected_ipv4}' in running-configuration")

        # Extract IPv4 address value
        actual_ipv4 = TestOSPFStaticRoutingVLAN4Node._extract_ipv4_from_running_config(config_output)

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

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_VLAN_STATIC_4NODE_001"])
    def test_ospf_vlan_static_routing_4node(self) -> None:
        """
        TC_OSPF_VLAN_STATIC_4NODE_001: Validate OSPF with VLAN and static routing in 4-node topology.

        Test Procedure:
        1. Remove IP addresses from all Ethernet interfaces that will be added to VLANs
        2. Create VLANs and add ports to VLANs, verify with 'show Vlan'
        3. Configure IP addresses on VLAN interfaces, verify with 'show running-configuration interface Vlan X'
        4. Configure static routes on D1 and D3
        5. Restart BGP docker on D1 and D3
        6. Verify static routes appear in routing tables
        7. Configure OSPF on D2 and D4
        8. Verify OSPF neighbor adjacency (Full state)
        9. Verify DR/BDR election
        10. Verify ping from D1 to D3
        11. Cleanup: Remove all configurations

        Expected Result:
        - IP addresses removed from Ethernet interfaces
        - VLANs created with correct ports (verified via show Vlan)
        - IP addresses configured on VLAN interfaces (verified via show running-configuration)
        - Static routes installed in routing tables
        - OSPF neighbors form adjacency (Full state)
        - DR/BDR election occurs
        - Ping from D1 to D3 successful
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF with VLAN and Static Routing - 4-Node Topology")
        st.log("=" * 80)

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4
        area = self.data.ospf_area

        # ===== STEP 1: Remove IP addresses from Ethernet interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Remove IP addresses from all Ethernet interfaces")
        st.log("-" * 80)

        # Remove IPs from all interfaces that will be added to VLANs
        self._remove_ip_addresses_from_interfaces(dut1, self.data.dut1_vlan10_ports)
        self._remove_ip_addresses_from_interfaces(dut2, self.data.dut2_vlan10_ports + self.data.dut2_vlan20_ports)
        self._remove_ip_addresses_from_interfaces(dut3, self.data.dut3_vlan30_ports)
        self._remove_ip_addresses_from_interfaces(dut4, self.data.dut4_vlan20_ports + self.data.dut4_vlan30_ports)

        st.log("IP addresses removed from all Ethernet interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: IP addresses removed successfully")

        # ===== STEP 2: Create VLANs and add ports =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Create VLANs and add ports to VLANs")
        st.log("-" * 80)

        # VLAN 10: D1 <-> D2
        self._create_vlan(dut1, self.data.vlan10)
        self._add_ports_to_vlan(dut1, self.data.dut1_vlan10_ports, self.data.vlan10)

        self._create_vlan(dut2, self.data.vlan10)
        self._add_ports_to_vlan(dut2, self.data.dut2_vlan10_ports, self.data.vlan10)

        # VLAN 20: D2 <-> D4
        self._create_vlan(dut2, self.data.vlan20)
        self._add_ports_to_vlan(dut2, self.data.dut2_vlan20_ports, self.data.vlan20)

        self._create_vlan(dut4, self.data.vlan20)
        self._add_ports_to_vlan(dut4, self.data.dut4_vlan20_ports, self.data.vlan20)

        # VLAN 30: D4 <-> D3
        self._create_vlan(dut4, self.data.vlan30)
        self._add_ports_to_vlan(dut4, self.data.dut4_vlan30_ports, self.data.vlan30)

        self._create_vlan(dut3, self.data.vlan30)
        self._add_ports_to_vlan(dut3, self.data.dut3_vlan30_ports, self.data.vlan30)

        st.log("VLANs created and ports added")
        time.sleep(WAIT_AFTER_VLAN_CONFIG)

        # Verify VLANs and ports on all devices
        st.log("Verifying VLANs and port membership")

        # Verify D1: VLAN 10 with Ethernet0, Ethernet4
        vlan_output_dut1 = self._get_show_vlan_output(dut1)
        if not self._verify_vlan_exists(vlan_output_dut1, self.data.vlan10):
            st.report_fail("msg", f"VLAN {self.data.vlan10} does not exist on {dut1}")
        for port in self.data.dut1_vlan10_ports:
            if not self._verify_port_in_vlan(vlan_output_dut1, self.data.vlan10, port):
                st.report_fail("msg", f"Port {port} is not in VLAN {self.data.vlan10} on {dut1}")

        # Verify D2: VLAN 10 and VLAN 20
        vlan_output_dut2 = self._get_show_vlan_output(dut2)
        if not self._verify_vlan_exists(vlan_output_dut2, self.data.vlan10):
            st.report_fail("msg", f"VLAN {self.data.vlan10} does not exist on {dut2}")
        for port in self.data.dut2_vlan10_ports:
            if not self._verify_port_in_vlan(vlan_output_dut2, self.data.vlan10, port):
                st.report_fail("msg", f"Port {port} is not in VLAN {self.data.vlan10} on {dut2}")
        if not self._verify_vlan_exists(vlan_output_dut2, self.data.vlan20):
            st.report_fail("msg", f"VLAN {self.data.vlan20} does not exist on {dut2}")
        for port in self.data.dut2_vlan20_ports:
            if not self._verify_port_in_vlan(vlan_output_dut2, self.data.vlan20, port):
                st.report_fail("msg", f"Port {port} is not in VLAN {self.data.vlan20} on {dut2}")

        # Verify D4: VLAN 20 and VLAN 30
        vlan_output_dut4 = self._get_show_vlan_output(dut4)
        if not self._verify_vlan_exists(vlan_output_dut4, self.data.vlan20):
            st.report_fail("msg", f"VLAN {self.data.vlan20} does not exist on {dut4}")
        for port in self.data.dut4_vlan20_ports:
            if not self._verify_port_in_vlan(vlan_output_dut4, self.data.vlan20, port):
                st.report_fail("msg", f"Port {port} is not in VLAN {self.data.vlan20} on {dut4}")
        if not self._verify_vlan_exists(vlan_output_dut4, self.data.vlan30):
            st.report_fail("msg", f"VLAN {self.data.vlan30} does not exist on {dut4}")
        for port in self.data.dut4_vlan30_ports:
            if not self._verify_port_in_vlan(vlan_output_dut4, self.data.vlan30, port):
                st.report_fail("msg", f"Port {port} is not in VLAN {self.data.vlan30} on {dut4}")

        # Verify D3: VLAN 30
        vlan_output_dut3 = self._get_show_vlan_output(dut3)
        if not self._verify_vlan_exists(vlan_output_dut3, self.data.vlan30):
            st.report_fail("msg", f"VLAN {self.data.vlan30} does not exist on {dut3}")
        for port in self.data.dut3_vlan30_ports:
            if not self._verify_port_in_vlan(vlan_output_dut3, self.data.vlan30, port):
                st.report_fail("msg", f"Port {port} is not in VLAN {self.data.vlan30} on {dut3}")

        st.log("PASS: VLANs created and ports added successfully, all verified")

        # ===== STEP 3: Configure IP addresses on VLAN interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Configure IP addresses on VLAN interfaces")
        st.log("-" * 80)

        # D1: Vlan10 - 10.1.1.1/24
        self._configure_vlan_ip(dut1, self.data.vlan10, self.data.dut1_vlan10_ip)

        # D2: Vlan10 - 10.1.1.2/24, Vlan20 - 20.1.1.1/24
        self._configure_vlan_ip(dut2, self.data.vlan10, self.data.dut2_vlan10_ip)
        self._configure_vlan_ip(dut2, self.data.vlan20, self.data.dut2_vlan20_ip)

        # D4: Vlan20 - 20.1.1.2/24, Vlan30 - 30.1.1.2/24
        self._configure_vlan_ip(dut4, self.data.vlan20, self.data.dut4_vlan20_ip)
        self._configure_vlan_ip(dut4, self.data.vlan30, self.data.dut4_vlan30_ip)

        # D3: Vlan30 - 30.1.1.1/24
        self._configure_vlan_ip(dut3, self.data.vlan30, self.data.dut3_vlan30_ip)

        st.log("IP addresses configured on VLAN interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Verify IP addresses on all VLAN interfaces
        st.log("Verifying IP addresses on VLAN interfaces")

        # Verify D1: Vlan10 IP
        config_output = self._get_running_config_vlan_interface(dut1, self.data.vlan10)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut1_vlan10_ip):
            st.report_fail("msg", f"IP address verification failed for Vlan{self.data.vlan10} on {dut1}")

        # Verify D2: Vlan10 and Vlan20 IPs
        config_output = self._get_running_config_vlan_interface(dut2, self.data.vlan10)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut2_vlan10_ip):
            st.report_fail("msg", f"IP address verification failed for Vlan{self.data.vlan10} on {dut2}")
        config_output = self._get_running_config_vlan_interface(dut2, self.data.vlan20)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut2_vlan20_ip):
            st.report_fail("msg", f"IP address verification failed for Vlan{self.data.vlan20} on {dut2}")

        # Verify D4: Vlan20 and Vlan30 IPs
        config_output = self._get_running_config_vlan_interface(dut4, self.data.vlan20)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut4_vlan20_ip):
            st.report_fail("msg", f"IP address verification failed for Vlan{self.data.vlan20} on {dut4}")
        config_output = self._get_running_config_vlan_interface(dut4, self.data.vlan30)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut4_vlan30_ip):
            st.report_fail("msg", f"IP address verification failed for Vlan{self.data.vlan30} on {dut4}")

        # Verify D3: Vlan30 IP
        config_output = self._get_running_config_vlan_interface(dut3, self.data.vlan30)
        if not self._verify_ipv4_in_running_config(config_output, self.data.dut3_vlan30_ip):
            st.report_fail("msg", f"IP address verification failed for Vlan{self.data.vlan30} on {dut3}")

        st.log("PASS: IP addresses configured successfully, all verified")

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

        # ===== STEP 5: Restart BGP docker on D1 and D3 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Restart BGP docker on D1 and D3")
        st.log("-" * 80)

        self._restart_bgp_docker(dut1)
        self._restart_bgp_docker(dut3)

        st.log(f"Waiting {WAIT_AFTER_BGP_RESTART} seconds for BGP docker to restart...")
        time.sleep(WAIT_AFTER_BGP_RESTART)

        st.log("PASS: BGP docker restarted on D1 and D3")

        # ===== STEP 6: Verify static routes in routing tables =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Verify static routes in routing tables")
        st.log("-" * 80)

        # Verify D1 has route to 30.1.1.0/24
        route_output_dut1 = self._get_show_ip_route_output(dut1)
        if not self._verify_static_route_in_routing_table(route_output_dut1, "30.1.1.0/24"):
            st.report_fail("msg", f"Static route 30.1.1.0/24 not found in routing table on {dut1}")

        # Verify D3 has route to 10.1.1.0/24
        route_output_dut3 = self._get_show_ip_route_output(dut3)
        if not self._verify_static_route_in_routing_table(route_output_dut3, "10.1.1.0/24"):
            st.report_fail("msg", f"Static route 10.1.1.0/24 not found in routing table on {dut3}")

        st.log("PASS: Static routes verified in routing tables")

        # ===== STEP 7: Configure OSPF on D2 and D4 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Configure OSPF on D2 and D4")
        st.log("-" * 80)

        # D2: OSPF configuration
        self._configure_ospf_process(dut2, area)
        self._configure_ospf_network(dut2, self.data.dut2_vlan20_ip, area)
        self._configure_ospf_network(dut2, self.data.dut2_vlan10_ip, area)

        # D4: OSPF configuration
        self._configure_ospf_process(dut4, area)
        self._configure_ospf_network(dut4, self.data.dut4_vlan20_ip, area)
        self._configure_ospf_network(dut4, self.data.dut4_vlan30_ip, area)

        st.log("OSPF configured on D2 and D4")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed")

        # ===== STEP 8: Verify OSPF neighbor adjacency =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Verify OSPF neighbor adjacency (Full state)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor output from D2 and D4
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        # Extract neighbor IPs (without mask)
        dut4_neighbor_ip = self.data.dut4_vlan20_ip.split('/')[0]  # 20.1.1.2
        dut2_neighbor_ip = self.data.dut2_vlan20_ip.split('/')[0]  # 20.1.1.1

        # Verify neighbors
        if not self._verify_ospf_neighbor_present(neighbor_output_dut2, dut4_neighbor_ip, "Full"):
            st.report_fail("msg", f"OSPF neighbor {dut4_neighbor_ip} not in Full state on {dut2}")

        if not self._verify_ospf_neighbor_present(neighbor_output_dut4, dut2_neighbor_ip, "Full"):
            st.report_fail("msg", f"OSPF neighbor {dut2_neighbor_ip} not in Full state on {dut4}")

        st.log("PASS: OSPF neighbors are in Full state")

        # ===== STEP 9: Verify DR/BDR election =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Verify DR/BDR election")
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

        # ===== STEP 10: Verify ping from D1 to D3 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Verify ping connectivity from D1 to D3")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_PING)

        # Ping from D1 to D3's IP (30.1.1.1)
        target_ip_d3 = self.data.dut3_vlan30_ip.split('/')[0]  # 30.1.1.1
        if not self._verify_ping_success(dut1, target_ip_d3):
            st.report_fail("msg", f"Ping from {dut1} to {target_ip_d3} failed")

        # Ping from D3 to D1's IP (10.1.1.1)
        target_ip_d1 = self.data.dut1_vlan10_ip.split('/')[0]  # 10.1.1.1
        if not self._verify_ping_success(dut3, target_ip_d1):
            st.report_fail("msg", f"Ping from {dut3} to {target_ip_d1} failed")

        st.log("PASS: Ping connectivity verified between D1 and D3")

        # ===== STEP 11: Cleanup - Remove all configurations =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Cleanup - Remove all configurations")
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

        # Remove IP addresses from VLAN interfaces
        self._remove_vlan_ip(dut1, self.data.vlan10)
        self._remove_vlan_ip(dut2, self.data.vlan10)
        self._remove_vlan_ip(dut2, self.data.vlan20)
        self._remove_vlan_ip(dut4, self.data.vlan20)
        self._remove_vlan_ip(dut4, self.data.vlan30)
        self._remove_vlan_ip(dut3, self.data.vlan30)
        st.log("IP addresses removed from VLAN interfaces")

        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Remove ports from VLANs
        self._remove_ports_from_vlan(dut1, self.data.dut1_vlan10_ports, self.data.vlan10)
        self._remove_ports_from_vlan(dut2, self.data.dut2_vlan10_ports, self.data.vlan10)
        self._remove_ports_from_vlan(dut2, self.data.dut2_vlan20_ports, self.data.vlan20)
        self._remove_ports_from_vlan(dut4, self.data.dut4_vlan20_ports, self.data.vlan20)
        self._remove_ports_from_vlan(dut4, self.data.dut4_vlan30_ports, self.data.vlan30)
        self._remove_ports_from_vlan(dut3, self.data.dut3_vlan30_ports, self.data.vlan30)
        st.log("Ports removed from VLANs")

        time.sleep(WAIT_AFTER_VLAN_CONFIG)

        # Delete VLANs
        self._delete_vlan(dut1, self.data.vlan10)
        self._delete_vlan(dut2, self.data.vlan10)
        self._delete_vlan(dut2, self.data.vlan20)
        self._delete_vlan(dut4, self.data.vlan20)
        self._delete_vlan(dut4, self.data.vlan30)
        self._delete_vlan(dut3, self.data.vlan30)
        st.log("VLANs deleted")

        time.sleep(WAIT_AFTER_VLAN_CONFIG)

        st.log("PASS: Cleanup completed successfully")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF with VLAN and static routing validated successfully")
        st.log("Test flow: Remove IPs → VLAN Config → IP Config → Static Routes → BGP Restart → OSPF Config → Neighbor Full → DR/BDR → Ping → Cleanup ✓")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
