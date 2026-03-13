"""
VLAN ACCESS PORT CHANGE - TC_VLAN_ACCESS_004
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \\
  --testbed ./testbeds/testbed_vs_2d.yaml  \\
  tests/switching/vlan/test_vlan_access_port_change.py \\
  --logs-path ./logs/vlan_access_$(date +%F_%H%M%S) \\
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Verify that access port VLAN assignment can be successfully changed and that
  configuration changes are properly reflected in system status and configuration
  files. This test validates VLAN membership changes for access ports, ensuring
  proper cleanup and status transitions.

Pre-requisites:
  - Topology: Single DUT (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Single DUT Topology
        # +--------------------+
        # |      spine02       |
        # |        (D1)        |
        # |  Eth12 (test port) |
        # +--------------------+

  - Feature flags / min SONiC version: VLAN support
  - Required test variables (YAML): spytest/vars/switching/vlan/vars_vlan_access.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api

# Variable file configuration
VAR_FILE_ENV = "VLAN_ACCESS_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "switching"
    / "vlan"
    / "vars_vlan_access.yaml"
)

# Test case IDs
TC_IDS = SpyTestDict({
    "access_change": "TC_VLAN_ACCESS_004",
})


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"VLAN access variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("VLAN access YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("D1")
class TestVlanAccessPortChange:
    """Test cases for VLAN access port membership changes."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("MODULE PROLOGUE: TestVlanAccessPortChange Setup")

        # Load configuration from YAML
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # Ensure minimum topology (single DUT)
        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        # Store configuration data
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # CLI type configuration
        cli_type = defaults.get("cli_type", "klish")
        cls.data.cli_type = cli_type

        # Verification timeout
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))

        # Cleanup configuration
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # DUT and interface mapping
        cls.data.dut = topology.D1
        cls.data.dut_name = st.get_dut_names()[0] if st.get_dut_names() else "D1"

        # Track created VLANs for cleanup
        cls.data.created_vlans = []
        cls.data.configured_interfaces = []

        st.log(f"Test DUT: {cls.data.dut_name}")
        st.log(f"CLI Type: {cls.data.cli_type}")
        st.log(f"Cleanup Enabled: {cls.data.cleanup_enabled}")

        # Get test interface from YAML
        testcase_config = cls.data.testcases.get("TC_VLAN_ACCESS_004", {})
        test_interface = testcase_config.get("test_interface", "Ethernet12")

        # Clean up IP addresses from test interface before execution
        st.banner(f"Cleaning up IP addresses from {test_interface}")
        cls._cleanup_interface_ips(test_interface)

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up all VLANs and interface configurations after the suite."""
        st.banner("MODULE EPILOGUE: TestVlanAccessPortChange Cleanup")

        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        # Clean up configured interfaces
        cls._cleanup_all_interfaces()

        # Clean up created VLANs
        cls._cleanup_all_vlans()

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        st.log("Test setup: Resetting per-test tracking")
        self._test_vlans = []
        self._test_interfaces = []

    def teardown_method(self) -> None:
        """Remove any VLANs that the testcase configured."""
        st.log("Test teardown: Cleaning up test-specific resources")

        if not self.data.cleanup_enabled:
            self._test_vlans = []
            self._test_interfaces = []
            return

        # Clean up test-specific interfaces
        while self._test_interfaces:
            interface = self._test_interfaces.pop()
            self._remove_interface_from_vlan(interface)
            if interface in self.data.configured_interfaces:
                self.data.configured_interfaces.remove(interface)

        # Clean up test-specific VLANs
        while self._test_vlans:
            vlan = self._test_vlans.pop()
            self._delete_vlan(vlan)
            if vlan in self.data.created_vlans:
                self.data.created_vlans.remove(vlan)

    @classmethod
    def _cleanup_all_vlans(cls) -> None:
        """Remove all VLANs tracked across the suite."""
        while cls.data.created_vlans:
            vlan = cls.data.created_vlans.pop()
            st.log(f"Cleaning up VLAN {vlan}")
            vlan_api.delete_vlan(
                cls.data.dut,
                vlan,
                cli_type=cls.data.cli_type,
                remove_vlan_mapping=True
            )

    @classmethod
    def _cleanup_all_interfaces(cls) -> None:
        """Remove all interface configurations tracked across the suite."""
        while cls.data.configured_interfaces:
            interface_info = cls.data.configured_interfaces.pop()
            st.log(f"Cleaning up interface {interface_info}")
            # Interface cleanup happens via VLAN deletion with remove_vlan_mapping=True

    @classmethod
    def _cleanup_interface_ips(cls, interface: str) -> None:
        """Remove IP and IPv6 addresses from an interface before test execution."""
        st.log(f"Removing IP addresses from interface {interface}")

        commands = []
        if cls.data.cli_type == "klish":
            # Klish CLI commands
            commands.append(f"interface {interface}")
            commands.append("no ip address")
            commands.append("no ipv6 address")
            commands.append("exit")
        elif cls.data.cli_type == "click":
            # Click CLI commands - need to get current IPs first and remove them
            # For click, we typically use: config interface ip remove <interface> <ip/mask>
            # However, for pre-cleanup, we can use a simpler approach
            st.log("IP cleanup via click CLI - using config commands")
            # Get interface details to see if IPs are configured
            # For simplicity, attempt removal with skip_error_check
            pass  # Click cleanup can be enhanced if needed

        if commands:
            st.config(cls.data.dut, commands, type=cls.data.cli_type, skip_error_check=True)
            st.log(f"IP cleanup completed for {interface}")

    def _create_vlan(self, vlan_id: int) -> bool:
        """Create a VLAN and track it for cleanup."""
        st.log(f"Creating VLAN {vlan_id}")
        result = vlan_api.create_vlan(
            self.data.dut,
            vlan_id,
            cli_type=self.data.cli_type
        )
        if result:
            if vlan_id not in self._test_vlans:
                self._test_vlans.append(vlan_id)
            if vlan_id not in self.data.created_vlans:
                self.data.created_vlans.append(vlan_id)
        return result

    def _delete_vlan(self, vlan_id: int) -> bool:
        """Delete a VLAN."""
        st.log(f"Deleting VLAN {vlan_id}")
        return vlan_api.delete_vlan(
            self.data.dut,
            vlan_id,
            cli_type=self.data.cli_type,
            remove_vlan_mapping=True
        )

    def _add_interface_to_vlan(
        self, interface: str, vlan_id: int, tagging_mode: bool = False
    ) -> bool:
        """Add an interface to a VLAN and track it for cleanup."""
        st.log(f"Adding interface {interface} to VLAN {vlan_id} (tagging={tagging_mode})")
        result = vlan_api.add_vlan_member(
            self.data.dut,
            vlan_id,
            interface,
            tagging_mode=tagging_mode,
            cli_type=self.data.cli_type
        )
        if result:
            interface_info = {"interface": interface, "vlan": vlan_id, "tagging": tagging_mode}
            if interface_info not in self._test_interfaces:
                self._test_interfaces.append(interface_info)
            if interface_info not in self.data.configured_interfaces:
                self.data.configured_interfaces.append(interface_info)
        return result

    def _remove_interface_from_vlan(self, interface_info: Dict[str, Any]) -> bool:
        """Remove an interface from a VLAN."""
        interface = interface_info.get("interface")
        vlan_id = interface_info.get("vlan")
        tagging_mode = interface_info.get("tagging", False)

        st.log(f"Removing interface {interface} from VLAN {vlan_id}")
        return vlan_api.add_vlan_member(
            self.data.dut,
            vlan_id,
            interface,
            tagging_mode=tagging_mode,
            no_form=True,
            cli_type=self.data.cli_type
        )

    def _verify_vlan_member(
        self, vlan_id: int, interface: str, should_exist: bool = True
    ) -> bool:
        """Verify that an interface is (or is not) a member of a VLAN."""
        st.log(f"Verifying VLAN {vlan_id} membership for {interface} (should_exist={should_exist})")

        # Use verify_vlan_config API for untagged (access) ports
        result = vlan_api.verify_vlan_config(
            self.data.dut,
            vlan_id,
            untagged=interface,
            cli_type=self.data.cli_type
        )

        if should_exist and not result:
            st.error(f"Interface {interface} is not an untagged member of VLAN {vlan_id}")
            return False
        elif not should_exist and result:
            st.error(f"Interface {interface} is still a member of VLAN {vlan_id}")
            return False

        return True

    def _verify_vlan_status(self, vlan_id: int, expected_status: str) -> bool:
        """Verify VLAN operational status."""
        st.log(f"Verifying VLAN {vlan_id} status (expected: {expected_status})")

        # Get VLAN configuration
        vlan_data = vlan_api.show_vlan_config(
            self.data.dut,
            vlan_id=str(vlan_id),
            cli_type=self.data.cli_type
        )

        if not vlan_data:
            st.error(f"VLAN {vlan_id} not found in configuration")
            return False

        # Check status from first entry (all entries for same VLAN have same status)
        actual_status = vlan_data[0].get("status", "").lower()
        expected_status_lower = expected_status.lower()

        # Handle various status representations
        if expected_status_lower in ["up", "active"]:
            if actual_status not in ["up", "active"]:
                st.error(f"VLAN {vlan_id} status is {actual_status}, expected {expected_status}")
                return False
        elif expected_status_lower in ["down", "inactive"]:
            if actual_status not in ["down", "inactive"]:
                st.error(f"VLAN {vlan_id} status is {actual_status}, expected {expected_status}")
                return False

        st.log(f"VLAN {vlan_id} status verified: {actual_status}")
        return True

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    @pytest.mark.inventory(feature="Regression", testcases=["TC_VLAN_ACCESS_004"])
    def test_vlan_access_004_change_membership(self) -> None:
        """
        TC_VLAN_ACCESS_004: Change Access Port VLAN Membership

        Verify that access port VLAN assignment can be successfully changed:
        1. Create VLANs 10 and 20
        2. Configure Ethernet12 as access port in VLAN 10
        3. Verify port is in VLAN 10 (status Up)
        4. Change port to VLAN 20
        5. Verify port moved to VLAN 20 (status Up) and VLAN 10 is Down
        """
        st.banner("TC_VLAN_ACCESS_004: Change Access Port VLAN Membership")

        # Get test case configuration
        testcase = self._get_testcase("TC_VLAN_ACCESS_004")
        test_interface = testcase.get("test_interface", "Ethernet12")
        source_vlan = testcase.get("source_vlan", 10)
        target_vlan = testcase.get("target_vlan", 20)
        initial_state = testcase.get("initial_state", {})
        final_state = testcase.get("final_state", {})

        st.log(f"Test Configuration:")
        st.log(f"  Interface: {test_interface}")
        st.log(f"  Source VLAN: {source_vlan}")
        st.log(f"  Target VLAN: {target_vlan}")

        try:
            # Step 1: Create VLANs 10 and 20
            st.banner("Step 1: Create VLANs 10 and 20")
            if not self._create_vlan(source_vlan):
                st.report_fail(
                    "msg",
                    f"Failed to create VLAN {source_vlan}",
                    tcid=TC_IDS.access_change
                )

            if not self._create_vlan(target_vlan):
                st.report_fail(
                    "msg",
                    f"Failed to create VLAN {target_vlan}",
                    tcid=TC_IDS.access_change
                )

            st.log(f"Successfully created VLANs {source_vlan} and {target_vlan}")

            # Step 2: Configure Ethernet12 as access port in VLAN 10
            st.banner(f"Step 2: Configure {test_interface} as access port in VLAN {source_vlan}")
            if not self._add_interface_to_vlan(test_interface, source_vlan, tagging_mode=False):
                st.report_fail(
                    "msg",
                    f"Failed to add {test_interface} to VLAN {source_vlan}",
                    tcid=TC_IDS.access_change
                )

            st.log(f"{test_interface} added to VLAN {source_vlan} as access port")

            # Step 3: Verify port in VLAN 10
            st.banner(f"Step 3: Verify {test_interface} in VLAN {source_vlan}")
            if not st.poll_wait(
                self._verify_vlan_member,
                self.data.verify_timeout,
                source_vlan,
                test_interface,
                should_exist=True
            ):
                st.report_fail(
                    "msg",
                    f"{test_interface} not found in VLAN {source_vlan}",
                    tcid=TC_IDS.access_change
                )

            # Verify VLAN 10 status is Up
            expected_status = initial_state.get("expected_status", "Up")
            if not st.poll_wait(
                self._verify_vlan_status,
                self.data.verify_timeout,
                source_vlan,
                expected_status
            ):
                st.report_fail(
                    "msg",
                    f"VLAN {source_vlan} status verification failed",
                    tcid=TC_IDS.access_change
                )

            st.log(f"Verified: {test_interface} is in VLAN {source_vlan} (status: {expected_status})")

            # Step 4: Change port to VLAN 20
            st.banner(f"Step 4: Change {test_interface} to VLAN {target_vlan}")
            if not self._add_interface_to_vlan(test_interface, target_vlan, tagging_mode=False):
                st.report_fail(
                    "msg",
                    f"Failed to move {test_interface} to VLAN {target_vlan}",
                    tcid=TC_IDS.access_change
                )

            st.log(f"{test_interface} moved to VLAN {target_vlan}")

            # Step 5: Verify port moved to VLAN 20 and VLAN 10 is Down
            st.banner(f"Step 5: Verify {test_interface} moved to VLAN {target_vlan}")

            # Verify port is in VLAN 20
            if not st.poll_wait(
                self._verify_vlan_member,
                self.data.verify_timeout,
                target_vlan,
                test_interface,
                should_exist=True
            ):
                st.report_fail(
                    "msg",
                    f"{test_interface} not found in VLAN {target_vlan} after change",
                    tcid=TC_IDS.access_change
                )

            # Verify VLAN 20 status is Up
            new_vlan_status = final_state.get("new_vlan_status", "Up")
            if not st.poll_wait(
                self._verify_vlan_status,
                self.data.verify_timeout,
                target_vlan,
                new_vlan_status
            ):
                st.report_fail(
                    "msg",
                    f"VLAN {target_vlan} status verification failed",
                    tcid=TC_IDS.access_change
                )

            # Verify VLAN 10 status is Down (no ports remaining)
            old_vlan_status = final_state.get("old_vlan_status", "Down")
            if not st.poll_wait(
                self._verify_vlan_status,
                self.data.verify_timeout,
                source_vlan,
                old_vlan_status
            ):
                st.report_fail(
                    "msg",
                    f"VLAN {source_vlan} should be {old_vlan_status} after port removal",
                    tcid=TC_IDS.access_change
                )

            st.log(f"Verified: {test_interface} successfully moved to VLAN {target_vlan}")
            st.log(f"Verified: VLAN {source_vlan} is {old_vlan_status} (no ports)")
            st.log(f"Verified: VLAN {target_vlan} is {new_vlan_status}")

            # Test passed
            st.report_tc_pass(TC_IDS.access_change, "msg", "Access port VLAN membership change successful")
            st.report_pass("test_case_passed")

        except Exception as e:
            st.error(f"Test failed with exception: {str(e)}")
            st.report_tc_fail(TC_IDS.access_change, "msg", f"Test failed: {str(e)}")
            st.report_fail("test_case_failed")
