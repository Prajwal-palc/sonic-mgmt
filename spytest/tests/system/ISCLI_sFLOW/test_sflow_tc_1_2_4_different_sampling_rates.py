"""
sFlow TEST CASE 1.2.4: DIFFERENT SAMPLING RATES PER INTERFACE
Test Case ID: TC-SFLOW-1.2.4

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_2_4_different_sampling_rates.py \
    --logs-path ./logs/sflow_tc_1_2_4_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.2.4: Different Sampling Rates per Interface

  Objective:
    Verify that different interfaces can be configured with different
    sampling rates simultaneously, and that sFlow samples are sent
    to the collector when traffic is generated.

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration:
       - Enable sFlow globally
       - Add collector 192.168.100.87
       - Enable sFlow on Ethernet4 with sampling rate 5000
       - Enable sFlow on Ethernet8 with sampling rate 6000
       - Verify configuration with 'show sflow' and 'show sflow interface'
       - Verify both interfaces show correct sampling rates
    3. Module 3 - Validation:
       - Start tcpdump on collector VM1 (192.168.100.87)
       - Generate traffic from VM1 to DUT (ping -c 2000 -i 0.2)
       - Monitor packet capture in real-time
       - Stop tcpdump
       - Analyze captured packets and verify sFlow samples received
    4. Module 4 - Cleanup: Remove all sFlow configuration

Pre-requisites:
  - 1 SONiC device (DUT1)
  - Collector VM1: 192.168.100.87 (SSH access required)
  - DUT1 IP: 192.168.100.91 (detected dynamically)
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
    "polling_interval":     "20",
    "interface_1":          "Ethernet4",
    "sampling_rate_1":      "5000",
    "interface_2":          "Ethernet8",
    "sampling_rate_2":      "6000",

    # DUT IP (will be dynamically determined from testbed)
    "dut1_ip":              "",  # Set dynamically in test

    # Traffic Configuration
    "ping_count":           "2000",
    "ping_interval":        "0.2",

    # Packet Capture Configuration
    "pcap_file":            "/tmp/sflow_test.pcap",
    "capture_duration":     "430",  # 2000 pings * 0.2s = 400s + 30s buffer
    "warmup_time":          "20",   # Wait after config before starting capture
})

# Test Case ID
TC_ID = "TC-SFLOW-1.2.4"


# ======================================================================
# Helper Function - SSH to Collector
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
    except subprocess.TimeoutExpired:
        st.log(f"Command timed out after {timeout}s: {cmd}")
        return ""
    except Exception as e:
        st.log(f"SSH command failed: {str(e)}")
        return ""


# ======================================================================
# Fixture - Module Level Setup/Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def sflow_module_hooks(request):
    """
    Module-level fixture for setup and teardown.
    Runs before all tests in this module and after all tests.
    """
    global vars

    # Ensure minimum topology: 1 DUT (D1)
    vars = st.ensure_min_topology("D1")

    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: DIFFERENT SAMPLING RATES PER INTERFACE")
    st.banner("=" * 80)

    st.log(f"Collector: {CONFIG.collector_ip}:{CONFIG.collector_port}")
    st.log(f"Interface 1: {CONFIG.interface_1} - Sampling Rate: {CONFIG.sampling_rate_1}")
    st.log(f"Interface 2: {CONFIG.interface_2} - Sampling Rate: {CONFIG.sampling_rate_2}")

    # Module 1: Pre-condition - Unconfigure all sFlow before tests
    st.banner("MODULE 1: UNCONFIGURATION - Cleaning existing sFlow config")
    module_1_unconfiguration(vars.D1)
    st.wait(2)

    yield

    # Module 4: Cleanup after all tests
    st.banner("MODULE 4: CLEANUP - Removing all sFlow configuration")
    module_4_cleanup(vars.D1)
    st.wait(1)


# ======================================================================
# MODULE 1: UNCONFIGURATION
# ======================================================================
def module_1_unconfiguration(dut: str):
    """
    Module 1: Unconfiguration
    Remove all existing sFlow configuration before starting tests.
    """
    st.log(f"[MODULE 1] Unconfiguring all sFlow settings on {dut}")

    commands = [
        "no sflow enable",
        f"no sflow collector {CONFIG.collector_ip}",
        f"interface {CONFIG.interface_1}",
        "no sflow enable",
        "exit",
        f"interface {CONFIG.interface_2}",
        "no sflow enable",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=True)
        st.log(f"[MODULE 1] Unconfiguration completed on {dut}")
    except Exception as e:
        st.log(f"[MODULE 1] Unconfiguration error (may be expected if no config exists): {str(e)}")


# ======================================================================
# MODULE 2: CONFIGURATION
# ======================================================================
def module_2_configuration(dut: str) -> bool:
    """
    Module 2: Configuration
    Configure sFlow with different sampling rates on two interfaces.
    """
    st.banner("[MODULE 2] Configuring sFlow with different sampling rates per interface")

    # Configuration commands
    commands = [
        "sflow enable",
        f"sflow collector {CONFIG.collector_ip}",
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
        st.log(f"[MODULE 2] sFlow configured on {dut}")
        st.log(f"  ✓ {CONFIG.interface_1}: sampling rate {CONFIG.sampling_rate_1}")
        st.log(f"  ✓ {CONFIG.interface_2}: sampling rate {CONFIG.sampling_rate_2}")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure sFlow on {dut}: {str(e)}")
        return False


def module_2_verify_configuration(dut: str) -> bool:
    """
    Module 2: Verify sFlow configuration.
    """
    st.log(f"[MODULE 2] Verifying sFlow configuration on {dut}")

    # Verify global sFlow configuration
    output = st.show(dut, "show sflow | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    # Check sFlow enabled
    if "sFlow Admin State:          up" not in output_str:
        st.error("sFlow not enabled globally")
        return False
    st.log(f"  ✓ sFlow Admin State: up")

    # Check collector configured
    if CONFIG.collector_ip not in output_str:
        st.error(f"Collector {CONFIG.collector_ip} not found")
        return False
    st.log(f"  ✓ Collector configured: {CONFIG.collector_ip}")

    # Verify interface sFlow configuration
    output = st.show(dut, "show sflow interface | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow interface output:\n{output_str}")

    # Parse interface configuration for Ethernet4
    eth4_found = False
    eth8_found = False

    for line in output_str.split('\n'):
        columns = [col.strip() for col in line.split('|') if col.strip()]

        # Check Ethernet4 (exact match)
        if len(columns) >= 3 and columns[0] == CONFIG.interface_1:
            eth4_found = True
            admin_state = columns[1]
            sampling_rate = columns[2]

            if "up" not in admin_state.lower():
                st.error(f"{CONFIG.interface_1} Admin State not 'up'")
                return False

            if CONFIG.sampling_rate_1 not in sampling_rate:
                st.error(f"{CONFIG.interface_1} Sampling Rate not {CONFIG.sampling_rate_1} (found: {sampling_rate})")
                return False

            st.log(f"  ✓ {CONFIG.interface_1} Admin State: up")
            st.log(f"  ✓ {CONFIG.interface_1} Sampling Rate: {CONFIG.sampling_rate_1}")

        # Check Ethernet8 (exact match)
        if len(columns) >= 3 and columns[0] == CONFIG.interface_2:
            eth8_found = True
            admin_state = columns[1]
            sampling_rate = columns[2]

            if "up" not in admin_state.lower():
                st.error(f"{CONFIG.interface_2} Admin State not 'up'")
                return False

            if CONFIG.sampling_rate_2 not in sampling_rate:
                st.error(f"{CONFIG.interface_2} Sampling Rate not {CONFIG.sampling_rate_2} (found: {sampling_rate})")
                return False

            st.log(f"  ✓ {CONFIG.interface_2} Admin State: up")
            st.log(f"  ✓ {CONFIG.interface_2} Sampling Rate: {CONFIG.sampling_rate_2}")

    if not eth4_found:
        st.error(f"{CONFIG.interface_1} not found in 'show sflow interface' output")
        return False

    if not eth8_found:
        st.error(f"{CONFIG.interface_2} not found in 'show sflow interface' output")
        return False

    st.log(f"✓ All configuration verified successfully")
    st.log(f"  - Both interfaces have different sampling rates configured")
    st.log(f"  - {CONFIG.interface_1}: {CONFIG.sampling_rate_1}")
    st.log(f"  - {CONFIG.interface_2}: {CONFIG.sampling_rate_2}")
    return True


# ======================================================================
# MODULE 3: VALIDATION - Packet Capture & Analysis
# ======================================================================
def start_tcpdump_collector() -> bool:
    """Start tcpdump on collector VM to capture sFlow packets."""
    st.log("[MODULE 3] Starting tcpdump on collector VM")

    # Kill any existing tcpdump processes (multiple times to be sure)
    exec_ssh_collector("sudo pkill -9 tcpdump", timeout=10)
    st.wait(1)
    exec_ssh_collector("sudo pkill -9 tcpdump", timeout=10)
    st.wait(1)

    # Verify all tcpdump processes are gone
    check_procs = exec_ssh_collector("pgrep tcpdump")
    if check_procs.strip():
        st.log(f"  Warning: Found remaining tcpdump processes, killing again...")
        exec_ssh_collector("sudo killall -9 tcpdump", timeout=10)
        st.wait(2)

    # Remove old pcap file
    exec_ssh_collector(f"sudo rm -f {CONFIG.pcap_file}")

    # Start tcpdump with filter for DUT IP and UDP port 6343
    # Using bash -c with nohup for proper backgrounding
    cmd = f"bash -c 'nohup sudo tcpdump -i any \"src host {CONFIG.dut1_ip} and udp port {CONFIG.collector_port}\" -nn -w {CONFIG.pcap_file} > /dev/null 2>&1 &'"
    exec_ssh_collector(cmd, timeout=3)

    # Wait and verify tcpdump started
    st.wait(3)
    check_output = exec_ssh_collector("pgrep tcpdump")
    if check_output.strip():
        pids = check_output.strip().split('\n')
        st.log(f"✓ tcpdump started successfully (PID: {pids[0]})")

        # Verify pcap file created
        st.wait(2)
        file_check = exec_ssh_collector(f"ls -la {CONFIG.pcap_file}")
        if file_check.strip():
            st.log(f"  ✓ Pcap file created: {CONFIG.pcap_file}")

        return True
    else:
        st.error("Failed to start tcpdump on collector")
        return False


def stop_tcpdump_collector() -> bool:
    """Stop tcpdump on collector VM."""
    st.log("[MODULE 3] Stopping tcpdump on collector VM")

    exec_ssh_collector("sudo pkill -9 tcpdump", timeout=10)
    st.wait(2)

    # Verify tcpdump stopped
    check_output = exec_ssh_collector("pgrep tcpdump")
    if not check_output.strip():
        st.log(f"✓ tcpdump stopped successfully")
        return True
    else:
        st.error("Failed to stop tcpdump (still running)")
        return False


def show_live_packet_samples(count: int = 10):
    """Show sample sFlow packets from pcap file."""
    st.log(f"  Sample sFlow packets (first {count}):")
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 2>/dev/null | head -{count}"
    output = exec_ssh_collector(cmd, timeout=10)

    if output.strip():
        for line in output.strip().split('\n')[:count]:
            st.log(f"    {line}")
    else:
        st.log(f"    (No packets captured yet)")


def analyze_sflow_packets() -> dict:
    """Analyze captured sFlow packets and return statistics."""
    st.log("[MODULE 3] Analyzing captured sFlow packets")

    results = {
        "total_packets": 0,
        "dut1_packets": 0,
    }

    # Count total packets
    cmd_total = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 2>/dev/null | wc -l"
    total_count = exec_ssh_collector(cmd_total, timeout=10)
    results["total_packets"] = int(total_count.strip()) if total_count.strip().isdigit() else 0

    # Count packets from DUT1 (should match total since we filter by src host)
    cmd_dut1 = f"sudo tcpdump -r {CONFIG.pcap_file} 'src host {CONFIG.dut1_ip}' -nn 2>/dev/null | wc -l"
    dut1_count = exec_ssh_collector(cmd_dut1, timeout=10)
    results["dut1_packets"] = int(dut1_count.strip()) if dut1_count.strip().isdigit() else 0

    # Get pcap file size
    cmd_size = f"ls -lh {CONFIG.pcap_file} 2>/dev/null | awk '{{print $5}}'"
    file_size = exec_ssh_collector(cmd_size, timeout=10)

    st.log("")
    st.log("Packet Analysis Results:")
    st.log(f"  Pcap file size: {file_size.strip() if file_size.strip() else '0 bytes'}")
    st.log(f"  Total sFlow packets captured: {results['total_packets']}")
    st.log(f"  Packets from DUT1 ({CONFIG.dut1_ip}): {results['dut1_packets']}")

    return results


# ======================================================================
# MODULE 4: CLEANUP
# ======================================================================
def module_4_cleanup(dut: str):
    """
    Module 4: Cleanup
    Remove all sFlow configuration after test completion.
    """
    st.log(f"[MODULE 4] Cleaning up sFlow configuration on {dut}")

    commands = [
        "no sflow enable",
        f"no sflow collector {CONFIG.collector_ip}",
        f"interface {CONFIG.interface_1}",
        "no sflow enable",
        "exit",
        f"interface {CONFIG.interface_2}",
        "no sflow enable",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=True)
        st.log(f"[MODULE 4] Cleanup completed on {dut}")

        # Also cleanup pcap file from collector
        st.log(f"[MODULE 4] Cleaning up pcap file from collector")
        exec_ssh_collector(f"sudo rm -f {CONFIG.pcap_file}")
        st.log(f"✓ Removed {CONFIG.pcap_file}")
    except Exception as e:
        st.log(f"[MODULE 4] Cleanup error: {str(e)}")


# ======================================================================
# Test Function - Main Test Case
# ======================================================================
def test_sflow_tc_1_2_4_different_sampling_rates():
    """
    Test Case 1.2.4: Different Sampling Rates per Interface

    This test verifies:
    1. Two interfaces can have different sampling rates configured simultaneously
    2. Configuration verified with 'show sflow interface'
    3. sFlow samples are sent to collector when traffic is generated
    4. Packet capture shows sFlow packets from DUT
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: DIFFERENT SAMPLING RATES PER INTERFACE")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    # Get actual DUT IP from testbed
    st.log("Detecting DUT management IP address...")
    try:
        # Try multiple methods to get DUT IP
        # Method 1: Get from hostname -I
        dut_ip_output = st.exec_ssh(dut, "hostname -I | awk '{print $1}'")
        if dut_ip_output and dut_ip_output.strip() and '192.168.100' in str(dut_ip_output):
            CONFIG.dut1_ip = dut_ip_output.strip().split('\n')[0]
            st.log(f"✓ Detected DUT1 IP: {CONFIG.dut1_ip}")
        else:
            # Method 2: Fallback to known IP
            CONFIG.dut1_ip = "192.168.100.91"
            st.log(f"Using fallback DUT1 IP: {CONFIG.dut1_ip}")
    except Exception as e:
        CONFIG.dut1_ip = "192.168.100.91"
        st.log(f"Using fallback DUT1 IP: {CONFIG.dut1_ip}")

    # ========================================================================
    # MODULE 2: CONFIGURATION
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 2] CONFIGURATION - sFlow Setup                         #")
    st.banner("=" * 80)

    st.log("STEP 1: Configure sFlow with different sampling rates on two interfaces")
    if not module_2_configuration(dut):
        st.report_fail("test_case_failed", "Failed to configure sFlow")

    st.wait(2)

    st.log("STEP 2: Verify sFlow configuration")
    if not module_2_verify_configuration(dut):
        st.report_fail("test_case_failed", "sFlow configuration verification failed")

    st.log("")
    st.log("  Configuration Summary:")
    st.log(f"    DUT Management IP: {CONFIG.dut1_ip}")
    st.log(f"    Collector IP: {CONFIG.collector_ip}")
    st.log(f"    {CONFIG.interface_1} Sampling Rate: {CONFIG.sampling_rate_1}")
    st.log(f"    {CONFIG.interface_2} Sampling Rate: {CONFIG.sampling_rate_2}")
    st.log("")

    # ========================================================================
    # MODULE 3: VALIDATION - Packet Capture
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 3] VALIDATION - Traffic and Packet Capture              #")
    st.banner("=" * 80)

    st.log(f"STEP 2.5: Wait {CONFIG.warmup_time} seconds for sFlow to initialize after configuration")
    st.log(f"  (sFlow daemon may need time to start sending samples)")
    st.wait(int(CONFIG.warmup_time))

    st.log("STEP 3: Start tcpdump on collector VM")
    if not start_tcpdump_collector():
        validation_failures.append("STEP 3: Failed to start tcpdump")
    else:
        st.log("STEP 4: Generate traffic from collector VM to DUT")
        st.log(f"  Testing connectivity with sample pings:")
        sample_ping = exec_ssh_collector(f"ping -c 5 -i 0.2 {CONFIG.dut1_ip}", timeout=10)
        for line in sample_ping.split('\n')[:10]:  # Show first 10 lines
            if line.strip():
                st.log(f"    {line}")

        st.log("")
        st.log(f"  Starting full ping test ({CONFIG.ping_count} pings) to DUT in background...")
        st.log(f"  Ping interval: {CONFIG.ping_interval}s")
        st.log(f"  Expected duration: ~{int(int(CONFIG.ping_count) * float(CONFIG.ping_interval))} seconds")
        st.log("")

        # Start ping in background
        cmd_ping = f"ping -c {CONFIG.ping_count} -i {CONFIG.ping_interval} {CONFIG.dut1_ip} > /tmp/ping_dut.log 2>&1 &"
        exec_ssh_collector(cmd_ping)

        st.log(f"  ✓ Ping started in background")
        st.log(f"  Monitoring packet capture progress...")

        # Monitor progress in intervals (check every 60 seconds)
        check_intervals = [60, 60, 60, 60, 60, 60, 60]  # 7 checks = 420 seconds
        elapsed = 0
        for interval in check_intervals:
            st.wait(interval)
            elapsed += interval
            st.log(f"  [{elapsed}s elapsed] Checking packet capture progress...")

            # Verify tcpdump still running
            tcpdump_check = exec_ssh_collector("pgrep tcpdump")
            if tcpdump_check.strip():
                st.log(f"    ✓ tcpdump still running (PID: {tcpdump_check.strip()})")

            # Check pcap file size
            file_size = exec_ssh_collector(f"ls -lh {CONFIG.pcap_file} 2>/dev/null | awk '{{print $5}}'")
            st.log(f"    Pcap file size: {file_size.strip() if file_size.strip() else '0 bytes'}")

            # Count packets
            cmd_total = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 2>/dev/null | wc -l"
            total_count = exec_ssh_collector(cmd_total, timeout=10)
            total = int(total_count.strip()) if total_count.strip().isdigit() else 0
            st.log(f"    Total packets captured: {total}")

            # Show sample if packets captured
            if total > 0 and elapsed <= 120:  # Only show samples in first 2 minutes
                st.log(f"    Sample packets captured:")
                cmd_sample = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 2>/dev/null | head -3"
                sample_output = exec_ssh_collector(cmd_sample, timeout=10)
                if sample_output.strip():
                    for line in sample_output.strip().split('\n')[:3]:
                        st.log(f"      {line}")

        st.log(f"✓ Capture duration completed ({elapsed} seconds)")

        # Check final ping status
        st.log("")
        st.log(f"  Checking ping completion status...")
        ping_status = exec_ssh_collector("tail -20 /tmp/ping_dut.log", timeout=10)
        if "packets transmitted" in ping_status:
            st.log(f"  Ping statistics:")
            for line in ping_status.split('\n'):
                if "packets transmitted" in line or "rtt min/avg/max" in line:
                    st.log(f"    {line.strip()}")

        st.log("STEP 5: Stop tcpdump on collector VM")
        if not stop_tcpdump_collector():
            validation_failures.append("STEP 5: Failed to stop tcpdump")

        st.wait(2)  # Let packets settle

        st.log("STEP 6: Analyze captured sFlow packets")
        st.log("")
        st.log("  Showing sample of captured packets:")
        show_live_packet_samples(count=10)
        st.log("")

        results = analyze_sflow_packets()

        # Verify packet capture results
        if results["total_packets"] == 0:
            validation_failures.append("STEP 6: No sFlow packets captured at all")
        else:
            st.log(f"✓ Total sFlow packets captured: {results['total_packets']}")

        if results["dut1_packets"] == 0:
            validation_failures.append(f"STEP 6: No sFlow packets from DUT1 ({CONFIG.dut1_ip})")
        else:
            st.log(f"✓ Packets from DUT1: {results['dut1_packets']}")

    # ========================================================================
    # Final Test Result
    # ========================================================================
    st.banner("=" * 80)
    if validation_failures:
        st.banner("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        st.log(f"TEST CASE {TC_ID} VALIDATION FAILURES:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.banner("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        st.report_fail("test_case_failed", f"Test Case {TC_ID}: {len(validation_failures)} validation failure(s)")
    else:
        st.banner("=" * 80)
        st.banner(f"TEST CASE {TC_ID}: PASSED")
        st.banner("=" * 80)
        st.log("✓ All validations passed successfully")
        st.log("  - Different sampling rates configured on two interfaces")
        st.log(f"  - {CONFIG.interface_1}: {CONFIG.sampling_rate_1}")
        st.log(f"  - {CONFIG.interface_2}: {CONFIG.sampling_rate_2}")
        st.log("  - sFlow packets captured from DUT")
        st.report_pass("test_case_passed")
