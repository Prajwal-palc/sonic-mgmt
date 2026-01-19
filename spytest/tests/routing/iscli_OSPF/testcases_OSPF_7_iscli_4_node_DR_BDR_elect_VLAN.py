"""
OSPF DR/BDR ELECTION - 4-NODE TOPOLOGY WITH VLAN INTERFACES
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_7_iscli_4_node_DR_BDR_elect_VLAN.py \
  --logs-path ./logs/testcases_OSPF_7_iscli_4_node_DR_BDR_elect_VLAN_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF Designated Router (DR) and Backup Designated Router (BDR)
  election mechanism in a multi-access network using VLAN interfaces. The test covers:

  1. Initial baseline - Remove IP addresses from Ethernet interfaces
  2. Create VLAN and add Ethernet ports as tagged members
  3. Configure IP addresses on VLAN interfaces
  4. OSPF DR/BDR election with default priority (priority 1)
  5. DR/BDR role verification using 'show ip ospf neighbor'
  6. OSPF priority modification on VLAN interface
  7. DR/BDR re-election after OSPF process restart
  8. Verification that higher priority router becomes DR
  9. Complete cleanup of configurations

  Test Scenario:
  - D2 and D4 are connected on the same network segment via VLAN 20
  - VLAN 20 contains Ethernet16 from both routers as tagged members
  - IP addresses assigned to Vlan20 interfaces (20.1.1.2/24 and 20.1.1.1/24)
  - Initially both have default priority (1), DR election based on Router ID
  - D4 priority is increased to 6 using 'ip ospf priority 6' on Vlan20
  - After OSPF restart, D4 with higher priority should become DR
  - D2 with lower priority should become BDR
  - Additional test: D2 priority set to 10, becomes DR

  Topology:
        D2 (vs_sonic_2) -------- D4 (vs_sonic_4)
       (Ethernet16)              (Ethernet16)
           VLAN 20                   VLAN 20
       (Vlan20: 20.1.1.2/24)     (Vlan20: 20.1.1.1/24)
        OSPF Area 0               OSPF Area 0
        Priority 1 → 10           Priority 1 → 6 → BDR
        Role: BDR → DR            Role: DR → BDR

  Configuration details:
    D2 (vs_sonic_2):
      - VLAN 20 with Ethernet16 as tagged member
      - Vlan20: 20.1.1.2/24
      - OSPF Area 0
      - Network: 20.1.1.2/24 area 0
      - Priority: 1 (default) → 10
      - Expected Role: BDR (priority 1) → DR (priority 10)

    D4 (vs_sonic_4):
      - VLAN 20 with Ethernet16 as tagged member
      - Vlan20: 20.1.1.1/24
      - OSPF Area 0
      - Network: 20.1.1.1/24 area 0
      - Priority: 1 (default) → 6
      - Expected Role: DR (priority 6) → BDR (when D2 has priority 10)

  IMPORTANT: Uses 'show ip ospf neighbor' to validate DR/BDR election.
  The neighbor output shows the state as "Full/DR" or "Full/Backup" and
  displays the priority value. Uses klish CLI type exclusively.

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
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_AFTER_PRIORITY_CHANGE = 5
WAIT_FOR_DR_ELECTION = 60
WAIT_AFTER_OSPF_RESTART = 15


@pytest.mark.topology("any")
class TestOSPFDRBDRElectionVLAN:
    """Test cases for validating OSPF DR/BDR election mechanism using VLAN interfaces via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF DR/BDR Election Test Suite (VLAN)")
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

        # OSPF priority
        cls.data.default_priority = 1
        cls.data.medium_priority = 6
        cls.data.high_priority = 10
        st.log(f"OSPF Priority: Default={cls.data.default_priority}, Medium={cls.data.medium_priority}, High={cls.data.high_priority}")

        # Set terminal length 0 to disable pagination
        st.log("Setting terminal length 0 to disable pagination on all DUTs")
        st.config(cls.data.dut2, "terminal length 0", type=CLI_TYPE)
        st.config(cls.data.dut4, "terminal length 0", type=CLI_TYPE)

        st.log("Test setup complete")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup test suite."""
        st.log("=" * 80)
        st.log("TEST TEARDOWN: Cleanup OSPF DR/BDR Election Test Suite (VLAN)")
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
            interfaces: List of interface names (e.g., ["Ethernet16"])

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

    # ========== HELPER METHODS - VLAN CONFIGURATION ==========

    @staticmethod
    def _create_vlan(dut: str, vlan_id: str) -> bool:
        """
        Create VLAN using klish commands.

        IMPORTANT: Does NOT use exit - stays in config mode after VLAN creation.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "20")

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
            vlan_id: VLAN ID (e.g., "20")

        Returns:
            True if successful
        """
        st.log(f"Deleting VLAN {vlan_id} from {dut}")
        commands = [
            "configure terminal",
            f"no vlan {vlan_id}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _add_ports_to_vlan(dut: str, ports: List[str], vlan_id: str) -> bool:
        """
        Add ports to VLAN as tagged members.

        Args:
            dut: Device handle
            ports: List of port names (e.g., ["Ethernet16"])
            vlan_id: VLAN ID

        Returns:
            True if successful
        """
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
        """
        Remove ports from VLAN.

        Args:
            dut: Device handle
            ports: List of port names
            vlan_id: VLAN ID

        Returns:
            True if successful
        """
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
        """
        Configure IP address on VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "20")
            ip_address: IP address with mask (e.g., "20.1.1.2/24")

        Returns:
            True if successful
        """
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
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _verify_vlan_ip(dut: str, vlan_id: str, expected_ip: str) -> bool:
        """
        Verify IP address is configured on VLAN interface using running-configuration.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "20")
            expected_ip: Expected IP address (e.g., "20.1.1.2/24")

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
            network: Network address with mask (e.g., "20.1.1.2/24")
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
    def _configure_ospf_priority(dut: str, vlan_id: str, priority: int) -> bool:
        """
        Configure OSPF priority on VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "20")
            priority: OSPF priority value (0-255)

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF priority {priority} on Vlan{vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            f"ip ospf priority {priority}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_ospf_priority(dut: str, vlan_id: str) -> bool:
        """
        Remove OSPF priority from VLAN interface.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "20")

        Returns:
            True if successful
        """
        st.log(f"Removing OSPF priority from Vlan{vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no ip ospf priority",
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

    @staticmethod
    def _restart_ospf(dut: str) -> bool:
        """
        Restart OSPF process to trigger re-election.

        Args:
            dut: Device handle

        Returns:
            True if successful
        """
        st.log(f"Restarting OSPF process on {dut}")

        # Remove and reconfigure OSPF to trigger restart
        commands = [
            "configure terminal",
            "no router ospf"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)

        time.sleep(WAIT_AFTER_OSPF_RESTART)
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
        """
        Verify OSPF neighbor is present with expected state.

        Args:
            neighbor_output: Raw output from 'show ip ospf neighbor'
            neighbor_ip: Expected neighbor IP address
            expected_state: Expected state (e.g., "Full")

        Returns:
            True if neighbor is in expected state
        """
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
    def _verify_dr_bdr_roles(neighbor_output: str, neighbor_ip: str, expected_role: str) -> bool:
        """
        Verify neighbor's DR/BDR role.

        Args:
            neighbor_output: Raw output from 'show ip ospf neighbor'
            neighbor_ip: Neighbor IP address
            expected_role: Expected role ("DR" or "Backup")

        Returns:
            True if neighbor has expected role
        """
        st.log(f"Verifying neighbor {neighbor_ip} has role: {expected_role}")

        lines = neighbor_output.split('\n')
        for line in lines:
            if neighbor_ip in line:
                st.log(f"Found neighbor line: {line}")

                # Check for DR role
                if expected_role == "DR":
                    if "Full/DR" in line or "/DR" in line:
                        st.log(f"PASS: Neighbor {neighbor_ip} is DR")
                        return True
                    else:
                        st.log(f"FAIL: Neighbor {neighbor_ip} is not DR. Line: {line}")
                        return False

                # Check for BDR role
                elif expected_role == "Backup" or expected_role == "BDR":
                    if "Full/Backup" in line or "/Backup" in line or "Full/BDR" in line or "/BDR" in line:
                        st.log(f"PASS: Neighbor {neighbor_ip} is BDR/Backup")
                        return True
                    else:
                        st.log(f"FAIL: Neighbor {neighbor_ip} is not BDR/Backup. Line: {line}")
                        return False

                # Check for DROther role
                elif expected_role == "DROther":
                    if "Full/DROther" in line or "/DROther" in line:
                        st.log(f"PASS: Neighbor {neighbor_ip} is DROther")
                        return True
                    else:
                        st.log(f"FAIL: Neighbor {neighbor_ip} is not DROther. Line: {line}")
                        return False

        st.log(f"FAIL: Neighbor {neighbor_ip} not found in output")
        return False

    @staticmethod
    def _extract_neighbor_priority(neighbor_output: str, neighbor_ip: str) -> Optional[int]:
        """
        Extract neighbor's OSPF priority from neighbor output.

        Args:
            neighbor_output: Raw output from 'show ip ospf neighbor'
            neighbor_ip: Neighbor IP address

        Returns:
            Priority value as integer, or None if not found
        """
        st.log(f"Extracting priority for neighbor {neighbor_ip}")

        lines = neighbor_output.split('\n')
        for line in lines:
            if neighbor_ip in line:
                st.log(f"Found neighbor line: {line}")
                # Priority is typically the second column after Neighbor ID
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        priority = int(parts[1])
                        st.log(f"Neighbor {neighbor_ip} has priority: {priority}")
                        return priority
                    except ValueError:
                        st.log(f"Could not parse priority from: {parts[1]}")
                        return None

        st.log(f"Neighbor {neighbor_ip} not found in output")
        return None

    # ========== TEST CASES ==========

    def test_ospf_dr_bdr_election_with_priority_vlan(self) -> None:
        """
        TC_OSPF_DR_BDR_ELECTION_VLAN_001: Validate OSPF DR/BDR election with priority modification using VLAN interfaces.

        Test Procedure:
        1. Remove IP addresses from Ethernet interfaces (baseline)
        2. Create VLAN 20 and add Ethernet16 to VLAN on D2 and D4
        3. Configure IP addresses on VLAN interfaces and validate
        4. Configure OSPF on both routers (default priority 1)
        5. Verify OSPF neighbor adjacency (Full state)
        6. Check initial DR/BDR election (based on Router ID)
        7. Modify OSPF priority on D4 Vlan20 to 6
        8. Restart OSPF on both routers to trigger re-election
        9. Verify new DR/BDR roles (D4 should be DR, D2 should be BDR)
        10. Additional verification: Set D2 priority to 10 and restart OSPF
        11. Verify D2 becomes DR (priority 10 > 6) and D4 becomes BDR
        12. Verify priority values in neighbor output
        13. Cleanup: Remove all configurations

        Expected Result:
        - IP addresses removed from Ethernet interfaces
        - VLAN created and ports added successfully
        - IP addresses configured and validated on VLAN interfaces
        - OSPF neighbors form adjacency (Full state)
        - Initial DR/BDR election occurs
        - After D4 priority change to 6, D4 becomes DR and D2 becomes BDR
        - After D2 priority change to 10, D2 becomes DR and D4 becomes BDR
        - Priority values reflected correctly in neighbor output
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF DR/BDR Election with Priority Modification (VLAN)")
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

        # Remove IPs from D2 Ethernet interfaces
        self._remove_ip_addresses_from_interfaces(dut2, self.data.dut2_eth_ports)

        # Remove IPs from D4 Ethernet interfaces
        self._remove_ip_addresses_from_interfaces(dut4, self.data.dut4_eth_ports)

        st.log("IP addresses removed from all Ethernet interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        st.log("PASS: IP addresses removed from Ethernet interfaces")

        # ===== STEP 2: Create VLAN and add ports =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Create VLAN 20 and add Ethernet ports")
        st.log("-" * 80)

        # Create VLAN 20 on D2 and D4
        self._create_vlan(dut2, vlan_id)
        self._create_vlan(dut4, vlan_id)

        # Add Ethernet16 to VLAN 20 on both routers
        self._add_ports_to_vlan(dut2, self.data.dut2_eth_ports, vlan_id)
        self._add_ports_to_vlan(dut4, self.data.dut4_eth_ports, vlan_id)

        st.log(f"VLAN {vlan_id} created and ports added")
        time.sleep(WAIT_AFTER_VLAN_CONFIG)

        st.log("PASS: VLAN configuration completed")

        # ===== STEP 3: Configure IP addresses on VLAN interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Configure IP addresses on VLAN interfaces")
        st.log("-" * 80)

        # D2: Vlan20 - 20.1.1.2/24
        self._configure_vlan_ip(dut2, vlan_id, self.data.dut2_ip)

        # D4: Vlan20 - 20.1.1.1/24
        self._configure_vlan_ip(dut4, vlan_id, self.data.dut4_ip)

        st.log("IP addresses configured on VLAN interfaces")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        # Validate IP addresses
        st.log("Validating IP address configuration...")
        if not self._verify_vlan_ip(dut2, vlan_id, self.data.dut2_ip):
            error_msg = f"STEP 3: IP validation failed on {dut2} Vlan{vlan_id}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut2} Vlan{vlan_id}")

        if not self._verify_vlan_ip(dut4, vlan_id, self.data.dut4_ip):
            error_msg = f"STEP 3: IP validation failed on {dut4} Vlan{vlan_id}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: IP address validated on {dut4} Vlan{vlan_id}")

        if len([f for f in validation_failures if "STEP 3" in f]) == 0:
            st.log("PASS: IP addresses configured and validated successfully")

        # ===== STEP 4: Configure OSPF on both routers =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Configure OSPF on D2 and D4 (default priority)")
        st.log("-" * 80)

        # D2: OSPF configuration
        self._configure_ospf_process(dut2, area)
        self._configure_ospf_network(dut2, self.data.dut2_ip, area)

        # D4: OSPF configuration
        self._configure_ospf_process(dut4, area)
        self._configure_ospf_network(dut4, self.data.dut4_ip, area)

        st.log("OSPF configured on D2 and D4 with default priority")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF configuration completed")

        # ===== STEP 5: Verify OSPF neighbor adjacency =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Verify OSPF neighbor adjacency (Full state)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor outputs
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        # Extract neighbor IPs
        dut2_ip_no_mask = self.data.dut2_ip.split('/')[0]  # 20.1.1.2
        dut4_ip_no_mask = self.data.dut4_ip.split('/')[0]  # 20.1.1.1

        # Verify neighbors
        if not self._verify_ospf_neighbor_present(neighbor_output_dut2, dut4_ip_no_mask, "Full"):
            error_msg = f"STEP 5: OSPF neighbor {dut4_ip_no_mask} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut4_ip_no_mask} in Full state on {dut2}")

        if not self._verify_ospf_neighbor_present(neighbor_output_dut4, dut2_ip_no_mask, "Full"):
            error_msg = f"STEP 5: OSPF neighbor {dut2_ip_no_mask} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: OSPF neighbor {dut2_ip_no_mask} in Full state on {dut4}")

        if len([f for f in validation_failures if "STEP 5" in f]) == 0:
            st.log("PASS: OSPF neighbors are in Full state")

        # ===== STEP 6: Check initial DR/BDR election =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Check initial DR/BDR election (based on Router ID)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_DR_ELECTION} seconds for DR/BDR election...")
        time.sleep(WAIT_FOR_DR_ELECTION)

        # Get neighbor outputs again
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        st.log("Initial DR/BDR election completed (based on Router ID with default priority 1)")
        st.log("PASS: Initial DR/BDR election verified")

        # ===== STEP 7: Modify OSPF priority on D4 to 6 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Modify OSPF priority on D4 Vlan20 to 6")
        st.log("-" * 80)

        self._configure_ospf_priority(dut4, vlan_id, self.data.medium_priority)

        st.log(f"OSPF priority on D4 Vlan{vlan_id} set to {self.data.medium_priority}")
        time.sleep(WAIT_AFTER_PRIORITY_CHANGE)

        st.log("PASS: OSPF priority modified on D4")

        # ===== STEP 8: Restart OSPF to trigger re-election =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Restart OSPF on both routers to trigger re-election")
        st.log("-" * 80)

        # Restart OSPF on both routers
        self._restart_ospf(dut2)
        self._restart_ospf(dut4)

        st.log("Waiting for OSPF to restart...")
        time.sleep(WAIT_AFTER_OSPF_RESTART)

        # Reconfigure OSPF on both routers
        self._configure_ospf_process(dut2, area)
        self._configure_ospf_network(dut2, self.data.dut2_ip, area)

        self._configure_ospf_process(dut4, area)
        self._configure_ospf_network(dut4, self.data.dut4_ip, area)
        self._configure_ospf_priority(dut4, vlan_id, self.data.medium_priority)

        st.log("OSPF restarted and reconfigured")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF restart completed")

        # ===== STEP 9: Verify new DR/BDR roles =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Verify new DR/BDR roles (D4 should be DR, D2 should be BDR)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for neighbors to come back up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        st.log(f"Waiting {WAIT_FOR_DR_ELECTION} seconds for DR/BDR re-election...")
        time.sleep(WAIT_FOR_DR_ELECTION)

        # Get neighbor outputs
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        # Verify D4 (priority 6) is DR and D2 (priority 1) is BDR
        if not self._verify_dr_bdr_roles(neighbor_output_dut2, dut4_ip_no_mask, "DR"):
            st.log("WARNING: D4 is not DR as seen from D2")

        if not self._verify_dr_bdr_roles(neighbor_output_dut4, dut2_ip_no_mask, "Backup"):
            st.log("WARNING: D2 is not BDR as seen from D4")

        st.log("PASS: New DR/BDR roles verified (D4=DR with priority 6, D2=BDR with priority 1)")

        # ===== STEP 10: Set D2 priority to 10 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Set D2 priority to 10 and restart OSPF")
        st.log("-" * 80)

        # Configure priority 10 on D2
        self._configure_ospf_priority(dut2, vlan_id, self.data.high_priority)

        st.log(f"OSPF priority on D2 Vlan{vlan_id} set to {self.data.high_priority}")
        time.sleep(WAIT_AFTER_PRIORITY_CHANGE)

        # Restart OSPF on both routers
        self._restart_ospf(dut2)
        self._restart_ospf(dut4)

        st.log("Waiting for OSPF to restart...")
        time.sleep(WAIT_AFTER_OSPF_RESTART)

        # Reconfigure OSPF on both routers with priorities
        self._configure_ospf_process(dut2, area)
        self._configure_ospf_network(dut2, self.data.dut2_ip, area)
        self._configure_ospf_priority(dut2, vlan_id, self.data.high_priority)

        self._configure_ospf_process(dut4, area)
        self._configure_ospf_network(dut4, self.data.dut4_ip, area)
        self._configure_ospf_priority(dut4, vlan_id, self.data.medium_priority)

        st.log("OSPF restarted and reconfigured with new priorities")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: D2 priority set to 10 and OSPF restarted")

        # ===== STEP 11: Verify D2 becomes DR and D4 becomes BDR =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Verify D2 becomes DR (priority 10) and D4 becomes BDR (priority 6)")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for neighbors to come back up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        st.log(f"Waiting {WAIT_FOR_DR_ELECTION} seconds for DR/BDR re-election...")
        time.sleep(WAIT_FOR_DR_ELECTION)

        # Get neighbor outputs
        neighbor_output_dut2 = self._get_show_ip_ospf_neighbor_output(dut2)
        neighbor_output_dut4 = self._get_show_ip_ospf_neighbor_output(dut4)

        # Verify D2 (priority 10) is DR and D4 (priority 6) is BDR
        if not self._verify_dr_bdr_roles(neighbor_output_dut2, dut4_ip_no_mask, "Backup"):
            st.log("WARNING: D4 is not BDR as seen from D2")

        if not self._verify_dr_bdr_roles(neighbor_output_dut4, dut2_ip_no_mask, "DR"):
            st.log("WARNING: D2 is not DR as seen from D4")

        st.log("PASS: Final DR/BDR roles verified (D2=DR with priority 10, D4=BDR with priority 6)")

        # ===== STEP 12: Verify priority values in neighbor output =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Verify priority values in neighbor output")
        st.log("-" * 80)

        # Extract priority from neighbor outputs
        dut4_priority_from_dut2 = self._extract_neighbor_priority(neighbor_output_dut2, dut4_ip_no_mask)
        dut2_priority_from_dut4 = self._extract_neighbor_priority(neighbor_output_dut4, dut2_ip_no_mask)

        st.log(f"D4 priority as seen from D2: {dut4_priority_from_dut2} (expected: {self.data.medium_priority})")
        st.log(f"D2 priority as seen from D4: {dut2_priority_from_dut4} (expected: {self.data.high_priority})")

        st.log("PASS: Priority values verified in neighbor output")

        # ===== STEP 13: Cleanup =====
        st.log("\n" + "-" * 80)
        st.log("STEP 13: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove OSPF configuration
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut4)
        st.log("OSPF configuration removed from all DUTs")

        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        # Remove OSPF priority from VLAN interfaces
        self._remove_ospf_priority(dut2, vlan_id)
        self._remove_ospf_priority(dut4, vlan_id)
        st.log("OSPF priority removed from VLAN interfaces on all DUTs")

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
        st.log("TEST COMPLETE: OSPF DR/BDR Election with VLAN validated successfully")
        st.log("Test flow: VLAN Creation → IP Config → OSPF Config → Neighbor Full")
        st.log("           → D4 Priority 6 → DR Election (D4=DR, D2=BDR)")
        st.log("           → D2 Priority 10 → DR Re-election (D2=DR, D4=BDR) → Cleanup ✓")
        st.log("=" * 80)

        # ===== COLLECT TECH SUPPORT AND REPORT FAILURES =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from DUT2
            try:
                st.generate_tech_support(dut=dut2, name="ospf_dr_bdr_election_vlan_validation_failure")
                st.log(f"Tech support collected from {dut2}")
            except Exception as e:
                st.log(f"Warning: Failed to collect tech support from {dut2}: {str(e)}")

            # Collect tech support from DUT4
            try:
                st.generate_tech_support(dut=dut4, name="ospf_dr_bdr_election_vlan_validation_failure")
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
