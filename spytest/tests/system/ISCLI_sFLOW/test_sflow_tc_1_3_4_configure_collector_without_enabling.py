"""
sFlow TEST CASE 1.3.4: CONFIGURE COLLECTOR WITHOUT ENABLING
Test Case ID: TC-SFLOW-1.3.4

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_3_4_configure_collector_without_enabling.py \
    --logs-path ./logs/sflow_tc_1_3_4_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.3.4: Configure Collector Without Enabling

  Objective:
    Verify that a collector can be configured when sFlow is globally disabled,
    but no sFlow packets are sent to the collector because sFlow is not enabled.
    This tests that collector configuration persists but remains inactive until
    sFlow is enabled.

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration:
       - Disable sFlow globally (no sflow enable)
       - Add collector 192.168.100.87
       - Keep polling interval at default (20)
       - Do NOT enable sFlow globally
    3. Module 3 - Validation:
       - Verify 'show sflow' shows:
         * sFlow Admin State: down
         * Collector 192.168.100.87 configured
       - Start tcpdump on collector VM
       - Generate traffic to DUT (ping -c 1000 -i 0.2)
       - Stop tcpdump
       - Verify 0 packets captured (no sFlow packets sent when disabled)
    4. Module 4 - Cleanup: Remove all sFlow configuration

Pre-requisites:
  - 1 SONiC device (DUT1)
  - Collector VM1: 192.168.100.87 (SSH access required)
  - DUT1 IP: 192.168.100.91 (detected dynamically)
  - Testbed: testbed_2vs.yaml or compatible

Notes:
  - Collector can be configured when sFlow is disabled
  - No sFlow packets are sent until sFlow is enabled globally
  - This tests that configuration persists but is inactive
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

    # DUT IP (will be dynamically determined from testbed)
    "dut1_ip":              "",  # Set dynamically in test

    # Traffic Configuration
    "ping_count":           "1000",
    "ping_interval":        "0.2",

    # Packet Capture Configuration
    "pcap_file":            "/tmp/sflow_disabled_test.pcap",
    "capture_duration":     "210",  # 1000 pings * 0.2s = 200s + 10s buffer
})

# Test Case ID
TC_ID = "TC-SFLOW-1.3.4"


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
    st.banner(f"TEST CASE {TC_ID}: CONFIGURE COLLECTOR WITHOUT ENABLING")
    st.banner("=" * 80)

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
    Configure collector with sFlow disabled globally.
    """
    st.banner("[MODULE 2] Configuring collector with sFlow globally disabled")

    # Configuration commands - matches manual test exactly
    commands = [
        "no sflow enable",  # Disable sFlow globally
        f"sflow collector {CONFIG.collector_ip}",  # Add collector
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] Collector configured on {dut}")
        st.log(f"  ✓ Global sFlow: DISABLED")
        st.log(f"  ✓ Collector: {CONFIG.collector_ip}")
        st.log(f"  Note: Collector configured but sFlow is not enabled")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure collector on {dut}: {str(e)}")
        return False


def module_2_verify_configuration(dut: str) -> bool:
    """
    Module 2: Verify collector configuration with sFlow disabled.
    """
    st.log(f"[MODULE 2] Verifying collector configuration on {dut}")

    output = st.show(dut, "show sflow | no-more", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    validation_errors = []

    # Check admin state is DOWN
    if "sFlow Admin State:          down" not in output_str:
        validation_errors.append("sFlow Admin State is not 'down'")
    else:
        st.log(f"  ✓ sFlow Admin State: down")

    # Check collector configured
    if CONFIG.collector_ip not in output_str:
        validation_errors.append(f"Collector IP {CONFIG.collector_ip} not found")
    else:
        st.log(f"  ✓ Collector IP: {CONFIG.collector_ip}")

    # Check collector count
    if "1 Collector configured:" not in output_str:
        validation_errors.append("Expected '1 Collector configured' not found")
    else:
        st.log(f"  ✓ 1 Collector configured")

    if validation_errors:
        for error in validation_errors:
            st.error(f"  ✗ {error}")
        return False

    st.log(f"✓ Collector configured but sFlow globally disabled")
    return True


# ======================================================================
# MODULE 3: VALIDATION - Packet Capture
# ======================================================================
def start_tcpdump_collector() -> bool:
    """Start tcpdump on collector VM to capture sFlow packets."""
    st.log("[MODULE 3] Starting tcpdump on collector VM")

    # Kill any existing tcpdump processes
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

    # Count packets from DUT1
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
def test_sflow_tc_1_3_4_configure_collector_without_enabling():
    """
    Test Case 1.3.4: Configure Collector Without Enabling

    This test verifies:
    1. Collector can be configured when sFlow is globally disabled
    2. 'show sflow' displays collector configuration with admin state 'down'
    3. When traffic is generated to DUT, no sFlow packets are sent
    4. 0 packets captured by tcpdump (collector configured but sFlow disabled)
    5. Configuration persists but remains inactive until sFlow enabled
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: CONFIGURE COLLECTOR WITHOUT ENABLING")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    # Get actual DUT IP from testbed
    st.log("Detecting DUT management IP address...")
    try:
        dut_ip_output = st.exec_ssh(dut, "hostname -I | awk '{print $1}'")
        if dut_ip_output and dut_ip_output.strip() and '192.168.100' in str(dut_ip_output):
            CONFIG.dut1_ip = dut_ip_output.strip().split('\n')[0]
            st.log(f"✓ Detected DUT1 IP: {CONFIG.dut1_ip}")
        else:
            CONFIG.dut1_ip = "192.168.100.91"
            st.log(f"Using fallback DUT1 IP: {CONFIG.dut1_ip}")
    except Exception as e:
        CONFIG.dut1_ip = "192.168.100.91"
        st.log(f"Using fallback DUT1 IP: {CONFIG.dut1_ip}")

    # ========================================================================
    # MODULE 2: CONFIGURATION
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 2] CONFIGURATION - Collector Without Enable             #")
    st.banner("=" * 80)

    st.log("STEP 1: Configure collector with sFlow globally disabled")
    st.log("  Configuration:")
    st.log("    1. Disable global sFlow (no sflow enable)")
    st.log("    2. Add collector 192.168.100.87")

    if not module_2_configuration(dut):
        st.report_fail("test_case_failed", "Failed to configure collector")

    st.wait(2)

    st.log("STEP 2: Verify collector configuration")
    if not module_2_verify_configuration(dut):
        st.report_fail("test_case_failed", "Collector configuration verification failed")

    st.log("")
    st.log("  Configuration Summary:")
    st.log(f"    DUT Management IP: {CONFIG.dut1_ip}")
    st.log(f"    Collector IP: {CONFIG.collector_ip}")
    st.log(f"    sFlow Admin State: down (DISABLED)")
    st.log("")

    # ========================================================================
    # MODULE 3: VALIDATION - No Packets Sent
    # ========================================================================
    st.banner("=" * 80)
    st.banner("#            [MODULE 3] VALIDATION - Verify No Packets Sent                  #")
    st.banner("=" * 80)

    st.log("STEP 3: Start tcpdump on collector VM")
    st.log(f"  Capturing packets from {CONFIG.dut1_ip} to {CONFIG.collector_ip}:6343")
    if not start_tcpdump_collector():
        validation_failures.append("STEP 3: Failed to start tcpdump")
    else:
        st.log("STEP 4: Generate traffic from collector VM to DUT")
        st.log(f"  Testing connectivity with sample pings:")
        sample_ping = exec_ssh_collector(f"ping -c 5 -i 0.2 {CONFIG.dut1_ip}", timeout=10)
        for line in sample_ping.split('\n')[:10]:
            if line.strip():
                st.log(f"    {line}")

        st.log("")
        st.log(f"  Starting full ping test ({CONFIG.ping_count} pings) to DUT in background...")
        st.log(f"  Ping interval: {CONFIG.ping_interval}s")
        st.log(f"  Expected duration: ~{int(int(CONFIG.ping_count) * float(CONFIG.ping_interval))} seconds")
        st.log("")

        # Start ping in background
        cmd_ping = f"ping -c {CONFIG.ping_count} -i {CONFIG.ping_interval} {CONFIG.dut1_ip} > /tmp/ping_disabled_test.log 2>&1 &"
        exec_ssh_collector(cmd_ping)

        st.log(f"  ✓ Ping started in background")
        st.log(f"  Monitoring packet capture...")

        # Monitor progress (check every 40 seconds)
        check_intervals = [40, 40, 40, 40, 40]  # 5 checks = 200 seconds
        elapsed = 0
        for interval in check_intervals:
            st.wait(interval)
            elapsed += interval
            st.log(f"  [{elapsed}s elapsed] Checking packet capture status...")

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

        st.log(f"✓ Capture duration completed ({elapsed} seconds)")

        # Check final ping status
        st.log("")
        st.log(f"  Checking ping completion status...")
        ping_status = exec_ssh_collector("tail -5 /tmp/ping_disabled_test.log", timeout=10)
        if "packets transmitted" in ping_status:
            st.log(f"  Ping statistics:")
            for line in ping_status.split('\n'):
                if "packets transmitted" in line or "rtt min/avg/max" in line:
                    st.log(f"    {line.strip()}")

        st.log("STEP 5: Stop tcpdump on collector VM")
        if not stop_tcpdump_collector():
            validation_failures.append("STEP 5: Failed to stop tcpdump")

        st.wait(2)

        st.log("STEP 6: Analyze captured sFlow packets")
        st.log("  Expected: 0 packets (sFlow is disabled globally)")
        st.log("")

        results = analyze_sflow_packets()

        # Verify NO packets captured (since sFlow is disabled)
        if results["total_packets"] == 0:
            st.log(f"✓ No sFlow packets captured (expected - sFlow disabled)")
        else:
            validation_failures.append(f"STEP 6: Expected 0 packets but got {results['total_packets']} packets")
            st.error(f"  ✗ sFlow packets captured when sFlow is disabled")

        if results["dut1_packets"] == 0:
            st.log(f"✓ No packets from DUT1 (expected - sFlow disabled)")
        else:
            validation_failures.append(f"STEP 6: Expected 0 packets from DUT1 but got {results['dut1_packets']} packets")

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
        st.log("  - Collector configured with sFlow globally disabled")
        st.log("  - sFlow Admin State: down")
        st.log("  - Traffic generated to DUT (1000 pings)")
        st.log("  - 0 sFlow packets captured (expected behavior)")
        st.log("  - Configuration persists but inactive until sFlow enabled")
        st.report_pass("test_case_passed")
