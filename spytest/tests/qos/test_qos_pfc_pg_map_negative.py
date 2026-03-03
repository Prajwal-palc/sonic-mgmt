"""
QoS PFC-Priority-PG Map Negative Testing
Author: Athira
2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_3rr.yaml \\
  tests/qos/test_qos_pfc_pg_map_negative.py \\
  --logs-path ./logs/qos_pfc_negative_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive negative testing and boundary value validation for QoS PFC-Priority-PG
  map CLI configuration. This test suite validates that the CLI properly enforces input
  validation rules and rejects invalid configurations including:
  - Invalid PFC priority values (negative, non-numeric, out of range)
  - Invalid Priority Group (PG) values (negative, non-numeric, out of range)
  - Map name length constraints (max 32 characters)
  - Proper error messaging for all invalid inputs

  The suite also validates boundary conditions by testing that exactly 32-character
  map names are accepted while 33+ character names are rejected. This ensures the
  system correctly enforces the documented constraints for PFC-Priority-PG mapping
  configuration via Klish CLI.

Pre-requisites:
  - Topology: Single DUT (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - Single node with test interface
        # +--------------------+
        # |        dut1        |
        # |  Ethernet4         |
        # +--------------------+

  - Feature flags / min SONiC version: QoS and PFC support required
  - Required test variables (YAML): vars/qos/vars_qos_pfc_pg_map_negative.yaml
    - defaults.cli_type (klish)
    - defaults.verify_timeout
    - defaults.cleanup
    - testcases.4.25.14 definitions
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st

# Default YAML variable file location
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "qos"
    / "vars_qos_pfc_pg_map_negative.yaml"
)

# Test Case IDs for granular tracking
TC_IDS = SpyTestDict({
    "invalid_priority_negative": "TC-QOS-4.25.14-001",
    "invalid_priority_non_numeric": "TC-QOS-4.25.14-002",
    "invalid_priority_out_of_range": "TC-QOS-4.25.14-003",
    "invalid_pg_negative": "TC-QOS-4.25.14-004",
    "invalid_pg_out_of_range": "TC-QOS-4.25.14-005",
    "invalid_pg_non_numeric": "TC-QOS-4.25.14-006",
    "valid_configuration": "TC-QOS-4.25.14-007",
    "invalid_name_33_chars": "TC-QOS-4.25.14-008",
    "valid_name_32_chars": "TC-QOS-4.25.14-009",
    "cleanup": "TC-QOS-4.25.14-010",
})


def load_test_data() -> Dict[str, Any]:
    """
    Load test configuration from YAML file.

    Returns:
        Dict containing test configuration data

    Raises:
        FileNotFoundError: If YAML file not found
        ValueError: If YAML structure is invalid
    """
    if not DEFAULT_VAR_FILE.is_file():
        raise FileNotFoundError(f"Test variable file not found: {DEFAULT_VAR_FILE}")

    with DEFAULT_VAR_FILE.open(encoding="utf-8") as f:
        payload = yaml.safe_load(f) or {}

    if "testcases" not in payload:
        raise ValueError("YAML must contain 'testcases' key")

    return payload


def expand_priority_specification(priorities: str) -> List[int]:
    """
    Expand priority specification into individual priority values.

    Handles formats: "0", "1-2", "3,4", "5,6-7"

    Args:
        priorities: Priority specification string

    Returns:
        List of individual priority values
    """
    result = []

    for part in priorities.split(','):
        part = part.strip()
        if '-' in part:
            start, end = map(int, part.split('-'))
            result.extend(range(start, end + 1))
        else:
            result.append(int(part))

    return sorted(set(result))


def attempt_invalid_pfc_priority_config(
    dut: str,
    map_name: str,
    priority_value: str,
    pg_value: int,
    cli_type: str = "klish"
) -> bool:
    """
    Attempt to configure invalid PFC priority value.

    Args:
        dut: Device Under Test
        map_name: Name of the PFC map
        priority_value: Priority value to test (can be invalid)
        pg_value: Priority Group value
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if command was rejected (expected), False if accepted (error)
    """
    st.log(f"Testing invalid PFC priority '{priority_value}' with PG {pg_value}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type == "klish":
        commands = [
            f"qos map pfc-priority-pg {map_name}",
            f"pfc-priority {priority_value} pg {pg_value}",
            "exit"
        ]

        # Use st.config with skip_error_check to capture rejection
        output = st.config(
            dut,
            commands,
            type=cli_type,
            skip_error_check=True,
            conf=True
        )

        output_str = str(output)

        # Check if error was detected
        if "Error" in output_str or "Invalid" in output_str or "error" in output_str.lower():
            st.log(f"CLI correctly rejected invalid priority '{priority_value}'")
            return True
        else:
            st.error(f"CLI incorrectly accepted invalid priority '{priority_value}'")
            return False
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False


def attempt_invalid_pg_config(
    dut: str,
    map_name: str,
    priority_value: str,
    pg_value: str,
    cli_type: str = "klish"
) -> bool:
    """
    Attempt to configure invalid PG value.

    Args:
        dut: Device Under Test
        map_name: Name of the PFC map
        priority_value: Priority value (valid)
        pg_value: PG value to test (can be invalid)
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if command was rejected (expected), False if accepted (error)
    """
    st.log(f"Testing invalid PG '{pg_value}' with priority {priority_value}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type == "klish":
        commands = [
            f"qos map pfc-priority-pg {map_name}",
            f"pfc-priority {priority_value} pg {pg_value}",
            "exit"
        ]

        output = st.config(
            dut,
            commands,
            type=cli_type,
            skip_error_check=True,
            conf=True
        )

        output_str = str(output)

        if "Error" in output_str or "Invalid" in output_str or "error" in output_str.lower():
            st.log(f"CLI correctly rejected invalid PG '{pg_value}'")
            return True
        else:
            st.error(f"CLI incorrectly accepted invalid PG '{pg_value}'")
            return False
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False


def configure_valid_pfc_mapping(
    dut: str,
    map_name: str,
    priority: str,
    pg: int,
    cli_type: str = "klish"
) -> bool:
    """
    Configure valid PFC priority to PG mapping.

    Args:
        dut: Device Under Test
        map_name: Name of the PFC map
        priority: Priority value
        pg: Priority Group value
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring valid mapping: priority {priority} to PG {pg}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            commands = [
                f"qos map pfc-priority-pg {map_name}",
                f"pfc-priority {priority} pg {pg}",
                "exit"
            ]

            output = st.config(
                dut,
                commands,
                type=cli_type,
                skip_error_check=False,
                conf=True
            )

            st.log(f"Valid configuration accepted successfully")
            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to configure valid mapping: {e}")
        return False


def attempt_create_map_with_name(
    dut: str,
    map_name: str,
    cli_type: str = "klish",
    expect_error: bool = False
) -> bool:
    """
    Attempt to create PFC-Priority-PG map with specified name.

    Args:
        dut: Device Under Test
        map_name: Name to use for the map
        cli_type: CLI type (default: klish)
        expect_error: If True, expects command to fail (invalid name)

    Returns:
        bool: True if result matches expectation, False otherwise
    """
    st.log(f"Attempting to create map with name: '{map_name}' (length: {len(map_name)})")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type == "klish":
        command = f"qos map pfc-priority-pg {map_name}"

        output = st.config(
            dut,
            command,
            type=cli_type,
            skip_error_check=True,
            conf=True  # Enter config mode
        )

        output_str = str(output)

        error_detected = "Error" in output_str or "Invalid" in output_str or "error" in output_str.lower()

        if expect_error:
            if error_detected:
                st.log(f"CLI correctly rejected map name '{map_name}' (length: {len(map_name)})")
                return True
            else:
                st.error(f"CLI incorrectly accepted map name '{map_name}' (length: {len(map_name)})")
                # Try to clean up if accidentally created
                st.config(dut, "exit", type=cli_type, skip_error_check=True)
                return False
        else:
            if error_detected:
                st.error(f"CLI incorrectly rejected valid map name '{map_name}' (length: {len(map_name)})")
                return False
            else:
                st.log(f"CLI correctly accepted map name '{map_name}' (length: {len(map_name)})")
                return True
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False


def configure_pfc_priority_in_map(
    dut: str,
    map_name: str,
    priority: str,
    pg: int,
    cli_type: str = "klish"
) -> bool:
    """
    Configure PFC priority mapping in an existing map.

    Args:
        dut: Device Under Test
        map_name: Name of the existing PFC map
        priority: Priority specification (e.g., "0", "1-2", "3,4", "5,6-7")
        pg: Priority Group value
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring priority {priority} -> PG {pg} in map '{map_name}'")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            # Expand priority specification into individual values
            priority_list = expand_priority_specification(priority)

            # Build command list with map context
            commands = [f"qos map pfc-priority-pg {map_name}"]

            for prio in priority_list:
                commands.append(f"pfc-priority {prio} pg {pg}")

            commands.append("exit")

            st.config(
                dut,
                commands,
                type=cli_type,
                skip_error_check=False,
                conf=True
            )

            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to configure priority mapping: {e}")
        return False


def verify_map_exists(
    dut: str,
    map_name: str,
    cli_type: str = "klish"
) -> bool:
    """
    Verify PFC-Priority-PG map exists.

    Args:
        dut: Device Under Test
        map_name: Name of the map to verify
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if map exists, False otherwise
    """
    st.log(f"Verifying map '{map_name}' exists")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type == "klish":
        # Use specific map name to avoid pagination issues with multiple maps
        command = f"show qos map pfc-priority-pg {map_name}"
        output = st.show(dut, command, type=cli_type, skip_error_check=True)
        output_str = str(output)

        # Check if output contains the map name or valid data (not just empty/error)
        if map_name in output_str and "Error" not in output_str and "Invalid" not in output_str:
            st.log(f"Map '{map_name}' found")
            return True
        else:
            st.log(f"Map '{map_name}' not found or error occurred")
            return False
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False


def delete_pfc_map(
    dut: str,
    map_name: str,
    cli_type: str = "klish"
) -> bool:
    """
    Delete PFC-Priority-PG map.

    Args:
        dut: Device Under Test
        map_name: Name of the map to delete
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Deleting PFC map '{map_name}'")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            command = f"no qos map pfc-priority-pg {map_name}"

            st.config(
                dut,
                command,
                type=cli_type,
                skip_error_check=True,
                conf=False
            )

            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to delete map: {e}")
        return False


@pytest.mark.topology("any")
@pytest.mark.qos
@pytest.mark.pfc
@pytest.mark.negative
class TestQosPfcPgMapNegative:
    """Test class for QoS PFC-Priority-PG map negative testing and validation."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("MODULE PROLOGUE: Starting QoS PFC-PG Map Negative Testing")

        # Load test configuration
        try:
            config = load_test_data()
        except (FileNotFoundError, ValueError) as e:
            pytest.skip(str(e))

        # Get defaults
        defaults = config.get("defaults", {})
        min_topology = config.get("min_topology", ["D1"])

        # Get topology
        try:
            vars_data = st.ensure_min_topology(*min_topology)
        except Exception as e:
            pytest.skip(f"Topology requirement not met: {e}")

        # Store configuration
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.vars = vars_data
        cls.data.dut = vars_data.D1

        # Store test parameters
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup = bool(defaults.get("cleanup", True))

        cls.data.test_map_name = config.get("test_map_name", "pfc_pg_map")
        cls.data.test_interface = config.get("test_interface", "Ethernet4")

        # Get testcase configuration
        cls.data.testcase = SpyTestDict(
            config.get("testcases", {}).get("4.25.14", {})
        )

        # Track created maps for cleanup
        cls.data.created_maps = []

        st.log(f"Test configuration loaded successfully")
        st.log(f"DUT: {cls.data.dut}")
        st.log(f"CLI Type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure all test PFC maps are removed after the suite completes."""
        if not cls.data.cleanup:
            st.log("Cleanup disabled, skipping teardown")
            return

        st.banner("MODULE EPILOGUE: Cleaning up QoS PFC-PG Map Negative Testing")

        # Delete any created maps
        for map_name in cls.data.created_maps:
            st.log(f"Cleaning up map: {map_name}")
            delete_pfc_map(cls.data.dut, map_name, cls.data.cli_type)

        st.log("Cleanup completed successfully")

    @pytest.mark.inventory(feature="Regression", testcases=["QoS_PFC_PG_4.25.14"])
    def test_invalid_pfc_priority_pg_config(self) -> None:
        """
        Test Case 4.25.14: Verify CLI rejection for invalid PFC-Priority-PG configuration.

        This test validates:
        1. Invalid PFC priority values are rejected
        2. Invalid PG values are rejected
        3. Valid configuration is accepted
        4. Map name length constraints are enforced
        """
        st.banner("TEST CASE 4.25.14: Invalid PFC-Priority-PG Configuration Validation")

        tc_result = True

        # Step 1: Create a test PFC map
        st.banner("Step 1: Create Test PFC-Priority-PG Map")
        st.log(f"Creating test map: {self.data.test_map_name}")

        command = f"qos map pfc-priority-pg {self.data.test_map_name}"
        st.config(
            self.data.dut,
            command,
            type=self.data.cli_type,
            skip_error_check=False,
            conf=False
        )

        self.data.created_maps.append(self.data.test_map_name)
        st.report_tc_pass(TC_IDS.valid_configuration, "msg", "Test map created successfully")

        # Step 2: Test invalid PFC priority values
        st.banner("Step 2: Test Invalid PFC Priority Values")

        invalid_priorities = self.data.testcase.get("invalid_priority_values", [])

        for test_case in invalid_priorities:
            priority_value = test_case.get("value")
            pg = test_case.get("pg")
            description = test_case.get("description")

            st.log(f"Testing: {description}")

            result = attempt_invalid_pfc_priority_config(
                self.data.dut,
                self.data.test_map_name,
                priority_value,
                pg,
                self.data.cli_type
            )

            if not result:
                st.error(f"Failed validation: {description}")
                tc_result = False

                if "negative" in description.lower() or "-" in priority_value:
                    st.report_tc_fail(TC_IDS.invalid_priority_negative, "msg", f"Failed: {description}")
                elif priority_value.isalpha():
                    st.report_tc_fail(TC_IDS.invalid_priority_non_numeric, "msg", f"Failed: {description}")
                elif int(priority_value) >= 8:
                    st.report_tc_fail(TC_IDS.invalid_priority_out_of_range, "msg", f"Failed: {description}")
            else:
                if "negative" in description.lower() or "-" in priority_value:
                    st.report_tc_pass(TC_IDS.invalid_priority_negative, "msg", f"Passed: {description}")
                elif priority_value.replace("-", "").isalpha():
                    st.report_tc_pass(TC_IDS.invalid_priority_non_numeric, "msg", f"Passed: {description}")
                else:
                    try:
                        if int(priority_value) >= 8:
                            st.report_tc_pass(TC_IDS.invalid_priority_out_of_range, "msg", f"Passed: {description}")
                    except ValueError:
                        pass

        # Step 3: Test invalid PG values
        st.banner("Step 3: Test Invalid PG Values")

        invalid_pgs = self.data.testcase.get("invalid_pg_values", [])

        for test_case in invalid_pgs:
            priority = test_case.get("priority")
            pg_value = test_case.get("value")
            description = test_case.get("description")

            st.log(f"Testing: {description}")

            result = attempt_invalid_pg_config(
                self.data.dut,
                self.data.test_map_name,
                priority,
                pg_value,
                self.data.cli_type
            )

            if not result:
                st.error(f"Failed validation: {description}")
                tc_result = False

                if "negative" in description.lower() or "-" in pg_value:
                    st.report_tc_fail(TC_IDS.invalid_pg_negative, "msg", f"Failed: {description}")
                elif pg_value.isalpha():
                    st.report_tc_fail(TC_IDS.invalid_pg_non_numeric, "msg", f"Failed: {description}")
                elif int(pg_value) >= 8:
                    st.report_tc_fail(TC_IDS.invalid_pg_out_of_range, "msg", f"Failed: {description}")
            else:
                if "negative" in description.lower() or "-" in pg_value:
                    st.report_tc_pass(TC_IDS.invalid_pg_negative, "msg", f"Passed: {description}")
                elif pg_value.replace("-", "").isalpha():
                    st.report_tc_pass(TC_IDS.invalid_pg_non_numeric, "msg", f"Passed: {description}")
                else:
                    try:
                        if int(pg_value) >= 8:
                            st.report_tc_pass(TC_IDS.invalid_pg_out_of_range, "msg", f"Passed: {description}")
                    except ValueError:
                        pass

        # Step 4: Test valid configuration
        st.banner("Step 4: Test Valid Configuration")

        valid_config = self.data.testcase.get("valid_configuration", {})
        priority = valid_config.get("priority")
        pg = valid_config.get("pg")

        if priority and pg is not None:
            result = configure_valid_pfc_mapping(
                self.data.dut,
                self.data.test_map_name,
                priority,
                pg,
                self.data.cli_type
            )

            if result:
                st.report_tc_pass(TC_IDS.valid_configuration, "msg", "Valid configuration accepted")
            else:
                st.error("Valid configuration was rejected")
                st.report_tc_fail(TC_IDS.valid_configuration, "msg", "Valid configuration rejected")
                tc_result = False

        # Exit from map configuration mode
        st.config(self.data.dut, "exit", type=self.data.cli_type, skip_error_check=True)

        # Step 5: Test map name length validation - Invalid names (33+ chars)
        st.banner("Step 5: Test Invalid Map Names (33+ Characters)")

        map_name_validation = self.data.testcase.get("map_name_validation", {})
        invalid_names = map_name_validation.get("invalid_names", [])

        for test_case in invalid_names:
            map_name = test_case.get("name")
            description = test_case.get("description")

            st.log(f"Testing: {description} - length {len(map_name)}")

            result = attempt_create_map_with_name(
                self.data.dut,
                map_name,
                self.data.cli_type,
                expect_error=True
            )

            if result:
                st.report_tc_pass(TC_IDS.invalid_name_33_chars, "msg", f"Passed: {description}")
            else:
                st.error(f"Failed validation: {description}")
                st.report_tc_fail(TC_IDS.invalid_name_33_chars, "msg", f"Failed: {description}")
                tc_result = False

        # Step 6: Test valid map names (32 chars)
        st.banner("Step 6: Test Valid Map Names (32 Characters)")

        valid_names = map_name_validation.get("valid_names", [])

        for test_case in valid_names:
            map_name = test_case.get("name")
            priority = test_case.get("priority")
            pg = test_case.get("pg")
            description = test_case.get("description")

            st.log(f"Testing: {description} - length {len(map_name)}")

            # Attempt to create map with 32-char name
            result = attempt_create_map_with_name(
                self.data.dut,
                map_name,
                self.data.cli_type,
                expect_error=False
            )

            if result:
                self.data.created_maps.append(map_name)

                # Configure priority mapping
                if priority and pg is not None:
                    mapping_result = configure_pfc_priority_in_map(
                        self.data.dut,
                        map_name,
                        priority,
                        pg,
                        self.data.cli_type
                    )

                    if mapping_result:
                        st.log(f"Successfully configured mapping in {description}")
                    else:
                        st.error(f"Failed to configure mapping in {description}")
                        tc_result = False

                # Exit from map configuration mode to config mode
                st.config(self.data.dut, "exit", type=self.data.cli_type, skip_error_check=True)
                # Exit from config mode to exec mode
                st.config(self.data.dut, "end", type=self.data.cli_type, skip_error_check=True, conf=False)

                # Verify map exists
                if verify_map_exists(self.data.dut, map_name, self.data.cli_type):
                    st.report_tc_pass(TC_IDS.valid_name_32_chars, "msg", f"Passed: {description}")
                else:
                    st.error(f"Map not found after creation: {description}")
                    st.report_tc_fail(TC_IDS.valid_name_32_chars, "msg", f"Failed: {description}")
                    tc_result = False
            else:
                st.error(f"Failed validation: {description}")
                st.report_tc_fail(TC_IDS.valid_name_32_chars, "msg", f"Failed: {description}")
                tc_result = False

        # Final result
        st.banner("TEST RESULT")

        if tc_result:
            st.report_pass("test_case_passed")
        else:
            st.report_fail("test_case_failed")
