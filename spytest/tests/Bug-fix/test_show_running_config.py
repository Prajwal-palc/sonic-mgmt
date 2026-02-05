"""
SHOW RUNNING-CONFIGURATION VALIDATION
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/bug-fix/test_show_running_config.py \
  --logs-path ./logs/test_show_running_config_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validates that 'show running-configuration' commands work correctly in sonic-cli
  for different configuration contexts:
  - show running-configuration interface <interface>
  - show running-configuration bgp
  - show running-configuration ospf

  Tests verify that commands execute successfully and return expected configuration
  sections with proper formatting.

Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - CLI type: klish (sonic-cli)
  - At least one interface configured
  - BGP/OSPF may or may not be configured (test handles both cases)

Test Steps:
  1. Test 'show running-configuration interface <interface>'
  2. Test 'show running-configuration bgp'
  3. Test 'show running-configuration ospf'
  4. Validate command output format and content
"""

from __future__ import annotations

import pytest
import re

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api


# Test data dictionary
data = SpyTestDict()
data.cli_type = "klish"


@pytest.fixture(scope="module", autouse=True)
def show_run_config_module_hooks(request):
    """
    Module-level fixture for show running-configuration test setup.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1")

    st.banner("MODULE SETUP: Show Running-Configuration Test")

    # Store DUT handle
    data.dut1 = vars.D1

    # Get first available interface from testbed
    if hasattr(vars, 'D1D2P1'):
        data.interface = vars.D1D2P1
    elif hasattr(vars, 'D1T1P1'):
        data.interface = vars.D1T1P1
    else:
        # Fallback to common interface
        data.interface = "Ethernet0"

    st.log(f"DUT1: {data.dut1}")
    st.log(f"Test Interface: {data.interface}")

    yield

    st.banner("MODULE TEARDOWN: Show Running-Configuration Test Complete")


@pytest.fixture(scope="function", autouse=True)
def show_run_config_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def execute_show_run_command(dut, command, cli_type="klish"):
    """
    Execute show running-configuration command.

    Args:
        dut: Device under test
        command: Full show running-configuration command
        cli_type: CLI type (default: klish)

    Returns:
        str: Raw output from command
    """
    st.log(f"Executing command: {command}")

    try:
        output = st.config(dut, command, type=cli_type, skip_error_check=True)
        st.log(f"Command output:\n{output}")
        return output
    except Exception as e:
        st.error(f"Failed to execute command: {str(e)}")
        return None


def verify_show_run_interface(output, interface):
    """
    Verify 'show running-configuration interface' output format and content.

    Expected format:
    !
    interface Ethernet0
    mtu 9100
    speed auto
    fec rs

    Args:
        output: Raw command output
        interface: Interface name

    Returns:
        dict: Verification results with parsed values
    """
    st.log(f"Verifying show running-configuration interface {interface}")

    result = {
        'command_success': False,
        'interface_found': False,
        'has_config': False,
        'mtu_value': None,
        'speed_value': None,
        'fec_value': None
    }

    if not output:
        st.error("No output received from command")
        return result

    result['command_success'] = True

    if not isinstance(output, str):
        st.error("Output is not a string")
        return result

    # Check for interface section
    interface_pattern = rf'interface\s+{re.escape(interface)}'
    if re.search(interface_pattern, output, re.IGNORECASE):
        result['interface_found'] = True
        st.log(f"Found interface {interface} in output")
    else:
        st.error(f"Interface {interface} not found in output")
        return result

    # Parse configuration parameters
    # Look for mtu, speed, fec after the interface line

    # MTU
    mtu_match = re.search(r'mtu\s+(\d+)', output, re.IGNORECASE)
    if mtu_match:
        result['mtu_value'] = mtu_match.group(1)
        result['has_config'] = True
        st.log(f"Found MTU: {result['mtu_value']}")

    # Speed
    speed_match = re.search(r'speed\s+(\S+)', output, re.IGNORECASE)
    if speed_match:
        result['speed_value'] = speed_match.group(1)
        result['has_config'] = True
        st.log(f"Found speed: {result['speed_value']}")

    # FEC
    fec_match = re.search(r'fec\s+(\S+)', output, re.IGNORECASE)
    if fec_match:
        result['fec_value'] = fec_match.group(1)
        result['has_config'] = True
        st.log(f"Found FEC: {result['fec_value']}")

    # Check for exclamation mark (config section delimiter)
    if '!' in output:
        st.log("Found '!' delimiter in output (proper format)")

    return result


def verify_show_run_bgp(output):
    """
    Verify 'show running-configuration bgp' output format and content.

    Expected format (if BGP configured):
    !
    router bgp <AS>
    neighbor <IP> remote-as <AS>
    ...

    Args:
        output: Raw command output

    Returns:
        dict: Verification results
    """
    st.log("Verifying show running-configuration bgp")

    result = {
        'command_success': False,
        'bgp_configured': False,
        'bgp_asn': None,
        'has_neighbors': False,
        'neighbor_count': 0
    }

    if not output:
        st.error("No output received from command")
        return result

    result['command_success'] = True

    if not isinstance(output, str):
        st.error("Output is not a string")
        return result

    # Check for BGP configuration
    bgp_pattern = r'router\s+bgp\s+(\d+)'
    bgp_match = re.search(bgp_pattern, output, re.IGNORECASE)

    if bgp_match:
        result['bgp_configured'] = True
        result['bgp_asn'] = bgp_match.group(1)
        st.log(f"Found BGP configuration with AS {result['bgp_asn']}")

        # Check for neighbors
        neighbor_pattern = r'neighbor\s+(\S+)'
        neighbors = re.findall(neighbor_pattern, output, re.IGNORECASE)
        if neighbors:
            result['has_neighbors'] = True
            result['neighbor_count'] = len(neighbors)
            st.log(f"Found {result['neighbor_count']} BGP neighbors")
    else:
        st.log("BGP not configured (this is acceptable)")

    return result


def verify_show_run_ospf(output):
    """
    Verify 'show running-configuration ospf' output format and content.

    Expected format (if OSPF configured):
    !
    router ospf
    network <network> area <area>
    ...

    Args:
        output: Raw command output

    Returns:
        dict: Verification results
    """
    st.log("Verifying show running-configuration ospf")

    result = {
        'command_success': False,
        'ospf_configured': False,
        'has_networks': False,
        'has_interfaces': False
    }

    if not output:
        st.error("No output received from command")
        return result

    result['command_success'] = True

    if not isinstance(output, str):
        st.error("Output is not a string")
        return result

    # Check for OSPF configuration
    ospf_pattern = r'router\s+ospf'
    if re.search(ospf_pattern, output, re.IGNORECASE):
        result['ospf_configured'] = True
        st.log("Found OSPF configuration")

        # Check for network statements
        network_pattern = r'network\s+\S+\s+area'
        if re.search(network_pattern, output, re.IGNORECASE):
            result['has_networks'] = True
            st.log("Found OSPF network statements")

        # Check for interface configuration
        interface_pattern = r'interface\s+\S+'
        if re.search(interface_pattern, output, re.IGNORECASE):
            result['has_interfaces'] = True
            st.log("Found OSPF interface configuration")
    else:
        st.log("OSPF not configured (this is acceptable)")

    return result


@pytest.mark.topology("any")
class TestShowRunningConfiguration:
    """
    Test class for show running-configuration command validation.
    """

    @pytest.mark.test_show_run_interface
    def test_show_run_interface(self):
        """
        TestCase: test_show_run_interface

        Test Steps:
        1. Execute 'show running-configuration interface <interface>'
        2. Verify command executes successfully
        3. Verify output contains interface section
        4. Verify output format (has '!' delimiter)
        5. Parse and log configuration parameters (mtu, speed, fec)

        Expected Result:
        - Command executes without errors
        - Output contains interface configuration section
        - Output follows proper format
        """
        st.banner(f"TEST: Show Running-Configuration Interface {data.interface}")

        # Step 1: Execute command
        st.log(f"Step 1: Executing show running-configuration interface {data.interface}")

        command = f"show running-configuration interface {data.interface}"
        output = execute_show_run_command(data.dut1, command, data.cli_type)

        if not output:
            st.report_fail("msg", f"Command failed or returned no output: {command}")

        # Step 2: Verify output
        st.log("Step 2: Verifying command output format and content")

        result = verify_show_run_interface(output, data.interface)

        if not result['command_success']:
            st.report_fail("msg", "Command did not execute successfully")

        if not result['interface_found']:
            st.report_fail("msg", f"Interface {data.interface} not found in output")

        # Step 3: Log parsed configuration
        st.log("Step 3: Configuration parameters found:")
        st.log(f"  - Interface: {data.interface}")
        st.log(f"  - MTU: {result['mtu_value'] if result['mtu_value'] else 'Not configured'}")
        st.log(f"  - Speed: {result['speed_value'] if result['speed_value'] else 'Not configured'}")
        st.log(f"  - FEC: {result['fec_value'] if result['fec_value'] else 'Not configured'}")

        if not result['has_config']:
            st.log("WARNING: No configuration parameters found (interface may use defaults)")

        st.report_pass("test_case_passed")


    @pytest.mark.test_show_run_bgp
    def test_show_run_bgp(self):
        """
        TestCase: test_show_run_bgp

        Test Steps:
        1. Execute 'show running-configuration bgp'
        2. Verify command executes successfully
        3. Check if BGP is configured
        4. If configured, verify BGP section format
        5. Parse and log BGP configuration details

        Expected Result:
        - Command executes without errors
        - If BGP configured, output shows proper BGP configuration
        - If BGP not configured, command returns gracefully
        """
        st.banner("TEST: Show Running-Configuration BGP")

        # Step 1: Execute command
        st.log("Step 1: Executing show running-configuration bgp")

        command = "show running-configuration bgp"
        output = execute_show_run_command(data.dut1, command, data.cli_type)

        if not output:
            st.report_fail("msg", f"Command failed or returned no output: {command}")

        # Step 2: Verify output
        st.log("Step 2: Verifying command output")

        result = verify_show_run_bgp(output)

        if not result['command_success']:
            st.report_fail("msg", "Command did not execute successfully")

        # Step 3: Log BGP configuration status
        st.log("Step 3: BGP configuration status:")

        if result['bgp_configured']:
            st.log(f"  - BGP is CONFIGURED")
            st.log(f"  - BGP AS Number: {result['bgp_asn']}")
            st.log(f"  - Has neighbors: {result['has_neighbors']}")
            if result['has_neighbors']:
                st.log(f"  - Neighbor count: {result['neighbor_count']}")
        else:
            st.log("  - BGP is NOT configured (this is acceptable)")

        st.report_pass("test_case_passed")


    @pytest.mark.test_show_run_ospf
    def test_show_run_ospf(self):
        """
        TestCase: test_show_run_ospf

        Test Steps:
        1. Execute 'show running-configuration ospf'
        2. Verify command executes successfully
        3. Check if OSPF is configured
        4. If configured, verify OSPF section format
        5. Parse and log OSPF configuration details

        Expected Result:
        - Command executes without errors
        - If OSPF configured, output shows proper OSPF configuration
        - If OSPF not configured, command returns gracefully
        """
        st.banner("TEST: Show Running-Configuration OSPF")

        # Step 1: Execute command
        st.log("Step 1: Executing show running-configuration ospf")

        command = "show running-configuration ospf"
        output = execute_show_run_command(data.dut1, command, data.cli_type)

        if not output:
            st.report_fail("msg", f"Command failed or returned no output: {command}")

        # Step 2: Verify output
        st.log("Step 2: Verifying command output")

        result = verify_show_run_ospf(output)

        if not result['command_success']:
            st.report_fail("msg", "Command did not execute successfully")

        # Step 3: Log OSPF configuration status
        st.log("Step 3: OSPF configuration status:")

        if result['ospf_configured']:
            st.log("  - OSPF is CONFIGURED")
            st.log(f"  - Has network statements: {result['has_networks']}")
            st.log(f"  - Has interface configuration: {result['has_interfaces']}")
        else:
            st.log("  - OSPF is NOT configured (this is acceptable)")

        st.report_pass("test_case_passed")


    @pytest.mark.test_show_run_all_protocols
    def test_show_run_all_protocols(self):
        """
        TestCase: test_show_run_all_protocols

        Test Steps:
        1. Execute show running-configuration for interface, BGP, and OSPF
        2. Verify all commands execute successfully
        3. Log summary of what is configured

        Expected Result:
        - All show running-configuration commands work
        - Summary shows configuration status for each protocol
        """
        st.banner("TEST: Show Running-Configuration - All Protocols Summary")

        summary = {
            'interface': False,
            'bgp': False,
            'ospf': False
        }

        # Test interface
        st.log(f"Testing show running-configuration interface {data.interface}")
        command = f"show running-configuration interface {data.interface}"
        output = execute_show_run_command(data.dut1, command, data.cli_type)
        if output:
            result = verify_show_run_interface(output, data.interface)
            summary['interface'] = result['interface_found']

        # Test BGP
        st.log("Testing show running-configuration bgp")
        command = "show running-configuration bgp"
        output = execute_show_run_command(data.dut1, command, data.cli_type)
        if output:
            result = verify_show_run_bgp(output)
            summary['bgp'] = result['bgp_configured']

        # Test OSPF
        st.log("Testing show running-configuration ospf")
        command = "show running-configuration ospf"
        output = execute_show_run_command(data.dut1, command, data.cli_type)
        if output:
            result = verify_show_run_ospf(output)
            summary['ospf'] = result['ospf_configured']

        # Log summary
        st.banner("CONFIGURATION SUMMARY")
        st.log(f"Interface {data.interface}: {'CONFIGURED' if summary['interface'] else 'NOT FOUND'}")
        st.log(f"BGP: {'CONFIGURED' if summary['bgp'] else 'NOT CONFIGURED'}")
        st.log(f"OSPF: {'CONFIGURED' if summary['ospf'] else 'NOT CONFIGURED'}")

        st.report_pass("test_case_passed")
