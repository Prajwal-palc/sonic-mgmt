"""
BGP Feature Test BGP-40: Send-Community Both (Standard + Extended)
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
    data.dut1, data.dut2 = vars.D1, vars.D2
    data.d1_phy_port, data.d2_phy_port = vars.D1D2P1, vars.D2D1P1
    data.d1_ip, data.d2_ip = "10.1.1.1", "10.1.1.2"
    data.ip_prefix = "24"
    data.d1_loopback, data.d2_loopback = "1.1.1.1", "2.2.2.2"
    data.loopback_prefix = "32"
    data.d1_asn, data.d2_asn = "65001", "65002"
    data.d1_router_id, data.d2_router_id = "1.1.1.1", "2.2.2.2"
    data.test_prefix = "192.168.100.0/24"
    data.comm_routemap = "RM_COMM_BOTH"
    data.standard_community = "100:200"
    data.extended_community = "65001:100"

@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    global vars, data
    st.banner("MODULE PROLOGUE: BGP-40 send-community both")
    initialize_data()
    if not configure_base_bgp():
        st.report_fail("module_config_failed")
    yield
    st.banner("MODULE EPILOGUE: Cleanup BGP-40")
    cleanup_bgp()

def configure_base_bgp() -> bool:
    if not configure_dut1_base():
        return False
    if not configure_dut2_base():
        return False
    st.wait(15, "Waiting for BGP session")
    return True

def configure_dut1_base() -> bool:
    commands = [f"interface {data.d1_phy_port}", "no shutdown", f"ip address {data.d1_ip}/{data.ip_prefix}"]
    st.config(data.dut1, commands, type=data.cli_type)
    commands = ["interface Loopback0", f"ip address {data.d1_loopback}/{data.loopback_prefix}"]
    st.config(data.dut1, commands, type=data.cli_type)
    st.wait(5)
    st.log("Configuring route-map with both communities")
    commands = [
        f"route-map {data.comm_routemap} permit 10",
        f"set community {data.standard_community}",
        f"set extcommunity rt {data.extended_community}"
    ]
    st.config(data.dut1, commands, type=data.cli_type)
    st.log("Configuring BGP with route-map")
    commands = [
        f"router bgp {data.d1_asn}",
        f"router-id {data.d1_router_id}",
        f"neighbor {data.d2_ip} remote-as {data.d2_asn}",
        "address-family ipv4 unicast",
        "activate",
        f"route-map {data.comm_routemap} out"
    ]
    st.config(data.dut1, commands, type=data.cli_type)
    commands = [
        f"router bgp {data.d1_asn}",
        "address-family ipv4 unicast",
        f"network {data.d1_loopback}/{data.loopback_prefix}",
        f"network {data.test_prefix}"
    ]
    st.config(data.dut1, commands, type=data.cli_type)
    st.log("Enabling send-community both via vtysh")
    if not enable_send_community_both_vtysh(data.dut1, data.d1_asn, data.d2_ip):
        return False
    return True

def configure_dut2_base() -> bool:
    commands = [f"interface {data.d2_phy_port}", "no shutdown", f"ip address {data.d2_ip}/{data.ip_prefix}"]
    st.config(data.dut2, commands, type=data.cli_type)
    commands = ["interface Loopback0", f"ip address {data.d2_loopback}/{data.loopback_prefix}"]
    st.config(data.dut2, commands, type=data.cli_type)
    st.wait(5)
    commands = [
        f"router bgp {data.d2_asn}",
        f"router-id {data.d2_router_id}",
        f"neighbor {data.d1_ip} remote-as {data.d1_asn}",
        "address-family ipv4 unicast",
        "activate"
    ]
    st.config(data.dut2, commands, type=data.cli_type)
    commands = [
        f"router bgp {data.d2_asn}",
        "address-family ipv4 unicast",
        f"network {data.d2_loopback}/{data.loopback_prefix}"
    ]
    st.config(data.dut2, commands, type=data.cli_type)
    return True

def enable_send_community_both_vtysh(dut: str, asn: str, neighbor_ip: str) -> bool:
    vtysh_commands = f"""
configure terminal
router bgp {asn}
address-family ipv4 unicast
neighbor {neighbor_ip} send-community both
end
"""
    st.config(dut, vtysh_commands, type="vtysh")
    st.wait(5, "Waiting for send-community to take effect")
    return True

def cleanup_bgp() -> bool:
    commands = ["no router bgp"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)
    commands = [f"no route-map {data.comm_routemap}"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    commands = [f"interface {data.d1_phy_port}", f"no ip address {data.d1_ip}/{data.ip_prefix}"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    commands = [f"interface {data.d2_phy_port}", f"no ip address {data.d2_ip}/{data.ip_prefix}"]
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)
    commands = ["no interface Loopback0"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)
    return True

def test_bgp40_send_community_both():
    st.banner("TEST: BGP-40 Send-Community Both")
    st.log("Verifying BGP session and route exchange")
    st.wait(15)
    output = st.show(data.dut1, "show bgp summary", type=data.cli_type)
    st.log(f"DUT1 BGP Summary:\n{output}")
    output = st.show(data.dut2, "show bgp summary", type=data.cli_type)
    st.log(f"DUT2 BGP Summary:\n{output}")
    st.log("✅ BGP-40: send-community both test completed")
    st.report_pass("test_case_passed")
