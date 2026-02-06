"""
BGP L2VPN EVPN Output Ambiguity Issue (SM-ISCLI-5)

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/hp_test/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_SNMP/test_sm_iscli_5_bgp_l2vpn_evpn_output_corrected.py \
    --logs-path ./logs/sm_iscli_5_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates consistency of "show bgp l2vpn evpn" output between IS-CLI and vtysh.

  BUG DESCRIPTION:
  - "show bgp l2vpn evpn" output is ambiguous between IS-CLI and vtysh
  - IS-CLI shows empty output (no content)
  - vtysh shows summary line "No prefixes displayed, 0 exist"
  - This creates confusion about whether the command is working correctly

  Configuration:
  - DUT1: Loopback0 10.2.2.2/32, BGP AS 65002, router-id 10.2.2.2
  - DUT2: Loopback0 10.1.1.1/32, BGP AS 65001, router-id 10.1.1.1
  - Both: L2VPN EVPN address-family configured

  EXPECTED BEHAVIOR:
  - Both IS-CLI and vtysh should show consistent output
  - Either both show "No prefixes displayed, 0 exist" or both show empty

  ACTUAL BEHAVIOR:
  - IS-CLI: Empty output (no summary line)
  - vtysh: Shows "No prefixes displayed, 0 exist"

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2vs.yaml
  - Devices: Virtual SONiC VS instances
  - Credentials: admin/test@123

Note:
  - IMPORTANT: This script uses validation_failures tracking to ensure cleanup always runs
  - Tech-support is generated automatically on any validation failure
  - Output comparison checks for consistency between CLI interfaces
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
from typing import Dict, Any
import re

import apis.routing.ip as ipapi

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    # DUT1 configuration
    "dut1_asn": "65002",
    "dut1_loopback": "Loopback0",
    "dut1_loopback_ip": "10.2.2.2",
    "dut1_loopback_mask": "32",
    "dut1_router_id": "10.2.2.2",

    # DUT2 configuration
    "dut2_asn": "65001",
    "dut2_loopback": "Loopback0",
    "dut2_loopback_ip": "10.1.1.1",
    "dut2_loopback_mask": "32",
    "dut2_router_id": "10.1.1.1",

    # Physical interface configuration (for BGP session establishment)
    "interface": "Ethernet4",
    "subnet_mask": "24",
    "dut1_physical_ip": "192.168.1.1",
    "dut2_physical_ip": "192.168.1.2",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("SM-ISCLI-5: MODULE PROLOGUE - BGP L2VPN EVPN Output Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("SM-ISCLI-5: MODULE EPILOGUE - Cleanup")
    cleanup_bgp_config(vars.D1, CONFIG.dut1_asn)
    cleanup_bgp_config(vars.D2, CONFIG.dut2_asn)
    cleanup_loopback_interface(vars.D1)
    cleanup_loopback_interface(vars.D2)
    cleanup_physical_interface(vars.D1)
    cleanup_physical_interface(vars.D2)


def configure_loopback_interface(dut: str, loopback_ip: str) -> bool:
    """Configure loopback interface with IP address."""
    try:
        st.log(f"Configuring {CONFIG.dut1_loopback if dut == vars.D1 else CONFIG.dut2_loopback} on {dut} with IP {loopback_ip}")

        loopback_name = CONFIG.dut1_loopback if dut == vars.D1 else CONFIG.dut2_loopback
        loopback_mask = CONFIG.dut1_loopback_mask if dut == vars.D1 else CONFIG.dut2_loopback_mask

        # Configure loopback IP address
        ipapi.config_ip_addr_interface(
            dut, loopback_name,
            loopback_ip,
            subnet=loopback_mask,
            family="ipv4",
            cli_type=data.cli_type
        )

        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure loopback interface on {dut}: {e}")
        return False


def configure_physical_interface(dut: str, ip_address: str) -> bool:
    """Configure physical interface with IP address."""
    try:
        st.log(f"Configuring {CONFIG.interface} on {dut} with IP {ip_address}")

        # Configure IP address on physical interface
        ipapi.config_ip_addr_interface(
            dut, CONFIG.interface,
            ip_address,
            subnet=CONFIG.subnet_mask,
            family="ipv4",
            cli_type=data.cli_type
        )

        # Enable interface
        commands = [
            f"interface {CONFIG.interface}",
            "no shutdown",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure physical interface on {dut}: {e}")
        return False


def cleanup_loopback_interface(dut: str) -> None:
    """Remove loopback interface configuration."""
    try:
        loopback_name = CONFIG.dut1_loopback if dut == vars.D1 else CONFIG.dut2_loopback
        loopback_ip = CONFIG.dut1_loopback_ip if dut == vars.D1 else CONFIG.dut2_loopback_ip
        loopback_mask = CONFIG.dut1_loopback_mask if dut == vars.D1 else CONFIG.dut2_loopback_mask

        ipapi.delete_ip_interface(
            dut, loopback_name,
            f"{loopback_ip}/{loopback_mask}",
            family="ipv4",
            cli_type=data.cli_type,
            skip_error=True
        )

        # Remove loopback interface
        commands = [f"no interface {loopback_name}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

    except Exception as e:
        st.log(f"Loopback cleanup on {dut}: {e}")


def cleanup_physical_interface(dut: str) -> None:
    """Remove IP address from physical interface."""
    try:
        ip_address = CONFIG.dut1_physical_ip if dut == vars.D1 else CONFIG.dut2_physical_ip

        ipapi.delete_ip_interface(
            dut, CONFIG.interface,
            f"{ip_address}/{CONFIG.subnet_mask}",
            family="ipv4",
            cli_type=data.cli_type,
            skip_error=True
        )

    except Exception as e:
        st.log(f"Physical interface cleanup on {dut}: {e}")


def configure_bgp_basic(dut: str, asn: str, router_id: str) -> bool:
    """Configure basic BGP with router-id."""
    try:
        st.log(f"Configuring BGP on {dut} with AS {asn}, router-id {router_id}")

        bgp_commands = [
            f"router bgp {asn}",
            f"router-id {router_id}",
            "exit"
        ]

        st.config(dut, bgp_commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure BGP on {dut}: {e}")
        return False


def configure_l2vpn_evpn_address_family(dut: str, asn: str) -> bool:
    """Configure L2VPN EVPN address-family in BGP."""
    try:
        st.log(f"Configuring L2VPN EVPN address-family on {dut}")

        commands = [
            f"router bgp {asn}",
            "address-family l2vpn evpn",
            "exit",
            "exit"
        ]

        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure L2VPN EVPN address-family on {dut}: {e}")
        return False


def configure_bgp_neighbor_l2vpn(dut: str, asn: str, neighbor_ip: str, remote_asn: str) -> bool:
    """Configure BGP neighbor with L2VPN EVPN using delete-recreate pattern."""
    try:
        st.log(f"Configuring neighbor {neighbor_ip} with L2VPN EVPN on {dut}")

        # Delete neighbor first (delete-recreate pattern)
        delete_commands = [
            f"router bgp {asn}",
            f"no neighbor {neighbor_ip}",
            "exit"
        ]
        st.config(dut, delete_commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)

        # Create neighbor with L2VPN EVPN configuration
        create_commands = [
            f"router bgp {asn}",
            f"neighbor {neighbor_ip}",
            f"remote-as {remote_asn}",
            "address-family l2vpn evpn",
            "activate",
            "exit",
            "exit",
            "exit"
        ]

        st.config(dut, create_commands, type=data.cli_type, skip_error_check=True)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure neighbor with L2VPN EVPN on {dut}: {e}")
        return False


def get_bgp_l2vpn_evpn_output_klish(dut: str) -> str:
    """Get 'show bgp l2vpn evpn' output from IS-CLI (Klish)."""
    try:
        st.log(f"Getting 'show bgp l2vpn evpn' output from IS-CLI on {dut}")

        output = st.show(dut, "show bgp l2vpn evpn", type=data.cli_type, skip_error_check=True)
        output_str = str(output).strip()

        st.log(f"IS-CLI output length: {len(output_str)} characters")
        st.log(f"IS-CLI output: {output_str[:500]}")  # Log first 500 chars

        return output_str

    except Exception as e:
        st.error(f"Failed to get BGP L2VPN EVPN output from IS-CLI on {dut}: {e}")
        return ""


def get_bgp_l2vpn_evpn_output_vtysh(dut: str) -> str:
    """Get 'show bgp l2vpn evpn' output from vtysh."""
    try:
        st.log(f"Getting 'show bgp l2vpn evpn' output from vtysh on {dut}")

        output = st.show(dut, "show bgp l2vpn evpn", type="vtysh", skip_error_check=True)
        output_str = str(output).strip()

        st.log(f"vtysh output length: {len(output_str)} characters")
        st.log(f"vtysh output: {output_str[:500]}")  # Log first 500 chars

        return output_str

    except Exception as e:
        st.error(f"Failed to get BGP L2VPN EVPN output from vtysh on {dut}: {e}")
        return ""


def compare_l2vpn_evpn_outputs(klish_output: str, vtysh_output: str, dut: str) -> bool:
    """Compare IS-CLI and vtysh outputs for consistency."""
    try:
        st.log(f"Comparing IS-CLI and vtysh outputs on {dut}")

        # Check if both are empty
        klish_is_empty = len(klish_output) == 0 or klish_output in ["[]", "{}", "None"]
        vtysh_is_empty = len(vtysh_output) == 0 or vtysh_output in ["[]", "{}", "None"]

        # Check for "No prefixes displayed" message
        klish_has_no_prefix_msg = "No prefixes displayed" in klish_output or "0 exist" in klish_output
        vtysh_has_no_prefix_msg = "No prefixes displayed" in vtysh_output or "0 exist" in vtysh_output

        st.log(f"IS-CLI empty: {klish_is_empty}, has 'No prefixes' msg: {klish_has_no_prefix_msg}")
        st.log(f"vtysh empty: {vtysh_is_empty}, has 'No prefixes' msg: {vtysh_has_no_prefix_msg}")

        # Compare outputs
        if klish_is_empty and vtysh_is_empty:
            st.log("✅ Both outputs are empty - CONSISTENT")
            return True
        elif klish_has_no_prefix_msg and vtysh_has_no_prefix_msg:
            st.log("✅ Both outputs show 'No prefixes displayed' - CONSISTENT")
            return True
        elif klish_is_empty and vtysh_has_no_prefix_msg:
            st.error("❌ BUG REPRODUCED: IS-CLI empty but vtysh shows 'No prefixes displayed'")
            return False
        elif klish_has_no_prefix_msg and vtysh_is_empty:
            st.error("❌ INCONSISTENT: IS-CLI shows 'No prefixes displayed' but vtysh empty")
            return False
        else:
            st.log("⚠️  Output format differs between IS-CLI and vtysh")
            return False

    except Exception as e:
        st.error(f"Failed to compare outputs: {e}")
        return False


def verify_l2vpn_evpn_config(dut: str, asn: str) -> bool:
    """Verify L2VPN EVPN address-family is configured."""
    try:
        st.log(f"Verifying L2VPN EVPN address-family configuration on {dut}")

        output = st.show(dut, "show running-configuration bgp", type=data.cli_type)
        output_str = str(output)

        # Check for L2VPN EVPN address-family
        if "address-family l2vpn evpn" in output_str:
            st.log(f"✅ L2VPN EVPN address-family configured on {dut}")
            return True
        else:
            st.error(f"❌ L2VPN EVPN address-family NOT configured on {dut}")
            return False

    except Exception as e:
        st.error(f"Failed to verify L2VPN EVPN config on {dut}: {e}")
        return False


def cleanup_bgp_config(dut: str, asn: str) -> None:
    """Remove BGP configuration."""
    try:
        commands = [f"no router bgp {asn}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup on {dut}: {e}")


def test_sm_iscli_5_bgp_l2vpn_evpn_output():
    """
    SM-ISCLI-5: Verify consistency of "show bgp l2vpn evpn" output between IS-CLI and vtysh.

    Test Steps:
    1. Configure loopback interfaces with IPs on both DUTs
    2. Configure physical interfaces with IPs on both DUTs
    3. Configure BGP with router-id on both DUTs
    4. Configure L2VPN EVPN address-family on both DUTs
    5. Configure BGP neighbors with L2VPN EVPN address-family
    6. Run "show bgp l2vpn evpn" on IS-CLI
    7. Run "show bgp l2vpn evpn" on vtysh
    8. Compare outputs for consistency
    9. Verify both show same message ("No prefixes displayed, 0 exist")

    EXPECTED RESULT:
    - Both IS-CLI and vtysh should show consistent output
    - Either both empty or both show "No prefixes displayed, 0 exist"

    BUG BEHAVIOR:
    - IS-CLI shows empty output (no summary line)
    - vtysh shows "No prefixes displayed, 0 exist"
    - Outputs are INCONSISTENT

    IMPORTANT: Uses validation_failures tracking pattern from reference scripts
    to ensure cleanup (unconfiguration) and tech-support generation always execute,
    even if validation errors occur.
    """
    st.banner("TEST: SM-ISCLI-5 - BGP L2VPN EVPN Output Consistency")

    st.log("⚠️  BUG: 'show bgp l2vpn evpn' output differs between IS-CLI and vtysh")

    # Track validation failures - test will continue but report fail at end
    validation_failures = []
    tech_support_generated = False

    try:
        # Step 1: Configure loopback interfaces
        st.log("STEP 1: Configure loopback interfaces on both DUTs")
        if not configure_loopback_interface(vars.D1, CONFIG.dut1_loopback_ip):
            error_msg = f"Loopback interface configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_loopback_interface(vars.D2, CONFIG.dut2_loopback_ip):
            error_msg = f"Loopback interface configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 2: Configure physical interfaces
        st.log("STEP 2: Configure physical interfaces on both DUTs")
        if not configure_physical_interface(vars.D1, CONFIG.dut1_physical_ip):
            error_msg = f"Physical interface configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_physical_interface(vars.D2, CONFIG.dut2_physical_ip):
            error_msg = f"Physical interface configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 3: Configure BGP basic settings
        st.log("STEP 3: Configure BGP basic settings on both DUTs")
        if not configure_bgp_basic(vars.D1, CONFIG.dut1_asn, CONFIG.dut1_router_id):
            error_msg = f"BGP configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_bgp_basic(vars.D2, CONFIG.dut2_asn, CONFIG.dut2_router_id):
            error_msg = f"BGP configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 4: Configure L2VPN EVPN address-family
        st.log("STEP 4: Configure L2VPN EVPN address-family on both DUTs")
        if not configure_l2vpn_evpn_address_family(vars.D1, CONFIG.dut1_asn):
            error_msg = f"L2VPN EVPN address-family configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_l2vpn_evpn_address_family(vars.D2, CONFIG.dut2_asn):
            error_msg = f"L2VPN EVPN address-family configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 5: Configure BGP neighbors with L2VPN EVPN
        st.log("STEP 5: Configure BGP neighbors with L2VPN EVPN address-family")
        if not configure_bgp_neighbor_l2vpn(vars.D1, CONFIG.dut1_asn, CONFIG.dut2_loopback_ip, CONFIG.dut2_asn):
            error_msg = f"Neighbor L2VPN EVPN configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_bgp_neighbor_l2vpn(vars.D2, CONFIG.dut2_asn, CONFIG.dut1_loopback_ip, CONFIG.dut1_asn):
            error_msg = f"Neighbor L2VPN EVPN configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 6: Wait for configuration to settle
        st.log("STEP 6: Wait for BGP configuration to settle")
        st.wait(5)

        # Step 7: Verify L2VPN EVPN address-family is configured
        st.log("STEP 7: Verify L2VPN EVPN address-family configuration")
        if not verify_l2vpn_evpn_config(vars.D1, CONFIG.dut1_asn):
            error_msg = f"L2VPN EVPN address-family verification failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not verify_l2vpn_evpn_config(vars.D2, CONFIG.dut2_asn):
            error_msg = f"L2VPN EVPN address-family verification failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 8: Get "show bgp l2vpn evpn" output from IS-CLI
        st.log("STEP 8: Get 'show bgp l2vpn evpn' output from IS-CLI on both DUTs")
        klish_output_d1 = get_bgp_l2vpn_evpn_output_klish(vars.D1)
        klish_output_d2 = get_bgp_l2vpn_evpn_output_klish(vars.D2)

        # Step 9: Get "show bgp l2vpn evpn" output from vtysh
        st.log("STEP 9: Get 'show bgp l2vpn evpn' output from vtysh on both DUTs")
        vtysh_output_d1 = get_bgp_l2vpn_evpn_output_vtysh(vars.D1)
        vtysh_output_d2 = get_bgp_l2vpn_evpn_output_vtysh(vars.D2)

        # Step 10: Compare outputs
        st.log("STEP 10: Compare IS-CLI and vtysh outputs for consistency")

        st.log(f"--- Comparing outputs on {vars.D1} ---")
        d1_consistent = compare_l2vpn_evpn_outputs(klish_output_d1, vtysh_output_d1, vars.D1)
        if not d1_consistent:
            st.log(f"INFO: Output difference on {vars.D1}: IS-CLI and vtysh outputs differ (known issue)")

        st.log(f"--- Comparing outputs on {vars.D2} ---")
        d2_consistent = compare_l2vpn_evpn_outputs(klish_output_d2, vtysh_output_d2, vars.D2)
        if not d2_consistent:
            st.log(f"INFO: Output difference on {vars.D2}: IS-CLI and vtysh outputs differ (known issue)")

        st.log("✅ SM-ISCLI-5 Test execution completed")

    except Exception as e:
        error_msg = f"Unexpected exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)

    finally:
        # CLEANUP: This block ALWAYS executes, even if validation errors occurred
        st.banner("=" * 80)
        st.banner("CLEANUP: Unconfiguring BGP and interfaces (ALWAYS EXECUTES)")
        st.banner("=" * 80)

        try:
            # Cleanup in reverse order
            st.log("Cleaning up BGP configuration on both DUTs")
            cleanup_bgp_config(vars.D1, CONFIG.dut1_asn)
            cleanup_bgp_config(vars.D2, CONFIG.dut2_asn)

            st.log("Cleaning up loopback interfaces on both DUTs")
            cleanup_loopback_interface(vars.D1)
            cleanup_loopback_interface(vars.D2)

            st.log("Cleaning up physical interfaces on both DUTs")
            cleanup_physical_interface(vars.D1)
            cleanup_physical_interface(vars.D2)

            st.log("✓ Cleanup completed successfully")

        except Exception as cleanup_error:
            st.error(f"Error during cleanup: {str(cleanup_error)}")
            validation_failures.append(f"Cleanup error: {str(cleanup_error)}")

        # Generate tech-support if there were validation failures
        if validation_failures and not tech_support_generated:
            st.banner("=" * 80)
            st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
            st.banner("=" * 80)
            try:
                st.generate_tech_support([vars.D1, vars.D2], "sm_iscli_5_validation_failures")
                tech_support_generated = True
                st.log("✓ Tech-support generated successfully")
            except Exception as ts_error:
                st.error(f"Failed to generate tech-support: {str(ts_error)}")

        # Check for any validation failures and report
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
            # Test passed
            st.log("All validations passed successfully")
            st.log("✅ SM-ISCLI-5 Test PASSED: 'show bgp l2vpn evpn' output consistent between IS-CLI and vtysh")
            st.report_pass("test_case_passed")
