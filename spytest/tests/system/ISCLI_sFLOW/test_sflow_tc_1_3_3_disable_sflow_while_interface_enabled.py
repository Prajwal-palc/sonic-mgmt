"""
sFlow TEST CASE 1.3.3: DISABLE SFLOW WHILE INTERFACE ENABLED
Test Case ID: TC-SFLOW-1.3.3

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_3_3_disable_sflow_while_interface_enabled.py \
    --logs-path ./logs/sflow_tc_1_3_3_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.3.3: Disable sFlow While Interface Enabled

  Objective:
    Verify that when sFlow is disabled globally, the interface-level
    configurations are not shown in 'show sflow interface', even though
    the interface has sFlow enabled with a sampling rate configured.
    This tests the dependency of interface sFlow on global sFlow state.

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration:
       - Add collector 192.168.100.87
       - Set polling interval 20
       - Disable sFlow globally (no sflow enable)
       - Enable sFlow on Ethernet4
       - Set sampling rate 6000 on Ethernet4
    3. Module 3 - Validation:
       - Verify 'show sflow' shows:
         * sFlow Admin State: down
         * Polling Interval: 20
         * Collector configured
       - Verify 'show sflow interface' shows:
         * "No sFlow interfaces configured"
         * Interface configurations are NOT shown when global sFlow is disabled
    4. Module 4 - Cleanup: Remove all sFlow configuration

Pre-requisites:
  - 1 SONiC device (DUT1)
  - Testbed: testbed_2vs.yaml or compatible

Notes:
  - When global sFlow is disabled, interface-level sFlow configurations
    are hidden/inactive
  - Collector and polling interval configurations persist even when
    global sFlow is disabled
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
    "polling_interval":     "20",
    "interface":            "Ethernet4",
    "sampling_rate":        "6000",
})

# Test Case ID
TC_ID = "TC-SFLOW-1.3.3"


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
    st.banner(f"TEST CASE {TC_ID}: DISABLE SFLOW WHILE INTERFACE ENABLED")
    st.banner("=" * 80)

    st.log(f"Collector: {CONFIG.collector_ip}:{CONFIG.collector_port}")
    st.log(f"Interface: {CONFIG.interface}")
    st.log(f"Sampling Rate: {CONFIG.sampling_rate}")

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
        f"interface {CONFIG.interface}",
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
    Configure sFlow with global sFlow disabled but interface enabled.
    """
    st.banner("[MODULE 2] Configuring sFlow with global disabled and interface enabled")

    # Configuration commands
    # Note: The order matches manual test exactly
    commands = [
        "no sflow enable",  # Disable sFlow globally
        f"sflow collector {CONFIG.collector_ip}",
        f"sflow polling-interval {CONFIG.polling_interval}",
        f"interface {CONFIG.interface}",
        "sflow enable",  # Enable on interface (but global is disabled)
        f"sflow sampling-rate {CONFIG.sampling_rate}",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] sFlow configured on {dut}")
        st.log(f"  ✓ Global sFlow: DISABLED")
        st.log(f"  ✓ Collector: {CONFIG.collector_ip}")
        st.log(f"  ✓ Polling interval: {CONFIG.polling_interval}")
        st.log(f"  ✓ {CONFIG.interface}: sFlow enabled with sampling rate {CONFIG.sampling_rate}")
        st.log(f"  Note: Interface config should be hidden due to global sFlow disabled")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure sFlow on {dut}: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION
# ======================================================================
def module_3_validate_show_sflow(dut: str) -> bool:
    """
    Module 3: Validate 'show sflow' command with global sFlow disabled.
    """
    st.log("[MODULE 3] Validating 'show sflow' command (global sFlow disabled)")

    output = st.show(dut, "show sflow | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    validation_errors = []

    # Check admin state is DOWN
    if "sFlow Admin State:          down" not in output_str:
        validation_errors.append("sFlow Admin State is not 'down'")
    else:
        st.log(f"  ✓ sFlow Admin State: down")

    # Check polling interval still configured
    if f"sFlow Polling Interval:     {CONFIG.polling_interval}" not in output_str:
        validation_errors.append(f"Polling interval is not {CONFIG.polling_interval}")
    else:
        st.log(f"  ✓ sFlow Polling Interval: {CONFIG.polling_interval}")

    # Check collector still configured
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

    st.log(f"✓ 'show sflow' validation passed - global sFlow is disabled")
    return True


def module_3_validate_show_sflow_interface_empty(dut: str) -> bool:
    """
    Module 3: Validate 'show sflow interface' shows no interfaces when global sFlow disabled.
    """
    st.log("[MODULE 3] Validating 'show sflow interface' command")
    st.log("  Expected: 'No sFlow interfaces configured' (global sFlow is disabled)")

    output = st.show(dut, "show sflow interface | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow interface output:\n{output_str}")

    validation_errors = []

    # Check for "No sFlow interfaces configured" message
    if "No sFlow interfaces configured" not in output_str:
        validation_errors.append("Expected 'No sFlow interfaces configured' message not found")
        st.error(f"  ✗ Expected 'No sFlow interfaces configured' message")
    else:
        st.log(f"  ✓ Found: 'No sFlow interfaces configured'")

    # Verify interface is NOT shown in output
    # Even though Ethernet4 has sFlow enabled, it should not appear when global sFlow is disabled
    interface_found = False
    for line in output_str.split('\n'):
        columns = [col.strip() for col in line.split('|') if col.strip()]
        if len(columns) >= 1 and columns[0] == CONFIG.interface:
            interface_found = True
            break

    if interface_found:
        validation_errors.append(f"{CONFIG.interface} found in output (should be hidden when global sFlow disabled)")
        st.error(f"  ✗ {CONFIG.interface} should not appear when global sFlow is disabled")
    else:
        st.log(f"  ✓ {CONFIG.interface} correctly hidden (global sFlow disabled)")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ 'show sflow interface' validation passed - no interfaces shown")
    return True


def module_3_validate_interface_config_hidden(dut: str) -> bool:
    """
    Module 3: Additional validation that interface-specific config is hidden.
    """
    st.log("[MODULE 3] Validating interface configuration is hidden")

    output = st.show(dut, "show sflow interface | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""

    validation_errors = []

    # Verify sampling rate is NOT shown anywhere
    if CONFIG.sampling_rate in output_str:
        # Check if it's in the context of interface config (not just in a message)
        for line in output_str.split('\n'):
            if CONFIG.sampling_rate in line and CONFIG.interface in line:
                validation_errors.append(f"Sampling rate {CONFIG.sampling_rate} shown for {CONFIG.interface} (should be hidden)")
                st.error(f"  ✗ Interface sampling rate should be hidden when global sFlow disabled")
                break

    if not validation_errors:
        st.log(f"  ✓ Interface sampling rate {CONFIG.sampling_rate} not shown (correctly hidden)")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ Interface configuration correctly hidden when global sFlow disabled")
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
        f"interface {CONFIG.interface}",
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
def test_sflow_tc_1_3_3_disable_sflow_while_interface_enabled():
    """
    Test Case 1.3.3: Disable sFlow While Interface Enabled

    This test verifies:
    1. When global sFlow is disabled, interface-level sFlow configurations are hidden
    2. 'show sflow' displays admin state as 'down'
    3. 'show sflow interface' displays 'No sFlow interfaces configured'
    4. Collector and polling interval configurations persist
    5. Interface configurations exist but are not active/visible when global disabled
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: DISABLE SFLOW WHILE INTERFACE ENABLED")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    # ========================================================================
    # MODULE 2: CONFIGURATION
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 2] CONFIGURATION - Global Disabled, Interface Enabled   #")
    st.banner("=" * 80)

    st.log("STEP 1: Configure sFlow with global disabled but interface enabled")
    st.log("  Configuration order:")
    st.log("    1. Disable global sFlow (no sflow enable)")
    st.log("    2. Add collector 192.168.100.87")
    st.log("    3. Set polling interval 20")
    st.log("    4. Enable sFlow on Ethernet4")
    st.log("    5. Set sampling rate 6000 on Ethernet4")

    if not module_2_configuration(dut):
        st.report_fail("test_case_failed", "Failed to configure sFlow")

    st.wait(2)

    # ========================================================================
    # MODULE 3: VALIDATION
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 3] VALIDATION - Verify Interface Config Hidden          #")
    st.banner("=" * 80)

    st.log("STEP 2: Validate 'show sflow' command")
    st.log("  Expected:")
    st.log("    - sFlow Admin State: down")
    st.log("    - Polling Interval: 20")
    st.log("    - Collector: 192.168.100.87")

    if not module_3_validate_show_sflow(dut):
        validation_failures.append("STEP 2: 'show sflow' validation failed")

    st.wait(1)

    st.log("STEP 3: Validate 'show sflow interface' command")
    st.log("  Expected:")
    st.log("    - Message: 'No sFlow interfaces configured'")
    st.log("    - Ethernet4 NOT shown (hidden due to global sFlow disabled)")

    if not module_3_validate_show_sflow_interface_empty(dut):
        validation_failures.append("STEP 3: 'show sflow interface' validation failed")

    st.wait(1)

    st.log("STEP 4: Validate interface configuration is hidden")
    st.log("  Expected:")
    st.log("    - Sampling rate 6000 NOT shown in output")
    st.log("    - Interface-level config inactive when global disabled")

    if not module_3_validate_interface_config_hidden(dut):
        validation_failures.append("STEP 4: Interface configuration hiding validation failed")

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
        st.log("  - Global sFlow disabled (Admin State: down)")
        st.log("  - Collector and polling interval persist")
        st.log("  - Interface configurations hidden in 'show sflow interface'")
        st.log("  - 'No sFlow interfaces configured' message displayed")
        st.log("  - Interface-level config inactive when global sFlow disabled")
        st.report_pass("test_case_passed")
