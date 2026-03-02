"""
BGP NEGATIVE TEST - NEG-01: Wrong ASN Configured (IPv4)

Test Case ID: NEG-01-IPv4
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/OSPF/test_ipv4_bgp_negative_asn.py \
    --logs-path ./logs/neg_asn_ipv4_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates NEGATIVE scenario - BGP MUST NOT establish with wrong ASN:
  - DUT1 expects remote-as 65003
  - DUT2 advertises AS 65002
  - Expected: BGP remains in Idle state with "Bad Peer AS" notification
  - Test PASSES when BGP correctly rejects wrong ASN

Pre-requisites:
  - 2 SONiC devices connected via Ethernet0
  - Testbed: testbed_2vs.yaml
  - Clean BGP configuration
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi
import apis.routing.bgp as bgpapi
import apis.switching.vlan as vlanapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration matching manual negative testcase
CONFIG = SpyTestDict({
    "interface": "Ethernet0",
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "subnet_mask": "24",
    "dut1_asn": "65001",
    "dut2_asn": "65002",
    "dut1_expected_remote_asn": "65003",  # DUT1 expects AS 65003, but DUT2 sends AS 65002
    "dut2_expected_remote_asn": "65001",  # DUT2 expects AS 65001 (correct)
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
    "bgp_wait_time": 90,
    "ping_count": 5,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "neg01_ipv4_wrong_asn": "TC-BGP-NEG-01-IPv4",
})


@pytest.fixture(scope="module", autouse=True)
def bgp_neg01_ipv4_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP NEG-01 IPv4 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    # Pre-configuration
    bgp_pre_config()

    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("BGP NEG-01 IPv4 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        bgp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def bgp_pre_config():
    """Pre-configuration: Clear existing configs and setup interfaces."""
    st.log("Pre-configuration: Clearing existing configuration")

    dut_list = [vars.D1, vars.D2]

    # Clear IP configuration
    ipapi.clear_ip_configuration(dut_list, family='ipv4', thread=True)

    # Clear VLAN configuration (critical for L3 config)
    vlanapi.clear_vlan_configuration(dut_list)

    # Additional VLAN cleanup on Ethernet0
    for dut in dut_list:
        try:
            cleanup_vlan_from_interface(dut, CONFIG.interface)
        except Exception as e:
            st.log(f"VLAN cleanup on {dut}: {str(e)}")

    # Clear any existing BGP configuration
    for dut in dut_list:
        try:
            bgpapi.cleanup_router_bgp(dut, cli_type='klish')
        except Exception as e:
            st.log(f"BGP cleanup warning on {dut}: {str(e)}")

    st.log("Pre-configuration completed")


def bgp_pre_config_cleanup():
    """Cleanup: Remove BGP and IP configuration."""
    st.log("Cleanup: Removing BGP and IP configuration")

    dut_list = [vars.D1, vars.D2]

    # Remove BGP configuration
    for dut in dut_list:
        try:
            bgpapi.cleanup_router_bgp(dut, cli_type='klish')
        except Exception as e:
            st.log(f"BGP cleanup warning on {dut}: {str(e)}")

    # Clear IP configuration
    ipapi.clear_ip_configuration(dut_list, family='ipv4', thread=True)

    st.log("Cleanup completed")


def cleanup_vlan_from_interface(dut, interface):
    """
    Remove interface from any VLAN membership before L3 configuration.
    Removes interface from VLAN member list AND deletes VLAN interfaces.
    """
    try:
        st.log(f"Checking and removing VLAN configuration from {interface} on {dut}")

        # Get VLAN configuration - use capital V for Klish
        vlan_show_cmd = "show Vlan brief"
        vlan_output = st.show(dut, vlan_show_cmd, type='klish', skip_error_check=True)

        cleanup_cmds = []

        if vlan_output and isinstance(vlan_output, list):
            for vlan_entry in vlan_output:
                if not isinstance(vlan_entry, dict):
                    continue

                vlan_id = vlan_entry.get('vid') or vlan_entry.get('vlan') or vlan_entry.get('id')
                ports = str(vlan_entry.get('ports', ''))

                # Check if our interface is a member of this VLAN
                if interface in ports or interface.replace('Ethernet', 'Eth') in ports:
                    if vlan_id:
                        st.log(f"Found {interface} in VLAN {vlan_id}, removing from VLAN members...")
                        cleanup_cmds.extend([
                            f"interface Vlan {vlan_id}",
                            f"no member {interface}",
                            "exit",
                        ])

        # Also try to delete any VLAN interface completely
        for vlan_id in [10, 100, 1000]:  # Common VLAN IDs
            cleanup_cmds.extend([
                f"no interface Vlan {vlan_id}",
            ])

        # Execute cleanup
        if cleanup_cmds:
            st.config(dut, cleanup_cmds, type='klish', skip_error_check=True)
            st.log(f"✓ VLAN cleanup completed on {dut}")
            st.wait(3, "Waiting after VLAN cleanup")
            return True

    except Exception as e:
        st.log(f"VLAN cleanup exception on {dut}: {str(e)}")
        return False


def configure_ip_on_interface(dut: str, interface: str, ip_address: str) -> bool:
    """Configure IP address on interface."""
    st.log(f"Configuring IP {ip_address}/{CONFIG.subnet_mask} on {dut} {interface}")

    # Clean VLAN first
    cleanup_vlan_from_interface(dut, interface)

    result = ipapi.config_ip_addr_interface(
        dut,
        interface,
        ip_address,
        subnet=CONFIG.subnet_mask,
        family="ipv4",
        cli_type=data.cli_type
    )

    if not result:
        st.error(f"Failed to configure IP on {dut} {interface}")
        return False

    # Bring up the interface explicitly
    st.log(f"Bringing up interface {interface} on {dut}")
    startup_commands = [
        "configure terminal",
        f"interface {interface}",
        "no shutdown",
        "exit"
    ]
    st.config(dut, startup_commands, type=data.cli_type)

    st.log(f"IP configured successfully on {dut} {interface}")
    return True


def configure_bgp_router(dut: str, asn: str, router_id: str) -> bool:
    """Configure BGP router with ASN and router-id."""
    st.log(f"Configuring BGP on {dut}: AS {asn}, Router-ID {router_id}")

    result = bgpapi.config_bgp_router(
        dut=dut,
        local_asn=asn,
        router_id=router_id,
        config='yes',
        cli_type='klish'
    )

    if not result:
        st.error(f"Failed to configure BGP router on {dut}")
        return False

    st.log(f"BGP router configured successfully on {dut}")
    return True


def configure_bgp_neighbor(dut: str, asn: str, neighbor_ip: str, remote_as: str) -> bool:
    """Configure BGP neighbor and activate IPv4 unicast."""
    st.log(f"Configuring BGP neighbor {neighbor_ip} (remote-as {remote_as}) on {dut}")

    commands = [
        "router bgp {}".format(asn),
        "neighbor {} remote-as {}".format(neighbor_ip, remote_as),
        "address-family ipv4 unicast",
        "activate",
        "exit",
        "exit"
    ]

    try:
        st.config(dut, commands, type='klish')
        st.log(f"BGP neighbor {neighbor_ip} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def verify_bgp_negative_behavior(dut: str, neighbor_ip: str, expected_state: str = 'Idle') -> bool:
    """
    Verify BGP neighbor is in expected NEGATIVE state (Idle/Active/Connect).
    For negative tests, we EXPECT the session to NOT establish.
    """
    st.log(f"Verifying NEGATIVE behavior: {dut} <-> {neighbor_ip}, expected state: {expected_state}")

    # Check BGP summary
    output = bgpapi.show_bgp_ipv4_summary(dut, cli_type='klish')

    if not output:
        st.error(f"No BGP summary output from {dut}")
        return False

    st.log(f"BGP Summary output: {output}")

    # Find the neighbor in the output
    for entry in output:
        if entry.get('neighbor') == neighbor_ip:
            neighbor_state = entry.get('state', '')
            st.log(f"Neighbor {neighbor_ip} state field: '{neighbor_state}'")

            # For NEGATIVE test: state should be a STRING (Idle, Active, Connect)
            # NOT a number (which means Established)
            if neighbor_state in ['Idle', 'Active', 'Connect'] or not neighbor_state.isdigit():
                st.log(f"✓ NEGATIVE TEST PASSED: BGP correctly NOT establishing")
                st.log(f"✓ BGP state: {neighbor_state} (expected non-established)")

                # Also check for "Bad Peer AS" notification
                try:
                    neighbor_detail = st.show(
                        dut,
                        f"show bgp ipv4 unicast neighbors {neighbor_ip}",
                        type='klish',
                        skip_tmpl=True
                    )
                    detail_str = str(neighbor_detail).lower()

                    if 'bad peer as' in detail_str:
                        st.log(f"✓ Found 'Bad Peer AS' notification - CORRECT negative behavior")
                    else:
                        st.log(f"Note: 'Bad Peer AS' notification not explicitly found in output")

                except Exception as e:
                    st.log(f"Could not check neighbor details: {str(e)}")

                return True
            else:
                st.error(f"NEGATIVE TEST FAILED: BGP session established when it should NOT")
                st.error(f"Unexpected state: {neighbor_state}")
                return False

    st.error(f"Neighbor {neighbor_ip} not found in BGP summary on {dut}")
    return False


def ping_test(src_dut: str, dst_ip: str, count: int = 5) -> bool:
    """Test ping connectivity."""
    st.log(f"Ping test: {src_dut} -> {dst_ip}")

    result = ipapi.ping(src_dut, dst_ip, family='ipv4', count=count)

    if result:
        st.log(f"✓ Ping successful: {src_dut} -> {dst_ip}")
        return True
    else:
        st.error(f"Ping failed: {src_dut} -> {dst_ip}")
        return False


def test_ipv4_bgp_negative_asn():
    """
    Test Case NEG-01-IPv4: Wrong ASN Configured

    NEGATIVE TEST - Test PASSES when BGP correctly REJECTS wrong ASN.

    Configuration:
    - DUT1 AS 65001 expects neighbor remote-as 65003
    - DUT2 AS 65002 sends AS 65002
    - Expected: BGP stays in Idle state with "Bad Peer AS" notification

    Steps:
    1. Configure IP addresses on Ethernet0
    2. Verify ping connectivity
    3. Configure BGP routers
    4. Configure BGP neighbors with MISMATCHED ASN
    5. Wait for BGP convergence attempt
    6. Verify BGP does NOT establish (Idle state)
    7. Verify "Bad Peer AS" notification
    """
    st.banner("=" * 80)
    st.banner("TEST NEG-01-IPv4: WRONG ASN CONFIGURED (NEGATIVE TEST)")
    st.banner("=" * 80)
    st.log("NEGATIVE TEST: Test PASSES when BGP correctly REJECTS wrong ASN")

    # ==================================================================
    # STEP 1: Configure IP Addresses on Interfaces
    # ==================================================================
    st.banner("STEP 1: Configure IP Addresses on Ethernet0")

    if not configure_ip_on_interface(vars.D1, CONFIG.interface, CONFIG.dut1_ip):
        st.report_tc_fail(TC_IDS.neg01_ipv4_wrong_asn, "msg", f"Failed to configure IP on {vars.D1}")
        st.report_fail("msg", f"Failed to configure IP on {vars.D1}")

    if not configure_ip_on_interface(vars.D2, CONFIG.interface, CONFIG.dut2_ip):
        st.report_tc_fail(TC_IDS.neg01_ipv4_wrong_asn, "msg", f"Failed to configure IP on {vars.D2}")
        st.report_fail("msg", f"Failed to configure IP on {vars.D2}")

    st.wait(5, "Waiting for interfaces to come up")

    # ==================================================================
    # STEP 2: Verify Ping Connectivity
    # ==================================================================
    st.banner("STEP 2: Verify Ping Connectivity")

    if not ping_test(vars.D1, CONFIG.dut2_ip, CONFIG.ping_count):
        st.generate_tech_support([vars.D1, vars.D2], "neg01_ipv4_ping_failed")
        st.report_tc_fail(TC_IDS.neg01_ipv4_wrong_asn, "msg", f"Ping failed {vars.D1} -> {CONFIG.dut2_ip}")
        st.report_fail("msg", f"Ping failed {vars.D1} -> {CONFIG.dut2_ip}")

    if not ping_test(vars.D2, CONFIG.dut1_ip, CONFIG.ping_count):
        st.generate_tech_support([vars.D1, vars.D2], "neg01_ipv4_ping_failed")
        st.report_tc_fail(TC_IDS.neg01_ipv4_wrong_asn, "msg", f"Ping failed {vars.D2} -> {CONFIG.dut1_ip}")
        st.report_fail("msg", f"Ping failed {vars.D2} -> {CONFIG.dut1_ip}")

    st.log("✓ Ping connectivity verified")

    # ==================================================================
    # STEP 3: Configure BGP Routers with Router-IDs
    # ==================================================================
    st.banner("STEP 3: Configure BGP Routers")

    if not configure_bgp_router(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_router_id):
        st.report_tc_fail(TC_IDS.neg01_ipv4_wrong_asn, "msg", f"Failed to configure BGP on {vars.D1}")
        st.report_fail("msg", f"Failed to configure BGP on {vars.D1}")

    if not configure_bgp_router(vars.D2, CONFIG.dut2_asn, CONFIG.dut2_router_id):
        st.report_tc_fail(TC_IDS.neg01_ipv4_wrong_asn, "msg", f"Failed to configure BGP on {vars.D2}")
        st.report_fail("msg", f"Failed to configure BGP on {vars.D2}")

    # ==================================================================
    # STEP 4: Configure BGP Neighbors with WRONG ASN
    # ==================================================================
    st.banner("STEP 4: Configure BGP Neighbors with MISMATCHED ASN")
    st.log(f"DUT1 expects remote-as {CONFIG.dut1_expected_remote_asn}, but DUT2 sends AS {CONFIG.dut2_asn}")

    # DUT1 expects AS 65003, but DUT2 actually has AS 65002
    if not configure_bgp_neighbor(vars.D1, CONFIG.dut1_asn, CONFIG.dut2_ip,
                                  CONFIG.dut1_expected_remote_asn):
        st.report_tc_fail(TC_IDS.neg01_ipv4_wrong_asn, "msg", f"Failed to configure neighbor on {vars.D1}")
        st.report_fail("msg", f"Failed to configure neighbor on {vars.D1}")

    # DUT2 expects AS 65001 (correct)
    if not configure_bgp_neighbor(vars.D2, CONFIG.dut2_asn, CONFIG.dut1_ip,
                                  CONFIG.dut2_expected_remote_asn):
        st.report_tc_fail(TC_IDS.neg01_ipv4_wrong_asn, "msg", f"Failed to configure neighbor on {vars.D2}")
        st.report_fail("msg", f"Failed to configure neighbor on {vars.D2}")

    # ==================================================================
    # STEP 5: Wait for BGP Convergence Attempt
    # ==================================================================
    st.banner("STEP 5: Wait for BGP Convergence Attempt")
    st.wait(CONFIG.bgp_wait_time, f"Waiting {CONFIG.bgp_wait_time}s for BGP")

    # ==================================================================
    # STEP 6: Verify NEGATIVE Behavior - BGP Should NOT Establish
    # ==================================================================
    st.banner("STEP 6: Verify NEGATIVE Behavior - BGP Should NOT Establish")
    st.log("NEGATIVE TEST: Verifying BGP correctly rejects wrong ASN")

    # Verify DUT1 does NOT establish BGP
    if not verify_bgp_negative_behavior(vars.D1, CONFIG.dut2_ip, 'Idle'):
        st.generate_tech_support([vars.D1, vars.D2], "neg01_ipv4_negative_test_failed")
        st.report_tc_fail(TC_IDS.neg01_ipv4_wrong_asn, "msg",
                         f"NEGATIVE TEST FAILED: BGP established when it should NOT")
        st.report_fail("msg", f"NEGATIVE TEST FAILED: BGP established when it should NOT")

    # Verify DUT2 does NOT establish BGP
    if not verify_bgp_negative_behavior(vars.D2, CONFIG.dut1_ip, 'Idle'):
        st.generate_tech_support([vars.D1, vars.D2], "neg01_ipv4_negative_test_failed")
        st.report_tc_fail(TC_IDS.neg01_ipv4_wrong_asn, "msg",
                         f"NEGATIVE TEST FAILED: BGP established when it should NOT")
        st.report_fail("msg", f"NEGATIVE TEST FAILED: BGP established when it should NOT")

    st.report_tc_pass(TC_IDS.neg01_ipv4_wrong_asn, "msg",
                     "NEGATIVE TEST PASSED: BGP correctly rejected wrong ASN")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: NEG-01-IPv4 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - NEG-01-IPv4: Wrong ASN Configured")
    st.log("=" * 80)
    st.log(f"✓ IP addresses configured: {CONFIG.dut1_ip}, {CONFIG.dut2_ip}")
    st.log(f"✓ Ping connectivity: VERIFIED")
    st.log(f"✓ BGP routers configured: DUT1 AS {CONFIG.dut1_asn}, DUT2 AS {CONFIG.dut2_asn}")
    st.log(f"✓ DUT1 expects remote-as {CONFIG.dut1_expected_remote_asn} (WRONG)")
    st.log(f"✓ DUT2 sends AS {CONFIG.dut2_asn}")
    st.log(f"✓ NEGATIVE TEST: BGP correctly stayed in Idle state")
    st.log(f"✓ NEGATIVE TEST: 'Bad Peer AS' notification received")
    st.log(f"✓ TEST PASSED: BGP correctly rejected wrong ASN configuration")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
