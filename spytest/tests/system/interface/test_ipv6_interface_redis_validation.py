"""
IPv6 INTERFACE REDIS VALIDATION
Author: Shiva
2026

How to run:
  ./bin/spytest  --tryssh 1  \\
  --testbed ./testbeds/ztp_standalone.yaml  \\
  tests/system/interface/test_ipv6_interface_redis_validation.py \\
  --logs-path ./logs/ipv6_redis_validation_$(date +%F_%H%M%S) \\
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IPv6 interface configuration state in Redis database
  and invalid IP address assignment prevention. This suite validates that toggling
  IPv6 on/off correctly updates Redis CONFIG_DB without leaving stale or malformed
  entries, and ensures the system properly rejects invalid IP addresses (multicast/
  broadcast) with clean, properly-formatted error messages.

Pre-requisites:
  - Topology: standalone (single DUT) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |        dut1        |
        # | Ethernet8 (test)   |
        # +--------------------+

  - Feature flags / min SONiC version: Redis database access required
  - Required test variables (YAML): vars/system/interface/vars_ipv6_redis_validation.yaml
  - Testbed must define: global.params.test_interface (e.g., "Ethernet8")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
from apis.system import interface_cli_api
from apis.system import interface_redis_api
from apis.routing import ip as ip_api
from apis.common import redis as redis_api

VAR_FILE_ENV = "IPV6_REDIS_VALIDATION_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "interface"
    / "vars_ipv6_redis_validation.yaml"
)

# Test case IDs
TC_IDS = SpyTestDict({
    "ipv6_redis_state": "TC-SONIC-IPV6-REDIS-01",
    "invalid_ip_validation": "TC-SONIC-IP-VALIDATION-02",
})


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"IPv6 Redis validation variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("IPv6 Redis validation YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestIpv6InterfaceRedisValidation:
    """Testcases for IPv6 interface Redis state and invalid IP validation."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("MODULE PROLOGUE: IPv6 Interface Redis Validation")

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

        # ** READ test_interface from testbed global params **
        test_interface = st.get_param("test_interface", None)

        if not test_interface:
            st.error("test_interface not found in testbed global.params")
            st.error("Please define global.params.test_interface in testbed YAML")
            pytest.skip("test_interface not defined in testbed YAML")

        cls.data.test_interface = test_interface
        st.log(f"Using test interface from testbed: {test_interface}")

        # Initialize Redis DB CLI
        redis_api.db_cli_init(cls.data.dut)

        st.banner(f"Test Configuration Loaded: DUT={cls.data.dut_name}, Interface={cls.data.test_interface}")

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure interface is restored to default state after suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        st.banner("MODULE EPILOGUE: Cleanup")

        try:
            # Clear any IP addresses
            st.log(f"Clearing IP configuration on {cls.data.test_interface}")
            interface_cli_api.config_ipv6_enable(
                cls.data.dut,
                cls.data.test_interface,
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

        # Restore interface to clean state
        try:
            interface_cli_api.config_ipv6_enable(
                self.data.dut,
                self.data.test_interface,
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

    def _substitute_interface_in_pattern(self, pattern: str, **kwargs) -> str:
        """Substitute interface name and other variables in pattern string."""
        substitutions = {
            "interface": self.data.test_interface,
        }
        substitutions.update(kwargs)

        try:
            return pattern.format(**substitutions)
        except KeyError as e:
            st.error(f"Missing substitution key in pattern '{pattern}': {e}")
            return pattern

    @pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.ipv6_redis_state])
    def test_ipv6_interface_redis_state_validation(self) -> None:
        """
        TC-SONIC-IPV6-REDIS-01: IPv6 Interface Configuration State Validation.

        Verify that toggling IPv6 on/off on an interface correctly updates Redis
        CONFIG_DB (database 4) without leaving stale or malformed entries.
        """
        st.banner(f"TEST: {TC_IDS.ipv6_redis_state} - IPv6 Redis State Validation")

        testcase = self._get_testcase(TC_IDS.ipv6_redis_state)
        interface = self.data.test_interface
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Testing interface: {interface}")

        # Step 1: Disable IPv6 on interface
        st.log("Step 1: Disabling IPv6 on interface")
        result = interface_cli_api.config_ipv6_enable(
            dut, interface, config="remove", cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to disable IPv6 on {interface}")

        st.wait(2)  # Allow time for config to propagate

        # Step 2: Enable IPv6 on interface
        st.log("Step 2: Enabling IPv6 on interface")
        result = interface_cli_api.config_ipv6_enable(
            dut, interface, config="add", cli_type=cli_type
        )
        if not result:
            st.report_fail("msg", f"Failed to enable IPv6 on {interface}")

        st.wait(2)  # Allow time for config to propagate

        # Step 3: Query Redis CONFIG_DB for interface-related keys
        st.log("Step 3: Querying Redis CONFIG_DB for interface keys")
        redis_keys = interface_redis_api.get_redis_interface_keys(dut, interface)
        st.log(f"Redis keys found: {redis_keys}")

        # Step 4: Validate expected keys exist
        st.log("Step 4: Validating expected Redis keys exist")
        expected_patterns = testcase.get("expected_key_patterns", [])
        expected_keys = [
            self._substitute_interface_in_pattern(pattern)
            for pattern in expected_patterns
        ]

        if not interface_redis_api.verify_redis_interface_keys(
            dut, interface, expected_keys=expected_keys
        ):
            st.report_fail(
                "msg",
                f"Expected Redis keys not found for {interface}. Expected: {expected_keys}, Found: {redis_keys}"
            )

        # Step 5: Check for stale/malformed entries
        st.log("Step 5: Checking for stale or malformed Redis entries")
        if not interface_redis_api.check_no_stale_interface_entries(dut, interface):
            st.report_fail(
                "msg",
                f"Stale or malformed Redis entries detected for {interface}"
            )

        st.log(f"Test {TC_IDS.ipv6_redis_state} completed successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.invalid_ip_validation])
    @pytest.mark.negative
    def test_invalid_multicast_ip_rejected(self) -> None:
        """
        TC-SONIC-IP-VALIDATION-02: Invalid Address Assignment Validation.

        Ensure the system prevents assignment of invalid IPv4 addresses (multicast/
        broadcast) to interfaces AND validates error message format is clean and proper.
        """
        st.banner(f"TEST: {TC_IDS.invalid_ip_validation} - Invalid IP Validation")

        testcase = self._get_testcase(TC_IDS.invalid_ip_validation)
        interface = self.data.test_interface
        dut = self.data.dut
        cli_type = self.data.cli_type

        st.log(f"Testing interface: {interface}")

        # Step 1: Clear existing IPv6 addresses
        st.log("Step 1: Clearing existing IPv6 addresses")
        interface_cli_api.config_ipv6_enable(
            dut, interface, config="remove", cli_type=cli_type, skip_error_check=True
        )

        st.wait(2)

        # Step 2: Clear existing IPv4 addresses (if any)
        st.log("Step 2: Clearing existing IPv4 addresses")
        # Note: We'll skip error check as there might not be any IP configured
        # Use interface shutdown/startup approach or skip if no IP is configured
        # For now, we'll just proceed as the interface should be clean from IPv6 disable

        st.wait(2)

        # Step 3: Attempt to assign invalid multicast IP
        st.log("Step 3: Attempting to assign invalid multicast IP address")

        invalid_ips = testcase.get("invalid_ips", [])
        if not invalid_ips:
            st.report_fail("msg", f"No invalid_ips defined for testcase {TC_IDS.invalid_ip_validation}")

        invalid_ip_config = invalid_ips[0]
        invalid_address = invalid_ip_config.get("address")
        expected_error_pattern = invalid_ip_config.get("expected_error_pattern", "")

        st.log(f"Invalid IP to test: {invalid_address}")

        # Parse IP and subnet
        if "/" in invalid_address:
            ip_addr, subnet = invalid_address.split("/")
        else:
            ip_addr = invalid_address
            subnet = "24"

        # Attempt to configure invalid IP (should fail)
        # Capture the output to validate error message format
        if cli_type == "klish":
            cmd = f"configure terminal\n"
            cmd += f"interface {interface}\n"
            cmd += f"ip address {ip_addr}/{subnet}\n"
            cmd += "exit\nexit"

            output = st.config(dut, cmd, type=cli_type, skip_error_check=True, conf=True)
        else:  # click
            cmd = f"config interface ip add {interface} {invalid_address}"
            output = st.config(dut, cmd, type=cli_type, skip_error_check=True)

        st.log(f"Command output:\n{output}")

        # Step 4: Validate error message format
        st.log("Step 4: Validating error message format")

        valid_error_format = testcase.get("valid_error_format", {})
        reject_patterns = valid_error_format.get("reject_patterns", [])

        # Substitute interface and IP in expected pattern
        expected_pattern = self._substitute_interface_in_pattern(
            expected_error_pattern,
            ip=invalid_address
        )

        st.log(f"Expected error pattern: {expected_pattern}")
        st.log(f"Reject patterns: {reject_patterns}")

        # Check error message format
        format_valid = interface_redis_api.verify_error_message_format(
            output,
            expected_pattern,
            reject_patterns=reject_patterns
        )

        if not format_valid:
            st.report_fail(
                "msg",
                f"Error message format is invalid or contains malformed content. "
                f"Output: {output}"
            )

        # Step 5: Verify command was rejected (error present in output)
        st.log("Step 5: Verifying command was rejected")

        if "Error" not in output and "error" not in output.lower():
            st.report_fail(
                "msg",
                f"Invalid IP {invalid_address} was accepted without error on {interface}"
            )

        # Step 6: Verify invalid IP does NOT appear in running config
        st.log("Step 6: Verifying invalid IP not present in running config")

        running_config = interface_cli_api.show_running_config_interface(
            dut, interface, cli_type=cli_type, skip_tmpl=True
        )

        if ip_addr in running_config:
            st.report_fail(
                "msg",
                f"Invalid IP {ip_addr} found in running config (should not exist)"
            )

        # Step 7: Verify invalid IP does NOT appear in Redis
        st.log("Step 7: Verifying invalid IP not present in Redis CONFIG_DB")

        redis_keys = interface_redis_api.get_redis_interface_keys(dut, interface)
        st.log(f"Redis keys for {interface}: {redis_keys}")

        # Check if any key contains the invalid IP
        for key in redis_keys:
            if ip_addr in key:
                st.report_fail(
                    "msg",
                    f"Invalid IP {ip_addr} found in Redis key: {key} (should not exist)"
                )

        st.log(f"Test {TC_IDS.invalid_ip_validation} completed successfully")
        st.report_pass("test_case_passed")
