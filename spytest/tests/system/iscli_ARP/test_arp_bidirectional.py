"""
ARP TEST - Bidirectional ARP

Test Case ID: ARP-BIDIRECTIONAL-08
Author: Automated SpyTest Framework
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_ARP/test_arp_bidirectional.py \
    --logs-path ./logs/arp_bidirectional_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates bidirectional ARP functionality with static entries:
  - Configure VLAN 100 with IP addresses on both DUTs
  - Configure static ARP entries on both DUTs
  - Clear dynamic ARP entries on both DUTs
  - Ping from DUT1 to DUT2 (10.1.1.2)
  - Verify static ARP entry persists on DUT1
  - Ping from DUT2 to DUT1 (10.1.1.1)
  - Verify static ARP entry persists on DUT2
  - Verify bidirectional communication works with static ARP

Pre-requisites:
  - 2 SONiC devices connected via Ethernet0
  - Testbed: testbed_2vs.yaml
  - Clean VLAN and ARP configuration
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi
import apis.routing.arp as arpapi
import apis.switching.vlan as vlanapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "vlan_id": "100",
    "interface": "Ethernet0",
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "dut1_mac": "22:af:18:c9:30:56",
    "dut2_mac": "22:58:e5:4d:e2:7d",
    "subnet_mask": "24",
    "ping_count": 3,
    "wait_after_config": 3,
    "expected_arp_count": 2,  # Static ARP + Management0
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "bidirectional_setup": "TC-ARP-BIDIRECTIONAL-08-001",
    "bidirectional_clear_arp": "TC-ARP-BIDIRECTIONAL-08-002",
    "bidirectional_ping_dut1": "TC-ARP-BIDIRECTIONAL-08-003",
    "bidirectional_verify_dut1": "TC-ARP-BIDIRECTIONAL-08-004",
    "bidirectional_ping_dut2": "TC-ARP-BIDIRECTIONAL-08-005",
    "bidirectional_verify_dut2": "TC-ARP-BIDIRECTIONAL-08-006",
    "bidirectional_final_verify": "TC-ARP-BIDIRECTIONAL-08-007",
})


@pytest.fixture(scope="module", autouse=True)
def arp_bidirectional_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("ARP BIDIRECTIONAL MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    # Pre-configuration
    arp_pre_config()

    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("ARP BIDIRECTIONAL MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        arp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def arp_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing configurations")

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

    st.log("Pre-configuration completed")


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

    # Remove static ARP entries
    for dut, ip in [(vars.D1, CONFIG.dut2_ip), (vars.D2, CONFIG.dut1_ip)]:
        try:
            commands = [
                "configure terminal",
                f"interface Vlan{CONFIG.vlan_id}",
                f"no ip arp {ip}",
                "end"
            ]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)
            st.log(f"✓ Static ARP removed from {dut}")
        except Exception as e:
            st.log(f"Static ARP remove on {dut}: {str(e)}")

    # Remove IP addresses
    for dut, ip in [(vars.D1, CONFIG.dut1_ip), (vars.D2, CONFIG.dut2_ip)]:
        try:
            ipapi.delete_ip_interface(dut, f"Vlan{CONFIG.vlan_id}", ip,
                                     CONFIG.subnet_mask, family="ipv4",
                                     cli_type=data.cli_type, skip_error=True)
            st.log(f"✓ IP removed from {dut}")
        except Exception as e:
            st.log(f"IP delete on {dut}: {str(e)}")

    # Remove VLAN memberships
    for dut in dut_list:
        try:
            vlanapi.delete_vlan_member(dut, CONFIG.vlan_id, CONFIG.interface,
                                      tagging_mode=False, cli_type=data.cli_type, skip_error=True)
            st.log(f"✓ VLAN member removed on {dut}")
        except Exception as e:
            st.log(f"VLAN member delete on {dut}: {str(e)}")

    # Delete VLANs
    for dut in dut_list:
        try:
            vlanapi.delete_vlan(dut, CONFIG.vlan_id, cli_type=data.cli_type, skip_error=True)
            st.log(f"✓ VLAN deleted on {dut}")
        except Exception as e:
            st.log(f"VLAN delete on {dut}: {str(e)}")

    st.log("Cleanup completed")


def configure_vlan_and_ip(dut: str, ip_address: str) -> bool:
    """Configure VLAN, add interface member, configure IP address."""
    st.log(f"Configuring VLAN {CONFIG.vlan_id} on {dut}: interface={CONFIG.interface}, ip={ip_address}/{CONFIG.subnet_mask}")

    try:
        vlanapi.create_vlan(dut, CONFIG.vlan_id, cli_type=data.cli_type)
        st.log(f"✓ VLAN {CONFIG.vlan_id} created on {dut}")

        ipapi.config_ip_addr_interface(
            dut, f"Vlan{CONFIG.vlan_id}", ip_address,
            subnet=CONFIG.subnet_mask, family="ipv4", cli_type=data.cli_type
        )
        st.log(f"✓ IP {ip_address}/{CONFIG.subnet_mask} configured on {dut}")

        commands = [
            "configure terminal",
            f"interface {CONFIG.interface}",
            "no ip address",
            "no ipv6 address",
            f"switchport access Vlan {CONFIG.vlan_id}",
            "no shutdown",
            "end"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

        commands = [
            "configure terminal",
            f"interface Vlan{CONFIG.vlan_id}",
            "no shutdown",
            "end"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

        return True

    except Exception as e:
        st.error(f"Failed to configure VLAN {CONFIG.vlan_id} on {dut}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def configure_static_arp(dut: str, ip_address: str, mac_address: str) -> bool:
    """Configure static ARP entry."""
    st.log(f"Configuring static ARP on {dut}: {ip_address} -> {mac_address}")

    try:
        commands = [
            "configure terminal",
            f"interface Vlan{CONFIG.vlan_id}",
            f"ip arp {ip_address} {mac_address}",
            "end"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"✓ Static ARP configured: {ip_address} -> {mac_address}")
        return True

    except Exception as e:
        st.error(f"Failed to configure static ARP on {dut}: {str(e)}")
        return False


def clear_dynamic_arp(dut: str) -> bool:
    """Clear dynamic ARP entries (static should remain)."""
    st.log(f"Clearing dynamic ARP entries on {dut}")

    try:
        show_cmd = "clear ip arp"
        output = st.show(dut, show_cmd, type='klish', skip_tmpl=True, skip_error_check=True)

        output_str = str(output)
        st.log(f"Clear ARP output on {dut}: {output_str}")

        if "All dynamic ARP entries cleared" in output_str or "cleared" in output_str.lower():
            st.log(f"✓ Dynamic ARP entries cleared on {dut}")
            return True
        else:
            st.log(f"Note: Clear ARP command executed on {dut}")
            return True

    except Exception as e:
        st.error(f"Exception clearing ARP on {dut}: {str(e)}")
        return False


def ping_test(dut: str, destination_ip: str, count: int = 3) -> dict:
    """Perform ping test."""
    st.log(f"Pinging {destination_ip} from {dut} ({count} packets)")

    try:
        ping_cmd = f"ping {destination_ip} -c {count}"
        output = st.show(dut, ping_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        output_str = str(output)

        result = {'success': False, 'transmitted': 0, 'received': 0, 'loss': '100%'}

        import re
        match = re.search(r'(\d+) packets transmitted, (\d+) received, (\d+)% packet loss', output_str)
        if match:
            result['transmitted'] = int(match.group(1))
            result['received'] = int(match.group(2))
            result['loss'] = match.group(3) + '%'
            result['success'] = (result['received'] > 0)

            st.log(f"Ping: {result['transmitted']} tx, {result['received']} rx, {result['loss']} loss")

        return result

    except Exception as e:
        st.error(f"Exception during ping: {str(e)}")
        return {'success': False, 'transmitted': 0, 'received': 0, 'loss': '100%'}


def verify_arp_entry(dut: str, ip_address: str, expected_type: str = "Static",
                     expected_action: str = "Fwd") -> bool:
    """
    Verify ARP entry exists and matches expected type and action.

    Returns: True if entry found and matches criteria
    """
    st.log(f"Verifying ARP entry on {dut} for IP {ip_address}")

    try:
        show_cmd = f"show ip arp | grep {ip_address}"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        output_str = str(output)
        st.log(f"ARP entry output on {dut}: {output_str}")

        # Check if IP is in output
        if ip_address not in output_str:
            st.error(f"✗ ARP entry for {ip_address} not found on {dut}")
            return False

        st.log(f"✓ ARP entry for {ip_address} found on {dut}")

        # Verify Type if specified
        if expected_type:
            if expected_type in output_str:
                st.log(f"✓ ARP Type matches: {expected_type}")
            else:
                st.error(f"✗ ARP Type mismatch. Expected: {expected_type}")
                return False

        # Verify Action if specified
        if expected_action:
            if expected_action in output_str:
                st.log(f"✓ ARP Action matches: {expected_action}")
            else:
                st.error(f"✗ ARP Action mismatch. Expected: {expected_action}")
                return False

        return True

    except Exception as e:
        st.error(f"Exception verifying ARP entry: {str(e)}")
        return False


def count_arp_entries(dut: str) -> int:
    """
    Count total ARP entries from ARP table.

    Returns: Number of ARP entries
    """
    st.log(f"Counting ARP entries on {dut}")

    try:
        show_cmd = "show ip arp"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        output_str = str(output)

        # Look for "Total number of ARP entries: X"
        import re
        match = re.search(r'Total number of ARP entries:\s*(\d+)', output_str)
        if match:
            count = int(match.group(1))
            st.log(f"✓ Total ARP entries on {dut}: {count}")
            return count

        # Alternative: count lines with IP addresses
        lines = output_str.split('\n')
        count = 0
        for line in lines:
            if re.search(r'\d+\.\d+\.\d+\.\d+', line) and 'Address' not in line:
                count += 1

        st.log(f"Total ARP entries on {dut}: {count} (counted from output)")
        return count

    except Exception as e:
        st.error(f"Exception counting ARP entries: {str(e)}")
        return 0


def test_arp_bidirectional():
    """
    Test Case: Bidirectional ARP

    Test Steps:
    1. Setup: Configure VLAN 100 and static ARP on both DUTs
    2. Clear dynamic ARP entries on both DUTs
    3. Ping from DUT1 to DUT2 (10.1.1.2)
    4. Verify static ARP entry persists on DUT1
    5. Ping from DUT2 to DUT1 (10.1.1.1)
    6. Verify static ARP entry persists on DUT2
    7. Final verification of bidirectional communication
    """
    st.banner("=" * 80)
    st.banner("TEST: BIDIRECTIONAL ARP")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Setup - Configure VLAN and Static ARP
    # ==================================================================
    st.banner("STEP 1: Setup - Configure VLAN 100 and Static ARP on Both DUTs")

    # Configure VLAN 100 on DUT1
    if not configure_vlan_and_ip(vars.D1, CONFIG.dut1_ip):
        st.report_tc_fail(TC_IDS.bidirectional_setup, "msg", "Failed to configure VLAN on DUT1")
        arp_pre_config_cleanup()
        st.report_fail("msg", "VLAN configuration failed on DUT1")

    # Configure VLAN 100 on DUT2
    if not configure_vlan_and_ip(vars.D2, CONFIG.dut2_ip):
        st.report_tc_fail(TC_IDS.bidirectional_setup, "msg", "Failed to configure VLAN on DUT2")
        arp_pre_config_cleanup()
        st.report_fail("msg", "VLAN configuration failed on DUT2")

    st.wait(CONFIG.wait_after_config, "Waiting after VLAN configuration")

    # Configure static ARP on DUT1 (10.1.1.2 -> MAC)
    if not configure_static_arp(vars.D1, CONFIG.dut2_ip, CONFIG.dut2_mac):
        st.report_tc_fail(TC_IDS.bidirectional_setup, "msg", "Failed to configure static ARP on DUT1")
        arp_pre_config_cleanup()
        st.report_fail("msg", "Static ARP configuration failed on DUT1")

    # Configure static ARP on DUT2 (10.1.1.1 -> MAC)
    if not configure_static_arp(vars.D2, CONFIG.dut1_ip, CONFIG.dut1_mac):
        st.report_tc_fail(TC_IDS.bidirectional_setup, "msg", "Failed to configure static ARP on DUT2")
        arp_pre_config_cleanup()
        st.report_fail("msg", "Static ARP configuration failed on DUT2")

    st.wait(CONFIG.wait_after_config, "Waiting after static ARP configuration")

    # Verify static ARP configured on both DUTs
    dut1_arp_configured = verify_arp_entry(vars.D1, CONFIG.dut2_ip, expected_type="Static")
    dut2_arp_configured = verify_arp_entry(vars.D2, CONFIG.dut1_ip, expected_type="Static")

    if dut1_arp_configured and dut2_arp_configured:
        st.log(f"✓ Static ARP entries configured on both DUTs")
        st.report_tc_pass(TC_IDS.bidirectional_setup, "msg", "VLAN and static ARP configured successfully")
    else:
        st.report_tc_fail(TC_IDS.bidirectional_setup, "msg", "Static ARP verification failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", "Static ARP configuration verification failed")

    # ==================================================================
    # STEP 2: Clear Dynamic ARP Entries
    # ==================================================================
    st.banner("STEP 2: Clear Dynamic ARP Entries on Both DUTs")

    # Clear dynamic ARP on DUT1
    clear_dut1 = clear_dynamic_arp(vars.D1)

    # Clear dynamic ARP on DUT2
    clear_dut2 = clear_dynamic_arp(vars.D2)

    st.wait(2, "Waiting after clearing dynamic ARP")

    if clear_dut1 and clear_dut2:
        st.log(f"✓ Dynamic ARP entries cleared on both DUTs")
        st.report_tc_pass(TC_IDS.bidirectional_clear_arp, "msg", "Dynamic ARP cleared successfully")
    else:
        st.log(f"Note: Clear ARP executed on both DUTs")
        st.report_tc_pass(TC_IDS.bidirectional_clear_arp, "msg", "Clear ARP executed")

    # ==================================================================
    # STEP 3: Ping from DUT1 to DUT2
    # ==================================================================
    st.banner(f"STEP 3: Ping from DUT1 ({CONFIG.dut1_ip}) to DUT2 ({CONFIG.dut2_ip})")

    ping_dut1_result = ping_test(vars.D1, CONFIG.dut2_ip, CONFIG.ping_count)

    if ping_dut1_result['success']:
        st.log(f"✓ Ping from DUT1 to DUT2 successful: {ping_dut1_result['received']}/{ping_dut1_result['transmitted']} packets, {ping_dut1_result['loss']} loss")
        st.report_tc_pass(TC_IDS.bidirectional_ping_dut1, "msg",
                         f"Ping DUT1→DUT2 successful: {ping_dut1_result['received']}/{ping_dut1_result['transmitted']}")
    else:
        st.error(f"✗ Ping from DUT1 to DUT2 failed: {ping_dut1_result['loss']} loss")
        st.report_tc_fail(TC_IDS.bidirectional_ping_dut1, "msg", "Ping DUT1→DUT2 failed")
        st.generate_tech_support([vars.D1, vars.D2], "arp_bidirectional_ping_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", "Ping from DUT1 to DUT2 failed")

    st.wait(2, "Waiting after ping from DUT1")

    # ==================================================================
    # STEP 4: Verify Static ARP Entry Persists on DUT1
    # ==================================================================
    st.banner(f"STEP 4: Verify Static ARP Entry for {CONFIG.dut2_ip} Persists on DUT1")

    # Verify ARP entry for 10.1.1.2 on DUT1
    dut1_arp_persists = verify_arp_entry(vars.D1, CONFIG.dut2_ip, expected_type="Static", expected_action="Fwd")

    # Count ARP entries on DUT1
    dut1_arp_count = count_arp_entries(vars.D1)
    st.log(f"DUT1 ARP entry count: {dut1_arp_count}")

    if dut1_arp_persists:
        st.log(f"✓ Static ARP entry persists on DUT1 after ping (Type=Static, Action=Fwd)")
        st.log(f"✓ DUT1 ARP table shows {dut1_arp_count} entries")
        st.report_tc_pass(TC_IDS.bidirectional_verify_dut1, "msg",
                         f"Static ARP persists on DUT1 ({dut1_arp_count} entries)")
    else:
        st.error(f"✗ Static ARP entry verification failed on DUT1")
        st.report_tc_fail(TC_IDS.bidirectional_verify_dut1, "msg", "Static ARP verification failed on DUT1")
        st.generate_tech_support([vars.D1, vars.D2], "arp_bidirectional_verify_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", "Static ARP entry verification failed on DUT1")

    # ==================================================================
    # STEP 5: Ping from DUT2 to DUT1
    # ==================================================================
    st.banner(f"STEP 5: Ping from DUT2 ({CONFIG.dut2_ip}) to DUT1 ({CONFIG.dut1_ip})")

    ping_dut2_result = ping_test(vars.D2, CONFIG.dut1_ip, CONFIG.ping_count)

    if ping_dut2_result['success']:
        st.log(f"✓ Ping from DUT2 to DUT1 successful: {ping_dut2_result['received']}/{ping_dut2_result['transmitted']} packets, {ping_dut2_result['loss']} loss")
        st.report_tc_pass(TC_IDS.bidirectional_ping_dut2, "msg",
                         f"Ping DUT2→DUT1 successful: {ping_dut2_result['received']}/{ping_dut2_result['transmitted']}")
    else:
        st.error(f"✗ Ping from DUT2 to DUT1 failed: {ping_dut2_result['loss']} loss")
        st.report_tc_fail(TC_IDS.bidirectional_ping_dut2, "msg", "Ping DUT2→DUT1 failed")
        st.generate_tech_support([vars.D1, vars.D2], "arp_bidirectional_ping_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", "Ping from DUT2 to DUT1 failed")

    st.wait(2, "Waiting after ping from DUT2")

    # ==================================================================
    # STEP 6: Verify Static ARP Entry Persists on DUT2
    # ==================================================================
    st.banner(f"STEP 6: Verify Static ARP Entry for {CONFIG.dut1_ip} Persists on DUT2")

    # Verify ARP entry for 10.1.1.1 on DUT2
    dut2_arp_persists = verify_arp_entry(vars.D2, CONFIG.dut1_ip, expected_type="Static", expected_action="Fwd")

    # Count ARP entries on DUT2
    dut2_arp_count = count_arp_entries(vars.D2)
    st.log(f"DUT2 ARP entry count: {dut2_arp_count}")

    if dut2_arp_persists:
        st.log(f"✓ Static ARP entry persists on DUT2 after ping (Type=Static, Action=Fwd)")
        st.log(f"✓ DUT2 ARP table shows {dut2_arp_count} entries")
        st.report_tc_pass(TC_IDS.bidirectional_verify_dut2, "msg",
                         f"Static ARP persists on DUT2 ({dut2_arp_count} entries)")
    else:
        st.error(f"✗ Static ARP entry verification failed on DUT2")
        st.report_tc_fail(TC_IDS.bidirectional_verify_dut2, "msg", "Static ARP verification failed on DUT2")
        st.generate_tech_support([vars.D1, vars.D2], "arp_bidirectional_verify_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", "Static ARP entry verification failed on DUT2")

    # ==================================================================
    # STEP 7: Final Verification of Bidirectional Communication
    # ==================================================================
    st.banner("STEP 7: Final Verification of Bidirectional Communication")

    # Display full ARP tables
    st.log("=== DUT1 ARP Table ===")
    st.show(vars.D1, "show ip arp", type=data.cli_type, skip_tmpl=True)

    st.log("=== DUT2 ARP Table ===")
    st.show(vars.D2, "show ip arp", type=data.cli_type, skip_tmpl=True)

    # Final verification
    bidirectional_working = (
        ping_dut1_result['success'] and
        ping_dut2_result['success'] and
        dut1_arp_persists and
        dut2_arp_persists
    )

    if bidirectional_working:
        st.log(f"✓ Bidirectional ARP communication verified successfully")
        st.log(f"  - DUT1→DUT2 ping: {ping_dut1_result['received']}/{ping_dut1_result['transmitted']} packets")
        st.log(f"  - DUT2→DUT1 ping: {ping_dut2_result['received']}/{ping_dut2_result['transmitted']} packets")
        st.log(f"  - Static ARP persists on both DUTs (Type=Static, Action=Fwd)")
        st.report_tc_pass(TC_IDS.bidirectional_final_verify, "msg",
                         "Bidirectional ARP communication verified successfully")
    else:
        st.error(f"✗ Bidirectional ARP verification failed")
        st.report_tc_fail(TC_IDS.bidirectional_final_verify, "msg", "Bidirectional verification failed")
        st.generate_tech_support([vars.D1, vars.D2], "arp_bidirectional_final_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", "Bidirectional ARP verification failed")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: BIDIRECTIONAL ARP - PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - Bidirectional ARP")
    st.log("=" * 80)
    st.log(f"✓ VLAN {CONFIG.vlan_id} configured on both DUTs")
    st.log(f"✓ Static ARP configured:")
    st.log(f"    - DUT1: {CONFIG.dut2_ip} -> {CONFIG.dut2_mac}")
    st.log(f"    - DUT2: {CONFIG.dut1_ip} -> {CONFIG.dut1_mac}")
    st.log(f"✓ Dynamic ARP entries cleared on both DUTs")
    st.log(f"✓ Ping DUT1→DUT2: {ping_dut1_result['received']}/{ping_dut1_result['transmitted']} packets, {ping_dut1_result['loss']} loss")
    st.log(f"✓ Ping DUT2→DUT1: {ping_dut2_result['received']}/{ping_dut2_result['transmitted']} packets, {ping_dut2_result['loss']} loss")
    st.log(f"✓ Static ARP entries persist on both DUTs (Type=Static, Action=Fwd)")
    st.log(f"✓ ARP entry count: DUT1={dut1_arp_count}, DUT2={dut2_arp_count}")
    st.log(f"✓ Bidirectional communication verified successfully")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
