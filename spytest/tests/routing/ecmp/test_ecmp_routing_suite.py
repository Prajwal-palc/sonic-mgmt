"""
ECMP ROUTING VALIDATION SUITE
Author: Athira
Copyright 2024, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  routing/ecmp/test_ecmp_routing_suite.py  \
  --logs-path ./logs/test_ecmp_routing_suite_$(date +%F_%H%M%S)  \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Template harness for building Equal-Cost Multi-Path (ECMP) routing test
  automation. The suite wires up reusable helpers to manage topology context,
  route programming, neighbor orchestration, and cleanup flows while delegating
  concrete testcase logic to project-specific implementations. Populate
  vars_ecmp.yaml and replace the placeholder test with plan-aligned coverage.

Pre-requisites:
  - Topology: t0/t1 | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - logical 4 node fabric
        # +-----------+      +-----------+      +-----------+
        # |  TG Port  |------|    D1     |======|   Peers   |
        # +-----------+      +-----------+      +-----------+
        #           traffic (src/dst)      ECMP next hops (static/OSPF/BGP)
  - Feature flags / min SONiC version (if any)
  - Required test variables (YAML): defaults.cli_type, defaults.verify_timeout,
    defaults.cleanup, defaults.min_topology, testcase metadata (optional)
"""

# Template scaffolding for ECMP routing scenarios.

from __future__ import annotations

import re
from collections.abc import Iterable as IterableCollection
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterable, List, Mapping, Sequence

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api

VAR_FILE_ENV = "ECMP_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "routing"
    / "ecmp"
    / "vars_ecmp.yaml"
)


def _load_yaml_data() -> SpyTestDict:
    """Load testcase metadata from YAML with optional environment override."""

    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"ECMP variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    if "testcases" not in payload:
        raise ValueError("ECMP YAML must contain key 'testcases'")

    return SpyTestDict(payload)


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases (D1, D2, ...) discovered in the topology map."""

    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestEcmpRoutingSuite:
    """SpyTest ECMP validation suite spanning static, OSPF, and BGP workflows."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase definitions for the ECMP suite."""

        config = _load_yaml_data()
        defaults = SpyTestDict(config.get("defaults", {}))

        original_links = list(defaults.get("min_topology") or [])
        sanitized_links = cls._filter_traffic_generator_links(original_links)
        if original_links and sanitized_links != original_links:
            removed = [link for link in original_links if link not in sanitized_links]
            st.log(
                "Filtered traffic generator dependencies from topology requirements: %s"
                % removed
            )
        if not sanitized_links:
            sanitized_links = ["D1D2:1"]
        defaults["min_topology"] = sanitized_links

        topology = st.ensure_min_topology(*sanitized_links)

        cls.data.config = config
        cls.data.defaults = defaults
        cls.data.topology = topology
        cls.data.testcases = SpyTestDict(config.get("testcases", {}))

        matrix = cls._normalize_cli_types(defaults.get("cli_type"))
        cls.data.cli_matrix = tuple(matrix or ["click", "klish"])
        cls.data.cli_type = cls.data.cli_matrix[0]
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 60))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))
        cls.data.dut_map = SpyTestDict()
        cls.data.dut_names = tuple(st.get_dut_names())

        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.suite_cleanups: List[Callable[[], None]] = []

    @classmethod
    def teardown_class(cls) -> None:
        """Perform best-effort cleanup after suite execution."""

        if not cls.data.get("cleanup_enabled", True):
            st.log("ECMP cleanup skipped as per defaults.cleanup flag")
            return

        while cls.data.suite_cleanups:
            callback = cls.data.suite_cleanups.pop()
            try:
                callback()
            except Exception as error:  # pylint: disable=broad-except
                st.warn(f"Suite cleanup failed: {error}")

        for dut in cls.data.get("dut_names", []):
            try:
                ip_api.clear_static_route(dut)
            except Exception as error:  # pylint: disable=broad-except
                st.warn(f"Failed to clear static routes on {dut}: {error}")

        for dut in cls.data.get("dut_names", []):
            try:
                bgp_api.clear_bgp(dut)
            except Exception as error:  # pylint: disable=broad-except
                st.warn(f"Failed to reset BGP on {dut}: {error}")

    def setup_method(self) -> None:  # pylint: disable=no-self-use
        """Initialize per-test cleanup stack."""

        self._test_cleanups: List[Callable[[], None]] = []

    def teardown_method(self) -> None:
        """Invoke cleanup callbacks registered by the testcase."""

        while self._test_cleanups:
            callback = self._test_cleanups.pop()
            try:
                callback()
            except Exception as error:  # pylint: disable=broad-except
                st.warn(f"Test cleanup failed: {error}")

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_cli_types(raw: Any) -> List[str]:
        """Return a normalized CLI type matrix supporting click and klish."""

        if raw is None:
            return ["click", "klish"]
        if isinstance(raw, str):
            candidates = [segment.strip().lower() for segment in raw.replace(",", " ").split() if segment.strip()]
        elif isinstance(raw, IterableCollection):
            candidates: List[str] = []
            for item in raw:
                if item is None:
                    continue
                if isinstance(item, str):
                    parts = [segment.strip().lower() for segment in item.replace(",", " ").split() if segment.strip()]
                    candidates.extend(parts)
                else:
                    candidates.append(str(item).lower())
        else:
            candidates = [str(raw).lower()]

        deduped: List[str] = []
        for entry in candidates:
            if entry and entry not in deduped:
                deduped.append(entry)
        return deduped or ["click", "klish"]

    def _iter_cli_types(self, override: Any = None) -> Sequence[str]:
        """Yield CLI types for a block, defaulting to the class matrix."""

        if override is None:
            return self.data.cli_matrix
        normalized = self._normalize_cli_types(override)
        return tuple(normalized or self.data.cli_matrix)

    def _register_cleanup(self, callback: Callable[[], None], scope: str = "test") -> None:
        """Register cleanup callback at test or suite scope."""

        if scope == "suite":
            self.data.suite_cleanups.append(callback)
        else:
            self._test_cleanups.append(callback)

    def _resolve_dut_alias(self, alias: str, default: str | None = None) -> str:
        """Translate DUT alias to actual SpyTest handle."""

        if alias in self.data.dut_map:
            return self.data.dut_map[alias]

        if default:
            return default

        if self.data.dut_names:
            return self.data.dut_names[0]

        raise RuntimeError("No DUT handles discovered for ECMP suite")

    def _resolve_port(self, alias: str | None) -> str | None:
        """Translate topology alias to concrete port name."""

        if alias is None:
            return None

        topology = self.data.topology
        if hasattr(topology, alias):
            return getattr(topology, alias)
        return alias

    def _require_testcase(self, testcase_id: str) -> SpyTestDict:
        """Fetch testcase metadata or skip if undefined."""

        metadata = self.data.testcases.get(testcase_id)
        if not metadata:
            pytest.skip(f"Testcase {testcase_id} not defined in vars_ecmp.yaml")
        return SpyTestDict(metadata)

    def _log_testcase_banner(self, testcase_id: str, metadata: Mapping[str, Any]) -> None:
        st.banner(
            f"ECMP Testcase {testcase_id}: {metadata.get('name', 'Unnamed')} | "
            f"Objective: {metadata.get('objective', 'n/a')}"
        )

    def _validate_topology(self, metadata: Mapping[str, Any]) -> None:
        required_links = metadata.get("topology") or []
        available_links = set(self.data.defaults.get("min_topology", []))
        missing = [link for link in required_links if link not in available_links]
        if missing:
            st.warn(
                "Requested topology links %s not covered by defaults.min_topology; "
                "ensure testbed YAML provides them" % missing
            )

    def _log_steps_and_validations(self, metadata: Mapping[str, Any]) -> None:
        steps = metadata.get("steps", [])
        validations = metadata.get("validations", [])

        if steps:
            st.log("Planned Steps:")
        for index, step in enumerate(steps, 1):
            st.log(f"  Step {index}: {step}")

        if validations:
            st.log("Expected Validations:")
        for index, validation in enumerate(validations, 1):
            st.log(f"  Validation {index}: {validation}")

    def _skip_if_manual(self, metadata: Mapping[str, Any], testcase_id: str) -> None:
        if not metadata.get("automated", True):
            pytest.skip(
                f"Testcase {testcase_id} is marked manual in vars_ecmp.yaml"
            )

    @staticmethod
    def _filter_traffic_generator_links(links: Iterable[Any]) -> List[str]:
        """Remove traffic generator connections from topology description."""

        sanitized: List[str] = []
        for entry in links or []:
            if entry is None:
                continue
            text = str(entry)
            alias = text.split(":", 1)[0]
            alias_upper = alias.upper()
            if re.match(r"^D\d+T\d+", alias_upper):
                continue
            sanitized.append(text)
        return sanitized

    @staticmethod
    def _family_from_prefix(prefix: str | None) -> str:
        """Derive IP family from a route prefix string."""

        if not prefix:
            return "ipv4"
        return "ipv6" if ":" in prefix else "ipv4"

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------

    def _apply_static_routes(self, metadata: Mapping[str, Any]) -> None:
        route_block = SpyTestDict(metadata.get("routes", {}))
        prefix = route_block.get("prefix")
        next_hops = route_block.get("next_hops") or []

        if not prefix or not next_hops:
            pytest.skip("Static route definitions missing in vars_ecmp.yaml")

        dut = self._resolve_dut_alias("D1")

        for hop in next_hops:
            hop_dict = SpyTestDict(hop)
            gateway = hop_dict.get("gateway")
            alias = hop_dict.get("alias")
            interface = self._resolve_port(alias)

            if not gateway:
                st.warn("Skipping static route next-hop with no gateway defined")
                continue

            for cli_type in self._iter_cli_types(hop_dict.get("cli_type")):
                st.log(
                    f"Programming static route {prefix} via {gateway} (alias {alias}) "
                    f"using CLI {cli_type}"
                )
                ip_api.config_static_route(
                    dut,
                    next_hop=gateway,
                    route=prefix,
                    cli_type=cli_type,
                    interface=interface,
                    config="add",
                )

                self._register_cleanup(
                    lambda d=dut, nh=gateway, p=prefix, iface=interface, cli=cli_type: ip_api.config_static_route(
                        d,
                        next_hop=nh,
                        route=p,
                        cli_type=cli,
                        interface=iface,
                        config="del",
                    )
                )

    def _configure_bgp_neighbors(self, metadata: Mapping[str, Any]) -> None:
        settings = SpyTestDict(metadata.get("bgp_settings", {}))
        local_as = settings.get("local_as")
        peer_groups = settings.get("peer_groups") or []

        if not local_as or not peer_groups:
            pytest.skip("Incomplete BGP settings in vars_ecmp.yaml")

        dut = self._resolve_dut_alias("D1")

        for peer in peer_groups:
            peer_dict = SpyTestDict(peer)
            neighbor = peer_dict.get("neighbor")
            remote_as = peer_dict.get("remote_as")

            if not neighbor or not remote_as:
                st.warn("Skipping BGP peer with incomplete neighbor/AS info")
                continue

            st.log(
                f"Configuring BGP neighbor {neighbor} (remote AS {remote_as})"
            )
            bgp_api.config_bgp_neighbor(
                dut,
                local_as=local_as,
                neighbor=neighbor,
                remote_as=remote_as,
                config="yes",
            )

            self._register_cleanup(
                lambda d=dut, las=local_as, nbr=neighbor: bgp_api.config_bgp_neighbor(
                    d,
                    local_as=las,
                    neighbor=nbr,
                    config="no",
                )
            )

        for prefix in settings.get("prefixes") or []:
            st.log(f"Advertising network {prefix} from DUT {dut}")
            bgp_api.config_bgp_network_advertise(
                dut,
                local_as=local_as,
                network=prefix,
                config="yes",
            )

            self._register_cleanup(
                lambda d=dut, las=local_as, net=prefix: bgp_api.config_bgp_network_advertise(
                    d,
                    local_as=las,
                    network=net,
                    config="no",
                )
            )

    @contextmanager
    def _suspend_interface(self, alias: str | None, wait_sec: int) -> Iterable[None]:
        """Context manager placeholder to simulate failover events."""

        if not alias:
            yield
            return

        port = self._resolve_port(alias)
        st.log(f"Simulating link down on {port} (alias {alias}) for {wait_sec}s")
        try:
            yield
        finally:
            st.log(f"Restoring interface {port} (alias {alias}) after failover window")

    def _log_skipped_traffic_generator(self, metadata: Mapping[str, Any]) -> None:
        """Note that traffic generator metadata is ignored by the testcase."""

        streams = metadata.get("traffic_streams") or []
        if streams:
            st.warn(
                "Traffic generator definitions present in vars_ecmp.yaml are ignored "
                "for this test execution"
            )

    def _verify_static_route_installation(self, metadata: Mapping[str, Any]) -> None:
        """Ensure configured static ECMP routes are installed on the DUT."""

        route_block = SpyTestDict(metadata.get("routes", {}))
        prefix = route_block.get("prefix")
        next_hops = [SpyTestDict(item) for item in route_block.get("next_hops") or []]

        if not prefix or not next_hops:
            pytest.skip("Static route definitions missing in vars_ecmp.yaml")

        dut = self._resolve_dut_alias("D1")
        family = self._family_from_prefix(prefix)

        failures: List[str] = []
        for hop in next_hops:
            gateway = hop.get("gateway")
            if not gateway:
                continue
            for cli_type in self._iter_cli_types(hop.get("cli_type")):
                st.log(
                    f"Verifying ECMP static route {prefix} via {gateway} on {dut} "
                    f"using CLI {cli_type}"
                )
                if not ip_api.verify_ip_route(
                    dut,
                    family=family,
                    ip_address=prefix,
                    type="S",
                    nexthop=gateway,
                    cli_type=cli_type,
                ):
                    failures.append(f"{gateway} (cli {cli_type})")

        if failures:
            details = ", ".join(failures)
            pytest.fail(
                f"Static ECMP route {prefix} missing expected next-hops: {details}"
            )

    # ------------------------------------------------------------------
    # Template placeholder
    # ------------------------------------------------------------------

    def test_static_ecmp_without_traffic_generator(self) -> None:
        """Validate static ECMP routing without requiring a traffic generator."""

        testcase_id = "2.4.1"
        metadata = self._require_testcase(testcase_id)
        self._skip_if_manual(metadata, testcase_id)
        self._log_testcase_banner(testcase_id, metadata)
        self._validate_topology(metadata)
        self._log_steps_and_validations(metadata)
        self._log_skipped_traffic_generator(metadata)

        self._apply_static_routes(metadata)
        self._verify_static_route_installation(metadata)

        failover = SpyTestDict(metadata.get("failover_action", {}))
        alias = failover.get("alias")
        wait_sec = int(failover.get("wait_sec", 0) or 0)

        with self._suspend_interface(alias, wait_sec):
            st.log("Failover simulation complete without traffic generator involvement")

        self._verify_static_route_installation(metadata)

