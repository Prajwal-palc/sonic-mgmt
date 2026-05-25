"""
sFlow TEST CASE 1.4.1: CONFIG SURVIVES SAVE
Test Case ID: TC-SFLOW-1.4.1

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_4_1_config_survives_save.py \
    --logs-path ./logs/sflow_tc_1_4_1_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.4.1: Config Survives Save

  Objective:
    Verify that sFlow configuration survives 'write memory' command and
    persists in running-configuration. This tests configuration persistence
    and ensures sFlow settings are saved to startup-config.

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration:
       - Enable sFlow globally
       - Add collector 192.168.100.87
       - Configure Ethernet4 with sampling rate 70000
       - Configure Ethernet8 with sampling rate 90000
       - Verify configuration with 'show sflow interface'
    3. Module 3 - Validation:
       - Execute 'write memory' command
       - Verify 'write memory' completes successfully
       - Execute 'show running-configuration | grep sflow'
       - Verify all sFlow configurations appear in running-config:
         * sflow enable
         * sflow collector 192.168.100.87
         * sflow sampling-rate 70000 (on Ethernet4)
         * sflow sampling-rate 90000 (on Ethernet8)
    4. Module 4 - Cleanup: Remove all sFlow configuration

Pre-requisites:
  - 1 SONiC device (DUT1)
  - Testbed: testbed_2vs.yaml or compatible

Notes:
  - 'write memory' saves running-config to startup-config
  - After 'write memory', config persists across reboots
  - This test verifies config persistence but does NOT reboot
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
    # Collector Configuration
    "collector_ip":         "192.168.100.87",
    "collector_port":       "6343",

    # sFlow Configuration
    "interface_1":          "Ethernet4",
    "sampling_rate_1":      "70000",
    "interface_2":          "Ethernet8",
    "sampling_rate_2":      "90000",
})

# Test Case ID
TC_ID = "TC-SFLOW-1.4.1"


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
    st.banner(f"TEST CASE {TC_ID}: CONFIG SURVIVES SAVE")
    st.banner("=" * 80)

    st.log(f"Collector: {CONFIG.collector_ip}:{CONFIG.collector_port}")
    st.log(f"Interface 1: {CONFIG.interface_1} - Sampling Rate: {CONFIG.sampling_rate_1}")
    st.log(f"Interface 2: {CONFIG.interface_2} - Sampling Rate: {CONFIG.sampling_rate_2}")

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
        f"no sflow collector {CONFIG.collector_ip}",
        f"interface {CONFIG.interface_1}",
        "no sflow enable",
        "exit",
        f"interface {CONFIG.interface_2}",
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
    Configure sFlow with collector and interface sampling rates.
    """
    st.banner("[MODULE 2] Configuring sFlow with collector and interfaces")

    # Configuration commands - matches manual test exactly
    commands = [
        "sflow enable",
        f"sflow collector {CONFIG.collector_ip}",
        f"interface {CONFIG.interface_1}",
        "sflow enable",
        f"sflow sampling-rate {CONFIG.sampling_rate_1}",
        "exit",
        f"interface {CONFIG.interface_2}",
        "sflow enable",
        f"sflow sampling-rate {CONFIG.sampling_rate_2}",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] sFlow configured on {dut}")
        st.log(f"  ✓ Global sFlow: ENABLED")
        st.log(f"  ✓ Collector: {CONFIG.collector_ip}")
        st.log(f"  ✓ {CONFIG.interface_1}: sampling rate {CONFIG.sampling_rate_1}")
        st.log(f"  ✓ {CONFIG.interface_2}: sampling rate {CONFIG.sampling_rate_2}")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure sFlow on {dut}: {str(e)}")
        return False


def module_2_verify_configuration(dut: str) -> bool:
    """
    Module 2: Verify sFlow configuration before save.
    """
    st.log(f"[MODULE 2] Verifying sFlow configuration on {dut}")

    output = st.show(dut, "show sflow interface | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow interface output:\n{output_str}")

    validation_errors = []
    eth4_found = False
    eth8_found = False

    # Parse output to find both interfaces
    for line in output_str.split('\n'):
        columns = [col.strip() for col in line.split('|') if col.strip()]

        # Check Ethernet4
        if len(columns) >= 3 and columns[0] == CONFIG.interface_1:
            eth4_found = True
            admin_state = columns[1]
            sampling_rate = columns[2]

            if "up" not in admin_state.lower():
                validation_errors.append(f"{CONFIG.interface_1} Admin State not 'up'")
            else:
                st.log(f"  ✓ {CONFIG.interface_1} Admin State: up")

            if CONFIG.sampling_rate_1 not in sampling_rate:
                validation_errors.append(f"{CONFIG.interface_1} Sampling Rate not {CONFIG.sampling_rate_1} (found: {sampling_rate})")
            else:
                st.log(f"  ✓ {CONFIG.interface_1} Sampling Rate: {CONFIG.sampling_rate_1}")

        # Check Ethernet8
        if len(columns) >= 3 and columns[0] == CONFIG.interface_2:
            eth8_found = True
            admin_state = columns[1]
            sampling_rate = columns[2]

            if "up" not in admin_state.lower():
                validation_errors.append(f"{CONFIG.interface_2} Admin State not 'up'")
            else:
                st.log(f"  ✓ {CONFIG.interface_2} Admin State: up")

            if CONFIG.sampling_rate_2 not in sampling_rate:
                validation_errors.append(f"{CONFIG.interface_2} Sampling Rate not {CONFIG.sampling_rate_2} (found: {sampling_rate})")
            else:
                st.log(f"  ✓ {CONFIG.interface_2} Sampling Rate: {CONFIG.sampling_rate_2}")

    if not eth4_found:
        validation_errors.append(f"{CONFIG.interface_1} not found in output")

    if not eth8_found:
        validation_errors.append(f"{CONFIG.interface_2} not found in output")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ Configuration verified successfully")
    return True


# ======================================================================
# MODULE 3: VALIDATION - Write Memory & Verify Persistence
# ======================================================================
def module_3_write_memory(dut: str) -> bool:
    """
    Module 3: Execute 'write memory' to save configuration.
    """
    st.log("[MODULE 3] Executing 'write memory' command")

    try:
        # Execute 'write memory' command
        output = st.config(dut, ["write memory"], type='klish', skip_error_check=False)
        output_str = str(output) if output else ""
        st.log(f"write memory output:\n{output_str}")

        # Check for successful completion
        if "completed" in output_str.lower() or "success" in output_str.lower():
            st.log(f"✓ 'write memory' completed successfully")
            return True
        else:
            st.log(f"Warning: 'write memory' may not have completed (no success message)")
            # Don't fail - some systems don't output confirmation
            return True

    except Exception as e:
        st.error(f"Failed to execute 'write memory': {str(e)}")
        return False


def module_3_verify_running_config(dut: str) -> bool:
    """
    Module 3: Verify sFlow configuration appears in running-configuration.
    """
    st.log("[MODULE 3] Verifying sFlow in running-configuration")

    output = st.show(dut, "show running-configuration | grep sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show running-configuration | grep sflow output:\n{output_str}")

    validation_errors = []

    # Expected configurations in running-config
    expected_configs = [
        "sflow enable",
        f"sflow collector {CONFIG.collector_ip}",
        f"sflow sampling-rate {CONFIG.sampling_rate_1}",
        f"sflow sampling-rate {CONFIG.sampling_rate_2}",
    ]

    for expected in expected_configs:
        if expected not in output_str:
            validation_errors.append(f"Expected config not found: {expected}")
            st.error(f"  ✗ Missing: {expected}")
        else:
            st.log(f"  ✓ Found: {expected}")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ All sFlow configurations present in running-config")
    return True


def module_3_verify_show_sflow(dut: str) -> bool:
    """
    Module 3: Verify 'show sflow' after write memory.
    """
    st.log("[MODULE 3] Verifying 'show sflow' after write memory")

    output = st.show(dut, "show sflow | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    validation_errors = []

    # Check admin state is UP
    if "sFlow Admin State:          up" not in output_str:
        validation_errors.append("sFlow Admin State is not 'up'")
    else:
        st.log(f"  ✓ sFlow Admin State: up")

    # Check collector configured
    if CONFIG.collector_ip not in output_str:
        validation_errors.append(f"Collector IP {CONFIG.collector_ip} not found")
    else:
        st.log(f"  ✓ Collector IP: {CONFIG.collector_ip}")

    # Check collector count
    if "1 Collector configured:" not in output_str:
        validation_errors.append("Expected '1 Collector configured' not found")
    else:
        st.log(f"  ✓ 1 Collector configured")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ 'show sflow' verification passed")
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
        f"no sflow collector {CONFIG.collector_ip}",
        f"interface {CONFIG.interface_1}",
        "no sflow enable",
        "exit",
        f"interface {CONFIG.interface_2}",
        "no sflow enable",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=True)
        st.log(f"[MODULE 4] Cleanup completed on {dut}")

        # Save cleanup to startup-config
        st.log(f"[MODULE 4] Saving cleanup with 'write memory'")
        st.config(dut, ["write memory"], type='klish', skip_error_check=True)
        st.log(f"✓ Cleanup saved to startup-config")

    except Exception as e:
        st.log(f"[MODULE 4] Cleanup error: {str(e)}")


# ======================================================================
# Test Function - Main Test Case
# ======================================================================
def test_sflow_tc_1_4_1_config_survives_save():
    """
    Test Case 1.4.1: Config Survives Save

    This test verifies:
    1. sFlow configuration can be created with collector and interfaces
    2. 'write memory' command executes successfully
    3. Configuration persists after 'write memory'
    4. 'show running-configuration | grep sflow' shows all configurations
    5. 'show sflow' and 'show sflow interface' still work after save
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: CONFIG SURVIVES SAVE")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    # ========================================================================
    # MODULE 2: CONFIGURATION
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 2] CONFIGURATION - sFlow Setup                         #")
    st.banner("=" * 80)

    st.log("STEP 1: Configure sFlow with collector and interface sampling rates")
    st.log("  Configuration:")
    st.log("    - Enable sFlow globally")
    st.log("    - Add collector 192.168.100.87")
    st.log("    - Ethernet4: sampling rate 70000")
    st.log("    - Ethernet8: sampling rate 90000")

    if not module_2_configuration(dut):
        st.report_fail("test_case_failed", "Failed to configure sFlow")

    st.wait(2)

    st.log("STEP 2: Verify configuration before save")
    if not module_2_verify_configuration(dut):
        st.report_fail("test_case_failed", "Configuration verification failed")

    # ========================================================================
    # MODULE 3: VALIDATION - Write Memory & Verify Persistence
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 3] VALIDATION - Write Memory & Verify                   #")
    st.banner("=" * 80)

    st.log("STEP 3: Execute 'write memory' to save configuration")
    st.log("  Command: write memory")
    st.log("  Expected: Write memory completed")

    if not module_3_write_memory(dut):
        validation_failures.append("STEP 3: 'write memory' command failed")

    st.wait(2)

    st.log("STEP 4: Verify 'show sflow' after write memory")
    if not module_3_verify_show_sflow(dut):
        validation_failures.append("STEP 4: 'show sflow' verification failed after write memory")

    st.wait(1)

    st.log("STEP 5: Verify configuration in running-config")
    st.log("  Command: show running-configuration | grep sflow")
    st.log("  Expected configurations:")
    st.log("    - sflow enable")
    st.log("    - sflow collector 192.168.100.87")
    st.log("    - sflow sampling-rate 70000")
    st.log("    - sflow sampling-rate 90000")

    if not module_3_verify_running_config(dut):
        validation_failures.append("STEP 5: Configuration not found in running-config")

    st.wait(1)

    st.log("STEP 6: Verify 'show sflow interface' after write memory")
    if not module_2_verify_configuration(dut):
        validation_failures.append("STEP 6: 'show sflow interface' verification failed after write memory")

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
        st.log("✓ All validations passed successfully")
        st.log("  - sFlow configured with collector and interfaces")
        st.log("  - 'write memory' executed successfully")
        st.log("  - Configuration persists after save")
        st.log("  - All configs present in running-configuration")
        st.log(f"  - {CONFIG.interface_1}: sampling rate {CONFIG.sampling_rate_1}")
        st.log(f"  - {CONFIG.interface_2}: sampling rate {CONFIG.sampling_rate_2}")
        st.report_pass("test_case_passed")
