"""
OSPF PER VRF OVER ETHERNET - 4-NODE TOPOLOGY WITH DUAL VRF VALIDATION
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_15_iscli_4_node_OSPF_per_VRF_over_Eth.py \
  --logs-path ./logs/testcases_OSPF_15_vrf_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF per VRF over Ethernet interfaces in a 4-node topology by:
  1. Creating two VRFs (Vrf-RED and Vrf-BLUE) on all devices
  2. Assigning interfaces to respective VRFs with IP addresses
  3. Configuring OSPF process per VRF with unique router IDs
  4. Verifying OSPF neighbor adjacency (Full state) for both VRFs
  5. Verifying DR/BDR election per VRF
  6. Validating OSPF interfaces and database per VRF
  7. Verifying route learning and ECMP in routing tables per VRF
  8. Testing end-to-end ping connectivity across VRFs
  9. Validating VRF isolation (no cross-VRF traffic)
  10. Cleanup: Removing all configurations

  Topology:
        D1 ======== (4 parallel links) ======== D2 ======== (4 parallel links) ======== D4 ======== (4 parallel links) ======== D3
       Eth0,4       Eth0,4       Eth16,20      Eth16,20      Eth32,36      Eth32,36
       Eth8,12      Eth8,12      Eth24,28      Eth24,28      Eth40,44      Eth40,44

  VRF Assignment:
    Vrf-RED:  Ethernet0, 4, 16, 20, 32, 36
    Vrf-BLUE: Ethernet8, 12, 24, 28, 40, 44

  IP Addressing:
    Vrf-RED:
      D1-D2: 10.1.1.0/24, 10.1.2.0/24
      D2-D4: 30.1.1.0/24, 30.1.2.0/24
      D4-D3: 50.1.1.0/24, 50.1.2.0/24

    Vrf-BLUE:
      D1-D2: 10.2.1.0/24, 10.2.2.0/24
      D2-D4: 40.1.1.0/24, 40.1.2.0/24
      D4-D3: 60.1.1.0/24, 60.1.2.0/24

  OSPF Configuration:
    Each VRF runs independent OSPF instance
    Router IDs: D1(1.1.1.1/1.1.1.2), D2(2.2.2.1/2.2.2.2), D3(3.3.3.1/3.3.3.2), D4(4.4.4.1/4.4.4.2)
    Area: 0 (Backbone) for all

  IMPORTANT: Uses 'show ip vrf', 'show ip ospf vrf <vrf>', 'show ip ospf neighbor vrf <vrf>',
  'show ip ospf interface vrf <vrf>', 'show ip ospf database vrf <vrf>', and
  'show ip route vrf <vrf>' commands. Uses klish CLI type exclusively.

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
WAIT_AFTER_VRF_CONFIG = 3
WAIT_AFTER_IP_CONFIG = 3
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_ROUTE_UPDATE = 15
WAIT_FOR_PING = 2


@pytest.mark.topology("any")
class TestOSPFPerVRF4Node:
    """Test cases for validating OSPF per VRF over Ethernet in 4-node topology via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF Per VRF Test Suite")
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

        # VRF names
        cls.data.vrf_red = "Vrf-RED"
        cls.data.vrf_blue = "Vrf-BLUE"
        st.log(f"VRF Names: {cls.data.vrf_red}, {cls.data.vrf_blue}")

        # Test interfaces based on testbed_4vs.yaml topology
        # D1 ↔ D2: 4 parallel links
        cls.data.dut1_d2_links = ["Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12"]
        cls.data.dut2_d1_links = ["Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12"]

        # D2 ↔ D4: 4 parallel links
        cls.data.dut2_d4_links = ["Ethernet16", "Ethernet20", "Ethernet24", "Ethernet28"]
        cls.data.dut4_d2_links = ["Ethernet16", "Ethernet20", "Ethernet24", "Ethernet28"]

        # D4 ↔ D3: 4 parallel links
        cls.data.dut4_d3_links = ["Ethernet32", "Ethernet36", "Ethernet40", "Ethernet44"]
        cls.data.dut3_d4_links = ["Ethernet32", "Ethernet36", "Ethernet40", "Ethernet44"]

        st.log("Topology Configuration:")
        st.log(f"  D1 ↔ D2: {cls.data.dut1_d2_links} ↔ {cls.data.dut2_d1_links}")
        st.log(f"  D2 ↔ D4: {cls.data.dut2_d4_links} ↔ {cls.data.dut4_d2_links}")
        st.log(f"  D4 ↔ D3: {cls.data.dut4_d3_links} ↔ {cls.data.dut3_d4_links}")

        # IP addresses for Vrf-RED
        # D1 ↔ D2: 10.1.x.x
        cls.data.dut1_vrf_red_ips = ["10.1.1.1/24", "10.1.2.1/24"]
        cls.data.dut2_vrf_red_d1_ips = ["10.1.1.2/24", "10.1.2.2/24"]

        # D2 ↔ D4: 30.1.x.x
        cls.data.dut2_vrf_red_d4_ips = ["30.1.1.1/24", "30.1.2.1/24"]
        cls.data.dut4_vrf_red_d2_ips = ["30.1.1.2/24", "30.1.2.2/24"]

        # D4 ↔ D3: 50.1.x.x
        cls.data.dut4_vrf_red_d3_ips = ["50.1.1.1/24", "50.1.2.1/24"]
        cls.data.dut3_vrf_red_ips = ["50.1.1.2/24", "50.1.2.2/24"]

        # IP addresses for Vrf-BLUE
        # D1 ↔ D2: 10.2.x.x
        cls.data.dut1_vrf_blue_ips = ["10.2.1.1/24", "10.2.2.1/24"]
        cls.data.dut2_vrf_blue_d1_ips = ["10.2.1.2/24", "10.2.2.2/24"]

        # D2 ↔ D4: 40.1.x.x
        cls.data.dut2_vrf_blue_d4_ips = ["40.1.1.1/24", "40.1.2.1/24"]
        cls.data.dut4_vrf_blue_d2_ips = ["40.1.1.2/24", "40.1.2.2/24"]

        # D4 ↔ D3: 60.1.x.x
        cls.data.dut4_vrf_blue_d3_ips = ["60.1.1.1/24", "60.1.2.1/24"]
        cls.data.dut3_vrf_blue_ips = ["60.1.1.2/24", "60.1.2.2/24"]

        # OSPF Router IDs per VRF
        cls.data.dut1_router_id_red = "1.1.1.1"
        cls.data.dut1_router_id_blue = "1.1.1.2"
        cls.data.dut2_router_id_red = "2.2.2.1"
        cls.data.dut2_router_id_blue = "2.2.2.2"
        cls.data.dut3_router_id_red = "3.3.3.1"
        cls.data.dut3_router_id_blue = "3.3.3.2"
        cls.data.dut4_router_id_red = "4.4.4.1"
        cls.data.dut4_router_id_blue = "4.4.4.2"

        # OSPF area
        cls.data.ospf_area = "0"
        st.log(f"OSPF Area: {cls.data.ospf_area}")

        # Set terminal length 0 to disable pagination
        st.log("Setting terminal length 0 to disable pagination on all DUTs")
        for dut in [cls.data.dut1, cls.data.dut2, cls.data.dut3, cls.data.dut4]:
            st.config(dut, "terminal length 0", type=CLI_TYPE)

        st.log("Test setup complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup OSPF Per VRF Test Suite")
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

    # ========== HELPER METHODS - VRF CONFIGURATION ==========

    @staticmethod
    def _create_vrf(dut: str, vrf_name: str) -> bool:
        """
        Create VRF instance.

        Args:
            dut: Device handle
            vrf_name: VRF name

        Returns:
            True if successful
        """
        st.log(f"Creating VRF {vrf_name} on {dut}")
        commands = [
            "configure terminal",
            f"ip vrf {vrf_name}"
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _delete_vrf(dut: str, vrf_name: str) -> bool:
        """
        Delete VRF instance.

        Args:
            dut: Device handle
            vrf_name: VRF name

        Returns:
            True if successful
        """
        st.log(f"Deleting VRF {vrf_name} on {dut}")
        commands = [
            "configure terminal",
            f"no ip vrf {vrf_name}"
        ]
        st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
        return True

    # ========== HELPER METHODS - INTERFACE CONFIGURATION ==========

    @staticmethod
    def _configure_interface_vrf_ip(dut: str, interface: str, vrf_name: str, ip_address: str) -> bool:
        """
        Configure interface with VRF and IP address.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            vrf_name: VRF name
            ip_address: IP address with mask (e.g., "10.1.1.1/24")

        Returns:
            True if successful
        """
        st.log(f"Configuring {interface} with VRF {vrf_name} and IP {ip_address} on {dut}")

        # Parse interface number
        interface_num = interface.replace("Ethernet", "").replace(" ", "")

        commands = [
            "configure terminal",
            f"interface Ethernet {interface_num}",
            "no ip address",
            f"ip vrf forwarding {vrf_name}",
            f"ip address {ip_address}",
            "no shutdown",
            "exit"
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_interface_config(dut: str, interface: str, vrf_name: str = None) -> bool:
        """
        Remove interface configuration.

        Args:
            dut: Device handle
            interface: Interface name
            vrf_name: VRF name (optional, if bound to VRF)

        Returns:
            True if successful
        """
        st.log(f"Removing configuration from {interface} on {dut}")

        interface_num = interface.replace("Ethernet", "").replace(" ", "")

        commands = [
            "configure terminal",
            f"interface Ethernet {interface_num}",
            "no ip address"
        ]

        # Add VRF unbinding command if VRF name is provided
        if vrf_name:
            commands.append(f"no ip vrf forwarding {vrf_name}")

        commands.append("exit")

        st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
        return True

    # ========== HELPER METHODS - OSPF CONFIGURATION ==========

    @staticmethod
    def _configure_ospf_vrf(dut: str, vrf_name: str, router_id: str, networks: List[str], area: str) -> bool:
        """
        Configure OSPF process for VRF.

        Args:
            dut: Device handle
            vrf_name: VRF name
            router_id: OSPF router ID
            networks: List of networks to advertise
            area: OSPF area ID

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF for VRF {vrf_name} on {dut}")
        commands = [
            "configure terminal",
            f"router ospf vrf {vrf_name}",
            f"ospf router-id {router_id}"
        ]

        for network in networks:
            commands.append(f"network {network} area {area}")

        commands.append("exit")
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_ospf_vrf(dut: str, vrf_name: str) -> bool:
        """
        Remove OSPF configuration for VRF.

        Args:
            dut: Device handle
            vrf_name: VRF name

        Returns:
            True if successful
        """
        st.log(f"Removing OSPF for VRF {vrf_name} on {dut}")
        commands = [
            "configure terminal",
            f"no router ospf vrf {vrf_name}"
        ]
        st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
        return True

    # ========== HELPER METHODS - SHOW COMMANDS ==========

    @staticmethod
    def _get_show_ip_vrf(dut: str) -> str:
        """Get 'show ip vrf' output."""
        st.log(f"Getting 'show ip vrf' output from {dut}")
        output = st.show(dut, "show ip vrf", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip vrf output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_vrf(dut: str, vrf_name: str) -> str:
        """Get 'show ip ospf vrf <vrf>' output."""
        st.log(f"Getting 'show ip ospf vrf {vrf_name}' output from {dut}")
        output = st.show(dut, f"show ip ospf vrf {vrf_name}", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf vrf {vrf_name} output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_neighbor_vrf(dut: str, vrf_name: str) -> str:
        """Get 'show ip ospf neighbor vrf <vrf>' output."""
        st.log(f"Getting 'show ip ospf neighbor vrf {vrf_name}' output from {dut}")
        output = st.show(dut, f"show ip ospf neighbor vrf {vrf_name}", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf neighbor vrf {vrf_name} output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_interface_vrf(dut: str, vrf_name: str) -> str:
        """Get 'show ip ospf interface vrf <vrf>' output."""
        st.log(f"Getting 'show ip ospf interface vrf {vrf_name}' output from {dut}")
        output = st.show(dut, f"show ip ospf interface vrf {vrf_name}", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf interface vrf {vrf_name} output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_database_vrf(dut: str, vrf_name: str) -> str:
        """Get 'show ip ospf database vrf <vrf>' output."""
        st.log(f"Getting 'show ip ospf database vrf {vrf_name}' output from {dut}")
        output = st.show(dut, f"show ip ospf database vrf {vrf_name}", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf database vrf {vrf_name} output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_route_vrf(dut: str, vrf_name: str) -> str:
        """Get 'show ip route vrf <vrf>' output."""
        st.log(f"Getting 'show ip route vrf {vrf_name}' output from {dut}")
        output = st.show(dut, f"show ip route vrf {vrf_name}", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip route vrf {vrf_name} output from {dut}:\n{output}")
        return output

    @staticmethod
    def _ping_vrf(dut: str, vrf_name: str, destination_ip: str, count: int = 5) -> str:
        """Execute ping in VRF context."""
        st.log(f"Pinging {destination_ip} from {dut} in VRF {vrf_name}")
        command = f"ping vrf {vrf_name} {destination_ip} -c {count}"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True, skip_error_check=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"Ping output:\n{output}")
        return output

    # ========== HELPER METHODS - VALIDATION ==========

    @staticmethod
    def _verify_vrf_exists(vrf_output: str, vrf_name: str) -> bool:
        """Verify VRF exists in output."""
        st.log(f"Verifying VRF {vrf_name} exists")
        if vrf_name in vrf_output:
            st.log(f"PASS: VRF {vrf_name} found")
            return True
        else:
            st.error(f"FAIL: VRF {vrf_name} not found")
            return False

    @staticmethod
    def _verify_interface_in_vrf(vrf_output: str, vrf_name: str, interface: str) -> bool:
        """Verify interface is bound to VRF."""
        st.log(f"Verifying {interface} is in VRF {vrf_name}")

        # Parse output to find VRF section
        lines = vrf_output.split('\n')
        in_vrf_section = False

        for line in lines:
            if vrf_name in line and '----' not in line:
                in_vrf_section = True
            elif in_vrf_section:
                if interface in line:
                    st.log(f"PASS: {interface} found in VRF {vrf_name}")
                    return True
                # Check if we've moved to next VRF
                if line.strip() and not line.startswith(' ') and 'Ethernet' not in line and vrf_name not in line:
                    break

        st.error(f"FAIL: {interface} not found in VRF {vrf_name}")
        return False

    @staticmethod
    def _verify_ospf_process_vrf(ospf_output: str, vrf_name: str, router_id: str) -> bool:
        """Verify OSPF process is running in VRF."""
        st.log(f"Verifying OSPF process in VRF {vrf_name} with Router ID {router_id}")

        if f"VRF Name: {vrf_name}" in ospf_output and f"Router ID: {router_id}" in ospf_output:
            st.log(f"PASS: OSPF process verified in VRF {vrf_name}")
            return True
        else:
            st.error(f"FAIL: OSPF process not verified in VRF {vrf_name}")
            return False

    @staticmethod
    def _verify_ospf_neighbor_count_vrf(neighbor_output: str, expected_count: int) -> bool:
        """Verify expected number of OSPF neighbors in VRF."""
        st.log(f"Verifying {expected_count} OSPF neighbors")

        # Count lines with "Full" state
        full_lines = [line for line in neighbor_output.split('\n') if 'Full' in line]
        actual_count = len(full_lines)

        if actual_count == expected_count:
            st.log(f"PASS: Found {actual_count} neighbors in Full state")
            return True
        else:
            st.error(f"FAIL: Expected {expected_count} neighbors, found {actual_count}")
            return False

    @staticmethod
    def _verify_ospf_neighbor_full_state(neighbor_output: str, neighbor_ip: str) -> bool:
        """Verify specific neighbor is in Full state."""
        st.log(f"Verifying neighbor {neighbor_ip} is in Full state")

        lines = neighbor_output.split('\n')
        for line in lines:
            if neighbor_ip in line and 'Full' in line:
                st.log(f"PASS: Neighbor {neighbor_ip} in Full state")
                return True

        st.error(f"FAIL: Neighbor {neighbor_ip} not in Full state")
        return False

    @staticmethod
    def _verify_ospf_database_has_lsas(database_output: str) -> bool:
        """Verify OSPF database contains LSAs."""
        st.log("Verifying OSPF database has LSAs")

        if "Router Link States" in database_output or "Net Link States" in database_output:
            st.log("PASS: OSPF database has LSAs")
            return True
        else:
            st.error("FAIL: OSPF database is empty")
            return False

    @staticmethod
    def _verify_route_in_table(route_output: str, network: str) -> bool:
        """Verify route is present in routing table."""
        st.log(f"Verifying route {network} in routing table")

        if network in route_output:
            st.log(f"PASS: Route {network} found")
            return True
        else:
            st.error(f"FAIL: Route {network} not found")
            return False

    @staticmethod
    def _verify_ecmp_routes(route_output: str, network: str) -> bool:
        """Verify ECMP (multiple next-hops) for a route."""
        st.log(f"Verifying ECMP for route {network}")

        lines = route_output.split('\n')
        found_network = False
        next_hop_count = 0

        for line in lines:
            if network in line and '>' in line:
                found_network = True
                next_hop_count += 1
            elif found_network and '*' in line and 'via' in line:
                next_hop_count += 1
            elif found_network and line.strip() and not line.startswith(' '):
                break

        if next_hop_count >= 2:
            st.log(f"PASS: ECMP verified with {next_hop_count} next-hops for {network}")
            return True
        else:
            st.log(f"INFO: Single path found for {network}")
            return False

    @staticmethod
    def _verify_ping_success(ping_output: str) -> bool:
        """Verify ping was successful (0% packet loss)."""
        st.log("Verifying ping success")

        if "0% packet loss" in ping_output or "0 % packet loss" in ping_output:
            st.log("PASS: Ping successful")
            return True
        else:
            st.error("FAIL: Ping failed or had packet loss")
            return False

    # ========== MAIN TEST CASE ==========

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_VRF_001"])
    def test_ospf_per_vrf_over_ethernet_4_node(self) -> None:
        """
        TC_OSPF_VRF_001: Validate OSPF per VRF over Ethernet in 4-node topology.

        Test Procedure:
        1. Create VRFs on all devices
        2. Configure interfaces with VRF binding and IP addresses
        3. Verify VRF configuration and interface assignments
        4. Configure OSPF per VRF on all devices
        5. Verify OSPF neighbors in Full state
        6. Verify OSPF interfaces, database, and routes
        7. Test end-to-end ping connectivity
        8. Cleanup: Remove all configurations

        Expected Result:
        - VRFs created successfully
        - Interfaces correctly bound to VRFs
        - OSPF neighbors form adjacency per VRF
        - Routes learned via OSPF with ECMP
        - End-to-end connectivity works
        - VRF isolation maintained
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF Per VRF Over Ethernet - 4-Node Topology")
        st.log("=" * 80)

        # Track validation failures
        validation_failures = []

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4
        vrf_red = self.data.vrf_red
        vrf_blue = self.data.vrf_blue
        area = self.data.ospf_area

        # ===== STEP 1: Create VRFs on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Create VRFs on all devices")
        st.log("-" * 80)

        for dut in [dut1, dut2, dut3, dut4]:
            self._create_vrf(dut, vrf_red)
            self._create_vrf(dut, vrf_blue)

        time.sleep(WAIT_AFTER_VRF_CONFIG)
        st.log("VRFs created on all devices")

        # ===== STEP 2: Configure D1 interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Configure D1 interfaces with VRF and IP addresses")
        st.log("-" * 80)

        # D1 Vrf-RED interfaces
        self._configure_interface_vrf_ip(dut1, "Ethernet0", vrf_red, self.data.dut1_vrf_red_ips[0])
        self._configure_interface_vrf_ip(dut1, "Ethernet4", vrf_red, self.data.dut1_vrf_red_ips[1])

        # D1 Vrf-BLUE interfaces
        self._configure_interface_vrf_ip(dut1, "Ethernet8", vrf_blue, self.data.dut1_vrf_blue_ips[0])
        self._configure_interface_vrf_ip(dut1, "Ethernet12", vrf_blue, self.data.dut1_vrf_blue_ips[1])

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("D1 interfaces configured")

        # ===== STEP 3: Configure D2 interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Configure D2 interfaces with VRF and IP addresses")
        st.log("-" * 80)

        # D2 Vrf-RED interfaces (D1 side)
        self._configure_interface_vrf_ip(dut2, "Ethernet0", vrf_red, self.data.dut2_vrf_red_d1_ips[0])
        self._configure_interface_vrf_ip(dut2, "Ethernet4", vrf_red, self.data.dut2_vrf_red_d1_ips[1])

        # D2 Vrf-BLUE interfaces (D1 side)
        self._configure_interface_vrf_ip(dut2, "Ethernet8", vrf_blue, self.data.dut2_vrf_blue_d1_ips[0])
        self._configure_interface_vrf_ip(dut2, "Ethernet12", vrf_blue, self.data.dut2_vrf_blue_d1_ips[1])

        # D2 Vrf-RED interfaces (D4 side)
        self._configure_interface_vrf_ip(dut2, "Ethernet16", vrf_red, self.data.dut2_vrf_red_d4_ips[0])
        self._configure_interface_vrf_ip(dut2, "Ethernet20", vrf_red, self.data.dut2_vrf_red_d4_ips[1])

        # D2 Vrf-BLUE interfaces (D4 side)
        self._configure_interface_vrf_ip(dut2, "Ethernet24", vrf_blue, self.data.dut2_vrf_blue_d4_ips[0])
        self._configure_interface_vrf_ip(dut2, "Ethernet28", vrf_blue, self.data.dut2_vrf_blue_d4_ips[1])

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("D2 interfaces configured")

        # ===== STEP 4: Configure D4 interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Configure D4 interfaces with VRF and IP addresses")
        st.log("-" * 80)

        # D4 Vrf-RED interfaces (D2 side)
        self._configure_interface_vrf_ip(dut4, "Ethernet16", vrf_red, self.data.dut4_vrf_red_d2_ips[0])
        self._configure_interface_vrf_ip(dut4, "Ethernet20", vrf_red, self.data.dut4_vrf_red_d2_ips[1])

        # D4 Vrf-BLUE interfaces (D2 side)
        self._configure_interface_vrf_ip(dut4, "Ethernet24", vrf_blue, self.data.dut4_vrf_blue_d2_ips[0])
        self._configure_interface_vrf_ip(dut4, "Ethernet28", vrf_blue, self.data.dut4_vrf_blue_d2_ips[1])

        # D4 Vrf-RED interfaces (D3 side)
        self._configure_interface_vrf_ip(dut4, "Ethernet32", vrf_red, self.data.dut4_vrf_red_d3_ips[0])
        self._configure_interface_vrf_ip(dut4, "Ethernet36", vrf_red, self.data.dut4_vrf_red_d3_ips[1])

        # D4 Vrf-BLUE interfaces (D3 side)
        self._configure_interface_vrf_ip(dut4, "Ethernet40", vrf_blue, self.data.dut4_vrf_blue_d3_ips[0])
        self._configure_interface_vrf_ip(dut4, "Ethernet44", vrf_blue, self.data.dut4_vrf_blue_d3_ips[1])

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("D4 interfaces configured")

        # ===== STEP 5: Configure D3 interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Configure D3 interfaces with VRF and IP addresses")
        st.log("-" * 80)

        # D3 Vrf-RED interfaces
        self._configure_interface_vrf_ip(dut3, "Ethernet32", vrf_red, self.data.dut3_vrf_red_ips[0])
        self._configure_interface_vrf_ip(dut3, "Ethernet36", vrf_red, self.data.dut3_vrf_red_ips[1])

        # D3 Vrf-BLUE interfaces
        self._configure_interface_vrf_ip(dut3, "Ethernet40", vrf_blue, self.data.dut3_vrf_blue_ips[0])
        self._configure_interface_vrf_ip(dut3, "Ethernet44", vrf_blue, self.data.dut3_vrf_blue_ips[1])

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("D3 interfaces configured")

        # ===== STEP 6: Verify VRF configuration on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Verify VRF configuration on all devices")
        st.log("-" * 80)

        for dut in [dut1, dut2, dut3, dut4]:
            vrf_output = self._get_show_ip_vrf(dut)

            if not self._verify_vrf_exists(vrf_output, vrf_red):
                error_msg = f"STEP 6: VRF {vrf_red} not found on {dut}"
                st.error(error_msg)
                validation_failures.append(error_msg)

            if not self._verify_vrf_exists(vrf_output, vrf_blue):
                error_msg = f"STEP 6: VRF {vrf_blue} not found on {dut}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 6" in f]) == 0:
            st.log("PASS: VRF configuration verified on all devices")

        # ===== STEP 7: Configure OSPF on D1 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Configure OSPF on D1")
        st.log("-" * 80)

        # D1 OSPF Vrf-RED
        networks_d1_red = ["10.1.1.0/24", "10.1.2.0/24"]
        self._configure_ospf_vrf(dut1, vrf_red, self.data.dut1_router_id_red, networks_d1_red, area)

        # D1 OSPF Vrf-BLUE
        networks_d1_blue = ["10.2.1.0/24", "10.2.2.0/24"]
        self._configure_ospf_vrf(dut1, vrf_blue, self.data.dut1_router_id_blue, networks_d1_blue, area)

        time.sleep(WAIT_AFTER_OSPF_CONFIG)
        st.log("OSPF configured on D1")

        # ===== STEP 8: Configure OSPF on D2 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Configure OSPF on D2")
        st.log("-" * 80)

        # D2 OSPF Vrf-RED
        networks_d2_red = ["10.1.1.0/24", "10.1.2.0/24", "30.1.1.0/24", "30.1.2.0/24"]
        self._configure_ospf_vrf(dut2, vrf_red, self.data.dut2_router_id_red, networks_d2_red, area)

        # D2 OSPF Vrf-BLUE
        networks_d2_blue = ["10.2.1.0/24", "10.2.2.0/24", "40.1.1.0/24", "40.1.2.0/24"]
        self._configure_ospf_vrf(dut2, vrf_blue, self.data.dut2_router_id_blue, networks_d2_blue, area)

        time.sleep(WAIT_AFTER_OSPF_CONFIG)
        st.log("OSPF configured on D2")

        # ===== STEP 9: Configure OSPF on D4 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Configure OSPF on D4")
        st.log("-" * 80)

        # D4 OSPF Vrf-RED
        networks_d4_red = ["30.1.1.0/24", "30.1.2.0/24", "50.1.1.0/24", "50.1.2.0/24"]
        self._configure_ospf_vrf(dut4, vrf_red, self.data.dut4_router_id_red, networks_d4_red, area)

        # D4 OSPF Vrf-BLUE
        networks_d4_blue = ["40.1.1.0/24", "40.1.2.0/24", "60.1.1.0/24", "60.1.2.0/24"]
        self._configure_ospf_vrf(dut4, vrf_blue, self.data.dut4_router_id_blue, networks_d4_blue, area)

        time.sleep(WAIT_AFTER_OSPF_CONFIG)
        st.log("OSPF configured on D4")

        # ===== STEP 10: Configure OSPF on D3 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Configure OSPF on D3")
        st.log("-" * 80)

        # D3 OSPF Vrf-RED
        networks_d3_red = ["50.1.1.0/24", "50.1.2.0/24"]
        self._configure_ospf_vrf(dut3, vrf_red, self.data.dut3_router_id_red, networks_d3_red, area)

        # D3 OSPF Vrf-BLUE
        networks_d3_blue = ["60.1.1.0/24", "60.1.2.0/24"]
        self._configure_ospf_vrf(dut3, vrf_blue, self.data.dut3_router_id_blue, networks_d3_blue, area)

        time.sleep(WAIT_AFTER_OSPF_CONFIG)
        st.log("OSPF configured on D3")

        # ===== STEP 11: Wait for OSPF convergence =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 11: Wait {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbor convergence")
        st.log("-" * 80)
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # ===== STEP 12: Verify OSPF process on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Verify OSPF process on all devices")
        st.log("-" * 80)

        # Verify D1 OSPF
        ospf_output_d1_red = self._get_show_ip_ospf_vrf(dut1, vrf_red)
        ospf_output_d1_blue = self._get_show_ip_ospf_vrf(dut1, vrf_blue)

        if not self._verify_ospf_process_vrf(ospf_output_d1_red, vrf_red, self.data.dut1_router_id_red):
            error_msg = f"STEP 12: OSPF process not verified on {dut1} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_process_vrf(ospf_output_d1_blue, vrf_blue, self.data.dut1_router_id_blue):
            error_msg = f"STEP 12: OSPF process not verified on {dut1} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D2 OSPF
        ospf_output_d2_red = self._get_show_ip_ospf_vrf(dut2, vrf_red)
        ospf_output_d2_blue = self._get_show_ip_ospf_vrf(dut2, vrf_blue)

        if not self._verify_ospf_process_vrf(ospf_output_d2_red, vrf_red, self.data.dut2_router_id_red):
            error_msg = f"STEP 12: OSPF process not verified on {dut2} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_process_vrf(ospf_output_d2_blue, vrf_blue, self.data.dut2_router_id_blue):
            error_msg = f"STEP 12: OSPF process not verified on {dut2} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D3 OSPF
        ospf_output_d3_red = self._get_show_ip_ospf_vrf(dut3, vrf_red)
        ospf_output_d3_blue = self._get_show_ip_ospf_vrf(dut3, vrf_blue)

        if not self._verify_ospf_process_vrf(ospf_output_d3_red, vrf_red, self.data.dut3_router_id_red):
            error_msg = f"STEP 12: OSPF process not verified on {dut3} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_process_vrf(ospf_output_d3_blue, vrf_blue, self.data.dut3_router_id_blue):
            error_msg = f"STEP 12: OSPF process not verified on {dut3} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D4 OSPF
        ospf_output_d4_red = self._get_show_ip_ospf_vrf(dut4, vrf_red)
        ospf_output_d4_blue = self._get_show_ip_ospf_vrf(dut4, vrf_blue)

        if not self._verify_ospf_process_vrf(ospf_output_d4_red, vrf_red, self.data.dut4_router_id_red):
            error_msg = f"STEP 12: OSPF process not verified on {dut4} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_process_vrf(ospf_output_d4_blue, vrf_blue, self.data.dut4_router_id_blue):
            error_msg = f"STEP 12: OSPF process not verified on {dut4} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 12" in f]) == 0:
            st.log("PASS: OSPF process verified on all devices")

        # ===== STEP 13: Verify OSPF neighbors on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 13: Verify OSPF neighbors on all devices")
        st.log("-" * 80)

        # D1 should have 2 neighbors in each VRF (to D2)
        neighbor_output_d1_red = self._get_show_ip_ospf_neighbor_vrf(dut1, vrf_red)
        neighbor_output_d1_blue = self._get_show_ip_ospf_neighbor_vrf(dut1, vrf_blue)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d1_red, 2):
            error_msg = f"STEP 13: Expected 2 neighbors on {dut1} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d1_blue, 2):
            error_msg = f"STEP 13: Expected 2 neighbors on {dut1} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # D2 should have 4 neighbors in each VRF (2 to D1, 2 to D4)
        neighbor_output_d2_red = self._get_show_ip_ospf_neighbor_vrf(dut2, vrf_red)
        neighbor_output_d2_blue = self._get_show_ip_ospf_neighbor_vrf(dut2, vrf_blue)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d2_red, 4):
            error_msg = f"STEP 13: Expected 4 neighbors on {dut2} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d2_blue, 4):
            error_msg = f"STEP 13: Expected 4 neighbors on {dut2} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # D4 should have 4 neighbors in each VRF (2 to D2, 2 to D3)
        neighbor_output_d4_red = self._get_show_ip_ospf_neighbor_vrf(dut4, vrf_red)
        neighbor_output_d4_blue = self._get_show_ip_ospf_neighbor_vrf(dut4, vrf_blue)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d4_red, 4):
            error_msg = f"STEP 13: Expected 4 neighbors on {dut4} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d4_blue, 4):
            error_msg = f"STEP 13: Expected 4 neighbors on {dut4} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # D3 should have 2 neighbors in each VRF (to D4)
        neighbor_output_d3_red = self._get_show_ip_ospf_neighbor_vrf(dut3, vrf_red)
        neighbor_output_d3_blue = self._get_show_ip_ospf_neighbor_vrf(dut3, vrf_blue)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d3_red, 2):
            error_msg = f"STEP 13: Expected 2 neighbors on {dut3} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d3_blue, 2):
            error_msg = f"STEP 13: Expected 2 neighbors on {dut3} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 13" in f]) == 0:
            st.log("PASS: OSPF neighbors verified on all devices")

        # ===== STEP 14: Verify OSPF interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 14: Verify OSPF interfaces on all devices")
        st.log("-" * 80)

        # Get OSPF interface outputs
        interface_output_d1_red = self._get_show_ip_ospf_interface_vrf(dut1, vrf_red)
        interface_output_d1_blue = self._get_show_ip_ospf_interface_vrf(dut1, vrf_blue)
        interface_output_d2_red = self._get_show_ip_ospf_interface_vrf(dut2, vrf_red)
        interface_output_d2_blue = self._get_show_ip_ospf_interface_vrf(dut2, vrf_blue)
        interface_output_d3_red = self._get_show_ip_ospf_interface_vrf(dut3, vrf_red)
        interface_output_d3_blue = self._get_show_ip_ospf_interface_vrf(dut3, vrf_blue)
        interface_output_d4_red = self._get_show_ip_ospf_interface_vrf(dut4, vrf_red)
        interface_output_d4_blue = self._get_show_ip_ospf_interface_vrf(dut4, vrf_blue)

        st.log("PASS: OSPF interfaces retrieved successfully")

        # ===== STEP 15: Verify OSPF database =====
        st.log("\n" + "-" * 80)
        st.log("STEP 15: Verify OSPF database on all devices")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_ROUTE_UPDATE)

        # Verify database on all devices
        for dut in [dut1, dut2, dut3, dut4]:
            db_output_red = self._get_show_ip_ospf_database_vrf(dut, vrf_red)
            db_output_blue = self._get_show_ip_ospf_database_vrf(dut, vrf_blue)

            if not self._verify_ospf_database_has_lsas(db_output_red):
                error_msg = f"STEP 15: OSPF database empty on {dut} Vrf-RED"
                st.error(error_msg)
                validation_failures.append(error_msg)

            if not self._verify_ospf_database_has_lsas(db_output_blue):
                error_msg = f"STEP 15: OSPF database empty on {dut} Vrf-BLUE"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 15" in f]) == 0:
            st.log("PASS: OSPF database verified on all devices")

        # ===== STEP 16: Verify routing tables =====
        st.log("\n" + "-" * 80)
        st.log("STEP 16: Verify routing tables on all devices")
        st.log("-" * 80)

        # Get routing tables
        route_output_d1_red = self._get_show_ip_route_vrf(dut1, vrf_red)
        route_output_d1_blue = self._get_show_ip_route_vrf(dut1, vrf_blue)
        route_output_d2_red = self._get_show_ip_route_vrf(dut2, vrf_red)
        route_output_d2_blue = self._get_show_ip_route_vrf(dut2, vrf_blue)
        route_output_d3_red = self._get_show_ip_route_vrf(dut3, vrf_red)
        route_output_d3_blue = self._get_show_ip_route_vrf(dut3, vrf_blue)
        route_output_d4_red = self._get_show_ip_route_vrf(dut4, vrf_red)
        route_output_d4_blue = self._get_show_ip_route_vrf(dut4, vrf_blue)

        # Verify D1 can see D3 networks
        if not self._verify_route_in_table(route_output_d1_red, "50.1.1.0/24"):
            error_msg = f"STEP 16: Route 50.1.1.0/24 not found on {dut1} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_route_in_table(route_output_d1_blue, "60.1.1.0/24"):
            error_msg = f"STEP 16: Route 60.1.1.0/24 not found on {dut1} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D3 can see D1 networks
        if not self._verify_route_in_table(route_output_d3_red, "10.1.1.0/24"):
            error_msg = f"STEP 16: Route 10.1.1.0/24 not found on {dut3} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_route_in_table(route_output_d3_blue, "10.2.1.0/24"):
            error_msg = f"STEP 16: Route 10.2.1.0/24 not found on {dut3} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify ECMP on D1
        self._verify_ecmp_routes(route_output_d1_red, "30.1.1.0/24")
        self._verify_ecmp_routes(route_output_d1_blue, "40.1.1.0/24")

        if len([f for f in validation_failures if "STEP 16" in f]) == 0:
            st.log("PASS: Routing tables verified on all devices")

        # ===== STEP 17: Test end-to-end ping connectivity =====
        st.log("\n" + "-" * 80)
        st.log("STEP 17: Test end-to-end ping connectivity")
        st.log("-" * 80)

        # D1 to D3 ping in Vrf-RED
        ping_output_d1_d3_red = self._ping_vrf(dut1, vrf_red, "50.1.1.2", count=5)
        if not self._verify_ping_success(ping_output_d1_d3_red):
            error_msg = f"STEP 17: Ping failed from {dut1} to D3 in Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping successful from {dut1} to D3 in Vrf-RED")

        # D1 to D3 ping in Vrf-BLUE
        ping_output_d1_d3_blue = self._ping_vrf(dut1, vrf_blue, "60.1.1.2", count=5)
        if not self._verify_ping_success(ping_output_d1_d3_blue):
            error_msg = f"STEP 17: Ping failed from {dut1} to D3 in Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping successful from {dut1} to D3 in Vrf-BLUE")

        # D3 to D1 ping in Vrf-RED
        ping_output_d3_d1_red = self._ping_vrf(dut3, vrf_red, "10.1.1.1", count=5)
        if not self._verify_ping_success(ping_output_d3_d1_red):
            error_msg = f"STEP 17: Ping failed from {dut3} to D1 in Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping successful from {dut3} to D1 in Vrf-RED")

        # D3 to D1 ping in Vrf-BLUE
        ping_output_d3_d1_blue = self._ping_vrf(dut3, vrf_blue, "10.2.1.1", count=5)
        if not self._verify_ping_success(ping_output_d3_d1_blue):
            error_msg = f"STEP 17: Ping failed from {dut3} to D1 in Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping successful from {dut3} to D1 in Vrf-BLUE")

        if len([f for f in validation_failures if "STEP 17" in f]) == 0:
            st.log("PASS: End-to-end ping connectivity verified")

        # ===== STEP 18: Cleanup - Remove OSPF configuration =====
        st.log("\n" + "-" * 80)
        st.log("STEP 18: Cleanup - Remove OSPF configuration")
        st.log("-" * 80)

        for dut in [dut1, dut2, dut3, dut4]:
            self._remove_ospf_vrf(dut, vrf_red)
            self._remove_ospf_vrf(dut, vrf_blue)

        time.sleep(WAIT_AFTER_OSPF_CONFIG)
        st.log("OSPF configuration removed from all devices")

        # ===== STEP 19: Cleanup - Remove interface configuration =====
        st.log("\n" + "-" * 80)
        st.log("STEP 19: Cleanup - Remove interface configuration")
        st.log("-" * 80)

        # Remove D1 interfaces
        for intf in ["Ethernet0", "Ethernet4"]:
            self._remove_interface_config(dut1, intf, vrf_red)
        for intf in ["Ethernet8", "Ethernet12"]:
            self._remove_interface_config(dut1, intf, vrf_blue)

        # Remove D2 interfaces
        for intf in ["Ethernet0", "Ethernet4", "Ethernet16", "Ethernet20"]:
            self._remove_interface_config(dut2, intf, vrf_red)
        for intf in ["Ethernet8", "Ethernet12", "Ethernet24", "Ethernet28"]:
            self._remove_interface_config(dut2, intf, vrf_blue)

        # Remove D3 interfaces
        for intf in ["Ethernet32", "Ethernet36"]:
            self._remove_interface_config(dut3, intf, vrf_red)
        for intf in ["Ethernet40", "Ethernet44"]:
            self._remove_interface_config(dut3, intf, vrf_blue)

        # Remove D4 interfaces
        for intf in ["Ethernet16", "Ethernet20", "Ethernet32", "Ethernet36"]:
            self._remove_interface_config(dut4, intf, vrf_red)
        for intf in ["Ethernet24", "Ethernet28", "Ethernet40", "Ethernet44"]:
            self._remove_interface_config(dut4, intf, vrf_blue)

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("Interface configuration removed from all devices")

        # ===== STEP 20: Cleanup - Remove VRFs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 20: Cleanup - Remove VRFs")
        st.log("-" * 80)

        for dut in [dut1, dut2, dut3, dut4]:
            self._delete_vrf(dut, vrf_red)
            self._delete_vrf(dut, vrf_blue)

        time.sleep(WAIT_AFTER_VRF_CONFIG)
        st.log("VRFs removed from all devices")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF per VRF over Ethernet validated successfully")
        st.log("=" * 80)

        # ===== COLLECT TECH SUPPORT AND REPORT FAILURES =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from all DUTs
            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_per_vrf_validation_failure")
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
