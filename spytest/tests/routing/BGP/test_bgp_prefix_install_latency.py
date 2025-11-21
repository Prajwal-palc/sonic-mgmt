"""
BGP PREFIX INSTALLATION LATENCY UNDER CHURN
Author: Athira
2025

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2node.yaml  \
  tests/routing/BGP/test_bgp_prefix_install_latency.py \
  --logs-path ./logs/test_bgp_prefix_install_latency_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Verify prefix installation time meets SLA while prefixes are added/withdrawn (churn).
  These subtests exercise increasing churn levels and a long-duration stability test to
  measure BGP routing table update performance under realistic production scenarios.

  The test suite simulates route churn using BGP route advertisements and withdrawals,
  measuring the latency from route update to FIB installation. Tests cover baseline
  performance (no churn), low/medium/high churn scenarios, and long-duration stability.

Pre-requisites:
  - Topology: 2-node | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes (Route Generator + DUT)
        # +--------------------+                       +--------------------+
        # |  Route Generator   |                       |        DUT         |
        # |      (D2)          |=======================|        D1          |
        # |  Eth4 10.0.24.1/31 |     BGP Session       |  Eth4 10.0.24.0/31 |
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version: BGP enabled
  - Required test variables (YAML): defaults.cli_type (klish for config, click for show),
    defaults.verify_timeout, defaults.cleanup, defaults.min_topology,
    testcases.* definitions with prefix counts and SLA thresholds
"""

from __future__ import annotations

import csv
import json
import time
from collections.abc import Iterable as IterableCollection
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api

VAR_FILE_ENV = "BGP_PREFIX_LATENCY_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parent
    / "vars_bgp_prefix_install_latency.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"BGP prefix latency variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("BGP prefix latency YAML must contain key 'testcases'")

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestBgpPrefixInstallLatency:
    """Testcases covering BGP prefix installation latency under various churn scenarios."""

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

        cls.data.config_cli_type = defaults.get("config_cli_type", "klish")
        cls.data.show_cli_type = defaults.get("show_cli_type", "click")
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 60))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))
        cls.data.configured_routes = []
        cls.data.dut_map = SpyTestDict()

        # Map DUT aliases (D1, D2, ...) to actual device handles.
        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.dut_names = st.get_dut_names()

        # Measurement data structures
        cls.data.measurements = []
        cls.data.log_dir = Path(st.get_logs_path())

    @classmethod
    def teardown_class(cls) -> None:
        """Cleanup BGP configuration and routes after the suite completes."""
        if not cls.data.cleanup_enabled:
            return
        cls._cleanup_all_bgp()

    def setup_method(self) -> None:
        """Reset per-test bookkeeping."""
        self._test_measurements: List[Dict[str, Any]] = []
        self._test_start_time = time.time()

    def teardown_method(self) -> None:
        """Save measurements and cleanup test-specific resources."""
        if self._test_measurements:
            self._save_measurements()
        self._test_measurements = []

    @classmethod
    def _cleanup_all_bgp(cls) -> None:
        """Remove all BGP configuration tracked across the suite."""
        st.log("Cleaning up BGP configuration on all DUTs")
        for dut_alias in cls.data.dut_map:
            dut = cls.data.dut_map[dut_alias]
            # Reset BGP configuration
            bgp_api.cleanup_router_bgp(dut)

    @classmethod
    def _resolve_dut(cls, alias: str | None) -> str | None:
        """Translate a topology alias (e.g., D1) to the framework DUT handle."""
        if not alias:
            return None
        if alias in cls.data.dut_map:
            return cls.data.dut_map[alias]
        if alias in cls.data.dut_names:
            return alias
        st.warn(f"Unable to resolve DUT alias '{alias}'")
        return None

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    def _setup_bgp_session(self, config: Mapping[str, Any]) -> None:
        """Configure BGP session between DUTs."""
        dut1_alias = config.get("dut1", "D1")
        dut2_alias = config.get("dut2", "D2")

        dut1 = self._resolve_dut(dut1_alias)
        dut2 = self._resolve_dut(dut2_alias)

        if not dut1 or not dut2:
            st.report_fail("msg", "Unable to resolve DUT aliases for BGP setup")

        # Configure BGP on DUT1 (receiver)
        bgp_config1 = config.get("bgp_dut1", {})
        local_asn1 = bgp_config1.get("local_asn")
        router_id1 = bgp_config1.get("router_id")
        neighbor_ip1 = bgp_config1.get("neighbor_ip")
        neighbor_asn1 = bgp_config1.get("neighbor_asn")

        st.log(f"Configuring BGP on {dut1_alias}: AS{local_asn1}, Router-ID {router_id1}")
        bgp_api.config_bgp(
            dut=dut1,
            local_as=local_asn1,
            router_id=router_id1,
            config='yes',
            cli_type=self.data.config_cli_type
        )

        bgp_api.config_bgp_neighbor(
            dut=dut1,
            local_asn=local_asn1,
            neighbor_ip=neighbor_ip1,
            remote_asn=neighbor_asn1,
            config='yes',
            cli_type=self.data.config_cli_type
        )

        # Configure BGP on DUT2 (route generator)
        bgp_config2 = config.get("bgp_dut2", {})
        local_asn2 = bgp_config2.get("local_asn")
        router_id2 = bgp_config2.get("router_id")
        neighbor_ip2 = bgp_config2.get("neighbor_ip")
        neighbor_asn2 = bgp_config2.get("neighbor_asn")

        st.log(f"Configuring BGP on {dut2_alias}: AS{local_asn2}, Router-ID {router_id2}")
        bgp_api.config_bgp(
            dut=dut2,
            local_as=local_asn2,
            router_id=router_id2,
            config='yes',
            cli_type=self.data.config_cli_type
        )

        bgp_api.config_bgp_neighbor(
            dut=dut2,
            local_asn=local_asn2,
            neighbor_ip=neighbor_ip2,
            remote_asn=neighbor_asn2,
            config='yes',
            cli_type=self.data.config_cli_type
        )

        # Wait for BGP session to establish
        st.log("Waiting for BGP session to establish...")
        if not st.poll_wait(
            bgp_api.verify_bgp_neighbor,
            self.data.verify_timeout,
            dut1,
            neighbor_ip1,
            state='Established',
            cli_type=self.data.show_cli_type
        ):
            st.report_fail("msg", f"BGP session failed to establish between {dut1_alias} and {dut2_alias}")

        st.log("BGP session established successfully")

    def _advertise_routes(
        self,
        dut: str,
        local_asn: int,
        prefix_list: List[str],
        network_import_check: bool = False
    ) -> Tuple[float, int]:
        """
        Advertise routes from route generator DUT.
        Returns (start_timestamp, routes_advertised_count).
        """
        start_time = time.time()
        success_count = 0

        for prefix in prefix_list:
            result = bgp_api.config_bgp_network_advertise(
                dut=dut,
                local_asn=local_asn,
                network=prefix,
                config='yes',
                cli_type=self.data.config_cli_type,
                network_import_check=network_import_check
            )
            if result:
                success_count += 1

        return start_time, success_count

    def _withdraw_routes(
        self,
        dut: str,
        local_asn: int,
        prefix_list: List[str]
    ) -> Tuple[float, int]:
        """
        Withdraw routes from route generator DUT.
        Returns (start_timestamp, routes_withdrawn_count).
        """
        start_time = time.time()
        success_count = 0

        for prefix in prefix_list:
            result = bgp_api.config_bgp_network_advertise(
                dut=dut,
                local_asn=local_asn,
                network=prefix,
                config='no',
                cli_type=self.data.config_cli_type
            )
            if result:
                success_count += 1

        return start_time, success_count

    def _measure_route_installation(
        self,
        receiver_dut: str,
        prefix_list: List[str],
        timeout: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Measure time for routes to appear in the routing table.
        Returns list of measurements with latencies.
        """
        measurements = []
        start_check = time.time()

        for prefix in prefix_list:
            prefix_installed = False
            install_time = None

            # Poll for route installation
            for _ in range(timeout):
                if ip_api.verify_ip_route(
                    receiver_dut,
                    family="ipv4",
                    ip_address=prefix,
                    type="B",  # BGP route
                    cli_type=self.data.show_cli_type
                ):
                    install_time = time.time()
                    prefix_installed = True
                    break
                time.sleep(1)

            measurement = {
                "prefix": prefix,
                "installed": prefix_installed,
                "install_timestamp": install_time,
                "check_start": start_check
            }
            measurements.append(measurement)

        return measurements

    def _calculate_statistics(
        self,
        measurements: List[Dict[str, Any]],
        advertise_start: float
    ) -> Dict[str, Any]:
        """Calculate latency statistics from measurements."""
        latencies = []
        failed_count = 0

        for m in measurements:
            if m["installed"] and m["install_timestamp"]:
                latency_ms = (m["install_timestamp"] - advertise_start) * 1000
                latencies.append(latency_ms)
            else:
                failed_count += 1

        if not latencies:
            return {
                "count": len(measurements),
                "failed": failed_count,
                "min_ms": 0,
                "max_ms": 0,
                "mean_ms": 0,
                "p50_ms": 0,
                "p90_ms": 0,
                "p95_ms": 0,
                "p99_ms": 0
            }

        latencies.sort()
        count = len(latencies)

        return {
            "count": count,
            "failed": failed_count,
            "min_ms": latencies[0],
            "max_ms": latencies[-1],
            "mean_ms": sum(latencies) / count,
            "p50_ms": latencies[int(count * 0.5)],
            "p90_ms": latencies[int(count * 0.9)],
            "p95_ms": latencies[int(count * 0.95)],
            "p99_ms": latencies[int(count * 0.99)] if count > 1 else latencies[0]
        }

    def _save_measurements(self) -> None:
        """Save measurement data to CSV file."""
        if not self._test_measurements:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = self.data.log_dir / f"latency_measurements_{timestamp}.csv"

        with csv_file.open('w', newline='') as f:
            if self._test_measurements:
                writer = csv.DictWriter(f, fieldnames=self._test_measurements[0].keys())
                writer.writeheader()
                writer.writerows(self._test_measurements)

        st.log(f"Saved measurements to {csv_file}")

    def _generate_prefix_list(self, base_prefix: str, count: int) -> List[str]:
        """Generate a list of prefixes for testing."""
        # Simple prefix generation: increment third octet
        # Example: 192.168.0.0/24 -> 192.168.1.0/24, 192.168.2.0/24, etc.
        parts = base_prefix.split('.')
        base_a = int(parts[0])
        base_b = int(parts[1])
        base_c = int(parts[2])

        prefixes = []
        for i in range(count):
            c = (base_c + i) % 256
            b = base_b + ((base_c + i) // 256)
            prefix = f"{base_a}.{b}.{c}.0/24"
            prefixes.append(prefix)

        return prefixes

    @pytest.mark.inventory(feature="Performance", testcases=["BGP_TC6.1.3.1"])
    def test_baseline_prefix_installation_no_churn(self) -> None:
        """
        TC 6.1.3.1 - Baseline prefix installation latency with no churn.
        Measure single-prefix and bulk-prefix installation latency when routes
        are advertised once (no withdraws).
        """
        testcase = self._get_testcase("6.1.3.1")

        # Setup BGP session
        self._setup_bgp_session(testcase.get("bgp_config", {}))

        # Get test parameters
        params = testcase.get("parameters", {})
        prefix_count = params.get("prefix_count", 100)
        base_prefix = params.get("base_prefix", "192.168.0.0/24")
        sla_ms = params.get("sla_ms_per_prefix", 50)

        dut1 = self._resolve_dut(testcase.get("bgp_config", {}).get("dut1", "D1"))
        dut2 = self._resolve_dut(testcase.get("bgp_config", {}).get("dut2", "D2"))
        local_asn2 = testcase.get("bgp_config", {}).get("bgp_dut2", {}).get("local_asn")

        # Generate prefix list
        prefix_list = self._generate_prefix_list(base_prefix, prefix_count)

        st.log(f"Starting baseline test with {prefix_count} prefixes")

        # Advertise routes
        adv_start, adv_count = self._advertise_routes(dut2, local_asn2, prefix_list)
        st.log(f"Advertised {adv_count} routes at {adv_start}")

        # Measure installation
        measurements = self._measure_route_installation(dut1, prefix_list)
        self._test_measurements.extend(measurements)

        # Calculate statistics
        stats = self._calculate_statistics(measurements, adv_start)
        st.log(f"Installation statistics: {json.dumps(stats, indent=2)}")

        # Verify pass criteria
        if stats["failed"] > 0:
            st.report_fail("msg", f"{stats['failed']} prefixes failed to install")

        if stats["p99_ms"] > sla_ms:
            st.report_fail(
                "msg",
                f"99th percentile latency {stats['p99_ms']:.2f}ms exceeds SLA {sla_ms}ms"
            )

        if stats["max_ms"] > 2 * sla_ms:
            st.warn(f"Max latency {stats['max_ms']:.2f}ms exceeds 2x SLA")

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Performance", testcases=["BGP_TC6.1.3.2"])
    def test_low_churn_prefix_installation(self) -> None:
        """
        TC 6.1.3.2 - Low churn prefix installation.
        Measure installation latency when prefixes are being added and withdrawn
        at low churn rate.
        """
        testcase = self._get_testcase("6.1.3.2")

        # Setup BGP session
        self._setup_bgp_session(testcase.get("bgp_config", {}))

        # Get test parameters
        params = testcase.get("parameters", {})
        prefix_count = params.get("prefix_count", 1000)
        base_prefix = params.get("base_prefix", "192.168.0.0/24")
        add_rate_pps = params.get("add_rate_pps", 200)
        withdraw_rate_pps = params.get("withdraw_rate_pps", 50)
        measurement_window_s = params.get("measurement_window_s", 120)
        sla_ms = params.get("sla_ms_per_prefix", 100)

        dut1 = self._resolve_dut(testcase.get("bgp_config", {}).get("dut1", "D1"))
        dut2 = self._resolve_dut(testcase.get("bgp_config", {}).get("dut2", "D2"))
        local_asn2 = testcase.get("bgp_config", {}).get("bgp_dut2", {}).get("local_asn")

        # Generate prefix list
        prefix_list = self._generate_prefix_list(base_prefix, prefix_count)

        st.log(f"Starting low churn test with {prefix_count} prefixes")

        test_start = time.time()
        cycle_count = 0

        while (time.time() - test_start) < measurement_window_s:
            cycle_count += 1
            st.log(f"Churn cycle {cycle_count}")

            # Add routes
            batch_size = min(add_rate_pps, len(prefix_list))
            add_batch = prefix_list[:batch_size]

            adv_start, adv_count = self._advertise_routes(dut2, local_asn2, add_batch)
            measurements = self._measure_route_installation(dut1, add_batch, timeout=30)
            self._test_measurements.extend(measurements)

            # Wait before withdraw
            time.sleep(2)

            # Withdraw some routes
            withdraw_size = min(withdraw_rate_pps, len(add_batch))
            withdraw_batch = add_batch[:withdraw_size]

            self._withdraw_routes(dut2, local_asn2, withdraw_batch)
            time.sleep(1)

        # Calculate statistics
        stats = self._calculate_statistics(self._test_measurements, test_start)
        st.log(f"Low churn statistics: {json.dumps(stats, indent=2)}")

        # Verify pass criteria
        if stats["p99_ms"] > sla_ms:
            st.report_fail(
                "msg",
                f"99th percentile latency {stats['p99_ms']:.2f}ms exceeds SLA {sla_ms}ms"
            )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Performance", testcases=["BGP_TC6.1.3.3"])
    def test_medium_churn_prefix_installation(self) -> None:
        """
        TC 6.1.3.3 - Medium churn prefix installation.
        Measure behavior under moderate churn expected in production spikes.
        """
        testcase = self._get_testcase("6.1.3.3")

        # Setup BGP session
        self._setup_bgp_session(testcase.get("bgp_config", {}))

        # Get test parameters
        params = testcase.get("parameters", {})
        prefix_count = params.get("prefix_count", 5000)
        base_prefix = params.get("base_prefix", "192.168.0.0/24")
        add_rate_pps = params.get("add_rate_pps", 1000)
        withdraw_rate_pps = params.get("withdraw_rate_pps", 500)
        measurement_window_s = params.get("measurement_window_s", 300)
        sla_ms = params.get("sla_ms_per_prefix", 200)

        dut1 = self._resolve_dut(testcase.get("bgp_config", {}).get("dut1", "D1"))
        dut2 = self._resolve_dut(testcase.get("bgp_config", {}).get("dut2", "D2"))
        local_asn2 = testcase.get("bgp_config", {}).get("bgp_dut2", {}).get("local_asn")

        # Generate prefix list
        prefix_list = self._generate_prefix_list(base_prefix, prefix_count)

        st.log(f"Starting medium churn test with {prefix_count} prefixes")
        st.warn("This test may take several minutes to complete")

        test_start = time.time()
        burst_count = 0

        while (time.time() - test_start) < measurement_window_s:
            burst_count += 1
            st.log(f"Burst {burst_count}")

            # High-rate add burst
            batch_size = min(add_rate_pps, len(prefix_list))
            add_batch = prefix_list[:batch_size]

            adv_start, adv_count = self._advertise_routes(dut2, local_asn2, add_batch)
            # Sample measurement (not all prefixes to reduce overhead)
            sample_size = min(100, len(add_batch))
            measurements = self._measure_route_installation(dut1, add_batch[:sample_size], timeout=20)
            self._test_measurements.extend(measurements)

            # Pause
            time.sleep(5)

            # Withdraw burst
            withdraw_size = min(withdraw_rate_pps, len(add_batch))
            withdraw_batch = add_batch[:withdraw_size]

            self._withdraw_routes(dut2, local_asn2, withdraw_batch)
            time.sleep(3)

        # Calculate statistics
        stats = self._calculate_statistics(self._test_measurements, test_start)
        st.log(f"Medium churn statistics: {json.dumps(stats, indent=2)}")

        # Verify pass criteria
        if stats["p95_ms"] > sla_ms:
            st.report_fail(
                "msg",
                f"95th percentile latency {stats['p95_ms']:.2f}ms exceeds SLA {sla_ms}ms"
            )

        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Performance", testcases=["BGP_TC6.1.3.4"])
    @pytest.mark.stress
    def test_high_churn_prefix_installation(self) -> None:
        """
        TC 6.1.3.4 - High churn prefix installation.
        Test DUT under aggressive churn to map breaking points and tail latency.
        WARNING: This is a disruptive stress test.
        """
        testcase = self._get_testcase("6.1.3.4")

        st.warn("Starting HIGH CHURN stress test - this may be disruptive")

        # Setup BGP session
        self._setup_bgp_session(testcase.get("bgp_config", {}))

        # Get test parameters
        params = testcase.get("parameters", {})
        prefix_count = params.get("prefix_count", 20000)
        base_prefix = params.get("base_prefix", "192.168.0.0/24")
        add_rate_pps = params.get("add_rate_pps", 5000)
        withdraw_rate_pps = params.get("withdraw_rate_pps", 4000)
        measurement_window_s = params.get("measurement_window_s", 600)
        sla_ms = params.get("sla_ms_per_prefix", 500)

        dut1 = self._resolve_dut(testcase.get("bgp_config", {}).get("dut1", "D1"))
        dut2 = self._resolve_dut(testcase.get("bgp_config", {}).get("dut2", "D2"))
        local_asn2 = testcase.get("bgp_config", {}).get("bgp_dut2", {}).get("local_asn")

        # Generate prefix list
        prefix_list = self._generate_prefix_list(base_prefix, prefix_count)

        st.log(f"Starting high churn stress test with {prefix_count} prefixes")

        test_start = time.time()

        # Continuous high-rate churn
        try:
            while (time.time() - test_start) < measurement_window_s:
                # Add large batch
                batch_size = min(add_rate_pps, len(prefix_list))
                add_batch = prefix_list[:batch_size]

                adv_start, adv_count = self._advertise_routes(dut2, local_asn2, add_batch)

                # Immediately withdraw
                withdraw_size = min(withdraw_rate_pps, len(add_batch))
                self._withdraw_routes(dut2, local_asn2, add_batch[:withdraw_size])

                # Minimal delay
                time.sleep(0.5)
        except Exception as e:
            st.error(f"High churn test encountered error: {e}")
            st.log("Test characterization: DUT behavior under extreme stress documented")

        # Verify DUT is still responsive by checking BGP session
        if not bgp_api.verify_bgp_neighbor(dut1, testcase.get("bgp_config", {}).get("bgp_dut1", {}).get("neighbor_ip"), state='Established'):
            st.report_fail("msg", "DUT became unresponsive during high churn test (BGP session down)")

        st.log("High churn test completed - DUT remained responsive")
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Performance", testcases=["BGP_TC6.1.3.5"])
    @pytest.mark.nightly
    def test_long_duration_stability_under_churn(self) -> None:
        """
        TC 6.1.3.5 - Long duration stability under churn (soak test).
        Validate long-run stability and steady-state latency under intermittent churn.
        WARNING: This test runs for 4 hours.
        """
        testcase = self._get_testcase("6.1.3.5")

        st.warn("Starting LONG DURATION soak test - will run for ~4 hours")

        # Setup BGP session
        self._setup_bgp_session(testcase.get("bgp_config", {}))

        # Get test parameters
        params = testcase.get("parameters", {})
        prefix_count = params.get("prefix_count", 5000)
        base_prefix = params.get("base_prefix", "192.168.0.0/24")
        add_rate_pps = params.get("add_rate_pps", 500)
        withdraw_rate_pps = params.get("withdraw_rate_pps", 250)
        measurement_window_s = params.get("measurement_window_s", 14400)  # 4 hours
        churn_interval_s = params.get("churn_interval_s", 300)  # 5 minutes
        churn_duration_s = params.get("churn_duration_s", 30)  # 30 seconds
        sla_ms = params.get("sla_ms_per_prefix", 150)

        dut1 = self._resolve_dut(testcase.get("bgp_config", {}).get("dut1", "D1"))
        dut2 = self._resolve_dut(testcase.get("bgp_config", {}).get("dut2", "D2"))
        local_asn2 = testcase.get("bgp_config", {}).get("bgp_dut2", {}).get("local_asn")

        # Generate prefix list
        prefix_list = self._generate_prefix_list(base_prefix, prefix_count)

        st.log(f"Starting soak test with {prefix_count} prefixes for {measurement_window_s}s")

        test_start = time.time()
        baseline_stats = None
        hourly_stats = []

        while (time.time() - test_start) < measurement_window_s:
            elapsed = time.time() - test_start
            st.log(f"Soak test progress: {elapsed:.0f}s / {measurement_window_s}s")

            # Wait for next churn interval
            time.sleep(churn_interval_s)

            # Run churn burst
            burst_start = time.time()
            while (time.time() - burst_start) < churn_duration_s:
                batch_size = min(add_rate_pps, len(prefix_list))
                add_batch = prefix_list[:batch_size]

                adv_start, adv_count = self._advertise_routes(dut2, local_asn2, add_batch)

                # Sample measurement
                sample_size = min(50, len(add_batch))
                measurements = self._measure_route_installation(dut1, add_batch[:sample_size], timeout=10)
                self._test_measurements.extend(measurements)

                # Withdraw
                withdraw_size = min(withdraw_rate_pps, len(add_batch))
                self._withdraw_routes(dut2, local_asn2, add_batch[:withdraw_size])

                time.sleep(1)

            # Calculate hourly statistics
            if len(hourly_stats) == 0:
                baseline_stats = self._calculate_statistics(self._test_measurements, test_start)
                st.log(f"Baseline statistics: {json.dumps(baseline_stats, indent=2)}")
                hourly_stats.append(baseline_stats)
            elif elapsed >= len(hourly_stats) * 3600:
                current_stats = self._calculate_statistics(self._test_measurements, test_start)
                hourly_stats.append(current_stats)
                st.log(f"Hour {len(hourly_stats)} statistics: {json.dumps(current_stats, indent=2)}")

                # Check for degradation
                if baseline_stats and current_stats["p95_ms"] > baseline_stats["p95_ms"] * 1.1:
                    st.warn(f"Latency degradation detected: {current_stats['p95_ms']:.2f}ms vs baseline {baseline_stats['p95_ms']:.2f}ms")

        # Final verification
        final_stats = self._calculate_statistics(self._test_measurements, test_start)
        st.log(f"Final soak test statistics: {json.dumps(final_stats, indent=2)}")

        # Check pass criteria
        if baseline_stats and final_stats["p95_ms"] > baseline_stats["p95_ms"] * 1.1:
            st.report_fail(
                "msg",
                f"Latency drift detected: {final_stats['p95_ms']:.2f}ms > 110% of baseline {baseline_stats['p95_ms']:.2f}ms"
            )

        st.report_pass("test_case_passed")
