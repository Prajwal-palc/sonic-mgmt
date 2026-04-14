"""
STATIC ROUTE TEST - OC-SR-10: IPv4 Static Route - Basic Next-Hop (3 DUTs)

Test Case ID: OC-SR-10
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/claudeuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_3vs.yaml \
    tests/system/OC_Static_Route/test_oc_static_route_01_ipv4_basic_nexthop.py \
    --logs-path ./logs/oc_sr10_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv4 basic static route with next-hop across 3 DUTs.
  Uses direct sonic-cli (klish) commands matching manual validation.
  Topology: DUT1 <-> DUT2 <-> DUT3

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0 -> ip address 10.1.1.1/24 -> no shutdown
    interface Ethernet 4 -> ip address 10.2.1.1/24 -> no shutdown
    ip route 30.30.30.0/24 10.1.1.2
    ip route 40.40.40.0/24 10.2.1.1

  DUT2:
    interface Ethernet 0 -> ip address 10.1.1.2/24 -> no shutdown
    interface Ethernet 4 -> ip address 10.1.2.2/24 -> no shutdown
    interface Ethernet 8 -> ip address 10.2.1.1/24 -> no shutdown
    interface Ethernet 12 -> ip address 10.2.2.1/24 -> no shutdown
    ip route 30.30.30.0/24 10.2.1.2
    ip route 40.40.40.0/24 10.1.1.1

  DUT3:
    interface Ethernet 8 -> ip address 10.3.1.2/24 -> no shutdown
    interface Ethernet 12 -> ip address 10.3.2.2/24 -> no shutdown
    ip route 40.40.40.0/24 10.2.1.1

Pre-requisites:
  - Topology: 3-node (D1-D2-D3) | Supported: HW and Virtual
  - OC-build with Klish CLI support
  - Minimum 2 ports between each DUT pair
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
    "dut1_eth4_ip": "10.2.1.1/24",
    "dut1_route1_prefix": "30.30.30.0/24",
    "dut1_route1_nexthop": "10.1.1.2",
    "dut1_route2_prefix": "40.40.40.0/24",
    "dut1_route2_nexthop": "10.2.1.1",

    # DUT2 Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ip": "10.1.1.2/24",
    "dut2_eth4": "Ethernet 4",
    "dut2_eth4_ip": "10.1.2.2/24",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ip": "10.2.1.1/24",
    "dut2_eth12": "Ethernet 12",
    "dut2_eth12_ip": "10.2.2.1/24",
    "dut2_route1_prefix": "30.30.30.0/24",
    "dut2_route1_nexthop": "10.2.1.2",
    "dut2_route2_prefix": "40.40.40.0/24",
    "dut2_route2_nexthop": "10.1.1.1",

    # DUT3 Configuration
    "dut3_eth8": "Ethernet 8",
    "dut3_eth8_ip": "10.2.1.2/24",  # Connected to DUT2 Eth8 (10.2.1.1/24)
    "dut3_eth12": "Ethernet 12",
    "dut3_eth12_ip": "10.2.2.2/24",  # Connected to DUT2 Eth12 (10.2.2.1/24)
    "dut3_route1_prefix": "40.40.40.0/24",
    "dut3_route1_nexthop": "10.2.1.1",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr10_interface_config": "TC-OC-SR-10-001",
    "oc_sr10_route_add": "TC-OC-SR-10-002",
    "oc_sr10_route_verify": "TC-OC-SR-10-003",
    "oc_sr10_route_remove": "TC-OC-SR-10-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-10 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Ensure 3-DUT topology
    vars = st.ensure_min_topology("D1D2:2", "D2D3:2")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}, DUT3: {vars.D3}")

    # Pre-configuration
    static_route_pre_config()

    yield

    # Cleanup - always executes even if test fails
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-10 MODULE CLEANUP - START")
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
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth4, CONFIG.dut2_eth8, CONFIG.dut2_eth12]:
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

    # Clear DUT3 interfaces
    for intf in [CONFIG.dut3_eth8, CONFIG.dut3_eth12]:
        try:
            st.config(vars.D3, [
                f"interface {intf}",
                "no ip address",
                "no ipv6 address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception:
            pass

    # Remove static routes if they exist
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop}",
            f"no ip route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop}",
            f"no ip route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    try:
        st.config(vars.D3, [
            f"no ip route {CONFIG.dut3_route1_prefix} {CONFIG.dut3_route1_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    st.wait(3, "Waiting for pre-config clear")

    # Explicitly exit Klish CLI mode back to normal user mode on all DUTs
    for dut in [vars.D1, vars.D2, vars.D3]:
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
            f"no ip route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop}",
            f"no ip route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 route cleanup warning: {str(e)}")

    # Remove static routes - DUT2
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop}",
            f"no ip route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT2 route cleanup warning: {str(e)}")

    # Remove static routes - DUT3
    try:
        st.config(vars.D3, [
            f"no ip route {CONFIG.dut3_route1_prefix} {CONFIG.dut3_route1_nexthop}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT3 route cleanup warning: {str(e)}")

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
    for intf in [CONFIG.dut2_eth0, CONFIG.dut2_eth4, CONFIG.dut2_eth8, CONFIG.dut2_eth12]:
        try:
            st.config(vars.D2, [
                f"interface {intf}",
                "no ip address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"DUT2 {intf} cleanup warning: {str(e)}")

    # Clear IP addresses - DUT3
    for intf in [CONFIG.dut3_eth8, CONFIG.dut3_eth12]:
        try:
            st.config(vars.D3, [
                f"interface {intf}",
                "no ip address",
                "shutdown",
                "exit"
            ], type='klish', skip_error_check=True)
        except Exception as e:
            st.log(f"DUT3 {intf} cleanup warning: {str(e)}")

    # Explicitly exit Klish CLI mode back to normal user mode on all DUTs
    for dut in [vars.D1, vars.D2, vars.D3]:
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


def verify_route_in_table(dut, prefix, nexthop=None):
    """Verify route exists in show ip route output."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup '{prefix}': {output_str[:300]}")

        # Check if route exists
        if "S" not in output_str:  # Static route marker
            return False

        # If nexthop specified, verify it matches
        if nexthop and nexthop not in output_str:
            return False

        return True
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        return False


def verify_route_not_in_table(dut, prefix):
    """Verify route is absent from routing table."""
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        output = st.show(dut, f"show ip route {prefix}", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Route lookup after removal '{prefix}': {output_str[:300]}")

        # Route should not have 'S' marker (static route)
        return "S" not in output_str or prefix not in output_str
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        return False


@pytest.mark.static_route
@pytest.mark.community
@pytest.mark.community_pass
def test_oc_sr10_ipv4_static_route_basic_nexthop():
    """
    Test Case OC-SR-10: IPv4 Static Route - Basic Next-Hop (3 DUTs)

    Validates sonic-cli commands across 3 DUTs:
      DUT1: Configure Ethernet0, Ethernet4, add 2 static routes
      DUT2: Configure 4 interfaces, add 2 static routes
      DUT3: Configure 2 interfaces, add 1 static route
      Verify routes in routing tables
      Remove routes and verify deletion
    """
    st.banner("=" * 80)
    st.banner("TEST OC-SR-10: IPv4 STATIC ROUTE - BASIC NEXT-HOP (3 DUTs)")
    st.banner("=" * 80)

    result_flag = True  # Track overall test result

    try:
        # ==================================================================
        # STEP 1: Configure IP Addresses on DUT1
        # ==================================================================
        st.banner("STEP 1: Configure IP Addresses on DUT1")

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr10_interface_config, "msg", "Failed to configure DUT1 Ethernet0")
            result_flag = False

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth4, CONFIG.dut1_eth4_ip):
            st.report_tc_fail(TC_IDS.oc_sr10_interface_config, "msg", "Failed to configure DUT1 Ethernet4")
            result_flag = False

        st.wait(3, "Waiting for DUT1 interfaces to stabilize")

        # ==================================================================
        # STEP 2: Configure IP Addresses on DUT2
        # ==================================================================
        st.banner("STEP 2: Configure IP Addresses on DUT2")

        interfaces_dut2 = [
            (CONFIG.dut2_eth0, CONFIG.dut2_eth0_ip),
            (CONFIG.dut2_eth4, CONFIG.dut2_eth4_ip),
            (CONFIG.dut2_eth8, CONFIG.dut2_eth8_ip),
            (CONFIG.dut2_eth12, CONFIG.dut2_eth12_ip)
        ]

        for intf, ip in interfaces_dut2:
            if not configure_interface_ip(vars.D2, intf, ip):
                st.report_tc_fail(TC_IDS.oc_sr10_interface_config, "msg", f"Failed to configure DUT2 {intf}")
                result_flag = False

        st.wait(3, "Waiting for DUT2 interfaces to stabilize")

        # ==================================================================
        # STEP 3: Configure IP Addresses on DUT3
        # ==================================================================
        st.banner("STEP 3: Configure IP Addresses on DUT3")

        if not configure_interface_ip(vars.D3, CONFIG.dut3_eth8, CONFIG.dut3_eth8_ip):
            st.report_tc_fail(TC_IDS.oc_sr10_interface_config, "msg", "Failed to configure DUT3 Ethernet8")
            result_flag = False

        if not configure_interface_ip(vars.D3, CONFIG.dut3_eth12, CONFIG.dut3_eth12_ip):
            st.report_tc_fail(TC_IDS.oc_sr10_interface_config, "msg", "Failed to configure DUT3 Ethernet12")
            result_flag = False

        st.wait(3, "Waiting for DUT3 interfaces to stabilize")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr10_interface_config, "msg", "All interface configurations successful")
        else:
            st.report_fail("msg", "Interface configuration failed - check logs")

        # ==================================================================
        # STEP 4: Add Static Routes on DUT1
        # ==================================================================
        st.banner("STEP 4: Add Static Routes on DUT1")
        st.log(f"DUT1 Route 1: ip route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop}")
        st.log(f"DUT1 Route 2: ip route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop}")

        if not add_static_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop):
            st.report_tc_fail(TC_IDS.oc_sr10_route_add, "msg", "Failed to add DUT1 route 1")
            result_flag = False

        if not add_static_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop):
            st.report_tc_fail(TC_IDS.oc_sr10_route_add, "msg", "Failed to add DUT1 route 2")
            result_flag = False

        st.wait(3, "Waiting for DUT1 routes to be programmed")

        # ==================================================================
        # STEP 5: Add Static Routes on DUT2
        # ==================================================================
        st.banner("STEP 5: Add Static Routes on DUT2")
        st.log(f"DUT2 Route 1: ip route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop}")
        st.log(f"DUT2 Route 2: ip route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop}")

        if not add_static_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop):
            st.report_tc_fail(TC_IDS.oc_sr10_route_add, "msg", "Failed to add DUT2 route 1")
            result_flag = False

        if not add_static_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop):
            st.report_tc_fail(TC_IDS.oc_sr10_route_add, "msg", "Failed to add DUT2 route 2")
            result_flag = False

        st.wait(3, "Waiting for DUT2 routes to be programmed")

        # ==================================================================
        # STEP 6: Add Static Route on DUT3
        # ==================================================================
        st.banner("STEP 6: Add Static Route on DUT3")
        st.log(f"DUT3 Route 1: ip route {CONFIG.dut3_route1_prefix} {CONFIG.dut3_route1_nexthop}")

        if not add_static_route(vars.D3, CONFIG.dut3_route1_prefix, CONFIG.dut3_route1_nexthop):
            st.report_tc_fail(TC_IDS.oc_sr10_route_add, "msg", "Failed to add DUT3 route 1")
            result_flag = False

        st.wait(3, "Waiting for DUT3 routes to be programmed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr10_route_add, "msg", "All static routes added successfully")
        else:
            st.report_fail("msg", "Static route addition failed - check logs")

        # ==================================================================
        # STEP 7: Verify Routes in Routing Tables
        # ==================================================================
        st.banner("STEP 7: Verify Routes in Routing Tables")

        # Verify DUT1 routes
        st.log("Verifying DUT1 routes...")
        if not verify_route_in_table(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop):
            st.error(f"DUT1: Route {CONFIG.dut1_route1_prefix} not found in routing table")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route {CONFIG.dut1_route1_prefix} via {CONFIG.dut1_route1_nexthop} verified")

        if not verify_route_in_table(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop):
            st.error(f"DUT1: Route {CONFIG.dut1_route2_prefix} not found in routing table")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route {CONFIG.dut1_route2_prefix} via {CONFIG.dut1_route2_nexthop} verified")

        # Verify DUT2 routes
        st.log("Verifying DUT2 routes...")
        if not verify_route_in_table(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop):
            st.error(f"DUT2: Route {CONFIG.dut2_route1_prefix} not found in routing table")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route1_prefix} via {CONFIG.dut2_route1_nexthop} verified")

        if not verify_route_in_table(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop):
            st.error(f"DUT2: Route {CONFIG.dut2_route2_prefix} not found in routing table")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route2_prefix} via {CONFIG.dut2_route2_nexthop} verified")

        # Verify DUT3 routes
        st.log("Verifying DUT3 routes...")
        if not verify_route_in_table(vars.D3, CONFIG.dut3_route1_prefix, CONFIG.dut3_route1_nexthop):
            st.error(f"DUT3: Route {CONFIG.dut3_route1_prefix} not found in routing table")
            result_flag = False
        else:
            st.log(f"✓ DUT3: Route {CONFIG.dut3_route1_prefix} via {CONFIG.dut3_route1_nexthop} verified")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr10_route_verify, "msg", "All static routes verified in routing tables")
        else:
            st.report_tc_fail(TC_IDS.oc_sr10_route_verify, "msg", "Route verification failed")
            st.generate_tech_support([vars.D1, vars.D2, vars.D3], "oc_sr10_route_verify_failed")

        # ==================================================================
        # STEP 8: Remove Static Routes
        # ==================================================================
        st.banner("STEP 8: Remove Static Routes")

        # Remove DUT1 routes
        st.log("Removing DUT1 routes...")
        if not delete_static_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop):
            st.error(f"Failed to remove DUT1 route {CONFIG.dut1_route1_prefix}")
            result_flag = False

        if not delete_static_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop):
            st.error(f"Failed to remove DUT1 route {CONFIG.dut1_route2_prefix}")
            result_flag = False

        # Remove DUT2 routes
        st.log("Removing DUT2 routes...")
        if not delete_static_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop):
            st.error(f"Failed to remove DUT2 route {CONFIG.dut2_route1_prefix}")
            result_flag = False

        if not delete_static_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop):
            st.error(f"Failed to remove DUT2 route {CONFIG.dut2_route2_prefix}")
            result_flag = False

        # Remove DUT3 route
        st.log("Removing DUT3 routes...")
        if not delete_static_route(vars.D3, CONFIG.dut3_route1_prefix, CONFIG.dut3_route1_nexthop):
            st.error(f"Failed to remove DUT3 route {CONFIG.dut3_route1_prefix}")
            result_flag = False

        st.wait(3, "Waiting for route removal")

        # ==================================================================
        # STEP 9: Verify Routes Removed
        # ==================================================================
        st.banner("STEP 9: Verify Routes Removed from Routing Tables")

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

        # Verify DUT3 route removed
        if not verify_route_not_in_table(vars.D3, CONFIG.dut3_route1_prefix):
            st.error(f"DUT3: Route {CONFIG.dut3_route1_prefix} still exists after deletion")
            result_flag = False
        else:
            st.log(f"✓ DUT3: Route {CONFIG.dut3_route1_prefix} successfully removed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr10_route_remove, "msg", "All static routes removed successfully")
        else:
            st.report_tc_fail(TC_IDS.oc_sr10_route_remove, "msg", "Route removal verification failed")

    except Exception as e:
        st.error(f"Test execution error: {str(e)}")
        st.generate_tech_support([vars.D1, vars.D2, vars.D3], "oc_sr10_exception")
        result_flag = False

    finally:
        # Ensure cleanup runs even if test fails
        st.log("Ensuring cleanup executes...")

    # ==================================================================
    # TEST RESULT
    # ==================================================================
    st.banner("=" * 80)
    if result_flag:
        st.banner("TEST RESULT: OC-SR-10 PASSED")
        st.banner("=" * 80)
        st.log("TEST SUMMARY - OC-SR-10: IPv4 Static Route - Basic Next-Hop (3 DUTs)")
        st.log("  ✓ All interface IP addresses configured")
        st.log("  ✓ All static routes added successfully")
        st.log("  ✓ All routes verified in routing tables")
        st.log("  ✓ All routes removed successfully")
        st.log("  ✓ Route removal verified")
        st.report_pass("test_case_passed")
    else:
        st.banner("TEST RESULT: OC-SR-10 FAILED")
        st.banner("=" * 80)
        st.log("TEST SUMMARY - OC-SR-10: IPv4 Static Route - Basic Next-Hop (3 DUTs)")
        st.log("  ✗ Test failed - check logs for details")
        st.report_fail("test_case_failed")
