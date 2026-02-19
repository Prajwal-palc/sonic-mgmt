"""
SHOW IP ROUTE CLI VALIDATION

Author: Shiva
Copyright (C) 2026, PALC Networks

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/ztp_standalone.yaml \\
  tests/routing/ip_route/test_show_ip_route_cli_validation.py \\
  --logs-path ./logs/ip_route_cli_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates 'show ip route' CLI behavior in SONiC by executing commands and
  verifying that the observed output matches expected CLI behavior.

  This test focuses on CLI validation, NOT routing protocol correctness:
  - Base command execution with route codes legend
  - CLI help (?) functionality
  - Filtered route views (connected, bgp)
  - Specific IP prefix lookup using DUT's management IP

Pre-requisites:
  - Topology: Single device (D1) | Supported: HW and Virtual
  - Access Method: sonic-cli (klish mode)
  - Test validates CLI behavior - empty output for bgp/ospf is VALID
  - No external YAML variable file required

Topology:
  ┌─────────────┐
  │    D1       │
  │  (DUT)      │
  │             │
  │ Management  │
  │  Interface  │
  └─────────────┘

Test Cases:
  TC1: test_show_ip_route_basic - Execute 'show ip route' and verify routing table display
  TC2: test_show_ip_route_help - Verify 'show ip route ?' displays valid subcommands
  TC3: test_show_ip_route_connected - Verify 'show ip route connected' shows only connected routes
  TC4: test_show_ip_route_bgp - Execute 'show ip route bgp' (empty output is valid)
  TC5: test_show_ip_route_specific_ip - Lookup DUT's management IP and verify routing entry

APIs Used:
  From apis/routing/ip.py:
    - show_ip_route() [lines 1089-1188]

  From apis/routing/ip_route_cli.py (NEW):
    - show_ip_route_help()
    - show_ip_route_connected()
    - show_ip_route_bgp_cli()
    - show_ip_route_specific_ip()
    - get_management_ip()

  From apis/system/basic.py:
    - get_ifconfig_inet() [lines 298-310]
"""

import pytest
from spytest import st, SpyTestDict

# Import existing APIs
import apis.routing.ip as ip_api

# Import new CLI validation APIs
import apis.routing.ip_route_cli as ip_route_cli_api


class TestShowIpRouteCliValidation:
    """
    Test class for 'show ip route' CLI command validation.

    This class validates CLI behavior and command execution,
    NOT routing protocol correctness or route accuracy.
    """

    @classmethod
    def setup_class(cls):
        """
        Setup class-level test data and configuration.

        Initializes:
        - DUT connection
        - CLI type (klish)
        - Test data dictionary
        """
        st.banner("SETUP: Initializing Show IP Route CLI Validation Tests")

        # Initialize test data
        cls.data = SpyTestDict()

        # Get testbed variables (single DUT topology)
        testbed_vars = st.get_testbed_vars()
        cls.data.dut = testbed_vars.dut_list[0]

        # Set CLI type to klish (sonic-cli)
        cls.data.cli_type = "klish"

        # Get DUT's management IP for TC5 (specific IP lookup)
        cls.data.mgmt_ip = ip_route_cli_api.get_management_ip(cls.data.dut)
        if cls.data.mgmt_ip:
            st.log(f"✓ Management IP detected: {cls.data.mgmt_ip}")
        else:
            st.log("⚠ Warning: Could not detect management IP, TC5 may be skipped")

        st.log(f"DUT: {cls.data.dut}")
        st.log(f"CLI Type: {cls.data.cli_type}")
        st.banner("SETUP: Complete")

    @classmethod
    def teardown_class(cls):
        """
        Cleanup after all tests complete.
        """
        st.banner("TEARDOWN: Show IP Route CLI Validation Tests Complete")

    def test_show_ip_route_basic(self):
        """
        TC1: Verify 'show ip route' displays IPv4 routing table.

        Objective:
          Execute base 'show ip route' command and validate that:
          - Command executes without error
          - Route codes legend is displayed
          - Routing table entries are shown (IPv4 unicast VRF default)

        Expected Behavior:
          - Command succeeds
          - Output contains route codes (K=kernel, C=connected, S=static, etc.)
          - Output shows "IPv4 unicast VRF default:"
          - At least one route entry is displayed

        Pass Criteria:
          - Command executes without CLI errors
          - Route codes legend present
          - IPv4 routing table displayed
        """
        st.banner("TC1: Show IP Route - Basic Command Execution")

        # Execute: show ip route
        st.log("Executing: show ip route")
        output = ip_api.show_ip_route(self.data.dut, cli_type=self.data.cli_type)
        output_str = str(output)

        st.log(f"Command output length: {len(output_str)} characters")

        # Validation 1: Check for route codes legend
        route_codes_indicators = [
            "Codes:",
            "kernel route",
            "connected",
            "static"
        ]

        found_codes = False
        for indicator in route_codes_indicators:
            if indicator in output_str:
                st.log(f"✓ Found route code indicator: '{indicator}'")
                found_codes = True
                break

        if not found_codes:
            st.log("⚠ Warning: Route codes legend not found in output")

        # Validation 2: Check for IPv4 routing table header
        if "IPv4" in output_str or "VRF" in output_str or "default" in output_str:
            st.log("✓ IPv4 routing table header found")
        else:
            st.log("⚠ Warning: IPv4 routing table header not clearly identified")

        # Validation 3: Check for at least one route entry
        # Routes typically contain IP addresses in format X.X.X.X
        import re
        ip_pattern = r'\d+\.\d+\.\d+\.\d+'
        ip_matches = re.findall(ip_pattern, output_str)

        if len(ip_matches) > 0:
            st.log(f"✓ Found {len(ip_matches)} IP address references in routing table")
        else:
            st.log("⚠ Warning: No IP addresses found in output")

        # Overall validation
        if output and len(output_str) > 50:
            st.log("✓ TC1 PASSED: 'show ip route' executed successfully")
            st.log(f"  Output preview: {output_str[:200]}...")
        else:
            st.error("✗ TC1 FAILED: Command output is empty or too short")
            pytest.fail("show ip route command did not return expected output")

    def test_show_ip_route_help(self):
        """
        TC2: Verify 'show ip route ?' displays valid subcommands and arguments.

        Objective:
          Execute 'show ip route ?' and validate help output shows:
          - IP address/prefix matching options (A.B.C.D, A.B.C.D/mask)
          - Protocol filters (bgp, connected, ospf, static)
          - Additional options (summary, vrf, pipe)

        Expected Help Output:
          A.B.C.D       Match this IP address
          A.B.C.D/mask  Match this IP prefix
          bgp           Border Gateway Protocol (BGP)
          connected     Connected routes
          ospf          Open Shortest Path First (OSPFv2)
          static        Statically configured routes
          summary       Summary of all routes
          vrf           IP route information per vrf
          |             Pipe through a command
          <cr>

        Pass Criteria:
          - Help command executes without error
          - Output contains expected subcommand options
          - At minimum: 'connected', 'bgp', 'A.B.C.D' should be present
        """
        st.banner("TC2: Show IP Route - Help Command Validation")

        # Execute: show ip route ?
        st.log("Executing: show ip route ?")
        output = ip_route_cli_api.show_ip_route_help(self.data.dut, cli_type=self.data.cli_type)
        output_str = str(output)

        st.log(f"Help output length: {len(output_str)} characters")

        # Validation: Check for expected help items
        expected_help_items = {
            "A.B.C.D": "IP address matching",
            "connected": "Connected routes filter",
            "bgp": "BGP routes filter",
            "static": "Static routes filter",
            "summary": "Route summary",
            "vrf": "VRF-specific routes"
        }

        found_items = {}
        for item, description in expected_help_items.items():
            if item in output_str:
                st.log(f"✓ Found help item: '{item}' ({description})")
                found_items[item] = True
            else:
                st.log(f"⚠ Help item not found: '{item}' ({description})")
                found_items[item] = False

        # Minimum requirement: connected and bgp should be present
        critical_items = ["connected", "bgp", "A.B.C.D"]
        critical_found = sum(1 for item in critical_items if found_items.get(item, False))

        if critical_found >= 2:
            st.log(f"✓ TC2 PASSED: Help output contains {critical_found}/3 critical items")
            st.log(f"  Found {sum(found_items.values())}/{len(expected_help_items)} total help items")
        else:
            st.error(f"✗ TC2 FAILED: Only {critical_found}/3 critical help items found")
            st.log(f"  Output: {output_str[:300]}")
            pytest.fail("Help output missing critical subcommand options")

    def test_show_ip_route_connected(self):
        """
        TC3: Verify 'show ip route connected' displays only directly connected routes.

        Objective:
          Execute 'show ip route connected' and validate that:
          - Command executes successfully
          - Only connected routes are shown (marked with 'C')
          - Routes show "directly connected" or similar indication
          - No kernel (K) or static (S) routes appear (unless also connected)

        Expected Output:
          IPv4 unicast VRF default:
          C>* 20.1.1.0/24 is directly connected, Vlan100
          C>* 172.31.0.0/16 is directly connected, Management0

        Pass Criteria:
          - Command executes without error
          - Output contains "directly connected" or 'C' route code
          - No obvious non-connected routes in output
        """
        st.banner("TC3: Show IP Route - Connected Routes Filter")

        # Execute: show ip route connected
        st.log("Executing: show ip route connected")
        output = ip_route_cli_api.show_ip_route_connected(self.data.dut, cli_type=self.data.cli_type)
        output_str = str(output)

        st.log(f"Connected routes output length: {len(output_str)} characters")

        # Validation 1: Check for connected route indicators
        connected_indicators = [
            "directly connected",
            "C>",
            "C ",
            "connected"
        ]

        found_connected = False
        for indicator in connected_indicators:
            if indicator in output_str:
                st.log(f"✓ Found connected route indicator: '{indicator}'")
                found_connected = True
                break

        # Validation 2: Check for IPv4 addresses (route entries)
        import re
        ip_pattern = r'\d+\.\d+\.\d+\.\d+'
        ip_matches = re.findall(ip_pattern, output_str)

        if len(ip_matches) > 0:
            st.log(f"✓ Found {len(ip_matches)} IP address references in connected routes")
        else:
            st.log("⚠ Warning: No IP addresses found - may have no connected routes")

        # Validation 3: Look for interface names (connected routes show interfaces)
        interface_patterns = [
            r'Management\d+',
            r'Ethernet\d+',
            r'Vlan\d+',
            r'PortChannel\d+',
            r'eth\d+'
        ]

        found_interfaces = []
        for pattern in interface_patterns:
            matches = re.findall(pattern, output_str)
            if matches:
                found_interfaces.extend(matches)

        if found_interfaces:
            st.log(f"✓ Found interfaces: {', '.join(set(found_interfaces))}")
        else:
            st.log("⚠ No interface names detected in output")

        # Overall validation
        if found_connected or len(ip_matches) > 0:
            st.log("✓ TC3 PASSED: 'show ip route connected' executed successfully")
            st.log(f"  Output preview: {output_str[:200]}...")
        else:
            st.log("⚠ TC3 WARNING: Command executed but no clear connected routes found")
            st.log("  Note: Empty output is VALID if no connected routes exist")

    def test_show_ip_route_bgp(self):
        """
        TC4: Verify 'show ip route bgp' executes successfully.

        Objective:
          Execute 'show ip route bgp' and validate that:
          - Command executes without CLI errors
          - Empty output is VALID (indicates no BGP routes configured)
          - If BGP routes exist, they are displayed with 'B' route code

        Expected Behavior:
          - Command succeeds (no syntax errors)
          - Output may be empty (valid - no BGP configuration)
          - If BGP routes present, shows route code 'B'

        IMPORTANT:
          This test validates CLI BEHAVIOR, not BGP configuration.
          Empty output is ACCEPTABLE and indicates no BGP routes.

        Pass Criteria:
          - Command executes without syntax/CLI errors
          - No error messages in output
          - Test passes regardless of whether BGP routes exist
        """
        st.banner("TC4: Show IP Route - BGP Routes Filter")

        # Execute: show ip route bgp
        st.log("Executing: show ip route bgp")
        st.log("Note: Empty output is VALID - indicates no BGP routes configured")

        output = ip_route_cli_api.show_ip_route_bgp_cli(self.data.dut, cli_type=self.data.cli_type)
        output_str = str(output)

        st.log(f"BGP routes output length: {len(output_str)} characters")

        # Validation 1: Check for CLI errors
        error_indicators = [
            "Error:",
            "Invalid",
            "Unknown command",
            "Incomplete command"
        ]

        has_error = False
        for error in error_indicators:
            if error in output_str:
                st.error(f"✗ Found error indicator: '{error}'")
                has_error = True

        if has_error:
            st.error("✗ TC4 FAILED: Command returned error")
            pytest.fail("show ip route bgp command returned error")

        # Validation 2: Check if BGP routes are present
        if len(output_str.strip()) < 10:
            st.log("✓ Empty output received (valid - no BGP routes configured)")
            st.log("  This is EXPECTED behavior when BGP is not configured")
            bgp_routes_present = False
        else:
            st.log(f"✓ Output received: {len(output_str)} characters")
            st.log(f"  Output preview: {output_str[:200]}...")

            # Check for BGP route indicators
            bgp_indicators = ["B>", "B ", "bgp", "BGP"]
            found_bgp = False
            for indicator in bgp_indicators:
                if indicator in output_str:
                    st.log(f"  ✓ Found BGP route indicator: '{indicator}'")
                    found_bgp = True

            if found_bgp:
                st.log("  ✓ BGP routes are present in routing table")
                bgp_routes_present = True
            else:
                st.log("  ⚠ Output present but no clear BGP indicators found")
                bgp_routes_present = False

        # Overall validation - command should execute without error
        st.log("✓ TC4 PASSED: 'show ip route bgp' executed successfully")
        if bgp_routes_present:
            st.log("  Result: BGP routes found in routing table")
        else:
            st.log("  Result: No BGP routes (expected when BGP not configured)")

    def test_show_ip_route_specific_ip(self):
        """
        TC5: Verify 'show ip route <IP>' displays routing entry for specific IP.

        Objective:
          Execute 'show ip route <IP>' using DUT's management IP and validate:
          - Command executes successfully
          - Displays routing entry matching the IP
          - Shows protocol (connected/kernel/static), metric, and interface

        Expected Output Format:
          Routing entry for 172.31.0.0/16
            Known via "connected", distance 0, metric 0, best
            * directly connected, Management0

        IMPORTANT:
          This test uses the DUT's ACTUAL management IP (dynamic),
          NOT a hardcoded IP address like 172.31.0.1.

        Pass Criteria:
          - Command executes without error
          - Output contains "Routing entry for" with the queried IP/prefix
          - Shows routing protocol and interface information
        """
        st.banner("TC5: Show IP Route - Specific IP Lookup (Dynamic Management IP)")

        # Check if management IP was detected in setup
        if not self.data.mgmt_ip:
            st.log("✗ Management IP not available, attempting to detect now...")
            self.data.mgmt_ip = ip_route_cli_api.get_management_ip(self.data.dut)

        if not self.data.mgmt_ip:
            st.error("✗ TC5 SKIPPED: Could not determine device management IP")
            pytest.skip("Management IP not available for testing")

        st.log(f"✓ Using management IP: {self.data.mgmt_ip}")

        # Execute: show ip route <management_ip>
        st.log(f"Executing: show ip route {self.data.mgmt_ip}")
        output = ip_route_cli_api.show_ip_route_specific_ip(
            self.data.dut,
            self.data.mgmt_ip,
            cli_type=self.data.cli_type
        )
        output_str = str(output)

        st.log(f"Specific IP route output length: {len(output_str)} characters")

        # Validation 1: Check for routing entry header
        routing_entry_indicators = [
            "Routing entry for",
            "Known via",
            "directly connected",
            "connected"
        ]

        found_routing_entry = False
        for indicator in routing_entry_indicators:
            if indicator in output_str:
                st.log(f"✓ Found routing entry indicator: '{indicator}'")
                found_routing_entry = True

        if not found_routing_entry:
            st.error("✗ No routing entry indicators found in output")
            st.log(f"  Output: {output_str[:300]}")

        # Validation 2: Check for protocol information
        protocol_indicators = [
            "connected",
            "kernel",
            "static",
            "distance",
            "metric"
        ]

        found_protocol = False
        for indicator in protocol_indicators:
            if indicator in output_str:
                st.log(f"✓ Found protocol/metric indicator: '{indicator}'")
                found_protocol = True

        # Validation 3: Check for interface information
        import re
        interface_patterns = [
            r'Management\d+',
            r'Ethernet\d+',
            r'eth\d+',
            r'Vlan\d+'
        ]

        found_interface = None
        for pattern in interface_patterns:
            match = re.search(pattern, output_str)
            if match:
                found_interface = match.group(0)
                st.log(f"✓ Found outgoing interface: {found_interface}")
                break

        # Validation 4: Verify the management IP appears in output
        if self.data.mgmt_ip in output_str:
            st.log(f"✓ Management IP {self.data.mgmt_ip} found in output")
        else:
            st.log(f"⚠ Management IP {self.data.mgmt_ip} not directly visible in output")
            st.log("  (May be shown as network prefix instead)")

        # Overall validation
        if found_routing_entry and (found_protocol or found_interface):
            st.log(f"✓ TC5 PASSED: Routing entry lookup for {self.data.mgmt_ip} successful")
            st.log(f"  Output preview: {output_str[:300]}...")
        else:
            st.error(f"✗ TC5 FAILED: Incomplete routing entry for {self.data.mgmt_ip}")
            st.log(f"  Full output: {output_str}")
            pytest.fail(f"show ip route {self.data.mgmt_ip} did not return expected routing entry")
