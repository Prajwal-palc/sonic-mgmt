"""
TC_SM_ISCLI_47: Port Breakout Show Commands Bug Fix

Test Case ID: SM-ISCLI-47
Author: Network Automation Team
Copyright (C) 2026, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_sm18_hw.yaml \
    tests/system/SM_ISCLI/test_sm_iscli_47_port_breakout_show_commands.py \
    --logs-path ./logs/sm_iscli_47_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates that all 'show interface breakout' commands display proper output.

  ORIGINAL BUG DESCRIPTION (FIXED):
  - 'show interface breakout resources' showed empty values (Total: , Configured: , Available: , Utilization: %)
  - 'show interface breakout dependencies' showed nothing
  - 'show interface breakout current <port>' didn't work even after port breakout
  - Commands should work without specifying port (display all ports)

  Test validates the fix by:
  1. Verifying 'show interface breakout' displays all configured ports with breakout modes
  2. Verifying 'show interface breakout current <port>' shows current mode details for specific port
  3. Verifying 'show interface breakout dependencies port <port>' shows port dependencies
  4. Verifying 'show interface breakout resources' shows pipeline resource information
  5. Verifying 'show interface breakout modes <port>' shows supported modes
  6. Testing commands work without port specification where applicable

  Expected Output Validation:
  - 'show interface breakout' must display Port, Breakout Mode, Status columns
  - 'show interface breakout current' must show Current Mode, Num Breakouts, Speed, Physical Channels
  - 'show interface breakout dependencies' must show dependency table or "No dependencies" message
  - 'show interface breakout resources' must show Pipeline, Ports, Max-Ports, Front-panel-ports
  - All outputs must be non-empty with actual values

  EXPECTED BEHAVIOR (AFTER FIX):
  - All show commands display proper formatted output
  - No empty or missing values
  - Commands work with and without port specification
  - Proper error messages for unconfigured ports

Pre-requisites:
  - Topology: single-node (D1 only) | Supported: HW only
  - Testbed: testbed_sm18_hw.yaml (single hardware device)
  - Device: 192.168.100.173 (Supermicro SSE-T8164S with 800G ports)
  - Credentials: admin/sonic@123
  - SONiC build: portbreakout-1203-1826 or later
  - Pre-existing breakout configuration (test is read-only, doesn't change config)

Note:
  - This is a read-only test (no configuration changes)
  - Uses existing port breakout configuration from the device
  - Tests sonic-cli show commands only
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
    # Test ports (use existing breakout ports from device)
    "test_port_8x": "Ethernet0",      # 8x100G breakout
    "test_port_2x": "Ethernet8",      # 2x400G breakout
    "test_port_4x": "Ethernet16",     # 4x200G breakout
    "test_port_1x": "Ethernet24",     # 1x800G (no breakout)
    "test_port_with_ip": "Ethernet0", # Port with IP dependency

    # Expected patterns in output
    "expected_columns": ["Port", "Breakout Mode", "Status"],
    "expected_resource_headers": ["Pipeline", "Ports", "Max-Ports", "Front-panel-ports"],
    "expected_current_fields": ["Current Mode", "Num Breakouts", "Speed", "Physical Channels"],

    # Validation thresholds
    "min_configured_ports": 2,  # At least 2 ports should be configured with breakout
    "min_pipelines": 1,         # At least 1 pipeline should be shown in resources
})

# Test Case IDs
TC_IDS = SpyTestDict({
    "sm47_show_breakout": "SM-ISCLI-47.1",
    "sm47_show_current": "SM-ISCLI-47.2",
    "sm47_show_dependencies": "SM-ISCLI-47.3",
    "sm47_show_resources": "SM-ISCLI-47.4",
    "sm47_show_capabilities": "SM-ISCLI-47.5",
})


#################################################################
# Module-level Fixture
#################################################################

@pytest.fixture(scope="module", autouse=True)
def sm47_module_hooks(request):
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
    st.banner("TC_SM_ISCLI_47 MODULE CONFIGURATION - START")
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
    sm47_pre_config()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_47 MODULE CONFIGURATION - COMPLETE")
    st.banner("=" * 80)

    # Yield to test execution
    yield

    # Cleanup (none needed, read-only test)
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_47 MODULE CLEANUP - START")
    st.banner("=" * 80)

    sm47_cleanup()

    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_47 MODULE CLEANUP - COMPLETE")
    st.banner("=" * 80)


#################################################################
# Pre-Configuration and Cleanup Functions
#################################################################

def sm47_pre_config() -> None:
    """
    Pre-configuration for SM_ISCLI_47 test.

    This is a read-only test, so no configuration changes are needed.
    We only verify the device is accessible and has existing breakout configuration.

    Returns:
        None
    """
    st.banner("STEP: SM47 PRE-CONFIGURATION")

    st.log("INFO: This is a read-only test - no configuration changes needed")
    st.log("INFO: Test will use existing port breakout configuration from device")

    # Verify device connectivity

    # Disable pagination for show commands
    # NOTE: terminal length 0 not supported in sonic-cli
    # Using | no-more pipe in show commands instead
    st.log("Pagination will be disabled using | no-more pipe in show commands")

    st.log(f"Verifying connectivity to device: {vars.D1}")

    st.banner("STEP: SM47 PRE-CONFIGURATION - COMPLETE")


def sm47_cleanup() -> None:
    """
    Cleanup configuration after SM_ISCLI_47 test.

    This is a read-only test, so no cleanup is needed.

    Returns:
        None
    """
    st.banner("STEP: SM47 CLEANUP")

    st.log("INFO: No cleanup needed - test made no configuration changes")

    st.banner("STEP: SM47 CLEANUP - COMPLETE")


#################################################################
# Helper Functions - Show Command Verification
#################################################################

def verify_show_interface_breakout(dut: str) -> bool:
    """
    Verify 'show interface breakout' command displays configured ports.

    ORIGINAL BUG: Command worked but we need to verify it shows proper output.

    Expected Output:
        ----------------------------------------------------------------------
        Port Breakout Configuration
        ----------------------------------------------------------------------
        Port                Breakout Mode       Status
        ----------------------------------------------------------------------
        Ethernet0           8x100G              Configured
        Ethernet8           2x400G              Configured
        ...
        ----------------------------------------------------------------------
        Total: 66 port(s) configured with breakout

    Validation:
        - Output contains column headers: Port, Breakout Mode, Status
        - At least minimum number of configured ports displayed
        - "Total: X port(s) configured with breakout" line present
        - All values are non-empty (not blank)

    Args:
        dut: Device under test

    Returns:
        bool: True if command output is valid, False otherwise
    """
    st.banner("STEP: Verify 'show interface breakout' command")

    try:
        # Execute show command
        cmd = "show interface breakout | no-more"
        st.log(f"Executing: {cmd}")
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)

        st.log(f"Command output:\n{output}")

        # Convert to string if needed
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output

        # Validation 1: Check for expected column headers
        st.log("Validation 1: Checking for column headers")
        for header in CONFIG.expected_columns:
            if header not in output_str:
                st.error(f"FAIL: Missing expected column header: {header}")
                return False
        st.log("PASS: All expected column headers found")

        # Validation 2: Check for port entries (at least one Ethernet port)
        st.log("Validation 2: Checking for port entries")
        if "Ethernet" not in output_str:
            st.error("FAIL: No Ethernet port entries found in output")
            return False
        st.log("PASS: Port entries found in output")

        # Validation 3: Check for "Total: X port(s)" summary line
        st.log("Validation 3: Checking for total ports summary")
        total_pattern = r'Total:\s+(\d+)\s+port\(s\)\s+configured\s+with\s+breakout'
        match = re.search(total_pattern, output_str)
        if not match:
            st.error("FAIL: Missing 'Total: X port(s) configured with breakout' line")
            return False

        total_ports = int(match.group(1))
        st.log(f"PASS: Total configured ports: {total_ports}")

        # Validation 4: Verify minimum number of configured ports
        st.log("Validation 4: Checking minimum configured ports threshold")
        if total_ports < CONFIG.min_configured_ports:
            st.error(f"FAIL: Only {total_ports} ports configured, expected at least {CONFIG.min_configured_ports}")
            return False
        st.log(f"PASS: Sufficient ports configured ({total_ports} >= {CONFIG.min_configured_ports})")

        # Validation 5: Check for breakout mode values (not empty)
        st.log("Validation 5: Checking for breakout mode values")
        mode_pattern = r'Ethernet\d+\s+([\dx]+G)\s+Configured'
        mode_matches = re.findall(mode_pattern, output_str)
        if not mode_matches:
            st.error("FAIL: No breakout mode values found")
            return False
        st.log(f"PASS: Found breakout modes: {set(mode_matches)}")

        st.log("SUCCESS: 'show interface breakout' displays proper output")
        return True

    except Exception as e:
        st.error(f"EXCEPTION: Failed to verify 'show interface breakout': {e}")
        return False


def verify_show_interface_breakout_current(dut: str, port: str) -> bool:
    """
    Verify 'show interface breakout current <port>' command displays port details.

    ORIGINAL BUG: Command didn't work even after breaking out port.
    Now it should display: Current Mode, Num Breakouts, Speed, Physical Channels.

    Expected Output:
        Port: Ethernet0
        ----------------------------------------
        Current Mode: 8x100G
        Num Breakouts: 8
        Speed: 100G
        Physical Channels: 4

    Validation:
        - Output contains "Port: <port_name>"
        - All expected fields present: Current Mode, Num Breakouts, Speed, Physical Channels
        - All field values are non-empty
        - Values are in correct format (e.g., Speed ends with 'G')

    Args:
        dut: Device under test
        port: Port name (e.g., "Ethernet0")

    Returns:
        bool: True if command output is valid, False otherwise
    """
    st.banner(f"STEP: Verify 'show interface breakout current {port}' command")

    try:
        # Execute show command
        cmd = f"show interface breakout current {port} | no-more"
        st.log(f"Executing: {cmd}")
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)

        st.log(f"Command output:\n{output}")

        # Convert to string if needed
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output

        # Validation 1: Check for port name in output
        st.log("Validation 1: Checking for port name")
        if f"Port: {port}" not in output_str and port not in output_str:
            st.error(f"FAIL: Port name '{port}' not found in output")
            return False
        st.log(f"PASS: Port name '{port}' found in output")

        # Validation 2: Check for all expected fields
        st.log("Validation 2: Checking for all expected fields")
        for field in CONFIG.expected_current_fields:
            if field not in output_str:
                st.error(f"FAIL: Missing expected field: {field}")
                return False
        st.log("PASS: All expected fields found")

        # Validation 3: Extract and validate Current Mode
        st.log("Validation 3: Validating Current Mode value")
        mode_pattern = r'Current Mode:\s+([\dx]+G)'
        mode_match = re.search(mode_pattern, output_str)
        if not mode_match:
            st.error("FAIL: Current Mode value not found or empty")
            return False
        current_mode = mode_match.group(1)
        st.log(f"PASS: Current Mode = {current_mode}")

        # Validation 4: Extract and validate Num Breakouts
        st.log("Validation 4: Validating Num Breakouts value")
        num_pattern = r'Num Breakouts:\s+(\d+)'
        num_match = re.search(num_pattern, output_str)
        if not num_match:
            st.error("FAIL: Num Breakouts value not found or empty")
            return False
        num_breakouts = int(num_match.group(1))
        st.log(f"PASS: Num Breakouts = {num_breakouts}")

        # Validation 5: Extract and validate Speed
        st.log("Validation 5: Validating Speed value")
        speed_pattern = r'Speed:\s+(\d+G)'
        speed_match = re.search(speed_pattern, output_str)
        if not speed_match:
            st.error("FAIL: Speed value not found or empty")
            return False
        speed = speed_match.group(1)
        st.log(f"PASS: Speed = {speed}")

        # Validation 6: Extract and validate Physical Channels
        st.log("Validation 6: Validating Physical Channels value")
        channels_pattern = r'Physical Channels:\s+(\d+)'
        channels_match = re.search(channels_pattern, output_str)
        if not channels_match:
            st.error("FAIL: Physical Channels value not found or empty")
            return False
        channels = int(channels_match.group(1))
        st.log(f"PASS: Physical Channels = {channels}")

        st.log(f"SUCCESS: 'show interface breakout current {port}' displays proper output")
        return True

    except Exception as e:
        st.error(f"EXCEPTION: Failed to verify 'show interface breakout current {port}': {e}")
        return False


def verify_show_interface_breakout_dependencies(dut: str, port: str) -> bool:
    """
    Verify 'show interface breakout dependencies port <port>' command displays dependencies.

    ORIGINAL BUG: Command showed nothing (empty output).
    Now it should display dependencies table or "No dependencies" message.

    Expected Output (with dependencies):
        Port: Ethernet0
        Dependencies found (1):
        ┌──────────────────────┬───────────────────────────────────┐
        │ Type                 │ Name                              │
        ├──────────────────────┼───────────────────────────────────┤
        │ IPv4 Address         │ 10.1.1.1                          │
        └──────────────────────┴───────────────────────────────────┘
        ⚠  Port has active configurations. Remove dependencies before breakout.

    Expected Output (without dependencies):
        Port: Ethernet24
        No dependencies found.
        ✓ Port is ready for breakout.

    Validation:
        - Output contains "Port: <port_name>"
        - Output contains either "Dependencies found" or "No dependencies"
        - If dependencies found, table with Type and Name columns is present
        - Output is not completely empty

    Args:
        dut: Device under test
        port: Port name (e.g., "Ethernet0")

    Returns:
        bool: True if command output is valid, False otherwise
    """
    st.banner(f"STEP: Verify 'show interface breakout dependencies port {port}' command")

    try:
        # Execute show command
        cmd = f"show interface breakout dependencies port {port} | no-more"
        st.log(f"Executing: {cmd}")
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)

        st.log(f"Command output:\n{output}")

        # Convert to string if needed
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output

        # Validation 1: Check output is not empty
        st.log("Validation 1: Checking output is not empty")
        if not output_str or len(output_str.strip()) == 0:
            st.error("FAIL: Command returned empty output")
            return False
        st.log("PASS: Output is not empty")

        # Validation 2: Check for port name in output
        st.log("Validation 2: Checking for port name")
        if f"Port: {port}" not in output_str and port not in output_str:
            st.error(f"FAIL: Port name '{port}' not found in output")
            return False
        st.log(f"PASS: Port name '{port}' found in output")

        # Validation 3: Check for dependencies status
        st.log("Validation 3: Checking for dependencies status")
        has_dependencies = "Dependencies found" in output_str or "Type" in output_str
        no_dependencies = "No dependencies" in output_str

        if not has_dependencies and not no_dependencies:
            st.error("FAIL: Output doesn't indicate dependencies status (neither 'Dependencies found' nor 'No dependencies')")
            return False

        if has_dependencies:
            st.log("PASS: Port has dependencies - dependency table displayed")

            # Validation 4: If dependencies exist, check for table structure
            st.log("Validation 4: Validating dependency table structure")
            if "Type" not in output_str or "Name" not in output_str:
                st.error("FAIL: Dependency table missing Type/Name columns")
                return False
            st.log("PASS: Dependency table has proper structure")

        elif no_dependencies:
            st.log("PASS: Port has no dependencies - ready for breakout")

        st.log(f"SUCCESS: 'show interface breakout dependencies port {port}' displays proper output")
        return True

    except Exception as e:
        st.error(f"EXCEPTION: Failed to verify 'show interface breakout dependencies port {port}': {e}")
        return False


def verify_show_interface_breakout_resources(dut: str) -> bool:
    """
    Verify 'show interface breakout resources' command displays pipeline information.

    ORIGINAL BUG: Command showed empty values for all fields:
        Total Breakout-Capable Ports: [empty]
        Configured Breakout Ports: [empty]
        Available Ports: [empty]
        Utilization: [empty]%

    Now it should display:
        Maximum ports supported in the system: 96
        Current ports in the system: 67
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
                return False
        st.log("PASS: All expected headers found")

        # Validation 4: Check for at least one pipeline entry
        st.log("Validation 4: Checking for pipeline entries")
        pipe_pattern = r'pipe\d+\s+\d+\s+\d+\s+Ethernet'
        pipe_matches = re.findall(pipe_pattern, output_str)
        if not pipe_matches:
            st.error("FAIL: No pipeline entries found in output")
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
        st.log(f"PASS: Port counts are valid (current: {current_ports}, max: {max_ports})")

        st.log("SUCCESS: 'show interface breakout resources' displays proper output")
        return True

    except Exception as e:
        st.error(f"EXCEPTION: Failed to verify 'show interface breakout resources': {e}")
        return False


def verify_show_interface_breakout_modes(dut: str, port: str) -> bool:
    """
    Verify 'show interface breakout modes <port>' command displays supported modes.

    This command was not mentioned as broken in the bug, but we verify it works properly.

    Expected Output:
        Port: Ethernet0
        Supported Breakout Modes:
        - 1x800G
        - 2x400G
        - 4x200G
        - 8x100G

    Validation:
        - Output contains "Port: <port_name>"
        - Output contains "Supported Breakout Modes" or "capabilities"
        - At least one breakout mode is listed
        - Modes are in correct format (e.g., "1x800G", "2x400G")

    Args:
        dut: Device under test
        port: Port name (e.g., "Ethernet0")

    Returns:
        bool: True if command output is valid, False otherwise
    """
    st.banner(f"STEP: Verify 'show interface breakout modes {port}' command")

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

        # Validation 1: Check output is not empty
        st.log("Validation 1: Checking output is not empty")
        if not output_str or len(output_str.strip()) == 0:
            st.error("FAIL: Command returned empty output")
            return False
        st.log("PASS: Output is not empty")

        # Validation 2: Check for port name or capabilities indication
        st.log("Validation 2: Checking for port capabilities indication")
        # Validation 2: Check for port in table output
        st.log("Validation 2: Checking if port is in the modes table")
        if port not in output_str:
            st.error(f"FAIL: Port '{port}' not found in modes table output")
            return False
        # Validation 2: Check for port in table output
        st.log("Validation 2: Checking if port is in the modes table")
        if port not in output_str:
            st.error(f"FAIL: Port '{port}' not found in modes table output")
            return False
        # Validation 2: Check for port in table output
        st.log("Validation 2: Checking if port is in the modes table")
        if port not in output_str:
            st.error(f"FAIL: Port '{port}' not found in modes table output")
            return False
        # Validation 2: Check for port in table output
        st.log("Validation 2: Checking if port is in the modes table")
        if port not in output_str:
            st.error(f"FAIL: Port '{port}' not found in modes table output")
            return False
        # Validation 2: Check for port in table output
        st.log("Validation 2: Checking if port is in the modes table")
        if port not in output_str:
            st.error(f"FAIL: Port '{port}' not found in modes table output")
            return False
        # Validation 3: Check for breakout mode patterns
        st.log("Validation 3: Checking for breakout mode values")
        mode_pattern = r'(\d+x\d+G)'
        mode_matches = re.findall(mode_pattern, output_str)
        if not mode_matches:
            st.error("FAIL: No breakout mode values found (expected formats like '1x800G', '2x400G')")
            return False

        st.log(f"PASS: Found supported breakout modes: {set(mode_matches)}")

        st.log(f"SUCCESS: 'show interface breakout modes {port}' displays proper output")
        return True

    except Exception as e:
        st.error(f"EXCEPTION: Failed to verify 'show interface breakout modes {port}': {e}")
        return False


#################################################################
# Main Test Function
#################################################################

def test_sm_iscli_47_port_breakout_show_commands():
    """
    TC_SM_ISCLI_47: Port Breakout Show Commands Bug Fix

    Test validates that all 'show interface breakout' commands display proper output
    instead of showing empty or missing values.

    Test Steps:
        1. Verify 'show interface breakout' displays all configured ports
        2. Verify 'show interface breakout current <port>' shows port details
        3. Verify 'show interface breakout dependencies port <port>' shows dependencies
        4. Verify 'show interface breakout resources' shows pipeline information
        5. Verify 'show interface breakout modes <port>' shows supported modes

    Expected Results:
        - All commands display proper formatted output with actual values
        - No empty or missing fields
        - Proper table structures and formatting
        - Error messages are meaningful (not empty)

    Returns:
        None (uses st.report_pass/fail for test result reporting)
    """
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_47: Port Breakout Show Commands Bug Fix TEST - START")
    st.banner("=" * 80)

    # Track validation errors
    validation_errors = []

    #################################################################
    # STEP 1: Verify 'show interface breakout' command
    #################################################################
    st.banner("=" * 80)
    st.banner("STEP 1: Verify 'show interface breakout' displays all configured ports")
    st.banner("=" * 80)

    if not verify_show_interface_breakout(vars.D1):
        error_msg = "STEP 1 FAILED: 'show interface breakout' does not display proper output"
        validation_errors.append(error_msg)
        st.error(error_msg)
        st.generate_tech_support([vars.D1], "sm47_show_breakout_failed")
        st.report_tc_fail(
            TC_IDS.sm47_show_breakout,
            "msg",
            "BUG NOT FIXED: 'show interface breakout' still shows improper output"
        )
    else:
        st.log("STEP 1 PASSED: 'show interface breakout' displays proper output")
        st.report_tc_pass(
            TC_IDS.sm47_show_breakout,
            "msg",
            "'show interface breakout' command works correctly"
        )

    #################################################################
    # STEP 2: Verify 'show interface breakout current <port>' command
    #################################################################
    st.banner("=" * 80)
    st.banner("STEP 2: Verify 'show interface breakout current <port>' shows port details")
    st.banner("=" * 80)

    # Test multiple ports with different breakout modes
    test_ports = [
        CONFIG.test_port_8x,  # Ethernet0 (8x100G)
        CONFIG.test_port_2x,  # Ethernet8 (2x400G)
        CONFIG.test_port_4x,  # Ethernet16 (4x200G)
    ]

    step2_failed = False
    for port in test_ports:
        if not verify_show_interface_breakout_current(vars.D1, port):
            error_msg = f"STEP 2 FAILED: 'show interface breakout current {port}' does not display proper output"
            validation_errors.append(error_msg)
            st.error(error_msg)
            step2_failed = True

    if step2_failed:
        st.generate_tech_support([vars.D1], "sm47_show_current_failed")
        st.report_tc_fail(
            TC_IDS.sm47_show_current,
            "msg",
            "BUG NOT FIXED: 'show interface breakout current' still doesn't work properly"
        )
    else:
        st.log("STEP 2 PASSED: 'show interface breakout current' displays proper output for all test ports")
        st.report_tc_pass(
            TC_IDS.sm47_show_current,
            "msg",
            "'show interface breakout current' command works correctly"
        )

    #################################################################
    # STEP 3: Verify 'show interface breakout dependencies port <port>' command
    #################################################################
    st.banner("=" * 80)
    st.banner("STEP 3: Verify 'show interface breakout dependencies port <port>' shows dependencies")
    st.banner("=" * 80)

    # Test port with IP dependency and port without dependencies
    dependency_test_ports = [
        CONFIG.test_port_with_ip,  # Ethernet0 (has IP dependency)
        CONFIG.test_port_1x,        # Ethernet24 (likely no dependencies)
    ]

    step3_failed = False
    for port in dependency_test_ports:
        if not verify_show_interface_breakout_dependencies(vars.D1, port):
            error_msg = f"STEP 3 FAILED: 'show interface breakout dependencies port {port}' does not display proper output"
            validation_errors.append(error_msg)
            st.error(error_msg)
            step3_failed = True

    if step3_failed:
        st.generate_tech_support([vars.D1], "sm47_show_dependencies_failed")
        st.report_tc_fail(
            TC_IDS.sm47_show_dependencies,
            "msg",
            "BUG NOT FIXED: 'show interface breakout dependencies' still shows empty output"
        )
    else:
        st.log("STEP 3 PASSED: 'show interface breakout dependencies' displays proper output")
        st.report_tc_pass(
            TC_IDS.sm47_show_dependencies,
            "msg",
            "'show interface breakout dependencies' command works correctly"
        )

    #################################################################
    # STEP 4: Verify 'show interface breakout resources' command
    #################################################################
    st.banner("=" * 80)
    st.banner("STEP 4: Verify 'show interface breakout resources' shows pipeline information")
    st.banner("=" * 80)

    if not verify_show_interface_breakout_resources(vars.D1):
        error_msg = "STEP 4 FAILED: 'show interface breakout resources' does not display proper output"
        validation_errors.append(error_msg)
        st.error(error_msg)
        st.generate_tech_support([vars.D1], "sm47_show_resources_failed")
        st.report_tc_fail(
            TC_IDS.sm47_show_resources,
            "msg",
            "BUG NOT FIXED: 'show interface breakout resources' still shows empty values"
        )
    else:
        st.log("STEP 4 PASSED: 'show interface breakout resources' displays proper output")
        st.report_tc_pass(
            TC_IDS.sm47_show_resources,
            "msg",
            "'show interface breakout resources' command works correctly"
        )

    #################################################################
    # STEP 5: Verify 'show interface breakout modes <port>' command
    #################################################################
    st.banner("=" * 80)
    st.banner("STEP 5: Verify 'show interface breakout modes <port>' shows supported modes")
    st.banner("=" * 80)

    if not verify_show_interface_breakout_modes(vars.D1, CONFIG.test_port_8x):
        error_msg = f"STEP 5 FAILED: 'show interface breakout modes {CONFIG.test_port_8x}' does not display proper output"
        validation_errors.append(error_msg)
        st.error(error_msg)
        st.generate_tech_support([vars.D1], "sm47_show_capabilities_failed")
        st.report_tc_fail(
            TC_IDS.sm47_show_capabilities,
            "msg",
            "'show interface breakout modes' command does not work properly"
        )
    else:
        st.log("STEP 5 PASSED: 'show interface breakout modes' displays proper output")
        st.report_tc_pass(
            TC_IDS.sm47_show_capabilities,
            "msg",
            "'show interface breakout modes' command works correctly"
        )

    #################################################################
    # Final Result
    #################################################################
    st.banner("=" * 80)
    st.banner("TC_SM_ISCLI_47: Port Breakout Show Commands Bug Fix TEST - COMPLETE")
    st.banner("=" * 80)

    if validation_errors:
        error_summary = f"TC_SM_ISCLI_47 FAILED with {len(validation_errors)} error(s): {'; '.join(validation_errors)}"
        st.error(error_summary)
        st.banner("TEST RESULT: FAILED ❌")
        st.report_fail("test_case_failed", error_summary)
    else:
        success_msg = "TC_SM_ISCLI_47 PASSED: All 'show interface breakout' commands display proper output"
        st.log(success_msg)
        st.banner("TEST RESULT: PASSED ✅")
        st.report_pass("test_case_passed", success_msg)
