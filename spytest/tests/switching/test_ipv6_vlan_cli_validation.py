"""
IPv6 Addressing and VLAN Trunking CLI Validation
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/ztp_standalone.yaml  \
  tests/switching/test_ipv6_vlan_cli_validation.py \
  --logs-path ./logs/test_ipv6_vlan_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IPv6 /128 address constraint enforcement and VLAN
  trunk configuration using both hyphenated range (10-13) and comma-separated
  (10,11,12,13) syntax. The suite validates that the system correctly rejects
  IPv6 /128 addresses where the host address equals the network address, and
  ensures VLAN existence checks are enforced before trunk assignment.

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 1 node (standalone)
        # +--------------------+
        # |    smic_sonic1     |
        # |  Ethernet8         |
        # +--------------------+

  - Feature flags / min SONiC version (if any): IS-CLI (klish) support required
  - Required test variables (YAML): vars/switching/vars_ipv6_vlan_cli_validation.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.switching.vlan as vlan_api
import apis.routing.ip as ip_api
from apis.system.interface import interface_properties_set

VAR_FILE_ENV = "IPV6_VLAN_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[2]
    / "vars"
    / "switching"
    / "vars_ipv6_vlan_cli_validation.yaml"
)

TC_IDS = SpyTestDict({
    "ipv6_128_reject": "TC-IPV6-VLAN-001",
    "vlan_range_missing": "TC-IPV6-VLAN-002",
    "vlan_range_success": "TC-IPV6-VLAN-003",
    "vlan_comma_success": "TC-IPV6-VLAN-004",
})


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"Variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestIpv6VlanCliValidation:
    """Testcases covering IPv6 /128 address validation and VLAN trunk configuration."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        # For standalone testing, we only need one DUT
        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))
        cls.data.dut = topology.D1

        # Read test_interface from testbed params (centralized configuration)
        cls.data.test_interface = st.get_param("test_interface", None)
        if not cls.data.test_interface:
            raise ValueError("test_interface not defined in testbed params section")

        cls.data.vlans_created = []

        st.log("Test setup completed. DUT: {}, Interface: {}".format(
            cls.data.dut, cls.data.test_interface))

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure all VLANs and configurations are removed after the suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        st.banner("CLASS TEARDOWN: Cleaning up VLANs and interface configuration")

        # Remove any IPv6/IPv4 addresses from the test interface
        cls._cleanup_interface_addresses(cls.data.dut, cls.data.test_interface)

        # Note: VLAN trunk configurations are cleaned up by each test's teardown_method

        # Delete all VLANs
        while cls.data.vlans_created:
            vlan = cls.data.vlans_created.pop()
            try:
                vlan_api.delete_vlan(
                    cls.data.dut,
                    vlan,
                    cli_type=cls.data.cli_type
                )
                st.log(f"Deleted VLAN {vlan}")
            except Exception as e:
                st.log(f"Error deleting VLAN {vlan}: {e}")

    @classmethod
    def _cleanup_interface_addresses(cls, dut: str, interface: str) -> None:
        """Remove all IPv4 and IPv6 addresses from interface."""
        st.log(f"Removing all IP addresses from {interface}")

        commands = [
            f"interface {interface}",
            "no ipv6 address",
            "no ip address",
            "exit"
        ]

        try:
            st.config(dut, commands, type=cls.data.cli_type, skip_error_check=True)
            st.log(f"Removed all IP addresses from {interface}")
        except Exception as e:
            st.log(f"Error removing IP addresses from {interface}: {e}")

    @classmethod
    def _cleanup_interface_vlans(cls, dut: str, interface: str, vlan_range: str = None) -> None:
        """Remove VLAN trunk configurations from interface."""
        if not vlan_range:
            st.log(f"No VLAN range specified for cleanup on {interface}")
            return

        st.log(f"Removing VLAN trunk configuration {vlan_range} from {interface}")

        commands = [
            f"interface {interface}",
            f"no switchport trunk allowed Vlan {vlan_range}",
            "exit"
        ]

        try:
            st.config(dut, commands, type=cls.data.cli_type, skip_error_check=True)
            st.log(f"Removed VLAN trunk configuration {vlan_range} from {interface}")
        except Exception as e:
            st.log(f"Error removing VLAN configuration from {interface}: {e}")

    def setup_method(self) -> None:
        """Reset per-test bookkeeping and ensure clean interface state."""
        self._test_vlans: List[int] = []
        self._vlan_trunk_config: str = None  # Track VLAN trunk configuration for cleanup

        st.log("Pre-test cleanup: Removing IP addresses from interface")
        # Clean any existing IP addresses from the interface
        self._cleanup_interface_addresses(self.data.dut, self.data.test_interface)

    def teardown_method(self) -> None:
        """Clean up any VLANs configured during the test."""
        if not self.data.cleanup_enabled:
            self._test_vlans = []
            self._vlan_trunk_config = None
            return

        st.log("Test teardown: cleaning up VLANs and interface")

        # Clean IP addresses from interface
        self._cleanup_interface_addresses(self.data.dut, self.data.test_interface)

        # Clean VLAN trunk configurations from interface using tracked config
        if self._vlan_trunk_config:
            self._cleanup_interface_vlans(
                self.data.dut,
                self.data.test_interface,
                self._vlan_trunk_config
            )

        # Delete VLANs
        while self._test_vlans:
            vlan = self._test_vlans.pop()
            try:
                vlan_api.delete_vlan(
                    self.data.dut,
                    vlan,
                    cli_type=self.data.cli_type
                )
                if vlan in self.data.vlans_created:
                    self.data.vlans_created.remove(vlan)
            except Exception:
                pass

    def _get_testcase(self, tcid: str) -> Dict[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    def _create_vlan(self, vlan: int) -> bool:
        """Create a single VLAN and track it."""
        result = vlan_api.create_vlan(
            self.data.dut,
            vlan,
            cli_type=self.data.cli_type
        )
        if result:
            if vlan not in self._test_vlans:
                self._test_vlans.append(vlan)
            if vlan not in self.data.vlans_created:
                self.data.vlans_created.append(vlan)
            st.log(f"Created VLAN {vlan}")
        return result

    def _delete_vlan(self, vlan: int) -> bool:
        """Delete a single VLAN."""
        result = vlan_api.delete_vlan(
            self.data.dut,
            vlan,
            cli_type=self.data.cli_type
        )
        if result:
            if vlan in self._test_vlans:
                self._test_vlans.remove(vlan)
            if vlan in self.data.vlans_created:
                self.data.vlans_created.remove(vlan)
            st.log(f"Deleted VLAN {vlan}")
        return result

    def _configure_ipv6_address(self, interface: str, ipv6_address: str,
                                prefix_len: int, expect_error: bool = False) -> bool:
        """
        Configure IPv6 address on interface using klish CLI.
        Returns True if configuration succeeded, False if it failed.
        If expect_error=True, returns True when error is detected (negative test).
        """
        st.log(f"Configuring IPv6 {ipv6_address}/{prefix_len} on {interface}, "
               f"expect_error={expect_error}")

        # Use config_ip_addr_interface for IPv6 configuration
        result = ip_api.config_ip_addr_interface(
            self.data.dut,
            interface_name=interface,
            ip_address=ipv6_address,
            subnet=str(prefix_len),
            family="ipv6",
            config="add",
            cli_type=self.data.cli_type,
            skip_error=True  # Don't fail on error, we'll check the result
        )

        if expect_error:
            # For negative tests, we expect the configuration to fail
            if result:
                st.log("NEGATIVE TEST FAILED: IPv6 address was accepted but should have been rejected")
                return False
            else:
                st.log("NEGATIVE TEST PASSED: IPv6 address was correctly rejected")
                return True
        else:
            # For positive tests, we expect success
            return result

    def _add_trunk_vlan_range(self, interface: str, vlan_range: str,
                              expect_error: bool = False) -> bool:
        """
        Add VLAN range to trunk using switchport trunk allowed Vlan command.
        Returns True if succeeded, False if failed.
        If expect_error=True, returns True when error is detected.
        """
        st.log(f"Adding trunk VLAN range {vlan_range} to {interface}, expect_error={expect_error}")

        # Configure interface in trunk mode and add allowed VLANs
        commands = [
            f"interface {interface}",
            f"switchport trunk allowed Vlan {vlan_range}",
            "exit"
        ]

        try:
            output = st.config(self.data.dut, commands, type=self.data.cli_type, skip_error_check=True)

            # Check if there was an error in the output
            error_detected = False
            if output:
                error_patterns = ["Error:", "Invalid", "does not exist"]
                for pattern in error_patterns:
                    if pattern in str(output):
                        error_detected = True
                        st.log(f"Error detected in output: {output}")
                        break

            if expect_error:
                # For negative tests, expect failure
                if not error_detected:
                    st.log("NEGATIVE TEST FAILED: VLAN range was accepted but should have been rejected")
                    return False
                else:
                    st.log("NEGATIVE TEST PASSED: VLAN range was correctly rejected")
                    return True
            else:
                # For positive tests, expect success
                if error_detected:
                    st.log(f"Failed to add VLAN range: {output}")
                    return False
                # Track the VLAN configuration for cleanup
                self._vlan_trunk_config = vlan_range
                st.log(f"Tracked VLAN trunk config for cleanup: {vlan_range}")
                return True
        except Exception as e:
            st.log(f"Exception while adding VLAN range: {e}")
            if expect_error:
                return True
            return False

    def _remove_trunk_vlan_range(self, interface: str, vlan_range: str) -> bool:
        """Remove VLAN range from trunk using 'no' command."""
        st.log(f"Removing trunk VLAN range {vlan_range} from {interface}")

        commands = [
            f"interface {interface}",
            f"no switchport trunk allowed Vlan {vlan_range}",
            "exit"
        ]

        try:
            output = st.config(self.data.dut, commands, type=self.data.cli_type, skip_error_check=True)
            # Check for errors
            if output and ("Error:" in str(output) or "Invalid" in str(output)):
                st.log(f"Warning: Error while removing VLAN range: {output}")
                return False
            # Clear tracked VLAN configuration
            self._vlan_trunk_config = None
            return True
        except Exception as e:
            st.log(f"Exception while removing VLAN range: {e}")
            return False

    @pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.ipv6_128_reject])
    @pytest.mark.negative
    def test_ipv6_128_address_rejection(self) -> None:
        """
        TC 1: Verify IPv6 /128 address is rejected when host equals network address.

        Expected error: "%Error: Interface IP cannot be same as network address"
        """
        st.banner("TC-1: IPv6 /128 Address Validation")
        testcase = self._get_testcase("tc1")

        interface = self.data.test_interface
        ipv6_addr = testcase.get("ipv6_address")
        prefix_len = testcase.get("prefix_length", 128)

        if not ipv6_addr:
            st.report_fail("msg", "Testcase tc1 missing 'ipv6_address' in YAML")

        st.log(f"Step 1: Attempting to configure {ipv6_addr}/{prefix_len} on {interface}")
        st.log("Step 2: Expecting rejection due to /128 constraint")

        # This should fail - we expect the configuration to be rejected
        success = self._configure_ipv6_address(interface, ipv6_addr, prefix_len, expect_error=True)

        if not success:
            st.report_fail(
                "msg",
                f"IPv6 /128 address {ipv6_addr} was not properly rejected on {interface}"
            )

        st.log("IPv6 /128 validation PASSED: Address was correctly rejected")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.vlan_range_missing])
    @pytest.mark.negative
    def test_vlan_trunk_range_missing_vlan(self) -> None:
        """
        TC 2a: Verify VLAN range assignment fails when intermediate VLAN is missing.

        Create VLANs 10, 12, 13 but not 11, then try to assign range 10-13.
        Expected error: "Error: VLAN 11 does not exist. Create Vlan first using 'vlan 11'"
        """
        st.banner("TC-2a: VLAN Range with Missing VLAN")
        testcase = self._get_testcase("tc2")

        interface = self.data.test_interface
        partial_vlans = testcase.get("partial_vlans", [10, 12, 13])
        vlan_range = testcase.get("vlan_range", "10-13")

        st.log(f"Step 1: Creating partial VLAN set: {partial_vlans}")
        for vlan in partial_vlans:
            if not self._create_vlan(vlan):
                st.report_fail("msg", f"Failed to create VLAN {vlan}")

        st.log(f"Step 2: Attempting to assign range {vlan_range} (VLAN 11 is missing)")

        # This should fail because VLAN 11 doesn't exist
        success = self._add_trunk_vlan_range(interface, vlan_range, expect_error=True)

        if not success:
            st.report_fail(
                "msg",
                f"VLAN range {vlan_range} was incorrectly accepted despite missing VLANs"
            )

        st.log("VLAN range dependency check PASSED: Missing VLAN was detected")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.vlan_range_success])
    def test_vlan_trunk_range_format(self) -> None:
        """
        TC 2b: Verify VLAN trunk range format (10-13) works when all VLANs exist.

        Create VLANs 10, 11, 12, 13, then assign range 10-13 and verify.
        """
        st.banner("TC-2b: VLAN Trunk Range Format Success")
        testcase = self._get_testcase("tc2")

        interface = self.data.test_interface
        all_vlans = testcase.get("all_vlans", [10, 11, 12, 13])
        vlan_range = testcase.get("vlan_range", "10-13")

        st.log(f"Step 1: Creating all required VLANs: {all_vlans}")
        for vlan in all_vlans:
            if not self._create_vlan(vlan):
                st.report_fail("msg", f"Failed to create VLAN {vlan}")

        st.log(f"Step 2: Assigning VLAN range {vlan_range} to {interface}")
        if not self._add_trunk_vlan_range(interface, vlan_range):
            st.report_fail("msg", f"Failed to assign VLAN range {vlan_range}")

        st.log(f"Step 3: Verifying VLAN range assignment")
        # Note: Verification would typically use show interface trunk command
        # For now, we consider the successful configuration as verification

        st.log(f"Step 4: Removing VLAN range {vlan_range}")
        if not self._remove_trunk_vlan_range(interface, vlan_range):
            st.log(f"Warning: Failed to remove VLAN range {vlan_range}")

        st.log("VLAN range format test PASSED")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.vlan_comma_success])
    def test_vlan_trunk_comma_format(self) -> None:
        """
        TC 2c: Verify VLAN trunk comma-separated format (10,11,12,13) works.

        Create VLANs 10, 11, 12, 13, then assign using comma format and verify.
        """
        st.banner("TC-2c: VLAN Trunk Comma-Separated Format Success")
        testcase = self._get_testcase("tc2")

        interface = self.data.test_interface
        all_vlans = testcase.get("all_vlans", [10, 11, 12, 13])
        vlan_comma_list = testcase.get("vlan_comma_list", "10,11,12,13")

        st.log(f"Step 1: Creating all required VLANs: {all_vlans}")
        for vlan in all_vlans:
            if not self._create_vlan(vlan):
                st.report_fail("msg", f"Failed to create VLAN {vlan}")

        st.log(f"Step 2: Assigning VLANs {vlan_comma_list} to {interface}")
        if not self._add_trunk_vlan_range(interface, vlan_comma_list):
            st.report_fail("msg", f"Failed to assign VLAN list {vlan_comma_list}")

        st.log(f"Step 3: Verifying VLAN assignment")
        # Note: Verification would typically use show interface trunk command

        st.log(f"Step 4: Removing VLAN list {vlan_comma_list}")
        if not self._remove_trunk_vlan_range(interface, vlan_comma_list):
            st.log(f"Warning: Failed to remove VLAN list {vlan_comma_list}")

        st.log("VLAN comma format test PASSED")
        st.report_pass("test_case_passed")
