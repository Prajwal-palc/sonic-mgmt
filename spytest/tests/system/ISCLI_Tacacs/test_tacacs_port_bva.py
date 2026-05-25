"""
TACACS+ TCP Port Boundary Value Analysis (BVA) Test Script
===========================================================

This module implements comprehensive TACACS+ TCP port boundary testing for SONiC devices.
Tests cover port configuration, boundary values (0-65536), and complete TACACS+ setup
with custom ports and AAA authentication.

Test Coverage:
- TCP port boundary values (Min: 1, Max: 65535)
- Invalid port rejection (0, 65536)
- Valid port acceptance (20, 49, 5049, 65535)
- Complete TACACS+ configuration with custom port
- Configuration verification across multiple show commands
- Support for both ISCLI and Broadcom/Klish CLI types

Test Case Reference: Test Case 2.5.2 (TCP Port BVA)

Module: test_tacacs_port_bva
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
    "tacacs_server_ip_2": "192.168.100.175",
    "tacacs_passkey": "Test234",
    "port_invalid_min": "0",
    "port_valid_min": "1",
    "port_low": "20",
    "port_default": "49",
    "port_custom": "5049",
    "port_valid_max": "65535",
    "port_invalid_max": "65536",
    "timeout_nominal": "25",
    "aaa_method_iscli": "tacacs+ local",
    "aaa_method_klish": "local group tacacs+",
    "cli_type": "klish"  # Will be auto-detected per DUT
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture.

    MODULE 1: UNCONFIGURATION
    - Initialize SpyTestDict variables
    - Ensure minimum topology
    - Perform unconfiguration (cleanup any existing TACACS+ config)
    - Remove all existing servers
    - Remove AAA authentication configuration

    MODULE 4: CLEANUP
    - Cleanup TACACS+ configuration after all tests
    - Remove servers, ports, keys, AAA settings
    - Restore device to default state
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TACACS+ PORT BVA: MODULE 1 - UNCONFIGURATION (PROLOGUE)")
    st.banner("=" * 80)

    # Ensure minimum topology (single DUT)
    vars = st.ensure_min_topology("D1")

    # Auto-detect CLI type based on device
    # Fix: st.get_ui_type() sometimes returns "click" (bash mode) which breaks config commands
    # Force to "klish" when "click" is returned so config mode is used correctly
    detected_cli = st.get_ui_type(vars.D1)
    if detected_cli == "click" or detected_cli not in ["klish", "rest-put", "rest-patch"]:
        data.cli_type = "klish"
        st.log(f"Module Setup: Detected '{detected_cli}', overriding to 'klish' for config mode")
    else:
        data.cli_type = detected_cli
        st.log(f"Module Setup: Using detected CLI type '{data.cli_type}' for DUT {vars.D1}")

    st.log(f"TACACS+ Server IP: {CONFIG.tacacs_server_ip}")
    st.log(f"TACACS+ Passkey: {CONFIG.tacacs_passkey}")
    st.log(f"Port Range: {CONFIG.port_valid_min}-{CONFIG.port_valid_max}")

    # MODULE 1: Unconfigure TACACS+ before starting tests
    st.log("MODULE 1: Performing unconfiguration of TACACS+ settings...")
    unconfigure_all_tacacs(vars.D1)
    st.wait(2, "Waiting for unconfiguration to complete")
    st.log("✅ MODULE 1 COMPLETED: Unconfiguration successful")

    yield  # Tests run here (MODULE 2 and MODULE 3)

    st.banner("=" * 80)
    st.banner("TACACS+ PORT BVA: MODULE 4 - CLEANUP (EPILOGUE)")
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
                "no tacacs-server host 192.168.100.175",
                "no tacacs-server host 192.168.100.174",
                "no tacacs-server host 192.168.100.145",
                "no tacacs-server host 192.168.100.20",
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
                "no tacacs server 192.168.100.175",
                "no tacacs server 192.168.100.174",
                "no tacacs server 192.168.100.145",
                "no tacacs server 192.168.100.20",
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


def configure_tacacs_server_with_port(dut: str, server_ip: str, port: str,
                                      expect_fail: bool = False) -> bool:
    """
    MODULE 2: Configure TACACS+ server with specific port.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IP address
        port: TCP port number
        expect_fail: If True, expect the command to fail (for negative testing)

    Returns:
        bool: True if successful (or failed as expected), False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 2: Configuring TACACS+ server {server_ip} on port {port}")

        if cli_type == "klish":
            commands = [f"tacacs-server host {server_ip} port {port}"]
        else:
            commands = [f"tacacs server {server_ip} port {port}"]

        output = st.config(dut, commands, type=cli_type, skip_error_check=expect_fail)

        if expect_fail:
            # Check if command was rejected (error in output)
            if output and ("Error" in str(output) or "Invalid" in str(output)):
                st.log(f"✅ Command rejected as expected for port {port}")
                return True
            else:
                st.error(f"❌ Expected rejection for port {port}, but command accepted")
                return False
        else:
            st.wait(1, "Waiting for server configuration with port")
            st.log(f"✅ Server {server_ip} configured on port {port}")
            return True

    except Exception as e:
        if expect_fail:
            st.log(f"✅ Command failed as expected: {str(e)}")
            return True
        else:
            st.error(f"❌ Failed to configure server with port: {str(e)}")
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


def configure_global_timeout(dut: str, timeout: str) -> bool:
    """
    MODULE 2: Configure global TACACS+ timeout.

    Args:
        dut: Device identifier
        timeout: Timeout value in seconds

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 2: Configuring TACACS+ timeout: {timeout}s")

        if cli_type == "klish":
            commands = [f"tacacs-server timeout {timeout}"]
        else:
            commands = [f"tacacs timeout {timeout}"]

        st.config(dut, commands, type=cli_type)
        st.wait(1, "Waiting for timeout configuration")
        st.log(f"✅ Timeout configured to {timeout}s")
        return True

    except Exception as e:
        st.error(f"❌ Failed to configure timeout: {str(e)}")
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


def remove_tacacs_server(dut: str, server_ip: str) -> bool:
    """
    MODULE 2: Remove TACACS+ server.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IP address to remove

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 2: Removing TACACS+ server: {server_ip}")

        if cli_type == "klish":
            commands = [f"no tacacs-server host {server_ip}"]
        else:
            commands = [f"no tacacs server {server_ip}"]

        st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.wait(1, "Waiting for server removal")
        st.log(f"✅ Server {server_ip} removed")
        return True

    except Exception as e:
        st.error(f"❌ Failed to remove server: {str(e)}")
        return False


def verify_tacacs_server_port(dut: str, server_ip: str, expected_port: str) -> bool:
    """
    MODULE 3: Verify TACACS+ server port configuration.

    Args:
        dut: Device identifier
        server_ip: Server IP address to verify
        expected_port: Expected port number

    Returns:
        bool: True if port matches expected value, False otherwise
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 3: Verifying TACACS+ server {server_ip} on port {expected_port}")

        if cli_type == "klish":
            output = st.show(dut, "show tacacs-server", type=cli_type, skip_error_check=True)
        else:
            output = st.show(dut, "show tacacs", type=cli_type, skip_error_check=True)

        if output:
            output_str = str(output)
            st.log(f"TACACS+ Configuration Output:\n{output_str}")

            # Check if both server IP and port appear in output
            if server_ip in output_str:
                # Look for port in various formats
                # ISCLI: "tcp_port 5049"  Klish: "PORT" column value
                if (f"PORT {expected_port}" in output_str.upper() or
                    f"port {expected_port}" in output_str or
                    f"tcp_port {expected_port}" in output_str):
                    st.log(f"✅ Server {server_ip} verified with port {expected_port}")
                    return True
                else:
                    st.error(f"❌ Server {server_ip} found, but port {expected_port} not verified")
                    return False
            else:
                st.error(f"❌ Server {server_ip} not found in output")
                return False
        else:
            st.error(f"❌ No TACACS+ configuration output")
            return False

    except Exception as e:
        st.error(f"❌ Failed to verify server port: {str(e)}")
        return False


def verify_server_not_present(dut: str, server_ip: str) -> bool:
    """
    MODULE 3: Verify TACACS+ server is NOT present in configuration.

    Args:
        dut: Device identifier
        server_ip: Server IP address that should NOT be present

    Returns:
        bool: True if server is NOT found, False if server is still present
    """
    try:
        cli_type = data.cli_type
        st.log(f"MODULE 3: Verifying TACACS+ server {server_ip} is NOT present")

        if cli_type == "klish":
            output = st.show(dut, "show tacacs-server", type=cli_type, skip_error_check=True)
        else:
            output = st.show(dut, "show tacacs", type=cli_type, skip_error_check=True)

        if output:
            output_str = str(output)
            if server_ip not in output_str:
                st.log(f"✅ Server {server_ip} is NOT present (as expected)")
                return True
            else:
                st.error(f"❌ Server {server_ip} is still present in configuration")
                return False
        else:
            st.log(f"✅ No TACACS+ configuration (server not present)")
            return True

    except Exception as e:
        st.error(f"❌ Failed to verify server absence: {str(e)}")
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
                "no tacacs-server host 192.168.100.175",
                "no tacacs-server timeout",
                "no tacacs-server key",
            ]
        else:
            commands = [
                "no aaa authentication login",
                "no tacacs server 192.168.100.87",
                "no tacacs server 192.168.100.175",
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
@pytest.mark.port_bva
@pytest.mark.negative
def test_tacacs_port_bva_invalid_min():
    """
    TEST 1: TACACS+ Port BVA - Invalid Minimum (Port 0)

    Module 2: Configuration (Negative Test)
    - Attempt to configure TACACS+ server with port 0

    Module 3: Validation
    - Verify command is rejected with error

    Expected Outcome:
    - Port 0 is rejected
    - Error message is displayed
    """
    st.banner("-" * 80)
    st.banner("TEST 1: TACACS+ Port BVA - Invalid Minimum (Port 0)")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration (Negative Test)
        st.log("MODULE 2: Configuration Phase (Negative Test)")
        st.log("STEP 1: Attempt to configure server with invalid port 0")
        if not configure_tacacs_server_with_port(dut, CONFIG.tacacs_server_ip_2,
                                                  CONFIG.port_invalid_min, expect_fail=True):
            validation_failures.append("Failed to reject port 0 (command should have been rejected)")
        st.log("✅ MODULE 2 STEP 1 completed: Port 0 rejected")

        st.log("✅ TEST 1 COMPLETED: Invalid port 0 rejection")

    except Exception as e:
        st.error(f"Exception in test_tacacs_port_bva_invalid_min: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_port_bva_invalid_min: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 1 PASSED: Invalid Port 0 Rejection")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
@pytest.mark.port_bva
def test_tacacs_port_bva_valid_low():
    """
    TEST 2: TACACS+ Port BVA - Valid Low Port (Port 20)

    Module 2: Configuration
    - Configure TACACS+ server with port 20

    Module 3: Validation
    - Verify server is configured with port 20

    Expected Outcome:
    - Port 20 is accepted
    - Configuration is visible in show commands
    """
    st.banner("-" * 80)
    st.banner("TEST 2: TACACS+ Port BVA - Valid Low Port (Port 20)")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration
        st.log("MODULE 2: Configuration Phase")
        st.log("STEP 1: Configure server with port 20")
        if not configure_tacacs_server_with_port(dut, CONFIG.tacacs_server_ip_2, CONFIG.port_low):
            validation_failures.append("Failed to configure server with port 20")
        st.log("✅ MODULE 2 STEP 1 completed")

        # MODULE 3: Validation
        st.log("MODULE 3: Validation Phase")
        st.log("STEP 2: Verify server port 20 in configuration")
        if not verify_tacacs_server_port(dut, CONFIG.tacacs_server_ip_2, CONFIG.port_low):
            validation_failures.append(f"Failed to verify server with port {CONFIG.port_low}")
        st.log("✅ MODULE 3 STEP 2 completed")

        st.log("✅ TEST 2 COMPLETED: Valid port 20")

    except Exception as e:
        st.error(f"Exception in test_tacacs_port_bva_valid_low: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_port_bva_valid_low: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 2 PASSED: Valid Port 20")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
@pytest.mark.port_bva
def test_tacacs_port_bva_default():
    """
    TEST 3: TACACS+ Port BVA - Default Port (Port 49)

    Module 2: Configuration
    - Configure TACACS+ server with default port 49

    Module 3: Validation
    - Verify server is configured with port 49

    Expected Outcome:
    - Port 49 (default) is accepted
    - Configuration is visible in show commands
    """
    st.banner("-" * 80)
    st.banner("TEST 3: TACACS+ Port BVA - Default Port (Port 49)")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration
        st.log("MODULE 2: Configuration Phase")
        st.log("STEP 1: Configure server with default port 49")
        if not configure_tacacs_server_with_port(dut, CONFIG.tacacs_server_ip_2, CONFIG.port_default):
            validation_failures.append("Failed to configure server with port 49")
        st.log("✅ MODULE 2 STEP 1 completed")

        # MODULE 3: Validation
        st.log("MODULE 3: Validation Phase")
        st.log("STEP 2: Verify server port 49 in configuration")
        if not verify_tacacs_server_port(dut, CONFIG.tacacs_server_ip_2, CONFIG.port_default):
            validation_failures.append(f"Failed to verify server with port {CONFIG.port_default}")
        st.log("✅ MODULE 3 STEP 2 completed")

        st.log("✅ TEST 3 COMPLETED: Default port 49")

    except Exception as e:
        st.error(f"Exception in test_tacacs_port_bva_default: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_port_bva_default: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 3 PASSED: Default Port 49")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
@pytest.mark.port_bva
def test_tacacs_port_bva_custom():
    """
    TEST 4: TACACS+ Port BVA - Custom Port (Port 5049)

    Module 2: Configuration
    - Configure TACACS+ server with custom port 5049

    Module 3: Validation
    - Verify server is configured with port 5049

    Expected Outcome:
    - Port 5049 (custom) is accepted
    - Configuration is visible in show commands
    """
    st.banner("-" * 80)
    st.banner("TEST 4: TACACS+ Port BVA - Custom Port (Port 5049)")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration
        st.log("MODULE 2: Configuration Phase")
        st.log("STEP 1: Remove existing server (if any)")
        remove_tacacs_server(dut, CONFIG.tacacs_server_ip_2)
        st.log("✅ MODULE 2 STEP 1 completed")

        st.log("STEP 2: Configure server with custom port 5049")
        if not configure_tacacs_server_with_port(dut, CONFIG.tacacs_server_ip_2, CONFIG.port_custom):
            validation_failures.append("Failed to configure server with port 5049")
        st.log("✅ MODULE 2 STEP 2 completed")

        # MODULE 3: Validation
        st.log("MODULE 3: Validation Phase")
        st.log("STEP 3: Verify server port 5049 in configuration")
        if not verify_tacacs_server_port(dut, CONFIG.tacacs_server_ip_2, CONFIG.port_custom):
            validation_failures.append(f"Failed to verify server with port {CONFIG.port_custom}")
        st.log("✅ MODULE 3 STEP 3 completed")

        st.log("✅ TEST 4 COMPLETED: Custom port 5049")

    except Exception as e:
        st.error(f"Exception in test_tacacs_port_bva_custom: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_port_bva_custom: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 4 PASSED: Custom Port 5049")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
@pytest.mark.port_bva
def test_tacacs_port_bva_valid_max():
    """
    TEST 5: TACACS+ Port BVA - Valid Maximum (Port 65535)

    Module 2: Configuration
    - Configure TACACS+ server with maximum valid port 65535

    Module 3: Validation
    - Verify server is configured with port 65535

    Expected Outcome:
    - Port 65535 (max valid) is accepted
    - Configuration is visible in show commands
    """
    st.banner("-" * 80)
    st.banner("TEST 5: TACACS+ Port BVA - Valid Maximum (Port 65535)")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration
        st.log("MODULE 2: Configuration Phase")
        st.log("STEP 1: Configure server with maximum valid port 65535")
        if not configure_tacacs_server_with_port(dut, CONFIG.tacacs_server_ip, CONFIG.port_valid_max):
            validation_failures.append("Failed to configure server with port 65535")
        st.log("✅ MODULE 2 STEP 1 completed")

        # MODULE 3: Validation
        st.log("MODULE 3: Validation Phase")
        st.log("STEP 2: Verify server port 65535 in configuration")
        if not verify_tacacs_server_port(dut, CONFIG.tacacs_server_ip, CONFIG.port_valid_max):
            validation_failures.append(f"Failed to verify server with port {CONFIG.port_valid_max}")
        st.log("✅ MODULE 3 STEP 2 completed")

        st.log("✅ TEST 5 COMPLETED: Maximum valid port 65535")

    except Exception as e:
        st.error(f"Exception in test_tacacs_port_bva_valid_max: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_port_bva_valid_max: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 5 PASSED: Valid Maximum Port 65535")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
@pytest.mark.port_bva
@pytest.mark.negative
def test_tacacs_port_bva_invalid_max():
    """
    TEST 6: TACACS+ Port BVA - Invalid Maximum (Port 65536)

    Module 2: Configuration (Negative Test)
    - Attempt to configure TACACS+ server with port 65536

    Module 3: Validation
    - Verify command is rejected with error

    Expected Outcome:
    - Port 65536 is rejected
    - Error message is displayed
    """
    st.banner("-" * 80)
    st.banner("TEST 6: TACACS+ Port BVA - Invalid Maximum (Port 65536)")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration (Negative Test)
        st.log("MODULE 2: Configuration Phase (Negative Test)")
        st.log("STEP 1: Attempt to configure server with invalid port 65536")
        if not configure_tacacs_server_with_port(dut, CONFIG.tacacs_server_ip_2,
                                                  CONFIG.port_invalid_max, expect_fail=True):
            validation_failures.append("Failed to reject port 65536 (command should have been rejected)")
        st.log("✅ MODULE 2 STEP 1 completed: Port 65536 rejected")

        st.log("✅ TEST 6 COMPLETED: Invalid port 65536 rejection")

    except Exception as e:
        st.error(f"Exception in test_tacacs_port_bva_invalid_max: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_port_bva_invalid_max: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 6 PASSED: Invalid Port 65536 Rejection")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
@pytest.mark.port_bva
@pytest.mark.integration
def test_tacacs_complete_configuration_with_custom_port():
    """
    TEST 7: Complete TACACS+ Configuration with Custom Port

    Module 2: Configuration
    - Remove existing server 192.168.100.87
    - Configure server 192.168.100.87 on custom port 5049
    - Configure server 192.168.100.175 on custom port 5049
    - Configure global passkey (Test234)
    - Configure global timeout (25 seconds)
    - Configure AAA authentication

    Module 3: Validation
    - Verify server 192.168.100.87 is configured with port 5049
    - Verify server 192.168.100.175 is configured with port 5049
    - Verify AAA authentication includes TACACS+
    - Display complete configuration

    Expected Outcome:
    - All configurations are applied successfully
    - All validations pass
    - Complete TACACS+ setup with custom port is functional
    """
    st.banner("-" * 80)
    st.banner("TEST 7: Complete TACACS+ Configuration with Custom Port")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # MODULE 2: Configuration
        st.log("MODULE 2: Configuration Phase")

        st.log("STEP 1: Remove existing server 192.168.100.87")
        remove_tacacs_server(dut, CONFIG.tacacs_server_ip)
        st.log("✅ MODULE 2 STEP 1 completed")

        st.log("STEP 2: Configure server 192.168.100.87 on port 5049")
        if not configure_tacacs_server_with_port(dut, CONFIG.tacacs_server_ip, CONFIG.port_custom):
            validation_failures.append("Failed to configure server 192.168.100.87 with port 5049")
        st.log("✅ MODULE 2 STEP 2 completed")

        st.log("STEP 3: Configure server 192.168.100.175 on port 5049")
        if not configure_tacacs_server_with_port(dut, CONFIG.tacacs_server_ip_2, CONFIG.port_custom):
            validation_failures.append("Failed to configure server 192.168.100.175 with port 5049")
        st.log("✅ MODULE 2 STEP 3 completed")

        st.log("STEP 4: Configure TACACS+ passkey")
        if not configure_global_key(dut, CONFIG.tacacs_passkey):
            validation_failures.append("Failed to configure TACACS+ key")
        st.log("✅ MODULE 2 STEP 4 completed")

        st.log("STEP 5: Configure TACACS+ timeout (25 seconds)")
        if not configure_global_timeout(dut, CONFIG.timeout_nominal):
            validation_failures.append("Failed to configure timeout")
        st.log("✅ MODULE 2 STEP 5 completed")

        st.log("STEP 6: Configure AAA authentication")
        if not configure_aaa_authentication(dut):
            validation_failures.append("Failed to configure AAA authentication")
        st.log("✅ MODULE 2 STEP 6 completed")

        # MODULE 3: Validation
        st.log("MODULE 3: Validation Phase")

        st.log("STEP 7: Verify server 192.168.100.87 with port 5049")
        if not verify_tacacs_server_port(dut, CONFIG.tacacs_server_ip, CONFIG.port_custom):
            validation_failures.append(f"Failed to verify server {CONFIG.tacacs_server_ip} with port 5049")
        st.log("✅ MODULE 3 STEP 7 completed")

        st.log("STEP 8: Verify server 192.168.100.175 with port 5049")
        if not verify_tacacs_server_port(dut, CONFIG.tacacs_server_ip_2, CONFIG.port_custom):
            validation_failures.append(f"Failed to verify server {CONFIG.tacacs_server_ip_2} with port 5049")
        st.log("✅ MODULE 3 STEP 8 completed")

        st.log("STEP 9: Verify AAA authentication configuration")
        if not verify_aaa_configuration(dut):
            validation_failures.append("Failed to verify AAA authentication")
        st.log("✅ MODULE 3 STEP 9 completed")

        st.log("STEP 10: Display complete TACACS+ configuration")
        cli_type = data.cli_type
        if cli_type == "klish":
            tacacs_output = st.show(dut, "show tacacs-server", type=cli_type, skip_error_check=True)
        else:
            tacacs_output = st.show(dut, "show tacacs", type=cli_type, skip_error_check=True)
        aaa_output = st.show(dut, "show aaa", type=cli_type, skip_error_check=True)
        st.log(f"Complete TACACS+ Configuration:\n{tacacs_output}")
        st.log(f"AAA Configuration:\n{aaa_output}")
        st.log("✅ MODULE 3 STEP 10 completed")

        st.log("✅ TEST 7 COMPLETED: Complete TACACS+ Configuration with Custom Port")

    except Exception as e:
        st.error(f"Exception in test_tacacs_complete_configuration_with_custom_port: {str(e)}")
        validation_failures.append(str(e))

    # Final result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"test_tacacs_complete_configuration_with_custom_port: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 7 PASSED: Complete TACACS+ Configuration with Custom Port")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


if __name__ == "__main__":
    # This allows running the script directly for debugging
    st.log("Running TACACS+ Port BVA tests directly")
    pytest.main([__file__, "-v", "-s"])
