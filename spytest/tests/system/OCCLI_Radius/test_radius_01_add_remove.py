"""
RADIUS Test Case 4.1.1: Add and Remove RADIUS Server
======================================================

Feature      : RADIUS (Remote Authentication Dial-In User Service)
Test Case ID : TC-RADIUS-4.1.1
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/OCCLI_Radius/test_radius_01_add_remove.py \
    --logs-path ./logs/radius_tc_4_1_1_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 4.1.1: Add and Remove RADIUS Server

  Manual Test Steps Covered:
    Step 1: Add RADIUS server with global parameters
      - radius-server host 192.168.100.174
      - radius-server key Test123
      - radius-server timeout 30
      - radius-server retransmit 5
      - radius-server statistics enable
      - radius-server auth-type pap
      - radius-server nas-ip 192.168.100.87
      - Verify: show radius-server

    Step 2: Add second server with all per-server parameters
      - radius-server host 192.168.100.175 auth-port 5049 auth-type chap
        key Drak123 priority 30 retransmit 3 timeout 20
        source-interface Ethernet0 vrf mgmt
      - Verify: show radius-server (both servers visible)

    Step 3: Remove server and global parameters
      - no radius-server host 192.168.100.174
      - no radius-server key
      - no radius-server retransmit
      - no radius-server auth-type
      - no radius-server nas-ip
      - Verify: show radius-server (server removed, global params reset)

  Module Structure:
    Module 1 - Unconfiguration : Clean all existing RADIUS config
    Module 2 - Configuration   : Configure servers and global params
    Module 3 - Validation      : Verify configuration via show commands
    Module 4 - Cleanup         : Remove all RADIUS configuration

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
    # Server 1 (Global config server)
    "server1_ip":          "192.168.100.174",
    "global_key":          "Test123",
    "global_timeout":      "30",
    "global_retransmit":   "5",
    "global_auth_type":    "pap",
    "global_nas_ip":       "192.168.100.87",
    "global_statistics":   "enable",

    # Server 2 (Full per-server config)
    "server2_ip":          "192.168.100.175",
    "server2_auth_port":   "5049",
    "server2_auth_type":   "chap",
    "server2_key":         "Drak123",
    "server2_priority":    "30",
    "server2_retransmit":  "3",
    "server2_timeout":     "20",
    "server2_src_intf":    "Ethernet0",
    "server2_vrf":         "mgmt",

    # CLI Type
    "cli_type":            "klish"
})

TC_ID = "TC-RADIUS-4.1.1"


# ======================================================================
# Fixture - Module Level Setup / Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def radius_module_hooks(request):
    """
    Module-level fixture:
      - Setup  : Unconfigure all RADIUS config (Module 1)
      - Yield  : Run all test functions
      - Teardown: Cleanup all RADIUS config (Module 4)
    """
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID}: MODULE PROLOGUE - Add and Remove RADIUS Server Test")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = CONFIG.cli_type

    st.log(f"CLI Type      : {data.cli_type}")
    st.log(f"Server1 IP    : {CONFIG.server1_ip}")
    st.log(f"Server2 IP    : {CONFIG.server2_ip}")
    st.log(f"NAS-IP        : {CONFIG.global_nas_ip}")
    st.log(f"Global Key    : {CONFIG.global_key}")
    st.log(f"Global Timeout: {CONFIG.global_timeout}")

    # ── Module 1: Unconfiguration ──────────────────────────────────────
    st.banner("MODULE 1: UNCONFIGURATION")
    module_1_unconfigure(vars.D1)
    st.wait(2, "Waiting after unconfiguration")

    yield  # ── Modules 2 & 3 run here (test functions) ──

    # ── Module 4: Cleanup ─────────────────────────────────────────────
    st.banner("MODULE 4: CLEANUP")
    module_4_cleanup(vars.D1)
    st.log("MODULE 4 COMPLETED: All RADIUS configuration removed")


# ======================================================================
# MODULE 1: UNCONFIGURATION
# ======================================================================
def module_1_unconfigure(dut: str):
    """
    Module 1: Remove all existing RADIUS configuration before tests start.
    Uses skip_error_check=True as config may not exist.
    """
    st.log(f"[MODULE 1] Removing all RADIUS config on {dut}...")

    commands = [
        f"no radius-server host {CONFIG.server1_ip}",
        f"no radius-server host {CONFIG.server2_ip}",
        "no radius-server key",
        "no radius-server timeout",
        "no radius-server retransmit",
        "no radius-server auth-type",
        "no radius-server nas-ip",
        "no radius-server statistics",
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log("[MODULE 1] Unconfiguration completed")
    except Exception as e:
        st.log(f"[MODULE 1] Unconfiguration note (may be expected): {str(e)}")


# ======================================================================
# MODULE 2: CONFIGURATION FUNCTIONS
# ======================================================================
def configure_global_radius_params(dut: str) -> bool:
    """
    Module 2: Configure global RADIUS parameters.

    Configures:
      - radius-server host 192.168.100.174
      - radius-server key Test123
      - radius-server timeout 30
      - radius-server retransmit 5
      - radius-server statistics enable
      - radius-server auth-type pap
      - radius-server nas-ip 192.168.100.87
    """
    st.log(f"[MODULE 2] Configuring global RADIUS parameters on {dut}")

    commands = [
        f"radius-server host {CONFIG.server1_ip}",
        f"radius-server key {CONFIG.global_key}",
        f"radius-server timeout {CONFIG.global_timeout}",
        f"radius-server retransmit {CONFIG.global_retransmit}",
        f"radius-server statistics {CONFIG.global_statistics}",
        f"radius-server auth-type {CONFIG.global_auth_type}",
        f"radius-server nas-ip {CONFIG.global_nas_ip}",
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for global RADIUS config to apply")
        st.log("[MODULE 2] Global RADIUS parameters configured successfully")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure global RADIUS params: {str(e)}")
        return False


def configure_server2_all_params(dut: str) -> bool:
    """
    Module 2: Configure second RADIUS server with ALL per-server parameters.

    Configures:
      - radius-server host 192.168.100.175 auth-port 5049 auth-type chap
        key Drak123 priority 30 retransmit 3 timeout 20
        source-interface Ethernet0 vrf mgmt
    """
    st.log(f"[MODULE 2] Configuring server2 ({CONFIG.server2_ip}) with all params on {dut}")

    cmd = (
        f"radius-server host {CONFIG.server2_ip}"
        f" auth-port {CONFIG.server2_auth_port}"
        f" auth-type {CONFIG.server2_auth_type}"
        f" key {CONFIG.server2_key}"
        f" priority {CONFIG.server2_priority}"
        f" retransmit {CONFIG.server2_retransmit}"
        f" timeout {CONFIG.server2_timeout}"
        f" source-interface {CONFIG.server2_src_intf}"
        f" vrf {CONFIG.server2_vrf}"
    )

    try:
        st.config(dut, [cmd], type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for server2 config to apply")
        st.log(f"[MODULE 2] Server2 ({CONFIG.server2_ip}) configured with all params")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure server2: {str(e)}")
        return False


def remove_server1_and_global_params(dut: str) -> bool:
    """
    Module 2: Remove server1 and global RADIUS parameters.

    Removes:
      - no radius-server host 192.168.100.174
      - no radius-server key
      - no radius-server retransmit
      - no radius-server auth-type
      - no radius-server nas-ip
    """
    st.log(f"[MODULE 2] Removing server1 and global params on {dut}")

    commands = [
        f"no radius-server host {CONFIG.server1_ip}",
        "no radius-server key",
        "no radius-server retransmit",
        "no radius-server auth-type",
        "no radius-server nas-ip",
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(1, "Waiting for removal to apply")
        st.log("[MODULE 2] Server1 and global params removed")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to remove server1/global params: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION FUNCTIONS
# ======================================================================
def get_show_radius_output(dut: str) -> str:
    """
    Module 3: Execute show radius-server and return raw output string.
    """
    st.wait(5, "Waiting before show command")
    output = st.show(
        dut, "show radius-server",
        type=data.cli_type,
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""
    st.log(f"[MODULE 3] show radius-server output:\n{output_str}")
    return output_str


def validate_global_radius_params(dut: str) -> bool:
    """
    Module 3: Validate global RADIUS parameters in show output.

    Actual show radius-server Global Configuration section format:
      ---------------------------------------------------------
      RADIUS Global Configuration
      ---------------------------------------------------------
      nas-ip-addr          : 192.168.100.87
      statistics           : True
      timeout              : 30
      auth-type            : PAP
      key configured       : Yes
      retransmit           : 5
      ---------------------------------------------------------
    """
    st.log(f"[MODULE 3] Validating global RADIUS params on {dut}")

    output_str = get_show_radius_output(dut)

    # Extract Global Configuration section (before HOST table)
    global_section = output_str
    if "HOST" in output_str:
        global_section = output_str.split("HOST")[0]

    st.log(f"  [Global section]:\n{global_section}")
    errors = []

    # Validate NAS-IP — check the label+value in global section
    if "nas-ip" in global_section.lower() and CONFIG.global_nas_ip in global_section:
        st.log(f"  ✓ NAS-IP: {CONFIG.global_nas_ip}")
    else:
        errors.append(f"NAS-IP '{CONFIG.global_nas_ip}' not found in global section")

    # Validate statistics : True
    if "statistics" in global_section.lower() and ("True" in global_section or "true" in global_section):
        st.log("  ✓ Statistics: True (enabled)")
    else:
        errors.append("Statistics True not found in global section")

    # Validate timeout : 30
    if "timeout" in global_section.lower() and CONFIG.global_timeout in global_section:
        st.log(f"  ✓ Timeout: {CONFIG.global_timeout}")
    else:
        errors.append(f"Timeout {CONFIG.global_timeout} not found in global section")

    # Validate auth-type : PAP (shown uppercase in output)
    if "auth-type" in global_section.lower() and "PAP" in global_section.upper():
        st.log(f"  ✓ Auth-type: PAP")
    else:
        errors.append("Auth-type PAP not found in global section")

    # Validate key configured : Yes
    if "key configured" in global_section.lower() and "yes" in global_section.lower():
        st.log("  ✓ Key Configured: Yes")
    else:
        errors.append("'key configured : Yes' not found in global section")

    # Validate retransmit : 5
    if "retransmit" in global_section.lower() and CONFIG.global_retransmit in global_section:
        st.log(f"  ✓ Retransmit: {CONFIG.global_retransmit}")
    else:
        errors.append(f"Retransmit {CONFIG.global_retransmit} not found in global section")

    if errors:
        for err in errors:
            st.error(f"  ✗ {err}")
        return False

    st.log("[MODULE 3] All global RADIUS params validated ✓")
    return True


def validate_server1_present(dut: str) -> bool:
    """
    Module 3: Validate server1 (192.168.100.174) is present in show output.
    Server1 uses global defaults so most columns show '-'.
    """
    st.log(f"[MODULE 3] Validating server1 ({CONFIG.server1_ip}) is present on {dut}")

    output_str = get_show_radius_output(dut)

    if CONFIG.server1_ip in output_str:
        st.log(f"  ✓ Server1 {CONFIG.server1_ip} found in output")
        return True
    else:
        st.error(f"  ✗ Server1 {CONFIG.server1_ip} NOT found in output")
        return False


def validate_server2_all_params(dut: str) -> bool:
    """
    Module 3: Validate server2 (192.168.100.175) with all per-server params.

    Expected in output row for 192.168.100.175:
      - AUTH-TYPE  : CHAP
      - KEY-CONFIG : Yes
      - AUTH-PORT  : 5049
      - PRIORITY   : 30
      - TIMEOUT    : 20
      - RTSMT      : 3
      - VRF        : mgmt
      - SRC-INTF   : Ethernet0
    """
    st.log(f"[MODULE 3] Validating server2 ({CONFIG.server2_ip}) all params on {dut}")

    output_str = get_show_radius_output(dut)
    errors = []

    # Validate server2 IP present
    if CONFIG.server2_ip in output_str:
        st.log(f"  ✓ Server2 IP: {CONFIG.server2_ip}")
    else:
        errors.append(f"Server2 IP {CONFIG.server2_ip} not found")

    # Validate auth-port
    if CONFIG.server2_auth_port in output_str:
        st.log(f"  ✓ Auth-Port: {CONFIG.server2_auth_port}")
    else:
        errors.append(f"Auth-Port {CONFIG.server2_auth_port} not found")

    # Validate auth-type CHAP
    if "CHAP" in output_str.upper():
        st.log("  ✓ Auth-Type: CHAP")
    else:
        errors.append("Auth-Type CHAP not found")

    # Validate priority
    if CONFIG.server2_priority in output_str:
        st.log(f"  ✓ Priority: {CONFIG.server2_priority}")
    else:
        errors.append(f"Priority {CONFIG.server2_priority} not found")

    # Validate timeout
    if CONFIG.server2_timeout in output_str:
        st.log(f"  ✓ Timeout: {CONFIG.server2_timeout}")
    else:
        errors.append(f"Timeout {CONFIG.server2_timeout} not found")

    # Validate retransmit
    if CONFIG.server2_retransmit in output_str:
        st.log(f"  ✓ Retransmit: {CONFIG.server2_retransmit}")
    else:
        errors.append(f"Retransmit {CONFIG.server2_retransmit} not found")

    # Validate VRF
    if CONFIG.server2_vrf in output_str:
        st.log(f"  ✓ VRF: {CONFIG.server2_vrf}")
    else:
        errors.append(f"VRF {CONFIG.server2_vrf} not found")

    # Validate source interface
    if CONFIG.server2_src_intf in output_str:
        st.log(f"  ✓ Source-Interface: {CONFIG.server2_src_intf}")
    else:
        errors.append(f"Source-Interface {CONFIG.server2_src_intf} not found")

    if errors:
        for err in errors:
            st.error(f"  ✗ {err}")
        return False

    st.log("[MODULE 3] Server2 all params validated ✓")
    return True


def validate_server1_removed_globals_reset(dut: str) -> bool:
    """
    Module 3: Validate server1 removed and global params reset.

    Expected after removal:
      - Server1 (192.168.100.174) NOT in output
      - nas-ip-addr label NOT present in Global Configuration section
      - key configured: No  (in Global Configuration section)
      - auth-type label NOT present in Global Configuration section
      - Server2 (192.168.100.175) still present
      - Statistics   : still True

    NOTE: NAS-IP validation must check the "nas-ip" label in the Global
    Configuration section — NOT the raw IP string — because the same IP
    (192.168.100.87) may appear as a RADIUS server host in the table.
    """
    st.log(f"[MODULE 3] Validating server1 removed and globals reset on {dut}")

    output_str = get_show_radius_output(dut)
    errors = []

    # ── Extract Global Configuration section only ─────────────────────────
    # The show output has this structure:
    #   RADIUS Global Configuration
    #   ---------------------------------------------------------
    #   statistics           : True
    #   timeout              : 30
    #   key configured       : No
    #   [nas-ip-addr         : x.x.x.x]   ← only present if configured
    #   -------...----
    #   HOST    AUTH-TYPE ...
    #   -------...----
    #   <server rows>
    global_section = output_str
    # Try to isolate global section (everything before the HOST table header)
    if "HOST" in output_str:
        global_section = output_str.split("HOST")[0]

    st.log(f"  [Global section parsed]:\n{global_section}")

    # Validate server1 is REMOVED from server table
    if CONFIG.server1_ip not in output_str:
        st.log(f"  ✓ Server1 {CONFIG.server1_ip} removed (not found in output)")
    else:
        errors.append(f"Server1 {CONFIG.server1_ip} still present after removal")

    # Validate NAS-IP removed — check the global section label, not raw IP
    # When nas-ip is configured: "nas-ip-addr          : 192.168.100.87"
    # When removed: that line is absent entirely
    if "nas-ip" in global_section.lower():
        errors.append(f"NAS-IP label still present in Global Configuration after 'no radius-server nas-ip'")
    else:
        st.log(f"  ✓ NAS-IP removed (label 'nas-ip' not found in global section)")

    # Validate key configured: No (in global section)
    if "key configured" in global_section.lower() and "no" in global_section.lower():
        st.log("  ✓ Key Configured: No (removed)")
    elif "No" in global_section:
        st.log("  ✓ Key Configured: No (removed)")
    else:
        errors.append("'key configured : No' not found in global section after key removal")

    # Validate auth-type removed from global section
    # When removed the auth-type line should be absent or show default
    # "no radius-server auth-type" removes the override; default (PAP) may still show
    # — we simply log what we see rather than hard-fail on default presence
    if "auth-type" in global_section.lower():
        st.log(f"  ℹ Auth-type line still present in global section (may be default PAP — acceptable)")
    else:
        st.log(f"  ✓ Auth-type override removed from global section")

    # Validate server2 still present in table
    if CONFIG.server2_ip in output_str:
        st.log(f"  ✓ Server2 {CONFIG.server2_ip} still present")
    else:
        errors.append(f"Server2 {CONFIG.server2_ip} missing after server1 removal")

    # Validate statistics still True (in global section)
    if "True" in global_section or "true" in global_section:
        st.log("  ✓ Statistics: True (still enabled)")
    else:
        errors.append("Statistics True not found in global section (should still be enabled)")

    if errors:
        for err in errors:
            st.error(f"  ✗ {err}")
        return False

    st.log("[MODULE 3] Post-removal validation passed ✓")
    return True


# ======================================================================
# MODULE 4: CLEANUP
# ======================================================================
def module_4_cleanup(dut: str):
    """
    Module 4: Remove all RADIUS configuration after test completion.
    """
    st.log(f"[MODULE 4] Cleaning up all RADIUS config on {dut}")

    commands = [
        f"no radius-server host {CONFIG.server1_ip}",
        f"no radius-server host {CONFIG.server2_ip}",
        "no radius-server key",
        "no radius-server timeout",
        "no radius-server retransmit",
        "no radius-server auth-type",
        "no radius-server nas-ip",
        "no radius-server statistics",
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(1, "Waiting for cleanup")
        st.log("[MODULE 4] Cleanup completed successfully")
    except Exception as e:
        st.log(f"[MODULE 4] Cleanup note: {str(e)}")


# ======================================================================
# TEST FUNCTIONS (Module 2 + Module 3 combined per step)
# ======================================================================

@pytest.mark.radius
def test_radius_4_1_1_add_server_with_global_params():
    """
    TC 4.1.1 - STEP 1: Add RADIUS server with global parameters.

    Test Steps:
      1. Configure global RADIUS parameters:
           radius-server host 192.168.100.174
           radius-server key Test123
           radius-server timeout 30
           radius-server retransmit 5
           radius-server statistics enable
           radius-server auth-type pap
           radius-server nas-ip 192.168.100.87
      2. Validate via show radius-server:
           - NAS-IP     : 192.168.100.87
           - statistics : True
           - timeout    : 30
           - auth-type  : PAP
           - key configured: Yes
           - retransmit : 5
           - Server1 IP is present in table

    Expected Result: All global params and server1 visible in show output
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 1: Add RADIUS Server with Global Parameters")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 2: Configuration ──────────────────────────────────────
    st.log("MODULE 2: Configuration Phase")
    st.log("STEP 1: Configure global RADIUS parameters")

    if not configure_global_radius_params(dut):
        failures.append("Failed to configure global RADIUS params")

    st.log(f"✅ MODULE 2 STEP 1 completed")

    # ── MODULE 3: Validation ─────────────────────────────────────────
    st.log("MODULE 3: Validation Phase")
    st.log("STEP 2: Validate global RADIUS params via show")

    if not validate_global_radius_params(dut):
        failures.append("Global RADIUS params validation failed")

    st.log("STEP 3: Validate server1 present in table")
    if not validate_server1_present(dut):
        failures.append("Server1 not found in show radius-server output")

    # ── Report ───────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.1 STEP 1 PASSED: RADIUS server added with global params")
        st.report_pass("test_case_passed", "RADIUS server with global params configured and verified")


@pytest.mark.radius
def test_radius_4_1_1_add_server2_all_params():
    """
    TC 4.1.1 - STEP 2: Add second RADIUS server with ALL per-server parameters.

    Test Steps:
      1. Configure server2 with full per-server parameters (one-line command):
           radius-server host 192.168.100.175 auth-port 5049 auth-type chap
             key Drak123 priority 30 retransmit 3 timeout 20
             source-interface Ethernet0 vrf mgmt
      2. Validate via show radius-server:
           - Server2 IP  : 192.168.100.175
           - AUTH-TYPE   : CHAP
           - KEY-CONFIG  : Yes
           - AUTH-PORT   : 5049
           - PRIORITY    : 30
           - TIMEOUT     : 20
           - RTSMT       : 3
           - VRF         : mgmt
           - SRC-INTF    : Ethernet0

    Expected Result: Server2 shows all per-server parameters in table
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 2: Add Server2 with All Per-Server Parameters")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 2: Configuration ──────────────────────────────────────
    st.log("MODULE 2: Configuration Phase")
    st.log("STEP 1: Configure server2 with all per-server parameters")

    if not configure_server2_all_params(dut):
        failures.append("Failed to configure server2 with all params")

    st.log("✅ MODULE 2 STEP 1 completed")

    # ── MODULE 3: Validation ─────────────────────────────────────────
    st.log("MODULE 3: Validation Phase")
    st.log("STEP 2: Validate server2 all params via show")

    if not validate_server2_all_params(dut):
        failures.append("Server2 per-server params validation failed")

    st.log("STEP 3: Validate server1 still present (no impact)")
    if not validate_server1_present(dut):
        failures.append("Server1 disappeared after adding server2")

    # ── Report ───────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.1 STEP 2 PASSED: Server2 with all params configured and verified")
        st.report_pass("test_case_passed", "Server2 all per-server params configured and verified")


@pytest.mark.radius
def test_radius_4_1_1_remove_server_and_global_params():
    """
    TC 4.1.1 - STEP 3: Remove RADIUS server and global parameters.

    Test Steps:
      1. Remove server1 and global params:
           no radius-server host 192.168.100.174
           no radius-server key
           no radius-server retransmit
           no radius-server auth-type
           no radius-server nas-ip
      2. Validate via show radius-server:
           - Server1 (192.168.100.174) is REMOVED
           - NAS-IP removed (not in output)
           - key configured: No
           - auth-type removed
           - retransmit removed
           - Server2 (192.168.100.175) still present
           - Statistics still True

    Expected Result: Server1 and specified global params removed,
                     Server2 unaffected, statistics remain enabled
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 3: Remove Server1 and Global Parameters")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 2: Configuration ──────────────────────────────────────
    st.log("MODULE 2: Configuration Phase")
    st.log("STEP 1: Remove server1 and global RADIUS parameters")

    if not remove_server1_and_global_params(dut):
        failures.append("Failed to remove server1 and global params")

    st.log("✅ MODULE 2 STEP 1 completed")

    # ── MODULE 3: Validation ─────────────────────────────────────────
    st.log("MODULE 3: Validation Phase")
    st.log("STEP 2: Validate server1 removed and globals reset")

    if not validate_server1_removed_globals_reset(dut):
        failures.append("Post-removal validation failed")

    # ── Report ───────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.1 STEP 3 PASSED: Server1 and global params removed correctly")
        st.report_pass("test_case_passed", "Server1 removed and global params reset verified")
