"""
STATIC ROUTE TEST - SR-06: IPv6 Static Route - Blackhole

Test Case ID: SR-06 (2.1.6)
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

Manual sonic-cli commands (DUT1 only):
  ipv6 route 2001:db8:999::/64 blackhole
  show ipv6 route -> S>* 2001:db8:999::/64 [1/0] unreachable (blackhole)
  ping6 2001:db8:999::1 -> ping6: connect: Invalid argument
  no ipv6 route 2001:db8:999::/64 blackhole
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "blackhole_prefix": "2001:db8:999::/64",
    "ping_target": "2001:db8:999::1",
    "ping_count": 5,
})

TC_IDS = SpyTestDict({
    "sr06_route_add": "TC-SR-06-001",
    "sr06_route_verify": "TC-SR-06-002",
    "sr06_route_remove": "TC-SR-06-003",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-06 MODULE CONFIGURATION - START")
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
    st.banner("STATIC ROUTE SR-06 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing configuration")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                "interface Ethernet 0",
                "no ipv6 address",
                "no ip address",
                "no ip vrf forwarding",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Remove blackhole route if exists
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.blackhole_prefix} blackhole"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    st.wait(3, "Waiting for config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Cleanup: Remove IPv6 blackhole route."""
    st.log("Cleanup: Removing IPv6 blackhole static route")
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.blackhole_prefix} blackhole"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Cleanup warning: {str(e)}")
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
def test_sr06_ipv6_blackhole_route():
    """
    Test Case SR-06: IPv6 Blackhole Route

    Validated sonic-cli commands:
      ipv6 route 2001:db8:999::/64 blackhole
      show ipv6 route -> S>* 2001:db8:999::/64 [1/0] unreachable (blackhole)
      ping6 2001:db8:999::1 -> ping6: connect: Invalid argument
      no ipv6 route 2001:db8:999::/64 blackhole
    """
    st.banner("=" * 80)
    st.banner("TEST SR-06: IPv6 BLACKHOLE STATIC ROUTE")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Add IPv6 Blackhole Static Route on DUT1
    # sonic-cli: ipv6 route 2001:db8:999::/64 blackhole
    # ==================================================================
    st.banner("STEP 1: Add IPv6 Blackhole Static Route on DUT1")
    st.log(f"Command: ipv6 route {CONFIG.blackhole_prefix} blackhole")

    try:
        st.config(vars.D1, [
            f"ipv6 route {CONFIG.blackhole_prefix} blackhole"
        ], type='klish', skip_error_check=False)
        st.log(f"IPv6 blackhole route added: ipv6 route {CONFIG.blackhole_prefix} blackhole")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr06_route_add, "msg", "Failed to add IPv6 blackhole route")
        st.report_fail("msg", f"Failed: ipv6 route {CONFIG.blackhole_prefix} blackhole: {str(e)}")

    st.report_tc_pass(TC_IDS.sr06_route_add, "msg", "IPv6 blackhole static route added successfully")
    st.config(vars.D1, ["end"], type='klish', skip_error_check=True)
    st.wait(5, "Waiting for route to be programmed")

    # ==================================================================
    # STEP 2: Verify Route in IPv6 Routing Table
    # sonic-cli: show ipv6 route
    # Expected: S>* 2001:db8:999::/64 [1/0] unreachable (blackhole)
    # ==================================================================
    st.banner("STEP 2: Verify IPv6 Blackhole Route in Routing Table")

    try:
        output = st.show(vars.D1, f"show ipv6 route {CONFIG.blackhole_prefix}", type='klish',
                         skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"IPv6 route lookup '{CONFIG.blackhole_prefix}': {output_str[:500]}")
        route_found = "blackhole" in output_str.lower() or "unreachable" in output_str.lower()
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_found = False

    if not route_found:
        st.generate_tech_support([vars.D1, vars.D2], "sr06_ipv6_blackhole_not_found")
        st.report_tc_fail(TC_IDS.sr06_route_verify, "msg", "IPv6 blackhole route not found in routing table")
        st.report_fail("msg", f"show ipv6 route: {CONFIG.blackhole_prefix} unreachable (blackhole) not found")

    st.log(f"Verified: S>* {CONFIG.blackhole_prefix} [1/0] unreachable (blackhole)")
    st.report_tc_pass(TC_IDS.sr06_route_verify, "msg", "IPv6 blackhole route verified in routing table")

    # ==================================================================
    # STEP 3: Verify Ping6 Fails (blackhole drops traffic)
    # ping6 2001:db8:999::1 -> ping6: connect: Invalid argument
    # ==================================================================
    st.banner("STEP 3: Verify Ping6 Fails (IPv6 Blackhole Drops Traffic)")

    if ping6_test(vars.D1, CONFIG.ping_target, CONFIG.ping_count):
        st.generate_tech_support([vars.D1, vars.D2], "sr06_ipv6_blackhole_ping_should_fail")
        st.report_fail("msg", "Ping6 succeeded - IPv6 blackhole route not working correctly")

    st.log(f"Ping6 {CONFIG.ping_target} failed as expected (ping6: connect: Invalid argument)")

    # ==================================================================
    # STEP 4: Remove IPv6 Blackhole Static Route
    # sonic-cli: no ipv6 route 2001:db8:999::/64 blackhole
    # ==================================================================
    st.banner("STEP 4: Remove IPv6 Blackhole Static Route")
    st.log(f"Command: no ipv6 route {CONFIG.blackhole_prefix} blackhole")

    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.blackhole_prefix} blackhole"
        ], type='klish', skip_error_check=False)
        st.log(f"IPv6 blackhole route removed: no ipv6 route {CONFIG.blackhole_prefix} blackhole")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "sr06_ipv6_blackhole_remove_failed")
        st.report_tc_fail(TC_IDS.sr06_route_remove, "msg", "Failed to remove IPv6 blackhole route")
        st.report_fail("msg", f"Failed: no ipv6 route {CONFIG.blackhole_prefix} blackhole: {str(e)}")

    st.wait(3, "Waiting for route removal")

    # ==================================================================
    # STEP 5: Verify Route Removed
    # ==================================================================
    st.banner("STEP 5: Verify Route Removal")

    try:
        output = st.show(vars.D1, f"show ipv6 route {CONFIG.blackhole_prefix}", type='klish',
                         skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"IPv6 route lookup after removal: {output_str[:300]}")
        route_exists = "blackhole" in output_str.lower() or "unreachable" in output_str.lower()
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_exists = True

    if route_exists:
        st.generate_tech_support([vars.D1, vars.D2], "sr06_ipv6_blackhole_still_exists")
        st.report_tc_fail(TC_IDS.sr06_route_remove, "msg", "IPv6 blackhole route still exists after deletion")
        st.report_fail("msg", "IPv6 route removal verification failed")

    st.log(f"{CONFIG.blackhole_prefix} blackhole removed from IPv6 routing table")
    st.report_tc_pass(TC_IDS.sr06_route_remove, "msg", "IPv6 blackhole route removed successfully")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: SR-06 PASSED")
    st.banner("=" * 80)
    st.log("TEST SUMMARY - SR-06: IPv6 Blackhole Static Route")
    st.log(f"  ipv6 route {CONFIG.blackhole_prefix} blackhole -> Added")
    st.log(f"  show ipv6 route -> S>* {CONFIG.blackhole_prefix} unreachable (blackhole)")
    st.log(f"  ping6 {CONFIG.ping_target} -> Failed (ping6: connect: Invalid argument)")
    st.log(f"  no ipv6 route {CONFIG.blackhole_prefix} blackhole -> Removed")

    st.report_pass("test_case_passed")
