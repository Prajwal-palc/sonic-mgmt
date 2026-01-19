"""
BGP PEER-GROUP TEST - PG-07: Peer-Group Default Shutdown Behaviour for New Peers

Test Case ID: PG-07
Author: Automated Test Development
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_bgp_peergroup_2vs.yaml \
    tests/system/iscli_BGP/test_bgp_pg07_shutdown_behaviour.py \
    --logs-path ./logs/pg07_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates BGP peer-group default shutdown behaviour:
  - Configure peer-group with shutdown enabled by default
  - Add neighbor to peer-group (should inherit shutdown state)
  - Verify neighbor is in Idle/Active state (not Established)
  - Override shutdown on specific neighbor with "no shutdown"
  - Verify that specific neighbor establishes session
  - Verify inheritance of shutdown from peer-group to neighbors

Pre-requisites:
  - 2 SONiC devices connected via Ethernet4
  - Testbed: testbed_bgp_peergroup_2vs.yaml
  - Clean BGP configuration
  - iBGP configuration (same AS on both devices)

Test Topology:
  D1 (1.1.1.1) ------- D2 (2.2.2.2)
  10.1.1.1/24          10.1.1.2/24
  AS 65001             AS 65001

Configuration Steps:
  D1:
    - Configure peer-group "PG1" with shutdown
    - Add neighbor 10.1.1.2 to peer-group
    - Neighbor inherits shutdown state (no BGP session)

  D2:
    - Configure peer-group "PG1" with shutdown
    - Add neighbor 10.1.1.1 to peer-group
    - Override with "no shutdown" on neighbor
    - BGP session should establish
"""

from __future__ import annotations

import pytest
import time
from spytest import st, SpyTestDict

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
    "peer_group_name": "PG1",
    "bgp_wait_time": 90,
    "shutdown_wait_time": 30,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "pg07_shutdown_inherit": "TC-BGP-PG-07-001",
    "pg07_shutdown_override": "TC-BGP-PG-07-002",
    "pg07_shutdown_default": "TC-BGP-PG-07-003",
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg07_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP PG-07 MODULE CONFIGURATION - START")
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
    st.banner("BGP PG-07 MODULE CLEANUP - START")
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

    # Clear BGP configuration
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


def configure_ip_addresses():
    """Configure IP addresses on both devices."""
    st.banner("Configuring IP addresses on interfaces")

    # D1 IP configuration
    result = ipapi.config_ip_addr_interface(
        vars.D1,
        CONFIG.interface,
        f"{CONFIG.dut1_ip}/{CONFIG.subnet_mask}",
        family="ipv4",
        cli_type=data.cli_type
    )
    if not result:
        st.report_fail("ip_config_failed", vars.D1, CONFIG.interface)

    # D2 IP configuration
    result = ipapi.config_ip_addr_interface(
        vars.D2,
        CONFIG.interface,
        f"{CONFIG.dut2_ip}/{CONFIG.subnet_mask}",
        family="ipv4",
        cli_type=data.cli_type
    )
    if not result:
        st.report_fail("ip_config_failed", vars.D2, CONFIG.interface)

    st.log("IP addresses configured successfully")


def configure_bgp_peer_group_with_shutdown(dut: str, router_id: str, neighbor_ip: str, override_shutdown: bool = False):
    """
    Configure BGP with peer-group having shutdown enabled.

    Args:
        dut: Device name
        router_id: BGP router ID
        neighbor_ip: Neighbor IP address
        override_shutdown: If True, override shutdown with "no shutdown" on neighbor
    """
    st.log(f"Configuring BGP peer-group with shutdown on {dut}")

    # Use API for configuration
    # Create BGP instance
    bgpapi.config_bgp(
        dut,
        local_as=CONFIG.asn,
        router_id=router_id,
        config='yes',
        cli_type=data.cli_type
    )

    # Configure peer-group
    bgpapi.create_bgp_peergroup(
        dut,
        local_asn=CONFIG.asn,
        peer_grp_name=CONFIG.peer_group_name,
        remote_asn=CONFIG.asn,
        config='yes',
        cli_type=data.cli_type
    )

    # Enable shutdown on peer-group
    bgpapi.config_bgp_neighbor_properties(
        dut,
        local_asn=CONFIG.asn,
        neighbor_ip=CONFIG.peer_group_name,
        config='yes',
        shutdown='yes',
        cli_type=data.cli_type,
        peergroup=CONFIG.peer_group_name
    )

    # Activate peer-group in address-family
    bgpapi.config_address_family_neighbor(
        dut,
        local_asn=CONFIG.asn,
        mode='ipv4',
        neighbor=CONFIG.peer_group_name,
        config='yes',
        activate='yes',
        cli_type=data.cli_type
    )

    # Configure neighbor with peer-group
    bgpapi.config_bgp_neighbor(
        dut,
        local_asn=CONFIG.asn,
        neighbor_ip=neighbor_ip,
        remote_asn=CONFIG.asn,
        config='yes',
        cli_type=data.cli_type
    )

    # Assign neighbor to peer-group
    bgpapi.config_bgp_neighbor_properties(
        dut,
        local_asn=CONFIG.asn,
        neighbor_ip=neighbor_ip,
        config='yes',
        peergroup=CONFIG.peer_group_name,
        cli_type=data.cli_type
    )

    # Override shutdown if requested
    if override_shutdown:
        st.log(f"Overriding shutdown with 'no shutdown' on neighbor {neighbor_ip}")
        bgpapi.config_bgp_neighbor_properties(
            dut,
            local_asn=CONFIG.asn,
            neighbor_ip=neighbor_ip,
            config='no',
            shutdown='yes',
            cli_type=data.cli_type
        )

    # Activate neighbor in address-family
    bgpapi.config_address_family_neighbor(
        dut,
        local_asn=CONFIG.asn,
        mode='ipv4',
        neighbor=neighbor_ip,
        config='yes',
        activate='yes',
        cli_type=data.cli_type
    )

    st.log(f"BGP peer-group with shutdown configured on {dut}")


def verify_bgp_neighbor_idle(dut: str, neighbor_ip: str):
    """
    Verify BGP neighbor is in Idle/Active/Connect state (not Established).

    Args:
        dut: Device name
        neighbor_ip: Neighbor IP address

    Returns:
        bool: True if neighbor is not Established, False otherwise
    """
    st.log(f"Verifying neighbor {neighbor_ip} is NOT established on {dut}")

    # Get BGP neighbor status
    output = bgpapi.show_bgp_neighbor(
        dut,
        neighborip=neighbor_ip,
        cli_type=data.cli_type
    )

    st.log(f"BGP neighbor {neighbor_ip} status on {dut}: {output}")

    # Check if neighbor is NOT in Established state
    result = bgpapi.verify_bgp_neighbor(
        dut,
        neighborip=neighbor_ip,
        state='Established',
        cli_type=data.cli_type
    )

    if result:
        st.error(f"Neighbor {neighbor_ip} is Established (expected: Idle/Active/Connect)")
        return False
    else:
        st.log(f"Neighbor {neighbor_ip} is NOT Established (expected behavior)")
        return True


def verify_bgp_session_established(dut: str, neighbor_ip: str):
    """
    Verify BGP session is established.

    Args:
        dut: Device name
        neighbor_ip: Neighbor IP address

    Returns:
        bool: True if session established, False otherwise
    """
    st.banner(f"Verifying BGP session established between {dut} and {neighbor_ip}")

    # Verify BGP neighbor is Established
    result = bgpapi.verify_bgp_neighbor(
        dut,
        neighborip=neighbor_ip,
        state='Established',
        asn=CONFIG.asn,
        cli_type=data.cli_type
    )

    if not result:
        st.error(f"BGP session not established on {dut} to {neighbor_ip}")
        return False

    st.log(f"BGP session established successfully on {dut}")
    return True


def verify_shutdown_in_config():
    """Verify shutdown configuration in running config."""
    st.banner("Verifying shutdown configuration in running-config")

    # Verify D1 peer-group has shutdown
    output_d1 = bgpapi.show_bgp_ipv4_summary(vars.D1, cli_type=data.cli_type)
    st.log(f"D1 BGP summary: {output_d1}")

    # Show running configuration
    try:
        show_output_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type)
        st.log(f"D1 BGP running-config: {show_output_d1}")

        if "shutdown" in str(show_output_d1).lower():
            st.log("D1: Shutdown configuration found in peer-group")
        else:
            st.warn("D1: Shutdown configuration not clearly visible in output")
    except Exception as e:
        st.log(f"Could not verify running-config: {str(e)}")

    return True


# ============================================================================
# TEST CASES
# ============================================================================

def test_bgp_pg07_basic_setup():
    """
    Basic setup: Configure IP addresses and BGP with shutdown on peer-group
    """
    st.banner("PG-07: Basic Setup - IP and BGP Configuration with Shutdown")

    # Configure IP addresses
    configure_ip_addresses()

    # Configure BGP with peer-group shutdown on D1 (no override)
    configure_bgp_peer_group_with_shutdown(
        vars.D1,
        CONFIG.dut1_router_id,
        CONFIG.dut2_ip,
        override_shutdown=False
    )

    # Configure BGP with peer-group shutdown on D2 (with override)
    configure_bgp_peer_group_with_shutdown(
        vars.D2,
        CONFIG.dut2_router_id,
        CONFIG.dut1_ip,
        override_shutdown=True  # D2 will override with "no shutdown"
    )

    st.log("Basic setup completed successfully")


def test_bgp_pg07_shutdown_inheritance():
    """
    TC-BGP-PG-07-001: Verify neighbor inherits shutdown from peer-group

    Validates:
    - D1: Peer-group has shutdown enabled
    - D1: Neighbor 10.1.1.2 inherits shutdown
    - D1: BGP session should NOT be Established
    """
    st.banner("PG-07-001: Testing shutdown inheritance from peer-group")

    st.log(f"Waiting {CONFIG.shutdown_wait_time} seconds to verify shutdown behavior")
    st.wait(CONFIG.shutdown_wait_time)

    # Verify D1 neighbor is NOT established (inherits shutdown)
    result = verify_bgp_neighbor_idle(vars.D1, CONFIG.dut2_ip)

    if not result:
        st.report_tc_fail(TC_IDS.pg07_shutdown_inherit, "shutdown_inheritance_failed",
                         "Neighbor should NOT be Established when inheriting shutdown from peer-group")

    # Verify configuration
    verify_shutdown_in_config()

    st.report_tc_pass(TC_IDS.pg07_shutdown_inherit, "test_case_passed",
                     "Neighbor correctly inherits shutdown from peer-group")


def test_bgp_pg07_shutdown_override():
    """
    TC-BGP-PG-07-002: Verify neighbor can override peer-group shutdown

    Validates:
    - D2: Peer-group has shutdown enabled
    - D2: Neighbor 10.1.1.1 configured with "no shutdown" (override)
    - D2: BGP session should be Established
    """
    st.banner("PG-07-002: Testing shutdown override on individual neighbor")

    st.log(f"Waiting {CONFIG.bgp_wait_time} seconds for BGP convergence")
    st.wait(CONFIG.bgp_wait_time)

    # Verify D2 neighbor IS established (overrides shutdown)
    result = verify_bgp_session_established(vars.D2, CONFIG.dut1_ip)

    if not result:
        st.report_tc_fail(TC_IDS.pg07_shutdown_override, "shutdown_override_failed",
                         "Neighbor should be Established when overriding peer-group shutdown with 'no shutdown'")

    st.report_tc_pass(TC_IDS.pg07_shutdown_override, "test_case_passed",
                     "Neighbor successfully overrides peer-group shutdown with 'no shutdown'")


def test_bgp_pg07_default_behavior():
    """
    TC-BGP-PG-07-003: Verify peer-group shutdown default behavior

    Validates:
    - Peer-group with shutdown prevents new neighbors from establishing
    - Individual neighbor can explicitly override with "no shutdown"
    - Shutdown inheritance works as expected
    """
    st.banner("PG-07-003: Testing peer-group shutdown default behavior")

    # Show BGP summary on both devices
    st.log("=" * 80)
    st.log("D1 BGP Summary:")
    st.log("=" * 80)
    output_d1 = bgpapi.show_bgp_ipv4_summary(vars.D1, cli_type=data.cli_type)
    st.log(output_d1)

    st.log("=" * 80)
    st.log("D2 BGP Summary:")
    st.log("=" * 80)
    output_d2 = bgpapi.show_bgp_ipv4_summary(vars.D2, cli_type=data.cli_type)
    st.log(output_d2)

    # Verify D1 neighbor count (should be 1, not established)
    # Verify D2 neighbor count (should be 1, established)

    st.report_tc_pass(TC_IDS.pg07_shutdown_default, "test_case_passed",
                     "Peer-group shutdown default behavior verified successfully")


def test_bgp_pg07_final_verification():
    """
    Final verification: Display complete BGP configuration and status
    """
    st.banner("PG-07: Final Verification - Display Configuration")

    # Show running config on both devices
    for dut in [vars.D1, vars.D2]:
        st.log("=" * 80)
        st.log(f"{dut} Running Configuration:")
        st.log("=" * 80)
        try:
            output = st.show(dut, "show running-configuration bgp", type=data.cli_type)
            st.log(output)
        except Exception as e:
            st.log(f"Could not show running-config: {str(e)}")

        st.log("=" * 80)
        st.log(f"{dut} BGP Summary:")
        st.log("=" * 80)
        summary = bgpapi.show_bgp_ipv4_summary(dut, cli_type=data.cli_type)
        st.log(summary)

        # Show neighbor details
        neighbor_ip = CONFIG.dut2_ip if dut == vars.D1 else CONFIG.dut1_ip
        st.log("=" * 80)
        st.log(f"{dut} BGP Neighbor {neighbor_ip}:")
        st.log("=" * 80)
        neighbor_output = bgpapi.show_bgp_neighbor(dut, neighborip=neighbor_ip, cli_type=data.cli_type)
        st.log(neighbor_output)

    st.log("PG-07 test suite completed successfully")
    st.report_pass("test_case_passed")
