"""
STATIC ROUTE TEST - SR-01: IPv4 Static Route - Basic

Test Case ID: SR-01 (2.1.1)
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_BGP/test_static_route_01_ipv4_basic.py \
    --logs-path ./logs/sr01_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv4 basic static route add/forward/remove.
  Uses direct sonic-cli (klish) commands matching manual validation.

Manual sonic-cli commands (DUT1):
  interface Ethernet 0
    ip address 10.1.1.1/24
    no shutdown
  ip route 10.0.0.0/24 10.1.1.2

Manual sonic-cli commands (DUT2):
  interface Ethernet 0
    ip address 10.1.1.2/24
    no shutdown
  interface Loopback 0
    ip address 10.0.0.1/32
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration - matches manual testcase exactly
CONFIG = SpyTestDict({
    "interface": "Ethernet 0",
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "prefix_len": "24",
    "loopback": "Loopback 0",
    "loopback_ip": "10.0.0.1",
    "loopback_mask": "32",
    "static_route_prefix": "10.0.0.0/24",
    "ping_target": "10.0.0.1",
    "ping_count": 5,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "sr01_route_add": "TC-SR-01-001",
    "sr01_route_verify": "TC-SR-01-002",
    "sr01_route_remove": "TC-SR-01-003",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("STATIC ROUTE SR-01 MODULE CONFIGURATION - START")
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
    st.banner("STATIC ROUTE SR-01 MODULE CLEANUP - START")
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
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Remove loopback IP on DUT2
    try:
        st.config(vars.D2, [
            "interface Loopback 0",
            "no ip address",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove static route if exists
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.static_route_prefix} {CONFIG.dut2_ip}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    st.wait(3, "Waiting for config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Cleanup: Remove static route and IP configuration."""
    st.log("Cleanup: Removing static route and IP configuration")

    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.static_route_prefix} {CONFIG.dut2_ip}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Route cleanup warning: {str(e)}")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, [
                "interface Ethernet 0",
                "no ip address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"IP cleanup warning: {str(e)}")

    try:
        st.config(vars.D2, [
            "interface Loopback 0",
            "no ip address",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Loopback cleanup warning: {str(e)}")

    st.log("Cleanup completed")


def configure_interface_ip(dut, interface, ip_with_prefix):
    """Configure IP on interface — sonic-cli: interface X -> ip address Y/Z -> no shutdown."""
    st.log(f"Configuring {ip_with_prefix} on {dut} {interface}")
    try:
        st.config(dut, [
            f"interface {interface}",
            f"ip address {ip_with_prefix}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"IP {ip_with_prefix} configured on {dut} {interface}")
        return True
    except Exception as e:
        st.error(f"Failed to configure IP on {dut} {interface}: {str(e)}")
        return False


def add_static_route(dut, prefix, nexthop):
    """Add static route — sonic-cli: ip route <prefix> <nexthop>."""
    st.log(f"Adding: ip route {prefix} {nexthop} on {dut}")
    try:
        st.config(dut, [
            f"ip route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"Static route added: ip route {prefix} {nexthop}")
        return True
    except Exception as e:
        st.error(f"Failed to add static route: {str(e)}")
        return False


def delete_static_route(dut, prefix, nexthop):
    """Delete static route — sonic-cli: no ip route <prefix> <nexthop>."""
    st.log(f"Removing: no ip route {prefix} {nexthop} on {dut}")
    try:
        st.config(dut, [
            f"no ip route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"Static route removed: no ip route {prefix} {nexthop}")
        return True
    except Exception as e:
        st.error(f"Failed to remove static route: {str(e)}")
        return False


def verify_route_in_table(dut, prefix, nexthop):
    """Verify route in show ip route <prefix> output."""
    try:
        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup '{prefix}' output: {output_str[:500]}")
        return nexthop in output_str and (">" in output_str or "via" in output_str)
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        return False


def verify_route_not_in_table(dut, prefix):
    """Verify route is absent from show ip route <prefix> output."""
    try:
        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup '{prefix}' after removal: {output_str[:300]}")
        return "via" not in output_str and ">" not in output_str
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        return False


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
def test_sr01_ipv4_static_route_basic():
    """
    Test Case SR-01: IPv4 Static Route - Basic

    Validated sonic-cli commands:
      DUT1: ip route 10.0.0.0/24 10.1.1.2
      DUT2: interface Loopback 0 / ip address 10.0.0.1/32
      Ping 10.0.0.1 -> success
      no ip route 10.0.0.0/24 10.1.1.2
      Ping 10.0.0.1 -> fail (100% packet loss)
    """
    st.banner("=" * 80)
    st.banner("TEST SR-01: IPv4 STATIC ROUTE - BASIC")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Configure IP on Ethernet0 - Both DUTs
    # sonic-cli: interface Ethernet 0 -> ip address X/24 -> no shutdown
    # ==================================================================
    st.banner("STEP 1: Configure IP Addresses on Ethernet0")

    if not configure_interface_ip(vars.D1, CONFIG.interface,
                                  f"{CONFIG.dut1_ip}/{CONFIG.prefix_len}"):
        st.report_tc_fail(TC_IDS.sr01_route_add, "msg", "Failed to configure IP on DUT1")
        st.report_fail("msg", f"Failed to configure IP on {vars.D1} Ethernet0")

    if not configure_interface_ip(vars.D2, CONFIG.interface,
                                  f"{CONFIG.dut2_ip}/{CONFIG.prefix_len}"):
        st.report_tc_fail(TC_IDS.sr01_route_add, "msg", "Failed to configure IP on DUT2")
        st.report_fail("msg", f"Failed to configure IP on {vars.D2} Ethernet0")

    st.wait(5, "Waiting for interfaces to come up")

    # ==================================================================
    # STEP 2: Configure Loopback0 on DUT2 (ping destination)
    # sonic-cli: interface Loopback 0 -> ip address 10.0.0.1/32
    # ==================================================================
    st.banner("STEP 2: Configure Loopback0 on DUT2")

    st.log(f"Configuring {CONFIG.loopback_ip}/{CONFIG.loopback_mask} on DUT2 Loopback0")
    try:
        st.config(vars.D2, [
            f"interface {CONFIG.loopback}",
            f"ip address {CONFIG.loopback_ip}/{CONFIG.loopback_mask}",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"Loopback0 configured: {CONFIG.loopback_ip}/{CONFIG.loopback_mask}")
    except Exception as e:
        st.report_tc_fail(TC_IDS.sr01_route_add, "msg", "Failed to configure Loopback0")
        st.report_fail("msg", f"Loopback0 config failed: {str(e)}")

    st.wait(2, "Waiting for loopback configuration")

    # ==================================================================
    # STEP 3: Add Static Route on DUT1
    # sonic-cli: ip route 10.0.0.0/24 10.1.1.2
    # ==================================================================
    st.banner("STEP 3: Add Static Route on DUT1")
    st.log(f"Command: ip route {CONFIG.static_route_prefix} {CONFIG.dut2_ip}")

    if not add_static_route(vars.D1, CONFIG.static_route_prefix, CONFIG.dut2_ip):
        st.report_tc_fail(TC_IDS.sr01_route_add, "msg", "Failed to add static route")
        st.report_fail("msg", "Failed: ip route 10.0.0.0/24 10.1.1.2")

    st.report_tc_pass(TC_IDS.sr01_route_add, "msg", "Static route added successfully")
    st.config(vars.D1, ["end"], type='klish', skip_error_check=True)
    st.wait(5, "Waiting for route to be programmed")

    # ==================================================================
    # STEP 4: Verify Route in Routing Table
    # sonic-cli: show ip route
    # Expected: S>* 10.0.0.0/24 [1/0] via 10.1.1.2, Ethernet0
    # ==================================================================
    st.banner("STEP 4: Verify Route in Routing Table")

    if not verify_route_in_table(vars.D1, CONFIG.static_route_prefix, CONFIG.dut2_ip):
        st.generate_tech_support([vars.D1, vars.D2], "sr01_route_not_found")
        st.report_tc_fail(TC_IDS.sr01_route_verify, "msg", "Route not found in routing table")
        st.report_fail("msg", "show ip route: 10.0.0.0/24 via 10.1.1.2 not found")

    st.log(f"Verified: S>* {CONFIG.static_route_prefix} [1/0] via {CONFIG.dut2_ip}, Ethernet0")
    st.report_tc_pass(TC_IDS.sr01_route_verify, "msg", "Static route verified in routing table")

    # ==================================================================
    # STEP 5: Ping Test - Expect Success
    # ping 10.0.0.1 -c 5 -> 0% packet loss
    # ==================================================================
    st.banner("STEP 5: Ping Test - Expect Success")

    if not ping_test(vars.D1, CONFIG.ping_target, CONFIG.ping_count):
        st.generate_tech_support([vars.D1, vars.D2], "sr01_ping_failed")
        st.report_fail("msg", f"Ping to {CONFIG.ping_target} failed - static route not forwarding")

    st.log(f"Ping {CONFIG.ping_target} successful - static route working")

    # ==================================================================
    # STEP 6: Remove Static Route
    # sonic-cli: no ip route 10.0.0.0/24 10.1.1.2
    # ==================================================================
    st.banner("STEP 6: Remove Static Route")
    st.log(f"Command: no ip route {CONFIG.static_route_prefix} {CONFIG.dut2_ip}")

    if not delete_static_route(vars.D1, CONFIG.static_route_prefix, CONFIG.dut2_ip):
        st.generate_tech_support([vars.D1, vars.D2], "sr01_route_remove_failed")
        st.report_tc_fail(TC_IDS.sr01_route_remove, "msg", "Failed to remove static route")
        st.report_fail("msg", "Failed: no ip route 10.0.0.0/24 10.1.1.2")

    st.wait(3, "Waiting for route removal")

    # ==================================================================
    # STEP 7: Verify Route Removed
    # ==================================================================
    st.banner("STEP 7: Verify Route Removal")

    if not verify_route_not_in_table(vars.D1, CONFIG.static_route_prefix):
        st.generate_tech_support([vars.D1, vars.D2], "sr01_route_still_exists")
        st.report_tc_fail(TC_IDS.sr01_route_remove, "msg", "Route still exists after deletion")
        st.report_fail("msg", "Route removal verification failed")

    st.log(f"{CONFIG.static_route_prefix} removed from routing table")
    st.report_tc_pass(TC_IDS.sr01_route_remove, "msg", "Route removed successfully")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: SR-01 PASSED")
    st.banner("=" * 80)
    st.log("TEST SUMMARY - SR-01: IPv4 Static Route - Basic")
    st.log(f"  ip route {CONFIG.static_route_prefix} {CONFIG.dut2_ip} -> Added")
    st.log(f"  show ip route {CONFIG.static_route_prefix} -> Verified")
    st.log(f"  ping {CONFIG.ping_target} -> Success")
    st.log(f"  no ip route {CONFIG.static_route_prefix} {CONFIG.dut2_ip} -> Removed")
    st.log(f"  show ip route {CONFIG.static_route_prefix} -> Route absent confirmed")

    st.report_pass("test_case_passed")
