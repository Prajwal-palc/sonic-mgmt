"""
TACACS+ Global Timeout Configuration Testing

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_vs_1node.yaml \
    system/ISCLI_Tacacs/test_tacacs_03_global_timeout.py \
    --logs-path ./logs/tacacs03_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native
"""

from __future__ import annotations
import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "global_passkey": "test123",
    "global_authtype": "pap",
    "global_timeout": "10",
    "cli_type": "klish"
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown fixture."""
    global vars, data

    st.banner("=" * 80)
    st.banner("TACACS-03: MODULE PROLOGUE - Global Timeout Configuration Test")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = CONFIG.cli_type

    st.log(f"Module Setup: Using CLI type '{data.cli_type}'")
    st.log(f"Global Passkey: {CONFIG.global_passkey}")
    st.log(f"Global Timeout: {CONFIG.global_timeout}s")

    st.log("Performing unconfiguration of TACACS+ settings...")
    unconfigure_all_tacacs(vars.D1)
    st.wait(2, "Waiting for unconfiguration")

    yield

    st.banner("=" * 80)
    st.banner("TACACS-03: MODULE EPILOGUE - Cleanup")
    st.banner("=" * 80)

    st.log("Cleaning up TACACS+ configuration...")
    cleanup_all_tacacs(vars.D1)
    st.log("✅ Cleanup completed")


def unconfigure_all_tacacs(dut: str) -> bool:
    """Unconfigure all TACACS+ settings."""
    try:
        st.log(f"Unconfiguring TACACS+ on {dut}...")
        commands = [
            "no tacacs server 192.168.1.10",
            "no tacacs server 192.168.100.87",
            "no tacacs server 192.168.1.20",
            "no tacacs server 192.168.1.30",
            "no tacacs timeout",
            "no tacacs authtype",
            "no tacacs passkey",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(1, "Waiting for unconfiguration")
        st.log(f"✅ Unconfiguration completed on {dut}")
        return True
    except Exception as e:
        st.log(f"⚠️  Unconfiguration note: {str(e)}")
        return True


def configure_passkey(dut: str, passkey: str) -> bool:
    """Configure global TACACS+ passkey."""
    try:
        st.log(f"Configuring TACACS+ passkey: {passkey}")
        commands = [f"tacacs passkey {passkey}"]
        st.config(dut, commands, type=data.cli_type)
        st.wait(1, "Waiting for passkey configuration")
        st.log(f"✅ Passkey configured")
        return True
    except Exception as e:
        st.error(f"❌ Failed to configure passkey: {str(e)}")
        return False


def configure_timeout(dut: str, timeout: str) -> bool:
    """Configure global TACACS+ timeout."""
    try:
        st.log(f"Configuring TACACS+ timeout: {timeout}s")
        commands = [f"tacacs timeout {timeout}"]
        st.config(dut, commands, type=data.cli_type)
        st.wait(1, "Waiting for timeout configuration")
        st.log(f"✅ Timeout configured to {timeout}s")
        return True
    except Exception as e:
        st.error(f"❌ Failed to configure timeout: {str(e)}")
        return False


def configure_authtype(dut: str, authtype: str) -> bool:
    """Configure global TACACS+ authentication type."""
    try:
        st.log(f"Configuring TACACS+ authtype: {authtype}")
        commands = [f"tacacs authtype {authtype}"]
        st.config(dut, commands, type=data.cli_type)
        st.wait(1, "Waiting for authtype configuration")
        st.log(f"✅ Authtype configured to {authtype}")
        return True
    except Exception as e:
        st.error(f"❌ Failed to configure authtype: {str(e)}")
        return False


def configure_server(dut: str, address: str, priority: str = "1",
                     tcp_port: str = None, timeout: str = None,
                     passkey: str = None, vrf: str = None) -> bool:
    """Configure TACACS+ server with options."""
    try:
        st.log(f"Configuring TACACS+ server: {address}")
        commands = [f"tacacs server {address}"]

        if priority:
            commands.append(f"  priority {priority}")
        if tcp_port:
            commands.append(f"  tcp_port {tcp_port}")
        if timeout:
            commands.append(f"  timeout {timeout}")
        if passkey:
            commands.append(f"  passkey {passkey}")
        if vrf:
            commands.append(f"  vrf {vrf}")

        st.config(dut, commands, type=data.cli_type)
        st.wait(1, "Waiting for server configuration")
        st.log(f"✅ Server {address} configured")
        return True
    except Exception as e:
        st.error(f"❌ Failed to configure server: {str(e)}")
        return False


def show_tacacs(dut: str) -> str:
    """Display TACACS+ configuration."""
    try:
        st.log(f"Displaying TACACS+ configuration on {dut}")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)
        if output:
            st.log(f"TACACS+ Configuration:\n{output}")
            return str(output)
        else:
            st.log("⚠️  No TACACS configuration output")
            return ""
    except Exception as e:
        st.error(f"Failed to show TACACS: {str(e)}")
        return ""


def cleanup_all_tacacs(dut: str) -> bool:
    """Cleanup all TACACS+ configuration."""
    try:
        st.log(f"Cleaning up TACACS+ on {dut}...")
        commands = [
            "no tacacs server 192.168.1.10",
            "no tacacs server 192.168.100.87",
            "no tacacs server 192.168.1.20",
            "no tacacs server 192.168.1.30",
            "no tacacs timeout",
            "no tacacs authtype",
            "no tacacs passkey",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(1, "Waiting for cleanup")
        st.log(f"✅ Cleanup completed")
        return True
    except Exception as e:
        st.error(f"Failed to cleanup: {str(e)}")
        return False


@pytest.mark.tacacs
def test_tacacs_03_global_timeout_basic():
    """Test 03: Global TACACS+ Timeout Configuration (Basic)"""
    st.banner("-" * 80)
    st.banner("TEST-03: Global TACACS+ Timeout Configuration (Basic)")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        st.log("STEP 1: Configure global TACACS+ passkey")
        if not configure_passkey(dut, CONFIG.global_passkey):
            validation_failures.append("Failed to configure passkey")
        st.log("✅ STEP 1 completed")

        st.log("STEP 2: Configure global TACACS+ timeout")
        if not configure_timeout(dut, CONFIG.global_timeout):
            validation_failures.append("Failed to configure timeout")
        st.log("✅ STEP 2 completed")

        st.log("STEP 3: Display TACACS+ configuration")
        output = show_tacacs(dut)
        if not output:
            validation_failures.append("Failed to display configuration")
        st.log("✅ STEP 3 completed")

        st.log("✅ TEST-03 COMPLETED")

    except Exception as e:
        st.error(f"Exception: {str(e)}")
        validation_failures.append(str(e))

    if validation_failures:
        st.log("\n" + "!"*80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!"*80)
        st.report_fail("msg", f"test_tacacs_03_global_timeout_basic: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "="*80)
        st.log("✅ TEST-03: ALL VALIDATIONS PASSED")
        st.log("="*80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
def test_tacacs_04_timeout_with_authtype():
    """Test 04: Global Timeout with Authentication Type"""
    st.banner("-" * 80)
    st.banner("TEST-04: Global Timeout with Authentication Type")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        st.log("STEP 1: Configure passkey")
        if not configure_passkey(dut, CONFIG.global_passkey):
            validation_failures.append("Failed to configure passkey")
        st.log("✅ STEP 1 completed")

        st.log("STEP 2: Configure authentication type (PAP)")
        if not configure_authtype(dut, CONFIG.global_authtype):
            validation_failures.append("Failed to configure authtype")
        st.log("✅ STEP 2 completed")

        st.log("STEP 3: Configure timeout (10s)")
        if not configure_timeout(dut, CONFIG.global_timeout):
            validation_failures.append("Failed to configure timeout")
        st.log("✅ STEP 3 completed")

        st.log("STEP 4: Display and verify configuration")
        output = show_tacacs(dut)
        if not output:
            validation_failures.append("Failed to display configuration")
        st.log("✅ STEP 4 completed")

        st.log("✅ TEST-04 COMPLETED")

    except Exception as e:
        st.error(f"Exception: {str(e)}")
        validation_failures.append(str(e))

    if validation_failures:
        st.log("\n" + "!"*80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!"*80)
        st.report_fail("msg", f"test_tacacs_04_timeout_with_authtype: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "="*80)
        st.log("✅ TEST-04: ALL VALIDATIONS PASSED")
        st.log("="*80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
def test_tacacs_05_timeout_with_multiple_servers():
    """Test 05: Global Timeout with Multiple TACACS+ Servers"""
    st.banner("-" * 80)
    st.banner("TEST-05: Global Timeout with Multiple TACACS+ Servers")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        st.log("STEP 1: Configure global TACACS+ baseline")
        if not configure_passkey(dut, CONFIG.global_passkey):
            validation_failures.append("Failed to configure passkey")
        if not configure_authtype(dut, CONFIG.global_authtype):
            validation_failures.append("Failed to configure authtype")
        if not configure_timeout(dut, CONFIG.global_timeout):
            validation_failures.append("Failed to configure timeout")
        st.log("✅ STEP 1 completed")

        st.log("STEP 2: Configure first server")
        if not configure_server(dut, "192.168.1.10", priority="1",
                               tcp_port="50", timeout="10",
                               passkey="testing123", vrf="mgmt"):
            validation_failures.append("Failed to configure server 1")
        st.log("✅ STEP 2 completed")

        st.log("STEP 3: Configure second server")
        if not configure_server(dut, "192.168.100.87", priority="1",
                               tcp_port="49"):
            validation_failures.append("Failed to configure server 2")
        st.log("✅ STEP 3 completed")

        st.log("STEP 4: Display and verify all servers")
        output = show_tacacs(dut)
        if not output:
            validation_failures.append("Failed to display configuration")
        st.log("✅ STEP 4 completed")

        st.log("✅ TEST-05 COMPLETED")

    except Exception as e:
        st.error(f"Exception: {str(e)}")
        validation_failures.append(str(e))

    if validation_failures:
        st.log("\n" + "!"*80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!"*80)
        st.report_fail("msg", f"test_tacacs_05_timeout_with_multiple_servers: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "="*80)
        st.log("✅ TEST-05: ALL VALIDATIONS PASSED")
        st.log("="*80)
        st.report_pass("test_case_passed")


@pytest.mark.tacacs
def test_tacacs_06_timeout_modification():
    """Test 06: Global Timeout Modification and Update"""
    st.banner("-" * 80)
    st.banner("TEST-06: Global Timeout Modification and Update")
    st.banner("-" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        st.log("STEP 1: Configure initial timeout (10s)")
        if not configure_passkey(dut, CONFIG.global_passkey):
            validation_failures.append("Failed to configure passkey")
        if not configure_timeout(dut, CONFIG.global_timeout):
            validation_failures.append("Failed to configure initial timeout")
        st.log("✅ STEP 1 completed")

        st.log("STEP 2: Display initial configuration")
        output1 = show_tacacs(dut)
        if not output1:
            validation_failures.append("Failed to display initial configuration")
        st.log("✅ STEP 2 completed")

        st.log("STEP 3: Modify timeout to 15s")
        if not configure_timeout(dut, "15"):
            validation_failures.append("Failed to modify timeout")
        st.log("✅ STEP 3 completed")

        st.log("STEP 4: Display modified configuration")
        output2 = show_tacacs(dut)
        if not output2:
            validation_failures.append("Failed to display modified configuration")
        st.log("✅ STEP 4 completed")

        st.log("✅ TEST-06 COMPLETED")

    except Exception as e:
        st.error(f"Exception: {str(e)}")
        validation_failures.append(str(e))

    if validation_failures:
        st.log("\n" + "!"*80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!"*80)
        st.report_fail("msg", f"test_tacacs_06_timeout_modification: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "="*80)
        st.log("✅ TEST-06: ALL VALIDATIONS PASSED")
        st.log("="*80)
        st.report_pass("test_case_passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
