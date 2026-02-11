"""
SM_ISCLI_28: BGP Configuration Mode - Show Configuration Verification

Author: Athira
Copyright (C) 2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  tests/routing/bgp/test_sm_iscli_28_bgp_show_config.py \\
  --logs-path ./logs/sm_iscli_28_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native \\
  --port-init-wait 0

Description:
  Verify that 'show configuration' command displays complete BGP configuration
  when executed from within BGP configuration modes (router-bgp, address-family,
  neighbor contexts). This test validates the fix for a bug where SMC IS-CLI did
  not show BGP configs when 'show configuration' was run from BGP configuration mode.

  Bug Scenario:
  1. Configure BGP in IS-CLI
  2. While in BGP configuration mode, execute 'show configuration'
  3. Expected: All relevant BGP configuration should be displayed
  4. Bug (old behavior): SMC IS-CLI would not show BGP configs

Pre-requisites:
  - Topology: single-node (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Single Device Topology
        # +--------------------+
        # |        DUT1        |
        # |   (BGP Router)     |
        # |   AS 65001         |
        # +--------------------+

  - SONiC version: 202505-smci-dev-iscli or later
  - CLI type: IS-CLI (klish) - Test validates show configuration in BGP modes
  - Required test variables (YAML): vars/routing/bgp/vars_sm_iscli_28.yaml
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
    / "routing"
    / "bgp"
    / "vars_sm_iscli_28.yaml"
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
    st.banner("MODULE PROLOGUE: SM_ISCLI_28 - BGP Show Configuration Validation")
    st.log("Starting BGP show configuration tests")

    # Initialize testbed - required by SpyTest framework
    try:
        vars_temp = st.get_testbed_vars()
        st.log(f"Testbed initialized successfully")
    except Exception as e:
        st.log(f"Testbed initialization: {e}")

    yield

    # Module epilogue - BGP cleanup is handled in teardown_class
    st.banner("MODULE EPILOGUE: SM_ISCLI_28 - Cleanup")
    st.log("BGP configuration cleanup completed in class teardown")


@pytest.mark.topology("D1")
@pytest.mark.routing
@pytest.mark.bgp
@pytest.mark.cli_validation
class TestSMISCLI28BGPShowConfiguration:
    """BGP show configuration validation testcases."""

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

        # Track configured BGP instances for cleanup
        cls.data.bgp_instances = []

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after test suite."""
        st.banner("SM_ISCLI_28: Cleaning up BGP configuration")

        # Remove all BGP instances configured during tests
        for asn in cls.data.bgp_instances:
            cls._cleanup_bgp(asn)

        st.log("SM_ISCLI_28 test suite completed")

    @classmethod
    def _cleanup_bgp(cls, asn: int) -> None:
        """Remove BGP configuration."""
        dut = cls.data.dut
        try:
            # Use direct config command to remove BGP instance
            cmd = f"no router bgp {asn}"
            st.config(dut, cmd, type=cls.data.cli_type, skip_error_check=True)
            st.log(f"Removed BGP AS {asn}")
        except Exception as e:
            st.warn(f"Failed to remove BGP AS {asn}: {e}")

    def _get_testcase(self, tcid: str) -> Dict[str, Any]:
        """Fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    def _execute_show_config_in_mode(
        self, config_commands: List[str], mode_description: str
    ) -> str:
        """
        Execute configuration commands and capture 'show configuration' output.

        Args:
            config_commands: List of CLI commands to execute
            mode_description: Description of the mode for logging

        Returns:
            Output of 'show configuration' command
        """
        dut = self.data.dut

        st.log(f"Entering {mode_description}")

        # Build complete command sequence
        # Start with configure terminal
        full_commands = ["configure terminal"]
        full_commands.extend(config_commands)
        full_commands.append("show configuration")
        full_commands.append("end")

        # Execute commands as a sequence
        cmd_str = "\n".join(full_commands)

        st.log(f"Executing command sequence:\n{cmd_str}")

        # Execute and capture output
        output = st.config(
            dut,
            cmd_str,
            type=self.data.cli_type,
            skip_error_check=True,
            faster_cli=False
        )

        st.log(f"Show configuration output:\n{output}")

        return str(output)

    def _verify_output_contains(
        self, output: str, expected_strings: List[str], testcase_id: str
    ) -> None:
        """
        Verify that output contains all expected strings.

        Args:
            output: CLI output to check
            expected_strings: List of strings that should be present
            testcase_id: Test case ID for error reporting
        """
        missing_strings = []
        output_lower = output.lower()

        for expected in expected_strings:
            # Case-insensitive search
            if expected.lower() not in output_lower:
                missing_strings.append(expected)

        if missing_strings:
            st.error(f"TC {testcase_id}: Missing expected strings in output:")
            for missing in missing_strings:
                st.error(f"  - {missing}")
            st.error(f"Actual output:\n{output}")
            st.report_fail(
                "msg",
                f"TC {testcase_id}: show configuration missing expected content: {missing_strings}"
            )

    def _configure_bgp_full(self, bgp_config: Dict[str, Any]) -> None:
        """
        Configure complete BGP setup based on YAML definition.

        Args:
            bgp_config: BGP configuration dictionary from YAML
        """
        dut = self.data.dut
        asn = bgp_config.get("asn")

        if not asn:
            st.report_fail("msg", "BGP ASN not specified in configuration")

        # Track this ASN for cleanup
        if asn not in self.data.bgp_instances:
            self.data.bgp_instances.append(asn)

        # Build configuration commands
        commands = [f"router bgp {asn}"]

        # Configure address families
        address_families = bgp_config.get("address_families", [])
        for af in address_families:
            if "ipv4_unicast" in af:
                commands.append("address-family ipv4 unicast")
                redistribute = af["ipv4_unicast"].get("redistribute", [])
                for redist in redistribute:
                    commands.append(f"redistribute {redist}")
                commands.append("exit")
            elif "ipv6_unicast" in af:
                commands.append("address-family ipv6 unicast")
                redistribute = af["ipv6_unicast"].get("redistribute", [])
                for redist in redistribute:
                    commands.append(f"redistribute {redist}")
                commands.append("exit")
            elif "l2vpn_evpn" in af:
                commands.append("address-family l2vpn evpn")
                commands.append("exit")

        # Configure neighbors
        neighbors = bgp_config.get("neighbors", [])
        for neighbor in neighbors:
            neighbor_ip = neighbor.get("ip")
            remote_as = neighbor.get("remote_as")
            if neighbor_ip and remote_as:
                commands.append(f"neighbor {neighbor_ip} remote-as {remote_as}")

                # Configure neighbor address families
                neighbor_afs = neighbor.get("address_families", [])
                for naf in neighbor_afs:
                    if "l2vpn_evpn" in naf:
                        commands.append("address-family l2vpn evpn")
                        if naf["l2vpn_evpn"].get("activate"):
                            commands.append("activate")
                        commands.append("exit")

                commands.append("exit")

        commands.append("exit")

        # Execute configuration
        cmd_str = "\n".join(commands)
        st.config(dut, cmd_str, type=self.data.cli_type, skip_error_check=True)
        st.log(f"BGP AS {asn} configured successfully")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_28_TC_1"])
    def test_sm_iscli_28_tc1_show_config_router_bgp_mode(self) -> None:
        """TC 28.1 - Verify show configuration from router-bgp mode."""
        tc = self._get_testcase("28.1")
        st.banner(f"TC 28.1: {tc.get('title')}")

        bgp_config = tc.get("bgp_config")
        asn = bgp_config.get("asn")

        # Track ASN for cleanup
        if asn not in self.data.bgp_instances:
            self.data.bgp_instances.append(asn)

        # Build commands to configure and show
        commands = [
            f"router bgp {asn}",
            "address-family ipv4 unicast",
            "redistribute connected",
            "exit",
            "address-family l2vpn evpn",
            "exit",
            "neighbor 20.1.1.4 remote-as 65001",
            "address-family l2vpn evpn",
            "activate",
            "exit",
            "exit",
        ]

        # Execute show configuration in router-bgp mode
        output = self._execute_show_config_in_mode(commands, "router-bgp mode")

        # Verify expected strings in output
        expected = tc.get("expected_in_output", [])
        self._verify_output_contains(output, expected, "28.1")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_28_TC_2"])
    def test_sm_iscli_28_tc2_show_config_address_family_mode(self) -> None:
        """TC 28.2 - Verify show configuration from address-family mode."""
        tc = self._get_testcase("28.2")
        st.banner(f"TC 28.2: {tc.get('title')}")

        bgp_config = tc.get("bgp_config")
        asn = bgp_config.get("asn")

        # Track ASN for cleanup
        if asn not in self.data.bgp_instances:
            self.data.bgp_instances.append(asn)

        # Build commands - stay in address-family mode
        commands = [
            f"router bgp {asn}",
            "address-family ipv4 unicast",
            "redistribute connected",
        ]

        # Execute show configuration in address-family mode
        output = self._execute_show_config_in_mode(
            commands, "router-bgp address-family mode"
        )

        # Verify expected strings in output
        expected = tc.get("expected_in_output", [])
        self._verify_output_contains(output, expected, "28.2")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_28_TC_3"])
    def test_sm_iscli_28_tc3_show_config_neighbor_mode(self) -> None:
        """TC 28.3 - Verify show configuration from neighbor mode."""
        tc = self._get_testcase("28.3")
        st.banner(f"TC 28.3: {tc.get('title')}")

        bgp_config = tc.get("bgp_config")
        asn = bgp_config.get("asn")
        neighbor_ip = bgp_config.get("neighbor", {}).get("ip")
        remote_as = bgp_config.get("neighbor", {}).get("remote_as")

        # Track ASN for cleanup
        if asn not in self.data.bgp_instances:
            self.data.bgp_instances.append(asn)

        # Build commands - configure neighbor and stay in neighbor mode
        commands = [
            f"router bgp {asn}",
            f"neighbor {neighbor_ip} remote-as {remote_as}",
            "address-family l2vpn evpn",
            "activate",
            "exit",
        ]

        # Execute show configuration in neighbor mode
        output = self._execute_show_config_in_mode(commands, "router-bgp neighbor mode")

        # Verify expected strings in output
        expected = tc.get("expected_in_output", [])
        self._verify_output_contains(output, expected, "28.3")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_28_TC_4"])
    def test_sm_iscli_28_tc4_show_config_neighbor_af_mode(self) -> None:
        """TC 28.4 - Verify show configuration from neighbor address-family mode."""
        tc = self._get_testcase("28.4")
        st.banner(f"TC 28.4: {tc.get('title')}")

        bgp_config = tc.get("bgp_config")
        asn = bgp_config.get("asn")
        neighbor_ip = bgp_config.get("neighbor", {}).get("ip")
        remote_as = bgp_config.get("neighbor", {}).get("remote_as")

        # Track ASN for cleanup
        if asn not in self.data.bgp_instances:
            self.data.bgp_instances.append(asn)

        # Build commands - stay in neighbor address-family mode
        commands = [
            f"router bgp {asn}",
            f"neighbor {neighbor_ip} remote-as {remote_as}",
            "address-family l2vpn evpn",
            "activate",
        ]

        # Execute show configuration in neighbor address-family mode
        output = self._execute_show_config_in_mode(
            commands, "router-bgp neighbor address-family mode"
        )

        # Verify expected strings in output
        expected = tc.get("expected_in_output", [])
        self._verify_output_contains(output, expected, "28.4")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["SM_ISCLI_28_TC_5"])
    def test_sm_iscli_28_tc5_pagination_large_config(self) -> None:
        """TC 28.5 - Verify pagination handling for large BGP configuration."""
        tc = self._get_testcase("28.5")
        st.banner(f"TC 28.5: {tc.get('title')}")

        bgp_config = tc.get("bgp_config")
        asn = bgp_config.get("asn")

        # Track ASN for cleanup
        if asn not in self.data.bgp_instances:
            self.data.bgp_instances.append(asn)

        # Configure full BGP with multiple address families and neighbors
        self._configure_bgp_full(bgp_config)

        # Execute show configuration in router-bgp mode
        commands = [f"router bgp {asn}"]
        output = self._execute_show_config_in_mode(commands, "router-bgp mode (large config)")

        # Verify we got substantial output (not truncated by pagination)
        expected_min_lines = tc.get("expected_min_lines", 10)
        output_lines = output.split('\n')
        actual_lines = len([line for line in output_lines if line.strip()])

        st.log(f"Output has {actual_lines} non-empty lines (expected minimum: {expected_min_lines})")

        if actual_lines < expected_min_lines:
            st.report_fail(
                "msg",
                f"TC 28.5: Output too short ({actual_lines} lines), may be truncated by pagination"
            )

        # Verify it contains key configuration elements
        if tc.get("expected_in_output"):
            self._verify_output_contains(output, tc["expected_in_output"], "28.5")

        st.report_pass("test_case_passed")
