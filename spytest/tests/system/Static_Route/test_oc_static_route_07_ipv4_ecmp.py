"""
STATIC ROUTE TEST - OC-SR-17: IPv4 Static Route - ECMP (Equal Cost Multi-Path)

Test Case ID: OC-SR-17
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_static_2vs.yaml \
    tests/system/Static_Route/test_oc_static_route_07_ipv4_ecmp.py \
    --logs-path ./logs/oc_sr17_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv4 ECMP (Equal Cost Multi-Path) static routes where multiple
  routes to the same destination with equal cost (same administrative distance)
  are installed for load balancing and redundancy.

  Key Features:
  - Multiple routes to same destination prefix
  - Equal administrative distance (default: 0)
  - Load balancing across multiple paths
  - Automatic failover if one path fails

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0 -> ip address 10.1.1.1/24 -> no shutdown
    interface Ethernet 4 -> ip address 10.1.2.1/24 -> no shutdown
    ip route 100.100.100.0/24 10.1.1.2
    ip route 100.100.100.0/24 10.1.2.2

  DUT2:
    interface Ethernet 0 -> ip address 10.1.1.2/24 -> no shutdown
    interface Ethernet 8 -> ip address 10.2.1.1/24 -> no shutdown
    interface Ethernet 12 -> ip address 10.2.2.1/24 -> no shutdown
    ip route 100.100.100.0/24 10.2.1.2
    ip route 100.100.100.0/24 10.2.2.2

Pre-requisites:
  - Topology: 2-node (D1-D2) | Supported: HW and Virtual
  - OC-build with Klish CLI support
  - Minimum 2 ports between DUTs for ECMP paths
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
    "dut1_eth4": "Ethernet 4",
    "dut1_eth4_ip": "10.1.2.1/24",

    # DUT1 ECMP Routes (same destination, different next-hops)
    "dut1_ecmp_prefix": "100.100.100.0/24",
    "dut1_ecmp_nh1": "10.1.1.2",
    "dut1_ecmp_nh2": "10.1.2.2",

    # DUT2 Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ip": "10.1.1.2/24",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ip": "10.2.1.1/24",
    "dut2_eth12": "Ethernet 12",
    "dut2_eth12_ip": "10.2.2.1/24",

    # DUT2 ECMP Routes (same destination, different next-hops)
    "dut2_ecmp_prefix": "100.100.100.0/24",
    "dut2_ecmp_nh1": "10.2.1.2",
    "dut2_ecmp_nh2": "10.2.2.2",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr17_interface_config": "TC-OC-SR-17-001",
    "oc_sr17_ecmp_add": "TC-OC-SR-17-002",
    "oc_sr17_ecmp_verify": "TC-OC-SR-17-003",
    "oc_sr17_ecmp_remove": "TC-OC-SR-17-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-17 MODULE CONFIGURATION - START")
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
    st.banner("OC STATIC ROUTE SR-17 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing configuration on all DUTs")

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

    # Remove DUT1 ECMP routes if they exist
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_ecmp_prefix} {CONFIG.dut1_ecmp_nh1}",
            f"no ip route {CONFIG.dut1_ecmp_prefix} {CONFIG.dut1_ecmp_nh2}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 ECMP routes if they exist
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_ecmp_prefix} {CONFIG.dut2_ecmp_nh1}",
            f"no ip route {CONFIG.dut2_ecmp_prefix} {CONFIG.dut2_ecmp_nh2}"
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
    """Cleanup: Remove ECMP routes and IP configuration."""
    st.log("Cleanup: Removing ECMP routes and IP configuration")

    # Remove ECMP routes - DUT1
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_ecmp_prefix} {CONFIG.dut1_ecmp_nh1}",
            f"no ip route {CONFIG.dut1_ecmp_prefix} {CONFIG.dut1_ecmp_nh2}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 route cleanup warning: {str(e)}")

    # Remove ECMP routes - DUT2
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_ecmp_prefix} {CONFIG.dut2_ecmp_nh1}",
            f"no ip route {CONFIG.dut2_ecmp_prefix} {CONFIG.dut2_ecmp_nh2}"
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


def add_ecmp_route(dut, prefix, nexthop):
    """Add ECMP static route - sonic-cli: ip route <prefix> <nexthop>."""
    st.log(f"Adding ECMP route: ip route {prefix} {nexthop}")
    try:
        st.config(dut, [
            f"ip route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ ECMP route added: {prefix} via {nexthop}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add ECMP route: {str(e)}")
        return False


def delete_ecmp_route(dut, prefix, nexthop):
    """Delete ECMP static route - sonic-cli: no ip route <prefix> <nexthop>."""
    st.log(f"Removing ECMP route: no ip route {prefix} {nexthop}")
    try:
        st.config(dut, [
            f"no ip route {prefix} {nexthop}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ ECMP route removed: {prefix} via {nexthop}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to remove ECMP route: {str(e)}")
        return False


def verify_ecmp_routes(dut, prefix, nexthop1, nexthop2):
    """Verify both ECMP routes exist in routing table for same destination."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"ECMP route lookup '{prefix}': {output_str[:600]}")

        # Check if both next-hops are present
        if nexthop1 not in output_str:
            st.log(f"ECMP path 1 not found: {nexthop1}")
            return False

        if nexthop2 not in output_str:
            st.log(f"ECMP path 2 not found: {nexthop2}")
            return False

        # Count occurrences of the prefix to verify multiple entries
        prefix_base = prefix.split('/')[0]
        count = output_str.count(prefix_base)

        if count < 2:
            st.log(f"Expected multiple ECMP entries but found only {count}")
            return False

        st.log(f"✓ ECMP routes verified: {prefix} via {nexthop1} and {nexthop2}")
        return True

    except Exception as e:
        st.error(f"✗ Exception during ECMP route verification: {str(e)}")
        return False


def verify_ecmp_count(dut, prefix, expected_count=2):
    """Verify the number of ECMP paths for a given prefix."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, "show ip route static", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)

        # Count how many times the prefix appears in static routes
        prefix_base = prefix.split('/')[0]
        count = 0
        for line in output_str.split('\n'):
            if prefix in line and 'S' in line:
                count += 1

        st.log(f"ECMP path count for {prefix}: {count} (expected: {expected_count})")

        if count == expected_count:
            st.log(f"✓ ECMP count verified: {count} paths")
            return True
        else:
            st.log(f"✗ ECMP count mismatch: found {count}, expected {expected_count}")
            return False

    except Exception as e:
        st.error(f"✗ Exception during ECMP count verification: {str(e)}")
        return False


def verify_ecmp_removed(dut, prefix):
    """Verify ECMP routes are removed from routing table."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup after ECMP removal '{prefix}': {output_str[:300]}")

        # Check if prefix is absent or no 'S' marker
        prefix_base = prefix.split('/')[0]
        if 'S' in output_str and prefix_base in output_str:
            st.log(f"ECMP routes still present for {prefix}")
            return False

        st.log(f"✓ ECMP routes successfully removed for {prefix}")
        return True

    except Exception as e:
        st.error(f"✗ Exception during ECMP removal verification: {str(e)}")
        return False


def test_oc_sr17_ipv4_ecmp_routes():
    """
    Test Case: OC-SR-17 - IPv4 ECMP (Equal Cost Multi-Path) Static Routes

    Test Steps:
    1. Configure interfaces on DUT1 and DUT2
    2. Add first ECMP route on DUT1
    3. Add second ECMP route on DUT1 (same destination)
    4. Add ECMP routes on DUT2
    5. Verify ECMP routes in routing table (both paths)
    6. Verify ECMP path count
    7. Remove ECMP routes
    8. Verify routes removed
    """
    result_flag = True

    try:
        st.banner("TEST OC-SR-17: IPv4 STATIC ROUTE - ECMP (EQUAL COST MULTI-PATH)")

        # ==================================================================
        # STEP 1: Configure IP Addresses on DUT1
        # ==================================================================
        st.banner("STEP 1: Configure IP Addresses on DUT1")

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr17_interface_config, "msg", "Failed to configure DUT1 Ethernet0")
            result_flag = False

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth4, CONFIG.dut1_eth4_ip):
            st.report_tc_fail(TC_IDS.oc_sr17_interface_config, "msg", "Failed to configure DUT1 Ethernet4")
            result_flag = False

        st.wait(3, "Waiting for DUT1 interfaces to stabilize")

        # ==================================================================
        # STEP 2: Configure IP Addresses on DUT2
        # ==================================================================
        st.banner("STEP 2: Configure IP Addresses on DUT2")

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr17_interface_config, "msg", "Failed to configure DUT2 Ethernet0")
            result_flag = False

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ip):
            st.report_tc_fail(TC_IDS.oc_sr17_interface_config, "msg", "Failed to configure DUT2 Ethernet8")
            result_flag = False

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth12, CONFIG.dut2_eth12_ip):
            st.report_tc_fail(TC_IDS.oc_sr17_interface_config, "msg", "Failed to configure DUT2 Ethernet12")
            result_flag = False

        st.wait(3, "Waiting for DUT2 interfaces to stabilize")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr17_interface_config, "msg", "All interface configurations successful")
        else:
            st.report_fail("msg", "Interface configuration failed - check logs")

        # ==================================================================
        # STEP 3: Add ECMP Routes on DUT1
        # ==================================================================
        st.banner("STEP 3: Add ECMP Routes on DUT1")
        st.log(f"Adding ECMP Path 1: {CONFIG.dut1_ecmp_prefix} via {CONFIG.dut1_ecmp_nh1}")
        st.log(f"Adding ECMP Path 2: {CONFIG.dut1_ecmp_prefix} via {CONFIG.dut1_ecmp_nh2}")

        if not add_ecmp_route(vars.D1, CONFIG.dut1_ecmp_prefix, CONFIG.dut1_ecmp_nh1):
            st.report_tc_fail(TC_IDS.oc_sr17_ecmp_add, "msg", "Failed to add DUT1 ECMP path 1")
            result_flag = False

        if not add_ecmp_route(vars.D1, CONFIG.dut1_ecmp_prefix, CONFIG.dut1_ecmp_nh2):
            st.report_tc_fail(TC_IDS.oc_sr17_ecmp_add, "msg", "Failed to add DUT1 ECMP path 2")
            result_flag = False

        st.wait(3, "Waiting for DUT1 ECMP routes to be programmed")

        # ==================================================================
        # STEP 4: Add ECMP Routes on DUT2
        # ==================================================================
        st.banner("STEP 4: Add ECMP Routes on DUT2")
        st.log(f"Adding ECMP Path 1: {CONFIG.dut2_ecmp_prefix} via {CONFIG.dut2_ecmp_nh1}")
        st.log(f"Adding ECMP Path 2: {CONFIG.dut2_ecmp_prefix} via {CONFIG.dut2_ecmp_nh2}")

        if not add_ecmp_route(vars.D2, CONFIG.dut2_ecmp_prefix, CONFIG.dut2_ecmp_nh1):
            st.report_tc_fail(TC_IDS.oc_sr17_ecmp_add, "msg", "Failed to add DUT2 ECMP path 1")
            result_flag = False

        if not add_ecmp_route(vars.D2, CONFIG.dut2_ecmp_prefix, CONFIG.dut2_ecmp_nh2):
            st.report_tc_fail(TC_IDS.oc_sr17_ecmp_add, "msg", "Failed to add DUT2 ECMP path 2")
            result_flag = False

        st.wait(3, "Waiting for DUT2 ECMP routes to be programmed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr17_ecmp_add, "msg", "All ECMP routes added successfully")

        # ==================================================================
        # STEP 5: Verify ECMP Routes in Routing Tables
        # ==================================================================
        st.banner("STEP 5: Verify ECMP Routes in Routing Tables")

        st.log("Verifying DUT1 ECMP routes...")
        if not verify_ecmp_routes(vars.D1, CONFIG.dut1_ecmp_prefix, CONFIG.dut1_ecmp_nh1, CONFIG.dut1_ecmp_nh2):
            st.error(f"DUT1: ECMP routes not found for {CONFIG.dut1_ecmp_prefix}")
            result_flag = False
        else:
            st.log(f"✓ DUT1: ECMP routes verified for {CONFIG.dut1_ecmp_prefix}")

        st.log("Verifying DUT2 ECMP routes...")
        if not verify_ecmp_routes(vars.D2, CONFIG.dut2_ecmp_prefix, CONFIG.dut2_ecmp_nh1, CONFIG.dut2_ecmp_nh2):
            st.error(f"DUT2: ECMP routes not found for {CONFIG.dut2_ecmp_prefix}")
            result_flag = False
        else:
            st.log(f"✓ DUT2: ECMP routes verified for {CONFIG.dut2_ecmp_prefix}")

        # ==================================================================
        # STEP 6: Verify ECMP Path Count
        # ==================================================================
        st.banner("STEP 6: Verify ECMP Path Count")

        st.log("Verifying DUT1 ECMP path count...")
        if not verify_ecmp_count(vars.D1, CONFIG.dut1_ecmp_prefix, expected_count=2):
            st.error(f"DUT1: ECMP path count mismatch for {CONFIG.dut1_ecmp_prefix}")
            result_flag = False
        else:
            st.log(f"✓ DUT1: ECMP path count verified (2 paths)")

        st.log("Verifying DUT2 ECMP path count...")
        if not verify_ecmp_count(vars.D2, CONFIG.dut2_ecmp_prefix, expected_count=2):
            st.error(f"DUT2: ECMP path count mismatch for {CONFIG.dut2_ecmp_prefix}")
            result_flag = False
        else:
            st.log(f"✓ DUT2: ECMP path count verified (2 paths)")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr17_ecmp_verify, "msg", "All ECMP routes verified successfully")

        # ==================================================================
        # STEP 7: Remove ECMP Routes
        # ==================================================================
        st.banner("STEP 7: Remove ECMP Routes")

        st.log("Removing DUT1 ECMP routes...")
        if not delete_ecmp_route(vars.D1, CONFIG.dut1_ecmp_prefix, CONFIG.dut1_ecmp_nh1):
            st.error("Failed to remove DUT1 ECMP path 1")
            result_flag = False

        if not delete_ecmp_route(vars.D1, CONFIG.dut1_ecmp_prefix, CONFIG.dut1_ecmp_nh2):
            st.error("Failed to remove DUT1 ECMP path 2")
            result_flag = False

        st.log("Removing DUT2 ECMP routes...")
        if not delete_ecmp_route(vars.D2, CONFIG.dut2_ecmp_prefix, CONFIG.dut2_ecmp_nh1):
            st.error("Failed to remove DUT2 ECMP path 1")
            result_flag = False

        if not delete_ecmp_route(vars.D2, CONFIG.dut2_ecmp_prefix, CONFIG.dut2_ecmp_nh2):
            st.error("Failed to remove DUT2 ECMP path 2")
            result_flag = False

        st.wait(3, "Waiting for ECMP route removal")

        # ==================================================================
        # STEP 8: Verify ECMP Routes Removed from Routing Tables
        # ==================================================================
        st.banner("STEP 8: Verify ECMP Routes Removed from Routing Tables")

        if verify_ecmp_removed(vars.D1, CONFIG.dut1_ecmp_prefix):
            st.log(f"✓ DUT1: ECMP routes successfully removed")
        else:
            st.error(f"DUT1: ECMP routes still present after removal")
            result_flag = False

        if verify_ecmp_removed(vars.D2, CONFIG.dut2_ecmp_prefix):
            st.log(f"✓ DUT2: ECMP routes successfully removed")
        else:
            st.error(f"DUT2: ECMP routes still present after removal")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr17_ecmp_remove, "msg", "All ECMP routes removed successfully")

    except Exception as e:
        st.error(f"Exception occurred during test execution: {str(e)}")
        result_flag = False

    finally:
        # Ensure cleanup executes
        st.log("Ensuring cleanup executes...")

    # Final test result
    st.banner("TEST RESULT: OC-SR-17")
    if result_flag:
        st.banner("TEST RESULT: OC-SR-17 PASSED")
        st.log("TEST SUMMARY - OC-SR-17: IPv4 Static Route - ECMP (Equal Cost Multi-Path)")
        st.log("  ✓ All tests passed successfully")
        st.report_pass("test_case_passed")
    else:
        st.banner("TEST RESULT: OC-SR-17 FAILED")
        st.log("TEST SUMMARY - OC-SR-17: IPv4 Static Route - ECMP (Equal Cost Multi-Path)")
        st.log("  ✗ Test failed - check logs for details")
        st.report_fail("msg", "Test case Failed.")
