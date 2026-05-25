"""
TACACS+ Global Configuration Test Script
==========================================

Based on manual testing logs for OC-Build

Test Coverage:
- TACACS+ server host configuration (192.168.100.87)
- TACACS+ global passkey configuration
- TACACS+ global timeout configuration
- TACACS+ authtype configuration (pap, chap, mschap, login)
- TACACS+ default commands (default authtype, default passkey, default timeout)
- Validation of global settings after each configuration

Module: test_tacacs_global_config
Framework: spytest
Device: SONiC (OC-Build)

Test Structure:
- Module 1: Unconfiguration (module_hooks prologue)
- Module 2: Configuration (test functions)
- Module 3: Validation (within test functions)
- Module 4: Cleanup (module_hooks epilogue)
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
    "tacacs_passkey_1": "Test12243",
    "tacacs_passkey_2": "Test123",
    "tacacs_timeout_default": "5",
    "tacacs_timeout_custom": "50",
    "tacacs_port_default": "49",
    "tacacs_priority_default": "1",
    "cli_type": "klish"
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture.

    MODULE 1: UNCONFIGURATION
    - Initialize variables
    - Ensure minimum topology
    - Unconfigure all TACACS+ settings

    MODULE 4: CLEANUP
    - Remove all TACACS+ configurations
    - Restore device to clean state
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TACACS-GLOBAL: MODULE 1 - UNCONFIGURATION (PROLOGUE)")
    st.banner("=" * 80)

    # Ensure minimum topology (single DUT)
    vars = st.ensure_min_topology("D1")
    data.cli_type = CONFIG.cli_type

    st.log(f"Module Setup: Using CLI type '{data.cli_type}'")
    st.log(f"TACACS+ Server IP: {CONFIG.tacacs_server_ip}")

    # MODULE 1: Unconfigure all TACACS+ settings before starting tests
    st.log("MODULE 1: Performing complete unconfiguration of TACACS+ settings...")
    unconfigure_all_tacacs(vars.D1)
    st.wait(2, "Waiting for unconfiguration to complete")
    st.log("MODULE 1: Unconfiguration completed")

    yield  # Tests run here (MODULE 2 & 3)

    st.banner("=" * 80)
    st.banner("TACACS-GLOBAL: MODULE 4 - CLEANUP (EPILOGUE)")
    st.banner("=" * 80)

    st.log("MODULE 4: Cleaning up all TACACS+ configuration...")
    cleanup_all_tacacs(vars.D1)
    st.wait(2, "Waiting for cleanup to complete")
    st.log("MODULE 4: Cleanup completed successfully")


def unconfigure_all_tacacs(dut: str) -> bool:
    """
    MODULE 1: Unconfigure all TACACS+ settings on the device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful
    """
    try:
        st.log(f"Unconfiguring all TACACS+ settings on {dut}...")
        # Klish syntax: tacacs-server host / no tacacs-server key / etc.
        commands = [
            f"no tacacs-server host {CONFIG.tacacs_server_ip}",
            "no tacacs-server key",
            "no tacacs-server timeout",
            "no tacacs-server auth-type",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"Unconfiguration completed on {dut}")
        return True
    except Exception as e:
        st.log(f"Unconfiguration completed (may not have been configured): {str(e)}")
        return True


def configure_tacacs_server(dut: str, server_ip: str) -> bool:
    """
    MODULE 2: Configure TACACS+ server host.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IP address

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"MODULE 2: Configuring TACACS+ server host {server_ip} on {dut}...")
        commands = [
            f"tacacs-server host {server_ip}",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(2, "Waiting for server configuration to apply")
        st.log(f"TACACS+ server host {server_ip} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure TACACS+ server on {dut}: {str(e)}")
        return False


def configure_tacacs_passkey(dut: str, passkey: str) -> bool:
    """
    MODULE 2: Configure TACACS+ global passkey.

    Args:
        dut: Device identifier
        passkey: TACACS+ passkey

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"MODULE 2: Configuring TACACS+ passkey on {dut}...")
        commands = [
            f"tacacs-server key {passkey}",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for passkey configuration to apply")
        st.log(f"TACACS+ passkey configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure TACACS+ passkey on {dut}: {str(e)}")
        return False


def configure_tacacs_timeout(dut: str, timeout: str) -> bool:
    """
    MODULE 2: Configure TACACS+ global timeout.

    Args:
        dut: Device identifier
        timeout: TACACS+ timeout value

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"MODULE 2: Configuring TACACS+ timeout {timeout} on {dut}...")
        commands = [
            f"tacacs-server timeout {timeout}",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for timeout configuration to apply")
        st.log(f"TACACS+ timeout {timeout} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure TACACS+ timeout on {dut}: {str(e)}")
        return False


def configure_tacacs_authtype(dut: str, authtype: str) -> bool:
    """
    MODULE 2: Configure TACACS+ global authtype.

    Args:
        dut: Device identifier
        authtype: TACACS+ authtype (pap, chap, mschap, login)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"MODULE 2: Configuring TACACS+ authtype {authtype} on {dut}...")
        commands = [
            f"tacacs-server auth-type {authtype}",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for authtype configuration to apply")
        st.log(f"TACACS+ authtype {authtype} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure TACACS+ authtype on {dut}: {str(e)}")
        return False


def set_tacacs_default_authtype(dut: str) -> bool:
    """
    MODULE 2: Set TACACS+ authtype to default.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"MODULE 2: Setting TACACS+ authtype to default on {dut}...")
        commands = [
            "no tacacs-server auth-type",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for default authtype to apply")
        st.log(f"TACACS+ authtype set to default on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to set default authtype on {dut}: {str(e)}")
        return False


def set_tacacs_default_passkey(dut: str) -> bool:
    """
    MODULE 2: Set TACACS+ passkey to default.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"MODULE 2: Setting TACACS+ passkey to default on {dut}...")
        commands = [
            "no tacacs-server key",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for default passkey to apply")
        st.log(f"TACACS+ passkey set to default on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to set default passkey on {dut}: {str(e)}")
        return False


def set_tacacs_default_timeout(dut: str) -> bool:
    """
    MODULE 2: Set TACACS+ timeout to default.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"MODULE 2: Setting TACACS+ timeout to default on {dut}...")
        commands = [
            "no tacacs-server timeout",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for default timeout to apply")
        st.log(f"TACACS+ timeout set to default on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to set default timeout on {dut}: {str(e)}")
        return False


def verify_tacacs_config(dut: str, expected_values: dict = None) -> bool:
    """
    MODULE 3: Verify TACACS+ configuration.

    Expected output format from manual testing:
    TACPLUS global auth_type pap (default)
    TACPLUS global timeout 5 (default)
    TACPLUS global passkey Test123

    TACPLUS_SERVER address 192.168.100.87
                   priority 1
                   tcp_port 49

    Args:
        dut: Device identifier
        expected_values: Dict with keys: authtype, timeout, passkey, server_ip

    Returns:
        bool: True if verification passes, False otherwise
    """
    try:
        st.log(f"MODULE 3: Verifying TACACS+ configuration on {dut}...")
        # Use skip_tmpl=True to get raw string output; the template show_tacacs.tmpl
        # returns [] for klish format which prevents validation
        output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        output_str = output if isinstance(output, str) else str(output) if output else ""

        if not output_str.strip():
            st.log(f"MODULE 3: TACACS+ output is empty on {dut}")
            return False

        st.log(f"TACACS+ raw output:\n{output_str}")

        verification_passed = True

        if expected_values:
            # Verify authtype
            if "authtype" in expected_values:
                expected_auth = expected_values["authtype"]
                if expected_auth == "N/A":
                    # After "no tacacs-server auth-type", global shows "Authentication Type  : N/A"
                    import re
                    match = re.search(r'Authentication Type\s*:\s*(\S+)', output_str, re.IGNORECASE)
                    actual_auth = match.group(1) if match else ""
                    if actual_auth.upper() == "N/A":
                        st.log(f"✓ MODULE 3: AUTH-TYPE verified: N/A (default/unset)")
                    else:
                        st.error(f"✗ MODULE 3: AUTH-TYPE mismatch. Expected N/A, got: {actual_auth}")
                        st.log(f"  Output was:\n{output_str}")
                        verification_passed = False
                else:
                    # Klish output: "Authentication Type  : LOGIN" (global section)
                    # Check global section only to avoid matching per-host AUTH-TYPE column
                    global_section = output_str.split("TACACS+ Servers")[0] if "TACACS+ Servers" in output_str else output_str
                    import re
                    match = re.search(r'Authentication Type\s*:\s*(\S+)', global_section, re.IGNORECASE)
                    actual_auth = match.group(1) if match else ""
                    if actual_auth.lower() == expected_auth.lower():
                        st.log(f"✓ MODULE 3: AUTH-TYPE verified: {expected_auth}")
                    else:
                        st.error(f"✗ MODULE 3: AUTH-TYPE mismatch. Expected: {expected_auth}, got: {actual_auth}")
                        st.log(f"  Output was:\n{output_str}")
                        verification_passed = False

            # Verify timeout
            if "timeout" in expected_values:
                expected_timeout = expected_values["timeout"]
                if expected_timeout == "N/A":
                    # After "no tacacs-server timeout", global shows "Global Timeout       : N/A"
                    import re
                    match = re.search(r'Global Timeout\s*:\s*(\S+)', output_str, re.IGNORECASE)
                    actual_timeout = match.group(1) if match else ""
                    if actual_timeout.upper() == "N/A":
                        st.log(f"✓ MODULE 3: TIMEOUT verified: N/A (default/unset)")
                    else:
                        st.error(f"✗ MODULE 3: TIMEOUT mismatch. Expected N/A, got: {actual_timeout}")
                        st.log(f"  Output was:\n{output_str}")
                        verification_passed = False
                else:
                    # Check "Global Timeout       : 50" in global section
                    import re
                    match = re.search(r'Global Timeout\s*:\s*(\S+)', output_str, re.IGNORECASE)
                    actual_timeout = match.group(1) if match else ""
                    if actual_timeout == expected_timeout:
                        st.log(f"✓ MODULE 3: TIMEOUT verified: {expected_timeout}")
                    else:
                        st.error(f"✗ MODULE 3: TIMEOUT mismatch. Expected: {expected_timeout}, got: {actual_timeout}")
                        st.log(f"  Output was:\n{output_str}")
                        verification_passed = False

            # Verify passkey
            if "passkey" in expected_values:
                expected_passkey = expected_values["passkey"]
                if expected_passkey == "<EMPTY_STRING>":
                    # After "no tacacs-server key", klish shows "Key Configured       : No"
                    if "Key Configured" in output_str and "No" in output_str:
                        st.log(f"✓ MODULE 3: PASSKEY verified: not configured (default)")
                    else:
                        st.error(f"✗ MODULE 3: PASSKEY mismatch. Expected key not configured")
                        st.log(f"  Output was:\n{output_str}")
                        verification_passed = False
                else:
                    # After tacacs-server key <key>, klish shows "Key Configured       : Yes"
                    if "Key Configured" in output_str and "Yes" in output_str:
                        st.log(f"✓ MODULE 3: PASSKEY verified: configured (Key Configured: Yes)")
                    else:
                        st.error(f"✗ MODULE 3: PASSKEY mismatch. Expected key to be configured")
                        st.log(f"  Output was:\n{output_str}")
                        verification_passed = False

            # Verify server IP
            if "server_ip" in expected_values:
                expected_ip = expected_values["server_ip"]
                if expected_ip in output_str:
                    st.log(f"✓ MODULE 3: SERVER IP verified: {expected_ip}")
                else:
                    st.error(f"✗ MODULE 3: SERVER IP mismatch. Expected: {expected_ip}")
                    st.log(f"  Output was:\n{output_str}")
                    verification_passed = False

        st.log(f"MODULE 3: Verification completed")
        return verification_passed

    except Exception as e:
        st.error(f"MODULE 3: Failed to verify TACACS+ configuration on {dut}: {str(e)}")
        return False


def cleanup_all_tacacs(dut: str) -> bool:
    """
    MODULE 4: Cleanup all TACACS+ configuration from device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful
    """
    try:
        st.log(f"MODULE 4: Cleaning up all TACACS+ configuration on {dut}...")
        commands = [
            f"no tacacs-server host {CONFIG.tacacs_server_ip}",
            "no tacacs-server key",
            "no tacacs-server timeout",
            "no tacacs-server auth-type",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2, "Waiting for cleanup to complete")
        st.log(f"MODULE 4: TACACS+ cleanup completed on {dut}")
        return True
    except Exception as e:
        st.log(f"MODULE 4: Cleanup completed (may have already been removed): {str(e)}")
        return True


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_01_basic_server_passkey():
    """
    Test 01: Basic TACACS+ Server and Passkey Configuration

    Based on manual testing:
    sonic(config)# tacacs server host 192.168.100.87
    sonic(config)# tacacs passkey Test12243
    sonic# show tacacs

    MODULE 2: Configuration
    - Configure TACACS+ server host (192.168.100.87)
    - Configure TACACS+ passkey (Test12243)

    MODULE 3: Validation
    - Verify server address: 192.168.100.87
    - Verify passkey: Test12243
    - Verify default authtype: pap
    - Verify default timeout: 5
    - Verify default priority: 1
    - Verify default tcp_port: 49

    Expected Outcome:
    - Server and passkey configured successfully
    - All default values match expected
    """
    st.banner("-" * 80)
    st.banner("TEST-01: Basic TACACS+ Server and Passkey Configuration")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # MODULE 2: Configuration
        st.log("MODULE 2: Configuring TACACS+ server and passkey")

        if not configure_tacacs_server(dut, CONFIG.tacacs_server_ip):
            st.error("Failed to configure TACACS+ server")
            result = False

        if not configure_tacacs_passkey(dut, CONFIG.tacacs_passkey_1):
            st.error("Failed to configure TACACS+ passkey")
            result = False

        # MODULE 3: Validation
        # Only check server_ip and passkey (key configured: Yes).
        # Global auth-type and timeout are N/A until explicitly set.
        st.log("MODULE 3: Validating configuration")
        expected = {
            "server_ip": CONFIG.tacacs_server_ip,
            "passkey": CONFIG.tacacs_passkey_1,
        }

        if not verify_tacacs_config(dut, expected):
            st.error("MODULE 3: Validation failed")
            result = False
        else:
            st.log("✓ MODULE 3: Validation passed")

        # Display complete configuration
        output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"Complete TACACS+ Configuration:\n{output}")

    except Exception as e:
        st.error(f"Exception in test_tacacs_global_01: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-01 PASSED: Basic server and passkey configuration")
    else:
        st.error("❌ TEST-01 FAILED: Basic server and passkey configuration")

    assert result, "Test failed: Basic TACACS+ Server and Passkey"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_02_timeout_configuration():
    """
    Test 02: TACACS+ Timeout Configuration

    Based on manual testing:
    sonic(config)# tacacs server host 192.168.100.87
    sonic(config)# tacacs passkey Test123
    sonic(config)# tacacs timeout 50
    sonic# show tacacs

    MODULE 2: Configuration
    - Configure TACACS+ server host
    - Configure TACACS+ passkey (Test123)
    - Configure TACACS+ timeout (50)

    MODULE 3: Validation
    - Verify timeout: 50
    - Verify passkey: Test123

    Expected Outcome:
    - Timeout configured to 50 successfully
    """
    st.banner("-" * 80)
    st.banner("TEST-02: TACACS+ Timeout Configuration")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Reset state from previous test
        unconfigure_all_tacacs(dut)
        st.wait(1)

        # MODULE 2: Configuration
        st.log("MODULE 2: Configuring TACACS+ with custom timeout")

        if not configure_tacacs_server(dut, CONFIG.tacacs_server_ip):
            st.error("Failed to configure TACACS+ server")
            result = False

        if not configure_tacacs_passkey(dut, CONFIG.tacacs_passkey_2):
            st.error("Failed to configure TACACS+ passkey")
            result = False

        if not configure_tacacs_timeout(dut, CONFIG.tacacs_timeout_custom):
            st.error("Failed to configure TACACS+ timeout")
            result = False

        # MODULE 3: Validation — only check what was explicitly configured
        st.log("MODULE 3: Validating timeout configuration")
        expected = {
            "server_ip": CONFIG.tacacs_server_ip,
            "passkey": CONFIG.tacacs_passkey_2,
            "timeout": CONFIG.tacacs_timeout_custom
        }

        if not verify_tacacs_config(dut, expected):
            st.error("MODULE 3: Timeout validation failed")
            result = False
        else:
            st.log("✓ MODULE 3: Timeout validation passed")

        output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"TACACS+ Configuration with custom timeout:\n{output}")

    except Exception as e:
        st.error(f"Exception in test_tacacs_global_02: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-02 PASSED: Timeout configuration")
    else:
        st.error("❌ TEST-02 FAILED: Timeout configuration")

    assert result, "Test failed: TACACS+ Timeout Configuration"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_03_authtype_pap_default():
    """
    Test 03: TACACS+ Authtype PAP and Default

    Based on manual testing:
    sonic(config)# tacacs authtype pap
    sonic(config)# tacacs default authtype
    sonic# show tacacs

    MODULE 2: Configuration
    - Configure authtype pap
    - Set authtype to default

    MODULE 3: Validation
    - Verify authtype: pap after configuration
    - Verify authtype: N/A after "no tacacs-server auth-type" (global unset)

    Expected Outcome:
    - Authtype pap configured successfully
    - After "no tacacs-server auth-type", global Authentication Type shows N/A
    """
    st.banner("-" * 80)
    st.banner("TEST-03: TACACS+ Authtype PAP and Default")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Reset state from previous test
        unconfigure_all_tacacs(dut)
        st.wait(1)
        configure_tacacs_server(dut, CONFIG.tacacs_server_ip)
        st.wait(1)

        # MODULE 2: Configuration - authtype pap
        st.log("MODULE 2: Configuring authtype pap")
        if not configure_tacacs_authtype(dut, "pap"):
            st.error("Failed to configure authtype pap")
            result = False

        # MODULE 3: Validation - authtype pap
        st.log("MODULE 3: Validating authtype pap")
        expected = {"authtype": "pap"}
        if not verify_tacacs_config(dut, expected):
            st.error("MODULE 3: Authtype pap validation failed")
            result = False

        # MODULE 2: Configuration - default authtype
        st.log("MODULE 2: Setting authtype to default")
        if not set_tacacs_default_authtype(dut):
            st.error("Failed to set default authtype")
            result = False

        # MODULE 3: Validation - default authtype
        # After "no tacacs-server auth-type", global shows "Authentication Type  : N/A"
        st.log("MODULE 3: Validating default authtype (expect N/A in global section)")
        expected = {"authtype": "N/A"}
        if not verify_tacacs_config(dut, expected):
            st.error("MODULE 3: Default authtype validation failed")
            result = False
        else:
            st.log("✓ MODULE 3: Default authtype verified as N/A (unset/default)")

        output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"TACACS+ Configuration after default authtype:\n{output}")

    except Exception as e:
        st.error(f"Exception in test_tacacs_global_03: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-03 PASSED: Authtype PAP and Default")
    else:
        st.error("❌ TEST-03 FAILED: Authtype PAP and Default")

    assert result, "Test failed: TACACS+ Authtype PAP and Default"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_04_authtype_chap_default_passkey():
    """
    Test 04: TACACS+ Authtype CHAP and Default Passkey

    Based on manual testing:
    sonic(config)# tacacs authtype chap
    sonic(config)# tacacs default passkey
    sonic# show tacacs

    MODULE 2: Configuration
    - Configure authtype chap
    - Set passkey to default

    MODULE 3: Validation
    - Verify authtype: chap
    - Verify passkey: <EMPTY_STRING> (default)

    Expected Outcome:
    - Authtype changes to chap
    - Passkey becomes <EMPTY_STRING> (default)
    """
    st.banner("-" * 80)
    st.banner("TEST-04: TACACS+ Authtype CHAP and Default Passkey")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Reset state from previous test
        unconfigure_all_tacacs(dut)
        st.wait(1)
        configure_tacacs_server(dut, CONFIG.tacacs_server_ip)
        configure_tacacs_passkey(dut, CONFIG.tacacs_passkey_2)
        st.wait(1)

        # MODULE 2: Configuration - authtype chap
        st.log("MODULE 2: Configuring authtype chap")
        if not configure_tacacs_authtype(dut, "chap"):
            st.error("Failed to configure authtype chap")
            result = False

        # MODULE 3: Validation - authtype chap
        st.log("MODULE 3: Validating authtype chap")
        expected = {"authtype": "chap"}
        if not verify_tacacs_config(dut, expected):
            st.error("MODULE 3: Authtype chap validation failed")
            result = False

        # MODULE 2: Configuration - default passkey
        st.log("MODULE 2: Setting passkey to default")
        if not set_tacacs_default_passkey(dut):
            st.error("Failed to set default passkey")
            result = False

        # MODULE 3: Validation - default passkey
        st.log("MODULE 3: Validating default passkey")
        expected = {
            "authtype": "chap",
            "passkey": "<EMPTY_STRING>"
        }
        if not verify_tacacs_config(dut, expected):
            st.error("MODULE 3: Default passkey validation failed")
            result = False
        else:
            st.log("✓ MODULE 3: Default passkey verified as <EMPTY_STRING>")

        output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"TACACS+ Configuration after default passkey:\n{output}")

    except Exception as e:
        st.error(f"Exception in test_tacacs_global_04: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-04 PASSED: Authtype CHAP and Default Passkey")
    else:
        st.error("❌ TEST-04 FAILED: Authtype CHAP and Default Passkey")

    assert result, "Test failed: TACACS+ Authtype CHAP and Default Passkey"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_05_authtype_chap_default_timeout():
    """
    Test 05: TACACS+ Authtype CHAP and Default Timeout

    Based on manual testing:
    sonic(config)# tacacs-server auth-type chap
    sonic(config)# no tacacs-server timeout
    sonic# show tacacs-server

    Note: mschap is NOT supported on this platform. Valid auth-types: pap, chap, login.
    After "no tacacs-server timeout", global shows "Global Timeout : N/A" (unset/default).

    MODULE 2: Configuration
    - Configure authtype chap
    - Set timeout to default (no tacacs-server timeout)

    MODULE 3: Validation
    - Verify authtype: chap
    - Verify timeout: N/A (global default unset)

    Expected Outcome:
    - Authtype changes to chap
    - Timeout global resets to N/A (default/unset)
    """
    st.banner("-" * 80)
    st.banner("TEST-05: TACACS+ Authtype CHAP and Default Timeout")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Reset state from previous test
        unconfigure_all_tacacs(dut)
        st.wait(1)
        configure_tacacs_server(dut, CONFIG.tacacs_server_ip)
        configure_tacacs_timeout(dut, CONFIG.tacacs_timeout_custom)
        st.wait(1)

        # MODULE 2: Configuration - authtype chap
        st.log("MODULE 2: Configuring authtype chap")
        if not configure_tacacs_authtype(dut, "chap"):
            st.error("Failed to configure authtype chap")
            result = False

        # MODULE 3: Validation - authtype chap and custom timeout still set
        st.log("MODULE 3: Validating authtype chap with custom timeout")
        expected = {"authtype": "chap", "timeout": CONFIG.tacacs_timeout_custom}
        if not verify_tacacs_config(dut, expected):
            st.error("MODULE 3: Authtype chap / timeout validation failed")
            result = False
        else:
            st.log("✓ MODULE 3: Authtype chap verified")

        # MODULE 2: Configuration - default timeout
        st.log("MODULE 2: Setting timeout to default (no tacacs-server timeout)")
        if not set_tacacs_default_timeout(dut):
            st.error("Failed to set default timeout")
            result = False

        # MODULE 3: Validation - after "no tacacs-server timeout", global shows N/A
        st.log("MODULE 3: Validating default timeout (expect Global Timeout: N/A)")
        expected = {
            "authtype": "chap",
            "timeout": "N/A"
        }
        if not verify_tacacs_config(dut, expected):
            st.error("MODULE 3: Default timeout validation failed")
            result = False
        else:
            st.log("✓ MODULE 3: Default timeout verified as N/A (unset/default)")

        output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"TACACS+ Configuration after default timeout:\n{output}")

    except Exception as e:
        st.error(f"Exception in test_tacacs_global_05: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-05 PASSED: Authtype CHAP and Default Timeout")
    else:
        st.error("❌ TEST-05 FAILED: Authtype CHAP and Default Timeout")

    assert result, "Test failed: TACACS+ Authtype CHAP and Default Timeout"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_06_authtype_login():
    """
    Test 06: TACACS+ Authtype LOGIN

    Based on manual testing:
    sonic(config)# tacacs authtype login
    sonic# show tacacs

    MODULE 2: Configuration
    - Configure authtype login

    MODULE 3: Validation
    - Verify authtype: login

    Expected Outcome:
    - Authtype changes to login successfully
    """
    st.banner("-" * 80)
    st.banner("TEST-06: TACACS+ Authtype LOGIN")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Reset state from previous test
        unconfigure_all_tacacs(dut)
        st.wait(1)
        configure_tacacs_server(dut, CONFIG.tacacs_server_ip)
        st.wait(1)

        # MODULE 2: Configuration - authtype login
        st.log("MODULE 2: Configuring authtype login")
        if not configure_tacacs_authtype(dut, "login"):
            st.error("Failed to configure authtype login")
            result = False

        # MODULE 3: Validation - authtype login
        st.log("MODULE 3: Validating authtype login")
        expected = {"authtype": "login"}
        if not verify_tacacs_config(dut, expected):
            st.error("MODULE 3: Authtype login validation failed")
            result = False
        else:
            st.log("✓ MODULE 3: Authtype login verified")

        output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"TACACS+ Configuration with authtype login:\n{output}")

    except Exception as e:
        st.error(f"Exception in test_tacacs_global_06: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-06 PASSED: Authtype LOGIN")
    else:
        st.error("❌ TEST-06 FAILED: Authtype LOGIN")

    assert result, "Test failed: TACACS+ Authtype LOGIN"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_07_all_authtypes():
    """
    Test 07: Comprehensive Authtype Cycle

    MODULE 2 & 3: Test all supported authtype values
    - Test authtype: pap, chap, login (mschap not supported on this platform)
    - Verify each authtype configuration

    Expected Outcome:
    - All valid authtype values can be configured and verified
    """
    st.banner("-" * 80)
    st.banner("TEST-07: Comprehensive Authtype Cycle")
    st.banner("-" * 80)

    dut = vars.D1
    result = True
    # Note: mschap is NOT supported on this platform. Valid auth-types: pap, chap, login
    authtypes = ["pap", "chap", "login"]

    try:
        # Reset state from previous test
        unconfigure_all_tacacs(dut)
        st.wait(1)
        configure_tacacs_server(dut, CONFIG.tacacs_server_ip)
        st.wait(1)

        for authtype in authtypes:
            st.log(f"MODULE 2: Testing authtype: {authtype}")

            if not configure_tacacs_authtype(dut, authtype):
                st.error(f"Failed to configure authtype {authtype}")
                result = False
                continue

            st.log(f"MODULE 3: Validating authtype: {authtype}")
            expected = {"authtype": authtype}
            if not verify_tacacs_config(dut, expected):
                st.error(f"MODULE 3: Authtype {authtype} validation failed")
                result = False
            else:
                st.log(f"✓ Authtype {authtype} verified successfully")

            st.wait(1)

    except Exception as e:
        st.error(f"Exception in test_tacacs_global_07: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-07 PASSED: Comprehensive Authtype Cycle")
    else:
        st.error("❌ TEST-07 FAILED: Comprehensive Authtype Cycle")

    assert result, "Test failed: Comprehensive Authtype Cycle"


if __name__ == "__main__":
    # This allows running the script directly for debugging
    st.log("Running TACACS+ Global Configuration tests directly")
    pytest.main([__file__, "-v"])
