"""
STATIC ROUTE TEST - OC-SR-11: IPv4 Static Route - Blackhole Routes

Test Case ID: OC-SR-11
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/Static_Route/test_oc_static_route_02_ipv4_blackhole.py \
    --logs-path ./logs/oc_sr11_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv4 blackhole static routes configuration and verification.
  Uses direct sonic-cli (klish) commands matching manual validation.
  Blackhole routes drop packets destined to specified prefixes.

Manual sonic-cli commands validated:
  DUT1:
    ip route 172.16.10.0/24 blackhole
    ip route 172.16.20.0/24 10.1.1.2
    show ip route static -> Verify "Unreachable (blackhole)"

  DUT2:
    ip route 172.16.10.0/24 10.1.1.1
    ip route 172.16.20.0/24 blackhole
    ip route 172.16.30.0/24 10.2.1.2
    show ip route static -> Verify "Unreachable (blackhole)"

Pre-requisites:
  - Topology: 2-node (D1-D2) | Supported: HW and Virtual
  - OC-build with Klish CLI support
  - Minimum 1 port between DUT1-DUT2
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration - matches manual testcase exactly
CONFIG = SpyTestDict({
    # Interface configuration
    "dut1_interface": "Ethernet 0",
    "dut1_ip": "10.1.1.1/24",
    "dut2_interface": "Ethernet 0",
    "dut2_ip": "10.1.1.2/24",

    # DUT1 Routes
    "dut1_blackhole_prefix": "172.16.10.0/24",
    "dut1_normal_prefix": "172.16.20.0/24",
    "dut1_normal_nexthop": "10.1.1.2",

    # DUT2 Routes
    "dut2_normal_prefix1": "172.16.10.0/24",
    "dut2_normal_nexthop1": "10.1.1.1",
    "dut2_blackhole_prefix": "172.16.20.0/24",
    "dut2_normal_prefix2": "172.16.30.0/24",
    "dut2_normal_nexthop2": "10.2.1.2",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr11_interface_config": "TC-OC-SR-11-001",
    "oc_sr11_blackhole_add": "TC-OC-SR-11-002",
    "oc_sr11_blackhole_verify": "TC-OC-SR-11-003",
    "oc_sr11_blackhole_remove": "TC-OC-SR-11-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_blackhole_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-11 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Ensure 2-DUT topology
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")

    # Pre-configuration
    static_route_pre_config()

    yield

    # Cleanup - always executes even if test fails
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-11 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing configuration on DUT1 and DUT2")

    # Clear DUT1 interface
    try:
        st.config(vars.D1, [
            f"interface {CONFIG.dut1_interface}",
            "no ip address",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Clear DUT2 interface
    try:
        st.config(vars.D2, [
            f"interface {CONFIG.dut2_interface}",
            "no ip address",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT1 routes if they exist
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_blackhole_prefix} blackhole",
            f"no ip route {CONFIG.dut1_normal_prefix} {CONFIG.dut1_normal_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 routes if they exist
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_normal_prefix1} {CONFIG.dut2_normal_nexthop1}",
            f"no ip route {CONFIG.dut2_blackhole_prefix} blackhole",
            f"no ip route {CONFIG.dut2_normal_prefix2} {CONFIG.dut2_normal_nexthop2}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Explicitly exit Klish CLI mode back to normal user mode on all DUTs
    for dut in [vars.D1, vars.D2]:
        try:
            # First exit from config mode to normal Klish prompt
            st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)
        except Exception:
            pass
        try:
            # Then exit from Klish CLI to Linux shell
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.wait(3, "Waiting for pre-config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Cleanup: Remove static routes and IP configuration."""
    st.log("Cleanup: Removing static routes and IP configuration")

    # Remove DUT1 routes
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_blackhole_prefix} blackhole",
            f"no ip route {CONFIG.dut1_normal_prefix} {CONFIG.dut1_normal_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 route cleanup warning: {str(e)}")

    # Remove DUT2 routes
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_normal_prefix1} {CONFIG.dut2_normal_nexthop1}",
            f"no ip route {CONFIG.dut2_blackhole_prefix} blackhole",
            f"no ip route {CONFIG.dut2_normal_prefix2} {CONFIG.dut2_normal_nexthop2}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT2 route cleanup warning: {str(e)}")

    # Clear IP addresses - DUT1
    try:
        st.config(vars.D1, [
            f"interface {CONFIG.dut1_interface}",
            "no ip address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 interface cleanup warning: {str(e)}")

    # Clear IP addresses - DUT2
    try:
        st.config(vars.D2, [
            f"interface {CONFIG.dut2_interface}",
            "no ip address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT2 interface cleanup warning: {str(e)}")

    # Explicitly exit Klish CLI mode back to normal user mode on all DUTs
    for dut in [vars.D1, vars.D2]:
        try:
            # First exit from config mode to normal Klish prompt
            st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)
        except Exception:
            pass
        try:
            # Then exit from Klish CLI to Linux shell
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.log("Cleanup completed")


def configure_interface_ip(dut, interface, ip_with_prefix):
    """Configure IP on interface - sonic-cli: interface X -> ip address Y/Z -> no shutdown."""
    st.log(f"Configuring {ip_with_prefix} on {dut} {interface}")
    try:
        st.config(dut, [
            f"interface {interface}",
            f"ip address {ip_with_prefix}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IP {ip_with_prefix} configured on {interface}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to configure IP on {interface}: {str(e)}")
        return False


def add_blackhole_route(dut, prefix):
    """Add blackhole route - sonic-cli: ip route <prefix> blackhole."""
    st.log(f"Adding blackhole route: ip route {prefix} blackhole")
    try:
        st.config(dut, [
            f"ip route {prefix} blackhole"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Blackhole route added: {prefix}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add blackhole route: {str(e)}")
        return False


def add_static_route(dut, prefix, nexthop):
    """Add static route - sonic-cli: ip route <prefix> <nexthop>."""
    st.log(f"Adding static route: ip route {prefix} {nexthop}")
    try:
        st.config(dut, [
            f"ip route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Static route added: {prefix} via {nexthop}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add static route: {str(e)}")
        return False


def delete_blackhole_route(dut, prefix):
    """Delete blackhole route - sonic-cli: no ip route <prefix> blackhole."""
    st.log(f"Removing blackhole route: no ip route {prefix} blackhole")
    try:
        st.config(dut, [
            f"no ip route {prefix} blackhole"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Blackhole route removed: {prefix}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to remove blackhole route: {str(e)}")
        return False


def delete_static_route(dut, prefix, nexthop):
    """Delete static route - sonic-cli: no ip route <prefix> <nexthop>."""
    st.log(f"Removing static route: no ip route {prefix} {nexthop}")
    try:
        st.config(dut, [
            f"no ip route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Static route removed: {prefix} via {nexthop}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to remove static route: {str(e)}")
        return False


def verify_blackhole_route(dut, prefix):
    """Verify blackhole route shows 'Unreachable (blackhole)' in routing table."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        # Exit Klish CLI to Linux shell before show command
        try:
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Blackhole route lookup '{prefix}': {output_str[:400]}")

        # Check for blackhole markers
        if "blackhole" in output_str.lower() or "unreachable" in output_str.lower():
            st.log(f"✓ Blackhole route verified: {prefix}")
            return True
        else:
            st.error(f"✗ Blackhole route not found or incorrect: {prefix}")
            return False
    except Exception as e:
        st.error(f"Blackhole route verify failed: {str(e)}")
        return False


def verify_static_route(dut, prefix, nexthop):
    """Verify static route exists in routing table."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        # Exit Klish CLI to Linux shell before show command
        try:
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup '{prefix}': {output_str[:300]}")

        # Check if route exists with correct nexthop
        if "S" in output_str and nexthop in output_str:
            st.log(f"✓ Static route verified: {prefix} via {nexthop}")
            return True
        else:
            st.error(f"✗ Static route not found: {prefix} via {nexthop}")
            return False
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        return False


def verify_route_not_in_table(dut, prefix):
    """Verify route is absent from routing table."""
    try:
        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup after removal '{prefix}': {output_str[:300]}")

        # Route should not have 'S' marker (static route)
        return "S" not in output_str or prefix not in output_str
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        return False


@pytest.mark.static_route
@pytest.mark.blackhole
@pytest.mark.community
@pytest.mark.community_pass
def test_oc_sr11_ipv4_blackhole_routes():
    """
    Test Case OC-SR-11: IPv4 Static Route - Blackhole Routes

    Validates sonic-cli blackhole route commands:
      DUT1: ip route 172.16.10.0/24 blackhole
            ip route 172.16.20.0/24 10.1.1.2
      DUT2: ip route 172.16.10.0/24 10.1.1.1
            ip route 172.16.20.0/24 blackhole
            ip route 172.16.30.0/24 10.2.1.2
      Verify blackhole routes show "Unreachable (blackhole)"
      Remove routes and verify deletion
    """
    st.banner("=" * 80)
    st.banner("TEST OC-SR-11: IPv4 STATIC ROUTE - BLACKHOLE ROUTES")
    st.banner("=" * 80)

    result_flag = True  # Track overall test result

    try:
        # ==================================================================
        # STEP 1: Configure IP Addresses on Interfaces
        # ==================================================================
        st.banner("STEP 1: Configure IP Addresses on DUT1 and DUT2")

        if not configure_interface_ip(vars.D1, CONFIG.dut1_interface, CONFIG.dut1_ip):
            st.report_tc_fail(TC_IDS.oc_sr11_interface_config, "msg", "Failed to configure DUT1 interface")
            result_flag = False

        if not configure_interface_ip(vars.D2, CONFIG.dut2_interface, CONFIG.dut2_ip):
            st.report_tc_fail(TC_IDS.oc_sr11_interface_config, "msg", "Failed to configure DUT2 interface")
            result_flag = False

        st.wait(3, "Waiting for interfaces to stabilize")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr11_interface_config, "msg", "Interface configurations successful")
        else:
            st.report_fail("msg", "Interface configuration failed - check logs")

        # ==================================================================
        # STEP 2: Configure Blackhole Route on DUT1
        # ==================================================================
        st.banner("STEP 2: Configure Blackhole Route on DUT1")
        st.log(f"DUT1: ip route {CONFIG.dut1_blackhole_prefix} blackhole")

        if not add_blackhole_route(vars.D1, CONFIG.dut1_blackhole_prefix):
            st.report_tc_fail(TC_IDS.oc_sr11_blackhole_add, "msg", "Failed to add DUT1 blackhole route")
            result_flag = False

        # Add normal route on DUT1
        st.log(f"DUT1: ip route {CONFIG.dut1_normal_prefix} {CONFIG.dut1_normal_nexthop}")
        if not add_static_route(vars.D1, CONFIG.dut1_normal_prefix, CONFIG.dut1_normal_nexthop):
            st.report_tc_fail(TC_IDS.oc_sr11_blackhole_add, "msg", "Failed to add DUT1 normal route")
            result_flag = False

        st.wait(3, "Waiting for DUT1 routes to be programmed")

        # ==================================================================
        # STEP 3: Configure Routes on DUT2
        # ==================================================================
        st.banner("STEP 3: Configure Routes on DUT2")
        st.log(f"DUT2: ip route {CONFIG.dut2_normal_prefix1} {CONFIG.dut2_normal_nexthop1}")

        if not add_static_route(vars.D2, CONFIG.dut2_normal_prefix1, CONFIG.dut2_normal_nexthop1):
            st.report_tc_fail(TC_IDS.oc_sr11_blackhole_add, "msg", "Failed to add DUT2 first route")
            result_flag = False

        st.log(f"DUT2: ip route {CONFIG.dut2_blackhole_prefix} blackhole")
        if not add_blackhole_route(vars.D2, CONFIG.dut2_blackhole_prefix):
            st.report_tc_fail(TC_IDS.oc_sr11_blackhole_add, "msg", "Failed to add DUT2 blackhole route")
            result_flag = False

        st.log(f"DUT2: ip route {CONFIG.dut2_normal_prefix2} {CONFIG.dut2_normal_nexthop2}")
        if not add_static_route(vars.D2, CONFIG.dut2_normal_prefix2, CONFIG.dut2_normal_nexthop2):
            st.report_tc_fail(TC_IDS.oc_sr11_blackhole_add, "msg", "Failed to add DUT2 third route")
            result_flag = False

        st.wait(3, "Waiting for DUT2 routes to be programmed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr11_blackhole_add, "msg", "All routes added successfully")
        else:
            st.report_fail("msg", "Route addition failed - check logs")

        # ==================================================================
        # STEP 4: Verify Blackhole Routes in Routing Tables
        # ==================================================================
        st.banner("STEP 4: Verify Blackhole Routes in Routing Tables")

        # Verify DUT1 blackhole route
        st.log(f"Verifying DUT1 blackhole route: {CONFIG.dut1_blackhole_prefix}")
        if not verify_blackhole_route(vars.D1, CONFIG.dut1_blackhole_prefix):
            st.error(f"DUT1: Blackhole route {CONFIG.dut1_blackhole_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Blackhole route {CONFIG.dut1_blackhole_prefix} shows 'Unreachable (blackhole)'")

        # Verify DUT1 normal route
        st.log(f"Verifying DUT1 normal route: {CONFIG.dut1_normal_prefix}")
        if not verify_static_route(vars.D1, CONFIG.dut1_normal_prefix, CONFIG.dut1_normal_nexthop):
            st.error(f"DUT1: Normal route {CONFIG.dut1_normal_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Normal route {CONFIG.dut1_normal_prefix} verified")

        # Verify DUT2 blackhole route
        st.log(f"Verifying DUT2 blackhole route: {CONFIG.dut2_blackhole_prefix}")
        if not verify_blackhole_route(vars.D2, CONFIG.dut2_blackhole_prefix):
            st.error(f"DUT2: Blackhole route {CONFIG.dut2_blackhole_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Blackhole route {CONFIG.dut2_blackhole_prefix} shows 'Unreachable (blackhole)'")

        # Verify DUT2 normal routes
        st.log(f"Verifying DUT2 normal routes")
        if not verify_static_route(vars.D2, CONFIG.dut2_normal_prefix1, CONFIG.dut2_normal_nexthop1):
            st.error(f"DUT2: Route {CONFIG.dut2_normal_prefix1} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_normal_prefix1} verified")

        if not verify_static_route(vars.D2, CONFIG.dut2_normal_prefix2, CONFIG.dut2_normal_nexthop2):
            st.error(f"DUT2: Route {CONFIG.dut2_normal_prefix2} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_normal_prefix2} verified")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr11_blackhole_verify, "msg", "All blackhole routes verified successfully")
        else:
            st.report_tc_fail(TC_IDS.oc_sr11_blackhole_verify, "msg", "Blackhole route verification failed")
            st.generate_tech_support([vars.D1, vars.D2], "oc_sr11_blackhole_verify_failed")

        # ==================================================================
        # STEP 5: Remove Blackhole and Static Routes
        # ==================================================================
        st.banner("STEP 5: Remove Blackhole and Static Routes")

        # Remove DUT1 routes
        st.log("Removing DUT1 routes...")
        if not delete_blackhole_route(vars.D1, CONFIG.dut1_blackhole_prefix):
            st.error(f"Failed to remove DUT1 blackhole route")
            result_flag = False

        if not delete_static_route(vars.D1, CONFIG.dut1_normal_prefix, CONFIG.dut1_normal_nexthop):
            st.error(f"Failed to remove DUT1 normal route")
            result_flag = False

        # Remove DUT2 routes
        st.log("Removing DUT2 routes...")
        if not delete_static_route(vars.D2, CONFIG.dut2_normal_prefix1, CONFIG.dut2_normal_nexthop1):
            st.error(f"Failed to remove DUT2 first route")
            result_flag = False

        if not delete_blackhole_route(vars.D2, CONFIG.dut2_blackhole_prefix):
            st.error(f"Failed to remove DUT2 blackhole route")
            result_flag = False

        if not delete_static_route(vars.D2, CONFIG.dut2_normal_prefix2, CONFIG.dut2_normal_nexthop2):
            st.error(f"Failed to remove DUT2 third route")
            result_flag = False

        st.wait(3, "Waiting for route removal")

        # ==================================================================
        # STEP 6: Verify Routes Removed
        # ==================================================================
        st.banner("STEP 6: Verify Routes Removed from Routing Tables")

        # Verify DUT1 routes removed
        if not verify_route_not_in_table(vars.D1, CONFIG.dut1_blackhole_prefix):
            st.error(f"DUT1: Blackhole route {CONFIG.dut1_blackhole_prefix} still exists")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Blackhole route {CONFIG.dut1_blackhole_prefix} removed")

        if not verify_route_not_in_table(vars.D1, CONFIG.dut1_normal_prefix):
            st.error(f"DUT1: Normal route {CONFIG.dut1_normal_prefix} still exists")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Normal route {CONFIG.dut1_normal_prefix} removed")

        # Verify DUT2 routes removed
        if not verify_route_not_in_table(vars.D2, CONFIG.dut2_blackhole_prefix):
            st.error(f"DUT2: Blackhole route {CONFIG.dut2_blackhole_prefix} still exists")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Blackhole route {CONFIG.dut2_blackhole_prefix} removed")

        if not verify_route_not_in_table(vars.D2, CONFIG.dut2_normal_prefix1):
            st.error(f"DUT2: Route {CONFIG.dut2_normal_prefix1} still exists")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_normal_prefix1} removed")

        if not verify_route_not_in_table(vars.D2, CONFIG.dut2_normal_prefix2):
            st.error(f"DUT2: Route {CONFIG.dut2_normal_prefix2} still exists")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_normal_prefix2} removed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr11_blackhole_remove, "msg", "All routes removed successfully")
        else:
            st.report_tc_fail(TC_IDS.oc_sr11_blackhole_remove, "msg", "Route removal verification failed")

    except Exception as e:
        st.error(f"Test execution error: {str(e)}")
        st.generate_tech_support([vars.D1, vars.D2], "oc_sr11_exception")
        result_flag = False

    finally:
        # Ensure cleanup runs even if test fails
        st.log("Ensuring cleanup executes...")

    # ==================================================================
    # TEST RESULT
    # ==================================================================
    st.banner("=" * 80)
    if result_flag:
        st.banner("TEST RESULT: OC-SR-11 PASSED")
        st.banner("=" * 80)
        st.log("TEST SUMMARY - OC-SR-11: IPv4 Static Route - Blackhole Routes")
        st.log("  ✓ Interface IP addresses configured")
        st.log("  ✓ Blackhole routes added successfully")
        st.log("  ✓ Blackhole routes verified with 'Unreachable (blackhole)'")
        st.log("  ✓ Normal routes added alongside blackhole routes")
        st.log("  ✓ All routes removed successfully")
        st.log("  ✓ Route removal verified")
        st.report_pass("test_case_passed")
    else:
        st.banner("TEST RESULT: OC-SR-11 FAILED")
        st.banner("=" * 80)
        st.log("TEST SUMMARY - OC-SR-11: IPv4 Static Route - Blackhole Routes")
        st.log("  ✗ Test failed - check logs for details")
        st.report_fail("test_case_failed")
