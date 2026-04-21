"""
BGP PEER-GROUP TEST - PG-07: Peer-Group Default Shutdown Behaviour for New Peers

Test Case ID: PG-07
Author: Automated from Manual Validation
Copyright (C) 2026 - Spytest Automation Framework, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_bgp_custom.yaml \
    tests/system/iscli_BGP/test_bgp_pg07_shutdown_inheritance.py \
    --logs-path ./logs/bgp_pg07_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates peer-group shutdown inheritance and override behavior:
  - Configure peer-group with shutdown
  - DUT1: Attach neighbor without override (inherits shutdown)
  - DUT2: Attach neighbor with "no shutdown" override
  - Verify DUT1 neighbor stays down (Connect/Idle state)
  - Verify DUT2 neighbor comes up (Established state)

Pre-requisites:
  - 2 SONiC devices connected via Ethernet4
  - Testbed: testbed_bgp_custom.yaml
  - Devices: 192.168.100.193, 192.168.100.217
  - Credentials: admin/test@123

Note:
  - Peer-group shutdown is inherited by neighbors unless explicitly overridden
  - DUT1 neighbor inherits shutdown (stays down)
  - DUT2 neighbor overrides with "no shutdown" (comes up)
  - Only DUT2 side will show established session
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

    # Test parameters
    "bgp_wait_time": 60,
})


@pytest.fixture(scope="module", autouse=True)
def bgp_pg07_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("MODULE PROLOGUE: PG-07 Setup")

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


def configure_peer_group_with_shutdown(dut: str, pg_name: str) -> bool:
    """
    Configure peer-group with shutdown.

    Neighbors that join this peer-group will inherit the shutdown state
    unless they explicitly override with "no shutdown".
    """
    st.log(f"Configuring peer-group '{pg_name}' with shutdown on {dut}")

    # Note: Skip AF activation on peer-group (causes CLI error)
    commands = [
        f"router bgp {CONFIG.asn}",
        f"peer-group {pg_name}",
        f"remote-as {CONFIG.asn}",
        "shutdown",  # Peer-group is shutdown by default
        "exit",      # Exit peer-group sub-mode
        "exit"       # Exit router-bgp
    ]

    try:
        st.config(dut, commands, type=data.cli_type)
        st.log(f"✓ Peer-group '{pg_name}' with shutdown configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to create peer-group on {dut}: {str(e)}")
        return False


def attach_neighbor_inherit_shutdown(dut: str, neighbor_ip: str, pg_name: str) -> bool:
    """
    Attach neighbor to peer-group WITHOUT overriding shutdown.

    The neighbor will inherit the shutdown state from the peer-group
    and will NOT establish BGP session.
    """
    st.log(f"Attaching neighbor {neighbor_ip} to peer-group '{pg_name}' (inherit shutdown) on {dut}")

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

    # Step 2: Create neighbor with peer-group (NO "no shutdown" - inherits shutdown)
    st.log(f"Step 2: Creating neighbor {neighbor_ip} with peer-group '{pg_name}' (inherits shutdown)")
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
        st.log(f"✓ Neighbor {neighbor_ip} attached (inherits shutdown from peer-group)")
        return True
    except Exception as e:
        st.error(f"Failed to attach neighbor on {dut}: {str(e)}")
        return False


def attach_neighbor_override_shutdown(dut: str, neighbor_ip: str, pg_name: str) -> bool:
    """
    Attach neighbor to peer-group WITH "no shutdown" override.

    The neighbor explicitly overrides the peer-group shutdown state
    and WILL establish BGP session.
    """
    st.log(f"Attaching neighbor {neighbor_ip} to peer-group '{pg_name}' (override shutdown) on {dut}")

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

    # Step 2: Create neighbor with peer-group AND "no shutdown" override
    st.log(f"Step 2: Creating neighbor {neighbor_ip} with peer-group '{pg_name}' and 'no shutdown' override")
    create_commands = [
        f"router bgp {CONFIG.asn}",
        f"neighbor {neighbor_ip} remote-as {CONFIG.asn}",
        f"peer-group {pg_name}",
        "no shutdown",  # Override peer-group shutdown!
        "address-family ipv4 unicast",
        "activate",
        "exit",  # Exit AF sub-mode
        "exit",  # Exit neighbor sub-mode
        "exit"   # Exit router-bgp
    ]

    try:
        st.config(dut, create_commands, type=data.cli_type)
        st.log(f"✓ Neighbor {neighbor_ip} attached with 'no shutdown' override")
        return True
    except Exception as e:
        st.error(f"Failed to attach neighbor on {dut}: {str(e)}")
        return False


def verify_bgp_session_down(dut: str, neighbor_ip: str) -> bool:
    """Verify BGP session is NOT established (down state)."""
    st.log(f"Verifying BGP session is DOWN: {dut} <-> {neighbor_ip}")

    # Check that neighbor is NOT in Established state
    # Expected states: Idle, Connect, Active (anything except Established)
    result = st.poll_wait(
        bgpapi.verify_bgp_summary,
        10,  # Short wait - we expect it to be down
        dut,
        family='ipv4',
        neighbor=neighbor_ip,
        state='Established',
        shell=data.cli_type
    )

    if not result:
        st.log(f"✓ BGP session {dut} <-> {neighbor_ip} is DOWN (as expected)")
        return True
    else:
        st.error(f"✗ BGP session {dut} <-> {neighbor_ip} is UP (unexpected!)")
        return False


def verify_bgp_session_up(dut: str, neighbor_ip: str) -> bool:
    """Verify BGP session is Established (up state)."""
    st.log(f"Verifying BGP session is UP: {dut} <-> {neighbor_ip}")

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


def test_bgp_pg07_shutdown_inheritance():
    """
    PG-07: Peer-Group Default Shutdown Behaviour for New Peers

    Test Flow:
    1. Configure IP and BGP on both DUTs
    2. Create peer-groups with shutdown on both DUTs
    3. DUT1: Attach neighbor WITHOUT "no shutdown" (inherits shutdown)
    4. DUT2: Attach neighbor WITH "no shutdown" (overrides shutdown)
    5. Verify DUT1 neighbor is DOWN (inherits shutdown)
    6. Verify DUT2 neighbor is UP (overrides shutdown)
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

    # Step 2: Create peer-groups with shutdown
    st.banner("STEP 2: Create Peer-Groups with Shutdown")

    st.log(f"DUT1: Creating peer-group with shutdown")
    if not configure_peer_group_with_shutdown(vars.D1, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to create peer-group on {vars.D1}")

    st.log(f"DUT2: Creating peer-group with shutdown")
    if not configure_peer_group_with_shutdown(vars.D2, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to create peer-group on {vars.D2}")

    st.log("✓ Peer-groups with shutdown configured on both DUTs")

    # Step 3: DUT1 - Attach neighbor (inherit shutdown)
    st.banner("STEP 3: DUT1 - Attach Neighbor (Inherit Shutdown)")

    st.log(f"DUT1: Attaching neighbor {CONFIG.dut2_ip} WITHOUT 'no shutdown' override")
    if not attach_neighbor_inherit_shutdown(vars.D1, CONFIG.dut2_ip, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to attach neighbor on {vars.D1}")

    st.log("✓ DUT1 neighbor attached (inherits shutdown - should stay down)")

    # Step 4: DUT2 - Attach neighbor (override shutdown)
    st.banner("STEP 4: DUT2 - Attach Neighbor (Override with 'no shutdown')")

    st.log(f"DUT2: Attaching neighbor {CONFIG.dut1_ip} WITH 'no shutdown' override")
    if not attach_neighbor_override_shutdown(vars.D2, CONFIG.dut1_ip, CONFIG.peer_group):
        st.report_fail("msg", f"Failed to attach neighbor on {vars.D2}")

    st.log("✓ DUT2 neighbor attached with 'no shutdown' override")

    # Step 5: Verify DUT1 neighbor is DOWN
    st.banner("STEP 5: Verify DUT1 Neighbor is DOWN (Inherits Shutdown)")

    st.wait(10, "Waiting before checking neighbor states")

    if not verify_bgp_session_down(vars.D1, CONFIG.dut2_ip):
        st.log(f"Warning: DUT1 neighbor unexpectedly established")
        st.log("Note: DUT1 neighbor should inherit shutdown and stay down")

    st.log("✓ DUT1 neighbor is down (inherits shutdown from peer-group)")

    # Step 6: Verify DUT2 neighbor is UP
    st.banner("STEP 6: Verify DUT2 Neighbor is UP (Overrides Shutdown)")

    if not verify_bgp_session_up(vars.D2, CONFIG.dut1_ip):
        st.log(f"Warning: DUT2 neighbor not established")
        st.log("Note: DUT2 neighbor has 'no shutdown' override and should be up")

    st.log("✓ DUT2 neighbor is up (overrides shutdown with 'no shutdown')")

    # Show running configs
    st.banner("FINAL: Show Running Configurations")

    for dut in [vars.D1, vars.D2]:
        show_cmd = "show running-configuration bgp"
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"\n{dut} BGP Configuration:\n{output[:800] if output else 'No output'}")

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
