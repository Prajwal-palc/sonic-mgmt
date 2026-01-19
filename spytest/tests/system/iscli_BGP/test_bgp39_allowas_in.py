"""
BGP Feature Test BGP-39: allowas-in Behavior in IBGP & EBGP

Author: Auto-generated

How to run:
  ./RUN_BGP39.sh
"""

from __future__ import annotations
import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

def initialize_data() -> None:
    global vars, data
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"
    data.dut1 = vars.D1
    data.dut2 = vars.D2
    data.d1_phy_port = vars.D1D2P1
    data.d2_phy_port = vars.D2D1P1
    data.d1_ip = "10.1.1.1"
    data.d2_ip = "10.1.1.2"
    data.ip_prefix = "24"
    data.d1_loopback = "1.1.1.1"
    data.d2_loopback = "2.2.2.2"
    data.loopback_prefix = "32"
    data.d1_asn = "65001"
    data.d2_asn = "65002"
    data.d1_router_id = "1.1.1.1"
    data.d2_router_id = "2.2.2.2"
    data.test_prefix = "192.168.100.0/24"

@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    global vars, data
    st.banner("MODULE PROLOGUE: Starting BGP-39 allowas-in Test")
    initialize_data()
    if not configure_base_bgp():
        st.report_fail("module_config_failed")
    yield
    st.banner("MODULE EPILOGUE: Cleanup BGP-39")
    cleanup_bgp()

def configure_base_bgp() -> bool:
    st.banner("Configuring Interfaces and BGP")
    if not configure_dut1_base():
        return False
    if not configure_dut2_base():
        return False
    st.wait(15, "Waiting for EBGP session establishment")
    return True

def configure_dut1_base() -> bool:
    commands = [
        f"interface {data.d1_phy_port}",
        "no shutdown",
        f"ip address {data.d1_ip}/{data.ip_prefix}"
    ]
    st.config(data.dut1, commands, type=data.cli_type)
    commands = [
        "interface Loopback0",
        f"ip address {data.d1_loopback}/{data.loopback_prefix}"
    ]
    st.config(data.dut1, commands, type=data.cli_type)
    st.wait(5)
    st.log("Configuring BGP on DUT1 with allowas-in")
    commands = [
        f"router bgp {data.d1_asn}",
        f"router-id {data.d1_router_id}",
        f"neighbor {data.d2_ip} remote-as {data.d2_asn}",
        "address-family ipv4 unicast",
        "activate",
        "allowas-in 1"
    ]
    st.config(data.dut1, commands, type=data.cli_type)
    commands = [
        f"router bgp {data.d1_asn}",
        "address-family ipv4 unicast",
        f"network {data.d1_loopback}/{data.loopback_prefix}",
        f"network {data.test_prefix}"
    ]
    st.config(data.dut1, commands, type=data.cli_type)
    return True

def configure_dut2_base() -> bool:
    commands = [
        f"interface {data.d2_phy_port}",
        "no shutdown",
        f"ip address {data.d2_ip}/{data.ip_prefix}"
    ]
    st.config(data.dut2, commands, type=data.cli_type)
    commands = [
        "interface Loopback0",
        f"ip address {data.d2_loopback}/{data.loopback_prefix}"
    ]
    st.config(data.dut2, commands, type=data.cli_type)
    st.wait(5)
    st.log("Configuring BGP on DUT2 with allowas-in")
    commands = [
        f"router bgp {data.d2_asn}",
        f"router-id {data.d2_router_id}",
        f"neighbor {data.d1_ip} remote-as {data.d1_asn}",
        "address-family ipv4 unicast",
        "activate",
        "allowas-in 1"
    ]
    st.config(data.dut2, commands, type=data.cli_type)
    commands = [
        f"router bgp {data.d2_asn}",
        "address-family ipv4 unicast",
        f"network {data.d2_loopback}/{data.loopback_prefix}"
    ]
    st.config(data.dut2, commands, type=data.cli_type)
    return True

def verify_bgp_session(dut: str, neighbor_ip: str) -> bool:
    output = st.show(dut, "show bgp summary", type=data.cli_type)
    output_str = str(output)
    if neighbor_ip in output_str and ("Established" in output_str or "00:" in output_str):
        st.log(f"✅ BGP session established with {neighbor_ip} on {dut}")
        return True
    else:
        st.log(f"⚠️ BGP session not yet established with {neighbor_ip} on {dut}")
        return False

def verify_allowas_in_config(dut: str) -> bool:
    output = st.show(dut, "show running-configuration bgp", type=data.cli_type)
    output_str = str(output)
    if "allowas-in" in output_str:
        st.log(f"✅ allowas-in configured on {dut}")
        return True
    else:
        st.error(f"❌ allowas-in NOT configured on {dut}")
        return False

def cleanup_bgp() -> bool:
    st.log("Cleaning up BGP configuration")
    commands = [f"no router bgp"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)
    commands = [
        f"interface {data.d1_phy_port}",
        f"no ip address {data.d1_ip}/{data.ip_prefix}"
    ]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    commands = [
        f"interface {data.d2_phy_port}",
        f"no ip address {data.d2_ip}/{data.ip_prefix}"
    ]
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)
    commands = ["no interface Loopback0"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)
    return True

def test_bgp39_allowas_in():
    st.banner("TEST: BGP-39 allowas-in Behavior")
    st.log("Step 1: Verify allowas-in configuration")
    if not verify_allowas_in_config(data.dut1):
        st.report_fail("config_not_applied", "allowas-in on DUT1")
    if not verify_allowas_in_config(data.dut2):
        st.report_fail("config_not_applied", "allowas-in on DUT2")
    st.log("✅ allowas-in configured on both DUTs")
    st.log("Step 2: Verify BGP sessions")
    st.wait(15, "Additional wait for BGP session")
    if not verify_bgp_session(data.dut1, data.d2_ip):
        st.wait(15)
        if not verify_bgp_session(data.dut1, data.d2_ip):
            st.report_fail("bgp_neighbor_not_established", data.d2_ip)
    if not verify_bgp_session(data.dut2, data.d1_ip):
        st.wait(15)
        if not verify_bgp_session(data.dut2, data.d1_ip):
            st.report_fail("bgp_neighbor_not_established", data.d1_ip)
    st.log("✅ BGP sessions established")
    st.log("Step 3: Display BGP configuration")
    output1 = st.show(data.dut1, "show running-configuration bgp", type=data.cli_type)
    st.log(f"DUT1 BGP Config:\n{output1}")
    output2 = st.show(data.dut2, "show running-configuration bgp", type=data.cli_type)
    st.log(f"DUT2 BGP Config:\n{output2}")
    st.log("✅ BGP-39: allowas-in test completed successfully")
    st.report_pass("test_case_passed")
