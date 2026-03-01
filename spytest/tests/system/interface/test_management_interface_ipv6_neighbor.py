"""
MANAGEMENT INTERFACE IPv6 AND NEIGHBOR VALIDATION
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \\
  --testbed ./testbeds/ztp_standalone.yaml  \\
  tests/system/interface/test_management_interface_ipv6_neighbor.py \\
  --logs-path ./logs/mgmt_ipv6_neighbor_$(date +%F_%H%M%S) \\
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of Management interface IPv6 autoconfig persistence
  in running configuration and neighbor table visibility (ARP/NDP). This suite
  validates that IPv6 address autoconfig on the Management interface is correctly
  stored in running configuration, and ensures that the Management interface
  correctly populates and displays entries in both ARP and IPv6 neighbor tables.

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |        dut1        |
        # |   Management0      |
        # |   (eth0 in click)  |
        # +--------------------+

  - Feature flags / min SONiC version: Management interface access required
  - Required test variables (YAML): vars/system/interface/vars_management_ipv6_neighbor.yaml
  - Network connectivity for neighbor table population (optional)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
from apis.system import management_interface_api

VAR_FILE_ENV = "MGMT_IPV6_NEIGHBOR_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "interface"
    / "vars_management_ipv6_neighbor.yaml"
)

# Test case IDs
TC_IDS = SpyTestDict({
    "mgmt_autoconfig": "TC-SONIC-MGMT-AUTOCONFIG-03",
    "neighbor_visibility": "TC-SONIC-NEIGHBOR-VISIBILITY-04",
    "mgmt_autoconfig_removal": "TC-SONIC-MGMT-AUTOCONFIG-REMOVAL-04",
})


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"Management interface variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("Management interface YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestManagementInterfaceIpv6Neighbor:
    """Testcases for Management interface IPv6 autoconfig and neighbor visibility."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("MODULE PROLOGUE: Management Interface IPv6 and Neighbor Validation")

        # Load YAML configuration
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Get topology
        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Get DUT
        cls.data.dut = topology.D1
        cls.data.dut_name = st.get_dut_names()[0] if st.get_dut_names() else topology.D1

        # Get Management interface name based on CLI type
        cls.data.mgmt_interface = management_interface_api.get_management_interface_name(cls.data.cli_type)
        cls.data.mgmt_interface_show = management_interface_api.get_management_interface_show_name(cls.data.cli_type)

        st.banner(f"Test Configuration Loaded: DUT={cls.data.dut_name}, Management Interface={cls.data.mgmt_interface}")

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure Management interface is restored to default state after suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        st.banner("MODULE EPILOGUE: Cleanup")

        try:
            # Remove IPv6 autoconfig if configured
            st.log(f"Removing IPv6 autoconfig from {cls.data.mgmt_interface}")
            management_interface_api.config_ipv6_autoconfig(
                cls.data.dut,
                config="remove",
                cli_type=cls.data.cli_type,
                skip_error_check=True
            )
        except Exception as e:
            st.warn(f"Exception during cleanup: {str(e)}")

    def setup_method(self, method) -> None:
        """Reset per-test bookkeeping."""
        st.banner(f"TEST SETUP: {method.__name__}")

    def teardown_method(self, method) -> None:
        """Cleanup after each test."""
        st.banner(f"TEST TEARDOWN: {method.__name__}")

        if not self.data.cleanup_enabled:
            return

        # Remove IPv6 autoconfig after each test
        try:
            management_interface_api.config_ipv6_autoconfig(
                self.data.dut,
                config="remove",
                cli_type=self.data.cli_type,
                skip_error_check=True
            )
        except Exception as e:
            st.warn(f"Exception during test cleanup: {str(e)}")

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    @pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.mgmt_autoconfig])
    def test_management_ipv6_autoconfig_persistence(self) -> None:
        """
        TC-SONIC-MGMT-AUTOCONFIG-03: Management Interface IPv6 Autoconfig Persistence.

        Verify that IPv6 address autoconfig on the Management interface is correctly
        stored in the running configuration.
        """
        st.banner(f"TEST: {TC_IDS.mgmt_autoconfig} - Management IPv6 Autoconfig Persistence")

        testcase = self._get_testcase(TC_IDS.mgmt_autoconfig)
        dut = self.data.dut
        cli_type = self.data.cli_type
        mgmt_interface = self.data.mgmt_interface

        st.log(f"Testing Management interface: {mgmt_interface}")

        # Step 1: Configure IPv6 autoconfig on Management interface
        st.log("Step 1: Configuring IPv6 address autoconfig on Management interface")
        result = management_interface_api.config_ipv6_autoconfig(
            dut, config="add", cli_type=cli_type
        )

        if not result:
            st.report_fail("msg", f"Failed to configure IPv6 autoconfig on {mgmt_interface}")

        st.wait(2)  # Allow time for config to propagate

        # Step 2: Verify IPv6 autoconfig appears in running configuration
        st.log("Step 2: Verifying IPv6 autoconfig in running configuration")

        if not management_interface_api.verify_ipv6_autoconfig_in_running_config(
            dut, should_exist=True, cli_type=cli_type
        ):
            st.report_fail(
                "msg",
                f"IPv6 address autoconfig not found in running configuration for {mgmt_interface}"
            )

        st.log(f"Test {TC_IDS.mgmt_autoconfig} completed successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.neighbor_visibility])
    def test_management_interface_neighbor_visibility(self) -> None:
        """
        TC-SONIC-NEIGHBOR-VISIBILITY-04: Neighbor Table Visibility.

        Ensure that the Management interface correctly populates and displays entries
        in the ARP and IPv6 neighbor tables.
        """
        st.banner(f"TEST: {TC_IDS.neighbor_visibility} - Management Interface Neighbor Visibility")

        testcase = self._get_testcase(TC_IDS.neighbor_visibility)
        dut = self.data.dut
        cli_type = self.data.cli_type
        mgmt_interface_show = self.data.mgmt_interface_show

        st.log(f"Testing Management interface visibility: {mgmt_interface_show}")

        # Step 1: Verify Management interface in ARP table
        st.log("Step 1: Verifying Management interface appears in ARP table")

        if not management_interface_api.verify_management_interface_in_arp(
            dut, cli_type=cli_type
        ):
            st.report_fail(
                "msg",
                f"Management interface {mgmt_interface_show} not found in ARP table"
            )

        # Get ARP entry count for logging
        arp_count = management_interface_api.get_arp_count_for_management_interface(
            dut, cli_type=cli_type
        )
        st.log(f"ARP table contains {arp_count} entries for {mgmt_interface_show}")

        # Step 2: Verify Management interface in IPv6 neighbor table
        st.log("Step 2: Verifying Management interface appears in IPv6 neighbor table")

        if not management_interface_api.verify_management_interface_in_ndp(
            dut, cli_type=cli_type
        ):
            st.report_fail(
                "msg",
                f"Management interface {mgmt_interface_show} not found in IPv6 neighbor table"
            )

        # Get NDP entry count for logging
        ndp_count = management_interface_api.get_ndp_count_for_management_interface(
            dut, cli_type=cli_type
        )
        st.log(f"IPv6 neighbor table contains {ndp_count} entries for {mgmt_interface_show}")

        # Step 3: Summary
        st.log(f"Summary: Management interface {mgmt_interface_show} found in both tables")
        st.log(f"  - ARP entries: {arp_count}")
        st.log(f"  - IPv6 neighbor entries: {ndp_count}")

        st.log(f"Test {TC_IDS.neighbor_visibility} completed successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.mgmt_autoconfig_removal])
    @pytest.mark.negative
    def test_management_ipv6_autoconfig_removal(self) -> None:
        """
        TC-SONIC-MGMT-AUTOCONFIG-REMOVAL-04: IPv6 Autoconfig Removal Validation.

        Verify that after executing 'no ipv6 address autoconfig', the configuration
        is properly removed from running configuration. If still present, test fails.
        """
        st.banner(f"TEST: {TC_IDS.mgmt_autoconfig_removal} - Management IPv6 Autoconfig Removal")

        testcase = self._get_testcase(TC_IDS.mgmt_autoconfig_removal)
        dut = self.data.dut
        cli_type = self.data.cli_type
        mgmt_interface = self.data.mgmt_interface

        st.log(f"Testing Management interface: {mgmt_interface}")

        # Step 1: Configure IPv6 autoconfig on Management interface
        st.log("Step 1: Configuring IPv6 address autoconfig on Management interface")
        result = management_interface_api.config_ipv6_autoconfig(
            dut, config="add", cli_type=cli_type
        )

        if not result:
            st.report_fail("msg", f"Failed to configure IPv6 autoconfig on {mgmt_interface}")

        st.wait(2)  # Allow time for config to propagate

        # Step 2: Verify IPv6 autoconfig appears in running configuration
        st.log("Step 2: Verifying IPv6 autoconfig in running configuration (should be present)")

        if not management_interface_api.verify_ipv6_autoconfig_in_running_config(
            dut, should_exist=True, cli_type=cli_type
        ):
            st.report_fail(
                "msg",
                f"IPv6 address autoconfig not found in running configuration after configuration"
            )

        st.log("IPv6 autoconfig successfully configured and present in running-config")

        # Step 3: Remove IPv6 autoconfig from Management interface
        st.log("Step 3: Removing IPv6 address autoconfig from Management interface")
        result = management_interface_api.config_ipv6_autoconfig(
            dut, config="remove", cli_type=cli_type
        )

        if not result:
            st.report_fail("msg", f"Failed to remove IPv6 autoconfig from {mgmt_interface}")

        st.wait(2)  # Allow time for config to propagate

        # Step 4: Verify IPv6 autoconfig is REMOVED from running configuration
        st.log("Step 4: Verifying IPv6 autoconfig is REMOVED from running configuration")

        if not management_interface_api.verify_ipv6_autoconfig_in_running_config(
            dut, should_exist=False, cli_type=cli_type
        ):
            st.report_fail(
                "msg",
                f"FAIL: IPv6 address autoconfig still present in running configuration after removal. "
                f"Configuration not properly cleaned up for {mgmt_interface}"
            )

        st.log("IPv6 autoconfig successfully removed from running configuration")
        st.log(f"Test {TC_IDS.mgmt_autoconfig_removal} completed successfully")
        st.report_pass("test_case_passed")
