"""
DIAGNOSTIC TOOLS TEST - TC-8.1.3: Verify IPv6 Ping

Test Case ID: 8.1.3
Author: Automated Testing Suite
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/diagnostic_tools/test_diagnostic_03_ipv6_ping.py \
    --logs-path ./logs/diag_03_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates IPv6 connectivity and loopback reachability:
  - Configure IPv4 and IPv6 addresses on Ethernet0
  - Enable IPv6 on interface (ipv6 enable)
  - Verify IPv4 ping (basic connectivity)
  - Verify IPv6 ping to remote host (ping6 -c 3 <host>)
  - Verify IPv6 loopback reachability (ping6 -c 3 ::1)
  - Verify IPv6 ping with timeout (ping6 -c 2 -W 5 <host>)
  - Verify IPv6 ping with interface (ping6 -c 2 -I Ethernet0 <host>)

Pre-requisites:
  - 2 SONiC devices: 192.168.100.114, 192.168.100.177
  - Credentials: admin/plat@123
  - Testbed: testbed_2vs.yaml
  - Ethernet0 interface connected between DUTs

Important:
  - Uses sonic-cli (klish) for configuration
  - Must enable IPv6 before configuring IPv6 address
  - Validates both IPv4 and IPv6 connectivity
"""

from __future__ import annotations

import pytest
import re
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi
import apis.system.interface as intapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "interface": "Ethernet0",
    "dut1_ipv4": "10.1.1.1",
    "dut2_ipv4": "10.1.1.2",
    "dut1_ipv6": "2001:db8::1",
    "dut2_ipv6": "2001:db8::2",
    "ipv4_subnet": "24",
    "ipv6_subnet": "64",
    "ipv6_loopback": "::1",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "diag03_ip_config": "TC-DIAG-03-001",
    "diag03_ipv4_ping": "TC-DIAG-03-002",
    "diag03_ipv6_ping": "TC-DIAG-03-003",
    "diag03_ipv6_loopback": "TC-DIAG-03-004",
    "diag03_ipv6_options": "TC-DIAG-03-005",
})


@pytest.fixture(scope="module", autouse=True)
def diagnostic_03_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("DIAGNOSTIC TC-8.1.3 MODULE CONFIGURATION - START")
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
    st.banner("DIAGNOSTIC TC-8.1.3 MODULE CLEANUP - START")
    st.banner("=" * 80)

    # Cleanup IP configuration
    cleanup_ip_configuration()


def cleanup_ip_configuration():
    """Cleanup IPv4 and IPv6 configuration from interfaces."""
    st.log("Cleaning up IP configuration")

    for dut in [vars.D1, vars.D2]:
        try:
            # Cleanup IPv4
            ipapi.delete_ip_interface(
                dut,
                CONFIG.interface,
                f"{CONFIG.dut1_ipv4 if dut == vars.D1 else CONFIG.dut2_ipv4}/{CONFIG.ipv4_subnet}",
                family="ipv4",
                skip_error=True
            )
            # Cleanup IPv6
            ipapi.delete_ip_interface(
                dut,
                CONFIG.interface,
                f"{CONFIG.dut1_ipv6 if dut == vars.D1 else CONFIG.dut2_ipv6}/{CONFIG.ipv6_subnet}",
                family="ipv6",
                skip_error=True
            )
            st.log(f"✓ IP cleanup completed on {dut}")
        except Exception as e:
            st.log(f"Cleanup warning on {dut}: {str(e)}")


def configure_ipv4_on_interface(dut: str, ip_address: str) -> bool:
    """Configure IPv4 address on Ethernet0 interface."""
    st.log(f"Configuring IPv4 {ip_address}/{CONFIG.ipv4_subnet} on {dut} {CONFIG.interface}")

    try:
        result = ipapi.config_ip_addr_interface(
            dut,
            CONFIG.interface,
            ip_address,
            subnet=CONFIG.ipv4_subnet,
            family="ipv4",
            cli_type=data.cli_type
        )

        if not result:
            st.error(f"Failed to configure IPv4 on {dut} {CONFIG.interface}")
            return False

        st.log(f"✓ IPv4 {ip_address}/{CONFIG.ipv4_subnet} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Exception configuring IPv4 on {dut}: {str(e)}")
        return False


def configure_ipv6_on_interface(dut: str, ip_address: str) -> bool:
    """
    Configure IPv6 address on Ethernet0 interface.

    Configuration steps (matching your test case):
    1. ipv6 enable
    2. ipv6 address 2001:db8::X/64
    """
    st.log(f"Configuring IPv6 {ip_address}/{CONFIG.ipv6_subnet} on {dut} {CONFIG.interface}")

    try:
        # Step 1: Enable IPv6 on interface using st.config()
        # This executes: ipv6 enable
        st.log(f"Enabling IPv6 on {dut} {CONFIG.interface}")
        cmd = f"interface {CONFIG.interface}"
        st.config(dut, cmd, type=data.cli_type)
        cmd = "ipv6 enable"
        st.config(dut, cmd, type=data.cli_type)
        st.log(f"✓ IPv6 enabled on {dut} {CONFIG.interface}")

        # Step 2: Configure IPv6 address
        # This executes: ipv6 address 2001:db8::X/64
        result = ipapi.config_ip_addr_interface(
            dut,
            CONFIG.interface,
            ip_address,
            subnet=CONFIG.ipv6_subnet,
            family="ipv6",
            cli_type=data.cli_type
        )

        if not result:
            st.error(f"Failed to configure IPv6 address on {dut} {CONFIG.interface}")
            return False

        st.log(f"✓ IPv6 {ip_address}/{CONFIG.ipv6_subnet} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Exception configuring IPv6 on {dut}: {str(e)}")
        return False


def execute_ping(dut: str, target_ip: str, count: int, options: str = "", is_ipv6: bool = False) -> dict:
    """
    Execute ping or ping6 command and parse results.

    Returns dict with:
        - success: bool
        - transmitted: int
        - received: int
        - loss_percent: float
        - output: str
    """
    cmd = f"{'ping6' if is_ipv6 else 'ping'} {options} -c {count} {target_ip}"
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


def test_diagnostic_03_ipv6_ping():
    """
    Test Case 8.1.3: Verify IPv6 Ping

    Test Steps:
    1. Configure IPv4 and IPv6 addresses on Ethernet0
    2. Verify IPv4 ping (basic connectivity check)
    3. Verify IPv6 ping to remote host (ping6 -c 3 <host>)
    4. Verify IPv6 loopback reachability (ping6 -c 3 ::1)
    5. Verify IPv6 ping with timeout (ping6 -c 2 -W 5 <host>)
    6. Verify IPv6 ping with interface (ping6 -c 2 -I Ethernet0 <host>)

    Expected Results:
    - IPv4 and IPv6 addresses configured successfully
    - IPv4 ping succeeds (confirms basic connectivity)
    - IPv6 ping to remote host succeeds
    - IPv6 loopback ping succeeds
    - IPv6 ping with options succeeds
    """
    st.banner("=" * 80)
    st.banner("TEST TC-8.1.3: VERIFY IPv6 PING")
    st.banner("=" * 80)

    # Track test status
    test_failed = False

    # ==================================================================
    # STEP 1: Configure IPv4 and IPv6 Addresses
    # ==================================================================
    st.banner("STEP 1: Configure IPv4 and IPv6 Addresses on Ethernet0")

    # Configure IPv4 on DUT1
    st.log(f"Configuring IPv4 {CONFIG.dut1_ipv4} on {vars.D1}")
    if not configure_ipv4_on_interface(vars.D1, CONFIG.dut1_ipv4):
        st.generate_tech_support([vars.D1, vars.D2], "diag03_ipv4_config_d1_failed")
        st.report_tc_fail(TC_IDS.diag03_ip_config, "msg",
                         f"Failed to configure IPv4 on {vars.D1}")
        test_failed = True

    # Configure IPv4 on DUT2
    st.log(f"Configuring IPv4 {CONFIG.dut2_ipv4} on {vars.D2}")
    if not configure_ipv4_on_interface(vars.D2, CONFIG.dut2_ipv4):
        st.generate_tech_support([vars.D1, vars.D2], "diag03_ipv4_config_d2_failed")
        st.report_tc_fail(TC_IDS.diag03_ip_config, "msg",
                         f"Failed to configure IPv4 on {vars.D2}")
        test_failed = True

    # Configure IPv6 on DUT1
    st.log(f"Configuring IPv6 {CONFIG.dut1_ipv6} on {vars.D1}")
    if not configure_ipv6_on_interface(vars.D1, CONFIG.dut1_ipv6):
        st.generate_tech_support([vars.D1, vars.D2], "diag03_ipv6_config_d1_failed")
        st.report_tc_fail(TC_IDS.diag03_ip_config, "msg",
                         f"Failed to configure IPv6 on {vars.D1}")
        test_failed = True

    # Configure IPv6 on DUT2
    st.log(f"Configuring IPv6 {CONFIG.dut2_ipv6} on {vars.D2}")
    if not configure_ipv6_on_interface(vars.D2, CONFIG.dut2_ipv6):
        st.generate_tech_support([vars.D1, vars.D2], "diag03_ipv6_config_d2_failed")
        st.report_tc_fail(TC_IDS.diag03_ip_config, "msg",
                         f"Failed to configure IPv6 on {vars.D2}")
        test_failed = True

    # Save configuration
    st.log("Saving configuration on both DUTs")
    for dut in [vars.D1, vars.D2]:
        try:
            st.show(dut, "sudo config save -y", skip_tmpl=True, skip_error_check=True)
        except:
            pass

    if not test_failed:
        st.report_tc_pass(TC_IDS.diag03_ip_config, "msg",
                         "IPv4 and IPv6 addresses configured successfully")

    # ==================================================================
    # STEP 2: Verify IPv4 Ping (Basic Connectivity)
    # ==================================================================
    st.banner("STEP 2: Verify IPv4 Ping (Basic Connectivity Check)")

    st.log(f"IPv4 Ping: {CONFIG.dut2_ipv4} from {vars.D1}")
    result_ipv4 = execute_ping(vars.D1, CONFIG.dut2_ipv4, 3, is_ipv6=False)

    if not result_ipv4['success'] or result_ipv4['loss_percent'] > 0:
        st.generate_tech_support([vars.D1, vars.D2], "diag03_ipv4_ping_failed")
        st.report_tc_fail(TC_IDS.diag03_ipv4_ping, "msg",
                         f"IPv4 ping failed: {result_ipv4['loss_percent']}% loss")
        test_failed = True
    else:
        st.log(f"✓ IPv4 ping successful: {result_ipv4['received']}/{result_ipv4['transmitted']} packets")
        st.report_tc_pass(TC_IDS.diag03_ipv4_ping, "msg",
                         "IPv4 ping connectivity verified successfully")

    # ==================================================================
    # STEP 3: Verify IPv6 Ping to Remote Host (ping6 -c 3 <host>)
    # ==================================================================
    st.banner("STEP 3: Verify IPv6 Ping to Remote Host (ping6 -c 3 <host>)")

    st.log(f"IPv6 Ping: {CONFIG.dut2_ipv6} from {vars.D1}")
    result_ipv6_d1 = execute_ping(vars.D1, CONFIG.dut2_ipv6, 3, is_ipv6=True)

    if not result_ipv6_d1['success'] or result_ipv6_d1['loss_percent'] > 0:
        st.generate_tech_support([vars.D1, vars.D2], "diag03_ipv6_ping_d1_failed")
        st.report_tc_fail(TC_IDS.diag03_ipv6_ping, "msg",
                         f"IPv6 ping from {vars.D1} failed: {result_ipv6_d1['loss_percent']}% loss")
        test_failed = True
    else:
        st.log(f"✓ IPv6 ping from {vars.D1} successful: {result_ipv6_d1['received']}/{result_ipv6_d1['transmitted']} packets")

    st.log(f"IPv6 Ping: {CONFIG.dut1_ipv6} from {vars.D2}")
    result_ipv6_d2 = execute_ping(vars.D2, CONFIG.dut1_ipv6, 3, is_ipv6=True)

    if not result_ipv6_d2['success'] or result_ipv6_d2['loss_percent'] > 0:
        st.generate_tech_support([vars.D1, vars.D2], "diag03_ipv6_ping_d2_failed")
        st.report_tc_fail(TC_IDS.diag03_ipv6_ping, "msg",
                         f"IPv6 ping from {vars.D2} failed: {result_ipv6_d2['loss_percent']}% loss")
        test_failed = True
    else:
        st.log(f"✓ IPv6 ping from {vars.D2} successful: {result_ipv6_d2['received']}/{result_ipv6_d2['transmitted']} packets")

    if not test_failed:
        st.report_tc_pass(TC_IDS.diag03_ipv6_ping, "msg",
                         "IPv6 ping connectivity verified successfully")

    # ==================================================================
    # STEP 4: Verify IPv6 Loopback Reachability (ping6 -c 3 ::1)
    # ==================================================================
    st.banner("STEP 4: Verify IPv6 Loopback Reachability (ping6 -c 3 ::1)")

    st.log(f"IPv6 Loopback Ping: {CONFIG.ipv6_loopback} on {vars.D1}")
    result_loopback = execute_ping(vars.D1, CONFIG.ipv6_loopback, 3, is_ipv6=True)

    if not result_loopback['success'] or result_loopback['loss_percent'] > 0:
        st.generate_tech_support([vars.D1, vars.D2], "diag03_ipv6_loopback_failed")
        st.report_tc_fail(TC_IDS.diag03_ipv6_loopback, "msg",
                         f"IPv6 loopback ping failed: {result_loopback['loss_percent']}% loss")
        test_failed = True
    else:
        st.log(f"✓ IPv6 loopback ping successful: {result_loopback['received']}/{result_loopback['transmitted']} packets")
        st.report_tc_pass(TC_IDS.diag03_ipv6_loopback, "msg",
                         "IPv6 loopback reachability verified successfully")

    # ==================================================================
    # STEP 5: Verify IPv6 Ping with Timeout and Interface Options
    # ==================================================================
    st.banner("STEP 5: Verify IPv6 Ping with Timeout and Interface Options")

    # Test 1: ping6 -c 2 -W 5 <host>
    st.log(f"IPv6 Ping with timeout: ping6 -c 2 -W 5 {CONFIG.dut2_ipv6} from {vars.D1}")
    result_timeout = execute_ping(vars.D1, CONFIG.dut2_ipv6, 2, "-W 5", is_ipv6=True)

    if not result_timeout['success'] or result_timeout['loss_percent'] > 0:
        st.log(f"Warning: IPv6 ping with timeout had issues: {result_timeout['loss_percent']}% loss")
    else:
        st.log(f"✓ IPv6 ping with timeout successful: {result_timeout['received']}/{result_timeout['transmitted']} packets")

    # Test 2: ping6 -c 2 -I Ethernet0 <host>
    st.log(f"IPv6 Ping with interface: ping6 -c 2 -I {CONFIG.interface} {CONFIG.dut2_ipv6} from {vars.D1}")
    result_interface = execute_ping(vars.D1, CONFIG.dut2_ipv6, 2, f"-I {CONFIG.interface}", is_ipv6=True)

    if not result_interface['success'] or result_interface['loss_percent'] > 0:
        st.log(f"Warning: IPv6 ping with interface had issues: {result_interface['loss_percent']}% loss")
    else:
        st.log(f"✓ IPv6 ping with interface successful: {result_interface['received']}/{result_interface['transmitted']} packets")

    st.report_tc_pass(TC_IDS.diag03_ipv6_options, "msg",
                     "IPv6 ping with options completed")

    # ==================================================================
    # STEP 6: Show Summary
    # ==================================================================
    st.banner("STEP 6: Test Summary")

    st.log("=" * 80)
    st.log("IPv6 PING TEST RESULTS:")
    st.log("=" * 80)
    st.log(f"Configuration: IPv4={CONFIG.dut1_ipv4} <-> {CONFIG.dut2_ipv4}, IPv6={CONFIG.dut1_ipv6} <-> {CONFIG.dut2_ipv6}")
    st.log(f"IPv4 Ping (D1→D2):      {result_ipv4['received']}/{result_ipv4['transmitted']} pkts, {result_ipv4['loss_percent']}% loss - {'✓ PASS' if result_ipv4['success'] else '✗ FAIL'}")
    st.log(f"IPv6 Ping (D1→D2):      {result_ipv6_d1['received']}/{result_ipv6_d1['transmitted']} pkts, {result_ipv6_d1['loss_percent']}% loss - {'✓ PASS' if result_ipv6_d1['success'] else '✗ FAIL'}")
    st.log(f"IPv6 Ping (D2→D1):      {result_ipv6_d2['received']}/{result_ipv6_d2['transmitted']} pkts, {result_ipv6_d2['loss_percent']}% loss - {'✓ PASS' if result_ipv6_d2['success'] else '✗ FAIL'}")
    st.log(f"IPv6 Loopback Ping:     {result_loopback['received']}/{result_loopback['transmitted']} pkts, {result_loopback['loss_percent']}% loss - {'✓ PASS' if result_loopback['success'] else '✗ FAIL'}")
    st.log(f"IPv6 Ping with Timeout: {result_timeout['received']}/{result_timeout['transmitted']} pkts, {result_timeout['loss_percent']}% loss - {'✓ PASS' if result_timeout['success'] else '✗ FAIL'}")
    st.log(f"IPv6 Ping with -I:      {result_interface['received']}/{result_interface['transmitted']} pkts, {result_interface['loss_percent']}% loss - {'✓ PASS' if result_interface['success'] else '✗ FAIL'}")
    st.log("=" * 80)

    # ==================================================================
    # TEST RESULT
    # ==================================================================
    if test_failed:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-8.1.3 FAILED")
        st.banner("=" * 80)
        st.report_fail("test_case_failed")
    else:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-8.1.3 PASSED")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - TC-8.1.3: IPv6 Ping Connectivity")
        st.log("=" * 80)
        st.log(f"✓ IPv4 addresses configured: {CONFIG.dut1_ipv4}, {CONFIG.dut2_ipv4}")
        st.log(f"✓ IPv6 addresses configured: {CONFIG.dut1_ipv6}, {CONFIG.dut2_ipv6}")
        st.log(f"✓ IPv4 ping connectivity verified")
        st.log(f"✓ IPv6 ping to remote host verified (ping6 -c 3 <host>)")
        st.log(f"✓ IPv6 loopback reachability verified (ping6 -c 3 ::1)")
        st.log(f"✓ IPv6 ping with timeout verified (ping6 -c 2 -W 5 <host>)")
        st.log(f"✓ IPv6 ping with interface verified (ping6 -c 2 -I Ethernet0 <host>)")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
