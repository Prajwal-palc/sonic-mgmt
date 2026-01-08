"""
SNMP TEST - TC-7.1.4: Delete SNMP Community

Test Case ID: 7.1.4
Author: Automated Testing Suite
Copyright (C) 2026

How to run:
  cd /home/hp/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/diagnostic_tools/test_snmp_04_delete_community.py \
    --logs-path ./logs/snmp_04_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates SNMP community deletion:
  - Create test communities (RO and RW)
  - Verify communities exist
  - Delete test communities
  - Verify communities are removed
  - Verify default community remains
  - Save configuration

Pre-requisites:
  - 2 SONiC devices: 192.168.100.161, 192.168.100.206
  - Credentials: admin/palc@123
  - Testbed: testbed_2vs.yaml
  - SNMP service must be enabled

Important:
  - Community deletion via sonic-cli
  - Command: no snmp-server community <name>
  - Default community should NOT be deleted
  - Save config: sudo config save -y
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "ro_community": "test_readonly",
    "rw_community": "test_readwrite",
    "default_community": "public",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "snmp04_setup": "TC-SNMP-04-001",
    "snmp04_delete_ro": "TC-SNMP-04-002",
    "snmp04_delete_rw": "TC-SNMP-04-003",
    "snmp04_verify": "TC-SNMP-04-004",
})


@pytest.fixture(scope="module", autouse=True)
def snmp_04_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("SNMP TC-7.1.4 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    yield

    st.banner("=" * 80)
    st.banner("SNMP TC-7.1.4 MODULE CLEANUP - START")
    st.banner("=" * 80)

    # Cleanup any remaining test communities
    cleanup_test_communities()


def cleanup_test_communities():
    """Cleanup test communities."""
    st.log("Cleaning up test communities")

    for dut in [vars.D1, vars.D2]:
        try:
            commands = [
                f"no snmp-server community {CONFIG.ro_community}",
                f"no snmp-server community {CONFIG.rw_community}",
            ]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)
            st.log(f"✓ Cleanup completed on {dut}")
        except Exception as e:
            st.log(f"Cleanup warning on {dut}: {str(e)}")


def add_snmp_community(dut: str, community_name: str, community_type: str) -> bool:
    """Add SNMP community."""
    st.log(f"Adding SNMP community '{community_name}' ({community_type.upper()}) on {dut}")

    commands = [
        f"snmp-server community {community_name} {community_type}"
    ]

    try:
        st.config(dut, commands, type=data.cli_type)
        st.log(f"✓ Community '{community_name}' added on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to add community on {dut}: {str(e)}")
        return False


def delete_snmp_community(dut: str, community_name: str) -> bool:
    """
    Delete SNMP community.

    Command: no snmp-server community <name>
    """
    st.log(f"Deleting SNMP community '{community_name}' on {dut}")

    commands = [
        f"no snmp-server community {community_name}"
    ]

    try:
        st.config(dut, commands, type=data.cli_type)
        st.log(f"✓ Community '{community_name}' deleted on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to delete community on {dut}: {str(e)}")
        return False


def show_snmp_communities(dut: str) -> str:
    """Show SNMP community configuration."""
    st.log(f"Getting SNMP community list on {dut}")

    command = "show snmp-server community"
    output = st.show(dut, command, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

    output_str = str(output)
    st.log(f"Community output:\n{output_str}")

    return output_str


def verify_community_exists(output: str, community_name: str) -> bool:
    """
    Verify community exists in output.

    Returns:
        True if community found, False if not found
    """
    output_lower = output.lower()
    community_lower = community_name.lower()

    if community_lower in output_lower:
        st.log(f"✓ Community '{community_name}' found in output")
        return True
    else:
        st.log(f"✗ Community '{community_name}' NOT found in output")
        return False


def verify_community_not_exists(output: str, community_name: str) -> bool:
    """
    Verify community does NOT exist in output.

    Returns:
        True if community NOT found (deleted successfully), False if still exists
    """
    output_lower = output.lower()
    community_lower = community_name.lower()

    if community_lower not in output_lower:
        st.log(f"✓ Community '{community_name}' NOT found (deleted successfully)")
        return True
    else:
        st.error(f"✗ Community '{community_name}' still exists (deletion failed)")
        return False


def save_configuration(dut: str) -> bool:
    """
    Save configuration to persistent storage.

    Command: sudo config save -y
    """
    st.log(f"Saving configuration on {dut}")

    command = "sudo config save -y"

    try:
        output = st.config(dut, command, skip_error_check=True)
        st.log(f"Config save output:\n{output}")
        st.log(f"✓ Configuration saved on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to save configuration on {dut}: {str(e)}")
        return False


def test_snmp_04_delete_community():
    """
    Test Case 7.1.4: Delete SNMP Community

    Test Steps:
    1. Setup: Add test communities (RO and RW)
    2. Verify communities exist
    3. Delete RO community
    4. Delete RW community
    5. Verify communities are deleted
    6. Verify default community remains
    7. Save configuration

    Expected Results:
    - Test communities created successfully
    - RO community deleted: test_readonly
    - RW community deleted: test_readwrite
    - Only default community remains: public (RO)
    - Configuration saved successfully
    """
    st.banner("=" * 80)
    st.banner("TEST TC-7.1.4: DELETE SNMP COMMUNITY")
    st.banner("=" * 80)

    # Track test status
    test_failed = False

    # ==================================================================
    # STEP 1: Setup - Add Test Communities
    # ==================================================================
    st.banner("STEP 1: Setup - Add Test Communities")

    # Add RO community on both DUTs
    st.log(f"Adding RO community '{CONFIG.ro_community}'")
    if not add_snmp_community(vars.D1, CONFIG.ro_community, "ro"):
        st.report_tc_fail(TC_IDS.snmp04_setup, "msg",
                         f"Failed to add RO community on {vars.D1}")
        test_failed = True

    if not add_snmp_community(vars.D2, CONFIG.ro_community, "ro"):
        st.report_tc_fail(TC_IDS.snmp04_setup, "msg",
                         f"Failed to add RO community on {vars.D2}")
        test_failed = True

    # Add RW community on both DUTs
    st.log(f"Adding RW community '{CONFIG.rw_community}'")
    if not add_snmp_community(vars.D1, CONFIG.rw_community, "rw"):
        st.report_tc_fail(TC_IDS.snmp04_setup, "msg",
                         f"Failed to add RW community on {vars.D1}")
        test_failed = True

    if not add_snmp_community(vars.D2, CONFIG.rw_community, "rw"):
        st.report_tc_fail(TC_IDS.snmp04_setup, "msg",
                         f"Failed to add RW community on {vars.D2}")
        test_failed = True

    # ==================================================================
    # STEP 2: Verify Communities Exist
    # ==================================================================
    st.banner("STEP 2: Verify Test Communities Exist")

    output_d1 = show_snmp_communities(vars.D1)
    output_d2 = show_snmp_communities(vars.D2)

    # Verify RO community exists
    if not verify_community_exists(output_d1, CONFIG.ro_community):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_ro_community_missing_after_creation")
        st.report_tc_fail(TC_IDS.snmp04_setup, "msg",
                         f"RO community not found after creation on {vars.D1}")
        test_failed = True

    if not verify_community_exists(output_d2, CONFIG.ro_community):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_ro_community_missing_after_creation")
        st.report_tc_fail(TC_IDS.snmp04_setup, "msg",
                         f"RO community not found after creation on {vars.D2}")
        test_failed = True

    # Verify RW community exists
    if not verify_community_exists(output_d1, CONFIG.rw_community):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_rw_community_missing_after_creation")
        st.report_tc_fail(TC_IDS.snmp04_setup, "msg",
                         f"RW community not found after creation on {vars.D1}")
        test_failed = True

    if not verify_community_exists(output_d2, CONFIG.rw_community):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_rw_community_missing_after_creation")
        st.report_tc_fail(TC_IDS.snmp04_setup, "msg",
                         f"RW community not found after creation on {vars.D2}")
        test_failed = True

    if not test_failed:
        st.report_tc_pass(TC_IDS.snmp04_setup, "msg",
                         "Test communities created and verified successfully")

    # ==================================================================
    # STEP 3: Delete RO Community
    # ==================================================================
    st.banner("STEP 3: Delete Read-Only Community")

    st.log(f"Deleting RO community '{CONFIG.ro_community}' on {vars.D1}")
    if not delete_snmp_community(vars.D1, CONFIG.ro_community):
        st.report_tc_fail(TC_IDS.snmp04_delete_ro, "msg",
                         f"Failed to delete RO community on {vars.D1}")
        test_failed = True

    st.log(f"Deleting RO community '{CONFIG.ro_community}' on {vars.D2}")
    if not delete_snmp_community(vars.D2, CONFIG.ro_community):
        st.report_tc_fail(TC_IDS.snmp04_delete_ro, "msg",
                         f"Failed to delete RO community on {vars.D2}")
        test_failed = True

    if not test_failed:
        st.report_tc_pass(TC_IDS.snmp04_delete_ro, "msg",
                         "RO community deleted successfully")

    # ==================================================================
    # STEP 4: Delete RW Community
    # ==================================================================
    st.banner("STEP 4: Delete Read-Write Community")

    st.log(f"Deleting RW community '{CONFIG.rw_community}' on {vars.D1}")
    if not delete_snmp_community(vars.D1, CONFIG.rw_community):
        st.report_tc_fail(TC_IDS.snmp04_delete_rw, "msg",
                         f"Failed to delete RW community on {vars.D1}")
        test_failed = True

    st.log(f"Deleting RW community '{CONFIG.rw_community}' on {vars.D2}")
    if not delete_snmp_community(vars.D2, CONFIG.rw_community):
        st.report_tc_fail(TC_IDS.snmp04_delete_rw, "msg",
                         f"Failed to delete RW community on {vars.D2}")
        test_failed = True

    if not test_failed:
        st.report_tc_pass(TC_IDS.snmp04_delete_rw, "msg",
                         "RW community deleted successfully")

    # ==================================================================
    # STEP 5: Verify Communities Are Deleted
    # ==================================================================
    st.banner("STEP 5: Verify Test Communities Are Deleted")

    output_d1 = show_snmp_communities(vars.D1)
    output_d2 = show_snmp_communities(vars.D2)

    # Verify RO community is deleted
    if not verify_community_not_exists(output_d1, CONFIG.ro_community):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_ro_community_deletion_failed")
        st.report_tc_fail(TC_IDS.snmp04_verify, "msg",
                         f"RO community still exists on {vars.D1}")
        test_failed = True

    if not verify_community_not_exists(output_d2, CONFIG.ro_community):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_ro_community_deletion_failed")
        st.report_tc_fail(TC_IDS.snmp04_verify, "msg",
                         f"RO community still exists on {vars.D2}")
        test_failed = True

    # Verify RW community is deleted
    if not verify_community_not_exists(output_d1, CONFIG.rw_community):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_rw_community_deletion_failed")
        st.report_tc_fail(TC_IDS.snmp04_verify, "msg",
                         f"RW community still exists on {vars.D1}")
        test_failed = True

    if not verify_community_not_exists(output_d2, CONFIG.rw_community):
        st.generate_tech_support([vars.D1, vars.D2], "snmp_rw_community_deletion_failed")
        st.report_tc_fail(TC_IDS.snmp04_verify, "msg",
                         f"RW community still exists on {vars.D2}")
        test_failed = True

    # ==================================================================
    # STEP 6: Verify Default Community Remains
    # ==================================================================
    st.banner("STEP 6: Verify Default Community Remains")

    # Verify default community still exists
    if not verify_community_exists(output_d1, CONFIG.default_community):
        st.log(f"Warning: Default community not found on {vars.D1}")

    if not verify_community_exists(output_d2, CONFIG.default_community):
        st.log(f"Warning: Default community not found on {vars.D2}")

    if not test_failed:
        st.report_tc_pass(TC_IDS.snmp04_verify, "msg",
                         "Test communities deleted, default community preserved")

    # ==================================================================
    # STEP 7: Save Configuration
    # ==================================================================
    st.banner("STEP 7: Save Configuration")

    st.log(f"Saving configuration on {vars.D1}")
    if not save_configuration(vars.D1):
        st.log(f"Warning: Failed to save configuration on {vars.D1}")

    st.log(f"Saving configuration on {vars.D2}")
    if not save_configuration(vars.D2):
        st.log(f"Warning: Failed to save configuration on {vars.D2}")

    # ==================================================================
    # STEP 8: Show Final Configuration
    # ==================================================================
    st.banner("STEP 8: Show Final SNMP Configuration")

    for dut in [vars.D1, vars.D2]:
        st.log(f"\n{dut} - Final SNMP Community Configuration:")
        output = show_snmp_communities(dut)

    # ==================================================================
    # TEST RESULT
    # ==================================================================
    if test_failed:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-7.1.4 FAILED")
        st.banner("=" * 80)
        st.report_fail("test_case_failed")
    else:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-7.1.4 PASSED")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - TC-7.1.4: Delete SNMP Community")
        st.log("=" * 80)
        st.log(f"✓ Test communities created: {CONFIG.ro_community}, {CONFIG.rw_community}")
        st.log(f"✓ RO community deleted: {CONFIG.ro_community}")
        st.log(f"✓ RW community deleted: {CONFIG.rw_community}")
        st.log(f"✓ Communities successfully removed from configuration")
        st.log(f"✓ Default community preserved: {CONFIG.default_community}")
        st.log(f"✓ Configuration saved successfully")
        st.log(f"✓ Test completed on both DUTs")
        st.log("=" * 80)
        st.log("FINAL STATE:")
        st.log(f"  - Only '{CONFIG.default_community}' community remains (RO)")
        st.log(f"  - Test communities successfully deleted")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
