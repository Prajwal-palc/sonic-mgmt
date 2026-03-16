"""
TC_SM_ISCLI_P2_158: Running Configuration Display After Port Breakout

Test Case ID: SM-ISCLI-P2-158
Author: Network Automation Team
Copyright (C) 2026, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_sm18_hw.yaml \
    tests/system/SM_ISCLI/test_sm_iscli_p2_158_running_config_display.py \
    --logs-path ./logs/sm_iscli_p2_158_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates that running configuration displays proper default values after port breakout.

  ORIGINAL BUG (FIXED):
  After port breakout, 'show runningconfiguration all' only showed 'speed auto' for 
  interfaces, hiding other default settings like admin status, MTU, etc.

  Example (BEFORE FIX):
  interface Ethernet64
   speed auto
  !
  
  Expected (AFTER FIX):
  interface Ethernet64
   admin-status up
   speed auto
   mtu 9100
  !

  Test validates:
  1. Breakout Ethernet64 to 2x400G
  2. Verify 'show runningconfiguration all' displays:
     - admin-status (up/down, not hidden)
     - speed setting
     - MTU value (9100 or configured value)
  3. Repeat with 4x200G breakout mode

Pre-requisites:
  - Topology: single-node (D1 only) | Supported: HW only
  - Testbed: testbed_sm18_hw.yaml
  - Device: 192.168.100.173
  - SONiC build with P2_158 fix

Note:
  - Test uses click CLI (show runningconfiguration all)
  - sonic-cli 'show run interface' command does not exist
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
            "description": "Breakout to 2x400G and verify running config display"
        },
        {
            "scenario_id": 2,
            "mode": "4x200G",
            "description": "Breakout to 4x200G and verify running config display"
        },
    ],
})

TC_IDS = SpyTestDict({
    "p2_158_scenario_1": "SM-ISCLI-P2-158.1",
    "p2_158_scenario_2": "SM-ISCLI-P2-158.2",
})


@pytest.fixture(scope="module", autouse=True)
def p2_158_module_hooks(request):
    global vars, data

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_158 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")

    p2_158_pre_config()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_158 MODULE CONFIGURATION - COMPLETE")
    st.banner("=" * 80)

    yield

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_158 MODULE CLEANUP - START")
    st.banner("=" * 80)

    p2_158_cleanup()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_158 MODULE CLEANUP - COMPLETE")
    st.banner("=" * 80)


def p2_158_pre_config() -> None:
    st.banner("STEP: P2_158 PRE-CONFIGURATION")
    st.log(f"Verifying connectivity to device: {vars.D1}")
    st.banner("STEP: P2_158 PRE-CONFIGURATION - COMPLETE")


def p2_158_cleanup() -> None:
    st.banner("STEP: P2_158 CLEANUP")
    
    try:
        cmd = f"interface breakout {CONFIG.test_port} mode 1x800G"
        st.config(vars.D1, cmd, type=data.cli_type)
        st.config(vars.D1, "end", type=data.cli_type)
        st.log(f"Port {CONFIG.test_port} restored to 1x800G")
    except Exception as e:
        st.error(f"Cleanup failed: {e}")

    st.banner("STEP: P2_158 CLEANUP - COMPLETE")


def apply_breakout_and_verify_running_config(dut: str, port: str, mode: str) -> bool:
    """
    Apply port breakout and verify running configuration displays proper values.
    
    ORIGINAL BUG: After breakout, running config only showed 'speed auto'
    AFTER FIX: Running config shows admin-status, speed, mtu, etc.
    """
    st.banner(f"STEP: Breakout {port} to {mode} and verify running config display")

    try:
        # Apply breakout using sonic-cli (klish)
        cmd = f"interface breakout {port} mode {mode}"
        st.log(f"Executing: {cmd}")
        output = st.config(dut, cmd, type=data.cli_type)
        
        # Exit config mode
        st.config(dut, "end", type=data.cli_type)
        
        if "Success" not in str(output):
            st.error("Breakout command failed")
            return False
        
        st.log("Breakout successful")
        
        # Get running configuration using click CLI
        # Note: Use 'click' type to access the Linux shell commands
        cmd = "show runningconfiguration all"
        st.log(f"Executing: {cmd}")
        output = st.show(dut, cmd, type='click', skip_tmpl=True)
        
        st.log(f"Running configuration output (partial):\n{output}")
        
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output
        
        # Find the interface section for our test port
        # Pattern: interface Ethernet64 ... (config lines) ... !
        interface_section_pattern = rf'interface {port}[\s\S]*?\n!'
        interface_match = re.search(interface_section_pattern, output_str)
        
        if not interface_match:
            st.error(f"FAIL: Interface {port} not found in running config")
            return False
        
        interface_section = interface_match.group(0)
        st.log(f"Interface config section:\n{interface_section}")
        
        # Validation 1: Admin status should be present (not hidden)
        st.log("Validation 1: Checking admin-status is present")
        if re.search(r'admin-status\s+(up|down)', interface_section):
            st.log("PASS: admin-status is present in running config")
        else:
            st.error("FAIL: admin-status is hidden/missing from running config")
            st.error("BUG NOT FIXED: Running config hides admin-status")
            return False
        
        # Validation 2: Speed should be present
        st.log("Validation 2: Checking speed setting is present")
        if re.search(r'speed\s+\w+', interface_section):
            st.log("PASS: speed setting is present in running config")
        else:
            st.error("FAIL: speed setting is hidden/missing from running config")
            return False
        
        # Validation 3: MTU should be present (not hidden)
        st.log("Validation 3: Checking MTU is present")
        if re.search(r'mtu\s+\d+', interface_section):
            st.log("PASS: MTU is present in running config")
        else:
            st.error("FAIL: MTU is hidden/missing from running config")
            st.error("BUG NOT FIXED: Running config hides MTU")
            return False
        
        # Validation 4: Config shows MORE than just 'speed auto'
        st.log("Validation 4: Checking config shows multiple settings (not just speed)")
        config_lines = interface_section.split('\n')
        # Count lines that are actual configuration (not interface line, not !)
        config_line_count = len([line for line in config_lines if line.strip() and not line.startswith('interface') and not line.strip() == '!'])
        
        if config_line_count > 1:
            st.log(f"PASS: Running config shows {config_line_count} settings (not just speed)")
        else:
            st.error(f"FAIL: Running config shows only {config_line_count} setting(s)")
            st.error("BUG NOT FIXED: Running config shows only 'speed auto', hides other defaults")
            return False
        
        st.log(f"SUCCESS: Running config displays all default values properly")
        return True
        
    except Exception as e:
        st.error(f"EXCEPTION: {e}")
        return False


def test_sm_iscli_p2_158_running_config_display():
    """
    TC_SM_ISCLI_P2_158: Running Configuration Display After Port Breakout
    
    Validates that after port breakout, 'show runningconfiguration all' displays
    all default values (admin-status, speed, mtu, etc.) instead of only showing
    'speed auto' and hiding other defaults.
    """
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_158: Running Config Display Validation TEST - START")
    st.banner("=" * 80)

    validation_errors = []

    for scenario in CONFIG.test_scenarios:
        scenario_id = scenario["scenario_id"]
        tc_id = f"p2_158_scenario_{scenario_id}"
        
        st.banner("=" * 80)
        st.banner(f"SCENARIO {scenario_id}: {scenario['description']}")
        st.banner("=" * 80)

        if not apply_breakout_and_verify_running_config(
            vars.D1,
            CONFIG.test_port,
            scenario["mode"]
        ):
            error_msg = f"SCENARIO {scenario_id} FAILED: Running config hides default values"
            validation_errors.append(error_msg)
            st.error(error_msg)
            st.generate_tech_support([vars.D1], f"p2_158_scenario_{scenario_id}_failed")
            st.report_tc_fail(
                TC_IDS[tc_id],
                "msg",
                "BUG NOT FIXED: Running config hides default values after breakout"
            )
            continue

        st.log(f"SCENARIO {scenario_id} PASSED")
        st.report_tc_pass(
            TC_IDS[tc_id],
            "msg",
            f"Running config displays all defaults after {scenario['mode']} breakout"
        )

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_158 TEST - COMPLETE")
    st.banner("=" * 80)

    if validation_errors:
        error_summary = f"TC_SM_ISCLI_P2_158 FAILED: {'; '.join(validation_errors)}"
        st.error(error_summary)
        st.banner("TEST RESULT: FAILED ❌")
        st.report_fail("test_case_failed", error_summary)
    else:
        success_msg = "TC_SM_ISCLI_P2_158 PASSED: Running config displays all default values after breakout"
        st.log(success_msg)
        st.banner("TEST RESULT: PASSED ✅")
        st.report_pass("test_case_passed", success_msg)
