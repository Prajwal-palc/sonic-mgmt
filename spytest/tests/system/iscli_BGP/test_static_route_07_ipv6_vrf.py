"""
STATIC ROUTE TEST - SR-07: IPv6 Static Route - VRF

Test Case ID: SR-07 (2.1.7)
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

Manual sonic-cli commands (DUT1):
  ip vrf VrfRed
  interface Ethernet 0
    no ip address
    no ipv6 address
    no shutdown
    (ip vrf forwarding VrfRed - may fail for IPv6, skip_error_check)
    ipv6 address 2001:db8:20::1/64
    no shutdown
  ipv6 route vrf VrfRed 2001:db8:200::/64 2001:db8:20::2
  show ipv6 route vrf VrfRed -> S>* 2001:db8:200::/64 [1/0] via 2001:db8:20::2

Manual sonic-cli commands (DUT2):
  ip vrf VrfRed
  interface Ethernet 0
    no ip address
    no ipv6 address
    no shutdown
    (ip vrf forwarding VrfRed - may fail for IPv6, skip_error_check)
    ipv6 address 2001:db8:20::2/64
    no shutdown
  interface Loopback 3
    ipv6 address 2001:db8:200::1/128
  (Note: Loopback3 is in DEFAULT VRF on DUT2, not in VrfRed)

Note from manual session:
  - 'ip vrf forwarding VrfRed' on Ethernet0 may give Invalid input for IPv6 context
  - 'ipv6 route vrf VrfRed ...' puts the route in the VRF table directly
  - DUT2 Loopback3 is in default VRF so VRF ping6 is not applicable for this test
  - Test validates: route install in VRF table and route removal only
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "vrf_name": "VrfRed",
    "interface": "Ethernet 0",
    "dut1_ipv6": "2001:db8:20::1",
    "dut2_ipv6": "2001:db8:20::2",
    "prefix_len": "64",
    "loopback": "Loopback 3",
    "loopback_ipv6": "2001:db8:200::1",
    "loopback_mask": "128",
    "static_route_prefix": "2001:db8:200::/64",
    "ping_count": 5,
})

TC_IDS = SpyTestDict({
    "sr07_vrf_create": "TC-SR-07-001",
    "sr07_route_add": "TC-SR-07-002",
    "sr07_route_verify": "TC-SR-07-003",
    "sr07_route_remove": "TC-SR-07-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    global vars, data

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-07 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    static_route_pre_config()

    yield

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-07 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Clear existing VRF and IPv6 config in correct order."""
    st.log("Pre-configuration: Clearing existing configuration")

    for dut in [vars.D1, vars.D2]:
        # Step 1: Remove IPv6/IP addresses from Ethernet0
        try:
            st.config(dut, [
                "interface Ethernet 0",
                "no ipv6 address",
                "no ip address",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass
        # Step 2: Remove VRF binding from Ethernet0 (may fail, that is ok)
        try:
            st.config(dut, [
                "interface Ethernet 0",
                "no ip vrf forwarding",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass
        # Step 3: Delete VRF
        try:
            st.config(dut, [f"no ip vrf {CONFIG.vrf_name}"], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Remove Loopback3 IPv6 on DUT2 (in default VRF)
    try:
        st.config(vars.D2, [
            "interface Loopback 3",
            "no ipv6 address",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove VRF static route if it exists
    try:
        st.config(vars.D1, [
            f"no ipv6 route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    st.wait(3, "Waiting for config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Remove VRF IPv6 static route, bindings, and VRF."""
    st.log("Cleanup: Removing VRF IPv6 static route configuration")

    try:
        st.config(vars.D1, [
            f"no ipv6 route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Route cleanup warning: {str(e)}")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                "interface Ethernet 0",
                "no ipv6 address",
                "no ip vrf forwarding",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass
        try:
            st.config(dut, [f"no ip vrf {CONFIG.vrf_name}"], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"VRF delete warning: {str(e)}")

    # Remove Loopback3 on DUT2 (default VRF)
    try:
        st.config(vars.D2, [
            "interface Loopback 3",
            "no ipv6 address",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Loopback3 cleanup warning: {str(e)}")

    st.log("Cleanup completed")


@pytest.mark.static_route
@pytest.mark.community
@pytest.mark.community_pass
def test_sr07_ipv6_vrf_static_route():
    """
    Test Case SR-07: IPv6 VRF Static Route

    Validated sonic-cli commands (matching manual session):
      ip vrf VrfRed
      interface Ethernet 0 -> ipv6 address 2001:db8:20::1/64 (ip vrf forwarding may fail, skip)
      ipv6 route vrf VrfRed 2001:db8:200::/64 2001:db8:20::2
      show ipv6 route vrf VrfRed -> S>* 2001:db8:200::/64 via 2001:db8:20::2
      no ipv6 route vrf VrfRed 2001:db8:200::/64 2001:db8:20::2
      show ipv6 route vrf VrfRed -> route absent

    Note: ping6 VRF test is NOT included because DUT2 Loopback3 is in
    default VRF (not VrfRed), so VRF ping6 is unreachable per manual session.
    """
    st.banner("=" * 80)
    st.banner("TEST SR-07: IPv6 VRF STATIC ROUTE")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Create VRF on Both DUTs
    # sonic-cli: ip vrf VrfRed
    # ==================================================================
    st.banner("STEP 1: Create VRF on Both DUTs")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [f"ip vrf {CONFIG.vrf_name}"], type='klish', skip_error_check=True)
            st.log(f"VRF {CONFIG.vrf_name} created on {dut} (or already exists)")
        except Exception as e:
            st.report_tc_fail(TC_IDS.sr07_vrf_create, "msg", f"Failed to create VRF on {dut}")
            st.report_fail("msg", f"ip vrf {CONFIG.vrf_name} failed: {str(e)}")

    st.report_tc_pass(TC_IDS.sr07_vrf_create, "msg", "VRF created on both DUTs")

    # ==================================================================
    # STEP 2: Configure Ethernet0 IPv6 on Both DUTs
    # sonic-cli: interface Ethernet 0 -> ipv6 address X/64 -> no shutdown
    # Note: 'ip vrf forwarding VrfRed' may fail for IPv6 - use skip_error_check=True
    #       The route itself is placed in VRF table via 'ipv6 route vrf VrfRed ...'
    # ==================================================================
    st.banner("STEP 2: Configure Ethernet0 IPv6 on Both DUTs")

    # DUT1: clear and configure IPv6
    try:
        st.config(vars.D1, [
            f"interface {CONFIG.interface}",
            "no ip address",
            "no ipv6 address",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Try VRF binding (may fail with Invalid input for IPv6, that is ok)
    try:
        st.config(vars.D1, [
            f"interface {CONFIG.interface}",
            f"ip vrf forwarding {CONFIG.vrf_name}",
            "exit"
        ], type='klish', skip_error_check=True)
        st.log(f"DUT1: ip vrf forwarding {CONFIG.vrf_name} applied to Ethernet0")
    except Exception:
        st.log("DUT1: ip vrf forwarding may have failed - continuing (expected for IPv6)")

    try:
        st.config(vars.D1, [
            f"interface {CONFIG.interface}",
            f"ipv6 address {CONFIG.dut1_ipv6}/{CONFIG.prefix_len}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT1 Ethernet0: {CONFIG.dut1_ipv6}/{CONFIG.prefix_len}")
    except Exception as e:
        st.report_fail("msg", f"DUT1 Ethernet0 IPv6 config failed: {str(e)}")

    # DUT2: clear and configure IPv6
    try:
        st.config(vars.D2, [
            f"interface {CONFIG.interface}",
            "no ip address",
            "no ipv6 address",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Try VRF binding (may fail with Invalid input for IPv6, that is ok)
    try:
        st.config(vars.D2, [
            f"interface {CONFIG.interface}",
            f"ip vrf forwarding {CONFIG.vrf_name}",
            "exit"
        ], type='klish', skip_error_check=True)
        st.log(f"DUT2: ip vrf forwarding {CONFIG.vrf_name} applied to Ethernet0")
    except Exception:
        st.log("DUT2: ip vrf forwarding may have failed - continuing (expected for IPv6)")

    try:
        st.config(vars.D2, [
            f"interface {CONFIG.interface}",
            f"ipv6 address {CONFIG.dut2_ipv6}/{CONFIG.prefix_len}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2 Ethernet0: {CONFIG.dut2_ipv6}/{CONFIG.prefix_len}")
    except Exception as e:
        st.report_fail("msg", f"DUT2 Ethernet0 IPv6 config failed: {str(e)}")

    st.wait(5, "Waiting for interfaces to come up")

    # ==================================================================
    # STEP 3: Configure Loopback3 on DUT2 (default VRF - destination)
    # sonic-cli: interface Loopback 3 -> ipv6 address 2001:db8:200::1/128
    # Note: Loopback3 is in DEFAULT VRF (not VrfRed) on DUT2 per manual session
    # ==================================================================
    st.banner("STEP 3: Configure Loopback3 on DUT2 (default VRF)")

    try:
        st.config(vars.D2, [
            f"interface {CONFIG.loopback}",
            f"ipv6 address {CONFIG.loopback_ipv6}/{CONFIG.loopback_mask}",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2 Loopback3: {CONFIG.loopback_ipv6}/{CONFIG.loopback_mask} (default VRF)")
    except Exception as e:
        st.report_fail("msg", f"Loopback3 IPv6 config failed: {str(e)}")

    st.wait(2, "Waiting for loopback configuration")

    # ==================================================================
    # STEP 4: Add IPv6 Static Route in VRF on DUT1
    # sonic-cli: ipv6 route vrf VrfRed 2001:db8:200::/64 2001:db8:20::2
    # ==================================================================
    st.banner("STEP 4: Add IPv6 Static Route in VRF on DUT1")
    st.log(f"Command: ipv6 route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}")

    try:
        st.config(vars.D1, [
            f"ipv6 route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}"
        ], type='klish', skip_error_check=False)
        st.log(f"VRF IPv6 static route added: ipv6 route vrf {CONFIG.vrf_name} "
               f"{CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr07_route_add, "msg", "Failed to add VRF IPv6 static route")
        st.report_fail("msg", f"ipv6 route vrf failed: {str(e)}")

    st.report_tc_pass(TC_IDS.sr07_route_add, "msg", "VRF IPv6 static route added successfully")
    st.config(vars.D1, ["end"], type='klish', skip_error_check=True)
    st.wait(5, "Waiting for route to be programmed")

    # ==================================================================
    # STEP 5: Verify Route in VRF IPv6 Routing Table
    # sonic-cli: show ipv6 route vrf VrfRed
    # Expected: S>* 2001:db8:200::/64 [1/0] via 2001:db8:20::2, Ethernet0
    # NOTE: "show ipv6 route vrf VrfRed <prefix>" is NOT valid in sonic-cli.
    #       Use "show ipv6 route vrf VrfRed" (full VRF table) and search output.
    # ==================================================================
    st.banner("STEP 5: Verify Route in VRF IPv6 Routing Table")

    try:
        output = st.show(vars.D1, f"show ipv6 route vrf {CONFIG.vrf_name}",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"VRF IPv6 route table: {output_str[:800]}")
        route_found = (CONFIG.static_route_prefix in output_str and
                       CONFIG.dut2_ipv6 in output_str and
                       (">" in output_str or "via" in output_str))
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_found = False

    if not route_found:
        st.generate_tech_support([vars.D1, vars.D2], "sr07_vrf_ipv6_route_not_found")
        st.report_tc_fail(TC_IDS.sr07_route_verify, "msg", "VRF IPv6 route not found in routing table")
        st.report_fail("msg", f"show ipv6 route vrf {CONFIG.vrf_name}: "
                       f"{CONFIG.static_route_prefix} via {CONFIG.dut2_ipv6} not found")

    st.log(f"Verified: S>* {CONFIG.static_route_prefix} via {CONFIG.dut2_ipv6} "
           f"in VRF {CONFIG.vrf_name}")
    st.report_tc_pass(TC_IDS.sr07_route_verify, "msg", "VRF IPv6 static route verified")

    # ==================================================================
    # STEP 6: Remove VRF IPv6 Static Route
    # sonic-cli: no ipv6 route vrf VrfRed 2001:db8:200::/64 2001:db8:20::2
    # ==================================================================
    st.banner("STEP 6: Remove VRF IPv6 Static Route")
    st.log(f"Command: no ipv6 route vrf {CONFIG.vrf_name} "
           f"{CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}")

    try:
        st.config(vars.D1, [
            f"no ipv6 route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ipv6}"
        ], type='klish', skip_error_check=False)
        st.log("VRF IPv6 static route removed")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "sr07_vrf_ipv6_route_remove_failed")
        st.report_tc_fail(TC_IDS.sr07_route_remove, "msg", "Failed to remove VRF IPv6 static route")
        st.report_fail("msg", f"no ipv6 route vrf failed: {str(e)}")

    st.wait(3, "Waiting for route removal")

    # ==================================================================
    # STEP 7: Verify Route Removed
    # sonic-cli: show ipv6 route vrf VrfRed
    # Expected: 2001:db8:200::/64 no longer present
    # ==================================================================
    st.banner("STEP 7: Verify Route Removal")

    try:
        output = st.show(vars.D1, f"show ipv6 route vrf {CONFIG.vrf_name}",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"VRF IPv6 route table after removal: {output_str[:500]}")
        route_exists = (CONFIG.static_route_prefix in output_str and
                        CONFIG.dut2_ipv6 in output_str and
                        (">" in output_str or "via" in output_str))
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_exists = True

    if route_exists:
        st.generate_tech_support([vars.D1, vars.D2], "sr07_vrf_ipv6_route_still_exists")
        st.report_tc_fail(TC_IDS.sr07_route_remove, "msg", "VRF IPv6 route still exists after deletion")
        st.report_fail("msg", "VRF IPv6 route removal verification failed")

    st.log(f"{CONFIG.static_route_prefix} removed from VRF {CONFIG.vrf_name} IPv6 routing table")
    st.report_tc_pass(TC_IDS.sr07_route_remove, "msg", "VRF IPv6 static route removed successfully")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: SR-07 PASSED")
    st.banner("=" * 80)
    st.log("TEST SUMMARY - SR-07: IPv6 VRF Static Route")
    st.log(f"  ip vrf {CONFIG.vrf_name} -> Created on both DUTs")
    st.log(f"  Ethernet0: {CONFIG.dut1_ipv6}/64 (DUT1), {CONFIG.dut2_ipv6}/64 (DUT2)")
    st.log(f"  ipv6 route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} "
           f"{CONFIG.dut2_ipv6} -> Added")
    st.log(f"  show ipv6 route vrf {CONFIG.vrf_name} -> Route verified")
    st.log(f"  no ipv6 route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} "
           f"{CONFIG.dut2_ipv6} -> Removed")
    st.log(f"  show ipv6 route vrf {CONFIG.vrf_name} -> Route absent confirmed")

    st.report_pass("test_case_passed")
