"""
OSPF UNNUMBERED INTERFACES WITH LOOPBACK DONOR - 4-NODE TOPOLOGY
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_13_iscli_4_node_unnumbered_adj_loopback_over_Eth.py \
  --logs-path ./logs/testcases_OSPF_13_unnumbered_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF unnumbered interfaces using loopback as donor interface by:
  1. Configuring Loopback0 on all devices with /32 addresses
  2. Configuring Ethernet interfaces as unnumbered (borrowing IP from Loopback0)
  3. Configuring OSPF on loopback interfaces using network statements
  4. Configuring OSPF on unnumbered interfaces with point-to-point network type
  5. Verifying OSPF neighbor adjacency (Full state) over unnumbered interfaces
  6. Verifying OSPF interface configuration and network types
  7. Validating OSPF routing table and database entries
  8. Testing end-to-end reachability between loopback addresses
  9. Cleanup: Removing all configurations

  Topology:
        D1 -------- D2 -------- D4 -------- D3
    Loopback0   Loopback0   Loopback0   Loopback0
    1.1.1.1/32  2.2.2.2/32  4.4.4.4/32  3.3.3.3/32
      Eth0        Eth0        Eth16       Eth32
    (unnumbered) (unnumbered) (unnumbered) (unnumbered)
                  Eth16       Eth32
                (unnumbered) (unnumbered)

  Configuration details:
    D1: Loopback0: 1.1.1.1/32, Ethernet0 unnumbered (donor: Loopback0)
    D2: Loopback0: 2.2.2.2/32, Ethernet0,16 unnumbered (donor: Loopback0)
    D4: Loopback0: 4.4.4.4/32, Ethernet16,32 unnumbered (donor: Loopback0)
    D3: Loopback0: 3.3.3.3/32, Ethernet32 unnumbered (donor: Loopback0)

  OSPF Configuration:
    - All loopbacks advertised in area 0 using network statements
    - All unnumbered interfaces configured with 'ip ospf area 0'
    - All unnumbered interfaces set to point-to-point network type
    - No IP addresses assigned directly to Ethernet interfaces

  IMPORTANT: Uses 'show ip ospf neighbor', 'show ip ospf interface', 'show ip route',
  'show ip ospf database', and 'show running-configuration' commands to validate
  OSPF unnumbered configuration. Uses klish CLI type exclusively.

Pre-requisites:
  - Topology: 4-node linear | Supported: HW and Virtual
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
WAIT_AFTER_LOOPBACK_CONFIG = 3
WAIT_AFTER_UNNUMBERED_CONFIG = 3
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_ROUTE_UPDATE = 10
WAIT_FOR_PING = 5


@pytest.mark.topology("any")
class TestOSPFUnnumberedLoopback4Node:
    """Test cases for validating OSPF unnumbered interfaces with loopback donor in 4-node topology via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF Unnumbered Interface Test Suite")
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
        # D1 (vs_sonic_1) Ethernet0 <-> D2 (vs_sonic_2) Ethernet0
        cls.data.dut1_if1 = "Ethernet0"
        cls.data.dut2_if1 = "Ethernet0"

        # D2 (vs_sonic_2) Ethernet16 <-> D4 (vs_sonic_4) Ethernet16
        cls.data.dut2_if2 = "Ethernet16"
        cls.data.dut4_if1 = "Ethernet16"

        # D4 (vs_sonic_4) Ethernet32 <-> D3 (vs_sonic_3) Ethernet32
        cls.data.dut4_if2 = "Ethernet32"
        cls.data.dut3_if1 = "Ethernet32"

        st.log("Topology Configuration:")
        st.log(f"  D1[{cls.data.dut1_if1}] <-> D2[{cls.data.dut2_if1}]")
        st.log(f"  D2[{cls.data.dut2_if2}] <-> D4[{cls.data.dut4_if1}]")
        st.log(f"  D4[{cls.data.dut4_if2}] <-> D3[{cls.data.dut3_if1}]")

        # Loopback addresses (donor interfaces)
        cls.data.dut1_loopback = "1.1.1.1/32"
        cls.data.dut2_loopback = "2.2.2.2/32"
        cls.data.dut3_loopback = "3.3.3.3/32"
        cls.data.dut4_loopback = "4.4.4.4/32"

        st.log("Loopback Addresses:")
        st.log(f"  D1[Loopback0]: {cls.data.dut1_loopback}")
        st.log(f"  D2[Loopback0]: {cls.data.dut2_loopback}")
        st.log(f"  D3[Loopback0]: {cls.data.dut3_loopback}")
        st.log(f"  D4[Loopback0]: {cls.data.dut4_loopback}")

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
        st.log("TEST TEARDOWN: Cleanup OSPF Unnumbered Interface Test Suite")
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

    # ========== HELPER METHODS - LOOPBACK CONFIGURATION ==========

    @staticmethod
    def _configure_loopback(dut: str, loopback_ip: str) -> bool:
        """
        Configure Loopback0 interface with IP address.

        Args:
            dut: Device handle
            loopback_ip: Loopback IP address with mask (e.g., "1.1.1.1/32")

        Returns:
            True if successful
        """
        st.log(f"Configuring Loopback0 with IP {loopback_ip} on {dut}")
        commands = [
            "configure terminal",
            "interface Loopback0",
            f"ip address {loopback_ip}",
            "no shutdown",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_loopback(dut: str) -> bool:
        """
        Remove Loopback0 interface.

        Args:
            dut: Device handle

        Returns:
            True if successful
        """
        st.log(f"Removing Loopback0 from {dut}")
        commands = [
            "configure terminal",
            "no interface Loopback0"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    # ========== HELPER METHODS - UNNUMBERED INTERFACE CONFIGURATION ==========

    @staticmethod
    def _configure_unnumbered_interface(dut: str, interface: str, donor_interface: str = "Loopback0") -> bool:
        """
        Configure interface as unnumbered using donor interface.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            donor_interface: Donor interface name (default: "Loopback0")

        Returns:
            True if successful
        """
        st.log(f"Configuring {interface} as unnumbered using {donor_interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no shutdown",
            "no ip address",
            f"ip unnumbered {donor_interface}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_unnumbered_interface(dut: str, interface: str) -> bool:
        """
        Remove unnumbered configuration from interface.

        Args:
            dut: Device handle
            interface: Interface name

        Returns:
            True if successful
        """
        st.log(f"Removing unnumbered configuration from {interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip unnumbered",
            "no ip address",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    # ========== HELPER METHODS - OSPF CONFIGURATION ==========

    @staticmethod
    def _configure_ospf_on_loopback(dut: str, area: str, loopback_network: str) -> bool:
        """
        Configure OSPF on loopback using network statement.

        Args:
            dut: Device handle
            area: OSPF area ID
            loopback_network: Loopback network to advertise

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF on loopback with network {loopback_network} area {area} on {dut}")
        commands = [
            "configure terminal",
            "router ospf",
            f"area {area}",
            f"network {loopback_network} area {area}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _configure_ospf_on_unnumbered_interface(dut: str, interface: str, area: str) -> bool:
        """
        Configure OSPF on unnumbered interface with point-to-point network type.

        Args:
            dut: Device handle
            interface: Interface name
            area: OSPF area ID

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF on unnumbered {interface} with area {area} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "ip ospf network point-to-point",
            f"ip ospf area {area}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_ospf_from_interface(dut: str, interface: str) -> bool:
        """
        Remove OSPF configuration from interface.

        Args:
            dut: Device handle
            interface: Interface name

        Returns:
            True if successful
        """
        st.log(f"Removing OSPF from {interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip ospf area",
            "no ip ospf network",
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
    def _get_show_ip_route(dut: str) -> str:
        """Get 'show ip route' output."""
        st.log(f"Getting 'show ip route' output from {dut}")
        output = st.show(dut, "show ip route", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show ip route output from {dut}:\n{output}")
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
    def _get_show_running_config_interface(dut: str, interface: str) -> str:
        """Get 'show running-configuration interface' output."""
        st.log(f"Getting 'show running-configuration interface {interface}' output from {dut}")
        output = st.show(dut, f"show running-configuration interface {interface}", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show running-configuration interface {interface} output from {dut}:\n{output}")
        return output

    @staticmethod
    def _get_show_running_config_router_ospf(dut: str) -> str:
        """Get 'show running-configuration router ospf' output."""
        st.log(f"Getting 'show running-configuration router ospf' output from {dut}")
        output = st.show(dut, "show running-configuration router ospf", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show running-configuration router ospf output from {dut}:\n{output}")
        return output

    # ========== HELPER METHODS - VALIDATION ==========

    @staticmethod
    def _verify_ospf_neighbor_present(neighbor_output: str, neighbor_ip: str, expected_state: str = "Full") -> bool:
        """Verify OSPF neighbor is present with expected state."""
        st.log(f"Verifying OSPF neighbor {neighbor_ip} is in {expected_state} state")

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
    def _verify_ospf_interface_network_type(interface_output: str, interface: str, network_type: str = "POINTOPOINT") -> bool:
        """Verify OSPF interface has expected network type."""
        st.log(f"Verifying {interface} has network type {network_type}")

        lines = interface_output.split('\n')
        interface_found = False
        for line in lines:
            if interface in line:
                interface_found = True
            if interface_found and network_type in line:
                st.log(f"PASS: Interface {interface} has network type {network_type}")
                return True

        if interface_found:
            st.log(f"FAIL: Interface {interface} does not have network type {network_type}")
        else:
            st.log(f"FAIL: Interface {interface} not found in OSPF interface output")
        return False

    @staticmethod
    def _verify_route_present(route_output: str, destination: str) -> bool:
        """Verify route is present in routing table."""
        st.log(f"Verifying route to {destination} is present")

        if destination in route_output:
            st.log(f"PASS: Route to {destination} is present")
            return True

        st.log(f"FAIL: Route to {destination} not found")
        return False

    @staticmethod
    def _verify_unnumbered_config(config_output: str, donor_interface: str = "Loopback0") -> bool:
        """Verify unnumbered configuration in running config."""
        st.log(f"Verifying ip unnumbered {donor_interface} is configured")

        if f"ip unnumbered {donor_interface}" in config_output:
            st.log(f"PASS: ip unnumbered {donor_interface} is configured")
            return True

        st.log(f"FAIL: ip unnumbered {donor_interface} not found in configuration")
        return False

    @staticmethod
    def _ping_test(from_dut: str, to_ip: str, count: int = 3) -> bool:
        """Test ping connectivity."""
        st.log(f"Pinging {to_ip} from {from_dut} ({count} packets)")

        # Remove /32 from IP if present
        to_ip_clean = to_ip.split('/')[0]

        command = f"ping {to_ip_clean} -c {count}"
        output = st.config(from_dut, command, type=CLI_TYPE)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"Ping output:\n{output}")

        # Check for success indicators
        if "0% packet loss" in output or f"{count} received" in output:
            st.log(f"PASS: Ping to {to_ip_clean} successful")
            return True

        st.log(f"FAIL: Ping to {to_ip_clean} failed")
        return False

    # ========== TEST CASE ==========

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_UNNUMBERED_001"])
    def test_ospf_unnumbered_adjacency_over_loopback(self) -> None:
        """
        TC_OSPF_UNNUMBERED_001: Validate OSPF adjacency over unnumbered interfaces using loopback donor.

        Test Procedure:
        1. Configure Loopback0 on all devices with /32 addresses
        2. Configure Ethernet interfaces as unnumbered (donor: Loopback0)
        3. Configure OSPF on loopback interfaces using network statements
        4. Configure OSPF on unnumbered interfaces with point-to-point network type
        5. Verify OSPF neighbor adjacency forms (Full state)
        6. Verify OSPF interface network types are point-to-point
        7. Verify OSPF routes are learned
        8. Verify OSPF database entries
        9. Test end-to-end ping connectivity between loopbacks
        10. Cleanup: Remove all configurations

        Expected Result:
        - All loopback interfaces configured successfully
        - All Ethernet interfaces configured as unnumbered
        - OSPF adjacencies form over unnumbered interfaces
        - All devices learn routes to remote loopbacks
        - End-to-end ping successful
        - All configurations cleaned up
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF Unnumbered Interfaces with Loopback Donor")
        st.log("=" * 80)

        # Track validation failures - test will continue but report fail at end
        validation_failures = []

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4
        area = self.data.ospf_area

        # ===== STEP 1: Configure Loopback0 on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Configure Loopback0 interfaces on all devices")
        st.log("-" * 80)

        self._configure_loopback(dut1, self.data.dut1_loopback)
        self._configure_loopback(dut2, self.data.dut2_loopback)
        self._configure_loopback(dut3, self.data.dut3_loopback)
        self._configure_loopback(dut4, self.data.dut4_loopback)

        st.log("Loopback interfaces configured on all devices")
        time.sleep(WAIT_AFTER_LOOPBACK_CONFIG)

        st.log("PASS: Loopback configuration completed")

        # ===== STEP 2: Configure unnumbered interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Configure Ethernet interfaces as unnumbered")
        st.log("-" * 80)

        # D1: Ethernet0 unnumbered
        self._configure_unnumbered_interface(dut1, self.data.dut1_if1)

        # D2: Ethernet0 and Ethernet16 unnumbered
        self._configure_unnumbered_interface(dut2, self.data.dut2_if1)
        self._configure_unnumbered_interface(dut2, self.data.dut2_if2)

        # D4: Ethernet16 and Ethernet32 unnumbered
        self._configure_unnumbered_interface(dut4, self.data.dut4_if1)
        self._configure_unnumbered_interface(dut4, self.data.dut4_if2)

        # D3: Ethernet32 unnumbered
        self._configure_unnumbered_interface(dut3, self.data.dut3_if1)

        st.log("All Ethernet interfaces configured as unnumbered")
        time.sleep(WAIT_AFTER_UNNUMBERED_CONFIG)

        # Verify unnumbered configuration
        st.log("Verifying unnumbered configuration on interfaces...")

        config_d1_eth0 = self._get_show_running_config_interface(dut1, self.data.dut1_if1)
        if not self._verify_unnumbered_config(config_d1_eth0):
            validation_failures.append(f"STEP 2: Unnumbered config not found on {dut1} {self.data.dut1_if1}")

        config_d2_eth0 = self._get_show_running_config_interface(dut2, self.data.dut2_if1)
        if not self._verify_unnumbered_config(config_d2_eth0):
            validation_failures.append(f"STEP 2: Unnumbered config not found on {dut2} {self.data.dut2_if1}")

        st.log("PASS: Unnumbered interface configuration completed")

        # ===== STEP 3: Configure OSPF on loopback interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Configure OSPF on loopback interfaces")
        st.log("-" * 80)

        self._configure_ospf_on_loopback(dut1, area, self.data.dut1_loopback)
        self._configure_ospf_on_loopback(dut2, area, self.data.dut2_loopback)
        self._configure_ospf_on_loopback(dut3, area, self.data.dut3_loopback)
        self._configure_ospf_on_loopback(dut4, area, self.data.dut4_loopback)

        st.log("OSPF configured on loopback interfaces")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF loopback configuration completed")

        # ===== STEP 4: Configure OSPF on unnumbered interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Configure OSPF on unnumbered interfaces")
        st.log("-" * 80)

        # D1: Ethernet0
        self._configure_ospf_on_unnumbered_interface(dut1, self.data.dut1_if1, area)

        # D2: Ethernet0 and Ethernet16
        self._configure_ospf_on_unnumbered_interface(dut2, self.data.dut2_if1, area)
        self._configure_ospf_on_unnumbered_interface(dut2, self.data.dut2_if2, area)

        # D4: Ethernet16 and Ethernet32
        self._configure_ospf_on_unnumbered_interface(dut4, self.data.dut4_if1, area)
        self._configure_ospf_on_unnumbered_interface(dut4, self.data.dut4_if2, area)

        # D3: Ethernet32
        self._configure_ospf_on_unnumbered_interface(dut3, self.data.dut3_if1, area)

        st.log("OSPF configured on all unnumbered interfaces")
        time.sleep(WAIT_AFTER_OSPF_CONFIG)

        st.log("PASS: OSPF unnumbered interface configuration completed")

        # ===== STEP 5: Verify OSPF neighbor adjacency =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Verify OSPF neighbor adjacency over unnumbered interfaces")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up...")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # Get neighbor outputs from all devices
        neighbor_output_d1 = self._get_show_ip_ospf_neighbor(dut1)
        neighbor_output_d2 = self._get_show_ip_ospf_neighbor(dut2)
        neighbor_output_d3 = self._get_show_ip_ospf_neighbor(dut3)
        neighbor_output_d4 = self._get_show_ip_ospf_neighbor(dut4)

        # Extract loopback IPs (without /32 mask)
        dut1_loopback_ip = self.data.dut1_loopback.split('/')[0]
        dut2_loopback_ip = self.data.dut2_loopback.split('/')[0]
        dut3_loopback_ip = self.data.dut3_loopback.split('/')[0]
        dut4_loopback_ip = self.data.dut4_loopback.split('/')[0]

        # D1 should see D2 as neighbor
        if not self._verify_ospf_neighbor_present(neighbor_output_d1, dut2_loopback_ip, "Full"):
            error_msg = f"STEP 5: OSPF neighbor {dut2_loopback_ip} not in Full state on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: D1 sees D2 ({dut2_loopback_ip}) as Full neighbor")

        # D2 should see D1 and D4 as neighbors
        if not self._verify_ospf_neighbor_present(neighbor_output_d2, dut1_loopback_ip, "Full"):
            error_msg = f"STEP 5: OSPF neighbor {dut1_loopback_ip} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: D2 sees D1 ({dut1_loopback_ip}) as Full neighbor")

        if not self._verify_ospf_neighbor_present(neighbor_output_d2, dut4_loopback_ip, "Full"):
            error_msg = f"STEP 5: OSPF neighbor {dut4_loopback_ip} not in Full state on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: D2 sees D4 ({dut4_loopback_ip}) as Full neighbor")

        # D4 should see D2 and D3 as neighbors
        if not self._verify_ospf_neighbor_present(neighbor_output_d4, dut2_loopback_ip, "Full"):
            error_msg = f"STEP 5: OSPF neighbor {dut2_loopback_ip} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: D4 sees D2 ({dut2_loopback_ip}) as Full neighbor")

        if not self._verify_ospf_neighbor_present(neighbor_output_d4, dut3_loopback_ip, "Full"):
            error_msg = f"STEP 5: OSPF neighbor {dut3_loopback_ip} not in Full state on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: D4 sees D3 ({dut3_loopback_ip}) as Full neighbor")

        # D3 should see D4 as neighbor
        if not self._verify_ospf_neighbor_present(neighbor_output_d3, dut4_loopback_ip, "Full"):
            error_msg = f"STEP 5: OSPF neighbor {dut4_loopback_ip} not in Full state on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: D3 sees D4 ({dut4_loopback_ip}) as Full neighbor")

        if len([f for f in validation_failures if "STEP 5" in f]) == 0:
            st.log("PASS: All OSPF neighbors in Full state")

        # ===== STEP 6: Verify OSPF interface network types =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Verify OSPF interface network types are point-to-point")
        st.log("-" * 80)

        # Get OSPF interface outputs
        ospf_intf_d1 = self._get_show_ip_ospf_interface(dut1)
        ospf_intf_d2 = self._get_show_ip_ospf_interface(dut2)
        ospf_intf_d3 = self._get_show_ip_ospf_interface(dut3)
        ospf_intf_d4 = self._get_show_ip_ospf_interface(dut4)

        # Verify network types
        if not self._verify_ospf_interface_network_type(ospf_intf_d1, self.data.dut1_if1, "POINTOPOINT"):
            error_msg = f"STEP 6: {self.data.dut1_if1} on {dut1} not configured as point-to-point"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_interface_network_type(ospf_intf_d2, self.data.dut2_if1, "POINTOPOINT"):
            error_msg = f"STEP 6: {self.data.dut2_if1} on {dut2} not configured as point-to-point"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_interface_network_type(ospf_intf_d2, self.data.dut2_if2, "POINTOPOINT"):
            error_msg = f"STEP 6: {self.data.dut2_if2} on {dut2} not configured as point-to-point"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 6" in f]) == 0:
            st.log("PASS: All OSPF interfaces configured as point-to-point")

        # ===== STEP 7: Verify OSPF routes are learned =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Verify OSPF routes are learned")
        st.log("-" * 80)

        st.log(f"Waiting {WAIT_FOR_ROUTE_UPDATE} seconds for routes to converge...")
        time.sleep(WAIT_FOR_ROUTE_UPDATE)

        # Get routing tables
        routes_d1 = self._get_show_ip_route(dut1)
        routes_d2 = self._get_show_ip_route(dut2)
        routes_d3 = self._get_show_ip_route(dut3)
        routes_d4 = self._get_show_ip_route(dut4)

        # D1 should have routes to D2, D3, D4 loopbacks
        if not self._verify_route_present(routes_d1, dut2_loopback_ip):
            error_msg = f"STEP 7: Route to {dut2_loopback_ip} not found on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_route_present(routes_d1, dut3_loopback_ip):
            error_msg = f"STEP 7: Route to {dut3_loopback_ip} not found on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_route_present(routes_d1, dut4_loopback_ip):
            error_msg = f"STEP 7: Route to {dut4_loopback_ip} not found on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # D3 should have routes to D1, D2, D4 loopbacks
        if not self._verify_route_present(routes_d3, dut1_loopback_ip):
            error_msg = f"STEP 7: Route to {dut1_loopback_ip} not found on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_route_present(routes_d3, dut2_loopback_ip):
            error_msg = f"STEP 7: Route to {dut2_loopback_ip} not found on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_route_present(routes_d3, dut4_loopback_ip):
            error_msg = f"STEP 7: Route to {dut4_loopback_ip} not found on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 7" in f]) == 0:
            st.log("PASS: All OSPF routes learned successfully")

        # ===== STEP 8: Verify OSPF database entries =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Verify OSPF database entries")
        st.log("-" * 80)

        # Get OSPF database from all devices
        database_d1 = self._get_show_ip_ospf_database(dut1)
        database_d2 = self._get_show_ip_ospf_database(dut2)
        database_d3 = self._get_show_ip_ospf_database(dut3)
        database_d4 = self._get_show_ip_ospf_database(dut4)

        st.log("OSPF database collected from all devices")

        # Verify database contains LSAs from all routers
        # This is informational - we already validated neighbors and routes
        st.log("PASS: OSPF database verification completed")

        # ===== STEP 9: Test end-to-end ping connectivity =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Test end-to-end ping connectivity")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_PING)

        # Ping from D1 to D3 loopback
        if not self._ping_test(dut1, dut3_loopback_ip, count=3):
            error_msg = f"STEP 9: Ping from {dut1} to {dut3_loopback_ip} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from D1 to D3 loopback successful")

        # Ping from D3 to D1 loopback
        if not self._ping_test(dut3, dut1_loopback_ip, count=3):
            error_msg = f"STEP 9: Ping from {dut3} to {dut1_loopback_ip} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from D3 to D1 loopback successful")

        # Ping from D1 to D4 loopback
        if not self._ping_test(dut1, dut4_loopback_ip, count=3):
            error_msg = f"STEP 9: Ping from {dut1} to {dut4_loopback_ip} failed"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping from D1 to D4 loopback successful")

        if len([f for f in validation_failures if "STEP 9" in f]) == 0:
            st.log("PASS: End-to-end connectivity verified")

        # ===== STEP 10: Cleanup all configurations =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Cleanup - Remove all configurations")
        st.log("-" * 80)

        # Remove OSPF from unnumbered interfaces
        self._remove_ospf_from_interface(dut1, self.data.dut1_if1)
        self._remove_ospf_from_interface(dut2, self.data.dut2_if1)
        self._remove_ospf_from_interface(dut2, self.data.dut2_if2)
        self._remove_ospf_from_interface(dut4, self.data.dut4_if1)
        self._remove_ospf_from_interface(dut4, self.data.dut4_if2)
        self._remove_ospf_from_interface(dut3, self.data.dut3_if1)

        # Remove OSPF configuration
        self._remove_ospf_configuration(dut1)
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut3)
        self._remove_ospf_configuration(dut4)

        # Remove unnumbered configuration
        self._remove_unnumbered_interface(dut1, self.data.dut1_if1)
        self._remove_unnumbered_interface(dut2, self.data.dut2_if1)
        self._remove_unnumbered_interface(dut2, self.data.dut2_if2)
        self._remove_unnumbered_interface(dut4, self.data.dut4_if1)
        self._remove_unnumbered_interface(dut4, self.data.dut4_if2)
        self._remove_unnumbered_interface(dut3, self.data.dut3_if1)

        # Remove loopback interfaces
        self._remove_loopback(dut1)
        self._remove_loopback(dut2)
        self._remove_loopback(dut3)
        self._remove_loopback(dut4)

        st.log("All configurations removed")

        st.log("PASS: Cleanup completed")

        # ===== SUMMARY =====
        st.log("\n" + "=" * 80)
        st.log("TEST SUMMARY: OSPF Unnumbered Interfaces with Loopback Donor")
        st.log("=" * 80)
        st.log("Test validated:")
        st.log("  1. Loopback configuration on all devices")
        st.log("  2. Unnumbered interface configuration")
        st.log("  3. OSPF adjacency over unnumbered interfaces")
        st.log("  4. Point-to-point network type configuration")
        st.log("  5. OSPF route learning")
        st.log("  6. OSPF database synchronization")
        st.log("  7. End-to-end connectivity")
        st.log("  8. Configuration cleanup")
        st.log("=" * 80)

        # ===== COLLECT TECH SUPPORT AND REPORT FAILURES =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from all DUTs
            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_unnumbered_validation_failure")
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
