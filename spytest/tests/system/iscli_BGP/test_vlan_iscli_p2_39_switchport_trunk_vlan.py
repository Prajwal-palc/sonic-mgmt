"""
VLAN TRUNK SWITCHPORT TEST - SM_ISCLI_P2_39
Bug: 'no switchport trunk allowed Vlan' does not remove the VLAN from the port

Test Case ID : SM_ISCLI_P2_39
Feature      : VLAN
Priority     : P1
Status       : Done (Fix verified)
Author       : Automated from Manual Validation
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \\
    --testbed ./testbeds/testbed_2vs.yaml \\
    tests/system/iscli_BGP/test_vlan_iscli_p2_39_switchport_trunk_vlan.py \\
    --logs-path ./logs/vlan_p2_39_$(date +%F_%H%M%S) \\
    --log-level debug --skip-init-config --ifname-type native

Description:
  Bug Fix Verification for SM_ISCLI_P2_39:
  - Part A: Add VLAN to trunk port → verify VLAN appears on port (T tag)
  - Part B: Remove VLAN from trunk port using 'no switchport trunk allowed Vlan'
            → verify VLAN is removed from port (main bug fix)
  - Part C: Full lifecycle — add multiple VLANs, remove one, verify only
            the correct VLAN is removed (others remain)

  Manual verified behavior (both DUTs):
  - After 'switchport trunk allowed Vlan 100':
      show Vlan → Vlan100  Up  T  Ethernet0
  - After 'no switchport trunk allowed Vlan 100':
      show Vlan → Vlan100  Down  (no ports listed)  ← BUG WAS: still showed T Ethernet0
  - After 'no vlan 100':
      show Vlan → No VLANs configured

Pre-requisites:
  - 2 SONiC devices (DUT1: 192.168.100.202, DUT2: 192.168.100.86)
  - Testbed: testbed_2vs.yaml
  - Clean VLAN configuration (no VLAN 100/101/102 pre-existing)
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.switching.vlan as vlanapi

# ======================================================================
# Global Variables
# ======================================================================
vars = SpyTestDict()
data = SpyTestDict()

# ======================================================================
# Test Configuration
# ======================================================================
CONFIG = SpyTestDict({
    "interface":        "Ethernet0",
    "vlan_id":          "100",
    "vlan_id2":         "101",
    "vlan_id3":         "102",
    "vlan_intf":        "Vlan100",
    "vlan_intf2":       "Vlan101",
    "vlan_intf3":       "Vlan102",
})

# ======================================================================
# Test Case IDs
# ======================================================================
TC_IDS = SpyTestDict({
    "part_a_add_vlan_trunk":    "TC-VLAN-P2-39-001",
    "part_b_remove_vlan_trunk": "TC-VLAN-P2-39-002",
    "part_c_multi_vlan":        "TC-VLAN-P2-39-003",
})


# ======================================================================
# Module Fixture - Setup and Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def vlan_p39_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("SM_ISCLI_P2_39 - VLAN TRUNK SWITCHPORT - MODULE START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    # Pre-condition: ensure clean VLAN state
    vlan_pre_config()

    yield

    # Module cleanup
    st.banner("=" * 80)
    st.banner("SM_ISCLI_P2_39 - MODULE CLEANUP")
    st.banner("=" * 80)
    try:
        vlan_pre_config_cleanup()
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


# ======================================================================
# Pre-configuration
# ======================================================================
def vlan_pre_config():
    """Ensure clean VLAN state on both DUTs before test."""
    st.log("Pre-configuration: Clearing any existing VLAN 100/101/102 configuration")

    for dut in [vars.D1, vars.D2]:
        # Remove VLANs from trunk port first
        _remove_vlan_from_trunk_if_exists(dut, CONFIG.vlan_id)
        _remove_vlan_from_trunk_if_exists(dut, CONFIG.vlan_id2)
        _remove_vlan_from_trunk_if_exists(dut, CONFIG.vlan_id3)
        # Remove VLANs
        _remove_vlan_if_exists(dut, CONFIG.vlan_id)
        _remove_vlan_if_exists(dut, CONFIG.vlan_id2)
        _remove_vlan_if_exists(dut, CONFIG.vlan_id3)

    st.log("Pre-configuration completed - clean state confirmed")


def vlan_pre_config_cleanup():
    """Cleanup: Remove all test VLANs from both DUTs."""
    st.log("Cleanup: Removing VLAN 100/101/102 from both DUTs")

    for dut in [vars.D1, vars.D2]:
        _remove_vlan_from_trunk_if_exists(dut, CONFIG.vlan_id)
        _remove_vlan_from_trunk_if_exists(dut, CONFIG.vlan_id2)
        _remove_vlan_from_trunk_if_exists(dut, CONFIG.vlan_id3)
        _remove_vlan_if_exists(dut, CONFIG.vlan_id)
        _remove_vlan_if_exists(dut, CONFIG.vlan_id2)
        _remove_vlan_if_exists(dut, CONFIG.vlan_id3)

    st.log("Cleanup completed")


# ======================================================================
# Helper Functions
# ======================================================================
def _remove_vlan_from_trunk_if_exists(dut: str, vlan_id: str):
    """Remove VLAN from trunk port if present (safe - no error if not present)."""
    try:
        commands = [
            f"interface {CONFIG.interface}",
            f"no switchport trunk allowed Vlan {vlan_id}",
            "end"
        ]
        st.config(dut, commands, type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"Trunk VLAN cleanup warning on {dut} vlan{vlan_id} (non-critical): {str(e)}")


def _remove_vlan_if_exists(dut: str, vlan_id: str):
    """Remove VLAN if it exists (safe - no error if not present)."""
    try:
        commands = [
            f"no vlan {vlan_id}",
            "end"
        ]
        st.config(dut, commands, type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"VLAN cleanup warning on {dut} vlan{vlan_id} (non-critical): {str(e)}")


def create_vlan(dut: str, vlan_id: str) -> bool:
    """
    Create a VLAN on DUT.

    Matches manual commands:
      configure
      vlan 100
      exit
    """
    st.log(f"Creating VLAN {vlan_id} on {dut}")

    commands = [
        f"vlan {vlan_id}",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"VLAN {vlan_id} created on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to create VLAN {vlan_id} on {dut}: {str(e)}")
        return False


def add_vlan_to_trunk(dut: str, vlan_id: str) -> bool:
    """
    Add VLAN to trunk port.

    Matches manual commands:
      configure
      interface Ethernet 0
        switchport trunk allowed Vlan 100
        no shutdown
      exit
    """
    st.log(f"Adding VLAN {vlan_id} to trunk port {CONFIG.interface} on {dut}")

    commands = [
        f"interface {CONFIG.interface}",
        f"switchport trunk allowed Vlan {vlan_id}",
        "no shutdown",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"VLAN {vlan_id} added to trunk {CONFIG.interface} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to add VLAN {vlan_id} to trunk on {dut}: {str(e)}")
        return False


def remove_vlan_from_trunk(dut: str, vlan_id: str) -> bool:
    """
    Remove VLAN from trunk port using 'no switchport trunk allowed Vlan'.

    This is the main bug fix command being tested.

    Matches manual commands:
      configure
      interface Ethernet 0
        no switchport trunk allowed Vlan 100
      exit
    """
    st.log(f"Removing VLAN {vlan_id} from trunk port {CONFIG.interface} on {dut}")

    commands = [
        f"interface {CONFIG.interface}",
        f"no switchport trunk allowed Vlan {vlan_id}",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"VLAN {vlan_id} removed from trunk {CONFIG.interface} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to remove VLAN {vlan_id} from trunk on {dut}: {str(e)}")
        return False


def verify_vlan_on_trunk(dut: str, vlan_id: str) -> bool:
    """
    Verify VLAN is present on trunk port (T tagged).

    Expected show Vlan output:
      Vlan100   Up   T  Ethernet0   Enable   No

    Matches manual:
      show Vlan → Vlan100  Up  T  Ethernet0
    """
    st.log(f"Verifying VLAN {vlan_id} is on trunk {CONFIG.interface} on {dut}")

    output = st.show(
        dut,
        "show Vlan",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    st.log(f"show Vlan output:\n{output_str[:600]}")

    # Check VLAN entry exists
    if f"Vlan{vlan_id}" not in output_str:
        st.error(f"VLAN {vlan_id} not found in show Vlan output on {dut}")
        return False

    # Check VLAN is tagged (T) on the interface
    # Expected line: Vlan100   Up   T  Ethernet0
    if CONFIG.interface not in output_str:
        st.error(
            f"VLAN {vlan_id} exists but {CONFIG.interface} not listed as tagged port on {dut}. "
            f"VLAN not added to trunk correctly."
        )
        return False

    # Confirm tagged (T) marker is present with the interface
    lines = output_str.splitlines()
    for line in lines:
        if f"Vlan{vlan_id}" in line and CONFIG.interface in line:
            if "T" in line:
                st.log(f"VLAN {vlan_id} confirmed as Tagged on {CONFIG.interface} on {dut}: {line.strip()}")
                return True

    st.error(
        f"VLAN {vlan_id} on {dut}: interface present but 'T' (Tagged) marker not confirmed. "
        f"Check output: {output_str[:300]}"
    )
    return False


def verify_vlan_removed_from_trunk(dut: str, vlan_id: str) -> bool:
    """
    Verify VLAN is removed from trunk port.

    After 'no switchport trunk allowed Vlan 100':
    - VLAN entry should still exist (vlan itself not deleted)
    - But NO port should be listed under it
    - Status should be 'Down' (no active port members)

    Bug behavior (before fix):
      show Vlan → Vlan100  Up  T  Ethernet0  ← still tagged! bug!

    Fixed behavior:
      show Vlan → Vlan100  Down              ← no ports listed

    Matches manual:
      show Vlan → Vlan100  Down  (no Ethernet0)
    """
    st.log(f"Verifying VLAN {vlan_id} is removed from trunk {CONFIG.interface} on {dut}")

    output = st.show(
        dut,
        "show Vlan",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    st.log(f"show Vlan output after removal:\n{output_str[:600]}")

    # VLAN should still exist (just removed from port)
    if f"Vlan{vlan_id}" not in output_str:
        st.error(
            f"VLAN {vlan_id} completely missing from show Vlan on {dut}. "
            f"Expected VLAN to still exist, just removed from port."
        )
        return False

    # BUG CHECK: if Ethernet0 still shows as tagged on this VLAN = bug not fixed
    lines = output_str.splitlines()
    for line in lines:
        if f"Vlan{vlan_id}" in line and CONFIG.interface in line:
            st.error(
                f"BUG DETECTED: VLAN {vlan_id} still shows {CONFIG.interface} as tagged "
                f"after 'no switchport trunk allowed Vlan {vlan_id}' on {dut}! "
                f"SM_ISCLI_P2_39 not fixed. Line: {line.strip()}"
            )
            return False

    # Verify VLAN shows Down (no port members)
    for line in lines:
        if f"Vlan{vlan_id}" in line:
            if "Down" in line:
                st.log(
                    f"VLAN {vlan_id} correctly shows 'Down' with no ports on {dut}: {line.strip()}"
                )
                return True
            # Also accept if line just has Vlan with no interface listed
            if CONFIG.interface not in line:
                st.log(
                    f"VLAN {vlan_id} correctly has no port member on {dut}: {line.strip()}"
                )
                return True

    st.error(f"VLAN {vlan_id} trunk removal verification inconclusive on {dut}. Output: {output_str[:300]}")
    return False


def verify_vlan_deleted(dut: str, vlan_id: str) -> bool:
    """
    Verify VLAN is completely deleted from the device.

    After 'no vlan 100':
      show Vlan → No VLANs configured  (or Vlan100 not listed)
    """
    st.log(f"Verifying VLAN {vlan_id} is deleted on {dut}")

    output = st.show(
        dut,
        "show Vlan",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    if f"Vlan{vlan_id}" in output_str:
        st.error(f"VLAN {vlan_id} still present after 'no vlan' on {dut}")
        return False

    st.log(f"VLAN {vlan_id} confirmed deleted on {dut}")
    return True


def verify_vlan_still_on_trunk(dut: str, vlan_id: str) -> bool:
    """
    Verify a VLAN is still on the trunk port (used in Part C to confirm
    other VLANs are not affected when one is removed).
    """
    st.log(f"Verifying VLAN {vlan_id} is still on trunk {CONFIG.interface} on {dut}")
    return verify_vlan_on_trunk(dut, vlan_id)


# ======================================================================
# Main Test Function
# ======================================================================
def test_vlan_p2_39_switchport_trunk_vlan():
    """
    SM_ISCLI_P2_39: 'no switchport trunk allowed Vlan' does not remove VLAN

    Bug: After adding a VLAN to a trunk port with 'switchport trunk allowed Vlan X',
         running 'no switchport trunk allowed Vlan X' does NOT remove it.
         The VLAN still appears as tagged on the port.

    Fix status: P1 - Done (Fix verified on both DUTs)

    Test Parts:
      Part A: Add VLAN 100 to trunk port → verify Tagged (T) on Ethernet0
      Part B: Remove VLAN 100 from trunk → verify NOT on Ethernet0 (main bug fix)
      Part C: Multi-VLAN scenario — add 100/101/102, remove 101, verify
              only 101 is removed and 100/102 remain

    Runs on both DUT1 and DUT2 independently.
    """
    st.banner("=" * 80)
    st.banner("SM_ISCLI_P2_39: VLAN TRUNK SWITCHPORT REMOVAL BUG FIX VERIFICATION")
    st.banner("=" * 80)

    dut_list = [vars.D1, vars.D2]

    # ================================================================
    # PART A: Add VLAN to Trunk Port
    # ================================================================
    st.banner("PART A: ADD VLAN TO TRUNK PORT")
    st.log("Verify: 'switchport trunk allowed Vlan 100' adds VLAN as Tagged on Ethernet0")

    for dut in dut_list:
        st.banner(f"Part A - DUT: {dut}")

        # Step A1: Create VLAN 100
        st.log(f"[A1] Creating VLAN {CONFIG.vlan_id} on {dut}")
        if not create_vlan(dut, CONFIG.vlan_id):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_a_vlan_create_failed")
            st.report_tc_fail(TC_IDS.part_a_add_vlan_trunk, "msg",
                              f"Part A: Failed to create VLAN {CONFIG.vlan_id} on {dut}")
            st.report_fail("msg", f"Part A: VLAN creation failed on {dut}")

        # Step A2: Add VLAN to trunk port
        st.log(f"[A2] Adding VLAN {CONFIG.vlan_id} to trunk {CONFIG.interface}")
        if not add_vlan_to_trunk(dut, CONFIG.vlan_id):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_a_trunk_add_failed")
            st.report_tc_fail(TC_IDS.part_a_add_vlan_trunk, "msg",
                              f"Part A: Failed to add VLAN to trunk on {dut}")
            st.report_fail("msg", f"Part A: Trunk VLAN add failed on {dut}")

        st.wait(2, "Waiting for VLAN to be active on trunk")

        # Step A3: Verify VLAN is tagged on trunk port
        st.log(f"[A3] Verifying VLAN {CONFIG.vlan_id} is tagged (T) on {CONFIG.interface}")
        if not verify_vlan_on_trunk(dut, CONFIG.vlan_id):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_a_vlan_not_on_trunk")
            st.report_tc_fail(TC_IDS.part_a_add_vlan_trunk, "msg",
                              f"Part A: VLAN {CONFIG.vlan_id} not Tagged on trunk {dut}")
            st.report_fail("msg", f"Part A: VLAN not tagged on trunk port on {dut}")

        st.log(f"Part A PASSED on {dut}")

    st.report_tc_pass(TC_IDS.part_a_add_vlan_trunk, "msg",
                      "Part A: VLAN added as Tagged on trunk port on both DUTs")

    # ================================================================
    # PART B: Remove VLAN from Trunk Port (Main Bug Fix)
    # ================================================================
    st.banner("PART B: REMOVE VLAN FROM TRUNK PORT (MAIN BUG FIX)")
    st.log("Verify: 'no switchport trunk allowed Vlan 100' removes VLAN from Ethernet0")

    for dut in dut_list:
        st.banner(f"Part B - DUT: {dut}")

        # Step B1: Remove VLAN from trunk port (the bug fix command)
        st.log(f"[B1] Running 'no switchport trunk allowed Vlan {CONFIG.vlan_id}' on {dut}")
        st.log(f"      THIS IS THE MAIN BUG FIX VERIFICATION")
        if not remove_vlan_from_trunk(dut, CONFIG.vlan_id):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_b_trunk_remove_failed")
            st.report_tc_fail(TC_IDS.part_b_remove_vlan_trunk, "msg",
                              f"Part B: 'no switchport trunk allowed Vlan' command failed on {dut}")
            st.report_fail("msg", f"Part B: Trunk VLAN remove command failed on {dut}")

        # Step B2: Verify VLAN is removed from trunk port (CRITICAL BUG CHECK)
        st.log(f"[B2] CRITICAL CHECK: Verifying VLAN {CONFIG.vlan_id} removed from {CONFIG.interface}")
        if not verify_vlan_removed_from_trunk(dut, CONFIG.vlan_id):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_b_vlan_still_on_trunk")
            st.report_tc_fail(TC_IDS.part_b_remove_vlan_trunk, "msg",
                              f"Part B FAILED: VLAN {CONFIG.vlan_id} still tagged on "
                              f"{CONFIG.interface} after removal on {dut} - SM_ISCLI_P2_39 NOT FIXED!")
            st.report_fail("msg",
                           f"Part B: VLAN still on trunk after 'no switchport' on {dut} - BUG NOT FIXED!")

        # Step B3: Delete VLAN completely and verify
        st.log(f"[B3] Deleting VLAN {CONFIG.vlan_id} completely from {dut}")
        commands = [f"no vlan {CONFIG.vlan_id}", "end"]
        st.config(dut, commands, type='klish', skip_error_check=False)

        if not verify_vlan_deleted(dut, CONFIG.vlan_id):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_b_vlan_delete_failed")
            st.report_tc_fail(TC_IDS.part_b_remove_vlan_trunk, "msg",
                              f"Part B: VLAN {CONFIG.vlan_id} not deleted on {dut}")
            st.report_fail("msg", f"Part B: VLAN deletion failed on {dut}")

        st.log(f"Part B PASSED on {dut}")

    st.report_tc_pass(TC_IDS.part_b_remove_vlan_trunk, "msg",
                      "Part B: VLAN removed from trunk port successfully on both DUTs")

    # ================================================================
    # PART C: Multi-VLAN Scenario
    # ================================================================
    st.banner("PART C: MULTI-VLAN SCENARIO - SELECTIVE VLAN REMOVAL")
    st.log("Verify: Removing one VLAN from trunk does NOT affect other VLANs")
    st.log(f"Add VLANs: {CONFIG.vlan_id}, {CONFIG.vlan_id2}, {CONFIG.vlan_id3}")
    st.log(f"Remove only: {CONFIG.vlan_id2}")
    st.log(f"Verify: {CONFIG.vlan_id} and {CONFIG.vlan_id3} still on trunk")

    for dut in dut_list:
        st.banner(f"Part C - DUT: {dut}")

        # Step C1: Create all 3 VLANs
        for vlan_id in [CONFIG.vlan_id, CONFIG.vlan_id2, CONFIG.vlan_id3]:
            st.log(f"[C1] Creating VLAN {vlan_id} on {dut}")
            if not create_vlan(dut, vlan_id):
                st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_c_vlan_create_failed")
                st.report_tc_fail(TC_IDS.part_c_multi_vlan, "msg",
                                  f"Part C: Failed to create VLAN {vlan_id} on {dut}")
                st.report_fail("msg", f"Part C: VLAN {vlan_id} creation failed on {dut}")

        # Step C2: Add all 3 VLANs to trunk
        for vlan_id in [CONFIG.vlan_id, CONFIG.vlan_id2, CONFIG.vlan_id3]:
            st.log(f"[C2] Adding VLAN {vlan_id} to trunk {CONFIG.interface} on {dut}")
            if not add_vlan_to_trunk(dut, vlan_id):
                st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_c_trunk_add_failed")
                st.report_tc_fail(TC_IDS.part_c_multi_vlan, "msg",
                                  f"Part C: Failed to add VLAN {vlan_id} to trunk on {dut}")
                st.report_fail("msg", f"Part C: VLAN {vlan_id} trunk add failed on {dut}")

        st.wait(2, "Waiting for VLANs to be active on trunk")

        # Step C3: Verify all 3 VLANs are on trunk
        for vlan_id in [CONFIG.vlan_id, CONFIG.vlan_id2, CONFIG.vlan_id3]:
            st.log(f"[C3] Verifying VLAN {vlan_id} on trunk before removal")
            if not verify_vlan_on_trunk(dut, vlan_id):
                st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_c_verify_before_failed")
                st.report_tc_fail(TC_IDS.part_c_multi_vlan, "msg",
                                  f"Part C: VLAN {vlan_id} not on trunk before removal test on {dut}")
                st.report_fail("msg", f"Part C: Pre-removal verify failed for VLAN {vlan_id} on {dut}")

        # Step C4: Remove only VLAN 101 (middle one)
        st.log(f"[C4] Removing ONLY VLAN {CONFIG.vlan_id2} from trunk (100 and 102 should remain)")
        if not remove_vlan_from_trunk(dut, CONFIG.vlan_id2):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_c_remove_failed")
            st.report_tc_fail(TC_IDS.part_c_multi_vlan, "msg",
                              f"Part C: Failed to remove VLAN {CONFIG.vlan_id2} from trunk on {dut}")
            st.report_fail("msg", f"Part C: Selective VLAN remove failed on {dut}")

        # Step C5: Verify VLAN 101 is removed from trunk
        st.log(f"[C5] Verifying VLAN {CONFIG.vlan_id2} removed from trunk")
        if not verify_vlan_removed_from_trunk(dut, CONFIG.vlan_id2):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_c_vlan101_still_on_trunk")
            st.report_tc_fail(TC_IDS.part_c_multi_vlan, "msg",
                              f"Part C: VLAN {CONFIG.vlan_id2} still on trunk after removal on {dut}")
            st.report_fail("msg",
                           f"Part C: VLAN {CONFIG.vlan_id2} not removed from trunk on {dut}")

        # Step C6: Verify VLAN 100 and 102 still on trunk (not affected)
        st.log(f"[C6] Verifying VLAN {CONFIG.vlan_id} still on trunk (should not be affected)")
        if not verify_vlan_still_on_trunk(dut, CONFIG.vlan_id):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_c_vlan100_removed_unexpectedly")
            st.report_tc_fail(TC_IDS.part_c_multi_vlan, "msg",
                              f"Part C: VLAN {CONFIG.vlan_id} unexpectedly removed from trunk on {dut}")
            st.report_fail("msg",
                           f"Part C: VLAN {CONFIG.vlan_id} affected by removal of {CONFIG.vlan_id2} on {dut}")

        st.log(f"[C6] Verifying VLAN {CONFIG.vlan_id3} still on trunk (should not be affected)")
        if not verify_vlan_still_on_trunk(dut, CONFIG.vlan_id3):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p39_part_c_vlan102_removed_unexpectedly")
            st.report_tc_fail(TC_IDS.part_c_multi_vlan, "msg",
                              f"Part C: VLAN {CONFIG.vlan_id3} unexpectedly removed from trunk on {dut}")
            st.report_fail("msg",
                           f"Part C: VLAN {CONFIG.vlan_id3} affected by removal of {CONFIG.vlan_id2} on {dut}")

        st.log(f"Part C PASSED on {dut}")

    st.report_tc_pass(TC_IDS.part_c_multi_vlan, "msg",
                      "Part C: Selective VLAN removal works correctly on both DUTs")

    # ================================================================
    # FINAL CLEANUP
    # ================================================================
    st.banner("FINAL CLEANUP")
    for dut in [vars.D1, vars.D2]:
        for vlan_id in [CONFIG.vlan_id, CONFIG.vlan_id2, CONFIG.vlan_id3]:
            _remove_vlan_from_trunk_if_exists(dut, vlan_id)
            _remove_vlan_if_exists(dut, vlan_id)
        st.log(f"Cleanup done on {dut}")

    # ================================================================
    # TEST SUMMARY
    # ================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: SM_ISCLI_P2_39 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - SM_ISCLI_P2_39: VLAN Trunk Switchport Removal Bug Fix Verification")
    st.log("=" * 80)
    st.log(f"DUT1: {vars.D1}  |  DUT2: {vars.D2}")
    st.log(f"Interface : {CONFIG.interface}")
    st.log(f"VLAN IDs  : {CONFIG.vlan_id}, {CONFIG.vlan_id2}, {CONFIG.vlan_id3}")
    st.log("")
    st.log("Part A - Add VLAN to Trunk:")
    st.log(f"  'switchport trunk allowed Vlan 100'  : PASS - Vlan100 Tagged (T) on Ethernet0")
    st.log("")
    st.log("Part B - Remove VLAN from Trunk (MAIN BUG FIX):")
    st.log(f"  'no switchport trunk allowed Vlan 100': PASS - Vlan100 removed from Ethernet0")
    st.log(f"  show Vlan shows Vlan100 Down (no ports): PASS")
    st.log("")
    st.log("Part C - Multi-VLAN Selective Removal:")
    st.log(f"  Remove Vlan101 only                  : PASS - Vlan101 removed from trunk")
    st.log(f"  Vlan100 and Vlan102 unaffected        : PASS - still Tagged on Ethernet0")
    st.log("")
    st.log("Bug SM_ISCLI_P2_39: CONFIRMED FIXED")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
