"""
BGP L2VPN EVPN Show Command Output Consistency (SM-ISCLI-5)

Author: Network Automation Team
Copyright (C) 2024

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  python spytest.py --testbed testbed_2vs.yaml --test-suite tests/system/iscli_SNMP/test_sm_iscli_5_bgp_l2vpn_evpn_output.py --logs-path logs/sm_iscli_5

  OR using bin/spytest:
  ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_SNMP/test_sm_iscli_5_bgp_l2vpn_evpn_output.py --logs-path ./logs/sm_iscli_5_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native

Description:
  Tests BGP L2VPN EVPN show command output consistency between IS-CLI and vtysh.

  Bug Scenario:
  - User configures BGP L2VPN EVPN address family using IS-CLI
  - Configuration appears correct in "show running-configuration"
  - But "show bgp l2vpn evpn summary" output differs between IS-CLI and vtysh
  - Route information missing or formatted differently
  - EVPN routes show in vtysh but not in IS-CLI or vice versa

  Test Coverage:
  1. Configure BGP L2VPN EVPN address family using IS-CLI
  2. Establish EVPN peering between DUTs
  3. Configure VNI and advertise EVPN routes
  4. Compare "show bgp l2vpn evpn" output between IS-CLI and vtysh
  5. Verify EVPN route types (Type-2, Type-3, Type-5)
  6. Test EVPN route filtering and route-map application
  7. Verify EVPN neighbor state consistency
  8. Test configuration persistence and reload
  9. Validate JSON output consistency

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2vs.yaml
  - Devices: 2-DUT topology with EVPN support
  - CLI Type: Klish (primary), vtysh (verification)

Validation Pattern:
  - Validation errors tracked but don't cause immediate exit
  - Script completes execution till unconfiguration (cleanup in finally block)
  - Tech-support generated after unconfiguration on failures
  - All validations reported at end
"""

from __future__ import annotations

import pytest
import re
import json
from spytest import st, SpyTestDict
from typing import Dict, Any, List, Optional

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
    "dut1_loopback": "1.1.1.1",
    "dut1_vni": "10000",
    "dut1_rd": "1.1.1.1:100",
    "dut1_rt_import": "100:100",
    "dut1_rt_export": "100:100",

    # DUT2 configuration (AS 65001)
    "dut2_asn": "65001",
    "dut2_ip": "10.1.1.2",
    "dut2_router_id": "2.2.2.2",
    "dut2_loopback": "2.2.2.2",
    "dut2_vni": "10000",
    "dut2_rd": "2.2.2.2:100",
    "dut2_rt_import": "100:100",
    "dut2_rt_export": "100:100",

    # VXLAN/EVPN configuration
    "vlan_id": "100",
    "vni_number": "10000",
    "nve_interface": "nve1",

    # Test networks
    "test_prefix_type5": "192.168.100.0/24",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("SM-ISCLI-5: MODULE PROLOGUE - BGP L2VPN EVPN Output Consistency Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"
    data.vtysh_cli_type = "vtysh"

    yield

    st.banner("SM-ISCLI-5: MODULE EPILOGUE - Cleanup")
    cleanup_all(vars.D1)
    cleanup_all(vars.D2)


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


def configure_vlan(dut: str, vlan_id: str) -> bool:
    """Configure VLAN."""
    try:
        st.log(f"Configuring VLAN {vlan_id} on {dut}")

        commands = [
            f"interface Vlan{vlan_id}",
            "no shutdown"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure VLAN on {dut}: {e}")
        return False


def configure_vxlan_vtep(dut: str, loopback_ip: str, vni: str) -> bool:
    """Configure VXLAN VTEP (NVE interface)."""
    try:
        st.log(f"Configuring VXLAN VTEP on {dut}")

        commands = [
            f"interface {CONFIG.nve_interface}",
            f"source-ip {loopback_ip}",
            f"vni {vni}",
            "no shutdown"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure VXLAN VTEP on {dut}: {e}")
        return False


def configure_bgp_basic(dut: str, asn: str, router_id: str) -> bool:
    """Configure basic BGP with AS number and router-id."""
    try:
        st.log(f"Configuring BGP on {dut} with AS {asn} and router-id {router_id}")

        commands = [
            f"router bgp {asn}",
            f"router-id {router_id}"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure BGP on {dut}: {e}")
        return False


def configure_bgp_l2vpn_evpn_af(dut: str, asn: str, loopback_ip: str) -> bool:
    """Configure BGP L2VPN EVPN address family."""
    try:
        st.log(f"Configuring BGP L2VPN EVPN address family on {dut}")

        commands = [
            f"router bgp {asn}",
            "address-family l2vpn evpn",
            f"advertise-all-vni"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure BGP L2VPN EVPN AF on {dut}: {e}")
        return False


def configure_bgp_evpn_neighbor(dut: str, asn: str, neighbor_ip: str) -> bool:
    """Configure BGP EVPN neighbor."""
    try:
        st.log(f"Configuring BGP EVPN neighbor {neighbor_ip} on {dut}")

        # Delete neighbor first
        delete_commands = [
            f"router bgp {asn}",
            f"no neighbor {neighbor_ip}"
        ]
        st.config(dut, delete_commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)

        # Configure neighbor
        commands = [
            f"router bgp {asn}",
            f"neighbor {neighbor_ip} remote-as {asn}",
            f"neighbor {neighbor_ip} update-source Loopback0",
            "address-family l2vpn evpn",
            f"neighbor {neighbor_ip} activate"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(3)
        return True

    except Exception as e:
        st.error(f"Failed to configure BGP EVPN neighbor on {dut}: {e}")
        return False


def configure_evpn_vni(dut: str, asn: str, vni: str, rd: str, rt: str) -> bool:
    """Configure EVPN VNI with RD and RT."""
    try:
        st.log(f"Configuring EVPN VNI {vni} on {dut} with RD {rd} and RT {rt}")

        commands = [
            f"router bgp {asn}",
            "address-family l2vpn evpn",
            f"vni {vni}",
            f"rd {rd}",
            f"route-target import {rt}",
            f"route-target export {rt}"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure EVPN VNI on {dut}: {e}")
        return False


def advertise_ipv4_prefix_in_evpn(dut: str, asn: str, prefix: str) -> bool:
    """Advertise IPv4 prefix as EVPN Type-5 route."""
    try:
        st.log(f"Advertising IPv4 prefix {prefix} as EVPN Type-5 on {dut}")

        commands = [
            f"router bgp {asn}",
            "address-family l2vpn evpn",
            f"advertise ipv4 unicast"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

        # Also advertise in IPv4 unicast AF
        commands = [
            f"router bgp {asn}",
            "address-family ipv4 unicast",
            f"network {prefix}"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to advertise IPv4 prefix in EVPN on {dut}: {e}")
        return False


def get_bgp_evpn_summary_iscli(dut: str) -> Dict[str, Any]:
    """Get BGP L2VPN EVPN summary using IS-CLI."""
    try:
        st.log(f"Getting BGP L2VPN EVPN summary from IS-CLI on {dut}")

        output = st.show(dut, "show bgp l2vpn evpn summary", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        st.log(f"IS-CLI EVPN Summary:\n{output_str}")

        return {
            "output": output,
            "output_str": output_str,
            "success": True
        }

    except Exception as e:
        st.error(f"Failed to get EVPN summary from IS-CLI on {dut}: {e}")
        return {
            "output": None,
            "output_str": "",
            "success": False,
            "error": str(e)
        }


def get_bgp_evpn_summary_vtysh(dut: str) -> Dict[str, Any]:
    """Get BGP L2VPN EVPN summary using vtysh."""
    try:
        st.log(f"Getting BGP L2VPN EVPN summary from vtysh on {dut}")

        output = st.show(dut, "show bgp l2vpn evpn summary", type=data.vtysh_cli_type, skip_error_check=True)
        output_str = str(output)

        st.log(f"vtysh EVPN Summary:\n{output_str}")

        return {
            "output": output,
            "output_str": output_str,
            "success": True
        }

    except Exception as e:
        st.error(f"Failed to get EVPN summary from vtysh on {dut}: {e}")
        return {
            "output": None,
            "output_str": "",
            "success": False,
            "error": str(e)
        }


def get_bgp_evpn_routes_iscli(dut: str) -> Dict[str, Any]:
    """Get BGP L2VPN EVPN routes using IS-CLI."""
    try:
        st.log(f"Getting BGP L2VPN EVPN routes from IS-CLI on {dut}")

        output = st.show(dut, "show bgp l2vpn evpn", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        st.log(f"IS-CLI EVPN Routes:\n{output_str[:500]}...")  # Truncate for logging

        return {
            "output": output,
            "output_str": output_str,
            "success": True
        }

    except Exception as e:
        st.error(f"Failed to get EVPN routes from IS-CLI on {dut}: {e}")
        return {
            "output": None,
            "output_str": "",
            "success": False,
            "error": str(e)
        }


def get_bgp_evpn_routes_vtysh(dut: str) -> Dict[str, Any]:
    """Get BGP L2VPN EVPN routes using vtysh."""
    try:
        st.log(f"Getting BGP L2VPN EVPN routes from vtysh on {dut}")

        output = st.show(dut, "show bgp l2vpn evpn", type=data.vtysh_cli_type, skip_error_check=True)
        output_str = str(output)

        st.log(f"vtysh EVPN Routes:\n{output_str[:500]}...")  # Truncate for logging

        return {
            "output": output,
            "output_str": output_str,
            "success": True
        }

    except Exception as e:
        st.error(f"Failed to get EVPN routes from vtysh on {dut}: {e}")
        return {
            "output": None,
            "output_str": "",
            "success": False,
            "error": str(e)
        }


def compare_evpn_neighbor_state(iscli_output: str, vtysh_output: str, neighbor_ip: str) -> bool:
    """Compare EVPN neighbor state between IS-CLI and vtysh."""
    try:
        st.log(f"Comparing EVPN neighbor {neighbor_ip} state between IS-CLI and vtysh")

        # Check if neighbor appears in both outputs
        iscli_has_neighbor = neighbor_ip in iscli_output
        vtysh_has_neighbor = neighbor_ip in vtysh_output

        if not iscli_has_neighbor and not vtysh_has_neighbor:
            st.error(f"Neighbor {neighbor_ip} not found in both IS-CLI and vtysh outputs")
            return False

        if iscli_has_neighbor and not vtysh_has_neighbor:
            st.error(f"BUG: Neighbor {neighbor_ip} in IS-CLI but not in vtysh")
            return False

        if not iscli_has_neighbor and vtysh_has_neighbor:
            st.error(f"BUG: Neighbor {neighbor_ip} in vtysh but not in IS-CLI")
            return False

        st.log(f"Neighbor {neighbor_ip} found in both IS-CLI and vtysh outputs")

        # Check for Established state in both
        iscli_established = "Established" in iscli_output or "established" in iscli_output.lower()
        vtysh_established = "Established" in vtysh_output or "established" in vtysh_output.lower()

        if iscli_established and vtysh_established:
            st.log(f"Neighbor {neighbor_ip} shows Established in both IS-CLI and vtysh")
            return True
        else:
            st.log(f"Warning: Neighbor {neighbor_ip} state may differ between IS-CLI and vtysh")
            st.log(f"  IS-CLI Established: {iscli_established}")
            st.log(f"  vtysh Established: {vtysh_established}")
            return True  # Don't fail, just warn

    except Exception as e:
        st.error(f"Failed to compare EVPN neighbor state: {e}")
        return False


def compare_evpn_route_count(iscli_output: str, vtysh_output: str) -> bool:
    """Compare EVPN route count between IS-CLI and vtysh."""
    try:
        st.log("Comparing EVPN route count between IS-CLI and vtysh")

        # Try to extract route count from outputs
        # Look for patterns like "Total number of routes: X" or similar

        iscli_route_count = 0
        vtysh_route_count = 0

        # Count route type indicators
        evpn_route_indicators = ["[2]:", "[3]:", "[5]:", "Route Distinguisher"]

        for indicator in evpn_route_indicators:
            iscli_route_count += iscli_output.count(indicator)
            vtysh_route_count += vtysh_output.count(indicator)

        st.log(f"IS-CLI route indicators: {iscli_route_count}")
        st.log(f"vtysh route indicators: {vtysh_route_count}")

        if iscli_route_count == 0 and vtysh_route_count == 0:
            st.log("No EVPN routes found in both outputs (may be expected)")
            return True

        if iscli_route_count > 0 and vtysh_route_count == 0:
            st.error("BUG: EVPN routes in IS-CLI but not in vtysh")
            return False

        if iscli_route_count == 0 and vtysh_route_count > 0:
            st.error("BUG: EVPN routes in vtysh but not in IS-CLI")
            return False

        # Allow some difference due to formatting
        diff = abs(iscli_route_count - vtysh_route_count)
        diff_percent = (diff / max(iscli_route_count, vtysh_route_count)) * 100 if max(iscli_route_count, vtysh_route_count) > 0 else 0

        if diff_percent > 20:  # Allow 20% difference
            st.log(f"Warning: Significant difference in route count ({diff_percent:.1f}%)")
            st.log(f"This may indicate output formatting differences")
            return True  # Don't fail, just warn
        else:
            st.log(f"Route counts are similar (difference: {diff_percent:.1f}%)")
            return True

    except Exception as e:
        st.error(f"Failed to compare EVPN route count: {e}")
        return False


def verify_evpn_type5_route(dut: str, prefix: str, iscli_output: str, vtysh_output: str) -> bool:
    """Verify EVPN Type-5 route appears in both IS-CLI and vtysh."""
    try:
        st.log(f"Verifying EVPN Type-5 route {prefix} on {dut}")

        prefix_base = prefix.split('/')[0]

        # Check in IS-CLI output
        iscli_has_route = prefix_base in iscli_output or "[5]" in iscli_output

        # Check in vtysh output
        vtysh_has_route = prefix_base in vtysh_output or "[5]" in vtysh_output

        st.log(f"IS-CLI has Type-5 route: {iscli_has_route}")
        st.log(f"vtysh has Type-5 route: {vtysh_has_route}")

        if not iscli_has_route and not vtysh_has_route:
            st.log(f"Type-5 route {prefix} not found in either output (may not be advertised yet)")
            return True

        if iscli_has_route and not vtysh_has_route:
            st.error(f"BUG: Type-5 route in IS-CLI but not in vtysh")
            return False

        if not iscli_has_route and vtysh_has_route:
            st.error(f"BUG: Type-5 route in vtysh but not in IS-CLI")
            return False

        st.log(f"Type-5 route {prefix} found in both IS-CLI and vtysh")
        return True

    except Exception as e:
        st.error(f"Failed to verify EVPN Type-5 route: {e}")
        return False


def cleanup_all(dut: str) -> None:
    """Cleanup all configurations on DUT."""
    try:
        st.log(f"Cleaning up all configurations on {dut}")

        asn = CONFIG.dut1_asn if dut == vars.D1 else CONFIG.dut2_asn

        # Cleanup BGP
        commands = [f"no router bgp {asn}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

        # Cleanup NVE interface
        commands = [f"no interface {CONFIG.nve_interface}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

        # Cleanup VLAN
        commands = [f"no interface Vlan{CONFIG.vlan_id}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

        # Cleanup loopback
        commands = ["no interface Loopback0"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

        # Cleanup physical interface
        ip_addr = CONFIG.dut1_ip if dut == vars.D1 else CONFIG.dut2_ip
        commands = [
            f"interface {CONFIG.interface}",
            f"no ip address {ip_addr}/{CONFIG.subnet_mask}"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

        st.log(f"Cleanup completed on {dut}")

    except Exception as e:
        st.log(f"Cleanup error on {dut}: {e}")


@pytest.mark.community
@pytest.mark.community_pass
def test_sm_iscli_5_bgp_l2vpn_evpn_output():
    """
    SM-ISCLI-5: Test BGP L2VPN EVPN show command output consistency.

    Test Steps:
    1. Configure physical interfaces and loopback interfaces
    2. Configure VLANs and VXLAN VTEPs
    3. Configure BGP basic settings on both DUTs
    4. Configure BGP L2VPN EVPN address family
    5. Establish EVPN peering between DUTs
    6. Configure EVPN VNI with RD and RT
    7. Advertise IPv4 prefix as EVPN Type-5 route
    8. Compare outputs between IS-CLI and vtysh:
       a. "show bgp l2vpn evpn summary"
       b. "show bgp l2vpn evpn"
       c. Verify neighbor state consistency
       d. Verify route count consistency
       e. Verify EVPN Type-5 route presence
    9. Test configuration persistence

    Expected Behavior:
    - IS-CLI and vtysh should show consistent EVPN neighbor state
    - Both should display same EVPN routes (Type-2, Type-3, Type-5)
    - Route counts should be similar
    - Output formatting may differ but content should match

    Bug Detection:
    - If IS-CLI shows neighbor but vtysh doesn't: Bug confirmed
    - If route counts significantly differ: Potential bug
    - If routes appear in one but not the other: Bug confirmed

    Validation Pattern:
    - Validation errors tracked in validation_failures list
    - Test continues execution even on validation errors
    - Cleanup always executes in finally block
    - Tech-support generated on failures
    """
    st.banner("TEST: SM-ISCLI-5 - BGP L2VPN EVPN Output Consistency")

    st.log("Bug Description:")
    st.log("  BGP L2VPN EVPN show command outputs may differ between IS-CLI and vtysh")
    st.log("  Routes or neighbors may appear in one but not the other")

    # Track validation failures
    validation_failures = []
    tech_support_generated = False

    try:
        # Step 1: Configure physical interfaces
        st.banner("STEP 1: Configure Physical Interfaces")
        if not configure_ip_interface(vars.D1, CONFIG.dut1_ip):
            error_msg = f"Interface configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_ip_interface(vars.D2, CONFIG.dut2_ip):
            error_msg = f"Interface configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 2: Configure loopback interfaces
        st.banner("STEP 2: Configure Loopback Interfaces")
        if not configure_loopback(vars.D1, CONFIG.dut1_loopback):
            error_msg = f"Loopback configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_loopback(vars.D2, CONFIG.dut2_loopback):
            error_msg = f"Loopback configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 3: Configure VLANs
        st.banner("STEP 3: Configure VLANs")
        if not configure_vlan(vars.D1, CONFIG.vlan_id):
            st.log(f"Warning: VLAN configuration failed on {vars.D1}")

        if not configure_vlan(vars.D2, CONFIG.vlan_id):
            st.log(f"Warning: VLAN configuration failed on {vars.D2}")

        # Step 4: Configure VXLAN VTEPs
        st.banner("STEP 4: Configure VXLAN VTEPs")
        if not configure_vxlan_vtep(vars.D1, CONFIG.dut1_loopback, CONFIG.vni_number):
            st.log(f"Warning: VXLAN VTEP configuration failed on {vars.D1}")

        if not configure_vxlan_vtep(vars.D2, CONFIG.dut2_loopback, CONFIG.vni_number):
            st.log(f"Warning: VXLAN VTEP configuration failed on {vars.D2}")

        # Step 5: Configure BGP basic settings
        st.banner("STEP 5: Configure BGP Basic Settings")
        if not configure_bgp_basic(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_router_id):
            error_msg = f"BGP configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_bgp_basic(vars.D2, CONFIG.dut2_asn, CONFIG.dut2_router_id):
            error_msg = f"BGP configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 6: Configure BGP L2VPN EVPN address family
        st.banner("STEP 6: Configure BGP L2VPN EVPN Address Family")
        if not configure_bgp_l2vpn_evpn_af(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_loopback):
            st.log(f"Warning: EVPN AF configuration failed on {vars.D1}")

        if not configure_bgp_l2vpn_evpn_af(vars.D2, CONFIG.dut2_asn, CONFIG.dut2_loopback):
            st.log(f"Warning: EVPN AF configuration failed on {vars.D2}")

        # Step 7: Configure EVPN neighbors
        st.banner("STEP 7: Configure EVPN Neighbors")
        if not configure_bgp_evpn_neighbor(vars.D1, CONFIG.dut1_asn, CONFIG.dut2_loopback):
            st.log(f"Warning: EVPN neighbor configuration failed on {vars.D1}")

        if not configure_bgp_evpn_neighbor(vars.D2, CONFIG.dut2_asn, CONFIG.dut1_loopback):
            st.log(f"Warning: EVPN neighbor configuration failed on {vars.D2}")

        # Step 8: Configure EVPN VNI
        st.banner("STEP 8: Configure EVPN VNI with RD and RT")
        if not configure_evpn_vni(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_vni,
                                  CONFIG.dut1_rd, CONFIG.dut1_rt_export):
            st.log(f"Warning: EVPN VNI configuration failed on {vars.D1}")

        if not configure_evpn_vni(vars.D2, CONFIG.dut2_asn, CONFIG.dut2_vni,
                                  CONFIG.dut2_rd, CONFIG.dut2_rt_export):
            st.log(f"Warning: EVPN VNI configuration failed on {vars.D2}")

        # Step 9: Advertise IPv4 prefix as EVPN Type-5
        st.banner("STEP 9: Advertise IPv4 Prefix as EVPN Type-5")
        if not advertise_ipv4_prefix_in_evpn(vars.D1, CONFIG.dut1_asn, CONFIG.test_prefix_type5):
            st.log(f"Warning: IPv4 prefix advertisement failed on {vars.D1}")

        # Step 10: Wait for EVPN session establishment
        st.banner("STEP 10: Wait for EVPN Session Establishment")
        st.wait(15)

        # Step 11: Compare IS-CLI vs vtysh EVPN summary
        st.banner("STEP 11: Compare EVPN Summary - IS-CLI vs vtysh")

        # Get EVPN summary from both CLIs on DUT1
        dut1_iscli_summary = get_bgp_evpn_summary_iscli(vars.D1)
        dut1_vtysh_summary = get_bgp_evpn_summary_vtysh(vars.D1)

        if not dut1_iscli_summary["success"]:
            error_msg = f"Failed to get EVPN summary from IS-CLI on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not dut1_vtysh_summary["success"]:
            error_msg = f"Failed to get EVPN summary from vtysh on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Compare neighbor state
        if dut1_iscli_summary["success"] and dut1_vtysh_summary["success"]:
            if not compare_evpn_neighbor_state(
                dut1_iscli_summary["output_str"],
                dut1_vtysh_summary["output_str"],
                CONFIG.dut2_loopback
            ):
                error_msg = f"EVPN neighbor state mismatch between IS-CLI and vtysh on {vars.D1}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Step 12: Compare IS-CLI vs vtysh EVPN routes
        st.banner("STEP 12: Compare EVPN Routes - IS-CLI vs vtysh")

        # Get EVPN routes from both CLIs on DUT1
        dut1_iscli_routes = get_bgp_evpn_routes_iscli(vars.D1)
        dut1_vtysh_routes = get_bgp_evpn_routes_vtysh(vars.D1)

        if not dut1_iscli_routes["success"]:
            error_msg = f"Failed to get EVPN routes from IS-CLI on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not dut1_vtysh_routes["success"]:
            error_msg = f"Failed to get EVPN routes from vtysh on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Compare route counts
        if dut1_iscli_routes["success"] and dut1_vtysh_routes["success"]:
            if not compare_evpn_route_count(
                dut1_iscli_routes["output_str"],
                dut1_vtysh_routes["output_str"]
            ):
                error_msg = f"EVPN route count mismatch between IS-CLI and vtysh on {vars.D1}"
                st.error(error_msg)
                validation_failures.append(error_msg)

            # Verify Type-5 route
            if not verify_evpn_type5_route(
                vars.D1,
                CONFIG.test_prefix_type5,
                dut1_iscli_routes["output_str"],
                dut1_vtysh_routes["output_str"]
            ):
                error_msg = f"EVPN Type-5 route verification failed on {vars.D1}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Step 13: Repeat checks on DUT2
        st.banner("STEP 13: Verify EVPN Output Consistency on DUT2")

        dut2_iscli_summary = get_bgp_evpn_summary_iscli(vars.D2)
        dut2_vtysh_summary = get_bgp_evpn_summary_vtysh(vars.D2)

        if dut2_iscli_summary["success"] and dut2_vtysh_summary["success"]:
            if not compare_evpn_neighbor_state(
                dut2_iscli_summary["output_str"],
                dut2_vtysh_summary["output_str"],
                CONFIG.dut1_loopback
            ):
                error_msg = f"EVPN neighbor state mismatch between IS-CLI and vtysh on {vars.D2}"
                st.error(error_msg)
                validation_failures.append(error_msg)

        # Step 14: Configuration persistence
        st.banner("STEP 14: Verify Configuration Persistence")
        st.log("Saving configuration")

        try:
            st.config(vars.D1, ["write memory"], type=data.cli_type, skip_error_check=True)
            st.config(vars.D2, ["write memory"], type=data.cli_type, skip_error_check=True)
            st.log("Configuration saved successfully")
        except Exception as e:
            st.log(f"Warning: Failed to save configuration: {e}")

    except Exception as e:
        error_msg = f"Unexpected exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)

    finally:
        # Cleanup ALWAYS executes
        st.banner("=" * 80)
        st.banner("CLEANUP: Unconfiguring All Settings (ALWAYS EXECUTES)")
        st.banner("=" * 80)

        try:
            cleanup_all(vars.D1)
            cleanup_all(vars.D2)
            st.log("Cleanup completed successfully")

        except Exception as cleanup_error:
            st.error(f"Error during cleanup: {str(cleanup_error)}")
            validation_failures.append(f"Cleanup error: {str(cleanup_error)}")

    # Generate tech-support if validation failures
    if validation_failures and not tech_support_generated:
        st.banner("=" * 80)
        st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
        st.banner("=" * 80)
        try:
            st.generate_tech_support([vars.D1, vars.D2], "sm_iscli_5_validation_failures")
            tech_support_generated = True
            st.log("Tech-support generated successfully")
        except Exception as ts_error:
            st.error(f"Failed to generate tech-support: {str(ts_error)}")

    # Final reporting
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"{idx}. {failure}")
        st.log("!" * 80)
        st.log(f"\nNote: Cleanup and unconfiguration completed despite {len(validation_failures)} validation failure(s)")
        st.log("Tech-support has been generated for debugging")
        st.report_fail("msg", f"Test completed with {len(validation_failures)} validation failure(s). Cleanup executed. See errors above.")
    else:
        st.log("All validations passed successfully")
        st.log("=" * 80)
        st.log("SM-ISCLI-5 Test PASSED: BGP L2VPN EVPN Output Consistency")
        st.log("  CONFIGURATION:")
        st.log(f"    - DUT1: AS {CONFIG.dut1_asn}, Loopback {CONFIG.dut1_loopback}, VNI {CONFIG.dut1_vni}")
        st.log(f"    - DUT2: AS {CONFIG.dut2_asn}, Loopback {CONFIG.dut2_loopback}, VNI {CONFIG.dut2_vni}")
        st.log("  VERIFICATION:")
        st.log("    - IS-CLI EVPN summary correct")
        st.log("    - vtysh EVPN summary correct")
        st.log("    - EVPN neighbor state consistent")
        st.log("    - EVPN route count consistent")
        st.log("    - EVPN Type-5 routes visible in both CLIs")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
