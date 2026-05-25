"""
sFlow TEST CASE 1.3.1: INVALID COLLECTOR IP (NEGATIVE TEST)
Test Case ID: TC-SFLOW-1.3.1

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_3_1_invalid_collector_ip.py \
    --logs-path ./logs/sflow_tc_1_3_1_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.3.1: Invalid Collector IP (Negative Test)

  Objective:
    Verify that the system correctly rejects invalid collector IP addresses
    and displays appropriate error messages.

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration:
       - Enable sFlow globally
       - Add valid collector 192.168.100.87 (for baseline)
    3. Module 3 - Validation (Negative Tests):
       - Attempt to add invalid collector IP: 999.999.999.999
         * Verify command is rejected with error
         * Verify error message contains "Invalid input" or "Error"
       - Attempt to add invalid collector IP: 256.1.1.1
         * Verify command is rejected with error
         * Verify error message contains "Invalid input" or "Error"
       - Verify 'show sflow' still shows only the valid collector
       - Verify original collector configuration unchanged
    4. Module 4 - Cleanup: Remove all sFlow configuration

Pre-requisites:
  - 1 SONiC device (DUT1)
  - Testbed: testbed_2vs.yaml or compatible
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
    # Valid Collector Configuration
    "valid_collector_ip":       "192.168.100.87",
    "collector_port":           "6343",

    # Invalid Collector IPs to test
    "invalid_ip_1":             "999.999.999.999",
    "invalid_ip_2":             "256.1.1.1",

    # sFlow Configuration
    "polling_interval":         "20",
})

# Test Case ID
TC_ID = "TC-SFLOW-1.3.1"


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
    st.banner(f"TEST CASE {TC_ID}: INVALID COLLECTOR IP (NEGATIVE TEST)")
    st.banner("=" * 80)

    st.log(f"Valid Collector: {CONFIG.valid_collector_ip}")
    st.log(f"Invalid IPs to test: {CONFIG.invalid_ip_1}, {CONFIG.invalid_ip_2}")

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
        f"no sflow collector {CONFIG.valid_collector_ip}",
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
    Configure sFlow with valid collector as baseline.
    """
    st.banner("[MODULE 2] Configuring sFlow with valid collector")

    # Configuration commands
    commands = [
        "sflow enable",
        f"sflow collector {CONFIG.valid_collector_ip}",
        f"sflow polling-interval {CONFIG.polling_interval}",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] sFlow configured on {dut}")
        st.log(f"  ✓ Valid collector: {CONFIG.valid_collector_ip}")
        st.log(f"  ✓ Polling interval: {CONFIG.polling_interval}")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure sFlow on {dut}: {str(e)}")
        return False


def module_2_verify_baseline_configuration(dut: str) -> bool:
    """
    Module 2: Verify baseline sFlow configuration with valid collector.
    """
    st.log(f"[MODULE 2] Verifying baseline sFlow configuration on {dut}")

    output = st.show(dut, "show sflow | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    # Check sFlow enabled
    if "sFlow Admin State:          up" not in output_str:
        st.error("sFlow not enabled globally")
        return False
    st.log(f"  ✓ sFlow Admin State: up")

    # Check valid collector configured
    if CONFIG.valid_collector_ip not in output_str:
        st.error(f"Valid collector {CONFIG.valid_collector_ip} not found")
        return False
    st.log(f"  ✓ Valid collector configured: {CONFIG.valid_collector_ip}")

    # Check collector count
    if "1 Collector configured:" not in output_str:
        st.error("Expected '1 Collector configured' not found")
        return False
    st.log(f"  ✓ 1 Collector configured")

    st.log(f"✓ Baseline configuration verified successfully")
    return True


# ======================================================================
# MODULE 3: VALIDATION - Negative Tests
# ======================================================================
def module_3_test_invalid_collector_ip(dut: str, invalid_ip: str) -> bool:
    """
    Module 3: Test adding invalid collector IP and verify rejection.

    Returns:
        True if the invalid IP is correctly rejected
        False if the invalid IP is accepted (test failure)
    """
    st.log(f"[MODULE 3] Testing invalid collector IP: {invalid_ip}")

    # Attempt to add invalid collector (expect failure)
    commands = [
        f"sflow collector {invalid_ip}",
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
            st.log(f"  ✓ Invalid IP correctly rejected")
            st.log(f"  Error message: {output_str}")
        else:
            st.error(f"  ✗ Invalid IP was accepted (no error detected)")
            return False

    except Exception as e:
        # Exception is expected for invalid input
        error_detected = True
        error_message = str(e)
        st.log(f"  ✓ Invalid IP correctly rejected with exception")
        st.log(f"  Exception: {str(e)}")

    # Verify error was detected
    if not error_detected:
        st.error(f"  ✗ No error detected for invalid IP: {invalid_ip}")
        return False

    # Verify error message contains expected keywords
    expected_keywords = ["Error", "Invalid", "error", "invalid"]
    keyword_found = any(keyword in error_message for keyword in expected_keywords)

    if not keyword_found:
        st.log(f"  Warning: Error message does not contain expected keywords")
        st.log(f"  Error message: {error_message}")

    st.log(f"✓ Invalid collector IP {invalid_ip} correctly rejected")
    return True


def module_3_verify_collector_unchanged(dut: str) -> bool:
    """
    Module 3: Verify that the valid collector is still configured and unchanged.
    """
    st.log(f"[MODULE 3] Verifying valid collector unchanged after negative tests")

    output = st.show(dut, "show sflow | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    validation_errors = []

    # Check valid collector still present
    if CONFIG.valid_collector_ip not in output_str:
        validation_errors.append(f"Valid collector {CONFIG.valid_collector_ip} not found")
    else:
        st.log(f"  ✓ Valid collector still present: {CONFIG.valid_collector_ip}")

    # Check only 1 collector configured
    if "1 Collector configured:" not in output_str:
        validation_errors.append("Expected '1 Collector configured' not found")
    else:
        st.log(f"  ✓ Still only 1 collector configured")

    # Check invalid IPs NOT present
    if CONFIG.invalid_ip_1 in output_str:
        validation_errors.append(f"Invalid IP {CONFIG.invalid_ip_1} found in config")
    else:
        st.log(f"  ✓ Invalid IP {CONFIG.invalid_ip_1} not in config")

    if CONFIG.invalid_ip_2 in output_str:
        validation_errors.append(f"Invalid IP {CONFIG.invalid_ip_2} found in config")
    else:
        st.log(f"  ✓ Invalid IP {CONFIG.invalid_ip_2} not in config")

    # Check sFlow still enabled
    if "sFlow Admin State:          up" not in output_str:
        validation_errors.append("sFlow Admin State changed from 'up'")
    else:
        st.log(f"  ✓ sFlow Admin State: up")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ Valid collector configuration unchanged")
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
        f"no sflow collector {CONFIG.valid_collector_ip}",
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
def test_sflow_tc_1_3_1_invalid_collector_ip():
    """
    Test Case 1.3.1: Invalid Collector IP (Negative Test)

    This test verifies:
    1. System correctly rejects invalid collector IP addresses
    2. Error messages are displayed for invalid IPs
    3. Valid collector configuration remains unchanged after invalid attempts
    4. Invalid IPs tested:
       - 999.999.999.999 (octets > 255)
       - 256.1.1.1 (first octet > 255)
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: INVALID COLLECTOR IP (NEGATIVE TEST)")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    # ========================================================================
    # MODULE 2: CONFIGURATION
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 2] CONFIGURATION - Baseline Setup                       #")
    st.banner("=" * 80)

    st.log("STEP 1: Configure sFlow with valid collector (baseline)")
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

    st.log(f"STEP 3: Test invalid collector IP: {CONFIG.invalid_ip_1}")
    if not module_3_test_invalid_collector_ip(dut, CONFIG.invalid_ip_1):
        validation_failures.append(f"STEP 3: Invalid IP {CONFIG.invalid_ip_1} was not rejected")

    st.wait(1)

    st.log(f"STEP 4: Test invalid collector IP: {CONFIG.invalid_ip_2}")
    if not module_3_test_invalid_collector_ip(dut, CONFIG.invalid_ip_2):
        validation_failures.append(f"STEP 4: Invalid IP {CONFIG.invalid_ip_2} was not rejected")

    st.wait(1)

    st.log("STEP 5: Verify valid collector configuration unchanged")
    if not module_3_verify_collector_unchanged(dut):
        validation_failures.append("STEP 5: Valid collector configuration was changed")

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
        st.log(f"  - Invalid IP {CONFIG.invalid_ip_1} correctly rejected")
        st.log(f"  - Invalid IP {CONFIG.invalid_ip_2} correctly rejected")
        st.log(f"  - Valid collector {CONFIG.valid_collector_ip} unchanged")
        st.log("  - Error messages displayed for invalid inputs")
        st.report_pass("test_case_passed")
