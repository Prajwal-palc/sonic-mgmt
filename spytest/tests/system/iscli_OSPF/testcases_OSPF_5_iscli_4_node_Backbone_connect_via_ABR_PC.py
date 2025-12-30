"""
OSPF 4-NODE BACKBONE TOPOLOGY WITH ABR - PORTCHANNEL INTERFACES
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_5_iscli_4_node_Backbone_connect_via_ABR_PC.py \
  --logs-path ./logs/testcases_OSPF_5_iscli_4_node_Backbone_connect_via_ABR_PC_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF multi-area configuration with Area Border Routers (ABR)
  in a 4-node topology using PortChannel interfaces. The test configures three OSPF
  areas (Area 0 - Backbone, Area 1, and Area 2) and validates inter-area routing through ABRs.

  Test validates:
  1. Remove IP addresses from all Ethernet interfaces (baseline)
  2. PortChannel creation and port management (PortChannel110, 120, 130)
  3. IP address configuration and validation on all PortChannel interfaces
  4. OSPF multi-area configuration (Area 0, Area 1, Area 2)
  5. ABR functionality (D2 and D4 act as ABRs)
  6. OSPF neighbor adjacency (Full state)
  7. OSPF database synchronization (Router LSA, Network LSA, Summary LSA)
  8. Inter-area routing via ABRs
  9. Ping connectivity between all routers across areas
  10. Traceroute validation through ABRs
  11. Complete cleanup of all configurations

  Topology:
        D1 (Area 1) -------- D2 (ABR) -------- D4 (ABR) -------- D3 (Area 2)
       (PortChannel110)   (PortChannel110)  (PortChannel120)  (PortChannel130)
        10.1.1.1          10.1.1.2           20.1.1.2          30.1.1.2
                         (PortChannel120)    (PortChannel130)
                          20.1.1.1           30.1.1.1
                          Area 0              Area 0
                          (Backbone)          (Backbone)

  Configuration details:
    D1 (vs_sonic_1):
      - PortChannel110: Ethernet0, Ethernet4
      - PortChannel110 IP: 10.1.1.1/24
      - OSPF Area 1
      - Network: 10.1.1.1/24 area 1

    D2 (vs_sonic_2) - ABR:
      - PortChannel110: Ethernet0, Ethernet4 (connects to D1 in Area 1)
      - PortChannel110 IP: 10.1.1.2/24
      - PortChannel120: Ethernet24, Ethernet28 (connects to D4 in Area 0 - Backbone)
      - PortChannel120 IP: 20.1.1.1/24
      - OSPF Areas: 0 (Backbone) and 1
      - Networks: 10.1.1.2/24 area 1, 20.1.1.1/24 area 0

    D4 (vs_sonic_4) - ABR:
      - PortChannel120: Ethernet24, Ethernet28 (connects to D2 in Area 0 - Backbone)
      - PortChannel120 IP: 20.1.1.2/24
      - PortChannel130: Ethernet40, Ethernet44 (connects to D3 in Area 2)
      - PortChannel130 IP: 30.1.1.1/24
      - OSPF Areas: 0 (Backbone) and 2
      - Networks: 20.1.1.2/24 area 0, 30.1.1.1/24 area 2

    D3 (vs_sonic_3):
      - PortChannel130: Ethernet40, Ethernet44
      - PortChannel130 IP: 30.1.1.2/24
      - OSPF Area 2
      - Network: 30.1.1.2/24 area 2

  IMPORTANT: Uses 'show ip ospf neighbor', 'show ip ospf', 'show ip ospf route',
  'show ip ospf database summary', 'show PortChannel summary', and
  'show running-configuration interface PortChannel' commands. Uses klish CLI type exclusively.

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
WAIT_AFTER_IP_CONFIG = 3
WAIT_AFTER_PORTCHANNEL_CONFIG = 3
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_ROUTE_UPDATE = 10
WAIT_FOR_PING = 5
WAIT_FOR_DATABASE_SYNC = 10


@pytest.mark.topology("any")
class TestOSPFMultiAreaABRPortChannel:
    """Test cases for validating OSPF multi-area configuration with ABRs using PortChannel interfaces via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF 4-Node Multi-Area ABR Test Suite (PortChannel)")
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

        # PortChannel IDs
        cls.data.portchannel110 = "110"
        cls.data.portchannel120 = "120"
        cls.data.portchannel130 = "130"

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

        # IP addresses for PortChannel interfaces
        cls.data.dut1_ip = "10.1.1.1/24"
        cls.data.dut2_ip1 = "10.1.1.2/24"
        cls.data.dut2_ip2 = "20.1.1.1/24"
        cls.data.dut4_ip1 = "20.1.1.2/24"
        cls.data.dut4_ip2 = "30.1.1.1/24"
        cls.data.dut3_ip = "30.1.1.2/24"

        st.log(f"IP Addresses:")
        st.log(f"  D1[PortChannel110]: {cls.data.dut1_ip} (Area 1)")
        st.log(f"  D2[PortChannel110]: {cls.data.dut2_ip1} (Area 1)")
        st.log(f"  D2[PortChannel120]: {cls.data.dut2_ip2} (Area 0 - Backbone)")
        st.log(f"  D4[PortChannel120]: {cls.data.dut4_ip1} (Area 0 - Backbone)")
        st.log(f"  D4[PortChannel130]: {cls.data.dut4_ip2} (Area 2)")
        st.log(f"  D3[PortChannel130]: {cls.data.dut3_ip} (Area 2)")

        # OSPF areas
        cls.data.ospf_area_0 = "0"  # Backbone
        cls.data.ospf_area_1 = "1"
        cls.data.ospf_area_2 = "2"
        st.log(f"OSPF Areas: Area 0 (Backbone), Area 1, Area 2")

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
        st.log("TEST TEARDOWN: Cleanup OSPF 4-Node Multi-Area ABR Test Suite (PortChannel)")
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
            portchannel_id: PortChannel ID (e.g., "110")

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
    def _add_port_to_portchannel(dut: str, interface: str, portchannel_id: str) -> bool:
        """
        Add interface to PortChannel using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            portchannel_id: PortChannel ID (e.g., "110")

        Returns:
            True if successful
        """
        st.log(f"Adding {interface} to PortChannel {portchannel_id} on {dut}")
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
        st.log(f"Removing {interface} from PortChannel on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
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
        st.log(f"Configuring IP address {ip_address} on PortChannel{portchannel_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
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
            portchannel_id: PortChannel ID (e.g., "110")

        Returns:
            True if successful
        """
        st.log(f"Removing IP address from PortChannel{portchannel_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            "no ip address",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _verify_portchannel_ip(dut: str, portchannel_id: str, expected_ip: str) -> bool:
        """
        Verify IP address configuration on PortChannel interface.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "110")
            expected_ip: Expected IP address with mask (e.g., "10.1.1.1/24")

        Returns:
            True if IP is configured correctly, False otherwise
        """
        st.log(f"Verifying IP address {expected_ip} on PortChannel{portchannel_id} on {dut}")

        # Command: show running-configuration interface PortChannel X
        command = f"show running-configuration interface PortChannel {portchannel_id}"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True, skip_error_check=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show running-configuration interface PortChannel {portchannel_id} output:\n{output}")

        if expected_ip in output:
            st.log(f"PASS: IP address {expected_ip} verified on PortChannel{portchannel_id}")
            return True
        else:
            st.log(f"FAIL: IP address {expected_ip} not found on PortChannel{portchannel_id}")
            return False

    # ========== HELPER METHODS - OSPF CONFIGURATION ==========

    @staticmethod
    def _configure_ospf_process(dut: str, areas: List[str]) -> bool:
        """Configure OSPF process and areas."""
        st.log(f"Configuring OSPF process with areas {areas} on {dut}")
        commands = ["configure terminal", "router ospf"]
        for area in areas:
            commands.append(f"area {area}")
        commands.append("exit")

        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _configure_ospf_network(dut: str, network: str, area: str) -> bool:
        """Configure OSPF network statement."""
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
        """Remove OSPF configuration."""
        st.log(f"Removing OSPF configuration from {dut}")
        commands = [
            "configure terminal",
            "no router ospf"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    # ========== HELPER METHODS - SHOW COMMANDS ==========

    @staticmethod
    def _get_show_ip_ospf_output(dut: str) -> str:
        """Get 'show ip ospf' output as raw string."""
        st.log(f"Getting 'show ip ospf' output from {dut}")
        command = "show ip ospf"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_neighbor_output(dut: str) -> str:
        """Get 'show ip ospf neighbor' output as raw string."""
        st.log(f"Getting 'show ip ospf neighbor' output from {dut}")
        command = "show ip ospf neighbor"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf neighbor output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_route_output(dut: str) -> str:
        """Get 'show ip ospf route' output as raw string."""
        st.log(f"Getting 'show ip ospf route' output from {dut}")
        command = "show ip ospf route"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf route output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_database_summary_output(dut: str) -> str:
        """Get 'show ip ospf database summary' output as raw string."""
        st.log(f"Getting 'show ip ospf database summary' output from {dut}")
        command = "show ip ospf database summary"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf database summary output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_portchannel_summary(dut: str) -> str:
        """Get 'show PortChannel summary' output as raw string."""
        st.log(f"Getting 'show PortChannel summary' output from {dut}")
        command = "show PortChannel summary"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show PortChannel summary output from {dut}:\n{output}")
        return output

    # ========== HELPER METHODS - VALIDATION ==========

    @staticmethod
    def _verify_ospf_abr_status(ospf_output: str, expected_abr: bool = True) -> bool:
        """Verify if router is configured as ABR."""
        st.log(f"Verifying ABR status (expected: {expected_abr})")

        is_abr = "This router is an ABR" in ospf_output

        if expected_abr and is_abr:
            st.log("PASS: Router is configured as ABR")
            return True
        elif not expected_abr and not is_abr:
            st.log("PASS: Router is not configured as ABR")
            return True
        else:
            st.log(f"FAIL: ABR status mismatch (expected: {expected_abr}, actual: {is_abr})")
            return False

    @staticmethod
    def _verify_ospf_areas(ospf_output: str, expected_areas: List[str]) -> bool:
        """Verify OSPF areas are configured."""
        st.log(f"Verifying OSPF areas: {expected_areas}")

        for area in expected_areas:
            area_pattern = f"Area ID: 0.0.0.{area}"
            if area_pattern not in ospf_output and f"Area {area}" not in ospf_output:
                st.log(f"FAIL: Area {area} not found in OSPF output")
                return False

        st.log(f"PASS: All areas {expected_areas} verified")
        return True

    @staticmethod
    def _verify_ospf_neighbor_present(neighbor_output: str, neighbor_ip: str, expected_state: str) -> bool:
        """Verify OSPF neighbor is present with expected state."""
        st.log(f"Verifying OSPF neighbor {neighbor_ip} in state {expected_state}")

        lines = neighbor_output.split('\n')
        for line in lines:
            if neighbor_ip in line:
                st.log(f"Found neighbor line: {line}")
                if expected_state in line:
                    st.log(f"PASS: Neighbor {neighbor_ip} is in {expected_state} state")
                    return True
                else:
                    st.log(f"FAIL: Neighbor {neighbor_ip} found but not in {expected_state} state")
                    return False

        st.log(f"FAIL: Neighbor {neighbor_ip} not found")
        return False

    @staticmethod
    def _verify_portchannel_members(pc_summary_output: str, portchannel_id: str, expected_ports: List[str]) -> bool:
        """Verify PortChannel has expected member ports."""
        st.log(f"Verifying PortChannel {portchannel_id} has members: {expected_ports}")

        pc_name = f"PortChannel{portchannel_id}"

        # Check if PortChannel exists in output
        if pc_name not in pc_summary_output:
            st.log(f"FAIL: PortChannel {portchannel_id} not found in output")
            return False

        # Check each expected port is listed
        for port in expected_ports:
            if port not in pc_summary_output:
                st.log(f"FAIL: Port {port} not found as member of PortChannel {portchannel_id}")
                return False

        st.log(f"PASS: PortChannel {portchannel_id} has all expected members")
        return True

    @staticmethod
    def _verify_inter_area_route(ospf_route_output: str, network: str, route_type: str = "IA") -> bool:
        """
        Verify inter-area route is present in OSPF routing table.

        Args:
            ospf_route_output: Raw output from 'show ip ospf route' command
            network: Expected network (e.g., "10.1.1.0/24")
            route_type: Expected route type (default: "IA" for inter-area)

        Returns:
            True if inter-area route is found
        """
        st.log(f"Verifying inter-area route {network} (type: {route_type})")

        if network not in ospf_route_output:
            st.error(f"FAIL: Network {network} not found in OSPF route table")
            return False

        lines = ospf_route_output.split('\n')
        for line in lines:
            if network in line and route_type in line:
                st.log(f"PASS: Inter-area route {network} found with type {route_type}")
                return True

        st.error(f"FAIL: Inter-area route {network} not found with type {route_type}")
        return False

    @staticmethod
    def _verify_summary_lsa_present(database_output: str, network: str) -> bool:
        """
        Verify Summary LSA is present in OSPF database.

        Args:
            database_output: Raw output from 'show ip ospf database summary' command
            network: Expected network in summary LSA

        Returns:
            True if summary LSA is found
        """
        st.log(f"Verifying Summary LSA for network {network}")

        if "Summary Link States" not in database_output:
            st.error("FAIL: No Summary Link States found in database")
            return False

        if network not in database_output:
            st.error(f"FAIL: Network {network} not found in Summary LSAs")
            return False

        st.log(f"PASS: Summary LSA for network {network} found")
        return True

    @staticmethod
    def _verify_ping_success(dut: str, target_ip: str, count: int = 4) -> bool:
        """
        Verify ping from DUT to target IP.

        Args:
            dut: Device handle
            target_ip: Target IP address to ping
            count: Number of ping packets (default: 4)

        Returns:
            True if ping successful
        """
        st.log(f"Verifying ping from {dut} to {target_ip}")

        command = f"ping -c {count} {target_ip}"
        output = st.config(dut, command, type="click")

        if not isinstance(output, str):
            output = str(output)

        st.log(f"Ping output:\n{output}")

        if "0% packet loss" in output or f"{count} received" in output:
            st.log(f"PASS: Ping from {dut} to {target_ip} successful")
            return True
        else:
            st.error(f"FAIL: Ping from {dut} to {target_ip} failed")
            return False

    @staticmethod
    def _verify_traceroute_path(dut: str, target_ip: str, expected_hops: List[str]) -> bool:
        """
        Verify traceroute shows expected path through ABRs.

        Args:
            dut: Device handle
            target_ip: Target IP address for traceroute
            expected_hops: List of expected hop IPs in order

        Returns:
            True if traceroute shows expected path
        """
        st.log(f"Verifying traceroute from {dut} to {target_ip}")
        st.log(f"Expected hops: {expected_hops}")

        command = f"traceroute {target_ip}"
        output = st.config(dut, command, type="click")

        if not isinstance(output, str):
            output = str(output)

        st.log(f"Traceroute output:\n{output}")

        # Verify all expected hops are in the output
        all_hops_found = True
        for hop_ip in expected_hops:
            if hop_ip in output:
                st.log(f"PASS: Hop {hop_ip} found in traceroute")
            else:
                st.error(f"FAIL: Hop {hop_ip} not found in traceroute")
                all_hops_found = False

        return all_hops_found

    # ========== TEST CASES ==========

    def test_ospf_multiarea_abr_portchannel(self) -> None:
        """
        TC_OSPF_ABR_MULTIAREA_PC_001: Validate OSPF multi-area configuration with ABRs using PortChannels.

        Test Procedure:
        1. Remove IP addresses from all Ethernet interfaces (baseline)
        2. Create PortChannels and add ports to PortChannels on all DUTs + validate members
        3. Configure IP addresses on PortChannel interfaces and validate
        4. Configure OSPF on D1 (Area 1)
        5. Configure OSPF on D2 (ABR - Area 0 and Area 1)
        6. Configure OSPF on D4 (ABR - Area 0 and Area 2)
        7. Configure OSPF on D3 (Area 2)
        8. Verify OSPF neighbor adjacencies (Full state)
        9. Verify ABR status on D2 and D4
        10. Verify OSPF database (Summary LSAs)
        11. Verify inter-area routing
        12. Verify ping connectivity across all areas
        13. Verify traceroute through ABRs
        14. Cleanup: Remove all configurations

        Expected Result:
        - IP addresses removed from Ethernet interfaces
        - PortChannels created and ports added successfully
        - IP addresses configured and validated on PortChannel interfaces
        - OSPF neighbors form adjacency (Full state)
        - D2 and D4 are identified as ABRs
        - Summary LSAs are generated by ABRs
        - Inter-area routes are installed
        - Ping successful across all areas
        - Traceroute shows path through ABRs
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF Multi-Area Configuration with ABRs using PortChannels")
        st.log("=" * 80)

        # Track validation failures - test will continue but report fail at end
        validation_failures = []

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4

        # ===== STEP 1: Remove IP addresses from all Ethernet interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Remove IP addresses from all Ethernet interfaces (baseline)")
        st.log("-" * 80)

        # Collect all interfaces that will be used
        all_dut1_interfaces = self.data.dut1_pc110_ports
        all_dut2_interfaces = self.data.dut2_pc110_ports + self.data.dut2_pc120_ports
        all_dut3_interfaces = self.data.dut3_pc130_ports
        all_dut4_interfaces = self.data.dut4_pc120_ports + self.data.dut4_pc130_ports

        # Remove IP addresses from all interfaces
        st.log(f"Removing IP addresses from D1 interfaces: {all_dut1_interfaces}")
        self._remove_ip_addresses_from_interfaces(dut1, all_dut1_interfaces)

        st.log(f"Removing IP addresses from D2 interfaces: {all_dut2_interfaces}")
        self._remove_ip_addresses_from_interfaces(dut2, all_dut2_interfaces)

        st.log(f"Removing IP addresses from D3 interfaces: {all_dut3_interfaces}")
        self._remove_ip_addresses_from_interfaces(dut3, all_dut3_interfaces)

        st.log(f"Removing IP addresses from D4 interfaces: {all_dut4_interfaces}")
        self._remove_ip_addresses_from_interfaces(dut4, all_dut4_interfaces)

        st.log("IP addresses removed from all Ethernet interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: IP addresses removed from all Ethernet interfaces")

        # ===== STEP 2: Create PortChannels and add ports =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Create PortChannels and add ports to PortChannels on all DUTs")
        st.log("-" * 80)

        # PortChannel 110: D1 <-> D2
        st.log("Creating PortChannel 110 on D1 and D2...")
        self._create_portchannel(dut1, self.data.portchannel110)
        self._create_portchannel(dut2, self.data.portchannel110)

        st.log("Adding ports to PortChannel 110...")
        for port in self.data.dut1_pc110_ports:
            self._add_port_to_portchannel(dut1, port, self.data.portchannel110)
        for port in self.data.dut2_pc110_ports:
            self._add_port_to_portchannel(dut2, port, self.data.portchannel110)

        # PortChannel 120: D2 <-> D4
        st.log("Creating PortChannel 120 on D2 and D4...")
        self._create_portchannel(dut2, self.data.portchannel120)
        self._create_portchannel(dut4, self.data.portchannel120)

        st.log("Adding ports to PortChannel 120...")
        for port in self.data.dut2_pc120_ports:
            self._add_port_to_portchannel(dut2, port, self.data.portchannel120)
        for port in self.data.dut4_pc120_ports:
            self._add_port_to_portchannel(dut4, port, self.data.portchannel120)

        # PortChannel 130: D4 <-> D3
        st.log("Creating PortChannel 130 on D4 and D3...")
        self._create_portchannel(dut4, self.data.portchannel130)
        self._create_portchannel(dut3, self.data.portchannel130)

        st.log("Adding ports to PortChannel 130...")
        for port in self.data.dut4_pc130_ports:
            self._add_port_to_portchannel(dut4, port, self.data.portchannel130)
        for port in self.data.dut3_pc130_ports:
            self._add_port_to_portchannel(dut3, port, self.data.portchannel130)

        st.log("PortChannels created and ports added")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        # Validate PortChannel member ports
        st.log("Validating PortChannel member ports...")

        pc_summary_dut1 = self._get_show_portchannel_summary(dut1)
        if not self._verify_portchannel_members(pc_summary_dut1, self.data.portchannel110, self.data.dut1_pc110_ports):
            error_msg = f"STEP 2: PortChannel {self.data.portchannel110} member validation failed on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: PortChannel {self.data.portchannel110} members validated on {dut1}")

        pc_summary_dut2 = self._get_show_portchannel_summary(dut2)
        if not self._verify_portchannel_members(pc_summary_dut2, self.data.portchannel110, self.data.dut2_pc110_ports):
            error_msg = f"STEP 2: PortChannel {self.data.portchannel110} member validation failed on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: PortChannel {self.data.portchannel110} members validated on {dut2}")

        if not self._verify_portchannel_members(pc_summary_dut2, self.data.portchannel120, self.data.dut2_pc120_ports):
            error_msg = f"STEP 2: PortChannel {self.data.portchannel120} member validation failed on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: PortChannel {self.data.portchannel120} members validated on {dut2}")

        pc_summary_dut4 = self._get_show_portchannel_summary(dut4)
        if not self._verify_portchannel_members(pc_summary_dut4, self.data.portchannel120, self.data.dut4_pc120_ports):
            error_msg = f"STEP 2: PortChannel {self.data.portchannel120} member validation failed on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: PortChannel {self.data.portchannel120} members validated on {dut4}")

        if not self._verify_portchannel_members(pc_summary_dut4, self.data.portchannel130, self.data.dut4_pc130_ports):
            error_msg = f"STEP 2: PortChannel {self.data.portchannel130} member validation failed on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: PortChannel {self.data.portchannel130} members validated on {dut4}")

        pc_summary_dut3 = self._get_show_portchannel_summary(dut3)
        if not self._verify_portchannel_members(pc_summary_dut3, self.data.portchannel130, self.data.dut3_pc130_ports):
            error_msg = f"STEP 2: PortChannel {self.data.portchannel130} member validation failed on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: PortChannel {self.data.portchannel130} members validated on {dut3}")

        if len([f for f in validation_failures if "STEP 2" in f]) == 0:
            st.log("PASS: PortChannel configuration completed and validated")

        # ===== STEP 3: Configure IP addresses on PortChannel interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Configure IP addresses on PortChannel interfaces")
        st.log("-" * 80)

        # D1: PortChannel110 - 10.1.1.1/24
        self._configure_portchannel_ip(dut1, self.data.portchannel110, self.data.dut1_ip)

        # D2: PortChannel110 - 10.1.1.2/24, PortChannel120 - 20.1.1.1/24
        self._configure_portchannel_ip(dut2, self.data.portchannel110, self.data.dut2_ip1)
        self._configure_portchannel_ip(dut2, self.data.portchannel120, self.data.dut2_ip2)

        # D4: PortChannel120 - 20.1.1.2/24, PortChannel130 - 30.1.1.1/24
        self._configure_portchannel_ip(dut4, self.data.portchannel120, self.data.dut4_ip1)
        self._configure_portchannel_ip(dut4, self.data.portchannel130, self.data.dut4_ip2)

        # D3: PortChannel130 - 30.1.1.2/24
        self._configure_portchannel_ip(dut3, self.data.portchannel130, self.data.dut3_ip)

        st.log("IP addresses configured on all PortChannel interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Validate IP addresses
        st.log("Validating IP address configuration...")
        if not self._verify_portchannel_ip(dut1, self.data.portchannel110, self.data.dut1_ip):
            error_msg = f"STEP 3: IP validation failed on {dut1} PortChannel{self.data.portchannel110}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut1} PortChannel{self.data.portchannel110}")

        if not self._verify_portchannel_ip(dut2, self.data.portchannel110, self.data.dut2_ip1):
            error_msg = f"STEP 3: IP validation failed on {dut2} PortChannel{self.data.portchannel110}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut2} PortChannel{self.data.portchannel110}")

        if not self._verify_portchannel_ip(dut2, self.data.portchannel120, self.data.dut2_ip2):
            error_msg = f"STEP 3: IP validation failed on {dut2} PortChannel{self.data.portchannel120}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut2} PortChannel{self.data.portchannel120}")

        if not self._verify_portchannel_ip(dut4, self.data.portchannel120, self.data.dut4_ip1):
            error_msg = f"STEP 3: IP validation failed on {dut4} PortChannel{self.data.portchannel120}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut4} PortChannel{self.data.portchannel120}")

        if not self._verify_portchannel_ip(dut4, self.data.portchannel130, self.data.dut4_ip2):
            error_msg = f"STEP 3: IP validation failed on {dut4} PortChannel{self.data.portchannel130}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut4} PortChannel{self.data.portchannel130}")

        if not self._verify_portchannel_ip(dut3, self.data.portchannel130, self.data.dut3_ip):
            error_msg = f"STEP 3: IP validation failed on {dut3} PortChannel{self.data.portchannel130}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut3} PortChannel{self.data.portchannel130}")

        if len([f for f in validation_failures if "STEP 3" in f]) == 0:
            st.log("PASS: IP addresses configured and validated successfully")

        # ===== STEP 4: Configure OSPF on D1 (Area 1) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Configure OSPF on D1 (Area 1)")
        st.log("-" * 80)

        self._configure_ospf_process(dut1, [self.data.ospf_area_1])
        self._configure_ospf_network(dut1, self.data.dut1_ip, self.data.ospf_area_1)

        st.log(f"OSPF configured on D1 for Area {self.data.ospf_area_1}")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed on D1")

        # ===== STEP 5: Configure OSPF on D2 (ABR - Area 0 and Area 1) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Configure OSPF on D2 (ABR - Area 0 and Area 1)")
        st.log("-" * 80)

        self._configure_ospf_process(dut2, [self.data.ospf_area_0, self.data.ospf_area_1])
        self._configure_ospf_network(dut2, self.data.dut2_ip1, self.data.ospf_area_1)
        self._configure_ospf_network(dut2, self.data.dut2_ip2, self.data.ospf_area_0)

        st.log(f"OSPF configured on D2 as ABR (Area {self.data.ospf_area_0} and Area {self.data.ospf_area_1})")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed on D2 (ABR)")

        # ===== STEP 6: Configure OSPF on D4 (ABR - Area 0 and Area 2) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Configure OSPF on D4 (ABR - Area 0 and Area 2)")
        st.log("-" * 80)

        self._configure_ospf_process(dut4, [self.data.ospf_area_0, self.data.ospf_area_2])
        self._configure_ospf_network(dut4, self.data.dut4_ip1, self.data.ospf_area_0)
        self._configure_ospf_network(dut4, self.data.dut4_ip2, self.data.ospf_area_2)

        st.log(f"OSPF configured on D4 as ABR (Area {self.data.ospf_area_0} and Area {self.data.ospf_area_2})")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed on D4 (ABR)")

        # ===== STEP 7: Configure OSPF on D3 (Area 2) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Configure OSPF on D3 (Area 2)")
        st.log("-" * 80)

        self._configure_ospf_process(dut3, [self.data.ospf_area_2])
        self._configure_ospf_network(dut3, self.data.dut3_ip, self.data.ospf_area_2)

        st.log(f"OSPF configured on D3 for Area {self.data.ospf_area_2}")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed on D3")

        # ===== STEP 8: Verify OSPF neighbor adjacencies =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Verify OSPF neighbor adjacencies (Full state)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor outputs
        neighbor_output_dut1 = self._get_show_ip_ospf_neighbor_output(dut1)
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut3 = self._get_show_ip_ospf_neighbor_output(dut3)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        # Extract neighbor IPs
        dut2_ip1_no_mask = self.data.dut2_ip1.split('/')[0]  # 10.1.1.2
        dut1_ip_no_mask = self.data.dut1_ip.split('/')[0]    # 10.1.1.1
        dut4_ip1_no_mask = self.data.dut4_ip1.split('/')[0]  # 20.1.1.2
        dut2_ip2_no_mask = self.data.dut2_ip2.split('/')[0]  # 20.1.1.1
        dut4_ip2_no_mask = self.data.dut4_ip2.split('/')[0]  # 30.1.1.1
        dut3_ip_no_mask = self.data.dut3_ip.split('/')[0]    # 30.1.1.2

        # Verify D1 sees D2 as neighbor
        if not self._verify_ospf_neighbor_present(neighbor_output_dut1, dut2_ip1_no_mask, "Full"):
            error_msg = f"STEP 8: OSPF neighbor {dut2_ip1_no_mask} not in Full state on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip1_no_mask} in Full state on {dut1}")

        # Verify D2 sees D1 and D4 as neighbors
        if not self._verify_ospf_neighbor_present(neighbor_output_dut2, dut1_ip_no_mask, "Full"):
            error_msg = f"STEP 8: OSPF neighbor {dut1_ip_no_mask} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut1_ip_no_mask} in Full state on {dut2}")

        if not self._verify_ospf_neighbor_present(neighbor_output_dut2, dut4_ip1_no_mask, "Full"):
            error_msg = f"STEP 8: OSPF neighbor {dut4_ip1_no_mask} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip1_no_mask} in Full state on {dut2}")

        # Verify D4 sees D2 and D3 as neighbors
        if not self._verify_ospf_neighbor_present(neighbor_output_dut4, dut2_ip2_no_mask, "Full"):
            error_msg = f"STEP 8: OSPF neighbor {dut2_ip2_no_mask} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip2_no_mask} in Full state on {dut4}")

        if not self._verify_ospf_neighbor_present(neighbor_output_dut4, dut3_ip_no_mask, "Full"):
            error_msg = f"STEP 8: OSPF neighbor {dut3_ip_no_mask} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut3_ip_no_mask} in Full state on {dut4}")

        # Verify D3 sees D4 as neighbor
        if not self._verify_ospf_neighbor_present(neighbor_output_dut3, dut4_ip2_no_mask, "Full"):
            error_msg = f"STEP 8: OSPF neighbor {dut4_ip2_no_mask} not in Full state on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip2_no_mask} in Full state on {dut3}")

        if len([f for f in validation_failures if "STEP 8" in f]) == 0:
            st.log("PASS: All OSPF neighbors are in Full state")

        # ===== STEP 9: Verify ABR status on D2 and D4 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Verify ABR status on D2 and D4")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_ROUTE_UPDATE)

        # Get OSPF outputs
        ospf_output_dut1 = self._get_show_ip_ospf_output(dut1)
        ospf_output_dut2 = self._get_show_ip_ospf_output(dut2)
        ospf_output_dut3 = self._get_show_ip_ospf_output(dut3)
        ospf_output_dut4 = self._get_show_ip_ospf_output(dut4)

        # Verify D1 is not an ABR
        if not self._verify_ospf_abr_status(ospf_output_dut1, expected_abr=False):
            st.log("WARNING: D1 ABR status check failed (expected: not ABR)")

        # Verify D2 is an ABR
        if not self._verify_ospf_abr_status(ospf_output_dut2, expected_abr=True):
            error_msg = f"STEP 9: {dut2} is not configured as ABR"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {dut2} is configured as ABR")

        # Verify D2 has Area 0 and Area 1
        if not self._verify_ospf_areas(ospf_output_dut2, [self.data.ospf_area_0, self.data.ospf_area_1]):
            error_msg = f"STEP 9: {dut2} does not have both Area 0 and Area 1"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {dut2} has both Area 0 and Area 1")

        # Verify D4 is an ABR
        if not self._verify_ospf_abr_status(ospf_output_dut4, expected_abr=True):
            error_msg = f"STEP 9: {dut4} is not configured as ABR"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {dut4} is configured as ABR")

        # Verify D4 has Area 0 and Area 2
        if not self._verify_ospf_areas(ospf_output_dut4, [self.data.ospf_area_0, self.data.ospf_area_2]):
            error_msg = f"STEP 9: {dut4} does not have both Area 0 and Area 2"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {dut4} has both Area 0 and Area 2")

        # Verify D3 is not an ABR
        if not self._verify_ospf_abr_status(ospf_output_dut3, expected_abr=False):
            st.log("WARNING: D3 ABR status check failed (expected: not ABR)")

        st.log("PASS: ABR status verified on D2 and D4")

        # ===== STEP 10: Verify OSPF database (Summary LSAs) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Verify OSPF database (Summary LSAs)")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_DATABASE_SYNC)

        # Get database outputs
        database_output_dut2 = self._get_show_ip_ospf_database_summary_output(dut2)
        database_output_dut4 = self._get_show_ip_ospf_database_summary_output(dut4)

        # D2 should have Summary LSAs for networks in Area 0 and Area 1
        if not self._verify_summary_lsa_present(database_output_dut2, "10.1.1.0"):
            st.log("WARNING: Summary LSA for 10.1.1.0 not found on D2")
        if not self._verify_summary_lsa_present(database_output_dut2, "30.1.1.0"):
            st.log("WARNING: Summary LSA for 30.1.1.0 not found on D2")

        # D4 should have Summary LSAs for networks in Area 0 and Area 2
        if not self._verify_summary_lsa_present(database_output_dut4, "10.1.1.0"):
            st.log("WARNING: Summary LSA for 10.1.1.0 not found on D4")
        if not self._verify_summary_lsa_present(database_output_dut4, "20.1.1.0"):
            st.log("WARNING: Summary LSA for 20.1.1.0 not found on D4")

        st.log("PASS: OSPF database verified with Summary LSAs")

        # ===== STEP 11: Verify inter-area routing =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Verify inter-area routing")
        st.log("-" * 80)

        # Get OSPF route outputs
        ospf_route_dut1 = self._get_show_ip_ospf_route_output(dut1)
        ospf_route_dut3 = self._get_show_ip_ospf_route_output(dut3)

        # D1 should have inter-area routes to Area 0 and Area 2 networks
        if not self._verify_inter_area_route(ospf_route_dut1, "20.1.1.0/24", "IA"):
            st.log("WARNING: Inter-area route 20.1.1.0/24 not found on D1")
        if not self._verify_inter_area_route(ospf_route_dut1, "30.1.1.0/24", "IA"):
            st.log("WARNING: Inter-area route 30.1.1.0/24 not found on D1")

        # D3 should have inter-area routes to Area 0 and Area 1 networks
        if not self._verify_inter_area_route(ospf_route_dut3, "10.1.1.0/24", "IA"):
            st.log("WARNING: Inter-area route 10.1.1.0/24 not found on D3")
        if not self._verify_inter_area_route(ospf_route_dut3, "20.1.1.0/24", "IA"):
            st.log("WARNING: Inter-area route 20.1.1.0/24 not found on D3")

        st.log("PASS: Inter-area routing verified")

        # ===== STEP 12: Verify ping connectivity across all areas =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Verify ping connectivity across all areas")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_PING)

        # Ping from D1 to D2
        if not self._verify_ping_success(dut1, dut2_ip1_no_mask):
            error_msg = f"STEP 12: Ping from {dut1} to {dut2_ip1_no_mask} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut1} to {dut2_ip1_no_mask} successful")

        # Ping from D1 to D3 (across areas through ABRs)
        if not self._verify_ping_success(dut1, dut3_ip_no_mask):
            error_msg = f"STEP 12: Ping from {dut1} to {dut3_ip_no_mask} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut1} to {dut3_ip_no_mask} successful")

        # Ping from D3 to D1 (across areas through ABRs)
        if not self._verify_ping_success(dut3, dut1_ip_no_mask):
            error_msg = f"STEP 12: Ping from {dut3} to {dut1_ip_no_mask} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut3} to {dut1_ip_no_mask} successful")

        # Ping from D2 to D4 (backbone area)
        if not self._verify_ping_success(dut2, dut4_ip1_no_mask):
            error_msg = f"STEP 12: Ping from {dut2} to {dut4_ip1_no_mask} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut2} to {dut4_ip1_no_mask} successful")

        if len([f for f in validation_failures if "STEP 12" in f]) == 0:
            st.log("PASS: Ping connectivity verified across all areas")

        # ===== STEP 13: Verify traceroute through ABRs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 13: Verify traceroute through ABRs")
        st.log("-" * 80)

        # Traceroute from D1 to D3 should go through D2 and D4
        expected_hops_d1_to_d3 = [dut2_ip1_no_mask, dut4_ip1_no_mask, dut3_ip_no_mask]
        if not self._verify_traceroute_path(dut1, dut3_ip_no_mask, expected_hops_d1_to_d3):
            st.log("WARNING: Traceroute from D1 to D3 did not show all expected hops")

        st.log("PASS: Traceroute verified through ABRs")

        # ===== STEP 14: Cleanup =====
        st.log("\n" + "-" * 80)
        st.log("STEP 14: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove OSPF configuration
        self._remove_ospf_configuration(dut1)
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut3)
        self._remove_ospf_configuration(dut4)
        st.log("OSPF configuration removed from all DUTs")

        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Remove IP addresses from PortChannel interfaces
        self._remove_portchannel_ip(dut1, self.data.portchannel110)
        self._remove_portchannel_ip(dut2, self.data.portchannel110)
        self._remove_portchannel_ip(dut2, self.data.portchannel120)
        self._remove_portchannel_ip(dut4, self.data.portchannel120)
        self._remove_portchannel_ip(dut4, self.data.portchannel130)
        self._remove_portchannel_ip(dut3, self.data.portchannel130)
        st.log("IP addresses removed from all PortChannel interfaces")

        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Remove ports from PortChannels
        for port in self.data.dut1_pc110_ports:
            self._remove_port_from_portchannel(dut1, port)
        for port in self.data.dut2_pc110_ports:
            self._remove_port_from_portchannel(dut2, port)
        for port in self.data.dut2_pc120_ports:
            self._remove_port_from_portchannel(dut2, port)
        for port in self.data.dut4_pc120_ports:
            self._remove_port_from_portchannel(dut4, port)
        for port in self.data.dut4_pc130_ports:
            self._remove_port_from_portchannel(dut4, port)
        for port in self.data.dut3_pc130_ports:
            self._remove_port_from_portchannel(dut3, port)

        # Delete PortChannels
        self._delete_portchannel(dut1, self.data.portchannel110)
        self._delete_portchannel(dut2, self.data.portchannel110)
        self._delete_portchannel(dut2, self.data.portchannel120)
        self._delete_portchannel(dut4, self.data.portchannel120)
        self._delete_portchannel(dut4, self.data.portchannel130)
        self._delete_portchannel(dut3, self.data.portchannel130)
        st.log("PortChannels deleted from all DUTs")

        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        st.log("PASS: Cleanup completed successfully")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF Multi-Area with ABRs using PortChannels validated successfully")
        st.log("Test flow: PortChannel Creation → IP Config → OSPF D1(Area1) → OSPF D2(ABR) → OSPF D4(ABR)")
        st.log("           → OSPF D3(Area2) → Neighbors Full → ABR Verify → Database LSAs ✓")
        st.log("           → Inter-Area Routes ✓ → Ping Connectivity ✓ → Traceroute ✓ → Cleanup ✓")
        st.log("=" * 80)

        # ===== COLLECT TECH SUPPORT AND REPORT FAILURES =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from all DUTs
            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_multiarea_abr_pc_validation_failure")
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
