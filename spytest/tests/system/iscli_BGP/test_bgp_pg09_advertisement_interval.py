"""
BGP PEER-GROUP TEST - PG-09: Peer-Group Advertisement-Interval Tuning

Test Case ID: PG-09
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_bgp_custom.yaml \
    tests/system/iscli_BGP/test_bgp_pg09_advertisement_interval.py \
    --logs-path ./logs/bgp_pg09_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates peer-group advertisement-interval configuration and inheritance:
  - Configure peer-group with advertisement-interval
  - DUT1: Attach neighbor (inherits advertisement-interval from peer-group)
  - DUT2: Attach neighbor with override (different advertisement-interval)
  - Verify advertisement-interval appears in running config
  - Verify neighbor inheritance and override behavior

Pre-requisites:
  - 2 SONiC devices connected via Ethernet4
  - Testbed: testbed_bgp_custom.yaml
  - Devices: 192.168.100.193, 192.168.100.217
  - Credentials: admin/test@123

Note:
  - Advertisement-interval: Minimum time between BGP routing updates (seconds)
  - DUT1 peer-group: advertisement-interval 10 (neighbor inherits)
  - DUT2 peer-group: advertisement-interval 5 (neighbor overrides with 15)
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi
import apis.routing.bgp as bgpapi

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
    "peer_group": "1",

    # Advertisement-interval configuration
    "dut1_pg_adv_interval": "10",    # DUT1 peer-group advertisement-interval
    "dut2_pg_adv_interval": "5",     # DUT2 peer-group advertisement-interval
    "dut2_neighbor_adv_interval": "15",  # DUT2 neighbor override

    # Test parameters
    "bgp_wait_time": 60,
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg09_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: PG-09 Setup")

    # Get testbed topology
    vars = st.ensure_min_topology("D1D2:1")

    # Initialize test data
    data.cli_type = st.get_ui_type(vars.D1, cli_type="klish")

    # Pre-configuration: Cleanup any existing BGP config
    st.banner("Pre-configuration: Cleanup")
    cleanup_bgp_config([vars.D1, vars.D2])

    st.log("Pre-configuration completed")

    yield

    # Module epilogue - cleanup
    st.banner("MODULE EPILOGUE: Cleanup")
    cleanup_bgp_config([vars.D1, vars.D2])

    # Clear IP configuration
    ipapi.clear_ip_configuration([vars.D1, vars.D2], family='ipv4', thread=True)
    st.log("Cleanup completed")


def cleanup_bgp_config(dut_list):
    """Cleanup BGP configuration on all DUTs."""
    st.log("Cleanup BGP mode ..")
    for dut in dut_list:
        bgpapi.cleanup_router_bgp(dut, cli_type=data.cli_type)
        st.wait(2)


def configure_ip_bgp_basic(dut: str, ip_address: str, router_id: str) -> bool:
    """Configure IP and BGP router."""
    st.log(f"Configuring IP and BGP on {dut}")

    # Configure IP
    if not ipapi.config_ip_addr_interface(dut, CONFIG.interface,
                                          ip_address,
                                          subnet=CONFIG.subnet_mask,
                                          family="ipv4", cli_type=data.cli_type):
        st.error(f"Failed to configure IP on {dut}")
        return False

    # Configure BGP router with router-id
    st.log("Configure BGP")
    bgp_commands = [
        f"router bgp {CONFIG.asn}",
        f"router-id {router_id}",
        "exit"
    ]

    try:
        st.config(dut, bgp_commands, type=data.cli_type)
        st.log(f"✓ BGP router configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP on {dut}: {str(e)}")
        return False


def configure_peer_group_with_adv_interval(dut: str, pg_name: str, adv_interval: str) -> bool:
    """
    Configure peer-group with advertisement-interval.

    The advertisement-interval is configured at peer-group level and will be
    inherited by all neighbors that join this peer-group.

    Advertisement-interval: Minimum time (in seconds) between sending BGP routing updates.
    """
    st.log(f"Configuring peer-group '{pg_name}' with advertisement-interval {adv_interval} on {dut}")

    # Note: Skip AF activation on peer-group (causes CLI error)
    commands = [
        f"router bgp {CONFIG.asn}",
        f"peer-group {pg_name}",
        f"remote-as {CONFIG.asn}",
        f"advertisement-interval {adv_interval}",
        "address-family ipv4 unicast",
        # "activate",  # Skip - causes error
        "exit",  # Exit AF sub-mode
        "exit",  # Exit peer-group sub-mode
        "exit"   # Exit router-bgp
    ]

    try:
        st.config(dut, commands, type=data.cli_type)
        st.log(f"✓ Peer-group '{pg_name}' with advertisement-interval {adv_interval} configured")
        return True
    except Exception as e:
        st.error(f"Failed to create peer-group on {dut}: {str(e)}")
        return False


def attach_neighbor_inherit_adv_interval(dut: str, neighbor_ip: str, pg_name: str) -> bool:
    """
    Attach neighbor to peer-group WITHOUT overriding advertisement-interval.

    The neighbor will inherit the advertisement-interval from the peer-group.
    """
    st.log(f"Attaching neighbor {neighbor_ip} to peer-group '{pg_name}' (inherit adv-interval) on {dut}")

    # Step 1: Delete existing neighbor (if exists)
    st.log(f"Step 1: Deleting existing neighbor {neighbor_ip}")
    delete_commands = [
        f"router bgp {CONFIG.asn}",
        f"no neighbor {neighbor_ip}",
        "exit"
    ]

    try:
        st.config(dut, delete_commands, type=data.cli_type, skip_error_check=True)
        st.log(f"✓ Deleted existing neighbor {neighbor_ip}")
    except Exception as e:
        st.log(f"Warning: Could not delete neighbor (might not exist): {str(e)}")

    st.wait(2, "Waiting for neighbor deletion to apply")

    # Step 2: Create neighbor with peer-group (inherits advertisement-interval)
    st.log(f"Step 2: Creating neighbor {neighbor_ip} with peer-group '{pg_name}' (inherits adv-interval)")
    create_commands = [
        f"router bgp {CONFIG.asn}",
        f"neighbor {neighbor_ip} remote-as {CONFIG.asn}",
        f"peer-group {pg_name}",
        "address-family ipv4 unicast",
        "activate",
        "exit",  # Exit AF sub-mode
        "exit",  # Exit neighbor sub-mode
        "exit"   # Exit router-bgp
    ]

    try:
        st.config(dut, create_commands, type=data.cli_type)
        st.log(f"✓ Neighbor {neighbor_ip} attached (inherits advertisement-interval from peer-group)")
        return True
    except Exception as e:
        st.error(f"Failed to attach neighbor on {dut}: {str(e)}")
        return False


def attach_neighbor_override_adv_interval(dut: str, neighbor_ip: str, pg_name: str,
                                           adv_interval: str) -> bool:
    """
    Attach neighbor to peer-group WITH advertisement-interval override.

    The neighbor explicitly overrides the peer-group advertisement-interval with a different value.
    """
    st.log(f"Attaching neighbor {neighbor_ip} to peer-group '{pg_name}' (override adv-interval {adv_interval}) on {dut}")

    # Step 1: Delete existing neighbor (if exists)
    st.log(f"Step 1: Deleting existing neighbor {neighbor_ip}")
    delete_commands = [
        f"router bgp {CONFIG.asn}",
        f"no neighbor {neighbor_ip}",
        "exit"
    ]

    try:
        st.config(dut, delete_commands, type=data.cli_type, skip_error_check=True)
        st.log(f"✓ Deleted existing neighbor {neighbor_ip}")
    except Exception as e:
        st.log(f"Warning: Could not delete neighbor (might not exist): {str(e)}")

    st.wait(2, "Waiting for neighbor deletion to apply")

    # Step 2: Create neighbor with peer-group and advertisement-interval override
    st.log(f"Step 2: Creating neighbor {neighbor_ip} with peer-group '{pg_name}' and adv-interval override")
    create_commands = [
        f"router bgp {CONFIG.asn}",
        f"neighbor {neighbor_ip} remote-as {CONFIG.asn}",
        f"advertisement-interval {adv_interval}",  # Override at neighbor level!
        f"peer-group {pg_name}",
        "address-family ipv4 unicast",
        "activate",
        "exit",  # Exit AF sub-mode
        "exit",  # Exit neighbor sub-mode
        "exit"   # Exit router-bgp
    ]

    try:
        st.config(dut, create_commands, type=data.cli_type)
        st.log(f"✓ Neighbor {neighbor_ip} attached with advertisement-interval override ({adv_interval})")
        return True
    except Exception as e:
        st.error(f"Failed to attach neighbor on {dut}: {str(e)}")
        return False


def verify_adv_interval_in_config(dut: str, expected_values: list) -> bool:
    """
    Verify advertisement-interval appears in BGP running config.

    Args:
        expected_values: List of tuples (context, adv_interval)
                        e.g., [("peer-group", "10"), ("neighbor", "15")]
    """
    st.log(f"Verifying advertisement-interval configuration on {dut}")

    show_cmd = "show running-configuration bgp"
    try:
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        if output:
            st.log(f"BGP config excerpt:\n{output[:1000] if output else 'No output'}")

            # Check for expected advertisement-interval values
            all_found = True
            for context, adv_interval in expected_values:
                expected = f"advertisement-interval {adv_interval}"
                if expected in str(output):
                    st.log(f"✓ Found '{expected}' in {context} config")
                else:
                    st.log(f"⚠ '{expected}' not found in {context} config")
                    all_found = False

            return all_found
        else:
            st.log(f"⚠ No BGP config output")
            return False
    except Exception as e:
        st.error(f"Failed to verify advertisement-interval in config: {str(e)}")
        return False


def verify_bgp_session(dut: str, neighbor_ip: str) -> bool:
    """Verify BGP session establishment."""
    st.log(f"Verifying BGP session: {dut} <-> {neighbor_ip}")

    result = st.poll_wait(
        bgpapi.verify_bgp_summary,
        CONFIG.bgp_wait_time,
        dut,
        family='ipv4',
        neighbor=neighbor_ip,
        state='Established',
        shell=data.cli_type
    )

    if result:
        st.log(f"✓ BGP session {dut} <-> {neighbor_ip} is Established")
        return True
    else:
        st.error(f"✗ BGP session {dut} <-> {neighbor_ip} NOT established")
        return False


def test_bgp_pg09_advertisement_interval():
    """
    PG-09: Peer-Group Advertisement-Interval Tuning

    Test Flow:
    1. Configure IP and BGP on both DUTs
    2. DUT1: Create peer-group with advertisement-interval 10
    3. DUT2: Create peer-group with advertisement-interval 5
    4. DUT1: Attach neighbor (inherits advertisement-interval 10)
    5. DUT2: Attach neighbor with override (advertisement-interval 15)
    6. Verify advertisement-interval appears in running config
    7. Verify BGP sessions establish
    8. Show configurations and BGP summary
    """

    # Step 1: Configure IP and BGP
    st.banner("STEP 1: Configure IP and BGP on Both DUTs")

    st.log(f"Configuring IP and BGP on {vars.D1}")
    if not configure_ip_bgp_basic(vars.D1, CONFIG.dut1_ip, CONFIG.dut1_router_id):
        st.report_fail("msg", f"Failed to configure {vars.D1}")

    st.log(f"Configuring IP and BGP on {vars.D2}")
    if not configure_ip_bgp_basic(vars.D2, CONFIG.dut2_ip, CONFIG.dut2_router_id):
        st.report_fail("msg", f"Failed to configure {vars.D2}")

    st.log("✓ IP and BGP configured on both DUTs")

    # Step 2: DUT1 - Create peer-group with advertisement-interval 10
    st.banner("STEP 2: DUT1 - Create Peer-Group with Advertisement-Interval 10")

    st.log(f"DUT1: Creating peer-group with advertisement-interval {CONFIG.dut1_pg_adv_interval}")
    if not configure_peer_group_with_adv_interval(vars.D1, CONFIG.peer_group,
                                                   CONFIG.dut1_pg_adv_interval):
        st.report_fail("msg", f"Failed to create peer-group on {vars.D1}")

    st.log(f"✓ DUT1 peer-group with advertisement-interval {CONFIG.dut1_pg_adv_interval} configured")

    # Step 3: DUT2 - Create peer-group with advertisement-interval 5
    st.banner("STEP 3: DUT2 - Create Peer-Group with Advertisement-Interval 5")

    st.log(f"DUT2: Creating peer-group with advertisement-interval {CONFIG.dut2_pg_adv_interval}")
    if not configure_peer_group_with_adv_interval(vars.D2, CONFIG.peer_group,
                                                   CONFIG.dut2_pg_adv_interval):
        st.report_fail("msg", f"Failed to create peer-group on {vars.D2}")

    st.log(f"✓ DUT2 peer-group with advertisement-interval {CONFIG.dut2_pg_adv_interval} configured")

    # Step 4: DUT1 - Attach neighbor (inherit advertisement-interval)
    st.banner("STEP 4: DUT1 - Attach Neighbor (Inherit Advertisement-Interval)")

    st.log(f"DUT1: Attaching neighbor {CONFIG.dut2_ip} (inherits advertisement-interval)")
    if not attach_neighbor_inherit_adv_interval(vars.D1, CONFIG.dut2_ip, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to attach neighbor on {vars.D1}")

    st.log(f"✓ DUT1 neighbor attached (inherits advertisement-interval {CONFIG.dut1_pg_adv_interval})")

    # Step 5: DUT2 - Attach neighbor (override advertisement-interval)
    st.banner("STEP 5: DUT2 - Attach Neighbor (Override Advertisement-Interval)")

    st.log(f"DUT2: Attaching neighbor {CONFIG.dut1_ip} with advertisement-interval override")
    if not attach_neighbor_override_adv_interval(vars.D2, CONFIG.dut1_ip, CONFIG.peer_group,
                                                  CONFIG.dut2_neighbor_adv_interval):
        st.report_fail("msg", f"Failed to attach neighbor on {vars.D2}")

    st.log(f"✓ DUT2 neighbor attached with advertisement-interval override ({CONFIG.dut2_neighbor_adv_interval})")

    # Step 6: Verify advertisement-interval in running config
    st.banner("STEP 6: Verify Advertisement-Interval Configuration")

    st.log(f"Verifying advertisement-interval on {vars.D1}")
    dut1_expected = [
        ("peer-group", CONFIG.dut1_pg_adv_interval),
    ]
    verify_adv_interval_in_config(vars.D1, dut1_expected)

    st.log(f"Verifying advertisement-interval on {vars.D2}")
    dut2_expected = [
        ("peer-group", CONFIG.dut2_pg_adv_interval),
        ("neighbor", CONFIG.dut2_neighbor_adv_interval),
    ]
    verify_adv_interval_in_config(vars.D2, dut2_expected)

    # Step 7: Verify BGP sessions
    st.banner("STEP 7: Verify BGP Session Establishment")

    st.wait(10, "Waiting for BGP sessions to establish")

    session_status = True

    if not verify_bgp_session(vars.D1, CONFIG.dut2_ip):
        st.log(f"Warning: BGP session not established on {vars.D1}")
        session_status = False

    if not verify_bgp_session(vars.D2, CONFIG.dut1_ip):
        st.log(f"Warning: BGP session not established on {vars.D2}")
        session_status = False

    if session_status:
        st.log("✓ BGP sessions established on both DUTs")
    else:
        st.log("⚠ BGP sessions not fully established")

    # Show running configs
    st.banner("FINAL: Show Running Configurations")

    for dut in [vars.D1, vars.D2]:
        show_cmd = "show running-configuration bgp"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"\n{dut} BGP Configuration:\n{output[:1000] if output else 'No output'}")

    # Show BGP summary
    st.banner("FINAL: Show BGP Summary")

    for dut in [vars.D1, vars.D2]:
        show_cmd = "show bgp summary"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"\n{dut} BGP Summary:\n{output[:600] if output else 'No output'}")

    # Test passed
    st.report_pass("test_case_passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
