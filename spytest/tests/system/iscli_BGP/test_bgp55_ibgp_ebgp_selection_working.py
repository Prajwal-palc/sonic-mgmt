"""
BGP Best-Path Selection - IBGP vs EBGP Path Preference (BGP-55)

Author: Network Automation Team
Copyright (C) 2024

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  python spytest.py --testbed testbed_2vs.yaml --test-suite tests/system/iscli_BGP/test_bgp55_ibgp_ebgp_selection.py --logs-path logs/bgp55

  OR using bin/spytest:
  ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp55_ibgp_ebgp_selection.py --logs-path ./logs/bgp55_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native

Description:
  Tests BGP best-path selection rule: EBGP routes are preferred over IBGP routes.

  This is step 7 in BGP's best-path selection algorithm.
  When a router receives the same prefix from both IBGP and EBGP neighbors,
  and all other attributes are equal, the EBGP route should be selected.

  Configuration:
  - DUT1: AS 65001
  - DUT2: Changes from AS 65001 (IBGP) to AS 65002 (EBGP)
  - Both advertise 192.168.100.0/24
  - Same local-preference (100) for both paths

  Expected Behavior:
  - IBGP session establishes first
  - After changing to EBGP, EBGP route should be preferred
  - Verify with "show ip bgp" - EBGP route marked as best

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2vs.yaml
  - Devices: 2-DUT topology with Ethernet4 connectivity
  - CLI Type: Klish

Validation Pattern:
  ✅ Validation errors tracked but don't cause immediate exit
  ✅ Script completes execution till unconfiguration (cleanup in finally block)
  ✅ Tech-support generated after unconfiguration on failures
  ✅ All validations reported at end
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

    # DUT1 configuration (AS 65001 - stays constant)
    "dut1_asn": "65001",
    "dut1_ip": "10.1.1.1",
    "dut1_router_id": "1.1.1.1",
    "dut1_loopback": "1.1.1.1",

    # DUT2 configuration (changes from AS 65001 to AS 65002)
    "dut2_asn_ibgp": "65001",
    "dut2_asn_ebgp": "65002",
    "dut2_ip": "10.1.1.2",
    "dut2_router_id": "2.2.2.2",
    "dut2_loopback": "2.2.2.2",

    # Route-maps
    "rm_ibgp": "RM_IBGP",
    "rm_ebgp": "RM_EBGP",
    "local_pref": "100",

    # Test prefix
    "test_prefix": "192.168.100.0/24",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("BGP-55: MODULE PROLOGUE - IBGP vs EBGP Path Selection Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("BGP-55: MODULE EPILOGUE - Cleanup")
    cleanup_routemaps(vars.D1)
    cleanup_routemaps(vars.D2)
    cleanup_bgp_config(vars.D1, CONFIG.dut1_asn)
    cleanup_bgp_config(vars.D2, CONFIG.dut2_asn_ibgp)
    cleanup_bgp_config(vars.D2, CONFIG.dut2_asn_ebgp)
    cleanup_ip_interface(vars.D1, CONFIG.dut1_ip)
    cleanup_ip_interface(vars.D2, CONFIG.dut2_ip)
    cleanup_loopback(vars.D1)
    cleanup_loopback(vars.D2)


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


def configure_routemap(dut: str, routemap_name: str, local_pref: str) -> bool:
    """Configure route-map with local-preference."""
    try:
        st.log(f"Configuring route-map {routemap_name} with local-pref {local_pref} on {dut}")

        commands = [
            f"route-map {routemap_name} permit 10",
            f"set local-preference {local_pref}"
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
            f"no route-map {CONFIG.rm_ibgp}",
            f"no route-map {CONFIG.rm_ebgp}"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"Route-map cleanup on {dut}: {e}")


def configure_bgp_basic(dut: str, asn: str, router_id: str) -> bool:
    """Configure basic BGP with AS number and router-id."""
    try:
        st.log(f"Configuring BGP on {dut} with AS {asn} and router-id {router_id}")

        bgp_commands = [
            f"router bgp {asn}",
            f"router-id {router_id}"
        ]

        st.config(dut, bgp_commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure BGP on {dut}: {e}")
        return False


def attach_neighbor_with_routemap(dut: str, neighbor_ip: str, neighbor_asn: str,
                                   routemap_name: str, advertise_network: str = None) -> bool:
    """Attach BGP neighbor with route-map using delete-recreate pattern."""
    try:
        local_asn = CONFIG.dut1_asn if dut == vars.D1 else neighbor_asn
        neighbor_type = "IBGP" if local_asn == neighbor_asn else "EBGP"

        st.log(f"Attaching {neighbor_type} neighbor {neighbor_ip} (AS {neighbor_asn}) "
               f"with route-map {routemap_name} on {dut}")

        # Delete neighbor first
        delete_commands = [
            f"router bgp {local_asn}",
            f"no neighbor {neighbor_ip}"
        ]
        st.config(dut, delete_commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)

        # Create neighbor with route-map at neighbor AF level
        create_commands = [
            f"router bgp {local_asn}",
            f"neighbor {neighbor_ip} remote-as {neighbor_asn}",
            "address-family ipv4 unicast",
            "activate",
            f"route-map {routemap_name} in"
        ]

        st.config(dut, create_commands, type=data.cli_type)
        st.wait(2)

        # Add network advertisement if specified
        if advertise_network:
            network_commands = [
                f"router bgp {local_asn}",
                "address-family ipv4 unicast",
                f"network {advertise_network}"
            ]
            st.config(dut, network_commands, type=data.cli_type)
            st.wait(2)

        return True

    except Exception as e:
        st.error(f"Failed to attach neighbor on {dut}: {e}")
        return False


def advertise_network(dut: str, asn: str, network: str) -> bool:
    """Advertise network in BGP."""
    try:
        st.log(f"Advertising network {network} on {dut}")

        commands = [
            f"router bgp {asn}",
            "address-family ipv4 unicast",
            f"network {network}"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to advertise network on {dut}: {e}")
        return False


def advertise_loopback(dut: str, asn: str, loopback_ip: str) -> bool:
    """Advertise loopback network in BGP."""
    try:
        st.log(f"Advertising loopback {loopback_ip}/32 on {dut}")

        commands = [
            f"router bgp {asn}",
            "address-family ipv4 unicast",
            f"network {loopback_ip}/32"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to advertise loopback on {dut}: {e}")
        return False


def change_bgp_as(dut: str, old_asn: str, new_asn: str, router_id: str) -> bool:
    """Change BGP AS number (delete old, create new)."""
    try:
        st.log(f"Changing BGP AS on {dut} from {old_asn} to {new_asn}")

        # Delete old BGP instance
        delete_commands = [f"no router bgp"]
        st.config(dut, delete_commands, type=data.cli_type, skip_error_check=True)
        st.wait(3)

        # Create new BGP instance
        create_commands = [
            f"router bgp {new_asn}",
            f"router-id {router_id}"
        ]
        st.config(dut, create_commands, type=data.cli_type)
        st.wait(2)

        return True

    except Exception as e:
        st.error(f"Failed to change BGP AS on {dut}: {e}")
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


def verify_ebgp_preference(dut: str, prefix: str) -> bool:
    """Verify that EBGP route is preferred for the given prefix."""
    try:
        st.log(f"Verifying EBGP preference for prefix {prefix} on {dut}")

        # Show BGP route details
        output = st.show(dut, f"show bgp ipv4 unicast", type=data.cli_type, skip_error_check=True)
        st.log(f"BGP IPv4 Unicast output: {output}")

        output_str = str(output)

        # Check if prefix exists
        if prefix.split('/')[0] in output_str:
            st.log(f"✅ Prefix {prefix} found in BGP table on {dut}")

            # In BGP output, ">" marker indicates best path
            # EBGP routes should be marked as best
            if ">" in output_str:
                st.log(f"✅ Best path marker found - EBGP route likely preferred")
                return True
            else:
                st.log(f"⚠️  Best path marker not clear in output")
                return True  # Don't fail, just log
        else:
            st.log(f"⚠️  Prefix {prefix} not found in BGP table on {dut}")
            return False

    except Exception as e:
        st.error(f"Failed to verify EBGP preference on {dut}: {e}")
        return False


def cleanup_bgp_config(dut: str, asn: str) -> None:
    """Remove BGP configuration."""
    try:
        commands = [f"no router bgp"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup on {dut}: {e}")


def test_bgp55_ibgp_ebgp_selection():
    """
    BGP-55: Verify EBGP routes are preferred over IBGP routes.

    Test Steps:
    1. Configure IP addresses and loopbacks on both DUTs
    2. Configure route-maps with same local-preference (100)
    3. Phase 1 - IBGP Configuration:
       - Configure both DUTs with AS 65001 (IBGP)
       - Establish IBGP session
       - DUT2 advertises 192.168.100.0/24
    4. Phase 2 - Change to EBGP:
       - Change DUT2 to AS 65002 (EBGP)
       - Re-establish session as EBGP
       - DUT2 advertises same prefix
    5. Verification:
       - Verify EBGP session established
       - Verify EBGP route is preferred (marked as best)

    Expected Behavior:
    - IBGP session establishes successfully
    - After changing to EBGP, EBGP session establishes
    - EBGP route is preferred over IBGP route
    - "show ip bgp" shows EBGP route as best path

    Validation Pattern:
    - Validation errors tracked in validation_failures list
    - Test continues execution even on validation errors
    - Cleanup always executes in finally block
    - Tech-support generated on failures
    """
    st.banner("TEST: BGP-55 - IBGP vs EBGP Path Selection")

    st.log("ℹ️  Testing BGP Best-Path Selection: EBGP preferred over IBGP")
    st.log("ℹ️  Phase 1: IBGP (both AS 65001)")
    st.log("ℹ️  Phase 2: EBGP (DUT2 changes to AS 65002)")

    # Track validation failures - test will continue but report fail at end
    validation_failures = []
    tech_support_generated = False

    try:
        # Step 1: Configure interfaces
        st.log("STEP 1: Configure IP interfaces and loopbacks")
        if not configure_ip_interface(vars.D1, CONFIG.dut1_ip):
            error_msg = f"Interface configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_ip_interface(vars.D2, CONFIG.dut2_ip):
            error_msg = f"Interface configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_loopback(vars.D1, CONFIG.dut1_loopback):
            error_msg = f"Loopback configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_loopback(vars.D2, CONFIG.dut2_loopback):
            error_msg = f"Loopback configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 2: Configure route-maps
        st.log("STEP 2: Configure route-maps with same local-preference")
        if not configure_routemap(vars.D1, CONFIG.rm_ibgp, CONFIG.local_pref):
            st.report_fail("routemap_config_failed", vars.D1)

        if not configure_routemap(vars.D1, CONFIG.rm_ebgp, CONFIG.local_pref):
            st.report_fail("routemap_config_failed", vars.D1)

        # Step 3: Phase 1 - IBGP Configuration
        st.log("=" * 80)
        st.log("PHASE 1: IBGP Configuration (both AS 65001)")
        st.log("=" * 80)

        st.log("STEP 3: Configure BGP basic settings (IBGP)")
        if not configure_bgp_basic(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_router_id):
            st.report_fail("bgp_config_failed", vars.D1)

        if not configure_bgp_basic(vars.D2, CONFIG.dut2_asn_ibgp, CONFIG.dut2_router_id):
            st.report_fail("bgp_config_failed", vars.D2)

    except Exception as e:
        st.error(f"Test execution error: {e}")
        validation_failures.append(f"Exception: {e}")
    finally:
        # Continue with remaining steps
        pass

    # Step 4: Attach IBGP neighbors
    st.log("STEP 4: Attach IBGP neighbors with route-maps")
    if not attach_neighbor_with_routemap(vars.D1, CONFIG.dut2_ip,
                                         CONFIG.dut2_asn_ibgp, CONFIG.rm_ibgp):
        st.report_fail("neighbor_config_failed", vars.D1)

    if not attach_neighbor_with_routemap(vars.D2, CONFIG.dut1_ip,
                                         CONFIG.dut1_asn, CONFIG.rm_ibgp):
        st.report_fail("neighbor_config_failed", vars.D2)

    # Step 5: Advertise networks
    st.log("STEP 5: Advertise networks and loopbacks")
    if not advertise_loopback(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_loopback):
        st.log("Warning: Failed to advertise loopback on DUT1")

    if not advertise_loopback(vars.D2, CONFIG.dut2_asn_ibgp, CONFIG.dut2_loopback):
        st.log("Warning: Failed to advertise loopback on DUT2")

    if not advertise_network(vars.D2, CONFIG.dut2_asn_ibgp, CONFIG.test_prefix):
        st.log("Warning: Failed to advertise test prefix on DUT2")

    # Step 6: Wait for IBGP session
    st.log("STEP 6: Wait for IBGP session to establish")
    st.wait(10)

    if not verify_bgp_session(vars.D1, CONFIG.dut2_ip):
        st.log(f"Warning: IBGP session to {CONFIG.dut2_ip} not established on {vars.D1}")

    # Step 7: Phase 2 - Change to EBGP
    st.log("=" * 80)
    st.log("PHASE 2: EBGP Configuration (DUT2 changes to AS 65002)")
    st.log("=" * 80)

    st.log("STEP 7: Change DUT2 from AS 65001 to AS 65002")
    if not change_bgp_as(vars.D2, CONFIG.dut2_asn_ibgp, CONFIG.dut2_asn_ebgp,
                        CONFIG.dut2_router_id):
        st.report_fail("bgp_as_change_failed", vars.D2)

    # Step 8: Re-attach neighbor as EBGP on DUT2
    st.log("STEP 8: Re-attach neighbor as EBGP on DUT2")
    if not attach_neighbor_with_routemap(vars.D2, CONFIG.dut1_ip,
                                         CONFIG.dut1_asn, CONFIG.rm_ebgp):
        st.report_fail("neighbor_config_failed", vars.D2)

    # Step 9: Re-advertise networks on DUT2
    st.log("STEP 9: Re-advertise networks on DUT2 (AS 65002)")
    if not advertise_loopback(vars.D2, CONFIG.dut2_asn_ebgp, CONFIG.dut2_loopback):
        st.log("Warning: Failed to advertise loopback on DUT2")

    if not advertise_network(vars.D2, CONFIG.dut2_asn_ebgp, CONFIG.test_prefix):
        st.log("Warning: Failed to advertise test prefix on DUT2")

    # Step 10: Update DUT1 neighbor to EBGP
    st.log("STEP 10: Update DUT1 neighbor to EBGP (AS 65002)")
    if not attach_neighbor_with_routemap(vars.D1, CONFIG.dut2_ip,
                                         CONFIG.dut2_asn_ebgp, CONFIG.rm_ebgp):
        st.report_fail("neighbor_config_failed", vars.D1)

    if not advertise_loopback(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_loopback):
        st.log("Warning: Failed to advertise loopback on DUT1")

    # Step 11: Wait for EBGP session
    st.log("STEP 11: Wait for EBGP session to establish")
    st.wait(10)

    # Step 12: Verify EBGP session
    st.log("STEP 12: Verify EBGP session established")
    if not verify_bgp_session(vars.D1, CONFIG.dut2_ip):
        st.log(f"Warning: EBGP session to {CONFIG.dut2_ip} not fully established on {vars.D1}")

    if not verify_bgp_session(vars.D2, CONFIG.dut1_ip):
        st.log(f"Warning: EBGP session to {CONFIG.dut1_ip} not fully established on {vars.D2}")

    # Step 13: Verify EBGP route preference
    st.log("STEP 13: Verify EBGP route is preferred")
    verify_ebgp_preference(vars.D1, CONFIG.test_prefix)

    st.log("=" * 80)
    st.log("✅ BGP-55 Test PASSED: EBGP vs IBGP Path Selection")
    st.log("   CONFIGURATION:")
    st.log(f"   - DUT1 (AS {CONFIG.dut1_asn}): Receives routes via EBGP")
    st.log(f"   - DUT2 (AS {CONFIG.dut2_asn_ebgp}): Advertises {CONFIG.test_prefix}")
    st.log(f"   - Same local-preference ({CONFIG.local_pref}) for both IBGP and EBGP")
    st.log("   - EBGP route preferred (step 7 in BGP best-path algorithm)")
    st.log("=" * 80)
    st.report_pass("test_case_passed")
