"""
IPv6 iBGP OVER LOOPBACK INTERFACES
Author: Prajwal


How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv6_bgp_loopback.py \
  --logs-path ./logs/test_ipv6_bgp_loopback_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IPv6 iBGP peering over Loopback interfaces using Klish CLI.
  This test suite configures loopback interfaces with /128 addresses, establishes iBGP
  sessions using loopback as update-source, and validates BGP neighborship. The test
  uses static routes for loopback reachability (underlay) and verifies that BGP sessions
  establish successfully over loopback interfaces.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with Loopback peering
        # +-------------------------+                       +-------------------------+
        # |      DUT1               |                       |      DUT2               |
        # | Loopback0: 2001:db8::1  |                       | Loopback0: 2001:db8::2  |
        # | Eth32: 2001:db8:1::1/64 |=======================| Eth32: 2001:db8:1::2/64 |
        # | (192.168.100.57)        |                       | (192.168.100.172)       |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: AS 65001 (iBGP), IPv6 Unicast address family
  - BGP Peering: Over Loopback interfaces using update-source
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
# Physical interface IPs (underlay)
data.dut1_ipv6 = "2001:db8:1::1"
data.dut2_ipv6 = "2001:db8:1::2"
data.ipv6_mask = "64"
# Loopback IPs (overlay - BGP peering)
data.dut1_loopback = "2001:db8::1"
data.dut2_loopback = "2001:db8::2"
data.loopback_mask = "128"
data.loopback_interface = "Loopback0"
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
data.ebgp_multihop = "2"


@pytest.fixture(scope="module", autouse=True)
def ipv6_bgp_loopback_module_hooks(request):
    """
    Module-level fixture for IPv6 BGP Loopback test setup and teardown.
    Sets up 2-node topology and configures interfaces.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv6 BGP Loopback Test")

    # Store DUT handles for easy access
    data.dut1 = vars.D1
    data.dut2 = vars.D2
    data.dut1_dut2_port = vars.D1D2P1
    data.dut2_dut1_port = vars.D2D1P1

    # Log topology information
    st.log(f"DUT1: {data.dut1}")
    st.log(f"DUT2: {data.dut2}")
    st.log(f"DUT1-DUT2 Ports: {data.dut1_dut2_port} <-> {data.dut2_dut1_port}")

    # Get UI type for the test
    data.shell_vtysh = st.get_ui_type()
    if data.shell_vtysh == "click":
        data.shell_vtysh = "vtysh"

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up IPv6 BGP Loopback configuration")
    cleanup_bgp_ipv6_loopback_config()


@pytest.fixture(scope="function", autouse=True)
def ipv6_bgp_loopback_func_hooks(request):
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
        command = f"show ipv6 interfaces"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        # Check if any IPv6 addresses are configured
        if output and "inet6" in output.lower():
            st.log(f"Found existing IPv6 address on {interface}, removing it")

            # Get list of IPv6 addresses to remove
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

        # Wait for interface to come up
        st.wait(2, "Waiting for interface to come up")
        return True
    except Exception as e:
        st.error(f"Failed to configure IPv6 address on {interface}: {str(e)}")
        return False


def configure_loopback_interface(dut, loopback_ip, mask, cli_type="klish"):
    """
    Configure Loopback interface with IPv6 address.

    Args:
        dut: Device under test
        loopback_ip: Loopback IPv6 address
        mask: Subnet mask (typically 128 for loopback)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring Loopback0 with IPv6 address {loopback_ip}/{mask} on {dut}")

    try:
        commands = []
        commands.append(f"interface {data.loopback_interface}")
        commands.append(f"ipv6 address {loopback_ip}/{mask}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured Loopback0 on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure Loopback0 on {dut}: {str(e)}")
        return False


def configure_static_route(dut, destination, nexthop, cli_type="klish"):
    """
    Configure IPv6 static route for loopback reachability.

    Args:
        dut: Device under test
        destination: Destination network (e.g., 2001:db8::2/128)
        nexthop: Next-hop IPv6 address
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring static route {destination} via {nexthop} on {dut}")

    try:
        commands = [f"ipv6 route {destination} {nexthop}"]
        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured static route on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure static route on {dut}: {str(e)}")
        return False


def verify_ipv6_interface(dut, interface, ipv6_addr, mask):
    """
    Verify IPv6 address configuration on an interface.
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


def configure_bgp_neighbor_loopback(dut, local_asn, neighbor_ip, remote_asn,
                                     update_source, multihop, family="ipv6", cli_type="klish"):
    """
    Configure BGP neighbor with update-source Loopback and ebgp-multihop.

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbor_ip: Neighbor IPv6 loopback address
        remote_asn: Remote AS number
        update_source: Update source interface (e.g., Loopback0)
        multihop: ebgp-multihop value
        family: Address family (default: ipv6)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP neighbor {neighbor_ip} with update-source {update_source} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")
        commands.append(f"update-source interface {update_source}")
        commands.append(f"ebgp-multihop {multihop}")
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"activate")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor {neighbor_ip} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def verify_bgp_neighbor_state(dut, neighbor_ip, state='Established', family='ipv6', timeout=90, cli_type='klish'):
    """
    Verify BGP neighbor state.
    Enhanced validation to accept (Policy) state.
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


def save_config_all_duts():
    """
    Save configuration on all DUTs using 'write memory' command.
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


def cleanup_bgp_ipv6_loopback_config():
    """
    Clean up BGP, IPv6, Loopback, and static route configuration from all DUTs.
    """
    st.log("Cleaning up BGP and IPv6 configuration")

    dut_list = [data.dut1, data.dut2]

    for dut in dut_list:
        try:
            # Remove BGP configuration
            bgp_api.enable_docker_routing_config_mode(dut, cli_type=data.cli_type)
            commands = ["no router bgp"]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            # Remove static routes
            if dut == data.dut1:
                commands = [f"no ipv6 route {data.dut2_loopback}/{data.loopback_mask} {data.dut2_ipv6}"]
            else:
                commands = [f"no ipv6 route {data.dut1_loopback}/{data.loopback_mask} {data.dut1_ipv6}"]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            # Remove loopback interface
            commands = [f"no interface {data.loopback_interface}"]
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


class TestIpv6BgpLoopback:
    """
    Test class for IPv6 BGP over Loopback interfaces.
    """

    def test_ipv6_bgp_loopback_config_verify(self):
        """
        Test IPv6 BGP peering over Loopback interfaces.

        Steps:
        1. Check and remove existing IPv6 addresses
        2. Configure physical interface MTU and speed
        3. Configure physical interfaces with IPv6 (underlay)
        4. Verify physical IPv6 configuration
        5. Test physical IPv6 connectivity
        6. Configure loopback interfaces
        7. Verify loopback configuration
        8. Configure static routes for loopback reachability
        9. Remove existing BGP configuration
        10. Configure BGP routers with router IDs
        11. Configure BGP neighbors with update-source Loopback0
        12. Verify BGP sessions establish over loopback

        Note: Loopback reachability is proven by BGP session establishment,
              so explicit loopback ping is not performed.
        """
        st.banner("TEST: IPv6 BGP over Loopback Configuration and Verification")

        # Step 1: Check and remove existing IPv6 addresses
        st.log("Step 1: Checking and removing existing IPv6 addresses from interfaces")

        check_and_remove_ipv6_address(data.dut1, data.dut1_dut2_port, data.cli_type)
        check_and_remove_ipv6_address(data.dut2, data.dut2_dut1_port, data.cli_type)

        # Step 2: Configure interface MTU and speed
        st.log("Step 2: Configuring interface MTU and speed on both DUTs")

        if not configure_interface_mtu_speed(data.dut1, data.dut1_dut2_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut1}")

        if not configure_interface_mtu_speed(data.dut2, data.dut2_dut1_port, data.mtu, data.speed, data.cli_type):
            st.report_fail("msg", f"Failed to configure MTU/speed on {data.dut2}")

        # Step 3: Configure IPv6 addresses on physical interfaces (underlay)
        st.log("Step 3: Configuring IPv6 addresses on physical interfaces (underlay)")

        if not configure_ipv6_interface(data.dut1, data.dut1_dut2_port, data.dut1_ipv6, data.ipv6_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv6 on {data.dut1}")

        if not configure_ipv6_interface(data.dut2, data.dut2_dut1_port, data.dut2_ipv6, data.ipv6_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv6 on {data.dut2}")

        # Step 4: Verify IPv6 configuration on physical interfaces
        st.log("Step 4: Verifying IPv6 configuration on physical interfaces")

        if not verify_ipv6_interface(data.dut1, data.dut1_dut2_port, data.dut1_ipv6, data.ipv6_mask):
            st.report_fail("msg", f"IPv6 verification failed on {data.dut1}")

        if not verify_ipv6_interface(data.dut2, data.dut2_dut1_port, data.dut2_ipv6, data.ipv6_mask):
            st.report_fail("msg", f"IPv6 verification failed on {data.dut2}")

        # Step 5: Test IPv6 connectivity on physical interfaces
        st.log("Step 5: Testing IPv6 connectivity on physical interfaces")

        if not ping_ipv6(data.dut1, data.dut2_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut1} to {data.dut2} failed")

        if not ping_ipv6(data.dut2, data.dut1_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut2} to {data.dut1} failed")

        # Step 6: Configure Loopback interfaces
        st.log("Step 6: Configuring Loopback interfaces on both DUTs")

        if not configure_loopback_interface(data.dut1, data.dut1_loopback, data.loopback_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure Loopback0 on {data.dut1}")

        if not configure_loopback_interface(data.dut2, data.dut2_loopback, data.loopback_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure Loopback0 on {data.dut2}")

        # Step 7: Verify Loopback configuration
        st.log("Step 7: Verifying Loopback configuration on both DUTs")

        if not verify_ipv6_interface(data.dut1, data.loopback_interface, data.dut1_loopback, data.loopback_mask):
            st.report_fail("msg", f"Loopback verification failed on {data.dut1}")

        if not verify_ipv6_interface(data.dut2, data.loopback_interface, data.dut2_loopback, data.loopback_mask):
            st.report_fail("msg", f"Loopback verification failed on {data.dut2}")

        # Step 8: Configure static routes for loopback reachability
        st.log("Step 8: Configuring static routes for loopback reachability")

        # DUT1: route to DUT2's loopback via DUT2's physical IP
        if not configure_static_route(data.dut1, f"{data.dut2_loopback}/{data.loopback_mask}",
                                       data.dut2_ipv6, data.cli_type):
            st.report_fail("msg", f"Failed to configure static route on {data.dut1}")

        # DUT2: route to DUT1's loopback via DUT1's physical IP
        if not configure_static_route(data.dut2, f"{data.dut1_loopback}/{data.loopback_mask}",
                                       data.dut1_ipv6, data.cli_type):
            st.report_fail("msg", f"Failed to configure static route on {data.dut2}")

        # Step 9: Remove existing BGP configuration
        st.log("Step 9: Removing existing BGP configuration from both DUTs")

        remove_bgp_config(data.dut1, data.cli_type)
        remove_bgp_config(data.dut2, data.cli_type)

        st.wait(5, "Waiting after BGP cleanup")

        # Step 10: Configure BGP routers with router IDs
        st.log("Step 10: Configuring BGP routers with router IDs on both DUTs")

        if not configure_bgp_router_with_router_id(data.dut1, data.bgp_asn, data.router_id_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        if not configure_bgp_router_with_router_id(data.dut2, data.bgp_asn, data.router_id_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        # Step 11: Configure BGP neighbors with update-source Loopback0
        st.log("Step 11: Configuring BGP neighbors with update-source Loopback0")

        # DUT1 peers with DUT2's loopback
        if not configure_bgp_neighbor_loopback(
            data.dut1, data.bgp_asn, data.dut2_loopback, data.bgp_asn,
            data.loopback_interface, data.ebgp_multihop, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        # DUT2 peers with DUT1's loopback
        if not configure_bgp_neighbor_loopback(
            data.dut2, data.bgp_asn, data.dut1_loopback, data.bgp_asn,
            data.loopback_interface, data.ebgp_multihop, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut2}")

        # Step 12: Wait and verify BGP session establishment
        st.log("Step 12: Verifying BGP session establishment over Loopback")
        st.wait(data.bgp_wait, "Waiting for BGP session establishment")

        # Verify DUT1 <-> DUT2 session
        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_loopback, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        # Verify DUT2 <-> DUT1 session
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_loopback, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP session failed to establish over Loopback on one or both DUTs")

        st.log("IPv6 BGP over Loopback configuration and verification test PASSED")
        st.report_pass("test_case_passed")

    def test_ipv6_bgp_loopback_save_reboot(self):
        """
        Test IPv6 BGP over Loopback persistence after save and reboot.

        Steps:
        1. Verify BGP sessions are established
        2. Save configuration on both DUTs
        3. Reboot both DUTs
        4. Verify BGP sessions after reboot
        """
        st.banner("TEST: IPv6 BGP over Loopback Persistence After Reboot")

        # Step 1: Verify BGP sessions before reboot
        st.log("Step 1: Verifying BGP sessions before reboot")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_loopback, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_loopback, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP sessions not established before reboot")

        # Step 2: Save configuration
        st.log("Step 2: Saving configuration on all DUTs")

        if not save_config_all_duts():
            st.report_fail("msg", "Failed to save configuration")

        # Step 3: Reboot DUTs
        st.log("Step 3: Rebooting all DUTs")

        for dut in [data.dut1, data.dut2]:
            st.log(f"Rebooting {dut}")
            st.reboot(dut, "fast")

        st.wait(data.reboot_wait, "Waiting for DUTs to reboot and stabilize")

        # Step 4: Verify BGP sessions after reboot
        st.log("Step 4: Verifying BGP sessions after reboot")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_loopback, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_loopback, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP sessions failed to establish after reboot")

        st.log("IPv6 BGP over Loopback persistence after reboot test PASSED")
        st.report_pass("test_case_passed")
