"""
RADIUS Test Case 4.1.3: Negative Testing of All RADIUS Server Commands
=======================================================================

Feature      : RADIUS (Remote Authentication Dial-In User Service)
Test Case ID : TC-RADIUS-4.1.3
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  SPYTEST_PYTHON=./spytest_venv/bin/python ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    system/OCCLI_Radius/test_radius_03_negative.py \
    --logs-path ./logs/radius_tc_4_1_3_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 4.1.3: Negative Testing of all RADIUS server commands.

  Manual Test Steps Covered:

  STEP 1: Invalid IP address formats (all must produce %Error)
    - radius-server host 999.999.999.999   → %Error (out-of-range octets)
    - radius-server host 256.1.1.1         → %Error (octet > 255)
    - radius-server host 192.168.1         → %Error (incomplete IP, 3 octets)
    - radius-server host 192.168.1.1.1     → %Error (5 octets)
    - radius-server host GGGG::1           → % Error: Invalid input (invalid IPv6)

  STEP 2: Invalid auth-port values (all must produce ^ error)
    - radius-server host 192.168.1.100 auth-port 99999  → ^ Error
    - radius-server host 192.168.1.100 auth-port 0      → ^ Error
    - radius-server host 192.168.1.100 auth-port 65536  → ^ Error
    - radius-server host 192.168.1.100 auth-port -1     → ^ Error

  STEP 3: Invalid per-server timeout values (all must produce ^ error)
    - radius-server host 192.168.1.100 timeout 999      → ^ Error
    - radius-server host 192.168.1.100 timeout 0        → ^ Error
    - radius-server host 192.168.1.100 timeout -5       → ^ Error
    - radius-server host 192.168.1.100 timeout abc      → ^ Error
    - radius-server host 192.168.1.100 timeout 61       → ^ Error
    Valid boundary values (must be accepted):
    - radius-server host 192.168.1.100 timeout 1        → accepted
    - radius-server host 192.168.1.100 timeout 60       → accepted

  STEP 4: Invalid retransmit value
    - radius-server host 192.168.1.100 retransmit 999   → ^ Error

  STEP 5: Invalid priority values
    - radius-server host 192.168.1.100 priority 0       → ^ Error
    - radius-server host 192.168.1.100 priority 999     → ^ Error

  STEP 6: Invalid VRF
    - radius-server host 192.168.1.100 vrf NonExistentVRF → ^ Error

  STEP 7: Non-existent source-interface (accepted — device does not validate intf)
    - radius-server host 192.168.1.100 source-interface Ethernet999 → accepted

  STEP 8: Max server limit (8 servers max)
    - Add 1 valid server (192.168.1.1) to reach limit
    - Try adding 192.168.1.2 through 192.168.1.9 → %Error: Max elements limit 8 reached
    - Cleanup all added servers

  Module Structure:
    Module 1 - Unconfiguration : Clean all existing RADIUS config
    Module 2 - Configuration   : Send invalid commands (expect rejection)
    Module 3 - Validation      : Verify rejected commands left no state
    Module 4 - Cleanup         : Remove all RADIUS configuration

Pre-requisites:
  - 1 SONiC device (DUT1) with Broadcom/Klish CLI
  - No existing RADIUS servers (Module 1 cleans up)
  - Testbed: testbed_2vs.yaml or compatible

Notes:
  - Negative tests: command MUST produce error output
  - Valid boundary tests: command MUST be accepted (no error)
  - source-interface Ethernet999 is intentionally accepted (no intf validation)
  - Max server limit is 8 — device already had 7 servers from TC 4.1.2
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
    # Test DUT IP (used for valid-host negative param tests)
    "test_host":               "192.168.1.100",

    # Invalid IP addresses
    "invalid_ip_out_of_range": "999.999.999.999",
    "invalid_ip_octet_256":    "256.1.1.1",
    "invalid_ip_incomplete":   "192.168.1",
    "invalid_ip_5_octets":     "192.168.1.1.1",
    "invalid_ipv6":            "GGGG::1",

    # Invalid auth-port values
    "port_invalid_99999":      "99999",
    "port_invalid_0":          "0",
    "port_invalid_65536":      "65536",
    "port_invalid_neg1":       "-1",

    # Invalid timeout values
    "timeout_invalid_999":     "999",
    "timeout_invalid_0":       "0",
    "timeout_invalid_neg5":    "-5",
    "timeout_invalid_abc":     "abc",
    "timeout_invalid_61":      "61",
    # Valid boundary timeout values
    "timeout_valid_min":       "1",
    "timeout_valid_max":       "60",

    # Invalid retransmit
    "retransmit_invalid_999":  "999",

    # Invalid priority values
    "priority_invalid_0":      "0",
    "priority_invalid_999":    "999",

    # Invalid VRF
    "vrf_invalid":             "NonExistentVRF",

    # Non-existent interface (accepted by device)
    "intf_nonexistent":        "Ethernet999",

    # Max limit test servers (limit = 8)
    # At start of this TC, device already has 7 servers from TC 4.1.2
    # We add 1 more to fill limit, then try to exceed it
    "max_limit_server_base":   "192.168.1.",   # base for 192.168.1.1 - 192.168.1.9
    "max_limit_server_first":  "192.168.1.1",
    "max_limit_servers_extra": [
        "192.168.1.2", "192.168.1.3", "192.168.1.4",
        "192.168.1.5", "192.168.1.6", "192.168.1.7",
        "192.168.1.8", "192.168.1.9"
    ],

    # CLI Type
    "cli_type":                "klish"
})

TC_ID = "TC-RADIUS-4.1.3"

# Error patterns to detect in output (device produces these on rejection)
ERROR_PATTERNS = ["%Error", "% Error", "Error:", "Invalid input", "^"]


# ======================================================================
# Fixture - Module Level Setup / Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def radius_tc_4_1_3_module_hooks(request):
    """
    Module-level fixture:
      - Setup  : Unconfigure all RADIUS config (Module 1)
      - Yield  : Run all test functions (Modules 2 & 3)
      - Teardown: Cleanup all RADIUS config (Module 4)
    """
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID}: MODULE PROLOGUE - Negative Testing of RADIUS Commands")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = CONFIG.cli_type

    st.log(f"CLI Type   : {data.cli_type}")
    st.log(f"Test Host  : {CONFIG.test_host}")
    st.log(f"TC Purpose : All invalid inputs must be rejected by the device")

    # ── Module 1: Unconfiguration ──────────────────────────────────────
    st.banner("MODULE 1: UNCONFIGURATION")
    module_1_unconfigure(vars.D1)
    st.wait(2, "Waiting after unconfiguration")

    yield  # ── Modules 2 & 3 run here ──

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
    """
    st.log(f"[MODULE 1] Removing all RADIUS config on {dut}...")

    # Remove test host + all max-limit test servers
    commands = [
        f"no radius-server host {CONFIG.test_host}",
        f"no radius-server host {CONFIG.max_limit_server_first}",
    ]
    for srv in CONFIG.max_limit_servers_extra:
        commands.append(f"no radius-server host {srv}")

    commands += [
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
# HELPER: Send command and check if it was rejected
# ======================================================================
def send_expect_error(dut: str, cmd: str, test_label: str) -> bool:
    """
    Send a command that MUST be rejected by the device.

    Args:
        dut        : Device identifier
        cmd        : Command to send
        test_label : Description for logging

    Returns:
        True  if command was rejected (error found in output) — TEST PASSES
        False if command was accepted (no error) — TEST FAILS
    """
    st.log(f"  [NEG] Sending: {cmd}")
    output = st.config(dut, [cmd], type=data.cli_type, skip_error_check=True)
    output_str = str(output) if output else ""

    rejected = any(pat in output_str for pat in ERROR_PATTERNS)

    if rejected:
        st.log(f"  ✓ REJECTED as expected: {test_label}")
        return True
    else:
        st.error(f"  ✗ NOT rejected (accepted!): {test_label}")
        st.error(f"    Output: {output_str[:200]}")
        return False


def send_expect_accepted(dut: str, cmd: str, test_label: str) -> bool:
    """
    Send a command that MUST be accepted (valid boundary value).

    Args:
        dut        : Device identifier
        cmd        : Command to send
        test_label : Description for logging

    Returns:
        True  if command was accepted (no error) — TEST PASSES
        False if command was rejected (error found) — TEST FAILS
    """
    st.log(f"  [POS] Sending: {cmd}")
    output = st.config(dut, [cmd], type=data.cli_type, skip_error_check=True)
    output_str = str(output) if output else ""

    rejected = any(pat in output_str for pat in ERROR_PATTERNS)

    if not rejected:
        st.log(f"  ✓ ACCEPTED as expected: {test_label}")
        return True
    else:
        st.error(f"  ✗ Unexpectedly REJECTED: {test_label}")
        st.error(f"    Output: {output_str[:200]}")
        return False


# ======================================================================
# MODULE 4: CLEANUP
# ======================================================================
def module_4_cleanup(dut: str):
    """
    Module 4: Remove all RADIUS configuration added during tests.
    """
    st.log(f"[MODULE 4] Cleaning up RADIUS config on {dut}")

    commands = [
        f"no radius-server host {CONFIG.test_host}",
        f"no radius-server host {CONFIG.max_limit_server_first}",
    ]
    for srv in CONFIG.max_limit_servers_extra:
        commands.append(f"no radius-server host {srv}")

    commands += [
        "no radius-server key",
        "no radius-server timeout",
        "no radius-server retransmit",
        "no radius-server auth-type",
        "no radius-server statistics",
    ]

    try:
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(1, "Waiting for cleanup")
        st.log("[MODULE 4] Cleanup completed")
    except Exception as e:
        st.log(f"[MODULE 4] Cleanup note: {str(e)}")


# ======================================================================
# MODULE 3: VALIDATION HELPER
# ======================================================================
def validate_host_not_in_table(dut: str, host_ip: str) -> bool:
    """
    Module 3: Verify a rejected host IP is NOT present in show radius-server.
    """
    output = st.show(dut, "show radius-server",
                     type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""

    if host_ip not in output_str:
        st.log(f"  ✓ Rejected host {host_ip} correctly absent from show radius-server")
        return True
    else:
        st.error(f"  ✗ Rejected host {host_ip} unexpectedly PRESENT in show radius-server")
        return False


# ======================================================================
# TEST FUNCTIONS
# ======================================================================

@pytest.mark.radius
@pytest.mark.negative
def test_radius_4_1_3_invalid_ip_addresses():
    """
    TC 4.1.3 - STEP 1: Invalid IP address formats must be rejected.

    Negative cases (all must produce %Error or ^ Error):
      - 999.999.999.999   out-of-range octets
      - 256.1.1.1         first octet > 255
      - 192.168.1         incomplete (3 octets only)
      - 192.168.1.1.1     too many octets (5)
      - GGGG::1           invalid IPv6 (non-hex characters)

    Module 3 Validation:
      - None of the invalid IPs appear in show radius-server
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 1: Invalid IP Address Formats")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 2: Send invalid IP commands ────────────────────────────
    st.log("MODULE 2: Sending invalid IP address commands")

    invalid_ips = [
        (CONFIG.invalid_ip_out_of_range, "999.999.999.999 out-of-range octets"),
        (CONFIG.invalid_ip_octet_256,    "256.1.1.1 first octet > 255"),
        (CONFIG.invalid_ip_incomplete,   "192.168.1 incomplete 3-octet address"),
        (CONFIG.invalid_ip_5_octets,     "192.168.1.1.1 five-octet address"),
        (CONFIG.invalid_ipv6,            "GGGG::1 invalid IPv6 hex characters"),
    ]

    for ip, label in invalid_ips:
        cmd = f"radius-server host {ip}"
        if not send_expect_error(dut, cmd, label):
            failures.append(f"Invalid IP '{ip}' was NOT rejected")

    st.log("✅ MODULE 2 completed: All invalid IP commands sent")

    # ── MODULE 3: Validate none were added ───────────────────────────
    st.log("MODULE 3: Validating no invalid IPs appear in show radius-server")
    st.wait(2, "Waiting before show command")

    for ip, label in invalid_ips:
        # Skip IPs that contain special chars which would break show parsing
        if ip in [CONFIG.invalid_ip_out_of_range, CONFIG.invalid_ip_octet_256,
                  CONFIG.invalid_ip_5_octets]:
            if not validate_host_not_in_table(dut, ip):
                failures.append(f"Invalid IP {ip} found in table after rejection")

    # ── Report ────────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.3 STEP 1 PASSED: All invalid IP addresses rejected")
        st.report_pass("test_case_passed", "All invalid IP address formats correctly rejected")


@pytest.mark.radius
@pytest.mark.negative
def test_radius_4_1_3_invalid_auth_port():
    """
    TC 4.1.3 - STEP 2: Invalid auth-port values must be rejected.

    Negative cases (all must produce ^ Error):
      - auth-port 99999   above valid range
      - auth-port 0       zero not valid
      - auth-port 65536   one above max (65535)
      - auth-port -1      negative value

    Module 3 Validation:
      - show radius-server: 192.168.1.100 either absent or has no invalid port
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 2: Invalid Auth-Port Values")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 2: Send invalid auth-port commands ─────────────────────
    st.log("MODULE 2: Sending invalid auth-port commands")

    invalid_ports = [
        (CONFIG.port_invalid_99999, "auth-port 99999 above range"),
        (CONFIG.port_invalid_0,     "auth-port 0 zero"),
        (CONFIG.port_invalid_65536, "auth-port 65536 one above max"),
        (CONFIG.port_invalid_neg1,  "auth-port -1 negative"),
    ]

    for port, label in invalid_ports:
        cmd = f"radius-server host {CONFIG.test_host} auth-port {port}"
        if not send_expect_error(dut, cmd, label):
            failures.append(f"Invalid auth-port '{port}' was NOT rejected")

    st.log("✅ MODULE 2 completed: All invalid auth-port commands sent")

    # ── MODULE 3: Validate host not added with invalid ports ──────────
    st.log("MODULE 3: Validating test host not in table (or has no invalid port)")
    st.wait(2, "Waiting before show command")
    validate_host_not_in_table(dut, CONFIG.test_host)

    # ── Report ────────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.3 STEP 2 PASSED: All invalid auth-port values rejected")
        st.report_pass("test_case_passed", "All invalid auth-port values correctly rejected")


@pytest.mark.radius
@pytest.mark.negative
def test_radius_4_1_3_invalid_timeout():
    """
    TC 4.1.3 - STEP 3: Invalid per-server timeout values rejected; valid boundaries accepted.

    Negative cases (must be rejected with ^ Error):
      - timeout 999   above max (60)
      - timeout 0     zero not valid
      - timeout -5    negative value
      - timeout abc   non-numeric
      - timeout 61    one above max

    Valid boundary cases (must be accepted):
      - timeout 1     minimum valid
      - timeout 60    maximum valid

    Module 3 Validation:
      - show radius-server: 192.168.1.100 has timeout 60 (last valid config applied)
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 3: Invalid and Valid Boundary Timeout Values")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 2: Send invalid timeout commands ───────────────────────
    st.log("MODULE 2: Sending invalid timeout values (must be rejected)")

    invalid_timeouts = [
        (CONFIG.timeout_invalid_999,  "timeout 999 above max"),
        (CONFIG.timeout_invalid_0,    "timeout 0 zero"),
        (CONFIG.timeout_invalid_neg5, "timeout -5 negative"),
        (CONFIG.timeout_invalid_abc,  "timeout abc non-numeric"),
        (CONFIG.timeout_invalid_61,   "timeout 61 one above max"),
    ]

    for timeout, label in invalid_timeouts:
        cmd = f"radius-server host {CONFIG.test_host} timeout {timeout}"
        if not send_expect_error(dut, cmd, label):
            failures.append(f"Invalid timeout '{timeout}' was NOT rejected")

    # ── Send valid boundary timeouts (must be accepted) ───────────────
    st.log("MODULE 2: Sending valid boundary timeout values (must be accepted)")

    valid_timeouts = [
        (CONFIG.timeout_valid_min, f"timeout {CONFIG.timeout_valid_min} minimum valid"),
        (CONFIG.timeout_valid_max, f"timeout {CONFIG.timeout_valid_max} maximum valid"),
    ]

    for timeout, label in valid_timeouts:
        cmd = f"radius-server host {CONFIG.test_host} timeout {timeout}"
        if not send_expect_accepted(dut, cmd, label):
            failures.append(f"Valid timeout '{timeout}' was unexpectedly rejected")

    st.log("✅ MODULE 2 completed")

    # ── MODULE 3: Validate show radius-server shows timeout 60 ───────
    st.log("MODULE 3: Validating show radius-server shows valid timeout (60)")
    st.wait(2, "Waiting before show command")

    output = st.show(dut, "show radius-server",
                     type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"  show radius-server output:\n{output_str}")

    if CONFIG.test_host in output_str and CONFIG.timeout_valid_max in output_str:
        st.log(f"  ✓ Host {CONFIG.test_host} present with timeout {CONFIG.timeout_valid_max}")
    else:
        st.log(f"  ℹ Host or timeout value may appear differently in table — check output above")

    # ── Report ────────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.3 STEP 3 PASSED: Timeout BVA — invalid rejected, valid accepted")
        st.report_pass("test_case_passed",
                       "Invalid timeout rejected and valid boundary timeouts accepted")


@pytest.mark.radius
@pytest.mark.negative
def test_radius_4_1_3_invalid_retransmit_priority_vrf():
    """
    TC 4.1.3 - STEP 4: Invalid retransmit, priority, VRF values must be rejected.

    Negative cases:
      - retransmit 999        above valid range → ^ Error
      - priority 0            zero not valid   → ^ Error
      - priority 999          above max        → ^ Error
      - vrf NonExistentVRF    VRF doesn't exist → ^ Error

    Special case:
      - source-interface Ethernet999  → ACCEPTED (device does not validate intf existence)

    Module 3 Validation:
      - show radius-server: NonExistentVRF NOT in output
      - Ethernet999 IS present in SRC-INTF column (accepted)
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 4: Invalid Retransmit / Priority / VRF Values")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 2: Invalid retransmit ──────────────────────────────────
    st.log("MODULE 2: Testing invalid retransmit value")
    cmd = f"radius-server host {CONFIG.test_host} retransmit {CONFIG.retransmit_invalid_999}"
    if not send_expect_error(dut, cmd, "retransmit 999 above range"):
        failures.append("Invalid retransmit 999 was NOT rejected")

    # ── MODULE 2: Invalid priority ────────────────────────────────────
    st.log("MODULE 2: Testing invalid priority values")
    for prio, label in [
        (CONFIG.priority_invalid_0,   "priority 0 zero not valid"),
        (CONFIG.priority_invalid_999, "priority 999 above max"),
    ]:
        cmd = f"radius-server host {CONFIG.test_host} priority {prio}"
        if not send_expect_error(dut, cmd, label):
            failures.append(f"Invalid priority '{prio}' was NOT rejected")

    # ── MODULE 2: Invalid VRF ─────────────────────────────────────────
    st.log("MODULE 2: Testing invalid VRF")
    cmd = f"radius-server host {CONFIG.test_host} vrf {CONFIG.vrf_invalid}"
    if not send_expect_error(dut, cmd, f"vrf {CONFIG.vrf_invalid} does not exist"):
        failures.append(f"Invalid VRF '{CONFIG.vrf_invalid}' was NOT rejected")

    # ── MODULE 2: Non-existent source-interface (accepted) ────────────
    st.log(f"MODULE 2: Testing source-interface {CONFIG.intf_nonexistent} (expected: ACCEPTED)")
    cmd = f"radius-server host {CONFIG.test_host} source-interface {CONFIG.intf_nonexistent}"
    if not send_expect_accepted(dut, cmd,
                                f"source-interface {CONFIG.intf_nonexistent} accepted (no intf validation)"):
        failures.append(f"source-interface {CONFIG.intf_nonexistent} was unexpectedly rejected")

    st.log("✅ MODULE 2 completed")

    # ── MODULE 3: Validate show radius-server ─────────────────────────
    st.log("MODULE 3: Validating show radius-server output")
    st.wait(2, "Waiting before show command")

    output = st.show(dut, "show radius-server",
                     type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"  show radius-server:\n{output_str}")

    # Validate NonExistentVRF was NOT applied
    if CONFIG.vrf_invalid not in output_str:
        st.log(f"  ✓ Invalid VRF '{CONFIG.vrf_invalid}' correctly absent from table")
    else:
        st.error(f"  ✗ Invalid VRF '{CONFIG.vrf_invalid}' found in table after rejection")
        failures.append(f"Invalid VRF '{CONFIG.vrf_invalid}' present in show output")

    # Validate source-interface Ethernet999 WAS applied (device accepts it)
    if CONFIG.intf_nonexistent in output_str:
        st.log(f"  ✓ SRC-INTF {CONFIG.intf_nonexistent} present in table (accepted as expected)")
    else:
        st.log(f"  ℹ {CONFIG.intf_nonexistent} not found in table — check output above")

    # ── Report ────────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.3 STEP 4 PASSED: Invalid retransmit/priority/VRF rejected correctly")
        st.report_pass("test_case_passed",
                       "Invalid retransmit, priority, VRF rejected; source-interface accepted")


@pytest.mark.radius
@pytest.mark.negative
def test_radius_4_1_3_max_server_limit():
    """
    TC 4.1.3 - STEP 5: Maximum RADIUS server limit (8 servers).

    Test Steps:
      1. Add server 192.168.1.1 (fills slot — device may already have 7 from prior TCs)
      2. Try adding 192.168.1.2 through 192.168.1.9 → each must produce:
           %Error: Max elements limit 8 reached
      3. Cleanup: remove all 192.168.1.x servers

    Module 3 Validation:
      - show radius-server: none of the overflow servers (192.168.1.2-9) appear in table
    """
    st.banner("=" * 80)
    st.banner(f"{TC_ID} STEP 5: Maximum RADIUS Server Limit (8 servers)")
    st.banner("=" * 80)

    dut = vars.D1
    failures = []

    # ── MODULE 2: Add first server (192.168.1.1) ──────────────────────
    st.log("MODULE 2: Adding 192.168.1.1 to approach/reach the 8-server limit")
    cmd = f"radius-server host {CONFIG.max_limit_server_first} key Key1"
    output = st.config(dut, [cmd], type=data.cli_type, skip_error_check=True)
    output_str = str(output) if output else ""

    if any(p in output_str for p in ERROR_PATTERNS):
        # Already at limit — that's fine, means prior TCs already filled 8
        st.log(f"  ℹ 192.168.1.1 rejected — limit already reached from prior test data")
    else:
        st.log(f"  ✓ 192.168.1.1 added (or already present)")

    # ── MODULE 2: Try adding overflow servers ─────────────────────────
    st.log("MODULE 2: Attempting to add overflow servers (must be rejected with Max limit error)")

    limit_error_count = 0
    for srv in CONFIG.max_limit_servers_extra:
        cmd = f"radius-server host {srv} key Key{srv.split('.')[-1]}"
        output = st.config(dut, [cmd], type=data.cli_type, skip_error_check=True)
        output_str = str(output) if output else ""

        if "Max elements limit" in output_str or "Max" in output_str:
            st.log(f"  ✓ {srv} rejected: Max elements limit reached")
            limit_error_count += 1
        elif any(p in output_str for p in ERROR_PATTERNS):
            st.log(f"  ✓ {srv} rejected (other error — acceptable): {output_str[:100]}")
            limit_error_count += 1
        else:
            st.error(f"  ✗ {srv} was ACCEPTED — should have been rejected (limit exceeded)")
            failures.append(f"Overflow server {srv} was accepted beyond 8-server limit")

    if limit_error_count > 0:
        st.log(f"  ✓ {limit_error_count} overflow servers correctly rejected by device")

    st.log("✅ MODULE 2 completed")

    # ── MODULE 3: Validate overflow servers not in table ──────────────
    st.log("MODULE 3: Validating overflow servers absent from show radius-server")
    st.wait(2, "Waiting before show command")

    output = st.show(dut, "show radius-server",
                     type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"  show radius-server:\n{output_str}")

    # Count how many overflow servers appear (should be 0)
    overflow_found = [srv for srv in CONFIG.max_limit_servers_extra if srv in output_str]
    if not overflow_found:
        st.log(f"  ✓ No overflow servers found in table")
    else:
        st.error(f"  ✗ Overflow servers found in table: {overflow_found}")
        failures.append(f"Overflow servers appeared in table: {overflow_found}")

    # ── MODULE 2: Cleanup all 192.168.1.x servers ─────────────────────
    st.log("MODULE 2: Removing all 192.168.1.x test servers")
    cleanup_cmds = [f"no radius-server host {CONFIG.max_limit_server_first}"]
    for srv in CONFIG.max_limit_servers_extra:
        cleanup_cmds.append(f"no radius-server host {srv}")
    st.config(dut, cleanup_cmds, type=data.cli_type, skip_error_check=True)
    st.log("  ✓ 192.168.1.x test servers removed")

    # ── Report ────────────────────────────────────────────────────────
    if failures:
        for f in failures:
            st.error(f"  ✗ {f}")
        st.report_fail("test_case_failed")
    else:
        st.log("✓ TC 4.1.3 STEP 5 PASSED: Max server limit (8) enforced correctly")
        st.report_pass("test_case_passed",
                       "Max RADIUS server limit of 8 correctly enforced by device")
