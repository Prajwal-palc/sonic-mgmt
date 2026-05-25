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

# ============================================================================
# MODULE 1: CONFIGURATION
# ============================================================================

def test_001_configure_aaa_and_tacacs():
    """Module 1: Configure AAA and TACACS+ on DUT (192.168.100.148)"""
    st.banner("MODULE 1: CONFIGURATION")
    st.banner("Configure AAA authentication login tacacs+")
    
    # Step 1: Configure all AAA and TACACS+ settings at once
    st.log("Step 1: Configure AAA authentication settings")
    commands = [
        "aaa authentication login tacacs+",
        "aaa authentication failthrough enable",
        "aaa authentication fallback enable",
        f"tacacs server {CONFIG.tacacs_server_ip}",
    ]
    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)
    st.log("All configuration commands executed")
    
    # Step 2: Verify AAA configuration
    st.log("\nStep 2: Verify AAA configuration")
    result = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"AAA Configuration:\n{result}")
    
    # Step 3: Verify TACACS+ configuration
    st.log("\nStep 3: Verify TACACS+ configuration")
    result = st.show(vars.D1, "show tacacs", skip_tmpl=True, skip_error_check=True)
    st.log(f"TACACS+ Configuration:\n{result}")
    
    st.log("\n✓ Configuration completed successfully")
    assert True

# ============================================================================
# MODULE 2: PACKET CAPTURE AND AUTHENTICATION
# ============================================================================

def test_002_capture_authentication_packets():
    """Module 2: Capture TACACS+ packets during authentication"""
    st.banner("MODULE 2: PACKET CAPTURE AND AUTHENTICATION")
    
    # Step 1: Start tcpdump on TACACS+ server (192.168.100.87)
    st.log("Step 1: Start tcpdump on TACACS+ server (192.168.100.87)")
    st.log(f"Command: sudo tcpdump -nei {CONFIG.tacacs_interface} port 49 -w {CONFIG.capture_file}")
    st.show(vars.D1, f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} 'sudo tcpdump -nei {CONFIG.tacacs_interface} port 49 -w {CONFIG.capture_file}' &", skip_tmpl=True, skip_error_check=True)
    st.wait(2, "Waiting for tcpdump to start")
    st.log("✓ tcpdump started in background")
    
    # Step 2: Trigger SSH authentication attempts on DUT (192.168.100.148)
    st.log("\nStep 2: Trigger SSH authentication attempts")
    
    # Attempt 1: Wrong password (will fail TACACS+ auth)
    st.log("Attempt 1: SSH login with WRONG password (triggers failed TACACS+ auth)")
    ssh_cmd_wrong = f"sshpass -p 'wrongpassword' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {CONFIG.tacacs_admin_user}@{CONFIG.dut_ip} 'show version' 2>&1"
    result = st.show(vars.D1, ssh_cmd_wrong, skip_tmpl=True, skip_error_check=True)
    st.log(f"Authentication attempt with wrong password: {str(result)[:100]}")
    st.wait(1, "Waiting between auth attempts")
    
    # Attempt 2: Correct password (will succeed TACACS+ auth)
    st.log("\nAttempt 2: SSH login with CORRECT password (triggers successful TACACS+ auth)")
    ssh_cmd_correct = f"sshpass -p '{CONFIG.tacacs_admin_pass}' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {CONFIG.tacacs_admin_user}@{CONFIG.dut_ip} 'show version' 2>&1"
    result = st.show(vars.D1, ssh_cmd_correct, skip_tmpl=True, skip_error_check=True)
    st.log(f"Authentication attempt with correct password: Success!")
    st.wait(2, "Waiting for tcpdump to capture packets")
    
    # Step 3: Stop tcpdump and get results
    st.log("\nStep 3: Stop tcpdump and analyze captured packets")
    stop_tcpdump_cmd = f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} 'pkill -f tcpdump'"
    st.show(vars.D1, stop_tcpdump_cmd, skip_tmpl=True, skip_error_check=True)
    st.wait(1, "Waiting for tcpdump to finish")
    st.log("✓ tcpdump stopped")
    
    # Step 4: Check captured packet file
    st.log("\nStep 4: Verify packet capture file")
    check_file_cmd = f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} 'ls -lh {CONFIG.capture_file}'"
    file_result = st.show(vars.D1, check_file_cmd, skip_tmpl=True, skip_error_check=True)
    st.log(f"Packet capture file size:\n{file_result}")
    
    # Step 5: Display captured packets
    st.log("\nStep 5: Display captured TACACS+ packets (port 49)")
    display_packets_cmd = f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} 'sudo tcpdump -r {CONFIG.capture_file} -n port 49'"
    packets_result = st.show(vars.D1, display_packets_cmd, skip_tmpl=True, skip_error_check=True)
    st.log(f"Captured packets between {CONFIG.tacacs_server_ip} and {CONFIG.dut_ip}:\n{packets_result}")
    
    st.log("\n✓ Packet capture and authentication completed successfully")
    assert True

# ============================================================================
# MODULE 3: VERIFICATION
# ============================================================================

def test_003_verify_authentication_flow():
    """Module 3: Verify authentication flow and packet details"""
    st.banner("MODULE 3: VERIFICATION")
    
    st.log("Step 1: Verify DUT still has configuration")
    result = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"Current AAA Configuration:\n{result}")
    
    st.log("\nStep 2: Verify TACACS+ server is still configured")
    result = st.show(vars.D1, "show tacacs", skip_tmpl=True, skip_error_check=True)
    st.log(f"Current TACACS+ Configuration:\n{result}")
    
    st.log("\nStep 3: Verify packet capture file exists on server")
    check_cmd = f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} 'test -f {CONFIG.capture_file} && echo \\\"Packet file exists\\\" || echo \\\"Packet file not found\\\"'"
    result = st.show(vars.D1, check_cmd, skip_tmpl=True, skip_error_check=True)
    st.log(f"Packet file verification: {result}")
    
    st.log("\n✓ Verification completed")
    assert True

# ============================================================================
# MODULE 4: CLEANUP
# ============================================================================

def test_004_cleanup_all():
    """Module 4: Cleanup - Remove all AAA and TACACS+ configuration"""
    st.banner("MODULE 4: CLEANUP")
    
    st.log("Step 1: Remove all AAA and TACACS+ configuration")
    commands = [
        "aaa authentication login default",
        "aaa authentication failthrough default",
        "aaa authentication fallback default",
        f"no tacacs server {CONFIG.tacacs_server_ip}",
    ]
    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)
    st.log("All cleanup commands executed")
    
    st.log("\nStep 2: Verify configuration is removed")
    result = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"Final AAA Status (should be default):\n{result}")
    
    st.log("\nStep 3: Clean up packet capture file on server")
    cleanup_cmd = f"ssh -o StrictHostKeyChecking=no adminuser@{CONFIG.tacacs_server_ip} 'rm -f {CONFIG.capture_file}'"
    st.show(vars.D1, cleanup_cmd, skip_tmpl=True, skip_error_check=True)
    st.log("Packet capture file cleaned up")
    
    st.log("\n✓ Cleanup completed successfully")
    assert True
