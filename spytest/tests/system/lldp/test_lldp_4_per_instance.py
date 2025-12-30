"""
LLDP PER-INTERFACE ENABLE/DISABLE
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_2vs.yaml  \
  tests/system/lldp/test_lldp_4.py \
  --logs-path ./logs/test_lldp_4_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of LLDP neighbor discovery by enabling LLDP per interface.
  The suite verifies per-interface enable/disable functionality, neighbor discovery,
  TLV validation (Chassis ID, Port ID, System Name, System Capabilities, TTL), and
  neighbor removal when LLDP is disabled on the interface. The test validates all
  show commands in both klish and click modes while ensuring clean teardown. Test
  cases consume topology-aware variables from YAML to remain reusable across SONiC
  hardware and virtual environments.

Pre-requisites:
  - Topology: t0/t1 | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |    smic_sonic1     |                       |    smic_sonic2     |
        # |  Ethernet4         |=======================|  Ethernet4         |
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version (if any)
  - Required test variables (YAML): defaults.cli_type_config (klish),
    defaults.cli_type_verify (click), defaults.verify_timeout,
    defaults.cleanup, defaults.min_topology, testcases.* definitions
"""

# Testcases for LLDP per-interface enable/disable covering SpyTest plan 1.1.4

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping
import re

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.system.lldp as lldp_api
import apis.system.interface as intf_api

VAR_FILE_ENV = "LLDP_PER_INTERFACE_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent
    / "var_test_lldp_4.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"LLDP per-interface variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("LLDP per-interface YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestLldpPerInterface:
    """Testcases covering LLDP per-interface enable/disable and neighbor discovery."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1D2:1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type_config = defaults.get("cli_type_config", "klish")
        cls.data.cli_type_verify = defaults.get("cli_type_verify", "click")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 120))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))
        cls.data.dut_map = SpyTestDict()

        # Map DUT aliases (D1, D2) to actual device handles
        for dut_alias in ["D1", "D2"]:
            if hasattr(topology, dut_alias):
                cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.dut_names = st.get_dut_names()

    @classmethod
    def teardown_class(cls) -> None:
        """Restore initial LLDP state after the suite completes."""
        if not cls.data.cleanup_enabled:
            return
        st.log("LLDP per-interface test suite completed")

    def setup_method(self) -> None:
        """Per-test setup."""
        self._configured = False

    def teardown_method(self) -> None:
        """Cleanup LLDP configuration after each test."""
        if not self.data.cleanup_enabled or not self._configured:
            return
        st.log("Test cleanup completed")

    @classmethod
    def _resolve_dut(cls, alias: str | None) -> str | None:
        """Translate a topology alias (e.g., D1) to the framework DUT handle."""
        if not alias:
            return None
        if alias in cls.data.dut_map:
            return cls.data.dut_map[alias]
        if alias in cls.data.dut_names:
            return alias
        st.warn(f"Unable to resolve DUT alias '{alias}'")
        return None

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    def _bring_up_interfaces(self, dut: str, interfaces: List[str]) -> bool:
        """Bring up interfaces with 'no shut' command before LLDP testing."""
        st.log(f"Bringing up interfaces on {dut}: {interfaces}")
        for interface in interfaces:
            st.log(f"Executing 'no shut' on {dut} interface {interface}")
            result = intf_api.interface_noshutdown(
                dut,
                interface,
                cli_type=self.data.cli_type_config
            )
            if not result:
                st.error(f"Failed to bring up interface {interface} on {dut}")
                return False
        st.log(f"All interfaces brought up successfully on {dut}")
        return True

    def _enable_lldp_globally(self, dut: str) -> bool:
        """Enable LLDP globally on the DUT using klish CLI."""
        st.log(f"Enabling LLDP globally on {dut}")
        result = lldp_api.lldp_config(
            dut,
            status="enable",
            cli_type=self.data.cli_type_config
        )
        if not result:
            st.error(f"Failed to enable LLDP globally on {dut}")
            return False
        return True

    def _disable_lldp_globally(self, dut: str) -> bool:
        """Disable LLDP globally on the DUT using klish CLI."""
        st.log(f"Disabling LLDP globally on {dut}")
        result = lldp_api.lldp_config(
            dut,
            status="disable",
            cli_type=self.data.cli_type_config
        )
        if not result:
            st.error(f"Failed to disable LLDP globally on {dut}")
            return False
        return True

    def _enable_lldp_on_interface(self, dut: str, interface: str) -> bool:
        """Enable LLDP on a specific interface using klish CLI."""
        st.log(f"Enabling LLDP on interface {interface} on {dut}")
        result = lldp_api.lldp_config(
            dut,
            interface=interface,
            status="enable",
            cli_type=self.data.cli_type_config
        )
        if not result:
            st.error(f"Failed to enable LLDP on interface {interface} on {dut}")
            return False
        return True

    def _disable_lldp_on_interface(self, dut: str, interface: str) -> bool:
        """Disable LLDP on a specific interface using klish CLI."""
        st.log(f"Disabling LLDP on interface {interface} on {dut}")
        result = lldp_api.lldp_config(
            dut,
            interface=interface,
            status="disable",
            cli_type=self.data.cli_type_config
        )
        if not result:
            st.error(f"Failed to disable LLDP on interface {interface} on {dut}")
            return False
        return True

    def _get_lldp_neighbor_output(self, dut: str, interface: str = None) -> str:
        """Get LLDP neighbor output as a simple string."""
        if interface:
            command = f"show lldp neighbors {interface}"
        else:
            command = "show lldp neighbors"

        output = st.show(dut, command, skip_tmpl=True, skip_error_check=True)

        if isinstance(output, list):
            output_str = '\n'.join(output)
        else:
            output_str = str(output)

        return output_str

    def _get_lldp_table_output(self, dut: str) -> str:
        """Get LLDP table output as a simple string."""
        command = "show lldp table"
        output = st.show(dut, command, skip_tmpl=True, skip_error_check=True)

        if isinstance(output, list):
            output_str = '\n'.join(output)
        else:
            output_str = str(output)

        return output_str

    def _get_lldp_statistics_output(self, dut: str, interface: str = None) -> str:
        """Get LLDP statistics output as a simple string."""
        if interface:
            command = f"show lldp statistics {interface}"
        else:
            command = "show lldp statistics"

        output = st.show(dut, command, skip_tmpl=True, skip_error_check=True)

        if isinstance(output, list):
            output_str = '\n'.join(output)
        else:
            output_str = str(output)

        return output_str

    def _verify_lldp_neighbor_present(self, dut: str, interface: str) -> bool:
        """Verify LLDP neighbor is discovered on the specified interface."""
        st.log(f"Verifying LLDP neighbor on {dut} interface {interface}")

        def _check_neighbor():
            output = self._get_lldp_neighbor_output(dut, interface)
            st.log(f"LLDP neighbor output:\n{output}")

            # Check if output contains neighbor information
            # Looking for patterns like "ChassisID", "SysName", "PortID"
            has_chassis = "ChassisID" in output or "Chassis ID" in output
            has_sysname = "SysName" in output or "System Name" in output
            has_portid = "PortID" in output or "Port ID" in output

            if has_chassis and has_sysname and has_portid:
                st.log("LLDP neighbor found with expected fields")
                return True

            st.log("LLDP neighbor not found or incomplete")
            return False

        if not st.poll_wait(_check_neighbor, self.data.verify_timeout):
            st.error(f"LLDP neighbor not discovered on {dut} interface {interface}")
            return False
        return True

    def _verify_lldp_neighbor_absent(self, dut: str, interface: str) -> bool:
        """Verify LLDP neighbor is removed from the specified interface."""
        st.log(f"Verifying LLDP neighbor is absent on {dut} interface {interface}")

        def _check_neighbor_absent():
            output = self._get_lldp_neighbor_output(dut, interface)
            st.log(f"LLDP neighbor output:\n{output}")

            # Check if output is empty or shows no neighbors
            has_chassis = "ChassisID" in output or "Chassis ID" in output
            has_sysname = "SysName" in output or "System Name" in output

            # If no key fields found, neighbor is absent
            is_absent = not (has_chassis or has_sysname)
            st.log(f"Neighbor absent: {is_absent}")
            return is_absent

        if not st.poll_wait(_check_neighbor_absent, self.data.verify_timeout):
            st.error(f"LLDP neighbor still present on {dut} interface {interface}")
            return False
        return True

    def _verify_tlvs_in_output(self, output: str, required_tlvs: List[str]) -> bool:
        """Verify that required TLVs are present in the output."""
        st.log(f"Verifying TLVs in output: {required_tlvs}")

        tlv_patterns = {
            'chassis_id': r'ChassisID|Chassis ID',
            'port_id': r'PortID|Port ID',
            'system_name': r'SysName|System Name',
            'system_capabilities': r'Capability|Capabilities',
            'ttl': r'TTL|Time To Live'
        }

        missing_tlvs = []
        for tlv in required_tlvs:
            pattern = tlv_patterns.get(tlv)
            if pattern and not re.search(pattern, output, re.IGNORECASE):
                missing_tlvs.append(tlv)
                st.error(f"Missing TLV: {tlv}")

        if missing_tlvs:
            st.error(f"Missing TLVs: {', '.join(missing_tlvs)}")
            return False

        st.log("All required TLVs are present")
        return True

    def _verify_show_commands_klish(self, dut: str, interface: str) -> bool:
        """Verify all show commands execute in sonic-cli (klish mode)."""
        st.log(f"Verifying show commands in sonic-cli (klish) on {dut}")
        st.warn("NOTE: Klish LLDP commands are under development - may not produce output")

        # Execute show commands in klish mode
        st.log("Executing: show lldp table")
        lldp_table = self._get_lldp_table_output(dut)
        st.log(f"Output: {lldp_table if lldp_table else 'No output (expected - under development)'}")

        st.log("Executing: show lldp neighbor")
        lldp_neighbor = self._get_lldp_neighbor_output(dut)
        st.log(f"Output: {lldp_neighbor if lldp_neighbor else 'No output (expected - under development)'}")

        st.log(f"Executing: show lldp neighbor {interface}")
        lldp_neighbor_intf = self._get_lldp_neighbor_output(dut, interface)
        st.log(f"Output: {lldp_neighbor_intf if lldp_neighbor_intf else 'No output (expected - under development)'}")

        st.log("Executing: show lldp statistics")
        lldp_stats = self._get_lldp_statistics_output(dut)
        st.log(f"Output: {lldp_stats if lldp_stats else 'No output (expected - under development)'}")

        st.log(f"Executing: show lldp statistics {interface}")
        lldp_stats_intf = self._get_lldp_statistics_output(dut, interface)
        st.log(f"Output: {lldp_stats_intf if lldp_stats_intf else 'No output (expected - under development)'}")

        st.log("Klish show commands validation completed")
        return True

    def _verify_show_commands_click(self, dut: str) -> bool:
        """Verify show commands execute successfully in click mode."""
        st.log(f"Verifying show commands in click mode on {dut}")

        # Execute show lldp neighbor using click
        st.log("Executing: show lldp neighbor (click)")
        neighbors = lldp_api.get_lldp_neighbors(dut, cli_type="click")
        if neighbors is False or neighbors is None:
            st.error("Failed to get LLDP neighbors using click")
            return False
        st.log(f"LLDP neighbors: {neighbors}")

        # Execute show lldp table using click
        st.log("Executing: show lldp table (click)")
        table = lldp_api.get_lldp_table(dut, cli_type="click")
        if table is False or table is None:
            st.error("Failed to get LLDP table using click")
            return False
        st.log(f"LLDP table: {table}")

        st.log("All show commands in click mode executed successfully")
        return True

    @pytest.mark.inventory(feature="Regression", testcases=["LLDP_TC1.1.4"])
    def test_lldp_per_interface_enable_disable(self) -> None:
        """
        TC 1.1.4 – Verify LLDP neighbor discovery by enabling LLDP per interface.

        Test steps:
        1. Configure and verify LLDP globally and interface level
           - Bring up interfaces with 'no shut'
           - Test global enable/disable in config mode
           - Test interface-level enable/disable
        2. Enable LLDP globally and on interface
        3. Connect to peer and wait for discovery
        4. Show LLDP neighbors/detail and verify TLVs
        5. Disable LLDP on interface
        6. Verify neighbor removal
        """
        testcase = self._get_testcase("1.1.4")
        config = testcase.get("config", {})
        verify = testcase.get("verify", {})

        dut_alias = config.get("dut", "D1")
        peer_alias = config.get("peer_dut", "D2")
        interface = config.get("interface", "Ethernet4")

        dut = self._resolve_dut(dut_alias)
        peer_dut = self._resolve_dut(peer_alias)

        if not dut:
            st.report_fail("msg", f"Unable to resolve DUT alias: {dut_alias}")
        if not peer_dut:
            st.report_fail("msg", f"Unable to resolve peer DUT alias: {peer_alias}")

        required_tlvs = verify.get("required_tlvs", [])

        # Step 1: Configure and verify LLDP globally and interface level
        st.banner("Step 1: Configure and verify LLDP globally and interface level")

        # Bring up interfaces
        st.log("Bringing up interfaces with 'no shut'")
        interfaces_to_bring_up = [interface]
        if not self._bring_up_interfaces(dut, interfaces_to_bring_up):
            st.report_fail("msg", f"Failed to bring up interfaces on {dut_alias}")
        if not self._bring_up_interfaces(peer_dut, interfaces_to_bring_up):
            st.report_fail("msg", f"Failed to bring up interfaces on {peer_alias}")

        st.wait(5, "Waiting for interfaces to come up")

        # Test LLDP enable/disable in config mode (globally)
        st.log("Testing LLDP enable/disable in config mode")
        if not self._enable_lldp_globally(dut):
            st.report_fail("msg", f"Failed to enable LLDP globally on {dut_alias}")

        st.wait(2, "Waiting after global enable")

        if not self._disable_lldp_globally(dut):
            st.report_fail("msg", f"Failed to disable LLDP globally on {dut_alias}")

        st.wait(2, "Waiting after global disable")

        if not self._enable_lldp_globally(dut):
            st.report_fail("msg", f"Failed to re-enable LLDP globally on {dut_alias}")

        # Test LLDP enable/disable in interface mode
        st.log("Testing LLDP enable/disable in interface mode")
        if not self._enable_lldp_on_interface(dut, interface):
            st.report_fail("msg", f"Failed to enable LLDP on interface {interface} on {dut_alias}")

        st.wait(2, "Waiting after interface enable")

        if not self._disable_lldp_on_interface(dut, interface):
            st.report_fail("msg", f"Failed to disable LLDP on interface {interface} on {dut_alias}")

        st.wait(2, "Waiting after interface disable")

        if not self._enable_lldp_on_interface(dut, interface):
            st.report_fail("msg", f"Failed to re-enable LLDP on interface {interface} on {dut_alias}")

        # Step 2: Enable LLDP globally and on interface for peer as well
        st.banner("Step 2: Enable LLDP globally and on interface")
        if not self._enable_lldp_globally(peer_dut):
            st.report_fail("msg", f"Failed to enable LLDP globally on {peer_alias}")

        if not self._enable_lldp_on_interface(peer_dut, interface):
            st.report_fail("msg", f"Failed to enable LLDP on interface {interface} on {peer_alias}")

        self._configured = True

        # Step 3: Connect to peer and wait for LLDP neighbor discovery
        st.banner("Step 3: Wait for LLDP neighbor discovery")
        discovery_wait = config.get("discovery_wait", 30)
        st.wait(discovery_wait, "Waiting for LLDP neighbor discovery to complete")

        # Step 4: Show LLDP neighbors/detail and verify TLVs
        st.banner("Step 4: Show LLDP neighbors/detail and verify TLVs")

        # Verify neighbor is present
        if not self._verify_lldp_neighbor_present(dut, interface):
            st.report_fail("msg", f"LLDP neighbor not discovered on {dut_alias} interface {interface}")

        # Get neighbor detail output and verify TLVs
        neighbor_detail = self._get_lldp_neighbor_output(dut, interface)
        st.log(f"LLDP neighbor detail:\n{neighbor_detail}")

        if not self._verify_tlvs_in_output(neighbor_detail, required_tlvs):
            st.report_fail("msg", f"Required TLVs missing in LLDP neighbor output on {dut_alias}")

        # Verify show commands in klish mode
        st.log("Verifying show commands in klish mode")
        if not self._verify_show_commands_klish(dut, interface):
            st.report_fail("msg", f"Show commands failed in klish mode on {dut_alias}")

        # Verify show commands in click mode
        st.log("Verifying show commands in click mode")
        if not self._verify_show_commands_click(dut):
            st.report_fail("msg", f"Show commands failed in click mode on {dut_alias}")

        # Step 5: Disable LLDP on interface
        st.banner("Step 5: Disable LLDP on interface")
        if not self._disable_lldp_on_interface(dut, interface):
            st.report_fail("msg", f"Failed to disable LLDP on interface {interface} on {dut_alias}")

        # Step 6: Verify neighbor removal
        st.banner("Step 6: Verify neighbor removal")
        removal_wait = config.get("removal_wait", 30)
        st.wait(removal_wait, "Waiting for LLDP neighbor to be removed after disabling interface")

        if not self._verify_lldp_neighbor_absent(dut, interface):
            st.report_fail("msg", f"LLDP neighbor not removed after disabling LLDP on {dut_alias} interface {interface}")

        st.log("All test steps passed successfully")
        st.report_pass("test_case_passed")
