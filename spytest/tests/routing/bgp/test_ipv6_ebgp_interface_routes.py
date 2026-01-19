"""
IPv6 PHYSICAL INTERFACE WITH BGP ROUTE ADVERTISEMENT
Author: Prajwal
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv6_bgp_interface_routes.py \
  --logs-path ./logs/test_ipv6_bgp_routes_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IPv6 BGP route advertisement over physical interfaces using Klish CLI.
  This test suite configures iBGP sessions, advertises IPv6 networks using 'network' and
  'redistribute connected' commands, and verifies that routes are properly received and
  installed on neighbor routers. The test validates route advertisement, route reception,
  configuration persistence after reboot, and end-to-end IPv6 connectivity.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +-------------------------+                       +-------------------------+
        # |      smic_sonic1        |                       |      smic_sonic2        |
        # | Eth32 2001:db8:20::1/64 |=======================| Eth32 2001:db8:20::2/64 |
        # | (192.168.100.57)        |                       | (192.168.100.172)       |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: AS 65001 (iBGP), IPv6 Unicast address family
  - Route Advertisement: network statements + redistribute connected
  - Required test variables (YAML): cli_type (klish), bgp_wait_time, reboot_wait_time
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
data.dut1_ipv6 = "2001:db8:20::1"
data.dut2_ipv6 = "2001:db8:20::2"
data.ipv6_mask = "64"
data.bgp_asn_dut1 = "65001"
data.bgp_asn_dut2 = "65002"
data.af_ipv6 = "ipv6"
data.cli_type = "klish"
data.mtu = "9100"
data.speed = "40000"
data.bgp_wait = 90
data.reboot_wait = 60
data.ping_count = 5
data.router_id_dut1 = "1.1.1.1"
data.router_id_dut2 = "2.2.2.2"


@pytest.fixture(scope="module", autouse=True)
def ipv6_bgp_routes_module_hooks(request):
    """
    Module-level fixture for IPv6 BGP route test setup and teardown.
    Sets up topology, configures interfaces, IPv6 addresses, and BGP.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv6 BGP Routes Test")

    # Store DUT handles for easy access
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
    st.banner("MODULE TEARDOWN: Cleaning up IPv6 BGP route configuration")
    cleanup_bgp_ipv6_config()


@pytest.fixture(scope="function", autouse=True)
def ipv6_bgp_routes_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def configure_interface_mtu_speed(dut, interface, mtu, speed, cli_type="klish"):
    """
    Configure MTU and speed on an interface.

    Args:
        dut: Device under test
        interface: Interface name (e.g., Ethernet32)
        mtu: MTU value
        speed: Speed value
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring MTU={mtu} and speed={speed} on {interface} for {dut}")

    try:
        # Configure MTU using interface API
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

    Args:
        dut: Device under test
        interface: Interface name
        ipv6_addr: IPv6 address
        mask: Subnet mask
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring IPv6 address {ipv6_addr}/{mask} on {interface} for {dut}")

    try:
        # Use direct Klish commands to configure IP and bring up interface
        commands = []
        commands.append(f"interface {interface}")
        commands.append(f"ipv6 address {ipv6_addr}/{mask}")
        commands.append("no shutdown")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured IPv6 address on {interface} and brought it up")

        # Wait for interface to come up
        st.wait(2, "Waiting for interface to come up")
        return True
    except Exception as e:
        st.error(f"Failed to configure IPv6 address on {interface}: {str(e)}")
        return False


def verify_ipv6_interface(dut, interface, ipv6_addr, mask):
    """
    Verify IPv6 address configuration on an interface using direct Klish commands.

    Args:
        dut: Device under test
        interface: Interface name
        ipv6_addr: Expected IPv6 address
        mask: Expected subnet mask

    Returns:
        bool: True if verification passes, False otherwise
    """
    st.log(f"Verifying IPv6 address {ipv6_addr}/{mask} on {interface} for {dut}")

    try:
        # Execute show command and get raw output
        command = f"show ipv6 interfaces"
        output = st.config(dut, command, type="klish", skip_error_check=True)

        st.log(f"Raw output from '{command}': {output}")

        expected_ip = f"{ipv6_addr}/{mask}"

        # Parse the output text directly
        if output and isinstance(output, str):
            # Look for the IP address pattern in the output
            pattern = rf'{interface}\s+({ipv6_addr}/{mask})'
            match = re.search(pattern, output, re.IGNORECASE)

            if match:
                st.log(f"Successfully verified IPv6 address {expected_ip} on {interface}")
                return True
            else:
                # Try simpler check - just see if both interface and IP are in output
                if interface in output and expected_ip in output:
                    st.log(f"Successfully verified IPv6 address {expected_ip} on {interface} (simple match)")
                    return True

        st.error(f"Failed to verify IPv6 address {expected_ip} on {interface}")
        return False

    except Exception as e:
        st.error(f"Exception during IPv6 verification: {str(e)}")
        return False


def configure_bgp_router_with_router_id(dut, local_asn, router_id, cli_type="klish"):
    """
    Configure BGP router with local ASN and router ID.

    Args:
        dut: Device under test
        local_asn: Local AS number
        router_id: BGP router ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
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
def configure_route_map(dut, route_map_name="ALLOW-ALL", sequence=10, action="permit", cli_type="klish"):
    """
    Configure route-map before BGP configuration to avoid Policy warning in show bgp summary.

    Args:
        dut: Device under test
        route_map_name: Route-map name (default: ALLOW-ALL)
        sequence: Sequence number (default: 10)
        action: permit or deny (default: permit)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring route-map {route_map_name} {action} {sequence} on {dut}")

    try:
        commands = [f"route-map {route_map_name} {action} {sequence}", "exit"]
        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured route-map {route_map_name} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure route-map on {dut}: {str(e)}")
        return False

def configure_bgp_neighbor_with_routes(dut, local_asn, neighbor_ip, remote_asn, network_prefix,
                                        redistribute=True, family="ipv6", cli_type="klish"):
    """
    Configure BGP neighbor with IPv6 address family, network advertisement, and redistribute connected.

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbor_ip: Neighbor IPv6 address
        remote_asn: Remote AS number
        network_prefix: Network to advertise (e.g., "2001:db8:20::1/64")
        redistribute: Enable redistribute connected (default: True)
        family: Address family (default: ipv6)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP neighbor {neighbor_ip} with route advertisement on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        # Use direct Klish commands for proper IPv6 BGP configuration
        commands = []
        commands.append(f"router bgp {local_asn}")

        # Configure address family with network and redistribute
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"network {network_prefix}")
        if redistribute:
            commands.append("redistribute connected")
        commands.append("exit")

        # Configure neighbor
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"activate")
        commands.append(f"route-map ALLOW-ALL in")
        commands.append(f"route-map ALLOW-ALL out")
        commands.append("exit")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor {neighbor_ip} with route advertisement on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def verify_bgp_neighbor_state(dut, neighbor_ip, state='Established', family='ipv6', timeout=90, cli_type='klish'):
    """
    Verify BGP neighbor state using sonic-cli (Klish) with direct show commands.
    Enhanced validation to accept (Policy) state which indicates session is established
    but route policies are filtering prefixes.

    Args:
        dut: Device under test
        neighbor_ip: Neighbor IPv6 address
        state: Expected state (default: Established)
        family: Address family (default: ipv6)
        timeout: Timeout in seconds
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if neighbor is in expected state, False otherwise
    """
    st.log(f"Verifying BGP neighbor {neighbor_ip} is in {state} state on {dut} using {cli_type} CLI")

    # Poll for BGP neighbor state using direct Klish show command
    iterations = int(timeout / 5)  # Check every 5 seconds
    for i in range(iterations):
        try:
            # Use direct Klish show command
            output = st.show(dut, "show bgp summary", type=cli_type)

            # Check if output contains the neighbor and state
            if output:
                for entry in output:
                    if str(entry.get('neighbor', '')).strip() == str(neighbor_ip).strip():
                        # Check if state column shows Established (or numeric value indicating up)
                        neighbor_state = entry.get('state', '')
                        st.log(f"Found neighbor {neighbor_ip} with state: {neighbor_state}")

                        # Enhanced validation: Accept Established, numeric states, (Policy), or policy
                        # (Policy) indicates session is established but route policies are filtering prefixes
                        if (state.lower() in str(neighbor_state).lower() or
                            str(neighbor_state).isdigit() or
                            '(Policy)' in str(neighbor_state) or
                            'policy' in str(neighbor_state).lower()):
                            st.log(f"BGP neighbor {neighbor_ip} is in {state} state (or equivalent)")
                            return True

            st.log(f"Attempt {i+1}/{iterations}: BGP neighbor {neighbor_ip} not yet in {state} state. Waiting 5 seconds...")
            st.wait(5)

        except Exception as e:
            st.log(f"Error checking BGP state: {str(e)}")
            st.wait(5)

    st.error(f"BGP neighbor {neighbor_ip} did not reach {state} state within {timeout} seconds")
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


def ping_ipv6(dut, destination_ipv6, count=5, cli_type='click'):
    """
    Ping an IPv6 address from a DUT.

    Args:
        dut: Device under test
        destination_ipv6: Destination IPv6 address
        count: Number of ping packets (default: 5)
        cli_type: CLI type (default: click)

    Returns:
        bool: True if ping succeeds, False otherwise
    """
    st.log(f"Pinging {destination_ipv6} from {dut} with count={count}")

    try:
        # Use ip_api.ping with correct parameters
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


def save_config_all_duts():
    """
    Save configuration on all DUTs using 'write memory' command in sonic-cli only.
    """
    st.log("Saving configuration on all DUTs using 'write memory' in sonic-cli")
    dut_list = [data.dut1, data.dut2]

    for dut in dut_list:
        try:
            bgp_api.enable_docker_routing_config_mode(dut, cli_type=data.cli_type)
            output = st.config(dut, "write memory", type=data.cli_type, skip_error_check=True)
            st.log(f"Write memory output on {dut}: {output}")
        except Exception as e:
            st.error(f"Failed to save configuration on {dut}: {str(e)}")
            return False

    return True


def reboot_all_duts():
    """
    Reboot all DUTs and wait for them to come back up.
    """
    st.log("Rebooting all DUTs")
    dut_list = [data.dut1, data.dut2]

    for dut in dut_list:
        st.log(f"Rebooting {dut}")
        st.reboot(dut, "fast")

    # Wait for DUTs to come back up
    st.wait(data.reboot_wait, "Waiting for DUTs to reboot and stabilize")

    st.log("All DUTs rebooted successfully")
    return True


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

            # Remove IPv6 configuration from interfaces
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


class TestIpv6BgpRoutes:
    """
    Test class for IPv6 BGP route advertisement and verification.
    """

    def test_ipv6_bgp_routes_config_verify(self):
        """
        Test IPv6 BGP route advertisement and verification.

        Steps:
        1. Configure interfaces with IPv6 addresses
        2. Configure BGP with router IDs
        3. Configure BGP neighbors with network advertisement and redistribute connected
        4. Verify BGP sessions are established
        5. Verify routes are received from neighbors
        6. Test IPv6 connectivity
        """
        st.banner("TEST: IPv6 BGP Route Advertisement and Verification")

        # Step 1: Configure interface MTU and speed
        st.log("Step 1: Configuring interface MTU and speed on both DUTs")

        if not configure_interface_mtu_speed(data.dut1, data.dut1_dut2_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut1}")

        if not configure_interface_mtu_speed(data.dut2, data.dut2_dut1_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut2}")

        # Step 2: Configure IPv6 addresses on interfaces
        st.log("Step 2: Configuring IPv6 addresses on both DUTs")

        if not configure_ipv6_interface(data.dut1, data.dut1_dut2_port, data.dut1_ipv6, data.ipv6_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv6 on {data.dut1}")

        if not configure_ipv6_interface(data.dut2, data.dut2_dut1_port, data.dut2_ipv6, data.ipv6_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv6 on {data.dut2}")

        # Step 3: Verify IPv6 configuration
        st.log("Step 3: Verifying IPv6 configuration on both DUTs")

        if not verify_ipv6_interface(data.dut1, data.dut1_dut2_port, data.dut1_ipv6, data.ipv6_mask):
            st.report_fail("msg", f"IPv6 verification failed on {data.dut1}")

        if not verify_ipv6_interface(data.dut2, data.dut2_dut1_port, data.dut2_ipv6, data.ipv6_mask):
            st.report_fail("msg", f"IPv6 verification failed on {data.dut2}")

        # Step 4: Test IPv6 connectivity before BGP
        st.log("Step 4: Testing IPv6 connectivity before BGP configuration")

        if not ping_ipv6(data.dut1, data.dut2_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut1} to {data.dut2} failed before BGP")

        if not ping_ipv6(data.dut2, data.dut1_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut2} to {data.dut1} failed before BGP")

        # Step 5: Configure BGP routers with router IDs
        st.log("Step 5: Configuring BGP routers with router IDs on both DUTs")

        if not configure_bgp_router_with_router_id(data.dut1, data.bgp_asn_dut1, data.router_id_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        if not configure_bgp_router_with_router_id(data.dut2, data.bgp_asn_dut2, data.router_id_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        # Step 6: Configure BGP neighbors with route advertisement
        st.log("Step 6: Configuring BGP neighbors with network advertisement and redistribute connected")
        
        if not configure_route_map(data.dut1, "ALLOW-ALL", 10, "permit", data.cli_type):
            st.report_fail("msg", f"Failed to configure route-map on {data.dut1}")

        # Configure route-map on DUT2 (before BGP configuration to avoid Policy warning)
        if not configure_route_map(data.dut2, "ALLOW-ALL", 10, "permit", data.cli_type):
            st.report_fail("msg", f"Failed to configure route-map on {data.dut2}")

        # DUT1 advertises its network
        if not configure_bgp_neighbor_with_routes(
            data.dut1, data.bgp_asn_dut1, data.dut2_ipv6, data.bgp_asn_dut2,
            f"{data.dut1_ipv6}/{data.ipv6_mask}", redistribute=True,
            family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor with routes on {data.dut1}")

        # DUT2 advertises its network
        if not configure_bgp_neighbor_with_routes(
            data.dut2, data.bgp_asn_dut2, data.dut1_ipv6, data.bgp_asn_dut1,
            f"{data.dut2_ipv6}/{data.ipv6_mask}", redistribute=True,
            family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor with routes on {data.dut2}")

        # Step 7: Wait and verify BGP session establishment
        st.log("Step 7: Verifying BGP session establishment")
        st.wait(data.bgp_wait, "Waiting for BGP session establishment")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP session failed to establish on one or both DUTs")

        # Step 8: Verify routes received from neighbors
        st.log("Step 8: Verifying routes received from BGP neighbors")

        # Verify DUT1 receives routes from DUT2
        if not verify_bgp_routes_from_neighbor(
            data.dut1, data.dut2_ipv6, min_routes=1, family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Failed to verify routes from neighbor on {data.dut1}")

        # Verify DUT2 receives routes from DUT1
        if not verify_bgp_routes_from_neighbor(
            data.dut2, data.dut1_ipv6, min_routes=1, family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Failed to verify routes from neighbor on {data.dut2}")

        # Step 9: Test IPv6 connectivity after BGP
        st.log("Step 9: Testing IPv6 connectivity after BGP configuration")

        if not ping_ipv6(data.dut1, data.dut2_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut1} to {data.dut2} failed after BGP")

        if not ping_ipv6(data.dut2, data.dut1_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut2} to {data.dut1} failed after BGP")

        st.log("IPv6 BGP route advertisement and verification test PASSED")
        st.report_pass("test_case_passed")

    def test_ipv6_bgp_routes_save_reboot(self):
        """
        Test IPv6 BGP route advertisement persistence after save and reboot.

        Steps:
        1. Verify BGP sessions are established
        2. Verify routes are received
        3. Save configuration on both DUTs
        4. Reboot both DUTs
        5. Verify BGP sessions after reboot
        6. Verify routes are still received after reboot
        7. Test IPv6 connectivity after reboot
        """
        st.banner("TEST: IPv6 BGP Routes Persistence After Reboot")

        # Step 1: Verify BGP sessions before reboot
        st.log("Step 1: Verifying BGP sessions before reboot")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP session not established before reboot")

        # Step 2: Verify routes before reboot
        st.log("Step 2: Verifying routes received before reboot")

        if not verify_bgp_routes_from_neighbor(
            data.dut1, data.dut2_ipv6, min_routes=1, family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Routes not received on {data.dut1} before reboot")

        if not verify_bgp_routes_from_neighbor(
            data.dut2, data.dut1_ipv6, min_routes=1, family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Routes not received on {data.dut2} before reboot")

        # Step 3: Save configuration
        st.log("Step 3: Saving configuration on all DUTs")

        if not save_config_all_duts():
            st.report_fail("msg", "Failed to save configuration")

        # Step 4: Reboot DUTs
        st.log("Step 4: Rebooting all DUTs")

        if not reboot_all_duts():
            st.report_fail("msg", "Failed to reboot DUTs")

        # Step 5: Verify BGP sessions after reboot
        st.log("Step 5: Verifying BGP sessions after reboot")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP session failed to establish after reboot")

        # Step 6: Verify routes after reboot
        st.log("Step 6: Verifying routes received after reboot")

        if not verify_bgp_routes_from_neighbor(
            data.dut1, data.dut2_ipv6, min_routes=1, family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Routes not received on {data.dut1} after reboot")

        if not verify_bgp_routes_from_neighbor(
            data.dut2, data.dut1_ipv6, min_routes=1, family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Routes not received on {data.dut2} after reboot")

        # Step 7: Test IPv6 connectivity after reboot
        st.log("Step 7: Testing IPv6 connectivity after reboot")

        if not ping_ipv6(data.dut1, data.dut2_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut1} to {data.dut2} failed after reboot")

        if not ping_ipv6(data.dut2, data.dut1_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut2} to {data.dut1} failed after reboot")

        st.log("IPv6 BGP routes persistence after reboot test PASSED")
        st.report_pass("test_case_passed")
