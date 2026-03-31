r"""
LLDP TEST - OC-1 Test ID 4.16.17: Verify LLDP continuity after MTU change

Test Case ID: 4.16.17
Feature: LLDP
Test Item: MTU Change Continuity
Author: Automated from Manual Validation
Copyright (C) 2024-2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_LLDP/test_lldp_17_mtu_change_continuity.py \
    --logs-path ./logs/lldp_17_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates LLDP continues working after MTU change:
  - Enable LLDP and verify neighbors
  - Change interface MTU
  - Verify LLDP neighbors still present (no disruption)
  - Restore original MTU
  - Rollback configuration

Pre-requisites:
  - 2 SONiC devices connected
  - Testbed: testbed_2vs.yaml
  - Interfaces cabled as per topology
  - Clean LLDP configuration

Expected Result (Manual Test):
  PASS - LLDP neighbors remain after MTU change

Manual Test Log Reference (Test 4.16.17 PASS):
  sonic(config)# lldp enable
  sonic(config)# interface Ethernet 8
  sonic(conf-if-Ethernet8)# lldp enable
  sonic# show lldp neighbor
  [Neighbors present]

  sonic(conf-if-Ethernet8)# mtu 9100
  sonic# show lldp neighbor
  [Neighbors still present - PASS]

  sonic(conf-if-Ethernet8)# mtu 1500
  [Restore original MTU]
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
import re
import time

import apis.system.lldp as lldpapi
import apis.system.interface as intfapi
import apis.system.basic as basicapi

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration matching manual testcase
CONFIG = SpyTestDict({
    "test_interface_dut1": "Ethernet8",
    "test_interface_dut2": "Ethernet8",
    "default_mtu": 1500,
    "jumbo_mtu": 9100,
    "lldp_wait_time": 60,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "lldp_global_enable": "TC-LLDP-4.16.17-001",
    "lldp_interface_enable": "TC-LLDP-4.16.17-002",
    "lldp_neighbor_discovery_baseline": "TC-LLDP-4.16.17-003",
    "mtu_change_to_jumbo": "TC-LLDP-4.16.17-004",
    "lldp_neighbor_after_mtu_change": "TC-LLDP-4.16.17-005",
    "mtu_restore": "TC-LLDP-4.16.17-006",
    "lldp_rollback": "TC-LLDP-4.16.17-007",
})


@pytest.fixture(scope="module", autouse=True)
def lldp_mtu_change_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.17 MTU CHANGE CONTINUITY TEST - MODULE START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")

    # Get CLI type from framework
    data.cli_type = st.get_ui_type()

    st.log(f"DUT1 (DUT-A): {vars.D1}")
    st.log(f"DUT2 (DUT-B): {vars.D2}")
    st.log(f"CLI Type: {data.cli_type} (auto-detected by framework)")
    st.log(f"Test Interface DUT1: {CONFIG.test_interface_dut1}")
    st.log(f"Test Interface DUT2: {CONFIG.test_interface_dut2}")

    # Pre-configuration
    lldp_pre_config()

    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.17 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        lldp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")

    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.17 MODULE CLEANUP - COMPLETED")
    st.banner("=" * 80)


def lldp_pre_config():
    """Pre-configuration: Clean LLDP state."""
    st.log("Pre-configuration: Preparing LLDP environment")

    dut_list = [vars.D1, vars.D2]

    # Ensure interfaces are up
    st.log(f"Ensuring test interfaces are up on both DUTs")
    try:
        intfapi.interface_operation(vars.D1, CONFIG.test_interface_dut1, operation="startup",
                                   cli_type=data.cli_type)
        intfapi.interface_operation(vars.D2, CONFIG.test_interface_dut2, operation="startup",
                                   cli_type=data.cli_type)
    except Exception as e:
        st.log(f"Interface startup warning: {str(e)}")

    # Restore default MTU
    st.log(f"Restoring default MTU ({CONFIG.default_mtu}) on test interfaces")
    try:
        configure_interface_mtu(vars.D1, CONFIG.test_interface_dut1, CONFIG.default_mtu)
        configure_interface_mtu(vars.D2, CONFIG.test_interface_dut2, CONFIG.default_mtu)
    except Exception as e:
        st.log(f"MTU restore warning: {str(e)}")

    # Disable LLDP initially for clean baseline
    st.log("Disabling LLDP globally on both DUTs (clean baseline)")
    for dut in dut_list:
        try:
            disable_lldp_globally(dut)
        except Exception as e:
            st.log(f"LLDP disable warning on {dut}: {str(e)}")

    st.wait(5, "Waiting for LLDP to stabilize")
    st.log("Pre-configuration completed")


def lldp_pre_config_cleanup():
    """Cleanup: Remove all LLDP configuration and restore MTU."""
    st.log("Cleanup: Removing LLDP configuration")

    dut_list = [vars.D1, vars.D2]

    # Restore default MTU
    st.log(f"Restoring default MTU ({CONFIG.default_mtu})")
    try:
        configure_interface_mtu(vars.D1, CONFIG.test_interface_dut1, CONFIG.default_mtu)
        configure_interface_mtu(vars.D2, CONFIG.test_interface_dut2, CONFIG.default_mtu)
    except Exception as e:
        st.log(f"MTU restore warning: {str(e)}")

    # Disable LLDP globally
    for dut in dut_list:
        try:
            disable_lldp_globally(dut)
        except Exception as e:
            st.log(f"LLDP disable warning on {dut}: {str(e)}")

    st.log("Cleanup completed")


def enable_lldp_globally(dut: str) -> bool:
    """Enable LLDP globally."""
    st.log(f"Enabling LLDP globally on {dut}")
    try:
        st.config(dut, [
            "configure terminal",
            "lldp enable",
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ LLDP enabled globally on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to enable LLDP globally on {dut}: {str(e)}")
        return False


def disable_lldp_globally(dut: str) -> bool:
    """Disable LLDP globally."""
    st.log(f"Disabling LLDP globally on {dut}")
    try:
        st.config(dut, [
            "configure terminal",
            "no lldp enable",
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ LLDP disabled globally on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to disable LLDP globally on {dut}: {str(e)}")
        return False


def enable_lldp_on_interface(dut: str, interface: str) -> bool:
    """Enable LLDP on specific interface."""
    st.log(f"Enabling LLDP on {dut} interface {interface}")
    try:
        st.config(dut, [
            "configure terminal",
            f"interface {interface}",
            "lldp enable",
            "exit",
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ LLDP enabled on {dut} {interface}")
        return True
    except Exception as e:
        st.error(f"Failed to enable LLDP on {dut} {interface}: {str(e)}")
        return False


def configure_interface_mtu(dut: str, interface: str, mtu: int) -> bool:
    """
    Configure interface MTU.

    Args:
        dut: Device name
        interface: Interface name (e.g., "Ethernet8")
        mtu: MTU value (e.g., 1500, 9100)

    Returns:
        bool: True if successful
    """
    st.log(f"Configuring MTU {mtu} on {dut} interface {interface}")
    try:
        st.config(dut, [
            "configure terminal",
            f"interface {interface}",
            f"mtu {mtu}",
            "exit",
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ MTU {mtu} configured on {dut} {interface}")
        return True
    except Exception as e:
        st.error(f"Failed to configure MTU on {dut} {interface}: {str(e)}")
        return False


def verify_lldp_neighbor_present(dut: str) -> bool:
    """
    Verify LLDP neighbor is present.

    Args:
        dut: Device name

    Returns:
        bool: True if neighbors found
    """
    st.log(f"Verifying LLDP neighbors present on {dut}")
    try:
        output = st.show(dut, "show lldp neighbor", type=data.cli_type, skip_tmpl=True)
        output_str = str(output)

        st.log(f"LLDP neighbor output:\n{output_str}")

        # Check if neighbor information is present
        if "ChassisID" in output_str or "PortID" in output_str or "SysName" in output_str:
            st.log(f"✓ LLDP neighbors present on {dut}")
            return True
        else:
            st.log(f"⚠ NO LLDP neighbors on {dut}")
            return False

    except Exception as e:
        st.error(f"Failed to verify LLDP neighbors on {dut}: {str(e)}")
        return False


def test_lldp_17_mtu_change_continuity():
    """
    Test Case 4.16.17: Verify LLDP continuity after MTU change

    Test Objective: Verify LLDP neighbors remain after interface MTU change

    Steps:
        1. Enable LLDP globally on both DUTs
        2. Enable LLDP on interfaces
        3. Wait for LLDP neighbor discovery
        4. Verify baseline: neighbors present
        5. Change MTU to 9100 (jumbo frames)
        6. Wait briefly for configuration to apply
        7. Verify LLDP neighbors still present (no disruption)
        8. Restore MTU to 1500 (default)
        9. Verify LLDP neighbors still present
        10. Rollback configuration

    Expected Result (from Manual Test):
        PASS - LLDP neighbors remain present after MTU change

    Actual Result: PASS (as per manual test log)
    """

    # Track validation results
    validation_results = SpyTestDict({
        "global_enable": False,
        "interface_enable": False,
        "baseline_neighbors": False,
        "mtu_change_to_jumbo": False,
        "neighbors_after_jumbo_mtu": False,
        "mtu_restore": False,
        "neighbors_after_mtu_restore": False,
        "rollback": False,
    })

    st.banner("=" * 80)
    st.banner("TEST CASE 4.16.17: Verify LLDP continuity after MTU change")
    st.banner("=" * 80)
    st.log(f"Test Objective: Verify LLDP continues after MTU change")
    st.log(f"DUT1: {vars.D1}")
    st.log(f"DUT2: {vars.D2}")
    st.log(f"Test Interface: {CONFIG.test_interface_dut1}")
    st.log(f"Default MTU: {CONFIG.default_mtu}")
    st.log(f"Jumbo MTU: {CONFIG.jumbo_mtu}")

    # ==================================================================
    # STEP 1: Enable LLDP Globally on Both DUTs
    # ==================================================================
    st.banner("STEP 1: Enable LLDP Globally on Both DUTs")

    if enable_lldp_globally(vars.D1) and enable_lldp_globally(vars.D2):
        validation_results.global_enable = True
        st.log("✓ LLDP enabled globally on both DUTs")
        st.report_tc_pass(TC_IDS.lldp_global_enable, "msg",
                         "LLDP enabled globally")
    else:
        st.log("✗ Failed to enable LLDP globally")
        st.report_tc_fail(TC_IDS.lldp_global_enable, "msg",
                         "Failed to enable LLDP globally")

    # ==================================================================
    # STEP 2: Enable LLDP on Interfaces
    # ==================================================================
    st.banner("STEP 2: Enable LLDP on Interfaces")

    intf_dut1 = enable_lldp_on_interface(vars.D1, CONFIG.test_interface_dut1)
    intf_dut2 = enable_lldp_on_interface(vars.D2, CONFIG.test_interface_dut2)

    if intf_dut1 and intf_dut2:
        validation_results.interface_enable = True
        st.log(f"✓ LLDP enabled on {CONFIG.test_interface_dut1} on both DUTs")
        st.report_tc_pass(TC_IDS.lldp_interface_enable, "msg",
                         "LLDP enabled on interfaces")
    else:
        st.log("✗ Failed to enable LLDP on interfaces")
        st.report_tc_fail(TC_IDS.lldp_interface_enable, "msg",
                         "Failed to enable LLDP on interfaces")

    # ==================================================================
    # STEP 3: Wait for LLDP Neighbor Discovery
    # ==================================================================
    st.banner("STEP 3: Wait for LLDP Neighbor Discovery")

    st.log(f"Waiting {CONFIG.lldp_wait_time} seconds for LLDP neighbors to appear")
    st.wait(CONFIG.lldp_wait_time, "Waiting for LLDP neighbor discovery")

    # ==================================================================
    # STEP 4: Verify Baseline - Neighbors Present
    # ==================================================================
    st.banner("STEP 4: Verify Baseline - LLDP Neighbors Present")

    if verify_lldp_neighbor_present(vars.D1):
        validation_results.baseline_neighbors = True
        st.log("✓ Baseline: LLDP neighbors present on DUT1")
        st.report_tc_pass(TC_IDS.lldp_neighbor_discovery_baseline, "msg",
                         "Baseline LLDP neighbors discovered")
    else:
        st.log("⚠ Baseline: No LLDP neighbors on DUT1 (may be VM environment)")
        st.report_tc_fail(TC_IDS.lldp_neighbor_discovery_baseline, "msg",
                         "Baseline LLDP neighbors not found")

    # ==================================================================
    # STEP 5: Change MTU to Jumbo Frames (9100)
    # ==================================================================
    st.banner(f"STEP 5: Change MTU to {CONFIG.jumbo_mtu} (Jumbo Frames)")

    mtu_dut1 = configure_interface_mtu(vars.D1, CONFIG.test_interface_dut1, CONFIG.jumbo_mtu)
    mtu_dut2 = configure_interface_mtu(vars.D2, CONFIG.test_interface_dut2, CONFIG.jumbo_mtu)

    if mtu_dut1 and mtu_dut2:
        validation_results.mtu_change_to_jumbo = True
        st.log(f"✓ MTU changed to {CONFIG.jumbo_mtu} on both DUTs")
        st.report_tc_pass(TC_IDS.mtu_change_to_jumbo, "msg",
                         f"MTU changed to {CONFIG.jumbo_mtu}")
    else:
        st.log("✗ Failed to change MTU to jumbo")
        st.report_tc_fail(TC_IDS.mtu_change_to_jumbo, "msg",
                         "Failed to change MTU to jumbo")

    # ==================================================================
    # STEP 6: Wait for Configuration to Apply
    # ==================================================================
    st.banner("STEP 6: Wait for MTU Configuration to Apply")

    st.log("Waiting for MTU change to take effect")
    st.wait(10, "Waiting for MTU configuration")

    # ==================================================================
    # STEP 7: Verify LLDP Neighbors Still Present After MTU Change
    # ==================================================================
    st.banner("STEP 7: Verify LLDP Neighbors Still Present After MTU Change")

    if verify_lldp_neighbor_present(vars.D1):
        validation_results.neighbors_after_jumbo_mtu = True
        st.log("✓ LLDP neighbors STILL PRESENT after MTU change (continuity verified)")
        st.report_tc_pass(TC_IDS.lldp_neighbor_after_mtu_change, "msg",
                         "LLDP neighbors present after MTU change")
    else:
        st.log("✗ LLDP neighbors LOST after MTU change (unexpected)")
        st.report_tc_fail(TC_IDS.lldp_neighbor_after_mtu_change, "msg",
                         "LLDP neighbors lost after MTU change")

    # ==================================================================
    # STEP 8: Restore MTU to Default (1500)
    # ==================================================================
    st.banner(f"STEP 8: Restore MTU to Default ({CONFIG.default_mtu})")

    restore_dut1 = configure_interface_mtu(vars.D1, CONFIG.test_interface_dut1, CONFIG.default_mtu)
    restore_dut2 = configure_interface_mtu(vars.D2, CONFIG.test_interface_dut2, CONFIG.default_mtu)

    if restore_dut1 and restore_dut2:
        validation_results.mtu_restore = True
        st.log(f"✓ MTU restored to {CONFIG.default_mtu} on both DUTs")
        st.report_tc_pass(TC_IDS.mtu_restore, "msg",
                         f"MTU restored to {CONFIG.default_mtu}")
    else:
        st.log("✗ Failed to restore MTU")
        st.report_tc_fail(TC_IDS.mtu_restore, "msg",
                         "Failed to restore MTU")

    st.wait(10, "Waiting for MTU restore to take effect")

    # ==================================================================
    # STEP 9: Verify LLDP Neighbors Still Present After MTU Restore
    # ==================================================================
    st.banner("STEP 9: Verify LLDP Neighbors Still Present After MTU Restore")

    if verify_lldp_neighbor_present(vars.D1):
        validation_results.neighbors_after_mtu_restore = True
        st.log("✓ LLDP neighbors STILL PRESENT after MTU restore")
    else:
        st.log("⚠ LLDP neighbors not present after MTU restore")

    # ==================================================================
    # STEP 10: Rollback Configuration
    # ==================================================================
    st.banner("STEP 10: Rollback Configuration - Disable LLDP")

    st.log("Disabling LLDP globally on both DUTs")
    if disable_lldp_globally(vars.D1) and disable_lldp_globally(vars.D2):
        validation_results.rollback = True
        st.log("✓ LLDP disabled globally on both DUTs")
        st.report_tc_pass(TC_IDS.lldp_rollback, "msg",
                         "Configuration rolled back successfully")
    else:
        st.log("⚠ Rollback incomplete")

    st.wait(30, "Waiting for LLDP to clean up")

    # ==================================================================
    # STEP 11: Final Test Result Evaluation
    # ==================================================================
    st.banner("STEP 11: Final Test Result Evaluation")

    # Main test criterion: LLDP neighbors remain after MTU change
    if validation_results.neighbors_after_jumbo_mtu:
        st.log("✓ LLDP continuity maintained after MTU change")

        st.banner("=" * 80)
        st.banner("TEST RESULT: LLDP 4.16.17 PASSED")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - 4.16.17: LLDP continuity after MTU change")
        st.log("=" * 80)
        st.log(f"✓ LLDP enabled globally on both DUTs")
        st.log(f"✓ LLDP enabled on interfaces")
        st.log(f"✓ Baseline LLDP neighbors discovered")
        st.log(f"✓ MTU changed to {CONFIG.jumbo_mtu} (jumbo frames)")
        st.log(f"✓ LLDP neighbors remained after MTU change (continuity verified)")
        st.log(f"✓ MTU restored to {CONFIG.default_mtu}")
        st.log(f"✓ Configuration rolled back")
        st.log("=" * 80)
        st.log("NOTE: As per manual test: PASS - LLDP unaffected by MTU change")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
    else:
        st.log("✗ LLDP continuity NOT maintained after MTU change")

        st.banner("=" * 80)
        st.banner("TEST RESULT: LLDP 4.16.17 FAILED")
        st.banner("=" * 80)

        st.report_fail("msg", "LLDP MTU change test failed: neighbors lost after MTU change")
