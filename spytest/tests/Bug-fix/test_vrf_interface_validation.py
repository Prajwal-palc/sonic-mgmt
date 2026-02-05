"""
VRF INTERFACE CONFIGURATION AND VALIDATION
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/bug-fix/test_vrf_interface_validation.py \
  --logs-path ./logs/test_vrf_validation_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of VRF (Virtual Routing and Forwarding) configuration
  using sonic-cli (Klish). This test suite validates:
  - Creating VRF and assigning interfaces
  - VRF appears in 'show ip vrf' with correct interfaces
  - VRF configuration in 'show running-configuration interface'
  - Error handling when L3 config exists before VRF assignment
  - Correct sequence: remove IP, add VRF, then add IP back

Pre-requisites:
  - Topology: 2-node or 1-node | Supported: HW and Virtual
  - CLI type: klish (sonic-cli)
  - Interfaces taken from testbed configuration

Test Steps:
  1. Create VRF (Vrf_11)
  2. Assign interface to VRF without IP (e.g., Ethernet0)
  3. Verify VRF in 'show ip vrf'
  4. Verify VRF in 'show running-configuration interface'
  5. Try assigning interface with IP to VRF (expect error)
  6. Remove IP, assign VRF, add IP back (correct sequence)
  7. Verify both interfaces in VRF
  8. Clean up VRF configuration
"""

from __future__ import annotations

import pytest
import re

from spytest import st, SpyTestDict


# Test data dictionary
data = SpyTestDict()
data.vrf_name = "Vrf_11"
data.ip_address = "20.1.1.3"
data.ip_mask = "24"
data.cli_type = "klish"


@pytest.fixture(scope="module", autouse=True)
def vrf_validation_module_hooks(request):
    """
    Module-level fixture for VRF validation test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1")

    st.banner("MODULE SETUP: VRF Interface Validation Test")

    # Store DUT handle
    data.dut1 = vars.D1

    # Get interfaces from testbed
    # Interface 1: Will be assigned to VRF without IP
    if hasattr(vars, 'D1D2P1'):
        data.interface1 = vars.D1D2P1
    elif hasattr(vars, 'D1T1P1'):
        data.interface1 = vars.D1T1P1
    else:
        data.interface1 = "Ethernet0"

    # Interface 2: Will test L3 config + VRF scenario
    if hasattr(vars, 'D1D2P2'):
        data.interface2 = vars.D1D2P2
    elif hasattr(vars, 'D1T1P2'):
        data.interface2 = vars.D1T1P2
    else:
        data.interface2 = "Ethernet272"

    st.log(f"DUT1: {data.dut1}")
    st.log(f"Interface 1 (no IP): {data.interface1}")
    st.log(f"Interface 2 (with IP): {data.interface2}")

    # INITIAL CLEANUP - Start with clean state
    st.banner("INITIAL CLEANUP: Removing existing VRF configuration")
    initial_cleanup()

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up VRF configuration")
    cleanup_vrf_config()


@pytest.fixture(scope="function", autouse=True)
def vrf_validation_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def initial_cleanup():
    """
    Initial cleanup: Remove VRF configuration and IP addresses.
    """
    st.log("Starting initial cleanup - removing VRF and IP configuration")

    try:
        # Remove IP addresses from interfaces
        for interface in [data.interface1, data.interface2]:
            commands = []
            commands.append(f"interface {interface}")
            commands.append("no ip address")
            commands.append("exit")
            st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove VRF binding from interfaces
        for interface in [data.interface1, data.interface2]:
            commands = []
            commands.append(f"interface {interface}")
            commands.append("no ip vrf forwarding")
            commands.append("exit")
            st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove VRF
        commands = [f"no ip vrf {data.vrf_name}"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        st.log("Initial cleanup completed")
    except Exception as e:
        st.error(f"Error during initial cleanup: {str(e)}")


def create_vrf(dut, vrf_name, cli_type="klish"):
    """
    Create VRF.

    Args:
        dut: Device under test
        vrf_name: VRF name
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Creating VRF {vrf_name} on {dut}")

    try:
        commands = [f"ip vrf {vrf_name}"]
        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully created VRF {vrf_name}")
        return True
    except Exception as e:
        st.error(f"Failed to create VRF {vrf_name}: {str(e)}")
        return False


def assign_interface_to_vrf(dut, interface, vrf_name, cli_type="klish"):
    """
    Assign interface to VRF.

    Args:
        dut: Device under test
        interface: Interface name
        vrf_name: VRF name
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Assigning interface {interface} to VRF {vrf_name} on {dut}")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append(f"ip vrf forwarding {vrf_name}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully assigned {interface} to VRF {vrf_name}")
        return True
    except Exception as e:
        st.error(f"Failed to assign {interface} to VRF {vrf_name}: {str(e)}")
        return False


def assign_interface_to_vrf_expect_error(dut, interface, vrf_name, cli_type="klish"):
    """
    Try to assign interface with IP to VRF (expect error).

    Args:
        dut: Device under test
        interface: Interface name
        vrf_name: VRF name
        cli_type: CLI type (default: klish)

    Returns:
        tuple: (bool, str) - (Error occurred, Output message)
    """
    st.log(f"Attempting to assign interface {interface} with IP to VRF {vrf_name} (expecting error)")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append(f"ip vrf forwarding {vrf_name}")
        commands.append("exit")

        output = st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.log(f"Command output:\n{output}")

        # Check if error occurred
        if output and isinstance(output, str):
            if "error" in output.lower() or "l3 configuration exists" in output.lower():
                st.log("Expected error occurred: L3 Configuration exists")
                return True, output

        st.log("No error occurred (unexpected)")
        return False, output

    except Exception as e:
        st.log(f"Exception occurred (may indicate error): {str(e)}")
        return True, str(e)


def configure_ip_address(dut, interface, ip_address, mask, cli_type="klish"):
    """
    Configure IP address on interface.

    Args:
        dut: Device under test
        interface: Interface name
        ip_address: IP address
        mask: Subnet mask
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring IP address {ip_address}/{mask} on {interface}")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append(f"ip address {ip_address}/{mask}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured IP on {interface}")
        return True
    except Exception as e:
        st.error(f"Failed to configure IP on {interface}: {str(e)}")
        return False


def remove_ip_address(dut, interface, cli_type="klish"):
    """
    Remove IP address from interface.

    Args:
        dut: Device under test
        interface: Interface name
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Removing IP address from {interface}")

    try:
        commands = []
        commands.append(f"interface {interface}")
        commands.append("no ip address")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully removed IP from {interface}")
        return True
    except Exception as e:
        st.error(f"Failed to remove IP from {interface}: {str(e)}")
        return False


def verify_vrf_in_show_ip_vrf(dut, vrf_name, expected_interfaces, cli_type="klish"):
    """
    Verify VRF appears in 'show ip vrf' with expected interfaces.

    Expected output:
    VRF          Interfaces
    --------     ------------
    default
    Vrf_11       Ethernet0
                 Ethernet272

    Args:
        dut: Device under test
        vrf_name: VRF name to verify
        expected_interfaces: List of expected interfaces
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if VRF found with expected interfaces, False otherwise
    """
    st.log(f"Verifying VRF {vrf_name} in 'show ip vrf' with interfaces {expected_interfaces}")

    try:
        output = st.show(dut, "show ip vrf", type=cli_type, skip_error_check=True)
        st.log(f"Show ip vrf output: {output}")

        if not output:
            # Try raw command output
            raw_output = st.config(dut, "show ip vrf", type=cli_type, skip_error_check=True)
            st.log(f"Raw show ip vrf output:\n{raw_output}")

            if raw_output and isinstance(raw_output, str):
                # Parse raw output
                if vrf_name in raw_output:
                    st.log(f"VRF {vrf_name} found in raw output")

                    # Check for interfaces
                    found_interfaces = []
                    for interface in expected_interfaces:
                        if interface in raw_output:
                            found_interfaces.append(interface)
                            st.log(f"Found interface {interface} in VRF {vrf_name}")

                    if len(found_interfaces) == len(expected_interfaces):
                        st.log(f"All expected interfaces found in VRF {vrf_name}")
                        return True
                    else:
                        st.error(f"Not all interfaces found. Expected: {expected_interfaces}, Found: {found_interfaces}")
                        return False
                else:
                    st.error(f"VRF {vrf_name} not found in output")
                    return False

        # Parse structured output
        vrf_found = False
        for entry in output:
            entry_vrf = entry.get('vrf', '') or entry.get('vrfname', '')

            if str(entry_vrf).strip() == vrf_name:
                vrf_found = True
                st.log(f"Found VRF {vrf_name} in output")

                # Check interfaces
                interfaces_str = entry.get('interfaces', '') or entry.get('interface', '')
                st.log(f"VRF interfaces: {interfaces_str}")

                # Verify all expected interfaces are present
                for interface in expected_interfaces:
                    if interface in str(interfaces_str):
                        st.log(f"Found interface {interface} in VRF")
                    else:
                        st.error(f"Interface {interface} not found in VRF")
                        return False

                return True

        if not vrf_found:
            st.error(f"VRF {vrf_name} not found in 'show ip vrf' output")
            return False

        return True

    except Exception as e:
        st.error(f"Exception during VRF verification: {str(e)}")
        return False


def verify_vrf_in_interface_config(dut, interface, vrf_name, cli_type="klish"):
    """
    Verify VRF appears in 'show running-configuration interface'.

    Expected output:
    !
    interface Ethernet0
    ip vrf forwarding Vrf_11
    ...

    Args:
        dut: Device under test
        interface: Interface name
        vrf_name: Expected VRF name
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if VRF found in config, False otherwise
    """
    st.log(f"Verifying VRF {vrf_name} in running config for {interface}")

    try:
        command = f"show running-configuration interface {interface}"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        st.log(f"Running config for {interface}:\n{output}")

        if not output or not isinstance(output, str):
            st.error("No output from show running-configuration")
            return False

        # Check for VRF configuration line
        pattern = rf'ip\s+vrf\s+forwarding\s+{re.escape(vrf_name)}'
        if re.search(pattern, output, re.IGNORECASE):
            st.log(f"Found VRF {vrf_name} in running config for {interface}")
            return True
        else:
            st.error(f"VRF {vrf_name} not found in running config for {interface}")
            return False

    except Exception as e:
        st.error(f"Exception during running config verification: {str(e)}")
        return False


def cleanup_vrf_config():
    """
    Clean up VRF configuration.
    """
    st.log("Cleaning up VRF configuration")

    try:
        # Remove IP addresses from interfaces
        for interface in [data.interface1, data.interface2]:
            commands = []
            commands.append(f"interface {interface}")
            commands.append("no ip address")
            commands.append("exit")
            st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove VRF binding from interfaces
        for interface in [data.interface1, data.interface2]:
            commands = []
            commands.append(f"interface {interface}")
            commands.append("no ip vrf forwarding")
            commands.append("exit")
            st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove VRF
        commands = [f"no ip vrf {data.vrf_name}"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        st.log("Cleanup completed")
    except Exception as e:
        st.error(f"Error during cleanup: {str(e)}")


@pytest.mark.topology("any")
class TestVrfInterfaceValidation:
    """
    Test class for VRF interface configuration validation.
    """

    @pytest.mark.test_vrf_basic_config
    def test_vrf_basic_config(self):
        """
        TestCase: test_vrf_basic_config

        Test Steps:
        1. Create VRF (Vrf_11)
        2. Assign interface without IP to VRF
        3. Verify VRF in 'show ip vrf'
        4. Verify VRF in 'show running-configuration interface'

        Expected Result:
        - VRF created successfully
        - Interface assigned to VRF
        - VRF appears in show commands
        """
        st.banner("TEST: VRF Basic Configuration")

        # Step 1: Create VRF
        st.log(f"Step 1: Creating VRF {data.vrf_name}")

        if not create_vrf(data.dut1, data.vrf_name, data.cli_type):
            st.report_fail("msg", f"Failed to create VRF {data.vrf_name}")

        # Step 2: Assign interface to VRF
        st.log(f"Step 2: Assigning {data.interface1} to VRF {data.vrf_name}")

        if not assign_interface_to_vrf(data.dut1, data.interface1, data.vrf_name, data.cli_type):
            st.report_fail("msg", f"Failed to assign {data.interface1} to VRF")

        st.wait(2, "Waiting for VRF configuration to apply")

        # Step 3: Verify VRF in 'show ip vrf'
        st.log(f"Step 3: Verifying VRF {data.vrf_name} in 'show ip vrf'")

        if not verify_vrf_in_show_ip_vrf(data.dut1, data.vrf_name, [data.interface1], data.cli_type):
            st.report_fail("msg", f"VRF {data.vrf_name} not found in 'show ip vrf'")

        # Step 4: Verify VRF in running config
        st.log(f"Step 4: Verifying VRF in running config for {data.interface1}")

        if not verify_vrf_in_interface_config(data.dut1, data.interface1, data.vrf_name, data.cli_type):
            st.report_fail("msg", f"VRF not found in running config for {data.interface1}")

        st.log("VRF basic configuration test PASSED")
        st.report_pass("test_case_passed")


    @pytest.mark.test_vrf_l3_config_error
    def test_vrf_l3_config_error_handling(self):
        """
        TestCase: test_vrf_l3_config_error_handling

        Test Steps:
        1. Create VRF if not exists
        2. Configure IP address on interface
        3. Try to assign interface to VRF (expect error)
        4. Remove IP address
        5. Assign interface to VRF (should succeed)
        6. Configure IP address again (should succeed)
        7. Verify VRF with both interfaces

        Expected Result:
        - Error when trying to assign interface with IP to VRF
        - Success after removing IP, assigning VRF, then adding IP
        - Both interfaces appear in VRF
        """
        st.banner("TEST: VRF L3 Configuration Error Handling")

        # Step 1: Ensure VRF exists
        st.log(f"Step 1: Ensuring VRF {data.vrf_name} exists")
        create_vrf(data.dut1, data.vrf_name, data.cli_type)

        # Step 2: Configure IP on interface
        st.log(f"Step 2: Configuring IP {data.ip_address}/{data.ip_mask} on {data.interface2}")

        if not configure_ip_address(data.dut1, data.interface2, data.ip_address, data.ip_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IP on {data.interface2}")

        # Step 3: Try to assign to VRF (expect error)
        st.log(f"Step 3: Attempting to assign {data.interface2} with IP to VRF (expecting error)")

        error_occurred, output = assign_interface_to_vrf_expect_error(
            data.dut1, data.interface2, data.vrf_name, data.cli_type
        )

        if not error_occurred:
            st.report_fail("msg", "Expected error did not occur when assigning interface with IP to VRF")

        st.log("Expected error occurred: L3 Configuration exists")

        # Step 4: Remove IP address
        st.log(f"Step 4: Removing IP address from {data.interface2}")

        if not remove_ip_address(data.dut1, data.interface2, data.cli_type):
            st.report_fail("msg", f"Failed to remove IP from {data.interface2}")

        # Step 5: Assign to VRF
        st.log(f"Step 5: Assigning {data.interface2} to VRF {data.vrf_name}")

        if not assign_interface_to_vrf(data.dut1, data.interface2, data.vrf_name, data.cli_type):
            st.report_fail("msg", f"Failed to assign {data.interface2} to VRF after removing IP")

        # Step 6: Configure IP again
        st.log(f"Step 6: Configuring IP {data.ip_address}/{data.ip_mask} on {data.interface2} again")

        if not configure_ip_address(data.dut1, data.interface2, data.ip_address, data.ip_mask, data.cli_type):
            st.report_fail("msg", f"Failed to configure IP after VRF assignment")

        st.wait(2, "Waiting for configuration to apply")

        # Step 7: Verify both interfaces in VRF
        st.log(f"Step 7: Verifying both interfaces in VRF {data.vrf_name}")

        if not verify_vrf_in_show_ip_vrf(
            data.dut1, data.vrf_name, [data.interface1, data.interface2], data.cli_type
        ):
            st.report_fail("msg", "Not all interfaces found in VRF")

        # Verify running config for interface2
        if not verify_vrf_in_interface_config(data.dut1, data.interface2, data.vrf_name, data.cli_type):
            st.report_fail("msg", f"VRF not found in running config for {data.interface2}")

        st.log("VRF L3 configuration error handling test PASSED")
        st.report_pass("test_case_passed")
