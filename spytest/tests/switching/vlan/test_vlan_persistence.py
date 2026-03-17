"""
VLAN CONFIGURATION PERSISTENCE - TC_VLAN_PERSIST_001
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \\
  --testbed ./testbeds/testbed_vs_2d.yaml  \\
  tests/switching/vlan/test_vlan_persistence.py \\
  --logs-path ./logs/vlan_persist_$(date +%F_%H%M%S) \\
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Verify that VLAN configuration persists after save command execution and
  system config reload. This test validates configuration persistence by
  creating VLANs, saving configuration, reloading the configuration database,
  and verifying all VLANs are restored correctly. Ensures configuration data
  is properly stored and restored during system operations.

Pre-requisites:
  - Topology: Single DUT (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Single DUT Topology
        # +--------------------+
        # |      spine02       |
        # |        (D1)        |
        # |   Config Persist   |
        # +--------------------+

  - Feature flags / min SONiC version: VLAN support, config save/reload
  - Required test variables (YAML): spytest/vars/switching/vlan/vars_vlan_persistence.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api
import apis.system.reboot as reboot_api

# Variable file configuration
VAR_FILE_ENV = "VLAN_PERSIST_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_persistence.yaml"
)

# Test case IDs
TC_IDS = SpyTestDict({
    "persistence": "TC_VLAN_PERSIST_001",
})


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"VLAN persistence variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("VLAN persistence YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestVlanPersistence:
    """Test cases for VLAN configuration persistence across config save/reload."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("MODULE PROLOGUE: TestVlanPersistence Setup")

        # Load configuration from YAML
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Get testbed vars - use first DUT only (single DUT test)
        vars = st.get_testbed_vars()

        # Store configuration data
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.vars = vars
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # CLI type configuration
        cli_type = defaults.get("cli_type", "klish")
        cls.data.cli_type = cli_type

        # Verification timeout
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))

        # Cleanup configuration
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Reboot/reload settings
        cls.data.reboot_wait_time = int(defaults.get("reboot_wait_time", 300))
        cls.data.post_reboot_wait = int(defaults.get("post_reboot_wait", 60))

        # DUT and interface mapping - use first DUT only
        dut_list = st.get_dut_names()
        if not dut_list:
            st.error("No DUTs found in testbed")
            pytest.skip("No DUTs available")

        cls.data.dut = vars.D1 if hasattr(vars, 'D1') else dut_list[0]
        cls.data.dut_name = dut_list[0]

        # Track created VLANs for cleanup
        cls.data.created_vlans = []

        st.banner(f"SINGLE DUT TEST - Using only first DUT: {cls.data.dut_name}")
        st.log(f"Available DUTs in testbed: {dut_list}")
        st.log(f"Test DUT: {cls.data.dut_name}")
        st.log(f"CLI Type: {cls.data.cli_type}")
        st.log(f"Cleanup Enabled: {cls.data.cleanup_enabled}")

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up all VLANs after the suite."""
        st.banner("MODULE EPILOGUE: TestVlanPersistence Cleanup")

        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        # Clean up created VLANs
        cls._cleanup_all_vlans()

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        st.log("Test setup: Resetting per-test tracking")
        self._test_vlans = []

    def teardown_method(self) -> None:
        """Remove any VLANs that the testcase configured."""
        st.log("Test teardown: Cleaning up test-specific resources")

        if not self.data.cleanup_enabled:
            self._test_vlans = []
            return

        # Clean up test-specific VLANs
        while self._test_vlans:
            vlan = self._test_vlans.pop()
            self._delete_vlan(vlan)
            if vlan in self.data.created_vlans:
                self.data.created_vlans.remove(vlan)

        # Ensure we exit config mode after cleanup
        self._exit_config_mode()

    @classmethod
    def _cleanup_all_vlans(cls) -> None:
        """Remove all VLANs tracked across the suite."""
        while cls.data.created_vlans:
            vlan = cls.data.created_vlans.pop()
            st.log(f"Cleaning up VLAN {vlan}")
            vlan_api.delete_vlan(
                cls.data.dut,
                vlan,
                cli_type=cls.data.cli_type,
                remove_vlan_mapping=True
            )

        # Ensure we exit config mode after cleanup
        cls._exit_config_mode_static()

    def _exit_config_mode(self) -> None:
        """Exit from klish config/exec mode to shell for clean state."""
        if self.data.cli_type == "klish":
            st.log("Exiting klish to shell for clean state")
            # Exit all the way to shell to ensure clean state
            # SpyTest will automatically re-enter klish when needed for next operation
            # Use "exit" multiple times instead of "end" to avoid internal errors
            commands = ["exit", "exit"]
            for cmd in commands:
                try:
                    st.config(self.data.dut, cmd, type=self.data.cli_type, skip_error_check=True)
                except Exception as e:
                    st.log(f"Ignoring error during {cmd}: {str(e)}")

    @classmethod
    def _exit_config_mode_static(cls) -> None:
        """Exit from klish config/exec mode to shell (class method for final cleanup)."""
        if cls.data.cli_type == "klish":
            st.log("Exiting klish to shell prompt (class method)")
            # Use "exit" multiple times instead of "end" to avoid internal errors
            # First exit goes from config mode to exec mode, second exit goes to shell
            commands = ["exit", "exit"]
            for cmd in commands:
                st.config(cls.data.dut, cmd, type=cls.data.cli_type, skip_error_check=True)

    def _create_vlan(self, vlan_id: int) -> bool:
        """Create a VLAN and track it for cleanup."""
        st.log(f"Creating VLAN {vlan_id}")
        result = vlan_api.create_vlan(
            self.data.dut,
            vlan_id,
            cli_type=self.data.cli_type
        )
        if result:
            if vlan_id not in self._test_vlans:
                self._test_vlans.append(vlan_id)
            if vlan_id not in self.data.created_vlans:
                self.data.created_vlans.append(vlan_id)
        return result

    def _delete_vlan(self, vlan_id: int) -> bool:
        """Delete a VLAN."""
        st.log(f"Deleting VLAN {vlan_id}")
        return vlan_api.delete_vlan(
            self.data.dut,
            vlan_id,
            cli_type=self.data.cli_type,
            remove_vlan_mapping=True
        )

    def _verify_vlan_exists(self, vlan_id: int) -> bool:
        """Verify that a VLAN exists using VLAN API."""
        st.log(f"Verifying VLAN {vlan_id} exists")
        try:
            # Use VLAN API to verify VLAN existence
            # This properly handles pagination and output parsing
            return vlan_api.verify_vlan_config(
                self.data.dut,
                vlan_id,
                cli_type=self.data.cli_type
            )
        except Exception as e:
            st.error(f"VLAN verification failed for VLAN {vlan_id}: {str(e)}")
            return False

    def _get_vlan_list(self) -> List[str]:
        """Get list of all configured VLANs using VLAN API."""
        st.log("Getting current VLAN list")
        try:
            # Use VLAN API to get VLAN list
            # This properly handles pagination issues with show commands
            vlan_list = vlan_api.get_vlan_list(
                self.data.dut,
                cli_type=self.data.cli_type
            )
            # Convert to sorted list of strings for consistency
            vlan_list = sorted([str(v) for v in vlan_list])
            st.log(f"Retrieved VLAN list: {vlan_list}")
            return vlan_list
        except Exception as e:
            st.error(f"Failed to get VLAN list: {str(e)}")
            return []

    def _save_configuration(self) -> bool:
        """Save running configuration to startup configuration."""
        st.log("Saving configuration using write memory")
        return reboot_api.config_save(
            self.data.dut,
            shell='sonic',
            cli_type=self.data.cli_type
        )

    def _reload_configuration(self) -> bool:
        """Reload configuration from startup configuration."""
        st.log("Reloading configuration database")
        try:
            return reboot_api.config_save_reload(self.data.dut)
        except Exception as e:
            st.error(f"Config reload failed: {str(e)}")
            return False

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_PERSIST_001"])
    def test_vlan_persist_001_config_save_reload(self) -> None:
        """
        TC_VLAN_PERSIST_001: Configuration Save and Reload

        Verify that VLAN configuration persists after save and reload:
        1. Create VLANs 10, 20, 30
        2. Verify VLANs exist in running configuration
        3. Save configuration with write memory
        4. Reload configuration database
        5. Verify all VLANs persist after reload
        6. Compare pre-reload and post-reload VLAN lists
        """
        st.banner("TC_VLAN_PERSIST_001: Configuration Save and Reload")

        # Get test case configuration
        testcase = self._get_testcase("TC_VLAN_PERSIST_001")
        test_vlans = testcase.get("test_vlans", [10, 20, 30])
        expected = testcase.get("expected", {})

        st.log(f"Test Configuration:")
        st.log(f"  VLANs to test: {test_vlans}")
        st.log(f"  Expected pre-reload count: {expected.get('pre_reboot_vlan_count', 3)}")
        st.log(f"  Expected post-reload count: {expected.get('post_reboot_vlan_count', 3)}")

        pre_reload_vlans = []
        post_reload_vlans = []

        try:
            # Phase 1: Create VLANs
            st.banner("Phase 1: Create VLANs 10, 20, 30")
            for vlan_id in test_vlans:
                if not self._create_vlan(vlan_id):
                    st.report_tc_fail(TC_IDS.persistence, "msg", f"Failed to create VLAN {vlan_id}")
                    st.report_fail("msg", f"Failed to create VLAN {vlan_id}")
                st.log(f"Successfully created VLAN {vlan_id}")

            # Exit config mode and allow config database to sync
            st.log("Exiting config mode after VLAN creation")
            self._exit_config_mode()

            # Wait for config database to fully sync
            st.wait(10, "Waiting for VLAN configuration to fully propagate to config database")

            # Phase 2: Verify VLANs before save
            st.banner("Phase 2: Verify VLANs in Running Configuration (Pre-Reload)")
            for vlan_id in test_vlans:
                if not st.poll_wait(
                    self._verify_vlan_exists,
                    self.data.verify_timeout,
                    vlan_id
                ):
                    st.report_tc_fail(TC_IDS.persistence, "msg", f"VLAN {vlan_id} not found in running configuration")
                    st.report_fail("msg", f"VLAN {vlan_id} not found in running configuration")
                st.log(f"Verified: VLAN {vlan_id} exists in running configuration")

            # Get pre-reload VLAN list
            pre_reload_vlans = self._get_vlan_list()
            st.log(f"Pre-reload VLAN list: {pre_reload_vlans}")

            # Verify all test VLANs are in the list
            for vlan_id in test_vlans:
                if str(vlan_id) not in pre_reload_vlans:
                    st.report_tc_fail(TC_IDS.persistence, "msg", f"VLAN {vlan_id} not in pre-reload VLAN list")
                    st.report_fail("msg", f"VLAN {vlan_id} not in pre-reload VLAN list")

            # Phase 3: Save configuration
            st.banner("Phase 3: Save Configuration (write memory)")
            if not self._save_configuration():
                st.report_tc_fail(TC_IDS.persistence, "msg", "Failed to save configuration")
                st.report_fail("msg", "Failed to save configuration")
            st.log("Configuration saved successfully")

            # Wait a bit after save
            st.wait(5, "Waiting after configuration save")

            # Phase 4: Reload configuration
            st.banner("Phase 4: Reload Configuration Database")
            st.log("Initiating config reload...")
            if not self._reload_configuration():
                st.report_tc_fail(TC_IDS.persistence, "msg", "Failed to reload configuration")
                st.report_fail("msg", "Failed to reload configuration")
            st.log("Configuration reload completed")

            # Wait for system to stabilize after reload
            st.wait(
                self.data.post_reboot_wait,
                f"Waiting {self.data.post_reboot_wait}s for system to stabilize after reload"
            )

            # Phase 5: Verify VLANs after reload
            st.banner("Phase 5: Verify VLAN Persistence After Reload")

            # Get post-reload VLAN list
            post_reload_vlans = self._get_vlan_list()
            st.log(f"Post-reload VLAN list: {post_reload_vlans}")

            # Verify all test VLANs still exist
            for vlan_id in test_vlans:
                if not st.poll_wait(
                    self._verify_vlan_exists,
                    self.data.verify_timeout,
                    vlan_id
                ):
                    st.report_tc_fail(
                        TC_IDS.persistence,
                        "msg",
                        f"VLAN {vlan_id} lost after config reload"
                    )
                    st.report_fail(
                        "msg",
                        f"VLAN {vlan_id} lost after config reload"
                    )
                st.log(f"Verified: VLAN {vlan_id} persisted after reload")

            # Verify all test VLANs are in post-reload list
            for vlan_id in test_vlans:
                if str(vlan_id) not in post_reload_vlans:
                    st.report_tc_fail(
                        TC_IDS.persistence,
                        "msg",
                        f"VLAN {vlan_id} not in post-reload VLAN list"
                    )
                    st.report_fail(
                        "msg",
                        f"VLAN {vlan_id} not in post-reload VLAN list"
                    )

            # Phase 6: Compare pre and post reload configurations
            st.banner("Phase 6: Compare Pre-Reload and Post-Reload Configurations")

            # Check if all test VLANs are present in both lists
            test_vlans_str = [str(v) for v in test_vlans]
            pre_test_vlans = [v for v in pre_reload_vlans if v in test_vlans_str]
            post_test_vlans = [v for v in post_reload_vlans if v in test_vlans_str]

            st.log(f"Test VLANs before reload: {pre_test_vlans}")
            st.log(f"Test VLANs after reload: {post_test_vlans}")

            if set(pre_test_vlans) != set(post_test_vlans):
                st.report_tc_fail(
                    TC_IDS.persistence,
                    "msg",
                    f"VLAN configuration mismatch: Pre={pre_test_vlans}, Post={post_test_vlans}"
                )
                st.report_fail(
                    "msg",
                    f"VLAN configuration mismatch: Pre={pre_test_vlans}, Post={post_test_vlans}"
                )

            # Verify counts match expected
            expected_count = expected.get('post_reboot_vlan_count', len(test_vlans))
            if len(post_test_vlans) != expected_count:
                st.report_tc_fail(
                    TC_IDS.persistence,
                    "msg",
                    f"Post-reload VLAN count mismatch: expected {expected_count}, got {len(post_test_vlans)}"
                )
                st.report_fail(
                    "msg",
                    f"Post-reload VLAN count mismatch: expected {expected_count}, got {len(post_test_vlans)}"
                )

            st.log(f"Verified: All {len(test_vlans)} VLANs persisted correctly after reload")
            st.log("Configuration persistence validation PASSED")

            # Test passed
            st.report_tc_pass(
                TC_IDS.persistence,
                "msg",
                "VLAN configuration persistence successful after save and reload"
            )
            st.report_pass("test_case_passed")

        except Exception as e:
            st.error(f"Test failed with exception: {str(e)}")
            st.log(f"Pre-reload VLANs: {pre_reload_vlans}")
            st.log(f"Post-reload VLANs: {post_reload_vlans}")
            st.report_tc_fail(TC_IDS.persistence, "msg", f"Test failed: {str(e)}")
            st.report_fail("test_case_failed")
