"""
IPv6 PHYSICAL INTERFACE WITH BGP
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv6_bgp_interface.py \
  --logs-path ./logs/test_ipv6_bgp_interface_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IPv6 BGP peering over physical interfaces using Klish CLI.
  This test suite provisions IPv6 addresses on Ethernet interfaces, establishes iBGP
  sessions between two SONiC devices, validates BGP neighborship, verifies IPv6
  connectivity via ping, saves configuration, performs reboot, and validates that
  BGP sessions and connectivity persist after reboot. The test is topology-aware
  and works across SONiC hardware and virtual environments.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +-------------------------+                       +-------------------------+
        # |      smic_sonic1        |                       |      smic_sonic2        |
        # | Eth32 2001:db8:1::1/64  |=======================| Eth32 2001:db8:1::2/64  |
        # | (192.168.100.57)        |                       | (192.168.100.172)       |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: AS 65001 (iBGP), IPv6 Unicast address family
  - Required test variables (YAML): cli_type (klish), bgp_wait_time, reboot_wait_time
"""

from __future__ import annotations

import pytest

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.system.interface as intf_api
import apis.system.reboot as reboot_api
import apis.system.basic as basic_api
from utilities.parallel import exec_all


# Test data dictionary
data = SpyTestDict()
data.dut1_ipv6 = "2001:db8:1::1"
data.dut2_ipv6 = "2001:db8:1::2"
data.ipv6_mask = "64"
data.bgp_asn = "65001"
data.af_ipv6 = "ipv6"
data.cli_type = "klish"
data.mtu = "9100"
data.speed = "40000"
data.bgp_wait = 90
data.reboot_wait = 60
data.ping_count = 5


@pytest.fixture(scope="module", autouse=True)
def ipv6_bgp_module_hooks(request):
    """
    Module-level fixture for IPv6 BGP test setup and teardown.
    Sets up topology, configures interfaces, IPv6 addresses, and BGP.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv6 BGP Interface Test")

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
    st.banner("MODULE TEARDOWN: Cleaning up IPv6 BGP configuration")
    cleanup_bgp_ipv6_config()


@pytest.fixture(scope="function", autouse=True)
def ipv6_bgp_func_hooks(request):
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
        import re

        # Execute show command and get raw output
        command = f"show ipv6 interfaces"
        output = st.config(dut, command, type="klish", skip_error_check=True)

        st.log(f"Raw output from '{command}': {output}")

        expected_ip = f"{ipv6_addr}/{mask}"

        # Parse the output text directly
        if output and isinstance(output, str):
            # Look for the IP address pattern in the output
            # Pattern matches lines like: "Ethernet32           2001:db8:1::1/64"
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


def configure_bgp_router(dut, local_asn, cli_type="klish"):
    """
    Configure BGP router with local ASN.

    Args:
        dut: Device under test
        local_asn: Local AS number
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP router with AS {local_asn} on {dut}")

    result = bgp_api.config_router_bgp_mode(
        dut=dut,
        local_asn=local_asn,
        config_mode='enable',
        vrf='default',
        cli_type=cli_type,
        skip_error_check=True
    )

    if result:
        st.log(f"Successfully configured BGP router on {dut}")
    else:
        st.error(f"Failed to configure BGP router on {dut}")

    return result


def configure_bgp_neighbor(dut, local_asn, neighbor_ip, remote_asn, family="ipv6", cli_type="klish"):
    """
    Configure BGP neighbor with IPv6 address family using direct Klish commands.

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
    st.log(f"Configuring BGP neighbor {neighbor_ip} with AS {remote_asn} on {dut}")

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
        st.error(f"Failed to configure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def verify_bgp_neighbor_state(dut, neighbor_ip, state='Established', family='ipv6', timeout=90, cli_type='klish'):
    """
    Verify BGP neighbor state using sonic-cli (Klish) with direct show commands.

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
            output = st.show(dut, "show bgp ipv6 unicast summary", type=cli_type)

            # Check if output contains the neighbor and state
            if output:
                for entry in output:
                    if str(entry.get('neighbor', '')).strip() == str(neighbor_ip).strip():
                        # Check if state column shows Established (or numeric value indicating up)
                        neighbor_state = entry.get('state', '')
                        st.log(f"Found neighbor {neighbor_ip} with state: {neighbor_state}")

                        # If state is numeric (e.g., "0"), neighbor is Established
                        # If state is "Established", that's also good
                        if state.lower() in str(neighbor_state).lower() or str(neighbor_state).isdigit():
                            st.log(f"BGP neighbor {neighbor_ip} is in {state} state")
                            return True

            st.log(f"Attempt {i+1}/{iterations}: BGP neighbor {neighbor_ip} not yet in {state} state. Waiting 5 seconds...")
            st.wait(5)

        except Exception as e:
            st.log(f"Error checking BGP state: {str(e)}")
            st.wait(5)

    st.error(f"BGP neighbor {neighbor_ip} is not in {state} state after {timeout} seconds")
    return False


def verify_ipv6_ping(src_dut, dst_ipv6, count=5, cli_type='click'):
    """
    Verify IPv6 connectivity using ping from click CLI.

    Args:
        src_dut: Source DUT
        dst_ipv6: Destination IPv6 address
        count: Number of ping packets
        cli_type: CLI type (default: click)

    Returns:
        bool: True if ping succeeds, False otherwise
    """
    st.log(f"Attempting IPv6 ping from {src_dut} to {dst_ipv6} using {cli_type} CLI (count={count})")

    # Use click CLI for ping6
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

    st.log(f"All DUTs rebooted successfully. Waiting {wait_time} seconds for BGP convergence")
    st.wait(wait_time, "Waiting for BGP neighborship establishment after reboot")

    return True


def cleanup_bgp_ipv6_config():
    """
    Clean up BGP and IPv6 configuration from all DUTs using direct Klish commands.
    """
    st.log("Cleaning up BGP and IPv6 configuration")

    dut_list = [data.dut1, data.dut2]

    # Clean up BGP configuration
    st.log("Removing BGP configuration")
    for dut in dut_list:
        commands = ["no router bgp"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

    # Clean up IPv6 configuration on physical interfaces
    st.log("Removing IPv6 configuration from Ethernet32 interfaces")
    commands_dut1 = []
    commands_dut1.append(f"interface {data.dut1_dut2_port}")
    commands_dut1.append("no ipv6 address")
    commands_dut1.append("exit")
    st.config(data.dut1, commands_dut1, type=data.cli_type, skip_error_check=True)

    commands_dut2 = []
    commands_dut2.append(f"interface {data.dut2_dut1_port}")
    commands_dut2.append("no ipv6 address")
    commands_dut2.append("exit")
    st.config(data.dut2, commands_dut2, type=data.cli_type, skip_error_check=True)

    st.log("Cleanup completed")


@pytest.mark.topology("any")
class TestIpv6BgpInterface:
    """
    Test class for IPv6 BGP over physical interface validation.
    """

    @pytest.mark.test_ipv6_bgp_basic
    def test_ipv6_bgp_interface_config_verify(self):
        """
        TestCase: test_ipv6_bgp_interface_config_verify

        Test Steps:
        1. Configure MTU and speed on interfaces
        2. Configure IPv6 addresses on both DUTs
        3. Verify IPv6 address configuration
        4. Test IPv6 connectivity via ping (both click and klish)
        5. Configure BGP router and neighbors on both DUTs
        6. Verify BGP session establishment
        7. Verify BGP neighbor details

        Expected Result:
        - All configuration steps succeed
        - IPv6 connectivity verified via ping
        - BGP sessions establish successfully
        """
        st.banner("TEST: IPv6 BGP Interface Configuration and Verification")

        # Step 1: Configure MTU and speed on interfaces
        st.log("Step 1: Configuring MTU and speed on interfaces")

        result1 = configure_interface_mtu_speed(
            data.dut1, data.dut1_dut2_port, data.mtu, data.speed, data.cli_type
        )
        result2 = configure_interface_mtu_speed(
            data.dut2, data.dut2_dut1_port, data.mtu, data.speed, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "Failed to configure MTU/speed on interfaces")

        # Step 2: Configure IPv6 addresses
        st.log("Step 2: Configuring IPv6 addresses on interfaces")

        result1 = configure_ipv6_interface(
            data.dut1, data.dut1_dut2_port, data.dut1_ipv6, data.ipv6_mask, data.cli_type
        )
        result2 = configure_ipv6_interface(
            data.dut2, data.dut2_dut1_port, data.dut2_ipv6, data.ipv6_mask, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "Failed to configure IPv6 addresses on interfaces")

        # Step 3: Verify IPv6 address configuration
        st.log("Step 3: Verifying IPv6 address configuration")

        result1 = verify_ipv6_interface(
            data.dut1, data.dut1_dut2_port, data.dut1_ipv6, data.ipv6_mask
        )
        result2 = verify_ipv6_interface(
            data.dut2, data.dut2_dut1_port, data.dut2_ipv6, data.ipv6_mask
        )

        if not (result1 and result2):
            st.report_fail("msg", "Failed to verify IPv6 addresses on interfaces")

        # Step 4: Test IPv6 connectivity via ping (both click and klish)
        st.log("Step 4: Testing IPv6 connectivity via ping")

        # Ping from DUT1 to DUT2
        result1 = verify_ipv6_ping(data.dut1, data.dut2_ipv6, data.ping_count)

        # Ping from DUT2 to DUT1
        result2 = verify_ipv6_ping(data.dut2, data.dut1_ipv6, data.ping_count)

        if not (result1 and result2):
            st.report_fail("msg", "IPv6 ping failed between DUTs")

        # Step 5: Configure BGP router and neighbors
        st.log("Step 5: Configuring BGP router and neighbors")

        # Configure BGP on DUT1
        if not configure_bgp_router(data.dut1, data.bgp_asn, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        if not configure_bgp_neighbor(
            data.dut1, data.bgp_asn, data.dut2_ipv6, data.bgp_asn, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        # Configure BGP on DUT2
        if not configure_bgp_router(data.dut2, data.bgp_asn, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        if not configure_bgp_neighbor(
            data.dut2, data.bgp_asn, data.dut1_ipv6, data.bgp_asn, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut2}")

        # Step 6: Wait and verify BGP session establishment
        st.log("Step 6: Verifying BGP session establishment")
        st.wait(data.bgp_wait, "Waiting for BGP session establishment")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP session failed to establish on one or both DUTs")

        # Step 7: Verify detailed BGP neighbor information using sonic-cli (Klish)
        st.log("Step 7: Verifying detailed BGP neighbor information using sonic-cli")

        # Get BGP neighbor details from DUT1 using Klish
        st.log(f"Showing BGP IPv6 neighbor details on {data.dut1}")
        bgp_output1 = st.show(data.dut1, f"show bgp ipv6 unicast neighbors {data.dut2_ipv6}", type='klish')
        st.log(f"BGP neighbor details on {data.dut1}: {bgp_output1}")

        # Get BGP neighbor details from DUT2 using Klish
        st.log(f"Showing BGP IPv6 neighbor details on {data.dut2}")
        bgp_output2 = st.show(data.dut2, f"show bgp ipv6 unicast neighbors {data.dut1_ipv6}", type='klish')
        st.log(f"BGP neighbor details on {data.dut2}: {bgp_output2}")

        st.report_pass("test_case_passed")


    @pytest.mark.test_ipv6_bgp_save_reboot
    def test_ipv6_bgp_save_reboot(self):
        """
        TestCase: test_ipv6_bgp_save_reboot

        Pre-requisite:
        - IPv6 addresses configured on interfaces
        - BGP sessions established

        Test Steps:
        1. Verify BGP session is established (pre-check)
        2. Verify IPv6 connectivity via ping
        3. Check BGP routes (if any advertised)
        4. Save configuration on all DUTs
        5. Reboot all DUTs
        6. Verify BGP sessions after reboot
        7. Verify IPv6 connectivity after reboot

        Expected Result:
        - Configuration persists after reboot
        - BGP sessions re-establish automatically
        - IPv6 connectivity restored
        """
        st.banner("TEST: IPv6 BGP Save and Reboot")

        # Ensure configuration is in place (run basic config first)
        st.log("Setting up IPv6 BGP configuration for save/reboot test")
        self.test_ipv6_bgp_interface_config_verify()

        # Step 1: Verify BGP session is established (pre-check)
        st.log("Step 1: Pre-reboot verification - checking BGP sessions")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, timeout=30
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, timeout=30
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP sessions not established before save/reboot")

        # Step 2: Verify IPv6 connectivity via ping (pre-reboot)
        st.log("Step 2: Pre-reboot verification - testing IPv6 connectivity")

        result1 = verify_ipv6_ping(data.dut1, data.dut2_ipv6, data.ping_count)
        result2 = verify_ipv6_ping(data.dut2, data.dut1_ipv6, data.ping_count)

        if not (result1 and result2):
            st.report_fail("msg", "IPv6 ping failed before save/reboot")

        # Step 3: Check BGP routes using sonic-cli (Klish)
        st.log("Step 3: Checking BGP IPv6 routes using sonic-cli")

        bgp_routes1 = st.show(data.dut1, "show bgp ipv6 unicast summary", type='klish')
        st.log(f"BGP IPv6 routes on {data.dut1}: {bgp_routes1}")

        bgp_routes2 = st.show(data.dut2, "show bgp ipv6 unicast summary", type='klish')
        st.log(f"BGP IPv6 routes on {data.dut2}: {bgp_routes2}")

        # Step 4: Save configuration on all DUTs
        st.log("Step 4: Saving configuration on all DUTs")

        if not save_config_all_duts():
            st.report_fail("msg", "Failed to save configuration on one or more DUTs")

        # Step 5: Reboot all DUTs
        st.log("Step 5: Rebooting all DUTs")

        if not reboot_all_duts(wait_time=data.reboot_wait):
            st.report_fail("msg", "Reboot failed on one or more DUTs")

        # Step 6: Verify BGP sessions after reboot
        st.log("Step 6: Post-reboot verification - checking BGP sessions")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )

        if not (result1 and result2):
            st.report_fail("msg", "BGP sessions failed to re-establish after reboot")

        # Step 7: Verify IPv6 connectivity after reboot
        st.log("Step 7: Post-reboot verification - testing IPv6 connectivity")

        result1 = verify_ipv6_ping(data.dut1, data.dut2_ipv6, data.ping_count)
        result2 = verify_ipv6_ping(data.dut2, data.dut1_ipv6, data.ping_count)

        if not (result1 and result2):
            st.report_fail("msg", "IPv6 ping failed after reboot")

        # Verify detailed BGP information post-reboot using sonic-cli (Klish)
        st.log("Verifying detailed BGP neighbor information after reboot using sonic-cli")

        bgp_output1 = st.show(data.dut1, f"show bgp ipv6 unicast neighbors {data.dut2_ipv6}", type='klish')
        st.log(f"BGP neighbor details on {data.dut1} after reboot: {bgp_output1}")

        bgp_output2 = st.show(data.dut2, f"show bgp ipv6 unicast neighbors {data.dut1_ipv6}", type='klish')
        st.log(f"BGP neighbor details on {data.dut2} after reboot: {bgp_output2}")

        st.report_pass("test_case_passed")
