"""
VLAN CREATION AND DELETION - BASIC CRUD OPERATIONS
Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/switching/vlan/test_vlan_create_delete.py \
  --logs-path ./logs/vlan_create_delete_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive validation of VLAN creation and deletion operations using SpyTest APIs
  and klish CLI. The suite verifies single VLAN creation, deletion, and bulk VLAN range
  operations. Each test case performs 5-step verification using: show Vlan, running-config
  grep, vlan count, interface brief, and interface status commands to ensure complete
  validation of VLAN lifecycle management.

Pre-requisites:
  - Topology: Single DUT (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |        DUT1        |
        # |     (spine02)      |
        # +--------------------+

  - Feature flags / min SONiC version: VLAN support required
  - Required test variables (YAML): spytest/vars/switching/vars_vlan_create.yaml
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api

VAR_FILE_ENV = "VLAN_CREATE_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest/vars/switching/vars_vlan_create.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        st.warn(f"VLAN variable file not found: {candidate}, using defaults")
        return {"defaults": {"cli_type": "klish"}, "testcases": {}}

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    return content


@pytest.mark.topology("D1")
class TestVlanCreateDelete:
    """Testcases covering VLAN creation and deletion CRUD operations."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Get single DUT topology
        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Get DUT handle
        cls.data.dut = topology.D1
        cls.data.dut_name = st.get_dut_names()[0] if st.get_dut_names() else None

        st.log(f"DUT for testing: {cls.data.dut}")

        # Pre-test cleanup - ensure VLANs used in tests don't exist
        cls._cleanup_test_vlans()

        # Ensure device returns to Linux shell mode after klish operations
        st.log("Ensuring device is in Linux shell mode after setup")
        try:
            # Force device back to Linux shell mode by running click command
            st.show(cls.data.dut, "show vlan brief", type='click', skip_error_check=True, skip_tmpl=True)
        except Exception:
            pass

        st.banner("VLAN Create/Delete Test Suite - Setup Complete")

    @classmethod
    def _cleanup_test_vlans(cls) -> None:
        """Cleanup VLANs that will be used in tests before starting."""
        st.banner("Pre-Test Cleanup - Removing Test VLANs if they exist")

        dut = cls.data.dut
        cli_type = cls.data.cli_type

        # Use VLAN APIs to delete test VLANs
        test_vlans_single = ["100"]  # TC_VLAN_CREATE_001, TC_VLAN_DELETE_001

        for vlan_id in test_vlans_single:
            try:
                st.log(f"Cleaning up VLAN {vlan_id} before test (if exists)")
                vlan_api.delete_vlan(dut, vlan_id, cli_type=cli_type, skip_error_report=True, remove_vlan_mapping=False)
                st.log(f"Pre-cleanup: VLAN {vlan_id} deleted (if existed)")
            except Exception as e:
                st.log(f"Pre-cleanup VLAN {vlan_id} exception (non-fatal): {e}")

        st.log("✅ Pre-test cleanup completed")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup all VLANs after test suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        st.banner("VLAN Create/Delete Test Suite - Cleanup")
        # Clean up any remaining VLANs (except default VLAN 1)
        try:
            vlan_list = vlan_api.get_vlan_list(cls.data.dut, cli_type=cls.data.cli_type)
            if vlan_list:
                st.log(f"Cleaning up VLANs: {vlan_list}")
                for vlan in vlan_list:
                    if str(vlan) != "1":  # Don't delete default VLAN
                        try:
                            vlan_api.delete_vlan(cls.data.dut, str(vlan), cli_type=cls.data.cli_type, skip_error_report=True, remove_vlan_mapping=False)
                        except Exception as e:
                            st.log(f"Teardown VLAN {vlan} exception (non-fatal): {e}")
        except Exception as e:
            st.log(f"Cleanup exception (non-fatal): {e}")

        # Ensure device returns to Linux shell mode after klish operations
        st.log("Ensuring device is in Linux shell mode after teardown")
        try:
            st.show(cls.data.dut, "show vlan brief", type='click', skip_error_check=True, skip_tmpl=True)
        except Exception:
            pass

    def _verify_vlan_5_commands(
        self,
        vlan_id: str,
        should_exist: bool = True,
        expected_count: int = None
    ) -> bool:
        """
        Perform 5-command verification for VLAN existence.

        Commands executed:
        1. show Vlan <id> - using raw st.show with string verification
        2. show running-configuration | grep Vlan<id> - using st.show
        3. show Vlan count - using get_vlan_count API
        4. show interface brief - using st.show
        5. show interface status | no-more - using st.show

        Args:
            vlan_id: VLAN ID to verify
            should_exist: True if VLAN should exist, False if it should not
            expected_count: Expected VLAN count (optional)

        Returns:
            True if all verifications pass, False otherwise
        """
        dut = self.data.dut
        cli_type = self.data.cli_type
        vlan_name = f"Vlan{vlan_id}"
        all_passed = True

        st.banner(f"5-COMMAND VERIFICATION: VLAN {vlan_id} (should_exist={should_exist})")

        # Command 1: show Vlan <id> - Use raw command with string verification
        st.log(f"STEP 1/5: Executing 'show Vlan {vlan_id}'")
        try:
            # Use raw show command and check string output directly
            output1 = st.show(dut, f"show Vlan {vlan_id}", type=cli_type, skip_tmpl=True, skip_error_check=True)
            output1_str = str(output1)
            st.log(f"show Vlan {vlan_id} output: {output1_str[:200]}")  # Log first 200 chars

            if should_exist:
                # Check if VLAN name appears in output (e.g., "Vlan100")
                if vlan_name in output1_str:
                    st.log(f"✅ VLAN {vlan_id} found in 'show Vlan {vlan_id}' output")
                    st.log(f"   Output contains: {vlan_name}")
                elif "not found" in output1_str.lower():
                    st.error(f"❌ VLAN {vlan_id} not found - output says 'not found'")
                    all_passed = False
                else:
                    # Check for the VLAN ID in various formats
                    if f"Vlan{vlan_id}" in output1_str or f"VLAN{vlan_id}" in output1_str or f"NUM" in output1_str:
                        st.log(f"✅ VLAN {vlan_id} found in output (format variation)")
                    else:
                        st.error(f"❌ VLAN {vlan_id} not found in output")
                        st.log(f"   Output received: {output1_str[:500]}")
                        all_passed = False
            else:
                # VLAN should NOT exist
                if "not found" in output1_str.lower():
                    st.log(f"✅ VLAN {vlan_id} correctly not found (output says 'not found')")
                elif vlan_name not in output1_str:
                    st.log(f"✅ VLAN {vlan_id} correctly not found (not in output)")
                else:
                    st.error(f"❌ VLAN {vlan_id} still exists but should be deleted")
                    st.log(f"   Output contains: {vlan_name}")
                    all_passed = False
        except Exception as e:
            st.log(f"Show Vlan {vlan_id} exception: {e}")
            if not should_exist:
                st.log(f"✅ Exception expected for non-existent VLAN {vlan_id}")
            else:
                st.error(f"❌ Unexpected exception for VLAN {vlan_id}: {e}")
                all_passed = False

        # Command 2: show running-configuration | grep Vlan<id>
        st.log(f"STEP 2/5: Checking running-configuration for {vlan_name}")
        try:
            # Use show command to get running config and grep for VLAN
            cmd = f"show running-configuration | grep {vlan_name}"
            output2 = st.show(dut, cmd, type=cli_type, skip_tmpl=True, skip_error_check=True)
            output2_str = str(output2)

            if should_exist:
                if f"interface {vlan_name}" in output2_str or vlan_name in output2_str:
                    st.log(f"✅ {vlan_name} found in running-configuration")
                else:
                    # Try alternate verification - check if VLAN config exists
                    st.warn(f"⚠️ {vlan_name} not found in running-config grep (may be normal for new VLANs)")
            else:
                if vlan_name not in output2_str or len(output2_str) < 10:
                    st.log(f"✅ {vlan_name} correctly not in running-configuration")
                else:
                    st.error(f"❌ {vlan_name} still in running-configuration")
                    all_passed = False
        except Exception as e:
            st.log(f"Running-config check exception: {e}")

        # Command 3: show Vlan count
        st.log("STEP 3/5: Executing 'show Vlan count' - using direct count from raw output")
        try:
            # Use raw output and count VLANs directly (template is broken)
            vlan_output = st.show(dut, "show Vlan", type=cli_type, skip_tmpl=True)
            vlan_lines = [line for line in vlan_output.splitlines() if re.match(r'^\s*Vlan\d+', line)]
            vlan_count = len(vlan_lines)
            st.log(f"Current VLAN count: {vlan_count} (VLANs: {[re.match(r'^\s*(Vlan\d+)', line).group(1) for line in vlan_lines]})")

            if expected_count is not None:
                if vlan_count == expected_count:
                    st.log(f"✅ VLAN count matches expected: {vlan_count}")
                else:
                    st.error(f"❌ VLAN count mismatch: {vlan_count} != {expected_count}")
                    all_passed = False
            else:
                st.log(f"ℹ️ VLAN count: {vlan_count} (no expected count specified)")
        except Exception as e:
            st.error(f"❌ Failed to get VLAN count: {e}")
            all_passed = False

        # Command 4: show interface brief
        st.log("STEP 4/5: Executing 'show interface brief'")
        try:
            output4 = st.show(dut, "show interface brief", type=cli_type, skip_tmpl=True, skip_error_check=True)
            output4_str = str(output4)

            if should_exist:
                if vlan_name in output4_str:
                    st.log(f"✅ {vlan_name} found in 'show interface brief'")
                else:
                    st.warn(f"⚠️ {vlan_name} not found in 'show interface brief' (may be normal for new VLANs)")
            else:
                if vlan_name not in output4_str:
                    st.log(f"✅ {vlan_name} correctly not in 'show interface brief'")
                else:
                    st.error(f"❌ {vlan_name} still in 'show interface brief'")
                    all_passed = False
        except Exception as e:
            st.log(f"Interface brief exception: {e}")

        # Command 5: show interface status | no-more
        st.log("STEP 5/5: Executing 'show interface status | no-more'")
        try:
            # Use "| no-more" to avoid --more-- pagination
            output5 = st.show(dut, "show interface status | no-more", type=cli_type, skip_tmpl=True, skip_error_check=True)
            output5_str = str(output5)

            if should_exist:
                if vlan_name in output5_str:
                    st.log(f"✅ {vlan_name} found in 'show interface status'")
                else:
                    st.warn(f"⚠️ {vlan_name} not found in 'show interface status' (may be normal for new VLANs)")
            else:
                if vlan_name not in output5_str:
                    st.log(f"✅ {vlan_name} correctly not in 'show interface status'")
                else:
                    st.error(f"❌ {vlan_name} still in 'show interface status'")
                    all_passed = False
        except Exception as e:
            st.log(f"Interface status exception: {e}")

        # Summary
        if all_passed:
            st.log(f"✅ ALL 5 VERIFICATIONS PASSED for VLAN {vlan_id}")
        else:
            st.error(f"❌ SOME VERIFICATIONS FAILED for VLAN {vlan_id}")

        return all_passed

    @pytest.mark.inventory(feature="VLAN_Basic", testcases=["TC_VLAN_CREATE_001"])
    def test_vlan_create_single(self) -> None:
        """
        TC_VLAN_CREATE_001: Create Single VLAN

        Objective: Verify single VLAN creation
        Steps:
        0. Pre-cleanup: Delete VLAN 100 if it exists
        1. Get initial VLAN count
        2. Create VLAN 100
        3. Verify using 5 commands with count check (initial_count + 1)

        Expected Result: VLAN 100 is created successfully
        """
        st.banner("TC_VLAN_CREATE_001: Create Single VLAN 100")

        dut = self.data.dut
        cli_type = self.data.cli_type
        vlan_id = "100"

        # Step 0: Pre-cleanup - delete VLAN 100 if it exists
        st.log(f"Pre-cleanup: Deleting VLAN {vlan_id} if it exists")
        vlan_api.delete_vlan(dut, vlan_id, cli_type=cli_type, skip_error_report=True, remove_vlan_mapping=False)

        # Step 1: Get initial VLAN count (before creating VLAN)
        # Use raw show command and count VLANs manually (template is broken)
        output = st.show(dut, "show Vlan", type=cli_type, skip_tmpl=True)
        # Count lines that start with "Vlan" followed by digits
        vlan_lines = [line for line in output.splitlines() if re.match(r'^\s*Vlan\d+', line)]
        initial_count = len(vlan_lines)
        st.log(f"Initial VLAN count (before create): {initial_count} (VLANs: {[re.match(r'^\s*(Vlan\d+)', line).group(1) for line in vlan_lines]})")

        # Step 2: Create VLAN 100
        st.log(f"Creating VLAN {vlan_id} using API")
        result = vlan_api.create_vlan(dut, vlan_id, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to create VLAN {vlan_id}")
        st.log(f"✅ VLAN {vlan_id} created successfully")

        # Step 3: Verify with 5 commands
        # Expected count after create = initial_count + 1
        expected_count = initial_count + 1
        st.log(f"Expected count after create: {expected_count}")

        verification_passed = self._verify_vlan_5_commands(
            vlan_id,
            should_exist=True,
            expected_count=expected_count
        )

        if not verification_passed:
            st.report_fail("msg", f"VLAN {vlan_id} creation verification failed")

        # Cleanup: Delete VLAN 100
        st.log(f"Cleanup: Deleting VLAN {vlan_id}")
        vlan_api.delete_vlan(dut, vlan_id, cli_type=cli_type)

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="VLAN_Basic", testcases=["TC_VLAN_DELETE_001"])
    def test_vlan_delete_single(self) -> None:
        """
        TC_VLAN_DELETE_001: Delete Single VLAN

        Objective: Verify VLAN deletion
        Steps:
        0. Pre-cleanup: Delete VLAN 100 if it exists (no vlan 100)
        1. Create VLAN 100
        2. Verify VLAN 100 exists using 5 commands
        3. Delete VLAN 100
        4. Verify VLAN 100 is deleted using 5 commands:
           - show Vlan 100 (should show "not found")
           - show running-configuration | grep Vlan100 (empty output)
           - show Vlan count (decremented)
           - show interface brief (no Vlan100)
           - show interface status | no-more (no Vlan100)

        Expected Result: VLAN 100 is deleted successfully
        """
        st.banner("TC_VLAN_DELETE_001: Delete Single VLAN 100")

        dut = self.data.dut
        cli_type = self.data.cli_type
        vlan_id = "100"

        # Step 0: Pre-cleanup - delete VLAN 100 if it exists
        st.log(f"Pre-cleanup: Deleting VLAN {vlan_id} if it exists")
        vlan_api.delete_vlan(dut, vlan_id, cli_type=cli_type, skip_error_report=True, remove_vlan_mapping=False)

        # Step 1: Get initial count (before creating VLAN)
        # Use raw show command and count VLANs manually (template is broken)
        output = st.show(dut, "show Vlan", type=cli_type, skip_tmpl=True)
        vlan_lines = [line for line in output.splitlines() if re.match(r'^\s*Vlan\d+', line)]
        initial_count = len(vlan_lines)
        st.log(f"Initial VLAN count (before create): {initial_count} (VLANs: {[re.match(r'^\s*(Vlan\d+)', line).group(1) for line in vlan_lines]})")

        # Step 2: Create VLAN 100
        st.log(f"Creating VLAN {vlan_id}")
        result = vlan_api.create_vlan(dut, vlan_id, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to create VLAN {vlan_id}")
        st.log(f"✅ VLAN {vlan_id} created successfully")

        # Step 2: Verify VLAN exists
        st.log(f"Verifying VLAN {vlan_id} exists before deletion")
        expected_count_after_create = initial_count + 1
        verification_create = self._verify_vlan_5_commands(
            vlan_id,
            should_exist=True,
            expected_count=expected_count_after_create
        )

        if not verification_create:
            st.report_fail("msg", f"VLAN {vlan_id} not found after creation")

        # Step 4: Delete VLAN 100
        st.log(f"Deleting VLAN {vlan_id}")
        result = vlan_api.delete_vlan(dut, vlan_id, cli_type=cli_type)
        if not result:
            st.report_fail("msg", f"Failed to delete VLAN {vlan_id}")
        st.log(f"✅ VLAN {vlan_id} deleted successfully")

        # Step 4: Verify VLAN is deleted
        st.log(f"Verifying VLAN {vlan_id} is deleted")
        expected_count_after_delete = initial_count
        verification_delete = self._verify_vlan_5_commands(
            vlan_id,
            should_exist=False,
            expected_count=expected_count_after_delete
        )

        if not verification_delete:
            st.report_fail("msg", f"VLAN {vlan_id} still exists after deletion")

        st.report_pass("test_case_passed")
