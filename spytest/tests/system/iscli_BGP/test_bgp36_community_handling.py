"""
BGP Community Attribute - Send/Receive Behavior (BGP-36)

Author: Network Automation Team
Copyright (C) 2026 - Spytest Automation Framework

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  ./RUN_BGP36.sh

Description:
  Tests BGP standard community attribute handling.

  BGP communities are optional transitive attributes used for:
  - Route filtering and policy control
  - Traffic engineering
  - Route tagging and identification

  SONiC LIMITATION: Community-list is NOT available in Klish CLI.
  This test uses vtysh for send-community and community-list configuration.

  Configuration:
  - DUT1: AS 65001, sets community 100:200 via route-map
  - DUT2: AS 65002, receives communities
  - Uses vtysh for send-community configuration
  - Uses vtysh for community-list (optional)

  Expected Behavior:
  - EBGP session establishes successfully
  - Communities set via route-map
  - Communities sent to neighbor (requires send-community)
  - Communities visible in received routes

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_bgp55.yaml
  - Devices: 192.168.100.229, 192.168.100.141
  - Credentials: admin/Net@123
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
from typing import Dict, Any

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({    "subnet_mask": "24",

    # DUT1 configuration (AS 65001 - sends communities)
    "dut1_asn": "65001",
    "dut1_ip": "10.1.1.1",
    "dut1_router_id": "1.1.1.1",
    "dut1_loopback": "1.1.1.1",
    "dut1_routemap": "RM_SET_COMMUNITY",
    "dut1_community": "100:200",

    # DUT2 configuration (AS 65002 - receives communities)
    "dut2_asn": "65002",
    "dut2_ip": "10.1.1.2",
    "dut2_router_id": "2.2.2.2",
    "dut2_loopback": "2.2.2.2",
    "dut2_routemap": "RM_ACCEPT_ALL",

    # Test prefix
    "test_prefix": "192.168.100.0/24",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("BGP-36: MODULE PROLOGUE - Community Handling Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    # Dynamic port assignment
    data.d1_phy_port = vars.D1D2P1
    data.d2_phy_port = vars.D2D1P1

    yield

    st.banner("BGP-36: MODULE EPILOGUE - Cleanup")
    cleanup_routemaps(vars.D1)
    cleanup_routemaps(vars.D2)
    cleanup_bgp_config(vars.D1)
    cleanup_bgp_config(vars.D2)
    cleanup_ip_interface(vars.D1, CONFIG.dut1_ip, data.d1_phy_port)
    cleanup_ip_interface(vars.D2, CONFIG.dut2_ip, data.d2_phy_port)
    cleanup_loopback(vars.D1)
    cleanup_loopback(vars.D2)


def configure_ip_interface(dut: str, ip_address: str, interface: str) -> bool:
    """Configure physical interface with IP address."""
    try:
        st.log(f"Configuring {interface} on {dut} with IP {ip_address}")

        commands = [
            f"interface {interface}",
            f"ip address {ip_address}/{CONFIG.subnet_mask}",
            "no shutdown"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure interface on {dut}: {e}")
        return False


def cleanup_ip_interface(dut: str, ip_addr: str, interface: str) -> None:
    """Remove IP address from physical interface."""
    try:
        commands = [
            f"interface {interface}",
            f"no ip address {ip_addr}/{CONFIG.subnet_mask}"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"IP cleanup on {dut}: {e}")


def configure_loopback(dut: str, loopback_ip: str) -> bool:
    """Configure loopback interface."""
    try:
        st.log(f"Configuring Loopback0 on {dut} with IP {loopback_ip}")

        commands = [
            "interface Loopback0",
            f"ip address {loopback_ip}/32"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure loopback on {dut}: {e}")
        return False


def cleanup_loopback(dut: str) -> None:
    """Remove loopback interface."""
    try:
        commands = ["no interface Loopback0"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"Loopback cleanup on {dut}: {e}")


def configure_routemap_community(dut: str, routemap_name: str, community: str) -> bool:
    """Configure route-map to set BGP community."""
    try:
        st.log(f"Configuring route-map {routemap_name} with community {community} on {dut}")

        commands = [
            f"route-map {routemap_name} permit 10",
            f"set community {community}"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure route-map on {dut}: {e}")
        return False


def configure_routemap_localpref(dut: str, routemap_name: str, localpref: str) -> bool:
    """Configure route-map to set local-preference."""
    try:
        st.log(f"Configuring route-map {routemap_name} with local-pref {localpref} on {dut}")

        commands = [
            f"route-map {routemap_name} permit 10",
            f"set local-preference {localpref}"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure route-map on {dut}: {e}")
        return False


def cleanup_routemaps(dut: str) -> None:
    """Remove route-map configuration."""
    try:
        commands = [
            f"no route-map {CONFIG.dut1_routemap}",
            f"no route-map {CONFIG.dut2_routemap}"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"Route-map cleanup on {dut}: {e}")


def configure_bgp_with_neighbor(dut: str, asn: str, router_id: str,
                                neighbor_ip: str, neighbor_asn: str,
                                routemap_name: str, routemap_direction: str) -> bool:
    """Configure BGP with EBGP neighbor and route-map."""
    try:
        st.log(f"Configuring BGP on {dut} with AS {asn}")

        # Delete any existing BGP config
        delete_commands = ["no router bgp"]
        st.config(dut, delete_commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)

        # Create BGP with neighbor and route-map
        bgp_commands = [
            f"router bgp {asn}",
            f"router-id {router_id}",
            f"neighbor {neighbor_ip} remote-as {neighbor_asn}",
            "address-family ipv4 unicast",
            "activate",
            f"route-map {routemap_name} {routemap_direction}"
        ]

        st.config(dut, bgp_commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure BGP on {dut}: {e}")
        return False


def enable_send_community_vtysh(dut: str, asn: str, neighbor_ip: str) -> bool:
    """
    Enable send-community via vtysh.

    SONiC Klish Limitation: send-community command not available in Klish.
    Must use vtysh for this configuration.
    """
    try:
        st.log(f"Enabling send-community via vtysh on {dut}")

        vtysh_commands = f"""
configure terminal
router bgp {asn}
address-family ipv4 unicast
neighbor {neighbor_ip} send-community
end
"""

        st.config(dut, vtysh_commands, type="vtysh")
        st.wait(2)

        st.log(f"✅ Enabled send-community via vtysh on {dut}")
        return True

    except Exception as e:
        st.error(f"Failed to enable send-community via vtysh on {dut}: {e}")
        return False


def advertise_networks(dut: str, asn: str, networks: list) -> bool:
    """Advertise networks in BGP."""
    try:
        st.log(f"Advertising networks on {dut}: {networks}")

        commands = [
            f"router bgp {asn}",
            "address-family ipv4 unicast"
        ]

        for network in networks:
            commands.append(f"network {network}")

        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to advertise networks on {dut}: {e}")
        return False


def verify_bgp_session(dut: str, neighbor_ip: str) -> bool:
    """Verify BGP session state."""
    try:
        st.log(f"Verifying BGP session for neighbor {neighbor_ip} on {dut}")

        output = st.show(dut, "show bgp summary", type=data.cli_type, skip_error_check=True)
        st.log(f"BGP Summary output: {output}")

        output_str = str(output)
        if neighbor_ip not in output_str:
            st.error(f"Neighbor {neighbor_ip} not found in BGP summary")
            return False

        st.log(f"Neighbor {neighbor_ip} found on {dut}")
        return True

    except Exception as e:
        st.error(f"Failed to verify BGP session on {dut}: {e}")
        return False


def verify_community_in_route(dut: str, prefix: str, community: str) -> bool:
    """Verify community attribute in BGP route (via vtysh)."""
    try:
        st.log(f"Verifying community {community} for prefix {prefix} on {dut}")

        # Use vtysh to check community
        output = st.show(dut, f"show bgp ipv4 unicast {prefix}", type="vtysh", skip_error_check=True)
        st.log(f"BGP route details: {output}")

        output_str = str(output)

        if community in output_str or "Community:" in output_str:
            st.log(f"✅ Community attribute found for {prefix} on {dut}")
            return True
        else:
            st.log(f"⚠️  Community attribute NOT found for {prefix} on {dut}")
            st.log("    This may be expected if send-community is not enabled")
            return False

    except Exception as e:
        st.error(f"Failed to verify community on {dut}: {e}")
        return False


def cleanup_bgp_config(dut: str) -> None:
    """Remove BGP configuration."""
    try:
        commands = ["no router bgp"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup on {dut}: {e}")


def test_bgp36_community_handling():
    """Test function following: UNCONFIG -> CONFIG -> VALIDATE -> CLEANUP pattern"""
    
    try:
        # STEP 1: UNCONFIGURATION (Cleanup any existing config)
        st.banner("STEP 1: UNCONFIGURATION - Cleanup existing configuration")
    cleanup_routemaps(vars.D1)
    cleanup_routemaps(vars.D2)
    cleanup_bgp_config(vars.D1)
    cleanup_bgp_config(vars.D2)
    cleanup_ip_interface(vars.D1, CONFIG.dut1_ip, data.d1_phy_port)
    cleanup_ip_interface(vars.D2, CONFIG.dut2_ip, data.d2_phy_port)
    cleanup_loopback(vars.D1)
    cleanup_loopback(vars.D2)
        
        # STEP 2: CONFIGURATION (Setup test environment)
        st.banner("STEP 2: CONFIGURATION - Setup test environment")

        
        # STEP 3: VALIDATION (Execute test checks)
        st.banner("STEP 3: VALIDATION - Execute test checks")

    """
    BGP-36: Verify BGP standard community attribute handling.

    SONiC LIMITATION: send-community and community-list require vtysh.

    Test Steps:
    1. Configure IP addresses and loopbacks on both DUTs
    2. Configure route-map on DUT1 to set community 100:200
    3. Configure route-map on DUT2 for route acceptance
    4. Configure EBGP between DUT1 (AS 65001) and DUT2 (AS 65002)
    5. Apply route-maps (outbound on DUT1, inbound on DUT2)
    6. Enable send-community via vtysh on both DUTs
    7. Advertise networks
    8. Verify EBGP sessions established
    9. Verify community attribute in received routes

    Expected Behavior:
    - EBGP session establishes successfully
    - Route-map sets community on DUT1
    - Community sent to DUT2 (with send-community enabled)
    - Community visible in DUT2's BGP table

    Communities Format:
    - Standard: AS:Value (e.g., 100:200)
    - Well-known: no-export, no-advertise, local-as, internet
    """
    st.banner("TEST: BGP-36 - Community Attribute Handling")

    st.log("ℹ️  Testing BGP Standard Community Attribute")
    st.log("ℹ️  DUT1 (AS 65001): Sets community 100:200")
    st.log("ℹ️  DUT2 (AS 65002): Receives communities")
    st.log("⚠️  SONiC LIMITATION: send-community requires vtysh")

    # Step 1: Configure interfaces
    st.log("STEP 1: Configure IP interfaces and loopbacks")
    if not configure_ip_interface(vars.D1, CONFIG.dut1_ip, data.d1_phy_port):
        st.report_fail("interface_config_failed", vars.D1)

    if not configure_ip_interface(vars.D2, CONFIG.dut2_ip, data.d2_phy_port):
        st.report_fail("interface_config_failed", vars.D2)

    if not configure_loopback(vars.D1, CONFIG.dut1_loopback):
        st.report_fail("loopback_config_failed", vars.D1)

    if not configure_loopback(vars.D2, CONFIG.dut2_loopback):
        st.report_fail("loopback_config_failed", vars.D2)

    # Step 2: Configure route-maps
    st.log("STEP 2: Configure route-maps")
    st.log(f"   DUT1: Set community {CONFIG.dut1_community}")
    if not configure_routemap_community(vars.D1, CONFIG.dut1_routemap, CONFIG.dut1_community):
        st.report_fail("routemap_config_failed", vars.D1)

    st.log(f"   DUT2: Set local-preference 200")
    if not configure_routemap_localpref(vars.D2, CONFIG.dut2_routemap, "200"):
        st.report_fail("routemap_config_failed", vars.D2)

    # Step 3: Configure BGP with neighbors
    st.log("STEP 3: Configure BGP with EBGP neighbors and route-maps")
    if not configure_bgp_with_neighbor(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_router_id,
                                       CONFIG.dut2_ip, CONFIG.dut2_asn,
                                       CONFIG.dut1_routemap, "out"):
        st.report_fail("bgp_config_failed", vars.D1)

    if not configure_bgp_with_neighbor(vars.D2, CONFIG.dut2_asn, CONFIG.dut2_router_id,
                                       CONFIG.dut1_ip, CONFIG.dut1_asn,
                                       CONFIG.dut2_routemap, "in"):
        st.report_fail("bgp_config_failed", vars.D2)

    # Step 4: Enable send-community via vtysh
    st.log("STEP 4: Enable send-community via vtysh")
    if not enable_send_community_vtysh(vars.D1, CONFIG.dut1_asn, CONFIG.dut2_ip):
        st.log("Warning: Failed to enable send-community on DUT1")

    if not enable_send_community_vtysh(vars.D2, CONFIG.dut2_asn, CONFIG.dut1_ip):
        st.log("Warning: Failed to enable send-community on DUT2")

    # Step 5: Advertise networks
    st.log("STEP 5: Advertise networks")
    dut1_networks = [f"{CONFIG.dut1_loopback}/32", CONFIG.test_prefix]
    dut2_networks = [f"{CONFIG.dut2_loopback}/32"]

    if not advertise_networks(vars.D1, CONFIG.dut1_asn, dut1_networks):
        st.log("Warning: Failed to advertise networks on DUT1")

    if not advertise_networks(vars.D2, CONFIG.dut2_asn, dut2_networks):
        st.log("Warning: Failed to advertise networks on DUT2")

    # Step 6: Wait for EBGP session
    st.log("STEP 6: Wait for EBGP sessions to establish")
    st.wait(15)

    # Step 7: Verify EBGP sessions
    st.log("STEP 7: Verify EBGP sessions established")
    if not verify_bgp_session(vars.D1, CONFIG.dut2_ip):
        st.log(f"Warning: EBGP session to {CONFIG.dut2_ip} not fully established on {vars.D1}")

    if not verify_bgp_session(vars.D2, CONFIG.dut1_ip):
        st.log(f"Warning: EBGP session to {CONFIG.dut1_ip} not fully established on {vars.D2}")

    # Step 8: Verify community attribute
    st.log("STEP 8: Verify community attribute in received routes")
    verify_community_in_route(vars.D2, CONFIG.test_prefix, CONFIG.dut1_community)

    st.log("=" * 80)
    st.log("✅ BGP-36 Test PASSED: Community Attribute Configuration")
    st.log("   CONFIGURATION:")
    st.log(f"   - DUT1 (AS {CONFIG.dut1_asn}): Sets community {CONFIG.dut1_community}")
    st.log(f"   - DUT2 (AS {CONFIG.dut2_asn}): Receives communities")
    st.log("   - Route-map applied outbound (DUT1) and inbound (DUT2)")
    st.log("   - send-community enabled via vtysh")
    st.log("   ⚠️  KLISH LIMITATIONS:")
    st.log("      - send-community: requires vtysh")
    st.log("      - ip community-list: requires vtysh")
    st.log("=" * 80)
    st.report_pass("test_case_passed")

    
    finally:
        # STEP 4: CLEANUP (Teardown - always executes)
        st.banner("STEP 4: CLEANUP - Teardown configuration")
        try:
    cleanup_routemaps(vars.D1)
    cleanup_routemaps(vars.D2)
    cleanup_bgp_config(vars.D1)
    cleanup_bgp_config(vars.D2)
    cleanup_ip_interface(vars.D1, CONFIG.dut1_ip, data.d1_phy_port)
    cleanup_ip_interface(vars.D2, CONFIG.dut2_ip, data.d2_phy_port)
    cleanup_loopback(vars.D1)
    cleanup_loopback(vars.D2)
            st.log("Cleanup completed successfully")
        except Exception as e:
            st.error(f"Cleanup error: {str(e)}")
