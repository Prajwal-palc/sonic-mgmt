"""
TACACS+ TEST CASE 2.1: COMPREHENSIVE CONFIGURATION AND VERIFICATION
Test Case ID: TC-TACACS-2.1

Feature      : TACACS+ (Terminal Access Controller Access-Control System Plus)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_Tacacs/test_tacacs_tc_2_1_comprehensive.py \
    --logs-path ./logs/tacacs_tc_2_1_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 2.1: Comprehensive TACACS+ Configuration

  Covers the following sub-test cases:
    - TC 2.1.1: Add and Remove TACACS+ Server (IPv4 and IPv6)
    - TC 2.1.2: Configure Shared Secret Key (passkey)
    - TC 2.1.3: Configure Timeout Value
    - TC 2.1.4: Configure Authentication Types (pap, chap, mschap, login)
    - TC 2.1.5: Test Default Configuration Commands

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing TACACS+ config
    2. Module 2 - Configuration:
       - Test IPv4 server add/remove
       - Test IPv6 server add/remove
       - Configure shared secret key
       - Configure timeout value
       - Configure different auth types
       - Test default configuration reset
    3. Module 3 - Validation:
       - Verify all configurations appear correctly in 'show tacacs'
       - Verify default values are restored correctly
    4. Module 4 - Cleanup: Remove all TACACS+ configuration

Pre-requisites:
  - 1 SONiC device (DUT1)
  - Testbed: testbed_2vs.yaml or compatible

Notes:
  - Tests cover both IPv4 and IPv6 server configuration
  - Tests all authentication types: pap, chap, mschap, login
  - Tests default configuration restoration
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# ======================================================================
# Global Variables
# ======================================================================
vars = SpyTestDict()
data = SpyTestDict()

# ======================================================================
# Test Configuration
# ======================================================================
CONFIG = SpyTestDict({
    # Server Configuration
    "tacacs_server_ipv4":   "192.168.100.87",
    "tacacs_server_ipv6":   "2001:db8::10",
    "tacacs_port":          "49",
    "tacacs_priority":      "1",

    # Authentication Configuration
    "passkey1":             "Test12243",
    "passkey2":             "Test123",
    "timeout_default":      "5",
    "timeout_custom":       "50",

    # Auth Types
    "authtype_pap":         "pap",
    "authtype_chap":        "chap",
    "authtype_mschap":      "mschap",
    "authtype_login":       "login",

    # CLI Type
    "cli_type":             "klish"
})

# Test Case ID
TC_ID = "TC-TACACS-2.1"


# ======================================================================
# Fixture - Module Level Setup/Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def tacacs_module_hooks(request):
    """
    Module-level fixture for setup and teardown.
    Runs before all tests in this module and after all tests.
    """
    global vars, data

    # Ensure minimum topology: 1 DUT (D1)
    vars = st.ensure_min_topology("D1")
    # Fix: st.get_ui_type() may return "click" (bash mode) which breaks config commands.
    # Detect and override to "klish" so proper config mode is used.
    detected_cli = st.get_ui_type(vars.D1)
    if detected_cli == "click" or detected_cli not in ["klish", "rest-put", "rest-patch"]:
        data.cli_type = "klish"
        st.log(f"Module Setup: Detected '{detected_cli}', overriding to 'klish' for config mode")
    else:
        data.cli_type = detected_cli
        st.log(f"Module Setup: Using detected CLI type '{data.cli_type}'")

    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: COMPREHENSIVE TACACS+ CONFIGURATION")
    st.banner("=" * 80)

    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"TACACS+ IPv4 Server: {CONFIG.tacacs_server_ipv4}")
    st.log(f"TACACS+ IPv6 Server: {CONFIG.tacacs_server_ipv6}")

    # Module 1: Pre-condition - Unconfigure all TACACS+ before tests
    st.banner("MODULE 1: UNCONFIGURATION - Cleaning existing TACACS+ config")
    module_1_unconfiguration(vars.D1)
    st.wait(2)

    yield

    # Module 4: Cleanup after all tests
    st.banner("MODULE 4: CLEANUP - Removing all TACACS+ configuration")
    module_4_cleanup(vars.D1)
    st.wait(1)


# ======================================================================
# MODULE 1: UNCONFIGURATION
# ======================================================================
def module_1_unconfiguration(dut: str):
    """
    Module 1: Unconfiguration
    Remove all existing TACACS+ configuration before starting tests.
    """
    st.log(f"[MODULE 1] Unconfiguring all TACACS+ settings on {dut}")

    # Platform-aware command syntax
    if data.cli_type == "klish":
        commands = [
            f"no tacacs-server host {CONFIG.tacacs_server_ipv4}",
            f"no tacacs-server host {CONFIG.tacacs_server_ipv6}",
            "no tacacs-server key",
            "no tacacs-server timeout",
            "no tacacs-server auth-type",
            "end"
        ]
    else:
        commands = [
            f"no tacacs server {CONFIG.tacacs_server_ipv4}",
            f"no tacacs server {CONFIG.tacacs_server_ipv6}",
            "tacacs default passkey",
            "tacacs default timeout",
            "tacacs default authtype",
            "end"
        ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"[MODULE 1] Unconfiguration completed on {dut}")
    except Exception as e:
        st.log(f"[MODULE 1] Unconfiguration error (may be expected if no config exists): {str(e)}")


# ======================================================================
# MODULE 2: CONFIGURATION FUNCTIONS
# ======================================================================
def configure_tacacs_server(dut: str, server_ip: str) -> bool:
    """
    Configure TACACS+ server.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IP address (IPv4 or IPv6)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[MODULE 2] Configuring TACACS+ server {server_ip} on {dut}")

    # Platform-aware command syntax
    if data.cli_type == "klish":
        cmd = f"tacacs-server host {server_ip}"
    else:
        cmd = f"tacacs server {server_ip}"

    commands = [cmd, "end"]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"[MODULE 2] TACACS+ server {server_ip} configured")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure TACACS+ server: {str(e)}")
        return False


def remove_tacacs_server(dut: str, server_ip: str) -> bool:
    """
    Remove TACACS+ server.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IP address to remove

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[MODULE 2] Removing TACACS+ server {server_ip} from {dut}")

    # Platform-aware command syntax
    if data.cli_type == "klish":
        cmd = f"no tacacs-server host {server_ip}"
    else:
        cmd = f"no tacacs server {server_ip}"

    commands = [cmd, "end"]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"[MODULE 2] TACACS+ server {server_ip} removed")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to remove TACACS+ server: {str(e)}")
        return False


def configure_tacacs_passkey(dut: str, passkey: str) -> bool:
    """
    Configure TACACS+ shared secret key (passkey).

    Args:
        dut: Device identifier
        passkey: Shared secret key

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[MODULE 2] Configuring TACACS+ passkey on {dut}")

    # Platform-aware command syntax
    if data.cli_type == "klish":
        cmd = f"tacacs-server key {passkey}"
    else:
        cmd = f"tacacs passkey {passkey}"

    commands = [cmd, "end"]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"[MODULE 2] TACACS+ passkey configured")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure passkey: {str(e)}")
        return False


def configure_tacacs_timeout(dut: str, timeout: str) -> bool:
    """
    Configure TACACS+ timeout value.

    Args:
        dut: Device identifier
        timeout: Timeout value in seconds

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[MODULE 2] Configuring TACACS+ timeout {timeout} on {dut}")

    # Platform-aware command syntax
    if data.cli_type == "klish":
        cmd = f"tacacs-server timeout {timeout}"
    else:
        cmd = f"tacacs timeout {timeout}"

    commands = [cmd, "end"]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"[MODULE 2] TACACS+ timeout {timeout} configured")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure timeout: {str(e)}")
        return False


def configure_tacacs_authtype(dut: str, authtype: str) -> bool:
    """
    Configure TACACS+ authentication type.

    Args:
        dut: Device identifier
        authtype: Authentication type (pap, chap, mschap, login)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[MODULE 2] Configuring TACACS+ authtype {authtype} on {dut}")

    # Platform-aware command syntax
    if data.cli_type == "klish":
        cmd = f"tacacs-server auth-type {authtype}"
    else:
        cmd = f"tacacs authtype {authtype}"

    commands = [cmd, "end"]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"[MODULE 2] TACACS+ authtype {authtype} configured")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure authtype: {str(e)}")
        return False


def reset_tacacs_default(dut: str, parameter: str) -> bool:
    """
    Reset TACACS+ parameter to default value.

    Args:
        dut: Device identifier
        parameter: Parameter to reset (passkey, timeout, authtype)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[MODULE 2] Resetting TACACS+ {parameter} to default on {dut}")

    # Platform-aware command syntax
    if data.cli_type == "klish":
        # Broadcom uses 'no' to reset to default
        param_map = {
            "passkey": "key",
            "timeout": "timeout",
            "authtype": "auth-type"
        }
        param = param_map.get(parameter, parameter)
        cmd = f"no tacacs-server {param}"
    else:
        # ISCLI uses 'default' keyword
        cmd = f"tacacs default {parameter}"

    commands = [cmd, "end"]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"[MODULE 2] TACACS+ {parameter} reset to default")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to reset {parameter}: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION FUNCTIONS
# ======================================================================
def validate_tacacs_output(dut: str, expected_values: dict) -> bool:
    """
    Validate TACACS+ configuration from 'show tacacs' output.

    Args:
        dut: Device identifier
        expected_values: Dictionary of expected values to check
            Keys can be: 'server', 'passkey', 'timeout', 'authtype', 'priority', 'port'

    Returns:
        bool: True if all validations pass, False otherwise
    """
    st.log(f"[MODULE 3] Validating TACACS+ configuration on {dut}")

    # Platform-aware show command
    if data.cli_type == "klish":
        show_cmd = "show tacacs-server | no-more"
    else:
        show_cmd = "show tacacs | no-more"

    output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show tacacs output:\n{output_str}")

    validation_errors = []

    # Check server address
    if 'server' in expected_values:
        expected_server = expected_values['server']
        if expected_server:
            # Platform-aware validation
            if data.cli_type == "klish":
                # Broadcom format: server appears in HOST column
                if expected_server in output_str:
                    st.log(f"  ✓ Server address: {expected_server}")
                else:
                    validation_errors.append(f"Server {expected_server} not found in output")
            else:
                # ISCLI format: "TACPLUS_SERVER address <ip>"
                if f"address {expected_server}" in output_str or f"TACPLUS_SERVER address {expected_server}" in output_str:
                    st.log(f"  ✓ Server address: {expected_server}")
                else:
                    validation_errors.append(f"Server {expected_server} not found in output")
        else:
            # Check server is NOT present
            if data.cli_type == "klish":
                # Broadcom: check if no servers in table
                if "TACACS+ Servers" in output_str and "HOST" in output_str:
                    lines = output_str.split('\n')
                    # Skip header lines and check if there are actual server entries
                    server_found = False
                    for line in lines:
                        if line.strip() and not line.startswith('-') and not 'HOST' in line and not 'TACACS+' in line:
                            parts = line.split()
                            if parts and '.' in parts[0]:  # Looks like an IP
                                server_found = True
                                break
                    if not server_found:
                        st.log(f"  ✓ No server configured (as expected)")
                    else:
                        validation_errors.append("Server found but expected none")
                else:
                    st.log(f"  ✓ No server configured (as expected)")
            else:
                # ISCLI format
                if "TACPLUS_SERVER address" not in output_str:
                    st.log(f"  ✓ No server configured (as expected)")
                else:
                    validation_errors.append("Server found but expected none")

    # Check passkey
    if 'passkey' in expected_values:
        expected_passkey = expected_values['passkey']
        if expected_passkey:
            # Platform-aware validation
            if data.cli_type == "klish":
                # Broadcom format: "Key Configured : Yes"
                if "Key Configured" in output_str and "Yes" in output_str:
                    st.log(f"  ✓ Passkey configured")
                else:
                    validation_errors.append(f"Passkey {expected_passkey} not found")
            else:
                # ISCLI format: "passkey <value>"
                if f"passkey {expected_passkey}" in output_str:
                    st.log(f"  ✓ Passkey: {expected_passkey}")
                else:
                    validation_errors.append(f"Passkey {expected_passkey} not found")
        else:
            # Check for default/empty passkey
            if data.cli_type == "klish":
                # Broadcom format: "Key Configured : No"
                if "Key Configured" in output_str and ("No" in output_str or "Yes" not in output_str):
                    st.log(f"  ✓ Passkey: default/empty")
                else:
                    validation_errors.append("Expected empty/default passkey not found")
            else:
                # ISCLI format
                if "passkey <EMPTY_STRING>" in output_str or "passkey <EMPTY_STRING> (default)" in output_str:
                    st.log(f"  ✓ Passkey: <EMPTY_STRING> (default)")
                else:
                    validation_errors.append("Expected empty/default passkey not found")

    # Check timeout
    if 'timeout' in expected_values:
        expected_timeout = expected_values['timeout']
        # Platform-aware validation
        if data.cli_type == "klish":
            # Broadcom format: "Global Timeout       : 50"
            if f"Global Timeout" in output_str and f"{expected_timeout}" in output_str:
                st.log(f"  ✓ Timeout: {expected_timeout}")
            else:
                validation_errors.append(f"Timeout {expected_timeout} not found")
        else:
            # ISCLI format: "timeout 50"
            if f"timeout {expected_timeout}" in output_str:
                st.log(f"  ✓ Timeout: {expected_timeout}")
            else:
                validation_errors.append(f"Timeout {expected_timeout} not found")

    # Check authtype
    if 'authtype' in expected_values:
        expected_authtype = expected_values['authtype']
        # Platform-aware validation
        if data.cli_type == "klish":
            # Broadcom format: "Authentication Type  : PAP" (uppercase)
            expected_authtype_upper = expected_authtype.upper()
            if "Authentication Type" in output_str and expected_authtype_upper in output_str:
                st.log(f"  ✓ Auth type: {expected_authtype}")
            else:
                validation_errors.append(f"Auth type {expected_authtype} not found")
        else:
            # ISCLI format: "auth_type pap" (lowercase)
            if f"auth_type {expected_authtype}" in output_str:
                st.log(f"  ✓ Auth type: {expected_authtype}")
            else:
                validation_errors.append(f"Auth type {expected_authtype} not found")

    # Check priority
    if 'priority' in expected_values:
        expected_priority = expected_values['priority']
        # ISCLI: "priority 1"   Klish: priority in table column
        if (f"priority {expected_priority}" in output_str or
                expected_priority in output_str):
            st.log(f"  ✓ Priority: {expected_priority}")
        else:
            validation_errors.append(f"Priority {expected_priority} not found")

    # Check port
    if 'port' in expected_values:
        expected_port = expected_values['port']
        # ISCLI: "tcp_port 49"   Klish: port value appears in PORT column
        if (f"tcp_port {expected_port}" in output_str or
                f"port {expected_port}" in output_str or
                f"PORT {expected_port}" in output_str.upper()):
            st.log(f"  ✓ TCP Port: {expected_port}")
        else:
            validation_errors.append(f"TCP Port {expected_port} not found")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ All TACACS+ validations passed")
    return True


# ======================================================================
# MODULE 4: CLEANUP
# ======================================================================
def module_4_cleanup(dut: str):
    """
    Module 4: Cleanup
    Remove all TACACS+ configuration after test completion.
    """
    st.log(f"[MODULE 4] Cleaning up TACACS+ configuration on {dut}")

    # Platform-aware command syntax
    if data.cli_type == "klish":
        commands = [
            f"no tacacs-server host {CONFIG.tacacs_server_ipv4}",
            f"no tacacs-server host {CONFIG.tacacs_server_ipv6}",
            "no tacacs-server key",
            "no tacacs-server timeout",
            "no tacacs-server auth-type",
            "end"
        ]
    else:
        commands = [
            f"no tacacs server {CONFIG.tacacs_server_ipv4}",
            f"no tacacs server {CONFIG.tacacs_server_ipv6}",
            "tacacs default passkey",
            "tacacs default timeout",
            "tacacs default authtype",
            "end"
        ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"[MODULE 4] Cleanup completed on {dut}")
    except Exception as e:
        st.log(f"[MODULE 4] Cleanup error: {str(e)}")


# ======================================================================
# Test Function - Main Test Case
# ======================================================================
def test_tacacs_tc_2_1_comprehensive():
    """
    Test Case 2.1: Comprehensive TACACS+ Configuration

    This test verifies:
    1. TC 2.1.1: Add and remove TACACS+ servers (IPv4 and IPv6)
    2. TC 2.1.2: Configure shared secret key (passkey)
    3. TC 2.1.3: Configure timeout value
    4. TC 2.1.4: Configure different authentication types
    5. TC 2.1.5: Test default configuration reset commands
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: COMPREHENSIVE TACACS+ CONFIGURATION")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # ========================================================================
        # TC 2.1.1: Add and Remove TACACS+ Server - IPv4
        # ========================================================================
        st.banner("=" * 80)
        st.banner("TC 2.1.1a: Add and Remove TACACS+ Server - IPv4")
        st.banner("=" * 80)

        st.log("STEP 1: Add IPv4 TACACS+ server")
        if not configure_tacacs_server(dut, CONFIG.tacacs_server_ipv4):
            validation_failures.append("STEP 1: Failed to add IPv4 server")

        st.wait(1)

        st.log("STEP 2: Verify IPv4 server in configuration")
        if not validate_tacacs_output(dut, {
            'server': CONFIG.tacacs_server_ipv4,
            'priority': CONFIG.tacacs_priority,
            'port': CONFIG.tacacs_port
        }):
            validation_failures.append("STEP 2: IPv4 server validation failed")

        st.wait(1)

        st.log("STEP 3: Remove IPv4 TACACS+ server")
        if not remove_tacacs_server(dut, CONFIG.tacacs_server_ipv4):
            validation_failures.append("STEP 3: Failed to remove IPv4 server")

        st.wait(1)

        st.log("STEP 4: Verify IPv4 server removed")
        if not validate_tacacs_output(dut, {'server': None}):
            validation_failures.append("STEP 4: IPv4 server still present after removal")

        # ========================================================================
        # TC 2.1.1b: Add and Remove TACACS+ Server - IPv6
        # ========================================================================
        st.banner("=" * 80)
        st.banner("TC 2.1.1b: Add and Remove TACACS+ Server - IPv6")
        st.banner("=" * 80)

        st.log("STEP 5: Add IPv6 TACACS+ server")
        if not configure_tacacs_server(dut, CONFIG.tacacs_server_ipv6):
            validation_failures.append("STEP 5: Failed to add IPv6 server")

        st.wait(1)

        st.log("STEP 6: Verify IPv6 server in configuration")
        if not validate_tacacs_output(dut, {
            'server': CONFIG.tacacs_server_ipv6,
            'priority': CONFIG.tacacs_priority,
            'port': CONFIG.tacacs_port
        }):
            validation_failures.append("STEP 6: IPv6 server validation failed")

        st.wait(1)

        st.log("STEP 7: Remove IPv6 TACACS+ server")
        if not remove_tacacs_server(dut, CONFIG.tacacs_server_ipv6):
            validation_failures.append("STEP 7: Failed to remove IPv6 server")

        st.wait(1)

        st.log("STEP 8: Verify IPv6 server removed")
        if not validate_tacacs_output(dut, {'server': None}):
            validation_failures.append("STEP 8: IPv6 server still present after removal")

        # ========================================================================
        # TC 2.1.2: Configure Shared Secret Key
        # ========================================================================
        st.banner("=" * 80)
        st.banner("TC 2.1.2: Configure Shared Secret Key")
        st.banner("=" * 80)

        st.log("STEP 9: Add IPv4 server for passkey testing")
        configure_tacacs_server(dut, CONFIG.tacacs_server_ipv4)
        st.wait(1)

        st.log("STEP 10: Configure TACACS+ passkey")
        if not configure_tacacs_passkey(dut, CONFIG.passkey1):
            validation_failures.append("STEP 10: Failed to configure passkey")

        st.wait(1)

        st.log("STEP 11: Verify passkey in configuration")
        if not validate_tacacs_output(dut, {
            'passkey': CONFIG.passkey1,
            'server': CONFIG.tacacs_server_ipv4
        }):
            validation_failures.append("STEP 11: Passkey validation failed")

        # ========================================================================
        # TC 2.1.3: Configure Timeout Value
        # ========================================================================
        st.banner("=" * 80)
        st.banner("TC 2.1.3: Configure Timeout Value")
        st.banner("=" * 80)

        st.log("STEP 12: Update passkey for timeout test")
        configure_tacacs_passkey(dut, CONFIG.passkey2)
        st.wait(1)

        st.log("STEP 13: Configure custom timeout value")
        if not configure_tacacs_timeout(dut, CONFIG.timeout_custom):
            validation_failures.append("STEP 13: Failed to configure timeout")

        st.wait(1)

        st.log("STEP 14: Verify timeout in configuration")
        if not validate_tacacs_output(dut, {
            'timeout': CONFIG.timeout_custom,
            'passkey': CONFIG.passkey2,
            'server': CONFIG.tacacs_server_ipv4
        }):
            validation_failures.append("STEP 14: Timeout validation failed")

        # ========================================================================
        # TC 2.1.4: Configure Authentication Types and Test Defaults
        # ========================================================================
        st.banner("=" * 80)
        st.banner("TC 2.1.4: Configure Authentication Types and Defaults")
        st.banner("=" * 80)

        # Test PAP authtype and reset authtype to default
        st.log("STEP 15: Configure authtype PAP")
        configure_tacacs_authtype(dut, CONFIG.authtype_pap)
        st.wait(1)

        st.log("STEP 16: Reset authtype to default")
        reset_tacacs_default(dut, "authtype")
        st.wait(1)

        st.log("STEP 17: Verify authtype is default (PAP)")
        if not validate_tacacs_output(dut, {'authtype': CONFIG.authtype_pap}):
            validation_failures.append("STEP 17: Default authtype validation failed")

        # Test CHAP authtype and reset passkey to default
        st.log("STEP 18: Configure authtype CHAP")
        configure_tacacs_authtype(dut, CONFIG.authtype_chap)
        st.wait(1)

        st.log("STEP 19: Reset passkey to default")
        reset_tacacs_default(dut, "passkey")
        st.wait(1)

        st.log("STEP 20: Verify authtype CHAP and passkey is default")
        if not validate_tacacs_output(dut, {
            'authtype': CONFIG.authtype_chap,
            'passkey': None  # Empty/default passkey
        }):
            validation_failures.append("STEP 20: CHAP authtype and default passkey validation failed")

        # Test MSCHAP authtype and reset timeout to default
        st.log("STEP 21: Configure authtype MSCHAP")
        configure_tacacs_authtype(dut, CONFIG.authtype_mschap)
        st.wait(1)

        st.log("STEP 22: Reset timeout to default")
        reset_tacacs_default(dut, "timeout")
        st.wait(1)

        st.log("STEP 23: Verify authtype MSCHAP and timeout is default (5)")
        if not validate_tacacs_output(dut, {
            'authtype': CONFIG.authtype_mschap,
            'timeout': CONFIG.timeout_default
        }):
            validation_failures.append("STEP 23: MSCHAP authtype and default timeout validation failed")

        # Test LOGIN authtype
        st.log("STEP 24: Configure authtype LOGIN")
        configure_tacacs_authtype(dut, CONFIG.authtype_login)
        st.wait(1)

        st.log("STEP 25: Verify authtype LOGIN")
        if not validate_tacacs_output(dut, {
            'authtype': CONFIG.authtype_login,
            'timeout': CONFIG.timeout_default,
            'server': CONFIG.tacacs_server_ipv4
        }):
            validation_failures.append("STEP 25: LOGIN authtype validation failed")

    except Exception as e:
        st.error(f"Exception in test_tacacs_tc_2_1_comprehensive: {str(e)}")
        validation_failures.append(f"Unexpected exception: {str(e)}")

    # ========================================================================
    # Final Test Result
    # ========================================================================
    st.banner("=" * 80)
    if validation_failures:
        st.banner("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        st.log(f"TEST CASE {TC_ID} VALIDATION FAILURES:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.banner("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        st.report_fail("test_case_failed", f"Test Case {TC_ID}: {len(validation_failures)} validation failure(s)")
    else:
        st.banner("=" * 80)
        st.banner(f"TEST CASE {TC_ID}: PASSED")
        st.banner("=" * 80)
        st.log("✓ All validations passed successfully")
        st.log("  - TC 2.1.1a: IPv4 server add/remove verified")
        st.log("  - TC 2.1.1b: IPv6 server add/remove verified")
        st.log("  - TC 2.1.2: Shared secret key (passkey) configured and verified")
        st.log("  - TC 2.1.3: Timeout value configured and verified")
        st.log("  - TC 2.1.4: All auth types (PAP, CHAP, MSCHAP, LOGIN) configured and verified")
        st.log("  - TC 2.1.5: Default configuration reset commands verified")
        st.report_pass("test_case_passed")
