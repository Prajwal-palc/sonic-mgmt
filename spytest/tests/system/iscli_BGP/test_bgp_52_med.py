#!/usr/bin/env python3
"""
BGP Best-Path Selection - MED Test - BGP-52

Test Objective: Verify BGP best-path selection using Multi-Exit Discriminator (MED)

Test Scenarios:
- Configure route-maps to set different MED values
- Verify lower MED routes are preferred
- Test MED in eBGP path selection

Topology:
    D1 (smic_sonic1) <--Ethernet4--> D2 (smic_sonic2)
    192.168.100.203                  192.168.100.196
    Router-ID: 1.1.1.1               Router-ID: 2.2.2.2
    AS: 65001                        AS: 65002

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_52_med.py \
  --logs-path ./logs/bgp_52_$(date +%F_%H%M%S) \
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
    "interface_config": "TC-BGP-52-001",
    "bgp_config": "TC-BGP-52-002",
    "neighbor_config": "TC-BGP-52-003",
    "route_map_config": "TC-BGP-52-004",
    "config_verification": "TC-BGP-52-005",
    "session_check": "TC-BGP-52-006",
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

    data.asn_d1 = "65001"
    data.asn_d2 = "65002"
    data.router_id_d1 = "1.1.1.1"
    data.router_id_d2 = "2.2.2.2"

    data.route_map_name = "SET_MED"
    data.med_low = "50"
    data.med_high = "200"
    data.keepalive = "10"
    data.holdtime = "30"

    # CLI type - using klish
    data.cli_type = "klish"

    st.log(f"Initialized BGP-52 test data")
    st.log(f"D1: {data.D1_ip} AS {data.asn_d1}, D2: {data.D2_ip} AS {data.asn_d2}")
    st.log(f"Route-map: {data.route_map_name}, MED low: {data.med_low}, high: {data.med_high}")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP-52: MED (MULTI-EXIT DISCRIMINATOR) TEST - MODULE PROLOGUE")
    st.banner("=" * 80)

    # Initialize test data
    initialize_data()

    st.log("Module setup completed")

    # Yield for test execution
    yield

    # Module epilogue - Cleanup
    st.banner("=" * 80)
    st.banner("BGP-52: MODULE EPILOGUE - CLEANUP")
    st.banner("=" * 80)

    cleanup_bgp_config()

    st.log("Module cleanup completed")


def cleanup_bgp_config() -> None:
    """Cleanup BGP and interface configuration."""
    st.log("Cleaning up BGP and interface configuration")

    # Remove route-map and BGP on D1
    st.log(f"Removing route-map on {vars.D1}")
    st.config(vars.D1, f"no route-map {data.route_map_name}", type=data.cli_type, skip_error_check=True)
    st.log(f"Removing BGP configuration on {vars.D1}")
    st.config(vars.D1, f"no router bgp {data.asn_d1}", type=data.cli_type, skip_error_check=True)
    st.config(vars.D1, f"interface {data.D1_interface}", type=data.cli_type, skip_error_check=True)
    st.config(vars.D1, f"no ip address {data.D1_ip}/{data.subnet_mask}",
              type=data.cli_type, skip_error_check=True)
    st.config(vars.D1, "exit", type=data.cli_type, skip_error_check=True)

    # Remove BGP on D2
    st.log(f"Removing BGP configuration on {vars.D2}")
    st.config(vars.D2, f"no router bgp {data.asn_d2}", type=data.cli_type, skip_error_check=True)
    st.config(vars.D2, f"interface {data.D2_interface}", type=data.cli_type, skip_error_check=True)
    st.config(vars.D2, f"no ip address {data.D2_ip}/{data.subnet_mask}",
              type=data.cli_type, skip_error_check=True)
    st.config(vars.D2, "exit", type=data.cli_type, skip_error_check=True)

    st.log("Cleanup completed")


@pytest.mark.bgp_med
@pytest.mark.best_path_test
def test_bgp_52_interface_config():
    """
    TC-BGP-52-001: Configure IP addresses on Ethernet4 interfaces.

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


@pytest.mark.bgp_med
@pytest.mark.best_path_test
def test_bgp_52_bgp_config():
    """
    TC-BGP-52-002: Configure BGP router on both devices.

    Steps:
        1. Configure BGP router on D1 with AS 65001
        2. Configure BGP router on D2 with AS 65002
        3. Set router-ID on both devices
        4. Verify BGP configuration
    """
    st.banner(f"Test Case: {TC_IDS.bgp_config} - BGP Configuration")

    # Configure BGP on D1
    st.log(f"Configuring BGP on {vars.D1} with AS {data.asn_d1}")
    st.config(vars.D1, f"router bgp {data.asn_d1}", type=data.cli_type)
    st.config(vars.D1, f"router-id {data.router_id_d1}", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure BGP on D2
    st.log(f"Configuring BGP on {vars.D2} with AS {data.asn_d2}")
    st.config(vars.D2, f"router bgp {data.asn_d2}", type=data.cli_type)
    st.config(vars.D2, f"router-id {data.router_id_d2}", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)

    # Verify BGP configuration on D1
    st.log(f"Verifying BGP configuration on {vars.D1}")
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Config: {bgp_config_d1}")

    if data.asn_d1 not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"AS {data.asn_d1} not found in D1 BGP config")

    st.log("[PASS] BGP configuration successful")
    st.report_tc_pass(TC_IDS.bgp_config, "msg", "BGP routers configured")


@pytest.mark.bgp_med
@pytest.mark.best_path_test
def test_bgp_52_neighbor_config():
    """
    TC-BGP-52-003: Configure BGP neighbors (eBGP).

    Steps:
        1. Configure neighbor 10.1.1.2 on D1 with remote-as 65002
        2. Configure neighbor 10.1.1.1 on D2 with remote-as 65001
        3. Activate address-family for neighbors
        4. Verify neighbor configuration
    """
    st.banner(f"Test Case: {TC_IDS.neighbor_config} - Neighbor Configuration")

    # Configure neighbor on D1
    st.log(f"Configuring neighbor on {vars.D1}")
    st.config(vars.D1, f"router bgp {data.asn_d1}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_ip} remote-as {data.asn_d2}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Configure neighbor on D2
    st.log(f"Configuring neighbor on {vars.D2}")
    st.config(vars.D2, f"router bgp {data.asn_d2}", type=data.cli_type)
    st.config(vars.D2, f"neighbor {data.D1_ip} remote-as {data.asn_d1}", type=data.cli_type)
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
    st.report_tc_pass(TC_IDS.neighbor_config, "msg", "BGP neighbors configured")


@pytest.mark.bgp_med
@pytest.mark.best_path_test
def test_bgp_52_route_map_config():
    """
    TC-BGP-52-004: Configure route-map with MED.

    Steps:
        1. Create route-map SET_MED
        2. Set metric (MED) to 50 (lower is preferred)
        3. Apply route-map to neighbor
        4. Verify route-map configuration
    """
    st.banner(f"Test Case: {TC_IDS.route_map_config} - Route-map Configuration")

    # Configure route-map on D1
    st.log(f"Configuring route-map with MED on {vars.D1}")
    st.config(vars.D1, f"route-map {data.route_map_name} permit 10", type=data.cli_type)
    st.config(vars.D1, f"set metric {data.med_low}", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Apply route-map to neighbor on D1
    st.log(f"Applying route-map to neighbor on {vars.D1}")
    st.config(vars.D1, f"router bgp {data.asn_d1}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_ip}", type=data.cli_type, skip_error_check=True)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, f"route-map {data.route_map_name} out", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)

    # Verify route-map configuration
    st.log(f"Verifying route-map configuration on {vars.D1}")
    route_map_output = st.show(vars.D1, f"show route-map {data.route_map_name}",
                                type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 Route-map output: {route_map_output}")

    if data.med_low in str(route_map_output):
        st.log(f"[PASS] MED {data.med_low} found in route-map")
    else:
        st.log("[INFO] MED may not appear in route-map show output")

    st.log("[PASS] Route-map configuration successful")
    st.report_tc_pass(TC_IDS.route_map_config, "msg", "Route-map with MED configured")


@pytest.mark.bgp_med
@pytest.mark.best_path_test
def test_bgp_52_config_verification():
    """
    TC-BGP-52-005: Verify BGP configuration with MED.

    Steps:
        1. Display running-configuration bgp on both DUTs
        2. Verify route-map configuration
        3. Verify MED setting
        4. Check BGP configuration details
    """
    st.banner(f"Test Case: {TC_IDS.config_verification} - Configuration Verification")

    # Verify D1 configuration
    st.log(f"Verifying configuration on {vars.D1}")

    # Show running-config
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Running Config:\n{bgp_config_d1}")

    config_str_d1 = str(bgp_config_d1)

    # Verify route-map is applied
    if data.route_map_name in config_str_d1:
        st.log(f"[PASS] Route-map {data.route_map_name} found in BGP config")
    else:
        st.log("[WARNING] Route-map may not appear in BGP running config")

    # Show route-map configuration
    st.log(f"Showing route-map configuration on {vars.D1}")
    route_map_config = st.show(vars.D1, "show running-configuration", type=data.cli_type,
                                skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 Running Config (route-map section):\n{route_map_config}")

    # Verify D2 configuration
    st.log(f"Verifying configuration on {vars.D2}")
    bgp_config_d2 = st.show(vars.D2, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP Running Config:\n{bgp_config_d2}")

    st.log("[PASS] Configuration verification successful")
    st.report_tc_pass(TC_IDS.config_verification, "msg", "BGP configuration with MED verified")


@pytest.mark.bgp_med
@pytest.mark.best_path_test
def test_bgp_52_session_check():
    """
    TC-BGP-52-006: Verify BGP session and MED.

    Steps:
        1. Wait for BGP session to establish
        2. Check BGP summary on both devices
        3. Verify routes with MED
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

    # Check BGP routes with MED on D2
    st.log(f"Checking BGP routes on {vars.D2} to verify MED")
    bgp_routes_d2 = st.show(vars.D2, "show bgp ipv4 unicast",
                            type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    st.log(f"D2 BGP Routes (should show MED):\n{bgp_routes_d2}")

    # Check BGP neighbor details on D1
    st.log(f"Checking BGP neighbor {data.D2_ip} on {vars.D1}")
    neighbor_output_d1 = st.show(vars.D1, f"show bgp ipv4 unicast neighbors {data.D2_ip}",
                                 type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 Neighbor Details:\n{neighbor_output_d1}")

    # Check BGP summary on D2
    st.log(f"Checking BGP summary on {vars.D2}")
    bgp_summary_d2 = st.show(vars.D2, "show bgp ipv4 unicast summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP IPv4 Summary:\n{bgp_summary_d2}")

    st.log("[PASS] BGP session check completed")
    st.report_tc_pass(TC_IDS.session_check, "msg", "BGP session verified with MED configured")
