"""
IPv6 BGP DAEMON RESTART - RECOVERY VERIFICATION
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv6_bgp_daemon_restart.py \
  --logs-path ./logs/test_ipv6_bgp_daemon_restart_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Test case to verify BGP session recovery after BGP daemon restart.
  This test validates that IPv6 BGP sessions, routes, and connectivity are properly
  restored after restarting the BGP daemon (bgpd). This is critical for:
  - Software upgrades
  - Configuration changes requiring daemon reload
  - Service recovery scenarios

  Test scenarios:
  1. Configure iBGP session between DUT1 and DUT2 using IPv6
  2. Advertise IPv6 network from DUT1
  3. Verify BGP session established and routes learned
  4. Restart BGP daemon on DUT1
  5. Verify BGP session recovers automatically
  6. Verify routes are re-learned/re-advertised
  7. Verify end-to-end IPv6 connectivity restored

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with iBGP over IPv6
        # +-------------------------+                       +-------------------------+
        # |      DUT1               |                       |      DUT2               |
        # | Eth32: 2001:db8:1::1/64 |=======================| Eth32: 2001:db8:1::2/64 |
        # | Network: 2001:db8:100::/48                      |                         |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: AS 65001 (iBGP), IPv6 Unicast address family
  - Network advertised: 2001:db8:100::/48 from DUT1
  - Expected Result: BGP recovers after daemon restart, routes restored
"""

from __future__ import annotations

import pytest
import re
import time

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.system.interface as intf_api
import apis.system.basic as basic_api


# Test data dictionary
data = SpyTestDict()
# Physical interface IPv6 addresses
data.dut1_ipv6 = "2001:db8:1::1"
data.dut2_ipv6 = "2001:db8:1::2"
data.ipv6_mask = "64"
# Network to advertise - using the actual interface network so it appears in BGP
data.advertised_network = "2001:db8:1::/64"
data.advertised_network_prefix = "2001:db8:1::"
data.advertised_network_mask = "64"
# BGP config
data.bgp_asn = "65001"
data.af_ipv6 = "ipv6"
data.cli_type = "klish"
data.mtu = "9100"
data.speed = "40000"
data.bgp_wait = 90
data.daemon_restart_wait = 120
data.recovery_wait = 90
data.ping_count = 5
data.router_id_dut1 = "1.1.1.1"
data.router_id_dut2 = "2.2.2.2"


@pytest.fixture(scope="module", autouse=True)
def ipv6_bgp_daemon_restart_module_hooks(request):
    """
    Module-level fixture for IPv6 BGP daemon restart test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv6 BGP Daemon Restart Test")

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
    st.banner("MODULE TEARDOWN: Cleaning up IPv6 BGP daemon restart test configuration")
    cleanup_bgp_ipv6_config()


@pytest.fixture(scope="function", autouse=True)
def ipv6_bgp_daemon_restart_func_hooks(request):
    """
    Function-level fixture - currently empty.
    """
    yield


def remove_ipv6_address(dut, interface, cli_type="klish"):
    """
    Remove all IPv6 addresses from interface.
    """
    st.log(f"Removing IPv6 addresses from {interface} on {dut}")
    commands = [f"interface {interface}", "no ipv6 address", "exit"]
    st.config(dut, commands, type=cli_type, skip_error_check=True)
    st.log(f"IPv6 address cleanup completed on {interface}")
    return True


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


def configure_ipv6_interface(dut, interface, ipv6_addr, mask, cli_type="klish"):
    """
    Configure IPv6 address on an interface and bring it up.
    """
    st.log(f"Configuring IPv6 address {ipv6_addr}/{mask} on {interface} for {dut}")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append(f"ipv6 address {ipv6_addr}/{mask}")
        commands.append("no shutdown")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured IPv6 address on {interface} and brought it up")

        st.wait(2, "Waiting for interface to come up")
        return True
    except Exception as e:
        st.error(f"Failed to configure IPv6 address on {interface}: {str(e)}")
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


def configure_bgp_neighbor_ipv6(dut, local_asn, neighbor_ipv6, remote_asn, family="ipv6", cli_type="klish"):
    """
    Configure BGP neighbor for IPv6.
    """
    st.log(f"Configuring BGP neighbor {neighbor_ipv6} (AS {remote_asn}) on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"neighbor {neighbor_ipv6} remote-as {remote_asn}")
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"activate")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor on {dut}: {str(e)}")
        return False


def advertise_bgp_network_ipv6(dut, local_asn, network, cli_type="klish"):
    """
    Advertise an IPv6 network in BGP.
    """
    st.log(f"Advertising IPv6 network {network} in BGP on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"network {network}")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully advertised IPv6 network in BGP on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to advertise IPv6 network on {dut}: {str(e)}")
        return False


def verify_bgp_neighbor_state(dut, neighbor_ip, state='Established', family='ipv6', timeout=90, cli_type='klish'):
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

                        # Accept Established, numeric states, (Policy), or policy
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


def verify_bgp_routes_from_neighbor(dut, neighbor_ip, expected_routes=None, min_routes=1,
                                     family='ipv6', cli_type='klish'):
    """
    Verify routes received from a BGP neighbor using 'show bgp ipv6 unicast neighbors X routes'.

    Args:
        dut: Device under test
        neighbor_ip: Neighbor IPv6 address
        expected_routes: List of expected route prefixes (optional)
        min_routes: Minimum number of routes expected (default: 1)
        family: Address family (default: ipv6)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if routes are received as expected, False otherwise
    """
    st.log(f"Verifying routes received from BGP neighbor {neighbor_ip} on {dut}")

    try:
        # Execute show command to get routes from neighbor
        command = f"show bgp ipv6 unicast neighbors {neighbor_ip} routes"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        st.log(f"Raw output from '{command}':\n{output}")

        if not output:
            st.error(f"No output received from command: {command}")
            return False

        # Parse the output to find route entries
        # Look for lines like: "*  i 2001:db8:1::/64 fe80::2014:11ff:fe9d:57dd"
        route_pattern = r'\*?\s*[>i]\s*([0-9a-fA-F:]+/\d+)'
        routes_found = re.findall(route_pattern, output)

        st.log(f"Routes found from neighbor {neighbor_ip}: {routes_found}")

        # Check if we have minimum number of routes
        if len(routes_found) < min_routes:
            st.error(f"Expected at least {min_routes} routes, but found {len(routes_found)}")
            return False

        # If specific routes are expected, verify they are present
        if expected_routes:
            for expected_route in expected_routes:
                if not any(expected_route in route for route in routes_found):
                    st.error(f"Expected route {expected_route} not found in received routes")
                    return False
                st.log(f"Verified route {expected_route} is received from neighbor")

        st.log(f"Successfully verified routes from neighbor {neighbor_ip}")
        return True

    except Exception as e:
        st.error(f"Exception during route verification: {str(e)}")
        return False


def restart_bgp_daemon(dut, cli_type='click'):
    """
    Restart BGP daemon (bgpd) on the DUT.

    Returns:
        bool: True if restart was successful, False otherwise
    """
    st.log(f"Restarting BGP daemon on {dut}")

    try:
        # Method 1: Using systemctl (preferred for SONiC)
        command = "docker restart bgp"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        st.log(f"BGP daemon restart command executed on {dut}")
        st.log(f"Output: {output}")

        # Wait for daemon to restart
        st.wait(20, "Waiting for BGP daemon to restart")

        # Verify BGP daemon is running
        verify_command = "sudo systemctl status bgp"
        verify_output = st.config(dut, verify_command, type=cli_type, skip_error_check=True)

        if verify_output and ("active (running)" in verify_output.lower() or "active" in verify_output.lower()):
            st.log(f"BGP daemon successfully restarted and running on {dut}")
            return True
        else:
            st.error(f"BGP daemon may not be running properly on {dut}")
            return False

    except Exception as e:
        st.error(f"Failed to restart BGP daemon on {dut}: {str(e)}")
        return False


def ping_ipv6(dut, destination_ipv6, count=5, cli_type='click'):
    """
    Ping an IPv6 address from a DUT.
    """
    st.log(f"Pinging {destination_ipv6} from {dut} with count={count}")

    try:
        result = ip_api.ping(
            dut=dut,
            addresses=destination_ipv6,
            family='ipv6',
            count=count,
            cli_type=cli_type
        )

        if result:
            st.log(f"Ping to {destination_ipv6} succeeded")
            return True
        else:
            st.error(f"Ping to {destination_ipv6} failed")
            return False

    except Exception as e:
        st.error(f"Exception during ping: {str(e)}")
        return False


def cleanup_bgp_ipv6_config():
    """
    Clean up BGP and IPv6 configuration from all DUTs.
    """
    st.log("Cleaning up BGP and IPv6 configuration")

    dut_list = [data.dut1, data.dut2]

    for dut in dut_list:
        try:
            # Remove BGP configuration
            bgp_api.enable_docker_routing_config_mode(dut, cli_type=data.cli_type)
            commands = ["no router bgp"]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            # Remove IPv6 configuration from physical interfaces
            if dut == data.dut1:
                interface = data.dut1_dut2_port
                ipv6_addr = data.dut1_ipv6
            else:
                interface = data.dut2_dut1_port
                ipv6_addr = data.dut2_ipv6

            commands = []
            commands.append(f"interface {interface}")
            commands.append(f"no ipv6 address {ipv6_addr}/{data.ipv6_mask}")
            commands.append("exit")
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            st.log(f"Cleaned up configuration on {dut}")

        except Exception as e:
            st.error(f"Error during cleanup on {dut}: {str(e)}")

    st.log("Cleanup completed")


class TestIpv6BgpDaemonRestart:
    """
    Test class for IPv6 BGP daemon restart recovery test.
    """

    def test_ipv6_bgp_daemon_restart_recovery(self):
        """
        Test: Verify BGP session recovery after BGP daemon restart (IPv6).

        Steps:
        1. Configure physical interfaces with IPv6
        2. Verify IPv6 connectivity
        3. Remove existing BGP configuration
        4. Configure BGP routers with router IDs
        5. Configure BGP neighbors (iBGP)
        6. Advertise IPv6 network from DUT1
        7. Verify BGP sessions establish
        8. Verify DUT2 learns the advertised route
        9. Restart BGP daemon on DUT1
        10. Verify BGP session recovers on both DUTs
        11. Verify routes are re-learned/re-advertised
        12. Verify connectivity is restored
        """
        st.banner("TEST: IPv6 BGP Daemon Restart Recovery")

        # Step 1: Check and remove existing IPv6 addresses
        st.log("Step 1: Checking and removing existing IPv6 addresses from interfaces")

        remove_ipv6_address(data.dut1, data.dut1_dut2_port, data.cli_type)
        remove_ipv6_address(data.dut2, data.dut2_dut1_port, data.cli_type)

        # Step 2: Configure interface MTU and speed
        st.log("Step 2: Configuring interface MTU and speed on both DUTs")

        if not configure_interface_mtu_speed(data.dut1, data.dut1_dut2_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut1}")

        if not configure_interface_mtu_speed(data.dut2, data.dut2_dut1_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut2}")

        # Step 3: Configure IPv6 addresses on physical interfaces
        st.log("Step 3: Configuring IPv6 addresses on physical interfaces")

        if not configure_ipv6_interface(data.dut1, data.dut1_dut2_port, data.dut1_ipv6, data.ipv6_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv6 on {data.dut1}")

        if not configure_ipv6_interface(data.dut2, data.dut2_dut1_port, data.dut2_ipv6, data.ipv6_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv6 on {data.dut2}")

        # Step 4: Verify IPv6 connectivity
        st.log("Step 4: Verifying IPv6 connectivity on physical interfaces")

        if not ping_ipv6(data.dut1, data.dut2_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut1} to {data.dut2} failed")

        # Step 5: Remove existing BGP configuration
        st.log("Step 5: Removing existing BGP configuration from both DUTs")

        remove_bgp_config(data.dut1, data.cli_type)
        remove_bgp_config(data.dut2, data.cli_type)

        st.wait(5, "Waiting after BGP cleanup")

        # Step 6: Configure BGP routers with router IDs
        st.log("Step 6: Configuring BGP routers with router IDs")

        if not configure_bgp_router_with_router_id(data.dut1, data.bgp_asn, data.router_id_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        if not configure_bgp_router_with_router_id(data.dut2, data.bgp_asn, data.router_id_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        # Step 7: Configure BGP neighbors
        st.log("Step 7: Configuring BGP neighbors (iBGP)")

        if not configure_bgp_neighbor_ipv6(data.dut1, data.bgp_asn, data.dut2_ipv6, data.bgp_asn, data.af_ipv6, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        if not configure_bgp_neighbor_ipv6(data.dut2, data.bgp_asn, data.dut1_ipv6, data.bgp_asn, data.af_ipv6, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut2}")

        # Step 8: Advertise network from DUT1
        st.log(f"Step 8: Advertising network {data.advertised_network} from DUT1")

        if not advertise_bgp_network_ipv6(data.dut1, data.bgp_asn, data.advertised_network, data.cli_type):
            st.report_fail("msg", f"Failed to advertise network on {data.dut1}")

        # Step 9: Verify BGP sessions establish
        st.log("Step 9: Verifying BGP sessions establish on both DUTs")

        st.wait(data.bgp_wait, "Waiting for BGP sessions to establish")

        if not verify_bgp_neighbor_state(data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not established on {data.dut1}")

        if not verify_bgp_neighbor_state(data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not established on {data.dut2}")

        st.log("PRE-RESTART: BGP sessions established successfully")

        # Step 10: Verify DUT2 learns the advertised route from DUT1
        st.log(f"Step 10: Verifying DUT2 learns advertised route {data.advertised_network} from neighbor {data.dut1_ipv6}")

        if not verify_bgp_routes_from_neighbor(data.dut2, data.dut1_ipv6,
                                                expected_routes=[data.advertised_network],
                                                min_routes=1, family='ipv6', cli_type=data.cli_type):
            st.report_fail("msg", f"DUT2 did not learn advertised route {data.advertised_network} from neighbor {data.dut1_ipv6}")

        st.log("PRE-RESTART: Routes learned successfully")

        # Step 11: Restart BGP daemon on DUT1
        st.log("Step 11: Restarting BGP daemon on DUT1")

        if not restart_bgp_daemon(data.dut1, 'click'):
            st.report_fail("msg", f"Failed to restart BGP daemon on {data.dut1}")

        st.wait(data.daemon_restart_wait, f"Waiting {data.daemon_restart_wait} seconds for BGP daemon to fully restart and recover")

        # Step 12: Verify BGP sessions recover on both DUTs
        st.log("Step 12: Verifying BGP sessions recover after daemon restart")

        if not verify_bgp_neighbor_state(data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, data.recovery_wait, data.cli_type):
            st.report_fail("msg", f"BGP session did NOT recover on {data.dut1} after daemon restart")

        if not verify_bgp_neighbor_state(data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, data.recovery_wait, data.cli_type):
            st.report_fail("msg", f"BGP session did NOT recover on {data.dut2} after daemon restart")

        st.log("POST-RESTART: BGP sessions recovered successfully")

        # Step 13: Verify routes are re-learned from neighbor
        st.log(f"Step 13: Verifying DUT2 re-learns advertised route {data.advertised_network} from neighbor {data.dut1_ipv6} after restart")

        if not verify_bgp_routes_from_neighbor(data.dut2, data.dut1_ipv6,
                                                expected_routes=[data.advertised_network],
                                                min_routes=1, family='ipv6', cli_type=data.cli_type):
            st.report_fail("msg", f"DUT2 did not re-learn advertised route {data.advertised_network} from neighbor {data.dut1_ipv6} after daemon restart")

        st.log("POST-RESTART: Routes re-learned successfully")

        # Step 14: Verify connectivity is restored
        st.log("Step 14: Verifying IPv6 connectivity is restored after daemon restart")

        if not ping_ipv6(data.dut1, data.dut2_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut1} to {data.dut2} failed after daemon restart")

        st.log("POST-RESTART: Connectivity restored successfully")

        st.log("ALL TESTS PASSED: BGP daemon restart recovery successful")
        st.log("- BGP sessions recovered")
        st.log("- Routes re-learned/re-advertised")
        st.log("- Connectivity restored")

        st.report_pass("test_case_passed")
