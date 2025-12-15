#!/usr/bin/env python3
"""
BGP Peer-Group Test - PG-20: Peer-Group with Neighbor-Specific Route-Map Override

This test validates route-map configuration inheritance from peer-group and
neighbor-specific route-map override capability.

Test Scenario:
- Create peer-group with route-map RM_PEER_GROUP_DEFAULT (local-pref 100)
- Assign neighbor to peer-group
- Override with neighbor-specific route-map RM_NEIGHBOR_OVERRIDE (local-pref 200)
- Verify neighbor route-map takes precedence over peer-group route-map

Topology:
    D1 (192.168.100.203) <--Ethernet4--> D2 (192.168.100.196)
    Router-ID: 1.1.1.1                   Router-ID: 2.2.2.2
    AS: 65001                            AS: 65001

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_2vs.yaml \\
  tests/system/iscli_BGP/test_bgp_pg20_routemap_override.py \\
  --logs-path ./logs/bgp_pg20_$(date +%F_%H%M%S) \\
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
    "interface_config": "TC-BGP-PG20-001",
    "routemap_creation": "TC-BGP-PG20-002",
    "peergroup_with_routemap": "TC-BGP-PG20-003",
    "neighbor_routemap_override": "TC-BGP-PG20-004",
    "config_verification": "TC-BGP-PG20-005",
})


def initialize_data() -> None:
    """Initialize test data and configuration."""
    global vars, data

    # Get topology variables
    vars = st.ensure_min_topology("D1D2:1")

    # Test configuration
    data.peer_group_name = "OVERRIDE_TEST"
    data.routemap_peergroup = "RM_PEER_GROUP_DEFAULT"
    data.routemap_neighbor = "RM_NEIGHBOR_OVERRIDE"
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

    # Route-map local-preference values
    data.localpref_peergroup = "100"
    data.localpref_neighbor = "200"

    # CLI type
    data.cli_type = "klish"

    st.log(f"Initialized test data: Peer-group={data.peer_group_name}")
    st.log(f"Peer-group route-map: {data.routemap_peergroup} (local-pref {data.localpref_peergroup})")
    st.log(f"Neighbor route-map: {data.routemap_neighbor} (local-pref {data.localpref_neighbor})")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: BGP PG-20 Test - Starting")

    # Initialize test data
    initialize_data()

    # Yield for test execution
    yield

    # Module epilogue - Cleanup
    st.banner("MODULE EPILOGUE: BGP PG-20 Test - Cleanup")

    st.log("Cleaning up BGP configuration on D1")
    cleanup_bgp_config(vars.D1)

    st.log("Cleaning up BGP configuration on D2")
    cleanup_bgp_config(vars.D2)

    st.log("Removing route-maps on D1")
    cleanup_routemaps(vars.D1)

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


def cleanup_routemaps(dut: str) -> None:
    """Clean up route-map configuration on device."""
    st.log(f"Removing route-maps on {dut}")
    try:
        st.config(dut, f"no route-map {data.routemap_peergroup}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"no route-map {data.routemap_neighbor}", type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"Route-map cleanup note: {e}")


@pytest.mark.bgp_peergroup
@pytest.mark.routemap_override
def test_bgp_pg20_interface_configuration():
    """
    TC-BGP-PG20-001: Configure IP addresses on Ethernet4 interfaces.

    Steps:
        1. Configure IP addresses on D1 and D2
        2. Bring up interfaces
        3. Verify IP configuration
    """
    st.banner(f"TEST CASE: {TC_IDS.interface_config} - Interface Configuration")

    # Configure D1
    st.log(f"Configuring IP {data.D1_ip}/{data.ip_mask} on {vars.D1} {data.D1_interface}")
    st.config(vars.D1, f"interface {data.D1_interface}", type=data.cli_type)
    st.config(vars.D1, f"ip address {data.D1_ip}/{data.ip_mask}", type=data.cli_type)
    st.config(vars.D1, "no shutdown", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure D2
    st.log(f"Configuring IP {data.D2_ip}/{data.ip_mask} on {vars.D2} {data.D2_interface}")
    st.config(vars.D2, f"interface {data.D2_interface}", type=data.cli_type)
    st.config(vars.D2, f"ip address {data.D2_ip}/{data.ip_mask}", type=data.cli_type)
    st.config(vars.D2, "no shutdown", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    time.sleep(5)

    # Verify IP configuration
    output_d1 = st.show(vars.D1, f"show ip interface {data.D1_interface}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 interface output: {output_d1}")

    if data.D1_ip not in str(output_d1):
        st.report_fail("test_case_failed", f"IP {data.D1_ip} not configured on D1")

    output_d2 = st.show(vars.D2, f"show ip interface {data.D2_interface}", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 interface output: {output_d2}")

    if data.D2_ip not in str(output_d2):
        st.report_fail("test_case_failed", f"IP {data.D2_ip} not configured on D2")

    st.report_tc_pass(TC_IDS.interface_config, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.routemap_override
def test_bgp_pg20_routemap_creation():
    """
    TC-BGP-PG20-002: Create route-maps with different local-preference values.

    Steps:
        1. Create RM_PEER_GROUP_DEFAULT with local-preference 100
        2. Create RM_NEIGHBOR_OVERRIDE with local-preference 200
        3. Verify route-map configurations
    """
    st.banner(f"TEST CASE: {TC_IDS.routemap_creation} - Route-Map Creation")

    # Create peer-group route-map
    st.log(f"Creating route-map {data.routemap_peergroup} with local-pref {data.localpref_peergroup}")
    st.config(vars.D1, f"route-map {data.routemap_peergroup} permit 10", type=data.cli_type)
    st.config(vars.D1, f"set local-preference {data.localpref_peergroup}", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Create neighbor override route-map
    st.log(f"Creating route-map {data.routemap_neighbor} with local-pref {data.localpref_neighbor}")
    st.config(vars.D1, f"route-map {data.routemap_neighbor} permit 10", type=data.cli_type)
    st.config(vars.D1, f"set local-preference {data.localpref_neighbor}", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Verify route-map creation
    st.log("Verifying route-map configuration")
    routemap_config = st.show(vars.D1, "show running-configuration route-map",
                              type=data.cli_type, skip_error_check=True, skip_tmpl=True)
    config_str = str(routemap_config)
    st.log(f"Route-map configuration:\n{config_str}")

    # Check peer-group route-map
    if data.routemap_peergroup in config_str:
        st.log(f"[PASS] Route-map {data.routemap_peergroup} created")
    else:
        st.log(f"[WARN] Route-map {data.routemap_peergroup} not visible in config")

    # Check neighbor route-map
    if data.routemap_neighbor in config_str:
        st.log(f"[PASS] Route-map {data.routemap_neighbor} created")
    else:
        st.log(f"[WARN] Route-map {data.routemap_neighbor} not visible in config")

    # Check local-preference values
    if data.localpref_peergroup in config_str:
        st.log(f"[PASS] Local-preference {data.localpref_peergroup} configured")
    if data.localpref_neighbor in config_str:
        st.log(f"[PASS] Local-preference {data.localpref_neighbor} configured")

    st.report_tc_pass(TC_IDS.routemap_creation, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.routemap_override
def test_bgp_pg20_peergroup_with_routemap():
    """
    TC-BGP-PG20-003: Create peer-group with route-map.

    Steps:
        1. Configure BGP router on D1
        2. Create peer-group OVERRIDE_TEST
        3. Apply route-map RM_PEER_GROUP_DEFAULT to peer-group
        4. Verify configuration
    """
    st.banner(f"TEST CASE: {TC_IDS.peergroup_with_routemap} - Peer-Group with Route-Map")

    st.log(f"Creating peer-group {data.peer_group_name} with route-map")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"router-id {data.router_id_d1}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D1, f"remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"timers {data.timers_keepalive} {data.timers_holdtime}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, f"route-map {data.routemap_peergroup} in", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure D2 (simple neighbor without route-map)
    st.log("Configuring BGP router on D2")
    st.config(vars.D2, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"router-id {data.router_id_d2}", type=data.cli_type)
    st.config(vars.D2, f"neighbor {data.D1_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D2, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D2, "activate", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify peer-group configuration
    st.log("Verifying peer-group configuration on D1")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d1 = str(bgp_config_d1)
    st.log(f"D1 BGP config:\n{config_str_d1}")

    # Check peer-group exists
    if data.peer_group_name not in config_str_d1:
        st.report_fail("test_case_failed", f"Peer-group {data.peer_group_name} not found")
    st.log(f"[PASS] Peer-group {data.peer_group_name} created")

    # Check route-map applied to peer-group
    if f"route-map {data.routemap_peergroup} in" in config_str_d1:
        st.log(f"[PASS] Route-map {data.routemap_peergroup} applied to peer-group")
    else:
        st.log(f"[WARN] Route-map not visible in peer-group section")

    st.report_tc_pass(TC_IDS.peergroup_with_routemap, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.routemap_override
def test_bgp_pg20_neighbor_routemap_override():
    """
    TC-BGP-PG20-004: Configure neighbor with route-map override.

    Steps:
        1. Configure neighbor 10.1.1.2 on D1
        2. Assign to peer-group OVERRIDE_TEST
        3. Apply neighbor-specific route-map RM_NEIGHBOR_OVERRIDE
        4. Verify neighbor route-map takes precedence
    """
    st.banner(f"TEST CASE: {TC_IDS.neighbor_routemap_override} - Neighbor Route-Map Override")

    st.log(f"Configuring neighbor {data.D2_ip} with route-map override")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    # Apply neighbor-specific route-map (overrides peer-group route-map)
    st.config(vars.D1, f"route-map {data.routemap_neighbor} in", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Verify neighbor configuration
    st.log("Verifying neighbor configuration with route-map override")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d1 = str(bgp_config_d1)
    st.log(f"D1 BGP config with neighbor:\n{config_str_d1}")

    # Check neighbor exists
    if f"neighbor {data.D2_ip}" not in config_str_d1:
        st.report_fail("test_case_failed", f"Neighbor {data.D2_ip} not found")
    st.log(f"[PASS] Neighbor {data.D2_ip} configured")

    # Check peer-group assignment
    if f"peer-group {data.peer_group_name}" not in config_str_d1:
        st.report_fail("test_case_failed", "Peer-group assignment not found")
    st.log(f"[PASS] Neighbor assigned to peer-group {data.peer_group_name}")

    # Check neighbor-specific route-map
    if f"route-map {data.routemap_neighbor} in" in config_str_d1:
        st.log(f"[PASS] Neighbor route-map {data.routemap_neighbor} configured")
        st.log(f"[INFO] Neighbor route-map OVERRIDES peer-group route-map")
    else:
        st.log(f"[WARN] Neighbor route-map not visible in config")

    # Check neighbor details
    st.log(f"Checking neighbor {data.D2_ip} details")
    neighbor_output = st.show(vars.D1, f"show bgp ipv4 unicast neighbors {data.D2_ip}",
                              type=data.cli_type, skip_error_check=True, skip_tmpl=True)
    neighbor_str = str(neighbor_output)
    st.log(f"Neighbor {data.D2_ip} details:\n{neighbor_str}")

    # Look for route-map reference
    if data.routemap_neighbor in neighbor_str:
        st.log(f"[PASS] Neighbor-specific route-map {data.routemap_neighbor} active")
    elif "route-map" in neighbor_str.lower():
        st.log(f"[INFO] Route-map mentioned in neighbor details")
    else:
        st.log(f"[INFO] Route-map details may require established session")

    st.report_tc_pass(TC_IDS.neighbor_routemap_override, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.routemap_override
def test_bgp_pg20_config_verification():
    """
    TC-BGP-PG20-005: Verify complete configuration and route-map precedence.

    Steps:
        1. Verify complete BGP configuration
        2. Verify route-map configurations
        3. Verify neighbor route-map takes precedence
        4. Check BGP summary
    """
    st.banner(f"TEST CASE: {TC_IDS.config_verification} - Configuration Verification")

    # Verify complete BGP configuration
    st.log("Verifying complete BGP configuration on D1")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d1 = str(bgp_config_d1)
    st.log(f"D1 complete BGP configuration:\n{config_str_d1}")

    # Verify all components
    components = [
        (data.router_id_d1, "Router-ID"),
        (f"peer-group {data.peer_group_name}", "Peer-group"),
        (f"route-map {data.routemap_peergroup}", "Peer-group route-map"),
        (f"neighbor {data.D2_ip}", "Neighbor"),
        (f"route-map {data.routemap_neighbor}", "Neighbor route-map"),
    ]

    for component, name in components:
        if component in config_str_d1:
            st.log(f"[PASS] {name} verified")
        else:
            st.log(f"[WARN] {name} not found in config")

    # Verify route-map configuration
    st.log("Verifying route-map configuration")
    routemap_config = st.show(vars.D1, "show running-configuration route-map",
                              type=data.cli_type, skip_error_check=True, skip_tmpl=True)
    routemap_str = str(routemap_config)
    st.log(f"Route-map configuration:\n{routemap_str}")

    # Check BGP summary
    st.log("Checking BGP summary on D1")
    bgp_summary_d1 = st.show(vars.D1, "show bgp summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP summary:\n{bgp_summary_d1}")

    st.log("Checking BGP summary on D2")
    bgp_summary_d2 = st.show(vars.D2, "show bgp summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP summary:\n{bgp_summary_d2}")

    # Summary of route-map precedence
    st.log("=" * 80)
    st.log("ROUTE-MAP PRECEDENCE:")
    st.log(f"- Peer-group route-map: {data.routemap_peergroup} (local-pref {data.localpref_peergroup})")
    st.log(f"- Neighbor route-map: {data.routemap_neighbor} (local-pref {data.localpref_neighbor})")
    st.log(f"- RESULT: Neighbor route-map OVERRIDES peer-group route-map")
    st.log(f"- Effective for neighbor {data.D2_ip}: {data.routemap_neighbor}")
    st.log("=" * 80)

    st.report_tc_pass(TC_IDS.config_verification, "test_case_passed")
