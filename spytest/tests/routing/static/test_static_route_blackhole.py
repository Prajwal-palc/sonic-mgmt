"""
STATIC IPV4 ROUTING - BLACKHOLE DROP VALIDATION
Author: Athira
© 2024, copyrights@SuperMicro

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  routing/static/test_static_route_blackhole.py \
  --logs-path ./logs/test_static_route_blackhole_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  Automates static route Test Case TC-IP-STATIC-BH-001 from
  testcases_static_route_2.md using the SpyTest framework. The scenario
  provisions an IPv4 static blackhole (Null0) route via the klish CLI, validates
  both klish and sudo vtysh show outputs, toggles route enable/disable actions,
  performs interface-level administration on Ethernet4 sourced from the
  topology YAML, and confirms that traffic to the blackholed prefix is dropped.

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |        dut1        |=======================|        dut2        |
        # |    Ethernet4       |                       |    Ethernet4       |
        # +--------------------+                       +--------------------+

  - Feature flags / min SONiC version: klish CLI support for IPv4 static routes
  - Required test variables (YAML): spytest/vars/routing/static/vars_static_ipv4_blackhole_klish.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st

import apis.routing.ip as ip_api
import apis.system.interface as intf_api

DEFAULT_CLI_TYPE = "klish"
VAR_FILE_ENV = "STATIC_IPV4_BH_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "routing"
    / "static"
    / "vars_static_ipv4_blackhole_klish.yaml"
)

SUITE_BANNER = "STATIC ROUTE BLACKHOLE"
TC_ID = "TC-IP-STATIC-BH-001"

vars = SpyTestDict()
data = SpyTestDict()


def initialize_data() -> None:
    try:
        payload = _load_yaml_payload()
    except FileNotFoundError as error:
        pytest.skip(str(error))
    except ValueError as error:
        pytest.fail(str(error))

    overrides = st.get_args("static_route_blackhole")
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

    route_cfg = SpyTestDict(config.get("routes", {}).get("blackhole", {}))
    if not route_cfg:
        pytest.fail("Missing 'routes.blackhole' definition in static route YAML")

    data.route = SpyTestDict()
    data.route.prefix = str(route_cfg.get("prefix") or "192.0.2.0/24")
    data.route.test_ip = str(route_cfg.get("test_ip") or "192.0.2.1")
    data.route.null_interface = str(route_cfg.get("null_interface") or "Null0")

    interface_cfg = SpyTestDict(config.get("interfaces", {}).get("D1", {}))
    data.interface = str(interface_cfg.get("primary") or "Ethernet4")

    data.route_configured = False
    data.interface_shutdown = False


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
        raise FileNotFoundError(
            "Static routing variable file not found: {}".format(candidate)
        )
    with candidate.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(
            "Static routing variable file must contain a mapping: {}".format(candidate)
        )
    return payload


def _cli_type() -> str:
    value = getattr(data, "cli_type", DEFAULT_CLI_TYPE)
    if isinstance(value, str) and value:
        return value
    return DEFAULT_CLI_TYPE


def _ensure_interface_admin_up() -> None:
    st.log(
        "Ensuring interface {} on {} is administratively up for {}".format(
            data.interface, vars.D1, SUITE_BANNER
        )
    )
    assert intf_api.interface_noshutdown(
        vars.D1, data.interface, cli_type=_cli_type()
    ), "Failed to bring interface {} up on {}".format(data.interface, vars.D1)


def _create_blackhole_route() -> None:
    st.log(
        "Configuring static blackhole route {} on {}".format(
            data.route.prefix, vars.D1
        )
    )
    assert ip_api.create_static_route(
        vars.D1,
        next_hop="blackhole",
        static_ip=data.route.prefix,
        family="ipv4",
        cli_type=_cli_type(),
    ), "Failed to configure blackhole route {}".format(data.route.prefix)
    data.route_configured = True
    st.wait(1)


def _delete_blackhole_route(force: bool = False) -> None:
    if not data.route_configured and not force:
        return
    st.log("Removing static blackhole route {} on {}".format(data.route.prefix, vars.D1))
    if not ip_api.delete_static_route(
        vars.D1,
        next_hop="blackhole",
        static_ip=data.route.prefix,
        family="ipv4",
        cli_type=_cli_type(),
    ):
        st.warn("Cleanup: unable to remove blackhole route {}".format(data.route.prefix))
    data.route_configured = False
    st.wait(1)


def _shutdown_interface() -> None:
    st.log("Shutting interface {} on {}".format(data.interface, vars.D1))
    if intf_api.interface_shutdown(
        vars.D1, data.interface, cli_type=_cli_type()
    ):
        data.interface_shutdown = True
        st.wait(1)
    else:
        pytest.fail(
            "Failed to shutdown interface {} on {}".format(data.interface, vars.D1)
        )


def _bring_interface_up(strict: bool = False) -> bool:
    if not data.interface_shutdown:
        return True
    st.log("Restoring interface {} on {}".format(data.interface, vars.D1))
    if intf_api.interface_noshutdown(
        vars.D1, data.interface, cli_type=_cli_type()
    ):
        data.interface_shutdown = False
        st.wait(1)
        return True
    if strict:
        pytest.fail("Failed to bring interface {} up on {}".format(data.interface, vars.D1))
    st.warn("Cleanup: failed to bring {} up on {}".format(data.interface, vars.D1))
    return False


def _capture_klish(command: str) -> str:
    output = st.show(
        vars.D1, command, type=_cli_type(), skip_tmpl=True, skip_error_check=False
    )
    return str(output or "")


def _capture_vtysh(command: str) -> str:
    output = st.vtysh_show(vars.D1, command, skip_tmpl=True, skip_error_check=False)
    return str(output or "")


def _assert_contains_blackhole(output: str, context: str) -> None:
    normalized = output.lower()
    if data.route.null_interface.lower() in normalized:
        return
    if "null0" in normalized:
        return
    if "blackhole" in normalized:
        return
    pytest.fail("Expected blackhole/null0 in {} output:\n{}".format(context, output))


@pytest.fixture(scope="class", autouse=True)
def static_blackhole_class_setup(request):
    initialize_data()
    if _cli_type() != "klish":
        pytest.skip("This suite requires cli_type 'klish', got '{}'".format(_cli_type()))
    if not st.is_feature_supported("klish", vars.D1):
        pytest.skip("klish CLI is not supported on {}".format(vars.D1))

    st.banner("{}: class setup".format(SUITE_BANNER))
    _ensure_interface_admin_up()
    _delete_blackhole_route(force=True)

    def fin():
        st.banner("{}: cleanup".format(SUITE_BANNER))
        _delete_blackhole_route(force=True)
        _bring_interface_up()

    request.addfinalizer(fin)


class TestStaticRouteBlackhole:
    @pytest.mark.staticrouting
    @pytest.mark.inventory(feature="STATIC_ROUTING", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_static_route_blackhole_drop(self):
        st.banner("{}: configure blackhole route and verify drop".format(TC_ID))

        _create_blackhole_route()

        klish_route = _capture_klish("show ip route")
        klish_static = _capture_klish("show ip route static")
        klish_running = _capture_klish("show running-config | section ip route")

        assert data.route.prefix in klish_route, "Route {} missing in klish show ip route".format(
            data.route.prefix
        )
        assert data.route.prefix in klish_static, "Route {} missing in klish show ip route static".format(
            data.route.prefix
        )
        _assert_contains_blackhole(klish_route, "klish show ip route")
        _assert_contains_blackhole(klish_static, "klish show ip route static")
        assert data.route.prefix in klish_running, (
            "Running-config does not reflect blackhole route {}".format(data.route.prefix)
        )

        vtysh_route = _capture_vtysh("show ip route")
        vtysh_running = _capture_vtysh("show running-config")
        assert data.route.prefix in vtysh_route, "Route {} missing in vtysh show ip route".format(
            data.route.prefix
        )
        _assert_contains_blackhole(vtysh_route, "vtysh show ip route")
        assert data.route.prefix in vtysh_running, (
            "Running-config from vtysh does not list route {}".format(data.route.prefix)
        )

        _delete_blackhole_route()
        running_after_remove = _capture_klish("show running-config | section ip route")
        assert data.route.prefix not in running_after_remove, (
            "Blackhole route {} still present after removal".format(data.route.prefix)
        )

        _create_blackhole_route()
        running_after_add = _capture_klish("show running-config | section ip route")
        assert data.route.prefix in running_after_add, (
            "Re-added blackhole route {} not reflected in running-config".format(data.route.prefix)
        )

        _shutdown_interface()
        _bring_interface_up(strict=True)

        klish_static_post_toggle = _capture_klish("show ip route static")
        _assert_contains_blackhole(
            klish_static_post_toggle, "klish show ip route static after interface toggle"
        )

        st.banner("{}: validate ping drop to {}".format(TC_ID, data.route.test_ip))
        ping_result = ip_api.ping(
            vars.D1,
            data.route.test_ip,
            family="ipv4",
            count=3,
            cli_type=_cli_type(),
        )
        assert not ping_result, (
            "Ping to {} unexpectedly succeeded; traffic should be dropped".format(
                data.route.test_ip
            )
        )

        st.report_pass("test_case_passed")
