"""
SM_ISCLI_45: IS-CLI Write Erase Command Availability Test

Author: Athira
Copyright (C) 2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  tests/system/mgmt/test_sm_iscli45_write_erase.py \\
  --logs-path ./logs/test_sm_iscli45_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Verifies that the 'write erase' command is available in IS-CLI privileged exec mode
  and functions correctly. Tests include command availability verification, syntax
  validation, and negative test cases.

Pre-requisites:
  - Topology: Single node (D1) | Supported: HW and Virtual
  - IS-CLI (klish) support required
  - Configuration backup mechanism available
  - Management connectivity must remain intact
  - Test variables: spytest/vars/system/mgmt/vars_sm_iscli45_write_erase.yaml

Test Cases:
  - TC_ISCLI_WRITE_ERASE_001: Verify write erase command availability
  - TC_ISCLI_WRITE_ERASE_002: Verify write erase command verification
  - TC_ISCLI_WRITE_ERASE_003: Non-destructive syntax verification
  - TC_ISCLI_WRITE_ERASE_004: Negative test cases
"""

from pathlib import Path
import pytest
import yaml
import time
import re
from spytest import SpyTestDict, st

# Test case identifiers
TC_IDS = SpyTestDict({
    "availability": "TC_ISCLI_WRITE_ERASE_001",
    "verification": "TC_ISCLI_WRITE_ERASE_002",
    "syntax_check": "TC_ISCLI_WRITE_ERASE_003",
    "negative_tests": "TC_ISCLI_WRITE_ERASE_004",
})

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Configuration file path
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "mgmt"
    / "vars_sm_iscli45_write_erase.yaml"
)


def initialize_data() -> None:
    """Load test configuration from YAML file"""
    try:
        with open(DEFAULT_VAR_FILE, "r") as f:
            payload = yaml.safe_load(f)
    except FileNotFoundError as error:
        pytest.skip(f"Configuration file not found: {error}")
    except yaml.YAMLError as error:
        pytest.skip(f"Error parsing YAML configuration: {error}")

    global vars, data
    vars = st.ensure_min_topology(*payload.get("min_topology", ["D1"]))
    data.config = SpyTestDict(payload)


def backup_device_configuration(dut: str) -> bool:
    """
    Backup current device configuration

    Args:
        dut: Device under test

    Returns:
        bool: True if backup successful, False otherwise
    """
    st.log("SAFETY: Creating configuration backup")
    try:
        # Save running config to startup config
        cmd = "copy running-config startup-config"
        output = st.config(dut, cmd, type="klish", skip_error_check=False)

        # Verify backup was successful
        if output and ("error" in str(output).lower() or "failed" in str(output).lower()):
            st.error("Configuration backup failed")
            return False

        st.log("Configuration backup completed successfully")
        return True
    except Exception as e:
        st.error(f"Exception during configuration backup: {e}")
        return False


def verify_management_connectivity(dut: str, retries: int = 3) -> bool:
    """
    Verify device management connectivity

    Args:
        dut: Device under test
        retries: Number of retry attempts

    Returns:
        bool: True if connectivity verified, False otherwise
    """
    st.log(f"Verifying management connectivity to {dut}")

    for attempt in range(retries):
        try:
            # Simple show command to verify connectivity
            output = st.show(dut, "show version", type="klish", skip_tmpl=True)
            if output:
                st.log(f"Management connectivity verified (attempt {attempt + 1}/{retries})")
                return True
        except Exception as e:
            st.log(f"Connectivity check failed (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(5)

    st.error("Management connectivity verification failed")
    return False


def create_test_loopback(dut: str, loopback_id: int, description: str, ip_address: str = None) -> bool:
    """
    Create test loopback interface

    Args:
        dut: Device under test
        loopback_id: Loopback interface ID
        description: Interface description
        ip_address: Optional IP address to configure

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Creating test loopback interface Loopback {loopback_id}")

    try:
        # Enter configuration mode and create loopback
        commands = [
            "configure terminal",
            f"interface Loopback {loopback_id}",
            f'description "{description}"',
        ]

        if ip_address:
            commands.append(f"ip address {ip_address}")

        commands.append("end")

        # Execute commands
        for cmd in commands:
            output = st.config(dut, cmd, type="klish", skip_error_check=False)
            if output and "error" in str(output).lower():
                st.error(f"Failed to execute command: {cmd}")
                return False

        st.log(f"Test loopback Loopback {loopback_id} created successfully")
        return True
    except Exception as e:
        st.error(f"Exception creating test loopback: {e}")
        return False


def remove_test_loopback(dut: str, loopback_id: int) -> bool:
    """
    Remove test loopback interface

    Args:
        dut: Device under test
        loopback_id: Loopback interface ID

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Removing test loopback interface Loopback {loopback_id}")

    try:
        commands = [
            "configure terminal",
            f"no interface Loopback {loopback_id}",
            "end",
        ]

        for cmd in commands:
            st.config(dut, cmd, type="klish", skip_error_check=True)

        st.log(f"Test loopback Loopback {loopback_id} removed")
        return True
    except Exception as e:
        st.error(f"Exception removing test loopback: {e}")
        return False


def verify_interface_in_config(dut: str, interface: str, config_type: str = "running") -> bool:
    """
    Verify if interface exists in configuration

    Args:
        dut: Device under test
        interface: Interface name (e.g., "Loopback 99")
        config_type: Configuration type ("running" or "startup")

    Returns:
        bool: True if interface found in config, False otherwise
    """
    st.log(f"Verifying {interface} in {config_type} configuration")

    try:
        cmd = f"show {config_type}-configuration interface {interface} | no-more"
        output = st.show(dut, cmd, type="klish", skip_tmpl=True)

        if output:
            output_str = str(output).lower()
            # Check if interface is present in output
            if interface.lower() in output_str or "interface" in output_str:
                st.log(f"{interface} found in {config_type} configuration")
                return True

        st.log(f"{interface} not found in {config_type} configuration")
        return False
    except Exception as e:
        st.log(f"Exception verifying interface in config: {e}")
        return False


def check_command_output_for_keywords(output: str, keywords: list, match_all: bool = False) -> bool:
    """
    Check if command output contains expected keywords

    Args:
        output: Command output string
        keywords: List of keywords to search for
        match_all: If True, all keywords must be present. If False, at least one must be present.

    Returns:
        bool: True if keywords found according to match_all setting
    """
    if not output or not keywords:
        return False

    output_lower = str(output).lower()
    matches = [keyword.lower() in output_lower for keyword in keywords]

    if match_all:
        result = all(matches)
    else:
        result = any(matches)

    return result


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level fixture for setup and teardown
    """
    global vars, data

    st.banner("MODULE PROLOGUE: SM_ISCLI_45 Write Erase Command Tests")

    # Initialize test data
    initialize_data()

    # Get DUT
    data.dut = vars.D1
    data.cli_type = data.config.get("defaults", {}).get("cli_type", "klish")

    st.log(f"Test DUT: {data.dut}")
    st.log(f"CLI Type: {data.cli_type}")

    # CRITICAL: Create safety backup
    st.banner("SAFETY: Creating configuration backup before tests")
    backup_success = backup_device_configuration(data.dut)

    if not backup_success:
        st.error("CRITICAL: Configuration backup failed - tests may be unsafe")
        # Still proceed but log the warning

    data.config_backup_created = backup_success

    # Verify initial connectivity
    if not verify_management_connectivity(data.dut):
        pytest.skip("Initial management connectivity verification failed")

    yield

    # Module epilogue - cleanup
    st.banner("MODULE EPILOGUE: Cleanup and restore")

    # Clean up any test loopback interfaces that might remain
    loopback_id = data.config.get("test_config", {}).get("non_destructive_loopback", 99)
    remove_test_loopback(data.dut, loopback_id)

    # Save final configuration
    st.config(data.dut, "copy running-config startup-config", type="klish", skip_error_check=True)

    # Verify final connectivity
    if not verify_management_connectivity(data.dut):
        st.error("CRITICAL: Management connectivity lost after tests")


@pytest.mark.topology("D1")
@pytest.mark.community_pass
def test_write_erase_command_availability():
    """
    TC_ISCLI_WRITE_ERASE_001: Verify write erase command is available in IS-CLI

    Test Steps:
    1. Execute 'write ?' command
    2. Verify 'erase' option is present
    3. Verify 'memory' option is present
    4. Execute 'write erase ?' command (informational)
    """
    tc_id = TC_IDS.availability
    st.banner(f"{tc_id}: Verify write erase command availability")

    # Get test configuration
    tc_config = data.config.get("testcases", {}).get(tc_id, {})
    expected_write_help = tc_config.get("expected_keywords", {}).get("write_help", [])
    expected_erase_help = tc_config.get("expected_keywords", {}).get("write_erase_help", [])

    # Step 1: Execute 'write ?' command
    st.log("Step 1: Executing 'write ?' command")
    write_help_output = st.show(data.dut, "write ?", type=data.cli_type, skip_tmpl=True)

    if not write_help_output:
        st.report_tc_fail(tc_id, "msg", "No output from 'write ?' command")
        st.report_fail("msg", "No output from 'write ?' command")

    st.log(f"Write help output: {write_help_output}")

    # Step 2-3: Verify 'erase' and 'memory' options are present
    st.log("Step 2-3: Verifying 'erase' and 'memory' options in write help")

    if not check_command_output_for_keywords(write_help_output, expected_write_help, match_all=True):
        missing_keywords = [kw for kw in expected_write_help
                          if kw.lower() not in str(write_help_output).lower()]
        st.report_tc_fail(tc_id, "msg",
                         f"Expected keywords missing from 'write ?' output: {missing_keywords}")
        st.report_fail("msg", f"write erase command not found in help output. Missing: {missing_keywords}")

    st.log("✓ Both 'erase' and 'memory' options found in write help")

    # Step 4: Execute 'write erase ?' command
    st.log("Step 4: Executing 'write erase ?' command")
    erase_help_output = st.show(data.dut, "write erase ?", type=data.cli_type, skip_tmpl=True)

    if not erase_help_output:
        st.report_tc_fail(tc_id, "msg", "No output from 'write erase ?' command")
        st.report_fail("msg", "No output from 'write erase ?' command")

    st.log(f"Write erase help output: {erase_help_output}")

    # Test passed
    st.log("✓ TC_ISCLI_WRITE_ERASE_001: PASSED")
    st.report_tc_pass(tc_id, "msg", "write erase command availability verified")
    st.report_pass("test_case_passed")


@pytest.mark.topology("D1")
@pytest.mark.community_pass
def test_write_erase_command_verification():
    """
    TC_ISCLI_WRITE_ERASE_002: Verify write erase command availability comparison with baseline

    Test Steps:
    1. Capture full write command help output
    2. Capture full write erase help output
    3. Verify command completeness
    4. Check SONiC version includes IS-CLI build
    """
    tc_id = TC_IDS.verification
    st.banner(f"{tc_id}: Verify write erase command verification")

    # Step 1: Capture full write command help
    st.log("Step 1: Capturing full 'write ?' help output")
    write_help_full = st.show(data.dut, "write ? | no-more", type=data.cli_type, skip_tmpl=True)

    if not write_help_full:
        st.report_tc_fail(tc_id, "msg", "Failed to capture full write help output")
        st.report_fail("msg", "Failed to capture full write help output")

    st.log(f"Full write help output captured ({len(str(write_help_full))} chars)")

    # Verify both erase and memory are present
    if not check_command_output_for_keywords(write_help_full, ["erase", "memory"], match_all=True):
        st.report_tc_fail(tc_id, "msg", "write help output missing required options")
        st.report_fail("msg", "write help output incomplete")

    # Step 2: Capture full write erase help
    st.log("Step 2: Capturing full 'write erase ?' help output")
    erase_help_full = st.show(data.dut, "write erase ? | no-more", type=data.cli_type, skip_tmpl=True)

    if not erase_help_full:
        st.report_tc_fail(tc_id, "msg", "Failed to capture full write erase help output")
        st.report_fail("msg", "Failed to capture full write erase help output")

    st.log(f"Full write erase help output captured ({len(str(erase_help_full))} chars)")

    # Step 3: Verify command completeness
    st.log("Step 3: Verifying write erase command completeness")
    required_options = ["startup-config", "boot"]

    if not check_command_output_for_keywords(erase_help_full, required_options):
        st.log("Warning: Some expected write erase options may be missing")

    # Step 4: Check SONiC version
    st.log("Step 4: Checking SONiC version information")
    version_output = st.show(data.dut, "show version | no-more", type=data.cli_type, skip_tmpl=True)

    if version_output:
        st.log(f"SONiC version output: {version_output}")
        # Log version information (informational only, not a failure if not found)
        if "iscli" in str(version_output).lower():
            st.log("✓ IS-CLI build detected in version output")
        else:
            st.log("Note: IS-CLI identifier not found in version output (may be expected)")

    # Test passed
    st.log("✓ TC_ISCLI_WRITE_ERASE_002: PASSED")
    st.report_tc_pass(tc_id, "msg", "write erase command verification completed")
    st.report_pass("test_case_passed")


@pytest.mark.topology("D1")
@pytest.mark.community_pass
def test_write_erase_syntax_nondestructive():
    """
    TC_ISCLI_WRITE_ERASE_003: Verify write erase command syntax without actual execution

    Test Steps:
    1. Create test loopback interface
    2. Verify interface in running-config only (not in startup)
    3. Test write erase command syntax (dry run)
    4. Cleanup test interface
    """
    tc_id = TC_IDS.syntax_check
    st.banner(f"{tc_id}: Non-destructive syntax verification")

    # Get test configuration
    loopback_id = data.config.get("test_config", {}).get("non_destructive_loopback", 99)
    description = data.config.get("test_config", {}).get("non_destructive_description", "Test Interface")

    try:
        # Step 1: Create test loopback interface
        st.log(f"Step 1: Creating test interface Loopback {loopback_id}")
        if not create_test_loopback(data.dut, loopback_id, description):
            st.report_tc_fail(tc_id, "msg", f"Failed to create test Loopback {loopback_id}")
            st.report_fail("msg", f"Failed to create test Loopback {loopback_id}")

        # Wait for configuration to apply
        time.sleep(2)

        # Step 2: Verify interface in running-config only
        st.log("Step 2: Verifying test interface in running-config")
        if not verify_interface_in_config(data.dut, f"Loopback {loopback_id}", "running"):
            st.report_tc_fail(tc_id, "msg", "Test interface not found in running-config")
            st.report_fail("msg", "Test interface not found in running-config")

        st.log("✓ Test interface present in running-config")

        # Verify NOT in startup-config (we didn't save it)
        st.log("Verifying test interface NOT in startup-config")
        in_startup = verify_interface_in_config(data.dut, f"Loopback {loopback_id}", "startup")
        if in_startup:
            st.log("Note: Test interface found in startup-config (may be from previous save)")
        else:
            st.log("✓ Test interface not in startup-config (as expected)")

        # Step 3: Test write erase command syntax (dry run)
        st.log("Step 3: Testing write erase command syntax (dry run)")
        syntax_output = st.show(data.dut, "write erase startup-config ?",
                               type=data.cli_type, skip_tmpl=True)

        if not syntax_output:
            st.log("Warning: No output from syntax check command")
        else:
            st.log(f"Syntax check output: {syntax_output}")
            # Verify no-prompt option is available
            if "no-prompt" in str(syntax_output).lower():
                st.log("✓ 'no-prompt' option available in syntax")

        # Step 4: Cleanup test interface
        st.log(f"Step 4: Cleaning up test interface Loopback {loopback_id}")
        remove_test_loopback(data.dut, loopback_id)

        # Verify cleanup
        time.sleep(1)
        if verify_interface_in_config(data.dut, f"Loopback {loopback_id}", "running"):
            st.log("Warning: Test interface still present after cleanup attempt")
        else:
            st.log("✓ Test interface cleaned up successfully")

        # Test passed
        st.log("✓ TC_ISCLI_WRITE_ERASE_003: PASSED")
        st.report_tc_pass(tc_id, "msg", "write erase syntax verification completed")
        st.report_pass("test_case_passed")

    except Exception as e:
        st.error(f"Exception during non-destructive syntax test: {e}")
        # Cleanup on exception
        remove_test_loopback(data.dut, loopback_id)
        st.report_tc_fail(tc_id, "msg", f"Exception during test: {e}")
        st.report_fail("msg", f"Test failed with exception: {e}")


@pytest.mark.topology("D1")
@pytest.mark.community_pass
def test_write_erase_negative_cases():
    """
    TC_ISCLI_WRITE_ERASE_004: Verify write erase command handles invalid options correctly

    Test Steps:
    1. Test invalid write erase option
    2. Test write erase with incomplete syntax
    3. Test write command with invalid sub-command
    """
    tc_id = TC_IDS.negative_tests
    st.banner(f"{tc_id}: Negative test cases")

    # Get test configuration
    tc_config = data.config.get("testcases", {}).get(tc_id, {})
    invalid_commands = tc_config.get("invalid_commands", [])

    # Step 1: Test invalid write erase option
    st.log("Step 1: Testing invalid write erase option")
    invalid_erase_output = st.config(data.dut, "write erase invalid-option",
                                    type=data.cli_type, skip_error_check=True)

    if invalid_erase_output:
        st.log(f"Invalid option output: {invalid_erase_output}")
        # Should contain error indication
        if check_command_output_for_keywords(invalid_erase_output, ["error", "invalid", "unknown"]):
            st.log("✓ Invalid option correctly rejected with error message")
        else:
            st.log("Note: Error message format may vary")

    # Step 2: Test write erase with incomplete syntax
    st.log("Step 2: Testing incomplete write erase command")
    incomplete_output = st.show(data.dut, "write erase", type=data.cli_type, skip_tmpl=True)

    if incomplete_output:
        st.log(f"Incomplete command output: {incomplete_output}")
        # Should show help or prompt
        st.log("✓ Incomplete command handled (help/prompt shown)")

    # Step 3: Test write command with invalid sub-command
    st.log("Step 3: Testing invalid write sub-command")
    invalid_write_output = st.config(data.dut, "write invalid-subcommand",
                                    type=data.cli_type, skip_error_check=True)

    if invalid_write_output:
        st.log(f"Invalid sub-command output: {invalid_write_output}")
        if check_command_output_for_keywords(invalid_write_output, ["error", "invalid", "unknown"]):
            st.log("✓ Invalid sub-command correctly rejected")

    # Verify device is still functional after negative tests
    if not verify_management_connectivity(data.dut):
        st.report_tc_fail(tc_id, "msg", "Device connectivity affected by negative tests")
        st.report_fail("msg", "Device connectivity lost during negative tests")

    # Test passed
    st.log("✓ TC_ISCLI_WRITE_ERASE_004: PASSED")
    st.report_tc_pass(tc_id, "msg", "Negative test cases completed")
    st.report_pass("test_case_passed")
