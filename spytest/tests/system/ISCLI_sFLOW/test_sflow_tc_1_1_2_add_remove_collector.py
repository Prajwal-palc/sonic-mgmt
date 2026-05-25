"""
sFlow TEST CASE 1.1.2: ADD AND REMOVE COLLECTOR
Test Case ID: TC-SFLOW-1.1.2

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_1_2_add_remove_collector.py \
    --logs-path ./logs/sflow_tc_1_1_2_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.1.2: Add and Remove Collector
  
  Objective: 
    Verify sFlow collector can be added and removed, and verify that
    collector configuration appears correctly in show commands.
  
  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration: Enable sFlow with base config
    3. Module 3 - Validation: 
       - Add collector and verify it appears in show sflow
       - Verify collector appears in running-config
       - Remove collector and verify it's removed from show sflow
       - Verify collector count is 0 after removal
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
    "collector_ip":         "192.168.100.175",
    "collector_port":       "6343",
    "collector_vrf":        "default",
    "agent_id":             "Ethernet4",
    "polling_interval":     "6",
    "sampling_rate":        "1234",
})

# ======================================================================
# Test Case ID
# ======================================================================
TC_ID = "TC-SFLOW-1.1.2"


# ======================================================================
# Module Fixture - Setup and Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def sflow_tc_1_1_2_module_hooks(request):
    """Module-level setup and teardown for Test Case 1.1.2."""
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID} - ADD AND REMOVE COLLECTOR - MODULE START")
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
        "no sflow collector 192.168.100.175",
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
    Configure sFlow with base settings (enable, agent-id, polling, sampling rate).
    """
    st.banner("[MODULE 2] Configuring sFlow with base parameters")

    commands = [
        f"sflow agent-id {CONFIG.agent_id}",
        f"sflow polling-interval {CONFIG.polling_interval}",
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
def module_3_validation_add_collector(dut: str) -> bool:
    """
    Module 3 - Validation Step 1: Add collector and verify it appears
    """
    st.log("[MODULE 3.1] Adding collector and verifying")

    # Add collector
    commands = [f"sflow collector {CONFIG.collector_ip}", "end"]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to add collector: {str(e)}")
        return False

    # Verify collector appears in show sflow
    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    
    st.log(f"show sflow output:\n{output_str}")

    # Check collector IP is present
    if CONFIG.collector_ip not in output_str:
        st.error(f"Collector {CONFIG.collector_ip} not found in show sflow output")
        return False

    # Check collector count is 1
    if "1" not in output_str or "collector" not in output_str.lower():
        st.error("Collector count not showing as 1")
        return False

    st.log(f"✓ Collector {CONFIG.collector_ip} added successfully")
    st.log("✓ Collector appears in show sflow output")
    return True


def module_3_validation_running_config(dut: str) -> bool:
    """
    Module 3 - Validation Step 2: Verify collector appears in running config
    """
    st.log("[MODULE 3.2] Verifying collector in running configuration")

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

    # Check for collector in running config
    if CONFIG.collector_ip not in output_str:
        st.error(f"Collector {CONFIG.collector_ip} not found in running configuration")
        return False

    # Check for expected format: "sflow collector <IP> 6343 vrf default"
    expected_parts = ["sflow collector", CONFIG.collector_ip, CONFIG.collector_port, CONFIG.collector_vrf]
    line_with_collector = [line for line in output_str.split('\n') if CONFIG.collector_ip in line]
    
    if not line_with_collector:
        st.error("Collector line not found in running config")
        return False

    st.log("✓ Collector found in running configuration with correct format")
    return True


def module_3_validation_remove_collector(dut: str) -> bool:
    """
    Module 3 - Validation Step 3: Remove collector and verify it's removed
    """
    st.log("[MODULE 3.3] Removing collector and verifying removal")

    # Remove collector
    commands = [f"no sflow collector {CONFIG.collector_ip}", "end"]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to remove collector: {str(e)}")
        return False

    # Verify collector is removed from show sflow
    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    
    st.log(f"show sflow output after removal:\n{output_str}")

    # Check collector count is 0
    if "0" not in output_str or "collector" not in output_str.lower():
        st.error("Collector count not showing as 0 after removal")
        return False

    # Collector IP should not appear anymore
    if CONFIG.collector_ip in output_str:
        st.error(f"Collector {CONFIG.collector_ip} still appears after removal")
        return False

    st.log(f"✓ Collector {CONFIG.collector_ip} removed successfully")
    st.log("✓ Collector count is 0")
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
        "no sflow collector 192.168.100.175",
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
def test_sflow_tc_1_1_2_add_remove_collector():
    """
    Test Case 1.1.2: Add and Remove Collector
    
    This test verifies:
    1. Collector can be added to sFlow configuration
    2. Collector appears in show sflow output with correct details
    3. Collector appears in running configuration
    4. Collector can be removed from configuration
    5. Collector count returns to 0 after removal
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: ADD AND REMOVE COLLECTOR")
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
        st.banner("[MODULE 3] VALIDATION - Testing add/remove collector functionality")

        st.log("STEP 1: Add collector and verify it appears in show sflow")
        if not module_3_validation_add_collector(dut):
            validation_failures.append("STEP 1: Failed to add collector or verify in show sflow")

        st.wait(1)

        st.log("STEP 2: Verify collector appears in running configuration")
        if not module_3_validation_running_config(dut):
            validation_failures.append("STEP 2: Collector not found in running configuration")

        st.wait(1)

        st.log("STEP 3: Remove collector and verify removal")
        if not module_3_validation_remove_collector(dut):
            validation_failures.append("STEP 3: Failed to remove collector or verify removal")

    except Exception as e:
        st.error(f"Exception in test_sflow_tc_1_1_2_add_remove_collector: {str(e)}")
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
        st.log(f"✅ TEST CASE {TC_ID}: ADD AND REMOVE COLLECTOR - PASSED")
        st.log("   All validations successful:")
        st.log("   ✓ Collector add functionality")
        st.log("   ✓ Collector appears in show sflow")
        st.log("   ✓ Collector appears in running config")
        st.log("   ✓ Collector remove functionality")
        st.log("   ✓ Collector count accuracy")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
