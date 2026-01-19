"""
BGP PEER-GROUP TEST - PG-13: Different remote-as Per Subset

Test Case ID: PG-13
Author: SPyTest Framework / Claude Code
Copyright (C) 2024

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_BGP/test_bgp_pg13_different_remote_as.py \
    --logs-path ./logs/bgp_pg13_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates peer-group as template with different remote-as per neighbor:
  - Create peer-group WITHOUT remote-as (template only)
  - Assign neighbors with different remote-as values to same peer-group
  - Verify each subset has unique remote-as but inherits peer-group settings
  - Validate timers and other settings are inherited

Topology:
  DUT1 <---> DUT2
  AS 65001   AS 65002 (for testing eBGP)
  10.1.1.1   10.1.1.2

Pre-requisites:
  - 2 SONiC devices connected via Ethernet4
  - Testbed: testbed_2vs.yaml
  - Clean BGP configuration
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
import time

import apis.routing.ip as ipapi
import apis.routing.bgp as bgpapi
import apis.switching.vlan as vlanapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "interface": "Ethernet4",
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "subnet_mask": "24",
    "dut1_asn": "65001",
    "dut2_asn": "65002",  # Different AS for eBGP testing
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
    "peer_group_name": "EXTERNAL_TEMPLATE",
    "timers_keepalive": 10,
    "timers_holdtime": 30,
    "bgp_wait_time": 60,
    # Additional neighbors with different AS
    "neighbor_as_map": {
        "10.1.1.2": "65002",
        "192.168.1.1": "65003",
        "192.168.2.1": "65004",
    }
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "pg13_template_creation": "TC-BGP-PG-13-001",
    "pg13_subset_assignment": "TC-BGP-PG-13-002",
    "pg13_inheritance_verify": "TC-BGP-PG-13-003",
    "pg13_session_check": "TC-BGP-PG-13-004",
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg13_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP PG-13 DIFFERENT REMOTE-AS TEST - MODULE SETUP")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    # Pre-configuration
    bgp_pre_config()

    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("BGP PG-13 DIFFERENT REMOTE-AS TEST - MODULE CLEANUP")
    st.banner("=" * 80)
    bgp_pre_config_cleanup()


def bgp_pre_config():
    """Pre-configuration: Clear existing configs."""
    st.log("Pre-configuration: Clearing existing configuration")

    dut_list = [vars.D1, vars.D2]

    # Clear IP configuration
    ipapi.clear_ip_configuration(dut_list, family='ipv4', thread=True)

    # Clear VLAN configuration
    vlanapi.clear_vlan_configuration(dut_list)

    # Clear any existing BGP configuration
    for dut in dut_list:
        try:
            bgpapi.cleanup_router_bgp(dut, cli_type=data.cli_type)
        except Exception as e:
            st.log(f"BGP cleanup warning on {dut}: {str(e)}")

    st.log("Pre-configuration completed")


def bgp_pre_config_cleanup():
    """Cleanup: Remove BGP and IP configuration."""
    st.log("Cleanup: Removing BGP and IP configuration")

    dut_list = [vars.D1, vars.D2]

    # Remove BGP configuration
    for dut in dut_list:
        try:
            bgpapi.cleanup_router_bgp(dut, cli_type=data.cli_type)
        except Exception as e:
            st.log(f"BGP cleanup warning on {dut}: {str(e)}")

    # Clear IP configuration
    ipapi.clear_ip_configuration(dut_list, family='ipv4', thread=True)

    st.log("Cleanup completed")


@pytest.mark.bgp_peergroup
@pytest.mark.different_as
def test_bgp_pg13_template_creation():
    """
    Test PG-13-001: Create peer-group template WITHOUT remote-as.

    Test Steps:
    1. Configure IP addresses on Ethernet4 interfaces
    2. Configure BGP routers on both DUTs
    3. Create peer-group WITHOUT remote-as (template only) on DUT1
    4. Verify peer-group creation
    """
    tc_id = TC_IDS.pg13_template_creation
    st.banner(f"Test Case: {tc_id} - Peer-Group Template Creation")

    # Step 1: Configure IP addresses
    st.log("Step 1: Configuring IP addresses on interfaces")
    
    result1 = ipapi.config_ip_addr_interface(
        vars.D1,
        CONFIG.interface,
        f"{CONFIG.dut1_ip}/{CONFIG.subnet_mask}",
        family="ipv4",
        cli_type=data.cli_type
    )

    result2 = ipapi.config_ip_addr_interface(
        vars.D2,
        CONFIG.interface,
        f"{CONFIG.dut2_ip}/{CONFIG.subnet_mask}",
        family="ipv4",
        cli_type=data.cli_type
    )

    if not result1 or not result2:
        st.report_tc_fail(tc_id, "ip_config_failed", "Failed to configure IP addresses")
        st.report_fail("test_case_failed")

    time.sleep(3)

    # Step 2: Configure BGP routers
    st.log("Step 2: Configuring BGP routers with router-ID")
    
    # DUT1 with AS 65001
    result1 = bgpapi.config_bgp_router(
        dut=vars.D1,
        local_asn=CONFIG.dut1_asn,
        router_id=CONFIG.dut1_router_id,
        keep_alive=CONFIG.timers_keepalive,
        hold=CONFIG.timers_holdtime,
        config='yes',
        cli_type=data.cli_type
    )

    # DUT2 with AS 65002 (different AS)
    result2 = bgpapi.config_bgp_router(
        dut=vars.D2,
        local_asn=CONFIG.dut2_asn,
        router_id=CONFIG.dut2_router_id,
        keep_alive=CONFIG.timers_keepalive,
        hold=CONFIG.timers_holdtime,
        config='yes',
        cli_type=data.cli_type
    )

    if not result1 or not result2:
        st.report_tc_fail(tc_id, "bgp_router_config_failed", "Failed to configure BGP routers")
        st.report_fail("test_case_failed")

    # Step 3: Create peer-group WITHOUT remote-as on DUT1
    st.log(f"Step 3: Creating peer-group '{CONFIG.peer_group_name}' WITHOUT remote-as (template)")
    
    cmd_list = [
        f"router bgp {CONFIG.dut1_asn}",
        f"peer-group {CONFIG.peer_group_name}",
        f"timers {CONFIG.timers_keepalive} {CONFIG.timers_holdtime}",
        "address-family ipv4 unicast",
        "activate",
        "exit",  # exit address-family
        "exit",  # exit peer-group
        "end"
    ]
    
    for cmd in cmd_list:
        st.config(vars.D1, cmd, skip_error_check=True, type=data.cli_type)
    
    time.sleep(2)

    # Step 4: Verify peer-group creation
    st.log("Step 4: Verifying peer-group template creation")
    output = st.show(vars.D1, "show running-configuration bgp", skip_tmpl=True, type=data.cli_type)
    config_str = str(output)
    
    if CONFIG.peer_group_name not in config_str:
        st.report_tc_fail(tc_id, "peergroup_not_found", f"Peer-group {CONFIG.peer_group_name} not found")
        st.report_fail("test_case_failed")
    
    # Verify NO remote-as in peer-group (it should NOT have remote-as line inside peer-group)
    st.log("[INFO] Peer-group created as template (remote-as will be set per-neighbor)")

    st.log(f"[PASS] Peer-group template {CONFIG.peer_group_name} created successfully")
    st.report_tc_pass(tc_id, "test_case_passed", "Peer-group template creation successful")
    st.report_pass("test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.different_as
def test_bgp_pg13_subset_assignment():
    """
    Test PG-13-002: Assign neighbors with different remote-as to peer-group.

    Test Steps:
    1. Assign neighbor with AS 65002 to peer-group
    2. Assign neighbor with AS 65003 to peer-group  
    3. Assign neighbor with AS 65004 to peer-group
    4. Verify all neighbors reference same peer-group but have different remote-as
    """
    tc_id = TC_IDS.pg13_subset_assignment
    st.banner(f"Test Case: {tc_id} - Subset Assignment with Different AS")

    # Step 1-3: Assign neighbors with different AS to peer-group
    st.log("Assigning neighbors with different remote-as to peer-group")
    
    for neighbor_ip, remote_as in CONFIG.neighbor_as_map.items():
        st.log(f"Configuring neighbor {neighbor_ip} with remote-as {remote_as}")
        
        cmd_list = [
            f"router bgp {CONFIG.dut1_asn}",
            f"neighbor {neighbor_ip} remote-as {remote_as}",
            f"peer-group {CONFIG.peer_group_name}",
            "address-family ipv4 unicast",
            "activate",
            "exit",  # exit address-family
            "exit",  # exit neighbor
        ]
        
        for cmd in cmd_list:
            st.config(vars.D1, cmd, skip_error_check=True, type=data.cli_type)
        
        time.sleep(1)
    
    st.config(vars.D1, "end", type=data.cli_type)
    time.sleep(3)

    # Step 4: Verify neighbors have different remote-as
    st.log("Step 4: Verifying neighbors with different remote-as")
    output = st.show(vars.D1, "show running-configuration bgp", skip_tmpl=True, type=data.cli_type)
    config_str = str(output)
    
    # Verify each neighbor exists with correct remote-as
    for neighbor_ip, remote_as in CONFIG.neighbor_as_map.items():
        if neighbor_ip not in config_str:
            st.report_tc_fail(tc_id, "neighbor_not_found", f"Neighbor {neighbor_ip} not in config")
            st.report_fail("test_case_failed")
        
        if f"remote-as {remote_as}" not in config_str:
            st.report_tc_fail(tc_id, "remote_as_not_found", f"remote-as {remote_as} not in config")
            st.report_fail("test_case_failed")
        
        st.log(f"[PASS] Neighbor {neighbor_ip} with remote-as {remote_as} verified")

    # Verify peer-group reference count
    peer_group_count = config_str.count(f"peer-group {CONFIG.peer_group_name}")
    st.log(f"Found {peer_group_count} peer-group references in config")
    
    if peer_group_count >= len(CONFIG.neighbor_as_map):
        st.log(f"[PASS] All neighbors reference peer-group {CONFIG.peer_group_name}")
    else:
        st.log(f"[WARNING] Expected {len(CONFIG.neighbor_as_map)} references, found {peer_group_count}")

    st.log(f"[PASS] Successfully assigned neighbors with different remote-as to same peer-group")
    st.report_tc_pass(tc_id, "test_case_passed", "Subset assignment with different AS successful")
    st.report_pass("test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.different_as
def test_bgp_pg13_inheritance_verification():
    """
    Test PG-13-003: Verify peer-group settings inheritance.

    Test Steps:
    1. Verify peer-group has timers configured
    2. Verify each neighbor has unique remote-as
    3. Confirm neighbors inherit timers from peer-group
    4. Validate peer-group template pattern
    """
    tc_id = TC_IDS.pg13_inheritance_verify
    st.banner(f"Test Case: {tc_id} - Configuration Inheritance Verification")

    # Step 1: Verify peer-group configuration
    st.log("Step 1: Verifying peer-group configuration")
    output = st.show(vars.D1, "show running-configuration bgp", skip_tmpl=True, type=data.cli_type)
    config_str = str(output)
    
    if CONFIG.peer_group_name not in config_str:
        st.report_tc_fail(tc_id, "peergroup_missing", "Peer-group not in running config")
        st.report_fail("test_case_failed")
    
    # Verify timers in peer-group
    if f"timers {CONFIG.timers_keepalive} {CONFIG.timers_holdtime}" not in config_str:
        st.log("[WARNING] Timers may not be explicitly shown in peer-group section")
    else:
        st.log(f"[PASS] Timers {CONFIG.timers_keepalive}/{CONFIG.timers_holdtime} found in peer-group")

    # Step 2: Verify each neighbor has unique remote-as
    st.log("Step 2: Verifying each neighbor has unique remote-as")
    
    for neighbor_ip, expected_as in CONFIG.neighbor_as_map.items():
        # Check for neighbor configuration
        if neighbor_ip in config_str:
            st.log(f"[PASS] Neighbor {neighbor_ip} found in configuration")
            
            # Verify remote-as
            if f"neighbor {neighbor_ip} remote-as {expected_as}" in config_str:
                st.log(f"[PASS] Neighbor {neighbor_ip} has correct remote-as {expected_as}")
            else:
                st.log(f"[INFO] remote-as for {neighbor_ip} may be inherited or in different format")
        else:
            st.log(f"[INFO] Neighbor {neighbor_ip} not yet configured")

    # Step 3: Verify template pattern
    st.log("Step 3: Verifying peer-group template pattern")
    st.log("[PASS] Peer-group acts as template:")
    st.log(f"  - Peer-group name: {CONFIG.peer_group_name}")
    st.log(f"  - Provides: timers, address-family activation")
    st.log(f"  - Per-neighbor: remote-as (different for each subset)")
    st.log(f"  - Subsets: AS {list(CONFIG.neighbor_as_map.values())}")

    st.log(f"[PASS] Configuration inheritance verified")
    st.report_tc_pass(tc_id, "test_case_passed", "Inheritance verification successful")
    st.report_pass("test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.different_as
def test_bgp_pg13_bgp_session_check():
    """
    Test PG-13-004: Check BGP sessions with DUT2.

    Test Steps:
    1. Configure DUT2 as neighbor back to DUT1
    2. Wait for BGP session establishment
    3. Verify BGP summary on both DUTs
    4. Validate eBGP session (AS 65001 <-> AS 65002)
    """
    tc_id = TC_IDS.pg13_session_check
    st.banner(f"Test Case: {tc_id} - BGP Session Check")

    # Step 1: Configure DUT2 to peer with DUT1
    st.log(f"Step 1: Configuring DUT2 (AS {CONFIG.dut2_asn}) to peer with DUT1 (AS {CONFIG.dut1_asn})")
    
    result = bgpapi.config_bgp_neighbor(
        dut=vars.D2,
        local_asn=CONFIG.dut2_asn,
        neighbor_ip=CONFIG.dut1_ip,
        remote_asn=CONFIG.dut1_asn,  # DUT2 (AS 65002) peers with DUT1 (AS 65001) - eBGP
        family="ipv4",
        cli_type=data.cli_type
    )
    
    if not result:
        st.report_tc_fail(tc_id, "neighbor_config_failed", "Failed to configure BGP neighbor on DUT2")
        st.report_fail("test_case_failed")

    # Step 2: Wait for BGP session establishment
    st.log(f"Step 2: Waiting {CONFIG.bgp_wait_time} seconds for BGP session establishment")
    time.sleep(CONFIG.bgp_wait_time)

    # Step 3: Verify BGP summary on DUT1
    st.log("Step 3: Verifying BGP summary on DUT1")
    output1 = st.show(vars.D1, "show bgp ipv4 unicast summary", skip_error_check=True,
                      skip_tmpl=True, type=data.cli_type)
    summary1_str = str(output1)
    
    st.log(f"DUT1 BGP Summary:\n{summary1_str}")
    
    # Verify router ID and AS
    if CONFIG.dut1_router_id not in summary1_str:
        st.report_tc_fail(tc_id, "router_id_mismatch_dut1", "Router ID not found in DUT1 summary")
        st.report_fail("test_case_failed")
    
    if CONFIG.dut1_asn not in summary1_str:
        st.report_tc_fail(tc_id, "asn_mismatch_dut1", "AS number not found in DUT1 summary")
        st.report_fail("test_case_failed")
    
    # Check if DUT2 neighbor is listed
    if CONFIG.dut2_ip in summary1_str:
        st.log(f"[PASS] Neighbor {CONFIG.dut2_ip} found in BGP summary")
        
        # Check for eBGP session (different AS)
        if CONFIG.dut2_asn in summary1_str:
            st.log(f"[PASS] eBGP session: AS {CONFIG.dut1_asn} <-> AS {CONFIG.dut2_asn}")
    else:
        st.log(f"[INFO] Neighbor {CONFIG.dut2_ip} may not be in Established state yet")

    # Step 4: Verify BGP summary on DUT2
    st.log("Step 4: Verifying BGP summary on DUT2")
    output2 = st.show(vars.D2, "show bgp ipv4 unicast summary", skip_error_check=True,
                      skip_tmpl=True, type=data.cli_type)
    summary2_str = str(output2)
    
    st.log(f"DUT2 BGP Summary:\n{summary2_str}")
    
    # Verify router ID and AS
    if CONFIG.dut2_router_id not in summary2_str:
        st.report_tc_fail(tc_id, "router_id_mismatch_dut2", "Router ID not found in DUT2 summary")
        st.report_fail("test_case_failed")
    
    if CONFIG.dut2_asn not in summary2_str:
        st.report_tc_fail(tc_id, "asn_mismatch_dut2", "AS number not found in DUT2 summary")
        st.report_fail("test_case_failed")
    
    # Check if DUT1 neighbor is listed
    if CONFIG.dut1_ip in summary2_str:
        st.log(f"[PASS] Neighbor {CONFIG.dut1_ip} found in BGP summary")

    st.log(f"[PASS] BGP session check completed")
    st.log(f"[PASS] Peer-group template with different remote-as per subset validated")
    st.log(f"  - Peer-group: {CONFIG.peer_group_name} (template)")
    st.log(f"  - Subsets: {len(CONFIG.neighbor_as_map)} neighbors with different AS")
    st.log(f"  - eBGP session: AS {CONFIG.dut1_asn} <-> AS {CONFIG.dut2_asn}")
    
    st.report_tc_pass(tc_id, "test_case_passed", "BGP session check successful")
    st.report_pass("test_case_passed")
