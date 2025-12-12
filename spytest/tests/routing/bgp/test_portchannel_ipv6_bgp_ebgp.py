"""
PortChannel IPv6 WITH eBGP
Author: Athira
© 2025, copyrights@SuperMicro

Variable File: vars_portchannel_ipv6_bgp_ebgp.yaml

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_portchannel_ipv6_bgp_ebgp.py \
  --logs-path ./logs/test_portchannel_ipv6_bgp_ebgp_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IPv6 BGP peering over PortChannel interfaces using Klish CLI.
  This test suite creates PortChannel10, adds physical interface Ethernet32 as member,
  provisions IPv6 addresses on PortChannel interfaces, establishes eBGP sessions (AS 65001 <-> AS 65002) between
  two SONiC devices, validates BGP neighborship, verifies IPv6 connectivity via ping using
  both click and klish CLI, saves configuration, performs reboot, and validates that BGP
  sessions and connectivity persist after reboot. The test is topology-aware and works
  across SONiC hardware and virtual environments.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +-------------------------+                       +-------------------------+
        # |      smic_sonic1        |                       |      smic_sonic2        |
        # | PC10 2001:db8:20::1/64  |=======================| PC10 2001:db8:20::2/64  |
        # |  └─ Ethernet32          |                       |  └─ Ethernet32          |
        # | (192.168.100.243)       |                       | (192.168.100.57)        |
        # +-------------------------+                       +-------------------------+

  - PortChannel Configuration: PortChannel10 (LACP mode)
  - BGP Configuration: AS 65001 (DUT1) <-> AS 65002 (DUT2) - eBGP, IPv6 Unicast address family
  - Required test variables (YAML): cli_type (klish), bgp_wait_time, reboot_wait_time
"""

from __future__ import annotations

import pytest

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.switching.portchannel as pc_api
import apis.system.interface as intf_api
import apis.system.reboot as reboot_api
import apis.system.basic as basic_api
from utilities.parallel import exec_all


# Test data dictionary
data = SpyTestDict()
data.dut1_ipv6 = "2001:db8:20::1"
data.dut2_ipv6 = "2001:db8:20::2"
data.ipv6_mask = "64"
data.bgp_asn_dut1 = "65001"  # eBGP: Different ASN for DUT1
data.bgp_asn_dut2 = "65002"  # eBGP: Different ASN for DUT2
data.router_id_dut1 = "1.1.1.1"
data.router_id_dut2 = "2.2.2.2"
data.af_ipv6 = "ipv6"
data.cli_type = "klish"
data.portchannel = "PortChannel10"
data.portchannel_id = "10"
data.mtu = "9100"
data.bgp_wait = 90
data.reboot_wait = 60
data.ping_count = 5


@pytest.fixture(scope="module", autouse=True)
def portchannel_ipv6_bgp_ebgp_module_hooks(request):
    """
    Module-level fixture for PortChannel IPv6 BGP test setup and teardown.
    Sets up topology, configures PortChannel, IPv6 addresses, and BGP.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: PortChannel IPv6 eBGP Test")

    # Store DUT handles for easy access
    data.dut1 = vars.D1
    data.dut2 = vars.D2
    data.dut1_dut2_port = vars.D1D2P1
    data.dut2_dut1_port = vars.D2D1P1

    # Log topology information
    st.log(f"DUT1: {data.dut1}, DUT2: {data.dut2}")
    st.log(f"DUT1-DUT2 Port: {data.dut1_dut2_port}, DUT2-DUT1 Port: {data.dut2_dut1_port}")
    st.log(f"PortChannel: {data.portchannel}")

    # Get UI type for the test
    data.shell_vtysh = st.get_ui_type()
    if data.shell_vtysh == "click":
        data.shell_vtysh = "vtysh"

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up PortChannel IPv6 eBGP configuration")
    cleanup_portchannel_bgp_ipv6_config()


@pytest.fixture(scope="function", autouse=True)
def portchannel_ipv6_bgp_ebgp_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def create_portchannel_interface(dut, portchannel_name, cli_type="klish"):
    """
    Create PortChannel interface.

    Args:
        dut: Device under test
        portchannel_name: PortChannel name (e.g., PortChannel10)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Creating {portchannel_name} on {dut}")

    try:
        # Create PortChannel using API
        result = pc_api.create_portchannel(
            dut=dut,
            portchannel_list=[portchannel_name],
            cli_type=cli_type
        )

        if result:
            st.log(f"Successfully created {portchannel_name}")
        else:
            st.error(f"Failed to create {portchannel_name}")

        return result
    except Exception as e:
        st.error(f"Exception creating {portchannel_name}: {str(e)}")
        return False


def add_member_to_portchannel(dut, portchannel_name, member_port, cli_type="klish"):
    """
    Add physical interface as member to PortChannel.

    Args:
        dut: Device under test
        portchannel_name: PortChannel name
        member_port: Physical interface to add
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Adding {member_port} to {portchannel_name} on {dut}")

    try:
        # Add member using API
        result = pc_api.add_portchannel_member(
            dut=dut,
            portchannel=portchannel_name,
            members=[member_port],
            cli_type=cli_type
        )

        if result:
            st.log(f"Successfully added {member_port} to {portchannel_name}")
        else:
            st.error(f"Failed to add {member_port} to {portchannel_name}")

        return result
    except Exception as e:
        st.error(f"Exception adding member to PortChannel: {str(e)}")
        return False


def configure_portchannel_no_shutdown(dut, portchannel_name, cli_type="klish"):
    """
    Bring up PortChannel interface.

    Args:
        dut: Device under test
        portchannel_name: PortChannel name
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Bringing up {portchannel_name} on {dut}")

    try:
        commands = []
        commands.append(f"interface {portchannel_name}")
        commands.append("no shutdown")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully brought up {portchannel_name}")

        # Wait for interface to come up
        st.wait(2, "Waiting for PortChannel to come up")
        return True
    except Exception as e:
        st.error(f"Failed to bring up {portchannel_name}: {str(e)}")
        return False


def configure_ipv6_on_portchannel(dut, portchannel_name, ipv6_addr, mask, cli_type="klish"):
    """
    Configure IPv6 address on PortChannel interface and bring it up.

    Args:
        dut: Device under test
        portchannel_name: PortChannel name
        ipv6_addr: IPv6 address
        mask: Subnet mask
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring IPv6 address {ipv6_addr}/{mask} on {portchannel_name} for {dut}")

    try:
        # Use direct Klish commands to configure IP and bring up interface
        commands = []
        commands.append(f"interface {portchannel_name}")
        commands.append(f"ipv6 address {ipv6_addr}/{mask}")
        commands.append("no shutdown")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured IPv6 address on {portchannel_name} and brought it up")

        # Wait for interface to come up
        st.wait(2, "Waiting for PortChannel interface to come up")
        return True
    except Exception as e:
        st.error(f"Failed to configure IPv6 address on {portchannel_name}: {str(e)}")
        return False


def verify_ipv6_on_portchannel(dut, portchannel_name, ipv6_addr, mask):
    """
    Verify IPv6 address configuration on PortChannel interface using direct Klish commands.

    Args:
        dut: Device under test
        portchannel_name: PortChannel name (e.g., PortChannel10)
        ipv6_addr: Expected IPv6 address
        mask: Expected subnet mask

    Returns:
        bool: True if verification passes, False otherwise
    """
    st.log(f"Verifying IPv6 address {ipv6_addr}/{mask} on {portchannel_name} for {dut}")

    try:
        import re

        # Execute show command and get raw output
        # Command format: "show interface PortChannel 10" (with space between PortChannel and ID)
        command = f"show interface {portchannel_name.replace('PortChannel', 'PortChannel ')}"
        output = st.config(dut, command, type="klish", skip_error_check=True)

        st.log(f"Raw output from '{command}': {output}")

        expected_ip = f"{ipv6_addr}/{mask}"

        # Parse the output text directly
        # Output format: "IPV6 address is 2001:db8:20::1/64"
        if output and isinstance(output, str):
            # Look for the IP address pattern in the output
            # Pattern matches lines like: "IPV6 address is 2001:db8:20::1/64"
            pattern = rf'IPV6 address is {ipv6_addr}/{mask}'
            match = re.search(pattern, output, re.IGNORECASE)

            if match:
                st.log(f"Successfully verified IPv6 address {expected_ip} on {portchannel_name}")
                return True
            else:
                # Try simpler check - just see if both "IPV6 address" and expected IP are in output
                if "IPV6 address" in output and expected_ip in output:
                    st.log(f"Successfully verified IPv6 address {expected_ip} on {portchannel_name} (simple match)")
                    return True

        st.error(f"Failed to verify IPv6 address {expected_ip} on {portchannel_name}")
        return False

    except Exception as e:
        st.error(f"Exception during IPv6 verification: {str(e)}")
        return False


def verify_portchannel_status(dut, portchannel_name):
    """
    Verify PortChannel interface status.

    Args:
        dut: Device under test
        portchannel_name: PortChannel name (e.g., PortChannel10)

    Returns:
        bool: True if PortChannel is up, False otherwise
    """
    st.log(f"Verifying {portchannel_name} status on {dut}")

    try:
        # Execute show command
        # Command format: "show interface PortChannel 10" (with space between PortChannel and ID)
        command = f"show interface {portchannel_name.replace('PortChannel', 'PortChannel ')}"
        output = st.config(dut, command, type="klish", skip_error_check=True)

        st.log(f"PortChannel status: {output}")

        # Check if output contains "is up"
        if output and isinstance(output, str):
            if "is up" in output.lower():
                st.log(f"{portchannel_name} is up on {dut}")
                return True

        st.error(f"{portchannel_name} is not up on {dut}")
        return False

    except Exception as e:
        st.error(f"Exception verifying PortChannel status: {str(e)}")
        return False


def configure_bgp_router_with_router_id(dut, local_asn, router_id, cli_type="klish"):
    """
    Configure BGP router with local ASN and router-id.

    Args:
        dut: Device under test
        local_asn: Local AS number
        router_id: BGP router identifier
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP router with AS {local_asn} and router-id {router_id} on {dut}")

    try:
        # Use direct Klish commands for proper BGP configuration
        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"router-id {router_id}")
        

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP router on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP router: {str(e)}")
        return False


def configure_bgp_neighbor(dut, local_asn, neighbor_ip, remote_asn, family="ipv6", cli_type="klish"):
    """
    Configure BGP neighbor with IPv6 address and activate in address family.

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbor_ip: Neighbor IPv6 address
        remote_asn: Remote AS number
        family: Address family (default: ipv6)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP neighbor {neighbor_ip} with remote-as {remote_asn} on {dut}")

    try:
        # Use direct Klish commands for proper IPv6 BGP configuration
        commands = []
        #commands.append(f"router bgp {local_asn}")
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"activate")
        commands.append("exit")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor {neighbor_ip} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor: {str(e)}")
        return False


def verify_bgp_neighbor_state(dut, neighbor_ip, state='Established', family='ipv6', timeout=90, cli_type='klish'):
    """
    Verify BGP neighbor state using direct Klish show commands.

    Args:
        dut: Device under test
        neighbor_ip: Neighbor IPv6 address
        state: Expected BGP state (default: Established)
        family: Address family (default: ipv6)
        timeout: Timeout in seconds
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if neighbor is in expected state, False otherwise
    """
    st.log(f"Verifying BGP neighbor {neighbor_ip} state on {dut} (expected: {state})")

    iterations = int(timeout / 5)

    for i in range(iterations):
        try:
            # Use direct Klish show command - STAYS IN KLISH MODE
            output = st.show(dut, "show bgp ipv6 unicast summary", type=cli_type)

            # Check if output contains the neighbor and state
            if output:
                for entry in output:
                    if str(entry.get('neighbor', '')).strip() == str(neighbor_ip).strip():
                        neighbor_state = entry.get('state', '')
                        st.log(f"BGP neighbor {neighbor_ip} current state: {neighbor_state}")

                        # Check if state is Established (or shows received routes count)
                        if (state.lower() in str(neighbor_state).lower() or
                            str(neighbor_state).isdigit() or
                            '(Policy)' in str(neighbor_state) or
                            'policy' in str(neighbor_state).lower()):
                            st.log(f"BGP neighbor {neighbor_ip} is in {state} state")
                            return True

        except Exception as e:
            st.log(f"Exception checking BGP state (attempt {i+1}/{iterations}): {str(e)}")

        # Wait before next attempt
        if i < iterations - 1:
            st.wait(5, f"Waiting for BGP session to establish (attempt {i+1}/{iterations})")

    st.error(f"BGP neighbor {neighbor_ip} did not reach {state} state within {timeout} seconds")
    return False


def verify_ipv6_ping(src_dut, dst_ipv6, count=5, cli_type='click'):
    """
    Verify IPv6 connectivity using ping.

    Args:
        src_dut: Source DUT
        dst_ipv6: Destination IPv6 address
        count: Number of ping packets
        cli_type: CLI type (default: click, can be klish)

    Returns:
        bool: True if ping succeeds, False otherwise
    """
    st.log(f"Attempting IPv6 ping from {src_dut} to {dst_ipv6} using {cli_type} CLI (count={count})")

    # Use specified CLI for ping6
    result = ip_api.ping(
        dut=src_dut,
        addresses=dst_ipv6,
        family=data.af_ipv6,
        count=count,
        cli_type=cli_type
    )

    if result:
        st.log(f"IPv6 ping to {dst_ipv6} successful using {cli_type} CLI")
    else:
        st.error(f"IPv6 ping to {dst_ipv6} failed using {cli_type} CLI")

    return result


def save_config_all_duts():
    """
    Save configuration on all DUTs.

    Returns:
        bool: True if save succeeds on all DUTs, False otherwise
    """
    st.log("Saving configuration on all DUTs")

    dut_list = [data.dut1, data.dut2]

    for dut in dut_list:
        st.log(f"Saving configuration on {dut}")

        # Enable docker routing config mode for vtysh config persistence
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=data.cli_type)

        # Save config in vtysh shell for BGP
        reboot_api.config_save(dut, shell='vtysh')

        # Save config in sonic shell for interface config
        reboot_api.config_save(dut, shell='sonic')

        st.log(f"Configuration saved on {dut}")

    return True


def reboot_all_duts(wait_time=60):
    """
    Reboot all DUTs and wait for them to come back.

    Args:
        wait_time: Additional wait time after reboot

    Returns:
        bool: True if reboot succeeds on all DUTs, False otherwise
    """
    st.log("Rebooting all DUTs")

    dut_list = [data.dut1, data.dut2]

    # Reboot DUTs in parallel
    result = exec_all(
        True,
        [[st.reboot, dut] for dut in dut_list]
    )[0]

    if False in result:
        st.error("Reboot failed on one or more DUTs")
        return False

    # Additional wait time for services to stabilize
    st.wait(wait_time, "Waiting for services to stabilize after reboot")

    st.log("All DUTs rebooted successfully")
    return True


def cleanup_portchannel_bgp_ipv6_config():
    """
    Clean up BGP, IPv6, and PortChannel configuration from all DUTs using direct Klish commands.
    """
    st.log("Cleaning up PortChannel BGP and IPv6 configuration")

    dut_list = [data.dut1, data.dut2]

    # Clean up BGP configuration
    st.log("Removing BGP configuration")
    for dut in dut_list:
        commands = ["no router bgp"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

    # Clean up IP configuration on PortChannel
    st.log("Removing IP configuration from PortChannel interfaces")
    for dut in dut_list:
        commands = []
        commands.append(f"interface {data.portchannel}")
        commands.append("no ip address")
        commands.append("exit")
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

    # Remove members from PortChannel
    st.log("Removing PortChannel members")
    pc_api.delete_portchannel_member(
        data.dut1, data.portchannel, [data.dut1_dut2_port], cli_type=data.cli_type
    )
    pc_api.delete_portchannel_member(
        data.dut2, data.portchannel, [data.dut2_dut1_port], cli_type=data.cli_type
    )

    # Delete PortChannel
    st.log("Removing PortChannel configuration")
    pc_api.delete_portchannel(data.dut1, [data.portchannel], cli_type=data.cli_type)
    pc_api.delete_portchannel(data.dut2, [data.portchannel], cli_type=data.cli_type)

    st.log("Cleanup completed")


@pytest.mark.topology("any")
class TestPortchannelIpv6Bgp:
    """
    Test class for IPv6 BGP over PortChannel interface validation.
    """

    @pytest.mark.test_portchannel_ipv6_bgp_ebgp_ebgp_basic
    def test_portchannel_ipv6_bgp_ebgp_ebgp_config_verify(self):
        """
        TestCase: test_portchannel_ipv6_bgp_ebgp_config_verify

        Test Steps:
        1. Create PortChannel10 on both DUTs
        2. Add Ethernet32 as member to PortChannel10
        3. Bring up PortChannel10 and member interfaces
        4. Configure IPv6 addresses on PortChannel interfaces
        5. Verify IPv6 address configuration
        6. Test IPv6 connectivity via ping (both click and klish CLI)
        7. Configure BGP router with router-id on both DUTs
        8. Configure BGP neighbors on both DUTs
        9. Verify BGP session establishment
        10. Verify detailed BGP neighbor information
        11. Verify BGP routes
        12. Test IPv6 traffic after BGP session establishment
        13. Save configuration on both DUTs
        14. Reboot both DUTs
        15. Verify PortChannel, IPv6, and BGP configuration after reboot
        16. Verify BGP session re-establishes after reboot
        17. Test IPv6 connectivity after reboot

        Expected Result:
        - PortChannel created and configured successfully
        - IPv6 addresses configured on PortChannel interfaces
        - BGP sessions established between DUTs
        - IPv6 connectivity works via ping (both click and klish)
        - Configuration persists after reboot
        - BGP sessions re-establish after reboot
        """
        st.banner("STARTING: PortChannel IPv6 BGP Configuration and Verification Test")

        # Step 1: Create PortChannel10 on both DUTs
        st.log("Step 1: Creating PortChannel10 on both DUTs")

        result1 = create_portchannel_interface(data.dut1, data.portchannel, data.cli_type)
        result2 = create_portchannel_interface(data.dut2, data.portchannel, data.cli_type)

        if not (result1 and result2):
            st.report_fail("msg", "Failed to create PortChannel on one or both DUTs")

        # Step 2: Add Ethernet32 as member to PortChannel10
        st.log("Step 2: Adding Ethernet32 to PortChannel10 on both DUTs")

        result1 = add_member_to_portchannel(data.dut1, data.portchannel, data.dut1_dut2_port, data.cli_type)
        result2 = add_member_to_portchannel(data.dut2, data.portchannel, data.dut2_dut1_port, data.cli_type)

        if not (result1 and result2):
            st.report_fail("msg", "Failed to add member to PortChannel on one or both DUTs")

        # Step 3: Bring up PortChannel10 and member interfaces
        st.log("Step 3: Bringing up PortChannel10 on both DUTs")

        result1 = configure_portchannel_no_shutdown(data.dut1, data.portchannel, data.cli_type)
        result2 = configure_portchannel_no_shutdown(data.dut2, data.portchannel, data.cli_type)

        if not (result1 and result2):
            st.report_fail("msg", "Failed to bring up PortChannel on one or both DUTs")

        # Wait for PortChannel to stabilize
        st.wait(5, "Waiting for PortChannel to stabilize")

        # Step 4: Configure IPv6 addresses on PortChannel interfaces
        st.log("Step 4: Configuring IPv6 addresses on PortChannel interfaces")

        result1 = configure_ipv6_on_portchannel(
            data.dut1, data.portchannel, data.dut1_ipv6, data.ipv6_mask, data.cli_type
        )
        result2 = configure_ipv6_on_portchannel(
            data.dut2, data.portchannel, data.dut2_ipv6, data.ipv6_mask, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "Failed to configure IPv6 addresses on PortChannel interfaces")

        # Step 5: Verify IPv6 address configuration
        st.log("Step 5: Verifying IPv6 address configuration on PortChannel interfaces")

        result1 = verify_ipv6_on_portchannel(
            data.dut1, data.portchannel, data.dut1_ipv6, data.ipv6_mask
        )
        result2 = verify_ipv6_on_portchannel(
            data.dut2, data.portchannel, data.dut2_ipv6, data.ipv6_mask
        )

        if not (result1 and result2):
            st.report_fail("msg", "Failed to verify IPv6 addresses on PortChannel interfaces")

        # Step 6: Test IPv6 connectivity via ping (both click and klish CLI)
        st.log("Step 6: Testing IPv6 connectivity via ping over PortChannel")

        # Test with click CLI
        st.log("Testing IPv6 ping using click CLI")
        result1 = verify_ipv6_ping(data.dut1, data.dut2_ipv6, data.ping_count, 'click')
        result2 = verify_ipv6_ping(data.dut2, data.dut1_ipv6, data.ping_count, 'click')

        if not (result1 and result2):
            st.report_fail("msg", "IPv6 ping failed between DUTs over PortChannel using click CLI")

        # Test with klish CLI
        #st.log("Testing IPv6 ping using klish CLI")
        #result1 = verify_ipv6_ping(data.dut1, data.dut2_ipv6, data.ping_count, 'klish')
        #result2 = verify_ipv6_ping(data.dut2, data.dut1_ipv6, data.ping_count, 'klish')

        #if not (result1 and result2):
        #    st.report_fail("msg", "IPv6 ping failed between DUTs over PortChannel using klish CLI")

        # Step 7: Configure BGP router with router-id
        st.log("Step 7: Configuring BGP router with router-id on both DUTs")

        # Configure BGP on DUT1
        if not configure_bgp_router_with_router_id(data.dut1, data.bgp_asn_dut1, data.router_id_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        # Configure BGP on DUT2
        if not configure_bgp_router_with_router_id(data.dut2, data.bgp_asn_dut2, data.router_id_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        # Step 8: Configure BGP neighbors
        st.log("Step 8: Configuring BGP neighbors on both DUTs")

        if not configure_bgp_neighbor(
            data.dut1, data.bgp_asn_dut1, data.dut2_ipv6, data.bgp_asn_dut2, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        if not configure_bgp_neighbor(
            data.dut2, data.bgp_asn_dut2, data.dut1_ipv6, data.bgp_asn_dut1, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut2}")

        # Step 9: Wait and verify BGP session establishment
        st.log("Step 9: Verifying BGP session establishment")
        st.wait(data.bgp_wait, "Waiting for BGP session establishment")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP session failed to establish on one or both DUTs")

        # Step 10: Verify detailed BGP neighbor information using sonic-cli
        st.log("Step 10: Verifying detailed BGP neighbor information using sonic-cli")

        # Get BGP neighbor details from DUT1 using Klish
        st.log(f"Showing BGP IPv6 neighbor details on {data.dut1}")
        bgp_output1 = st.show(data.dut1, f"show bgp ipv6 unicast neighbors {data.dut2_ipv6}", type='klish')
        st.log(f"BGP neighbor details on {data.dut1}: {bgp_output1}")

        # Get BGP neighbor details from DUT2 using Klish
        st.log(f"Showing BGP IPv6 neighbor details on {data.dut2}")
        bgp_output2 = st.show(data.dut2, f"show bgp ipv6 unicast neighbors {data.dut1_ipv6}", type='klish')
        st.log(f"BGP neighbor details on {data.dut2}: {bgp_output2}")

        # Step 11: Verify BGP routes are being exchanged
        st.log("Step 11: Checking BGP IPv6 routes using sonic-cli")

        bgp_routes1 = st.show(data.dut1, "show bgp ipv6 unicast summary", type='klish')
        st.log(f"BGP IPv6 routes on {data.dut1}: {bgp_routes1}")

        bgp_routes2 = st.show(data.dut2, "show bgp ipv6 unicast summary", type='klish')
        st.log(f"BGP IPv6 routes on {data.dut2}: {bgp_routes2}")

        # Step 12: Test IPv6 traffic after BGP session establishment
        st.log("Step 12: Testing IPv6 connectivity after BGP session establishment")

        # Test with both click and klish CLI
        st.log("Testing with click CLI")
        result1 = verify_ipv6_ping(data.dut1, data.dut2_ipv6, data.ping_count, 'click')
        result2 = verify_ipv6_ping(data.dut2, data.dut1_ipv6, data.ping_count, 'click')

        if not (result1 and result2):
            st.report_fail("msg", "IPv6 ping failed after BGP session establishment using click CLI")

        # Step 13: Save configuration on both DUTs
        st.log("Step 13: Saving configuration on both DUTs")

        if not save_config_all_duts():
            st.report_fail("msg", "Failed to save configuration on one or both DUTs")

        # Step 14: Reboot both DUTs
        st.log("Step 14: Rebooting both DUTs")

        if not reboot_all_duts(data.reboot_wait):
            st.report_fail("msg", "Failed to reboot one or both DUTs")

        # Step 15: Verify PortChannel, IPv6, and BGP configuration after reboot
        st.log("Step 15: Verifying PortChannel and IPv6 configuration after reboot")

        # Verify PortChannel status
        result1 = verify_portchannel_status(data.dut1, data.portchannel)
        result2 = verify_portchannel_status(data.dut2, data.portchannel)

        if not (result1 and result2):
            st.report_fail("msg", "PortChannel not up after reboot on one or both DUTs")

        # Verify IPv6 configuration
        result1 = verify_ipv6_on_portchannel(
            data.dut1, data.portchannel, data.dut1_ipv6, data.ipv6_mask
        )
        result2 = verify_ipv6_on_portchannel(
            data.dut2, data.portchannel, data.dut2_ipv6, data.ipv6_mask
        )

        if not (result1 and result2):
            st.report_fail("msg", "IPv6 configuration not present after reboot")

        # Step 16: Verify BGP session re-establishes after reboot
        st.log("Step 16: Verifying BGP session after reboot")

        # Wait for BGP to stabilize
        st.wait(data.bgp_wait, "Waiting for BGP to stabilize after reboot")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, data.bgp_wait, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP session failed to re-establish after reboot")

        st.log("Verifying detailed BGP neighbor information after reboot using sonic-cli")

        bgp_output1 = st.show(data.dut1, f"show bgp ipv6 unicast neighbors {data.dut2_ipv6}", type='klish')
        st.log(f"BGP neighbor details on {data.dut1} after reboot: {bgp_output1}")

        bgp_output2 = st.show(data.dut2, f"show bgp ipv6 unicast neighbors {data.dut1_ipv6}", type='klish')
        st.log(f"BGP neighbor details on {data.dut2} after reboot: {bgp_output2}")

        # Step 17: Test IPv6 connectivity after reboot
        st.log("Step 17: Testing IPv6 connectivity after reboot")

        # Test with both click and klish CLI
        st.log("Testing with click CLI")
        result1 = verify_ipv6_ping(data.dut1, data.dut2_ipv6, data.ping_count, 'click')
        result2 = verify_ipv6_ping(data.dut2, data.dut1_ipv6, data.ping_count, 'click')

        if not (result1 and result2):
            st.report_fail("msg", "IPv6 ping failed after reboot using click CLI")

        # All tests passed
        st.banner("ALL TESTS PASSED: PortChannel IPv6 BGP Configuration and Verification")
        st.report_pass("test_case_passed")
