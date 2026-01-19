"""
IPv4 BGP LINK FLAP TEST - INTERFACE DOWN UNEXPECTEDLY
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv4_bgp_link_flap.py \
  --logs-path ./logs/test_ipv4_bgp_link_flap_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Test case to verify BGP behavior during interface link flap storm (interface down unexpectedly).
  This test validates BGP session resilience and recovery when the physical interface experiences
  multiple up/down events in quick succession (link flap storm). This simulates real-world
  scenarios like cable issues, switch port flaps, or hardware problems.

  Test scenarios:
  1. Configure iBGP between DUT1 and DUT2 over physical interface
  2. Verify BGP session establishes and routes are exchanged
  3. Simulate link flap storm (multiple interface shutdown/no shutdown cycles)
  4. Monitor BGP session state during flaps
  5. Verify BGP session recovers after flaps stop
  6. Verify routes are re-installed after recovery

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with iBGP
        # +-------------------------+                       +-------------------------+
        # |      DUT1               |                       |      DUT2               |
        # | Eth32: 10.1.1.1/24 |=======================| Eth32: 10.1.1.2/24 |
        # | Network: 192.168.10.0/24                       |                         |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: AS 65001 (iBGP), IPv4 Unicast address family
  - Network advertised: 192.168.10.0/24 from DUT1
  - Link Flap: 5 rapid shutdown/no shutdown cycles on DUT1's interface
  - Expected Result: BGP session recovers and routes are restored after flaps
"""

from __future__ import annotations

import pytest
import re
import time

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
# Network to advertise
data.advertised_network = "192.168.10.0/24"
data.advertised_network_prefix = "192.168.10.0"
data.advertised_network_mask = "24"
# Interface for advertised network (needed for BGP to advertise)
data.advertised_network_interface = "Ethernet4"
data.advertised_network_ip = "192.168.10.4"
# BGP config
data.bgp_asn = "65001"
data.af_ipv4 = "ipv4"
data.cli_type = "klish"
data.mtu = "9100"
data.speed = "40000"
data.bgp_wait = 90
data.flap_count = 5
data.flap_interval = 2
data.recovery_wait = 120
data.reboot_wait = 60
data.ping_count = 5
data.router_id_dut1 = "1.1.1.1"
data.router_id_dut2 = "2.2.2.2"


@pytest.fixture(scope="module", autouse=True)
def ipv4_bgp_link_flap_module_hooks(request):
    """
    Module-level fixture for IPv4 BGP link flap test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv4 BGP Link Flap Test")

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
def ipv4_bgp_link_flap_func_hooks(request):
    """
    Function-level fixture - currently empty.
    """
    yield


def remove_ipv4_address(dut, interface, cli_type="klish"):
    """
    Remove all IPv4 addresses from interface.
    """
    st.log(f"Removing IPv4 addresses from {interface} on {dut}")
    commands = [f"interface {interface}", "no ip address", "exit"]
    st.config(dut, commands, type=cli_type, skip_error_check=True)
    st.log(f"IPv4 address cleanup completed on {interface}")
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


def advertise_network(dut, local_asn, network, family="ipv4", cli_type="klish"):
    """
    Advertise a network in BGP.
    """
    st.log(f"Advertising network {network} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"address-family ipv4 unicast")
        commands.append(f"network {network}")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully advertised network {network} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to advertise network on {dut}: {str(e)}")
        return False


def shutdown_interface(dut, interface, cli_type="klish"):
    """
    Shutdown an interface (admin down).
    """
    st.log(f"Shutting down interface {interface} on {dut}")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append("shutdown")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully shut down interface {interface} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to shutdown interface {interface} on {dut}: {str(e)}")
        return False


def no_shutdown_interface(dut, interface, cli_type="klish"):
    """
    Bring up an interface (no shutdown).
    """
    st.log(f"Bringing up interface {interface} on {dut}")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append("no shutdown")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully brought up interface {interface} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to bring up interface {interface} on {dut}: {str(e)}")
        return False


def simulate_link_flap_storm(dut, interface, flap_count, interval, cli_type="klish"):
    """
    Simulate link flap storm by repeatedly shutting down and bringing up interface.

    Args:
        dut: Device under test
        interface: Interface to flap
        flap_count: Number of flap cycles
        interval: Time between flaps in seconds
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Simulating link flap storm on {interface} of {dut}")
    st.log(f"Flap count: {flap_count}, Interval: {interval} seconds")

    try:
        for i in range(flap_count):
            st.banner(f"Link Flap {i+1}/{flap_count}")

            # Shutdown interface
            st.log(f"Flap {i+1}: Shutting down {interface}")
            if not shutdown_interface(dut, interface, cli_type):
                st.error(f"Failed to shutdown interface during flap {i+1}")
                return False

            st.wait(interval, f"Waiting {interval} seconds with interface down")

            # Bring up interface
            st.log(f"Flap {i+1}: Bringing up {interface}")
            if not no_shutdown_interface(dut, interface, cli_type):
                st.error(f"Failed to bring up interface during flap {i+1}")
                return False

            st.wait(interval, f"Waiting {interval} seconds with interface up")

        st.log(f"Completed {flap_count} link flaps on {interface}")
        return True

    except Exception as e:
        st.error(f"Exception during link flap simulation: {str(e)}")
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


def verify_route_in_routing_table(dut, network, timeout=90, cli_type='klish'):
    """
    Verify that a BGP route IS installed in the routing table.
    Uses st.config to get raw output since template parsing may fail.
    """
    st.log(f"Verifying route {network} is in routing table on {dut}")

    iterations = int(timeout / 5)
    for i in range(iterations):
        try:
            # Use st.config with skip_error_check to get raw text output (no template parsing)
            command = "show ip route"
            output = st.config(dut, command, type=cli_type, skip_error_check=True)

            if output and isinstance(output, str):
                # Check if network prefix appears in the raw output
                if network in output:
                    st.log(f"Route {network} found in routing table on {dut}")
                    st.log(f"Raw output snippet: {output[:500]}")
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
            commands.append("no shutdown")
            commands.append("exit")
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            # Remove IPv4 configuration from advertised network interface (DUT1 only)
            if dut == data.dut1:
                commands = []
                commands.append(f"interface {data.advertised_network_interface}")
                commands.append(f"no ip address {data.advertised_network_ip}/{data.advertised_network_mask}")
                commands.append("no shutdown")
                commands.append("exit")
                st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            st.log(f"Cleaned up configuration on {dut}")

        except Exception as e:
            st.error(f"Error during cleanup on {dut}: {str(e)}")

    st.log("Cleanup completed")


class TestIpv4BgpLinkFlap:
    """
    Test class for IPv4 BGP link flap test (interface down unexpectedly).
    """

    def test_ipv4_bgp_link_flap_storm(self):
        """
        Test: Verify BGP behavior during link flap storm (interface down unexpectedly).

        Steps:
        1. Check and remove existing IPv4 addresses
        2. Configure interface MTU and speed
        3. Configure IPv4 addresses on physical interfaces
        4. Verify IPv4 connectivity
        5. Remove existing BGP configuration
        6. Configure BGP with router IDs
        7. Configure BGP neighbors
        8. DUT1: Configure advertised network interface (for BGP to advertise)
        9. DUT1: Advertise network
        10. Verify BGP sessions establish
        11. Verify route is installed on DUT2
        12. Simulate link flap storm on DUT1's interface (5 flaps)
        13. Verify BGP session recovers after flaps
        14. Verify route is re-installed after recovery
        """
        st.banner("TEST: IPv4 BGP Link Flap Storm (Interface Down Unexpectedly)")

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

        # Step 6: Configure BGP routers with router IDs
        st.log("Step 6: Configuring BGP routers with router IDs")

        if not configure_bgp_router_with_router_id(data.dut1, data.bgp_asn, data.router_id_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        if not configure_bgp_router_with_router_id(data.dut2, data.bgp_asn, data.router_id_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        # Step 7: Configure BGP neighbors
        st.log("Step 7: Configuring BGP neighbors")

        if not configure_bgp_neighbor(data.dut1, data.bgp_asn, data.dut2_ipv4, data.bgp_asn, data.af_ipv4, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        if not configure_bgp_neighbor(data.dut2, data.bgp_asn, data.dut1_ipv4, data.bgp_asn, data.af_ipv4, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut2}")

        # Step 8: Configure advertised network interface on DUT1 (needed for BGP to advertise)
        st.log("Step 8: Configuring advertised network interface on DUT1")
        st.log(f"Interface: {data.advertised_network_interface}, IP: {data.advertised_network_ip}/{data.advertised_network_mask}")

        if not configure_ipv4_interface(data.dut1, data.advertised_network_interface,
                                         data.advertised_network_ip, data.advertised_network_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure advertised network interface on {data.dut1}")

        # Step 9: DUT1 advertises network
        st.log("Step 9: DUT1 advertising network")
        st.log(f"Network: {data.advertised_network}")

        if not advertise_network(data.dut1, data.bgp_asn, data.advertised_network, data.af_ipv4, data.cli_type):
            st.report_fail("msg", f"Failed to advertise network on {data.dut1}")

        # Step 10: Verify BGP sessions establish
        st.log("Step 10: Verifying BGP sessions establish")

        st.wait(data.bgp_wait, "Waiting for BGP sessions to establish")

        if not verify_bgp_neighbor_state(data.dut1, data.dut2_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not established on {data.dut1}")

        if not verify_bgp_neighbor_state(data.dut2, data.dut1_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not established on {data.dut2}")

        st.log("BGP sessions established successfully")

        # Step 11: Verify route is installed on DUT2
        st.log("Step 11: Verifying route is installed on DUT2")

        if not verify_route_in_routing_table(data.dut2, data.advertised_network_prefix, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"Route not installed on {data.dut2}")

        st.log("Route installed successfully on DUT2")

        # Step 12: Simulate link flap storm on DUT1's interface
        st.log("Step 12: Simulating link flap storm on DUT1's interface")
        st.log(f"Performing {data.flap_count} flaps with {data.flap_interval} second intervals")

        if not simulate_link_flap_storm(data.dut1, data.dut1_dut2_port, data.flap_count,
                                         data.flap_interval, data.cli_type):
            st.report_fail("msg", f"Failed to simulate link flap storm on {data.dut1}")

        st.log("Link flap storm completed")

        # Step 13: Verify BGP session recovers after flaps
        st.log("Step 13: Verifying BGP session recovers after link flaps")

        st.wait(data.recovery_wait, f"Waiting {data.recovery_wait} seconds for BGP to recover")

        if not verify_bgp_neighbor_state(data.dut1, data.dut2_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not recovered on {data.dut1} after link flaps")

        if not verify_bgp_neighbor_state(data.dut2, data.dut1_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not recovered on {data.dut2} after link flaps")

        st.log("BGP sessions recovered successfully after link flaps")

        # Step 14: Verify route is re-installed after recovery
        st.log("Step 14: Verifying route is re-installed on DUT2 after recovery")

        if not verify_route_in_routing_table(data.dut2, data.advertised_network_prefix, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"Route not re-installed on {data.dut2} after recovery")

        st.log("Route re-installed successfully on DUT2 after recovery")

        st.log("TEST PASSED: BGP recovered successfully after link flap storm")

        st.report_pass("test_case_passed")
