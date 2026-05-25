"""
TACACS+ TEST CASE 2.1.6: CONFIGURE SOURCE INTERFACE
Test Case ID: TC-TACACS-2.1.6

Feature      : TACACS+ (Terminal Access Controller Access-Control System Plus)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_Tacacs/test_tacacs_tc_2_1_6_source_interface.py \
    --logs-path ./logs/tacacs_tc_2_1_6_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 2.1.6: Configure Source Interface

  Objective:
    Verify TACACS+ source interface can be configured and changed between
    different interface types (Ethernet, Management, Loopback).

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing TACACS+ config
    2. Module 2 - Configuration:
       - Configure TACACS+ server with shared key
       - Set source-interface to Ethernet4
       - Change source-interface to Management0
       - Change source-interface back to Ethernet4
       - Configure AAA authentication with TACACS+ and local fallback
    3. Module 3 - Validation:
       - Verify source-interface appears in 'show tacacs-server'
       - Verify source-interface appears in running configuration
       - Verify AAA configuration
       - Verify TACACS+ server configuration details
    4. Module 4 - Cleanup: Remove all TACACS+ configuration

Pre-requisites:
  - 1 SONiC device (DUT1) - IP: 192.168.100.120
  - TACACS+ server running on 192.168.100.87
  - Management and Ethernet interfaces available
  - Testbed: testbed_2vs.yaml or compatible

Notes:
  - Source interface determines which IP address TACACS+ packets originate from
  - Can be set to Ethernet, Management, Loopback, or Vlan interfaces
  - Only one source interface can be active at a time
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
    # TACACS+ Server Configuration
    "tacacs_server_ip":     "192.168.100.87",
    "tacacs_key":           "Test123",
    "tacacs_port":          "49",
    "tacacs_timeout":       "5",
    "tacacs_authtype":      "pap",

    # Source Interface Options
    "source_if_ethernet":   "Ethernet4",
    "source_if_mgmt":       "Management0",
    "source_if_loopback":   "Loopback0",

    # CLI Type
    "cli_type":             "klish"
})

# Test Case ID
TC_ID = "TC-TACACS-2.1.6"


# ======================================================================
# Fixture - Module Level Setup/Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def tacacs_tc_2_1_6_module_hooks(request):
    """Module-level fixture for setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID} - CONFIGURE SOURCE INTERFACE - MODULE START")
    st.banner("=" * 80)

    # Ensure minimum topology (single DUT)
    vars = st.ensure_min_topology("D1")
    # Fix: st.get_ui_type() may return "click" (bash mode) which breaks config commands.
    # Detect and override to "klish" so proper config mode is used.
    detected_cli = st.get_ui_type(vars.D1)
    if detected_cli == "click" or detected_cli not in ["klish", "rest-put", "rest-patch"]:
        data.cli_type = "klish"
        st.log(f"Module Setup: Detected '{detected_cli}', overriding to 'klish' for config mode")
    else:
        data.cli_type = detected_cli

    st.log(f"DUT1: {vars.D1}")
    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"TACACS+ Server: {CONFIG.tacacs_server_ip}")
    st.log(f"TACACS+ Key: {CONFIG.tacacs_key}")

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

    commands = [
        f"no tacacs-server host {CONFIG.tacacs_server_ip}",
        "no tacacs-server source-interface",
        "no tacacs-server key",
        "no tacacs-server timeout",
        "no tacacs-server auth-type",
        "no aaa authentication login default",
        "no aaa authentication failthrough",
        "end"
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"[MODULE 1] Unconfiguration completed on {dut}")
    except Exception as e:
        st.log(f"[MODULE 1] Unconfiguration error (may be expected): {str(e)}")


# ======================================================================
# MODULE 2: CONFIGURATION FUNCTIONS
# ======================================================================
def configure_tacacs_server_with_key(dut: str, server_ip: str, key: str) -> bool:
    """
    Configure TACACS+ server with shared key.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IP address
        key: Shared secret key

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[MODULE 2] Configuring TACACS+ server {server_ip} with key")

    commands = [
        f"tacacs-server host {server_ip}",
        f"tacacs-server key {key}",
        "end"
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"[MODULE 2] TACACS+ server configured with key")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure TACACS+ server: {str(e)}")
        return False


def configure_source_interface(dut: str, interface: str) -> bool:
    """
    Configure TACACS+ source interface.

    Args:
        dut: Device identifier
        interface: Source interface (e.g., "Ethernet4", "Management0")

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[MODULE 2] Configuring source-interface: {interface}")

    commands = [
        f"tacacs-server source-interface {interface}",
        "end"
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"[MODULE 2] Source interface {interface} configured")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure source interface: {str(e)}")
        return False


def remove_source_interface(dut: str) -> bool:
    """
    Remove TACACS+ source interface configuration.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[MODULE 2] Removing source-interface configuration")

    commands = [
        "no tacacs-server source-interface",
        "end"
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"[MODULE 2] Source interface removed")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to remove source interface: {str(e)}")
        return False


def configure_aaa_authentication(dut: str) -> bool:
    """
    Configure AAA authentication to use TACACS+ with local fallback.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[MODULE 2] Configuring AAA authentication")

    commands = [
        "aaa authentication login default group tacacs+ local",
        "aaa authentication failthrough enable",
        "end"
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.log(f"[MODULE 2] AAA authentication configured")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure AAA: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION FUNCTIONS
# ======================================================================
def validate_source_interface_in_show_tacacs(dut: str, expected_interface: str) -> bool:
    """
    Validate source interface appears in 'show tacacs-server' output.

    Args:
        dut: Device identifier
        expected_interface: Expected source interface (e.g., "Ethernet4")

    Returns:
        bool: True if validation passes, False otherwise
    """
    st.log(f"[MODULE 3] Validating source-interface '{expected_interface}' in show tacacs-server")

    output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""

    st.log(f"show tacacs-server output:\n{output_str}")

    # Check for source-interface line
    if "source interface" in output_str.lower() and expected_interface.lower() in output_str.lower():
        st.log(f"  ✓ Source interface '{expected_interface}' found in output")
        return True
    else:
        st.error(f"  ✗ Source interface '{expected_interface}' NOT found in output")
        st.log(f"Expected: 'source-interface  : {expected_interface}'")
        return False


def validate_source_interface_in_running_config(dut: str, expected_interface: str) -> bool:
    """
    Validate source interface appears in running configuration.

    Args:
        dut: Device identifier
        expected_interface: Expected source interface

    Returns:
        bool: True if validation passes, False otherwise
    """
    st.log(f"[MODULE 3] Validating source-interface in running configuration")

    output = st.show(
        dut,
        "show running-configuration | grep tacacs",
        type=data.cli_type,
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    st.log(f"Running configuration (tacacs):\n{output_str}")

    expected_line = f"tacacs-server source-interface {expected_interface}"

    if expected_line in output_str:
        st.log(f"  ✓ Found in running config: {expected_line}")
        return True
    else:
        st.error(f"  ✗ NOT found in running config: {expected_line}")
        return False


def validate_tacacs_server_config(dut: str) -> bool:
    """
    Validate complete TACACS+ server configuration.

    Args:
        dut: Device identifier

    Returns:
        bool: True if validation passes, False otherwise
    """
    st.log(f"[MODULE 3] Validating TACACS+ server configuration")

    output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""

    st.log(f"show tacacs-server output:\n{output_str}")

    # Platform-aware validation checks
    failed_checks = []

    # Check server IP present (both platforms)
    if CONFIG.tacacs_server_ip in output_str:
        st.log(f"  ✓ Server IP: {CONFIG.tacacs_server_ip}")
    else:
        st.error(f"  ✗ Server IP: {CONFIG.tacacs_server_ip} NOT found")
        failed_checks.append("server_ip")

    # Check timeout (ISCLI: "timeout 5", Klish: "5" in Global Timeout row)
    if CONFIG.tacacs_timeout in output_str:
        st.log(f"  ✓ Timeout: {CONFIG.tacacs_timeout}")
    else:
        st.error(f"  ✗ Timeout: {CONFIG.tacacs_timeout} NOT found")
        failed_checks.append("timeout")

    # Check port (ISCLI: "tcp_port 49", Klish: "49" in PORT column)
    if CONFIG.tacacs_port in output_str:
        st.log(f"  ✓ Port: {CONFIG.tacacs_port}")
    else:
        st.error(f"  ✗ Port: {CONFIG.tacacs_port} NOT found")
        failed_checks.append("port")

    # Check auth-type (ISCLI: "auth_type pap", Klish: "Authentication Type : PAP")
    if data.cli_type == "klish":
        authtype_check = CONFIG.tacacs_authtype.upper()
        if authtype_check in output_str.upper():
            st.log(f"  ✓ Auth-type: {CONFIG.tacacs_authtype}")
        else:
            st.error(f"  ✗ Auth-type: {CONFIG.tacacs_authtype} NOT found")
            failed_checks.append("auth-type")
    else:
        if f"auth_type {CONFIG.tacacs_authtype}" in output_str:
            st.log(f"  ✓ Auth-type: {CONFIG.tacacs_authtype}")
        else:
            st.error(f"  ✗ Auth-type: {CONFIG.tacacs_authtype} NOT found")
            failed_checks.append("auth-type")

    # Check key configured (Klish: "Key Configured : Yes", ISCLI: passkey present)
    if data.cli_type == "klish":
        if "Key Configured" in output_str and "Yes" in output_str:
            st.log(f"  ✓ Key configured: Yes")
        else:
            st.error(f"  ✗ Key configured: Yes NOT found")
            failed_checks.append("key_configured")
    else:
        if "passkey" in output_str and CONFIG.tacacs_key in output_str:
            st.log(f"  ✓ Key configured: {CONFIG.tacacs_key}")
        else:
            st.error(f"  ✗ Key (passkey) NOT found in output")
            failed_checks.append("key_configured")

    if failed_checks:
        st.error(f"Failed validation checks: {failed_checks}")
        return False

    st.log(f"  ✓ All TACACS+ server configuration checks passed")
    return True


def validate_aaa_configuration(dut: str) -> bool:
    """
    Validate AAA authentication configuration.

    Args:
        dut: Device identifier

    Returns:
        bool: True if validation passes, False otherwise
    """
    st.log(f"[MODULE 3] Validating AAA configuration")

    output = st.show(dut, "show aaa", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""

    st.log(f"show aaa output:\n{output_str}")

    # Check for expected AAA configuration
    expected_items = [
        "failthrough",
        "enabled",
        "login-method",
        "tacacs+"
    ]

    missing_items = []
    for item in expected_items:
        if item in output_str:
            st.log(f"  ✓ Found: {item}")
        else:
            st.error(f"  ✗ Missing: {item}")
            missing_items.append(item)

    if missing_items:
        st.error(f"Missing items in AAA config: {missing_items}")
        return False

    st.log(f"  ✓ AAA configuration validated successfully")
    return True


def validate_running_config_complete(dut: str) -> bool:
    """
    Validate complete running configuration for TACACS+.

    Args:
        dut: Device identifier

    Returns:
        bool: True if validation passes, False otherwise
    """
    st.log(f"[MODULE 3] Validating complete running configuration")

    output = st.show(
        dut,
        "show running-configuration | grep tacacs",
        type=data.cli_type,
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    st.log(f"Running configuration (tacacs):\n{output_str}")

    # Expected items in running config
    expected_items = [
        f"tacacs-server host {CONFIG.tacacs_server_ip}",
        "tacacs-server source-interface",
        "tacacs-server authtype",
        "tacacs-server passkey"
    ]

    missing_items = []
    for item in expected_items:
        if item in output_str:
            st.log(f"  ✓ Found: {item}")
        else:
            st.error(f"  ✗ Missing: {item}")
            missing_items.append(item)

    if missing_items:
        st.error(f"Missing items in running config: {missing_items}")
        return False

    st.log(f"  ✓ Running configuration validated successfully")
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

    commands = [
        f"no tacacs-server host {CONFIG.tacacs_server_ip}",
        "no tacacs-server source-interface",
        "no tacacs-server key",
        "no tacacs-server timeout",
        "no tacacs-server auth-type",
        "no aaa authentication login default",
        "no aaa authentication failthrough",
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
def test_tacacs_tc_2_1_6_source_interface():
    """
    Test Case 2.1.6: Configure Source Interface

    This test verifies:
    1. TACACS+ server can be configured with shared key
    2. Source interface can be set to Ethernet4
    3. Source interface can be changed to Management0
    4. Source interface can be changed back to Ethernet4
    5. Source interface appears in show tacacs-server
    6. Source interface appears in running configuration
    7. AAA authentication can be configured with TACACS+ and local fallback
    8. Complete TACACS+ configuration is accurate
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: CONFIGURE SOURCE INTERFACE")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # ====================================================================
        # Module 2: Configuration
        # ====================================================================
        st.banner("[MODULE 2] CONFIGURATION - Setting up TACACS+ with source interface")

        st.log("STEP 1: Configure TACACS+ server with shared key")
        if not configure_tacacs_server_with_key(dut, CONFIG.tacacs_server_ip, CONFIG.tacacs_key):
            validation_failures.append("STEP 1: Failed to configure TACACS+ server with key")

        st.wait(1)

        st.log("STEP 2: Verify initial TACACS+ configuration")
        if not validate_tacacs_server_config(dut):
            validation_failures.append("STEP 2: Initial TACACS+ configuration validation failed")

        st.wait(1)

        st.log("STEP 3: Configure source-interface as Ethernet4")
        if not configure_source_interface(dut, CONFIG.source_if_ethernet):
            validation_failures.append("STEP 3: Failed to configure source-interface Ethernet4")

        st.wait(1)

        # ====================================================================
        # Module 3: Validation - Source Interface Ethernet4
        # ====================================================================
        st.banner("[MODULE 3] VALIDATION - Verifying source-interface Ethernet4")

        st.log("STEP 4: Verify source-interface Ethernet4 in show tacacs-server")
        if not validate_source_interface_in_show_tacacs(dut, CONFIG.source_if_ethernet):
            validation_failures.append("STEP 4: Source-interface Ethernet4 not found in show tacacs-server")

        st.wait(1)

        st.log("STEP 5: Verify source-interface Ethernet4 in running config")
        if not validate_source_interface_in_running_config(dut, CONFIG.source_if_ethernet):
            validation_failures.append("STEP 5: Source-interface Ethernet4 not found in running config")

        st.wait(1)

        # ====================================================================
        # Change Source Interface to Management0
        # ====================================================================
        st.log("STEP 6: Change source-interface to Management0")
        if not configure_source_interface(dut, CONFIG.source_if_mgmt):
            validation_failures.append("STEP 6: Failed to change source-interface to Management0")

        st.wait(1)

        st.log("STEP 7: Verify source-interface Management0 in show tacacs-server")
        if not validate_source_interface_in_show_tacacs(dut, CONFIG.source_if_mgmt):
            validation_failures.append("STEP 7: Source-interface Management0 not found in show tacacs-server")

        st.wait(1)

        # ====================================================================
        # Change Source Interface back to Ethernet4
        # ====================================================================
        st.log("STEP 8: Change source-interface back to Ethernet4")
        if not configure_source_interface(dut, CONFIG.source_if_ethernet):
            validation_failures.append("STEP 8: Failed to change source-interface back to Ethernet4")

        st.wait(1)

        st.log("STEP 9: Verify source-interface Ethernet4 (after changing back)")
        if not validate_source_interface_in_show_tacacs(dut, CONFIG.source_if_ethernet):
            validation_failures.append("STEP 9: Source-interface Ethernet4 not found after changing back")

        st.wait(1)

        # ====================================================================
        # Configure AAA Authentication
        # ====================================================================
        st.log("STEP 10: Configure AAA authentication with TACACS+ and local fallback")
        if not configure_aaa_authentication(dut):
            validation_failures.append("STEP 10: Failed to configure AAA authentication")

        st.wait(1)

        st.log("STEP 11: Verify AAA configuration")
        if not validate_aaa_configuration(dut):
            validation_failures.append("STEP 11: AAA configuration validation failed")

        st.wait(1)

        # ====================================================================
        # Final Validation
        # ====================================================================
        st.log("STEP 12: Verify complete TACACS+ server configuration")
        if not validate_tacacs_server_config(dut):
            validation_failures.append("STEP 12: Final TACACS+ server configuration validation failed")

        st.wait(1)

        st.log("STEP 13: Verify complete running configuration")
        if not validate_running_config_complete(dut):
            validation_failures.append("STEP 13: Complete running configuration validation failed")

    except Exception as e:
        st.error(f"Exception in test_tacacs_tc_2_1_6_source_interface: {str(e)}")
        validation_failures.append(f"Unexpected exception: {str(e)}")

    # ====================================================================
    # Final Test Result
    # ====================================================================
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log(f"TEST CASE {TC_ID} VALIDATION FAILURES:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("test_case_failed", f"Test Case {TC_ID}: {len(validation_failures)} validation failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log(f"✅ TEST CASE {TC_ID}: CONFIGURE SOURCE INTERFACE - PASSED")
        st.log("=" * 80)
        st.log("✓ All validations passed successfully")
        st.log("  - TACACS+ server configured with shared key")
        st.log("  - Source interface Ethernet4 configured and verified")
        st.log("  - Source interface changed to Management0 and verified")
        st.log("  - Source interface changed back to Ethernet4 and verified")
        st.log("  - AAA authentication configured with TACACS+ and local fallback")
        st.log("  - Complete configuration verified in show commands")
        st.log("  - Complete configuration verified in running-config")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
