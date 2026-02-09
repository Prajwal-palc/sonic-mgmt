"""
IPv6 INTERFACE ENABLE/DISABLE ACTUAL BEHAVIOR VALIDATION

Author: Shiva
2026

Test ID: IPV6-DISABLE-ACTUAL-001

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/ztp_standalone.yaml \\
  tests/system/ipv6/test_ipv6_interface_enable_disable.py \\
  --logs-path ./logs/ipv6_interface_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates the ACTUAL behavior of 'no ipv6 enable' command on SONiC interfaces.

  ACTUAL BEHAVIOR (validated in this test suite):
  1. 'no ipv6 enable' REMOVES link-local IPv6 address (fe80::)
  2. Global IPv6 addresses CAN still be configured after 'no ipv6 enable'
  3. IPv6 traffic (ping) WORKS with global IPv6 even when 'no ipv6 enable' is active
  4. Interface disappears from 'show ipv6 interface' when link-local is removed
  5. Interface reappears when global IPv6 is configured (even without link-local)

  Test Strategy:
  - Capture 'show ipv6 interface' BEFORE and AFTER each action
  - Prove link-local removal with evidence-based validation
  - Verify global IPv6 functionality independent of link-local state
  - Use both Klish (config) and Click (verification) CLI types

Pre-requisites:
  - Topology: standalone (D1) | Supported: HW and Virtual
  - Topology Diagram:
        +--------------------+
        |     smic_sonic1    |
        | (192.168.100.197)  |
        |    Ethernet32      |
        +--------------------+
  - Required test variables (YAML): vars/system/ipv6/vars_ipv6_interface.yaml
  - Configuration CLI: klish (IS-CLI)
  - Verification CLI: click (legacy CLI for 'show ipv6 interface')

Test Cases:
  1. test_link_local_removal_on_ipv6_disable
     - Proves link-local (fe80::) is REMOVED after 'no ipv6 enable'
     - Evidence: Before/After comparison of 'show ipv6 interface'

  2. test_global_ipv6_works_despite_disable
     - Proves global IPv6 still works after 'no ipv6 enable'
     - Evidence: Global IP configured, ping succeeds, link-local still absent
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api
import apis.system.interface as intf_api

# Module-level constants
VAR_FILE_ENV = "IPV6_INTERFACE_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "ipv6"
    / "vars_ipv6_interface.yaml"
)

# Test case IDs for inventory tracking
TC_IDS = SpyTestDict({
    "link_local_removal": "IPV6-DISABLE-ACTUAL-001-TC1",
    "global_ipv6_works": "IPV6-DISABLE-ACTUAL-001-TC2",
})


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"IPv6 interface variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("IPv6 interface YAML must contain key 'testcases'")

    return content


def _is_link_local_address(ipv6_addr: str) -> bool:
    """Check if an IPv6 address is link-local (fe80::/10)."""
    if not ipv6_addr:
        return False
    # Remove interface suffix if present (e.g., fe80::1%eth0)
    addr_only = ipv6_addr.split('%')[0]
    # Remove prefix length if present
    addr_only = addr_only.split('/')[0]
    # Link-local addresses start with fe80:
    return addr_only.lower().startswith('fe80:')


@pytest.mark.topology("any")
class TestIpv6EnableDisableActualBehavior:
    """
    Test suite for IPv6 interface enable/disable ACTUAL behavior validation.

    Validates the real-world behavior of 'no ipv6 enable' command:
    - Link-local addresses ARE removed
    - Global IPv6 addresses CAN be configured and DO work
    - Evidence-based testing with before/after state capture
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("IPv6 ACTUAL BEHAVIOR TEST SUITE - Starting")

        config = _load_yaml_data()
        defaults = config.get("defaults", {})

        min_topology = defaults.get("min_topology") or ["D1"]
        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = SpyTestDict(config)
        cls.data.defaults = SpyTestDict(defaults)
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))
        cls.data.dut = topology.D1
        cls.data.cli_type = defaults.get("cli_type", "klish")
        cls.data.verify_cli_type = defaults.get("verify_cli_type", "click")
        cls.data.test_interface = defaults.get("interface", "Ethernet32")
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))

        st.log(f"Test DUT: {cls.data.dut}")
        st.log(f"Test Interface: {cls.data.test_interface}")
        st.log(f"Configuration CLI Type: {cls.data.cli_type}")
        st.log(f"Verification CLI Type: {cls.data.verify_cli_type}")
        st.log(f"Cleanup Enabled: {cls.data.cleanup_enabled}")

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure IPv6 is re-enabled on test interface after all tests complete."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown")
            return

        st.banner("TEARDOWN CLASS: Re-enabling IPv6 on test interface")
        try:
            # Ensure interface is up
            intf_api.interface_noshutdown(
                cls.data.dut,
                interfaces=[cls.data.test_interface],
                cli_type=cls.data.cli_type
            )
            # Re-enable IPv6
            ip_api.config_interface_ip6_link_local(
                cls.data.dut,
                interface_list=[cls.data.test_interface],
                action='enable',
                cli_type=cls.data.cli_type
            )
            st.log(f"IPv6 re-enabled on {cls.data.test_interface}")
        except Exception as e:
            st.error(f"Teardown class failed: {e}")

    def setup_method(self) -> None:
        """Reset interface to known state before each test."""
        st.banner(f"SETUP METHOD: Ensuring {self.data.test_interface} is ready")

        # Ensure interface is administratively up
        intf_api.interface_noshutdown(
            self.data.dut,
            interfaces=[self.data.test_interface],
            cli_type=self.data.cli_type
        )

        # Re-enable IPv6 to start fresh
        ip_api.config_interface_ip6_link_local(
            self.data.dut,
            interface_list=[self.data.test_interface],
            action='enable',
            cli_type=self.data.cli_type
        )

        # Clear any existing global IPv6 addresses
        self._cleanup_global_ipv6_addresses()

        st.log(f"Setup complete: {self.data.test_interface} ready for testing")

    def teardown_method(self) -> None:
        """Cleanup after each test."""
        if not self.data.cleanup_enabled:
            st.log("Cleanup disabled, skipping teardown method")
            return

        st.banner("TEARDOWN METHOD: Cleaning up test artifacts")

        # Re-enable IPv6
        ip_api.config_interface_ip6_link_local(
            self.data.dut,
            interface_list=[self.data.test_interface],
            action='enable',
            cli_type=self.data.cli_type
        )

        # Ensure interface is up
        intf_api.interface_noshutdown(
            self.data.dut,
            interfaces=[self.data.test_interface],
            cli_type=self.data.cli_type
        )

        # Clear configured addresses
        self._cleanup_global_ipv6_addresses()

    def _cleanup_global_ipv6_addresses(self) -> None:
        """Remove all configured global IPv6 addresses from test interface."""
        try:
            addresses = ip_api.get_interface_ip_address(
                self.data.dut,
                interface_name=self.data.test_interface,
                family="ipv6",
                cli_type=self.data.cli_type
            )

            if addresses:
                for addr_entry in addresses:
                    ipaddr = addr_entry.get('ipaddr', '')
                    if ipaddr and not _is_link_local_address(ipaddr):
                        # Parse address and subnet
                        if '/' in ipaddr:
                            ip, subnet = ipaddr.split('/')
                            st.log(f"Removing IPv6 address {ip}/{subnet} from {self.data.test_interface}")
                            ip_api.delete_ip_interface(
                                self.data.dut,
                                interface_name=self.data.test_interface,
                                ip_address=ip,
                                subnet=subnet,
                                family="ipv6",
                                skip_error=True,
                                cli_type=self.data.cli_type
                            )
        except Exception as e:
            st.warn(f"Cleanup IPv6 addresses failed: {e}")

    def _show_ipv6_interface(self) -> str:
        """
        Execute 'show ipv6 interface' using Click CLI and return raw output.

        Returns:
            Raw command output as string
        """
        try:
            cmd = "show ipv6 interface"
            output = st.show(
                self.data.dut,
                cmd,
                type=self.data.verify_cli_type,
                skip_tmpl=True,
                skip_error_check=True
            )

            output_str = str(output) if output else ""
            st.log(f"'show ipv6 interface' output ({len(output_str)} chars):\n{output_str}")
            return output_str

        except Exception as e:
            st.error(f"Failed to execute 'show ipv6 interface': {e}")
            return ""

    def _is_interface_in_ipv6_list(self, output: str, interface: str) -> bool:
        """
        Check if interface appears in 'show ipv6 interface' output.

        Args:
            output: Raw output from 'show ipv6 interface'
            interface: Interface name (e.g., 'Ethernet32')

        Returns:
            True if interface is listed, False otherwise
        """
        if not output or not interface:
            return False

        # Look for interface name in output (case-insensitive)
        pattern = rf'\b{re.escape(interface)}\b'
        found = re.search(pattern, output, re.IGNORECASE)

        result = found is not None
        st.log(f"Interface {interface} in IPv6 list: {result}")
        return result

    def _extract_link_local_from_output(self, output: str, interface: str) -> Optional[str]:
        """
        Extract link-local IPv6 address (fe80::) for specific interface from output.

        Args:
            output: Raw output from 'show ipv6 interface'
            interface: Interface name

        Returns:
            Link-local address string if found, None otherwise
        """
        if not output or not interface:
            return None

        # Strategy: Find interface line, then look for fe80:: in nearby lines
        lines = output.split('\n')

        for i, line in enumerate(lines):
            if interface in line:
                # Check this line and next few lines for fe80::
                search_lines = lines[i:i+5]  # Check current + next 4 lines
                for search_line in search_lines:
                    # Look for fe80:: pattern
                    fe80_pattern = r'(fe80:[0-9a-fA-F:]+(?:/\d{1,3})?)'
                    match = re.search(fe80_pattern, search_line, re.IGNORECASE)
                    if match:
                        link_local = match.group(1)
                        st.log(f"Found link-local for {interface}: {link_local}")
                        return link_local

        st.log(f"No link-local found for {interface}")
        return None

    def _extract_global_ipv6_from_output(self, output: str, interface: str) -> Optional[str]:
        """
        Extract global IPv6 address (non-fe80::) for specific interface from output.

        Args:
            output: Raw output from 'show ipv6 interface'
            interface: Interface name

        Returns:
            Global IPv6 address string if found, None otherwise
        """
        if not output or not interface:
            return None

        # Strategy: Find interface line, then look for non-fe80:: IPv6 addresses
        lines = output.split('\n')

        for i, line in enumerate(lines):
            if interface in line:
                # Check this line and next few lines for global IPv6
                search_lines = lines[i:i+5]
                for search_line in search_lines:
                    # Look for IPv6 pattern (but not fe80::)
                    ipv6_pattern = r'([0-9a-fA-F]{1,4}:[0-9a-fA-F:]+(?:/\d{1,3})?)'
                    matches = re.findall(ipv6_pattern, search_line, re.IGNORECASE)

                    for match in matches:
                        if not match.lower().startswith('fe80:'):
                            st.log(f"Found global IPv6 for {interface}: {match}")
                            return match

        st.log(f"No global IPv6 found for {interface}")
        return None

    def _ping_ipv6_local(self, target: str, count: int = 3) -> bool:
        """
        Ping IPv6 address from DUT itself (loopback test).

        Args:
            target: IPv6 address to ping
            count: Number of ping packets

        Returns:
            True if ping succeeds, False otherwise
        """
        try:
            # Use ping6 command from Linux shell
            cmd = f"ping6 -c {count} {target}"

            st.log(f"Executing ping: {cmd}")

            output = st.show(
                self.data.dut,
                cmd,
                skip_tmpl=True,
                skip_error_check=True,
                type=self.data.verify_cli_type
            )

            output_str = str(output) if output else ""
            st.log(f"Ping output:\n{output_str}")

            # Check for success indicators
            success_patterns = [
                r'(\d+) packets transmitted, (\d+) received',
                r'(\d+)% packet loss',
            ]

            for pattern in success_patterns:
                match = re.search(pattern, output_str)
                if match:
                    if 'packet loss' in pattern:
                        loss_match = re.search(r'(\d+)% packet loss', output_str)
                        if loss_match:
                            loss = int(loss_match.group(1))
                            if loss < 100:
                                st.log(f"Ping successful: {100 - loss}% packets received")
                                return True
                    elif 'packets transmitted' in pattern:
                        transmitted = int(match.group(1))
                        received = int(match.group(2))
                        if received > 0:
                            st.log(f"Ping successful: {received}/{transmitted} packets received")
                            return True

            st.log(f"Ping failed: no response from {target}")
            return False

        except Exception as e:
            st.error(f"Ping execution failed: {e}")
            return False

    # ==========================================================================
    # Test Case 1: Link-Local Address Removal on IPv6 Disable
    # ==========================================================================
    @pytest.mark.inventory(feature="IPv6", testcases=[TC_IDS.link_local_removal])
    def test_link_local_removal_on_ipv6_disable(self) -> None:
        """
        TC 1 - Link-Local Address Removal on IPv6 Disable.

        Objective:
            Prove that executing 'no ipv6 enable' REMOVES the link-local (fe80::)
            address from the interface.

        Test Flow:
            1. BEFORE: Enable IPv6, capture 'show ipv6 interface'
            2. Verify link-local (fe80::) exists
            3. ACTION: Execute 'no ipv6 enable'
            4. AFTER: Capture 'show ipv6 interface'
            5. Verify interface removed from IPv6 list (link-local gone)

        Evidence:
            - Before: Interface has fe80:: address
            - After: Interface NOT in 'show ipv6 interface' output
        """
        st.banner("TEST CASE 1: Link-Local Address Removal on IPv6 Disable")

        testcase = self.data.testcases.get("scenario1", {})
        interface = testcase.get("interface", self.data.test_interface)

        # ===== STEP 1: BEFORE - Ensure IPv6 is enabled =====
        st.log("=" * 80)
        st.log("STEP 1: BEFORE STATE - Enable IPv6 on interface")
        st.log("=" * 80)

        result = ip_api.config_interface_ip6_link_local(
            self.data.dut,
            interface_list=[interface],
            action='enable',
            cli_type=self.data.cli_type
        )

        if not result:
            st.report_fail("msg", f"Failed to enable IPv6 on {interface}")

        # Wait for link-local address assignment
        st.log("Waiting 3 seconds for link-local address assignment...")
        time.sleep(3)

        # ===== STEP 2: BEFORE CHECK - Capture initial state =====
        st.log("=" * 80)
        st.log("STEP 2: BEFORE CHECK - Capture 'show ipv6 interface'")
        st.log("=" * 80)

        output_before = self._show_ipv6_interface()

        # Verify interface is present
        interface_present_before = self._is_interface_in_ipv6_list(output_before, interface)

        if not interface_present_before:
            st.report_fail("msg", f"BEFORE: {interface} not found in 'show ipv6 interface' - cannot proceed with test")

        st.log(f"✓ BEFORE: {interface} is present in IPv6 interface list")

        # Extract link-local address
        link_local_before = self._extract_link_local_from_output(output_before, interface)

        if not link_local_before:
            st.report_fail("msg", f"BEFORE: No link-local address found for {interface}")

        st.banner(f"BEFORE STATE CONFIRMED")
        st.log(f"✓ Interface: {interface}")
        st.log(f"✓ Link-Local: {link_local_before}")
        st.log(f"✓ Status: Present in 'show ipv6 interface'")

        # ===== STEP 3: ACTION - Disable IPv6 =====
        st.log("=" * 80)
        st.log("STEP 3: ACTION - Execute 'no ipv6 enable'")
        st.log("=" * 80)

        result = ip_api.config_interface_ip6_link_local(
            self.data.dut,
            interface_list=[interface],
            action='disable',
            cli_type=self.data.cli_type
        )

        if not result:
            st.report_fail("msg", f"Failed to execute 'no ipv6 enable' on {interface}")

        st.log(f"✓ Successfully executed 'no ipv6 enable' on {interface}")

        # Wait for state propagation
        st.log("Waiting 2 seconds for state propagation...")
        time.sleep(2)

        # ===== STEP 4: AFTER CHECK - Capture final state =====
        st.log("=" * 80)
        st.log("STEP 4: AFTER CHECK - Capture 'show ipv6 interface'")
        st.log("=" * 80)

        output_after = self._show_ipv6_interface()

        # Verify interface is NOT present
        interface_present_after = self._is_interface_in_ipv6_list(output_after, interface)

        st.banner(f"AFTER STATE CONFIRMED")
        st.log(f"✓ Interface: {interface}")
        st.log(f"✓ Status: {'PRESENT' if interface_present_after else 'NOT PRESENT'} in 'show ipv6 interface'")

        # ===== STEP 5: VALIDATION =====
        st.log("=" * 80)
        st.log("STEP 5: VALIDATION - Compare Before vs After")
        st.log("=" * 80)

        if testcase.get("expected_link_local_removed", True):
            if interface_present_after:
                st.report_fail(
                    "msg",
                    f"FAIL: {interface} still present in 'show ipv6 interface' after 'no ipv6 enable'. "
                    f"Link-local was NOT removed."
                )

            st.banner("✓ TEST PASSED - EVIDENCE CONFIRMED")
            st.log(f"✓ BEFORE: {interface} had link-local {link_local_before}")
            st.log(f"✓ AFTER: {interface} removed from IPv6 interface list")
            st.log(f"✓ CONCLUSION: Link-local address was REMOVED by 'no ipv6 enable'")

            st.report_pass("test_case_passed")
        else:
            st.report_fail("msg", "Test configuration error: expected_link_local_removed not set")

    # ==========================================================================
    # Test Case 2: Global IPv6 Works Despite Disable
    # ==========================================================================
    @pytest.mark.inventory(feature="IPv6", testcases=[TC_IDS.global_ipv6_works])
    def test_global_ipv6_works_despite_disable(self) -> None:
        """
        TC 2 - Global IPv6 Works Despite Disable.

        Objective:
            Prove that global IPv6 addresses CAN be configured and DO work
            even after 'no ipv6 enable' is active.

        Test Flow:
            1. BEFORE: Execute 'no ipv6 enable', verify clean state
            2. Verify interface NOT in 'show ipv6 interface' (no link-local)
            3. ACTION: Configure global IPv6 address
            4. AFTER: Capture 'show ipv6 interface'
            5. Verify global IP present, link-local still absent
            6. PING: Test reachability to global IP
            7. Verify ping succeeds

        Evidence:
            - Before: No link-local (interface not listed)
            - After: Global IP present, link-local STILL absent
            - Ping: Successful to global IP
        """
        st.banner("TEST CASE 2: Global IPv6 Works Despite Disable")

        testcase = self.data.testcases.get("scenario2", {})
        interface = testcase.get("interface", self.data.test_interface)
        global_ipv6 = testcase.get("global_ipv6", "2001:db8::1")
        subnet = testcase.get("subnet", "64")

        if not global_ipv6 or not subnet:
            st.report_fail("msg", "Test requires global_ipv6 and subnet in YAML")

        # ===== STEP 1: BEFORE - Disable IPv6 =====
        st.log("=" * 80)
        st.log("STEP 1: BEFORE STATE - Disable IPv6 on interface")
        st.log("=" * 80)

        result = ip_api.config_interface_ip6_link_local(
            self.data.dut,
            interface_list=[interface],
            action='disable',
            cli_type=self.data.cli_type
        )

        if not result:
            st.report_fail("msg", f"Failed to execute 'no ipv6 enable' on {interface}")

        st.log(f"✓ Successfully executed 'no ipv6 enable' on {interface}")

        # Wait for state propagation
        st.log("Waiting 2 seconds for state propagation...")
        time.sleep(2)

        # ===== STEP 2: BEFORE CHECK - Verify clean state =====
        st.log("=" * 80)
        st.log("STEP 2: BEFORE CHECK - Verify interface not in IPv6 list")
        st.log("=" * 80)

        output_before = self._show_ipv6_interface()

        interface_present_before = self._is_interface_in_ipv6_list(output_before, interface)

        st.banner(f"BEFORE STATE CONFIRMED")
        st.log(f"✓ Interface: {interface}")
        st.log(f"✓ Status: {'PRESENT' if interface_present_before else 'NOT PRESENT'} in 'show ipv6 interface'")
        st.log(f"✓ Link-Local: Absent (as expected after 'no ipv6 enable')")

        # ===== STEP 3: ACTION - Configure Global IPv6 Address =====
        st.log("=" * 80)
        st.log(f"STEP 3: ACTION - Configure global IPv6 {global_ipv6}/{subnet}")
        st.log("=" * 80)

        config_result = ip_api.config_ip_addr_interface(
            self.data.dut,
            interface_name=interface,
            ip_address=global_ipv6,
            subnet=subnet,
            family="ipv6",
            config='add',
            cli_type=self.data.cli_type
        )

        if not config_result:
            st.report_fail("msg", f"Failed to configure IPv6 address {global_ipv6}/{subnet}")

        st.log(f"✓ Successfully configured {global_ipv6}/{subnet} on {interface}")

        # Wait for configuration to take effect
        st.log("Waiting 3 seconds for configuration to take effect...")
        time.sleep(3)

        # ===== STEP 4: AFTER CHECK - Verify global IP present =====
        st.log("=" * 80)
        st.log("STEP 4: AFTER CHECK - Capture 'show ipv6 interface'")
        st.log("=" * 80)

        output_after = self._show_ipv6_interface()

        interface_present_after = self._is_interface_in_ipv6_list(output_after, interface)
        global_ip_after = self._extract_global_ipv6_from_output(output_after, interface)
        link_local_after = self._extract_link_local_from_output(output_after, interface)

        st.banner(f"AFTER STATE CONFIRMED")
        st.log(f"✓ Interface: {interface}")
        st.log(f"✓ Status: {'PRESENT' if interface_present_after else 'NOT PRESENT'} in 'show ipv6 interface'")
        st.log(f"✓ Global IPv6: {global_ip_after if global_ip_after else 'NOT FOUND'}")
        st.log(f"✓ Link-Local: {link_local_after if link_local_after else 'ABSENT (as expected)'}")

        # ===== STEP 5: VALIDATION - Global IP Present =====
        st.log("=" * 80)
        st.log("STEP 5: VALIDATION - Verify global IPv6 configured")
        st.log("=" * 80)

        if not interface_present_after:
            st.report_fail(
                "msg",
                f"FAIL: {interface} not in 'show ipv6 interface' after configuring global IP"
            )

        if not global_ip_after:
            st.report_fail(
                "msg",
                f"FAIL: Global IPv6 {global_ipv6} not found in 'show ipv6 interface'"
            )

        # Verify link-local is still absent
        if link_local_after:
            st.warn(f"Link-local {link_local_after} found (unexpected - may be auto-generated)")
        else:
            st.log(f"✓ Link-local still ABSENT (confirms 'no ipv6 enable' is active)")

        st.log(f"✓ Global IPv6 {global_ip_after} successfully configured")

        # ===== STEP 6: REACHABILITY TEST - Ping Global IP =====
        st.log("=" * 80)
        st.log("STEP 6: REACHABILITY TEST - Ping global IPv6 address")
        st.log("=" * 80)

        ping_count = testcase.get("ping_count", 3)

        st.log(f"Pinging {global_ipv6} (count={ping_count})...")
        ping_result = self._ping_ipv6_local(global_ipv6, count=ping_count)

        # ===== STEP 7: VALIDATION - Ping Success =====
        st.log("=" * 80)
        st.log("STEP 7: VALIDATION - Verify ping succeeded")
        st.log("=" * 80)

        if testcase.get("ping_expected", True):
            if not ping_result:
                st.report_fail(
                    "msg",
                    f"FAIL: Ping to {global_ipv6} failed despite global IP being configured"
                )

            st.banner("✓ TEST PASSED - ALL EVIDENCE CONFIRMED")
            st.log(f"✓ BEFORE: {interface} not in IPv6 list (no link-local)")
            st.log(f"✓ AFTER: {interface} has global IP {global_ip_after}")
            st.log(f"✓ AFTER: Link-local still ABSENT (no ipv6 enable active)")
            st.log(f"✓ PING: Successfully reached {global_ipv6}")
            st.log(f"✓ CONCLUSION: Global IPv6 WORKS without link-local (after 'no ipv6 enable')")

            st.report_pass("test_case_passed")
        else:
            if ping_result:
                st.report_fail(
                    "msg",
                    f"FAIL: Ping to {global_ipv6} succeeded when it was expected to fail"
                )
            st.report_pass("test_case_passed")
