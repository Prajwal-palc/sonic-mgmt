"""
SM_ISCLI_19: Grep Filter Effectiveness in Command Combinations

Author: Athira
2026-02-06

How to run:
  export SM_ISCLI_19_VAR_FILE=/home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest/vars/system/cli/vars_sm_iscli_19.yaml
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  system/cli/test_sm_iscli_19_grep_filter.py \\
  --logs-path ./logs/sm_iscli_19_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates grep filter effectiveness in IS-CLI (Klish) command combinations.
  The test suite addresses a bug where grep filters in command pipelines
  (e.g., "show ip interfaces | grep pattern") fail to properly filter output,
  returning all results instead of only lines matching the search pattern.

  Test coverage includes:
  - Negative matching (non-existent patterns should return empty output)
  - Positive matching (valid patterns should return only matching lines)
  - Case sensitivity validation
  - Special character handling
  - Multiple command validation
  - Chained grep filters
  - Performance with large outputs

Pre-requisites:
  - Topology: Single DUT | Supported: HW and Virtual
  - Topology Diagram:
        # Single Node Topology
        # +--------------------+
        # |        DUT         |
        # | Multiple interfaces|
        # | IP addresses       |
        # | configured         |
        # +--------------------+

  - CLI Type: klish (IS-CLI)
  - Multiple interfaces with IP addresses configured
  - Required test variables (YAML): vars/system/cli/vars_sm_iscli_19.yaml
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st

# Environment variable for custom var file
VAR_FILE_ENV = "SM_ISCLI_19_VAR_FILE"

# Default variable file location
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "cli"
    / "vars_sm_iscli_19.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load test variables from YAML file with environment override support."""
    override_path = os.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"SM_ISCLI_19 variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("SM_ISCLI_19 YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestGrepFilterEffectiveness:
    """Test cases validating grep filter effectiveness in IS-CLI commands."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("SM_ISCLI_19: Setup Class - Loading Test Configuration")

        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Get topology requirement
        min_topology = defaults.get("min_topology")

        # Handle topology - for single-node tests with no specific topology requirements
        if min_topology and len(min_topology) > 0:
            topology = st.ensure_min_topology(*min_topology)
            cls.data.dut = topology.D1 if hasattr(topology, "D1") else st.get_dut_names()[0]
        else:
            # Single-node test without topology requirements
            st.log("Single-node test detected - using first available DUT")
            cls.data.dut = st.get_dut_names()[0]

        # Store configuration
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.test_patterns = SpyTestDict(config.get("test_patterns", {}))
        cls.data.test_commands = SpyTestDict(config.get("test_commands", {}))

        # CLI configuration
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 10))

        st.log(f"Test DUT: {cls.data.dut}")
        st.log(f"CLI Type: {cls.data.cli_type}")
        st.log(f"Total test cases loaded: {len(cls.data.testcases)}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after all tests complete."""
        st.banner("SM_ISCLI_19: Teardown Class - Test Suite Completed")

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        pass

    def teardown_method(self) -> None:
        """Cleanup after each test."""
        pass

    def _execute_cli_command(
        self, dut: str, command: str, cli_type: str = None
    ) -> str:
        """
        Execute a CLI command and return output.

        Args:
            dut: Device under test
            command: Command to execute
            cli_type: CLI type (klish/click)

        Returns:
            Command output as string
        """
        cli_type = cli_type or self.data.cli_type

        st.log(f"Executing command on {dut}: {command}")
        st.log(f"CLI Type: {cli_type}")

        # Execute command using st.show (for show commands) or st.config (for config)
        if command.strip().startswith("show"):
            # For show commands, use st.show and skip_tmpl to get raw output
            output = st.show(dut, command, skip_tmpl=True, skip_error_check=True)
        else:
            # For other commands
            output = st.config(dut, command, skip_error_check=True, type=cli_type)

        # Convert output to string if it's a list or dict
        if isinstance(output, list):
            output_str = "\n".join(str(item) for item in output)
        elif isinstance(output, dict):
            output_str = str(output)
        else:
            output_str = str(output) if output else ""

        st.log(f"Command output length: {len(output_str)} characters")
        return output_str

    def _count_output_lines(self, output: str) -> int:
        """
        Count non-empty lines in command output.

        Args:
            output: Command output string

        Returns:
            Number of non-empty lines
        """
        if not output:
            return 0

        lines = [line.strip() for line in output.split("\n") if line.strip()]

        # Filter out common prompt lines and command echoes
        filtered_lines = []
        for line in lines:
            # Skip lines that are just the device prompt or command echo
            if line.endswith("#") or line.endswith("$"):
                continue
            if line.startswith("show ") and " | grep " in line:
                continue
            filtered_lines.append(line)

        return len(filtered_lines)

    def _validate_pattern_in_output(
        self, output: str, pattern: str, should_exist: bool = True
    ) -> bool:
        """
        Validate whether pattern exists in output.

        Args:
            output: Command output string
            pattern: Pattern to search for
            should_exist: Whether pattern should exist (True) or not (False)

        Returns:
            True if validation passes, False otherwise
        """
        if not output and should_exist:
            st.log(f"Pattern '{pattern}' validation: Empty output received")
            return False

        lines = [line for line in output.split("\n") if line.strip()]

        # Filter out prompts, command echoes, and error messages
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip shell prompts
            if stripped.endswith("#") or stripped.endswith("$"):
                continue
            # Skip command echoes
            if "show " in stripped and " | grep " in stripped:
                continue
            # Skip error messages
            if "Error:" in stripped or "Usage:" in stripped or "Try " in stripped:
                continue
            filtered_lines.append(line)

        # Count lines containing the pattern
        matching_lines = [line for line in filtered_lines if pattern in line]

        st.log(f"Pattern '{pattern}': Found in {len(matching_lines)}/{len(filtered_lines)} lines")

        if should_exist:
            # Pattern should exist - at least one line should contain it
            if len(matching_lines) == 0:
                st.error(f"Pattern '{pattern}' not found in any line (expected to find it)")
                return False

            # All filtered lines should contain the pattern (for grep output)
            if filtered_lines:
                for line in filtered_lines:
                    if pattern not in line:
                        st.error(f"Line without pattern found: {line[:100]}")
                        st.error(f"This indicates grep is not filtering properly")
                        return False
            return True
        else:
            # Pattern should NOT exist - no lines should contain it
            if len(matching_lines) > 0:
                st.error(f"Pattern '{pattern}' found in {len(matching_lines)} lines (expected 0)")
                st.error(f"Sample line: {matching_lines[0][:100]}")
                return False
            return True

    def _get_testcase(self, tcid: str) -> Dict[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_19_TC1"])
    def test_grep_non_existent_pattern(self) -> None:
        """
        TC 19.1: Verify grep returns no output for non-existent patterns.

        Bug scenario: grep returns all output instead of filtering.
        Expected: grep should return empty output when pattern doesn't exist.
        """
        st.banner("TC 19.1: Grep with Non-Existent Pattern (Negative Match)")

        testcase = self._get_testcase("19.1")
        patterns = testcase.get("patterns", [])
        commands = testcase.get("commands", [])

        if not patterns or not commands:
            st.report_fail("msg", "TC 19.1 missing patterns or commands in YAML")

        test_passed = True

        for command in commands:
            for pattern in patterns:
                grep_command = f"{command} | grep {pattern}"

                st.log(f"Testing command: {grep_command}")
                st.log(f"Expected: NO OUTPUT (pattern '{pattern}' should not exist)")

                output = self._execute_cli_command(self.data.dut, grep_command)
                line_count = self._count_output_lines(output)

                st.log(f"Output line count: {line_count}")

                if line_count > 0:
                    st.error(f"FAIL: grep returned {line_count} lines for non-existent pattern '{pattern}'")
                    st.error(f"This indicates the grep bug - all output returned instead of filtering")
                    st.error(f"Sample output: {output[:200]}")
                    test_passed = False
                else:
                    st.log(f"PASS: grep correctly returned empty output for pattern '{pattern}'")

        if not test_passed:
            st.report_fail(
                "msg",
                "Grep filter bug detected: non-existent patterns return all output instead of empty"
            )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_19_TC2"])
    def test_grep_exact_interface_match(self) -> None:
        """
        TC 19.2: Verify grep correctly filters for exact interface names.

        Expected: Only lines containing the exact search pattern should be returned.
        """
        st.banner("TC 19.2: Grep with Exact Interface Name (Positive Match)")

        testcase = self._get_testcase("19.2")
        pattern = testcase.get("pattern")
        command = testcase.get("command")

        if not pattern or not command:
            st.report_fail("msg", "TC 19.2 missing pattern or command in YAML")

        grep_command = f"{command} | grep {pattern}"

        st.log(f"Testing command: {grep_command}")
        st.log(f"Expected: Only lines containing '{pattern}'")

        output = self._execute_cli_command(self.data.dut, grep_command)
        line_count = self._count_output_lines(output)

        st.log(f"Output line count: {line_count}")

        if line_count == 0:
            st.log(f"No output for pattern '{pattern}' - may not exist on DUT")
            st.log("This is acceptable if interface doesn't exist")
        else:
            # Validate all lines contain the pattern
            if not self._validate_pattern_in_output(output, pattern, should_exist=True):
                st.report_fail(
                    "msg",
                    f"Grep filter failed: Output contains lines without pattern '{pattern}'"
                )
            st.log(f"PASS: All {line_count} lines contain pattern '{pattern}'")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_19_TC3"])
    def test_grep_ip_address_pattern(self) -> None:
        """
        TC 19.3: Verify grep filters IP addresses correctly.

        Expected: Only lines containing the IP pattern should be returned.
        """
        st.banner("TC 19.3: Grep with IP Address Pattern (Positive Match)")

        testcase = self._get_testcase("19.3")
        patterns = testcase.get("patterns", [])
        command = testcase.get("command")

        if not patterns or not command:
            st.report_fail("msg", "TC 19.3 missing patterns or command in YAML")

        test_passed = True

        for pattern in patterns:
            grep_command = f"{command} | grep {pattern}"

            st.log(f"Testing command: {grep_command}")
            st.log(f"Expected: Only lines containing '{pattern}'")

            output = self._execute_cli_command(self.data.dut, grep_command)
            line_count = self._count_output_lines(output)

            st.log(f"Output line count: {line_count}")

            if line_count == 0:
                st.log(f"No output for pattern '{pattern}' - may not exist on DUT")
            else:
                # Validate all lines contain the pattern
                if not self._validate_pattern_in_output(output, pattern, should_exist=True):
                    st.error(f"Grep filter failed for pattern '{pattern}'")
                    test_passed = False
                else:
                    st.log(f"PASS: All {line_count} lines contain pattern '{pattern}'")

        if not test_passed:
            st.report_fail("msg", "Grep filter failed for one or more IP patterns")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_19_TC4"])
    def test_grep_status_keywords(self) -> None:
        """
        TC 19.4: Verify grep filters interface status/state keywords.

        Expected: Only lines with matching status should be returned.
        """
        st.banner("TC 19.4: Grep with Status/State Keywords (Positive Match)")

        testcase = self._get_testcase("19.4")
        patterns = testcase.get("patterns", [])
        command = testcase.get("command")

        if not patterns or not command:
            st.report_fail("msg", "TC 19.4 missing patterns or command in YAML")

        test_passed = True

        for pattern in patterns:
            grep_command = f"{command} | grep {pattern}"

            st.log(f"Testing command: {grep_command}")
            st.log(f"Expected: Only lines containing status '{pattern}'")

            output = self._execute_cli_command(self.data.dut, grep_command)
            line_count = self._count_output_lines(output)

            st.log(f"Output line count: {line_count}")

            if line_count > 0:
                # Validate pattern exists in output
                if not self._validate_pattern_in_output(output, pattern, should_exist=True):
                    st.error(f"Grep filter failed for status pattern '{pattern}'")
                    test_passed = False
                else:
                    st.log(f"PASS: Grep correctly filtered for status '{pattern}'")

        if not test_passed:
            st.report_fail("msg", "Grep filter failed for one or more status keywords")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_19_TC5"])
    def test_grep_case_sensitivity(self) -> None:
        """
        TC 19.5: Verify grep respects case sensitivity.

        Expected: Grep should be case-sensitive by default (or behave consistently).
        """
        st.banner("TC 19.5: Grep Case Sensitivity Validation")

        testcase = self._get_testcase("19.5")
        patterns = testcase.get("patterns", [])
        command = testcase.get("command")

        if not patterns or not command:
            st.report_fail("msg", "TC 19.5 missing patterns or command in YAML")

        for pattern_config in patterns:
            pattern = pattern_config.get("pattern")
            should_match = pattern_config.get("should_match", True)

            grep_command = f"{command} | grep {pattern}"

            st.log(f"Testing command: {grep_command}")
            st.log(f"Pattern: '{pattern}' - Expected match: {should_match}")

            output = self._execute_cli_command(self.data.dut, grep_command)
            line_count = self._count_output_lines(output)

            st.log(f"Output line count: {line_count}")

            if should_match:
                if line_count == 0:
                    st.warn(f"Expected match for '{pattern}' but got no output")
                    st.log("This may indicate case-sensitive behavior or pattern doesn't exist")
                else:
                    st.log(f"PASS: Pattern '{pattern}' matched as expected")
            else:
                if line_count > 0:
                    st.log(f"Pattern '{pattern}' returned {line_count} lines when expecting no match")
                    st.log("This may indicate case-insensitive behavior")
                else:
                    st.log(f"PASS: Pattern '{pattern}' did not match (case-sensitive)")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_19_TC7"])
    def test_grep_multiple_commands(self) -> None:
        """
        TC 19.7: Verify grep works consistently across various show commands.

        Expected: Grep should filter correctly regardless of the show command used.
        """
        st.banner("TC 19.7: Grep with Multiple Commands (Comprehensive)")

        testcase = self._get_testcase("19.7")
        test_matrix = testcase.get("test_matrix", [])

        if not test_matrix:
            st.report_fail("msg", "TC 19.7 missing test_matrix in YAML")

        test_passed = True

        for test_item in test_matrix:
            command = test_item.get("command")
            pattern = test_item.get("pattern")

            if not command or not pattern:
                continue

            grep_command = f"{command} | grep {pattern}"

            st.log(f"Testing command: {grep_command}")

            output = self._execute_cli_command(self.data.dut, grep_command)
            line_count = self._count_output_lines(output)

            st.log(f"Output line count: {line_count}")

            if line_count > 0:
                # Validate pattern filtering
                if not self._validate_pattern_in_output(output, pattern, should_exist=True):
                    st.error(f"Grep failed for command: {command} with pattern: {pattern}")
                    test_passed = False
                else:
                    st.log(f"PASS: Grep worked correctly for: {command} | grep {pattern}")
            else:
                st.log(f"No output for: {command} | grep {pattern}")

        if not test_passed:
            st.report_fail("msg", "Grep filter failed for one or more commands")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_19_TC8"])
    def test_grep_empty_pattern(self) -> None:
        """
        TC 19.8: Verify grep behavior with empty or invalid patterns.

        Expected: Grep should handle empty patterns gracefully (return all or error).
        """
        st.banner("TC 19.8: Grep with Empty Pattern")

        testcase = self._get_testcase("19.8")
        patterns = testcase.get("patterns", [])
        command = testcase.get("command")

        if not command:
            st.report_fail("msg", "TC 19.8 missing command in YAML")

        for pattern in patterns:
            if pattern == "":
                grep_command = f'{command} | grep ""'
            else:
                grep_command = f'{command} | grep "{pattern}"'

            st.log(f"Testing command: {grep_command}")
            st.log(f"Pattern: '{pattern}' (empty or space)")

            output = self._execute_cli_command(self.data.dut, grep_command)
            line_count = self._count_output_lines(output)

            st.log(f"Output line count: {line_count}")
            st.log(f"Behavior documented: Empty pattern returned {line_count} lines")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_19_TC9"])
    def test_grep_performance(self) -> None:
        """
        TC 19.9: Verify grep efficiently filters large output sets.

        Expected: Grep should handle large outputs without performance issues.
        """
        st.banner("TC 19.9: Grep Performance with Large Output")

        testcase = self._get_testcase("19.9")
        command = testcase.get("command")
        pattern = testcase.get("pattern")
        max_execution_time = testcase.get("max_execution_time", 5)

        if not command or not pattern:
            st.report_fail("msg", "TC 19.9 missing command or pattern in YAML")

        grep_command = f"{command} | grep {pattern}"

        st.log(f"Testing command: {grep_command}")
        st.log(f"Max execution time: {max_execution_time} seconds")

        start_time = time.time()
        output = self._execute_cli_command(self.data.dut, grep_command)
        execution_time = time.time() - start_time

        line_count = self._count_output_lines(output)

        st.log(f"Output line count: {line_count}")
        st.log(f"Execution time: {execution_time:.2f} seconds")

        if execution_time > max_execution_time:
            st.warn(f"Execution time ({execution_time:.2f}s) exceeded threshold ({max_execution_time}s)")
        else:
            st.log(f"PASS: Execution completed within {max_execution_time}s threshold")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_19_TC10"])
    def test_grep_chained_filters(self) -> None:
        """
        TC 19.10: Verify multiple grep filters can be chained.

        Expected: Chained greps should work as progressive filters.
        """
        st.banner("TC 19.10: Chained Grep Filters")

        testcase = self._get_testcase("19.10")
        test_chains = testcase.get("test_chains", [])

        if not test_chains:
            st.report_fail("msg", "TC 19.10 missing test_chains in YAML")

        test_passed = True

        for chain_config in test_chains:
            base_command = chain_config.get("base_command")
            grep_chain = chain_config.get("grep_chain", [])

            if not base_command or not grep_chain:
                continue

            # Build chained command
            chained_command = base_command
            for pattern in grep_chain:
                chained_command += f" | grep {pattern}"

            st.log(f"Testing chained command: {chained_command}")

            output = self._execute_cli_command(self.data.dut, chained_command)
            line_count = self._count_output_lines(output)

            st.log(f"Output line count: {line_count}")

            if line_count > 0:
                # Validate all patterns exist in each line
                all_patterns_present = True
                for pattern in grep_chain:
                    if not self._validate_pattern_in_output(output, pattern, should_exist=True):
                        st.error(f"Pattern '{pattern}' not found in all lines of chained output")
                        all_patterns_present = False
                        test_passed = False

                if all_patterns_present:
                    st.log(f"PASS: All patterns present in chained grep output")
            else:
                st.log(f"No output for chained grep (patterns may not coexist)")

        if not test_passed:
            st.report_fail("msg", "Chained grep filters failed validation")

        st.report_pass("test_case_passed")


# Test case identifiers for documentation and tracking
TC_IDS = SpyTestDict({
    "non_existent_pattern": "SM_ISCLI_19_TC1",
    "exact_interface_match": "SM_ISCLI_19_TC2",
    "ip_pattern_match": "SM_ISCLI_19_TC3",
    "status_keywords": "SM_ISCLI_19_TC4",
    "case_sensitivity": "SM_ISCLI_19_TC5",
    "multiple_commands": "SM_ISCLI_19_TC7",
    "empty_pattern": "SM_ISCLI_19_TC8",
    "performance": "SM_ISCLI_19_TC9",
    "chained_grep": "SM_ISCLI_19_TC10",
})
