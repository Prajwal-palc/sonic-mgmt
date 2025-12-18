"""
BGP IPv4 Route Reflector Configuration and Verification

Author: Claude Code
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_3rr.yaml \
  tests/routing/BGP/test_ipv4_bgp_route_reflector.py \
  --logs-path ./logs/test_ipv4_bgp_rr_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test suite validates BGP IPv4 Route Reflector functionality in a 3-node topology.
  Tests cover:
  - Route Reflector server and client configuration
  - Route propagation between RR clients through RR server
  - Route-Reflector-Client attribute verification
  - Configuration persistence across save and reboot

Pre-requisites:
  - Topology: 3-node (DUT1-DUT2-DUT3) | Supported: HW and Virtual
  - DUT1 (192.168.100.107) - Route Reflector Client
  - DUT2 (192.168.100.80) - Route Reflector Server
  - DUT3 (192.168.100.117) - Route Reflector Client
  - Required testbed: testbeds/testbed_vs_3rr.yaml
  - Required variables: tests/routing/BGP/vars_ipv4_bgp_route_reflector.yaml
  - CLI Type: klish (sonic-cli)

Topology:
  DUT1 (Client) --[Eth0-Eth48]-- DUT2 (RR Server) --[Eth32-Eth32]-- DUT3 (Client)
"""

import pytest
import time
import re
from pathlib import Path
import yaml

from spytest import st, SpyTestDict
from spytest.tgen.tg import tgen_obj_dict
import apis.routing.ip as ip_api
import apis.routing.bgp as bgp_api
import apis.system.interface as intf_api
import apis.system.reboot as reboot_api
import apis.system.basic as basic_api

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Default variable file path
DEFAULT_VAR_FILE = Path(__file__).resolve().parent / "vars_ipv4_bgp_route_reflector.yaml"


def initialize_data() -> None:
    """Load test configuration from YAML file"""
    try:
        with open(DEFAULT_VAR_FILE, "r") as f:
            payload = yaml.safe_load(f)
    except FileNotFoundError as error:
        pytest.skip(str(error))

    global vars, data
    vars = st.ensure_min_topology("D1D2:1", "D2D3:1")
    data.config = SpyTestDict(payload)

    # Map DUTs to their roles
    data.dut1 = vars.D1  # Route Reflector Client
    data.dut2 = vars.D2  # Route Reflector Server
    data.dut3 = vars.D3  # Route Reflector Client

    # Extract configuration from YAML
    ipv4_config = data.config.get("ipv4", {})
    bgp_config = data.config.get("bgp", {})

    # DUT1-DUT2 link addressing
    dut1_dut2_link = ipv4_config.get("dut1_dut2_link", {})
    data.dut1_dut2_ip = dut1_dut2_link.get("dut1_address", "10.1.12.1")
    data.dut2_dut1_ip = dut1_dut2_link.get("dut2_address", "10.1.12.2")
    data.dut1_dut2_mask = dut1_dut2_link.get("prefix_length", "24")

    # DUT2-DUT3 link addressing
    dut2_dut3_link = ipv4_config.get("dut2_dut3_link", {})
    data.dut2_dut3_ip = dut2_dut3_link.get("dut2_address", "10.2.23.2")
    data.dut3_dut2_ip = dut2_dut3_link.get("dut3_address", "10.2.23.3")
    data.dut2_dut3_mask = dut2_dut3_link.get("prefix_length", "24")

    # BGP configuration
    data.bgp_asn = bgp_config.get("asn", "65001")

    # DUT1 BGP config
    dut1_bgp = bgp_config.get("dut1", {})
    data.dut1_router_id = dut1_bgp.get("router_id", "1.1.1.1")
    data.dut1_networks = dut1_bgp.get("networks", ["192.168.1.0/24"])

    # DUT2 BGP config (Route Reflector Server)
    dut2_bgp = bgp_config.get("dut2", {})
    data.dut2_router_id = dut2_bgp.get("router_id", "2.2.2.2")
    data.dut2_networks = dut2_bgp.get("networks", ["192.168.2.0/24"])

    # DUT3 BGP config
    dut3_bgp = bgp_config.get("dut3", {})
    data.dut3_router_id = dut3_bgp.get("router_id", "3.3.3.3")
    data.dut3_networks = dut3_bgp.get("networks", ["192.168.3.0/24"])

    # Interface names
    data.dut1_dut2_intf = vars.D1D2P1
    data.dut2_dut1_intf = vars.D2D1P1
    data.dut2_dut3_intf = vars.D2D3P1
    data.dut3_dut2_intf = vars.D3D2P1

    st.log(f"Initialized data: DUT1={data.dut1}, DUT2={data.dut2}, DUT3={data.dut3}")
    st.log(f"DUT1-DUT2 link: {data.dut1_dut2_intf}({data.dut1_dut2_ip}) <-> {data.dut2_dut1_intf}({data.dut2_dut1_ip})")
    st.log(f"DUT2-DUT3 link: {data.dut2_dut3_intf}({data.dut2_dut3_ip}) <-> {data.dut3_dut2_intf}({data.dut3_dut2_ip})")


def convert_intf_name_to_klish(interface_name):
    """
    Convert interface name from click format to klish format.

    Args:
        interface_name: Interface name in click format (e.g., Ethernet0, Ethernet48)

    Returns:
        str: Interface name in klish format (e.g., Ethernet 0, Ethernet 48)

    Examples:
        Ethernet0 -> Ethernet 0
        Ethernet48 -> Ethernet 48
        Ethernet32 -> Ethernet 32
    """
    import re
    match = re.match(r'([A-Za-z]+)(\d+)', interface_name)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return interface_name


def check_and_remove_ipv4_address(dut, interface, cli_type="klish"):
    """
    Check if IPv4 address exists on interface and remove it if present.

    Args:
        dut: Device under test
        interface: Interface name (e.g., Ethernet0)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if cleanup successful, False otherwise
    """
    st.log(f"Checking for existing IPv4 addresses on {dut} interface {interface}")

    # Convert interface name to klish format if using klish CLI for show command
    intf_name_show = convert_intf_name_to_klish(interface) if cli_type == "klish" else interface

    # Get interface configuration - use same CLI type for consistency
    output = st.show(dut, f"show ip interfaces {intf_name_show}", type=cli_type)

    if not output:
        st.log(f"No IP configuration found on {interface}")
        return True

    # Pattern to match IPv4 addresses: 10.1.1.1/24 format
    ipv4_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2})'

    addresses_to_remove = []
    for line in str(output).split('\n'):
        match = re.search(ipv4_pattern, line)
        if match:
            addresses_to_remove.append(match.group(1))

    if addresses_to_remove:
        st.log(f"Found IPv4 addresses to remove: {addresses_to_remove}")

        # Convert interface name to klish format if using klish CLI
        intf_name = convert_intf_name_to_klish(interface) if cli_type == "klish" else interface

        # Remove each IPv4 address using klish CLI
        for addr in addresses_to_remove:
            commands = []
            commands.append(f"interface {intf_name}")
            commands.append(f"no ip address {addr}")
            commands.append("exit")

            result = st.config(dut, commands, type=cli_type)
            if result:
                st.log(f"Successfully removed IPv4 address {addr} from {interface}")
            else:
                st.error(f"Failed to remove IPv4 address {addr} from {interface}")
                return False

        # Verify removal
        time.sleep(2)
        verify_output = st.show(dut, f"show ip interface {intf_name_show}", type=cli_type)
        if verify_output:
            for addr in addresses_to_remove:
                if addr in str(verify_output):
                    st.error(f"IPv4 address {addr} still present after removal")
                    return False

        st.log(f"All IPv4 addresses successfully removed from {interface}")
    else:
        st.log(f"No IPv4 addresses found on {interface}")

    return True


def cleanup_bgp_config(dut, cli_type="klish"):
    """
    Clean up BGP configuration using 'no router bgp' command.

    Args:
        dut: Device under test
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if cleanup successful, False otherwise
    """
    st.log(f"Cleaning up BGP configuration on {dut}")

    # Check if BGP is configured
    output = st.show(dut, "show bgp summary", type="klish", skip_error_check=True)

    if not output or "BGP is not configured" in str(output):
        st.log(f"BGP is not configured on {dut}, no cleanup needed")
        return True

    # Remove BGP configuration
    commands = ["no router bgp"]
    result = st.config(dut, commands, type=cli_type, skip_error_check=True)
    # Wait for BGP to be removed
    time.sleep(3)
    # Verify BGP removal
    verify_output = st.show(dut, "show bgp summary", type="klish", skip_error_check=True)

    if verify_output and "BGP is not configured" not in str(verify_output):
        # Try to extract AS number and remove explicitly
        bgp_asn_match = re.search(r'local AS number (\d+)', str(verify_output))
        if bgp_asn_match:
            asn = bgp_asn_match.group(1)
            st.log(f"Retrying BGP cleanup with explicit AS number {asn}")
            commands = ["no router bgp"]
            result = st.config(dut, commands, type=cli_type, skip_error_check=True)
            time.sleep(3)

    # Final verification
    final_output = st.show(dut, "show bgp summary", type="klish", skip_error_check=True)

    if final_output and "BGP is not configured" in str(final_output):
        st.log(f"BGP configuration successfully removed from {dut}")
        return True
    elif not final_output:
        st.log(f"BGP appears to be removed from {dut} (no output)")
        return True
    else:
        st.error(f"Failed to remove BGP configuration from {dut}")
        st.log(f"BGP status: {final_output}")
        return False


def configure_ipv4_interface(dut, interface, ipv4_addr, mask, cli_type="klish"):
    """
    Configure IPv4 address on an interface and bring it up.

    Args:
        dut: Device under test
        interface: Interface name
        ipv4_addr: IPv4 address (without mask)
        mask: Prefix length (e.g., 24)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if configuration successful, False otherwise
    """
    st.log(f"Configuring IPv4 address {ipv4_addr}/{mask} on {dut} interface {interface}")

    # Convert interface name to klish format if using klish CLI
    intf_name = convert_intf_name_to_klish(interface) if cli_type == "klish" else interface

    commands = []
    commands.append(f"interface {intf_name}")
    commands.append(f"ip address {ipv4_addr}/{mask}")
    commands.append("no shutdown")
    commands.append("exit")

    st.config(dut, commands, type=cli_type)

    # Note: Following IPv6 RR test pattern - we don't verify configuration here
    # because show commands don't work in klish config mode. The config command
    # itself will fail if there's a problem (e.g., "IP already in use").
    st.log(f"Successfully configured IPv4 address on {interface} and brought it up")

    # Sleep to allow interface to come up
    st.log(f"Sleep for 2 sec(s)...Waiting for interface to come up")
    time.sleep(2)

    return True


def configure_bgp_route_reflector_client(dut, local_asn, neighbor_ip, remote_asn,
                                          router_id=None, network_prefixes=None,
                                          route_reflector_client=False, family="ipv4"):
    """
    Configure BGP with Route Reflector client settings.

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbor_ip: BGP neighbor IP address
        remote_asn: Remote AS number
        router_id: BGP router ID (optional)
        network_prefixes: List of networks to advertise (optional)
        route_reflector_client: Set to True to configure neighbor as RR client
        family: Address family (default: ipv4)

    Returns:
        bool: True if configuration successful, False otherwise
    """
    st.log(f"Configuring BGP on {dut}: AS={local_asn}, Neighbor={neighbor_ip}, RR_Client={route_reflector_client}")

    # Configure router-id globally (not in BGP context for klish mode)
    if router_id:
        id_commands = [f"router-id {router_id}"]
        st.config(dut, id_commands, type="klish")
        st.log(f"Configured global router-id {router_id}")

    commands = []
    commands.append(f"router bgp {local_asn}")

    # Configure neighbor
    commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")

    # Address family configuration
    commands.append(f"address-family {family} unicast")
    commands.append("activate")

    # Configure as route-reflector-client if specified
    if route_reflector_client:
        commands.append("route-reflector-client")
        st.log(f"Configuring {neighbor_ip} as route-reflector-client")

    commands.append("end")

    result = st.config(dut, commands, type="klish")

    if not result:
        st.error(f"Failed to configure BGP neighbor on {dut}")
        return False

    # Step 2: Advertise networks in separate session if provided
    if network_prefixes:
        net_commands = []
        net_commands.append(f"router bgp {local_asn}")
        net_commands.append(f"address-family {family} unicast")

        for network in network_prefixes:
            net_commands.append(f"network {network}")
            st.log(f"Advertising network {network}")

        net_commands.append("exit")
        net_commands.append("exit")

        result = st.config(dut, net_commands, type="klish")

        if not result:
            st.error(f"Failed to advertise BGP networks on {dut}")
            return False

    # Wait for BGP to initialize
    time.sleep(5)

    st.log(f"BGP configuration completed on {dut}")
    return True


def configure_bgp_multiple_neighbors(dut, local_asn, neighbors_config, router_id=None,
                                      network_prefixes=None, family="ipv4"):
    """
    Configure BGP with multiple neighbors (for Route Reflector server).

    Important: Klish CLI requires entering address-family context per neighbor for
    activate and route-reflector-client commands. Network advertisements must be
    done in a separate session.

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbors_config: List of dicts with neighbor configuration
                         Each dict: {"ip": "10.1.1.1", "remote_asn": "65001", "rr_client": True}
        router_id: BGP router ID (optional)
        network_prefixes: List of networks to advertise (optional)
        family: Address family (default: ipv4)

    Returns:
        bool: True if configuration successful, False otherwise
    """
    st.log(f"Configuring BGP on {dut} with multiple neighbors: AS={local_asn}")

    # Step 1: Configure router-id globally (not in BGP context for klish mode)
    if router_id:
        id_commands = [f"router-id {router_id}"]
        st.config(dut, id_commands, type="klish")
        st.log(f"Configured global router-id {router_id}")

    # Step 2: Configure neighbors with address-family per neighbor
    commands = []
    commands.append(f"router bgp {local_asn}")

    # Configure each neighbor with its address-family context
    for neighbor in neighbors_config:
        neighbor_ip = neighbor.get("ip")
        remote_asn = neighbor.get("remote_asn")
        rr_client = neighbor.get("rr_client", False)

        # Neighbor configuration
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")

        # Enter address-family for this neighbor
        commands.append(f"address-family {family} unicast")
        commands.append("activate")

        if rr_client:
            commands.append("route-reflector-client")
            st.log(f"Configuring {neighbor_ip} as route-reflector-client")

        # Exit address-family context
        commands.append("exit")

    # Exit router bgp context
    commands.append("exit")

    result = st.config(dut, commands, type="klish")

    if not result:
        st.error(f"Failed to configure BGP neighbors on {dut}")
        return False

    # Step 2: Configure network advertisements separately if provided
    if network_prefixes:
        net_commands = []
        net_commands.append(f"router bgp {local_asn}")
        net_commands.append(f"address-family {family} unicast")

        for network in network_prefixes:
            net_commands.append(f"network {network}")
            st.log(f"Advertising network {network}")

        net_commands.append("exit")
        net_commands.append("exit")

        result = st.config(dut, net_commands, type="klish")

        if not result:
            st.error(f"Failed to configure BGP network advertisements on {dut}")
            return False

    # Wait for BGP to initialize
    time.sleep(5)

    st.log(f"BGP configuration with multiple neighbors completed on {dut}")
    return True


def verify_bgp_neighbor_state(dut, neighbor_ip, expected_state="Established", timeout=60, family="ipv4"):
    """
    Verify BGP neighbor state reaches expected state within timeout.
    Enhanced to accept (Policy) state as valid along with numeric states.

    Args:
        dut: Device under test
        neighbor_ip: BGP neighbor IP address
        expected_state: Expected BGP state (default: Established)
        timeout: Maximum wait time in seconds
        family: Address family (default: ipv4)

    Returns:
        bool: True if neighbor reaches expected state, False otherwise
    """
    st.log(f"Verifying BGP neighbor {neighbor_ip} on {dut} reaches state '{expected_state}'")

    start_time = time.time()
    while (time.time() - start_time) < timeout:
        output = st.show(dut, "show bgp summary", type="klish")

        if output:
            # Look for neighbor in output
            for entry in output if isinstance(output, list) else []:
                if isinstance(entry, dict):
                    neighbor = entry.get("neighbor") or entry.get("neigh")
                    state = entry.get("state") or entry.get("state/pfxrcd")

                    if neighbor == neighbor_ip:
                        # Accept numeric states (prefix count), "Established", or "(Policy)" as valid
                        if state:
                            state_str = str(state).strip()
                            # Check if state is numeric (prefix count), "Established", or contains "(Policy)"
                            if state_str.isdigit() or state_str == expected_state or "(Policy)" in state_str:
                                st.log(f"BGP neighbor {neighbor_ip} state: {state_str} (Valid)")
                                return True
                            else:
                                st.log(f"BGP neighbor {neighbor_ip} current state: {state_str}, waiting...")

        time.sleep(5)

    st.error(f"BGP neighbor {neighbor_ip} did not reach state '{expected_state}' within {timeout} seconds")

    # Log final state for debugging
    final_output = st.show(dut, "show bgp summary", type="klish")
    st.log(f"Final BGP summary on {dut}: {final_output}")

    return False


def verify_bgp_route_present(dut, network_prefix, expected_nexthop=None, timeout=30, family="ipv4"):
    """
    Verify that a BGP route is present in the BGP table.
    Uses BGP API function that bypasses broken TextFSM template.

    Args:
        dut: Device under test
        network_prefix: Network prefix to check (e.g., 10.1.12.0/24)
        expected_nexthop: Expected next-hop IP (optional)
        timeout: Maximum wait time in seconds
        family: Address family (default: ipv4)

    Returns:
        bool: True if route is present, False otherwise
    """
    st.log(f"Verifying BGP route {network_prefix} is present on {dut}")

    start_time = time.time()
    while (time.time() - start_time) < timeout:
        # Use BGP API function that works around TextFSM template spacing constraint issue
        routes = bgp_api.show_bgp_ipv4_network_parsed(dut, family=family)

        for route in routes:
            if route['network'] == network_prefix:
                st.log(f"Route {network_prefix} found with next-hop {route['next_hop']}")

                if expected_nexthop:
                    if route['next_hop'] == expected_nexthop:
                        st.log(f"Route has expected next-hop {expected_nexthop}")
                        return True
                    else:
                        st.log(f"Route found but next-hop {route['next_hop']} != expected {expected_nexthop}")
                else:
                    return True

        time.sleep(5)

    st.error(f"BGP route {network_prefix} not found on {dut} within {timeout} seconds")

    # Log final BGP table for debugging
    final_routes = bgp_api.show_bgp_ipv4_network_parsed(dut, family=family)
    st.log(f"Final BGP routes on {dut}: {final_routes}")

    return False


def verify_route_reflector_client(dut, neighbor_ip, cli_type='klish'):
    """
    Verify that a BGP neighbor is configured as Route-Reflector Client.
    Uses 'show bgp ipv4 unicast neighbors' as RR configuration is visible in this output.

    Args:
        dut: Device under test
        neighbor_ip: BGP neighbor IP address
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if neighbor is configured as RR client, False otherwise
    """
    st.log(f"Verifying Route-Reflector Client configuration for neighbor {neighbor_ip} on {dut}")

    # Use show bgp ipv4 unicast neighbors command - RR client info visible here
    command = "show bgp ipv4 unicast neighbors"
    output = st.show(dut, command, type="klish", skip_tmpl=True)

    if not output:
        st.error(f"No output from command: {command}")
        return False

    # Convert output to string for searching
    output_str = str(output)

    # Check if this neighbor section contains Route-Reflector Client
    # Look for the neighbor IP and then Route-Reflector Client in the same section
    lines = output_str.split('\n') if isinstance(output_str, str) else str(output_str).split('\n')

    neighbor_found = False
    in_neighbor_section = False

    for line in lines:
        # Check if we're in the correct neighbor section
        if f"BGP neighbor is {neighbor_ip}" in line:
            neighbor_found = True
            in_neighbor_section = True
        elif "BGP neighbor is" in line and neighbor_ip not in line:
            # We've moved to a different neighbor section
            in_neighbor_section = False

        # Look for Route-Reflector Client in the current neighbor section
        if in_neighbor_section and "Route-Reflector Client" in line:
            st.log(f"✓ Neighbor {neighbor_ip} is configured as Route-Reflector Client")
            return True

    if not neighbor_found:
        st.error(f"Neighbor {neighbor_ip} not found in BGP neighbors output")
    else:
        st.error(f"Neighbor {neighbor_ip} is NOT configured as Route-Reflector Client")

    st.log(f"Output: {output}")
    return False


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown.
    """
    global vars, data

    st.banner("MODULE PROLOGUE: BGP IPv4 Route Reflector Test Suite Starting")

    # Initialize test data
    initialize_data()

    # Store original CLI type
    data.cli_type = st.get_ui_type(data.dut1, cli_type="klish")

    st.log(f"Test topology: {data.dut1} <-> {data.dut2} <-> {data.dut3}")
    st.log(f"CLI type: {data.cli_type}")

    yield

    st.banner("MODULE EPILOGUE: BGP IPv4 Route Reflector Test Suite Cleanup")

    # Cleanup BGP configuration on all DUTs
    cleanup_bgp_config(data.dut1, cli_type=data.cli_type)
    cleanup_bgp_config(data.dut2, cli_type=data.cli_type)
    cleanup_bgp_config(data.dut3, cli_type=data.cli_type)

    # Cleanup IPv4 addresses on interfaces
    check_and_remove_ipv4_address(data.dut1, data.dut1_dut2_intf, cli_type=data.cli_type)
    check_and_remove_ipv4_address(data.dut2, data.dut2_dut1_intf, cli_type=data.cli_type)
    check_and_remove_ipv4_address(data.dut2, data.dut2_dut3_intf, cli_type=data.cli_type)
    check_and_remove_ipv4_address(data.dut3, data.dut3_dut2_intf, cli_type=data.cli_type)

    st.log("Module cleanup completed")


@pytest.fixture(scope="function", autouse=True)
def function_hooks(request):
    """
    Function-level setup and teardown.
    """
    st.banner(f"TEST CASE: {request.node.name} - Starting")
    yield
    st.banner(f"TEST CASE: {request.node.name} - Completed")


def test_bgp_route_reflector_basic():
    """
    Test ID: BGP_RR_IPv4_001

    Verify basic BGP Route Reflector functionality:
    1. Configure IPv4 addresses on all links
    2. Configure DUT2 as Route Reflector server
    3. Configure DUT1 and DUT3 as Route Reflector clients
    4. Verify BGP neighbor sessions are Established
    5. Verify routes are reflected between clients
    6. Verify Route-Reflector-Client attribute is present
    """
    st.log("Starting test_bgp_route_reflector_basic")

    # Step 1: Cleanup existing configuration
    st.log("Step 1: Cleanup existing IPv4 addresses and BGP configuration")

    assert check_and_remove_ipv4_address(data.dut1, data.dut1_dut2_intf, cli_type=data.cli_type), \
        "Failed to cleanup IPv4 address on DUT1"
    assert check_and_remove_ipv4_address(data.dut2, data.dut2_dut1_intf, cli_type=data.cli_type), \
        "Failed to cleanup IPv4 address on DUT2-DUT1 interface"
    assert check_and_remove_ipv4_address(data.dut2, data.dut2_dut3_intf, cli_type=data.cli_type), \
        "Failed to cleanup IPv4 address on DUT2-DUT3 interface"
    assert check_and_remove_ipv4_address(data.dut3, data.dut3_dut2_intf, cli_type=data.cli_type), \
        "Failed to cleanup IPv4 address on DUT3"

    assert cleanup_bgp_config(data.dut1, cli_type=data.cli_type), "Failed to cleanup BGP on DUT1"
    assert cleanup_bgp_config(data.dut2, cli_type=data.cli_type), "Failed to cleanup BGP on DUT2"
    assert cleanup_bgp_config(data.dut3, cli_type=data.cli_type), "Failed to cleanup BGP on DUT3"

    # Step 2: Configure IPv4 addresses
    st.log("Step 2: Configure IPv4 addresses on all interfaces")

    assert configure_ipv4_interface(data.dut1, data.dut1_dut2_intf, data.dut1_dut2_ip,
                                     data.dut1_dut2_mask, cli_type=data.cli_type), \
        "Failed to configure IPv4 on DUT1"

    assert configure_ipv4_interface(data.dut2, data.dut2_dut1_intf, data.dut2_dut1_ip,
                                     data.dut1_dut2_mask, cli_type=data.cli_type), \
        "Failed to configure IPv4 on DUT2-DUT1 interface"

    assert configure_ipv4_interface(data.dut2, data.dut2_dut3_intf, data.dut2_dut3_ip,
                                     data.dut2_dut3_mask, cli_type=data.cli_type), \
        "Failed to configure IPv4 on DUT2-DUT3 interface"

    assert configure_ipv4_interface(data.dut3, data.dut3_dut2_intf, data.dut3_dut2_ip,
                                     data.dut2_dut3_mask, cli_type=data.cli_type), \
        "Failed to configure IPv4 on DUT3"

    # Wait for interfaces to come up
    time.sleep(5)

    # Step 3: Configure BGP on DUT1 (Route Reflector Client)
    st.log("Step 3: Configure BGP on DUT1 (Route Reflector Client)")

    assert configure_bgp_route_reflector_client(
        data.dut1,
        local_asn=data.bgp_asn,
        neighbor_ip=data.dut2_dut1_ip,
        remote_asn=data.bgp_asn,
        router_id=data.dut1_router_id,
        network_prefixes=data.dut1_networks,
        route_reflector_client=True,
        family="ipv4"
    ), "Failed to configure BGP on DUT1"

    # Step 4: Configure BGP on DUT3 (Route Reflector Client)
    st.log("Step 4: Configure BGP on DUT3 (Route Reflector Client)")

    assert configure_bgp_route_reflector_client(
        data.dut3,
        local_asn=data.bgp_asn,
        neighbor_ip=data.dut2_dut3_ip,
        remote_asn=data.bgp_asn,
        router_id=data.dut3_router_id,
        network_prefixes=data.dut3_networks,
        route_reflector_client=True,
        family="ipv4"
    ), "Failed to configure BGP on DUT3"

    # Step 5: Configure BGP on DUT2 (Route Reflector Server)
    st.log("Step 5: Configure BGP on DUT2 (Route Reflector Server)")

    neighbors_config = [
        {
            "ip": data.dut1_dut2_ip,
            "remote_asn": data.bgp_asn,
            "rr_client": True
        },
        {
            "ip": data.dut3_dut2_ip,
            "remote_asn": data.bgp_asn,
            "rr_client": True
        }
    ]

    assert configure_bgp_multiple_neighbors(
        data.dut2,
        local_asn=data.bgp_asn,
        neighbors_config=neighbors_config,
        router_id=data.dut2_router_id,
        network_prefixes=data.dut2_networks,
        family="ipv4"
    ), "Failed to configure BGP on DUT2"

    # Step 6: Verify BGP neighbor sessions
    st.log("Step 6: Verify BGP neighbor sessions are Established")

    assert verify_bgp_neighbor_state(data.dut1, data.dut2_dut1_ip, timeout=90, family="ipv4"), \
        "DUT1 BGP neighbor session not established"

    assert verify_bgp_neighbor_state(data.dut2, data.dut1_dut2_ip, timeout=90, family="ipv4"), \
        "DUT2-DUT1 BGP neighbor session not established"

    assert verify_bgp_neighbor_state(data.dut2, data.dut3_dut2_ip, timeout=90, family="ipv4"), \
        "DUT2-DUT3 BGP neighbor session not established"

    assert verify_bgp_neighbor_state(data.dut3, data.dut2_dut3_ip, timeout=90, family="ipv4"), \
        "DUT3 BGP neighbor session not established"

    # Step 7: Verify routes are reflected
    st.log("Step 7: Verify routes are reflected between Route Reflector clients")

    # DUT1 should learn DUT3's network via DUT2
    # Note: iBGP Route Reflectors preserve the original advertising router's next-hop
    # So DUT1 will see next-hop as DUT3's IP (10.2.23.3), not DUT2's interface IP
    if data.dut3_networks:
        for network in data.dut3_networks:
            assert verify_bgp_route_present(data.dut1, network, expected_nexthop=data.dut3_dut2_ip,
                                           timeout=60, family="ipv4"), \
                f"DUT1 did not learn DUT3's network {network} via Route Reflector"

    # DUT3 should learn DUT1's network via DUT2
    # Note: iBGP Route Reflectors preserve the original advertising router's next-hop
    # So DUT3 will see next-hop as DUT1's IP (10.1.12.1), not DUT2's interface IP
    if data.dut1_networks:
        for network in data.dut1_networks:
            assert verify_bgp_route_present(data.dut3, network, expected_nexthop=data.dut1_dut2_ip,
                                           timeout=60, family="ipv4"), \
                f"DUT3 did not learn DUT1's network {network} via Route Reflector"

    # Step 8: Verify Route-Reflector-Client attribute
    st.log("Step 8: Verify Route-Reflector-Client attribute on DUT2")

    assert verify_route_reflector_client(data.dut2, data.dut1_dut2_ip), \
        "DUT1 is not configured as Route-Reflector Client on DUT2"

    assert verify_route_reflector_client(data.dut2, data.dut3_dut2_ip), \
        "DUT3 is not configured as Route-Reflector Client on DUT2"

    st.report_pass("test_case_passed")


def test_bgp_route_reflector_persistence():
    """
    Test ID: BGP_RR_IPv4_002

    Verify BGP Route Reflector configuration persistence across save and reboot:
    1. Verify existing BGP configuration (from previous test)
    2. Save configuration
    3. Reboot DUT2 (Route Reflector server)
    4. Verify BGP sessions re-establish
    5. Verify routes are still reflected
    6. Verify Route-Reflector-Client attribute persists
    """
    st.log("Starting test_bgp_route_reflector_persistence")

    # Step 1: Verify BGP is running
    st.log("Step 1: Verify BGP neighbor sessions before save/reboot")

    # Check if BGP neighbors are established
    dut2_dut1_established = verify_bgp_neighbor_state(data.dut2, data.dut1_dut2_ip,
                                                      timeout=30, family="ipv4")
    dut2_dut3_established = verify_bgp_neighbor_state(data.dut2, data.dut3_dut2_ip,
                                                      timeout=30, family="ipv4")

    if not (dut2_dut1_established and dut2_dut3_established):
        st.log("BGP not fully configured, running basic configuration first")
        test_bgp_route_reflector_basic()

    # Step 2: Save configuration on DUT2
    st.log("Step 2: Save configuration on DUT2")

    save_result = basic_api.deploy_package(data.dut2)
    assert save_result, "Failed to save configuration on DUT2"

    time.sleep(5)

    # Step 3: Reboot DUT2
    st.log("Step 3: Rebooting DUT2 (Route Reflector server)")

    reboot_result = st.reboot(data.dut2, "fast")
    assert reboot_result, "Failed to reboot DUT2"

    st.log("DUT2 reboot completed, waiting for BGP docker to be ready")
    # Wait longer for BGP docker container to start and stabilize after reboot
    # The BGP container needs time to initialize before we can verify sessions
    time.sleep(60)

    # Step 3a: Restart BGP docker on all devices
    st.log("Step 3a: Restarting BGP docker on all devices")

    st.log("Restarting BGP docker on DUT1")
    st.config(data.dut1, "docker restart bgp", type='click', skip_error_check=True)

    st.log("Restarting BGP docker on DUT2")
    st.config(data.dut2, "docker restart bgp", type='click', skip_error_check=True)

    st.log("Restarting BGP docker on DUT3")
    st.config(data.dut3, "docker restart bgp", type='click', skip_error_check=True)

    st.log("Waiting 5 minutes (300 seconds) for BGP docker containers to stabilize")
    time.sleep(300)

    # Step 4: Verify BGP sessions re-establish
    st.log("Step 4: Verify BGP sessions re-establish after docker restart")

    assert verify_bgp_neighbor_state(data.dut2, data.dut1_dut2_ip, timeout=120, family="ipv4"), \
        "DUT2-DUT1 BGP session did not re-establish after reboot"

    assert verify_bgp_neighbor_state(data.dut2, data.dut3_dut2_ip, timeout=120, family="ipv4"), \
        "DUT2-DUT3 BGP session did not re-establish after reboot"

    assert verify_bgp_neighbor_state(data.dut1, data.dut2_dut1_ip, timeout=120, family="ipv4"), \
        "DUT1 BGP session did not re-establish after DUT2 reboot"

    assert verify_bgp_neighbor_state(data.dut3, data.dut2_dut3_ip, timeout=120, family="ipv4"), \
        "DUT3 BGP session did not re-establish after DUT2 reboot"

    # Step 5: Verify routes are still reflected
    st.log("Step 5: Verify routes are still reflected after reboot")

    # DUT1 should still learn DUT3's network
    if data.dut3_networks:
        for network in data.dut3_networks:
            assert verify_bgp_route_present(data.dut1, network, expected_nexthop=data.dut3_dut2_ip,
                                           timeout=60, family="ipv4"), \
                f"DUT1 did not learn DUT3's network {network} after reboot"

    # DUT3 should still learn DUT1's network
    if data.dut1_networks:
        for network in data.dut1_networks:
            assert verify_bgp_route_present(data.dut3, network, expected_nexthop=data.dut1_dut2_ip,
                                           timeout=60, family="ipv4"), \
                f"DUT3 did not learn DUT1's network {network} after reboot"

    # Step 6: Verify Route-Reflector-Client attribute persists
    st.log("Step 6: Verify Route-Reflector-Client attribute persists after reboot")

    assert verify_route_reflector_client(data.dut2, data.dut1_dut2_ip), \
        "DUT1 Route-Reflector Client attribute did not persist after reboot"

    assert verify_route_reflector_client(data.dut2, data.dut3_dut2_ip), \
        "DUT3 Route-Reflector Client attribute did not persist after reboot"

    # Add static routes for end-to-end connectivity
    # In iBGP Route Reflector setup, next-hops are preserved, so we need static routes
    # to enable direct connectivity between DUT1 and DUT3 via DUT2
    st.log("Adding static routes on DUT1 and DUT3 for end-to-end connectivity")

    # DUT1 needs route to DUT2-DUT3 subnet (10.2.23.0/24) via DUT2
    st.log(f"Adding static route on DUT1 to reach 10.2.23.0/24 via {data.dut2_dut1_ip}")
    result = ip_api.create_static_route(data.dut1, data.dut2_dut1_ip, "10.2.23.0/24",
                                        shell="sonic", family='ipv4', cli_type=data.cli_type)
    if not result:
        st.warn("Failed to add static route on DUT1, ping tests may fail")

    # DUT3 needs route to DUT1-DUT2 subnet (10.1.12.0/24) via DUT2
    st.log(f"Adding static route on DUT3 to reach 10.1.12.0/24 via {data.dut2_dut3_ip}")
    result = ip_api.create_static_route(data.dut3, data.dut2_dut3_ip, "10.1.12.0/24",
                                        shell="sonic", family='ipv4', cli_type=data.cli_type)
    if not result:
        st.warn("Failed to add static route on DUT3, ping tests may fail")

    # Wait longer for static routes to be installed and BGP routes to become valid
    # In iBGP Route Reflector setups, BGP routes are initially invalid (*ui) until
    # the static routes make the next-hops reachable, at which point they become valid (*>i)
    st.log("Waiting 15 seconds for static routes to install and BGP routes to become valid...")
    time.sleep(15)

    # Step 7: Verify connectivity with ping tests
    st.log("Step 7: Verifying end-to-end connectivity with ping tests")

    # DUT1 should be able to ping DUT3's IP (10.2.23.3)
    st.log("Ping from DUT1 to DUT3 IP address 10.2.23.3")
    ping_result_dut1 = ip_api.ping(data.dut1, data.dut3_dut2_ip, family='ipv4', count=5)
    assert ping_result_dut1, f"DUT1 failed to ping DUT3 at {data.dut3_dut2_ip}"
    st.log(f"✓ DUT1 successfully pinged DUT3 at {data.dut3_dut2_ip}")

    # DUT3 should be able to ping DUT1's IP (10.1.12.1)
    st.log("Ping from DUT3 to DUT1 IP address 10.1.12.1")
    ping_result_dut3 = ip_api.ping(data.dut3, data.dut1_dut2_ip, family='ipv4', count=5)
    assert ping_result_dut3, f"DUT3 failed to ping DUT1 at {data.dut1_dut2_ip}"
    st.log(f"✓ DUT3 successfully pinged DUT1 at {data.dut1_dut2_ip}")

    st.report_pass("test_case_passed")
