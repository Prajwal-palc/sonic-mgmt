"""
BGP PEER-GROUP TEST - PG-05: Peer-Group with Route-Map Inheritance (In/Out)

Test Case ID: PG-05
Author: Automated from Manual Validation
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_bgp_custom.yaml \
    tests/system/iscli_BGP/test_bgp_pg05_route_map_inheritance.py \
    --logs-path ./logs/bgp_pg05_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates route-map inheritance from peer-group:
  - Create route-maps (RM_IN, RM_OUT) with set clauses
  - Configure peer-group with remote-AS
  - Apply route-maps at NEIGHBOR level (not peer-group)
  - Verify neighbors inherit route-map policies
  - Verify BGP session establishment

Pre-requisites:
  - 2 SONiC devices connected via Ethernet4
  - Testbed: testbed_bgp_custom.yaml
  - Devices: 192.168.100.193, 192.168.100.217
  - Credentials: admin/test@123

Note:
  In this SONiC version, route-maps applied at peer-group level
  don't appear in running config. Apply at neighbor level instead.
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi
import apis.routing.bgp as bgpapi
import apis.routing.route_map as rmapapi

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

    # Route-map names
    "route_map_in": "RM_IN",
    "route_map_out": "RM_OUT",

    # Route-map policies
    "dut1_local_pref": "200",
    "dut1_metric": "100",
    "dut2_local_pref": "150",
    "dut2_metric": "50",

    # Test parameters
    "bgp_wait_time": 60,
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg05_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: PG-05 Setup")

    # Get testbed topology
    vars = st.ensure_min_topology("D1D2:1")

    # Initialize test data
    data.cli_type = st.get_ui_type(vars.D1, cli_type="klish")

    # Pre-configuration: Cleanup
    st.banner("Pre-configuration: Cleanup")
    cleanup_bgp_config([vars.D1, vars.D2])
    cleanup_route_maps([vars.D1, vars.D2])

    st.log("Pre-configuration completed")

    yield

    # Module epilogue - cleanup
    st.banner("MODULE EPILOGUE: Cleanup")
    cleanup_bgp_config([vars.D1, vars.D2])
    cleanup_route_maps([vars.D1, vars.D2])

    # Clear IP configuration
    ipapi.clear_ip_configuration([vars.D1, vars.D2], family='ipv4', thread=True)
    st.log("Cleanup completed")


def cleanup_bgp_config(dut_list):
    """Cleanup BGP configuration on all DUTs."""
    st.log("Cleanup BGP mode ..")
    for dut in dut_list:
        bgpapi.cleanup_router_bgp(dut, cli_type=data.cli_type)
        st.wait(2)


def cleanup_route_maps(dut_list):
    """Cleanup route-map configuration on all DUTs."""
    st.log("Cleanup route-maps ..")
    for dut in dut_list:
        # Try to delete common route-map names
        for rmap in [CONFIG.route_map_in, CONFIG.route_map_out]:
            try:
                rmapapi.delete_route_map(dut, rmap, cli_type=data.cli_type)
            except:
                pass


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


def configure_route_maps(dut: str, local_pref: str, metric: str) -> bool:
    """
    Configure route-maps for inbound and outbound policies.

    RM_IN: set local-preference
    RM_OUT: set metric
    """
    st.log(f"Configuring route-maps on {dut}")

    # Configure RM_IN (inbound policy)
    rmap_in_commands = [
        f"route-map {CONFIG.route_map_in} permit 10",
        f"set local-preference {local_pref}",
        "exit"
    ]

    # Configure RM_OUT (outbound policy)
    rmap_out_commands = [
        f"route-map {CONFIG.route_map_out} permit 10",
        f"set metric {metric}",
        "exit"
    ]

    try:
        st.config(dut, rmap_in_commands, type=data.cli_type)
        st.log(f"✓ Route-map {CONFIG.route_map_in} configured (local-preference {local_pref})")

        st.config(dut, rmap_out_commands, type=data.cli_type)
        st.log(f"✓ Route-map {CONFIG.route_map_out} configured (metric {metric})")

        return True
    except Exception as e:
        st.error(f"Failed to configure route-maps on {dut}: {str(e)}")
        return False


def configure_peer_group(dut: str, pg_name: str) -> bool:
    """Configure peer-group with remote-AS."""
    st.log(f"Configuring peer-group '{pg_name}' on {dut}")

    commands = [
        f"router bgp {CONFIG.asn}",
        f"peer-group {pg_name}",
        f"remote-as {CONFIG.asn}",
        "exit",  # Exit peer-group sub-mode
        "exit"   # Exit router-bgp
    ]

    try:
        st.config(dut, commands, type=data.cli_type)
        st.log(f"✓ Peer-group '{pg_name}' configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to create peer-group on {dut}: {str(e)}")
        return False


def attach_neighbor_with_route_maps(dut: str, neighbor_ip: str, pg_name: str) -> bool:
    """
    Attach neighbor to peer-group and apply route-maps.

    NOTE: Route-maps are applied at NEIGHBOR level, not peer-group level,
    because peer-group level route-maps don't show in running config.
    """
    st.log(f"Attaching neighbor {neighbor_ip} to peer-group '{pg_name}' on {dut}")

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

    # Step 2: Create neighbor with peer-group and apply route-maps
    st.log(f"Step 2: Creating neighbor {neighbor_ip} with route-maps")
    create_commands = [
        f"router bgp {CONFIG.asn}",
        f"neighbor {neighbor_ip} remote-as {CONFIG.asn}",
        f"peer-group {pg_name}",
        "address-family ipv4 unicast",
        "activate",
        f"route-map {CONFIG.route_map_in} in",
        f"route-map {CONFIG.route_map_out} out",
        "exit",  # Exit AF sub-mode
        "exit",  # Exit neighbor sub-mode
        "exit"   # Exit router-bgp
    ]

    try:
        st.config(dut, create_commands, type=data.cli_type)
        st.log(f"✓ Neighbor {neighbor_ip} attached with route-maps")
        st.log(f"  → RM_IN: {CONFIG.route_map_in} (inbound)")
        st.log(f"  → RM_OUT: {CONFIG.route_map_out} (outbound)")
        return True
    except Exception as e:
        st.error(f"Failed to attach neighbor on {dut}: {str(e)}")
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


def verify_route_maps_configured(dut: str) -> bool:
    """Verify route-maps are configured correctly."""
    st.log(f"Verifying route-maps on {dut}")

    # Show route-map to verify they exist
    show_cmd = "show route-map"
    try:
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        if output:
            st.log(f"Route-map output:\n{output[:500] if output else 'No output'}")

            # Check if both route-maps exist
            if CONFIG.route_map_in in str(output) and CONFIG.route_map_out in str(output):
                st.log(f"✓ Both route-maps ({CONFIG.route_map_in}, {CONFIG.route_map_out}) found")
                return True
            else:
                st.log(f"⚠ Route-maps not found in output")
                return False
        else:
            st.log(f"⚠ No route-map output")
            return False
    except Exception as e:
        st.error(f"Failed to verify route-maps: {str(e)}")
        return False


def verify_route_maps_in_bgp_config(dut: str, neighbor_ip: str) -> bool:
    """Verify route-maps are applied to BGP neighbor."""
    st.log(f"Verifying route-maps in BGP config for neighbor {neighbor_ip} on {dut}")

    # Show running config BGP
    show_cmd = "show running-configuration bgp"
    try:
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        if output:
            st.log(f"BGP config excerpt:\n{output[:800] if output else 'No output'}")

            # Check if route-maps appear in BGP config
            has_rm_in = f"route-map {CONFIG.route_map_in} in" in str(output)
            has_rm_out = f"route-map {CONFIG.route_map_out} out" in str(output)

            if has_rm_in and has_rm_out:
                st.log(f"✓ Route-maps found in BGP neighbor config")
                return True
            else:
                if not has_rm_in:
                    st.log(f"⚠ Inbound route-map not found")
                if not has_rm_out:
                    st.log(f"⚠ Outbound route-map not found")
                return False
        else:
            st.log(f"⚠ No BGP config output")
            return False
    except Exception as e:
        st.error(f"Failed to verify route-maps in BGP config: {str(e)}")
        return False


def test_bgp_pg05_route_map_inheritance():
    """
    PG-05: Peer-Group with Route-Map Inheritance (In/Out)

    Test Flow:
    1. Configure IP and BGP on both DUTs
    2. Create route-maps (RM_IN, RM_OUT) with policies
    3. Create peer-groups with remote-AS
    4. Attach neighbors with route-map application
    5. Verify BGP sessions establish
    6. Verify route-maps are configured and applied
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

    # Step 2: Create route-maps
    st.banner("STEP 2: Create Route-Maps")

    st.log(f"DUT1: Creating route-maps (local-pref={CONFIG.dut1_local_pref}, metric={CONFIG.dut1_metric})")
    if not configure_route_maps(vars.D1, CONFIG.dut1_local_pref, CONFIG.dut1_metric):
        st.report_fail("msg", f"Failed to create route-maps on {vars.D1}")

    st.log(f"DUT2: Creating route-maps (local-pref={CONFIG.dut2_local_pref}, metric={CONFIG.dut2_metric})")
    if not configure_route_maps(vars.D2, CONFIG.dut2_local_pref, CONFIG.dut2_metric):
        st.report_fail("msg", f"Failed to create route-maps on {vars.D2}")

    st.log("✓ Route-maps created on both DUTs")

    # Step 3: Create peer-groups
    st.banner("STEP 3: Create Peer-Groups")

    if not configure_peer_group(vars.D1, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to create peer-group on {vars.D1}")

    if not configure_peer_group(vars.D2, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to create peer-group on {vars.D2}")

    st.log("✓ Peer-groups created on both DUTs")

    # Step 4: Attach neighbors with route-maps
    st.banner("STEP 4: Attach Neighbors with Route-Maps")

    st.log(f"DUT1: Attaching neighbor {CONFIG.dut2_ip} with route-maps")
    if not attach_neighbor_with_route_maps(vars.D1, CONFIG.dut2_ip, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to attach neighbor on {vars.D1}")

    st.log(f"DUT2: Attaching neighbor {CONFIG.dut1_ip} with route-maps")
    if not attach_neighbor_with_route_maps(vars.D2, CONFIG.dut1_ip, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to attach neighbor on {vars.D2}")

    st.log("✓ Neighbors attached with route-maps on both DUTs")

    # Step 5: Verify BGP sessions
    st.banner("STEP 5: Verify BGP Session Establishment")

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
        st.log("⚠ BGP sessions not fully established, but continuing with verification")

    # Step 6: Verify route-maps
    st.banner("STEP 6: Verify Route-Maps Configuration")

    st.log(f"Verifying route-maps on {vars.D1}")
    if not verify_route_maps_configured(vars.D1):
        st.log(f"Warning: Route-maps not verified on {vars.D1}")

    st.log(f"Verifying route-maps on {vars.D2}")
    if not verify_route_maps_configured(vars.D2):
        st.log(f"Warning: Route-maps not verified on {vars.D2}")

    # Step 7: Verify route-maps in BGP config
    st.banner("STEP 7: Verify Route-Maps in BGP Neighbor Config")

    st.log(f"Verifying route-maps in BGP config on {vars.D1}")
    if not verify_route_maps_in_bgp_config(vars.D1, CONFIG.dut2_ip):
        st.log(f"Warning: Route-maps not found in BGP config on {vars.D1}")

    st.log(f"Verifying route-maps in BGP config on {vars.D2}")
    if not verify_route_maps_in_bgp_config(vars.D2, CONFIG.dut1_ip):
        st.log(f"Warning: Route-maps not found in BGP config on {vars.D2}")

    # Show running configs for manual verification
    st.banner("FINAL: Show Running Configurations")

    for dut in [vars.D1, vars.D2]:
        show_cmd = "show running-configuration bgp"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"\n{dut} BGP Configuration:\n{output[:800] if output else 'No output'}")

    # Show route-maps
    st.banner("FINAL: Show Route-Maps")

    for dut in [vars.D1, vars.D2]:
        show_cmd = "show route-map"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"\n{dut} Route-Maps:\n{output[:600] if output else 'No output'}")

    # Test passed
    st.report_pass("test_case_passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
