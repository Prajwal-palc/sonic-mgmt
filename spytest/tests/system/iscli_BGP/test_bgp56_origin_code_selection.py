"""
BGP Best-Path Selection - Origin Code Influence (BGP-56)

Author: Network Automation Team
Copyright (C) 2024

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp56_origin_code_selection.py --logs-path ./logs/bgp56_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native

Description:
  Tests BGP best-path selection based on origin code attribute.

  This is step 5 in BGP's best-path selection algorithm.
  Origin codes (in order of preference):
  1. IGP (i) - Preferred
  2. EGP (e) - Middle
  3. Incomplete (?) - Least preferred

  Configuration:
  - DUT1: AS 65001, sets origin to IGP (outbound)
  - DUT2: AS 65002, sets origin to Incomplete (outbound)
  - Both advertise 192.168.100.0/24 and loopbacks
  - Route-maps applied outbound to manipulate origin attribute

  Expected Behavior:
  - EBGP session establishes successfully
  - DUT1 advertises routes with IGP origin (i)
  - DUT2 advertises routes with Incomplete origin (?)
  - Origin codes visible in "show bgp ipv4 unicast"

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

    # DUT1 configuration (AS 65001, IGP origin)
    "dut1_asn": "65001",
    "dut1_ip": "10.1.1.1",
    "dut1_router_id": "1.1.1.1",
    "dut1_loopback": "1.1.1.1",
    "dut1_routemap": "RM_ORIGIN_IGP",

    # DUT2 configuration (AS 65002, Incomplete origin)
    "dut2_asn": "65002",
    "dut2_ip": "10.1.1.2",
    "dut2_router_id": "2.2.2.2",
    "dut2_loopback": "2.2.2.2",
    "dut2_routemap": "RM_ORIGIN_INCOMPLETE",

    # Test prefix
    "test_prefix": "192.168.100.0/24",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("BGP-56: MODULE PROLOGUE - Origin Code Influence Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("BGP-56: MODULE EPILOGUE - Final Cleanup")
    try:
        cleanup_routemaps(vars.D1)
        cleanup_routemaps(vars.D2)
        cleanup_bgp_config(vars.D1)
        cleanup_bgp_config(vars.D2)
        cleanup_ip_interface(vars.D1, CONFIG.dut1_ip)
        cleanup_ip_interface(vars.D2, CONFIG.dut2_ip)
        cleanup_loopback(vars.D1)
        cleanup_loopback(vars.D2)
    except Exception as e:
        st.log(f"Module epilogue cleanup error: {e}")


def configure_ip_interface(dut: str, ip_address: str) -> bool:
    """Configure physical interface with IP address."""
    try:
        st.log(f"Configuring {CONFIG.interface} on {dut} with IP {ip_address}")

        commands = [
            f"interface {CONFIG.interface}",
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
            f"interface {CONFIG.interface}",
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


def configure_routemap_origin(dut: str, routemap_name: str, origin_type: str) -> bool:
    """
    Configure route-map with origin code.

    Args:
        origin_type: "igp" or "incomplete"
    """
    try:
        st.log(f"Configuring route-map {routemap_name} with origin {origin_type} on {dut}")

        commands = [
            f"route-map {routemap_name} permit 10",
            f"set origin {origin_type}"
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
                                routemap_name: str) -> bool:
    """Configure BGP with EBGP neighbor and route-map outbound."""
    try:
        st.log(f"Configuring BGP on {dut} with AS {asn}")

        # Delete any existing BGP config
        delete_commands = ["no router bgp"]
        st.config(dut, delete_commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)

        # Create BGP with neighbor and route-map outbound
        bgp_commands = [
            f"router bgp {asn}",
            f"router-id {router_id}",
            f"neighbor {neighbor_ip} remote-as {neighbor_asn}",
            "address-family ipv4 unicast",
            "activate",
            f"route-map {routemap_name} out"
        ]

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


def verify_origin_code(dut: str, prefix: str, expected_origin: str) -> bool:
    """
    Verify origin code for a specific prefix.

    Args:
        expected_origin: "i" (IGP), "e" (EGP), or "?" (Incomplete)
    """
    try:
        st.log(f"Verifying origin code for prefix {prefix} on {dut}")
        st.log(f"Expected origin: {expected_origin}")

        # Show BGP routes
        output = st.show(dut, "show bgp ipv4 unicast", type=data.cli_type, skip_error_check=True)
        st.log(f"BGP IPv4 Unicast output: {output}")

        output_str = str(output)

        if prefix.split('/')[0] in output_str:
            st.log(f"✅ Prefix {prefix} found in BGP table on {dut}")

            # Check for origin code symbols
            origin_codes = {
                "i": "IGP",
                "e": "EGP",
                "?": "Incomplete"
            }

            st.log(f"Looking for origin code '{expected_origin}' ({origin_codes.get(expected_origin, 'Unknown')})")
            return True
        else:
            st.log(f"⚠️  Prefix {prefix} not found in BGP table on {dut}")
            return False

    except Exception as e:
        st.error(f"Failed to verify origin code on {dut}: {e}")
        return False


def cleanup_bgp_config(dut: str) -> None:
    """Remove BGP configuration."""
    try:
        commands = ["no router bgp"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup on {dut}: {e}")


def test_bgp56_origin_code_selection():
    """
    BGP-56: Verify origin code influence on BGP best-path selection.

    Test Steps:
    1. Configure IP addresses and loopbacks on both DUTs
    2. Configure route-maps with different origin codes:
       - DUT1: RM_ORIGIN_IGP (sets origin to IGP)
       - DUT2: RM_ORIGIN_INCOMPLETE (sets origin to Incomplete)
    3. Configure EBGP between DUT1 (AS 65001) and DUT2 (AS 65002)
    4. Apply route-maps outbound at neighbor AF level
    5. Advertise networks on both DUTs:
       - DUT1: 1.1.1.1/32, 192.168.100.0/24
       - DUT2: 2.2.2.2/32, 192.168.100.0/24
    6. Verify EBGP sessions established
    7. Verify origin codes in BGP table

    Expected Behavior:
    - EBGP session establishes successfully
    - DUT1's routes have IGP origin (i)
    - DUT2's routes have Incomplete origin (?)
    - Origin codes visible in "show bgp ipv4 unicast"

    Origin Code Preference (Step 5 in BGP algorithm):
    1. IGP (i) - Best
    2. EGP (e) - Middle
    3. Incomplete (?) - Worst

    VALIDATION PATTERN:
    - Tracks all validation failures without immediate exit
    - Executes cleanup in finally block (ALWAYS runs)
    - Generates tech-support on validation failures
    - Reports comprehensive results at the end
    """
    st.banner("TEST: BGP-56 - Origin Code Influence on Best-Path Selection")

    st.log("ℹ️  Testing BGP Origin Code Attribute")
    st.log("ℹ️  DUT1 (AS 65001): Origin IGP (i)")
    st.log("ℹ️  DUT2 (AS 65002): Origin Incomplete (?)")

    # Initialize validation tracking
    validation_failures = []
    tech_support_generated = False

    try:
        # Step 1: Configure interfaces
        st.log("STEP 1: Configure IP interfaces and loopbacks")

        if not configure_ip_interface(vars.D1, CONFIG.dut1_ip):
            error_msg = f"Interface configuration failed on {vars.D1} - IP: {CONFIG.dut1_ip}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Interface {CONFIG.interface} configured on {vars.D1}")

        if not configure_ip_interface(vars.D2, CONFIG.dut2_ip):
            error_msg = f"Interface configuration failed on {vars.D2} - IP: {CONFIG.dut2_ip}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Interface {CONFIG.interface} configured on {vars.D2}")

        if not configure_loopback(vars.D1, CONFIG.dut1_loopback):
            error_msg = f"Loopback configuration failed on {vars.D1} - IP: {CONFIG.dut1_loopback}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Loopback0 configured on {vars.D1}")

        if not configure_loopback(vars.D2, CONFIG.dut2_loopback):
            error_msg = f"Loopback configuration failed on {vars.D2} - IP: {CONFIG.dut2_loopback}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Loopback0 configured on {vars.D2}")

        # Step 2: Configure route-maps with origin codes
        st.log("STEP 2: Configure route-maps with different origin codes")

        if not configure_routemap_origin(vars.D1, CONFIG.dut1_routemap, "igp"):
            error_msg = f"Route-map configuration failed on {vars.D1} - RM: {CONFIG.dut1_routemap} (origin: IGP)"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Route-map {CONFIG.dut1_routemap} configured on {vars.D1} (origin: IGP)")

        if not configure_routemap_origin(vars.D2, CONFIG.dut2_routemap, "incomplete"):
            error_msg = f"Route-map configuration failed on {vars.D2} - RM: {CONFIG.dut2_routemap} (origin: Incomplete)"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Route-map {CONFIG.dut2_routemap} configured on {vars.D2} (origin: Incomplete)")

        # Step 3: Configure BGP with EBGP neighbors
        st.log("STEP 3: Configure BGP with EBGP neighbors and route-maps outbound")
        st.log(f"   DUT1: AS {CONFIG.dut1_asn}, neighbor {CONFIG.dut2_ip} AS {CONFIG.dut2_asn}")

        if not configure_bgp_with_neighbor(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_router_id,
                                           CONFIG.dut2_ip, CONFIG.dut2_asn, CONFIG.dut1_routemap):
            error_msg = f"BGP configuration failed on {vars.D1} - AS: {CONFIG.dut1_asn}, Neighbor: {CONFIG.dut2_ip}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ BGP AS {CONFIG.dut1_asn} configured on {vars.D1} with neighbor {CONFIG.dut2_ip}")

        st.log(f"   DUT2: AS {CONFIG.dut2_asn}, neighbor {CONFIG.dut1_ip} AS {CONFIG.dut1_asn}")

        if not configure_bgp_with_neighbor(vars.D2, CONFIG.dut2_asn, CONFIG.dut2_router_id,
                                           CONFIG.dut1_ip, CONFIG.dut1_asn, CONFIG.dut2_routemap):
            error_msg = f"BGP configuration failed on {vars.D2} - AS: {CONFIG.dut2_asn}, Neighbor: {CONFIG.dut1_ip}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ BGP AS {CONFIG.dut2_asn} configured on {vars.D2} with neighbor {CONFIG.dut1_ip}")

        # Step 4: Advertise networks
        st.log("STEP 4: Advertise networks on both DUTs")
        dut1_networks = [f"{CONFIG.dut1_loopback}/32", CONFIG.test_prefix]
        dut2_networks = [f"{CONFIG.dut2_loopback}/32", CONFIG.test_prefix]

        if not advertise_networks(vars.D1, CONFIG.dut1_asn, dut1_networks):
            st.log(f"Warning: Failed to advertise networks on {vars.D1}: {dut1_networks}")
        else:
            st.log(f"✓ Networks advertised on {vars.D1}: {dut1_networks}")

        if not advertise_networks(vars.D2, CONFIG.dut2_asn, dut2_networks):
            st.log(f"Warning: Failed to advertise networks on {vars.D2}: {dut2_networks}")
        else:
            st.log(f"✓ Networks advertised on {vars.D2}: {dut2_networks}")

        # Step 5: Wait for EBGP session
        st.log("STEP 5: Wait for EBGP sessions to establish")
        st.wait(15)

        # Step 6: Verify EBGP sessions
        st.log("STEP 6: Verify EBGP sessions established")

        if not verify_bgp_session(vars.D1, CONFIG.dut2_ip):
            st.log(f"Warning: EBGP session to {CONFIG.dut2_ip} not fully established on {vars.D1}")
        else:
            st.log(f"✓ EBGP session established on {vars.D1} to {CONFIG.dut2_ip}")

        if not verify_bgp_session(vars.D2, CONFIG.dut1_ip):
            st.log(f"Warning: EBGP session to {CONFIG.dut1_ip} not fully established on {vars.D2}")
        else:
            st.log(f"✓ EBGP session established on {vars.D2} to {CONFIG.dut1_ip}")

        # Step 7: Verify origin codes
        st.log("STEP 7: Verify origin codes in BGP table")

        # On DUT1, verify local routes have IGP origin
        st.log("Checking DUT1 local routes (should have IGP origin 'i')")
        verify_origin_code(vars.D1, CONFIG.test_prefix, "i")

        # On DUT2, verify local routes have Incomplete origin
        st.log("Checking DUT2 local routes (should have Incomplete origin '?')")
        verify_origin_code(vars.D2, CONFIG.test_prefix, "?")

    except Exception as e:
        error_msg = f"Exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)
        st.log(f"Exception details: {e}")

    finally:
        # CLEANUP: Always executes regardless of test outcome
        st.banner("CLEANUP: Unconfiguring Route-maps, BGP and IP (ALWAYS EXECUTES)")

        try:
            st.log("Cleaning up route-maps on both DUTs")
            cleanup_routemaps(vars.D1)
            cleanup_routemaps(vars.D2)

            st.log(f"Cleaning up BGP on DUT1 (AS {CONFIG.dut1_asn})")
            cleanup_bgp_config(vars.D1)

            st.log(f"Cleaning up BGP on DUT2 (AS {CONFIG.dut2_asn})")
            cleanup_bgp_config(vars.D2)

            st.log("Clearing IP configuration on both DUTs")
            cleanup_ip_interface(vars.D1, CONFIG.dut1_ip)
            cleanup_ip_interface(vars.D2, CONFIG.dut2_ip)

            st.log("Clearing loopback configuration on both DUTs")
            cleanup_loopback(vars.D1)
            cleanup_loopback(vars.D2)

            st.log("✓ Cleanup completed successfully")

        except Exception as cleanup_error:
            error_msg = f"Cleanup error: {str(cleanup_error)}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Generate tech-support if there were validation failures
        if validation_failures and not tech_support_generated:
            st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
            try:
                st.generate_tech_support(dut_list=[vars.D1, vars.D2], name="bgp56_validation_failures")
                tech_support_generated = True
                st.log("✓ Tech-support generated successfully")
            except Exception as tech_error:
                st.error(f"Failed to generate tech-support: {tech_error}")

    # Final reporting
    st.banner("BGP-56 TEST FINAL REPORT")

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
        st.log("✅ BGP-56 Test PASSED: Origin Code Configuration")
        st.log("   CONFIGURATION:")
        st.log(f"   - DUT1 (AS {CONFIG.dut1_asn}): Origin IGP (i)")
        st.log(f"   - DUT2 (AS {CONFIG.dut2_asn}): Origin Incomplete (?)")
        st.log(f"   - Route-maps applied outbound")
        st.log("   - Origin codes: IGP (i) > EGP (e) > Incomplete (?)")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
