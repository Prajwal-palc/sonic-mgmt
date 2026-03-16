"""
TC_SM_ISCLI_P2_4: Show Interface Breakout Resources Command Validation

Test Case ID: SM-ISCLI-P2-4
Author: Network Automation Team
Copyright (C) 2026, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_sm18_hw.yaml \
    tests/system/SM_ISCLI/test_sm_iscli_p2_4_show_breakout_resources.py \
    --logs-path ./logs/sm_iscli_p2_4_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates 'show interface breakout resources' command displays proper pipeline breakdown.

  ORIGINAL BUG (FIXED):
  Command showed incorrect generic system-wide statistics instead of per-pipeline breakdown:
    - Displayed: "Breakout-capable ports: 0"
    - Missing: Pipeline table with per-pipeline resource information
    - Root cause: Platform information (platform.json, hwsku.json) not available

  EXPECTED OUTPUT (AFTER FIX):
    Maximum ports supported in the system: 96
    Current ports in the system: 66
    --------------------------------------------------
    Pipeline Ports Max-Ports Front-panel-ports
    --------------------------------------------------
    pipe0    4     32        Ethernet0, Ethernet16, Ethernet24, Ethernet8
    pipe1    4     32        Ethernet32, Ethernet40, Ethernet48, Ethernet56
    ...

  Test validates the fix by:
  1. Verifying 'show interface breakout resources' displays pipeline breakdown table
  2. Checking all required fields are present:
     - Maximum ports supported in the system
     - Current ports in the system
     - Pipeline table with columns: Pipeline, Ports, Max-Ports, Front-panel-ports
  3. Validating that pipelines are listed with proper resource information
  4. Ensuring all values are non-empty
  5. Verifying table format and structure

Pre-requisites:
  - Topology: single-node (D1 only) | Supported: HW only
  - Testbed: testbed_sm18_hw.yaml (single hardware device)
  - Device: 192.168.100.173 (Supermicro SSE-T8164S with 800G ports)
  - Credentials: admin/sonic@123
  - SONiC build: portbreakout-1203-1826 or later with P2_4 fix

Note:
  - This is a read-only test (no configuration changes)
  - Tests sonic-cli show command only
  - No cleanup needed (no config changes made)
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
    # Expected table columns
    "expected_resource_headers": ["Pipeline", "Ports", "Max-Ports", "Front-panel-ports"],
    
    # Expected summary fields
    "expected_summary_fields": [
        "Maximum ports supported in the system",
        "Current ports in the system"
    ],
    
    # Validation thresholds
    "min_pipelines": 1,         # At least 1 pipeline should be shown
    "min_max_ports": 10,        # Maximum ports should be at least 10
    "min_current_ports": 1,     # Current ports should be at least 1
})

# Test Case IDs
TC_IDS = SpyTestDict({
    "p2_4_show_resources": "SM-ISCLI-P2-4.1",
})


#################################################################
# Module-level Fixture
#################################################################

@pytest.fixture(scope="module", autouse=True)
def p2_4_module_hooks(request):
    """
    Module-level setup and teardown.

    This fixture runs once before all tests in the module and once after all tests complete.
    It handles topology initialization and ensures the device is accessible.

    Args:
        request: pytest request object

    Yields:
        None (control returns to test execution)
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_4 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get device variables
    vars = st.ensure_min_topology("D1")

    # Set CLI type
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")

    # Pre-configuration (none needed, read-only test)
    p2_4_pre_config()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_4 MODULE CONFIGURATION - COMPLETE")
    st.banner("=" * 80)

    # Yield to test execution
    yield

    # Cleanup (none needed, read-only test)
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_4 MODULE CLEANUP - START")
    st.banner("=" * 80)

    p2_4_cleanup()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_4 MODULE CLEANUP - COMPLETE")
    st.banner("=" * 80)


#################################################################
# Pre-Configuration and Cleanup Functions
#################################################################

def p2_4_pre_config() -> None:
    """
    Pre-configuration for SM_ISCLI_P2_4 test.

    This is a read-only test, so no configuration changes are needed.

    Returns:
        None
    """
    st.banner("STEP: P2_4 PRE-CONFIGURATION")

    st.log("INFO: This is a read-only test - no configuration changes needed")
    st.log("INFO: Test will verify 'show interface breakout resources' command output")

    st.log(f"Verifying connectivity to device: {vars.D1}")

    st.banner("STEP: P2_4 PRE-CONFIGURATION - COMPLETE")


def p2_4_cleanup() -> None:
    """
    Cleanup configuration after SM_ISCLI_P2_4 test.

    This is a read-only test, so no cleanup is needed.

    Returns:
        None
    """
    st.banner("STEP: P2_4 CLEANUP")

    st.log("INFO: No cleanup needed - test made no configuration changes")

    st.banner("STEP: P2_4 CLEANUP - COMPLETE")


#################################################################
# Helper Functions
#################################################################

def verify_show_interface_breakout_resources(dut: str) -> bool:
    """
    Verify 'show interface breakout resources' command displays pipeline information.

    ORIGINAL BUG: Command showed generic system-wide statistics without pipeline breakdown.
    
    EXPECTED OUTPUT (AFTER FIX):
        Maximum ports supported in the system: 96
        Current ports in the system: 66
        --------------------------------------------------
        Pipeline Ports Max-Ports Front-panel-ports
        --------------------------------------------------
        pipe0    4     32        Ethernet0, Ethernet16, Ethernet24, Ethernet8
        pipe1    4     32        Ethernet32, Ethernet40, Ethernet48, Ethernet56
        ...

    Validation:
        - Output contains "Maximum ports supported" with a number
        - Output contains "Current ports in the system" with a number
        - Output contains pipeline table with headers: Pipeline, Ports, Max-Ports, Front-panel-ports
        - At least one pipeline entry (pipe0, pipe1, etc.) is shown
        - All values are non-empty (not blank)
        - Pipeline entries have proper format: pipeN

    Args:
        dut: Device under test

    Returns:
        bool: True if command output is valid, False otherwise
    """
    st.banner("STEP: Verify 'show interface breakout resources' command")

    try:
        # Execute show command
        cmd = "show interface breakout resources | no-more"
        st.log(f"Executing: {cmd}")
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)

        st.log(f"Command output:\n{output}")

        # Convert to string if needed
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output

        # Validation 1: Check for maximum ports supported
        st.log("Validation 1: Checking for 'Maximum ports supported' field")
        max_ports_pattern = r'Maximum ports supported in the system:\s+(\d+)'
        max_match = re.search(max_ports_pattern, output_str)
        if not max_match:
            st.error("FAIL: 'Maximum ports supported' field not found or empty")
            st.error("BUG NOT FIXED: Command may still be showing old format")
            return False
        max_ports = int(max_match.group(1))
        st.log(f"PASS: Maximum ports supported = {max_ports}")

        # Validation 2: Check for current ports in system
        st.log("Validation 2: Checking for 'Current ports in the system' field")
        current_ports_pattern = r'Current ports in the system:\s+(\d+)'
        current_match = re.search(current_ports_pattern, output_str)
        if not current_match:
            st.error("FAIL: 'Current ports in the system' field not found or empty")
            return False
        current_ports = int(current_match.group(1))
        st.log(f"PASS: Current ports in the system = {current_ports}")

        # Validation 3: Check for pipeline table headers
        st.log("Validation 3: Checking for pipeline table headers")
        for header in CONFIG.expected_resource_headers:
            if header not in output_str:
                st.error(f"FAIL: Missing expected header: {header}")
                st.error("BUG NOT FIXED: Pipeline table not present")
                return False
        st.log("PASS: All expected headers found (Pipeline, Ports, Max-Ports, Front-panel-ports)")

        # Validation 4: Check for at least one pipeline entry
        st.log("Validation 4: Checking for pipeline entries")
        pipe_pattern = r'pipe\d+\s+\d+\s+\d+\s+Ethernet'
        pipe_matches = re.findall(pipe_pattern, output_str)
        if not pipe_matches:
            st.error("FAIL: No pipeline entries found in output")
            st.error("BUG NOT FIXED: Pipeline breakdown missing")
            return False

        num_pipelines = len(pipe_matches)
        st.log(f"PASS: Found {num_pipelines} pipeline entries")

        # Validation 5: Verify minimum number of pipelines
        st.log("Validation 5: Checking minimum pipelines threshold")
        if num_pipelines < CONFIG.min_pipelines:
            st.error(f"FAIL: Only {num_pipelines} pipelines found, expected at least {CONFIG.min_pipelines}")
            return False
        st.log(f"PASS: Sufficient pipelines found ({num_pipelines} >= {CONFIG.min_pipelines})")

        # Validation 6: Verify ports count is reasonable
        st.log("Validation 6: Validating port counts")
        if current_ports > max_ports:
            st.error(f"FAIL: Current ports ({current_ports}) exceeds maximum ({max_ports})")
            return False
        if current_ports <= 0:
            st.error(f"FAIL: Current ports is zero or negative ({current_ports})")
            return False
        if max_ports < CONFIG.min_max_ports:
            st.error(f"FAIL: Maximum ports ({max_ports}) is too low (expected at least {CONFIG.min_max_ports})")
            return False
        st.log(f"PASS: Port counts are valid (current: {current_ports}, max: {max_ports})")

        # Validation 7: Verify pipeline entries show front-panel ports
        st.log("Validation 7: Checking front-panel ports are listed")
        ethernet_pattern = r'Ethernet\d+'
        ethernet_matches = re.findall(ethernet_pattern, output_str)
        if not ethernet_matches:
            st.error("FAIL: No Ethernet ports listed in Front-panel-ports column")
            return False
        
        unique_ports = set(ethernet_matches)
        st.log(f"PASS: Found {len(unique_ports)} unique Ethernet ports in pipeline table")

        # Validation 8: Check that old incorrect format is NOT present
        st.log("Validation 8: Verifying old incorrect format is not present")
        old_format_indicators = [
            "Breakout-capable ports",
            "Max breakout ports (ASIC limit)",
            "Warning: Platform hwsku.json not found"
        ]
        
        for indicator in old_format_indicators:
            if indicator in output_str:
                st.error(f"FAIL: Old format detected - found '{indicator}'")
                st.error("BUG NOT FIXED: Command still showing old generic format")
                return False
        
        st.log("PASS: Old incorrect format is not present - bug is fixed")

        st.log("SUCCESS: 'show interface breakout resources' displays proper pipeline breakdown")
        return True

    except Exception as e:
        st.error(f"EXCEPTION: Failed to verify 'show interface breakout resources': {e}")
        return False


#################################################################
# Main Test Function
#################################################################

def test_sm_iscli_p2_4_show_breakout_resources():
    """
    TC_SM_ISCLI_P2_4: Show Interface Breakout Resources Command Validation

    Test validates that 'show interface breakout resources' command displays proper
    pipeline breakdown instead of generic system-wide statistics.

    Test Steps:
        1. Execute 'show interface breakout resources' command
        2. Verify maximum ports and current ports fields are present
        3. Validate pipeline table structure with all expected columns
        4. Check pipeline entries are listed with proper values
        5. Verify front-panel ports are shown for each pipeline
        6. Ensure old incorrect format is not present

    Expected Results:
        - Command displays pipeline breakdown table
        - Maximum ports and current ports fields populated
        - Pipeline table shows: Pipeline, Ports, Max-Ports, Front-panel-ports
        - At least one pipeline entry present
        - Front-panel Ethernet ports listed
        - Old generic format not shown
        - No warnings about missing platform files

    Returns:
        None (uses st.report_pass/fail for test result reporting)
    """
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_4: Show Interface Breakout Resources Validation TEST - START")
    st.banner("=" * 80)

    # Track validation errors
    validation_errors = []

    #################################################################
    # STEP 1: Verify 'show interface breakout resources' command
    #################################################################
    st.banner("=" * 80)
    st.banner("STEP 1: Verify 'show interface breakout resources' displays pipeline breakdown")
    st.banner("=" * 80)

    if not verify_show_interface_breakout_resources(vars.D1):
        error_msg = "STEP 1 FAILED: 'show interface breakout resources' does not display proper pipeline breakdown"
        validation_errors.append(error_msg)
        st.error(error_msg)
        st.generate_tech_support([vars.D1], "p2_4_show_resources_failed")
        st.report_tc_fail(
            TC_IDS.p2_4_show_resources,
            "msg",
            "BUG NOT FIXED: 'show interface breakout resources' still shows incorrect output"
        )
    else:
        st.log("STEP 1 PASSED: 'show interface breakout resources' displays proper pipeline breakdown")
        st.report_tc_pass(
            TC_IDS.p2_4_show_resources,
            "msg",
            "'show interface breakout resources' command works correctly with pipeline breakdown"
        )

    #################################################################
    # Final Result
    #################################################################
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_4: Show Interface Breakout Resources Validation TEST - COMPLETE")
    st.banner("=" * 80)

    if validation_errors:
        error_summary = f"TC_SM_ISCLI_P2_4 FAILED with {len(validation_errors)} error(s): {'; '.join(validation_errors)}"
        st.error(error_summary)
        st.banner("TEST RESULT: FAILED ❌")
        st.report_fail("test_case_failed", error_summary)
    else:
        success_msg = "TC_SM_ISCLI_P2_4 PASSED: 'show interface breakout resources' displays correct pipeline breakdown"
        st.log(success_msg)
        st.banner("TEST RESULT: PASSED ✅")
        st.report_pass("test_case_passed", success_msg)
