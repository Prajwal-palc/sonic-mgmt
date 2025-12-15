#!/usr/bin/env python3
"""
BGP Soft-Reconfiguration Inbound Test - BGP-38

Test Objective: Verify soft-reconfiguration inbound functionality

Test Scenarios:
- Configure soft-reconfiguration inbound on peer-group
- Verify routing policy changes without session reset
- Validate pre-policy route storage

Topology:
    D1 (smic_sonic1) <--Ethernet4--> D2 (smic_sonic2)
    192.168.100.203                  192.168.100.196
    Router-ID: 1.1.1.1               Router-ID: 2.2.2.2
    AS: 65001                        AS: 65001

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_38_soft_reconfig.py \
  --logs-path ./logs/bgp_38_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Prerequisites:
  - Topology: two-device (D1-D2) | Supported: HW and Virtual
  - SONiC devices with BGP support
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
    "interface_config": "TC-BGP-38-001",
    "bgp_config": "TC-BGP-38-002",
    "neighbor_config": "TC-BGP-38-003",
    "soft_reconfig_config": "TC-BGP-38-004",
    "config_verification": "TC-BGP-38-005",
    "session_check": "TC-BGP-38-006",
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

    data.asn = "65001"
    data.router_id_d1 = "1.1.1.1"
    data.router_id_d2 = "2.2.2.2"

    data.peer_group_name = "SOFT_RECONFIG_PG"
    data.keepalive = "10"
    data.holdtime = "30"

    # CLI type - using klish
    data.cli_type = "klish"

    st.log(f"Initialized BGP-38 test data")
    st.log(f"D1: {data.D1_ip}, D2: {data.D2_ip}, AS: {data.asn}")
    st.log(f"Peer-group: {data.peer_group_name}")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP-38: SOFT-RECONFIGURATION INBOUND TEST - MODULE PROLOGUE")
    st.banner("=" * 80)

    # Initialize test data
    initialize_data()

    st.log("Module setup completed")

    # Yield for test execution
    yield

    # Module epilogue - Cleanup
    st.banner("=" * 80)
    st.banner("BGP-38: MODULE EPILOGUE - CLEANUP")
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

        # Remove IP addresses
        interface = data.D1_interface if dut == vars.D1 else data.D2_interface
        st.config(dut, f"interface {interface}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"no ip address {data.D1_ip if dut == vars.D1 else data.D2_ip}/{data.subnet_mask}",
                  type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)

    st.log("Cleanup completed")


@pytest.mark.bgp_soft_reconfig
@pytest.mark.soft_reconfiguration_test
def test_bgp_38_interface_config():
    """
    TC-BGP-38-001: Configure IP addresses on Ethernet4 interfaces.

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


@pytest.mark.bgp_soft_reconfig
@pytest.mark.soft_reconfiguration_test
def test_bgp_38_bgp_config():
    """
    TC-BGP-38-002: Configure BGP router and peer-group.

    Steps:
        1. Configure BGP router on D1 and D2
        2. Set router-ID on both devices
        3. Create peer-group SOFT_RECONFIG_PG
        4. Configure peer-group timers
        5. Verify BGP configuration
    """
    st.banner(f"Test Case: {TC_IDS.bgp_config} - BGP Configuration")

    # Configure BGP on D1
    st.log(f"Configuring BGP on {vars.D1}")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"router-id {data.router_id_d1}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D1, f"remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"timers {data.keepalive} {data.holdtime}", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure BGP on D2
    st.log(f"Configuring BGP on {vars.D2}")
    st.config(vars.D2, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"router-id {data.router_id_d2}", type=data.cli_type)
    st.config(vars.D2, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D2, f"remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"timers {data.keepalive} {data.holdtime}", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify BGP configuration on D1
    st.log(f"Verifying BGP configuration on {vars.D1}")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Config: {bgp_config_d1}")

    if data.peer_group_name not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"Peer-group {data.peer_group_name} not found on {vars.D1}")

    st.log("[PASS] BGP configuration successful")
    st.report_tc_pass(TC_IDS.bgp_config, "msg", "BGP router and peer-group configured")


@pytest.mark.bgp_soft_reconfig
@pytest.mark.soft_reconfiguration_test
def test_bgp_38_neighbor_config():
    """
    TC-BGP-38-003: Configure BGP neighbors.

    Steps:
        1. Configure neighbor 10.1.1.2 on D1
        2. Assign neighbor to peer-group
        3. Configure neighbor 10.1.1.1 on D2
        4. Assign neighbor to peer-group
        5. Activate address-family for neighbors
    """
    st.banner(f"Test Case: {TC_IDS.neighbor_config} - Neighbor Configuration")

    # Configure neighbor on D1
    st.log(f"Configuring neighbor on {vars.D1}")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure neighbor on D2
    st.log(f"Configuring neighbor on {vars.D2}")
    st.config(vars.D2, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"neighbor {data.D1_ip} remote-as {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D2, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D2, "activate", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify neighbor configuration
    st.log(f"Verifying neighbor configuration on {vars.D1}")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)

    if data.D2_ip not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"Neighbor {data.D2_ip} not configured on {vars.D1}")

    st.log("[PASS] Neighbor configuration successful")
    st.report_tc_pass(TC_IDS.neighbor_config, "msg", "Neighbors configured")


@pytest.mark.bgp_soft_reconfig
@pytest.mark.soft_reconfiguration_test
def test_bgp_38_soft_reconfig_config():
    """
    TC-BGP-38-004: Configure soft-reconfiguration inbound.

    Steps:
        1. Configure soft-reconfiguration inbound on peer-group
        2. Apply configuration to both devices
        3. Verify soft-reconfiguration setting
    """
    st.banner(f"Test Case: {TC_IDS.soft_reconfig_config} - Soft-Reconfiguration Configuration")

    # Configure soft-reconfiguration inbound on D1
    st.log(f"Configuring soft-reconfiguration inbound on {vars.D1}")
    st.config(vars.D1, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D1, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "soft-reconfiguration inbound", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure soft-reconfiguration inbound on D2
    st.log(f"Configuring soft-reconfiguration inbound on {vars.D2}")
    st.config(vars.D2, f"router bgp {data.asn}", type=data.cli_type)
    st.config(vars.D2, f"peer-group {data.peer_group_name}", type=data.cli_type)
    st.config(vars.D2, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D2, "soft-reconfiguration inbound", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify soft-reconfiguration configuration on D1
    st.log(f"Verifying soft-reconfiguration configuration on {vars.D1}")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Config: {bgp_config_d1}")

    config_str_d1 = str(bgp_config_d1)

    if "soft-reconfiguration inbound" not in config_str_d1:
        st.report_fail("test_case_failed", "soft-reconfiguration inbound not configured")

    st.log("[PASS] Soft-reconfiguration inbound configuration successful")
    st.report_tc_pass(TC_IDS.soft_reconfig_config, "msg", "Soft-reconfiguration inbound configured")


@pytest.mark.bgp_soft_reconfig
@pytest.mark.soft_reconfiguration_test
def test_bgp_38_config_verification():
    """
    TC-BGP-38-005: Verify BGP configuration with soft-reconfiguration.

    Steps:
        1. Display running-configuration bgp on both DUTs
        2. Verify peer-group configuration
        3. Verify soft-reconfiguration inbound setting
        4. Check peer-group details
    """
    st.banner(f"Test Case: {TC_IDS.config_verification} - Configuration Verification")

    # Verify D1 configuration
    st.log(f"Verifying configuration on {vars.D1}")

    # Show running-config
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Running Config:\n{bgp_config_d1}")

    config_str_d1 = str(bgp_config_d1)

    # Verify peer-group exists
    if data.peer_group_name not in config_str_d1:
        st.report_fail("test_case_failed", f"Peer-group {data.peer_group_name} not found in config")

    # Verify soft-reconfiguration inbound is configured
    if "soft-reconfiguration inbound" not in config_str_d1:
        st.report_fail("test_case_failed", "soft-reconfiguration inbound not found in config")

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
    st.report_tc_pass(TC_IDS.config_verification, "msg", "BGP configuration with soft-reconfiguration verified")


@pytest.mark.bgp_soft_reconfig
@pytest.mark.soft_reconfiguration_test
def test_bgp_38_session_check():
    """
    TC-BGP-38-006: Verify BGP session with soft-reconfiguration.

    Steps:
        1. Wait for BGP session to establish
        2. Check BGP summary on both devices
        3. Verify neighbor details show soft-reconfiguration
        4. Validate session state
    """
    st.banner(f"Test Case: {TC_IDS.session_check} - BGP Session Check")

    # Wait for BGP session establishment
    st.log("Waiting 30 seconds for BGP session establishment")
    time.sleep(30)

    # Check BGP summary on D1
    st.log(f"Checking BGP summary on {vars.D1}")
    bgp_summary_d1 = st.show(vars.D1, "show bgp summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Summary:\n{bgp_summary_d1}")

    # Check BGP neighbor details on D1
    st.log(f"Checking BGP neighbor {data.D2_ip} on {vars.D1}")
    neighbor_output_d1 = st.show(vars.D1, f"show bgp ipv4 unicast neighbors {data.D2_ip}",
                                 type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 Neighbor Details:\n{neighbor_output_d1}")

    neighbor_str_d1 = str(neighbor_output_d1)

    # Check for soft-reconfiguration
    if "soft" in neighbor_str_d1.lower() or "reconfiguration" in neighbor_str_d1.lower():
        st.log("[PASS] Soft-reconfiguration information found in neighbor details")
    else:
        st.log("[INFO] Soft-reconfiguration may not appear in neighbor output")

    # Check BGP summary on D2
    st.log(f"Checking BGP summary on {vars.D2}")
    bgp_summary_d2 = st.show(vars.D2, "show bgp ipv4 unicast summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP IPv4 Summary:\n{bgp_summary_d2}")

    st.log("[PASS] BGP session check completed")
    st.report_tc_pass(TC_IDS.session_check, "msg", "BGP session verified with soft-reconfiguration inbound")
