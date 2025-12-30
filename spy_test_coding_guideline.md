# SpyTest Coding Guideline for Codex (SONiC test scripts)

Use this as **input to Codex** to auto‑generate SpyTest test scripts and APIs for `sonic-mgmt` environments. The goal is reproducible, topology‑aware tests that work on **HW and Virtual**.

---

## 0) Scope & Feature → Path Mapping
Follow these rules to decide the **script path**. If a directory doesn’t exist, create it.

- **Routing features** → `spytest/tests/routing/<feature_name>/<test_meaningfulname>.py`
- **Switching features** → `spytest/tests/switching/<feature_name>/<test_meaningfulname>.py`
- **System features** (ntp, lldp, interface, reboot, sflow, snmp, device‑management, ssh, …) → `spytest/tests/system/<feature_name>/<test_meaningfulname>.py`
- **QoS & ACL** → `spytest/tests/qos/<test_name>.py` or `spytest/tests/qos/acl/<test_name>.py`

**Feature list (this project) → concrete subpaths**

| Feature | Category | Directory (create if absent) | Example file |
|---|---|---|---|
| Interface Events | system | `spytest/tests/system/interface_events/` | `test_interface_link_flap_events.py` |
| RoCEv2 support | qos | `spytest/tests/qos/rocev2/` | `test_rocev2_pfc_ecn.py` |
| LLDP | system | `spytest/tests/system/lldp/` | `test_lldp_neighbors_basic.py` |
| ECMP | routing | `spytest/tests/routing/ecmp/` | `test_ecmp_nexthops_hash.py` |
| OSPFv2 | routing | `spytest/tests/routing/ospfv2/` | `test_ospfv2_neighbor_states.py` |
| Static Routing | routing | `spytest/tests/routing/static/` | `test_static_route_basic.py` |
| IPv4 Unnumbered Interfaces | routing | `spytest/tests/routing/ipv4_unnumbered/` | `test_unnumbered_bgp_ospf_interop.py` |
| NTP Server & Auth | system | `spytest/tests/system/ntp/` | `test_ntp_server_auth.py` |

> **Naming**: always begin files with `test_<feature>.py`; keep names short, meaningful, and lower_snake_case.

---

## 1) Required Docstring Banner (top of every test script)
Add a module‑level docstring _banner_ that answers **what/why/how**:

```
"""
<FEATURE NAME>
Author: Athira
© <Current YEAR>, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  interface/test_intf_sample.py \
  --logs-path ./logs/test_intf_sample_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  <One‑paragraph summary of what this test does and key validations>

Pre‑requisites:
  - Topology: <t0/t1/any> | Supported: HW, Virtual, or Both
  - Topology Diagram : <Created based on the testbed yaml and test scenario>
  Example:
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        #|        dut1        |                       |        dut2        |
        #|  Eth4 10.0.24.1/31 |=======================|  Eth4 10.0.24.0/31 |
        #+--------------------+                       +--------------------+

  - Feature flags / min SONiC version (if any)
  - Required test variables (YAML): <list keys>
"""
```

---

## 2) Canonical Script Structure

1. **Filename**: `test_<feature>.py`
2. **Docstring**: as above.
3. **Imports**: stdlib, pytest, spytest libs, and **feature APIs** from `spytest/apis`.
4. **Globals / Helpers**: constants, regex, small helpers (pure functions only).
5. **Test Class**: `class Test<FeatureCamelCase>:` containing all tests and class‑level setup/teardown.
6. **Test Names**: `test_<short_meaningful_name>`
7. **Topology‑agnostic**: avoid hardcoding; read from YAML/inventory. Gate behavior with capability checks.
8. **YAML variables**: create and load via SpyTest utilities; do **not** embed test data in code.
9. **APIs**: CRUD/verify functions in `spytest/apis/<feature>/...`. Reuse existing APIs first; avoid breaking changes.

**Example skeleton**

```python
"""
STATIC IPV4 ROUTING

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  routing/static/test_static_ipv4_routes.py \
  --logs-path ./logs/test_static_ipv4_routes_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of IPv4 static routing CRUD operations using SpyTest APIs
  and the sonic-cli (klish) as well as legacy click/vtysh paths. The suite
  provisions static routes through next-hop IP, interface-qualified paths, and
  multi-prefix scenarios while ensuring clean teardown and negative gating. Each
  testcase consumes topology-aware variables from YAML to remain reusable across
  SONiC hardware and virtual environments.

Pre-requisites:
  - Topology: t0/t1 | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |        dut1        |                       |        dut2        |
        # |Eth4 198.51.100.0/24|=======================|  Eth4              |
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version (if any)
  - Required test variables (YAML): defaults.cli_type (click, klish),
    defaults.verify_timeout, defaults.cleanup, defaults.min_topology,
    testcases.* definitions
"""

# Testcases for IPv4 static route scenarios covering SpyTest plan 2.1.1–2.1.4.

from __future__ import annotations

from collections.abc import Iterable as IterableCollection
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api

VAR_FILE_ENV = "STATIC_IPV4_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "routing"
    / "static"
    / "vars_static_ipv4.yaml"
)


def _load_yaml_data() -> Dict[str, Any]:
    """Load testcase variables from YAML with optional environment override."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE

    if not candidate.is_file():
        raise FileNotFoundError(f"Static IPv4 variable file not found: {candidate}")

    with candidate.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle) or {}

    if "testcases" not in content:
        raise ValueError("Static IPv4 YAML must contain key 'testcases'")

    return content


def _iter_candidate_duts(topology: Mapping[str, Any]) -> Iterable[str]:
    """Yield DUT aliases discovered in the topology map."""
    for key, value in topology.items():
        if key.startswith("D") and value:
            yield key


@pytest.mark.topology("any")
class TestStaticIpv4Routes:
    """Testcases covering IPv4 static routing CRUD and negative validation."""

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
        matrix = cls._normalize_cli_types(defaults.get("cli_type"))
        if not matrix:
            matrix = ["click", "klish"]
        cls.data.cli_matrix = tuple(matrix)
        cls.data.cli_type = cls.data.cli_matrix[0]
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 30))
        cls.data.cleanup_enabled = bool(defaults.get("cleanup", True))
        cls.data.configured_routes = []
        cls.data.dut_map = SpyTestDict()

        # Map DUT aliases (D1, D2, ...) to actual device handles.
        for dut_alias in _iter_candidate_duts(topology):
            cls.data.dut_map[dut_alias] = getattr(topology, dut_alias)

        cls.data.dut_names = st.get_dut_names()

    @classmethod
    def teardown_class(cls) -> None:
        """Ensure all static routes are removed after the suite completes."""
        if not cls.data.cleanup_enabled:
            return
        cls._cleanup_all_routes()

    def setup_method(self) -> None:  # pylint: disable=no-self-use
        """Reset per-test bookkeeping."""
        self._test_routes: List[Mapping[str, Any]] = []

    def teardown_method(self) -> None:
        """Remove any static routes that the testcase configured."""
        if not self.data.cleanup_enabled:
            self._test_routes = []
            return
        while self._test_routes:
            route = self._test_routes.pop()
            self._remove_static_route(route)
            if route in self.data.configured_routes:
                self.data.configured_routes.remove(route)

    @classmethod
    def _cleanup_all_routes(cls) -> None:
        """Remove all routes tracked across the suite."""
        while cls.data.get("configured_routes"):
            route = cls.data.configured_routes.pop()
            cls._remove_static_route_static(route)

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

    def _iter_cli_types(self, override: Any = None) -> Iterable[str]:
        """Yield CLI types for a route, defaulting to the class matrix."""
        if override is None:
            matrix = list(self.data.cli_matrix)
        else:
            matrix = self._normalize_cli_types(override)
        if not matrix:
            matrix = list(self.data.cli_matrix)
        if not matrix:
            matrix = [self.data.cli_type]
        return tuple(matrix)

    @staticmethod
    def _prepare_route(template: Mapping[str, Any], cli_type: str) -> SpyTestDict:
        """Deep copy a route definition and stamp the CLI type."""
        prepared = SpyTestDict(deepcopy(dict(template)))
        prepared.cli_type = cli_type
        return prepared

    def _untrack_route(self, route: Mapping[str, Any]) -> None:
        """Remove a route from per-test and suite tracking collections."""
        if route in self._test_routes:
            self._test_routes.remove(route)
        if route in self.data.configured_routes:
            self.data.configured_routes.remove(route)

    @contextmanager
    def _static_route_context(self, route: Mapping[str, Any], persist: bool = False):
        """Context manager to configure and optionally auto-remove a route."""
        self._configure_static_route(route)
        try:
            yield route
        finally:
            if not persist:
                self._remove_static_route(route)
                self._untrack_route(route)

    def _collect_cli_union(self, *routes: Mapping[str, Any]) -> Iterable[str]:
        """Return the ordered union of CLI types referenced by the given routes."""
        union: List[str] = []
        for route in routes:
            for cli_type in self._iter_cli_types(route.get("cli_type") if route else None):
                if cli_type not in union:
                    union.append(cli_type)
        if not union:
            union.extend(list(self._iter_cli_types()))
        return tuple(union)

    def _collect_routes_for_cli(
        self, routes: Iterable[Mapping[str, Any]], cli_type: str
    ) -> List[SpyTestDict]:
        """Prepare all route definitions that should run with a specific CLI type."""
        prepared: List[SpyTestDict] = []
        for route in routes:
            if cli_type in self._iter_cli_types(route.get("cli_type") if route else None):
                prepared.append(self._prepare_route(route, cli_type))
        return prepared

    @classmethod
    def _remove_static_route_static(cls, route: Mapping[str, Any]) -> None:
        """Static helper for teardown_class to delete a route."""
        dut = cls._resolve_dut(route.get("dut"))
        if not dut:
            return
        cli_type = route.get("cli_type", cls.data.cli_type)
        ip_api.delete_static_route(
            dut,
            next_hop=route.get("next_hop"),
            static_ip=route.get("destination"),
            family="ipv4",
            interface=route.get("interface"),
            vrf=route.get("vrf"),
            cli_type=cli_type,
        )

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

    def _configure_static_route(self, route: Mapping[str, Any]) -> None:
        """Configure a static IPv4 route using SpyTest APIs."""
        dut = self._resolve_dut(route.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in route definition: {route}")
        cli_type = route.get("cli_type", self.data.cli_type)
        kwargs: Dict[str, Any] = {"cli_type": cli_type}
        for optional in ("distance", "nexthop_vrf", "track"):
            if route.get(optional) is not None:
                kwargs[optional] = route[optional]
        result = ip_api.create_static_route(
            dut,
            next_hop=route.get("next_hop"),
            static_ip=route.get("destination"),
            family="ipv4",
            interface=route.get("interface"),
            vrf=route.get("vrf"),
            **kwargs,
        )
        if not result:
            st.report_fail(
                "msg",
                f"Failed to configure static route {route.get('destination')} on {route.get('dut')}",
            )
        if route not in self._test_routes:
            self._test_routes.append(route)
        if route not in self.data.configured_routes:
            self.data.configured_routes.append(route)

    def _remove_static_route(self, route: Mapping[str, Any]) -> None:
        """Delete a static IPv4 route and ignore failures during cleanup."""
        dut = self._resolve_dut(route.get("dut"))
        if not dut:
            return
        cli_type = route.get("cli_type", self.data.cli_type)
        ip_api.delete_static_route(
            dut,
            next_hop=route.get("next_hop"),
            static_ip=route.get("destination"),
            family="ipv4",
            interface=route.get("interface"),
            vrf=route.get("vrf"),
            cli_type=cli_type,
        )

    def _build_verify_kwargs(self, route: Mapping[str, Any], cli_type: str) -> Dict[str, Any]:
        """Construct keyword arguments for verify_ip_route."""
        verify = route.get("verify") or {}
        verify_ip = verify.get("ip_address", route.get("destination"))
        verify_kwargs: Dict[str, Any] = {"ip_address": verify_ip, "cli_type": cli_type}
        for key in (
            "type",
            "selected",
            "fib",
            "nexthop",
            "interface",
            "distance",
            "cost",
            "filter_type",
        ):
            if verify.get(key) is not None:
                verify_kwargs[key] = verify[key]
        return verify_kwargs

    def _assert_route_present(self, route: Mapping[str, Any]) -> None:
        """Assert that a static route is present in the routing table."""
        dut = self._resolve_dut(route.get("dut"))
        if not dut:
            st.report_fail("msg", f"Invalid DUT alias in route verification: {route}")
        cli_type = route.get("cli_type", self.data.cli_type)
        verify_kwargs = self._build_verify_kwargs(route, cli_type)
        vrf_name = route.get("vrf")
        if not st.poll_wait(
            ip_api.verify_ip_route,
            self.data.verify_timeout,
            dut,
            family="ipv4",
            vrf_name=vrf_name,
            **verify_kwargs,
        ):
            st.report_fail(
                "msg",
                f"Static route {verify_kwargs['ip_address']} missing on {route.get('dut')}",
            )

    def _assert_route_absent(self, route: Mapping[str, Any]) -> None:
        """Assert that a static route is no longer present."""
        dut = self._resolve_dut(route.get("dut"))
        if not dut:
            return
        cli_type = route.get("cli_type", self.data.cli_type)
        verify = route.get("verify") or {}
        verify_ip = verify.get("ip_address", route.get("destination"))

        def _is_absent() -> bool:
            return not ip_api.verify_ip_route(
                dut,
                family="ipv4",
                vrf_name=route.get("vrf"),
                ip_address=verify_ip,
                cli_type=cli_type,
            )

        if not st.poll_wait(_is_absent, self.data.verify_timeout):
            st.report_fail(
                "msg",
                f"Static route {verify_ip} still present on {route.get('dut')} after removal",
            )

    def _get_testcase(self, tcid: str) -> Mapping[str, Any]:
        """Helper to fetch testcase definition from YAML."""
        testcase = self.data.testcases.get(tcid)
        if not testcase:
            st.report_fail("msg", f"Missing testcase definition for {tcid} in YAML")
        return testcase

    @pytest.mark.inventory(feature="Regression", testcases=["StaticIPv4_TC2.1.1"])
    def test_static_ipv4_next_hop_route(self) -> None:
        """TC 2.1.1 – Configure IPv4 static route via next-hop IP and verify installation."""
        testcase = self._get_testcase("2.1.1")
        route = testcase.get("route")
        if not route:
            st.report_fail("msg", "Testcase 2.1.1 missing 'route' definition in YAML")
        for cli_type in self._iter_cli_types(route.get("cli_type")):
            candidate = self._prepare_route(route, cli_type)
            with self._static_route_context(candidate):
                self._assert_route_present(candidate)
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["StaticIPv4_TC2.1.2"])
    def test_static_ipv4_route_removal(self) -> None:
        """TC 2.1.2 – Verify static route removal cleans up routing table."""
        testcase = self._get_testcase("2.1.2")
        route = testcase.get("route")
        if not route:
            st.report_fail("msg", "Testcase 2.1.2 missing 'route' definition in YAML")
        for cli_type in self._iter_cli_types(route.get("cli_type")):
            candidate = self._prepare_route(route, cli_type)
            with self._static_route_context(candidate, persist=True):
                self._assert_route_present(candidate)
                self._remove_static_route(candidate)
                self._assert_route_absent(candidate)
                self._untrack_route(candidate)
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["StaticIPv4_TC2.1.3"])
    def test_static_ipv4_multiple_routes(self) -> None:
        """TC 2.1.3 – Configure multiple static routes and validate each entry."""
        testcase = self._get_testcase("2.1.3")
        routes = testcase.get("routes") or []
        if not routes:
            st.report_fail("msg", "Testcase 2.1.3 requires at least one route entry")
        cli_union = self._collect_cli_union(*routes)
        for cli_type in cli_union:
            prepared_routes = self._collect_routes_for_cli(routes, cli_type)
            if not prepared_routes:
                continue
            try:
                for route in prepared_routes:
                    self._configure_static_route(route)
                for route in prepared_routes:
                    self._assert_route_present(route)
            finally:
                while prepared_routes:
                    cleanup_route = prepared_routes.pop()
                    self._remove_static_route(cleanup_route)
                    self._untrack_route(cleanup_route)
        st.report_pass("test_case_passed")

    @pytest.mark.inventory(feature="Regression", testcases=["StaticIPv4_TC2.1.4"])
    @pytest.mark.negative
    def test_static_ipv4_invalid_prefix_rejected(self) -> None:
        """TC 2.1.4 – Ensure malformed IPv4 static routes are rejected."""
        testcase = self._get_testcase("2.1.4")
        invalid_route = testcase.get("invalid_route")
        if not invalid_route:
            st.report_fail("msg", "Testcase 2.1.4 missing 'invalid_route' definition in YAML")
        for cli_type in self._iter_cli_types(invalid_route.get("cli_type")):
            candidate = self._prepare_route(invalid_route, cli_type)
            dut = self._resolve_dut(candidate.get("dut"))
            if not dut:
                st.report_fail("msg", "Invalid DUT alias for negative testcase 2.1.4")
            result = ip_api.create_static_route(
                dut,
                next_hop=candidate.get("next_hop"),
                static_ip=candidate.get("destination"),
                family="ipv4",
                interface=candidate.get("interface"),
                vrf=candidate.get("vrf"),
                cli_type=candidate.get("cli_type"),
                skip_error_check=True,
            )
            if result:
                # Cleanup in case the platform accepted the invalid route.
                self._remove_static_route(candidate)
                self._untrack_route(candidate)
                st.report_fail(
                    "msg",
                    f"Invalid static route {candidate.get('destination')} was accepted on {candidate.get('dut')}",
                )
        st.report_pass("test_case_passed")

```

> Keep test bodies small; push logic into APIs. Prefer `pytest.mark` for topology, speed, build gating, and negative cases.

---

## 3) YAML Test Data / Variables

- Location: `spytest/vars/<feature>/vars_<feature>.yaml`
- **Never hardcode** device names, IPs, ports, VLANs. Parameterize via YAML.
- Provide **defaults** and allow override using environment or CLI `-e`/SpyTest `st.getenv`.

**Sample `spytest/testbeds/testbed_2vs.yaml`**

```yaml
version: 2.0
devices:
  smic_sonic1:
    device_type: sonic
    access: {protocol: ssh, ip: 192.168.100.75, port: 22}
    credentials: {username: admin, password: YourPaSsWoRd, altpassword: YourPaSsWoRd}
    properties: {services: default, build: default, config: default, errors: default}

  smic_sonic2:
    device_type: sonic
    access: {protocol: ssh, ip: 192.168.100.61, port: 22}
    credentials: {username: admin, password: YourPaSsWoRd, altpassword: YourPaSsWoRd}
    properties: {services: default, build: default, config: default, errors: default}

topology:
  smic_sonic1:
    interfaces:
      Ethernet4: {EndDevice: smic_sonic2, EndPort: Ethernet4}

  smic_sonic2:
    interfaces:
      Ethernet4: {EndDevice: smic_sonic1, EndPort: Ethernet4}

services: {default: {}}
builds:   {default: {}}
configs:  {default: {}}
errors:   {default: {}}
params:   {}
```

**Loading**: use SpyTest helpers to merge vars and inventory.

---

## 4) API Development Rules (`spytest/apis`)

- Place feature APIs in a cohesive module tree, e.g.:
  - `spytest/apis/routing/`
  - `spytest/apis/system/`
  - `spytest/apis/switching/`
- **Must** be idempotent; multiple calls shouldn’t corrupt state.
- Return **structured dicts/lists**, not raw CLI strings.
- Prefer FRR/sonic‑cfggen/REST/Click wrappers already present. Don’t modify existing APIs.
- If no apis can be leveraged, new <feature>_api.py is generated under spytest/apis/<feature>/
- Use clear exceptions (e.g., `class OspfConfigError(Exception): ...`).
- Include `verify_*` helpers that return `(ok: bool, details: dict)` for clean asserts.
- Log via `st.log()` and respect global CLI log levels. No `print()`.

---

## 5) Markers, Parametrization, and Gating

- **Markers**: `@pytest.mark.topology("t0","t1","any","hw","virtual")`, `@pytest.mark.smoke`, `@pytest.mark.nightly`, `@pytest.mark.negative`, `@pytest.mark.build(">=2025.03")`.
- **Parametrize** where possible to cover matrix (e.g., interfaces, address families).
- **Skip/XFail** with reason strings and conditions derived from capabilities (read from DUT facts or image version).

```python
if not st.is_feature_supported(self.dut, "ospf"):
    pytest.skip("OSPF not supported on this image")
```

**Sample `spytest/routing/static/vars_static_ipv4.yaml`**

```yaml
defaults:
  cli_type: klish
  verify_timeout: 30
  cleanup: true
  min_topology:
    - "D1D2:1"

testcases:
  "2.1.1":
    title: "Install IPv4 static route via next-hop IP"
    route:
      dut: "D1"
      destination: "198.51.100.0/24"
      next_hop: "10.0.24.2"
      vrf: null
      verify:
        type: "S"
        nexthop: "10.0.24.2"
  "2.1.2":
    title: "Remove IPv4 static route"
    route:
      dut: "D1"
      destination: "198.51.101.0/24"
      next_hop: "10.0.24.2"
      vrf: null
      verify:
        type: "S"
        nexthop: "10.0.24.2"
  "2.1.3":
    title: "Configure multiple IPv4 static routes"
    routes:
      - dut: "D1"
        destination: "198.51.102.0/24"
        next_hop: "10.0.24.2"
        verify:
          type: "S"
          nexthop: "10.0.24.2"
      - dut: "D1"
        destination: "198.51.103.0/24"
        interface: "Ethernet4"
        verify:
          type: "S"
          interface: "Ethernet4"
  "2.1.4":
    title: "Reject invalid IPv4 static route prefix"
    invalid_route:
      dut: "D1"
      destination: "198.51.104.0"
      next_hop: "10.0.24.2"
```
---

## 6) Setup/Teardown & Idempotency

- Use `@pytest.fixture(scope="class", autouse=True)` for one‑time config; ensure teardown **always** runs (use `yield`).
- Avoid global mutable state.
- Implement **cleanup APIs** and call them in teardown.
- Do not leave DUTs with test residue (routes, ACLs, NTP keys, etc.).

---

## 7) Logging, Results, and Artifacts

- Respect run options passed via `-e "--result-log=..."`.
- Use `st.log()` with meaningful messages and structured dumps for diffs.
- When validating, include **why** it failed: expected vs actual details.
- Save any captures (pcaps, counters) under `tests/logs/<feature>/...` using run timestamp.

---

## 8) Virtual vs HW Alignment

- Feature‑detect capabilities (ASIC, platform) before running hardware‑specific checks.
- Keep parity: if logic differs, parametrize with `@pytest.mark.topology("hw")` vs `("virtual")` and explain in docstring.

---

## 9) Negative, Scale, and Interop

- Include at least **one negative** case per feature (bad config, auth failure, interface down).
- Add **scale** parameters (e.g., ECMP nexthops, LLDP neighbors count) as data‑driven.
- For cross‑feature (e.g., Unnumbered + OSPF), write separate focused tests and one light interop sanity.

---

## 10) Performance, Timeouts, Retries

- Centralize waits in constants (e.g., `WAIT_NEIGH_UP = 60`).
- Use bounded retries with backoff for eventually‑consistent states.
- Keep total runtime reasonable; mark long cases as `@pytest.mark.nightly`.

---

## 11) Linting, Style, and Types

- **PEP8/flake8** clean; run **black** formatting.
- Docstrings follow **Google** or **NumPy** style.
- Add **type hints** for API functions.

---

## 12) CI Integration and Naming

- Tests must be runnable via `./bin/spytest` as shown in the banner.
- Name tests to sort logically in dashboards (prefix with `basic_`, `scale_`, `negative_` where useful).
- Use stable **random seeds** if randomization is needed.

---

## 13) Security & Secrets

- No secrets in repo/YAML. Read sensitive material from env/CI secrets (e.g., NTP keys). Provide placeholders only.

---

## 14) Submission Checklist (for each new script/API)

- [ ] Correct **directory & filename** per mapping
- [ ] Docstring banner with **how to run**, **topology**, **prereqs**
- [ ] No hardcoding; parameters in **YAML**
- [ ] APIs added under `spytest/apis/<feature>/...`; existing APIs reused
- [ ] HW/Virtual aligned or gated with markers
- [ ] Negative and basic positive cases included
- [ ] Cleanup implemented; leaves DUT clean
- [ ] Logs and artifacts stored under `tests/logs/<feature>/...`
- [ ] Linted & typed; PR passes CI

---






