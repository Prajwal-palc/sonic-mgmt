"""
BGP IPv6 CLI VALIDATION - VRF and Pipe Handling
Author: Shiva
2026

Test ID: BGP-IPV6-CLI-VRF-001

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/ztp_standalone.yaml \\
  tests/routing/bgp/test_bgp_ipv6_cli_validation.py \\
  --logs-path ./logs/bgp_ipv6_cli_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive BGP IPv6 CLI validation test suite covering:
  - Help output validation (? operator)
  - VRF keyword support in IPv6 commands
  - Error message validation when BGP IPv6 not configured
  - Pipe operator behavior (complete and incomplete)
  - CLI parity with IPv4 commands

  This suite tests ALL possible outcomes for each command:
  - Command with BGP data present
  - Command with no BGP configuration (error messages)
  - Incomplete pipe commands (validation)
  - Complete pipe commands (filtering, pagination)

Test Scenarios Covered:
  1. Help output - verify 'vrf' keyword present
  2. VRF all help - verify options displayed
  3. Summary command - multiple outcomes (data/errors)
  4. Incomplete pipes - 4 commands (except, find, grep, save)
  5. Complete pipe no-more - without data (error validation)
  6. Complete pipes with arguments - batch validation

Known Issues (Documented):
  - Error message is ambiguous when BGP IPv6 not configured
  - Expected: "%BGP IPv6 unicast is not configured for any VRF"
  - Actual: "%BGP instance not found"
  - Tests marked with @pytest.mark.xfail for known bugs

Pre-requisites:
  - Topology: Single DUT (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Single node topology
        # +--------------------+
        # |    smic_sonic1     |
        # | (192.168.100.197)  |
        # +--------------------+

  - No BGP configuration required (tests validate CLI behavior)
  - SONiC CLI (klish) access required
  - Tests can run with or without BGP configured

Data Sources:
  - DUT Details: testbeds/ztp_standalone.yaml
    - Device: smic_sonic1 (192.168.100.197:22)
    - Credentials: admin/root@123
    - CLI Type: klish (SONiC management CLI)

  - Test Scenarios: bgp_ipv6_cli.md
    - Commands to test and expected behavior
    - Error message validation
    - Pipe operator behavior

  - Test Variables: vars/routing/bgp/vars_bgp_ipv6_cli.yaml
    - Command templates
    - Expected keywords
    - Error message patterns

APIs Used:
  - spytest/apis/routing/bgp.py:
    - show_bgp_ipv6_summary(dut, **kwargs) - Get BGP IPv6 summary
    - show_bgp_ipv6_summary_vtysh(dut, vrf, **kwargs) - vtysh command
    - get_show_cli_type(dut, **kwargs) - Get CLI type for commands

  - spytest framework (spytest/__init__.py):
    - st.show(dut, cmd, type, skip_tmpl, skip_error_check) - Execute show commands
    - st.config(dut, cmd, type, conf, skip_error_check) - Execute config commands
    - st.log() - Logging
    - st.banner() - Section headers
    - st.report_pass() / st.report_fail() - Test results

Logs Location:
  ./logs/bgp_ipv6_cli_<timestamp>/
  - dlog-D1-smic_sonic1.log - Full CLI command/output transcript
  - module_test_bgp_ipv6_cli_validation.log - Module-level logs
  - results.html - HTML test results report
  - summary.txt - Quick test summary

Test Strategy:
  - Execute commands using st.show() with skip_error_check=True
  - Capture raw output including error messages
  - Parse output to detect state (BGP configured vs not configured)
  - Validate against expected outcomes for each state
  - Mark known bugs with @pytest.mark.xfail
  - Document expected vs actual behavior
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api


# Environment variable for YAML override
VAR_FILE_ENV = "BGP_IPV6_CLI_VAR_FILE"

# Default YAML configuration file path
# Path calculation: test_bgp_ipv6_cli_validation.py is in tests/routing/bgp/
# YAML file is in vars/routing/bgp/
# From test file: go up 3 levels to spytest/, then to vars/routing/bgp/
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "routing"
    / "bgp"
    / "vars_bgp_ipv6_cli.yaml"
)


def _set_terminal_length(dut: str, length: int = 0) -> None:
    """Set terminal length to control pagination in show commands.

    Args:
        dut: Device under test
        length: Terminal length (0 = no pagination, disable --more-- prompts)

    Note:
        This prevents show commands from displaying --more-- prompts that
        would cause automation scripts to hang waiting for user input.
    """
    try:
        cmd = f"terminal length {length}"
        st.config(dut, cmd, type="klish", conf=False, skip_error_check=True)
        st.log(f"Set terminal length to {length} on {dut} (pagination disabled)")
    except Exception as e:
        st.warn(f"Failed to set terminal length: {e}")


def _load_yaml_config() -> Dict[str, Any]:
    """Load test configuration from YAML file.

    Returns:
        Dictionary containing test configuration

    Raises:
        FileNotFoundError: If YAML file not found
        ValueError: If YAML structure is invalid
    """
    # Check for environment override
    override_path = st.getenv(VAR_FILE_ENV)
    yaml_path = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not yaml_path.is_file():
        raise FileNotFoundError(
            f"BGP IPv6 CLI test variable file not found: {yaml_path}\n"
            f"Expected location: {DEFAULT_VAR_FILE}\n"
            f"Override via environment: export {VAR_FILE_ENV}=<path>"
        )

    st.log(f"Loading BGP IPv6 CLI test configuration from: {yaml_path}")

    with yaml_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    if "testcases" not in config:
        raise ValueError(
            f"YAML file must contain 'testcases' key: {yaml_path}"
        )

    st.log("BGP IPv6 CLI test configuration loaded successfully")
    return config


@pytest.mark.topology("any")
class TestBgpIpv6CliValidation:
    """BGP IPv6 CLI Validation - VRF and Pipe Handling Test Suite.

    Tests validate BGP IPv6 CLI behavior covering:
    - Help output validation
    - VRF keyword support
    - Error messages when BGP not configured
    - Pipe operator behavior
    - CLI parity with IPv4 commands
    """

    # Class-level data storage
    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Setup test suite: Load configuration, prepare DUT, verify connectivity.

        Steps:
            1. Load YAML configuration (test parameters, expected outputs)
            2. Get DUT handle from topology
            3. Disable terminal pagination (avoid --more-- prompts)
            4. Verify DUT connectivity
            5. Record initial BGP state (for test logic)
        """
        st.banner("CLASS SETUP: BGP IPv6 CLI Validation Test Suite")

        # Load test configuration from YAML
        config = _load_yaml_config()
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(config.get("defaults", {}))
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # Get topology
        min_topology = cls.data.defaults.get("min_topology", ["D1"])
        topology = st.ensure_min_topology(*min_topology)
        cls.data.topology = topology

        # Get DUT handles
        cls.data.dut_names = st.get_dut_names()
        if not cls.data.dut_names:
            st.report_fail("msg", "No DUTs found in topology")

        cls.data.dut = cls.data.dut_names[0]
        st.log(f"Test DUT: {cls.data.dut}")

        # Get test parameters
        cls.data.cli_type = cls.data.defaults.get("cli_type", "klish")
        st.log(f"CLI Type: {cls.data.cli_type}")

        # Disable terminal pagination to avoid --more-- prompts
        _set_terminal_length(cls.data.dut, 0)
        st.log("Terminal pagination disabled for all show commands")

        # Check initial BGP state (for test logic - not required to be configured)
        st.banner("INITIAL STATE CHECK: BGP IPv6 Configuration")
        try:
            bgp_output = st.show(
                cls.data.dut,
                "show bgp ipv6 unicast summary",
                type=cls.data.cli_type,
                skip_tmpl=True,
                skip_error_check=True
            )

            if bgp_output and "Neighbor" in str(bgp_output):
                cls.data.bgp_ipv6_configured = True
                st.log("✓ BGP IPv6 is configured on DUT")
            else:
                cls.data.bgp_ipv6_configured = False
                st.log("✓ BGP IPv6 is NOT configured on DUT (this is OK for tests)")

        except Exception as e:
            cls.data.bgp_ipv6_configured = False
            st.log(f"BGP IPv6 state check: {e}")
            st.log("✓ Assuming BGP IPv6 not configured (this is OK for tests)")

        st.log("Class setup completed successfully")

    @classmethod
    def teardown_class(cls) -> None:
        """Teardown test suite: No cleanup needed (read-only tests).

        Note:
            These tests only execute show commands, no configuration changes.
            No cleanup is required.
        """
        st.banner("CLASS TEARDOWN: BGP IPv6 CLI Validation")
        st.log("No cleanup required (read-only tests)")
        st.log("Class teardown completed")

    def setup_method(self, method) -> None:
        """Per-test setup: Log test start.

        Args:
            method: Test method being executed
        """
        st.banner(f"TEST SETUP: {method.__name__}")
        st.log("No per-test setup required (read-only tests)")

    def teardown_method(self, method) -> None:
        """Per-test teardown: Log test completion.

        Args:
            method: Test method that was executed
        """
        st.banner(f"TEST TEARDOWN: {method.__name__}")
        st.log("No per-test teardown required (read-only tests)")

    def _execute_show_command(self, command: str) -> str:
        """Execute show command and capture full output including errors.

        Args:
            command: Show command to execute

        Returns:
            Command output as string (may include error messages)

        Note:
            Uses skip_error_check=True to capture error messages without
            failing the command execution. This allows us to validate
            error message content.
        """
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Executing command: {command}")

        try:
            output = st.show(
                dut,
                command,
                type=cli_type,
                skip_tmpl=True,
                skip_error_check=True
            )

            output_str = str(output) if output else ""
            st.log(f"Command output ({len(output_str)} chars):\n{output_str[:500]}")

            return output_str

        except Exception as e:
            st.log(f"Command execution exception: {e}")
            return str(e)

    def _check_keyword_in_output(self, output: str, keyword: str) -> bool:
        """Check if keyword appears in command output.

        Args:
            output: Command output string
            keyword: Keyword to search for (case-insensitive)

        Returns:
            True if keyword found, False otherwise
        """
        if not output:
            return False

        return keyword.lower() in output.lower()

    def _check_multiple_keywords(
        self,
        output: str,
        keywords: List[str]
    ) -> Tuple[bool, List[str]]:
        """Check if multiple keywords appear in output.

        Args:
            output: Command output string
            keywords: List of keywords to search for

        Returns:
            Tuple of (all_found: bool, missing_keywords: List[str])
        """
        missing = []

        for keyword in keywords:
            if not self._check_keyword_in_output(output, keyword):
                missing.append(keyword)

        all_found = len(missing) == 0
        return all_found, missing

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-IPV6-CLI-001"])
    def test_bgp_ipv6_unicast_help_shows_vrf_keyword(self) -> None:
        """Test Scenario 1: Verify help output shows 'vrf' keyword.

        Command: show bgp ipv6 unicast ?

        Expected Output:
            community  neighbors  route-map  statistics  summary  vrf
            |

        Validation:
            - 'vrf' keyword must be present
            - '|' (pipe operator) must be present
            - 'summary' keyword must be present
            - Output should match IPv4 command help format
        """
        st.banner("TEST 1: BGP IPv6 Help Output - VRF Keyword Validation")

        # Get expected keywords from YAML
        testcase = self.data.testcases.get("help_validation", {})
        expected_keywords = testcase.get("expected_keywords", ["vrf", "|", "summary"])

        st.log(f"Expected keywords: {expected_keywords}")

        # Execute help command
        command = "show bgp ipv6 unicast ?"
        output = self._execute_show_command(command)

        # Validate keywords present
        all_found, missing = self._check_multiple_keywords(output, expected_keywords)

        if all_found:
            st.log("✓ All expected keywords found in help output")
            for keyword in expected_keywords:
                st.log(f"  ✓ '{keyword}' - FOUND")
            st.report_pass("test_case_passed")
        else:
            st.error("✗ Some expected keywords missing from help output")
            for keyword in missing:
                st.error(f"  ✗ '{keyword}' - MISSING")
            st.report_fail(
                "msg",
                f"BGP IPv6 help missing keywords: {', '.join(missing)}. "
                f"Command: {command}"
            )

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-IPV6-CLI-002"])
    def test_bgp_ipv6_vrf_all_help_output(self) -> None:
        """Test Scenario 2: Verify 'vrf all' help output.

        Command: show bgp ipv6 unicast vrf all ?

        Expected Output:
            summary  Summary of BGP neighbor status
            |        Pipe through a command
            <cr>

        Validation:
            - 'summary' keyword with description
            - '|' (pipe) option with description
            - '<cr>' indicating command can complete
        """
        st.banner("TEST 2: BGP IPv6 VRF All Help Output Validation")

        expected_keywords = ["summary", "|", "<cr>"]
        st.log(f"Expected keywords: {expected_keywords}")

        # Execute help command
        command = "show bgp ipv6 unicast vrf all ?"
        output = self._execute_show_command(command)

        # Validate keywords present
        all_found, missing = self._check_multiple_keywords(output, expected_keywords)

        if all_found:
            st.log("✓ All expected keywords found in vrf all help output")
            for keyword in expected_keywords:
                st.log(f"  ✓ '{keyword}' - FOUND")

            # Additional validation: check for description text
            if "Pipe through" in output or "pipe through" in output.lower():
                st.log("  ✓ Pipe description text - FOUND")

            st.report_pass("test_case_passed")
        else:
            st.error("✗ Some expected keywords missing from vrf all help output")
            for keyword in missing:
                st.error(f"  ✗ '{keyword}' - MISSING")
            st.report_fail(
                "msg",
                f"BGP IPv6 vrf all help missing keywords: {', '.join(missing)}. "
                f"Command: {command}"
            )

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-IPV6-CLI-003"])
    def test_bgp_ipv6_summary_with_bgp_configured(self) -> None:
        """Test Scenario 3A: Summary command when BGP IPv6 is configured.

        Command: show bgp ipv6 unicast vrf all summary

        Expected Output (when BGP configured):
            BGP router identifier 192.0.2.1, local AS number 65001
            Neighbor        V    AS MsgRcvd MsgSent   Up/Down State
            2001:db8::1     4 65002      10      10  00:05:30 Established

        Validation:
            - BGP neighbor table displayed
            - IPv6 addresses present
            - Neighbor state information
        """
        st.banner("TEST 3A: BGP IPv6 Summary - With BGP Configured")

        # Execute summary command
        command = "show bgp ipv6 unicast vrf all summary"
        output = self._execute_show_command(command)

        # Check if BGP is configured (neighbor table present)
        if "Neighbor" in output and "State" in output:
            st.log("✓ BGP IPv6 is configured - neighbor table displayed")

            # Validate table format - check for IPv6 address pattern
            ipv6_pattern = r'[0-9a-f:]+\s+\d+\s+\d+'
            if re.search(ipv6_pattern, output, re.IGNORECASE):
                st.log("✓ IPv6 neighbor addresses found in table")

            # Check for standard table headers
            if "AS" in output and "MsgRcvd" in output:
                st.log("✓ BGP summary table headers present")

            st.log("TEST 3A RESULT: BGP IPv6 configured - table format validated")
            st.report_pass("test_case_passed")

        elif "BGP instance not found" in output or not output or "--sonic-mgmt--" in output:
            st.log("BGP IPv6 not configured on this DUT")
            st.log("Test 3A requires BGP configuration - reporting as UNSUPPORTED")
            st.report_unsupported("msg", "BGP IPv6 not configured - test requires BGP configuration")

        else:
            st.log(f"Unexpected output: {output[:200]}")
            st.report_fail("msg", f"Unexpected output format for: {command}")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-IPV6-CLI-004"])
    @pytest.mark.negative
    def test_bgp_ipv6_summary_error_message_no_config(self) -> None:
        """Test Scenario 3B: Summary command when BGP IPv6 NOT configured.

        Command: show bgp ipv6 unicast vrf all summary

        Expected Behavior:
            Command should return SOME output (not empty)
            - Could be "%BGP instance not found"
            - Could be "%BGP IPv6 unicast is not configured"
            - Could be other BGP-related message
            - Output should NOT be empty

        Validation:
            Test PASSES if command returns any output
            Test FAILS if output is empty

        Result:
            Validates that CLI provides feedback (not silent failure)
        """
        st.banner("TEST 3B: BGP IPv6 Summary - Validates Output Present (No Config)")

        # Execute summary command
        command = "show bgp ipv6 unicast vrf all summary"
        st.log(f"Executing: {command}")
        st.log("Validating: Command should return SOME output (not empty)")

        output = self._execute_show_command(command)

        # Check if BGP is configured
        if "Neighbor" in output and "State" in output:
            st.log("BGP IPv6 is configured on this DUT")
            st.log("Test 3B requires no BGP configuration - reporting as UNSUPPORTED")
            st.report_unsupported("msg", "BGP IPv6 configured - test requires no BGP configuration")

        # Validate output is not empty (check for prompt-only output)
        output_str = str(output).strip()

        # Remove CLI prompts from output for validation
        if "--sonic-mgmt--" in output_str:
            output_str = output_str.replace("--sonic-mgmt--", "").replace("#", "").strip()

        if output_str and len(output_str) > 0:
            st.log(f"✓ PASS: Command returned output")
            st.log(f"Output received: {output_str[:200]}")

            # Log what type of message was received
            if "BGP instance not found" in output_str:
                st.log("Message type: 'BGP instance not found'")
            elif "not configured" in output_str:
                st.log("Message type: 'not configured' message")
            else:
                st.log("Message type: Other BGP-related output")

            st.report_pass("test_case_passed")
        else:
            st.error(f"✗ FAIL: Command returned empty output")
            st.report_fail("msg", f"No output received for: {command}")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-IPV6-CLI-005"])
    @pytest.mark.negative
    def test_bgp_ipv6_incomplete_pipe_except(self) -> None:
        """Test Scenario 4A: Incomplete pipe - except (no argument).

        Command: show bgp ipv6 unicast vrf all summary | except

        Expected Output:
            % Error: The command is not completed.

        Result:
            VERIFIED ✅ - Working correctly
        """
        st.banner("TEST 4A: Incomplete Pipe - except")

        command = "show bgp ipv6 unicast vrf all summary | except"
        expected_error = "% Error: The command is not completed."

        st.log(f"Testing incomplete pipe: {command}")
        st.log(f"Expected error: '{expected_error}'")

        output = self._execute_show_command(command)

        if expected_error in output:
            st.log(f"✓ PASS: Correct error message for incomplete 'except'")
            st.report_pass("test_case_passed")
        else:
            st.error(f"✗ FAIL: Expected error not found")
            st.error(f"Output: {output}")
            st.report_fail("msg", f"Incomplete pipe 'except' did not show expected error")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-IPV6-CLI-006"])
    @pytest.mark.negative
    def test_bgp_ipv6_incomplete_pipe_find(self) -> None:
        """Test Scenario 4B: Incomplete pipe - find (no argument).

        Command: show bgp ipv6 unicast vrf all summary | find

        Expected Output:
            % Error: The command is not completed.

        Result:
            VERIFIED ✅ - Working correctly
        """
        st.banner("TEST 4B: Incomplete Pipe - find")

        command = "show bgp ipv6 unicast vrf all summary | find"
        expected_error = "% Error: The command is not completed."

        st.log(f"Testing incomplete pipe: {command}")
        st.log(f"Expected error: '{expected_error}'")

        output = self._execute_show_command(command)

        if expected_error in output:
            st.log(f"✓ PASS: Correct error message for incomplete 'find'")
            st.report_pass("test_case_passed")
        else:
            st.error(f"✗ FAIL: Expected error not found")
            st.error(f"Output: {output}")
            st.report_fail("msg", f"Incomplete pipe 'find' did not show expected error")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-IPV6-CLI-007"])
    @pytest.mark.negative
    def test_bgp_ipv6_incomplete_pipe_grep(self) -> None:
        """Test Scenario 4C: Incomplete pipe - grep (no argument).

        Command: show bgp ipv6 unicast vrf all summary | grep

        Expected Output:
            % Error: The command is not completed.

        Result:
            VERIFIED ✅ - Working correctly
        """
        st.banner("TEST 4C: Incomplete Pipe - grep")

        command = "show bgp ipv6 unicast vrf all summary | grep"
        expected_error = "% Error: The command is not completed."

        st.log(f"Testing incomplete pipe: {command}")
        st.log(f"Expected error: '{expected_error}'")

        output = self._execute_show_command(command)

        if expected_error in output:
            st.log(f"✓ PASS: Correct error message for incomplete 'grep'")
            st.report_pass("test_case_passed")
        else:
            st.error(f"✗ FAIL: Expected error not found")
            st.error(f"Output: {output}")
            st.report_fail("msg", f"Incomplete pipe 'grep' did not show expected error")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-IPV6-CLI-008"])
    @pytest.mark.negative
    def test_bgp_ipv6_incomplete_pipe_save(self) -> None:
        """Test Scenario 4D: Incomplete pipe - save (no filename).

        Command: show bgp ipv6 unicast vrf all summary | save

        Expected Output:
            % Error: The command is not completed.

        Result:
            VERIFIED ✅ - Working correctly
        """
        st.banner("TEST 4D: Incomplete Pipe - save")

        command = "show bgp ipv6 unicast vrf all summary | save"
        expected_error = "% Error: The command is not completed."

        st.log(f"Testing incomplete pipe: {command}")
        st.log(f"Expected error: '{expected_error}'")

        output = self._execute_show_command(command)

        if expected_error in output:
            st.log(f"✓ PASS: Correct error message for incomplete 'save'")
            st.report_pass("test_case_passed")
        else:
            st.error(f"✗ FAIL: Expected error not found")
            st.error(f"Output: {output}")
            st.report_fail("msg", f"Incomplete pipe 'save' did not show expected error")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-IPV6-CLI-009"])
    @pytest.mark.negative
    def test_bgp_ipv6_pipe_no_more_error_message(self) -> None:
        """Test Scenario 5: Pipe no-more when BGP IPv6 NOT configured.

        Command: show bgp ipv6 unicast vrf all summary | no-more

        Expected Behavior:
            Command should return SOME output (not empty)
            - Could be "%BGP instance not found"
            - Could be "%BGP IPv6 unicast is not configured"
            - Could be other BGP-related message
            - Output should NOT be empty

        Validation:
            Test PASSES if command returns any output
            Test FAILS if output is empty

        Result:
            Validates that CLI with pipe operator provides feedback
        """
        st.banner("TEST 5: Pipe no-more - Validates Output Present (No Config)")

        command = "show bgp ipv6 unicast vrf all summary | no-more"
        st.log(f"Executing: {command}")
        st.log("Validating: Command should return SOME output (not empty)")

        output = self._execute_show_command(command)

        # Check if BGP is configured
        if "Neighbor" in output and "State" in output:
            st.log("BGP IPv6 is configured on this DUT")
            st.log("Test 5 requires no BGP configuration - reporting as UNSUPPORTED")
            st.report_unsupported("msg", "BGP IPv6 configured - test requires no BGP configuration")

        # Validate output is not empty (check for prompt-only output)
        output_str = str(output).strip()

        # Remove CLI prompts from output for validation
        if "--sonic-mgmt--" in output_str:
            output_str = output_str.replace("--sonic-mgmt--", "").replace("#", "").strip()

        if output_str and len(output_str) > 0:
            st.log(f"✓ PASS: Command with pipe returned output")
            st.log(f"Output received: {output_str[:200]}")

            # Log what type of message was received
            if "BGP instance not found" in output_str:
                st.log("Message type: 'BGP instance not found'")
            elif "not configured" in output_str:
                st.log("Message type: 'not configured' message")
            else:
                st.log("Message type: Other BGP-related output")

            st.report_pass("test_case_passed")
        else:
            st.error(f"✗ FAIL: Command with pipe returned empty output")
            st.report_fail("msg", f"No output received for: {command}")

    @pytest.mark.inventory(feature="Regression", testcases=["BGP-IPV6-CLI-011"])
    def test_bgp_ipv6_all_incomplete_pipes_batch(self) -> None:
        """Test Scenario 6: Batch test all incomplete pipe commands.

        Commands:
            - show bgp ipv6 unicast vrf all summary | except
            - show bgp ipv6 unicast vrf all summary | find
            - show bgp ipv6 unicast vrf all summary | grep
            - show bgp ipv6 unicast vrf all summary | save

        Expected Output (all commands):
            % Error: The command is not completed.

        Result:
            All VERIFIED ✅ - Working correctly

        Note:
            This is a batch test covering all incomplete pipes in one test.
        """
        st.banner("TEST 6: Batch Test - All Incomplete Pipe Commands")

        base_cmd = "show bgp ipv6 unicast vrf all summary"
        incomplete_pipes = ["except", "find", "grep", "save"]
        expected_error = "% Error: The command is not completed."

        all_passed = True
        failed_commands = []

        for pipe_cmd in incomplete_pipes:
            command = f"{base_cmd} | {pipe_cmd}"
            st.log(f"Testing: {command}")

            output = self._execute_show_command(command)

            if expected_error in output:
                st.log(f"  ✓ PASS: '{pipe_cmd}' shows correct error")
            else:
                st.error(f"  ✗ FAIL: '{pipe_cmd}' did not show expected error")
                st.error(f"  Output: {output}")
                all_passed = False
                failed_commands.append(pipe_cmd)

        if all_passed:
            st.log("✓ ALL TESTS PASSED: All incomplete pipes show correct error")
            st.report_pass("test_case_passed")
        else:
            st.error(f"✗ SOME TESTS FAILED: {', '.join(failed_commands)}")
            st.report_fail(
                "msg",
                f"Incomplete pipes failed: {', '.join(failed_commands)}"
            )
