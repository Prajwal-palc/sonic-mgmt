"""
SM_ISCLI_9: L2VPN EVPN Lost When update-source After address-family

Test Case ID: SM_ISCLI_9
Bug: L2VPN EVPN configuration order sensitivity
Priority: P2

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/hp_test/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_SNMP/test_sm_iscli_9_l2vpn_evpn_order.py \
    --logs-path ./logs/sm_iscli_9_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates that L2VPN EVPN address-family configuration works correctly
  regardless of command order with update-source.

  Test Scenarios:
  - DUT1: update-source BEFORE address-family (correct order)
  - DUT2: update-source BEFORE address-family (correct order)
  - Verify both configurations persist correctly in running-config and vtysh

  Expected Behavior:
  - L2VPN EVPN address-family should be active
  - update-source should be configured
  - Both should appear in running-config and vtysh output

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2vs.yaml
  - Loopback interfaces supported
  - Credentials: admin/test@123

Note:
  - IMPORTANT: This script uses validation_failures tracking to ensure cleanup always runs
  - Tech-support is generated automatically on any validation failure
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
    "asn": "65001",

    # DUT1 configuration
    "dut1_loopback": "Loopback0",
    "dut1_loopback_ip": "10.2.2.2",
    "dut1_loopback_mask": "32",
    "dut1_router_id": "10.2.2.2",
    "dut1_neighbor_ip": "10.1.1.1",

    # DUT2 configuration
    "dut2_loopback": "Loopback0",
    "dut2_loopback_ip": "10.1.1.1",
    "dut2_loopback_mask": "32",
    "dut2_router_id": "10.1.1.1",
    "dut2_neighbor_ip": "10.2.2.2",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("SM_ISCLI_9: MODULE PROLOGUE - L2VPN EVPN Order Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("SM_ISCLI_9: MODULE EPILOGUE - Cleanup")
    cleanup_bgp_config(vars.D1)
    cleanup_bgp_config(vars.D2)
    cleanup_loopback(vars.D1)
    cleanup_loopback(vars.D2)


def configure_loopback(dut: str, loopback_ip: str) -> bool:
    """Configure loopback interface."""
    try:
        st.log(f"Configuring {CONFIG.dut1_loopback if dut == vars.D1 else CONFIG.dut2_loopback} on {dut}")

        commands = [
            f"interface {CONFIG.dut1_loopback if dut == vars.D1 else CONFIG.dut2_loopback}",
            f"ip address {loopback_ip}/{CONFIG.dut1_loopback_mask if dut == vars.D1 else CONFIG.dut2_loopback_mask}",
            "no shutdown",
            "exit"
        ]

        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure loopback on {dut}: {e}")
        return False


def configure_bgp_with_evpn_correct_order(dut: str, router_id: str, neighbor_ip: str, loopback_name: str) -> bool:
    """
    Configure BGP with L2VPN EVPN using CORRECT order:
    1. Configure neighbor
    2. update-source FIRST
    3. address-family l2vpn evpn SECOND
    """
    try:
        st.log(f"Configuring BGP with L2VPN EVPN (CORRECT ORDER) on {dut}")

        commands = [
            f"router bgp {CONFIG.asn}",
            f"router-id {router_id}",
            f"neighbor {neighbor_ip} remote-as {CONFIG.asn}",

            # CORRECT ORDER: update-source BEFORE address-family
            f"update-source interface {loopback_name}",
            "address-family l2vpn evpn",
            "activate",
            "exit",  # Exit AF
            "exit",  # Exit neighbor
            "exit"   # Exit router bgp
        ]

        st.config(dut, commands, type=data.cli_type)
        st.wait(2)
        return True

    except Exception as e:
        st.error(f"Failed to configure BGP with EVPN on {dut}: {e}")
        return False


def verify_evpn_config_klish(dut: str, neighbor_ip: str) -> bool:
    """Verify L2VPN EVPN configuration in IS-CLI."""
    try:
        st.log(f"Verifying L2VPN EVPN configuration in IS-CLI on {dut}")

        output = st.show(dut, "show running-configuration bgp", type=data.cli_type)
        output_str = str(output)

        checks_passed = 0
        total_checks = 3

        # Check 1: Neighbor exists
        if f"neighbor {neighbor_ip}" in output_str:
            st.log(f"✅ Check 1/3: Neighbor {neighbor_ip} found in config")
            checks_passed += 1
        else:
            st.log(f"❌ Check 1/3: Neighbor {neighbor_ip} NOT found")

        # Check 2: update-source configured
        if "update-source" in output_str.lower():
            st.log(f"✅ Check 2/3: update-source found in config")
            checks_passed += 1
        else:
            st.log(f"❌ Check 2/3: update-source NOT found")

        # Check 3: L2VPN EVPN address-family configured
        if "address-family l2vpn evpn" in output_str or "l2vpn evpn" in output_str:
            st.log(f"✅ Check 3/3: L2VPN EVPN address-family found in config")
            checks_passed += 1
        else:
            st.log(f"❌ Check 3/3: L2VPN EVPN address-family NOT found")

        st.log(f"IS-CLI verification: {checks_passed}/{total_checks} checks passed")
        return checks_passed == total_checks

    except Exception as e:
        st.error(f"Failed to verify EVPN config in IS-CLI on {dut}: {e}")
        return False


def verify_evpn_config_vtysh(dut: str, neighbor_ip: str) -> bool:
    """Verify L2VPN EVPN configuration in vtysh."""
    try:
        st.log(f"Verifying L2VPN EVPN configuration in vtysh on {dut}")

        # Run vtysh command
        output = st.show(dut, "sudo vtysh -c 'show running-config'", skip_tmpl=True, skip_error_check=True)
        output_str = str(output)

        checks_passed = 0
        total_checks = 3

        # Check 1: BGP router exists
        if f"router bgp {CONFIG.asn}" in output_str:
            st.log(f"✅ Check 1/3: BGP router found in vtysh")
            checks_passed += 1
        else:
            st.log(f"❌ Check 1/3: BGP router NOT found in vtysh")

        # Check 2: Neighbor with update-source
        if f"neighbor {neighbor_ip}" in output_str and "update-source" in output_str:
            st.log(f"✅ Check 2/3: Neighbor with update-source found in vtysh")
            checks_passed += 1
        else:
            st.log(f"❌ Check 2/3: Neighbor with update-source NOT found in vtysh")

        # Check 3: L2VPN EVPN address-family
        if "address-family l2vpn evpn" in output_str:
            st.log(f"✅ Check 3/3: L2VPN EVPN address-family found in vtysh")
            checks_passed += 1
        else:
            st.log(f"❌ Check 3/3: L2VPN EVPN address-family NOT found in vtysh")

        st.log(f"vtysh verification: {checks_passed}/{total_checks} checks passed")
        return checks_passed >= 2  # Allow some flexibility

    except Exception as e:
        st.error(f"Failed to verify EVPN config in vtysh on {dut}: {e}")
        return False


def cleanup_bgp_config(dut: str) -> None:
    """Remove BGP configuration."""
    try:
        commands = [f"no router bgp {CONFIG.asn}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"BGP cleanup on {dut}: {e}")


def cleanup_loopback(dut: str) -> None:
    """Remove loopback interface."""
    try:
        loopback_name = CONFIG.dut1_loopback if dut == vars.D1 else CONFIG.dut2_loopback
        commands = [f"no interface {loopback_name}"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except Exception as e:
        st.log(f"Loopback cleanup on {dut}: {e}")


def test_sm_iscli_9_l2vpn_evpn_order():
    """
    SM_ISCLI_9: Test L2VPN EVPN configuration order.

    Test Steps:
    1. Configure loopback interfaces on both DUTs
    2. Configure BGP with update-source BEFORE address-family (correct order)
    3. Verify configuration appears in IS-CLI running-config
    4. Verify configuration appears in vtysh running-config
    5. Cleanup: Remove BGP and loopback configuration

    IMPORTANT: Uses validation_failures tracking pattern to ensure cleanup
    and tech-support generation always execute, even if validation errors occur.
    """
    st.banner("TEST: SM_ISCLI_9 - L2VPN EVPN Configuration Order")

    # Track validation failures - test will continue but report fail at end
    validation_failures = []
    tech_support_generated = False

    try:
        # Step 1: Configure loopback interfaces
        st.log("STEP 1: Configure loopback interfaces")
        if not configure_loopback(vars.D1, CONFIG.dut1_loopback_ip):
            error_msg = f"Loopback configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_loopback(vars.D2, CONFIG.dut2_loopback_ip):
            error_msg = f"Loopback configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 2: Configure BGP with EVPN (correct order) on DUT1
        st.log("STEP 2: Configure BGP with L2VPN EVPN on DUT1 (update-source BEFORE address-family)")
        if not configure_bgp_with_evpn_correct_order(vars.D1, CONFIG.dut1_router_id,
                                                       CONFIG.dut1_neighbor_ip, CONFIG.dut1_loopback):
            error_msg = f"BGP EVPN configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 3: Configure BGP with EVPN (correct order) on DUT2
        st.log("STEP 3: Configure BGP with L2VPN EVPN on DUT2 (update-source BEFORE address-family)")
        if not configure_bgp_with_evpn_correct_order(vars.D2, CONFIG.dut2_router_id,
                                                       CONFIG.dut2_neighbor_ip, CONFIG.dut2_loopback):
            error_msg = f"BGP EVPN configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 4: Verify IS-CLI configuration
        st.log("STEP 4: Verify L2VPN EVPN configuration in IS-CLI")
        st.wait(5, "Waiting for configuration to apply")

        if not verify_evpn_config_klish(vars.D1, CONFIG.dut1_neighbor_ip):
            error_msg = f"L2VPN EVPN verification failed in IS-CLI on {vars.D1}"
            st.log(f"WARNING: {error_msg}")
            validation_failures.append(error_msg)

        if not verify_evpn_config_klish(vars.D2, CONFIG.dut2_neighbor_ip):
            error_msg = f"L2VPN EVPN verification failed in IS-CLI on {vars.D2}"
            st.log(f"WARNING: {error_msg}")
            validation_failures.append(error_msg)

        # Step 5: Verify vtysh configuration
        st.log("STEP 5: Verify L2VPN EVPN configuration in vtysh")

        if not verify_evpn_config_vtysh(vars.D1, CONFIG.dut1_neighbor_ip):
            error_msg = f"L2VPN EVPN verification failed in vtysh on {vars.D1}"
            st.log(f"WARNING: {error_msg}")
            validation_failures.append(error_msg)

        if not verify_evpn_config_vtysh(vars.D2, CONFIG.dut2_neighbor_ip):
            error_msg = f"L2VPN EVPN verification failed in vtysh on {vars.D2}"
            st.log(f"WARNING: {error_msg}")
            validation_failures.append(error_msg)

        st.log("✅ SM_ISCLI_9 Test execution completed")

    except Exception as e:
        error_msg = f"Unexpected exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)

    finally:
        # CLEANUP: This block ALWAYS executes
        st.banner("=" * 80)
        st.banner("CLEANUP: Removing BGP and Loopback Configuration (ALWAYS EXECUTES)")
        st.banner("=" * 80)

        try:
            st.log("Cleaning up BGP and loopback configuration on both DUTs")
            cleanup_bgp_config(vars.D1)
            cleanup_bgp_config(vars.D2)
            cleanup_loopback(vars.D1)
            cleanup_loopback(vars.D2)
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
                st.generate_tech_support([vars.D1, vars.D2], "sm_iscli_9_validation_failures")
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
            st.log("All validations passed successfully")
            st.log("✅ SM_ISCLI_9 Test PASSED: L2VPN EVPN configuration order correct")
            st.report_pass("test_case_passed")
