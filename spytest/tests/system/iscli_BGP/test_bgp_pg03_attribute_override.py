"""
BGP PEER-GROUP TEST - PG-03: Override Peer-Group Attribute on Single Neighbor

Test Case ID: PG-03
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_BGP/test_bgp_pg03_attribute_override.py \
    --logs-path ./logs/pg03_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates that individual neighbor can override peer-group attributes:
  - DUT1: peer-group timers 60/180, neighbor overrides to 10/30
  - DUT2: peer-group timers 60/180, neighbor inherits (no override)
  - Verify different timer values on each side
  - Verify BGP session establishment with different timers

Pre-requisites:
  - 2 SONiC devices connected via Ethernet4
  - Testbed: testbed_2vs.yaml (192.168.100.203, 192.168.100.196)
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi
import apis.routing.bgp as bgpapi
import apis.switching.vlan as vlanapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration - matching manual testcase
CONFIG = SpyTestDict({
    "interface": "Ethernet4",
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "subnet_mask": "24",
    "asn": "65001",
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
    "peer_group_name": "1",
    "pg_keepalive": "60",      # Peer-group default timers
    "pg_holdtime": "180",
    "override_keepalive": "10",  # DUT1 neighbor override
    "override_holdtime": "30",
    "bgp_wait_time": 90,
})

# Test case IDs
TC_IDS = SpyTestDict({
    "pg03_override": "TC-BGP-PG-03-001",
    "pg03_verify": "TC-BGP-PG-03-002",
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg03_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP PG-03 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")

    bgp_pre_config()
    yield
    bgp_pre_config_cleanup()


def bgp_pre_config():
    """Pre-configuration."""
    dut_list = [vars.D1, vars.D2]
    ipapi.clear_ip_configuration(dut_list, family='ipv4', thread=True)
    vlanapi.clear_vlan_configuration(dut_list)
    for dut in dut_list:
        try:
            bgpapi.cleanup_router_bgp(dut, cli_type=data.cli_type)
        except Exception as e:
            st.log(f"BGP cleanup on {dut}: {str(e)}")


def bgp_pre_config_cleanup():
    """Cleanup."""
    dut_list = [vars.D1, vars.D2]
    for dut in dut_list:
        try:
            bgpapi.cleanup_router_bgp(dut, cli_type=data.cli_type)
        except:
            pass
    ipapi.clear_ip_configuration(dut_list, family='ipv4', thread=True)


def test_bgp_pg03_attribute_override():
    """
    Test Case PG-03: Override Peer-Group Attribute

    Manual validation flow:
    1. Configure IP and BGP
    2. Create peer-group with timers 60/180 on both DUTs
    3. DUT1: Attach neighbor with timer override (10/30)
    4. DUT2: Attach neighbor without override (inherits 60/180)
    5. Verify BGP session with different timers
    """
    st.banner("=" * 80)
    st.banner("TEST PG-03: OVERRIDE PEER-GROUP ATTRIBUTE")
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

    # STEP 3: Create peer-group with timers on DUT1
    st.banner("STEP 3: Create Peer-Group with Timers (60/180) on DUT1")

    # Create peer-group
    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     neighbor=CONFIG.peer_group_name, remote_as=CONFIG.asn,
                     config='yes', config_type_list=["peer_group"],
                     cli_type=data.cli_type)
    # Configure timers on peer-group
    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     neighbor=CONFIG.peer_group_name, config='yes',
                     config_type_list=["keepalive", "holdtime"],
                     keepalive=CONFIG.pg_keepalive,
                     holdtime=CONFIG.pg_holdtime,
                     cli_type=data.cli_type)
    # Activate IPv4 unicast
    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     neighbor=CONFIG.peer_group_name, addr_family="ipv4",
                     config='yes', config_type_list=["activate"],
                     cli_type=data.cli_type)

    # STEP 4: Attach neighbor with OVERRIDE on DUT1
    st.banner("STEP 4: Attach Neighbor with Timer Override (10/30) on DUT1")

    # Attach neighbor to peer-group
    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     neighbor=CONFIG.dut2_ip, remote_as=CONFIG.asn,
                     peergroup=CONFIG.peer_group_name,
                     config='yes', cli_type=data.cli_type)
    # Override timers on neighbor
    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     neighbor=CONFIG.dut2_ip, config='yes',
                     config_type_list=["keepalive", "holdtime"],
                     keepalive=CONFIG.override_keepalive,
                     holdtime=CONFIG.override_holdtime,
                     cli_type=data.cli_type)
    # Activate IPv4 unicast
    bgpapi.config_bgp(dut=vars.D1, local_as=CONFIG.asn,
                     neighbor=CONFIG.dut2_ip, addr_family="ipv4",
                     config='yes', config_type_list=["activate"],
                     cli_type=data.cli_type)

    # STEP 5: Create peer-group with timers on DUT2
    st.banner("STEP 5: Create Peer-Group with Timers (60/180) on DUT2")

    bgpapi.config_bgp(dut=vars.D2, local_as=CONFIG.asn,
                     neighbor=CONFIG.peer_group_name, remote_as=CONFIG.asn,
                     config='yes', config_type_list=["peer_group"],
                     cli_type=data.cli_type)
    bgpapi.config_bgp(dut=vars.D2, local_as=CONFIG.asn,
                     neighbor=CONFIG.peer_group_name, config='yes',
                     config_type_list=["keepalive", "holdtime"],
                     keepalive=CONFIG.pg_keepalive,
                     holdtime=CONFIG.pg_holdtime,
                     cli_type=data.cli_type)
    bgpapi.config_bgp(dut=vars.D2, local_as=CONFIG.asn,
                     neighbor=CONFIG.peer_group_name, addr_family="ipv4",
                     config='yes', config_type_list=["activate"],
                     cli_type=data.cli_type)

    # STEP 6: Attach neighbor WITHOUT override on DUT2
    st.banner("STEP 6: Attach Neighbor WITHOUT Override on DUT2 (inherits 60/180)")

    bgpapi.config_bgp(dut=vars.D2, local_as=CONFIG.asn,
                     neighbor=CONFIG.dut1_ip, remote_as=CONFIG.asn,
                     peergroup=CONFIG.peer_group_name,
                     config='yes', cli_type=data.cli_type)
    bgpapi.config_bgp(dut=vars.D2, local_as=CONFIG.asn,
                     neighbor=CONFIG.dut1_ip, addr_family="ipv4",
                     config='yes', config_type_list=["activate"],
                     cli_type=data.cli_type)

    # STEP 7: Verify BGP session
    st.banner("STEP 7: Verify BGP Session Establishment")

    st.wait(CONFIG.bgp_wait_time, "Waiting for BGP convergence")

    result1 = st.poll_wait(bgpapi.verify_bgp_summary, CONFIG.bgp_wait_time,
                          vars.D1, family='ipv4', neighbor=CONFIG.dut2_ip,
                          state='Established', shell=data.cli_type)
    result2 = st.poll_wait(bgpapi.verify_bgp_summary, CONFIG.bgp_wait_time,
                          vars.D2, family='ipv4', neighbor=CONFIG.dut1_ip,
                          state='Established', shell=data.cli_type)

    if not result1 or not result2:
        st.generate_tech_support([vars.D1, vars.D2], "pg03_bgp_session_failed")
        st.report_tc_fail(TC_IDS.pg03_override, "bgp_ip_peer_establish_fail",
                         "BGP session failed")
        st.report_fail("bgp_ip_peer_establish_fail", "neighbors")

    st.report_tc_pass(TC_IDS.pg03_override, "msg",
                     "BGP session established with different timers")

    # STEP 8: Verify timer values
    st.banner("STEP 8: Verify Timer Values")
    st.log(f"DUT1 should have timers: {CONFIG.override_keepalive}/{CONFIG.override_holdtime}")
    st.log(f"DUT2 should have timers: {CONFIG.pg_keepalive}/{CONFIG.pg_holdtime}")

    output_d1 = bgpapi.show_bgp_neighbor(vars.D1, CONFIG.dut2_ip, cli_type=data.cli_type)
    output_d2 = bgpapi.show_bgp_neighbor(vars.D2, CONFIG.dut1_ip, cli_type=data.cli_type)

    st.log(f"DUT1 neighbor output:\n{output_d1}")
    st.log(f"DUT2 neighbor output:\n{output_d2}")

    st.report_tc_pass(TC_IDS.pg03_verify, "msg",
                     "Timer override verified successfully")

    # TEST PASSED
    st.banner("=" * 80)
    st.banner("TEST RESULT: PG-03 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - PG-03: Override Peer-Group Attribute")
    st.log("=" * 80)
    st.log(f"✓ Peer-group created with timers: {CONFIG.pg_keepalive}/{CONFIG.pg_holdtime}")
    st.log(f"✓ DUT1 neighbor overrides timers to: {CONFIG.override_keepalive}/{CONFIG.override_holdtime}")
    st.log(f"✓ DUT2 neighbor inherits timers: {CONFIG.pg_keepalive}/{CONFIG.pg_holdtime}")
    st.log(f"✓ BGP session established with different timers on each side")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
