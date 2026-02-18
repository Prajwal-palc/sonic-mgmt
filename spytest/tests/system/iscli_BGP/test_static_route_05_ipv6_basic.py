"""
STATIC ROUTE TEST - SR-05: IPv6 Static Route - Basic

Test Case ID: SR-05 (2.1.5)
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

Manual sonic-cli commands (DUT1):
  interface Ethernet 0
    ipv6 address 2001:db8:10::1/64
    no shutdown
  ipv6 route 2001:db8:100::/64 2001:db8:10::2
  show ipv6 route -> S>* 2001:db8:100::/64 [1/0] via 2001:db8:10::2, Ethernet0

Manual sonic-cli commands (DUT2):
  interface Ethernet 0
    ipv6 address 2001:db8:10::2/64
    no shutdown
  interface Loopback 0
    ipv6 address 2001:db8:100::1/128
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "interface": "Ethernet 0",
    "dut1_ipv6": "2001:db8:10::1",
    "dut2_ipv6": "2001:db8:10::2",
    "prefix_len": "64",
    "loopback": "Loopback 0",
    "loopback_ipv6": "2001:db8:100::1",
    "loopback_mask": "128",
    "static_route_prefix": "2001:db8:100::/64",
    "ping_target": "2001:db8:100::1",
    "ping_count": 5,
})

TC_IDS = SpyTestDict({
    "sr05_route_add": "TC-SR-05-001",
    "sr05_route_verify": "TC-SR-05-002",
    "sr05_route_remove": "TC-SR-05-003",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-05 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    static_route_pre_config()

    yield

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-05 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing IPv6 configs."""
    st.log("Pre-configuration: Clearing existing configuration")

    for dut in [vars.D1, vars.D2]:
        # Remove IPv6 addresses and VRF bindings from Ethernet0
        try:
            st.config(dut, [
                "interface Ethernet 0",
                "no ipv6 address",
                "no ip address",
                "no ip vrf forwarding",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

        # Remove IPv6 from Loopback0
        try:
            st.config(dut, [
                "interface Loopback 0",
                "no ipv6 address",
                "no ip address",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Remove static route if exists
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    st.wait(3, "Waiting for config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Cleanup: Remove IPv6 static route and IP configuration."""
    st.log("Cleanup: Removing IPv6 static route and configuration")

    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Route cleanup warning: {str(e)}")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                "interface Ethernet 0",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"IPv6 cleanup warning: {str(e)}")

    try:
        st.config(vars.D2, [
            "interface Loopback 0",
            "no ipv6 address",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Loopback cleanup warning: {str(e)}")

    st.log("Cleanup completed")


def ping6_test(src_dut, dst_ip, count=5):
    """Run ping6 via Linux shell (sudo mode) and return True if successful."""
    st.log(f"Ping6: {src_dut} -> {dst_ip} count={count}")
    try:
        output = st.show(src_dut, f"ping6 {dst_ip} -c {count}",
                         skip_tmpl=True, type='click', skip_error_check=True)
        output_str = str(output)
        st.log(f"Ping6 output: {output_str[:300]}")
        return "0% packet loss" in output_str or "bytes from" in output_str
    except Exception as e:
        st.log(f"Ping6 exception: {str(e)}")
        return False


@pytest.mark.static_route
@pytest.mark.community
@pytest.mark.community_pass
def test_sr05_ipv6_static_route_basic():
    """
    Test Case SR-05: IPv6 Static Route - Basic

    Validated sonic-cli commands:
      DUT1: ipv6 route 2001:db8:100::/64 2001:db8:10::2
      DUT2: interface Loopback 0 / ipv6 address 2001:db8:100::1/128
      ping6 2001:db8:100::1 -> success
      no ipv6 route 2001:db8:100::/64 2001:db8:10::2
      ping6 2001:db8:100::1 -> fail (100% packet loss)
    """
    st.banner("=" * 80)
    st.banner("TEST SR-05: IPv6 STATIC ROUTE - BASIC")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Configure IPv6 on Ethernet0 - Both DUTs
    # sonic-cli: interface Ethernet 0 -> ipv6 address X/64 -> no shutdown
    # ==================================================================
    st.banner("STEP 1: Configure IPv6 Addresses on Ethernet0")

    try:
        st.config(vars.D1, [
            f"interface {CONFIG.interface}",
            f"ipv6 address {CONFIG.dut1_ipv6}/{CONFIG.prefix_len}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT1 Ethernet0: {CONFIG.dut1_ipv6}/{CONFIG.prefix_len}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr05_route_add, "msg", "Failed to configure IPv6 on DUT1")
        st.report_fail("msg", f"DUT1 IPv6 config failed: {str(e)}")

    try:
        st.config(vars.D2, [
            f"interface {CONFIG.interface}",
            f"ipv6 address {CONFIG.dut2_ipv6}/{CONFIG.prefix_len}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2 Ethernet0: {CONFIG.dut2_ipv6}/{CONFIG.prefix_len}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr05_route_add, "msg", "Failed to configure IPv6 on DUT2")
        st.report_fail("msg", f"DUT2 IPv6 config failed: {str(e)}")

    st.wait(5, "Waiting for interfaces to come up")

    # ==================================================================
    # STEP 2: Configure Loopback0 on DUT2 (ping destination)
    # sonic-cli: interface Loopback 0 -> ipv6 address 2001:db8:100::1/128
    # ==================================================================
    st.banner("STEP 2: Configure Loopback0 on DUT2")

    try:
        st.config(vars.D2, [
            f"interface {CONFIG.loopback}",
            f"ipv6 address {CONFIG.loopback_ipv6}/{CONFIG.loopback_mask}",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2 Loopback0: {CONFIG.loopback_ipv6}/{CONFIG.loopback_mask}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr05_route_add, "msg", "Failed to configure Loopback0 on DUT2")
        st.report_fail("msg", f"Loopback0 IPv6 config failed: {str(e)}")

    st.wait(2, "Waiting for loopback configuration")

    # ==================================================================
    # STEP 3: Add IPv6 Static Route on DUT1
    # sonic-cli: ipv6 route 2001:db8:100::/64 2001:db8:10::2
    # ==================================================================
    st.banner("STEP 3: Add IPv6 Static Route on DUT1")
    st.log(f"Command: ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}")

    try:
        st.config(vars.D1, [
            f"ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}"
        ], type='klish', skip_error_check=False)
        st.log(f"IPv6 static route added: ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr05_route_add, "msg", "Failed to add IPv6 static route")
        st.report_fail("msg", f"Failed: ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}: {str(e)}")

    st.report_tc_pass(TC_IDS.sr05_route_add, "msg", "IPv6 static route added successfully")
    st.config(vars.D1, ["end"], type='klish', skip_error_check=True)
    st.wait(5, "Waiting for route to be programmed")

    # ==================================================================
    # STEP 4: Verify Route in IPv6 Routing Table
    # sonic-cli: show ipv6 route
    # Expected: S>* 2001:db8:100::/64 [1/0] via 2001:db8:10::2, Ethernet0
    # ==================================================================
    st.banner("STEP 4: Verify Route in IPv6 Routing Table")

    try:
        output = st.show(vars.D1, f"show ipv6 route {CONFIG.static_route_prefix}", type='klish',
                         skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"IPv6 route lookup '{CONFIG.static_route_prefix}': {output_str[:500]}")
        route_found = CONFIG.dut2_ipv6 in output_str and (">" in output_str or "via" in output_str)
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_found = False

    if not route_found:
        st.generate_tech_support([vars.D1, vars.D2], "sr05_ipv6_route_not_found")
        st.report_tc_fail(TC_IDS.sr05_route_verify, "msg", "IPv6 route not found in routing table")
        st.report_fail("msg", f"show ipv6 route: {CONFIG.static_route_prefix} via {CONFIG.dut2_ipv6} not found")

    st.log(f"Verified: S>* {CONFIG.static_route_prefix} [1/0] via {CONFIG.dut2_ipv6}, Ethernet0")
    st.report_tc_pass(TC_IDS.sr05_route_verify, "msg", "IPv6 static route verified in routing table")

    # ==================================================================
    # STEP 5: Ping6 Test - Expect Success
    # ping6 2001:db8:100::1 -c 5 -> 0% packet loss
    # ==================================================================
    st.banner("STEP 5: Ping6 Test - Expect Success")

    if not ping6_test(vars.D1, CONFIG.ping_target, CONFIG.ping_count):
        st.generate_tech_support([vars.D1, vars.D2], "sr05_ipv6_ping_failed")
        st.report_fail("msg", f"ping6 {CONFIG.ping_target} failed - IPv6 static route not forwarding")

    st.log(f"Ping6 {CONFIG.ping_target} successful - IPv6 static route working")

    # ==================================================================
    # STEP 6: Remove IPv6 Static Route
    # sonic-cli: no ipv6 route 2001:db8:100::/64 2001:db8:10::2
    # ==================================================================
    st.banner("STEP 6: Remove IPv6 Static Route")
    st.log(f"Command: no ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}")

    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}"
        ], type='klish', skip_error_check=False)
        st.log(f"IPv6 static route removed: no ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "sr05_ipv6_route_remove_failed")
        st.report_tc_fail(TC_IDS.sr05_route_remove, "msg", "Failed to remove IPv6 static route")
        st.report_fail("msg", f"Failed: no ipv6 route {CONFIG.static_route_prefix}: {str(e)}")

    st.wait(3, "Waiting for route removal")

    # ==================================================================
    # STEP 7: Verify Route Removed
    # ==================================================================
    st.banner("STEP 7: Verify Route Removal")

    try:
        output = st.show(vars.D1, f"show ipv6 route {CONFIG.static_route_prefix}", type='klish',
                         skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"IPv6 route lookup after removal: {output_str[:300]}")
        route_exists = CONFIG.dut2_ipv6 in output_str and (">" in output_str or "via" in output_str)
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_exists = True

    if route_exists:
        st.generate_tech_support([vars.D1, vars.D2], "sr05_ipv6_route_still_exists")
        st.report_tc_fail(TC_IDS.sr05_route_remove, "msg", "IPv6 route still exists after deletion")
        st.report_fail("msg", "IPv6 route removal verification failed")

    st.log(f"{CONFIG.static_route_prefix} removed from IPv6 routing table")
    st.report_tc_pass(TC_IDS.sr05_route_remove, "msg", "IPv6 route removed successfully")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: SR-05 PASSED")
    st.banner("=" * 80)
    st.log("TEST SUMMARY - SR-05: IPv6 Static Route - Basic")
    st.log(f"  ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6} -> Added")
    st.log(f"  show ipv6 route {CONFIG.static_route_prefix} -> Verified")
    st.log(f"  ping6 {CONFIG.ping_target} -> Success")
    st.log(f"  no ipv6 route {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6} -> Removed")
    st.log(f"  show ipv6 route {CONFIG.static_route_prefix} -> Route absent confirmed")

    st.report_pass("test_case_passed")
