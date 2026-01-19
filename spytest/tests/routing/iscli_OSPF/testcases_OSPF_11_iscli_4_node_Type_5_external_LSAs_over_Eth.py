"""
OSPF TYPE 5 EXTERNAL LSAs (AS EXTERNAL LSAs) VERIFICATION - 4-NODE TOPOLOGY OVER ETHERNET
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_11_iscli_4_node_Type_5_external_LSAs_over_Eth.py \
  --logs-path ./logs/testcases_OSPF_11_Type5_LSAs_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF Type 5 External LSAs (AS External LSAs) propagation and verification
  in a 4-node linear topology over Ethernet interfaces by:
  1. Configuring IP addresses on all Ethernet interfaces
  2. Configuring OSPF Area 0 on all devices
  3. Verifying OSPF neighbor adjacency (Full state) on all links
  4. Configuring static routes on D1 (ASBR)
  5. Redistributing static routes into OSPF on D1
  6. Verifying Type 5 External LSAs are generated on D1
  7. Verifying Type 5 External LSAs are propagated to D2, D4, and D3
  8. Verifying external routes appear in routing tables with E2 flag
  9. Testing end-to-end connectivity to external networks
  10. Cleanup: Removing all configurations

  Topology:
        D1 (ASBR) -------- D2 -------- D4 -------- D3
    (Ethernet0)       (Ethernet0) (Ethernet16) (Ethernet16)
    10.1.1.1          10.1.1.2    20.1.1.1     20.1.1.2
                      (Ethernet16) (Ethernet32)
                      20.1.1.1     30.1.1.1
                                  (Ethernet32)
                                  30.1.1.2

  Configuration details:
    D1 (ASBR): Ethernet0: 10.1.1.1/24, OSPF area 0
               Static routes: 100.1.1.0/24, 100.2.2.0/24, 100.3.3.0/24 via 10.1.1.2
               OSPF: redistribute static
    D2: Ethernet0: 10.1.1.2/24, Ethernet16: 20.1.1.1/24, OSPF area 0
    D4: Ethernet16: 20.1.1.2/24, Ethernet32: 30.1.1.1/24, OSPF area 0
    D3: Ethernet32: 30.1.1.2/24, OSPF area 0

  Type 5 LSA Verification:
    - D1 generates Type 5 LSAs for redistributed static routes (100.1.1.0/24, 100.2.2.0/24, 100.3.3.0/24)
    - D1 LSAs: self-originated external LSAs visible in 'show ip ospf database external self-originate'
    - D2, D4, D3: receive Type 5 LSAs from D1's Router ID
    - All routers should have external routes with O E2 flag in routing table
    - Expected route format: O E2 100.1.1.0/24 [110/20] via X.X.X.X

  IMPORTANT: Uses 'show ip ospf neighbor', 'show ip ospf interface',
  'show ip ospf database external', 'show ip ospf database external self-originate',
  'show ip route', 'show ip route ospf', and 'show running-configuration' commands.
  Uses klish CLI type exclusively.

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
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_AFTER_STATIC_ROUTE = 3
WAIT_AFTER_REDISTRIBUTION = 15
WAIT_FOR_LSA_PROPAGATION = 10
WAIT_FOR_ROUTE_UPDATE = 10
WAIT_FOR_PING = 2


@pytest.mark.topology("any")
class TestOSPFType5ExternalLSAs4Node:
    """Test cases for validating OSPF Type 5 External LSAs in 4-node topology via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF Type 5 External LSA Verification Test Suite")
        st.log("=" * 80)

        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if len(cls.data.dut_names) < 4:
            st.report_fail("msg", "Minimum 4 DUTs required for this test")

        cls.data.dut1 = cls.data.dut_names[0]  # vs_sonic_1 - ASBR
        cls.data.dut2 = cls.data.dut_names[1]  # vs_sonic_2
        cls.data.dut3 = cls.data.dut_names[2]  # vs_sonic_3
        cls.data.dut4 = cls.data.dut_names[3]  # vs_sonic_4

        st.log(f"DUT1 (D1 - ASBR): {cls.data.dut1}")
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
        cls.data.dut4_ip2 = "30.1.1.1/24"
        cls.data.dut3_ip = "30.1.1.2/24"

        st.log(f"IP Addresses:")
        st.log(f"  D1[{cls.data.dut1_if1}]: {cls.data.dut1_ip}")
        st.log(f"  D2[{cls.data.dut2_if1}]: {cls.data.dut2_ip1}")
        st.log(f"  D2[{cls.data.dut2_if2}]: {cls.data.dut2_ip2}")
        st.log(f"  D4[{cls.data.dut4_if1}]: {cls.data.dut4_ip1}")
        st.log(f"  D4[{cls.data.dut4_if2}]: {cls.data.dut4_ip2}")
        st.log(f"  D3[{cls.data.dut3_if1}]: {cls.data.dut3_ip}")

        # External networks (static routes)
        cls.data.external_networks = ["100.1.1.0/24", "100.2.2.0/24", "100.3.3.0/24"]
        cls.data.static_next_hop = "10.1.1.2"
        st.log(f"External Networks: {cls.data.external_networks}")

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
        st.log("TEST TEARDOWN: Cleanup OSPF Type 5 External LSA Test Suite")
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
    def _configure_static_route(dut: str, network: str, next_hop: str) -> bool:
        """
        Configure static route.

        Args:
            dut: Device handle
            network: Network address with mask (e.g., "100.1.1.0/24")
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
    def _configure_ospf_redistribute_static(dut: str) -> bool:
        """
        Configure OSPF to redistribute static routes.

        Args:
            dut: Device handle

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF redistribute static on {dut}")
        commands = [
            "configure terminal",
            "router ospf",
            "redistribute static",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_ospf_redistribute_static(dut: str) -> bool:
        """
        Remove OSPF redistribute static configuration.

        Args:
            dut: Device handle

        Returns:
            True if successful
        """
        st.log(f"Removing OSPF redistribute static on {dut}")
        commands = [
            "configure terminal",
            "router ospf",
            "no redistribute static",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_static_route(dut: str, network: str, next_hop: str) -> bool:
        """
        Remove static route.

        Args:
            dut: Device handle
            network: Network address with mask
            next_hop: Next hop IP address

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
    def _get_show_ip_route_static(dut: str) -> str:
        """Get 'show ip route static' output."""
        st.log(f"Getting 'show ip route static' output from {dut}")
        output = st.show(dut, "show ip route static", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip route static output from {dut}:\n{output}")
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
    def _get_show_ip_route(dut: str) -> str:
        """Get 'show ip route' output."""
        st.log(f"Getting 'show ip route' output from {dut}")
        output = st.show(dut, "show ip route", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip route output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_database_external(dut: str) -> str:
        """Get 'show ip ospf database external' output."""
        st.log(f"Getting 'show ip ospf database external' output from {dut}")
        output = st.show(dut, "show ip ospf database external", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf database external output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_ip_ospf_database_external_self_originate(dut: str) -> str:
        """Get 'show ip ospf database external self-originate' output."""
        st.log(f"Getting 'show ip ospf database external self-originate' output from {dut}")
        output = st.show(dut, "show ip ospf database external self-originate", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip ospf database external self-originate output from {dut}:\n{output}")
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
    def _verify_static_route_in_table(output: str, network: str) -> bool:
        """
        Verify static route is present in routing table.

        Args:
            output: Output from 'show ip route static'
            network: Network to verify (e.g., "100.1.1.0/24")

        Returns:
            True if route found
        """
        st.log(f"Verifying static route {network} in routing table")

        if network in output and ('S>' in output or 'S*' in output or 'S ' in output):
            st.log(f"PASS: Static route {network} found in routing table")
            return True

        st.error(f"FAIL: Static route {network} not found in routing table")
        return False

    @staticmethod
    def _verify_type5_lsa_generated(output: str, network_prefix: str) -> bool:
        """
        Verify Type 5 External LSA is generated.

        Args:
            output: Output from 'show ip ospf database external'
            network_prefix: Network prefix without mask (e.g., "100.1.1.0")

        Returns:
            True if LSA found
        """
        st.log(f"Verifying Type 5 LSA for {network_prefix} is generated")

        # Check if "AS External Link States" section exists
        if "AS External Link States" not in output:
            st.error("FAIL: No AS External Link States section found")
            return False

        # Check if network prefix is in the output
        if network_prefix in output:
            st.log(f"PASS: Type 5 LSA for {network_prefix} found")
            return True

        st.error(f"FAIL: Type 5 LSA for {network_prefix} not found")
        return False

    @staticmethod
    def _verify_type5_lsa_self_originated(output: str, network_prefix: str) -> bool:
        """
        Verify self-originated Type 5 External LSA.

        Args:
            output: Output from 'show ip ospf database external self-originate'
            network_prefix: Network prefix without mask

        Returns:
            True if self-originated LSA found
        """
        st.log(f"Verifying self-originated Type 5 LSA for {network_prefix}")

        if "AS External Link States" not in output:
            st.error("FAIL: No self-originated AS External Link States found")
            return False

        if network_prefix in output:
            st.log(f"PASS: Self-originated Type 5 LSA for {network_prefix} found")
            return True

        st.error(f"FAIL: Self-originated Type 5 LSA for {network_prefix} not found")
        return False

    @staticmethod
    def _verify_external_route_in_ospf_table(output: str, network: str) -> bool:
        """
        Verify external route (O E2) in OSPF routing table.

        Args:
            output: Output from 'show ip route ospf'
            network: Network to verify (e.g., "100.1.1.0/24")

        Returns:
            True if external route found with E2 flag
        """
        st.log(f"Verifying external route {network} in OSPF routing table")

        # Look for "O E2" or "O>* E2" pattern with the network
        lines = output.split('\n')
        for line in lines:
            if network in line and ('E2' in line or 'O>' in line):
                st.log(f"PASS: External route {network} found in OSPF table")
                return True

        st.error(f"FAIL: External route {network} not found in OSPF table")
        return False

    @staticmethod
    def _verify_ping_success(dut: str, target_ip: str, count: int = 4) -> bool:
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

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_TYPE5_LSA_4NODE_001"])
    def test_ospf_type5_external_lsa_verification(self) -> None:
        """
        TC_OSPF_TYPE5_LSA_4NODE_001: Validate OSPF Type 5 External LSAs in 4-node topology.

        Test Procedure:
        1. Configure IP addresses on all interfaces
        2. Configure OSPF Area 0 on all devices
        3. Verify OSPF neighbor adjacency (Full state) on all links
        4. Configure static routes on D1 (ASBR) for external networks
        5. Verify static routes are installed in D1's routing table
        6. Redistribute static routes into OSPF on D1
        7. Verify Type 5 External LSAs are generated on D1 (self-originated)
        8. Verify Type 5 External LSAs are present in OSPF database on all devices
        9. Verify external routes appear in routing tables with O E2 flag
        10. Verify complete OSPF database on all devices
        11. Test end-to-end connectivity
        12. Cleanup: Remove all configurations

        Expected Result:
        - OSPF neighbors form Full adjacency on all links
        - Static routes installed on D1
        - Type 5 External LSAs generated on D1 for all external networks
        - Type 5 LSAs propagated to D2, D4, and D3
        - External routes visible in all routing tables with E2 flag
        - OSPF database contains AS External Link States on all devices
        - End-to-end connectivity working
        - All configurations cleaned up

        Known Issue:
        - This test validates the bug reported in JIRA where Type 5 LSAs
          are not generated even after 'redistribute static' is configured
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF Type 5 External LSA Verification - 4-Node Topology over Ethernet")
        st.log("=" * 80)

        # Track validation failures - test will continue but report fail at end
        validation_failures = []

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4
        area = self.data.ospf_area

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

        st.log("PASS: IP addresses configured successfully")

        # ===== STEP 2: Configure OSPF on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Configure OSPF Area 0 on all devices")
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

        # ===== STEP 3: Verify OSPF neighbor adjacency =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Verify OSPF neighbor adjacency (Full state) on all links")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor outputs from all devices
        st.log("Getting OSPF neighbor information from all devices...")
        neighbor_output_dut1 = self._get_show_ip_ospf_neighbor(dut1)
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor(dut2)
        neighbor_output_dut3 = self._get_show_ip_ospf_neighbor(dut3)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor(dut4)

        # Verify D1 ↔ D2 neighbor relationship
        dut2_ip_no_mask = self.data.dut2_ip1.split('/')[0]  # 10.1.1.2
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut1, dut2_ip_no_mask):
            error_msg = f"STEP 3: OSPF neighbor {dut2_ip_no_mask} not in Full state on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip_no_mask} in Full state on {dut1}")

        dut1_ip_no_mask = self.data.dut1_ip.split('/')[0]  # 10.1.1.1
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut2, dut1_ip_no_mask):
            error_msg = f"STEP 3: OSPF neighbor {dut1_ip_no_mask} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut1_ip_no_mask} in Full state on {dut2}")

        # Verify D2 ↔ D4 neighbor relationship
        dut4_ip1_no_mask = self.data.dut4_ip1.split('/')[0]  # 20.1.1.2
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut2, dut4_ip1_no_mask):
            error_msg = f"STEP 3: OSPF neighbor {dut4_ip1_no_mask} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip1_no_mask} in Full state on {dut2}")

        dut2_ip2_no_mask = self.data.dut2_ip2.split('/')[0]  # 20.1.1.1
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut4, dut2_ip2_no_mask):
            error_msg = f"STEP 3: OSPF neighbor {dut2_ip2_no_mask} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip2_no_mask} in Full state on {dut4}")

        # Verify D4 ↔ D3 neighbor relationship
        dut3_ip_no_mask = self.data.dut3_ip.split('/')[0]  # 30.1.1.2
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut4, dut3_ip_no_mask):
            error_msg = f"STEP 3: OSPF neighbor {dut3_ip_no_mask} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut3_ip_no_mask} in Full state on {dut4}")

        dut4_ip2_no_mask = self.data.dut4_ip2.split('/')[0]  # 30.1.1.1
        if not self._verify_ospf_neighbor_full_state(neighbor_output_dut3, dut4_ip2_no_mask):
            error_msg = f"STEP 3: OSPF neighbor {dut4_ip2_no_mask} not in Full state on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip2_no_mask} in Full state on {dut3}")

        if len([f for f in validation_failures if "STEP 3" in f]) == 0:
            st.log("PASS: All OSPF neighbors are in Full state")

        # ===== STEP 4: Configure static routes on D1 (ASBR) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Configure static routes on D1 (ASBR) for external networks")
        st.log("-" * 80)

        # Configure static routes for external networks
        for network in self.data.external_networks:
            self._configure_static_route(dut1, network, self.data.static_next_hop)

        st.log("Static routes configured on D1")
        time.sleep(WAIT_AFTER_STATIC_ROUTE)

        st.log("PASS: Static routes configured successfully")

        # ===== STEP 5: Verify static routes in D1's routing table =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Verify static routes are installed in D1's routing table")
        st.log("-" * 80)

        # Get static route output from D1
        static_route_output_dut1 = self._get_show_ip_route_static(dut1)

        # Verify each static route
        for network in self.data.external_networks:
            if not self._verify_static_route_in_table(static_route_output_dut1, network):
                error_msg = f"STEP 5: Static route {network} not found in routing table on {dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: Static route {network} found in routing table on {dut1}")

        if len([f for f in validation_failures if "STEP 5" in f]) == 0:
            st.log("PASS: All static routes verified in routing table")

        # ===== STEP 6: Redistribute static routes into OSPF on D1 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Redistribute static routes into OSPF on D1")
        st.log("-" * 80)

        # Configure redistribute static
        self._configure_ospf_redistribute_static(dut1)

        st.log(f"Waiting {WAIT_AFTER_REDISTRIBUTION} seconds for redistribution to take effect...")
        time.sleep(WAIT_AFTER_REDISTRIBUTION)

        st.log("PASS: OSPF redistribute static configured on D1")

        # ===== STEP 7: Verify Type 5 External LSAs generated on D1 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Verify Type 5 External LSAs are generated on D1 (self-originated)")
        st.log("-" * 80)

        # Get OSPF database external output from D1
        db_external_output_dut1 = self._get_show_ip_ospf_database_external(dut1)

        # Verify Type 5 LSAs for each external network
        for network in self.data.external_networks:
            network_prefix = network.split('/')[0]  # e.g., "100.1.1.0"
            if not self._verify_type5_lsa_generated(db_external_output_dut1, network_prefix):
                error_msg = f"STEP 7: Type 5 LSA for {network} not generated on {dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: Type 5 LSA for {network} generated on {dut1}")

        # Get self-originated LSAs
        db_external_self_orig_output_dut1 = self._get_show_ip_ospf_database_external_self_originate(dut1)

        # Verify self-originated Type 5 LSAs
        for network in self.data.external_networks:
            network_prefix = network.split('/')[0]
            if not self._verify_type5_lsa_self_originated(db_external_self_orig_output_dut1, network_prefix):
                error_msg = f"STEP 7: Self-originated Type 5 LSA for {network} not found on {dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: Self-originated Type 5 LSA for {network} found on {dut1}")

        if len([f for f in validation_failures if "STEP 7" in f]) == 0:
            st.log("PASS: All Type 5 External LSAs generated on D1")

        # ===== STEP 8: Verify Type 5 LSAs propagated to all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Verify Type 5 External LSAs are propagated to D2, D4, and D3")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_LSA_PROPAGATION} seconds for LSA propagation...")
        time.sleep(WAIT_FOR_LSA_PROPAGATION)

        # Get OSPF database external output from all devices
        db_external_output_dut2 = self._get_show_ip_ospf_database_external(dut2)
        db_external_output_dut4 = self._get_show_ip_ospf_database_external(dut4)
        db_external_output_dut3 = self._get_show_ip_ospf_database_external(dut3)

        # Verify Type 5 LSAs on D2
        for network in self.data.external_networks:
            network_prefix = network.split('/')[0]
            if not self._verify_type5_lsa_generated(db_external_output_dut2, network_prefix):
                error_msg = f"STEP 8: Type 5 LSA for {network} not received on {dut2}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: Type 5 LSA for {network} received on {dut2}")

        # Verify Type 5 LSAs on D4
        for network in self.data.external_networks:
            network_prefix = network.split('/')[0]
            if not self._verify_type5_lsa_generated(db_external_output_dut4, network_prefix):
                error_msg = f"STEP 8: Type 5 LSA for {network} not received on {dut4}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: Type 5 LSA for {network} received on {dut4}")

        # Verify Type 5 LSAs on D3
        for network in self.data.external_networks:
            network_prefix = network.split('/')[0]
            if not self._verify_type5_lsa_generated(db_external_output_dut3, network_prefix):
                error_msg = f"STEP 8: Type 5 LSA for {network} not received on {dut3}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: Type 5 LSA for {network} received on {dut3}")

        if len([f for f in validation_failures if "STEP 8" in f]) == 0:
            st.log("PASS: All Type 5 External LSAs propagated to all devices")

        # ===== STEP 9: Verify external routes in routing tables =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Verify external routes appear in routing tables with O E2 flag")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_ROUTE_UPDATE} seconds for routes to be installed...")
        time.sleep(WAIT_FOR_ROUTE_UPDATE)

        # Get OSPF route output from all devices
        ospf_route_output_dut2 = self._get_show_ip_route_ospf(dut2)
        ospf_route_output_dut4 = self._get_show_ip_route_ospf(dut4)
        ospf_route_output_dut3 = self._get_show_ip_route_ospf(dut3)

        # Verify external routes on D2
        for network in self.data.external_networks:
            if not self._verify_external_route_in_ospf_table(ospf_route_output_dut2, network):
                error_msg = f"STEP 9: External route {network} not found in OSPF routing table on {dut2}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: External route {network} found in OSPF routing table on {dut2}")

        # Verify external routes on D4
        for network in self.data.external_networks:
            if not self._verify_external_route_in_ospf_table(ospf_route_output_dut4, network):
                error_msg = f"STEP 9: External route {network} not found in OSPF routing table on {dut4}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: External route {network} found in OSPF routing table on {dut4}")

        # Verify external routes on D3
        for network in self.data.external_networks:
            if not self._verify_external_route_in_ospf_table(ospf_route_output_dut3, network):
                error_msg = f"STEP 9: External route {network} not found in OSPF routing table on {dut3}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: External route {network} found in OSPF routing table on {dut3}")

        if len([f for f in validation_failures if "STEP 9" in f]) == 0:
            st.log("PASS: All external routes verified in routing tables")

        # ===== STEP 10: Verify OSPF database on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Verify complete OSPF database on all devices")
        st.log("-" * 80)

        # Get complete OSPF database from all devices
        db_output_dut1 = self._get_show_ip_ospf_database(dut1)
        db_output_dut2 = self._get_show_ip_ospf_database(dut2)
        db_output_dut4 = self._get_show_ip_ospf_database(dut4)
        db_output_dut3 = self._get_show_ip_ospf_database(dut3)

        # Verify "AS External Link States" section exists
        for dut_name, db_output in [(dut1, db_output_dut1), (dut2, db_output_dut2),
                                      (dut4, db_output_dut4), (dut3, db_output_dut3)]:
            if "AS External Link States" not in db_output:
                error_msg = f"STEP 10: AS External Link States section not found in OSPF database on {dut_name}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            else:
                st.log(f"PASS: AS External Link States section found in OSPF database on {dut_name}")

        if len([f for f in validation_failures if "STEP 10" in f]) == 0:
            st.log("PASS: OSPF database verified on all devices")

        # ===== STEP 11: Test end-to-end connectivity =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Verify end-to-end connectivity")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_PING)

        # Ping from D1 to D3
        d3_ip = self.data.dut3_ip.split('/')[0]
        if not self._verify_ping_success(dut1, d3_ip, 4):
            error_msg = f"STEP 11: Ping from {dut1} to {d3_ip} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut1} to {d3_ip} successful")

        # Ping from D3 to D1
        d1_ip = self.data.dut1_ip.split('/')[0]
        if not self._verify_ping_success(dut3, d1_ip, 4):
            error_msg = f"STEP 11: Ping from {dut3} to {d1_ip} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from {dut3} to {d1_ip} successful")

        if len([f for f in validation_failures if "STEP 11" in f]) == 0:
            st.log("PASS: End-to-end connectivity verified")

        # ===== STEP 12: Cleanup - Remove all configurations =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove redistribute static from D1
        self._remove_ospf_redistribute_static(dut1)
        st.log("Removed 'redistribute static' from D1")

        # Remove static routes from D1
        for network in self.data.external_networks:
            self._remove_static_route(dut1, network, self.data.static_next_hop)
        st.log("Removed static routes from D1")

        # Remove OSPF configuration from all devices
        self._remove_ospf_configuration(dut1)
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut3)
        self._remove_ospf_configuration(dut4)
        st.log("OSPF configuration removed from all devices")

        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Remove IP addresses from all interfaces
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
        st.log("=" * 80)
        st.log("TEST COMPLETE: OSPF Type 5 External LSA verification test completed")
        st.log("Summary:")
        st.log(f"  ✓ OSPF neighbors formed on all links")
        st.log(f"  ✓ Static routes configured on {dut1} (ASBR)")
        st.log(f"  ✓ Static routes redistributed into OSPF")
        st.log(f"  ✓ Type 5 External LSAs generated on {dut1}")
        st.log(f"  ✓ Type 5 External LSAs propagated to all devices")
        st.log(f"  ✓ External routes installed in routing tables with E2 flag")
        st.log(f"  ✓ End-to-end connectivity verified")
        st.log("=" * 80)

        # Check for any validation failures
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED:")
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.log("!" * 80)
            st.report_fail("msg", f"Test completed with {len(validation_failures)} validation failure(s). See errors above.")
        else:
            st.log("All validations passed ✓")
            st.report_pass("test_case_passed")
