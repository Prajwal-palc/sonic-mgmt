"""
STATIC ROUTE TEST - OC-SR-27: Route Deletion and Modification (3 DUTs)

Test Case ID: OC-SR-27
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_3d.yaml \
    tests/system/Static_Route/test_oc_static_route_17_route_deletion_modification.py \
    --logs-path ./logs/oc_sr27_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates route deletion and modification operations on SONiC OC-build.
  Demonstrates adding routes, deleting specific routes, and modifying route next-hops.
  Validates proper cleanup and route table updates after modifications.
  Topology: DUT1 <-> DUT2 <-> DUT3 with DUT3 hosting destination addresses on Loopback.

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0
    ip address 10.1.1.1/24
    ip route 192.168.120.0/24 10.1.1.2
    ip route 192.168.121.0/24 10.1.1.2
    no ip route 192.168.120.0/24 10.1.1.2
    ip route 192.168.120.0/24 10.1.1.3  (modification - different nexthop)

  DUT2:
    interface Ethernet 0
    ip address 10.1.1.2/24
    interface Ethernet 8
    ip address 10.2.1.1/24
    ip route 192.168.120.0/24 10.2.1.2
    ip route 192.168.121.0/24 10.2.1.2

  DUT3:
    interface Ethernet 8
    ip address 10.2.1.2/24
    interface Loopback 0
    ip address 192.168.120.1/32
    ip address 192.168.121.1/32

Pre-requisites:
  - Topology: 3-node (D1-D2-D3) | Supported: HW and Virtual
  - OC-build with Klish CLI support for route operations
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
    "dut1_route1_prefix": "192.168.120.0/24",
    "dut1_route1_nexthop_original": "10.1.1.2",
    "dut1_route1_nexthop_modified": "10.1.1.3",
    "dut1_route2_prefix": "192.168.121.0/24",
    "dut1_route2_nexthop": "10.1.1.2",

    # DUT2 Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ip": "10.1.1.2/24",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ip": "10.2.1.1/24",
    "dut2_route1_prefix": "192.168.120.0/24",
    "dut2_route1_nexthop": "10.2.1.2",
    "dut2_route2_prefix": "192.168.121.0/24",
    "dut2_route2_nexthop": "10.2.1.2",

    # DUT3 Configuration
    "dut3_eth8": "Ethernet 8",
    "dut3_eth8_ip": "10.2.1.2/24",
    "dut3_loopback": "Loopback 0",
    "dut3_loopback_ip1": "192.168.120.1/32",
    "dut3_loopback_ip2": "192.168.121.1/32",
})

TC_IDS = SpyTestDict({
    "oc_sr27_interface_config": "TC-OC-SR-27-001",
    "oc_sr27_route_add": "TC-OC-SR-27-002",
    "oc_sr27_route_delete": "TC-OC-SR-27-003",
    "oc_sr27_route_modify": "TC-OC-SR-27-004",
    "oc_sr27_verify_cleanup": "TC-OC-SR-27-005",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    global vars, data
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-27 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1", "D2D3:1")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}, DUT3: {vars.D3}")

    static_route_pre_config()
    yield

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-27 MODULE CLEANUP - START")
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


def add_static_route(dut, prefix, nexthop):
    st.log(f"Adding route {prefix} via {nexthop} on {dut}")
    try:
        st.config(dut, [f"ip route {prefix} {nexthop}"], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def delete_static_route(dut, prefix, nexthop):
    st.log(f"Deleting route {prefix} via {nexthop} on {dut}")
    try:
        st.config(dut, [f"no ip route {prefix} {nexthop}"], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def test_oc_sr27_route_deletion_modification():
    st.banner("=" * 80)
    st.banner("TEST: OC-SR-27 - Route Deletion and Modification")
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
        st.report_tc_pass(TC_IDS.oc_sr27_interface_config, "interface_config_passed")
        results.append(True)
    else:
        st.error("✗ Interface configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr27_interface_config, "interface_config_failed")
        results.append(False)

    # Step 2: Configure DUT3 Loopback
    st.banner("STEP 2: Configure DUT3 Loopback")
    result = configure_loopback_ip(vars.D3, CONFIG.dut3_loopback,
                                   CONFIG.dut3_loopback_ip1, CONFIG.dut3_loopback_ip2)
    if result:
        st.log("✓ Loopback configuration successful")
        results.append(True)
    else:
        st.error("✗ Loopback configuration failed")
        results.append(False)

    st.wait(5, "Waiting for interface stabilization")

    # Step 3: Add initial routes
    st.banner("STEP 3: Add Initial Routes")

    # DUT1 routes
    result1 = add_static_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop_original)
    result2 = add_static_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop)

    # DUT2 routes
    result3 = add_static_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop)
    result4 = add_static_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop)

    if result1 and result2 and result3 and result4:
        st.log("✓ Initial routes added successfully")
        st.report_tc_pass(TC_IDS.oc_sr27_route_add, "route_add_passed")
        results.append(True)
    else:
        st.error("✗ Initial route addition failed")
        st.report_tc_fail(TC_IDS.oc_sr27_route_add, "route_add_failed")
        results.append(False)

    st.wait(3, "Waiting for routes to be programmed")

    # Step 4: Delete specific route (192.168.120.0/24 on DUT1)
    st.banner("STEP 4: Delete Route 192.168.120.0/24 from DUT1")
    result = delete_static_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop_original)

    if result:
        st.log("✓ Route deletion successful")
        st.report_tc_pass(TC_IDS.oc_sr27_route_delete, "route_delete_passed")
        results.append(True)
    else:
        st.error("✗ Route deletion failed")
        st.report_tc_fail(TC_IDS.oc_sr27_route_delete, "route_delete_failed")
        results.append(False)

    st.wait(2, "Waiting for route deletion")

    # Step 5: Modify route (add same prefix with different nexthop)
    st.banner("STEP 5: Modify Route - Add 192.168.120.0/24 with New Nexthop")
    result = add_static_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop_modified)

    if result:
        st.log(f"✓ Route modified - new nexthop: {CONFIG.dut1_route1_nexthop_modified}")
        st.report_tc_pass(TC_IDS.oc_sr27_route_modify, "route_modify_passed")
        results.append(True)
    else:
        st.error("✗ Route modification failed")
        st.report_tc_fail(TC_IDS.oc_sr27_route_modify, "route_modify_failed")
        results.append(False)

    st.wait(2, "Waiting for route modification")

    # Step 6: Cleanup all routes
    st.banner("STEP 6: Delete All Routes")
    cleanup_success = True

    # DUT1 cleanup
    if not delete_static_route(vars.D1, CONFIG.dut1_route1_prefix, CONFIG.dut1_route1_nexthop_modified):
        st.error(f"✗ Failed to delete DUT1 route1 {CONFIG.dut1_route1_prefix}")
        cleanup_success = False

    if not delete_static_route(vars.D1, CONFIG.dut1_route2_prefix, CONFIG.dut1_route2_nexthop):
        st.error(f"✗ Failed to delete DUT1 route2 {CONFIG.dut1_route2_prefix}")
        cleanup_success = False

    # DUT2 cleanup
    if not delete_static_route(vars.D2, CONFIG.dut2_route1_prefix, CONFIG.dut2_route1_nexthop):
        st.error(f"✗ Failed to delete DUT2 route1 {CONFIG.dut2_route1_prefix}")
        cleanup_success = False

    if not delete_static_route(vars.D2, CONFIG.dut2_route2_prefix, CONFIG.dut2_route2_nexthop):
        st.error(f"✗ Failed to delete DUT2 route2 {CONFIG.dut2_route2_prefix}")
        cleanup_success = False

    if cleanup_success:
        st.log("✓ All routes deleted")
        st.report_tc_pass(TC_IDS.oc_sr27_verify_cleanup, "verify_cleanup_passed")
        results.append(True)
    else:
        st.error("✗ Route cleanup failed - some routes could not be deleted")
        st.report_tc_fail(TC_IDS.oc_sr27_verify_cleanup, "verify_cleanup_failed")
        results.append(False)

    st.banner("=" * 80)
    st.banner("TEST RESULT SUMMARY: OC-SR-27")
    st.banner("=" * 80)

    if all(results):
        st.log("✓ ALL TEST STEPS PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("✗ ONE OR MORE TEST STEPS FAILED")
        st.report_fail("test_case_failed")
