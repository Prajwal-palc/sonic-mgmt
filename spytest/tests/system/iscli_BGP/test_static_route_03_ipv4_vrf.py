"""
STATIC ROUTE TEST - SR-03: IPv4 Static Route - VRF

Test Case ID: SR-03 (2.1.3)
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

Manual sonic-cli commands (DUT1):
  ip vrf VrfRed
  interface Ethernet 0
    ip vrf forwarding VrfRed
    ip address 10.1.1.1/24
    no shutdown
  ip route vrf VrfRed 40.0.0.0/24 10.1.1.2
  show ip route vrf VrfRed -> S>* 40.0.0.0/24 [1/0] via 10.1.1.2, Ethernet0

Manual sonic-cli commands (DUT2):
  ip vrf VrfRed
  interface Ethernet 0
    ip vrf forwarding VrfRed
    ip address 10.1.1.2/24
    no shutdown
  interface Loopback 1
    ip address 40.0.0.1/32
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "vrf_name": "VrfRed",
    "interface": "Ethernet 0",
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "prefix_len": "24",
    "loopback": "Loopback 1",
    "loopback_ip": "40.0.0.1",
    "loopback_mask": "32",
    "static_route_prefix": "40.0.0.0/24",
    "ping_target": "40.0.0.1",
    "ping_count": 5,
})

TC_IDS = SpyTestDict({
    "sr03_vrf_create": "TC-SR-03-001",
    "sr03_route_add": "TC-SR-03-002",
    "sr03_route_verify": "TC-SR-03-003",
    "sr03_route_remove": "TC-SR-03-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    global vars, data

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-03 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    static_route_pre_config()

    yield

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-03 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Clear existing VRF and IP config in correct order."""
    st.log("Pre-configuration: Clearing existing configuration")

    for dut in [vars.D1, vars.D2]:
        # Step 1: Remove IPs
        for intf in ["Ethernet 0", "Loopback 1"]:
            try:
                st.config(dut, [f"interface {intf}", "no ip address", "no ipv6 address", "exit"],
                          type='klish', skip_error_check=True)
            except Exception:
                pass
        # Step 2: Remove VRF bindings
        for intf in ["Ethernet 0", "Loopback 1"]:
            try:
                st.config(dut, [f"interface {intf}", "no ip vrf forwarding", "exit"],
                          type='klish', skip_error_check=True)
            except Exception:
                pass
        # Step 3: Delete VRF
        try:
            st.config(dut, [f"no ip vrf {CONFIG.vrf_name}"], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.wait(3, "Waiting for config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Remove VRF static route, bindings, and VRF."""
    st.log("Cleanup: Removing VRF static route configuration")
    try:
        st.config(vars.D1, [
            f"no ip route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ip}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Route cleanup warning: {str(e)}")

    for dut in [vars.D1, vars.D2]:
        for intf in ["Ethernet 0", "Loopback 1"]:
            try:
                st.config(dut, [f"interface {intf}", "no ip address", "no ip vrf forwarding", "exit"],
                          type='klish', skip_error_check=True)
            except Exception:
                pass
        try:
            st.config(dut, [f"no ip vrf {CONFIG.vrf_name}"], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"VRF delete warning: {str(e)}")

    st.log("Cleanup completed")


def ping_test_vrf(src_dut, dst_ip, vrf_name, count=5):
    """Run ping in VRF via Linux shell (ip vrf exec) and return True if successful."""
    st.log(f"Ping VRF {vrf_name}: {src_dut} -> {dst_ip}")
    try:
        output = st.show(src_dut, f"sudo ip vrf exec {vrf_name} ping {dst_ip} -c {count}",
                         skip_tmpl=True, type='click', skip_error_check=True)
        output_str = str(output)
        st.log(f"Ping VRF output: {output_str[:300]}")
        return "0% packet loss" in output_str or "bytes from" in output_str
    except Exception as e:
        st.log(f"Ping VRF exception: {str(e)}")
        return False


@pytest.mark.static_route
@pytest.mark.community
@pytest.mark.community_pass
def test_sr03_ipv4_vrf_static_route():
    """
    Test Case SR-03: IPv4 VRF Static Route

    Validated sonic-cli commands:
      ip vrf VrfRed
      interface Ethernet 0 -> ip vrf forwarding VrfRed -> ip address 10.1.1.1/24
      ip route vrf VrfRed 40.0.0.0/24 10.1.1.2
      show ip route vrf VrfRed -> S>* 40.0.0.0/24 via 10.1.1.2
      ping vrf VrfRed 40.0.0.1 -> success
      no ip route vrf VrfRed 40.0.0.0/24 10.1.1.2
    """
    st.banner("=" * 80)
    st.banner("TEST SR-03: IPv4 VRF STATIC ROUTE")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Create VRF on Both DUTs
    # sonic-cli: ip vrf VrfRed
    # ==================================================================
    st.banner("STEP 1: Create VRF on Both DUTs")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [f"ip vrf {CONFIG.vrf_name}"], type='klish', skip_error_check=True)
            st.log(f"VRF {CONFIG.vrf_name} created on {dut}")
        except Exception as e:
            st.report_tc_fail(TC_IDS.sr03_vrf_create, "msg", f"Failed to create VRF on {dut}")
            st.report_fail("msg", f"ip vrf {CONFIG.vrf_name} failed: {str(e)}")

    st.report_tc_pass(TC_IDS.sr03_vrf_create, "msg", "VRF created on both DUTs")

    # ==================================================================
    # STEP 2: Bind Ethernet0 to VRF + Configure IP - Both DUTs
    # sonic-cli: interface Ethernet 0 -> ip vrf forwarding VrfRed -> ip address X/24
    # ==================================================================
    st.banner("STEP 2: Bind Ethernet0 to VRF and Configure IP")

    try:
        st.config(vars.D1, [
            f"interface {CONFIG.interface}",
            f"ip vrf forwarding {CONFIG.vrf_name}",
            f"ip address {CONFIG.dut1_ip}/{CONFIG.prefix_len}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT1 Ethernet0: {CONFIG.dut1_ip}/{CONFIG.prefix_len} in VRF {CONFIG.vrf_name}")
    except Exception as e:
        st.report_fail("msg", f"DUT1 Ethernet0 bind failed: {str(e)}")

    try:
        st.config(vars.D2, [
            f"interface {CONFIG.interface}",
            f"ip vrf forwarding {CONFIG.vrf_name}",
            f"ip address {CONFIG.dut2_ip}/{CONFIG.prefix_len}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"DUT2 Ethernet0: {CONFIG.dut2_ip}/{CONFIG.prefix_len} in VRF {CONFIG.vrf_name}")
    except Exception as e:
        st.report_fail("msg", f"DUT2 Ethernet0 bind failed: {str(e)}")

    st.wait(5, "Waiting for interfaces to come up")

    # ==================================================================
    # STEP 3: Configure Loopback1 on DUT2 (destination)
    # sonic-cli: interface Loopback 1 -> ip address 40.0.0.1/32
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
        st.report_fail("msg", f"Loopback1 config failed: {str(e)}")

    st.wait(2, "Waiting for loopback configuration")

    # ==================================================================
    # STEP 4: Add Static Route in VRF on DUT1
    # sonic-cli: ip route vrf VrfRed 40.0.0.0/24 10.1.1.2
    # ==================================================================
    st.banner("STEP 4: Add Static Route in VRF on DUT1")
    st.log(f"Command: ip route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ip}")

    try:
        st.config(vars.D1, [
            f"ip route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ip}"
        ], type='klish', skip_error_check=False)
        st.log(f"VRF static route added")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr03_route_add, "msg", "Failed to add VRF static route")
        st.report_fail("msg", f"ip route vrf failed: {str(e)}")

    st.report_tc_pass(TC_IDS.sr03_route_add, "msg", "VRF static route added successfully")
    st.config(vars.D1, ["end"], type='klish', skip_error_check=True)
    st.wait(5, "Waiting for route to be programmed")

    # ==================================================================
    # STEP 5: Verify Route in VRF Routing Table
    # sonic-cli: show ip route vrf VrfRed
    # Expected: S>* 40.0.0.0/24 [1/0] via 10.1.1.2, Ethernet0
    # NOTE: "show ip route vrf VrfRed <prefix>" is NOT supported in sonic-cli.
    #       Must use "show ip route vrf VrfRed" and search within output.
    # ==================================================================
    st.banner("STEP 5: Verify Route in VRF Routing Table")

    try:
        output = st.show(vars.D1, f"show ip route vrf {CONFIG.vrf_name}",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"VRF route table output: {output_str[:800]}")
        route_found = (CONFIG.static_route_prefix in output_str and
                       CONFIG.dut2_ip in output_str and
                       (">" in output_str or "via" in output_str))
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_found = False

    if not route_found:
        st.generate_tech_support([vars.D1, vars.D2], "sr03_vrf_route_not_found")
        st.report_tc_fail(TC_IDS.sr03_route_verify, "msg", "VRF route not found in routing table")
        st.report_fail("msg", f"show ip route vrf {CONFIG.vrf_name}: route not found")

    st.log(f"Verified: S>* {CONFIG.static_route_prefix} via {CONFIG.dut2_ip} in VRF {CONFIG.vrf_name}")
    st.report_tc_pass(TC_IDS.sr03_route_verify, "msg", "VRF static route verified")

    # ==================================================================
    # STEP 6: Ping Test in VRF - Expect Success
    # ==================================================================
    st.banner("STEP 6: Ping Test in VRF - Expect Success")

    if not ping_test_vrf(vars.D1, CONFIG.ping_target, CONFIG.vrf_name, CONFIG.ping_count):
        st.generate_tech_support([vars.D1, vars.D2], "sr03_vrf_ping_failed")
        st.report_fail("msg", f"ping vrf {CONFIG.vrf_name} {CONFIG.ping_target} failed")

    st.log(f"Ping {CONFIG.ping_target} in VRF {CONFIG.vrf_name} successful")

    # ==================================================================
    # STEP 7: Remove VRF Static Route
    # sonic-cli: no ip route vrf VrfRed 40.0.0.0/24 10.1.1.2
    # ==================================================================
    st.banner("STEP 7: Remove VRF Static Route")

    try:
        st.config(vars.D1, [
            f"no ip route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ip}"
        ], type='klish', skip_error_check=False)
        st.log("VRF static route removed")
    except Exception as e:
        st.generate_tech_support([vars.D1, vars.D2], "sr03_vrf_route_remove_failed")
        st.report_tc_fail(TC_IDS.sr03_route_remove, "msg", "Failed to remove VRF static route")
        st.report_fail("msg", f"no ip route vrf failed: {str(e)}")

    st.wait(3, "Waiting for route removal")

    # ==================================================================
    # STEP 8: Verify Route Removed
    # NOTE: "show ip route vrf VrfRed <prefix>" is NOT supported in sonic-cli.
    #       Must use "show ip route vrf VrfRed" and check prefix absent from output.
    # ==================================================================
    st.banner("STEP 8: Verify Route Removal")

    try:
        output = st.show(vars.D1, f"show ip route vrf {CONFIG.vrf_name}",
                         type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"VRF route table after removal: {output_str[:500]}")
        route_exists = (CONFIG.static_route_prefix in output_str and
                        CONFIG.dut2_ip in output_str and
                        (">" in output_str or "via" in output_str))
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        route_exists = True

    if route_exists:
        st.generate_tech_support([vars.D1, vars.D2], "sr03_vrf_route_still_exists")
        st.report_tc_fail(TC_IDS.sr03_route_remove, "msg", "VRF route still exists after deletion")
        st.report_fail("msg", "VRF route removal verification failed")

    st.log(f"{CONFIG.static_route_prefix} removed from VRF {CONFIG.vrf_name}")
    st.report_tc_pass(TC_IDS.sr03_route_remove, "msg", "VRF static route removed successfully")

    st.banner("=" * 80)
    st.banner("TEST RESULT: SR-03 PASSED")
    st.banner("=" * 80)
    st.log("TEST SUMMARY - SR-03: IPv4 VRF Static Route")
    st.log(f"  ip vrf {CONFIG.vrf_name} -> Created")
    st.log(f"  ip route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ip} -> Added")
    st.log(f"  show ip route vrf {CONFIG.vrf_name} -> Verified")
    st.log(f"  ping vrf {CONFIG.vrf_name} {CONFIG.ping_target} -> Success")
    st.log(f"  no ip route vrf {CONFIG.vrf_name} {CONFIG.static_route_prefix} {CONFIG.dut2_ip} -> Removed")

    st.report_pass("test_case_passed")
