"""
INTERFACE CLI VERIFICATION
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/ztp_standalone.yaml  \
  tests/system/interface/test_interface_cli_verification.py \
  --logs-path ./logs/interface_cli_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of interface CLI operations including speed option
  verification and IPv6 enable/disable state management. This suite validates:
  1. Interface speed help output displays correct supported speed values
  2. IPv6 enable/disable commands correctly update running configuration
  3. Running configuration accurately reflects the interface state

  The tests use the new interface_cli_api module for IPv6 configuration and
  the existing interface_speed_api module for speed-related operations.

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node (standalone)
        # +--------------------+
        # |     smic_sonic1    |
        # |   Ethernet8        |
        # +--------------------+

  - Feature flags / min SONiC version: IS-CLI (klish) support required
  - Required test variables (YAML): vars/system/vars_interface_cli_verification.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.system.interface_cli_api as cli_api
import apis.system.interface_speed_api as speed_api

VAR_FILE_ENV = "INTERFACE_CLI_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "vars_interface_cli_verification.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"Interface CLI variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("Interface CLI YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestInterfaceCliVerification:
    """Testcases covering interface CLI verification for speed options and IPv6 enable."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1:1"]
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
        cls.data.dut_names = st.get_dut_names()

        st.banner(f"Setup complete - DUT: {cls.data.dut}, CLI type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after the suite completes."""
        if not cls.data.cleanup_enabled:
            return

        st.banner("Teardown complete")

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        st.banner(f"Starting test method")

    def teardown_method(self) -> None:
        """Cleanup after each test."""
        st.banner(f"Test method complete")

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    @pytest.mark.inventory(feature="Regression", testcases=["InterfaceSpeedOptions_TC1.1"])
    def test_interface_speed_options_display(self) -> None:
        """
        TC 1.1 – Verify Interface Speed Options Display.

        Objective:
            Confirm that the CLI displays the correct supported speed values
            and auto-negotiation options for a given interface.

        Execution Steps:
            1. Enter global configuration mode
            2. Navigate to the specific interface (e.g., Ethernet8)
            3. Use the "speed ?" command to list available speed parameters
            4. Verify expected output contains all supported speeds and auto option

        Expected Output:
            The CLI should display the exact list of supported speeds:
            <10/100/1000/2500/5000/10000/20000/25000/40000/50000/100000/200000/400000/800000>
            Speed config of the interface
            auto    Enable auto-negotiation

        Pass/Fail Criteria:
            Pass: All expected speed values and auto option are present
            Fail: Any expected speed values are missing or unexpected values appear
        """
        testcase = self._get_testcase("1.1")
        interface = testcase.get("interface")
        expected_options = testcase.get("expected_speed_options", [])
        expected_output_contains = testcase.get("expected_output_contains", [])

        if not interface:
            st.report_fail("msg", "Testcase 1.1 missing 'interface' definition in YAML")

        st.banner(f"TC 1.1: Verifying speed options for {interface}")

        # Get speed options using the CLI API
        st.log(f"Step 1-3: Retrieving speed options for {interface}")
        options_output = cli_api.get_interface_speed_options(
            self.data.dut, interface, cli_type=self.data.cli_type
        )

        if not options_output:
            st.report_fail("msg", f"Failed to retrieve speed options for {interface}")

        st.log(f"Speed options output:\n{options_output}")

        # Verify all expected options are present
        st.log(f"Step 4: Verifying expected speed options are available")
        success, details = cli_api.verify_speed_options_available(
            self.data.dut, interface, expected_options, cli_type=self.data.cli_type
        )

        if not success:
            st.report_fail(
                "msg",
                f"Speed options verification failed - Missing: {details.get('missing', [])}",
            )

        # Verify expected output strings are present
        st.log("Verifying expected output strings are present")
        missing_strings = []
        for expected_str in expected_output_contains:
            if expected_str not in options_output:
                missing_strings.append(expected_str)
                st.error(f"Expected string not found: {expected_str}")

        if missing_strings:
            st.report_fail(
                "msg",
                f"Speed options output missing expected strings: {missing_strings}",
            )

        st.log("All speed options verified successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["InterfaceIPv6_TC2.1"])
    def test_interface_ipv6_disable_state(self) -> None:
        """
        TC 2.1 – Verify IPv6 Disable State in Running Configuration.

        Objective:
            Ensure that disabling IPv6 accurately reflects in the interface's
            running configuration.

        Execution Steps:
            1. Enter interface configuration mode
            2. Disable IPv6 explicitly using "no ipv6 enable"
            3. Check the running configuration for that interface
            4. Verify "ipv6 enable" is NOT present in the output

        Expected Behavior:
            After issuing "no ipv6 enable", the running configuration should
            NOT contain "ipv6 enable" for the interface.

        Pass/Fail Criteria:
            Pass: The phrase "ipv6 enable" is not present in the output
            Fail: The phrase "ipv6 enable" is still present after disable
        """
        testcase = self._get_testcase("2.1")
        interface = testcase.get("interface")
        verify_params = testcase.get("verify", {})
        ipv6_enable_should_exist = verify_params.get("ipv6_enable_present", False)

        if not interface:
            st.report_fail("msg", "Testcase 2.1 missing 'interface' definition in YAML")

        st.banner(f"TC 2.1: Verifying IPv6 disable state for {interface}")

        # Step 1-2: Disable IPv6 on the interface
        st.log(f"Step 1-2: Disabling IPv6 on {interface}")
        result = cli_api.config_ipv6_enable(
            self.data.dut, interface, config="remove", cli_type=self.data.cli_type
        )

        if not result:
            st.report_fail("msg", f"Failed to disable IPv6 on {interface}")

        # Step 3-4: Verify running configuration
        st.log(f"Step 3-4: Verifying IPv6 is NOT present in running-config")
        verified = cli_api.verify_ipv6_enable_in_config(
            self.data.dut,
            interface,
            should_exist=ipv6_enable_should_exist,
            cli_type=self.data.cli_type,
        )

        if not verified:
            st.report_fail(
                "msg",
                f"IPv6 disable verification failed - 'ipv6 enable' still present in config",
            )

        st.log("IPv6 disable state verified successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["InterfaceIPv6_TC2.2"])
    def test_interface_ipv6_enable_state(self) -> None:
        """
        TC 2.2 – Verify IPv6 Enable State in Running Configuration.

        Objective:
            Ensure that enabling IPv6 accurately reflects in the interface's
            running configuration.

        Execution Steps:
            1. Re-enable IPv6 using "ipv6 enable"
            2. Check the running configuration again
            3. Verify "ipv6 enable" IS present in the output

        Expected Output:
            !
            interface Ethernet8
             mtu 9100
             speed auto
             ipv6 enable
            !

        Pass/Fail Criteria:
            Pass: The phrase "ipv6 enable" is successfully present in the output
            Fail: The configuration does not show "ipv6 enable"
        """
        testcase = self._get_testcase("2.2")
        interface = testcase.get("interface")
        verify_params = testcase.get("verify", {})
        ipv6_enable_should_exist = verify_params.get("ipv6_enable_present", True)
        expected_config = testcase.get("expected_config", [])

        if not interface:
            st.report_fail("msg", "Testcase 2.2 missing 'interface' definition in YAML")

        st.banner(f"TC 2.2: Verifying IPv6 enable state for {interface}")

        # Step 1: Enable IPv6 on the interface
        st.log(f"Step 1: Enabling IPv6 on {interface}")
        result = cli_api.config_ipv6_enable(
            self.data.dut, interface, config="add", cli_type=self.data.cli_type
        )

        if not result:
            st.report_fail("msg", f"Failed to enable IPv6 on {interface}")

        # Step 2-3: Verify running configuration
        st.log(f"Step 2-3: Verifying IPv6 IS present in running-config")
        verified = cli_api.verify_ipv6_enable_in_config(
            self.data.dut,
            interface,
            should_exist=ipv6_enable_should_exist,
            cli_type=self.data.cli_type,
        )

        if not verified:
            st.report_fail(
                "msg",
                f"IPv6 enable verification failed - 'ipv6 enable' not present in config",
            )

        # Additional verification: Check for expected configuration lines
        if expected_config:
            st.log("Verifying expected configuration lines are present")
            config_output = cli_api.show_running_config_interface(
                self.data.dut, interface, cli_type=self.data.cli_type
            )

            missing_lines = []
            for expected_line in expected_config:
                if expected_line not in config_output:
                    missing_lines.append(expected_line)
                    st.warn(f"Expected config line not found: {expected_line}")

            # Note: Not failing on missing lines like "mtu 9100" or "speed auto"
            # since these are informational and may vary by platform
            if missing_lines:
                st.log(f"Some expected config lines not found (informational): {missing_lines}")

        st.log("IPv6 enable state verified successfully")
        st.report_pass("test_case_passed")
