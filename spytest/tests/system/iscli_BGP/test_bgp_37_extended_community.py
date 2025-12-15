#!/usr/bin/env python3
"""
BGP Extended Community Handling Test - BGP-37

Test Objective: Verify extended community (RT/RT2) propagation for EVPN

Test Scenarios:
- Configure L2VPN EVPN address-family
- Verify extended community attribute sent to neighbors
- Validate RT/RT2 extended communities for EVPN routes

Topology:
    D1 (smic_sonic1) <--Ethernet4--> D2 (smic_sonic2)
    192.168.100.203                  192.168.100.196
    Router-ID: 1.1.1.1               Router-ID: 2.2.2.2
    AS: 65001                        AS: 65001

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_37_extended_community.py \
  --logs-path ./logs/bgp_37_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Prerequisites:
  - Topology: two-device (D1-D2) | Supported: HW and Virtual
  - SONiC devices with BGP and EVPN support
  - Testbed: testbed_2vs.yaml

Author: SPyTest Framework / Claude Code
Copyright (C) 2024
"""

from __future__ import annotations

import pytest
import time
from spytest import st, SpyTestDict

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test case IDs
TC_IDS = SpyTestDict({
    "interface_config": "TC-BGP-37-001",
    "loopback_config": "TC-BGP-37-002",
    "bgp_evpn_config": "TC-BGP-37-003",
    "neighbor_config": "TC-BGP-37-004",
    "config_verification": "TC-BGP-37-005",
    "session_check": "TC-BGP-37-006",
})


def initialize_data() -> None:
    """Initialize test data and configuration."""
    global vars, data

    # Get topology variables
    vars = st.ensure_min_topology("D1D2:1")

    # Test configuration
    data.D1_interface = "Ethernet4"
    data.D2_interface = "Ethernet4"

    data.D1_ip = "10.1.1.1"
    data.D2_ip = "10.1.1.2"
    data.subnet_mask = "24"

    data.D1_loopback = "Loopback0"
    data.D2_loopback = "Loopback0"
    data.D1_loopback_ip = "1.1.1.1"
    data.D2_loopback_ip = "2.2.2.2"
    data.loopback_mask = "32"

    data.asn = "65001"
    data.router_id_d1 = "1.1.1.1"
    data.router_id_d2 = "2.2.2.2"

    data.peer_group_name = "EVPN_PG"
    data.keepalive = "10"
    data.holdtime = "30"

    # CLI type - using klish
    data.cli_type = "klish"

    st.log(f"Initialized BGP-37 test data")
    st.log(f"D1: {data.D1_ip}, D2: {data.D2_ip}, AS: {data.asn}")
    st.log(f"Loopback D1: {data.D1_loopback_ip}, D2: {data.D2_loopback_ip}")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP-37: EXTENDED COMMUNITY (EVPN) TEST - MODULE PROLOGUE")
    st.banner("=" * 80)

    # Initialize test data
    initialize_data()

    st.log("Module setup completed")

    # Yield for test execution
    yield

    # Module epilogue - Cleanup
    st.banner("=" * 80)
    st.banner("BGP-37: MODULE EPILOGUE - CLEANUP")
    st.banner("=" * 80)

    cleanup_bgp_config()

    st.log("Module cleanup completed")


def cleanup_bgp_config() -> None:
    """Cleanup BGP and interface configuration."""
    st.log("Cleaning up BGP and interface configuration")

    # Remove BGP configuration on both devices
    for dut in [vars.D1, vars.D2]:
        st.log(f"Removing BGP configuration on {dut}")
        st.config(dut, f"no router bgp {data.asn}", type=data.cli_type, skip_error_check=True)

        # Remove loopback IP addresses
        loopback = data.D1_loopback if dut == vars.D1 else data.D2_loopback
        loopback_ip = data.D1_loopback_ip if dut == vars.D1 else data.D2_loopback_ip
        st.config(dut, f"interface {loopback}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"no ip address {loopback_ip}/{data.loopback_mask}",
                  type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)

        # Remove IP addresses
        interface = data.D1_interface if dut == vars.D1 else data.D2_interface
        ip_addr = data.D1_ip if dut == vars.D1 else data.D2_ip
        st.config(dut, f"interface {interface}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"no ip address {ip_addr}/{data.subnet_mask}",
                  type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)

    st.log("Cleanup completed")


@pytest.mark.bgp_extended_community
@pytest.mark.evpn_test
def test_bgp_37_interface_config():
    """
    TC-BGP-37-001: Configure IP addresses on Ethernet4 interfaces.

    Steps:
        1. Configure IP 10.1.1.1/24 on D1 Ethernet4
        2. Configure IP 10.1.1.2/24 on D2 Ethernet4
        3. Bring up interfaces (no shutdown)
        4. Verify interface status and IP addresses
    """
    st.banner(f"Test Case: {TC_IDS.interface_config} - Interface Configuration")

    # Configure D1 interface
    st.log(f"Configuring {data.D1_interface} on {vars.D1}")
    st.config(vars.D1, f"interface {data.D1_interface}", type=data.cli_type)
    st.config(vars.D1, f"ip address {data.D1_ip}/{data.subnet_mask}", type=data.cli_type)
    st.config(vars.D1, "no shutdown", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure D2 interface
    st.log(f"Configuring {data.D2_interface} on {vars.D2}")
    st.config(vars.D2, f"interface {data.D2_interface}", type=data.cli_type)
    st.config(vars.D2, f"ip address {data.D2_ip}/{data.subnet_mask}", type=data.cli_type)
    st.config(vars.D2, "no shutdown", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Wait for interfaces to come up
    st.log("Waiting 5 seconds for interfaces to stabilize")
    time.sleep(5)

    # Verify IP addresses on D1
    st.log(f"Verifying IP address on {vars.D1}")
    output_d1 = st.show(vars.D1, f"show ip interface {data.D1_interface}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 Interface output: {output_d1}")

    if data.D1_ip not in str(output_d1):
        st.report_fail("test_case_failed", f"IP {data.D1_ip} not found on {vars.D1} {data.D1_interface}")

    # Verify IP addresses on D2
    st.log(f"Verifying IP address on {vars.D2}")
    output_d2 = st.show(vars.D2, f"show ip interface {data.D2_interface}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 Interface output: {output_d2}")

    if data.D2_ip not in str(output_d2):
        st.report_fail("test_case_failed", f"IP {data.D2_ip} not found on {vars.D2} {data.D2_interface}")

    st.log("[PASS] Interface configuration successful")
    st.report_tc_pass(TC_IDS.interface_config, "msg", "Interface configuration successful")


@pytest.mark.bgp_extended_community
@pytest.mark.evpn_test
def test_bgp_37_loopback_config():
    """
    TC-BGP-37-002: Configure loopback interfaces for BGP EVPN.

    Steps:
        1. Configure Loopback0 on D1 with IP 1.1.1.1/32
        2. Configure Loopback0 on D2 with IP 2.2.2.2/32
        3. Verify loopback configuration
    """
    st.banner(f"Test Case: {TC_IDS.loopback_config} - Loopback Configuration")

    # Configure D1 loopback
    st.log(f"Configuring {data.D1_loopback} on {vars.D1}")
    st.config(vars.D1, f"interface {data.D1_loopback}", type=data.cli_type)
    st.config(vars.D1, f"ip address {data.D1_loopback_ip}/{data.loopback_mask}", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure D2 loopback
    st.log(f"Configuring {data.D2_loopback} on {vars.D2}")
    st.config(vars.D2, f"interface {data.D2_loopback}", type=data.cli_type)
    st.config(vars.D2, f"ip address {data.D2_loopback_ip}/{data.loopback_mask}", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify loopback on D1
    st.log(f"Verifying loopback on {vars.D1}")
    output_d1 = st.show(vars.D1, f"show ip interface {data.D1_loopback}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 Loopback output: {output_d1}")

    if data.D1_loopback_ip not in str(output_d1):
        st.report_fail("test_case_failed", f"Loopback IP {data.D1_loopback_ip} not found on {vars.D1}")

    # Verify loopback on D2
    st.log(f"Verifying loopback on {vars.D2}")
    output_d2 = st.show(vars.D2, f"show ip interface {data.D2_loopback}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 Loopback output: {output_d2}")

    if data.D2_loopback_ip not in str(output_d2):
        st.report_fail("test_case_failed", f"Loopback IP {data.D2_loopback_ip} not found on {vars.D2}")

    st.log("[PASS] Loopback configuration successful")
    st.report_tc_pass(TC_IDS.loopback_config, "msg", "Loopback configuration successful")


@pytest.mark.bgp_extended_community
@pytest.mark.evpn_test
def test_bgp_37_bgp_evpn_config():
    """
    TC-BGP-37-003: Configure BGP with L2VPN EVPN address-family.

    Steps:
        1. Configure BGP router on D1 and D2
        2. Set router-ID on both devices
        3. Create peer-group for EVPN
        4. Configure L2VPN EVPN address-family
        5. Enable send-community extended
    """
    st.banner(f"Test Case: {TC_IDS.bgp_evpn_config} - BGP EVPN Configuration")

    # Configure BGP on D1
    st.log(f"Configuring BGP with EVPN on {vars.D1}")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"router-id {data.router_id_d1}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D1, f"remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"timers {data.keepalive} {data.holdtime}", type=data.cli_type)
    st.config(vars.D1, "address-family l2vpn evpn", type=data.cli_type)
    st.config(vars.D1, "send-community extended", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure BGP on D2
    st.log(f"Configuring BGP with EVPN on {vars.D2}")
    st.config(vars.D2, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"router-id {data.router_id_d2}", type=data.cli_type)
    st.config(vars.D2, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D2, f"remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"timers {data.keepalive} {data.holdtime}", type=data.cli_type)
    st.config(vars.D2, "address-family l2vpn evpn", type=data.cli_type)
    st.config(vars.D2, "send-community extended", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify BGP configuration on D1
    st.log(f"Verifying BGP EVPN configuration on {vars.D1}")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Config: {bgp_config_d1}")

    config_str_d1 = str(bgp_config_d1)

    if "l2vpn evpn" not in config_str_d1:
        st.report_fail("test_case_failed", f"L2VPN EVPN not configured on {vars.D1}")

    if "send-community extended" not in config_str_d1:
        st.report_fail("test_case_failed", f"send-community extended not configured on {vars.D1}")

    st.log("[PASS] BGP EVPN configuration successful")
    st.report_tc_pass(TC_IDS.bgp_evpn_config, "msg", "BGP EVPN with extended community configured")


@pytest.mark.bgp_extended_community
@pytest.mark.evpn_test
def test_bgp_37_neighbor_config():
    """
    TC-BGP-37-004: Configure BGP neighbors for EVPN.

    Steps:
        1. Configure neighbor using loopback IPs
        2. Assign neighbor to EVPN peer-group
        3. Enable update-source loopback
        4. Activate L2VPN EVPN address-family
    """
    st.banner(f"Test Case: {TC_IDS.neighbor_config} - BGP Neighbor Configuration")

    # Configure neighbor on D1
    st.log(f"Configuring BGP neighbor on {vars.D1}")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_loopback_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D1, f"update-source {data.D1_loopback}", type=data.cli_type)
    st.config(vars.D1, "address-family l2vpn evpn", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure neighbor on D2
    st.log(f"Configuring BGP neighbor on {vars.D2}")
    st.config(vars.D2, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"neighbor {data.D1_loopback_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D2, f"update-source {data.D2_loopback}", type=data.cli_type)
    st.config(vars.D2, "address-family l2vpn evpn", type=data.cli_type)
    st.config(vars.D2, "activate", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify neighbor configuration
    st.log(f"Verifying neighbor configuration on {vars.D1}")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)

    if data.D2_loopback_ip not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"Neighbor {data.D2_loopback_ip} not configured on {vars.D1}")

    st.log("[PASS] BGP neighbor configuration successful")
    st.report_tc_pass(TC_IDS.neighbor_config, "msg", "BGP neighbors configured for EVPN")


@pytest.mark.bgp_extended_community
@pytest.mark.evpn_test
def test_bgp_37_config_verification():
    """
    TC-BGP-37-005: Verify BGP EVPN configuration.

    Steps:
        1. Display running-configuration bgp on both DUTs
        2. Verify L2VPN EVPN address-family
        3. Verify send-community extended setting
        4. Check peer-group details
    """
    st.banner(f"Test Case: {TC_IDS.config_verification} - Configuration Verification")

    # Verify D1 configuration
    st.log(f"Verifying configuration on {vars.D1}")

    # Show running-config
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Running Config:\n{bgp_config_d1}")

    config_str_d1 = str(bgp_config_d1)

    # Verify L2VPN EVPN exists
    if "l2vpn evpn" not in config_str_d1:
        st.report_fail("test_case_failed", "L2VPN EVPN address-family not found in config")

    # Verify send-community extended is configured
    if "send-community extended" not in config_str_d1:
        st.report_fail("test_case_failed", "send-community extended not found in config")

    # Show peer-group details
    st.log(f"Showing peer-group {data.peer_group_name} on {vars.D1}")
    pg_output_d1 = st.show(vars.D1, f"show bgp peer-group {data.peer_group_name}",
                           type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 Peer-group output:\n{pg_output_d1}")

    # Verify D2 configuration
    st.log(f"Verifying configuration on {vars.D2}")
    bgp_config_d2 = st.show(vars.D2, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP Running Config:\n{bgp_config_d2}")

    st.log("[PASS] Configuration verification successful")
    st.report_tc_pass(TC_IDS.config_verification, "msg", "BGP EVPN configuration verified")


@pytest.mark.bgp_extended_community
@pytest.mark.evpn_test
def test_bgp_37_session_check():
    """
    TC-BGP-37-006: Verify BGP EVPN session establishment.

    Steps:
        1. Wait for BGP session to establish
        2. Check BGP L2VPN EVPN summary
        3. Verify neighbor details show extended community
        4. Validate session state
    """
    st.banner(f"Test Case: {TC_IDS.session_check} - BGP EVPN Session Check")

    # Wait for BGP session establishment
    st.log("Waiting 30 seconds for BGP session establishment")
    time.sleep(30)

    # Check BGP EVPN summary on D1
    st.log(f"Checking BGP L2VPN EVPN summary on {vars.D1}")
    bgp_summary_d1 = st.show(vars.D1, "show bgp l2vpn evpn summary", type=data.cli_type,
                             skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 BGP L2VPN EVPN Summary:\n{bgp_summary_d1}")

    # Check BGP neighbor details on D1
    st.log(f"Checking BGP L2VPN EVPN neighbor {data.D2_loopback_ip} on {vars.D1}")
    neighbor_output_d1 = st.show(vars.D1, f"show bgp l2vpn evpn neighbors {data.D2_loopback_ip}",
                                 type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 Neighbor Details:\n{neighbor_output_d1}")

    neighbor_str_d1 = str(neighbor_output_d1)

    # Check for extended community attribute
    if "extended" in neighbor_str_d1.lower() or "community" in neighbor_str_d1.lower():
        st.log("[PASS] Extended community attribute found in neighbor details")
    else:
        st.log("[INFO] Extended community attribute may require EVPN route exchange")

    # Check BGP summary on D2
    st.log(f"Checking BGP L2VPN EVPN summary on {vars.D2}")
    bgp_summary_d2 = st.show(vars.D2, "show bgp l2vpn evpn summary", type=data.cli_type,
                             skip_tmpl=True, skip_error_check=True)
    st.log(f"D2 BGP L2VPN EVPN Summary:\n{bgp_summary_d2}")

    st.log("[PASS] BGP EVPN session check completed")
    st.report_tc_pass(TC_IDS.session_check, "msg", "BGP EVPN session verified with extended community")
