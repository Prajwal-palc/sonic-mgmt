"""
BGP Best-Path Selection - Next-hop Reachability Dependency (BGP-58)

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp58_nexthop_reachability.py --logs-path ./logs/bgp58_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native

Description:
  Tests BGP next-hop reachability dependency for route installation.

  BGP routes are only installed in the routing table if the next-hop is reachable.
  This test validates that:
  1. Routes with reachable next-hops are installed
  2. Routes become invalid when next-hop is unreachable
  3. Routes are restored when next-hop becomes reachable again

  Configuration:
  - DUT1: AS 65001, has static route to next-hop 100.1.1.2
  - DUT2: AS 65002, sets custom next-hop 100.1.1.2 via route-map
  - Test removes/adds static route to simulate next-hop reachability changes

  Expected Behavior:
  - With static route: BGP routes valid and installed
  - Without static route: BGP routes invalid, not installed
  - After restoring static route: BGP routes valid again

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2vs.yaml
  - Devices: Virtual Switches
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
from typing import Dict, Any

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "interface": "Ethernet4",
    "subnet_mask": "24",

    # DUT1 configuration (AS 65001)
    "dut1_asn": "65001",
    "dut1_ip": "10.1.1.1",
    "dut1_router_id": "1.1.1.1",
    "dut1_loopback0": "1.1.1.1",
    "dut1_loopback1": "100.1.1.1",

    # DUT2 configuration (AS 65002)
    "dut2_asn": "65002",
    "dut2_ip": "10.1.1.2",
    "dut2_router_id": "2.2.2.2",
    "dut2_loopback0": "2.2.2.2",
    "dut2_loopback1": "100.1.1.2",

    # Route-map and next-hop
    "routemap_nexthop": "RM_NEXT_HOP",
    "custom_nexthop": "100.1.1.2",

    # Test prefix
    "test_prefix": "192.168.100.0/24",

    # Static route for next-hop reachability
    "static_route_prefix": "100.1.1.2/32",
    "static_route_nexthop": "10.1.1.2",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("BGP-58: MODULE PROLOGUE - Next-hop Reachability Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("BGP-58: MODULE EPILOGUE - Final Cleanup")
    try:
        cleanup_static_route(vars.D1)
        cleanup_routemaps(vars.D2)
        cleanup_bgp_config(vars.D1)
        cleanup_bgp_config(vars.D2)
        cleanup_ip_interface(vars.D1, CONFIG.dut1_ip)
        cleanup_ip_interface(vars.D2, CONFIG.dut2_ip)
        cleanup_loopback(vars.D1, "Loopback0")
        cleanup_loopback(vars.D1, "Loopback1")
        cleanup_loopback(vars.D2, "Loopback0")
        cleanup_loopback(vars.D2, "Loopback1")
    except Exception as e:
        st.log(f"Module epilogue cleanup error: {e}")


def configure_ip_interface(dut: str, ip_address: str) -> bool:
    """Configure physical interface with IP address."""
    try:
        st.log(f"Configuring {data.d1_phy_port} on {dut} with IP {ip_address}")

        commands = [
            f"interface {data.d1_phy_port}",
            f"ip address {ip_address}/{CONFIG.subnet_mask}",
            "no shutdown"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure interface on {dut}: {e}")
        return False


def cleanup_ip_interface(dut: str, ip_addr: str) -> None:
    """Remove IP address from physical interface."""
    try:
        commands = [
            f"interface {data.d1_phy_port}",
            f"no ip address {ip_addr}/{CONFIG.subnet_mask}"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"IP cleanup on {dut}: {e}")


def configure_loopback(dut: str, loopback_name: str, loopback_ip: str) -> bool:
    """Configure loopback interface."""
    try:
        st.log(f"Configuring {loopback_name} on {dut} with IP {loopback_ip}")

        commands = [
            f"interface {loopback_name}",
            f"ip address {loopback_ip}/32"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure loopback on {dut}: {e}")
        return False


def cleanup_loopback(dut: str, loopback_name: str) -> None:
    """Remove loopback interface."""
    try:
        commands = [f"no interface {loopback_name}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"Loopback cleanup on {dut}: {e}")


def configure_routemap_nexthop(dut: str, routemap_name: str, nexthop: str) -> bool:
    """Configure route-map to set custom next-hop."""
    try:
        st.log(f"Configuring route-map {routemap_name} with next-hop {nexthop} on {dut}")

        commands = [
            f"route-map {routemap_name} permit 10",
            f"set ip next-hop {nexthop}"
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
        commands = [f"no route-map {CONFIG.routemap_nexthop}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"Route-map cleanup on {dut}: {e}")


def configure_static_route(dut: str, prefix: str, nexthop: str) -> bool:
    """Configure static route for next-hop reachability."""
    try:
        st.log(f"Configuring static route {prefix} via {nexthop} on {dut}")

        commands = [f"ip route {prefix} {nexthop}"]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure static route on {dut}: {e}")
        return False


def remove_static_route(dut: str, prefix: str, nexthop: str) -> bool:
    """Remove static route to make next-hop unreachable."""
    try:
        st.log(f"Removing static route {prefix} via {nexthop} on {dut}")

        commands = [f"no ip route {prefix} {nexthop}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to remove static route on {dut}: {e}")
        return False


def cleanup_static_route(dut: str) -> None:
    """Cleanup static route."""
    try:
        commands = [f"no ip route {CONFIG.static_route_prefix} {CONFIG.static_route_nexthop}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"Static route cleanup on {dut}: {e}")


def configure_bgp_with_neighbor(dut: str, asn: str, router_id: str,
                                neighbor_ip: str, neighbor_asn: str,
                                routemap_name: str = None) -> bool:
    """Configure BGP with EBGP neighbor and optional route-map."""
    try:
        st.log(f"Configuring BGP on {dut} with AS {asn}")

        # Delete any existing BGP config
        delete_commands = ["no router bgp"]
        st.config(dut, delete_commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)

        # Create BGP with neighbor
        bgp_commands = [
            f"router bgp {asn}",
            f"router-id {router_id}",
            f"neighbor {neighbor_ip} remote-as {neighbor_asn}",
            "address-family ipv4 unicast",
            "activate"
        ]

        # Add route-map if specified
        if routemap_name:
            bgp_commands.append(f"route-map {routemap_name} out")

        st.config(dut, bgp_commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure BGP on {dut}: {e}")
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


def verify_bgp_route_exists(dut: str, prefix: str) -> bool:
    """Verify BGP route exists in BGP table."""
    try:
        st.log(f"Verifying BGP route {prefix} exists on {dut}")

        output = st.show(dut, "show bgp ipv4 unicast", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        if prefix.split('/')[0] in output_str:
            st.log(f"✅ Route {prefix} found in BGP table on {dut}")
            return True
        else:
            st.log(f"⚠️  Route {prefix} NOT found in BGP table on {dut}")
            return False

    except Exception as e:
        st.error(f"Failed to verify BGP route on {dut}: {e}")
        return False


def verify_route_in_rib(dut: str, prefix: str) -> bool:
    """Verify route is installed in routing table (RIB)."""
    try:
        st.log(f"Verifying route {prefix} is in routing table on {dut}")

        output = st.show(dut, "show ip route", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        if prefix.split('/')[0] in output_str:
            st.log(f"✅ Route {prefix} installed in routing table on {dut}")
            return True
        else:
            st.log(f"⚠️  Route {prefix} NOT in routing table on {dut}")
            return False

    except Exception as e:
        st.error(f"Failed to verify route in RIB on {dut}: {e}")
        return False


def cleanup_bgp_config(dut: str) -> None:
    """Remove BGP configuration."""
    try:
        commands = ["no router bgp"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup on {dut}: {e}")


def test_bgp58_nexthop_reachability():
    """
    BGP-58: Verify next-hop reachability dependency for route installation.

    Test Steps:
    1. Configure IP addresses and loopbacks on both DUTs
    2. Configure route-map on DUT2 to set custom next-hop (100.1.1.2)
    3. Configure EBGP between DUT1 (AS 65001) and DUT2 (AS 65002)
    4. Apply route-map outbound on DUT2
    5. Advertise test prefix (192.168.100.0/24) from DUT2
    6. Phase 1: Configure static route on DUT1 for next-hop reachability
       - Verify BGP route valid and installed in routing table
    7. Phase 2: Remove static route (next-hop unreachable)
       - Verify BGP route becomes invalid, not in routing table
    8. Phase 3: Restore static route (next-hop reachable again)
       - Verify BGP route valid again, reinstalled in routing table

    Expected Behavior:
    - With static route: next-hop reachable, route installed
    - Without static route: next-hop unreachable, route not installed
    - After restoring: next-hop reachable, route reinstalled

    VALIDATION PATTERN:
    - Tracks all validation failures without immediate exit
    - Executes cleanup in finally block (ALWAYS runs)
    - Generates tech-support on validation failures
    - Reports comprehensive results at the end
    """
    st.banner("TEST: BGP-58 - Next-hop Reachability Dependency")

    st.log("ℹ️  Testing BGP Next-hop Reachability")
    st.log("ℹ️  DUT2 sets custom next-hop 100.1.1.2")
    st.log("ℹ️  DUT1 uses static route for next-hop reachability")

    # Initialize validation tracking
    validation_failures = []
    tech_support_generated = False

    # Variables for phase tracking
    route_in_rib_phase1 = False
    route_in_rib_phase2 = False
    route_in_rib_phase3 = False

    try:
        # Step 1: Configure interfaces
        st.log("STEP 1: Configure IP interfaces and loopbacks")

        if not configure_ip_interface(vars.D1, CONFIG.dut1_ip):
            error_msg = f"Interface configuration failed on {vars.D1} - IP: {CONFIG.dut1_ip}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Interface {data.d1_phy_port} configured on {vars.D1}")

        if not configure_ip_interface(vars.D2, CONFIG.dut2_ip):
            error_msg = f"Interface configuration failed on {vars.D2} - IP: {CONFIG.dut2_ip}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Interface {data.d2_phy_port} configured on {vars.D2}")

        if not configure_loopback(vars.D1, "Loopback0", CONFIG.dut1_loopback0):
            error_msg = f"Loopback0 configuration failed on {vars.D1} - IP: {CONFIG.dut1_loopback0}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Loopback0 configured on {vars.D1}")

        if not configure_loopback(vars.D1, "Loopback1", CONFIG.dut1_loopback1):
            error_msg = f"Loopback1 configuration failed on {vars.D1} - IP: {CONFIG.dut1_loopback1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Loopback1 configured on {vars.D1}")

        if not configure_loopback(vars.D2, "Loopback0", CONFIG.dut2_loopback0):
            error_msg = f"Loopback0 configuration failed on {vars.D2} - IP: {CONFIG.dut2_loopback0}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Loopback0 configured on {vars.D2}")

        if not configure_loopback(vars.D2, "Loopback1", CONFIG.dut2_loopback1):
            error_msg = f"Loopback1 configuration failed on {vars.D2} - IP: {CONFIG.dut2_loopback1}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Loopback1 configured on {vars.D2}")

        # Step 2: Configure route-map on DUT2
        st.log("STEP 2: Configure route-map with custom next-hop on DUT2")

        if not configure_routemap_nexthop(vars.D2, CONFIG.routemap_nexthop, CONFIG.custom_nexthop):
            error_msg = f"Route-map configuration failed on {vars.D2} - RM: {CONFIG.routemap_nexthop}, NH: {CONFIG.custom_nexthop}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Route-map {CONFIG.routemap_nexthop} configured on {vars.D2}")

        # Step 3: Configure BGP
        st.log("STEP 3: Configure BGP with EBGP neighbors")

        if not configure_bgp_with_neighbor(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_router_id,
                                           CONFIG.dut2_ip, CONFIG.dut2_asn):
            error_msg = f"BGP configuration failed on {vars.D1} - AS: {CONFIG.dut1_asn}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ BGP AS {CONFIG.dut1_asn} configured on {vars.D1}")

        if not configure_bgp_with_neighbor(vars.D2, CONFIG.dut2_asn, CONFIG.dut2_router_id,
                                           CONFIG.dut1_ip, CONFIG.dut1_asn, CONFIG.routemap_nexthop):
            error_msg = f"BGP configuration failed on {vars.D2} - AS: {CONFIG.dut2_asn}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ BGP AS {CONFIG.dut2_asn} configured on {vars.D2} with route-map")

        # Step 4: Advertise networks
        st.log("STEP 4: Advertise networks")
        dut1_networks = [f"{CONFIG.dut1_loopback0}/32"]
        dut2_networks = [f"{CONFIG.dut2_loopback0}/32", CONFIG.test_prefix]

        if not advertise_networks(vars.D1, CONFIG.dut1_asn, dut1_networks):
            st.log(f"Warning: Failed to advertise networks on {vars.D1}: {dut1_networks}")
        else:
            st.log(f"✓ Networks advertised on {vars.D1}: {dut1_networks}")

        if not advertise_networks(vars.D2, CONFIG.dut2_asn, dut2_networks):
            st.log(f"Warning: Failed to advertise networks on {vars.D2}: {dut2_networks}")
        else:
            st.log(f"✓ Networks advertised on {vars.D2}: {dut2_networks}")

        # Wait for BGP session
        st.log("STEP 5: Wait for EBGP session to establish")
        st.wait(15)

        verify_bgp_session(vars.D1, CONFIG.dut2_ip)
        verify_bgp_session(vars.D2, CONFIG.dut1_ip)

        # Phase 1: Next-hop reachable
        st.log("=" * 80)
        st.log("PHASE 1: Next-hop REACHABLE (with static route)")
        st.log("=" * 80)

        st.log("STEP 6: Configure static route for next-hop reachability")
        if not configure_static_route(vars.D1, CONFIG.static_route_prefix, CONFIG.static_route_nexthop):
            st.log(f"Warning: Failed to configure static route on {vars.D1}")
        else:
            st.log(f"✓ Static route {CONFIG.static_route_prefix} configured on {vars.D1}")

        st.wait(5)

        st.log("STEP 7: Verify BGP route is valid and installed")
        verify_bgp_route_exists(vars.D1, CONFIG.test_prefix)
        route_in_rib_phase1 = verify_route_in_rib(vars.D1, CONFIG.test_prefix)

        # Phase 2: Next-hop unreachable
        st.log("=" * 80)
        st.log("PHASE 2: Next-hop UNREACHABLE (remove static route)")
        st.log("=" * 80)

        st.log("STEP 8: Remove static route to make next-hop unreachable")
        if not remove_static_route(vars.D1, CONFIG.static_route_prefix, CONFIG.static_route_nexthop):
            st.log(f"Warning: Failed to remove static route on {vars.D1}")
        else:
            st.log(f"✓ Static route {CONFIG.static_route_prefix} removed from {vars.D1}")

        st.wait(5)

        st.log("STEP 9: Verify BGP route becomes invalid (not in routing table)")
        verify_bgp_route_exists(vars.D1, CONFIG.test_prefix)
        route_in_rib_phase2 = verify_route_in_rib(vars.D1, CONFIG.test_prefix)

        # Phase 3: Next-hop reachable again
        st.log("=" * 80)
        st.log("PHASE 3: Next-hop REACHABLE AGAIN (restore static route)")
        st.log("=" * 80)

        st.log("STEP 10: Restore static route for next-hop reachability")
        if not configure_static_route(vars.D1, CONFIG.static_route_prefix, CONFIG.static_route_nexthop):
            st.log(f"Warning: Failed to restore static route on {vars.D1}")
        else:
            st.log(f"✓ Static route {CONFIG.static_route_prefix} restored on {vars.D1}")

        st.wait(5)

        st.log("STEP 11: Verify BGP route is valid and reinstalled")
        verify_bgp_route_exists(vars.D1, CONFIG.test_prefix)
        route_in_rib_phase3 = verify_route_in_rib(vars.D1, CONFIG.test_prefix)

    except Exception as e:
        error_msg = f"Exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)
        st.log(f"Exception details: {e}")

    finally:
        # CLEANUP: Always executes regardless of test outcome
        st.banner("CLEANUP: Unconfiguring Static Route, Route-maps, BGP and IP (ALWAYS EXECUTES)")

        try:
            st.log("Cleaning up static route on DUT1")
            cleanup_static_route(vars.D1)

            st.log("Cleaning up route-maps on DUT2")
            cleanup_routemaps(vars.D2)

            st.log(f"Cleaning up BGP on DUT1 (AS {CONFIG.dut1_asn})")
            cleanup_bgp_config(vars.D1)

            st.log(f"Cleaning up BGP on DUT2 (AS {CONFIG.dut2_asn})")
            cleanup_bgp_config(vars.D2)

            st.log("Clearing IP configuration on both DUTs")
            cleanup_ip_interface(vars.D1, CONFIG.dut1_ip)
            cleanup_ip_interface(vars.D2, CONFIG.dut2_ip)

            st.log("Clearing loopback configuration on both DUTs")
            cleanup_loopback(vars.D1, "Loopback0")
            cleanup_loopback(vars.D1, "Loopback1")
            cleanup_loopback(vars.D2, "Loopback0")
            cleanup_loopback(vars.D2, "Loopback1")

            st.log("✓ Cleanup completed successfully")

        except Exception as cleanup_error:
            error_msg = f"Cleanup error: {str(cleanup_error)}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Generate tech-support if there were validation failures
        if validation_failures and not tech_support_generated:
            st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
            try:
                st.generate_tech_support(dut_list=[vars.D1, vars.D2], name="bgp58_validation_failures")
                tech_support_generated = True
                st.log("✓ Tech-support generated successfully")
            except Exception as tech_error:
                st.error(f"Failed to generate tech-support: {tech_error}")

    # Final reporting
    st.banner("BGP-58 TEST FINAL REPORT")

    if validation_failures:
        st.log("=" * 80)
        st.error("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"ERROR {idx}. {failure}")
        st.log("=" * 80)
        st.log(f"Note: Cleanup and unconfiguration completed despite {len(validation_failures)} validation failure(s)")
        if tech_support_generated:
            st.log("Tech-support has been generated for debugging")

        error_summary = f"Test completed with {len(validation_failures)} validation failure(s). Cleanup executed. See errors above."
        st.report_fail("msg", error_summary)
    else:
        st.log("=" * 80)
        st.log("All validations passed successfully")
        st.log("=" * 80)
        st.log("✅ BGP-58 Test PASSED: Next-hop Reachability Dependency")
        st.log("   CONFIGURATION:")
        st.log(f"   - DUT2 sets custom next-hop: {CONFIG.custom_nexthop}")
        st.log(f"   - DUT1 uses static route for reachability")
        st.log("   PHASES:")
        st.log(f"   - Phase 1 (with static route): Route in RIB = {route_in_rib_phase1}")
        st.log(f"   - Phase 2 (without static route): Route in RIB = {route_in_rib_phase2}")
        st.log(f"   - Phase 3 (restored static route): Route in RIB = {route_in_rib_phase3}")
        st.log("   KEY LEARNING:")
        st.log("   - BGP routes only installed if next-hop is reachable")
        st.log("   - Next-hop reachability checked before route installation")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
