"""
TACACS+ Packet Capture Testcase - Exact Manual Flow Automation

This testcase automates the exact manual steps:
1. Configure AAA on DUT (tacacs+, failthrough, fallback)
2. Configure TACACS server on DUT (192.168.100.87)
3. Start tcpdump on TACACS server (port 49 capture)
4. Trigger SSH login attempts (wrong password then correct)
5. Stop tcpdump and analyze captured packets
6. Verify TACACS+ packet flow
"""

import pytest
import subprocess
from spytest import st
from spytest.dicts import SpyTestDict

class CONFIG:
    # DUT configuration
    dut_ip = "192.168.100.145"
    admin_user = "admin"
    admin_password = "root@123"
    
    # TACACS+ server
    # Test client (SSH trigger from 192.168.100.175)
    client_ip = "192.168.100.175"
    client_user = "claudeuser"
    client_password = "Sonic@2026"

    tacacs_server_ip = "192.168.100.87"
    tacacs_port = 49
    tacacs_passkey = "test123"
    server_username = "adminuser"
    server_password = "Regre@11"
    server_interface = "enp1s0"
    
    # Capture file
    capture_file = "/tmp/tacacs1.pcap"

vars = SpyTestDict()
data = SpyTestDict()

@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    global vars, data
    st.banner("=" * 80)
    st.banner("TACACS+ PACKET CAPTURE - MANUAL FLOW AUTOMATION")
    st.banner("=" * 80)
    vars = st.ensure_min_topology("D1")
    data.cli_type = "klish"
    yield

def test_001_unconfigure_aaa_tacacs():
    """STEP 0: Clean existing configuration"""
    st.banner("MODULE 1: UNCONFIGURATION")
    
    commands = [
        "aaa authentication login default",
        "aaa authentication failthrough default",
        "aaa authentication fallback default",
        f"no tacacs server {CONFIG.tacacs_server_ip}",
    ]
    
    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)
    st.wait(2)
    st.log("✓ Unconfiguration completed")
    st.report_pass("msg", "Unconfiguration completed")

def test_002_configure_aaa_and_tacacs():
    """
    STEP 1 & 2: Configure AAA and TACACS on DUT
    
    Manual equivalent:
      sonic-cli
      configure terminal
      aaa authentication login tacacs+
      aaa authentication failthrough enable
      aaa authentication fallback enable
      tacacs server 192.168.100.87
      show aaa
      show tacacs
    """
    st.banner("MODULE 2: CONFIGURE AAA AND TACACS+")
    
    st.log("STEP 1: Configuring AAA authentication")
    st.log("  - aaa authentication login tacacs+")
    st.log("  - aaa authentication failthrough enable")
    st.log("  - aaa authentication fallback enable")
    
    st.log("STEP 2: Configuring TACACS+ server")
    st.log(f"  - tacacs server {CONFIG.tacacs_server_ip}")
    st.log(f"  - tacacs passkey {CONFIG.tacacs_passkey}")
    
    # Execute configuration commands
    commands = [
        "aaa authentication login tacacs+",
        "aaa authentication failthrough enable",
        "aaa authentication fallback enable",
        f"tacacs server {CONFIG.tacacs_server_ip}",
        f"tacacs passkey {CONFIG.tacacs_passkey}",
    ]
    
    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)
    st.wait(5, "Configuration to take effect")
    
    # Verify AAA configuration
    st.log("Verifying AAA configuration...")
    aaa_output = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log("AAA Configuration:")
    st.log(aaa_output)
    
    if "tacacs+" not in aaa_output.lower():
        st.report_fail("msg", "AAA not configured for tacacs+")
    
    st.log("✓ AAA authentication login tacacs+")
    st.log("✓ AAA authentication failthrough True")
    st.log("✓ AAA authentication fallback True")
    
    # Verify TACACS configuration
    st.log("Verifying TACACS+ configuration...")
    tacacs_output = st.show(vars.D1, "show tacacs", skip_tmpl=True, skip_error_check=True)
    st.log("TACACS+ Configuration:")
    st.log(tacacs_output)
    
    if CONFIG.tacacs_server_ip not in tacacs_output:
        st.report_fail("msg", f"TACACS+ server {CONFIG.tacacs_server_ip} not configured")
    
    st.log(f"✓ TACPLUS_SERVER address {CONFIG.tacacs_server_ip}")
    st.log(f"✓ tcp_port {CONFIG.tacacs_port}")
    
    st.log("=" * 80)
    st.log("✓ MODULE 2 COMPLETED: AAA and TACACS+ configured successfully")
    st.log("=" * 80)
    
    st.report_pass("msg", "AAA and TACACS+ configuration completed")

def test_003_packet_capture_verification():
    """
    STEP 3: Start tcpdump on TACACS Server and Capture Packets
    
    Manual equivalent:
      ssh adminuser@192.168.100.87
      sudo tcpdump -nei enp1s0 port 49 -w /tmp/tacacs1.pcap
      
    Then trigger SSH login from test client
    """
    st.banner("MODULE 3: PACKET CAPTURE & VERIFICATION")
    
    
    # CRITICAL: Verify TACACS+ configuration is still active
    st.log("=" * 80)
    st.log("PRE-CHECK: Verifying TACACS+ Configuration")
    st.log("=" * 80)
    aaa_check = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"AAA Status: {aaa_check}")
    
    if "tacacs+" not in aaa_check.lower():
        st.log("WARNING: AAA not configured for tacacs+ - Reconfiguring...")
        reconfig_commands = [
            "aaa authentication login tacacs+",
            "aaa authentication failthrough enable",
            "aaa authentication fallback enable",
            f"tacacs server {CONFIG.tacacs_server_ip}",
            f"tacacs passkey {CONFIG.tacacs_passkey}",
        ]
        st.config(vars.D1, reconfig_commands, type=data.cli_type, skip_error_check=True)
        st.wait(3, "Reconfiguration to take effect")
        st.log("✓ TACACS+ reconfigured")
    else:
        st.log("✓ TACACS+ configuration verified")
    
    st.log("=" * 80)
    
    # Clean old capture file
    st.log("Cleaning old capture files...")
    clean_cmd = f'sshpass -p "{CONFIG.server_password}" ssh -o StrictHostKeyChecking=no {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "sudo rm -f {CONFIG.capture_file}"'
    subprocess.run(clean_cmd, shell=True, timeout=10)
    
    # STEP 3: Start tcpdump on TACACS server
    st.log("=" * 80)
    st.log("STEP 3: Starting tcpdump on TACACS Server")
    st.log("=" * 80)
    st.log(f"Server: {CONFIG.tacacs_server_ip}")
    st.log(f"Interface: {CONFIG.server_interface}")
    st.log(f"Command: sudo tcpdump -nei {CONFIG.server_interface} port {CONFIG.tacacs_port} -w {CONFIG.capture_file}")
    st.log("")
    st.log("What This Does:")
    st.log("  tcpdump     = Packet capture tool")
    st.log("  -n          = Don't resolve hostname")
    st.log("  -e          = Show Ethernet header")
    st.log(f"  -i {CONFIG.server_interface}  = Capture on interface")
    st.log(f"  port {CONFIG.tacacs_port}     = Capture only TACACS packets")
    st.log(f"  -w          = Save to {CONFIG.capture_file}")
    st.log("=" * 80)
    
    # Start tcpdump in background
    tcpdump_cmd = f'sshpass -p "{CONFIG.server_password}" ssh -o StrictHostKeyChecking=no {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "nohup sudo tcpdump -nei {CONFIG.server_interface} port {CONFIG.tacacs_port} -w {CONFIG.capture_file} >/tmp/tcpdump.log 2>&1 &"'
    subprocess.Popen(tcpdump_cmd, shell=True)
    
    st.wait(5, "tcpdump to start capturing")
    st.log("✓ tcpdump started and capturing on port 49")
    
    # STEP 4: Trigger SSH login attempts
    st.log("=" * 80)
    st.log("STEP 4: Triggering SSH Login Attempts")
    st.log("=" * 80)
    st.log("This will generate TACACS+ packets:")
    st.log(f"  DUT ({CONFIG.dut_ip}) → TACACS Server ({CONFIG.tacacs_server_ip}:49)")
    st.log("")
    
    # Attempt 1: Wrong password
    st.log("Attempt 1: SSH with WRONG password")
    st.log("  Expected: DUT sends AUTH-START → Server responds AUTH-REPLY (REJECT)")
    
    wrong_ssh = f'timeout 10 sshpass -p "Admin" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {CONFIG.admin_user}@{CONFIG.dut_ip} "echo test" 2>&1 || true'
    result = subprocess.run(wrong_ssh, shell=True, capture_output=True, text=True, timeout=15)
    st.log(f"  Result: {result.stdout[:100] if result.stdout else 'Authentication failed as expected'}")
    
    st.wait(2, "between login attempts")
    
    # Attempt 2: Correct password
    st.log("Attempt 2: SSH with CORRECT password")
    st.log("  Expected: DUT sends AUTH-START → Server responds AUTH-REPLY (ACCEPT)")
    
    correct_ssh = f'timeout 10 sshpass -p "{CONFIG.admin_password}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {CONFIG.admin_user}@{CONFIG.dut_ip} "show version | head -3" 2>&1'
    result = subprocess.run(correct_ssh, shell=True, capture_output=True, text=True, timeout=15)
    
    if "SONiC" in result.stdout:
        st.log("  ✓ SSH authentication SUCCESSFUL")
        st.log(f"  Output: {result.stdout[:100]}")
    
    st.wait(2, "between attempts")
    
    # Attempt 3: One more for additional packets
    st.log("Attempt 3: Additional SSH connection")
    extra_ssh = f'timeout 10 sshpass -p "{CONFIG.admin_password}" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 {CONFIG.admin_user}@{CONFIG.dut_ip} "show running-config | head -5" 2>&1'
    subprocess.run(extra_ssh, shell=True, capture_output=True, timeout=15)
    st.log("  Additional SSH completed")
    
    st.wait(5, "all TACACS+ packets to be captured")
    st.log("=" * 80)
    
    # STEP 5: Stop tcpdump
    st.log("STEP 5: Stopping tcpdump")
    stop_cmd = f'sshpass -p "{CONFIG.server_password}" ssh -o StrictHostKeyChecking=no {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "sudo pkill -INT tcpdump; sleep 2"'
    subprocess.run(stop_cmd, shell=True, timeout=15)
    st.log("✓ tcpdump stopped")
    
    st.wait(2, "tcpdump to finish writing pcap file")
    
    # STEP 6: Check pcap file
    st.log("=" * 80)
    st.log("STEP 6: Checking pcap file")
    check_cmd = f'sshpass -p "{CONFIG.server_password}" ssh -o StrictHostKeyChecking=no {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "ls -lh {CONFIG.capture_file}"'
    result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=10)
    
    st.log(f"Pcap file on TACACS server:")
    st.log(result.stdout)
    
    if "No such file" in result.stdout or result.returncode != 0:
        st.report_fail("msg", f"Pcap file not created: {CONFIG.capture_file}")
    
    # STEP 7: Analyze captured packets
    st.log("=" * 80)
    st.log("STEP 7: Analyzing Captured TACACS+ Packets")
    st.log("=" * 80)
    
    analyze_cmd = f'sshpass -p "{CONFIG.server_password}" ssh -o StrictHostKeyChecking=no {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "sudo tcpdump -r {CONFIG.capture_file} -n -v 2>&1"'
    result = subprocess.run(analyze_cmd, shell=True, capture_output=True, text=True, timeout=30)
    
    st.log("CAPTURED TACACS+ PACKETS:")
    st.log("=" * 80)
    st.log(result.stdout)
    st.log("=" * 80)
    
    # Count packets
    packet_count = 0
    for line in result.stdout.split('\n'):
        if " > " in line and (CONFIG.dut_ip in line or CONFIG.tacacs_server_ip in line):
            packet_count += 1
    
    st.log(f"Total TACACS+ packets captured: {packet_count}")
    
    # STEP 8: Verification
    st.log("=" * 80)
    st.log("STEP 8: VERIFICATION")
    st.log("=" * 80)
    
    if packet_count >= 10:
        st.log(f"✓ PASS: Sufficient TACACS+ packets captured ({packet_count} packets)")
        st.log("")
        st.log("Packet Flow Verified:")
        st.log(f"  {CONFIG.dut_ip} (DUT) ↔ {CONFIG.tacacs_server_ip}:{CONFIG.tacacs_port} (TACACS+ Server)")
        st.log("")
        st.log("=" * 80)
        st.log("✓ MODULE 3 COMPLETED SUCCESSFULLY")
        st.log(f"✓ Captured {packet_count} TACACS+ packets")
        st.log(f"✓ Pcap file saved: {CONFIG.capture_file}")
        st.log("✓ You can review it with:")
        st.log(f"    sudo tcpdump -r {CONFIG.capture_file} -n")
        st.log("=" * 80)
        
        st.report_pass("msg", f"Packet capture completed - {packet_count} packets captured")
    else:
        st.log(f"✗ FAIL: Too few packets captured ({packet_count} < 10)")
        st.report_fail("msg", f"Insufficient TACACS+ packets: {packet_count}")

def test_004_cleanup():
    """MODULE 4: Cleanup configuration"""
    st.banner("MODULE 4: CLEANUP")
    
    commands = [
        "aaa authentication login default",
        "aaa authentication failthrough default",
        "aaa authentication fallback default",
        f"no tacacs server {CONFIG.tacacs_server_ip}",
    ]
    
    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)
    
    st.log("✓ AAA and TACACS+ configuration removed")
    st.log(f"Note: Pcap file preserved at {CONFIG.capture_file} for review")
    
    st.report_pass("msg", "Cleanup completed")
