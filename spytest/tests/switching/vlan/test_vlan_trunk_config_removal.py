"""
VLAN TRUNK PORT CONFIGURATION AND REMOVAL TEST
Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/ztp_standalone.yaml \\
  tests/switching/vlan/test_vlan_trunk_config_removal.py \\
  --logs-path ./logs/vlan_trunk_004_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  TC_VLAN_TRUNK_004: Validates trunk port VLAN configuration lifecycle including
  configuration persistence in running-config and proper cleanup.

  Test creates VLAN 10, configures trunk port, verifies show commands and running-config,
  removes trunk configuration, and verifies complete cleanup. Uses single DUT standalone
  topology with interface read from testbed global parameters.

Pre-requisites:
  - Topology: Standalone single DUT | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node (standalone)
        # +--------------------+
        # |    smic_sonic1     |
        # |   Ethernet8        |
        # +--------------------+
  - Feature flags / min SONiC version: VLAN support required
  - Required test variables (YAML): spytest/vars/switching/vlan/vars_vlan_trunk_004.yaml
  - Testbed global param: test_interface (defaults to Ethernet8)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api

# Default YAML variable file location
VAR_FILE_ENV = "VLAN_TRUNK_004_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_trunk_004.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"VLAN trunk 004 variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("VLAN trunk 004 YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("D1:1")
class TestVlanTrunkConfigRemoval:
    """Testcase validating VLAN trunk port configuration lifecycle."""

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

        st.log(f"✓ Test setup complete. CLI type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after test suite completes."""
        st.log("Test suite teardown complete")

    def _get_test_interface(self, dut: str) -> str:
        """Get test interface from testbed global params or default."""
        # Read from testbed global params (test_interface)
        test_interface = st.get_testbed_vars().get("test_interface")

        if not test_interface:
            # Fallback to default
            test_interface = "Ethernet8"
            st.log(f"No test_interface in testbed global params, using default: {test_interface}")

        st.log(f"Test interface: {test_interface}")
        return test_interface

    def _verify_vlan_membership(self, dut: str, vlan_id: int, interface: str,
                                should_exist: bool = True, expected_status: str = "Up") -> bool:
        """Verify VLAN membership and status in show Vlan output.

        Args:
            dut: Device under test
            vlan_id: VLAN ID to check
            interface: Interface name (e.g., Ethernet8)
            should_exist: True if interface should be VLAN member, False otherwise
            expected_status: Expected VLAN status (Up/Down)

        Returns:
            True if verification passes, False otherwise
        """
        st.log(f"Verifying VLAN {vlan_id} membership for {interface}, should_exist={should_exist}, expected_status={expected_status}")

        # Get show Vlan output
        output = vlan_api.show_vlan_config(dut, vlan_id, cli_type=self.data.cli_type)

        if not output:
            st.error(f"Failed to get show Vlan output for VLAN {vlan_id}")
            return False

        # Convert output to string for parsing
        output_str = str(output)
        st.log(f"Show Vlan output:\n{output_str}")

        # Parse show Vlan output (raw format since TextFSM may not work)
        cmd = f"show Vlan {vlan_id}"
        raw_output = st.show(dut, cmd, type=self.data.cli_type, skip_tmpl=True, skip_error_check=True)

        if not raw_output:
            st.error("Failed to get raw show Vlan output")
            return False

        # Check VLAN status
        status_found = False
        interface_found = False

        for line in raw_output.split('\n'):
            st.log(f"Parsing line: {line}")

            # Look for VLAN status line (e.g., "Vlan10    Up          T  Ethernet8        Enable      No")
            if f"Vlan{vlan_id}" in line or f"VLAN{vlan_id}" in line:
                parts = line.split()
                if len(parts) >= 2:
                    status = parts[1]
                    st.log(f"Found VLAN {vlan_id} status: {status}")

                    if status != expected_status:
                        st.error(f"VLAN {vlan_id} status is {status}, expected {expected_status}")
                        return False

                    status_found = True

                    # Check if interface is in the line (tagged member)
                    if interface in line:
                        # Check for Tagged indicator (T)
                        if "T" in parts or "Tagged" in line:
                            interface_found = True
                            st.log(f"✓ Found {interface} as Tagged member of VLAN {vlan_id}")

        if not status_found:
            st.error(f"Could not find VLAN {vlan_id} status in output")
            return False

        # Verify interface membership
        if should_exist and not interface_found:
            st.error(f"{interface} should be member of VLAN {vlan_id} but not found")
            return False

        if not should_exist and interface_found:
            st.error(f"{interface} should NOT be member of VLAN {vlan_id} but was found")
            return False

        st.log(f"✓ VLAN {vlan_id} verification passed: status={expected_status}, interface_member={interface_found}")
        return True

    def _verify_running_config(self, dut: str, interface: str, vlan_id: int,
                               should_exist: bool = True) -> bool:
        """Verify running-configuration contains or does not contain trunk VLAN config.

        Args:
            dut: Device under test
            interface: Interface name
            vlan_id: VLAN ID
            should_exist: True if config should exist, False if it should be removed

        Returns:
            True if verification passes, False otherwise
        """
        st.log(f"Verifying running-config for {interface}, VLAN {vlan_id}, should_exist={should_exist}")

        # Get running-configuration for interface
        match = re.search(r'Ethernet(\d+)', interface)
        if not match:
            st.error(f"Invalid interface name: {interface}")
            return False

        intf_num = match.group(1)
        cmd = f"show running-configuration interface Ethernet {intf_num}"

        output = st.show(dut, cmd, type=self.data.cli_type, skip_tmpl=True, skip_error_check=True)

        if not output:
            st.error("Failed to get running-configuration output")
            return False

        st.log(f"Running-config output:\n{output}")

        # Look for "switchport trunk allowed Vlan <vlan_id>" in output
        config_line = f"switchport trunk allowed Vlan {vlan_id}"
        config_exists = config_line in output

        if should_exist and not config_exists:
            st.error(f"Running-config should contain '{config_line}' but does not")
            return False

        if not should_exist and config_exists:
            st.error(f"Running-config should NOT contain '{config_line}' but does")
            return False

        st.log(f"✓ Running-config verification passed: config_exists={config_exists}")
        return True

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_TRUNK_004"])
    def test_vlan_trunk_004_config_removal(self) -> None:
        """
        TC_VLAN_TRUNK_004: Verify trunk port VLAN configuration, persistence, and removal.

        Test Steps:
        1. Get test interface from testbed global params
        2. Pre-cleanup: Remove VLAN 10 if exists
        3. Create VLAN 10
        4. Configure trunk port: switchport trunk allowed Vlan 10
        5. Verify show Vlan: VLAN 10 status=Up, interface is Tagged member
        6. Verify running-config contains trunk configuration
        7. Remove trunk configuration: no switchport trunk allowed Vlan 10
        8. Verify show Vlan: VLAN 10 status=Down, interface NOT a member
        9. Verify running-config does NOT contain trunk configuration
        10. Cleanup: Delete VLAN 10
        """
        st.banner("TC_VLAN_TRUNK_004: VLAN Trunk Configuration and Removal Test")

        testcase = self.data.testcases.get("TC_VLAN_TRUNK_004")
        if not testcase:
            st.report_fail("msg", "TC_VLAN_TRUNK_004 testcase not found in YAML")

        vlan_config = SpyTestDict(testcase.get("vlan", {}))
        verification = SpyTestDict(testcase.get("verification", {}))

        topology = self.data.topology
        dut = topology.D1

        st.banner("Step 1: Getting test interface from testbed")
        test_interface = self._get_test_interface(dut)

        vlan_id = vlan_config.get("id", 10)

        try:
            st.banner("Step 2: Pre-cleanup - Remove VLAN if exists")
            vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ Pre-cleanup completed")

            st.banner(f"Step 3: Creating VLAN {vlan_id}")
            if not vlan_api.create_vlan(dut, vlan_id, cli_type=self.data.cli_type):
                st.report_fail("msg", f"Failed to create VLAN {vlan_id}")
            st.log(f"✓ VLAN {vlan_id} created")

            st.banner(f"Step 4: Configuring trunk port {test_interface}")

            # Configure trunk using raw CLI (no existing API for trunk config)
            match = re.search(r'Ethernet(\d+)', test_interface)
            intf_num = match.group(1)

            trunk_commands = [
                f"interface Ethernet {intf_num}",
                "no ip address",
                "no switchport access Vlan",
                f"switchport trunk allowed Vlan {vlan_id}",
                "no shutdown",
                "end"
            ]

            st.config(dut, trunk_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ Trunk port configured with VLAN {vlan_id}")

            st.banner("Step 5: Verifying show Vlan output (trunk added)")

            trunk_added_verify = verification.get("trunk_added", {})
            expected_status = trunk_added_verify.get("show_vlan_status", "Up")

            if not self._verify_vlan_membership(dut, vlan_id, test_interface,
                                               should_exist=True, expected_status=expected_status):
                st.report_fail("msg", f"VLAN {vlan_id} membership verification failed after adding trunk")

            st.log(f"✓ Show Vlan verification passed: {test_interface} is Tagged member, status={expected_status}")

            st.banner("Step 6: Verifying running-configuration (trunk added)")

            if not self._verify_running_config(dut, test_interface, vlan_id, should_exist=True):
                st.report_fail("msg", "Running-config verification failed: trunk config not found")

            st.log("✓ Running-config contains trunk configuration")

            st.banner(f"Step 7: Removing trunk configuration from {test_interface}")

            remove_commands = [
                f"interface Ethernet {intf_num}",
                f"no switchport trunk allowed Vlan {vlan_id}",
                "end"
            ]

            st.config(dut, remove_commands, type=self.data.cli_type, skip_error_check=True)
            st.log(f"✓ Trunk configuration removed")

            st.banner("Step 8: Verifying show Vlan output (trunk removed)")

            trunk_removed_verify = verification.get("trunk_removed", {})
            expected_status_removed = trunk_removed_verify.get("show_vlan_status", "Down")

            if not self._verify_vlan_membership(dut, vlan_id, test_interface,
                                               should_exist=False, expected_status=expected_status_removed):
                st.report_fail("msg", f"VLAN {vlan_id} membership verification failed after removing trunk")

            st.log(f"✓ Show Vlan verification passed: {test_interface} NOT a member, status={expected_status_removed}")

            st.banner("Step 9: Verifying running-configuration (trunk removed)")

            if not self._verify_running_config(dut, test_interface, vlan_id, should_exist=False):
                st.report_fail("msg", "Running-config verification failed: trunk config still exists")

            st.log("✓ Running-config does NOT contain trunk configuration")

            st.banner("Step 10: Cleanup")
            vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type, skip_error_check=True)
            st.log("✓ Cleanup completed")

            st.report_pass("test_case_passed")

        except Exception as e:
            st.error(f"Test failed: {e}")

            if self.data.cleanup_enabled:
                st.log("Performing cleanup after failure")

                # Remove trunk config
                if test_interface:
                    match = re.search(r'Ethernet(\d+)', test_interface)
                    if match:
                        intf_num = match.group(1)
                        cleanup_cmds = [
                            f"interface Ethernet {intf_num}",
                            f"no switchport trunk allowed Vlan {vlan_id}",
                            "no switchport access Vlan",
                            "exit"
                        ]
                        st.config(dut, cleanup_cmds, type=self.data.cli_type, skip_error_check=True)

                # Delete VLAN
                vlan_api.delete_vlan(dut, vlan_id, cli_type=self.data.cli_type, skip_error_check=True)

            st.report_fail("msg", f"Test failed: {e}")
