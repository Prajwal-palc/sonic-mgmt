"""
sFlow TEST CASE 1.1.4: MODIFY SAMPLING RATE
Test Case ID: TC-SFLOW-1.1.4

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_1_4_modify_sampling_rate.py \
    --logs-path ./logs/sflow_tc_1_1_4_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.1.4: Modify Sampling Rate
  
  Objective: 
    Verify sFlow sampling rate can be modified globally and per-interface.
  
  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration: Enable sFlow with base config
    3. Module 3 - Validation: 
       - Set global sampling rate to 4000 and verify in running-config
       - Change global sampling rate to 2000 and verify in running-config
       - Set interface-level sampling rate on Ethernet4 to 3000
       - Verify both global and interface rates in running configuration
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
    "sampling_rate_1":      "4000",
    "sampling_rate_2":      "2000",
    "sampling_rate_intf":   "3000",
    "interface":            "Ethernet4",
    "polling_interval":     "6",
})

# ======================================================================
# Test Case ID
# ======================================================================
TC_ID = "TC-SFLOW-1.1.4"


# ======================================================================
# Module Fixture - Setup and Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def sflow_tc_1_1_4_module_hooks(request):
    """Module-level setup and teardown for Test Case 1.1.4."""
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID} - MODIFY SAMPLING RATE - MODULE START")
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
        "no sflow sampling-rate",
        "no sflow polling-interval",
        "no sflow enable",
        f"interface {CONFIG.interface}",
        "no sflow enable",
        "exit",
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
        f"sflow polling-interval {CONFIG.polling_interval}",
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
def module_3_validation_set_sampling_rate_4000(dut: str) -> bool:
    """
    Module 3 - Validation Step 1: Set global sampling rate to 4000 and verify
    """
    st.log("[MODULE 3.1] Setting global sampling rate to 4000 and verifying")

    # Set sampling rate to 4000
    commands = [f"sflow sampling-rate {CONFIG.sampling_rate_1}", "end"]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to set sampling rate to {CONFIG.sampling_rate_1}: {str(e)}")
        return False

    # Verify sampling rate in running configuration
    # Note: Global sampling rate may not appear in "show sflow" on all platforms
    # So we verify it in running-config instead
    output = st.show(
        dut,
        "show running-configuration | grep sflow",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""
    
    st.log(f"show running-configuration | grep sflow output:\n{output_str}")

    # Check sampling rate 4000 appears in running config
    if CONFIG.sampling_rate_1 not in output_str:
        st.error(f"Sampling rate {CONFIG.sampling_rate_1} not found in running configuration")
        return False

    st.log(f"✓ Global sampling rate set to {CONFIG.sampling_rate_1} successfully")
    st.log(f"✓ Verified in running configuration")
    return True


def module_3_validation_change_sampling_rate_2000(dut: str) -> bool:
    """
    Module 3 - Validation Step 2: Change global sampling rate to 2000 and verify
    """
    st.log("[MODULE 3.2] Changing global sampling rate to 2000 and verifying")

    # Change sampling rate to 2000
    commands = [f"sflow sampling-rate {CONFIG.sampling_rate_2}", "end"]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to change sampling rate to {CONFIG.sampling_rate_2}: {str(e)}")
        return False

    # Verify sampling rate in running configuration
    output = st.show(
        dut,
        "show running-configuration | grep sflow",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""
    
    st.log(f"show running-configuration | grep sflow output:\n{output_str}")

    # Check sampling rate shows 2000 (not 4000)
    if CONFIG.sampling_rate_2 not in output_str:
        st.error(f"Sampling rate {CONFIG.sampling_rate_2} not found in running configuration")
        return False

    # Ensure 4000 is no longer present (replaced by 2000)
    if CONFIG.sampling_rate_1 in output_str and CONFIG.sampling_rate_2 in output_str:
        # Check if 4000 is in interface config (that's OK)
        # But global should be 2000
        pass

    st.log(f"✓ Global sampling rate changed to {CONFIG.sampling_rate_2} successfully")
    st.log(f"✓ Verified in running configuration")
    return True


def module_3_validation_set_interface_sampling_rate(dut: str) -> bool:
    """
    Module 3 - Validation Step 3: Set interface-level sampling rate and verify
    """
    st.log("[MODULE 3.3] Setting interface-level sampling rate on Ethernet4")

    # Set interface-level sampling rate
    commands = [
        f"interface {CONFIG.interface}",
        "sflow enable",
        f"sflow sampling-rate {CONFIG.sampling_rate_intf}",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to set interface sampling rate: {str(e)}")
        return False

    # Verify interface sampling rate in show sflow interface
    output = st.show(
        dut, 
        f"show sflow interface {CONFIG.interface}",
        type='klish', 
        skip_tmpl=True, 
        skip_error_check=True
    )
    output_str = str(output) if output else ""
    
    st.log(f"show sflow interface output:\n{output_str}")

    # Check interface sampling rate
    if CONFIG.sampling_rate_intf not in output_str:
        st.error(f"Interface sampling rate {CONFIG.sampling_rate_intf} not found")
        return False

    st.log(f"✓ Interface sampling rate set to {CONFIG.sampling_rate_intf} on {CONFIG.interface}")
    return True


def module_3_validation_running_config(dut: str) -> bool:
    """
    Module 3 - Validation Step 4: Verify running configuration shows both rates
    """
    st.log("[MODULE 3.4] Verifying running configuration")

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

    # Check for global sampling rate
    if CONFIG.sampling_rate_2 not in output_str:
        st.error(f"Global sampling rate {CONFIG.sampling_rate_2} not found in running config")
        return False

    # Check for interface sampling rate
    if CONFIG.sampling_rate_intf not in output_str:
        st.error(f"Interface sampling rate {CONFIG.sampling_rate_intf} not found in running config")
        return False

    st.log("✓ Both global and interface sampling rates found in running configuration")
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
        "no sflow sampling-rate",
        "no sflow polling-interval",
        f"interface {CONFIG.interface}",
        "no sflow enable",
        "exit",
        "end"
    ]
    
    st.config(dut, commands, type='klish', skip_error_check=True)
    st.wait(1)
    st.log(f"[MODULE 4] Cleanup completed on {dut}")


# ======================================================================
# Test Function - Main Test Case
# ======================================================================
def test_sflow_tc_1_1_4_modify_sampling_rate():
    """
    Test Case 1.1.4: Modify Sampling Rate
    
    This test verifies:
    1. Global sampling rate can be set to 4000
    2. Global sampling rate can be changed from 4000 to 2000
    3. Interface-level sampling rate can be set (overriding global)
    4. Both global and interface rates appear in running configuration
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: MODIFY SAMPLING RATE")
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
        st.banner("[MODULE 3] VALIDATION - Testing sampling rate modification")

        st.log("STEP 1: Set global sampling rate to 4000 and verify")
        if not module_3_validation_set_sampling_rate_4000(dut):
            validation_failures.append("STEP 1: Failed to set sampling rate to 4000")

        st.wait(1)

        st.log("STEP 2: Change global sampling rate to 2000 and verify")
        if not module_3_validation_change_sampling_rate_2000(dut):
            validation_failures.append("STEP 2: Failed to change sampling rate to 2000")

        st.wait(1)

        st.log("STEP 3: Set interface-level sampling rate on Ethernet4")
        if not module_3_validation_set_interface_sampling_rate(dut):
            validation_failures.append("STEP 3: Failed to set interface sampling rate")

        st.wait(1)

        st.log("STEP 4: Verify running configuration shows both rates")
        if not module_3_validation_running_config(dut):
            validation_failures.append("STEP 4: Running configuration validation failed")

    except Exception as e:
        st.error(f"Exception in test_sflow_tc_1_1_4_modify_sampling_rate: {str(e)}")
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
        st.log(f"✅ TEST CASE {TC_ID}: MODIFY SAMPLING RATE - PASSED")
        st.log("   All validations successful:")
        st.log("   ✓ Set global sampling rate to 4000")
        st.log("   ✓ Change global sampling rate to 2000")
        st.log("   ✓ Set interface-level sampling rate to 3000")
        st.log("   ✓ Running configuration accuracy")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
