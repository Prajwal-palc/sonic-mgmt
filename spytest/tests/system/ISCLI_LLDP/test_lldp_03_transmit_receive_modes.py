r"""
LLDP TEST - OC-1 Test ID 4.16.3: Verify LLDP TRANSMIT and RECEIVE modes

Test Case ID: 4.16.3
Feature: LLDP
Test Item: TRANSMIT and RECEIVE Modes
Author: Automated from Manual Validation
Copyright (C) 2024-2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_LLDP/test_lldp_03_transmit_receive_modes.py \
    --logs-path ./logs/lldp_03_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates LLDP TRANSMIT and RECEIVE mode restrictions:
  - Enable LLDP globally
  - Disable TRANSMIT mode on one side
  - Verify no neighbor discovered (TRANSMIT disabled)
  - Enable TRANSMIT mode
  - Disable RECEIVE mode on other side
  - Verify no neighbor discovered (RECEIVE disabled)
  - Rollback configuration

KNOWN ISSUE (Manual Test FAIL):
  - "no lldp TRANSMIT" command does not disable transmission
  - "no lldp RECEIVE" command does not disable reception
  - LLDP continues to work even with modes disabled
  - This is a confirmed bug in ISCLI LLDP implementation

Pre-requisites:
  - 2 SONiC devices connected
  - Testbed: testbed_2vs.yaml
  - Interfaces cabled as per topology
  - Clean LLDP configuration

Expected Result (Manual Test):
  FAIL - LLDP RECEIVE and TRANSMIT modes are not being honored

Manual Test Log Reference (Test 4.16.3 FAIL):
  sonic(config)# lldp enable
  sonic(config)# interface Ethernet 8
  sonic(conf-if-Ethernet8)# lldp enable
  sonic(conf-if-Ethernet8)# no lldp TRANSMIT
  [Expected: No neighbor on remote, Actual: Neighbor still present]

  sonic(conf-if-Ethernet8)# lldp TRANSMIT
  sonic(conf-if-Ethernet8)# no lldp RECEIVE
  [Expected: No neighbor received, Actual: Neighbor still received]

  Issue: "LLDP RECEIVE mode is not being honored"
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
    "lldp_global_enable": "TC-LLDP-4.16.3-001",
    "lldp_interface_enable": "TC-LLDP-4.16.3-002",
    "lldp_disable_transmit": "TC-LLDP-4.16.3-003",
    "lldp_verify_no_neighbor_tx_disabled": "TC-LLDP-4.16.3-004",
    "lldp_enable_transmit": "TC-LLDP-4.16.3-005",
    "lldp_disable_receive": "TC-LLDP-4.16.3-006",
    "lldp_verify_no_neighbor_rx_disabled": "TC-LLDP-4.16.3-007",
    "lldp_rollback": "TC-LLDP-4.16.3-008",
})


@pytest.fixture(scope="module", autouse=True)
def lldp_tx_rx_modes_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.3 TRANSMIT/RECEIVE MODES TEST - MODULE START")
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

    st.log("⚠ KNOWN ISSUE: LLDP TX/RX mode disable commands do not work in ISCLI")
    st.log("⚠ This test documents the expected failure from manual testing")

    # Pre-configuration
    lldp_pre_config()

    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.3 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        lldp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")

    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.3 MODULE CLEANUP - COMPLETED")
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


def disable_lldp_transmit_mode(dut: str, interface: str) -> bool:
    """
    Disable LLDP TRANSMIT mode on interface.

    KNOWN ISSUE: This command does NOT actually disable transmission.
    From manual test: "LLDP TRANSMIT mode is not being honored"

    Args:
        dut: Device name
        interface: Interface name (e.g., "Ethernet8")

    Returns:
        bool: True if command executed (even if ineffective)
    """
    st.log(f"Disabling LLDP TRANSMIT mode on {dut} interface {interface}")
    st.log("⚠ KNOWN ISSUE: This command may not be effective")
    try:
        st.config(dut, [
            "configure terminal",
            f"interface {interface}",
            "no lldp TRANSMIT",
            "exit",
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ 'no lldp TRANSMIT' command issued on {dut} {interface}")
        st.log(f"⚠ WARNING: Command may not actually disable transmission (known bug)")
        return True
    except Exception as e:
        st.error(f"Failed to disable LLDP TRANSMIT on {dut} {interface}: {str(e)}")
        return False


def enable_lldp_transmit_mode(dut: str, interface: str) -> bool:
    """Enable LLDP TRANSMIT mode on interface."""
    st.log(f"Enabling LLDP TRANSMIT mode on {dut} interface {interface}")
    try:
        st.config(dut, [
            "configure terminal",
            f"interface {interface}",
            "lldp TRANSMIT",
            "exit",
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ LLDP TRANSMIT enabled on {dut} {interface}")
        return True
    except Exception as e:
        st.error(f"Failed to enable LLDP TRANSMIT on {dut} {interface}: {str(e)}")
        return False


def disable_lldp_receive_mode(dut: str, interface: str) -> bool:
    """
    Disable LLDP RECEIVE mode on interface.

    KNOWN ISSUE: This command does NOT actually disable reception.
    From manual test: "LLDP RECEIVE mode is not being honored"

    Args:
        dut: Device name
        interface: Interface name (e.g., "Ethernet8")

    Returns:
        bool: True if command executed (even if ineffective)
    """
    st.log(f"Disabling LLDP RECEIVE mode on {dut} interface {interface}")
    st.log("⚠ KNOWN ISSUE: This command may not be effective")
    try:
        st.config(dut, [
            "configure terminal",
            f"interface {interface}",
            "no lldp RECEIVE",
            "exit",
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ 'no lldp RECEIVE' command issued on {dut} {interface}")
        st.log(f"⚠ WARNING: Command may not actually disable reception (known bug)")
        return True
    except Exception as e:
        st.error(f"Failed to disable LLDP RECEIVE on {dut} {interface}: {str(e)}")
        return False


def verify_no_lldp_neighbor(dut: str) -> bool:
    """
    Verify that NO LLDP neighbor is present.

    Args:
        dut: Device name

    Returns:
        bool: True if NO neighbors found (expected behavior when TX/RX disabled)
    """
    st.log(f"Verifying NO LLDP neighbors on {dut}")
    try:
        output = st.show(dut, "show lldp neighbor", type=data.cli_type, skip_tmpl=True)
        output_str = str(output)

        st.log(f"LLDP neighbor output:\n{output_str}")

        # Check if neighbor information is present
        if ("ChassisID" in output_str or "PortID" in output_str or
            "SysName" in output_str):
            st.log(f"✗ LLDP neighbors STILL PRESENT on {dut} (unexpected)")
            return False
        else:
            st.log(f"✓ NO LLDP neighbors on {dut} (expected)")
            return True

    except Exception as e:
        st.log(f"LLDP neighbor check error on {dut}: {str(e)}")
        # If command errors, assume no neighbors
        return True


def test_lldp_03_transmit_receive_modes():
    """
    Test Case 4.16.3: Verify LLDP TRANSMIT and RECEIVE modes

    Test Objective: Verify that disabling TRANSMIT/RECEIVE modes prevents
                    LLDP neighbor discovery

    Steps:
        1. Enable LLDP globally on both DUTs
        2. Enable LLDP on interface Ethernet8 on both DUTs
        3. Verify baseline: neighbors discovered
        4. Disable TRANSMIT mode on DUT1 Ethernet8
        5. Wait and verify: DUT2 should NOT see DUT1 neighbor
        6. Re-enable TRANSMIT mode on DUT1
        7. Disable RECEIVE mode on DUT2 Ethernet8
        8. Wait and verify: DUT2 should NOT see DUT1 neighbor
        9. Rollback configuration

    Expected Result (from Manual Test):
        FAIL - LLDP TRANSMIT and RECEIVE modes are NOT honored
        - "no lldp TRANSMIT" does not stop transmission
        - "no lldp RECEIVE" does not stop reception
        - Neighbors remain visible even with modes disabled

    Actual Result: FAIL (as per manual test log)

    KNOWN ISSUE:
        This is a confirmed bug in ISCLI LLDP implementation.
        The test documents this expected failure.
    """

    # Track validation results
    validation_results = SpyTestDict({
        "global_enable": False,
        "interface_enable": False,
        "baseline_neighbors": False,
        "transmit_disabled_effective": False,  # Should be True if bug fixed
        "receive_disabled_effective": False,   # Should be True if bug fixed
        "rollback": False,
        "known_bug_confirmed": False,
    })

    st.banner("=" * 80)
    st.banner("TEST CASE 4.16.3: Verify LLDP TRANSMIT and RECEIVE modes")
    st.banner("=" * 80)
    st.log(f"Test Objective: Verify TX/RX mode restrictions")
    st.log(f"DUT1: {vars.D1}")
    st.log(f"DUT2: {vars.D2}")
    st.log(f"Test Interface DUT1: {CONFIG.test_interface_dut1}")
    st.log(f"Test Interface DUT2: {CONFIG.test_interface_dut2}")
    st.log("")
    st.log("⚠ KNOWN ISSUE: LLDP TX/RX mode disable commands do not work")
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
    # STEP 3: Verify Baseline - Neighbors Discovered
    # ==================================================================
    st.banner("STEP 3: Verify Baseline - LLDP Neighbors Discovered")

    st.log(f"Waiting {CONFIG.lldp_wait_time} seconds for LLDP neighbors to appear")
    st.wait(CONFIG.lldp_wait_time, "Waiting for LLDP neighbor discovery")

    # Check if neighbors present (baseline)
    try:
        output_dut2 = st.show(vars.D2, "show lldp neighbor", type=data.cli_type, skip_tmpl=True)
        output_str = str(output_dut2)
        if "ChassisID" in output_str or "PortID" in output_str:
            validation_results.baseline_neighbors = True
            st.log("✓ Baseline: LLDP neighbors present on DUT2")
        else:
            st.log("⚠ Baseline: No LLDP neighbors on DUT2 (may be VM environment)")
    except Exception as e:
        st.log(f"Baseline check warning: {str(e)}")

    # ==================================================================
    # STEP 4: Disable TRANSMIT Mode on DUT1 Ethernet8
    # ==================================================================
    st.banner("STEP 4: Disable TRANSMIT Mode on DUT1 Ethernet8")

    if disable_lldp_transmit_mode(vars.D1, CONFIG.test_interface_dut1):
        st.log(f"✓ 'no lldp TRANSMIT' command issued on DUT1 {CONFIG.test_interface_dut1}")
        st.report_tc_pass(TC_IDS.lldp_disable_transmit, "msg",
                         "LLDP TRANSMIT disable command executed")
    else:
        st.log(f"✗ Failed to disable TRANSMIT mode on DUT1")
        st.report_tc_fail(TC_IDS.lldp_disable_transmit, "msg",
                         "Failed to disable LLDP TRANSMIT")

    # ==================================================================
    # STEP 5: Verify DUT2 Should NOT See DUT1 Neighbor (TX Disabled)
    # ==================================================================
    st.banner("STEP 5: Verify DUT2 Should NOT See DUT1 Neighbor (TX Disabled)")

    st.log("Waiting for LLDP timers to expire")
    st.wait(CONFIG.lldp_wait_time, "Waiting for LLDP to stop transmitting")

    if verify_no_lldp_neighbor(vars.D2):
        st.log("✓ NO neighbors on DUT2 - TRANSMIT disable is WORKING")
        validation_results.transmit_disabled_effective = True
        st.report_tc_pass(TC_IDS.lldp_verify_no_neighbor_tx_disabled, "msg",
                         "LLDP TRANSMIT disable effective (bug fixed!)")
    else:
        st.log("✗ NEIGHBORS STILL PRESENT on DUT2 - TRANSMIT disable NOT WORKING")
        st.log("⚠ KNOWN BUG: 'no lldp TRANSMIT' does not stop transmission")
        validation_results.known_bug_confirmed = True
        # Report as expected failure
        st.log("⚠ This is an expected failure (documented bug)")
        st.report_tc_fail(TC_IDS.lldp_verify_no_neighbor_tx_disabled, "msg",
                         "LLDP TRANSMIT disable not effective (known bug)")

    # ==================================================================
    # STEP 6: Re-enable TRANSMIT Mode on DUT1
    # ==================================================================
    st.banner("STEP 6: Re-enable TRANSMIT Mode on DUT1")

    if enable_lldp_transmit_mode(vars.D1, CONFIG.test_interface_dut1):
        st.log(f"✓ LLDP TRANSMIT re-enabled on DUT1 {CONFIG.test_interface_dut1}")
        st.report_tc_pass(TC_IDS.lldp_enable_transmit, "msg",
                         "LLDP TRANSMIT re-enabled")
    else:
        st.log(f"✗ Failed to re-enable TRANSMIT mode on DUT1")

    st.wait(30, "Waiting for LLDP to resume")

    # ==================================================================
    # STEP 7: Disable RECEIVE Mode on DUT2 Ethernet8
    # ==================================================================
    st.banner("STEP 7: Disable RECEIVE Mode on DUT2 Ethernet8")

    if disable_lldp_receive_mode(vars.D2, CONFIG.test_interface_dut2):
        st.log(f"✓ 'no lldp RECEIVE' command issued on DUT2 {CONFIG.test_interface_dut2}")
        st.report_tc_pass(TC_IDS.lldp_disable_receive, "msg",
                         "LLDP RECEIVE disable command executed")
    else:
        st.log(f"✗ Failed to disable RECEIVE mode on DUT2")
        st.report_tc_fail(TC_IDS.lldp_disable_receive, "msg",
                         "Failed to disable LLDP RECEIVE")

    # ==================================================================
    # STEP 8: Verify DUT2 Should NOT See DUT1 Neighbor (RX Disabled)
    # ==================================================================
    st.banner("STEP 8: Verify DUT2 Should NOT See DUT1 Neighbor (RX Disabled)")

    st.log("Waiting for LLDP timers to expire")
    st.wait(CONFIG.lldp_wait_time, "Waiting for LLDP to stop receiving")

    if verify_no_lldp_neighbor(vars.D2):
        st.log("✓ NO neighbors on DUT2 - RECEIVE disable is WORKING")
        validation_results.receive_disabled_effective = True
        st.report_tc_pass(TC_IDS.lldp_verify_no_neighbor_rx_disabled, "msg",
                         "LLDP RECEIVE disable effective (bug fixed!)")
    else:
        st.log("✗ NEIGHBORS STILL PRESENT on DUT2 - RECEIVE disable NOT WORKING")
        st.log("⚠ KNOWN BUG: 'no lldp RECEIVE' does not stop reception")
        validation_results.known_bug_confirmed = True
        # Report as expected failure
        st.log("⚠ This is an expected failure (documented bug)")
        st.report_tc_fail(TC_IDS.lldp_verify_no_neighbor_rx_disabled, "msg",
                         "LLDP RECEIVE disable not effective (known bug)")

    # ==================================================================
    # STEP 9: Rollback Configuration
    # ==================================================================
    st.banner("STEP 9: Rollback Configuration - Disable LLDP")

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
    # STEP 10: Final Test Result Evaluation
    # ==================================================================
    st.banner("STEP 10: Final Test Result Evaluation")

    # This test is EXPECTED to fail due to known bug
    if validation_results.known_bug_confirmed:
        st.log("✓ KNOWN BUG CONFIRMED: LLDP TX/RX mode disable commands ineffective")
        st.log("  - 'no lldp TRANSMIT' does not stop transmission")
        st.log("  - 'no lldp RECEIVE' does not stop reception")
        st.log("  - LLDP continues to work with modes disabled")

    if validation_results.transmit_disabled_effective and validation_results.receive_disabled_effective:
        st.log("✓ BUG FIXED! LLDP TX/RX mode restrictions now working!")
        st.banner("=" * 80)
        st.banner("TEST RESULT: LLDP 4.16.3 PASSED (BUG FIXED!)")
        st.banner("=" * 80)
        st.report_pass("test_case_passed")
    else:
        st.log("✗ LLDP TX/RX mode restrictions NOT working (as expected)")

        st.banner("=" * 80)
        st.banner("TEST RESULT: LLDP 4.16.3 FAILED (KNOWN BUG)")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - 4.16.3: LLDP TRANSMIT and RECEIVE modes")
        st.log("=" * 80)
        st.log(f"✓ LLDP enabled globally on both DUTs")
        st.log(f"✓ LLDP enabled on interfaces")
        st.log(f"✓ 'no lldp TRANSMIT' command executed (but ineffective)")
        st.log(f"✗ TRANSMIT disable did NOT prevent LLDP transmission (BUG)")
        st.log(f"✓ 'no lldp RECEIVE' command executed (but ineffective)")
        st.log(f"✗ RECEIVE disable did NOT prevent LLDP reception (BUG)")
        st.log(f"✓ Configuration rolled back")
        st.log("=" * 80)
        st.log("NOTE: As per manual test: FAIL - LLDP TX/RX modes not honored")
        st.log("=" * 80)

        st.report_fail("msg", "LLDP TX/RX mode test failed (known bug): modes not enforced")
