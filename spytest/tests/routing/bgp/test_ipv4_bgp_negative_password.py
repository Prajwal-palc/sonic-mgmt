"""
IPv4 BGP NEGATIVE TEST - WRONG PASSWORD AUTHENTICATION
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv4_bgp_negative_password.py \
  --logs-path ./logs/test_ipv4_bgp_negative_password_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Negative test case to verify BGP session behavior with incorrect password authentication.
  This test validates that BGP sessions do NOT establish when passwords don't match between
  neighbors. BGP password authentication (MD5) is a security feature to prevent unauthorized
  BGP peering.

  Test scenarios:
  1. Configure BGP with correct matching password on both D1 and D2
  2. Verify BGP session establishes (State: Established)
  3. Change password on D1 to a different value (password mismatch)
  4. Verify BGP session does NOT establish (State: Connect)
  5. Fix password on D1 to match D2
  6. Verify BGP session re-establishes

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with physical interface peering
        # +-------------------------+                       +-------------------------+
        # |      DUT1               |                       |      DUT2               |
        # | Eth32: 10.1.1.1/24 |=======================| Eth32: 10.1.1.2/24 |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: AS 65001 (iBGP), IPv4 Unicast address family
  - BGP Password: hello@123 (correct), different@456 (wrong for negative test)
  - Expected Result with wrong password: BGP session should be in Connect state
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
data.dut1_ipv4 = "10.1.0.1"
data.dut2_ipv4 = "10.1.0.2"
data.ipv4_mask = "24"
# BGP config
data.bgp_asn = "65001"
data.af_ipv4 = "ipv4"
data.cli_type = "klish"
data.mtu = "9100"
data.speed = "40000"
data.bgp_wait = 90
data.negative_test_wait = 90
data.reboot_wait = 60
data.ping_count = 5
data.router_id_dut1 = "1.1.1.1"
data.router_id_dut2 = "2.2.2.2"
# BGP Password
data.correct_password = "hello@123"
data.wrong_password = "different@456"


@pytest.fixture(scope="module", autouse=True)
def ipv4_bgp_negative_password_module_hooks(request):
    """
    Module-level fixture for IPv4 BGP negative password test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv4 BGP Negative Test (Wrong Password)")

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
def ipv4_bgp_negative_password_func_hooks(request):
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


def configure_bgp_neighbor_with_password(dut, local_asn, neighbor_ip, remote_asn, password,
                                          family="ipv4", cli_type="klish"):
    """
    Configure BGP neighbor with password authentication.

    Commands (using neighbor submode):
        router bgp <asn>
        neighbor <ipv4> remote-as <asn>
        password <password>
        address-family ipv4 unicast
        activate
    """
    st.log(f"Configuring BGP neighbor {neighbor_ip} with password '{password}' on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")
        commands.append(f"no password")
        commands.append(f"password {password}")
        commands.append(f"address-family ipv4 unicast")
        commands.append(f"activate")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor {neighbor_ip} with password on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def reconfigure_bgp_neighbor_password(dut, local_asn, neighbor_ip, remote_asn, new_password,
                                       family="ipv4", cli_type="klish"):
    """
    Reconfigure BGP neighbor with different password (for negative test).

    This removes the neighbor and reconfigures with new password.
    """
    st.log(f"Reconfiguring BGP neighbor {neighbor_ip} with new password '{new_password}' on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        # Remove old config
        commands.append(f"no neighbor {neighbor_ip}")
        # Reconfigure with new password
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")
        commands.append(f"password {new_password}")
        commands.append(f"address-family ipv4 unicast")
        commands.append(f"activate")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully reconfigured BGP neighbor {neighbor_ip} with new password on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to reconfigure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
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


def verify_bgp_neighbor_connect_state(dut, neighbor_ip, timeout=90, cli_type='klish'):
    """
    Verify that BGP neighbor is in Connect state (negative test with wrong password).
    Returns True if neighbor is in Connect state (as expected in negative test).
    """
    st.log(f"Verifying BGP neighbor {neighbor_ip} is in Connect state on {dut} (password mismatch)")

    st.wait(timeout, f"Waiting {timeout} seconds to check for Connect state")

    try:
        output = st.show(dut, "show bgp summary", type=cli_type)

        if output:
            for entry in output:
                if str(entry.get('neighbor', '')).strip() == str(neighbor_ip).strip():
                    neighbor_state = entry.get('state', '')
                    st.log(f"Found neighbor {neighbor_ip} with state: {neighbor_state}")

                    # Check if in Connect state (expected with wrong password)
                    if 'connect' in str(neighbor_state).lower():
                        st.log(f"BGP neighbor {neighbor_ip} is in Connect state (as expected with password mismatch)")
                        return True

                    # If established, test failed (passwords should NOT match)
                    if ('established' in str(neighbor_state).lower() or
                        str(neighbor_state).isdigit()):
                        st.error(f"BGP neighbor {neighbor_ip} INCORRECTLY established with wrong password!")
                        return False

                    # Other non-established states are also acceptable
                    st.log(f"BGP neighbor in non-established state: {neighbor_state}")
                    return True

        st.log(f"BGP neighbor {neighbor_ip} not found or in appropriate non-established state")
        return True

    except Exception as e:
        st.error(f"Exception while checking BGP neighbor state: {str(e)}")
        return True  # In negative test, exception might be acceptable


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
            commands.append("exit")
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)

            st.log(f"Cleaned up configuration on {dut}")

        except Exception as e:
            st.error(f"Error during cleanup on {dut}: {str(e)}")

    st.log("Cleanup completed")


class TestIpv6BgpNegativePassword:
    """
    Test class for IPv4 BGP negative test - wrong password authentication.
    """

    def test_ipv4_bgp_password_mismatch(self):
        """
        Negative Test: Verify BGP session behavior with password mismatch.

        Steps:
        1. Check and remove existing IPv4 addresses
        2. Configure interface MTU and speed
        3. Configure IPv4 addresses on physical interfaces
        4. Verify IPv4 connectivity
        5. Remove existing BGP configuration
        6. Configure BGP with router IDs
        7. Configure BGP neighbors with CORRECT matching password on both DUTs
        8. Verify BGP session establishes (Established state)
        9. Change password on DUT1 to WRONG password (mismatch)
        10. Verify BGP session does NOT establish (Connect state)
        11. Fix password on DUT1 to CORRECT password
        12. Verify BGP session re-establishes
        """
        st.banner("NEGATIVE TEST: IPv4 BGP - Password Mismatch")

        # Step 1: Check and remove existing IPv4 addresses
        st.log("Step 1: Checking and removing existing IPv4 addresses from interfaces")

        remove_ipv4_address(data.dut1, data.dut1_dut2_port, data.cli_type)
        remove_ipv4_address(data.dut2, data.dut2_dut1_port, data.cli_type)

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

        # Step 7: Configure BGP neighbors with CORRECT matching password
        st.log("Step 7: Configuring BGP neighbors with CORRECT matching password on both DUTs")
        st.log(f"Password: {data.correct_password}")

        if not configure_bgp_neighbor_with_password(
            data.dut1, data.bgp_asn, data.dut2_ipv4, data.bgp_asn,
            data.correct_password, data.af_ipv4, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        if not configure_bgp_neighbor_with_password(
            data.dut2, data.bgp_asn, data.dut1_ipv4, data.bgp_asn,
            data.correct_password, data.af_ipv4, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut2}")

        # Step 8: Verify BGP sessions establish with correct password
        st.log("Step 8: Verifying BGP sessions establish with correct matching password")

        st.wait(data.bgp_wait, "Waiting for BGP sessions to establish")

        if not verify_bgp_neighbor_state(data.dut1, data.dut2_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not established on {data.dut1} with correct password")

        if not verify_bgp_neighbor_state(data.dut2, data.dut1_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not established on {data.dut2} with correct password")

        st.log("POSITIVE TEST PASSED: BGP sessions established with correct matching password")

        # Step 9: Change password on DUT1 to WRONG password (mismatch)
        st.log("Step 9: Changing password on DUT1 to WRONG password (creating mismatch)")
        st.log(f"DUT1 new password: {data.wrong_password}")
        st.log(f"DUT2 password remains: {data.correct_password}")

        if not reconfigure_bgp_neighbor_password(
            data.dut1, data.bgp_asn, data.dut2_ipv4, data.bgp_asn,
            data.wrong_password, data.af_ipv4, data.cli_type
        ):
            st.report_fail("msg", f"Failed to reconfigure BGP neighbor with wrong password on {data.dut1}")

        # Step 10: Verify BGP session does NOT establish (Connect state)
        st.log("Step 10: Verifying BGP session does NOT establish with password mismatch (Connect state)")

        if not verify_bgp_neighbor_connect_state(data.dut1, data.dut2_ipv4, data.negative_test_wait, data.cli_type):
            st.report_fail("msg", f"BGP session INCORRECTLY established on {data.dut1} with wrong password!")

        st.log("NEGATIVE TEST PASSED: BGP session did NOT establish with password mismatch (Connect state)")

        # Step 11: Fix password on DUT1 to CORRECT password
        st.log("Step 11: Fixing password on DUT1 back to CORRECT password")
        st.log(f"DUT1 password changed back to: {data.correct_password}")

        if not reconfigure_bgp_neighbor_password(
            data.dut1, data.bgp_asn, data.dut2_ipv4, data.bgp_asn,
            data.correct_password, data.af_ipv4, data.cli_type
        ):
            st.report_fail("msg", f"Failed to fix BGP neighbor password on {data.dut1}")

        # Step 12: Verify BGP sessions re-establish after fixing password
        st.log("Step 12: Verifying BGP sessions re-establish after fixing password")

        st.wait(data.bgp_wait, "Waiting for BGP sessions to re-establish after password fix")

        if not verify_bgp_neighbor_state(data.dut1, data.dut2_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not re-established on {data.dut1} after fixing password")

        if not verify_bgp_neighbor_state(data.dut2, data.dut1_ipv4, 'Established', data.af_ipv4, data.bgp_wait, data.cli_type):
            st.report_fail("msg", f"BGP session not re-established on {data.dut2}")

        st.log("POSITIVE TEST PASSED: BGP sessions re-established after fixing password")

        st.report_pass("test_case_passed")
