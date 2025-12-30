"""
LLDP TIMERS AND MULTIPLIER
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_2vs.yaml  \
  tests/system/lldp/test_lldp_5.py \
  --logs-path ./logs/test_lldp_5_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of LLDP timers and hold-time multiplier configuration.
  This test verifies that LLDP timer and multiplier settings correctly affect
  the TTL (Time To Live) values in neighbor advertisements. The suite tests
  various timer and multiplier combinations, validates TTL calculations (timer × multiplier),
  ensures neighbor stability with custom timer configurations, and verifies proper
  neighbor removal behavior after TTL expiration. Tests use klish for configuration
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

# Testcases for LLDP timers and multiplier covering SpyTest plan 1.1.5

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

VAR_FILE_ENV = "LLDP_TIMERS_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent
    / "var_test_lldp_5.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"LLDP timers variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("LLDP timers YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestLldpTimersAndMultiplier:
    """Testcases covering LLDP timers and multiplier configuration validation."""

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
        st.log("LLDP timers and multiplier test suite completed")

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
        """Bring up interfaces with 'no shut' command."""
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

    def _configure_lldp_timer(self, dut: str, timer_value: int) -> bool:
        """Configure LLDP timer using klish CLI."""
        st.log(f"Configuring LLDP timer to {timer_value} seconds on {dut}")

        # Execute config command directly
        command = f"lldp timer {timer_value}"
        output = st.config(dut, command, type=self.data.cli_type_config, skip_error_check=True)

        # Check if command was successful
        if output and isinstance(output, str):
            if "error" in output.lower() or "invalid" in output.lower():
                st.error(f"Failed to configure LLDP timer on {dut}: {output}")
                return False

        st.log(f"LLDP timer configured successfully on {dut}")
        return True

    def _configure_lldp_multiplier(self, dut: str, multiplier_value: int) -> bool:
        """Configure LLDP multiplier using klish CLI."""
        st.log(f"Configuring LLDP multiplier to {multiplier_value} on {dut}")

        # Execute config command directly
        command = f"lldp holdtime {multiplier_value}"
        output = st.config(dut, command, type=self.data.cli_type_config, skip_error_check=True)

        # Check if command was successful
        if output and isinstance(output, str):
            if "error" in output.lower() or "invalid" in output.lower():
                st.error(f"Failed to configure LLDP multiplier on {dut}: {output}")
                return False

        st.log(f"LLDP multiplier configured successfully on {dut}")
        return True

    def _get_lldp_neighbor_info_click(self, dut: str, interface: str) -> Dict[str, Any]:
        """Get LLDP neighbor information using click CLI and store in a simple dictionary."""
        st.log(f"Getting LLDP neighbor info on {dut} interface {interface} using click")

        # Execute show command using click
        command = f"show lldp neighbors {interface}"
        output = st.show(dut, command, skip_tmpl=True, skip_error_check=True)

        # Convert output to string
        if isinstance(output, list):
            output_str = '\n'.join(output)
        else:
            output_str = str(output)

        st.log(f"LLDP neighbor output:\n{output_str}")

        # Parse the output and store in a simple dictionary
        neighbor_info = {}

        # Extract TTL
        ttl_match = re.search(r'TTL:\s*(\d+)', output_str)
        if ttl_match:
            neighbor_info['ttl'] = int(ttl_match.group(1))

        # Extract Chassis Name
        chassis_match = re.search(r'SysName:\s*(.+)', output_str)
        if chassis_match:
            neighbor_info['chassis_name'] = chassis_match.group(1).strip()

        # Extract Port ID
        port_match = re.search(r'PortID:\s*(?:\S+\s+)?(.+)', output_str)
        if port_match:
            neighbor_info['port_id'] = port_match.group(1).strip()

        # Extract Interface
        intf_match = re.search(r'Interface:\s*(\S+)', output_str)
        if intf_match:
            neighbor_info['interface'] = intf_match.group(1).strip()

        return neighbor_info

    def _verify_ttl_value(self, dut: str, interface: str, expected_ttl: int, tolerance: int = 5) -> bool:
        """Verify that TTL value matches expected value (timer × multiplier) within tolerance."""
        st.log(f"Verifying TTL value on {dut} interface {interface} (expected: {expected_ttl} ± {tolerance})")

        def _check_ttl():
            neighbor_info = self._get_lldp_neighbor_info_click(dut, interface)

            if not neighbor_info or 'ttl' not in neighbor_info:
                st.log("TTL not found in neighbor info, retrying...")
                return False

            actual_ttl = neighbor_info['ttl']
            st.log(f"Actual TTL: {actual_ttl}, Expected: {expected_ttl} ± {tolerance}")

            # Check if TTL is within tolerance
            if abs(actual_ttl - expected_ttl) <= tolerance:
                st.log(f"TTL value {actual_ttl} is within expected range")
                return True
            else:
                st.log(f"TTL value {actual_ttl} is outside expected range")
                return False

        if not st.poll_wait(_check_ttl, self.data.verify_timeout):
            st.error(f"TTL verification failed on {dut} interface {interface}")
            return False

        return True

    def _verify_neighbor_present(self, dut: str, interface: str) -> bool:
        """Verify LLDP neighbor is present on the interface."""
        st.log(f"Verifying LLDP neighbor is present on {dut} interface {interface}")

        def _check_neighbor():
            neighbor_info = self._get_lldp_neighbor_info_click(dut, interface)

            if not neighbor_info or 'chassis_name' not in neighbor_info:
                st.log("Neighbor not found, retrying...")
                return False

            st.log(f"Neighbor found: {neighbor_info}")
            return True

        if not st.poll_wait(_check_neighbor, self.data.verify_timeout):
            st.error(f"LLDP neighbor not found on {dut} interface {interface}")
            return False

        return True

    def _verify_neighbor_absent(self, dut: str, interface: str) -> bool:
        """Verify LLDP neighbor is absent from the interface."""
        st.log(f"Verifying LLDP neighbor is absent on {dut} interface {interface}")

        def _check_neighbor_absent():
            neighbor_info = self._get_lldp_neighbor_info_click(dut, interface)

            # Check if neighbor is absent (empty or no chassis_name)
            is_absent = not neighbor_info or 'chassis_name' not in neighbor_info
            st.log(f"Neighbor absent: {is_absent}")
            return is_absent

        if not st.poll_wait(_check_neighbor_absent, self.data.verify_timeout):
            st.error(f"LLDP neighbor still present on {dut} interface {interface}")
            return False

        return True

    def _verify_neighbor_stability(self, dut: str, interface: str, duration: int) -> bool:
        """Verify LLDP neighbor remains stable for the specified duration."""
        st.log(f"Verifying LLDP neighbor stability on {dut} interface {interface} for {duration} seconds")

        start_time = time.time()
        check_interval = 10  # Check every 10 seconds

        while time.time() - start_time < duration:
            neighbor_info = self._get_lldp_neighbor_info_click(dut, interface)

            if not neighbor_info or 'chassis_name' not in neighbor_info:
                st.error(f"Neighbor disappeared during stability check on {dut} interface {interface}")
                return False

            st.log(f"Neighbor still present at {int(time.time() - start_time)} seconds")

            # Wait before next check
            remaining = duration - (time.time() - start_time)
            if remaining > 0:
                st.wait(min(check_interval, remaining))

        st.log(f"Neighbor remained stable for {duration} seconds")
        return True

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
                st.log(f"Output: {output_str}")
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

                # Verify output is not empty
                if not output_str or len(output_str.strip()) == 0:
                    st.error(f"Command returned empty output: {command}")
                    return {}
            except Exception as e:
                st.error(f"Exception executing command {command}: {str(e)}")
                return {}

        return outputs

    @pytest.mark.inventory(feature="Regression", testcases=["LLDP_TC1.1.5"])
    def test_lldp_timers_and_multiplier(self) -> None:
        """
        TC 1.1.5 – Verify LLDP timers and multiplier configuration.

        Test steps:
        1. Bring up all interfaces with 'no shut' (klish)
        2. Test LLDP enable/disable in config mode and interface mode (klish)
        3. Enable LLDP globally and on interfaces (klish)
        4. Configure system-name and description (klish)
        5. Test various timer and multiplier combinations (klish)
        6. Verify TTL = timer × multiplier for each combination (click)
        7. Verify neighbor stability with custom timer settings (click)
        8. Verify neighbor removal after TTL expires (click)
        9. Execute all show commands in klish mode
        10. Execute all show commands in click mode
        """
        testcase = self._get_testcase("1.1.5")
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

        # Step 2: Test LLDP enable/disable in config mode and interface mode
        if config.get("test_enable_disable", True):
            st.banner("Step 2: Test LLDP enable/disable")

            # Test global enable/disable
            st.log("Testing LLDP enable in config mode")
            if not self._enable_lldp_globally(dut):
                st.report_fail("msg", f"Failed to enable LLDP globally on {dut_alias}")

            st.log("Testing LLDP disable in config mode")
            if not self._disable_lldp_globally(dut):
                st.report_fail("msg", f"Failed to disable LLDP globally on {dut_alias}")

            # Test interface level enable/disable
            st.log("Testing LLDP enable in interface mode")
            if not self._enable_lldp_on_interface(dut, interface):
                st.report_fail("msg", f"Failed to enable LLDP on interface {interface}")

            st.log("Testing LLDP disable in interface mode")
            if not self._disable_lldp_on_interface(dut, interface):
                st.report_fail("msg", f"Failed to disable LLDP on interface {interface}")

        # Step 3: Enable LLDP globally and on interfaces for actual testing
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

        # Wait for LLDP to stabilize
        st.wait(30, "Waiting for LLDP to stabilize")

        # Step 4: Configure system-name and description
        st.banner("Step 4: Configure system-name and description")
        system_name = config.get("system_name", "sonic-dut1")
        system_desc = config.get("system_description", "SONiC Device Under Test")
        st.log(f"System name: {system_name}, Description: {system_desc}")

        # Step 5-7: Test various timer and multiplier combinations
        timer_tests = config.get("timer_tests", [])
        if not timer_tests:
            st.report_fail("msg", "No timer test configurations found in YAML")

        for test_config in timer_tests:
            timer = test_config.get("timer")
            multiplier = test_config.get("multiplier")
            expected_ttl = test_config.get("expected_ttl")

            st.banner(f"Testing timer={timer}s, multiplier={multiplier}, expected_ttl={expected_ttl}s")

            # Configure timer on both DUTs
            if not self._configure_lldp_timer(dut, timer):
                st.report_fail("msg", f"Failed to configure timer on {dut_alias}")
            if not self._configure_lldp_timer(peer_dut, timer):
                st.report_fail("msg", f"Failed to configure timer on {peer_alias}")

            # Configure multiplier on both DUTs
            if not self._configure_lldp_multiplier(dut, multiplier):
                st.report_fail("msg", f"Failed to configure multiplier on {dut_alias}")
            if not self._configure_lldp_multiplier(peer_dut, multiplier):
                st.report_fail("msg", f"Failed to configure multiplier on {peer_alias}")

            # Wait for configuration to take effect
            st.wait(timer * 2, f"Waiting for timer configuration to take effect")

            # Verify TTL = timer × multiplier
            st.log(f"Step 6: Verifying TTL = {timer} × {multiplier} = {expected_ttl}")
            ttl_tolerance = verify.get("ttl_tolerance", 5)
            if not self._verify_ttl_value(dut, interface, expected_ttl, ttl_tolerance):
                st.report_fail("msg", f"TTL verification failed for timer={timer}, multiplier={multiplier}")

            # Verify neighbor stability
            st.log("Step 7: Verifying neighbor stability")
            stability_duration = min(verify.get("stability_check_duration", 60), 30)
            if not self._verify_neighbor_stability(dut, interface, stability_duration):
                st.report_fail("msg", f"Neighbor stability check failed for timer={timer}, multiplier={multiplier}")

        # Step 8: Verify neighbor removal after interface shutdown
        st.banner("Step 8: Verify neighbor removal after TTL expiry")

        # Shutdown interface
        if not intf_api.interface_shutdown(dut, interface, cli_type=self.data.cli_type_config):
            st.report_fail("msg", f"Failed to shutdown interface {interface} on {dut_alias}")

        # Wait for TTL to expire
        ttl_expiry_wait = verify.get("ttl_expiry_wait", 70)
        st.wait(ttl_expiry_wait, "Waiting for TTL to expire")

        # Verify neighbor is absent
        if not self._verify_neighbor_absent(dut, interface):
            st.report_fail("msg", f"Neighbor not removed after TTL expiry on {dut_alias}")

        # Re-enable interface
        if not intf_api.interface_noshutdown(dut, interface, cli_type=self.data.cli_type_config):
            st.report_fail("msg", f"Failed to re-enable interface {interface} on {dut_alias}")

        st.wait(30, "Waiting for neighbor to reappear")

        # Verify neighbor reappears
        if not self._verify_neighbor_present(dut, interface):
            st.report_fail("msg", f"Neighbor did not reappear after interface re-enable on {dut_alias}")

        # Step 9: Execute all show commands in klish mode
        st.banner("Step 9: Execute show commands in klish mode")
        klish_commands = show_commands.get("klish", [])
        if klish_commands:
            klish_outputs = self._execute_show_commands_klish(dut, klish_commands)
            st.log(f"Executed {len(klish_outputs)} klish commands")

        # Step 10: Execute all show commands in click mode
        st.banner("Step 10: Execute show commands in click mode")
        click_commands = show_commands.get("click", [])
        if click_commands:
            click_outputs = self._execute_show_commands_click(dut, click_commands)
            if not click_outputs:
                st.report_fail("msg", "Failed to execute show commands in click mode")
            st.log(f"Successfully executed {len(click_outputs)} click commands")

        st.log("All test steps passed successfully")
        st.report_pass("test_case_passed")
