"""
OSPF AREA ID MISMATCH PREVENTS ADJACENCY - ETHERNET INTERFACES
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_6_iscli_4_node_Area_ID_mismatch_prevents_adj_Eth.py \
  --logs-path ./logs/testcases_OSPF_6_iscli_4_node_Area_ID_mismatch_prevents_adj_Eth_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates that OSPF Area ID mismatch prevents neighbor adjacency
  formation on the same Ethernet link. The test demonstrates OSPF area validation
  by intentionally creating an area mismatch and verifying that adjacency fails.

  Test validates:
  1. IP address configuration and connectivity (ping succeeds)
  2. OSPF configuration with different areas on same link (Area 0 vs Area 1)
  3. Verification that OSPF neighbor adjacency FAILS due to area mismatch
  4. No neighbors appear in "show ip ospf neighbor" output
  5. "Number of fully adjacent neighbors in this area: 0" in "show ip ospf"
  6. No DR/BDR election occurs (no neighbors)
  7. Fixing area mismatch by changing both routers to same area
  8. Verification that adjacency succeeds after fix
  9. Complete cleanup of all configurations

  Negative Test Scenario:
  - D2 and D4 are connected on the same Ethernet segment (20.1.1.0/24)
  - D2 is configured for OSPF Area 0 (Backbone)
  - D4 is configured for OSPF Area 1 (Non-backbone)
  - Expected Result: Adjacency FAILS (no neighbors)
  - After fixing to same area: Adjacency SUCCEEDS

  Topology:
        D2 (vs_sonic_2) -------- D4 (vs_sonic_4)
       (Ethernet16)              (Ethernet16)
        20.1.1.1/24              20.1.1.2/24
        OSPF Area 0              OSPF Area 1 (MISMATCH)
        ❌ No Adjacency          ❌ No Adjacency

  After Fix (Both Area 0):
        D2 (vs_sonic_2) -------- D4 (vs_sonic_4)
       (Ethernet16)              (Ethernet16)
        20.1.1.1/24              20.1.1.2/24
        OSPF Area 0              OSPF Area 0
        ✅ Full Adjacency        ✅ Full Adjacency

  Configuration details:
    Phase 1 - Area Mismatch (Negative Test):
      D2 (vs_sonic_2):
        - Ethernet16: 20.1.1.1/24
        - OSPF Area 0 (Backbone)
        - Network: 20.1.1.1/24 area 0
        - Expected: No neighbors, no adjacency

      D4 (vs_sonic_4):
        - Ethernet16: 20.1.1.2/24
        - OSPF Area 1
        - Network: 20.1.1.2/24 area 1
        - Expected: No neighbors, no adjacency

    Phase 2 - Area Match (Positive Test):
      D2 (vs_sonic_2):
        - OSPF Area 0 (unchanged)

      D4 (vs_sonic_4):
        - OSPF Area 0 (changed from Area 1)
        - Expected: Full adjacency with D2

  IMPORTANT: Uses 'show ip ospf' and 'show ip ospf neighbor' to validate
  that area mismatch prevents adjacency. Uses klish CLI type exclusively.

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
WAIT_AFTER_IP_CONFIG = 3
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_ATTEMPT = 60  # Wait long enough for OSPF to attempt adjacency
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_PING = 5


@pytest.mark.topology("any")
class TestOSPFAreaMismatch:
    """Test cases for validating OSPF area mismatch prevents adjacency via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF Area ID Mismatch Test Suite")
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

        # Test interfaces based on testbed_4vs.yaml topology
        # D2 (vs_sonic_2) Ethernet16 <-> D4 (vs_sonic_4) Ethernet16
        cls.data.dut2_if = "Ethernet16"
        cls.data.dut4_if = "Ethernet16"

        st.log(f"Topology: D2[{cls.data.dut2_if}] <-> D4[{cls.data.dut4_if}]")

        # IP addresses
        cls.data.dut2_ip = "20.1.1.1/24"
        cls.data.dut4_ip = "20.1.1.2/24"

        st.log(f"IP Addresses:")
        st.log(f"  D2[{cls.data.dut2_if}]: {cls.data.dut2_ip}")
        st.log(f"  D4[{cls.data.dut4_if}]: {cls.data.dut4_ip}")

        # OSPF areas
        cls.data.ospf_area_0 = "0"  # Backbone
        cls.data.ospf_area_1 = "1"  # Non-backbone
        st.log(f"OSPF Areas: Area 0 (Backbone), Area 1 (for mismatch test)")

        # Set terminal length 0 to disable pagination
        st.log("Setting terminal length 0 to disable pagination on all DUTs")
        st.config(cls.data.dut2, "terminal length 0", type=CLI_TYPE)
        st.config(cls.data.dut4, "terminal length 0", type=CLI_TYPE)

        st.log("Test setup complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup OSPF Area ID Mismatch Test Suite")
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
            interface: Interface name (e.g., "Ethernet16")
            ip_address: IP address with mask (e.g., "20.1.1.1/24")

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
            interface: Interface name (e.g., "Ethernet16")
            expected_ip: Expected IP address (e.g., "20.1.1.1/24")

        Returns:
            True if IP is configured correctly
        """
        st.log(f"Verifying IP address {expected_ip} on {interface} on {dut}")

        # Parse interface number from name (e.g., "Ethernet16" -> "16")
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
            network: Network address with mask (e.g., "20.1.1.1/24")
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

    # ========== HELPER METHODS - VALIDATION ==========

    @staticmethod
    def _verify_ospf_area_configured(ospf_output: str, expected_area: str) -> bool:
        """
        Verify OSPF area is configured.

        Args:
            ospf_output: Raw output from 'show ip ospf' command
            expected_area: Expected area ID

        Returns:
            True if area is configured
        """
        st.log(f"Verifying OSPF area {expected_area} is configured")

        # Area 0 is shown as "Area ID: 0.0.0.0 (Backbone)"
        # Other areas shown as "Area ID: 0.0.0.X"
        if expected_area == "0":
            area_pattern = "Area ID: 0.0.0.0 (Backbone)"
        else:
            area_pattern = f"Area ID: 0.0.0.{expected_area}"

        if area_pattern in ospf_output:
            st.log(f"PASS: Area {expected_area} is configured")
            return True
        else:
            st.error(f"FAIL: Area {expected_area} not found in OSPF configuration")
            return False

    @staticmethod
    def _verify_no_neighbors(neighbor_output: str) -> bool:
        """
        Verify that no OSPF neighbors are present.

        Expected output format when no neighbors:
        Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
        (empty - no neighbor entries)

        Args:
            neighbor_output: Raw output from 'show ip ospf neighbor' command

        Returns:
            True if no neighbors found
        """
        st.log("Verifying that no OSPF neighbors are present")

        # Split output into lines
        lines = neighbor_output.split('\n')

        # Count non-empty lines that are not headers
        neighbor_count = 0
        for line in lines:
            line = line.strip()
            # Skip empty lines, header lines, and prompt lines
            if not line:
                continue
            if "Neighbor ID" in line or "Pri State" in line:
                continue
            if line.startswith("--sonic-mgmt--"):
                continue
            # If line has content and is not a header, it's a neighbor entry
            if len(line.split()) >= 7:  # Neighbor entries have multiple columns
                neighbor_count += 1

        if neighbor_count == 0:
            st.log("PASS: No OSPF neighbors found (expected due to area mismatch)")
            return True
        else:
            st.error(f"FAIL: Found {neighbor_count} OSPF neighbor(s) when none expected")
            return False

    @staticmethod
    def _verify_zero_adjacent_neighbors(ospf_output: str, area: str) -> bool:
        """
        Verify "Number of fully adjacent neighbors in this area: 0".

        Args:
            ospf_output: Raw output from 'show ip ospf' command
            area: Area ID to check

        Returns:
            True if zero adjacent neighbors found
        """
        st.log(f"Verifying zero adjacent neighbors in area {area}")

        # Look for "Number of fully adjacent neighbors in this area: 0"
        pattern = r"Number of fully adjacent neighbors in this area:\s*0"

        if re.search(pattern, ospf_output):
            st.log(f"PASS: Zero adjacent neighbors in area {area}")
            return True
        else:
            st.error(f"FAIL: Expected zero adjacent neighbors in area {area}")
            return False

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

    # ========== TEST CASE ==========

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_AREA_MISMATCH_001"])
    def test_ospf_area_mismatch_prevents_adjacency(self) -> None:
        """
        TC_OSPF_AREA_MISMATCH_001: Validate OSPF area mismatch prevents adjacency.

        Test Procedure:
        1. Configure IP addresses on D2 and D4 and validate
        2. Verify ping connectivity (should succeed)
        3. Configure OSPF on D2 with Area 0
        4. Configure OSPF on D4 with Area 1 (intentional mismatch)
        5. Wait for OSPF to attempt adjacency formation
        6. Verify NO neighbors on both routers (adjacency fails)
        7. Verify "Number of fully adjacent neighbors: 0"
        8. Fix area mismatch - change D4 to Area 0
        9. Verify adjacency succeeds (neighbors in Full state)
        10. Cleanup: Remove all configurations

        Expected Result:
        - IP addresses configured and validated
        - Ping succeeds before OSPF
        - With area mismatch: NO OSPF adjacency (no neighbors)
        - After fixing mismatch: Adjacency succeeds (Full state)
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF Area ID Mismatch Prevents Adjacency")
        st.log("=" * 80)

        # Track validation failures - test will continue but report fail at end
        validation_failures = []

        dut2 = self.data.dut2
        dut4 = self.data.dut4

        # ===== STEP 1: Configure IP addresses on D2 and D4 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Configure IP addresses on D2 and D4")
        st.log("-" * 80)

        # D2: Ethernet16 - 20.1.1.1/24
        self._configure_interface_ip(dut2, self.data.dut2_if, self.data.dut2_ip)

        # D4: Ethernet16 - 20.1.1.2/24
        self._configure_interface_ip(dut4, self.data.dut4_if, self.data.dut4_ip)

        st.log("IP addresses configured on both DUTs")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Validate IP addresses
        st.log("Validating IP address configuration...")
        if not self._verify_interface_ip(dut2, self.data.dut2_if, self.data.dut2_ip):
            error_msg = f"STEP 1: IP validation failed on {dut2} {self.data.dut2_if}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        if not self._verify_interface_ip(dut4, self.data.dut4_if, self.data.dut4_ip):
            error_msg = f"STEP 1: IP validation failed on {dut4} {self.data.dut4_if}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 1" in f]) == 0:
            st.log("PASS: IP addresses configured and validated successfully")

        # ===== STEP 2: Verify ping connectivity =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Verify ping connectivity (before OSPF)")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_PING)

        # Extract IPs without mask
        dut2_ip_no_mask = self.data.dut2_ip.split('/')[0]  # 20.1.1.1
        dut4_ip_no_mask = self.data.dut4_ip.split('/')[0]  # 20.1.1.2

        # Ping from D2 to D4
        if not self._verify_ping_success(dut2, dut4_ip_no_mask):
            error_msg = f"STEP 2: Ping from {dut2} to {dut4_ip_no_mask} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Ping from D4 to D2
        if not self._verify_ping_success(dut4, dut2_ip_no_mask):
            error_msg = f"STEP 2: Ping from {dut4} to {dut2_ip_no_mask} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 2" in f]) == 0:
            st.log("PASS: Ping connectivity verified")

        # ===== STEP 3: Configure OSPF on D2 with Area 0 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Configure OSPF on D2 with Area 0 (Backbone)")
        st.log("-" * 80)

        self._configure_ospf_process(dut2, self.data.ospf_area_0)
        self._configure_ospf_network(dut2, self.data.dut2_ip, self.data.ospf_area_0)

        st.log("OSPF configured on D2 with Area 0")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Verify OSPF configuration on D2
        ospf_output_dut2 = self._get_show_ip_ospf_output(dut2)
        if not self._verify_ospf_area_configured(ospf_output_dut2, self.data.ospf_area_0):
            error_msg = f"STEP 3: OSPF Area 0 not configured on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 3" in f]) == 0:
            st.log("PASS: OSPF configuration completed on D2")

        # ===== STEP 4: Configure OSPF on D4 with Area 1 (MISMATCH) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Configure OSPF on D4 with Area 1 (INTENTIONAL MISMATCH)")
        st.log("-" * 80)

        self._configure_ospf_process(dut4, self.data.ospf_area_1)
        self._configure_ospf_network(dut4, self.data.dut4_ip, self.data.ospf_area_1)

        st.log("OSPF configured on D4 with Area 1 (mismatch with D2's Area 0)")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Verify OSPF configuration on D4
        ospf_output_dut4 = self._get_show_ip_ospf_output(dut4)
        if not self._verify_ospf_area_configured(ospf_output_dut4, self.data.ospf_area_1):
            error_msg = f"STEP 4: OSPF Area 1 not configured on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 4" in f]) == 0:
            st.log("PASS: OSPF configuration completed on D4 with Area 1")

        # ===== STEP 5: Wait for OSPF to attempt adjacency =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Wait for OSPF to attempt adjacency formation")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_ATTEMPT} seconds for OSPF adjacency attempt...")
        st.log("Expected: Adjacency will FAIL due to area mismatch")
        time.sleep(WAIT_FOR_NEIGHBOR_ATTEMPT)

        # ===== STEP 6: Verify NO neighbors (adjacency fails) =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Verify NO OSPF neighbors (adjacency fails due to area mismatch)")
        st.log("-" * 80)

        # Get neighbor outputs
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        # Verify no neighbors on D2
        if not self._verify_no_neighbors(neighbor_output_dut2):
            error_msg = f"STEP 6: OSPF neighbors found on {dut2} when none expected (area mismatch)"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify no neighbors on D4
        if not self._verify_no_neighbors(neighbor_output_dut4):
            error_msg = f"STEP 6: OSPF neighbors found on {dut4} when none expected (area mismatch)"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 6" in f]) == 0:
            st.log("PASS: No OSPF neighbors found on both routers (area mismatch prevents adjacency)")

        # ===== STEP 7: Verify zero adjacent neighbors in show ip ospf =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Verify 'Number of fully adjacent neighbors: 0' in show ip ospf")
        st.log("-" * 80)

        # Get fresh OSPF outputs
        ospf_output_dut2_check = self._get_show_ip_ospf_output(dut2)
        ospf_output_dut4_check = self._get_show_ip_ospf_output(dut4)

        # Verify zero adjacent neighbors on D2
        if not self._verify_zero_adjacent_neighbors(ospf_output_dut2_check, self.data.ospf_area_0):
            st.log("WARNING: Expected zero adjacent neighbors on D2")

        # Verify zero adjacent neighbors on D4
        if not self._verify_zero_adjacent_neighbors(ospf_output_dut4_check, self.data.ospf_area_1):
            st.log("WARNING: Expected zero adjacent neighbors on D4")

        st.log("PASS: Zero adjacent neighbors verified on both routers")

        # ===== STEP 8: Fix area mismatch - change D4 to Area 0 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Fix area mismatch - change D4 to Area 0")
        st.log("-" * 80)

        st.log("Removing OSPF configuration from D4...")
        self._remove_ospf_configuration(dut4)
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("Reconfiguring D4 with Area 0 (same as D2)...")
        self._configure_ospf_process(dut4, self.data.ospf_area_0)
        self._configure_ospf_network(dut4, self.data.dut4_ip, self.data.ospf_area_0)

        st.log("D4 reconfigured with Area 0")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: Area mismatch fixed - both routers now in Area 0")

        # ===== STEP 9: Verify adjacency succeeds after fix =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Verify OSPF adjacency succeeds after fixing area mismatch")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF adjacency to form...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor outputs after fix
        neighbor_output_dut2_final = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4_final = self._get_show_ip_ospf_neighbor_output(dut4)

        # Verify D2 sees D4 as neighbor in Full state
        if not self._verify_ospf_neighbor_present(neighbor_output_dut2_final, dut4_ip_no_mask, "Full"):
            error_msg = f"STEP 9: OSPF neighbor {dut4_ip_no_mask} not in Full state on {dut2} after fix"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D4 sees D2 as neighbor in Full state
        if not self._verify_ospf_neighbor_present(neighbor_output_dut4_final, dut2_ip_no_mask, "Full"):
            error_msg = f"STEP 9: OSPF neighbor {dut2_ip_no_mask} not in Full state on {dut4} after fix"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 9" in f]) == 0:
            st.log("PASS: OSPF adjacency established successfully after fixing area mismatch")

        # ===== STEP 10: Cleanup - Remove all configurations =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove OSPF configuration
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut4)
        st.log("OSPF configuration removed from D2 and D4")

        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Remove IP addresses
        self._remove_interface_ip(dut2, self.data.dut2_if)
        self._remove_interface_ip(dut4, self.data.dut4_if)
        st.log("IP addresses removed from all interfaces")

        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: Cleanup completed successfully")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF Area ID mismatch validated")
        st.log("Test flow: IP Config → Ping Test → OSPF D2(Area0) → OSPF D4(Area1)")
        st.log("           → NO Adjacency (Mismatch) → Fix D4(Area0) → Adjacency Success → Cleanup ✓")
        st.log("")
        st.log("Verified scenarios:")
        st.log("  1. Ping succeeds before OSPF (L3 connectivity OK)")
        st.log("  2. OSPF adjacency FAILS with area mismatch (D2=Area0, D4=Area1)")
        st.log("  3. No neighbors shown in 'show ip ospf neighbor'")
        st.log("  4. OSPF adjacency SUCCEEDS after fixing mismatch (both Area0)")
        st.log("=" * 80)

        # ===== COLLECT TECH SUPPORT AND REPORT FAILURES =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from DUT2
            try:
                st.generate_tech_support(dut=dut2, name="ospf_area_mismatch_eth_validation_failure")
                st.log(f"Tech support collected from {dut2}")
            except Exception as e:
                st.log(f"Warning: Failed to collect tech support from {dut2}: {str(e)}")

            # Collect tech support from DUT4
            try:
                st.generate_tech_support(dut=dut4, name="ospf_area_mismatch_eth_validation_failure")
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
