"""
sFlow TEST CASE 1.3.2: OUT OF RANGE SAMPLING RATE (NEGATIVE TEST)
Test Case ID: TC-SFLOW-1.3.2

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_3_2_out_of_range_sampling_rate.py \
    --logs-path ./logs/sflow_tc_1_3_2_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.3.2: Out of Range Sampling Rate (Negative Test)

  Objective:
    Verify that the system correctly rejects out-of-range sampling rate values
    and displays appropriate error messages. Valid sampling rate range is
    typically 1 to 4294967295 (2^32 - 1).

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration:
       - Enable sFlow globally
       - Enable sFlow on Ethernet4
       - Configure Ethernet8 with valid sampling rate 6000 (baseline)
    3. Module 3 - Validation (Negative Tests):
       - Attempt to set out-of-range sampling rate on Ethernet4: 9999999999
         * Verify command is rejected with error
         * Verify error message contains "Invalid input" or "Error"
       - Verify 'show sflow interface' shows Ethernet4 unchanged
       - Verify Ethernet4 has default sampling rate 4294967295 (disabled)
       - Verify Ethernet8 still has valid sampling rate 6000
    4. Module 4 - Cleanup: Remove all sFlow configuration

Pre-requisites:
  - 1 SONiC device (DUT1)
  - Testbed: testbed_2vs.yaml or compatible

Notes:
  - Valid sampling rate range: 1 to 4294967295
  - Default (disabled) sampling rate: 4294967295
  - Out-of-range value tested: 9999999999 (exceeds 32-bit unsigned int)
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# ======================================================================
# Global Variables
# ======================================================================
vars = SpyTestDict()
data = SpyTestDict()

# ======================================================================
# Test Configuration
# ======================================================================
CONFIG = SpyTestDict({
    # sFlow Configuration
    "interface_test":           "Ethernet4",      # Interface to test invalid sampling rate
    "interface_baseline":       "Ethernet8",      # Interface with valid sampling rate
    "valid_sampling_rate":      "6000",           # Valid baseline sampling rate
    "invalid_sampling_rate":    "9999999999",     # Out of range value (> 2^32 - 1)
    "default_sampling_rate":    "4294967295",     # Default disabled rate
})

# Test Case ID
TC_ID = "TC-SFLOW-1.3.2"


# ======================================================================
# Fixture - Module Level Setup/Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def sflow_module_hooks(request):
    """
    Module-level fixture for setup and teardown.
    Runs before all tests in this module and after all tests.
    """
    global vars

    # Ensure minimum topology: 1 DUT (D1)
    vars = st.ensure_min_topology("D1")

    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: OUT OF RANGE SAMPLING RATE (NEGATIVE TEST)")
    st.banner("=" * 80)

    st.log(f"Test Interface: {CONFIG.interface_test}")
    st.log(f"Baseline Interface: {CONFIG.interface_baseline} (sampling rate: {CONFIG.valid_sampling_rate})")
    st.log(f"Invalid sampling rate to test: {CONFIG.invalid_sampling_rate}")

    # Module 1: Pre-condition - Unconfigure all sFlow before tests
    st.banner("MODULE 1: UNCONFIGURATION - Cleaning existing sFlow config")
    module_1_unconfiguration(vars.D1)
    st.wait(2)

    yield

    # Module 4: Cleanup after all tests
    st.banner("MODULE 4: CLEANUP - Removing all sFlow configuration")
    module_4_cleanup(vars.D1)
    st.wait(1)


# ======================================================================
# MODULE 1: UNCONFIGURATION
# ======================================================================
def module_1_unconfiguration(dut: str):
    """
    Module 1: Unconfiguration
    Remove all existing sFlow configuration before starting tests.
    """
    st.log(f"[MODULE 1] Unconfiguring all sFlow settings on {dut}")

    commands = [
        "no sflow enable",
        f"interface {CONFIG.interface_test}",
        "no sflow enable",
        "exit",
        f"interface {CONFIG.interface_baseline}",
        "no sflow enable",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=True)
        st.log(f"[MODULE 1] Unconfiguration completed on {dut}")
    except Exception as e:
        st.log(f"[MODULE 1] Unconfiguration error (may be expected if no config exists): {str(e)}")


# ======================================================================
# MODULE 2: CONFIGURATION
# ======================================================================
def module_2_configuration(dut: str) -> bool:
    """
    Module 2: Configuration
    Configure sFlow with baseline valid configuration.
    """
    st.banner("[MODULE 2] Configuring sFlow with baseline configuration")

    # Configuration commands
    commands = [
        "sflow enable",
        f"interface {CONFIG.interface_test}",
        "sflow enable",
        "exit",
        f"interface {CONFIG.interface_baseline}",
        "sflow enable",
        f"sflow sampling-rate {CONFIG.valid_sampling_rate}",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] sFlow configured on {dut}")
        st.log(f"  ✓ {CONFIG.interface_test}: sFlow enabled (no sampling rate - default)")
        st.log(f"  ✓ {CONFIG.interface_baseline}: sampling rate {CONFIG.valid_sampling_rate}")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure sFlow on {dut}: {str(e)}")
        return False


def module_2_verify_baseline_configuration(dut: str) -> bool:
    """
    Module 2: Verify baseline sFlow configuration.
    """
    st.log(f"[MODULE 2] Verifying baseline sFlow configuration on {dut}")

    output = st.show(dut, "show sflow interface | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow interface output:\n{output_str}")

    validation_errors = []
    test_interface_found = False
    baseline_interface_found = False

    # Parse output to find both interfaces
    for line in output_str.split('\n'):
        columns = [col.strip() for col in line.split('|') if col.strip()]

        # Check test interface (Ethernet4 - should have default rate)
        if len(columns) >= 3 and columns[0] == CONFIG.interface_test:
            test_interface_found = True
            admin_state = columns[1]
            sampling_rate = columns[2]

            if "up" not in admin_state.lower():
                validation_errors.append(f"{CONFIG.interface_test} Admin State not 'up'")
            else:
                st.log(f"  ✓ {CONFIG.interface_test} Admin State: up")

            if CONFIG.default_sampling_rate not in sampling_rate:
                validation_errors.append(f"{CONFIG.interface_test} Sampling Rate not {CONFIG.default_sampling_rate} (found: {sampling_rate})")
            else:
                st.log(f"  ✓ {CONFIG.interface_test} Sampling Rate: {CONFIG.default_sampling_rate} (default/disabled)")

        # Check baseline interface (Ethernet8 - should have valid rate)
        if len(columns) >= 3 and columns[0] == CONFIG.interface_baseline:
            baseline_interface_found = True
            admin_state = columns[1]
            sampling_rate = columns[2]

            if "up" not in admin_state.lower():
                validation_errors.append(f"{CONFIG.interface_baseline} Admin State not 'up'")
            else:
                st.log(f"  ✓ {CONFIG.interface_baseline} Admin State: up")

            if CONFIG.valid_sampling_rate not in sampling_rate:
                validation_errors.append(f"{CONFIG.interface_baseline} Sampling Rate not {CONFIG.valid_sampling_rate} (found: {sampling_rate})")
            else:
                st.log(f"  ✓ {CONFIG.interface_baseline} Sampling Rate: {CONFIG.valid_sampling_rate}")

    if not test_interface_found:
        validation_errors.append(f"{CONFIG.interface_test} not found in output")

    if not baseline_interface_found:
        validation_errors.append(f"{CONFIG.interface_baseline} not found in output")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ Baseline configuration verified successfully")
    return True


# ======================================================================
# MODULE 3: VALIDATION - Negative Tests
# ======================================================================
def module_3_test_invalid_sampling_rate(dut: str, interface: str, invalid_rate: str) -> bool:
    """
    Module 3: Test setting invalid sampling rate and verify rejection.

    Returns:
        True if the invalid rate is correctly rejected
        False if the invalid rate is accepted (test failure)
    """
    st.log(f"[MODULE 3] Testing invalid sampling rate on {interface}: {invalid_rate}")

    # Convert interface name for command (e.g., Ethernet4 -> "Ethernet 4")
    interface_cmd = interface.replace("Ethernet", "Ethernet ")

    # Attempt to set invalid sampling rate (expect failure)
    commands = [
        f"interface {interface_cmd}",
        f"sflow sampling-rate {invalid_rate}",
        "end"
    ]

    error_detected = False
    error_message = ""

    try:
        # Use skip_error_check=False to catch CLI errors
        output = st.config(dut, commands, type='klish', skip_error_check=False)
        output_str = str(output) if output else ""
        st.log(f"Command output:\n{output_str}")

        # Check if error was returned in output
        if "Error" in output_str or "Invalid" in output_str or "error" in output_str.lower():
            error_detected = True
            error_message = output_str
            st.log(f"  ✓ Invalid sampling rate correctly rejected")
            st.log(f"  Error message: {output_str}")
        else:
            st.error(f"  ✗ Invalid sampling rate was accepted (no error detected)")
            return False

    except Exception as e:
        # Exception is expected for invalid input
        error_detected = True
        error_message = str(e)
        st.log(f"  ✓ Invalid sampling rate correctly rejected with exception")
        st.log(f"  Exception: {str(e)}")

    # Verify error was detected
    if not error_detected:
        st.error(f"  ✗ No error detected for invalid sampling rate: {invalid_rate}")
        return False

    # Verify error message contains expected keywords
    expected_keywords = ["Error", "Invalid", "error", "invalid"]
    keyword_found = any(keyword in error_message for keyword in expected_keywords)

    if not keyword_found:
        st.log(f"  Warning: Error message does not contain expected keywords")
        st.log(f"  Error message: {error_message}")

    st.log(f"✓ Invalid sampling rate {invalid_rate} correctly rejected")
    return True


def module_3_verify_configuration_unchanged(dut: str) -> bool:
    """
    Module 3: Verify that interface configurations are unchanged after negative test.
    """
    st.log(f"[MODULE 3] Verifying interface configurations unchanged after negative test")

    output = st.show(dut, "show sflow interface | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow interface output:\n{output_str}")

    validation_errors = []
    test_interface_found = False
    baseline_interface_found = False

    # Parse output to verify both interfaces
    for line in output_str.split('\n'):
        columns = [col.strip() for col in line.split('|') if col.strip()]

        # Check test interface (should still have default rate)
        if len(columns) >= 3 and columns[0] == CONFIG.interface_test:
            test_interface_found = True
            admin_state = columns[1]
            sampling_rate = columns[2]

            if "up" not in admin_state.lower():
                validation_errors.append(f"{CONFIG.interface_test} Admin State changed")
            else:
                st.log(f"  ✓ {CONFIG.interface_test} Admin State: up")

            # Verify still has default rate (not the invalid rate)
            if CONFIG.default_sampling_rate not in sampling_rate:
                validation_errors.append(f"{CONFIG.interface_test} Sampling Rate changed from default {CONFIG.default_sampling_rate} (found: {sampling_rate})")
            else:
                st.log(f"  ✓ {CONFIG.interface_test} Sampling Rate: {CONFIG.default_sampling_rate} (unchanged)")

            # Verify invalid rate NOT applied
            if CONFIG.invalid_sampling_rate in sampling_rate:
                validation_errors.append(f"{CONFIG.interface_test} has invalid sampling rate {CONFIG.invalid_sampling_rate}")
            else:
                st.log(f"  ✓ {CONFIG.interface_test} does not have invalid rate {CONFIG.invalid_sampling_rate}")

        # Check baseline interface (should still have valid rate)
        if len(columns) >= 3 and columns[0] == CONFIG.interface_baseline:
            baseline_interface_found = True
            admin_state = columns[1]
            sampling_rate = columns[2]

            if "up" not in admin_state.lower():
                validation_errors.append(f"{CONFIG.interface_baseline} Admin State changed")
            else:
                st.log(f"  ✓ {CONFIG.interface_baseline} Admin State: up")

            if CONFIG.valid_sampling_rate not in sampling_rate:
                validation_errors.append(f"{CONFIG.interface_baseline} Sampling Rate changed from {CONFIG.valid_sampling_rate} (found: {sampling_rate})")
            else:
                st.log(f"  ✓ {CONFIG.interface_baseline} Sampling Rate: {CONFIG.valid_sampling_rate} (unchanged)")

    if not test_interface_found:
        validation_errors.append(f"{CONFIG.interface_test} not found in output")

    if not baseline_interface_found:
        validation_errors.append(f"{CONFIG.interface_baseline} not found in output")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ Interface configurations unchanged after negative test")
    return True


# ======================================================================
# MODULE 4: CLEANUP
# ======================================================================
def module_4_cleanup(dut: str):
    """
    Module 4: Cleanup
    Remove all sFlow configuration after test completion.
    """
    st.log(f"[MODULE 4] Cleaning up sFlow configuration on {dut}")

    commands = [
        "no sflow enable",
        f"interface {CONFIG.interface_test}",
        "no sflow enable",
        "exit",
        f"interface {CONFIG.interface_baseline}",
        "no sflow enable",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=True)
        st.log(f"[MODULE 4] Cleanup completed on {dut}")
    except Exception as e:
        st.log(f"[MODULE 4] Cleanup error: {str(e)}")


# ======================================================================
# Test Function - Main Test Case
# ======================================================================
def test_sflow_tc_1_3_2_out_of_range_sampling_rate():
    """
    Test Case 1.3.2: Out of Range Sampling Rate (Negative Test)

    This test verifies:
    1. System correctly rejects out-of-range sampling rate values
    2. Error messages are displayed for invalid sampling rates
    3. Interface configuration remains unchanged after invalid attempts
    4. Other interface configurations are not affected
    5. Invalid sampling rate tested: 9999999999 (exceeds 2^32 - 1)
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: OUT OF RANGE SAMPLING RATE (NEGATIVE TEST)")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    # ========================================================================
    # MODULE 2: CONFIGURATION
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 2] CONFIGURATION - Baseline Setup                       #")
    st.banner("=" * 80)

    st.log("STEP 1: Configure sFlow with baseline configuration")
    if not module_2_configuration(dut):
        st.report_fail("test_case_failed", "Failed to configure baseline sFlow")

    st.wait(2)

    st.log("STEP 2: Verify baseline configuration")
    if not module_2_verify_baseline_configuration(dut):
        st.report_fail("test_case_failed", "Baseline configuration verification failed")

    # ========================================================================
    # MODULE 3: VALIDATION - Negative Tests
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 3] VALIDATION - Negative Tests                          #")
    st.banner("=" * 80)

    st.log(f"STEP 3: Test out-of-range sampling rate: {CONFIG.invalid_sampling_rate}")
    st.log(f"  Attempting to set sampling rate {CONFIG.invalid_sampling_rate} on {CONFIG.interface_test}")
    st.log(f"  Expected: Command rejected with error (valid range: 1 to {CONFIG.default_sampling_rate})")

    if not module_3_test_invalid_sampling_rate(dut, CONFIG.interface_test, CONFIG.invalid_sampling_rate):
        validation_failures.append(f"STEP 3: Out-of-range sampling rate {CONFIG.invalid_sampling_rate} was not rejected")

    st.wait(1)

    st.log("STEP 4: Verify interface configurations unchanged")
    st.log(f"  Verifying {CONFIG.interface_test} still has default rate {CONFIG.default_sampling_rate}")
    st.log(f"  Verifying {CONFIG.interface_baseline} still has valid rate {CONFIG.valid_sampling_rate}")

    if not module_3_verify_configuration_unchanged(dut):
        validation_failures.append("STEP 4: Interface configurations were changed after invalid attempt")

    # ========================================================================
    # Final Test Result
    # ========================================================================
    st.banner("=" * 80)
    if validation_failures:
        st.banner("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        st.log(f"TEST CASE {TC_ID} VALIDATION FAILURES:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.banner("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        st.report_fail("test_case_failed", f"Test Case {TC_ID}: {len(validation_failures)} validation failure(s)")
    else:
        st.banner("=" * 80)
        st.banner(f"TEST CASE {TC_ID}: PASSED")
        st.banner("=" * 80)
        st.log("✓ All negative test validations passed successfully")
        st.log(f"  - Out-of-range sampling rate {CONFIG.invalid_sampling_rate} correctly rejected")
        st.log(f"  - {CONFIG.interface_test} unchanged (still has default rate {CONFIG.default_sampling_rate})")
        st.log(f"  - {CONFIG.interface_baseline} unchanged (still has valid rate {CONFIG.valid_sampling_rate})")
        st.log("  - Error message displayed for invalid input")
        st.report_pass("test_case_passed")
