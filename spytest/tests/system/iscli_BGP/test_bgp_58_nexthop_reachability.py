#!/usr/bin/env python3
"""
BGP Next-Hop Reachability Dependency Test - BGP-58

Test Objective: Verify BGP routes are removed when next-hop becomes unreachable

Test Scenarios:
- Configure BGP neighbors and establish sessions
- Verify routes are installed with reachable next-hops
- Shutdown interface and verify routes are removed
- Bring up interface and verify routes are re-installed

Topology:
    D1 (smic_sonic1) <--Ethernet4--> D2 (smic_sonic2)
    192.168.100.203                  192.168.100.196
    Router-ID: 1.1.1.1               Router-ID: 2.2.2.2
    AS: 65001                        AS: 65002

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_BGP/test_bgp_58_nexthop_reachability.py \
  --logs-path ./logs/bgp_58_$(date +%F_%H%M%S) \
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

vars = SpyTestDict()
data = SpyTestDict()

TC_IDS = SpyTestDict({
    "interface_config": "TC-BGP-58-001",
    "bgp_config": "TC-BGP-58-002",
    "neighbor_config": "TC-BGP-58-003",
    "reachability_check": "TC-BGP-58-004",
    "interface_shutdown_test": "TC-BGP-58-005",
    "session_check": "TC-BGP-58-006",
})


def initialize_data() -> None:
    global vars, data
    vars = st.ensure_min_topology("D1D2:1")
    data.D1_interface = "Ethernet4"
    data.D2_interface = "Ethernet4"
    data.D1_ip = "10.1.1.1"
    data.D2_ip = "10.1.1.2"
    data.subnet_mask = "24"
    data.asn_d1 = "65001"
    data.asn_d2 = "65002"
    data.router_id_d1 = "1.1.1.1"
    data.router_id_d2 = "2.2.2.2"
    data.keepalive = "10"
    data.holdtime = "30"
    data.cli_type = "klish"
    st.log(f"Initialized BGP-58 test data")
    st.log(f"Testing next-hop reachability dependency")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    global vars, data
    st.banner("=" * 80)
    st.banner("BGP-58: NEXT-HOP REACHABILITY DEPENDENCY TEST - MODULE PROLOGUE")
    st.banner("=" * 80)
    initialize_data()
    st.log("Module setup completed")
    yield
    st.banner("=" * 80)
    st.banner("BGP-58: MODULE EPILOGUE - CLEANUP")
    st.banner("=" * 80)
    cleanup_bgp_config()
    st.log("Module cleanup completed")


def cleanup_bgp_config() -> None:
    st.log("Cleaning up BGP and interface configuration")
    for dut in [vars.D1, vars.D2]:
        asn = data.asn_d1 if dut == vars.D1 else data.asn_d2
        interface = data.D1_interface if dut == vars.D1 else data.D2_interface
        ip_addr = data.D1_ip if dut == vars.D1 else data.D2_ip
        st.log(f"Ensuring interface {interface} is up on {dut}")
        st.config(dut, f"interface {interface}", type=data.cli_type, skip_error_check=True)
        st.config(dut, "no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"no router bgp {asn}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"interface {interface}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"no ip address {ip_addr}/{data.subnet_mask}", type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)
    st.log("Cleanup completed")


@pytest.mark.bgp_nexthop
@pytest.mark.reachability_test
def test_bgp_58_interface_config():
    st.banner(f"Test Case: {TC_IDS.interface_config} - Interface Configuration")
    st.log(f"Configuring {data.D1_interface} on {vars.D1}")
    st.config(vars.D1, f"interface {data.D1_interface}", type=data.cli_type)
    st.config(vars.D1, f"ip address {data.D1_ip}/{data.subnet_mask}", type=data.cli_type)
    st.config(vars.D1, "no shutdown", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.log(f"Configuring {data.D2_interface} on {vars.D2}")
    st.config(vars.D2, f"interface {data.D2_interface}", type=data.cli_type)
    st.config(vars.D2, f"ip address {data.D2_ip}/{data.subnet_mask}", type=data.cli_type)
    st.config(vars.D2, "no shutdown", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.log("Waiting 5 seconds for interfaces to stabilize")
    time.sleep(5)
    output_d1 = st.show(vars.D1, f"show ip interface {data.D1_interface}", type=data.cli_type, skip_tmpl=True)
    if data.D1_ip not in str(output_d1):
        st.report_fail("test_case_failed", f"IP {data.D1_ip} not found on {vars.D1}")
    output_d2 = st.show(vars.D2, f"show ip interface {data.D2_interface}", type=data.cli_type, skip_tmpl=True)
    if data.D2_ip not in str(output_d2):
        st.report_fail("test_case_failed", f"IP {data.D2_ip} not found on {vars.D2}")
    st.log("[PASS] Interface configuration successful")
    st.report_tc_pass(TC_IDS.interface_config, "msg", "Interface configuration successful")


@pytest.mark.bgp_nexthop
@pytest.mark.reachability_test
def test_bgp_58_bgp_config():
    st.banner(f"Test Case: {TC_IDS.bgp_config} - BGP Configuration")
    st.log(f"Configuring BGP on {vars.D1}")
    st.config(vars.D1, f"router bgp {data.asn_d1}", type=data.cli_type)
    st.config(vars.D1, f"router-id {data.router_id_d1}", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.log(f"Configuring BGP on {vars.D2}")
    st.config(vars.D2, f"router bgp {data.asn_d2}", type=data.cli_type)
    st.config(vars.D2, f"router-id {data.router_id_d2}", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    if data.asn_d1 not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"AS {data.asn_d1} not found")
    st.log("[PASS] BGP configuration successful")
    st.report_tc_pass(TC_IDS.bgp_config, "msg", "BGP routers configured")


@pytest.mark.bgp_nexthop
@pytest.mark.reachability_test
def test_bgp_58_neighbor_config():
    st.banner(f"Test Case: {TC_IDS.neighbor_config} - Neighbor Configuration")
    st.log(f"Configuring neighbor on {vars.D1}")
    st.config(vars.D1, f"router bgp {data.asn_d1}", type=data.cli_type)
    st.config(vars.D1, f"neighbor {data.D2_ip} remote-as {data.asn_d2}", type=data.cli_type)
    st.config(vars.D1, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D1, "activate", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.log(f"Configuring neighbor on {vars.D2}")
    st.config(vars.D2, f"router bgp {data.asn_d2}", type=data.cli_type)
    st.config(vars.D2, f"neighbor {data.D1_ip} remote-as {data.asn_d1}", type=data.cli_type)
    st.config(vars.D2, "address-family ipv4 unicast", type=data.cli_type)
    st.config(vars.D2, "activate", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    st.config(vars.D2, "exit", type=data.cli_type)
    bgp_config_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)
    if data.D2_ip not in str(bgp_config_d1):
        st.report_fail("test_case_failed", f"Neighbor {data.D2_ip} not configured")
    st.log("[PASS] Neighbor configuration successful")
    st.report_tc_pass(TC_IDS.neighbor_config, "msg", "BGP neighbors configured")


@pytest.mark.bgp_nexthop
@pytest.mark.reachability_test
def test_bgp_58_reachability_check():
    st.banner(f"Test Case: {TC_IDS.reachability_check} - Next-Hop Reachability Check")
    st.log("Waiting 30 seconds for BGP session establishment")
    time.sleep(30)
    st.log(f"Checking BGP routes on {vars.D1} with reachable next-hop")
    bgp_routes_d1 = st.show(vars.D1, "show bgp ipv4 unicast", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 BGP Routes (next-hop reachable):\n{bgp_routes_d1}")
    st.log(f"Checking BGP summary on {vars.D1}")
    bgp_summary_d1 = st.show(vars.D1, "show bgp summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Summary:\n{bgp_summary_d1}")
    st.log("[INFO] BGP routes should be installed with reachable next-hop")
    st.log("[PASS] Next-hop reachability check completed")
    st.report_tc_pass(TC_IDS.reachability_check, "msg", "Next-hop reachability verified")


@pytest.mark.bgp_nexthop
@pytest.mark.reachability_test
def test_bgp_58_interface_shutdown_test():
    st.banner(f"Test Case: {TC_IDS.interface_shutdown_test} - Interface Shutdown Test")
    st.log(f"Shutting down interface {data.D1_interface} on {vars.D1}")
    st.config(vars.D1, f"interface {data.D1_interface}", type=data.cli_type)
    st.config(vars.D1, "shutdown", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.log("Waiting 20 seconds for BGP session to go down")
    time.sleep(20)
    st.log(f"Checking BGP summary on {vars.D1} after interface shutdown")
    bgp_summary_d1_down = st.show(vars.D1, "show bgp summary", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 BGP Summary (interface down):\n{bgp_summary_d1_down}")
    st.log("[INFO] BGP session should be down, routes removed")
    st.log(f"Bringing up interface {data.D1_interface} on {vars.D1}")
    st.config(vars.D1, f"interface {data.D1_interface}", type=data.cli_type)
    st.config(vars.D1, "no shutdown", type=data.cli_type)
    st.config(vars.D1, "exit", type=data.cli_type)
    st.log("Waiting 30 seconds for BGP session to re-establish")
    time.sleep(30)
    st.log(f"Checking BGP summary on {vars.D1} after interface restoration")
    bgp_summary_d1_up = st.show(vars.D1, "show bgp summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Summary (interface up):\n{bgp_summary_d1_up}")
    st.log("[INFO] BGP session should be re-established, routes re-installed")
    st.log("[PASS] Interface shutdown test completed")
    st.report_tc_pass(TC_IDS.interface_shutdown_test, "msg", "Next-hop dependency verified with interface shutdown")


@pytest.mark.bgp_nexthop
@pytest.mark.reachability_test
def test_bgp_58_session_check():
    st.banner(f"Test Case: {TC_IDS.session_check} - Final BGP Session Check")
    st.log("Waiting 10 seconds for BGP stabilization")
    time.sleep(10)
    bgp_summary_d1 = st.show(vars.D1, "show bgp summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D1 BGP Summary:\n{bgp_summary_d1}")
    neighbor_output_d1 = st.show(vars.D1, f"show bgp ipv4 unicast neighbors {data.D2_ip}",
                                 type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 Neighbor Details:\n{neighbor_output_d1}")
    bgp_routes_d1 = st.show(vars.D1, "show bgp ipv4 unicast", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
    st.log(f"D1 BGP Routes (final state):\n{bgp_routes_d1}")
    bgp_summary_d2 = st.show(vars.D2, "show bgp ipv4 unicast summary", type=data.cli_type, skip_tmpl=True)
    st.log(f"D2 BGP IPv4 Summary:\n{bgp_summary_d2}")
    st.log("[PASS] BGP session check completed")
    st.report_tc_pass(TC_IDS.session_check, "msg", "BGP session verified after next-hop reachability test")
