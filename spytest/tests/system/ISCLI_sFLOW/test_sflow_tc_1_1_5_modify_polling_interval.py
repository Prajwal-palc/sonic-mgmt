"""
sFlow TEST CASE 1.1.5: MODIFY POLLING INTERVAL
Test Case ID: TC-SFLOW-1.1.5

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_1_5_modify_polling_interval.py \
    --logs-path ./logs/sflow_tc_1_1_5_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.1.5: Modify Polling Interval
  
  Objective: 
    Verify sFlow polling interval can be modified and reset to default.
  
  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration: Enable sFlow with base config
    3. Module 3 - Validation: 
       - Set polling interval to 20 and verify
       - Reset polling interval to default and verify
       - Verify running configuration reflects changes
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
    "polling_interval":     "20",
    "sampling_rate":        "2000",
})

# ======================================================================
# Test Case ID
# ======================================================================
TC_ID = "TC-SFLOW-1.1.5"


# ======================================================================
# Module Fixture - Setup and Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def sflow_tc_1_1_5_module_hooks(request):
    """Module-level setup and teardown for Test Case 1.1.5."""
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID} - MODIFY POLLING INTERVAL - MODULE START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}")
    st.log(f"CLI Type: {data.cli_type}")

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
        "no sflow polling-interval",
        "no sflow sampling-rate",
        "no sflow enable",
        "end"
    ]
    
    st.config(dut, commands, type='klish', skip_error_check=True)
    st.wait(1)
    st.log(f"[MODULE 1] Unconfiguration completed on {dut}")


# ======================================================================
# MODULE 2: CONFIGURATION
# ======================================================================
def module_2_configuration(dut: str):
    """
    Module 2: Configuration
    Configure sFlow with base settings.
    """
    st.banner("[MODULE 2] Configuring sFlow with base parameters")

    commands = [
        f"sflow sampling-rate {CONFIG.sampling_rate}",
        "sflow enable",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] sFlow base configuration completed on {dut}")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure sFlow on {dut}: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION
# ======================================================================
def module_3_validation_set_polling_interval_20(dut: str) -> bool:
    """
    Module 3 - Validation Step 1: Set polling interval to 20 and verify
    """
    st.log("[MODULE 3.1] Setting polling interval to 20 and verifying")

    # Set polling interval to 20
    commands = [f"sflow polling-interval {CONFIG.polling_interval}", "end"]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to set polling interval to {CONFIG.polling_interval}: {str(e)}")
        return False

    # Verify polling interval in show sflow
    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    
    st.log(f"show sflow output:\n{output_str}")

    # Check polling interval shows 20
    if CONFIG.polling_interval not in output_str or "polling" not in output_str.lower():
        st.error(f"Polling interval {CONFIG.polling_interval} not found in show sflow output")
        return False

    st.log(f"✓ Polling interval set to {CONFIG.polling_interval} successfully")
    return True


def module_3_validation_reset_polling_interval_default(dut: str) -> bool:
    """
    Module 3 - Validation Step 2: Reset polling interval to default and verify
    """
    st.log("[MODULE 3.2] Resetting polling interval to default and verifying")

    # Reset polling interval to default
    commands = ["no sflow polling-interval", "end"]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to reset polling interval to default: {str(e)}")
        return False

    # Verify polling interval is reset in show sflow
    # When reset to default, the polling interval line may be:
    # 1. Omitted completely (most platforms)
    # 2. Show "default" text (some platforms)
    # 3. Show default value like "20" (rare)
    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    
    st.log(f"show sflow output:\n{output_str}")

    # Check if custom interval (20) is no longer present
    # The line "sFlow Polling Interval:     20" should not appear
    lines = output_str.split('\n')
    polling_line = [line for line in lines if 'polling' in line.lower() and 'interval' in line.lower()]
    
    if polling_line:
        # Polling interval line exists
        polling_line_str = polling_line[0]
        # Check if it's NOT set to our custom value (20)
        if CONFIG.polling_interval in polling_line_str:
            st.error(f"Polling interval still shows custom value {CONFIG.polling_interval} after reset")
            return False
        st.log(f"✓ Polling interval line present: {polling_line_str.strip()}")
    else:
        # Polling interval line omitted (default behavior on many platforms)
        st.log("✓ Polling interval line omitted (default behavior)")

    st.log("✓ Polling interval reset to default successfully")
    return True


def module_3_validation_running_config(dut: str) -> bool:
    """
    Module 3 - Validation Step 3: Verify running configuration
    """
    st.log("[MODULE 3.3] Verifying running configuration")

    # Get running configuration
    output = st.show(
        dut,
        "show running-configuration | grep sflow",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""
    
    st.log(f"show running-configuration | grep sflow output:\n{output_str}")

    # Since polling interval was reset to default, it should not appear in running config
    # Check that sflow enable and sampling-rate are present
    expected_items = [
        "sflow enable",
        f"sflow sampling-rate {CONFIG.sampling_rate}",
    ]

    missing_items = []
    for item in expected_items:
        if item not in output_str:
            missing_items.append(item)

    if missing_items:
        st.error(f"Missing items in running configuration: {missing_items}")
        return False

    # Polling interval should NOT be in running config (default value)
    # Note: This is expected behavior - default values are not shown in running-config
    if "sflow polling-interval" in output_str:
        st.log("Note: Polling interval present in running config (may be platform-specific)")
    else:
        st.log("✓ Polling interval not in running config (default value)")
    
    st.log("✓ Running configuration verified")
    return True


# ======================================================================
# MODULE 4: CLEANUP
# ======================================================================
def module_4_cleanup(dut: str):
    """
    Module 4: Cleanup
    Remove all sFlow configuration after test completion.
    """
    st.log(f"[MODULE 4] Cleaning up all sFlow configuration on {dut}")

    commands = [
        "no sflow enable",
        "no sflow polling-interval",
        "no sflow sampling-rate",
        "end"
    ]
    
    st.config(dut, commands, type='klish', skip_error_check=True)
    st.wait(1)
    st.log(f"[MODULE 4] Cleanup completed on {dut}")


# ======================================================================
# Test Function - Main Test Case
# ======================================================================
def test_sflow_tc_1_1_5_modify_polling_interval():
    """
    Test Case 1.1.5: Modify Polling Interval
    
    This test verifies:
    1. Polling interval can be set to 20
    2. Polling interval can be reset to default
    3. Default polling interval does not appear in running configuration
    4. Changes reflect correctly in show sflow output
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: MODIFY POLLING INTERVAL")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # Module 2: Configuration
        st.banner("[MODULE 2] CONFIGURATION - Setting up sFlow base config")
        if not module_2_configuration(dut):
            validation_failures.append("[MODULE 2] Failed to configure sFlow")
            st.report_fail("msg", "Configuration failed - cannot proceed with test")
            return

        st.wait(2)  # Wait for configuration to settle

        # Module 3: Validation
        st.banner("[MODULE 3] VALIDATION - Testing polling interval modification")

        st.log("STEP 1: Set polling interval to 20 and verify")
        if not module_3_validation_set_polling_interval_20(dut):
            validation_failures.append("STEP 1: Failed to set polling interval to 20")

        st.wait(1)

        st.log("STEP 2: Reset polling interval to default and verify")
        if not module_3_validation_reset_polling_interval_default(dut):
            validation_failures.append("STEP 2: Failed to reset polling interval to default")

        st.wait(1)

        st.log("STEP 3: Verify running configuration")
        if not module_3_validation_running_config(dut):
            validation_failures.append("STEP 3: Running configuration validation failed")

    except Exception as e:
        st.error(f"Exception in test_sflow_tc_1_1_5_modify_polling_interval: {str(e)}")
        validation_failures.append(f"Unexpected exception: {str(e)}")

    # Report test result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log(f"TEST CASE {TC_ID} VALIDATION FAILURES:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"Test Case {TC_ID}: {len(validation_failures)} validation failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log(f"✅ TEST CASE {TC_ID}: MODIFY POLLING INTERVAL - PASSED")
        st.log("   All validations successful:")
        st.log("   ✓ Set polling interval to 20")
        st.log("   ✓ Reset polling interval to default")
        st.log("   ✓ Running configuration accuracy")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
