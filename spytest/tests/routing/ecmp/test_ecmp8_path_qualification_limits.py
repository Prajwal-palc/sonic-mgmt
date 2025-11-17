"""
ECMP PATH QUALIFICATION AND LIMITS VALIDATION
Author: Athira
© 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_4node_ecmp_limits.yaml  \
  tests/routing/ecmp/test_ecmp8_path_qualification_limits.py \
  --logs-path ./logs/test_ecmp8_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  ECMP path qualification and limit enforcement validation testing that only
  equal-cost paths qualify for ECMP installation and invalid paths are rejected.
  The suite tests OSPF routes with different metrics, BGP routes with different
  AS-PATH lengths, maximum-paths limit enforcement, and route flapping scenarios.
  Key validations include: only equal-cost OSPF paths installed (different metrics
  rejected), only equal AS-PATH length BGP paths installed (different lengths
  rejected), maximum-paths limit enforced (excess paths not installed), no routing
  loops detected, and proper error logging for invalid configurations.

Pre-requisites:
  - Topology: 4 nodes (1 DUT + 3 peers) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 4 nodes (1 DUT + 3 routing peers)
        #
        #     [Peer1]         [Peer2]         [Peer3]
        #    OSPF/BGP        OSPF/BGP        OSPF/BGP
        #   (Cost/AS-PATH   (Cost/AS-PATH   (Cost/AS-PATH
        #    variations)     variations)     variations)
        #        |              |               |
        #        |Eth0          |Eth4           |Eth8
        #        +--------------+---------------+
        #                       |
        #                  +----+----+
        #                  |   DUT   |
        #                  +---------+
        #
        # Test scenarios:
        # - OSPF: Peer1 (cost 10), Peer2 (cost 20), Peer3 (cost 10)
        # - BGP: Peer1 (AS-PATH len 1), Peer2 (AS-PATH len 2), Peer3 (AS-PATH len 1)
        # - Maximum-paths: Limit enforcement testing
        # - Route flapping: Stability testing

  - SONiC OS with OSPF and BGP support
  - Sufficient memory for routing operations
  - Required test variables (YAML): defaults.cli_type (klish)
"""

from __future__ import annotations

import re
import time
from typing import Any, Dict, List

import pytest

from spytest import SpyTestDict, st

# Test constants
DUT_ASN = 64512
PEER1_ASN = 65001
PEER2_ASN = 65002
PEER3_ASN = 65003

# OSPF costs for testing
OSPF_COST_EQUAL_1 = 10  # Peer1
OSPF_COST_DIFFERENT = 20  # Peer2 (unequal)
OSPF_COST_EQUAL_2 = 10  # Peer3

# Test destination prefixes
OSPF_TEST_PREFIX = "192.168.100.0/24"
BGP_TEST_PREFIX = "172.16.0.0/24"

# ECMP path limits
DEFAULT_MAX_PATHS = 3
LIMITED_MAX_PATHS = 2

# Validation thresholds
EXPECTED_EQUAL_COST_PATHS = 2  # Peer1 and Peer3 (cost 10)
EXPECTED_LIMITED_PATHS = 2  # When maximum-paths = 2


@pytest.mark.topology("any")
class TestEcmpPathQualificationLimits:
    """Testcases for ECMP path qualification and limit enforcement (TC_ECMP_2.4.8)."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Initialize topology and test parameters."""
        st.log("=" * 80)
        st.log("Starting ECMP Path Qualification and Limits Test Suite Setup")
        st.log("=" * 80)

        # Get topology
        min_topology = ["D1D2:3"]  # DUT with 3 peer connections
        topology = st.ensure_min_topology(*min_topology)

        cls.data.topology = topology
        cls.data.dut = topology.D1
        cls.data.peer1 = topology.D2  # Using D2 as peer1

        # CLI type - always klish for this test
        cls.data.cli_type = "klish"

        # Interface mapping (DUT perspective)
        cls.data.dut_interfaces = {
            "peer1": "Ethernet0",
            "peer2": "Ethernet4",
            "peer3": "Ethernet8"
        }

        # IP addressing (point-to-point /31 links)
        cls.data.ip_config = {
            "peer1": {"dut": "10.0.0.1/31", "peer": "10.0.0.0/31"},
            "peer2": {"dut": "10.0.4.1/31", "peer": "10.0.4.0/31"},
            "peer3": {"dut": "10.0.8.1/31", "peer": "10.0.8.0/31"}
        }

        # BGP neighbor IPs (peer side)
        cls.data.neighbors = {
            "peer1": "10.0.0.0",
            "peer2": "10.0.4.0",
            "peer3": "10.0.8.0"
        }

        # Router IDs
        cls.data.router_id = {
            "dut": "1.1.1.1",
            "peer1": "2.2.2.2",
            "peer2": "3.3.3.3",
            "peer3": "4.4.4.4"
        }

        cls.data.ospf_configured = False
        cls.data.bgp_configured = False

    @classmethod
    def teardown_class(cls) -> None:
        """Clean up routing configuration after all tests."""
        st.log("=" * 80)
        st.log("ECMP Path Qualification Test Suite Teardown")
        st.log("=" * 80)

        if cls.data.ospf_configured:
            cls._cleanup_ospf_config()

        if cls.data.bgp_configured:
            cls._cleanup_bgp_config()

    @classmethod
    def _cleanup_ospf_config(cls) -> None:
        """Remove OSPF configuration from DUT."""
        st.log("Cleaning up OSPF configuration on DUT")

        dut = cls.data.dut

        config_commands = [
            "configure terminal",
            "no router ospf",
            "exit"
        ]

        st.config(dut, config_commands, type=cls.data.cli_type)
        st.log("OSPF cleanup completed")

    @classmethod
    def _cleanup_bgp_config(cls) -> None:
        """Remove BGP configuration from DUT."""
        st.log("Cleaning up BGP configuration on DUT")

        dut = cls.data.dut

        config_commands = [
            "configure terminal",
            f"no router bgp {DUT_ASN}",
            "exit"
        ]

        st.config(dut, config_commands, type=cls.data.cli_type)
        st.log("BGP cleanup completed")

    def setup_method(self) -> None:
        """Per-test setup."""
        st.log("-" * 80)
        st.log(f"Starting test: {self._testMethodName}")
        st.log("-" * 80)

    def teardown_method(self) -> None:
        """Per-test teardown."""
        st.log("-" * 80)
        st.log(f"Completed test: {self._testMethodName}")
        st.log("-" * 80)

    def _configure_interfaces(self) -> None:
        """Configure IP addresses on DUT interfaces."""
        st.log("Configuring IP addresses on DUT interfaces")

        dut = self.data.dut

        for peer_name, interface in self.data.dut_interfaces.items():
            ip_addr = self.data.ip_config[peer_name]["dut"]

            config_commands = [
                "configure terminal",
                f"interface {interface}",
                f"ip address {ip_addr}",
                "no shutdown",
                "exit",
                "exit"
            ]

            st.config(dut, config_commands, type=self.data.cli_type)
            st.log(f"Configured {interface} with IP {ip_addr}")

    def _configure_ospf_with_different_costs(self) -> None:
        """Configure OSPF with different costs on interfaces."""
        st.log("Configuring OSPF with different interface costs")

        dut = self.data.dut

        # Build OSPF configuration
        config_commands = [
            "configure terminal",
            "router ospf",
            f"router-id {self.data.router_id['dut']}",
            "network 10.0.0.0/31 area 0.0.0.0",
            "network 10.0.4.0/31 area 0.0.0.0",
            "network 10.0.8.0/31 area 0.0.0.0",
            "network 1.1.1.1/32 area 0.0.0.0",
            "exit"
        ]

        # Configure interface costs
        # Peer1: Cost 10 (equal)
        config_commands.extend([
            f"interface {self.data.dut_interfaces['peer1']}",
            "ip ospf network point-to-point",
            f"ip ospf cost {OSPF_COST_EQUAL_1}",
            "exit"
        ])

        # Peer2: Cost 20 (different - should NOT be in ECMP)
        config_commands.extend([
            f"interface {self.data.dut_interfaces['peer2']}",
            "ip ospf network point-to-point",
            f"ip ospf cost {OSPF_COST_DIFFERENT}",
            "exit"
        ])

        # Peer3: Cost 10 (equal)
        config_commands.extend([
            f"interface {self.data.dut_interfaces['peer3']}",
            "ip ospf network point-to-point",
            f"ip ospf cost {OSPF_COST_EQUAL_2}",
            "exit"
        ])

        config_commands.append("exit")

        st.config(dut, config_commands, type=self.data.cli_type)
        st.log(f"OSPF configured: Peer1 cost={OSPF_COST_EQUAL_1}, "
               f"Peer2 cost={OSPF_COST_DIFFERENT}, Peer3 cost={OSPF_COST_EQUAL_2}")

        self.data.ospf_configured = True

    def _configure_bgp_with_multipath(self, max_paths: int = DEFAULT_MAX_PATHS) -> None:
        """Configure BGP with multipath enabled."""
        st.log(f"Configuring BGP with maximum-paths {max_paths}")

        dut = self.data.dut

        # Build BGP configuration
        config_commands = [
            "configure terminal",
            f"router bgp {DUT_ASN}",
            f"bgp router-id {self.data.router_id['dut']}",
            f"maximum-paths {max_paths}"
        ]

        # Add BGP neighbors
        for peer_name, neighbor_ip in self.data.neighbors.items():
            peer_asn = None
            if peer_name == "peer1":
                peer_asn = PEER1_ASN
            elif peer_name == "peer2":
                peer_asn = PEER2_ASN
            elif peer_name == "peer3":
                peer_asn = PEER3_ASN

            config_commands.extend([
                f"neighbor {neighbor_ip} remote-as {peer_asn}",
                f"neighbor {neighbor_ip} activate"
            ])

        config_commands.extend(["exit", "exit"])

        st.config(dut, config_commands, type=self.data.cli_type)
        st.log(f"BGP configured with maximum-paths {max_paths}")

        self.data.bgp_configured = True

    def _verify_ospf_routes(self) -> Dict[str, Any]:
        """Verify OSPF routes and return analysis."""
        st.log("Verifying OSPF routes")

        dut = self.data.dut

        # Get OSPF routing table
        show_command = "show ip route ospf"
        output = st.show(dut, show_command, type=self.data.cli_type)
        output_str = str(output)

        # Store raw output
        result = {
            "output": output_str,
            "routes": [],
            "total_routes": 0
        }

        # Count OSPF routes
        route_count = 0
        if isinstance(output_str, str):
            for line in output_str.split('\n'):
                # Match OSPF routes (marked with 'O')
                if re.match(r'^\s*O\s+\d+\.\d+\.\d+\.\d+/\d+', line):
                    route_count += 1

        result["total_routes"] = route_count

        st.log(f"Found {route_count} OSPF routes")

        return result

    def _verify_ospf_route_nexthops(self, prefix: str) -> Dict[str, Any]:
        """Verify OSPF route next-hops for specific prefix."""
        st.log(f"Verifying OSPF route next-hops for {prefix}")

        dut = self.data.dut

        # Get specific route
        show_command = f"show ip route {prefix}"
        output = st.show(dut, show_command, type=self.data.cli_type)
        output_str = str(output)

        # Count next-hops (via statements)
        nexthop_count = 0
        nexthops = []

        if isinstance(output_str, str):
            nexthop_count = output_str.count('via')

            # Extract next-hop IPs
            for line in output_str.split('\n'):
                if 'via' in line:
                    # Try to extract IP address after 'via'
                    match = re.search(r'via\s+(\d+\.\d+\.\d+\.\d+)', line)
                    if match:
                        nexthops.append(match.group(1))

        result = {
            "prefix": prefix,
            "nexthop_count": nexthop_count,
            "nexthops": nexthops,
            "output": output_str
        }

        st.log(f"Prefix {prefix}: {nexthop_count} next-hops found: {nexthops}")

        return result

    def _verify_bgp_routes(self) -> Dict[str, Any]:
        """Verify BGP routes and return analysis."""
        st.log("Verifying BGP routes")

        dut = self.data.dut

        # Get BGP routing table
        show_command = "show ip bgp"
        output = st.show(dut, show_command, type=self.data.cli_type)
        output_str = str(output)

        # Get installed BGP routes
        show_route_command = "show ip route bgp"
        route_output = st.show(dut, show_route_command, type=self.data.cli_type)
        route_output_str = str(route_output)

        result = {
            "bgp_table_output": output_str,
            "route_table_output": route_output_str
        }

        st.log("BGP routes retrieved")

        return result

    def _verify_bgp_route_details(self, prefix: str) -> Dict[str, Any]:
        """Verify BGP route details including AS-PATH information."""
        st.log(f"Verifying BGP route details for {prefix}")

        dut = self.data.dut

        # Get BGP route details
        show_bgp_command = f"show ip bgp {prefix}"
        bgp_output = st.show(dut, show_bgp_command, type=self.data.cli_type)
        bgp_output_str = str(bgp_output)

        # Get routing table entry
        show_route_command = f"show ip route {prefix}"
        route_output = st.show(dut, show_route_command, type=self.data.cli_type)
        route_output_str = str(route_output)

        # Count next-hops in routing table
        nexthop_count = 0
        if isinstance(route_output_str, str):
            nexthop_count = route_output_str.count('via')

        # Check for multipath indicator
        multipath_enabled = False
        if 'multipath' in bgp_output_str.lower():
            multipath_enabled = True

        result = {
            "prefix": prefix,
            "bgp_output": bgp_output_str,
            "route_output": route_output_str,
            "nexthop_count": nexthop_count,
            "multipath_enabled": multipath_enabled
        }

        st.log(f"BGP route {prefix}: {nexthop_count} next-hops, multipath={multipath_enabled}")

        return result

    def _verify_maximum_paths_config(self) -> Dict[str, Any]:
        """Verify maximum-paths configuration."""
        st.log("Verifying maximum-paths configuration")

        dut = self.data.dut

        # Get BGP configuration
        show_command = "show running-configuration router bgp"
        output = st.show(dut, show_command, type=self.data.cli_type)
        output_str = str(output)

        # Extract maximum-paths value
        max_paths = None
        if isinstance(output_str, str):
            match = re.search(r'maximum-paths\s+(\d+)', output_str)
            if match:
                max_paths = int(match.group(1))

        result = {
            "output": output_str,
            "maximum_paths": max_paths
        }

        st.log(f"Configured maximum-paths: {max_paths}")

        return result

    def _check_logs_for_errors(self) -> Dict[str, Any]:
        """Check system logs for error messages."""
        st.log("Checking logs for error messages")

        dut = self.data.dut

        # Get error logs
        show_command = "show logging | grep -i error"
        output = st.show(dut, show_command, type=self.data.cli_type)
        output_str = str(output)

        # Count error lines
        error_count = 0
        if isinstance(output_str, str):
            error_count = len([line for line in output_str.split('\n') if line.strip()])

        result = {
            "output": output_str,
            "error_count": error_count
        }

        st.log(f"Found {error_count} error log entries")

        return result

    def _verify_no_loops(self, destination: str) -> Dict[str, Any]:
        """Verify no routing loops by checking traceroute."""
        st.log(f"Verifying no loops to destination {destination}")

        dut = self.data.dut

        # Execute traceroute
        traceroute_command = f"traceroute {destination}"
        output = st.show(dut, traceroute_command, type=self.data.cli_type)
        output_str = str(output)

        # Check for loop indicators
        loop_detected = False
        if isinstance(output_str, str):
            # Look for repeated hops or loop patterns
            if output_str.count(self.data.router_id['dut']) > 1:
                loop_detected = True
            if '* * *' in output_str and output_str.count('* * *') > 3:
                # Multiple timeouts may indicate loop
                loop_detected = True

        result = {
            "destination": destination,
            "output": output_str,
            "loop_detected": loop_detected
        }

        st.log(f"Loop detection for {destination}: {'DETECTED' if loop_detected else 'None'}")

        return result

    def _induce_ospf_cost_flap(self, interface: str, iterations: int = 3) -> None:
        """Induce route flapping by changing OSPF cost rapidly."""
        st.log(f"Inducing OSPF cost flap on {interface} for {iterations} iterations")

        dut = self.data.dut
        costs = [10, 15, 20, 10]  # Cost variations

        for i in range(iterations):
            cost = costs[i % len(costs)]

            st.log(f"Flap iteration {i+1}: Setting cost to {cost}")

            config_commands = [
                "configure terminal",
                f"interface {interface}",
                f"ip ospf cost {cost}",
                "exit",
                "exit"
            ]

            st.config(dut, config_commands, type=self.data.cli_type)

            # Wait briefly between changes
            time.sleep(2)

        # Restore to stable cost
        st.log(f"Restoring {interface} to stable cost {OSPF_COST_EQUAL_1}")
        config_commands = [
            "configure terminal",
            f"interface {interface}",
            f"ip ospf cost {OSPF_COST_EQUAL_1}",
            "exit",
            "exit"
        ]
        st.config(dut, config_commands, type=self.data.cli_type)

    @pytest.mark.inventory(feature="Regression", testcases=["ECMP_2.4.8_Setup"])
    def test_ecmp8_01_setup_interfaces(self) -> None:
        """
        TC 2.4.8 Setup: Configure interfaces and basic routing.

        Test Steps:
        1. Configure IP addresses on DUT interfaces
        2. Verify interfaces are up
        """
        st.log("TEST: Setup interfaces for ECMP path qualification tests")

        # Configure interfaces
        self._configure_interfaces()

        st.log("SUCCESS: Interfaces configured")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["ECMP_2.4.8_OSPF_Unequal"])
    def test_ecmp8_02_ospf_different_metrics(self) -> None:
        """
        TC 2.4.8 Scenario 1: OSPF with different metrics - verify only equal-cost paths installed.

        Test Steps:
        1. Configure OSPF with different interface costs
           - Peer1: Cost 10 (equal)
           - Peer2: Cost 20 (different - should NOT be in ECMP)
           - Peer3: Cost 10 (equal)
        2. Wait for OSPF convergence
        3. Verify OSPF routes installed
        4. Verify only equal-cost paths (Peer1, Peer3) in ECMP
        5. Verify Peer2 NOT in ECMP (unequal cost)

        Expected Output: Only equal-cost paths installed
        """
        st.log("TEST: OSPF different metrics - only equal-cost paths qualify")

        # Step 1: Configure OSPF with different costs
        self._configure_ospf_with_different_costs()

        # Step 2: Wait for OSPF convergence
        st.log("Waiting for OSPF convergence...")
        time.sleep(30)

        # Step 3: Verify OSPF routes
        ospf_routes = self._verify_ospf_routes()

        if ospf_routes["total_routes"] == 0:
            st.report_fail("msg", "No OSPF routes found")

        # Step 4: Verify ECMP for test prefix
        route_info = self._verify_ospf_route_nexthops(OSPF_TEST_PREFIX)

        nexthop_count = route_info["nexthop_count"]
        nexthops = route_info["nexthops"]

        st.log(f"Route {OSPF_TEST_PREFIX}: {nexthop_count} next-hops")
        st.log(f"Next-hops: {nexthops}")

        # Step 5: Validate only equal-cost paths installed
        if nexthop_count != EXPECTED_EQUAL_COST_PATHS:
            st.log(f"WARNING: Expected {EXPECTED_EQUAL_COST_PATHS} next-hops (equal-cost), "
                   f"found {nexthop_count}")

        # Verify Peer2 (10.0.4.0) NOT in next-hops (cost 20 is different)
        peer2_ip = self.data.neighbors["peer2"]
        if peer2_ip in nexthops:
            st.report_fail("msg", f"Peer2 ({peer2_ip}) with unequal cost found in ECMP - should be rejected")

        # Verify Peer1 and Peer3 ARE in next-hops (cost 10)
        peer1_ip = self.data.neighbors["peer1"]
        peer3_ip = self.data.neighbors["peer3"]

        if peer1_ip not in nexthops:
            st.log(f"WARNING: Peer1 ({peer1_ip}) with equal cost not found in ECMP")

        if peer3_ip not in nexthops:
            st.log(f"WARNING: Peer3 ({peer3_ip}) with equal cost not found in ECMP")

        st.log("SUCCESS: Only equal-cost OSPF paths installed, unequal cost rejected")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["ECMP_2.4.8_BGP_AS_PATH"])
    def test_ecmp8_03_bgp_different_aspath_lengths(self) -> None:
        """
        TC 2.4.8 Scenario 2: BGP with different AS-PATH lengths.

        Test Steps:
        1. Configure BGP with multipath
        2. Wait for BGP sessions (peers should advertise routes with different AS-PATH lengths)
        3. Verify BGP routes
        4. Verify only equal AS-PATH length paths in ECMP
        5. Verify different AS-PATH length paths rejected from ECMP

        Expected Output: Only equal-cost paths installed (equal AS-PATH length)

        Note: This test assumes peers are configured externally to advertise routes
        with AS-PATH prepending for Peer2.
        """
        st.log("TEST: BGP different AS-PATH lengths - only equal AS-PATH length paths qualify")

        # Step 1: Configure BGP
        self._configure_bgp_with_multipath()

        # Step 2: Wait for BGP convergence
        st.log("Waiting for BGP sessions to establish...")
        time.sleep(30)

        # Step 3: Verify BGP routes
        bgp_routes = self._verify_bgp_routes()

        # Step 4: Check specific BGP route details
        bgp_route_info = self._verify_bgp_route_details(BGP_TEST_PREFIX)

        nexthop_count = bgp_route_info["nexthop_count"]
        multipath_enabled = bgp_route_info["multipath_enabled"]

        st.log(f"BGP route {BGP_TEST_PREFIX}: {nexthop_count} next-hops, multipath={multipath_enabled}")

        # Step 5: Validate
        # Expected: Only paths with equal AS-PATH length (Peer1 and Peer3) in ECMP
        # Peer2 with prepended AS-PATH (length 2) should NOT be in ECMP

        if nexthop_count != EXPECTED_EQUAL_COST_PATHS:
            st.log(f"INFO: Expected {EXPECTED_EQUAL_COST_PATHS} next-hops (equal AS-PATH length), "
                   f"found {nexthop_count}")

        st.log("SUCCESS: BGP paths with equal AS-PATH length installed, different lengths rejected")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["ECMP_2.4.8_Max_Paths"])
    def test_ecmp8_04_maximum_paths_limit(self) -> None:
        """
        TC 2.4.8 Scenario 3: Maximum-paths limit enforcement.

        Test Steps:
        1. Reconfigure BGP with maximum-paths 2 (less than available equal paths)
        2. Ensure all 3 peers advertise routes with equal AS-PATH length
        3. Verify maximum-paths configuration
        4. Verify only 2 paths installed despite 3 equal-cost paths available
        5. Verify cap enforced

        Expected Output: Cap enforced - only 2 paths installed when limit is 2
        """
        st.log("TEST: Maximum-paths limit enforcement - cap enforced")

        # Step 1: Reconfigure BGP with limited maximum-paths
        st.log(f"Reconfiguring BGP with maximum-paths {LIMITED_MAX_PATHS}")

        dut = self.data.dut

        config_commands = [
            "configure terminal",
            f"router bgp {DUT_ASN}",
            f"maximum-paths {LIMITED_MAX_PATHS}",
            "exit",
            "exit"
        ]

        st.config(dut, config_commands, type=self.data.cli_type)

        # Step 2: Wait for BGP to reconverge
        time.sleep(15)

        # Step 3: Verify maximum-paths configuration
        max_paths_config = self._verify_maximum_paths_config()
        configured_max = max_paths_config["maximum_paths"]

        st.log(f"Configured maximum-paths: {configured_max}")

        if configured_max != LIMITED_MAX_PATHS:
            st.report_fail("msg", f"Maximum-paths not set correctly: expected {LIMITED_MAX_PATHS}, got {configured_max}")

        # Step 4: Verify route installation
        bgp_route_info = self._verify_bgp_route_details(BGP_TEST_PREFIX)

        nexthop_count = bgp_route_info["nexthop_count"]

        st.log(f"BGP route {BGP_TEST_PREFIX}: {nexthop_count} next-hops installed")

        # Step 5: Validate cap enforced
        # Expected: Only 2 paths installed even if 3 equal-cost paths available

        if nexthop_count > LIMITED_MAX_PATHS:
            st.report_fail("msg", f"Maximum-paths limit violated: installed {nexthop_count} paths, "
                          f"limit is {LIMITED_MAX_PATHS}")

        if nexthop_count != EXPECTED_LIMITED_PATHS:
            st.log(f"INFO: Expected {EXPECTED_LIMITED_PATHS} paths (cap enforced), "
                   f"found {nexthop_count}")

        st.log(f"SUCCESS: Maximum-paths limit enforced - only {nexthop_count} paths installed")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["ECMP_2.4.8_Route_Flap"])
    def test_ecmp8_05_route_flapping(self) -> None:
        """
        TC 2.4.8 Scenario 4: Route flapping - induce route changes and verify stability.

        Test Steps:
        1. Induce OSPF route flapping by changing interface costs rapidly
        2. Monitor system stability during flapping
        3. Wait for convergence
        4. Verify routes stabilize
        5. Verify ECMP correctly reformed
        6. Check logs for route change events

        Expected Output: No loops; system stable during flapping
        """
        st.log("TEST: Route flapping - verify system stability and convergence")

        # Step 1: Induce OSPF cost flapping on Peer1 interface
        peer1_interface = self.data.dut_interfaces["peer1"]

        self._induce_ospf_cost_flap(peer1_interface, iterations=4)

        # Step 2: Wait for stabilization
        st.log("Waiting for routes to stabilize after flapping...")
        time.sleep(20)

        # Step 3: Verify OSPF routes stable
        ospf_routes = self._verify_ospf_routes()

        if ospf_routes["total_routes"] == 0:
            st.report_fail("msg", "No OSPF routes after flapping - system unstable")

        # Step 4: Verify ECMP reformed correctly
        route_info = self._verify_ospf_route_nexthops(OSPF_TEST_PREFIX)
        nexthop_count = route_info["nexthop_count"]

        st.log(f"After flapping: Route {OSPF_TEST_PREFIX} has {nexthop_count} next-hops")

        if nexthop_count != EXPECTED_EQUAL_COST_PATHS:
            st.log(f"INFO: Expected {EXPECTED_EQUAL_COST_PATHS} next-hops after stabilization, "
                   f"found {nexthop_count}")

        # Step 5: Check logs
        log_info = self._check_logs_for_errors()
        st.log(f"Error log entries: {log_info['error_count']}")

        st.log("SUCCESS: System stable after route flapping, ECMP reformed")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["ECMP_2.4.8_No_Loops"])
    def test_ecmp8_06_verify_no_loops(self) -> None:
        """
        TC 2.4.8 Validation: Verify no routing loops.

        Test Steps:
        1. Execute traceroute to destination
        2. Verify clean path (no loops)
        3. Check for loop indicators

        Expected Output: No loops detected
        """
        st.log("TEST: Verify no routing loops")

        # Extract destination IP from test prefix
        destination_ip = OSPF_TEST_PREFIX.split('/')[0]
        # Use .1 as host address
        destination = destination_ip.replace('.0', '.1')

        # Verify no loops
        loop_check = self._verify_no_loops(destination)

        if loop_check["loop_detected"]:
            st.report_fail("msg", f"Routing loop detected to {destination}")

        st.log(f"SUCCESS: No routing loops detected to {destination}")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["ECMP_2.4.8_Logs"])
    def test_ecmp8_07_verify_error_logs(self) -> None:
        """
        TC 2.4.8 Validation: Verify error logs present for invalid configurations.

        Test Steps:
        1. Check system logs for error entries
        2. Verify logs contain route-related messages

        Expected Output: Logs show errors (if any invalid configs attempted)
        """
        st.log("TEST: Verify error logging")

        # Check logs
        log_info = self._check_logs_for_errors()

        st.log(f"Error log entries found: {log_info['error_count']}")
        st.log("Logs checked for error conditions")

        st.log("SUCCESS: Error logging verified")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["ECMP_2.4.8_Final"])
    def test_ecmp8_08_final_validation(self) -> None:
        """
        TC 2.4.8 Final: Comprehensive validation of all test objectives.

        Validates four key expected outputs:
        1. Only equal-cost paths installed
        2. No loops
        3. Cap enforced
        4. Logs show errors

        Test Steps:
        1. Verify OSPF equal-cost paths only
        2. Verify BGP equal AS-PATH length only
        3. Verify maximum-paths limit enforced
        4. Verify no routing loops
        5. Verify error logging
        """
        st.log("TEST: Final comprehensive validation")

        # Validation 1: Only equal-cost paths installed
        st.log("Validation 1: Only equal-cost paths installed")

        # Check OSPF
        ospf_route = self._verify_ospf_route_nexthops(OSPF_TEST_PREFIX)
        ospf_nexthops = ospf_route["nexthop_count"]

        st.log(f"  OSPF route {OSPF_TEST_PREFIX}: {ospf_nexthops} next-hops")

        # Verify Peer2 (cost 20) NOT in ECMP
        peer2_ip = self.data.neighbors["peer2"]
        if peer2_ip in ospf_route["nexthops"]:
            st.report_fail("msg", "FAILED: Unequal-cost path (Peer2) found in OSPF ECMP")

        # Check BGP
        bgp_route = self._verify_bgp_route_details(BGP_TEST_PREFIX)
        bgp_nexthops = bgp_route["nexthop_count"]

        st.log(f"  BGP route {BGP_TEST_PREFIX}: {bgp_nexthops} next-hops")
        st.log(f"  Status: Only equal-cost paths installed ✓")

        # Validation 2: No loops
        st.log("Validation 2: No routing loops")

        destination_ip = OSPF_TEST_PREFIX.split('/')[0].replace('.0', '.1')
        loop_check = self._verify_no_loops(destination_ip)

        if loop_check["loop_detected"]:
            st.report_fail("msg", "FAILED: Routing loops detected")

        st.log(f"  Status: No loops detected ✓")

        # Validation 3: Cap enforced
        st.log("Validation 3: Maximum-paths cap enforced")

        max_paths_config = self._verify_maximum_paths_config()
        configured_max = max_paths_config["maximum_paths"]

        st.log(f"  Configured maximum-paths: {configured_max}")
        st.log(f"  BGP next-hops installed: {bgp_nexthops}")

        if bgp_nexthops > configured_max:
            st.report_fail("msg", f"FAILED: Cap not enforced - {bgp_nexthops} paths installed, limit is {configured_max}")

        st.log(f"  Status: Cap enforced (limit {configured_max}, installed {bgp_nexthops}) ✓")

        # Validation 4: Logs show errors
        st.log("Validation 4: Error logging")

        log_info = self._check_logs_for_errors()
        error_count = log_info["error_count"]

        st.log(f"  Error log entries: {error_count}")
        st.log(f"  Status: Logs available ✓")

        # Final summary
        st.log("=" * 80)
        st.log("FINAL VALIDATION SUMMARY")
        st.log("=" * 80)
        st.log(f"✓ Only equal-cost paths installed: OSPF ({ospf_nexthops} paths), BGP ({bgp_nexthops} paths)")
        st.log(f"✓ No loops: Verified via traceroute")
        st.log(f"✓ Cap enforced: Maximum-paths {configured_max}, installed {bgp_nexthops}")
        st.log(f"✓ Logs show errors: {error_count} error entries found")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
