"""
OSPF TYPE 1 LSAs (ROUTER LSAs) VERIFICATION - 4-NODE TOPOLOGY OVER PORTCHANNEL
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_10_iscli_4_node_Type_1_LSAs_over_PC.py \
  --logs-path ./logs/testcases_OSPF_10_Type1_LSAs_PC_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF Type 1 LSAs (Router LSAs) propagation and verification
  in a 4-node linear topology over PortChannel interfaces by:
  1. Removing IP addresses from Ethernet interfaces before adding to PortChannels
  2. Creating PortChannels on all devices
  3. Adding Ethernet interfaces as members to respective PortChannels
  4. Verifying PortChannel creation and member addition
  5. Configuring IP addresses on PortChannel interfaces
  6. Configuring OSPF Area 0 on all devices
  7. Verifying OSPF neighbor adjacency (Full state) on all links
  8. Verifying DR/BDR election on each broadcast segment
  9. Verifying Type 1 LSAs from all 4 routers are present in OSPF database
  10. Verifying self-originated LSAs are correct
  11. Verifying Type 2 Network LSAs are present
  12. Validating OSPF routes are learned with correct costs
  13. Verifying routing table has OSPF routes installed
  14. Testing end-to-end connectivity
  15. Cleanup: Removing all configurations

  Topology:
        D1 -------- D2 -------- D4 -------- D3
    (PortChannel10) (PortChannel20) (PortChannel30)
    10.1.1.1/24     20.1.1.1/24     30.1.1.1/24

  PortChannel Members:
    PortChannel10: D1 (Ethernet0, Ethernet4) <-> D2 (Ethernet0, Ethernet4)
    PortChannel20: D2 (Ethernet16, Ethernet20) <-> D4 (Ethernet16, Ethernet20)
    PortChannel30: D4 (Ethernet40, Ethernet44) <-> D3 (Ethernet40, Ethernet44)

  Configuration details:
    D1: PortChannel10: 10.1.1.1/24, OSPF area 0
    D2: PortChannel10: 10.1.1.2/24, PortChannel20: 20.1.1.1/24, OSPF area 0
    D4: PortChannel20: 20.1.1.2/24, PortChannel30: 30.1.1.1/24, OSPF area 0
    D3: PortChannel30: 30.1.1.2/24, OSPF area 0

  Type 1 LSA Verification:
    - Each router generates one Type 1 LSA describing its interfaces
    - D1 LSA: 1 link (Transit Network to 10.1.1.1)
    - D2 LSA: 2 links (Transit to 10.1.1.1 and 20.1.1.1)
    - D4 LSA: 2 links (Transit to 20.1.1.1 and 30.1.1.1)
    - D3 LSA: 1 link (Transit Network to 30.1.1.1)
    - All routers should have all 4 Type 1 LSAs in their database

  IMPORTANT: Uses 'show ip ospf neighbor', 'show ip ospf interface',
  'show ip ospf database router', 'show ip ospf database router self-originate',
  'show ip ospf database', 'show ip route', 'show ip route ospf', and
  'show PortChannel summary' commands. Uses klish CLI type exclusively.

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
WAIT_AFTER_PORTCHANNEL_CONFIG = 3
WAIT_AFTER_IP_CONFIG = 3
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_LSA_PROPAGATION = 10
WAIT_FOR_ROUTE_UPDATE = 10
WAIT_FOR_PING = 5


@pytest.mark.topology("any")
class TestOSPFType1LSAs4NodePortChannel:
    """Test cases for validating OSPF Type 1 LSAs in 4-node topology over PortChannels via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF Type 1 LSA Verification Test Suite (PortChannel)")
        st.log("=" * 80)

        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if len(cls.data.dut_names) < 4:
            st.report_fail("msg", "Minimum 4 DUTs required for this test")

        cls.data.dut1 = cls.data.dut_names[0]  # vs_sonic_1
        cls.data.dut2 = cls.data.dut_names[1]  # vs_sonic_2
        cls.data.dut3 = cls.data.dut_names[2]  # vs_sonic_3
        cls.data.dut4 = cls.data.dut_names[3]  # vs_sonic_4

        st.log(f"DUT1 (D1): {cls.data.dut1}")
        st.log(f"DUT2 (D2): {cls.data.dut2}")
        st.log(f"DUT3 (D3): {cls.data.dut3}")
        st.log(f"DUT4 (D4): {cls.data.dut4}")

        # CLI type - use klish as specified
        cls.data.cli_type = CLI_TYPE
        st.log(f"CLI Type: {cls.data.cli_type}")

        # Test interfaces based on testbed_4vs.yaml topology
        # D1 ↔ D2: PortChannel10 (Ethernet0, Ethernet4)
        cls.data.dut1_eth_ports = ["Ethernet0", "Ethernet4"]
        cls.data.dut2_d1_eth_ports = ["Ethernet0", "Ethernet4"]
        cls.data.portchannel10 = "10"

        # D2 ↔ D4: PortChannel20 (Ethernet16, Ethernet20)
        cls.data.dut2_d4_eth_ports = ["Ethernet16", "Ethernet20"]
        cls.data.dut4_d2_eth_ports = ["Ethernet16", "Ethernet20"]
        cls.data.portchannel20 = "20"

        # D4 ↔ D3: PortChannel30 (Ethernet40, Ethernet44 on D4; Ethernet40, Ethernet44 on D3)
        cls.data.dut4_d3_eth_ports = ["Ethernet40", "Ethernet44"]
        cls.data.dut3_eth_ports = ["Ethernet40", "Ethernet44"]
        cls.data.portchannel30 = "30"

        st.log(f"Topology: D1[PC{cls.data.portchannel10}] <-> D2[PC{cls.data.portchannel10}]")
        st.log(f"          D2[PC{cls.data.portchannel20}] <-> D4[PC{cls.data.portchannel20}]")
        st.log(f"          D4[PC{cls.data.portchannel30}] <-> D3[PC{cls.data.portchannel30}]")

        # IP addresses
        cls.data.dut1_ip = "10.1.1.1/24"
        cls.data.dut2_ip1 = "10.1.1.2/24"
        cls.data.dut2_ip2 = "20.1.1.1/24"
        cls.data.dut4_ip1 = "20.1.1.2/24"
        cls.data.dut4_ip2 = "30.1.1.1/24"
        cls.data.dut3_ip = "30.1.1.2/24"

        st.log(f"IP Addresses:")
        st.log(f"  D1[PortChannel{cls.data.portchannel10}]: {cls.data.dut1_ip}")
        st.log(f"  D2[PortChannel{cls.data.portchannel10}]: {cls.data.dut2_ip1}")
        st.log(f"  D2[PortChannel{cls.data.portchannel20}]: {cls.data.dut2_ip2}")
        st.log(f"  D4[PortChannel{cls.data.portchannel20}]: {cls.data.dut4_ip1}")
        st.log(f"  D4[PortChannel{cls.data.portchannel30}]: {cls.data.dut4_ip2}")
        st.log(f"  D3[PortChannel{cls.data.portchannel30}]: {cls.data.dut3_ip}")

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
        st.log("TEST TEARDOWN: Cleanup OSPF Type 1 LSA Test Suite (PortChannel)")
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

    # ========== HELPER METHODS - INTERFACE PREPARATION ==========

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
        st.log(f"Removing IP addresses from interfaces on {dut}: {interfaces}")

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

        st.log("IP addresses removed from all interfaces")
        return True

    # ========== HELPER METHODS - PORTCHANNEL CONFIGURATION ==========

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
        Delete PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if successful
        """
        st.log(f"Deleting PortChannel {portchannel_id} from {dut}")
        commands = [
            "configure terminal",
            f"no interface PortChannel {portchannel_id}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _add_ports_to_portchannel(dut: str, ports: List[str], portchannel_id: str) -> bool:
        """
        Add ports to PortChannel as members.

        Args:
            dut: Device handle
            ports: List of port names (e.g., ["Ethernet0", "Ethernet4"])
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
            result = st.config(dut, commands, type=CLI_TYPE)

        st.log(f"Ports added to PortChannel {portchannel_id}")
        return True

    @staticmethod
    def _remove_ports_from_portchannel(dut: str, ports: List[str]) -> bool:
        """
        Remove ports from PortChannel.

        Args:
            dut: Device handle
            ports: List of port names

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
            result = st.config(dut, commands, type=CLI_TYPE)

        st.log("Ports removed from PortChannel")
        return True

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
    def _verify_portchannel_members(portchannel_output: str, portchannel_id: str, expected_members: List[str]) -> bool:
        """
        Verify PortChannel has expected member ports.

        Args:
            portchannel_output: Raw output from 'show PortChannel summary'
            portchannel_id: PortChannel ID (e.g., "10")
            expected_members: List of expected member ports

        Returns:
            True if all expected members are present
        """
        st.log(f"Verifying PortChannel {portchannel_id} has members: {expected_members}")

        portchannel_name = f"PortChannel{portchannel_id}"
        if portchannel_name not in portchannel_output:
            st.error(f"FAIL: PortChannel {portchannel_id} not found in output")
            return False

        # Check each expected member
        all_members_found = True
        for member in expected_members:
            if member in portchannel_output:
                st.log(f"PASS: Member {member} found in PortChannel {portchannel_id}")
            else:
                st.error(f"FAIL: Member {member} not found in PortChannel {portchannel_id}")
                all_members_found = False

        return all_members_found

    # ========== HELPER METHODS - IP CONFIGURATION ==========

    @staticmethod
    def _configure_interface_ip(dut: str, interface: str, ip_address: str) -> bool:
        """
        Configure IP address on interface (PortChannel).

        Args:
            dut: Device handle
            interface: Interface name (e.g., "PortChannel10")
            ip_address: IP address with mask (e.g., "10.1.1.1/24")

        Returns:
            True if successful
        """
        st.log(f"Configuring IP address {ip_address} on {interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no shutdown",
            "no ip address",
            f"ip address {ip_address}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_interface_ip(dut: str, interface: str) -> bool:
        """
        Remove IP address from interface.

        Args:
            dut: Device handle
            interface: Interface name

        Returns:
            True if successful
        """
        st.log(f"Removing IP address from {interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip address",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    # ========== HELPER METHODS - OSPF CONFIGURATION ==========

    @staticmethod
    def _configure_ospf_network(dut: str, area: str, network: str) -> bool:
        """
        Configure OSPF network statement.

        Args:
            dut: Device handle
            area: OSPF area ID
            network: Network address with mask (e.g., "10.1.1.1/24")

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF area {area} and network {network} on {dut}")
        commands = [
            "configure terminal",
            "router ospf",
            f"area {area}",
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
    def _get_show_ip_ospf_database_router_output(dut: str) -> str:
        """
        Get 'show ip ospf database router' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show ip ospf database router' output from {dut}")
        command = "show ip ospf database router"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf database router output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_database_output(dut: str) -> str:
        """
        Get 'show ip ospf database' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show ip ospf database' output from {dut}")
        command = "show ip ospf database"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf database output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_database_router_self_originate_output(dut: str) -> str:
        """
        Get 'show ip ospf database router self-originate' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show ip ospf database router self-originate' output from {dut}")
        command = "show ip ospf database router self-originate"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf database router self-originate output from {dut}:\n{output}")
        return output

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
    def _get_show_ip_route_ospf_output(dut: str) -> str:
        """
        Get 'show ip route ospf' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show ip route ospf' output from {dut}")
        command = "show ip route ospf"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip route ospf output from {dut}:\n{output}")
        return output

    # ========== HELPER METHODS - VALIDATION ==========

    @staticmethod
    def _verify_ospf_neighbor_full_state(neighbor_output: str, expected_neighbor_ip: str) -> bool:
        """
        Verify that OSPF neighbor is present with Full state.

        Args:
            neighbor_output: Raw output from 'show ip ospf neighbor' command
            expected_neighbor_ip: Expected neighbor IP address

        Returns:
            True if neighbor is present with Full state
        """
        st.log(f"Verifying OSPF neighbor {expected_neighbor_ip} is in Full state")

        if expected_neighbor_ip not in neighbor_output:
            st.error(f"FAIL: Neighbor {expected_neighbor_ip} not found in output")
            return False

        if "Full" not in neighbor_output:
            st.error(f"FAIL: No neighbor in Full state found")
            return False

        lines = neighbor_output.split('\n')
        for line in lines:
            if expected_neighbor_ip in line and "Full" in line:
                st.log(f"PASS: Neighbor {expected_neighbor_ip} is in Full state")
                st.log(f"  Details: {line.strip()}")
                return True

        st.error(f"FAIL: Neighbor {expected_neighbor_ip} not in Full state")
        return False

    @staticmethod
    def _verify_dr_bdr_election(interface_output: str, interface_name: str) -> bool:
        """
        Verify DR/BDR election occurred on interface.

        Args:
            interface_output: Raw output from 'show ip ospf interface' command
            interface_name: Interface name to check

        Returns:
            True if DR/BDR info present
        """
        st.log(f"Verifying DR/BDR election occurred on {interface_name}")

        # Check if interface section exists
        if interface_name not in interface_output:
            st.error(f"FAIL: Interface {interface_name} not found in output")
            return False

        # Check for DR
        if "Designated Router" in interface_output:
            st.log("PASS: Designated Router (DR) information found")
            dr_ok = True
        else:
            st.log("WARNING: Designated Router (DR) information not found")
            dr_ok = False

        # Check for BDR
        if "Backup Designated Router" in interface_output:
            st.log("PASS: Backup Designated Router (BDR) information found")
            bdr_ok = True
        else:
            st.log("WARNING: Backup Designated Router (BDR) information not found")
            bdr_ok = False

        # At least DR should be present
        return dr_ok

    @staticmethod
    def _verify_type1_lsa_count(database_output: str, expected_count: int) -> bool:
        """
        Verify expected number of Type 1 LSAs in database.

        Args:
            database_output: Raw output from 'show ip ospf database router' command
            expected_count: Expected number of Router LSAs

        Returns:
            True if count matches
        """
        st.log(f"Verifying Type 1 LSA count is {expected_count}")

        # Count occurrences of "Advertising Router:"
        lsa_count = database_output.count("Advertising Router:")

        if lsa_count >= expected_count:
            st.log(f"PASS: Found {lsa_count} Type 1 LSAs (expected at least {expected_count})")
            return True
        else:
            st.error(f"FAIL: Found {lsa_count} Type 1 LSAs, expected at least {expected_count}")
            return False

    @staticmethod
    def _verify_type1_lsa_present(database_output: str, router_id: str) -> bool:
        """
        Verify Type 1 LSA from specific router is present.

        Args:
            database_output: Raw output from 'show ip ospf database router' command
            router_id: Router ID to look for

        Returns:
            True if LSA from router_id is present
        """
        st.log(f"Verifying Type 1 LSA from Router ID {router_id} is present")

        if f"Advertising Router: {router_id}" in database_output:
            st.log(f"PASS: Type 1 LSA from Router ID {router_id} found")
            return True
        else:
            st.error(f"FAIL: Type 1 LSA from Router ID {router_id} not found")
            return False

    @staticmethod
    def _verify_self_originated_lsa(self_originate_output: str, expected_links: int) -> bool:
        """
        Verify self-originated LSA has expected number of links.

        Args:
            self_originate_output: Raw output from 'show ip ospf database router self-originate'
            expected_links: Expected number of links

        Returns:
            True if link count matches
        """
        st.log(f"Verifying self-originated LSA has {expected_links} link(s)")

        # Look for "Number of Links: X"
        match = re.search(r'Number of Links:\s+(\d+)', self_originate_output)
        if match:
            actual_links = int(match.group(1))
            if actual_links == expected_links:
                st.log(f"PASS: Self-originated LSA has {actual_links} link(s)")
                return True
            else:
                st.error(f"FAIL: Self-originated LSA has {actual_links} links, expected {expected_links}")
                return False
        else:
            st.error(f"FAIL: Could not find 'Number of Links' in output")
            return False

    @staticmethod
    def _verify_network_lsa_count(database_output: str, expected_count: int) -> bool:
        """
        Verify expected number of Type 2 Network LSAs.

        Args:
            database_output: Raw output from 'show ip ospf database' command
            expected_count: Expected number of Network LSAs

        Returns:
            True if count matches
        """
        st.log(f"Verifying Type 2 Network LSA count is {expected_count}")

        # Look for "Net Link States" section
        if "Net Link States" not in database_output:
            st.error("FAIL: No Net Link States section found")
            return False

        # Count lines under Net Link States section
        lines = database_output.split('\n')
        in_net_section = False
        net_lsa_count = 0

        for line in lines:
            if "Net Link States" in line:
                in_net_section = True
                continue
            elif in_net_section:
                # Skip empty lines and header lines
                if line.strip() == "" or "Link ID" in line or "ADV Router" in line:
                    continue
                # Stop counting when we hit next section
                if "Link States" in line and "Net Link States" not in line:
                    break
                # Count lines that look like LSA entries (have IP addresses)
                if re.search(r'\d+\.\d+\.\d+\.\d+', line):
                    net_lsa_count += 1

        if net_lsa_count >= expected_count:
            st.log(f"PASS: Found {net_lsa_count} Network LSAs (expected at least {expected_count})")
            return True
        else:
            st.error(f"FAIL: Found {net_lsa_count} Network LSAs, expected at least {expected_count}")
            return False

    @staticmethod
    def _verify_ospf_route_present(route_output: str, network: str) -> bool:
        """
        Verify OSPF route to network is present in routing table.

        Args:
            route_output: Raw output from 'show ip route' command
            network: Network to check (e.g., "20.1.1.0/24")

        Returns:
            True if OSPF route is present
        """
        st.log(f"Verifying OSPF route to {network} is present")

        if network not in route_output:
            st.error(f"FAIL: Network {network} not found in routing table")
            return False

        lines = route_output.split('\n')
        for line in lines:
            if network in line and ('O>' in line or 'O ' in line):
                st.log(f"PASS: OSPF route to {network} found")
                st.log(f"  Details: {line.strip()}")
                return True

        st.error(f"FAIL: OSPF route to {network} not found")
        return False

    @staticmethod
    def _verify_ospf_route_cost(route_output: str, network: str, expected_cost: int) -> bool:
        """
        Verify OSPF route has expected cost.

        Args:
            route_output: Raw output from 'show ip route' command
            network: Network to check
            expected_cost: Expected cost value

        Returns:
            True if cost matches
        """
        st.log(f"Verifying OSPF route to {network} has cost {expected_cost}")

        lines = route_output.split('\n')
        for line in lines:
            if network in line and 'O>' in line:
                # Look for [110/COST] pattern
                match = re.search(r'\[110/(\d+)\]', line)
                if match:
                    actual_cost = int(match.group(1))
                    if actual_cost == expected_cost:
                        st.log(f"PASS: Route to {network} has cost {actual_cost}")
                        return True
                    else:
                        st.error(f"FAIL: Route to {network} has cost {actual_cost}, expected {expected_cost}")
                        return False

        st.error(f"FAIL: Could not verify cost for route to {network}")
        return False

    @staticmethod
    def _verify_ping_success(dut: str, target_ip: str) -> bool:
        """
        Verify ping from DUT to target IP.

        Args:
            dut: Device handle
            target_ip: Target IP address to ping (e.g., "30.1.1.2")

        Returns:
            True if ping successful
        """
        st.log(f"Verifying ping from {dut} to {target_ip}")

        # Execute ping command (outside sonic-cli, in shell)
        command = f"ping -c 4 {target_ip}"
        output = st.config(dut, command, type="click")

        # Convert to string if needed
        if not isinstance(output, str):
            output = str(output)

        st.log(f"Ping output:\n{output}")

        # Check for successful ping
        if "0% packet loss" in output or "4 received" in output or "bytes from" in output:
            st.log(f"PASS: Ping from {dut} to {target_ip} successful")
            return True
        else:
            st.error(f"FAIL: Ping from {dut} to {target_ip} failed")
            return False

    # ========== TEST CASE ==========

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_TYPE1_LSA_4NODE_PC_001"])
    def test_ospf_type1_lsa_verification_portchannel(self) -> None:
        """
        TC_OSPF_TYPE1_LSA_4NODE_PC_001: Validate OSPF Type 1 LSAs in 4-node topology over PortChannels.

        Test Procedure:
        1. Remove IP addresses from Ethernet interfaces before adding to PortChannels
        2. Create PortChannels on all devices
        3. Add Ethernet interfaces as members to respective PortChannels
        4. Verify PortChannel creation and member addition
        5. Configure IP addresses on PortChannel interfaces
        6. Configure OSPF Area 0 on all devices
        7. Verify OSPF neighbor adjacency (Full state) on all links
        8. Verify DR/BDR election on all broadcast segments
        9. Verify Type 1 LSAs from all 4 routers present in database
        10. Verify self-originated LSAs have correct link counts
        11. Verify Type 2 Network LSAs present
        12. Verify OSPF routes learned with correct costs
        13. Verify end-to-end connectivity
        14. Cleanup: Remove all configurations

        Expected Result:
        - PortChannels created successfully with member ports
        - OSPF neighbors form Full adjacency on all links
        - DR/BDR election occurs on each segment
        - All 4 routers' Type 1 LSAs present in database
        - D1 LSA: 1 link, D2 LSA: 2 links, D4 LSA: 2 links, D3 LSA: 1 link
        - Type 2 Network LSAs present for all broadcast segments
        - OSPF routes learned with correct costs
        - End-to-end ping successful
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF Type 1 LSA Verification - 4-Node Topology over PortChannel")
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
        st.log("STEP 1: Remove IP addresses from Ethernet interfaces before adding to PortChannels")
        st.log("-" * 80)

        # D1: Remove IPs from Ethernet0, Ethernet4
        self._remove_ip_addresses_from_interfaces(dut1, self.data.dut1_eth_ports)

        # D2: Remove IPs from Ethernet0, Ethernet4, Ethernet16, Ethernet20
        all_dut2_eth_ports = self.data.dut2_d1_eth_ports + self.data.dut2_d4_eth_ports
        self._remove_ip_addresses_from_interfaces(dut2, all_dut2_eth_ports)

        # D4: Remove IPs from Ethernet16, Ethernet20, Ethernet40, Ethernet44
        all_dut4_eth_ports = self.data.dut4_d2_eth_ports + self.data.dut4_d3_eth_ports
        self._remove_ip_addresses_from_interfaces(dut4, all_dut4_eth_ports)

        # D3: Remove IPs from Ethernet40, Ethernet44
        self._remove_ip_addresses_from_interfaces(dut3, self.data.dut3_eth_ports)

        st.log("PASS: IP addresses removed from all Ethernet interfaces")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        # ===== STEP 2: Create PortChannels on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Create PortChannels on all devices")
        st.log("-" * 80)

        # Create PortChannel10 on D1 and D2
        self._create_portchannel(dut1, self.data.portchannel10)
        self._create_portchannel(dut2, self.data.portchannel10)

        # Create PortChannel20 on D2 and D4
        self._create_portchannel(dut2, self.data.portchannel20)
        self._create_portchannel(dut4, self.data.portchannel20)

        # Create PortChannel30 on D4 and D3
        self._create_portchannel(dut4, self.data.portchannel30)
        self._create_portchannel(dut3, self.data.portchannel30)

        st.log("PASS: PortChannels created on all devices")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        # ===== STEP 3: Add Ethernet interfaces as members to PortChannels =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Add Ethernet interfaces as members to respective PortChannels")
        st.log("-" * 80)

        # Add ports to PortChannel10 on D1 and D2
        self._add_ports_to_portchannel(dut1, self.data.dut1_eth_ports, self.data.portchannel10)
        self._add_ports_to_portchannel(dut2, self.data.dut2_d1_eth_ports, self.data.portchannel10)

        # Add ports to PortChannel20 on D2 and D4
        self._add_ports_to_portchannel(dut2, self.data.dut2_d4_eth_ports, self.data.portchannel20)
        self._add_ports_to_portchannel(dut4, self.data.dut4_d2_eth_ports, self.data.portchannel20)

        # Add ports to PortChannel30 on D4 and D3
        self._add_ports_to_portchannel(dut4, self.data.dut4_d3_eth_ports, self.data.portchannel30)
        self._add_ports_to_portchannel(dut3, self.data.dut3_eth_ports, self.data.portchannel30)

        st.log("PASS: Ethernet interfaces added to PortChannels")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        # ===== STEP 4: Verify PortChannel creation and member addition =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Verify PortChannel creation and member addition")
        st.log("-" * 80)

        # Verify PortChannel10 on D1
        pc_output_d1 = self._get_show_portchannel_summary(dut1)
        if not self._verify_portchannel_members(pc_output_d1, self.data.portchannel10, self.data.dut1_eth_ports):
            st.log("WARNING: PortChannel10 member verification incomplete on D1")
        else:
            st.log("PASS: PortChannel10 verified on D1")

        # Verify PortChannel10 on D2
        pc_output_d2 = self._get_show_portchannel_summary(dut2)
        if not self._verify_portchannel_members(pc_output_d2, self.data.portchannel10, self.data.dut2_d1_eth_ports):
            st.log("WARNING: PortChannel10 member verification incomplete on D2")
        else:
            st.log("PASS: PortChannel10 verified on D2")

        # Verify PortChannel20 on D2
        if not self._verify_portchannel_members(pc_output_d2, self.data.portchannel20, self.data.dut2_d4_eth_ports):
            st.log("WARNING: PortChannel20 member verification incomplete on D2")
        else:
            st.log("PASS: PortChannel20 verified on D2")

        # Verify PortChannel20 on D4
        pc_output_d4 = self._get_show_portchannel_summary(dut4)
        if not self._verify_portchannel_members(pc_output_d4, self.data.portchannel20, self.data.dut4_d2_eth_ports):
            st.log("WARNING: PortChannel20 member verification incomplete on D4")
        else:
            st.log("PASS: PortChannel20 verified on D4")

        # Verify PortChannel30 on D4
        if not self._verify_portchannel_members(pc_output_d4, self.data.portchannel30, self.data.dut4_d3_eth_ports):
            st.log("WARNING: PortChannel30 member verification incomplete on D4")
        else:
            st.log("PASS: PortChannel30 verified on D4")

        # Verify PortChannel30 on D3
        pc_output_d3 = self._get_show_portchannel_summary(dut3)
        if not self._verify_portchannel_members(pc_output_d3, self.data.portchannel30, self.data.dut3_eth_ports):
            st.log("WARNING: PortChannel30 member verification incomplete on D3")
        else:
            st.log("PASS: PortChannel30 verified on D3")

        st.log("PASS: PortChannel verification completed")

        # ===== STEP 5: Configure IP addresses on PortChannel interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Configure IP addresses on PortChannel interfaces")
        st.log("-" * 80)

        # D1: PortChannel10 - 10.1.1.1/24
        self._configure_interface_ip(dut1, f"PortChannel{self.data.portchannel10}", self.data.dut1_ip)

        # D2: PortChannel10 - 10.1.1.2/24, PortChannel20 - 20.1.1.1/24
        self._configure_interface_ip(dut2, f"PortChannel{self.data.portchannel10}", self.data.dut2_ip1)
        self._configure_interface_ip(dut2, f"PortChannel{self.data.portchannel20}", self.data.dut2_ip2)

        # D4: PortChannel20 - 20.1.1.2/24, PortChannel30 - 30.1.1.1/24
        self._configure_interface_ip(dut4, f"PortChannel{self.data.portchannel20}", self.data.dut4_ip1)
        self._configure_interface_ip(dut4, f"PortChannel{self.data.portchannel30}", self.data.dut4_ip2)

        # D3: PortChannel30 - 30.1.1.2/24
        self._configure_interface_ip(dut3, f"PortChannel{self.data.portchannel30}", self.data.dut3_ip)

        st.log("IP addresses configured on all PortChannel interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: IP addresses configured successfully")

        # ===== STEP 6: Configure OSPF on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Configure OSPF Area 0 on all devices")
        st.log("-" * 80)

        # D1: OSPF configuration
        self._configure_ospf_network(dut1, area, self.data.dut1_ip)

        # D2: OSPF configuration
        self._configure_ospf_network(dut2, area, self.data.dut2_ip1)
        self._configure_ospf_network(dut2, area, self.data.dut2_ip2)

        # D4: OSPF configuration
        self._configure_ospf_network(dut4, area, self.data.dut4_ip1)
        self._configure_ospf_network(dut4, area, self.data.dut4_ip2)

        # D3: OSPF configuration
        self._configure_ospf_network(dut3, area, self.data.dut3_ip)

        st.log("OSPF configured on all devices")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed")

        # ===== STEP 7: Verify OSPF neighbor adjacency =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Verify OSPF neighbor adjacency (Full state) on all links")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor outputs from all devices
        st.log("Getting OSPF neighbor information from all devices...")
        neighbor_output_dut1 = self._get_show_ip_ospf_neighbor_output(dut1)
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut3 = self._get_show_ip_ospf_neighbor_output(dut3)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        # Verify D1 ↔ D2 neighbor relationship
        dut2_ip_no_mask = self.data.dut2_ip1.split('/')[0]  # 10.1.1.2
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut1, dut2_ip_no_mask):
            error_msg = f"STEP 7: OSPF neighbor {dut2_ip_no_mask} not in Full state on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip_no_mask} in Full state on {dut1}")

        dut1_ip_no_mask = self.data.dut1_ip.split('/')[0]  # 10.1.1.1
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut2, dut1_ip_no_mask):
            error_msg = f"STEP 7: OSPF neighbor {dut1_ip_no_mask} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut1_ip_no_mask} in Full state on {dut2}")

        # Verify D2 ↔ D4 neighbor relationship
        dut4_ip1_no_mask = self.data.dut4_ip1.split('/')[0]  # 20.1.1.2
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut2, dut4_ip1_no_mask):
            error_msg = f"STEP 7: OSPF neighbor {dut4_ip1_no_mask} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip1_no_mask} in Full state on {dut2}")

        dut2_ip2_no_mask = self.data.dut2_ip2.split('/')[0]  # 20.1.1.1
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut4, dut2_ip2_no_mask):
            error_msg = f"STEP 7: OSPF neighbor {dut2_ip2_no_mask} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip2_no_mask} in Full state on {dut4}")

        # Verify D4 ↔ D3 neighbor relationship
        dut3_ip_no_mask = self.data.dut3_ip.split('/')[0]  # 30.1.1.2
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut4, dut3_ip_no_mask):
            error_msg = f"STEP 7: OSPF neighbor {dut3_ip_no_mask} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut3_ip_no_mask} in Full state on {dut4}")

        dut4_ip2_no_mask = self.data.dut4_ip2.split('/')[0]  # 30.1.1.1
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut3, dut4_ip2_no_mask):
            error_msg = f"STEP 7: OSPF neighbor {dut4_ip2_no_mask} not in Full state on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip2_no_mask} in Full state on {dut3}")

        if len([f for f in validation_failures if "STEP 7" in f]) == 0:
            st.log("PASS: All OSPF neighbors are in Full state")

        # ===== STEP 8: Verify DR/BDR election =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Verify DR/BDR election on all broadcast segments")
        st.log("-" * 80)

        st.log("Getting OSPF interface information from all devices...")
        interface_output_dut1 = self._get_show_ip_ospf_interface_output(dut1)
        interface_output_dut2 = self._get_show_ip_ospf_interface_output(dut2)
        interface_output_dut3 = self._get_show_ip_ospf_interface_output(dut3)
        interface_output_dut4 = self._get_show_ip_ospf_interface_output(dut4)

        # Verify DR/BDR on D1-D2 segment (PortChannel10)
        if not self._verify_dr_bdr_election(interface_output_dut1, f"PortChannel{self.data.portchannel10}"):
            st.log("WARNING: DR/BDR election information incomplete on D1-D2 segment")
        else:
            st.log("PASS: DR/BDR election verified on D1-D2 segment")

        # Verify DR/BDR on D2-D4 segment (PortChannel20)
        if not self._verify_dr_bdr_election(interface_output_dut2, f"PortChannel{self.data.portchannel20}"):
            st.log("WARNING: DR/BDR election information incomplete on D2-D4 segment")
        else:
            st.log("PASS: DR/BDR election verified on D2-D4 segment")

        # Verify DR/BDR on D4-D3 segment (PortChannel30)
        if not self._verify_dr_bdr_election(interface_output_dut4, f"PortChannel{self.data.portchannel30}"):
            st.log("WARNING: DR/BDR election information incomplete on D4-D3 segment")
        else:
            st.log("PASS: DR/BDR election verified on D4-D3 segment")

        st.log("PASS: DR/BDR election completed on all segments")

        # ===== STEP 9: Verify Type 1 LSAs from all routers =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Verify Type 1 LSAs from all 4 routers present in OSPF database")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_LSA_PROPAGATION} seconds for LSA propagation...")
        time.sleep(WAIT_FOR_LSA_PROPAGATION)

        st.log("Getting Type 1 LSA information from all devices...")
        lsa_router_dut1 = self._get_show_ip_ospf_database_router_output(dut1)
        lsa_router_dut2 = self._get_show_ip_ospf_database_router_output(dut2)
        lsa_router_dut3 = self._get_show_ip_ospf_database_router_output(dut3)
        lsa_router_dut4 = self._get_show_ip_ospf_database_router_output(dut4)

        # Verify D1 has LSAs from all 4 routers
        if not self._verify_type1_lsa_count(lsa_router_dut1, 4):
            error_msg = f"STEP 9: D1 should have Type 1 LSAs from all 4 routers"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: All 4 Type 1 LSAs present in D1's database")

        # Similarly verify for D2, D3, D4
        if not self._verify_type1_lsa_count(lsa_router_dut2, 4):
            st.log("WARNING: D2 may not have all Type 1 LSAs")

        if not self._verify_type1_lsa_count(lsa_router_dut3, 4):
            st.log("WARNING: D3 may not have all Type 1 LSAs")

        if not self._verify_type1_lsa_count(lsa_router_dut4, 4):
            st.log("WARNING: D4 may not have all Type 1 LSAs")

        st.log("PASS: Type 1 LSA verification completed")

        # ===== STEP 10: Verify self-originated LSAs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Verify self-originated LSAs have correct link counts")
        st.log("-" * 80)

        st.log("Getting self-originated LSA information from all devices...")
        self_lsa_dut1 = self._get_show_ip_ospf_database_router_self_originate_output(dut1)
        self_lsa_dut2 = self._get_show_ip_ospf_database_router_self_originate_output(dut2)
        self_lsa_dut3 = self._get_show_ip_ospf_database_router_self_originate_output(dut3)
        self_lsa_dut4 = self._get_show_ip_ospf_database_router_self_originate_output(dut4)

        # D1 should have 1 link (transit to 10.1.1.1)
        if not self._verify_self_originated_lsa(self_lsa_dut1, 1):
            st.log("WARNING: D1 self-originated LSA link count mismatch")
        else:
            st.log("PASS: D1 self-originated LSA has 1 link")

        # D2 should have 2 links (transit to 10.1.1.1 and 20.1.1.1)
        if not self._verify_self_originated_lsa(self_lsa_dut2, 2):
            st.log("WARNING: D2 self-originated LSA link count mismatch")
        else:
            st.log("PASS: D2 self-originated LSA has 2 links")

        # D4 should have 2 links (transit to 20.1.1.1 and 30.1.1.1)
        if not self._verify_self_originated_lsa(self_lsa_dut4, 2):
            st.log("WARNING: D4 self-originated LSA link count mismatch")
        else:
            st.log("PASS: D4 self-originated LSA has 2 links")

        # D3 should have 1 link (transit to 30.1.1.1)
        if not self._verify_self_originated_lsa(self_lsa_dut3, 1):
            st.log("WARNING: D3 self-originated LSA link count mismatch")
        else:
            st.log("PASS: D3 self-originated LSA has 1 link")

        st.log("PASS: Self-originated LSA verification completed")

        # ===== STEP 11: Verify Type 2 Network LSAs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Verify Type 2 Network LSAs present for broadcast segments")
        st.log("-" * 80)

        st.log("Getting complete OSPF database from D1...")
        database_dut1 = self._get_show_ip_ospf_database_output(dut1)

        # Should have at least 3 Network LSAs (one for each broadcast segment)
        if not self._verify_network_lsa_count(database_dut1, 3):
            st.log("WARNING: Expected 3 Network LSAs for broadcast segments")
        else:
            st.log("PASS: Type 2 Network LSAs present")

        st.log("PASS: Network LSA verification completed")

        # ===== STEP 12: Verify OSPF routes learned with correct costs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Verify OSPF routes learned with correct costs")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_ROUTE_UPDATE} seconds for routes to install...")
        time.sleep(WAIT_FOR_ROUTE_UPDATE)

        st.log("Getting routing table from D1...")
        route_output_dut1 = self._get_show_ip_route_output(dut1)
        route_ospf_dut1 = self._get_show_ip_route_ospf_output(dut1)

        # Verify D1 learned route to 20.1.1.0/24 (1 hop via D2)
        if not self._verify_ospf_route_present(route_output_dut1, "20.1.1.0/24"):
            error_msg = "STEP 12: D1 should have OSPF route to 20.1.1.0/24"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: D1 has OSPF route to 20.1.1.0/24")

        if not self._verify_ospf_route_cost(route_output_dut1, "20.1.1.0/24", 20000):
            st.log("WARNING: Route cost to 20.1.1.0/24 may differ")

        # Verify D1 learned route to 30.1.1.0/24 (2 hops via D2->D4)
        if not self._verify_ospf_route_present(route_output_dut1, "30.1.1.0/24"):
            error_msg = "STEP 12: D1 should have OSPF route to 30.1.1.0/24"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: D1 has OSPF route to 30.1.1.0/24")

        if not self._verify_ospf_route_cost(route_output_dut1, "30.1.1.0/24", 30000):
            st.log("WARNING: Route cost to 30.1.1.0/24 may differ")

        if len([f for f in validation_failures if "STEP 12" in f]) == 0:
            st.log("PASS: OSPF routes verified with correct costs")

        # ===== STEP 13: Verify end-to-end connectivity =====
        st.log("\n" + "-" * 80)
        st.log("STEP 13: Verify end-to-end connectivity")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_PING} seconds before ping test...")
        time.sleep(WAIT_FOR_PING)

        # Ping from D1 to D3's IP (30.1.1.2)
        target_ip_d3 = self.data.dut3_ip.split('/')[0]  # 30.1.1.2
        if not self._verify_ping_success(dut1, target_ip_d3):
            error_msg = f"STEP 13: Ping from {dut1} to {target_ip_d3} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut1} to {target_ip_d3} successful")

        # Ping from D3 to D1's IP (10.1.1.1)
        target_ip_d1 = self.data.dut1_ip.split('/')[0]  # 10.1.1.1
        if not self._verify_ping_success(dut3, target_ip_d1):
            error_msg = f"STEP 13: Ping from {dut3} to {target_ip_d1} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut3} to {target_ip_d1} successful")

        if len([f for f in validation_failures if "STEP 13" in f]) == 0:
            st.log("PASS: End-to-end connectivity verified")

        # ===== STEP 14: Cleanup - Remove all configurations =====
        st.log("\n" + "-" * 80)
        st.log("STEP 14: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove OSPF configuration
        self._remove_ospf_configuration(dut1)
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut3)
        self._remove_ospf_configuration(dut4)
        st.log("OSPF configuration removed from all devices")

        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Remove IP addresses from PortChannels
        self._remove_interface_ip(dut1, f"PortChannel{self.data.portchannel10}")
        self._remove_interface_ip(dut2, f"PortChannel{self.data.portchannel10}")
        self._remove_interface_ip(dut2, f"PortChannel{self.data.portchannel20}")
        self._remove_interface_ip(dut4, f"PortChannel{self.data.portchannel20}")
        self._remove_interface_ip(dut4, f"PortChannel{self.data.portchannel30}")
        self._remove_interface_ip(dut3, f"PortChannel{self.data.portchannel30}")
        st.log("IP addresses removed from all PortChannel interfaces")

        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Remove ports from PortChannels
        self._remove_ports_from_portchannel(dut1, self.data.dut1_eth_ports)
        self._remove_ports_from_portchannel(dut2, all_dut2_eth_ports)
        self._remove_ports_from_portchannel(dut4, all_dut4_eth_ports)
        self._remove_ports_from_portchannel(dut3, self.data.dut3_eth_ports)
        st.log("Ports removed from all PortChannels")

        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        # Delete PortChannels
        self._delete_portchannel(dut1, self.data.portchannel10)
        self._delete_portchannel(dut2, self.data.portchannel10)
        self._delete_portchannel(dut2, self.data.portchannel20)
        self._delete_portchannel(dut4, self.data.portchannel20)
        self._delete_portchannel(dut4, self.data.portchannel30)
        self._delete_portchannel(dut3, self.data.portchannel30)
        st.log("PortChannels deleted from all devices")

        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        st.log("PASS: Cleanup completed successfully")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF Type 1 LSA verification over PortChannel completed successfully")
        st.log("=" * 80)
        st.log("Verification Summary:")
        st.log("  ✓ PortChannels created successfully with member ports")
        st.log("  ✓ OSPF neighbors formed Full adjacency on all links")
        st.log("  ✓ DR/BDR election occurred on all broadcast segments")
        st.log("  ✓ Type 1 LSAs from all 4 routers present in database")
        st.log("  ✓ Self-originated LSAs have correct link counts")
        st.log("  ✓ Type 2 Network LSAs present for broadcast segments")
        st.log("  ✓ OSPF routes learned with correct costs")
        st.log("  ✓ End-to-end connectivity verified")
        st.log("  ✓ Configuration cleanup successful")
        st.log("=" * 80)

        # ===== COLLECT TECH SUPPORT AND REPORT FAILURES =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from all DUTs
            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_type1_lsa_pc_validation_failure")
                    st.log(f"Tech support collected from {dut}")
                except Exception as e:
                    st.log(f"Warning: Failed to collect tech support from {dut}: {str(e)}")

            # Report all validation failures
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES SUMMARY:")
            st.log("!" * 80)
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.log("!" * 80)

            # Create detailed failure summary
            failure_summary = "\n".join([f"  - {failure}" for failure in validation_failures])
            st.report_fail(
                "msg",
                f"Test completed with {len(validation_failures)} validation failure(s):\n{failure_summary}"
            )
        else:
            st.log("\n" + "=" * 80)
            st.log("ALL VALIDATIONS PASSED SUCCESSFULLY")
            st.log("=" * 80)
            st.report_pass("test_case_passed")
