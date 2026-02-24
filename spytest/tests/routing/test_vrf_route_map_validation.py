"""
VRF AND ROUTE-MAP VALIDATION
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/ztp_standalone.yaml  \
  tests/routing/test_vrf_route_map_validation.py \
  --logs-path ./logs/vrf_route_map_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validates SONiC IS-CLI route-map configuration and VRF dependency checks.
  This test suite covers:
  1. Route-map creation with AS-path prepend and local-preference set statements
  2. Verification of route-map attributes in BGP running configuration
  3. VRF existence validation when configuring OSPF under non-existent VRF
  4. Error handling for dependency violations

  The tests use klish CLI mode to match the IS-CLI interface and verify that:
  - Route-maps can be configured with complex set-clauses
  - Set statements (AS-path prepend, local-preference) persist correctly
  - OSPF configuration rejects non-existent VRF references with proper error messages

Pre-requisites:
  - Topology: single-node (standalone DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node (standalone)
        # +--------------------+
        # |     smic_sonic1    |
        # | (192.168.100.101)  |
        # +--------------------+

  - Feature requirements: BGP, OSPF, VRF support
  - Min SONiC version: Any version with IS-CLI (klish) support
  - Required test variables (YAML): spytest/vars/routing/vars_vrf_route_map.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.vrf as vrf_api

# YAML variable file path
VAR_FILE_ENV = "VRF_ROUTE_MAP_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[2]
    / "spytest"
    / "vars"
    / "routing"
    / "vars_vrf_route_map.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"VRF route-map variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("VRF route-map YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestVrfRouteMapValidation:
    """Test suite for VRF and route-map dependency validation in IS-CLI mode."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize test suite with topology and configuration data."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Ensure minimum topology (single DUT for standalone tests)
        topology = st.ensure_min_topology("D1")

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Track created resources for cleanup
        cls.data.created_route_maps: List[str] = []
        cls.data.created_vrfs: List[str] = []

        # Get DUT handle
        cls.data.dut = topology.D1
        cls.data.dut_name = st.get_dut_names()[0] if st.get_dut_names() else None

        st.banner("VRF ROUTE-MAP VALIDATION TEST SUITE - SETUP COMPLETE")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup all created resources after test suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        st.banner("TEARDOWN: Cleaning up VRFs and route-maps")

        # Clean up route-maps
        while cls.data.created_route_maps:
            rmap_name = cls.data.created_route_maps.pop()
            cls._delete_route_map_safe(rmap_name)

        # Clean up VRFs
        while cls.data.created_vrfs:
            vrf_name = cls.data.created_vrfs.pop()
            cls._delete_vrf_safe(vrf_name)

    @classmethod
    def _delete_route_map_safe(cls, route_map_name: str) -> None:
        """Safely delete a route-map, suppressing errors."""
        try:
            st.log(f"Cleanup: Deleting route-map '{route_map_name}'")
            # Use direct CLI command for cleanup
            cmd = f"no route-map {route_map_name}"
            st.config(cls.data.dut, cmd, type=cls.data.cli_type, skip_error_check=True)
        except Exception as error:
            st.warn(f"Failed to delete route-map {route_map_name}: {error}")

    @classmethod
    def _delete_vrf_safe(cls, vrf_name: str) -> None:
        """Safely delete a VRF, suppressing errors."""
        try:
            st.log(f"Cleanup: Deleting VRF '{vrf_name}'")
            vrf_api.config_vrf(
                cls.data.dut,
                vrf_name=vrf_name,
                config="no",
                cli_type=cls.data.cli_type,
                skip_error=True
            )
        except Exception as error:
            st.warn(f"Failed to delete VRF {vrf_name}: {error}")

    def setup_method(self) -> None:
        """Reset per-test tracking."""
        self._test_route_maps: List[str] = []
        self._test_vrfs: List[str] = []

    def teardown_method(self) -> None:
        """Cleanup resources created during individual test."""
        if not self.data.cleanup_enabled:
            self._test_route_maps = []
            self._test_vrfs = []
            return

        # Remove test-specific route-maps
        while self._test_route_maps:
            rmap_name = self._test_route_maps.pop()
            self._delete_route_map_safe(rmap_name)
            if rmap_name in self.data.created_route_maps:
                self.data.created_route_maps.remove(rmap_name)

        # Remove test-specific VRFs
        while self._test_vrfs:
            vrf_name = self._test_vrfs.pop()
            self._delete_vrf_safe(vrf_name)
            if vrf_name in self.data.created_vrfs:
                self.data.created_vrfs.remove(vrf_name)

    def _track_route_map(self, route_map_name: str) -> None:
        """Track route-map for cleanup."""
        if route_map_name not in self._test_route_maps:
            self._test_route_maps.append(route_map_name)
        if route_map_name not in self.data.created_route_maps:
            self.data.created_route_maps.append(route_map_name)

    def _track_vrf(self, vrf_name: str) -> None:
        """Track VRF for cleanup."""
        if vrf_name not in self._test_vrfs:
            self._test_vrfs.append(vrf_name)
        if vrf_name not in self.data.created_vrfs:
            self.data.created_vrfs.append(vrf_name)

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Retrieve testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    def _create_route_map_with_sets(
        self,
        name: str,
        sequence: str,
        action: str = "permit",
        as_path_prepend: str = None,
        local_preference: str = None
    ) -> None:
        """
        Create route-map with set statements using direct CLI commands.

        Args:
            name: Route-map name
            sequence: Sequence number
            action: 'permit' or 'deny'
            as_path_prepend: Comma-separated AS path list (e.g., "1,2,3,4")
            local_preference: Local preference value
        """
        st.log(f"Creating route-map '{name}' sequence {sequence} ({action})")

        # Build command directly for klish CLI
        cmd = f"route-map {name} {action} {sequence}\n"

        if as_path_prepend:
            # For klish, use comma-separated AS path (e.g., "1,2,3,4")
            cmd += f"set as-path prepend {as_path_prepend}\n"
            st.log(f"  Set AS-path prepend: {as_path_prepend}")

        if local_preference:
            cmd += f"set local-preference {local_preference}\n"
            st.log(f"  Set local-preference: {local_preference}")

        # Exit route-map mode
        cmd += "exit\nexit"

        # Execute configuration
        st.config(self.data.dut, cmd, type=self.data.cli_type, conf=True)

        self._track_route_map(name)
        st.log(f"Route-map '{name}' created successfully")

    def _verify_route_map_in_output(
        self,
        route_map_name: str,
        expected_strings: List[str],
        process_filter: str = None
    ) -> None:
        """
        Verify route-map exists with expected attributes in show output.

        Args:
            route_map_name: Route-map name to verify
            expected_strings: List of strings that must be present in output
            process_filter: Filter by process (e.g., "BGP", "OSPF")
        """
        st.log(f"Verifying route-map '{route_map_name}' in show output")

        # Execute show command
        show_cmd = "show route-map"
        output = st.show(self.data.dut, show_cmd, type=self.data.cli_type, skip_tmpl=True)

        if not output:
            st.report_fail("msg", f"No output from '{show_cmd}' command")

        # Convert output to string for parsing
        output_str = str(output)

        # Verify all expected strings are present
        missing_strings = []
        for expected in expected_strings:
            if expected not in output_str:
                missing_strings.append(expected)

        if missing_strings:
            st.error(f"Route-map verification failed. Missing strings: {missing_strings}")
            st.error(f"Actual output:\n{output_str}")
            st.report_fail(
                "msg",
                f"Route-map '{route_map_name}' missing expected attributes: {missing_strings}"
            )

        st.log(f"Route-map '{route_map_name}' verified successfully with all expected attributes")

    def _verify_vrf_not_exists(self, vrf_name: str) -> None:
        """Verify that a VRF does not exist in the system."""
        st.log(f"Verifying VRF '{vrf_name}' does not exist")

        exists = vrf_api.verify_vrf(
            self.data.dut,
            vrfname=vrf_name,
            cli_type=self.data.cli_type
        )

        if exists:
            st.report_fail("msg", f"VRF '{vrf_name}' exists but should not")

        st.log(f"Confirmed: VRF '{vrf_name}' does not exist")

    def _configure_ospf_with_vrf_expect_error(
        self,
        vrf_name: str,
        expected_error_strings: List[str]
    ) -> None:
        """
        Attempt to configure OSPF under a VRF and expect error.

        Args:
            vrf_name: VRF name to use
            expected_error_strings: List of error message fragments to expect
        """
        st.log(f"Attempting to configure OSPF under non-existent VRF '{vrf_name}'")

        # Build OSPF configuration command
        cmd = f"router ospf vrf {vrf_name}"

        # Execute with error checking disabled to capture error message
        output = st.config(
            self.data.dut,
            cmd,
            type=self.data.cli_type,
            skip_error_check=True
        )

        output_str = str(output)

        # Verify expected error strings are present
        missing_errors = []
        for expected_error in expected_error_strings:
            if expected_error not in output_str:
                missing_errors.append(expected_error)

        if missing_errors:
            st.error(f"Expected error validation failed. Missing error strings: {missing_errors}")
            st.error(f"Actual output:\n{output_str}")
            st.report_fail(
                "msg",
                f"OSPF VRF dependency check failed - expected error not found: {missing_errors}"
            )

        st.log(f"OSPF correctly rejected configuration for non-existent VRF '{vrf_name}'")
        st.log(f"Error message contained expected strings: {expected_error_strings}")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_ROUTE_MAP_001"])
    def test_route_map_creation_with_set_statements(self) -> None:
        """
        TC_ROUTE_MAP_001: Create route-map with AS-path prepend and local-preference.

        Validates:
        1. Route-map can be created with permit sequence
        2. Set AS-path prepend statement is configured correctly
        3. Set local-preference statement is configured correctly
        4. Attributes are visible in 'show route-map' output under BGP process
        """
        st.banner("TEST CASE: Route-Map Creation with Set Statements")

        testcase = self._get_testcase("TC_ROUTE_MAP_001")
        route_map_cfg = testcase.get("route_map", {})

        if not route_map_cfg:
            st.report_fail("msg", "TC_ROUTE_MAP_001 missing 'route_map' definition in YAML")

        # Extract configuration parameters
        rmap_name = route_map_cfg.get("name")
        sequence = route_map_cfg.get("sequence")
        action = route_map_cfg.get("action", "permit")
        as_path = route_map_cfg.get("set_as_path_prepend")
        local_pref = route_map_cfg.get("set_local_preference")

        if not rmap_name or not sequence:
            st.report_fail("msg", "Route-map name and sequence are required")

        # Pre-check: Ensure route-map doesn't exist
        st.log(f"Pre-check: Verifying route-map '{rmap_name}' does not exist")
        output = st.show(self.data.dut, "show route-map", type=self.data.cli_type, skip_tmpl=True)
        if rmap_name in str(output):
            st.warn(f"Route-map '{rmap_name}' already exists, cleaning up")
            self._delete_route_map_safe(rmap_name)

        # Step 1: Create route-map with set statements
        self._create_route_map_with_sets(
            name=rmap_name,
            sequence=sequence,
            action=action,
            as_path_prepend=as_path,
            local_preference=local_pref
        )

        # Step 2: Verify route-map in show output
        verify_cfg = testcase.get("verify", {})
        expected_output = verify_cfg.get("expected_output", {})
        expected_all = expected_output.get("all", [])

        if not expected_all:
            st.report_fail("msg", "TC_ROUTE_MAP_001 missing verification strings in YAML")

        self._verify_route_map_in_output(
            route_map_name=rmap_name,
            expected_strings=expected_all,
            process_filter=verify_cfg.get("process")
        )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VRF_OSPF_DEPENDENCY_001"])
    @pytest.mark.negative
    def test_ospf_vrf_dependency_validation(self) -> None:
        """
        TC_VRF_OSPF_DEPENDENCY_001: Verify OSPF rejects non-existent VRF.

        Validates:
        1. VRF does not exist in system before test
        2. OSPF configuration under non-existent VRF is rejected
        3. Error message contains expected dependency violation text
        4. VRF list confirms the VRF remains absent after failed configuration
        """
        st.banner("TEST CASE: OSPF VRF Dependency Validation")

        testcase = self._get_testcase("TC_VRF_OSPF_DEPENDENCY_001")
        vrf_cfg = testcase.get("vrf", {})
        ospf_cfg = testcase.get("ospf", {})

        if not vrf_cfg or not ospf_cfg:
            st.report_fail(
                "msg",
                "TC_VRF_OSPF_DEPENDENCY_001 missing 'vrf' or 'ospf' definition in YAML"
            )

        vrf_name = vrf_cfg.get("name")
        should_exist = vrf_cfg.get("should_exist", False)

        if not vrf_name:
            st.report_fail("msg", "VRF name is required for dependency test")

        # Step 1: Pre-check - Verify VRF does not exist
        if not should_exist:
            self._verify_vrf_not_exists(vrf_name)

        # Step 2: Attempt OSPF configuration under non-existent VRF
        expected_errors = ospf_cfg.get("expected_error", {})
        error_all = expected_errors.get("all", [])
        error_any = expected_errors.get("any", [])

        # Combine all expected error fragments (require all from 'all' list)
        if not error_all and not error_any:
            st.report_fail(
                "msg",
                "TC_VRF_OSPF_DEPENDENCY_001 missing expected error strings in YAML"
            )

        # For simplicity, use 'all' list as required error strings
        required_errors = error_all if error_all else error_any

        self._configure_ospf_with_vrf_expect_error(
            vrf_name=vrf_name,
            expected_error_strings=required_errors
        )

        # Step 3: Post-check - Verify VRF still does not exist
        verify_cfg = testcase.get("verify", {})
        if verify_cfg.get("check_vrf_list"):
            absent_vrf = verify_cfg.get("vrf_should_be_absent")
            if absent_vrf:
                self._verify_vrf_not_exists(absent_vrf)

        st.report_pass("test_case_passed")
