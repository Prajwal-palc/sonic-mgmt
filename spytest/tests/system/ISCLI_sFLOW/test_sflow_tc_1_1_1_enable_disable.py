"""
sFlow TEST CASE 1.1.1: ENABLE AND DISABLE SFLOW GLOBALLY
Test Case ID: TC-SFLOW-1.1.1

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_1_1_enable_disable.py \
    --logs-path ./logs/sflow_tc_1_1_1_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.1.1: Enable and Disable sFlow Globally
  
  Objective: 
    Verify sFlow can be enabled and disabled globally, and verify that
    configuration persists correctly in running configuration.
  
  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration: Enable sFlow and configure collectors
    3. Module 3 - Validation: 
       - Enable sFlow globally and verify admin state is "up"
       - Verify collectors, agent-id, polling-interval in show sflow
       - Disable sFlow globally and verify admin state is "down"
       - Verify collectors remain in config even when disabled
       - Re-enable sFlow and verify admin state is "up"
       - Verify running configuration contains sflow commands
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
    "collector_ip_v4":      "192.168.100.87",
    "collector_ip_v6":      "2001:db8::10",
    "agent_id":             "Ethernet4",
    "polling_interval":     "6",
    "sampling_rate":        "1234",
})

# ======================================================================
# Test Case ID
# ======================================================================
TC_ID = "TC-SFLOW-1.1.1"


# ======================================================================
# Module Fixture - Setup and Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def sflow_tc_1_1_1_module_hooks(request):
    """Module-level setup and teardown for Test Case 1.1.1."""
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID} - ENABLE AND DISABLE SFLOW GLOBALLY - MODULE START")
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
        "no sflow collector 192.168.100.87",
        "no sflow collector 2001:db8::10",
        "no sflow agent-id",
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
    Configure sFlow with collectors, agent-id, polling-interval, etc.
    This sets up the base configuration for testing enable/disable.
    """
    st.banner("[MODULE 2] Configuring sFlow with collectors and parameters")

    commands = [
        f"sflow collector {CONFIG.collector_ip_v4}",
        f"sflow collector {CONFIG.collector_ip_v6}",
        f"sflow agent-id {CONFIG.agent_id}",
        f"sflow polling-interval {CONFIG.polling_interval}",
        f"sflow sampling-rate {CONFIG.sampling_rate}",
        "sflow enable",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] sFlow configuration completed on {dut}")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure sFlow on {dut}: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION
# ======================================================================
def module_3_validation_enable_sflow(dut: str) -> bool:
    """
    Module 3 - Validation Step 1: Enable sFlow and verify admin state is UP
    """
    st.log("[MODULE 3.1] Enabling sFlow and verifying admin state")

    # Enable sFlow
    commands = ["sflow enable", "end"]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to enable sFlow: {str(e)}")
        return False

    # Verify admin state is UP
    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    
    st.log(f"show sflow output:\n{output_str}")

    # Check for admin state UP
    if "admin state" in output_str.lower() and "up" not in output_str.lower():
        st.error("sFlow admin state is not UP after enable")
        return False

    # Verify expected configuration items are present
    expected_items = [
        CONFIG.collector_ip_v4,
        CONFIG.collector_ip_v6,
        CONFIG.agent_id,
        CONFIG.polling_interval,
    ]

    missing_items = []
    for item in expected_items:
        if item not in output_str:
            missing_items.append(item)

    if missing_items:
        st.error(f"Missing items in show sflow output: {missing_items}")
        return False

    st.log("✓ sFlow enabled successfully and admin state is UP")
    st.log("✓ Collectors and configuration parameters verified")
    return True


def module_3_validation_disable_sflow(dut: str) -> bool:
    """
    Module 3 - Validation Step 2: Disable sFlow and verify admin state is DOWN
    """
    st.log("[MODULE 3.2] Disabling sFlow and verifying admin state")

    # Disable sFlow
    commands = ["no sflow enable", "end"]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to disable sFlow: {str(e)}")
        return False

    # Verify admin state is DOWN
    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    
    st.log(f"show sflow output:\n{output_str}")

    # Check for admin state DOWN
    if "admin state" in output_str.lower() and "down" not in output_str.lower():
        st.error("sFlow admin state is not DOWN after disable")
        return False

    # Verify collectors still exist in configuration (even when disabled)
    if CONFIG.collector_ip_v4 not in output_str or CONFIG.collector_ip_v6 not in output_str:
        st.error("Collectors missing from configuration after disable")
        return False

    st.log("✓ sFlow disabled successfully and admin state is DOWN")
    st.log("✓ Collectors remain in configuration (expected behavior)")
    return True


def module_3_validation_reenable_sflow(dut: str) -> bool:
    """
    Module 3 - Validation Step 3: Re-enable sFlow and verify admin state is UP again
    """
    st.log("[MODULE 3.3] Re-enabling sFlow and verifying admin state")

    # Re-enable sFlow
    commands = ["sflow enable", "end"]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to re-enable sFlow: {str(e)}")
        return False

    # Verify admin state is UP
    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    
    st.log(f"show sflow output:\n{output_str}")

    # Check for admin state UP
    if "admin state" in output_str.lower() and "up" not in output_str.lower():
        st.error("sFlow admin state is not UP after re-enable")
        return False

    st.log("✓ sFlow re-enabled successfully and admin state is UP")
    return True


def module_3_validation_running_config(dut: str) -> bool:
    """
    Module 3 - Validation Step 4: Verify running configuration contains sflow commands
    """
    st.log("[MODULE 3.4] Verifying running configuration contains sFlow commands")

    # Get running configuration with grep for sflow
    output = st.show(
        dut,
        "show running-configuration | grep sflow",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""
    
    st.log(f"show running-configuration | grep sflow output:\n{output_str}")

    # Expected sflow commands in running config (mandatory ones)
    expected_commands = [
        f"sflow collector {CONFIG.collector_ip_v4}",
        f"sflow collector {CONFIG.collector_ip_v6}",
        "sflow enable",
        f"sflow agent-id {CONFIG.agent_id}",
        f"sflow polling-interval {CONFIG.polling_interval}",
        f"sflow sampling-rate {CONFIG.sampling_rate}",
    ]

    missing_commands = []
    for cmd in expected_commands:
        # Check if key parts of the command are present (first 2-3 words)
        if "collector" in cmd:
            # For collector, just check IP is present
            ip = cmd.split()[2]
            if ip not in output_str:
                missing_commands.append(cmd)
        else:
            # For other commands, check key words
            key_parts = cmd.split()[:2]  # Take first 2 words as key identifier
            if not any(all(part in line for part in key_parts) for line in output_str.split('\n')):
                missing_commands.append(cmd)

    if missing_commands:
        st.error(f"Missing commands in running configuration: {missing_commands}")
        return False

    st.log("✓ All expected sFlow commands found in running configuration")
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
        "no sflow collector 192.168.100.87",
        "no sflow collector 2001:db8::10",
        "no sflow agent-id",
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
def test_sflow_tc_1_1_1_enable_disable_globally():
    """
    Test Case 1.1.1: Enable and Disable sFlow Globally
    
    This test verifies:
    1. sFlow can be enabled globally (admin state: up)
    2. sFlow can be disabled globally (admin state: down)
    3. Configuration persists when sFlow is disabled
    4. sFlow can be re-enabled after disabling
    5. Running configuration reflects all sFlow settings
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: ENABLE AND DISABLE SFLOW GLOBALLY")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # Module 2: Configuration
        st.banner("[MODULE 2] CONFIGURATION - Setting up sFlow")
        if not module_2_configuration(dut):
            validation_failures.append("[MODULE 2] Failed to configure sFlow")
            st.report_fail("msg", "Configuration failed - cannot proceed with test")
            return

        st.wait(2)  # Wait for configuration to settle

        # Module 3: Validation
        st.banner("[MODULE 3] VALIDATION - Testing enable/disable functionality")

        st.log("STEP 1: Enable sFlow and verify admin state is UP")
        if not module_3_validation_enable_sflow(dut):
            validation_failures.append("STEP 1: Failed to enable sFlow or verify admin state UP")

        st.wait(1)

        st.log("STEP 2: Disable sFlow and verify admin state is DOWN")
        if not module_3_validation_disable_sflow(dut):
            validation_failures.append("STEP 2: Failed to disable sFlow or verify admin state DOWN")

        st.wait(1)

        st.log("STEP 3: Re-enable sFlow and verify admin state is UP")
        if not module_3_validation_reenable_sflow(dut):
            validation_failures.append("STEP 3: Failed to re-enable sFlow or verify admin state UP")

        st.wait(1)

        st.log("STEP 4: Verify running configuration contains all sFlow commands")
        if not module_3_validation_running_config(dut):
            validation_failures.append("STEP 4: Running configuration validation failed")

    except Exception as e:
        st.error(f"Exception in test_sflow_tc_1_1_1_enable_disable_globally: {str(e)}")
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
        st.log(f"✅ TEST CASE {TC_ID}: ENABLE AND DISABLE SFLOW GLOBALLY - PASSED")
        st.log("   All validations successful:")
        st.log("   ✓ sFlow enable/disable functionality")
        st.log("   ✓ Admin state transitions (up/down/up)")
        st.log("   ✓ Configuration persistence when disabled")
        st.log("   ✓ Running configuration accuracy")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
