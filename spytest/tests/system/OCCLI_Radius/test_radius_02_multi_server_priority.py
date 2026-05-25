"""
RADIUS Test Case 4.1.2: Configure Multiple Servers with Priority
=================================================================

Feature      : RADIUS (Remote Authentication Dial-In User Service)
Test Case ID : TC-RADIUS-4.1.2
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  SPYTEST_PYTHON=./spytest_venv/bin/python ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    system/OCCLI_Radius/test_radius_02_multi_server_priority.py \
    --logs-path ./logs/radius_tc_4_1_2_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 4.1.2: Configure Multiple RADIUS Servers with Priority

  Manual Test Steps Covered:
    Step 1: Configure 3 RADIUS servers with priorities 2, 3, 4
      - radius-server host 10.10.10.100  auth-port 1812 key Key2 priority 2 timeout 5 retransmit 3
      - radius-server host 172.16.1.200  auth-port 1812 key Key3 priority 3 timeout 5 retransmit 3
      - radius-server host 192.168.200.100 auth-port 1812 key Key4 priority 4 timeout 5 retransmit 3
      - Verify: show radius-server (all 3 servers with correct priorities)

    Step 2: Configure AAA authentication with TACACS+ and failthrough/fallback
      - aaa authentication failthrough enable
      - aaa authentication fallback enable
      - aaa authentication login tacacs+
      - Verify: show aaa

    Step 3: Configure TACACS+ global parameters alongside RADIUS
      - tacacs-server passkey Test123
      - tacacs-server source-interface Ethernet4
      - tacacs-server authtype chap
      - tacacs-server timeout 40
      - tacacs-server host 192.168.100.87
      - Verify: show tacacs-server

  Module Structure:
    Module 1 - Unconfiguration : Clean all existing RADIUS + TACACS config
    Module 2 - Configuration   : Configure all servers and global params
    Module 3 - Validation      : Verify via show radius-server, show aaa, show tacacs-server
    Module 4 - Cleanup         : Remove all RADIUS + TACACS configuration

Pre-requisites:
  - 1 SONiC device (DUT1) with Broadcom/Klish CLI
  - Testbed: testbed_2vs.yaml or compatible
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
    # RADIUS Server 1
    "radius_server1_ip":        "10.10.10.100",
    "radius_server1_auth_port": "1812",
    "radius_server1_key":       "Key2",
    "radius_server1_priority":  "2",
    "radius_server1_timeout":   "5",
    "radius_server1_retransmit":"3",

    # RADIUS Server 2
    "radius_server2_ip":        "172.16.1.200",
    "radius_server2_auth_port": "1812",
    "radius_server2_key":       "Key3",
    "radius_server2_priority":  "3",
    "radius_server2_timeout":   "5",
    "radius_server2_retransmit":"3",

    # RADIUS Server 3
    "radius_server3_ip":        "192.168.200.100",
    "radius_server3_auth_port": "1812",
    "radius_server3_key":       "Key4",
    "radius_server3_priority":  "4",
    "radius_server3_timeout":   "5",
    "radius_server3_retransmit":"3",

    # AAA Configuration
    "aaa_login_method":         "tacacs+",
    "aaa_failthrough":          "enable",
    "aaa_fallback":             "enable",

    # TACACS+ Configuration
    "tacacs_server_ip":         "192.168.100.87",
    "tacacs_passkey":           "Test123",
    "tacacs_src_intf":          "Ethernet4",
    "tacacs_authtype":          "chap",
    "tacacs_timeout":           "40",
    "tacacs_port":              "49",
    "tacacs_priority":          "1",

    # CLI Type
    "cli_type":                 "klish"
})

TC_ID = "TC-RADIUS-4.1.2"


# ======================================================================
# Fixture - Module Level Setup / Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def radius_tc_4_1_2_module_hooks(request):
    """
    Module-level fixture:
      - Setup  : Unconfigure all RADIUS + TACACS config (Module 1)
      - Yield  : Run all test functions (Modules 2 & 3)
      - Teardown: Cleanup all RADIUS + TACACS config (Module 4)
    """
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID}: MODULE PROLOGUE - Multiple RADIUS Servers with Priority")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = CONFIG.cli_type

    st.log(f"CLI Type           : {data.cli_type}")
    st.log(f"RADIUS Server1     : {CONFIG.radius_server1_ip} (priority {CONFIG.radius_server1_priority})")
    st.log(f"RADIUS Server2     : {CONFIG.radius_server2_ip} (priority {CONFIG.radius_server2_priority})")
    st.log(f"RADIUS Server3     : {CONFIG.radius_server3_ip} (priority {CONFIG.radius_server3_priority})")
    st.log(f"TACACS+ Server     : {CONFIG.tacacs_server_ip}")
    st.log(f"TACACS+ Src-Intf   : {CONFIG.tacacs_src_intf}")
    st.log(f"TACACS+ Auth-type  : {CONFIG.tacacs_authtype}")
    st.log(f"TACACS+ Timeout    : {CONFIG.tacacs_timeout}")

    # ── Module 1: Unconfiguration ──────────────────────────────────────
    st.banner("MODULE 1: UNCONFIGURATION")
    module_1_unconfigure(vars.D1)
    st.wait(2, "Waiting after unconfiguration")

    yield  # ── Modules 2 & 3 run here ──

    # ── Module 4: Cleanup ─────────────────────────────────────────────
    st.banner("MODULE 4: CLEANUP")
    module_4_cleanup(vars.D1)
    st.log("MODULE 4 COMPLETED: All RADIUS + TACACS configuration removed")


# ======================================================================
# MODULE 1: UNCONFIGURATION
# ======================================================================
def module_1_unconfigure(dut: str):
    """
    Module 1: Remove all existing RADIUS and TACACS+ configuration.
    Uses skip_error_check=True as config may not exist.
    """
    st.log(f"[MODULE 1] Removing all RADIUS + TACACS config on {dut}...")

    radius_commands = [
        f"no radius-server host {CONFIG.radius_server1_ip}",
        f"no radius-server host {CONFIG.radius_server2_ip}",
        f"no radius-server host {CONFIG.radius_server3_ip}",
        "no radius-server key",
        "no radius-server timeout",
        "no radius-server retransmit",
        "no radius-server auth-type",
        "no radius-server nas-ip",
        "no radius-server statistics",
    ]

    tacacs_commands = [
        f"no tacacs-server host {CONFIG.tacacs_server_ip}",
        "no tacacs-server passkey",
        "no tacacs-server timeout",
        "no tacacs-server authtype",
        "no tacacs-server source-interface",
    ]

    aaa_commands = [
        "no aaa authentication login default",
        "no aaa authentication failthrough",
        "no aaa authentication fallback",
    ]

    try:
        st.config(dut, radius_commands + tacacs_commands + aaa_commands,
                  type=data.cli_type, skip_error_check=True)
        st.log("[MODULE 1] Unconfiguration completed")
    except Exception as e:
        st.log(f"[MODULE 1] Unconfiguration note (may be expected): {str(e)}")


# ======================================================================
# MODULE 2: CONFIGURATION FUNCTIONS
# ======================================================================
def configure_radius_servers(dut: str) -> bool:
    """
    Module 2: Configure 3 RADIUS servers with per-server priority, key,
    auth-port, timeout, retransmit.

    Commands:
      radius-server host 10.10.10.100  auth-port 1812 key Key2 priority 2 timeout 5 retransmit 3
      radius-server host 172.16.1.200  auth-port 1812 key Key3 priority 3 timeout 5 retransmit 3
      radius-server host 192.168.200.100 auth-port 1812 key Key4 priority 4 timeout 5 retransmit 3
    """
    st.log(f"[MODULE 2] Configuring 3 RADIUS servers with priorities on {dut}")

    commands = [
        (
            f"radius-server host {CONFIG.radius_server1_ip}"
            f" auth-port {CONFIG.radius_server1_auth_port}"
            f" key {CONFIG.radius_server1_key}"
            f" priority {CONFIG.radius_server1_priority}"
            f" timeout {CONFIG.radius_server1_timeout}"
            f" retransmit {CONFIG.radius_server1_retransmit}"
        ),
        (
            f"radius-server host {CONFIG.radius_server2_ip}"
            f" auth-port {CONFIG.radius_server2_auth_port}"
            f" key {CONFIG.radius_server2_key}"
            f" priority {CONFIG.radius_server2_priority}"
            f" timeout {CONFIG.radius_server2_timeout}"
            f" retransmit {CONFIG.radius_server2_retransmit}"
        ),
        (
            f"radius-server host {CONFIG.radius_server3_ip}"
            f" auth-port {CONFIG.radius_server3_auth_port}"
            f" key {CONFIG.radius_server3_key}"
            f" priority {CONFIG.radius_server3_priority}"
            f" timeout {CONFIG.radius_server3_timeout}"
            f" retransmit {CONFIG.radius_server3_retransmit}"
        ),
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for RADIUS server config to apply")
        st.log("[MODULE 2] All 3 RADIUS servers configured")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure RADIUS servers: {str(e)}")
        return False


def configure_aaa_authentication(dut: str) -> bool:
    """
    Module 2: Configure AAA authentication with TACACS+, failthrough, fallback.

    Commands:
      aaa authentication failthrough enable
      aaa authentication fallback enable
      aaa authentication login tacacs+
    """
    st.log(f"[MODULE 2] Configuring AAA authentication on {dut}")

    commands = [
        f"aaa authentication failthrough {CONFIG.aaa_failthrough}",
        f"aaa authentication fallback {CONFIG.aaa_fallback}",
        f"aaa authentication login default group {CONFIG.aaa_login_method} local",
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for AAA config to apply")
        st.log("[MODULE 2] AAA authentication configured")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure AAA: {str(e)}")
        return False


def configure_tacacs_params(dut: str) -> bool:
    """
    Module 2: Configure TACACS+ global params alongside RADIUS.

    Commands:
      tacacs-server key Test123
      tacacs-server source-interface Ethernet4
      tacacs-server auth-type chap
      tacacs-server timeout 40
      tacacs-server host 192.168.100.87
    """
    st.log(f"[MODULE 2] Configuring TACACS+ parameters on {dut}")

    commands = [
        f"tacacs-server passkey {CONFIG.tacacs_passkey}",
        f"tacacs-server source-interface {CONFIG.tacacs_src_intf}",
        f"tacacs-server authtype {CONFIG.tacacs_authtype}",
        f"tacacs-server timeout {CONFIG.tacacs_timeout}",
        f"tacacs-server host {CONFIG.tacacs_server_ip}",
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for TACACS+ config to apply")
        st.log("[MODULE 2] TACACS+ parameters configured")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure TACACS+ params: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION FUNCTIONS
# ======================================================================
def get_show_radius_output(dut: str) -> str:
    """Module 3: Execute show radius-server and return raw output string."""
    st.wait(3, "before show radius-server")
    output = st.show(
        dut, "show radius-server",
        type=data.cli_type,
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""
    st.log(f"[MODULE 3] show radius-server output:\n{output_str}")
    return output_str


def get_show_aaa_output(dut: str) -> str:
    """Module 3: Execute show aaa and return raw output string."""
    output = st.show(
        dut, "show aaa",
        type=data.cli_type,
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""
    st.log(f"[MODULE 3] show aaa output:\n{output_str}")
    return output_str


def get_show_tacacs_output(dut: str) -> str:
    """Module 3: Execute show tacacs-server and return raw output string."""
    output = st.show(
        dut, "show tacacs-server",
        type=data.cli_type,
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""
    st.log(f"[MODULE 3] show tacacs-server output:\n{output_str}")
    return output_str


def validate_radius_servers(dut: str) -> bool:
    """
    Module 3: Validate all 3 RADIUS servers with correct priorities.

    Expected in show radius-server:
      10.10.10.100    -   Yes   1812   2   5   3   -   -
      172.16.1.200    -   Yes   1812   3   5   3   -   -
      192.168.200.100 -   Yes   1812   4   5   3   -   -
    """
    st.log(f"[MODULE 3] Validating 3 RADIUS servers on {dut}")

    output_str = get_show_radius_output(dut)
    errors = []

    # ── Server 1: 10.10.10.100 priority 2 ────────────────────────────
    if CONFIG.radius_server1_ip in output_str:
        st.log(f"  ✓ Server1 {CONFIG.radius_server1_ip} present")
    else:
        errors.append(f"Server1 {CONFIG.radius_server1_ip} NOT found")

    if CONFIG.radius_server1_priority in output_str:
        st.log(f"  ✓ Server1 priority: {CONFIG.radius_server1_priority}")
    else:
        errors.append(f"Server1 priority {CONFIG.radius_server1_priority} NOT found")

    if CONFIG.radius_server1_auth_port in output_str:
        st.log(f"  ✓ Server1 auth-port: {CONFIG.radius_server1_auth_port}")
    else:
        errors.append(f"Server1 auth-port {CONFIG.radius_server1_auth_port} NOT found")

    # ── Server 2: 172.16.1.200 priority 3 ────────────────────────────
    if CONFIG.radius_server2_ip in output_str:
        st.log(f"  ✓ Server2 {CONFIG.radius_server2_ip} present")
    else:
        errors.append(f"Server2 {CONFIG.radius_server2_ip} NOT found")

    if CONFIG.radius_server2_priority in output_str:
        st.log(f"  ✓ Server2 priority: {CONFIG.radius_server2_priority}")
    else:
        errors.append(f"Server2 priority {CONFIG.radius_server2_priority} NOT found")

    if CONFIG.radius_server2_auth_port in output_str:
        st.log(f"  ✓ Server2 auth-port: {CONFIG.radius_server2_auth_port}")
    else:
        errors.append(f"Server2 auth-port {CONFIG.radius_server2_auth_port} NOT found")

    # ── Server 3: 192.168.200.100 priority 4 ─────────────────────────
    if CONFIG.radius_server3_ip in output_str:
        st.log(f"  ✓ Server3 {CONFIG.radius_server3_ip} present")
    else:
        errors.append(f"Server3 {CONFIG.radius_server3_ip} NOT found")

    if CONFIG.radius_server3_priority in output_str:
        st.log(f"  ✓ Server3 priority: {CONFIG.radius_server3_priority}")
    else:
        errors.append(f"Server3 priority {CONFIG.radius_server3_priority} NOT found")

    if CONFIG.radius_server3_auth_port in output_str:
        st.log(f"  ✓ Server3 auth-port: {CONFIG.radius_server3_auth_port}")
    else:
        errors.append(f"Server3 auth-port {CONFIG.radius_server3_auth_port} NOT found")

    # ── Key configured: Yes for all servers ──────────────────────────
    # All 3 servers have per-server keys — KEY-CONFIG column shows "Yes"
    key_yes_count = output_str.count("Yes")
    if key_yes_count >= 3:
        st.log(f"  ✓ KEY-CONFIG: Yes found for all servers ({key_yes_count} entries)")
    else:
        errors.append(f"Expected >=3 'Yes' in KEY-CONFIG, found {key_yes_count}")

    if errors:
        for err in errors:
            st.error(f"  ✗ {err}")
        return False

    st.log("[MODULE 3] All 3 RADIUS servers validated ✓")
    return True


def validate_aaa_configuration(dut: str) -> bool:
    """
    Module 3: Validate AAA authentication config.

    Expected in show aaa:
      failthrough  : enabled
      fallback     : enabled
      login-method : tacacs+
    """
    st.log(f"[MODULE 3] Validating AAA configuration on {dut}")

    output_str = get_show_aaa_output(dut)
    errors = []

    # Validate failthrough enabled
    if "failthrough" in output_str.lower() and "enabled" in output_str.lower():
        st.log("  ✓ Failthrough: enabled")
    else:
        errors.append("Failthrough 'enabled' not found in show aaa")

    # Validate fallback enabled
    if "fallback" in output_str.lower() and "enabled" in output_str.lower():
        st.log("  ✓ Fallback: enabled")
    else:
        errors.append("Fallback 'enabled' not found in show aaa")

    # Validate login-method tacacs+
    if "login-method" in output_str.lower() and "tacacs" in output_str.lower():
        st.log(f"  ✓ Login-method: {CONFIG.aaa_login_method}")
    else:
        errors.append(f"Login-method '{CONFIG.aaa_login_method}' not found in show aaa")

    if errors:
        for err in errors:
            st.error(f"  ✗ {err}")
        return False

    st.log("[MODULE 3] AAA configuration validated ✓")
    return True


def validate_tacacs_configuration(dut: str) -> bool:
    """
    Module 3: Validate TACACS+ global parameters.

    Expected in show tacacs-server:
      Source Interface     : Ethernet4
      Authentication Type  : CHAP
      Global Timeout       : 40
      Key Configured       : Yes
      HOST: 192.168.100.87   PORT: 49   PRIORITY: 1
    """
    st.log(f"[MODULE 3] Validating TACACS+ configuration on {dut}")

    output_str = get_show_tacacs_output(dut)
    errors = []

    # Validate source interface
    if "source interface" in output_str.lower() and CONFIG.tacacs_src_intf in output_str:
        st.log(f"  ✓ Source Interface: {CONFIG.tacacs_src_intf}")
    else:
        errors.append(f"Source Interface {CONFIG.tacacs_src_intf} not found in show tacacs-server")

    # Validate auth-type CHAP (shown uppercase)
    if "CHAP" in output_str.upper() and "authentication type" in output_str.lower():
        st.log(f"  ✓ Authentication Type: CHAP")
    else:
        errors.append("Authentication Type CHAP not found in show tacacs-server")

    # Validate global timeout
    if "timeout" in output_str.lower() and CONFIG.tacacs_timeout in output_str:
        st.log(f"  ✓ Global Timeout: {CONFIG.tacacs_timeout}")
    else:
        errors.append(f"Global Timeout {CONFIG.tacacs_timeout} not found in show tacacs-server")

    # Validate key configured: Yes
    if "key configured" in output_str.lower() and "yes" in output_str.lower():
        st.log("  ✓ Key Configured: Yes")
    else:
        errors.append("Key Configured: Yes not found in show tacacs-server")

    # Validate TACACS+ server host present
    if CONFIG.tacacs_server_ip in output_str:
        st.log(f"  ✓ TACACS+ host: {CONFIG.tacacs_server_ip}")
    else:
        errors.append(f"TACACS+ host {CONFIG.tacacs_server_ip} not found in show tacacs-server")

    # Validate port 49
    if CONFIG.tacacs_port in output_str:
        st.log(f"  ✓ TACACS+ port: {CONFIG.tacacs_port}")
    else:
        errors.append(f"TACACS+ port {CONFIG.tacacs_port} not found")

    if errors:
        for err in errors:
            st.error(f"  ✗ {err}")
        return False

    st.log("[MODULE 3] TACACS+ configuration validated ✓")
    return True


# ======================================================================
# MODULE 4: CLEANUP
# ======================================================================
def module_4_cleanup(dut: str):
    """
    Module 4: Remove all RADIUS and TACACS+ configuration after tests.
    """
    st.log(f"[MODULE 4] Cleaning up all RADIUS + TACACS config on {dut}")

    radius_commands = [
        f"no radius-server host {CONFIG.radius_server1_ip}",
        f"no radius-server host {CONFIG.radius_server2_ip}",
        f"no radius-server host {CONFIG.radius_server3_ip}",
        "no radius-server key",
        "no radius-server timeout",
        "no radius-server retransmit",
        "no radius-server auth-type",
        "no radius-server statistics",
    ]

    tacacs_commands = [
        f"no tacacs-server host {CONFIG.tacacs_server_ip}",
        "no tacacs-server passkey",
        "no tacacs-server timeout",
        "no tacacs-server authtype",
        "no tacacs-server source-interface",
    ]

    aaa_commands = [
        "no aaa authentication login default",
        "no aaa authentication failthrough",
        "no aaa authentication fallback",
    ]

    try:
        st.config(dut, radius_commands + tacacs_commands + aaa_commands,
                  type=data.cli_type, skip_error_check=True)
        st.wait(1, "Waiting for cleanup")
        st.log("[MODULE 4] Cleanup completed successfully")
    except Exception as e:
        st.log(f"[MODULE 4] Cleanup note: {str(e)}")


# ======================================================================
# TEST FUNCTIONS
# ======================================================================

@pytest.mark.radius
def test_radius_4_1_2_configure_multi_server_priority():
    """
    TC 4.1.2 - STEP 1: Configure 3 RADIUS servers with different priorities.

    Test Steps:
      1. Configure server1 (10.10.10.100)  priority 2, key Key2, port 1812, timeout 5, retransmit 3
      2. Configure server2 (172.16.1.200)  priority 3, key Key3, port 1812, timeout 5, retransmit 3
      3. Configure server3 (192.168.200.100) priority 4, key Key4, port 1812, timeout 5, retransmit 3
      4. Validate show radius-server:
           - All 3 servers visible
           - Correct priorities (2, 3, 4)
           - KEY-CONFIG: Yes for all
           - AUTH-PORT: 1812 for all

    Expected Result: All 3 servers present with correct priority ordering
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 1: Configure Multiple RADIUS Servers with Priority")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 2: Configuration ──────────────────────────────────────
    st.log("MODULE 2: Configuration Phase")
    st.log("STEP 1: Configure 3 RADIUS servers with priorities 2, 3, 4")

    if not configure_radius_servers(dut):
        failures.append("Failed to configure RADIUS servers with priorities")

    st.log("✅ MODULE 2 STEP 1 completed")

    # ── MODULE 3: Validation ─────────────────────────────────────────
    st.log("MODULE 3: Validation Phase")
    st.log("STEP 2: Validate all 3 servers in show radius-server")

    if not validate_radius_servers(dut):
        failures.append("RADIUS servers with priority validation failed")

    # ── Report ───────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.2 STEP 1 PASSED: 3 RADIUS servers configured with priorities")
        st.report_pass("test_case_passed",
                       "Multiple RADIUS servers configured with correct priorities")


@pytest.mark.radius
def test_radius_4_1_2_configure_aaa_with_tacacs():
    """
    TC 4.1.2 - STEP 2: Configure AAA authentication + TACACS+ global params.

    Test Steps:
      1. Configure TACACS+ (must be done FIRST to create passkey):
           tacacs-server passkey Test123
           tacacs-server source-interface Ethernet4
           tacacs-server authtype chap
           tacacs-server timeout 40
           tacacs-server host 192.168.100.87
      2. Configure AAA (requires TACACS+ passkey to exist):
           aaa authentication failthrough enable
           aaa authentication fallback enable
           aaa authentication login default group tacacs+ local
      3. Validate show aaa:
           - failthrough : enabled
           - fallback    : enabled
           - login-method: tacacs+
      4. Validate show tacacs-server:
           - Source Interface: Ethernet4
           - Authentication Type: CHAP
           - Global Timeout: 40
           - Key Configured: Yes
           - Host 192.168.100.87 present on port 49

    Expected Result: AAA and TACACS+ configured and visible in show outputs
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 2: Configure AAA Authentication + TACACS+ Global Params")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 2: Configuration ──────────────────────────────────────
    st.log("MODULE 2: Configuration Phase")

    st.log("STEP 1: Configure TACACS+ global parameters")
    if not configure_tacacs_params(dut):
        failures.append("Failed to configure TACACS+ parameters")
    st.log("✅ MODULE 2 STEP 1 completed")
    st.log("STEP 2: Configure AAA authentication (failthrough + fallback + tacacs+)")
    if not configure_aaa_authentication(dut):
        failures.append("Failed to configure AAA authentication")
    st.log("✅ MODULE 2 STEP 2 completed")

    # ── MODULE 3: Validation ─────────────────────────────────────────
    st.log("MODULE 3: Validation Phase")

    st.log("STEP 3: Validate show aaa output")
    if not validate_aaa_configuration(dut):
        failures.append("AAA configuration validation failed")
    st.log("✅ MODULE 3 STEP 3 completed")

    st.log("STEP 4: Validate show tacacs-server output")
    if not validate_tacacs_configuration(dut):
        failures.append("TACACS+ configuration validation failed")
    st.log("✅ MODULE 3 STEP 4 completed")

    # ── Report ───────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.2 STEP 2 PASSED: AAA + TACACS+ configured and verified")
        st.report_pass("test_case_passed",
                       "AAA authentication and TACACS+ global params configured and verified")


@pytest.mark.radius
def test_radius_4_1_2_verify_combined_config():
    """
    TC 4.1.2 - STEP 3: Verify combined RADIUS + AAA + TACACS+ configuration.

    Test Steps:
      1. Validate show radius-server — all 3 RADIUS servers still present
      2. Validate show aaa           — failthrough + fallback + login-method
      3. Validate show tacacs-server — source-interface + auth-type + timeout + key + host

    Expected Result: All configurations co-exist correctly with no conflicts
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 3: Verify Combined RADIUS + AAA + TACACS+ Configuration")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 3: Validation ─────────────────────────────────────────
    st.log("MODULE 3: Validation Phase — Combined configuration check")

    st.log("STEP 1: Validate RADIUS servers still present (no conflict with TACACS+)")
    if not validate_radius_servers(dut):
        failures.append("RADIUS server validation failed in combined config check")
    st.log("✅ MODULE 3 STEP 1 completed")

    st.log("STEP 2: Validate AAA configuration")
    if not validate_aaa_configuration(dut):
        failures.append("AAA validation failed in combined config check")
    st.log("✅ MODULE 3 STEP 2 completed")

    st.log("STEP 3: Validate TACACS+ configuration")
    if not validate_tacacs_configuration(dut):
        failures.append("TACACS+ validation failed in combined config check")
    st.log("✅ MODULE 3 STEP 3 completed")

    # ── Report ───────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.2 STEP 3 PASSED: Combined RADIUS + AAA + TACACS+ verified")
        st.report_pass("test_case_passed",
                       "Combined RADIUS, AAA and TACACS+ configuration verified successfully")
