"""
sFlow TEST CASE 1.2.1: VERIFY SAMPLES REACH COLLECTOR
Test Case ID: TC-SFLOW-1.2.1

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_2_1_verify_samples_reach_collector.py \
    --logs-path ./logs/sflow_tc_1_2_1_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.2.1: Verify Samples Reach Collector

  Objective:
    Verify that both DUT1 and DUT2 send sFlow samples to the collector
    when traffic is generated to them.

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config on both DUTs
    2. Module 2 - Configuration:
       - On both DUT1 and DUT2:
         * Add collector 192.168.100.87
         * Set polling interval 15
         * Enable sFlow on Ethernet4 with sampling rate 4000
         * Enable sFlow on Ethernet8 with sampling rate 1000
       - Verify configuration with 'show sflow' and 'show sflow interface'
    3. Module 3 - Validation:
       - Start tcpdump on collector VM1 (192.168.100.87)
       - Generate traffic from VM1 to DUT1 (ping -c 500 -i 0.2)
       - Generate traffic from VM1 to DUT2 (ping -c 500 -i 0.2)
       - Stop tcpdump
       - Analyze captured packets:
         * Count total sFlow packets
         * Count packets from DUT1
         * Count packets from DUT2
       - Verify both DUTs sent sFlow samples
    4. Module 4 - Cleanup: Remove all sFlow configuration from both DUTs

Pre-requisites:
  - 2 SONiC devices (DUT1 and DUT2)
  - Collector VM1: 192.168.100.87 (SSH access required)
  - DUT1 IP: 192.168.100.91
  - DUT2 IP: 192.168.100.145
  - Testbed: testbed_2vs.yaml or compatible
"""

from __future__ import annotations

import pytest
import time
import subprocess
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
    # Collector Configuration
    "collector_ip":         "192.168.100.87",
    "collector_port":       "6343",
    "collector_user":       "adminuser",
    "collector_password":   "Regre@11",

    # sFlow Configuration
    "polling_interval":     "15",
    "interface_1":          "Ethernet4",
    "sampling_rate_1":      "4000",
    "interface_2":          "Ethernet8",
    "sampling_rate_2":      "1000",

    # DUT IPs for traffic generation (will be dynamically determined)
    "dut1_ip":              "",  # Set dynamically in test
    "dut2_ip":              "",  # Set dynamically in test

    # Traffic Configuration
    "ping_count":           "500",
    "ping_interval":        "0.2",

    # Packet Capture
    "pcap_file":            "/tmp/sflow_both.pcap",
})

# ======================================================================
# Test Case ID
# ======================================================================
TC_ID = "TC-SFLOW-1.2.1"


# ======================================================================
# Helper Functions - SSH to Collector
# ======================================================================
def exec_ssh_collector(cmd: str, timeout: int = 60) -> str:
    """Execute command on collector VM via SSH."""
    ssh_cmd = [
        "sshpass", "-p", CONFIG.collector_password,
        "ssh", "-o", "StrictHostKeyChecking=no",
        f"{CONFIG.collector_user}@{CONFIG.collector_ip}",
        cmd
    ]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout
    except Exception as e:
        st.error(f"Failed to execute SSH command on collector: {str(e)}")
        return ""


# ======================================================================
# Module Fixture - Setup and Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def sflow_tc_1_2_1_module_hooks(request):
    """Module-level setup and teardown for Test Case 1.2.1."""
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID} - VERIFY SAMPLES REACH COLLECTOR - MODULE START")
    st.banner("=" * 80)

    # Ensure 2 DUTs with 1 link between them
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}")
    st.log(f"DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"Collector: {CONFIG.collector_ip}:{CONFIG.collector_port}")

    # Module 1: Pre-condition - Unconfigure all sFlow before tests
    st.banner("MODULE 1: UNCONFIGURATION - Cleaning existing sFlow config on both DUTs")
    module_1_unconfiguration(vars.D1, vars.D2)
    st.wait(2)

    yield

    # Module 4: Cleanup after all tests
    st.banner("MODULE 4: CLEANUP - Removing all sFlow configuration from both DUTs")
    module_4_cleanup(vars.D1, vars.D2)
    st.wait(1)


# ======================================================================
# MODULE 1: UNCONFIGURATION
# ======================================================================
def module_1_unconfiguration(dut1: str, dut2: str):
    """
    Module 1: Unconfiguration
    Remove all existing sFlow configuration before starting tests.
    """
    st.log(f"[MODULE 1] Unconfiguring all sFlow settings on both DUTs")

    for dut in [dut1, dut2]:
        commands = [
            "no sflow enable",
            f"no sflow collector {CONFIG.collector_ip}",
            f"interface {CONFIG.interface_1}",
            "no sflow enable",
            "exit",
            f"interface {CONFIG.interface_2}",
            "no sflow enable",
            "exit",
            "end"
        ]
        st.config(dut, commands, type='klish', skip_error_check=True)

    st.wait(1)
    st.log(f"[MODULE 1] Unconfiguration completed on both DUTs")


# ======================================================================
# MODULE 2: CONFIGURATION
# ======================================================================
def module_2_configuration_dut(dut: str, dut_name: str) -> bool:
    """
    Module 2: Configuration for a single DUT
    Configure sFlow collector, polling interval, and interface sampling rates.
    """
    st.log(f"[MODULE 2] Configuring sFlow on {dut_name}")

    # Configuration commands
    commands = [
        "sflow enable",
        f"sflow collector {CONFIG.collector_ip}",
        f"sflow polling-interval {CONFIG.polling_interval}",
        f"interface {CONFIG.interface_1}",
        "sflow enable",
        f"sflow sampling-rate {CONFIG.sampling_rate_1}",
        "exit",
        f"interface {CONFIG.interface_2}",
        "sflow enable",
        f"sflow sampling-rate {CONFIG.sampling_rate_2}",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] sFlow configured on {dut_name}")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure sFlow on {dut_name}: {str(e)}")
        return False


def module_2_verify_configuration(dut: str, dut_name: str) -> bool:
    """
    Module 2: Verify sFlow configuration on a DUT.
    """
    st.log(f"[MODULE 2] Verifying sFlow configuration on {dut_name}")

    # Verify global sFlow configuration
    output = st.show(dut, "show sflow | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"{dut_name} - show sflow output:\n{output_str}")

    # Check sFlow Admin State is up
    if "admin state" not in output_str.lower() or "up" not in output_str.lower():
        st.error(f"{dut_name}: sFlow Admin State not 'up'")
        return False

    # Check collector is configured
    if CONFIG.collector_ip not in output_str:
        st.error(f"{dut_name}: Collector {CONFIG.collector_ip} not found")
        return False

    # Check polling interval
    if CONFIG.polling_interval not in output_str:
        st.error(f"{dut_name}: Polling interval {CONFIG.polling_interval} not found")
        return False

    st.log(f"✓ {dut_name}: Global sFlow configuration verified")

    # Verify interface sFlow configuration
    output = st.show(dut, "show sflow interface | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"{dut_name} - show sflow interface output:\n{output_str}")

    # Parse interface configuration (table format with | separators)
    eth4_found = False
    eth8_found = False

    for line in output_str.split('\n'):
        # Split by "|" and strip whitespace from each column
        columns = [col.strip() for col in line.split('|') if col.strip()]

        # Skip header and separator lines
        if not columns or columns[0] in ['Interface', '=============']:
            continue

        # Check if this is the Ethernet4 row (exact match)
        if len(columns) >= 3 and columns[0] == CONFIG.interface_1:
            eth4_found = True
            admin_state = columns[1] if len(columns) > 1 else ""
            sampling_rate = columns[2] if len(columns) > 2 else ""

            if "up" not in admin_state.lower() or CONFIG.sampling_rate_1 not in sampling_rate:
                st.error(f"{dut_name}: {CONFIG.interface_1} config incorrect: {line}")
                st.error(f"  Expected: Admin State 'up', Sampling Rate {CONFIG.sampling_rate_1}")
                st.error(f"  Found: Admin State '{admin_state}', Sampling Rate '{sampling_rate}'")
                return False
            st.log(f"✓ {dut_name}: {CONFIG.interface_1} - Admin State '{admin_state}', Sampling Rate {sampling_rate}")

        # Check if this is the Ethernet8 row (exact match)
        if len(columns) >= 3 and columns[0] == CONFIG.interface_2:
            eth8_found = True
            admin_state = columns[1] if len(columns) > 1 else ""
            sampling_rate = columns[2] if len(columns) > 2 else ""

            if "up" not in admin_state.lower() or CONFIG.sampling_rate_2 not in sampling_rate:
                st.error(f"{dut_name}: {CONFIG.interface_2} config incorrect: {line}")
                st.error(f"  Expected: Admin State 'up', Sampling Rate {CONFIG.sampling_rate_2}")
                st.error(f"  Found: Admin State '{admin_state}', Sampling Rate '{sampling_rate}'")
                return False
            st.log(f"✓ {dut_name}: {CONFIG.interface_2} - Admin State '{admin_state}', Sampling Rate {sampling_rate}'")

    if not eth4_found or not eth8_found:
        st.error(f"{dut_name}: Interface configuration incomplete")
        return False

    st.log(f"✓ {dut_name}: All interface configurations verified")
    return True


# ======================================================================
# MODULE 3: VALIDATION - Traffic Generation & Packet Capture
# ======================================================================
def start_tcpdump_collector() -> bool:
    """Start tcpdump on collector VM to capture sFlow packets."""
    st.log("[MODULE 3] Starting tcpdump on collector VM")

    # Kill any existing tcpdump processes
    exec_ssh_collector("sudo pkill -9 tcpdump", timeout=10)
    st.wait(2)

    # Remove old pcap file if exists
    exec_ssh_collector(f"sudo rm -f {CONFIG.pcap_file}")

    # Start tcpdump in background with proper detachment
    # Use bash -c with nohup to ensure proper backgrounding
    cmd = f"bash -c 'nohup sudo tcpdump -i any udp port {CONFIG.collector_port} -nn -w {CONFIG.pcap_file} > /dev/null 2>&1 &'"
    exec_ssh_collector(cmd, timeout=3)

    # Wait for tcpdump to start
    st.wait(3)

    # Verify tcpdump is running
    check_output = exec_ssh_collector("pgrep tcpdump")
    if check_output.strip():
        pids = check_output.strip().split('\n')
        st.log(f"✓ tcpdump started successfully (PID: {pids[0]})")

        # Verify pcap file was created
        st.wait(2)
        file_check = exec_ssh_collector(f"ls -la {CONFIG.pcap_file}")
        if file_check.strip():
            st.log(f"  ✓ Pcap file created: {CONFIG.pcap_file}")
        else:
            st.log(f"  Warning: Pcap file not yet visible")

        return True
    else:
        st.error("Failed to start tcpdump on collector")
        return False


def stop_tcpdump_collector() -> bool:
    """Stop tcpdump on collector VM."""
    st.log("[MODULE 3] Stopping tcpdump on collector VM")

    # Kill tcpdump process with SIGTERM first, then SIGKILL if needed
    exec_ssh_collector("sudo pkill -f 'tcpdump.*6343'")
    st.wait(2)

    # Force kill if still running
    exec_ssh_collector("sudo pkill -9 -f 'tcpdump.*6343'")
    st.wait(1)

    # Verify tcpdump stopped
    check_output = exec_ssh_collector("pgrep -f 'tcpdump.*6343'")
    if not check_output.strip():
        st.log("✓ tcpdump stopped successfully")
        return True
    else:
        st.log(f"Warning: tcpdump may still be running (PIDs: {check_output.strip()})")
        return True  # Don't fail the test for this


def generate_traffic_to_dut(dut_ip: str, dut_name: str) -> bool:
    """Generate ping traffic from VM1 to DUT."""
    st.log(f"[MODULE 3] Generating traffic from collector to {dut_name} ({dut_ip})")
    st.log(f"  Sending {CONFIG.ping_count} pings at {CONFIG.ping_interval}s interval (~{int(CONFIG.ping_count) * float(CONFIG.ping_interval)}s total)")

    # Calculate timeout: ping_count * interval + 200s buffer
    timeout = int(int(CONFIG.ping_count) * float(CONFIG.ping_interval)) + 200
    st.log(f"  Timeout set to {timeout} seconds")

    cmd = f"ping -c {CONFIG.ping_count} -i {CONFIG.ping_interval} {dut_ip} > /dev/null 2>&1"
    output = exec_ssh_collector(cmd, timeout=timeout)

    st.log(f"✓ Traffic generation to {dut_name} completed ({CONFIG.ping_count} pings)")
    return True


def show_live_packet_capture_sample(source_ip: str, dut_name: str, count: int = 5):
    """Show sample of live packet capture from a specific DUT."""
    st.log(f"  Sample sFlow packets from {dut_name} ({source_ip}):")
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 'src host {source_ip}' 2>/dev/null | head -{count}"
    output = exec_ssh_collector(cmd, timeout=10)
    if output.strip():
        for line in output.strip().split('\n')[:count]:
            st.log(f"    {line}")
    else:
        st.log(f"    (No packets from {source_ip} yet)")


def check_packet_capture_progress() -> dict:
    """Check current packet capture progress (without stopping tcpdump)."""
    # Check if pcap file exists first
    file_check = exec_ssh_collector(f"test -f {CONFIG.pcap_file} && echo 'EXISTS' || echo 'NOT_FOUND'")
    if 'NOT_FOUND' in file_check:
        st.log(f"  Warning: Pcap file {CONFIG.pcap_file} does not exist yet")
        return {"total_packets": 0, "dut1_packets": 0, "dut2_packets": 0}

    # Count total sFlow packets captured so far
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 2>/dev/null | wc -l"
    total_output = exec_ssh_collector(cmd, timeout=15)
    total_packets = int(total_output.strip()) if total_output.strip().isdigit() else 0

    # Count packets from DUT1
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 'src host {CONFIG.dut1_ip}' 2>/dev/null | wc -l"
    dut1_output = exec_ssh_collector(cmd, timeout=15)
    dut1_packets = int(dut1_output.strip()) if dut1_output.strip().isdigit() else 0

    # Count packets from DUT2
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 'src host {CONFIG.dut2_ip}' 2>/dev/null | wc -l"
    dut2_output = exec_ssh_collector(cmd, timeout=15)
    dut2_packets = int(dut2_output.strip()) if dut2_output.strip().isdigit() else 0

    return {
        "total_packets": total_packets,
        "dut1_packets": dut1_packets,
        "dut2_packets": dut2_packets
    }


def analyze_sflow_packets() -> dict:
    """Analyze captured sFlow packets from pcap file."""
    st.log("[MODULE 3] Analyzing captured sFlow packets")

    # Count total sFlow packets
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 2>/dev/null | wc -l"
    total_output = exec_ssh_collector(cmd)
    total_packets = int(total_output.strip()) if total_output.strip().isdigit() else 0

    # Count packets from DUT1
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 'src host {CONFIG.dut1_ip}' 2>/dev/null | wc -l"
    dut1_output = exec_ssh_collector(cmd)
    dut1_packets = int(dut1_output.strip()) if dut1_output.strip().isdigit() else 0

    # Count packets from DUT2
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 'src host {CONFIG.dut2_ip}' 2>/dev/null | wc -l"
    dut2_output = exec_ssh_collector(cmd)
    dut2_packets = int(dut2_output.strip()) if dut2_output.strip().isdigit() else 0

    results = {
        "total_packets": total_packets,
        "dut1_packets": dut1_packets,
        "dut2_packets": dut2_packets
    }

    st.log(f"Packet Analysis Results:")
    st.log(f"  Total sFlow packets captured: {total_packets}")
    st.log(f"  Packets from DUT1 ({CONFIG.dut1_ip}): {dut1_packets}")
    st.log(f"  Packets from DUT2 ({CONFIG.dut2_ip}): {dut2_packets}")

    return results


def cleanup_pcap_file():
    """Remove the pcap file and ping logs from collector."""
    st.log("[MODULE 3] Cleaning up pcap file and ping logs from collector")
    exec_ssh_collector(f"sudo rm -f {CONFIG.pcap_file}")
    exec_ssh_collector(f"sudo rm -f /tmp/ping_dut1.log /tmp/ping_dut2.log")
    st.log(f"✓ Removed {CONFIG.pcap_file} and ping log files")


# ======================================================================
# MODULE 4: CLEANUP
# ======================================================================
def module_4_cleanup(dut1: str, dut2: str):
    """
    Module 4: Cleanup
    Remove all sFlow configuration after test completion.
    """
    st.log(f"[MODULE 4] Cleaning up all sFlow configuration on both DUTs")

    for dut in [dut1, dut2]:
        commands = [
            "no sflow enable",
            f"no sflow collector {CONFIG.collector_ip}",
            f"interface {CONFIG.interface_1}",
            "no sflow enable",
            "exit",
            f"interface {CONFIG.interface_2}",
            "no sflow enable",
            "exit",
            "end"
        ]
        st.config(dut, commands, type='klish', skip_error_check=True)

    # Also cleanup pcap file
    cleanup_pcap_file()

    st.wait(1)
    st.log(f"[MODULE 4] Cleanup completed on both DUTs")


# ======================================================================
# Test Function - Main Test Case
# ======================================================================
def test_sflow_tc_1_2_1_verify_samples_reach_collector():
    """
    Test Case 1.2.1: Verify Samples Reach Collector

    This test verifies:
    1. sFlow can be configured on both DUT1 and DUT2
    2. Collector, polling interval, and interface sampling rates are set correctly
    3. Configuration is verified with 'show sflow' and 'show sflow interface'
    4. Traffic generation from collector to both DUTs triggers sFlow samples
    5. sFlow packets from both DUTs are successfully captured at collector
    6. Both DUTs send sFlow samples (packet count > 0 for each)
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: VERIFY SAMPLES REACH COLLECTOR")
    st.banner("=" * 80)

    dut1 = vars.D1
    dut2 = vars.D2
    validation_failures = []

    # Get actual DUT IPs from testbed
    st.log("Detecting DUT management IP addresses...")
    try:
        # Get DUT1 IP
        dut1_ip_output = st.exec_ssh(dut1, "hostname -I | awk '{print $1}'")
        if dut1_ip_output and dut1_ip_output.strip() and '192.168.100' in str(dut1_ip_output):
            CONFIG.dut1_ip = dut1_ip_output.strip().split('\n')[0]
            st.log(f"✓ Detected DUT1 IP: {CONFIG.dut1_ip}")
        else:
            st.log("Using fallback DUT1 IP: 192.168.100.145")
            CONFIG.dut1_ip = "192.168.100.145"

        # Get DUT2 IP
        dut2_ip_output = st.exec_ssh(dut2, "hostname -I | awk '{print $1}'")
        if dut2_ip_output and dut2_ip_output.strip() and '192.168.100' in str(dut2_ip_output):
            CONFIG.dut2_ip = dut2_ip_output.strip().split('\n')[0]
            st.log(f"✓ Detected DUT2 IP: {CONFIG.dut2_ip}")
        else:
            st.log("Using fallback DUT2 IP: 192.168.100.91")
            CONFIG.dut2_ip = "192.168.100.91"
    except Exception as e:
        st.log(f"Error detecting DUT IPs: {str(e)}")
        st.log("Using fallback IPs: DUT1=192.168.100.145, DUT2=192.168.100.91")
        CONFIG.dut1_ip = "192.168.100.145"
        CONFIG.dut2_ip = "192.168.100.91"

    st.log(f"  DUT1: {CONFIG.dut1_ip}")
    st.log(f"  DUT2: {CONFIG.dut2_ip}")
    st.log(f"  Collector: {CONFIG.collector_ip}:{CONFIG.collector_port}")

    try:
        # ============================================================
        # Module 2: Configuration
        # ============================================================
        st.banner("[MODULE 2] CONFIGURATION - Configuring sFlow on both DUTs")

        st.log("STEP 1: Configure sFlow on DUT1")
        if not module_2_configuration_dut(dut1, "DUT1"):
            validation_failures.append("STEP 1: Failed to configure sFlow on DUT1")

        st.log("STEP 2: Configure sFlow on DUT2")
        if not module_2_configuration_dut(dut2, "DUT2"):
            validation_failures.append("STEP 2: Failed to configure sFlow on DUT2")

        st.wait(2)  # Wait for configuration to settle

        st.log("STEP 3: Verify sFlow configuration on DUT1")
        if not module_2_verify_configuration(dut1, "DUT1"):
            validation_failures.append("STEP 3: Failed to verify sFlow config on DUT1")

        st.log("STEP 4: Verify sFlow configuration on DUT2")
        if not module_2_verify_configuration(dut2, "DUT2"):
            validation_failures.append("STEP 4: Failed to verify sFlow config on DUT2")

        # ============================================================
        # Module 3: Validation - Traffic & Packet Capture
        # ============================================================
        st.banner("[MODULE 3] VALIDATION - Traffic Generation & Packet Capture")

        st.log("STEP 5: Start tcpdump on collector VM")
        if not start_tcpdump_collector():
            validation_failures.append("STEP 5: Failed to start tcpdump on collector")
            st.report_fail("msg", "Cannot proceed - tcpdump failed to start")
            return

        st.log("STEP 6 & 7: Generate traffic from collector to both DUTs in parallel")

        # Start ping to DUT1 in background - show first few packets
        st.log(f"  Starting ping to DUT1 ({CONFIG.dut1_ip})...")
        st.log(f"  Testing connectivity with sample pings:")
        sample_ping = exec_ssh_collector(f"ping -c 5 -i 0.2 {CONFIG.dut1_ip}", timeout=10)
        for line in sample_ping.split('\n')[:10]:  # Show first 10 lines
            if line.strip():
                st.log(f"    {line}")

        st.log(f"  Starting full ping test ({CONFIG.ping_count} pings) to DUT1 in background...")
        cmd_dut1 = f"ping -c {CONFIG.ping_count} -i {CONFIG.ping_interval} {CONFIG.dut1_ip} > /tmp/ping_dut1.log 2>&1 &"
        exec_ssh_collector(cmd_dut1)
        st.wait(2)

        # Start ping to DUT2 in background - show first few packets
        st.log(f"  Starting ping to DUT2 ({CONFIG.dut2_ip})...")
        st.log(f"  Testing connectivity with sample pings:")
        sample_ping = exec_ssh_collector(f"ping -c 5 -i 0.2 {CONFIG.dut2_ip}", timeout=10)
        for line in sample_ping.split('\n')[:10]:  # Show first 10 lines
            if line.strip():
                st.log(f"    {line}")

        st.log(f"  Starting full ping test ({CONFIG.ping_count} pings) to DUT2 in background...")
        cmd_dut2 = f"ping -c {CONFIG.ping_count} -i {CONFIG.ping_interval} {CONFIG.dut2_ip} > /tmp/ping_dut2.log 2>&1 &"
        exec_ssh_collector(cmd_dut2)
        st.wait(2)

        # Verify both pings started successfully
        st.log("  Verifying ping processes started...")
        check_pings = exec_ssh_collector("pgrep -f 'ping.*192.168.100'")
        if check_pings.strip():
            pids = check_pings.strip().split('\n')
            st.log(f"  ✓ Ping processes running (PIDs: {', '.join(pids)})")
        else:
            st.error("  ✗ Ping processes did not start!")
            validation_failures.append("STEP 6: Ping processes failed to start")

        # Calculate expected duration
        duration = int(int(CONFIG.ping_count) * float(CONFIG.ping_interval))
        st.log(f"  Both pings running in parallel, will take ~{duration} seconds ({duration//60} minutes)")
        st.log(f"  Monitoring packet capture progress every 30 seconds...")

        # Monitor progress in intervals
        intervals = [30, 30, 40]  # Check at 30s, 60s, 100s (total 100s, leave 60s buffer)
        elapsed = 0
        for interval in intervals:
            st.wait(interval)
            elapsed += interval

            # Check packet capture progress
            st.log(f"  [{elapsed}s] Checking packet capture and ping progress...")
            progress = check_packet_capture_progress()
            st.log(f"    - Total packets captured: {progress['total_packets']}")
            st.log(f"    - Packets from DUT1 ({CONFIG.dut1_ip}): {progress['dut1_packets']}")
            st.log(f"    - Packets from DUT2 ({CONFIG.dut2_ip}): {progress['dut2_packets']}")

            # Show sample packets if any captured
            if progress['dut1_packets'] > 0:
                show_live_packet_capture_sample(CONFIG.dut1_ip, "DUT1", count=3)
            if progress['dut2_packets'] > 0:
                show_live_packet_capture_sample(CONFIG.dut2_ip, "DUT2", count=3)

            # Check ping progress from log files
            st.log(f"    Ping progress:")
            ping1_check = exec_ssh_collector("tail -5 /tmp/ping_dut1.log 2>/dev/null")
            if ping1_check.strip():
                st.log(f"      DUT1 ping (last 5 lines):")
                for line in ping1_check.strip().split('\n')[-3:]:
                    st.log(f"        {line}")

            ping2_check = exec_ssh_collector("tail -5 /tmp/ping_dut2.log 2>/dev/null")
            if ping2_check.strip():
                st.log(f"      DUT2 ping (last 5 lines):")
                for line in ping2_check.strip().split('\n')[-3:]:
                    st.log(f"        {line}")

            # Check if pings are still running
            check_pings = exec_ssh_collector("pgrep -f 'ping.*192.168.100'")
            if check_pings.strip():
                pids = check_pings.strip().split('\n')
                st.log(f"    - Ping processes still active ({len(pids)} running)")
            else:
                st.log(f"    - Ping processes completed early")
                break

        # Final wait for any remaining traffic
        st.log(f"  Waiting final 60 seconds for traffic to complete...")
        st.wait(60)

        # Verify pings completed and show final statistics
        check_pings = exec_ssh_collector("pgrep -f 'ping.*192.168.100'")
        if check_pings.strip():
            st.log(f"  Pings still running, waiting additional 60 seconds...")
            st.wait(60)
            check_pings = exec_ssh_collector("pgrep -f 'ping.*192.168.100'")
            if check_pings.strip():
                st.log(f"  Warning: Pings still running after extended wait")
            else:
                st.log(f"  ✓ All ping processes completed")
        else:
            st.log(f"  ✓ All ping processes completed successfully")

        # Show final ping statistics
        st.log(f"")
        st.log(f"  Final Ping Statistics:")
        st.log(f"  =====================")

        ping1_stats = exec_ssh_collector("tail -10 /tmp/ping_dut1.log 2>/dev/null")
        if ping1_stats.strip():
            st.log(f"  DUT1 ({CONFIG.dut1_ip}) - Final ping statistics:")
            for line in ping1_stats.strip().split('\n')[-5:]:
                if 'packet' in line.lower() or 'rtt' in line.lower() or 'transmitted' in line.lower():
                    st.log(f"    {line}")

        ping2_stats = exec_ssh_collector("tail -10 /tmp/ping_dut2.log 2>/dev/null")
        if ping2_stats.strip():
            st.log(f"  DUT2 ({CONFIG.dut2_ip}) - Final ping statistics:")
            for line in ping2_stats.strip().split('\n')[-5:]:
                if 'packet' in line.lower() or 'rtt' in line.lower() or 'transmitted' in line.lower():
                    st.log(f"    {line}")

        st.log("✓ Traffic generation to both DUTs completed")

        st.log("STEP 8: Stop tcpdump on collector VM")
        if not stop_tcpdump_collector():
            validation_failures.append("STEP 8: Failed to stop tcpdump")

        st.wait(2)  # Let packets settle

        st.log("STEP 9: Analyze captured sFlow packets")
        results = analyze_sflow_packets()

        # Verify packet capture results
        if results["total_packets"] == 0:
            validation_failures.append("STEP 9: No sFlow packets captured at all")
        else:
            st.log(f"✓ Total sFlow packets captured: {results['total_packets']}")

        if results["dut1_packets"] == 0:
            validation_failures.append(f"STEP 9: No sFlow packets from DUT1 ({CONFIG.dut1_ip})")
        else:
            st.log(f"✓ DUT1 sent {results['dut1_packets']} sFlow packets")

        if results["dut2_packets"] == 0:
            validation_failures.append(f"STEP 9: No sFlow packets from DUT2 ({CONFIG.dut2_ip})")
        else:
            st.log(f"✓ DUT2 sent {results['dut2_packets']} sFlow packets")

        # Cleanup pcap file
        cleanup_pcap_file()

    except Exception as e:
        st.error(f"Exception in test_sflow_tc_1_2_1_verify_samples_reach_collector: {str(e)}")
        validation_failures.append(f"Unexpected exception: {str(e)}")

    # Report test result
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log(f"TEST CASE {TC_ID} VALIDATION FAILURES:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"Test Case {TC_ID}: {len(validation_failures)} validation failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log(f"✅ TEST CASE {TC_ID}: VERIFY SAMPLES REACH COLLECTOR - PASSED")
        st.log("   All validations successful:")
        st.log("   ✓ sFlow configured on DUT1 and DUT2")
        st.log("   ✓ Collector, polling interval, interface sampling rates verified")
        st.log("   ✓ 'show sflow' displays correct configuration on both DUTs")
        st.log("   ✓ 'show sflow interface' displays correct interface config on both DUTs")
        st.log("   ✓ tcpdump successfully captured sFlow packets")
        st.log("   ✓ DUT1 sent sFlow samples to collector")
        st.log("   ✓ DUT2 sent sFlow samples to collector")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
