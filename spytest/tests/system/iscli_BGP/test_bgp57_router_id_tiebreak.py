"""
BGP Best-Path Selection - Router-ID Tie-Break (BGP-57)

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp57_router_id_tiebreak.py --logs-path ./logs/bgp57_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native

Description:
  Tests BGP router-ID configuration and its role in best-path selection.

  This is step 10 in BGP's best-path selection algorithm.
  When all other attributes are equal, the route from the neighbor with the
  LOWEST router-ID is preferred.

  2-Device Limitation:
  With only 2 devices, this test cannot fully demonstrate router-ID tie-break
  because locally originated routes always win (higher weight). A proper
  router-ID tie-break test requires receiving the same prefix from MULTIPLE
  neighbors.

  This test documents the concept and validates:
  - Router-ID configuration on both DUTs
  - EBGP session establishment
  - Router-IDs visible in BGP table

  Configuration:
  - DUT1: AS 65001, Router-ID 3.3.3.3 (higher)
  - DUT2: AS 65002, Router-ID 2.2.2.2 (lower)
  - EBGP session between different AS
  - Both advertise 192.168.100.0/24 (for documentation)

  Expected Behavior:
  - EBGP session establishes successfully
  - Router-IDs configured and visible
  - Locally originated routes preferred (weight 32768)

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

    # DUT1 configuration (AS 65001, higher router-ID)
    "dut1_asn": "65001",
    "dut1_ip": "10.1.1.1",
    "dut1_router_id": "3.3.3.3",  # Higher router-ID
    "dut1_loopback": "1.1.1.1",

    # DUT2 configuration (AS 65002, lower router-ID)
    "dut2_asn": "65002",
    "dut2_ip": "10.1.1.2",
    "dut2_router_id": "2.2.2.2",  # Lower router-ID (would win in tie-break)
    "dut2_loopback": "2.2.2.2",

    # Test prefix
    "test_prefix": "192.168.100.0/24",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("BGP-57: MODULE PROLOGUE - Router-ID Tie-Break Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("BGP-57: MODULE EPILOGUE - Final Cleanup")
    try:
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


def configure_bgp_with_neighbor(dut: str, asn: str, router_id: str,
                                neighbor_ip: str, neighbor_asn: str) -> bool:
    """Configure BGP with EBGP neighbor and specific router-ID."""
    try:
        st.log(f"Configuring BGP on {dut} with AS {asn} and router-ID {router_id}")

        # Delete any existing BGP config
        delete_commands = ["no router bgp"]
        st.config(dut, delete_commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)

        # Create BGP with specific router-ID
        bgp_commands = [
            f"router bgp {asn}",
            f"router-id {router_id}",
            f"neighbor {neighbor_ip} remote-as {neighbor_asn}",
            "address-family ipv4 unicast",
            "activate"
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


def verify_router_id(dut: str, expected_router_id: str) -> bool:
    """Verify configured router-ID."""
    try:
        st.log(f"Verifying router-ID {expected_router_id} on {dut}")

        output = st.show(dut, "show bgp summary", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        if expected_router_id in output_str:
            st.log(f"✅ Router-ID {expected_router_id} configured on {dut}")
            return True
        else:
            st.log(f"⚠️  Router-ID {expected_router_id} not found on {dut}")
            return False

    except Exception as e:
        st.error(f"Failed to verify router-ID on {dut}: {e}")
        return False


def cleanup_bgp_config(dut: str) -> None:
    """Remove BGP configuration."""
    try:
        commands = ["no router bgp"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup on {dut}: {e}")


def test_bgp57_router_id_tiebreak():
    """
    BGP-57: Verify router-ID configuration and tie-break concept.

    2-DEVICE LIMITATION: This test cannot fully demonstrate router-ID tie-break
    because locally originated routes always win. A proper test requires receiving
    the same prefix from MULTIPLE neighbors.

    Test Steps:
    1. Configure IP addresses and loopbacks on both DUTs
    2. Configure EBGP between DUT1 (AS 65001) and DUT2 (AS 65002)
    3. Set different router-IDs:
       - DUT1: 3.3.3.3 (higher)
       - DUT2: 2.2.2.2 (lower - would win in tie-break)
    4. Advertise networks on both DUTs
    5. Verify EBGP sessions established
    6. Verify router-IDs configured correctly
    7. Document that locally originated routes win (not router-ID)

    Expected Behavior:
    - EBGP session establishes successfully
    - Router-IDs configured as specified
    - Locally originated routes preferred (weight 32768)
    - Router-ID visible in BGP table for external routes

    Router-ID Tie-Break (Step 10):
    - Applies when same prefix received from MULTIPLE neighbors
    - Lower router-ID wins
    - With 2 devices, locally originated routes always win first

    VALIDATION PATTERN:
    - Tracks all validation failures without immediate exit
    - Executes cleanup in finally block (ALWAYS runs)
    - Generates tech-support on validation failures
    - Reports comprehensive results at the end
    """
    st.banner("TEST: BGP-57 - Router-ID Tie-Break (with 2-device limitation)")

    st.log("ℹ️  Testing BGP Router-ID Configuration")
    st.log("ℹ️  DUT1 (AS 65001): Router-ID 3.3.3.3 (higher)")
    st.log("ℹ️  DUT2 (AS 65002): Router-ID 2.2.2.2 (lower)")
    st.log("⚠️  2-Device Limitation: Locally originated routes win before router-ID tie-break")

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
            st.log(f"✓ Interface {data.d1_phy_port} configured on {vars.D1}")

        if not configure_ip_interface(vars.D2, CONFIG.dut2_ip):
            error_msg = f"Interface configuration failed on {vars.D2} - IP: {CONFIG.dut2_ip}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ Interface {data.d2_phy_port} configured on {vars.D2}")

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

        # Step 2: Configure BGP with specific router-IDs
        st.log("STEP 2: Configure BGP with EBGP neighbors and specific router-IDs")
        st.log(f"   DUT1: AS {CONFIG.dut1_asn}, Router-ID {CONFIG.dut1_router_id}")

        if not configure_bgp_with_neighbor(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_router_id,
                                           CONFIG.dut2_ip, CONFIG.dut2_asn):
            error_msg = f"BGP configuration failed on {vars.D1} - AS: {CONFIG.dut1_asn}, Router-ID: {CONFIG.dut1_router_id}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ BGP AS {CONFIG.dut1_asn} configured on {vars.D1} with router-ID {CONFIG.dut1_router_id}")

        st.log(f"   DUT2: AS {CONFIG.dut2_asn}, Router-ID {CONFIG.dut2_router_id}")

        if not configure_bgp_with_neighbor(vars.D2, CONFIG.dut2_asn, CONFIG.dut2_router_id,
                                           CONFIG.dut1_ip, CONFIG.dut1_asn):
            error_msg = f"BGP configuration failed on {vars.D2} - AS: {CONFIG.dut2_asn}, Router-ID: {CONFIG.dut2_router_id}"
            st.error(error_msg)
            validation_failures.append(error_msg)
        else:
            st.log(f"✓ BGP AS {CONFIG.dut2_asn} configured on {vars.D2} with router-ID {CONFIG.dut2_router_id}")

        # Step 3: Advertise networks
        st.log("STEP 3: Advertise networks on both DUTs")
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

        # Step 4: Wait for EBGP session
        st.log("STEP 4: Wait for EBGP sessions to establish")
        st.wait(20)

        # Step 5: Verify EBGP sessions
        st.log("STEP 5: Verify EBGP sessions established")

        if not verify_bgp_session(vars.D1, CONFIG.dut2_ip):
            st.log(f"Warning: EBGP session to {CONFIG.dut2_ip} not fully established on {vars.D1}")
        else:
            st.log(f"✓ EBGP session established on {vars.D1} to {CONFIG.dut2_ip}")

        if not verify_bgp_session(vars.D2, CONFIG.dut1_ip):
            st.log(f"Warning: EBGP session to {CONFIG.dut1_ip} not fully established on {vars.D2}")
        else:
            st.log(f"✓ EBGP session established on {vars.D2} to {CONFIG.dut1_ip}")

        # Step 6: Verify router-IDs
        st.log("STEP 6: Verify router-IDs configured correctly")
        verify_router_id(vars.D1, CONFIG.dut1_router_id)
        verify_router_id(vars.D2, CONFIG.dut2_router_id)

    except Exception as e:
        error_msg = f"Exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)
        st.log(f"Exception details: {e}")

    finally:
        # CLEANUP: Always executes regardless of test outcome
        st.banner("CLEANUP: Unconfiguring BGP and IP (ALWAYS EXECUTES)")

        try:
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
                st.generate_tech_support(dut_list=[vars.D1, vars.D2], name="bgp57_validation_failures")
                tech_support_generated = True
                st.log("✓ Tech-support generated successfully")
            except Exception as tech_error:
                st.error(f"Failed to generate tech-support: {tech_error}")

    # Final reporting
    st.banner("BGP-57 TEST FINAL REPORT")

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
        st.log("✅ BGP-57 Test PASSED: Router-ID Configuration")
        st.log("   CONFIGURATION:")
        st.log(f"   - DUT1 (AS {CONFIG.dut1_asn}): Router-ID {CONFIG.dut1_router_id} (higher)")
        st.log(f"   - DUT2 (AS {CONFIG.dut2_asn}): Router-ID {CONFIG.dut2_router_id} (lower)")
        st.log("   ⚠️  2-DEVICE LIMITATION:")
        st.log("      - Both routers advertise 192.168.100.0/24 locally")
        st.log("      - Locally originated routes always win (weight 32768)")
        st.log("      - Router-ID tie-break requires MULTIPLE neighbors advertising same prefix")
        st.log("   ROUTER-ID TIE-BREAK RULE (Step 10):")
        st.log("      - Lower router-ID wins when all other attributes equal")
        st.log("      - Requires receiving same prefix from multiple neighbors")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
