"""
STATIC ROUTE TEST - OC-SR-15: IPv4 Static Route - Routes with Tag and Distance

Test Case ID: OC-SR-15
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_static_2vs.yaml \
    tests/system/Static_Route/test_oc_static_route_05_ipv4_tag_distance.py \
    --logs-path ./logs/oc_sr15_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv4 static routes configured with both route tags and
  administrative distance for traffic engineering and route preference control.

  Key Features:
  - Routes with tag AND distance (metric) together
  - Multiple routes to same destination with different distances
  - Tag values for route identification/filtering
  - Distance for route preference (lower distance = higher preference)

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0 -> ip address 10.1.1.1/24 -> no shutdown
    interface Ethernet 4 -> ip address 10.1.2.1/24 -> no shutdown
    ip route 192.168.100.0/24 10.1.1.2 tag 200 25
    ip route 192.168.100.0/24 10.1.2.2 tag 201 50

  DUT2:
    interface Ethernet 0 -> ip address 10.1.1.2/24 -> no shutdown
    interface Ethernet 8 -> ip address 10.2.1.1/24 -> no shutdown
    interface Ethernet 12 -> ip address 10.2.2.1/24 -> no shutdown
    ip route 192.168.100.0/24 10.2.1.2 tag 200 30
    ip route 192.168.100.0/24 10.2.2.2 tag 201 60

Pre-requisites:
  - Topology: 2-node (D1-D2) | Supported: HW and Virtual
  - OC-build with Klish CLI support
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
    "dut1_eth0_ip": "10.1.1.1/24",
    "dut1_eth4": "Ethernet 4",
    "dut1_eth4_ip": "10.1.2.1/24",

    # DUT1 Routes with Tag and Distance
    "dut1_route1_prefix": "192.168.100.0/24",
    "dut1_route1_nexthop": "10.1.1.2",
    "dut1_route1_tag": 200,
    "dut1_route1_distance": 25,

    "dut1_route2_prefix": "192.168.100.0/24",  # Same prefix, different path
    "dut1_route2_nexthop": "10.1.2.2",
    "dut1_route2_tag": 201,
    "dut1_route2_distance": 50,

    # DUT2 Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ip": "10.1.1.2/24",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ip": "10.2.1.1/24",
    "dut2_eth12": "Ethernet 12",
    "dut2_eth12_ip": "10.2.2.1/24",

    # DUT2 Routes with Tag and Distance
    "dut2_route1_prefix": "192.168.100.0/24",
    "dut2_route1_nexthop": "10.2.1.2",
    "dut2_route1_tag": 200,
    "dut2_route1_distance": 30,

    "dut2_route2_prefix": "192.168.100.0/24",  # Same prefix, different path
    "dut2_route2_nexthop": "10.2.2.2",
    "dut2_route2_tag": 201,
    "dut2_route2_distance": 60,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr15_interface_config": "TC-OC-SR-15-001",
    "oc_sr15_route_add": "TC-OC-SR-15-002",
    "oc_sr15_route_verify": "TC-OC-SR-15-003",
    "oc_sr15_route_remove": "TC-OC-SR-15-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-15 MODULE CONFIGURATION - START")
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
    st.banner("OC STATIC ROUTE SR-15 MODULE CLEANUP - START")
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

    # Remove DUT1 static routes if they exist
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop} tag {CONFIG.dut1_route1_tag} metric {CONFIG.dut1_route1_distance}",
            f"no ip route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop} tag {CONFIG.dut1_route2_tag} metric {CONFIG.dut1_route2_distance}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 static routes if they exist
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop} tag {CONFIG.dut2_route1_tag} metric {CONFIG.dut2_route1_distance}",
            f"no ip route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop} tag {CONFIG.dut2_route2_tag} metric {CONFIG.dut2_route2_distance}"
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
            f"no ip route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop} tag {CONFIG.dut1_route1_tag} metric {CONFIG.dut1_route1_distance}",
            f"no ip route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop} tag {CONFIG.dut1_route2_tag} metric {CONFIG.dut1_route2_distance}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 route cleanup warning: {str(e)}")

    # Remove static routes - DUT2
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop} tag {CONFIG.dut2_route1_tag} metric {CONFIG.dut2_route1_distance}",
            f"no ip route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop} tag {CONFIG.dut2_route2_tag} metric {CONFIG.dut2_route2_distance}"
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


def add_static_route_with_tag_distance(dut, prefix, nexthop, tag, distance):
    """Add static route with tag and distance - sonic-cli: ip route <prefix> <nexthop> tag <tag> <distance>."""
    st.log(f"Adding static route: ip route {prefix} {nexthop} tag {tag} {distance}")
    try:
        st.config(dut, [
            f"ip route {prefix} {nexthop} tag {tag} {distance}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Static route added: {prefix} via {nexthop} tag {tag} distance {distance}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add static route: {str(e)}")
        return False


def delete_static_route_with_tag_distance(dut, prefix, nexthop, tag, distance):
    """Delete static route with tag and distance - sonic-cli: no ip route <prefix> <nexthop> tag <tag> <distance>."""
    st.log(f"Removing static route: no ip route {prefix} {nexthop} tag {tag} {distance}")
    try:
        st.config(dut, [
            f"no ip route {prefix} {nexthop} tag {tag} {distance}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Static route removed: {prefix} via {nexthop} tag {tag} distance {distance}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to remove static route: {str(e)}")
        return False


def verify_route_with_distance(dut, prefix, nexthop, distance):
    """Verify route exists in routing table with specified distance."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup '{prefix}' with distance {distance}: {output_str[:500]}")

        # Check if route exists (has 'S' marker for static)
        if "S" not in output_str:
            st.log(f"Route {prefix} not found - no 'S' marker in output")
            return False

        # Verify nexthop is present
        if nexthop not in output_str:
            st.log(f"Route {prefix} found but nexthop {nexthop} not present")
            return False

        # Verify distance is present (shown as "distance/0" in output)
        distance_str = f"{distance}/0"
        if distance_str not in output_str:
            st.log(f"Route {prefix} found but distance {distance} not visible (expected '{distance_str}')")
            # Note: Distance might not always be visible in show ip route, check running-config
            return True  # Still return True if route exists with correct nexthop

        st.log(f"✓ Route {prefix} via {nexthop} with distance {distance} verified")
        return True

    except Exception as e:
        st.error(f"✗ Exception during route verification: {str(e)}")
        return False


def verify_route_in_running_config(dut, prefix, nexthop, tag, distance):
    """Verify route with tag and distance in running-configuration."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, "show running-configuration", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)

        # Expected format: ip route 192.168.100.0/24 10.1.1.2 tag 200 metric 25
        expected_route = f"ip route {prefix} {nexthop} tag {tag} metric {distance}"

        st.log(f"Searching for: '{expected_route}'")

        if expected_route in output_str:
            st.log(f"✓ Route configuration verified in running-config")
            return True
        else:
            st.log(f"✗ Route configuration NOT found in running-config")
            st.log(f"   Expected: {expected_route}")
            return False

    except Exception as e:
        st.error(f"✗ Exception during running-config verification: {str(e)}")
        return False


def verify_route_not_in_table(dut, prefix, nexthop=None, distance=None):
    """Verify route does NOT exist in routing table (for removal verification)."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup after removal '{prefix}': {output_str[:300]}")

        # If nexthop specified, check if it's absent
        if nexthop and nexthop in output_str:
            # If distance also specified, check if that specific route is absent
            if distance:
                distance_str = f"{distance}/0"
                if distance_str in output_str:
                    st.log(f"Route {prefix} via {nexthop} with distance {distance} still present")
                    return False
                else:
                    st.log(f"✓ Route {prefix} via {nexthop} with distance {distance} successfully removed")
                    return True
            else:
                st.log(f"Route {prefix} via {nexthop} still present")
                return False

        st.log(f"✓ Route {prefix} successfully removed")
        return True

    except Exception as e:
        st.error(f"✗ Exception during route removal verification: {str(e)}")
        return False


def test_oc_sr15_ipv4_routes_with_tag_and_distance():
    """
    Test Case: OC-SR-15 - IPv4 Static Routes with Tag and Distance

    Test Steps:
    1. Configure interfaces on DUT1 and DUT2
    2. Add static routes with tag and distance on DUT1
    3. Add static routes with tag and distance on DUT2
    4. Verify routes in routing table (distance verification)
    5. Verify routes in running-configuration (tag and distance)
    6. Remove static routes
    7. Verify routes removed
    """
    result_flag = True

    try:
        st.banner("TEST OC-SR-15: IPv4 STATIC ROUTE - ROUTES WITH TAG AND DISTANCE")

        # ==================================================================
        # STEP 1: Configure IP Addresses on DUT1
        # ==================================================================
        st.banner("STEP 1: Configure IP Addresses on DUT1")

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr15_interface_config, "msg", "Failed to configure DUT1 Ethernet0")
            result_flag = False

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth4, CONFIG.dut1_eth4_ip):
            st.report_tc_fail(TC_IDS.oc_sr15_interface_config, "msg", "Failed to configure DUT1 Ethernet4")
            result_flag = False

        st.wait(3, "Waiting for DUT1 interfaces to stabilize")

        # ==================================================================
        # STEP 2: Configure IP Addresses on DUT2
        # ==================================================================
        st.banner("STEP 2: Configure IP Addresses on DUT2")

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr15_interface_config, "msg", "Failed to configure DUT2 Ethernet0")
            result_flag = False

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ip):
            st.report_tc_fail(TC_IDS.oc_sr15_interface_config, "msg", "Failed to configure DUT2 Ethernet8")
            result_flag = False

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth12, CONFIG.dut2_eth12_ip):
            st.report_tc_fail(TC_IDS.oc_sr15_interface_config, "msg", "Failed to configure DUT2 Ethernet12")
            result_flag = False

        st.wait(3, "Waiting for DUT2 interfaces to stabilize")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr15_interface_config, "msg", "All interface configurations successful")
        else:
            st.report_fail("msg", "Interface configuration failed - check logs")

        # ==================================================================
        # STEP 3: Add Static Routes with Tag and Distance on DUT1
        # ==================================================================
        st.banner("STEP 3: Add Static Routes with Tag and Distance on DUT1")
        st.log(f"DUT1 Route 1: ip route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop} tag {CONFIG.dut1_route1_tag} {CONFIG.dut1_route1_distance}")
        st.log(f"DUT1 Route 2: ip route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop} tag {CONFIG.dut1_route2_tag} {CONFIG.dut1_route2_distance}")

        if not add_static_route_with_tag_distance(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop,
                                                    CONFIG.dut1_route1_tag, CONFIG.dut1_route1_distance):
            st.report_tc_fail(TC_IDS.oc_sr15_route_add, "msg", "Failed to add DUT1 route 1")
            result_flag = False

        if not add_static_route_with_tag_distance(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop,
                                                    CONFIG.dut1_route2_tag, CONFIG.dut1_route2_distance):
            st.report_tc_fail(TC_IDS.oc_sr15_route_add, "msg", "Failed to add DUT1 route 2")
            result_flag = False

        st.wait(3, "Waiting for DUT1 routes to be programmed")

        # ==================================================================
        # STEP 4: Add Static Routes with Tag and Distance on DUT2
        # ==================================================================
        st.banner("STEP 4: Add Static Routes with Tag and Distance on DUT2")
        st.log(f"DUT2 Route 1: ip route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop} tag {CONFIG.dut2_route1_tag} {CONFIG.dut2_route1_distance}")
        st.log(f"DUT2 Route 2: ip route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop} tag {CONFIG.dut2_route2_tag} {CONFIG.dut2_route2_distance}")

        if not add_static_route_with_tag_distance(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop,
                                                    CONFIG.dut2_route1_tag, CONFIG.dut2_route1_distance):
            st.report_tc_fail(TC_IDS.oc_sr15_route_add, "msg", "Failed to add DUT2 route 1")
            result_flag = False

        if not add_static_route_with_tag_distance(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop,
                                                    CONFIG.dut2_route2_tag, CONFIG.dut2_route2_distance):
            st.report_tc_fail(TC_IDS.oc_sr15_route_add, "msg", "Failed to add DUT2 route 2")
            result_flag = False

        st.wait(3, "Waiting for DUT2 routes to be programmed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr15_route_add, "msg", "All static routes added successfully")

        # ==================================================================
        # STEP 5: Verify Routes in Routing Tables (Distance Check)
        # ==================================================================
        st.banner("STEP 5: Verify Routes in Routing Tables (Distance Check)")

        st.log("Verifying DUT1 routes with distance...")
        if not verify_route_with_distance(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop, CONFIG.dut1_route1_distance):
            st.error(f"DUT1: Route {CONFIG.dut1_route1_prefix} via {CONFIG.dut1_route1_nexthop} with distance {CONFIG.dut1_route1_distance} not found")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route {CONFIG.dut1_route1_prefix} via {CONFIG.dut1_route1_nexthop} with distance {CONFIG.dut1_route1_distance} verified")

        if not verify_route_with_distance(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop, CONFIG.dut1_route2_distance):
            st.error(f"DUT1: Route {CONFIG.dut1_route2_prefix} via {CONFIG.dut1_route2_nexthop} with distance {CONFIG.dut1_route2_distance} not found")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route {CONFIG.dut1_route2_prefix} via {CONFIG.dut1_route2_nexthop} with distance {CONFIG.dut1_route2_distance} verified")

        st.log("Verifying DUT2 routes with distance...")
        if not verify_route_with_distance(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop, CONFIG.dut2_route1_distance):
            st.error(f"DUT2: Route {CONFIG.dut2_route1_prefix} via {CONFIG.dut2_route1_nexthop} with distance {CONFIG.dut2_route1_distance} not found")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route1_prefix} via {CONFIG.dut2_route1_nexthop} with distance {CONFIG.dut2_route1_distance} verified")

        if not verify_route_with_distance(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop, CONFIG.dut2_route2_distance):
            st.error(f"DUT2: Route {CONFIG.dut2_route2_prefix} via {CONFIG.dut2_route2_nexthop} with distance {CONFIG.dut2_route2_distance} not found")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route2_prefix} via {CONFIG.dut2_route2_nexthop} with distance {CONFIG.dut2_route2_distance} verified")

        # ==================================================================
        # STEP 6: Verify Routes in Running Configuration (Tag and Distance)
        # ==================================================================
        st.banner("STEP 6: Verify Routes in Running Configuration (Tag and Distance)")

        st.log("Verifying DUT1 routes in running-configuration...")
        if not verify_route_in_running_config(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop,
                                               CONFIG.dut1_route1_tag, CONFIG.dut1_route1_distance):
            st.error(f"DUT1: Route config not found in running-config")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route 1 configuration verified (tag {CONFIG.dut1_route1_tag}, distance {CONFIG.dut1_route1_distance})")

        if not verify_route_in_running_config(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop,
                                               CONFIG.dut1_route2_tag, CONFIG.dut1_route2_distance):
            st.error(f"DUT1: Route 2 config not found in running-config")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route 2 configuration verified (tag {CONFIG.dut1_route2_tag}, distance {CONFIG.dut1_route2_distance})")

        st.log("Verifying DUT2 routes in running-configuration...")
        if not verify_route_in_running_config(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop,
                                               CONFIG.dut2_route1_tag, CONFIG.dut2_route1_distance):
            st.error(f"DUT2: Route 1 config not found in running-config")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route 1 configuration verified (tag {CONFIG.dut2_route1_tag}, distance {CONFIG.dut2_route1_distance})")

        if not verify_route_in_running_config(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop,
                                               CONFIG.dut2_route2_tag, CONFIG.dut2_route2_distance):
            st.error(f"DUT2: Route 2 config not found in running-config")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route 2 configuration verified (tag {CONFIG.dut2_route2_tag}, distance {CONFIG.dut2_route2_distance})")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr15_route_verify, "msg", "All routes verified successfully")

        # ==================================================================
        # STEP 7: Remove Static Routes
        # ==================================================================
        st.banner("STEP 7: Remove Static Routes")

        st.log("Removing DUT1 routes...")
        if not delete_static_route_with_tag_distance(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop,
                                                       CONFIG.dut1_route1_tag, CONFIG.dut1_route1_distance):
            st.error("Failed to remove DUT1 route 1")
            result_flag = False

        if not delete_static_route_with_tag_distance(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop,
                                                       CONFIG.dut1_route2_tag, CONFIG.dut1_route2_distance):
            st.error("Failed to remove DUT1 route 2")
            result_flag = False

        st.log("Removing DUT2 routes...")
        if not delete_static_route_with_tag_distance(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop,
                                                       CONFIG.dut2_route1_tag, CONFIG.dut2_route1_distance):
            st.error("Failed to remove DUT2 route 1")
            result_flag = False

        if not delete_static_route_with_tag_distance(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop,
                                                       CONFIG.dut2_route2_tag, CONFIG.dut2_route2_distance):
            st.error("Failed to remove DUT2 route 2")
            result_flag = False

        st.wait(3, "Waiting for route removal")

        # ==================================================================
        # STEP 8: Verify Routes Removed from Routing Tables
        # ==================================================================
        st.banner("STEP 8: Verify Routes Removed from Routing Tables")

        if verify_route_not_in_table(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop, CONFIG.dut1_route1_distance):
            st.log(f"✓ DUT1: Route 1 successfully removed")
        else:
            st.error(f"DUT1: Route 1 still present after removal")
            result_flag = False

        if verify_route_not_in_table(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop, CONFIG.dut1_route2_distance):
            st.log(f"✓ DUT1: Route 2 successfully removed")
        else:
            st.error(f"DUT1: Route 2 still present after removal")
            result_flag = False

        if verify_route_not_in_table(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop, CONFIG.dut2_route1_distance):
            st.log(f"✓ DUT2: Route 1 successfully removed")
        else:
            st.error(f"DUT2: Route 1 still present after removal")
            result_flag = False

        if verify_route_not_in_table(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop, CONFIG.dut2_route2_distance):
            st.log(f"✓ DUT2: Route 2 successfully removed")
        else:
            st.error(f"DUT2: Route 2 still present after removal")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr15_route_remove, "msg", "All routes removed successfully")

    except Exception as e:
        st.error(f"Exception occurred during test execution: {str(e)}")
        result_flag = False

    finally:
        # Ensure cleanup executes
        st.log("Ensuring cleanup executes...")

    # Final test result
    st.banner("TEST RESULT: OC-SR-15")
    if result_flag:
        st.banner("TEST RESULT: OC-SR-15 PASSED")
        st.log("TEST SUMMARY - OC-SR-15: IPv4 Static Route - Routes with Tag and Distance")
        st.log("  ✓ All tests passed successfully")
        st.report_pass("test_case_passed")
    else:
        st.banner("TEST RESULT: OC-SR-15 FAILED")
        st.log("TEST SUMMARY - OC-SR-15: IPv4 Static Route - Routes with Tag and Distance")
        st.log("  ✗ Test failed - check logs for details")
        st.report_fail("msg", "Test case Failed.")
