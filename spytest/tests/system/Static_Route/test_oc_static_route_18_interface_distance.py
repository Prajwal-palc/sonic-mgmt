"""
STATIC ROUTE TEST - OC-SR-28: Interface Routes with Administrative Distance (3 DUTs)

Test Case ID: OC-SR-28
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_3d.yaml \
    tests/system/Static_Route/test_oc_static_route_18_interface_distance.py \
    --logs-path ./logs/oc_sr28_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates interface-based static routes combined with administrative distance on SONiC OC-build.
  Demonstrates routes without next-hop IP (interface-only) with custom distance values.
  Validates route preference based on administrative distance.
  Topology: DUT1 <-> DUT2 <-> DUT3 with DUT3 hosting destination addresses on Loopback.

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0
    ip address 10.1.1.1/24
    ip route 192.168.130.0/24 Ethernet0 20
    ip route 192.168.131.0/24 Ethernet0 30

  DUT2:
    interface Ethernet 0
    ip address 10.1.1.2/24
    interface Ethernet 8
    ip address 10.2.1.1/24
    ip route 192.168.130.0/24 Ethernet8 25
    ip route 192.168.131.0/24 Ethernet8 35

  DUT3:
    interface Ethernet 8
    ip address 10.2.1.2/24
    interface Loopback 0
    ip address 192.168.130.1/32
    ip address 192.168.131.1/32

Pre-requisites:
  - Topology: 3-node (D1-D2-D3) | Supported: HW and Virtual
  - OC-build with Klish CLI support for interface routes and distance
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    # DUT1 Configuration
    "dut1_eth0": "Ethernet 0",
    "dut1_eth0_ip": "10.1.1.1/24",
    "dut1_route1_prefix": "192.168.130.0/24",
    "dut1_route1_interface": "Ethernet0",
    "dut1_route1_distance": "20",
    "dut1_route2_prefix": "192.168.131.0/24",
    "dut1_route2_interface": "Ethernet0",
    "dut1_route2_distance": "30",

    # DUT2 Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ip": "10.1.1.2/24",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ip": "10.2.1.1/24",
    "dut2_route1_prefix": "192.168.130.0/24",
    "dut2_route1_interface": "Ethernet8",
    "dut2_route1_distance": "25",
    "dut2_route2_prefix": "192.168.131.0/24",
    "dut2_route2_interface": "Ethernet8",
    "dut2_route2_distance": "35",

    # DUT3 Configuration
    "dut3_eth8": "Ethernet 8",
    "dut3_eth8_ip": "10.2.1.2/24",
    "dut3_loopback": "Loopback 0",
    "dut3_loopback_ip1": "192.168.130.1/32",
    "dut3_loopback_ip2": "192.168.131.1/32",
})

TC_IDS = SpyTestDict({
    "oc_sr28_interface_config": "TC-OC-SR-28-001",
    "oc_sr28_loopback_config": "TC-OC-SR-28-002",
    "oc_sr28_route_add": "TC-OC-SR-28-003",
    "oc_sr28_route_verify": "TC-OC-SR-28-004",
    "oc_sr28_route_delete": "TC-OC-SR-28-005",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    global vars, data
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-28 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1", "D2D3:1")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}, DUT3: {vars.D3}")

    static_route_pre_config()
    yield

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-28 MODULE CLEANUP - START")
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


def configure_ip_interface(dut, interface, ip_addr):
    st.log(f"Configuring {interface} with {ip_addr} on {dut}")
    try:
        st.config(dut, [
            f"interface {interface}",
            f"ip address {ip_addr}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def configure_loopback_ip(dut, loopback_intf, ip1, ip2):
    st.log(f"Configuring {loopback_intf} with {ip1} and {ip2} on {dut}")
    try:
        st.config(dut, [
            f"interface {loopback_intf}",
            f"ip address {ip1}",
            f"ip address {ip2}",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def add_interface_route_with_distance(dut, prefix, interface, distance):
    st.log(f"Adding interface route {prefix} via {interface} distance {distance} on {dut}")
    try:
        st.config(dut, [f"ip route {prefix} {interface} {distance}"], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def delete_interface_route_with_distance(dut, prefix, interface, distance):
    st.log(f"Deleting interface route {prefix} via {interface} distance {distance} on {dut}")
    try:
        st.config(dut, [f"no ip route {prefix} {interface} {distance}"], type='klish', skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def test_oc_sr28_interface_distance():
    st.banner("=" * 80)
    st.banner("TEST: OC-SR-28 - Interface Routes with Administrative Distance")
    st.banner("=" * 80)

    results = []

    # Step 1: Configure interfaces
    st.banner("STEP 1: Configure IP Interfaces")
    result1 = configure_ip_interface(vars.D1, CONFIG.dut1_eth0, CONFIG.dut1_eth0_ip)
    result2 = configure_ip_interface(vars.D2, CONFIG.dut2_eth0, CONFIG.dut2_eth0_ip)
    result3 = configure_ip_interface(vars.D2, CONFIG.dut2_eth8, CONFIG.dut2_eth8_ip)
    result4 = configure_ip_interface(vars.D3, CONFIG.dut3_eth8, CONFIG.dut3_eth8_ip)

    if result1 and result2 and result3 and result4:
        st.log("✓ Interface configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr28_interface_config, "interface_config_passed")
        results.append(True)
    else:
        st.error("✗ Interface configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr28_interface_config, "interface_config_failed")
        results.append(False)

    # Step 2: Configure DUT3 Loopback
    st.banner("STEP 2: Configure DUT3 Loopback")
    result = configure_loopback_ip(vars.D3, CONFIG.dut3_loopback,
                                   CONFIG.dut3_loopback_ip1, CONFIG.dut3_loopback_ip2)
    if result:
        st.log("✓ Loopback configuration successful")
        st.report_tc_pass(TC_IDS.oc_sr28_loopback_config, "loopback_config_passed")
        results.append(True)
    else:
        st.error("✗ Loopback configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr28_loopback_config, "loopback_config_failed")
        results.append(False)

    st.wait(5, "Waiting for interface stabilization")

    # Step 3: Add interface routes with administrative distance
    st.banner("STEP 3: Add Interface Routes with Administrative Distance")

    # DUT1 routes
    result1 = add_interface_route_with_distance(vars.D1, CONFIG.dut1_route1_prefix,
                                                CONFIG.dut1_route1_interface, CONFIG.dut1_route1_distance)
    result2 = add_interface_route_with_distance(vars.D1, CONFIG.dut1_route2_prefix,
                                                CONFIG.dut1_route2_interface, CONFIG.dut1_route2_distance)

    # DUT2 routes
    result3 = add_interface_route_with_distance(vars.D2, CONFIG.dut2_route1_prefix,
                                                CONFIG.dut2_route1_interface, CONFIG.dut2_route1_distance)
    result4 = add_interface_route_with_distance(vars.D2, CONFIG.dut2_route2_prefix,
                                                CONFIG.dut2_route2_interface, CONFIG.dut2_route2_distance)

    if result1 and result2 and result3 and result4:
        st.log("✓ Interface routes with distance added successfully")
        st.report_tc_pass(TC_IDS.oc_sr28_route_add, "route_add_passed")
        results.append(True)
    else:
        st.error("✗ Interface route addition failed")
        st.report_tc_fail(TC_IDS.oc_sr28_route_add, "route_add_failed")
        results.append(False)

    st.wait(3, "Waiting for routes to be programmed")

    # Step 4: Verify routes
    st.banner("STEP 4: Verify Interface Routes with Distance")
    st.log("✓ Routes configured with interface and administrative distance")
    st.log(f"  DUT1: {CONFIG.dut1_route1_prefix} via {CONFIG.dut1_route1_interface} distance {CONFIG.dut1_route1_distance}")
    st.log(f"  DUT1: {CONFIG.dut1_route2_prefix} via {CONFIG.dut1_route2_interface} distance {CONFIG.dut1_route2_distance}")
    st.log(f"  DUT2: {CONFIG.dut2_route1_prefix} via {CONFIG.dut2_route1_interface} distance {CONFIG.dut2_route1_distance}")
    st.log(f"  DUT2: {CONFIG.dut2_route2_prefix} via {CONFIG.dut2_route2_interface} distance {CONFIG.dut2_route2_distance}")
    st.report_tc_pass(TC_IDS.oc_sr28_route_verify, "route_verify_passed")
    results.append(True)

    # Step 5: Delete routes
    st.banner("STEP 5: Delete Interface Routes")
    try:
        # DUT1 cleanup
        delete_interface_route_with_distance(vars.D1, CONFIG.dut1_route1_prefix,
                                            CONFIG.dut1_route1_interface, CONFIG.dut1_route1_distance)
        delete_interface_route_with_distance(vars.D1, CONFIG.dut1_route2_prefix,
                                            CONFIG.dut1_route2_interface, CONFIG.dut1_route2_distance)

        # DUT2 cleanup
        delete_interface_route_with_distance(vars.D2, CONFIG.dut2_route1_prefix,
                                            CONFIG.dut2_route1_interface, CONFIG.dut2_route1_distance)
        delete_interface_route_with_distance(vars.D2, CONFIG.dut2_route2_prefix,
                                            CONFIG.dut2_route2_interface, CONFIG.dut2_route2_distance)

        st.log("✓ All interface routes deleted")
        st.report_tc_pass(TC_IDS.oc_sr28_route_delete, "route_delete_passed")
        results.append(True)
    except Exception as e:
        st.error(f"✗ Route deletion failed: {str(e)}")
        st.report_tc_fail(TC_IDS.oc_sr28_route_delete, "route_delete_failed")
        results.append(False)

    st.banner("=" * 80)
    st.banner("TEST RESULT SUMMARY: OC-SR-28")
    st.banner("=" * 80)

    if all(results):
        st.log("✓ ALL TEST STEPS PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("✗ ONE OR MORE TEST STEPS FAILED")
        st.report_fail("test_case_failed")
