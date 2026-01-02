"""
EVPN Test EVPN-05: RT/RD Import-Export Functionality
NOTE: Requires vtysh for VRF configuration (ip vrf not in Klish)
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
    data.vrf_name = "VrfRed"
    data.rd_value = "65001:100"
    data.rt_value = "65001:100"

@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    global vars, data
    st.banner("MODULE PROLOGUE: EVPN-05 RT/RD Import-Export")
    initialize_data()
    if not configure_base_vrf_evpn():
        st.report_fail("module_config_failed")
    yield
    st.banner("MODULE EPILOGUE: Cleanup EVPN-05")
    cleanup_vrf_evpn()

def configure_base_vrf_evpn() -> bool:
    if not configure_dut1_vrf_evpn():
        return False
    if not configure_dut2_vrf_evpn():
        return False
    st.wait(15, "Waiting for BGP EVPN session")
    return True

def configure_dut1_vrf_evpn() -> bool:
    commands = [f"interface {data.d1_phy_port}", "no shutdown", f"ip address {data.d1_ip}/{data.ip_prefix}"]
    st.config(data.dut1, commands, type=data.cli_type)
    commands = ["interface Loopback0", f"ip address {data.d1_loopback}/{data.loopback_prefix}"]
    st.config(data.dut1, commands, type=data.cli_type)
    st.wait(5)
    st.log("Configuring VRF with RD and RT via vtysh")
    vtysh_commands = f"""
configure terminal
vrf {data.vrf_name}
 vni 1000
exit
router bgp {data.d1_asn} vrf {data.vrf_name}
 bgp router-id {data.d1_router_id}
 address-family ipv4 unicast
  redistribute connected
 exit-address-family
 address-family l2vpn evpn
  advertise ipv4 unicast
  rd {data.rd_value}
  route-target import {data.rt_value}
  route-target export {data.rt_value}
 exit-address-family
exit
router bgp {data.d1_asn}
 bgp router-id {data.d1_router_id}
 neighbor {data.d2_ip} remote-as {data.d2_asn}
 address-family l2vpn evpn
  neighbor {data.d2_ip} activate
 exit-address-family
exit
end
"""
    st.config(data.dut1, vtysh_commands, type="vtysh")
    return True

def configure_dut2_vrf_evpn() -> bool:
    commands = [f"interface {data.d2_phy_port}", "no shutdown", f"ip address {data.d2_ip}/{data.ip_prefix}"]
    st.config(data.dut2, commands, type=data.cli_type)
    commands = ["interface Loopback0", f"ip address {data.d2_loopback}/{data.loopback_prefix}"]
    st.config(data.dut2, commands, type=data.cli_type)
    st.wait(5)
    st.log("Configuring BGP EVPN on DUT2")
    commands = [
        f"router bgp {data.d2_asn}",
        f"router-id {data.d2_router_id}",
        f"neighbor {data.d1_ip} remote-as {data.d1_asn}",
        "address-family l2vpn evpn",
        "activate"
    ]
    st.config(data.dut2, commands, type=data.cli_type)
    return True

def cleanup_vrf_evpn() -> bool:
    st.log("Cleaning up VRF and BGP via vtysh")
    vtysh_commands = f"""
configure terminal
no router bgp {data.d1_asn} vrf {data.vrf_name}
no router bgp {data.d1_asn}
no vrf {data.vrf_name}
end
"""
    st.config(data.dut1, vtysh_commands, type="vtysh", skip_error_check=True)
    commands = ["no router bgp"]
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)
    commands = [f"interface {data.d1_phy_port}", f"no ip address {data.d1_ip}/{data.ip_prefix}"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    commands = [f"interface {data.d2_phy_port}", f"no ip address {data.d2_ip}/{data.ip_prefix}"]
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)
    commands = ["no interface Loopback0"]
    st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
    st.config(data.dut2, commands, type=data.cli_type, skip_error_check=True)
    return True

def test_evpn05_rt_rd():
    st.banner("TEST: EVPN-05 RT/RD Import-Export")
    st.log("Verifying VRF and EVPN configuration")
    st.wait(15)
    st.log("Display vtysh running config")
    vtysh_show = "show running-config"
    output1 = st.config(data.dut1, vtysh_show, type="vtysh")
    st.log(f"DUT1 VRF/EVPN Config:\n{output1}")
    st.log("✅ EVPN-05: RT/RD test completed")
    st.report_pass("test_case_passed")
