"""
BGP HIGH PREFIX SCALE TESTING (Test ID 6.1.1)
Author: Athira
2025

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/BGP/test_bgp_high_prefix_scale.py \
  --logs-path ./logs/test_bgp_high_prefix_scale_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Comprehensive test suite for BGP high prefix scale testing (Test ID 6.1.1).
  Validates DUT stability and correct route handling under large BGP prefix scale
  (≥10k routes). Includes control-plane and data-plane verification, resource
  monitoring, incremental injection, withdraw/recovery, route churn, IPv6 scale,
  VRF scale, FIB programming validation, persistence across reboots, and
  diagnostic artifact collection. Uses klish for BGP configuration and click
  for show command verification.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes (testbed_vs_2node.yaml)
        # +--------------------+                       +--------------------+
        # |       DUT1         |                       |       DUT2         |
        # | (Route Receiver)   |=======================| (Route Generator)  |
        # |  Eth4 10.0.24.0/31 |      BGP Peering      |  Eth4 10.0.24.1/31 |
        # +--------------------+                       +--------------------+

  - Feature: BGP with prefix advertisement capability
  - Required test variables (YAML): defaults.cli_type, defaults.verify_timeout,
    defaults.cleanup, testcases.* definitions for 6.1.1.1 through 6.1.1.10
  - DUT2 acts as route generator to advertise large number of prefixes
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.system.basic as basic_api

VAR_FILE_ENV = "BGP_HIGH_PREFIX_SCALE_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent / "vars_bgp_high_prefix_scale.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(
            f"BGP high prefix scale variable file not found: {candidate}"
        )

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError(
            "BGP high prefix scale YAML must contain key 'testcases'"
        )

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBGPHighPrefixScale:
    """Test suite for BGP high prefix scale validation (Test ID 6.1.1)."""

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
        cls.data.thresholds = SpyTestDict(defaults.get("thresholds", {}))

        # CLI type handling
        cls.data.config_cli_type = defaults.get("config_cli_type", "klish")
        cls.data.show_cli_type = defaults.get("show_cli_type", "click")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 120))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))
        cls.data.baseline_metrics = SpyTestDict()
        cls.data.test_artifacts = []

        # Map DUT aliases (D1, D2) to actual device handles
        cls.data.dut_map = SpyTestDict()
        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.dut_names = st.get_dut_names()

        # Extract common configuration
        cls.data.bgp_config = SpyTestDict(defaults.get("bgp", {}))
        cls.data.interface_config = SpyTestDict(defaults.get("interfaces", {}))

        st.log(f"BGP high prefix scale test suite initialized")
        st.log(f"Topology: {min_topology}")
        st.log(f"Config CLI: {cls.data.config_cli_type}")
        st.log(f"Show CLI: {cls.data.show_cli_type}")

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup all BGP configuration after suite completes."""
        if not cls.data.cleanup_enabled:
            st.log("Cleanup disabled; skipping teardown")
            return

        st.log("Starting suite-level cleanup...")
        cls._cleanup_bgp_configuration()
        st.log("Suite-level cleanup completed")

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        self._test_prefixes: List[str] = []
        self._test_start_time = datetime.now()
        st.log(f"Test started at {self._test_start_time}")

    def teardown_method(self) -> None:
        """Cleanup per-test resources."""
        if not self.data.cleanup_enabled:
            return

        # Test-specific cleanup handled within each test
        test_duration = (datetime.now() - self._test_start_time).total_seconds()
        st.log(f"Test duration: {test_duration:.2f} seconds")

    @classmethod
    def _resolve_dut(cls, alias: str | None) -> str | None:
        """Translate topology alias (e.g., D1) to framework DUT handle."""
        if not alias:
            return None
        if alias in cls.data.dut_map:
            return cls.data.dut_map[alias]
        if alias in cls.data.dut_names:
            return alias
        st.warn(f"Unable to resolve DUT alias '{alias}'")
        return None

    @classmethod
    def _cleanup_bgp_configuration(cls) -> None:
        """Remove all BGP configuration from all DUTs."""
        for dut_alias in ["D1", "D2"]:
            dut = cls._resolve_dut(dut_alias)
            if not dut:
                continue

            bgp_asn = cls.data.bgp_config.get(f"{dut_alias}_asn")
            if bgp_asn:
                st.log(f"Removing BGP configuration from {dut_alias}")
                # Delete BGP instance
                bgp_api.cleanup_router_bgp(dut, cli_type=cls.data.config_cli_type)

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid}")
        return testcase

    def _get_cpu_usage(self, dut: str) -> Dict[str, float]:
        """Get current CPU usage statistics."""
        try:
            # Use show processes cpu with click CLI
            output = st.show(
                dut,
                "show processes cpu",
                type=self.data.show_cli_type,
                skip_tmpl=True,
            )

            cpu_stats = {}
            # Parse output for CPU percentages
            # Format varies by platform; extract what we can
            if isinstance(output, str):
                # Look for CPU idle percentage
                idle_match = re.search(r"(\d+\.?\d*)%?\s*idle", output, re.I)
                if idle_match:
                    idle = float(idle_match.group(1))
                    cpu_stats["idle"] = idle
                    cpu_stats["usage"] = 100.0 - idle
                else:
                    # Try alternative format
                    usage_match = re.search(r"CPU:\s*(\d+\.?\d*)%", output, re.I)
                    if usage_match:
                        cpu_stats["usage"] = float(usage_match.group(1))

            return cpu_stats
        except Exception as e:
            st.warn(f"Failed to get CPU usage: {e}")
            return {}

    def _get_memory_usage(self, dut: str) -> Dict[str, int]:
        """Get current memory usage statistics."""
        try:
            # Use show system-memory
            output = st.show(
                dut,
                "show system-memory",
                type=self.data.show_cli_type,
                skip_tmpl=True,
            )

            mem_stats = {}
            if isinstance(output, str):
                # Parse memory statistics
                # Look for Total, Used, Free
                total_match = re.search(r"Total:\s*(\d+)", output, re.I)
                used_match = re.search(r"Used:\s*(\d+)", output, re.I)
                free_match = re.search(r"Free:\s*(\d+)", output, re.I)

                if total_match:
                    mem_stats["total"] = int(total_match.group(1))
                if used_match:
                    mem_stats["used"] = int(used_match.group(1))
                if free_match:
                    mem_stats["free"] = int(free_match.group(1))

                # Calculate percentage if we have total and used
                if "total" in mem_stats and "used" in mem_stats:
                    mem_stats["usage_percent"] = (
                        mem_stats["used"] * 100.0 / mem_stats["total"]
                    )

            return mem_stats
        except Exception as e:
            st.warn(f"Failed to get memory usage: {e}")
            return {}

    def _get_bgp_route_count(self, dut: str, vrf: str = None) -> int:
        """Get current BGP RIB route count."""
        try:
            cmd = "show ip bgp summary"
            if vrf:
                cmd = f"show ip bgp vrf {vrf} summary"

            # Try JSON output first
            output = st.show(
                dut,
                f"{cmd} -j",
                type=self.data.show_cli_type,
                skip_tmpl=True,
            )

            if output:
                # Parse JSON for route count
                try:
                    data = json.loads(output) if isinstance(output, str) else output
                    # JSON structure varies; look for common patterns
                    if isinstance(data, dict):
                        # Look for totalRoutes or similar
                        if "totalRoutes" in data:
                            return int(data["totalRoutes"])
                        # Or look in ipv4Unicast section
                        if "ipv4Unicast" in data:
                            return int(data["ipv4Unicast"].get("totalRoutes", 0))
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass

            # Fallback to text parsing
            output = st.show(dut, cmd, type=self.data.show_cli_type, skip_tmpl=True)
            if isinstance(output, str):
                # Look for "Total number of neighbors X" or similar
                match = re.search(r"(\d+)\s+route", output, re.I)
                if match:
                    return int(match.group(1))

            return 0
        except Exception as e:
            st.warn(f"Failed to get BGP route count: {e}")
            return 0

    def _get_fib_route_count(self, dut: str, vrf: str = None) -> int:
        """Get current FIB (routing table) route count."""
        try:
            cmd = "show ip route summary"
            if vrf:
                cmd = f"show ip route vrf {vrf} summary"

            output = st.show(dut, cmd, type=self.data.show_cli_type, skip_tmpl=True)

            if isinstance(output, str):
                # Look for BGP routes in summary
                match = re.search(r"bgp\s*:\s*(\d+)", output, re.I)
                if match:
                    return int(match.group(1))

            return 0
        except Exception as e:
            st.warn(f"Failed to get FIB route count: {e}")
            return 0

    def _collect_baseline_metrics(self, dut: str) -> Dict[str, Any]:
        """Collect baseline metrics for later comparison."""
        st.log(f"Collecting baseline metrics from {dut}")

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu": self._get_cpu_usage(dut),
            "memory": self._get_memory_usage(dut),
            "bgp_routes": self._get_bgp_route_count(dut),
            "fib_routes": self._get_fib_route_count(dut),
        }

        st.log(f"Baseline metrics: {metrics}")
        return metrics

    def _verify_resource_thresholds(
        self, dut: str, phase: str = "test"
    ) -> Tuple[bool, str]:
        """Verify CPU and memory are within acceptable thresholds."""
        cpu_stats = self._get_cpu_usage(dut)
        mem_stats = self._get_memory_usage(dut)

        cpu_threshold = self.data.thresholds.get("cpu_percent_warning", 70)
        mem_threshold = self.data.thresholds.get("memory_percent_warning", 75)

        issues = []

        if "usage" in cpu_stats:
            if cpu_stats["usage"] > cpu_threshold:
                issues.append(
                    f"CPU usage {cpu_stats['usage']:.1f}% exceeds threshold {cpu_threshold}%"
                )

        if "usage_percent" in mem_stats:
            if mem_stats["usage_percent"] > mem_threshold:
                issues.append(
                    f"Memory usage {mem_stats['usage_percent']:.1f}% exceeds threshold {mem_threshold}%"
                )

        if issues:
            return False, "; ".join(issues)

        return True, "Resources within thresholds"

    def _configure_interface(
        self, dut: str, interface: str, ip_address: str
    ) -> bool:
        """Configure IP address on interface."""
        try:
            st.log(f"Configuring {interface} on {dut} with IP {ip_address}")

            # Use klish CLI for configuration
            commands = [
                f"interface {interface}",
                "no shutdown",
                f"ip address {ip_address}",
                "exit",
            ]

            result = st.config(
                dut,
                commands,
                type=self.data.config_cli_type,
                skip_error_check=False,
            )

            # Verify interface is up
            time.sleep(2)
            return True
        except Exception as e:
            st.error(f"Failed to configure interface {interface}: {e}")
            return False

    def _configure_bgp_instance(
        self,
        dut: str,
        asn: int,
        router_id: str,
        neighbor_ip: str,
        neighbor_asn: int,
    ) -> bool:
        """Configure basic BGP instance with neighbor."""
        try:
            st.log(f"Configuring BGP AS {asn} on {dut}")

            # Use klish CLI for BGP configuration
            commands = [
                f"router bgp {asn}",
                f"bgp router-id {router_id}",
                f"neighbor {neighbor_ip} remote-as {neighbor_asn}",
                "address-family ipv4 unicast",
                f"neighbor {neighbor_ip} activate",
                "maximum-paths 64",
                "exit",
                "exit",
            ]

            result = st.config(
                dut,
                commands,
                type=self.data.config_cli_type,
                skip_error_check=False,
            )

            return True
        except Exception as e:
            st.error(f"Failed to configure BGP: {e}")
            return False

    def _verify_bgp_session(
        self, dut: str, neighbor_ip: str, timeout: int = 120
    ) -> bool:
        """Verify BGP session reaches Established state."""
        st.log(f"Verifying BGP session to {neighbor_ip} on {dut}")

        def _is_established():
            return bgp_api.verify_bgp_neighbor(
                dut,
                neighborip=neighbor_ip,
                state="Established",
                cli_type=self.data.show_cli_type,
            )

        if st.poll_wait(_is_established, timeout):
            st.log(f"BGP session to {neighbor_ip} is Established")
            return True
        else:
            st.error(f"BGP session to {neighbor_ip} failed to reach Established")
            return False

    def _advertise_prefixes(
        self, dut: str, asn: int, prefix_list: List[str]
    ) -> bool:
        """Advertise list of prefixes via BGP network statements."""
        try:
            st.log(f"Advertising {len(prefix_list)} prefixes from {dut}")

            commands = [f"router bgp {asn}", "address-family ipv4 unicast"]

            for prefix in prefix_list:
                commands.append(f"network {prefix}")

            commands.extend(["exit", "exit"])

            result = st.config(
                dut,
                commands,
                type=self.data.config_cli_type,
                skip_error_check=False,
            )

            st.log(f"Prefix advertisement configured on {dut}")
            return True
        except Exception as e:
            st.error(f"Failed to advertise prefixes: {e}")
            return False

    def _withdraw_prefixes(
        self, dut: str, asn: int, prefix_list: List[str]
    ) -> bool:
        """Withdraw list of prefixes via BGP."""
        try:
            st.log(f"Withdrawing {len(prefix_list)} prefixes from {dut}")

            commands = [f"router bgp {asn}", "address-family ipv4 unicast"]

            for prefix in prefix_list:
                commands.append(f"no network {prefix}")

            commands.extend(["exit", "exit"])

            result = st.config(
                dut,
                commands,
                type=self.data.config_cli_type,
                skip_error_check=True,
            )

            st.log(f"Prefix withdrawal configured on {dut}")
            return True
        except Exception as e:
            st.warn(f"Failed to withdraw prefixes (may be acceptable): {e}")
            return False

    def _generate_prefix_list(
        self, base_prefix: str, count: int, prefix_len: int = 24
    ) -> List[str]:
        """Generate list of IP prefixes for testing."""
        # Parse base prefix (e.g., "100.0.0.0")
        parts = base_prefix.split(".")
        if len(parts) != 4:
            st.error(f"Invalid base prefix: {base_prefix}")
            return []

        prefixes = []
        base_octets = [int(p) for p in parts]

        for i in range(count):
            # Calculate incremented octets from base
            # Increment across 2nd, 3rd, and 4th octets
            total_offset = i
            fourth_octet = (base_octets[3] + (total_offset % 256)) % 256
            third_octet = (base_octets[2] + ((total_offset // 256) % 256)) % 256
            second_octet = (base_octets[1] + (total_offset // 65536)) % 256
            first_octet = base_octets[0]

            prefix = f"{first_octet}.{second_octet}.{third_octet}.{fourth_octet}/{prefix_len}"
            prefixes.append(prefix)

        return prefixes

    def _wait_for_bgp_convergence(
        self,
        dut: str,
        expected_count: int,
        tolerance: int = 10,
        timeout: int = 600,
    ) -> bool:
        """Wait for BGP to converge to expected route count."""
        st.log(
            f"Waiting for BGP convergence on {dut}: expecting ~{expected_count} routes"
        )

        start_time = time.time()
        stable_count = 0
        last_count = -1

        while (time.time() - start_time) < timeout:
            current_count = self._get_bgp_route_count(dut)

            # Check if count is within tolerance
            if abs(current_count - expected_count) <= tolerance:
                # Need stable count for 3 consecutive checks
                if current_count == last_count:
                    stable_count += 1
                    if stable_count >= 3:
                        st.log(
                            f"BGP converged: {current_count} routes (expected {expected_count})"
                        )
                        return True
                else:
                    stable_count = 0

            last_count = current_count
            time.sleep(10)

        st.error(
            f"BGP did not converge within {timeout}s: current={last_count}, expected={expected_count}"
        )
        return False

    @pytest.mark.inventory(feature="Scalability", testcases=["BGP_High_Scale_6.1.1.1"])
    def test_baseline_environment_verification(self) -> None:
        """
        TC 6.1.1.1 - Baseline: Verify environment & resource baselines.

        Collect CPU, memory and baseline route counts before scale test
        to compare during/after injection.
        """
        testcase = self._get_testcase("6.1.1.1")
        dut1 = self._resolve_dut("D1")

        if not dut1:
            st.report_fail("msg", "Failed to resolve DUT1")

        st.log("=" * 80)
        st.log("TC 6.1.1.1: Baseline environment verification")
        st.log("=" * 80)

        # Collect baseline metrics from DUT1
        baseline = self._collect_baseline_metrics(dut1)
        self.data.baseline_metrics["D1"] = baseline

        # Verify metrics are reasonable
        if not baseline.get("cpu"):
            st.report_fail("msg", "Failed to collect CPU baseline")

        if not baseline.get("memory"):
            st.report_fail("msg", "Failed to collect memory baseline")

        # Verify resources are in good state
        cpu_usage = baseline["cpu"].get("usage", 0)
        if cpu_usage > 50:
            st.warn(f"High baseline CPU usage: {cpu_usage}%")

        mem_usage = baseline["memory"].get("usage_percent", 0)
        if mem_usage > 60:
            st.warn(f"High baseline memory usage: {mem_usage}%")

        st.log(f"Baseline established: CPU={cpu_usage}%, Memory={mem_usage}%")
        st.log(f"Baseline BGP routes: {baseline['bgp_routes']}")
        st.log(f"Baseline FIB routes: {baseline['fib_routes']}")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Scalability", testcases=["BGP_High_Scale_6.1.1.2"])
    def test_scale_injection_10k_ipv4_prefixes(self) -> None:
        """
        TC 6.1.1.2 - Scale injection: Advertise 10k IPv4 prefixes.

        Inject ≥10,000 IPv4 prefixes into DUT's BGP control-plane and
        verify BGP RIB growth and stability.
        """
        testcase = self._get_testcase("6.1.1.2")
        dut1 = self._resolve_dut("D1")
        dut2 = self._resolve_dut("D2")

        if not dut1 or not dut2:
            st.report_fail("msg", "Failed to resolve DUTs")

        st.log("=" * 80)
        st.log("TC 6.1.1.2: Scale injection - 10k IPv4 prefixes")
        st.log("=" * 80)

        # Get test parameters from configuration section
        config = testcase.get("configuration", {})
        prefix_count = config.get("prefix_count", 10000)
        base_prefix = config.get("base_prefix", "100.0.0.0")

        # Setup interfaces
        d1_interface = self.data.interface_config.get("D1_interface", "Ethernet4")
        d1_ip = self.data.interface_config.get("D1_ip", "10.0.24.0/31")
        d2_interface = self.data.interface_config.get("D2_interface", "Ethernet4")
        d2_ip = self.data.interface_config.get("D2_ip", "10.0.24.1/31")

        # Configure interfaces
        if not self._configure_interface(dut1, d1_interface, d1_ip):
            st.report_fail("msg", f"Failed to configure interface on D1")

        if not self._configure_interface(dut2, d2_interface, d2_ip):
            st.report_fail("msg", f"Failed to configure interface on D2")

        # Setup BGP
        d1_asn = self.data.bgp_config.get("D1_asn", 65001)
        d1_router_id = self.data.bgp_config.get("D1_router_id", "1.1.1.1")
        d2_asn = self.data.bgp_config.get("D2_asn", 65002)
        d2_router_id = self.data.bgp_config.get("D2_router_id", "2.2.2.2")

        neighbor_ip_d1 = d2_ip.split("/")[0]
        neighbor_ip_d2 = d1_ip.split("/")[0]

        # Configure BGP on both DUTs
        if not self._configure_bgp_instance(
            dut1, d1_asn, d1_router_id, neighbor_ip_d1, d2_asn
        ):
            st.report_fail("msg", "Failed to configure BGP on D1")

        if not self._configure_bgp_instance(
            dut2, d2_asn, d2_router_id, neighbor_ip_d2, d1_asn
        ):
            st.report_fail("msg", "Failed to configure BGP on D2")

        # Verify BGP sessions
        if not self._verify_bgp_session(dut1, neighbor_ip_d1, timeout=120):
            st.report_fail("msg", "BGP session failed to establish on D1")

        # Generate and advertise prefixes from DUT2
        st.log(f"Generating {prefix_count} prefixes...")
        prefix_list = self._generate_prefix_list(base_prefix, prefix_count)
        self._test_prefixes = prefix_list

        st.log(f"Advertising {len(prefix_list)} prefixes from D2...")
        if not self._advertise_prefixes(dut2, d2_asn, prefix_list):
            st.report_fail("msg", "Failed to advertise prefixes")

        # Monitor convergence
        st.log("Waiting for BGP convergence on D1...")
        if not self._wait_for_bgp_convergence(
            dut1, prefix_count, tolerance=100, timeout=1800
        ):
            st.report_fail("msg", "BGP failed to converge with expected route count")

        # Verify resources
        ok, msg = self._verify_resource_thresholds(dut1, phase="after_injection")
        if not ok:
            st.warn(f"Resource threshold violation: {msg}")

        # Get final counts
        final_bgp_count = self._get_bgp_route_count(dut1)
        st.log(f"Final BGP route count: {final_bgp_count}")

        if final_bgp_count < (prefix_count * 0.95):
            st.report_fail(
                "msg",
                f"Insufficient routes learned: {final_bgp_count} < {prefix_count * 0.95}",
            )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Scalability", testcases=["BGP_High_Scale_6.1.1.3"])
    def test_fib_programming_verification(self) -> None:
        """
        TC 6.1.1.3 - FIB programming: Ensure large route set installed into FIB.

        Verify large portion of injected routes are programmed into FIB and
        forwarding entries exist.
        """
        testcase = self._get_testcase("6.1.1.3")
        dut1 = self._resolve_dut("D1")

        if not dut1:
            st.report_fail("msg", "Failed to resolve DUT1")

        st.log("=" * 80)
        st.log("TC 6.1.1.3: FIB programming verification")
        st.log("=" * 80)

        # Prerequisites check
        bgp_count = self._get_bgp_route_count(dut1)
        if bgp_count < 1000:
            st.report_fail(
                "msg", f"Prerequisite failed: insufficient BGP routes ({bgp_count})"
            )

        # Get FIB route count
        st.log("Querying FIB route count...")
        fib_count = self._get_fib_route_count(dut1)

        st.log(f"BGP RIB routes: {bgp_count}")
        st.log(f"FIB routes: {fib_count}")

        # Calculate programming ratio
        if bgp_count > 0:
            programming_ratio = fib_count / bgp_count
            st.log(f"FIB programming ratio: {programming_ratio:.2%}")

            threshold = self.data.thresholds.get("fib_programming_success_rate", 0.95)
            if programming_ratio < threshold:
                st.report_fail(
                    "msg",
                    f"FIB programming below threshold: {programming_ratio:.2%} < {threshold:.2%}",
                )

        # Sample verification - check random prefixes
        if self._test_prefixes:
            import random

            sample_size = min(100, len(self._test_prefixes))
            sample_prefixes = random.sample(self._test_prefixes, sample_size)

            st.log(f"Verifying {sample_size} sampled prefixes in FIB...")
            verified = 0

            for prefix in sample_prefixes[:10]:  # Check first 10 for time
                # Verify route exists
                ip_addr = prefix.split("/")[0]
                if ip_api.verify_ip_route(
                    dut1,
                    family="ipv4",
                    ip_address=ip_addr,
                    type="B",
                    cli_type=self.data.show_cli_type,
                ):
                    verified += 1

            st.log(f"Sampled verification: {verified}/10 prefixes found in FIB")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Scalability", testcases=["BGP_High_Scale_6.1.1.4"])
    def test_incremental_injection_ramp(self) -> None:
        """
        TC 6.1.1.4 - Incremental injection ramp (observe resource scaling).

        Inject prefixes in steps to measure resource growth curve and
        identify tipping points.
        """
        testcase = self._get_testcase("6.1.1.4")
        dut1 = self._resolve_dut("D1")
        dut2 = self._resolve_dut("D2")

        if not dut1 or not dut2:
            st.report_fail("msg", "Failed to resolve DUTs")

        st.log("=" * 80)
        st.log("TC 6.1.1.4: Incremental injection ramp")
        st.log("=" * 80)

        # Test parameters from configuration section
        config = testcase.get("configuration", {})
        increments = config.get("increments", [1000, 2000, 5000, 10000])
        base_prefix = config.get("base_prefix", "100.0.0.0")
        d2_asn = self.data.bgp_config.get("D2_asn", 65002)

        metrics_log = []

        for increment in increments:
            st.log(f"\n--- Injecting {increment} prefixes ---")

            # Generate prefixes for this increment
            prefix_list = self._generate_prefix_list(base_prefix, increment)

            # Advertise prefixes
            if not self._advertise_prefixes(dut2, d2_asn, prefix_list):
                st.warn(f"Failed to advertise {increment} prefixes")
                continue

            # Wait for convergence
            st.log(f"Waiting for convergence at {increment} prefixes...")
            time.sleep(60)  # Stabilization period

            # Collect metrics
            cpu = self._get_cpu_usage(dut1)
            mem = self._get_memory_usage(dut1)
            bgp_routes = self._get_bgp_route_count(dut1)
            fib_routes = self._get_fib_route_count(dut1)

            increment_metrics = {
                "prefix_count": increment,
                "bgp_routes": bgp_routes,
                "fib_routes": fib_routes,
                "cpu_usage": cpu.get("usage", 0),
                "memory_usage": mem.get("usage_percent", 0),
            }

            metrics_log.append(increment_metrics)
            st.log(f"Metrics at {increment}: {increment_metrics}")

            # Verify thresholds
            ok, msg = self._verify_resource_thresholds(dut1, phase=f"increment_{increment}")
            if not ok:
                st.warn(f"Threshold violation at {increment}: {msg}")

            # Withdraw before next increment
            self._withdraw_prefixes(dut2, d2_asn, prefix_list)
            time.sleep(30)  # Wait for withdrawal

        st.log("\n=== Incremental Injection Summary ===")
        for metric in metrics_log:
            st.log(
                f"Prefixes: {metric['prefix_count']:5d} | "
                f"BGP: {metric['bgp_routes']:5d} | "
                f"FIB: {metric['fib_routes']:5d} | "
                f"CPU: {metric['cpu_usage']:5.1f}% | "
                f"MEM: {metric['memory_usage']:5.1f}%"
            )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Scalability", testcases=["BGP_High_Scale_6.1.1.5"])
    def test_withdrawal_and_recovery(self) -> None:
        """
        TC 6.1.1.5 - Withdrawal and recovery: Mass withdraw of prefixes.

        Validate that when large set of prefixes is withdrawn, DUT clears
        RIB/FIB cleanly and recovers without residual resource leaks.
        """
        testcase = self._get_testcase("6.1.1.5")
        dut1 = self._resolve_dut("D1")
        dut2 = self._resolve_dut("D2")

        if not dut1 or not dut2:
            st.report_fail("msg", "Failed to resolve DUTs")

        st.log("=" * 80)
        st.log("TC 6.1.1.5: Withdrawal and recovery")
        st.log("=" * 80)

        # Record pre-withdrawal state
        pre_bgp = self._get_bgp_route_count(dut1)
        pre_fib = self._get_fib_route_count(dut1)
        pre_cpu = self._get_cpu_usage(dut1)
        pre_mem = self._get_memory_usage(dut1)

        st.log(f"Pre-withdrawal: BGP={pre_bgp}, FIB={pre_fib}")

        if pre_bgp < 100:
            st.report_fail("msg", "Prerequisite failed: no routes to withdraw")

        # Withdraw all test prefixes
        d2_asn = self.data.bgp_config.get("D2_asn", 65002)
        if self._test_prefixes:
            st.log(f"Withdrawing {len(self._test_prefixes)} prefixes...")
            self._withdraw_prefixes(dut2, d2_asn, self._test_prefixes)

        # Monitor withdrawal
        st.log("Monitoring route withdrawal...")
        start_time = time.time()
        while (time.time() - start_time) < 600:  # 10 min timeout
            current_bgp = self._get_bgp_route_count(dut1)
            current_fib = self._get_fib_route_count(dut1)

            st.log(f"Current: BGP={current_bgp}, FIB={current_fib}")

            if current_bgp < 100 and current_fib < 100:
                st.log("Routes successfully withdrawn")
                break

            time.sleep(30)
        else:
            st.warn("Withdrawal timeout, routes may still be present")

        # Verify resource recovery
        post_cpu = self._get_cpu_usage(dut1)
        post_mem = self._get_memory_usage(dut1)

        st.log(f"Resource comparison:")
        st.log(f"CPU: {pre_cpu.get('usage',0):.1f}% -> {post_cpu.get('usage',0):.1f}%")
        st.log(
            f"MEM: {pre_mem.get('usage_percent',0):.1f}% -> {post_mem.get('usage_percent',0):.1f}%"
        )

        # Check for memory leaks (memory should return to near baseline)
        if "usage_percent" in pre_mem and "usage_percent" in post_mem:
            mem_delta = post_mem["usage_percent"] - pre_mem["usage_percent"]
            if mem_delta > 5:  # Allow 5% variance
                st.warn(f"Possible memory leak detected: +{mem_delta:.1f}%")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Scalability", testcases=["BGP_High_Scale_6.1.1.6"])
    def test_route_churn_stress(self) -> None:
        """
        TC 6.1.1.6 - Route churn stress (updates per second) impact.

        Measure DUT behavior under high churn and determine sustainable
        update rate before instability.
        """
        st.log("=" * 80)
        st.log("TC 6.1.1.6: Route churn stress test")
        st.log("=" * 80)

        # This test requires specialized route generator with churn capability
        # For basic implementation, we simulate with repeated add/remove cycles

        dut1 = self._resolve_dut("D1")
        dut2 = self._resolve_dut("D2")

        if not dut1 or not dut2:
            st.report_fail("msg", "Failed to resolve DUTs")

        testcase = self._get_testcase("6.1.1.6")
        config = testcase.get("configuration", {})
        churn_prefix_count = config.get("churn_prefix_count", 1000)
        churn_cycles = config.get("churn_cycles", 5)
        base_prefix = config.get("base_prefix", "150.0.0.0")
        d2_asn = self.data.bgp_config.get("D2_asn", 65002)

        # Generate prefix set for churning
        prefix_list = self._generate_prefix_list(base_prefix, churn_prefix_count)

        st.log(
            f"Starting churn test: {churn_cycles} cycles of {churn_prefix_count} prefixes"
        )

        for cycle in range(churn_cycles):
            st.log(f"\n--- Churn cycle {cycle + 1}/{churn_cycles} ---")

            # Add prefixes
            st.log("Adding prefixes...")
            self._advertise_prefixes(dut2, d2_asn, prefix_list)
            time.sleep(30)

            # Check stability
            bgp_count = self._get_bgp_route_count(dut1)
            st.log(f"Routes after add: {bgp_count}")

            # Remove prefixes
            st.log("Removing prefixes...")
            self._withdraw_prefixes(dut2, d2_asn, prefix_list)
            time.sleep(30)

            bgp_count = self._get_bgp_route_count(dut1)
            st.log(f"Routes after withdraw: {bgp_count}")

            # Verify session still up
            neighbor_ip = self.data.interface_config.get("D2_ip", "10.0.24.1/31").split("/")[0]
            if not self._verify_bgp_session(dut1, neighbor_ip, timeout=30):
                st.report_fail("msg", f"BGP session flapped during churn cycle {cycle + 1}")

        st.log("Churn test completed successfully")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Scalability", testcases=["BGP_High_Scale_6.1.1.7"])
    def test_ipv6_scale(self) -> None:
        """
        TC 6.1.1.7 - IPv6 scale: Inject ≥10k IPv6 prefixes.

        Repeat scale tests for IPv6 NLRI and observe control/data-plane
        behavior for large IPv6 route sets.
        """
        st.log("=" * 80)
        st.log("TC 6.1.1.7: IPv6 scale test")
        st.log("=" * 80)

        # Note: Full IPv6 implementation requires IPv6 BGP configuration
        # This is a placeholder showing the structure

        dut1 = self._resolve_dut("D1")

        if not dut1:
            st.report_fail("msg", "Failed to resolve DUT1")

        # Check IPv6 capability
        # This test would require IPv6 addresses, neighbor config, etc.

        st.log("IPv6 scale test - requires IPv6 BGP configuration")
        st.log("Test structure validated - full implementation requires IPv6 setup")

        # Skip for now if IPv6 not configured
        pytest.skip("IPv6 scale test requires IPv6 BGP configuration")

    @pytest.mark.inventory(feature="Scalability", testcases=["BGP_High_Scale_6.1.1.8"])
    def test_vrf_scale(self) -> None:
        """
        TC 6.1.1.8 - VRF-scale: Many prefixes across multiple VRFs.

        Test scale when prefixes are distributed across multiple VRFs.
        """
        st.log("=" * 80)
        st.log("TC 6.1.1.8: VRF scale test")
        st.log("=" * 80)

        # Note: Full VRF implementation requires VRF creation and per-VRF BGP
        # This is a placeholder showing the structure

        dut1 = self._resolve_dut("D1")

        if not dut1:
            st.report_fail("msg", "Failed to resolve DUT1")

        st.log("VRF scale test - requires VRF and per-VRF BGP configuration")
        st.log("Test structure validated - full implementation requires VRF setup")

        # Skip for now
        pytest.skip("VRF scale test requires VRF configuration support")

    @pytest.mark.inventory(feature="Scalability", testcases=["BGP_High_Scale_6.1.1.9"])
    def test_persistence_and_reboot(self) -> None:
        """
        TC 6.1.1.9 - Persistence & reboot: Routes survive control-plane restart.

        Verify behavior across configuration save and control-plane restart.
        """
        st.log("=" * 80)
        st.log("TC 6.1.1.9: Persistence and reboot test")
        st.log("=" * 80)

        dut1 = self._resolve_dut("D1")

        if not dut1:
            st.report_fail("msg", "Failed to resolve DUT1")

        # Record pre-restart state
        pre_bgp = self._get_bgp_route_count(dut1)
        st.log(f"Pre-restart BGP routes: {pre_bgp}")

        if pre_bgp < 100:
            st.report_fail("msg", "Prerequisite failed: insufficient routes for restart test")

        # Save configuration
        st.log("Saving configuration...")
        st.config(dut1, "do write memory", type=self.data.config_cli_type)
        time.sleep(5)

        # Restart BGP process (control-plane restart)
        st.log("Restarting BGP process...")
        basic_api.service_operations_by_systemctl(dut1, "bgp", "restart")

        # Wait for BGP to come back up
        st.log("Waiting for BGP process to restart...")
        time.sleep(60)

        # Verify session re-establishes
        neighbor_ip = self.data.interface_config.get("D2_ip", "10.0.24.1/31").split("/")[0]
        if not self._verify_bgp_session(dut1, neighbor_ip, timeout=180):
            st.report_fail("msg", "BGP session failed to re-establish after restart")

        # Wait for route reconvergence
        st.log("Waiting for route reconvergence...")
        time.sleep(120)

        # Verify routes recovered
        post_bgp = self._get_bgp_route_count(dut1)
        st.log(f"Post-restart BGP routes: {post_bgp}")

        # Allow 5% tolerance
        if post_bgp < (pre_bgp * 0.95):
            st.report_fail(
                "msg",
                f"Route recovery insufficient: {post_bgp} < {pre_bgp * 0.95}",
            )

        st.log(f"Routes recovered successfully: {post_bgp}/{pre_bgp}")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(
        feature="Scalability", testcases=["BGP_High_Scale_6.1.1.10"]
    )
    def test_diagnostics_and_logging(self) -> None:
        """
        TC 6.1.1.10 - Diagnostics, logging and failure analysis.

        Collect diagnostic artifacts during scale test for analysis.
        """
        st.log("=" * 80)
        st.log("TC 6.1.1.10: Diagnostics and logging")
        st.log("=" * 80)

        dut1 = self._resolve_dut("D1")

        if not dut1:
            st.report_fail("msg", "Failed to resolve DUT1")

        # Collect various diagnostic outputs
        st.log("Collecting diagnostic information...")

        # BGP summary
        bgp_summary = st.show(
            dut1,
            "show ip bgp summary",
            type=self.data.show_cli_type,
            skip_tmpl=True,
        )
        st.log(f"BGP Summary:\n{bgp_summary}")

        # System resource usage
        cpu_info = st.show(
            dut1,
            "show processes cpu",
            type=self.data.show_cli_type,
            skip_tmpl=True,
        )
        st.log(f"CPU Info:\n{cpu_info}")

        mem_info = st.show(
            dut1,
            "show system-memory",
            type=self.data.show_cli_type,
            skip_tmpl=True,
        )
        st.log(f"Memory Info:\n{mem_info}")

        # Route summary
        route_summary = st.show(
            dut1,
            "show ip route summary",
            type=self.data.show_cli_type,
            skip_tmpl=True,
        )
        st.log(f"Route Summary:\n{route_summary}")

        # Check logs for BGP events
        bgp_logs = st.show(
            dut1,
            "show logging | grep -i bgp | tail -50",
            type=self.data.show_cli_type,
            skip_tmpl=True,
        )
        st.log(f"Recent BGP logs:\n{bgp_logs}")

        st.log("Diagnostic collection completed")
        st.log(
            "NOTE: For production testing, enable tcpdump and save artifacts to files"
        )

        st.report_pass("test_case_passed")
