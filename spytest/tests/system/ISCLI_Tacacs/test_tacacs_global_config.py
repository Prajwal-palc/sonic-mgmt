"""
TACACS+ Global Configuration Test Script
==========================================

Based on manual testing logs for OC-Build

Device behaviour (confirmed from test runs):
- tacacs-server host <IP>                       : add server (global)
- tacacs-server host <IP> auth-type <val>       : per-server auth-type (pap/chap/login)
- tacacs-server host <IP> key <val>             : per-server passkey
- tacacs-server host <IP> port <val>            : per-server port
- tacacs-server host <IP> timeout <val>         : per-server timeout
- tacacs-server timeout <val>                   : global timeout (ONLY global param accepted)
- no tacacs-server timeout                      : reset global timeout
- no tacacs-server host <IP>                    : remove server

NOT supported as global commands on this device:
- tacacs-server auth-type / no tacacs-server auth-type   -> Error
- tacacs-server key       / no tacacs-server key         -> Error

Show output format:
  TACACS+ Global Configuration
  Authentication Type  : N/A   (always N/A — no global auth-type)
  Global Timeout       : N/A / 50
  Key Configured       : Yes/No
  -------
  TACACS+ Servers
  HOST           AUTH-TYPE  KEY  PORT  PRIORITY  TIMEOUT  VRF
  192.168.100.87 pap        Yes  49    1         5        DEFAULT

Test Coverage:
- TACACS+ server host add/remove
- Per-server auth-type (pap, chap, login)
- Per-server passkey
- Global timeout configuration and reset
- Validation of show tacacs-server after each operation

Module: test_tacacs_global_config
Framework: spytest
Device: SONiC (OC-Build)
"""

from __future__ import annotations
import re
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
    "tacacs_timeout_custom": "50",
    "tacacs_port_default": "49",
    "tacacs_priority_default": "1",
    "tacacs_timeout_per_server": "5",   # per-server default timeout shown in HOST table
    "cli_type": "klish"
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture.
    MODULE 1: Unconfigure any existing TACACS+ config before tests.
    MODULE 4: Cleanup after all tests.
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TACACS-GLOBAL: MODULE 1 - UNCONFIGURATION (PROLOGUE)")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = CONFIG.cli_type

    st.log(f"Module Setup: CLI type='{data.cli_type}'  Server={CONFIG.tacacs_server_ip}")
    unconfigure_all_tacacs(vars.D1)
    st.wait(2, "Waiting for unconfiguration to complete")
    st.log("MODULE 1: Unconfiguration completed")

    yield

    st.banner("=" * 80)
    st.banner("TACACS-GLOBAL: MODULE 4 - CLEANUP (EPILOGUE)")
    st.banner("=" * 80)
    cleanup_all_tacacs(vars.D1)
    st.wait(2, "Waiting for cleanup to complete")
    st.log("MODULE 4: Cleanup completed")


# ---------------------------------------------------------------------------
# Helper: unconfigure / cleanup
# ---------------------------------------------------------------------------

def unconfigure_all_tacacs(dut: str) -> bool:
    """Remove server + reset global timeout. auth-type/key are per-server only."""
    try:
        st.log(f"Unconfiguring all TACACS+ on {dut}...")
        commands = [
            f"no tacacs-server host {CONFIG.tacacs_server_ip}",
            "no tacacs-server timeout",   # only global param that can be reset
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log("Unconfiguration done")
        return True
    except Exception as e:
        st.log(f"Unconfiguration note: {e}")
        return True


def cleanup_all_tacacs(dut: str) -> bool:
    """Same as unconfigure — used in epilogue."""
    return unconfigure_all_tacacs(dut)


# ---------------------------------------------------------------------------
# Helper: configure
# ---------------------------------------------------------------------------

def configure_tacacs_server(dut: str, server_ip: str) -> bool:
    """Add TACACS+ server host."""
    try:
        st.log(f"Configuring tacacs-server host {server_ip} on {dut}...")
        st.config(dut, [f"tacacs-server host {server_ip}"],
                  type=data.cli_type, skip_error_check=False)
        st.wait(2, "Waiting for server configuration to apply")
        st.log(f"TACACS+ server {server_ip} configured")
        return True
    except Exception as e:
        st.error(f"Failed to configure server: {e}")
        return False


def configure_server_authtype(dut: str, server_ip: str, authtype: str) -> bool:
    """Set per-server auth-type: tacacs-server host <IP> auth-type <val>"""
    try:
        cmd = f"tacacs-server host {server_ip} auth-type {authtype}"
        st.log(f"Setting auth-type={authtype} on server {server_ip}...")
        output = st.config(dut, [cmd], type=data.cli_type, skip_error_check=True)
        output_str = output if isinstance(output, str) else str(output)
        if "Error" in output_str or "^" in output_str:
            st.error(f"✗ Command rejected: {cmd}\n  Output: {output_str}")
            return False
        st.wait(1, "Waiting for auth-type to apply")
        st.log(f"✓ auth-type={authtype} set on {server_ip}")
        return True
    except Exception as e:
        st.error(f"Failed to set auth-type: {e}")
        return False


def configure_server_passkey(dut: str, server_ip: str, passkey: str) -> bool:
    """Set per-server passkey: tacacs-server host <IP> key <val>"""
    try:
        cmd = f"tacacs-server host {server_ip} key {passkey}"
        st.log(f"Setting passkey on server {server_ip}...")
        output = st.config(dut, [cmd], type=data.cli_type, skip_error_check=True)
        output_str = output if isinstance(output, str) else str(output)
        if "Error" in output_str or "^" in output_str:
            st.error(f"✗ Command rejected: {cmd}\n  Output: {output_str}")
            return False
        st.wait(1, "Waiting for passkey to apply")
        st.log(f"✓ passkey set on {server_ip}")
        return True
    except Exception as e:
        st.error(f"Failed to set passkey: {e}")
        return False


def configure_global_timeout(dut: str, timeout: str) -> bool:
    """Set global timeout: tacacs-server timeout <val>"""
    try:
        cmd = f"tacacs-server timeout {timeout}"
        st.log(f"Setting global timeout={timeout}...")
        output = st.config(dut, [cmd], type=data.cli_type, skip_error_check=True)
        output_str = output if isinstance(output, str) else str(output)
        if "Error" in output_str or "^" in output_str:
            st.error(f"✗ Command rejected: {cmd}\n  Output: {output_str}")
            return False
        st.wait(1, "Waiting for timeout to apply")
        st.log(f"✓ global timeout={timeout} set")
        return True
    except Exception as e:
        st.error(f"Failed to set global timeout: {e}")
        return False


def reset_global_timeout(dut: str) -> bool:
    """Reset global timeout: no tacacs-server timeout"""
    try:
        st.log("Resetting global timeout to default (no tacacs-server timeout)...")
        output = st.config(dut, ["no tacacs-server timeout"],
                           type=data.cli_type, skip_error_check=True)
        output_str = output if isinstance(output, str) else str(output)
        if "Error" in output_str and "^" in output_str:
            st.error(f"✗ 'no tacacs-server timeout' rejected\n  Output: {output_str}")
            return False
        st.wait(1, "Waiting for timeout reset to apply")
        st.log("✓ global timeout reset to N/A")
        return True
    except Exception as e:
        st.error(f"Failed to reset timeout: {e}")
        return False


# ---------------------------------------------------------------------------
# Helper: verify
# ---------------------------------------------------------------------------

def show_tacacs(dut: str) -> str:
    """Run show tacacs-server and return raw string output."""
    output = st.show(dut, "show tacacs-server", type=data.cli_type,
                     skip_tmpl=True, skip_error_check=True)
    return output if isinstance(output, str) else str(output) if output else ""


def verify_global_timeout(dut: str, expected_timeout: str) -> bool:
    """
    Verify Global Timeout in the global section.
    expected_timeout: "50" for a configured value, "N/A" for default/reset.
    """
    output_str = show_tacacs(dut)
    st.log(f"TACACS+ output:\n{output_str}")
    match = re.search(r'Global Timeout\s*:\s*(\S+)', output_str, re.IGNORECASE)
    actual = match.group(1) if match else ""
    if actual.upper() == expected_timeout.upper():
        st.log(f"✓ Global Timeout verified: {actual}")
        return True
    else:
        st.error(f"✗ Global Timeout mismatch: expected '{expected_timeout}', got '{actual}'")
        return False


def verify_server_present(dut: str, server_ip: str) -> bool:
    """Verify server IP appears in HOST table."""
    output_str = show_tacacs(dut)
    st.log(f"TACACS+ output:\n{output_str}")
    if server_ip in output_str:
        st.log(f"✓ Server {server_ip} present")
        return True
    st.error(f"✗ Server {server_ip} not found in output")
    return False


def verify_server_removed(dut: str, server_ip: str) -> bool:
    """Verify server IP is gone from HOST table."""
    output_str = show_tacacs(dut)
    st.log(f"TACACS+ output:\n{output_str}")
    if server_ip not in output_str:
        st.log(f"✓ Server {server_ip} successfully removed")
        return True
    st.error(f"✗ Server {server_ip} still present after removal")
    return False


def verify_server_authtype(dut: str, server_ip: str, expected_authtype: str) -> bool:
    """
    Verify AUTH-TYPE column in the HOST table row for server_ip.
    Parses the row: HOST  AUTH-TYPE  KEY  PORT  PRIORITY  TIMEOUT  VRF
    """
    output_str = show_tacacs(dut)
    st.log(f"TACACS+ output:\n{output_str}")
    for line in output_str.splitlines():
        if server_ip in line:
            tokens = line.split()
            # tokens[0]=HOST [1]=AUTH-TYPE [2]=KEY [3]=PORT [4]=PRIORITY [5]=TIMEOUT [6]=VRF
            if len(tokens) >= 2:
                actual = tokens[1].lower()
                if actual == expected_authtype.lower():
                    st.log(f"✓ AUTH-TYPE verified: {actual}")
                    return True
                else:
                    st.error(f"✗ AUTH-TYPE mismatch: expected '{expected_authtype}', got '{actual}'")
                    return False
    st.error(f"✗ Server row for {server_ip} not found in output")
    return False


def verify_server_key_configured(dut: str, server_ip: str, expected: str) -> bool:
    """
    Verify KEY column in HOST table row for server_ip.
    expected: 'Yes' if key is configured, 'No' if not.
    """
    output_str = show_tacacs(dut)
    st.log(f"TACACS+ output:\n{output_str}")
    for line in output_str.splitlines():
        if server_ip in line:
            tokens = line.split()
            # tokens[2] = KEY (Yes/No)
            if len(tokens) >= 3:
                actual = tokens[2]
                if actual.lower() == expected.lower():
                    st.log(f"✓ KEY column verified: {actual}")
                    return True
                else:
                    st.error(f"✗ KEY mismatch: expected '{expected}', got '{actual}'")
                    return False
    st.error(f"✗ Server row for {server_ip} not found in output")
    return False


# ===========================================================================
# TEST FUNCTIONS
# ===========================================================================

@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_01_basic_server_passkey():
    """
    Test 01: Add server + set per-server passkey

    Commands:
      tacacs-server host 192.168.100.87
      tacacs-server host 192.168.100.87 key Test12243

    Validates:
      - Server present in HOST table
      - KEY column = Yes (passkey configured)
    """
    st.banner("-" * 80)
    st.banner("TEST-01: Basic TACACS+ Server and Per-Server Passkey")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        unconfigure_all_tacacs(dut)
        st.wait(1)

        # Configure server
        if not configure_tacacs_server(dut, CONFIG.tacacs_server_ip):
            st.error("Failed to configure TACACS+ server")
            result = False

        # Set per-server passkey
        if not configure_server_passkey(dut, CONFIG.tacacs_server_ip, CONFIG.tacacs_passkey_1):
            st.error("Failed to configure per-server passkey")
            result = False

        # Verify server present
        if not verify_server_present(dut, CONFIG.tacacs_server_ip):
            result = False

        # Verify KEY = Yes
        if not verify_server_key_configured(dut, CONFIG.tacacs_server_ip, "Yes"):
            result = False

    except Exception as e:
        st.error(f"Exception in TEST-01: {e}")
        result = False

    if result:
        st.log("✅ TEST-01 PASSED: Server + per-server passkey configured and verified")
    else:
        st.error("❌ TEST-01 FAILED")

    assert result, "Test failed: TACACS+ server + passkey"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_02_global_timeout():
    """
    Test 02: Global timeout configuration and reset

    Commands:
      tacacs-server host 192.168.100.87
      tacacs-server timeout 50          <- global
      no tacacs-server timeout          <- reset global

    Validates:
      - Global Timeout = 50 after configure
      - Global Timeout = N/A after reset
    """
    st.banner("-" * 80)
    st.banner("TEST-02: TACACS+ Global Timeout Configuration")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        unconfigure_all_tacacs(dut)
        st.wait(1)

        if not configure_tacacs_server(dut, CONFIG.tacacs_server_ip):
            st.error("Failed to configure TACACS+ server")
            result = False

        # Set global timeout
        if not configure_global_timeout(dut, CONFIG.tacacs_timeout_custom):
            st.error("Failed to set global timeout")
            result = False

        # Verify global timeout = 50
        if not verify_global_timeout(dut, CONFIG.tacacs_timeout_custom):
            result = False

        # Reset global timeout
        if not reset_global_timeout(dut):
            st.error("Failed to reset global timeout")
            result = False

        # Verify global timeout = N/A
        if not verify_global_timeout(dut, "N/A"):
            result = False

    except Exception as e:
        st.error(f"Exception in TEST-02: {e}")
        result = False

    if result:
        st.log("✅ TEST-02 PASSED: Global timeout configured and reset verified")
    else:
        st.error("❌ TEST-02 FAILED")

    assert result, "Test failed: TACACS+ global timeout"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_03_authtype_pap():
    """
    Test 03: Per-server auth-type PAP

    Command:
      tacacs-server host 192.168.100.87 auth-type pap

    Validates:
      - AUTH-TYPE column = pap in HOST table
    """
    st.banner("-" * 80)
    st.banner("TEST-03: Per-Server Auth-Type PAP")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        unconfigure_all_tacacs(dut)
        st.wait(1)
        configure_tacacs_server(dut, CONFIG.tacacs_server_ip)
        st.wait(1)

        if not configure_server_authtype(dut, CONFIG.tacacs_server_ip, "pap"):
            st.error("Failed to set auth-type pap")
            result = False

        if not verify_server_authtype(dut, CONFIG.tacacs_server_ip, "pap"):
            result = False

    except Exception as e:
        st.error(f"Exception in TEST-03: {e}")
        result = False

    if result:
        st.log("✅ TEST-03 PASSED: Per-server auth-type pap verified")
    else:
        st.error("❌ TEST-03 FAILED")

    assert result, "Test failed: per-server auth-type pap"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_04_authtype_chap_and_passkey():
    """
    Test 04: Per-server auth-type CHAP + passkey

    Commands:
      tacacs-server host 192.168.100.87 auth-type chap
      tacacs-server host 192.168.100.87 key Test123

    Validates:
      - AUTH-TYPE column = chap
      - KEY column = Yes
    """
    st.banner("-" * 80)
    st.banner("TEST-04: Per-Server Auth-Type CHAP + Passkey")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        unconfigure_all_tacacs(dut)
        st.wait(1)
        configure_tacacs_server(dut, CONFIG.tacacs_server_ip)
        st.wait(1)

        if not configure_server_authtype(dut, CONFIG.tacacs_server_ip, "chap"):
            st.error("Failed to set auth-type chap")
            result = False

        if not configure_server_passkey(dut, CONFIG.tacacs_server_ip, CONFIG.tacacs_passkey_2):
            st.error("Failed to set per-server passkey")
            result = False

        if not verify_server_authtype(dut, CONFIG.tacacs_server_ip, "chap"):
            result = False

        if not verify_server_key_configured(dut, CONFIG.tacacs_server_ip, "Yes"):
            result = False

    except Exception as e:
        st.error(f"Exception in TEST-04: {e}")
        result = False

    if result:
        st.log("✅ TEST-04 PASSED: Per-server auth-type chap + passkey verified")
    else:
        st.error("❌ TEST-04 FAILED")

    assert result, "Test failed: per-server auth-type chap + passkey"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_05_authtype_login_and_global_timeout():
    """
    Test 05: Per-server auth-type LOGIN + global timeout

    Commands:
      tacacs-server host 192.168.100.87 auth-type login
      tacacs-server timeout 50

    Validates:
      - AUTH-TYPE column = login
      - Global Timeout = 50
    """
    st.banner("-" * 80)
    st.banner("TEST-05: Per-Server Auth-Type LOGIN + Global Timeout")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        unconfigure_all_tacacs(dut)
        st.wait(1)
        configure_tacacs_server(dut, CONFIG.tacacs_server_ip)
        st.wait(1)

        if not configure_server_authtype(dut, CONFIG.tacacs_server_ip, "login"):
            st.error("Failed to set auth-type login")
            result = False

        if not configure_global_timeout(dut, CONFIG.tacacs_timeout_custom):
            st.error("Failed to set global timeout")
            result = False

        if not verify_server_authtype(dut, CONFIG.tacacs_server_ip, "login"):
            result = False

        if not verify_global_timeout(dut, CONFIG.tacacs_timeout_custom):
            result = False

    except Exception as e:
        st.error(f"Exception in TEST-05: {e}")
        result = False

    if result:
        st.log("✅ TEST-05 PASSED: Per-server auth-type login + global timeout verified")
    else:
        st.error("❌ TEST-05 FAILED")

    assert result, "Test failed: per-server auth-type login + global timeout"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_06_remove_server():
    """
    Test 06: Remove TACACS+ server

    Command:
      no tacacs-server host 192.168.100.87

    Validates:
      - Server IP no longer in show tacacs-server output
    """
    st.banner("-" * 80)
    st.banner("TEST-06: Remove TACACS+ Server")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        unconfigure_all_tacacs(dut)
        st.wait(1)
        configure_tacacs_server(dut, CONFIG.tacacs_server_ip)
        st.wait(1)

        # Confirm present before removal
        if not verify_server_present(dut, CONFIG.tacacs_server_ip):
            st.error("Precondition failed: server not present before removal")
            result = False

        # Remove
        st.log(f"Removing tacacs-server host {CONFIG.tacacs_server_ip}...")
        st.config(dut, [f"no tacacs-server host {CONFIG.tacacs_server_ip}"],
                  type=data.cli_type, skip_error_check=True)
        st.wait(2)

        # Confirm removed
        if not verify_server_removed(dut, CONFIG.tacacs_server_ip):
            result = False

    except Exception as e:
        st.error(f"Exception in TEST-06: {e}")
        result = False

    if result:
        st.log("✅ TEST-06 PASSED: TACACS+ server removed and verified")
    else:
        st.error("❌ TEST-06 FAILED")

    assert result, "Test failed: TACACS+ server removal"


@pytest.mark.tacacs
@pytest.mark.tacacs_global
def test_tacacs_global_07_all_authtypes():
    """
    Test 07: Comprehensive per-server auth-type cycle (pap → chap → login)

    Note: auth-type is per-server on this platform. Valid values: pap, chap, login.
    Reconfiguring the server with a new auth-type overrides the previous one.

    Commands (per iteration):
      no tacacs-server host <IP>                      <- remove to reset auth-type
      tacacs-server host <IP>                         <- re-add
      tacacs-server host <IP> auth-type <val>         <- set new auth-type

    Validates:
      - AUTH-TYPE column in HOST table matches configured value
    """
    st.banner("-" * 80)
    st.banner("TEST-07: Comprehensive Per-Server Auth-Type Cycle (pap/chap/login)")
    st.banner("-" * 80)

    dut = vars.D1
    result = True
    # Only pap, chap, login are supported on this device
    authtypes = ["pap", "chap", "login"]

    try:
        unconfigure_all_tacacs(dut)
        st.wait(1)

        for authtype in authtypes:
            st.log(f"\n--- Testing auth-type: {authtype} ---")

            # Re-add server fresh each iteration to reset auth-type
            st.config(dut, [f"no tacacs-server host {CONFIG.tacacs_server_ip}"],
                      type=data.cli_type, skip_error_check=True)
            st.wait(1)

            if not configure_tacacs_server(dut, CONFIG.tacacs_server_ip):
                st.error(f"Failed to add server for auth-type={authtype}")
                result = False
                continue

            if not configure_server_authtype(dut, CONFIG.tacacs_server_ip, authtype):
                st.error(f"Failed to set auth-type={authtype}")
                result = False
                continue

            if not verify_server_authtype(dut, CONFIG.tacacs_server_ip, authtype):
                st.error(f"AUTH-TYPE verification failed for: {authtype}")
                result = False
            else:
                st.log(f"✓ auth-type={authtype} verified successfully")

            st.wait(1)

    except Exception as e:
        st.error(f"Exception in TEST-07: {e}")
        result = False

    if result:
        st.log("✅ TEST-07 PASSED: Comprehensive auth-type cycle (pap/chap/login)")
    else:
        st.error("❌ TEST-07 FAILED")

    assert result, "Test failed: Comprehensive auth-type cycle"


if __name__ == "__main__":
    st.log("Running TACACS+ Global Configuration tests directly")
    pytest.main([__file__, "-v"])
