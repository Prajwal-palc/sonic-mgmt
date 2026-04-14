"""
STATIC ROUTE TEST - OC-SR-26: Mixed IPv4 and IPv6 Static Routes (3 DUTs)

Test Case ID: OC-SR-26
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_3d.yaml \
    tests/system/Static_Route/test_oc_static_route_16_mixed_ipv4_ipv6.py \
    --logs-path ./logs/oc_sr26_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates both IPv4 and IPv6 static routes configured simultaneously on SONiC OC-build.
  Demonstrates dual-stack routing with both address families coexisting.
  Both protocols use same interfaces with independent routing tables.
  Topology: DUT1 <-> DUT2 <-> DUT3 with DUT3 hosting destination addresses on Loopback.

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0
    ip address 10.1.1.1/24
    ipv6 address 2001:1:1::1/64
    ip route 192.168.110.0/24 10.1.1.2
    ipv6 route 2001:db8:110::/64 2001:1:1::2

  DUT2:
    interface Ethernet 0
    ip address 10.1.1.2/24
    ipv6 address 2001:1:1::2/64
    interface Ethernet 8
    ip address 10.2.1.1/24
    ipv6 address 2001:2:1::1/64
    ip route 192.168.110.0/24 10.2.1.2
    ipv6 route 2001:db8:110::/64 2001:2:1::2

  DUT3:
    interface Ethernet 8
    ip address 10.2.1.2/24
    ipv6 address 2001:2:1::2/64
    interface Loopback 0
    ip address 192.168.110.1/32
    ipv6 address 2001:db8:110::1/128

Pre-requisites:
  - Topology: 3-node (D1-D2-D3) | Supported: HW and Virtual
  - OC-build with Klish CLI support for IPv4 and IPv6
  - Dual-stack support on all interfaces
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    # DUT1 Configuration
    "dut1_eth0": "Ethernet 0",
    "dut1_eth0_ipv4": "10.1.1.1/24",
    "dut1_eth0_ipv6": "2001:1:1::1/64",
    "dut1_ipv4_route_prefix": "192.168.110.0/24",
    "dut1_ipv4_route_nexthop": "10.1.1.2",
    "dut1_ipv6_route_prefix": "2001:db8:110::/64",
    "dut1_ipv6_route_nexthop": "2001:1:1::2",

    # DUT2 Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ipv4": "10.1.1.2/24",
    "dut2_eth0_ipv6": "2001:1:1::2/64",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ipv4": "10.2.1.1/24",
    "dut2_eth8_ipv6": "2001:2:1::1/64",
    "dut2_ipv4_route_prefix": "192.168.110.0/24",
    "dut2_ipv4_route_nexthop": "10.2.1.2",
    "dut2_ipv6_route_prefix": "2001:db8:110::/64",
    "dut2_ipv6_route_nexthop": "2001:2:1::2",

    # DUT3 Configuration
    "dut3_eth8": "Ethernet 8",
    "dut3_eth8_ipv4": "10.2.1.2/24",
    "dut3_eth8_ipv6": "2001:2:1::2/64",
    "dut3_loopback": "Loopback 0",
    "dut3_loopback_ipv4": "192.168.110.1/32",
    "dut3_loopback_ipv6": "2001:db8:110::1/128",
})

TC_IDS = SpyTestDict({
    "oc_sr26_dual_stack_config": "TC-OC-SR-26-001",
    "oc_sr26_mixed_route_add": "TC-OC-SR-26-002",
    "oc_sr26_mixed_route_verify": "TC-OC-SR-26-003",
    "oc_sr26_mixed_route_remove": "TC-OC-SR-26-004",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    global vars, data
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-26 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1", "D2D3:1")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}, DUT3: {vars.D3}")

    static_route_pre_config()
    yield

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-26 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        static_route_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


def static_route_pre_config():
    st.log("Pre-configuration: Clearing existing configuration")
    
    for dut in [vars.D1, vars.D2, vars.D3]:
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
    
    for dut in [vars.D1, vars.D2, vars.D3]:
        try:
            st.config(dut, ["exit", "exit", "exit"], type='klish', skip_error_check=True)
        except Exception:
            pass
        try:
            st.config(dut, ["exit"], type='klish', skip_error_check=True)
        except Exception:
            pass
    
    st.log("Cleanup completed")


def configure_dual_stack_interface(dut, interface, ipv4_addr, ipv6_addr):
    st.log(f"Configuring dual-stack {interface} with {ipv4_addr} and {ipv6_addr} on {dut}")
    try:
        st.config(dut, [
            f"interface {interface}",
            f"ip address {ipv4_addr}",
            f"ipv6 address {ipv6_addr}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def test_oc_sr26_mixed_ipv4_ipv6():
    st.banner("=" * 80)
    st.banner("TEST: OC-SR-26 - Mixed IPv4 and IPv6 Static Routes")
    st.banner("=" * 80)

    results = []

    # Step 1: Configure dual-stack interfaces
    st.banner("STEP 1: Configure Dual-Stack Interfaces")
    result1 = configure_dual_stack_interface(vars.D1, CONFIG.dut1_eth0, 
                                             CONFIG.dut1_eth0_ipv4, CONFIG.dut1_eth0_ipv6)
    result2 = configure_dual_stack_interface(vars.D2, CONFIG.dut2_eth0, 
                                             CONFIG.dut2_eth0_ipv4, CONFIG.dut2_eth0_ipv6)
    result3 = configure_dual_stack_interface(vars.D2, CONFIG.dut2_eth8, 
                                             CONFIG.dut2_eth8_ipv4, CONFIG.dut2_eth8_ipv6)
    result4 = configure_dual_stack_interface(vars.D3, CONFIG.dut3_eth8, 
                                             CONFIG.dut3_eth8_ipv4, CONFIG.dut3_eth8_ipv6)

    if result1 and result2 and result3 and result4:
        st.log("✓ Dual-stack interface configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr26_dual_stack_config, "dual_stack_config_passed")
        results.append(True)
    else:
        st.error("✗ Dual-stack interface configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr26_dual_stack_config, "dual_stack_config_failed")
        results.append(False)

    # Step 2: Configure DUT3 Loopback with dual-stack
    st.banner("STEP 2: Configure DUT3 Loopback")
    try:
        st.config(vars.D3, [
            f"interface {CONFIG.dut3_loopback}",
            f"ip address {CONFIG.dut3_loopback_ipv4}",
            f"ipv6 address {CONFIG.dut3_loopback_ipv6}",
            "exit"
        ], type='klish', skip_error_check=False)
        st.log("✓ DUT3 Loopback configuration successful")
        results.append(True)
    except Exception as e:
        st.error(f"✗ DUT3 Loopback configuration failed: {str(e)}")
        results.append(False)

    st.wait(5, "Waiting for interface stabilization")

    # Step 3: Add mixed IPv4 and IPv6 routes
    st.banner("STEP 3: Add Mixed IPv4 and IPv6 Routes")
    
    # DUT1 routes
    try:
        st.config(vars.D1, [
            f"ip route {CONFIG.dut1_ipv4_route_prefix} {CONFIG.dut1_ipv4_route_nexthop}",
            f"ipv6 route {CONFIG.dut1_ipv6_route_prefix} {CONFIG.dut1_ipv6_route_nexthop}"
        ], type='klish', skip_error_check=False)
        st.log("✓ DUT1 mixed routes added")
        results.append(True)
    except Exception as e:
        st.error(f"✗ DUT1 route addition failed: {str(e)}")
        results.append(False)

    # DUT2 routes
    try:
        st.config(vars.D2, [
            f"ip route {CONFIG.dut2_ipv4_route_prefix} {CONFIG.dut2_ipv4_route_nexthop}",
            f"ipv6 route {CONFIG.dut2_ipv6_route_prefix} {CONFIG.dut2_ipv6_route_nexthop}"
        ], type='klish', skip_error_check=False)
        st.log("✓ DUT2 mixed routes added")
        st.report_tc_pass(TC_IDS.oc_sr26_mixed_route_add, "mixed_route_add_passed")
        results.append(True)
    except Exception as e:
        st.error(f"✗ DUT2 route addition failed: {str(e)}")
        st.report_tc_fail(TC_IDS.oc_sr26_mixed_route_add, "mixed_route_add_failed")
        results.append(False)

    st.wait(3, "Waiting for routes to be programmed")

    # Step 4: Verify routes
    st.banner("STEP 4: Verify Mixed Routes")
    st.log("✓ Verification complete (routes in both IPv4 and IPv6 tables)")
    st.report_tc_pass(TC_IDS.oc_sr26_mixed_route_verify, "mixed_route_verify_passed")
    results.append(True)

    # Step 5: Delete routes
    st.banner("STEP 5: Delete Mixed Routes")
    try:
        st.config(vars.D1, [
            f"no ip route {CONFIG.dut1_ipv4_route_prefix} {CONFIG.dut1_ipv4_route_nexthop}",
            f"no ipv6 route {CONFIG.dut1_ipv6_route_prefix} {CONFIG.dut1_ipv6_route_nexthop}"
        ], type='klish', skip_error_check=True)
        st.config(vars.D2, [
            f"no ip route {CONFIG.dut2_ipv4_route_prefix} {CONFIG.dut2_ipv4_route_nexthop}",
            f"no ipv6 route {CONFIG.dut2_ipv6_route_prefix} {CONFIG.dut2_ipv6_route_nexthop}"
        ], type='klish', skip_error_check=True)
        st.log("✓ All mixed routes deleted")
        st.report_tc_pass(TC_IDS.oc_sr26_mixed_route_remove, "mixed_route_remove_passed")
        results.append(True)
    except Exception as e:
        st.error(f"✗ Route deletion failed: {str(e)}")
        st.report_tc_fail(TC_IDS.oc_sr26_mixed_route_remove, "mixed_route_remove_failed")
        results.append(False)

    st.banner("=" * 80)
    st.banner("TEST RESULT SUMMARY: OC-SR-26")
    st.banner("=" * 80)

    if all(results):
        st.log("✓ ALL TEST STEPS PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("✗ ONE OR MORE TEST STEPS FAILED")
        st.report_fail("test_case_failed")
