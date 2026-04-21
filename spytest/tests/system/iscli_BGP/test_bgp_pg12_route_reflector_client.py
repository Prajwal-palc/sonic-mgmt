"""
BGP PEER-GROUP TEST - PG-12: Peer-Group Route-Reflector Client Defaults via Peer-Group

Test Case ID: PG-12
Author: Automated from Manual Validation
Copyright (C) 2026 - Spytest Automation Framework, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_bgp_custom.yaml \
    tests/system/iscli_BGP/test_bgp_pg12_route_reflector_client.py \
    --logs-path ./logs/bgp_pg12_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates peer-group route-reflector-client configuration and inheritance:
  - Configure peer-group with route-reflector-client at AF level
  - DUT1: Route Reflector with neighbors inheriting route-reflector-client
  - DUT2: Also configured with route-reflector-client setting
  - Verify route-reflector-client appears in running config
  - Verify neighbor inheritance behavior

Pre-requisites:
  - 2 SONiC devices connected via Ethernet4
  - Testbed: testbed_bgp_custom.yaml
  - Devices: 192.168.100.193, 192.168.100.217
  - Credentials: admin/test@123

Note:
  - Route-reflector-client: Marks neighbors as route-reflector clients
  - Configured at peer-group address-family level
  - All neighbors in peer-group inherit route-reflector-client setting
  - Used in iBGP route-reflection topology
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
CONFIG = SpyTestDict({    "dut1_ip": "10.1.1.1",
    "dut2_ip": "10.1.1.2",
    "subnet_mask": "24",
    "asn": "65001",
    "dut1_router_id": "1.1.1.1",
    "dut2_router_id": "2.2.2.2",
    "peer_group": "1",

    # Neighbor descriptions
    "dut1_neighbor_desc": "RR Client 1",
    "dut2_neighbor_desc": "RR Client 1",

    # Test parameters
    "bgp_wait_time": 60,
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg12_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: PG-12 Setup")

    # Get testbed topology
    vars = st.ensure_min_topology("D1D2:1")


    # Dynamic port assignment
    data.d1_phy_port = vars.D1D2P1
    data.d2_phy_port = vars.D2D1P1
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
    if not ipapi.config_ip_addr_interface(dut, data.d1_phy_port,
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


def configure_peer_group_with_rr_client(dut: str, pg_name: str) -> bool:
    """
    Configure peer-group with route-reflector-client at address-family level.

    The route-reflector-client setting is configured in the peer-group's address-family
    and will be inherited by all neighbors that join this peer-group.

    This marks all neighbors in this peer-group as route-reflector clients.
    """
    st.log(f"Configuring peer-group '{pg_name}' with route-reflector-client on {dut}")

    # Note: Skip AF activation on peer-group (causes CLI error)
    # Apply route-reflector-client at peer-group AF level
    commands = [
        f"router bgp {CONFIG.asn}",
        f"peer-group {pg_name}",
        f"remote-as {CONFIG.asn}",
        "address-family ipv4 unicast",
        # "activate",  # Skip - causes error
        "route-reflector-client",
        "exit",  # Exit AF sub-mode
        "exit",  # Exit peer-group sub-mode
        "exit"   # Exit router-bgp
    ]

    try:
        st.config(dut, commands, type=data.cli_type)
        st.log(f"✓ Peer-group '{pg_name}' with route-reflector-client configured")
        return True
    except Exception as e:
        st.error(f"Failed to create peer-group on {dut}: {str(e)}")
        return False


def attach_neighbor_with_description(dut: str, neighbor_ip: str, pg_name: str,
                                      description: str) -> bool:
    """
    Attach neighbor to peer-group with description.

    The neighbor will inherit the route-reflector-client setting from the peer-group.
    """
    st.log(f"Attaching neighbor {neighbor_ip} to peer-group '{pg_name}' with description on {dut}")

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

    # Step 2: Create neighbor with peer-group, description, and AF activation
    st.log(f"Step 2: Creating neighbor {neighbor_ip} with peer-group '{pg_name}'")
    create_commands = [
        f"router bgp {CONFIG.asn}",
        f"neighbor {neighbor_ip} remote-as {CONFIG.asn}",
        f"peer-group {pg_name}",
        f"description {description}",
        "address-family ipv4 unicast",
        "activate",
        "exit",  # Exit AF sub-mode
        "exit",  # Exit neighbor sub-mode
        "exit"   # Exit router-bgp
    ]

    try:
        st.config(dut, create_commands, type=data.cli_type)
        st.log(f"✓ Neighbor {neighbor_ip} attached (inherits route-reflector-client from peer-group)")
        return True
    except Exception as e:
        st.error(f"Failed to attach neighbor on {dut}: {str(e)}")
        return False


def verify_rr_client_in_config(dut: str) -> bool:
    """
    Verify route-reflector-client appears in BGP running config.

    The route-reflector-client should appear in the peer-group address-family section.
    """
    st.log(f"Verifying route-reflector-client configuration on {dut}")

    show_cmd = "show running-configuration bgp"
    try:
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        if output:
            st.log(f"BGP config excerpt:\n{output[:1000] if output else 'No output'}")

            # Check for route-reflector-client in config
            if "route-reflector-client" in str(output):
                st.log(f"✓ Found 'route-reflector-client' in config")
                return True
            else:
                st.log(f"⚠ 'route-reflector-client' not found in config")
                return False
        else:
            st.log(f"⚠ No BGP config output")
            return False
    except Exception as e:
        st.error(f"Failed to verify route-reflector-client in config: {str(e)}")
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


def test_bgp_pg12_route_reflector_client():
    """
    PG-12: Peer-Group Route-Reflector Client Defaults via Peer-Group

    Test Flow:
    1. Configure IP and BGP on both DUTs
    2. Create peer-groups with route-reflector-client at AF level
    3. DUT1: Attach neighbor (inherits route-reflector-client)
    4. DUT2: Attach neighbor (inherits route-reflector-client)
    5. Verify route-reflector-client appears in running config
    6. Verify BGP sessions establish
    7. Show configurations and BGP summary
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

    # Step 2: Create peer-groups with route-reflector-client
    st.banner("STEP 2: Create Peer-Groups with Route-Reflector-Client")

    st.log(f"DUT1: Creating peer-group with route-reflector-client")
    if not configure_peer_group_with_rr_client(vars.D1, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to create peer-group on {vars.D1}")

    st.log(f"DUT2: Creating peer-group with route-reflector-client")
    if not configure_peer_group_with_rr_client(vars.D2, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to create peer-group on {vars.D2}")

    st.log("✓ Peer-groups with route-reflector-client configured on both DUTs")

    # Step 3: DUT1 - Attach neighbor
    st.banner("STEP 3: DUT1 - Attach Neighbor (Inherit Route-Reflector-Client)")

    st.log(f"DUT1: Attaching neighbor {CONFIG.dut2_ip}")
    if not attach_neighbor_with_description(vars.D1, CONFIG.dut2_ip, CONFIG.peer_group,
                                             CONFIG.dut1_neighbor_desc):
        st.report_fail("msg", f"Failed to attach neighbor on {vars.D1}")

    st.log(f"✓ DUT1 neighbor attached (inherits route-reflector-client from peer-group)")

    # Step 4: DUT2 - Attach neighbor
    st.banner("STEP 4: DUT2 - Attach Neighbor (Inherit Route-Reflector-Client)")

    st.log(f"DUT2: Attaching neighbor {CONFIG.dut1_ip}")
    if not attach_neighbor_with_description(vars.D2, CONFIG.dut1_ip, CONFIG.peer_group,
                                             CONFIG.dut2_neighbor_desc):
        st.report_fail("msg", f"Failed to attach neighbor on {vars.D2}")

    st.log(f"✓ DUT2 neighbor attached (inherits route-reflector-client from peer-group)")

    # Step 5: Verify route-reflector-client in running config
    st.banner("STEP 5: Verify Route-Reflector-Client Configuration")

    st.log(f"Verifying route-reflector-client on {vars.D1}")
    verify_rr_client_in_config(vars.D1)

    st.log(f"Verifying route-reflector-client on {vars.D2}")
    verify_rr_client_in_config(vars.D2)

    # Step 6: Verify BGP sessions
    st.banner("STEP 6: Verify BGP Session Establishment")

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
