"""
IPv4 BGP NEGATIVE TEST - WRONG ASN CONFIGURATION
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv4_bgp_negative_asn.py \
  --logs-path ./logs/test_ipv4_bgp_negative_asn_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Negative test case to verify BGP session behavior with incorrect ASN configuration.
  This test validates that BGP sessions do NOT establish when there is an ASN mismatch
  between configured neighbor AS and actual remote AS. This ensures proper BGP validation
  and prevents unintended peering relationships.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +-------------------------+                       +-------------------------+
        # |      DUT1 (AS 65001)    |                       |      DUT2 (AS 65002)    |
        # | Eth32 10.1.1.1/24  |=======================| Eth32 10.1.1.2/24  |
        # | (192.168.100.57)        |                       | (192.168.100.172)       |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: DUT1 AS 65001, DUT2 AS 65002
  - DUT1 configured with WRONG remote-as (65003 instead of 65002)
  - Expected Result: BGP session should NOT establish
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
data.dut1_ipv4 = "10.1.1.1"
data.dut2_ipv4 = "10.1.1.2"
data.ipv4_mask = "24"
data.dut1_bgp_asn = "65001"  # DUT1's actual AS
data.dut2_bgp_asn = "65002"  # DUT2's actual AS
data.wrong_asn = "65003"     # Wrong AS configured on DUT1 for DUT2
data.af_ipv4 = "ipv4"
data.cli_type = "klish"
data.mtu = "9100"
data.speed = "40000"
data.bgp_wait = 90
data.ping_count = 5
data.router_id_dut1 = "1.1.1.1"
data.router_id_dut2 = "2.2.2.2"


@pytest.fixture(scope="module", autouse=True)
def ipv4_bgp_negative_asn_module_hooks(request):
    """
    Module-level fixture for IPv4 BGP negative ASN test setup and teardown.
    """
    global vars

    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv4 BGP Negative ASN Test")

    data.dut1 = vars.D1
    data.dut2 = vars.D2
    data.dut1_dut2_port = vars.D1D2P1
    data.dut2_dut1_port = vars.D2D1P1

    st.log(f"DUT1: {data.dut1}")
    st.log(f"DUT2: {data.dut2}")
    st.log(f"DUT1-DUT2 Ports: {data.dut1_dut2_port} <-> {data.dut2_dut1_port}")

    data.shell_vtysh = st.get_ui_type()
    if data.shell_vtysh == "click":
        data.shell_vtysh = "vtysh"

    yield

    st.banner("MODULE TEARDOWN: Cleaning up IPv4 BGP negative ASN test configuration")
    cleanup_bgp_ipv4_config()


@pytest.fixture(scope="function", autouse=True)
def ipv4_bgp_negative_asn_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
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

            ipv4_pattern = r'([0-9.]+/\d+)'
            addresses = re.findall(ipv4_pattern, output)

            if addresses:
                for addr in addresses:
                    
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


def verify_ipv4_interface(dut, interface, ipv4_addr, mask):
    """
    Verify IPv4 address configuration on an interface.
    """
    st.log(f"Verifying IPv4 address {ipv4_addr}/{mask} on {interface} for {dut}")

    try:
        command = f"show ip interfaces"
        output = st.config(dut, command, type="click", skip_error_check=True)

        st.log(f"Raw output from '{command}': {output}")

        expected_ip = f"{ipv4_addr}/{mask}"

        if output and isinstance(output, str):
            pattern = rf'{interface}\s+({ipv4_addr}/{mask})'
            match = re.search(pattern, output, re.IGNORECASE)

            if match:
                st.log(f"Successfully verified IPv4 address {expected_ip} on {interface}")
                return True
            else:
                if interface in output and expected_ip in output:
                    st.log(f"Successfully verified IPv4 address {expected_ip} on {interface} (simple match)")
                    return True

        st.error(f"Failed to verify IPv4 address {expected_ip} on {interface}")
        return False

    except Exception as e:
        st.error(f"Exception during IPv4 verification: {str(e)}")
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


def configure_route_map(dut, route_map_name="ALLOW-ALL", sequence=10, action="permit", cli_type="klish"):
    """
    Configure route-map before BGP configuration to avoid Policy warning in show bgp summary.
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
        commands.append(f"route-map ALLOW-ALL in")
        commands.append(f"route-map ALLOW-ALL out")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor {neighbor_ip} with route-maps on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def verify_bgp_neighbor_not_established(dut, neighbor_ip, timeout=90, cli_type='klish'):
    """
    Verify that BGP neighbor does NOT reach Established state (negative test).

    Args:
        dut: Device under test
        neighbor_ip: Neighbor IPv4 address
        timeout: Timeout in seconds to wait
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if neighbor is NOT established (as expected), False if it establishes
    """
    st.log(f"Verifying BGP neighbor {neighbor_ip} does NOT establish on {dut}")

    # Wait for the timeout period to see if session incorrectly establishes
    st.wait(timeout, f"Waiting {timeout} seconds to ensure session does not establish")

    try:
        output = st.show(dut, "show bgp summary", type=cli_type)

        if output:
            for entry in output:
                if str(entry.get('neighbor', '')).strip() == str(neighbor_ip).strip():
                    neighbor_state = entry.get('state', '')
                    st.log(f"Found neighbor {neighbor_ip} with state: {neighbor_state}")

                    # Check if state is Established or numeric (active)
                    if ('established' in str(neighbor_state).lower() or
                        str(neighbor_state).isdigit()):
                        st.error(f"BGP neighbor {neighbor_ip} INCORRECTLY established with wrong ASN!")
                        return False

                    # If state is something like "Active", "Connect", "Idle", that's expected
                    st.log(f"BGP neighbor {neighbor_ip} is in non-established state: {neighbor_state} (as expected)")
                    return True

        # If neighbor not found in output, that's also acceptable
        st.log(f"BGP neighbor {neighbor_ip} not found in summary (acceptable for wrong ASN)")
        return True

    except Exception as e:
        st.error(f"Exception during BGP state check: {str(e)}")
        return False


def verify_bgp_neighbor_state(dut, neighbor_ip, state='Established', family='ipv4', timeout=90, cli_type='klish'):
    """
    Verify BGP neighbor state (for positive verification).
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

            # Remove IPv4 configuration from interfaces
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


class TestIpv6BgpNegativeAsn:
    """
    Test class for IPv4 BGP negative test with wrong ASN.
    """

    def test_ipv4_bgp_wrong_asn_no_establish(self):
        """
        Negative Test: Verify BGP session does NOT establish with wrong ASN.

        Steps:
        1. Configure physical interfaces with IPv4
        2. Verify IPv4 connectivity
        3. Remove existing BGP configuration
        4. Configure DUT1 with AS 65001
        5. Configure DUT2 with AS 65002
        6. Configure DUT1 neighbor with WRONG remote-as 65003 (should be 65002)
        7. Configure DUT2 neighbor correctly with remote-as 65001
        8. Verify BGP session does NOT establish on DUT1
        9. Verify BGP session does NOT establish on DUT2
        """
        st.banner("NEGATIVE TEST: IPv4 BGP Wrong ASN - Session Should NOT Establish")

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

        # Step 3: Configure IPv4 addresses on interfaces
        st.log("Step 3: Configuring IPv4 addresses on both DUTs")

        if not configure_ipv4_interface(data.dut1, data.dut1_dut2_port, data.dut1_ipv4, data.ipv4_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv4 on {data.dut1}")

        if not configure_ipv4_interface(data.dut2, data.dut2_dut1_port, data.dut2_ipv4, data.ipv4_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IPv4 on {data.dut2}")

        # Step 4: Verify IPv4 configuration
        st.log("Step 4: Verifying IPv4 configuration on both DUTs")

        if not verify_ipv4_interface(data.dut1, data.dut1_dut2_port, data.dut1_ipv4, data.ipv4_mask):
            st.report_fail("msg", f"IPv4 verification failed on {data.dut1}")

        if not verify_ipv4_interface(data.dut2, data.dut2_dut1_port, data.dut2_ipv4, data.ipv4_mask):
            st.report_fail("msg", f"IPv4 verification failed on {data.dut2}")

        # Step 5: Test IPv4 connectivity
        st.log("Step 5: Testing IPv4 connectivity before BGP configuration")

        if not ping_ipv4(data.dut1, data.dut2_ipv4, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut1} to {data.dut2} failed before BGP")

        if not ping_ipv4(data.dut2, data.dut1_ipv4, data.ping_count):
            st.report_fail("msg", f"Ping from {data.dut2} to {data.dut1} failed before BGP")

        # Step 6: Remove existing BGP configuration
        st.log("Step 6: Removing existing BGP configuration from both DUTs")

        remove_bgp_config(data.dut1, data.cli_type)
        remove_bgp_config(data.dut2, data.cli_type)

        st.wait(5, "Waiting after BGP cleanup")

        # Step 7: Configure BGP routers with router IDs
        st.log("Step 7: Configuring BGP routers with different AS numbers")

        # Configure route-map on DUT1 (before BGP configuration to avoid Policy warning)
        if not configure_route_map(data.dut1, "ALLOW-ALL", 10, "permit", data.cli_type):
            st.report_fail("msg", f"Failed to configure route-map on {data.dut1}")

        if not configure_bgp_router_with_router_id(data.dut1, data.dut1_bgp_asn, data.router_id_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        # Configure route-map on DUT2 (before BGP configuration to avoid Policy warning)
        if not configure_route_map(data.dut2, "ALLOW-ALL", 10, "permit", data.cli_type):
            st.report_fail("msg", f"Failed to configure route-map on {data.dut2}")

        if not configure_bgp_router_with_router_id(data.dut2, data.dut2_bgp_asn, data.router_id_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        # Step 8: Configure BGP neighbors with WRONG ASN on DUT1
        st.log("Step 8: Configuring BGP neighbor on DUT1 with WRONG remote-as")
        st.log(f"DUT1 actual AS: {data.dut1_bgp_asn}")
        st.log(f"DUT2 actual AS: {data.dut2_bgp_asn}")
        st.log(f"DUT1 configuring neighbor with WRONG AS: {data.wrong_asn} (should be {data.dut2_bgp_asn})")

        # DUT1: Configure neighbor with WRONG remote AS (65003 instead of 65002)
        if not configure_bgp_neighbor(
            data.dut1, data.dut1_bgp_asn, data.dut2_ipv4, data.wrong_asn, data.af_ipv4, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        # Step 9: Configure BGP neighbor on DUT2 correctly
        st.log("Step 9: Configuring BGP neighbor on DUT2 with correct remote-as")

        # DUT2: Configure neighbor with CORRECT remote AS (65001)
        if not configure_bgp_neighbor(
            data.dut2, data.dut2_bgp_asn, data.dut1_ipv4, data.dut1_bgp_asn, data.af_ipv4, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut2}")

        # Step 10: Verify BGP session does NOT establish
        st.log("Step 10: Verifying BGP session does NOT establish (negative test)")

        # Verify DUT1 neighbor does not establish
        result1 = verify_bgp_neighbor_not_established(
            data.dut1, data.dut2_ipv4, data.bgp_wait, data.cli_type
        )

        if not result1:
            st.report_fail("msg", f"BGP session INCORRECTLY established on {data.dut1} with wrong ASN!")

        # Verify DUT2 neighbor does not establish
        result2 = verify_bgp_neighbor_not_established(
            data.dut2, data.dut1_ipv4, data.bgp_wait, data.cli_type
        )

        if not result2:
            st.report_fail("msg", f"BGP session INCORRECTLY established on {data.dut2} with wrong ASN!")

        st.log("NEGATIVE TEST PASSED: BGP session did NOT establish with wrong ASN (as expected)")
        st.report_pass("test_case_passed")

    def test_ipv4_bgp_correct_asn_after_fix(self):
        """
        Positive Test: Verify BGP session establishes after fixing ASN.

        Steps:
        1. Verify BGP is not established from previous test
        2. Fix DUT1 neighbor configuration with correct remote-as
        3. Verify BGP session establishes successfully
        """
        st.banner("POSITIVE TEST: IPv4 BGP Correct ASN - Session Should Establish After Fix")

        # Step 1: Fix BGP configuration on DUT1
        st.log("Step 1: Fixing BGP neighbor configuration on DUT1 with correct remote-as")

        # Remove old neighbor config
        try:
            bgp_api.enable_docker_routing_config_mode(data.dut1, cli_type=data.cli_type)
            commands = []
            commands.append(f"router bgp {data.dut1_bgp_asn}")
            commands.append(f"no neighbor {data.dut2_ipv4}")
            commands.append("exit")
            st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
        except Exception as e:
            st.log(f"Error removing old neighbor config: {str(e)}")

        st.wait(5, "Waiting after removing old neighbor config")

        # Configure with correct remote AS
        st.log(f"Configuring DUT1 neighbor with CORRECT remote-as {data.dut2_bgp_asn}")

        if not configure_bgp_neighbor(
            data.dut1, data.dut1_bgp_asn, data.dut2_ipv4, data.dut2_bgp_asn, data.af_ipv4, data.cli_type
        ):
            st.report_fail("msg", f"Failed to fix BGP neighbor configuration on {data.dut1}")

        # Step 2: Wait and verify BGP session establishment
        st.log("Step 2: Verifying BGP session establishes after ASN fix")
        st.wait(data.bgp_wait, "Waiting for BGP session establishment")

        # Verify DUT1 <-> DUT2 session
        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type
        )

        # Verify DUT2 <-> DUT1 session
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP session failed to establish even after fixing ASN")

        st.log("POSITIVE TEST PASSED: BGP session established successfully after fixing ASN")
        st.report_pass("test_case_passed")
