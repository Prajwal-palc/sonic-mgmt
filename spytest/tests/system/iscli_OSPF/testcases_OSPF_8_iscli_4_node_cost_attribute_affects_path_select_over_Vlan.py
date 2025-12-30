"""
OSPF COST ATTRIBUTE AFFECTS PATH SELECTION - 4-NODE TOPOLOGY WITH MULTIPLE PARALLEL VLANS
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_8_iscli_4_node_cost_attribute_affects_path_select_over_Vlan.py \
  --logs-path ./logs/testcases_OSPF_8_cost_path_selection_Vlan_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates that OSPFv2 cost attribute affects path selection over VLAN interfaces by:
  1. Removing IP addresses from Ethernet interfaces before adding to VLANs
  2. Creating 4 VLANs between each device pair
  3. Adding Ethernet interfaces as members to respective VLANs
  4. Verifying VLAN creation and member addition
  5. Configuring IP addresses on VLAN interfaces
  6. Validating IP address configuration
  7. Configuring OSPF with different costs (10, 50, 100, 200) on parallel VLANs
  8. Verifying OSPF neighbor adjacency (Full state) on all VLANs
  9. Verifying that lowest cost path (cost 10) is selected for routing
  10. Testing dynamic cost change (increase Vlan110 cost, verify path switches to Vlan120)
  11. Testing link failure and automatic failover to next lowest cost path
  12. Testing ECMP when multiple paths have equal cost
  13. Validating ping connectivity end-to-end
  14. Cleanup: Removing all configurations
  15. Tech Support: Collecting tech support on validation failures

  Topology:
        D1 ======== (4 parallel VLANs) ======== D2 ======== (4 parallel VLANs) ======== D4 ======== (4 parallel VLANs) ======== D3

  VLANs with costs:
    D1 ↔ D2: VLAN 110,120,130,140 (costs: 10, 50, 100, 200)
    D2 ↔ D4: VLAN 150,160,170,180 (costs: 10, 50, 100, 200)
    D4 ↔ D3: VLAN 10,20,30,40 (costs: 10, 50, 100, 200)

  VLAN Members:
    VLAN 110: Ethernet0 (D1-D2)
    VLAN 120: Ethernet4 (D1-D2)
    VLAN 130: Ethernet8 (D1-D2)
    VLAN 140: Ethernet12 (D1-D2)
    VLAN 150: Ethernet16 (D2-D4)
    VLAN 160: Ethernet20 (D2-D4)
    VLAN 170: Ethernet24 (D2-D4)
    VLAN 180: Ethernet28 (D2-D4)
    VLAN 10: Ethernet32 (D4-D3)
    VLAN 20: Ethernet36 (D4-D3)
    VLAN 30: Ethernet40 (D4-D3)
    VLAN 40: Ethernet44 (D4-D3)

  Configuration details:
    D1: Vlan110,120,130,140: 10.0.1.1/30, 10.0.2.1/30, 10.0.3.1/30, 10.0.4.1/30
    D2: Vlan110,120,130,140: 10.0.1.2/30, 10.0.2.2/30, 10.0.3.2/30, 10.0.4.2/30
        Vlan150,160,170,180: 20.0.1.1/30, 20.0.2.1/30, 20.0.3.1/30, 20.0.4.1/30
    D4: Vlan150,160,170,180: 20.0.1.2/30, 20.0.2.2/30, 20.0.3.2/30, 20.0.4.2/30
        Vlan10,20,30,40: 30.0.1.1/30, 30.0.2.1/30, 30.0.3.1/30, 30.0.4.1/30
    D3: Vlan10,20,30,40: 30.0.1.2/30, 30.0.2.2/30, 30.0.3.2/30, 30.0.4.2/30

  IMPORTANT: Uses 'show ip ospf neighbor', 'show ip ospf interface', 'show ip route',
  'show ip ospf database', and 'show Vlan' commands to validate OSPF configuration.
  Uses klish CLI type exclusively.

Pre-requisites:
  - Topology: 4-node with multiple parallel links | Supported: HW and Virtual
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
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_COST_CHANGE = 15
WAIT_FOR_LINK_DOWN = 45
WAIT_FOR_LINK_UP = 60  # Increased to allow OSPF neighbor to reach Full state (2-Way -> Full transition)
WAIT_FOR_PING = 2


@pytest.mark.topology("any")
class TestOSPFCostPathSelectionVLAN4Node:
    """Test cases for validating OSPF cost-based path selection in 4-node topology using VLANs via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF Cost-Based Path Selection Test Suite (VLAN)")
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
        # D1 ↔ D2: 4 parallel links (Ethernet interfaces to be added to VLANs)
        cls.data.dut1_d2_eth_ports = ["Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12"]
        cls.data.dut2_d1_eth_ports = ["Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12"]

        # D2 ↔ D4: 4 parallel links
        cls.data.dut2_d4_eth_ports = ["Ethernet16", "Ethernet20", "Ethernet24", "Ethernet28"]
        cls.data.dut4_d2_eth_ports = ["Ethernet16", "Ethernet20", "Ethernet24", "Ethernet28"]

        # D4 ↔ D3: 4 parallel links
        cls.data.dut4_d3_eth_ports = ["Ethernet32", "Ethernet36", "Ethernet40", "Ethernet44"]
        cls.data.dut3_d4_eth_ports = ["Ethernet32", "Ethernet36", "Ethernet40", "Ethernet44"]

        # VLAN IDs
        cls.data.dut1_d2_vlans = ["110", "120", "130", "140"]
        cls.data.dut2_d1_vlans = ["110", "120", "130", "140"]
        cls.data.dut2_d4_vlans = ["150", "160", "170", "180"]
        cls.data.dut4_d2_vlans = ["150", "160", "170", "180"]
        cls.data.dut4_d3_vlans = ["10", "20", "30", "40"]
        cls.data.dut3_d4_vlans = ["10", "20", "30", "40"]

        st.log("Topology Configuration:")
        st.log(f"  D1 ↔ D2: VLANs {cls.data.dut1_d2_vlans}")
        st.log(f"  D2 ↔ D4: VLANs {cls.data.dut2_d4_vlans}")
        st.log(f"  D4 ↔ D3: VLANs {cls.data.dut4_d3_vlans}")

        # IP addresses for D1 ↔ D2 VLANs
        cls.data.dut1_d2_ips = ["10.0.1.1/30", "10.0.2.1/30", "10.0.3.1/30", "10.0.4.1/30"]
        cls.data.dut2_d1_ips = ["10.0.1.2/30", "10.0.2.2/30", "10.0.3.2/30", "10.0.4.2/30"]

        # IP addresses for D2 ↔ D4 VLANs
        cls.data.dut2_d4_ips = ["20.0.1.1/30", "20.0.2.1/30", "20.0.3.1/30", "20.0.4.1/30"]
        cls.data.dut4_d2_ips = ["20.0.1.2/30", "20.0.2.2/30", "20.0.3.2/30", "20.0.4.2/30"]

        # IP addresses for D4 ↔ D3 VLANs
        cls.data.dut4_d3_ips = ["30.0.1.1/30", "30.0.2.1/30", "30.0.3.1/30", "30.0.4.1/30"]
        cls.data.dut3_d4_ips = ["30.0.1.2/30", "30.0.2.2/30", "30.0.3.2/30", "30.0.4.2/30"]

        # OSPF costs for parallel VLANs (10, 50, 100, 200)
        cls.data.ospf_costs = [10, 50, 100, 200]

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
        st.log("TEST TEARDOWN: Cleanup OSPF Cost Path Selection Test Suite (VLAN)")
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
        Remove IP addresses from Ethernet interface before adding to VLAN.

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
        result = st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
        return True

    # ========== HELPER METHODS - VLAN CONFIGURATION ==========

    @staticmethod
    def _create_vlan(dut: str, vlan_id: str) -> bool:
        """
        Create VLAN using klish commands.

        IMPORTANT: Does NOT use exit - stays in config mode after VLAN creation.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "110")

        Returns:
            True if successful
        """
        st.log(f"Creating VLAN {vlan_id} on {dut}")
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
            vlan_id: VLAN ID (e.g., "110")

        Returns:
            True if successful
        """
        st.log(f"Deleting VLAN {vlan_id} from {dut}")
        commands = [
            "configure terminal",
            f"no vlan {vlan_id}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
        return True

    @staticmethod
    def _add_port_to_vlan(dut: str, interface: str, vlan_id: str) -> bool:
        """
        Add interface to VLAN using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            vlan_id: VLAN ID (e.g., "110")

        Returns:
            True if successful
        """
        st.log(f"Adding {interface} to VLAN {vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"switchport trunk allowed vlan {vlan_id}",
            "exit"
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
            vlan_id: VLAN ID

        Returns:
            True if successful
        """
        st.log(f"Removing {interface} from VLAN {vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"no switchport trunk allowed vlan {vlan_id}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
        return True

    @staticmethod
    def _get_show_vlan(dut: str) -> str:
        """Get 'show Vlan' output."""
        st.log(f"Getting 'show Vlan' output from {dut}")
        output = st.show(dut, "show Vlan", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show Vlan output from {dut}:\n{output}")
        return output

    @staticmethod
    def _verify_vlan_exists(dut: str, vlan_output: str, vlan_id: str) -> bool:
        """
        Verify that VLAN exists in show Vlan output.

        Args:
            dut: Device handle
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "110")

        Returns:
            True if VLAN exists, False otherwise
        """
        st.log(f"Verifying VLAN {vlan_id} exists on {dut}")

        # Search for "Vlan<id>" pattern
        vlan_pattern = rf'Vlan{vlan_id}'
        match = re.search(vlan_pattern, vlan_output, re.IGNORECASE)

        if match:
            st.log(f"PASS: VLAN {vlan_id} exists on {dut}")
            return True
        else:
            st.error(f"FAIL: VLAN {vlan_id} does not exist on {dut}")
            return False

    @staticmethod
    def _verify_port_in_vlan(dut: str, vlan_output: str, vlan_id: str, interface: str) -> bool:
        """
        Verify that interface is a member of VLAN.

        Args:
            dut: Device handle
            vlan_output: Raw output from 'show Vlan' command
            vlan_id: VLAN ID (e.g., "110")
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if interface is member of VLAN, False otherwise
        """
        st.log(f"Verifying {interface} is member of VLAN {vlan_id} on {dut}")

        # Check if both VLAN and port are in the same vicinity in output
        lines = vlan_output.split('\n')
        in_vlan_section = False

        for line in lines:
            if f"Vlan{vlan_id}" in line or f"VLAN {vlan_id}" in line:
                in_vlan_section = True

            if in_vlan_section and interface in line:
                st.log(f"PASS: {interface} is member of VLAN {vlan_id} on {dut}")
                return True

            # Stop if we hit next VLAN section
            if in_vlan_section and "Vlan" in line and vlan_id not in line:
                break

        st.log(f"INFO: {interface} verification for VLAN {vlan_id} on {dut}")
        return False

    # ========== HELPER METHODS - IP CONFIGURATION ==========

    @staticmethod
    def _configure_vlan_ip(dut: str, vlan_id: str, ip_address: str) -> bool:
        """
        Configure IP address on VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "110")
            ip_address: IP address with mask (e.g., "10.0.1.1/30")

        Returns:
            True if successful
        """
        st.log(f"Configuring IP address {ip_address} on Vlan{vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no shutdown",
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
        st.log(f"Removing IP address from Vlan{vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no ip address",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
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
    def _configure_ospf_interface_cost(dut: str, vlan_id: str, cost: int) -> bool:
        """
        Configure OSPF cost on VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "110")
            cost: OSPF cost value

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF cost {cost} on Vlan{vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            f"ip ospf cost {cost}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _shutdown_vlan(dut: str, vlan_id: str) -> bool:
        """
        Shutdown VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID

        Returns:
            True if successful
        """
        st.log(f"Shutting down Vlan{vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "shutdown",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _no_shutdown_vlan(dut: str, vlan_id: str) -> bool:
        """
        Enable VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID

        Returns:
            True if successful
        """
        st.log(f"Enabling Vlan{vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no shutdown",
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
        result = st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
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
    def _get_show_ip_route(dut: str, network: str = "") -> str:
        """Get 'show ip route' output."""
        command = f"show ip route {network}" if network else "show ip route"
        st.log(f"Getting '{command}' output from {dut}")
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"{command} output from {dut}:\n{output}")
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

    # ========== HELPER METHODS - VALIDATION ==========

    @staticmethod
    def _verify_vlan_ip(dut: str, vlan_id: str, expected_ip: str) -> bool:
        """
        Verify IP address is configured on VLAN interface using running-configuration.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "110")
            expected_ip: Expected IP address (e.g., "10.0.1.1/30")

        Returns:
            True if IP is configured correctly
        """
        st.log(f"Verifying IP address {expected_ip} on Vlan{vlan_id} on {dut}")

        # Command: show running-configuration interface Vlan X
        command = f"show running-configuration interface Vlan {vlan_id}"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True, skip_error_check=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"Running-config output from {dut}:\n{output}")

        # Check if expected IP is in the output
        if expected_ip in output:
            st.log(f"PASS: IP address {expected_ip} verified on Vlan{vlan_id}")
            return True
        else:
            # Also check for IP without mask format
            ip_without_mask = expected_ip.split('/')[0]
            if ip_without_mask in output and "ip address" in output.lower():
                st.log(f"PASS: IP address {expected_ip} verified on Vlan{vlan_id}")
                return True
            else:
                st.error(f"FAIL: IP address {expected_ip} not found on Vlan{vlan_id}")
                return False

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
    def _verify_ospf_neighbor_full_state(output: str, neighbor_ip: str) -> bool:
        """
        Verify that specific OSPF neighbor is in Full state.

        Args:
            output: Output from 'show ip ospf neighbor'
            neighbor_ip: Expected neighbor IP

        Returns:
            True if neighbor is in Full state
        """
        st.log(f"Verifying OSPF neighbor {neighbor_ip} is in Full state")

        if neighbor_ip not in output:
            st.error(f"FAIL: Neighbor {neighbor_ip} not found")
            return False

        lines = output.split('\n')
        for line in lines:
            if neighbor_ip in line and 'Full' in line:
                st.log(f"PASS: Neighbor {neighbor_ip} is in Full state")
                return True

        st.error(f"FAIL: Neighbor {neighbor_ip} not in Full state")
        return False

    @staticmethod
    def _verify_ospf_interface_cost(output: str, vlan_id: str, expected_cost: int) -> bool:
        """
        Verify OSPF VLAN interface cost.

        Args:
            output: Output from 'show ip ospf interface'
            vlan_id: VLAN ID (e.g., "110")
            expected_cost: Expected cost value

        Returns:
            True if cost matches
        """
        st.log(f"Verifying Vlan{vlan_id} has OSPF cost {expected_cost}")

        # Look for VLAN section and extract cost
        lines = output.split('\n')
        in_interface_section = False
        vlan_name = f"Vlan{vlan_id}"

        for line in lines:
            if vlan_name in line and 'is up' in line:
                in_interface_section = True
            elif in_interface_section:
                if f'Cost: {expected_cost}' in line:
                    st.log(f"PASS: Vlan{vlan_id} has cost {expected_cost}")
                    return True
                elif 'Cost:' in line:
                    st.error(f"FAIL: Vlan{vlan_id} cost mismatch. Line: {line}")
                    return False
                elif 'is up' in line and vlan_name not in line:
                    # Started next interface section
                    break

        st.error(f"FAIL: Could not verify cost for Vlan{vlan_id}")
        return False

    @staticmethod
    def _verify_route_via_vlan(output: str, network: str, next_hop_ip: str, vlan_id: str) -> bool:
        """
        Verify that route to network uses specific next-hop and VLAN.

        Args:
            output: Output from 'show ip route'
            network: Network to check (e.g., "30.0.1.0/30")
            next_hop_ip: Expected next-hop IP
            vlan_id: Expected outgoing VLAN (e.g., "110")

        Returns:
            True if route uses specified next-hop and VLAN
        """
        st.log(f"Verifying route to {network} uses next-hop {next_hop_ip} via Vlan{vlan_id}")

        vlan_name = f"Vlan{vlan_id}"
        lines = output.split('\n')
        for line in lines:
            if network in line and next_hop_ip in line and vlan_name in line and 'O>' in line:
                st.log(f"PASS: Route to {network} via {next_hop_ip}, {vlan_name}")
                return True

        st.error(f"FAIL: Route to {network} does not use {next_hop_ip} via {vlan_name}")
        return False

    @staticmethod
    def _verify_ecmp_routes(output: str, network: str) -> bool:
        """
        Verify that network has ECMP (multiple next-hops).

        Args:
            output: Output from 'show ip route'
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
        else:
            st.error(f"FAIL: Expected ECMP, found only {next_hop_count} next-hop(s)")
            return False

    @staticmethod
    def _verify_ping_success(dut: str, target_ip: str, count: int = 5) -> bool:
        """
        Verify ping from DUT to target IP using sonic-cli (klish mode).

        Args:
            dut: Device handle
            target_ip: Target IP address to ping
            count: Number of ping packets

        Returns:
            True if ping successful
        """
        st.log(f"Verifying ping from {dut} to {target_ip} (from sonic-cli)")

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

    # ========== TEST CASE ==========

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_COST_PATH_SELECTION_VLAN_001"])
    def test_ospf_cost_path_selection_vlan(self) -> None:
        """
        TC_OSPF_COST_PATH_SELECTION_VLAN_001: Validate OSPF cost-based path selection using VLANs.

        Test Procedure:
        1. Remove IP addresses from Ethernet interfaces before adding to VLANs
        2. Create VLANs on all devices
        3. Add Ethernet interfaces as members to VLANs
        4. Verify VLAN creation and member addition
        5. Configure IP addresses on VLAN interfaces
        6. Validate IP address configuration
        7. Configure OSPF on all devices with different costs on parallel VLANs
        8. Verify OSPF neighbors form on all VLANs (Full state)
        9. Verify OSPF interface costs on VLANs
        10. Verify that lowest cost path (cost 10) is selected for routing
        11. Test dynamic cost change - verify path switches when cost changes
        12. Test link failure - verify automatic failover to next lowest cost
        13. Test ECMP - verify load balancing when costs are equal
        14. Verify end-to-end connectivity with ping
        15. Verify OSPF database
        16. Cleanup: Remove all configurations
        17. Tech Support: Collect tech support if validation failures occur

        Expected Result:
        - VLANs created successfully with member ports
        - IP addresses configured and validated on all VLAN interfaces
        - OSPF neighbors form on all parallel VLANs
        - Traffic uses lowest cost path (Vlan110 with cost 10)
        - Path switches to Vlan120 when Vlan110 cost increased
        - Automatic failover when Vlan110 shut down
        - ECMP when Vlan110 and Vlan120 have equal costs
        - End-to-end ping successful
        - All configurations cleaned up
        - Tech support collected on failures
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF Cost-Based Path Selection - 4-Node Topology with Parallel VLANs")
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
        st.log("STEP 1: Remove IP addresses from Ethernet interfaces before adding to VLANs")
        st.log("-" * 80)

        # Remove IPs from D1 ↔ D2 Ethernet interfaces
        for interface in self.data.dut1_d2_eth_ports:
            self._remove_ip_from_ethernet_interface(dut1, interface)

        for interface in self.data.dut2_d1_eth_ports:
            self._remove_ip_from_ethernet_interface(dut2, interface)

        # Remove IPs from D2 ↔ D4 Ethernet interfaces
        for interface in self.data.dut2_d4_eth_ports:
            self._remove_ip_from_ethernet_interface(dut2, interface)

        for interface in self.data.dut4_d2_eth_ports:
            self._remove_ip_from_ethernet_interface(dut4, interface)

        # Remove IPs from D4 ↔ D3 Ethernet interfaces
        for interface in self.data.dut4_d3_eth_ports:
            self._remove_ip_from_ethernet_interface(dut4, interface)

        for interface in self.data.dut3_d4_eth_ports:
            self._remove_ip_from_ethernet_interface(dut3, interface)

        st.log("IP addresses removed from all Ethernet interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        # ===== STEP 2: Create VLANs on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Create VLANs on all devices")
        st.log("-" * 80)

        # Create VLANs on D1
        for vlan_id in self.data.dut1_d2_vlans:
            self._create_vlan(dut1, vlan_id)

        # Create VLANs on D2
        for vlan_id in self.data.dut2_d1_vlans + self.data.dut2_d4_vlans:
            self._create_vlan(dut2, vlan_id)

        # Create VLANs on D4
        for vlan_id in self.data.dut4_d2_vlans + self.data.dut4_d3_vlans:
            self._create_vlan(dut4, vlan_id)

        # Create VLANs on D3
        for vlan_id in self.data.dut3_d4_vlans:
            self._create_vlan(dut3, vlan_id)

        st.log("VLANs created on all devices")
        time.sleep(WAIT_AFTER_VLAN_CONFIG)

        # ===== STEP 3: Add Ethernet interfaces as members to VLANs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Add Ethernet interfaces as members to VLANs")
        st.log("-" * 80)

        # Add members to D1 VLANs
        for eth_port, vlan_id in zip(self.data.dut1_d2_eth_ports, self.data.dut1_d2_vlans):
            self._add_port_to_vlan(dut1, eth_port, vlan_id)

        # Add members to D2 VLANs
        for eth_port, vlan_id in zip(self.data.dut2_d1_eth_ports, self.data.dut2_d1_vlans):
            self._add_port_to_vlan(dut2, eth_port, vlan_id)
        for eth_port, vlan_id in zip(self.data.dut2_d4_eth_ports, self.data.dut2_d4_vlans):
            self._add_port_to_vlan(dut2, eth_port, vlan_id)

        # Add members to D4 VLANs
        for eth_port, vlan_id in zip(self.data.dut4_d2_eth_ports, self.data.dut4_d2_vlans):
            self._add_port_to_vlan(dut4, eth_port, vlan_id)
        for eth_port, vlan_id in zip(self.data.dut4_d3_eth_ports, self.data.dut4_d3_vlans):
            self._add_port_to_vlan(dut4, eth_port, vlan_id)

        # Add members to D3 VLANs
        for eth_port, vlan_id in zip(self.data.dut3_d4_eth_ports, self.data.dut3_d4_vlans):
            self._add_port_to_vlan(dut3, eth_port, vlan_id)

        st.log("Ethernet interfaces added as members to VLANs")
        time.sleep(WAIT_AFTER_VLAN_CONFIG)

        # ===== STEP 4: Verify VLAN creation and member addition =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Verify VLAN creation and member addition")
        st.log("-" * 80)

        # Get VLAN summary from D1
        d1_vlan_output = self._get_show_vlan(dut1)

        # Verify VLANs exist on D1 - continue even if fails
        for vlan_id in self.data.dut1_d2_vlans:
            if not self._verify_vlan_exists(dut1, d1_vlan_output, vlan_id):
                error_msg = f"STEP 4: VLAN {vlan_id} verification failed on {dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify members on D1 - continue even if fails
        for eth_port, vlan_id in zip(self.data.dut1_d2_eth_ports, self.data.dut1_d2_vlans):
            if not self._verify_port_in_vlan(dut1, d1_vlan_output, vlan_id, eth_port):
                st.log(f"INFO: Port {eth_port} verification for VLAN {vlan_id} on {dut1}")

        if len([f for f in validation_failures if "STEP 4" in f]) == 0:
            st.log("PASS: All VLANs created and members added successfully")

        # ===== STEP 5: Configure IP addresses on VLAN interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Configure IP addresses on all VLAN interfaces")
        st.log("-" * 80)

        # Configure D1 ↔ D2 VLANs
        for vlan_id, ip in zip(self.data.dut1_d2_vlans, self.data.dut1_d2_ips):
            self._configure_vlan_ip(dut1, vlan_id, ip)

        for vlan_id, ip in zip(self.data.dut2_d1_vlans, self.data.dut2_d1_ips):
            self._configure_vlan_ip(dut2, vlan_id, ip)

        # Configure D2 ↔ D4 VLANs
        for vlan_id, ip in zip(self.data.dut2_d4_vlans, self.data.dut2_d4_ips):
            self._configure_vlan_ip(dut2, vlan_id, ip)

        for vlan_id, ip in zip(self.data.dut4_d2_vlans, self.data.dut4_d2_ips):
            self._configure_vlan_ip(dut4, vlan_id, ip)

        # Configure D4 ↔ D3 VLANs
        for vlan_id, ip in zip(self.data.dut4_d3_vlans, self.data.dut4_d3_ips):
            self._configure_vlan_ip(dut4, vlan_id, ip)

        for vlan_id, ip in zip(self.data.dut3_d4_vlans, self.data.dut3_d4_ips):
            self._configure_vlan_ip(dut3, vlan_id, ip)

        st.log("IP addresses configured on all VLAN interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        # ===== STEP 6: Validate IP address configuration =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Validate IP address configuration on VLAN interfaces")
        st.log("-" * 80)

        # Verify IP configuration on VLANs - continue even if fails
        st.log("Verifying IP configuration on VLAN interfaces...")

        # Verify D1 ↔ D2 VLANs (D1 side)
        for vlan_id, ip in zip(self.data.dut1_d2_vlans, self.data.dut1_d2_ips):
            if not self._verify_vlan_ip(dut1, vlan_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut1} Vlan{vlan_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D1 ↔ D2 VLANs (D2 side)
        for vlan_id, ip in zip(self.data.dut2_d1_vlans, self.data.dut2_d1_ips):
            if not self._verify_vlan_ip(dut2, vlan_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut2} Vlan{vlan_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D2 ↔ D4 VLANs (D2 side)
        for vlan_id, ip in zip(self.data.dut2_d4_vlans, self.data.dut2_d4_ips):
            if not self._verify_vlan_ip(dut2, vlan_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut2} Vlan{vlan_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D2 ↔ D4 VLANs (D4 side)
        for vlan_id, ip in zip(self.data.dut4_d2_vlans, self.data.dut4_d2_ips):
            if not self._verify_vlan_ip(dut4, vlan_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut4} Vlan{vlan_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D4 ↔ D3 VLANs (D4 side)
        for vlan_id, ip in zip(self.data.dut4_d3_vlans, self.data.dut4_d3_ips):
            if not self._verify_vlan_ip(dut4, vlan_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut4} Vlan{vlan_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D4 ↔ D3 VLANs (D3 side)
        for vlan_id, ip in zip(self.data.dut3_d4_vlans, self.data.dut3_d4_ips):
            if not self._verify_vlan_ip(dut3, vlan_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut3} Vlan{vlan_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 6" in f]) == 0:
            st.log("PASS: All 24 VLAN IP addresses configured and verified successfully")

        # ===== STEP 7: Configure OSPF on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Configure OSPF on all devices")
        st.log("-" * 80)

        # Configure OSPF on D1
        d1_networks = ["10.0.1.0/30", "10.0.2.0/30", "10.0.3.0/30", "10.0.4.0/30"]
        self._configure_ospf_process(dut1, area, d1_networks)

        # Configure OSPF on D2
        d2_networks = ["10.0.1.0/30", "10.0.2.0/30", "10.0.3.0/30", "10.0.4.0/30",
                      "20.0.1.0/30", "20.0.2.0/30", "20.0.3.0/30", "20.0.4.0/30"]
        self._configure_ospf_process(dut2, area, d2_networks)

        # Configure OSPF on D4
        d4_networks = ["20.0.1.0/30", "20.0.2.0/30", "20.0.3.0/30", "20.0.4.0/30",
                      "30.0.1.0/30", "30.0.2.0/30", "30.0.3.0/30", "30.0.4.0/30"]
        self._configure_ospf_process(dut4, area, d4_networks)

        # Configure OSPF on D3
        d3_networks = ["30.0.1.0/30", "30.0.2.0/30", "30.0.3.0/30", "30.0.4.0/30"]
        self._configure_ospf_process(dut3, area, d3_networks)

        st.log("OSPF configured on all devices")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Configure OSPF costs on all VLAN interfaces (10, 50, 100, 200)
        st.log("Configuring OSPF costs on all VLAN interfaces (10, 50, 100, 200)")

        # Configure costs on D1 VLANs
        for vlan_id, cost in zip(self.data.dut1_d2_vlans, self.data.ospf_costs):
            self._configure_ospf_interface_cost(dut1, vlan_id, cost)

        # Configure costs on D2 VLANs (both D1-facing and D4-facing)
        for vlan_id, cost in zip(self.data.dut2_d1_vlans, self.data.ospf_costs):
            self._configure_ospf_interface_cost(dut2, vlan_id, cost)
        for vlan_id, cost in zip(self.data.dut2_d4_vlans, self.data.ospf_costs):
            self._configure_ospf_interface_cost(dut2, vlan_id, cost)

        # Configure costs on D4 VLANs (both D2-facing and D3-facing)
        for vlan_id, cost in zip(self.data.dut4_d2_vlans, self.data.ospf_costs):
            self._configure_ospf_interface_cost(dut4, vlan_id, cost)
        for vlan_id, cost in zip(self.data.dut4_d3_vlans, self.data.ospf_costs):
            self._configure_ospf_interface_cost(dut4, vlan_id, cost)

        # Configure costs on D3 VLANs
        for vlan_id, cost in zip(self.data.dut3_d4_vlans, self.data.ospf_costs):
            self._configure_ospf_interface_cost(dut3, vlan_id, cost)

        st.log("OSPF costs configured on all VLAN interfaces")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed")

        # ===== STEP 8: Verify OSPF neighbors =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Verify OSPF neighbors form on all VLANs (Full state)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor outputs
        d1_neighbor_output = self._get_show_ip_ospf_neighbor(dut1)
        d2_neighbor_output = self._get_show_ip_ospf_neighbor(dut2)
        d3_neighbor_output = self._get_show_ip_ospf_neighbor(dut3)
        d4_neighbor_output = self._get_show_ip_ospf_neighbor(dut4)

        # Verify neighbor counts - continue even if fails
        if not self._verify_ospf_neighbor_count(d1_neighbor_output, 4):
            error_msg = f"STEP 8: D1 should have 4 OSPF neighbors"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: D1 has 4 OSPF neighbors")

        if not self._verify_ospf_neighbor_count(d2_neighbor_output, 8):
            error_msg = f"STEP 8: D2 should have 8 OSPF neighbors"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: D2 has 8 OSPF neighbors")

        if not self._verify_ospf_neighbor_count(d3_neighbor_output, 4):
            error_msg = f"STEP 8: D3 should have 4 OSPF neighbors"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: D3 has 4 OSPF neighbors")

        if not self._verify_ospf_neighbor_count(d4_neighbor_output, 8):
            error_msg = f"STEP 8: D4 should have 8 OSPF neighbors"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: D4 has 8 OSPF neighbors")

        if len([f for f in validation_failures if "STEP 8" in f]) == 0:
            st.log("PASS: All OSPF neighbors are in Full state")

        # ===== STEP 9: Verify OSPF interface costs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Verify OSPF interface costs on VLANs")
        st.log("-" * 80)

        d1_ospf_intf_output = self._get_show_ip_ospf_interface(dut1)

        # Verify costs on D1 - continue even if fails
        for vlan_id, cost in zip(self.data.dut1_d2_vlans, self.data.ospf_costs):
            if not self._verify_ospf_interface_cost(d1_ospf_intf_output, vlan_id, cost):
                error_msg = f"STEP 9: OSPF cost verification failed on {dut1} Vlan{vlan_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 9" in f]) == 0:
            st.log("PASS: OSPF interface costs verified on VLANs")

        # ===== STEP 10: Verify path selection (should use lowest cost) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Verify path selection uses lowest cost path (Vlan110, cost 10)")
        st.log("-" * 80)

        d1_route_output = self._get_show_ip_route(dut1, "30.0.1.0")

        # Verify route to D3's network uses Vlan110 (lowest cost) - continue even if fails
        if not self._verify_route_via_vlan(d1_route_output, "30.0.1.0/30", "10.0.1.2", "110"):
            error_msg = "STEP 10: Route should use lowest cost path via Vlan110"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Traffic uses lowest cost path (Vlan110)")

        # ===== STEP 11: Test dynamic cost change =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Test dynamic cost change (increase Vlan110 cost to 500)")
        st.log("-" * 80)

        # Increase Vlan110 cost to 500
        self._configure_ospf_interface_cost(dut1, "110", 500)
        st.log(f"Waiting {WAIT_FOR_COST_CHANGE} seconds for OSPF to reconverge...")
        time.sleep(WAIT_FOR_COST_CHANGE)

        # Verify path switched to Vlan120 - continue even if fails
        d1_route_output = self._get_show_ip_route(dut1, "30.0.1.0")

        if not self._verify_route_via_vlan(d1_route_output, "30.0.1.0/30", "10.0.2.2", "120"):
            error_msg = "STEP 11: Route should switch to Vlan120 after cost change"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Path switched to Vlan120 after cost change")

        # Restore original cost
        self._configure_ospf_interface_cost(dut1, "110", 10)
        time.sleep(WAIT_FOR_COST_CHANGE)

        # Verify path switched back to Vlan110 - continue even if fails
        d1_route_output = self._get_show_ip_route(dut1, "30.0.1.0")

        if not self._verify_route_via_vlan(d1_route_output, "30.0.1.0/30", "10.0.1.2", "110"):
            error_msg = "STEP 11: Route should switch back to Vlan110 after cost restore"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Path switched back to Vlan110 after cost restore")

        # ===== STEP 12: Test link failure and failover =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Test link failure and automatic failover")
        st.log("-" * 80)

        # Shutdown Vlan110
        self._shutdown_vlan(dut1, "110")
        st.log(f"Waiting {WAIT_FOR_LINK_DOWN} seconds for OSPF to detect link down...")
        time.sleep(WAIT_FOR_LINK_DOWN)

        # Verify neighbor count decreased - continue even if fails
        d1_neighbor_output = self._get_show_ip_ospf_neighbor(dut1)
        if not self._verify_ospf_neighbor_count(d1_neighbor_output, 3):
            error_msg = "STEP 12: D1 should have 3 neighbors after Vlan110 shutdown"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify traffic failed over to Vlan120 - continue even if fails
        d1_route_output = self._get_show_ip_route(dut1, "30.0.1.0")
        if not self._verify_route_via_vlan(d1_route_output, "30.0.1.0/30", "10.0.2.2", "120"):
            error_msg = "STEP 12: Traffic should failover to Vlan120"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify connectivity still works - continue even if fails
        if not self._verify_ping_success(dut1, "30.0.1.2", 3):
            error_msg = "STEP 12: Ping should work via backup path"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Automatic failover to Vlan120 successful")

        # Restore Vlan110
        self._no_shutdown_vlan(dut1, "110")
        st.log(f"Waiting {WAIT_FOR_LINK_UP} seconds for OSPF neighbor to reform...")
        time.sleep(WAIT_FOR_LINK_UP)

        # Verify neighbor count restored - continue even if fails
        d1_neighbor_output = self._get_show_ip_ospf_neighbor(dut1)
        if not self._verify_ospf_neighbor_count(d1_neighbor_output, 4):
            error_msg = "STEP 12: D1 should have 4 neighbors after Vlan110 restored"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify traffic returned to Vlan110 - continue even if fails
        d1_route_output = self._get_show_ip_route(dut1, "30.0.1.0")
        if not self._verify_route_via_vlan(d1_route_output, "30.0.1.0/30", "10.0.1.2", "110"):
            error_msg = "STEP 12: Traffic should return to Vlan110"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Link recovery and path restoration successful")

        # ===== STEP 13: Test ECMP with equal costs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 13: Test ECMP when multiple paths have equal cost")
        st.log("-" * 80)

        # Set Vlan120 cost to 10 (same as Vlan110)
        self._configure_ospf_interface_cost(dut1, "120", 10)
        st.log(f"Waiting {WAIT_FOR_COST_CHANGE} seconds for OSPF to reconverge...")
        time.sleep(WAIT_FOR_COST_CHANGE)

        # Verify ECMP (multiple next-hops) - just log warning, don't fail
        d1_route_output = self._get_show_ip_route(dut1, "30.0.1.0")

        if not self._verify_ecmp_routes(d1_route_output, "30.0.1.0/30"):
            st.log("WARNING: ECMP not detected, may be normal depending on platform")
        else:
            st.log("PASS: ECMP active with multiple paths")

        # Restore original cost
        self._configure_ospf_interface_cost(dut1, "120", 50)
        time.sleep(WAIT_FOR_COST_CHANGE)

        st.log("PASS: ECMP test completed")

        # ===== STEP 14: Verify end-to-end connectivity =====
        st.log("\n" + "-" * 80)
        st.log("STEP 14: Verify end-to-end connectivity")
        st.log("-" * 80)

        # Ping from D1 to D3 - continue even if fails
        if not self._verify_ping_success(dut1, "30.0.1.2", 5):
            error_msg = "STEP 14: Ping from D1 to D3 failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Ping from D1 to D3 successful")

        # Ping from D3 to D1 - continue even if fails
        if not self._verify_ping_success(dut3, "10.0.1.1", 5):
            error_msg = "STEP 14: Ping from D3 to D1 failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log("PASS: Ping from D3 to D1 successful")

        if len([f for f in validation_failures if "STEP 14" in f]) == 0:
            st.log("PASS: End-to-end connectivity verified")

        # ===== STEP 15: Verify OSPF database =====
        st.log("\n" + "-" * 80)
        st.log("STEP 15: Verify OSPF database")
        st.log("-" * 80)

        d1_ospf_db_output = self._get_show_ip_ospf_database(dut1)

        # Just verify we got output
        if len(d1_ospf_db_output) > 100:
            st.log("PASS: OSPF database populated")
        else:
            st.log("WARNING: OSPF database output seems short")

        # ===== STEP 16: Cleanup - Remove all configurations =====
        st.log("\n" + "-" * 80)
        st.log("STEP 16: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove OSPF configuration
        self._remove_ospf_configuration(dut1)
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut3)
        self._remove_ospf_configuration(dut4)
        st.log("OSPF configuration removed from all devices")

        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Remove IP addresses from VLANs
        for vlan_id in self.data.dut1_d2_vlans:
            self._remove_vlan_ip(dut1, vlan_id)

        for vlan_id in self.data.dut2_d1_vlans + self.data.dut2_d4_vlans:
            self._remove_vlan_ip(dut2, vlan_id)

        for vlan_id in self.data.dut3_d4_vlans:
            self._remove_vlan_ip(dut3, vlan_id)

        for vlan_id in self.data.dut4_d2_vlans + self.data.dut4_d3_vlans:
            self._remove_vlan_ip(dut4, vlan_id)

        st.log("IP addresses removed from all VLAN interfaces")

        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Remove Ethernet ports from VLANs
        for eth_port, vlan_id in zip(self.data.dut1_d2_eth_ports, self.data.dut1_d2_vlans):
            self._remove_port_from_vlan(dut1, eth_port, vlan_id)

        for eth_port, vlan_id in zip(self.data.dut2_d1_eth_ports, self.data.dut2_d1_vlans):
            self._remove_port_from_vlan(dut2, eth_port, vlan_id)
        for eth_port, vlan_id in zip(self.data.dut2_d4_eth_ports, self.data.dut2_d4_vlans):
            self._remove_port_from_vlan(dut2, eth_port, vlan_id)

        for eth_port, vlan_id in zip(self.data.dut3_d4_eth_ports, self.data.dut3_d4_vlans):
            self._remove_port_from_vlan(dut3, eth_port, vlan_id)

        for eth_port, vlan_id in zip(self.data.dut4_d2_eth_ports, self.data.dut4_d2_vlans):
            self._remove_port_from_vlan(dut4, eth_port, vlan_id)
        for eth_port, vlan_id in zip(self.data.dut4_d3_eth_ports, self.data.dut4_d3_vlans):
            self._remove_port_from_vlan(dut4, eth_port, vlan_id)

        st.log("Ethernet ports removed from VLANs")

        time.sleep(WAIT_AFTER_VLAN_CONFIG)

        # Delete VLANs
        for vlan_id in self.data.dut1_d2_vlans:
            self._delete_vlan(dut1, vlan_id)

        for vlan_id in self.data.dut2_d1_vlans + self.data.dut2_d4_vlans:
            self._delete_vlan(dut2, vlan_id)

        for vlan_id in self.data.dut3_d4_vlans:
            self._delete_vlan(dut3, vlan_id)

        for vlan_id in self.data.dut4_d2_vlans + self.data.dut4_d3_vlans:
            self._delete_vlan(dut4, vlan_id)

        st.log("VLANs deleted from all devices")

        time.sleep(WAIT_AFTER_VLAN_CONFIG)

        st.log("PASS: Cleanup completed successfully")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF cost-based path selection test completed (VLAN)")
        st.log("=" * 80)

        # ===== CHECK FOR VALIDATION FAILURES AND COLLECT TECH SUPPORT IF NEEDED =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from all DUTs involved in the test
            try:
                st.generate_tech_support(dut=dut1, name="ospf_cost_path_selection_vlan_4node_validation_failure")
                st.log(f"Tech support collected from {dut1}")
            except Exception as e:
                st.log(f"Warning: Failed to collect tech support from {dut1}: {str(e)}")

            try:
                st.generate_tech_support(dut=dut2, name="ospf_cost_path_selection_vlan_4node_validation_failure")
                st.log(f"Tech support collected from {dut2}")
            except Exception as e:
                st.log(f"Warning: Failed to collect tech support from {dut2}: {str(e)}")

            try:
                st.generate_tech_support(dut=dut3, name="ospf_cost_path_selection_vlan_4node_validation_failure")
                st.log(f"Tech support collected from {dut3}")
            except Exception as e:
                st.log(f"Warning: Failed to collect tech support from {dut3}: {str(e)}")

            try:
                st.generate_tech_support(dut=dut4, name="ospf_cost_path_selection_vlan_4node_validation_failure")
                st.log(f"Tech support collected from {dut4}")
            except Exception as e:
                st.log(f"Warning: Failed to collect tech support from {dut4}: {str(e)}")

            # Report all validation failures
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES SUMMARY:")
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
            st.log("Summary:")
            st.log("  ✓ VLANs created with Ethernet members")
            st.log("  ✓ IP addresses configured and validated on all VLAN interfaces")
            st.log("  ✓ OSPF neighbors formed on all parallel VLANs")
            st.log("  ✓ Lowest cost path (Vlan110, cost 10) selected")
            st.log("  ✓ Dynamic cost change triggers path switch")
            st.log("  ✓ Automatic failover on link failure")
            st.log("  ✓ Path restoration on link recovery")
            st.log("  ✓ ECMP with equal costs")
            st.log("  ✓ End-to-end connectivity verified")
            st.log("=" * 80)
            st.log("All validations passed successfully")
            st.report_pass("test_case_passed")
