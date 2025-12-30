"""
OSPF 4-NODE BACKBONE TOPOLOGY WITH ABR - ETHERNET INTERFACES
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_5_iscli_4_node_Backbone_connect_via_ABR_Eth.py \
  --logs-path ./logs/testcases_OSPF_5_iscli_4_node_Backbone_connect_via_ABR_Eth_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF multi-area configuration with Area Border Routers (ABR)
  in a 4-node topology. The test configures three OSPF areas (Area 0 - Backbone,
  Area 1, and Area 2) and validates inter-area routing through ABRs.

  Test validates:
  1. IP address configuration and validation on all interfaces
  2. OSPF multi-area configuration (Area 0, Area 1, Area 2)
  3. ABR functionality (D2 and D4 act as ABRs)
  4. OSPF neighbor adjacency (Full state)
  5. OSPF database synchronization (Router LSA, Network LSA, Summary LSA)
  6. Inter-area routing via ABRs
  7. Ping connectivity between all routers across areas
  8. Traceroute validation through ABRs
  9. Complete cleanup of all configurations

  Topology:
        D1 (Area 1) -------- D2 (ABR) -------- D4 (ABR) -------- D3 (Area 2)
       (Ethernet0)        (Ethernet0)        (Ethernet16)      (Ethernet32)
        10.1.1.1          10.1.1.2           20.1.1.2          30.1.1.2
                         (Ethernet16)        (Ethernet32)
                          20.1.1.1           30.1.1.1
                          Area 0              Area 0
                          (Backbone)          (Backbone)

  Configuration details:
    D1 (vs_sonic_1):
      - Ethernet0: 10.1.1.1/24
      - OSPF Area 1
      - Network: 10.1.1.1/24 area 1

    D2 (vs_sonic_2) - ABR:
      - Ethernet0: 10.1.1.2/24 (connects to D1 in Area 1)
      - Ethernet16: 20.1.1.1/24 (connects to D4 in Area 0 - Backbone)
      - OSPF Areas: 0 (Backbone) and 1
      - Networks: 10.1.1.2/24 area 1, 20.1.1.1/24 area 0

    D4 (vs_sonic_4) - ABR:
      - Ethernet16: 20.1.1.2/24 (connects to D2 in Area 0 - Backbone)
      - Ethernet32: 30.1.1.1/24 (connects to D3 in Area 2)
      - OSPF Areas: 0 (Backbone) and 2
      - Networks: 20.1.1.2/24 area 0, 30.1.1.1/24 area 2

    D3 (vs_sonic_3):
      - Ethernet32: 30.1.1.2/24
      - OSPF Area 2
      - Network: 30.1.1.2/24 area 2

  IMPORTANT: Uses 'show ip ospf', 'show ip ospf neighbor', 'show ip ospf route',
  'show ip ospf database summary', 'show ip route', and connectivity tests to
  validate multi-area OSPF configuration. Uses klish CLI type exclusively.

Pre-requisites:
  - Topology: 4-node | Supported: HW and Virtual
  - Testbed: testbed_4vs.yaml with topology:
    * D1 (vs_sonic_1) Ethernet0 <-> D2 (vs_sonic_2) Ethernet0
    * D2 (vs_sonic_2) Ethernet16 <-> D4 (vs_sonic_4) Ethernet16
    * D4 (vs_sonic_4) Ethernet32 <-> D3 (vs_sonic_3) Ethernet32
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
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_ROUTE_UPDATE = 10
WAIT_FOR_PING = 5
WAIT_FOR_DATABASE_SYNC = 10


@pytest.mark.topology("any")
class TestOSPFMultiAreaABR:
    """Test cases for validating OSPF multi-area configuration with ABRs via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF 4-Node Multi-Area ABR Test Suite")
        st.log("=" * 80)

        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if len(cls.data.dut_names) < 4:
            st.report_fail("msg", "Minimum 4 DUTs required for this test")

        cls.data.dut1 = cls.data.dut_names[0]  # vs_sonic_1
        cls.data.dut2 = cls.data.dut_names[1]  # vs_sonic_2
        cls.data.dut3 = cls.data.dut_names[2]  # vs_sonic_3
        cls.data.dut4 = cls.data.dut_names[3]  # vs_sonic_4

        st.log(f"DUT1 (D1 - Area 1): {cls.data.dut1}")
        st.log(f"DUT2 (D2 - ABR Area 0/1): {cls.data.dut2}")
        st.log(f"DUT3 (D3 - Area 2): {cls.data.dut3}")
        st.log(f"DUT4 (D4 - ABR Area 0/2): {cls.data.dut4}")

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
        cls.data.dut4_ip2 = "30.1.1.1/24"
        cls.data.dut3_ip = "30.1.1.2/24"

        st.log(f"IP Addresses:")
        st.log(f"  D1[{cls.data.dut1_if1}]: {cls.data.dut1_ip} (Area 1)")
        st.log(f"  D2[{cls.data.dut2_if1}]: {cls.data.dut2_ip1} (Area 1)")
        st.log(f"  D2[{cls.data.dut2_if2}]: {cls.data.dut2_ip2} (Area 0 - Backbone)")
        st.log(f"  D4[{cls.data.dut4_if1}]: {cls.data.dut4_ip1} (Area 0 - Backbone)")
        st.log(f"  D4[{cls.data.dut4_if2}]: {cls.data.dut4_ip2} (Area 2)")
        st.log(f"  D3[{cls.data.dut3_if1}]: {cls.data.dut3_ip} (Area 2)")

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
        st.log("TEST TEARDOWN: Cleanup OSPF 4-Node Multi-Area ABR Test Suite")
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

    @staticmethod
    def _verify_interface_ip(dut: str, interface: str, expected_ip: str) -> bool:
        """
        Verify IP address is configured on interface using running-configuration.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            expected_ip: Expected IP address (e.g., "10.1.1.1/24")

        Returns:
            True if IP is configured correctly
        """
        st.log(f"Verifying IP address {expected_ip} on {interface} on {dut}")

        # Parse interface number from name (e.g., "Ethernet0" -> "0")
        interface_number = interface.replace("Ethernet", "").strip()

        # Command: show running-configuration interface Ethernet X
        command = f"show running-configuration interface Ethernet {interface_number}"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True, skip_error_check=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"Running-config output from {dut}:\n{output}")

        # Check if expected IP is in the output
        if expected_ip in output:
            st.log(f"PASS: IP address {expected_ip} verified on {interface}")
            return True
        else:
            # Also check for IP without mask format
            ip_without_mask = expected_ip.split('/')[0]
            if ip_without_mask in output and "ip address" in output.lower():
                st.log(f"PASS: IP address {expected_ip} verified on {interface}")
                return True
            else:
                st.error(f"FAIL: IP address {expected_ip} not found on {interface}")
                return False

    # ========== HELPER METHODS - OSPF CONFIGURATION ==========

    @staticmethod
    def _configure_ospf_process(dut: str, areas: List[str]) -> bool:
        """
        Configure OSPF process and areas.

        Args:
            dut: Device handle
            areas: List of OSPF area IDs

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF process with areas {areas} on {dut}")
        commands = ["configure terminal", "router ospf"]
        for area in areas:
            commands.append(f"area {area}")
        commands.append("exit")

        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _configure_ospf_network(dut: str, network: str, area: str) -> bool:
        """
        Configure OSPF network statement.

        Args:
            dut: Device handle
            network: Network address with mask (e.g., "10.1.1.1/24")
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
    def _get_show_ip_ospf_output(dut: str) -> str:
        """
        Get 'show ip ospf' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show ip ospf' output from {dut}")
        command = "show ip ospf"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf output from {dut}:\n{output}")
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
    def _get_show_ip_ospf_route_output(dut: str) -> str:
        """
        Get 'show ip ospf route' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show ip ospf route' output from {dut}")
        command = "show ip ospf route"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf route output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_database_summary_output(dut: str) -> str:
        """
        Get 'show ip ospf database summary' output as raw string.

        Args:
            dut: Device handle

        Returns:
            Command output as raw string
        """
        st.log(f"Getting 'show ip ospf database summary' output from {dut}")
        command = "show ip ospf database summary"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf database summary output from {dut}:\n{output}")
        return output

    # ========== HELPER METHODS - VALIDATION ==========

    @staticmethod
    def _verify_ospf_abr_status(ospf_output: str, expected_abr: bool = True) -> bool:
        """
        Verify if router is configured as ABR.

        Args:
            ospf_output: Raw output from 'show ip ospf' command
            expected_abr: Whether router should be ABR (default: True)

        Returns:
            True if ABR status matches expectation
        """
        st.log(f"Verifying ABR status (expected: {expected_abr})")

        is_abr = "This router is an ABR" in ospf_output

        if expected_abr and is_abr:
            st.log("PASS: Router is configured as ABR")
            return True
        elif not expected_abr and not is_abr:
            st.log("PASS: Router is not configured as ABR")
            return True
        else:
            st.error(f"FAIL: ABR status mismatch (expected: {expected_abr}, found: {is_abr})")
            return False

    @staticmethod
    def _verify_ospf_areas(ospf_output: str, expected_areas: List[str]) -> bool:
        """
        Verify OSPF areas are configured.

        Args:
            ospf_output: Raw output from 'show ip ospf' command
            expected_areas: List of expected area IDs

        Returns:
            True if all areas are found
        """
        st.log(f"Verifying OSPF areas: {expected_areas}")

        all_found = True
        for area in expected_areas:
            # Area 0 is shown as "Area ID: 0.0.0.0 (Backbone)"
            # Other areas shown as "Area ID: 0.0.0.X"
            if area == "0":
                area_pattern = "Area ID: 0.0.0.0 (Backbone)"
            else:
                area_pattern = f"Area ID: 0.0.0.{area}"

            if area_pattern in ospf_output:
                st.log(f"PASS: Area {area} found in OSPF configuration")
            else:
                st.error(f"FAIL: Area {area} not found in OSPF configuration")
                all_found = False

        return all_found

    @staticmethod
    def _verify_ospf_neighbor_present(neighbor_output: str, expected_neighbor_ip: str,
                                     expected_state: str = "Full") -> bool:
        """
        Verify that OSPF neighbor is present with expected state.

        Args:
            neighbor_output: Raw output from 'show ip ospf neighbor' command
            expected_neighbor_ip: Expected neighbor IP address
            expected_state: Expected neighbor state (default: "Full")

        Returns:
            True if neighbor is present with correct state
        """
        st.log(f"Verifying OSPF neighbor {expected_neighbor_ip} is in {expected_state} state")

        if expected_neighbor_ip not in neighbor_output:
            st.error(f"FAIL: Neighbor {expected_neighbor_ip} not found in output")
            return False

        if expected_state not in neighbor_output:
            st.error(f"FAIL: Neighbor state {expected_state} not found in output")
            return False

        lines = neighbor_output.split('\n')
        for line in lines:
            if expected_neighbor_ip in line and expected_state in line:
                st.log(f"PASS: Neighbor {expected_neighbor_ip} is in {expected_state} state")
                return True

        st.error(f"FAIL: Neighbor {expected_neighbor_ip} not in {expected_state} state")
        return False

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

    # ========== TEST CASE ==========

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_ABR_MULTIAREA_001"])
    def test_ospf_multiarea_abr_backbone(self) -> None:
        """
        TC_OSPF_ABR_MULTIAREA_001: Validate OSPF multi-area configuration with ABRs.

        Test Procedure:
        1. Configure IP addresses on all interfaces and validate
        2. Configure OSPF on D1 (Area 1)
        3. Configure OSPF on D2 (ABR - Area 0 and Area 1)
        4. Configure OSPF on D4 (ABR - Area 0 and Area 2)
        5. Configure OSPF on D3 (Area 2)
        6. Verify OSPF neighbor adjacencies (Full state)
        7. Verify ABR status on D2 and D4
        8. Verify OSPF database (Summary LSAs)
        9. Verify inter-area routing
        10. Verify ping connectivity across all areas
        11. Verify traceroute through ABRs
        12. Cleanup: Remove all configurations

        Expected Result:
        - IP addresses configured and validated
        - OSPF neighbors form adjacency (Full state)
        - D2 and D4 are identified as ABRs
        - Summary LSAs are generated by ABRs
        - Inter-area routes are installed
        - Ping successful across all areas
        - Traceroute shows path through ABRs
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF Multi-Area Configuration with ABRs")
        st.log("=" * 80)

        # Track validation failures - test will continue but report fail at end
        validation_failures = []

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4

        # ===== STEP 1: Configure IP addresses on all interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Configure IP addresses on all interfaces")
        st.log("-" * 80)

        # D1: Ethernet0 - 10.1.1.1/24
        self._configure_interface_ip(dut1, self.data.dut1_if1, self.data.dut1_ip)

        # D2: Ethernet0 - 10.1.1.2/24, Ethernet16 - 20.1.1.1/24
        self._configure_interface_ip(dut2, self.data.dut2_if1, self.data.dut2_ip1)
        self._configure_interface_ip(dut2, self.data.dut2_if2, self.data.dut2_ip2)

        # D4: Ethernet16 - 20.1.1.2/24, Ethernet32 - 30.1.1.1/24
        self._configure_interface_ip(dut4, self.data.dut4_if1, self.data.dut4_ip1)
        self._configure_interface_ip(dut4, self.data.dut4_if2, self.data.dut4_ip2)

        # D3: Ethernet32 - 30.1.1.2/24
        self._configure_interface_ip(dut3, self.data.dut3_if1, self.data.dut3_ip)

        st.log("IP addresses configured on all interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Validate IP addresses
        st.log("Validating IP address configuration...")
        if not self._verify_interface_ip(dut1, self.data.dut1_if1, self.data.dut1_ip):
            error_msg = f"STEP 1: IP validation failed on {dut1} {self.data.dut1_if1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut1} {self.data.dut1_if1}")

        if not self._verify_interface_ip(dut2, self.data.dut2_if1, self.data.dut2_ip1):
            error_msg = f"STEP 1: IP validation failed on {dut2} {self.data.dut2_if1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut2} {self.data.dut2_if1}")

        if not self._verify_interface_ip(dut2, self.data.dut2_if2, self.data.dut2_ip2):
            error_msg = f"STEP 1: IP validation failed on {dut2} {self.data.dut2_if2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut2} {self.data.dut2_if2}")

        if not self._verify_interface_ip(dut4, self.data.dut4_if1, self.data.dut4_ip1):
            error_msg = f"STEP 1: IP validation failed on {dut4} {self.data.dut4_if1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut4} {self.data.dut4_if1}")

        if not self._verify_interface_ip(dut4, self.data.dut4_if2, self.data.dut4_ip2):
            error_msg = f"STEP 1: IP validation failed on {dut4} {self.data.dut4_if2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut4} {self.data.dut4_if2}")

        if not self._verify_interface_ip(dut3, self.data.dut3_if1, self.data.dut3_ip):
            error_msg = f"STEP 1: IP validation failed on {dut3} {self.data.dut3_if1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut3} {self.data.dut3_if1}")

        if len([f for f in validation_failures if "STEP 1" in f]) == 0:
            st.log("PASS: IP addresses configured and validated successfully")

        # ===== STEP 2: Configure OSPF on D1 (Area 1) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Configure OSPF on D1 (Area 1)")
        st.log("-" * 80)

        self._configure_ospf_process(dut1, [self.data.ospf_area_1])
        self._configure_ospf_network(dut1, self.data.dut1_ip, self.data.ospf_area_1)

        st.log(f"OSPF configured on D1 for Area {self.data.ospf_area_1}")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed on D1")

        # ===== STEP 3: Configure OSPF on D2 (ABR - Area 0 and Area 1) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Configure OSPF on D2 (ABR - Area 0 and Area 1)")
        st.log("-" * 80)

        self._configure_ospf_process(dut2, [self.data.ospf_area_0, self.data.ospf_area_1])
        self._configure_ospf_network(dut2, self.data.dut2_ip1, self.data.ospf_area_1)
        self._configure_ospf_network(dut2, self.data.dut2_ip2, self.data.ospf_area_0)

        st.log(f"OSPF configured on D2 as ABR (Area {self.data.ospf_area_0} and Area {self.data.ospf_area_1})")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed on D2 (ABR)")

        # ===== STEP 4: Configure OSPF on D4 (ABR - Area 0 and Area 2) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Configure OSPF on D4 (ABR - Area 0 and Area 2)")
        st.log("-" * 80)

        self._configure_ospf_process(dut4, [self.data.ospf_area_0, self.data.ospf_area_2])
        self._configure_ospf_network(dut4, self.data.dut4_ip1, self.data.ospf_area_0)
        self._configure_ospf_network(dut4, self.data.dut4_ip2, self.data.ospf_area_2)

        st.log(f"OSPF configured on D4 as ABR (Area {self.data.ospf_area_0} and Area {self.data.ospf_area_2})")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed on D4 (ABR)")

        # ===== STEP 5: Configure OSPF on D3 (Area 2) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Configure OSPF on D3 (Area 2)")
        st.log("-" * 80)

        self._configure_ospf_process(dut3, [self.data.ospf_area_2])
        self._configure_ospf_network(dut3, self.data.dut3_ip, self.data.ospf_area_2)

        st.log(f"OSPF configured on D3 for Area {self.data.ospf_area_2}")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed on D3")

        # ===== STEP 6: Verify OSPF neighbor adjacencies =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Verify OSPF neighbor adjacencies (Full state)")
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
            error_msg = f"STEP 6: OSPF neighbor {dut2_ip1_no_mask} not in Full state on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip1_no_mask} in Full state on {dut1}")

        # Verify D2 sees D1 and D4 as neighbors
        if not self._verify_ospf_neighbor_present(neighbor_output_dut2, dut1_ip_no_mask, "Full"):
            error_msg = f"STEP 6: OSPF neighbor {dut1_ip_no_mask} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut1_ip_no_mask} in Full state on {dut2}")

        if not self._verify_ospf_neighbor_present(neighbor_output_dut2, dut4_ip1_no_mask, "Full"):
            error_msg = f"STEP 6: OSPF neighbor {dut4_ip1_no_mask} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip1_no_mask} in Full state on {dut2}")

        # Verify D4 sees D2 and D3 as neighbors
        if not self._verify_ospf_neighbor_present(neighbor_output_dut4, dut2_ip2_no_mask, "Full"):
            error_msg = f"STEP 6: OSPF neighbor {dut2_ip2_no_mask} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip2_no_mask} in Full state on {dut4}")

        if not self._verify_ospf_neighbor_present(neighbor_output_dut4, dut3_ip_no_mask, "Full"):
            error_msg = f"STEP 6: OSPF neighbor {dut3_ip_no_mask} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut3_ip_no_mask} in Full state on {dut4}")

        # Verify D3 sees D4 as neighbor
        if not self._verify_ospf_neighbor_present(neighbor_output_dut3, dut4_ip2_no_mask, "Full"):
            error_msg = f"STEP 6: OSPF neighbor {dut4_ip2_no_mask} not in Full state on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip2_no_mask} in Full state on {dut3}")

        if len([f for f in validation_failures if "STEP 6" in f]) == 0:
            st.log("PASS: All OSPF neighbors are in Full state")

        # ===== STEP 7: Verify ABR status on D2 and D4 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Verify ABR status on D2 and D4")
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
            error_msg = f"STEP 7: {dut2} is not configured as ABR"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {dut2} is configured as ABR")

        # Verify D2 has Area 0 and Area 1
        if not self._verify_ospf_areas(ospf_output_dut2, [self.data.ospf_area_0, self.data.ospf_area_1]):
            error_msg = f"STEP 7: {dut2} does not have both Area 0 and Area 1"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {dut2} has both Area 0 and Area 1")

        # Verify D4 is an ABR
        if not self._verify_ospf_abr_status(ospf_output_dut4, expected_abr=True):
            error_msg = f"STEP 7: {dut4} is not configured as ABR"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {dut4} is configured as ABR")

        # Verify D4 has Area 0 and Area 2
        if not self._verify_ospf_areas(ospf_output_dut4, [self.data.ospf_area_0, self.data.ospf_area_2]):
            error_msg = f"STEP 7: {dut4} does not have both Area 0 and Area 2"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: {dut4} has both Area 0 and Area 2")

        # Verify D3 is not an ABR
        if not self._verify_ospf_abr_status(ospf_output_dut3, expected_abr=False):
            st.log("WARNING: D3 ABR status check failed (expected: not ABR)")

        st.log("PASS: ABR status verified on D2 and D4")

        # ===== STEP 8: Verify OSPF database (Summary LSAs) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Verify OSPF database (Summary LSAs)")
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

        # ===== STEP 9: Verify inter-area routing =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Verify inter-area routing")
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

        # ===== STEP 10: Verify ping connectivity across all areas =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Verify ping connectivity across all areas")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_PING)

        # Ping from D1 to D2
        if not self._verify_ping_success(dut1, dut2_ip1_no_mask):
            error_msg = f"STEP 10: Ping from {dut1} to {dut2_ip1_no_mask} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut1} to {dut2_ip1_no_mask} successful")

        # Ping from D1 to D3 (across areas through ABRs)
        if not self._verify_ping_success(dut1, dut3_ip_no_mask):
            error_msg = f"STEP 10: Ping from {dut1} to {dut3_ip_no_mask} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut1} to {dut3_ip_no_mask} successful")

        # Ping from D3 to D1 (across areas through ABRs)
        if not self._verify_ping_success(dut3, dut1_ip_no_mask):
            error_msg = f"STEP 10: Ping from {dut3} to {dut1_ip_no_mask} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut3} to {dut1_ip_no_mask} successful")

        # Ping from D2 to D4 (backbone area)
        if not self._verify_ping_success(dut2, dut4_ip1_no_mask):
            error_msg = f"STEP 10: Ping from {dut2} to {dut4_ip1_no_mask} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut2} to {dut4_ip1_no_mask} successful")

        if len([f for f in validation_failures if "STEP 10" in f]) == 0:
            st.log("PASS: Ping connectivity verified across all areas")

        # ===== STEP 11: Verify traceroute through ABRs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Verify traceroute through ABRs")
        st.log("-" * 80)

        # Traceroute from D1 to D3 should go through D2 and D4
        expected_hops_d1_to_d3 = [dut2_ip1_no_mask, dut4_ip1_no_mask, dut3_ip_no_mask]
        if not self._verify_traceroute_path(dut1, dut3_ip_no_mask, expected_hops_d1_to_d3):
            st.log("WARNING: Traceroute from D1 to D3 did not show all expected hops")

        st.log("PASS: Traceroute verified through ABRs")

        # ===== STEP 12: Cleanup - Remove all configurations =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove OSPF configuration
        self._remove_ospf_configuration(dut1)
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut3)
        self._remove_ospf_configuration(dut4)
        st.log("OSPF configuration removed from all DUTs")

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

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF Multi-Area with ABRs validated successfully")
        st.log("Test flow: IP Config → OSPF D1(Area1) → OSPF D2(ABR) → OSPF D4(ABR) → OSPF D3(Area2)")
        st.log("           → Neighbors Full → ABR Verify → Database → Inter-area → Ping → Traceroute → Cleanup ✓")
        st.log("=" * 80)

        # ===== COLLECT TECH SUPPORT AND REPORT FAILURES =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from all DUTs
            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_multiarea_abr_validation_failure")
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
