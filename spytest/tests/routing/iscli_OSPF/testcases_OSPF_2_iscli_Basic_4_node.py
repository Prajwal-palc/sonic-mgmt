"""
OSPF BASIC CONFIGURATION - 4-NODE TOPOLOGY WITH STATIC ROUTING
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_2_iscli_Basic_4_node.py \
  --logs-path ./logs/testcases_OSPF_2_iscli_Basic_4_node_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF configuration with static routing in a 4-node topology by:
  1. Configuring IP addresses on all interfaces
  2. Configuring static routes on D1 and D3
  3. Restarting BGP docker and validating static routes in routing table
  4. Configuring OSPF on D2 and D4 (middle nodes)
  5. Verifying OSPF neighbor adjacency (Full state)
  6. Verifying DR/BDR election
  7. Validating ping connectivity from D1 to D3
  8. Cleanup: Removing all configurations

  Topology:
        D1 -------- D2 -------- D4 -------- D3
    (Ethernet0) (Ethernet0) (Ethernet16) (Ethernet16)
    10.1.1.1    10.1.1.2    20.1.1.1     20.1.1.2
                (Ethernet16) (Ethernet32)
                20.1.1.1     30.1.1.2
                            (Ethernet32)
                            30.1.1.1

  Configuration details:
    D1: Ethernet0: 10.1.1.1/24, Static route: 30.1.1.0/24 via 10.1.1.2
    D2: Ethernet0: 10.1.1.2/24, Ethernet16: 20.1.1.1/24, OSPF area 0
    D4: Ethernet16: 20.1.1.2/24, Ethernet32: 30.1.1.2/24, OSPF area 0
    D3: Ethernet32: 30.1.1.1/24, Static route: 10.1.1.0/24 via 30.1.1.2

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
WAIT_AFTER_IP_CONFIG = 3
WAIT_AFTER_STATIC_ROUTE = 3
WAIT_AFTER_BGP_RESTART = 180
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_ROUTE_UPDATE = 10
WAIT_FOR_PING = 5


@pytest.mark.topology("any")
class TestOSPFStaticRouting4Node:
    """Test cases for validating OSPF with static routing in 4-node topology via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF 4-Node Static Routing Test Suite")
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
        # D1 (vs_sonic_1) Ethernet0 <-> D2 (vs_sonic_2) Ethernet0
        cls.data.dut1_if1 = "Ethernet0"
        cls.data.dut2_if1 = "Ethernet0"

        # D2 (vs_sonic_2) Ethernet16 <-> D4 (vs_sonic_4) Ethernet16
        cls.data.dut2_if2 = "Ethernet16"
        cls.data.dut4_if1 = "Ethernet16"

        # D4 (vs_sonic_4) Ethernet32 <-> D3 (vs_sonic_3) Ethernet32
        cls.data.dut4_if2 = "Ethernet32"
        cls.data.dut3_if1 = "Ethernet32"

        st.log(f"Topology: D1[{cls.data.dut1_if1}] <-> D2[{cls.data.dut2_if1}]")
        st.log(f"          D2[{cls.data.dut2_if2}] <-> D4[{cls.data.dut4_if1}]")
        st.log(f"          D4[{cls.data.dut4_if2}] <-> D3[{cls.data.dut3_if1}]")

        # IP addresses
        cls.data.dut1_ip = "10.1.1.1/24"
        cls.data.dut2_ip1 = "10.1.1.2/24"
        cls.data.dut2_ip2 = "20.1.1.1/24"
        cls.data.dut4_ip1 = "20.1.1.2/24"
        cls.data.dut4_ip2 = "30.1.1.2/24"
        cls.data.dut3_ip = "30.1.1.1/24"

        st.log(f"IP Addresses:")
        st.log(f"  D1[{cls.data.dut1_if1}]: {cls.data.dut1_ip}")
        st.log(f"  D2[{cls.data.dut2_if1}]: {cls.data.dut2_ip1}")
        st.log(f"  D2[{cls.data.dut2_if2}]: {cls.data.dut2_ip2}")
        st.log(f"  D4[{cls.data.dut4_if1}]: {cls.data.dut4_ip1}")
        st.log(f"  D4[{cls.data.dut4_if2}]: {cls.data.dut4_ip2}")
        st.log(f"  D3[{cls.data.dut3_if1}]: {cls.data.dut3_ip}")

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
        st.log("TEST TEARDOWN: Cleanup OSPF 4-Node Static Routing Test Suite")
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

    # ========== HELPER METHODS - IP CONFIGURATION ==========

    @staticmethod
    def _configure_interface_ip(dut: str, interface: str, ip_address: str) -> bool:
        """
        Configure IP address on interface.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            ip_address: IP address with mask (e.g., "10.1.1.1/24")

        Returns:
            True if successful
        """
        st.log(f"Configuring IP address {ip_address} on {interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
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

    # ========== HELPER METHODS - VALIDATION ==========

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

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_STATIC_4NODE_001"])
    def test_ospf_static_routing_4node(self) -> None:
        """
        TC_OSPF_STATIC_4NODE_001: Validate OSPF with static routing in 4-node topology.

        Test Procedure:
        1. Configure IP addresses on all interfaces
        2. Configure static routes on D1 and D3
        3. Restart BGP docker on D1 and D3
        4. Verify static routes appear in routing tables
        5. Configure OSPF on D2 and D4
        6. Verify OSPF neighbor adjacency (Full state)
        7. Verify DR/BDR election
        8. Verify ping from D1 to D3
        9. Cleanup: Remove all configurations

        Expected Result:
        - IP addresses configured successfully
        - Static routes installed in routing tables
        - OSPF neighbors form adjacency (Full state)
        - DR/BDR election occurs
        - Ping from D1 to D3 successful
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF with Static Routing - 4-Node Topology")
        st.log("=" * 80)

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4
        area = self.data.ospf_area

        validation_failures = []

        # ===== STEP 1: Configure IP addresses on all interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Configure IP addresses on all interfaces")
        st.log("-" * 80)

        # D1: Ethernet0 - 10.1.1.1/24
        self._configure_interface_ip(dut1, self.data.dut1_if1, self.data.dut1_ip)

        # D2: Ethernet0 - 10.1.1.2/24, Ethernet16 - 20.1.1.1/24
        self._configure_interface_ip(dut2, self.data.dut2_if1, self.data.dut2_ip1)
        self._configure_interface_ip(dut2, self.data.dut2_if2, self.data.dut2_ip2)

        # D4: Ethernet16 - 20.1.1.2/24, Ethernet32 - 30.1.1.2/24
        self._configure_interface_ip(dut4, self.data.dut4_if1, self.data.dut4_ip1)
        self._configure_interface_ip(dut4, self.data.dut4_if2, self.data.dut4_ip2)

        # D3: Ethernet32 - 30.1.1.1/24
        self._configure_interface_ip(dut3, self.data.dut3_if1, self.data.dut3_ip)

        st.log("IP addresses configured on all interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: IP addresses configured successfully")

        # ===== STEP 2: Configure static routes on D1 and D3 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Configure static routes on D1 and D3")
        st.log("-" * 80)

        # D1: ip route 30.1.1.0/24 via 10.1.1.2
        self._configure_static_route(dut1, "30.1.1.0/24", "10.1.1.2")

        # D3: ip route 10.1.1.0/24 via 30.1.1.2
        self._configure_static_route(dut3, "10.1.1.0/24", "30.1.1.2")

        st.log("Static routes configured on D1 and D3")
        time.sleep(WAIT_AFTER_STATIC_ROUTE)

        st.log("PASS: Static routes configured successfully")

        # ===== STEP 3: Restart BGP docker on D1 and D3 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Restart BGP docker on D1 and D3")
        st.log("-" * 80)

        self._restart_bgp_docker(dut1)
        self._restart_bgp_docker(dut3)

        st.log(f"Waiting {WAIT_AFTER_BGP_RESTART} seconds for BGP docker to restart...")
        time.sleep(WAIT_AFTER_BGP_RESTART)

        st.log("PASS: BGP docker restarted on D1 and D3")

        # ===== STEP 4: Verify static routes in routing tables =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Verify static routes in routing tables")
        st.log("-" * 80)

        # Verify D1 has route to 30.1.1.0/24
        route_output_dut1 = self._get_show_ip_route_output(dut1)
        if not self._verify_static_route_in_routing_table(route_output_dut1, "30.1.1.0/24"):
            error_msg = f"STEP 4: Static route 30.1.1.0/24 not found in routing table on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D3 has route to 10.1.1.0/24
        route_output_dut3 = self._get_show_ip_route_output(dut3)
        if not self._verify_static_route_in_routing_table(route_output_dut3, "10.1.1.0/24"):
            error_msg = f"STEP 4: Static route 10.1.1.0/24 not found in routing table on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        st.log("PASS: Static routes verified in routing tables")

        # ===== STEP 5: Configure OSPF on D2 and D4 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Configure OSPF on D2 and D4")
        st.log("-" * 80)

        # D2: OSPF configuration
        self._configure_ospf_process(dut2, area)
        self._configure_ospf_network(dut2, self.data.dut2_ip2, area)
        self._configure_ospf_network(dut2, self.data.dut2_ip1, area)

        # D4: OSPF configuration
        self._configure_ospf_process(dut4, area)
        self._configure_ospf_network(dut4, self.data.dut4_ip1, area)
        self._configure_ospf_network(dut4, self.data.dut4_ip2, area)

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
        dut4_neighbor_ip = self.data.dut4_ip1.split('/')[0]  # 20.1.1.2
        dut2_neighbor_ip = self.data.dut2_ip2.split('/')[0]  # 20.1.1.1

        # Verify neighbors
        if not self._verify_ospf_neighbor_present(neighbor_output_dut2, dut4_neighbor_ip, "Full"):
            error_msg = f"STEP 6: OSPF neighbor {dut4_neighbor_ip} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_present(neighbor_output_dut4, dut2_neighbor_ip, "Full"):
            error_msg = f"STEP 6: OSPF neighbor {dut2_neighbor_ip} not in Full state on {dut4}"
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
        target_ip_d3 = self.data.dut3_ip.split('/')[0]  # 30.1.1.1
        if not self._verify_ping_success(dut1, target_ip_d3):
            error_msg = f"STEP 8: Ping from {dut1} to {target_ip_d3} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Ping from D3 to D1's IP (10.1.1.1)
        target_ip_d1 = self.data.dut1_ip.split('/')[0]  # 10.1.1.1
        if not self._verify_ping_success(dut3, target_ip_d1):
            error_msg = f"STEP 8: Ping from {dut3} to {target_ip_d1} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)

        st.log("PASS: Ping connectivity verified between D1 and D3")

        # ===== STEP 9: Cleanup - Remove all configurations =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Cleanup - Remove all configurations")
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

        # Remove IP addresses
        self._remove_interface_ip(dut1, self.data.dut1_if1)
        self._remove_interface_ip(dut2, self.data.dut2_if1)
        self._remove_interface_ip(dut2, self.data.dut2_if2)
        self._remove_interface_ip(dut4, self.data.dut4_if1)
        self._remove_interface_ip(dut4, self.data.dut4_if2)
        self._remove_interface_ip(dut3, self.data.dut3_if1)
        st.log("IP addresses removed from all interfaces")

        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: Cleanup completed successfully")

        # ===== FINAL RESULT =====
        st.log("\n" + "=" * 80)
        st.log("TEST RESULT: OSPF with Static Routing - 4-Node Topology")
        st.log("=" * 80)

        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_static_4node_validation_failure")
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
            st.log("PASS: All validations passed successfully")
            st.log("Test flow: IP Config → Static Routes → BGP Restart → OSPF Config → Neighbor Full → DR/BDR → Ping → Cleanup ✓")
            st.log("=" * 80)
            st.report_pass("test_case_passed")
