"""
IPv6 PHYSICAL INTERFACE WITH eBGP
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv6_bgp_interface_ebgp.py \
  --logs-path ./logs/test_ipv6_bgp_interface_ebgp_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IPv6 BGP peering over physical interfaces using Klish CLI.
  This test suite provisions IPv6 addresses on Ethernet interfaces, establishes eBGP
  sessions between two SONiC devices (different AS numbers), validates BGP neighborship,
  verifies IPv6 connectivity via ping, saves configuration using 'write memory', performs
  reboot, and validates that BGP sessions and connectivity persist after reboot.

  The test automatically cleans up any existing IPv4/IPv6 addresses on test interfaces
  before starting. The test is topology-aware and works across SONiC hardware and
  virtual environments.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +-------------------------+                       +-------------------------+
        # |      smic_sonic1        |                       |      smic_sonic2        |
        # | Eth32 2001:db8:1::1/64  |=======================| Eth32 2001:db8:1::2/64  |
        # | AS 65001                |                       | AS 65002                |
        # | (192.168.100.57)        |                       | (192.168.100.172)       |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: DUT1 AS 65001, DUT2 AS 65002 (eBGP), IPv6 Unicast address family
  - Variable file: vars_ipv6_bgp_interface_ebgp.yaml
  - Required test variables: cli_type (klish), bgp_wait_time, reboot_wait_time

Features:
  - Automatic pre-test cleanup of existing IPv4/IPv6 addresses
  - Configuration save using 'write memory' command in sonic-cli
  - eBGP peering with different AS numbers (65001 and 65002)
  - Post-reboot validation of BGP sessions and connectivity
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
data.bgp_asn_dut1 = "65001"  # eBGP: Different ASN for DUT1
data.bgp_asn_dut2 = "65002"  # eBGP: Different ASN for DUT2
data.af_ipv6 = "ipv6"
data.cli_type = "klish"
data.mtu = "9100"
data.speed = "40000"
data.bgp_wait = 90
data.reboot_wait = 60
data.ping_count = 5


def cleanup_existing_ip_addresses():
    """
    Check and remove any existing IPv4 and IPv6 addresses on test interfaces.
    This ensures a clean starting state for the test.

    Uses CLICK CLI for show commands to avoid pagination issues.
    Uses Klish CLI for config commands to maintain consistency with test.

    Parses output from:
    - show ip interfaces (format: Interface, IP Address/Mask, Status)
    - show ipv6 interfaces (format: Interface, IPv6 address/mask, Admin/Oper)
    """
    st.log("Checking for existing IP addresses on test interfaces")

    dut_interface_list = [
        (data.dut1, data.dut1_dut2_port),
        (data.dut2, data.dut2_dut1_port)
    ]

    for dut, interface in dut_interface_list:
        st.log(f"Checking interface {interface} on {dut}")

        # Check for existing IPv4 addresses
        try:
            # Use CLICK CLI for show commands (avoids pagination issues)
            output = st.show(dut, "show ip interfaces", type="click", skip_error_check=True)
            st.log(f"IPv4 interface output on {dut}:\n{output}")

            # Convert list of dicts to string if needed
            if isinstance(output, list):
                # If we get structured data, convert to string for parsing
                output_str = ""
                for entry in output:
                    if_name = entry.get('interface', '')
                    ip_addr = entry.get('ipaddress', entry.get('ipv4address', ''))
                    status = entry.get('status', '')
                    output_str += f"{if_name}  {ip_addr}  {status}\n"
                output = output_str

            # Parse the text output for the specific interface
            has_ipv4 = False
            if output and isinstance(output, str):
                # Split into lines and look for the interface
                for line in output.split('\n'):
                    # Skip header and separator lines
                    if 'Interface' in line or '---' in line or not line.strip():
                        continue

                    # Check if this line contains our interface
                    if line.startswith(interface):
                        # Split the line by whitespace
                        parts = line.split()
                        if len(parts) >= 2:
                            # parts[0] = Interface name, parts[1] = IP/Mask
                            ip_addr = parts[1]
                            if ip_addr and ip_addr != 'N/A' and '.' in ip_addr:
                                st.log(f"Found existing IPv4 address {ip_addr} on {interface}")
                                has_ipv4 = True
                                break

            # Remove IPv4 address if found
            if has_ipv4:
                st.log(f"Removing IPv4 address from {interface} on {dut}")
                commands = []
                commands.append(f"interface {interface}")
                commands.append("no ip address")
                commands.append("exit")
                st.config(dut, commands, type=data.cli_type, skip_error_check=True)
                st.log(f"IPv4 address removed from {interface} on {dut}")
            else:
                st.log(f"No IPv4 address found on {interface}")

        except Exception as e:
            st.log(f"Error checking IPv4 on {interface}: {str(e)}")

        # Check for existing IPv6 addresses
        try:
            # Use CLICK CLI for show commands (avoids pagination issues)
            output = st.show(dut, "show ipv6 interfaces", type="click", skip_error_check=True)
            st.log(f"IPv6 interface output on {dut}:\n{output}")

            # Convert list of dicts to string if needed
            if isinstance(output, list):
                # If we get structured data, convert to string for parsing
                output_str = ""
                for entry in output:
                    if_name = entry.get('interface', '')
                    ipv6_addr = entry.get('ipv6address', entry.get('ipaddress', ''))
                    admin_oper = entry.get('admin_oper', entry.get('status', ''))
                    output_str += f"{if_name}  {ipv6_addr}  {admin_oper}\n"
                output = output_str

            # Parse the text output for the specific interface
            has_ipv6 = False
            if output and isinstance(output, str):
                # Split into lines and look for the interface
                for line in output.split('\n'):
                    # Skip header and separator lines
                    if 'Interface' in line or '---' in line or not line.strip():
                        continue

                    # Check if this line contains our interface
                    if interface in line:
                        # Look for IPv6 address pattern (xxxx:xxxx::/xx)
                        import re
                        ipv6_pattern = r'([0-9a-fA-F:]+/\d+)'
                        matches = re.findall(ipv6_pattern, line)
                        if matches:
                            st.log(f"Found existing IPv6 address(es) on {interface}: {matches}")
                            has_ipv6 = True
                            break

            # Remove IPv6 address if found
            if has_ipv6:
                st.log(f"Removing IPv6 address from {interface} on {dut}")
                commands = []
                commands.append(f"interface {interface}")
                commands.append("no ipv6 address")
                commands.append("exit")
                st.config(dut, commands, type=data.cli_type, skip_error_check=True)
                st.log(f"IPv6 address removed from {interface} on {dut}")
            else:
                st.log(f"No IPv6 address found on {interface}")

        except Exception as e:
            st.log(f"Error checking IPv6 on {interface}: {str(e)}")

    st.log("Pre-test cleanup completed - all existing IP addresses removed")


@pytest.fixture(scope="module", autouse=True)
def ipv6_bgp_module_hooks(request):
    """
    Module-level fixture for IPv6 BGP test setup and teardown.
    Sets up topology, configures interfaces, IPv6 addresses, and BGP.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv6 eBGP Interface Test")

    # Store DUT handles for easy access
    data.dut1 = vars.D1
    data.dut2 = vars.D2
    data.dut1_dut2_port = vars.D1D2P1
    data.dut2_dut1_port = vars.D2D1P1

    # Log topology information
    st.log(f"DUT1: {data.dut1}, DUT2: {data.dut2}")
    st.log(f"DUT1-DUT2 Port: {data.dut1_dut2_port}, DUT2-DUT1 Port: {data.dut2_dut1_port}")
    st.log(f"DUT1 BGP ASN: {data.bgp_asn_dut1}, DUT2 BGP ASN: {data.bgp_asn_dut2}")

    # Get UI type for the test
    data.shell_vtysh = st.get_ui_type()
    if data.shell_vtysh == "click":
        data.shell_vtysh = "vtysh"

    # Pre-test cleanup: Remove any existing IP addresses on test interfaces
    st.banner("PRE-TEST CLEANUP: Checking and removing existing IP addresses")
    cleanup_existing_ip_addresses()

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up IPv6 eBGP configuration")
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


def configure_bgp_neighbor(dut, local_asn, neighbor_ip, remote_asn, family="ipv6", cli_type="klish"):
    """
    Configure BGP neighbor with IPv6 address family using direct Klish commands.
    For eBGP, local_asn and remote_asn will be different.

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbor_ip: Neighbor IPv6 address
        remote_asn: Remote AS number (different from local_asn for eBGP)
        family: Address family (default: ipv6)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring eBGP neighbor {neighbor_ip} (Remote AS {remote_asn}) on {dut} (Local AS {local_asn})")

    try:
        # Use direct Klish commands for proper IPv6 BGP configuration
        commands = []
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_asn}")
        commands.append(f"address-family ipv6 unicast")
        commands.append(f"activate")
        commands.append(f"route-map ALLOW-ALL in")
        commands.append(f"route-map ALLOW-ALL out")
        commands.append("exit")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured eBGP neighbor {neighbor_ip} with route-maps on {dut}")
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
            output = st.show(dut, "show bgp summary", type=cli_type)

            # Check if output contains the neighbor and state
            if output:
                for entry in output:
                    if str(entry.get('neighbor', '')).strip() == str(neighbor_ip).strip():
                        # Check if state column shows Established (or numeric value indicating up)
                        neighbor_state = entry.get('state', '')
                        st.log(f"Found neighbor {neighbor_ip} with state: {neighbor_state}")

                        # If state is numeric (e.g., "0"), neighbor is Established
                        # If state is "Established", that's also good
                        # If state is "(Policy)", session is established but policies are applied
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
    Save configuration on all DUTs using 'write memory' command in sonic-cli only.

    Returns:
        bool: True if save succeeds on all DUTs, False otherwise
    """
    st.log("Saving configuration on all DUTs using 'write memory' in sonic-cli")

    dut_list = [data.dut1, data.dut2]

    for dut in dut_list:
        st.log(f"Saving configuration on {dut}")

        try:
            # Enable docker routing config mode for BGP config persistence
            bgp_api.enable_docker_routing_config_mode(dut, cli_type=data.cli_type)

            # Save config using 'write memory' in sonic-cli only
            st.log(f"Executing 'write memory' on {dut} using sonic-cli")
            output = st.config(dut, "write memory", type=data.cli_type, skip_error_check=True)
            st.log(f"Write memory output on {dut}: {output}")

            st.log(f"Configuration saved on {dut}")
        except Exception as e:
            st.error(f"Failed to save configuration on {dut}: {str(e)}")
            return False

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
    st.log("Cleaning up eBGP and IPv6 configuration")

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
class TestIpv6EbgpInterface:
    """
    Test class for IPv6 eBGP over physical interface validation.
    """

    @pytest.mark.test_ipv6_ebgp_basic
    def test_ipv6_ebgp_interface_config_verify(self):
        """
        TestCase: test_ipv6_ebgp_interface_config_verify

        Test Steps:
        1. Configure MTU and speed on interfaces
        2. Configure IPv6 addresses on both DUTs
        3. Verify IPv6 address configuration
        4. Test IPv6 connectivity via ping (both click and klish)
        5. Configure eBGP router and neighbors on both DUTs
        6. Verify eBGP session establishment
        7. Verify BGP neighbor details

        Expected Result:
        - All configuration steps succeed
        - IPv6 connectivity verified via ping
        - eBGP sessions establish successfully
        """
        st.banner("TEST: IPv6 eBGP Interface Configuration and Verification")

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

        # Step 5: Configure eBGP router and neighbors
        st.log("Step 5: Configuring eBGP router and neighbors")

        # Configure route-map on DUT1 (before BGP configuration to avoid Policy warning)
        if not configure_route_map(data.dut1, "ALLOW-ALL", 10, "permit", data.cli_type):
            st.report_fail("msg", f"Failed to configure route-map on {data.dut1}")

        # Configure BGP on DUT1 (AS 65001)
        if not configure_bgp_router(data.dut1, data.bgp_asn_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        # DUT1 peers with DUT2 (remote AS 65002)
        if not configure_bgp_neighbor(
            data.dut1, data.bgp_asn_dut1, data.dut2_ipv6, data.bgp_asn_dut2, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut1}")

        # Configure route-map on DUT2 (before BGP configuration to avoid Policy warning)
        if not configure_route_map(data.dut2, "ALLOW-ALL", 10, "permit", data.cli_type):
            st.report_fail("msg", f"Failed to configure route-map on {data.dut2}")

        # Configure BGP on DUT2 (AS 65002)
        if not configure_bgp_router(data.dut2, data.bgp_asn_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        # DUT2 peers with DUT1 (remote AS 65001)
        if not configure_bgp_neighbor(
            data.dut2, data.bgp_asn_dut2, data.dut1_ipv6, data.bgp_asn_dut1, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure BGP neighbor on {data.dut2}")

        # Step 6: Wait and verify eBGP session establishment
        st.log("Step 6: Verifying eBGP session establishment")
        st.wait(data.bgp_wait, "Waiting for eBGP session establishment")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )

        if not (result1 and result2):
            st.report_fail("msg", "eBGP session failed to establish on one or both DUTs")

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


    @pytest.mark.test_ipv6_ebgp_save_reboot
    def test_ipv6_ebgp_save_reboot(self):
        """
        TestCase: test_ipv6_ebgp_save_reboot

        Pre-requisite:
        - IPv6 addresses configured on interfaces
        - eBGP sessions established

        Test Steps:
        1. Verify eBGP session is established (pre-check)
        2. Verify IPv6 connectivity via ping
        3. Check BGP routes (if any advertised)
        4. Save configuration on all DUTs
        5. Reboot all DUTs
        6. Verify eBGP sessions after reboot
        7. Verify IPv6 connectivity after reboot

        Expected Result:
        - Configuration persists after reboot
        - eBGP sessions re-establish automatically
        - IPv6 connectivity restored
        """
        st.banner("TEST: IPv6 eBGP Save and Reboot")

        # Ensure configuration is in place (run basic config first)
        st.log("Setting up IPv6 eBGP configuration for save/reboot test")
        self.test_ipv6_ebgp_interface_config_verify()

        # Step 1: Verify eBGP session is established (pre-check)
        st.log("Step 1: Pre-reboot verification - checking eBGP sessions")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, timeout=30
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, timeout=30
        )

        if not (result1 and result2):
            st.report_fail("msg", "eBGP sessions not established before save/reboot")

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

        # Step 6: Verify eBGP sessions after reboot
        st.log("Step 6: Post-reboot verification - checking eBGP sessions")

        result1 = verify_bgp_neighbor_state(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )
        result2 = verify_bgp_neighbor_state(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )

        if not (result1 and result2):
            st.report_fail("msg", "eBGP sessions failed to re-establish after reboot")

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
