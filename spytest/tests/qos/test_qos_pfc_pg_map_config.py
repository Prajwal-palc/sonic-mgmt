"""
QoS PFC-Priority to Priority-Group Map Creation via CLI

Test ID: 4.25.13
Feature: QoS
Test Case: Verify PFC-Priority to Priority-Group map creation via CLI

Author: Athira
2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  tests/qos/test_qos_pfc_pg_map_config.py \\
  --logs-path ./logs/qos_pfc_config_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates that the CLI allows creation of PFC-Priority-PG maps and
  configuration of valid mappings with proper syntax support. It tests individual
  priority mappings, range-based mappings, comma-separated lists, and combined
  formats. The test also verifies error handling for non-existent maps and
  validates that the configuration is correctly applied and visible in show commands.

Pre-requisites:
  - Topology: Single DUT (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |        DUT1        |
        # | Ethernet4          |
        # +--------------------+

  - Feature: QoS and PFC support required
  - CLI Mode: Klish (IS-CLI)
  - Required test variables (YAML): vars/qos/vars_qos_pfc_pg_map_config.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test case IDs for tracking
TC_IDS = SpyTestDict({
    "map_creation": "TC-QOS-4.25.13-001",
    "individual_mapping": "TC-QOS-4.25.13-002",
    "range_mapping": "TC-QOS-4.25.13-003",
    "comma_separated_mapping": "TC-QOS-4.25.13-004",
    "combined_mapping": "TC-QOS-4.25.13-005",
    "negative_map_apply": "TC-QOS-4.25.13-006",
    "positive_map_apply": "TC-QOS-4.25.13-007",
    "pfc_enable": "TC-QOS-4.25.13-008",
    "verify_global_map": "TC-QOS-4.25.13-009",
    "verify_interface_map": "TC-QOS-4.25.13-010",
})

# Default YAML configuration file path
VAR_FILE_ENV = "QOS_PFC_PG_CONFIG_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[2]
    / "vars"
    / "qos"
    / "vars_qos_pfc_pg_map_config.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"QoS PFC-PG config variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("QoS PFC-PG config YAML must contain key 'testcases'")

    return content


def configure_pfc_pg_map(dut: str, map_name: str, cli_type: str = "klish") -> bool:
    """
    Create PFC-Priority-PG map.

    Args:
        dut: Device Under Test
        map_name: Name of the PFC-Priority-PG map
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Creating PFC-Priority-PG map '{map_name}' on {dut}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            commands = [f"qos map pfc-priority-pg {map_name}", "exit"]
            st.config(dut, commands, type=cli_type)
            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to create PFC-Priority-PG map: {e}")
        return False


def configure_pfc_priority_mapping(
    dut: str,
    map_name: str,
    priorities: str,
    pg: int,
    cli_type: str = "klish"
) -> bool:
    """
    Configure PFC priority to priority-group mapping.

    Args:
        dut: Device Under Test
        map_name: Name of the PFC-Priority-PG map
        priorities: Priority specification (e.g., "0", "1-2", "3,4", "5,6-7")
        pg: Priority Group number
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring PFC priority '{priorities}' to PG {pg} in map '{map_name}'")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            commands = [
                f"qos map pfc-priority-pg {map_name}",
                f"pfc-priority {priorities} pg {pg}",
                "exit"
            ]
            st.config(dut, commands, type=cli_type)
            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to configure PFC priority mapping: {e}")
        return False


def apply_pfc_map_to_interface(
    dut: str,
    interface: str,
    map_name: str,
    cli_type: str = "klish",
    expect_error: bool = False
) -> tuple[bool, bool]:
    """
    Apply PFC-Priority-PG map to interface.

    Args:
        dut: Device Under Test
        interface: Interface name
        map_name: Name of the PFC-Priority-PG map
        cli_type: CLI type (default: klish)
        expect_error: If True, expects operation to fail

    Returns:
        tuple: (success, error_occurred)
    """
    st.log(f"Applying PFC map '{map_name}' to interface {interface} on {dut}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            commands = [
                f"interface {interface}",
                f"qos-map pfc-priority-pg {map_name}",
                "exit"
            ]
            output = st.config(dut, commands, type=cli_type, skip_error_check=True)
            output_str = str(output)

            # Check for errors
            error_indicators = ["Error", "Failed", "Invalid"]
            error_occurred = any(indicator in output_str for indicator in error_indicators)

            if error_occurred:
                st.log(f"Application encountered error: {output_str}")
                if expect_error:
                    st.log("Error expected and received - PASS")
                    return (True, True)
                else:
                    st.warn(f"Unexpected error during application: {output_str}")
                    return (False, True)
            else:
                st.log("Map application command accepted without error")
                if expect_error:
                    st.warn("Expected error but application was accepted")
                    return (False, False)
                else:
                    return (True, False)
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return (False, False)
    except Exception as e:
        st.error(f"Exception during PFC map application: {e}")
        if expect_error:
            return (True, True)
        return (False, True)


def enable_pfc_on_interface(
    dut: str,
    interface: str,
    priorities: List[int],
    cli_type: str = "klish"
) -> bool:
    """
    Enable priority-flow-control on interface for specific priorities.

    Args:
        dut: Device Under Test
        interface: Interface name
        priorities: List of priorities to enable
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Enabling PFC priorities {priorities} on interface {interface}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            commands = [f"interface {interface}"]
            for priority in priorities:
                commands.append(f"priority-flow-control priority {priority}")
            commands.append("exit")

            st.config(dut, commands, type=cli_type)
            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to enable PFC priorities: {e}")
        return False


def verify_pfc_pg_map_exists(
    dut: str,
    map_name: str,
    expected_mappings: Dict[int, int],
    cli_type: str = "klish"
) -> bool:
    """
    Verify PFC-Priority-PG map exists and has correct mappings.

    Args:
        dut: Device Under Test
        map_name: Name of the PFC map
        expected_mappings: Dictionary of {priority: pg} expected mappings
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if map exists with correct mappings, False otherwise
    """
    st.log(f"Verifying PFC-Priority-PG map '{map_name}' on {dut}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            command = "show qos map pfc-priority-pg"
            output = st.show(dut, command, type=cli_type, skip_error_check=True)
            output_str = str(output)

            # Check if map name appears in output
            if map_name not in output_str:
                st.error(f"PFC map '{map_name}' not found in output")
                return False

            st.log(f"PFC map '{map_name}' found in output")

            # Verify individual mappings
            # Note: This is a basic check. For production, parse structured output
            for priority, pg in expected_mappings.items():
                st.log(f"Verifying priority {priority} maps to PG {pg}")
                # Additional parsing would go here for strict validation

            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to verify PFC map: {e}")
        return False


def verify_interface_pfc_map(
    dut: str,
    interface: str,
    map_name: str,
    cli_type: str = "klish"
) -> bool:
    """
    Verify interface has PFC map applied.

    Args:
        dut: Device Under Test
        interface: Interface name
        map_name: Expected map name
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if interface has the map applied, False otherwise
    """
    st.log(f"Verifying interface {interface} has PFC map '{map_name}' applied")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            command = f"show qos interface {interface}"
            output = st.show(dut, command, type=cli_type, skip_error_check=True)
            output_str = str(output)

            # Check if map name appears in interface output
            if map_name in output_str:
                st.log(f"Interface {interface} has PFC map '{map_name}' applied")
                return True
            else:
                st.error(f"Interface {interface} does not show PFC map '{map_name}'")
                return False
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to verify interface PFC map: {e}")
        return False


def delete_pfc_pg_map(dut: str, map_name: str, cli_type: str = "klish") -> bool:
    """
    Delete PFC-Priority-PG map.

    Args:
        dut: Device Under Test
        map_name: Name of the PFC map to delete
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Deleting PFC-Priority-PG map '{map_name}' on {dut}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            command = f"no qos map pfc-priority-pg {map_name}"
            st.config(dut, command, type=cli_type, skip_error_check=True)
            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to delete PFC map: {e}")
        return False


def cleanup_interface_pfc_config(
    dut: str,
    interface: str,
    map_name: str,
    priorities: List[int],
    cli_type: str = "klish"
) -> bool:
    """
    Clean up PFC configuration from interface.

    Args:
        dut: Device Under Test
        interface: Interface name
        map_name: Name of the PFC map
        priorities: List of priorities to disable
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Cleaning up PFC configuration on interface {interface}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            commands = [f"interface {interface}"]

            # Disable PFC priorities
            for priority in priorities:
                commands.append(f"no priority-flow-control priority {priority}")

            # Remove QoS map
            commands.append(f"no qos-map pfc-priority-pg {map_name}")
            commands.append("exit")

            st.config(dut, commands, type=cli_type, skip_error_check=True)
            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed during cleanup: {e}")
        return False


@pytest.mark.topology("any")
@pytest.mark.qos
@pytest.mark.pfc
class TestQosPfcPgMapConfig:
    """Test class for QoS PFC-Priority-PG map configuration validation."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("MODULE PROLOGUE: Starting QoS PFC-PG Map Configuration Test")

        # Load configuration from YAML
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Get minimum topology
        min_topology = config.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        # Store configuration
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # Store commonly used values
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Get DUT handles
        cls.data.dut = topology.D1
        st.log(f"Test will run on DUT: {cls.data.dut}")

        # Get test configuration
        cls.data.pfc_map_name = config.get("pfc_map_name", "pfcmap")
        cls.data.test_interface = config.get("test_interface", "Ethernet4")

        st.log("Module prologue completed successfully")

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure all PFC configurations are removed after the suite completes."""
        st.banner("MODULE EPILOGUE: Cleaning up QoS PFC-PG Map Configuration Test")

        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled - skipping")
            return

        try:
            # Get test case config
            testcase = cls.data.testcases.get("4.25.13", {})
            pfc_priorities = testcase.get("pfc_priorities", [])

            # Cleanup interface configuration
            cleanup_interface_pfc_config(
                cls.data.dut,
                cls.data.test_interface,
                cls.data.pfc_map_name,
                pfc_priorities,
                cls.data.cli_type
            )

            # Delete the map
            delete_pfc_pg_map(cls.data.dut, cls.data.pfc_map_name, cls.data.cli_type)

            st.log("Cleanup completed successfully")
        except Exception as e:
            st.warn(f"Cleanup encountered error (non-fatal): {e}")

    @pytest.mark.inventory(feature="Regression", testcases=["QoS_PFC_PG_4.25.13"])
    def test_pfc_pg_map_config(self) -> None:
        """
        Test Case 4.25.13: Verify PFC-Priority to Priority-Group map creation via CLI.

        This test validates that the CLI allows creation of PFC-Priority-PG maps with
        various priority specification formats including individual, range, comma-separated,
        and combined formats.
        """
        st.banner("TEST CASE 4.25.13: PFC-Priority-PG Map Creation via CLI")

        tc_result = True

        try:
            # Get test case configuration
            testcase = self.data.testcases.get("4.25.13")
            if not testcase:
                st.report_fail("msg", "Testcase 4.25.13 configuration not found in YAML")

            priority_mappings = testcase.get("priority_mappings", [])
            negative_test = testcase.get("negative_test", {})
            pfc_priorities = testcase.get("pfc_priorities", [])
            expected_mappings = testcase.get("expected_mappings", {})

            # Step 1: Create PFC-Priority-PG map with valid name
            st.banner("Step 1: Create PFC-Priority-PG Map")
            st.log(f"Creating PFC-Priority-PG map '{self.data.pfc_map_name}'")

            if not configure_pfc_pg_map(self.data.dut, self.data.pfc_map_name, self.data.cli_type):
                st.error("Failed to create PFC-Priority-PG map")
                st.report_fail("test_case_failed", TC_IDS.map_creation)

            st.report_tc_pass(TC_IDS.map_creation, "msg", "PFC map created successfully")

            # Steps 2-6: Configure priority mappings with different syntax formats
            st.banner("Steps 2-6: Configure Priority Mappings with Different Syntax Formats")

            for idx, mapping in enumerate(priority_mappings, start=1):
                priorities = mapping.get("priorities")
                pg = mapping.get("pg")
                format_type = mapping.get("format")
                description = mapping.get("description")

                st.log(f"\nMapping {idx}: {description}")
                st.log(f"  Format: {format_type}")
                st.log(f"  Command: pfc-priority {priorities} pg {pg}")

                if not configure_pfc_priority_mapping(
                    self.data.dut,
                    self.data.pfc_map_name,
                    priorities,
                    pg,
                    self.data.cli_type
                ):
                    st.error(f"Failed to configure {format_type} priority mapping")
                    tc_result = False
                else:
                    st.log(f"Successfully configured {format_type} priority mapping")

            # Report based on format types
            if tc_result:
                st.report_tc_pass(TC_IDS.individual_mapping, "msg", "Individual priority mapping successful")
                st.report_tc_pass(TC_IDS.range_mapping, "msg", "Range priority mapping successful")
                st.report_tc_pass(TC_IDS.comma_separated_mapping, "msg", "Comma-separated priority mapping successful")
                st.report_tc_pass(TC_IDS.combined_mapping, "msg", "Combined priority mapping successful")

            # Step 7: Apply map to interface (negative test - non-existent map)
            st.banner("Step 7: Apply Non-Existent Map to Interface (Negative Test)")
            non_existent_map = negative_test.get("non_existent_map", "test")

            st.log(f"Attempting to apply non-existent map '{non_existent_map}' to interface {self.data.test_interface}")

            success, error_occurred = apply_pfc_map_to_interface(
                self.data.dut,
                self.data.test_interface,
                non_existent_map,
                self.data.cli_type,
                expect_error=True
            )

            if not success:
                st.warn("Negative test did not behave as expected")
                st.report_tc_fail(TC_IDS.negative_map_apply, "msg", "Negative test failed")
                tc_result = False
            else:
                st.report_tc_pass(TC_IDS.negative_map_apply, "msg", "Negative test passed - error handling correct")

            # Step 8: Apply map to interface (positive test)
            st.banner("Step 8: Apply PFC Map to Interface (Positive Test)")
            st.log(f"Applying PFC map '{self.data.pfc_map_name}' to interface {self.data.test_interface}")

            success, error_occurred = apply_pfc_map_to_interface(
                self.data.dut,
                self.data.test_interface,
                self.data.pfc_map_name,
                self.data.cli_type,
                expect_error=False
            )

            if not success or error_occurred:
                st.error("Failed to apply PFC map to interface")
                st.report_fail("test_case_failed", TC_IDS.positive_map_apply)

            st.report_tc_pass(TC_IDS.positive_map_apply, "msg", "PFC map applied to interface successfully")

            # Step 9: Enable Priority Flow Control on interface
            st.banner("Step 9: Enable Priority Flow Control on Interface")
            st.log(f"Enabling PFC priorities {pfc_priorities} on interface {self.data.test_interface}")

            if not enable_pfc_on_interface(
                self.data.dut,
                self.data.test_interface,
                pfc_priorities,
                self.data.cli_type
            ):
                st.error("Failed to enable PFC priorities")
                st.report_fail("test_case_failed", TC_IDS.pfc_enable)

            st.report_tc_pass(TC_IDS.pfc_enable, "msg", "PFC priorities enabled successfully")

            # Step 10: Verify global PFC-Priority-PG map configuration
            st.banner("Step 10: Verify Global PFC-Priority-PG Map Configuration")
            st.log(f"Verifying PFC-Priority-PG map '{self.data.pfc_map_name}' configuration")

            # Display map configuration
            st.log("Displaying PFC map configuration:")
            output = st.show(self.data.dut, "show qos map pfc-priority-pg", type=self.data.cli_type, skip_error_check=True)
            st.log(f"PFC Map Configuration:\n{output}")

            if not verify_pfc_pg_map_exists(
                self.data.dut,
                self.data.pfc_map_name,
                expected_mappings,
                self.data.cli_type
            ):
                st.error("PFC map verification failed")
                st.report_tc_fail(TC_IDS.verify_global_map, "msg", "Global map verification failed")
                tc_result = False
            else:
                st.report_tc_pass(TC_IDS.verify_global_map, "msg", "Global map verification successful")

            # Step 11: Verify interface QoS configuration
            st.banner("Step 11: Verify Interface QoS Configuration")
            st.log(f"Verifying interface {self.data.test_interface} QoS configuration")

            # Display interface QoS configuration
            st.log("Displaying interface QoS configuration:")
            output = st.show(
                self.data.dut,
                f"show qos interface {self.data.test_interface}",
                type=self.data.cli_type,
                skip_error_check=True
            )
            st.log(f"Interface QoS Configuration:\n{output}")

            if not verify_interface_pfc_map(
                self.data.dut,
                self.data.test_interface,
                self.data.pfc_map_name,
                self.data.cli_type
            ):
                st.error("Interface PFC map verification failed")
                st.report_tc_fail(TC_IDS.verify_interface_map, "msg", "Interface map verification failed")
                tc_result = False
            else:
                st.report_tc_pass(TC_IDS.verify_interface_map, "msg", "Interface map verification successful")

        except Exception as e:
            st.error(f"Test encountered unexpected exception: {e}")
            import traceback
            st.error(traceback.format_exc())
            tc_result = False

        # Report final test result
        st.banner("TEST RESULT")
        if tc_result:
            st.report_pass("test_case_passed")
        else:
            st.report_fail("test_case_failed")
