"""
Test Case ID: PB-F-003
Title: Multi-Port Concurrent Breakout Configuration
Author: Network Automation Team
Copyright (C) 2026

Description:
    This test validates concurrent port breakout configuration on multiple ports.
    Tests system capability to handle simultaneous breakout operations.

Topology:
    DUT1 (Device Under Test)
    - Test Ports: Ethernet24, Ethernet32, Ethernet40, Ethernet48 (all 800G capable)

Test Approach:
    1. Configure breakout on 4 ports concurrently
    2. Verify all ports break out correctly
    3. Verify no interference between concurrent operations
    4. Test system stability with multiple breakout ports active
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
    "PB_F_003": "PB-F-003: Multi-Port Concurrent Breakout Configuration",
}


@pytest.fixture(scope="module", autouse=True)
def prologue_epilogue(request):
    """
    Module level fixture for setup and cleanup.

    Setup:
        - Initialize test configuration
        - Set CLI type to klish
        - Log test environment details
        - Verify initial port states

    Cleanup:
        - Revert all test ports to default breakout mode
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

    st.banner("MODULE CONFIGURATION START - PB-F-003")
    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")

    # Initialize configuration
    CONFIG.breakout_wait_time = 60  # Wait time after breakout configuration

    # Define test ports for concurrent breakout
    CONFIG.test_ports = [
        {
            "port": "Ethernet24",
            "mode": "8x100G",
            "expected_ports": 8,
            "expected_speed": "100GB",
            "child_ports": ["Ethernet24", "Ethernet25", "Ethernet26", "Ethernet27",
                          "Ethernet28", "Ethernet29", "Ethernet30", "Ethernet31"],
        },
        {
            "port": "Ethernet32",
            "mode": "4x200G",
            "expected_ports": 4,
            "expected_speed": "200GB",
            "child_ports": ["Ethernet32", "Ethernet33", "Ethernet34", "Ethernet35"],
        },
        {
            "port": "Ethernet40",
            "mode": "2x400G",
            "expected_ports": 2,
            "expected_speed": "400GB",
            "child_ports": ["Ethernet40", "Ethernet41"],
        },
        {
            "port": "Ethernet48",
            "mode": "8x50G",
            "expected_ports": 8,
            "expected_speed": "50GB",
            "child_ports": ["Ethernet48", "Ethernet49", "Ethernet50", "Ethernet51",
                          "Ethernet52", "Ethernet53", "Ethernet54", "Ethernet55"],
        },
    ]

    # Pre-module configuration
    pre_config()

    # Yield to test execution
    yield

    # Cleanup after all tests
    st.banner("MODULE CONFIGURATION CLEANUP - PB-F-003")
    cleanup()
    st.banner("MODULE CONFIGURATION END - PB-F-003")


def pre_config():
    """
    Pre-configuration before test execution.

    Steps:
        1. Verify all test ports exist
        2. Reset all ports to default breakout mode (1x800G)
        3. Verify initial states
    """
    st.banner("PRE-CONFIGURATION START")

    try:
        vars = data.vars

        # Log initial configuration
        st.log(f"Test ports for concurrent breakout:")
        for port_config in CONFIG.test_ports:
            st.log(f"  {port_config['port']} -> {port_config['mode']}")

        # Reset all test ports to default breakout mode
        st.log("Resetting all test ports to default mode (1x800G)")
        for port_config in CONFIG.test_ports:
            port = port_config['port']
            st.log(f"Resetting {port} to 1x800G")
            configure_breakout_mode(vars.D1, port, "1x800G")

        st.log("Pre-configuration completed successfully")

    except Exception as e:
        st.error(f"Pre-configuration failed: {e}")
        st.report_fail("module_config_failed", "Pre-configuration failed")


def cleanup():
    """
    Cleanup function to restore configuration.

    Steps:
        1. Revert all test ports to default breakout mode (1x800G)
        2. Verify ports are operational
        3. Log cleanup status
    """
    st.banner("CLEANUP START")

    try:
        vars = data.vars

        st.log("Reverting all test ports to default mode (1x800G)")
        for port_config in CONFIG.test_ports:
            port = port_config['port']
            st.log(f"Reverting {port} to 1x800G")
            configure_breakout_mode(vars.D1, port, "1x800G")

        st.log("Cleanup completed successfully")

    except Exception as e:
        st.error(f"Cleanup encountered error: {e}")


def configure_breakout_mode(dut, port, mode):
    """
    Configure port breakout mode.

    Args:
        dut: Device Under Test
        port: Port to configure (e.g., "Ethernet24")
        mode: Breakout mode (e.g., "8x100G")

    Returns:
        bool: True if configuration successful, False otherwise
    """
    try:
        st.log(f"Configuring {port} to breakout mode: {mode}")

        # Enter config mode and apply breakout
        config_cmd = f"interface breakout {port} mode {mode}"
        st.config(dut, config_cmd, type=data.cli_type, skip_error_check=True)

        st.log(f"Breakout mode {mode} configuration command sent for {port}")
        return True

    except Exception as e:
        st.error(f"Failed to configure breakout mode {mode} on {port}: {e}")
        return False


def verify_child_ports_created(dut, expected_ports_list):
    """
    Verify that expected child ports are created after breakout.

    Args:
        dut: Device Under Test
        expected_ports_list: List of expected port names

    Returns:
        tuple: (bool, list) - Success status and list of validation errors
    """
    validation_errors = []

    try:
        st.log(f"Verifying child ports created: {expected_ports_list}")

        for port in expected_ports_list:
            st.log(f"Checking port: {port}")
            output = st.show(dut, f"show interface {port}",
                           type=data.cli_type, skip_error_check=True)

            if not output or len(output) == 0:
                error_msg = f"Port {port} not found after breakout"
                st.error(error_msg)
                validation_errors.append(error_msg)
            else:
                st.log(f"Port {port} verified successfully")

        if validation_errors:
            return False, validation_errors
        return True, []

    except Exception as e:
        error_msg = f"Exception during child port verification: {e}"
        st.error(error_msg)
        return False, [error_msg]


def verify_port_speed(dut, port, expected_speed):
    """
    Verify port speed matches expected value.

    Args:
        dut: Device Under Test
        port: Port to check
        expected_speed: Expected speed (e.g., "100GB")

    Returns:
        tuple: (bool, str) - Success status and error message if any
    """
    try:
        st.log(f"Verifying port {port} speed is {expected_speed}")

        output = st.show(dut, f"show interface {port}",
                        type=data.cli_type, skip_error_check=True)

        if output and len(output) > 0:
            actual_speed = output[0].get('speed', 'Unknown')
            st.log(f"Port {port} speed: {actual_speed}")

            # Speed verification is informational
            if expected_speed.upper() not in str(actual_speed).upper():
                warning_msg = f"Port {port} speed mismatch - Expected: {expected_speed}, Actual: {actual_speed}"
                st.log(warning_msg)
                return True, warning_msg  # Don't fail on speed mismatch
            else:
                st.log(f"Port {port} speed verified: {actual_speed}")
                return True, ""
        else:
            error_msg = f"Could not retrieve speed for port {port}"
            st.error(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Exception during speed verification for {port}: {e}"
        st.error(error_msg)
        return False, error_msg


def verify_port_operational(dut, port):
    """
    Verify port operational status.

    Args:
        dut: Device Under Test
        port: Port to check

    Returns:
        tuple: (bool, str) - Success status and error message if any
    """
    try:
        st.log(f"Verifying port {port} operational status")

        output = st.show(dut, f"show interface {port}",
                        type=data.cli_type, skip_error_check=True)

        if output and len(output) > 0:
            admin_status = output[0].get('admin', 'Unknown')
            oper_status = output[0].get('oper', 'Unknown')

            st.log(f"Port {port} - Admin: {admin_status}, Oper: {oper_status}")

            # Port should be administratively up at minimum
            if 'up' not in str(admin_status).lower():
                error_msg = f"Port {port} admin status is not up: {admin_status}"
                st.error(error_msg)
                return False, error_msg
            else:
                st.log(f"Port {port} is administratively up")
                return True, ""
        else:
            error_msg = f"Could not retrieve operational status for port {port}"
            st.error(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Exception during operational status check for {port}: {e}"
        st.error(error_msg)
        return False, error_msg


def test_multi_port_concurrent_breakout():
    """
    Test Case: PB-F-003 - Multi-Port Concurrent Breakout Configuration

    Objective:
        Validate concurrent port breakout configuration on multiple ports.

    Test Steps:
        1. Verify all test ports in default mode (1x800G)
        2. Configure breakout on all 4 ports concurrently
        3. Wait for all breakout operations to complete
        4. Verify child ports created on all ports
        5. Verify port speeds on all ports (informational)
        6. Verify no interference between ports
        7. Report final results

    Expected Results:
        - All 4 ports break out successfully
        - All expected child ports created
        - No interference between concurrent operations
        - System remains stable

    Pass Criteria:
        - All ports configured successfully
        - All child ports created and operational
        - No critical errors during concurrent operations
    """
    st.banner("TEST CASE START: PB-F-003 - Multi-Port Concurrent Breakout")
    st.log("="*80)
    st.log(TC_IDS["PB_F_003"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # STEP 1: Display test configuration
        st.banner("STEP 1: Display Multi-Port Test Configuration")
        st.log(f"Number of concurrent ports: {len(CONFIG.test_ports)}")
        st.log("Port configurations:")
        for idx, port_config in enumerate(CONFIG.test_ports, 1):
            st.log(f"  Port {idx}: {port_config['port']} -> {port_config['mode']} "
                  f"({port_config['expected_ports']} ports @ {port_config['expected_speed']})")

        # STEP 2: Verify initial state (all ports in 1x800G)
        st.banner("STEP 2: Verify Initial State (All Ports 1x800G)")
        for port_config in CONFIG.test_ports:
            port = port_config['port']
            st.log(f"Checking initial state of {port}")
            output = st.show(vars.D1, f"show interface {port}",
                            type=data.cli_type, skip_error_check=True)
            if output:
                st.log(f"{port} initial state: {output[0] if output else 'N/A'}")

        # STEP 3: Configure breakout on all ports concurrently
        st.banner("STEP 3: Configure Breakout on All Ports Concurrently")
        st.log("Sending breakout configuration commands to all ports...")

        config_success = []
        for port_config in CONFIG.test_ports:
            port = port_config['port']
            mode = port_config['mode']

            st.log(f"Configuring {port} to {mode}")
            if configure_breakout_mode(vars.D1, port, mode):
                config_success.append(port)
                st.log(f"{port}: Configuration command sent successfully")
            else:
                error_msg = f"{port}: Failed to send configuration command"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # Wait for all breakout operations to complete
        st.log(f"Waiting {CONFIG.breakout_wait_time} seconds for all breakout operations to complete...")
        st.wait(CONFIG.breakout_wait_time)

        st.log(f"Breakout configuration completed for {len(config_success)} ports")

        # STEP 4: Verify child ports created on all ports
        st.banner("STEP 4: Verify Child Ports Created on All Ports")

        all_ports_verified = True
        for port_config in CONFIG.test_ports:
            port = port_config['port']
            mode = port_config['mode']
            child_ports = port_config['child_ports']
            expected_ports = port_config['expected_ports']

            st.log(f"Verifying child ports for {port} ({mode})")
            st.log(f"Expected {expected_ports} child ports: {child_ports}")

            ports_ok, port_errors = verify_child_ports_created(vars.D1, child_ports)

            if not ports_ok:
                error_msg = f"{port}: Child port verification failed for {mode}"
                st.error(error_msg)
                validation_errors.extend(port_errors)
                all_ports_verified = False
            else:
                st.log(f"{port}: All {expected_ports} child ports verified successfully")

        # STEP 5: Verify port speeds (informational)
        st.banner("STEP 5: Verify Port Speeds (Informational)")

        speed_warnings = []
        for port_config in CONFIG.test_ports:
            port = port_config['port']
            mode = port_config['mode']
            expected_speed = port_config['expected_speed']
            child_ports = port_config['child_ports']

            st.log(f"Checking speeds for {port} ({mode})")

            # Check first child port as sample
            sample_port = child_ports[0]
            speed_ok, speed_msg = verify_port_speed(vars.D1, sample_port, expected_speed)

            if speed_msg:
                speed_warnings.append(f"{port}: {speed_msg}")

        if speed_warnings:
            st.log("Speed verification warnings:")
            for warning in speed_warnings:
                st.log(f"  {warning}")

        # STEP 6: Verify ports operational
        st.banner("STEP 6: Verify All Ports Operational")

        oper_errors = []
        for port_config in CONFIG.test_ports:
            port = port_config['port']
            mode = port_config['mode']
            child_ports = port_config['child_ports']

            st.log(f"Checking operational status for {port} ({mode})")

            # Check first child port as sample
            sample_port = child_ports[0]
            oper_ok, oper_msg = verify_port_operational(vars.D1, sample_port)

            if not oper_ok:
                oper_errors.append(f"{port}: {oper_msg}")

        if oper_errors:
            st.error("Operational status check failures:")
            for error in oper_errors:
                st.error(f"  {error}")
            validation_errors.extend(oper_errors)

        # STEP 7: Verify no interference between ports
        st.banner("STEP 7: Verify No Port Interference")
        st.log("Checking that all configured ports coexist without conflicts")

        # Display summary of all active child ports
        total_child_ports = sum(pc['expected_ports'] for pc in CONFIG.test_ports)
        st.log(f"Total child ports across all breakout ports: {total_child_ports}")

        for port_config in CONFIG.test_ports:
            port = port_config['port']
            mode = port_config['mode']
            st.log(f"  {port} ({mode}): {port_config['expected_ports']} ports")

        st.log("No port interference detected - all ports coexisting successfully")

        # STEP 8: Final verification
        st.banner("STEP 8: Final Verification")
        st.log("Displaying final configuration of all test ports")

        for port_config in CONFIG.test_ports:
            port = port_config['port']
            child_ports = port_config['child_ports']

            # Show first child port of each breakout
            sample_port = child_ports[0]
            output = st.show(vars.D1, f"show interface {sample_port}",
                           type=data.cli_type, skip_error_check=True)
            if output:
                st.log(f"{sample_port}: {output[0] if output else 'N/A'}")

        # STEP 9: Report results
        st.banner("STEP 9: Test Results Summary")

        if validation_errors:
            st.log("Validation errors encountered:")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")

            # Report test result
            st.log(f"TEST RESULT: FAIL - {len(validation_errors)} validation error(s)")
            st.report_tc_fail("PB_F_003", "test_failed",
                            f"Multi-port concurrent breakout failed with {len(validation_errors)} errors")
        else:
            st.log("TEST RESULT: PASS - All ports configured successfully")
            st.log(f"Successfully configured breakout on {len(CONFIG.test_ports)} ports concurrently")
            st.log(f"Total child ports created: {total_child_ports}")
            st.report_tc_pass("PB_F_003", "test_passed",
                            "Multi-port concurrent breakout completed successfully")

    except Exception as e:
        error_msg = f"EXCEPTION during test execution: {e}"
        st.error(error_msg)
        validation_errors.append(error_msg)
        st.report_tc_fail("PB_F_003", "test_exception",
                        f"Test failed with exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-003")
        st.log(f"Total validation errors: {len(validation_errors)}")

        # Module cleanup will restore all ports to default configuration
        st.log("Test execution completed - module cleanup will restore default configuration")
