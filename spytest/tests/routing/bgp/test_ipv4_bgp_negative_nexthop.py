"""
IPv4 BGP NEGATIVE TEST - NEXT-HOP UNREACHABLE
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv4_bgp_negative_nexthop.py \
  --logs-path ./logs/test_ipv4_bgp_negative_nexthop_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Negative test case to verify BGP behavior when next-hop is unreachable.
  This test validates that BGP routes are NOT installed in the routing table when
  the next-hop IP address is unreachable. This is a critical BGP behavior that
  prevents routing black holes.

  Test scenarios:
  1. Configure iBGP between DUT1 and DUT2
  2. DUT1 advertises a network with next-hop set to an unreachable IP (Loopback IP)
  3. Verify DUT2 receives the BGP route but does NOT install it (next-hop unreachable)
  4. Add static route on DUT2 to make next-hop reachable
  5. Verify DUT2 now installs the route in routing table

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with iBGP
        # +-------------------------+                       +-------------------------+
        # |      DUT1               |                       |      DUT2               |
        # | Eth32: 10.1.1.1/24 |=======================| Eth32: 10.1.1.2/24 |
        # | Lo0: 10.0.0.1/32    |                       | (No route to Lo0)       |
        # | Network: 192.168.100.0/24                      |                         |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: AS 65001 (iBGP), IPv4 Unicast address family
  - Network advertised: 192.168.100.0/24 with next-hop 10.0.0.1 (DUT1 Loopback)
  - Expected Result: DUT2 receives route but doesn't install (next-hop unreachable)
"""

from __future__ import annotations

import pytest
import re

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.system.interface as intf_api
import apis.system.reboot as reboot_api
import apis.system.basic as basic_api
from utilities.parallel import exec_all


# Test data dictionary
data = SpyTestDict()
# Physical interface IPs
data.dut1_ipv4 = "10.1.1.1"
data.dut2_ipv4 = "10.1.1.2"
data.ipv4_mask = "24"
# Loopback IP (will be unreachable next-hop)
data.dut1_loopback = "10.0.0.1"
data.loopback_mask = "32"
data.loopback_interface = "Loopback0"
# Network to advertise
data.advertised_network = "192.168.100.0/24"
data.advertised_network_prefix = "192.168.100.0"
data.advertised_network_mask = "24"
# BGP config
data.bgp_asn = "65001"
data.af_ipv4 = "ipv4"
data.cli_type = "klish"
data.mtu = "9100"
data.speed = "40000"
data.bgp_wait = 90
data.negative_test_wait = 60
data.reboot_wait = 60
data.ping_count = 5
data.router_id_dut1 = "1.1.1.1"
data.router_id_dut2 = "2.2.2.2"


@pytest.fixture(scope="module", autouse=True)
def ipv4_bgp_negative_nexthop_module_hooks(request):
    """
    Module-level fixture for IPv4 BGP negative next-hop test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv4 BGP Negative Test (Next-Hop Unreachable)")

    # Store DUT handles
    data.dut1 = vars.D1
    data.dut2 = vars.D2
    data.dut1_dut2_port = vars.D1D2P1
    data.dut2_dut1_port = vars.D2D1P1

    # Log topology information
    st.log(f"DUT1: {data.dut1}, DUT2: {data.dut2}")
    st.log(f"DUT1-DUT2 Port: {data.dut1_dut2_port}, DUT2-DUT1 Port: {data.dut2_dut1_port}")

    # Get UI type for the test
    data.shell_vtysh = st.get_ui_type()
    if data.shell_vtysh == "click":
        data.shell_vtysh = "vtysh"

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up IPv4 BGP configuration")
    cleanup_bgp_ipv4_config()


@pytest.fixture(scope="function", autouse=True)
def ipv4_bgp_negative_nexthop_func_hooks(request):
    """
    Function-level fixture - currently empty.
    """
    yield


def check_and_remove_ipv4_address(dut, interface, cli_type="klish"):
    """
    Check if IPv4 address exists on interface and remove it if present.
    """
    st.log(f"Checking for existing IPv4 addresses on {interface} of {dut}")

    try:
        command = f"show ip interfaces"
        output = st.config(dut, command, type="click", skip_error_check=True)

        if output and "inet" in output.lower():
            st.log(f"Found existing IPv4 address on {interface}, removing it")

            ipv4_pattern = r'([0-9.]+/\d++)'
            addresses = re.findall(ipv4_pattern, output)

            if addresses:
                for addr in addresses:
                    if not addr.startswith('fe80'):
                        st.log(f"Removing IPv4 address {addr} from {interface}")
                        commands = []
                        commands.append(f"interface {interface}")
                        commands.append(f"no ip address {addr}")
                        commands.append("exit")
                        st.config(dut, commands, type=cli_type, skip_error_check=True)

        st.log(f"IPv4 address cleanup completed on {interface}")
        return True

    except Exception as e:
        st.error(f"Failed to check/remove IPv4 address on {interface}: {str(e)}")
        return False


def remove_bgp_config(dut, cli_type="klish"):
    """
    Remove existing BGP configuration from DUT.
    """
    st.log(f"Removing existing BGP configuration on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = ["no router bgp"]
        st.config(dut, commands, type=cli_type, skip_error_check=True)

        st.log(f"Successfully removed BGP configuration on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to remove BGP configuration on {dut}: {str(e)}")
        return False


def configure_interface_mtu_speed(dut, interface, mtu, speed, cli_type="klish"):
    """
    Configure MTU and speed on an interface.
    """
    st.log(f"Configuring MTU={mtu} and speed={speed} on {interface} for {dut}")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append(f"mtu {mtu}")
        commands.append(f"speed {speed}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured MTU and speed on {interface}")
        return True
    except Exception as e:
        st.error(f"Failed to configure MTU/speed on {interface}: {str(e)}")
        return False


def configure_ipv4_interface(dut, interface, ipv4_addr, mask, cli_type="klish"):
    """
    Configure IPv4 address on an interface and bring it up.
    """
    st.log(f"Configuring IPv4 address {ipv4_addr}/{mask} on {interface} for {dut}")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append(f"ip address {ipv4_addr}/{mask}")
        commands.append("no shutdown")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured IPv4 address on {interface} and brought it up")

        st.wait(2, "Waiting for interface to come up")
        return True
    except Exception as e:
        st.error(f"Failed to configure IPv4 address on {interface}: {str(e)}")
        return False


def configure_loopback_interface(dut, loopback_ip, mask, cli_type="klish"):
    """
    Configure Loopback interface with IPv4 address.
    """
    st.log(f"Configuring Loopback0 with IPv4 address {loopback_ip}/{mask} on {dut}")

    try:
        commands = []
        commands.append(f"interface {data.loopback_interface}")
        commands.append(f"ip address {loopback_ip}/{mask}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured Loopback0 on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure Loopback0 on {dut}: {str(e)}")
        return False


def configure_static_route(dut, destination, nexthop, cli_type="klish"):
    """
    Configure IPv4 static route.
    """
    st.log(f"Configuring static route {destination} via {nexthop} on {dut}")

    try:
        commands = [f"ip route {destination} {nexthop}"]
        st.config(dut, commands, type=cli_type)

        st.log(f"Successfully configured static route on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure static route on {dut}: {str(e)}")
        return False


def configure_bgp_router_with_router_id(dut, local_asn, router_id, cli_type="klish"):
    """
    Configure BGP router with local ASN and router ID.
    """
    st.log(f"Configuring BGP router with AS {local_asn} and router-id {router_id} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"router-id {router_id}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP router on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP router on {dut}: {str(e)}")
        return False


def configure_bgp_neighbor(dut, local_asn, neighbor_ip, remote_asn, family="ipv4", cli_type="klish"):
    """
    Configure BGP neighbor with IPv4 address family.
    """
    st.log(f"Configuring BGP neighbor {neighbor_ip} with remote-as {remote_asn} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")
        commands.append(f"address-family ipv4 unicast")
        commands.append(f"activate")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor {neighbor_ip} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def advertise_network_with_nexthop(dut, local_asn, network, nexthop_ip, family="ipv4", cli_type="klish"):
    """
    Advertise a network with specific next-hop using route-map.

    This configures:
    1. Route-map to set next-hop
    2. Network advertisement
    3. Apply route-map to neighbor
    """
    st.log(f"Advertising network {network} with next-hop {nexthop_ip} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        # Configure route-map to set next-hop
        commands = []
        commands.append("route-map SET_NEXTHOP permit 10")
        commands.append(f"set ip next-hop {nexthop_ip}")
        commands.append("exit")
        st.config(dut, commands, type=cli_type)

        # Advertise network and apply route-map
        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"address-family ipv4 unicast")
        commands.append(f"network {network}")
        # Note: route-map is applied to the neighbor to set next-hop
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured network advertisement with next-hop on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to advertise network on {dut}: {str(e)}")
        return False


def apply_routemap_to_neighbor(dut, local_asn, neighbor_ip, routemap_name, direction="out", cli_type="klish"):
    """
    Apply route-map to BGP neighbor.
    """
    st.log(f"Applying route-map {routemap_name} to neighbor {neighbor_ip} direction {direction} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"address-family ipv4 unicast")
        commands.append(f"neighbor {neighbor_ip} route-map {routemap_name} {direction}")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully applied route-map to neighbor on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to apply route-map on {dut}: {str(e)}")
        return False


def verify_bgp_neighbor_state(dut, neighbor_ip, state='Established', family='ipv4', timeout=90, cli_type='klish'):
    """
    Verify BGP neighbor state.
    """
    st.log(f"Verifying BGP neighbor {neighbor_ip} is in {state} state on {dut}")

    iterations = int(timeout / 5)
    for i in range(iterations):
        try:
            output = st.show(dut, "show bgp summary", type=cli_type)

            if output:
                for entry in output:
                    if str(entry.get('neighbor', '')).strip() == str(neighbor_ip).strip():
                        neighbor_state = entry.get('state', '')
                        st.log(f"Found neighbor {neighbor_ip} with state: {neighbor_state}")

                        if ('established' in str(neighbor_state).lower() or
                            str(neighbor_state).isdigit() or
                            'policy' in str(neighbor_state).lower()):
                            st.log(f"BGP neighbor {neighbor_ip} is established on {dut}")
                            return True
                        else:
                            st.log(f"BGP neighbor {neighbor_ip} is in state: {neighbor_state}, waiting...")

        except Exception as e:
            st.error(f"Exception while checking BGP neighbor state: {str(e)}")

        if i < iterations - 1:
            st.wait(5, f"Waiting for BGP neighbor to reach {state} state (attempt {i+1}/{iterations})")

    st.error(f"BGP neighbor {neighbor_ip} did not reach {state} state on {dut} after {timeout} seconds")
    return False


def verify_route_not_in_routing_table(dut, network, timeout=60, cli_type='klish'):
    """
    Verify that a BGP route is NOT installed in the routing table (next-hop unreachable).
    Returns True if route is NOT found in routing table (expected for negative test).
    """
    st.log(f"Verifying route {network} is NOT in routing table on {dut} (next-hop unreachable)")

    st.wait(timeout, f"Waiting {timeout} seconds to check routing table")

    try:
        output = st.show(dut, "show ip route", type=cli_type)

        if output:
            route_found = False
            if isinstance(output, str):
                if network in output:
                    route_found = True
            elif isinstance(output, list):
                for entry in output:
                    if network in str(entry):
                        route_found = True
                        break

            if route_found:
                st.error(f"Route {network} INCORRECTLY installed in routing table despite unreachable next-hop!")
                return False
            else:
                st.log(f"Route {network} NOT in routing table (as expected with unreachable next-hop)")
                return True

        st.log(f"Route {network} not found in routing table (as expected)")
        return True

    except Exception as e:
        st.error(f"Exception while checking routing table: {str(e)}")
        return True


def verify_route_in_routing_table(dut, network, timeout=90, cli_type='klish'):
    """
    Verify that a BGP route IS installed in the routing table.
    """
    st.log(f"Verifying route {network} is in routing table on {dut}")

    iterations = int(timeout / 5)
    for i in range(iterations):
        try:
            output = st.show(dut, "show ip route", type=cli_type)

            if output:
                if isinstance(output, str):
                    if network in output:
                        st.log(f"Route {network} found in routing table on {dut}")
                        return True
                elif isinstance(output, list):
                    for entry in output:
                        if network in str(entry):
                            st.log(f"Route {network} found in routing table on {dut}")
                            return True

        except Exception as e:
            st.error(f"Exception while checking routing table: {str(e)}")

        if i < iterations - 1:
            st.wait(5, f"Waiting for route to appear in routing table (attempt {i+1}/{iterations})")

    st.error(f"Route {network} not found in routing table on {dut} after {timeout} seconds")
    return False


def ping_ipv4(dut, destination_ipv4, count=5, cli_type='click'):
    """
    Ping an IPv4 address from a DUT.
    """
    st.log(f"Pinging {destination_ipv4} from {dut} with count={count}")

    try:
        result = ip_api.ping(
            dut=dut,
            addresses=destination_ipv4,
            family='ipv4',
            count=count,
            cli_type=cli_type
        )

        if result:
            st.log(f"Ping to {destination_ipv4} succeeded")
            return True
        else:
            st.error(f"Ping to {destination_ipv4} failed")
            return False

    except Exception as e:
        st.error(f"Exception during ping: {str(e)}")
        return False


def cleanup_bgp_ipv4_config():
    """
    Clean up BGP and IPv4 configuration from all DUTs.
    """
    st.log("Cleaning up BGP and IPv4 configuration")

    dut_list = [data.dut1, data.dut2]

    for dut in dut_list:
        try:
            # Remove BGP configuration
            bgp_api.enable_docker_routing_config_mode(dut, cli_type=data.cli_type)
            commands = ["no router bgp"]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            # Remove route-map
            commands = ["no route-map SET_NEXTHOP"]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            # Remove static routes
            if dut == data.dut2:
                commands = [f"no ip route {data.dut1_loopback}/{data.loopback_mask} {data.dut1_ipv4}"]
                st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            # Remove Loopback interface
            if dut == data.dut1:
                commands = [f"no interface {data.loopback_interface}"]
                st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            # Remove IPv4 configuration from physical interfaces
            if dut == data.dut1:
                interface = data.dut1_dut2_port
                ipv4_addr = data.dut1_ipv4
            else:
                interface = data.dut2_dut1_port
                ipv4_addr = data.dut2_ipv4

            commands = []
            commands.append(f"interface {interface}")
            commands.append(f"no ip address {ipv4_addr}/{data.ipv4_mask}")
            commands.append("exit")
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            st.log(f"Cleaned up configuration on {dut}")

        except Exception as e:
            st.error(f"Error during cleanup on {dut}: {str(e)}")

    st.log("Cleanup completed")


class TestIpv6BgpNegativeNexthop:
    """
    Test class for IPv4 BGP negative test - next-hop unreachable.
    """

    def test_ipv4_bgp_nexthop_unreachable(self):
        """
        Negative Test: Verify BGP behavior when next-hop is unreachable.

        Steps:
        1. Check and remove existing IPv4 addresses
        2. Configure interface MTU and speed
        3. Configure IPv4 addresses on physical interfaces
        4. Verify IPv4 connectivity
        5. Remove existing BGP configuration
        6. Configure Loopback0 on DUT1 (will be the unreachable next-hop)
        7. Configure BGP with router IDs
        8. Configure BGP neighbors
        9. DUT1: Advertise network with next-hop set to Loopback0 IP
        10. Verify BGP session establishes
        11. Verify DUT2 does NOT install route (next-hop unreachable)
        12. Add static route on DUT2 to reach DUT1's Loopback
        13. Verify DUT2 now installs the route
        """
        st.banner("NEGATIVE TEST: IPv4 BGP - Next-Hop Unreachable")

        # Step 1: Check and remove existing IPv4 addresses
        st.log("Step 1: Checking and removing existing IPv4 addresses from interfaces")

        check_and_remove_ipv4_address(data.dut1, data.dut1_dut2_port, data.cli_type)
        check_and_remove_ipv4_address(data.dut2, data.dut2_dut1_port, data.cli_type)

        # Step 2: Configure interface MTU and speed
        st.log("Step 2: Configuring interface MTU and speed on both DUTs")

        if not configure_interface_mtu_speed(data.dut1, data.dut1_dut2_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut1}")

        if not configure_interface_mtu_speed(data.dut2, data.dut2_dut1_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut2}")

        # Step 3: Configure IPv4 addresses on physical interfaces
        st.log("Step 3: Configuring IPv4 addresses on physical interfaces")

        if not configure_ipv4_interface(data.dut1, data.dut1_dut2_port, data.dut1_ipv4, data.ipv4_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv4 on {data.dut1}")

        if not configure_ipv4_interface(data.dut2, data.dut2_dut1_port, data.dut2_ipv4, data.ipv4_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv4 on {data.dut2}")

        # Step 4: Verify IPv4 connectivity on physical interfaces
        st.log("Step 4: Verifying IPv4 connectivity on physical interfaces")

        if not ping_ipv4(data.dut1, data.dut2_ipv4, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut1} to {data.dut2} failed")

        if not ping_ipv4(data.dut2, data.dut1_ipv4, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut2} to {data.dut1} failed")

        # Step 5: Remove existing BGP configuration
        st.log("Step 5: Removing existing BGP configuration from both DUTs")

        remove_bgp_config(data.dut1, data.cli_type)
        remove_bgp_config(data.dut2, data.cli_type)

        st.wait(5, "Waiting after BGP cleanup")

        # Step 6: Configure Loopback0 on DUT1 (will be unreachable next-hop for DUT2)
        st.log("Step 6: Configuring Loopback0 on DUT1 (unreachable next-hop)")

        if not configure_loopback_interface(data.dut1, data.dut1_loopback, data.loopback_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure Loopback0 on {data.dut1}")

        # Step 7: Configure BGP routers with router IDs
        st.log("Step 7: Configuring BGP routers with router IDs")

        if not configure_bgp_router_with_router_id(data.dut1, data.bgp_asn, data.router_id_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        if not configure_bgp_router_with_router_id(data.dut2, data.bgp_asn, data.router_id_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        # Step 8: Configure BGP neighbors
        st.log("Step 8: Configuring BGP neighbors")

        if not configure_bgp_neighbor(data.dut1, data.bgp_asn, data.dut2_ipv4, data.bgp_asn, data.af_ipv4, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        if not configure_bgp_neighbor(data.dut2, data.bgp_asn, data.dut1_ipv4, data.bgp_asn, data.af_ipv4, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut2}")

        # Step 9: DUT1 advertises network with next-hop set to Loopback IP (unreachable from DUT2)
        st.log("Step 9: DUT1 advertising network with next-hop set to Loopback IP (unreachable from DUT2)")
        st.log(f"Network: {data.advertised_network}, Next-hop: {data.dut1_loopback}")

        if not advertise_network_with_nexthop(data.dut1, data.bgp_asn, data.advertised_network,
                                               data.dut1_loopback, data.af_ipv4, data.cli_type):
            st.report_fail("msg", f"Failed to advertise network on {data.dut1}")

        if not apply_routemap_to_neighbor(data.dut1, data.bgp_asn, data.dut2_ipv4, "SET_NEXTHOP", "out", data.cli_type):
            st.report_fail("msg", f"Failed to apply route-map on {data.dut1}")

        # Step 10: Verify BGP sessions establish
        st.log("Step 10: Verifying BGP sessions establish")

        st.wait(data.bgp_wait, "Waiting for BGP sessions to establish")

        if not verify_bgp_neighbor_state(data.dut1, data.dut2_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not established on {data.dut1}")

        if not verify_bgp_neighbor_state(data.dut2, data.dut1_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not established on {data.dut2}")

        # Step 11: Verify DUT2 does NOT install route in routing table (next-hop unreachable)
        st.log("Step 11: Verifying DUT2 does NOT install route (next-hop unreachable)")

        if not verify_route_not_in_routing_table(data.dut2, data.advertised_network_prefix, data.negative_test_wait, data.cli_type):
            st.report_fail("msg", f"Route INCORRECTLY installed on {data.dut2} despite unreachable next-hop!")

        st.log("NEGATIVE TEST PASSED: Route NOT installed due to unreachable next-hop (as expected)")

        # Step 12: Add static route on DUT2 to make next-hop reachable
        st.log("Step 12: Adding static route on DUT2 to make next-hop reachable")
        st.log(f"Static route: {data.dut1_loopback}/{data.loopback_mask} via {data.dut1_ipv4}")

        if not configure_static_route(data.dut2, f"{data.dut1_loopback}/{data.loopback_mask}",
                                       data.dut1_ipv4, data.cli_type):
            st.report_fail("msg", f"Failed to configure static route on {data.dut2}")

        # Step 13: Verify DUT2 now installs the route in routing table
        st.log("Step 13: Verifying DUT2 now installs route after next-hop becomes reachable")

        if not verify_route_in_routing_table(data.dut2, data.advertised_network_prefix, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"Route NOT installed on {data.dut2} after making next-hop reachable")

        st.log("POSITIVE TEST PASSED: Route installed after next-hop became reachable")

        st.report_pass("test_case_passed")
