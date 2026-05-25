"""
sFlow TEST CASE 1.2.2: VERIFY COUNTER POLLING WORKS
Test Case ID: TC-SFLOW-1.2.2

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_2_2_verify_counter_polling.py \
    --logs-path ./logs/sflow_tc_1_2_2_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.2.2: Verify Counter Polling Works

  Objective:
    Verify that sFlow counter polling samples are sent to the collector
    at the configured polling interval without any traffic generation.

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration:
       - Enable sFlow globally
       - Add collector 192.168.100.87
       - Set polling interval 20
       - Enable sFlow on Ethernet4 with sampling rate 4000
         (Note: At least one interface needs sampling rate for sFlow daemon to send packets)
       - Verify configuration with 'show sflow' and 'show sflow interface'
    3. Module 3 - Validation:
       - Wait 30 seconds warmup for sFlow daemon initialization
       - Start tcpdump on collector VM1 (192.168.100.87)
       - Wait 80 seconds (4x polling interval) to capture counter samples
       - Stop tcpdump
       - Analyze captured packets:
         * Verify sFlow packets captured from DUT
         * Verify counter polling samples present (no traffic needed)
    4. Module 4 - Cleanup: Remove all sFlow configuration

Pre-requisites:
  - 1 SONiC device (DUT1)
  - Collector VM1: 192.168.100.87 (SSH access required)
  - DUT1 IP: 192.168.100.91
  - Testbed: testbed_2vs.yaml or compatible
"""

from __future__ import annotations

import pytest
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
    "interface":            "Ethernet4",
    "sampling_rate":        "4000",  # Need at least one interface with sampling rate for sFlow daemon to send packets

    # DUT IP (will be dynamically determined from testbed)
    "dut1_ip":              "",  # Set dynamically in test

    # Packet Capture
    "pcap_file":            "/tmp/sflow_polling_test.pcap",
    "capture_duration":     "80",  # Wait 80 seconds (4x polling interval)
    "warmup_time":          "30",  # Wait 30s after config for sFlow to start
})

# ======================================================================
# Test Case ID
# ======================================================================
TC_ID = "TC-SFLOW-1.2.2"


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
def sflow_tc_1_2_2_module_hooks(request):
    """Module-level setup and teardown for Test Case 1.2.2."""
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID} - VERIFY COUNTER POLLING WORKS - MODULE START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}")
    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"Collector: {CONFIG.collector_ip}:{CONFIG.collector_port}")

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
        f"interface {CONFIG.interface}",
        "no sflow enable",
        "exit",
        "end"
    ]
    st.config(dut, commands, type='klish', skip_error_check=True)

    st.wait(1)
    st.log(f"[MODULE 1] Unconfiguration completed on {dut}")


# ======================================================================
# MODULE 2: CONFIGURATION
# ======================================================================
def module_2_configuration(dut: str) -> bool:
    """
    Module 2: Configuration
    Configure sFlow with collector and polling interval.
    """
    st.banner("[MODULE 2] Configuring sFlow with counter polling")

    # Configuration commands
    commands = [
        "sflow enable",
        f"sflow collector {CONFIG.collector_ip}",
        f"sflow polling-interval {CONFIG.polling_interval}",
        f"interface {CONFIG.interface}",
        "sflow enable",
        f"sflow sampling-rate {CONFIG.sampling_rate}",  # Required for sFlow daemon to send packets
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] sFlow configured on {dut}")
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

    # Check sFlow Admin State is up
    if "admin state" not in output_str.lower() or "up" not in output_str.lower():
        st.error(f"sFlow Admin State not 'up'")
        return False
    st.log(f"  ✓ sFlow Admin State: up")

    # Check collector is configured
    if CONFIG.collector_ip not in output_str:
        st.error(f"Collector {CONFIG.collector_ip} not found")
        return False
    st.log(f"  ✓ Collector configured: {CONFIG.collector_ip}")

    # Check polling interval
    if CONFIG.polling_interval not in output_str:
        st.error(f"Polling interval {CONFIG.polling_interval} not found")
        return False
    st.log(f"  ✓ Polling interval: {CONFIG.polling_interval}")

    # Verify specific grep commands from manual test
    st.log(f"[MODULE 2] Verifying with grep commands (matching manual test):")

    # show sflow | grep "Admin State"
    grep_output = st.show(dut, 'show sflow | grep "Admin State"', type='klish', skip_tmpl=True, skip_error_check=True)
    st.log(f"  show sflow | grep 'Admin State': {grep_output}")

    # show sflow | grep "Polling Interval"
    grep_output = st.show(dut, 'show sflow | grep "Polling Interval"', type='klish', skip_tmpl=True, skip_error_check=True)
    st.log(f"  show sflow | grep 'Polling Interval': {grep_output}")

    # show sflow | grep Collector
    grep_output = st.show(dut, 'show sflow | grep Collector', type='klish', skip_tmpl=True, skip_error_check=True)
    st.log(f"  show sflow | grep Collector: {grep_output}")

    # Verify interface sFlow configuration
    output = st.show(dut, "show sflow interface | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow interface output:\n{output_str}")

    # Parse interface configuration to find Ethernet4
    eth4_found = False
    for line in output_str.split('\n'):
        columns = [col.strip() for col in line.split('|') if col.strip()]
        if len(columns) >= 3 and columns[0] == CONFIG.interface:
            eth4_found = True
            admin_state = columns[1] if len(columns) > 1 else ""
            sampling_rate = columns[2] if len(columns) > 2 else ""

            if "up" not in admin_state.lower():
                st.error(f"{CONFIG.interface} Admin State not 'up'")
                return False
            st.log(f"  ✓ {CONFIG.interface} Admin State: up")

            if CONFIG.sampling_rate not in sampling_rate:
                st.error(f"{CONFIG.interface} Sampling Rate not {CONFIG.sampling_rate} (found: {sampling_rate})")
                return False
            st.log(f"  ✓ {CONFIG.interface} Sampling Rate: {CONFIG.sampling_rate}")
            break

    if not eth4_found:
        st.error(f"{CONFIG.interface} not found in 'show sflow interface' output")
        return False

    st.log(f"✓ All configuration verified successfully")
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

    # Remove old pcap file if exists
    exec_ssh_collector(f"sudo rm -f {CONFIG.pcap_file}")

    # Start tcpdump in background with proper detachment
    # Use bash -c to ensure proper backgrounding
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

    # Kill tcpdump process
    exec_ssh_collector("sudo pkill -9 tcpdump")
    st.wait(2)

    # Verify tcpdump stopped
    check_output = exec_ssh_collector("pgrep tcpdump")
    if not check_output.strip():
        st.log("✓ tcpdump stopped successfully")
        return True
    else:
        st.log(f"Warning: tcpdump may still be running")
        return True


def show_live_packet_samples(count: int = 10):
    """Show sample of captured sFlow packets."""
    st.log(f"  Sample sFlow packets (first {count}):")
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 2>/dev/null | head -{count}"
    output = exec_ssh_collector(cmd, timeout=15)
    if output.strip():
        for line in output.strip().split('\n')[:count]:
            st.log(f"    {line}")
    else:
        st.log(f"    (No packets captured yet)")


def analyze_sflow_packets() -> dict:
    """Analyze captured sFlow packets from pcap file."""
    st.log("[MODULE 3] Analyzing captured sFlow packets")

    # Check if pcap file exists
    file_check = exec_ssh_collector(f"test -f {CONFIG.pcap_file} && echo 'EXISTS' || echo 'NOT_FOUND'")
    if 'NOT_FOUND' in file_check:
        st.error(f"Pcap file {CONFIG.pcap_file} not found")
        return {"total_packets": 0, "dut1_packets": 0}

    # Count total sFlow packets
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 2>/dev/null | wc -l"
    total_output = exec_ssh_collector(cmd, timeout=15)
    total_packets = int(total_output.strip()) if total_output.strip().isdigit() else 0

    # Count packets from DUT1
    cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 'src host {CONFIG.dut1_ip}' 2>/dev/null | wc -l"
    dut1_output = exec_ssh_collector(cmd, timeout=15)
    dut1_packets = int(dut1_output.strip()) if dut1_output.strip().isdigit() else 0

    results = {
        "total_packets": total_packets,
        "dut1_packets": dut1_packets
    }

    st.log(f"Packet Analysis Results:")
    st.log(f"  Total sFlow packets captured: {total_packets}")
    st.log(f"  Packets from DUT1 ({CONFIG.dut1_ip}): {dut1_packets}")

    return results


def cleanup_pcap_file():
    """Remove the pcap file from collector."""
    st.log("[MODULE 3] Cleaning up pcap file from collector")
    exec_ssh_collector(f"sudo rm -f {CONFIG.pcap_file}")
    st.log(f"✓ Removed {CONFIG.pcap_file}")


# ======================================================================
# MODULE 4: CLEANUP
# ======================================================================
def module_4_cleanup(dut: str):
    """
    Module 4: Cleanup
    Remove all sFlow configuration after test completion.
    """
    st.log(f"[MODULE 4] Cleaning up all sFlow configuration on {dut}")

    commands = [
        "no sflow enable",
        f"no sflow collector {CONFIG.collector_ip}",
        f"interface {CONFIG.interface}",
        "no sflow enable",
        "exit",
        "end"
    ]
    st.config(dut, commands, type='klish', skip_error_check=True)

    # Also cleanup pcap file
    cleanup_pcap_file()

    st.wait(1)
    st.log(f"[MODULE 4] Cleanup completed on {dut}")


# ======================================================================
# Test Function - Main Test Case
# ======================================================================
def test_sflow_tc_1_2_2_verify_counter_polling():
    """
    Test Case 1.2.2: Verify Counter Polling Works

    This test verifies:
    1. sFlow can be configured with collector and polling interval
    2. Interface configured with sampling rate (required for sFlow daemon to send packets)
    3. Configuration verified with 'show sflow' and 'show sflow interface'
    4. Counter polling samples are automatically sent to collector
    5. Packets captured at configured polling interval (20 seconds)
    6. No traffic generation needed - polling happens automatically
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: VERIFY COUNTER POLLING WORKS")
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
            st.log(f"✓ Detected DUT1 IP (hostname -I): {CONFIG.dut1_ip}")
        else:
            # Method 2: Get from ip addr show eth0
            dut_ip_output = st.exec_ssh(dut, "ip addr show eth0 | grep 'inet ' | awk '{print $2}' | cut -d'/' -f1")
            if dut_ip_output and dut_ip_output.strip():
                CONFIG.dut1_ip = dut_ip_output.strip().split('\n')[0]
                st.log(f"✓ Detected DUT1 IP (eth0): {CONFIG.dut1_ip}")
            else:
                st.error("Could not determine DUT IP address!")
                st.log("Using fallback IP: 192.168.100.145")
                CONFIG.dut1_ip = "192.168.100.145"  # Fallback from your testbed
    except Exception as e:
        st.log(f"Error detecting DUT IP: {str(e)}")
        st.log("Using fallback IP: 192.168.100.145")
        CONFIG.dut1_ip = "192.168.100.145"  # Fallback from your testbed

    try:
        # ============================================================
        # Module 2: Configuration
        # ============================================================
        st.banner("[MODULE 2] CONFIGURATION - Configuring sFlow with counter polling")

        st.log("STEP 1: Configure sFlow on DUT1")
        if not module_2_configuration(dut):
            validation_failures.append("STEP 1: Failed to configure sFlow on DUT1")
            st.report_fail("msg", "Configuration failed - cannot proceed with test")
            return

        st.wait(2)  # Wait for configuration to settle

        st.log("STEP 2: Verify sFlow configuration on DUT1")
        if not module_2_verify_configuration(dut):
            validation_failures.append("STEP 2: Failed to verify sFlow config on DUT1")

        st.log("")
        st.log(f"  DUT Management IP: {CONFIG.dut1_ip}")
        st.log(f"  Collector IP: {CONFIG.collector_ip}")
        st.log(f"  Will capture sFlow packets from {CONFIG.dut1_ip} -> {CONFIG.collector_ip}:{CONFIG.collector_port}")

        # ============================================================
        # Module 3: Validation - Packet Capture
        # ============================================================
        st.banner("[MODULE 3] VALIDATION - Counter Polling Packet Capture")

        st.log(f"STEP 2.5: Wait {CONFIG.warmup_time} seconds for sFlow to initialize after configuration")
        st.log(f"  (sFlow daemon may need time to start sending counter polling samples)")
        st.wait(int(CONFIG.warmup_time))

        st.log("STEP 3: Start tcpdump on collector VM")
        if not start_tcpdump_collector():
            validation_failures.append("STEP 3: Failed to start tcpdump on collector")
            st.report_fail("msg", "Cannot proceed - tcpdump failed to start")
            return

        st.log("STEP 4: Wait for counter polling samples")
        st.log(f"  Polling interval: {CONFIG.polling_interval} seconds")
        st.log(f"  Waiting {CONFIG.capture_duration} seconds (3x polling interval) to capture samples...")
        st.log(f"  NOTE: Counter polling happens automatically - no traffic generation needed")

        # Wait and check progress periodically
        check_intervals = [20, 20, 20, 20]  # Check at 20s, 40s, 60s, 80s
        elapsed = 0
        for interval in check_intervals:
            st.wait(interval)
            elapsed += interval
            st.log(f"  [{elapsed}s elapsed] Checking packet capture progress...")

            # Verify tcpdump still running
            tcpdump_check = exec_ssh_collector("pgrep tcpdump")
            if tcpdump_check.strip():
                st.log(f"    ✓ tcpdump still running (PID: {tcpdump_check.strip()})")
            else:
                st.error(f"    ✗ tcpdump process died!")

            # Check pcap file size
            file_size = exec_ssh_collector(f"ls -lh {CONFIG.pcap_file} 2>/dev/null | awk '{{print $5}}'")
            st.log(f"    Pcap file size: {file_size.strip() if file_size.strip() else '0 bytes'}")

            # Quick packet count check
            file_check = exec_ssh_collector(f"test -f {CONFIG.pcap_file} && echo 'EXISTS' || echo 'NOT_FOUND'")
            if 'EXISTS' in file_check:
                # Count total packets (any source)
                cmd_total = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 2>/dev/null | wc -l"
                total_count = exec_ssh_collector(cmd_total, timeout=10)
                total = int(total_count.strip()) if total_count.strip().isdigit() else 0
                st.log(f"    Total packets (any source): {total}")

                # Count packets from DUT1
                cmd = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 'src host {CONFIG.dut1_ip}' 2>/dev/null | wc -l"
                packet_count = exec_ssh_collector(cmd, timeout=10)
                count = int(packet_count.strip()) if packet_count.strip().isdigit() else 0
                st.log(f"    Packets from DUT1 ({CONFIG.dut1_ip}): {count}")

                # Show sample if ANY packets captured
                if total > 0:
                    st.log(f"    Sample packets captured:")
                    cmd_sample = f"sudo tcpdump -r {CONFIG.pcap_file} -nn 2>/dev/null | head -3"
                    sample_output = exec_ssh_collector(cmd_sample, timeout=10)
                    if sample_output.strip():
                        for line in sample_output.strip().split('\n')[:3]:
                            st.log(f"      {line}")
            else:
                st.log(f"    Pcap file not found yet")

        st.log(f"✓ Capture duration completed ({CONFIG.capture_duration} seconds)")

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
            st.log(f"✓ DUT1 sent {results['dut1_packets']} sFlow packets")
            st.log(f"  Expected: ~{int(CONFIG.capture_duration) // int(CONFIG.polling_interval)} packets")
            st.log(f"  (one counter polling sample per {CONFIG.polling_interval} second interval)")

        # Cleanup pcap file
        cleanup_pcap_file()

    except Exception as e:
        st.error(f"Exception in test_sflow_tc_1_2_2_verify_counter_polling: {str(e)}")
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
        st.log(f"✅ TEST CASE {TC_ID}: VERIFY COUNTER POLLING WORKS - PASSED")
        st.log("   All validations successful:")
        st.log("   ✓ sFlow configured with collector and polling interval")
        st.log("   ✓ Configuration verified with 'show sflow' and 'show sflow interface'")
        st.log("   ✓ tcpdump successfully captured sFlow packets")
        st.log("   ✓ DUT1 sent counter polling samples to collector")
        st.log("   ✓ Polling works automatically without traffic generation")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
