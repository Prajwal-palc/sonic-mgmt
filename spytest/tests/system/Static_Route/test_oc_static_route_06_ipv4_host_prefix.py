"""
STATIC ROUTE TEST - OC-SR-16: IPv4 Static Route - Host Routes and Various Prefix Lengths

Test Case ID: OC-SR-16
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_static_2vs.yaml \
    tests/system/Static_Route/test_oc_static_route_06_ipv4_host_prefix.py \
    --logs-path ./logs/oc_sr16_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv4 static routes with various prefix lengths including:
  - Host routes (/32) - Single IP address
  - Supernets (/16, /12, /8) - Large address blocks
  - Standard subnets (/24) - Common network masks

  Key Features:
  - /32 prefix (Host route) - 192.168.1.1/32
  - /16 prefix (Class B supernet) - 192.168.0.0/16
  - /12 prefix (Large supernet) - 172.16.0.0/12
  - /8 prefix (Class A network) - 10.0.0.0/8

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0 -> ip address 10.1.1.1/24 -> no shutdown
    ip route 192.168.1.1/32 10.1.1.2
    ip route 192.168.0.0/16 10.1.1.2
    ip route 172.16.0.0/12 10.1.1.2
    ip route 10.0.0.0/8 10.1.1.2

  DUT2:
    interface Ethernet 0 -> ip address 10.1.1.2/24 -> no shutdown
    interface Ethernet 8 -> ip address 10.2.1.1/24 -> no shutdown
    ip route 192.168.1.1/32 10.2.1.2
    ip route 192.168.0.0/16 10.2.1.2
    ip route 172.16.0.0/12 10.2.1.2
    ip route 10.0.0.0/8 10.2.1.2

Pre-requisites:
  - Topology: 2-node (D1-D2) | Supported: HW and Virtual
  - OC-build with Klish CLI support
  - Minimum 1 port between DUTs
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration - matches manual testcase exactly
CONFIG = SpyTestDict({
    # DUT1 Configuration
    "dut1_eth0": "Ethernet 0",
    "dut1_eth0_ip": "10.1.1.1/24",

    # DUT1 Routes with various prefix lengths
    "dut1_route_host": {
        "prefix": "192.168.1.1/32",
        "nexthop": "10.1.1.2",
        "description": "Host route (/32)"
    },
    "dut1_route_16": {
        "prefix": "192.168.0.0/16",
        "nexthop": "10.1.1.2",
        "description": "Class B supernet (/16)"
    },
    "dut1_route_12": {
        "prefix": "172.16.0.0/12",
        "nexthop": "10.1.1.2",
        "description": "Large supernet (/12)"
    },
    "dut1_route_8": {
        "prefix": "10.0.0.0/8",
        "nexthop": "10.1.1.2",
        "description": "Class A network (/8)"
    },

    # DUT2 Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ip": "10.1.1.2/24",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ip": "10.2.1.1/24",

    # DUT2 Routes with various prefix lengths
    "dut2_route_host": {
        "prefix": "192.168.1.1/32",
        "nexthop": "10.2.1.2",
        "description": "Host route (/32)"
    },
    "dut2_route_16": {
        "prefix": "192.168.0.0/16",
        "nexthop": "10.2.1.2",
        "description": "Class B supernet (/16)"
    },
    "dut2_route_12": {
        "prefix": "172.16.0.0/12",
        "nexthop": "10.2.1.2",
        "description": "Large supernet (/12)"
    },
    "dut2_route_8": {
        "prefix": "10.0.0.0/8",
        "nexthop": "10.2.1.2",
        "description": "Class A network (/8)"
    },
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr16_interface_config": "TC-OC-SR-16-001",
    "oc_sr16_route_add": "TC-OC-SR-16-002",
    "oc_sr16_route_verify": "TC-OC-SR-16-003",
    "oc_sr16_route_remove": "TC-OC-SR-16-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-16 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Ensure 2-DUT topology
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")

    # Pre-configuration
    static_route_pre_config()

    yield

    # Cleanup - always executes even if test fails
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-16 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing configuration on all DUTs")

    # Clear DUT1 interfaces
    try:
        st.config(vars.D1, [
            f"interface {CONFIG.dut1_eth0}",
            "no ip address",
            "no ipv6 address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Clear DUT2 interfaces
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth8]:
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

    # Remove DUT1 static routes if they exist
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_route_host['prefix']} {CONFIG.dut1_route_host['nexthop']}",
            f"no ip route {CONFIG.dut1_route_16['prefix']} {CONFIG.dut1_route_16['nexthop']}",
            f"no ip route {CONFIG.dut1_route_12['prefix']} {CONFIG.dut1_route_12['nexthop']}",
            f"no ip route {CONFIG.dut1_route_8['prefix']} {CONFIG.dut1_route_8['nexthop']}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 static routes if they exist
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_route_host['prefix']} {CONFIG.dut2_route_host['nexthop']}",
            f"no ip route {CONFIG.dut2_route_16['prefix']} {CONFIG.dut2_route_16['nexthop']}",
            f"no ip route {CONFIG.dut2_route_12['prefix']} {CONFIG.dut2_route_12['nexthop']}",
            f"no ip route {CONFIG.dut2_route_8['prefix']} {CONFIG.dut2_route_8['nexthop']}"
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

    # Explicitly exit Klish CLI mode back to normal user mode on all DUTs
    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.log("Pre-configuration completed")


def static_route_cleanup():
    """Cleanup: Remove static routes and IP configuration."""
    st.log("Cleanup: Removing static routes and IP configuration")

    # Remove static routes - DUT1
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_route_host['prefix']} {CONFIG.dut1_route_host['nexthop']}",
            f"no ip route {CONFIG.dut1_route_16['prefix']} {CONFIG.dut1_route_16['nexthop']}",
            f"no ip route {CONFIG.dut1_route_12['prefix']} {CONFIG.dut1_route_12['nexthop']}",
            f"no ip route {CONFIG.dut1_route_8['prefix']} {CONFIG.dut1_route_8['nexthop']}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 route cleanup warning: {str(e)}")

    # Remove static routes - DUT2
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_route_host['prefix']} {CONFIG.dut2_route_host['nexthop']}",
            f"no ip route {CONFIG.dut2_route_16['prefix']} {CONFIG.dut2_route_16['nexthop']}",
            f"no ip route {CONFIG.dut2_route_12['prefix']} {CONFIG.dut2_route_12['nexthop']}",
            f"no ip route {CONFIG.dut2_route_8['prefix']} {CONFIG.dut2_route_8['nexthop']}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT2 route cleanup warning: {str(e)}")

    # Clear IP addresses - DUT1
    try:
        st.config(vars.D1, [
            f"interface {CONFIG.dut1_eth0}",
            "no ip address",
            "shutdown",
            "exit"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 {CONFIG.dut1_eth0} cleanup warning: {str(e)}")

    # Clear IP addresses - DUT2
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth8]:
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
            st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)
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


def add_static_route(dut, prefix, nexthop, description=""):
    """Add static route - sonic-cli: ip route <prefix> <nexthop>."""
    st.log(f"Adding static route: ip route {prefix} {nexthop} ({description})")
    try:
        st.config(dut, [
            f"ip route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Static route added: {prefix} via {nexthop}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add static route: {str(e)}")
        return False


def delete_static_route(dut, prefix, nexthop, description=""):
    """Delete static route - sonic-cli: no ip route <prefix> <nexthop>."""
    st.log(f"Removing static route: no ip route {prefix} {nexthop} ({description})")
    try:
        st.config(dut, [
            f"no ip route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Static route removed: {prefix} via {nexthop}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to remove static route: {str(e)}")
        return False


def verify_route_in_table(dut, prefix, nexthop=None):
    """Verify route exists in routing table."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup '{prefix}': {output_str[:500]}")

        # Check if route exists (has 'S' marker for static)
        if "S" not in output_str:
            st.log(f"Route {prefix} not found - no 'S' marker in output")
            return False

        # Verify nexthop if specified
        if nexthop and nexthop not in output_str:
            st.log(f"Route {prefix} found but nexthop {nexthop} not present")
            return False

        st.log(f"✓ Route {prefix} verified in routing table")
        return True

    except Exception as e:
        st.error(f"✗ Exception during route verification: {str(e)}")
        return False


def verify_route_by_grep(dut, prefix_mask, expected_prefix):
    """Verify route using grep for specific prefix length."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        # Execute: show ip route | grep "/<prefix_mask>"
        # Example: show ip route | grep "/16" to find 192.168.0.0/16
        cmd = f"show ip route | grep \"/{prefix_mask}\""
        output = st.show(dut, cmd, type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)

        st.log(f"Grep search for '/{prefix_mask}': {output_str[:300]}")

        # Check if expected prefix is in output
        if expected_prefix in output_str:
            st.log(f"✓ Route {expected_prefix} found using grep /{prefix_mask}")
            return True
        else:
            st.log(f"✗ Route {expected_prefix} not found in grep output")
            return False

    except Exception as e:
        st.error(f"✗ Exception during grep verification: {str(e)}")
        return False


def verify_route_not_in_table(dut, prefix):
    """Verify route does NOT exist in routing table (for removal verification)."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup after removal '{prefix}': {output_str[:300]}")

        # Check if route is absent (no 'S' marker or route not found)
        if "S" in output_str and prefix.split('/')[0] in output_str:
            st.log(f"Route {prefix} still present after removal")
            return False

        st.log(f"✓ Route {prefix} successfully removed")
        return True

    except Exception as e:
        st.error(f"✗ Exception during route removal verification: {str(e)}")
        return False


def test_oc_sr16_ipv4_host_routes_and_prefix_lengths():
    """
    Test Case: OC-SR-16 - IPv4 Static Routes with Host Routes and Various Prefix Lengths

    Test Steps:
    1. Configure interfaces on DUT1 and DUT2
    2. Add static routes with various prefix lengths on DUT1 (/32, /16, /12, /8)
    3. Add static routes with various prefix lengths on DUT2 (/32, /16, /12, /8)
    4. Verify routes in routing table
    5. Verify specific prefix lengths using grep
    6. Remove static routes
    7. Verify routes removed
    """
    result_flag = True

    try:
        st.banner("TEST OC-SR-16: IPv4 STATIC ROUTE - HOST ROUTES AND PREFIX LENGTHS")

        # ==================================================================
        # STEP 1: Configure IP Addresses on DUT1
        # ==================================================================
        st.banner("STEP 1: Configure IP Addresses on DUT1")

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr16_interface_config, "msg", "Failed to configure DUT1 Ethernet0")
            result_flag = False

        st.wait(3, "Waiting for DUT1 interfaces to stabilize")

        # ==================================================================
        # STEP 2: Configure IP Addresses on DUT2
        # ==================================================================
        st.banner("STEP 2: Configure IP Addresses on DUT2")

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr16_interface_config, "msg", "Failed to configure DUT2 Ethernet0")
            result_flag = False

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ip):
            st.report_tc_fail(TC_IDS.oc_sr16_interface_config, "msg", "Failed to configure DUT2 Ethernet8")
            result_flag = False

        st.wait(3, "Waiting for DUT2 interfaces to stabilize")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr16_interface_config, "msg", "All interface configurations successful")
        else:
            st.report_fail("msg", "Interface configuration failed - check logs")

        # ==================================================================
        # STEP 3: Add Static Routes on DUT1 (Various Prefix Lengths)
        # ==================================================================
        st.banner("STEP 3: Add Static Routes on DUT1 (Various Prefix Lengths)")

        dut1_routes = [
            CONFIG.dut1_route_host,
            CONFIG.dut1_route_16,
            CONFIG.dut1_route_12,
            CONFIG.dut1_route_8
        ]

        for route in dut1_routes:
            if not add_static_route(vars.D1, route['prefix'], route['nexthop'], route['description']):
                st.report_tc_fail(TC_IDS.oc_sr16_route_add, "msg", f"Failed to add DUT1 route {route['prefix']}")
                result_flag = False

        st.wait(3, "Waiting for DUT1 routes to be programmed")

        # ==================================================================
        # STEP 4: Add Static Routes on DUT2 (Various Prefix Lengths)
        # ==================================================================
        st.banner("STEP 4: Add Static Routes on DUT2 (Various Prefix Lengths)")

        dut2_routes = [
            CONFIG.dut2_route_host,
            CONFIG.dut2_route_16,
            CONFIG.dut2_route_12,
            CONFIG.dut2_route_8
        ]

        for route in dut2_routes:
            if not add_static_route(vars.D2, route['prefix'], route['nexthop'], route['description']):
                st.report_tc_fail(TC_IDS.oc_sr16_route_add, "msg", f"Failed to add DUT2 route {route['prefix']}")
                result_flag = False

        st.wait(3, "Waiting for DUT2 routes to be programmed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr16_route_add, "msg", "All static routes added successfully")

        # ==================================================================
        # STEP 5: Verify Routes in Routing Tables
        # ==================================================================
        st.banner("STEP 5: Verify Routes in Routing Tables")

        st.log("Verifying DUT1 routes...")
        for route in dut1_routes:
            if not verify_route_in_table(vars.D1, route['prefix'], route['nexthop']):
                st.error(f"DUT1: Route {route['prefix']} not found in routing table")
                result_flag = False
            else:
                st.log(f"✓ DUT1: Route {route['prefix']} ({route['description']}) verified")

        st.log("Verifying DUT2 routes...")
        for route in dut2_routes:
            if not verify_route_in_table(vars.D2, route['prefix'], route['nexthop']):
                st.error(f"DUT2: Route {route['prefix']} not found in routing table")
                result_flag = False
            else:
                st.log(f"✓ DUT2: Route {route['prefix']} ({route['description']}) verified")

        # ==================================================================
        # STEP 6: Verify Specific Prefix Lengths Using Grep
        # ==================================================================
        st.banner("STEP 6: Verify Specific Prefix Lengths Using Grep")

        # Verify /32 prefix (host route)
        st.log("Verifying /32 prefix (host route) using grep...")
        if verify_route_by_grep(vars.D1, "32", "192.168.1.1/32"):
            st.log("✓ DUT1: Host route /32 verified using grep")
        else:
            st.error("DUT1: Host route /32 not found using grep")
            result_flag = False

        # Verify /16 prefix
        st.log("Verifying /16 prefix using grep...")
        if verify_route_by_grep(vars.D1, "16", "192.168.0.0/16"):
            st.log("✓ DUT1: /16 prefix route verified using grep")
        else:
            st.error("DUT1: /16 prefix route not found using grep")
            result_flag = False

        # Verify /12 prefix
        st.log("Verifying /12 prefix using grep...")
        if verify_route_by_grep(vars.D1, "12", "172.16.0.0/12"):
            st.log("✓ DUT1: /12 prefix route verified using grep")
        else:
            st.error("DUT1: /12 prefix route not found using grep")
            result_flag = False

        # Verify /8 prefix
        st.log("Verifying /8 prefix using grep...")
        if verify_route_by_grep(vars.D1, "8", "10.0.0.0/8"):
            st.log("✓ DUT1: /8 prefix route verified using grep")
        else:
            st.error("DUT1: /8 prefix route not found using grep")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr16_route_verify, "msg", "All routes verified successfully")

        # ==================================================================
        # STEP 7: Remove Static Routes
        # ==================================================================
        st.banner("STEP 7: Remove Static Routes")

        st.log("Removing DUT1 routes...")
        for route in dut1_routes:
            if not delete_static_route(vars.D1, route['prefix'], route['nexthop'], route['description']):
                st.error(f"Failed to remove DUT1 route {route['prefix']}")
                result_flag = False

        st.log("Removing DUT2 routes...")
        for route in dut2_routes:
            if not delete_static_route(vars.D2, route['prefix'], route['nexthop'], route['description']):
                st.error(f"Failed to remove DUT2 route {route['prefix']}")
                result_flag = False

        st.wait(3, "Waiting for route removal")

        # ==================================================================
        # STEP 8: Verify Routes Removed from Routing Tables
        # ==================================================================
        st.banner("STEP 8: Verify Routes Removed from Routing Tables")

        for route in dut1_routes:
            if verify_route_not_in_table(vars.D1, route['prefix']):
                st.log(f"✓ DUT1: Route {route['prefix']} successfully removed")
            else:
                st.error(f"DUT1: Route {route['prefix']} still present after removal")
                result_flag = False

        for route in dut2_routes:
            if verify_route_not_in_table(vars.D2, route['prefix']):
                st.log(f"✓ DUT2: Route {route['prefix']} successfully removed")
            else:
                st.error(f"DUT2: Route {route['prefix']} still present after removal")
                result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr16_route_remove, "msg", "All routes removed successfully")

    except Exception as e:
        st.error(f"Exception occurred during test execution: {str(e)}")
        result_flag = False

    finally:
        # Ensure cleanup executes
        st.log("Ensuring cleanup executes...")

    # Final test result
    st.banner("TEST RESULT: OC-SR-16")
    if result_flag:
        st.banner("TEST RESULT: OC-SR-16 PASSED")
        st.log("TEST SUMMARY - OC-SR-16: IPv4 Static Route - Host Routes and Prefix Lengths")
        st.log("  ✓ All tests passed successfully")
        st.report_pass("test_case_passed")
    else:
        st.banner("TEST RESULT: OC-SR-16 FAILED")
        st.log("TEST SUMMARY - OC-SR-16: IPv4 Static Route - Host Routes and Prefix Lengths")
        st.log("  ✗ Test failed - check logs for details")
        st.report_fail("msg", "Test case Failed.")
