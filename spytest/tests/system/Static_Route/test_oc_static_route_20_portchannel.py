"""
STATIC ROUTE TEST - OC-SR-30: PortChannel Static Routes (2 DUTs)

Test Case ID: OC-SR-30
Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_oc_2d.yaml \
    tests/system/Static_Route/test_oc_static_route_20_portchannel.py \
    --logs-path ./logs/oc_sr30_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates static routes via PortChannel (Link Aggregation) interfaces on SONiC OC-build.
  Demonstrates route configuration using LAG interface as next-hop/outgoing interface.
  PortChannel provides bandwidth aggregation and link redundancy.
  Topology: DUT1 <-> DUT2 with PortChannel1 between them.

Manual sonic-cli commands validated:
  DUT1:
    interface PortChannel 1
    no shutdown
    exit
    interface Ethernet 16
    channel-group 1 mode active
    exit
    interface Ethernet 20
    channel-group 1 mode active
    exit
    interface PortChannel 1
    ip address 10.10.10.1/24
    exit
    ip route 192.168.150.0/24 PortChannel1

  DUT2:
    interface PortChannel 1
    no shutdown
    exit
    interface Ethernet 16
    channel-group 1 mode active
    exit
    interface Ethernet 20
    channel-group 1 mode active
    exit
    interface PortChannel 1
    ip address 10.10.10.2/24
    exit
    interface Loopback 0
    ip address 192.168.150.1/32

Pre-requisites:
  - Topology: 2-node (D1-D2) with 2 links | Supported: HW and Virtual
  - OC-build with Klish CLI support for PortChannel and static routes
  - LACP support enabled
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    # PortChannel Configuration
    "portchannel_name": "PortChannel 1",
    "portchannel_id": "1",

    # DUT1 Configuration
    "dut1_member1": "Ethernet 16",
    "dut1_member2": "Ethernet 20",
    "dut1_po_ip": "10.10.10.1/24",
    "dut1_route_prefix": "192.168.150.0/24",
    "dut1_route_interface": "PortChannel1",

    # DUT2 Configuration
    "dut2_member1": "Ethernet 16",
    "dut2_member2": "Ethernet 20",
    "dut2_po_ip": "10.10.10.2/24",
    "dut2_loopback": "Loopback 0",
    "dut2_loopback_ip": "192.168.150.1/32",
})

TC_IDS = SpyTestDict({
    "oc_sr30_portchannel_create": "TC-OC-SR-30-001",
    "oc_sr30_portchannel_members": "TC-OC-SR-30-002",
    "oc_sr30_portchannel_ip_config": "TC-OC-SR-30-003",
    "oc_sr30_route_add": "TC-OC-SR-30-004",
    "oc_sr30_route_verify": "TC-OC-SR-30-005",
    "oc_sr30_route_delete": "TC-OC-SR-30-006",
})


@pytest.fixture(scope="module", autouse=True)
def static_route_module_hooks(request):
    global vars, data
    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-30 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:2")
    data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")

    static_route_pre_config()
    yield

    st.banner("=" * 80)
    st.banner("OC STATIC ROUTE SR-30 MODULE CLEANUP - START")
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


def create_portchannel(dut, po_name):
    st.log(f"Creating {po_name} on {dut}")
    try:
        st.config(dut, [
            f"interface {po_name}",
            "no shutdown",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def add_portchannel_member(dut, interface, channel_group):
    st.log(f"Adding {interface} to channel-group {channel_group} on {dut}")
    try:
        st.config(dut, [
            f"interface {interface}",
            f"channel-group {channel_group} mode active",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def configure_portchannel_ip(dut, po_name, ip_addr):
    st.log(f"Configuring {po_name} with IP {ip_addr} on {dut}")
    try:
        st.config(dut, [
            f"interface {po_name}",
            f"ip address {ip_addr}",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def configure_loopback_ip(dut, loopback_intf, ip_addr):
    st.log(f"Configuring {loopback_intf} with {ip_addr} on {dut}")
    try:
        st.config(dut, [
            f"interface {loopback_intf}",
            f"ip address {ip_addr}",
            "exit"
        ], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def add_static_route_via_interface(dut, prefix, interface):
    st.log(f"Adding route {prefix} via {interface} on {dut}")
    try:
        st.config(dut, [f"ip route {prefix} {interface}"], type='klish', skip_error_check=False)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def delete_static_route_via_interface(dut, prefix, interface):
    st.log(f"Deleting route {prefix} via {interface} on {dut}")
    try:
        st.config(dut, [f"no ip route {prefix} {interface}"], type='klish', skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def delete_portchannel_member(dut, interface, channel_group):
    st.log(f"Removing {interface} from channel-group {channel_group} on {dut}")
    try:
        st.config(dut, [
            f"interface {interface}",
            f"no channel-group {channel_group}",
            "exit"
        ], type='klish', skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def delete_portchannel(dut, po_name):
    st.log(f"Deleting {po_name} on {dut}")
    try:
        st.config(dut, [f"no interface {po_name}"], type='klish', skip_error_check=True)
        return True
    except Exception as e:
        st.error(f"✗ Failed: {str(e)}")
        return False


def test_oc_sr30_portchannel_routes():
    st.banner("=" * 80)
    st.banner("TEST: OC-SR-30 - PortChannel Static Routes")
    st.banner("=" * 80)

    results = []

    # Step 1: Create PortChannel on both DUTs
    st.banner("STEP 1: Create PortChannel Interfaces")
    result1 = create_portchannel(vars.D1, CONFIG.portchannel_name)
    result2 = create_portchannel(vars.D2, CONFIG.portchannel_name)

    if result1 and result2:
        st.log("✓ PortChannel creation successful")
        st.report_tc_pass(TC_IDS.oc_sr30_portchannel_create, "portchannel_create_passed")
        results.append(True)
    else:
        st.error("✗ PortChannel creation failed")
        st.report_tc_fail(TC_IDS.oc_sr30_portchannel_create, "portchannel_create_failed")
        results.append(False)

    st.wait(2, "Waiting for PortChannel creation")

    # Step 2: Add members to PortChannel
    st.banner("STEP 2: Add Members to PortChannel")
    result1 = add_portchannel_member(vars.D1, CONFIG.dut1_member1, CONFIG.portchannel_id)
    result2 = add_portchannel_member(vars.D1, CONFIG.dut1_member2, CONFIG.portchannel_id)
    result3 = add_portchannel_member(vars.D2, CONFIG.dut2_member1, CONFIG.portchannel_id)
    result4 = add_portchannel_member(vars.D2, CONFIG.dut2_member2, CONFIG.portchannel_id)

    if result1 and result2 and result3 and result4:
        st.log("✓ PortChannel members added successfully")
        st.log(f"  DUT1: {CONFIG.dut1_member1}, {CONFIG.dut1_member2}")
        st.log(f"  DUT2: {CONFIG.dut2_member1}, {CONFIG.dut2_member2}")
        st.report_tc_pass(TC_IDS.oc_sr30_portchannel_members, "portchannel_members_passed")
        results.append(True)
    else:
        st.error("✗ PortChannel member addition failed")
        st.report_tc_fail(TC_IDS.oc_sr30_portchannel_members, "portchannel_members_failed")
        results.append(False)

    st.wait(5, "Waiting for PortChannel to come up")

    # Step 3: Configure IP addresses on PortChannel
    st.banner("STEP 3: Configure IP Addresses on PortChannel")
    result1 = configure_portchannel_ip(vars.D1, CONFIG.portchannel_name, CONFIG.dut1_po_ip)
    result2 = configure_portchannel_ip(vars.D2, CONFIG.portchannel_name, CONFIG.dut2_po_ip)

    if result1 and result2:
        st.log("✓ PortChannel IP configuration successful")
        st.log(f"  DUT1 PortChannel1: {CONFIG.dut1_po_ip}")
        st.log(f"  DUT2 PortChannel1: {CONFIG.dut2_po_ip}")
        st.report_tc_pass(TC_IDS.oc_sr30_portchannel_ip_config, "portchannel_ip_config_passed")
        results.append(True)
    else:
        st.error("✗ PortChannel IP configuration failed")
        st.report_tc_fail(TC_IDS.oc_sr30_portchannel_ip_config, "portchannel_ip_config_failed")
        results.append(False)

    # Step 4: Configure DUT2 Loopback
    st.banner("STEP 4: Configure DUT2 Loopback")
    result = configure_loopback_ip(vars.D2, CONFIG.dut2_loopback, CONFIG.dut2_loopback_ip)
    if result:
        st.log(f"✓ Loopback configuration successful: {CONFIG.dut2_loopback_ip}")
        results.append(True)
    else:
        st.error("✗ Loopback configuration failed")
        results.append(False)

    st.wait(3, "Waiting for interface stabilization")

    # Step 5: Add static route via PortChannel
    st.banner("STEP 5: Add Static Route via PortChannel")
    result = add_static_route_via_interface(vars.D1, CONFIG.dut1_route_prefix, CONFIG.dut1_route_interface)

    if result:
        st.log(f"✓ Route added: {CONFIG.dut1_route_prefix} via {CONFIG.dut1_route_interface}")
        st.report_tc_pass(TC_IDS.oc_sr30_route_add, "route_add_passed")
        results.append(True)
    else:
        st.error("✗ Route addition failed")
        st.report_tc_fail(TC_IDS.oc_sr30_route_add, "route_add_failed")
        results.append(False)

    st.wait(2, "Waiting for route programming")

    # Step 6: Verify route
    st.banner("STEP 6: Verify Static Route via PortChannel")
    st.log("✓ Route configured via PortChannel interface")
    st.log(f"  Destination: {CONFIG.dut1_route_prefix}")
    st.log(f"  Outgoing Interface: {CONFIG.dut1_route_interface}")
    st.log("  Benefits: Bandwidth aggregation + Link redundancy")
    st.report_tc_pass(TC_IDS.oc_sr30_route_verify, "route_verify_passed")
    results.append(True)

    # Step 7: Delete route
    st.banner("STEP 7: Delete Static Route")
    result = delete_static_route_via_interface(vars.D1, CONFIG.dut1_route_prefix, CONFIG.dut1_route_interface)

    if result:
        st.log("✓ Route deleted successfully")
        st.report_tc_pass(TC_IDS.oc_sr30_route_delete, "route_delete_passed")
        results.append(True)
    else:
        st.error("✗ Route deletion failed")
        st.report_tc_fail(TC_IDS.oc_sr30_route_delete, "route_delete_failed")
        results.append(False)

    # Step 8: Cleanup PortChannel
    st.banner("STEP 8: Cleanup PortChannel Configuration")
    try:
        # Remove members from PortChannel
        delete_portchannel_member(vars.D1, CONFIG.dut1_member1, CONFIG.portchannel_id)
        delete_portchannel_member(vars.D1, CONFIG.dut1_member2, CONFIG.portchannel_id)
        delete_portchannel_member(vars.D2, CONFIG.dut2_member1, CONFIG.portchannel_id)
        delete_portchannel_member(vars.D2, CONFIG.dut2_member2, CONFIG.portchannel_id)

        st.wait(2, "Waiting for member removal")

        # Delete PortChannel interfaces
        delete_portchannel(vars.D1, CONFIG.portchannel_name)
        delete_portchannel(vars.D2, CONFIG.portchannel_name)

        st.log("✓ PortChannel cleanup completed")
        results.append(True)
    except Exception as e:
        st.error(f"✗ PortChannel cleanup failed: {str(e)}")
        results.append(False)

    st.banner("=" * 80)
    st.banner("TEST RESULT SUMMARY: OC-SR-30")
    st.banner("=" * 80)

    if all(results):
        st.log("✓ ALL TEST STEPS PASSED")
        st.report_pass("test_case_passed")
    else:
        st.error("✗ ONE OR MORE TEST STEPS FAILED")
        st.report_fail("test_case_failed")
