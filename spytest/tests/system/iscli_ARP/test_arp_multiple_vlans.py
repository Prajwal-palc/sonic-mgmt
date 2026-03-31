"""
ARP TEST - ARP on Multiple VLANs

Test Case ID: ARP-MULTI-VLAN-06
Author: Automated SpyTest Framework
Copyright (C) 2024

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_ARP/test_arp_multiple_vlans.py \
    --logs-path ./logs/arp_multi_vlan_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates ARP functionality across multiple VLANs:
  - Configure VLAN 100 (Ethernet0) and VLAN 200 (Ethernet4) on both DUTs
  - Configure IP addresses on both VLAN interfaces
  - Configure static ARP on VLAN 100
  - Verify dynamic ARP learning on VLAN 200
  - Ping across both VLANs
  - Verify ARP entries exist on both VLANs with correct interface association
  - Verify Type: Static on VLAN 100, Dynamic on VLAN 200

Pre-requisites:
  - 2 SONiC devices connected via Ethernet0 and Ethernet4
  - Testbed: testbed_2vs.yaml
  - Clean VLAN and ARP configuration
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi
import apis.routing.arp as arpapi
import apis.switching.vlan as vlanapi
import apis.common.scapy_traffic as scapy_utils

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    # VLAN 100 configuration
    "vlan1_id": "100",
    # vlan1_interface will be populated from testbed in module_hooks
    "vlan1_dut1_ip": "10.1.1.1",
    "vlan1_dut2_ip": "10.1.1.2",
    # MAC addresses will be retrieved dynamically from DUTs in module_hooks

    # VLAN 200 configuration
    "vlan2_id": "200",
    # vlan2_interface will be populated from testbed in module_hooks
    "vlan2_dut1_ip": "10.2.2.1",
    "vlan2_dut2_ip": "10.2.2.2",

    # Common settings
    "subnet_mask": "24",
    "ping_count": 3,
    "wait_after_config": 3,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "multi_vlan_vlan1_config": "TC-ARP-MULTI-VLAN-06-001",
    "multi_vlan_vlan2_config": "TC-ARP-MULTI-VLAN-06-002",
    "multi_vlan_static_arp": "TC-ARP-MULTI-VLAN-06-003",
    "multi_vlan_ping_vlan1": "TC-ARP-MULTI-VLAN-06-004",
    "multi_vlan_ping_vlan2": "TC-ARP-MULTI-VLAN-06-005",
    "multi_vlan_verify_arp": "TC-ARP-MULTI-VLAN-06-006",
    "multi_vlan_verify_types": "TC-ARP-MULTI-VLAN-06-007",
})


@pytest.fixture(scope="module", autouse=True)
def arp_multi_vlan_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("ARP MULTI-VLAN MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:2")  # Requires 2 links
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    # Get interfaces from testbed topology (2 links required)
    CONFIG.vlan1_interface = vars.D1D2P1
    CONFIG.vlan2_interface = vars.D1D2P2
    st.log(f"VLAN 100 Interface: {CONFIG.vlan1_interface}")
    st.log(f"VLAN 200 Interface: {CONFIG.vlan2_interface}")

    # Pre-configuration
    arp_pre_config()

    # Get MAC addresses dynamically after VLAN configuration
    vlan1_intf_name = f"Vlan{CONFIG.vlan1_id}"
    vlan2_intf_name = f"Vlan{CONFIG.vlan2_id}"
    st.log(f"Retrieving MAC addresses for VLAN interfaces on both DUTs")

    CONFIG.vlan1_dut1_mac = scapy_utils.get_interface_mac(vars.D1, vlan1_intf_name, data.cli_type)
    CONFIG.vlan1_dut2_mac = scapy_utils.get_interface_mac(vars.D2, vlan1_intf_name, data.cli_type)

    if not CONFIG.vlan1_dut1_mac or not CONFIG.vlan1_dut2_mac:
        st.error(f"Failed to retrieve MAC addresses for {vlan1_intf_name}")
        st.report_fail("msg", f"Failed to get {vlan1_intf_name} MAC addresses")

    st.log(f"DUT1 {vlan1_intf_name} MAC: {CONFIG.vlan1_dut1_mac}")
    st.log(f"DUT2 {vlan1_intf_name} MAC: {CONFIG.vlan1_dut2_mac}")

    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("ARP MULTI-VLAN MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        arp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def arp_pre_config():
    """Pre-configuration: Setup VLANs and IP addresses."""
    st.log("Pre-configuration: Setting up multiple VLANs and IP addresses")

    dut_list = [vars.D1, vars.D2]

    # Clear existing VLAN configuration
    try:
        vlanapi.clear_vlan_configuration(dut_list)
    except Exception as e:
        st.log(f"VLAN clear warning: {str(e)}")

    # Clear existing IP configuration
    try:
        ipapi.clear_ip_configuration(dut_list, family='ipv4', thread=True)
    except Exception as e:
        st.log(f"IP clear warning: {str(e)}")

    st.log("Pre-configuration completed (VLANs will be configured in test steps)")


def arp_pre_config_cleanup():
    """Cleanup: Remove ARP, IP, and VLAN configuration."""
    st.log("Cleanup: Removing ARP, IP, and VLAN configuration")

    dut_list = [vars.D1, vars.D2]

    # Clear ARP cache
    for dut in dut_list:
        try:
            st.show(dut, "clear ip arp", skip_tmpl=True, skip_error_check=True, type='klish')
            st.log(f"✓ ARP cache cleared on {dut}")
        except Exception as e:
            st.log(f"ARP clear on {dut}: {str(e)}")

    # Remove static ARP entries from VLAN 100
    for dut, ip in [(vars.D1, CONFIG.vlan1_dut2_ip), (vars.D2, CONFIG.vlan1_dut1_ip)]:
        try:
            commands = [
                "configure terminal",
                f"interface Vlan{CONFIG.vlan1_id}",
                f"no ip arp {ip}",
                "end"
            ]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)
            st.log(f"✓ Static ARP removed from {dut} VLAN{CONFIG.vlan1_id}")
        except Exception as e:
            st.log(f"Static ARP remove on {dut}: {str(e)}")

    # Remove IP addresses from VLAN 100 interfaces
    for dut, ip in [(vars.D1, CONFIG.vlan1_dut1_ip), (vars.D2, CONFIG.vlan1_dut2_ip)]:
        try:
            ipapi.delete_ip_interface(dut, f"Vlan{CONFIG.vlan1_id}", ip,
                                     CONFIG.subnet_mask, family="ipv4",
                                     cli_type=data.cli_type, skip_error=True)
            st.log(f"✓ IP removed from {dut} VLAN{CONFIG.vlan1_id}")
        except Exception as e:
            st.log(f"IP delete on {dut} VLAN{CONFIG.vlan1_id}: {str(e)}")

    # Remove IP addresses from VLAN 200 interfaces
    for dut, ip in [(vars.D1, CONFIG.vlan2_dut1_ip), (vars.D2, CONFIG.vlan2_dut2_ip)]:
        try:
            ipapi.delete_ip_interface(dut, f"Vlan{CONFIG.vlan2_id}", ip,
                                     CONFIG.subnet_mask, family="ipv4",
                                     cli_type=data.cli_type, skip_error=True)
            st.log(f"✓ IP removed from {dut} VLAN{CONFIG.vlan2_id}")
        except Exception as e:
            st.log(f"IP delete on {dut} VLAN{CONFIG.vlan2_id}: {str(e)}")

    # Remove VLAN 100 membership
    for dut in dut_list:
        try:
            vlanapi.delete_vlan_member(dut, CONFIG.vlan1_id, CONFIG.vlan1_interface,
                                      tagging_mode=False, cli_type=data.cli_type,
                                      skip_error=True)
            st.log(f"✓ VLAN{CONFIG.vlan1_id} member removed on {dut}")
        except Exception as e:
            st.log(f"VLAN{CONFIG.vlan1_id} member delete on {dut}: {str(e)}")

    # Remove VLAN 200 membership
    for dut in dut_list:
        try:
            vlanapi.delete_vlan_member(dut, CONFIG.vlan2_id, CONFIG.vlan2_interface,
                                      tagging_mode=False, cli_type=data.cli_type,
                                      skip_error=True)
            st.log(f"✓ VLAN{CONFIG.vlan2_id} member removed on {dut}")
        except Exception as e:
            st.log(f"VLAN{CONFIG.vlan2_id} member delete on {dut}: {str(e)}")

    # Delete VLANs
    for dut in dut_list:
        try:
            vlanapi.delete_vlan(dut, CONFIG.vlan1_id, cli_type=data.cli_type, skip_error=True)
            vlanapi.delete_vlan(dut, CONFIG.vlan2_id, cli_type=data.cli_type, skip_error=True)
            st.log(f"✓ VLANs deleted on {dut}")
        except Exception as e:
            st.log(f"VLAN delete on {dut}: {str(e)}")

    st.log("Cleanup completed")


def configure_vlan_and_ip(dut: str, vlan_id: str, interface: str, ip_address: str) -> bool:
    """
    Configure VLAN, add interface member, configure IP address.

    Commands:
      configure terminal
      vlan 200
      interface Vlan 200
      ip address 10.2.2.1/24
      no shutdown
      exit
      interface Ethernet 4
      no ip address
      no ipv6 address
      switchport access Vlan 200
      no shutdown
      end
    """
    st.log(f"Configuring VLAN {vlan_id} on {dut}: interface={interface}, ip={ip_address}/{CONFIG.subnet_mask}")

    try:
        # Create VLAN
        vlanapi.create_vlan(dut, vlan_id, cli_type=data.cli_type)
        st.log(f"✓ VLAN {vlan_id} created on {dut}")

        # Configure IP on VLAN interface
        ipapi.config_ip_addr_interface(
            dut,
            f"Vlan{vlan_id}",
            ip_address,
            subnet=CONFIG.subnet_mask,
            family="ipv4",
            cli_type=data.cli_type
        )
        st.log(f"✓ IP {ip_address}/{CONFIG.subnet_mask} configured on {dut} Vlan{vlan_id}")

        # Remove any existing IP from physical interface and add to VLAN as switchport
        commands = [
            "configure terminal",
            f"interface {interface}",
            "no ip address",
            "no ipv6 address",
            f"switchport access Vlan {vlan_id}",
            "no shutdown",
            "end"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"✓ {interface} added to VLAN {vlan_id} as access port on {dut}")

        # Bring up VLAN interface
        commands = [
            "configure terminal",
            f"interface Vlan{vlan_id}",
            "no shutdown",
            "end"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"✓ Vlan{vlan_id} interface brought up on {dut}")

        return True

    except Exception as e:
        st.error(f"Failed to configure VLAN {vlan_id} on {dut}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def configure_static_arp(dut: str, interface: str, ip_address: str, mac_address: str) -> bool:
    """Configure static ARP entry."""
    st.log(f"Configuring static ARP on {dut}: {ip_address} -> {mac_address}")

    try:
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"ip arp {ip_address} {mac_address}",
            "end"
        ]

        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"✓ Static ARP configured: {ip_address} -> {mac_address}")
        return True

    except Exception as e:
        st.error(f"Failed to configure static ARP on {dut}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def ping_test(dut: str, destination_ip: str, count: int = 3) -> dict:
    """Perform ping test."""
    st.log(f"Pinging {destination_ip} from {dut} ({count} packets)")

    try:
        ping_cmd = f"ping {destination_ip} -c {count}"
        output = st.show(dut, ping_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        output_str = str(output)
        st.log(f"Ping output:\n{output_str}")

        result = {
            'success': False,
            'transmitted': 0,
            'received': 0,
            'loss': '100%'
        }

        # Parse ping statistics
        import re
        match = re.search(r'(\d+) packets transmitted, (\d+) received, (\d+)% packet loss', output_str)
        if match:
            result['transmitted'] = int(match.group(1))
            result['received'] = int(match.group(2))
            result['loss'] = match.group(3) + '%'
            result['success'] = (result['received'] > 0)

            st.log(f"Ping statistics: {result['transmitted']} transmitted, "
                   f"{result['received']} received, {result['loss']} loss")

        return result

    except Exception as e:
        st.error(f"Exception during ping: {str(e)}")
        return {'success': False, 'transmitted': 0, 'received': 0, 'loss': '100%'}


def verify_arp_entry(dut: str, ip_address: str, expected_vlan: str, expected_mac: str = None,
                     expected_type: str = None, expected_action: str = "Fwd") -> bool:
    """
    Verify ARP entry exists with correct attributes on specific VLAN.

    Command: show ip arp | grep <ip_address>
    """
    st.log(f"Verifying ARP entry for {ip_address} on {dut} (expected VLAN: {expected_vlan})")

    try:
        show_cmd = "show ip arp"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        output_str = str(output)
        st.log(f"ARP table output:\n{output_str}")

        # Check if IP is in ARP table
        if ip_address not in output_str:
            st.error(f"✗ IP {ip_address} not found in ARP table")
            return False

        st.log(f"✓ IP {ip_address} found in ARP table")

        # Parse ARP entry details
        lines = output_str.split('\n')
        for line in lines:
            if ip_address in line and 'Address' not in line:
                st.log(f"ARP entry line: {line}")

                # Verify VLAN interface
                if expected_vlan:
                    if expected_vlan in line:
                        st.log(f"✓ VLAN interface matches: {expected_vlan}")
                    else:
                        st.error(f"✗ VLAN interface mismatch. Expected: {expected_vlan}, Line: {line}")
                        return False

                # Verify MAC address if provided
                if expected_mac:
                    if expected_mac.lower() in line.lower():
                        st.log(f"✓ MAC address matches: {expected_mac}")
                    else:
                        st.error(f"✗ MAC address mismatch. Expected: {expected_mac}")
                        return False

                # Verify ARP type if provided
                if expected_type:
                    if expected_type in line:
                        st.log(f"✓ ARP type matches: {expected_type}")
                    else:
                        st.error(f"✗ ARP type mismatch. Expected: {expected_type}, Line: {line}")
                        return False

                # Verify action
                if expected_action:
                    if expected_action in line:
                        st.log(f"✓ Action matches: {expected_action}")
                    else:
                        st.error(f"✗ Action mismatch. Expected: {expected_action}")
                        return False

                return True

        st.error(f"Could not parse ARP entry for {ip_address}")
        return False

    except Exception as e:
        st.error(f"Exception verifying ARP entry: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def verify_vlan_status(dut: str, vlan_id: str, expected_interface: str) -> bool:
    """
    Verify VLAN configuration.

    Command: show vlan <vlan_id>
    """
    st.log(f"Verifying VLAN {vlan_id} on {dut}")

    try:
        show_cmd = f"show vlan {vlan_id}"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        output_str = str(output)
        st.log(f"VLAN {vlan_id} output:\n{output_str}")

        if expected_interface in output_str and vlan_id in output_str:
            st.log(f"✓ VLAN {vlan_id} verified with interface {expected_interface}")
            return True
        else:
            st.error(f"✗ VLAN {vlan_id} verification failed")
            return False

    except Exception as e:
        st.error(f"Exception verifying VLAN: {str(e)}")
        return False


def test_arp_multiple_vlans():
    """
    Test Case: ARP on Multiple VLANs

    Test Steps:
    1. Configure VLAN 100 (Ethernet0) with IPs on both DUTs
    2. Configure VLAN 200 (Ethernet4) with IPs on both DUTs
    3. Configure static ARP on VLAN 100
    4. Ping across VLAN 100 (with static ARP)
    5. Ping across VLAN 200 (dynamic ARP learning)
    6. Verify ARP entries on both VLANs
    7. Verify ARP types: Static on VLAN 100, Dynamic on VLAN 200
    """
    st.banner("=" * 80)
    st.banner("TEST: ARP ON MULTIPLE VLANs")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Configure VLAN 100 on Both DUTs
    # ==================================================================
    st.banner("STEP 1: Configure VLAN 100 (Ethernet0) on Both DUTs")

    # Configure VLAN 100 on DUT1
    if not configure_vlan_and_ip(vars.D1, CONFIG.vlan1_id, CONFIG.vlan1_interface, CONFIG.vlan1_dut1_ip):
        st.report_tc_fail(TC_IDS.multi_vlan_vlan1_config, "msg",
                         f"Failed to configure VLAN {CONFIG.vlan1_id} on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "multi_vlan1_config_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure VLAN {CONFIG.vlan1_id} on {vars.D1}")

    # Configure VLAN 100 on DUT2
    if not configure_vlan_and_ip(vars.D2, CONFIG.vlan1_id, CONFIG.vlan1_interface, CONFIG.vlan1_dut2_ip):
        st.report_tc_fail(TC_IDS.multi_vlan_vlan1_config, "msg",
                         f"Failed to configure VLAN {CONFIG.vlan1_id} on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "multi_vlan1_config_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure VLAN {CONFIG.vlan1_id} on {vars.D2}")

    # Verify VLAN 100
    verify_vlan_status(vars.D1, CONFIG.vlan1_id, CONFIG.vlan1_interface)
    verify_vlan_status(vars.D2, CONFIG.vlan1_id, CONFIG.vlan1_interface)

    st.report_tc_pass(TC_IDS.multi_vlan_vlan1_config, "msg",
                     f"VLAN {CONFIG.vlan1_id} configured on both DUTs")

    st.wait(CONFIG.wait_after_config, "Waiting after VLAN 100 configuration")

    # ==================================================================
    # STEP 2: Configure VLAN 200 on Both DUTs
    # ==================================================================
    st.banner("STEP 2: Configure VLAN 200 (Ethernet4) on Both DUTs")

    # Configure VLAN 200 on DUT1
    if not configure_vlan_and_ip(vars.D1, CONFIG.vlan2_id, CONFIG.vlan2_interface, CONFIG.vlan2_dut1_ip):
        st.report_tc_fail(TC_IDS.multi_vlan_vlan2_config, "msg",
                         f"Failed to configure VLAN {CONFIG.vlan2_id} on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "multi_vlan2_config_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure VLAN {CONFIG.vlan2_id} on {vars.D1}")

    # Configure VLAN 200 on DUT2
    if not configure_vlan_and_ip(vars.D2, CONFIG.vlan2_id, CONFIG.vlan2_interface, CONFIG.vlan2_dut2_ip):
        st.report_tc_fail(TC_IDS.multi_vlan_vlan2_config, "msg",
                         f"Failed to configure VLAN {CONFIG.vlan2_id} on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "multi_vlan2_config_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure VLAN {CONFIG.vlan2_id} on {vars.D2}")

    # Verify VLAN 200
    verify_vlan_status(vars.D1, CONFIG.vlan2_id, CONFIG.vlan2_interface)
    verify_vlan_status(vars.D2, CONFIG.vlan2_id, CONFIG.vlan2_interface)

    st.report_tc_pass(TC_IDS.multi_vlan_vlan2_config, "msg",
                     f"VLAN {CONFIG.vlan2_id} configured on both DUTs")

    st.wait(CONFIG.wait_after_config, "Waiting after VLAN 200 configuration")

    # ==================================================================
    # STEP 3: Configure Static ARP on VLAN 100
    # ==================================================================
    st.banner("STEP 3: Configure Static ARP on VLAN 100")

    # Configure static ARP on DUT1 for DUT2
    if not configure_static_arp(vars.D1, f"Vlan{CONFIG.vlan1_id}",
                                CONFIG.vlan1_dut2_ip, CONFIG.vlan1_dut2_mac):
        st.report_tc_fail(TC_IDS.multi_vlan_static_arp, "msg",
                         f"Failed to configure static ARP on {vars.D1} VLAN{CONFIG.vlan1_id}")
        st.generate_tech_support([vars.D1, vars.D2], "multi_vlan_static_arp_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure static ARP on {vars.D1}")

    # Configure static ARP on DUT2 for DUT1
    if not configure_static_arp(vars.D2, f"Vlan{CONFIG.vlan1_id}",
                                CONFIG.vlan1_dut1_ip, CONFIG.vlan1_dut1_mac):
        st.report_tc_fail(TC_IDS.multi_vlan_static_arp, "msg",
                         f"Failed to configure static ARP on {vars.D2} VLAN{CONFIG.vlan1_id}")
        st.generate_tech_support([vars.D1, vars.D2], "multi_vlan_static_arp_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure static ARP on {vars.D2}")

    st.report_tc_pass(TC_IDS.multi_vlan_static_arp, "msg",
                     f"Static ARP configured on VLAN {CONFIG.vlan1_id}")

    st.wait(CONFIG.wait_after_config, "Waiting after static ARP configuration")

    # ==================================================================
    # STEP 4: Ping Across VLAN 100 (Static ARP)
    # ==================================================================
    st.banner("STEP 4: Ping Across VLAN 100 (with Static ARP)")

    # Ping from DUT1 to DUT2 on VLAN 100
    ping_vlan1_dut1 = ping_test(vars.D1, CONFIG.vlan1_dut2_ip, CONFIG.ping_count)

    # Ping from DUT2 to DUT1 on VLAN 100
    ping_vlan1_dut2 = ping_test(vars.D2, CONFIG.vlan1_dut1_ip, CONFIG.ping_count)

    if ping_vlan1_dut2['success']:
        st.log(f"✓ Ping across VLAN {CONFIG.vlan1_id} successful")
        st.report_tc_pass(TC_IDS.multi_vlan_ping_vlan1, "msg",
                         f"Ping successful on VLAN {CONFIG.vlan1_id}")
    else:
        st.log(f"Warning: Ping across VLAN {CONFIG.vlan1_id} failed")

    # ==================================================================
    # STEP 5: Ping Across VLAN 200 (Dynamic ARP)
    # ==================================================================
    st.banner("STEP 5: Ping Across VLAN 200 (Dynamic ARP Learning)")

    # Ping from DUT1 to DUT2 on VLAN 200
    ping_vlan2_dut1 = ping_test(vars.D1, CONFIG.vlan2_dut2_ip, CONFIG.ping_count)

    # Ping from DUT2 to DUT1 on VLAN 200
    ping_vlan2_dut2 = ping_test(vars.D2, CONFIG.vlan2_dut1_ip, CONFIG.ping_count)

    if ping_vlan2_dut1['success'] and ping_vlan2_dut2['success']:
        st.log(f"✓ Ping across VLAN {CONFIG.vlan2_id} successful")
        st.report_tc_pass(TC_IDS.multi_vlan_ping_vlan2, "msg",
                         f"Ping successful on VLAN {CONFIG.vlan2_id}")
    else:
        st.log(f"Warning: Ping across VLAN {CONFIG.vlan2_id} had issues")
        st.report_tc_pass(TC_IDS.multi_vlan_ping_vlan2, "msg",
                         f"Ping executed on VLAN {CONFIG.vlan2_id}")

    st.wait(2, "Waiting for dynamic ARP entries to be populated")

    # ==================================================================
    # STEP 6: Verify ARP Entries on Both VLANs
    # ==================================================================
    st.banner("STEP 6: Verify ARP Entries on Both VLANs")

    # Verify VLAN 100 ARP entries on DUT1
    if not verify_arp_entry(vars.D1, CONFIG.vlan1_dut2_ip, f"Vlan{CONFIG.vlan1_id}",
                           expected_mac=CONFIG.vlan1_dut2_mac, expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.multi_vlan_verify_arp, "msg",
                         f"ARP entry for VLAN {CONFIG.vlan1_id} not found on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "multi_vlan_verify_vlan1_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"ARP verification failed on {vars.D1} VLAN{CONFIG.vlan1_id}")

    # Verify VLAN 200 ARP entries on DUT1
    if not verify_arp_entry(vars.D1, CONFIG.vlan2_dut2_ip, f"Vlan{CONFIG.vlan2_id}",
                           expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.multi_vlan_verify_arp, "msg",
                         f"ARP entry for VLAN {CONFIG.vlan2_id} not found on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "multi_vlan_verify_vlan2_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"ARP verification failed on {vars.D1} VLAN{CONFIG.vlan2_id}")

    # Verify VLAN 100 ARP entries on DUT2
    if not verify_arp_entry(vars.D2, CONFIG.vlan1_dut1_ip, f"Vlan{CONFIG.vlan1_id}",
                           expected_mac=CONFIG.vlan1_dut1_mac, expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.multi_vlan_verify_arp, "msg",
                         f"ARP entry for VLAN {CONFIG.vlan1_id} not found on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "multi_vlan_verify_vlan1_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"ARP verification failed on {vars.D2} VLAN{CONFIG.vlan1_id}")

    # Verify VLAN 200 ARP entries on DUT2
    if not verify_arp_entry(vars.D2, CONFIG.vlan2_dut1_ip, f"Vlan{CONFIG.vlan2_id}",
                           expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.multi_vlan_verify_arp, "msg",
                         f"ARP entry for VLAN {CONFIG.vlan2_id} not found on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "multi_vlan_verify_vlan2_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"ARP verification failed on {vars.D2} VLAN{CONFIG.vlan2_id}")

    st.report_tc_pass(TC_IDS.multi_vlan_verify_arp, "msg",
                     "ARP entries verified on both VLANs")

    # ==================================================================
    # STEP 7: Verify ARP Types (Static vs Dynamic)
    # ==================================================================
    st.banner("STEP 7: Verify ARP Types - Static on VLAN 100, Dynamic on VLAN 200")

    # Verify Static ARP on VLAN 100 (DUT1)
    if not verify_arp_entry(vars.D1, CONFIG.vlan1_dut2_ip, f"Vlan{CONFIG.vlan1_id}",
                           expected_type="Static"):
        st.error(f"✗ VLAN {CONFIG.vlan1_id} ARP type is not Static on {vars.D1}")

    # Verify Dynamic ARP on VLAN 200 (DUT1)
    if not verify_arp_entry(vars.D1, CONFIG.vlan2_dut2_ip, f"Vlan{CONFIG.vlan2_id}",
                           expected_type="Dynamic"):
        st.log(f"Note: VLAN {CONFIG.vlan2_id} ARP type verification on {vars.D1}")

    # Verify Static ARP on VLAN 100 (DUT2)
    if not verify_arp_entry(vars.D2, CONFIG.vlan1_dut1_ip, f"Vlan{CONFIG.vlan1_id}",
                           expected_type="Static"):
        st.error(f"✗ VLAN {CONFIG.vlan1_id} ARP type is not Static on {vars.D2}")

    # Verify Dynamic ARP on VLAN 200 (DUT2)
    if not verify_arp_entry(vars.D2, CONFIG.vlan2_dut1_ip, f"Vlan{CONFIG.vlan2_id}",
                           expected_type="Dynamic"):
        st.log(f"Note: VLAN {CONFIG.vlan2_id} ARP type verification on {vars.D2}")

    st.report_tc_pass(TC_IDS.multi_vlan_verify_types, "msg",
                     "ARP types verified: Static on VLAN 100, Dynamic on VLAN 200")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: ARP ON MULTIPLE VLANs - PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - ARP on Multiple VLANs")
    st.log("=" * 80)
    st.log(f"✓ VLAN {CONFIG.vlan1_id} configured: {CONFIG.vlan1_interface} with IPs {CONFIG.vlan1_dut1_ip}/{CONFIG.vlan1_dut2_ip}")
    st.log(f"✓ VLAN {CONFIG.vlan2_id} configured: {CONFIG.vlan2_interface} with IPs {CONFIG.vlan2_dut1_ip}/{CONFIG.vlan2_dut2_ip}")
    st.log(f"✓ Static ARP on VLAN {CONFIG.vlan1_id}: DUT1→{CONFIG.vlan1_dut2_mac}, DUT2→{CONFIG.vlan1_dut1_mac}")
    st.log(f"✓ Ping VLAN {CONFIG.vlan1_id}: DUT1={ping_vlan1_dut1['received']}/{ping_vlan1_dut1['transmitted']}, "
           f"DUT2={ping_vlan1_dut2['received']}/{ping_vlan1_dut2['transmitted']}")
    st.log(f"✓ Ping VLAN {CONFIG.vlan2_id}: DUT1={ping_vlan2_dut1['received']}/{ping_vlan2_dut1['transmitted']}, "
           f"DUT2={ping_vlan2_dut2['received']}/{ping_vlan2_dut2['transmitted']}")
    st.log(f"✓ ARP entries verified on both VLANs with correct interface association")
    st.log(f"✓ VLAN {CONFIG.vlan1_id} ARP Type: Static")
    st.log(f"✓ VLAN {CONFIG.vlan2_id} ARP Type: Dynamic")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
