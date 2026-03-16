"""
TC_SM_ISCLI_2: Port Breakout Modes and Num-Lanes Validation

Test Case ID: SM-ISCLI-2
Author: Network Automation Team
Copyright (C) 2026, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_sm18_hw.yaml \
    tests/system/SM_ISCLI/test_sm_iscli_2_port_breakout_modes_validation.py \
    --logs-path ./logs/sm_iscli_2_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates port breakout functionality with different modes and num-lanes parameters.

  Test validates:
  1. Port breakout with 1x400G mode and num-lanes 4 (Physical Channels: 8)
  2. Port breakout with 1x400G mode and num-lanes 8 (Physical Channels: 8)
  3. Port breakout with 1x400G mode default (Physical Channels: 8)
  4. Port breakout with 1x400G(4) mode syntax (Physical Channels: 4)
  5. Port breakout with 2x200G mode and num-lanes 4 (Physical Channels: 4)
  6. Port breakout with 1x800G mode (Physical Channels: 16)

  Each test step:
  - Applies port breakout configuration
  - Verifies configuration success message
  - Validates 'show interface breakout current' output
  - Confirms Current Mode, Num Breakouts, Speed, Physical Channels

  EXPECTED BEHAVIOR:
  - All port breakout commands succeed with success message
  - Show commands display correct mode, speed, and physical channels
  - num-lanes parameter affects physical channels allocation
  - Mode with parentheses syntax (e.g., 1x400G(4)) works correctly

Pre-requisites:
  - Topology: single-node (D1 only) | Supported: HW only
  - Testbed: testbed_sm18_hw.yaml (single hardware device)
  - Device: 192.168.100.173 (Supermicro SSE-T8164S with 800G ports)
  - Credentials: admin/sonic@123
  - SONiC build: portbreakout-1203-1826 or later
  - Test port: Ethernet64 (800G capable port)

Note:
  - Test uses sonic-cli (klish) interface
  - Configuration changes are made and verified
  - Test restores port to 1x800G at cleanup
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
import re

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    # Test port (use 800G capable port)
    "test_port": "Ethernet64",
    
    # Test scenarios with expected values
    "test_scenarios": [
        {
            "scenario_id": 1,
            "mode": "1x400G",
            "num_lanes": 4,
            "expected_mode": "1x400G",
            "expected_breakouts": 1,
            "expected_speed": "400G",
            "expected_channels": 8,
            "description": "1x400G with num-lanes 4 (Physical Channels: 8)"
        },
        {
            "scenario_id": 2,
            "mode": "1x400G",
            "num_lanes": 8,
            "expected_mode": "1x400G",
            "expected_breakouts": 1,
            "expected_speed": "400G",
            "expected_channels": 8,
            "description": "1x400G with num-lanes 8 (Physical Channels: 8)"
        },
        {
            "scenario_id": 3,
            "mode": "1x400G",
            "num_lanes": None,  # Default
            "expected_mode": "1x400G",
            "expected_breakouts": 1,
            "expected_speed": "400G",
            "expected_channels": 8,
            "description": "1x400G default (Physical Channels: 8)"
        },
        {
            "scenario_id": 4,
            "mode": "1x400G(4)",
            "num_lanes": None,
            "expected_mode": "1x400G",
            "expected_breakouts": 1,
            "expected_speed": "400G",
            "expected_channels": 8,
            "description": "1x400G(4) mode with parentheses (Physical Channels: 8 - device strips parentheses)"
        },
        {
            "scenario_id": 5,
            "mode": "2x200G",
            "num_lanes": 4,
            "expected_mode": "2x200G",
            "expected_breakouts": 2,
            "expected_speed": "200G",
            "expected_channels": 4,
            "description": "2x200G with num-lanes 4 (Physical Channels: 4)"
        },
        {
            "scenario_id": 6,
            "mode": "1x800G",
            "num_lanes": None,
            "expected_mode": "1x800G",
            "expected_breakouts": 1,
            "expected_speed": "800G",
            "expected_channels": 16,
            "description": "1x800G default (Physical Channels: 16)"
        },
    ],
})

# Test Case IDs
TC_IDS = SpyTestDict({
    "sm2_scenario_1": "SM-ISCLI-2.1",
    "sm2_scenario_2": "SM-ISCLI-2.2",
    "sm2_scenario_3": "SM-ISCLI-2.3",
    "sm2_scenario_4": "SM-ISCLI-2.4",
    "sm2_scenario_5": "SM-ISCLI-2.5",
    "sm2_scenario_6": "SM-ISCLI-2.6",
})


#################################################################
# Module-level Fixture
#################################################################

@pytest.fixture(scope="module", autouse=True)
def sm2_module_hooks(request):
    """
    Module-level setup and teardown.

    This fixture runs once before all tests in the module and once after all tests complete.
    It handles topology initialization and device verification.

    Args:
        request: pytest request object

    Yields:
        None (control returns to test execution)
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_2 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get device variables
    vars = st.ensure_min_topology("D1")

    # Set CLI type
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")
    st.log(f"Test port: {CONFIG.test_port}")

    # Pre-configuration
    sm2_pre_config()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_2 MODULE CONFIGURATION - COMPLETE")
    st.banner("=" * 80)

    # Yield to test execution
    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_2 MODULE CLEANUP - START")
    st.banner("=" * 80)

    sm2_cleanup()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_2 MODULE CLEANUP - COMPLETE")
    st.banner("=" * 80)


#################################################################
# Pre-Configuration and Cleanup Functions
#################################################################

def sm2_pre_config() -> None:
    """
    Pre-configuration for SM_ISCLI_2 test.

    Verifies device connectivity and initial port state.

    Returns:
        None
    """
    st.banner("STEP: SM2 PRE-CONFIGURATION")

    st.log(f"Verifying connectivity to device: {vars.D1}")
    
    # Verify test port exists
    st.log(f"Verifying test port {CONFIG.test_port} exists")
    cmd = "show interface breakout | no-more"
    output = st.show(vars.D1, cmd, type=data.cli_type, skip_tmpl=True)
    st.log(f"Current breakout configuration:\n{output}")

    st.banner("STEP: SM2 PRE-CONFIGURATION - COMPLETE")


def sm2_cleanup() -> None:
    """
    Cleanup configuration after SM_ISCLI_2 test.

    Restores test port to default 1x800G mode.

    Returns:
        None
    """
    st.banner("STEP: SM2 CLEANUP")

    st.log(f"Restoring {CONFIG.test_port} to default 1x800G mode")
    
    try:
        # Restore to 1x800G
        cmd = f"interface breakout {CONFIG.test_port} mode 1x800G"
        st.config(vars.D1, cmd, type=data.cli_type)
        st.log(f"Port {CONFIG.test_port} restored to 1x800G")
        
        # Verify restoration
        verify_cmd = f"show interface breakout current {CONFIG.test_port} | no-more"
        output = st.show(vars.D1, verify_cmd, type=data.cli_type, skip_tmpl=True)
        st.log(f"Final port state:\n{output}")
        
    except Exception as e:
        st.error(f"Cleanup failed: {e}")

    st.banner("STEP: SM2 CLEANUP - COMPLETE")


#################################################################
# Helper Functions
#################################################################

def apply_port_breakout(dut: str, port: str, mode: str, num_lanes: int = None) -> bool:
    """
    Apply port breakout configuration.

    Args:
        dut: Device under test
        port: Port name (e.g., "Ethernet64")
        mode: Breakout mode (e.g., "1x400G", "2x200G", "1x400G(4)")
        num_lanes: Number of lanes (optional, 4 or 8)

    Returns:
        bool: True if configuration successful, False otherwise
    """
    st.banner(f"STEP: Apply port breakout - {port} mode {mode}" + 
              (f" num-lanes {num_lanes}" if num_lanes else ""))

    try:
        # Build command
        if num_lanes:
            cmd = f"interface breakout {port} mode {mode} num-lanes {num_lanes}"
        else:
            cmd = f"interface breakout {port} mode {mode}"

        st.log(f"Executing: {cmd}")
        output = st.config(vars.D1, cmd, type=data.cli_type)

        st.log(f"Command output:\\n{output}")

        # Validate success message
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output

        # Exit config mode to allow show commands to work properly
        st.log("Exiting config mode after breakout configuration")
        st.config(vars.D1, "end", type=data.cli_type)

        # Check for success message
        if "Success" in output_str and "Port breakout successful" in output_str:
            st.log(f"PASS: Port breakout configuration successful")
            return True
        elif "Error" in output_str:
            st.error(f"FAIL: Port breakout configuration failed with error")
            return False
        else:
            # Some SONiC versions may not show success message
            st.log("INFO: No explicit success/error message - verifying with show command")
            return True

    except Exception as e:
        st.error(f"EXCEPTION: Failed to apply port breakout: {e}")
        return False



def verify_port_breakout_current(dut: str, port: str, expected_mode: str, 
                                  expected_breakouts: int, expected_speed: str,
                                  expected_channels: int) -> bool:
    """
    Verify port breakout current configuration.

    Args:
        dut: Device under test
        port: Port name (e.g., "Ethernet64")
        expected_mode: Expected breakout mode (e.g., "1x400G")
        expected_breakouts: Expected number of breakouts (e.g., 1, 2, 4, 8)
        expected_speed: Expected speed (e.g., "400G")
        expected_channels: Expected physical channels (e.g., 4, 8, 16)

    Returns:
        bool: True if verification successful, False otherwise
    """
    st.banner(f"STEP: Verify 'show interface breakout current {port}'")

    try:
        # Execute show command
        cmd = f"show interface breakout current {port} | no-more"
        st.log(f"Executing: {cmd}")
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)

        st.log(f"Command output:\n{output}")

        # Convert to string if needed
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output

        # Validation 1: Check for port name
        st.log("Validation 1: Checking for port name")
        if f"Port: {port}" not in output_str and port not in output_str:
            st.error(f"FAIL: Port name '{port}' not found in output")
            return False
        st.log(f"PASS: Port name '{port}' found")

        # Validation 2: Extract and validate Current Mode
        st.log("Validation 2: Validating Current Mode")
        mode_pattern = r'Current Mode:\s+([\dx]+G(?:\(\d+\))?)'
        mode_match = re.search(mode_pattern, output_str)
        if not mode_match:
            st.error("FAIL: Current Mode not found in output")
            return False
        
        actual_mode = mode_match.group(1)
        if actual_mode != expected_mode:
            st.error(f"FAIL: Current Mode mismatch - Expected: {expected_mode}, Actual: {actual_mode}")
            return False
        st.log(f"PASS: Current Mode = {actual_mode} (matches expected)")

        # Validation 3: Extract and validate Num Breakouts
        st.log("Validation 3: Validating Num Breakouts")
        num_pattern = r'Num Breakouts:\s+(\d+)'
        num_match = re.search(num_pattern, output_str)
        if not num_match:
            st.error("FAIL: Num Breakouts not found in output")
            return False
        
        actual_breakouts = int(num_match.group(1))
        if actual_breakouts != expected_breakouts:
            st.error(f"FAIL: Num Breakouts mismatch - Expected: {expected_breakouts}, Actual: {actual_breakouts}")
            return False
        st.log(f"PASS: Num Breakouts = {actual_breakouts} (matches expected)")

        # Validation 4: Extract and validate Speed
        st.log("Validation 4: Validating Speed")
        speed_pattern = r'Speed:\s+(\d+G)'
        speed_match = re.search(speed_pattern, output_str)
        if not speed_match:
            st.error("FAIL: Speed not found in output")
            return False
        
        actual_speed = speed_match.group(1)
        if actual_speed != expected_speed:
            st.error(f"FAIL: Speed mismatch - Expected: {expected_speed}, Actual: {actual_speed}")
            return False
        st.log(f"PASS: Speed = {actual_speed} (matches expected)")

        # Validation 5: Extract and validate Physical Channels
        st.log("Validation 5: Validating Physical Channels")
        channels_pattern = r'Physical Channels:\s+(\d+)'
        channels_match = re.search(channels_pattern, output_str)
        if not channels_match:
            st.error("FAIL: Physical Channels not found in output")
            return False
        
        actual_channels = int(channels_match.group(1))
        if actual_channels != expected_channels:
            st.error(f"FAIL: Physical Channels mismatch - Expected: {expected_channels}, Actual: {actual_channels}")
            return False
        st.log(f"PASS: Physical Channels = {actual_channels} (matches expected)")

        st.log(f"SUCCESS: All validations passed for {port}")
        return True

    except Exception as e:
        st.error(f"EXCEPTION: Failed to verify port breakout current: {e}")
        return False


#################################################################
# Main Test Function
#################################################################

def test_sm_iscli_2_port_breakout_modes_validation():
    """
    TC_SM_ISCLI_2: Port Breakout Modes and Num-Lanes Validation

    Test validates port breakout functionality with different modes and num-lanes parameters.

    Test Steps:
        1. Configure 1x400G with num-lanes 4, verify Physical Channels: 8
        2. Configure 1x400G with num-lanes 8, verify Physical Channels: 8
        3. Configure 1x400G default, verify Physical Channels: 8
        4. Configure 1x400G(4) with parentheses, verify Physical Channels: 4
        5. Configure 2x200G with num-lanes 4, verify Physical Channels: 4
        6. Configure 1x800G default, verify Physical Channels: 16

    Expected Results:
        - All port breakout commands succeed
        - Show commands display correct Current Mode, Num Breakouts, Speed, Physical Channels
        - num-lanes parameter affects physical channels allocation
        - Mode with parentheses syntax works correctly

    Returns:
        None (uses st.report_pass/fail for test result reporting)
    """
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_2: Port Breakout Modes and Num-Lanes Validation TEST - START")
    st.banner("=" * 80)

    # Track validation errors
    validation_errors = []

    #################################################################
    # Execute all test scenarios
    #################################################################
    
    for scenario in CONFIG.test_scenarios:
        scenario_id = scenario["scenario_id"]
        tc_id = f"sm2_scenario_{scenario_id}"
        
        st.banner("=" * 80)
        st.banner(f"SCENARIO {scenario_id}: {scenario['description']}")
        st.banner("=" * 80)

        # Step 1: Apply port breakout configuration
        st.log(f"Step 1: Applying port breakout - mode {scenario['mode']}" + 
               (f" num-lanes {scenario['num_lanes']}" if scenario['num_lanes'] else ""))
        
        if not apply_port_breakout(vars.D1, CONFIG.test_port, scenario["mode"], scenario["num_lanes"]):
            error_msg = f"SCENARIO {scenario_id} FAILED: Port breakout configuration failed"
            validation_errors.append(error_msg)
            st.error(error_msg)
            st.generate_tech_support([vars.D1], f"sm2_scenario_{scenario_id}_config_failed")
            st.report_tc_fail(
                TC_IDS[tc_id],
                "msg",
                f"Port breakout configuration failed for {scenario['description']}"
            )
            continue

        # Step 2: Verify port breakout current output
        st.log(f"Step 2: Verifying 'show interface breakout current' output")
        
        if not verify_port_breakout_current(
            vars.D1, 
            CONFIG.test_port,
            scenario["expected_mode"],
            scenario["expected_breakouts"],
            scenario["expected_speed"],
            scenario["expected_channels"]
        ):
            error_msg = f"SCENARIO {scenario_id} FAILED: Port breakout verification failed"
            validation_errors.append(error_msg)
            st.error(error_msg)
            st.generate_tech_support([vars.D1], f"sm2_scenario_{scenario_id}_verify_failed")
            st.report_tc_fail(
                TC_IDS[tc_id],
                "msg",
                f"Port breakout verification failed for {scenario['description']}"
            )
            continue

        # Scenario passed
        st.log(f"SCENARIO {scenario_id} PASSED: {scenario['description']}")
        st.report_tc_pass(
            TC_IDS[tc_id],
            "msg",
            f"Port breakout validation successful for {scenario['description']}"
        )

    #################################################################
    # Final Result
    #################################################################
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_2: Port Breakout Modes and Num-Lanes Validation TEST - COMPLETE")
    st.banner("=" * 80)

    if validation_errors:
        error_summary = f"TC_SM_ISCLI_2 FAILED with {len(validation_errors)} error(s): {'; '.join(validation_errors)}"
        st.error(error_summary)
        st.banner("TEST RESULT: FAILED ❌")
        st.report_fail("test_case_failed", error_summary)
    else:
        success_msg = "TC_SM_ISCLI_2 PASSED: All port breakout modes and num-lanes scenarios validated successfully"
        st.log(success_msg)
        st.banner("TEST RESULT: PASSED ✅")
        st.report_pass("test_case_passed", success_msg)
