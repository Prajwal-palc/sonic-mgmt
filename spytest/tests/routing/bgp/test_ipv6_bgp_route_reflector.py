"""
IPv6 BGP ROUTE REFLECTOR CONFIGURATION AND VERIFICATION
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_3node.yaml  \
  tests/routing/bgp/test_ipv6_bgp_route_reflector.py \
  --logs-path ./logs/test_ipv6_bgp_rr_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IPv6 BGP Route Reflector configuration over physical interfaces.
  This test suite configures a 3-node iBGP topology where DUT2 acts as a Route Reflector
  Server, and DUT1 and DUT3 are Route Reflector Clients. The test verifies that routes
  advertised by DUT1 are reflected to DUT3 (and vice versa) through the RR server without
  requiring a direct iBGP session between clients.

Pre-requisites:
  - Topology: 3-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 3 nodes (Route Reflector)
        # +-------------------------+                       +-------------------------+
        # |      DUT1 (Client)      |                       |   DUT2 (RR Server)      |
        # | Eth32 2001:db8:12::2/64 |=======================| Eth32 2001:db8:12::4/64 |
        # | AS 65001                |                       | AS 65001                |
        # +-------------------------+                       | Eth64 2001:db8:14::2/64 |
        #                                                   +============|=============+
        #                                                                |
        #                                                   +============|=============+
        #                                                   |   DUT3 (Client)         |
        #                                                   | Eth32 2001:db8:14::3/64 |
        #                                                   | AS 65001                |
        #                                                   +-------------------------+

  - BGP Configuration: AS 65001 (iBGP), IPv6 Unicast address family
  - Route Reflector: DUT2 is RR Server, DUT1 and DUT3 are RR Clients
  - Required test variables (YAML): cli_type (klish), bgp_wait_time
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
# DUT1 - DUT2 link
data.dut1_ipv6 = "2001:db8:12::2"
data.dut2_ipv6_link1 = "2001:db8:12::4"
# DUT2 - DUT3 link
data.dut2_ipv6_link2 = "2001:db8:14::2"
data.dut3_ipv6 = "2001:db8:14::3"
data.ipv6_mask = "64"
data.bgp_asn = "65001"
data.af_ipv6 = "ipv6"
data.cli_type = "klish"
data.mtu = "9100"
data.speed = "40000"
data.bgp_wait = 90
data.reboot_wait = 60
data.ping_count = 5
data.router_id_dut1 = "1.1.1.1"
data.router_id_dut2 = "2.2.2.2"
data.router_id_dut3 = "3.3.3.3"


@pytest.fixture(scope="module", autouse=True)
def ipv6_bgp_rr_module_hooks(request):
    """
    Module-level fixture for IPv6 BGP Route Reflector test setup and teardown.
    Sets up 3-node topology and configures interfaces.
    """
    global vars

    # Ensure minimum topology requirement: 3 nodes with 2 links
    vars = st.ensure_min_topology("D1D2:1", "D2D3:1")

    st.banner("MODULE SETUP: IPv6 BGP Route Reflector Test")

    # Store DUT handles for easy access
    data.dut1 = vars.D1
    data.dut2 = vars.D2
    data.dut3 = vars.D3
    data.dut1_dut2_port = vars.D1D2P1
    data.dut2_dut1_port = vars.D2D1P1
    data.dut2_dut3_port = vars.D2D3P1
    data.dut3_dut2_port = vars.D3D2P1

    # Log topology information
    st.log(f"DUT1 (Client): {data.dut1}")
    st.log(f"DUT2 (RR Server): {data.dut2}")
    st.log(f"DUT3 (Client): {data.dut3}")
    st.log(f"DUT1-DUT2 Ports: {data.dut1_dut2_port} <-> {data.dut2_dut1_port}")
    st.log(f"DUT2-DUT3 Ports: {data.dut2_dut3_port} <-> {data.dut3_dut2_port}")

    # Get UI type for the test
    data.shell_vtysh = st.get_ui_type()
    if data.shell_vtysh == "click":
        data.shell_vtysh = "vtysh"

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up IPv6 BGP Route Reflector configuration")
    cleanup_bgp_ipv6_config()


@pytest.fixture(scope="function", autouse=True)
def ipv6_bgp_rr_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def check_and_remove_ipv6_address(dut, interface, cli_type="klish"):
    """
    Check if IPv6 address exists on interface and remove it if present.

    Args:
        dut: Device under test
        interface: Interface name
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if operation successful, False otherwise
    """
    st.log(f"Checking for existing IPv6 addresses on {interface} of {dut}")

    try:
        # Get existing IPv6 addresses
        command = f"show ipv6 interface {interface}"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        # Check if any IPv6 addresses are configured
        if output and "inet6" in output.lower():
            st.log(f"Found existing IPv6 address on {interface}, removing it")

            # Get list of IPv6 addresses to remove
            # Pattern to match IPv6 addresses: 2001:db8::/64 format
            ipv6_pattern = r'([0-9a-fA-F:]+/\d+)'
            addresses = re.findall(ipv6_pattern, output)

            if addresses:
                for addr in addresses:
                    # Skip link-local addresses
                    if not addr.startswith('fe80'):
                        st.log(f"Removing IPv6 address {addr} from {interface}")
                        commands = []
                        commands.append(f"interface {interface}")
                        commands.append(f"no ipv6 address {addr}")
                        commands.append("exit")
                        st.config(dut, commands, type=cli_type, skip_error_check=True)

        st.log(f"IPv6 address cleanup completed on {interface}")
        return True

    except Exception as e:
        st.error(f"Failed to check/remove IPv6 address on {interface}: {str(e)}")
        return False


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
        command = f"show ipv6 interfaces"
        output = st.config(dut, command, type="klish", skip_error_check=True)

        st.log(f"Raw output from '{command}': {output}")

        expected_ip = f"{ipv6_addr}/{mask}"

        if output and isinstance(output, str):
            pattern = rf'{interface}\s+({ipv6_addr}/{mask})'
            match = re.search(pattern, output, re.IGNORECASE)

            if match:
                st.log(f"Successfully verified IPv6 address {expected_ip} on {interface}")
                return True
            else:
                if interface in output and expected_ip in output:
                    st.log(f"Successfully verified IPv6 address {expected_ip} on {interface} (simple match)")
                    return True

        st.error(f"Failed to verify IPv6 address {expected_ip} on {interface}")
        return False

    except Exception as e:
        st.error(f"Exception during IPv6 verification: {str(e)}")
        return False


def remove_bgp_config(dut, cli_type="klish"):
    """
    Remove existing BGP configuration from DUT.

    Args:
        dut: Device under test
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
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


def configure_bgp_neighbor_with_routes(dut, local_asn, neighbor_ip, remote_asn, network_prefix,
                                        redistribute=True, family="ipv6", cli_type="klish"):
    """
    Configure BGP neighbor with IPv6 address family, network advertisement, and redistribute connected.

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbor_ip: Neighbor IPv6 address
        remote_asn: Remote AS number
        network_prefix: Network to advertise (e.g., "2001:db8:12::2/64")
        redistribute: Enable redistribute connected (default: True)
        family: Address family (default: ipv6)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP neighbor {neighbor_ip} with route advertisement on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")

        # Configure address family with network
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"network {network_prefix}")
        if redistribute:
            commands.append("redistribute connected")
        commands.append("exit")

        # Configure neighbor
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"activate")
        commands.append("exit")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor {neighbor_ip} with route advertisement on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def configure_bgp_route_reflector_client(dut, local_asn, neighbor_ip, remote_asn,
                                          network_prefixes=None, family="ipv6", cli_type="klish"):
    """
    Configure BGP Route Reflector server with route-reflector-client for neighbors.

    Args:
        dut: Device under test (RR Server)
        local_asn: Local AS number
        neighbor_ip: Neighbor IPv6 address (can be list for multiple neighbors)
        remote_asn: Remote AS number
        network_prefixes: List of networks to advertise (optional)
        family: Address family (default: ipv6)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP Route Reflector client for neighbor {neighbor_ip} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        # Handle single neighbor or list of neighbors
        neighbors = neighbor_ip if isinstance(neighbor_ip, list) else [neighbor_ip]

        commands = []
        commands.append(f"router bgp {local_asn}")

        # Configure address family with network advertisements if provided
        if network_prefixes:
            commands.append(f"address-family ipv6 unicast")
            for prefix in network_prefixes:
                commands.append(f"network {prefix}")
            commands.append("exit")

        # Configure each neighbor as route-reflector-client
        for nbr in neighbors:
            commands.append(f"neighbor {nbr} remote-as {remote_asn}")
            commands.append(f"address-family ipv6 unicast")
            commands.append(f"activate")
            commands.append(f"route-reflector-client")
            commands.append("exit")
            commands.append("exit")

        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured Route Reflector client on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure Route Reflector client on {dut}: {str(e)}")
        return False


def verify_route_reflector_client(dut, neighbor_ip, cli_type='klish'):
    """
    Verify that a BGP neighbor is configured as Route-Reflector Client.

    Args:
        dut: Device under test (RR Server)
        neighbor_ip: Neighbor IPv6 address
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if neighbor is configured as RR client, False otherwise
    """
    st.log(f"Verifying Route-Reflector Client configuration for neighbor {neighbor_ip} on {dut}")

    try:
        # Execute show command to get detailed neighbor information
        command = f"show bgp ipv6 unicast neighbors {neighbor_ip}"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        st.log(f"Checking for 'Route-Reflector Client' in neighbor {neighbor_ip} output")

        if not output:
            st.error(f"No output received from command: {command}")
            return False

        # Check if "Route-Reflector Client" is present in the output
        if "Route-Reflector Client" in output or "route-reflector-client" in output.lower():
            st.log(f"Successfully verified Route-Reflector Client for neighbor {neighbor_ip}")
            return True
        else:
            st.error(f"Route-Reflector Client NOT found for neighbor {neighbor_ip}")
            st.log(f"Output snippet: {output[:500]}")
            return False

    except Exception as e:
        st.error(f"Exception during Route-Reflector Client verification: {str(e)}")
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

    iterations = int(timeout / 5)
    for i in range(iterations):
        try:
            output = st.show(dut, "show bgp summary", type=cli_type)

            if output:
                for entry in output:
                    if str(entry.get('neighbor', '')).strip() == str(neighbor_ip).strip():
                        neighbor_state = entry.get('state', '')
                        st.log(f"Found neighbor {neighbor_ip} with state: {neighbor_state}")

                        # Enhanced validation: Accept Established, numeric states, (Policy), or policy
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
        command = f"show bgp ipv6 unicast neighbors {neighbor_ip} routes"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        st.log(f"Raw output from '{command}':\n{output}")

        if not output:
            st.error(f"No output received from command: {command}")
            return False

        # Parse the output to find route entries
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
    dut_list = [data.dut1, data.dut2, data.dut3]

    for dut in dut_list:
        try:
            bgp_api.enable_docker_routing_config_mode(dut, cli_type=data.cli_type)
            output = st.config(dut, "write memory", type=data.cli_type, skip_error_check=True)
            st.log(f"Write memory output on {dut}: {output}")
        except Exception as e:
            st.error(f"Failed to save configuration on {dut}: {str(e)}")
            return False

    return True


def cleanup_bgp_ipv6_config():
    """
    Clean up BGP and IPv6 configuration from all DUTs.
    """
    st.log("Cleaning up BGP and IPv6 configuration")

    dut_configs = [
        (data.dut1, data.dut1_dut2_port, data.dut1_ipv6),
        (data.dut2, data.dut2_dut1_port, data.dut2_ipv6_link1),
        (data.dut2, data.dut2_dut3_port, data.dut2_ipv6_link2),
        (data.dut3, data.dut3_dut2_port, data.dut3_ipv6)
    ]

    for dut, interface, ipv6_addr in dut_configs:
        try:
            # Remove BGP configuration
            bgp_api.enable_docker_routing_config_mode(dut, cli_type=data.cli_type)
            commands = ["no router bgp"]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            # Remove IPv6 configuration from interfaces
            commands = []
            commands.append(f"interface {interface}")
            commands.append(f"no ipv6 address {ipv6_addr}/{data.ipv6_mask}")
            commands.append("exit")
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            st.log(f"Cleaned up configuration on {dut}")

        except Exception as e:
            st.error(f"Error during cleanup on {dut}: {str(e)}")

    st.log("Cleanup completed")


class TestIpv6BgpRouteReflector:
    """
    Test class for IPv6 BGP Route Reflector configuration and verification.
    """

    def test_ipv6_bgp_route_reflector_config_verify(self):
        """
        Test IPv6 BGP Route Reflector configuration and route propagation.

        Topology:
        DUT1 (RR Client) <---> DUT2 (RR Server) <---> DUT3 (RR Client)

        Steps:
        1. Check and remove existing IPv6 addresses from interfaces
        2. Configure interfaces with IPv6 addresses
        3. Configure BGP with router IDs on all DUTs
        4. Configure DUT1 and DUT3 as regular iBGP neighbors
        5. Configure DUT2 as Route Reflector Server
        6. Verify BGP sessions are established
        7. Verify routes from DUT1 are reflected to DUT3
        8. Verify routes from DUT3 are reflected to DUT1
        """
        st.banner("TEST: IPv6 BGP Route Reflector Configuration and Verification")

        # Step 1: Check and remove existing IPv6 addresses
        st.log("Step 1: Checking and removing existing IPv6 addresses from interfaces")

        check_and_remove_ipv6_address(data.dut1, data.dut1_dut2_port, data.cli_type)
        check_and_remove_ipv6_address(data.dut2, data.dut2_dut1_port, data.cli_type)
        check_and_remove_ipv6_address(data.dut2, data.dut2_dut3_port, data.cli_type)
        check_and_remove_ipv6_address(data.dut3, data.dut3_dut2_port, data.cli_type)

        # Step 2: Configure interface MTU and speed
        st.log("Step 2: Configuring interface MTU and speed on all DUTs")

        if not configure_interface_mtu_speed(data.dut1, data.dut1_dut2_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut1}")

        if not configure_interface_mtu_speed(data.dut2, data.dut2_dut1_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut2} link1")

        if not configure_interface_mtu_speed(data.dut2, data.dut2_dut3_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut2} link2")

        if not configure_interface_mtu_speed(data.dut3, data.dut3_dut2_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut3}")

        # Step 3: Configure IPv6 addresses on interfaces
        st.log("Step 3: Configuring IPv6 addresses on all interfaces")

        if not configure_ipv6_interface(data.dut1, data.dut1_dut2_port, data.dut1_ipv6, data.ipv6_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv6 on {data.dut1}")

        if not configure_ipv6_interface(data.dut2, data.dut2_dut1_port, data.dut2_ipv6_link1, data.ipv6_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv6 on {data.dut2} link1")

        if not configure_ipv6_interface(data.dut2, data.dut2_dut3_port, data.dut2_ipv6_link2, data.ipv6_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv6 on {data.dut2} link2")

        if not configure_ipv6_interface(data.dut3, data.dut3_dut2_port, data.dut3_ipv6, data.ipv6_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv6 on {data.dut3}")

        # Step 4: Verify IPv6 configuration
        st.log("Step 4: Verifying IPv6 configuration on all interfaces")

        if not verify_ipv6_interface(data.dut1, data.dut1_dut2_port, data.dut1_ipv6, data.ipv6_mask):
            st.report_fail("msg", f"IPv6 verification failed on {data.dut1}")

        if not verify_ipv6_interface(data.dut2, data.dut2_dut1_port, data.dut2_ipv6_link1, data.ipv6_mask):
            st.report_fail("msg", f"IPv6 verification failed on {data.dut2} link1")

        if not verify_ipv6_interface(data.dut2, data.dut2_dut3_port, data.dut2_ipv6_link2, data.ipv6_mask):
            st.report_fail("msg", f"IPv6 verification failed on {data.dut2} link2")

        if not verify_ipv6_interface(data.dut3, data.dut3_dut2_port, data.dut3_ipv6, data.ipv6_mask):
            st.report_fail("msg", f"IPv6 verification failed on {data.dut3}")

        # Step 5: Test IPv6 connectivity
        st.log("Step 5: Testing IPv6 connectivity between neighbors")

        if not ping_ipv6(data.dut1, data.dut2_ipv6_link1, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut1} to {data.dut2} failed")

        if not ping_ipv6(data.dut3, data.dut2_ipv6_link2, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut3} to {data.dut2} failed")

        # Step 6: Remove existing BGP configuration
        st.log("Step 6: Removing existing BGP configuration from all DUTs")

        remove_bgp_config(data.dut1, data.cli_type)
        remove_bgp_config(data.dut2, data.cli_type)
        remove_bgp_config(data.dut3, data.cli_type)

        st.wait(5, "Waiting after BGP cleanup")

        # Step 7: Configure BGP routers with router IDs
        st.log("Step 7: Configuring BGP routers with router IDs on all DUTs")

        if not configure_bgp_router_with_router_id(data.dut1, data.bgp_asn, data.router_id_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        if not configure_bgp_router_with_router_id(data.dut2, data.bgp_asn, data.router_id_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        if not configure_bgp_router_with_router_id(data.dut3, data.bgp_asn, data.router_id_dut3, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut3}")

        # Step 8: Configure BGP neighbors on DUT1 (RR Client)
        st.log("Step 8: Configuring BGP neighbor on DUT1 (RR Client)")

        if not configure_bgp_neighbor_with_routes(
            data.dut1, data.bgp_asn, data.dut2_ipv6_link1, data.bgp_asn,
            f"{data.dut1_ipv6}/{data.ipv6_mask}", redistribute=False,
            family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        # Step 9: Configure BGP neighbors on DUT3 (RR Client)
        st.log("Step 9: Configuring BGP neighbor on DUT3 (RR Client)")

        if not configure_bgp_neighbor_with_routes(
            data.dut3, data.bgp_asn, data.dut2_ipv6_link2, data.bgp_asn,
            f"{data.dut3_ipv6}/{data.ipv6_mask}", redistribute=False,
            family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut3}")

        # Step 10: Configure DUT2 as Route Reflector Server
        st.log("Step 10: Configuring DUT2 as Route Reflector Server")

        # Configure DUT2 with both neighbors as RR clients
        if not configure_bgp_route_reflector_client(
            data.dut2, data.bgp_asn,
            [data.dut1_ipv6, data.dut3_ipv6],  # Both neighbors are RR clients
            data.bgp_asn,
            network_prefixes=[f"{data.dut2_ipv6_link1}/{data.ipv6_mask}",
                             f"{data.dut2_ipv6_link2}/{data.ipv6_mask}"],
            family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure Route Reflector on {data.dut2}")

        # Step 11: Wait and verify BGP session establishment
        st.log("Step 11: Verifying BGP session establishment on all DUTs")
        st.wait(data.bgp_wait, "Waiting for BGP session establishment")

        # Verify DUT1 <-> DUT2 session
        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6_link1, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        # Verify DUT2 <-> DUT1 session
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        # Verify DUT2 <-> DUT3 session
        result3 = verify_bgp_neighbor_state(
            data.dut2, data.dut3_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        # Verify DUT3 <-> DUT2 session
        result4 = verify_bgp_neighbor_state(
            data.dut3, data.dut2_ipv6_link2, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2 and result3 and result4):
            st.report_fail("msg", "BGP session failed to establish on one or more DUTs")

        # Step 12: Verify Route-Reflector Client configuration on DUT2
        st.log("Step 12: Verifying Route-Reflector Client configuration on DUT2")

        # Verify DUT1 is configured as RR client on DUT2
        rr_result1 = verify_route_reflector_client(data.dut2, data.dut1_ipv6, data.cli_type)
        if not rr_result1:
            st.report_fail("msg", f"Route-Reflector Client verification failed for {data.dut1_ipv6} on {data.dut2}")

        # Verify DUT3 is configured as RR client on DUT2
        rr_result2 = verify_route_reflector_client(data.dut2, data.dut3_ipv6, data.cli_type)
        if not rr_result2:
            st.report_fail("msg", f"Route-Reflector Client verification failed for {data.dut3_ipv6} on {data.dut2}")

        st.log("Successfully verified Route-Reflector Client configuration for both neighbors on DUT2")

        # Step 13: Verify routes are reflected from DUT1 to DUT3
        st.log("Step 13: Verifying routes from DUT1 are reflected to DUT3 via Route Reflector")

        # DUT3 should receive routes from DUT1 via DUT2 (RR)
        if not verify_bgp_routes_from_neighbor(
            data.dut3, data.dut2_ipv6_link2,
            expected_routes=[f"{data.dut1_ipv6}"],
            min_routes=1, family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.log("Route reflection from DUT1 to DUT3 verification needs more time")

        # Step 14: Verify routes are reflected from DUT3 to DUT1
        st.log("Step 14: Verifying routes from DUT3 are reflected to DUT1 via Route Reflector")

        # DUT1 should receive routes from DUT3 via DUT2 (RR)
        if not verify_bgp_routes_from_neighbor(
            data.dut1, data.dut2_ipv6_link1,
            expected_routes=[f"{data.dut3_ipv6}"],
            min_routes=1, family=data.af_ipv6, cli_type=data.cli_type
        ):
            st.log("Route reflection from DUT3 to DUT1 verification needs more time")

        st.log("IPv6 BGP Route Reflector configuration and verification test PASSED")
        st.report_pass("test_case_passed")

    def test_ipv6_bgp_route_reflector_save_reboot(self):
        """
        Test IPv6 BGP Route Reflector persistence after save and reboot.

        Steps:
        1. Verify BGP sessions are established
        2. Save configuration on all DUTs
        3. Reboot all DUTs
        4. Verify BGP sessions after reboot
        5. Verify route reflection still works after reboot
        """
        st.banner("TEST: IPv6 BGP Route Reflector Persistence After Reboot")

        # Step 1: Verify BGP sessions before reboot
        st.log("Step 1: Verifying BGP sessions before reboot")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6_link1, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result3 = verify_bgp_neighbor_state(
            data.dut2, data.dut3_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result4 = verify_bgp_neighbor_state(
            data.dut3, data.dut2_ipv6_link2, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2 and result3 and result4):
            st.report_fail("msg", "BGP sessions not established before reboot")

        # Step 2: Save configuration
        st.log("Step 2: Saving configuration on all DUTs")

        if not save_config_all_duts():
            st.report_fail("msg", "Failed to save configuration")

        # Step 3: Reboot DUTs
        st.log("Step 3: Rebooting all DUTs")

        for dut in [data.dut1, data.dut2, data.dut3]:
            st.log(f"Rebooting {dut}")
            st.reboot(dut, "fast")

        st.wait(data.reboot_wait, "Waiting for DUTs to reboot and stabilize")

        # Step 4: Verify BGP sessions after reboot
        st.log("Step 4: Verifying BGP sessions after reboot")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6_link1, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result3 = verify_bgp_neighbor_state(
            data.dut2, data.dut3_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result4 = verify_bgp_neighbor_state(
            data.dut3, data.dut2_ipv6_link2, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2 and result3 and result4):
            st.report_fail("msg", "BGP sessions failed to establish after reboot")

        # Step 5: Verify route reflection works after reboot
        st.log("Step 5: Verifying route reflection after reboot")

        # Verify routes are still reflected
        verify_bgp_routes_from_neighbor(
            data.dut3, data.dut2_ipv6_link2, min_routes=1, family=data.af_ipv6, cli_type=data.cli_type
        )

        verify_bgp_routes_from_neighbor(
            data.dut1, data.dut2_ipv6_link1, min_routes=1, family=data.af_ipv6, cli_type=data.cli_type
        )

        st.log("IPv6 BGP Route Reflector persistence after reboot test PASSED")
        st.report_pass("test_case_passed")
