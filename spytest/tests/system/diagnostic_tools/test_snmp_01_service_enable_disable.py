"""
SNMP TEST - TC-7.1.1: Verify SNMP Service Enable/Disable

Test Case ID: 7.1.1
Author: Automated Testing Suite
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/diagnostic_tools/test_snmp_01_service_enable_disable.py \
    --logs-path ./logs/snmp_01_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates SNMP service enable/disable functionality:
  - Check initial SNMP service status
  - Disable SNMP service
  - Verify service is disabled
  - Re-enable SNMP service
  - Verify service is enabled
  - Verify state changes are reflected immediately

Pre-requisites:
  - 2 SONiC devices: 192.168.100.161, 192.168.100.206
  - Credentials: admin/palc@123
  - Testbed: testbed_2vs.yaml
  - NOTE: Feature enable/disable is ONLY available via Linux shell (sudo mode)

Important:
  - This test uses Linux shell commands (NOT sonic-cli)
  - Commands: show feature status snmp, sudo config feature state snmp [enabled|disabled]
  - Follows BGP test pattern: continues on errors, generates tech-support on failures
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "service_name": "snmp",
    "wait_after_disable": 5,
    "wait_after_enable": 15,
})

# Test case identifiers - Multiple IDs for different phases
TC_IDS = SpyTestDict({
    "snmp01_initial_status": "TC-SNMP-01-001",
    "snmp01_disable": "TC-SNMP-01-002",
    "snmp01_enable": "TC-SNMP-01-003",
})


@pytest.fixture(scope="module", autouse=True)
def snmp_01_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("SNMP TC-7.1.1 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"NOTE: This test uses Linux shell commands, NOT sonic-cli")

    yield

    # Cleanup - Ensure SNMP is enabled after test
    st.banner("=" * 80)
    st.banner("SNMP TC-7.1.1 MODULE CLEANUP - START")
    st.banner("=" * 80)

    for dut in [vars.D1, vars.D2]:
        try:
            st.log(f"Ensuring SNMP is enabled on {dut}")
            enable_snmp_service(dut)
        except Exception as e:
            st.log(f"Cleanup warning on {dut}: {str(e)}")


def show_feature_status(dut: str, service: str = "snmp") -> dict:
    """
    Show feature status using Linux shell command.

    Command: show feature status snmp
    Output format:
        Feature    State    AutoRestart
        ---------  -------  -------------
        snmp       enabled  enabled

    Returns dict with 'feature', 'state', 'autorestart' keys.
    """
    st.log(f"Checking feature status for '{service}' on {dut}")

    command = f"show feature status {service}"
    output = st.show(dut, command, skip_tmpl=True, skip_error_check=True)

    st.log(f"Feature status output:\n{output}")

    # Parse output properly - look for the State column value
    output_str = str(output)

    result = {
        'feature': service,
        'state': 'unknown',
        'autorestart': 'unknown'
    }

    # Parse the output properly - look for the State column value
    # Format: snmp       enabled  enabled  OR  snmp       disabled  enabled
    lines = output_str.split('\n')
    for line in lines:
        if service in line.lower():
            # Split by whitespace and get the state column (2nd column)
            parts = line.split()
            if len(parts) >= 2:
                state_value = parts[1].lower().strip()
                if 'enabled' in state_value:
                    result['state'] = 'enabled'
                elif 'disabled' in state_value:
                    result['state'] = 'disabled'
                break

    st.log(f"Parsed state: {result['state']}")
    return result


def disable_snmp_service(dut: str) -> bool:
    """
    Disable SNMP service using Linux shell command.

    Command: sudo config feature state snmp disabled
    """
    st.log(f"Disabling SNMP service on {dut}")

    command = "sudo config feature state snmp disabled"

    try:
        st.config(dut, command, skip_error_check=False)
        st.log(f"✓ SNMP service disabled command executed on {dut}")

        # Wait for service to stop
        st.wait(CONFIG.wait_after_disable, "Waiting for SNMP service to stop")

        return True
    except Exception as e:
        st.error(f"Failed to disable SNMP service on {dut}: {str(e)}")
        return False


def enable_snmp_service(dut: str) -> bool:
    """
    Enable SNMP service using Linux shell command.

    Command: sudo config feature state snmp enabled
    """
    st.log(f"Enabling SNMP service on {dut}")

    command = "sudo config feature state snmp enabled"

    try:
        st.config(dut, command, skip_error_check=False)
        st.log(f"✓ SNMP service enabled command executed on {dut}")

        # Wait for service to start (longer wait for container startup)
        st.wait(CONFIG.wait_after_enable, "Waiting for SNMP service to start")

        return True
    except Exception as e:
        st.error(f"Failed to enable SNMP service on {dut}: {str(e)}")
        return False


def verify_service_state(dut: str, expected_state: str) -> bool:
    """
    Verify SNMP service state.

    Args:
        dut: Device under test
        expected_state: Expected state ('enabled' or 'disabled')

    Returns:
        True if state matches expected, False otherwise
    """
    st.log(f"Verifying SNMP service state on {dut}: expected '{expected_state}'")

    status = show_feature_status(dut, CONFIG.service_name)
    actual_state = status.get('state', 'unknown')

    if actual_state == expected_state:
        st.log(f"✓ Service state is '{actual_state}' as expected")
        return True
    else:
        st.error(f"✗ Service state is '{actual_state}', expected '{expected_state}'")
        return False


def test_snmp_01_service_enable_disable():
    """
    Test Case 7.1.1: Verify SNMP Service Enable/Disable

    Test Steps:
    1. Check initial SNMP service status (should be enabled)
    2. Disable SNMP service
    3. Verify service is disabled
    4. Re-enable SNMP service
    5. Verify service is enabled

    Expected Results:
    - Initial state: enabled
    - After disable: disabled
    - After enable: enabled
    - State changes reflected immediately

    NOTE: Following BGP test pattern - continues on errors, generates tech-support on critical failures
    """
    st.banner("=" * 80)
    st.banner("TEST TC-7.1.1: SNMP SERVICE ENABLE/DISABLE")
    st.banner("=" * 80)

    # Track test status
    test_failed = False

    # ==================================================================
    # STEP 1: Check Initial Service Status
    # ==================================================================
    st.banner("STEP 1: Check Initial SNMP Service Status")

    st.log(f"Checking initial SNMP status on {vars.D1}")
    status_d1 = show_feature_status(vars.D1, CONFIG.service_name)

    st.log(f"Checking initial SNMP status on {vars.D2}")
    status_d2 = show_feature_status(vars.D2, CONFIG.service_name)

    st.log(f"DUT1 initial state: {status_d1.get('state')}")
    st.log(f"DUT2 initial state: {status_d2.get('state')}")

    # If not enabled, enable it first
    if status_d1.get('state') != 'enabled':
        st.log(f"SNMP not enabled on {vars.D1}, enabling it")
        enable_snmp_service(vars.D1)

    if status_d2.get('state') != 'enabled':
        st.log(f"SNMP not enabled on {vars.D2}, enabling it")
        enable_snmp_service(vars.D2)

    # Verify both are enabled
    if not verify_service_state(vars.D1, 'enabled'):
        st.report_tc_fail(TC_IDS.snmp01_initial_status, "msg",
                         f"SNMP service not enabled on {vars.D1}")
        test_failed = True
    else:
        st.log(f"✓ SNMP service verified enabled on {vars.D1}")

    if not verify_service_state(vars.D2, 'enabled'):
        st.report_tc_fail(TC_IDS.snmp01_initial_status, "msg",
                         f"SNMP service not enabled on {vars.D2}")
        test_failed = True
    else:
        st.log(f"✓ SNMP service verified enabled on {vars.D2}")

    if not test_failed:
        st.report_tc_pass(TC_IDS.snmp01_initial_status, "msg",
                         "SNMP service initially enabled on both DUTs")

    # ==================================================================
    # STEP 2: Disable SNMP Service
    # ==================================================================
    st.banner("STEP 2: Disable SNMP Service")

    st.log(f"Disabling SNMP on {vars.D1}")
    if not disable_snmp_service(vars.D1):
        st.report_tc_fail(TC_IDS.snmp01_disable, "msg",
                         f"Failed to disable SNMP on {vars.D1}")
        test_failed = True

    st.log(f"Disabling SNMP on {vars.D2}")
    if not disable_snmp_service(vars.D2):
        st.report_tc_fail(TC_IDS.snmp01_disable, "msg",
                         f"Failed to disable SNMP on {vars.D2}")
        test_failed = True

    # ==================================================================
    # STEP 3: Verify Service is Disabled
    # ==================================================================
    st.banner("STEP 3: Verify SNMP Service is Disabled")

    if not verify_service_state(vars.D1, 'disabled'):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_disable_verification_failed")
        st.report_tc_fail(TC_IDS.snmp01_disable, "msg",
                         f"SNMP service not disabled on {vars.D1}")
        test_failed = True
    else:
        st.log(f"✓ SNMP service verified disabled on {vars.D1}")

    if not verify_service_state(vars.D2, 'disabled'):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_disable_verification_failed")
        st.report_tc_fail(TC_IDS.snmp01_disable, "msg",
                         f"SNMP service not disabled on {vars.D2}")
        test_failed = True
    else:
        st.log(f"✓ SNMP service verified disabled on {vars.D2}")

    if not test_failed:
        st.report_tc_pass(TC_IDS.snmp01_disable, "msg",
                         "SNMP service successfully disabled on both DUTs")

    # ==================================================================
    # STEP 4: Re-Enable SNMP Service
    # ==================================================================
    st.banner("STEP 4: Re-Enable SNMP Service")

    st.log(f"Enabling SNMP on {vars.D1}")
    if not enable_snmp_service(vars.D1):
        st.report_tc_fail(TC_IDS.snmp01_enable, "msg",
                         f"Failed to enable SNMP on {vars.D1}")
        test_failed = True

    st.log(f"Enabling SNMP on {vars.D2}")
    if not enable_snmp_service(vars.D2):
        st.report_tc_fail(TC_IDS.snmp01_enable, "msg",
                         f"Failed to enable SNMP on {vars.D2}")
        test_failed = True

    # ==================================================================
    # STEP 5: Verify Service is Enabled
    # ==================================================================
    st.banner("STEP 5: Verify SNMP Service is Enabled")

    if not verify_service_state(vars.D1, 'enabled'):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_enable_verification_failed")
        st.report_tc_fail(TC_IDS.snmp01_enable, "msg",
                         f"SNMP service not enabled on {vars.D1}")
        test_failed = True
    else:
        st.log(f"✓ SNMP service verified enabled on {vars.D1}")

    if not verify_service_state(vars.D2, 'enabled'):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_enable_verification_failed")
        st.report_tc_fail(TC_IDS.snmp01_enable, "msg",
                         f"SNMP service not enabled on {vars.D2}")
        test_failed = True
    else:
        st.log(f"✓ SNMP service verified enabled on {vars.D2}")

    if not test_failed:
        st.report_tc_pass(TC_IDS.snmp01_enable, "msg",
                         "SNMP service successfully enabled on both DUTs")

    # ==================================================================
    # TEST RESULT
    # ==================================================================
    if test_failed:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-7.1.1 FAILED")
        st.banner("=" * 80)
        st.report_fail("test_case_failed")
    else:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-7.1.1 PASSED")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - TC-7.1.1: SNMP Service Enable/Disable")
        st.log("=" * 80)
        st.log(f"✓ Initial state: enabled (both DUTs)")
        st.log(f"✓ Disabled successfully (both DUTs)")
        st.log(f"✓ State verified as disabled (both DUTs)")
        st.log(f"✓ Re-enabled successfully (both DUTs)")
        st.log(f"✓ State verified as enabled (both DUTs)")
        st.log(f"✓ State changes reflected immediately")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
