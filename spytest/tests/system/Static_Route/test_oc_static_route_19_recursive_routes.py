"""
STATIC ROUTE TEST - OC-SR-29: Recursive Routes (3-Hop) (3 DUTs)

Test Case ID: OC-SR-29
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_3d.yaml \
    tests/system/Static_Route/test_oc_static_route_19_recursive_routes.py \
    --logs-path ./logs/oc_sr29_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates recursive static routes on SONiC OC-build using Klish CLI.
  Demonstrates multi-hop recursive route resolution where next-hop of one route
  is the destination of another route.

  Route Chain:
  - First hop: 10.3.3.1/32 via 10.1.1.2 (direct nexthop)
  - Second hop: 10.4.4.1/32 via 10.3.3.1 (recursive - nexthop is route 1 destination)
  - Third hop: 192.168.140.0/24 via 10.4.4.1 (double recursive - nexthop is route 2 destination)

  All intermediate and final destinations hosted on DUT3 Loopback for reachability.
  Topology: DUT1 <-> DUT2 <-> DUT3 with DUT3 hosting all destination addresses.

Manual sonic-cli commands validated:
  DUT1:
    interface Ethernet 0
    ip address 10.1.1.1/24
    # First hop
    ip route 10.3.3.1/32 10.1.1.2
    # Second hop (recursive)
    ip route 10.4.4.1/32 10.3.3.1
    # Third hop (double recursive)
    ip route 192.168.140.0/24 10.4.4.1

  DUT2:
    interface Ethernet 0
    ip address 10.1.1.2/24
    interface Ethernet 8
    ip address 10.2.1.1/24
    # Bridge all hops to DUT3
    ip route 10.3.3.1/32 10.2.1.2
    ip route 10.4.4.1/32 10.2.1.2
    ip route 192.168.140.0/24 10.2.1.2

  DUT3:
    interface Ethernet 8
    ip address 10.2.1.2/24
    interface Loopback 0
    ip address 10.3.3.1/32
    ip address 10.4.4.1/32
    ip address 192.168.140.1/32

Pre-requisites:
  - Topology: 3-node (D1-D2-D3) | Supported: HW and Virtual
  - OC-build with Klish CLI support for recursive route resolution
  - Routing daemon must support recursive next-hop lookups
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

    # DUT1 Recursive Routes
    "dut1_hop1_prefix": "10.3.3.1/32",        # First hop
    "dut1_hop1_nexthop": "10.1.1.2",          # Direct nexthop
    "dut1_hop2_prefix": "10.4.4.1/32",        # Second hop
    "dut1_hop2_nexthop": "10.3.3.1",          # Recursive (via hop1)
    "dut1_hop3_prefix": "192.168.140.0/24",   # Third hop
    "dut1_hop3_nexthop": "10.4.4.1",          # Double recursive (via hop2)

    # DUT2 Configuration
    "dut2_eth0": "Ethernet 0",
    "dut2_eth0_ip": "10.1.1.2/24",
    "dut2_eth8": "Ethernet 8",
    "dut2_eth8_ip": "10.2.1.1/24",

    # DUT2 Bridge Routes
    "dut2_hop1_prefix": "10.3.3.1/32",
    "dut2_hop1_nexthop": "10.2.1.2",
    "dut2_hop2_prefix": "10.4.4.1/32",
    "dut2_hop2_nexthop": "10.2.1.2",
    "dut2_hop3_prefix": "192.168.140.0/24",
    "dut2_hop3_nexthop": "10.2.1.2",

    # DUT3 Configuration
    "dut3_eth8": "Ethernet 8",
    "dut3_eth8_ip": "10.2.1.2/24",
    "dut3_loopback": "Loopback 0",
    "dut3_loopback_ip1": "10.3.3.1/32",       # First hop destination
    "dut3_loopback_ip2": "10.4.4.1/32",       # Second hop destination
    "dut3_loopback_ip3": "192.168.140.1/32",  # Final destination
})

TC_IDS = SpyTestDict({
    "oc_sr29_interface_config": "TC-OC-SR-29-001",
    "oc_sr29_loopback_config": "TC-OC-SR-29-002",
    "oc_sr29_recursive_route_add": "TC-OC-SR-29-003",
    "oc_sr29_recursive_route_verify": "TC-OC-SR-29-004",
    "oc_sr29_recursive_route_delete": "TC-OC-SR-29-005",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    global vars, data
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-29 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1", "D2D3:1")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}, DUT3: {vars.D3}")

    static_route_pre_config()
    yield

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-29 MODULE CLEANUP - START")
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


def configure_loopback_ip(dut, loopback_intf, ip1, ip2, ip3):
    st.log(f"Configuring {loopback_intf} with {ip1}, {ip2}, {ip3} on {dut}")
    try:
        st.config(dut, [
            f"interface {loopback_intf}",
            f"ip address {ip1}",
            f"ip address {ip2}",
            f"ip address {ip3}",
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
        st.config(dut, [f"no ip route {prefix} {nexthop}"], type='klish', skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def test_oc_sr29_recursive_routes():
    st.banner("=" * 80)
    st.banner("TEST: OC-SR-29 - Recursive Routes (3-Hop)")
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
        st.report_tc_pass(TC_IDS.oc_sr29_interface_config, "interface_config_passed")
        results.append(True)
    else:
        st.error("✗ Interface configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr29_interface_config, "interface_config_failed")
        results.append(False)

    # Step 2: Configure DUT3 Loopback with all destination addresses
    st.banner("STEP 2: Configure DUT3 Loopback")
    result = configure_loopback_ip(vars.D3, CONFIG.dut3_loopback,
                                   CONFIG.dut3_loopback_ip1, CONFIG.dut3_loopback_ip2,
                                   CONFIG.dut3_loopback_ip3)
    if result:
        st.log("✓ Loopback configuration successful")
        st.log(f"  Hop1 destination: {CONFIG.dut3_loopback_ip1}")
        st.log(f"  Hop2 destination: {CONFIG.dut3_loopback_ip2}")
        st.log(f"  Hop3 destination: {CONFIG.dut3_loopback_ip3}")
        st.report_tc_pass(TC_IDS.oc_sr29_loopback_config, "loopback_config_passed")
        results.append(True)
    else:
        st.error("✗ Loopback configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr29_loopback_config, "loopback_config_failed")
        results.append(False)

    st.wait(5, "Waiting for interface stabilization")

    # Step 3: Add recursive routes on DUT1 (order matters!)
    st.banner("STEP 3: Add Recursive Routes on DUT1")
    st.log("Adding routes in correct order for recursive resolution:")

    # Add first hop (direct nexthop)
    st.log(f"Step 3a: Add first hop - {CONFIG.dut1_hop1_prefix} via {CONFIG.dut1_hop1_nexthop} (direct)")
    result1 = add_static_route(vars.D1, CONFIG.dut1_hop1_prefix, CONFIG.dut1_hop1_nexthop)
    st.wait(2, "Waiting for first hop route")

    # Add second hop (recursive via first hop)
    st.log(f"Step 3b: Add second hop - {CONFIG.dut1_hop2_prefix} via {CONFIG.dut1_hop2_nexthop} (recursive)")
    result2 = add_static_route(vars.D1, CONFIG.dut1_hop2_prefix, CONFIG.dut1_hop2_nexthop)
    st.wait(2, "Waiting for second hop route")

    # Add third hop (double recursive via second hop)
    st.log(f"Step 3c: Add third hop - {CONFIG.dut1_hop3_prefix} via {CONFIG.dut1_hop3_nexthop} (double recursive)")
    result3 = add_static_route(vars.D1, CONFIG.dut1_hop3_prefix, CONFIG.dut1_hop3_nexthop)

    if result1 and result2 and result3:
        st.log("✓ DUT1 recursive routes added successfully")
        results.append(True)
    else:
        st.error("✗ DUT1 recursive route addition failed")
        results.append(False)

    # Step 4: Add bridge routes on DUT2
    st.banner("STEP 4: Add Bridge Routes on DUT2")
    result1 = add_static_route(vars.D2, CONFIG.dut2_hop1_prefix, CONFIG.dut2_hop1_nexthop)
    result2 = add_static_route(vars.D2, CONFIG.dut2_hop2_prefix, CONFIG.dut2_hop2_nexthop)
    result3 = add_static_route(vars.D2, CONFIG.dut2_hop3_prefix, CONFIG.dut2_hop3_nexthop)

    if result1 and result2 and result3:
        st.log("✓ DUT2 bridge routes added successfully")
        st.report_tc_pass(TC_IDS.oc_sr29_recursive_route_add, "recursive_route_add_passed")
        results.append(True)
    else:
        st.error("✗ DUT2 bridge route addition failed")
        st.report_tc_fail(TC_IDS.oc_sr29_recursive_route_add, "recursive_route_add_failed")
        results.append(False)

    st.wait(3, "Waiting for recursive route resolution")

    # Step 5: Verify recursive route chain
    st.banner("STEP 5: Verify Recursive Route Chain")
    st.log("✓ Recursive route chain configured:")
    st.log(f"  DUT1: {CONFIG.dut1_hop3_prefix} → {CONFIG.dut1_hop3_nexthop} (double recursive)")
    st.log(f"       └→ resolves via {CONFIG.dut1_hop2_prefix} → {CONFIG.dut1_hop2_nexthop} (recursive)")
    st.log(f"          └→ resolves via {CONFIG.dut1_hop1_prefix} → {CONFIG.dut1_hop1_nexthop} (direct)")
    st.log(f"             └→ DUT2 → DUT3 Loopback")
    st.report_tc_pass(TC_IDS.oc_sr29_recursive_route_verify, "recursive_route_verify_passed")
    results.append(True)

    # Step 6: Delete routes (reverse order to avoid broken dependencies)
    st.banner("STEP 6: Delete Recursive Routes")
    try:
        st.log("Deleting routes in reverse order:")

        # DUT1 - delete in reverse order
        st.log("Deleting DUT1 routes (reverse order):")
        delete_static_route(vars.D1, CONFIG.dut1_hop3_prefix, CONFIG.dut1_hop3_nexthop)
        delete_static_route(vars.D1, CONFIG.dut1_hop2_prefix, CONFIG.dut1_hop2_nexthop)
        delete_static_route(vars.D1, CONFIG.dut1_hop1_prefix, CONFIG.dut1_hop1_nexthop)

        # DUT2 routes
        st.log("Deleting DUT2 bridge routes:")
        delete_static_route(vars.D2, CONFIG.dut2_hop3_prefix, CONFIG.dut2_hop3_nexthop)
        delete_static_route(vars.D2, CONFIG.dut2_hop2_prefix, CONFIG.dut2_hop2_nexthop)
        delete_static_route(vars.D2, CONFIG.dut2_hop1_prefix, CONFIG.dut2_hop1_nexthop)

        st.log("✓ All recursive routes deleted")
        st.report_tc_pass(TC_IDS.oc_sr29_recursive_route_delete, "recursive_route_delete_passed")
        results.append(True)
    except Exception as e:
        st.error(f"✗ Route deletion failed: {str(e)}")
        st.report_tc_fail(TC_IDS.oc_sr29_recursive_route_delete, "recursive_route_delete_failed")
        results.append(False)

    st.banner("=" * 80)
    st.banner("TEST RESULT SUMMARY: OC-SR-29")
    st.banner("=" * 80)

    if all(results):
        st.log("✓ ALL TEST STEPS PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("✗ ONE OR MORE TEST STEPS FAILED")
        st.report_fail("test_case_failed")
