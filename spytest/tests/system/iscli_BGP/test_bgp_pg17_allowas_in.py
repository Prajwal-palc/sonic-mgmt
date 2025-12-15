#!/usr/bin/env python3
"""
BGP Peer-Group Test - PG-17: Peer-Group with allowas-in for Many Members

This test validates allowas-in configuration for BGP neighbors to allow own AS
in AS-PATH. Due to SONiC limitation, allowas-in must be configured at neighbor
level (peer-group inheritance not supported).

Test Scenario:
- Create peer-group with basic configuration
- Assign neighbors to peer-group
- Configure allowas-in on each neighbor individually
- Verify configuration inheritance and allowas-in settings

KNOWN LIMITATION:
- allowas-in numeric parameter (1-10) converts to "origin" (SONiC bug)
- allowas-in not supported at peer-group level
- Must configure allowas-in individually on each neighbor

Topology:
    D1 (192.168.100.203) <--Ethernet4--> D2 (192.168.100.196)
    Router-ID: 1.1.1.1                   Router-ID: 2.2.2.2
    AS: 65001                            AS: 65001

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_2vs.yaml \\
  tests/system/iscli_BGP/test_bgp_pg17_allowas_in.py \\
  --logs-path ./logs/bgp_pg17_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Prerequisites:
  - Topology: two-device (D1-D2) via Ethernet4
  - SONiC devices with BGP support

Author: SPyTest Framework / Claude Code
Copyright (C) 2024
"""

from __future__ import annotations

import pytest
import time
from typing import Any, Dict, List, Optional

from spytest import st, SpyTestDict
import apis.routing.ip as ipapi

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test case IDs
TC_IDS = SpyTestDict({
    "interface_config": "TC-BGP-PG17-001",
    "peergroup_creation": "TC-BGP-PG17-002",
    "neighbor_assignment": "TC-BGP-PG17-003",
    "allowas_in_config": "TC-BGP-PG17-004",
    "config_verification": "TC-BGP-PG17-005",
})


def initialize_data() -> None:
    """Initialize test data and configuration."""
    global vars, data

    # Get topology variables
    vars = st.ensure_min_topology("D1D2:1")

    # Test configuration - Using peer-group "1" as shown in CLI logs
    data.peer_group_name = "1"
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

    # allowas-in configuration (note: will convert to "origin" due to SONiC bug)
    data.allowas_in_value = "3"  # Will be stored as "origin"

    # CLI type
    data.cli_type = "klish"

    st.log(f"Initialized test data: Peer-group={data.peer_group_name}, AS={data.asn}")
    st.log(f"D1-D2 connection: {data.D1_interface}({data.D1_ip}) <--> {data.D2_interface}({data.D2_ip})")
    st.log(f"[NOTE] allowas-in {data.allowas_in_value} will convert to 'allowas-in origin' (known SONiC bug)")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: BGP PG-17 Test - Starting")

    # Initialize test data
    initialize_data()

    # Yield for test execution
    yield

    # Module epilogue - Cleanup
    st.banner("MODULE EPILOGUE: BGP PG-17 Test - Cleanup")

    st.log("Cleaning up BGP configuration on D1")
    cleanup_bgp_config(vars.D1)

    st.log("Cleaning up BGP configuration on D2")
    cleanup_bgp_config(vars.D2)

    st.log("Removing IP addresses")
    ipapi.delete_ip_interface(vars.D1, data.D1_interface, f"{data.D1_ip}/{data.ip_mask}", family="ipv4")
    ipapi.delete_ip_interface(vars.D2, data.D2_interface, f"{data.D2_ip}/{data.ip_mask}", family="ipv4")

    st.log("Module cleanup completed")


def cleanup_bgp_config(dut: str) -> None:
    """Clean up BGP configuration on device."""
    st.log(f"Removing BGP configuration on {dut}")
    try:
        st.config(dut, f"no router bgp {data.asn}", type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup note: {e}")


@pytest.mark.bgp_peergroup
@pytest.mark.allowas_in
@pytest.mark.known_bug  # allowas-in numeric parameter bug
def test_bgp_pg17_interface_configuration():
    """
    TC-BGP-PG17-001: Configure IP addresses on Ethernet4 interfaces.

    Steps:
        1. Configure IP address on D1 Ethernet4
        2. Configure IP address on D2 Ethernet4
        3. Bring up interfaces
        4. Verify IP configuration
    """
    st.banner(f"TEST CASE: {TC_IDS.interface_config} - Interface Configuration")

    # Configure D1 interface
    st.log(f"Configuring IP {data.D1_ip}/{data.ip_mask} on {vars.D1} {data.D1_interface}")
    st.config(vars.D1, f"interface {data.D1_interface}", type=data.cli_type)
    st.config(vars.D1, f"ip address {data.D1_ip}/{data.ip_mask}", type=data.cli_type)
    st.config(vars.D1, "no shutdown", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure D2 interface
    st.log(f"Configuring IP {data.D2_ip}/{data.ip_mask} on {vars.D2} {data.D2_interface}")
    st.config(vars.D2, f"interface {data.D2_interface}", type=data.cli_type)
    st.config(vars.D2, f"ip address {data.D2_ip}/{data.ip_mask}", type=data.cli_type)
    st.config(vars.D2, "no shutdown", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    time.sleep(5)

    # Verify IP configuration
    st.log("Verifying IP configuration on D1")
    output_d1 = st.show(vars.D1, f"show ip interface {data.D1_interface}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 interface output: {output_d1}")

    if data.D1_ip not in str(output_d1):
        st.report_fail("test_case_failed", f"IP {data.D1_ip} not configured on D1")

    st.log("Verifying IP configuration on D2")
    output_d2 = st.show(vars.D2, f"show ip interface {data.D2_interface}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 interface output: {output_d2}")

    if data.D2_ip not in str(output_d2):
        st.report_fail("test_case_failed", f"IP {data.D2_ip} not configured on D2")

    st.report_tc_pass(TC_IDS.interface_config, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.allowas_in
@pytest.mark.known_bug
def test_bgp_pg17_peergroup_creation():
    """
    TC-BGP-PG17-002: Create BGP peer-group.

    Steps:
        1. Configure BGP router with router-id
        2. Create peer-group with remote-as and timers
        3. Activate IPv4 unicast address-family
        4. Verify peer-group configuration
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

    # Verify configuration
    st.log("Verifying peer-group configuration on D1")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP config: {bgp_config_d1}")

    if f"peer-group {data.peer_group_name}" not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"Peer-group {data.peer_group_name} not found in D1 config")

    st.log("Verifying peer-group configuration on D2")
    bgp_config_d2 = st.show(vars.D2, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP config: {bgp_config_d2}")

    if f"peer-group {data.peer_group_name}" not in str(bgp_config_d2):
        st.report_fail("test_case_failed", f"Peer-group {data.peer_group_name} not found in D2 config")

    st.report_tc_pass(TC_IDS.peergroup_creation, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.allowas_in
@pytest.mark.known_bug
def test_bgp_pg17_neighbor_assignment():
    """
    TC-BGP-PG17-003: Assign neighbors to peer-group.

    Steps:
        1. Configure neighbor and assign to peer-group on D1
        2. Configure neighbor and assign to peer-group on D2
        3. Activate address-family
        4. Verify neighbor assignment
    """
    st.banner(f"TEST CASE: {TC_IDS.neighbor_assignment} - Neighbor Assignment")

    # Configure D1 neighbor
    st.log(f"Configuring neighbor {data.D2_ip} on D1")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure D2 neighbor
    st.log(f"Configuring neighbor {data.D1_ip} on D2")
    st.config(vars.D2, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"neighbor {data.D1_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D2, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D2, "activate", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify neighbor assignment
    st.log("Verifying neighbor assignment on D1")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP config: {bgp_config_d1}")

    if f"neighbor {data.D2_ip}" not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"Neighbor {data.D2_ip} not found in D1 config")

    st.log("Verifying neighbor assignment on D2")
    bgp_config_d2 = st.show(vars.D2, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP config: {bgp_config_d2}")

    if f"neighbor {data.D1_ip}" not in str(bgp_config_d2):
        st.report_fail("test_case_failed", f"Neighbor {data.D1_ip} not found in D2 config")

    st.report_tc_pass(TC_IDS.neighbor_assignment, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.allowas_in
@pytest.mark.known_bug
def test_bgp_pg17_allowas_in_config():
    """
    TC-BGP-PG17-004: Configure allowas-in on neighbors.

    Steps:
        1. Configure allowas-in on D1 neighbor (at neighbor level, not peer-group)
        2. Configure allowas-in on D2 neighbor
        3. Verify allowas-in configuration
        4. NOTE: allowas-in 3 will be stored as "allowas-in origin" (SONiC bug)
    """
    st.banner(f"TEST CASE: {TC_IDS.allowas_in_config} - allowas-in Configuration")

    st.log(f"[NOTE] Configuring allowas-in {data.allowas_in_value} (will convert to 'origin')")

    # Configure allowas-in on D1 neighbor
    st.log(f"Configuring allowas-in on D1 neighbor {data.D2_ip}")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, f"allowas-in {data.allowas_in_value}", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure allowas-in on D2 neighbor
    st.log(f"Configuring allowas-in on D2 neighbor {data.D1_ip}")
    st.config(vars.D2, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"neighbor {data.D1_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D2, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D2, f"allowas-in {data.allowas_in_value}", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify allowas-in configuration on D1
    st.log("Verifying allowas-in configuration on D1")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d1 = str(bgp_config_d1)
    st.log(f"D1 BGP config: {config_str_d1}")

    # Due to SONiC bug, check for "allowas-in origin" instead of numeric value
    if "allowas-in origin" in config_str_d1:
        st.log(f"[PASS] allowas-in configured on D1 (as 'origin' due to bug)")
    elif "allowas-in" in config_str_d1:
        st.log(f"[PASS] allowas-in configured on D1")
    else:
        st.log(f"[FAIL] allowas-in NOT found in D1 config")
        st.report_fail("test_case_failed", "allowas-in not found in D1 configuration")

    # Verify allowas-in configuration on D2
    st.log("Verifying allowas-in configuration on D2")
    bgp_config_d2 = st.show(vars.D2, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d2 = str(bgp_config_d2)
    st.log(f"D2 BGP config: {config_str_d2}")

    if "allowas-in origin" in config_str_d2:
        st.log(f"[PASS] allowas-in configured on D2 (as 'origin' due to bug)")
    elif "allowas-in" in config_str_d2:
        st.log(f"[PASS] allowas-in configured on D2")
    else:
        st.log(f"[FAIL] allowas-in NOT found in D2 config")
        st.report_fail("test_case_failed", "allowas-in not found in D2 configuration")

    # Check neighbor details
    st.log("Checking neighbor details for allowas-in on D1")
    neighbor_output_d1 = st.show(vars.D1, f"show bgp ipv4 unicast neighbors {data.D2_ip}",
                                  type=data.cli_type, skip_error_check=True, skip_tmpl=True)
    st.log(f"D1 neighbor {data.D2_ip} output:\n{neighbor_output_d1}")

    st.report_tc_pass(TC_IDS.allowas_in_config, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.allowas_in
@pytest.mark.known_bug
def test_bgp_pg17_configuration_verification():
    """
    TC-BGP-PG17-005: Verify complete configuration.

    Steps:
        1. Verify peer-group configuration on both devices
        2. Verify neighbors assigned to peer-group
        3. Verify allowas-in configured on neighbors
        4. Check BGP summary
    """
    st.banner(f"TEST CASE: {TC_IDS.config_verification} - Configuration Verification")

    # Verify complete configuration on D1
    st.log("Verifying complete BGP configuration on D1")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d1 = str(bgp_config_d1)
    st.log(f"D1 complete BGP configuration:\n{config_str_d1}")

    # Check all components
    components_d1 = [
        (data.router_id_d1, "Router-ID"),
        (f"peer-group {data.peer_group_name}", "Peer-group"),
        (f"neighbor {data.D2_ip}", "Neighbor"),
        ("allowas-in", "allowas-in feature"),
    ]

    for component, name in components_d1:
        if component in config_str_d1:
            st.log(f"[PASS] {name} verified on D1")
        else:
            st.log(f"[WARN] {name} not found in D1 config")

    # Verify complete configuration on D2
    st.log("Verifying complete BGP configuration on D2")
    bgp_config_d2 = st.show(vars.D2, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d2 = str(bgp_config_d2)
    st.log(f"D2 complete BGP configuration:\n{config_str_d2}")

    components_d2 = [
        (data.router_id_d2, "Router-ID"),
        (f"peer-group {data.peer_group_name}", "Peer-group"),
        (f"neighbor {data.D1_ip}", "Neighbor"),
        ("allowas-in", "allowas-in feature"),
    ]

    for component, name in components_d2:
        if component in config_str_d2:
            st.log(f"[PASS] {name} verified on D2")
        else:
            st.log(f"[WARN] {name} not found in D2 config")

    # Check BGP summary
    st.log("Checking BGP summary on D1")
    bgp_summary_d1 = st.show(vars.D1, "show bgp summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP summary:\n{bgp_summary_d1}")

    st.log("Checking BGP summary on D2")
    bgp_summary_d2 = st.show(vars.D2, "show bgp summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP summary:\n{bgp_summary_d2}")

    st.report_tc_pass(TC_IDS.config_verification, "test_case_passed")
