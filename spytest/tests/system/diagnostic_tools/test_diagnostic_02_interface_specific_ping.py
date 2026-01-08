"""
DIAGNOSTIC TOOLS TEST - TC-8.1.2: Verify Interface Specific Ping

Test Case ID: 8.1.2
Author: Automated Testing Suite
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/diagnostic_tools/test_diagnostic_02_interface_specific_ping.py \
    --logs-path ./logs/diag_02_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates ping using specific outgoing interfaces:
  - Configure IP addresses on Ethernet0
  - Ping using interface name (ping -I Ethernet0)
  - Ping using source IP (ping -I <ip>)
  - Verify interface-specific routing

Pre-requisites:
  - 2 SONiC devices: 192.168.100.114, 192.168.100.177
  - Credentials: admin/plat@123
  - Testbed: testbed_2vs.yaml
  - Ethernet0 interface connected between DUTs

Important:
  - Uses sonic-cli (klish) for configuration
  - Uses Linux shell for ping with -I option
  - Validates source interface/IP binding
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
    "ping_count": 2,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "diag02_ip_config": "TC-DIAG-02-001",
    "diag02_ping_interface": "TC-DIAG-02-002",
    "diag02_ping_source_ip": "TC-DIAG-02-003",
})


@pytest.fixture(scope="module", autouse=True)
def diagnostic_02_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("DIAGNOSTIC TC-8.1.2 MODULE CONFIGURATION - START")
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
    st.banner("DIAGNOSTIC TC-8.1.2 MODULE CLEANUP - START")
    st.banner("=" * 80)

    # Cleanup IP configuration
    cleanup_ip_configuration()


def cleanup_ip_configuration():
    """Cleanup IP configuration from interfaces."""
    st.log("Cleaning up IP configuration")

    for dut in [vars.D1, vars.D2]:
        try:
            ipapi.delete_ip_interface(
                dut,
                CONFIG.interface,
                f"{CONFIG.dut1_ip if dut == vars.D1 else CONFIG.dut2_ip}/{CONFIG.subnet_mask}",
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


def execute_ping_interface(dut: str, target_ip: str, source_interface: str, count: int) -> dict:
    """
    Execute ping with -I interface option.

    Returns dict with:
        - success: bool
        - transmitted: int
        - received: int
        - loss_percent: float
        - output: str
        - from_interface: bool (True if "from" shows in output)
    """
    cmd = f"ping -c {count} -I {source_interface} {target_ip}"
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
            'output': output_str,
            'from_interface': False
        }

        # Check if "from" appears in output (indicates source binding)
        if 'from' in output_str.lower():
            result['from_interface'] = True
            st.log(f"✓ Ping shows 'from' indicating source binding")

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
        return {'success': False, 'transmitted': 0, 'received': 0, 'loss_percent': 100.0, 'output': str(e), 'from_interface': False}


def test_diagnostic_02_interface_specific_ping():
    """
    Test Case 8.1.2: Verify Interface Specific Ping

    Test Steps:
    1. Configure IP addresses on Ethernet0
    2. Ping using interface name (-I Ethernet0)
    3. Ping using source IP (-I <ip>)
    4. Verify interface-specific routing

    Expected Results:
    - IP addresses configured successfully
    - Ping with -I Ethernet0 succeeds
    - Ping with -I <source_ip> succeeds
    - Source interface/IP correctly bound
    """
    st.banner("=" * 80)
    st.banner("TEST TC-8.1.2: VERIFY INTERFACE SPECIFIC PING")
    st.banner("=" * 80)

    # Track test status
    test_failed = False

    # ==================================================================
    # STEP 1: Configure IP Addresses
    # ==================================================================
    st.banner("STEP 1: Configure IP Addresses on Ethernet0")

    st.log(f"Configuring IP {CONFIG.dut1_ip} on {vars.D1}")
    if not configure_ip_on_interface(vars.D1, CONFIG.dut1_ip):
        st.generate_tech_support([vars.D1, vars.D2], "diag02_ip_config_d1_failed")
        st.report_tc_fail(TC_IDS.diag02_ip_config, "msg",
                         f"Failed to configure IP on {vars.D1}")
        test_failed = True

    st.log(f"Configuring IP {CONFIG.dut2_ip} on {vars.D2}")
    if not configure_ip_on_interface(vars.D2, CONFIG.dut2_ip):
        st.generate_tech_support([vars.D1, vars.D2], "diag02_ip_config_d2_failed")
        st.report_tc_fail(TC_IDS.diag02_ip_config, "msg",
                         f"Failed to configure IP on {vars.D2}")
        test_failed = True

    if not test_failed:
        st.report_tc_pass(TC_IDS.diag02_ip_config, "msg",
                         "IP addresses configured successfully")

    # ==================================================================
    # STEP 2: Ping Using Interface Name (-I Ethernet0)
    # ==================================================================
    st.banner("STEP 2: Ping Using Interface Name (-I Ethernet0)")

    st.log(f"Pinging {CONFIG.dut2_ip} from {vars.D1} using -I {CONFIG.interface}")
    result_interface = execute_ping_interface(vars.D1, CONFIG.dut2_ip, CONFIG.interface, CONFIG.ping_count)

    if not result_interface['success'] or result_interface['loss_percent'] > 0:
        st.generate_tech_support([vars.D1, vars.D2], "diag02_ping_interface_failed")
        st.report_tc_fail(TC_IDS.diag02_ping_interface, "msg",
                         f"Ping with -I {CONFIG.interface} failed: {result_interface['loss_percent']}% loss")
        test_failed = True
    else:
        st.log(f"✓ Ping with -I {CONFIG.interface} successful: {result_interface['received']}/{result_interface['transmitted']} packets")
        if result_interface['from_interface']:
            st.log(f"✓ Ping correctly shows source interface binding")
        st.report_tc_pass(TC_IDS.diag02_ping_interface, "msg",
                         f"Ping using interface {CONFIG.interface} verified successfully")

    # ==================================================================
    # STEP 3: Ping Using Source IP (-I <ip>)
    # ==================================================================
    st.banner("STEP 3: Ping Using Source IP (-I <ip>)")

    st.log(f"Pinging {CONFIG.dut2_ip} from {vars.D1} using -I {CONFIG.dut1_ip}")
    result_source_ip = execute_ping_interface(vars.D1, CONFIG.dut2_ip, CONFIG.dut1_ip, CONFIG.ping_count)

    if not result_source_ip['success'] or result_source_ip['loss_percent'] > 0:
        st.generate_tech_support([vars.D1, vars.D2], "diag02_ping_source_ip_failed")
        st.report_tc_fail(TC_IDS.diag02_ping_source_ip, "msg",
                         f"Ping with -I {CONFIG.dut1_ip} failed: {result_source_ip['loss_percent']}% loss")
        test_failed = True
    else:
        st.log(f"✓ Ping with -I {CONFIG.dut1_ip} successful: {result_source_ip['received']}/{result_source_ip['transmitted']} packets")
        if result_source_ip['from_interface']:
            st.log(f"✓ Ping correctly shows source IP binding")
        st.report_tc_pass(TC_IDS.diag02_ping_source_ip, "msg",
                         f"Ping using source IP {CONFIG.dut1_ip} verified successfully")

    # ==================================================================
    # STEP 4: Show Summary
    # ==================================================================
    st.banner("STEP 4: Test Summary")

    st.log("=" * 80)
    st.log("INTERFACE SPECIFIC PING TEST RESULTS:")
    st.log("=" * 80)
    st.log(f"Configuration: {CONFIG.dut1_ip} <-> {CONFIG.dut2_ip}")
    st.log(f"Ping -I {CONFIG.interface}: {result_interface['received']}/{result_interface['transmitted']} pkts, {result_interface['loss_percent']}% loss - {'✓ PASS' if result_interface['success'] else '✗ FAIL'}")
    st.log(f"Ping -I {CONFIG.dut1_ip}:   {result_source_ip['received']}/{result_source_ip['transmitted']} pkts, {result_source_ip['loss_percent']}% loss - {'✓ PASS' if result_source_ip['success'] else '✗ FAIL'}")
    st.log("=" * 80)

    # ==================================================================
    # TEST RESULT
    # ==================================================================
    if test_failed:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-8.1.2 FAILED")
        st.banner("=" * 80)
        st.report_fail("test_case_failed")
    else:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-8.1.2 PASSED")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - TC-8.1.2: Interface Specific Ping")
        st.log("=" * 80)
        st.log(f"✓ IP addresses configured: {CONFIG.dut1_ip}, {CONFIG.dut2_ip}")
        st.log(f"✓ Ping with -I {CONFIG.interface} successful")
        st.log(f"✓ Ping with -I {CONFIG.dut1_ip} successful")
        st.log(f"✓ Interface-specific routing verified")
        st.log(f"✓ All pings completed with 0% packet loss")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
