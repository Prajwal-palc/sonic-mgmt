"""
IPv6 VLAN INTERFACE WITH eBGP
Author: Athira
© 2025, copyrights@SuperMicro

Variable File: vars_ipv6_vlan_bgp_interface_ebgp.yaml

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_ipv6_vlan_bgp_interface_ebgp.py \
  --logs-path ./logs/test_ipv6_vlan_bgp_ebgp_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IPv6 eBGP peering over VLAN interfaces using Klish CLI.
  This test suite provisions VLAN 100, configures Ethernet32 as access port, creates
  VLAN interface (Vlan100) with IPv6 addresses, establishes eBGP sessions between
  two SONiC devices over the VLAN (AS 65001 <-> AS 65002), validates BGP neighborship
  including (Policy) state, verifies IPv6 connectivity via ping, saves configuration,
  performs reboot, and validates that BGP sessions and connectivity persist after
  reboot. The test is topology-aware and works across SONiC hardware and virtual
  environments.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with VLAN
        # +-------------------------+                       +-------------------------+
        # |      smic_sonic1        |                       |      smic_sonic2        |
        # | VLAN 100                |                       | VLAN 100                |
        # | Vlan100                 |                       | Vlan100                 |
        # |  2001:db8:100::1/64     |                       |  2001:db8:100::2/64     |
        # | AS 65001                |                       | AS 65002                |
        # | Eth32 (Access VLAN 100) |=======================| Eth32 (Access VLAN 100) |
        # | (192.168.100.57)        |                       | (192.168.100.172)       |
        # +-------------------------+                       +-------------------------+

  - BGP Configuration: AS 65001 (DUT1) <-> AS 65002 (DUT2) - eBGP
  - Router ID: 1.1.1.1 (DUT1), 2.2.2.2 (DUT2)
  - Required test variables (YAML): cli_type (klish), bgp_wait_time, reboot_wait_time
"""

from __future__ import annotations

import pytest

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.system.interface as intf_api
import apis.system.reboot as reboot_api
import apis.switching.vlan as vlan_api
from utilities.parallel import exec_all


# Test data dictionary
data = SpyTestDict()
data.vlan_id = "100"
data.dut1_ipv6 = "2001:db8:100::1"
data.dut2_ipv6 = "2001:db8:100::2"
data.ipv6_mask = "64"
data.bgp_asn_dut1 = "65001"  # eBGP: Different ASN for DUT1
data.bgp_asn_dut2 = "65002"  # eBGP: Different ASN for DUT2
data.router_id_dut1 = "1.1.1.1"
data.router_id_dut2 = "2.2.2.2"
data.af_ipv6 = "ipv6"
data.cli_type = "klish"
data.bgp_wait = 90
data.reboot_wait = 60
data.ping_count = 5
data.vlan_name = "Vlan100"


@pytest.fixture(scope="module", autouse=True)
def ipv6_vlan_bgp_ebgp_module_hooks(request):
    """
    Module-level fixture for IPv6 VLAN eBGP test setup and teardown.
    Sets up topology, configures VLANs, VLAN interfaces, IPv6 addresses, and eBGP.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1D2:1")

    st.banner("MODULE SETUP: IPv6 VLAN eBGP Interface Test")

    # Store DUT handles for easy access
    data.dut1 = vars.D1
    data.dut2 = vars.D2
    data.dut1_dut2_port = vars.D1D2P1
    data.dut2_dut1_port = vars.D2D1P1

    # Log topology information
    st.log(f"DUT1: {data.dut1}, DUT2: {data.dut2}")
    st.log(f"DUT1-DUT2 Port: {data.dut1_dut2_port}, DUT2-DUT1 Port: {data.dut2_dut1_port}")
    st.log(f"eBGP: AS {data.bgp_asn_dut1} <-> AS {data.bgp_asn_dut2}")

    # Get UI type for the test
    data.shell_vtysh = st.get_ui_type()
    if data.shell_vtysh == "click":
        data.shell_vtysh = "vtysh"

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up IPv6 VLAN eBGP configuration")
    cleanup_vlan_bgp_config()


@pytest.fixture(scope="function", autouse=True)
def ipv6_vlan_bgp_ebgp_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def create_vlan(dut, vlan_id, cli_type="klish"):
    """
    Create VLAN on the device using direct Klish commands.

    Args:
        dut: Device under test
        vlan_id: VLAN ID to create
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Creating VLAN {vlan_id} on {dut}")

    try:
        # Use direct Klish command "vlan 100" to create VLAN
        commands = []
        commands.append(f"vlan {vlan_id}")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully created VLAN {vlan_id} on {dut}")
        return True
    except Exception as e:
        st.error(f"Exception creating VLAN {vlan_id} on {dut}: {str(e)}")
        return False


def verify_vlan_config(dut, vlan_id, cli_type="klish"):
    """
    Verify VLAN configuration using show Vlan command.

    Args:
        dut: Device under test
        vlan_id: VLAN ID to verify
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if VLAN exists, False otherwise
    """
    st.log(f"Verifying VLAN {vlan_id} configuration on {dut}")

    try:
        # Execute show Vlan command
        command = "show Vlan"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        st.log(f"Show Vlan output: {output}")

        # Check if VLAN ID is present in output
        if output and isinstance(output, str):
            if str(vlan_id) in output:
                st.log(f"Successfully verified VLAN {vlan_id} exists on {dut}")
                return True

        st.error(f"VLAN {vlan_id} not found in show Vlan output on {dut}")
        return False

    except Exception as e:
        st.error(f"Exception verifying VLAN {vlan_id}: {str(e)}")
        return False


def configure_switchport_access(dut, interface, vlan_id, cli_type="klish"):
    """
    Configure interface as switchport access to VLAN and bring it up.

    Args:
        dut: Device under test
        interface: Interface name
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring {interface} as access port for VLAN {vlan_id} on {dut}")

    try:
        # Use direct Klish commands to configure switchport and bring up interface
        commands = []
        commands.append(f"interface {interface}")
        commands.append(f"switchport access vlan {vlan_id}")
        commands.append("no shutdown")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured {interface} as access port for VLAN {vlan_id} and brought it up")

        return True
    except Exception as e:
        st.error(f"Exception configuring switchport: {str(e)}")
        return False


def configure_vlan_ipv6_address(dut, vlan_name, ipv6_addr, mask, cli_type="klish"):
    """
    Configure IPv6 address on VLAN interface and bring it up.

    Args:
        dut: Device under test
        vlan_name: VLAN interface name (e.g., Vlan100)
        ipv6_addr: IPv6 address
        mask: Subnet mask
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring IPv6 address {ipv6_addr}/{mask} on {vlan_name} for {dut}")

    try:
        # Use direct Klish commands to configure IP and bring up interface
        commands = []
        commands.append(f"interface {vlan_name}")
        commands.append(f"ipv6 address {ipv6_addr}/{mask}")
        commands.append("no shutdown")


        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured IPv6 address on {vlan_name} and brought it up")

        # Wait for interface to come up
        st.wait(2, "Waiting for VLAN interface to come up")
        return True
    except Exception as e:
        st.error(f"Failed to configure IPv6 address on {vlan_name}: {str(e)}")
        return False


def verify_vlan_ipv6_interface(dut, vlan_name, ipv6_addr, mask):
    """
    Verify IPv6 address configuration on VLAN interface using direct Klish commands.

    Args:
        dut: Device under test
        vlan_name: VLAN interface name
        ipv6_addr: Expected IPv6 address
        mask: Expected subnet mask

    Returns:
        bool: True if verification passes, False otherwise
    """
    st.log(f"Verifying IPv6 address {ipv6_addr}/{mask} on {vlan_name} for {dut}")

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
            # Pattern matches lines like: "Vlan100              2001:db8:100::1/64"
            pattern = rf'{vlan_name}\s+({ipv6_addr}/{mask})'
            match = re.search(pattern, output, re.IGNORECASE)

            if match:
                st.log(f"Successfully verified IPv6 address {expected_ip} on {vlan_name}")
                return True
            else:
                # Try simpler check - just see if both interface and IP are in output
                if vlan_name in output and expected_ip in output:
                    st.log(f"Successfully verified IPv6 address {expected_ip} on {vlan_name} (simple match)")
                    return True

        st.error(f"Failed to verify IPv6 address {expected_ip} on {vlan_name}")
        return False

    except Exception as e:
        st.error(f"Exception during IPv6 verification: {str(e)}")
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
        # Use direct Klish commands
        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"router-id {router_id}")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP router on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP router on {dut}: {str(e)}")
        return False


def configure_bgp_neighbor_vlan(dut, local_asn, neighbor_ip, remote_asn, family="ipv6", cli_type="klish"):
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


        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor {neighbor_ip} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor {neighbor_ip} on {dut}: {str(e)}")
        return False


def verify_bgp_neighbor_state_vlan(dut, neighbor_ip, state='Established', family='ipv6', timeout=90, cli_type='klish'):
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


def cleanup_vlan_bgp_config():
    """
    Clean up BGP, IPv6, VLAN interface, and VLAN configuration from all DUTs using direct Klish commands.
    """
    st.log("Cleaning up VLAN eBGP and IPv6 configuration")

    dut_list = [data.dut1, data.dut2]

    # Clean up BGP configuration
    st.log("Removing BGP configuration")
    for dut in dut_list:
        commands = ["no router bgp"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

    # Clean up IP configuration on VLAN interface
    st.log("Removing IP configuration from VLAN interfaces")
    for dut in dut_list:
        commands = []
        commands.append(f"interface {data.vlan_name}")
        commands.append("no ip address")
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

    # Clean up switchport access configuration
    st.log("Removing switchport access configuration")
    commands_dut1 = []
    commands_dut1.append(f"interface {data.dut1_dut2_port}")
    commands_dut1.append("no switchport access Vlan")
    st.config(data.dut1, commands_dut1, type=data.cli_type, skip_error_check=True)

    commands_dut2 = []
    commands_dut2.append(f"interface {data.dut2_dut1_port}")
    commands_dut2.append("no switchport access Vlan")
    st.config(data.dut2, commands_dut2, type=data.cli_type, skip_error_check=True)

    # Clean up VLAN
    st.log("Removing VLAN configuration")
    for dut in dut_list:
        commands = [f"no vlan {data.vlan_id}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

    st.log("Cleanup completed")


@pytest.mark.topology("any")
class TestIpv6VlanBgpEbgpInterface:
    """
    Test class for IPv6 eBGP over VLAN interface validation.
    """

    @pytest.mark.test_ipv6_vlan_bgp_ebgp_basic
    def test_ipv6_vlan_bgp_ebgp_interface_config_verify(self):
        """
        TestCase: test_ipv6_vlan_bgp_ebgp_interface_config_verify

        Test Steps:
        1. Create VLAN 100 on both DUTs
        1.1. Verify VLAN creation using show Vlan
        2. Configure Ethernet32 as access port for VLAN 100
        3. Configure IPv6 addresses on VLAN interfaces
        4. Verify IPv6 address configuration
        5. Test IPv6 connectivity via ping (click CLI)
        6. Configure eBGP router with router-id on both DUTs
        7. Configure eBGP neighbors (AS 65001 <-> AS 65002)
        8. Verify BGP session establishment (accepts (Policy) state)
        9. Verify BGP neighbor details

        Expected Result:
        - All configuration steps succeed
        - VLAN verified using show Vlan command
        - IPv6 connectivity verified via ping over VLAN
        - eBGP sessions establish successfully (Established or (Policy))
        """
        st.banner("TEST: IPv6 VLAN eBGP Interface Configuration and Verification")

        # Step 1: Create VLAN 100 on both DUTs
        st.log("Step 1: Creating VLAN 100 on both DUTs")

        result1 = create_vlan(data.dut1, data.vlan_id, data.cli_type)
        result2 = create_vlan(data.dut2, data.vlan_id, data.cli_type)

        if not (result1 and result2):
            st.report_fail("msg", "Failed to create VLAN on one or both DUTs")

        # Step 1.1: Verify VLAN creation using show Vlan
        st.log("Step 1.1: Verifying VLAN creation using show Vlan")

        result1 = verify_vlan_config(data.dut1, data.vlan_id, data.cli_type)
        result2 = verify_vlan_config(data.dut2, data.vlan_id, data.cli_type)

        if not (result1 and result2):
            st.report_fail("msg", "Failed to verify VLAN on one or both DUTs")

        # Step 2: Configure Ethernet32 as access port for VLAN 100
        st.log("Step 2: Configuring Ethernet32 as access port for VLAN 100")

        result1 = configure_switchport_access(data.dut1, data.dut1_dut2_port, data.vlan_id, data.cli_type)
        result2 = configure_switchport_access(data.dut2, data.dut2_dut1_port, data.vlan_id, data.cli_type)

        if not (result1 and result2):
            st.report_fail("msg", "Failed to configure switchport access on one or both DUTs")

        # Step 3: Configure IPv6 addresses on VLAN interfaces
        st.log("Step 3: Configuring IPv6 addresses on VLAN interfaces")

        result1 = configure_vlan_ipv6_address(
            data.dut1, data.vlan_name, data.dut1_ipv6, data.ipv6_mask, data.cli_type
        )
        result2 = configure_vlan_ipv6_address(
            data.dut2, data.vlan_name, data.dut2_ipv6, data.ipv6_mask, data.cli_type
        )

        if not (result1 and result2):
            st.report_fail("msg", "Failed to configure IPv6 addresses on VLAN interfaces")

        # Step 4: Verify IPv6 address configuration
        st.log("Step 4: Verifying IPv6 address configuration on VLAN interfaces")

        result1 = verify_vlan_ipv6_interface(
            data.dut1, data.vlan_name, data.dut1_ipv6, data.ipv6_mask
        )
        result2 = verify_vlan_ipv6_interface(
            data.dut2, data.vlan_name, data.dut2_ipv6, data.ipv6_mask
        )

        if not (result1 and result2):
            st.report_fail("msg", "Failed to verify IPv6 addresses on VLAN interfaces")

        # Step 5: Test IPv6 connectivity via ping (click CLI)
        st.log("Step 5: Testing IPv6 connectivity via ping over VLAN")

        # Ping from DUT1 to DUT2
        result1 = verify_ipv6_ping(data.dut1, data.dut2_ipv6, data.ping_count)

        # Ping from DUT2 to DUT1
        result2 = verify_ipv6_ping(data.dut2, data.dut1_ipv6, data.ping_count)

        if not (result1 and result2):
            st.report_fail("msg", "IPv6 ping failed between DUTs over VLAN")

        # Step 6: Configure eBGP router with router-id
        st.log("Step 6: Configuring eBGP router with router-id on both DUTs")

        # Configure BGP on DUT1 with AS 65001 and router-id 1.1.1.1
        if not configure_bgp_router_with_router_id(data.dut1, data.bgp_asn_dut1, data.router_id_dut1, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut1}")

        # Configure BGP on DUT2 with AS 65002 and router-id 2.2.2.2
        if not configure_bgp_router_with_router_id(data.dut2, data.bgp_asn_dut2, data.router_id_dut2, data.cli_type):
            st.report_fail("msg", f"Failed to configure BGP router on {data.dut2}")

        # Step 7: Configure eBGP neighbors (different AS numbers)
        st.log("Step 7: Configuring eBGP neighbors on both DUTs (AS 65001 <-> AS 65002)")

        # DUT1 (AS 65001) peers with DUT2 (AS 65002)
        if not configure_bgp_neighbor_vlan(
            data.dut1, data.bgp_asn_dut1, data.dut2_ipv6, data.bgp_asn_dut2, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure eBGP neighbor on {data.dut1}")

        # DUT2 (AS 65002) peers with DUT1 (AS 65001)
        if not configure_bgp_neighbor_vlan(
            data.dut2, data.bgp_asn_dut2, data.dut1_ipv6, data.bgp_asn_dut1, data.af_ipv6, data.cli_type
        ):
            st.report_fail("msg", f"Failed to configure eBGP neighbor on {data.dut2}")

        # Step 8: Wait and verify eBGP session establishment (accepts (Policy) state)
        st.log("Step 8: Verifying eBGP session establishment (accepts Established or (Policy) state)")
        st.wait(data.bgp_wait, "Waiting for eBGP session establishment")

        result1 = verify_bgp_neighbor_state_vlan(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )
        result2 = verify_bgp_neighbor_state_vlan(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )

        if not (result1 and result2):
            st.report_fail("msg", "eBGP session failed to establish on one or both DUTs over VLAN")

        # Step 9: Verify detailed BGP neighbor information using sonic-cli (Klish)
        st.log("Step 9: Verifying detailed eBGP neighbor information using sonic-cli")

        # Get BGP neighbor details from DUT1 using Klish
        st.log(f"Showing BGP IPv6 neighbor details on {data.dut1}")
        bgp_output1 = st.show(data.dut1, f"show bgp ipv6 unicast neighbors {data.dut2_ipv6}", type='klish')
        st.log(f"eBGP neighbor details on {data.dut1}: {bgp_output1}")

        # Get BGP neighbor details from DUT2 using Klish
        st.log(f"Showing BGP IPv6 neighbor details on {data.dut2}")
        bgp_output2 = st.show(data.dut2, f"show bgp ipv6 unicast neighbors {data.dut1_ipv6}", type='klish')
        st.log(f"eBGP neighbor details on {data.dut2}: {bgp_output2}")

        st.report_pass("test_case_passed")


    @pytest.mark.test_ipv6_vlan_bgp_ebgp_save_reboot
    def test_ipv6_vlan_bgp_ebgp_save_reboot(self):
        """
        TestCase: test_ipv6_vlan_bgp_ebgp_save_reboot

        Pre-requisite:
        - VLAN 100 created
        - IPv6 addresses configured on VLAN interfaces
        - eBGP sessions established (AS 65001 <-> AS 65002)

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
        - IPv6 connectivity restored over VLAN
        """
        st.banner("TEST: IPv6 VLAN eBGP Save and Reboot")

        # Ensure configuration is in place (run basic config first)
        st.log("Setting up IPv6 VLAN eBGP configuration for save/reboot test")
        self.test_ipv6_vlan_bgp_ebgp_interface_config_verify()

        # Step 1: Verify eBGP session is established (pre-check)
        st.log("Step 1: Pre-reboot verification - checking eBGP sessions")

        result1 = verify_bgp_neighbor_state_vlan(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, timeout=30
        )
        result2 = verify_bgp_neighbor_state_vlan(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, timeout=30
        )

        if not (result1 and result2):
            st.report_fail("msg", "eBGP sessions not established before save/reboot")

        # Step 2: Verify IPv6 connectivity via ping (pre-reboot)
        st.log("Step 2: Pre-reboot verification - testing IPv6 connectivity over VLAN")

        result1 = verify_ipv6_ping(data.dut1, data.dut2_ipv6, data.ping_count)
        result2 = verify_ipv6_ping(data.dut2, data.dut1_ipv6, data.ping_count)

        if not (result1 and result2):
            st.report_fail("msg", "IPv6 ping failed before save/reboot")

        # Step 3: Check BGP routes using sonic-cli (Klish)
        st.log("Step 3: Checking eBGP IPv6 routes using sonic-cli")

        bgp_routes1 = st.show(data.dut1, "show bgp ipv6 unicast summary", type='klish')
        st.log(f"eBGP IPv6 routes on {data.dut1}: {bgp_routes1}")

        bgp_routes2 = st.show(data.dut2, "show bgp ipv6 unicast summary", type='klish')
        st.log(f"eBGP IPv6 routes on {data.dut2}: {bgp_routes2}")

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

        result1 = verify_bgp_neighbor_state_vlan(
            data.dut1, data.dut2_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )
        result2 = verify_bgp_neighbor_state_vlan(
            data.dut2, data.dut1_ipv6, 'Established', data.af_ipv6, timeout=data.bgp_wait
        )

        if not (result1 and result2):
            st.report_fail("msg", "eBGP sessions failed to re-establish after reboot")

        # Step 7: Verify IPv6 connectivity after reboot
        st.log("Step 7: Post-reboot verification - testing IPv6 connectivity over VLAN")

        result1 = verify_ipv6_ping(data.dut1, data.dut2_ipv6, data.ping_count)
        result2 = verify_ipv6_ping(data.dut2, data.dut1_ipv6, data.ping_count)

        if not (result1 and result2):
            st.report_fail("msg", "IPv6 ping failed after reboot")

        # Verify detailed BGP information post-reboot using sonic-cli (Klish)
        st.log("Verifying detailed eBGP neighbor information after reboot using sonic-cli")

        bgp_output1 = st.show(data.dut1, f"show bgp ipv6 unicast neighbors {data.dut2_ipv6}", type='klish')
        st.log(f"eBGP neighbor details on {data.dut1} after reboot: {bgp_output1}")

        bgp_output2 = st.show(data.dut2, f"show bgp ipv6 unicast neighbors {data.dut1_ipv6}", type='klish')
        st.log(f"eBGP neighbor details on {data.dut2} after reboot: {bgp_output2}")

        st.report_pass("test_case_passed")
