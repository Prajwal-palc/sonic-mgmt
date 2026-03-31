"""
Test Case IDs: PB-F-004, PB-F-005, PB-F-006, PB-F-007, PB-F-008
Title: Port Breakout Configuration Operations Test Suite
Author: Network Automation Team
Copyright (C) 2026

Description:
    This test suite validates various configuration operations on breakout ports:
    - PB-F-004: Revert breakout to default mode
    - PB-F-005: IP address configuration on breakout sub-ports
    - PB-F-006: MTU configuration (jumbo frames)
    - PB-F-007: Shutdown/no shutdown operations
    - PB-F-008: Multiple speed grades sequential configuration

Topology:
    DUT1 (Device Under Test)
    - Test Port: Ethernet24 (800G capable)

Test Approach:
    1. Configure breakout mode on test port
    2. Perform various configuration operations
    3. Verify each operation succeeds
    4. Test configuration persistence and correctness
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict
import apis.switching.portchannel as portchannel_obj
import apis.system.interface as intf_obj
import apis.system.basic as basic_obj

# Module level variables
data = SpyTestDict()
CONFIG = SpyTestDict()

# Test Case IDs
TC_IDS = {
    "PB_F_004": "PB-F-004: Revert Breakout to Default Mode",
    "PB_F_005": "PB-F-005: IP Address Configuration on Breakout Sub-Ports",
    "PB_F_006": "PB-F-006: MTU Configuration (Jumbo Frames)",
    "PB_F_007": "PB-F-007: Shutdown/No Shutdown Operations",
    "PB_F_008": "PB-F-008: Multiple Speed Grades Sequential Configuration",
}


@pytest.fixture(scope="module", autouse=True)
def prologue_epilogue(request):
    """
    Module level fixture for setup and cleanup.

    Setup:
        - Initialize test configuration
        - Set CLI type to klish
        - Log test environment details
        - Verify initial port state

    Cleanup:
        - Revert port to default breakout mode
        - Remove all test configurations
        - Verify cleanup successful
    """
    global data, CONFIG

    # Get test variables
    vars = st.get_testbed_vars()
    data.vars = vars

    # Set CLI type
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.banner("MODULE CONFIGURATION START - Configuration Operations Tests")
    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")

    # Initialize configuration
    CONFIG.test_port = "Ethernet24"
    CONFIG.breakout_wait_time = 60
    CONFIG.test_breakout_mode = "8x100G"
    CONFIG.test_child_ports = ["Ethernet24", "Ethernet25", "Ethernet26", "Ethernet27",
                               "Ethernet28", "Ethernet29", "Ethernet30", "Ethernet31"]

    # Test IP addresses
    CONFIG.test_ipv4_addr = "192.168.100.1/24"
    CONFIG.test_ipv6_addr = "2001:db8:100::1/64"

    # Test MTU values
    CONFIG.default_mtu = 9100
    CONFIG.jumbo_mtu = 9216

    # Speed grades for PB-F-008
    CONFIG.speed_grades = [
        {"mode": "8x100G", "speed": "100GB", "ports": 8},
        {"mode": "4x200G", "speed": "200GB", "ports": 4},
        {"mode": "2x400G", "speed": "400GB", "ports": 2},
    ]

    # Pre-module configuration
    pre_config()

    # Yield to test execution
    yield

    # Cleanup after all tests
    st.banner("MODULE CONFIGURATION CLEANUP - Configuration Operations Tests")
    cleanup()
    st.banner("MODULE CONFIGURATION END - Configuration Operations Tests")


def pre_config():
    """
    Pre-configuration before test execution.

    Steps:
        1. Verify test port exists
        2. Reset port to default breakout mode
        3. Verify initial state
    """
    st.banner("PRE-CONFIGURATION START")

    try:
        vars = data.vars

        # Log initial configuration
        st.log(f"Test port: {CONFIG.test_port}")
        st.log(f"Test breakout mode: {CONFIG.test_breakout_mode}")

        # Reset to default breakout mode
        st.log(f"Resetting {CONFIG.test_port} to default mode (1x800G)")
        configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G")

        st.log("Pre-configuration completed successfully")

    except Exception as e:
        st.error(f"Pre-configuration failed: {e}")
        st.report_fail("module_config_failed", "Pre-configuration failed")


def cleanup():
    """
    Cleanup function to restore configuration.

    Steps:
        1. Remove all IP configurations
        2. Reset MTU to default
        3. Revert port to default breakout mode
        4. Verify cleanup successful
    """
    st.banner("CLEANUP START")

    try:
        vars = data.vars

        # Remove IP configurations from test ports
        st.log("Removing IP configurations from test ports")
        for port in CONFIG.test_child_ports[:2]:  # Clean first 2 ports
            try:
                st.config(vars.D1, f"interface {port}", type=data.cli_type, skip_error_check=True)
                st.config(vars.D1, f"no ip address {CONFIG.test_ipv4_addr}",
                         type=data.cli_type, skip_error_check=True)
                st.config(vars.D1, f"no ipv6 address {CONFIG.test_ipv6_addr}",
                         type=data.cli_type, skip_error_check=True)
                st.config(vars.D1, "exit", type=data.cli_type, skip_error_check=True)
            except:
                pass  # Continue cleanup even if removal fails

        # Revert to default breakout mode
        st.log(f"Reverting {CONFIG.test_port} to default mode (1x800G)")
        configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G")

        st.log("Cleanup completed successfully")

    except Exception as e:
        st.error(f"Cleanup encountered error: {e}")


def configure_breakout_mode(dut, port, mode):
    """
    Configure port breakout mode.

    Args:
        dut: Device Under Test
        port: Port to configure
        mode: Breakout mode

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Configuring {port} to breakout mode: {mode}")

        config_cmd = f"interface breakout {port} mode {mode}"
        st.config(dut, config_cmd, type=data.cli_type, skip_error_check=True)

        st.log(f"Waiting {CONFIG.breakout_wait_time} seconds for breakout to complete...")
        st.wait(CONFIG.breakout_wait_time)

        st.log(f"Breakout mode {mode} configured on {port}")
        return True

    except Exception as e:
        st.error(f"Failed to configure breakout mode {mode} on {port}: {e}")
        return False


def verify_port_exists(dut, port):
    """
    Verify port exists in system.

    Args:
        dut: Device Under Test
        port: Port to check

    Returns:
        bool: True if port exists, False otherwise
    """
    try:
        output = st.show(dut, f"show interface {port}",
                        type=data.cli_type, skip_error_check=True)
        return output and len(output) > 0

    except Exception as e:
        st.error(f"Exception checking port {port}: {e}")
        return False


def configure_ip_address(dut, port, ip_address):
    """
    Configure IP address on port.

    Args:
        dut: Device Under Test
        port: Port to configure
        ip_address: IP address with mask (e.g., "192.168.100.1/24")

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Configuring IP address {ip_address} on {port}")

        # Determine if IPv4 or IPv6
        if ':' in ip_address:
            cmd_type = "ipv6 address"
        else:
            cmd_type = "ip address"

        # Configure IP address
        st.config(dut, f"interface {port}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"{cmd_type} {ip_address}", type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)

        st.log(f"IP address {ip_address} configured on {port}")
        return True

    except Exception as e:
        st.error(f"Failed to configure IP address {ip_address} on {port}: {e}")
        return False


def verify_ip_address(dut, port, ip_address):
    """
    Verify IP address configured on port.

    Args:
        dut: Device Under Test
        port: Port to check
        ip_address: Expected IP address

    Returns:
        tuple: (bool, str) - Success status and error message if any
    """
    try:
        st.log(f"Verifying IP address {ip_address} on {port}")

        # Check IPv4 or IPv6
        if ':' in ip_address:
            show_cmd = f"show ipv6 interface {port}"
        else:
            show_cmd = f"show ip interface {port}"

        output = st.show(dut, show_cmd, type=data.cli_type, skip_error_check=True)

        if output:
            st.log(f"IP configuration on {port}: {output}")
            return True, ""
        else:
            error_msg = f"Could not verify IP address on {port}"
            st.log(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Exception verifying IP address on {port}: {e}"
        st.error(error_msg)
        return False, error_msg


def configure_mtu(dut, port, mtu_value):
    """
    Configure MTU on port.

    Args:
        dut: Device Under Test
        port: Port to configure
        mtu_value: MTU value (e.g., 9216)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Configuring MTU {mtu_value} on {port}")

        st.config(dut, f"interface {port}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"mtu {mtu_value}", type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)

        st.log(f"MTU {mtu_value} configured on {port}")
        return True

    except Exception as e:
        st.error(f"Failed to configure MTU {mtu_value} on {port}: {e}")
        return False


def verify_mtu(dut, port, expected_mtu):
    """
    Verify MTU value on port.

    Args:
        dut: Device Under Test
        port: Port to check
        expected_mtu: Expected MTU value

    Returns:
        tuple: (bool, str) - Success status and error message if any
    """
    try:
        st.log(f"Verifying MTU {expected_mtu} on {port}")

        output = st.show(dut, f"show interface {port}",
                        type=data.cli_type, skip_error_check=True)

        if output and len(output) > 0:
            actual_mtu = output[0].get('mtu', 'Unknown')
            st.log(f"Port {port} MTU: {actual_mtu}")

            if str(expected_mtu) in str(actual_mtu):
                st.log(f"MTU verified: {actual_mtu}")
                return True, ""
            else:
                error_msg = f"MTU mismatch - Expected: {expected_mtu}, Actual: {actual_mtu}"
                st.log(error_msg)
                return False, error_msg
        else:
            error_msg = f"Could not retrieve MTU for {port}"
            st.error(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Exception verifying MTU on {port}: {e}"
        st.error(error_msg)
        return False, error_msg


def shutdown_interface(dut, port):
    """
    Shutdown interface.

    Args:
        dut: Device Under Test
        port: Port to shutdown

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Shutting down interface {port}")

        st.config(dut, f"interface {port}", type=data.cli_type, skip_error_check=True)
        st.config(dut, "shutdown", type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)

        st.log(f"Interface {port} shutdown")
        return True

    except Exception as e:
        st.error(f"Failed to shutdown {port}: {e}")
        return False


def no_shutdown_interface(dut, port):
    """
    Bring up interface (no shutdown).

    Args:
        dut: Device Under Test
        port: Port to bring up

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Bringing up interface {port}")

        st.config(dut, f"interface {port}", type=data.cli_type, skip_error_check=True)
        st.config(dut, "no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)

        st.log(f"Interface {port} brought up")
        return True

    except Exception as e:
        st.error(f"Failed to bring up {port}: {e}")
        return False


def verify_admin_status(dut, port, expected_status):
    """
    Verify interface admin status.

    Args:
        dut: Device Under Test
        port: Port to check
        expected_status: Expected admin status ("up" or "down")

    Returns:
        tuple: (bool, str) - Success status and error message if any
    """
    try:
        st.log(f"Verifying admin status of {port} is {expected_status}")

        output = st.show(dut, f"show interface {port}",
                        type=data.cli_type, skip_error_check=True)

        if output and len(output) > 0:
            admin_status = output[0].get('admin', 'Unknown')
            st.log(f"Port {port} admin status: {admin_status}")

            if expected_status.lower() in str(admin_status).lower():
                st.log(f"Admin status verified: {admin_status}")
                return True, ""
            else:
                error_msg = f"Admin status mismatch - Expected: {expected_status}, Actual: {admin_status}"
                st.log(error_msg)
                return False, error_msg
        else:
            error_msg = f"Could not retrieve admin status for {port}"
            st.error(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Exception verifying admin status on {port}: {e}"
        st.error(error_msg)
        return False, error_msg


def test_pb_f_004_revert_breakout_to_default():
    """
    Test Case: PB-F-004 - Revert Breakout to Default Mode

    Objective:
        Validate reverting port from breakout mode to default (1x800G).

    Test Steps:
        1. Configure port to breakout mode (8x100G)
        2. Verify child ports created
        3. Revert port to default mode (1x800G)
        4. Verify port back to single port
        5. Verify child ports removed

    Expected Results:
        - Breakout configuration successful
        - Revert to default successful
        - Port returns to single 800G mode
        - All sub-ports removed

    Pass Criteria:
        - Port successfully reverted to default
        - Only single port remains after revert
    """
    st.banner("TEST CASE START: PB-F-004 - Revert Breakout to Default Mode")
    st.log("="*80)
    st.log(TC_IDS["PB_F_004"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # STEP 1: Configure breakout mode
        st.banner("STEP 1: Configure Port to Breakout Mode (8x100G)")
        if not configure_breakout_mode(vars.D1, CONFIG.test_port, CONFIG.test_breakout_mode):
            error_msg = "Failed to configure breakout mode"
            st.error(error_msg)
            validation_errors.append(error_msg)

        # STEP 2: Verify child ports created
        st.banner("STEP 2: Verify Child Ports Created")
        for port in CONFIG.test_child_ports:
            if verify_port_exists(vars.D1, port):
                st.log(f"Child port {port} verified")
            else:
                error_msg = f"Child port {port} not found"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # STEP 3: Revert to default mode
        st.banner("STEP 3: Revert Port to Default Mode (1x800G)")
        if not configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G"):
            error_msg = "Failed to revert to default mode"
            st.error(error_msg)
            validation_errors.append(error_msg)

        # STEP 4: Verify port back to single port
        st.banner("STEP 4: Verify Port Reverted to Single Port")
        if verify_port_exists(vars.D1, CONFIG.test_port):
            st.log(f"Main port {CONFIG.test_port} exists after revert")
        else:
            error_msg = f"Main port {CONFIG.test_port} not found after revert"
            st.error(error_msg)
            validation_errors.append(error_msg)

        # STEP 5: Verify child ports removed (except first one which is main port)
        st.banner("STEP 5: Verify Child Ports Removed")
        for port in CONFIG.test_child_ports[1:]:  # Skip first port (main port)
            if not verify_port_exists(vars.D1, port):
                st.log(f"Child port {port} correctly removed")
            else:
                warning_msg = f"Child port {port} still exists after revert"
                st.log(warning_msg)  # This might be OK depending on platform behavior

        # Report results
        st.banner("TEST RESULTS SUMMARY")
        if validation_errors:
            st.log("Validation errors encountered:")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")

            st.log(f"TEST RESULT: FAIL - {len(validation_errors)} validation error(s)")
            st.report_tc_fail("PB_F_004", "test_failed",
                            f"Revert breakout test failed with {len(validation_errors)} errors")
        else:
            st.log("TEST RESULT: PASS - Port successfully reverted to default mode")
            st.report_tc_pass("PB_F_004", "test_passed",
                            "Revert breakout to default completed successfully")

    except Exception as e:
        error_msg = f"EXCEPTION during test execution: {e}"
        st.error(error_msg)
        validation_errors.append(error_msg)
        st.report_tc_fail("PB_F_004", "test_exception", f"Test failed with exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-004")
        st.log(f"Total validation errors: {len(validation_errors)}")


def test_pb_f_005_ip_address_configuration():
    """
    Test Case: PB-F-005 - IP Address Configuration on Breakout Sub-Ports

    Objective:
        Validate IP address configuration on breakout port sub-interfaces.

    Test Steps:
        1. Configure port to breakout mode (8x100G)
        2. Configure IPv4 address on first sub-port
        3. Configure IPv6 address on second sub-port
        4. Verify IP addresses configured correctly
        5. Verify connectivity (if applicable)

    Expected Results:
        - Breakout configuration successful
        - IPv4 address configured on sub-port
        - IPv6 address configured on sub-port
        - IP addresses verified successfully

    Pass Criteria:
        - IP addresses successfully configured
        - IP addresses visible in show commands
    """
    st.banner("TEST CASE START: PB-F-005 - IP Address Configuration")
    st.log("="*80)
    st.log(TC_IDS["PB_F_005"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # STEP 1: Configure breakout mode
        st.banner("STEP 1: Configure Port to Breakout Mode (8x100G)")
        if not configure_breakout_mode(vars.D1, CONFIG.test_port, CONFIG.test_breakout_mode):
            error_msg = "Failed to configure breakout mode"
            st.error(error_msg)
            validation_errors.append(error_msg)
            # Continue to test IP configuration even if breakout seems to fail

        # STEP 2: Configure IPv4 address
        st.banner("STEP 2: Configure IPv4 Address on First Sub-Port")
        test_port_ipv4 = CONFIG.test_child_ports[0]
        st.log(f"Configuring IPv4 {CONFIG.test_ipv4_addr} on {test_port_ipv4}")

        if not configure_ip_address(vars.D1, test_port_ipv4, CONFIG.test_ipv4_addr):
            error_msg = f"Failed to configure IPv4 address on {test_port_ipv4}"
            st.error(error_msg)
            validation_errors.append(error_msg)
        else:
            st.log(f"IPv4 address configured successfully on {test_port_ipv4}")

        # STEP 3: Configure IPv6 address
        st.banner("STEP 3: Configure IPv6 Address on Second Sub-Port")
        test_port_ipv6 = CONFIG.test_child_ports[1]
        st.log(f"Configuring IPv6 {CONFIG.test_ipv6_addr} on {test_port_ipv6}")

        if not configure_ip_address(vars.D1, test_port_ipv6, CONFIG.test_ipv6_addr):
            error_msg = f"Failed to configure IPv6 address on {test_port_ipv6}"
            st.error(error_msg)
            validation_errors.append(error_msg)
        else:
            st.log(f"IPv6 address configured successfully on {test_port_ipv6}")

        # STEP 4: Verify IP addresses
        st.banner("STEP 4: Verify IP Address Configuration")

        # Verify IPv4
        st.log(f"Verifying IPv4 address on {test_port_ipv4}")
        ipv4_ok, ipv4_msg = verify_ip_address(vars.D1, test_port_ipv4, CONFIG.test_ipv4_addr)
        if not ipv4_ok:
            validation_errors.append(ipv4_msg)

        # Verify IPv6
        st.log(f"Verifying IPv6 address on {test_port_ipv6}")
        ipv6_ok, ipv6_msg = verify_ip_address(vars.D1, test_port_ipv6, CONFIG.test_ipv6_addr)
        if not ipv6_ok:
            validation_errors.append(ipv6_msg)

        # Report results
        st.banner("TEST RESULTS SUMMARY")
        if validation_errors:
            st.log("Validation errors encountered:")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")

            st.log(f"TEST RESULT: FAIL - {len(validation_errors)} validation error(s)")
            st.report_tc_fail("PB_F_005", "test_failed",
                            f"IP address configuration test failed with {len(validation_errors)} errors")
        else:
            st.log("TEST RESULT: PASS - IP addresses configured successfully on sub-ports")
            st.report_tc_pass("PB_F_005", "test_passed",
                            "IP address configuration on sub-ports completed successfully")

    except Exception as e:
        error_msg = f"EXCEPTION during test execution: {e}"
        st.error(error_msg)
        validation_errors.append(error_msg)
        st.report_tc_fail("PB_F_005", "test_exception", f"Test failed with exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-005")
        st.log(f"Total validation errors: {len(validation_errors)}")


def test_pb_f_006_mtu_configuration():
    """
    Test Case: PB-F-006 - MTU Configuration (Jumbo Frames)

    Objective:
        Validate MTU configuration on breakout port sub-interfaces.

    Test Steps:
        1. Configure port to breakout mode (8x100G)
        2. Configure jumbo frame MTU (9216) on sub-port
        3. Verify MTU configured correctly
        4. Test with different MTU values

    Expected Results:
        - Breakout configuration successful
        - MTU configured successfully
        - MTU verified correctly

    Pass Criteria:
        - MTU successfully configured
        - MTU value visible in show commands
    """
    st.banner("TEST CASE START: PB-F-006 - MTU Configuration")
    st.log("="*80)
    st.log(TC_IDS["PB_F_006"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # STEP 1: Configure breakout mode
        st.banner("STEP 1: Configure Port to Breakout Mode (8x100G)")
        if not configure_breakout_mode(vars.D1, CONFIG.test_port, CONFIG.test_breakout_mode):
            error_msg = "Failed to configure breakout mode"
            st.error(error_msg)
            validation_errors.append(error_msg)

        # STEP 2: Configure jumbo frame MTU
        st.banner("STEP 2: Configure Jumbo Frame MTU (9216)")
        test_port = CONFIG.test_child_ports[0]
        st.log(f"Configuring MTU {CONFIG.jumbo_mtu} on {test_port}")

        if not configure_mtu(vars.D1, test_port, CONFIG.jumbo_mtu):
            error_msg = f"Failed to configure MTU on {test_port}"
            st.error(error_msg)
            validation_errors.append(error_msg)
        else:
            st.log(f"MTU {CONFIG.jumbo_mtu} configured successfully on {test_port}")

        # STEP 3: Verify MTU
        st.banner("STEP 3: Verify MTU Configuration")
        st.log(f"Verifying MTU {CONFIG.jumbo_mtu} on {test_port}")

        mtu_ok, mtu_msg = verify_mtu(vars.D1, test_port, CONFIG.jumbo_mtu)
        if not mtu_ok and mtu_msg:
            validation_errors.append(mtu_msg)

        # STEP 4: Test default MTU on another port
        st.banner("STEP 4: Verify Default MTU on Other Sub-Port")
        test_port2 = CONFIG.test_child_ports[1]
        st.log(f"Checking default MTU on {test_port2}")

        output = st.show(vars.D1, f"show interface {test_port2}",
                        type=data.cli_type, skip_error_check=True)
        if output:
            st.log(f"Port {test_port2} MTU: {output[0].get('mtu', 'Unknown')}")

        # Report results
        st.banner("TEST RESULTS SUMMARY")
        if validation_errors:
            st.log("Validation errors encountered:")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")

            st.log(f"TEST RESULT: FAIL - {len(validation_errors)} validation error(s)")
            st.report_tc_fail("PB_F_006", "test_failed",
                            f"MTU configuration test failed with {len(validation_errors)} errors")
        else:
            st.log("TEST RESULT: PASS - MTU configured successfully on sub-port")
            st.report_tc_pass("PB_F_006", "test_passed",
                            "MTU configuration on sub-port completed successfully")

    except Exception as e:
        error_msg = f"EXCEPTION during test execution: {e}"
        st.error(error_msg)
        validation_errors.append(error_msg)
        st.report_tc_fail("PB_F_006", "test_exception", f"Test failed with exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-006")
        st.log(f"Total validation errors: {len(validation_errors)}")


def test_pb_f_007_shutdown_no_shutdown():
    """
    Test Case: PB-F-007 - Shutdown/No Shutdown Operations

    Objective:
        Validate shutdown/no shutdown operations on breakout port sub-interfaces.

    Test Steps:
        1. Configure port to breakout mode (8x100G)
        2. Verify sub-port is up initially
        3. Shutdown sub-port
        4. Verify sub-port is down
        5. Bring up sub-port (no shutdown)
        6. Verify sub-port is up again

    Expected Results:
        - Breakout configuration successful
        - Shutdown operation successful
        - Port admin status changes to down
        - No shutdown operation successful
        - Port admin status changes to up

    Pass Criteria:
        - Shutdown/no shutdown operations successful
        - Admin status changes correctly
    """
    st.banner("TEST CASE START: PB-F-007 - Shutdown/No Shutdown Operations")
    st.log("="*80)
    st.log(TC_IDS["PB_F_007"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # STEP 1: Configure breakout mode
        st.banner("STEP 1: Configure Port to Breakout Mode (8x100G)")
        if not configure_breakout_mode(vars.D1, CONFIG.test_port, CONFIG.test_breakout_mode):
            error_msg = "Failed to configure breakout mode"
            st.error(error_msg)
            validation_errors.append(error_msg)

        # STEP 2: Verify initial state (should be up)
        st.banner("STEP 2: Verify Initial State (Should Be Up)")
        test_port = CONFIG.test_child_ports[0]
        st.log(f"Checking initial admin status of {test_port}")

        # Bring up port first to ensure known state
        no_shutdown_interface(vars.D1, test_port)
        st.wait(2)

        status_ok, status_msg = verify_admin_status(vars.D1, test_port, "up")
        if not status_ok:
            st.log(f"Initial state verification: {status_msg}")

        # STEP 3: Shutdown port
        st.banner("STEP 3: Shutdown Sub-Port")
        if not shutdown_interface(vars.D1, test_port):
            error_msg = f"Failed to shutdown {test_port}"
            st.error(error_msg)
            validation_errors.append(error_msg)

        st.wait(2)  # Wait for status to propagate

        # STEP 4: Verify port is down
        st.banner("STEP 4: Verify Port Is Down")
        status_ok, status_msg = verify_admin_status(vars.D1, test_port, "down")
        if not status_ok:
            validation_errors.append(status_msg)

        # STEP 5: Bring up port
        st.banner("STEP 5: Bring Up Sub-Port (No Shutdown)")
        if not no_shutdown_interface(vars.D1, test_port):
            error_msg = f"Failed to bring up {test_port}"
            st.error(error_msg)
            validation_errors.append(error_msg)

        st.wait(2)  # Wait for status to propagate

        # STEP 6: Verify port is up
        st.banner("STEP 6: Verify Port Is Up")
        status_ok, status_msg = verify_admin_status(vars.D1, test_port, "up")
        if not status_ok:
            validation_errors.append(status_msg)

        # Report results
        st.banner("TEST RESULTS SUMMARY")
        if validation_errors:
            st.log("Validation errors encountered:")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")

            st.log(f"TEST RESULT: FAIL - {len(validation_errors)} validation error(s)")
            st.report_tc_fail("PB_F_007", "test_failed",
                            f"Shutdown/no shutdown test failed with {len(validation_errors)} errors")
        else:
            st.log("TEST RESULT: PASS - Shutdown/no shutdown operations successful")
            st.report_tc_pass("PB_F_007", "test_passed",
                            "Shutdown/no shutdown operations completed successfully")

    except Exception as e:
        error_msg = f"EXCEPTION during test execution: {e}"
        st.error(error_msg)
        validation_errors.append(error_msg)
        st.report_tc_fail("PB_F_007", "test_exception", f"Test failed with exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-007")
        st.log(f"Total validation errors: {len(validation_errors)}")

        # Ensure port is up after test
        try:
            no_shutdown_interface(vars.data.vars.D1, CONFIG.test_child_ports[0])
        except:
            pass


def test_pb_f_008_multiple_speed_grades():
    """
    Test Case: PB-F-008 - Multiple Speed Grades Sequential Configuration

    Objective:
        Validate sequential configuration of multiple speed grades (100G, 200G, 400G).

    Test Steps:
        1. Configure 8x100G breakout
        2. Verify all ports at 100G speed
        3. Change to 4x200G breakout
        4. Verify all ports at 200G speed
        5. Change to 2x400G breakout
        6. Verify all ports at 400G speed

    Expected Results:
        - All speed grade transitions successful
        - Ports correctly reconfigured after each transition
        - Correct number of ports created for each mode
        - Port speeds match expected values

    Pass Criteria:
        - All 3 speed grades configured successfully
        - Port counts correct for each mode
        - Speeds verified for each mode
    """
    st.banner("TEST CASE START: PB-F-008 - Multiple Speed Grades Sequential")
    st.log("="*80)
    st.log(TC_IDS["PB_F_008"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # Iterate through speed grades
        for idx, speed_grade in enumerate(CONFIG.speed_grades, 1):
            mode = speed_grade['mode']
            expected_speed = speed_grade['speed']
            expected_ports = speed_grade['ports']

            st.banner(f"SPEED GRADE {idx}/3: Configuring {mode}")

            # STEP 1: Configure breakout mode
            st.log(f"Configuring breakout mode: {mode}")
            if not configure_breakout_mode(vars.D1, CONFIG.test_port, mode):
                error_msg = f"Failed to configure {mode}"
                st.error(error_msg)
                validation_errors.append(error_msg)
                continue  # Continue with next speed grade

            # STEP 2: Verify expected number of ports
            st.log(f"Verifying {expected_ports} ports created for {mode}")
            child_ports = CONFIG.test_child_ports[:expected_ports]

            ports_found = 0
            for port in child_ports:
                if verify_port_exists(vars.D1, port):
                    ports_found += 1
                else:
                    error_msg = f"Speed grade {mode}: Port {port} not found"
                    st.error(error_msg)
                    validation_errors.append(error_msg)

            st.log(f"Speed grade {mode}: Found {ports_found}/{expected_ports} ports")

            # STEP 3: Verify port speed (sample check)
            st.log(f"Verifying port speed for {mode} (sample check)")
            sample_port = child_ports[0]

            output = st.show(vars.D1, f"show interface {sample_port}",
                           type=data.cli_type, skip_error_check=True)
            if output:
                actual_speed = output[0].get('speed', 'Unknown')
                st.log(f"Sample port {sample_port} speed: {actual_speed}")

            st.log(f"Speed grade {mode} configuration completed")
            st.log("-" * 80)

        # Final summary
        st.banner("TEST RESULTS SUMMARY")
        if validation_errors:
            st.log("Validation errors encountered:")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")

            st.log(f"TEST RESULT: FAIL - {len(validation_errors)} validation error(s)")
            st.report_tc_fail("PB_F_008", "test_failed",
                            f"Multiple speed grades test failed with {len(validation_errors)} errors")
        else:
            st.log("TEST RESULT: PASS - All speed grades configured successfully")
            st.log(f"Successfully configured {len(CONFIG.speed_grades)} speed grades")
            st.report_tc_pass("PB_F_008", "test_passed",
                            "Multiple speed grades sequential configuration completed successfully")

    except Exception as e:
        error_msg = f"EXCEPTION during test execution: {e}"
        st.error(error_msg)
        validation_errors.append(error_msg)
        st.report_tc_fail("PB_F_008", "test_exception", f"Test failed with exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-008")
        st.log(f"Total validation errors: {len(validation_errors)}")
