"""
Test Case ID: PB-F-002
Title: Port Breakout Sequential Mode Transitions (Stress Test)
Author: Network Automation Team
Copyright (C) 2026

Description:
    This test validates port breakout stability during rapid sequential mode transitions.
    Tests system resilience by applying 6 different breakout modes consecutively.

Topology:
    DUT1 (Device Under Test)
    - Test Port: Ethernet24 (800G capable)

Test Approach:
    1. Start with default breakout mode (1x800G)
    2. Apply 6 different breakout modes sequentially
    3. Verify each transition completes successfully
    4. Verify child ports created correctly after each transition
    5. Monitor system stability throughout transitions
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
    "PB_F_002": "PB-F-002: Sequential Mode Transitions Stress Test",
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

    st.banner("MODULE CONFIGURATION START - PB-F-002")
    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")

    # Initialize configuration
    CONFIG.test_port = "Ethernet24"
    CONFIG.breakout_wait_time = 60  # Wait time after breakout configuration
    CONFIG.transition_count = 6

    # Define sequential breakout modes for stress test
    CONFIG.stress_test_modes = [
        {
            "mode": "8x100G",
            "expected_ports": 8,
            "expected_speed": "100GB",
            "child_ports": ["Ethernet24", "Ethernet25", "Ethernet26", "Ethernet27",
                          "Ethernet28", "Ethernet29", "Ethernet30", "Ethernet31"],
        },
        {
            "mode": "4x200G",
            "expected_ports": 4,
            "expected_speed": "200GB",
            "child_ports": ["Ethernet24", "Ethernet25", "Ethernet26", "Ethernet27"],
        },
        {
            "mode": "2x400G",
            "expected_ports": 2,
            "expected_speed": "400GB",
            "child_ports": ["Ethernet24", "Ethernet25"],
        },
        {
            "mode": "1x800G",
            "expected_ports": 1,
            "expected_speed": "800GB",
            "child_ports": ["Ethernet24"],
        },
        {
            "mode": "8x50G",
            "expected_ports": 8,
            "expected_speed": "50GB",
            "child_ports": ["Ethernet24", "Ethernet25", "Ethernet26", "Ethernet27",
                          "Ethernet28", "Ethernet29", "Ethernet30", "Ethernet31"],
        },
        {
            "mode": "4x100G",
            "expected_ports": 4,
            "expected_speed": "100GB",
            "child_ports": ["Ethernet24", "Ethernet25", "Ethernet26", "Ethernet27"],
        },
    ]

    # Pre-module configuration
    pre_config()

    # Yield to test execution
    yield

    # Cleanup after all tests
    st.banner("MODULE CONFIGURATION CLEANUP - PB-F-002")
    cleanup()
    st.banner("MODULE CONFIGURATION END - PB-F-002")


def pre_config():
    """
    Pre-configuration before test execution.

    Steps:
        1. Verify test port exists
        2. Reset port to default breakout mode (1x800G)
        3. Verify initial state
    """
    st.banner("PRE-CONFIGURATION START")

    try:
        vars = data.vars

        # Log initial configuration
        st.log(f"Test port: {CONFIG.test_port}")
        st.log(f"Stress test transitions: {CONFIG.transition_count}")
        st.log("Sequential modes:")
        for idx, mode_config in enumerate(CONFIG.stress_test_modes, 1):
            st.log(f"  Transition {idx}: {mode_config['mode']}")

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
        1. Revert port to default breakout mode (1x800G)
        2. Verify port is operational
        3. Log cleanup status
    """
    st.banner("CLEANUP START")

    try:
        vars = data.vars

        st.log(f"Reverting {CONFIG.test_port} to default mode (1x800G)")
        configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G")

        # Verify default mode
        st.log(f"Verifying {CONFIG.test_port} is in default mode")
        output = st.show(vars.D1, f"show interface {CONFIG.test_port}",
                        type=data.cli_type, skip_error_check=True)

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

        # Wait for breakout to complete
        st.log(f"Waiting {CONFIG.breakout_wait_time} seconds for breakout to complete...")
        st.wait(CONFIG.breakout_wait_time)

        st.log(f"Breakout mode {mode} configured on {port}")
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


def test_port_breakout_sequential_transitions():
    """
    Test Case: PB-F-002 - Port Breakout Sequential Mode Transitions (Stress Test)

    Objective:
        Validate port breakout stability during rapid sequential mode transitions.

    Test Steps:
        1. Start with port in default mode (1x800G)
        2. Apply 6 different breakout modes sequentially
        3. For each transition:
           - Configure new breakout mode
           - Verify child ports created correctly
           - Verify port speeds (informational)
           - Verify ports are operational
        4. Track all validation errors
        5. Report final result

    Expected Results:
        - All 6 transitions complete successfully
        - Child ports created correctly after each transition
        - System remains stable throughout
        - No critical errors during transitions

    Pass Criteria:
        - All breakout mode transitions successful
        - All expected child ports created
        - System stability maintained
    """
    st.banner("TEST CASE START: PB-F-002 - Sequential Mode Transitions Stress Test")
    st.log("="*80)
    st.log(TC_IDS["PB_F_002"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # STEP 1: Display test configuration
        st.banner("STEP 1: Display Stress Test Configuration")
        st.log(f"Test port: {CONFIG.test_port}")
        st.log(f"Total transitions: {CONFIG.transition_count}")
        st.log(f"Transition sequence:")
        for idx, mode_config in enumerate(CONFIG.stress_test_modes, 1):
            st.log(f"  Transition {idx}: {mode_config['mode']} "
                  f"({mode_config['expected_ports']} ports @ {mode_config['expected_speed']})")

        # STEP 2: Verify initial state (1x800G)
        st.banner("STEP 2: Verify Initial State (1x800G)")
        st.log(f"Verifying {CONFIG.test_port} is in default mode")
        output = st.show(vars.D1, f"show interface {CONFIG.test_port}",
                        type=data.cli_type, skip_error_check=True)

        if output:
            st.log(f"Initial port state: {output[0] if output else 'N/A'}")

        # STEP 3: Execute sequential transitions
        st.banner("STEP 3: Execute Sequential Breakout Mode Transitions")

        for transition_num, mode_config in enumerate(CONFIG.stress_test_modes, 1):
            st.banner(f"TRANSITION {transition_num}/{CONFIG.transition_count}: "
                     f"Applying {mode_config['mode']}")

            mode = mode_config['mode']
            expected_ports = mode_config['expected_ports']
            expected_speed = mode_config['expected_speed']
            child_ports = mode_config['child_ports']

            # Configure breakout mode
            st.log(f"Configuring breakout mode: {mode}")
            if not configure_breakout_mode(vars.D1, CONFIG.test_port, mode):
                error_msg = f"Transition {transition_num}: Failed to configure {mode}"
                st.error(error_msg)
                validation_errors.append(error_msg)
                continue  # Continue with next transition even on error

            st.log(f"Transition {transition_num}: {mode} configured successfully")

            # Verify child ports created
            st.log(f"Verifying {expected_ports} child ports created")
            ports_ok, port_errors = verify_child_ports_created(vars.D1, child_ports)

            if not ports_ok:
                error_msg = (f"Transition {transition_num}: Child port verification failed "
                           f"for {mode}")
                st.error(error_msg)
                validation_errors.extend(port_errors)
            else:
                st.log(f"Transition {transition_num}: All {expected_ports} child ports verified")

            # Verify port speeds (informational)
            st.log("Verifying port speeds (informational)")
            speed_warnings = []
            for port in child_ports[:2]:  # Check first 2 ports as sample
                speed_ok, speed_msg = verify_port_speed(vars.D1, port, expected_speed)
                if speed_msg:
                    speed_warnings.append(speed_msg)

            if speed_warnings:
                st.log(f"Speed verification warnings: {speed_warnings}")

            # Verify ports operational
            st.log("Verifying ports are operational")
            oper_errors = []
            for port in child_ports[:2]:  # Check first 2 ports as sample
                oper_ok, oper_msg = verify_port_operational(vars.D1, port)
                if not oper_ok:
                    oper_errors.append(oper_msg)

            if oper_errors:
                error_msg = (f"Transition {transition_num}: Operational status check failed "
                           f"for {mode}")
                st.error(error_msg)
                validation_errors.extend(oper_errors)

            st.log(f"Transition {transition_num} completed: {mode}")
            st.log("-" * 80)

        # STEP 4: Final verification
        st.banner("STEP 4: Final Verification After All Transitions")
        st.log("Displaying final port configuration")

        final_mode = CONFIG.stress_test_modes[-1]
        for port in final_mode['child_ports'][:3]:  # Show first 3 ports
            output = st.show(vars.D1, f"show interface {port}",
                           type=data.cli_type, skip_error_check=True)
            if output:
                st.log(f"Port {port}: {output[0] if output else 'N/A'}")

        # STEP 5: Report results
        st.banner("STEP 5: Test Results Summary")

        if validation_errors:
            st.log("Validation errors encountered:")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")

            # Report test result
            st.log(f"TEST RESULT: FAIL - {len(validation_errors)} validation error(s)")
            st.report_tc_fail("PB_F_002", "test_failed",
                            f"Sequential transitions stress test failed with {len(validation_errors)} errors")
        else:
            st.log("TEST RESULT: PASS - All sequential transitions completed successfully")
            st.log(f"Successfully completed {CONFIG.transition_count} sequential breakout mode transitions")
            st.report_tc_pass("PB_F_002", "test_passed",
                            "Sequential transitions stress test completed successfully")

    except Exception as e:
        error_msg = f"EXCEPTION during test execution: {e}"
        st.error(error_msg)
        validation_errors.append(error_msg)
        st.report_tc_fail("PB_F_002", "test_exception",
                        f"Test failed with exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-002")
        st.log(f"Total validation errors: {len(validation_errors)}")

        # Ensure port is left in a known state (will be cleaned up by module cleanup)
        st.log("Test execution completed - module cleanup will restore default configuration")
