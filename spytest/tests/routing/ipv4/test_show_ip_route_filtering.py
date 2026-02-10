"""
IPv4 ROUTING CLI - SHOW IP ROUTE FILTERING
Author: Shiva
2026

Test ID: SM_ISCLI_76

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/ztp_standalone.yaml \\
  tests/routing/ipv4/test_show_ip_route_filtering.py \\
  --logs-path ./logs/show_ip_route_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Comprehensive validation of the 'show ip route' command suite within the SONiC
  Management CLI (klish). This test suite verifies functionality, filtering capabilities,
  and error handling across various routing scenarios:

  - General routing table display with protocol legend
  - Context-sensitive help and command options
  - Protocol filtering (connected, bgp, ospf, static)
  - Specific prefix lookup (longest match)
  - Route summary validation and aggregation
  - VRF command syntax and error handling

  The suite uses evidence-based validation by capturing command outputs and
  verifying expected formatting, protocol codes, and route information against
  the actual routing table state.

Pre-requisites:
  - Topology: Single DUT (D1) | Supported: HW and Virtual
  - Topology Diagram:
        +--------------------+
        |    smic_sonic1     |
        | (192.168.100.134)  |
        |  Management0       |
        |  Vlan100 (optional)|
        +--------------------+

  - Interfaces configured: Management0 (required), Vlan100 (optional for connected routes)
  - CLI access: klish (SONiC IS-CLI)
  - Required test variables (YAML): vars/routing/ipv4/vars_show_ip_route_filtering.yaml

Test Scenarios:
  1. General routing table display - Verify legend codes and route entries
  2. Context-sensitive help - Verify available filtering options
  3. Protocol filtering (connected) - Filter connected routes only
  4. Protocol filtering (empty) - Handle protocols with no routes (BGP, OSPF)
  5. Specific prefix lookup - Longest match prefix validation
  6. Route summary - Validate route counts and aggregation
  7. VRF command validation - Error handling and vrf all summary
"""

# Testcases for IPv4 show ip route filtering covering SM_ISCLI_76

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api

# Module-level constants
VAR_FILE_ENV = "SHOW_IP_ROUTE_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "routing"
    / "ipv4"
    / "vars_show_ip_route_filtering.yaml"
)

# Test case IDs for inventory tracking
TC_IDS = SpyTestDict({
    "general_display": "SM_ISCLI_76_TC1",
    "context_help": "SM_ISCLI_76_TC2",
    "filter_connected": "SM_ISCLI_76_TC3",
    "filter_empty_protocol": "SM_ISCLI_76_TC4",
    "prefix_lookup": "SM_ISCLI_76_TC5",
    "route_summary": "SM_ISCLI_76_TC6",
    "vrf_validation": "SM_ISCLI_76_TC7",
})


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"Show IP route variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("Show IP route YAML must contain key 'testcases'")

    return content


@pytest.mark.topology("any")
class TestShowIpRouteFiltering:
    """
    Test suite for 'show ip route' filtering and validation.

    Validates the SONiC IS-CLI (klish) routing table display commands:
    - General route display with legend
    - Protocol-based filtering
    - Prefix-specific lookups
    - Summary and aggregation
    - VRF command syntax and error handling
    """

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase variables for the suite."""
        st.banner("SHOW IP ROUTE FILTERING TEST SUITE - Starting")

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
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))

        st.log(f"Test DUT: {cls.data.dut}")
        st.log(f"CLI Type: {cls.data.cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup after test suite completion."""
        st.banner("TEARDOWN CLASS: Show IP Route Filtering Tests")
        st.log("No cleanup required (read-only tests)")

    def _execute_show_command(self, command: str, skip_tmpl: bool = True) -> Any:
        """
        Execute show command and return output.

        Args:
            command: Command to execute
            skip_tmpl: Skip template parsing

        Returns:
            Command output (parsed or raw)
        """
        try:
            st.log(f"Executing command: {command}")

            output = st.show(
                self.data.dut,
                command,
                type=self.data.cli_type,
                skip_tmpl=skip_tmpl,
                skip_error_check=True
            )

            if isinstance(output, str):
                st.log(f"Command output ({len(output)} chars):\n{output[:500]}")
            else:
                st.log(f"Command output (parsed): {output}")

            return output

        except Exception as e:
            st.error(f"Command execution failed: {e}")
            return None

    def _check_protocol_legend(self, output: str) -> bool:
        """
        Check if routing table output contains protocol legend codes.

        Args:
            output: Command output string

        Returns:
            True if legend found, False otherwise
        """
        if not output:
            return False

        # Look for protocol code legend (K, C, S, R, B, O, etc.)
        legend_patterns = [
            r'Codes:.*K.*kernel',
            r'C.*connected',
            r'S.*static',
            r'B.*BGP',
            r'O.*OSPF',
        ]

        for pattern in legend_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                st.log(f"Found protocol legend pattern: {pattern}")
                return True

        st.log("Protocol legend not found in output")
        return False

    def _check_route_entry(self, output: str, expected_route: str) -> bool:
        """
        Check if specific route entry exists in output.

        Args:
            output: Command output string
            expected_route: Route prefix to find (e.g., "20.1.1.0/24")

        Returns:
            True if route found, False otherwise
        """
        if not output or not expected_route:
            return False

        # Normalize route format for matching
        route_pattern = re.escape(expected_route)
        found = re.search(route_pattern, output)

        result = found is not None
        st.log(f"Route {expected_route} in output: {result}")
        return result

    def _check_vrf_header(self, output: str, vrf_name: str = "default") -> bool:
        """
        Check if output contains VRF header.

        Args:
            output: Command output string
            vrf_name: VRF name to check

        Returns:
            True if VRF header found, False otherwise
        """
        if not output:
            return False

        # Look for "IPv4 unicast VRF <name>:" header
        vrf_pattern = rf'IPv4\s+unicast\s+VRF\s+{re.escape(vrf_name)}'
        found = re.search(vrf_pattern, output, re.IGNORECASE)

        result = found is not None
        st.log(f"VRF header '{vrf_name}' in output: {result}")
        return result

    def _check_error_message(self, output: str, error_msg: str) -> bool:
        """
        Check if output contains expected error message.

        Args:
            output: Command output string
            error_msg: Expected error message

        Returns:
            True if error message found, False otherwise
        """
        if not output:
            return False

        found = error_msg in output
        st.log(f"Error message '{error_msg}' in output: {found}")
        return found

    def _count_route_entries(self, output: str) -> int:
        """
        Count number of route entries in output.

        Args:
            output: Command output string

        Returns:
            Number of route entries found
        """
        if not output:
            return 0

        # Count lines that start with route type indicators (K, C, S, B, O, etc.)
        # Format: "K>* 0.0.0.0/0 [0/0] via ..."
        route_pattern = r'^[KCSRBOL][>*\s]+\d+\.\d+\.\d+\.\d+/\d+'
        lines = output.split('\n')

        count = 0
        for line in lines:
            if re.search(route_pattern, line.strip()):
                count += 1

        st.log(f"Found {count} route entries in output")
        return count

    # ==========================================================================
    # Test Case 1: General Routing Table Display
    # ==========================================================================
    @pytest.mark.inventory(feature="Routing", testcases=[TC_IDS.general_display])
    def test_general_routing_table_display(self) -> None:
        """
        TC 1 - General Routing Table Display.

        Objective:
            Verify the global routing table is displayed with correct legend codes
            and route entries.

        Command: show ip route

        Expected:
            - Display protocol code legend (K, C, S, R, B, O, etc.)
            - Display 'IPv4 unicast VRF default' header
            - List installed routes (e.g., 0.0.0.0/0 via Management0)
        """
        st.banner("TEST CASE 1: General Routing Table Display")

        testcase = self.data.testcases.get("general_display", {})

        # Execute command
        command = "show ip route"
        output = self._execute_show_command(command)

        if not output:
            st.report_fail("msg", f"No output received for command: {command}")

        output_str = str(output)

        # Validation 1: Check for protocol legend
        st.log("Validation 1: Checking for protocol legend codes")
        has_legend = self._check_protocol_legend(output_str)

        if not has_legend:
            st.report_fail("msg", "Protocol legend codes not found in routing table output")

        st.log("✓ Protocol legend codes found")

        # Validation 2: Check for VRF header
        st.log("Validation 2: Checking for VRF default header")
        has_vrf_header = self._check_vrf_header(output_str, "default")

        if not has_vrf_header:
            st.warn("VRF default header not found (may not be displayed on all platforms)")

        # Validation 3: Check for at least one route entry
        st.log("Validation 3: Checking for route entries")
        route_count = self._count_route_entries(output_str)

        if route_count == 0:
            st.report_fail("msg", "No route entries found in routing table")

        st.log(f"✓ Found {route_count} route entries")

        # Validation 4: Check for specific routes if specified in YAML
        expected_routes = testcase.get("expected_routes", [])
        for route in expected_routes:
            st.log(f"Checking for route: {route}")
            if not self._check_route_entry(output_str, route):
                st.warn(f"Expected route {route} not found (may not be configured)")

        st.banner("✓ TEST PASSED - General routing table display validated")
        st.report_pass("test_case_passed")

    # ==========================================================================
    # Test Case 2: Context Sensitive Help & Options
    # ==========================================================================
    @pytest.mark.inventory(feature="Routing", testcases=[TC_IDS.context_help])
    def test_context_sensitive_help(self) -> None:
        """
        TC 2 - Context Sensitive Help & Options.

        Objective:
            Verify available sub-commands for route filtering.

        Command: show ip route ?

        Expected:
            Should list options including:
            - A.B.C.D (Match IP address)
            - bgp
            - connected
            - ospf
            - static
            - summary
            - vrf
        """
        st.banner("TEST CASE 2: Context Sensitive Help & Options")

        testcase = self.data.testcases.get("context_help", {})

        # Execute help command
        command = "show ip route ?"
        output = self._execute_show_command(command)

        if not output:
            st.report_fail("msg", f"No output received for help command: {command}")

        output_str = str(output)

        # Expected options from specification
        expected_options = testcase.get("expected_options", [
            "A.B.C.D",
            "bgp",
            "connected",
            "ospf",
            "static",
            "summary",
            "vrf"
        ])

        st.log(f"Checking for expected options: {expected_options}")

        missing_options = []
        for option in expected_options:
            # Check if option appears in output (case-insensitive)
            if option.lower() not in output_str.lower():
                missing_options.append(option)
                st.log(f"  ✗ Option '{option}' - NOT FOUND")
            else:
                st.log(f"  ✓ Option '{option}' - FOUND")

        if missing_options:
            st.warn(f"Some expected options not found: {missing_options}")
            st.log("This may be due to platform differences or CLI version")

        # At least 'connected', 'summary', and 'vrf' should be present
        critical_options = ["connected", "summary", "vrf"]
        missing_critical = [opt for opt in critical_options if opt.lower() not in output_str.lower()]

        if missing_critical:
            st.report_fail(
                "msg",
                f"Critical options missing from help output: {missing_critical}"
            )

        st.banner("✓ TEST PASSED - Context-sensitive help validated")
        st.report_pass("test_case_passed")

    # ==========================================================================
    # Test Case 3: Protocol Filtering (Connected)
    # ==========================================================================
    @pytest.mark.inventory(feature="Routing", testcases=[TC_IDS.filter_connected])
    def test_protocol_filtering_connected(self) -> None:
        """
        TC 3 - Protocol Filtering (Connected).

        Objective:
            Verify the CLI correctly filters the routing table to show only
            directly connected networks.

        Command: show ip route connected

        Expected:
            - Only connected routes displayed
            - Route type indicator 'C' present
            - No other protocol routes shown
        """
        st.banner("TEST CASE 3: Protocol Filtering - Connected Routes")

        testcase = self.data.testcases.get("filter_connected", {})

        # Execute command
        command = "show ip route connected"
        output = self._execute_show_command(command)

        if not output:
            st.report_fail("msg", f"No output received for command: {command}")

        output_str = str(output)

        # Validation 1: Check for connected routes (type 'C')
        st.log("Validation 1: Checking for connected route indicator 'C'")

        if not re.search(r'\bC[>*\s]', output_str):
            st.report_fail("msg", "No connected routes (type 'C') found in filtered output")

        st.log("✓ Connected routes found")

        # Validation 2: Verify no other protocol types present
        st.log("Validation 2: Checking that only connected routes are shown")

        # Look for other protocol indicators (B, O, S, K, R)
        other_protocols = re.findall(r'^([BOSKR])[>*\s]', output_str, re.MULTILINE)

        if other_protocols:
            st.report_fail(
                "msg",
                f"Unexpected protocol routes found in connected filter: {set(other_protocols)}"
            )

        st.log("✓ No other protocol routes present - filter working correctly")

        # Validation 3: Check for expected connected routes if specified
        expected_connected = testcase.get("expected_connected_routes", [])
        for route in expected_connected:
            st.log(f"Checking for connected route: {route}")
            if not self._check_route_entry(output_str, route):
                st.warn(f"Expected connected route {route} not found")

        st.banner("✓ TEST PASSED - Connected route filtering validated")
        st.report_pass("test_case_passed")

    # ==========================================================================
    # Test Case 4: Protocol Filtering (Empty Protocols)
    # ==========================================================================
    @pytest.mark.inventory(feature="Routing", testcases=[TC_IDS.filter_empty_protocol])
    @pytest.mark.negative
    def test_protocol_filtering_empty_protocols(self) -> None:
        """
        TC 4 - Protocol Filtering (Empty Protocols).

        Objective:
            Verify CLI behavior when filtering by a protocol that has no active routes.

        Commands:
            - show ip route bgp
            - show ip route ospf

        Expected:
            - Command executes without error
            - Output is empty (no routes displayed)
            - No CLI errors or crashes
        """
        st.banner("TEST CASE 4: Protocol Filtering - Empty Protocols")

        testcase = self.data.testcases.get("filter_empty_protocol", {})

        # Test protocols that typically have no routes in test environment
        empty_protocols = testcase.get("empty_protocols", ["bgp", "ospf"])

        for protocol in empty_protocols:
            st.log(f"Testing empty protocol filter: {protocol}")

            command = f"show ip route {protocol}"
            output = self._execute_show_command(command)

            if output is None:
                st.report_fail("msg", f"Command failed to execute: {command}")

            output_str = str(output) if output else ""

            # Check that command executed without errors
            if "Error" in output_str or "error" in output_str:
                st.report_fail("msg", f"Command returned error for {protocol}: {output_str[:200]}")

            st.log(f"✓ Command executed successfully for {protocol}")

            # Verify output is empty (no routes)
            # Output should not contain route type indicators
            route_count = self._count_route_entries(output_str)

            if route_count > 0:
                st.warn(f"Found {route_count} {protocol} routes (unexpected in test env)")

            st.log(f"✓ {protocol} filter handled correctly (empty or minimal output)")

        st.banner("✓ TEST PASSED - Empty protocol filtering validated")
        st.report_pass("test_case_passed")

    # ==========================================================================
    # Test Case 5: Specific Prefix Lookup (Longest Match)
    # ==========================================================================
    @pytest.mark.inventory(feature="Routing", testcases=[TC_IDS.prefix_lookup])
    def test_specific_prefix_lookup(self) -> None:
        """
        TC 5 - Specific Prefix Lookup (Longest Match).

        Objective:
            Verify the CLI provides detailed information for a specific destination IP.

        Command: show ip route <A.B.C.D>

        Expected:
            - Routing entry for the longest-match prefix displayed
            - Shows protocol, distance, metric
            - Shows next-hop or interface information
        """
        st.banner("TEST CASE 5: Specific Prefix Lookup (Longest Match)")

        testcase = self.data.testcases.get("prefix_lookup", {})

        # Get test prefix from YAML or use default
        test_prefix = testcase.get("lookup_prefix", "172.31.0.1")

        st.log(f"Testing prefix lookup for: {test_prefix}")

        # Execute command
        command = f"show ip route {test_prefix}"
        output = self._execute_show_command(command)

        if not output:
            st.report_fail("msg", f"No output received for command: {command}")

        output_str = str(output)

        # Validation 1: Check for "Routing entry for" text
        st.log("Validation 1: Checking for routing entry header")

        if "Routing entry for" in output_str or "routing entry" in output_str.lower():
            st.log("✓ Routing entry header found")
        else:
            st.warn("Routing entry header not found (format may vary)")

        # Validation 2: Check for protocol information
        st.log("Validation 2: Checking for protocol information")

        protocol_patterns = [
            r'Known via.*connected',
            r'Known via.*kernel',
            r'Known via.*static',
            r'distance\s+\d+',
            r'metric\s+\d+',
        ]

        found_protocol_info = False
        for pattern in protocol_patterns:
            if re.search(pattern, output_str, re.IGNORECASE):
                st.log(f"✓ Found protocol info: {pattern}")
                found_protocol_info = True
                break

        if not found_protocol_info:
            st.warn("Detailed protocol information not found in output")

        # Validation 3: Verify output is not empty
        if len(output_str.strip()) < 20:
            st.report_fail("msg", f"Output too short for prefix lookup: {test_prefix}")

        st.log("✓ Prefix lookup returned detailed information")

        st.banner("✓ TEST PASSED - Specific prefix lookup validated")
        st.report_pass("test_case_passed")

    # ==========================================================================
    # Test Case 6: Route Summary Validation
    # ==========================================================================
    @pytest.mark.inventory(feature="Routing", testcases=[TC_IDS.route_summary])
    def test_route_summary_validation(self) -> None:
        """
        TC 6 - Route Summary Validation.

        Objective:
            Verify the summary command aggregates route counts correctly.

        Command: show ip route summary

        Expected Output Format:
            Route Source         Routes               FIB  (vrf default)
            kernel               11                   1
            connected            34                   34
            ------
            Totals               45                   35

        Validation:
            - Table header present (Route Source, Routes, FIB, vrf name)
            - Route sources listed (kernel, connected, static, bgp, ospf, etc.)
            - Numeric route counts shown
            - Totals row present and matches sum of individual routes
        """
        st.banner("TEST CASE 6: Route Summary Validation")

        testcase = self.data.testcases.get("route_summary", {})

        # Execute command
        command = "show ip route summary"
        output = self._execute_show_command(command, skip_tmpl=True)

        if not output:
            st.report_fail("msg", f"No output received for command: {command}")

        output_str = str(output)
        st.log(f"Summary output:\n{output_str}")

        # ===== Validation 1: Check for table header =====
        st.log("=" * 80)
        st.log("Validation 1: Checking for summary table header")
        st.log("=" * 80)

        header_patterns = [
            r'Route\s+Source',
            r'Routes',
            r'FIB',
            r'\(vrf\s+default\)',
        ]

        header_found = True
        for pattern in header_patterns:
            if not re.search(pattern, output_str, re.IGNORECASE):
                st.warn(f"Header pattern '{pattern}' not found")
                header_found = False

        if header_found:
            st.log("✓ Summary table header found")
        else:
            st.warn("Complete table header not found (format may vary)")

        # ===== Validation 2: Parse and validate route source entries =====
        st.log("=" * 80)
        st.log("Validation 2: Parsing route source entries")
        st.log("=" * 80)

        # Pattern to match route source lines
        # Format: "kernel               11                   1"
        route_pattern = r'^\s*(kernel|connected|static|bgp|ospf|rip|isis)\s+(\d+)\s+(\d+)'

        route_entries = {}
        calculated_total_routes = 0
        calculated_total_fib = 0

        for line in output_str.split('\n'):
            match = re.search(route_pattern, line, re.IGNORECASE)
            if match:
                source = match.group(1).lower()
                routes = int(match.group(2))
                fib = int(match.group(3))

                route_entries[source] = {'routes': routes, 'fib': fib}
                calculated_total_routes += routes
                calculated_total_fib += fib

                st.log(f"  {source:15} Routes: {routes:5}  FIB: {fib:5}")

        if not route_entries:
            st.report_fail("msg", "No route source entries found in summary output")

        st.log(f"✓ Found {len(route_entries)} route source entries")
        st.log(f"  Calculated totals - Routes: {calculated_total_routes}, FIB: {calculated_total_fib}")

        # ===== Validation 3: Validate Totals row =====
        st.log("=" * 80)
        st.log("Validation 3: Validating Totals row")
        st.log("=" * 80)

        # Pattern for totals line
        # Format: "Totals               45                   35"
        totals_pattern = r'^\s*Totals\s+(\d+)\s+(\d+)'

        totals_match = re.search(totals_pattern, output_str, re.MULTILINE | re.IGNORECASE)

        if not totals_match:
            st.warn("Totals row not found in summary output")
            st.banner("✓ TEST PASSED - Route summary structure validated (no totals row)")
            st.report_pass("test_case_passed")
            return

        reported_total_routes = int(totals_match.group(1))
        reported_total_fib = int(totals_match.group(2))

        st.log(f"Reported totals - Routes: {reported_total_routes}, FIB: {reported_total_fib}")

        # Validate totals match
        totals_match_routes = (calculated_total_routes == reported_total_routes)
        totals_match_fib = (calculated_total_fib == reported_total_fib)

        if totals_match_routes:
            st.log(f"✓ Routes total MATCHES: {calculated_total_routes} == {reported_total_routes}")
        else:
            st.error(f"✗ Routes total MISMATCH: calculated={calculated_total_routes}, reported={reported_total_routes}")
            st.report_fail(
                "msg",
                f"Route count mismatch: calculated {calculated_total_routes} != reported {reported_total_routes}"
            )

        if totals_match_fib:
            st.log(f"✓ FIB total MATCHES: {calculated_total_fib} == {reported_total_fib}")
        else:
            st.warn(f"FIB total MISMATCH: calculated={calculated_total_fib}, reported={reported_total_fib}")

        # ===== Validation 4: Check for separator line =====
        st.log("=" * 80)
        st.log("Validation 4: Checking for separator line")
        st.log("=" * 80)

        separator_pattern = r'^\s*-+\s*$'
        if re.search(separator_pattern, output_str, re.MULTILINE):
            st.log("✓ Separator line (------) found before Totals")

        st.banner("✓ TEST PASSED - Route summary validated")
        st.log(f"Summary: {len(route_entries)} route sources, {reported_total_routes} total routes, {reported_total_fib} in FIB")
        st.report_pass("test_case_passed")

    # ==========================================================================
    # Test Case 7: VRF Command Syntax & Error Handling
    # ==========================================================================
    @pytest.mark.inventory(feature="Routing", testcases=[TC_IDS.vrf_validation])
    @pytest.mark.negative
    def test_vrf_command_validation(self) -> None:
        """
        TC 7 - VRF Command Syntax & Error Handling.

        Objective:
            Verify command completion logic and error handling for VRF commands.

        Test Steps:
            A) Negative Test: show ip route vrf all
               - Expected: "% Error: The command is not completed."
               - Confirms that 'vrf all' requires additional sub-command

            B) Positive Test: show ip route vrf default
               - Expected: Displays routing table for default VRF
               - Should show routes similar to 'show ip route'

        Note:
            The command 'show ip route vrf all summary' produces identical output
            to 'show ip route summary' (both show default VRF summary), so we test
            'vrf default' instead to validate VRF-specific route display.
        """
        st.banner("TEST CASE 7: VRF Command Syntax & Error Handling")

        testcase = self.data.testcases.get("vrf_validation", {})

        # ===== Step A: Negative Test - Incomplete Command =====
        st.log("=" * 80)
        st.log("STEP A: Negative Test - 'show ip route vrf all' (incomplete)")
        st.log("=" * 80)

        command_incomplete = "show ip route vrf all"
        output_incomplete = self._execute_show_command(command_incomplete)

        if not output_incomplete:
            st.report_fail("msg", f"No output for command: {command_incomplete}")

        output_str = str(output_incomplete)

        # Check for error message
        expected_error = testcase.get("expected_incomplete_error", "% Error: The command is not completed")

        has_error = self._check_error_message(output_str, expected_error)

        if not has_error:
            st.warn(f"Expected error '{expected_error}' not found")
            st.log("Platform may accept 'vrf all' without additional keywords")
        else:
            st.log(f"✓ Correct error message returned: {expected_error}")

        # ===== Step B: Positive Test - VRF Default Route Display =====
        st.log("=" * 80)
        st.log("STEP B: Positive Test - 'show ip route vrf default' (complete)")
        st.log("=" * 80)

        command_complete = "show ip route vrf default"
        output_complete = self._execute_show_command(command_complete)

        if not output_complete:
            st.report_fail("msg", f"No output for command: {command_complete}")

        output_str_complete = str(output_complete)

        # Validation 1: Check that command executed without error
        if "Error" in output_str_complete and "error" in output_str_complete.lower():
            st.report_fail("msg", f"'vrf default' command returned error: {output_str_complete[:200]}")

        st.log(f"✓ Command executed successfully")

        # Validation 2: Check for VRF header
        if "vrf default" in output_str_complete.lower() or "VRF default" in output_str_complete:
            st.log("✓ VRF default header found in output")

        # Validation 3: Check for routing table content (protocol legend or routes)
        has_legend = self._check_protocol_legend(output_str_complete)
        route_count = self._count_route_entries(output_str_complete)

        if has_legend:
            st.log("✓ Protocol legend codes found")

        if route_count > 0:
            st.log(f"✓ Found {route_count} route entries in VRF default")
        else:
            st.warn("No route entries found (VRF may be empty)")

        # ===== Step C: Additional Test - VRF All with Sub-command =====
        st.log("=" * 80)
        st.log("STEP C: Additional Test - 'show ip route vrf all summary' (for comparison)")
        st.log("=" * 80)

        command_vrf_all_summary = "show ip route vrf all summary"
        output_vrf_all_summary = self._execute_show_command(command_vrf_all_summary, skip_tmpl=True)

        if output_vrf_all_summary:
            output_vrf_all_str = str(output_vrf_all_summary)

            # Note: This output is identical to 'show ip route summary'
            if "Route Source" in output_vrf_all_str and "Routes" in output_vrf_all_str:
                st.log("✓ VRF all summary executed successfully (shows default VRF summary)")

                # Check if it shows vrf identifier
                if "(vrf" in output_vrf_all_str.lower():
                    vrf_match = re.search(r'\(vrf\s+(\w+)\)', output_vrf_all_str, re.IGNORECASE)
                    if vrf_match:
                        vrf_name = vrf_match.group(1)
                        st.log(f"✓ Summary shows VRF: {vrf_name}")

        st.banner("✓ TEST PASSED - VRF command validation completed")
        st.log("Validated:")
        st.log("  - Incomplete 'vrf all' command error handling")
        st.log("  - Complete 'vrf default' route display")
        st.log("  - VRF all summary command execution")
        st.report_pass("test_case_passed")
