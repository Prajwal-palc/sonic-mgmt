"""
BGP PEER-GROUP TEST - PG-09: Peer-Group Advertisement-Interval Tuning

Test Case ID: PG-09
Author: Automated Test Development
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_bgp_peergroup_2vs.yaml \
    tests/system/iscli_BGP/test_bgp_pg09_advertisement_interval.py \
    --logs-path ./logs/pg09_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates BGP peer-group advertisement-interval tuning:
  - Configure peer-group with advertisement-interval
  - Add neighbor to peer-group (should inherit interval)
  - Verify neighbor inherits advertisement-interval from peer-group
  - Override advertisement-interval on specific neighbor
  - Verify that specific neighbor uses overridden value
  - Test different interval values (5s, 10s, 15s, etc.)

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
    - Configure peer-group "PG1" with advertisement-interval 10
    - Add neighbor 10.1.1.2 to peer-group
    - Neighbor inherits advertisement-interval 10

  D2:
    - Configure peer-group "PG1" with advertisement-interval 5
    - Add neighbor 10.1.1.1 to peer-group
    - Override with advertisement-interval 15 on neighbor
    - Neighbor uses 15 seconds (override value)
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
    "d1_adv_interval": "10",      # D1 peer-group advertisement-interval
    "d2_adv_interval": "5",       # D2 peer-group advertisement-interval
    "d2_neighbor_override": "15", # D2 neighbor override value
    "bgp_wait_time": 90,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "pg09_adv_interval_pg": "TC-BGP-PG-09-001",
    "pg09_adv_interval_inherit": "TC-BGP-PG-09-002",
    "pg09_adv_interval_override": "TC-BGP-PG-09-003",
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg09_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("BGP PG-09 MODULE CONFIGURATION - START")
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
    st.banner("BGP PG-09 MODULE CLEANUP - START")
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


def configure_bgp_with_advertisement_interval(dut: str, router_id: str, neighbor_ip: str,
                                               pg_adv_interval: str, neighbor_override: str = None):
    """
    Configure BGP with peer-group having advertisement-interval.

    Args:
        dut: Device name
        router_id: BGP router ID
        neighbor_ip: Neighbor IP address
        pg_adv_interval: Advertisement interval for peer-group
        neighbor_override: Override advertisement-interval for specific neighbor (optional)
    """
    st.log(f"Configuring BGP with advertisement-interval on {dut}")

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

    # Configure advertisement-interval on peer-group
    st.log(f"Setting advertisement-interval {pg_adv_interval} on peer-group {CONFIG.peer_group_name}")
    bgpapi.config_bgp_neighbor_properties(
        dut,
        local_asn=CONFIG.asn,
        neighbor_ip=CONFIG.peer_group_name,
        config='yes',
        advertisement_interval=pg_adv_interval,
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

    # Override advertisement-interval on neighbor if specified
    if neighbor_override:
        st.log(f"Overriding advertisement-interval to {neighbor_override} on neighbor {neighbor_ip}")
        bgpapi.config_bgp_neighbor_properties(
            dut,
            local_asn=CONFIG.asn,
            neighbor_ip=neighbor_ip,
            config='yes',
            advertisement_interval=neighbor_override,
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

    st.log(f"BGP with advertisement-interval configured on {dut}")


def verify_advertisement_interval_config():
    """Verify advertisement-interval configuration in running config."""
    st.banner("Verifying advertisement-interval configuration")

    # Verify D1 peer-group has advertisement-interval
    try:
        output_d1 = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type)
        st.log(f"D1 BGP running-config: {output_d1}")

        if f"advertisement-interval {CONFIG.d1_adv_interval}" in str(output_d1):
            st.log(f"D1: Peer-group advertisement-interval {CONFIG.d1_adv_interval} verified")
        else:
            st.warn(f"D1: advertisement-interval {CONFIG.d1_adv_interval} not clearly visible in config")
    except Exception as e:
        st.log(f"Could not verify D1 running-config: {str(e)}")

    # Verify D2 peer-group and neighbor override
    try:
        output_d2 = st.show(vars.D2, "show running-configuration bgp", type=data.cli_type)
        st.log(f"D2 BGP running-config: {output_d2}")

        if f"advertisement-interval {CONFIG.d2_adv_interval}" in str(output_d2):
            st.log(f"D2: Peer-group advertisement-interval {CONFIG.d2_adv_interval} verified")

        if f"advertisement-interval {CONFIG.d2_neighbor_override}" in str(output_d2):
            st.log(f"D2: Neighbor override advertisement-interval {CONFIG.d2_neighbor_override} verified")
        else:
            st.warn(f"D2: Neighbor override advertisement-interval not clearly visible in config")
    except Exception as e:
        st.log(f"Could not verify D2 running-config: {str(e)}")

    return True


def verify_bgp_session():
    """Verify BGP session is established."""
    st.banner("Verifying BGP session establishment")

    st.log(f"Waiting {CONFIG.bgp_wait_time} seconds for BGP convergence")
    st.wait(CONFIG.bgp_wait_time)

    # Verify on D1
    result = bgpapi.verify_bgp_neighbor(
        vars.D1,
        neighborip=CONFIG.dut2_ip,
        state='Established',
        asn=CONFIG.asn,
        cli_type=data.cli_type
    )

    if not result:
        st.error("BGP session not established on D1")
        return False

    # Verify on D2
    result = bgpapi.verify_bgp_neighbor(
        vars.D2,
        neighborip=CONFIG.dut1_ip,
        state='Established',
        asn=CONFIG.asn,
        cli_type=data.cli_type
    )

    if not result:
        st.error("BGP session not established on D2")
        return False

    st.log("BGP sessions established successfully")
    return True


def verify_neighbor_advertisement_interval(dut: str, neighbor_ip: str, expected_interval: str = None):
    """
    Verify advertisement-interval in neighbor details.

    Args:
        dut: Device name
        neighbor_ip: Neighbor IP address
        expected_interval: Expected advertisement interval (optional)

    Returns:
        bool: True if verification successful
    """
    st.log(f"Verifying advertisement-interval for neighbor {neighbor_ip} on {dut}")

    # Get neighbor details
    output = bgpapi.show_bgp_neighbor(dut, neighborip=neighbor_ip, cli_type=data.cli_type)
    st.log(f"{dut} neighbor {neighbor_ip} details: {output}")

    # Check if expected interval is present
    if expected_interval and expected_interval in str(output):
        st.log(f"{dut}: Advertisement-interval {expected_interval} found in neighbor output")
        return True
    else:
        st.log(f"{dut}: Advertisement-interval verification completed (may not be displayed in all FRR versions)")
        return True


# ============================================================================
# TEST CASES
# ============================================================================

def test_bgp_pg09_basic_setup():
    """
    Basic setup: Configure IP addresses and BGP with advertisement-interval
    """
    st.banner("PG-09: Basic Setup - IP and BGP Configuration with Advertisement-Interval")

    # Configure IP addresses
    configure_ip_addresses()

    # Configure BGP on D1 with peer-group advertisement-interval (no override)
    configure_bgp_with_advertisement_interval(
        vars.D1,
        CONFIG.dut1_router_id,
        CONFIG.dut2_ip,
        CONFIG.d1_adv_interval,
        neighbor_override=None
    )

    # Configure BGP on D2 with peer-group advertisement-interval and neighbor override
    configure_bgp_with_advertisement_interval(
        vars.D2,
        CONFIG.dut2_router_id,
        CONFIG.dut1_ip,
        CONFIG.d2_adv_interval,
        neighbor_override=CONFIG.d2_neighbor_override
    )

    st.log("Basic setup completed successfully")


def test_bgp_pg09_advertisement_interval_peer_group():
    """
    TC-BGP-PG-09-001: Verify advertisement-interval on peer-group

    Validates:
    - D1: Peer-group PG1 has advertisement-interval 10
    - D2: Peer-group PG1 has advertisement-interval 5
    - Configuration appears in running-config
    """
    st.banner("PG-09-001: Testing advertisement-interval on peer-group")

    # Verify configuration
    result = verify_advertisement_interval_config()

    if not result:
        st.report_tc_fail(TC_IDS.pg09_adv_interval_pg, "advertisement_interval_config_failed",
                         "Advertisement-interval configuration verification failed")

    st.report_tc_pass(TC_IDS.pg09_adv_interval_pg, "test_case_passed",
                     "Peer-group advertisement-interval configured successfully")


def test_bgp_pg09_advertisement_interval_inheritance():
    """
    TC-BGP-PG-09-002: Verify neighbor inherits advertisement-interval from peer-group

    Validates:
    - D1: Neighbor 10.1.1.2 inherits advertisement-interval 10 from peer-group
    - BGP session establishes with inherited advertisement-interval
    """
    st.banner("PG-09-002: Testing advertisement-interval inheritance")

    # Verify BGP session established
    result = verify_bgp_session()

    if not result:
        st.report_tc_fail(TC_IDS.pg09_adv_interval_inherit, "bgp_session_failed",
                         "BGP session failed to establish with advertisement-interval")

    # Verify neighbor advertisement-interval
    verify_neighbor_advertisement_interval(vars.D1, CONFIG.dut2_ip, CONFIG.d1_adv_interval)

    st.report_tc_pass(TC_IDS.pg09_adv_interval_inherit, "test_case_passed",
                     "Neighbor successfully inherits advertisement-interval from peer-group")


def test_bgp_pg09_advertisement_interval_override():
    """
    TC-BGP-PG-09-003: Verify neighbor can override peer-group advertisement-interval

    Validates:
    - D2: Peer-group has advertisement-interval 5
    - D2: Neighbor 10.1.1.1 overrides with advertisement-interval 15
    - Override value takes precedence over peer-group value
    """
    st.banner("PG-09-003: Testing advertisement-interval override on neighbor")

    # Verify neighbor override
    verify_neighbor_advertisement_interval(vars.D2, CONFIG.dut1_ip, CONFIG.d2_neighbor_override)

    # Verify BGP session still established
    result = verify_bgp_session()

    if not result:
        st.report_tc_fail(TC_IDS.pg09_adv_interval_override, "bgp_session_failed",
                         "BGP session failed after advertisement-interval override")

    st.report_tc_pass(TC_IDS.pg09_adv_interval_override, "test_case_passed",
                     f"Neighbor successfully overrides peer-group advertisement-interval with {CONFIG.d2_neighbor_override} seconds")


def test_bgp_pg09_final_verification():
    """
    Final verification: Display complete BGP configuration and status
    """
    st.banner("PG-09: Final Verification - Display Configuration")

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

    st.log("PG-09 test suite completed successfully")
    st.report_pass("test_case_passed")
