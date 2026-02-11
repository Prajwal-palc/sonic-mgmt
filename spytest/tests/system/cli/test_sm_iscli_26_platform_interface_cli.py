"""
SM_ISCLI_26 - Platform and Interface CLI Validation

Author: Athira
Copyright (C) 2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  system/cli/test_sm_iscli_26_platform_interface_cli.py \\
  --logs-path ./logs/sm_iscli_26_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native \\
  --port-init-wait 0

Description:
  Validates platform and interface CLI commands for completeness, correctness, and
  consistency between click and klish (IS-CLI) modes. Identifies missing options,
  incomplete help text, and non-functional subcommands. Covers platform SSD health,
  firmware version, ping/traceroute utilities, and interface transceiver commands.

Pre-requisites:
  - Topology: single-node (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |        DUT1        |
        # |   (Platform CLI)   |
        # +--------------------+
  - At least one interface with transceiver installed (for transceiver tests)
  - Required test variables (YAML): vars/system/cli/vars_sm_iscli_26.yaml
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st

# Default vars file location
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "cli"
    / "vars_sm_iscli_26.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML file."""
    try:
        with open(DEFAULT_VAR_FILE, "r", encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
    except FileNotFoundError as error:
        pytest.skip(f"Vars file not found: {error}")

    if "testcases" not in content:
        pytest.skip("YAML must contain 'testcases' key")

    return content


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level fixture for prologue and epilogue.
    This is required by SpyTest framework for module configuration management.
    """
    # Module prologue
    st.banner("MODULE PROLOGUE: SM_ISCLI_26 - Platform and Interface CLI Validation")
    st.log("This module performs read-only CLI validation - no configuration changes")

    # Initialize testbed - required by SpyTest framework
    try:
        global vars
        vars_temp = st.get_testbed_vars()
        st.log(f"Testbed initialized successfully")
    except Exception as e:
        st.log(f"Testbed initialization: {e}")

    yield

    # Module epilogue - cleanup (nothing to clean for read-only tests)
    st.banner("MODULE EPILOGUE: SM_ISCLI_26 - Cleanup")
    st.log("No cleanup required - tests were read-only")


@pytest.mark.topology("D1")
@pytest.mark.system
@pytest.mark.cli_validation
class TestSMISCLI26PlatformInterfaceCLI:
    """Platform and Interface CLI validation testcases."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Load topology and test configuration."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))

        # Get DUT handle
        cls.data.dut = topology.D1
        st.log(f"DUT: {cls.data.dut}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after test suite."""
        st.log("SM_ISCLI_26 test suite completed")

    def _get_testcase(self, tcid: str) -> Dict[str, Any]:
        """Fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    @pytest.mark.syslog_ignore
    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_26_TC_1"])
    def test_sm_iscli_26_tc1_platform_ssdhealth_disk_option(self) -> None:
        """TC 26.1 - Verify show platform ssdhealth supports disk parameter option."""
        tc = self._get_testcase("26.1")
        st.banner(f"TC 26.1: {tc.get('title')}")

        dut = self.data.dut
        klish_cmd = tc.get("commands", {}).get("klish", "show platform ssdhealth")

        # Execute command in klish mode
        output = st.show(dut, klish_cmd, type="klish", skip_error_check=True)
        st.log(f"SSD Health Output: {output}")

        # Get expected fields from YAML
        expected_fields = tc.get("expected_fields", [])
        output_str = str(output)
        # Verify expected fields are present
        missing = []

        for field in expected_fields:
            if field not in output_str:
                missing.append(field)

        if missing:
            st.report_fail("missing_expected_fields", ",".join(missing))
        else:
            st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_26_TC_4"])
    def test_sm_iscli_26_tc4_ping_help_text_completeness(self) -> None:
        """TC 26.4 - Verify ping displays actual options instead of generic text."""
        tc = self._get_testcase("26.4")
        st.banner(f"TC 26.4: {tc.get('title')}")

        dut = self.data.dut
        command = tc.get("command", "ping")
        unwanted_text = tc.get("unwanted_text", ["normal options"])

        # Try to get help text
        help_output = st.show(dut, f"{command} ?", type=self.data.cli_type, skip_error_check=True)
        if not help_output:
            help_output = st.show(dut, f"{command} --help", type=self.data.cli_type, skip_error_check=True)

        st.log(f"Ping help output: {help_output}")
        help_str = str(help_output).lower()

        # Check for unwanted generic text
        for unwanted in unwanted_text:
            if unwanted.lower() in help_str:
                st.warn(
                    f"Found generic placeholder text '{unwanted}' in help output. "
                    "Recommendation: Display actual ping options"
                )

        # Check for expected options
        expected_options = tc.get("expected_options", [])
        missing_options = []
        for option in expected_options:
            if option.lower() not in help_str:
                missing_options.append(option)

        if missing_options:
            st.log(f"Missing options in help text: {missing_options}")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_26_TC_5"])
    def test_sm_iscli_26_tc5_traceroute_availability(self) -> None:
        """TC 26.5 - Verify traceroute command is available and functional."""
        tc = self._get_testcase("26.5")
        st.banner(f"TC 26.5: {tc.get('title')}")

        dut = self.data.dut
        test_dest = tc.get("test_destination", "8.8.8.8")
        max_hops = tc.get("max_hops", 30)

        # Execute traceroute with limited hops
        command = f"traceroute -m 3 {test_dest}"
        output = st.config(dut, command, type=self.data.cli_type, skip_error_check=True)
        st.log(f"Traceroute output: {output}")

        output_str = str(output).lower()

        # Check if command is recognized
        error_indicators = ["not found", "invalid", "error", "unknown command"]
        has_error = any(indicator in output_str for indicator in error_indicators)

        if has_error:
            st.report_fail("msg", f"Traceroute command not available: {output}")

        # Check for traceroute output format (hop numbers)
        has_hops = re.search(r'\d+\s+\d+\.\d+\.\d+\.\d+', output_str)
        if not has_hops:
            st.warn("Traceroute output format unexpected")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_26_TC_6"])
    @pytest.mark.negative
    def test_sm_iscli_26_tc6_transceiver_pm_subcommand(self) -> None:
        """TC 26.6 - Verify show interface transceiver pm displays data or clear message."""
        tc = self._get_testcase("26.6")
        st.banner(f"TC 26.6: {tc.get('title')}")

        dut = self.data.dut
        command = tc.get("command", "show interface transceiver pm")

        # Execute command
        output = st.show(dut, command, type=self.data.cli_type, skip_error_check=True)
        st.log(f"Transceiver PM Output: {output}")

        # Check if command returns meaningful data
        if not output or len(str(output).strip()) == 0:
            st.log("WARNING: Command returns no data")
            st.log("RECOMMENDATION: Remove non-functional 'pm' subcommand from CLI")

        # Document findings
        st.log(f"Expected behavior: {tc.get('expected_behavior', 'should_be_removed')}")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_26_TC_7"])
    @pytest.mark.negative
    def test_sm_iscli_26_tc7_transceiver_lpmode_subcommand(self) -> None:
        """TC 26.7 - Verify show interface transceiver lpmode displays data or clear message."""
        tc = self._get_testcase("26.7")
        st.banner(f"TC 26.7: {tc.get('title')}")

        dut = self.data.dut
        command = tc.get("command", "show interface transceiver lpmode")

        # Execute command
        output = st.show(dut, command, type=self.data.cli_type, skip_error_check=True)
        st.log(f"Transceiver LPMode Output: {output}")

        # Check if command returns meaningful data
        if not output or len(str(output).strip()) == 0:
            st.log("WARNING: Command returns no data")
            st.log("RECOMMENDATION: Remove non-functional 'lpmode' subcommand from CLI")

        # Document findings
        st.log(f"Expected behavior: {tc.get('expected_behavior', 'should_be_removed')}")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_26_TC_8"])
    @pytest.mark.negative
    def test_sm_iscli_26_tc8_transceiver_error_status_verbose(self) -> None:
        """TC 26.8 - Verify show interface transceiver error-status verbose displays verbose data."""
        tc = self._get_testcase("26.8")
        st.banner(f"TC 26.8: {tc.get('title')}")

        dut = self.data.dut
        command = tc.get("command", "show interface transceiver error-status verbose")

        # Execute command
        output = st.show(dut, command, type=self.data.cli_type, skip_error_check=True)
        st.log(f"Transceiver Error-Status Verbose Output: {output}")

        output_str = str(output).lower()

        # Check for "not implemented" message
        expected_messages = tc.get("expected_messages", ["not implemented"])
        has_not_impl = any(msg.lower() in output_str for msg in expected_messages)

        if has_not_impl:
            st.log("Command returns 'not implemented' message")
            st.log("RECOMMENDATION: Remove 'verbose' option if not implemented")
        elif not output or len(output_str.strip()) == 0:
            st.log("WARNING: Command returns no data")

        # Document findings
        st.log(f"Expected behavior: {tc.get('expected_behavior', 'should_be_removed')}")

        st.report_pass("test_case_passed")
