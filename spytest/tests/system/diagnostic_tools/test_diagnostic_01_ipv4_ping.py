"""
DIAGNOSTIC TOOLS TEST - TC-8.1.1: Verify IPv4 Ping Basic Connectivity

Test Case ID: 8.1.1
Author: Automated Testing Suite
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/diagnostic_tools/test_diagnostic_01_ipv4_ping.py \
    --logs-path ./logs/diag_01_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv4 connectivity using ping with different options:
  - Configure IP addresses on Ethernet0 interfaces
  - Test 1: ping -c 3 <host>
  - Test 2: ping -c 2 -W 5 <host>
  - Test 3: ping -4 <host>
  - Validate packet loss and RTT statistics

Pre-requisites:
  - 2 SONiC devices: 192.168.100.114, 192.168.100.177
  - Credentials: admin/plat@123
  - Testbed: testbed_2vs.yaml
  - Ethernet0 interface connected between DUTs

Important:
  - Uses sonic-cli (klish) for configuration
  - Tests ALL ping options from test case
  - Validates packet transmission and reception
"""

from __future__ import annotations

import pytest
import re
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "interface": "Ethernet0",
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "subnet_mask": "24",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "diag01_ip_config": "TC-DIAG-01-001",
    "diag01_ping_basic": "TC-DIAG-01-002",
    "diag01_ping_timeout": "TC-DIAG-01-003",
    "diag01_ping_ipv4": "TC-DIAG-01-004",
})


@pytest.fixture(scope="module", autouse=True)
def diagnostic_01_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("DIAGNOSTIC TC-8.1.1 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    yield

    st.banner("=" * 80)
    st.banner("DIAGNOSTIC TC-8.1.1 MODULE CLEANUP - START")
    st.banner("=" * 80)

    # Cleanup IP configuration
    cleanup_ip_configuration()


def cleanup_ip_configuration():
    """Cleanup IP configuration from interfaces."""
    st.log("Cleaning up IP configuration")

    for dut in [vars.D1, vars.D2]:
        try:
            ip_addr = CONFIG.dut1_ip if dut == vars.D1 else CONFIG.dut2_ip
            ipapi.delete_ip_interface(
                dut,
                CONFIG.interface,
                f"{ip_addr}/{CONFIG.subnet_mask}",
                family="ipv4",
                skip_error=True
            )
            st.log(f"✓ IP cleanup completed on {dut}")
        except Exception as e:
            st.log(f"Cleanup warning on {dut}: {str(e)}")


def configure_ip_on_interface(dut: str, ip_address: str) -> bool:
    """Configure IP address on Ethernet0 interface."""
    st.log(f"Configuring IP {ip_address}/{CONFIG.subnet_mask} on {dut} {CONFIG.interface}")

    try:
        result = ipapi.config_ip_addr_interface(
            dut,
            CONFIG.interface,
            ip_address,
            subnet=CONFIG.subnet_mask,
            family="ipv4",
            cli_type=data.cli_type
        )

        if not result:
            st.error(f"Failed to configure IP on {dut} {CONFIG.interface}")
            return False

        st.log(f"✓ IP {ip_address}/{CONFIG.subnet_mask} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Exception configuring IP on {dut}: {str(e)}")
        return False


def execute_ping_command(dut: str, target_ip: str, ping_options: str) -> dict:
    """
    Execute ping command with specific options and parse results.

    Args:
        dut: Device to execute ping from
        target_ip: Target IP address
        ping_options: Ping command options (e.g., "-c 3", "-c 2 -W 5", "-4 -c 3")

    Returns dict with:
        - success: bool
        - transmitted: int
        - received: int
        - loss_percent: float
        - output: str
    """
    cmd = f"ping {ping_options} {target_ip}"
    st.log(f"Executing on {dut}: {cmd}")

    try:
        output = st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
        output_str = str(output)
        st.log(f"Ping output:\n{output_str}")

        result = {
            'success': False,
            'transmitted': 0,
            'received': 0,
            'loss_percent': 100.0,
            'output': output_str
        }

        # Parse ping statistics
        # Example: "3 packets transmitted, 3 received, 0% packet loss"
        match = re.search(r'(\d+) packets transmitted, (\d+) received, (\d+)% packet loss', output_str)
        if match:
            result['transmitted'] = int(match.group(1))
            result['received'] = int(match.group(2))
            result['loss_percent'] = float(match.group(3))
            result['success'] = (result['received'] > 0 and result['loss_percent'] < 100)

        st.log(f"Parsed results: TX={result['transmitted']}, RX={result['received']}, Loss={result['loss_percent']}%")
        return result

    except Exception as e:
        st.error(f"Exception executing ping on {dut}: {str(e)}")
        return {'success': False, 'transmitted': 0, 'received': 0, 'loss_percent': 100.0, 'output': str(e)}


def test_diagnostic_01_ipv4_ping():
    """
    Test Case 8.1.1: Verify IPv4 Ping Basic Connectivity

    Test Steps:
    1. Configure IP addresses on Ethernet0 interfaces
    2. Execute ping -c 3 (basic ping)
    3. Execute ping -c 2 -W 5 (ping with timeout)
    4. Execute ping -4 -c 3 (ping with IPv4 explicit)
    5. Verify all pings succeed with 0% packet loss

    Expected Results:
    - IP addresses configured successfully
    - ping -c 3: succeeds with 0% packet loss
    - ping -c 2 -W 5: succeeds with 0% packet loss
    - ping -4 -c 3: succeeds with 0% packet loss
    """
    st.banner("=" * 80)
    st.banner("TEST TC-8.1.1: VERIFY IPv4 PING BASIC CONNECTIVITY")
    st.banner("=" * 80)

    # Track test status
    test_failed = False

    # ==================================================================
    # STEP 1: Configure IP Addresses
    # ==================================================================
    st.banner("STEP 1: Configure IP Addresses on Ethernet0")

    st.log(f"Configuring IP {CONFIG.dut1_ip} on {vars.D1}")
    if not configure_ip_on_interface(vars.D1, CONFIG.dut1_ip):
        st.generate_tech_support([vars.D1, vars.D2], "diag01_ip_config_d1_failed")
        st.report_tc_fail(TC_IDS.diag01_ip_config, "msg",
                         f"Failed to configure IP on {vars.D1}")
        test_failed = True

    st.log(f"Configuring IP {CONFIG.dut2_ip} on {vars.D2}")
    if not configure_ip_on_interface(vars.D2, CONFIG.dut2_ip):
        st.generate_tech_support([vars.D1, vars.D2], "diag01_ip_config_d2_failed")
        st.report_tc_fail(TC_IDS.diag01_ip_config, "msg",
                         f"Failed to configure IP on {vars.D2}")
        test_failed = True

    if not test_failed:
        st.report_tc_pass(TC_IDS.diag01_ip_config, "msg",
                         "IP addresses configured successfully")

    # ==================================================================
    # STEP 2: Execute ping -c 3 (Basic Ping)
    # ==================================================================
    st.banner("STEP 2: Execute ping -c 3 <host> (Basic Ping)")

    st.log(f"Testing: ping -c 3 {CONFIG.dut2_ip} from {vars.D1}")
    result_basic = execute_ping_command(vars.D1, CONFIG.dut2_ip, "-c 3")

    if not result_basic['success'] or result_basic['loss_percent'] > 0:
        st.generate_tech_support([vars.D1, vars.D2], "diag01_ping_basic_failed")
        st.report_tc_fail(TC_IDS.diag01_ping_basic, "msg",
                         f"ping -c 3 failed: {result_basic['received']}/{result_basic['transmitted']} packets, {result_basic['loss_percent']}% loss")
        test_failed = True
    else:
        st.log(f"✓ ping -c 3 successful: {result_basic['received']}/{result_basic['transmitted']} packets, {result_basic['loss_percent']}% loss")
        st.report_tc_pass(TC_IDS.diag01_ping_basic, "msg",
                         f"ping -c 3 successful with 0% packet loss")

    # ==================================================================
    # STEP 3: Execute ping -c 2 -W 5 (Ping with Timeout)
    # ==================================================================
    st.banner("STEP 3: Execute ping -c 2 -W 5 <host> (Ping with Timeout)")

    st.log(f"Testing: ping -c 2 -W 5 {CONFIG.dut2_ip} from {vars.D1}")
    result_timeout = execute_ping_command(vars.D1, CONFIG.dut2_ip, "-c 2 -W 5")

    if not result_timeout['success'] or result_timeout['loss_percent'] > 0:
        st.generate_tech_support([vars.D1, vars.D2], "diag01_ping_timeout_failed")
        st.report_tc_fail(TC_IDS.diag01_ping_timeout, "msg",
                         f"ping -c 2 -W 5 failed: {result_timeout['received']}/{result_timeout['transmitted']} packets, {result_timeout['loss_percent']}% loss")
        test_failed = True
    else:
        st.log(f"✓ ping -c 2 -W 5 successful: {result_timeout['received']}/{result_timeout['transmitted']} packets, {result_timeout['loss_percent']}% loss")
        st.report_tc_pass(TC_IDS.diag01_ping_timeout, "msg",
                         f"ping -c 2 -W 5 successful with 0% packet loss")

    # ==================================================================
    # STEP 4: Execute ping -4 -c 3 (Ping with IPv4 Explicit)
    # ==================================================================
    st.banner("STEP 4: Execute ping -4 -c 3 <host> (Ping with IPv4 Explicit)")

    st.log(f"Testing: ping -4 -c 3 {CONFIG.dut2_ip} from {vars.D1}")
    result_ipv4 = execute_ping_command(vars.D1, CONFIG.dut2_ip, "-4 -c 3")

    if not result_ipv4['success'] or result_ipv4['loss_percent'] > 0:
        st.generate_tech_support([vars.D1, vars.D2], "diag01_ping_ipv4_failed")
        st.report_tc_fail(TC_IDS.diag01_ping_ipv4, "msg",
                         f"ping -4 -c 3 failed: {result_ipv4['received']}/{result_ipv4['transmitted']} packets, {result_ipv4['loss_percent']}% loss")
        test_failed = True
    else:
        st.log(f"✓ ping -4 -c 3 successful: {result_ipv4['received']}/{result_ipv4['transmitted']} packets, {result_ipv4['loss_percent']}% loss")
        st.report_tc_pass(TC_IDS.diag01_ping_ipv4, "msg",
                         f"ping -4 -c 3 successful with 0% packet loss")

    # ==================================================================
    # STEP 5: Show Summary
    # ==================================================================
    st.banner("STEP 5: Test Summary")

    st.log("=" * 80)
    st.log("PING TEST RESULTS:")
    st.log("=" * 80)
    st.log(f"Configuration: {CONFIG.dut1_ip} <-> {CONFIG.dut2_ip}")
    st.log(f"ping -c 3:        {result_basic['received']}/{result_basic['transmitted']} pkts, {result_basic['loss_percent']}% loss - {'✓ PASS' if result_basic['success'] else '✗ FAIL'}")
    st.log(f"ping -c 2 -W 5:   {result_timeout['received']}/{result_timeout['transmitted']} pkts, {result_timeout['loss_percent']}% loss - {'✓ PASS' if result_timeout['success'] else '✗ FAIL'}")
    st.log(f"ping -4 -c 3:     {result_ipv4['received']}/{result_ipv4['transmitted']} pkts, {result_ipv4['loss_percent']}% loss - {'✓ PASS' if result_ipv4['success'] else '✗ FAIL'}")
    st.log("=" * 80)

    # ==================================================================
    # TEST RESULT
    # ==================================================================
    if test_failed:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-8.1.1 FAILED")
        st.banner("=" * 80)
        st.report_fail("test_case_failed")
    else:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-8.1.1 PASSED")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - TC-8.1.1: IPv4 Ping Connectivity")
        st.log("=" * 80)
        st.log(f"✓ IP addresses configured: {CONFIG.dut1_ip}, {CONFIG.dut2_ip}")
        st.log(f"✓ ping -c 3: {result_basic['received']}/{result_basic['transmitted']} packets, 0% loss")
        st.log(f"✓ ping -c 2 -W 5: {result_timeout['received']}/{result_timeout['transmitted']} packets, 0% loss")
        st.log(f"✓ ping -4 -c 3: {result_ipv4['received']}/{result_ipv4['transmitted']} packets, 0% loss")
        st.log(f"✓ All ping options tested successfully")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
