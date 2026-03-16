"""
TC_SM_ISCLI_P2_157: Interface Status Display After Port Breakout

Test Case ID: SM-ISCLI-P2-157
Author: Network Automation Team
Copyright (C) 2026, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_sm18_hw.yaml \
    tests/system/SM_ISCLI/test_sm_iscli_p2_157_interface_status_display.py \
    --logs-path ./logs/sm_iscli_p2_157_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates that 'show interface status' displays proper default values after port breakout.

  ORIGINAL BUG (FIXED):
  After port breakout, Admin, MTU, FEC, and DHCP fields in 'show interface status' 
  displayed as "-" (unspecified) instead of showing actual default values.

  Example (BEFORE FIX):
  Ethernet64    -    -    -    -    -
  
  Expected (AFTER FIX):
  Ethernet64    -    up   800GB   9100

  Test validates:
  1. Breakout Ethernet64 to 2x400G
  2. Verify 'show interface status' displays proper values for:
     - Admin status (up/down, NOT "-")
     - Speed (800GB/400GB/etc., NOT "-")
     - MTU (9100 or actual value, NOT "-")
  3. Repeat with 4x200G breakout mode

Pre-requisites:
  - Topology: single-node (D1 only) | Supported: HW only
  - Testbed: testbed_sm18_hw.yaml
  - Device: 192.168.100.173
  - SONiC build with P2_157 fix

Note:
  - Test uses sonic-cli
  - Validates display output only
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
import re

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "test_port": "Ethernet64",
    
    "test_scenarios": [
        {
            "scenario_id": 1,
            "mode": "2x400G",
            "expected_speed": "400GB",
            "description": "Breakout to 2x400G and verify status display"
        },
        {
            "scenario_id": 2,
            "mode": "4x200G",
            "expected_speed": "200GB",
            "description": "Breakout to 4x200G and verify status display"
        },
    ],
})

TC_IDS = SpyTestDict({
    "p2_157_scenario_1": "SM-ISCLI-P2-157.1",
    "p2_157_scenario_2": "SM-ISCLI-P2-157.2",
})


@pytest.fixture(scope="module", autouse=True)
def p2_157_module_hooks(request):
    global vars, data

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_157 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")

    p2_157_pre_config()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_157 MODULE CONFIGURATION - COMPLETE")
    st.banner("=" * 80)

    yield

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_157 MODULE CLEANUP - START")
    st.banner("=" * 80)

    p2_157_cleanup()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_157 MODULE CLEANUP - COMPLETE")
    st.banner("=" * 80)


def p2_157_pre_config() -> None:
    st.banner("STEP: P2_157 PRE-CONFIGURATION")
    st.log(f"Verifying connectivity to device: {vars.D1}")
    st.banner("STEP: P2_157 PRE-CONFIGURATION - COMPLETE")


def p2_157_cleanup() -> None:
    st.banner("STEP: P2_157 CLEANUP")
    
    try:
        cmd = f"interface breakout {CONFIG.test_port} mode 1x800G"
        st.config(vars.D1, cmd, type=data.cli_type)
        st.config(vars.D1, "end", type=data.cli_type)
        st.log(f"Port {CONFIG.test_port} restored to 1x800G")
    except Exception as e:
        st.error(f"Cleanup failed: {e}")

    st.banner("STEP: P2_157 CLEANUP - COMPLETE")


def apply_breakout_and_verify_status(dut: str, port: str, mode: str, expected_speed: str) -> bool:
    """
    Apply port breakout and verify interface status displays proper values.
    
    ORIGINAL BUG: After breakout, status showed "-" for Admin, Speed, MTU
    AFTER FIX: Status shows actual values
    """
    st.banner(f"STEP: Breakout {port} to {mode} and verify status display")

    try:
        # Apply breakout
        cmd = f"interface breakout {port} mode {mode}"
        st.log(f"Executing: {cmd}")
        output = st.config(dut, cmd, type=data.cli_type)
        
        # Exit config mode
        st.config(dut, "end", type=data.cli_type)
        
        if "Success" not in str(output):
            st.error("Breakout command failed")
            return False
        
        st.log("Breakout successful")
        
        # Get interface status
        cmd = "show interface status | no-more"
        st.log(f"Executing: {cmd}")
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)
        
        st.log(f"Interface status output:\n{output}")
        
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output
        
        # Find the line for our test port
        port_line_pattern = rf'{port}\s+([^\n]+)'
        port_match = re.search(port_line_pattern, output_str)
        
        if not port_match:
            st.error(f"FAIL: Port {port} not found in status output")
            return False
        
        port_line = port_match.group(0)
        st.log(f"Port status line: {port_line}")
        
        # Validation 1: Admin status should NOT be "-"
        st.log("Validation 1: Checking Admin status is not '-'")
        # Admin is typically "up" or "down"
        if re.search(rf'{port}\s+\S*\s+up', port_line):
            st.log("PASS: Admin status shows 'up' (not '-')")
        elif re.search(rf'{port}\s+\S*\s+down', port_line):
            st.log("PASS: Admin status shows 'down' (not '-')")
        else:
            st.error("FAIL: Admin status appears to be '-' or missing")
            return False
        
        # Validation 2: Speed should NOT be "-"
        st.log("Validation 2: Checking Speed is not '-'")
        speed_pattern = r'(\d+G[B]?)'
        speed_matches = re.findall(speed_pattern, port_line)
        if speed_matches:
            st.log(f"PASS: Speed field shows value: {speed_matches} (not '-')")
        else:
            st.error("FAIL: Speed field appears to be '-' or missing")
            return False
        
        # Validation 3: MTU should NOT be "-"
        st.log("Validation 3: Checking MTU is not '-'")
        mtu_pattern = r'(9\d{3})'  # Match 9100, 9216, etc.
        mtu_match = re.search(mtu_pattern, port_line)
        if mtu_match:
            st.log(f"PASS: MTU field shows value: {mtu_match.group(1)} (not '-')")
        else:
            st.error("FAIL: MTU field appears to be '-' or missing")
            return False
        
        st.log(f"SUCCESS: All status fields display proper values (not '-')")
        return True
        
    except Exception as e:
        st.error(f"EXCEPTION: {e}")
        return False


def test_sm_iscli_p2_157_interface_status_display():
    """
    TC_SM_ISCLI_P2_157: Interface Status Display After Port Breakout
    
    Validates that after port breakout, 'show interface status' displays
    proper default values instead of "-" for Admin, Speed, and MTU fields.
    """
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_157: Interface Status Display Validation TEST - START")
    st.banner("=" * 80)

    validation_errors = []

    for scenario in CONFIG.test_scenarios:
        scenario_id = scenario["scenario_id"]
        tc_id = f"p2_157_scenario_{scenario_id}"
        
        st.banner("=" * 80)
        st.banner(f"SCENARIO {scenario_id}: {scenario['description']}")
        st.banner("=" * 80)

        if not apply_breakout_and_verify_status(
            vars.D1,
            CONFIG.test_port,
            scenario["mode"],
            scenario["expected_speed"]
        ):
            error_msg = f"SCENARIO {scenario_id} FAILED: Status display shows '-' instead of values"
            validation_errors.append(error_msg)
            st.error(error_msg)
            st.generate_tech_support([vars.D1], f"p2_157_scenario_{scenario_id}_failed")
            st.report_tc_fail(
                TC_IDS[tc_id],
                "msg",
                "BUG NOT FIXED: Interface status displays '-' after breakout"
            )
            continue

        st.log(f"SCENARIO {scenario_id} PASSED")
        st.report_tc_pass(
            TC_IDS[tc_id],
            "msg",
            f"Interface status displays proper values after {scenario['mode']} breakout"
        )

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_157 TEST - COMPLETE")
    st.banner("=" * 80)

    if validation_errors:
        error_summary = f"TC_SM_ISCLI_P2_157 FAILED: {'; '.join(validation_errors)}"
        st.error(error_summary)
        st.banner("TEST RESULT: FAILED ❌")
        st.report_fail("test_case_failed", error_summary)
    else:
        success_msg = "TC_SM_ISCLI_P2_157 PASSED: Interface status displays proper values after breakout"
        st.log(success_msg)
        st.banner("TEST RESULT: PASSED ✅")
        st.report_pass("test_case_passed", success_msg)
