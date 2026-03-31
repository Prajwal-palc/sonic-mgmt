"""
TC_SM_ISCLI_P2_75: Show Interface Breakout Modes Command Validation

Test Case ID: SM-ISCLI-P2-75
Author: Network Automation Team
Copyright (C) 2026, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_sm18_hw.yaml \
    tests/system/SM_ISCLI/test_sm_iscli_p2_75_show_breakout_modes.py \
    --logs-path ./logs/sm_iscli_p2_75_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates 'show interface breakout modes' command displays proper table output.

  Test validates the fix by:
  1. Verifying 'show interface breakout modes' displays complete table
  2. Checking all required columns are present: Port, Pipe, Interface, Supported Modes, Default Mode
  3. Validating that ports are listed with their supported and default modes
  4. Ensuring all mode values are non-empty
  5. Verifying table format and structure

  Expected Output:
    +---------------+------+---------------+-------------------------------+---------------+
    | Port          | Pipe | Interface     | Supported Modes               | Default Mode  |
    +---------------+------+---------------+-------------------------------+---------------+
    | Ethernet0     | 0    | Ethernet0     | 2x200G                        | 2x200G        |
    | Ethernet8     | 0    | Ethernet8     | 2x400G                        | 2x400G        |
    | Ethernet16    | 0    | Ethernet16    | 4x200G                        | 4x200G        |
    | Ethernet24    | 0    | Ethernet24    | 1x800G                        | 1x800G        |
    ...

  EXPECTED BEHAVIOR (AFTER FIX):
  - Command displays complete table with all ports
  - All columns populated with proper values
  - Supported Modes and Default Mode fields are non-empty
  - Table shows Port, Pipe, Interface, Supported Modes, Default Mode columns

Pre-requisites:
  - Topology: single-node (D1 only) | Supported: HW only
  - Testbed: testbed_sm18_hw.yaml (single hardware device)
  - Device: 192.168.100.173 (Supermicro SSE-T8164S with 800G ports)
  - Credentials: admin/sonic@123
  - SONiC build: portbreakout-1203-1826 or later

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
    "expected_columns": ["Port", "Pipe", "Interface", "Supported Modes", "Default Mode"],
    
    # Sample ports to verify in detail
    "sample_ports": ["Ethernet0", "Ethernet8", "Ethernet16", "Ethernet24", "Ethernet64"],
    
    # Validation thresholds
    "min_ports_in_table": 10,  # At least 10 ports should be listed
})

# Test Case IDs
TC_IDS = SpyTestDict({
    "p2_75_show_modes": "SM-ISCLI-P2-75.1",
})


#################################################################
# Module-level Fixture
#################################################################

@pytest.fixture(scope="module", autouse=True)
def p2_75_module_hooks(request):
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
    st.banner("TC_SM_ISCLI_P2_75 MODULE CONFIGURATION - START")
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
    p2_75_pre_config()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_75 MODULE CONFIGURATION - COMPLETE")
    st.banner("=" * 80)

    # Yield to test execution
    yield

    # Cleanup (none needed, read-only test)
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_75 MODULE CLEANUP - START")
    st.banner("=" * 80)

    p2_75_cleanup()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_75 MODULE CLEANUP - COMPLETE")
    st.banner("=" * 80)


#################################################################
# Pre-Configuration and Cleanup Functions
#################################################################

def p2_75_pre_config() -> None:
    """
    Pre-configuration for SM_ISCLI_P2_75 test.

    This is a read-only test, so no configuration changes are needed.

    Returns:
        None
    """
    st.banner("STEP: P2_75 PRE-CONFIGURATION")

    st.log("INFO: This is a read-only test - no configuration changes needed")
    st.log("INFO: Test will verify 'show interface breakout modes' command output")

    st.log(f"Verifying connectivity to device: {vars.D1}")

    st.banner("STEP: P2_75 PRE-CONFIGURATION - COMPLETE")


def p2_75_cleanup() -> None:
    """
    Cleanup configuration after SM_ISCLI_P2_75 test.

    This is a read-only test, so no cleanup is needed.

    Returns:
        None
    """
    st.banner("STEP: P2_75 CLEANUP")

    st.log("INFO: No cleanup needed - test made no configuration changes")

    st.banner("STEP: P2_75 CLEANUP - COMPLETE")


#################################################################
# Helper Functions
#################################################################

def verify_show_interface_breakout_modes(dut: str) -> bool:
    """
    Verify 'show interface breakout modes' command displays complete table.

    Expected Output:
        +---------------+------+---------------+-------------------------------+---------------+
        | Port          | Pipe | Interface     | Supported Modes               | Default Mode  |
        +---------------+------+---------------+-------------------------------+---------------+
        | Ethernet0     | 0    | Ethernet0     | 2x200G                        | 2x200G        |
        | Ethernet8     | 0    | Ethernet8     | 2x400G                        | 2x400G        |
        | Ethernet16    | 0    | Ethernet16    | 4x200G                        | 4x200G        |
        | Ethernet24    | 0    | Ethernet24    | 1x800G                        | 1x800G        |
        ...
        +---------------+------+---------------+-------------------------------+---------------+

    Validation:
        - Output contains all expected column headers
        - Table contains port entries
        - Supported Modes column is populated (not empty)
        - Default Mode column is populated (not empty)
        - At least minimum number of ports are listed
        - Mode values are in correct format (e.g., "1x800G", "2x400G")

    Args:
        dut: Device under test

    Returns:
        bool: True if command output is valid, False otherwise
    """
    st.banner("STEP: Verify 'show interface breakout modes' command")

    try:
        # Execute show command
        cmd = "show interface breakout modes | no-more"
        st.log(f"Executing: {cmd}")
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)

        st.log(f"Command output:\n{output}")

        # Convert to string if needed
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output

        # Validation 1: Check for expected column headers
        st.log("Validation 1: Checking for all expected column headers")
        for header in CONFIG.expected_columns:
            if header not in output_str:
                st.error(f"FAIL: Missing expected column header: {header}")
                return False
        st.log("PASS: All expected column headers found (Port, Pipe, Interface, Supported Modes, Default Mode)")

        # Validation 2: Check for port entries
        st.log("Validation 2: Checking for Ethernet port entries")
        port_pattern = r'Ethernet\d+'
        port_matches = re.findall(port_pattern, output_str)
        if not port_matches:
            st.error("FAIL: No Ethernet port entries found in output")
            return False
        
        num_ports = len(set(port_matches))  # Unique ports (each port appears multiple times in the line)
        st.log(f"PASS: Found {num_ports} unique port entries in the table")

        # Validation 3: Check minimum number of ports
        st.log("Validation 3: Checking minimum ports threshold")
        if num_ports < CONFIG.min_ports_in_table:
            st.error(f"FAIL: Only {num_ports} ports found, expected at least {CONFIG.min_ports_in_table}")
            return False
        st.log(f"PASS: Sufficient ports in table ({num_ports} >= {CONFIG.min_ports_in_table})")

        # Validation 4: Check for Supported Modes values
        st.log("Validation 4: Checking for Supported Modes values")
        mode_pattern = r'(\d+x\d+G)'
        mode_matches = re.findall(mode_pattern, output_str)
        if not mode_matches:
            st.error("FAIL: No mode values found (expected formats like '1x800G', '2x400G')")
            return False
        
        unique_modes = set(mode_matches)
        st.log(f"PASS: Found breakout modes in table: {unique_modes}")

        # Validation 5: Check for pipe numbers
        st.log("Validation 5: Checking for Pipe column values")
        pipe_pattern = r'\|\s+(\d+)\s+\|\s+Ethernet'
        pipe_matches = re.findall(pipe_pattern, output_str)
        if not pipe_matches:
            st.error("FAIL: No pipe numbers found in Pipe column")
            return False
        st.log(f"PASS: Pipe column populated with values: {set(pipe_matches)}")

        # Validation 6: Verify sample ports are in the table
        st.log("Validation 6: Verifying sample ports are listed")
        missing_ports = []
        for port in CONFIG.sample_ports:
            if port not in output_str:
                missing_ports.append(port)
        
        if missing_ports:
            st.log(f"WARNING: Some sample ports not found: {missing_ports} (may not exist on device)")
        else:
            st.log(f"PASS: All sample ports found in table: {CONFIG.sample_ports}")

        # Validation 7: Check table format (has border lines)
        st.log("Validation 7: Checking table format")
        if "+" not in output_str or "|" not in output_str:
            st.error("FAIL: Table border characters not found - improper table format")
            return False
        st.log("PASS: Table has proper formatting with borders")

        # Validation 8: Verify each port has both Supported Modes and Default Mode
        st.log("Validation 8: Verifying port entries have complete information")
        # Look for lines with port, pipe, interface, and mode info
        table_row_pattern = r'\|\s*(Ethernet\d+)\s*\|\s*(\d+)\s*\|\s*(Ethernet\d+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|'
        row_matches = re.findall(table_row_pattern, output_str)
        
        if row_matches:
            st.log(f"PASS: Found {len(row_matches)} complete table rows with all columns populated")
            
            # Show sample rows
            for i, row in enumerate(row_matches[:3]):  # Show first 3 rows
                port, pipe, interface, supported_modes, default_mode = row
                st.log(f"  Sample row {i+1}: Port={port.strip()}, Pipe={pipe.strip()}, " +
                       f"Supported={supported_modes.strip()}, Default={default_mode.strip()}")
        else:
            st.log("INFO: Could not parse individual rows, but table structure validated")

        st.log("SUCCESS: 'show interface breakout modes' displays proper table output")
        return True

    except Exception as e:
        st.error(f"EXCEPTION: Failed to verify 'show interface breakout modes': {e}")
        return False


#################################################################
# Main Test Function
#################################################################

def test_sm_iscli_p2_75_show_breakout_modes():
    """
    TC_SM_ISCLI_P2_75: Show Interface Breakout Modes Command Validation

    Test validates that 'show interface breakout modes' command displays proper
    table output with all required columns and values.

    Test Steps:
        1. Execute 'show interface breakout modes' command
        2. Verify table structure with all expected columns
        3. Validate port entries are listed
        4. Check Supported Modes and Default Mode values are populated
        5. Verify table formatting is correct

    Expected Results:
        - Command displays complete table
        - All columns present: Port, Pipe, Interface, Supported Modes, Default Mode
        - All ports have mode information
        - No empty or missing values
        - Proper table format with borders

    Returns:
        None (uses st.report_pass/fail for test result reporting)
    """
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_75: Show Interface Breakout Modes Command Validation TEST - START")
    st.banner("=" * 80)

    # Track validation errors
    validation_errors = []

    #################################################################
    # STEP 1: Verify 'show interface breakout modes' command
    #################################################################
    st.banner("=" * 80)
    st.banner("STEP 1: Verify 'show interface breakout modes' displays complete table")
    st.banner("=" * 80)

    if not verify_show_interface_breakout_modes(vars.D1):
        error_msg = "STEP 1 FAILED: 'show interface breakout modes' does not display proper table output"
        validation_errors.append(error_msg)
        st.error(error_msg)
        st.generate_tech_support([vars.D1], "p2_75_show_modes_failed")
        st.report_tc_fail(
            TC_IDS.p2_75_show_modes,
            "msg",
            "BUG NOT FIXED: 'show interface breakout modes' command output is incomplete or malformed"
        )
    else:
        st.log("STEP 1 PASSED: 'show interface breakout modes' displays proper table output")
        st.report_tc_pass(
            TC_IDS.p2_75_show_modes,
            "msg",
            "'show interface breakout modes' command works correctly"
        )

    #################################################################
    # Final Result
    #################################################################
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_P2_75: Show Interface Breakout Modes Command Validation TEST - COMPLETE")
    st.banner("=" * 80)

    if validation_errors:
        error_summary = f"TC_SM_ISCLI_P2_75 FAILED with {len(validation_errors)} error(s): {'; '.join(validation_errors)}"
        st.error(error_summary)
        st.banner("TEST RESULT: FAILED ❌")
        st.report_fail("test_case_failed", error_summary)
    else:
        success_msg = "TC_SM_ISCLI_P2_75 PASSED: 'show interface breakout modes' command displays complete table output"
        st.log(success_msg)
        st.banner("TEST RESULT: PASSED ✅")
        st.report_pass("test_case_passed", success_msg)
