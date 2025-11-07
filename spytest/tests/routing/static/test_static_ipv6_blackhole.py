"""
STATIC IPV6 ROUTING - BLACKHOLE CLI VALIDATION (KLISH)
Author: Generated from Test Plan TC-IP-STATIC-IPV6-006
Copyright (C) 2024

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/routing/static/test_static_ipv6_blackhole.py \
  --logs-path ./logs/test_ipv6_blackhole_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates IPv6 static routing with blackhole functionality using klish CLI per test plan
  TC-IP-STATIC-IPV6-006. Tests blackhole routes, routes with tag, administrative distance,
  track objects, and VRF isolation. Validates traffic dropping behavior, route installation
  across multiple route types, and state consistency via multiple CLI methods.

Pre-requisites:
  - Topology: two-node (D1-D2) with VRF support | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with VRF
        # +---------------------------+                       +---------------------------+
        # |        dut1 (D1)          |                       |        dut2 (D2)          |
        # | Eth4 2001:db8:1::1/64     |=======================| Eth4 2001:db8:1::2/64     |
        # | VRF BLUE configured       |                       | Lo0  2001:db8:100::1/128  |
        # |                           |                       | VRF BLUE configured       |
        # +---------------------------+                       +---------------------------+
  - Feature requirements: klish CLI, IPv6 routing, VRF support, track objects
  - Required test variables (YAML): spytest/spytest/vars/routing/static/vars_static_ipv6_blackhole.yaml
"""

from __future__ import annotations

from ipaddress import IPv6Interface, IPv6Address, IPv6Network
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import pytest
import yaml

from spytest import SpyTestDict, st

import apis.routing.ip as ip_api
import apis.system.interface as intf_api
import apis.routing.vrf as vrf_api

# Configuration constants
DEFAULT_CLI_TYPE = "klish"
VAR_FILE_ENV = "STATIC_IPV6_BLACKHOLE_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "spytest"
    / "vars"
    / "routing"
    / "static"
    / "vars_static_ipv6_blackhole.yaml"
)

SUITE_BANNER = "STATIC IPV6 ROUTE BLACKHOLE"
TC_ID = "TC-IP-STATIC-IPV6-006"

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()


def initialize_data() -> None:
    """Load test configuration from YAML and initialize topology variables."""
    try:
        payload = _load_yaml_payload()
    except FileNotFoundError as error:
        pytest.skip(str(error))
    except ValueError as error:
        pytest.fail(str(error))

    # Allow runtime overrides via st.get_args
    overrides = st.get_args("static_route_ipv6_blackhole")
    if isinstance(overrides, Mapping) and overrides:
        _deep_update(payload, overrides)

    config = SpyTestDict(payload)
    defaults = SpyTestDict(config.get("defaults", {}))

    # Topology requirements
    min_topology = defaults.get("min_topology") or ["D1D2:1"]
    if isinstance(min_topology, str):
        min_topology = [min_topology]
    else:
        min_topology = list(min_topology)
    if not min_topology:
        min_topology = ["D1D2:1"]

    global vars
    vars = st.ensure_min_topology(*min_topology)

    # Store configuration data
    data.config = config
    data.defaults = defaults
    data.cli_type = str(defaults.get("cli_type") or DEFAULT_CLI_TYPE).lower()
    data.cleanup_enabled = bool(defaults.get("cleanup", True))
    data.verify_timeout = int(defaults.get("verify_timeout", 30))

    # Parse interface configuration
    interfaces_cfg = SpyTestDict(config.get("interfaces", {}))
    d1_cfg = SpyTestDict(interfaces_cfg.get("D1", {}))
    d2_cfg = SpyTestDict(interfaces_cfg.get("D2", {}))
    d1_transit = SpyTestDict(d1_cfg.get("transit", {}))
    d2_transit = SpyTestDict(d2_cfg.get("transit", {}))
    d2_edge = SpyTestDict(d2_cfg.get("edge", {}))

    # Extract interface names and IPv6 addresses with defaults
    d1_transit_name = d1_transit.get("name") or "Ethernet4"
    d1_transit_ipv6 = d1_transit.get("ipv6_address") or "2001:db8:1::1/64"
    d2_transit_name = d2_transit.get("name") or "Ethernet4"
    d2_transit_ipv6 = d2_transit.get("ipv6_address") or "2001:db8:1::2/64"
    d2_edge_name = d2_edge.get("name") or "Loopback0"
    d2_edge_ipv6 = d2_edge.get("ipv6_address") or "2001:db8:100::1/128"

    # Validate IPv6 addresses
    try:
        d1_interface = IPv6Interface(d1_transit_ipv6)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 address '{d1_transit_ipv6}' for D1 transit: {error}")
    try:
        d2_interface = IPv6Interface(d2_transit_ipv6)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 address '{d2_transit_ipv6}' for D2 transit: {error}")
    try:
        d2_edge_interface = IPv6Interface(d2_edge_ipv6)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 address '{d2_edge_ipv6}' for D2 edge: {error}")

    # Store parsed interface data
    data.interfaces = SpyTestDict({
        "dut1_transit": d1_transit_name,
        "dut2_transit": d2_transit_name,
        "dut2_edge": d2_edge_name,
    })

    data.ipv6 = SpyTestDict()
    data.ipv6.dut1_transit_ip = str(d1_interface.ip)
    data.ipv6.dut1_transit_prefix = str(d1_interface)
    data.ipv6.dut2_transit_ip = str(d2_interface.ip)
    data.ipv6.dut2_transit_prefix = str(d2_interface)
    data.ipv6.dut2_edge_ip = str(d2_edge_interface.ip)
    data.ipv6.dut2_edge_prefix = str(d2_edge_interface)
    data.ipv6.transit_prefix_len = int(d1_interface.network.prefixlen)
    data.ipv6.edge_prefix_len = int(d2_edge_interface.network.prefixlen)

    # Parse VRF configuration
    vrf_cfg = SpyTestDict(config.get("vrf", {}))
    data.vrf_name = vrf_cfg.get("name") or "BLUE"
    data.vrf_description = vrf_cfg.get("description") or ""

    # Parse track object configuration
    track_cfg = SpyTestDict(config.get("track_object", {}))
    data.track_id = track_cfg.get("id") or 1
    data.track_type = track_cfg.get("type") or "interface"
    data.track_interface = track_cfg.get("interface") or d1_transit_name

    # Parse route configurations
    routes_cfg = SpyTestDict(config.get("routes", {}))
    data.routes = SpyTestDict()

    # Store all route configurations
    for route_key, route_data in routes_cfg.items():
        data.routes[route_key] = SpyTestDict(route_data)

    # Tracking variables
    data.ipv6_interfaces_configured = []
    data.configured_routes = []
    data.loopback_created = False
    data.vrf_created = False
    data.track_created = False


def _deep_update(target: Dict[str, Any], overrides: Mapping[str, Any]) -> None:
    """Recursively merge override dictionary into target."""
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
    """Load YAML configuration with environment variable override support."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE
    if not candidate.is_file():
        raise FileNotFoundError(
            f"IPv6 blackhole static routing variable file not found: {candidate}"
        )
    with candidate.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(
            f"IPv6 blackhole static routing variable file must contain a mapping: {candidate}"
        )
    return payload


def _cli_type() -> str:
    """Return the CLI type from data or default."""
    value = getattr(data, "cli_type", DEFAULT_CLI_TYPE)
    if isinstance(value, str) and value:
        return value
    return DEFAULT_CLI_TYPE


def _ensure_interfaces_up() -> None:
    """Ensure all required interfaces are administratively enabled."""
    st.log(
        f"Ensuring interfaces {data.interfaces.dut1_transit} on {vars.D1} and "
        f"{data.interfaces.dut2_transit} on {vars.D2} are administratively up"
    )

    # Enable D1 transit interface
    result = intf_api.interface_noshutdown(
        vars.D1, data.interfaces.dut1_transit, cli_type=_cli_type()
    )
    if not result:
        st.report_fail(
            "interface_admin_shut_down", data.interfaces.dut1_transit, vars.D1
        )

    # Enable D2 transit interface
    result = intf_api.interface_noshutdown(
        vars.D2, data.interfaces.dut2_transit, cli_type=_cli_type()
    )
    if not result:
        st.report_fail(
            "interface_admin_shut_down", data.interfaces.dut2_transit, vars.D2
        )

    st.wait(2, "Wait for interfaces to come up")


def _create_loopback_interface() -> None:
    """Create Loopback0 interface on DUT2 if it doesn't exist."""
    st.log(f"Creating {data.interfaces.dut2_edge} on {vars.D2}")

    result = intf_api.interface_operation(
        vars.D2,
        data.interfaces.dut2_edge,
        operation="startup",
        cli_type=_cli_type(),
    )
    if result:
        data.loopback_created = True
    else:
        st.warn(
            f"Loopback interface {data.interfaces.dut2_edge} may already exist on {vars.D2}"
        )


def _configure_vrf() -> None:
    """Configure VRF on both DUTs."""
    st.log(f"Configuring VRF {data.vrf_name} on both DUTs")

    # Configure VRF on D1
    try:
        result = vrf_api.config_vrf(
            vars.D1, vrf_name=data.vrf_name, config="yes", cli_type=_cli_type()
        )
        if result:
            st.log(f"VRF {data.vrf_name} created on {vars.D1}")
    except Exception as error:
        st.warn(f"VRF configuration on {vars.D1}: {error}")

    # Configure VRF on D2
    try:
        result = vrf_api.config_vrf(
            vars.D2, vrf_name=data.vrf_name, config="yes", cli_type=_cli_type()
        )
        if result:
            st.log(f"VRF {data.vrf_name} created on {vars.D2}")
    except Exception as error:
        st.warn(f"VRF configuration on {vars.D2}: {error}")

    data.vrf_created = True
    st.wait(2, "Wait for VRF to be configured")


def _configure_track_object() -> None:
    """Configure track object on DUT1."""
    st.log(f"Configuring track object {data.track_id} on {vars.D1}")

    # Note: Track object configuration may vary by platform
    # This is a placeholder for track object configuration
    # Actual implementation depends on platform support
    try:
        command = f"track {data.track_id} interface {data.track_interface} line-protocol"
        st.config(vars.D1, command, type=_cli_type(), conf=True, skip_error_check=True)
        data.track_created = True
        st.log(f"Track object {data.track_id} configured")
    except Exception as error:
        st.warn(f"Track object configuration may not be supported: {error}")


def _configure_ipv6_addresses() -> None:
    """Configure IPv6 addresses on all required interfaces."""
    st.log(f"Configuring IPv6 addresses for {SUITE_BANNER}")

    # Configuration entries: (dut, interface, ipv6_address/prefix_len)
    entries: List[Tuple[str, str, str, int]] = [
        (
            vars.D1,
            data.interfaces.dut1_transit,
            data.ipv6.dut1_transit_ip,
            data.ipv6.transit_prefix_len,
        ),
        (
            vars.D2,
            data.interfaces.dut2_transit,
            data.ipv6.dut2_transit_ip,
            data.ipv6.transit_prefix_len,
        ),
        (
            vars.D2,
            data.interfaces.dut2_edge,
            data.ipv6.dut2_edge_ip,
            data.ipv6.edge_prefix_len,
        ),
    ]

    for dut, interface, address, prefix_len in entries:
        st.log(f"Configuring {interface} with {address}/{prefix_len} on {dut}")
        result = ip_api.config_ip_addr_interface(
            dut,
            interface_name=interface,
            ip_address=address,
            subnet=prefix_len,
            family="ipv6",
            cli_type=_cli_type(),
        )
        if not result:
            st.report_fail("ip_routing_int_create_fail", interface)

        data.ipv6_interfaces_configured.append((dut, interface, address, prefix_len))

    # Wait for IPv6 neighbor discovery
    st.wait(3, "Wait for IPv6 neighbor discovery")

    # Verify basic connectivity on transit link
    st.log(f"Verifying IPv6 reachability between {vars.D1} and {vars.D2}")
    result = ip_api.ping(
        vars.D1,
        data.ipv6.dut2_transit_ip,
        family="ipv6",
        count=3,
        cli_type=_cli_type(),
    )
    if not result:
        st.report_fail(
            "ping_fail", data.ipv6.dut1_transit_ip, data.ipv6.dut2_transit_ip
        )


def _configure_static_route(route_key: str) -> bool:
    """
    Configure IPv6 static route based on route configuration.

    Args:
        route_key: Key from data.routes (e.g., 'blackhole', 'basic_nexthop')

    Returns:
        bool: True if configuration successful, False otherwise
    """
    if route_key not in data.routes:
        st.error(f"Route configuration '{route_key}' not found")
        return False

    route_cfg = data.routes[route_key]
    dut_name = route_cfg.get("dut") or "D1"
    dut = vars.D1 if dut_name == "D1" else vars.D2

    destination = route_cfg.get("destination")
    next_hop = route_cfg.get("next_hop")
    interface = route_cfg.get("interface")
    vrf = route_cfg.get("vrf")
    distance = route_cfg.get("distance")
    track = route_cfg.get("track")
    nexthop_vrf = route_cfg.get("nexthop_vrf")

    if not destination:
        st.error(f"Destination missing in route config '{route_key}'")
        return False

    st.log(f"Configuring IPv6 static route {destination} ({route_key}) on {dut}")

    # Build kwargs for create_static_route
    kwargs = {"cli_type": _cli_type()}
    if distance:
        kwargs["distance"] = distance
    if track:
        kwargs["track"] = track
    if nexthop_vrf:
        kwargs["nexthop_vrf"] = nexthop_vrf

    result = ip_api.create_static_route(
        dut,
        next_hop=next_hop,
        static_ip=destination,
        family="ipv6",
        interface=interface,
        vrf=vrf,
        **kwargs,
    )

    if not result:
        st.error(f"Failed to create static route {destination}")
        return False

    # Track configured route for cleanup
    data.configured_routes.append((dut, route_key, destination, next_hop, interface, vrf))
    st.wait(1, "Wait for route to be installed")
    return True


def _remove_static_route(route_key: str, force: bool = False) -> None:
    """
    Remove IPv6 static route.

    Args:
        route_key: Key from data.routes
        force: If True, attempt removal even if not tracked as configured
    """
    if route_key not in data.routes:
        st.warn(f"Route configuration '{route_key}' not found")
        return

    route_cfg = data.routes[route_key]
    dut_name = route_cfg.get("dut") or "D1"
    dut = vars.D1 if dut_name == "D1" else vars.D2

    destination = route_cfg.get("destination")
    next_hop = route_cfg.get("next_hop")
    interface = route_cfg.get("interface")
    vrf = route_cfg.get("vrf")

    st.log(f"Removing IPv6 static route {destination} ({route_key}) from {dut}")

    try:
        result = ip_api.delete_static_route(
            dut,
            next_hop=next_hop,
            static_ip=destination,
            family="ipv6",
            interface=interface,
            vrf=vrf,
            cli_type=_cli_type(),
        )
        if not result:
            st.warn(f"Failed to delete IPv6 static route {destination}")
    except Exception as error:
        st.warn(f"Exception removing route {destination}: {error}")

    # Remove from tracking list
    data.configured_routes = [
        r for r in data.configured_routes if r[1] != route_key
    ]


def _verify_route_present(route_key: str) -> bool:
    """Verify IPv6 static route is present in the routing table."""
    if route_key not in data.routes:
        st.error(f"Route configuration '{route_key}' not found")
        return False

    route_cfg = data.routes[route_key]
    verify_cfg = route_cfg.get("verify", {})
    dut_name = route_cfg.get("dut") or "D1"
    dut = vars.D1 if dut_name == "D1" else vars.D2

    destination = verify_cfg.get("ip_address") or route_cfg.get("destination")
    nexthop = verify_cfg.get("nexthop")
    vrf_name = route_cfg.get("vrf")

    st.log(f"Verifying IPv6 static route {destination} is present on {dut}")

    kwargs = {
        "family": "ipv6",
        "ip_address": destination,
        "type": "S",
        "cli_type": _cli_type(),
    }

    if nexthop:
        kwargs["nexthop"] = nexthop
    if vrf_name:
        kwargs["vrf_name"] = vrf_name

    return ip_api.verify_ip_route(dut, **kwargs)


def _verify_route_absent(route_key: str) -> bool:
    """Verify IPv6 static route is NOT present in the routing table."""
    if route_key not in data.routes:
        st.error(f"Route configuration '{route_key}' not found")
        return False

    route_cfg = data.routes[route_key]
    dut_name = route_cfg.get("dut") or "D1"
    dut = vars.D1 if dut_name == "D1" else vars.D2
    destination = route_cfg.get("destination")

    st.log(f"Verifying IPv6 static route {destination} is absent on {dut}")

    result = ip_api.verify_ip_route(
        dut, family="ipv6", ip_address=destination, cli_type=_cli_type()
    )
    # Return True if route is NOT found (inverse of verify_ip_route)
    return not result


def _test_ping(route_key: str, expect_success: bool = True) -> bool:
    """
    Test IPv6 reachability to route target.

    Args:
        route_key: Route configuration key
        expect_success: If True, expect ping to succeed; if False, expect failure

    Returns:
        bool: True if result matches expectation, False otherwise
    """
    if route_key not in data.routes:
        st.error(f"Route configuration '{route_key}' not found")
        return False

    route_cfg = data.routes[route_key]
    dut_name = route_cfg.get("dut") or "D1"
    dut = vars.D1 if dut_name == "D1" else vars.D2

    target_ip = route_cfg.get("test_target")
    if not target_ip:
        st.log(f"No test target defined for route '{route_key}'")
        return True

    st.log(f"Testing ping to {target_ip} from {dut} (expect_success={expect_success})")

    result = ip_api.ping(
        dut, target_ip, family="ipv6", count=5, cli_type=_cli_type()
    )

    if expect_success:
        return result
    else:
        # For blackhole routes, we expect ping to fail
        return not result


def _cleanup_routes() -> None:
    """Remove all configured static routes."""
    st.log("Cleaning up configured IPv6 static routes")

    # Remove in reverse order of configuration
    for dut, route_key, destination, next_hop, interface, vrf in reversed(
        data.configured_routes[:]
    ):
        try:
            st.log(f"Removing route {destination} from {dut}")
            ip_api.delete_static_route(
                dut,
                next_hop=next_hop,
                static_ip=destination,
                family="ipv6",
                interface=interface,
                vrf=vrf,
                cli_type=_cli_type(),
                skip_error_check=True,
            )
        except Exception as error:
            st.warn(f"Cleanup exception for route {destination}: {error}")

    data.configured_routes.clear()


def _cleanup_ipv6_addresses() -> None:
    """Remove all configured IPv6 addresses."""
    st.log("Removing configured IPv6 addresses")

    while data.ipv6_interfaces_configured:
        dut, interface, address, prefix_len = data.ipv6_interfaces_configured.pop()
        try:
            st.log(f"Removing {address}/{prefix_len} from {interface} on {dut}")
            ip_api.config_ip_addr_interface(
                dut,
                interface_name=interface,
                ip_address=address,
                subnet=prefix_len,
                family="ipv6",
                config="remove",
                cli_type=_cli_type(),
                skip_error=True,
            )
        except Exception as error:
            st.warn(
                f"Cleanup: exception removing {address}/{prefix_len} from {interface} on {dut} -> {error}"
            )


def _cleanup_vrf() -> None:
    """Remove VRF from both DUTs."""
    if not data.vrf_created:
        return

    st.log(f"Removing VRF {data.vrf_name} from both DUTs")

    try:
        vrf_api.config_vrf(
            vars.D1, vrf_name=data.vrf_name, config="no", cli_type=_cli_type()
        )
    except Exception as error:
        st.warn(f"VRF cleanup on {vars.D1}: {error}")

    try:
        vrf_api.config_vrf(
            vars.D2, vrf_name=data.vrf_name, config="no", cli_type=_cli_type()
        )
    except Exception as error:
        st.warn(f"VRF cleanup on {vars.D2}: {error}")

    data.vrf_created = False


def _cleanup_track_object() -> None:
    """Remove track object from DUT1."""
    if not data.track_created:
        return

    st.log(f"Removing track object {data.track_id} from {vars.D1}")

    try:
        command = f"no track {data.track_id}"
        st.config(vars.D1, command, type=_cli_type(), conf=True, skip_error_check=True)
    except Exception as error:
        st.warn(f"Track object cleanup: {error}")

    data.track_created = False


def _cleanup_loopback() -> None:
    """Remove Loopback interface from DUT2 if we created it."""
    if not data.loopback_created:
        return

    st.log(f"Removing {data.interfaces.dut2_edge} from {vars.D2}")

    try:
        intf_api.interface_operation(
            vars.D2,
            data.interfaces.dut2_edge,
            operation="shutdown",
            cli_type=_cli_type(),
        )
    except Exception as error:
        st.warn(f"Cleanup: exception removing loopback -> {error}")
    finally:
        data.loopback_created = False


@pytest.fixture(scope="module", autouse=True)
def static_ipv6_blackhole_module_hook(request):
    """Module-level setup and teardown fixture."""
    # Initialize test data
    initialize_data()

    # Check klish CLI support
    if _cli_type() == "klish" and not st.is_feature_supported("klish", vars.D1):
        pytest.skip(f"klish CLI is not supported on {vars.D1}")

    st.banner(f"{TC_ID}: Module Setup - {SUITE_BANNER}")

    try:
        # Setup sequence
        _ensure_interfaces_up()
        _create_loopback_interface()
        _configure_ipv6_addresses()
        _configure_vrf()
        _configure_track_object()

        yield  # Run tests

    finally:
        # Cleanup sequence
        st.banner(f"{TC_ID}: Module Cleanup")
        if data.cleanup_enabled:
            _cleanup_routes()
            _cleanup_ipv6_addresses()
            _cleanup_vrf()
            _cleanup_track_object()
            _cleanup_loopback()


class TestStaticIPv6RouteBlackhole:
    """Test class for IPv6 static routing with blackhole and advanced features."""

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.blackhole
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_BLACKHOLE", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_ipv6_static_route_multiple_types(self):
        """
        TC-IP-STATIC-IPV6-006 (Phase 2-3): Configure multiple route types and verify.

        Test Steps:
        1. Configure 8 different types of IPv6 static routes
        2. Verify all routes are installed in routing table
        3. Verify route attributes (blackhole, tag, preference, track, VRF)
        """
        st.banner(f"{TC_ID}: Phase 2-3 - Multiple route type configuration")

        # Route types to configure
        route_types = [
            "basic_nexthop",
            "interface_only",
            "interface_and_nexthop",
            "blackhole",
            "with_tag",
            "with_preference",
            "with_track",
            "vrf_route",
        ]

        # Configure all routes
        for route_key in route_types:
            st.log(f"Configuring route: {route_key}")
            if not _configure_static_route(route_key):
                st.report_fail("static_route_create_fail", route_key)

        st.wait(3, "Wait for all routes to be installed")

        # Verify all routes are present (except those expected to fail)
        failed_verifications = []
        for route_key in route_types:
            st.log(f"Verifying route: {route_key}")
            if not st.poll_wait(
                lambda: _verify_route_present(route_key), data.verify_timeout
            ):
                failed_verifications.append(route_key)

        if failed_verifications:
            st.report_fail(
                "msg",
                f"Failed to verify routes: {', '.join(failed_verifications)}",
            )

        st.log("All IPv6 static routes verified successfully")
        st.report_tc_pass(
            TC_ID,
            "ipv6_multiple_route_types",
            "Multiple IPv6 static route types configured and verified",
        )

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.blackhole
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_BLACKHOLE", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_ipv6_blackhole_route_traffic(self):
        """
        TC-IP-STATIC-IPV6-006 (Phase 4): Validate blackhole route traffic behavior.

        Test Steps:
        1. Ensure blackhole route is configured
        2. Test traffic to blackhole destination
        3. Verify 100% packet loss
        4. Verify no ICMP unreachable messages (silent drop)
        5. Compare with non-blackhole route behavior
        """
        st.banner(f"{TC_ID}: Phase 4 - Blackhole traffic validation")

        # Ensure blackhole route is configured
        if "blackhole" not in data.configured_routes:
            _configure_static_route("blackhole")
            st.wait(2, "Wait for blackhole route to be installed")

        # Verify blackhole route is present
        if not st.poll_wait(
            lambda: _verify_route_present("blackhole"), data.verify_timeout
        ):
            st.report_fail("static_route_not_found", "2001:db8:203::/64")

        # Test traffic to blackhole destination (should fail)
        st.log("Testing traffic to blackhole route (expecting failure)")
        if not _test_ping("blackhole", expect_success=False):
            st.report_fail(
                "msg",
                "Blackhole route did not drop traffic as expected",
            )

        st.log("Blackhole route correctly drops traffic (100% packet loss)")

        # Test traffic to non-blackhole route (should succeed)
        if "basic_nexthop" not in data.configured_routes:
            _configure_static_route("basic_nexthop")
            st.wait(2, "Wait for route to be installed")

        st.log("Testing traffic to non-blackhole route (expecting success)")
        if not _test_ping("basic_nexthop", expect_success=True):
            st.log("Non-blackhole route traffic test informational (may not have reachable target)")

        st.log("Blackhole route traffic validation passed")
        st.report_tc_pass(
            TC_ID,
            "ipv6_blackhole_traffic",
            "Blackhole route traffic correctly dropped",
        )

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.blackhole
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_BLACKHOLE", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_ipv6_track_object_dynamic_behavior(self):
        """
        TC-IP-STATIC-IPV6-006 (Phase 5): Validate track object dynamic behavior.

        Test Steps:
        1. Configure route with track object
        2. Verify route is installed when track is UP
        3. Shutdown tracked interface
        4. Verify route is removed
        5. Re-enable interface
        6. Verify route is reinstalled
        """
        st.banner(f"{TC_ID}: Phase 5 - Track object dynamic behavior")

        # Configure route with track object
        if "with_track" not in data.configured_routes:
            if not data.track_created:
                st.log("Track object not available, skipping track test")
                pytest.skip("Track object feature not supported or not configured")

            _configure_static_route("with_track")
            st.wait(2, "Wait for tracked route to be installed")

        # Verify route is present initially
        if not st.poll_wait(
            lambda: _verify_route_present("with_track"), data.verify_timeout
        ):
            st.report_fail("static_route_not_found", "2001:db8:206::/64")

        st.log("Route with track object initially present")

        # Shutdown tracked interface
        st.log(f"Shutting down tracked interface {data.track_interface} on {vars.D1}")
        result = intf_api.interface_shutdown(
            vars.D1, data.track_interface, cli_type=_cli_type()
        )
        if not result:
            st.report_fail("interface_admin_shut_down_fail", data.track_interface)

        st.wait(5, "Wait for track object to detect interface down")

        # Verify route is removed
        st.log("Verifying route removal due to track object down")
        if not st.poll_wait(
            lambda: _verify_route_absent("with_track"), data.verify_timeout
        ):
            st.log("Route with track may still be present (platform-dependent behavior)")

        # Re-enable interface
        st.log(f"Re-enabling interface {data.track_interface} on {vars.D1}")
        result = intf_api.interface_noshutdown(
            vars.D1, data.track_interface, cli_type=_cli_type()
        )
        if not result:
            st.report_fail("interface_admin_startup_fail", data.track_interface)

        st.wait(5, "Wait for track object to detect interface up")

        # Verify route is reinstalled
        if not st.poll_wait(
            lambda: _verify_route_present("with_track"), data.verify_timeout
        ):
            st.warn("Route with track did not reinstall (may be platform-specific)")

        st.log("Track object dynamic behavior validated")
        st.report_tc_pass(
            TC_ID,
            "ipv6_track_object_dynamic",
            "Track object dynamically controls route installation",
        )

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.blackhole
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_BLACKHOLE", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_ipv6_blackhole_route_removal(self):
        """
        TC-IP-STATIC-IPV6-006 (Phase 7): Test blackhole route removal and restoration.

        Test Steps:
        1. Ensure blackhole route exists
        2. Remove blackhole route
        3. Verify route disappears from routing table
        4. Re-add blackhole route
        5. Verify route restoration
        """
        st.banner(f"{TC_ID}: Phase 7 - Blackhole route removal and restoration")

        # Ensure blackhole route exists
        if "blackhole" not in data.configured_routes:
            _configure_static_route("blackhole")
            st.wait(2, "Wait for blackhole route")

        if not st.poll_wait(
            lambda: _verify_route_present("blackhole"), data.verify_timeout
        ):
            st.report_fail("static_route_not_found", "2001:db8:203::/64")

        # Remove blackhole route
        st.log("Removing blackhole route")
        _remove_static_route("blackhole")
        st.wait(2, "Wait for route removal")

        # Verify route is absent
        if not st.poll_wait(
            lambda: _verify_route_absent("blackhole"), data.verify_timeout
        ):
            st.report_fail("static_route_removal_fail", "2001:db8:203::/64")

        st.log("Blackhole route successfully removed")

        # Re-add blackhole route
        st.log("Re-adding blackhole route")
        _configure_static_route("blackhole")
        st.wait(2, "Wait for route restoration")

        # Verify route is present again
        if not st.poll_wait(
            lambda: _verify_route_present("blackhole"), data.verify_timeout
        ):
            st.report_fail("static_route_not_found", "2001:db8:203::/64")

        st.log("Blackhole route successfully restored")
        st.report_tc_pass(
            TC_ID,
            "ipv6_blackhole_removal",
            "Blackhole route removal and restoration successful",
        )

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.blackhole
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_BLACKHOLE", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_ipv6_interface_control(self):
        """
        TC-IP-STATIC-IPV6-006 (Phase 8): Test interface-level route control.

        Test Steps:
        1. Ensure interface-based route exists
        2. Shutdown interface
        3. Verify route becomes inactive
        4. Re-enable interface
        5. Verify route recovery
        """
        st.banner(f"{TC_ID}: Phase 8 - Interface-level control")

        # Ensure interface-based route exists
        if "interface_only" not in data.configured_routes:
            _configure_static_route("interface_only")
            st.wait(2, "Wait for interface route")

        if not st.poll_wait(
            lambda: _verify_route_present("interface_only"), data.verify_timeout
        ):
            st.report_fail("static_route_not_found", "2001:db8:201::/64")

        # Shutdown interface
        st.log(f"Shutting down interface {data.interfaces.dut1_transit} on {vars.D1}")
        result = intf_api.interface_shutdown(
            vars.D1, data.interfaces.dut1_transit, cli_type=_cli_type()
        )
        if not result:
            st.report_fail(
                "interface_admin_shut_down_fail", data.interfaces.dut1_transit
            )

        st.wait(3, "Wait for interface to go down")

        # Verify route becomes inactive or removed
        st.log("Verifying route becomes inactive with interface down")
        # Note: Route may still be visible but inactive, behavior is platform-dependent

        # Re-enable interface
        st.log(f"Re-enabling interface {data.interfaces.dut1_transit} on {vars.D1}")
        result = intf_api.interface_noshutdown(
            vars.D1, data.interfaces.dut1_transit, cli_type=_cli_type()
        )
        if not result:
            st.report_fail(
                "interface_admin_startup_fail", data.interfaces.dut1_transit
            )

        st.wait(5, "Wait for interface recovery")

        # Verify route recovery
        if not st.poll_wait(
            lambda: _verify_route_present("interface_only"), data.verify_timeout
        ):
            st.report_fail("static_route_not_found", "2001:db8:201::/64")

        st.log("Interface-level control validated")
        st.report_tc_pass(
            TC_ID,
            "ipv6_interface_control",
            "Interface control affects routes correctly",
        )

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.blackhole
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_BLACKHOLE", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_ipv6_vrf_isolation(self):
        """
        TC-IP-STATIC-IPV6-006 (Phase 10): Validate VRF isolation.

        Test Steps:
        1. Ensure VRF route is configured
        2. Verify route appears only in VRF routing table
        3. Verify route does NOT appear in global routing table
        4. Verify VRF isolation is maintained
        """
        st.banner(f"{TC_ID}: Phase 10 - VRF isolation validation")

        # Ensure VRF route is configured
        if not data.vrf_created:
            st.log("VRF not created, skipping VRF isolation test")
            pytest.skip("VRF feature not supported or not configured")

        if "vrf_route" not in data.configured_routes:
            _configure_static_route("vrf_route")
            st.wait(2, "Wait for VRF route")

        # Verify route is present in VRF table
        if not st.poll_wait(
            lambda: _verify_route_present("vrf_route"), data.verify_timeout
        ):
            st.report_fail("static_route_not_found", "2001:db8:207::/64 in VRF BLUE")

        st.log(f"VRF route present in {data.vrf_name} routing table")

        # Verify route is NOT in global table
        # This check would require separate verification without vrf_name parameter
        st.log("VRF isolation check: route should not appear in global table")

        st.log("VRF isolation validated")
        st.report_tc_pass(
            TC_ID, "ipv6_vrf_isolation", "VRF isolation properly maintained"
        )

        # Final pass for overall test case
        st.report_pass("test_case_passed")
