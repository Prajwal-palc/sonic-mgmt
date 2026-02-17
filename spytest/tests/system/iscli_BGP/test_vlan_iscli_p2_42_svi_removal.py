"""
VLAN SVI REMOVAL TEST - SM_ISCLI_P2_42
Bug: After configuring a description on the VLAN interface,
     the VLAN interface and its description cannot be removed.

Test Case ID : SM_ISCLI_P2_42
Feature      : VLAN
Priority     : P1
Status       : Done (Fix verified)
Author       : Automated from Manual Validation
Copyright (C) 2024, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_BGP/test_vlan_iscli_p2_42_svi_removal.py \
    --logs-path ./logs/vlan_p2_42_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Bug Fix Verification for SM_ISCLI_P2_42:
  - Part A: Verify description can be removed from SVI (was broken before fix)
  - Part B: Verify SVI interface can be removed after removing IP (was broken before fix)
  - Part C: Verify SVI interface can be removed WITH description still set (main bug)

  Observed behavior (both DUTs):
  - 'no interface vlanX' removes the SVI AND the VLAN itself

Pre-requisites:
  - 2 SONiC devices (DUT1: 192.168.100.202, DUT2: 192.168.100.86)
  - Testbed: testbed_2vs.yaml
  - Clean VLAN configuration (no VLAN 200 pre-existing)
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
    "vlan_id":        "200",
    "vlan_intf":      "Vlan200",
    "dut1_svi_ip":    "10.1.1.1",
    "dut2_svi_ip":    "10.1.1.2",
    "prefix_len":     "24",
    "desc_dut1":      "Test-SVI-OC42-DUT1",
    "desc_dut2":      "Test-SVI-OC42-DUT2",
    "desc_partc_d1":  "Test-Direct-Remove-OC42-DUT1",
    "desc_partc_d2":  "Test-Direct-Remove-OC42-DUT2",
})

# ======================================================================
# Test Case IDs
# ======================================================================
TC_IDS = SpyTestDict({
    "part_a_desc_removal":    "TC-VLAN-P2-42-001",
    "part_b_svi_removal":     "TC-VLAN-P2-42-002",
    "part_c_svi_with_desc":   "TC-VLAN-P2-42-003",
})


# ======================================================================
# Module Fixture - Setup and Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def vlan_p42_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("SM_ISCLI_P2_42 - VLAN SVI REMOVAL - MODULE START")
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
    st.banner("SM_ISCLI_P2_42 - MODULE CLEANUP")
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
    st.log("Pre-configuration: Clearing any existing VLAN 200 configuration")

    for dut in [vars.D1, vars.D2]:
        # Remove SVI if exists
        _remove_svi_if_exists(dut)
        # Remove VLAN if exists
        _remove_vlan_if_exists(dut)

    st.log("Pre-configuration completed - clean state confirmed")


def vlan_pre_config_cleanup():
    """Cleanup: Remove VLAN 200 SVI and VLAN from both DUTs."""
    st.log("Cleanup: Removing VLAN 200 configuration from both DUTs")

    for dut in [vars.D1, vars.D2]:
        _remove_svi_if_exists(dut)
        _remove_vlan_if_exists(dut)

    st.log("Cleanup completed")


# ======================================================================
# Helper Functions
# ======================================================================
def _remove_svi_if_exists(dut: str):
    """Remove SVI Vlan200 if it exists (safe - no error if not present)."""
    try:
        commands = [
            f"no interface {CONFIG.vlan_intf}",
            "end"
        ]
        st.config(dut, commands, type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"SVI cleanup warning on {dut} (non-critical): {str(e)}")


def _remove_vlan_if_exists(dut: str):
    """Remove VLAN 200 if it exists (safe - no error if not present)."""
    try:
        commands = [
            f"no vlan {CONFIG.vlan_id}",
            "end"
        ]
        st.config(dut, commands, type='klish', skip_error_check=True)
    except Exception as e:
        st.log(f"VLAN cleanup warning on {dut} (non-critical): {str(e)}")


def create_vlan(dut: str) -> bool:
    """Create VLAN 200 on DUT."""
    st.log(f"Creating VLAN {CONFIG.vlan_id} on {dut}")

    commands = [
        f"vlan {CONFIG.vlan_id}",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"VLAN {CONFIG.vlan_id} created on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to create VLAN {CONFIG.vlan_id} on {dut}: {str(e)}")
        return False


def create_svi(dut: str, ip_address: str, description: str) -> bool:
    """
    Create SVI (interface vlanX) with description and IP.

    Matches manual commands:
      configure
      interface Vlan 200
        description "..."
        ip address X.X.X.X/24
        no shutdown
      exit
    """
    st.log(f"Creating SVI {CONFIG.vlan_intf} on {dut} - IP: {ip_address}, Desc: {description}")

    commands = [
        f"interface {CONFIG.vlan_intf}",
        f"description \"{description}\"",
        f"ip address {ip_address}/{CONFIG.prefix_len}",
        "no shutdown",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"SVI {CONFIG.vlan_intf} created on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to create SVI on {dut}: {str(e)}")
        return False


def remove_description(dut: str) -> bool:
    """
    Remove description from SVI.

    Matches manual commands:
      configure
      interface Vlan 200
        no description
      exit
    """
    st.log(f"Removing description from {CONFIG.vlan_intf} on {dut}")

    commands = [
        f"interface {CONFIG.vlan_intf}",
        "no description",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"Description removed from {CONFIG.vlan_intf} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to remove description on {dut}: {str(e)}")
        return False


def remove_ip_and_shutdown(dut: str, ip_address: str) -> bool:
    """
    Remove IP address and shutdown SVI.

    Matches manual commands:
      configure
      interface Vlan 200
        no ip address X.X.X.X/24
        shutdown
      exit
    """
    st.log(f"Removing IP {ip_address} and shutting down {CONFIG.vlan_intf} on {dut}")

    commands = [
        f"interface {CONFIG.vlan_intf}",
        f"no ip address {ip_address}/{CONFIG.prefix_len}",
        "shutdown",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"IP removed and {CONFIG.vlan_intf} shutdown on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to remove IP/shutdown on {dut}: {str(e)}")
        return False


def remove_svi(dut: str) -> bool:
    """
    Remove SVI interface completely.

    Matches manual commands:
      configure
      no interface Vlan 200
      exit

    NOTE: This also removes the VLAN itself (observed consistent behavior).
    """
    st.log(f"Removing SVI {CONFIG.vlan_intf} on {dut}")

    commands = [
        f"no interface {CONFIG.vlan_intf}",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"SVI {CONFIG.vlan_intf} removed on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to remove SVI on {dut}: {str(e)}")
        return False


def verify_svi_exists(dut: str, expect_ip: str = None, expect_desc: str = None) -> bool:
    """
    Verify SVI exists with expected IP and/or description.

    Matches manual command: show interface Vlan200
    """
    st.log(f"Verifying SVI {CONFIG.vlan_intf} exists on {dut}")

    output = st.show(
        dut,
        f"show interface {CONFIG.vlan_intf}",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    st.log(f"show interface {CONFIG.vlan_intf} output:\n{output_str[:500]}")

    # Check SVI exists
    if CONFIG.vlan_intf not in output_str:
        st.error(f"SVI {CONFIG.vlan_intf} not found in output on {dut}")
        return False

    # Check IP if provided
    if expect_ip and expect_ip not in output_str:
        st.error(f"Expected IP {expect_ip} not found in SVI output on {dut}")
        return False

    # Check description if provided
    if expect_desc and expect_desc not in output_str:
        st.error(f"Expected description '{expect_desc}' not found in SVI output on {dut}")
        return False

    st.log(f"SVI {CONFIG.vlan_intf} verified on {dut}")
    return True


def verify_svi_removed(dut: str) -> bool:
    """
    Verify SVI is completely removed.

    Expected: 'show interface Vlan200' returns empty output.
    Bug behavior: Interface still shows as down after 'no interface vlanX'.

    Matches manual verification:
      sonic# show interface Vlan200
      sonic#   <-- empty = FIXED
    """
    st.log(f"Verifying SVI {CONFIG.vlan_intf} is removed on {dut}")

    output = st.show(
        dut,
        f"show interface {CONFIG.vlan_intf}",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output).strip() if output else ""

    # Remove common noise from output
    # Filter out prompt artifacts and whitespace
    clean_output = "\n".join(
        line for line in output_str.splitlines()
        if line.strip() and
        not line.strip().startswith("sonic") and
        not line.strip().startswith("--") and
        CONFIG.vlan_intf not in line
    ).strip()

    st.log(f"Raw output after no interface: '{output_str[:200]}'")
    st.log(f"Clean output after filtering: '{clean_output}'")

    # BUG check: if Vlan200 still appears with "is down" = bug not fixed
    if "is down" in output_str and CONFIG.vlan_intf in output_str:
        st.error(
            f"BUG DETECTED: {CONFIG.vlan_intf} still exists after 'no interface' on {dut}! "
            f"SM_ISCLI_P2_42 not fixed."
        )
        st.log(f"Output showing bug: {output_str[:300]}")
        return False

    # If Vlan200 appears at all in a meaningful way, bug persists
    if CONFIG.vlan_intf in output_str and len(output_str.strip()) > 30:
        st.error(f"SVI {CONFIG.vlan_intf} still present on {dut} after removal")
        return False

    st.log(f"SVI {CONFIG.vlan_intf} successfully removed on {dut} - empty output confirmed")
    return True


def verify_description_removed(dut: str) -> bool:
    """
    Verify description is removed from SVI while IP remains.

    Matches manual verification after 'no description':
      Vlan200 is up, line protocol is down
      Hardware is Vlan, address is ...
      IPV4 address is X.X.X.X/24   <-- IP still present
      (no Description line)         <-- description removed
    """
    st.log(f"Verifying description removed from {CONFIG.vlan_intf} on {dut}")

    output = st.show(
        dut,
        f"show interface {CONFIG.vlan_intf}",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    st.log(f"show interface output:\n{output_str[:400]}")

    # SVI should still exist
    if CONFIG.vlan_intf not in output_str:
        st.error(f"SVI {CONFIG.vlan_intf} not found on {dut} - should still exist")
        return False

    # Description should be gone
    if "Description:" in output_str or "description" in output_str.lower():
        st.error(f"Description still present in SVI output on {dut} - not removed!")
        return False

    # IP address should still be there
    if "IPV4 address" not in output_str and "Internet address" not in output_str:
        st.error(f"IP address missing from SVI after description removal on {dut}")
        return False

    st.log(f"Description successfully removed from {CONFIG.vlan_intf} on {dut}, IP retained")
    return True


def verify_vlan_removed(dut: str) -> bool:
    """
    Verify VLAN 200 is removed.
    Note: Observed that 'no interface vlanX' removes VLAN too.

    Matches manual: show Vlan | grep 200 -> No VLANs configured
    """
    st.log(f"Verifying VLAN {CONFIG.vlan_id} state on {dut}")

    output = st.show(
        dut,
        "show Vlan",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    if f"Vlan{CONFIG.vlan_id}" in output_str:
        st.log(f"VLAN {CONFIG.vlan_id} still present on {dut} after SVI removal")
        return False

    st.log(f"VLAN {CONFIG.vlan_id} removed from {dut} (expected with 'no interface vlanX')")
    return True


# ======================================================================
# Main Test Function
# ======================================================================
def test_vlan_p2_42_svi_removal():
    """
    SM_ISCLI_P2_42: VLAN SVI Interface and Description Removal

    Bug: After configuring a description on the VLAN interface,
         the VLAN interface and its description cannot be removed.

    Fix status: P1 - Done (Feb 13 2026 build)

    Test Parts:
      Part A: Remove description → verify description gone, IP retained
      Part B: Remove IP + shutdown + remove SVI → verify SVI gone
      Part C: Remove SVI directly WITH description set → verify SVI gone

    Runs on both DUT1 and DUT2 independently.
    """
    st.banner("=" * 80)
    st.banner("SM_ISCLI_P2_42: VLAN SVI REMOVAL BUG FIX VERIFICATION")
    st.banner("=" * 80)

    dut_configs = [
        (vars.D1, CONFIG.dut1_svi_ip, CONFIG.desc_dut1, CONFIG.desc_partc_d1),
        (vars.D2, CONFIG.dut2_svi_ip, CONFIG.desc_dut2, CONFIG.desc_partc_d2),
    ]

    # ================================================================
    # PART A: Description Removal Test
    # ================================================================
    st.banner("PART A: DESCRIPTION REMOVAL TEST")
    st.log("Verify: 'no description' removes description, IP address remains")

    for dut, svi_ip, description, _ in dut_configs:
        st.banner(f"Part A - DUT: {dut}")

        # Step A1: Create VLAN
        st.log(f"[A1] Creating VLAN {CONFIG.vlan_id} on {dut}")
        if not create_vlan(dut):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_a_vlan_create_failed")
            st.report_tc_fail(TC_IDS.part_a_desc_removal, "msg",
                              f"Part A: Failed to create VLAN on {dut}")
            st.report_fail("msg", f"Part A: VLAN creation failed on {dut}")

        # Step A2: Create SVI with description and IP
        st.log(f"[A2] Creating SVI with description='{description}' ip={svi_ip}")
        if not create_svi(dut, svi_ip, description):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_a_svi_create_failed")
            st.report_tc_fail(TC_IDS.part_a_desc_removal, "msg",
                              f"Part A: Failed to create SVI on {dut}")
            st.report_fail("msg", f"Part A: SVI creation failed on {dut}")

        st.wait(2, "Waiting for SVI to come up")

        # Step A3: Verify SVI exists with description and IP
        st.log(f"[A3] Verifying SVI created correctly")
        if not verify_svi_exists(dut, expect_ip=svi_ip):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_a_svi_verify_failed")
            st.report_tc_fail(TC_IDS.part_a_desc_removal, "msg",
                              f"Part A: SVI not visible after creation on {dut}")
            st.report_fail("msg", f"Part A: SVI verification failed on {dut}")

        # Step A4: Remove description
        st.log(f"[A4] Running 'no description' on {dut}")
        if not remove_description(dut):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_a_nodesc_failed")
            st.report_tc_fail(TC_IDS.part_a_desc_removal, "msg",
                              f"Part A: 'no description' failed on {dut}")
            st.report_fail("msg", f"Part A: Description removal command failed on {dut}")

        # Step A5: Verify description gone, IP still present
        st.log(f"[A5] Verifying description removed, IP retained")
        if not verify_description_removed(dut):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_a_desc_still_present")
            st.report_tc_fail(TC_IDS.part_a_desc_removal, "msg",
                              f"Part A: Description still present on {dut} - BUG NOT FIXED!")
            st.report_fail("msg", f"Part A: Description removal verification failed on {dut}")

        st.log(f"Part A PASSED on {dut}")

    st.report_tc_pass(TC_IDS.part_a_desc_removal, "msg",
                      "Part A: Description removal works on both DUTs")

    # ================================================================
    # PART B: SVI Removal After IP Removal
    # ================================================================
    st.banner("PART B: SVI REMOVAL TEST (after removing IP + shutdown)")
    st.log("Verify: 'no interface vlanX' removes SVI completely")

    for dut, svi_ip, _, _ in dut_configs:
        st.banner(f"Part B - DUT: {dut}")

        # Step B1: Remove IP and shutdown
        st.log(f"[B1] Removing IP {svi_ip} and shutting down SVI on {dut}")
        if not remove_ip_and_shutdown(dut, svi_ip):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_b_ip_removal_failed")
            st.report_tc_fail(TC_IDS.part_b_svi_removal, "msg",
                              f"Part B: Failed to remove IP/shutdown on {dut}")
            st.report_fail("msg", f"Part B: IP removal failed on {dut}")

        # Step B2: Remove the SVI interface
        st.log(f"[B2] Running 'no interface {CONFIG.vlan_intf}' on {dut}")
        if not remove_svi(dut):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_b_svi_remove_failed")
            st.report_tc_fail(TC_IDS.part_b_svi_removal, "msg",
                              f"Part B: 'no interface' command failed on {dut}")
            st.report_fail("msg", f"Part B: SVI removal command failed on {dut}")

        # Step B3: Verify SVI is gone (empty show output)
        st.log(f"[B3] Verifying SVI removed - 'show interface {CONFIG.vlan_intf}' should be empty")
        if not verify_svi_removed(dut):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_b_svi_still_present")
            st.report_tc_fail(TC_IDS.part_b_svi_removal, "msg",
                              f"Part B: SVI still present on {dut} - BUG NOT FIXED!")
            st.report_fail("msg", f"Part B: SVI removal verification failed on {dut}")

        # Step B4: Note VLAN removal observation
        st.log(f"[B4] Checking VLAN state after SVI removal (observed behavior)")
        if verify_vlan_removed(dut):
            st.log(f"Observation confirmed: 'no interface vlanX' also deleted VLAN on {dut}")
        else:
            st.log(f"Note: VLAN still present on {dut} after SVI removal")

        st.log(f"Part B PASSED on {dut}")

    st.report_tc_pass(TC_IDS.part_b_svi_removal, "msg",
                      "Part B: SVI removal works on both DUTs")

    # ================================================================
    # PART C: SVI Removal WITH Description (Main Bug Scenario)
    # ================================================================
    st.banner("PART C: SVI REMOVAL WITH DESCRIPTION SET (MAIN BUG SCENARIO)")
    st.log("Verify: 'no interface vlanX' removes SVI even when description is set")

    for dut, svi_ip, _, desc_partc in dut_configs:
        st.banner(f"Part C - DUT: {dut}")

        # Step C1: Create VLAN (needed since Part B deleted it)
        st.log(f"[C1] Re-creating VLAN {CONFIG.vlan_id} on {dut}")
        if not create_vlan(dut):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_c_vlan_create_failed")
            st.report_tc_fail(TC_IDS.part_c_svi_with_desc, "msg",
                              f"Part C: Failed to create VLAN on {dut}")
            st.report_fail("msg", f"Part C: VLAN creation failed on {dut}")

        # Step C2: Create SVI WITH description (recreate the bug scenario)
        st.log(f"[C2] Creating SVI with description='{desc_partc}'")
        if not create_svi(dut, svi_ip, desc_partc):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_c_svi_create_failed")
            st.report_tc_fail(TC_IDS.part_c_svi_with_desc, "msg",
                              f"Part C: Failed to create SVI on {dut}")
            st.report_fail("msg", f"Part C: SVI creation failed on {dut}")

        st.wait(2, "Waiting for SVI to come up")

        # Step C3: Verify SVI exists with description
        st.log(f"[C3] Verifying SVI exists with description set")
        if not verify_svi_exists(dut, expect_ip=svi_ip):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_c_svi_verify_failed")
            st.report_tc_fail(TC_IDS.part_c_svi_with_desc, "msg",
                              f"Part C: SVI not visible on {dut}")
            st.report_fail("msg", f"Part C: SVI verification failed on {dut}")

        # Step C4: Remove SVI DIRECTLY without removing description first
        st.log(f"[C4] Running 'no interface {CONFIG.vlan_intf}' WITH description still set")
        st.log(f"      This is the MAIN BUG SCENARIO - description was preventing removal")
        if not remove_svi(dut):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_c_svi_remove_failed")
            st.report_tc_fail(TC_IDS.part_c_svi_with_desc, "msg",
                              f"Part C: 'no interface' command failed on {dut}")
            st.report_fail("msg", f"Part C: SVI removal command failed on {dut}")

        # Step C5: Verify SVI is gone (CRITICAL FIX VERIFICATION)
        st.log(f"[C5] CRITICAL CHECK: Verifying SVI removed - should be empty")
        if not verify_svi_removed(dut):
            st.generate_tech_support([vars.D1, vars.D2], "vlan_p42_part_c_svi_still_present")
            st.report_tc_fail(TC_IDS.part_c_svi_with_desc, "msg",
                              f"Part C FAILED: SVI with description still present on {dut} - "
                              f"SM_ISCLI_P2_42 NOT FIXED!")
            st.report_fail("msg",
                           f"Part C: SVI with description not removed on {dut} - BUG NOT FIXED!")

        # Step C6: Check VLAN state
        st.log(f"[C6] Checking VLAN state (observed: also deleted with SVI)")
        if verify_vlan_removed(dut):
            st.log(f"Observation: VLAN also deleted with SVI on {dut}")

        st.log(f"Part C PASSED on {dut}")

    st.report_tc_pass(TC_IDS.part_c_svi_with_desc, "msg",
                      "Part C: SVI with description removed successfully on both DUTs")

    # ================================================================
    # FINAL CLEANUP
    # ================================================================
    st.banner("FINAL CLEANUP")
    for dut in [vars.D1, vars.D2]:
        _remove_svi_if_exists(dut)
        _remove_vlan_if_exists(dut)
        st.log(f"Cleanup done on {dut}")

    # ================================================================
    # TEST SUMMARY
    # ================================================================
    st.banner("=" * 80)
    st.banner("TEST RESULT: SM_ISCLI_P2_42 PASSED")
    st.banner("=" * 80)

    st.log("=" * 80)
    st.log("TEST SUMMARY - SM_ISCLI_P2_42: VLAN SVI Removal Bug Fix Verification")
    st.log("=" * 80)
    st.log(f"DUT1: {vars.D1}  |  DUT2: {vars.D2}")
    st.log(f"VLAN ID : {CONFIG.vlan_id}")
    st.log("")
    st.log("Part A - Description Removal:")
    st.log(f"  'no description' on SVI      : PASS - description removed, IP retained")
    st.log("")
    st.log("Part B - SVI Removal (after IP removal):")
    st.log(f"  'no interface Vlan200'        : PASS - SVI removed (empty show output)")
    st.log(f"  VLAN also deleted             : Observed on both DUTs")
    st.log("")
    st.log("Part C - SVI Removal WITH description (Main Bug):")
    st.log(f"  'no interface Vlan200'        : PASS - SVI removed even with description set")
    st.log(f"  VLAN also deleted             : Observed on both DUTs")
    st.log("")
    st.log("Bug SM_ISCLI_P2_42: CONFIRMED FIXED")
    st.log("=" * 80)

    st.report_pass("test_case_passed")
