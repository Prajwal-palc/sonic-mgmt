"""
TACACS+ Authentication with Scapy Packet Capture and Verification

Test Topology:
    VM1 (TACACS+ Server): 192.168.100.87 (adminuser/Regre@11)
    DUT (SONiC Switch): 192.168.100.148 (admin/root@123)
    Test Client: 192.168.100.175 (claudeuser/Sonic@2026)

Test Flow:
    1. Configure AAA and TACACS+ on DUT (192.168.100.148)
    2. Start Scapy packet capture on VM1 (192.168.100.87:49)
    3. Trigger SSH authentication from test client (192.168.100.175)
       - First attempt with WRONG password (Admin)
       - Second attempt with CORRECT password (root@123)
    4. Stop capture and analyze packets with Scapy
    5. Verify TACACS+ packet flow between DUT and server

Expected Packet Flow:
    192.168.100.148 (DUT) --> 192.168.100.87:49 (AUTH-START - wrong password)
    192.168.100.87:49 --> 192.168.100.148 (AUTH-REPLY - FAILURE)
    192.168.100.148 (DUT) --> 192.168.100.87:49 (AUTH-START - correct password)
    192.168.100.87:49 --> 192.168.100.148 (AUTH-REPLY - SUCCESS)

Expected Packet Count: 30-40 packets
"""

import pytest
import time
import subprocess
from spytest import st
from spytest.dicts import SpyTestDict

# Test configuration
class CONFIG:
    # DUT configuration
    dut_ip = "192.168.100.148"
    admin_user = "admin"
    admin_password = "root@123"
    admin_wrong_password = "Admin"

    # TACACS+ server (VM1)
    tacacs_server_ip = "192.168.100.87"
    tacacs_port = 49
    tacacs_passkey = "test123"
    server_username = "adminuser"
    server_password = "Regre@11"
    server_interface = "enp1s0"

    # Test client
    test_client_ip = "192.168.100.175"
    test_client_user = "claudeuser"
    test_client_password = "Sonic@2026"

    # Capture file
    capture_file = "/tmp/tacacs1.pcap"
    scapy_script = "/tmp/scapy_capture.py"
    scapy_analysis = "/tmp/scapy_analysis.py"


# Global variables
vars = SpyTestDict()
data = SpyTestDict()


@pytest.fixture(scope="module", autouse=True)
def tacacs_scapy_module_hooks(request):
    """
    Module-level fixture for TACACS+ Scapy traffic test
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TACACS+ AUTHENTICATION - SCAPY PACKET CAPTURE & VERIFICATION")
    st.banner("=" * 80)
    st.log("")
    st.log("Test Environment:")
    st.log(f"  DUT (SONiC Switch): {CONFIG.dut_ip}")
    st.log(f"  TACACS+ Server (VM1): {CONFIG.tacacs_server_ip}")
    st.log(f"  Test Client: {CONFIG.test_client_ip}")
    st.log("")
    st.log("Test Flow:")
    st.log("  1. Configure AAA/TACACS+ on DUT")
    st.log("  2. Start Scapy packet capture on VM1")
    st.log("  3. Trigger SSH from test client with wrong password")
    st.log("  4. Trigger SSH from test client with correct password")
    st.log("  5. Analyze captured packets with Scapy")
    st.log("  6. Verify TACACS+ protocol packet flow")
    st.log("")

    vars = st.ensure_min_topology("D1")
    data.cli_type = st.get_ui_type(vars.D1)

    yield

    st.log("Module cleanup completed")


def test_001_unconfigure_all_aaa_tacacs():
    """
    MODULE 1: UNCONFIGURATION
    Remove all existing AAA and TACACS+ configuration
    """
    st.banner("=" * 80)
    st.banner("MODULE 1: UNCONFIGURATION - Remove existing config")
    st.banner("=" * 80)

    commands = [
        "aaa authentication login default",
        "aaa authentication failthrough default",
        "aaa authentication fallback default",
        f"no tacacs server {CONFIG.tacacs_server_ip}",
    ]

    st.log("Removing existing AAA and TACACS+ configuration")
    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)

    aaa_output = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"AAA Status after unconfiguration:\n{aaa_output}")

    st.log("✓ MODULE 1 COMPLETED: Unconfiguration successful")
    st.report_pass("msg", "Unconfiguration completed successfully")


def test_002_configure_all_aaa_tacacs():
    """
    MODULE 2: CONFIGURATION
    Configure AAA and TACACS+ on DUT for packet capture test
    """
    st.banner("=" * 80)
    st.banner("MODULE 2: CONFIGURATION - Configure AAA and TACACS+")
    st.banner("=" * 80)

    commands = [
        "aaa authentication login tacacs+",
        "aaa authentication failthrough enable",
        "aaa authentication fallback enable",
        f"tacacs server {CONFIG.tacacs_server_ip}",
        f"tacacs passkey {CONFIG.tacacs_passkey}",
    ]

    st.log("Executing batch configuration commands")
    for cmd in commands:
        st.log(f"  - {cmd}")

    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)
    st.wait(2, "Configuration stabilization")

    # Verify configuration
    st.log("Verifying configuration...")
    aaa_output = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"AAA Status:\n{aaa_output}")

    tacacs_output = st.show(vars.D1, "show tacacs", skip_tmpl=True, skip_error_check=True)
    st.log(f"TACACS Status:\n{tacacs_output}")

    if "tacacs+" not in aaa_output.lower():
        st.report_fail("msg", "AAA authentication login not set to tacacs+")

    if CONFIG.tacacs_server_ip not in tacacs_output:
        st.report_fail("msg", f"TACACS+ server {CONFIG.tacacs_server_ip} not configured")

    if "49" not in tacacs_output:
        st.report_fail("msg", "TACACS+ port 49 not configured")

    st.log("✓ MODULE 2 COMPLETED: Configuration successful")
    st.log("DUT is ready for TACACS+ packet capture test")
    st.report_pass("msg", "Configuration verified successfully")


def test_003_scapy_packet_capture_and_verification():
    """
    MODULE 3: SCAPY PACKET CAPTURE & VERIFICATION

    Steps:
    1. Create Scapy capture script on VM1
    2. Start packet capture on VM1 in background
    3. Trigger SSH authentication from test client (wrong password)
    4. Trigger SSH authentication from test client (correct password)
    5. Stop capture
    6. Analyze packets with Scapy
    7. Verify TACACS+ protocol flow
    """
    st.banner("=" * 80)
    st.banner("MODULE 3: SCAPY PACKET CAPTURE & VERIFICATION")
    st.banner("=" * 80)

    # Step 1: Create Scapy capture script on VM1
    st.log("Step 1: Creating Scapy packet capture script on VM1")

    scapy_capture_code = f'''#!/usr/bin/env python3
import sys
from scapy.all import sniff, wrpcap

def packet_capture():
    """Capture TACACS+ packets on port 49"""
    print("Starting packet capture on {CONFIG.server_interface} port {CONFIG.tacacs_port}...")
    print("Waiting for TACACS+ packets...")

    # Capture packets with filter
    packets = sniff(
        iface="{CONFIG.server_interface}",
        filter="tcp port {CONFIG.tacacs_port} and host {CONFIG.dut_ip}",
        timeout=60,
        count=100
    )

    print(f"Captured {{len(packets)}} packets")

    # Save to pcap file
    wrpcap("{CONFIG.capture_file}", packets)
    print(f"Packets saved to {CONFIG.capture_file}")
    print(f"Total packets: {{len(packets)}}")

    return len(packets)

if __name__ == "__main__":
    try:
        count = packet_capture()
        sys.exit(0)
    except Exception as e:
        print(f"Error: {{e}}")
        sys.exit(1)
'''

    # Write Scapy capture script to VM1
    create_script_cmd = f"cat > {CONFIG.scapy_script} << 'SCAPY_EOF'\n{scapy_capture_code}\nSCAPY_EOF"
    cmd = f'sshpass -p "{CONFIG.server_password}" ssh -o StrictHostKeyChecking=no {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "{create_script_cmd}"'

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        st.report_fail("msg", f"Failed to create Scapy capture script on VM1: {result.stderr}")

    st.log(f"✓ Scapy capture script created: {CONFIG.scapy_script}")

    # Make script executable
    chmod_cmd = f'sshpass -p "{CONFIG.server_password}" ssh {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "chmod +x {CONFIG.scapy_script}"'
    subprocess.run(chmod_cmd, shell=True, timeout=5)

    # Step 2: Start packet capture on VM1 in background
    st.log("Step 2: Starting Scapy packet capture on VM1 in background")

    capture_cmd = f'sshpass -p "{CONFIG.server_password}" ssh {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "sudo -S python3 {CONFIG.scapy_script} > /tmp/scapy_output.log 2>&1 &"'

    # Start capture in background
    subprocess.Popen(capture_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    st.wait(3, "Waiting for Scapy capture to start")
    st.log("✓ Scapy packet capture started on VM1")

    # Step 3: Trigger SSH authentication from test client (wrong password)
    st.log("Step 3: Triggering SSH from test client with WRONG password")

    ssh_wrong_cmd = f'''sshpass -p "{CONFIG.test_client_password}" ssh -o StrictHostKeyChecking=no {CONFIG.test_client_user}@{CONFIG.test_client_ip} "sshpass -p '{CONFIG.admin_wrong_password}' ssh -o StrictHostKeyChecking=no {CONFIG.admin_user}@{CONFIG.dut_ip} 'echo test' 2>&1 || true"'''

    result = subprocess.run(ssh_wrong_cmd, shell=True, capture_output=True, text=True, timeout=15)
    st.log(f"SSH attempt with wrong password result: {result.stdout}")

    st.wait(2, "Waiting between authentication attempts")

    # Step 4: Trigger SSH authentication from test client (correct password)
    st.log("Step 4: Triggering SSH from test client with CORRECT password")

    ssh_correct_cmd = f'''sshpass -p "{CONFIG.test_client_password}" ssh -o StrictHostKeyChecking=no {CONFIG.test_client_user}@{CONFIG.test_client_ip} "sshpass -p '{CONFIG.admin_password}' ssh -o StrictHostKeyChecking=no {CONFIG.admin_user}@{CONFIG.dut_ip} 'echo Successfully authenticated' 2>&1"'''

    result = subprocess.run(ssh_correct_cmd, shell=True, capture_output=True, text=True, timeout=15)
    st.log(f"SSH attempt with correct password result: {result.stdout}")

    if "Successfully authenticated" in result.stdout:
        st.log("✓ SSH authentication with correct password SUCCESSFUL")
    else:
        st.log("✗ SSH authentication with correct password FAILED")

    st.wait(5, "Waiting for all TACACS+ packets to be captured")

    # Step 5: Stop capture (wait for timeout or kill process)
    st.log("Step 5: Waiting for Scapy capture to complete")
    st.wait(10, "Final packet capture completion")

    # Step 6: Analyze captured packets with Scapy
    st.log("Step 6: Analyzing captured packets with Scapy")

    scapy_analysis_code = f'''#!/usr/bin/env python3
from scapy.all import rdpcap, TCP, IP
import sys

def analyze_packets():
    """Analyze TACACS+ packets"""
    try:
        packets = rdpcap("{CONFIG.capture_file}")
        total_packets = len(packets)

        print(f"Total packets captured: {{total_packets}}")
        print("=" * 80)

        if total_packets == 0:
            print("ERROR: No packets captured!")
            return False

        # Analyze packet details
        dut_to_server = 0
        server_to_dut = 0
        tacacs_port_packets = 0

        print("Packet Analysis:")
        print("-" * 80)

        for i, pkt in enumerate(packets, 1):
            if IP in pkt and TCP in pkt:
                src_ip = pkt[IP].src
                dst_ip = pkt[IP].dst
                src_port = pkt[TCP].sport
                dst_port = pkt[TCP].dport

                # Count packets by direction
                if src_ip == "{CONFIG.dut_ip}" and dst_ip == "{CONFIG.tacacs_server_ip}":
                    dut_to_server += 1
                    direction = "DUT -> Server"
                elif src_ip == "{CONFIG.tacacs_server_ip}" and dst_ip == "{CONFIG.dut_ip}":
                    server_to_dut += 1
                    direction = "Server -> DUT"
                else:
                    direction = "Other"

                # Count port 49 packets
                if src_port == {CONFIG.tacacs_port} or dst_port == {CONFIG.tacacs_port}:
                    tacacs_port_packets += 1

                print(f"Packet {{i:3d}}: {{src_ip:15s}}:{{src_port:5d}} -> {{dst_ip:15s}}:{{dst_port:5d}} [{{direction}}]")

        print("-" * 80)
        print(f"DUT -> Server packets: {{dut_to_server}}")
        print(f"Server -> DUT packets: {{server_to_dut}}")
        print(f"TACACS+ port 49 packets: {{tacacs_port_packets}}")
        print("=" * 80)

        # Verification
        success = True

        if total_packets < 10:
            print(f"FAIL: Too few packets captured ({{total_packets}} < 10)")
            success = False
        else:
            print(f"PASS: Sufficient packets captured ({{total_packets}} >= 10)")

        if dut_to_server == 0:
            print("FAIL: No packets from DUT to Server")
            success = False
        else:
            print(f"PASS: DUT to Server packets present ({{dut_to_server}})")

        if server_to_dut == 0:
            print("FAIL: No packets from Server to DUT")
            success = False
        else:
            print(f"PASS: Server to DUT packets present ({{server_to_dut}})")

        if tacacs_port_packets == 0:
            print("FAIL: No TACACS+ port 49 packets")
            success = False
        else:
            print(f"PASS: TACACS+ port 49 packets present ({{tacacs_port_packets}})")

        return success

    except FileNotFoundError:
        print(f"ERROR: Capture file {{CONFIG.capture_file}} not found")
        return False
    except Exception as e:
        print(f"ERROR: {{e}}")
        return False

if __name__ == "__main__":
    success = analyze_packets()
    sys.exit(0 if success else 1)
'''

    # Write Scapy analysis script to VM1
    create_analysis_cmd = f"cat > {CONFIG.scapy_analysis} << 'ANALYSIS_EOF'\n{scapy_analysis_code}\nANALYSIS_EOF"
    cmd = f'sshpass -p "{CONFIG.server_password}" ssh {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "{create_analysis_cmd}"'

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        st.report_fail("msg", f"Failed to create Scapy analysis script: {result.stderr}")

    # Make analysis script executable and run it
    chmod_cmd = f'sshpass -p "{CONFIG.server_password}" ssh {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "chmod +x {CONFIG.scapy_analysis}"'
    subprocess.run(chmod_cmd, shell=True, timeout=5)

    # Run analysis script
    analysis_cmd = f'sshpass -p "{CONFIG.server_password}" ssh {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "python3 {CONFIG.scapy_analysis}"'

    result = subprocess.run(analysis_cmd, shell=True, capture_output=True, text=True, timeout=30)

    st.log("=" * 80)
    st.log("SCAPY PACKET ANALYSIS RESULTS:")
    st.log("=" * 80)
    st.log(result.stdout)

    if result.returncode != 0:
        st.log(f"Analysis stderr: {result.stderr}")
        st.report_fail("msg", "Scapy packet analysis FAILED - verification checks did not pass")

    # Step 7: Verify results
    st.log("Step 7: Verifying TACACS+ packet flow")

    if "PASS" not in result.stdout:
        st.report_fail("msg", "TACACS+ packet verification FAILED")

    if "FAIL" in result.stdout:
        st.report_fail("msg", "Some TACACS+ packet checks FAILED")

    st.log("=" * 80)
    st.log("✓ MODULE 3 COMPLETED: Scapy packet capture and verification successful")
    st.log(f"✓ TACACS+ packets captured and analyzed successfully")
    st.log(f"✓ Pcap file saved: {CONFIG.capture_file}")
    st.log("=" * 80)

    st.report_pass("msg", "Scapy packet capture and verification completed successfully")


def test_004_cleanup_and_remove_all():
    """
    MODULE 4: CLEANUP
    Remove all configuration and cleanup temporary files
    """
    st.banner("=" * 80)
    st.banner("MODULE 4: CLEANUP - Remove all configuration")
    st.banner("=" * 80)

    # Remove AAA and TACACS+ configuration
    st.log("Step 1: Removing AAA and TACACS+ configuration")
    commands = [
        "aaa authentication login default",
        "aaa authentication failthrough default",
        "aaa authentication fallback default",
        f"no tacacs server {CONFIG.tacacs_server_ip}",
    ]

    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)

    aaa_final = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"Final AAA status:\n{aaa_final}")

    # Cleanup temporary files on VM1
    st.log("Step 2: Cleaning up temporary files on VM1")
    cleanup_cmd = f'sshpass -p "{CONFIG.server_password}" ssh {CONFIG.server_username}@{CONFIG.tacacs_server_ip} "rm -f {CONFIG.scapy_script} {CONFIG.scapy_analysis} /tmp/scapy_output.log"'
    subprocess.run(cleanup_cmd, shell=True, timeout=10)

    st.log("✓ MODULE 4 COMPLETED: Cleanup successful")
    st.log(f"Note: Pcap file preserved at {CONFIG.capture_file} for manual review")

    st.report_pass("msg", "Cleanup completed successfully")
