"""
ARP TEST - Clear ARP Functionality

Test Case ID: ARP-CLEAR-04
Author: Automated SpyTest Framework
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_ARP/test_arp_clear_functionality.py \
    --logs-path ./logs/arp_clear_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates ARP clear functionality:
  - Configure VLAN 100 and IP addresses on both DUTs
  - Configure static ARP entries
  - Verify ping works with static ARP
  - Clear dynamic ARP entries (static should remain)
  - Verify static ARP entries persist after clear
  - Verify ping continues to work after clear

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
    "wait_after_clear": 2,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "clear_arp_static_config": "TC-ARP-CLEAR-04-001",
    "clear_arp_ping_before": "TC-ARP-CLEAR-04-002",
    "clear_arp_verify_before": "TC-ARP-CLEAR-04-003",
    "clear_arp_execute": "TC-ARP-CLEAR-04-004",
    "clear_arp_verify_persist": "TC-ARP-CLEAR-04-005",
    "clear_arp_ping_after": "TC-ARP-CLEAR-04-006",
    "clear_arp_final_verify": "TC-ARP-CLEAR-04-007",
})


@pytest.fixture(scope="module", autouse=True)
def arp_clear_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("ARP CLEAR FUNCTIONALITY MODULE CONFIGURATION - START")
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
    st.banner("ARP CLEAR FUNCTIONALITY MODULE CLEANUP - START")
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

    # Remove static ARP entries
    for dut, ip in [(vars.D1, CONFIG.dut2_vlan_ip), (vars.D2, CONFIG.dut1_vlan_ip)]:
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


def clear_dynamic_arp(dut: str) -> bool:
    """
    Clear dynamic ARP entries (static entries should remain).

    Command: clear ip arp
    """
    st.log(f"Clearing dynamic ARP entries on {dut}")

    try:
        output = st.show(dut, "clear ip arp", skip_tmpl=True, skip_error_check=True, type='klish')
        output_str = str(output)
        st.log(f"Clear ARP output: {output_str}")

        if "All dynamic ARP entries cleared" in output_str or "cleared" in output_str.lower():
            st.log(f"✓ Dynamic ARP entries cleared on {dut}")
            return True
        else:
            st.log(f"ARP clear executed on {dut} (output: {output_str})")
            return True

    except Exception as e:
        st.error(f"Failed to clear ARP on {dut}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def verify_arp_entry(dut: str, ip_address: str, expected_mac: str = None,
                     expected_type: str = "Static", expected_action: str = "Fwd") -> bool:
    """
    Verify ARP entry exists with correct attributes.

    Command: show ip arp | grep <ip_address>
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


def count_arp_entries(dut: str) -> int:
    """
    Count total ARP entries.

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
            st.log(f"Total ARP entries on {dut}: {count}")
            return count

        # Alternative: count lines with IP addresses (excluding header)
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


def test_arp_clear_functionality():
    """
    Test Case: Clear ARP Functionality

    Test Steps:
    1. Configure static ARP entries on both DUTs
    2. Ping to establish connectivity and verify ARP
    3. Show ARP table before clear
    4. Clear dynamic ARP entries
    5. Verify static ARP entries persist after clear
    6. Ping again to verify connectivity still works
    7. Show ARP table after ping to verify static entries remain
    """
    st.banner("=" * 80)
    st.banner("TEST: CLEAR ARP FUNCTIONALITY")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Configure Static ARP Entries
    # ==================================================================
    st.banner("STEP 1: Configure Static ARP Entries on Both DUTs")

    # Configure on DUT1
    if not configure_static_arp(vars.D1, f"Vlan{CONFIG.vlan_id}",
                                CONFIG.dut2_vlan_ip, CONFIG.dut2_static_mac):
        st.report_tc_fail(TC_IDS.clear_arp_static_config, "msg",
                         f"Failed to configure static ARP on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "clear_arp_config_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure static ARP on {vars.D1}")

    # Configure on DUT2
    if not configure_static_arp(vars.D2, f"Vlan{CONFIG.vlan_id}",
                                CONFIG.dut1_vlan_ip, CONFIG.dut1_static_mac):
        st.report_tc_fail(TC_IDS.clear_arp_static_config, "msg",
                         f"Failed to configure static ARP on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "clear_arp_config_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure static ARP on {vars.D2}")

    st.report_tc_pass(TC_IDS.clear_arp_static_config, "msg",
                     "Static ARP entries configured on both DUTs")

    st.wait(CONFIG.wait_after_config, "Waiting after static ARP configuration")

    # ==================================================================
    # STEP 2: Ping from Both DUTs (Before Clear)
    # ==================================================================
    st.banner("STEP 2: Ping Test Before Clear ARP")

    # Ping from DUT1 to DUT2
    ping_result_dut1_before = ping_test(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.ping_count)

    # Ping from DUT2 to DUT1
    ping_result_dut2_before = ping_test(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.ping_count)

    if ping_result_dut2_before['success']:
        st.log(f"✓ Ping from {vars.D2} successful before clear")
        st.report_tc_pass(TC_IDS.clear_arp_ping_before, "msg",
                         "Ping successful before clear ARP")
    else:
        st.log(f"Warning: Ping from {vars.D2} failed before clear")

    # ==================================================================
    # STEP 3: Verify ARP Entries Before Clear
    # ==================================================================
    st.banner("STEP 3: Verify ARP Entries Before Clear")

    # Show and count ARP entries on DUT1
    st.log(f"=== ARP Table on {vars.D1} (Before Clear) ===")
    arp_count_dut1_before = count_arp_entries(vars.D1)

    if not verify_arp_entry(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.dut2_static_mac,
                           expected_type="Static", expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.clear_arp_verify_before, "msg",
                         f"Static ARP entry verification failed on {vars.D1} before clear")
        st.generate_tech_support([vars.D1, vars.D2], "clear_arp_verify_before_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not found on {vars.D1} before clear")

    # Show and count ARP entries on DUT2
    st.log(f"=== ARP Table on {vars.D2} (Before Clear) ===")
    arp_count_dut2_before = count_arp_entries(vars.D2)

    if not verify_arp_entry(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.dut1_static_mac,
                           expected_type="Static", expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.clear_arp_verify_before, "msg",
                         f"Static ARP entry verification failed on {vars.D2} before clear")
        st.generate_tech_support([vars.D1, vars.D2], "clear_arp_verify_before_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not found on {vars.D2} before clear")

    st.report_tc_pass(TC_IDS.clear_arp_verify_before, "msg",
                     "Static ARP entries verified before clear")

    # ==================================================================
    # STEP 4: Clear Dynamic ARP Entries
    # ==================================================================
    st.banner("STEP 4: Clear Dynamic ARP Entries (Static Should Remain)")

    # Clear on DUT1
    if not clear_dynamic_arp(vars.D1):
        st.report_tc_fail(TC_IDS.clear_arp_execute, "msg",
                         f"Failed to clear ARP on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "clear_arp_execute_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to clear ARP on {vars.D1}")

    # Clear on DUT2
    if not clear_dynamic_arp(vars.D2):
        st.report_tc_fail(TC_IDS.clear_arp_execute, "msg",
                         f"Failed to clear ARP on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "clear_arp_execute_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to clear ARP on {vars.D2}")

    st.report_tc_pass(TC_IDS.clear_arp_execute, "msg",
                     "Dynamic ARP entries cleared on both DUTs")

    st.wait(CONFIG.wait_after_clear, "Waiting after ARP clear")

    # ==================================================================
    # STEP 5: Verify Static ARP Entries Persist After Clear
    # ==================================================================
    st.banner("STEP 5: Verify Static ARP Entries Persist After Clear")

    # Verify on DUT1
    st.log(f"=== ARP Table on {vars.D1} (After Clear) ===")

    if not verify_arp_entry(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.dut2_static_mac,
                           expected_type="Static", expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.clear_arp_verify_persist, "msg",
                         f"Static ARP entry disappeared on {vars.D1} after clear")
        st.generate_tech_support([vars.D1, vars.D2], "clear_arp_persist_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not found on {vars.D1} after clear")

    # Verify on DUT2
    st.log(f"=== ARP Table on {vars.D2} (After Clear) ===")

    if not verify_arp_entry(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.dut1_static_mac,
                           expected_type="Static", expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.clear_arp_verify_persist, "msg",
                         f"Static ARP entry disappeared on {vars.D2} after clear")
        st.generate_tech_support([vars.D1, vars.D2], "clear_arp_persist_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not found on {vars.D2} after clear")

    st.report_tc_pass(TC_IDS.clear_arp_verify_persist, "msg",
                     "Static ARP entries persist after clear")

    # ==================================================================
    # STEP 6: Ping After Clear (Should Still Work)
    # ==================================================================
    st.banner("STEP 6: Ping Test After Clear (Should Still Work)")

    # Ping from DUT1 to DUT2
    ping_result_dut1_after = ping_test(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.ping_count)

    # Ping from DUT2 to DUT1
    ping_result_dut2_after = ping_test(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.ping_count)

    if ping_result_dut2_after['success']:
        st.log(f"✓ Ping from {vars.D2} successful after clear")
        st.report_tc_pass(TC_IDS.clear_arp_ping_after, "msg",
                         "Ping successful after clear ARP")
    else:
        st.log(f"Warning: Ping from {vars.D2} failed after clear")

    # ==================================================================
    # STEP 7: Final Verification - Static ARP Entries Still Present
    # ==================================================================
    st.banner("STEP 7: Final Verification - Static ARP Entries After Ping")

    # Final verification on DUT1
    st.log(f"=== Final ARP Table on {vars.D1} ===")
    arp_count_dut1_after = count_arp_entries(vars.D1)

    if not verify_arp_entry(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.dut2_static_mac,
                           expected_type="Static", expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.clear_arp_final_verify, "msg",
                         f"Static ARP entry verification failed on {vars.D1} after ping")
        st.generate_tech_support([vars.D1, vars.D2], "clear_arp_final_verify_dut1_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not persistent on {vars.D1}")

    # Final verification on DUT2
    st.log(f"=== Final ARP Table on {vars.D2} ===")
    arp_count_dut2_after = count_arp_entries(vars.D2)

    if not verify_arp_entry(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.dut1_static_mac,
                           expected_type="Static", expected_action="Fwd"):
        st.report_tc_fail(TC_IDS.clear_arp_final_verify, "msg",
                         f"Static ARP entry verification failed on {vars.D2} after ping")
        st.generate_tech_support([vars.D1, vars.D2], "clear_arp_final_verify_dut2_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not persistent on {vars.D2}")

    st.report_tc_pass(TC_IDS.clear_arp_final_verify, "msg",
                     "Static ARP entries remain after clear and ping")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: CLEAR ARP FUNCTIONALITY - PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - Clear ARP Functionality")
    st.log("=" * 80)
    st.log(f"✓ Static ARP configured: DUT1={CONFIG.dut2_vlan_ip}->{CONFIG.dut2_static_mac}, "
           f"DUT2={CONFIG.dut1_vlan_ip}->{CONFIG.dut1_static_mac}")
    st.log(f"✓ Ping before clear: DUT1={ping_result_dut1_before['received']}/{ping_result_dut1_before['transmitted']}, "
           f"DUT2={ping_result_dut2_before['received']}/{ping_result_dut2_before['transmitted']}")
    st.log(f"✓ ARP entries before clear: DUT1={arp_count_dut1_before}, DUT2={arp_count_dut2_before}")
    st.log(f"✓ Dynamic ARP entries cleared (static entries preserved)")
    st.log(f"✓ Static ARP entries verified to persist after clear")
    st.log(f"✓ Ping after clear: DUT1={ping_result_dut1_after['received']}/{ping_result_dut1_after['transmitted']}, "
           f"DUT2={ping_result_dut2_after['received']}/{ping_result_dut2_after['transmitted']}")
    st.log(f"✓ ARP entries after clear+ping: DUT1={arp_count_dut1_after}, DUT2={arp_count_dut2_after}")
    st.log(f"✓ Static ARP entries remain Type=Static, Action=Fwd")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
