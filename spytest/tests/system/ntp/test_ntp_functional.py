"""
NTP SERVER FUNCTIONAL TESTS
Author: Athira
2025

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/system/ntp/test_ntp_functional.py \
  --logs-path ./logs/test_ntp_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Basic validation of NTP server configuration and synchronization on SONiC devices.
  This test validates NTP server configuration using 'config ntp add server <ip>',
  and verifies synchronization status using 'show ntp', 'show ntp associations', and
  'show clock' commands. Tests verify both configuration application and synchronization
  status using chrony tracking and sources validation.

Pre-requisites:
  - Topology: single-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |        dut1        |
        # |   (Management IF)  |
        # +--------------------+
  - Feature flags / min SONiC version: NTP/Chrony support required
  - Required test variables (YAML): defaults.cli_type, defaults.verify_timeout,
    defaults.sync_timeout, defaults.min_topology, testcases.* definitions
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.system.ntp as ntp_api

VAR_FILE_ENV = "NTP_FUNCTIONAL_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent / "vars_ntp_functional.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"NTP test variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("NTP test YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestNTPFunctional:
    """Testcases covering NTP server configuration and synchronization."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 120))
        cls.data.sync_timeout = int(defaults.get("sync_timeout", 60))
        cls.data.mgmt_vrf = defaults.get("mgmt_vrf", "mgmt")
        cls.data.dut1 = getattr(topology, "D1")

        st.log("NTP Functional Test Suite: Setup completed")
        st.log(f"DUT: {cls.data.dut1}")
        st.log(f"CLI Type: {cls.data.cli_type}")

    def _cleanup_ntp_servers(self) -> None:
        """Clean up all NTP servers using direct CLI commands."""
        st.log("Cleaning up NTP servers")
        try:
            # Get list of configured NTP servers
            ntp_output = ntp_api.show_ntp_server(self.data.dut1, cli_type=self.data.cli_type)
            if ntp_output and isinstance(ntp_output, list):
                for entry in ntp_output:
                    if entry.get("remote"):
                        # Extract server IP/hostname by removing status markers
                        server = entry.get("remote", "").strip("+*#o-x?").strip()
                        if server:
                            st.log(f"Removing NTP server: {server}")
                            commands = [f"no ntp server {server}"]
                            st.config(self.data.dut1, commands, type=self.data.cli_type, skip_error_check=True)
        except Exception as e:
            st.log(f"Warning: Error during NTP cleanup: {e}")

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up NTP configuration after the suite completes."""
        st.log("NTP Functional Test Suite: Teardown starting")
        # Disable NTP admin state
        st.config(cls.data.dut1, ["no ntp enable"], type=cls.data.cli_type, skip_error_check=True)
        st.log("NTP Functional Test Suite: Teardown completed")

    def setup_method(self) -> None:
        """Reset per-test state."""
        st.log("Test setup: Disabling NTP and removing existing NTP servers")
        # Disable NTP admin state first
        st.config(self.data.dut1, ["no ntp enable"], type=self.data.cli_type, skip_error_check=True)
        st.wait(3)
        # Remove existing servers
        self._cleanup_ntp_servers()
        st.wait(5)

    def teardown_method(self) -> None:
        """Clean up after each test."""
        st.log("Test teardown: Removing NTP servers and disabling NTP")
        # Remove NTP servers
        self._cleanup_ntp_servers()
        # Disable NTP admin state
        st.config(self.data.dut1, ["no ntp enable"], type=self.data.cli_type, skip_error_check=True)

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    def _enable_ntp_admin_state(self) -> None:
        """Enable NTP admin state."""
        st.log("Enabling NTP admin state")
        # Use klish CLI to enable NTP
        commands = ["ntp enable"]
        result = st.config(self.data.dut1, commands, type=self.data.cli_type)
        st.wait(5)
        st.log("NTP admin state enabled")

    def _configure_ntp_servers(self, servers: list) -> None:
        """Configure NTP servers on the DUT."""
        st.log(f"Configuring NTP servers: {servers}")

        # First, enable NTP admin state
        self._enable_ntp_admin_state()

        # Configure each NTP server individually using klish CLI
        for server in servers:
            st.log(f"Configuring NTP server: {server}")
            commands = [f"ntp server {server}"]
            st.config(self.data.dut1, commands, type=self.data.cli_type)

        # Wait for configuration to take effect
        st.wait(5)
        st.log(f"Configured {len(servers)} NTP server(s)")

    def _verify_ntp_synchronization(self) -> bool:
        """Verify NTP synchronization status using chrony tracking."""
        st.log("Verifying NTP synchronization status")
        st.log(f"Waiting {self.data.sync_timeout} seconds for NTP synchronization...")

        # Poll for synchronization instead of single wait
        poll_interval = 30  # Check every 30 seconds
        max_polls = self.data.sync_timeout // poll_interval

        for attempt in range(1, max_polls + 1):
            st.wait(poll_interval)
            st.log(f"Checking NTP sync status (attempt {attempt}/{max_polls})...")

            # Check chrony tracking output
            tracking_output = st.show(self.data.dut1, "chronyc tracking", skip_tmpl=True)

            # Check for normal leap status
            if "Leap status" in tracking_output and "Normal" in tracking_output:
                st.log(f"NTP synchronized after {attempt * poll_interval} seconds!")
                st.log(f"Chrony tracking output: {tracking_output}")

                # Verify active source
                sources_output = st.show(self.data.dut1, "chronyc sources", skip_tmpl=True)
                st.log(f"Chrony sources output: {sources_output}")

                if "*" in sources_output or "+" in sources_output:
                    st.log("NTP synchronization: Active source confirmed")
                    return True
                else:
                    st.log("NTP synchronization: Leap status Normal but no active source marker yet")
                    # Continue polling
            else:
                st.log(f"Attempt {attempt}: Not synchronized yet (Leap status not Normal)")

        # Final check after all attempts
        st.error(f"NTP synchronization failed after {self.data.sync_timeout} seconds")
        tracking_output = st.show(self.data.dut1, "chronyc tracking", skip_tmpl=True)
        sources_output = st.show(self.data.dut1, "chronyc sources", skip_tmpl=True)
        st.error(f"Final chrony tracking: {tracking_output}")
        st.error(f"Final chrony sources: {sources_output}")
        return False

    def _verify_ntp_configuration(self) -> bool:
        """Verify NTP configuration using show commands."""
        st.log("Verifying NTP configuration using show commands")

        # Verify show ntp (show ntp associations)
        st.log("Executing: show ntp")
        ntp_output = ntp_api.show_ntp_server(self.data.dut1, cli_type=self.data.cli_type)
        if not ntp_output:
            st.error("show ntp: No NTP servers found in configuration")
            return False

        st.log(f"show ntp output: {ntp_output}")

        # Verify show clock
        st.log("Executing: show clock")
        clock_output = st.show(self.data.dut1, "show clock", skip_tmpl=True)
        st.log(f"show clock output: {clock_output}")

        return True

    @pytest.mark.inventory(feature="Regression", testcases=["NTP-01"])
    def test_ntp_basic_synchronization(self) -> None:
        """TC NTP-01: Verify device synchronizes with a single NTP server."""
        testcase = self._get_testcase("NTP-01")
        st.banner(f"Running {testcase.get('title', 'NTP-01')}")
        st.log(f"Description: {testcase.get('description', '')}")

        servers = testcase.get("servers", [])
        if not servers:
            st.report_fail("msg", "No servers defined in testcase NTP-01")

        # Configure NTP server
        self._configure_ntp_servers(servers)

        # Verify NTP configuration using show commands
        if not self._verify_ntp_configuration():
            st.report_fail("msg", "NTP-01: Failed to verify NTP configuration")

        # Verify synchronization
        if not self._verify_ntp_synchronization():
            st.report_fail("msg", "NTP-01: Failed to synchronize with NTP server")

        st.log("NTP-01: PASSED - Device synchronized with single NTP server")
        st.report_pass("test_case_passed")
