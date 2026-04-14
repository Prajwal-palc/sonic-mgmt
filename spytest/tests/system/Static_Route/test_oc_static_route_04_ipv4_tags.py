"""
STATIC ROUTE TEST - OC-SR-13: IPv4 Static Route - Routes with Tags

Test Case ID: OC-SR-13
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/Static_Route/test_oc_static_route_04_ipv4_tags.py \
    --logs-path ./logs/oc_sr13_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv4 static routes with route tags for policy-based routing.
  Uses direct sonic-cli (klish) commands matching manual validation.
  Route tags are metadata used for route filtering and redistribution.

Manual sonic-cli commands validated:
  DUT1:
    ip route 192.168.80.0/24 10.1.1.2 tag 50
    ip route 192.168.81.0/24 10.1.2.2 tag 100
    show ip route static -> Note: Tags NOT displayed in output (known issue)

  DUT2:
    ip route 192.168.80.0/24 10.2.1.2 tag 50
    ip route 192.168.81.0/24 10.2.2.2 tag 100
    ip route 192.168.82.0/24 10.1.1.1 tag 150
    show ip route static -> Note: Tags NOT displayed in output (known issue)

Known Issues:
  - Route tags are configured successfully
  - Tags visible in 'show running-configuration'
  - Tags NOT displayed in 'show ip route' output (bug)

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
    "dut1_eth4_ip": "10.1.2.1/24",

    # DUT2 Interface configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ip": "10.1.1.2/24",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ip": "10.2.1.2/24",
    "dut2_eth12": "Ethernet 12",
    "dut2_eth12_ip": "10.2.2.2/24",

    # DUT1 Routes with tags
    "dut1_route1_prefix": "192.168.80.0/24",
    "dut1_route1_nexthop": "10.1.1.2",
    "dut1_route1_tag": "50",
    "dut1_route2_prefix": "192.168.81.0/24",
    "dut1_route2_nexthop": "10.1.2.2",
    "dut1_route2_tag": "100",

    # DUT2 Routes with tags
    "dut2_route1_prefix": "192.168.80.0/24",
    "dut2_route1_nexthop": "10.2.1.2",
    "dut2_route1_tag": "50",
    "dut2_route2_prefix": "192.168.81.0/24",
    "dut2_route2_nexthop": "10.2.2.2",
    "dut2_route2_tag": "100",
    "dut2_route3_prefix": "192.168.82.0/24",
    "dut2_route3_nexthop": "10.1.1.1",
    "dut2_route3_tag": "150",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "oc_sr13_interface_config": "TC-OC-SR-13-001",
    "oc_sr13_tagged_route_add": "TC-OC-SR-13-002",
    "oc_sr13_tagged_route_verify": "TC-OC-SR-13-003",
    "oc_sr13_tagged_route_remove": "TC-OC-SR-13-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_tags_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-13 MODULE CONFIGURATION - START")
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
    st.banner("OC STATIC ROUTE SR-13 MODULE CLEANUP - START")
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

    # Remove DUT1 tagged routes if they exist
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop} tag {CONFIG.dut1_route1_tag}",
            f"no ip route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop} tag {CONFIG.dut1_route2_tag}"
        ], type='klish', skip_error_check=True)
    except Exception:
        pass

    # Remove DUT2 tagged routes if they exist
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop} tag {CONFIG.dut2_route1_tag}",
            f"no ip route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop} tag {CONFIG.dut2_route2_tag}",
            f"no ip route {CONFIG.dut2_route3_prefix} {CONFIG.dut2_route3_nexthop} tag {CONFIG.dut2_route3_tag}"
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
    st.log("Cleanup: Removing tagged routes and IP configuration")

    # Remove DUT1 tagged routes
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop} tag {CONFIG.dut1_route1_tag}",
            f"no ip route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop} tag {CONFIG.dut1_route2_tag}"
        ], type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"DUT1 route cleanup warning: {str(e)}")

    # Remove DUT2 tagged routes
    try:
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop} tag {CONFIG.dut2_route1_tag}",
            f"no ip route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop} tag {CONFIG.dut2_route2_tag}",
            f"no ip route {CONFIG.dut2_route3_prefix} {CONFIG.dut2_route3_nexthop} tag {CONFIG.dut2_route3_tag}"
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


def add_tagged_route(dut, prefix, nexthop, tag):
    """Add tagged route - sonic-cli: ip route <prefix> <nexthop> tag <tag>."""
    st.log(f"Adding tagged route: ip route {prefix} {nexthop} tag {tag}")
    try:
        st.config(dut, [
            f"ip route {prefix} {nexthop} tag {tag}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Tagged route added: {prefix} via {nexthop} tag {tag}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to add tagged route: {str(e)}")
        return False


def delete_tagged_route(dut, prefix, nexthop, tag):
    """Delete tagged route - sonic-cli: no ip route <prefix> <nexthop> tag <tag>."""
    st.log(f"Removing tagged route: no ip route {prefix} {nexthop} tag {tag}")
    try:
        st.config(dut, [
            f"no ip route {prefix} {nexthop} tag {tag}"
        ], type='klish', skip_error_check=False)
        st.log(f"✓ Tagged route removed: {prefix} via {nexthop} tag {tag}")
        return True
    except Exception as e:
        st.error(f"✗ Failed to remove tagged route: {str(e)}")
        return False


def verify_tagged_route_in_routing_table(dut, prefix, nexthop):
    """
    Verify tagged route exists in routing table.
    Note: Tags are NOT displayed in 'show ip route' (known bug).
    This function only verifies route exists with correct next-hop.
    """
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
        st.log(f"Tagged route lookup '{prefix}': {output_str[:400]}")

        # Check if route exists with correct next-hop
        # Note: Tag won't be displayed (known issue)
        if "S" in output_str and nexthop in output_str:
            st.log(f"✓ Route verified (tag not displayed): {prefix} via {nexthop}")
            st.log(f"⚠ Known Issue: Route tag not visible in 'show ip route' output")
            return True
        else:
            st.error(f"✗ Route not found: {prefix} via {nexthop}")
            return False
    except Exception as e:
        st.error(f"Route verify failed: {str(e)}")
        return False


def verify_tagged_route_in_config(dut, prefix, nexthop, tag):
    """
    Verify tagged route exists in running-configuration.
    Tags ARE visible in running config.
    """
    try:
        # Exit config mode before show command
        st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)

        # Exit Klish CLI to Linux shell before show command
        try:
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

        output = st.show(dut, "show running-configuration", type='klish', skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Checking running config for route with tag...")

        # Look for the complete route configuration with tag
        route_config = f"ip route {prefix} {nexthop} tag {tag}"

        if route_config in output_str:
            st.log(f"✓ Tagged route verified in running-config: {route_config}")
            return True
        else:
            st.error(f"✗ Tagged route not found in running-config: {route_config}")
            st.log(f"Running config snippet: {output_str[:500]}")
            return False
    except Exception as e:
        st.error(f"Running-config verify failed: {str(e)}")
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
@pytest.mark.route_tags
@pytest.mark.community
@pytest.mark.community_pass
def test_oc_sr13_ipv4_routes_with_tags():
    """
    Test Case OC-SR-13: IPv4 Static Route - Routes with Tags

    Validates sonic-cli tagged route commands:
      DUT1: ip route 192.168.80.0/24 10.1.1.2 tag 50
            ip route 192.168.81.0/24 10.1.2.2 tag 100
      DUT2: ip route 192.168.80.0/24 10.2.1.2 tag 50
            ip route 192.168.81.0/24 10.2.2.2 tag 100
            ip route 192.168.82.0/24 10.1.1.1 tag 150
      Verify routes exist in routing table (tags not displayed - known bug)
      Verify tags visible in running-configuration
      Remove routes and verify deletion

    Known Issue: Route tags NOT displayed in 'show ip route' output
    """
    st.banner("=" * 80)
    st.banner("TEST OC-SR-13: IPv4 STATIC ROUTE - ROUTES WITH TAGS")
    st.banner("=" * 80)

    result_flag = True  # Track overall test result

    try:
        # ==================================================================
        # STEP 1: Configure IP Addresses on DUT1 Interfaces
        # ==================================================================
        st.banner("STEP 1: Configure IP Addresses on DUT1 Interfaces")

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr13_interface_config, "msg", "Failed to configure DUT1 Ethernet0")
            result_flag = False

        if not configure_interface_ip(vars.D1, CONFIG.dut1_eth4, CONFIG.dut1_eth4_ip):
            st.report_tc_fail(TC_IDS.oc_sr13_interface_config, "msg", "Failed to configure DUT1 Ethernet4")
            result_flag = False

        st.wait(3, "Waiting for DUT1 interfaces to stabilize")

        # ==================================================================
        # STEP 2: Configure IP Addresses on DUT2 Interfaces
        # ==================================================================
        st.banner("STEP 2: Configure IP Addresses on DUT2 Interfaces")

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ip):
            st.report_tc_fail(TC_IDS.oc_sr13_interface_config, "msg", "Failed to configure DUT2 Ethernet0")
            result_flag = False

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ip):
            st.report_tc_fail(TC_IDS.oc_sr13_interface_config, "msg", "Failed to configure DUT2 Ethernet8")
            result_flag = False

        if not configure_interface_ip(vars.D2, CONFIG.dut2_eth12, CONFIG.dut2_eth12_ip):
            st.report_tc_fail(TC_IDS.oc_sr13_interface_config, "msg", "Failed to configure DUT2 Ethernet12")
            result_flag = False

        st.wait(3, "Waiting for DUT2 interfaces to stabilize")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr13_interface_config, "msg", "All interface configurations successful")
        else:
            st.report_fail("msg", "Interface configuration failed - check logs")

        # ==================================================================
        # STEP 3: Add Tagged Routes on DUT1
        # ==================================================================
        st.banner("STEP 3: Add Tagged Routes on DUT1")
        st.log(f"DUT1 Route 1: ip route {CONFIG.dut1_route1_prefix} {CONFIG.dut1_route1_nexthop} tag {CONFIG.dut1_route1_tag}")
        st.log(f"DUT1 Route 2: ip route {CONFIG.dut1_route2_prefix} {CONFIG.dut1_route2_nexthop} tag {CONFIG.dut1_route2_tag}")

        if not add_tagged_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop, CONFIG.dut1_route1_tag):
            st.report_tc_fail(TC_IDS.oc_sr13_tagged_route_add, "msg", "Failed to add DUT1 tagged route 1")
            result_flag = False

        if not add_tagged_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop, CONFIG.dut1_route2_tag):
            st.report_tc_fail(TC_IDS.oc_sr13_tagged_route_add, "msg", "Failed to add DUT1 tagged route 2")
            result_flag = False

        st.wait(3, "Waiting for DUT1 routes to be programmed")

        # ==================================================================
        # STEP 4: Add Tagged Routes on DUT2
        # ==================================================================
        st.banner("STEP 4: Add Tagged Routes on DUT2")
        st.log(f"DUT2 Route 1: ip route {CONFIG.dut2_route1_prefix} {CONFIG.dut2_route1_nexthop} tag {CONFIG.dut2_route1_tag}")
        st.log(f"DUT2 Route 2: ip route {CONFIG.dut2_route2_prefix} {CONFIG.dut2_route2_nexthop} tag {CONFIG.dut2_route2_tag}")
        st.log(f"DUT2 Route 3: ip route {CONFIG.dut2_route3_prefix} {CONFIG.dut2_route3_nexthop} tag {CONFIG.dut2_route3_tag}")

        if not add_tagged_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop, CONFIG.dut2_route1_tag):
            st.report_tc_fail(TC_IDS.oc_sr13_tagged_route_add, "msg", "Failed to add DUT2 tagged route 1")
            result_flag = False

        if not add_tagged_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop, CONFIG.dut2_route2_tag):
            st.report_tc_fail(TC_IDS.oc_sr13_tagged_route_add, "msg", "Failed to add DUT2 tagged route 2")
            result_flag = False

        if not add_tagged_route(vars.D2, CONFIG.dut2_route3_prefix, CONFIG.dut2_route3_nexthop, CONFIG.dut2_route3_tag):
            st.report_tc_fail(TC_IDS.oc_sr13_tagged_route_add, "msg", "Failed to add DUT2 tagged route 3")
            result_flag = False

        st.wait(3, "Waiting for DUT2 routes to be programmed")

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr13_tagged_route_add, "msg", "All tagged routes added successfully")
        else:
            st.report_fail("msg", "Tagged route addition failed - check logs")

        # ==================================================================
        # STEP 5: Verify Tagged Routes in Routing Tables
        # ==================================================================
        st.banner("STEP 5: Verify Tagged Routes in Routing Tables")
        st.log("⚠ Known Issue: Route tags NOT displayed in 'show ip route' output")
        st.log("Verifying routes exist (without tag visibility)...")

        # Verify DUT1 tagged routes (tags won't be visible)
        st.log("Verifying DUT1 tagged routes...")
        if not verify_tagged_route_in_routing_table(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop):
            st.error(f"DUT1: Route {CONFIG.dut1_route1_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route {CONFIG.dut1_route1_prefix} via {CONFIG.dut1_route1_nexthop} verified")

        if not verify_tagged_route_in_routing_table(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop):
            st.error(f"DUT1: Route {CONFIG.dut1_route2_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT1: Route {CONFIG.dut1_route2_prefix} via {CONFIG.dut1_route2_nexthop} verified")

        # Verify DUT2 tagged routes (tags won't be visible)
        st.log("Verifying DUT2 tagged routes...")
        if not verify_tagged_route_in_routing_table(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop):
            st.error(f"DUT2: Route {CONFIG.dut2_route1_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route1_prefix} via {CONFIG.dut2_route1_nexthop} verified")

        if not verify_tagged_route_in_routing_table(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop):
            st.error(f"DUT2: Route {CONFIG.dut2_route2_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route2_prefix} via {CONFIG.dut2_route2_nexthop} verified")

        if not verify_tagged_route_in_routing_table(vars.D2, CONFIG.dut2_route3_prefix, CONFIG.dut2_route3_nexthop):
            st.error(f"DUT2: Route {CONFIG.dut2_route3_prefix} verification failed")
            result_flag = False
        else:
            st.log(f"✓ DUT2: Route {CONFIG.dut2_route3_prefix} via {CONFIG.dut2_route3_nexthop} verified")

        # ==================================================================
        # STEP 6: Verify Tags in Running Configuration
        # ==================================================================
        st.banner("STEP 6: Verify Tags in Running Configuration")
        st.log("Tags ARE visible in running-configuration")

        # Verify DUT1 tags in running config
        st.log("Verifying DUT1 route tags in running-config...")
        if not verify_tagged_route_in_config(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop, CONFIG.dut1_route1_tag):
            st.error(f"DUT1: Route tag {CONFIG.dut1_route1_tag} not found in running-config")
            result_flag = False

        if not verify_tagged_route_in_config(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop, CONFIG.dut1_route2_tag):
            st.error(f"DUT1: Route tag {CONFIG.dut1_route2_tag} not found in running-config")
            result_flag = False

        # Verify DUT2 tags in running config
        st.log("Verifying DUT2 route tags in running-config...")
        if not verify_tagged_route_in_config(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop, CONFIG.dut2_route1_tag):
            st.error(f"DUT2: Route tag {CONFIG.dut2_route1_tag} not found in running-config")
            result_flag = False

        if not verify_tagged_route_in_config(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop, CONFIG.dut2_route2_tag):
            st.error(f"DUT2: Route tag {CONFIG.dut2_route2_tag} not found in running-config")
            result_flag = False

        if not verify_tagged_route_in_config(vars.D2, CONFIG.dut2_route3_prefix, CONFIG.dut2_route3_nexthop, CONFIG.dut2_route3_tag):
            st.error(f"DUT2: Route tag {CONFIG.dut2_route3_tag} not found in running-config")
            result_flag = False

        if result_flag:
            st.report_tc_pass(TC_IDS.oc_sr13_tagged_route_verify, "msg", "All tagged routes verified successfully")
        else:
            st.report_tc_fail(TC_IDS.oc_sr13_tagged_route_verify, "msg", "Tagged route verification failed")
            st.generate_tech_support([vars.D1, vars.D2], "oc_sr13_tagged_route_verify_failed")

        # ==================================================================
        # STEP 7: Remove Tagged Routes
        # ==================================================================
        st.banner("STEP 7: Remove Tagged Routes")

        # Remove DUT1 tagged routes
        st.log("Removing DUT1 tagged routes...")
        if not delete_tagged_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop, CONFIG.dut1_route1_tag):
            st.error(f"Failed to remove DUT1 route {CONFIG.dut1_route1_prefix}")
            result_flag = False

        if not delete_tagged_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop, CONFIG.dut1_route2_tag):
            st.error(f"Failed to remove DUT1 route {CONFIG.dut1_route2_prefix}")
            result_flag = False

        # Remove DUT2 tagged routes
        st.log("Removing DUT2 tagged routes...")
        if not delete_tagged_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop, CONFIG.dut2_route1_tag):
            st.error(f"Failed to remove DUT2 route {CONFIG.dut2_route1_prefix}")
            result_flag = False

        if not delete_tagged_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop, CONFIG.dut2_route2_tag):
            st.error(f"Failed to remove DUT2 route {CONFIG.dut2_route2_prefix}")
            result_flag = False

        if not delete_tagged_route(vars.D2, CONFIG.dut2_route3_prefix, CONFIG.dut2_route3_nexthop, CONFIG.dut2_route3_tag):
            st.error(f"Failed to remove DUT2 route {CONFIG.dut2_route3_prefix}")
            result_flag = False

        st.wait(3, "Waiting for route removal")

        # ==================================================================
        # STEP 8: Verify Routes Removed
        # ==================================================================
        st.banner("STEP 8: Verify Routes Removed from Routing Tables")

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
            st.report_tc_pass(TC_IDS.oc_sr13_tagged_route_remove, "msg", "All tagged routes removed successfully")
        else:
            st.report_tc_fail(TC_IDS.oc_sr13_tagged_route_remove, "msg", "Route removal verification failed")

    except Exception as e:
        st.error(f"Test execution error: {str(e)}")
        st.generate_tech_support([vars.D1, vars.D2], "oc_sr13_exception")
        result_flag = False

    finally:
        # Ensure cleanup runs even if test fails
        st.log("Ensuring cleanup executes...")

    # ==================================================================
    # TEST RESULT
    # ==================================================================
    st.banner("=" * 80)
    if result_flag:
        st.banner("TEST RESULT: OC-SR-13 PASSED")
        st.banner("=" * 80)
        st.log("TEST SUMMARY - OC-SR-13: IPv4 Static Route - Routes with Tags")
        st.log("  ✓ All interface IP addresses configured")
        st.log("  ✓ All tagged routes added successfully")
        st.log("  ✓ Routes verified in routing table (tags not displayed - known issue)")
        st.log("  ✓ Tags verified in running-configuration")
        st.log("  ✓ All routes removed successfully")
        st.log("  ✓ Route removal verified")
        st.log("")
        st.log("  ⚠ Known Issue: Route tags configured but NOT displayed in 'show ip route'")
        st.log("  ℹ  Tags ARE visible in 'show running-configuration'")
        st.report_pass("test_case_passed")
    else:
        st.banner("TEST RESULT: OC-SR-13 FAILED")
        st.banner("=" * 80)
        st.log("TEST SUMMARY - OC-SR-13: IPv4 Static Route - Routes with Tags")
        st.log("  ✗ Test failed - check logs for details")
        st.report_fail("test_case_failed")
