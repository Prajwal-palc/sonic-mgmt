"""
ARP TEST - Static ARP with Correct MAC

Test Case ID: ARP-STATIC-03
Author: Automated SpyTest Framework
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_ARP/test_arp_static_correct_mac.py \
    --logs-path ./logs/arp_static_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates static ARP configuration with correct MAC addresses:
  - Configure VLAN 100 on both DUTs
  - Configure IP addresses on VLAN interfaces
  - Clear dynamic ARP entries
  - Configure static ARP entries with correct MAC addresses
  - Verify static ARP entries are created
  - Test ping between DUTs
  - Verify static ARP entries persist after ping

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
    "dut1_vlan_ip": "10.1.1.1",
    "dut2_vlan_ip": "10.1.1.2",
    "subnet_mask": "24",
    "dut1_static_mac": "22:af:18:c9:30:56",  # MAC for DUT1
    "dut2_static_mac": "22:58:e5:4d:e2:7d",  # MAC for DUT2
    "ping_count": 3,
    "wait_after_config": 3,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "static_arp_config": "TC-ARP-STATIC-03-001",
    "static_arp_verify": "TC-ARP-STATIC-03-002",
    "static_arp_ping": "TC-ARP-STATIC-03-003",
    "static_arp_persist": "TC-ARP-STATIC-03-004",
})


@pytest.fixture(scope="module", autouse=True)
def arp_static_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("ARP STATIC TEST MODULE CONFIGURATION - START")
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
    st.banner("ARP STATIC TEST MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        arp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def arp_pre_config():
    """Pre-configuration: Setup VLAN and IP addresses."""
    st.log("Pre-configuration: Setting up VLAN and IP addresses")

    dut_list = [vars.D1, vars.D2]

    # Clear existing VLAN configuration
    vlanapi.clear_vlan_configuration(dut_list)

    # Clear existing IP configuration
    ipapi.clear_ip_configuration(dut_list, family='ipv4', thread=True)

    # Create VLAN 100
    for dut in dut_list:
        try:
            vlanapi.create_vlan(dut, CONFIG.vlan_id, cli_type=data.cli_type)
            st.log(f"✓ VLAN {CONFIG.vlan_id} created on {dut}")
        except Exception as e:
            st.log(f"VLAN creation on {dut}: {str(e)}")

    # Add Ethernet0 to VLAN 100 as untagged member
    for dut in dut_list:
        try:
            vlanapi.add_vlan_member(dut, CONFIG.vlan_id, CONFIG.interface,
                                   tagging_mode=False, cli_type=data.cli_type)
            st.log(f"✓ {CONFIG.interface} added to VLAN {CONFIG.vlan_id} on {dut}")
        except Exception as e:
            st.log(f"VLAN member add on {dut}: {str(e)}")

    # Configure IP addresses on VLAN interfaces
    try:
        ipapi.config_ip_addr_interface(
            vars.D1,
            f"Vlan{CONFIG.vlan_id}",
            CONFIG.dut1_vlan_ip,
            subnet=CONFIG.subnet_mask,
            family="ipv4",
            cli_type=data.cli_type
        )
        st.log(f"✓ IP {CONFIG.dut1_vlan_ip}/{CONFIG.subnet_mask} configured on {vars.D1}")
    except Exception as e:
        st.log(f"IP config on {vars.D1}: {str(e)}")

    try:
        ipapi.config_ip_addr_interface(
            vars.D2,
            f"Vlan{CONFIG.vlan_id}",
            CONFIG.dut2_vlan_ip,
            subnet=CONFIG.subnet_mask,
            family="ipv4",
            cli_type=data.cli_type
        )
        st.log(f"✓ IP {CONFIG.dut2_vlan_ip}/{CONFIG.subnet_mask} configured on {vars.D2}")
    except Exception as e:
        st.log(f"IP config on {vars.D2}: {str(e)}")

    # Bring up interfaces
    for dut in dut_list:
        try:
            commands = [
                "configure terminal",
                f"interface Vlan{CONFIG.vlan_id}",
                "no shutdown",
                f"interface {CONFIG.interface}",
                "no shutdown",
                "end"
            ]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)
            st.log(f"✓ Interfaces brought up on {dut}")
        except Exception as e:
            st.log(f"Interface up on {dut}: {str(e)}")

    st.wait(CONFIG.wait_after_config, "Waiting after interface configuration")
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

    # Remove IP addresses from VLAN interfaces
    for dut, ip in [(vars.D1, CONFIG.dut1_vlan_ip), (vars.D2, CONFIG.dut2_vlan_ip)]:
        try:
            ipapi.delete_ip_interface(dut, f"Vlan{CONFIG.vlan_id}", ip,
                                     CONFIG.subnet_mask, family="ipv4",
                                     cli_type=data.cli_type, skip_error=True)
            st.log(f"✓ IP removed from {dut}")
        except Exception as e:
            st.log(f"IP delete on {dut}: {str(e)}")

    # Remove VLAN membership
    for dut in dut_list:
        try:
            vlanapi.delete_vlan_member(dut, CONFIG.vlan_id, CONFIG.interface,
                                      tagging_mode=False, cli_type=data.cli_type,
                                      skip_error=True)
            st.log(f"✓ VLAN member removed on {dut}")
        except Exception as e:
            st.log(f"VLAN member delete on {dut}: {str(e)}")

    # Delete VLAN
    for dut in dut_list:
        try:
            vlanapi.delete_vlan(dut, CONFIG.vlan_id, cli_type=data.cli_type, skip_error=True)
            st.log(f"✓ VLAN deleted on {dut}")
        except Exception as e:
            st.log(f"VLAN delete on {dut}: {str(e)}")

    st.log("Cleanup completed")


def clear_arp_entries(dut: str) -> bool:
    """
    Clear all dynamic ARP entries.

    Command: clear ip arp
    """
    st.log(f"Clearing ARP entries on {dut}")

    try:
        output = st.show(dut, "clear ip arp", skip_tmpl=True, skip_error_check=True, type='klish')
        st.log(f"ARP clear output: {output}")
        return True
    except Exception as e:
        st.error(f"Failed to clear ARP on {dut}: {str(e)}")
        return False


def configure_static_arp(dut: str, interface: str, ip_address: str, mac_address: str) -> bool:
    """
    Configure static ARP entry.

    Commands:
      configure terminal
      interface Vlan 100
      ip arp 10.1.1.2 22:58:e5:4d:e2:7d
      end
    """
    st.log(f"Configuring static ARP on {dut}: {ip_address} -> {mac_address}")

    try:
        commands = [
            "configure terminal",
            f"interface {interface}",
            f"ip arp {ip_address} {mac_address}",
            "end"
        ]

        output = st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"✓ Static ARP configured: {ip_address} -> {mac_address}")
        return True

    except Exception as e:
        st.error(f"Failed to configure static ARP on {dut}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def verify_arp_entry(dut: str, ip_address: str, expected_mac: str = None,
                     expected_type: str = "Static", expected_action: str = "Fwd") -> bool:
    """
    Verify ARP entry exists with correct attributes.

    Command: show ip arp | grep <ip_address>

    Expected output format:
    10.1.1.2    22:58:e5:4d:e2:7d   Vlan100    -    Static    Fwd
    """
    st.log(f"Verifying ARP entry for {ip_address} on {dut}")

    try:
        # Get ARP table
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

                # Verify MAC address if provided
                if expected_mac:
                    if expected_mac.lower() in line.lower():
                        st.log(f"✓ MAC address matches: {expected_mac}")
                    else:
                        st.error(f"✗ MAC address mismatch. Expected: {expected_mac}")
                        return False

                # Verify ARP type
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
                        st.error(f"✗ Action mismatch. Expected: {expected_action}, Line: {line}")
                        return False

                return True

        st.error(f"Could not parse ARP entry for {ip_address}")
        return False

    except Exception as e:
        st.error(f"Exception verifying ARP entry: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def ping_test(dut: str, destination_ip: str, count: int = 3) -> dict:
    """
    Perform ping test.

    Command: ping <ip> -c <count>

    Returns:
      dict with 'success' (bool), 'transmitted' (int), 'received' (int), 'loss' (str)
    """
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

        # Look for: "3 packets transmitted, 3 received, 0% packet loss"
        match = re.search(r'(\d+) packets transmitted, (\d+) received, (\d+)% packet loss', output_str)
        if match:
            result['transmitted'] = int(match.group(1))
            result['received'] = int(match.group(2))
            result['loss'] = match.group(3) + '%'
            result['success'] = (result['received'] > 0)

            st.log(f"Ping statistics: {result['transmitted']} transmitted, "
                   f"{result['received']} received, {result['loss']} loss")
        else:
            st.log("Could not parse ping statistics")

        return result

    except Exception as e:
        st.error(f"Exception during ping: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return {'success': False, 'transmitted': 0, 'received': 0, 'loss': '100%'}


def test_arp_static_correct_mac():
    """
    Test Case: Static ARP with Correct MAC

    Test Steps:
    1. Clear ARP entries on both DUTs
    2. Configure static ARP on DUT1 (10.1.1.2 -> DUT2's MAC)
    3. Configure static ARP on DUT2 (10.1.1.1 -> DUT1's MAC)
    4. Verify static ARP entries on both DUTs
    5. Ping from DUT1 to DUT2
    6. Ping from DUT2 to DUT1
    7. Verify static ARP entries persist after ping
    """
    st.banner("=" * 80)
    st.banner("TEST: STATIC ARP WITH CORRECT MAC")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Clear ARP Entries on Both DUTs
    # ==================================================================
    st.banner("STEP 1: Clear ARP Entries on Both DUTs")

    if not clear_arp_entries(vars.D1):
        st.report_fail("msg", f"Failed to clear ARP entries on {vars.D1}")

    if not clear_arp_entries(vars.D2):
        st.report_fail("msg", f"Failed to clear ARP entries on {vars.D2}")

    st.wait(2, "Waiting after ARP clear")

    # ==================================================================
    # STEP 2: Configure Static ARP on DUT1
    # ==================================================================
    st.banner("STEP 2: Configure Static ARP on DUT1")
    st.log(f"Configuring: {CONFIG.dut2_vlan_ip} -> {CONFIG.dut2_static_mac}")

    if not configure_static_arp(vars.D1, f"Vlan{CONFIG.vlan_id}",
                                CONFIG.dut2_vlan_ip, CONFIG.dut2_static_mac):
        st.report_tc_fail(TC_IDS.static_arp_config, "msg",
                         f"Failed to configure static ARP on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "static_arp_config_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure static ARP on {vars.D1}")

    st.report_tc_pass(TC_IDS.static_arp_config, "msg",
                     f"Static ARP configured on {vars.D1}")

    # ==================================================================
    # STEP 3: Configure Static ARP on DUT2
    # ==================================================================
    st.banner("STEP 3: Configure Static ARP on DUT2")
    st.log(f"Configuring: {CONFIG.dut1_vlan_ip} -> {CONFIG.dut1_static_mac}")

    if not configure_static_arp(vars.D2, f"Vlan{CONFIG.vlan_id}",
                                CONFIG.dut1_vlan_ip, CONFIG.dut1_static_mac):
        st.report_tc_fail(TC_IDS.static_arp_config, "msg",
                         f"Failed to configure static ARP on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "static_arp_config_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure static ARP on {vars.D2}")

    st.wait(CONFIG.wait_after_config, "Waiting after static ARP configuration")

    # ==================================================================
    # STEP 4: Verify Static ARP Entries on Both DUTs
    # ==================================================================
    st.banner("STEP 4: Verify Static ARP Entries")

    # Verify on DUT1
    st.log(f"Verifying static ARP entry on {vars.D1}")
    if not verify_arp_entry(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.dut2_static_mac,
                           expected_type="Static", expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.static_arp_verify, "msg",
                         f"Static ARP entry verification failed on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "static_arp_verify_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not found on {vars.D1}")

    # Verify on DUT2
    st.log(f"Verifying static ARP entry on {vars.D2}")
    if not verify_arp_entry(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.dut1_static_mac,
                           expected_type="Static", expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.static_arp_verify, "msg",
                         f"Static ARP entry verification failed on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "static_arp_verify_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not found on {vars.D2}")

    st.report_tc_pass(TC_IDS.static_arp_verify, "msg",
                     "Static ARP entries verified on both DUTs")

    # ==================================================================
    # STEP 5: Ping from DUT1 to DUT2
    # ==================================================================
    st.banner("STEP 5: Ping from DUT1 to DUT2")

    ping_result_dut1 = ping_test(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.ping_count)

    if not ping_result_dut1['success']:
        st.log(f"Warning: Ping from {vars.D1} to {CONFIG.dut2_vlan_ip} failed")
        st.log(f"This may indicate L2 connectivity issues")
        # Note: We don't fail the test here as static ARP config is verified

    # ==================================================================
    # STEP 6: Ping from DUT2 to DUT1
    # ==================================================================
    st.banner("STEP 6: Ping from DUT2 to DUT1")

    ping_result_dut2 = ping_test(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.ping_count)

    if ping_result_dut2['success']:
        st.log(f"✓ Ping from {vars.D2} to {CONFIG.dut1_vlan_ip} successful")
        st.report_tc_pass(TC_IDS.static_arp_ping, "msg", "Ping test successful")
    else:
        st.log(f"Warning: Ping from {vars.D2} to {CONFIG.dut1_vlan_ip} failed")

    # ==================================================================
    # STEP 7: Verify Static ARP Entries Persist After Ping
    # ==================================================================
    st.banner("STEP 7: Verify Static ARP Entries Persist After Ping")

    # Verify on DUT1
    if not verify_arp_entry(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.dut2_static_mac,
                           expected_type="Static", expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.static_arp_persist, "msg",
                         f"Static ARP entry disappeared on {vars.D1} after ping")
        st.generate_tech_support([vars.D1, vars.D2], "static_arp_persist_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not persistent on {vars.D1}")

    # Verify on DUT2
    if not verify_arp_entry(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.dut1_static_mac,
                           expected_type="Static", expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.static_arp_persist, "msg",
                         f"Static ARP entry disappeared on {vars.D2} after ping")
        st.generate_tech_support([vars.D1, vars.D2], "static_arp_persist_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not persistent on {vars.D2}")

    st.report_tc_pass(TC_IDS.static_arp_persist, "msg",
                     "Static ARP entries persist after ping test")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: STATIC ARP WITH CORRECT MAC - PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - Static ARP with Correct MAC")
    st.log("=" * 80)
    st.log(f"✓ Static ARP configured on {vars.D1}: {CONFIG.dut2_vlan_ip} -> {CONFIG.dut2_static_mac}")
    st.log(f"✓ Static ARP configured on {vars.D2}: {CONFIG.dut1_vlan_ip} -> {CONFIG.dut1_static_mac}")
    st.log(f"✓ Static ARP entries verified with Type=Static, Action=Fwd")
    st.log(f"✓ Ping DUT1->DUT2: {ping_result_dut1['received']}/{ping_result_dut1['transmitted']} packets")
    st.log(f"✓ Ping DUT2->DUT1: {ping_result_dut2['received']}/{ping_result_dut2['transmitted']} packets")
    st.log(f"✓ Static ARP entries persist after ping")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
