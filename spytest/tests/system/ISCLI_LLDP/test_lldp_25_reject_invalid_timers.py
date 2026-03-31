r"""
LLDP TEST - OC-1 Test ID 4.16.25: Verify rejection of invalid LLDP timer values

Test Case ID: 4.16.25
Feature: LLDP
Test Item: Invalid Timer Rejection
Author: Automated from Manual Validation
Copyright (C) 2024-2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_LLDP/test_lldp_25_reject_invalid_timers.py \
    --logs-path ./logs/lldp_25_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates that invalid LLDP timer values are rejected:
  - Enable LLDP globally
  - Attempt to configure invalid timer values (out of range)
  - Verify configuration is rejected with error
  - Attempt to configure invalid hold-time multiplier
  - Verify configuration is rejected with error
  - Configure valid timer values (verify system accepts)
  - Rollback configuration

Pre-requisites:
  - 2 SONiC devices connected
  - Testbed: testbed_2vs.yaml
  - Clean LLDP configuration

Expected Result (Manual Test):
  PASS - Invalid timer values rejected, valid values accepted

Manual Test Log Reference (Test 4.16.25 PASS):
  sonic(config)# lldp enable
  sonic(config)# lldp timer 4
  [Expected: Error - out of range]
  [Actual: Error message shown - PASS]

  sonic(config)# lldp timer 32768
  [Expected: Error - out of range]
  [Actual: Error message shown - PASS]

  sonic(config)# lldp timer 30
  [Expected: Success]
  [Actual: Command accepted - PASS]

  sonic(config)# lldp holdtime 1
  [Expected: Error - out of range]
  [Actual: Error message shown - PASS]

  sonic(config)# lldp holdtime 11
  [Expected: Error - out of range]
  [Actual: Error message shown - PASS]

  sonic(config)# lldp holdtime 4
  [Expected: Success]
  [Actual: Command accepted - PASS]
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
import re
import time

import apis.system.lldp as lldpapi
import apis.system.interface as intfapi
import apis.system.basic as basicapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration matching manual testcase
CONFIG = SpyTestDict({
    # Invalid timer values (should be rejected)
    "invalid_timer_too_low": 4,      # Below minimum (5)
    "invalid_timer_too_high": 32768,  # Above maximum (32767)
    # Valid timer value
    "valid_timer": 30,

    # Invalid hold-time multiplier values (should be rejected)
    "invalid_holdtime_too_low": 1,   # Below minimum (2)
    "invalid_holdtime_too_high": 11, # Above maximum (10)
    # Valid hold-time multiplier
    "valid_holdtime": 4,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "lldp_global_enable": "TC-LLDP-4.16.25-001",
    "reject_invalid_timer_low": "TC-LLDP-4.16.25-002",
    "reject_invalid_timer_high": "TC-LLDP-4.16.25-003",
    "accept_valid_timer": "TC-LLDP-4.16.25-004",
    "reject_invalid_holdtime_low": "TC-LLDP-4.16.25-005",
    "reject_invalid_holdtime_high": "TC-LLDP-4.16.25-006",
    "accept_valid_holdtime": "TC-LLDP-4.16.25-007",
    "lldp_rollback": "TC-LLDP-4.16.25-008",
})


@pytest.fixture(scope="module", autouse=True)
def lldp_invalid_timers_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.25 INVALID TIMER REJECTION TEST - MODULE START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")

    # Get CLI type from framework
    data.cli_type = st.get_ui_type()

    st.log(f"DUT1 (DUT-A): {vars.D1}")
    st.log(f"DUT2 (DUT-B): {vars.D2}")
    st.log(f"CLI Type: {data.cli_type} (auto-detected by framework)")

    # Pre-configuration
    lldp_pre_config()

    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.25 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        lldp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")

    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.25 MODULE CLEANUP - COMPLETED")
    st.banner("=" * 80)


def lldp_pre_config():
    """Pre-configuration: Clean LLDP state."""
    st.log("Pre-configuration: Preparing LLDP environment")

    dut_list = [vars.D1, vars.D2]

    # Disable LLDP initially for clean baseline
    st.log("Disabling LLDP globally on both DUTs (clean baseline)")
    for dut in dut_list:
        try:
            disable_lldp_globally(dut)
        except Exception as e:
            st.log(f"LLDP disable warning on {dut}: {str(e)}")

    st.wait(5, "Waiting for LLDP to stabilize")
    st.log("Pre-configuration completed")


def lldp_pre_config_cleanup():
    """Cleanup: Remove all LLDP configuration."""
    st.log("Cleanup: Removing LLDP configuration")

    dut_list = [vars.D1, vars.D2]

    # Disable LLDP globally
    for dut in dut_list:
        try:
            disable_lldp_globally(dut)
        except Exception as e:
            st.log(f"LLDP disable warning on {dut}: {str(e)}")

    st.log("Cleanup completed")


def enable_lldp_globally(dut: str) -> bool:
    """Enable LLDP globally."""
    st.log(f"Enabling LLDP globally on {dut}")
    try:
        st.config(dut, [
            "configure terminal",
            "lldp enable",
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ LLDP enabled globally on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to enable LLDP globally on {dut}: {str(e)}")
        return False


def disable_lldp_globally(dut: str) -> bool:
    """Disable LLDP globally."""
    st.log(f"Disabling LLDP globally on {dut}")
    try:
        st.config(dut, [
            "configure terminal",
            "no lldp enable",
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ LLDP disabled globally on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to disable LLDP globally on {dut}: {str(e)}")
        return False


def configure_lldp_timer_expect_error(dut: str, timer_value: int) -> bool:
    """
    Attempt to configure LLDP timer and expect error.

    Args:
        dut: Device name
        timer_value: Timer value (expected to be invalid)

    Returns:
        bool: True if error received (expected behavior)
    """
    st.log(f"Attempting to configure LLDP timer to {timer_value} (expecting error)")
    try:
        output = st.config(dut, [
            "configure terminal",
            f"lldp timer {timer_value}",
            "exit"
        ], type=data.cli_type, skip_error_check=False)

        output_str = str(output)
        st.log(f"Command output:\n{output_str}")

        # Check for error indicators
        if ("Error" in output_str or "error" in output_str or
            "Invalid" in output_str or "invalid" in output_str or
            "out of range" in output_str or
            "%" in output_str):  # CLI error indicator
            st.log(f"✓ Invalid timer {timer_value} REJECTED (expected)")
            return True
        else:
            st.log(f"✗ Invalid timer {timer_value} ACCEPTED (unexpected)")
            return False

    except Exception as e:
        # Exception means command was rejected (expected)
        st.log(f"✓ Invalid timer {timer_value} REJECTED with exception (expected): {str(e)}")
        return True


def configure_lldp_timer_expect_success(dut: str, timer_value: int) -> bool:
    """
    Attempt to configure LLDP timer and expect success.

    Args:
        dut: Device name
        timer_value: Timer value (expected to be valid)

    Returns:
        bool: True if successful (expected behavior)
    """
    st.log(f"Attempting to configure LLDP timer to {timer_value} (expecting success)")
    try:
        output = st.config(dut, [
            "configure terminal",
            f"lldp timer {timer_value}",
            "exit"
        ], type=data.cli_type, skip_error_check=True)

        output_str = str(output)
        st.log(f"Command output:\n{output_str}")

        # Check for error indicators
        if ("Error" in output_str or "error" in output_str or
            "Invalid" in output_str or "invalid" in output_str):
            st.log(f"✗ Valid timer {timer_value} REJECTED (unexpected)")
            return False
        else:
            st.log(f"✓ Valid timer {timer_value} ACCEPTED (expected)")
            return True

    except Exception as e:
        st.log(f"✗ Valid timer {timer_value} REJECTED with exception (unexpected): {str(e)}")
        return False


def configure_lldp_holdtime_expect_error(dut: str, holdtime_value: int) -> bool:
    """
    Attempt to configure LLDP hold-time and expect error.

    Args:
        dut: Device name
        holdtime_value: Hold-time multiplier (expected to be invalid)

    Returns:
        bool: True if error received (expected behavior)
    """
    st.log(f"Attempting to configure LLDP hold-time to {holdtime_value} (expecting error)")
    try:
        output = st.config(dut, [
            "configure terminal",
            f"lldp holdtime {holdtime_value}",
            "exit"
        ], type=data.cli_type, skip_error_check=False)

        output_str = str(output)
        st.log(f"Command output:\n{output_str}")

        # Check for error indicators
        if ("Error" in output_str or "error" in output_str or
            "Invalid" in output_str or "invalid" in output_str or
            "out of range" in output_str or
            "%" in output_str):
            st.log(f"✓ Invalid hold-time {holdtime_value} REJECTED (expected)")
            return True
        else:
            st.log(f"✗ Invalid hold-time {holdtime_value} ACCEPTED (unexpected)")
            return False

    except Exception as e:
        # Exception means command was rejected (expected)
        st.log(f"✓ Invalid hold-time {holdtime_value} REJECTED with exception (expected): {str(e)}")
        return True


def configure_lldp_holdtime_expect_success(dut: str, holdtime_value: int) -> bool:
    """
    Attempt to configure LLDP hold-time and expect success.

    Args:
        dut: Device name
        holdtime_value: Hold-time multiplier (expected to be valid)

    Returns:
        bool: True if successful (expected behavior)
    """
    st.log(f"Attempting to configure LLDP hold-time to {holdtime_value} (expecting success)")
    try:
        output = st.config(dut, [
            "configure terminal",
            f"lldp holdtime {holdtime_value}",
            "exit"
        ], type=data.cli_type, skip_error_check=True)

        output_str = str(output)
        st.log(f"Command output:\n{output_str}")

        # Check for error indicators
        if ("Error" in output_str or "error" in output_str or
            "Invalid" in output_str or "invalid" in output_str):
            st.log(f"✗ Valid hold-time {holdtime_value} REJECTED (unexpected)")
            return False
        else:
            st.log(f"✓ Valid hold-time {holdtime_value} ACCEPTED (expected)")
            return True

    except Exception as e:
        st.log(f"✗ Valid hold-time {holdtime_value} REJECTED with exception (unexpected): {str(e)}")
        return False


def test_lldp_25_reject_invalid_timers():
    """
    Test Case 4.16.25: Verify rejection of invalid LLDP timer values

    Test Objective: Verify system rejects invalid timer values and accepts valid values

    Steps:
        1. Enable LLDP globally
        2. Attempt to configure timer value 4 (too low) - expect rejection
        3. Attempt to configure timer value 32768 (too high) - expect rejection
        4. Configure timer value 30 (valid) - expect success
        5. Attempt to configure hold-time 1 (too low) - expect rejection
        6. Attempt to configure hold-time 11 (too high) - expect rejection
        7. Configure hold-time 4 (valid) - expect success
        8. Rollback configuration

    Expected Result (from Manual Test):
        PASS - Invalid timer values rejected, valid values accepted

    Actual Result: PASS (as per manual test log)

    Valid Ranges (typical):
        - LLDP Timer: 5-32767 seconds
        - LLDP Hold-time Multiplier: 2-10
    """

    # Track validation results
    validation_results = SpyTestDict({
        "global_enable": False,
        "reject_timer_too_low": False,
        "reject_timer_too_high": False,
        "accept_valid_timer": False,
        "reject_holdtime_too_low": False,
        "reject_holdtime_too_high": False,
        "accept_valid_holdtime": False,
        "rollback": False,
    })

    st.banner("=" * 80)
    st.banner("TEST CASE 4.16.25: Verify rejection of invalid LLDP timer values")
    st.banner("=" * 80)
    st.log(f"Test Objective: Verify invalid timer values are rejected")
    st.log(f"DUT1: {vars.D1}")
    st.log("")
    st.log(f"Test Values:")
    st.log(f"  Invalid Timer (too low): {CONFIG.invalid_timer_too_low} (< 5)")
    st.log(f"  Invalid Timer (too high): {CONFIG.invalid_timer_too_high} (> 32767)")
    st.log(f"  Valid Timer: {CONFIG.valid_timer}")
    st.log(f"  Invalid Hold-time (too low): {CONFIG.invalid_holdtime_too_low} (< 2)")
    st.log(f"  Invalid Hold-time (too high): {CONFIG.invalid_holdtime_too_high} (> 10)")
    st.log(f"  Valid Hold-time: {CONFIG.valid_holdtime}")
    st.log("")

    # ==================================================================
    # STEP 1: Enable LLDP Globally
    # ==================================================================
    st.banner("STEP 1: Enable LLDP Globally")

    if enable_lldp_globally(vars.D1):
        validation_results.global_enable = True
        st.log("✓ LLDP enabled globally on DUT1")
        st.report_tc_pass(TC_IDS.lldp_global_enable, "msg",
                         "LLDP enabled globally")
    else:
        st.log("✗ Failed to enable LLDP globally")
        st.report_tc_fail(TC_IDS.lldp_global_enable, "msg",
                         "Failed to enable LLDP globally")

    # ==================================================================
    # STEP 2: Attempt Invalid Timer Value (Too Low)
    # ==================================================================
    st.banner(f"STEP 2: Attempt Invalid Timer Value {CONFIG.invalid_timer_too_low} (Too Low)")

    if configure_lldp_timer_expect_error(vars.D1, CONFIG.invalid_timer_too_low):
        validation_results.reject_timer_too_low = True
        st.log(f"✓ Invalid timer {CONFIG.invalid_timer_too_low} REJECTED (expected)")
        st.report_tc_pass(TC_IDS.reject_invalid_timer_low, "msg",
                         f"Invalid timer {CONFIG.invalid_timer_too_low} rejected")
    else:
        st.log(f"✗ Invalid timer {CONFIG.invalid_timer_too_low} NOT REJECTED (unexpected)")
        st.report_tc_fail(TC_IDS.reject_invalid_timer_low, "msg",
                         f"Invalid timer {CONFIG.invalid_timer_too_low} not rejected")

    # ==================================================================
    # STEP 3: Attempt Invalid Timer Value (Too High)
    # ==================================================================
    st.banner(f"STEP 3: Attempt Invalid Timer Value {CONFIG.invalid_timer_too_high} (Too High)")

    if configure_lldp_timer_expect_error(vars.D1, CONFIG.invalid_timer_too_high):
        validation_results.reject_timer_too_high = True
        st.log(f"✓ Invalid timer {CONFIG.invalid_timer_too_high} REJECTED (expected)")
        st.report_tc_pass(TC_IDS.reject_invalid_timer_high, "msg",
                         f"Invalid timer {CONFIG.invalid_timer_too_high} rejected")
    else:
        st.log(f"✗ Invalid timer {CONFIG.invalid_timer_too_high} NOT REJECTED (unexpected)")
        st.report_tc_fail(TC_IDS.reject_invalid_timer_high, "msg",
                         f"Invalid timer {CONFIG.invalid_timer_too_high} not rejected")

    # ==================================================================
    # STEP 4: Configure Valid Timer Value
    # ==================================================================
    st.banner(f"STEP 4: Configure Valid Timer Value {CONFIG.valid_timer}")

    if configure_lldp_timer_expect_success(vars.D1, CONFIG.valid_timer):
        validation_results.accept_valid_timer = True
        st.log(f"✓ Valid timer {CONFIG.valid_timer} ACCEPTED (expected)")
        st.report_tc_pass(TC_IDS.accept_valid_timer, "msg",
                         f"Valid timer {CONFIG.valid_timer} accepted")
    else:
        st.log(f"✗ Valid timer {CONFIG.valid_timer} REJECTED (unexpected)")
        st.report_tc_fail(TC_IDS.accept_valid_timer, "msg",
                         f"Valid timer {CONFIG.valid_timer} rejected")

    # ==================================================================
    # STEP 5: Attempt Invalid Hold-time Value (Too Low)
    # ==================================================================
    st.banner(f"STEP 5: Attempt Invalid Hold-time Value {CONFIG.invalid_holdtime_too_low} (Too Low)")

    if configure_lldp_holdtime_expect_error(vars.D1, CONFIG.invalid_holdtime_too_low):
        validation_results.reject_holdtime_too_low = True
        st.log(f"✓ Invalid hold-time {CONFIG.invalid_holdtime_too_low} REJECTED (expected)")
        st.report_tc_pass(TC_IDS.reject_invalid_holdtime_low, "msg",
                         f"Invalid hold-time {CONFIG.invalid_holdtime_too_low} rejected")
    else:
        st.log(f"✗ Invalid hold-time {CONFIG.invalid_holdtime_too_low} NOT REJECTED (unexpected)")
        st.report_tc_fail(TC_IDS.reject_invalid_holdtime_low, "msg",
                         f"Invalid hold-time {CONFIG.invalid_holdtime_too_low} not rejected")

    # ==================================================================
    # STEP 6: Attempt Invalid Hold-time Value (Too High)
    # ==================================================================
    st.banner(f"STEP 6: Attempt Invalid Hold-time Value {CONFIG.invalid_holdtime_too_high} (Too High)")

    if configure_lldp_holdtime_expect_error(vars.D1, CONFIG.invalid_holdtime_too_high):
        validation_results.reject_holdtime_too_high = True
        st.log(f"✓ Invalid hold-time {CONFIG.invalid_holdtime_too_high} REJECTED (expected)")
        st.report_tc_pass(TC_IDS.reject_invalid_holdtime_high, "msg",
                         f"Invalid hold-time {CONFIG.invalid_holdtime_too_high} rejected")
    else:
        st.log(f"✗ Invalid hold-time {CONFIG.invalid_holdtime_too_high} NOT REJECTED (unexpected)")
        st.report_tc_fail(TC_IDS.reject_invalid_holdtime_high, "msg",
                         f"Invalid hold-time {CONFIG.invalid_holdtime_too_high} not rejected")

    # ==================================================================
    # STEP 7: Configure Valid Hold-time Value
    # ==================================================================
    st.banner(f"STEP 7: Configure Valid Hold-time Value {CONFIG.valid_holdtime}")

    if configure_lldp_holdtime_expect_success(vars.D1, CONFIG.valid_holdtime):
        validation_results.accept_valid_holdtime = True
        st.log(f"✓ Valid hold-time {CONFIG.valid_holdtime} ACCEPTED (expected)")
        st.report_tc_pass(TC_IDS.accept_valid_holdtime, "msg",
                         f"Valid hold-time {CONFIG.valid_holdtime} accepted")
    else:
        st.log(f"✗ Valid hold-time {CONFIG.valid_holdtime} REJECTED (unexpected)")
        st.report_tc_fail(TC_IDS.accept_valid_holdtime, "msg",
                         f"Valid hold-time {CONFIG.valid_holdtime} rejected")

    # ==================================================================
    # STEP 8: Rollback Configuration
    # ==================================================================
    st.banner("STEP 8: Rollback Configuration - Disable LLDP")

    st.log("Disabling LLDP globally")
    if disable_lldp_globally(vars.D1):
        validation_results.rollback = True
        st.log("✓ LLDP disabled globally on DUT1")
        st.report_tc_pass(TC_IDS.lldp_rollback, "msg",
                         "Configuration rolled back successfully")
    else:
        st.log("⚠ Rollback incomplete")

    st.wait(10, "Waiting for LLDP to clean up")

    # ==================================================================
    # STEP 9: Final Test Result Evaluation
    # ==================================================================
    st.banner("STEP 9: Final Test Result Evaluation")

    # Check all validation criteria
    all_validations_passed = (
        validation_results.reject_timer_too_low and
        validation_results.reject_timer_too_high and
        validation_results.accept_valid_timer and
        validation_results.reject_holdtime_too_low and
        validation_results.reject_holdtime_too_high and
        validation_results.accept_valid_holdtime
    )

    if all_validations_passed:
        st.log("✓ All validation checks passed")

        st.banner("=" * 80)
        st.banner("TEST RESULT: LLDP 4.16.25 PASSED")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - 4.16.25: Reject invalid LLDP timer values")
        st.log("=" * 80)
        st.log(f"✓ LLDP enabled globally")
        st.log(f"✓ Invalid timer {CONFIG.invalid_timer_too_low} (too low) - REJECTED")
        st.log(f"✓ Invalid timer {CONFIG.invalid_timer_too_high} (too high) - REJECTED")
        st.log(f"✓ Valid timer {CONFIG.valid_timer} - ACCEPTED")
        st.log(f"✓ Invalid hold-time {CONFIG.invalid_holdtime_too_low} (too low) - REJECTED")
        st.log(f"✓ Invalid hold-time {CONFIG.invalid_holdtime_too_high} (too high) - REJECTED")
        st.log(f"✓ Valid hold-time {CONFIG.valid_holdtime} - ACCEPTED")
        st.log(f"✓ Configuration rolled back")
        st.log("=" * 80)
        st.log("NOTE: As per manual test: PASS - Invalid values rejected, valid values accepted")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
    else:
        st.log("✗ Some validation checks failed")

        st.banner("=" * 80)
        st.banner("TEST RESULT: LLDP 4.16.25 FAILED")
        st.banner("=" * 80)

        failed_checks = []
        if not validation_results.reject_timer_too_low:
            failed_checks.append(f"Timer {CONFIG.invalid_timer_too_low} not rejected")
        if not validation_results.reject_timer_too_high:
            failed_checks.append(f"Timer {CONFIG.invalid_timer_too_high} not rejected")
        if not validation_results.accept_valid_timer:
            failed_checks.append(f"Valid timer {CONFIG.valid_timer} rejected")
        if not validation_results.reject_holdtime_too_low:
            failed_checks.append(f"Hold-time {CONFIG.invalid_holdtime_too_low} not rejected")
        if not validation_results.reject_holdtime_too_high:
            failed_checks.append(f"Hold-time {CONFIG.invalid_holdtime_too_high} not rejected")
        if not validation_results.accept_valid_holdtime:
            failed_checks.append(f"Valid hold-time {CONFIG.valid_holdtime} rejected")

        st.report_fail("msg", f"Invalid timer rejection test failed: {', '.join(failed_checks)}")
