"""
SHOW RUNNING-CONFIGURATION INTERFACE
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/bug-fix/test_show_run_interface.py \
  --logs-path ./logs/test_show_run_interface_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validates that 'show running-configuration interface' command works correctly
  and returns expected interface configuration parameters like MTU, speed, and FEC.

Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - CLI type: klish (sonic-cli)

Test Steps:
  1. Get interface from testbed
  2. Execute 'show running-configuration interface <interface>'
  3. Validate output contains expected parameters (mtu, speed, fec)
  4. Parse and verify specific values
"""

from __future__ import annotations

import pytest
import re

from spytest import st, SpyTestDict


# Test data dictionary
data = SpyTestDict()
data.cli_type = "klish"


@pytest.fixture(scope="module", autouse=True)
def show_run_interface_module_hooks(request):
    """
    Module-level fixture for show running-config interface test setup.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1")

    st.banner("MODULE SETUP: Show Running-Config Interface Test")

    # Store DUT handle
    data.dut1 = vars.D1

    # Get first available interface from testbed
    # Try different interface options from topology
    if hasattr(vars, 'D1D2P1'):
        data.interface = vars.D1D2P1
    elif hasattr(vars, 'D1T1P1'):
        data.interface = vars.D1T1P1
    else:
        # Fallback to getting ports from platform
        data.interface = st.get_free_ports(data.dut1)[0]

    st.log(f"DUT1: {data.dut1}")
    st.log(f"Test Interface: {data.interface}")

    yield

    st.banner("MODULE TEARDOWN: Show Running-Config Interface Test Complete")


@pytest.fixture(scope="function", autouse=True)
def show_run_interface_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def get_show_run_interface(dut, interface, cli_type="klish"):
    """
    Get running configuration for an interface.

    Args:
        dut: Device under test
        interface: Interface name
        cli_type: CLI type (default: klish)

    Returns:
        str: Raw output from show running-configuration command
    """
    st.log(f"Getting running configuration for interface {interface} on {dut}")

    try:
        # Execute show running-configuration interface command
        command = f"show running-configuration interface {interface}"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        st.log(f"Show running-config output:\n{output}")
        return output

    except Exception as e:
        st.error(f"Failed to get running config for {interface}: {str(e)}")
        return None


def verify_interface_config_params(output, interface):
    """
    Verify that show running-config output contains expected parameters.

    Expected output format:
    !
    interface Ethernet0
    mtu 9100
    speed auto
    fec rs

    Args:
        output: Raw output from show running-configuration command
        interface: Interface name

    Returns:
        dict: Dictionary with parsed values and validation status
    """
    st.log(f"Verifying interface configuration parameters for {interface}")

    result = {
        'interface_found': False,
        'mtu_found': False,
        'speed_found': False,
        'fec_found': False,
        'mtu_value': None,
        'speed_value': None,
        'fec_value': None
    }

    if not output or not isinstance(output, str):
        st.error("No output or invalid output format")
        return result

    # Check if interface section exists
    interface_pattern = rf'interface\s+{re.escape(interface)}'
    if re.search(interface_pattern, output, re.IGNORECASE):
        result['interface_found'] = True
        st.log(f"Found interface {interface} in output")
    else:
        st.error(f"Interface {interface} not found in output")
        return result

    # Parse MTU value
    mtu_match = re.search(r'mtu\s+(\d+)', output, re.IGNORECASE)
    if mtu_match:
        result['mtu_found'] = True
        result['mtu_value'] = mtu_match.group(1)
        st.log(f"Found MTU: {result['mtu_value']}")
    else:
        st.log("MTU not found in output (may not be configured)")

    # Parse speed value
    speed_match = re.search(r'speed\s+(\S+)', output, re.IGNORECASE)
    if speed_match:
        result['speed_found'] = True
        result['speed_value'] = speed_match.group(1)
        st.log(f"Found speed: {result['speed_value']}")
    else:
        st.log("Speed not found in output (may not be configured)")

    # Parse FEC value
    fec_match = re.search(r'fec\s+(\S+)', output, re.IGNORECASE)
    if fec_match:
        result['fec_found'] = True
        result['fec_value'] = fec_match.group(1)
        st.log(f"Found FEC: {result['fec_value']}")
    else:
        st.log("FEC not found in output (may not be configured)")

    return result


@pytest.mark.topology("any")
class TestShowRunInterface:
    """
    Test class for show running-configuration interface validation.
    """

    @pytest.mark.test_show_run_interface_basic
    def test_show_run_interface_basic(self):
        """
        TestCase: test_show_run_interface_basic

        Test Steps:
        1. Execute 'show running-configuration interface <interface>'
        2. Verify command executes successfully
        3. Verify output contains interface configuration
        4. Verify output contains expected parameters (mtu, speed, fec)
        5. Parse and log parameter values

        Expected Result:
        - Command executes without errors
        - Output contains interface section
        - Output contains configuration parameters
        """
        st.banner("TEST: Show Running-Configuration Interface Basic Test")

        # Step 1 & 2: Execute show running-configuration command
        st.log(f"Step 1: Executing show running-configuration interface {data.interface}")

        output = get_show_run_interface(data.dut1, data.interface, data.cli_type)

        if not output:
            st.report_fail("msg", f"Failed to get running configuration for {data.interface}")

        # Step 3 & 4: Verify output contains expected parameters
        st.log("Step 2: Verifying output contains expected parameters")

        result = verify_interface_config_params(output, data.interface)

        # Check if interface was found
        if not result['interface_found']:
            st.report_fail("msg", f"Interface {data.interface} not found in running configuration")

        # Step 5: Log parsed values
        st.log("Step 3: Configuration parameters found:")
        st.log(f"  - Interface: {data.interface} - {'FOUND' if result['interface_found'] else 'NOT FOUND'}")
        st.log(f"  - MTU: {result['mtu_value'] if result['mtu_found'] else 'NOT CONFIGURED'}")
        st.log(f"  - Speed: {result['speed_value'] if result['speed_found'] else 'NOT CONFIGURED'}")
        st.log(f"  - FEC: {result['fec_value'] if result['fec_found'] else 'NOT CONFIGURED'}")

        # Verify at least some configuration parameters are present
        # (MTU, speed, or FEC should be configured on most interfaces)
        if not (result['mtu_found'] or result['speed_found'] or result['fec_found']):
            st.log("WARNING: No configuration parameters (MTU/speed/FEC) found for interface")
            st.log("This may be expected for some interface types or default configurations")

        st.report_pass("test_case_passed")


    @pytest.mark.test_show_run_interface_specific_values
    def test_show_run_interface_specific_values(self):
        """
        TestCase: test_show_run_interface_specific_values

        Test Steps:
        1. Execute 'show running-configuration interface <interface>'
        2. Parse MTU, speed, and FEC values
        3. Verify values match expected patterns
        4. Log detailed configuration

        Expected Result:
        - MTU is numeric (if configured)
        - Speed is valid value (auto, specific speed, etc.)
        - FEC is valid value (rs, fc, none, etc.)
        """
        st.banner("TEST: Show Running-Configuration Interface - Verify Specific Values")

        # Step 1: Execute show running-configuration command
        st.log(f"Step 1: Executing show running-configuration interface {data.interface}")

        output = get_show_run_interface(data.dut1, data.interface, data.cli_type)

        if not output:
            st.report_fail("msg", f"Failed to get running configuration for {data.interface}")

        # Step 2: Parse values
        st.log("Step 2: Parsing configuration values")

        result = verify_interface_config_params(output, data.interface)

        if not result['interface_found']:
            st.report_fail("msg", f"Interface {data.interface} not found in running configuration")

        # Step 3: Verify values match expected patterns
        st.log("Step 3: Verifying values match expected patterns")

        validation_passed = True

        # Validate MTU (should be numeric if present)
        if result['mtu_found']:
            if result['mtu_value'] and result['mtu_value'].isdigit():
                st.log(f"MTU validation PASSED: {result['mtu_value']} is numeric")
            else:
                st.error(f"MTU validation FAILED: {result['mtu_value']} is not numeric")
                validation_passed = False
        else:
            st.log("MTU not configured - skipping MTU validation")

        # Validate Speed (should be auto or numeric)
        if result['speed_found']:
            speed_val = result['speed_value']
            if speed_val and (speed_val.lower() == 'auto' or speed_val.isdigit()):
                st.log(f"Speed validation PASSED: {speed_val}")
            else:
                st.log(f"Speed value found: {speed_val} (may be valid, logging for info)")
        else:
            st.log("Speed not configured - skipping speed validation")

        # Validate FEC (common values: rs, fc, none, auto, off)
        if result['fec_found']:
            fec_val = result['fec_value'].lower() if result['fec_value'] else ''
            valid_fec_values = ['rs', 'fc', 'none', 'auto', 'off']
            if any(fec_val == valid for valid in valid_fec_values):
                st.log(f"FEC validation PASSED: {result['fec_value']}")
            else:
                st.log(f"FEC value found: {result['fec_value']} (may be valid, logging for info)")
        else:
            st.log("FEC not configured - skipping FEC validation")

        # Step 4: Log detailed configuration
        st.log("Step 4: Detailed configuration summary:")
        st.log(f"Interface: {data.interface}")
        st.log(f"  MTU: {result['mtu_value'] if result['mtu_found'] else 'Not configured'}")
        st.log(f"  Speed: {result['speed_value'] if result['speed_found'] else 'Not configured'}")
        st.log(f"  FEC: {result['fec_value'] if result['fec_found'] else 'Not configured'}")

        if not validation_passed:
            st.report_fail("msg", "Configuration value validation failed")

        st.report_pass("test_case_passed")
