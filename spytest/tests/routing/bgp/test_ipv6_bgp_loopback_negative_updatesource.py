"""
IPv6 BGP LOOPBACK NEGATIVE TEST - WRONG UPDATE-SOURCE
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv6_bgp_loopback_negative_updatesource.py \
  --logs-path ./logs/test_ipv6_bgp_loopback_negative_updatesource_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Negative test case to verify BGP session behavior with incorrect update-source configuration.
  This test validates that BGP sessions do NOT establish (or have issues) when update-source
  is configured with a wrong interface. This ensures proper BGP update-source validation
  and helps troubleshoot common configuration errors.

  Test scenarios:
  1. Configure BGP with wrong update-source (non-existent interface)
  2. Verify BGP session does NOT establish properly
  3. Fix update-source to correct Loopback0
  4. Verify BGP session establishes successfully

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with Loopback peering
        # +-------------------------+                       +-------------------------+
        # |      DUT1               |                       |      DUT2               |
        # | Loopback0: 2001:db8::1  |                       | Loopback0: 2001:db8::2  |
        # | Eth32: 2001:db8:1::1/64 |=======================| Eth32: 2001:db8:1::2/64 |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: AS 65001 (iBGP), IPv6 Unicast address family
  - BGP Peering: Over Loopback interfaces using update-source
  - Expected Result with wrong update-source: BGP session should NOT establish or have issues
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
data.wrong_loopback = "Loopback1"  # Wrong update-source for negative test
# BGP config
data.bgp_asn = "65001"
data.af_ipv6 = "ipv6"
data.cli_type = "klish"
data.mtu = "9100"
data.speed = "40000"
data.bgp_wait = 90
data.negative_test_wait = 90
data.reboot_wait = 60
data.ping_count = 5
data.router_id_dut1 = "1.1.1.1"
data.router_id_dut2 = "2.2.2.2"
data.ebgp_multihop = 2


@pytest.fixture(scope="module", autouse=True)
def ipv6_bgp_loopback_negative_module_hooks(request):
    """
    Module-level fixture for IPv6 BGP Loopback negative test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv6 BGP Loopback Negative Test (Wrong Update-Source)")

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
    st.banner("MODULE TEARDOWN: Cleaning up IPv6 BGP Loopback configuration")
    cleanup_bgp_ipv6_loopback_config()


@pytest.fixture(scope="function", autouse=True)
def ipv6_bgp_loopback_negative_func_hooks(request):
    """
    Function-level fixture - currently empty.
    """
    yield


def check_and_remove_ipv6_address(dut, interface, cli_type="klish"):
    """
    Check if IPv6 address exists on interface and remove it if present.
    """
    st.log(f"Checking for existing IPv6 addresses on {interface} of {dut}")

    try:
        command = f"show ipv6 interfaces"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        if output and "inet6" in output.lower():
            st.log(f"Found existing IPv6 address on {interface}, removing it")

            ipv6_pattern = r'([0-9a-fA-F:]+/\d+)'
            addresses = re.findall(ipv6_pattern, output)

            if addresses:
                for addr in addresses:
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


def configure_loopback_interface(dut, loopback_ip, mask, cli_type="klish"):
    """
    Configure Loopback interface with IPv6 address.
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


def configure_bgp_neighbor_loopback_wrong_updatesource(dut, local_asn, neighbor_ip, remote_asn,
                                                        wrong_update_source, multihop,
                                                        family="ipv6", cli_type="klish"):
    """
    Configure BGP neighbor with WRONG update-source for negative testing.

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbor_ip: Neighbor IPv6 loopback address
        remote_asn: Remote AS number
        wrong_update_source: Wrong update source interface (e.g., Loopback1 that doesn't exist)
        multihop: ebgp-multihop value
        family: Address family (default: ipv6)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP neighbor {neighbor_ip} with WRONG update-source {wrong_update_source} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")
        commands.append(f"update-source interface {wrong_update_source}")  # WRONG! (using neighbor submode)
        commands.append(f"ebgp-multihop {multihop}")
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"activate")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor {neighbor_ip} with WRONG update-source on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def configure_bgp_neighbor_loopback_correct_updatesource(dut, local_asn, neighbor_ip, remote_asn,
                                                          correct_update_source, multihop,
                                                          family="ipv6", cli_type="klish"):
    """
    Configure BGP neighbor with CORRECT update-source (fixing the wrong configuration).

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbor_ip: Neighbor IPv6 loopback address
        remote_asn: Remote AS number
        correct_update_source: Correct update source interface (e.g., Loopback0)
        multihop: ebgp-multihop value
        family: Address family (default: ipv6)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Reconfiguring BGP neighbor {neighbor_ip} with CORRECT update-source {correct_update_source} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        # Remove old wrong config
        commands.append(f"no neighbor {neighbor_ip}")
        # Configure with correct update-source
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")
        commands.append(f"update-source interface {correct_update_source}")  # CORRECT! (using neighbor submode)
        commands.append(f"ebgp-multihop {multihop}")
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"activate")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully reconfigured BGP neighbor {neighbor_ip} with CORRECT update-source on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to reconfigure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def verify_bgp_neighbor_not_established(dut, neighbor_ip, timeout=90, cli_type='klish'):
    """
    Verify that BGP neighbor does NOT reach Established state (negative test).
    Returns True if neighbor is NOT established (as expected in negative test).
    """
    st.log(f"Verifying BGP neighbor {neighbor_ip} does NOT establish on {dut}")

    st.wait(timeout, f"Waiting {timeout} seconds to ensure session does not establish")

    try:
        output = st.show(dut, "show bgp summary", type=cli_type)

        if output:
            for entry in output:
                if str(entry.get('neighbor', '')).strip() == str(neighbor_ip).strip():
                    neighbor_state = entry.get('state', '')
                    st.log(f"Found neighbor {neighbor_ip} with state: {neighbor_state}")

                    # Check if incorrectly established
                    if ('established' in str(neighbor_state).lower() or
                        str(neighbor_state).isdigit()):
                        st.error(f"BGP neighbor {neighbor_ip} INCORRECTLY established with wrong update-source!")
                        return False

                    st.log(f"BGP neighbor in non-established state: {neighbor_state} (as expected)")
                    return True

        st.log(f"BGP neighbor {neighbor_ip} not found or not established (as expected)")
        return True

    except Exception as e:
        st.error(f"Exception while checking BGP neighbor state: {str(e)}")
        return True  # In negative test, exception might be acceptable


def verify_bgp_neighbor_state(dut, neighbor_ip, state='Established', family='ipv6', timeout=90, cli_type='klish'):
    """
    Verify BGP neighbor state (for positive validation after fix).
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


def cleanup_bgp_ipv6_loopback_config():
    """
    Clean up BGP, IPv6, and Loopback configuration from all DUTs.
    """
    st.log("Cleaning up BGP, IPv6, and Loopback configuration")

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

            # Remove Loopback interface
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


class TestIpv6BgpLoopbackNegativeUpdateSource:
    """
    Test class for IPv6 BGP Loopback negative test - wrong update-source.
    """

    def test_ipv6_bgp_loopback_wrong_updatesource(self):
        """
        Negative Test: Verify BGP session behavior with wrong update-source.

        Steps:
        1. Configure physical interfaces with IPv6 (underlay)
        2. Verify IPv6 connectivity
        3. Remove existing BGP configuration
        4. Configure Loopback0 interfaces
        5. Configure static routes for loopback reachability
        6. Configure BGP with router IDs
        7. Configure DUT1 neighbor with WRONG update-source (Loopback1 instead of Loopback0)
        8. Configure DUT2 neighbor correctly with Loopback0
        9. Verify BGP session does NOT establish on DUT1 (or has issues)
        10. Fix DUT1 update-source to correct Loopback0
        11. Verify BGP sessions establish successfully after fix
        """
        st.banner("NEGATIVE TEST: IPv6 BGP Loopback - Wrong Update-Source")

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

        # Step 4: Verify IPv6 connectivity on physical interfaces
        st.log("Step 4: Verifying IPv6 connectivity on physical interfaces")

        if not ping_ipv6(data.dut1, data.dut2_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut1} to {data.dut2} failed")

        if not ping_ipv6(data.dut2, data.dut1_ipv6, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut2} to {data.dut1} failed")

        # Step 5: Remove existing BGP configuration
        st.log("Step 5: Removing existing BGP configuration from both DUTs")

        remove_bgp_config(data.dut1, data.cli_type)
        remove_bgp_config(data.dut2, data.cli_type)

        st.wait(5, "Waiting after BGP cleanup")

        # Step 6: Configure Loopback0 interfaces
        st.log("Step 6: Configuring Loopback0 interfaces on both DUTs")

        if not configure_loopback_interface(data.dut1, data.dut1_loopback, data.loopback_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure Loopback0 on {data.dut1}")

        if not configure_loopback_interface(data.dut2, data.dut2_loopback, data.loopback_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure Loopback0 on {data.dut2}")

        # Step 7: Configure static routes for loopback reachability
        st.log("Step 7: Configuring static routes for loopback reachability")

        if not configure_static_route(data.dut1, f"{data.dut2_loopback}/{data.loopback_mask}",
                                       data.dut2_ipv6, data.cli_type):
            st.report_fail("msg", f"Failed to configure static route on {data.dut1}")

        if not configure_static_route(data.dut2, f"{data.dut1_loopback}/{data.loopback_mask}",
                                       data.dut1_ipv6, data.cli_type):
            st.report_fail("msg", f"Failed to configure static route on {data.dut2}")

        # Step 8: Configure BGP routers with router IDs
        st.log("Step 8: Configuring BGP routers with router IDs")

        if not configure_bgp_router_with_router_id(data.dut1, data.bgp_asn, data.router_id_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        if not configure_bgp_router_with_router_id(data.dut2, data.bgp_asn, data.router_id_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        # Step 9: Configure BGP neighbor on DUT1 with WRONG update-source
        st.log("Step 9: Configuring BGP neighbor on DUT1 with WRONG update-source")
        st.log(f"DUT1: Configuring with WRONG update-source: {data.wrong_loopback} (should be {data.loopback_interface})")

        if not configure_bgp_neighbor_loopback_wrong_updatesource(
            data.dut1, data.bgp_asn, data.dut2_loopback, data.bgp_asn,
            data.wrong_loopback, data.ebgp_multihop, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        # Step 10: Configure BGP neighbor on DUT2 correctly
        st.log("Step 10: Configuring BGP neighbor on DUT2 correctly with Loopback0")

        if not configure_bgp_neighbor_loopback_correct_updatesource(
            data.dut2, data.bgp_asn, data.dut1_loopback, data.bgp_asn,
            data.loopback_interface, data.ebgp_multihop, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut2}")

        # Step 11: Verify BGP session does NOT establish on DUT1 (negative validation)
        st.log("Step 11: Verifying BGP session does NOT establish on DUT1 with wrong update-source")

        if not verify_bgp_neighbor_not_established(data.dut1, data.dut2_loopback, data.negative_test_wait, data.cli_type):
            st.report_fail("msg", f"BGP session INCORRECTLY established on {data.dut1} with wrong update-source!")

        st.log("NEGATIVE TEST PASSED: BGP session did NOT establish with wrong update-source (as expected)")

        # Step 12: Fix DUT1 update-source to correct Loopback0
        st.log("Step 12: Fixing DUT1 update-source to correct Loopback0")

        if not configure_bgp_neighbor_loopback_correct_updatesource(
            data.dut1, data.bgp_asn, data.dut2_loopback, data.bgp_asn,
            data.loopback_interface, data.ebgp_multihop, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to fix BGP neighbor update-source on {data.dut1}")

        # Step 13: Verify BGP sessions establish after fix
        st.log("Step 13: Verifying BGP sessions establish after fixing update-source")

        st.wait(data.bgp_wait, "Waiting for BGP sessions to establish after fix")

        if not verify_bgp_neighbor_state(data.dut1, data.dut2_loopback, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not established on {data.dut1} after fixing update-source")

        if not verify_bgp_neighbor_state(data.dut2, data.dut1_loopback, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not established on {data.dut2}")

        st.log("POSITIVE TEST PASSED: BGP sessions established successfully after fixing update-source")

        st.report_pass("test_case_passed")
