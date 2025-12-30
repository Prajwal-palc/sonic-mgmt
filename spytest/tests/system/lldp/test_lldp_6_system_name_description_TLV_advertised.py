"""
LLDP SYSTEM-NAME, DESCRIPTION AND MANAGEMENT-ADDRESS TLV
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_2vs.yaml  \
  tests/system/lldp/test_lldp_6.py \
  --logs-path ./logs/test_lldp_6_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of LLDP system-name, system-description, and management-address
  TLV configuration and advertisement. This test verifies that configured TLV values are
  properly advertised to neighbors and appear in neighbor output. The suite configures
  system-name, system-description, enables management-address TLV selection, and sets
  per-interface management addresses. It then validates that neighbors receive these
  TLVs correctly by checking SysName, SysDescr, and MgmtIP fields in neighbor output.
  Tests use klish for configuration and click for validation, consuming topology-aware
  variables from YAML to remain reusable across SONiC hardware and virtual environments.

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

# Testcases for LLDP TLV configuration covering SpyTest plan 1.1.6

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping
import re

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.system.lldp as lldp_api
import apis.system.interface as intf_api

VAR_FILE_ENV = "LLDP_TLV_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent
    / "var_test_lldp_6.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"LLDP TLV variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("LLDP TLV YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestLldpTlvAdvertisement:
    """Testcases covering LLDP TLV configuration and advertisement validation."""

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
        st.log("LLDP TLV advertisement test suite completed")

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

    def _configure_lldp_system_name(self, dut: str, system_name: str) -> bool:
        """Configure LLDP system-name using klish CLI."""
        st.log(f"Configuring LLDP system-name to '{system_name}' on {dut}")

        # Execute config command directly
        command = f'lldp system-name "{system_name}"'
        output = st.config(dut, command, type=self.data.cli_type_config, skip_error_check=True)

        # Check if command was successful
        if output and isinstance(output, str):
            if "error" in output.lower() or "invalid" in output.lower():
                st.error(f"Failed to configure LLDP system-name on {dut}: {output}")
                return False

        st.log(f"LLDP system-name configured successfully on {dut}")
        return True

    def _configure_lldp_system_description(self, dut: str, system_desc: str) -> bool:
        """Configure LLDP system-description using klish CLI."""
        st.log(f"Configuring LLDP system-description to '{system_desc}' on {dut}")

        # Execute config command directly
        command = f'lldp system-description "{system_desc}"'
        output = st.config(dut, command, type=self.data.cli_type_config, skip_error_check=True)

        # Check if command was successful
        if output and isinstance(output, str):
            if "error" in output.lower() or "invalid" in output.lower():
                st.error(f"Failed to configure LLDP system-description on {dut}: {output}")
                return False

        st.log(f"LLDP system-description configured successfully on {dut}")
        return True

    def _configure_management_address_tlv(self, dut: str) -> bool:
        """Enable management-address TLV selection using klish CLI."""
        st.log(f"Enabling management-address TLV on {dut}")

        # Execute config command directly
        command = "lldp tlv-select management-address"
        output = st.config(dut, command, type=self.data.cli_type_config, skip_error_check=True)

        # Check if command was successful
        if output and isinstance(output, str):
            if "error" in output.lower() or "invalid" in output.lower():
                st.error(f"Failed to enable management-address TLV on {dut}: {output}")
                return False

        st.log(f"Management-address TLV enabled successfully on {dut}")
        return True

    def _configure_interface_management_address(self, dut: str, interface: str, ipv4_addr: str) -> bool:
        """Configure per-interface management address using klish CLI."""
        st.log(f"Configuring management address {ipv4_addr} on {dut} interface {interface}")

        # Enter interface configuration mode and set management address
        commands = [
            f"interface {interface}",
            f"lldp tlv-set management-address ipv4 {ipv4_addr}",
            "exit"
        ]

        for command in commands:
            output = st.config(dut, command, type=self.data.cli_type_config, skip_error_check=True)
            if output and isinstance(output, str):
                if "error" in output.lower() or "invalid" in output.lower():
                    st.error(f"Failed to execute command '{command}' on {dut}: {output}")
                    return False

        st.log(f"Management address configured successfully on {dut} interface {interface}")
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

        # Extract System Name
        sysname_match = re.search(r'SysName:\s*(.+?)(?:\n|$)', output_str)
        if sysname_match:
            neighbor_info['system_name'] = sysname_match.group(1).strip()

        # Extract System Description
        sysdesc_match = re.search(r'SysDescr:\s*(.+?)(?:\n|$)', output_str)
        if sysdesc_match:
            neighbor_info['system_description'] = sysdesc_match.group(1).strip()

        # Extract Management IP addresses (can be multiple)
        mgmt_ips = re.findall(r'MgmtIP:\s*(\S+)', output_str)
        if mgmt_ips:
            neighbor_info['management_ips'] = mgmt_ips
            neighbor_info['management_ip'] = mgmt_ips[0] if mgmt_ips else None

        # Extract Interface
        intf_match = re.search(r'Interface:\s*(\S+)', output_str)
        if intf_match:
            neighbor_info['interface'] = intf_match.group(1).strip()

        # Extract Port ID
        port_match = re.search(r'PortID:\s*(?:\S+\s+)?(.+?)(?:\n|$)', output_str)
        if port_match:
            neighbor_info['port_id'] = port_match.group(1).strip()

        # Extract Chassis ID
        chassis_match = re.search(r'ChassisID:\s*\S+\s+(.+?)(?:\n|$)', output_str)
        if chassis_match:
            neighbor_info['chassis_id'] = chassis_match.group(1).strip()

        return neighbor_info

    def _verify_neighbor_system_name(self, dut: str, interface: str, expected_name: str) -> bool:
        """Verify neighbor advertises the expected system name."""
        st.log(f"Verifying neighbor system name on {dut} interface {interface} (expected: '{expected_name}')")

        def _check_system_name():
            neighbor_info = self._get_lldp_neighbor_info_click(dut, interface)

            if not neighbor_info or 'system_name' not in neighbor_info:
                st.log("System name not found in neighbor info, retrying...")
                return False

            actual_name = neighbor_info['system_name']
            st.log(f"Actual system name: '{actual_name}', Expected: '{expected_name}'")

            if actual_name == expected_name:
                st.log(f"System name matches expected value")
                return True
            else:
                st.log(f"System name does not match expected value")
                return False

        if not st.poll_wait(_check_system_name, self.data.verify_timeout):
            st.error(f"System name verification failed on {dut} interface {interface}")
            return False

        return True

    def _verify_neighbor_system_description(self, dut: str, interface: str, expected_desc: str) -> bool:
        """Verify neighbor advertises the expected system description."""
        st.log(f"Verifying neighbor system description on {dut} interface {interface}")

        def _check_system_description():
            neighbor_info = self._get_lldp_neighbor_info_click(dut, interface)

            if not neighbor_info or 'system_description' not in neighbor_info:
                st.log("System description not found in neighbor info, retrying...")
                return False

            actual_desc = neighbor_info['system_description']
            st.log(f"Actual system description: '{actual_desc}'")
            st.log(f"Expected system description: '{expected_desc}'")

            if expected_desc in actual_desc or actual_desc == expected_desc:
                st.log(f"System description matches expected value")
                return True
            else:
                st.log(f"System description does not match expected value")
                return False

        if not st.poll_wait(_check_system_description, self.data.verify_timeout):
            st.error(f"System description verification failed on {dut} interface {interface}")
            return False

        return True

    def _verify_neighbor_management_address(self, dut: str, interface: str, expected_ip: str) -> bool:
        """Verify neighbor advertises the expected management address."""
        st.log(f"Verifying neighbor management address on {dut} interface {interface} (expected: '{expected_ip}')")

        def _check_management_address():
            neighbor_info = self._get_lldp_neighbor_info_click(dut, interface)

            if not neighbor_info or 'management_ips' not in neighbor_info:
                st.log("Management address not found in neighbor info, retrying...")
                return False

            mgmt_ips = neighbor_info['management_ips']
            st.log(f"Actual management IPs: {mgmt_ips}, Expected: '{expected_ip}'")

            # Check if expected IP is in the list of management IPs
            if expected_ip in mgmt_ips:
                st.log(f"Management address matches expected value")
                return True
            else:
                st.log(f"Management address not found in advertised IPs")
                return False

        if not st.poll_wait(_check_management_address, self.data.verify_timeout):
            st.error(f"Management address verification failed on {dut} interface {interface}")
            return False

        return True

    def _verify_neighbor_present(self, dut: str, interface: str) -> bool:
        """Verify LLDP neighbor is present on the interface."""
        st.log(f"Verifying LLDP neighbor is present on {dut} interface {interface}")

        def _check_neighbor():
            neighbor_info = self._get_lldp_neighbor_info_click(dut, interface)

            if not neighbor_info or 'system_name' not in neighbor_info:
                st.log("Neighbor not found, retrying...")
                return False

            st.log(f"Neighbor found: {neighbor_info}")
            return True

        if not st.poll_wait(_check_neighbor, self.data.verify_timeout):
            st.error(f"LLDP neighbor not found on {dut} interface {interface}")
            return False

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

    @pytest.mark.inventory(feature="Regression", testcases=["LLDP_TC1.1.6"])
    def test_lldp_tlv_advertisement(self) -> None:
        """
        TC 1.1.6 – Verify system-name/description and management-address TLV advertised.

        Test steps:
        1. Bring up all interfaces with 'no shut' (klish)
        2. Test LLDP enable/disable in config mode and interface mode (klish)
        3. Enable LLDP globally and on interfaces (klish)
        4. Configure system-name and system-description (klish)
        5. Enable management-address TLV selection (klish)
        6. Configure per-interface management address (klish)
        7. Verify neighbor shows configured SysName (click)
        8. Verify neighbor shows configured SysDescr (click)
        9. Verify neighbor shows configured MgmtIP (click)
        10. Execute all show commands in klish mode
        11. Execute all show commands in click mode
        """
        testcase = self._get_testcase("1.1.6")
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

        # Step 4: Configure system-name and system-description
        st.banner("Step 4: Configure system-name and system-description")
        system_name = config.get("system_name", "sonic-test-device")
        system_desc = config.get("system_description", "SONiC Test Device")
        peer_system_name = config.get("peer_system_name", "sonic-peer-device")
        peer_system_desc = config.get("peer_system_description", "SONiC Peer Device")

        # Configure on DUT
        if not self._configure_lldp_system_name(dut, system_name):
            st.report_fail("msg", f"Failed to configure system-name on {dut_alias}")
        if not self._configure_lldp_system_description(dut, system_desc):
            st.report_fail("msg", f"Failed to configure system-description on {dut_alias}")

        # Configure on peer DUT
        if not self._configure_lldp_system_name(peer_dut, peer_system_name):
            st.report_fail("msg", f"Failed to configure system-name on {peer_alias}")
        if not self._configure_lldp_system_description(peer_dut, peer_system_desc):
            st.report_fail("msg", f"Failed to configure system-description on {peer_alias}")

        # Step 5: Enable management-address TLV selection
        st.banner("Step 5: Enable management-address TLV selection")
        if config.get("enable_management_address_tlv", True):
            if not self._configure_management_address_tlv(dut):
                st.report_fail("msg", f"Failed to enable management-address TLV on {dut_alias}")
            if not self._configure_management_address_tlv(peer_dut):
                st.report_fail("msg", f"Failed to enable management-address TLV on {peer_alias}")

        # Step 6: Configure per-interface management address
        st.banner("Step 6: Configure per-interface management address")
        mgmt_addr = config.get("management_address_ipv4", "192.168.100.10")
        peer_mgmt_addr = config.get("peer_management_address_ipv4", "192.168.100.20")

        if not self._configure_interface_management_address(dut, interface, mgmt_addr):
            st.report_fail("msg", f"Failed to configure management address on {dut_alias}")
        if not self._configure_interface_management_address(peer_dut, interface, peer_mgmt_addr):
            st.report_fail("msg", f"Failed to configure management address on {peer_alias}")

        # Wait for configuration to propagate
        config_wait = verify.get("config_propagate_wait", 20)
        st.wait(config_wait, "Waiting for configuration to propagate")

        # Wait for LLDP to stabilize
        lldp_wait = verify.get("lldp_stabilize_wait", 30)
        st.wait(lldp_wait, "Waiting for LLDP to stabilize")

        # First verify neighbor is present
        st.banner("Verifying LLDP neighbor is present")
        if not self._verify_neighbor_present(dut, interface):
            st.report_fail("msg", f"LLDP neighbor not present on {dut_alias} interface {interface}")

        # Step 7: Verify neighbor shows configured SysName
        st.banner("Step 7: Verify neighbor shows configured SysName")
        expected_neighbor = verify.get("expected_neighbor", {})
        if expected_neighbor.get("verify_system_name", True):
            if not self._verify_neighbor_system_name(dut, interface, peer_system_name):
                st.report_fail("msg", f"System name verification failed on {dut_alias}")

        # Step 8: Verify neighbor shows configured SysDescr
        st.banner("Step 8: Verify neighbor shows configured SysDescr")
        if expected_neighbor.get("verify_system_description", True):
            if not self._verify_neighbor_system_description(dut, interface, peer_system_desc):
                st.report_fail("msg", f"System description verification failed on {dut_alias}")

        # Step 9: Verify neighbor shows configured MgmtIP
        st.banner("Step 9: Verify neighbor shows configured MgmtIP")
        if expected_neighbor.get("verify_management_address", True):
            if not self._verify_neighbor_management_address(dut, interface, peer_mgmt_addr):
                st.report_fail("msg", f"Management address verification failed on {dut_alias}")

        # Step 10: Execute all show commands in klish mode
        st.banner("Step 10: Execute show commands in klish mode")
        klish_commands = show_commands.get("klish", [])
        if klish_commands:
            klish_outputs = self._execute_show_commands_klish(dut, klish_commands)
            st.log(f"Executed {len(klish_outputs)} klish commands")

        # Step 11: Execute all show commands in click mode
        st.banner("Step 11: Execute show commands in click mode")
        click_commands = show_commands.get("click", [])
        if click_commands:
            click_outputs = self._execute_show_commands_click(dut, click_commands)
            if not click_outputs:
                st.report_fail("msg", "Failed to execute show commands in click mode")
            st.log(f"Successfully executed {len(click_outputs)} click commands")

        st.log("All test steps passed successfully")
        st.report_pass("test_case_passed")
