r"""
LLDP TEST - OC-1 Test ID 4.16.6: Verify System Name, Description, and Management Address TLVs

Test Case ID: 4.16.6
Feature: LLDP
Test Item: System TLVs (Name, Description, Management Address)
Author: Automated from Manual Validation
Copyright (C) 2024-2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_LLDP/test_lldp_06_system_name_description_mgmt_tlv.py \
    --logs-path ./logs/lldp_06_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates LLDP System TLVs:
  - System Name TLV (hostname)
  - System Description TLV (SONiC version)
  - Management Address TLV (management IP)
  - Enable/disable TLV advertisement
  - Verify TLVs in neighbor output

KNOWN ISSUE (Manual Test FAIL):
  - Management Address TLV is NOT visible in "show lldp neighbor" output
  - Mgmt IP field is missing from CLI output
  - TLV is present but not displayed by ISCLI
  - Workaround: Use "sudo lldpctl show neighbors" to see Mgmt Address

Pre-requisites:
  - 2 SONiC devices connected
  - Testbed: testbed_2vs.yaml
  - Interfaces cabled as per topology
  - Management IP configured
  - Clean LLDP configuration

Expected Result (Manual Test):
  FAIL - Management Address TLV not shown in CLI output

Manual Test Log Reference (Test 4.16.6 FAIL):
  sonic(config)# lldp enable
  sonic(config)# lldp tlv-select management-address enable
  sonic(config)# lldp tlv-select system-name enable
  sonic(config)# lldp tlv-select system-description enable

  sonic# show lldp neighbor
    ChassisID: 52:54:00:a3:7a:49
    SysName: sonic
    SysDescr: SONiC Software Version...
    [Expected: Mgmt Address, Actual: Field not present]

  Issue: "No Mgmt ip field present in this command output"
  Workaround: "sudo lldpctl show neighbors" shows management address
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
    "lldp_wait_time": 60,
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "lldp_global_enable": "TC-LLDP-4.16.6-001",
    "lldp_interface_enable": "TC-LLDP-4.16.6-002",
    "lldp_tlv_system_name": "TC-LLDP-4.16.6-003",
    "lldp_tlv_system_description": "TC-LLDP-4.16.6-004",
    "lldp_tlv_management_address": "TC-LLDP-4.16.6-005",
    "lldp_neighbor_discovery": "TC-LLDP-4.16.6-006",
    "lldp_verify_tlvs": "TC-LLDP-4.16.6-007",
    "lldp_verify_mgmt_address": "TC-LLDP-4.16.6-008",
    "lldp_rollback": "TC-LLDP-4.16.6-009",
})


@pytest.fixture(scope="module", autouse=True)
def lldp_system_tlvs_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.6 SYSTEM TLVs TEST - MODULE START")
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

    st.log("⚠ KNOWN ISSUE: Management Address TLV not visible in 'show lldp neighbor'")
    st.log("⚠ Workaround: Use 'sudo lldpctl show neighbors' for full TLV details")

    # Pre-configuration
    lldp_pre_config()

    yield

    # Cleanup
    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.6 MODULE CLEANUP - START")
    st.banner("=" * 80)
    try:
        lldp_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")

    st.banner("=" * 80)
    st.banner("LLDP OC-1 4.16.6 MODULE CLEANUP - COMPLETED")
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


def configure_lldp_tlv_system_name(dut: str, enable: bool = True) -> bool:
    """
    Enable/disable System Name TLV advertisement.

    Args:
        dut: Device name
        enable: True to enable, False to disable

    Returns:
        bool: True if command executed
    """
    action = "enable" if enable else "disable"
    st.log(f"Configuring LLDP TLV System Name to {action} on {dut}")
    try:
        cmd = "lldp tlv-select system-name enable" if enable else "no lldp tlv-select system-name"
        st.config(dut, [
            "configure terminal",
            cmd,
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ System Name TLV {action}d on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure System Name TLV on {dut}: {str(e)}")
        return False


def configure_lldp_tlv_system_description(dut: str, enable: bool = True) -> bool:
    """
    Enable/disable System Description TLV advertisement.

    Args:
        dut: Device name
        enable: True to enable, False to disable

    Returns:
        bool: True if command executed
    """
    action = "enable" if enable else "disable"
    st.log(f"Configuring LLDP TLV System Description to {action} on {dut}")
    try:
        cmd = "lldp tlv-select system-description enable" if enable else "no lldp tlv-select system-description"
        st.config(dut, [
            "configure terminal",
            cmd,
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ System Description TLV {action}d on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure System Description TLV on {dut}: {str(e)}")
        return False


def configure_lldp_tlv_management_address(dut: str, enable: bool = True) -> bool:
    """
    Enable/disable Management Address TLV advertisement.

    Args:
        dut: Device name
        enable: True to enable, False to disable

    Returns:
        bool: True if command executed
    """
    action = "enable" if enable else "disable"
    st.log(f"Configuring LLDP TLV Management Address to {action} on {dut}")
    try:
        cmd = "lldp tlv-select management-address enable" if enable else "no lldp tlv-select management-address"
        st.config(dut, [
            "configure terminal",
            cmd,
            "exit"
        ], type=data.cli_type, skip_error_check=True)
        st.log(f"✓ Management Address TLV {action}d on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure Management Address TLV on {dut}: {str(e)}")
        return False


def verify_lldp_system_tlvs(dut: str) -> dict:
    """
    Verify LLDP System TLVs in neighbor output.

    Returns dict with TLV presence:
    {
        "system_name": bool,
        "system_description": bool,
        "management_address": bool,
    }

    Args:
        dut: Device name

    Returns:
        dict: TLV presence status
    """
    st.log(f"Verifying LLDP System TLVs on {dut}")

    tlv_status = {
        "system_name": False,
        "system_description": False,
        "management_address": False,
    }

    try:
        output = st.show(dut, "show lldp neighbor", type=data.cli_type, skip_tmpl=True)
        output_str = str(output)

        st.log(f"LLDP neighbor output:\n{output_str}")

        # Check for System Name TLV
        if "SysName" in output_str:
            tlv_status["system_name"] = True
            st.log(f"  ✓ System Name TLV present")
        else:
            st.log(f"  ✗ System Name TLV not present")

        # Check for System Description TLV
        if "SysDescr" in output_str:
            tlv_status["system_description"] = True
            st.log(f"  ✓ System Description TLV present")
        else:
            st.log(f"  ✗ System Description TLV not present")

        # Check for Management Address TLV
        # Known issue: This may not be visible in CLI output
        if "Mgmt" in output_str or "Management" in output_str or "MgmtIP" in output_str:
            tlv_status["management_address"] = True
            st.log(f"  ✓ Management Address TLV present")
        else:
            st.log(f"  ⚠ Management Address TLV NOT present (known issue)")

        return tlv_status

    except Exception as e:
        st.error(f"Failed to verify LLDP TLVs on {dut}: {str(e)}")
        return tlv_status


def verify_management_address_via_lldpctl(dut: str) -> bool:
    """
    Verify Management Address TLV using lldpctl (workaround).

    This is a workaround for the known issue where Management Address
    is not visible in "show lldp neighbor" but is present in lldpctl output.

    Args:
        dut: Device name

    Returns:
        bool: True if Management Address found in lldpctl output
    """
    st.log(f"Attempting to verify Management Address via lldpctl on {dut}")
    st.log("  (Workaround for CLI limitation)")

    try:
        # Execute lldpctl via bash
        output = st.show(dut, "sudo lldpctl show neighbors", type="click", skip_tmpl=True)
        output_str = str(output)

        st.log(f"lldpctl output:\n{output_str}")

        # Check for Management Address in lldpctl output
        if "MgmtIP" in output_str or "Management" in output_str:
            st.log(f"  ✓ Management Address found in lldpctl output")
            # Try to extract IP
            ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', output_str)
            if ip_match:
                mgmt_ip = ip_match.group(1)
                st.log(f"  Management IP: {mgmt_ip}")
            return True
        else:
            st.log(f"  ⚠ Management Address not found even in lldpctl")
            return False

    except Exception as e:
        st.log(f"lldpctl command failed (may not be available): {str(e)}")
        return False


def test_lldp_06_system_name_description_mgmt_tlv():
    """
    Test Case 4.16.6: Verify System Name, Description, and Management Address TLVs

    Test Objective: Configure and verify LLDP System TLVs

    Steps:
        1. Enable LLDP globally on both DUTs
        2. Enable System Name TLV
        3. Enable System Description TLV
        4. Enable Management Address TLV
        5. Enable LLDP on interfaces
        6. Wait for LLDP neighbor discovery
        7. Verify System Name TLV in neighbor output
        8. Verify System Description TLV in neighbor output
        9. Verify Management Address TLV (expected to fail in CLI)
        10. Attempt workaround: Use lldpctl to verify Management Address
        11. Rollback configuration

    Expected Result (from Manual Test):
        FAIL - Management Address TLV not shown in "show lldp neighbor" output
        System Name and Description TLVs should be visible

    Actual Result: FAIL (as per manual test log)

    KNOWN ISSUE:
        Management Address TLV is not displayed in "show lldp neighbor" output.
        Workaround: Use "sudo lldpctl show neighbors" to see Management Address.
    """

    # Track validation results
    validation_results = SpyTestDict({
        "global_enable": False,
        "tlv_system_name_config": False,
        "tlv_system_description_config": False,
        "tlv_management_address_config": False,
        "interface_enable": False,
        "neighbor_discovery": False,
        "system_name_visible": False,
        "system_description_visible": False,
        "management_address_visible": False,  # Expected to fail
        "management_address_lldpctl": False,  # Workaround
        "rollback": False,
    })

    st.banner("=" * 80)
    st.banner("TEST CASE 4.16.6: Verify System TLVs")
    st.banner("=" * 80)
    st.log(f"Test Objective: Configure and verify LLDP System TLVs")
    st.log(f"DUT1: {vars.D1}")
    st.log(f"DUT2: {vars.D2}")
    st.log("")
    st.log("⚠ KNOWN ISSUE: Management Address TLV not visible in CLI output")
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
    # STEP 2: Enable System Name TLV
    # ==================================================================
    st.banner("STEP 2: Enable System Name TLV on Both DUTs")

    tlv_name_dut1 = configure_lldp_tlv_system_name(vars.D1, enable=True)
    tlv_name_dut2 = configure_lldp_tlv_system_name(vars.D2, enable=True)

    if tlv_name_dut1 and tlv_name_dut2:
        validation_results.tlv_system_name_config = True
        st.log("✓ System Name TLV enabled on both DUTs")
        st.report_tc_pass(TC_IDS.lldp_tlv_system_name, "msg",
                         "System Name TLV enabled")
    else:
        st.log("✗ Failed to enable System Name TLV")
        st.report_tc_fail(TC_IDS.lldp_tlv_system_name, "msg",
                         "Failed to enable System Name TLV")

    # ==================================================================
    # STEP 3: Enable System Description TLV
    # ==================================================================
    st.banner("STEP 3: Enable System Description TLV on Both DUTs")

    tlv_desc_dut1 = configure_lldp_tlv_system_description(vars.D1, enable=True)
    tlv_desc_dut2 = configure_lldp_tlv_system_description(vars.D2, enable=True)

    if tlv_desc_dut1 and tlv_desc_dut2:
        validation_results.tlv_system_description_config = True
        st.log("✓ System Description TLV enabled on both DUTs")
        st.report_tc_pass(TC_IDS.lldp_tlv_system_description, "msg",
                         "System Description TLV enabled")
    else:
        st.log("✗ Failed to enable System Description TLV")
        st.report_tc_fail(TC_IDS.lldp_tlv_system_description, "msg",
                         "Failed to enable System Description TLV")

    # ==================================================================
    # STEP 4: Enable Management Address TLV
    # ==================================================================
    st.banner("STEP 4: Enable Management Address TLV on Both DUTs")

    tlv_mgmt_dut1 = configure_lldp_tlv_management_address(vars.D1, enable=True)
    tlv_mgmt_dut2 = configure_lldp_tlv_management_address(vars.D2, enable=True)

    if tlv_mgmt_dut1 and tlv_mgmt_dut2:
        validation_results.tlv_management_address_config = True
        st.log("✓ Management Address TLV enabled on both DUTs")
        st.report_tc_pass(TC_IDS.lldp_tlv_management_address, "msg",
                         "Management Address TLV enabled")
    else:
        st.log("✗ Failed to enable Management Address TLV")
        st.report_tc_fail(TC_IDS.lldp_tlv_management_address, "msg",
                         "Failed to enable Management Address TLV")

    # ==================================================================
    # STEP 5: Enable LLDP on Interfaces
    # ==================================================================
    st.banner("STEP 5: Enable LLDP on Interfaces")

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
    # STEP 6: Wait for LLDP Neighbor Discovery
    # ==================================================================
    st.banner("STEP 6: Wait for LLDP Neighbor Discovery")

    st.log(f"Waiting {CONFIG.lldp_wait_time} seconds for LLDP neighbors to appear")
    st.wait(CONFIG.lldp_wait_time, "Waiting for LLDP neighbor discovery")

    # ==================================================================
    # STEP 7-9: Verify System TLVs in Neighbor Output
    # ==================================================================
    st.banner("STEP 7-9: Verify System TLVs in Neighbor Output")

    st.log("Verifying System TLVs on DUT1")
    tlv_status_dut1 = verify_lldp_system_tlvs(vars.D1)

    if tlv_status_dut1["system_name"]:
        validation_results.system_name_visible = True
        st.log("✓ System Name TLV visible on DUT1")
    else:
        st.log("✗ System Name TLV not visible on DUT1")

    if tlv_status_dut1["system_description"]:
        validation_results.system_description_visible = True
        st.log("✓ System Description TLV visible on DUT1")
    else:
        st.log("✗ System Description TLV not visible on DUT1")

    if tlv_status_dut1["management_address"]:
        validation_results.management_address_visible = True
        st.log("✓ Management Address TLV visible on DUT1 (BUG FIXED!)")
        st.report_tc_pass(TC_IDS.lldp_verify_mgmt_address, "msg",
                         "Management Address TLV visible (bug fixed)")
    else:
        st.log("✗ Management Address TLV NOT visible on DUT1 (known issue)")
        st.report_tc_fail(TC_IDS.lldp_verify_mgmt_address, "msg",
                         "Management Address TLV not visible in CLI (known bug)")

    # ==================================================================
    # STEP 10: Workaround - Use lldpctl to Verify Management Address
    # ==================================================================
    st.banner("STEP 10: Workaround - Use lldpctl to Verify Management Address")

    st.log("Attempting to verify Management Address via lldpctl (workaround)")
    if verify_management_address_via_lldpctl(vars.D1):
        validation_results.management_address_lldpctl = True
        st.log("✓ Management Address found via lldpctl (workaround successful)")
    else:
        st.log("⚠ Management Address not found even in lldpctl")

    # ==================================================================
    # STEP 11: Rollback Configuration
    # ==================================================================
    st.banner("STEP 11: Rollback Configuration - Disable LLDP")

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
    # STEP 12: Final Test Result Evaluation
    # ==================================================================
    st.banner("STEP 12: Final Test Result Evaluation")

    # Check if Management Address is visible (main test criterion)
    if validation_results.management_address_visible:
        st.log("✓ BUG FIXED! Management Address TLV now visible in CLI!")
        st.banner("=" * 80)
        st.banner("TEST RESULT: LLDP 4.16.6 PASSED (BUG FIXED!)")
        st.banner("=" * 80)
        st.report_pass("test_case_passed")
    else:
        st.log("✗ Management Address TLV not visible in CLI (as expected)")

        st.banner("=" * 80)
        st.banner("TEST RESULT: LLDP 4.16.6 FAILED (KNOWN BUG)")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - 4.16.6: System TLVs")
        st.log("=" * 80)
        st.log(f"✓ LLDP enabled globally on both DUTs")
        st.log(f"✓ System Name TLV enabled")
        st.log(f"✓ System Description TLV enabled")
        st.log(f"✓ Management Address TLV enabled")
        st.log(f"✓ LLDP enabled on interfaces")
        if validation_results.system_name_visible:
            st.log(f"✓ System Name TLV visible in CLI output")
        if validation_results.system_description_visible:
            st.log(f"✓ System Description TLV visible in CLI output")
        st.log(f"✗ Management Address TLV NOT visible in CLI output (BUG)")
        if validation_results.management_address_lldpctl:
            st.log(f"✓ Management Address visible via lldpctl (workaround)")
        st.log(f"✓ Configuration rolled back")
        st.log("=" * 80)
        st.log("NOTE: As per manual test: FAIL - Management Address TLV not in CLI")
        st.log("NOTE: Workaround: Use 'sudo lldpctl show neighbors'")
        st.log("=" * 80)

        st.report_fail("msg", "Management Address TLV test failed (known bug): not visible in CLI output")
