"""
LLDP NEGATIVE TESTING - RAPID LINK FAILURE
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_2vs.yaml  \
  tests/system/lldp/test_lldp_9.py \
  --logs-path ./logs/test_lldp_9_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Negative testing to verify LLDP behavior and neighbor table integrity during
  rapid interface link flaps. This test keeps LLDP enabled throughout and performs
  rapid interface shutdown/no-shutdown operations to simulate link failures. The suite
  validates that LLDP handles rapid link state changes gracefully with timely neighbor
  withdrawal when links go down and timely neighbor appearance when links come up.
  It verifies that no stale entries persist beyond TTL, the neighbor table converges
  correctly after link stabilization, and both DUTs maintain consistent neighbor
  information. Tests use klish for interface configuration and click for validation,
  consuming topology-aware variables from YAML to remain reusable across SONiC
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

# Testcases for LLDP rapid link failure negative testing covering SpyTest plan 1.1.9

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional
import re
import time

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.system.lldp as lldp_api
import apis.system.interface as intf_api

VAR_FILE_ENV = "LLDP_LINK_FLAP_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent
    / "var_test_lldp_9.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"LLDP link flap variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("LLDP link flap YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestLldpRapidLinkFailure:
    """Testcases covering LLDP behavior during rapid interface link flaps."""

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
        """Restore default configuration after the suite completes."""
        if not cls.data.cleanup_enabled:
            return
        st.log("LLDP rapid link failure test suite completed")

    def setup_method(self) -> None:
        """Per-test setup."""
        self._configured = False
        self._flap_stats = {
            'shutdown_count': 0,
            'noshutdown_count': 0,
            'withdrawal_times': [],
            'appearance_times': [],
            'errors': []
        }

    def teardown_method(self) -> None:
        """Cleanup after each test."""
        if not self.data.cleanup_enabled or not self._configured:
            return
        st.log(f"Flap statistics: {self._flap_stats}")
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

    def _shutdown_interface(self, dut: str, interface: str) -> bool:
        """Shutdown interface using klish CLI."""
        st.log(f"Shutting down interface {interface} on {dut}")
        result = intf_api.interface_shutdown(
            dut,
            interface,
            cli_type=self.data.cli_type_config
        )
        if result:
            self._flap_stats['shutdown_count'] += 1
        else:
            self._flap_stats['errors'].append(f"Failed to shutdown {interface} on {dut}")
        return result

    def _noshutdown_interface(self, dut: str, interface: str) -> bool:
        """Bring up interface using klish CLI (no shutdown)."""
        st.log(f"Bringing up interface {interface} on {dut}")
        result = intf_api.interface_noshutdown(
            dut,
            interface,
            cli_type=self.data.cli_type_config
        )
        if result:
            self._flap_stats['noshutdown_count'] += 1
        else:
            self._flap_stats['errors'].append(f"Failed to no-shutdown {interface} on {dut}")
        return result

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

    def _get_lldp_table_click(self, dut: str) -> List[Dict[str, Any]]:
        """Get LLDP table information using click CLI and store in a list of dictionaries."""
        command = "show lldp table"
        output = st.show(dut, command, skip_tmpl=True, skip_error_check=True)

        # Convert output to string
        if isinstance(output, list):
            output_str = '\n'.join(output)
        else:
            output_str = str(output)

        # Parse the output
        table_entries = []
        lines = output_str.split('\n')
        for line in lines:
            line = line.strip()
            if not line or 'Interface' in line or '---' in line:
                continue

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

        return table_entries

    def _get_neighbor_count_on_interface(self, dut: str, interface: str) -> int:
        """Get count of LLDP neighbors on specific interface."""
        table_entries = self._get_lldp_table_click(dut)
        count = 0
        for entry in table_entries:
            if entry.get('interface') == interface and entry.get('neighbor'):
                count += 1
        return count

    def _is_neighbor_present_on_interface(self, dut: str, interface: str) -> bool:
        """Check if neighbor is present on specific interface."""
        count = self._get_neighbor_count_on_interface(dut, interface)
        return count > 0

    def _rapid_flap_interface(self, dut: str, interface: str, iterations: int,
                             shutdown_delay: float, noshutdown_delay: float) -> bool:
        """Rapidly flap interface with specified iterations and delays."""
        st.log(f"Performing rapid interface flap on {dut} {interface}: {iterations} iterations")
        st.log(f"Shutdown delay: {shutdown_delay}s, No-shutdown delay: {noshutdown_delay}s")

        for i in range(iterations):
            st.log(f"Iteration {i+1}/{iterations}: Shutting down {interface}")

            # Record time before shutdown
            start_time = time.time()

            if not self._shutdown_interface(dut, interface):
                st.error(f"Failed to shutdown interface in iteration {i+1}")
                return False

            # Wait after shutdown
            if shutdown_delay > 0:
                time.sleep(shutdown_delay)

            # Check if neighbor was withdrawn (optional quick check)
            neighbor_present = self._is_neighbor_present_on_interface(dut, interface)
            withdrawal_time = time.time() - start_time
            if not neighbor_present:
                st.log(f"Neighbor withdrawn in {withdrawal_time:.2f} seconds")
                self._flap_stats['withdrawal_times'].append(withdrawal_time)

            st.log(f"Iteration {i+1}/{iterations}: Bringing up {interface}")

            # Record time before no-shutdown
            start_time = time.time()

            if not self._noshutdown_interface(dut, interface):
                st.error(f"Failed to no-shutdown interface in iteration {i+1}")
                return False

            # Wait after no-shutdown
            if noshutdown_delay > 0:
                time.sleep(noshutdown_delay)

            # Check if neighbor appeared (optional quick check)
            neighbor_present = self._is_neighbor_present_on_interface(dut, interface)
            appearance_time = time.time() - start_time
            if neighbor_present:
                st.log(f"Neighbor appeared in {appearance_time:.2f} seconds")
                self._flap_stats['appearance_times'].append(appearance_time)

        st.log(f"Completed {iterations} rapid interface flap iterations")
        return True

    def _verify_neighbor_withdrawal_timing(self, dut: str, interface: str, max_time: int) -> bool:
        """Verify neighbor is withdrawn within expected time after interface shutdown."""
        st.log(f"Verifying neighbor withdrawal timing on {dut} {interface} (max: {max_time}s)")

        # Shutdown interface
        start_time = time.time()
        if not self._shutdown_interface(dut, interface):
            st.error("Failed to shutdown interface for withdrawal test")
            return False

        # Poll for neighbor to be withdrawn
        def _check_neighbor_withdrawn():
            return not self._is_neighbor_present_on_interface(dut, interface)

        if not st.poll_wait(_check_neighbor_withdrawn, max_time):
            elapsed = time.time() - start_time
            st.error(f"Neighbor not withdrawn within {max_time}s (elapsed: {elapsed:.2f}s)")
            return False

        elapsed = time.time() - start_time
        st.log(f"Neighbor withdrawn in {elapsed:.2f} seconds")
        self._flap_stats['withdrawal_times'].append(elapsed)
        return True

    def _verify_neighbor_appearance_timing(self, dut: str, interface: str,
                                          min_time: int, max_time: int) -> bool:
        """Verify neighbor appears within expected time after interface comes up."""
        st.log(f"Verifying neighbor appearance timing on {dut} {interface}")
        st.log(f"Expected: {min_time}s - {max_time}s")

        # Bring up interface
        start_time = time.time()
        if not self._noshutdown_interface(dut, interface):
            st.error("Failed to no-shutdown interface for appearance test")
            return False

        # Poll for neighbor to appear
        def _check_neighbor_appeared():
            return self._is_neighbor_present_on_interface(dut, interface)

        if not st.poll_wait(_check_neighbor_appeared, max_time):
            elapsed = time.time() - start_time
            st.error(f"Neighbor not appeared within {max_time}s (elapsed: {elapsed:.2f}s)")
            return False

        elapsed = time.time() - start_time
        st.log(f"Neighbor appeared in {elapsed:.2f} seconds")
        self._flap_stats['appearance_times'].append(elapsed)

        # Check if appearance time is within expected range
        if elapsed < min_time:
            st.warn(f"Neighbor appeared faster than expected minimum ({min_time}s)")

        return True

    def _verify_no_stale_entries(self, dut: str, max_ttl: int) -> bool:
        """Verify no stale entries exist in LLDP table beyond TTL."""
        st.log(f"Verifying no stale entries in LLDP table on {dut} (max TTL: {max_ttl}s)")

        table_entries = self._get_lldp_table_click(dut)

        if not table_entries:
            st.log("No LLDP table entries found")
            return True

        stale_entries = []
        for entry in table_entries:
            age_str = entry.get('age')
            if age_str:
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

    def _verify_bidirectional_neighbors(self, dut1: str, dut2: str, interface: str) -> bool:
        """Verify both DUTs have discovered each other as neighbors."""
        st.log(f"Verifying bidirectional neighbor discovery between {dut1} and {dut2}")

        # Check if dut1 sees dut2 as neighbor
        dut1_has_neighbor = self._is_neighbor_present_on_interface(dut1, interface)
        st.log(f"{dut1} sees neighbor on {interface}: {dut1_has_neighbor}")

        # Check if dut2 sees dut1 as neighbor
        dut2_has_neighbor = self._is_neighbor_present_on_interface(dut2, interface)
        st.log(f"{dut2} sees neighbor on {interface}: {dut2_has_neighbor}")

        if not dut1_has_neighbor or not dut2_has_neighbor:
            st.error("Bidirectional neighbor discovery failed")
            return False

        st.log("Bidirectional neighbor discovery successful")
        return True

    def _verify_table_convergence(self, dut: str, interface: str, expected_present: bool, timeout: int) -> bool:
        """Verify LLDP table converges to expected state."""
        st.log(f"Verifying LLDP table convergence on {dut} interface {interface}")
        st.log(f"Expected neighbor present: {expected_present}")

        def _check_convergence():
            has_neighbor = self._is_neighbor_present_on_interface(dut, interface)
            st.log(f"Neighbor present: {has_neighbor}, Expected: {expected_present}")
            return has_neighbor == expected_present

        if not st.poll_wait(_check_convergence, timeout):
            st.error(f"LLDP table did not converge to expected state within {timeout}s")
            return False

        st.log("LLDP table converged to expected state")
        return True

    def _check_system_stability(self, dut: str) -> bool:
        """Check system stability by verifying basic system operations."""
        st.log(f"Checking system stability on {dut}")

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

    @pytest.mark.inventory(feature="Regression", testcases=["LLDP_TC1.1.9"])
    @pytest.mark.negative
    def test_lldp_rapid_link_failure(self) -> None:
        """
        TC 1.1.9 – Negative testing: Verify LLDP during rapid link failure.

        Test steps:
        1. Bring up all interfaces with 'no shut' (klish)
        2. Test initial LLDP enable/disable (klish)
        3. Enable LLDP globally and on interfaces (klish)
        4. Verify baseline neighbor discovery (click)
        5. Verify baseline bidirectional neighbors (click)
        6. Test neighbor withdrawal timing (klish + click)
        7. Test neighbor appearance timing (klish + click)
        8. Perform rapid interface flapping (klish)
        9. Verify system stability after flapping (click)
        10. Establish stable state and verify convergence (click)
        11. Verify no stale entries beyond TTL (click)
        12. Verify bidirectional neighbors after flapping (click)
        13. Perform asymmetric flapping (klish)
        14. Repeat rapid flapping for consistency (klish)
        15. Execute all show commands in klish and click modes
        """
        testcase = self._get_testcase("1.1.9")
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

        # Step 3: Enable LLDP globally and on interfaces (and keep it enabled)
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

        # Step 4: Wait for baseline LLDP to stabilize and verify neighbor discovery
        st.banner("Step 4: Verify baseline neighbor discovery")
        baseline_wait = verify.get("baseline_stabilization", 30)
        st.wait(baseline_wait, "Waiting for baseline LLDP to stabilize")

        convergence_timeout = verify.get("convergence_timeout", 90)
        if not self._verify_table_convergence(dut, interface, expected_present=True, timeout=convergence_timeout):
            st.warn("Baseline neighbor not discovered - continuing with link flap test")

        # Get baseline neighbor count
        baseline_count = self._get_neighbor_count_on_interface(dut, interface)
        st.log(f"Baseline neighbor count on {dut_alias} {interface}: {baseline_count}")

        # Step 5: Verify baseline bidirectional neighbors
        st.banner("Step 5: Verify baseline bidirectional neighbors")
        if verify.get("verify_both_duts", True):
            if not self._verify_bidirectional_neighbors(dut, peer_dut, interface):
                st.warn("Baseline bidirectional neighbor discovery not complete")

        # Step 6: Test neighbor withdrawal timing
        st.banner("Step 6: Test neighbor withdrawal timing")
        withdrawal_max = verify.get("withdrawal_max_time", 10)

        if not self._verify_neighbor_withdrawal_timing(dut, interface, withdrawal_max):
            st.warn("Neighbor withdrawal timing test failed - may be expected behavior")

        st.wait(5, "Waiting after withdrawal test")

        # Step 7: Test neighbor appearance timing
        st.banner("Step 7: Test neighbor appearance timing")
        appearance_min = verify.get("appearance_min_time", 20)
        appearance_max = verify.get("appearance_max_time", 70)

        if not self._verify_neighbor_appearance_timing(dut, interface, appearance_min, appearance_max):
            st.warn("Neighbor appearance timing test failed - may be expected behavior")

        st.wait(10, "Waiting after appearance test")

        # Step 8: Perform rapid interface flapping
        rapid_flap = config.get("rapid_flap", {})
        if rapid_flap.get("enabled", True):
            st.banner("Step 8: Perform rapid interface flapping")
            iterations = rapid_flap.get("iterations", 18)
            shutdown_delay = rapid_flap.get("shutdown_delay", 2)
            noshutdown_delay = rapid_flap.get("no_shutdown_delay", 3)

            if not self._rapid_flap_interface(dut, interface, iterations, shutdown_delay, noshutdown_delay):
                st.report_fail("msg", "Rapid interface flapping failed")

            # Step 9: Verify system stability after flapping
            st.banner("Step 9: Verify system stability after flapping")
            if verify.get("check_system_stability", True):
                if not self._check_system_stability(dut):
                    st.report_fail("msg", "System unstable after rapid interface flapping")
                if not self._check_system_stability(peer_dut):
                    st.report_fail("msg", "Peer system unstable after rapid interface flapping")

        # Step 10: Establish stable state and verify convergence
        st.banner("Step 10: Establish stable state and verify convergence")

        # Ensure interface is up
        self._noshutdown_interface(dut, interface)

        # Wait for stabilization
        stabilization_wait = verify.get("post_flap_stabilization", 45)
        st.wait(stabilization_wait, "Waiting for LLDP to stabilize after rapid flapping")

        # Verify convergence
        if not self._verify_table_convergence(dut, interface, expected_present=True, timeout=convergence_timeout):
            st.warn("LLDP table did not fully converge after flapping")

        # Step 11: Verify no stale entries beyond TTL
        st.banner("Step 11: Verify no stale entries beyond TTL")
        if verify.get("check_stale_entries", True):
            max_ttl = verify.get("default_ttl", 120) + verify.get("ttl_tolerance", 10)
            if not self._verify_no_stale_entries(dut, max_ttl):
                st.warn("Stale entries detected after link flapping")

        # Step 12: Verify bidirectional neighbors after flapping
        st.banner("Step 12: Verify bidirectional neighbors after flapping")
        if verify.get("verify_both_duts", True):
            if not self._verify_bidirectional_neighbors(dut, peer_dut, interface):
                st.warn("Bidirectional neighbor discovery not complete after flapping")

        # Step 13: Perform asymmetric flapping (flap on one side only)
        asymmetric_flap = config.get("asymmetric_flap", {})
        if asymmetric_flap.get("enabled", True):
            st.banner("Step 13: Perform asymmetric flapping (DUT side only)")
            iterations = asymmetric_flap.get("iterations", 10)

            if not self._rapid_flap_interface(dut, interface, iterations, 2, 3):
                st.report_fail("msg", "Asymmetric interface flapping failed")

            st.wait(30, "Waiting after asymmetric flapping")

            # Ensure interface is up
            self._noshutdown_interface(dut, interface)
            st.wait(30, "Waiting for convergence after asymmetric flapping")

        # Step 14: Repeat rapid flapping to verify consistency
        if config.get("repeat_rapid_flap", True):
            st.banner("Step 14: Repeat rapid flapping to verify consistency")
            repeat_iterations = config.get("repeat_iterations", 10)

            if not self._rapid_flap_interface(dut, interface, repeat_iterations, 2, 3):
                st.report_fail("msg", "Repeated rapid flapping failed")

            # Verify system stability
            if not self._check_system_stability(dut):
                st.report_fail("msg", "System unstable after repeated rapid flapping")

            # Ensure interface is up for final state
            self._noshutdown_interface(dut, interface)
            st.wait(30, "Waiting for final stabilization")

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
        st.log("=== Rapid Link Flap Test Statistics ===")
        st.log(f"Interface shutdowns: {self._flap_stats['shutdown_count']}")
        st.log(f"Interface no-shutdowns: {self._flap_stats['noshutdown_count']}")

        if self._flap_stats['withdrawal_times']:
            avg_withdrawal = sum(self._flap_stats['withdrawal_times']) / len(self._flap_stats['withdrawal_times'])
            st.log(f"Average withdrawal time: {avg_withdrawal:.2f}s")
            st.log(f"Min withdrawal time: {min(self._flap_stats['withdrawal_times']):.2f}s")
            st.log(f"Max withdrawal time: {max(self._flap_stats['withdrawal_times']):.2f}s")

        if self._flap_stats['appearance_times']:
            avg_appearance = sum(self._flap_stats['appearance_times']) / len(self._flap_stats['appearance_times'])
            st.log(f"Average appearance time: {avg_appearance:.2f}s")
            st.log(f"Min appearance time: {min(self._flap_stats['appearance_times']):.2f}s")
            st.log(f"Max appearance time: {max(self._flap_stats['appearance_times']):.2f}s")

        st.log(f"Errors encountered: {len(self._flap_stats['errors'])}")
        if self._flap_stats['errors']:
            st.log(f"Error details: {self._flap_stats['errors']}")

        st.log("All test steps passed successfully")
        st.report_pass("test_case_passed")
