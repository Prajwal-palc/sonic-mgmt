"""
STATIC ROUTE TEST - SR-09: ECMP Route Validation

Test Case ID: SR-09 (2.1.9)
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

Manual sonic-cli commands (DUT1):
  interface Ethernet 0
    ip address 10.1.1.1/24
    no shutdown
  interface Ethernet 4
    ip address 10.2.2.1/24
    no shutdown
  ip route 50.0.0.0/24 10.1.1.2
  ip route 50.0.0.0/24 10.2.2.2
  show ip route 50.0.0.0/24 ->
    S>* 50.0.0.0/24 [1/0] via 10.1.1.2, Ethernet0, weight 1
                   [1/0] via 10.2.2.2, Ethernet4, weight 1
  ping 50.0.0.1 -c 10 -> success

Manual sonic-cli commands (DUT2):
  interface Ethernet 0
    ip address 10.1.1.2/24
    no shutdown
  interface Ethernet 4
    ip address 10.2.2.2/24
    no shutdown
  interface Loopback 1
    ip address 50.0.0.1/32
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    # DUT1 interfaces
    "intf_eth0": "Ethernet 0",
    "intf_eth4": "Ethernet 4",
    "dut1_eth0_ip": "10.1.1.1",
    "dut1_eth4_ip": "10.2.2.1",
    # DUT2 interfaces
    "dut2_eth0_ip": "10.1.1.2",
    "dut2_eth4_ip": "10.2.2.2",
    "prefix_len": "24",
    # DUT2 Loopback1 (ECMP destination)
    "loopback": "Loopback 1",
    "loopback_ip": "50.0.0.1",
    "loopback_mask": "32",
    # ECMP routes
    "ecmp_prefix": "50.0.0.0/24",
    "nexthop1": "10.1.1.2",
    "nexthop2": "10.2.2.2",
    "ping_target": "50.0.0.1",
    "ping_count": 10,
})

TC_IDS = SpyTestDict({
    "sr09_route_add": "TC-SR-09-001",
    "sr09_route_verify": "TC-SR-09-002",
    "sr09_ecmp_verify": "TC-SR-09-003",
    "sr09_route_remove": "TC-SR-09-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-09 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:2")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    static_route_pre_config()

    yield

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-09 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing configs on both interfaces."""
    st.log("Pre-configuration: Clearing existing configuration")

    for dut in [vars.D1, vars.D2]:
        for intf in ["Ethernet 0", "Ethernet 4"]:
            try:
                st.config(dut, [
                    f"interface {intf}",
                    "no ip address",
                    "no ipv6 address",
                    "no ip vrf forwarding",
                    "shutdown",
                    "exit"
                ], type='klish', skip_error_check=True)
            except Exception:
                pass

    # Remove Loopback1 on DUT2
    try:
        st.config(vars.D2, [
            "interface Loopback 1",
            "no ip address",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove ECMP routes if they exist
    for nexthop in [CONFIG.nexthop1, CONFIG.nexthop2]:
        try:
            st.config(vars.D1, [
                f"no ip route {CONFIG.ecmp_prefix} {nexthop}"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.wait(3, "Waiting for config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Cleanup: Remove ECMP routes and IP configuration."""
    st.log("Cleanup: Removing ECMP routes and IP configuration")

    for nexthop in [CONFIG.nexthop1, CONFIG.nexthop2]:
        try:
            st.config(vars.D1, [
                f"no ip route {CONFIG.ecmp_prefix} {nexthop}"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"Route cleanup warning: {str(e)}")

    for dut in [vars.D1, vars.D2]:
        for intf in ["Ethernet 0", "Ethernet 4"]:
            try:
                st.config(dut, [
                    f"interface {intf}",
                    "no ip address",
                    "shutdown",
                    "exit"
                ], type='klish', skip_error_check=True)
            except Exception as e:
                st.log(f"IP cleanup warning: {str(e)}")

    try:
        st.config(vars.D2, [
            "interface Loopback 1",
            "no ip address",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Loopback cleanup warning: {str(e)}")

    st.log("Cleanup completed")


def ping_test(src_dut, dst_ip, count=5):
    """Run ping via Linux shell (sudo mode) and return True if successful."""
    st.log(f"Ping: {src_dut} -> {dst_ip} count={count}")
    try:
        output = st.show(src_dut, f"ping {dst_ip} -c {count}",
                         skip_tmpl=True, type='click', skip_error_check=True)
        output_str = str(output)
        st.log(f"Ping output: {output_str[:300]}")
        return "0% packet loss" in output_str or "bytes from" in output_str
    except Exception as e:
        st.log(f"Ping exception: {str(e)}")
        return False


@pytest.mark.static_route
@pytest.mark.community
@pytest.mark.community_pass
def test_sr09_ecmp_static_route():
    """
    Test Case SR-09: ECMP Static Route Validation

    Validated sonic-cli commands:
      DUT1: ip route 50.0.0.0/24 10.1.1.2
      DUT1: ip route 50.0.0.0/24 10.2.2.2
      show ip route 50.0.0.0/24 -> both nexthops shown
      ping 50.0.0.1 -> success (ECMP forwarding)
      no ip route 50.0.0.0/24 10.1.1.2
      no ip route 50.0.0.0/24 10.2.2.2
    """
    st.banner("=" * 80)
    st.banner("TEST SR-09: ECMP STATIC ROUTE VALIDATION")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Configure IP on Ethernet0 - Both DUTs
    # sonic-cli: interface Ethernet 0 -> ip address X/24 -> no shutdown
    # ==================================================================
    st.banner("STEP 1: Configure IP on Ethernet0 - Both DUTs")

    try:
        st.config(vars.D1, [
            f"interface {CONFIG.intf_eth0}",
            f"ip address {CONFIG.dut1_eth0_ip}/{CONFIG.prefix_len}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT1 Ethernet0: {CONFIG.dut1_eth0_ip}/{CONFIG.prefix_len}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr09_route_add, "msg", "Failed to configure IP on DUT1 Ethernet0")
        st.report_fail("msg", f"DUT1 Ethernet0 IP config failed: {str(e)}")

    try:
        st.config(vars.D2, [
            f"interface {CONFIG.intf_eth0}",
            f"ip address {CONFIG.dut2_eth0_ip}/{CONFIG.prefix_len}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2 Ethernet0: {CONFIG.dut2_eth0_ip}/{CONFIG.prefix_len}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr09_route_add, "msg", "Failed to configure IP on DUT2 Ethernet0")
        st.report_fail("msg", f"DUT2 Ethernet0 IP config failed: {str(e)}")

    # ==================================================================
    # STEP 2: Configure IP on Ethernet4 - Both DUTs
    # sonic-cli: interface Ethernet 4 -> ip address X/24 -> no shutdown
    # ==================================================================
    st.banner("STEP 2: Configure IP on Ethernet4 - Both DUTs")

    try:
        st.config(vars.D1, [
            f"interface {CONFIG.intf_eth4}",
            f"ip address {CONFIG.dut1_eth4_ip}/{CONFIG.prefix_len}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT1 Ethernet4: {CONFIG.dut1_eth4_ip}/{CONFIG.prefix_len}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr09_route_add, "msg", "Failed to configure IP on DUT1 Ethernet4")
        st.report_fail("msg", f"DUT1 Ethernet4 IP config failed: {str(e)}")

    try:
        st.config(vars.D2, [
            f"interface {CONFIG.intf_eth4}",
            f"ip address {CONFIG.dut2_eth4_ip}/{CONFIG.prefix_len}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2 Ethernet4: {CONFIG.dut2_eth4_ip}/{CONFIG.prefix_len}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr09_route_add, "msg", "Failed to configure IP on DUT2 Ethernet4")
        st.report_fail("msg", f"DUT2 Ethernet4 IP config failed: {str(e)}")

    st.wait(5, "Waiting for interfaces to come up")

    # ==================================================================
    # STEP 3: Configure Loopback1 on DUT2 (ECMP destination)
    # sonic-cli: interface Loopback 1 -> ip address 50.0.0.1/32
    # ==================================================================
    st.banner("STEP 3: Configure Loopback1 on DUT2")

    try:
        st.config(vars.D2, [
            f"interface {CONFIG.loopback}",
            f"ip address {CONFIG.loopback_ip}/{CONFIG.loopback_mask}",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2 Loopback1: {CONFIG.loopback_ip}/{CONFIG.loopback_mask}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr09_route_add, "msg", "Failed to configure Loopback1 on DUT2")
        st.report_fail("msg", f"Loopback1 IP config failed: {str(e)}")

    st.wait(2, "Waiting for loopback configuration")

    # ==================================================================
    # STEP 4: Add Two ECMP Static Routes on DUT1
    # sonic-cli: ip route 50.0.0.0/24 10.1.1.2
    # sonic-cli: ip route 50.0.0.0/24 10.2.2.2
    # ==================================================================
    st.banner("STEP 4: Add Two ECMP Static Routes on DUT1")
    st.log(f"Command 1: ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop1}")
    st.log(f"Command 2: ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop2}")

    try:
        st.config(vars.D1, [
            f"ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop1}"
        ], type='klish', skip_error_check=False)
        st.log(f"ECMP route 1 added: ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop1}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr09_route_add, "msg", "Failed to add ECMP route via nexthop1")
        st.report_fail("msg", f"Failed: ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop1}: {str(e)}")

    try:
        st.config(vars.D1, [
            f"ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop2}"
        ], type='klish', skip_error_check=False)
        st.log(f"ECMP route 2 added: ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop2}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr09_route_add, "msg", "Failed to add ECMP route via nexthop2")
        st.report_fail("msg", f"Failed: ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop2}: {str(e)}")

    st.report_tc_pass(TC_IDS.sr09_route_add, "msg", "Both ECMP static routes added successfully")
    st.config(vars.D1, ["end"], type='klish', skip_error_check=True)
    st.wait(5, "Waiting for ECMP routes to be programmed")

    # ==================================================================
    # STEP 5: Verify Both Nexthops in Routing Table
    # sonic-cli: show ip route 50.0.0.0/24
    # Expected:
    #   S>* 50.0.0.0/24 [1/0] via 10.1.1.2, Ethernet0, weight 1
    #                   [1/0] via 10.2.2.2, Ethernet4, weight 1
    # ==================================================================
    st.banner("STEP 5: Verify ECMP - Both Nexthops in Routing Table")

    try:
        output = st.show(vars.D1, f"show ip route {CONFIG.ecmp_prefix}",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"ECMP route lookup '{CONFIG.ecmp_prefix}': {output_str[:500]}")
        nexthop1_found = CONFIG.nexthop1 in output_str and (">" in output_str or "via" in output_str)
        nexthop2_found = CONFIG.nexthop2 in output_str
        route_found = nexthop1_found and nexthop2_found
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_found = False
        nexthop1_found = False
        nexthop2_found = False

    if not route_found:
        st.generate_tech_support([vars.D1, vars.D2], "sr09_ecmp_routes_not_found")
        st.report_tc_fail(TC_IDS.sr09_route_verify, "msg",
                          f"ECMP routes not found: nexthop1={nexthop1_found}, nexthop2={nexthop2_found}")
        st.report_fail("msg",
                       f"show ip route {CONFIG.ecmp_prefix}: not both nexthops found "
                       f"({CONFIG.nexthop1}={nexthop1_found}, {CONFIG.nexthop2}={nexthop2_found})")

    st.log(f"Verified: {CONFIG.ecmp_prefix} via {CONFIG.nexthop1} AND {CONFIG.nexthop2} (ECMP)")
    st.report_tc_pass(TC_IDS.sr09_route_verify, "msg", "ECMP routes verified - both nexthops present")

    # ==================================================================
    # STEP 6: Ping Test - Expect Success (ECMP forwarding)
    # ping 50.0.0.1 -c 10 -> 0% packet loss
    # ==================================================================
    st.banner("STEP 6: Ping Test - Expect Success (ECMP Forwarding)")

    if not ping_test(vars.D1, CONFIG.ping_target, CONFIG.ping_count):
        st.generate_tech_support([vars.D1, vars.D2], "sr09_ecmp_ping_failed")
        st.report_tc_fail(TC_IDS.sr09_ecmp_verify, "msg", "Ping failed with ECMP routes")
        st.report_fail("msg", f"ping {CONFIG.ping_target} failed - ECMP not forwarding correctly")

    st.log(f"Ping {CONFIG.ping_target} successful - ECMP forwarding working")
    st.report_tc_pass(TC_IDS.sr09_ecmp_verify, "msg", "ECMP ping test passed")

    # ==================================================================
    # STEP 7: Remove First ECMP Route
    # sonic-cli: no ip route 50.0.0.0/24 10.1.1.2
    # ==================================================================
    st.banner("STEP 7: Remove First ECMP Route (nexthop1)")
    st.log(f"Command: no ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop1}")

    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop1}"
        ], type='klish', skip_error_check=False)
        st.log(f"ECMP route 1 removed: no ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop1}")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "sr09_ecmp_route1_remove_failed")
        st.report_tc_fail(TC_IDS.sr09_route_remove, "msg", "Failed to remove ECMP route 1")
        st.report_fail("msg", f"Failed: no ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop1}: {str(e)}")

    # ==================================================================
    # STEP 8: Remove Second ECMP Route
    # sonic-cli: no ip route 50.0.0.0/24 10.2.2.2
    # ==================================================================
    st.banner("STEP 8: Remove Second ECMP Route (nexthop2)")
    st.log(f"Command: no ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop2}")

    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop2}"
        ], type='klish', skip_error_check=False)
        st.log(f"ECMP route 2 removed: no ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop2}")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "sr09_ecmp_route2_remove_failed")
        st.report_tc_fail(TC_IDS.sr09_route_remove, "msg", "Failed to remove ECMP route 2")
        st.report_fail("msg", f"Failed: no ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop2}: {str(e)}")

    st.wait(3, "Waiting for route removal")

    # ==================================================================
    # STEP 9: Verify All ECMP Routes Removed
    # ==================================================================
    st.banner("STEP 9: Verify All ECMP Routes Removed")

    try:
        output = st.show(vars.D1, f"show ip route {CONFIG.ecmp_prefix}",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"ECMP route lookup after removal: {output_str[:300]}")
        route_exists = (CONFIG.nexthop1 in output_str or CONFIG.nexthop2 in output_str) and \
                       (">" in output_str or "via" in output_str)
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_exists = True

    if route_exists:
        st.generate_tech_support([vars.D1, vars.D2], "sr09_ecmp_routes_still_exist")
        st.report_tc_fail(TC_IDS.sr09_route_remove, "msg", "ECMP routes still exist after deletion")
        st.report_fail("msg", "ECMP route removal verification failed")

    st.log(f"{CONFIG.ecmp_prefix} ECMP routes removed from routing table")
    st.report_tc_pass(TC_IDS.sr09_route_remove, "msg", "All ECMP routes removed successfully")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: SR-09 PASSED")
    st.banner("=" * 80)
    st.log("TEST SUMMARY - SR-09: ECMP Static Route Validation")
    st.log(f"  ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop1} -> Added")
    st.log(f"  ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop2} -> Added")
    st.log(f"  show ip route {CONFIG.ecmp_prefix} -> Both nexthops verified")
    st.log(f"  ping {CONFIG.ping_target} -c {CONFIG.ping_count} -> Success (ECMP)")
    st.log(f"  no ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop1} -> Removed")
    st.log(f"  no ip route {CONFIG.ecmp_prefix} {CONFIG.nexthop2} -> Removed")

    st.report_pass("test_case_passed")
