"""
TACACS+ Global Timeout Boundary Value Analysis (BVA) Test Script
=================================================================

This module implements comprehensive TACACS+ timeout boundary testing for SONiC devices.
Tests cover global timeout configuration, boundary values, and complete TACACS+ setup
with AAA authentication.

Test Coverage:
- Global timeout boundary values (Min: 1, Max: 60)
- Invalid timeout rejection (> 60)
- Complete TACACS+ configuration (server, key, timeout, AAA)
- Configuration verification across multiple show commands
- Support for both ISCLI and Broadcom/Klish CLI types

Test Case Reference: Test Case 2.5.1 (Timeout BVA)

Module: test_tacacs_timeout_bva
Framework: spytest
Device: SONiC (ISCLI and Broadcom)
Author: Network Automation Team
Date: 2026-05-21
"""

from __future__ import annotations
import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "tacacs_server_ip": "192.168.100.87",
    "tacacs_passkey": "Drak123",
    "timeout_min": "1",
    "timeout_max": "60",
    "timeout_invalid": "65",
    "timeout_nominal": "25",
    "aaa_method_iscli": "tacacs+ local",
    "aaa_method_klish": "local group tacacs+",
    "cli_type": "klish"  # Will be auto-detected per DUT
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture.

    Module 1: UNCONFIGURATION
    - Initialize SpyTestDict variables
    - Ensure minimum topology
    - Perform unconfiguration (cleanup any existing TACACS+ config)
    - Remove all existing servers
    - Remove AAA authentication configuration

    Module 4: CLEANUP
    - Cleanup TACACS+ configuration after all tests
    - Remove servers, timeouts, keys, AAA settings
    - Restore device to default state
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TACACS+ TIMEOUT BVA: MODULE 1 - UNCONFIGURATION (PROLOGUE)")
    st.banner("=" * 80)

    # Ensure minimum topology (single DUT)
    vars = st.ensure_min_topology("D1")

    # Auto-detect CLI type based on device
    detected_cli = st.get_ui_type(vars.D1)

    # Fix: st.get_ui_type() sometimes returns "click" which doesn't work for config commands
    # "click" means Python Click CLI in bash mode - we need config mode
    # For SONiC devices, use "klish" which enters proper config mode
    if detected_cli == "click" or detected_cli not in ["klish", "rest-put", "rest-patch"]:
        # Use klish for config commands (works for both ISCLI and Broadcom)
        data.cli_type = "klish"
        st.log(f"Module Setup: Detected '{detected_cli}', using 'klish' for config mode")
    else:
        data.cli_type = detected_cli
        st.log(f"Module Setup: Using detected CLI type '{data.cli_type}' for DUT {vars.D1}")

    st.log(f"TACACS+ Server IP: {CONFIG.tacacs_server_ip}")
    st.log(f"TACACS+ Passkey: {CONFIG.tacacs_passkey}")
    st.log(f"Timeout Range: {CONFIG.timeout_min}-{CONFIG.timeout_max} seconds")

    # MODULE 1: Unconfigure TACACS+ before starting tests
    st.log("MODULE 1: Performing unconfiguration of TACACS+ settings...")
    unconfigure_all_tacacs(vars.D1)
    st.wait(2, "Waiting for unconfiguration to complete")
    st.log("✅ MODULE 1 COMPLETED: Unconfiguration successful")

    yield  # Tests run here (MODULE 2 and MODULE 3)

    st.banner("=" * 80)
    st.banner("TACACS+ TIMEOUT BVA: MODULE 4 - CLEANUP (EPILOGUE)")
    st.banner("=" * 80)

    # MODULE 4: Cleanup after all tests
    st.log("MODULE 4: Cleaning up TACACS+ configuration...")
    cleanup_all_tacacs(vars.D1)
    st.wait(1, "Waiting for cleanup to complete")
    st.log("✅ MODULE 4 COMPLETED: Cleanup successful")


def unconfigure_all_tacacs(dut: str) -> bool:
    """
    MODULE 1: Unconfigure all TACACS+ settings on the device.

    Removes:
    - AAA authentication configuration
    - All TACACS+ servers (including junk/invalid entries)
    - Global timeout settings
    - Global passkey/key
    - Global authentication type

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"MODULE 1: Unconfiguring TACACS+ on {dut}...")

        # Use stored CLI type from module setup
        cli_type = data.cli_type

        if cli_type == "klish":
            # Broadcom/Klish syntax
            commands = [
                # Remove AAA authentication
                "no aaa authentication login default",
                "no aaa authentication failthrough",
                # Remove servers (common test servers)
                "no tacacs-server host 192.168.100.87",
                "no tacacs-server host 192.168.100.174",
                "no tacacs-server host 192.168.100.175",
                "no tacacs-server host 10.1.1.1",
                "no tacacs-server host 192.168.1.10",
                "no tacacs-server host 192.168.1.20",
                # Remove global settings
                "no tacacs-server timeout",
                "no tacacs-server key",
                "no tacacs-server auth-type",
            ]
        else:
            # ISCLI/Click syntax
            commands = [
                # Remove AAA authentication
                "no aaa authentication login",
                "no aaa authentication failthrough",
                # Remove servers (including junk entries from manual testing)
                "no tacacs server 192.168.100.87",
                "no tacacs server 192.168.100.174",
                "no tacacs server 192.168.100.175",
                "no tacacs server 1-00.120.102.1",
                "no tacacs server 1-00.12draksha0.102.1",
                "no tacacs server 10l.10.01.01",
                "no tacacs server 192.168.100.1",
                "no tacacs server 192.168.1.10",
                "no tacacs server 192.168.1.20",
                # Remove global settings
                "no tacacs timeout",
                "no tacacs passkey",
                "no tacacs authtype",
            ]

        st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.log(f"✅ Unconfiguration completed on {dut}")
        return True

    except Exception as e:
        st.log(f"⚠️  Unconfiguration note: {str(e)}")
        return True  # Continue even if unconfiguration has issues


def configure_global_timeout(dut: str, timeout: str, expect_fail: bool = False) -> bool:
    """
    MODULE 2: Configure global TACACS+ timeout.

    Args:
        dut: Device identifier
        timeout: Timeout value in seconds
        expect_fail: If True, expect the command to fail (for negative testing)

    Returns:
        bool: True if successful (or failed as expected), False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 2: Configuring TACACS+ timeout: {timeout}s (CLI: {cli_type})")

        if cli_type == "klish":
            commands = [f"tacacs-server timeout {timeout}"]
        else:
            commands = [f"tacacs timeout {timeout}"]

        output = st.config(dut, commands, type=cli_type, skip_error_check=expect_fail)

        if expect_fail:
            # Check if command was rejected (error in output)
            if output and ("Error" in str(output) or "Invalid" in str(output)):
                st.log(f"✅ Command rejected as expected for timeout {timeout}")
                return True
            else:
                st.error(f"❌ Expected rejection for timeout {timeout}, but command accepted")
                return False
        else:
            st.wait(1, "Waiting for timeout configuration")
            st.log(f"✅ Timeout configured to {timeout}s")
            return True

    except Exception as e:
        if expect_fail:
            st.log(f"✅ Command failed as expected: {str(e)}")
            return True
        else:
            st.error(f"❌ Failed to configure timeout: {str(e)}")
            return False


def configure_global_key(dut: str, passkey: str) -> bool:
    """
    MODULE 2: Configure global TACACS+ shared secret (passkey/key).

    Args:
        dut: Device identifier
        passkey: TACACS+ shared secret

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 2: Configuring TACACS+ key: {passkey}")

        if cli_type == "klish":
            commands = [f"tacacs-server key {passkey}"]
        else:
            commands = [f"tacacs passkey {passkey}"]

        st.config(dut, commands, type=cli_type)
        st.wait(1, "Waiting for key configuration")
        st.log(f"✅ Key configured")
        return True

    except Exception as e:
        st.error(f"❌ Failed to configure key: {str(e)}")
        return False


def configure_tacacs_server(dut: str, server_ip: str) -> bool:
    """
    MODULE 2: Configure TACACS+ server.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IP address

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 2: Configuring TACACS+ server: {server_ip}")

        if cli_type == "klish":
            commands = [f"tacacs-server host {server_ip}"]
        else:
            commands = [f"tacacs server {server_ip}"]

        st.config(dut, commands, type=cli_type)
        st.wait(1, "Waiting for server configuration")
        st.log(f"✅ Server {server_ip} configured")
        return True

    except Exception as e:
        st.error(f"❌ Failed to configure server: {str(e)}")
        return False


def configure_aaa_authentication(dut: str) -> bool:
    """
    MODULE 2: Configure AAA authentication to use TACACS+.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 2: Configuring AAA authentication")

        if cli_type == "klish":
            # Broadcom: aaa authentication login default local group tacacs+
            commands = [f"aaa authentication login default {CONFIG.aaa_method_klish}"]
        else:
            # ISCLI: aaa authentication login tacacs+ local
            commands = [f"aaa authentication login {CONFIG.aaa_method_iscli}"]

        st.config(dut, commands, type=cli_type)
        st.wait(1, "Waiting for AAA configuration")
        st.log(f"✅ AAA authentication configured")
        return True

    except Exception as e:
        st.error(f"❌ Failed to configure AAA: {str(e)}")
        return False


def verify_tacacs_timeout(dut: str, expected_timeout: str) -> bool:
    """
    MODULE 3: Verify TACACS+ timeout configuration.

    Args:
        dut: Device identifier
        expected_timeout: Expected timeout value

    Returns:
        bool: True if timeout matches expected value, False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 3: Verifying TACACS+ timeout (expected: {expected_timeout}s)")

        if cli_type == "klish":
            output = st.show(dut, "show tacacs-server", type=cli_type, skip_error_check=True)
        else:
            output = st.show(dut, "show tacacs", type=cli_type, skip_error_check=True)

        if output:
            output_str = str(output)
            st.log(f"TACACS+ Configuration Output:\n{output_str}")

            # Check if timeout appears in output
            if f"timeout {expected_timeout}" in output_str or f"timeout: {expected_timeout}" in output_str:
                st.log(f"✅ Timeout {expected_timeout}s verified in output")
                return True
            else:
                st.error(f"❌ Expected timeout {expected_timeout}s not found in output")
                return False
        else:
            st.error(f"❌ No TACACS+ configuration output")
            return False

    except Exception as e:
        st.error(f"❌ Failed to verify timeout: {str(e)}")
        return False


def verify_tacacs_server(dut: str, expected_server: str) -> bool:
    """
    MODULE 3: Verify TACACS+ server configuration.

    Args:
        dut: Device identifier
        expected_server: Expected server IP address

    Returns:
        bool: True if server is configured, False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 3: Verifying TACACS+ server: {expected_server}")

        if cli_type == "klish":
            output = st.show(dut, "show tacacs-server", type=cli_type, skip_error_check=True)
        else:
            output = st.show(dut, "show tacacs", type=cli_type, skip_error_check=True)

        if output:
            output_str = str(output)
            if expected_server in output_str:
                st.log(f"✅ Server {expected_server} verified in output")
                return True
            else:
                st.error(f"❌ Server {expected_server} not found in output")
                st.log(f"Output: {output_str}")
                return False
        else:
            st.error(f"❌ No TACACS+ configuration output")
            return False

    except Exception as e:
        st.error(f"❌ Failed to verify server: {str(e)}")
        return False


def verify_aaa_configuration(dut: str) -> bool:
    """
    MODULE 3: Verify AAA authentication configuration.

    Args:
        dut: Device identifier

    Returns:
        bool: True if AAA is configured with TACACS+, False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 3: Verifying AAA authentication configuration")

        output = st.show(dut, "show aaa", type=cli_type, skip_error_check=True)

        if output:
            output_str = str(output)
            st.log(f"AAA Configuration Output:\n{output_str}")

            # Check if tacacs+ is in the authentication method
            if "tacacs+" in output_str.lower():
                st.log(f"✅ AAA authentication includes TACACS+")
                return True
            else:
                st.error(f"❌ TACACS+ not found in AAA authentication")
                return False
        else:
            st.error(f"❌ No AAA configuration output")
            return False

    except Exception as e:
        st.error(f"❌ Failed to verify AAA: {str(e)}")
        return False


def cleanup_all_tacacs(dut: str) -> bool:
    """
    MODULE 4: Cleanup and remove all TACACS+ configuration from device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"MODULE 4: Cleaning up TACACS+ configuration on {dut}...")

        cli_type = data.cli_type

        if cli_type == "klish":
            commands = [
                "no aaa authentication login default",
                "no tacacs-server host 192.168.100.87",
                "no tacacs-server timeout",
                "no tacacs-server key",
            ]
        else:
            commands = [
                "no aaa authentication login",
                "no tacacs server 192.168.100.87",
                "no tacacs timeout",
                "no tacacs passkey",
            ]

        st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.log(f"✅ TACACS+ cleanup completed on {dut}")
        return True

    except Exception as e:
        st.error(f"❌ Failed to cleanup TACACS+: {str(e)}")
        return False


@pytest.mark.tacacs
@pytest.mark.timeout_bva
def test_tacacs_timeout_bva_min():
    """
    TEST 1: TACACS+ Timeout BVA - Minimum Value (1 second)

    Module 2: Configuration
    - Configure global timeout to minimum value (1 second)

    Module 3: Validation
    - Verify timeout is set to 1 second in CLI output

    Expected Outcome:
    - Timeout value 1 is accepted
    - Configuration is visible in show commands
    """
    st.banner("-" * 80)
    st.banner("TEST 1: TACACS+ Timeout BVA - Minimum Value (1 second)")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration
        st.log("MODULE 2: Configuration Phase")
        st.log("STEP 1: Configure minimum timeout (1 second)")
        if not configure_global_timeout(dut, CONFIG.timeout_min):
            validation_failures.append("Failed to configure minimum timeout")
        st.log("✅ MODULE 2 STEP 1 completed")

        # MODULE 3: Validation
        st.log("MODULE 3: Validation Phase")
        st.log("STEP 2: Verify minimum timeout in configuration")
        if not verify_tacacs_timeout(dut, CONFIG.timeout_min):
            validation_failures.append(f"Failed to verify timeout {CONFIG.timeout_min}")
        st.log("✅ MODULE 3 STEP 2 completed")

        st.log("✅ TEST 1 COMPLETED: Minimum timeout BVA")

    except Exception as e:
        st.error(f"Exception in test_tacacs_timeout_bva_min: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_timeout_bva_min: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 1 PASSED: Minimum Timeout BVA")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
@pytest.mark.timeout_bva
def test_tacacs_timeout_bva_max():
    """
    TEST 2: TACACS+ Timeout BVA - Maximum Value (60 seconds)

    Module 2: Configuration
    - Configure global timeout to maximum value (60 seconds)

    Module 3: Validation
    - Verify timeout is set to 60 seconds in CLI output

    Expected Outcome:
    - Timeout value 60 is accepted
    - Configuration is visible in show commands
    """
    st.banner("-" * 80)
    st.banner("TEST 2: TACACS+ Timeout BVA - Maximum Value (60 seconds)")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration
        st.log("MODULE 2: Configuration Phase")
        st.log("STEP 1: Configure maximum timeout (60 seconds)")
        if not configure_global_timeout(dut, CONFIG.timeout_max):
            validation_failures.append("Failed to configure maximum timeout")
        st.log("✅ MODULE 2 STEP 1 completed")

        # MODULE 3: Validation
        st.log("MODULE 3: Validation Phase")
        st.log("STEP 2: Verify maximum timeout in configuration")
        if not verify_tacacs_timeout(dut, CONFIG.timeout_max):
            validation_failures.append(f"Failed to verify timeout {CONFIG.timeout_max}")
        st.log("✅ MODULE 3 STEP 2 completed")

        st.log("✅ TEST 2 COMPLETED: Maximum timeout BVA")

    except Exception as e:
        st.error(f"Exception in test_tacacs_timeout_bva_max: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_timeout_bva_max: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 2 PASSED: Maximum Timeout BVA")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
@pytest.mark.timeout_bva
@pytest.mark.negative
def test_tacacs_timeout_bva_invalid():
    """
    TEST 3: TACACS+ Timeout BVA - Invalid Value (>60 seconds)

    Module 2: Configuration
    - Attempt to configure timeout > 60 (invalid value: 65)

    Module 3: Validation
    - Verify command is rejected with error

    Expected Outcome:
    - Timeout value 65 is rejected
    - Error message is displayed
    - Configuration remains unchanged
    """
    st.banner("-" * 80)
    st.banner("TEST 3: TACACS+ Timeout BVA - Invalid Value (65 seconds)")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration (Negative Test)
        st.log("MODULE 2: Configuration Phase (Negative Test)")
        st.log("STEP 1: Attempt to configure invalid timeout (65 seconds)")
        if not configure_global_timeout(dut, CONFIG.timeout_invalid, expect_fail=True):
            validation_failures.append("Failed to reject invalid timeout (command should have been rejected)")
        st.log("✅ MODULE 2 STEP 1 completed: Invalid timeout rejected")

        st.log("✅ TEST 3 COMPLETED: Invalid timeout rejection")

    except Exception as e:
        st.error(f"Exception in test_tacacs_timeout_bva_invalid: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_timeout_bva_invalid: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 3 PASSED: Invalid Timeout Rejection")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
@pytest.mark.timeout_bva
@pytest.mark.integration
def test_tacacs_complete_configuration_with_timeout():
    """
    TEST 4: Complete TACACS+ Configuration with Timeout

    Module 2: Configuration
    - Configure TACACS+ server (192.168.100.87)
    - Configure global passkey (Drak123)
    - Configure global timeout (25 seconds)
    - Configure AAA authentication (tacacs+ local)

    Module 3: Validation
    - Verify server is configured
    - Verify timeout is set to 25 seconds
    - Verify AAA authentication includes TACACS+
    - Display complete configuration

    Expected Outcome:
    - All configurations are applied successfully
    - All validations pass
    - Complete TACACS+ setup is functional
    """
    st.banner("-" * 80)
    st.banner("TEST 4: Complete TACACS+ Configuration with Timeout")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration
        st.log("MODULE 2: Configuration Phase")

        st.log("STEP 1: Configure TACACS+ server")
        if not configure_tacacs_server(dut, CONFIG.tacacs_server_ip):
            validation_failures.append("Failed to configure TACACS+ server")
        st.log("✅ MODULE 2 STEP 1 completed")

        st.log("STEP 2: Configure TACACS+ passkey")
        if not configure_global_key(dut, CONFIG.tacacs_passkey):
            validation_failures.append("Failed to configure TACACS+ key")
        st.log("✅ MODULE 2 STEP 2 completed")

        st.log("STEP 3: Configure TACACS+ timeout (25 seconds)")
        if not configure_global_timeout(dut, CONFIG.timeout_nominal):
            validation_failures.append("Failed to configure nominal timeout")
        st.log("✅ MODULE 2 STEP 3 completed")

        st.log("STEP 4: Configure AAA authentication")
        if not configure_aaa_authentication(dut):
            validation_failures.append("Failed to configure AAA authentication")
        st.log("✅ MODULE 2 STEP 4 completed")

        # MODULE 3: Validation
        st.log("MODULE 3: Validation Phase")

        st.log("STEP 5: Verify TACACS+ server configuration")
        if not verify_tacacs_server(dut, CONFIG.tacacs_server_ip):
            validation_failures.append(f"Failed to verify server {CONFIG.tacacs_server_ip}")
        st.log("✅ MODULE 3 STEP 5 completed")

        st.log("STEP 6: Verify TACACS+ timeout configuration")
        if not verify_tacacs_timeout(dut, CONFIG.timeout_nominal):
            validation_failures.append(f"Failed to verify timeout {CONFIG.timeout_nominal}")
        st.log("✅ MODULE 3 STEP 6 completed")

        st.log("STEP 7: Verify AAA authentication configuration")
        if not verify_aaa_configuration(dut):
            validation_failures.append("Failed to verify AAA authentication")
        st.log("✅ MODULE 3 STEP 7 completed")

        st.log("STEP 8: Display complete TACACS+ configuration")
        cli_type = data.cli_type
        if cli_type == "klish":
            tacacs_output = st.show(dut, "show tacacs-server", type=cli_type, skip_error_check=True)
        else:
            tacacs_output = st.show(dut, "show tacacs", type=cli_type, skip_error_check=True)
        aaa_output = st.show(dut, "show aaa", type=cli_type, skip_error_check=True)
        st.log(f"Complete TACACS+ Configuration:\n{tacacs_output}")
        st.log(f"AAA Configuration:\n{aaa_output}")
        st.log("✅ MODULE 3 STEP 8 completed")

        st.log("✅ TEST 4 COMPLETED: Complete TACACS+ Configuration")

    except Exception as e:
        st.error(f"Exception in test_tacacs_complete_configuration_with_timeout: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_complete_configuration_with_timeout: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 4 PASSED: Complete TACACS+ Configuration")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


if __name__ == "__main__":
    # This allows running the script directly for debugging
    st.log("Running TACACS+ Timeout BVA tests directly")
    pytest.main([__file__, "-v", "-s"])
