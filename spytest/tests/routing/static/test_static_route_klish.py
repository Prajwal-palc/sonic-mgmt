"""
STATIC ROUTE CONNECTIVITY (KLISH CLI)
Author: Athira
© 2024, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_Dvs.yaml  \
  routing/static/test_static_route_klish.py \
  --logs-path ./logs/test_static_route_klish_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Validates test plan entry TC-IP-STATIC-001 by configuring IPv4 interfaces and
  a static route on DUT1 via the klish CLI (sonic-cli) and then verifying
  reachability to the remote host hanging off DUT2. The flow provisions peer
  link addressing, programs the static route, sources ICMP from DUT1's
  Ethernet32, and performs cleanup to leave the fabric in the baseline state.

Pre-requisites:
  - Topology: t0/t1 | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |        dut1        |=======================|        dut2        |
        # |  Eth32 20.1.1.3/24 |                       |  Eth32 20.1.1.4/24 |
        # |                    |                       |  Eth36 30.1.1.3/24 |
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version (if any)
  - Required test variables (YAML): defaults.*, testcases.static_route_via_dut2.*
"""

from __future__ import annotations

from pathlib import Path
import ipaddress

import pytest
import yaml

from spytest import SpyTestDict, st
import apis.routing.ip as ip_api

pytestmark = pytest.mark.topology("any")

VAR_FILE_ENV = "STATIC_ROUTE_KLISH_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "routing"
    / "static"
    / "vars_static_route_klish.yaml"
)


def _load_yaml_payload() -> SpyTestDict:
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE
    if not candidate.is_file():
        raise FileNotFoundError(
            f"Static route klish variable file not found: {candidate}"
        )
    with candidate.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return SpyTestDict(payload)


class TestStaticRouteKlish:
    """SpyTest suite for TC-IP-STATIC-001 using the klish CLI path."""

    data = SpyTestDict()

    @classmethod
    def setup_class(cls) -> None:
        """Collect topology handles and testcase metadata."""
        try:
            config = _load_yaml_payload()
        except FileNotFoundError as error:
            pytest.fail(str(error))

        defaults = SpyTestDict(config.get("defaults") or {})
        testcase = SpyTestDict(
            (config.get("testcases") or {}).get("static_route_via_dut2") or {}
        )
        if not testcase:
            pytest.fail(
                "Missing 'static_route_via_dut2' definition in vars_static_route_klish.yaml"
            )

        cli_type = (defaults.get("cli_type") or "klish").strip().lower()
        if cli_type != "klish":
            st.warn(
                f"Overriding cli_type={cli_type} with 'klish' per static route testcase requirement"
            )
            cli_type = "klish"

        min_topology = defaults.get("min_topology") or ["D1D2:1"]
        if isinstance(min_topology, str):
            min_topology = [min_topology]

        topology = st.ensure_min_topology(*min_topology)

        cls.data.config = config
        cls.data.defaults = defaults
        cls.data.testcase = testcase
        cls.data.cli_type = cli_type
        cls.data.topology = topology
        cls.data.alias_map = SpyTestDict()
        cls.data.dut_names = tuple(st.get_dut_names() or ())
        cls.data.cleanup = bool(defaults.get("cleanup", True))
        cls.data.verify_timeout = int(defaults.get("verify_timeout", 60))
        cls.data.case_id = testcase.get("id", "TC-IP-STATIC-001")

        interface_matrix = cls._build_interface_matrix(testcase)
        cls.data.interface_configs = interface_matrix
        cls.data.static_route = cls._build_static_route_block(testcase, interface_matrix)
        cls.data.ping = cls._build_ping_block(testcase)

    @classmethod
    def teardown_class(cls) -> None:
        """Best-effort cleanup in case execution terminates early."""
        if not cls.data.get("cleanup", True):
            return
        try:
            cls._configure_static_route(add=False)
        except Exception as error:  # pylint: disable=broad-except
            st.warn(f"Static route cleanup failed: {error}")
        try:
            cls._configure_interfaces(enable=False)
        except Exception as error:  # pylint: disable=broad-except
            st.warn(f"Interface cleanup failed: {error}")

    @classmethod
    def _resolve_alias(cls, alias: str):
        if not alias:
            pytest.fail("Topology alias missing in vars_static_route_klish.yaml")
        mapping = cls.data.get("alias_map", {})
        candidate = mapping.get(alias)
        if candidate:
            return candidate
        topology = cls.data.get("topology")
        if topology:
            candidate = getattr(topology, alias, None)
            if candidate:
                mapping[alias] = candidate
                cls.data.alias_map = mapping
                return candidate
        all_aliases = set(mapping.keys())
        all_aliases.update(cls.data.get("dut_names") or st.get_dut_names() or [])
        available = ", ".join(sorted(all_aliases))
        pytest.fail(
            f"Alias '{alias}' not present in topology (available aliases: {available})"
        )

    @classmethod
    def _build_interface_matrix(cls, testcase: SpyTestDict):
        entries = testcase.get("interfaces") or []
        if not entries:
            pytest.fail(
                "vars_static_route_klish.yaml must define testcases.static_route_via_dut2.interfaces"
            )

        resolved = []
        for raw_entry in entries:
            entry = SpyTestDict(raw_entry)
            alias = entry.get("alias")
            interface = entry.get("interface")
            ip_address = entry.get("ip")
            prefix = entry.get("prefix")
            family = (entry.get("family") or "ipv4").lower()

            if not alias or not interface or ip_address is None or prefix is None:
                pytest.fail(
                    f"Incomplete interface entry in vars_static_route_klish.yaml: {entry}"
                )

            dut = cls._resolve_alias(alias)
            try:
                prefix_value = int(prefix)
            except (TypeError, ValueError) as error:
                pytest.fail(
                    f"Invalid prefix '{prefix}' for {alias}:{interface}: {error}"
                )

            resolved.append(
                SpyTestDict(
                    {
                        "alias": alias,
                        "dut": dut,
                        "interface": interface,
                        "ip": str(ip_address),
                        "prefix": prefix_value,
                        "family": family,
                    }
                )
            )

        return tuple(resolved)

    @classmethod
    def _build_static_route_block(cls, testcase: SpyTestDict, interface_matrix):
        block = SpyTestDict(testcase.get("static_route") or {})
        owner_alias = block.get("owner_alias") or testcase.get("dut1_alias") or "D1"

        block["owner_alias"] = owner_alias
        block["dut"] = cls._resolve_alias(owner_alias)

        route = block.get("route") or testcase.get("remote_network")
        if not route:
            pytest.fail(
                "Static route definition requires 'route' in vars_static_route_klish.yaml"
            )
        try:
            network = ipaddress.ip_network(str(route), strict=False)
        except ValueError as error:
            pytest.fail(f"Invalid static route prefix '{route}': {error}")
        block["route"] = f"{network.network_address}/{network.prefixlen}"

        next_hop = block.get("next_hop")
        if not next_hop:
            pytest.fail(
                "Static route definition requires 'next_hop' in vars_static_route_klish.yaml"
            )
        block["next_hop"] = str(next_hop)
        block["family"] = (block.get("family") or "ipv4").lower()
        block["interface"] = block.get("interface")
        block["next_hop_alias"] = block.get("next_hop_alias")

        return block

    @classmethod
    def _build_ping_block(cls, testcase: SpyTestDict):
        block = SpyTestDict(testcase.get("ping") or {})
        source_alias = block.get("source_alias") or testcase.get("dut1_alias") or "D1"
        target = block.get("target")
        if not target:
            pytest.fail(
                "Ping block requires 'target' in vars_static_route_klish.yaml"
            )

        count = block.get("count", 3)
        try:
            count_value = int(count)
        except (TypeError, ValueError) as error:
            pytest.fail(f"Invalid ping count '{count}': {error}")

        family = (block.get("family") or "ipv4").lower()

        return SpyTestDict(
            {
                "source_alias": source_alias,
                "target": str(target),
                "count": count_value,
                "family": family,
                "source_interface": block.get("source_interface"),
                "timeout": block.get("timeout"),
                "packetsize": block.get("packetsize"),
                "dut": cls._resolve_alias(source_alias),
            }
        )

    @classmethod
    def _configure_interfaces(cls, enable: bool) -> None:
        action = "add" if enable else "remove"
        for entry in cls.data.interface_configs:
            verb = "Configuring" if enable else "Removing"
            st.log(
                f"{verb} {entry.ip}/{entry.prefix} on {entry.alias}:{entry.interface} using {cls.data.cli_type}"
            )
            result = ip_api.config_ip_addr_interface(
                entry.dut,
                interface_name=entry.interface,
                ip_address=entry.ip,
                subnet=entry.prefix,
                family=entry.family,
                config=action,
                skip_error=not enable,
                cli_type=cls.data.cli_type,
            )
            if enable and not result:
                st.report_fail(
                    "msg",
                    f"Failed to configure {entry.ip}/{entry.prefix} on {entry.interface} ({entry.alias}) using {cls.data.cli_type}",
                )

    @classmethod
    def _configure_static_route(cls, add: bool) -> None:
        route_block = cls.data.static_route
        action = "add" if add else "del"
        verb = "Applying" if add else "Removing"
        st.log(
            f"{verb} static route {route_block.route} via {route_block.next_hop} on {route_block.owner_alias} using {cls.data.cli_type}"
        )
        result = ip_api.config_static_route(
            route_block.dut,
            route=route_block.route,
            next_hop=route_block.next_hop,
            family=route_block.family,
            interface=route_block.get("interface"),
            config=action,
            cli_type=cls.data.cli_type,
        )
        if add and not result:
            st.report_fail(
                "msg",
                f"Failed to configure static route {route_block.route} via {route_block.next_hop} on {route_block.owner_alias}",
            )

    def test_static_route_reachability_klish(self) -> None:
        """Validate IPv4 reachability after provisioning the static route via klish CLI."""
        st.log(
            f"Executing {self.data.case_id}: verify ping to {self.data.ping.target} with klish CLI static route"
        )

        interfaces_configured = False
        route_configured = False
        try:
            self._configure_interfaces(enable=True)
            interfaces_configured = True
            self._configure_static_route(add=True)
            route_configured = True

            ping_block = self.data.ping
            ping_kwargs = {
                "count": ping_block.count,
                "cli_type": self.data.cli_type,
            }
            if ping_block.source_interface:
                ping_kwargs["interface"] = ping_block.source_interface
            if ping_block.timeout:
                ping_kwargs["timeout"] = ping_block.timeout
            if ping_block.packetsize:
                ping_kwargs["packetsize"] = ping_block.packetsize

            ping_ok = ip_api.ping(
                ping_block.dut,
                ping_block.target,
                family=ping_block.family,
                **ping_kwargs,
            )
            if not ping_ok:
                st.report_fail(
                    "msg",
                    f"Ping from {ping_block.source_alias} to {ping_block.target} failed after static route configuration",
                )
        finally:
            if self.data.get("cleanup", True):
                if route_configured:
                    self._configure_static_route(add=False)
                if interfaces_configured:
                    self._configure_interfaces(enable=False)

        st.report_pass("test_case_passed")
