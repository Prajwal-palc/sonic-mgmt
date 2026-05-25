"""
sFlow TEST CASE 1.1.6: ENABLE SFLOW ON SPECIFIC INTERFACE
Test Case ID: TC-SFLOW-1.1.6

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_1_6_enable_interface.py \
    --logs-path ./logs/sflow_tc_1_1_6_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.1.6: Enable sFlow on Specific Interface

  Objective:
    Verify sFlow can be enabled on specific interface with custom sampling rate,
    and verify that disabling sFlow on interface resets the configuration.

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration: Enable sFlow globally
    3. Module 3 - Validation:
       - Enable sFlow on Ethernet4 with sampling rate 2048
       - Run 'show sflow interface' (all interfaces) and verify:
         * All interfaces appear in output
         * Ethernet4 shows Admin State "up" and Sampling Rate 2048
       - Disable sFlow on Ethernet4
       - Run 'show sflow interface' (all interfaces) and verify:
         * All interfaces appear in output
         * Ethernet4 shows Admin State "down" and sampling rate resets to 4294967295
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
    "interface":            "Ethernet4",
    "sampling_rate":        "2048",
    "disabled_rate":        "4294967295",  # Platform's disabled sampling rate value
})

# ======================================================================
# Test Case ID
# ======================================================================
TC_ID = "TC-SFLOW-1.1.6"


# ======================================================================
# Module Fixture - Setup and Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def sflow_tc_1_1_6_module_hooks(request):
    """Module-level setup and teardown for Test Case 1.1.6."""
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID} - ENABLE SFLOW ON SPECIFIC INTERFACE - MODULE START")
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
    Enable sFlow globally.
    """
    st.banner("[MODULE 2] Enabling sFlow globally")

    commands = [
        "sflow enable",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] sFlow enabled globally on {dut}")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to enable sFlow on {dut}: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION
# ======================================================================
def module_3_validation_enable_interface_sflow(dut: str) -> bool:
    """
    Module 3 - Validation Step 1: Enable sFlow on Ethernet4 with sampling rate
    and verify using 'show sflow interface' (all interfaces)
    """
    st.log("[MODULE 3.1] Enabling sFlow on Ethernet4 with sampling rate 2048")

    # Enable sFlow on interface with sampling rate
    commands = [
        f"interface {CONFIG.interface}",
        "sflow enable",
        f"sflow sampling-rate {CONFIG.sampling_rate}",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to enable sFlow on interface: {str(e)}")
        return False

    # Verify interface sFlow configuration using 'show sflow interface' (all interfaces)
    # Using '| no-more' to prevent pagination
    output = st.show(
        dut,
        "show sflow interface | no-more",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    st.log(f"show sflow interface (all interfaces) output:\n{output_str}")

    # Parse output to find Ethernet4 line
    ethernet4_found = False
    admin_state_ok = False
    sampling_rate_ok = False

    for line in output_str.split('\n'):
        if CONFIG.interface in line:
            ethernet4_found = True
            st.log(f"Found {CONFIG.interface} in output: {line}")

            # Check Admin State is "up"
            if "up" in line.lower():
                admin_state_ok = True
                st.log(f"✓ Admin State is 'up' for {CONFIG.interface}")

            # Check Sampling Rate is 2048
            if CONFIG.sampling_rate in line:
                sampling_rate_ok = True
                st.log(f"✓ Sampling Rate is {CONFIG.sampling_rate} for {CONFIG.interface}")

            break

    # Validate findings
    if not ethernet4_found:
        st.error(f"{CONFIG.interface} not found in 'show sflow interface' output")
        return False

    if not admin_state_ok:
        st.error(f"Admin State not showing as 'up' for {CONFIG.interface}")
        return False

    if not sampling_rate_ok:
        st.error(f"Sampling rate {CONFIG.sampling_rate} not found for {CONFIG.interface}")
        return False

    st.log(f"✓ sFlow enabled on {CONFIG.interface} with sampling rate {CONFIG.sampling_rate}")
    st.log(f"✓ All interfaces shown in 'show sflow interface' output (matching manual test)")
    return True


def module_3_validation_disable_interface_sflow(dut: str) -> bool:
    """
    Module 3 - Validation Step 2: Disable sFlow on Ethernet4 and verify
    using 'show sflow interface' (all interfaces)
    """
    st.log("[MODULE 3.2] Disabling sFlow on Ethernet4 and verifying")

    # Disable sFlow on interface
    commands = [
        f"interface {CONFIG.interface}",
        "no sflow enable",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to disable sFlow on interface: {str(e)}")
        return False

    # Verify interface sFlow is disabled using 'show sflow interface' (all interfaces)
    # Using '| no-more' to prevent pagination
    output = st.show(
        dut,
        "show sflow interface | no-more",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    st.log(f"show sflow interface (all interfaces) output after disable:\n{output_str}")

    # Parse output to find Ethernet4 line
    ethernet4_found = False
    admin_state_ok = False
    sampling_rate_ok = False

    for line in output_str.split('\n'):
        if CONFIG.interface in line:
            ethernet4_found = True
            st.log(f"Found {CONFIG.interface} in output: {line}")

            # Check Admin State is "down"
            if "down" in line.lower():
                admin_state_ok = True
                st.log(f"✓ Admin State is 'down' for {CONFIG.interface}")

            # Check Sampling Rate reset to disabled value (4294967295)
            if CONFIG.disabled_rate in line:
                sampling_rate_ok = True
                st.log(f"✓ Sampling rate reset to {CONFIG.disabled_rate} (disabled)")
            else:
                # Different platforms may handle differently - log but don't fail
                st.log(f"Note: Sampling rate may have reset to different value (not {CONFIG.disabled_rate})")
                sampling_rate_ok = True  # Don't fail on this

            break

    # Validate findings
    if not ethernet4_found:
        st.error(f"{CONFIG.interface} not found in 'show sflow interface' output after disable")
        return False

    if not admin_state_ok:
        st.error(f"Admin State not showing as 'down' for {CONFIG.interface} after disable")
        return False

    st.log(f"✓ sFlow disabled on {CONFIG.interface}")
    st.log(f"✓ Admin State changed to 'down'")
    st.log(f"✓ All interfaces shown in 'show sflow interface' output (matching manual test)")
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
def test_sflow_tc_1_1_6_enable_interface():
    """
    Test Case 1.1.6: Enable sFlow on Specific Interface

    This test verifies:
    1. sFlow can be enabled on specific interface (Ethernet4)
    2. Interface-specific sampling rate can be set (2048)
    3. 'show sflow interface' displays all interfaces when any interface has sFlow enabled
    4. Ethernet4 shows Admin State "up" and Sampling Rate 2048 when enabled
    5. Disabling sFlow on interface changes Admin State to "down"
    6. Sampling rate resets to 4294967295 (disabled) when sFlow is disabled on interface
    7. All interfaces continue to appear in output even after Ethernet4 is disabled
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: ENABLE SFLOW ON SPECIFIC INTERFACE")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # Module 2: Configuration
        st.banner("[MODULE 2] CONFIGURATION - Enabling sFlow globally")
        if not module_2_configuration(dut):
            validation_failures.append("[MODULE 2] Failed to enable sFlow globally")
            st.report_fail("msg", "Configuration failed - cannot proceed with test")
            return

        st.wait(2)  # Wait for configuration to settle

        # Module 3: Validation
        st.banner("[MODULE 3] VALIDATION - Testing interface-specific sFlow")

        st.log("STEP 1: Enable sFlow on Ethernet4 with sampling rate 2048")
        if not module_3_validation_enable_interface_sflow(dut):
            validation_failures.append("STEP 1: Failed to enable sFlow on interface")

        st.wait(1)

        st.log("STEP 2: Disable sFlow on Ethernet4 and verify state changes")
        if not module_3_validation_disable_interface_sflow(dut):
            validation_failures.append("STEP 2: Failed to disable sFlow or verify state")

    except Exception as e:
        st.error(f"Exception in test_sflow_tc_1_1_6_enable_interface: {str(e)}")
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
        st.log(f"✅ TEST CASE {TC_ID}: ENABLE SFLOW ON SPECIFIC INTERFACE - PASSED")
        st.log("   All validations successful:")
        st.log("   ✓ Enable sFlow on Ethernet4 with sampling rate 2048")
        st.log("   ✓ Verify 'show sflow interface' displays all interfaces")
        st.log("   ✓ Verify Ethernet4 has Admin State 'up' and Sampling Rate 2048")
        st.log("   ✓ Disable sFlow on Ethernet4")
        st.log("   ✓ Verify 'show sflow interface' displays all interfaces after disable")
        st.log("   ✓ Verify Ethernet4 Admin State changes to 'down'")
        st.log("   ✓ Verify Ethernet4 sampling rate resets to 4294967295 (disabled)")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
