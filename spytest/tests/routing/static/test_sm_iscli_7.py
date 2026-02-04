"""
SM_ISCLI_7 - Static Route Installation Verification (IS-CLI/Klish)
Author: Athira
2026

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  routing/static/test_sm_iscli_7.py \
  --logs-path ./logs/test_sm_iscli_7_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Automates bug fix verification for SM_ISCLI_7. The original bug reported static
  routes configured via IS-CLI (klish) were not appearing in the FRR routing table.
  This test verifies routes are properly installed with correct state (S>*) after
  the fix was implemented in SONiC.202505-smci-dev-iscli-2026-01-27.

Pre-requisites:
  - Topology: Single DUT (D1) or connected to DUT2 | Supported: HW and Virtual
  - Minimum SONiC version: 202505-smci-dev-iscli with SM_ISCLI_7 fix
  - Test interface: Auto-detected from testbed topology (fallback: Ethernet32)
  - Interface IP: 10.1.1.1/24, Next-hop: 10.1.1.2
  - For proper testing, ensure next-hop is reachable via connected interface
"""

from __future__ import annotations

import pytest

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api
import apis.system.interface as intf_api

# Test configuration - interface will be read from testbed
DEFAULT_CLI_TYPE = "klish"
DEFAULT_INTERFACE_IP = "10.1.1.1"
DEFAULT_INTERFACE_SUBNET = "24"
DEFAULT_NEXT_HOP_IP = "10.1.1.2"

# Test routes based on verified scenario
TEST_ROUTE_NEXTHOP = "2.2.2.0/24"
TEST_ROUTE_INTERFACE = "3.3.3.0/24"
TEST_ROUTE_HOST = "2.2.2.2/32"

vars = SpyTestDict()
data = SpyTestDict()


@pytest.fixture(scope="module", autouse=True)
def sm_iscli_7_module_hooks(request):
    """Module level setup and teardown"""
    global vars, data

    st.banner("SM_ISCLI_7 MODULE PROLOGUE: Starting")

    # Get device from testbed
    try:
        vars = st.get_testbed_vars()
        data.dut = vars.D1
    except Exception as e:
        pytest.skip(f"Unable to get testbed device: {e}")

    data.cli_type = DEFAULT_CLI_TYPE

    # Get test interface from testbed topology
    # Try to get the first connected interface from topology
    data.test_interface = None
    try:
        # Get all interfaces that have connections in topology
        topo_data = st.get_tg_topology()
        if hasattr(vars, 'D1D2P1'):
            # If D1 is connected to D2, use that interface
            data.test_interface = vars.D1D2P1
            st.log(f"Using D1D2P1 interface: {data.test_interface}")
        elif 'dut_list' in topo_data and data.dut in topo_data['dut_list']:
            # Get first available interface from DUT's connections
            dut_links = st.get_dut_links(data.dut)
            if dut_links:
                data.test_interface = dut_links[0]
                st.log(f"Using first available link: {data.test_interface}")
    except Exception as e:
        st.log(f"Could not auto-detect interface from topology: {e}")

    # Fallback: Use Ethernet32 as default if not found in topology
    if not data.test_interface:
        data.test_interface = "Ethernet32"
        st.log(f"Using default interface: {data.test_interface}")

    data.interface_ip = DEFAULT_INTERFACE_IP
    data.interface_subnet = DEFAULT_INTERFACE_SUBNET
    data.next_hop = DEFAULT_NEXT_HOP_IP
    data.configured_routes = []

    st.log(f"Testing on DUT: {data.dut}")
    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"Test Interface: {data.test_interface}")
    st.log(f"Interface IP: {data.interface_ip}/{data.interface_subnet}")
    st.log(f"Next-hop IP: {data.next_hop}")

    yield

    # Cleanup
    st.banner("SM_ISCLI_7 MODULE EPILOGUE: Cleanup")
    cleanup_all_routes()
    cleanup_interface()


def cleanup_interface():
    """Remove IP address from test interface"""
    try:
        st.log(f"Cleaning up interface {data.test_interface}")
        intf_api.clear_interface_config(data.dut, [data.test_interface])
    except Exception as e:
        st.warn(f"Interface cleanup failed: {e}")


def cleanup_all_routes():
    """Remove all configured static routes"""
    st.log("Removing all configured static routes")
    for route_info in data.configured_routes:
        try:
            ip_api.delete_static_route(
                data.dut,
                static_ip=route_info["destination"],
                next_hop=route_info.get("next_hop"),
                interface=route_info.get("interface"),
                family="ipv4",
                cli_type=data.cli_type
            )
        except Exception as e:
            st.warn(f"Failed to remove route {route_info['destination']}: {e}")
    data.configured_routes = []


def configure_test_interface():
    """Configure IP address on test interface"""
    st.log(f"Configuring {data.interface_ip}/{data.interface_subnet} on {data.test_interface}")
    result = ip_api.config_ip_addr_interface(
        data.dut,
        data.test_interface,
        data.interface_ip,
        subnet=data.interface_subnet,
        family="ipv4",
        cli_type=data.cli_type
    )
    if not result:
        st.report_fail("msg", f"Failed to configure IP on {data.test_interface}")
    st.wait(2, "Wait for interface configuration to settle")


def create_and_track_route(destination, next_hop=None, interface=None):
    """Create static route and track it for cleanup"""
    st.log(f"Creating static route {destination} via {next_hop or interface}")

    result = ip_api.create_static_route(
        data.dut,
        static_ip=destination,
        next_hop=next_hop,
        interface=interface,
        family="ipv4",
        cli_type=data.cli_type
    )

    if result:
        data.configured_routes.append({
            "destination": destination,
            "next_hop": next_hop,
            "interface": interface
        })
        st.log(f"Successfully created route {destination}")
    else:
        st.error(f"Failed to create route {destination}")

    return result


def verify_route_in_table(destination, next_hop=None, interface=None, should_exist=True):
    """Verify static route appears in routing table with correct state (S>*)"""
    st.log(f"Verifying route {destination} in routing table")

    def _check_route_exists():
        """Check if route exists with S>* flags in routing table"""
        try:
            # Get all routes from routing table
            routes = ip_api.show_ip_route(data.dut, family="ipv4", cli_type=data.cli_type)

            if not routes:
                st.log("No routes returned from show_ip_route")
                return False

            st.log(f"Total routes in table: {len(routes)}, looking for: {destination}")

            # Look for our destination in the route entries
            for route_entry in routes:
                route_ip = route_entry.get("ip_address", "")

                # Match destination (normalize format)
                if route_ip == destination or route_ip.split("/")[0] == destination.split("/")[0]:
                    st.log(f"Found route entry for {destination}: {route_entry}")

                    # TextFSM parses S>* into separate fields:
                    # type='S', selected='>', fib='*'
                    route_type = route_entry.get("type", "")
                    route_selected = route_entry.get("selected", "")
                    route_fib = route_entry.get("fib", "")

                    st.log(f"Route flags - type:'{route_type}' selected:'{route_selected}' fib:'{route_fib}'")

                    # Verify flags: S (static), > (selected), * (in FIB)
                    if route_type != 'S':
                        st.log(f"Route type is '{route_type}', expected 'S' (static)")
                        continue

                    if route_selected != '>':
                        st.log(f"Route not selected (missing '>'), selected field: '{route_selected}'")
                        continue

                    if route_fib != '*':
                        st.log(f"Route not in FIB (missing '*'), fib field: '{route_fib}'")
                        continue

                    st.log(f"Route has correct flags: S (static), > (selected), * (FIB)")

                    # If next_hop specified, verify it matches
                    if next_hop:
                        route_nexthop = route_entry.get("nexthop", "")
                        if next_hop not in str(route_nexthop):
                            st.log(f"Next-hop mismatch: expected {next_hop}, got {route_nexthop}")
                            continue
                        st.log(f"Next-hop verified: {next_hop}")

                    # If interface specified, verify it matches
                    if interface:
                        route_interface = route_entry.get("interface", "")
                        if interface not in str(route_interface):
                            st.log(f"Interface mismatch: expected {interface}, got {route_interface}")
                            continue
                        st.log(f"Interface verified: {interface}")

                    # All checks passed
                    st.log(f"Route {destination} verified with S>* flags and correct attributes")
                    return True

            st.log(f"Route {destination} not found with required S>* flags")
            return False

        except Exception as e:
            st.error(f"Error checking route: {e}")
            import traceback
            st.error(f"Traceback: {traceback.format_exc()}")
            return False

    # Poll for route to appear/disappear
    if should_exist:
        if not st.poll_wait(_check_route_exists, 30):
            st.error(f"Route {destination} not found in routing table after 30s")
            return False
        st.log(f"Route {destination} verified in routing table")
    else:
        # Route should NOT exist
        def _check_absent():
            return not _check_route_exists()

        if not st.poll_wait(_check_absent, 30):
            st.error(f"Route {destination} still present in routing table after removal")
            return False
        st.log(f"Route {destination} confirmed absent from routing table")

    return True


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_7_TC1"])
@pytest.mark.sm_iscli_7
def test_sm_iscli_7_tc1_static_route_nexthop():
    """
    SM_ISCLI_7_TC1: Verify static route via next-hop IP appears in routing table

    Scenario:
      1. Configure interface with IP address (10.1.1.1/24 on Ethernet32)
      2. Configure static route with next-hop IP (2.2.2.0/24 via 10.1.1.2)
      3. Verify route appears in routing table as S>*
      4. Remove route and verify removal
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_7_TC1: Static Route via Next-Hop IP")
    st.log("=" * 80)

    # Step 1: Configure interface
    configure_test_interface()

    # Step 2: Create static route
    if not create_and_track_route(TEST_ROUTE_NEXTHOP, next_hop=data.next_hop):
        st.report_fail("msg", f"Failed to create static route {TEST_ROUTE_NEXTHOP}")

    # Step 3: Verify route in table (next-hop routes also show egress interface)
    if not verify_route_in_table(TEST_ROUTE_NEXTHOP, next_hop=data.next_hop, interface=data.test_interface):
        st.report_fail("msg", f"Static route {TEST_ROUTE_NEXTHOP} not in routing table")

    # Step 4: Remove route
    st.log(f"Removing static route {TEST_ROUTE_NEXTHOP}")
    ip_api.delete_static_route(
        data.dut,
        static_ip=TEST_ROUTE_NEXTHOP,
        next_hop=data.next_hop,
        family="ipv4",
        cli_type=data.cli_type
    )

    # Step 5: Verify removal
    if not verify_route_in_table(TEST_ROUTE_NEXTHOP, should_exist=False):
        st.report_fail("msg", f"Route {TEST_ROUTE_NEXTHOP} not removed from routing table")

    st.report_pass("test_case_passed")


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_7_TC2"])
@pytest.mark.sm_iscli_7
def test_sm_iscli_7_tc2_static_route_interface():
    """
    SM_ISCLI_7_TC2: Verify static route via interface appears in routing table

    Scenario:
      1. Configure interface with IP address (10.1.1.1/24 on Ethernet32)
      2. Configure static route via interface (3.3.3.0/24 via Ethernet32)
      3. Verify route appears as directly connected (S>*)
      4. Remove route and verify removal
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_7_TC2: Static Route via Interface")
    st.log("=" * 80)

    # Step 1: Configure interface (already done in TC1, but verify)
    configure_test_interface()

    # Step 2: Create static route via interface
    if not create_and_track_route(TEST_ROUTE_INTERFACE, interface=data.test_interface):
        st.report_fail("msg", f"Failed to create static route {TEST_ROUTE_INTERFACE}")

    # Step 3: Verify route in table
    if not verify_route_in_table(TEST_ROUTE_INTERFACE, interface=data.test_interface):
        st.report_fail("msg", f"Static route {TEST_ROUTE_INTERFACE} not in routing table")

    # Step 4: Remove route
    st.log(f"Removing static route {TEST_ROUTE_INTERFACE}")
    ip_api.delete_static_route(
        data.dut,
        static_ip=TEST_ROUTE_INTERFACE,
        interface=data.test_interface,
        family="ipv4",
        cli_type=data.cli_type
    )

    # Step 5: Verify removal
    if not verify_route_in_table(TEST_ROUTE_INTERFACE, should_exist=False):
        st.report_fail("msg", f"Route {TEST_ROUTE_INTERFACE} not removed from routing table")

    st.report_pass("test_case_passed")


@pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_7_TC3"])
@pytest.mark.sm_iscli_7
def test_sm_iscli_7_tc3_host_route():
    """
    SM_ISCLI_7_TC3: Verify /32 host route appears in routing table

    Scenario:
      1. Configure interface with IP address (10.1.1.1/24 on Ethernet32)
      2. Configure /32 host route (2.2.2.2/32 via 10.1.1.2)
      3. Verify route appears in routing table as S>*
    """
    st.log("=" * 80)
    st.banner("SM_ISCLI_7_TC3: Static /32 Host Route")
    st.log("=" * 80)

    # Configure interface
    configure_test_interface()

    # Create /32 host route
    if not create_and_track_route(TEST_ROUTE_HOST, next_hop=data.next_hop):
        st.report_fail("msg", f"Failed to create host route {TEST_ROUTE_HOST}")

    # Verify route in table (host routes with next-hop also show egress interface)
    if not verify_route_in_table(TEST_ROUTE_HOST, next_hop=data.next_hop, interface=data.test_interface):
        st.report_fail("msg", f"Host route {TEST_ROUTE_HOST} not in routing table")

    st.report_pass("test_case_passed")
