"""
OSPF MD5 AUTHENTICATION - 4-NODE TOPOLOGY WITH ETHERNET INTERFACES
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_9_iscli_4_node_MD5_authentication_over_Eth.py \
  --logs-path ./logs/testcases_OSPF_9_MD5_authentication_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF MD5 authentication mechanism over Ethernet interfaces by:
  1. Configuring IP addresses on 4 parallel links between each device pair
  2. Configuring OSPF with MD5 authentication using different keys per device pair
  3. Verifying OSPF neighbor adjacency reaches Full state with correct authentication
  4. Verifying "Cryptographic authentication enabled" appears in show commands
  5. Testing authentication failure by configuring mismatched MD5 key
  6. Verifying neighbor goes down when authentication fails (Dead timer expires)
  7. Restoring correct MD5 key and verifying neighbor comes back up
  8. Validating routing table updates with authenticated OSPF routes
  9. Cleanup: Removing all configurations

  Topology:
        D1 ======== (4 parallel links) ======== D2 ======== (4 parallel links) ======== D4 ======== (4 parallel links) ======== D3

  MD5 Authentication Keys:
    D1 ↔ D2: sonic123 (on all 4 links: Ethernet0,4,8,12)
    D2 ↔ D4: sonic456 (on all 4 links: Ethernet16,20,24,28)
    D4 ↔ D3: sonic789 (on all 4 links: Ethernet32,36,40,44)

  Configuration details:
    D1: Ethernet0,4,8,12: 10.0.1.1/30, 10.0.2.1/30, 10.0.3.1/30, 10.0.4.1/30
    D2: Ethernet0,4,8,12: 10.0.1.2/30, 10.0.2.2/30, 10.0.3.2/30, 10.0.4.2/30
        Ethernet16,20,24,28: 20.0.1.1/30, 20.0.2.1/30, 20.0.3.1/30, 20.0.4.1/30
    D4: Ethernet16,20,24,28: 20.0.1.2/30, 20.0.2.2/30, 20.0.3.2/30, 20.0.4.2/30
        Ethernet32,36,40,44: 30.0.1.1/30, 30.0.2.1/30, 30.0.3.1/30, 30.0.4.1/30
    D3: Ethernet32,36,40,44: 30.0.1.2/30, 30.0.2.2/30, 30.0.3.2/30, 30.0.4.2/30

  IMPORTANT: Uses 'show ip ospf neighbor', 'show ip ospf interface', 'show ip route ospf',
  and 'show ip ospf database' commands to validate OSPF MD5 authentication. Uses klish CLI type exclusively.

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
WAIT_AFTER_IP_CONFIG = 3
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_AFTER_MD5_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_NEIGHBOR_DOWN = 45  # Wait for dead timer to expire after auth failure
WAIT_FOR_ROUTE_UPDATE = 10
WAIT_FOR_PING = 2


@pytest.mark.topology("any")
class TestOSPFMD5Authentication4Node:
    """Test cases for validating OSPF MD5 authentication in 4-node topology via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF MD5 Authentication Test Suite")
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

        # IP addresses for D1 ↔ D2 links
        cls.data.dut1_d2_ips = ["10.0.1.1/30", "10.0.2.1/30", "10.0.3.1/30", "10.0.4.1/30"]
        cls.data.dut2_d1_ips = ["10.0.1.2/30", "10.0.2.2/30", "10.0.3.2/30", "10.0.4.2/30"]

        # IP addresses for D2 ↔ D4 links
        cls.data.dut2_d4_ips = ["20.0.1.1/30", "20.0.2.1/30", "20.0.3.1/30", "20.0.4.1/30"]
        cls.data.dut4_d2_ips = ["20.0.1.2/30", "20.0.2.2/30", "20.0.3.2/30", "20.0.4.2/30"]

        # IP addresses for D4 ↔ D3 links
        cls.data.dut4_d3_ips = ["30.0.1.1/30", "30.0.2.1/30", "30.0.3.1/30", "30.0.4.1/30"]
        cls.data.dut3_d4_ips = ["30.0.1.2/30", "30.0.2.2/30", "30.0.3.2/30", "30.0.4.2/30"]

        # MD5 authentication keys
        cls.data.md5_key_d1_d2 = "sonic123"
        cls.data.md5_key_d2_d4 = "sonic456"
        cls.data.md5_key_d4_d3 = "sonic789"

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
        st.log("TEST TEARDOWN: Cleanup OSPF MD5 Authentication Test Suite")
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
            ip_address: IP address with mask (e.g., "10.0.1.1/30")

        Returns:
            True if successful
        """
        st.log(f"Configuring IP address {ip_address} on {interface} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no shutdown",
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
    def _configure_ospf_md5_authentication(dut: str, interface: str, key_id: int, md5_key: str) -> bool:
        """
        Configure OSPF MD5 authentication on interface.

        Args:
            dut: Device handle
            interface: Interface name
            key_id: MD5 key ID (typically 1)
            md5_key: MD5 authentication key

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF MD5 authentication on {interface} on {dut} with key {md5_key}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "ip ospf authentication message-digest",
            f"ip ospf message-digest-key {key_id} md5 {md5_key}",
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
    def _get_show_ip_ospf_interface(dut: str, interface: str = "") -> str:
        """Get 'show ip ospf interface' output."""
        command = f"show ip ospf interface {interface}" if interface else "show ip ospf interface"
        st.log(f"Getting '{command}' output from {dut}")
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"{command} output from {dut}:\n{output}")
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
    def _verify_interface_ip(dut: str, interface: str, expected_ip: str) -> bool:
        """
        Verify IP address is configured on interface using running-configuration.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            expected_ip: Expected IP address (e.g., "10.0.1.1/30")

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
    def _verify_ospf_neighbor_full_state(output: str, neighbor_ip: str, interface: str) -> bool:
        """
        Verify that specific OSPF neighbor is in Full state on specific interface.

        Args:
            output: Output from 'show ip ospf neighbor'
            neighbor_ip: Expected neighbor IP
            interface: Interface name

        Returns:
            True if neighbor is in Full state
        """
        st.log(f"Verifying OSPF neighbor {neighbor_ip} on {interface} is in Full state")

        lines = output.split('\n')
        for line in lines:
            if neighbor_ip in line and interface in line and 'Full' in line:
                st.log(f"PASS: Neighbor {neighbor_ip} on {interface} is in Full state")
                return True

        st.error(f"FAIL: Neighbor {neighbor_ip} on {interface} not in Full state or not found")
        return False

    @staticmethod
    def _verify_ospf_neighbor_not_present(output: str, neighbor_ip: str, interface: str) -> bool:
        """
        Verify that specific OSPF neighbor is NOT present (down due to auth failure).

        Args:
            output: Output from 'show ip ospf neighbor'
            neighbor_ip: Neighbor IP that should NOT be present
            interface: Interface name

        Returns:
            True if neighbor is not present
        """
        st.log(f"Verifying OSPF neighbor {neighbor_ip} on {interface} is NOT present (auth failure)")

        lines = output.split('\n')
        for line in lines:
            if neighbor_ip in line and interface in line and 'Full' in line:
                st.error(f"FAIL: Neighbor {neighbor_ip} on {interface} is still present")
                return False

        st.log(f"PASS: Neighbor {neighbor_ip} on {interface} is not present (as expected)")
        return True

    @staticmethod
    def _verify_cryptographic_auth_enabled(output: str, interface: str) -> bool:
        """
        Verify that cryptographic authentication is enabled on interface.

        Args:
            output: Output from 'show ip ospf interface'
            interface: Interface name

        Returns:
            True if cryptographic authentication is enabled
        """
        st.log(f"Verifying cryptographic authentication is enabled on {interface}")

        lines = output.split('\n')
        in_interface_section = False

        for line in lines:
            if interface in line and 'is up' in line:
                in_interface_section = True
            elif in_interface_section:
                if 'Cryptographic authentication enabled' in line:
                    st.log(f"PASS: Cryptographic authentication enabled on {interface}")
                    return True
                elif 'is up' in line and interface not in line:
                    # Started next interface section
                    break

        st.error(f"FAIL: Cryptographic authentication not found on {interface}")
        return False

    @staticmethod
    def _verify_md5_algorithm(output: str, interface: str) -> bool:
        """
        Verify that MD5 algorithm is shown in interface output.

        Args:
            output: Output from 'show ip ospf interface'
            interface: Interface name

        Returns:
            True if MD5 algorithm is shown
        """
        st.log(f"Verifying MD5 algorithm on {interface}")

        lines = output.split('\n')
        in_interface_section = False

        for line in lines:
            if interface in line and 'is up' in line:
                in_interface_section = True
            elif in_interface_section:
                if 'Algorithm:MD5' in line or 'Algorithm: MD5' in line:
                    st.log(f"PASS: MD5 algorithm confirmed on {interface}")
                    return True
                elif 'is up' in line and interface not in line:
                    # Started next interface section
                    break

        st.error(f"FAIL: MD5 algorithm not found on {interface}")
        return False

    @staticmethod
    def _verify_ospf_route_present(output: str, network: str) -> bool:
        """
        Verify OSPF route is present in routing table.

        Args:
            output: Output from 'show ip route ospf'
            network: Network to check (e.g., "30.0.1.0/30")

        Returns:
            True if route is present
        """
        st.log(f"Verifying OSPF route {network} is present")

        if network in output and ('O>' in output or 'O ' in output):
            st.log(f"PASS: OSPF route {network} is present")
            return True
        else:
            st.error(f"FAIL: OSPF route {network} not found")
            return False

    # ========== TEST CASES ==========

    def test_ospf_md5_authentication(self) -> None:
        """
        Test OSPF MD5 authentication functionality.

        Test Steps:
        1. Configure IP addresses on all interfaces
        2. Verify IP configuration
        3. Configure OSPF with MD5 authentication
        4. Verify OSPF neighbors reach Full state
        5. Verify cryptographic authentication is enabled
        6. Verify OSPF routes are learned
        7. Test authentication failure (mismatched key)
        8. Verify neighbor goes down
        9. Restore correct key
        10. Verify neighbor comes back up
        11. Cleanup configuration
        """
        st.log("=" * 80)
        st.log("TEST CASE: OSPF MD5 Authentication")
        st.log("=" * 80)

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4

        validation_failures = []

        # ========== STEP 1: Configure IP addresses on all interfaces ==========
        st.banner("STEP 1: Configuring IP addresses on all interfaces")

        # Configure D1 → D2 links
        st.log(f"Configuring IPs on {dut1} for D1 → D2 links")
        for interface, ip in zip(self.data.dut1_d2_links, self.data.dut1_d2_ips):
            self._configure_interface_ip(dut1, interface, ip)

        # Configure D2 → D1 links
        st.log(f"Configuring IPs on {dut2} for D2 → D1 links")
        for interface, ip in zip(self.data.dut2_d1_links, self.data.dut2_d1_ips):
            self._configure_interface_ip(dut2, interface, ip)

        # Configure D2 → D4 links
        st.log(f"Configuring IPs on {dut2} for D2 → D4 links")
        for interface, ip in zip(self.data.dut2_d4_links, self.data.dut2_d4_ips):
            self._configure_interface_ip(dut2, interface, ip)

        # Configure D4 → D2 links
        st.log(f"Configuring IPs on {dut4} for D4 → D2 links")
        for interface, ip in zip(self.data.dut4_d2_links, self.data.dut4_d2_ips):
            self._configure_interface_ip(dut4, interface, ip)

        # Configure D4 → D3 links
        st.log(f"Configuring IPs on {dut4} for D4 → D3 links")
        for interface, ip in zip(self.data.dut4_d3_links, self.data.dut4_d3_ips):
            self._configure_interface_ip(dut4, interface, ip)

        # Configure D3 → D4 links
        st.log(f"Configuring IPs on {dut3} for D3 → D4 links")
        for interface, ip in zip(self.data.dut3_d4_links, self.data.dut3_d4_ips):
            self._configure_interface_ip(dut3, interface, ip)

        st.log(f"Waiting {WAIT_AFTER_IP_CONFIG} seconds after IP configuration")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        # ========== STEP 2: Verify IP configuration ==========
        st.banner("STEP 2: Verifying IP configuration on all interfaces")

        # Verify D1 IPs
        for interface, ip in zip(self.data.dut1_d2_links, self.data.dut1_d2_ips):
            if not self._verify_interface_ip(dut1, interface, ip):
                error_msg = f"STEP 2: IP validation failed on {dut1} {interface}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D2 IPs (D1 side)
        for interface, ip in zip(self.data.dut2_d1_links, self.data.dut2_d1_ips):
            if not self._verify_interface_ip(dut2, interface, ip):
                error_msg = f"STEP 2: IP validation failed on {dut2} {interface}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D2 IPs (D4 side)
        for interface, ip in zip(self.data.dut2_d4_links, self.data.dut2_d4_ips):
            if not self._verify_interface_ip(dut2, interface, ip):
                error_msg = f"STEP 2: IP validation failed on {dut2} {interface}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D4 IPs (D2 side)
        for interface, ip in zip(self.data.dut4_d2_links, self.data.dut4_d2_ips):
            if not self._verify_interface_ip(dut4, interface, ip):
                error_msg = f"STEP 2: IP validation failed on {dut4} {interface}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D4 IPs (D3 side)
        for interface, ip in zip(self.data.dut4_d3_links, self.data.dut4_d3_ips):
            if not self._verify_interface_ip(dut4, interface, ip):
                error_msg = f"STEP 2: IP validation failed on {dut4} {interface}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D3 IPs
        for interface, ip in zip(self.data.dut3_d4_links, self.data.dut3_d4_ips):
            if not self._verify_interface_ip(dut3, interface, ip):
                error_msg = f"STEP 2: IP validation failed on {dut3} {interface}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 2" in f]) == 0:
            st.log("PASS: All IP addresses configured and verified successfully")

        # ========== STEP 3: Configure OSPF with MD5 authentication ==========
        st.banner("STEP 3: Configuring OSPF with MD5 authentication")

        # Configure OSPF on D1
        st.log(f"Configuring OSPF on {dut1}")
        networks_d1 = ["10.0.1.0/30", "10.0.2.0/30", "10.0.3.0/30", "10.0.4.0/30"]
        self._configure_ospf_process(dut1, self.data.ospf_area, networks_d1)

        # Configure MD5 authentication on D1 interfaces
        for interface in self.data.dut1_d2_links:
            self._configure_ospf_md5_authentication(dut1, interface, 1, self.data.md5_key_d1_d2)

        # Configure OSPF on D2
        st.log(f"Configuring OSPF on {dut2}")
        networks_d2 = ["10.0.1.0/30", "10.0.2.0/30", "10.0.3.0/30", "10.0.4.0/30",
                       "20.0.1.0/30", "20.0.2.0/30", "20.0.3.0/30", "20.0.4.0/30"]
        self._configure_ospf_process(dut2, self.data.ospf_area, networks_d2)

        # Configure MD5 authentication on D2 interfaces (D1 side)
        for interface in self.data.dut2_d1_links:
            self._configure_ospf_md5_authentication(dut2, interface, 1, self.data.md5_key_d1_d2)

        # Configure MD5 authentication on D2 interfaces (D4 side)
        for interface in self.data.dut2_d4_links:
            self._configure_ospf_md5_authentication(dut2, interface, 1, self.data.md5_key_d2_d4)

        # Configure OSPF on D4
        st.log(f"Configuring OSPF on {dut4}")
        networks_d4 = ["20.0.1.0/30", "20.0.2.0/30", "20.0.3.0/30", "20.0.4.0/30",
                       "30.0.1.0/30", "30.0.2.0/30", "30.0.3.0/30", "30.0.4.0/30"]
        self._configure_ospf_process(dut4, self.data.ospf_area, networks_d4)

        # Configure MD5 authentication on D4 interfaces (D2 side)
        for interface in self.data.dut4_d2_links:
            self._configure_ospf_md5_authentication(dut4, interface, 1, self.data.md5_key_d2_d4)

        # Configure MD5 authentication on D4 interfaces (D3 side)
        for interface in self.data.dut4_d3_links:
            self._configure_ospf_md5_authentication(dut4, interface, 1, self.data.md5_key_d4_d3)

        # Configure OSPF on D3
        st.log(f"Configuring OSPF on {dut3}")
        networks_d3 = ["30.0.1.0/30", "30.0.2.0/30", "30.0.3.0/30", "30.0.4.0/30"]
        self._configure_ospf_process(dut3, self.data.ospf_area, networks_d3)

        # Configure MD5 authentication on D3 interfaces
        for interface in self.data.dut3_d4_links:
            self._configure_ospf_md5_authentication(dut3, interface, 1, self.data.md5_key_d4_d3)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # ========== STEP 4: Verify OSPF neighbors reach Full state ==========
        st.banner("STEP 4: Verifying OSPF neighbors reach Full state")

        # Verify D1 neighbors
        output_d1 = self._get_show_ip_ospf_neighbor(dut1)
        if not self._verify_ospf_neighbor_count(output_d1, 4):
            error_msg = f"STEP 4: Expected 4 OSPF neighbors on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify each neighbor individually
        for interface, neighbor_ip in zip(self.data.dut1_d2_links, ["10.0.1.2", "10.0.2.2", "10.0.3.2", "10.0.4.2"]):
            if not self._verify_ospf_neighbor_full_state(output_d1, neighbor_ip, interface):
                error_msg = f"STEP 4: Neighbor {neighbor_ip} on {dut1} {interface} not in Full state"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D2 neighbors
        output_d2 = self._get_show_ip_ospf_neighbor(dut2)
        if not self._verify_ospf_neighbor_count(output_d2, 8):
            error_msg = f"STEP 4: Expected 8 OSPF neighbors on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D4 neighbors
        output_d4 = self._get_show_ip_ospf_neighbor(dut4)
        if not self._verify_ospf_neighbor_count(output_d4, 8):
            error_msg = f"STEP 4: Expected 8 OSPF neighbors on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D3 neighbors
        output_d3 = self._get_show_ip_ospf_neighbor(dut3)
        if not self._verify_ospf_neighbor_count(output_d3, 4):
            error_msg = f"STEP 4: Expected 4 OSPF neighbors on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 4" in f]) == 0:
            st.log("PASS: All OSPF neighbors reached Full state")

        # ========== STEP 5: Verify cryptographic authentication is enabled ==========
        st.banner("STEP 5: Verifying cryptographic authentication is enabled")

        # Check D1 interfaces
        output_intf_d1 = self._get_show_ip_ospf_interface(dut1, "Ethernet0")
        if not self._verify_cryptographic_auth_enabled(output_intf_d1, "Ethernet0"):
            error_msg = f"STEP 5: Cryptographic auth not enabled on {dut1} Ethernet0"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_md5_algorithm(output_intf_d1, "Ethernet0"):
            error_msg = f"STEP 5: MD5 algorithm not shown on {dut1} Ethernet0"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Check D2 interfaces (sample check on Ethernet0 and Ethernet16)
        output_intf_d2_eth0 = self._get_show_ip_ospf_interface(dut2, "Ethernet0")
        if not self._verify_cryptographic_auth_enabled(output_intf_d2_eth0, "Ethernet0"):
            error_msg = f"STEP 5: Cryptographic auth not enabled on {dut2} Ethernet0"
            st.error(error_msg)
            validation_failures.append(error_msg)

        output_intf_d2_eth16 = self._get_show_ip_ospf_interface(dut2, "Ethernet16")
        if not self._verify_cryptographic_auth_enabled(output_intf_d2_eth16, "Ethernet16"):
            error_msg = f"STEP 5: Cryptographic auth not enabled on {dut2} Ethernet16"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Check D4 interfaces (sample check on Ethernet16 and Ethernet32)
        output_intf_d4_eth16 = self._get_show_ip_ospf_interface(dut4, "Ethernet16")
        if not self._verify_cryptographic_auth_enabled(output_intf_d4_eth16, "Ethernet16"):
            error_msg = f"STEP 5: Cryptographic auth not enabled on {dut4} Ethernet16"
            st.error(error_msg)
            validation_failures.append(error_msg)

        output_intf_d4_eth32 = self._get_show_ip_ospf_interface(dut4, "Ethernet32")
        if not self._verify_cryptographic_auth_enabled(output_intf_d4_eth32, "Ethernet32"):
            error_msg = f"STEP 5: Cryptographic auth not enabled on {dut4} Ethernet32"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Check D3 interfaces
        output_intf_d3 = self._get_show_ip_ospf_interface(dut3, "Ethernet32")
        if not self._verify_cryptographic_auth_enabled(output_intf_d3, "Ethernet32"):
            error_msg = f"STEP 5: Cryptographic auth not enabled on {dut3} Ethernet32"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 5" in f]) == 0:
            st.log("PASS: Cryptographic authentication enabled on all interfaces")

        # ========== STEP 6: Verify OSPF routes are learned ==========
        st.banner("STEP 6: Verifying OSPF routes are learned")

        # Check D1 routing table - should have routes to 20.0.x.x and 30.0.x.x networks
        output_route_d1 = self._get_show_ip_route_ospf(dut1)
        if not self._verify_ospf_route_present(output_route_d1, "20.0.1.0/30"):
            error_msg = f"STEP 6: OSPF route 20.0.1.0/30 not found on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_route_present(output_route_d1, "30.0.1.0/30"):
            error_msg = f"STEP 6: OSPF route 30.0.1.0/30 not found on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Check D3 routing table - should have routes to 10.0.x.x and 20.0.x.x networks
        output_route_d3 = self._get_show_ip_route_ospf(dut3)
        if not self._verify_ospf_route_present(output_route_d3, "10.0.1.0/30"):
            error_msg = f"STEP 6: OSPF route 10.0.1.0/30 not found on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_route_present(output_route_d3, "20.0.1.0/30"):
            error_msg = f"STEP 6: OSPF route 20.0.1.0/30 not found on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 6" in f]) == 0:
            st.log("PASS: OSPF routes learned successfully with MD5 authentication")

        # ========== STEP 7: Verify OSPF database ==========
        st.banner("STEP 7: Verifying OSPF database")

        # Get OSPF database from all devices
        output_db_d1 = self._get_show_ip_ospf_database(dut1)
        output_db_d2 = self._get_show_ip_ospf_database(dut2)
        output_db_d3 = self._get_show_ip_ospf_database(dut3)
        output_db_d4 = self._get_show_ip_ospf_database(dut4)

        # Verify database contains Router Link States
        if "Router Link States" not in output_db_d1:
            error_msg = f"STEP 7: Router Link States not found in {dut1} OSPF database"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 7" in f]) == 0:
            st.log("PASS: OSPF database verified successfully")

        # ========== STEP 8: Test authentication failure (mismatched key) ==========
        st.banner("STEP 8: Testing authentication failure with mismatched MD5 key")

        st.log(f"Changing MD5 key on {dut1} Ethernet0 to WRONGKEY to cause authentication failure")
        self._configure_ospf_md5_authentication(dut1, "Ethernet0", 1, "WRONGKEY")

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_DOWN} seconds for neighbor to go down (dead timer)")
        time.sleep(WAIT_FOR_NEIGHBOR_DOWN)

        # ========== STEP 9: Verify neighbor goes down ==========
        st.banner("STEP 9: Verifying neighbor goes down due to authentication failure")

        output_d1_after_failure = self._get_show_ip_ospf_neighbor(dut1)
        if not self._verify_ospf_neighbor_not_present(output_d1_after_failure, "10.0.1.2", "Ethernet0"):
            error_msg = f"STEP 9: Neighbor 10.0.1.2 on Ethernet0 still present after auth failure"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify other neighbors on Ethernet4,8,12 are still up
        if not self._verify_ospf_neighbor_count(output_d1_after_failure, 3):
            error_msg = f"STEP 9: Expected 3 OSPF neighbors on {dut1} (Ethernet0 down)"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 9" in f]) == 0:
            st.log("PASS: Neighbor went down as expected due to authentication mismatch")

        # ========== STEP 10: Restore correct key ==========
        st.banner("STEP 10: Restoring correct MD5 key")

        st.log(f"Restoring correct MD5 key on {dut1} Ethernet0")
        self._configure_ospf_md5_authentication(dut1, "Ethernet0", 1, self.data.md5_key_d1_d2)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for neighbor to come back up")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # ========== STEP 11: Verify neighbor comes back up ==========
        st.banner("STEP 11: Verifying neighbor comes back up after restoring correct key")

        output_d1_after_restore = self._get_show_ip_ospf_neighbor(dut1)
        if not self._verify_ospf_neighbor_full_state(output_d1_after_restore, "10.0.1.2", "Ethernet0"):
            error_msg = f"STEP 11: Neighbor 10.0.1.2 on Ethernet0 did not come back up"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify all 4 neighbors are now up
        if not self._verify_ospf_neighbor_count(output_d1_after_restore, 4):
            error_msg = f"STEP 11: Expected 4 OSPF neighbors on {dut1} after restore"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 11" in f]) == 0:
            st.log("PASS: Neighbor came back up successfully after restoring correct key")

        # ========== STEP 12: Cleanup ==========
        st.banner("STEP 12: Cleaning up configurations")

        # Remove OSPF configuration from all DUTs
        st.log("Removing OSPF configuration from all DUTs")
        self._remove_ospf_configuration(dut1)
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut3)
        self._remove_ospf_configuration(dut4)

        # Remove IP addresses from all interfaces
        st.log("Removing IP addresses from all interfaces")
        for interface in self.data.dut1_d2_links:
            self._remove_interface_ip(dut1, interface)

        for interface in self.data.dut2_d1_links + self.data.dut2_d4_links:
            self._remove_interface_ip(dut2, interface)

        for interface in self.data.dut4_d2_links + self.data.dut4_d3_links:
            self._remove_interface_ip(dut4, interface)

        for interface in self.data.dut3_d4_links:
            self._remove_interface_ip(dut3, interface)

        st.log("Cleanup completed")

        # ========== FINAL RESULT ==========
        st.banner("TEST RESULT")
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_md5_auth_validation_failure")
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
            st.log("=" * 80)
            st.log("PASS: All validations passed successfully")
            st.log("=" * 80)
            st.report_pass("msg", "OSPF MD5 authentication test completed successfully")
