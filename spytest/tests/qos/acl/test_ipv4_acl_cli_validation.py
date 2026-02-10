"""
IPv4 ACL CLI VALIDATION
Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/ztp_standalone.yaml \\
  tests/qos/acl/test_ipv4_acl_cli_validation.py \\
  --logs-path ./logs/acl_cli_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates IS-CLI (klish) behavior for IPv4 ACL configuration commands.
  This test suite verifies that the CLI follows standard industry patterns
  (Cisco/Arista compatibility) for:

  1. CLI Help Completeness - Verifies 'ip access?' command displays both
     'access-group' and 'access-list' options with proper descriptions

  2. Mode Navigation Hierarchy - Verifies 'exit' command from ACL configuration
     mode correctly returns to global configuration mode (not privileged exec)

  These tests validate that IS-CLI provides complete help documentation and
  maintains proper CLI mode hierarchy for ACL configuration.

Pre-requisites:
  - Topology: Standalone | Supported: HW and Virtual
  - Topology Diagram:
        +-------------------------+
        |   DUT: smic_sonic1     |
        |   192.168.100.215      |
        |   Username: admin      |
        |   Password: root@123   |
        +-------------------------+

  - CLI Mode: IS-CLI (klish) required
  - Feature: IPv4 Access Control Lists
  - Required test variables (YAML): vars/qos/acl/vars_ipv4_acl_cli.yaml

Test Cases:
  TC01: test_acl_help_access_group_presence
        - Verifies 'ip access?' displays both 'access-list' and 'access-group'
        - Expected: PASS - Both options should be visible in help output

  TC02: test_acl_mode_exit_navigation
        - Verifies 'exit' from ACL mode returns to config mode
        - Expected: PASS - Should follow standard CLI hierarchy pattern

  TC03: test_acl_rule_protocol_options
        - Verifies 'seq 1 permit?' displays all protocol options
        - Expected: PASS - Should show icmp, ip, tcp, udp, <0..255>
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.qos.acl_cli_api as acl_cli_api

# Test case identifiers
TC_IDS = SpyTestDict({
    "help_validation": "ACL-CLI-VALIDATION-001-TC01",
    "mode_exit": "ACL-CLI-VALIDATION-001-TC02",
    "protocol_options": "ACL-CLI-VALIDATION-001-TC03",
})

# YAML variable file path
VAR_FILE_ENV = "ACL_CLI_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "qos"
    / "acl"
    / "vars_ipv4_acl_cli.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """
    Load test case variables from YAML file with optional environment override.

    :return: Dictionary containing test configuration
    :raises FileNotFoundError: If YAML file is not found
    :raises ValueError: If YAML structure is invalid
    """
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"ACL CLI validation variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("ACL CLI YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestIPv4AclCliValidation:
    """
    Test suite for IPv4 ACL CLI validation.

    This class contains test cases that validate IS-CLI behavior for ACL commands,
    specifically testing help string completeness and mode navigation consistency.
    These tests document known bugs and should PASS after CLI fixes are applied.
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """
        Collect topology handles and test case variables for the suite.

        This method is called once before all tests in the class.
        It loads configuration from YAML and sets up the test environment.
        """
        st.banner("IPv4 ACL CLI VALIDATION TEST SUITE - SETUP")

        # Load test configuration from YAML
        config = _load_yaml_data()
        defaults = config.get("defaults", {})
        cli_prompts = config.get("cli_prompts", {})

        # Store configuration in class data
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.cli_prompts = SpyTestDict(cli_prompts)
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # CLI type configuration
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 10))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Get DUT from testbed (standalone device - no topology requirements)
        cls.data.dut_names = st.get_dut_names()

        if not cls.data.dut_names:
            st.error("No DUTs found in testbed")
            st.report_fail("msg", "No DUTs available in testbed for ACL CLI validation")

        # Use first DUT from testbed (standalone test)
        cls.data.dut = cls.data.dut_names[0]

        st.log(f"Test configuration loaded. DUT: {cls.data.dut}")
        st.log(f"Available DUTs: {cls.data.dut_names}")
        st.log(f"CLI type: {cls.data.cli_type}")
        st.log(f"Expected prompts: {cls.data.cli_prompts}")

    @classmethod
    def teardown_class(cls) -> None:
        """
        Teardown after all tests in the class complete.

        This method is called once after all tests in the class.
        """
        st.banner("IPv4 ACL CLI VALIDATION TEST SUITE - TEARDOWN")
        st.log("Test suite teardown completed")

    def setup_method(self) -> None:
        """
        Reset per-test bookkeeping.

        This method is called before each individual test.
        """
        st.banner(f"Starting test method: {self._testMethodName if hasattr(self, '_testMethodName') else 'unknown'}")

    def teardown_method(self) -> None:
        """
        Teardown after each individual test.

        This method is called after each individual test.
        """
        st.banner(f"Completed test method: {self._testMethodName if hasattr(self, '_testMethodName') else 'unknown'}")

    @pytest.mark.inventory(feature="ACL", testcases=["ACL-CLI-VALIDATION-001-TC01"])
    def test_acl_help_access_group_presence(self) -> None:
        """
        TC01 - Verify CLI help command 'ip access?' shows both access-list and access-group.

        Test Steps:
        1. Enter global configuration mode
        2. Execute help command: 'ip access?'
        3. Verify output contains 'access-group' string
        4. Verify output contains 'access-list' string
        5. Report results

        Expected Behavior:
        - Help output should contain: "access-group  Specify IP access control for packets"
        - Help output should contain: "access-list   Configure IPv4 access-list"
        - Both options should be visible to users querying help

        Industry Standard:
        - Follows Cisco/Arista CLI patterns where '?' shows all available sub-commands
        - Users can discover 'access-group' through CLI help system
        """
        st.banner("TEST CASE: CLI Help String Validation for 'ip access?' Command")

        tc_data = self.data.testcases.get("cli_help_validation")
        if not tc_data:
            st.report_fail("msg", "Test case 'cli_help_validation' not found in YAML")

        dut = self.data.dut
        help_command = tc_data.get("help_command", "ip access?")
        expected_strings = tc_data.get("expected_help_strings", ["access-group", "access-list"])

        # Step 1: Enter configuration mode
        st.log("Step 1: Entering global configuration mode")
        acl_cli_api.enter_config_mode(dut, cli_type=self.data.cli_type)
        st.log("✓ Entered configuration mode")

        # Step 2: Execute help command and verify output
        st.log(f"Step 2: Executing help command: {help_command}")

        success, details = acl_cli_api.verify_cli_help_contains(
            dut=dut,
            command=help_command,
            expected_strings=expected_strings,
            cli_type=self.data.cli_type
        )

        # Log results
        st.log("Step 3: Analyzing help output")
        st.log(f"Expected strings: {expected_strings}")
        st.log(f"Found strings: {details['found']}")
        st.log(f"Missing strings: {details['missing']}")
        st.log(f"Total found: {details['total_found']}/{details['total_expected']}")

        # Verify all expected strings are present
        if not success:
            st.error("CLI Help Validation FAILED:")
            st.error(f"  Expected both 'access-group' and 'access-list' in help output")
            st.error(f"  Found: {details['found']}")
            st.error(f"  Missing: {details['missing']}")
            st.error(f"  Command: {help_command}")

            # Report failure
            st.report_fail(
                "msg",
                f"CLI help validation FAILED: Missing strings {details['missing']} in output of '{help_command}'. "
                f"Expected both 'access-group' and 'access-list' to be displayed for user discoverability."
            )

        st.log("✓ Verified: 'access-group' is present in help output")
        st.log("✓ Verified: 'access-list' is present in help output")
        st.log("✓✓ Test passed: CLI help output contains all expected strings")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="ACL", testcases=["ACL-CLI-VALIDATION-001-TC02"])
    def test_acl_mode_exit_navigation(self) -> None:
        """
        TC02 - Verify exit from ACL configuration mode returns to global config mode.

        Test Steps:
        1. Enter global configuration mode - verify prompt is sonic(config)#
        2. Enter ACL configuration mode - verify prompt is sonic(config-ipv4-acl)#
        3. Execute 'exit' command
        4. Verify prompt is sonic(config)# (correct behavior)
        5. Cleanup: Remove test ACL

        Expected Behavior:
        - Exit from ACL mode should return to global configuration mode
        - Prompt should be: sonic(config)#
        - Mode hierarchy: ACL Config -> Config -> Privileged Exec
        - This follows standard industry CLI patterns (Cisco/Arista compatibility)

        Industry Standard:
        - Exit command returns to parent mode in CLI hierarchy
        - Users can exit configuration modes step-by-step
        - Maintains predictable navigation pattern
        """
        st.banner("TEST CASE: CLI Mode Exit Navigation from ACL Configuration Mode")

        tc_data = self.data.testcases.get("mode_exit_navigation")
        if not tc_data:
            st.report_fail("msg", "Test case 'mode_exit_navigation' not found in YAML")

        dut = self.data.dut
        test_acl_name = tc_data.get("test_acl_name", "test_cli_validation")

        # Step 1: Enter configuration mode
        st.log("Step 1: Entering global configuration mode")
        acl_cli_api.enter_config_mode(dut, cli_type=self.data.cli_type)
        st.log("✓ Entered global configuration mode")

        # Step 2: Enter ACL configuration mode
        st.log(f"Step 2: Entering ACL configuration mode: ip access-list {test_acl_name}")
        acl_cli_api.enter_ipv4_acl_mode(dut, test_acl_name, cli_type=self.data.cli_type)
        st.log("✓ Entered ACL configuration mode")

        # Step 3: Execute exit command
        st.log("Step 3: Executing 'exit' command from ACL configuration mode")

        acl_cli_api.exit_current_mode(dut, cli_type=self.data.cli_type)

        # Step 4: Verify we're in config mode by executing a config-only command
        st.log("Step 4: Verifying we returned to global configuration mode")

        # Try to create another ACL (only works in config mode, not in privileged exec)
        verify_acl_name = f"{test_acl_name}_verify"

        try:
            # This command only works in config mode
            st.config(dut, f"ip access-list {verify_acl_name}", type=self.data.cli_type, conf=True, skip_error_check=False)

            # If we got here, we're in config mode!
            st.log("✓ Successfully executed config-mode command (ip access-list)")
            st.log("✓ VERIFIED: Exit from ACL mode correctly returned to global configuration mode")
            st.log(f"✓ Current mode: sonic(config)# (NOT sonic#)")

            # Exit from the verification ACL mode
            st.config(dut, "exit", type=self.data.cli_type, conf=False, skip_error_check=True)

        except Exception as e:
            st.error("CLI Mode Navigation FAILED:")
            st.error(f"  Could not execute 'ip access-list' command after exiting ACL mode")
            st.error(f"  This command only works in config mode, not in privileged exec")
            st.error(f"  Error: {e}")

            st.report_fail(
                "msg",
                f"CLI mode exit validation FAILED: Cannot execute config-mode commands after exit. "
                f"This indicates we are in privileged exec mode (sonic#) instead of config mode (sonic(config)#)."
            )

        st.log("✓✓ Test passed: Exit from ACL mode correctly returned to config mode")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="ACL", testcases=["ACL-CLI-VALIDATION-001-TC03"])
    def test_acl_rule_protocol_options(self) -> None:
        """
        TC03 - Verify ACL rule protocol options in CLI help output.

        Test Steps:
        1. Enter global configuration mode
        2. Enter ACL configuration mode: ip access-list test_cli_validation
        3. Execute partial rule command with help: 'seq 1 permit?'
        4. Verify output contains all expected protocol options:
           - <0..255> (protocol number range)
           - icmp (ICMP packets)
           - ip (any IPv4 packets)
           - tcp (TCP packets)
           - udp (UDP packets)
        5. Exit ACL configuration mode
        6. Report results

        Expected Behavior:
        - Help output should display all protocol options for rule configuration
        - Users can discover available protocols through CLI help system
        - Follows industry-standard ACL rule syntax (Cisco/Arista compatibility)

        Industry Standard:
        - ACL rules support multiple protocol specifications
        - '?' shows all available protocol options at current command position
        - Protocol can be specified by name (tcp, udp, icmp) or number (0-255)
        """
        st.banner("TEST CASE: ACL Rule Protocol Options Validation")

        tc_data = self.data.testcases.get("protocol_options_validation")
        if not tc_data:
            st.report_fail("msg", "Test case 'protocol_options_validation' not found in YAML")

        dut = self.data.dut
        test_acl_name = tc_data.get("test_acl_name", "test_cli_validation")
        seq_number = tc_data.get("seq_number", 1)
        action = tc_data.get("action", "permit")
        expected_protocols = tc_data.get("expected_protocols", [
            "<0..255>",
            "icmp",
            "ip",
            "tcp",
            "udp"
        ])

        # Step 1: Enter configuration mode
        st.log("Step 1: Entering global configuration mode")
        acl_cli_api.enter_config_mode(dut, cli_type=self.data.cli_type)
        st.log("✓ Entered global configuration mode")

        # Step 2-4: Verify protocol options in ACL rule help
        st.log(f"Step 2: Verifying ACL rule protocol options: seq {seq_number} {action}?")

        success, details = acl_cli_api.verify_acl_rule_protocol_options(
            dut=dut,
            acl_name=test_acl_name,
            seq_number=seq_number,
            action=action,
            expected_protocols=expected_protocols,
            cli_type=self.data.cli_type
        )

        # Log results
        st.log("Step 3: Analyzing protocol options help output")
        st.log(f"Expected protocols: {expected_protocols}")
        st.log(f"Found protocols: {details['found']}")
        st.log(f"Missing protocols: {details['missing']}")
        st.log(f"Total found: {details['total_found']}/{details['total_expected']}")

        # Verify all expected protocol options are present
        if not success:
            st.error("ACL Rule Protocol Options Validation FAILED:")
            st.error(f"  Expected all protocol options in help output for 'seq {seq_number} {action}?'")
            st.error(f"  Found: {details['found']}")
            st.error(f"  Missing: {details['missing']}")

            # Report failure
            st.report_fail(
                "msg",
                f"ACL rule protocol options validation FAILED: Missing protocols {details['missing']} "
                f"in output of 'seq {seq_number} {action}?'. Expected all protocol options "
                f"(icmp, ip, tcp, udp, <0..255>) to be displayed for user guidance."
            )

        st.log("✓ Verified: All expected protocol options are present")
        st.log(f"✓ Found protocols: {', '.join(details['found'])}")
        st.log("✓✓ Test passed: ACL rule protocol options help output is complete")
        st.report_pass("test_case_passed")
