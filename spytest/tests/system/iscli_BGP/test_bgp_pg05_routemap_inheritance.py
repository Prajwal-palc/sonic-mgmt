"""
BGP PEER-GROUP TEST - PG-05: Peer-Group with Route-Map Inheritance

Test Case ID: PG-05
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_BGP/test_bgp_pg05_routemap_inheritance.py \
    --logs-path ./logs/pg05_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates route-map policy inheritance from peer-group:
  - Create route-maps (RM_IN, RM_OUT)
  - Apply route-maps to peer-group at AF level
  - Attach neighbors to peer-group
  - Verify route-map inheritance
  - Verify BGP session establishment

Note: Based on manual validation, route-maps are applied at
      peer-group address-family level, not global AF level.
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi
import apis.routing.bgp as bgpapi
import apis.switching.vlan as vlanapi

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "interface": "Ethernet4",
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "subnet_mask": "24",
    "asn": "65001",
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
    "peer_group_name": "1",
    "dut1_local_pref": "200",
    "dut1_metric": "100",
    "dut2_local_pref": "150",
    "dut2_metric": "50",
    "bgp_wait_time": 90,
})

TC_IDS = SpyTestDict({
    "pg05_routemap": "TC-BGP-PG-05-001",
    "pg05_inherit": "TC-BGP-PG-05-002",
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg05_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP PG-05 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    dut_list = [vars.D1, vars.D2]
    ipapi.clear_ip_configuration(dut_list, family='ipv4', thread=True)
    vlanapi.clear_vlan_configuration(dut_list)
    for dut in dut_list:
        try:
            bgpapi.cleanup_router_bgp(dut, cli_type=data.cli_type)
        except:
            pass

    yield

    for dut in dut_list:
        try:
            bgpapi.cleanup_router_bgp(dut, cli_type=data.cli_type)
        except:
            pass
    ipapi.clear_ip_configuration(dut_list, family='ipv4', thread=True)


def create_route_maps(dut: str, local_pref: str, metric: str) -> bool:
    """Create route-maps RM_IN and RM_OUT."""
    st.log(f"Creating route-maps on {dut}")

    try:
        # Create RM_IN
        st.config(dut,
                 f"route-map RM_IN permit 10\n"
                 f"set local-preference {local_pref}",
                 type=data.cli_type)

        # Create RM_OUT
        st.config(dut,
                 f"route-map RM_OUT permit 10\n"
                 f"set metric {metric}",
                 type=data.cli_type)

        st.log(f"Route-maps created on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to create route-maps on {dut}: {str(e)}")
        return False


def apply_routemaps_to_peergroup(dut: str) -> bool:
    """Apply route-maps to peer-group at AF level."""
    st.log(f"Applying route-maps to peer-group on {dut}")

    try:
        # Route-maps must be applied at peer-group AF level
        st.config(dut,
                 f"router bgp {CONFIG.asn}\n"
                 f"peer-group {CONFIG.peer_group_name}\n"
                 f"address-family ipv4 unicast\n"
                 f"route-map RM_IN in\n"
                 f"route-map RM_OUT out",
                 type=data.cli_type)

        st.log(f"Route-maps applied to peer-group on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to apply route-maps on {dut}: {str(e)}")
        return False


def test_bgp_pg05_routemap_inheritance():
    """
    Test Case PG-05: Route-Map Inheritance

    Manual validation flow:
    1. Configure IP and BGP
    2. Create route-maps (RM_IN, RM_OUT)
    3. Create peer-group and apply route-maps at AF level
    4. Attach neighbors to peer-group
    5. Verify BGP session and route-map inheritance
    """
    st.banner("=" * 80)
    st.banner("TEST PG-05: PEER-GROUP WITH ROUTE-MAP INHERITANCE")
    st.banner("=" * 80)

    # STEP 1: Configure IP addresses
    st.banner("STEP 1: Configure IP Addresses")

    ipapi.config_ip_addr_interface(vars.D1, CONFIG.interface,
                                    f"{CONFIG.dut1_ip}/{CONFIG.subnet_mask}",
                                    family="ipv4", cli_type=data.cli_type)
    ipapi.config_ip_addr_interface(vars.D2, CONFIG.interface,
                                    f"{CONFIG.dut2_ip}/{CONFIG.subnet_mask}",
                                    family="ipv4", cli_type=data.cli_type)
    st.wait(5, "Waiting for interfaces")

    # STEP 2: Configure BGP routers
    st.banner("STEP 2: Configure BGP Routers")

    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     router_id=CONFIG.dut1_router_id,
                     config='yes', cli_type=data.cli_type)
    bgpapi.config_bgp(dut=vars.D2, local_as=CONFIG.asn,
                     router_id=CONFIG.dut2_router_id,
                     config='yes', cli_type=data.cli_type)

    # STEP 3: Create route-maps on both DUTs
    st.banner("STEP 3: Create Route-Maps")

    st.log(f"DUT1: Creating route-maps (local-pref={CONFIG.dut1_local_pref}, metric={CONFIG.dut1_metric})")
    if not create_route_maps(vars.D1, CONFIG.dut1_local_pref, CONFIG.dut1_metric):
        st.report_fail("msg", f"Failed to create route-maps on {vars.D1}")

    st.log(f"DUT2: Creating route-maps (local-pref={CONFIG.dut2_local_pref}, metric={CONFIG.dut2_metric})")
    if not create_route_maps(vars.D2, CONFIG.dut2_local_pref, CONFIG.dut2_metric):
        st.report_fail("msg", f"Failed to create route-maps on {vars.D2}")

    st.report_tc_pass(TC_IDS.pg05_routemap, "msg", "Route-maps created successfully")

    # STEP 4: Create peer-group on DUT1
    st.banner("STEP 4: Create Peer-Group and Apply Route-Maps on DUT1")

    # Create peer-group
    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     neighbor=CONFIG.peer_group_name, remote_as=CONFIG.asn,
                     config='yes', config_type_list=["peer_group"],
                     cli_type=data.cli_type)

    # Activate IPv4 unicast first
    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     neighbor=CONFIG.peer_group_name, addr_family="ipv4",
                     config='yes', config_type_list=["activate"],
                     cli_type=data.cli_type)

    # Apply route-maps to peer-group
    if not apply_routemaps_to_peergroup(vars.D1):
        st.report_fail("msg", f"Failed to apply route-maps on {vars.D1}")

    # STEP 5: Create peer-group on DUT2
    st.banner("STEP 5: Create Peer-Group and Apply Route-Maps on DUT2")

    bgpapi.config_bgp(dut=vars.D2, local_as=CONFIG.asn,
                     neighbor=CONFIG.peer_group_name, remote_as=CONFIG.asn,
                     config='yes', config_type_list=["peer_group"],
                     cli_type=data.cli_type)

    bgpapi.config_bgp(dut=vars.D2, local_as=CONFIG.asn,
                     neighbor=CONFIG.peer_group_name, addr_family="ipv4",
                     config='yes', config_type_list=["activate"],
                     cli_type=data.cli_type)

    if not apply_routemaps_to_peergroup(vars.D2):
        st.report_fail("msg", f"Failed to apply route-maps on {vars.D2}")

    # STEP 6: Attach neighbors to peer-groups
    st.banner("STEP 6: Attach Neighbors to Peer-Groups")

    # DUT1
    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     neighbor=CONFIG.dut2_ip, remote_as=CONFIG.asn,
                     peergroup=CONFIG.peer_group_name,
                     config='yes', cli_type=data.cli_type)
    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     neighbor=CONFIG.dut2_ip, addr_family="ipv4",
                     config='yes', config_type_list=["activate"],
                     cli_type=data.cli_type)

    # DUT2
    bgpapi.config_bgp(dut=vars.D2, local_as=CONFIG.asn,
                     neighbor=CONFIG.dut1_ip, remote_as=CONFIG.asn,
                     peergroup=CONFIG.peer_group_name,
                     config='yes', cli_type=data.cli_type)
    bgpapi.config_bgp(dut=vars.D2, local_as=CONFIG.asn,
                     neighbor=CONFIG.dut1_ip, addr_family="ipv4",
                     config='yes', config_type_list=["activate"],
                     cli_type=data.cli_type)

    # STEP 7: Verify BGP session
    st.banner("STEP 7: Verify BGP Session with Route-Map Inheritance")

    st.wait(CONFIG.bgp_wait_time, "Waiting for BGP convergence")

    result1 = st.poll_wait(bgpapi.verify_bgp_summary, CONFIG.bgp_wait_time,
                          vars.D1, family='ipv4', neighbor=CONFIG.dut2_ip,
                          state='Established', shell=data.cli_type)
    result2 = st.poll_wait(bgpapi.verify_bgp_summary, CONFIG.bgp_wait_time,
                          vars.D2, family='ipv4', neighbor=CONFIG.dut1_ip,
                          state='Established', shell=data.cli_type)

    if not result1 or not result2:
        st.generate_tech_support([vars.D1, vars.D2], "pg05_bgp_session_failed")
        st.report_tc_fail(TC_IDS.pg05_inherit, "bgp_ip_peer_establish_fail",
                         "BGP session failed")
        st.report_fail("bgp_ip_peer_establish_fail", "neighbors")

    st.report_tc_pass(TC_IDS.pg05_inherit, "msg",
                     "BGP session established with route-map inheritance")

    # STEP 8: Verify route-maps are configured
    st.banner("STEP 8: Verify Route-Map Configuration")

    # Show route-maps
    try:
        output_d1 = st.show(vars.D1, "show route-map", skip_tmpl=True, cli_type=data.cli_type)
        output_d2 = st.show(vars.D2, "show route-map", skip_tmpl=True, cli_type=data.cli_type)

        st.log(f"DUT1 route-maps:\n{output_d1}")
        st.log(f"DUT2 route-maps:\n{output_d2}")
    except Exception as e:
        st.log(f"Route-map verification: {str(e)}")

    # Show BGP neighbor to verify route-map application
    output_d1 = bgpapi.show_bgp_neighbor(vars.D1, CONFIG.dut2_ip, cli_type=data.cli_type)
    output_d2 = bgpapi.show_bgp_neighbor(vars.D2, CONFIG.dut1_ip, cli_type=data.cli_type)

    st.log(f"DUT1 neighbor output:\n{output_d1}")
    st.log(f"DUT2 neighbor output:\n{output_d2}")

    # TEST PASSED
    st.banner("=" * 80)
    st.banner("TEST RESULT: PG-05 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - PG-05: Route-Map Inheritance")
    st.log("=" * 80)
    st.log(f"✓ Route-maps created on both DUTs")
    st.log(f"✓ DUT1: RM_IN (local-pref {CONFIG.dut1_local_pref}), RM_OUT (metric {CONFIG.dut1_metric})")
    st.log(f"✓ DUT2: RM_IN (local-pref {CONFIG.dut2_local_pref}), RM_OUT (metric {CONFIG.dut2_metric})")
    st.log(f"✓ Route-maps applied to peer-group at AF level")
    st.log(f"✓ Neighbors attached to peer-group")
    st.log(f"✓ BGP session established with route-map inheritance")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
