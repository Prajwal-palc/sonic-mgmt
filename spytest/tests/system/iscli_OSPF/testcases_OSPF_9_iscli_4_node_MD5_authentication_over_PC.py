"""
OSPF MD5 AUTHENTICATION - 4-NODE TOPOLOGY WITH PORTCHANNELS
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_9_iscli_4_node_MD5_authentication_over_PC.py \
  --logs-path ./logs/testcases_OSPF_9_MD5_authentication_PC_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF MD5 authentication mechanism over PortChannel interfaces by:
  1. Removing IP addresses from Ethernet interfaces before adding to PortChannels
  2. Creating 4 PortChannels between each device pair
  3. Adding Ethernet interfaces as members to respective PortChannels
  4. Verifying PortChannel creation and member addition
  5. Configuring IP addresses on PortChannel interfaces
  6. Configuring OSPF with MD5 authentication using different keys per device pair
  7. Verifying OSPF neighbor adjacency reaches Full state with correct authentication
  8. Verifying "Cryptographic authentication enabled" appears in show commands
  9. Testing authentication failure by configuring mismatched MD5 key
  10. Verifying neighbor goes down when authentication fails (Dead timer expires)
  11. Restoring correct MD5 key and verifying neighbor comes back up
  12. Validating routing table updates with authenticated OSPF routes
  13. Cleanup: Removing all configurations

  Topology:
        D1 ======== (4 parallel PortChannels) ======== D2 ======== (4 parallel PortChannels) ======== D4 ======== (4 parallel PortChannels) ======== D3

  PortChannels with MD5 Authentication:
    D1 ↔ D2: PortChannel10,20,30,40 (MD5 key: sonic123)
    D2 ↔ D4: PortChannel110,120,130,140 (MD5 key: sonic456)
    D4 ↔ D3: PortChannel60,70,80,90 (MD5 key: sonic789)

  PortChannel Members:
    PortChannel10: Ethernet0 (D1-D2)
    PortChannel20: Ethernet4 (D1-D2)
    PortChannel30: Ethernet8 (D1-D2)
    PortChannel40: Ethernet12 (D1-D2)
    PortChannel110: Ethernet16 (D2-D4)
    PortChannel120: Ethernet20 (D2-D4)
    PortChannel130: Ethernet24 (D2-D4)
    PortChannel140: Ethernet28 (D2-D4)
    PortChannel60: Ethernet32 (D4-D3)
    PortChannel70: Ethernet36 (D4-D3)
    PortChannel80: Ethernet40 (D4-D3)
    PortChannel90: Ethernet44 (D4-D3)

  Configuration details:
    D1: PortChannel10,20,30,40: 10.0.1.1/30, 10.0.2.1/30, 10.0.3.1/30, 10.0.4.1/30
    D2: PortChannel10,20,30,40: 10.0.1.2/30, 10.0.2.2/30, 10.0.3.2/30, 10.0.4.2/30
        PortChannel110,120,130,140: 20.0.1.1/30, 20.0.2.1/30, 20.0.3.1/30, 20.0.4.1/30
    D4: PortChannel110,120,130,140: 20.0.1.2/30, 20.0.2.2/30, 20.0.3.2/30, 20.0.4.2/30
        PortChannel60,70,80,90: 30.0.1.1/30, 30.0.2.1/30, 30.0.3.1/30, 30.0.4.1/30
    D3: PortChannel60,70,80,90: 30.0.1.2/30, 30.0.2.2/30, 30.0.3.2/30, 30.0.4.2/30

  IMPORTANT: Uses 'show ip ospf neighbor', 'show ip ospf interface', 'show ip route ospf',
  'show ip ospf database', and 'show PortChannel summary' commands to validate OSPF MD5 authentication.
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
WAIT_AFTER_PORTCHANNEL_CONFIG = 3
WAIT_AFTER_IP_CONFIG = 3
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_AFTER_MD5_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_NEIGHBOR_DOWN = 45  # Wait for dead timer to expire after auth failure
WAIT_FOR_ROUTE_UPDATE = 10
WAIT_FOR_PING = 2


@pytest.mark.topology("any")
class TestOSPFMD5AuthenticationPortChannel4Node:
    """Test cases for validating OSPF MD5 authentication over PortChannels in 4-node topology via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF MD5 Authentication Test Suite (PortChannel)")
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
        # D1 ↔ D2: 4 parallel links (Ethernet interfaces to be added to PortChannels)
        cls.data.dut1_d2_eth_ports = ["Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12"]
        cls.data.dut2_d1_eth_ports = ["Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12"]

        # D2 ↔ D4: 4 parallel links
        cls.data.dut2_d4_eth_ports = ["Ethernet16", "Ethernet20", "Ethernet24", "Ethernet28"]
        cls.data.dut4_d2_eth_ports = ["Ethernet16", "Ethernet20", "Ethernet24", "Ethernet28"]

        # D4 ↔ D3: 4 parallel links
        cls.data.dut4_d3_eth_ports = ["Ethernet32", "Ethernet36", "Ethernet40", "Ethernet44"]
        cls.data.dut3_d4_eth_ports = ["Ethernet32", "Ethernet36", "Ethernet40", "Ethernet44"]

        # PortChannel IDs
        cls.data.dut1_d2_portchannels = ["10", "20", "30", "40"]
        cls.data.dut2_d1_portchannels = ["10", "20", "30", "40"]
        cls.data.dut2_d4_portchannels = ["110", "120", "130", "140"]
        cls.data.dut4_d2_portchannels = ["110", "120", "130", "140"]
        cls.data.dut4_d3_portchannels = ["60", "70", "80", "90"]
        cls.data.dut3_d4_portchannels = ["60", "70", "80", "90"]

        st.log("Topology Configuration:")
        st.log(f"  D1 ↔ D2: PortChannels {cls.data.dut1_d2_portchannels}")
        st.log(f"  D2 ↔ D4: PortChannels {cls.data.dut2_d4_portchannels}")
        st.log(f"  D4 ↔ D3: PortChannels {cls.data.dut4_d3_portchannels}")

        # IP addresses for D1 ↔ D2 PortChannels
        cls.data.dut1_d2_ips = ["10.0.1.1/30", "10.0.2.1/30", "10.0.3.1/30", "10.0.4.1/30"]
        cls.data.dut2_d1_ips = ["10.0.1.2/30", "10.0.2.2/30", "10.0.3.2/30", "10.0.4.2/30"]

        # IP addresses for D2 ↔ D4 PortChannels
        cls.data.dut2_d4_ips = ["20.0.1.1/30", "20.0.2.1/30", "20.0.3.1/30", "20.0.4.1/30"]
        cls.data.dut4_d2_ips = ["20.0.1.2/30", "20.0.2.2/30", "20.0.3.2/30", "20.0.4.2/30"]

        # IP addresses for D4 ↔ D3 PortChannels
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
        st.log("TEST TEARDOWN: Cleanup OSPF MD5 Authentication Test Suite (PortChannel)")
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
        Remove IP addresses from Ethernet interface before adding to PortChannel.

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
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    # ========== HELPER METHODS - PORTCHANNEL CONFIGURATION ==========

    @staticmethod
    def _create_portchannel(dut: str, portchannel_id: str) -> bool:
        """
        Create PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if successful
        """
        st.log(f"Creating PortChannel {portchannel_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _delete_portchannel(dut: str, portchannel_id: str) -> bool:
        """
        Delete PortChannel using klish commands.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if successful
        """
        st.log(f"Deleting PortChannel {portchannel_id} from {dut}")
        commands = [
            "configure terminal",
            f"no interface PortChannel {portchannel_id}"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _add_port_to_portchannel(dut: str, interface: str, portchannel_id: str) -> bool:
        """
        Add interface to PortChannel using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if successful
        """
        st.log(f"Adding {interface} to PortChannel {portchannel_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"channel-group {portchannel_id}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_port_from_portchannel(dut: str, interface: str) -> bool:
        """
        Remove interface from PortChannel using klish commands.

        Args:
            dut: Device handle
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if successful
        """
        st.log(f"Removing {interface} from PortChannel on {dut}")
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no channel-group",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _get_show_portchannel_summary(dut: str) -> str:
        """Get 'show PortChannel summary' output."""
        st.log(f"Getting 'show PortChannel summary' output from {dut}")
        output = st.show(dut, "show PortChannel summary", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show PortChannel summary output from {dut}:\n{output}")
        return output

    @staticmethod
    def _verify_portchannel_exists(dut: str, pc_output: str, portchannel_id: str) -> bool:
        """
        Verify that PortChannel exists in show PortChannel summary output.

        Args:
            dut: Device handle
            pc_output: Raw output from 'show PortChannel summary' command
            portchannel_id: PortChannel ID (e.g., "10")

        Returns:
            True if PortChannel exists, False otherwise
        """
        st.log(f"Verifying PortChannel {portchannel_id} exists on {dut}")

        # Search for "PortChannel<id>" pattern
        pc_pattern = rf'PortChannel{portchannel_id}'
        match = re.search(pc_pattern, pc_output, re.IGNORECASE)

        if match:
            st.log(f"PASS: PortChannel {portchannel_id} exists on {dut}")
            return True
        else:
            st.error(f"FAIL: PortChannel {portchannel_id} does not exist on {dut}")
            return False

    @staticmethod
    def _verify_port_in_portchannel(dut: str, pc_output: str, portchannel_id: str, interface: str) -> bool:
        """
        Verify that interface is a member of PortChannel.

        Args:
            dut: Device handle
            pc_output: Raw output from 'show PortChannel summary' command
            portchannel_id: PortChannel ID (e.g., "10")
            interface: Interface name (e.g., "Ethernet0")

        Returns:
            True if interface is member of PortChannel, False otherwise
        """
        st.log(f"Verifying {interface} is member of PortChannel {portchannel_id} on {dut}")

        # Search for PortChannel entry and check if interface is listed
        pc_section_pattern = rf'PortChannel{portchannel_id}\s+.*?(?=\n\s*\d+\s+PortChannel|\Z)'
        pc_match = re.search(pc_section_pattern, pc_output, re.IGNORECASE | re.DOTALL)

        if not pc_match:
            st.error(f"FAIL: PortChannel {portchannel_id} not found in output on {dut}")
            return False

        pc_section = pc_match.group(0)

        # Check if interface is in this PortChannel section
        if interface in pc_section:
            st.log(f"PASS: {interface} is member of PortChannel {portchannel_id} on {dut}")
            return True
        else:
            st.error(f"FAIL: {interface} is not member of PortChannel {portchannel_id} on {dut}")
            return False

    # ========== HELPER METHODS - IP CONFIGURATION ==========

    @staticmethod
    def _configure_portchannel_ip(dut: str, portchannel_id: str, ip_address: str) -> bool:
        """
        Configure IP address on PortChannel interface.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
            ip_address: IP address with mask (e.g., "10.0.1.1/30")

        Returns:
            True if successful
        """
        st.log(f"Configuring IP address {ip_address} on PortChannel{portchannel_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            "no shutdown",
            "no ip address",
            f"ip address {ip_address}",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_portchannel_ip(dut: str, portchannel_id: str) -> bool:
        """
        Remove IP address from PortChannel interface.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID

        Returns:
            True if successful
        """
        st.log(f"Removing IP address from PortChannel{portchannel_id} on {dut}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
            "no ip address",
            "exit"
        ]
        result = st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _verify_portchannel_ip(dut: str, portchannel_id: str, expected_ip: str) -> bool:
        """
        Verify IP address is configured on PortChannel using running-configuration.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID (e.g., "10")
            expected_ip: Expected IP address (e.g., "10.0.1.1/30")

        Returns:
            True if IP is configured correctly
        """
        st.log(f"Verifying IP address {expected_ip} on PortChannel{portchannel_id} on {dut}")

        # Command: show running-configuration interface PortChannel X
        command = f"show running-configuration interface PortChannel {portchannel_id}"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True, skip_error_check=True)

        if not isinstance(output, str):
            output = str(output)

        st.log(f"Running-config output from {dut}:\n{output}")

        # Check if expected IP is in the output
        if expected_ip in output:
            st.log(f"PASS: IP address {expected_ip} verified on PortChannel{portchannel_id}")
            return True
        else:
            # Also check for IP without mask format
            ip_without_mask = expected_ip.split('/')[0]
            if ip_without_mask in output and "ip address" in output.lower():
                st.log(f"PASS: IP address {expected_ip} verified on PortChannel{portchannel_id}")
                return True
            else:
                st.error(f"FAIL: IP address {expected_ip} not found on PortChannel{portchannel_id}")
                return False

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
    def _configure_ospf_md5_authentication_portchannel(dut: str, portchannel_id: str, key_id: int, md5_key: str) -> bool:
        """
        Configure OSPF MD5 authentication on PortChannel interface.

        Args:
            dut: Device handle
            portchannel_id: PortChannel ID
            key_id: MD5 key ID (typically 1)
            md5_key: MD5 authentication key

        Returns:
            True if successful
        """
        st.log(f"Configuring OSPF MD5 authentication on PortChannel{portchannel_id} on {dut} with key {md5_key}")
        commands = [
            "configure terminal",
            f"interface PortChannel {portchannel_id}",
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

    def test_ospf_md5_authentication_portchannel(self) -> None:
        """
        Test OSPF MD5 authentication functionality over PortChannels.

        Test Steps:
        1. Remove IP addresses from Ethernet interfaces
        2. Create PortChannels
        3. Add Ethernet interfaces to PortChannels
        4. Verify PortChannel creation and member addition
        5. Configure IP addresses on PortChannels
        6. Verify IP configuration
        7. Configure OSPF with MD5 authentication
        8. Verify OSPF neighbors reach Full state
        9. Verify cryptographic authentication is enabled
        10. Verify OSPF routes are learned
        11. Test authentication failure (mismatched key)
        12. Verify neighbor goes down
        13. Restore correct key
        14. Verify neighbor comes back up
        15. Cleanup configuration
        """
        st.log("=" * 80)
        st.log("TEST CASE: OSPF MD5 Authentication over PortChannels")
        st.log("=" * 80)

        dut1 = self.data.dut1
        dut2 = self.data.dut2
        dut3 = self.data.dut3
        dut4 = self.data.dut4

        validation_failures = []

        # ========== STEP 1: Remove IP addresses from Ethernet interfaces ==========
        st.banner("STEP 1: Removing IP addresses from Ethernet interfaces")

        # Remove IPs from D1 interfaces
        for interface in self.data.dut1_d2_eth_ports:
            self._remove_ip_from_ethernet_interface(dut1, interface)

        # Remove IPs from D2 interfaces
        for interface in self.data.dut2_d1_eth_ports + self.data.dut2_d4_eth_ports:
            self._remove_ip_from_ethernet_interface(dut2, interface)

        # Remove IPs from D4 interfaces
        for interface in self.data.dut4_d2_eth_ports + self.data.dut4_d3_eth_ports:
            self._remove_ip_from_ethernet_interface(dut4, interface)

        # Remove IPs from D3 interfaces
        for interface in self.data.dut3_d4_eth_ports:
            self._remove_ip_from_ethernet_interface(dut3, interface)

        st.log("IP addresses removed from all Ethernet interfaces")

        # ========== STEP 2: Create PortChannels ==========
        st.banner("STEP 2: Creating PortChannels")

        # Create PortChannels on D1
        for pc_id in self.data.dut1_d2_portchannels:
            self._create_portchannel(dut1, pc_id)

        # Create PortChannels on D2
        for pc_id in self.data.dut2_d1_portchannels + self.data.dut2_d4_portchannels:
            self._create_portchannel(dut2, pc_id)

        # Create PortChannels on D4
        for pc_id in self.data.dut4_d2_portchannels + self.data.dut4_d3_portchannels:
            self._create_portchannel(dut4, pc_id)

        # Create PortChannels on D3
        for pc_id in self.data.dut3_d4_portchannels:
            self._create_portchannel(dut3, pc_id)

        st.log(f"Waiting {WAIT_AFTER_PORTCHANNEL_CONFIG} seconds after PortChannel creation")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        # ========== STEP 3: Add Ethernet interfaces to PortChannels ==========
        st.banner("STEP 3: Adding Ethernet interfaces to PortChannels")

        # Add D1 interfaces to PortChannels
        for interface, pc_id in zip(self.data.dut1_d2_eth_ports, self.data.dut1_d2_portchannels):
            self._add_port_to_portchannel(dut1, interface, pc_id)

        # Add D2 interfaces to PortChannels
        for interface, pc_id in zip(self.data.dut2_d1_eth_ports, self.data.dut2_d1_portchannels):
            self._add_port_to_portchannel(dut2, interface, pc_id)
        for interface, pc_id in zip(self.data.dut2_d4_eth_ports, self.data.dut2_d4_portchannels):
            self._add_port_to_portchannel(dut2, interface, pc_id)

        # Add D4 interfaces to PortChannels
        for interface, pc_id in zip(self.data.dut4_d2_eth_ports, self.data.dut4_d2_portchannels):
            self._add_port_to_portchannel(dut4, interface, pc_id)
        for interface, pc_id in zip(self.data.dut4_d3_eth_ports, self.data.dut4_d3_portchannels):
            self._add_port_to_portchannel(dut4, interface, pc_id)

        # Add D3 interfaces to PortChannels
        for interface, pc_id in zip(self.data.dut3_d4_eth_ports, self.data.dut3_d4_portchannels):
            self._add_port_to_portchannel(dut3, interface, pc_id)

        st.log(f"Waiting {WAIT_AFTER_PORTCHANNEL_CONFIG} seconds after adding members")
        time.sleep(WAIT_AFTER_PORTCHANNEL_CONFIG)

        # ========== STEP 4: Verify PortChannel creation and member addition ==========
        st.banner("STEP 4: Verifying PortChannel creation and member addition")

        # Verify D1 PortChannels
        output_pc_d1 = self._get_show_portchannel_summary(dut1)
        for pc_id, interface in zip(self.data.dut1_d2_portchannels, self.data.dut1_d2_eth_ports):
            if not self._verify_portchannel_exists(dut1, output_pc_d1, pc_id):
                error_msg = f"STEP 4: PortChannel {pc_id} does not exist on {dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            if not self._verify_port_in_portchannel(dut1, output_pc_d1, pc_id, interface):
                error_msg = f"STEP 4: {interface} not in PortChannel {pc_id} on {dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D2 PortChannels
        output_pc_d2 = self._get_show_portchannel_summary(dut2)
        for pc_id, interface in zip(self.data.dut2_d1_portchannels, self.data.dut2_d1_eth_ports):
            if not self._verify_portchannel_exists(dut2, output_pc_d2, pc_id):
                error_msg = f"STEP 4: PortChannel {pc_id} does not exist on {dut2}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            if not self._verify_port_in_portchannel(dut2, output_pc_d2, pc_id, interface):
                error_msg = f"STEP 4: {interface} not in PortChannel {pc_id} on {dut2}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        for pc_id, interface in zip(self.data.dut2_d4_portchannels, self.data.dut2_d4_eth_ports):
            if not self._verify_portchannel_exists(dut2, output_pc_d2, pc_id):
                error_msg = f"STEP 4: PortChannel {pc_id} does not exist on {dut2}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            if not self._verify_port_in_portchannel(dut2, output_pc_d2, pc_id, interface):
                error_msg = f"STEP 4: {interface} not in PortChannel {pc_id} on {dut2}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D4 PortChannels
        output_pc_d4 = self._get_show_portchannel_summary(dut4)
        for pc_id, interface in zip(self.data.dut4_d2_portchannels, self.data.dut4_d2_eth_ports):
            if not self._verify_portchannel_exists(dut4, output_pc_d4, pc_id):
                error_msg = f"STEP 4: PortChannel {pc_id} does not exist on {dut4}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            if not self._verify_port_in_portchannel(dut4, output_pc_d4, pc_id, interface):
                error_msg = f"STEP 4: {interface} not in PortChannel {pc_id} on {dut4}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        for pc_id, interface in zip(self.data.dut4_d3_portchannels, self.data.dut4_d3_eth_ports):
            if not self._verify_portchannel_exists(dut4, output_pc_d4, pc_id):
                error_msg = f"STEP 4: PortChannel {pc_id} does not exist on {dut4}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            if not self._verify_port_in_portchannel(dut4, output_pc_d4, pc_id, interface):
                error_msg = f"STEP 4: {interface} not in PortChannel {pc_id} on {dut4}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D3 PortChannels
        output_pc_d3 = self._get_show_portchannel_summary(dut3)
        for pc_id, interface in zip(self.data.dut3_d4_portchannels, self.data.dut3_d4_eth_ports):
            if not self._verify_portchannel_exists(dut3, output_pc_d3, pc_id):
                error_msg = f"STEP 4: PortChannel {pc_id} does not exist on {dut3}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            if not self._verify_port_in_portchannel(dut3, output_pc_d3, pc_id, interface):
                error_msg = f"STEP 4: {interface} not in PortChannel {pc_id} on {dut3}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 4" in f]) == 0:
            st.log("PASS: All PortChannels created and members added successfully")

        # ========== STEP 5: Configure IP addresses on PortChannels ==========
        st.banner("STEP 5: Configuring IP addresses on PortChannels")

        # Configure D1 PortChannel IPs
        for pc_id, ip in zip(self.data.dut1_d2_portchannels, self.data.dut1_d2_ips):
            self._configure_portchannel_ip(dut1, pc_id, ip)

        # Configure D2 PortChannel IPs
        for pc_id, ip in zip(self.data.dut2_d1_portchannels, self.data.dut2_d1_ips):
            self._configure_portchannel_ip(dut2, pc_id, ip)
        for pc_id, ip in zip(self.data.dut2_d4_portchannels, self.data.dut2_d4_ips):
            self._configure_portchannel_ip(dut2, pc_id, ip)

        # Configure D4 PortChannel IPs
        for pc_id, ip in zip(self.data.dut4_d2_portchannels, self.data.dut4_d2_ips):
            self._configure_portchannel_ip(dut4, pc_id, ip)
        for pc_id, ip in zip(self.data.dut4_d3_portchannels, self.data.dut4_d3_ips):
            self._configure_portchannel_ip(dut4, pc_id, ip)

        # Configure D3 PortChannel IPs
        for pc_id, ip in zip(self.data.dut3_d4_portchannels, self.data.dut3_d4_ips):
            self._configure_portchannel_ip(dut3, pc_id, ip)

        st.log(f"Waiting {WAIT_AFTER_IP_CONFIG} seconds after IP configuration")
        time.sleep(WAIT_AFTER_IP_CONFIG)

        # ========== STEP 6: Verify IP configuration ==========
        st.banner("STEP 6: Verifying IP configuration on PortChannels")

        # Verify D1 PortChannel IPs
        for pc_id, ip in zip(self.data.dut1_d2_portchannels, self.data.dut1_d2_ips):
            if not self._verify_portchannel_ip(dut1, pc_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut1} PortChannel{pc_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D2 PortChannel IPs
        for pc_id, ip in zip(self.data.dut2_d1_portchannels, self.data.dut2_d1_ips):
            if not self._verify_portchannel_ip(dut2, pc_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut2} PortChannel{pc_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)
        for pc_id, ip in zip(self.data.dut2_d4_portchannels, self.data.dut2_d4_ips):
            if not self._verify_portchannel_ip(dut2, pc_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut2} PortChannel{pc_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D4 PortChannel IPs
        for pc_id, ip in zip(self.data.dut4_d2_portchannels, self.data.dut4_d2_ips):
            if not self._verify_portchannel_ip(dut4, pc_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut4} PortChannel{pc_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)
        for pc_id, ip in zip(self.data.dut4_d3_portchannels, self.data.dut4_d3_ips):
            if not self._verify_portchannel_ip(dut4, pc_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut4} PortChannel{pc_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D3 PortChannel IPs
        for pc_id, ip in zip(self.data.dut3_d4_portchannels, self.data.dut3_d4_ips):
            if not self._verify_portchannel_ip(dut3, pc_id, ip):
                error_msg = f"STEP 6: IP validation failed on {dut3} PortChannel{pc_id}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 6" in f]) == 0:
            st.log("PASS: All PortChannel IP addresses configured and verified successfully")

        # ========== STEP 7: Configure OSPF with MD5 authentication ==========
        st.banner("STEP 7: Configuring OSPF with MD5 authentication")

        # Configure OSPF on D1
        st.log(f"Configuring OSPF on {dut1}")
        networks_d1 = ["10.0.1.0/30", "10.0.2.0/30", "10.0.3.0/30", "10.0.4.0/30"]
        self._configure_ospf_process(dut1, self.data.ospf_area, networks_d1)

        # Configure MD5 authentication on D1 PortChannels
        for pc_id in self.data.dut1_d2_portchannels:
            self._configure_ospf_md5_authentication_portchannel(dut1, pc_id, 1, self.data.md5_key_d1_d2)

        # Configure OSPF on D2
        st.log(f"Configuring OSPF on {dut2}")
        networks_d2 = ["10.0.1.0/30", "10.0.2.0/30", "10.0.3.0/30", "10.0.4.0/30",
                       "20.0.1.0/30", "20.0.2.0/30", "20.0.3.0/30", "20.0.4.0/30"]
        self._configure_ospf_process(dut2, self.data.ospf_area, networks_d2)

        # Configure MD5 authentication on D2 PortChannels (D1 side)
        for pc_id in self.data.dut2_d1_portchannels:
            self._configure_ospf_md5_authentication_portchannel(dut2, pc_id, 1, self.data.md5_key_d1_d2)

        # Configure MD5 authentication on D2 PortChannels (D4 side)
        for pc_id in self.data.dut2_d4_portchannels:
            self._configure_ospf_md5_authentication_portchannel(dut2, pc_id, 1, self.data.md5_key_d2_d4)

        # Configure OSPF on D4
        st.log(f"Configuring OSPF on {dut4}")
        networks_d4 = ["20.0.1.0/30", "20.0.2.0/30", "20.0.3.0/30", "20.0.4.0/30",
                       "30.0.1.0/30", "30.0.2.0/30", "30.0.3.0/30", "30.0.4.0/30"]
        self._configure_ospf_process(dut4, self.data.ospf_area, networks_d4)

        # Configure MD5 authentication on D4 PortChannels (D2 side)
        for pc_id in self.data.dut4_d2_portchannels:
            self._configure_ospf_md5_authentication_portchannel(dut4, pc_id, 1, self.data.md5_key_d2_d4)

        # Configure MD5 authentication on D4 PortChannels (D3 side)
        for pc_id in self.data.dut4_d3_portchannels:
            self._configure_ospf_md5_authentication_portchannel(dut4, pc_id, 1, self.data.md5_key_d4_d3)

        # Configure OSPF on D3
        st.log(f"Configuring OSPF on {dut3}")
        networks_d3 = ["30.0.1.0/30", "30.0.2.0/30", "30.0.3.0/30", "30.0.4.0/30"]
        self._configure_ospf_process(dut3, self.data.ospf_area, networks_d3)

        # Configure MD5 authentication on D3 PortChannels
        for pc_id in self.data.dut3_d4_portchannels:
            self._configure_ospf_md5_authentication_portchannel(dut3, pc_id, 1, self.data.md5_key_d4_d3)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbors to come up")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # ========== STEP 8: Verify OSPF neighbors reach Full state ==========
        st.banner("STEP 8: Verifying OSPF neighbors reach Full state")

        # Verify D1 neighbors
        output_d1 = self._get_show_ip_ospf_neighbor(dut1)
        if not self._verify_ospf_neighbor_count(output_d1, 4):
            error_msg = f"STEP 8: Expected 4 OSPF neighbors on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify each neighbor individually
        for pc_id, neighbor_ip in zip(self.data.dut1_d2_portchannels, ["10.0.1.2", "10.0.2.2", "10.0.3.2", "10.0.4.2"]):
            interface_name = f"PortChannel{pc_id}"
            if not self._verify_ospf_neighbor_full_state(output_d1, neighbor_ip, interface_name):
                error_msg = f"STEP 8: Neighbor {neighbor_ip} on {dut1} {interface_name} not in Full state"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Verify D2 neighbors
        output_d2 = self._get_show_ip_ospf_neighbor(dut2)
        if not self._verify_ospf_neighbor_count(output_d2, 8):
            error_msg = f"STEP 8: Expected 8 OSPF neighbors on {dut2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D4 neighbors
        output_d4 = self._get_show_ip_ospf_neighbor(dut4)
        if not self._verify_ospf_neighbor_count(output_d4, 8):
            error_msg = f"STEP 8: Expected 8 OSPF neighbors on {dut4}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D3 neighbors
        output_d3 = self._get_show_ip_ospf_neighbor(dut3)
        if not self._verify_ospf_neighbor_count(output_d3, 4):
            error_msg = f"STEP 8: Expected 4 OSPF neighbors on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 8" in f]) == 0:
            st.log("PASS: All OSPF neighbors reached Full state")

        # ========== STEP 9: Verify cryptographic authentication is enabled ==========
        st.banner("STEP 9: Verifying cryptographic authentication is enabled")

        # Check D1 PortChannels
        output_intf_d1 = self._get_show_ip_ospf_interface(dut1, "PortChannel10")
        if not self._verify_cryptographic_auth_enabled(output_intf_d1, "PortChannel10"):
            error_msg = f"STEP 9: Cryptographic auth not enabled on {dut1} PortChannel10"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_md5_algorithm(output_intf_d1, "PortChannel10"):
            error_msg = f"STEP 9: MD5 algorithm not shown on {dut1} PortChannel10"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Check D2 PortChannels (sample check on PortChannel10 and PortChannel110)
        output_intf_d2_pc10 = self._get_show_ip_ospf_interface(dut2, "PortChannel10")
        if not self._verify_cryptographic_auth_enabled(output_intf_d2_pc10, "PortChannel10"):
            error_msg = f"STEP 9: Cryptographic auth not enabled on {dut2} PortChannel10"
            st.error(error_msg)
            validation_failures.append(error_msg)

        output_intf_d2_pc110 = self._get_show_ip_ospf_interface(dut2, "PortChannel110")
        if not self._verify_cryptographic_auth_enabled(output_intf_d2_pc110, "PortChannel110"):
            error_msg = f"STEP 9: Cryptographic auth not enabled on {dut2} PortChannel110"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Check D4 PortChannels (sample check on PortChannel110 and PortChannel60)
        output_intf_d4_pc110 = self._get_show_ip_ospf_interface(dut4, "PortChannel110")
        if not self._verify_cryptographic_auth_enabled(output_intf_d4_pc110, "PortChannel110"):
            error_msg = f"STEP 9: Cryptographic auth not enabled on {dut4} PortChannel110"
            st.error(error_msg)
            validation_failures.append(error_msg)

        output_intf_d4_pc60 = self._get_show_ip_ospf_interface(dut4, "PortChannel60")
        if not self._verify_cryptographic_auth_enabled(output_intf_d4_pc60, "PortChannel60"):
            error_msg = f"STEP 9: Cryptographic auth not enabled on {dut4} PortChannel60"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Check D3 PortChannels
        output_intf_d3 = self._get_show_ip_ospf_interface(dut3, "PortChannel60")
        if not self._verify_cryptographic_auth_enabled(output_intf_d3, "PortChannel60"):
            error_msg = f"STEP 9: Cryptographic auth not enabled on {dut3} PortChannel60"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 9" in f]) == 0:
            st.log("PASS: Cryptographic authentication enabled on all PortChannels")

        # ========== STEP 10: Verify OSPF routes are learned ==========
        st.banner("STEP 10: Verifying OSPF routes are learned")

        # Check D1 routing table - should have routes to 20.0.x.x and 30.0.x.x networks
        output_route_d1 = self._get_show_ip_route_ospf(dut1)
        if not self._verify_ospf_route_present(output_route_d1, "20.0.1.0/30"):
            error_msg = f"STEP 10: OSPF route 20.0.1.0/30 not found on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_route_present(output_route_d1, "30.0.1.0/30"):
            error_msg = f"STEP 10: OSPF route 30.0.1.0/30 not found on {dut1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Check D3 routing table - should have routes to 10.0.x.x and 20.0.x.x networks
        output_route_d3 = self._get_show_ip_route_ospf(dut3)
        if not self._verify_ospf_route_present(output_route_d3, "10.0.1.0/30"):
            error_msg = f"STEP 10: OSPF route 10.0.1.0/30 not found on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_route_present(output_route_d3, "20.0.1.0/30"):
            error_msg = f"STEP 10: OSPF route 20.0.1.0/30 not found on {dut3}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 10" in f]) == 0:
            st.log("PASS: OSPF routes learned successfully with MD5 authentication over PortChannels")

        # ========== STEP 11: Verify OSPF database ==========
        st.banner("STEP 11: Verifying OSPF database")

        # Get OSPF database from all devices
        output_db_d1 = self._get_show_ip_ospf_database(dut1)
        output_db_d2 = self._get_show_ip_ospf_database(dut2)
        output_db_d3 = self._get_show_ip_ospf_database(dut3)
        output_db_d4 = self._get_show_ip_ospf_database(dut4)

        # Verify database contains Router Link States
        if "Router Link States" not in output_db_d1:
            error_msg = f"STEP 11: Router Link States not found in {dut1} OSPF database"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 11" in f]) == 0:
            st.log("PASS: OSPF database verified successfully")

        # ========== STEP 12: Test authentication failure (mismatched key) ==========
        st.banner("STEP 12: Testing authentication failure with mismatched MD5 key")

        st.log(f"Changing MD5 key on {dut1} PortChannel10 to WRONGKEY to cause authentication failure")
        self._configure_ospf_md5_authentication_portchannel(dut1, "10", 1, "WRONGKEY")

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_DOWN} seconds for neighbor to go down (dead timer)")
        time.sleep(WAIT_FOR_NEIGHBOR_DOWN)

        # ========== STEP 13: Verify neighbor goes down ==========
        st.banner("STEP 13: Verifying neighbor goes down due to authentication failure")

        output_d1_after_failure = self._get_show_ip_ospf_neighbor(dut1)
        if not self._verify_ospf_neighbor_not_present(output_d1_after_failure, "10.0.1.2", "PortChannel10"):
            error_msg = f"STEP 13: Neighbor 10.0.1.2 on PortChannel10 still present after auth failure"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify other neighbors on PortChannel20,30,40 are still up
        if not self._verify_ospf_neighbor_count(output_d1_after_failure, 3):
            error_msg = f"STEP 13: Expected 3 OSPF neighbors on {dut1} (PortChannel10 down)"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 13" in f]) == 0:
            st.log("PASS: Neighbor went down as expected due to authentication mismatch")

        # ========== STEP 14: Restore correct key ==========
        st.banner("STEP 14: Restoring correct MD5 key")

        st.log(f"Restoring correct MD5 key on {dut1} PortChannel10")
        self._configure_ospf_md5_authentication_portchannel(dut1, "10", 1, self.data.md5_key_d1_d2)

        st.log(f"Waiting {WAIT_FOR_NEIGHBOR_UP} seconds for neighbor to come back up")
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # ========== STEP 15: Verify neighbor comes back up ==========
        st.banner("STEP 15: Verifying neighbor comes back up after restoring correct key")

        output_d1_after_restore = self._get_show_ip_ospf_neighbor(dut1)
        if not self._verify_ospf_neighbor_full_state(output_d1_after_restore, "10.0.1.2", "PortChannel10"):
            error_msg = f"STEP 15: Neighbor 10.0.1.2 on PortChannel10 did not come back up"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify all 4 neighbors are now up
        if not self._verify_ospf_neighbor_count(output_d1_after_restore, 4):
            error_msg = f"STEP 15: Expected 4 OSPF neighbors on {dut1} after restore"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 15" in f]) == 0:
            st.log("PASS: Neighbor came back up successfully after restoring correct key")

        # ========== STEP 16: Cleanup ==========
        st.banner("STEP 16: Cleaning up configurations")

        # Remove OSPF configuration from all DUTs
        st.log("Removing OSPF configuration from all DUTs")
        self._remove_ospf_configuration(dut1)
        self._remove_ospf_configuration(dut2)
        self._remove_ospf_configuration(dut3)
        self._remove_ospf_configuration(dut4)

        # Remove IP addresses from all PortChannels
        st.log("Removing IP addresses from all PortChannels")
        for pc_id in self.data.dut1_d2_portchannels:
            self._remove_portchannel_ip(dut1, pc_id)

        for pc_id in self.data.dut2_d1_portchannels + self.data.dut2_d4_portchannels:
            self._remove_portchannel_ip(dut2, pc_id)

        for pc_id in self.data.dut4_d2_portchannels + self.data.dut4_d3_portchannels:
            self._remove_portchannel_ip(dut4, pc_id)

        for pc_id in self.data.dut3_d4_portchannels:
            self._remove_portchannel_ip(dut3, pc_id)

        # Remove ports from PortChannels
        st.log("Removing ports from PortChannels")
        for interface in self.data.dut1_d2_eth_ports:
            self._remove_port_from_portchannel(dut1, interface)

        for interface in self.data.dut2_d1_eth_ports + self.data.dut2_d4_eth_ports:
            self._remove_port_from_portchannel(dut2, interface)

        for interface in self.data.dut4_d2_eth_ports + self.data.dut4_d3_eth_ports:
            self._remove_port_from_portchannel(dut4, interface)

        for interface in self.data.dut3_d4_eth_ports:
            self._remove_port_from_portchannel(dut3, interface)

        # Delete PortChannels
        st.log("Deleting PortChannels")
        for pc_id in self.data.dut1_d2_portchannels:
            self._delete_portchannel(dut1, pc_id)

        for pc_id in self.data.dut2_d1_portchannels + self.data.dut2_d4_portchannels:
            self._delete_portchannel(dut2, pc_id)

        for pc_id in self.data.dut4_d2_portchannels + self.data.dut4_d3_portchannels:
            self._delete_portchannel(dut4, pc_id)

        for pc_id in self.data.dut3_d4_portchannels:
            self._delete_portchannel(dut3, pc_id)

        st.log("Cleanup completed")

        # ========== FINAL RESULT ==========
        st.banner("TEST RESULT")
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_md5_auth_pc_validation_failure")
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
            st.report_pass("msg", "OSPF MD5 authentication over PortChannels test completed successfully")
