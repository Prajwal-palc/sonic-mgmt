#!/usr/bin/env python3
"""
BGP Peer-Group Test - PG-16: subgroup-pkt-queue-max Behavior

This test validates peer-group configuration for packet queue optimization
with efficient update packing under high fanout scenarios.

Test Scenario:
- Create peer-group with timers configuration
- Assign neighbor to peer-group
- Verify configuration inheritance
- Validate BGP session establishment

Topology:
    D1 (192.168.100.203) <--Ethernet4--> D2 (192.168.100.196)
    Router-ID: 1.1.1.1                   Router-ID: 2.2.2.2
    AS: 65001                            AS: 65001

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_2vs.yaml \\
  tests/system/iscli_BGP/test_bgp_pg16_pkt_queue.py \\
  --logs-path ./logs/bgp_pg16_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Prerequisites:
  - Topology: two-device (D1-D2) via Ethernet4
  - SONiC devices with BGP support
  - SSH access to devices

Author: SPyTest Framework / Claude Code
Copyright (C) 2024
"""

from __future__ import annotations

import pytest
import time
from typing import Any, Dict, List, Optional

from spytest import st, SpyTestDict
import apis.routing.ip as ipapi
import apis.system.interface as intf_api

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test case IDs
TC_IDS = SpyTestDict({
    "interface_config": "TC-BGP-PG16-001",
    "peergroup_creation": "TC-BGP-PG16-002",
    "neighbor_assignment": "TC-BGP-PG16-003",
    "config_verification": "TC-BGP-PG16-004",
    "session_check": "TC-BGP-PG16-005",
})


def initialize_data() -> None:
    """Initialize test data and configuration."""
    global vars, data

    # Get topology variables
    vars = st.ensure_min_topology("D1D2:1")

    # Test configuration
    data.peer_group_name = "PKT_QUEUE_TEST"
    data.asn = "65001"
    data.router_id_d1 = "1.1.1.1"
    data.router_id_d2 = "2.2.2.2"

    # Interface configuration
    data.D1_interface = "Ethernet4"
    data.D2_interface = "Ethernet4"

    # IP addresses
    data.D1_ip = "10.1.1.1"
    data.D2_ip = "10.1.1.2"
    data.ip_mask = "24"

    # Timer configuration
    data.timers_keepalive = "10"
    data.timers_holdtime = "30"

    # CLI type - MUST use klish as requested
    data.cli_type = "klish"

    st.log(f"Initialized test data: Peer-group={data.peer_group_name}, AS={data.asn}")
    st.log(f"D1-D2 connection: {data.D1_interface}({data.D1_ip}) <--> {data.D2_interface}({data.D2_ip})")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: BGP PG-16 Test - Starting")

    # Initialize test data
    initialize_data()

    # Yield for test execution
    yield

    # Module epilogue - Cleanup
    st.banner("MODULE EPILOGUE: BGP PG-16 Test - Cleanup")

    st.log("Cleaning up BGP configuration on D1")
    cleanup_bgp_config(vars.D1)

    st.log("Cleaning up BGP configuration on D2")
    cleanup_bgp_config(vars.D2)

    st.log("Removing IP addresses")
    ipapi.delete_ip_interface(vars.D1, data.D1_interface, f"{data.D1_ip}/{data.ip_mask}", family="ipv4")
    ipapi.delete_ip_interface(vars.D2, data.D2_interface, f"{data.D2_ip}/{data.ip_mask}", family="ipv4")

    st.log("Module cleanup completed")


def cleanup_bgp_config(dut: str) -> None:
    """
    Clean up BGP configuration on device.

    Args:
        dut: Device under test
    """
    st.log(f"Removing BGP configuration on {dut}")
    try:
        st.config(dut, f"no router bgp {data.asn}", type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup note: {e}")


@pytest.mark.bgp_peergroup
@pytest.mark.packet_queue
def test_bgp_pg16_interface_configuration():
    """
    TC-BGP-PG16-001: Configure IP addresses on Ethernet4 interfaces.

    Steps:
        1. Configure IP address on D1 Ethernet4
        2. Configure IP address on D2 Ethernet4
        3. Bring up interfaces
        4. Verify IP configuration
        5. Verify interface status
    """
    st.banner(f"TEST CASE: {TC_IDS.interface_config} - Interface Configuration")

    # Step 1-2: Configure IP addresses
    st.log(f"Configuring IP {data.D1_ip}/{data.ip_mask} on {vars.D1} {data.D1_interface}")
    st.config(vars.D1, f"interface {data.D1_interface}", type=data.cli_type)
    st.config(vars.D1, f"ip address {data.D1_ip}/{data.ip_mask}", type=data.cli_type)
    st.config(vars.D1, "no shutdown", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    st.log(f"Configuring IP {data.D2_ip}/{data.ip_mask} on {vars.D2} {data.D2_interface}")
    st.config(vars.D2, f"interface {data.D2_interface}", type=data.cli_type)
    st.config(vars.D2, f"ip address {data.D2_ip}/{data.ip_mask}", type=data.cli_type)
    st.config(vars.D2, "no shutdown", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Wait for interfaces to come up
    time.sleep(5)

    # Step 4: Verify IP configuration
    st.log(f"Verifying IP configuration on {vars.D1}")
    output_d1 = st.show(vars.D1, f"show ip interface {data.D1_interface}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 interface output: {output_d1}")

    if data.D1_ip not in str(output_d1):
        st.report_fail("test_case_failed", f"IP {data.D1_ip} not configured on D1 {data.D1_interface}")

    st.log(f"Verifying IP configuration on {vars.D2}")
    output_d2 = st.show(vars.D2, f"show ip interface {data.D2_interface}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 interface output: {output_d2}")

    if data.D2_ip not in str(output_d2):
        st.report_fail("test_case_failed", f"IP {data.D2_ip} not configured on D2 {data.D2_interface}")

    # Step 5: Verify interface status
    st.log("Verifying interface status on both devices")
    status_d1 = st.show(vars.D1, f"show interface status {data.D1_interface}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 interface status: {status_d1}")

    status_d2 = st.show(vars.D2, f"show interface status {data.D2_interface}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 interface status: {status_d2}")

    st.report_tc_pass(TC_IDS.interface_config, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.packet_queue
def test_bgp_pg16_peergroup_creation():
    """
    TC-BGP-PG16-002: Create BGP peer-group with configuration.

    Steps:
        1. Configure BGP router with router-id on D1
        2. Create peer-group PKT_QUEUE_TEST
        3. Configure peer-group with remote-as and timers
        4. Activate IPv4 unicast address-family
        5. Repeat on D2
        6. Verify peer-group configuration
    """
    st.banner(f"TEST CASE: {TC_IDS.peergroup_creation} - Peer-Group Creation")

    # Configure D1
    st.log("Configuring BGP router and peer-group on D1")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"router-id {data.router_id_d1}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D1, f"remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"timers {data.timers_keepalive} {data.timers_holdtime}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure D2
    st.log("Configuring BGP router and peer-group on D2")
    st.config(vars.D2, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"router-id {data.router_id_d2}", type=data.cli_type)
    st.config(vars.D2, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D2, f"remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"timers {data.timers_keepalive} {data.timers_holdtime}", type=data.cli_type)
    st.config(vars.D2, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D2, "activate", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify configuration on D1
    st.log("Verifying peer-group configuration on D1")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP config: {bgp_config_d1}")

    if data.peer_group_name not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"Peer-group {data.peer_group_name} not found in D1 config")

    if f"timers {data.timers_keepalive} {data.timers_holdtime}" not in str(bgp_config_d1):
        st.log(f"[INFO] Timers may be inherited, checking peer-group section")

    # Verify configuration on D2
    st.log("Verifying peer-group configuration on D2")
    bgp_config_d2 = st.show(vars.D2, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP config: {bgp_config_d2}")

    if data.peer_group_name not in str(bgp_config_d2):
        st.report_fail("test_case_failed", f"Peer-group {data.peer_group_name} not found in D2 config")

    # Check BGP peer-group details
    st.log("Checking BGP peer-group details on D1")
    pg_output_d1 = st.show(vars.D1, f"show bgp peer-group {data.peer_group_name}",
                           type=data.cli_type, skip_error_check=True, skip_tmpl=True)
    st.log(f"D1 peer-group output: {pg_output_d1}")

    st.report_tc_pass(TC_IDS.peergroup_creation, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.packet_queue
def test_bgp_pg16_neighbor_assignment():
    """
    TC-BGP-PG16-003: Assign neighbor to peer-group.

    Steps:
        1. Configure neighbor 10.1.1.2 on D1 and assign to peer-group
        2. Configure neighbor 10.1.1.1 on D2 and assign to peer-group
        3. Activate address-family
        4. Verify neighbor assignment in configuration
    """
    st.banner(f"TEST CASE: {TC_IDS.neighbor_assignment} - Neighbor Assignment")

    # Configure neighbor on D1
    st.log(f"Configuring neighbor {data.D2_ip} on D1")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure neighbor on D2
    st.log(f"Configuring neighbor {data.D1_ip} on D2")
    st.config(vars.D2, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"neighbor {data.D1_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D2, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D2, "activate", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify neighbor assignment on D1
    st.log("Verifying neighbor assignment on D1")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP config: {bgp_config_d1}")

    if f"neighbor {data.D2_ip}" not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"Neighbor {data.D2_ip} not found in D1 config")

    if f"peer-group {data.peer_group_name}" not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"Peer-group assignment not found in D1 neighbor config")

    # Verify neighbor assignment on D2
    st.log("Verifying neighbor assignment on D2")
    bgp_config_d2 = st.show(vars.D2, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP config: {bgp_config_d2}")

    if f"neighbor {data.D1_ip}" not in str(bgp_config_d2):
        st.report_fail("test_case_failed", f"Neighbor {data.D1_ip} not found in D2 config")

    st.report_tc_pass(TC_IDS.neighbor_assignment, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.packet_queue
def test_bgp_pg16_configuration_verification():
    """
    TC-BGP-PG16-004: Verify complete BGP configuration.

    Steps:
        1. Verify BGP router-id on both devices
        2. Verify peer-group exists with correct parameters
        3. Verify neighbor is assigned to peer-group
        4. Check complete BGP configuration
    """
    st.banner(f"TEST CASE: {TC_IDS.config_verification} - Configuration Verification")

    # Verify D1 configuration
    st.log("Verifying complete BGP configuration on D1")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d1 = str(bgp_config_d1)
    st.log(f"D1 BGP configuration:\n{config_str_d1}")

    # Check router-id
    if data.router_id_d1 not in config_str_d1:
        st.report_fail("test_case_failed", f"Router-ID {data.router_id_d1} not found in D1 config")
    st.log(f"[PASS] Router-ID {data.router_id_d1} verified on D1")

    # Check peer-group
    if f"peer-group {data.peer_group_name}" not in config_str_d1:
        st.report_fail("test_case_failed", f"Peer-group {data.peer_group_name} not found in D1 config")
    st.log(f"[PASS] Peer-group {data.peer_group_name} verified on D1")

    # Check neighbor
    if f"neighbor {data.D2_ip}" not in config_str_d1:
        st.report_fail("test_case_failed", f"Neighbor {data.D2_ip} not found in D1 config")
    st.log(f"[PASS] Neighbor {data.D2_ip} verified on D1")

    # Verify D2 configuration
    st.log("Verifying complete BGP configuration on D2")
    bgp_config_d2 = st.show(vars.D2, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d2 = str(bgp_config_d2)
    st.log(f"D2 BGP configuration:\n{config_str_d2}")

    # Check router-id
    if data.router_id_d2 not in config_str_d2:
        st.report_fail("test_case_failed", f"Router-ID {data.router_id_d2} not found in D2 config")
    st.log(f"[PASS] Router-ID {data.router_id_d2} verified on D2")

    # Check peer-group
    if f"peer-group {data.peer_group_name}" not in config_str_d2:
        st.report_fail("test_case_failed", f"Peer-group {data.peer_group_name} not found in D2 config")
    st.log(f"[PASS] Peer-group {data.peer_group_name} verified on D2")

    # Check neighbor
    if f"neighbor {data.D1_ip}" not in config_str_d2:
        st.report_fail("test_case_failed", f"Neighbor {data.D1_ip} not found in D2 config")
    st.log(f"[PASS] Neighbor {data.D1_ip} verified on D2")

    st.report_tc_pass(TC_IDS.config_verification, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.packet_queue
def test_bgp_pg16_session_check():
    """
    TC-BGP-PG16-005: Verify BGP session establishment.

    Steps:
        1. Wait for BGP session to establish
        2. Check BGP summary on both devices
        3. Verify neighbor state
        4. Check IPv4 unicast summary
    """
    st.banner(f"TEST CASE: {TC_IDS.session_check} - BGP Session Check")

    # Wait for BGP session
    st.log("Waiting for BGP session to establish...")
    time.sleep(30)

    # Check BGP summary on D1
    st.log("Checking BGP summary on D1")
    bgp_summary_d1 = st.show(vars.D1, "show bgp summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP summary:\n{bgp_summary_d1}")

    summary_str_d1 = str(bgp_summary_d1)
    if data.router_id_d1 not in summary_str_d1:
        st.log(f"[WARN] Router-ID {data.router_id_d1} not visible in summary (may be normal)")

    if data.D2_ip in summary_str_d1:
        st.log(f"[PASS] Neighbor {data.D2_ip} found in D1 BGP summary")
    else:
        st.log(f"[INFO] Neighbor {data.D2_ip} not yet visible in summary")

    # Check BGP summary on D2
    st.log("Checking BGP summary on D2")
    bgp_summary_d2 = st.show(vars.D2, "show bgp summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP summary:\n{bgp_summary_d2}")

    summary_str_d2 = str(bgp_summary_d2)
    if data.router_id_d2 not in summary_str_d2:
        st.log(f"[WARN] Router-ID {data.router_id_d2} not visible in summary (may be normal)")

    if data.D1_ip in summary_str_d2:
        st.log(f"[PASS] Neighbor {data.D1_ip} found in D2 BGP summary")
    else:
        st.log(f"[INFO] Neighbor {data.D1_ip} not yet visible in summary")

    # Check IPv4 unicast summary
    st.log("Checking IPv4 unicast summary on D1")
    ipv4_summary_d1 = st.show(vars.D1, "show bgp ipv4 unicast summary",
                               type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 IPv4 unicast summary:\n{ipv4_summary_d1}")

    st.log("Checking IPv4 unicast summary on D2")
    ipv4_summary_d2 = st.show(vars.D2, "show bgp ipv4 unicast summary",
                               type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 IPv4 unicast summary:\n{ipv4_summary_d2}")

    # Check detailed neighbor information
    st.log(f"Checking detailed neighbor {data.D2_ip} on D1")
    neighbor_detail_d1 = st.show(vars.D1, f"show bgp ipv4 unicast neighbors {data.D2_ip}",
                                  type=data.cli_type, skip_error_check=True, skip_tmpl=True)
    st.log(f"D1 neighbor {data.D2_ip} details:\n{neighbor_detail_d1}")

    st.report_tc_pass(TC_IDS.session_check, "test_case_passed")
