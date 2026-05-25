"""
sFlow TEST CASE 1.2.5: VERIFY ALL SHOW COMMANDS WORK
Test Case ID: TC-SFLOW-1.2.5

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_2_5_verify_show_commands.py \
    --logs-path ./logs/sflow_tc_1_2_5_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.2.5: Verify All Show Commands Work

  Objective:
    Verify that all sFlow show commands work correctly and display
    expected information:
    - show sflow
    - show sflow interface
    - show sflow interface <interface-name>
    - show running-configuration | grep sflow

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration:
       - Enable sFlow globally
       - Add collector 192.168.100.87
       - Set polling interval 20
       - Configure Ethernet4 with sampling rate 5000
       - Configure Ethernet8 with sampling rate 6000
    3. Module 3 - Validation:
       - Test 'show sflow' command
         * Verify admin state is up
         * Verify polling interval is 20
         * Verify collector IP is present
       - Test 'show sflow interface' command
         * Verify all interfaces listed
         * Verify Ethernet4 has sampling rate 5000
         * Verify Ethernet8 has sampling rate 6000
       - Test 'show sflow interface Ethernet4' command
         * Verify only Ethernet4 is shown
         * Verify sampling rate 5000
       - Test 'show sflow interface Ethernet8' command
         * Verify only Ethernet8 is shown
         * Verify sampling rate 6000
       - Test 'show running-configuration | grep sflow' command
         * Verify sFlow configurations appear in running config
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
    # Collector Configuration
    "collector_ip":         "192.168.100.87",
    "collector_port":       "6343",

    # sFlow Configuration
    "polling_interval":     "20",
    "interface_1":          "Ethernet4",
    "sampling_rate_1":      "5000",
    "interface_2":          "Ethernet8",
    "sampling_rate_2":      "6000",
})

# Test Case ID
TC_ID = "TC-SFLOW-1.2.5"


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
    st.banner(f"TEST CASE {TC_ID}: VERIFY ALL SHOW COMMANDS WORK")
    st.banner("=" * 80)

    st.log(f"Collector: {CONFIG.collector_ip}:{CONFIG.collector_port}")

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
    Configure sFlow with collector, polling interval, and interface sampling rates.
    """
    st.banner("[MODULE 2] Configuring sFlow")

    # Configuration commands
    commands = [
        "sflow enable",
        f"sflow collector {CONFIG.collector_ip}",
        f"sflow polling-interval {CONFIG.polling_interval}",
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
        st.log(f"  ✓ Collector: {CONFIG.collector_ip}")
        st.log(f"  ✓ Polling interval: {CONFIG.polling_interval}")
        st.log(f"  ✓ {CONFIG.interface_1}: sampling rate {CONFIG.sampling_rate_1}")
        st.log(f"  ✓ {CONFIG.interface_2}: sampling rate {CONFIG.sampling_rate_2}")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure sFlow on {dut}: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION - Show Commands
# ======================================================================
def module_3_validate_show_sflow(dut: str) -> bool:
    """
    Module 3: Validate 'show sflow' command output.
    """
    st.log("[MODULE 3] Validating 'show sflow' command")

    output = st.show(dut, "show sflow | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    validation_errors = []

    # Check admin state
    if "sFlow Admin State:          up" not in output_str:
        validation_errors.append("sFlow Admin State is not 'up'")
    else:
        st.log(f"  ✓ sFlow Admin State: up")

    # Check polling interval
    if f"sFlow Polling Interval:     {CONFIG.polling_interval}" not in output_str:
        validation_errors.append(f"Polling interval is not {CONFIG.polling_interval}")
    else:
        st.log(f"  ✓ sFlow Polling Interval: {CONFIG.polling_interval}")

    # Check collector configured
    if "1 Collector configured:" not in output_str:
        validation_errors.append("Collector count not shown as '1 Collector configured'")
    else:
        st.log(f"  ✓ 1 Collector configured")

    # Check collector IP
    if CONFIG.collector_ip not in output_str:
        validation_errors.append(f"Collector IP {CONFIG.collector_ip} not found")
    else:
        st.log(f"  ✓ Collector IP: {CONFIG.collector_ip}")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ 'show sflow' command validation passed")
    return True


def module_3_validate_show_sflow_interface_all(dut: str) -> bool:
    """
    Module 3: Validate 'show sflow interface' command (all interfaces).
    """
    st.log("[MODULE 3] Validating 'show sflow interface' command")

    output = st.show(dut, "show sflow interface | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow interface output:\n{output_str}")

    validation_errors = []
    eth4_found = False
    eth8_found = False

    # Parse output to find Ethernet4 and Ethernet8
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

    st.log(f"✓ 'show sflow interface' command validation passed")
    return True


def module_3_validate_show_sflow_interface_specific(dut: str, interface: str, expected_rate: str) -> bool:
    """
    Module 3: Validate 'show sflow interface <interface>' command (specific interface).
    """
    st.log(f"[MODULE 3] Validating 'show sflow interface {interface}' command")

    # Convert interface name for command (e.g., Ethernet4 -> "Ethernet 4")
    interface_cmd = interface.replace("Ethernet", "Ethernet ")

    output = st.show(dut, f"show sflow interface {interface_cmd} | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow interface {interface_cmd} output:\n{output_str}")

    validation_errors = []
    interface_found = False

    # Parse output to find the specific interface
    for line in output_str.split('\n'):
        columns = [col.strip() for col in line.split('|') if col.strip()]

        if len(columns) >= 3 and columns[0] == interface:
            interface_found = True
            admin_state = columns[1]
            sampling_rate = columns[2]

            if "up" not in admin_state.lower():
                validation_errors.append(f"{interface} Admin State not 'up'")
            else:
                st.log(f"  ✓ {interface} Admin State: up")

            if expected_rate not in sampling_rate:
                validation_errors.append(f"{interface} Sampling Rate not {expected_rate} (found: {sampling_rate})")
            else:
                st.log(f"  ✓ {interface} Sampling Rate: {expected_rate}")

    if not interface_found:
        validation_errors.append(f"{interface} not found in output")

    # Verify ONLY this interface is shown (not other interfaces)
    interface_count = 0
    for line in output_str.split('\n'):
        columns = [col.strip() for col in line.split('|') if col.strip()]
        if len(columns) >= 3 and columns[0].startswith("Ethernet"):
            interface_count += 1

    if interface_count > 1:
        validation_errors.append(f"Expected only {interface} but found {interface_count} interfaces")
    else:
        st.log(f"  ✓ Only {interface} shown in output")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ 'show sflow interface {interface_cmd}' command validation passed")
    return True


def module_3_validate_running_config_grep(dut: str) -> bool:
    """
    Module 3: Validate 'show running-configuration | grep sflow' command.
    """
    st.log("[MODULE 3] Validating 'show running-configuration | grep sflow' command")

    output = st.show(dut, "show running-configuration | grep sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show running-configuration | grep sflow output:\n{output_str}")

    validation_errors = []

    # Expected strings in running config
    expected_configs = [
        "sflow enable",
        f"sflow collector {CONFIG.collector_ip}",
        f"sflow polling-interval {CONFIG.polling_interval}",
        f"sflow sampling-rate {CONFIG.sampling_rate_1}",
        f"sflow sampling-rate {CONFIG.sampling_rate_2}",
    ]

    for expected in expected_configs:
        if expected not in output_str:
            validation_errors.append(f"Expected config not found: {expected}")
        else:
            st.log(f"  ✓ Found: {expected}")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ 'show running-configuration | grep sflow' validation passed")
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
    except Exception as e:
        st.log(f"[MODULE 4] Cleanup error: {str(e)}")


# ======================================================================
# Test Function - Main Test Case
# ======================================================================
def test_sflow_tc_1_2_5_verify_show_commands():
    """
    Test Case 1.2.5: Verify All Show Commands Work

    This test verifies:
    1. 'show sflow' command displays global sFlow configuration
    2. 'show sflow interface' command displays all interface configurations
    3. 'show sflow interface <interface>' displays specific interface
    4. 'show running-configuration | grep sflow' shows sFlow in config
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: VERIFY ALL SHOW COMMANDS WORK")
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
    if not module_2_configuration(dut):
        st.report_fail("test_case_failed", "Failed to configure sFlow")

    st.wait(2)

    # ========================================================================
    # MODULE 3: VALIDATION - Show Commands
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 3] VALIDATION - Show Commands                           #")
    st.banner("=" * 80)

    st.log("STEP 2: Validate 'show sflow' command")
    if not module_3_validate_show_sflow(dut):
        validation_failures.append("STEP 2: 'show sflow' command validation failed")

    st.wait(1)

    st.log("STEP 3: Validate 'show sflow interface' command (all interfaces)")
    if not module_3_validate_show_sflow_interface_all(dut):
        validation_failures.append("STEP 3: 'show sflow interface' command validation failed")

    st.wait(1)

    st.log(f"STEP 4: Validate 'show sflow interface {CONFIG.interface_1}' command")
    if not module_3_validate_show_sflow_interface_specific(dut, CONFIG.interface_1, CONFIG.sampling_rate_1):
        validation_failures.append(f"STEP 4: 'show sflow interface {CONFIG.interface_1}' command validation failed")

    st.wait(1)

    st.log(f"STEP 5: Validate 'show sflow interface {CONFIG.interface_2}' command")
    if not module_3_validate_show_sflow_interface_specific(dut, CONFIG.interface_2, CONFIG.sampling_rate_2):
        validation_failures.append(f"STEP 5: 'show sflow interface {CONFIG.interface_2}' command validation failed")

    st.wait(1)

    st.log("STEP 6: Validate 'show running-configuration | grep sflow' command")
    if not module_3_validate_running_config_grep(dut):
        validation_failures.append("STEP 6: 'show running-configuration | grep sflow' validation failed")

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
        st.log("✓ All show command validations passed successfully")
        st.log("  - show sflow")
        st.log("  - show sflow interface")
        st.log(f"  - show sflow interface {CONFIG.interface_1}")
        st.log(f"  - show sflow interface {CONFIG.interface_2}")
        st.log("  - show running-configuration | grep sflow")
        st.report_pass("test_case_passed")
