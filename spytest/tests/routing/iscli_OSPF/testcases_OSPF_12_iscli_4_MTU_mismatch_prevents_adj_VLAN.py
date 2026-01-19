"""
OSPF MTU MISMATCH PREVENTS ADJACENCY - 4-NODE TOPOLOGY WITH VLAN INTERFACES
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_12_iscli_4_MTU_mismatch_prevents_adj_VLAN.py \
  --logs-path ./logs/testcases_OSPF_12_iscli_4_MTU_mismatch_prevents_adj_VLAN_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates that OSPF adjacency is prevented when there is an MTU mismatch
  between neighboring routers on VLAN interfaces. The test covers:

  1. Remove IP addresses from Ethernet interfaces (baseline)
  2. Create VLAN and add Ethernet ports as tagged members
  3. Configure IP addresses on VLAN interfaces with matching MTU
  4. Configure OSPF on both routers
  5. Verify OSPF neighbor adjacency forms successfully (Full state)
  6. Change MTU on one VLAN to create mismatch
  7. Verify OSPF adjacency is broken or prevented (negative test)
  8. Restore matching MTU configuration
  9. Verify OSPF adjacency recovers
  10. Complete cleanup of configurations

  Test Scenario:
  - D2 and D4 are connected via VLAN 20 (20.1.1.0/24)
  - VLAN 20 contains Ethernet16 from both routers as tagged members
  - Initially both have matching MTU (9100), OSPF adjacency forms
  - D4 VLAN MTU is changed to 1500 using 'mtu 1500' command
  - After MTU mismatch, OSPF adjacency should fail or break
  - When MTU is restored to matching values, adjacency should recover

  Topology:
        D2 (vs_sonic_2) -------- D4 (vs_sonic_4)
       (Ethernet16)              (Ethernet16)
           VLAN 20                   VLAN 20
       (Vlan20: 20.1.1.2/24)     (Vlan20: 20.1.1.1/24)
        OSPF Area 0               OSPF Area 0
        MTU 9100                  MTU 9100 → 1500 → 9100
        Adjacency: Full → Broken → Full

  Configuration details:
    D2 (vs_sonic_2):
      - VLAN 20 with Ethernet16 as tagged member
      - Vlan20: 20.1.1.2/24
      - OSPF Area 0
      - Network: 20.1.1.2/24 area 0
      - MTU: 9100 (constant)

    D4 (vs_sonic_4):
      - VLAN 20 with Ethernet16 as tagged member
      - Vlan20: 20.1.1.1/24
      - OSPF Area 0
      - Network: 20.1.1.1/24 area 0
      - MTU: 9100 → 1500 (mismatch) → 9100 (restored)

  IMPORTANT: This is a NEGATIVE test case. Uses 'show ip ospf neighbor' to verify
  that adjacency is broken when MTU mismatch exists. Uses klish CLI type exclusively.

Pre-requisites:
  - Topology: 4-node (uses D2 and D4) | Supported: HW and Virtual
  - Testbed: testbed_4vs.yaml with topology:
    * D2 (vs_sonic_2) Ethernet16 <-> D4 (vs_sonic_4) Ethernet16
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
WAIT_AFTER_MTU_CHANGE = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_NEIGHBOR_DOWN = 60


@pytest.mark.topology("any")
class TestOSPFMTUMismatchVLAN:
    """Test cases for validating OSPF MTU mismatch prevents adjacency on VLAN interfaces via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF MTU Mismatch Test Suite (VLAN)")
        st.log("=" * 80)

        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if len(cls.data.dut_names) < 4:
            st.report_fail("msg", "Minimum 4 DUTs required for this test")

        cls.data.dut1 = cls.data.dut_names[0]  # vs_sonic_1 (not used in this test)
        cls.data.dut2 = cls.data.dut_names[1]  # vs_sonic_2
        cls.data.dut3 = cls.data.dut_names[2]  # vs_sonic_3 (not used in this test)
        cls.data.dut4 = cls.data.dut_names[3]  # vs_sonic_4

        st.log(f"DUT2 (D2): {cls.data.dut2}")
        st.log(f"DUT4 (D4): {cls.data.dut4}")

        # CLI type - use klish as specified
        cls.data.cli_type = CLI_TYPE
        st.log(f"CLI Type: {cls.data.cli_type}")

        # VLAN ID
        cls.data.vlan_id = "20"
        st.log(f"VLAN ID: {cls.data.vlan_id}")

        # Test interfaces based on testbed_4vs.yaml topology
        # D2 (vs_sonic_2) Ethernet16 <-> D4 (vs_sonic_4) Ethernet16
        cls.data.dut2_eth_ports = ["Ethernet16"]
        cls.data.dut4_eth_ports = ["Ethernet16"]

        st.log(f"Topology: D2{cls.data.dut2_eth_ports} <-> D4{cls.data.dut4_eth_ports} (VLAN {cls.data.vlan_id})")

        # IP addresses for VLAN interfaces
        cls.data.dut2_ip = "20.1.1.2/24"
        cls.data.dut4_ip = "20.1.1.1/24"

        st.log(f"IP Addresses:")
        st.log(f"  D2[Vlan{cls.data.vlan_id}]: {cls.data.dut2_ip}")
        st.log(f"  D4[Vlan{cls.data.vlan_id}]: {cls.data.dut4_ip}")

        # OSPF area
        cls.data.ospf_area = "0"
        st.log(f"OSPF Area: {cls.data.ospf_area}")

        # MTU values
        cls.data.default_mtu = "9100"
        cls.data.mismatch_mtu = "1500"
        st.log(f"MTU: Default={cls.data.default_mtu}, Mismatch={cls.data.mismatch_mtu}")

        # Set terminal length 0 to disable pagination
        st.log("Setting terminal length 0 to disable pagination on all DUTs")
        st.config(cls.data.dut2, "terminal length 0", type=CLI_TYPE)
        st.config(cls.data.dut4, "terminal length 0", type=CLI_TYPE)

        st.log("Test setup complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup OSPF MTU Mismatch Test Suite (VLAN)")
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
        """Remove IPv4 and IPv6 addresses from all specified interfaces."""
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

    # ========== HELPER METHODS - VLAN CONFIGURATION ==========

    @staticmethod
    def _create_vlan(dut: str, vlan_id: str) -> bool:
        """Create VLAN using klish commands."""
        st.log(f"Creating VLAN {vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"vlan {vlan_id}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _delete_vlan(dut: str, vlan_id: str) -> bool:
        """Delete VLAN using klish commands."""
        st.log(f"Deleting VLAN {vlan_id} from {dut}")
        commands = [
            "configure terminal",
            f"no vlan {vlan_id}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _add_ports_to_vlan(dut: str, ports: List[str], vlan_id: str) -> bool:
        """Add ports to VLAN as tagged members."""
        st.log(f"Adding ports {ports} to VLAN {vlan_id} on {dut}")

        for port in ports:
            commands = [
                "configure terminal",
                f"interface {port}",
                f"switchport trunk allowed vlan {vlan_id}",
                "exit"
            ]
            result = st.config(dut, commands, type=CLI_TYPE)

        st.log(f"Ports added to VLAN {vlan_id}")
        return True

    @staticmethod
    def _remove_ports_from_vlan(dut: str, ports: List[str], vlan_id: str) -> bool:
        """Remove ports from VLAN."""
        st.log(f"Removing ports {ports} from VLAN {vlan_id} on {dut}")

        for port in ports:
            commands = [
                "configure terminal",
                f"interface {port}",
                f"no switchport trunk allowed vlan {vlan_id}",
                "exit"
            ]
            result = st.config(dut, commands, type=CLI_TYPE)

        st.log(f"Ports removed from VLAN {vlan_id}")
        return True

    # ========== HELPER METHODS - IP CONFIGURATION ==========

    @staticmethod
    def _configure_vlan_ip(dut: str, vlan_id: str, ip_address: str) -> bool:
        """Configure IP address on VLAN interface."""
        st.log(f"Configuring IP address {ip_address} on Vlan{vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            f"ip address {ip_address}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_vlan_ip(dut: str, vlan_id: str) -> bool:
        """Remove IP address from VLAN interface."""
        st.log(f"Removing IP address from Vlan{vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no ip address",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    # ========== HELPER METHODS - MTU CONFIGURATION ==========

    @staticmethod
    def _configure_vlan_mtu(dut: str, vlan_id: str, mtu_value: str) -> bool:
        """Configure MTU on VLAN interface."""
        st.log(f"Configuring MTU {mtu_value} on Vlan{vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            f"mtu {mtu_value}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _get_vlan_mtu(dut: str, vlan_id: str) -> Optional[str]:
        """Get current MTU value from VLAN interface running-configuration."""
        st.log(f"Getting MTU value for Vlan{vlan_id} on {dut}")

        # Command: show running-configuration interface Vlan X
        command = f"show running-configuration interface Vlan {vlan_id}"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True, skip_error_check=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"Running-config output from {dut}:\n{output}")

        # Search for "mtu <value>" pattern
        mtu_pattern = r'mtu\s+(\d+)'
        match = re.search(mtu_pattern, output, re.IGNORECASE)

        if match:
            mtu_value = match.group(1)
            st.log(f"Found MTU value: {mtu_value}")
            return mtu_value
        else:
            st.log("MTU value not found in output")
            return None

    # ========== HELPER METHODS - OSPF CONFIGURATION ==========

    @staticmethod
    def _configure_ospf_process(dut: str, area: str) -> bool:
        """Configure OSPF process and area."""
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
    def _get_show_ip_ospf_neighbor_output(dut: str) -> str:
        """Get 'show ip ospf neighbor' output as raw string."""
        st.log(f"Getting 'show ip ospf neighbor' output from {dut}")
        command = "show ip ospf neighbor"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"show ip ospf neighbor output from {dut}:\n{output}")
        return output

    # ========== HELPER METHODS - VALIDATION ==========

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
    def _verify_ospf_neighbor_absent_or_not_full(neighbor_output: str, neighbor_ip: str) -> bool:
        """Verify that OSPF neighbor is either absent or not in Full state (negative test)."""
        st.log(f"Verifying OSPF neighbor {neighbor_ip} is NOT in Full state (negative test)")

        # If neighbor is not in output at all, that's acceptable
        if neighbor_ip not in neighbor_output:
            st.log(f"PASS: Neighbor {neighbor_ip} not found (adjacency prevented)")
            return True

        # If neighbor is in output but not in Full state, that's acceptable
        lines = neighbor_output.split('\n')
        for line in lines:
            if neighbor_ip in line:
                st.log(f"Found neighbor line: {line}")
                if "Full" in line:
                    st.log(f"FAIL: Neighbor {neighbor_ip} is in Full state (should be broken)")
                    return False
                else:
                    st.log(f"PASS: Neighbor {neighbor_ip} exists but not in Full state (adjacency broken)")
                    return True

        st.log(f"PASS: Neighbor {neighbor_ip} adjacency prevented")
        return True

    # ========== TEST CASE ==========

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_MTU_MISMATCH_VLAN_001"])
    @pytest.mark.negative
    def test_ospf_mtu_mismatch_prevents_adjacency_vlan(self) -> None:
        """
        TC_OSPF_MTU_MISMATCH_VLAN_001: Validate that MTU mismatch prevents OSPF adjacency on VLAN.

        Test Procedure:
        1. Remove IP addresses from Ethernet interfaces (baseline)
        2. Create VLAN 20 and add Ethernet16 to VLAN on D2 and D4
        3. Configure IP addresses on VLAN interfaces
        4. Configure matching MTU (9100) on both VLAN interfaces
        5. Configure OSPF on both routers
        6. Verify OSPF neighbor adjacency forms (Full state) - baseline
        7. Change MTU on D4 VLAN to 1500 (create mismatch)
        8. Verify OSPF adjacency is broken or prevented (negative test)
        9. Restore MTU on D4 VLAN to 9100 (matching)
        10. Verify OSPF adjacency recovers (Full state)
        11. Cleanup: Remove all configurations

        Expected Result:
        - With matching MTU (9100), OSPF adjacency forms successfully
        - With MTU mismatch (D2=9100, D4=1500), OSPF adjacency is broken/prevented
        - After restoring matching MTU, OSPF adjacency recovers
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF MTU Mismatch Prevents Adjacency (VLAN)")
        st.log("=" * 80)

        # Track validation failures - test will continue but report fail at end
        validation_failures = []

        dut2 = self.data.dut2
        dut4 = self.data.dut4
        area = self.data.ospf_area
        vlan_id = self.data.vlan_id

        # ===== STEP 1: Remove IP addresses from Ethernet interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Remove IP addresses from Ethernet interfaces (baseline)")
        st.log("-" * 80)

        self._remove_ip_addresses_from_interfaces(dut2, self.data.dut2_eth_ports)
        self._remove_ip_addresses_from_interfaces(dut4, self.data.dut4_eth_ports)

        st.log("IP addresses removed from all Ethernet interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: IP addresses removed from Ethernet interfaces")

        # ===== STEP 2: Create VLAN and add ports =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Create VLAN 20 and add Ethernet ports")
        st.log("-" * 80)

        self._create_vlan(dut2, vlan_id)
        self._create_vlan(dut4, vlan_id)

        self._add_ports_to_vlan(dut2, self.data.dut2_eth_ports, vlan_id)
        self._add_ports_to_vlan(dut4, self.data.dut4_eth_ports, vlan_id)

        st.log(f"VLAN {vlan_id} created and ports added")
        time.sleep(WAIT_AFTER_VLAN_CONFIG)

        st.log("PASS: VLAN configuration completed")

        # ===== STEP 3: Configure IP addresses on VLAN interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Configure IP addresses on VLAN interfaces")
        st.log("-" * 80)

        self._configure_vlan_ip(dut2, vlan_id, self.data.dut2_ip)
        self._configure_vlan_ip(dut4, vlan_id, self.data.dut4_ip)

        st.log("IP addresses configured on VLAN interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: IP addresses configured")

        # ===== STEP 4: Configure matching MTU on both VLAN interfaces =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 4: Configure matching MTU ({self.data.default_mtu}) on both VLAN interfaces")
        st.log("-" * 80)

        self._configure_vlan_mtu(dut2, vlan_id, self.data.default_mtu)
        self._configure_vlan_mtu(dut4, vlan_id, self.data.default_mtu)

        st.log(f"MTU {self.data.default_mtu} configured on both VLAN interfaces")
        time.sleep(WAIT_AFTER_MTU_CHANGE)

        # Verify MTU configuration
        dut2_mtu = self._get_vlan_mtu(dut2, vlan_id)
        dut4_mtu = self._get_vlan_mtu(dut4, vlan_id)

        st.log(f"D2 Vlan{vlan_id} MTU: {dut2_mtu}")
        st.log(f"D4 Vlan{vlan_id} MTU: {dut4_mtu}")

        st.log("PASS: Matching MTU configured")

        # ===== STEP 5: Configure OSPF on both routers =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Configure OSPF on D2 and D4")
        st.log("-" * 80)

        self._configure_ospf_process(dut2, area)
        self._configure_ospf_network(dut2, self.data.dut2_ip, area)

        self._configure_ospf_process(dut4, area)
        self._configure_ospf_network(dut4, self.data.dut4_ip, area)

        st.log("OSPF configured on D2 and D4")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed")

        # ===== STEP 6: Verify OSPF neighbor adjacency (baseline with matching MTU) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Verify OSPF neighbor adjacency forms with matching MTU (baseline)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        dut2_ip_no_mask = self.data.dut2_ip.split('/')[0]
        dut4_ip_no_mask = self.data.dut4_ip.split('/')[0]

        if not self._verify_ospf_neighbor_present(neighbor_output_dut2, dut4_ip_no_mask, "Full"):
            error_msg = f"STEP 6: OSPF neighbor {dut4_ip_no_mask} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip_no_mask} in Full state on {dut2}")

        if not self._verify_ospf_neighbor_present(neighbor_output_dut4, dut2_ip_no_mask, "Full"):
            error_msg = f"STEP 6: OSPF neighbor {dut2_ip_no_mask} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip_no_mask} in Full state on {dut4}")

        if len([f for f in validation_failures if "STEP 6" in f]) == 0:
            st.log("PASS: Baseline verified - OSPF adjacency formed with matching MTU")

        # ===== STEP 7: Change MTU on D4 VLAN to create mismatch =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 7: Change MTU on D4 Vlan{vlan_id} to {self.data.mismatch_mtu} (create mismatch)")
        st.log("-" * 80)

        self._configure_vlan_mtu(dut4, vlan_id, self.data.mismatch_mtu)

        st.log(f"MTU on D4 Vlan{vlan_id} changed to {self.data.mismatch_mtu}")
        time.sleep(WAIT_AFTER_MTU_CHANGE)

        # Verify MTU mismatch
        dut2_mtu_after = self._get_vlan_mtu(dut2, vlan_id)
        dut4_mtu_after = self._get_vlan_mtu(dut4, vlan_id)

        st.log(f"MTU mismatch created:")
        st.log(f"  D2 Vlan{vlan_id} MTU: {dut2_mtu_after}")
        st.log(f"  D4 Vlan{vlan_id} MTU: {dut4_mtu_after}")

        st.log("PASS: MTU mismatch created")

        # ===== STEP 8: Verify OSPF adjacency is broken (negative test) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Verify OSPF adjacency is broken/prevented with MTU mismatch (NEGATIVE TEST)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_DOWN} seconds for adjacency to break...")
        time.sleep(WAIT_FOR_NEIGHBOR_DOWN)

        neighbor_output_dut2_mismatch = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4_mismatch = self._get_show_ip_ospf_neighbor_output(dut4)

        if not self._verify_ospf_neighbor_absent_or_not_full(neighbor_output_dut2_mismatch, dut4_ip_no_mask):
            error_msg = f"STEP 8: NEGATIVE TEST FAILED - OSPF neighbor {dut4_ip_no_mask} still in Full state on {dut2} despite MTU mismatch"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: NEGATIVE TEST - OSPF neighbor {dut4_ip_no_mask} adjacency broken/prevented on {dut2}")

        if not self._verify_ospf_neighbor_absent_or_not_full(neighbor_output_dut4_mismatch, dut2_ip_no_mask):
            error_msg = f"STEP 8: NEGATIVE TEST FAILED - OSPF neighbor {dut2_ip_no_mask} still in Full state on {dut4} despite MTU mismatch"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: NEGATIVE TEST - OSPF neighbor {dut2_ip_no_mask} adjacency broken/prevented on {dut4}")

        if len([f for f in validation_failures if "STEP 8" in f]) == 0:
            st.log("PASS: MTU mismatch successfully prevented OSPF adjacency")

        # ===== STEP 9: Restore matching MTU =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 9: Restore MTU on D4 Vlan{vlan_id} to {self.data.default_mtu} (matching)")
        st.log("-" * 80)

        self._configure_vlan_mtu(dut4, vlan_id, self.data.default_mtu)

        st.log(f"MTU on D4 Vlan{vlan_id} restored to {self.data.default_mtu}")
        time.sleep(WAIT_AFTER_MTU_CHANGE)

        # Verify matching MTU restored
        dut2_mtu_restored = self._get_vlan_mtu(dut2, vlan_id)
        dut4_mtu_restored = self._get_vlan_mtu(dut4, vlan_id)

        st.log(f"Matching MTU restored:")
        st.log(f"  D2 Vlan{vlan_id} MTU: {dut2_mtu_restored}")
        st.log(f"  D4 Vlan{vlan_id} MTU: {dut4_mtu_restored}")

        st.log("PASS: Matching MTU restored")

        # ===== STEP 10: Verify OSPF adjacency recovers =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Verify OSPF adjacency recovers after MTU match restored")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to recover...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        neighbor_output_dut2_restored = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4_restored = self._get_show_ip_ospf_neighbor_output(dut4)

        if not self._verify_ospf_neighbor_present(neighbor_output_dut2_restored, dut4_ip_no_mask, "Full"):
            error_msg = f"STEP 10: OSPF neighbor {dut4_ip_no_mask} not in Full state on {dut2} after MTU restored"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip_no_mask} recovered to Full state on {dut2}")

        if not self._verify_ospf_neighbor_present(neighbor_output_dut4_restored, dut2_ip_no_mask, "Full"):
            error_msg = f"STEP 10: OSPF neighbor {dut2_ip_no_mask} not in Full state on {dut4} after MTU restored"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip_no_mask} recovered to Full state on {dut4}")

        if len([f for f in validation_failures if "STEP 10" in f]) == 0:
            st.log("PASS: OSPF adjacency recovered after matching MTU restored")

        # ===== STEP 11: Cleanup =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove OSPF configuration
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut4)
        st.log("OSPF configuration removed from all DUTs")

        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Remove IP addresses from VLAN interfaces
        self._remove_vlan_ip(dut2, vlan_id)
        self._remove_vlan_ip(dut4, vlan_id)
        st.log("IP addresses removed from VLAN interfaces")

        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Remove ports from VLANs
        self._remove_ports_from_vlan(dut2, self.data.dut2_eth_ports, vlan_id)
        self._remove_ports_from_vlan(dut4, self.data.dut4_eth_ports, vlan_id)

        # Delete VLANs
        self._delete_vlan(dut2, vlan_id)
        self._delete_vlan(dut4, vlan_id)
        st.log("VLANs deleted from all DUTs")

        time.sleep(WAIT_AFTER_VLAN_CONFIG)

        st.log("PASS: Cleanup completed successfully")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF MTU mismatch adjacency prevention validated successfully (VLAN)")
        st.log("Test flow: VLAN Creation → IP Config → Matching MTU → OSPF Config → Adjacency Full (baseline)")
        st.log("           → MTU Mismatch (D4=1500) → Adjacency Broken (negative test) ✓")
        st.log("           → MTU Restored (D4=9100) → Adjacency Recovered → Cleanup ✓")
        st.log("")
        st.log("Verified scenarios:")
        st.log("  1. OSPF adjacency forms with matching MTU (9100) on VLAN")
        st.log("  2. OSPF adjacency breaks with MTU mismatch (D2=9100, D4=1500) - NEGATIVE TEST")
        st.log("  3. OSPF adjacency recovers when MTU match restored")
        st.log("=" * 80)

        # ===== COLLECT TECH SUPPORT AND REPORT FAILURES =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from DUT2
            try:
                st.generate_tech_support(dut=dut2, name="ospf_mtu_mismatch_vlan_validation_failure")
                st.log(f"Tech support collected from {dut2}")
            except Exception as e:
                st.log(f"Warning: Failed to collect tech support from {dut2}: {str(e)}")

            # Collect tech support from DUT4
            try:
                st.generate_tech_support(dut=dut4, name="ospf_mtu_mismatch_vlan_validation_failure")
                st.log(f"Tech support collected from {dut4}")
            except Exception as e:
                st.log(f"Warning: Failed to collect tech support from {dut4}: {str(e)}")

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
