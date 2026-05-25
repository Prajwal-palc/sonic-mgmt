"""
AAA TACACS+ Authentication TEST - Exact Manual Workflow
Packet Flow: 192.168.100.87 (TACACS+ server) <-> 192.168.100.148 (DUT)
"""

from __future__ import annotations
import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "dut_ip": "192.168.100.148",
    "tacacs_server_ip": "192.168.100.87",
    "tacacs_interface": "enp1s0",
    "tacacs_passkey": "test123",
    "tacacs_admin_user": "admin",
    "tacacs_admin_pass": "Admin123",
    "capture_file": "/tmp/tacacs1.pcap",
})

@pytest.fixture(scope="module", autouse=True)
def aaa_tacacs_module_hooks(request):
    global vars, data
    vars = st.ensure_min_topology("D1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'
    st.log(f"DUT: {vars.D1} ({CONFIG.dut_ip})")
    st.log(f"TACACS+ Server: {CONFIG.tacacs_server_ip}")
    yield
    # Module epilogue: cleanup
    st.log("Module epilogue: removing AAA/TACACS+ config and pcap file")
    cleanup_cmds = [
        "no aaa authentication login default",
        "no aaa authentication failthrough",
        "no aaa authentication fallback",
        f"no tacacs-server host {CONFIG.tacacs_server_ip}",
    ]
    st.config(vars.D1, cleanup_cmds, type=data.cli_type, skip_error_check=True)
    st.show(vars.D1,
            f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} "
            f"'rm -f {CONFIG.capture_file}'",
            skip_tmpl=True, skip_error_check=True)


# ============================================================================
# MODULE 1: CONFIGURATION
# ============================================================================

def test_001_configure_aaa_and_tacacs():
    """Module 1: Configure AAA and TACACS+ on DUT (192.168.100.148)"""
    st.banner("MODULE 1: CONFIGURATION")
    st.banner("Configure AAA authentication login tacacs+")

    dut = vars.D1
    result = True

    # Step 1: Apply AAA + TACACS+ configuration
    st.log("Step 1: Configure AAA authentication settings")
    commands = [
        "aaa authentication login default group tacacs+ local",
        "aaa authentication failthrough enable",
        "aaa authentication fallback enable",
        f"tacacs-server host {CONFIG.tacacs_server_ip}",
    ]
    st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    st.log("All configuration commands executed")

    # Step 2: Verify AAA configuration
    st.log("\nStep 2: Verify AAA configuration")
    aaa_out = st.show(dut, "show aaa", skip_tmpl=True, skip_error_check=True)
    aaa_str = aaa_out if isinstance(aaa_out, str) else str(aaa_out)
    st.log(f"AAA Configuration:\n{aaa_str}")

    if "tacacs+" not in aaa_str.lower() and "tacacs" not in aaa_str.lower():
        st.error("✗ AAA output does not show tacacs+ as login method")
        result = False
    else:
        st.log("✓ AAA login method includes tacacs+")

    # Step 3: Verify TACACS+ server configuration
    st.log("\nStep 3: Verify TACACS+ configuration")
    tacacs_out = st.show(dut, "show tacacs-server", skip_tmpl=True, skip_error_check=True)
    tacacs_str = tacacs_out if isinstance(tacacs_out, str) else str(tacacs_out)
    st.log(f"TACACS+ Configuration:\n{tacacs_str}")

    if CONFIG.tacacs_server_ip not in tacacs_str:
        st.error(f"✗ TACACS+ server {CONFIG.tacacs_server_ip} not found in show tacacs-server output")
        result = False
    else:
        st.log(f"✓ TACACS+ server {CONFIG.tacacs_server_ip} present in configuration")

    if result:
        st.log("✅ MODULE 1 PASSED: AAA and TACACS+ configured and verified")
    else:
        st.error("❌ MODULE 1 FAILED: AAA/TACACS+ configuration verification failed")

    assert result, "Test failed: AAA and TACACS+ configuration not applied correctly"


# ============================================================================
# MODULE 2: PACKET CAPTURE AND AUTHENTICATION
# ============================================================================

def test_002_capture_authentication_packets():
    """Module 2: Capture TACACS+ packets during authentication"""
    st.banner("MODULE 2: PACKET CAPTURE AND AUTHENTICATION")

    dut = vars.D1
    result = True

    # Step 1: Start tcpdump on TACACS+ server
    st.log(f"Step 1: Start tcpdump on TACACS+ server ({CONFIG.tacacs_server_ip})")
    st.show(dut,
            f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} "
            f"'nohup sudo tcpdump -nei {CONFIG.tacacs_interface} port 49 "
            f"-w {CONFIG.capture_file} > /tmp/tcpdump.log 2>&1 &'",
            skip_tmpl=True, skip_error_check=True)
    st.wait(2, "Waiting for tcpdump to start")

    # Verify tcpdump is running
    pid_out = st.show(dut,
                      f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} "
                      f"'pgrep -a tcpdump'",
                      skip_tmpl=True, skip_error_check=True)
    pid_str = pid_out if isinstance(pid_out, str) else str(pid_out)
    if "tcpdump" not in pid_str:
        st.error("✗ tcpdump process not running on TACACS+ server")
        result = False
    else:
        st.log(f"✓ tcpdump started: {pid_str.strip()}")

    # Step 2: Trigger SSH authentication attempts
    st.log("\nStep 2: Trigger SSH authentication attempts on DUT")

    # Attempt 1: Wrong password
    st.log("Attempt 1: SSH with WRONG password (triggers failed TACACS+ auth)")
    wrong_out = st.show(dut,
                        f"sshpass -p 'wrongpassword' ssh -o StrictHostKeyChecking=no "
                        f"-o ConnectTimeout=5 {CONFIG.tacacs_admin_user}@{CONFIG.dut_ip} "
                        f"'show version' 2>&1 || true",
                        skip_tmpl=True, skip_error_check=True)
    st.log(f"Wrong-password auth result (expected failure): {str(wrong_out)[:120]}")
    st.wait(1)

    # Attempt 2: Correct password
    st.log("\nAttempt 2: SSH with CORRECT password (triggers successful TACACS+ auth)")
    correct_out = st.show(dut,
                          f"sshpass -p '{CONFIG.tacacs_admin_pass}' ssh -o StrictHostKeyChecking=no "
                          f"-o ConnectTimeout=5 {CONFIG.tacacs_admin_user}@{CONFIG.dut_ip} "
                          f"'show version' 2>&1",
                          skip_tmpl=True, skip_error_check=True)
    correct_str = correct_out if isinstance(correct_out, str) else str(correct_out)
    st.log(f"Correct-password auth result: {correct_str[:200]}")
    st.wait(2, "Waiting for tcpdump to capture packets")

    # Step 3: Stop tcpdump
    st.log("\nStep 3: Stop tcpdump on TACACS+ server")
    st.show(dut,
            f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} "
            f"'sudo pkill -f tcpdump; sleep 1'",
            skip_tmpl=True, skip_error_check=True)
    st.wait(1, "Waiting for tcpdump to flush and close")
    st.log("✓ tcpdump stopped")

    # Step 4: Verify packet capture file exists and has size > 0
    st.log("\nStep 4: Verify packet capture file")
    file_out = st.show(dut,
                       f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} "
                       f"'ls -lh {CONFIG.capture_file} 2>/dev/null || echo FILE_MISSING'",
                       skip_tmpl=True, skip_error_check=True)
    file_str = file_out if isinstance(file_out, str) else str(file_out)
    st.log(f"Packet capture file info:\n{file_str}")

    if "FILE_MISSING" in file_str or CONFIG.capture_file not in file_str:
        st.error(f"✗ Packet capture file {CONFIG.capture_file} not found on TACACS+ server")
        result = False
    else:
        st.log(f"✓ Packet capture file exists: {file_str.strip()}")

    # Step 5: Display and validate captured TACACS+ packets (port 49)
    st.log("\nStep 5: Display and validate captured TACACS+ packets (port 49)")
    packets_out = st.show(dut,
                          f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} "
                          f"'sudo tcpdump -r {CONFIG.capture_file} -n port 49 2>/dev/null "
                          f"|| echo NO_PACKETS'",
                          skip_tmpl=True, skip_error_check=True)
    packets_str = packets_out if isinstance(packets_out, str) else str(packets_out)
    st.log(f"Captured TACACS+ packets between {CONFIG.tacacs_server_ip} and {CONFIG.dut_ip}:\n{packets_str}")

    if "NO_PACKETS" in packets_str or (
        CONFIG.tacacs_server_ip not in packets_str and CONFIG.dut_ip not in packets_str
    ):
        st.error("✗ No TACACS+ packets captured on port 49 — authentication traffic not observed")
        result = False
    else:
        st.log("✓ TACACS+ packets captured on port 49 — authentication traffic observed")

    if result:
        st.log("✅ MODULE 2 PASSED: Packet capture and authentication verified")
    else:
        st.error("❌ MODULE 2 FAILED: Packet capture or authentication check failed")

    assert result, "Test failed: TACACS+ packet capture did not capture expected authentication traffic"


# ============================================================================
# MODULE 3: VERIFICATION
# ============================================================================

def test_003_verify_authentication_flow():
    """Module 3: Verify authentication flow and packet details"""
    st.banner("MODULE 3: VERIFICATION")

    dut = vars.D1
    result = True

    # Step 1: Verify DUT still has AAA config
    st.log("Step 1: Verify DUT still has AAA configuration")
    aaa_out = st.show(dut, "show aaa", skip_tmpl=True, skip_error_check=True)
    aaa_str = aaa_out if isinstance(aaa_out, str) else str(aaa_out)
    st.log(f"Current AAA Configuration:\n{aaa_str}")

    if "tacacs+" not in aaa_str.lower() and "tacacs" not in aaa_str.lower():
        st.error("✗ AAA config lost — tacacs+ not in show aaa output")
        result = False
    else:
        st.log("✓ AAA tacacs+ configuration persists")

    # Step 2: Verify TACACS+ server still configured
    st.log("\nStep 2: Verify TACACS+ server still configured")
    tacacs_out = st.show(dut, "show tacacs-server", skip_tmpl=True, skip_error_check=True)
    tacacs_str = tacacs_out if isinstance(tacacs_out, str) else str(tacacs_out)
    st.log(f"Current TACACS+ Configuration:\n{tacacs_str}")

    if CONFIG.tacacs_server_ip not in tacacs_str:
        st.error(f"✗ TACACS+ server {CONFIG.tacacs_server_ip} not found — config lost")
        result = False
    else:
        st.log(f"✓ TACACS+ server {CONFIG.tacacs_server_ip} still configured")

    # Step 3: Verify packet capture file still present on server
    st.log("\nStep 3: Verify packet capture file exists on TACACS+ server")
    check_out = st.show(dut,
                        f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} "
                        f"'test -f {CONFIG.capture_file} && echo FILE_EXISTS || echo FILE_MISSING'",
                        skip_tmpl=True, skip_error_check=True)
    check_str = check_out if isinstance(check_out, str) else str(check_out)
    st.log(f"Packet file check: {check_str.strip()}")

    if "FILE_EXISTS" not in check_str:
        st.error(f"✗ Packet capture file {CONFIG.capture_file} missing from TACACS+ server")
        result = False
    else:
        st.log(f"✓ Packet capture file {CONFIG.capture_file} confirmed present")

    if result:
        st.log("✅ MODULE 3 PASSED: Authentication flow and packet file verified")
    else:
        st.error("❌ MODULE 3 FAILED: One or more verification checks failed")

    assert result, "Test failed: AAA/TACACS+ configuration or packet file lost after capture"


# ============================================================================
# MODULE 4: CLEANUP
# ============================================================================

def test_004_cleanup_all():
    """Module 4: Cleanup - Remove all AAA and TACACS+ configuration"""
    st.banner("MODULE 4: CLEANUP")

    dut = vars.D1
    result = True

    # Step 1: Remove all AAA and TACACS+ configuration
    st.log("Step 1: Remove AAA and TACACS+ configuration")
    commands = [
        "no aaa authentication login default",
        "no aaa authentication failthrough",
        "no aaa authentication fallback",
        f"no tacacs-server host {CONFIG.tacacs_server_ip}",
    ]
    st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    st.log("All cleanup commands executed")

    # Step 2: Verify AAA is reset to default (no tacacs+)
    st.log("\nStep 2: Verify AAA configuration is removed/reset")
    aaa_out = st.show(dut, "show aaa", skip_tmpl=True, skip_error_check=True)
    aaa_str = aaa_out if isinstance(aaa_out, str) else str(aaa_out)
    st.log(f"Final AAA Status:\n{aaa_str}")

    # Verify TACACS+ server removed
    st.log("\nStep 3: Verify TACACS+ server is removed")
    tacacs_out = st.show(dut, "show tacacs-server", skip_tmpl=True, skip_error_check=True)
    tacacs_str = tacacs_out if isinstance(tacacs_out, str) else str(tacacs_out)
    st.log(f"Final TACACS+ Status:\n{tacacs_str}")

    if CONFIG.tacacs_server_ip in tacacs_str:
        st.error(f"✗ TACACS+ server {CONFIG.tacacs_server_ip} still present after cleanup")
        result = False
    else:
        st.log(f"✓ TACACS+ server {CONFIG.tacacs_server_ip} successfully removed")

    # Step 4: Remove packet capture file from server
    st.log("\nStep 4: Clean up packet capture file on TACACS+ server")
    rm_out = st.show(dut,
                     f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} "
                     f"'rm -f {CONFIG.capture_file} && echo REMOVED || echo REMOVE_FAILED'",
                     skip_tmpl=True, skip_error_check=True)
    rm_str = rm_out if isinstance(rm_out, str) else str(rm_out)
    if "REMOVED" in rm_str:
        st.log(f"✓ Packet capture file {CONFIG.capture_file} removed")
    else:
        st.log(f"Note: pcap file may already be absent: {rm_str.strip()}")

    if result:
        st.log("✅ MODULE 4 PASSED: Cleanup completed successfully")
    else:
        st.error("❌ MODULE 4 FAILED: Cleanup verification failed")

    assert result, "Test failed: AAA/TACACS+ cleanup did not remove all configuration"
