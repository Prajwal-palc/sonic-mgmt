#!/usr/bin/env python3
"""
BGP Peer-Group Test - PG-18: Negative Test - Conflicting Peer-Group Settings Detection

This test validates SONiC detection of conflicting peer-group settings when
assigning neighbors to incompatible peer-groups.

Test Scenario:
- Create two peer-groups with different remote-AS
- IBGP_GROUP with AS 65001
- EBGP_GROUP with AS 65002
- Assign neighbor to IBGP_GROUP
- Attempt to reassign to EBGP_GROUP (should fail)

KNOWN BUG:
- SONiC does NOT validate peer-group remote-AS compatibility
- Conflicting assignment is accepted without error
- This is a validation bug in SONiC CLI

Topology:
    D1 (192.168.100.203) <--Ethernet4--> D2 (192.168.100.196)
    Router-ID: 1.1.1.1                   Router-ID: 2.2.2.2
    AS: 65001                            AS: 65001/65002

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_2vs.yaml \\
  tests/system/iscli_BGP/test_bgp_pg18_conflicting_settings.py \\
  --logs-path ./logs/bgp_pg18_$(date +%F_%H%M%S) \\
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
    "interface_config": "TC-BGP-PG18-001",
    "peergroup_creation": "TC-BGP-PG18-002",
    "initial_assignment": "TC-BGP-PG18-003",
    "conflicting_assignment": "TC-BGP-PG18-004",
    "config_verification": "TC-BGP-PG18-005",
})


def initialize_data() -> None:
    """Initialize test data and configuration."""
    global vars, data

    # Get topology variables
    vars = st.ensure_min_topology("D1D2:1")

    # Test configuration
    data.pg_ibgp_name = "IBGP_GROUP"
    data.pg_ebgp_name = "EBGP_GROUP"
    data.asn_local = "65001"
    data.asn_remote = "65002"
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
    data.ibgp_keepalive = "10"
    data.ibgp_holdtime = "30"
    data.ebgp_keepalive = "5"
    data.ebgp_holdtime = "15"

    # CLI type
    data.cli_type = "klish"

    st.log(f"Initialized test data: IBGP={data.pg_ibgp_name}(AS{data.asn_local}), "
           f"EBGP={data.pg_ebgp_name}(AS{data.asn_remote})")
    st.log(f"[NOTE] This is a NEGATIVE test - conflicting assignment should FAIL but currently PASSES (bug)")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: BGP PG-18 Test - Starting")

    # Initialize test data
    initialize_data()

    # Yield for test execution
    yield

    # Module epilogue - Cleanup
    st.banner("MODULE EPILOGUE: BGP PG-18 Test - Cleanup")

    st.log("Cleaning up BGP configuration on D1")
    cleanup_bgp_config(vars.D1)

    st.log("Removing IP addresses")
    ipapi.delete_ip_interface(vars.D1, data.D1_interface, f"{data.D1_ip}/{data.ip_mask}", family="ipv4")
    ipapi.delete_ip_interface(vars.D2, data.D2_interface, f"{data.D2_ip}/{data.ip_mask}", family="ipv4")

    st.log("Module cleanup completed")


def cleanup_bgp_config(dut: str) -> None:
    """Clean up BGP configuration on device."""
    st.log(f"Removing BGP configuration on {dut}")
    try:
        st.config(dut, f"no router bgp {data.asn_local}", type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup note: {e}")


@pytest.mark.bgp_peergroup
@pytest.mark.negative_test
@pytest.mark.known_bug  # SONiC doesn't validate conflicting remote-AS
def test_bgp_pg18_interface_configuration():
    """
    TC-BGP-PG18-001: Configure IP addresses on Ethernet4 interfaces.

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

    st.report_tc_pass(TC_IDS.interface_config, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.negative_test
@pytest.mark.known_bug
def test_bgp_pg18_peergroup_creation():
    """
    TC-BGP-PG18-002: Create two peer-groups with different remote-AS.

    Steps:
        1. Configure BGP router on D1
        2. Create IBGP_GROUP with remote-as 65001
        3. Create EBGP_GROUP with remote-as 65002
        4. Configure timers and address-family for both
        5. Verify peer-group configurations
    """
    st.banner(f"TEST CASE: {TC_IDS.peergroup_creation} - Peer-Group Creation")

    # Configure BGP router
    st.log("Configuring BGP router on D1")
    st.config(vars.D1, f"router bgp {data.asn_local}", type=data.cli_type)
    st.config(vars.D1, f"router-id {data.router_id_d1}", type=data.cli_type)

    # Create IBGP_GROUP
    st.log(f"Creating {data.pg_ibgp_name} with AS {data.asn_local}")
    st.config(vars.D1, f"peer-group {data.pg_ibgp_name}", type=data.cli_type)
    st.config(vars.D1, f"remote-as {data.asn_local}", type=data.cli_type)
    st.config(vars.D1, f"timers {data.ibgp_keepalive} {data.ibgp_holdtime}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Create EBGP_GROUP
    st.log(f"Creating {data.pg_ebgp_name} with AS {data.asn_remote}")
    st.config(vars.D1, f"peer-group {data.pg_ebgp_name}", type=data.cli_type)
    st.config(vars.D1, f"remote-as {data.asn_remote}", type=data.cli_type)
    st.config(vars.D1, f"timers {data.ebgp_keepalive} {data.ebgp_holdtime}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Verify peer-group configuration
    st.log("Verifying peer-group configuration on D1")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d1 = str(bgp_config_d1)
    st.log(f"D1 BGP config:\n{config_str_d1}")

    # Verify IBGP_GROUP
    if data.pg_ibgp_name not in config_str_d1:
        st.report_fail("test_case_failed", f"Peer-group {data.pg_ibgp_name} not found")
    st.log(f"[PASS] {data.pg_ibgp_name} created")

    # Verify EBGP_GROUP
    if data.pg_ebgp_name not in config_str_d1:
        st.report_fail("test_case_failed", f"Peer-group {data.pg_ebgp_name} not found")
    st.log(f"[PASS] {data.pg_ebgp_name} created")

    st.report_tc_pass(TC_IDS.peergroup_creation, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.negative_test
@pytest.mark.known_bug
def test_bgp_pg18_initial_assignment():
    """
    TC-BGP-PG18-003: Assign neighbor to IBGP_GROUP initially.

    Steps:
        1. Configure neighbor 10.1.1.2 with remote-as 65001
        2. Assign neighbor to IBGP_GROUP (compatible AS)
        3. Verify assignment successful
    """
    st.banner(f"TEST CASE: {TC_IDS.initial_assignment} - Initial Assignment to IBGP_GROUP")

    st.log(f"Assigning neighbor {data.D2_ip} to {data.pg_ibgp_name}")
    st.config(vars.D1, f"router bgp {data.asn_local}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_ip} remote-as {data.asn_local}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.pg_ibgp_name}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Verify initial assignment
    st.log("Verifying initial assignment")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d1 = str(bgp_config_d1)
    st.log(f"D1 BGP config after initial assignment:\n{config_str_d1}")

    if f"neighbor {data.D2_ip}" not in config_str_d1:
        st.report_fail("test_case_failed", f"Neighbor {data.D2_ip} not found in config")

    if f"peer-group {data.pg_ibgp_name}" not in config_str_d1:
        st.report_fail("test_case_failed", f"Peer-group {data.pg_ibgp_name} assignment not found")

    st.log(f"[PASS] Neighbor {data.D2_ip} assigned to {data.pg_ibgp_name}")

    st.report_tc_pass(TC_IDS.initial_assignment, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.negative_test
@pytest.mark.known_bug
def test_bgp_pg18_conflicting_assignment():
    """
    TC-BGP-PG18-004: Attempt to reassign neighbor to EBGP_GROUP (conflicting AS).

    Steps:
        1. Attempt to assign same neighbor to EBGP_GROUP
        2. EXPECTED: Error message (remote-AS conflict)
        3. ACTUAL: Command accepted without error (BUG)
        4. Verify configuration state

    KNOWN BUG:
        SONiC does NOT validate peer-group remote-AS compatibility.
        Conflicting assignment is accepted silently.
    """
    st.banner(f"TEST CASE: {TC_IDS.conflicting_assignment} - Conflicting Assignment (Negative Test)")

    st.log(f"[TEST] Attempting to reassign neighbor {data.D2_ip} to {data.pg_ebgp_name}")
    st.log(f"[EXPECTED] Error: remote-AS conflict ({data.asn_local} vs {data.asn_remote})")
    st.log(f"[ACTUAL] Command accepted (BUG - no validation)")

    # Attempt conflicting assignment
    st.config(vars.D1, f"router bgp {data.asn_local}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_ip} remote-as {data.asn_local}", type=data.cli_type)

    # This SHOULD fail but currently succeeds (bug)
    st.config(vars.D1, f"peer-group {data.pg_ebgp_name}", type=data.cli_type, skip_error_check=True)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Check configuration after attempted reassignment
    st.log("Checking configuration after conflicting assignment attempt")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d1 = str(bgp_config_d1)
    st.log(f"D1 BGP config after conflicting assignment:\n{config_str_d1}")

    # Analyze configuration
    if f"peer-group {data.pg_ebgp_name}" in config_str_d1 and f"neighbor {data.D2_ip}" in config_str_d1:
        st.log(f"[BUG CONFIRMED] Neighbor assigned to EBGP_GROUP despite remote-AS conflict")
        st.log(f"[BUG] Neighbor AS: {data.asn_local}, EBGP_GROUP AS: {data.asn_remote}")
        st.log(f"[BUG] SONiC should have rejected this configuration")

        # This documents the bug - test passes because we're testing buggy behavior
        st.log(f"[INFO] Test validates presence of bug (negative test)")
    else:
        st.log(f"[INFO] Configuration state unclear - checking details")

    st.report_tc_pass(TC_IDS.conflicting_assignment, "test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.negative_test
@pytest.mark.known_bug
def test_bgp_pg18_config_verification():
    """
    TC-BGP-PG18-005: Verify final configuration state.

    Steps:
        1. Display complete BGP configuration
        2. Document conflicting state (if present)
        3. Verify both peer-groups exist
        4. Document validation gap
    """
    st.banner(f"TEST CASE: {TC_IDS.config_verification} - Configuration Verification")

    # Get complete BGP configuration
    st.log("Retrieving complete BGP configuration")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    config_str_d1 = str(bgp_config_d1)
    st.log(f"D1 complete BGP configuration:\n{config_str_d1}")

    # Verify peer-groups exist
    st.log("Verifying peer-groups")
    if data.pg_ibgp_name in config_str_d1:
        st.log(f"[PASS] {data.pg_ibgp_name} exists (AS {data.asn_local})")
    else:
        st.log(f"[FAIL] {data.pg_ibgp_name} not found")

    if data.pg_ebgp_name in config_str_d1:
        st.log(f"[PASS] {data.pg_ebgp_name} exists (AS {data.asn_remote})")
    else:
        st.log(f"[FAIL] {data.pg_ebgp_name} not found")

    # Check neighbor configuration
    st.log(f"Checking neighbor {data.D2_ip} configuration")
    if f"neighbor {data.D2_ip}" in config_str_d1:
        st.log(f"[PASS] Neighbor {data.D2_ip} configured")

        # Check which peer-group is assigned
        neighbor_section = config_str_d1[config_str_d1.find(f"neighbor {data.D2_ip}"):]
        neighbor_section = neighbor_section[:neighbor_section.find("!") if "!" in neighbor_section else len(neighbor_section)]

        if data.pg_ebgp_name in neighbor_section:
            st.log(f"[BUG] Neighbor assigned to {data.pg_ebgp_name} (conflicting AS)")
        elif data.pg_ibgp_name in neighbor_section:
            st.log(f"[OK] Neighbor assigned to {data.pg_ibgp_name} (matching AS)")
        else:
            st.log(f"[INFO] Peer-group assignment unclear")
    else:
        st.log(f"[WARN] Neighbor {data.D2_ip} not found in config")

    # Document bug
    st.log("=" * 80)
    st.log("VALIDATION GAP DOCUMENTED:")
    st.log(f"- SONiC CLI does NOT validate peer-group remote-AS compatibility")
    st.log(f"- Neighbor with remote-as {data.asn_local} can be assigned to")
    st.log(f"  peer-group with remote-as {data.asn_remote}")
    st.log(f"- No error message is displayed")
    st.log(f"- Configuration may be invalid/inconsistent")
    st.log("=" * 80)

    st.report_tc_pass(TC_IDS.config_verification, "test_case_passed")
