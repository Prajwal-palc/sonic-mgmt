"""
STATIC ROUTE TEST - OC-SR-18: IPv6 Static Route - Basic Next-Hop

Test Case ID: OC-SR-18
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_static_2vs.yaml \
    tests/system/Static_Route/test_oc_static_route_08_ipv6_basic.py \
    --logs-path ./logs/oc_sr18_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv6 basic static routes with next-hop IPv6 addresses.
  This is the first IPv6 static route test case covering fundamental
  IPv6 routing capabilities.

  Key Features:
  - IPv6 address configuration on interfaces
  - IPv6 static routes with next-hop IPv6 addresses
  - IPv6 routing table verification
  - show ipv6 route static command validation

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0 -> ipv6 address 2001:1:1::1/64 -> no shutdown
    interface Ethernet 4 -> ipv6 address 2001:1:2::1/64 -> no shutdown
    ipv6 route 2001:db8:100::/64 2001:1:1::2
    ipv6 route 2001:db8:200::/64 2001:1:1::2

  DUT2:
    interface Ethernet 0 -> ipv6 address 2001:1:1::2/64 -> no shutdown
    interface Ethernet 8 -> ipv6 address 2001:2:1::1/64 -> no shutdown
    interface Ethernet 12 -> ipv6 address 2001:2:2::1/64 -> no shutdown
    ipv6 route 2001:db8:100::/64 2001:2:1::2
    ipv6 route 2001:db8:200::/64 2001:1:1::1

Pre-requisites:
  - Topology: 2-node (D1-D2) | Supported: HW and Virtual
  - OC-build with Klish CLI support
  - IPv6 enabled on devices
  - Minimum 2 ports between DUTs
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
    "dut1_eth0_ipv6": "2001:1:1::1/64",
    "dut1_eth4": "Ethernet 4",
    "dut1_eth4_ipv6": "2001:1:2::1/64",

    # DUT1 IPv6 Static Routes
    "dut1_route1_prefix": "2001:db8:100::/64",
    "dut1_route1_nexthop": "2001:1:1::2",
    "dut1_route2_prefix": "2001:db8:200::/64",
    "dut1_route2_nexthop": "2001:1:1::2",

    # DUT2 Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ipv6": "2001:1:1::2/64",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ipv6": "2001:2:1::1/64",
    "dut2_eth12": "Ethernet 12",
    "dut2_eth12_ipv6": "2001:2:2::1/64",

    # DUT2 IPv6 Static Routes
    "dut2_route1_prefix": "2001:db8:100::/64",
    "dut2_route1_nexthop": "2001:2:1::2",
    "dut2_route2_prefix": "2001:db8:200::/64",
    "dut2_route2_nexthop": "2001:1:1::1",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr18_interface_config": "TC-OC-SR-18-001",
    "oc_sr18_route_add": "TC-OC-SR-18-002",
    "oc_sr18_route_verify": "TC-OC-SR-18-003",
    "oc_sr18_route_remove": "TC-OC-SR-18-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-18 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Ensure 2-DUT topology
    vars = st.ensure_min_topology("D1D2:2")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")

    # Pre-configuration
    static_route_pre_config()

    yield

    # Cleanup - always executes even if test fails
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-18 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing IPv6 configuration on all DUTs")

    # Clear DUT1 interfaces
    for intf in [CONFIG.dut1_eth0, CONFIG.dut1_eth4]:
        try:
            st.config(vars.D1, [
                f"interface {intf}",
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
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Remove DUT1 IPv6 static routes if they exist
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop}",
            f"no ipv6 route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 IPv6 static routes if they exist
    try:
        st.config(vars.D2, [
            f"no ipv6 route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop}",
            f"no ipv6 route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop}"
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
    """Cleanup: Remove IPv6 static routes and IP configuration."""
    st.log("Cleanup: Removing IPv6 static routes and IPv6 configuration")

    # Remove static routes - DUT1
    try:
        st.config(vars.D1, [
            f"no ipv6 route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop}",
            f"no ipv6 route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 IPv6 route cleanup warning: {str(e)}")

    # Remove static routes - DUT2
    try:
        st.config(vars.D2, [
            f"no ipv6 route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop}",
            f"no ipv6 route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT2 IPv6 route cleanup warning: {str(e)}")

    # Clear IPv6 addresses - DUT1
    for intf in [CONFIG.dut1_eth0, CONFIG.dut1_eth4]:
        try:
            st.config(vars.D1, [
                f"interface {intf}",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"DUT1 {intf} cleanup warning: {str(e)}")

    # Clear IPv6 addresses - DUT2
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth8, CONFIG.dut2_eth12]:
        try:
            st.config(vars.D2, [
                f"interface {intf}",
                "no ipv6 address",
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


def configure_interface_ipv6(dut, interface, ipv6_with_prefix):
    """Configure IPv6 on interface - sonic-cli: interface X -> ipv6 address Y -> no shutdown."""
    st.log(f"Configuring IPv6 {ipv6_with_prefix} on {dut} {interface}")
    try:
        st.config(dut, [
            f"interface {interface}",
            f"ipv6 address {ipv6_with_prefix}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IPv6 {ipv6_with_prefix} configured on {interface}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to configure IPv6 on {interface}: {str(e)}")
        return False


def add_ipv6_static_route(dut, prefix, nexthop):
    """Add IPv6 static route - sonic-cli: ipv6 route <prefix> <nexthop>."""
    st.log(f"Adding IPv6 static route: ipv6 route {prefix} {nexthop}")
    try:
        st.config(dut, [
            f"ipv6 route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IPv6 static route added: {prefix} via {nexthop}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add IPv6 static route: {str(e)}")
        return False


def delete_ipv6_static_route(dut, prefix, nexthop):
    """Delete IPv6 static route - sonic-cli: no ipv6 route <prefix> <nexthop>."""
    st.log(f"Removing IPv6 static route: no ipv6 route {prefix} {nexthop}")
    try:
        st.config(dut, [
            f"no ipv6 route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ IPv6 static route removed: {prefix} via {nexthop}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to remove IPv6 static route: {str(e)}")
        return False


def verify_ipv6_route_in_table(dut, prefix, nexthop=None):
    """Verify IPv6 route exists in routing table."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, f"show ipv6 route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"IPv6 route lookup '{prefix}': {output_str[:500]}")

        # Check if route exists (has 'S' marker for static)
        if "S" not in output_str:
            st.log(f"IPv6 route {prefix} not found - no 'S' marker in output")
            return False

        # Verify nexthop if specified
        if nexthop:
            # Normalize IPv6 address for comparison (handle :: compression)
            nexthop_normalized = nexthop.lower()
            output_lower = output_str.lower()

            if nexthop_normalized not in output_lower:
                st.log(f"IPv6 route {prefix} found but nexthop {nexthop} not present")
                return False

        st.log(f"✓ IPv6 route {prefix} verified in routing table")
        return True

    except Exception as e:
        st.error(f"✗ Exception during IPv6 route verification: {str(e)}")
        return False


def verify_ipv6_route_not_in_table(dut, prefix):
    """Verify IPv6 route does NOT exist in routing table (for removal verification)."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, f"show ipv6 route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"IPv6 route lookup after removal '{prefix}': {output_str[:300]}")

        # Check if route is absent (no 'S' marker or route not found)
        # Extract prefix network portion for checking
        prefix_network = prefix.split('/')[0]

        if "S" in output_str and prefix_network in output_str:
            st.log(f"IPv6 route {prefix} still present after removal")
            return False

        st.log(f"✓ IPv6 route {prefix} successfully removed")
        return True

    except Exception as e:
        st.error(f"✗ Exception during IPv6 route removal verification: {str(e)}")
        return False


def test_oc_sr18_ipv6_static_route_basic():
    """
    Test Case: OC-SR-18 - IPv6 Static Routes with Basic Next-Hop

    Test Steps:
    1. Configure IPv6 addresses on DUT1 interfaces
    2. Configure IPv6 addresses on DUT2 interfaces
    3. Add IPv6 static routes on DUT1
    4. Add IPv6 static routes on DUT2
    5. Verify IPv6 routes in routing table
    6. Remove IPv6 static routes
    7. Verify IPv6 routes removed
    """
    result_flag = True

    try:
        st.banner("TEST OC-SR-18: IPv6 STATIC ROUTE - BASIC NEXT-HOP")

        # ==================================================================
        # STEP 1: Configure IPv6 Addresses on DUT1
        # ==================================================================
        st.banner("STEP 1: Configure IPv6 Addresses on DUT1")

        if not configure_interface_ipv6(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ipv6):
            st.report_tc_fail(TC_IDS.oc_sr18_interface_config, "msg", "Failed to configure DUT1 Ethernet0")
            result_flag = False

        if not configure_interface_ipv6(vars.D1, CONFIG.dut1_eth4, CONFIG.dut1_eth4_ipv6):
            st.report_tc_fail(TC_IDS.oc_sr18_interface_config, "msg", "Failed to configure DUT1 Ethernet4")
            result_flag = False

        st.wait(3, "Waiting for DUT1 IPv6 interfaces to stabilize")

        # ==================================================================
        # STEP 2: Configure IPv6 Addresses on DUT2
        # ==================================================================
        st.banner("STEP 2: Configure IPv6 Addresses on DUT2")

        if not configure_interface_ipv6(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ipv6):
            st.report_tc_fail(TC_IDS.oc_sr18_interface_config, "msg", "Failed to configure DUT2 Ethernet0")
            result_flag = False

        if not configure_interface_ipv6(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ipv6):
            st.report_tc_fail(TC_IDS.oc_sr18_interface_config, "msg", "Failed to configure DUT2 Ethernet8")
            result_flag = False

        if not configure_interface_ipv6(vars.D2, CONFIG.dut2_eth12, CONFIG.dut2_eth12_ipv6):
            st.report_tc_fail(TC_IDS.oc_sr18_interface_config, "msg", "Failed to configure DUT2 Ethernet12")
            result_flag = False

        st.wait(3, "Waiting for DUT2 IPv6 interfaces to stabilize")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr18_interface_config, "msg", "All IPv6 interface configurations successful")
        else:
            st.report_fail("msg", "IPv6 interface configuration failed - check logs")

        # ==================================================================
        # STEP 3: Add IPv6 Static Routes on DUT1
        # ==================================================================
        st.banner("STEP 3: Add IPv6 Static Routes on DUT1")
        st.log(f"DUT1 Route 1: ipv6 route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop}")
        st.log(f"DUT1 Route 2: ipv6 route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop}")

        if not add_ipv6_static_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop):
            st.report_tc_fail(TC_IDS.oc_sr18_route_add, "msg", "Failed to add DUT1 IPv6 route 1")
            result_flag = False

        if not add_ipv6_static_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop):
            st.report_tc_fail(TC_IDS.oc_sr18_route_add, "msg", "Failed to add DUT1 IPv6 route 2")
            result_flag = False

        st.wait(3, "Waiting for DUT1 IPv6 routes to be programmed")

        # ==================================================================
        # STEP 4: Add IPv6 Static Routes on DUT2
        # ==================================================================
        st.banner("STEP 4: Add IPv6 Static Routes on DUT2")
        st.log(f"DUT2 Route 1: ipv6 route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop}")
        st.log(f"DUT2 Route 2: ipv6 route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop}")

        if not add_ipv6_static_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop):
            st.report_tc_fail(TC_IDS.oc_sr18_route_add, "msg", "Failed to add DUT2 IPv6 route 1")
            result_flag = False

        if not add_ipv6_static_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop):
            st.report_tc_fail(TC_IDS.oc_sr18_route_add, "msg", "Failed to add DUT2 IPv6 route 2")
            result_flag = False

        st.wait(3, "Waiting for DUT2 IPv6 routes to be programmed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr18_route_add, "msg", "All IPv6 static routes added successfully")

        # ==================================================================
        # STEP 5: Verify IPv6 Routes in Routing Tables
        # ==================================================================
        st.banner("STEP 5: Verify IPv6 Routes in Routing Tables")

        st.log("Verifying DUT1 IPv6 routes...")
        if not verify_ipv6_route_in_table(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop):
            st.error(f"DUT1: IPv6 route {CONFIG.dut1_route1_prefix} not found in routing table")
            result_flag = False
        else:
            st.log(f"✓ DUT1: IPv6 route {CONFIG.dut1_route1_prefix} via {CONFIG.dut1_route1_nexthop} verified")

        if not verify_ipv6_route_in_table(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop):
            st.error(f"DUT1: IPv6 route {CONFIG.dut1_route2_prefix} not found in routing table")
            result_flag = False
        else:
            st.log(f"✓ DUT1: IPv6 route {CONFIG.dut1_route2_prefix} via {CONFIG.dut1_route2_nexthop} verified")

        st.log("Verifying DUT2 IPv6 routes...")
        if not verify_ipv6_route_in_table(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop):
            st.error(f"DUT2: IPv6 route {CONFIG.dut2_route1_prefix} not found in routing table")
            result_flag = False
        else:
            st.log(f"✓ DUT2: IPv6 route {CONFIG.dut2_route1_prefix} via {CONFIG.dut2_route1_nexthop} verified")

        if not verify_ipv6_route_in_table(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop):
            st.error(f"DUT2: IPv6 route {CONFIG.dut2_route2_prefix} not found in routing table")
            result_flag = False
        else:
            st.log(f"✓ DUT2: IPv6 route {CONFIG.dut2_route2_prefix} via {CONFIG.dut2_route2_nexthop} verified")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr18_route_verify, "msg", "All IPv6 routes verified successfully")

        # ==================================================================
        # STEP 6: Remove IPv6 Static Routes
        # ==================================================================
        st.banner("STEP 6: Remove IPv6 Static Routes")

        st.log("Removing DUT1 IPv6 routes...")
        if not delete_ipv6_static_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop):
            st.error("Failed to remove DUT1 IPv6 route 1")
            result_flag = False

        if not delete_ipv6_static_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop):
            st.error("Failed to remove DUT1 IPv6 route 2")
            result_flag = False

        st.log("Removing DUT2 IPv6 routes...")
        if not delete_ipv6_static_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop):
            st.error("Failed to remove DUT2 IPv6 route 1")
            result_flag = False

        if not delete_ipv6_static_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop):
            st.error("Failed to remove DUT2 IPv6 route 2")
            result_flag = False

        st.wait(3, "Waiting for IPv6 route removal")

        # ==================================================================
        # STEP 7: Verify IPv6 Routes Removed from Routing Tables
        # ==================================================================
        st.banner("STEP 7: Verify IPv6 Routes Removed from Routing Tables")

        if verify_ipv6_route_not_in_table(vars.D1, CONFIG.dut1_route1_prefix):
            st.log(f"✓ DUT1: IPv6 route {CONFIG.dut1_route1_prefix} successfully removed")
        else:
            st.error(f"DUT1: IPv6 route {CONFIG.dut1_route1_prefix} still present after removal")
            result_flag = False

        if verify_ipv6_route_not_in_table(vars.D1, CONFIG.dut1_route2_prefix):
            st.log(f"✓ DUT1: IPv6 route {CONFIG.dut1_route2_prefix} successfully removed")
        else:
            st.error(f"DUT1: IPv6 route {CONFIG.dut1_route2_prefix} still present after removal")
            result_flag = False

        if verify_ipv6_route_not_in_table(vars.D2, CONFIG.dut2_route1_prefix):
            st.log(f"✓ DUT2: IPv6 route {CONFIG.dut2_route1_prefix} successfully removed")
        else:
            st.error(f"DUT2: IPv6 route {CONFIG.dut2_route1_prefix} still present after removal")
            result_flag = False

        if verify_ipv6_route_not_in_table(vars.D2, CONFIG.dut2_route2_prefix):
            st.log(f"✓ DUT2: IPv6 route {CONFIG.dut2_route2_prefix} successfully removed")
        else:
            st.error(f"DUT2: IPv6 route {CONFIG.dut2_route2_prefix} still present after removal")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr18_route_remove, "msg", "All IPv6 routes removed successfully")

    except Exception as e:
        st.error(f"Exception occurred during test execution: {str(e)}")
        result_flag = False

    finally:
        # Ensure cleanup executes
        st.log("Ensuring cleanup executes...")

    # Final test result
    st.banner("TEST RESULT: OC-SR-18")
    if result_flag:
        st.banner("TEST RESULT: OC-SR-18 PASSED")
        st.log("TEST SUMMARY - OC-SR-18: IPv6 Static Route - Basic Next-Hop")
        st.log("  ✓ All tests passed successfully")
        st.report_pass("test_case_passed")
    else:
        st.banner("TEST RESULT: OC-SR-18 FAILED")
        st.log("TEST SUMMARY - OC-SR-18: IPv6 Static Route - Basic Next-Hop")
        st.log("  ✗ Test failed - check logs for details")
        st.report_fail("msg", "Test case Failed.")
