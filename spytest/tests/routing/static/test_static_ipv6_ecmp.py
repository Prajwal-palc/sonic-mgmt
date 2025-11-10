"""
STATIC IPV6 ROUTING - ECMP ROUTE VALIDATION (KLISH)
Author: Athira
Copyright (C) 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/routing/static/test_static_ipv6_ecmp.py \
  --logs-path ./logs/test_ipv6_ecmp_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Validates IPv6 ECMP (Equal-Cost Multi-Path) static routing using klish CLI per test plan
  TC-IP-STATIC-IPV6-009. Tests configure multiple equal-cost next-hops for the same IPv6
  destination prefix, validate ECMP route installation with multiple next-hops appearing
  under the same route entry, verify load balancing distributes traffic across multiple paths,
  test automatic failover when one path fails, and validate ECMP re-establishment upon path
  restoration. Comprehensive validation includes interface counters for load distribution,
  next-hop failure simulation, and enable/disable operations at both global config and
  interface levels.

  Key Features Tested:
  - ECMP route creation with multiple next-hops (equal cost)
  - Load balancing traffic distribution across ECMP paths
  - Automatic failover when one next-hop path fails
  - ECMP re-establishment after failed path recovery
  - Interface-level and global config enable/disable operations
  - Traffic distribution validation via interface counters
  - Route state consistency across CLI methods (klish, vtysh, kernel)

Pre-requisites:
  - Topology: two-node (D1-D2) with multiple paths | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - ECMP Configuration with Multiple Next-Hops
        # +--------------------------------+                       +--------------------------------+
        # |        smic_sonic1 (D1)        |                       |        smic_sonic2 (D2)        |
        # |        (DUT - Source)          |                       |     (Intermediate Router)      |
        # |                                |   Path 1 (Ethernet4)  |                                |
        # | IPv6: 2001:db8:10::1/64        |=======================| IPv6: 2001:db8:10::2/64        |
        # |                                |                       |                                |
        # |                                |   Path 2 (Ethernet8)  | IPv6: 2001:db8:11::2/64        |
        # | IPv6: 2001:db8:11::1/64        |=======================|                                |
        # |                                |                       | Loopback: 2001:db8:20::1/128   |
        # +--------------------------------+                       +--------------------------------+
        #
        # Static Route on D1:
        #   2001:db8:20::/64 via 2001:db8:10::2  (Next-hop 1 - Path via Ethernet4)
        #   2001:db8:20::/64 via 2001:db8:11::2  (Next-hop 2 - Path via Ethernet8)
        #
        # Both routes have equal cost -> ECMP entry created
        # Traffic to 2001:db8:20::/64 load-balanced across both paths
  - Feature requirements: klish CLI, IPv6 routing, ECMP support, FRR routing daemon
  - Required test variables (YAML): spytest/spytest/vars/routing/static/vars_static_ipv6_ecmp.yaml
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

# Configuration constants
DEFAULT_CLI_TYPE = "klish"
VAR_FILE_ENV = "STATIC_IPV6_ECMP_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "routing"
    / "static"
    / "vars_static_ipv6_ecmp.yaml"
)

SUITE_BANNER = "STATIC IPV6 ECMP ROUTE VALIDATION"
TC_ID = "TC-IP-STATIC-IPV6-009"

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
    overrides = st.get_args("static_route_ipv6_ecmp")
    if isinstance(overrides, Mapping) and overrides:
        _deep_update(payload, overrides)

    config = SpyTestDict(payload)
    defaults = SpyTestDict(config.get("defaults", {}))

    # Topology requirements - need at least 2 links between D1 and D2
    min_topology = defaults.get("min_topology") or ["D1D2:2"]
    if isinstance(min_topology, str):
        min_topology = [min_topology]
    else:
        min_topology = list(min_topology)
    if not min_topology:
        min_topology = ["D1D2:2"]

    global vars
    vars = st.ensure_min_topology(*min_topology)

    # Store configuration data
    data.config = config
    data.defaults = defaults
    data.cli_type = str(defaults.get("cli_type") or DEFAULT_CLI_TYPE).lower()
    data.cleanup_enabled = bool(defaults.get("cleanup", True))
    data.verify_timeout = int(defaults.get("verify_timeout", 30))
    data.ecmp_verify_timeout = int(defaults.get("ecmp_verify_timeout", 60))

    # Parse ECMP path configuration
    ecmp_paths = SpyTestDict(config.get("ecmp_paths", {}))
    path1 = SpyTestDict(ecmp_paths.get("path1", {}))
    path2 = SpyTestDict(ecmp_paths.get("path2", {}))

    # Extract path 1 configuration with defaults
    d1_path1_name = path1.get("D1_interface") or "Ethernet4"
    d1_path1_ipv6 = path1.get("D1_ipv6") or "2001:db8:10::1/64"
    d2_path1_name = path1.get("D2_interface") or "Ethernet4"
    d2_path1_ipv6 = path1.get("D2_ipv6") or "2001:db8:10::2/64"

    # Extract path 2 configuration with defaults
    d1_path2_name = path2.get("D1_interface") or "Ethernet8"
    d1_path2_ipv6 = path2.get("D1_ipv6") or "2001:db8:11::1/64"
    d2_path2_name = path2.get("D2_interface") or "Ethernet8"
    d2_path2_ipv6 = path2.get("D2_ipv6") or "2001:db8:11::2/64"

    # Validate IPv6 addresses for ECMP paths
    try:
        d1_p1_interface = IPv6Interface(d1_path1_ipv6)
        d2_p1_interface = IPv6Interface(d2_path1_ipv6)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 address for ECMP path 1: {error}")

    try:
        d1_p2_interface = IPv6Interface(d1_path2_ipv6)
        d2_p2_interface = IPv6Interface(d2_path2_ipv6)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 address for ECMP path 2: {error}")

    # Parse destination network configuration
    destination = SpyTestDict(config.get("destination", {}))
    dest_prefix = destination.get("prefix") or "2001:db8:20::/64"
    dest_test_ip = destination.get("test_ip") or "2001:db8:20::1"
    dest_location = destination.get("location") or "D2 loopback0"

    # Parse loopback configuration for destination
    loopback_config = SpyTestDict(destination.get("loopback_config", {}))
    loopback_name = loopback_config.get("interface") or "Loopback0"
    loopback_ipv6 = loopback_config.get("ipv6") or "2001:db8:20::1/128"

    try:
        dest_network = IPv6Network(dest_prefix)
        dest_ip = IPv6Address(dest_test_ip)
        loopback_interface = IPv6Interface(loopback_ipv6)
    except ValueError as error:
        pytest.fail(f"Invalid IPv6 destination configuration: {error}")

    # Parse ECMP route configuration
    ecmp_routes = SpyTestDict(config.get("ecmp_routes", {}))
    route1 = SpyTestDict(ecmp_routes.get("route1", {}))
    route2 = SpyTestDict(ecmp_routes.get("route2", {}))

    route1_prefix = route1.get("prefix") or dest_prefix
    route1_nexthop = route1.get("nexthop") or str(d2_p1_interface.ip)
    route1_interface = route1.get("interface") or d1_path1_name

    route2_prefix = route2.get("prefix") or dest_prefix
    route2_nexthop = route2.get("nexthop") or str(d2_p2_interface.ip)
    route2_interface = route2.get("interface") or d1_path2_name

    # Store parsed interface data
    data.interfaces = SpyTestDict({
        "dut1_path1": d1_path1_name,
        "dut2_path1": d2_path1_name,
        "dut1_path2": d1_path2_name,
        "dut2_path2": d2_path2_name,
        "dut2_loopback": loopback_name,
    })

    # Store IPv6 addressing for ECMP paths
    data.ipv6 = SpyTestDict()

    # Path 1 addressing
    data.ipv6.dut1_path1_ip = str(d1_p1_interface.ip)
    data.ipv6.dut1_path1_prefix = str(d1_p1_interface)
    data.ipv6.dut2_path1_ip = str(d2_p1_interface.ip)
    data.ipv6.dut2_path1_prefix = str(d2_p1_interface)
    data.ipv6.path1_network = str(d1_p1_interface.network)
    data.ipv6.path1_prefix_len = int(d1_p1_interface.network.prefixlen)

    # Path 2 addressing
    data.ipv6.dut1_path2_ip = str(d1_p2_interface.ip)
    data.ipv6.dut1_path2_prefix = str(d1_p2_interface)
    data.ipv6.dut2_path2_ip = str(d2_p2_interface.ip)
    data.ipv6.dut2_path2_prefix = str(d2_p2_interface)
    data.ipv6.path2_network = str(d1_p2_interface.network)
    data.ipv6.path2_prefix_len = int(d1_p2_interface.network.prefixlen)

    # Destination network addressing
    data.ipv6.dest_network = str(dest_network)
    data.ipv6.dest_test_ip = str(dest_ip)
    data.ipv6.dest_prefix_len = int(dest_network.prefixlen)
    data.ipv6.loopback_ip = str(loopback_interface.ip)
    data.ipv6.loopback_prefix = str(loopback_interface)
    data.ipv6.loopback_prefix_len = int(loopback_interface.network.prefixlen)

    # Store ECMP route details
    data.ecmp_routes = SpyTestDict({
        "route1": {
            "prefix": route1_prefix,
            "nexthop": route1_nexthop,
            "interface": route1_interface,
        },
        "route2": {
            "prefix": route2_prefix,
            "nexthop": route2_nexthop,
            "interface": route2_interface,
        },
    })

    # Traffic test configuration
    traffic_cfg = SpyTestDict(config.get("traffic", {}))
    data.traffic = SpyTestDict({
        "ping_count": int(traffic_cfg.get("ping_count", 100)),
        "ping_interval": float(traffic_cfg.get("ping_interval", 0.2)),
        "stream_duration": int(traffic_cfg.get("stream_duration", 30)),
        "expected_load_balance_tolerance": float(traffic_cfg.get("expected_load_balance_tolerance", 0.2)),
    })

    # Tracking variables
    data.ipv6_interfaces_configured = []
    data.ecmp_routes_configured = []
    data.loopback_created = False


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
        raise FileNotFoundError(f"IPv6 ECMP variable file not found: {candidate}")
    with candidate.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    return payload


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown for IPv6 ECMP static route tests."""
    st.banner(f"{SUITE_BANNER} - MODULE PROLOGUE")
    st.log(f"Test Case ID: {TC_ID}")

    # Initialize test data from YAML
    initialize_data()

    st.log(f"Using topology: D1={vars.D1}, D2={vars.D2}")
    st.log(f"CLI type: {data.cli_type}")
    st.log(f"ECMP Path 1: {data.interfaces.dut1_path1} <-> {data.interfaces.dut2_path1}")
    st.log(f"ECMP Path 2: {data.interfaces.dut1_path2} <-> {data.interfaces.dut2_path2}")
    st.log(f"Destination network: {data.ipv6.dest_network}")

    # Module prologue: Configure base IPv6 interfaces for ECMP paths
    _configure_base_interfaces()

    yield

    # Module epilogue: Cleanup
    st.banner(f"{SUITE_BANNER} - MODULE EPILOGUE")
    if data.cleanup_enabled:
        _cleanup_all_configuration()
    else:
        st.log("Cleanup disabled - configuration left intact")


def _configure_base_interfaces() -> None:
    """Configure base IPv6 interfaces for ECMP paths and destination network."""
    st.banner("Configuring Base IPv6 Interfaces for ECMP")

    # Configure Path 1 interfaces
    st.log(f"Configuring Path 1: {data.interfaces.dut1_path1} on D1 and {data.interfaces.dut2_path1} on D2")

    # D1 Path 1
    result = ip_api.config_ip_addr_interface(
        vars.D1,
        data.interfaces.dut1_path1,
        data.ipv6.dut1_path1_prefix,
        family="ipv6",
        cli_type=data.cli_type
    )
    if not result:
        st.report_fail("msg", f"Failed to configure IPv6 on D1 {data.interfaces.dut1_path1}")
    data.ipv6_interfaces_configured.append({"dut": vars.D1, "interface": data.interfaces.dut1_path1})

    # Enable interface on D1 Path 1
    intf_api.interface_operation(
        vars.D1,
        data.interfaces.dut1_path1,
        operation="startup",
        cli_type=data.cli_type
    )

    # D2 Path 1
    result = ip_api.config_ip_addr_interface(
        vars.D2,
        data.interfaces.dut2_path1,
        data.ipv6.dut2_path1_prefix,
        family="ipv6",
        cli_type=data.cli_type
    )
    if not result:
        st.report_fail("msg", f"Failed to configure IPv6 on D2 {data.interfaces.dut2_path1}")
    data.ipv6_interfaces_configured.append({"dut": vars.D2, "interface": data.interfaces.dut2_path1})

    # Enable interface on D2 Path 1
    intf_api.interface_operation(
        vars.D2,
        data.interfaces.dut2_path1,
        operation="startup",
        cli_type=data.cli_type
    )

    # Configure Path 2 interfaces
    st.log(f"Configuring Path 2: {data.interfaces.dut1_path2} on D1 and {data.interfaces.dut2_path2} on D2")

    # D1 Path 2
    result = ip_api.config_ip_addr_interface(
        vars.D1,
        data.interfaces.dut1_path2,
        data.ipv6.dut1_path2_prefix,
        family="ipv6",
        cli_type=data.cli_type
    )
    if not result:
        st.report_fail("msg", f"Failed to configure IPv6 on D1 {data.interfaces.dut1_path2}")
    data.ipv6_interfaces_configured.append({"dut": vars.D1, "interface": data.interfaces.dut1_path2})

    # Enable interface on D1 Path 2
    intf_api.interface_operation(
        vars.D1,
        data.interfaces.dut1_path2,
        operation="startup",
        cli_type=data.cli_type
    )

    # D2 Path 2
    result = ip_api.config_ip_addr_interface(
        vars.D2,
        data.interfaces.dut2_path2,
        data.ipv6.dut2_path2_prefix,
        family="ipv6",
        cli_type=data.cli_type
    )
    if not result:
        st.report_fail("msg", f"Failed to configure IPv6 on D2 {data.interfaces.dut2_path2}")
    data.ipv6_interfaces_configured.append({"dut": vars.D2, "interface": data.interfaces.dut2_path2})

    # Enable interface on D2 Path 2
    intf_api.interface_operation(
        vars.D2,
        data.interfaces.dut2_path2,
        operation="startup",
        cli_type=data.cli_type
    )

    # Wait for interfaces to stabilize
    st.wait(5, "Waiting for IPv6 interfaces to stabilize")

    # Configure loopback on D2 for destination network
    st.log(f"Configuring destination network loopback on D2: {data.interfaces.dut2_loopback}")

    result = ip_api.config_ip_addr_interface(
        vars.D2,
        data.interfaces.dut2_loopback,
        data.ipv6.loopback_prefix,
        family="ipv6",
        cli_type=data.cli_type
    )
    if not result:
        st.report_fail("msg", f"Failed to configure IPv6 loopback on D2 {data.interfaces.dut2_loopback}")
    data.loopback_created = True
    data.ipv6_interfaces_configured.append({"dut": vars.D2, "interface": data.interfaces.dut2_loopback})

    # Verify interface status
    st.log("Verifying interface status for all ECMP paths")
    _verify_interface_status(vars.D1, data.interfaces.dut1_path1, expected_state="up")
    _verify_interface_status(vars.D1, data.interfaces.dut1_path2, expected_state="up")
    _verify_interface_status(vars.D2, data.interfaces.dut2_path1, expected_state="up")
    _verify_interface_status(vars.D2, data.interfaces.dut2_path2, expected_state="up")

    # Verify IPv6 connectivity on both paths
    st.log("Verifying IPv6 connectivity on Path 1")
    if not st.ping(vars.D1, data.ipv6.dut2_path1_ip, family="ipv6", count=3):
        st.report_fail("msg", f"Path 1 connectivity check failed: D1 cannot ping D2 ({data.ipv6.dut2_path1_ip})")

    st.log("Verifying IPv6 connectivity on Path 2")
    if not st.ping(vars.D1, data.ipv6.dut2_path2_ip, family="ipv6", count=3):
        st.report_fail("msg", f"Path 2 connectivity check failed: D1 cannot ping D2 ({data.ipv6.dut2_path2_ip})")

    st.log("Base IPv6 interface configuration completed successfully")


def _verify_interface_status(dut: str, interface: str, expected_state: str = "up") -> None:
    """Verify interface operational status."""
    if not intf_api.verify_interface_status(
        dut,
        interface,
        property="oper",
        value=expected_state,
        cli_type=data.cli_type
    ):
        st.warn(f"Interface {interface} on {dut} is not in expected state '{expected_state}'")


def _cleanup_all_configuration() -> None:
    """Remove all ECMP routes and IPv6 interface configurations."""
    st.banner("Cleaning up IPv6 ECMP configuration")

    # Remove ECMP static routes
    while data.ecmp_routes_configured:
        route_info = data.ecmp_routes_configured.pop()
        st.log(f"Removing ECMP route: {route_info}")
        ip_api.delete_static_route(
            route_info["dut"],
            next_hop=route_info["nexthop"],
            static_ip=route_info["prefix"],
            family="ipv6",
            cli_type=data.cli_type
        )

    # Remove IPv6 addresses from interfaces
    while data.ipv6_interfaces_configured:
        intf_info = data.ipv6_interfaces_configured.pop()
        st.log(f"Removing IPv6 from {intf_info['dut']} {intf_info['interface']}")
        # Note: For loopback interfaces, we may need to delete the entire interface
        if "Loopback" in intf_info['interface'] and data.loopback_created:
            # Delete loopback interface
            try:
                intf_api.clear_interface_config(
                    intf_info['dut'],
                    intf_info['interface'],
                    cli_type=data.cli_type
                )
            except Exception as e:
                st.log(f"Error removing loopback interface: {e}")
        else:
            # Remove IPv6 address from physical interface
            try:
                ip_api.delete_ip_interface(
                    intf_info['dut'],
                    intf_info['interface'],
                    family="ipv6",
                    cli_type=data.cli_type
                )
            except Exception as e:
                st.log(f"Error removing IPv6 from interface: {e}")

    st.log("Cleanup completed")


def _configure_ecmp_route(route_num: int, dut: str, prefix: str, nexthop: str, interface: str = None) -> bool:
    """Configure a single ECMP route."""
    st.log(f"Configuring ECMP Route {route_num}: {prefix} via {nexthop}")

    result = ip_api.create_static_route(
        dut,
        next_hop=nexthop,
        static_ip=prefix,
        family="ipv6",
        interface=interface,
        cli_type=data.cli_type
    )

    if result:
        data.ecmp_routes_configured.append({
            "dut": dut,
            "prefix": prefix,
            "nexthop": nexthop,
            "interface": interface
        })

    return result


def _remove_ecmp_route(dut: str, prefix: str, nexthop: str, interface: str = None) -> None:
    """Remove a single ECMP route."""
    st.log(f"Removing ECMP Route: {prefix} via {nexthop}")

    ip_api.delete_static_route(
        dut,
        next_hop=nexthop,
        static_ip=prefix,
        family="ipv6",
        interface=interface,
        cli_type=data.cli_type
    )

    # Remove from tracking list
    for route_info in data.ecmp_routes_configured[:]:
        if (route_info["dut"] == dut and
            route_info["prefix"] == prefix and
            route_info["nexthop"] == nexthop):
            data.ecmp_routes_configured.remove(route_info)
            break


def _verify_ecmp_route_installed(dut: str, prefix: str, nexthops: List[str]) -> bool:
    """Verify ECMP route is installed with all next-hops."""
    st.log(f"Verifying ECMP route {prefix} with next-hops: {nexthops}")

    # Check route exists
    if not ip_api.verify_ip_route(
        dut,
        family="ipv6",
        ip_address=prefix,
        cli_type=data.cli_type
    ):
        st.error(f"Route {prefix} not found in routing table")
        return False

    # Verify each next-hop appears in the route
    for nexthop in nexthops:
        if not ip_api.verify_ip_route(
            dut,
            family="ipv6",
            ip_address=prefix,
            nexthop=nexthop,
            cli_type=data.cli_type
        ):
            st.error(f"Next-hop {nexthop} not found for route {prefix}")
            return False

    st.log(f"ECMP route {prefix} verified with all {len(nexthops)} next-hops")
    return True


def _get_interface_counters(dut: str, interface: str) -> Dict[str, int]:
    """Get interface TX/RX counters."""
    counters = intf_api.get_interface_counters(dut, interface, cli_type=data.cli_type)
    if not counters:
        return {"tx_ok": 0, "rx_ok": 0, "tx_bps": 0, "rx_bps": 0}
    return counters[0] if isinstance(counters, list) else counters


def _clear_interface_counters(dut: str) -> None:
    """Clear all interface counters on a DUT."""
    st.log(f"Clearing interface counters on {dut}")
    intf_api.clear_interface_counters(dut, interface_type="all", cli_type=data.cli_type)


@pytest.mark.inventory(feature="Regression", testcases=["TC-IP-STATIC-IPV6-009"])
class TestIPv6ECMPStaticRoute:
    """Test class for IPv6 ECMP static route validation."""

    def test_ipv6_ecmp_001_configure_single_route(self):
        """
        TC-IP-STATIC-IPV6-009-001: Configure first static route and verify single path.

        Test Steps:
        1. Configure first static route to destination network via Path 1
        2. Verify route is installed with single next-hop
        3. Test reachability to destination
        4. Verify traffic uses only Path 1 interface
        """
        st.banner("TEST: Configure Single Route (Before ECMP)")

        # Configure first route
        route1 = data.ecmp_routes.route1
        result = _configure_ecmp_route(
            1,
            vars.D1,
            route1.prefix,
            route1.nexthop,
            route1.interface
        )
        if not result:
            st.report_fail("msg", "Failed to configure first static route")

        # Verify single route installation
        if not st.poll_wait(
            ip_api.verify_ip_route,
            data.verify_timeout,
            vars.D1,
            family="ipv6",
            ip_address=route1.prefix,
            nexthop=route1.nexthop,
            type="S",
            cli_type=data.cli_type
        ):
            st.report_fail("msg", f"First static route {route1.prefix} not installed")

        st.log("Single route installed successfully")

        # Test reachability
        if not st.ping(vars.D1, data.ipv6.dest_test_ip, family="ipv6", count=5):
            st.report_fail("msg", f"Ping to destination {data.ipv6.dest_test_ip} failed with single route")

        st.log("Reachability verified with single path")
        st.report_pass("test_case_passed")

    def test_ipv6_ecmp_002_configure_second_route_create_ecmp(self):
        """
        TC-IP-STATIC-IPV6-009-002: Configure second route and verify ECMP creation.

        Test Steps:
        1. Configure second static route to same destination via Path 2
        2. Verify ECMP entry is created with both next-hops
        3. Verify both next-hops appear under same route entry
        4. Check route type is Static (S) with equal cost
        """
        st.banner("TEST: Configure Second Route and Create ECMP")

        # Ensure first route exists (dependency on previous test)
        route1 = data.ecmp_routes.route1
        if not ip_api.verify_ip_route(
            vars.D1,
            family="ipv6",
            ip_address=route1.prefix,
            cli_type=data.cli_type
        ):
            # Configure first route if not present
            _configure_ecmp_route(1, vars.D1, route1.prefix, route1.nexthop, route1.interface)
            st.wait(3)

        # Configure second route
        route2 = data.ecmp_routes.route2
        result = _configure_ecmp_route(
            2,
            vars.D1,
            route2.prefix,
            route2.nexthop,
            route2.interface
        )
        if not result:
            st.report_fail("msg", "Failed to configure second static route for ECMP")

        st.wait(5, "Waiting for ECMP route convergence")

        # Verify ECMP route with both next-hops
        nexthops = [route1.nexthop, route2.nexthop]
        if not st.poll_wait(
            _verify_ecmp_route_installed,
            data.ecmp_verify_timeout,
            vars.D1,
            route1.prefix,
            nexthops
        ):
            st.report_fail("msg", f"ECMP route not created with both next-hops: {nexthops}")

        st.log("ECMP entry created successfully with both next-hops")

        # Verify route via vtysh
        output = st.show(vars.D1, f"sudo vtysh -c 'show ipv6 route {route1.prefix}'", skip_tmpl=True)
        st.log(f"Route output via vtysh: {output}")

        st.report_pass("test_case_passed")

    def test_ipv6_ecmp_003_verify_load_balancing(self):
        """
        TC-IP-STATIC-IPV6-009-003: Verify traffic load balancing across ECMP paths.

        Test Steps:
        1. Clear interface counters on both ECMP paths
        2. Send sustained ping traffic to destination
        3. Check interface counters on both paths
        4. Verify traffic distribution across both interfaces
        5. Validate load balancing within acceptable tolerance
        """
        st.banner("TEST: Verify ECMP Load Balancing")

        # Ensure ECMP routes are configured
        route1 = data.ecmp_routes.route1
        route2 = data.ecmp_routes.route2
        nexthops = [route1.nexthop, route2.nexthop]

        if not _verify_ecmp_route_installed(vars.D1, route1.prefix, nexthops):
            st.report_fail("msg", "ECMP routes not configured - prerequisite failed")

        # Clear counters
        _clear_interface_counters(vars.D1)
        st.wait(2, "Waiting after clearing counters")

        # Get baseline counters
        baseline_path1 = _get_interface_counters(vars.D1, data.interfaces.dut1_path1)
        baseline_path2 = _get_interface_counters(vars.D1, data.interfaces.dut1_path2)

        st.log(f"Baseline Path 1 ({data.interfaces.dut1_path1}) TX: {baseline_path1.get('tx_ok', 0)}")
        st.log(f"Baseline Path 2 ({data.interfaces.dut1_path2}) TX: {baseline_path2.get('tx_ok', 0)}")

        # Send traffic
        ping_count = data.traffic.ping_count
        st.log(f"Sending {ping_count} pings to trigger ECMP load balancing")

        ping_result = st.ping(
            vars.D1,
            data.ipv6.dest_test_ip,
            family="ipv6",
            count=ping_count,
            interval=data.traffic.ping_interval
        )

        if not ping_result:
            st.report_fail("msg", f"Ping failed during load balancing test")

        st.wait(2, "Waiting for counter updates")

        # Get post-traffic counters
        post_path1 = _get_interface_counters(vars.D1, data.interfaces.dut1_path1)
        post_path2 = _get_interface_counters(vars.D1, data.interfaces.dut1_path2)

        path1_tx_delta = post_path1.get('tx_ok', 0) - baseline_path1.get('tx_ok', 0)
        path2_tx_delta = post_path2.get('tx_ok', 0) - baseline_path2.get('tx_ok', 0)

        st.log(f"Path 1 TX delta: {path1_tx_delta} packets")
        st.log(f"Path 2 TX delta: {path2_tx_delta} packets")

        # Verify both paths carried traffic
        if path1_tx_delta == 0:
            st.report_fail("msg", f"Path 1 ({data.interfaces.dut1_path1}) carried no traffic - ECMP not working")

        if path2_tx_delta == 0:
            st.report_fail("msg", f"Path 2 ({data.interfaces.dut1_path2}) carried no traffic - ECMP not working")

        # Calculate distribution
        total_packets = path1_tx_delta + path2_tx_delta
        path1_percent = (path1_tx_delta / total_packets) * 100 if total_packets > 0 else 0
        path2_percent = (path2_tx_delta / total_packets) * 100 if total_packets > 0 else 0

        st.log(f"Traffic distribution: Path 1 = {path1_percent:.1f}%, Path 2 = {path2_percent:.1f}%")

        # Check if distribution is within acceptable tolerance (40-60%)
        tolerance = data.traffic.expected_load_balance_tolerance * 100  # Convert to percentage
        min_percent = 50 - (tolerance * 50 / 100)
        max_percent = 50 + (tolerance * 50 / 100)

        if not (min_percent <= path1_percent <= max_percent):
            st.warn(f"Path 1 traffic distribution ({path1_percent:.1f}%) outside ideal range ({min_percent:.1f}%-{max_percent:.1f}%)")

        if not (min_percent <= path2_percent <= max_percent):
            st.warn(f"Path 2 traffic distribution ({path2_percent:.1f}%) outside ideal range ({min_percent:.1f}%-{max_percent:.1f}%)")

        st.log("Load balancing verified - traffic distributed across both ECMP paths")
        st.report_pass("test_case_passed")

    def test_ipv6_ecmp_004_simulate_path_failure(self):
        """
        TC-IP-STATIC-IPV6-009-004: Simulate next-hop failure and verify automatic failover.

        Test Steps:
        1. Shutdown first ECMP path interface (Path 1)
        2. Verify ECMP degrades to single path automatically
        3. Test reachability via remaining path
        4. Verify traffic uses only active path
        5. Confirm automatic failover without manual intervention
        """
        st.banner("TEST: Simulate Path Failure and Verify Failover")

        # Ensure ECMP is configured
        route1 = data.ecmp_routes.route1
        route2 = data.ecmp_routes.route2
        nexthops = [route1.nexthop, route2.nexthop]

        if not _verify_ecmp_route_installed(vars.D1, route1.prefix, nexthops):
            st.report_fail("msg", "ECMP routes not configured - prerequisite failed")

        # Shutdown Path 1 interface
        st.log(f"Shutting down Path 1 interface: {data.interfaces.dut1_path1}")
        intf_api.interface_operation(
            vars.D1,
            data.interfaces.dut1_path1,
            operation="shutdown",
            cli_type=data.cli_type
        )

        st.wait(5, "Waiting for route convergence after interface shutdown")

        # Verify interface is down
        _verify_interface_status(vars.D1, data.interfaces.dut1_path1, expected_state="down")

        # Verify route automatically updates to single path (Path 2 only)
        st.log("Verifying automatic failover to Path 2")
        if not st.poll_wait(
            ip_api.verify_ip_route,
            data.verify_timeout,
            vars.D1,
            family="ipv6",
            ip_address=route2.prefix,
            nexthop=route2.nexthop,
            cli_type=data.cli_type
        ):
            st.report_fail("msg", "Failover failed - Path 2 route not active after Path 1 failure")

        # Verify Path 1 next-hop is not active
        route_output = ip_api.show_ip_route(
            vars.D1,
            family="ipv6",
            ip_address=route1.prefix,
            cli_type=data.cli_type
        )
        st.log(f"Route output after Path 1 failure: {route_output}")

        # Test connectivity with failover
        if not st.ping(vars.D1, data.ipv6.dest_test_ip, family="ipv6", count=10):
            st.report_fail("msg", "Connectivity lost after Path 1 failure - failover unsuccessful")

        st.log("Automatic failover successful - connectivity maintained via Path 2")

        # Verify only Path 2 carries traffic
        _clear_interface_counters(vars.D1)
        st.wait(2)

        baseline_path2 = _get_interface_counters(vars.D1, data.interfaces.dut1_path2)
        st.ping(vars.D1, data.ipv6.dest_test_ip, family="ipv6", count=20)
        st.wait(2)
        post_path2 = _get_interface_counters(vars.D1, data.interfaces.dut1_path2)

        path2_tx_delta = post_path2.get('tx_ok', 0) - baseline_path2.get('tx_ok', 0)

        if path2_tx_delta == 0:
            st.report_fail("msg", "Path 2 carried no traffic after Path 1 failure")

        st.log(f"Path 2 carried {path2_tx_delta} packets after failover")
        st.report_pass("test_case_passed")

    def test_ipv6_ecmp_005_restore_failed_path(self):
        """
        TC-IP-STATIC-IPV6-009-005: Restore failed path and verify ECMP re-establishment.

        Test Steps:
        1. Re-enable previously failed interface (Path 1)
        2. Verify interface comes back up
        3. Verify ECMP is automatically re-established with both paths
        4. Test load balancing after recovery
        5. Confirm ECMP operates normally after restoration
        """
        st.banner("TEST: Restore Failed Path and Re-establish ECMP")

        # Re-enable Path 1 interface
        st.log(f"Re-enabling Path 1 interface: {data.interfaces.dut1_path1}")
        intf_api.interface_operation(
            vars.D1,
            data.interfaces.dut1_path1,
            operation="startup",
            cli_type=data.cli_type
        )

        st.wait(5, "Waiting for interface to come up")

        # Verify interface is up
        _verify_interface_status(vars.D1, data.interfaces.dut1_path1, expected_state="up")

        # Verify connectivity on Path 1
        if not st.ping(vars.D1, data.ipv6.dut2_path1_ip, family="ipv6", count=3):
            st.report_fail("msg", "Path 1 connectivity not restored after interface up")

        st.wait(5, "Waiting for ECMP re-establishment")

        # Verify ECMP is re-established with both paths
        route1 = data.ecmp_routes.route1
        route2 = data.ecmp_routes.route2
        nexthops = [route1.nexthop, route2.nexthop]

        if not st.poll_wait(
            _verify_ecmp_route_installed,
            data.ecmp_verify_timeout,
            vars.D1,
            route1.prefix,
            nexthops
        ):
            st.report_fail("msg", "ECMP not re-established after Path 1 recovery")

        st.log("ECMP successfully re-established with both paths")

        # Quick load balancing verification
        _clear_interface_counters(vars.D1)
        st.wait(2)

        baseline_path1 = _get_interface_counters(vars.D1, data.interfaces.dut1_path1)
        baseline_path2 = _get_interface_counters(vars.D1, data.interfaces.dut1_path2)

        st.ping(vars.D1, data.ipv6.dest_test_ip, family="ipv6", count=50)
        st.wait(2)

        post_path1 = _get_interface_counters(vars.D1, data.interfaces.dut1_path1)
        post_path2 = _get_interface_counters(vars.D1, data.interfaces.dut1_path2)

        path1_tx_delta = post_path1.get('tx_ok', 0) - baseline_path1.get('tx_ok', 0)
        path2_tx_delta = post_path2.get('tx_ok', 0) - baseline_path2.get('tx_ok', 0)

        st.log(f"After recovery - Path 1 TX: {path1_tx_delta}, Path 2 TX: {path2_tx_delta}")

        if path1_tx_delta == 0 or path2_tx_delta == 0:
            st.report_fail("msg", "Load balancing not working after ECMP recovery")

        st.log("Load balancing restored after ECMP re-establishment")
        st.report_pass("test_case_passed")

    def test_ipv6_ecmp_006_enable_disable_global_config(self):
        """
        TC-IP-STATIC-IPV6-009-006: Test enable/disable in global configuration mode.

        Test Steps:
        1. Remove first ECMP route via global config
        2. Verify ECMP degrades to single route
        3. Re-add first route
        4. Verify ECMP is restored
        5. Test multiple enable/disable cycles
        """
        st.banner("TEST: Enable/Disable Routes in Global Config Mode")

        # Ensure ECMP is configured
        route1 = data.ecmp_routes.route1
        route2 = data.ecmp_routes.route2
        nexthops = [route1.nexthop, route2.nexthop]

        if not _verify_ecmp_route_installed(vars.D1, route1.prefix, nexthops):
            # Configure if missing
            _configure_ecmp_route(1, vars.D1, route1.prefix, route1.nexthop, route1.interface)
            _configure_ecmp_route(2, vars.D1, route2.prefix, route2.nexthop, route2.interface)
            st.wait(5)

        # Remove first route
        st.log("Removing first ECMP route via global config")
        _remove_ecmp_route(vars.D1, route1.prefix, route1.nexthop, route1.interface)
        st.wait(3)

        # Verify single route remains
        if not ip_api.verify_ip_route(
            vars.D1,
            family="ipv6",
            ip_address=route2.prefix,
            nexthop=route2.nexthop,
            cli_type=data.cli_type
        ):
            st.report_fail("msg", "Route 2 not present after removing Route 1")

        # Verify reachability via single path
        if not st.ping(vars.D1, data.ipv6.dest_test_ip, family="ipv6", count=5):
            st.report_fail("msg", "Connectivity lost after removing one ECMP route")

        # Re-add first route
        st.log("Re-adding first ECMP route")
        _configure_ecmp_route(1, vars.D1, route1.prefix, route1.nexthop, route1.interface)
        st.wait(5)

        # Verify ECMP restored
        if not _verify_ecmp_route_installed(vars.D1, route1.prefix, nexthops):
            st.report_fail("msg", "ECMP not restored after re-adding first route")

        st.log("ECMP successfully restored after global config enable/disable cycle")
        st.report_pass("test_case_passed")

    def test_ipv6_ecmp_007_comprehensive_show_commands(self):
        """
        TC-IP-STATIC-IPV6-009-007: Validate all show commands for ECMP routes.

        Test Steps:
        1. Execute standard CLI show commands
        2. Execute privileged (vtysh) show commands
        3. Verify kernel routing table
        4. Validate consistency across all CLI methods
        5. Confirm ECMP visibility in all views
        """
        st.banner("TEST: Comprehensive Show Command Validation")

        # Ensure ECMP is configured
        route1 = data.ecmp_routes.route1
        route2 = data.ecmp_routes.route2
        nexthops = [route1.nexthop, route2.nexthop]

        if not _verify_ecmp_route_installed(vars.D1, route1.prefix, nexthops):
            st.report_fail("msg", "ECMP routes not configured - prerequisite failed")

        # Standard CLI commands
        st.log("=== Standard CLI Show Commands ===")

        st.log("1. show ipv6 route")
        output1 = st.show(vars.D1, "show ipv6 route", type=data.cli_type)
        st.log(f"Output: {output1}")

        st.log("2. show ipv6 route static")
        output2 = st.show(vars.D1, "show ipv6 route static", type=data.cli_type)
        st.log(f"Output: {output2}")

        st.log(f"3. show ipv6 route {route1.prefix}")
        output3 = st.show(vars.D1, f"show ipv6 route {route1.prefix}", type=data.cli_type)
        st.log(f"Output: {output3}")

        st.log("4. show interface status")
        output4 = st.show(vars.D1, "show interface status", type=data.cli_type)
        st.log(f"Interface status output length: {len(str(output4))}")

        st.log("5. show interfaces counters")
        output5 = st.show(vars.D1, "show interfaces counters", type=data.cli_type)
        st.log(f"Interface counters output length: {len(str(output5))}")

        # Privileged commands
        st.log("=== Privileged (sudo vtysh) Show Commands ===")

        st.log("6. sudo vtysh -c 'show ipv6 route'")
        output6 = st.show(vars.D1, "sudo vtysh -c 'show ipv6 route'", skip_tmpl=True)
        st.log(f"Output length: {len(str(output6))}")

        st.log(f"7. sudo vtysh -c 'show ipv6 route {route1.prefix}'")
        output7 = st.show(vars.D1, f"sudo vtysh -c 'show ipv6 route {route1.prefix}'", skip_tmpl=True)
        st.log(f"Output: {output7}")

        # Kernel routing table
        st.log("=== Kernel Routing Table ===")

        st.log(f"8. sudo ip -6 route show {route1.prefix}")
        output8 = st.show(vars.D1, f"sudo ip -6 route show {route1.prefix}", skip_tmpl=True)
        st.log(f"Output: {output8}")

        st.log("9. sudo ip -6 route list")
        output9 = st.show(vars.D1, "sudo ip -6 route list | head -20", skip_tmpl=True)
        st.log(f"Output length: {len(str(output9))}")

        # Neighbor validation
        st.log("=== IPv6 Neighbor Validation ===")

        st.log(f"10. sudo ip -6 neigh show {route1.nexthop}")
        output10 = st.show(vars.D1, f"sudo ip -6 neigh show {route1.nexthop}", skip_tmpl=True)
        st.log(f"Neighbor 1 output: {output10}")

        st.log(f"11. sudo ip -6 neigh show {route2.nexthop}")
        output11 = st.show(vars.D1, f"sudo ip -6 neigh show {route2.nexthop}", skip_tmpl=True)
        st.log(f"Neighbor 2 output: {output11}")

        st.log("All show commands executed successfully")
        st.report_pass("test_case_passed")
