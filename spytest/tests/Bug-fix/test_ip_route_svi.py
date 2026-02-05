"""
IP ROUTE ON SVI INTERFACE
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/test_ip_route_svi.py \
  --logs-path ./logs/test_ip_route_svi_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IP routes on SVI (Switched Virtual Interface).
  This test suite creates VLAN, configures IP address on SVI interface,
  assigns physical port to VLAN, validates IP route and VLAN configuration,
  and performs complete cleanup.

Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - At least one Ethernet interface available for VLAN assignment
  - CLI type: klish (sonic-cli)

Test Steps:
  1. Initial cleanup - remove any existing VLAN and SVI configuration
  2. Create VLAN 10
  3. Configure IP address on Vlan10 interface
  4. Assign Ethernet port to VLAN 10 as access port
  5. Validate VLAN configuration (show Vlan)
  6. Validate IP route (show ip route - verify connected route)
  7. Unconfigure - remove IP, VLAN assignment, and VLAN
"""

from __future__ import annotations

import pytest

from spytest import st, SpyTestDict
import apis.routing.ip as ip_api
import apis.switching.vlan as vlan_api


# Test data dictionary
data = SpyTestDict()
data.vlan_id = "10"
data.svi_ip = "10.1.2.4"
data.svi_mask = "24"
data.svi_network = "10.1.2.0/24"
data.cli_type = "klish"


@pytest.fixture(scope="module", autouse=True)
def svi_route_module_hooks(request):
    """
    Module-level fixture for SVI IP route test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1")

    st.banner("MODULE SETUP: IP Route on SVI Interface Test")

    # Store DUT handle
    data.dut1 = vars.D1

    # Get first available port for VLAN assignment
    # Using D1D2P1 if available, otherwise use the first port from topology
    if hasattr(vars, 'D1D2P1'):
        data.eth_port = vars.D1D2P1
    elif hasattr(vars, 'D1T1P1'):
        data.eth_port = vars.D1T1P1
    else:
        # Fallback to getting ports from platform
        data.eth_port = st.get_free_ports(data.dut1)[0]

    st.log(f"DUT1: {data.dut1}")
    st.log(f"Ethernet Port for VLAN: {data.eth_port}")

    # INITIAL CLEANUP - Start with clean state
    st.banner("INITIAL CLEANUP: Removing existing VLAN and SVI configuration")
    initial_cleanup()

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up SVI and VLAN configuration")
    cleanup_svi_vlan_config()


@pytest.fixture(scope="function", autouse=True)
def svi_route_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def initial_cleanup():
    """
    Initial cleanup: Remove IP from SVI, VLAN member, and VLAN.
    Ensures we start with a clean state.
    """
    st.log("Starting initial cleanup - removing SVI IP, VLAN member, and VLAN")

    # Remove IP address from SVI interface
    st.log(f"Removing IP address from Vlan{data.vlan_id}")
    commands = []
    commands.append(f"interface Vlan{data.vlan_id}")
    commands.append("no ip address")
    commands.append("exit")
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

    # Remove port from VLAN
    st.log(f"Removing {data.eth_port} from VLAN {data.vlan_id}")
    commands = []
    commands.append(f"interface {data.eth_port}")
    commands.append("no switchport access vlan")
    commands.append("exit")
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

    # Delete VLAN
    st.log(f"Deleting VLAN {data.vlan_id}")
    commands = [f"no vlan {data.vlan_id}"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

    st.log("Initial cleanup completed")


def create_vlan(dut, vlan_id, cli_type="klish"):
    """
    Create VLAN.

    Args:
        dut: Device under test
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Creating VLAN {vlan_id} on {dut}")

    try:
        commands = [f"vlan {vlan_id}"]
        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully created VLAN {vlan_id}")
        return True
    except Exception as e:
        st.error(f"Failed to create VLAN {vlan_id}: {str(e)}")
        return False


def configure_svi_ip(dut, vlan_id, ip_addr, mask, cli_type="klish"):
    """
    Configure IP address on SVI interface.

    Args:
        dut: Device under test
        vlan_id: VLAN ID
        ip_addr: IP address
        mask: Subnet mask
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring IP address {ip_addr}/{mask} on Vlan{vlan_id}")

    try:
        commands = []
        commands.append(f"interface Vlan{vlan_id}")
        commands.append(f"ip address {ip_addr}/{mask}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured IP address on Vlan{vlan_id}")
        return True
    except Exception as e:
        st.error(f"Failed to configure IP on Vlan{vlan_id}: {str(e)}")
        return False


def assign_port_to_vlan(dut, interface, vlan_id, cli_type="klish"):
    """
    Assign port to VLAN as access port.

    Args:
        dut: Device under test
        interface: Interface name
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Assigning {interface} to VLAN {vlan_id} as access port")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append(f"switchport access vlan {vlan_id}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully assigned {interface} to VLAN {vlan_id}")
        return True
    except Exception as e:
        st.error(f"Failed to assign {interface} to VLAN {vlan_id}: {str(e)}")
        return False


def verify_vlan_config(dut, vlan_id, expected_port, cli_type="klish"):
    """
    Verify VLAN configuration using 'show Vlan'.

    Args:
        dut: Device under test
        vlan_id: VLAN ID to verify
        expected_port: Expected port in VLAN
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if VLAN exists with expected port, False otherwise
    """
    st.log(f"Verifying VLAN {vlan_id} configuration on {dut}")

    try:
        output = st.show(dut, "show Vlan", type=cli_type)
        st.log(f"VLAN output: {output}")

        if output:
            for entry in output:
                # Log all keys for debugging
                st.log(f"VLAN entry keys: {list(entry.keys())}")
                st.log(f"VLAN entry data: {entry}")

                # Try different possible key names for VLAN ID
                vlan_num = (entry.get('vid', '') or
                           entry.get('vlan_id', '') or
                           entry.get('num', '') or
                           entry.get('vlanid', ''))

                # Remove "Vlan" prefix if present
                vlan_num_str = str(vlan_num).replace('Vlan', '').strip()

                if vlan_num_str == str(vlan_id):
                    st.log(f"Found VLAN {vlan_id} in output")

                    # Check if expected port is in the VLAN
                    # Try different possible key names for ports
                    ports = (entry.get('ports', '') or
                            entry.get('member_ports', '') or
                            entry.get('members', ''))

                    st.log(f"VLAN {vlan_id} ports: {ports}")

                    if expected_port in str(ports):
                        st.log(f"VLAN {vlan_id} contains expected port {expected_port}")
                        return True
                    else:
                        st.error(f"VLAN {vlan_id} does not contain expected port {expected_port}")
                        return False

        st.error(f"VLAN {vlan_id} not found in output")
        return False

    except Exception as e:
        st.error(f"Exception during VLAN verification: {str(e)}")
        return False


def verify_ip_route(dut, network, interface, cli_type="klish"):
    """
    Verify IP route exists for the network connected to SVI.

    Args:
        dut: Device under test
        network: Network to verify (e.g., "10.1.2.0/24")
        interface: Expected interface (e.g., "Vlan10")
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if route exists, False otherwise
    """
    st.log(f"Verifying IP route for network {network} on {dut}")

    try:
        output = st.show(dut, "show ip route", type=cli_type)
        st.log(f"IP route output: {output}")

        if output:
            for entry in output:
                # Log all keys for debugging
                st.log(f"Route entry keys: {list(entry.keys())}")
                st.log(f"Route entry data: {entry}")

                # Try different possible key names for network/prefix
                route_network = (entry.get('ip_prefix', '') or
                                entry.get('prefix', '') or
                                entry.get('network', '') or
                                entry.get('route', ''))

                route_interface = (entry.get('interface', '') or
                                  entry.get('nexthop_if', '') or
                                  entry.get('intf', ''))

                st.log(f"Route network: {route_network}, Interface: {route_interface}")

                # Check if this is the connected route we're looking for
                if network in str(route_network) and interface in str(route_interface):
                    st.log(f"Found connected route for {network} via {interface}")
                    return True

        st.error(f"Connected route for {network} via {interface} not found")
        return False

    except Exception as e:
        st.error(f"Exception during IP route verification: {str(e)}")
        return False


def remove_svi_ip(dut, vlan_id, cli_type="klish"):
    """
    Remove IP address from SVI interface.

    Args:
        dut: Device under test
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Removing IP address from Vlan{vlan_id}")

    try:
        commands = []
        commands.append(f"interface Vlan{vlan_id}")
        commands.append("no ip address")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully removed IP address from Vlan{vlan_id}")
        return True
    except Exception as e:
        st.error(f"Failed to remove IP from Vlan{vlan_id}: {str(e)}")
        return False


def remove_port_from_vlan(dut, interface, cli_type="klish"):
    """
    Remove port from VLAN.

    Args:
        dut: Device under test
        interface: Interface name
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Removing {interface} from VLAN")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append("no switchport access vlan")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully removed {interface} from VLAN")
        return True
    except Exception as e:
        st.error(f"Failed to remove {interface} from VLAN: {str(e)}")
        return False


def delete_vlan(dut, vlan_id, cli_type="klish"):
    """
    Delete VLAN.

    Args:
        dut: Device under test
        vlan_id: VLAN ID
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Deleting VLAN {vlan_id}")

    try:
        commands = [f"no vlan {vlan_id}"]
        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully deleted VLAN {vlan_id}")
        return True
    except Exception as e:
        st.error(f"Failed to delete VLAN {vlan_id}: {str(e)}")
        return False


def cleanup_svi_vlan_config():
    """
    Clean up SVI IP, VLAN member, and VLAN configuration.
    """
    st.log("Cleaning up SVI and VLAN configuration")

    # Remove IP address from SVI
    remove_svi_ip(data.dut1, data.vlan_id, data.cli_type)

    # Remove port from VLAN
    remove_port_from_vlan(data.dut1, data.eth_port, data.cli_type)

    # Delete VLAN
    delete_vlan(data.dut1, data.vlan_id, data.cli_type)

    st.log("Cleanup completed")


@pytest.mark.topology("any")
class TestIpRouteSvi:
    """
    Test class for IP route on SVI interface validation.
    """

    @pytest.mark.test_ip_route_svi_config_verify
    def test_ip_route_svi_config_verify(self):
        """
        TestCase: test_ip_route_svi_config_verify

        Test Steps:
        1. Create VLAN 10
        2. Configure IP address on Vlan10 interface (10.1.2.4/24)
        3. Assign Ethernet port to VLAN 10 as access port
        4. Validate VLAN configuration (show Vlan)
        5. Validate IP route (show ip route - verify connected route exists)
        6. Unconfigure - remove IP, VLAN member, and VLAN

        Expected Result:
        - VLAN created successfully
        - SVI IP configured successfully
        - Port assigned to VLAN successfully
        - Connected route appears in routing table
        - Cleanup succeeds
        """
        st.banner("TEST: IP Route on SVI Interface - Config, Verify, Unconfigure")

        # Step 1: Create VLAN 10
        st.log("Step 1: Creating VLAN 10")

        if not create_vlan(data.dut1, data.vlan_id, data.cli_type):
            st.report_fail("msg", f"Failed to create VLAN {data.vlan_id}")

        # Step 2: Configure IP address on Vlan10 interface
        st.log("Step 2: Configuring IP address on Vlan10")

        if not configure_svi_ip(data.dut1, data.vlan_id, data.svi_ip, data.svi_mask, data.cli_type):
            st.report_fail("msg", "Failed to configure IP address on SVI")

        # Step 3: Assign Ethernet port to VLAN 10 as access port
        st.log("Step 3: Assigning Ethernet port to VLAN 10")

        if not assign_port_to_vlan(data.dut1, data.eth_port, data.vlan_id, data.cli_type):
            st.report_fail("msg", f"Failed to assign {data.eth_port} to VLAN {data.vlan_id}")

        # Wait for configuration to take effect
        st.wait(3, "Waiting for SVI and VLAN configuration to take effect")

        # Step 4: Validate VLAN configuration
        st.log("Step 4: Validating VLAN configuration")

        # Show VLAN configuration
        st.show(data.dut1, "show Vlan", type=data.cli_type)

        if not verify_vlan_config(data.dut1, data.vlan_id, data.eth_port, data.cli_type):
            st.report_fail("msg", f"Failed to verify VLAN {data.vlan_id} configuration")

        # Step 5: Validate IP route
        st.log("Step 5: Validating IP route for connected network")

        # Show IP route
        st.show(data.dut1, "show ip route", type=data.cli_type)

        if not verify_ip_route(data.dut1, data.svi_network, f"Vlan{data.vlan_id}", data.cli_type):
            st.report_fail("msg", f"Failed to verify IP route for {data.svi_network}")

        # Step 6: Unconfigure - remove IP, VLAN member, and VLAN
        st.log("Step 6: Unconfiguring - removing IP, VLAN member, and VLAN")

        # Remove IP from SVI
        if not remove_svi_ip(data.dut1, data.vlan_id, data.cli_type):
            st.report_fail("msg", "Failed to remove IP address from SVI")

        # Remove port from VLAN
        if not remove_port_from_vlan(data.dut1, data.eth_port, data.cli_type):
            st.report_fail("msg", f"Failed to remove {data.eth_port} from VLAN")

        # Delete VLAN
        if not delete_vlan(data.dut1, data.vlan_id, data.cli_type):
            st.report_fail("msg", f"Failed to delete VLAN {data.vlan_id}")

        # Verify cleanup - show VLAN should not show VLAN 10
        st.log("Verifying cleanup - checking VLAN is removed")
        st.show(data.dut1, "show Vlan", type=data.cli_type)

        # Verify IP route is removed
        st.log("Verifying IP route is removed")
        st.show(data.dut1, "show ip route", type=data.cli_type)

        st.report_pass("test_case_passed")
