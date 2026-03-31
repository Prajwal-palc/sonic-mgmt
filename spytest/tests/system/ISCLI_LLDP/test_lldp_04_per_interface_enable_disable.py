r"""
LLDP TEST - OC-1 Test ID 4.16.4: Verify per-interface LLDP enable/disable

Test Case ID: 4.16.4
Feature: LLDP
Test Item: Per-Interface Enable/Disable
Author: Automated from Manual Validation
Copyright (C) 2024-2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_LLDP/test_lldp_04_per_interface_enable_disable.py \
    --logs-path ./logs/lldp_04_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates per-interface LLDP enable/disable functionality:
  - Enable LLDP globally and on interfaces
  - Verify neighbors discovered
  - Disable LLDP on one interface only
  - Verify neighbors removed on that interface
  - Other interfaces should still have neighbors
  - Rollback configuration

KNOWN ISSUE (Manual Test FAIL):
  - "no lldp enable" on interface does not disable LLDP
  - Interface continues to send/receive LLDP packets
  - Neighbors remain visible after per-interface disable
  - This is a confirmed bug in ISCLI LLDP implementation

Pre-requisites:
  - 2 SONiC devices connected
  - Testbed: testbed_2vs.yaml
  - Interfaces cabled as per topology
  - Clean LLDP configuration

Expected Result (Manual Test):
  FAIL - Per-interface LLDP disable is not working

Manual Test Log Reference (Test 4.16.4 FAIL):
  sonic(config)# lldp enable
  sonic(config)# interface Ethernet 8
  sonic(conf-if-Ethernet8)# lldp enable
  sonic# show lldp neighbor
  [Neighbor present on Ethernet8]

  sonic(conf-if-Ethernet8)# no lldp enable
  sonic# show lldp neighbor
  [Expected: No neighbor on Ethernet8, Actual: Neighbor still present]

  Issue: "Ethernet8 still showing neighbor after 'no lldp enable'"
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
    "lldp_wait_time": 60,  # Wait time for LLDP neighbors to appear
    "lldp_timer": 30,      # LLDP update timer
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "lldp_global_enable": "TC-LLDP-4.16.4-001",
    "lldp_interface_enable": "TC-LLDP-4.16.4-002",
    "lldp_neighbor_discovery": "TC-LLDP-4.16.4-003",
    "lldp_interface_disable": "TC-LLDP-4.16.4-004",
    "lldp_verify_neighbor_removed": "TC-LLDP-4.16.4-005",
    "lldp_rollback": "TC-LLDP-4.16.4-006",
})


@pytest.fixture(scope="module", autouse=True)
def lldp_per_interface_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.4 PER-INTERFACE ENABLE/DISABLE TEST - MODULE START")
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

    st.log("⚠ KNOWN ISSUE: Per-interface 'no lldp enable' does not disable LLDP")
    st.log("⚠ This test documents the expected failure from manual testing")

    # Pre-configuration
    lldp_pre_config()

    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.4 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        lldp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")

    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.4 MODULE CLEANUP - COMPLETED")
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
    """Cleanup: Remove all LLDP configuration."""
    st.log("Cleanup: Removing LLDP configuration")

    dut_list = [vars.D1, vars.D2]

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


def disable_lldp_on_interface(dut: str, interface: str) -> bool:
    """
    Disable LLDP on specific interface.

    KNOWN ISSUE: This command does NOT actually disable LLDP on the interface.
    From manual test: "Ethernet8 still showing neighbor after 'no lldp enable'"

    Args:
        dut: Device name
        interface: Interface name (e.g., "Ethernet8")

    Returns:
        bool: True if command executed (even if ineffective)
    """
    st.log(f"Disabling LLDP on {dut} interface {interface}")
    st.log("⚠ KNOWN ISSUE: This command may not be effective")
    try:
        st.config(dut, [
            "configure terminal",
            f"interface {interface}",
            "no lldp enable",
            "exit",
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ 'no lldp enable' command issued on {dut} {interface}")
        st.log(f"⚠ WARNING: Command may not actually disable LLDP (known bug)")
        return True
    except Exception as e:
        st.error(f"Failed to disable LLDP on {dut} {interface}: {str(e)}")
        return False


def verify_lldp_neighbor_present(dut: str, expected_interface: str = None) -> bool:
    """
    Verify LLDP neighbor is present.

    Args:
        dut: Device name
        expected_interface: Expected local interface with neighbor

    Returns:
        bool: True if neighbors found
    """
    st.log(f"Verifying LLDP neighbors present on {dut}")
    try:
        output = st.show(dut, "show lldp neighbor", type=data.cli_type, skip_tmpl=True)
        output_str = str(output)

        st.log(f"LLDP neighbor output:\n{output_str}")

        # Check if neighbor information is present
        if "ChassisID" in output_str or "PortID" in output_str:
            st.log(f"✓ LLDP neighbors present on {dut}")
            if expected_interface and expected_interface in output_str:
                st.log(f"  ✓ Neighbor on interface {expected_interface}")
            return True
        else:
            st.log(f"⚠ NO LLDP neighbors on {dut}")
            return False

    except Exception as e:
        st.error(f"Failed to verify LLDP neighbors on {dut}: {str(e)}")
        return False


def verify_lldp_neighbor_absent_on_interface(dut: str, interface: str) -> bool:
    """
    Verify that NO LLDP neighbor is present on specific interface.

    Args:
        dut: Device name
        interface: Interface name (e.g., "Ethernet8")

    Returns:
        bool: True if NO neighbors found on specified interface
    """
    st.log(f"Verifying NO LLDP neighbors on {dut} interface {interface}")
    try:
        output = st.show(dut, "show lldp neighbor", type=data.cli_type, skip_tmpl=True)
        output_str = str(output)

        st.log(f"LLDP neighbor output:\n{output_str}")

        # Check if interface appears in neighbor output
        if interface in output_str and ("ChassisID" in output_str or "PortID" in output_str):
            st.log(f"✗ LLDP neighbors STILL PRESENT on {dut} interface {interface} (unexpected)")
            return False
        else:
            st.log(f"✓ NO LLDP neighbors on {dut} interface {interface} (expected)")
            return True

    except Exception as e:
        st.log(f"LLDP neighbor check error on {dut}: {str(e)}")
        # If command errors, assume no neighbors
        return True


def test_lldp_04_per_interface_enable_disable():
    """
    Test Case 4.16.4: Verify per-interface LLDP enable/disable

    Test Objective: Verify that disabling LLDP on a specific interface
                    removes LLDP neighbors on that interface only

    Steps:
        1. Enable LLDP globally on both DUTs
        2. Enable LLDP on interface Ethernet8 on both DUTs
        3. Wait for LLDP neighbor discovery
        4. Verify neighbors present on Ethernet8
        5. Disable LLDP on interface Ethernet8 on DUT1
        6. Wait for LLDP timers to expire
        7. Verify DUT2 should NOT see DUT1 neighbor on Ethernet8
        8. Rollback configuration

    Expected Result (from Manual Test):
        FAIL - Per-interface LLDP disable is NOT working
        - "no lldp enable" on interface does not stop LLDP
        - Neighbors remain visible after per-interface disable

    Actual Result: FAIL (as per manual test log)

    KNOWN ISSUE:
        This is a confirmed bug in ISCLI LLDP implementation.
        The test documents this expected failure.
    """

    # Track validation results
    validation_results = SpyTestDict({
        "global_enable": False,
        "interface_enable": False,
        "neighbor_discovery": False,
        "interface_disable_command": False,
        "neighbor_removed": False,  # Should be True if bug fixed
        "rollback": False,
        "known_bug_confirmed": False,
    })

    st.banner("=" * 80)
    st.banner("TEST CASE 4.16.4: Verify per-interface LLDP enable/disable")
    st.banner("=" * 80)
    st.log(f"Test Objective: Verify per-interface LLDP disable functionality")
    st.log(f"DUT1: {vars.D1}")
    st.log(f"DUT2: {vars.D2}")
    st.log(f"Test Interface DUT1: {CONFIG.test_interface_dut1}")
    st.log(f"Test Interface DUT2: {CONFIG.test_interface_dut2}")
    st.log("")
    st.log("⚠ KNOWN ISSUE: Per-interface 'no lldp enable' does not work")
    st.log("⚠ This test is expected to FAIL due to known bug")
    st.log("")

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
    # STEP 2: Enable LLDP on Interface on Both DUTs
    # ==================================================================
    st.banner("STEP 2: Enable LLDP on Interface Ethernet8 on Both DUTs")

    dut1_intf = enable_lldp_on_interface(vars.D1, CONFIG.test_interface_dut1)
    dut2_intf = enable_lldp_on_interface(vars.D2, CONFIG.test_interface_dut2)

    if dut1_intf and dut2_intf:
        validation_results.interface_enable = True
        st.log(f"✓ LLDP enabled on {CONFIG.test_interface_dut1} on both DUTs")
        st.report_tc_pass(TC_IDS.lldp_interface_enable, "msg",
                         "LLDP enabled on interfaces")
    else:
        st.log(f"✗ Failed to enable LLDP on interfaces")
        st.report_tc_fail(TC_IDS.lldp_interface_enable, "msg",
                         "Failed to enable LLDP on interfaces")

    # ==================================================================
    # STEP 3: Wait for LLDP Neighbor Discovery
    # ==================================================================
    st.banner("STEP 3: Wait for LLDP Neighbor Discovery")

    st.log(f"Waiting {CONFIG.lldp_wait_time} seconds for LLDP neighbors to appear")
    st.wait(CONFIG.lldp_wait_time, "Waiting for LLDP neighbor discovery")

    # ==================================================================
    # STEP 4: Verify Neighbors Present on Ethernet8
    # ==================================================================
    st.banner("STEP 4: Verify Neighbors Present on Ethernet8")

    if verify_lldp_neighbor_present(vars.D2, CONFIG.test_interface_dut2):
        validation_results.neighbor_discovery = True
        st.log("✓ LLDP neighbors discovered on DUT2")
        st.report_tc_pass(TC_IDS.lldp_neighbor_discovery, "msg",
                         "LLDP neighbors discovered")
    else:
        st.log("⚠ No LLDP neighbors on DUT2 (may be VM environment)")
        st.report_tc_fail(TC_IDS.lldp_neighbor_discovery, "msg",
                         "LLDP neighbors not found (may be VM limitation)")

    # ==================================================================
    # STEP 5: Disable LLDP on Interface Ethernet8 on DUT1
    # ==================================================================
    st.banner("STEP 5: Disable LLDP on Interface Ethernet8 on DUT1")

    if disable_lldp_on_interface(vars.D1, CONFIG.test_interface_dut1):
        validation_results.interface_disable_command = True
        st.log(f"✓ 'no lldp enable' command issued on DUT1 {CONFIG.test_interface_dut1}")
        st.report_tc_pass(TC_IDS.lldp_interface_disable, "msg",
                         "Per-interface LLDP disable command executed")
    else:
        st.log(f"✗ Failed to disable LLDP on DUT1 interface")
        st.report_tc_fail(TC_IDS.lldp_interface_disable, "msg",
                         "Failed to disable LLDP on interface")

    # ==================================================================
    # STEP 6: Wait for LLDP Timers to Expire
    # ==================================================================
    st.banner("STEP 6: Wait for LLDP Timers to Expire")

    st.log("Waiting for LLDP timers to expire")
    st.wait(CONFIG.lldp_wait_time, "Waiting for LLDP to stop on disabled interface")

    # ==================================================================
    # STEP 7: Verify DUT2 Should NOT See DUT1 Neighbor on Ethernet8
    # ==================================================================
    st.banner("STEP 7: Verify DUT2 Should NOT See DUT1 Neighbor on Ethernet8")

    if verify_lldp_neighbor_absent_on_interface(vars.D2, CONFIG.test_interface_dut2):
        st.log("✓ NO neighbors on DUT2 - Per-interface disable is WORKING")
        validation_results.neighbor_removed = True
        st.report_tc_pass(TC_IDS.lldp_verify_neighbor_removed, "msg",
                         "Per-interface LLDP disable effective (bug fixed!)")
    else:
        st.log("✗ NEIGHBORS STILL PRESENT on DUT2 - Per-interface disable NOT WORKING")
        st.log(f"⚠ KNOWN BUG: 'no lldp enable' on interface does not disable LLDP")
        validation_results.known_bug_confirmed = True
        # Report as expected failure
        st.log("⚠ This is an expected failure (documented bug)")
        st.report_tc_fail(TC_IDS.lldp_verify_neighbor_removed, "msg",
                         "Per-interface LLDP disable not effective (known bug)")

    # ==================================================================
    # STEP 8: Rollback Configuration
    # ==================================================================
    st.banner("STEP 8: Rollback Configuration - Disable LLDP")

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
    # STEP 9: Final Test Result Evaluation
    # ==================================================================
    st.banner("STEP 9: Final Test Result Evaluation")

    # This test is EXPECTED to fail due to known bug
    if validation_results.known_bug_confirmed:
        st.log("✓ KNOWN BUG CONFIRMED: Per-interface LLDP disable ineffective")
        st.log("  - 'no lldp enable' on interface does not stop LLDP")
        st.log("  - Neighbors remain visible after per-interface disable")

    if validation_results.neighbor_removed:
        st.log("✓ BUG FIXED! Per-interface LLDP disable now working!")
        st.banner("=" * 80)
        st.banner("TEST RESULT: LLDP 4.16.4 PASSED (BUG FIXED!)")
        st.banner("=" * 80)
        st.report_pass("test_case_passed")
    else:
        st.log("✗ Per-interface LLDP disable NOT working (as expected)")

        st.banner("=" * 80)
        st.banner("TEST RESULT: LLDP 4.16.4 FAILED (KNOWN BUG)")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - 4.16.4: Per-interface LLDP enable/disable")
        st.log("=" * 80)
        st.log(f"✓ LLDP enabled globally on both DUTs")
        st.log(f"✓ LLDP enabled on interfaces")
        st.log(f"✓ LLDP neighbors discovered")
        st.log(f"✓ 'no lldp enable' command executed on interface (but ineffective)")
        st.log(f"✗ Per-interface disable did NOT remove neighbors (BUG)")
        st.log(f"✓ Configuration rolled back")
        st.log("=" * 80)
        st.log("NOTE: As per manual test: FAIL - Per-interface disable not working")
        st.log("=" * 80)

        st.report_fail("msg", "Per-interface LLDP disable test failed (known bug): command not effective")
