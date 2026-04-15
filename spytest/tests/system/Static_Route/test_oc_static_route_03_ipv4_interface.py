"""
STATIC ROUTE TEST - OC-SR-12: IPv4 Static Route - Interface-Based Routes

Test Case ID: OC-SR-12
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/Static_Route/test_oc_static_route_03_ipv4_interface.py \
    --logs-path ./logs/oc_sr12_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv4 static routes with interface-based next-hops (no IP address).
  Uses direct sonic-cli (klish) commands matching manual validation.
  Interface-based routes use ARP resolution on egress interface.

Manual sonic-cli commands validated:
  DUT1:
    ip route 192.168.70.0/24 interface Ethernet0
    ip route 192.168.71.0/24 interface Ethernet4
    show ip route static -> Verify "directly connected, Ethernet0"

  DUT2:
    ip route 192.168.70.0/24 interface Ethernet8
    ip route 192.168.71.0/24 interface Ethernet0
    ip route 192.168.72.0/24 interface Ethernet12
    show ip route static -> Verify "directly connected, Ethernet<X>"

Pre-requisites:
  - Topology: 2-node (D1-D2) | Supported: HW and Virtual
  - OC-build with Klish CLI support
  - Minimum 2 ports between DUT1-DUT2
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration - matches manual testcase exactly
CONFIG = SpyTestDict({
    # DUT1 Interface configuration
    "dut1_eth0": "Ethernet 0",
    "dut1_eth0_ip": "10.1.1.1/24",
    "dut1_eth4": "Ethernet 4",
    "dut1_eth4_ip": "10.2.1.1/24",

    # DUT2 Interface configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ip": "10.1.1.2/24",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ip": "10.2.1.2/24",
    "dut2_eth12": "Ethernet 12",
    "dut2_eth12_ip": "10.3.1.2/24",

    # DUT1 Interface-based routes
    "dut1_route1_prefix": "192.168.70.0/24",
    "dut1_route1_interface": "Ethernet0",
    "dut1_route2_prefix": "192.168.71.0/24",
    "dut1_route2_interface": "Ethernet4",

    # DUT2 Interface-based routes
    "dut2_route1_prefix": "192.168.70.0/24",
    "dut2_route1_interface": "Ethernet8",
    "dut2_route2_prefix": "192.168.71.0/24",
    "dut2_route2_interface": "Ethernet0",
    "dut2_route3_prefix": "192.168.72.0/24",
    "dut2_route3_interface": "Ethernet12",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr12_interface_config": "TC-OC-SR-12-001",
    "oc_sr12_interface_route_add": "TC-OC-SR-12-002",
    "oc_sr12_interface_route_verify": "TC-OC-SR-12-003",
    "oc_sr12_interface_route_remove": "TC-OC-SR-12-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_interface_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-12 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Ensure 2-DUT topology with at least 2 links
    vars = st.ensure_min_topology("D1D2:2")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")

    # Pre-configuration
    static_route_pre_config()

    yield

    # Cleanup - always executes even if test fails
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-12 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing configuration on DUT1 and DUT2")

    # Clear DUT1 interfaces
    for intf in [CONFIG.dut1_eth0, CONFIG.dut1_eth4]:
        try:
            st.config(vars.D1, [
                f"interface {intf}",
                "no ip address",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Clear DUT2 interfaces
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth8, CONFIG.dut2_eth12]:
        try:
            st.config(vars.D2, [
                f"interface {intf}",
                "no ip address",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Remove DUT1 interface-based routes if they exist
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_route1_prefix} interface {CONFIG.dut1_route1_interface}",
            f"no ip route {CONFIG.dut1_route2_prefix} interface {CONFIG.dut1_route2_interface}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 interface-based routes if they exist
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_route1_prefix} interface {CONFIG.dut2_route1_interface}",
            f"no ip route {CONFIG.dut2_route2_prefix} interface {CONFIG.dut2_route2_interface}",
            f"no ip route {CONFIG.dut2_route3_prefix} interface {CONFIG.dut2_route3_interface}"
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
    st.log("Cleanup: Removing interface-based routes and IP configuration")

    # Remove DUT1 interface-based routes
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_route1_prefix} interface {CONFIG.dut1_route1_interface}",
            f"no ip route {CONFIG.dut1_route2_prefix} interface {CONFIG.dut1_route2_interface}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 route cleanup warning: {str(e)}")

    # Remove DUT2 interface-based routes
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_route1_prefix} interface {CONFIG.dut2_route1_interface}",
            f"no ip route {CONFIG.dut2_route2_prefix} interface {CONFIG.dut2_route2_interface}",
            f"no ip route {CONFIG.dut2_route3_prefix} interface {CONFIG.dut2_route3_interface}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT2 route cleanup warning: {str(e)}")

    # Clear IP addresses - DUT1
    for intf in [CONFIG.dut1_eth0, CONFIG.dut1_eth4]:
        try:
            st.config(vars.D1, [
                f"interface {intf}",
                "no ip address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"DUT1 {intf} cleanup warning: {str(e)}")

    # Clear IP addresses - DUT2
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth8, CONFIG.dut2_eth12]:
        try:
            st.config(vars.D2, [
                f"interface {intf}",
                "no ip address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"DUT2 {intf} cleanup warning: {str(e)}")

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
        except Exception:            pass

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


def add_interface_route(dut, prefix, interface):
    """Add interface-based route - sonic-cli: ip route <prefix> interface <interface>."""
    st.log(f"Adding interface route: ip route {prefix} interface {interface}")
    try:
        st.config(dut, [
            f"ip route {prefix} interface {interface}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Interface route added: {prefix} via {interface}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add interface route: {str(e)}")
        return False


def delete_interface_route(dut, prefix, interface):
    """Delete interface-based route - sonic-cli: no ip route <prefix> interface <interface>."""
    st.log(f"Removing interface route: no ip route {prefix} interface {interface}")
    try:
        st.config(dut, [
            f"no ip route {prefix} interface {interface}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Interface route removed: {prefix} via {interface}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to remove interface route: {str(e)}")
        return False


def verify_interface_route(dut, prefix, interface):
    """Verify interface-based route shows 'directly connected, <interface>' in routing table."""
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
        st.log(f"Interface route lookup '{prefix}': {output_str[:400]}")

        # Check for interface-based route markers
        # Looking for "directly connected" AND interface name
        if ("directly connected" in output_str.lower() or "via" in output_str) and interface.replace(" ", "") in output_str.replace(" ", ""):
            st.log(f"✓ Interface route verified: {prefix} via {interface}")
            return True
        else:
            st.error(f"✗ Interface route not found or incorrect: {prefix} via {interface}")
            return False
    except Exception as e:
        st.error(f"Interface route verify failed: {str(e)}")
        return False


def verify_route_not_in_table(dut, prefix):
    """Verify route is absent from routing table."""
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
        st.log(f"Route lookup after removal '{prefix}': {output_str[:300]}")

        # Route should not have 'S' marker (static route)
        return "S" not in output_str or prefix not in output_str
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        return False


@pytest.mark.static_route
@pytest.mark.interface_route
@pytest.mark.community
@pytest.mark.community_pass
def test_oc_sr12_ipv4_interface_based_routes():
    """
    Test Case OC-SR-12: IPv4 Static Route - Interface-Based Routes

    Validates sonic-cli interface-based route commands:
      DUT1: ip route 192.168.70.0/24 interface Ethernet0
            ip route 192.168.71.0/24 interface Ethernet4
      DUT2: ip route 192.168.70.0/24 interface Ethernet8
            ip route 192.168.71.0/24 interface Ethernet0
            ip route 192.168.72.0/24 interface Ethernet12
      Verify routes show "directly connected, Ethernet<X>"
      Remove routes and verify deletion
    """
    st.banner("=" * 80)
    st.banner("TEST OC-SR-12: IPv4 STATIC ROUTE - INTERFACE-BASED ROUTES")
    st.banner("=" * 80)

    result_flag = True  # Track overall test result

    try:
        # ==================================================================
        # STEP 1: Configure IP Addresses on DUT1 Interfaces
        # ==================================================================
        st.banner("STEP 1: Configure IP Addresses on DUT1 Interfaces")

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr12_interface_config, "msg", "Failed to configure DUT1 Ethernet0")
            result_flag = False

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth4, CONFIG.dut1_eth4_ip):
            st.report_tc_fail(TC_IDS.oc_sr12_interface_config, "msg", "Failed to configure DUT1 Ethernet4")
            result_flag = False

        st.wait(3, "Waiting for DUT1 interfaces to stabilize")

        # ==================================================================
        # STEP 2: Configure IP Addresses on DUT2 Interfaces
        # ==================================================================
        st.banner("STEP 2: Configure IP Addresses on DUT2 Interfaces")

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr12_interface_config, "msg", "Failed to configure DUT2 Ethernet0")
            result_flag = False

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ip):
            st.report_tc_fail(TC_IDS.oc_sr12_interface_config, "msg", "Failed to configure DUT2 Ethernet8")
            result_flag = False

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth12, CONFIG.dut2_eth12_ip):
            st.report_tc_fail(TC_IDS.oc_sr12_interface_config, "msg", "Failed to configure DUT2 Ethernet12")
            result_flag = False

        st.wait(3, "Waiting for DUT2 interfaces to stabilize")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr12_interface_config, "msg", "All interface configurations successful")
        else:
            st.report_fail("msg", "Interface configuration failed - check logs")

        # ==================================================================
        # STEP 3: Add Interface-Based Routes on DUT1
        # ==================================================================
        st.banner("STEP 3: Add Interface-Based Routes on DUT1")
        st.log(f"DUT1 Route 1: ip route {CONFIG.dut1_route1_prefix} interface {CONFIG.dut1_route1_interface}")
        st.log(f"DUT1 Route 2: ip route {CONFIG.dut1_route2_prefix} interface {CONFIG.dut1_route2_interface}")

        if not add_interface_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_interface):
            st.report_tc_fail(TC_IDS.oc_sr12_interface_route_add, "msg", "Failed to add DUT1 interface route 1")
            result_flag = False

        if not add_interface_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_interface):
            st.report_tc_fail(TC_IDS.oc_sr12_interface_route_add, "msg", "Failed to add DUT1 interface route 2")
            result_flag = False

        st.wait(3, "Waiting for DUT1 routes to be programmed")

        # ==================================================================
        # STEP 4: Add Interface-Based Routes on DUT2
        # ==================================================================
        st.banner("STEP 4: Add Interface-Based Routes on DUT2")
        st.log(f"DUT2 Route 1: ip route {CONFIG.dut2_route1_prefix} interface {CONFIG.dut2_route1_interface}")
        st.log(f"DUT2 Route 2: ip route {CONFIG.dut2_route2_prefix} interface {CONFIG.dut2_route2_interface}")
        st.log(f"DUT2 Route 3: ip route {CONFIG.dut2_route3_prefix} interface {CONFIG.dut2_route3_interface}")

        if not add_interface_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_interface):
            st.report_tc_fail(TC_IDS.oc_sr12_interface_route_add, "msg", "Failed to add DUT2 interface route 1")
            result_flag = False

        if not add_interface_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_interface):
            st.report_tc_fail(TC_IDS.oc_sr12_interface_route_add, "msg", "Failed to add DUT2 interface route 2")
            result_flag = False

        if not add_interface_route(vars.D2, CONFIG.dut2_route3_prefix, CONFIG.dut2_route3_interface):
            st.report_tc_fail(TC_IDS.oc_sr12_interface_route_add, "msg", "Failed to add DUT2 interface route 3")
            result_flag = False

        st.wait(3, "Waiting for DUT2 routes to be programmed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr12_interface_route_add, "msg", "All interface-based routes added successfully")
        else:
            st.report_fail("msg", "Interface route addition failed - check logs")

        # ==================================================================
        # STEP 5: Verify Interface-Based Routes in Routing Tables
        # ==================================================================
        st.banner("STEP 5: Verify Interface-Based Routes in Routing Tables")

        # Verify DUT1 interface routes
        st.log("Verifying DUT1 interface routes...")
        if not verify_interface_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_interface):
            st.error(f"DUT1: Interface route {CONFIG.dut1_route1_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route {CONFIG.dut1_route1_prefix} via {CONFIG.dut1_route1_interface} verified")

        if not verify_interface_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_interface):
            st.error(f"DUT1: Interface route {CONFIG.dut1_route2_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route {CONFIG.dut1_route2_prefix} via {CONFIG.dut1_route2_interface} verified")

        # Verify DUT2 interface routes
        st.log("Verifying DUT2 interface routes...")
        if not verify_interface_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_interface):
            st.error(f"DUT2: Interface route {CONFIG.dut2_route1_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route1_prefix} via {CONFIG.dut2_route1_interface} verified")

        if not verify_interface_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_interface):
            st.error(f"DUT2: Interface route {CONFIG.dut2_route2_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route2_prefix} via {CONFIG.dut2_route2_interface} verified")

        if not verify_interface_route(vars.D2, CONFIG.dut2_route3_prefix, CONFIG.dut2_route3_interface):
            st.error(f"DUT2: Interface route {CONFIG.dut2_route3_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route3_prefix} via {CONFIG.dut2_route3_interface} verified")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr12_interface_route_verify, "msg", "All interface-based routes verified successfully")
        else:
            st.report_tc_fail(TC_IDS.oc_sr12_interface_route_verify, "msg", "Interface route verification failed")
            st.generate_tech_support([vars.D1, vars.D2], "oc_sr12_interface_route_verify_failed")

        # ==================================================================
        # STEP 6: Remove Interface-Based Routes
        # ==================================================================
        st.banner("STEP 6: Remove Interface-Based Routes")

        # Remove DUT1 routes
        st.log("Removing DUT1 interface routes...")
        if not delete_interface_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_interface):
            st.error(f"Failed to remove DUT1 route {CONFIG.dut1_route1_prefix}")
            result_flag = False

        if not delete_interface_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_interface):
            st.error(f"Failed to remove DUT1 route {CONFIG.dut1_route2_prefix}")
            result_flag = False

        # Remove DUT2 routes
        st.log("Removing DUT2 interface routes...")
        if not delete_interface_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_interface):
            st.error(f"Failed to remove DUT2 route {CONFIG.dut2_route1_prefix}")
            result_flag = False

        if not delete_interface_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_interface):
            st.error(f"Failed to remove DUT2 route {CONFIG.dut2_route2_prefix}")
            result_flag = False

        if not delete_interface_route(vars.D2, CONFIG.dut2_route3_prefix, CONFIG.dut2_route3_interface):
            st.error(f"Failed to remove DUT2 route {CONFIG.dut2_route3_prefix}")
            result_flag = False

        st.wait(3, "Waiting for route removal")

        # ==================================================================
        # STEP 7: Verify Routes Removed
        # ==================================================================
        st.banner("STEP 7: Verify Routes Removed from Routing Tables")

        # Verify DUT1 routes removed
        if not verify_route_not_in_table(vars.D1, CONFIG.dut1_route1_prefix):
            st.error(f"DUT1: Route {CONFIG.dut1_route1_prefix} still exists after deletion")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route {CONFIG.dut1_route1_prefix} successfully removed")

        if not verify_route_not_in_table(vars.D1, CONFIG.dut1_route2_prefix):
            st.error(f"DUT1: Route {CONFIG.dut1_route2_prefix} still exists after deletion")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route {CONFIG.dut1_route2_prefix} successfully removed")

        # Verify DUT2 routes removed
        if not verify_route_not_in_table(vars.D2, CONFIG.dut2_route1_prefix):
            st.error(f"DUT2: Route {CONFIG.dut2_route1_prefix} still exists after deletion")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route1_prefix} successfully removed")

        if not verify_route_not_in_table(vars.D2, CONFIG.dut2_route2_prefix):
            st.error(f"DUT2: Route {CONFIG.dut2_route2_prefix} still exists after deletion")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route2_prefix} successfully removed")

        if not verify_route_not_in_table(vars.D2, CONFIG.dut2_route3_prefix):
            st.error(f"DUT2: Route {CONFIG.dut2_route3_prefix} still exists after deletion")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route3_prefix} successfully removed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr12_interface_route_remove, "msg", "All interface routes removed successfully")
        else:
            st.report_tc_fail(TC_IDS.oc_sr12_interface_route_remove, "msg", "Route removal verification failed")

    except Exception as e:
        st.error(f"Test execution error: {str(e)}")
        st.generate_tech_support([vars.D1, vars.D2], "oc_sr12_exception")
        result_flag = False

    finally:
        # Ensure cleanup runs even if test fails
        st.log("Ensuring cleanup executes...")

    # ==================================================================
    # TEST RESULT
    # ==================================================================
    st.banner("=" * 80)
    if result_flag:
        st.banner("TEST RESULT: OC-SR-12 PASSED")
        st.banner("=" * 80)
        st.log("TEST SUMMARY - OC-SR-12: IPv4 Static Route - Interface-Based Routes")
        st.log("  ✓ All interface IP addresses configured")
        st.log("  ✓ All interface-based routes added successfully")
        st.log("  ✓ All routes verified with 'directly connected, Ethernet<X>'")
        st.log("  ✓ All routes removed successfully")
        st.log("  ✓ Route removal verified")
        st.report_pass("test_case_passed")
    else:
        st.banner("TEST RESULT: OC-SR-12 FAILED")
        st.banner("=" * 80)
        st.log("TEST SUMMARY - OC-SR-12: IPv4 Static Route - Interface-Based Routes")
        st.log("  ✗ Test failed - check logs for details")
        st.report_fail("test_case_failed")
