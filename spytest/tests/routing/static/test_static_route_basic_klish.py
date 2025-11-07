"""
STATIC IPV4 ROUTING - STATIC ROUTE VIA DUT2 (KLISH)
Author: Codex Agent for Supermicro QA

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  routing/static/test_static_route_basic_klish.py \
  --logs-path ./logs/test_static_route_basic_klish_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Automates test plan TC-IP-STATIC-001 from testcases_static_route_1.md using the SpyTest
  framework with klish CLI validation. The scenario brings up Ethernet32 on both DUTs with
  20.1.1.0/24, configures Ethernet36 on DUT2 with 30.1.1.3/24, installs a static route on
  DUT1 pointing to DUT2 as the next hop, and verifies reachability to the remote interface.

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported on hardware and virtual platforms
  - Feature flags / min SONiC version: klish CLI support for IPv4 static routing
  - Required test variables (YAML): spytest/vars/routing/static/vars_static_ipv4_klish.yaml
"""

from __future__ import annotations

from ipaddress import ip_interface
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Tuple

import pytest
import yaml

from spytest import SpyTestDict, st

import apis.routing.ip as ip_api
import apis.system.interface as intf_api


DEFAULT_CLI_TYPE = "klish"
VAR_FILE_ENV = "STATIC_IPV4_KLISH_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "routing"
    / "static"
    / "vars_static_ipv4_klish.yaml"
)

SUITE_BANNER = "STATIC ROUTE BASIC KLISH"
TC_ID = "TC-IP-STATIC-001"

vars = SpyTestDict()
data = SpyTestDict()


def initialize_data() -> None:
    try:
        payload = _load_yaml_payload()
    except FileNotFoundError as error:
        pytest.skip(str(error))
    except ValueError as error:
        pytest.fail(str(error))

    overrides = st.get_args("static_route_klish")
    if isinstance(overrides, Mapping) and overrides:
        _deep_update(payload, overrides)

    config = SpyTestDict(payload)
    defaults = SpyTestDict(config.get("defaults", {}))

    min_topology = defaults.get("min_topology") or ["D1D2:1"]
    if isinstance(min_topology, str):
        min_topology = [min_topology]
    else:
        min_topology = list(min_topology)
    if not min_topology:
        min_topology = ["D1D2:1"]

    global vars
    vars = st.ensure_min_topology(*min_topology)

    data.config = config
    data.defaults = defaults
    data.cli_type = str(defaults.get("cli_type") or DEFAULT_CLI_TYPE).lower()
    data.cleanup_enabled = bool(defaults.get("cleanup", True))

    interfaces_cfg = SpyTestDict(config.get("interfaces", {}))
    d1_cfg = SpyTestDict(interfaces_cfg.get("D1", {}))
    d2_cfg = SpyTestDict(interfaces_cfg.get("D2", {}))
    d1_transit = SpyTestDict(d1_cfg.get("transit", {}))
    d2_transit = SpyTestDict(d2_cfg.get("transit", {}))
    d2_edge = SpyTestDict(d2_cfg.get("edge", {}))

    d1_transit_name = d1_transit.get("name") or "Ethernet32"
    d1_transit_prefix = d1_transit.get("prefix") or "20.1.1.3/24"
    d2_transit_name = d2_transit.get("name") or "Ethernet32"
    d2_transit_prefix = d2_transit.get("prefix") or "20.1.1.4/24"
    d2_edge_name = d2_edge.get("name") or "Ethernet36"
    d2_edge_prefix = d2_edge.get("prefix") or "30.1.1.3/24"

    try:
        d1_interface = ip_interface(d1_transit_prefix)
    except ValueError as error:
        pytest.fail("Invalid IPv4 prefix '{}' for D1 transit: {}".format(d1_transit_prefix, error))
    try:
        d2_interface = ip_interface(d2_transit_prefix)
    except ValueError as error:
        pytest.fail("Invalid IPv4 prefix '{}' for D2 transit: {}".format(d2_transit_prefix, error))
    try:
        d2_edge_interface = ip_interface(d2_edge_prefix)
    except ValueError as error:
        pytest.fail("Invalid IPv4 prefix '{}' for D2 edge: {}".format(d2_edge_prefix, error))

    route_cfg = SpyTestDict(config.get("routes", {}).get("primary", {}))
    if not route_cfg:
        pytest.fail("Missing 'routes.primary' definition in static route YAML")

    destination_prefix = str(route_cfg.get("destination") or str(d2_edge_interface.network))
    next_hop = str(route_cfg.get("next_hop") or str(d2_interface.ip))

    data.interfaces = SpyTestDict(
        {
            "dut1_primary": d1_transit_name,
            "dut2_primary": d2_transit_name,
            "dut2_secondary": d2_edge_name,
        }
    )

    data.ipv4 = SpyTestDict()
    data.ipv4.dut1_primary_ip = str(d1_interface.ip)
    data.ipv4.dut2_primary_ip = str(d2_interface.ip)
    data.ipv4.dut2_secondary_ip = str(d2_edge_interface.ip)
    data.ipv4.primary_prefix_len = int(d1_interface.network.prefixlen)
    data.ipv4.secondary_prefix_len = int(d2_edge_interface.network.prefixlen)
    data.ipv4.secondary_prefix = destination_prefix
    data.ipv4.next_hop = next_hop

    data.ip_interfaces_configured = []
    data.static_route_configured = False

    pings = SpyTestDict(config.get("pings", {}))
    data.pings = SpyTestDict(
        {
            "target_ip": str(pings.get("edge", {}).get("target") or data.ipv4.dut2_secondary_ip),
            "count": int(pings.get("edge", {}).get("count") or 4),
            "family": str(pings.get("edge", {}).get("family") or "ipv4"),
        }
    )


def _deep_update(target: Dict[str, Any], overrides: Mapping[str, Any]) -> None:
    for key, value in overrides.items():
        if isinstance(value, Mapping):
            existing = target.get(key)
            if not isinstance(existing, Mapping):
                existing = {}
            else:
                existing = dict(existing)
            target[key] = existing
            _deep_update(existing, value)
        elif value not in (None, ""):
            target[key] = value


def _load_yaml_payload() -> Dict[str, Any]:
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE
    if not candidate.is_file():
        raise FileNotFoundError("Static routing variable file not found: {}".format(candidate))
    with candidate.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("Static routing variable file must contain a mapping: {}".format(candidate))
    return payload


def _cli_type() -> str:
    value = getattr(data, "cli_type", DEFAULT_CLI_TYPE)
    if isinstance(value, str) and value:
        return value
    return DEFAULT_CLI_TYPE


def _ensure_interfaces_up() -> None:
    st.log(
        "Ensuring interfaces {} on {} and {} on {} are administratively up".format(
            data.interfaces.dut1_primary, vars.D1, data.interfaces.dut2_primary, vars.D2
        )
    )
    assert intf_api.interface_noshutdown(
        vars.D1, data.interfaces.dut1_primary, cli_type=_cli_type()
    ), "Failed to enable interface {} on {}".format(data.interfaces.dut1_primary, vars.D1)
    assert intf_api.interface_noshutdown(
        vars.D2,
        [data.interfaces.dut2_primary, data.interfaces.dut2_secondary],
        cli_type=_cli_type(),
    ), "Failed to enable interfaces {} and {} on {}".format(
        data.interfaces.dut2_primary, data.interfaces.dut2_secondary, vars.D2
    )


def _configure_ipv4_addresses() -> None:
    st.log("Configuring IPv4 addresses for {}".format(SUITE_BANNER))
    entries: Iterable[Tuple[str, str, str, int]] = [
        (vars.D1, data.interfaces.dut1_primary, data.ipv4.dut1_primary_ip, data.ipv4.primary_prefix_len),
        (vars.D2, data.interfaces.dut2_primary, data.ipv4.dut2_primary_ip, data.ipv4.primary_prefix_len),
        (vars.D2, data.interfaces.dut2_secondary, data.ipv4.dut2_secondary_ip, data.ipv4.secondary_prefix_len),
    ]

    for dut, interface, address, prefix_len in entries:
        msg = "Failed to configure {} {}/{} on {}".format(interface, address, prefix_len, dut)
        assert ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=address,
            subnet=prefix_len,
            family="ipv4",
            cli_type=_cli_type(),
        ), msg
        data.ip_interfaces_configured.append((dut, interface, address, prefix_len))

    assert ip_api.ping(
        vars.D1,
        data.ipv4.dut2_primary_ip,
        family="ipv4",
        count=3,
        cli_type=_cli_type(),
    ), "Failed to verify reachability on the primary link between {} and {}".format(vars.D1, vars.D2)


def _configure_static_route() -> None:
    st.log(
        "Configuring static route {} via {} on {}".format(
            data.ipv4.secondary_prefix, data.ipv4.next_hop, vars.D1
        )
    )
    assert ip_api.create_static_route(
        vars.D1,
        next_hop=data.ipv4.next_hop,
        static_ip=data.ipv4.secondary_prefix,
        family="ipv4",
        cli_type=_cli_type(),
    ), "Failed to create static route {} via {}".format(
        data.ipv4.secondary_prefix, data.ipv4.next_hop
    )
    data.static_route_configured = True
    st.wait(2)


def _remove_static_route(force: bool = False) -> None:
    should_attempt = data.static_route_configured
    if not should_attempt and force:
        try:
            should_attempt = ip_api.verify_ip_route(
                vars.D1,
                family="ipv4",
                ip_address=data.ipv4.secondary_prefix,
                nexthop=data.ipv4.next_hop,
                type="S",
                cli_type=_cli_type(),
            )
        except Exception as error:  # pylint: disable=broad-except
            st.warn("Cleanup: unable to confirm static route presence -> {}".format(error))
            should_attempt = True
    if not should_attempt:
        return
    try:
        if not ip_api.delete_static_route(
            vars.D1,
            next_hop=data.ipv4.next_hop,
            static_ip=data.ipv4.secondary_prefix,
            family="ipv4",
            cli_type=_cli_type(),
        ):
            st.warn(
                "Cleanup: failed to delete static route {} via {}".format(
                    data.ipv4.secondary_prefix, data.ipv4.next_hop
                )
            )
    finally:
        data.static_route_configured = False


def _remove_configured_addresses() -> None:
    while data.ip_interfaces_configured:
        dut, interface, address, prefix_len = data.ip_interfaces_configured.pop()
        try:
            ip_api.config_ip_addr_interface(
                dut,
                interface_name=interface,
                ip_address=address,
                subnet=prefix_len,
                family="ipv4",
                config="remove",
                cli_type=_cli_type(),
                skip_error=True,
            )
        except Exception as error:  # pragma: no cover - defensive cleanup
            st.warn(
                "Cleanup: exception removing {} {}/{} on {} -> {}".format(
                    interface, address, prefix_len, dut, error
                )
            )


@pytest.fixture(scope="class", autouse=True)
def static_route_class_hook(request):
    initialize_data()
    if _cli_type() == "klish" and not st.is_feature_supported("klish", vars.D1):
        pytest.skip("klish CLI is not supported on {}".format(vars.D1))

    st.banner("{}: test setup".format(TC_ID))
    try:
        _ensure_interfaces_up()
        _configure_ipv4_addresses()
        _configure_static_route()
        yield
    finally:
        st.banner("{}: cleanup".format(TC_ID))
        _remove_static_route()
        _remove_configured_addresses()


class TestStaticRouteBasicKlish:
    @pytest.mark.staticrouting
    @pytest.mark.inventory(feature="STATIC_ROUTING", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_static_route_reachability_klish(self):
        st.banner("{}: verify static route reachability using klish".format(TC_ID))

        assert ip_api.verify_ip_route(
            vars.D1,
            family="ipv4",
            ip_address=data.ipv4.secondary_prefix,
            nexthop=data.ipv4.next_hop,
            type="S",
            cli_type=_cli_type(),
        ), "Static route {} via {} not present on {}".format(
            data.ipv4.secondary_prefix, data.ipv4.next_hop, vars.D1
        )

        assert ip_api.ping(
            vars.D1,
            data.pings.target_ip,
            family=data.pings.family,
            count=data.pings.count,
            cli_type=_cli_type(),
        ), "Ping to {} from {} failed via static route".format(
            data.pings.target_ip, vars.D1
        )
        st.report_pass("test_case_passed")
