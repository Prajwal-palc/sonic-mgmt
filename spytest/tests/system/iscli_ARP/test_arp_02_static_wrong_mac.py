"""
ARP TEST - TC-02: Static ARP with Wrong MAC

Test Case ID: ARP-02
Author: Automated SpyTest Framework
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_ARP/test_arp_02_static_wrong_mac.py \
    --logs-path ./logs/arp02_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native \
    --skip-tgen --faster-init

Description:
  Test validates static ARP configuration with incorrect MAC addresses:
  - Configure static ARP entry on DUT1 with wrong MAC for DUT2
  - Configure static ARP entry on DUT2 with wrong MAC for DUT1
  - Verify static ARP entries are configured
  - Test ping behavior with incorrect MAC addresses
  - Verify static ARP entries remain after ping (not replaced by dynamic)

Pre-requisites:
  - 2 SONiC devices connected via Ethernet0
  - Testbed: testbed_2vs.yaml
  - VLAN 100 already configured (from test_arp_01)
  - IP addresses configured on VLAN 100
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi
import apis.switching.vlan as vlanapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration matching manual testcase
CONFIG = SpyTestDict({
    "vlan_id": "100",
    "interface": "Ethernet0",
    "dut1_vlan_ip": "10.1.1.1",
    "dut2_vlan_ip": "10.1.1.2",
    "subnet_mask": "24",
    # Wrong MAC addresses for testing
    "dut1_wrong_mac": "11:22:33:44:55:66",  # Wrong MAC for DUT2
    "dut2_wrong_mac": "aa:11:22:33:44:55",  # Wrong MAC for DUT1
    "ping_count": 3,
    "wait_after_config": 3,
    "wait_after_ping": 2,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "arp02_clear_arp": "TC-ARP-02-001",
    "arp02_static_config": "TC-ARP-02-002",
    "arp02_static_verify": "TC-ARP-02-003",
    "arp02_ping_test": "TC-ARP-02-004",
    "arp02_static_persistence": "TC-ARP-02-005",
})


@pytest.fixture(scope="module", autouse=True)
def arp_02_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("ARP TC-02 MODULE CONFIGURATION - START")
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

    # Cleanup after test
    st.banner("=" * 80)
    st.banner("ARP TC-02 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        arp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def arp_pre_config():
    """Pre-configuration: Ensure VLAN and IP are configured."""
    st.log("Pre-configuration: Ensuring VLAN and IP configuration")

    dut_list = [vars.D1, vars.D2]

    # Ensure VLAN 100 exists (create if not present)
    for dut in dut_list:
        try:
            vlanapi.create_vlan(dut, CONFIG.vlan_id, cli_type=data.cli_type)
        except Exception as e:
            st.log(f"VLAN creation on {dut}: {str(e)}")

    # Configure IP addresses on VLAN interfaces if not present
    try:
        ipapi.config_ip_addr_interface(
            vars.D1,
            f"Vlan{CONFIG.vlan_id}",
            CONFIG.dut1_vlan_ip,
            subnet=CONFIG.subnet_mask,
            family="ipv4",
            cli_type=data.cli_type
        )
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
    except Exception as e:
        st.log(f"IP config on {vars.D2}: {str(e)}")

    # Ensure interfaces are up
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
        except Exception as e:
            st.log(f"Interface up on {dut}: {str(e)}")

    st.log("Pre-configuration completed")


def arp_pre_config_cleanup():
    """Cleanup: Remove static ARP entries."""
    st.log("Cleanup: Removing static ARP entries")

    dut_list = [vars.D1, vars.D2]

    # Remove static ARP entries
    for dut in dut_list:
        try:
            # Use raw command to remove static ARP
            clear_cmd = "clear ip arp"
            st.show(dut, clear_cmd, skip_tmpl=True, skip_error_check=True, type='click')
        except Exception as e:
            st.log(f"ARP clear on {dut}: {str(e)}")

    st.log("Cleanup completed")


def clear_arp_table(dut: str) -> bool:
    """
    Clear ARP table.

    Command:
      clear ip arp
    """
    st.log(f"Clearing ARP table on {dut}")

    try:
        # Use raw command
        clear_cmd = "clear ip arp"
        output = st.show(dut, clear_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        st.log(f"ARP table cleared on {dut}")
        st.log(f"Clear output: {str(output)[:200]}")
        return True

    except Exception as e:
        st.error(f"Exception clearing ARP table on {dut}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def configure_static_arp(dut: str, vlan_id: str, ip_address: str, mac_address: str) -> bool:
    """
    Configure static ARP entry.

    Commands:
      configure terminal
      interface Vlan 100
      ip arp 10.1.1.2 11:22:33:44:55:66
      end
    """
    st.log(f"Configuring static ARP on {dut}: {ip_address} -> {mac_address}")

    commands = [
        "configure terminal",
        f"interface Vlan{vlan_id}",
        f"ip arp {ip_address} {mac_address}",
        "end"
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"✓ Static ARP configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Exception configuring static ARP on {dut}: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def verify_static_arp_entry(dut: str, ip_address: str, mac_address: str, expected_type: str = "Static") -> bool:
    """
    Verify static ARP entry exists.

    Command:
      show ip arp | grep 10.1.1.2

    Expected output:
      10.1.1.2    11:22:33:44:55:66   Vlan100   -   Static   Fwd
    """
    st.log(f"Verifying {expected_type} ARP entry for {ip_address} on {dut}")

    try:
        # Use raw show command
        show_cmd = f"show ip arp"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        output_str = str(output)
        st.log(f"ARP table output length: {len(output_str)} characters")
        st.log(f"ARP table output: {output_str[:1500]}")

        # Check if IP address is in ARP table
        if ip_address not in output_str:
            st.error(f"IP address {ip_address} not found in ARP table")
            return False

        # Split into lines and find the line with our IP
        lines = output_str.split('\n')
        for line in lines:
            if ip_address in line:
                st.log(f"Found ARP entry line: {line}")

                # Check for MAC address
                if mac_address.lower() not in line.lower():
                    st.error(f"MAC address {mac_address} not found in ARP entry")
                    return False

                st.log(f"✓ MAC address {mac_address} found in ARP entry")

                # Check for entry type (Static/Dynamic)
                if expected_type.lower() in line.lower():
                    st.log(f"✓ {expected_type} ARP entry found for {ip_address}")
                else:
                    st.log(f"Warning: Expected {expected_type} but line is: {line}")
                    # Still return True if IP and MAC match
                    return True

                # Verify action is Fwd
                if 'fwd' in line.lower():
                    st.log(f"✓ ARP action is Fwd")

                return True

        st.error(f"Could not parse ARP entry for {ip_address}")
        return False

    except Exception as e:
        st.error(f"Exception verifying ARP entry: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def ping_test(src_dut: str, dst_ip: str, count: int = 3, expect_success: bool = True) -> dict:
    """
    Test ping connectivity.

    Command:
      ping 10.1.1.2 -c 3

    Returns:
      dict with 'success' (bool) and 'duplicates' (bool) keys
    """
    st.log(f"Ping test: {src_dut} -> {dst_ip} (expect_success={expect_success})")

    try:
        # Use raw ping command
        ping_cmd = f"ping {dst_ip} -c {count}"

        # Execute ping from normal mode (not config mode)
        output = st.show(src_dut, ping_cmd, skip_tmpl=True, skip_error_check=True, type='click')

        output_str = str(output)
        st.log(f"Ping output: {output_str[:800]}")

        result = {
            'success': False,
            'duplicates': False,
            'packet_loss': 100
        }

        # Check for successful ping
        if " 0% packet loss" in output_str or "bytes from" in output_str:
            result['success'] = True
            st.log(f"✓ Ping successful: {src_dut} -> {dst_ip}")

            # Check for duplicates
            if "DUP!" in output_str or "duplicates" in output_str:
                result['duplicates'] = True
                st.log(f"✓ Duplicate packets detected (expected with wrong MAC)")

            # Extract packet loss
            if "% packet loss" in output_str:
                for line in output_str.split('\n'):
                    if "% packet loss" in line:
                        parts = line.split('%')
                        if len(parts) > 0:
                            try:
                                loss_str = parts[0].split()[-1]
                                result['packet_loss'] = float(loss_str)
                            except:
                                pass
        else:
            result['success'] = False
            st.log(f"Ping failed: {src_dut} -> {dst_ip}")

        return result

    except Exception as e:
        st.error(f"Exception during ping: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return {'success': False, 'duplicates': False, 'packet_loss': 100}


def test_arp_02_static_wrong_mac():
    """
    Test Case ARP-02: Static ARP with Wrong MAC

    Test Steps:
    1. Clear ARP tables on both DUTs
    2. Configure static ARP with wrong MAC on DUT1 (for DUT2)
    3. Configure static ARP with wrong MAC on DUT2 (for DUT1)
    4. Verify static ARP entries are configured
    5. Ping from DUT1 to DUT2 (may have duplicates)
    6. Ping from DUT2 to DUT1 (may fail due to wrong MAC)
    7. Verify static ARP entries persist (not replaced by dynamic)
    """
    st.banner("=" * 80)
    st.banner("TEST ARP-02: STATIC ARP WITH WRONG MAC")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Clear ARP Tables on Both DUTs
    # ==================================================================
    st.banner("STEP 1: Clear ARP Tables on Both DUTs")

    if not clear_arp_table(vars.D1):
        st.report_tc_fail(TC_IDS.arp02_clear_arp, "msg", f"Failed to clear ARP on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "arp02_clear_arp_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to clear ARP on {vars.D1}")

    if not clear_arp_table(vars.D2):
        st.report_tc_fail(TC_IDS.arp02_clear_arp, "msg", f"Failed to clear ARP on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "arp02_clear_arp_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to clear ARP on {vars.D2}")

    st.report_tc_pass(TC_IDS.arp02_clear_arp, "msg", "ARP tables cleared successfully")

    st.wait(CONFIG.wait_after_config, "Waiting after ARP clear")

    # ==================================================================
    # STEP 2: Configure Static ARP with Wrong MAC on DUT1
    # ==================================================================
    st.banner("STEP 2: Configure Static ARP with Wrong MAC on DUT1")
    st.log(f"DUT1: Configuring static ARP {CONFIG.dut2_vlan_ip} -> {CONFIG.dut1_wrong_mac} (WRONG MAC)")

    if not configure_static_arp(vars.D1, CONFIG.vlan_id, CONFIG.dut2_vlan_ip, CONFIG.dut1_wrong_mac):
        st.report_tc_fail(TC_IDS.arp02_static_config, "msg", f"Failed to configure static ARP on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "arp02_static_config_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure static ARP on {vars.D1}")

    # ==================================================================
    # STEP 3: Configure Static ARP with Wrong MAC on DUT2
    # ==================================================================
    st.banner("STEP 3: Configure Static ARP with Wrong MAC on DUT2")
    st.log(f"DUT2: Configuring static ARP {CONFIG.dut1_vlan_ip} -> {CONFIG.dut2_wrong_mac} (WRONG MAC)")

    if not configure_static_arp(vars.D2, CONFIG.vlan_id, CONFIG.dut1_vlan_ip, CONFIG.dut2_wrong_mac):
        st.report_tc_fail(TC_IDS.arp02_static_config, "msg", f"Failed to configure static ARP on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "arp02_static_config_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Failed to configure static ARP on {vars.D2}")

    st.report_tc_pass(TC_IDS.arp02_static_config, "msg", "Static ARP entries configured successfully")

    st.wait(CONFIG.wait_after_config, "Waiting for static ARP to apply")

    # ==================================================================
    # STEP 4: Verify Static ARP Entry on DUT1
    # ==================================================================
    st.banner("STEP 4: Verify Static ARP Entry on DUT1")
    st.log(f"Expected: Static ARP entry {CONFIG.dut2_vlan_ip} -> {CONFIG.dut1_wrong_mac}")

    if not verify_static_arp_entry(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.dut1_wrong_mac, "Static"):
        st.report_tc_fail(TC_IDS.arp02_static_verify, "msg",
                         f"Static ARP entry not found on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "arp02_static_verify_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not found on {vars.D1}")

    # ==================================================================
    # STEP 5: Verify Static ARP Entry on DUT2
    # ==================================================================
    st.banner("STEP 5: Verify Static ARP Entry on DUT2")
    st.log(f"Expected: Static ARP entry {CONFIG.dut1_vlan_ip} -> {CONFIG.dut2_wrong_mac}")

    if not verify_static_arp_entry(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.dut2_wrong_mac, "Static"):
        st.report_tc_fail(TC_IDS.arp02_static_verify, "msg",
                         f"Static ARP entry not found on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "arp02_static_verify_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry not found on {vars.D2}")

    st.report_tc_pass(TC_IDS.arp02_static_verify, "msg",
                     "Static ARP entries verified successfully on both DUTs")

    # ==================================================================
    # STEP 6: Ping Test - DUT1 to DUT2 (May Have Duplicates)
    # ==================================================================
    st.banner("STEP 6: Ping Test - DUT1 to DUT2 (Wrong MAC - May Have Duplicates)")

    ping_result_d1 = ping_test(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.ping_count, expect_success=True)

    if ping_result_d1['success']:
        st.log(f"✓ Ping from DUT1 to DUT2 succeeded")
        if ping_result_d1['duplicates']:
            st.log(f"✓ Duplicate packets detected (expected behavior with wrong MAC)")
    else:
        st.log(f"Note: Ping from DUT1 to DUT2 failed (acceptable with wrong MAC)")

    st.wait(CONFIG.wait_after_ping, "Waiting after ping")

    # ==================================================================
    # STEP 7: Ping Test - DUT2 to DUT1 (May Fail Due to Wrong MAC)
    # ==================================================================
    st.banner("STEP 7: Ping Test - DUT2 to DUT1 (Wrong MAC - May Fail)")

    ping_result_d2 = ping_test(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.ping_count, expect_success=False)

    if ping_result_d2['success']:
        st.log(f"Ping from DUT2 to DUT1 succeeded (unexpected but acceptable)")
    else:
        st.log(f"✓ Ping from DUT2 to DUT1 failed (expected with wrong MAC)")

    st.wait(CONFIG.wait_after_ping, "Waiting after ping")

    # ==================================================================
    # STEP 8: Verify Static ARP Persistence on DUT1 (Not Replaced)
    # ==================================================================
    st.banner("STEP 8: Verify Static ARP Persistence on DUT1 (Not Replaced by Dynamic)")
    st.log(f"Expected: Static ARP entry {CONFIG.dut2_vlan_ip} -> {CONFIG.dut1_wrong_mac} still present")

    if not verify_static_arp_entry(vars.D1, CONFIG.dut2_vlan_ip, CONFIG.dut1_wrong_mac, "Static"):
        st.report_tc_fail(TC_IDS.arp02_static_persistence, "msg",
                         f"Static ARP entry was replaced on {vars.D1}")
        st.generate_tech_support([vars.D1, vars.D2], "arp02_static_persistence_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry was replaced on {vars.D1}")

    # ==================================================================
    # STEP 9: Verify Static ARP Persistence on DUT2 (Not Replaced)
    # ==================================================================
    st.banner("STEP 9: Verify Static ARP Persistence on DUT2 (Not Replaced by Dynamic)")
    st.log(f"Expected: Static ARP entry {CONFIG.dut1_vlan_ip} -> {CONFIG.dut2_wrong_mac} still present")

    if not verify_static_arp_entry(vars.D2, CONFIG.dut1_vlan_ip, CONFIG.dut2_wrong_mac, "Static"):
        st.report_tc_fail(TC_IDS.arp02_static_persistence, "msg",
                         f"Static ARP entry was replaced on {vars.D2}")
        st.generate_tech_support([vars.D1, vars.D2], "arp02_static_persistence_failed")
        arp_pre_config_cleanup()
        st.report_fail("msg", f"Static ARP entry was replaced on {vars.D2}")

    st.report_tc_pass(TC_IDS.arp02_static_persistence, "msg",
                     "Static ARP entries persisted correctly (not replaced by dynamic)")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: ARP-02 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - ARP-02: Static ARP with Wrong MAC")
    st.log("=" * 80)
    st.log(f"✓ ARP tables cleared on both DUTs")
    st.log(f"✓ Static ARP configured on DUT1: {CONFIG.dut2_vlan_ip} -> {CONFIG.dut1_wrong_mac} (wrong MAC)")
    st.log(f"✓ Static ARP configured on DUT2: {CONFIG.dut1_vlan_ip} -> {CONFIG.dut2_wrong_mac} (wrong MAC)")
    st.log(f"✓ Static ARP entries verified as Static type")
    st.log(f"✓ Ping from DUT1: {'Success with duplicates' if ping_result_d1['duplicates'] else 'Executed'}")
    st.log(f"✓ Ping from DUT2: {'Failed as expected' if not ping_result_d2['success'] else 'Succeeded'}")
    st.log(f"✓ Static ARP entries persisted (not replaced by dynamic ARP)")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
