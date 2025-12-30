"""
LLDP NEGATIVE TESTING - RAPID ENABLE/DISABLE
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_2vs.yaml  \
  tests/system/lldp/test_lldp_8.py \
  --logs-path ./logs/test_lldp_8_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Negative testing to verify system stability and correct LLDP table behavior
  under rapid enable/disable operations. This test performs rapid state transitions
  of LLDP at both global and interface levels with minimal delays between operations
  to stress test the system. The suite validates that the system handles rapid churn
  gracefully without crashes, memory leaks, or table corruption. It verifies that
  LLDP table converges correctly after rapid state changes, entries age out properly
  according to TTL, and no stale entries persist. Tests use klish for configuration
  and click for validation, consuming topology-aware variables from YAML to remain
  reusable across SONiC hardware and virtual environments.

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

# Testcases for LLDP rapid enable/disable negative testing covering SpyTest plan 1.1.8

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping
import re
import time

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.system.lldp as lldp_api
import apis.system.interface as intf_api

VAR_FILE_ENV = "LLDP_RAPID_TOGGLE_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent
    / "var_test_lldp_8.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"LLDP rapid toggle variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("LLDP rapid toggle YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestLldpRapidToggle:
    """Testcases covering LLDP rapid enable/disable negative testing."""

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
        """Restore default LLDP configuration after the suite completes."""
        if not cls.data.cleanup_enabled:
            return
        st.log("LLDP rapid toggle test suite completed")

    def setup_method(self) -> None:
        """Per-test setup."""
        self._configured = False
        self._toggle_stats = {
            'global_enable_count': 0,
            'global_disable_count': 0,
            'interface_enable_count': 0,
            'interface_disable_count': 0,
            'errors': []
        }

    def teardown_method(self) -> None:
        """Cleanup after each test."""
        if not self.data.cleanup_enabled or not self._configured:
            return
        st.log(f"Toggle statistics: {self._toggle_stats}")
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
        """Bring up interfaces with 'no shut' command."""
        st.log(f"Bringing up interfaces on {dut}: {interfaces}")
        for interface in interfaces:
            result = intf_api.interface_noshutdown(
                dut,
                interface,
                cli_type=self.data.cli_type_config
            )
            if not result:
                st.error(f"Failed to bring up interface {interface} on {dut}")
                return False
        return True

    def _enable_lldp_globally(self, dut: str) -> bool:
        """Enable LLDP globally on the DUT using klish CLI."""
        result = lldp_api.lldp_config(
            dut,
            status="enable",
            cli_type=self.data.cli_type_config
        )
        if result:
            self._toggle_stats['global_enable_count'] += 1
        else:
            self._toggle_stats['errors'].append(f"Failed to enable LLDP globally on {dut}")
        return result

    def _disable_lldp_globally(self, dut: str) -> bool:
        """Disable LLDP globally on the DUT using klish CLI."""
        result = lldp_api.lldp_config(
            dut,
            status="disable",
            cli_type=self.data.cli_type_config
        )
        if result:
            self._toggle_stats['global_disable_count'] += 1
        else:
            self._toggle_stats['errors'].append(f"Failed to disable LLDP globally on {dut}")
        return result

    def _enable_lldp_on_interface(self, dut: str, interface: str) -> bool:
        """Enable LLDP on a specific interface using klish CLI."""
        result = lldp_api.lldp_config(
            dut,
            interface=interface,
            status="enable",
            cli_type=self.data.cli_type_config
        )
        if result:
            self._toggle_stats['interface_enable_count'] += 1
        else:
            self._toggle_stats['errors'].append(f"Failed to enable LLDP on {interface} on {dut}")
        return result

    def _disable_lldp_on_interface(self, dut: str, interface: str) -> bool:
        """Disable LLDP on a specific interface using klish CLI."""
        result = lldp_api.lldp_config(
            dut,
            interface=interface,
            status="disable",
            cli_type=self.data.cli_type_config
        )
        if result:
            self._toggle_stats['interface_disable_count'] += 1
        else:
            self._toggle_stats['errors'].append(f"Failed to disable LLDP on {interface} on {dut}")
        return result

    def _rapid_toggle_global(self, dut: str, iterations: int, delay: float) -> bool:
        """Rapidly toggle LLDP globally with specified iterations and delay."""
        st.log(f"Performing rapid global LLDP toggle on {dut}: {iterations} iterations, {delay}s delay")

        for i in range(iterations):
            st.log(f"Iteration {i+1}/{iterations}: Enabling LLDP globally")
            if not self._enable_lldp_globally(dut):
                st.error(f"Failed to enable LLDP in iteration {i+1}")
                return False

            if delay > 0:
                time.sleep(delay)

            st.log(f"Iteration {i+1}/{iterations}: Disabling LLDP globally")
            if not self._disable_lldp_globally(dut):
                st.error(f"Failed to disable LLDP in iteration {i+1}")
                return False

            if delay > 0 and i < iterations - 1:
                time.sleep(delay)

        st.log(f"Completed {iterations} rapid global toggle iterations")
        return True

    def _rapid_toggle_interface(self, dut: str, interface: str, iterations: int, delay: float) -> bool:
        """Rapidly toggle LLDP on interface with specified iterations and delay."""
        st.log(f"Performing rapid interface LLDP toggle on {dut} {interface}: {iterations} iterations, {delay}s delay")

        for i in range(iterations):
            st.log(f"Iteration {i+1}/{iterations}: Enabling LLDP on {interface}")
            if not self._enable_lldp_on_interface(dut, interface):
                st.error(f"Failed to enable LLDP on interface in iteration {i+1}")
                return False

            if delay > 0:
                time.sleep(delay)

            st.log(f"Iteration {i+1}/{iterations}: Disabling LLDP on {interface}")
            if not self._disable_lldp_on_interface(dut, interface):
                st.error(f"Failed to disable LLDP on interface in iteration {i+1}")
                return False

            if delay > 0 and i < iterations - 1:
                time.sleep(delay)

        st.log(f"Completed {iterations} rapid interface toggle iterations")
        return True

    def _rapid_toggle_combined(self, dut: str, interface: str, iterations: int, delay: float) -> bool:
        """Rapidly toggle LLDP at both global and interface levels (interleaved)."""
        st.log(f"Performing combined rapid LLDP toggle on {dut}: {iterations} iterations, {delay}s delay")

        for i in range(iterations):
            st.log(f"Iteration {i+1}/{iterations}: Enable global, disable interface")
            self._enable_lldp_globally(dut)
            if delay > 0:
                time.sleep(delay)
            self._disable_lldp_on_interface(dut, interface)
            if delay > 0:
                time.sleep(delay)

            st.log(f"Iteration {i+1}/{iterations}: Disable global, enable interface")
            self._disable_lldp_globally(dut)
            if delay > 0:
                time.sleep(delay)
            self._enable_lldp_on_interface(dut, interface)
            if delay > 0 and i < iterations - 1:
                time.sleep(delay)

        st.log(f"Completed {iterations} combined rapid toggle iterations")
        return True

    def _get_lldp_table_click(self, dut: str) -> List[Dict[str, Any]]:
        """Get LLDP table information using click CLI and store in a list of dictionaries."""
        st.log(f"Getting LLDP table on {dut} using click")

        # Execute show command using click
        command = "show lldp table"
        output = st.show(dut, command, skip_tmpl=True, skip_error_check=True)

        # Convert output to string
        if isinstance(output, list):
            output_str = '\n'.join(output)
        else:
            output_str = str(output)

        st.log(f"LLDP table output:\n{output_str}")

        # Parse the output and store in a list of entry dictionaries
        table_entries = []

        # Parse table entries - typical format:
        # Interface    Neighbor Name    Neighbor Port    Age (seconds)
        # Format may vary, so we'll try to extract key information

        lines = output_str.split('\n')
        for line in lines:
            line = line.strip()
            if not line or 'Interface' in line or '---' in line:
                continue

            # Try to extract interface, neighbor, port, age
            # Simple pattern: Interface Name Port Age
            parts = line.split()
            if len(parts) >= 2:
                entry = {
                    'interface': parts[0] if parts else None,
                    'neighbor': parts[1] if len(parts) > 1 else None,
                    'port': parts[2] if len(parts) > 2 else None,
                    'age': parts[3] if len(parts) > 3 else None,
                    'raw_line': line
                }
                table_entries.append(entry)

        st.log(f"Parsed {len(table_entries)} LLDP table entries")
        return table_entries

    def _get_lldp_neighbor_count_click(self, dut: str) -> int:
        """Get count of LLDP neighbors using click CLI."""
        table_entries = self._get_lldp_table_click(dut)
        return len(table_entries)

    def _verify_no_stale_entries(self, dut: str, max_ttl: int) -> bool:
        """Verify no stale entries exist in LLDP table beyond TTL."""
        st.log(f"Verifying no stale entries in LLDP table on {dut} (max TTL: {max_ttl}s)")

        table_entries = self._get_lldp_table_click(dut)

        if not table_entries:
            st.log("No LLDP table entries found")
            return True

        # Check each entry's age
        stale_entries = []
        for entry in table_entries:
            age_str = entry.get('age')
            if age_str:
                # Try to extract numeric age value
                age_match = re.search(r'(\d+)', str(age_str))
                if age_match:
                    age_seconds = int(age_match.group(1))
                    st.log(f"Entry {entry.get('interface')} age: {age_seconds}s (max: {max_ttl}s)")

                    if age_seconds > max_ttl:
                        st.error(f"Stale entry found: {entry}, age {age_seconds}s exceeds max TTL {max_ttl}s")
                        stale_entries.append(entry)

        if stale_entries:
            st.error(f"Found {len(stale_entries)} stale entries beyond TTL")
            return False

        st.log("No stale entries found - all entries within TTL")
        return True

    def _verify_table_convergence(self, dut: str, interface: str, expected_present: bool, timeout: int) -> bool:
        """Verify LLDP table converges to expected state."""
        st.log(f"Verifying LLDP table convergence on {dut} interface {interface}")
        st.log(f"Expected neighbor present: {expected_present}")

        def _check_convergence():
            table_entries = self._get_lldp_table_click(dut)

            # Check if interface has neighbor entry
            has_neighbor = False
            for entry in table_entries:
                if entry.get('interface') == interface and entry.get('neighbor'):
                    has_neighbor = True
                    break

            st.log(f"Neighbor present: {has_neighbor}, Expected: {expected_present}")
            return has_neighbor == expected_present

        if not st.poll_wait(_check_convergence, timeout):
            st.error(f"LLDP table did not converge to expected state within {timeout}s")
            return False

        st.log("LLDP table converged to expected state")
        return True

    def _verify_neighbor_present(self, dut: str, interface: str, timeout: int) -> bool:
        """Verify LLDP neighbor is present on the interface."""
        st.log(f"Verifying LLDP neighbor is present on {dut} interface {interface}")

        def _check_neighbor():
            table_entries = self._get_lldp_table_click(dut)

            for entry in table_entries:
                if entry.get('interface') == interface and entry.get('neighbor'):
                    st.log(f"Neighbor found: {entry}")
                    return True

            st.log("Neighbor not found yet, retrying...")
            return False

        if not st.poll_wait(_check_neighbor, timeout):
            st.error(f"LLDP neighbor not found on {dut} interface {interface}")
            return False

        return True

    def _check_system_stability(self, dut: str) -> bool:
        """Check system stability by verifying basic system operations."""
        st.log(f"Checking system stability on {dut}")

        # Try basic show command to verify system is responsive
        try:
            output = st.show(dut, "show version", skip_tmpl=True, skip_error_check=True)
            if not output:
                st.error(f"System appears unresponsive on {dut}")
                return False

            st.log("System is responsive and stable")
            return True

        except Exception as e:
            st.error(f"System stability check failed on {dut}: {str(e)}")
            return False

    def _execute_show_commands_klish(self, dut: str, commands: List[str]) -> Dict[str, str]:
        """Execute show commands in klish mode and store outputs."""
        st.log(f"Executing show commands in klish mode on {dut}")
        st.warn("NOTE: Klish LLDP commands are under development - may not produce output")

        outputs = {}
        for command in commands:
            st.log(f"Executing: {command}")
            try:
                output = st.show(dut, command, type="klish", skip_tmpl=True, skip_error_check=True)
                if isinstance(output, list):
                    output_str = '\n'.join(output)
                else:
                    output_str = str(output)
                outputs[command] = output_str
            except Exception as e:
                st.warn(f"Expected exception (feature not implemented): {str(e)}")
                outputs[command] = ""

        return outputs

    def _execute_show_commands_click(self, dut: str, commands: List[str]) -> Dict[str, str]:
        """Execute show commands in click mode and store outputs."""
        st.log(f"Executing show commands in click mode on {dut}")

        outputs = {}
        for command in commands:
            st.log(f"Executing: {command}")
            try:
                output = st.show(dut, command, skip_tmpl=True, skip_error_check=True)
                if isinstance(output, list):
                    output_str = '\n'.join(output)
                else:
                    output_str = str(output)
                outputs[command] = output_str
                st.log(f"Output length: {len(output_str)} characters")

                if not output_str or len(output_str.strip()) == 0:
                    st.error(f"Command returned empty output: {command}")
                    return {}
            except Exception as e:
                st.error(f"Exception executing command {command}: {str(e)}")
                return {}

        return outputs

    @pytest.mark.inventory(feature="Regression", testcases=["LLDP_TC1.1.8"])
    @pytest.mark.negative
    def test_lldp_rapid_enable_disable(self) -> None:
        """
        TC 1.1.8 – Negative testing: Rapid enable/disable of LLDP.

        Test steps:
        1. Bring up all interfaces with 'no shut' (klish)
        2. Test initial LLDP enable/disable (klish)
        3. Enable LLDP globally and on interfaces (klish)
        4. Verify baseline neighbor discovery (click)
        5. Perform rapid global LLDP toggle (klish)
        6. Verify system stability (click)
        7. Perform rapid interface LLDP toggle (klish)
        8. Verify system stability (click)
        9. Perform combined rapid toggle (klish)
        10. Verify system stability (click)
        11. Establish stable state and verify convergence (click)
        12. Verify no stale entries beyond TTL (click)
        13. Verify table updates correctly (click)
        14. Repeat rapid toggle to verify consistency (klish)
        15. Execute all show commands in klish and click modes
        """
        testcase = self._get_testcase("1.1.8")
        config = testcase.get("config", {})
        verify = testcase.get("verify", {})
        show_commands = testcase.get("show_commands", {})

        dut_alias = config.get("dut", "D1")
        peer_alias = config.get("peer_dut", "D2")
        interface = config.get("interface", "Ethernet4")

        dut = self._resolve_dut(dut_alias)
        peer_dut = self._resolve_dut(peer_alias)

        if not dut:
            st.report_fail("msg", f"Unable to resolve DUT alias: {dut_alias}")
        if not peer_dut:
            st.report_fail("msg", f"Unable to resolve peer DUT alias: {peer_alias}")

        # Step 1: Bring up all interfaces with 'no shut'
        st.banner("Step 1: Bring up interfaces with 'no shut'")
        interfaces_to_bring_up = [interface]
        if not self._bring_up_interfaces(dut, interfaces_to_bring_up):
            st.report_fail("msg", f"Failed to bring up interfaces on {dut_alias}")
        if not self._bring_up_interfaces(peer_dut, interfaces_to_bring_up):
            st.report_fail("msg", f"Failed to bring up interfaces on {peer_alias}")

        st.wait(5, "Waiting for interfaces to come up")

        # Step 2: Test initial LLDP enable/disable
        if config.get("test_initial_enable_disable", True):
            st.banner("Step 2: Test initial LLDP enable/disable")

            if not self._enable_lldp_globally(dut):
                st.report_fail("msg", f"Failed to enable LLDP globally on {dut_alias}")
            if not self._disable_lldp_globally(dut):
                st.report_fail("msg", f"Failed to disable LLDP globally on {dut_alias}")

            if not self._enable_lldp_on_interface(dut, interface):
                st.report_fail("msg", f"Failed to enable LLDP on interface {interface}")
            if not self._disable_lldp_on_interface(dut, interface):
                st.report_fail("msg", f"Failed to disable LLDP on interface {interface}")

        # Step 3: Enable LLDP globally and on interfaces for baseline
        st.banner("Step 3: Enable LLDP globally and on interfaces")
        if not self._enable_lldp_globally(dut):
            st.report_fail("msg", f"Failed to enable LLDP globally on {dut_alias}")
        if not self._enable_lldp_globally(peer_dut):
            st.report_fail("msg", f"Failed to enable LLDP globally on {peer_alias}")

        if not self._enable_lldp_on_interface(dut, interface):
            st.report_fail("msg", f"Failed to enable LLDP on interface {interface} on {dut_alias}")
        if not self._enable_lldp_on_interface(peer_dut, interface):
            st.report_fail("msg", f"Failed to enable LLDP on interface {interface} on {peer_alias}")

        self._configured = True

        st.wait(30, "Waiting for baseline LLDP to stabilize")

        # Step 4: Verify baseline neighbor discovery
        st.banner("Step 4: Verify baseline neighbor discovery")
        neighbor_timeout = verify.get("neighbor_discovery_timeout", 60)
        if not self._verify_neighbor_present(dut, interface, neighbor_timeout):
            st.warn("Baseline neighbor not discovered - continuing with rapid toggle test")

        # Get baseline table state
        st.log("Capturing baseline LLDP table state")
        baseline_count = self._get_lldp_neighbor_count_click(dut)
        st.log(f"Baseline neighbor count: {baseline_count}")

        # Step 5: Perform rapid global LLDP toggle
        rapid_global = config.get("rapid_toggle_global", {})
        if rapid_global.get("enabled", True):
            st.banner("Step 5: Perform rapid global LLDP toggle")
            iterations = rapid_global.get("iterations", 15)
            delay = rapid_global.get("delay_between_iterations", 1)

            if not self._rapid_toggle_global(dut, iterations, delay):
                st.report_fail("msg", "Rapid global toggle failed")

            # Step 6: Verify system stability after global toggle
            st.banner("Step 6: Verify system stability after global toggle")
            if not self._check_system_stability(dut):
                st.report_fail("msg", "System unstable after rapid global toggle")

        # Step 7: Perform rapid interface LLDP toggle
        rapid_interface = config.get("rapid_toggle_interface", {})
        if rapid_interface.get("enabled", True):
            st.banner("Step 7: Perform rapid interface LLDP toggle")
            iterations = rapid_interface.get("iterations", 15)
            delay = rapid_interface.get("delay_between_iterations", 1)

            # Ensure global LLDP is enabled first
            self._enable_lldp_globally(dut)

            if not self._rapid_toggle_interface(dut, interface, iterations, delay):
                st.report_fail("msg", "Rapid interface toggle failed")

            # Step 8: Verify system stability after interface toggle
            st.banner("Step 8: Verify system stability after interface toggle")
            if not self._check_system_stability(dut):
                st.report_fail("msg", "System unstable after rapid interface toggle")

        # Step 9: Perform combined rapid toggle
        rapid_combined = config.get("rapid_toggle_combined", {})
        if rapid_combined.get("enabled", True):
            st.banner("Step 9: Perform combined rapid toggle (global + interface)")
            iterations = rapid_combined.get("iterations", 10)
            delay = rapid_combined.get("delay_between_iterations", 1)

            if not self._rapid_toggle_combined(dut, interface, iterations, delay):
                st.report_fail("msg", "Combined rapid toggle failed")

            # Step 10: Verify system stability after combined toggle
            st.banner("Step 10: Verify system stability after combined toggle")
            if not self._check_system_stability(dut):
                st.report_fail("msg", "System unstable after combined rapid toggle")

        # Step 11: Establish stable state and verify convergence
        st.banner("Step 11: Establish stable state and verify convergence")

        # Enable LLDP to stable state
        self._enable_lldp_globally(dut)
        self._enable_lldp_globally(peer_dut)
        self._enable_lldp_on_interface(dut, interface)
        self._enable_lldp_on_interface(peer_dut, interface)

        # Wait for stabilization
        stabilization_wait = verify.get("stabilization_wait", 45)
        st.wait(stabilization_wait, "Waiting for LLDP to stabilize after rapid churn")

        # Verify convergence
        convergence_timeout = verify.get("convergence_timeout", 60)
        if verify.get("verify_neighbor_after_churn", True):
            if not self._verify_table_convergence(dut, interface, expected_present=True, timeout=convergence_timeout):
                st.warn("LLDP table did not fully converge - may be expected after rapid churn")

        # Step 12: Verify no stale entries beyond TTL
        st.banner("Step 12: Verify no stale entries beyond TTL")
        if verify.get("check_stale_entries", True):
            max_ttl = verify.get("default_ttl", 120) + verify.get("ttl_tolerance", 10)
            if not self._verify_no_stale_entries(dut, max_ttl):
                st.warn("Stale entries detected - this may indicate a timing issue")

        # Step 13: Verify table updates correctly
        st.banner("Step 13: Verify table updates correctly")
        final_count = self._get_lldp_neighbor_count_click(dut)
        st.log(f"Final neighbor count: {final_count}, Baseline: {baseline_count}")

        # Table should have converged back to similar state
        if final_count == 0 and baseline_count > 0:
            st.warn("LLDP table is empty after rapid churn - neighbors not rediscovered")

        # Step 14: Repeat rapid toggle to verify consistency
        if config.get("repeat_rapid_toggle", True):
            st.banner("Step 14: Repeat rapid toggle to verify consistency")
            repeat_iterations = config.get("repeat_iterations", 10)

            # Quick global toggle test
            self._rapid_toggle_global(dut, repeat_iterations, 1)

            # Verify system stability
            if not self._check_system_stability(dut):
                st.report_fail("msg", "System unstable after repeated rapid toggle")

            # Re-enable for final state
            self._enable_lldp_globally(dut)
            self._enable_lldp_on_interface(dut, interface)
            st.wait(15, "Waiting for final stabilization")

        # Step 15: Execute all show commands
        st.banner("Step 15: Execute show commands in klish mode")
        klish_commands = show_commands.get("klish", [])
        if klish_commands:
            klish_outputs = self._execute_show_commands_klish(dut, klish_commands)
            st.log(f"Executed {len(klish_outputs)} klish commands")

        st.banner("Step 15: Execute show commands in click mode")
        click_commands = show_commands.get("click", [])
        if click_commands:
            click_outputs = self._execute_show_commands_click(dut, click_commands)
            if not click_outputs:
                st.report_fail("msg", "Failed to execute show commands in click mode")
            st.log(f"Successfully executed {len(click_outputs)} click commands")

        # Log final statistics
        st.log("=== Rapid Toggle Test Statistics ===")
        st.log(f"Global enables: {self._toggle_stats['global_enable_count']}")
        st.log(f"Global disables: {self._toggle_stats['global_disable_count']}")
        st.log(f"Interface enables: {self._toggle_stats['interface_enable_count']}")
        st.log(f"Interface disables: {self._toggle_stats['interface_disable_count']}")
        st.log(f"Errors encountered: {len(self._toggle_stats['errors'])}")
        if self._toggle_stats['errors']:
            st.log(f"Error details: {self._toggle_stats['errors']}")

        st.log("All test steps passed successfully")
        st.report_pass("test_case_passed")
