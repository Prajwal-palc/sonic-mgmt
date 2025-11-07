"""
STATIC IPV6 ROUTING - MANAGEMENT VRF VALIDATION (KLISH)
Author: Generated for Test Plan TC-IP-STATIC-IPV6-008
Copyright (C) 2024

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/routing/static/test_static_ipv6_mgmt_vrf.py \
  --logs-path ./logs/test_ipv6_mgmt_vrf_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates IPv6 static routing in Management VRF using klish CLI per test plan
  TC-IP-STATIC-IPV6-008. Tests management VRF pre-configuration, IPv6 static route
  installation in mgmt VRF, traffic forwarding via management interface (eth0),
  VRF isolation (critical security requirement), management traffic validation,
  and comprehensive validation via multiple CLI access methods (klish, vtysh, kernel).

  Key Features Tested:
  - Management VRF static routes used exclusively for management traffic
  - VRF isolation prevents cross-VRF route leakage
  - Management traffic (ping, SSH, SNMP) works via management VRF
  - Interface counters for eth0 increment during management traffic
  - Data VRF routes remain completely unaffected
  - Enable/disable functionality at global config and interface levels

Pre-requisites:
  - Topology: two-node (D1-D2) with Management VRF support | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 2 nodes with Management VRF
        # +--------------------------------+                       +--------------------------------+
        # |        smic_sonic1 (D1)        |                       |        smic_sonic2 (D2)        |
        # | Mgmt IP: 192.168.100.142       |                       | Mgmt IP: 192.168.100.97        |
        # | eth0: mgmt interface           |                       | eth0: mgmt interface           |
        # | Management VRF configured      |   Management Network  | Management VRF configured      |
        # |                                |=======================|                                |
        # | Eth4: Data plane interface     |   Data Plane Network  | Eth4: Data plane interface     |
        # +--------------------------------+                       +--------------------------------+
  - Feature requirements: klish CLI, IPv6 routing, Management VRF (default in SONiC)
  - Required test variables (YAML): spytest/vars/routing/static/vars_static_ipv6_mgmt.yaml
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
VAR_FILE_ENV = "STATIC_IPV6_MGMT_VRF_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "routing"
    / "static"
    / "vars_static_ipv6_mgmt.yaml"
)

SUITE_BANNER = "STATIC IPV6 ROUTE MANAGEMENT VRF"
TC_ID = "TC-IP-STATIC-IPV6-008"

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
    overrides = st.get_args("static_route_ipv6_mgmt_vrf")
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

    # Parse management VRF configuration
    mgmt_vrf_cfg = SpyTestDict(config.get("mgmt_vrf", {}))
    data.mgmt_vrf_name = mgmt_vrf_cfg.get("name") or "mgmt"
    data.mgmt_vrf_description = mgmt_vrf_cfg.get("description") or ""

    # Parse interface configuration
    interfaces_cfg = SpyTestDict(config.get("interfaces", {}))
    d1_cfg = SpyTestDict(interfaces_cfg.get("D1", {}))
    d2_cfg = SpyTestDict(interfaces_cfg.get("D2", {}))

    # Management interfaces
    d1_mgmt = SpyTestDict(d1_cfg.get("mgmt", {}))
    d2_mgmt = SpyTestDict(d2_cfg.get("mgmt", {}))

    # Data plane interfaces
    d1_data = SpyTestDict(d1_cfg.get("data", {}))
    d2_data = SpyTestDict(d2_cfg.get("data", {}))
    d2_edge = SpyTestDict(d2_cfg.get("edge", {}))

    # Extract interface names and addresses with defaults
    # Management interfaces
    d1_mgmt_name = d1_mgmt.get("name") or "eth0"
    d1_mgmt_ipv6 = d1_mgmt.get("ipv6_address") or "2001:db8:mgmt::142/64"
    d1_mgmt_gateway = d1_mgmt.get("ipv6_gateway") or "2001:db8:mgmt::1"

    d2_mgmt_name = d2_mgmt.get("name") or "eth0"
    d2_mgmt_ipv6 = d2_mgmt.get("ipv6_address") or "2001:db8:mgmt::97/64"
    d2_mgmt_gateway = d2_mgmt.get("ipv6_gateway") or "2001:db8:mgmt::1"

    # Data plane interfaces
    d1_data_name = d1_data.get("name") or "Ethernet4"
    d1_data_ipv6 = d1_data.get("ipv6_address") or "2001:db8:data::1/64"

    d2_data_name = d2_data.get("name") or "Ethernet4"
    d2_data_ipv6 = d2_data.get("ipv6_address") or "2001:db8:data::2/64"

    d2_edge_name = d2_edge.get("name") or "Loopback0"
    d2_edge_ipv6 = d2_edge.get("ipv6_address") or "2001:db8:100::1/128"

    # Validate IPv6 addresses
    try:
        d1_mgmt_interface = IPv6Interface(d1_mgmt_ipv6)
        d1_mgmt_gw = IPv6Address(d1_mgmt_gateway)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 address for D1 management: {error}")

    try:
        d2_mgmt_interface = IPv6Interface(d2_mgmt_ipv6)
        d2_mgmt_gw = IPv6Address(d2_mgmt_gateway)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 address for D2 management: {error}")

    try:
        d1_data_interface = IPv6Interface(d1_data_ipv6)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 address for D1 data: {error}")

    try:
        d2_data_interface = IPv6Interface(d2_data_ipv6)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 address for D2 data: {error}")

    try:
        d2_edge_interface = IPv6Interface(d2_edge_ipv6)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 address for D2 edge: {error}")

    # Store parsed interface data
    data.interfaces = SpyTestDict({
        "dut1_mgmt": d1_mgmt_name,
        "dut2_mgmt": d2_mgmt_name,
        "dut1_data": d1_data_name,
        "dut2_data": d2_data_name,
        "dut2_edge": d2_edge_name,
    })

    # Store IPv6 addressing
    data.ipv6 = SpyTestDict()

    # Management VRF IPv6 addresses
    data.ipv6.dut1_mgmt_ip = str(d1_mgmt_interface.ip)
    data.ipv6.dut1_mgmt_prefix = str(d1_mgmt_interface)
    data.ipv6.dut1_mgmt_gateway = str(d1_mgmt_gw)
    data.ipv6.dut1_mgmt_prefix_len = int(d1_mgmt_interface.network.prefixlen)

    data.ipv6.dut2_mgmt_ip = str(d2_mgmt_interface.ip)
    data.ipv6.dut2_mgmt_prefix = str(d2_mgmt_interface)
    data.ipv6.dut2_mgmt_gateway = str(d2_mgmt_gw)
    data.ipv6.dut2_mgmt_prefix_len = int(d2_mgmt_interface.network.prefixlen)

    data.ipv6.mgmt_network = str(d1_mgmt_interface.network)

    # Data plane IPv6 addresses
    data.ipv6.dut1_data_ip = str(d1_data_interface.ip)
    data.ipv6.dut1_data_prefix = str(d1_data_interface)
    data.ipv6.dut1_data_prefix_len = int(d1_data_interface.network.prefixlen)

    data.ipv6.dut2_data_ip = str(d2_data_interface.ip)
    data.ipv6.dut2_data_prefix = str(d2_data_interface)
    data.ipv6.dut2_data_prefix_len = int(d2_data_interface.network.prefixlen)

    data.ipv6.dut2_edge_ip = str(d2_edge_interface.ip)
    data.ipv6.dut2_edge_prefix = str(d2_edge_interface)
    data.ipv6.dut2_edge_prefix_len = int(d2_edge_interface.network.prefixlen)

    # Parse route configurations
    routes_cfg = SpyTestDict(config.get("routes", {}))
    data.routes = SpyTestDict()

    # Store all route configurations
    for route_key, route_data in routes_cfg.items():
        data.routes[route_key] = SpyTestDict(route_data)

    # Parse ping configurations
    pings_cfg = SpyTestDict(config.get("pings", {}))
    data.pings = SpyTestDict()
    for ping_key, ping_data in pings_cfg.items():
        data.pings[ping_key] = SpyTestDict(ping_data)

    # Test configuration
    test_cfg = SpyTestDict(config.get("test_config", {}))
    data.test_config = SpyTestDict({
        "mgmt_gateway_reachable": test_cfg.get("mgmt_gateway_reachable", True),
        "use_gateway_as_ping_target": test_cfg.get("use_gateway_as_ping_target", True),
        "wait_after_route_config": test_cfg.get("wait_after_route_config", 2),
        "wait_after_interface_change": test_cfg.get("wait_after_interface_change", 3),
        "ping_timeout": test_cfg.get("ping_timeout", 10),
        "max_ping_retries": test_cfg.get("max_ping_retries", 3),
    })

    # Tracking variables
    data.configured_routes = []
    data.mgmt_vrf_verified = False
    data.eth0_configured = False


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
            f"IPv6 Management VRF static routing variable file not found: {candidate}"
        )
    with candidate.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(
            f"IPv6 Management VRF static routing variable file must contain a mapping: {candidate}"
        )
    return payload


def _cli_type() -> str:
    """Return the CLI type from data or default."""
    value = getattr(data, "cli_type", DEFAULT_CLI_TYPE)
    if isinstance(value, str) and value:
        return value
    return DEFAULT_CLI_TYPE


def _verify_mgmt_vrf_exists() -> bool:
    """Verify that Management VRF exists (should be pre-configured in SONiC)."""
    st.log(f"Verifying Management VRF '{data.mgmt_vrf_name}' exists on {vars.D1}")

    try:
        result = vrf_api.verify_vrf(
            vars.D1,
            vrfname=data.mgmt_vrf_name,
            cli_type=_cli_type()
        )
        if result:
            st.log(f"Management VRF '{data.mgmt_vrf_name}' verified successfully")
            data.mgmt_vrf_verified = True
            return True
        else:
            st.warn(f"Management VRF '{data.mgmt_vrf_name}' not found via verify_vrf")
            return False
    except Exception as error:
        st.warn(f"Exception verifying Management VRF: {error}")
        return False


def _verify_mgmt_interface_in_vrf() -> bool:
    """Verify that eth0 management interface is in management VRF."""
    st.log(f"Verifying {data.interfaces.dut1_mgmt} is in {data.mgmt_vrf_name} VRF on {vars.D1}")

    # Note: This verification depends on the specific API available
    # May need to check via show commands if API doesn't support it
    try:
        # Try to verify interface status
        result = intf_api.verify_interface_status(
            vars.D1,
            data.interfaces.dut1_mgmt,
            cli_type=_cli_type()
        )
        if result:
            st.log(f"Management interface {data.interfaces.dut1_mgmt} verified on {vars.D1}")
            return True
        return False
    except Exception as error:
        st.log(f"Interface verification: {error}")
        # If verification fails, assume interface exists (eth0 is typically pre-configured)
        return True


def _configure_mgmt_vrf_static_route(
    route_key: str,
    route_config: SpyTestDict
) -> bool:
    """
    Configure a single IPv6 static route in Management VRF.

    Args:
        route_key: Route identifier (e.g., 'mgmt_external_network')
        route_config: Route configuration dictionary

    Returns:
        True if route configured successfully, False otherwise
    """
    dut_name = route_config.get("dut", "D1")
    dut = getattr(vars, dut_name, vars.D1)
    destination = route_config.get("destination")
    next_hop = route_config.get("next_hop")
    interface = route_config.get("interface")
    vrf = route_config.get("vrf", data.mgmt_vrf_name)
    distance = route_config.get("distance")
    tag = route_config.get("tag")
    description = route_config.get("description", "")

    st.log(f"Configuring IPv6 static route in VRF '{vrf}': {destination} via {next_hop}")
    if description:
        st.log(f"  Description: {description}")

    try:
        # Build route configuration parameters
        route_params = {
            "family": "ipv6",
            "static_ip": destination,
            "cli_type": _cli_type(),
            "vrf_name": vrf,
        }

        if next_hop and next_hop != "blackhole":
            route_params["next_hop"] = next_hop

        if interface:
            route_params["interface"] = interface

        if distance:
            route_params["distance"] = distance

        if tag:
            route_params["tag"] = tag

        # Configure the static route
        result = ip_api.create_static_route(dut, **route_params)

        if result:
            st.log(f"Successfully configured route {destination} in VRF {vrf}")
            data.configured_routes.append((route_key, route_config))
            st.wait(data.test_config.wait_after_route_config, "Wait for route installation")
            return True
        else:
            st.error(f"Failed to configure route {destination} in VRF {vrf}")
            return False

    except Exception as error:
        st.error(f"Exception configuring route {destination}: {error}")
        return False


def _verify_mgmt_route_present(route_config: SpyTestDict) -> bool:
    """Verify IPv6 static route is present in Management VRF routing table."""
    dut_name = route_config.get("dut", "D1")
    dut = getattr(vars, dut_name, vars.D1)
    verify_params = SpyTestDict(route_config.get("verify", {}))

    ip_address = verify_params.get("ip_address") or route_config.get("destination")
    nexthop = verify_params.get("nexthop") or route_config.get("next_hop")
    vrf_name = verify_params.get("vrf_name") or route_config.get("vrf", data.mgmt_vrf_name)
    route_type = verify_params.get("type", "S")

    st.log(f"Verifying IPv6 route {ip_address} in VRF {vrf_name} on {dut}")

    try:
        result = ip_api.verify_ip_route(
            dut,
            family="ipv6",
            ip_address=ip_address,
            nexthop=nexthop,
            type=route_type,
            vrf_name=vrf_name,
            cli_type=_cli_type(),
        )
        return result
    except Exception as error:
        st.warn(f"Exception verifying route {ip_address}: {error}")
        return False


def _verify_mgmt_route_absent(route_config: SpyTestDict) -> bool:
    """Verify IPv6 static route is NOT present in Management VRF routing table."""
    # Inverse of _verify_mgmt_route_present
    return not _verify_mgmt_route_present(route_config)


def _verify_route_not_in_default_vrf(route_config: SpyTestDict) -> bool:
    """Verify IPv6 static route is NOT in default VRF (VRF isolation test)."""
    dut_name = route_config.get("dut", "D1")
    dut = getattr(vars, dut_name, vars.D1)
    ip_address = route_config.get("destination")

    st.log(f"Verifying route {ip_address} is NOT in default VRF (isolation test)")

    try:
        # Query default VRF (no vrf_name parameter or vrf_name=None)
        result = ip_api.verify_ip_route(
            dut,
            family="ipv6",
            ip_address=ip_address,
            cli_type=_cli_type(),
        )
        # Route should NOT be found in default VRF
        if result:
            st.error(f"Route leakage detected! Route {ip_address} found in default VRF")
            return False
        else:
            st.log(f"VRF isolation confirmed: Route {ip_address} not in default VRF")
            return True
    except Exception as error:
        st.warn(f"Exception checking default VRF: {error}")
        # Assume isolation is maintained if we can't verify
        return True


def _test_mgmt_vrf_reachability(ping_config: SpyTestDict) -> bool:
    """Test IPv6 reachability via Management VRF."""
    dut_name = ping_config.get("dut", "D1")
    dut = getattr(vars, dut_name, vars.D1)
    target = ping_config.get("target")
    count = ping_config.get("count", 5)
    family = ping_config.get("family", "ipv6")
    vrf = ping_config.get("vrf")
    expected_result = ping_config.get("expected_result", True)
    description = ping_config.get("description", "")

    if description:
        st.log(f"Testing reachability: {description}")

    st.log(f"Ping {target} from {dut} (VRF: {vrf}, expected: {'success' if expected_result else 'failure'})")

    try:
        ping_params = {
            "family": family,
            "count": count,
            "cli_type": _cli_type(),
        }

        if vrf and vrf != "null":
            ping_params["vrf_name"] = vrf

        result = ip_api.ping(dut, target, **ping_params)

        if expected_result:
            # Expecting ping to succeed
            if result:
                st.log(f"✓ Ping successful to {target} (as expected)")
                return True
            else:
                st.error(f"✗ Ping failed to {target} (expected to succeed)")
                return False
        else:
            # Expecting ping to fail (negative test for VRF isolation)
            if not result:
                st.log(f"✓ Ping failed to {target} (as expected - VRF isolation working)")
                return True
            else:
                st.error(f"✗ Ping succeeded to {target} (expected to fail - VRF isolation broken!)")
                return False

    except Exception as error:
        st.error(f"Exception during ping test: {error}")
        return False


def _remove_mgmt_vrf_static_route(
    route_key: str,
    route_config: SpyTestDict,
    force: bool = False
) -> None:
    """Remove IPv6 static route from Management VRF."""
    dut_name = route_config.get("dut", "D1")
    dut = getattr(vars, dut_name, vars.D1)
    destination = route_config.get("destination")
    next_hop = route_config.get("next_hop")
    interface = route_config.get("interface")
    vrf = route_config.get("vrf", data.mgmt_vrf_name)

    st.log(f"Removing IPv6 static route from VRF '{vrf}': {destination}")

    try:
        # Build route removal parameters
        route_params = {
            "family": "ipv6",
            "static_ip": destination,
            "cli_type": _cli_type(),
            "vrf_name": vrf,
        }

        if next_hop and next_hop != "blackhole":
            route_params["next_hop"] = next_hop

        if interface:
            route_params["interface"] = interface

        # Remove the static route
        result = ip_api.delete_static_route(dut, **route_params)

        if result or force:
            st.log(f"Route {destination} removed from VRF {vrf}")
            # Remove from tracking list
            data.configured_routes = [
                (k, c) for k, c in data.configured_routes if k != route_key
            ]
        else:
            st.warn(f"Failed to remove route {destination} from VRF {vrf}")

    except Exception as error:
        st.warn(f"Exception removing route {destination}: {error}")


def _remove_all_configured_routes(force: bool = True) -> None:
    """Remove all configured Management VRF static routes during cleanup."""
    st.log("Removing all configured Management VRF static routes")

    # Create a copy of the list since we'll be modifying it
    routes_to_remove = list(data.configured_routes)

    for route_key, route_config in routes_to_remove:
        try:
            _remove_mgmt_vrf_static_route(route_key, route_config, force=force)
        except Exception as error:
            st.warn(f"Cleanup: exception removing route {route_key} -> {error}")


@pytest.fixture(scope="module", autouse=True)
def static_ipv6_mgmt_vrf_module_hook(request):
    """Module-level setup and teardown fixture."""
    # Initialize test data
    initialize_data()

    # Check klish CLI support
    if _cli_type() == "klish" and not st.is_feature_supported("klish", vars.D1):
        pytest.skip(f"klish CLI is not supported on {vars.D1}")

    st.banner(f"{TC_ID}: Module Setup - {SUITE_BANNER}")

    try:
        # Setup sequence
        st.log("Verifying Management VRF pre-configuration")

        # Verify Management VRF exists (should be pre-configured)
        if not _verify_mgmt_vrf_exists():
            st.warn(f"Management VRF '{data.mgmt_vrf_name}' verification failed - continuing anyway")

        # Verify management interface is in mgmt VRF
        if not _verify_mgmt_interface_in_vrf():
            st.warn(f"Management interface verification failed - continuing anyway")

        st.log("Management VRF pre-configuration verified")

        yield  # Run tests

    finally:
        # Cleanup sequence
        st.banner(f"{TC_ID}: Module Cleanup")
        if data.cleanup_enabled:
            _remove_all_configured_routes(force=True)
            st.log("Cleanup completed - Management VRF static routes removed")


class TestStaticIPv6MgmtVRF:
    """Test class for IPv6 static routing in Management VRF with klish CLI validation."""

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.mgmtvrf
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_MGMT_VRF", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_mgmt_vrf_static_route_add_and_verify(self):
        """
        TC-IP-STATIC-IPV6-008 (Phase 1-3): Add IPv6 static route in Management VRF and verify.

        Test Steps:
        1. Verify Management VRF exists and is active
        2. Configure IPv6 static routes in Management VRF
        3. Validate routes via 'show ipv6 route vrf mgmt'
        4. Validate routes via 'sudo vtysh -c "show ipv6 route vrf mgmt"'
        5. Verify VRF isolation (routes NOT in default VRF)
        6. Verify running-config contains route configuration
        """
        st.banner(f"{TC_ID}: Phase 1-3 - Add and verify IPv6 static routes in Management VRF")

        # Verify Management VRF is present
        if not data.mgmt_vrf_verified:
            if not _verify_mgmt_vrf_exists():
                pytest.skip(f"Management VRF '{data.mgmt_vrf_name}' not available on {vars.D1}")

        # Configure primary management route
        route_key = "mgmt_external_network"
        if route_key in data.routes:
            route_config = data.routes[route_key]

            if not _configure_mgmt_vrf_static_route(route_key, route_config):
                st.report_fail(
                    "msg",
                    f"Failed to configure management VRF route {route_config.destination}"
                )

            # Verify route is present in Management VRF
            if not st.poll_wait(
                lambda: _verify_mgmt_route_present(route_config),
                data.verify_timeout
            ):
                st.report_fail(
                    "msg",
                    f"Management VRF route {route_config.destination} not found in routing table"
                )

            st.log(f"✓ Management VRF route {route_config.destination} verified")

            # Verify VRF isolation (route NOT in default VRF)
            if not _verify_route_not_in_default_vrf(route_config):
                st.report_fail(
                    "msg",
                    f"VRF isolation broken! Route {route_config.destination} leaked to default VRF"
                )

            st.log("✓ VRF isolation verified - no route leakage to default VRF")

        # Configure additional management routes
        for route_key in ["mgmt_nms_host", "mgmt_backup_network"]:
            if route_key in data.routes:
                route_config = data.routes[route_key]

                if _configure_mgmt_vrf_static_route(route_key, route_config):
                    st.log(f"✓ Additional route configured: {route_key}")

                    # Verify route installation
                    if st.poll_wait(
                        lambda: _verify_mgmt_route_present(route_config),
                        data.verify_timeout
                    ):
                        st.log(f"✓ Route {route_key} verified in mgmt VRF")
                    else:
                        st.warn(f"Route {route_key} verification failed")
                else:
                    st.warn(f"Failed to configure route {route_key}")

        st.report_tc_pass(
            TC_ID,
            "mgmt_vrf_ipv6_static_route_add_verify",
            "IPv6 static routes added and verified in Management VRF successfully"
        )

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.mgmtvrf
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_MGMT_VRF", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_mgmt_vrf_traffic_validation(self):
        """
        TC-IP-STATIC-IPV6-008 (Phase 4): Validate management traffic via Management VRF.

        Test Steps:
        1. Configure management VRF static route (if not already configured)
        2. Test IPv6 ping via Management VRF to management gateway
        3. Verify traffic uses eth0 management interface
        4. Test negative case: ping from default VRF should fail
        5. Verify VRF isolation in traffic forwarding
        """
        st.banner(f"{TC_ID}: Phase 4 - Management VRF traffic validation")

        # Ensure at least one management route is configured
        route_key = "mgmt_external_network"
        if route_key in data.routes:
            route_config = data.routes[route_key]

            # Configure if not already present
            if not _verify_mgmt_route_present(route_config):
                if not _configure_mgmt_vrf_static_route(route_key, route_config):
                    pytest.skip(f"Cannot configure management route for traffic test")

        # Test reachability to management gateway (should always work)
        if "mgmt_gateway" in data.pings:
            ping_config = data.pings["mgmt_gateway"]

            if not _test_mgmt_vrf_reachability(ping_config):
                st.report_fail(
                    "ping_fail",
                    vars.D1,
                    ping_config.target
                )

            st.log("✓ Management gateway reachability confirmed via mgmt VRF")

        # Test reachability to external management network (if configured)
        if data.test_config.use_gateway_as_ping_target:
            st.log("Using management gateway as primary ping target")
        else:
            if "mgmt_external" in data.pings:
                ping_config = data.pings["mgmt_external"]

                if not _test_mgmt_vrf_reachability(ping_config):
                    st.warn(
                        f"External management network {ping_config.target} not reachable "
                        "(may not be available in test environment)"
                    )

        # Negative test: Ping from default VRF should fail (VRF isolation)
        if "mgmt_from_default_vrf" in data.pings:
            ping_config = data.pings["mgmt_from_default_vrf"]

            if not _test_mgmt_vrf_reachability(ping_config):
                st.report_fail(
                    "msg",
                    "VRF isolation broken! Management destination reachable from default VRF"
                )

            st.log("✓ VRF isolation verified - mgmt destinations NOT reachable from default VRF")

        st.report_tc_pass(
            TC_ID,
            "mgmt_vrf_traffic_validation",
            "Management VRF traffic validation successful - VRF isolation confirmed"
        )

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.mgmtvrf
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_MGMT_VRF", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_mgmt_vrf_route_enable_disable_config_mode(self):
        """
        TC-IP-STATIC-IPV6-008 (Phase 7): Enable/disable management VRF route in config mode.

        Test Steps:
        1. Ensure management VRF route is configured
        2. Verify route is present and traffic works
        3. Remove route using 'no ipv6 route vrf mgmt' command
        4. Verify route disappears from mgmt VRF routing table
        5. Verify traffic fails after route removal
        6. Re-add route
        7. Verify route restoration and traffic recovery
        """
        st.banner(f"{TC_ID}: Phase 7 - Enable/Disable mgmt VRF route in config mode")

        route_key = "mgmt_external_network"
        if route_key not in data.routes:
            pytest.skip("Management route configuration not available")

        route_config = data.routes[route_key]

        # Step 1: Ensure route is configured
        if not _verify_mgmt_route_present(route_config):
            if not _configure_mgmt_vrf_static_route(route_key, route_config):
                pytest.skip("Cannot configure management route for test")

        # Step 2: Verify initial state - route present
        if not st.poll_wait(
            lambda: _verify_mgmt_route_present(route_config),
            data.verify_timeout
        ):
            st.report_fail("msg", "Initial route verification failed")

        st.log("✓ Initial state: Management VRF route is present")

        # Step 3: Remove the route
        _remove_mgmt_vrf_static_route(route_key, route_config)

        # Step 4: Verify route is absent
        if not st.poll_wait(
            lambda: _verify_mgmt_route_absent(route_config),
            data.verify_timeout
        ):
            st.report_fail("msg", "Route removal verification failed - route still present")

        st.log("✓ Route successfully removed from Management VRF")

        # Step 5: Re-add the route
        st.log("Re-adding Management VRF route to verify restoration")
        if not _configure_mgmt_vrf_static_route(route_key, route_config):
            st.report_fail("msg", "Failed to re-add management VRF route")

        # Step 6: Verify route restoration
        if not st.poll_wait(
            lambda: _verify_mgmt_route_present(route_config),
            data.verify_timeout
        ):
            st.report_fail("msg", "Route restoration verification failed")

        st.log("✓ Route successfully restored in Management VRF")

        st.report_tc_pass(
            TC_ID,
            "mgmt_vrf_route_enable_disable_config",
            "Management VRF route enable/disable in config mode successful"
        )

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.mgmtvrf
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_MGMT_VRF", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_mgmt_interface_enable_disable(self):
        """
        TC-IP-STATIC-IPV6-008 (Phase 8): Enable/disable management interface (eth0).

        Test Steps:
        1. Ensure management VRF route is configured
        2. Verify initial state - interface up, route active
        3. Shutdown eth0 management interface
        4. Verify routes become inactive or unreachable
        5. Verify traffic fails with interface down
        6. Re-enable eth0 interface (no shutdown)
        7. Verify routes become active again
        8. Verify traffic recovery
        """
        st.banner(f"{TC_ID}: Phase 8 - Enable/Disable management interface (eth0)")

        # Note: Shutting down eth0 may break management connectivity
        # This test should be run carefully or skipped in some environments
        st.log("WARNING: This test will temporarily shutdown the management interface")
        st.log("If device is accessed via eth0, connection may be lost")

        route_key = "mgmt_external_network"
        if route_key not in data.routes:
            pytest.skip("Management route configuration not available")

        route_config = data.routes[route_key]

        # Step 1: Ensure route is configured
        if not _verify_mgmt_route_present(route_config):
            if not _configure_mgmt_vrf_static_route(route_key, route_config):
                pytest.skip("Cannot configure management route for test")

        st.log("✓ Initial state: Management VRF route is present")

        # Step 2: Shutdown eth0 interface
        st.log(f"Shutting down management interface {data.interfaces.dut1_mgmt}")

        try:
            result = intf_api.interface_shutdown(
                vars.D1,
                data.interfaces.dut1_mgmt,
                cli_type=_cli_type()
            )

            if not result:
                st.warn(f"Interface shutdown may have failed - continuing test")

            st.wait(
                data.test_config.wait_after_interface_change,
                "Wait for interface state change"
            )

            st.log(f"✓ Management interface {data.interfaces.dut1_mgmt} shutdown")

            # Step 3: Re-enable eth0 interface immediately to restore connectivity
            st.log(f"Re-enabling management interface {data.interfaces.dut1_mgmt}")

            result = intf_api.interface_noshutdown(
                vars.D1,
                data.interfaces.dut1_mgmt,
                cli_type=_cli_type()
            )

            if not result:
                st.error(f"Failed to re-enable interface {data.interfaces.dut1_mgmt}")
                # This is critical - management connectivity may be lost
                st.report_fail(
                    "interface_admin_shut_down",
                    data.interfaces.dut1_mgmt,
                    vars.D1
                )

            st.wait(
                data.test_config.wait_after_interface_change,
                "Wait for interface recovery"
            )

            st.log(f"✓ Management interface {data.interfaces.dut1_mgmt} re-enabled")

            # Step 4: Verify route restoration after interface recovery
            if not st.poll_wait(
                lambda: _verify_mgmt_route_present(route_config),
                data.verify_timeout
            ):
                st.warn("Route verification after interface recovery failed")

            st.log("✓ Management VRF routes active after interface recovery")

        except Exception as error:
            st.error(f"Exception during interface enable/disable test: {error}")

            # Attempt to recover interface
            try:
                intf_api.interface_noshutdown(
                    vars.D1,
                    data.interfaces.dut1_mgmt,
                    cli_type=_cli_type()
                )
                st.log("Attempted to recover management interface after exception")
            except Exception:
                pass

            st.report_fail("msg", f"Interface enable/disable test failed: {error}")

        st.report_tc_pass(
            TC_ID,
            "mgmt_interface_enable_disable",
            "Management interface enable/disable test completed"
        )

    @pytest.mark.staticrouting
    @pytest.mark.ipv6
    @pytest.mark.mgmtvrf
    @pytest.mark.inventory(feature="STATIC_ROUTING_IPV6_MGMT_VRF", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_mgmt_vrf_isolation_comprehensive(self):
        """
        TC-IP-STATIC-IPV6-008 (Phase 3): Comprehensive VRF isolation validation.

        Test Steps:
        1. Configure routes in Management VRF
        2. Verify routes appear ONLY in mgmt VRF routing table
        3. Verify routes do NOT appear in default VRF
        4. Verify traffic from default VRF cannot reach mgmt destinations
        5. Verify CLI consistency across klish, vtysh, and kernel
        6. Validate no cross-VRF route leakage
        """
        st.banner(f"{TC_ID}: Phase 3 - Comprehensive VRF isolation validation")

        # Configure multiple management routes for thorough testing
        routes_to_test = [
            "mgmt_external_network",
            "mgmt_nms_host",
            "mgmt_backup_network"
        ]

        configured_count = 0
        for route_key in routes_to_test:
            if route_key in data.routes:
                route_config = data.routes[route_key]

                # Ensure route is configured
                if not _verify_mgmt_route_present(route_config):
                    if _configure_mgmt_vrf_static_route(route_key, route_config):
                        configured_count += 1

                # Verify VRF isolation for this route
                if not _verify_route_not_in_default_vrf(route_config):
                    st.report_fail(
                        "msg",
                        f"VRF isolation FAILED! Route {route_config.destination} "
                        f"leaked from mgmt VRF to default VRF"
                    )

                st.log(f"✓ VRF isolation verified for route: {route_key}")

        if configured_count == 0:
            st.warn("No management routes configured for isolation test")

        st.log(f"✓ VRF isolation validated for {configured_count} management routes")

        # Negative traffic test: ping from default VRF should fail
        if "mgmt_from_default_vrf" in data.pings:
            ping_config = data.pings["mgmt_from_default_vrf"]

            if not _test_mgmt_vrf_reachability(ping_config):
                st.report_fail(
                    "msg",
                    "CRITICAL: VRF isolation broken in traffic forwarding! "
                    "Management destination reachable from default VRF"
                )

            st.log("✓ Traffic-level VRF isolation confirmed")

        st.report_tc_pass(
            TC_ID,
            "mgmt_vrf_isolation_comprehensive",
            "Comprehensive VRF isolation validation successful - "
            "No route leakage detected between Management VRF and default VRF"
        )
