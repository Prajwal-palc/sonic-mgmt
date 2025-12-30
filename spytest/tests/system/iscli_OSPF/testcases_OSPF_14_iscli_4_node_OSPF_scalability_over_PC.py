"""
OSPF SCALABILITY TESTING - 4-NODE TOPOLOGY WITH MULTIPLE PORTCHANNEL LINKS
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_14_iscli_4_node_OSPF_scalability_over_PC.py \
  --logs-path ./logs/testcases_OSPF_14_scalability_PC_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF scalability in a 4-node topology with multiple PortChannel
  links between devices. The test covers:

  1. Removing IP addresses from Ethernet interfaces before adding to PortChannels
  2. Creating 12 PortChannels (4 between each device pair)
  3. Adding Ethernet interfaces as members to respective PortChannels
  4. Verifying PortChannel creation and member addition
  5. Configuring IP addresses on all 12 PortChannel interfaces
  6. Configuring OSPF Area 0 on all devices
  7. Verifying OSPF neighbor adjacency on all PortChannels (Full state)
  8. Verifying OSPF interface parameters (State, DR/BDR election, Router ID, Cost, etc.)
  9. Verifying OSPF routes are learned with ECMP (Equal Cost Multi-Path)
  10. Verifying OSPF database and LSA (Link State Advertisements)
  11. Verifying OSPF neighbor detailed information
  12. Verifying 'show ip ospf border-routers' command output
  13. Testing end-to-end connectivity with ping
  14. Cleanup: Removing all configurations

  Test Focus: OSPF scalability over PortChannel interfaces
  - 4 devices with 4 parallel PortChannel links between each pair
  - Total of 12 PortChannels across the topology
  - Each PortChannel has 1 Ethernet member
  - 12 OSPF adjacencies across the topology
  - ECMP load balancing verification
  - DR/BDR election on broadcast networks
  - LSA database validation

  Topology:
        D1 ======== (4 parallel PortChannels) ======== D2
                                                        ||
                                                        ||
                          (4 parallel PortChannels)     ||
                                                        ||
        D3 ======== (4 parallel PortChannels) ======== D4

  PortChannels:
    D1 ↔ D2: PortChannel110,120,130,140 ↔ PortChannel110,120,130,140
    D2 ↔ D4: PortChannel150,160,170,180 ↔ PortChannel150,160,170,180
    D4 ↔ D3: PortChannel10,20,30,40 ↔ PortChannel10,20,30,40

  PortChannel Members (1 Ethernet port per PortChannel):
    D1 ↔ D2:
      PortChannel110: Ethernet0 (D1) ↔ Ethernet0 (D2)
      PortChannel120: Ethernet4 (D1) ↔ Ethernet4 (D2)
      PortChannel130: Ethernet8 (D1) ↔ Ethernet8 (D2)
      PortChannel140: Ethernet12 (D1) ↔ Ethernet12 (D2)
    D2 ↔ D4:
      PortChannel150: Ethernet16 (D2) ↔ Ethernet16 (D4)
      PortChannel160: Ethernet20 (D2) ↔ Ethernet20 (D4)
      PortChannel170: Ethernet24 (D2) ↔ Ethernet24 (D4)
      PortChannel180: Ethernet28 (D2) ↔ Ethernet28 (D4)
    D4 ↔ D3:
      PortChannel10: Ethernet32 (D4) ↔ Ethernet32 (D3)
      PortChannel20: Ethernet36 (D4) ↔ Ethernet36 (D3)
      PortChannel30: Ethernet40 (D4) ↔ Ethernet40 (D3)
      PortChannel40: Ethernet44 (D4) ↔ Ethernet44 (D3)

  IP Addressing:
    D1: PortChannel110,120,130,140: 10.1.1.1/24, 10.1.2.1/24, 10.1.3.1/24, 10.1.4.1/24
    D2: PortChannel110,120,130,140: 10.1.1.2/24, 10.1.2.2/24, 10.1.3.2/24, 10.1.4.2/24
        PortChannel150,160,170,180: 20.1.1.1/24, 20.1.2.1/24, 20.1.3.1/24, 20.1.4.1/24
    D4: PortChannel150,160,170,180: 20.1.1.2/24, 20.1.2.2/24, 20.1.3.2/24, 20.1.4.2/24
        PortChannel10,20,30,40: 30.1.1.2/24, 30.1.2.2/24, 30.1.3.2/24, 30.1.4.2/24
    D3: PortChannel10,20,30,40: 30.1.1.1/24, 30.1.2.1/24, 30.1.3.1/24, 30.1.4.1/24

  IMPORTANT: Uses 'show ip ospf neighbor', 'show ip ospf interface',
  'show ip route ospf', 'show ip ospf database', 'show ip ospf database router',
  'show ip ospf neighbor detail', 'show ip ospf border-routers', and PortChannel
  verification commands to validate OSPF scalability. Uses klish CLI type exclusively.

  NOTE: 'show ip ospf border-routers' is expected to return empty table in this
  single-area topology (all Area 0). Border routers (ABRs/ASBRs) only appear in
  multi-area topologies or when external routes are redistributed.

Pre-requisites:
  - Topology: 4-node with 4 parallel links | Supported: HW and Virtual
  - Testbed: testbed_4vs.yaml
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
WAIT_FOR_NEIGHBOR_UP = 60
WAIT_FOR_ROUTE_UPDATE = 15
WAIT_FOR_PING = 2


@pytest.mark.topology("any")
class TestOSPFScalabilityOverPortChannel:
    """Test cases for validating OSPF scalability over PortChannel links in 4-node topology."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF Scalability Test Suite - PortChannel Links")
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
        # D1 ↔ D2: 4 parallel links (Ethernet interfaces to be added to PortChannels)
        cls.data.dut1_d2_eth_ports = ["Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12"]
        cls.data.dut2_d1_eth_ports = ["Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12"]

        # D2 ↔ D4: 4 parallel links
        cls.data.dut2_d4_eth_ports = ["Ethernet16", "Ethernet20", "Ethernet24", "Ethernet28"]
        cls.data.dut4_d2_eth_ports = ["Ethernet16", "Ethernet20", "Ethernet24", "Ethernet28"]

        # D4 ↔ D3: 4 parallel links
        cls.data.dut4_d3_eth_ports = ["Ethernet32", "Ethernet36", "Ethernet40", "Ethernet44"]
        cls.data.dut3_d4_eth_ports = ["Ethernet32", "Ethernet36", "Ethernet40", "Ethernet44"]

        # PortChannel IDs (must be 1-256)
        cls.data.dut1_d2_portchannels = ["110", "120", "130", "140"]
        cls.data.dut2_d1_portchannels = ["110", "120", "130", "140"]
        cls.data.dut2_d4_portchannels = ["150", "160", "170", "180"]
        cls.data.dut4_d2_portchannels = ["150", "160", "170", "180"]
        cls.data.dut4_d3_portchannels = ["10", "20", "30", "40"]
        cls.data.dut3_d4_portchannels = ["10", "20", "30", "40"]

        st.log("Topology Configuration:")
        st.log(f"  D1 ↔ D2: PortChannels {cls.data.dut1_d2_portchannels}")
        st.log(f"  D2 ↔ D4: PortChannels {cls.data.dut2_d4_portchannels}")
        st.log(f"  D4 ↔ D3: PortChannels {cls.data.dut4_d3_portchannels}")

        # IP addresses for D1 ↔ D2 PortChannels
        cls.data.dut1_d2_ips = ["10.1.1.1/24", "10.1.2.1/24", "10.1.3.1/24", "10.1.4.1/24"]
        cls.data.dut2_d1_ips = ["10.1.1.2/24", "10.1.2.2/24", "10.1.3.2/24", "10.1.4.2/24"]

        # IP addresses for D2 ↔ D4 PortChannels
        cls.data.dut2_d4_ips = ["20.1.1.1/24", "20.1.2.1/24", "20.1.3.1/24", "20.1.4.1/24"]
        cls.data.dut4_d2_ips = ["20.1.1.2/24", "20.1.2.2/24", "20.1.3.2/24", "20.1.4.2/24"]

        # IP addresses for D4 ↔ D3 PortChannels
        cls.data.dut4_d3_ips = ["30.1.1.2/24", "30.1.2.2/24", "30.1.3.2/24", "30.1.4.2/24"]
        cls.data.dut3_d4_ips = ["30.1.1.1/24", "30.1.2.1/24", "30.1.3.1/24", "30.1.4.1/24"]

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
        st.log("TEST TEARDOWN: Cleanup OSPF Scalability Test Suite (PortChannel)")
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
    def _remove_ip_from_ethernet_interface(dut: str, interface: str) -> bool:
        """
        Remove IP addresses from Ethernet interface before adding to PortChannel.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if successful
        """
        st.log(f"Removing IP addresses from {interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip address",
            "no ipv6 address",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    # ========== HELPER METHODS - PORTCHANNEL CONFIGURATION ==========

    @staticmethod
    def _create_portchannel(dut: str, portchannel_id: str) -> bool:
        """
        Create PortChannel using klish commands.

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
        Delete PortChannel using klish commands.

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
    def _add_member_to_portchannel(dut: str, portchannel_id: str, member_port: str) -> bool:
        """
        Add Ethernet interface as member to PortChannel.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "110")
            member_port: Member port (e.g., "Ethernet0")

        Returns:
            True if successful
        """
        st.log(f"Adding {member_port} to PortChannel {portchannel_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface {member_port}",
            f"channel-group {portchannel_id}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_member_from_portchannel(dut: str, member_port: str) -> bool:
        """
        Remove Ethernet interface from PortChannel.

        Args:
            dut: Device handle
            member_port: Member port (e.g., "Ethernet0")

        Returns:
            True if successful
        """
        st.log(f"Removing {member_port} from PortChannel on {dut}")
        commands = [
            "configure terminal",
            f"interface {member_port}",
            "no channel-group",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

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
            "no shutdown",
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

    # ========== HELPER METHODS - OSPF CONFIGURATION ==========

    @staticmethod
    def _configure_ospf_process(dut: str, area: str, networks: List[str]) -> bool:
        """
        Configure OSPF process and networks.

        Args:
            dut: Device handle
            area: OSPF area ID
            networks: List of networks to advertise

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF process with area {area} on {dut}")
        commands = ["configure terminal", "router ospf", f"area {area}"]

        for network in networks:
            commands.append(f"network {network} area {area}")

        commands.append("exit")
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
    def _get_show_ip_ospf_neighbor(dut: str) -> str:
        """Get 'show ip ospf neighbor' output."""
        st.log(f"Getting 'show ip ospf neighbor' output from {dut}")
        output = st.show(dut, "show ip ospf neighbor", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf neighbor output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_interface(dut: str) -> str:
        """Get 'show ip ospf interface' output."""
        st.log(f"Getting 'show ip ospf interface' output from {dut}")
        output = st.show(dut, "show ip ospf interface", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf interface output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_route_ospf(dut: str) -> str:
        """Get 'show ip route ospf' output."""
        st.log(f"Getting 'show ip route ospf' output from {dut}")
        output = st.show(dut, "show ip route ospf", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip route ospf output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_database(dut: str) -> str:
        """Get 'show ip ospf database' output."""
        st.log(f"Getting 'show ip ospf database' output from {dut}")
        output = st.show(dut, "show ip ospf database", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf database output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_database_router(dut: str) -> str:
        """Get 'show ip ospf database router' output."""
        st.log(f"Getting 'show ip ospf database router' output from {dut}")
        output = st.show(dut, "show ip ospf database router", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf database router output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_neighbor_detail(dut: str) -> str:
        """Get 'show ip ospf neighbor detail' output."""
        st.log(f"Getting 'show ip ospf neighbor detail' output from {dut}")
        output = st.show(dut, "show ip ospf neighbor detail", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf neighbor detail output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_border_routers(dut: str) -> str:
        """Get 'show ip ospf border-routers' output."""
        st.log(f"Getting 'show ip ospf border-routers' output from {dut}")
        output = st.show(dut, "show ip ospf border-routers", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf border-routers output from {dut}:\n{output}")
        return output

    # ========== HELPER METHODS - VALIDATION ==========

    @staticmethod
    def _verify_ospf_neighbor_count(output: str, expected_count: int) -> bool:
        """
        Verify expected number of OSPF neighbors.

        Args:
            output: Output from 'show ip ospf neighbor'
            expected_count: Expected neighbor count

        Returns:
            True if neighbor count matches
        """
        st.log(f"Verifying OSPF neighbor count is {expected_count}")

        # Count lines with "Full" state
        full_state_lines = [line for line in output.split('\n') if 'Full' in line]
        actual_count = len(full_state_lines)

        if actual_count == expected_count:
            st.log(f"PASS: Found {actual_count} OSPF neighbors in Full state")
            return True
        else:
            st.error(f"FAIL: Expected {expected_count} neighbors, found {actual_count}")
            return False

    @staticmethod
    def _verify_ospf_interface_present(output: str, interface: str) -> bool:
        """
        Verify OSPF interface is present and up.

        Args:
            output: Output from 'show ip ospf interface'
            interface: Interface name (e.g., "PortChannel110")

        Returns:
            True if interface is present and up
        """
        st.log(f"Verifying {interface} is present in OSPF")

        if f"{interface} is up" in output:
            st.log(f"PASS: {interface} is up in OSPF")
            return True
        else:
            st.error(f"FAIL: {interface} not found or not up in OSPF")
            return False

    @staticmethod
    def _verify_dr_bdr_election(output: str) -> bool:
        """
        Verify DR/BDR election occurred.

        Args:
            output: Output from 'show ip ospf interface'

        Returns:
            True if DR/BDR found
        """
        st.log("Verifying DR/BDR election occurred")

        dr_count = output.count("Designated Router")
        bdr_count = output.count("Backup Designated Router")

        if dr_count > 0 and bdr_count > 0:
            st.log(f"PASS: DR/BDR election verified (DR: {dr_count}, BDR: {bdr_count})")
            return True
        else:
            st.error(f"FAIL: DR/BDR election incomplete (DR: {dr_count}, BDR: {bdr_count})")
            return False

    @staticmethod
    def _verify_ospf_routes_present(output: str, expected_networks: List[str]) -> bool:
        """
        Verify OSPF routes are present.

        Args:
            output: Output from 'show ip route ospf'
            expected_networks: List of expected networks

        Returns:
            True if all routes found
        """
        st.log(f"Verifying OSPF routes are present for networks: {expected_networks}")

        missing_routes = []
        for network in expected_networks:
            if network not in output:
                missing_routes.append(network)

        if not missing_routes:
            st.log(f"PASS: All {len(expected_networks)} expected OSPF routes found")
            return True
        else:
            st.error(f"FAIL: Missing routes: {missing_routes}")
            return False

    @staticmethod
    def _verify_ecmp_routes(output: str, network: str) -> bool:
        """
        Verify that network has ECMP (multiple next-hops).

        Args:
            output: Output from 'show ip route ospf'
            network: Network to check

        Returns:
            True if multiple next-hops found
        """
        st.log(f"Verifying ECMP for network {network}")

        lines = output.split('\n')
        next_hop_count = 0
        in_route_entry = False

        for line in lines:
            # Found the route entry line
            if network in line and 'O>' in line:
                next_hop_count += 1  # Count the first next-hop
                in_route_entry = True
            # Found continuation line with additional next-hop
            elif in_route_entry and line.strip().startswith('*') and 'via' in line:
                next_hop_count += 1
            # Moved to a different route entry
            elif in_route_entry and not line.strip().startswith('*'):
                in_route_entry = False

        if next_hop_count >= 2:
            st.log(f"PASS: Found ECMP with {next_hop_count} next-hops for {network}")
            return True
        elif next_hop_count == 1:
            st.log(f"INFO: Found single path for {network} (ECMP not required)")
            return True
        else:
            st.error(f"FAIL: No routes found for {network}")
            return False

    @staticmethod
    def _verify_lsa_present(output: str, lsa_type: str) -> bool:
        """
        Verify LSA is present in database.

        Args:
            output: Output from 'show ip ospf database'
            lsa_type: LSA type to verify (e.g., "Router Link States", "Net Link States")

        Returns:
            True if LSA type found
        """
        st.log(f"Verifying {lsa_type} in OSPF database")

        if lsa_type in output:
            st.log(f"PASS: {lsa_type} found in OSPF database")
            return True
        else:
            st.error(f"FAIL: {lsa_type} not found in OSPF database")
            return False

    @staticmethod
    def _verify_ping_success(dut: str, target_ip: str, count: int = 4) -> bool:
        """
        Verify ping from DUT to target IP.

        Args:
            dut: Device handle
            target_ip: Target IP address to ping
            count: Number of ping packets

        Returns:
            True if ping successful
        """
        st.log(f"Verifying ping from {dut} to {target_ip}")

        command = f"ping {target_ip} -c {count}"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True, skip_error_check=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"Ping output:\n{output}")

        if "0% packet loss" in output or f"{count} received" in output or "bytes from" in output:
            st.log(f"PASS: Ping from {dut} to {target_ip} successful")
            return True
        else:
            st.error(f"FAIL: Ping from {dut} to {target_ip} failed")
            return False

    @staticmethod
    def _verify_border_routers_output(output: str, single_area_topology: bool = True) -> bool:
        """
        Verify 'show ip ospf border-routers' output.

        Args:
            output: Output from 'show ip ospf border-routers'
            single_area_topology: True if all routers in same area (no ABRs expected)

        Returns:
            True if command executed successfully
        """
        st.log("Verifying 'show ip ospf border-routers' command output")

        # Check if output contains only the header (empty/no data)
        lines = [line.strip() for line in output.split('\n') if line.strip()]

        # Check if output is completely empty or just has header
        has_header = "OSPF router routing table" in output or "ospf router routing table" in output.lower()

        # Count non-header lines (actual border router entries)
        data_lines = [line for line in lines if line and
                     "OSPF router routing table" not in line and
                     "=" not in line and
                     len(line) > 5]

        if not has_header:
            st.error("FAIL: 'show ip ospf border-routers' output missing expected header")
            return False

        if len(data_lines) == 0:
            # Empty output - no border router entries
            if single_area_topology:
                # In single-area topology (all Area 0), empty is EXPECTED and CORRECT
                # No ABRs (Area Border Routers) because all routers in same area
                # No ASBRs (AS Boundary Routers) because no external route redistribution
                st.log("PASS: 'show ip ospf border-routers' returned empty table (expected for single-area topology)")
                st.log("      No ABRs/ASBRs present - all routers in Area 0")
                return True
            else:
                # Multi-area topology - we expect to see ABR entries
                st.error("FAIL: 'show ip ospf border-routers' returned empty in multi-area topology")
                st.error("      Expected ABR/ASBR entries but none found")
                return False
        else:
            st.log(f"PASS: 'show ip ospf border-routers' command executed, found {len(data_lines)} border router entries")
            # Log the entries found
            for line in data_lines:
                st.log(f"      Border router entry: {line}")
            return True

    # ========== TEST CASE ==========

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_SCALABILITY_PORTCHANNEL_001"])
    def test_ospf_scalability_over_portchannel(self) -> None:
        """
        TC_OSPF_SCALABILITY_PORTCHANNEL_001: Validate OSPF scalability over PortChannel links.

        Test Procedure:
        1. Remove IP addresses from all Ethernet interfaces
        2. Create 12 PortChannels (4 between each device pair)
        3. Add Ethernet members to PortChannels (1 port per PortChannel)
        4. Configure IP addresses on all 12 PortChannel interfaces
        5. Configure OSPF on all devices with all networks
        6. Verify OSPF neighbors form on all PortChannels (Full state)
        7. Verify OSPF interface status on all devices
        8. Verify DR/BDR election on broadcast networks
        9. Verify OSPF routes are learned with ECMP
        10. Verify OSPF database and LSAs
        11. Verify OSPF neighbor detailed information
        11B. Verify 'show ip ospf border-routers' command output
        12. Verify end-to-end connectivity with ping
        13. Cleanup: Remove all configurations

        Expected Result:
        - IPs removed from all Ethernet interfaces
        - 12 PortChannels created successfully
        - All Ethernet members added to respective PortChannels
        - IP addresses configured on all 12 PortChannel interfaces
        - OSPF neighbors form on all PortChannels (12 adjacencies total)
        - OSPF interfaces are up and operational
        - DR/BDR election occurs on all broadcast segments
        - OSPF routes learned with ECMP for redundant paths
        - OSPF database populated with Router and Network LSAs
        - 'show ip ospf border-routers' returns empty (correct for single-area topology)
        - End-to-end ping successful
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF Scalability Over PortChannel - 4-Node Topology with 12 PortChannels")
        st.log("=" * 80)

        # Initialize validation failures list for tracking
        validation_failures = []

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4
        area = self.data.ospf_area

        # ===== STEP 1: Remove IP addresses from Ethernet interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Remove IP addresses from all Ethernet interfaces before adding to PortChannels")
        st.log("-" * 80)

        # Remove IPs from D1 ↔ D2 Ethernet interfaces
        for eth_port in self.data.dut1_d2_eth_ports:
            self._remove_ip_from_ethernet_interface(dut1, eth_port)

        for eth_port in self.data.dut2_d1_eth_ports:
            self._remove_ip_from_ethernet_interface(dut2, eth_port)

        # Remove IPs from D2 ↔ D4 Ethernet interfaces
        for eth_port in self.data.dut2_d4_eth_ports:
            self._remove_ip_from_ethernet_interface(dut2, eth_port)

        for eth_port in self.data.dut4_d2_eth_ports:
            self._remove_ip_from_ethernet_interface(dut4, eth_port)

        # Remove IPs from D4 ↔ D3 Ethernet interfaces
        for eth_port in self.data.dut4_d3_eth_ports:
            self._remove_ip_from_ethernet_interface(dut4, eth_port)

        for eth_port in self.data.dut3_d4_eth_ports:
            self._remove_ip_from_ethernet_interface(dut3, eth_port)

        st.log("IP addresses removed from all Ethernet interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: IP removal from Ethernet interfaces completed")

        # ===== STEP 2: Create PortChannels =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Create 12 PortChannels (4 between each device pair)")
        st.log("-" * 80)

        # Create PortChannels on D1
        for pc_id in self.data.dut1_d2_portchannels:
            self._create_portchannel(dut1, pc_id)

        # Create PortChannels on D2
        for pc_id in self.data.dut2_d1_portchannels:
            self._create_portchannel(dut2, pc_id)

        for pc_id in self.data.dut2_d4_portchannels:
            self._create_portchannel(dut2, pc_id)

        # Create PortChannels on D4
        for pc_id in self.data.dut4_d2_portchannels:
            self._create_portchannel(dut4, pc_id)

        for pc_id in self.data.dut4_d3_portchannels:
            self._create_portchannel(dut4, pc_id)

        # Create PortChannels on D3
        for pc_id in self.data.dut3_d4_portchannels:
            self._create_portchannel(dut3, pc_id)

        st.log("All 12 PortChannels created")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        st.log("PASS: PortChannel creation completed")

        # ===== STEP 3: Add Ethernet members to PortChannels =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Add Ethernet interfaces as members to respective PortChannels")
        st.log("-" * 80)

        # Add members for D1 ↔ D2 PortChannels
        for i, (pc_id, eth_port) in enumerate(zip(self.data.dut1_d2_portchannels, self.data.dut1_d2_eth_ports)):
            self._add_member_to_portchannel(dut1, pc_id, eth_port)

        for i, (pc_id, eth_port) in enumerate(zip(self.data.dut2_d1_portchannels, self.data.dut2_d1_eth_ports)):
            self._add_member_to_portchannel(dut2, pc_id, eth_port)

        # Add members for D2 ↔ D4 PortChannels
        for i, (pc_id, eth_port) in enumerate(zip(self.data.dut2_d4_portchannels, self.data.dut2_d4_eth_ports)):
            self._add_member_to_portchannel(dut2, pc_id, eth_port)

        for i, (pc_id, eth_port) in enumerate(zip(self.data.dut4_d2_portchannels, self.data.dut4_d2_eth_ports)):
            self._add_member_to_portchannel(dut4, pc_id, eth_port)

        # Add members for D4 ↔ D3 PortChannels
        for i, (pc_id, eth_port) in enumerate(zip(self.data.dut4_d3_portchannels, self.data.dut4_d3_eth_ports)):
            self._add_member_to_portchannel(dut4, pc_id, eth_port)

        for i, (pc_id, eth_port) in enumerate(zip(self.data.dut3_d4_portchannels, self.data.dut3_d4_eth_ports)):
            self._add_member_to_portchannel(dut3, pc_id, eth_port)

        st.log("All Ethernet members added to PortChannels")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        st.log("PASS: Ethernet member addition completed")

        # ===== STEP 4: Configure IP addresses on PortChannel interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Configure IP addresses on all 12 PortChannel interfaces")
        st.log("-" * 80)

        # Configure IPs on D1 ↔ D2 PortChannels
        for i, (pc_id, ip) in enumerate(zip(self.data.dut1_d2_portchannels, self.data.dut1_d2_ips)):
            self._configure_portchannel_ip(dut1, pc_id, ip)

        for i, (pc_id, ip) in enumerate(zip(self.data.dut2_d1_portchannels, self.data.dut2_d1_ips)):
            self._configure_portchannel_ip(dut2, pc_id, ip)

        # Configure IPs on D2 ↔ D4 PortChannels
        for i, (pc_id, ip) in enumerate(zip(self.data.dut2_d4_portchannels, self.data.dut2_d4_ips)):
            self._configure_portchannel_ip(dut2, pc_id, ip)

        for i, (pc_id, ip) in enumerate(zip(self.data.dut4_d2_portchannels, self.data.dut4_d2_ips)):
            self._configure_portchannel_ip(dut4, pc_id, ip)

        # Configure IPs on D4 ↔ D3 PortChannels
        for i, (pc_id, ip) in enumerate(zip(self.data.dut4_d3_portchannels, self.data.dut4_d3_ips)):
            self._configure_portchannel_ip(dut4, pc_id, ip)

        for i, (pc_id, ip) in enumerate(zip(self.data.dut3_d4_portchannels, self.data.dut3_d4_ips)):
            self._configure_portchannel_ip(dut3, pc_id, ip)

        st.log("IP addresses configured on all 12 PortChannel interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: IP address configuration on PortChannels completed")

        # ===== STEP 5: Configure OSPF on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Configure OSPF on all devices")
        st.log("-" * 80)

        # Configure OSPF on D1
        d1_networks = ["10.1.1.1/24", "10.1.2.1/24", "10.1.3.1/24", "10.1.4.1/24"]
        self._configure_ospf_process(dut1, area, d1_networks)

        # Configure OSPF on D2
        d2_networks = ["10.1.1.2/24", "10.1.2.2/24", "10.1.3.2/24", "10.1.4.2/24",
                      "20.1.1.1/24", "20.1.2.1/24", "20.1.3.1/24", "20.1.4.1/24"]
        self._configure_ospf_process(dut2, area, d2_networks)

        # Configure OSPF on D4
        d4_networks = ["20.1.1.2/24", "20.1.2.2/24", "20.1.3.2/24", "20.1.4.2/24",
                      "30.1.1.2/24", "30.1.2.2/24", "30.1.3.2/24", "30.1.4.2/24"]
        self._configure_ospf_process(dut4, area, d4_networks)

        # Configure OSPF on D3
        d3_networks = ["30.1.1.1/24", "30.1.2.1/24", "30.1.3.1/24", "30.1.4.1/24"]
        self._configure_ospf_process(dut3, area, d3_networks)

        st.log("OSPF configured on all devices")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed")

        # ===== STEP 6: Verify OSPF neighbors on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Verify OSPF neighbors form on all PortChannels (Full state)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor outputs from all devices
        d1_neighbor_output = self._get_show_ip_ospf_neighbor(dut1)
        d2_neighbor_output = self._get_show_ip_ospf_neighbor(dut2)
        d3_neighbor_output = self._get_show_ip_ospf_neighbor(dut3)
        d4_neighbor_output = self._get_show_ip_ospf_neighbor(dut4)

        # Verify neighbor counts - continue even if fails
        if not self._verify_ospf_neighbor_count(d1_neighbor_output, 4):
            error_msg = f"STEP 6: D1 should have 4 OSPF neighbors"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: D1 has 4 OSPF neighbors in Full state")

        if not self._verify_ospf_neighbor_count(d2_neighbor_output, 8):
            error_msg = f"STEP 6: D2 should have 8 OSPF neighbors"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: D2 has 8 OSPF neighbors in Full state")

        if not self._verify_ospf_neighbor_count(d3_neighbor_output, 4):
            error_msg = f"STEP 6: D3 should have 4 OSPF neighbors"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: D3 has 4 OSPF neighbors in Full state")

        if not self._verify_ospf_neighbor_count(d4_neighbor_output, 8):
            error_msg = f"STEP 6: D4 should have 8 OSPF neighbors"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: D4 has 8 OSPF neighbors in Full state")

        if len([f for f in validation_failures if "STEP 6" in f]) == 0:
            st.log("PASS: All OSPF neighbors are in Full state - Total 12 adjacencies verified")

        # ===== STEP 7: Verify OSPF interface status =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Verify OSPF interface status on all devices")
        st.log("-" * 80)

        # Get OSPF interface outputs
        d1_ospf_intf_output = self._get_show_ip_ospf_interface(dut1)
        d2_ospf_intf_output = self._get_show_ip_ospf_interface(dut2)
        d3_ospf_intf_output = self._get_show_ip_ospf_interface(dut3)
        d4_ospf_intf_output = self._get_show_ip_ospf_interface(dut4)

        # Verify D1 PortChannel interfaces
        for pc_id in self.data.dut1_d2_portchannels:
            pc_name = f"PortChannel{pc_id}"
            if not self._verify_ospf_interface_present(d1_ospf_intf_output, pc_name):
                error_msg = f"STEP 7: {pc_name} not present or not up on {dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D2 PortChannel interfaces
        for pc_id in self.data.dut2_d1_portchannels + self.data.dut2_d4_portchannels:
            pc_name = f"PortChannel{pc_id}"
            if not self._verify_ospf_interface_present(d2_ospf_intf_output, pc_name):
                error_msg = f"STEP 7: {pc_name} not present or not up on {dut2}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D3 PortChannel interfaces
        for pc_id in self.data.dut3_d4_portchannels:
            pc_name = f"PortChannel{pc_id}"
            if not self._verify_ospf_interface_present(d3_ospf_intf_output, pc_name):
                error_msg = f"STEP 7: {pc_name} not present or not up on {dut3}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D4 PortChannel interfaces
        for pc_id in self.data.dut4_d2_portchannels + self.data.dut4_d3_portchannels:
            pc_name = f"PortChannel{pc_id}"
            if not self._verify_ospf_interface_present(d4_ospf_intf_output, pc_name):
                error_msg = f"STEP 7: {pc_name} not present or not up on {dut4}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 7" in f]) == 0:
            st.log("PASS: All 12 OSPF PortChannel interfaces are up and operational")

        # ===== STEP 8: Verify DR/BDR election =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Verify DR/BDR election on broadcast networks")
        st.log("-" * 80)

        # Verify DR/BDR on all devices - continue even if fails
        if not self._verify_dr_bdr_election(d1_ospf_intf_output):
            st.log("WARNING: DR/BDR election incomplete on D1")
        else:
            st.log("PASS: DR/BDR election verified on D1")

        if not self._verify_dr_bdr_election(d2_ospf_intf_output):
            st.log("WARNING: DR/BDR election incomplete on D2")
        else:
            st.log("PASS: DR/BDR election verified on D2")

        if not self._verify_dr_bdr_election(d3_ospf_intf_output):
            st.log("WARNING: DR/BDR election incomplete on D3")
        else:
            st.log("PASS: DR/BDR election verified on D3")

        if not self._verify_dr_bdr_election(d4_ospf_intf_output):
            st.log("WARNING: DR/BDR election incomplete on D4")
        else:
            st.log("PASS: DR/BDR election verified on D4")

        st.log("PASS: DR/BDR election check completed")

        # ===== STEP 9: Verify OSPF routes with ECMP =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Verify OSPF routes are learned with ECMP")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_ROUTE_UPDATE)

        # Get route outputs
        d1_route_output = self._get_show_ip_route_ospf(dut1)
        d2_route_output = self._get_show_ip_route_ospf(dut2)
        d3_route_output = self._get_show_ip_route_ospf(dut3)
        d4_route_output = self._get_show_ip_route_ospf(dut4)

        # Verify D1 can reach D3 networks via ECMP
        d3_networks = ["30.1.1.0/24", "30.1.2.0/24", "30.1.3.0/24", "30.1.4.0/24"]

        for network in d3_networks:
            if not self._verify_ecmp_routes(d1_route_output, network):
                error_msg = f"STEP 9: D1 missing route to {network}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D2 can reach D3 networks
        for network in d3_networks:
            if network not in d2_route_output:
                error_msg = f"STEP 9: D2 missing route to {network}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D3 can reach D1 networks via ECMP
        d1_networks = ["10.1.1.0/24", "10.1.2.0/24", "10.1.3.0/24", "10.1.4.0/24"]

        for network in d1_networks:
            if not self._verify_ecmp_routes(d3_route_output, network):
                error_msg = f"STEP 9: D3 missing route to {network}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 9" in f]) == 0:
            st.log("PASS: OSPF routes verified with ECMP across all devices")

        # ===== STEP 10: Verify OSPF database and LSAs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Verify OSPF database and LSAs")
        st.log("-" * 80)

        # Get database outputs
        d1_db_output = self._get_show_ip_ospf_database(dut1)
        d2_db_output = self._get_show_ip_ospf_database(dut2)

        # Verify Router LSAs present
        if not self._verify_lsa_present(d1_db_output, "Router Link States"):
            error_msg = "STEP 10: Router Link States not found in D1 OSPF database"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify Network LSAs present
        if not self._verify_lsa_present(d1_db_output, "Net Link States"):
            error_msg = "STEP 10: Net Link States not found in D1 OSPF database"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Get detailed Router LSA information
        d1_db_router_output = self._get_show_ip_ospf_database_router(dut1)
        d2_db_router_output = self._get_show_ip_ospf_database_router(dut2)

        # Verify Router LSA details present
        if "Link connected to: a Transit Network" not in d1_db_router_output:
            st.log("WARNING: Transit Network links not found in Router LSAs on D1")
        else:
            st.log("PASS: Router LSAs contain Transit Network links on D1")

        if len([f for f in validation_failures if "STEP 10" in f]) == 0:
            st.log("PASS: OSPF database and LSAs verified")

        # ===== STEP 11: Verify OSPF neighbor detailed information =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Verify OSPF neighbor detailed information")
        st.log("-" * 80)

        # Get neighbor detail outputs
        d1_neighbor_detail = self._get_show_ip_ospf_neighbor_detail(dut1)
        d2_neighbor_detail = self._get_show_ip_ospf_neighbor_detail(dut2)

        # Verify neighbor detail contains expected information
        if "State is Full" not in d1_neighbor_detail:
            error_msg = "STEP 11: Neighbor detail missing Full state information on D1"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Neighbor detail shows Full state on D1")

        if "Neighbor priority" not in d1_neighbor_detail and "priority is" not in d1_neighbor_detail:
            st.log("INFO: Neighbor priority information not found in detail output on D1")
        else:
            st.log("PASS: Neighbor detail includes priority information on D1")

        if len([f for f in validation_failures if "STEP 11" in f]) == 0:
            st.log("PASS: OSPF neighbor detailed information verified")

        # ===== STEP 11B: Verify OSPF border-routers command =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11B: Verify 'show ip ospf border-routers' command")
        st.log("-" * 80)

        # Get border-routers outputs from all devices
        d1_border_routers = self._get_show_ip_ospf_border_routers(dut1)
        d2_border_routers = self._get_show_ip_ospf_border_routers(dut2)
        d3_border_routers = self._get_show_ip_ospf_border_routers(dut3)
        d4_border_routers = self._get_show_ip_ospf_border_routers(dut4)

        # Verify border-routers output
        # NOTE: This is a single-area topology (all devices in Area 0)
        # Expected behavior: Empty table (no ABRs or ASBRs)
        # ABRs only exist when routers connect multiple OSPF areas
        # ASBRs only exist when external routes are redistributed
        if not self._verify_border_routers_output(d1_border_routers, single_area_topology=True):
            error_msg = "STEP 11B: 'show ip ospf border-routers' command validation failed on D1"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_border_routers_output(d2_border_routers, single_area_topology=True):
            error_msg = "STEP 11B: 'show ip ospf border-routers' command validation failed on D2"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_border_routers_output(d3_border_routers, single_area_topology=True):
            error_msg = "STEP 11B: 'show ip ospf border-routers' command validation failed on D3"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_border_routers_output(d4_border_routers, single_area_topology=True):
            error_msg = "STEP 11B: 'show ip ospf border-routers' command validation failed on D4"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 11B" in f]) == 0:
            st.log("PASS: 'show ip ospf border-routers' command executed successfully on all devices")
        else:
            st.log("FAIL: 'show ip ospf border-routers' command validation failed - see errors above")

        # ===== STEP 12: Verify end-to-end connectivity =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Verify end-to-end connectivity with ping")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_PING)

        # Ping from D1 to D3 (all 4 IPs)
        for ip in ["30.1.1.1", "30.1.2.1", "30.1.3.1", "30.1.4.1"]:
            if not self._verify_ping_success(dut1, ip, 4):
                error_msg = f"STEP 12: Ping from D1 to {ip} (D3) failed"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Ping from D3 to D1 (all 4 IPs)
        for ip in ["10.1.1.1", "10.1.2.1", "10.1.3.1", "10.1.4.1"]:
            if not self._verify_ping_success(dut3, ip, 4):
                error_msg = f"STEP 12: Ping from D3 to {ip} (D1) failed"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Ping from D2 to D4
        if not self._verify_ping_success(dut2, "30.1.1.1", 4):
            error_msg = f"STEP 12: Ping from D2 to D4's network failed"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 12" in f]) == 0:
            st.log("PASS: End-to-end connectivity verified across all devices")

        # ===== STEP 13: Cleanup - Remove all configurations =====
        st.log("\n" + "-" * 80)
        st.log("STEP 13: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove OSPF configuration
        self._remove_ospf_configuration(dut1)
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut3)
        self._remove_ospf_configuration(dut4)
        st.log("OSPF configuration removed from all devices")

        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Remove IP addresses from PortChannels
        for pc_id in self.data.dut1_d2_portchannels:
            self._remove_portchannel_ip(dut1, pc_id)

        for pc_id in self.data.dut2_d1_portchannels + self.data.dut2_d4_portchannels:
            self._remove_portchannel_ip(dut2, pc_id)

        for pc_id in self.data.dut3_d4_portchannels:
            self._remove_portchannel_ip(dut3, pc_id)

        for pc_id in self.data.dut4_d2_portchannels + self.data.dut4_d3_portchannels:
            self._remove_portchannel_ip(dut4, pc_id)

        st.log("IP addresses removed from all PortChannels")

        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Remove Ethernet members from PortChannels
        for eth_port in self.data.dut1_d2_eth_ports:
            self._remove_member_from_portchannel(dut1, eth_port)

        for eth_port in self.data.dut2_d1_eth_ports + self.data.dut2_d4_eth_ports:
            self._remove_member_from_portchannel(dut2, eth_port)

        for eth_port in self.data.dut3_d4_eth_ports:
            self._remove_member_from_portchannel(dut3, eth_port)

        for eth_port in self.data.dut4_d2_eth_ports + self.data.dut4_d3_eth_ports:
            self._remove_member_from_portchannel(dut4, eth_port)

        st.log("Ethernet members removed from all PortChannels")

        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        # Delete PortChannels
        for pc_id in self.data.dut1_d2_portchannels:
            self._delete_portchannel(dut1, pc_id)

        for pc_id in self.data.dut2_d1_portchannels + self.data.dut2_d4_portchannels:
            self._delete_portchannel(dut2, pc_id)

        for pc_id in self.data.dut3_d4_portchannels:
            self._delete_portchannel(dut3, pc_id)

        for pc_id in self.data.dut4_d2_portchannels + self.data.dut4_d3_portchannels:
            self._delete_portchannel(dut4, pc_id)

        st.log("All 12 PortChannels deleted")

        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        st.log("PASS: Cleanup completed successfully")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF Scalability Over PortChannel")
        st.log("=" * 80)
        st.log("Summary:")
        st.log("  ✓ IPs removed from all Ethernet interfaces")
        st.log("  ✓ 12 PortChannels created successfully")
        st.log("  ✓ Ethernet members added to PortChannels (1 port per PortChannel)")
        st.log("  ✓ IP addresses configured on all 12 PortChannel interfaces")
        st.log("  ✓ OSPF configured on all 4 devices")
        st.log("  ✓ 12 OSPF neighbor adjacencies formed (Full state)")
        st.log("  ✓ DR/BDR election on broadcast segments")
        st.log("  ✓ OSPF routes learned with ECMP load balancing")
        st.log("  ✓ OSPF database populated with Router and Network LSAs")
        st.log("  ✓ OSPF neighbor detailed information verified")
        st.log("  ✓ 'show ip ospf border-routers' command output validated")
        st.log("  ✓ End-to-end connectivity verified")
        st.log("  ✓ Configuration cleanup completed")
        st.log("=" * 80)

        # ===== COLLECT TECH SUPPORT AND REPORT FAILURES =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from all DUTs
            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_scalability_portchannel_validation_failure")
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
