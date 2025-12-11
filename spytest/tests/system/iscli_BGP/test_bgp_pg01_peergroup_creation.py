"""
BGP PEER-GROUP TEST - PG-01: Create Peer-Group and Apply to Neighbors

Test Case ID: PG-01
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_BGP/test_bgp_pg01_peergroup_creation.py \
    --logs-path ./logs/pg01_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates basic iBGP peer-group configuration:
  - Configure IP addresses on Ethernet4 interfaces
  - Configure BGP router with router-id
  - Create basic neighbor without peer-group
  - Verify BGP session establishment
  - Create peer-group "1"
  - Attach neighbors to peer-group
  - Verify peer-group membership

Pre-requisites:
  - 2 SONiC devices connected via Ethernet4
  - Testbed: testbed_2vs.yaml
  - Clean BGP configuration
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

# Test configuration matching manual testcase
CONFIG = SpyTestDict({
    "interface": "Ethernet4",
    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "subnet_mask": "24",
    "asn": "65001",
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
    "peer_group_name": "1",
    "bgp_wait_time": 90,
    "ping_count": 5,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "pg01_basic_bgp": "TC-BGP-PG-01-001",
    "pg01_peergroup": "TC-BGP-PG-01-002",
    "pg01_membership": "TC-BGP-PG-01-003",
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg01_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP PG-01 MODULE CONFIGURATION - START")
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
    st.banner("BGP PG-01 MODULE CLEANUP - START")
    st.banner("=" * 80)
    bgp_pre_config_cleanup()


def bgp_pre_config():
    """Pre-configuration: Clear existing configs and setup interfaces."""
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


def configure_ip_on_interface(dut: str, interface: str, ip_address: str) -> bool:
    """Configure IP address on interface."""
    st.log(f"Configuring IP {ip_address}/{CONFIG.subnet_mask} on {dut} {interface}")

    result = ipapi.config_ip_addr_interface(
        dut,
        interface,
        f"{ip_address}/{CONFIG.subnet_mask}",
        family="ipv4",
        cli_type=data.cli_type
    )

    if not result:
        st.error(f"Failed to configure IP on {dut} {interface}")
        return False

    st.log(f"IP configured successfully on {dut} {interface}")
    return True


def configure_bgp_router(dut: str, asn: str, router_id: str) -> bool:
    """Configure BGP router with ASN and router-id."""
    st.log(f"Configuring BGP on {dut}: AS {asn}, Router-ID {router_id}")

    result = bgpapi.config_bgp(
        dut=dut,
        local_as=asn,
        router_id=router_id,
        config='yes',
        cli_type=data.cli_type
    )

    if not result:
        st.error(f"Failed to configure BGP router on {dut}")
        return False

    st.log(f"BGP router configured successfully on {dut}")
    return True


def configure_bgp_neighbor(dut: str, asn: str, neighbor_ip: str, remote_as: str) -> bool:
    """
    Configure BGP neighbor and activate IPv4 unicast.

    Matches manual commands:
      neighbor 10.1.1.X remote-as 65001
      address-family ipv4 unicast
        activate
    """
    st.log(f"Configuring BGP neighbor {neighbor_ip} on {dut}")

    # Configure neighbor
    result = bgpapi.config_bgp(
        dut=dut,
        local_as=asn,
        neighbor=neighbor_ip,
        remote_as=remote_as,
        config='yes',
        cli_type=data.cli_type
    )

    if not result:
        st.error(f"Failed to configure neighbor on {dut}")
        return False

    # Activate in IPv4 unicast
    result = bgpapi.config_bgp(
        dut=dut,
        local_as=asn,
        neighbor=neighbor_ip,
        addr_family="ipv4",
        config='yes',
        config_type_list=["activate"],
        cli_type=data.cli_type
    )

    st.log(f"BGP neighbor {neighbor_ip} configured and activated on {dut}")
    return True


def configure_peer_group(dut: str, asn: str, pg_name: str, remote_as: str) -> bool:
    """
    Configure peer-group with remote-as and activate IPv4 unicast.

    Matches manual commands:
      peer-group 1
        remote-as 65001
        address-family ipv4 unicast
          activate
    """
    st.log(f"Configuring peer-group '{pg_name}' on {dut}")

    # Create peer-group with remote-as
    result = bgpapi.config_bgp(
        dut=dut,
        local_as=asn,
        neighbor=pg_name,
        remote_as=remote_as,
        config='yes',
        config_type_list=["peer_group"],
        cli_type=data.cli_type
    )

    if not result:
        st.error(f"Failed to configure peer-group on {dut}")
        return False

    # Activate IPv4 unicast for peer-group
    result = bgpapi.config_bgp(
        dut=dut,
        local_as=asn,
        neighbor=pg_name,
        addr_family="ipv4",
        config='yes',
        config_type_list=["activate"],
        cli_type=data.cli_type
    )

    st.log(f"Peer-group '{pg_name}' configured on {dut}")
    return True


def attach_neighbor_to_peergroup(dut: str, asn: str, neighbor_ip: str, pg_name: str) -> bool:
    """
    Attach neighbor to peer-group.

    Matches manual commands:
      neighbor 10.1.1.X remote-as 65001
        peer-group 1
        address-family ipv4 unicast
          activate
    """
    st.log(f"Attaching neighbor {neighbor_ip} to peer-group '{pg_name}' on {dut}")

    # Configure neighbor with peer-group
    result = bgpapi.config_bgp(
        dut=dut,
        local_as=asn,
        neighbor=neighbor_ip,
        remote_as=CONFIG.asn,
        peergroup=pg_name,
        config='yes',
        config_type_list=["peergroup"],
        cli_type=data.cli_type
    )

    if not result:
        st.error(f"Failed to attach neighbor to peer-group on {dut}")
        return False

    # Activate IPv4 unicast for neighbor
    result = bgpapi.config_bgp(
        dut=dut,
        local_as=asn,
        neighbor=neighbor_ip,
        addr_family="ipv4",
        config='yes',
        config_type_list=["activate"],
        cli_type=data.cli_type
    )

    st.log(f"Neighbor {neighbor_ip} attached to peer-group '{pg_name}'")
    return True


def verify_bgp_session(dut: str, neighbor_ip: str, state: str = 'Established') -> bool:
    """Verify BGP neighbor session state."""
    st.log(f"Verifying BGP session: {dut} <-> {neighbor_ip}, expected state: {state}")

    result = st.poll_wait(
        bgpapi.verify_bgp_summary,
        CONFIG.bgp_wait_time,
        dut,
        family='ipv4',
        neighbor=neighbor_ip,
        state=state,
        shell=data.cli_type
    )

    if result:
        st.log(f"BGP session {dut} <-> {neighbor_ip} is {state}")
        return True
    else:
        st.error(f"BGP session {dut} <-> {neighbor_ip} did not reach {state} state")
        return False


def verify_peer_group_membership(dut: str, neighbor_ip: str, pg_name: str) -> bool:
    """Verify peer-group membership in neighbor output."""
    st.log(f"Verifying peer-group membership for {neighbor_ip} on {dut}")

    output = bgpapi.show_bgp_neighbor(dut, neighbor_ip, cli_type=data.cli_type)
    st.log(f"BGP Neighbor Output:\n{output}")

    output_str = str(output)

    # Check for peer-group membership
    expected_patterns = [
        f"Member of peer-group {pg_name}",
        f"peer-group {pg_name}",
        f"peergroup {pg_name}"
    ]

    for pattern in expected_patterns:
        if pattern in output_str or pattern.upper() in output_str.upper():
            st.log(f"SUCCESS: Neighbor {neighbor_ip} is member of peer-group '{pg_name}'")
            return True

    st.error(f"FAILED: Peer-group membership not verified for {neighbor_ip}")
    return False


def ping_test(src_dut: str, dst_ip: str, count: int = 5) -> bool:
    """Test ping connectivity."""
    st.log(f"Ping test: {src_dut} -> {dst_ip}")

    result = ipapi.ping(src_dut, dst_ip, family='ipv4', count=count)

    if result:
        st.log(f"Ping successful: {src_dut} -> {dst_ip}")
        return True
    else:
        st.error(f"Ping failed: {src_dut} -> {dst_ip}")
        return False


def test_bgp_pg01_peergroup_creation():
    """
    Test Case PG-01: Create Peer-Group and Apply to Neighbors

    Following exact manual testcase validation steps:
    1. Configure IP addresses on Ethernet4
    2. Configure BGP routers with router-ids
    3. Configure basic BGP neighbors
    4. Activate IPv4 unicast address family
    5. Verify BGP session establishment
    6. Create peer-groups
    7. Attach neighbors to peer-groups
    8. Verify peer-group membership
    """
    st.banner("=" * 80)
    st.banner("TEST PG-01: CREATE PEER-GROUP AND APPLY TO NEIGHBORS")
    st.banner("=" * 80)

    # ==================================================================
    # STEP 1: Configure IP Addresses on Interfaces
    # ==================================================================
    st.banner("STEP 1: Configure IP Addresses on Ethernet4")

    if not configure_ip_on_interface(vars.D1, CONFIG.interface, CONFIG.dut1_ip):
        st.report_tc_fail(TC_IDS.pg01_basic_bgp, "msg", f"Failed to configure IP on {vars.D1}")
        st.report_fail("msg", f"Failed to configure IP on {vars.D1}")

    if not configure_ip_on_interface(vars.D2, CONFIG.interface, CONFIG.dut2_ip):
        st.report_tc_fail(TC_IDS.pg01_basic_bgp, "msg", f"Failed to configure IP on {vars.D2}")
        st.report_fail("msg", f"Failed to configure IP on {vars.D2}")

    st.wait(5, "Waiting for interfaces to come up")

    # ==================================================================
    # STEP 2: Proceed to BGP Configuration (No Ping Test - Matches Manual)
    # ==================================================================
    st.banner("STEP 2: Proceed to BGP Configuration")
    st.log("NOTE: Skipping ping test to match manual configuration sequence")
    st.log("Manual test proceeds directly from IP config to BGP config")
    st.log("BGP session establishment will verify connectivity")

    # ==================================================================
    # STEP 3: Configure BGP Routers with Router-IDs
    # ==================================================================
    st.banner("STEP 3: Configure BGP Routers with Router-ID")

    if not configure_bgp_router(vars.D1, CONFIG.asn, CONFIG.dut1_router_id):
        st.report_tc_fail(TC_IDS.pg01_basic_bgp, "bgp_router_id_failed", vars.D1)
        st.report_fail("bgp_router_id_failed", vars.D1)

    if not configure_bgp_router(vars.D2, CONFIG.asn, CONFIG.dut2_router_id):
        st.report_tc_fail(TC_IDS.pg01_basic_bgp, "bgp_router_id_failed", vars.D2)
        st.report_fail("bgp_router_id_failed", vars.D2)

    # ==================================================================
    # STEP 4: Configure BGP Neighbors
    # ==================================================================
    st.banner("STEP 4: Configure BGP Neighbors")

    st.log(f"DUT1: Configuring neighbor {CONFIG.dut2_ip}")
    if not configure_bgp_neighbor(vars.D1, CONFIG.asn, CONFIG.dut2_ip, CONFIG.asn):
        st.report_tc_fail(TC_IDS.pg01_basic_bgp, "msg", f"Failed to configure neighbor on {vars.D1}")
        st.report_fail("msg", f"Failed to configure neighbor on {vars.D1}")

    st.log(f"DUT2: Configuring neighbor {CONFIG.dut1_ip}")
    if not configure_bgp_neighbor(vars.D2, CONFIG.asn, CONFIG.dut1_ip, CONFIG.asn):
        st.report_tc_fail(TC_IDS.pg01_basic_bgp, "msg", f"Failed to configure neighbor on {vars.D2}")
        st.report_fail("msg", f"Failed to configure neighbor on {vars.D2}")

    # ==================================================================
    # STEP 5: Verify BGP Session Establishment (Initial)
    # ==================================================================
    st.banner("STEP 5: Verify Initial BGP Session Establishment")

    st.wait(30, "Waiting for initial BGP session")

    if not verify_bgp_session(vars.D1, CONFIG.dut2_ip, 'Established'):
        st.generate_tech_support([vars.D1, vars.D2], "pg01_initial_bgp_session_failed")
        st.report_tc_fail(TC_IDS.pg01_basic_bgp, "bgp_ip_peer_establish_fail", CONFIG.dut2_ip)
        st.report_fail("bgp_ip_peer_establish_fail", CONFIG.dut2_ip)

    if not verify_bgp_session(vars.D2, CONFIG.dut1_ip, 'Established'):
        st.generate_tech_support([vars.D1, vars.D2], "pg01_initial_bgp_session_failed")
        st.report_tc_fail(TC_IDS.pg01_basic_bgp, "bgp_ip_peer_establish_fail", CONFIG.dut1_ip)
        st.report_fail("bgp_ip_peer_establish_fail", CONFIG.dut1_ip)

    st.report_tc_pass(TC_IDS.pg01_basic_bgp, "msg", "Basic BGP session established successfully")

    # ==================================================================
    # STEP 6: Create Peer-Groups
    # ==================================================================
    st.banner("STEP 6: Create Peer-Groups")

    st.log(f"Creating peer-group '{CONFIG.peer_group_name}' on both DUTs")

    if not configure_peer_group(vars.D1, CONFIG.asn, CONFIG.peer_group_name, CONFIG.asn):
        st.report_tc_fail(TC_IDS.pg01_peergroup, "msg", f"Failed to configure peer-group on {vars.D1}")
        st.report_fail("msg", f"Failed to configure peer-group on {vars.D1}")

    if not configure_peer_group(vars.D2, CONFIG.asn, CONFIG.peer_group_name, CONFIG.asn):
        st.report_tc_fail(TC_IDS.pg01_peergroup, "msg", f"Failed to configure peer-group on {vars.D2}")
        st.report_fail("msg", f"Failed to configure peer-group on {vars.D2}")

    st.report_tc_pass(TC_IDS.pg01_peergroup, "msg", "Peer-groups created successfully")

    # ==================================================================
    # STEP 7: Attach Neighbors to Peer-Groups
    # ==================================================================
    st.banner("STEP 7: Attach Neighbors to Peer-Groups")

    st.log(f"DUT1: Attaching neighbor {CONFIG.dut2_ip} to peer-group '{CONFIG.peer_group_name}'")
    if not attach_neighbor_to_peergroup(vars.D1, CONFIG.asn, CONFIG.dut2_ip, CONFIG.peer_group_name):
        st.report_tc_fail(TC_IDS.pg01_membership, "msg", f"Failed to attach neighbor on {vars.D1}")
        st.report_fail("msg", f"Failed to attach neighbor on {vars.D1}")

    st.log(f"DUT2: Attaching neighbor {CONFIG.dut1_ip} to peer-group '{CONFIG.peer_group_name}'")
    if not attach_neighbor_to_peergroup(vars.D2, CONFIG.asn, CONFIG.dut1_ip, CONFIG.peer_group_name):
        st.report_tc_fail(TC_IDS.pg01_membership, "msg", f"Failed to attach neighbor on {vars.D2}")
        st.report_fail("msg", f"Failed to attach neighbor on {vars.D2}")

    # ==================================================================
    # STEP 8: Verify BGP Session with Peer-Group
    # ==================================================================
    st.banner("STEP 8: Verify BGP Session with Peer-Group")

    st.wait(CONFIG.bgp_wait_time, "Waiting for BGP convergence with peer-group")

    if not verify_bgp_session(vars.D1, CONFIG.dut2_ip, 'Established'):
        st.generate_tech_support([vars.D1, vars.D2], "pg01_peergroup_bgp_session_failed")
        st.report_tc_fail(TC_IDS.pg01_membership, "bgp_ip_peer_establish_fail", CONFIG.dut2_ip)
        st.report_fail("bgp_ip_peer_establish_fail", CONFIG.dut2_ip)

    if not verify_bgp_session(vars.D2, CONFIG.dut1_ip, 'Established'):
        st.generate_tech_support([vars.D1, vars.D2], "pg01_peergroup_bgp_session_failed")
        st.report_tc_fail(TC_IDS.pg01_membership, "bgp_ip_peer_establish_fail", CONFIG.dut1_ip)
        st.report_fail("bgp_ip_peer_establish_fail", CONFIG.dut1_ip)

    # ==================================================================
    # STEP 9: Verify Peer-Group Membership (CRITICAL CHECK)
    # ==================================================================
    st.banner("STEP 9: Verify Peer-Group Membership (CRITICAL CHECK)")
    st.log(f"Expected: 'Member of peer-group {CONFIG.peer_group_name} for session parameters'")

    if not verify_peer_group_membership(vars.D1, CONFIG.dut2_ip, CONFIG.peer_group_name):
        st.report_tc_fail(TC_IDS.pg01_membership, "msg",
                         f"Peer-group membership verification failed on {vars.D1}")
        st.report_fail("msg", f"Peer-group membership verification failed on {vars.D1}")

    if not verify_peer_group_membership(vars.D2, CONFIG.dut1_ip, CONFIG.peer_group_name):
        st.report_tc_fail(TC_IDS.pg01_membership, "msg",
                         f"Peer-group membership verification failed on {vars.D2}")
        st.report_fail("msg", f"Peer-group membership verification failed on {vars.D2}")

    st.report_tc_pass(TC_IDS.pg01_membership, "msg", "Peer-group membership verified successfully")

    # ==================================================================
    # TEST PASSED
    # ==================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: PG-01 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - PG-01: Create Peer-Group and Apply to Neighbors")
    st.log("=" * 80)
    st.log(f"✓ IP addresses configured: {CONFIG.dut1_ip}/{CONFIG.subnet_mask}, {CONFIG.dut2_ip}/{CONFIG.subnet_mask}")
    st.log(f"✓ IP connectivity: VERIFIED BY BGP SESSION (no ping test - matches manual)")
    st.log(f"✓ BGP routers configured: {vars.D1}, {vars.D2}")
    st.log(f"✓ Initial BGP session: ESTABLISHED")
    st.log(f"✓ Peer-group '{CONFIG.peer_group_name}': CREATED")
    st.log(f"✓ Neighbors attached to peer-group: VERIFIED")
    st.log(f"✓ BGP sessions with peer-group: ESTABLISHED")
    st.log(f"✓ CRITICAL CHECK - 'Member of peer-group {CONFIG.peer_group_name}': CONFIRMED")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
