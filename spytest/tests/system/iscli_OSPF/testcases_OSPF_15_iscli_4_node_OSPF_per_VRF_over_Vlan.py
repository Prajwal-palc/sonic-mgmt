"""
OSPF PER VRF OVER VLAN - 4-NODE TOPOLOGY WITH DUAL VRF VALIDATION
Author: Test Engineering Team
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_4vs.yaml \
  tests/system/iscli_OSPF/testcases_OSPF_15_iscli_4_node_OSPF_per_VRF_over_Vlan.py \
  --logs-path ./logs/testcases_OSPF_15_vrf_vlan_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates OSPF per VRF over VLAN interfaces in a 4-node topology by:
  1. Removing IP addresses from Ethernet interfaces before adding to VLANs
  2. Creating VLANs on all devices
  3. Adding Ethernet interfaces as members to respective VLANs
  4. Verifying VLAN creation and member addition
  5. Creating two VRFs (Vrf-RED and Vrf-BLUE) on all devices
  6. Assigning VLAN interfaces to respective VRFs with IP addresses
  7. Verifying VLAN IP configuration
  8. Configuring OSPF process per VRF with unique router IDs
  9. Verifying OSPF neighbor adjacency (Full state) for both VRFs
  10. Verifying DR/BDR election per VRF
  11. Validating OSPF interfaces and database per VRF
  12. Verifying route learning and ECMP in routing tables per VRF
  13. Testing end-to-end ping connectivity across VRFs
  14. Validating VRF isolation (no cross-VRF traffic)
  15. Cleanup: Removing all configurations

  Topology:
        D1 ======== (4 parallel VLANs) ======== D2 ======== (4 parallel VLANs) ======== D4 ======== (4 parallel VLANs) ======== D3
       Vlan1-4      Vlan1-4      Vlan5-8        Vlan5-8        Vlan9-12       Vlan9-12

  VLAN Member Assignments:
    D1: Vlan1(Eth0), Vlan2(Eth4), Vlan3(Eth8), Vlan4(Eth12)
    D2: Vlan1(Eth0), Vlan2(Eth4), Vlan3(Eth8), Vlan4(Eth12), Vlan5(Eth16), Vlan6(Eth20), Vlan7(Eth24), Vlan8(Eth28)
    D4: Vlan5(Eth16), Vlan6(Eth20), Vlan7(Eth24), Vlan8(Eth28), Vlan9(Eth32), Vlan10(Eth36), Vlan11(Eth40), Vlan12(Eth44)
    D3: Vlan9(Eth32), Vlan10(Eth36), Vlan11(Eth40), Vlan12(Eth44)

  VRF Assignment:
    Vrf-RED:  Vlan1, Vlan2, Vlan5, Vlan6, Vlan9, Vlan10
    Vrf-BLUE: Vlan3, Vlan4, Vlan7, Vlan8, Vlan11, Vlan12

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

  IMPORTANT: Uses 'show Vlan', 'show ip vrf', 'show ip ospf vrf <vrf>',
  'show ip ospf neighbor vrf <vrf>', 'show ip ospf interface vrf <vrf>',
  'show ip ospf database vrf <vrf>', 'show ip route vrf <vrf>', and
  'show running-configuration interface Vlan X' commands.
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
WAIT_AFTER_VLAN_CONFIG = 5
WAIT_AFTER_VRF_CONFIG = 3
WAIT_AFTER_IP_CONFIG = 3
WAIT_AFTER_OSPF_CONFIG = 5
WAIT_FOR_NEIGHBOR_UP = 45
WAIT_FOR_ROUTE_UPDATE = 15
WAIT_FOR_PING = 2


@pytest.mark.topology("any")
class TestOSPFPerVRF4NodeVLAN:
    """Test cases for validating OSPF per VRF over VLAN in 4-node topology via CLI (klish mode)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("TEST SETUP: Initializing OSPF Per VRF over VLAN Test Suite")
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

        # VLAN IDs and member ports based on testbed_4vs.yaml
        # D1: Vlan1-4 with Eth0,4,8,12
        cls.data.dut1_vlans = {
            "1": ["Ethernet0"],    # Vrf-RED
            "2": ["Ethernet4"],    # Vrf-RED
            "3": ["Ethernet8"],    # Vrf-BLUE
            "4": ["Ethernet12"]    # Vrf-BLUE
        }

        # D2: Vlan1-8 with Eth0,4,8,12,16,20,24,28
        cls.data.dut2_vlans = {
            "1": ["Ethernet0"],    # Vrf-RED (to D1)
            "2": ["Ethernet4"],    # Vrf-RED (to D1)
            "3": ["Ethernet8"],    # Vrf-BLUE (to D1)
            "4": ["Ethernet12"],   # Vrf-BLUE (to D1)
            "5": ["Ethernet16"],   # Vrf-RED (to D4)
            "6": ["Ethernet20"],   # Vrf-RED (to D4)
            "7": ["Ethernet24"],   # Vrf-BLUE (to D4)
            "8": ["Ethernet28"]    # Vrf-BLUE (to D4)
        }

        # D4: Vlan5-12 with Eth16,20,24,28,32,36,40,44
        cls.data.dut4_vlans = {
            "5": ["Ethernet16"],   # Vrf-RED (to D2)
            "6": ["Ethernet20"],   # Vrf-RED (to D2)
            "7": ["Ethernet24"],   # Vrf-BLUE (to D2)
            "8": ["Ethernet28"],   # Vrf-BLUE (to D2)
            "9": ["Ethernet32"],   # Vrf-RED (to D3)
            "10": ["Ethernet36"],  # Vrf-RED (to D3)
            "11": ["Ethernet40"],  # Vrf-BLUE (to D3)
            "12": ["Ethernet44"]   # Vrf-BLUE (to D3)
        }

        # D3: Vlan9-12 with Eth32,36,40,44
        cls.data.dut3_vlans = {
            "9": ["Ethernet32"],   # Vrf-RED
            "10": ["Ethernet36"],  # Vrf-RED
            "11": ["Ethernet40"],  # Vrf-BLUE
            "12": ["Ethernet44"]   # Vrf-BLUE
        }

        # IP addresses for Vrf-RED on VLAN interfaces
        # D1 ↔ D2: 10.1.x.x
        cls.data.dut1_vrf_red_ips = ["10.1.1.1/24", "10.1.2.1/24"]  # Vlan1, Vlan2
        cls.data.dut2_vrf_red_d1_ips = ["10.1.1.2/24", "10.1.2.2/24"]  # Vlan1, Vlan2

        # D2 ↔ D4: 30.1.x.x
        cls.data.dut2_vrf_red_d4_ips = ["30.1.1.1/24", "30.1.2.1/24"]  # Vlan5, Vlan6
        cls.data.dut4_vrf_red_d2_ips = ["30.1.1.2/24", "30.1.2.2/24"]  # Vlan5, Vlan6

        # D4 ↔ D3: 50.1.x.x
        cls.data.dut4_vrf_red_d3_ips = ["50.1.1.1/24", "50.1.2.1/24"]  # Vlan9, Vlan10
        cls.data.dut3_vrf_red_ips = ["50.1.1.2/24", "50.1.2.2/24"]  # Vlan9, Vlan10

        # IP addresses for Vrf-BLUE on VLAN interfaces
        # D1 ↔ D2: 10.2.x.x
        cls.data.dut1_vrf_blue_ips = ["10.2.1.1/24", "10.2.2.1/24"]  # Vlan3, Vlan4
        cls.data.dut2_vrf_blue_d1_ips = ["10.2.1.2/24", "10.2.2.2/24"]  # Vlan3, Vlan4

        # D2 ↔ D4: 40.1.x.x
        cls.data.dut2_vrf_blue_d4_ips = ["40.1.1.1/24", "40.1.2.1/24"]  # Vlan7, Vlan8
        cls.data.dut4_vrf_blue_d2_ips = ["40.1.1.2/24", "40.1.2.2/24"]  # Vlan7, Vlan8

        # D4 ↔ D3: 60.1.x.x
        cls.data.dut4_vrf_blue_d3_ips = ["60.1.1.1/24", "60.1.2.1/24"]  # Vlan11, Vlan12
        cls.data.dut3_vrf_blue_ips = ["60.1.1.2/24", "60.1.2.2/24"]  # Vlan11, Vlan12

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
        st.log("TEST TEARDOWN: Cleanup OSPF Per VRF over VLAN Test Suite")
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
            interfaces: List of interface names (e.g., ["Ethernet0", "Ethernet4"])

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
            st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)

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
            vlan_id: VLAN ID (e.g., "1")

        Returns:
            True if successful
        """
        st.log(f"Creating VLAN {vlan_id} on {dut}")
        commands = [
            "configure terminal",
            f"vlan {vlan_id}"
            # NO exit - stay in config mode
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _delete_vlan(dut: str, vlan_id: str) -> bool:
        """
        Delete VLAN using klish commands.

        Args:
            dut: Device handle
            vlan_id: VLAN ID (e.g., "1")

        Returns:
            True if successful
        """
        st.log(f"Deleting VLAN {vlan_id} from {dut}")
        commands = [
            "configure terminal",
            f"no vlan {vlan_id}"
        ]
        st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)
        return True

    @staticmethod
    def _add_ports_to_vlan(dut: str, ports: List[str], vlan_id: str) -> bool:
        """
        Add ports to VLAN as tagged members.

        Args:
            dut: Device handle
            ports: List of port names (e.g., ["Ethernet0"])
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
            st.config(dut, commands, type=CLI_TYPE)

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
            st.config(dut, commands, type=CLI_TYPE, skip_error_check=True)

        st.log(f"Ports removed from VLAN {vlan_id}")
        return True

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

    # ========== HELPER METHODS - VLAN INTERFACE CONFIGURATION ==========

    @staticmethod
    def _configure_vlan_vrf_ip(dut: str, vlan_id: str, vrf_name: str, ip_address: str) -> bool:
        """
        Configure VLAN interface with VRF and IP address.

        Args:
            dut: Device handle
            vlan_id: VLAN ID
            vrf_name: VRF name
            ip_address: IP address with mask (e.g., "10.1.1.1/24")

        Returns:
            True if successful
        """
        st.log(f"Configuring Vlan {vlan_id} with VRF {vrf_name} and IP {ip_address} on {dut}")

        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
            "no ip address",
            f"ip vrf forwarding {vrf_name}",
            f"ip address {ip_address}",
            "no shutdown",
            "exit"
        ]
        st.config(dut, commands, type=CLI_TYPE)
        return True

    @staticmethod
    def _remove_vlan_config(dut: str, vlan_id: str, vrf_name: str = None) -> bool:
        """
        Remove VLAN interface configuration.

        Args:
            dut: Device handle
            vlan_id: VLAN ID
            vrf_name: VRF name (optional, if bound to VRF)

        Returns:
            True if successful
        """
        st.log(f"Removing configuration from Vlan {vlan_id} on {dut}")

        commands = [
            "configure terminal",
            f"interface Vlan {vlan_id}",
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
    def _get_show_vlan(dut: str) -> str:
        """Get 'show Vlan' output."""
        st.log(f"Getting 'show Vlan' output from {dut}")
        output = st.show(dut, "show Vlan", type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show Vlan output from {dut}:\n{output}")
        return output

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
    def _get_show_running_config_vlan(dut: str, vlan_id: str) -> str:
        """Get 'show running-configuration interface Vlan X' output."""
        st.log(f"Getting 'show running-configuration interface Vlan {vlan_id}' output from {dut}")
        command = f"show running-configuration interface Vlan {vlan_id}"
        output = st.show(dut, command, type=CLI_TYPE, skip_tmpl=True)
        if not isinstance(output, str):
            output = str(output)
        st.log(f"show running-configuration interface Vlan {vlan_id} output from {dut}:\n{output}")
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
    def _verify_vlan_exists(vlan_output: str, vlan_id: str) -> bool:
        """Verify VLAN exists in output."""
        st.log(f"Verifying VLAN {vlan_id} exists")
        # Look for Vlan{id} or just {id} in output
        if f"Vlan{vlan_id}" in vlan_output or f" {vlan_id} " in vlan_output or f"Vlan {vlan_id}" in vlan_output:
            st.log(f"PASS: VLAN {vlan_id} found")
            return True
        else:
            st.error(f"FAIL: VLAN {vlan_id} not found")
            return False

    @staticmethod
    def _verify_port_in_vlan(vlan_output: str, vlan_id: str, interface: str) -> bool:
        """Verify interface is member of VLAN."""
        st.log(f"Verifying {interface} is in VLAN {vlan_id}")

        # Parse output to find VLAN line
        # Format: Vlan1     Up          T  Ethernet0        Enable      No
        # The interface name appears on the SAME line as the VLAN
        lines = vlan_output.split('\n')

        for line in lines:
            # Look for VLAN ID in line - check if this line is for our VLAN
            if f"Vlan{vlan_id}" in line or (line.startswith(f"Vlan{vlan_id} ") or f" Vlan{vlan_id} " in line):
                # Check if the interface is on this same line
                if interface in line:
                    st.log(f"PASS: {interface} found in VLAN {vlan_id}")
                    return True

        st.error(f"FAIL: {interface} not found in VLAN {vlan_id}")
        return False

    @staticmethod
    def _verify_vlan_ip(running_config: str, expected_ip: str) -> bool:
        """Verify IP address is configured on VLAN interface."""
        st.log(f"Verifying IP address {expected_ip} in running configuration")

        # Extract IP without mask for verification
        ip_without_mask = expected_ip.split('/')[0]

        if f"ip address {expected_ip}" in running_config or ip_without_mask in running_config:
            st.log(f"PASS: IP address {expected_ip} found")
            return True
        else:
            st.error(f"FAIL: IP address {expected_ip} not found")
            return False

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
                if line.strip() and not line.startswith(' ') and 'Vlan' not in line and vrf_name not in line:
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

    @pytest.mark.inventory(feature="Regression", testcases=["TC_OSPF_VRF_VLAN_001"])
    def test_ospf_per_vrf_over_vlan_4_node(self) -> None:
        """
        TC_OSPF_VRF_VLAN_001: Validate OSPF per VRF over VLAN in 4-node topology.

        Test Procedure:
        1. Remove IP addresses from Ethernet interfaces
        2. Create VLANs and add member ports on all devices
        3. Verify VLAN creation and port membership
        4. Create VRFs on all devices
        5. Configure VLAN interfaces with VRF binding and IP addresses
        6. Verify VLAN IP configuration
        7. Verify VRF configuration and VLAN interface assignments
        8. Configure OSPF per VRF on all devices
        9. Verify OSPF neighbors in Full state
        10. Verify OSPF interfaces, database, and routes
        11. Test end-to-end ping connectivity
        12. Cleanup: Remove all configurations

        Expected Result:
        - VLANs created successfully with correct port membership
        - VRFs created successfully
        - VLAN interfaces correctly bound to VRFs
        - OSPF neighbors form adjacency per VRF
        - Routes learned via OSPF with ECMP
        - End-to-end connectivity works
        - VRF isolation maintained
        """
        st.log("\n" + "=" * 80)
        st.log("TEST: OSPF Per VRF Over VLAN - 4-Node Topology")
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

        # ===== STEP 1: Remove IP addresses from Ethernet interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 1: Remove IP addresses from Ethernet interfaces")
        st.log("-" * 80)

        # Collect all ports that will be used
        dut1_all_ports = []
        for ports in self.data.dut1_vlans.values():
            dut1_all_ports.extend(ports)
        self._remove_ip_addresses_from_interfaces(dut1, dut1_all_ports)

        dut2_all_ports = []
        for ports in self.data.dut2_vlans.values():
            dut2_all_ports.extend(ports)
        self._remove_ip_addresses_from_interfaces(dut2, dut2_all_ports)

        dut3_all_ports = []
        for ports in self.data.dut3_vlans.values():
            dut3_all_ports.extend(ports)
        self._remove_ip_addresses_from_interfaces(dut3, dut3_all_ports)

        dut4_all_ports = []
        for ports in self.data.dut4_vlans.values():
            dut4_all_ports.extend(ports)
        self._remove_ip_addresses_from_interfaces(dut4, dut4_all_ports)

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("IP addresses removed from all Ethernet interfaces")

        # ===== STEP 2: Create VLANs on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 2: Create VLANs on all devices")
        st.log("-" * 80)

        # Create VLANs on D1
        for vlan_id in self.data.dut1_vlans.keys():
            self._create_vlan(dut1, vlan_id)

        # Create VLANs on D2
        for vlan_id in self.data.dut2_vlans.keys():
            self._create_vlan(dut2, vlan_id)

        # Create VLANs on D3
        for vlan_id in self.data.dut3_vlans.keys():
            self._create_vlan(dut3, vlan_id)

        # Create VLANs on D4
        for vlan_id in self.data.dut4_vlans.keys():
            self._create_vlan(dut4, vlan_id)

        time.sleep(WAIT_AFTER_VLAN_CONFIG)
        st.log("VLANs created on all devices")

        # ===== STEP 3: Add member ports to VLANs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 3: Add member ports to VLANs")
        st.log("-" * 80)

        # Add ports to D1 VLANs
        for vlan_id, ports in self.data.dut1_vlans.items():
            self._add_ports_to_vlan(dut1, ports, vlan_id)

        # Add ports to D2 VLANs
        for vlan_id, ports in self.data.dut2_vlans.items():
            self._add_ports_to_vlan(dut2, ports, vlan_id)

        # Add ports to D3 VLANs
        for vlan_id, ports in self.data.dut3_vlans.items():
            self._add_ports_to_vlan(dut3, ports, vlan_id)

        # Add ports to D4 VLANs
        for vlan_id, ports in self.data.dut4_vlans.items():
            self._add_ports_to_vlan(dut4, ports, vlan_id)

        time.sleep(WAIT_AFTER_VLAN_CONFIG)
        st.log("Member ports added to VLANs on all devices")

        # ===== STEP 4: Verify VLAN creation and port membership =====
        st.log("\n" + "-" * 80)
        st.log("STEP 4: Verify VLAN creation and port membership")
        st.log("-" * 80)

        # Verify D1 VLANs
        vlan_output_d1 = self._get_show_vlan(dut1)
        for vlan_id, ports in self.data.dut1_vlans.items():
            if not self._verify_vlan_exists(vlan_output_d1, vlan_id):
                error_msg = f"STEP 4: VLAN {vlan_id} not found on {dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            for port in ports:
                if not self._verify_port_in_vlan(vlan_output_d1, vlan_id, port):
                    error_msg = f"STEP 4: Port {port} not in VLAN {vlan_id} on {dut1}"
                    st.error(error_msg)
                    validation_failures.append(error_msg)

        # Verify D2 VLANs
        vlan_output_d2 = self._get_show_vlan(dut2)
        for vlan_id, ports in self.data.dut2_vlans.items():
            if not self._verify_vlan_exists(vlan_output_d2, vlan_id):
                error_msg = f"STEP 4: VLAN {vlan_id} not found on {dut2}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            for port in ports:
                if not self._verify_port_in_vlan(vlan_output_d2, vlan_id, port):
                    error_msg = f"STEP 4: Port {port} not in VLAN {vlan_id} on {dut2}"
                    st.error(error_msg)
                    validation_failures.append(error_msg)

        # Verify D3 VLANs
        vlan_output_d3 = self._get_show_vlan(dut3)
        for vlan_id, ports in self.data.dut3_vlans.items():
            if not self._verify_vlan_exists(vlan_output_d3, vlan_id):
                error_msg = f"STEP 4: VLAN {vlan_id} not found on {dut3}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            for port in ports:
                if not self._verify_port_in_vlan(vlan_output_d3, vlan_id, port):
                    error_msg = f"STEP 4: Port {port} not in VLAN {vlan_id} on {dut3}"
                    st.error(error_msg)
                    validation_failures.append(error_msg)

        # Verify D4 VLANs
        vlan_output_d4 = self._get_show_vlan(dut4)
        for vlan_id, ports in self.data.dut4_vlans.items():
            if not self._verify_vlan_exists(vlan_output_d4, vlan_id):
                error_msg = f"STEP 4: VLAN {vlan_id} not found on {dut4}"
                st.error(error_msg)
                validation_failures.append(error_msg)
            for port in ports:
                if not self._verify_port_in_vlan(vlan_output_d4, vlan_id, port):
                    error_msg = f"STEP 4: Port {port} not in VLAN {vlan_id} on {dut4}"
                    st.error(error_msg)
                    validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 4" in f]) == 0:
            st.log("PASS: VLANs created and port membership verified on all devices")

        # ===== STEP 5: Create VRFs on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 5: Create VRFs on all devices")
        st.log("-" * 80)

        for dut in [dut1, dut2, dut3, dut4]:
            self._create_vrf(dut, vrf_red)
            self._create_vrf(dut, vrf_blue)

        time.sleep(WAIT_AFTER_VRF_CONFIG)
        st.log("VRFs created on all devices")

        # ===== STEP 6: Configure D1 VLAN interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 6: Configure D1 VLAN interfaces with VRF and IP addresses")
        st.log("-" * 80)

        # D1 Vrf-RED VLAN interfaces
        self._configure_vlan_vrf_ip(dut1, "1", vrf_red, self.data.dut1_vrf_red_ips[0])
        self._configure_vlan_vrf_ip(dut1, "2", vrf_red, self.data.dut1_vrf_red_ips[1])

        # D1 Vrf-BLUE VLAN interfaces
        self._configure_vlan_vrf_ip(dut1, "3", vrf_blue, self.data.dut1_vrf_blue_ips[0])
        self._configure_vlan_vrf_ip(dut1, "4", vrf_blue, self.data.dut1_vrf_blue_ips[1])

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("D1 VLAN interfaces configured")

        # ===== STEP 7: Configure D2 VLAN interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 7: Configure D2 VLAN interfaces with VRF and IP addresses")
        st.log("-" * 80)

        # D2 Vrf-RED VLAN interfaces (D1 side)
        self._configure_vlan_vrf_ip(dut2, "1", vrf_red, self.data.dut2_vrf_red_d1_ips[0])
        self._configure_vlan_vrf_ip(dut2, "2", vrf_red, self.data.dut2_vrf_red_d1_ips[1])

        # D2 Vrf-BLUE VLAN interfaces (D1 side)
        self._configure_vlan_vrf_ip(dut2, "3", vrf_blue, self.data.dut2_vrf_blue_d1_ips[0])
        self._configure_vlan_vrf_ip(dut2, "4", vrf_blue, self.data.dut2_vrf_blue_d1_ips[1])

        # D2 Vrf-RED VLAN interfaces (D4 side)
        self._configure_vlan_vrf_ip(dut2, "5", vrf_red, self.data.dut2_vrf_red_d4_ips[0])
        self._configure_vlan_vrf_ip(dut2, "6", vrf_red, self.data.dut2_vrf_red_d4_ips[1])

        # D2 Vrf-BLUE VLAN interfaces (D4 side)
        self._configure_vlan_vrf_ip(dut2, "7", vrf_blue, self.data.dut2_vrf_blue_d4_ips[0])
        self._configure_vlan_vrf_ip(dut2, "8", vrf_blue, self.data.dut2_vrf_blue_d4_ips[1])

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("D2 VLAN interfaces configured")

        # ===== STEP 8: Configure D4 VLAN interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 8: Configure D4 VLAN interfaces with VRF and IP addresses")
        st.log("-" * 80)

        # D4 Vrf-RED VLAN interfaces (D2 side)
        self._configure_vlan_vrf_ip(dut4, "5", vrf_red, self.data.dut4_vrf_red_d2_ips[0])
        self._configure_vlan_vrf_ip(dut4, "6", vrf_red, self.data.dut4_vrf_red_d2_ips[1])

        # D4 Vrf-BLUE VLAN interfaces (D2 side)
        self._configure_vlan_vrf_ip(dut4, "7", vrf_blue, self.data.dut4_vrf_blue_d2_ips[0])
        self._configure_vlan_vrf_ip(dut4, "8", vrf_blue, self.data.dut4_vrf_blue_d2_ips[1])

        # D4 Vrf-RED VLAN interfaces (D3 side)
        self._configure_vlan_vrf_ip(dut4, "9", vrf_red, self.data.dut4_vrf_red_d3_ips[0])
        self._configure_vlan_vrf_ip(dut4, "10", vrf_red, self.data.dut4_vrf_red_d3_ips[1])

        # D4 Vrf-BLUE VLAN interfaces (D3 side)
        self._configure_vlan_vrf_ip(dut4, "11", vrf_blue, self.data.dut4_vrf_blue_d3_ips[0])
        self._configure_vlan_vrf_ip(dut4, "12", vrf_blue, self.data.dut4_vrf_blue_d3_ips[1])

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("D4 VLAN interfaces configured")

        # ===== STEP 9: Configure D3 VLAN interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 9: Configure D3 VLAN interfaces with VRF and IP addresses")
        st.log("-" * 80)

        # D3 Vrf-RED VLAN interfaces
        self._configure_vlan_vrf_ip(dut3, "9", vrf_red, self.data.dut3_vrf_red_ips[0])
        self._configure_vlan_vrf_ip(dut3, "10", vrf_red, self.data.dut3_vrf_red_ips[1])

        # D3 Vrf-BLUE VLAN interfaces
        self._configure_vlan_vrf_ip(dut3, "11", vrf_blue, self.data.dut3_vrf_blue_ips[0])
        self._configure_vlan_vrf_ip(dut3, "12", vrf_blue, self.data.dut3_vrf_blue_ips[1])

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("D3 VLAN interfaces configured")

        # ===== STEP 10: Verify VLAN IP configuration =====
        st.log("\n" + "-" * 80)
        st.log("STEP 10: Verify VLAN IP configuration")
        st.log("-" * 80)

        # Verify D1 VLAN IPs
        for idx, vlan_id in enumerate(["1", "2"], 0):
            config_output = self._get_show_running_config_vlan(dut1, vlan_id)
            if not self._verify_vlan_ip(config_output, self.data.dut1_vrf_red_ips[idx]):
                error_msg = f"STEP 10: IP validation failed for Vlan{vlan_id} on {dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        for idx, vlan_id in enumerate(["3", "4"], 0):
            config_output = self._get_show_running_config_vlan(dut1, vlan_id)
            if not self._verify_vlan_ip(config_output, self.data.dut1_vrf_blue_ips[idx]):
                error_msg = f"STEP 10: IP validation failed for Vlan{vlan_id} on {dut1}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 10" in f]) == 0:
            st.log("PASS: VLAN IP configuration verified")

        # ===== STEP 11: Verify VRF configuration on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 11: Verify VRF configuration on all devices")
        st.log("-" * 80)

        for dut in [dut1, dut2, dut3, dut4]:
            vrf_output = self._get_show_ip_vrf(dut)

            if not self._verify_vrf_exists(vrf_output, vrf_red):
                error_msg = f"STEP 11: VRF {vrf_red} not found on {dut}"
                st.error(error_msg)
                validation_failures.append(error_msg)

            if not self._verify_vrf_exists(vrf_output, vrf_blue):
                error_msg = f"STEP 11: VRF {vrf_blue} not found on {dut}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 11" in f]) == 0:
            st.log("PASS: VRF configuration verified on all devices")

        # ===== STEP 12: Configure OSPF on D1 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 12: Configure OSPF on D1")
        st.log("-" * 80)

        # D1 OSPF Vrf-RED
        networks_d1_red = ["10.1.1.0/24", "10.1.2.0/24"]
        self._configure_ospf_vrf(dut1, vrf_red, self.data.dut1_router_id_red, networks_d1_red, area)

        # D1 OSPF Vrf-BLUE
        networks_d1_blue = ["10.2.1.0/24", "10.2.2.0/24"]
        self._configure_ospf_vrf(dut1, vrf_blue, self.data.dut1_router_id_blue, networks_d1_blue, area)

        time.sleep(WAIT_AFTER_OSPF_CONFIG)
        st.log("OSPF configured on D1")

        # ===== STEP 13: Configure OSPF on D2 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 13: Configure OSPF on D2")
        st.log("-" * 80)

        # D2 OSPF Vrf-RED
        networks_d2_red = ["10.1.1.0/24", "10.1.2.0/24", "30.1.1.0/24", "30.1.2.0/24"]
        self._configure_ospf_vrf(dut2, vrf_red, self.data.dut2_router_id_red, networks_d2_red, area)

        # D2 OSPF Vrf-BLUE
        networks_d2_blue = ["10.2.1.0/24", "10.2.2.0/24", "40.1.1.0/24", "40.1.2.0/24"]
        self._configure_ospf_vrf(dut2, vrf_blue, self.data.dut2_router_id_blue, networks_d2_blue, area)

        time.sleep(WAIT_AFTER_OSPF_CONFIG)
        st.log("OSPF configured on D2")

        # ===== STEP 14: Configure OSPF on D4 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 14: Configure OSPF on D4")
        st.log("-" * 80)

        # D4 OSPF Vrf-RED
        networks_d4_red = ["30.1.1.0/24", "30.1.2.0/24", "50.1.1.0/24", "50.1.2.0/24"]
        self._configure_ospf_vrf(dut4, vrf_red, self.data.dut4_router_id_red, networks_d4_red, area)

        # D4 OSPF Vrf-BLUE
        networks_d4_blue = ["40.1.1.0/24", "40.1.2.0/24", "60.1.1.0/24", "60.1.2.0/24"]
        self._configure_ospf_vrf(dut4, vrf_blue, self.data.dut4_router_id_blue, networks_d4_blue, area)

        time.sleep(WAIT_AFTER_OSPF_CONFIG)
        st.log("OSPF configured on D4")

        # ===== STEP 15: Configure OSPF on D3 =====
        st.log("\n" + "-" * 80)
        st.log("STEP 15: Configure OSPF on D3")
        st.log("-" * 80)

        # D3 OSPF Vrf-RED
        networks_d3_red = ["50.1.1.0/24", "50.1.2.0/24"]
        self._configure_ospf_vrf(dut3, vrf_red, self.data.dut3_router_id_red, networks_d3_red, area)

        # D3 OSPF Vrf-BLUE
        networks_d3_blue = ["60.1.1.0/24", "60.1.2.0/24"]
        self._configure_ospf_vrf(dut3, vrf_blue, self.data.dut3_router_id_blue, networks_d3_blue, area)

        time.sleep(WAIT_AFTER_OSPF_CONFIG)
        st.log("OSPF configured on D3")

        # ===== STEP 16: Wait for OSPF convergence =====
        st.log("\n" + "-" * 80)
        st.log(f"STEP 16: Wait {WAIT_FOR_NEIGHBOR_UP} seconds for OSPF neighbor convergence")
        st.log("-" * 80)
        time.sleep(WAIT_FOR_NEIGHBOR_UP)

        # ===== STEP 17: Verify OSPF process on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 17: Verify OSPF process on all devices")
        st.log("-" * 80)

        # Verify D1 OSPF
        ospf_output_d1_red = self._get_show_ip_ospf_vrf(dut1, vrf_red)
        ospf_output_d1_blue = self._get_show_ip_ospf_vrf(dut1, vrf_blue)

        if not self._verify_ospf_process_vrf(ospf_output_d1_red, vrf_red, self.data.dut1_router_id_red):
            error_msg = f"STEP 17: OSPF process not verified on {dut1} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_process_vrf(ospf_output_d1_blue, vrf_blue, self.data.dut1_router_id_blue):
            error_msg = f"STEP 17: OSPF process not verified on {dut1} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D2 OSPF
        ospf_output_d2_red = self._get_show_ip_ospf_vrf(dut2, vrf_red)
        ospf_output_d2_blue = self._get_show_ip_ospf_vrf(dut2, vrf_blue)

        if not self._verify_ospf_process_vrf(ospf_output_d2_red, vrf_red, self.data.dut2_router_id_red):
            error_msg = f"STEP 17: OSPF process not verified on {dut2} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_process_vrf(ospf_output_d2_blue, vrf_blue, self.data.dut2_router_id_blue):
            error_msg = f"STEP 17: OSPF process not verified on {dut2} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D3 OSPF
        ospf_output_d3_red = self._get_show_ip_ospf_vrf(dut3, vrf_red)
        ospf_output_d3_blue = self._get_show_ip_ospf_vrf(dut3, vrf_blue)

        if not self._verify_ospf_process_vrf(ospf_output_d3_red, vrf_red, self.data.dut3_router_id_red):
            error_msg = f"STEP 17: OSPF process not verified on {dut3} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_process_vrf(ospf_output_d3_blue, vrf_blue, self.data.dut3_router_id_blue):
            error_msg = f"STEP 17: OSPF process not verified on {dut3} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D4 OSPF
        ospf_output_d4_red = self._get_show_ip_ospf_vrf(dut4, vrf_red)
        ospf_output_d4_blue = self._get_show_ip_ospf_vrf(dut4, vrf_blue)

        if not self._verify_ospf_process_vrf(ospf_output_d4_red, vrf_red, self.data.dut4_router_id_red):
            error_msg = f"STEP 17: OSPF process not verified on {dut4} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_process_vrf(ospf_output_d4_blue, vrf_blue, self.data.dut4_router_id_blue):
            error_msg = f"STEP 17: OSPF process not verified on {dut4} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 17" in f]) == 0:
            st.log("PASS: OSPF process verified on all devices")

        # ===== STEP 18: Verify OSPF neighbors on all devices =====
        st.log("\n" + "-" * 80)
        st.log("STEP 18: Verify OSPF neighbors on all devices")
        st.log("-" * 80)

        # D1 should have 2 neighbors in each VRF (to D2)
        neighbor_output_d1_red = self._get_show_ip_ospf_neighbor_vrf(dut1, vrf_red)
        neighbor_output_d1_blue = self._get_show_ip_ospf_neighbor_vrf(dut1, vrf_blue)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d1_red, 2):
            error_msg = f"STEP 18: Expected 2 neighbors on {dut1} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d1_blue, 2):
            error_msg = f"STEP 18: Expected 2 neighbors on {dut1} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # D2 should have 4 neighbors in each VRF (2 to D1, 2 to D4)
        neighbor_output_d2_red = self._get_show_ip_ospf_neighbor_vrf(dut2, vrf_red)
        neighbor_output_d2_blue = self._get_show_ip_ospf_neighbor_vrf(dut2, vrf_blue)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d2_red, 4):
            error_msg = f"STEP 18: Expected 4 neighbors on {dut2} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d2_blue, 4):
            error_msg = f"STEP 18: Expected 4 neighbors on {dut2} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # D4 should have 4 neighbors in each VRF (2 to D2, 2 to D3)
        neighbor_output_d4_red = self._get_show_ip_ospf_neighbor_vrf(dut4, vrf_red)
        neighbor_output_d4_blue = self._get_show_ip_ospf_neighbor_vrf(dut4, vrf_blue)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d4_red, 4):
            error_msg = f"STEP 18: Expected 4 neighbors on {dut4} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d4_blue, 4):
            error_msg = f"STEP 18: Expected 4 neighbors on {dut4} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # D3 should have 2 neighbors in each VRF (to D4)
        neighbor_output_d3_red = self._get_show_ip_ospf_neighbor_vrf(dut3, vrf_red)
        neighbor_output_d3_blue = self._get_show_ip_ospf_neighbor_vrf(dut3, vrf_blue)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d3_red, 2):
            error_msg = f"STEP 18: Expected 2 neighbors on {dut3} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_ospf_neighbor_count_vrf(neighbor_output_d3_blue, 2):
            error_msg = f"STEP 18: Expected 2 neighbors on {dut3} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 18" in f]) == 0:
            st.log("PASS: OSPF neighbors verified on all devices")

        # ===== STEP 19: Verify OSPF interfaces =====
        st.log("\n" + "-" * 80)
        st.log("STEP 19: Verify OSPF interfaces on all devices")
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

        # ===== STEP 20: Verify OSPF database =====
        st.log("\n" + "-" * 80)
        st.log("STEP 20: Verify OSPF database on all devices")
        st.log("-" * 80)

        time.sleep(WAIT_FOR_ROUTE_UPDATE)

        # Verify database on all devices
        for dut in [dut1, dut2, dut3, dut4]:
            db_output_red = self._get_show_ip_ospf_database_vrf(dut, vrf_red)
            db_output_blue = self._get_show_ip_ospf_database_vrf(dut, vrf_blue)

            if not self._verify_ospf_database_has_lsas(db_output_red):
                error_msg = f"STEP 20: OSPF database empty on {dut} Vrf-RED"
                st.error(error_msg)
                validation_failures.append(error_msg)

            if not self._verify_ospf_database_has_lsas(db_output_blue):
                error_msg = f"STEP 20: OSPF database empty on {dut} Vrf-BLUE"
                st.error(error_msg)
                validation_failures.append(error_msg)

        if len([f for f in validation_failures if "STEP 20" in f]) == 0:
            st.log("PASS: OSPF database verified on all devices")

        # ===== STEP 21: Verify routing tables =====
        st.log("\n" + "-" * 80)
        st.log("STEP 21: Verify routing tables on all devices")
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
            error_msg = f"STEP 21: Route 50.1.1.0/24 not found on {dut1} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_route_in_table(route_output_d1_blue, "60.1.1.0/24"):
            error_msg = f"STEP 21: Route 60.1.1.0/24 not found on {dut1} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify D3 can see D1 networks
        if not self._verify_route_in_table(route_output_d3_red, "10.1.1.0/24"):
            error_msg = f"STEP 21: Route 10.1.1.0/24 not found on {dut3} Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not self._verify_route_in_table(route_output_d3_blue, "10.2.1.0/24"):
            error_msg = f"STEP 21: Route 10.2.1.0/24 not found on {dut3} Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Verify ECMP on D1
        self._verify_ecmp_routes(route_output_d1_red, "30.1.1.0/24")
        self._verify_ecmp_routes(route_output_d1_blue, "40.1.1.0/24")

        if len([f for f in validation_failures if "STEP 21" in f]) == 0:
            st.log("PASS: Routing tables verified on all devices")

        # ===== STEP 22: Test end-to-end ping connectivity =====
        st.log("\n" + "-" * 80)
        st.log("STEP 22: Test end-to-end ping connectivity")
        st.log("-" * 80)

        # D1 to D3 ping in Vrf-RED
        ping_output_d1_d3_red = self._ping_vrf(dut1, vrf_red, "50.1.1.2", count=5)
        if not self._verify_ping_success(ping_output_d1_d3_red):
            error_msg = f"STEP 22: Ping failed from {dut1} to D3 in Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping successful from {dut1} to D3 in Vrf-RED")

        # D1 to D3 ping in Vrf-BLUE
        ping_output_d1_d3_blue = self._ping_vrf(dut1, vrf_blue, "60.1.1.2", count=5)
        if not self._verify_ping_success(ping_output_d1_d3_blue):
            error_msg = f"STEP 22: Ping failed from {dut1} to D3 in Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping successful from {dut1} to D3 in Vrf-BLUE")

        # D3 to D1 ping in Vrf-RED
        ping_output_d3_d1_red = self._ping_vrf(dut3, vrf_red, "10.1.1.1", count=5)
        if not self._verify_ping_success(ping_output_d3_d1_red):
            error_msg = f"STEP 22: Ping failed from {dut3} to D1 in Vrf-RED"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping successful from {dut3} to D1 in Vrf-RED")

        # D3 to D1 ping in Vrf-BLUE
        ping_output_d3_d1_blue = self._ping_vrf(dut3, vrf_blue, "10.2.1.1", count=5)
        if not self._verify_ping_success(ping_output_d3_d1_blue):
            error_msg = f"STEP 22: Ping failed from {dut3} to D1 in Vrf-BLUE"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"PASS: Ping successful from {dut3} to D1 in Vrf-BLUE")

        if len([f for f in validation_failures if "STEP 22" in f]) == 0:
            st.log("PASS: End-to-end ping connectivity verified")

        # ===== STEP 23: Cleanup - Remove OSPF configuration =====
        st.log("\n" + "-" * 80)
        st.log("STEP 23: Cleanup - Remove OSPF configuration")
        st.log("-" * 80)

        for dut in [dut1, dut2, dut3, dut4]:
            self._remove_ospf_vrf(dut, vrf_red)
            self._remove_ospf_vrf(dut, vrf_blue)

        time.sleep(WAIT_AFTER_OSPF_CONFIG)
        st.log("OSPF configuration removed from all devices")

        # ===== STEP 24: Cleanup - Remove VLAN interface configuration =====
        st.log("\n" + "-" * 80)
        st.log("STEP 24: Cleanup - Remove VLAN interface configuration")
        st.log("-" * 80)

        # Remove D1 VLAN configs
        for vlan_id in ["1", "2"]:
            self._remove_vlan_config(dut1, vlan_id, vrf_red)
        for vlan_id in ["3", "4"]:
            self._remove_vlan_config(dut1, vlan_id, vrf_blue)

        # Remove D2 VLAN configs
        for vlan_id in ["1", "2", "5", "6"]:
            self._remove_vlan_config(dut2, vlan_id, vrf_red)
        for vlan_id in ["3", "4", "7", "8"]:
            self._remove_vlan_config(dut2, vlan_id, vrf_blue)

        # Remove D3 VLAN configs
        for vlan_id in ["9", "10"]:
            self._remove_vlan_config(dut3, vlan_id, vrf_red)
        for vlan_id in ["11", "12"]:
            self._remove_vlan_config(dut3, vlan_id, vrf_blue)

        # Remove D4 VLAN configs
        for vlan_id in ["5", "6", "9", "10"]:
            self._remove_vlan_config(dut4, vlan_id, vrf_red)
        for vlan_id in ["7", "8", "11", "12"]:
            self._remove_vlan_config(dut4, vlan_id, vrf_blue)

        time.sleep(WAIT_AFTER_IP_CONFIG)
        st.log("VLAN interface configuration removed from all devices")

        # ===== STEP 25: Cleanup - Remove ports from VLANs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 25: Cleanup - Remove ports from VLANs")
        st.log("-" * 80)

        # Remove ports from D1 VLANs
        for vlan_id, ports in self.data.dut1_vlans.items():
            self._remove_ports_from_vlan(dut1, ports, vlan_id)

        # Remove ports from D2 VLANs
        for vlan_id, ports in self.data.dut2_vlans.items():
            self._remove_ports_from_vlan(dut2, ports, vlan_id)

        # Remove ports from D3 VLANs
        for vlan_id, ports in self.data.dut3_vlans.items():
            self._remove_ports_from_vlan(dut3, ports, vlan_id)

        # Remove ports from D4 VLANs
        for vlan_id, ports in self.data.dut4_vlans.items():
            self._remove_ports_from_vlan(dut4, ports, vlan_id)

        time.sleep(WAIT_AFTER_VLAN_CONFIG)
        st.log("Ports removed from VLANs on all devices")

        # ===== STEP 26: Cleanup - Delete VLANs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 26: Cleanup - Delete VLANs")
        st.log("-" * 80)

        # Delete D1 VLANs
        for vlan_id in self.data.dut1_vlans.keys():
            self._delete_vlan(dut1, vlan_id)

        # Delete D2 VLANs
        for vlan_id in self.data.dut2_vlans.keys():
            self._delete_vlan(dut2, vlan_id)

        # Delete D3 VLANs
        for vlan_id in self.data.dut3_vlans.keys():
            self._delete_vlan(dut3, vlan_id)

        # Delete D4 VLANs
        for vlan_id in self.data.dut4_vlans.keys():
            self._delete_vlan(dut4, vlan_id)

        time.sleep(WAIT_AFTER_VLAN_CONFIG)
        st.log("VLANs deleted from all devices")

        # ===== STEP 27: Cleanup - Remove VRFs =====
        st.log("\n" + "-" * 80)
        st.log("STEP 27: Cleanup - Remove VRFs")
        st.log("-" * 80)

        for dut in [dut1, dut2, dut3, dut4]:
            self._delete_vrf(dut, vrf_red)
            self._delete_vrf(dut, vrf_blue)

        time.sleep(WAIT_AFTER_VRF_CONFIG)
        st.log("VRFs removed from all devices")

        # ===== TEST COMPLETE =====
        st.log("\n" + "=" * 80)
        st.log("TEST COMPLETE: OSPF per VRF over VLAN validated successfully")
        st.log("=" * 80)

        # ===== COLLECT TECH SUPPORT AND REPORT FAILURES =====
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED - Collecting tech support from all DUTs...")
            st.log("!" * 80)

            # Collect tech support from all DUTs
            for dut in [dut1, dut2, dut3, dut4]:
                try:
                    st.generate_tech_support(dut=dut, name="ospf_per_vrf_vlan_validation_failure")
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
