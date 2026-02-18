"""
STATIC ROUTE TEST - SR-02: IPv4 Static Route - Blackhole

Test Case ID: SR-02 (2.1.2)
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_BGP/test_static_route_02_ipv4_blackhole.py \
    --logs-path ./logs/sr02_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Manual sonic-cli commands (DUT1 only):
  ip route 30.0.0.0/24 blackhole
  show ip route -> S>* 30.0.0.0/24 [1/0] unreachable (blackhole)
  ping 30.0.0.1 -> ping: connect: Invalid argument
  no ip route 30.0.0.0/24 blackhole
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "blackhole_prefix": "30.0.0.0/24",
    "ping_target": "30.0.0.1",
    "ping_count": 5,
})

TC_IDS = SpyTestDict({
    "sr02_route_add": "TC-SR-02-001",
    "sr02_route_verify": "TC-SR-02-002",
    "sr02_route_remove": "TC-SR-02-003",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-02 MODULE CONFIGURATION - START")
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
    st.banner("STATIC ROUTE SR-02 MODULE CLEANUP - START")
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
                "no ip address",
                "no ipv6 address",
                "no ip vrf forwarding",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Remove blackhole route if exists
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.blackhole_prefix} blackhole"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    st.wait(3, "Waiting for config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Cleanup: Remove blackhole route."""
    st.log("Cleanup: Removing blackhole static route")
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.blackhole_prefix} blackhole"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Cleanup warning: {str(e)}")
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
def test_sr02_ipv4_blackhole_route():
    """
    Test Case SR-02: IPv4 Blackhole Route

    Validated sonic-cli commands:
      ip route 30.0.0.0/24 blackhole
      show ip route -> S>* 30.0.0.0/24 [1/0] unreachable (blackhole)
      ping 30.0.0.1 -> ping: connect: Invalid argument
      no ip route 30.0.0.0/24 blackhole
    """
    st.banner("=" * 80)
    st.banner("TEST SR-02: IPv4 BLACKHOLE STATIC ROUTE")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Add Blackhole Static Route on DUT1
    # sonic-cli: ip route 30.0.0.0/24 blackhole
    # ==================================================================
    st.banner("STEP 1: Add Blackhole Static Route on DUT1")
    st.log(f"Command: ip route {CONFIG.blackhole_prefix} blackhole")

    try:
        st.config(vars.D1, [
            f"ip route {CONFIG.blackhole_prefix} blackhole"
        ], type='klish', skip_error_check=False)
        st.log(f"Blackhole route added: ip route {CONFIG.blackhole_prefix} blackhole")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr02_route_add, "msg", "Failed to add blackhole route")
        st.report_fail("msg", f"Failed: ip route {CONFIG.blackhole_prefix} blackhole: {str(e)}")

    st.report_tc_pass(TC_IDS.sr02_route_add, "msg", "Blackhole static route added successfully")
    st.config(vars.D1, ["end"], type='klish', skip_error_check=True)
    st.wait(5, "Waiting for route to be programmed")

    # ==================================================================
    # STEP 2: Verify Route in Routing Table
    # sonic-cli: show ip route
    # Expected: S>* 30.0.0.0/24 [1/0] unreachable (blackhole)
    # ==================================================================
    st.banner("STEP 2: Verify Blackhole Route in Routing Table")

    try:
        output = st.show(vars.D1, f"show ip route {CONFIG.blackhole_prefix}", type='klish',
                         skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup '{CONFIG.blackhole_prefix}': {output_str[:500]}")
        route_found = "blackhole" in output_str.lower() or "unreachable" in output_str.lower()
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_found = False

    if not route_found:
        st.generate_tech_support([vars.D1, vars.D2], "sr02_blackhole_not_found")
        st.report_tc_fail(TC_IDS.sr02_route_verify, "msg", "Blackhole route not found in routing table")
        st.report_fail("msg", "show ip route: 30.0.0.0/24 unreachable (blackhole) not found")

    st.log(f"Verified: S>* {CONFIG.blackhole_prefix} [1/0] unreachable (blackhole)")
    st.report_tc_pass(TC_IDS.sr02_route_verify, "msg", "Blackhole route verified in routing table")

    # ==================================================================
    # STEP 3: Verify Ping Fails (blackhole drops traffic)
    # ping 30.0.0.1 -> ping: connect: Invalid argument
    # ==================================================================
    st.banner("STEP 3: Verify Ping Fails (Blackhole Drops Traffic)")

    if ping_test(vars.D1, CONFIG.ping_target, CONFIG.ping_count):
        st.generate_tech_support([vars.D1, vars.D2], "sr02_blackhole_ping_should_fail")
        st.report_fail("msg", "Ping succeeded - blackhole route not working correctly")

    st.log(f"Ping {CONFIG.ping_target} failed as expected (ping: connect: Invalid argument)")

    # ==================================================================
    # STEP 4: Remove Blackhole Static Route
    # sonic-cli: no ip route 30.0.0.0/24 blackhole
    # ==================================================================
    st.banner("STEP 4: Remove Blackhole Static Route")
    st.log(f"Command: no ip route {CONFIG.blackhole_prefix} blackhole")

    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.blackhole_prefix} blackhole"
        ], type='klish', skip_error_check=False)
        st.log(f"Blackhole route removed: no ip route {CONFIG.blackhole_prefix} blackhole")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "sr02_blackhole_remove_failed")
        st.report_tc_fail(TC_IDS.sr02_route_remove, "msg", "Failed to remove blackhole route")
        st.report_fail("msg", f"Failed: no ip route {CONFIG.blackhole_prefix} blackhole: {str(e)}")

    st.wait(3, "Waiting for route removal")

    # ==================================================================
    # STEP 5: Verify Route Removed
    # ==================================================================
    st.banner("STEP 5: Verify Route Removal")

    try:
        output = st.show(vars.D1, f"show ip route {CONFIG.blackhole_prefix}", type='klish',
                         skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup after removal: {output_str[:300]}")
        route_exists = "blackhole" in output_str.lower() or "unreachable" in output_str.lower()
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_exists = True

    if route_exists:
        st.generate_tech_support([vars.D1, vars.D2], "sr02_blackhole_still_exists")
        st.report_tc_fail(TC_IDS.sr02_route_remove, "msg", "Blackhole route still exists after deletion")
        st.report_fail("msg", "Route removal verification failed")

    st.log(f"{CONFIG.blackhole_prefix} blackhole removed from routing table")
    st.report_tc_pass(TC_IDS.sr02_route_remove, "msg", "Blackhole route removed successfully")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: SR-02 PASSED")
    st.banner("=" * 80)
    st.log("TEST SUMMARY - SR-02: IPv4 Blackhole Static Route")
    st.log(f"  ip route {CONFIG.blackhole_prefix} blackhole -> Added")
    st.log(f"  show ip route -> S>* {CONFIG.blackhole_prefix} unreachable (blackhole)")
    st.log(f"  ping {CONFIG.ping_target} -> Failed (ping: connect: Invalid argument)")
    st.log(f"  no ip route {CONFIG.blackhole_prefix} blackhole -> Removed")

    st.report_pass("test_case_passed")
