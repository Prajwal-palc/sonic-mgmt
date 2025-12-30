"""
STATIC IPV4 ROUTING - STATIC ROUTE VIA DUT2
Author: Athira
Copyright (C) 2024, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  routing/static/test_static_route_basic.py \
  --logs-path ./logs/test_static_route_basic_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates IPv4 static routing using the klish CLI path. The scenario configures
  Ethernet32 on both DUTs with 20.1.1.0/24, assigns 30.1.1.3/24 to DUT2 Ethernet36,
  adds a static route on DUT1 pointing to DUT2, and verifies reachability to the
  remote interface via the programmed route.

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Topology Diagram :
        # Topology - 2 nodes
        # +--------------------+                       +--------------------+
        # |        dut1        |=======================|        dut2        |
        # |  Ethernet32        |                       |  Ethernet32        |
        # |                    |                       |  Ethernet36        |
        # +--------------------+                       +--------------------+
  - Feature flags / min SONiC version: klish CLI support for IPv4 routing
  - Required test variables (YAML):
      * static_route.interfaces.dut1_primary
      * static_route.interfaces.dut2_primary
      * static_route.interfaces.dut2_secondary
      * static_route.ipv4.dut1_primary_ip
      * static_route.ipv4.dut2_primary_ip
      * static_route.ipv4.dut2_secondary_ip
      * static_route.ipv4.primary_prefix
      * static_route.ipv4.secondary_prefix
"""

from ipaddress import ip_network
from typing import Dict, Iterable, Tuple

import pytest

from spytest import SpyTestDict, st

import apis.routing.ip as ip_api
import apis.system.interface as intf_api

CLI_TYPE = "klish"
TC_ID = "TC_STATIC_ROUTE_001"

vars = SpyTestDict()
data = SpyTestDict()


def _merge_nested_dict(defaults: Dict[str, str], overrides: Dict[str, str]) -> SpyTestDict:
    result = SpyTestDict(defaults)
    for key, value in overrides.items():
        if value is not None and value != "":
            result[key] = value
    return result


def initialize_data() -> None:
    defaults = {
        "interfaces": {
            "dut1_primary": "Ethernet32",
            "dut2_primary": "Ethernet32",
            "dut2_secondary": "Ethernet36",
        },
        "ipv4": {
            "dut1_primary_ip": "20.1.1.3",
            "dut2_primary_ip": "20.1.1.4",
            "dut2_secondary_ip": "30.1.1.3",
            "primary_prefix": "20.1.1.0/24",
            "secondary_prefix": "30.1.1.0/24",
        },
    }

    overrides = st.get_args("static_route") or {}
    interfaces_override = overrides.get("interfaces", {}) if isinstance(overrides, dict) else {}
    ipv4_override = overrides.get("ipv4", {}) if isinstance(overrides, dict) else {}

    data.interfaces = _merge_nested_dict(defaults["interfaces"], interfaces_override)
    data.ipv4 = _merge_nested_dict(defaults["ipv4"], ipv4_override)
    data.ipv4.primary_prefix_len = ip_network(data.ipv4.primary_prefix, strict=False).prefixlen
    data.ipv4.secondary_prefix_len = ip_network(data.ipv4.secondary_prefix, strict=False).prefixlen
    data.ipv4.next_hop = data.ipv4.dut2_primary_ip
    data.ip_interfaces_configured = []
    data.static_route_configured = False


def _ensure_interfaces_up() -> None:
    st.log(
        "Ensuring interfaces {} on {} and {} on {} are administratively up".format(
            data.interfaces.dut1_primary, vars.D1, data.interfaces.dut2_primary, vars.D2
        )
    )

    assert intf_api.interface_noshutdown(
        vars.D1, data.interfaces.dut1_primary, cli_type=CLI_TYPE
    ), "Failed to bring up interface {} on {}".format(data.interfaces.dut1_primary, vars.D1)
    assert intf_api.interface_noshutdown(
        vars.D2, [data.interfaces.dut2_primary, data.interfaces.dut2_secondary], cli_type=CLI_TYPE
    ), "Failed to bring up interfaces {} and {} on {}".format(
        data.interfaces.dut2_primary, data.interfaces.dut2_secondary, vars.D2
    )


def _configure_ipv4_addresses() -> None:
    st.log("Configuring IPv4 addresses for {}".format(TC_ID))
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
            cli_type=CLI_TYPE,
        ), msg
        data.ip_interfaces_configured.append((dut, interface, address, prefix_len))

    assert ip_api.ping(
        vars.D1,
        data.ipv4.dut2_primary_ip,
        family="ipv4",
        count=3,
        cli_type=CLI_TYPE,
    ), "Failed to verify reachability on the primary link between {} and {}".format(vars.D1, vars.D2)


def _configure_static_route() -> None:
    st.log("Configuring static route {} via {} on {}".format(
        data.ipv4.secondary_prefix, data.ipv4.next_hop, vars.D1
    ))
    assert ip_api.create_static_route(
        vars.D1,
        next_hop=data.ipv4.next_hop,
        static_ip=data.ipv4.secondary_prefix,
        family="ipv4",
        cli_type=CLI_TYPE,
    ), "Failed to create static route {} via {}".format(
        data.ipv4.secondary_prefix, data.ipv4.next_hop
    )
    data.static_route_configured = True
    st.wait(2)


def _remove_static_route() -> None:
    if not data.static_route_configured:
        return
    try:
        if not ip_api.delete_static_route(
            vars.D1,
            next_hop=data.ipv4.next_hop,
            static_ip=data.ipv4.secondary_prefix,
            family="ipv4",
            cli_type=CLI_TYPE,
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
                cli_type=CLI_TYPE,
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
    global vars
    vars = st.ensure_min_topology("D1D2:1")
    if not st.is_feature_supported("klish", vars.D1):
        pytest.skip("klish CLI is not supported on {}".format(vars.D1))

    initialize_data()
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


class TestStaticRouteBasic:
    @pytest.mark.staticrouting
    @pytest.mark.inventory(feature="STATIC_ROUTING", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_static_route_reachability(self):
        st.banner("{}: verify static route reachability".format(TC_ID))

        assert ip_api.verify_ip_route(
            vars.D1,
            family="ipv4",
            ip_address=data.ipv4.secondary_prefix,
            nexthop=data.ipv4.next_hop,
            type="S",
            cli_type=CLI_TYPE,
        ), "Static route {} via {} not present on {}".format(
            data.ipv4.secondary_prefix, data.ipv4.next_hop, vars.D1
        )

        assert ip_api.ping(
            vars.D1,
            data.ipv4.dut2_secondary_ip,
            family="ipv4",
            count=5,
            cli_type=CLI_TYPE,
        ), "Ping to {} from {} failed via static route".format(
            data.ipv4.dut2_secondary_ip, vars.D1
        )
        st.report_pass("test_case_passed")
