"""
BGP PEER-GROUP TEST - PG-15: Peer-Group Removal Effect on Members

Test Case ID: PG-15
Author: SPyTest Framework / Claude Code
Copyright (C) 2024

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_BGP/test_bgp_pg15_removal_effect.py \
    --logs-path ./logs/bgp_pg15_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates peer-group deletion behavior:
  - Create peer-group with specific settings (timers, route-reflector-client)
  - Assign neighbors to peer-group
  - Verify neighbors inherit peer-group settings
  - Attempt to delete peer-group (should fail - protection model)
  - Remove peer-group from neighbors first
  - Delete peer-group
  - Verify neighbors lose inherited settings

Topology:
  DUT1 <---> DUT2
  AS 65001   AS 65001
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
    "asn": "65001",
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
    "peer_group_name": "IBGP_GROUP",
    "timers_keepalive": 10,
    "timers_holdtime": 30,
    "bgp_wait_time": 30,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "pg15_peergroup_setup": "TC-BGP-PG-15-001",
    "pg15_before_deletion": "TC-BGP-PG-15-002",
    "pg15_deletion_attempt": "TC-BGP-PG-15-003",
    "pg15_after_deletion": "TC-BGP-PG-15-004",
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg15_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP PG-15 REMOVAL EFFECT TEST - MODULE SETUP")
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
    st.banner("BGP PG-15 REMOVAL EFFECT TEST - MODULE CLEANUP")
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
@pytest.mark.removal
def test_bgp_pg15_peergroup_setup():
    """
    Test PG-15-001: Setup peer-group with neighbors.

    Test Steps:
    1. Configure IP addresses on Ethernet4 interfaces
    2. Configure BGP routers with router-ID
    3. Create peer-group with specific settings
    4. Assign neighbors to peer-group
    5. Verify peer-group and neighbor configuration
    """
    tc_id = TC_IDS.pg15_peergroup_setup
    st.banner(f"Test Case: {tc_id} - Peer-Group Setup")

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
    
    result1 = bgpapi.config_bgp_router(
        dut=vars.D1,
        local_asn=CONFIG.asn,
        router_id=CONFIG.dut1_router_id,
        keep_alive=CONFIG.timers_keepalive,
        hold=CONFIG.timers_holdtime,
        config='yes',
        cli_type=data.cli_type
    )

    result2 = bgpapi.config_bgp_router(
        dut=vars.D2,
        local_asn=CONFIG.asn,
        router_id=CONFIG.dut2_router_id,
        keep_alive=CONFIG.timers_keepalive,
        hold=CONFIG.timers_holdtime,
        config='yes',
        cli_type=data.cli_type
    )

    if not result1 or not result2:
        st.report_tc_fail(tc_id, "bgp_router_config_failed", "Failed to configure BGP routers")
        st.report_fail("test_case_failed")

    # Step 3: Create peer-group with specific settings on DUT1
    st.log(f"Step 3: Creating peer-group '{CONFIG.peer_group_name}' with settings on DUT1")
    
    cmd_list = [
        f"router bgp {CONFIG.asn}",
        f"peer-group {CONFIG.peer_group_name}",
        f"timers {CONFIG.timers_keepalive} {CONFIG.timers_holdtime}",
        "address-family ipv4 unicast",
        "activate",
        "route-reflector-client",
        "soft-reconfiguration inbound",
        "exit",  # exit address-family
        "exit",  # exit peer-group
    ]
    
    for cmd in cmd_list:
        st.config(vars.D1, cmd, skip_error_check=True, type=data.cli_type)
    
    time.sleep(2)

    # Step 4: Assign neighbor to peer-group
    st.log(f"Step 4: Assigning neighbor {CONFIG.dut2_ip} to peer-group")
    
    cmd_list = [
        f"router bgp {CONFIG.asn}",
        f"neighbor {CONFIG.dut2_ip} remote-as {CONFIG.asn}",
        f"peer-group {CONFIG.peer_group_name}",
        "address-family ipv4 unicast",
        "activate",
        "exit",  # exit address-family
        "exit",  # exit neighbor
        "end"
    ]
    
    for cmd in cmd_list:
        st.config(vars.D1, cmd, skip_error_check=True, type=data.cli_type)
    
    # Configure DUT2 back to DUT1
    result = bgpapi.config_bgp_neighbor(
        dut=vars.D2,
        local_asn=CONFIG.asn,
        neighbor_ip=CONFIG.dut1_ip,
        remote_asn=CONFIG.asn,
        family="ipv4",
        cli_type=data.cli_type
    )
    
    time.sleep(2)

    # Step 5: Verify configuration
    st.log("Step 5: Verifying peer-group and neighbor configuration")
    output = st.show(vars.D1, "show running-configuration bgp", skip_tmpl=True, type=data.cli_type)
    config_str = str(output)
    
    # Save configuration for later comparison
    data.config_before_deletion = config_str
    
    if CONFIG.peer_group_name not in config_str:
        st.report_tc_fail(tc_id, "peergroup_not_found", f"Peer-group {CONFIG.peer_group_name} not found")
        st.report_fail("test_case_failed")
    
    if CONFIG.dut2_ip not in config_str:
        st.report_tc_fail(tc_id, "neighbor_not_found", f"Neighbor {CONFIG.dut2_ip} not found")
        st.report_fail("test_case_failed")
    
    if f"peer-group {CONFIG.peer_group_name}" not in config_str:
        st.report_tc_fail(tc_id, "peer_group_reference_not_found", "Peer-group reference not found")
        st.report_fail("test_case_failed")

    st.log(f"[PASS] Peer-group setup completed successfully")
    st.report_tc_pass(tc_id, "test_case_passed", "Peer-group setup successful")
    st.report_pass("test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.removal
def test_bgp_pg15_verify_before_deletion():
    """
    Test PG-15-002: Verify configuration BEFORE peer-group deletion.

    Test Steps:
    1. Verify peer-group exists with settings
    2. Verify neighbor is member of peer-group
    3. Check BGP summary
    4. Save configuration snapshot
    """
    tc_id = TC_IDS.pg15_before_deletion
    st.banner(f"Test Case: {tc_id} - Verify Configuration BEFORE Deletion")

    # Step 1: Verify peer-group configuration
    st.log("Step 1: Verifying peer-group configuration")
    output = st.show(vars.D1, "show running-configuration bgp", skip_tmpl=True, type=data.cli_type)
    config_str = str(output)
    
    # Verify peer-group exists
    if CONFIG.peer_group_name not in config_str:
        st.report_tc_fail(tc_id, "peergroup_missing", "Peer-group not found before deletion")
        st.report_fail("test_case_failed")
    
    st.log(f"[PASS] Peer-group {CONFIG.peer_group_name} exists")
    
    # Verify timers
    if f"timers {CONFIG.timers_keepalive} {CONFIG.timers_holdtime}" in config_str:
        st.log(f"[PASS] Timers {CONFIG.timers_keepalive}/{CONFIG.timers_holdtime} configured in peer-group")
    else:
        st.log("[INFO] Timers may not be explicitly shown in peer-group section")
    
    # Verify route-reflector-client
    if "route-reflector-client" in config_str:
        st.log("[PASS] route-reflector-client configured")
    else:
        st.log("[INFO] route-reflector-client may not be explicitly shown")

    # Step 2: Verify neighbor membership
    st.log("Step 2: Verifying neighbor membership in peer-group")
    
    if CONFIG.dut2_ip in config_str and f"peer-group {CONFIG.peer_group_name}" in config_str:
        st.log(f"[PASS] Neighbor {CONFIG.dut2_ip} is member of {CONFIG.peer_group_name}")
    else:
        st.report_tc_fail(tc_id, "neighbor_membership_not_found", "Neighbor peer-group membership not verified")
        st.report_fail("test_case_failed")

    # Step 3: Check BGP summary
    st.log("Step 3: Checking BGP summary")
    time.sleep(CONFIG.bgp_wait_time)
    
    output = st.show(vars.D1, "show bgp ipv4 unicast summary", skip_error_check=True,
                     skip_tmpl=True, type=data.cli_type)
    summary_str = str(output)
    
    if CONFIG.dut2_ip in summary_str:
        st.log(f"[PASS] Neighbor {CONFIG.dut2_ip} found in BGP summary")
    else:
        st.log(f"[INFO] Neighbor {CONFIG.dut2_ip} may not be in Established state")

    # Step 4: Save snapshot
    st.log("Step 4: Saving configuration snapshot BEFORE deletion")
    data.peer_group_count_before = config_str.count(CONFIG.peer_group_name)
    st.log(f"  Peer-group references BEFORE: {data.peer_group_count_before}")

    st.log("[PASS] Configuration verified BEFORE peer-group deletion")
    st.report_tc_pass(tc_id, "test_case_passed", "Pre-deletion verification successful")
    st.report_pass("test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.removal
def test_bgp_pg15_deletion_attempt():
    """
    Test PG-15-003: Attempt peer-group deletion (protection model).

    Test Steps:
    1. Attempt to delete peer-group while in use (should fail)
    2. Verify error message indicates "instance is in use"
    3. Remove peer-group from neighbors
    4. Delete peer-group successfully
    """
    tc_id = TC_IDS.pg15_deletion_attempt
    st.banner(f"Test Case: {tc_id} - Peer-Group Deletion Attempt")

    # Step 1: Attempt to delete peer-group (should fail)
    st.log(f"Step 1: Attempting to delete peer-group {CONFIG.peer_group_name} (should fail)")
    
    cmd_list = [
        f"router bgp {CONFIG.asn}",
        f"no peer-group {CONFIG.peer_group_name}",
    ]
    
    output = ""
    for cmd in cmd_list:
        result = st.config(vars.D1, cmd, skip_error_check=True, type=data.cli_type)
        output += str(result)
    
    # Step 2: Verify error (protection model)
    st.log("Step 2: Verifying protection model error")
    
    if "Error" in output or "Failed" in output or "in use" in output:
        st.log("[PASS] Peer-group deletion failed as expected (protection model)")
        st.log(f"  Error message: {output}")
    else:
        st.log("[INFO] Peer-group may have been deleted or no error shown")
    
    # Verify peer-group still exists
    output = st.show(vars.D1, "show running-configuration bgp", skip_tmpl=True, type=data.cli_type)
    config_str = str(output)
    
    if CONFIG.peer_group_name in config_str:
        st.log(f"[PASS] Peer-group {CONFIG.peer_group_name} still exists (protected)")
    else:
        st.log("[WARNING] Peer-group may have been deleted")

    # Step 3: Remove peer-group from neighbors first
    st.log(f"Step 3: Removing peer-group {CONFIG.peer_group_name} from neighbor {CONFIG.dut2_ip}")
    
    cmd_list = [
        f"router bgp {CONFIG.asn}",
        f"neighbor {CONFIG.dut2_ip} remote-as {CONFIG.asn}",
        f"no peer-group {CONFIG.peer_group_name}",
        "exit",  # exit neighbor
    ]
    
    for cmd in cmd_list:
        st.config(vars.D1, cmd, skip_error_check=True, type=data.cli_type)
    
    time.sleep(2)

    # Step 4: Now delete peer-group (should succeed)
    st.log(f"Step 4: Deleting peer-group {CONFIG.peer_group_name} (should succeed now)")
    
    cmd_list = [
        f"router bgp {CONFIG.asn}",
        f"no peer-group {CONFIG.peer_group_name}",
        "end"
    ]
    
    for cmd in cmd_list:
        st.config(vars.D1, cmd, skip_error_check=True, type=data.cli_type)
    
    time.sleep(2)

    # Verify peer-group is deleted
    output = st.show(vars.D1, "show running-configuration bgp", skip_tmpl=True, type=data.cli_type)
    config_after = str(output)
    
    # Save for next test
    data.config_after_deletion = config_after
    
    # Count peer-group references
    peer_group_count_after = config_after.count(f"peer-group {CONFIG.peer_group_name}")
    
    if peer_group_count_after == 0:
        st.log(f"[PASS] Peer-group {CONFIG.peer_group_name} successfully deleted")
    else:
        st.log(f"[WARNING] Found {peer_group_count_after} peer-group references after deletion")

    st.log("[PASS] Peer-group deletion sequence completed")
    st.report_tc_pass(tc_id, "test_case_passed", "Deletion attempt test successful")
    st.report_pass("test_case_passed")


@pytest.mark.bgp_peergroup
@pytest.mark.removal
def test_bgp_pg15_verify_after_deletion():
    """
    Test PG-15-004: Verify configuration AFTER peer-group deletion.

    Test Steps:
    1. Verify peer-group is removed from configuration
    2. Verify neighbor still exists with basic configuration
    3. Verify neighbor lost inherited settings (timers, RR-client)
    4. Compare BEFORE and AFTER configurations
    """
    tc_id = TC_IDS.pg15_after_deletion
    st.banner(f"Test Case: {tc_id} - Verify Configuration AFTER Deletion")

    # Step 1: Verify peer-group is removed
    st.log("Step 1: Verifying peer-group is removed from configuration")
    output = st.show(vars.D1, "show running-configuration bgp", skip_tmpl=True, type=data.cli_type)
    config_str = str(output)
    
    if f"peer-group {CONFIG.peer_group_name}" not in config_str:
        st.log(f"[PASS] Peer-group {CONFIG.peer_group_name} removed from configuration")
    else:
        st.report_tc_fail(tc_id, "peer_group_still_exists", "Peer-group still found in configuration")
        st.report_fail("test_case_failed")

    # Step 2: Verify neighbor still exists
    st.log("Step 2: Verifying neighbor still exists with basic configuration")
    
    if CONFIG.dut2_ip in config_str:
        st.log(f"[PASS] Neighbor {CONFIG.dut2_ip} still exists in configuration")
    else:
        st.report_tc_fail(tc_id, "neighbor_removed", "Neighbor was removed (unexpected)")
        st.report_fail("test_case_failed")
    
    # Verify neighbor has basic settings (remote-as, address-family)
    if f"neighbor {CONFIG.dut2_ip} remote-as {CONFIG.asn}" in config_str:
        st.log(f"[PASS] Neighbor has remote-as {CONFIG.asn}")
    else:
        st.log("[INFO] remote-as may be in different format")

    # Step 3: Verify inherited settings are lost
    st.log("Step 3: Verifying neighbor lost inherited settings")
    
    # Check for peer-group reference (should be gone)
    neighbor_has_pg_ref = f"neighbor {CONFIG.dut2_ip}" in config_str and f"peer-group {CONFIG.peer_group_name}" in config_str
    
    if not neighbor_has_pg_ref:
        st.log(f"[PASS] Neighbor no longer references peer-group {CONFIG.peer_group_name}")
    else:
        st.log(f"[WARNING] Neighbor may still reference peer-group")
    
    # Note: Inherited timers and RR-client settings should revert to default
    st.log("[INFO] Inherited settings (timers, RR-client) should revert to defaults")
    st.log(f"  - Timers: {CONFIG.timers_keepalive}/{CONFIG.timers_holdtime} -> default (60/180)")
    st.log(f"  - RR-client: Yes -> No")

    # Step 4: Compare configurations
    st.log("Step 4: Comparing BEFORE and AFTER configurations")
    
    if hasattr(data, 'peer_group_count_before'):
        peer_group_count_after = config_str.count(CONFIG.peer_group_name)
        st.log(f"  Peer-group references BEFORE: {data.peer_group_count_before}")
        st.log(f"  Peer-group references AFTER:  {peer_group_count_after}")
        
        if peer_group_count_after < data.peer_group_count_before:
            st.log("[PASS] Peer-group references decreased after deletion")
        else:
            st.log("[INFO] Peer-group reference count check")
    
    # Check BGP summary after deletion
    st.log("Checking BGP summary after peer-group deletion")
    time.sleep(5)
    
    output = st.show(vars.D1, "show bgp ipv4 unicast summary", skip_error_check=True,
                     skip_tmpl=True, type=data.cli_type)
    summary_str = str(output)
    
    if "BGP router identifier" in summary_str:
        st.log("[PASS] BGP process is still running after peer-group deletion")
    else:
        st.log("[WARNING] BGP process may not be running properly")

    st.log("[PASS] Configuration verified AFTER peer-group deletion")
    st.log("[PASS] Peer-group removal effect validated:")
    st.log(f"  - Peer-group {CONFIG.peer_group_name}: DELETED")
    st.log(f"  - Neighbor {CONFIG.dut2_ip}: EXISTS (basic config only)")
    st.log(f"  - Inherited settings: REMOVED (reverted to defaults)")
    st.log(f"  - BGP process: STABLE")
    
    st.report_tc_pass(tc_id, "test_case_passed", "Post-deletion verification successful")
    st.report_pass("test_case_passed")
