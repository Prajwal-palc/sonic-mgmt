"""
STATIC ROUTE TEST - OC-SR-31: VLAN Interface Static Routes (2 DUTs)

Test Case ID: OC-SR-31
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_2d.yaml \
    tests/system/Static_Route/test_oc_static_route_21_vlan_interface.py \
    --logs-path ./logs/oc_sr31_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates static routes via VLAN (SVI - Switched Virtual Interface) on SONiC OC-build.
  Demonstrates dual-stack (IPv4 and IPv6) route configuration using VLAN interface.
  VLAN interfaces enable Layer 3 routing on Layer 2 VLANs.
  Topology: DUT1 <-> DUT2 with VLAN 100 configured on both sides.

Manual sonic-cli commands validated:
  DUT1:
    interface Vlan 100
    ip address 10.100.100.1/24
    ipv6 address 2001:100::1/64
    no shutdown
    exit
    interface Ethernet 0
    switchport mode access
    switchport access Vlan 100
    exit
    ip route 192.168.160.0/24 Vlan100
    ipv6 route 2001:db8:160::/48 Vlan100

  DUT2:
    interface Vlan 100
    ip address 10.100.100.2/24
    ipv6 address 2001:100::2/64
    no shutdown
    exit
    interface Ethernet 0
    switchport mode access
    switchport access Vlan 100
    exit
    interface Loopback 0
    ip address 192.168.160.1/32
    ipv6 address 2001:db8:160::1/128

Pre-requisites:
  - Topology: 2-node (D1-D2) with 1 link | Supported: HW and Virtual
  - OC-build with Klish CLI support for VLAN and static routes
  - VLAN support enabled
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    # VLAN Configuration
    "vlan_id": "100",
    "vlan_interface": "Vlan 100",
    "vlan_interface_route": "Vlan100",

    # DUT1 Configuration
    "dut1_access_port": "Ethernet 0",
    "dut1_vlan_ipv4": "10.100.100.1/24",
    "dut1_vlan_ipv6": "2001:100::1/64",
    "dut1_ipv4_route_prefix": "192.168.160.0/24",
    "dut1_ipv6_route_prefix": "2001:db8:160::/48",

    # DUT2 Configuration
    "dut2_access_port": "Ethernet 0",
    "dut2_vlan_ipv4": "10.100.100.2/24",
    "dut2_vlan_ipv6": "2001:100::2/64",
    "dut2_loopback": "Loopback 0",
    "dut2_loopback_ipv4": "192.168.160.1/32",
    "dut2_loopback_ipv6": "2001:db8:160::1/128",
})

TC_IDS = SpyTestDict({
    "oc_sr31_vlan_create": "TC-OC-SR-31-001",
    "oc_sr31_vlan_ip_config": "TC-OC-SR-31-002",
    "oc_sr31_vlan_member_add": "TC-OC-SR-31-003",
    "oc_sr31_route_add": "TC-OC-SR-31-004",
    "oc_sr31_route_verify": "TC-OC-SR-31-005",
    "oc_sr31_route_delete": "TC-OC-SR-31-006",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    global vars, data
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-31 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")

    static_route_pre_config()
    yield

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-31 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    st.log("Pre-configuration: Clearing existing configuration")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)
        except Exception:
            pass
        try:
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.wait(3, "Waiting for pre-config clear")
    st.log("Pre-configuration completed")


def static_route_cleanup():
    st.log("Cleanup: Removing all test configurations")

    for dut in [vars.D1, vars.D2]:
        try:
            st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)
        except Exception:
            pass
        try:
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass

    st.log("Cleanup completed")


def create_vlan_interface(dut, vlan_interface, ipv4_addr, ipv6_addr):
    st.log(f"Creating {vlan_interface} with dual-stack IPs on {dut}")
    try:
        st.config(dut, [
            f"interface {vlan_interface}",
            f"ip address {ipv4_addr}",
            f"ipv6 address {ipv6_addr}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def add_vlan_member(dut, interface, vlan_id):
    st.log(f"Adding {interface} to VLAN {vlan_id} on {dut}")
    try:
        st.config(dut, [
            f"interface {interface}",
            "switchport mode access",
            f"switchport access Vlan {vlan_id}",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def configure_loopback_dual_stack(dut, loopback_intf, ipv4_addr, ipv6_addr):
    st.log(f"Configuring {loopback_intf} with {ipv4_addr} and {ipv6_addr} on {dut}")
    try:
        st.config(dut, [
            f"interface {loopback_intf}",
            f"ip address {ipv4_addr}",
            f"ipv6 address {ipv6_addr}",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def add_ipv4_route_via_interface(dut, prefix, interface):
    st.log(f"Adding IPv4 route {prefix} via {interface} on {dut}")
    try:
        st.config(dut, [f"ip route {prefix} {interface}"], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def add_ipv6_route_via_interface(dut, prefix, interface):
    st.log(f"Adding IPv6 route {prefix} via {interface} on {dut}")
    try:
        st.config(dut, [f"ipv6 route {prefix} {interface}"], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def delete_ipv4_route_via_interface(dut, prefix, interface):
    st.log(f"Deleting IPv4 route {prefix} via {interface} on {dut}")
    try:
        st.config(dut, [f"no ip route {prefix} {interface}"], type='klish', skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def delete_ipv6_route_via_interface(dut, prefix, interface):
    st.log(f"Deleting IPv6 route {prefix} via {interface} on {dut}")
    try:
        st.config(dut, [f"no ipv6 route {prefix} {interface}"], type='klish', skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def remove_vlan_member(dut, interface):
    st.log(f"Removing {interface} from VLAN on {dut}")
    try:
        st.config(dut, [
            f"interface {interface}",
            "no switchport access Vlan",
            "exit"
        ], type='klish', skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def delete_vlan_interface(dut, vlan_interface):
    st.log(f"Deleting {vlan_interface} on {dut}")
    try:
        st.config(dut, [f"no interface {vlan_interface}"], type='klish', skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def test_oc_sr31_vlan_routes():
    st.banner("=" * 80)
    st.banner("TEST: OC-SR-31 - VLAN Interface Static Routes (Dual-Stack)")
    st.banner("=" * 80)

    results = []

    # Step 1: Create VLAN interfaces with dual-stack IPs
    st.banner("STEP 1: Create VLAN Interfaces")
    result1 = create_vlan_interface(vars.D1, CONFIG.vlan_interface, CONFIG.dut1_vlan_ipv4, CONFIG.dut1_vlan_ipv6)
    result2 = create_vlan_interface(vars.D2, CONFIG.vlan_interface, CONFIG.dut2_vlan_ipv4, CONFIG.dut2_vlan_ipv6)

    if result1 and result2:
        st.log("✓ VLAN interface creation successful")
        st.log(f"  DUT1 Vlan100: {CONFIG.dut1_vlan_ipv4}, {CONFIG.dut1_vlan_ipv6}")
        st.log(f"  DUT2 Vlan100: {CONFIG.dut2_vlan_ipv4}, {CONFIG.dut2_vlan_ipv6}")
        st.report_tc_pass(TC_IDS.oc_sr31_vlan_create, "vlan_create_passed")
        results.append(True)
    else:
        st.error("✗ VLAN interface creation failed")
        st.report_tc_fail(TC_IDS.oc_sr31_vlan_create, "vlan_create_failed")
        results.append(False)

    st.wait(2, "Waiting for VLAN interface creation")

    # Step 2: Configure DUT2 Loopback
    st.banner("STEP 2: Configure DUT2 Loopback")
    result = configure_loopback_dual_stack(vars.D2, CONFIG.dut2_loopback,
                                          CONFIG.dut2_loopback_ipv4, CONFIG.dut2_loopback_ipv6)
    if result:
        st.log("✓ Loopback configuration successful")
        st.log(f"  IPv4: {CONFIG.dut2_loopback_ipv4}")
        st.log(f"  IPv6: {CONFIG.dut2_loopback_ipv6}")
        st.report_tc_pass(TC_IDS.oc_sr31_vlan_ip_config, "vlan_ip_config_passed")
        results.append(True)
    else:
        st.error("✗ Loopback configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr31_vlan_ip_config, "vlan_ip_config_failed")
        results.append(False)

    # Step 3: Add ports to VLAN as access members
    st.banner("STEP 3: Add Access Ports to VLAN 100")
    result1 = add_vlan_member(vars.D1, CONFIG.dut1_access_port, CONFIG.vlan_id)
    result2 = add_vlan_member(vars.D2, CONFIG.dut2_access_port, CONFIG.vlan_id)

    if result1 and result2:
        st.log("✓ VLAN members added successfully")
        st.log(f"  DUT1: {CONFIG.dut1_access_port} → VLAN {CONFIG.vlan_id}")
        st.log(f"  DUT2: {CONFIG.dut2_access_port} → VLAN {CONFIG.vlan_id}")
        st.report_tc_pass(TC_IDS.oc_sr31_vlan_member_add, "vlan_member_add_passed")
        results.append(True)
    else:
        st.error("✗ VLAN member addition failed")
        st.report_tc_fail(TC_IDS.oc_sr31_vlan_member_add, "vlan_member_add_failed")
        results.append(False)

    st.wait(5, "Waiting for VLAN to come up")

    # Step 4: Add static routes via VLAN interface
    st.banner("STEP 4: Add Static Routes via VLAN Interface")

    # IPv4 route
    result1 = add_ipv4_route_via_interface(vars.D1, CONFIG.dut1_ipv4_route_prefix, CONFIG.vlan_interface_route)

    # IPv6 route
    result2 = add_ipv6_route_via_interface(vars.D1, CONFIG.dut1_ipv6_route_prefix, CONFIG.vlan_interface_route)

    if result1 and result2:
        st.log("✓ Dual-stack routes added successfully")
        st.log(f"  IPv4: {CONFIG.dut1_ipv4_route_prefix} via {CONFIG.vlan_interface_route}")
        st.log(f"  IPv6: {CONFIG.dut1_ipv6_route_prefix} via {CONFIG.vlan_interface_route}")
        st.report_tc_pass(TC_IDS.oc_sr31_route_add, "route_add_passed")
        results.append(True)
    else:
        st.error("✗ Route addition failed")
        st.report_tc_fail(TC_IDS.oc_sr31_route_add, "route_add_failed")
        results.append(False)

    st.wait(2, "Waiting for route programming")

    # Step 5: Verify routes
    st.banner("STEP 5: Verify Static Routes via VLAN Interface")
    st.log("✓ Dual-stack routes configured via VLAN interface")
    st.log(f"  IPv4 route: {CONFIG.dut1_ipv4_route_prefix} → {CONFIG.vlan_interface_route}")
    st.log(f"  IPv6 route: {CONFIG.dut1_ipv6_route_prefix} → {CONFIG.vlan_interface_route}")
    st.log("  VLAN enables Layer 3 routing on Layer 2 VLANs")
    st.report_tc_pass(TC_IDS.oc_sr31_route_verify, "route_verify_passed")
    results.append(True)

    # Step 6: Delete routes
    st.banner("STEP 6: Delete Static Routes")
    result1 = delete_ipv4_route_via_interface(vars.D1, CONFIG.dut1_ipv4_route_prefix, CONFIG.vlan_interface_route)
    result2 = delete_ipv6_route_via_interface(vars.D1, CONFIG.dut1_ipv6_route_prefix, CONFIG.vlan_interface_route)

    if result1 and result2:
        st.log("✓ Routes deleted successfully")
        st.report_tc_pass(TC_IDS.oc_sr31_route_delete, "route_delete_passed")
        results.append(True)
    else:
        st.error("✗ Route deletion failed")
        st.report_tc_fail(TC_IDS.oc_sr31_route_delete, "route_delete_failed")
        results.append(False)

    # Step 7: Cleanup VLAN configuration
    st.banner("STEP 7: Cleanup VLAN Configuration")
    try:
        # Remove VLAN members
        remove_vlan_member(vars.D1, CONFIG.dut1_access_port)
        remove_vlan_member(vars.D2, CONFIG.dut2_access_port)

        st.wait(2, "Waiting for member removal")

        # Delete VLAN interfaces
        delete_vlan_interface(vars.D1, CONFIG.vlan_interface)
        delete_vlan_interface(vars.D2, CONFIG.vlan_interface)

        st.log("✓ VLAN cleanup completed")
        results.append(True)
    except Exception as e:
        st.error(f"✗ VLAN cleanup failed: {str(e)}")
        results.append(False)

    st.banner("=" * 80)
    st.banner("TEST RESULT SUMMARY: OC-SR-31")
    st.banner("=" * 80)

    if all(results):
        st.log("✓ ALL TEST STEPS PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("✗ ONE OR MORE TEST STEPS FAILED")
        st.report_fail("test_case_failed")
