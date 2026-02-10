"""
IP INTERFACE CONFIGURATION & VALIDATION
Author: Shiva
2026

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/ztp_standalone.yaml \\
  tests/system/interface/test_interface_ip_config_validation.py \\
  --logs-path ./logs/interface_ip_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates IP interface configuration and display functionality in IS-CLI (sonic-cli).
  Tests three critical scenarios:

  1. Management IP Visibility - Verifies that 'show ip interfaces' correctly displays
     the Management interface IP address, ensuring CLI parser works correctly.

  2. Loopback Subnet Mask Constraint - Validates that CLI strictly enforces /32 subnet
     mask requirement for Loopback interfaces, rejecting any other mask values.

  3. Primary vs Secondary IP Overlap Prevention - Ensures the system prevents assigning
     the same IP address as both Primary and Secondary on the same interface.

Pre-requisites:
  - Topology: standalone (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node (standalone)
        # +--------------------+
        # |        DUT1        |
        # | Management: eth0   |
        # | Test: Ethernet0    |
        # | Test: Loopback1    |
        # +--------------------+

  - Feature: Interface Management (IP/Management/Loopback)
  - CLI Mode: IS-CLI (klish) required
  - Required test variables (YAML): vars/system/interface/vars_interface_ip_config.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api
import apis.system.interface_ip_api as intf_ip_api

# Test case identifiers
TC_IDS = SpyTestDict({
    "management_ip_visibility": "IP-INTF-CONFIG-001-TC01",
    "loopback_constraint": "IP-INTF-CONFIG-001-TC02",
    "primary_secondary_overlap": "IP-INTF-CONFIG-001-TC03",
})

# YAML variable file path
VAR_FILE_ENV = "INTERFACE_IP_CONFIG_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "interface"
    / "vars_interface_ip_config.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """
    Load test case variables from YAML file with optional environment override.

    :return: Dictionary containing test configuration
    :raises FileNotFoundError: If YAML file is not found
    :raises ValueError: If YAML structure is invalid
    """
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"Interface IP config variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("Interface IP config YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestInterfaceIpConfig:
    """
    Test suite for IP interface configuration and validation.

    This class contains test cases that validate IP interface display, Loopback
    constraints, and IP address overlap detection in IS-CLI.
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """
        Collect topology handles and test case variables for the suite.

        This method is called once before all tests in the class.
        It loads configuration from YAML and sets up the test environment.
        """
        st.banner("IP INTERFACE CONFIG VALIDATION TEST SUITE - SETUP")

        # Load test configuration from YAML
        config = _load_yaml_data()
        defaults = config.get("defaults", {})
        interface_config = config.get("interface_config", {})

        # Get testbed topology (standalone DUT scenario)
        topology = st.get_testbed_vars()

        # Store configuration in class data
        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.interface_config = SpyTestDict(interface_config)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        # CLI type configuration
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        # Device mapping
        cls.data.dut = topology.D1 if hasattr(topology, 'D1') else st.get_dut_names()[0]
        cls.data.dut_names = st.get_dut_names()

        # Get test interfaces from config
        cls.data.test_interface = interface_config.get("test_interface", "Ethernet0")
        cls.data.loopback_name = interface_config.get("loopback_name", "Loopback1")

        st.log(f"Test configuration loaded. DUT: {cls.data.dut}, CLI type: {cls.data.cli_type}")
        st.log(f"Test interface: {cls.data.test_interface}, Loopback: {cls.data.loopback_name}")

        # Set terminal length to 0 to avoid pagination (--more--)
        st.log("Setting terminal length to 0 to avoid pagination")
        cls._set_terminal_length_zero()

        # PRE-TEST CLEANUP: Remove any existing test configurations
        st.banner("PRE-TEST CLEANUP: Removing existing test configurations")
        cls._cleanup_test_interfaces()
        st.log("✓ Pre-test cleanup completed - starting with clean state")

    @classmethod
    def teardown_class(cls) -> None:
        """
        Ensure all test configurations are removed after the suite completes.

        This method is called once after all tests in the class.
        """
        st.banner("IP INTERFACE CONFIG VALIDATION TEST SUITE - TEARDOWN")

        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        # POST-TEST CLEANUP: Remove all test configurations
        st.banner("POST-TEST CLEANUP: Removing all test configurations")
        cls._cleanup_test_interfaces()
        st.log("✓ Post-test cleanup completed - test configurations removed")
        st.log("Test suite teardown completed")

    def setup_method(self) -> None:
        """
        Reset per-test bookkeeping.

        This method is called before each individual test.
        """
        st.banner(f"Starting test method: {self._testMethodName if hasattr(self, '_testMethodName') else 'unknown'}")

        # Ensure terminal length is 0 before each test (avoid pagination)
        self._set_terminal_length_zero()

    def teardown_method(self) -> None:
        """
        Clean up configurations after each test.

        This method is called after each individual test.
        """
        st.banner(f"Cleaning up test method: {self._testMethodName if hasattr(self, '_testMethodName') else 'unknown'}")

        if not self.data.cleanup_enabled:
            return

        # Clean up after each test to ensure isolation
        self._cleanup_test_interfaces()

    @classmethod
    def _set_terminal_length_zero(cls) -> None:
        """
        Set terminal length to 0 to prevent pagination (--more--).

        This prevents "show running-configuration" and other show commands
        from pausing for user input when output exceeds screen length.

        Must be called:
        - In setup_class() - for initial setup
        - In setup_method() - before each test (session might reset)
        """
        try:
            if cls.data.cli_type == "klish":
                # For IS-CLI (klish), exit to enable mode first then set terminal length
                # This ensures the command works regardless of current CLI mode
                cmd = "end\nterminal length 0"
                st.config(cls.data.dut, cmd, type=cls.data.cli_type, skip_error_check=True, conf=False)
                st.log("✓ Terminal length set to 0 (pagination disabled)")
            elif cls.data.cli_type == "click":
                # For Click CLI, pagination is typically not an issue
                # But we can set TERM environment if needed
                st.log("Click CLI - pagination not applicable")
            else:
                st.log(f"Terminal length setting for CLI type {cls.data.cli_type}")

        except Exception as e:
            st.warn(f"Could not set terminal length (non-critical): {e}")

    @classmethod
    def _cleanup_test_interfaces(cls) -> None:
        """
        Remove IP configurations from test interfaces and delete test Loopback.

        This method cleans up:
        - All IP addresses on test interface (Ethernet0)
        - Loopback interface (Loopback1)
        """
        st.log("Cleaning up test interface configurations")

        try:
            # Clean test physical interface
            if cls.data.test_interface:
                st.log(f"Removing IP addresses from {cls.data.test_interface}")
                # Exit interface mode, then config mode to return to enable mode
                cmd = f"interface {cls.data.test_interface}\n no ip address\n exit\n exit"
                st.config(cls.data.dut, cmd, type=cls.data.cli_type,
                         skip_error_check=True, conf=True)

            # Clean Loopback interface
            if cls.data.loopback_name:
                st.log(f"Removing {cls.data.loopback_name}")
                intf_ip_api.config_loopback_interface(
                    dut=cls.data.dut,
                    loopback_name=cls.data.loopback_name,
                    config="remove",
                    cli_type=cls.data.cli_type,
                    skip_error_check=True
                )

            st.log("✓ Interface cleanup completed")

        except Exception as e:
            st.warn(f"Error during interface cleanup (non-critical): {e}")

    @pytest.mark.inventory(feature="Regression", testcases=["IP-INTF-CONFIG-001-TC01"])
    def test_management_ip_visibility(self) -> None:
        """
        TC01 - Verify Management interface IP is visible in 'show ip interfaces'.

        Test Steps:
        1. Execute 'show ip interfaces' command in IS-CLI (klish)
        2. Parse output for Management interface (Management0/eth0)
        3. Verify IP address is displayed
        4. Validate IP address format

        Expected Behavior:
        - Management interface should appear in output
        - IP address should be visible and properly formatted
        - Output should match underlying system state
        """
        st.banner("TEST CASE: Management IP Visibility in CLI")

        tc_data = self.data.testcases.get("management_ip_visibility")
        if not tc_data:
            st.report_fail("msg", "Test case 'management_ip_visibility' not found in YAML")

        # Execute show ip interfaces command
        st.log("Executing 'show ip interfaces' command")
        interfaces_output = intf_ip_api.show_ip_interfaces(
            dut=self.data.dut,
            cli_type=self.data.cli_type,
            skip_tmpl=True
        )

        if not interfaces_output:
            st.report_fail("msg", "No output from 'show ip interfaces' command")

        st.log(f"Command output received ({len(interfaces_output)} characters)")

        # Verify Management interface IP is visible
        success, ip_address, details = intf_ip_api.verify_management_ip_visible(
            dut=self.data.dut,
            cli_type=self.data.cli_type
        )

        if not success:
            error_msg = details.get('error', 'Unknown error')
            st.report_fail("msg", f"Management interface verification failed: {error_msg}")

        st.log(f"✓ Management interface found: {details.get('interface')}")
        st.log(f"✓ Management IP address: {ip_address}")

        # Additional validation - IP format check
        expected = tc_data.get("expected", {})
        ip_format_regex = expected.get("ip_format_regex")

        if ip_format_regex and ip_address:
            import re
            if not re.search(ip_format_regex, ip_address):
                st.report_fail("msg", f"IP address format mismatch: {ip_address}")

        st.log("✓✓ Test passed: Management IP is visible in 'show ip interfaces'")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["IP-INTF-CONFIG-001-TC02"])
    @pytest.mark.negative
    def test_loopback_subnet_mask_constraint(self) -> None:
        """
        TC02 - Verify Loopback interface strictly enforces /32 subnet mask.

        Test Steps:
        1. Create Loopback interface (Loopback1)
        2. Attempt to configure IP with /24 mask → expect ERROR
        3. Attempt to configure IP with /30 mask → expect ERROR
        4. Configure IP with /32 mask → expect SUCCESS
        5. Verify /32 IP appears in running-config
        6. Cleanup Loopback interface

        Expected Behavior:
        - /24 and /30 masks should be REJECTED with error message
        - Only /32 mask should be ACCEPTED
        - Error message: "Loopback interface only supports /32 mask"
        """
        st.banner("TEST CASE: Loopback Interface Subnet Mask Constraint")

        tc_data = self.data.testcases.get("loopback_constraint")
        if not tc_data:
            st.report_fail("msg", "Test case 'loopback_constraint' not found in YAML")

        loopback_config = tc_data.get("loopback", {})
        loopback_name = loopback_config.get("name", self.data.loopback_name)
        test_ip = loopback_config.get("test_ip", "10.0.0.1")
        invalid_masks = loopback_config.get("invalid_masks", [24, 30])
        valid_mask = loopback_config.get("valid_mask", 32)

        # Step 1: Create Loopback interface
        st.log(f"Step 1: Creating {loopback_name}")
        result = intf_ip_api.config_loopback_interface(
            dut=self.data.dut,
            loopback_name=loopback_name,
            config="add",
            cli_type=self.data.cli_type
        )

        if not result:
            st.report_fail("msg", f"Failed to create {loopback_name}")

        st.log(f"✓ {loopback_name} created successfully")

        # Step 2 & 3: Test invalid subnet masks (should be rejected)
        for invalid_mask in invalid_masks:
            st.log(f"Step: Testing INVALID mask /{invalid_mask} (should be rejected)")

            result = intf_ip_api.config_loopback_ip_address(
                dut=self.data.dut,
                loopback_name=loopback_name,
                ip_address=test_ip,
                subnet_mask=invalid_mask,
                config="add",
                cli_type=self.data.cli_type,
                expect_error=True  # We expect this to fail
            )

            if not result['success']:
                st.report_fail("msg", f"Mask /{invalid_mask} should have been rejected but wasn't")

            if result['accepted']:
                st.report_fail("msg", f"Mask /{invalid_mask} was incorrectly accepted (should reject non-/32)")

            st.log(f"✓ Mask /{invalid_mask} correctly rejected")

        # Step 4: Test valid /32 mask (should be accepted)
        st.log(f"Step: Testing VALID mask /{valid_mask} (should be accepted)")

        result = intf_ip_api.config_loopback_ip_address(
            dut=self.data.dut,
            loopback_name=loopback_name,
            ip_address=test_ip,
            subnet_mask=valid_mask,
            config="add",
            cli_type=self.data.cli_type,
            expect_error=False  # Should succeed
        )

        if not result['success']:
            error_msg = result.get('error', 'Unknown error')
            st.report_fail("msg", f"Valid mask /{valid_mask} was rejected: {error_msg}")

        if not result['accepted']:
            st.report_fail("msg", f"Mask /{valid_mask} was not accepted")

        st.log(f"✓ Mask /{valid_mask} correctly accepted")

        # Step 5: Verify IP appears in running-config
        st.wait(2, "Waiting for configuration to stabilize")

        verified = intf_ip_api.verify_interface_ip_in_config(
            dut=self.data.dut,
            interface=loopback_name,
            ip_address=test_ip,
            subnet_mask=valid_mask,
            cli_type=self.data.cli_type,
            should_exist=True
        )

        if not verified:
            st.report_fail("msg", f"IP {test_ip}/{valid_mask} not found in running-config")

        st.log(f"✓ IP {test_ip}/{valid_mask} verified in running-config")

        st.log("✓✓ Test passed: Loopback interface correctly enforces /32 mask constraint")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["IP-INTF-CONFIG-001-TC03"])
    @pytest.mark.negative
    def test_primary_secondary_ip_overlap(self) -> None:
        """
        TC03 - Verify prevention of duplicate IP as Primary and Secondary.

        Test Steps:
        1. Configure primary IP address on physical interface
        2. Verify primary IP is set in running-config
        3. Attempt to add SAME IP as secondary → expect ERROR
        4. Verify only ONE IP entry exists in running-config (no duplicate)
        5. Test valid secondary IP (different from primary) → expect SUCCESS
        6. Cleanup all IP configurations

        Expected Behavior:
        - Duplicate IP as secondary should be REJECTED
        - Error: "IPv4 address: x.x.x.x/xx is already configured as primary"
        - Different secondary IP should be ACCEPTED
        """
        st.banner("TEST CASE: Primary vs Secondary IP Overlap Prevention")

        tc_data = self.data.testcases.get("primary_secondary_overlap")
        if not tc_data:
            st.report_fail("msg", "Test case 'primary_secondary_overlap' not found in YAML")

        interface_config = tc_data.get("interface", {})
        test_interface = interface_config.get("name", self.data.test_interface)
        primary_ip = interface_config.get("primary_ip")
        primary_subnet = interface_config.get("primary_subnet")
        secondary_ip_same = interface_config.get("secondary_ip")  # Same as primary
        secondary_subnet = interface_config.get("secondary_subnet")
        valid_secondary_ip = interface_config.get("valid_secondary_ip")

        # Step 1: Configure primary IP address
        st.log(f"Step 1: Configuring PRIMARY IP {primary_ip}/{primary_subnet} on {test_interface}")

        result = ip_api.config_ip_addr_interface(
            dut=self.data.dut,
            interface_name=test_interface,
            ip_address=primary_ip,
            subnet=primary_subnet,
            family="ipv4",
            config="add",
            cli_type=self.data.cli_type
        )

        if not result:
            st.report_fail("msg", f"Failed to configure primary IP on {test_interface}")

        st.log(f"✓ Primary IP {primary_ip}/{primary_subnet} configured")

        # Step 2: Verify primary IP is set
        st.wait(2, "Waiting for configuration to stabilize")

        verified = intf_ip_api.verify_interface_ip_in_config(
            dut=self.data.dut,
            interface=test_interface,
            ip_address=primary_ip,
            subnet_mask=primary_subnet,
            cli_type=self.data.cli_type,
            should_exist=True
        )

        if not verified:
            st.report_fail("msg", f"Primary IP {primary_ip}/{primary_subnet} not found in running-config")

        st.log(f"✓ Primary IP verified in running-config")

        # Step 3: Attempt to configure SAME IP as secondary (should be rejected)
        st.log(f"Step 3: Attempting to add DUPLICATE IP as secondary (should be rejected)")

        result = intf_ip_api.config_secondary_ip_address(
            dut=self.data.dut,
            interface=test_interface,
            ip_address=secondary_ip_same,
            subnet_mask=secondary_subnet,
            cli_type=self.data.cli_type,
            expect_error=True  # We expect this to be rejected
        )

        if not result['success']:
            st.report_fail("msg", "Duplicate secondary IP should have been rejected but test failed")

        if result['accepted']:
            st.report_fail("msg", f"Duplicate IP {secondary_ip_same}/{secondary_subnet} was incorrectly accepted as secondary")

        st.log(f"✓ Duplicate secondary IP correctly rejected")
        st.log(f"  Error message: {result.get('error', 'N/A')}")

        # Step 4: Verify only ONE IP entry exists (no duplicate)
        st.wait(2, "Waiting for configuration check")

        # The duplicate should NOT appear as secondary
        duplicate_exists = intf_ip_api.verify_interface_ip_in_config(
            dut=self.data.dut,
            interface=test_interface,
            ip_address=secondary_ip_same,
            subnet_mask=secondary_subnet,
            cli_type=self.data.cli_type,
            is_secondary=True,
            should_exist=False  # Should NOT exist as secondary
        )

        if not duplicate_exists:
            st.report_fail("msg", "Verification failed: duplicate check")

        st.log(f"✓ Verified: No duplicate IP entry in running-config")

        # Step 5: Configure DIFFERENT secondary IP (should succeed)
        if valid_secondary_ip:
            st.log(f"Step 5: Configuring VALID secondary IP {valid_secondary_ip}/{secondary_subnet}")

            result = intf_ip_api.config_secondary_ip_address(
                dut=self.data.dut,
                interface=test_interface,
                ip_address=valid_secondary_ip,
                subnet_mask=secondary_subnet,
                cli_type=self.data.cli_type,
                expect_error=False  # Should succeed
            )

            if not result['success']:
                error_msg = result.get('error', 'Unknown error')
                st.report_fail("msg", f"Valid secondary IP was rejected: {error_msg}")

            st.log(f"✓ Valid secondary IP {valid_secondary_ip} accepted")

        st.log("✓✓ Test passed: System correctly prevents duplicate IP as Primary+Secondary")
        st.report_pass("test_case_passed")
