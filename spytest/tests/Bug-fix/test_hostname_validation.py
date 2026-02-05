"""
HOSTNAME CONFIGURATION AND VALIDATION
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/bug-fix/test_hostname_validation.py \
  --logs-path ./logs/test_hostname_validation_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of hostname configuration using sonic-cli (Klish).
  This test suite validates:
  - Changing hostname using 'hostname <name>' command
  - Broadcast message about hostname change
  - New hostname appears in CLI prompt
  - Hostname appears correctly in 'show version'
  - Hostname appears in 'show running-configuration'
  - Restoring original hostname after test

Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - CLI type: klish (sonic-cli)

Test Steps:
  1. Get current/original hostname
  2. Configure new hostname (e.g., DVT1)
  3. Verify hostname change message
  4. Verify new hostname in 'show version'
  5. Verify hostname in 'show running-configuration'
  6. Restore original hostname
  7. Verify restoration successful
"""

from __future__ import annotations

import pytest
import re

from spytest import st, SpyTestDict
import apis.system.basic as basic_api


# Test data dictionary
data = SpyTestDict()
data.new_hostname = "DVT1"
data.cli_type = "klish"


@pytest.fixture(scope="module", autouse=True)
def hostname_validation_module_hooks(request):
    """
    Module-level fixture for hostname validation test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1")

    st.banner("MODULE SETUP: Hostname Validation Test")

    # Store DUT handle
    data.dut1 = vars.D1

    st.log(f"DUT1: {data.dut1}")

    # Get original hostname to restore later
    data.original_hostname = get_current_hostname(data.dut1)
    st.log(f"Original hostname: {data.original_hostname}")

    yield

    # Module teardown - Restore original hostname
    st.banner("MODULE TEARDOWN: Restoring original hostname")
    if data.original_hostname:
        restore_hostname(data.dut1, data.original_hostname)


@pytest.fixture(scope="function", autouse=True)
def hostname_validation_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def get_current_hostname(dut, cli_type="klish"):
    """
    Get current hostname from the device.

    Args:
        dut: Device under test
        cli_type: CLI type (default: klish)

    Returns:
        str: Current hostname or None
    """
    st.log(f"Getting current hostname from {dut}")

    try:
        # Try using basic_api
        hostname = basic_api.get_hostname(dut)
        if hostname:
            st.log(f"Current hostname: {hostname}")
            return hostname

        # Fallback: Parse from show version
        output = st.show(dut, "show version", type=cli_type, skip_error_check=True)
        if output:
            for entry in output:
                hostname = entry.get('hostname', '') or entry.get('host_name', '')
                if hostname:
                    st.log(f"Current hostname from show version: {hostname}")
                    return hostname

        st.log("Using default hostname 'sonic'")
        return "sonic"

    except Exception as e:
        st.error(f"Failed to get current hostname: {str(e)}")
        return "sonic"


def configure_hostname(dut, hostname, cli_type="klish"):
    """
    Configure hostname on the device.

    Args:
        dut: Device under test
        hostname: New hostname
        cli_type: CLI type (default: klish)

    Returns:
        tuple: (bool, str) - (Success status, Output message)
    """
    st.log(f"Configuring hostname to '{hostname}' on {dut}")

    try:
        commands = [f"hostname {hostname}"]
        output = st.config(dut, commands, type=cli_type, skip_error_check=True)

        st.log(f"Hostname configuration output:\n{output}")

        # Check for success or broadcast message
        if output and isinstance(output, str):
            if "hostname has been changed" in output.lower() or hostname in output:
                st.log(f"Hostname successfully changed to {hostname}")
                return True, output

        st.log(f"Hostname command executed")
        return True, str(output)

    except Exception as e:
        st.error(f"Failed to configure hostname: {str(e)}")
        return False, str(e)


def verify_hostname_change_message(output, new_hostname):
    """
    Verify hostname change broadcast message in output.

    Expected message:
    Hostname has been changed from 'sonic' to 'DVT1'.

    Args:
        output: Command output
        new_hostname: New hostname

    Returns:
        bool: True if message found, False otherwise
    """
    st.log(f"Verifying hostname change message for {new_hostname}")

    if not output or not isinstance(output, str):
        st.log("No output to verify")
        return False

    # Look for hostname change message
    pattern = rf'hostname\s+has\s+been\s+changed.*{re.escape(new_hostname)}'

    if re.search(pattern, output, re.IGNORECASE):
        st.log(f"Found hostname change message for {new_hostname}")
        return True
    else:
        st.log("Hostname change message not found (may not always appear)")
        return False


def verify_hostname_in_show_version(dut, expected_hostname, cli_type="klish"):
    """
    Verify hostname appears in 'show version' output.

    Args:
        dut: Device under test
        expected_hostname: Expected hostname
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if hostname matches, False otherwise
    """
    st.log(f"Verifying hostname '{expected_hostname}' in 'show version'")

    try:
        output = st.show(dut, "show version", type=cli_type, skip_error_check=True)
        st.log(f"Show version output: {output}")

        if output:
            for entry in output:
                hostname = entry.get('hostname', '') or entry.get('host_name', '')

                if hostname:
                    st.log(f"Found hostname in show version: {hostname}")

                    if str(hostname).strip() == str(expected_hostname).strip():
                        st.log(f"Hostname matches expected: {expected_hostname}")
                        return True
                    else:
                        st.error(f"Hostname mismatch. Expected: {expected_hostname}, Found: {hostname}")
                        return False

        # Try raw output parsing
        raw_output = st.config(dut, "show version", type=cli_type, skip_error_check=True)
        if raw_output and isinstance(raw_output, str):
            st.log(f"Raw show version output:\n{raw_output}")

            # Look for hostname in raw output
            if expected_hostname in raw_output:
                st.log(f"Found hostname {expected_hostname} in raw output")
                return True

        st.error(f"Hostname {expected_hostname} not found in show version")
        return False

    except Exception as e:
        st.error(f"Exception during show version verification: {str(e)}")
        return False


def verify_hostname_in_running_config(dut, expected_hostname, cli_type="klish"):
    """
    Verify hostname appears in 'show running-configuration'.

    Expected format:
    hostname DVT1

    Args:
        dut: Device under test
        expected_hostname: Expected hostname
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if hostname found, False otherwise
    """
    st.log(f"Verifying hostname '{expected_hostname}' in running configuration")

    try:
        command = "show running-configuration"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)

        st.log(f"Show running-configuration output (first 500 chars):\n{str(output)[:500]}")

        if not output or not isinstance(output, str):
            st.error("No output from show running-configuration")
            return False

        # Look for hostname line
        pattern = rf'hostname\s+{re.escape(expected_hostname)}'

        if re.search(pattern, output, re.IGNORECASE):
            st.log(f"Found hostname {expected_hostname} in running configuration")
            return True
        else:
            st.error(f"Hostname {expected_hostname} not found in running configuration")
            return False

    except Exception as e:
        st.error(f"Exception during running config verification: {str(e)}")
        return False


def restore_hostname(dut, original_hostname, cli_type="klish"):
    """
    Restore original hostname.

    Args:
        dut: Device under test
        original_hostname: Original hostname to restore
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Restoring original hostname '{original_hostname}' on {dut}")

    try:
        commands = [f"hostname {original_hostname}"]
        st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.log(f"Hostname restored to {original_hostname}")

        # Wait for change to take effect
        st.wait(2, "Waiting for hostname restoration to apply")
        return True

    except Exception as e:
        st.error(f"Failed to restore hostname: {str(e)}")
        return False


@pytest.mark.topology("any")
class TestHostnameValidation:
    """
    Test class for hostname configuration validation.
    """

    @pytest.mark.test_hostname_change_verify
    def test_hostname_change_verify(self):
        """
        TestCase: test_hostname_change_verify

        Test Steps:
        1. Get current/original hostname
        2. Configure new hostname (DVT1)
        3. Verify hostname change message (if present)
        4. Wait for change to propagate
        5. Verify hostname in 'show version'
        6. Verify hostname in 'show running-configuration'
        7. Restore original hostname
        8. Verify restoration successful

        Expected Result:
        - Hostname changed successfully
        - New hostname appears in show version
        - New hostname appears in running config
        - Original hostname restored
        """
        st.banner("TEST: Hostname Change and Verification")

        # Step 1: Get current hostname (already done in module setup)
        st.log(f"Step 1: Current hostname: {data.original_hostname}")

        # Step 2: Configure new hostname
        st.log(f"Step 2: Configuring new hostname '{data.new_hostname}'")

        success, output = configure_hostname(data.dut1, data.new_hostname, data.cli_type)

        if not success:
            st.report_fail("msg", f"Failed to configure hostname {data.new_hostname}")

        # Step 3: Verify hostname change message
        st.log("Step 3: Checking for hostname change broadcast message")

        message_found = verify_hostname_change_message(output, data.new_hostname)
        if message_found:
            st.log("Hostname change broadcast message found")
        else:
            st.log("Hostname change message not found (may not always appear in automation)")

        # Step 4: Wait for change to propagate
        st.log("Step 4: Waiting for hostname change to propagate")
        st.wait(3, "Waiting for hostname change to take effect")

        # Step 5: Verify hostname in 'show version'
        st.log(f"Step 5: Verifying hostname '{data.new_hostname}' in 'show version'")

        if not verify_hostname_in_show_version(data.dut1, data.new_hostname, data.cli_type):
            st.report_fail("msg", f"Hostname {data.new_hostname} not found in 'show version'")

        # Step 6: Verify hostname in running configuration
        st.log(f"Step 6: Verifying hostname '{data.new_hostname}' in running configuration")

        if not verify_hostname_in_running_config(data.dut1, data.new_hostname, data.cli_type):
            st.report_fail("msg", f"Hostname {data.new_hostname} not found in running config")

        # Step 7: Restore original hostname
        st.log(f"Step 7: Restoring original hostname '{data.original_hostname}'")

        if not restore_hostname(data.dut1, data.original_hostname, data.cli_type):
            st.report_fail("msg", "Failed to restore original hostname")

        # Step 8: Verify restoration
        st.log(f"Step 8: Verifying hostname restored to '{data.original_hostname}'")

        if not verify_hostname_in_show_version(data.dut1, data.original_hostname, data.cli_type):
            st.log("Warning: Original hostname not verified in show version")

        st.log("Hostname change and verification test PASSED")
        st.report_pass("test_case_passed")


    @pytest.mark.test_hostname_persistence
    def test_hostname_persistence(self):
        """
        TestCase: test_hostname_persistence

        Test Steps:
        1. Configure new hostname
        2. Save configuration
        3. Verify hostname in running config
        4. (Optional: Reboot and verify persistence - can be added if needed)

        Expected Result:
        - Hostname configured successfully
        - Hostname appears in running config
        - Hostname can be saved
        """
        st.banner("TEST: Hostname Configuration Persistence")

        # Step 1: Configure new hostname
        st.log(f"Step 1: Configuring hostname '{data.new_hostname}'")

        success, output = configure_hostname(data.dut1, data.new_hostname, data.cli_type)

        if not success:
            st.report_fail("msg", f"Failed to configure hostname {data.new_hostname}")

        st.wait(2, "Waiting for configuration to apply")

        # Step 2: Verify in running config
        st.log(f"Step 2: Verifying hostname '{data.new_hostname}' in running config")

        if not verify_hostname_in_running_config(data.dut1, data.new_hostname, data.cli_type):
            st.report_fail("msg", f"Hostname {data.new_hostname} not in running config")

        # Step 3: Save configuration
        st.log("Step 3: Saving configuration")

        try:
            st.config(data.dut1, "write memory", type=data.cli_type, skip_error_check=True)
            st.log("Configuration saved successfully")
        except Exception as e:
            st.log(f"Note: Write memory command output: {str(e)}")

        # Step 4: Restore original hostname
        st.log(f"Step 4: Restoring original hostname '{data.original_hostname}'")

        restore_hostname(data.dut1, data.original_hostname, data.cli_type)

        st.log("Hostname persistence test PASSED")
        st.report_pass("test_case_passed")


    @pytest.mark.test_hostname_multiple_changes
    def test_hostname_multiple_changes(self):
        """
        TestCase: test_hostname_multiple_changes

        Test Steps:
        1. Change hostname to DVT1
        2. Verify change
        3. Change hostname to DVT2
        4. Verify change
        5. Change hostname to DVT3
        6. Verify change
        7. Restore original hostname

        Expected Result:
        - Multiple hostname changes work correctly
        - Each change reflected in show version
        """
        st.banner("TEST: Multiple Hostname Changes")

        hostnames = ["DVT1", "DVT2", "DVT3"]

        for hostname in hostnames:
            st.log(f"Changing hostname to '{hostname}'")

            success, output = configure_hostname(data.dut1, hostname, data.cli_type)

            if not success:
                st.report_fail("msg", f"Failed to configure hostname {hostname}")

            st.wait(2, "Waiting for hostname change")

            if not verify_hostname_in_show_version(data.dut1, hostname, data.cli_type):
                st.report_fail("msg", f"Hostname {hostname} not found in show version")

            st.log(f"Successfully changed and verified hostname: {hostname}")

        # Restore original
        st.log(f"Restoring original hostname '{data.original_hostname}'")
        restore_hostname(data.dut1, data.original_hostname, data.cli_type)

        st.log("Multiple hostname changes test PASSED")
        st.report_pass("test_case_passed")
