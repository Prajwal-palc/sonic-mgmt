"""
STATIC IPV4 ROUTING - VRF CONFIGURATION (KLISH)
Author: Athira
(c) 2025, copyrights@SuperMicro

How to run:
  ./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  routing/static/test_static_route_vrf_klish.py \
  --logs-path ./logs/test_static_route_vrf_klish_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

Description:
  Automates test plan TC-IP-STATIC-VRF-001 from testcases_static_route_3.md using the
  SpyTest framework with klish CLI validation. This test validates IPv4 static route
  configuration within a non-default VRF, ensuring proper route installation, VRF
  isolation, and traffic forwarding. The test creates a VRF instance, binds interfaces
  to the VRF, configures static routes within the VRF context, and validates that routes
  are properly isolated (no cross-VRF leakage).

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported on hardware and virtual platforms
  - Topology Diagram:
        # Topology - 2 nodes
        # +------------------------+                       +------------------------+
        # |         DUT1           |                       |         DUT2           |
        # | Eth4 10.0.24.1/31      |=======================| Eth4 10.0.24.0/31      |
        # |  (VRF: Vrf-RED)        |                       |                        |
        # | Loopback10 192.0.2.1/32|                       |                        |
        # +------------------------+                       +------------------------+
  - Feature flags / min SONiC version: klish CLI support for VRF and IPv4 static routing
  - Required test variables (YAML): spytest/vars/routing/static/vars_static_ipv4_vrf_klish.yaml
"""

from __future__ import annotations

from ipaddress import ip_interface
from pathlib import Path
from typing import Any, Dict, List, Mapping

import pytest
import yaml

from spytest import SpyTestDict, st

import apis.routing.ip as ip_api
import apis.routing.vrf as vrf_api
import apis.system.interface as intf_api

DEFAULT_CLI_TYPE = "klish"
VAR_FILE_ENV = "STATIC_IPV4_VRF_KLISH_VAR_FILE"
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "spytest"
    / "vars"
    / "routing"
    / "static"
    / "vars_static_ipv4_vrf_klish.yaml"
)

SUITE_BANNER = "STATIC ROUTE VRF KLISH"
TC_ID = "TC-IP-STATIC-VRF-001"

vars = SpyTestDict()
data = SpyTestDict()


def initialize_data() -> None:
    """Load YAML configuration and initialize test data structures."""
    try:
        payload = _load_yaml_payload()
    except FileNotFoundError as error:
        pytest.skip(str(error))
    except ValueError as error:
        pytest.fail(str(error))

    overrides = st.get_args("static_route_vrf_klish")
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
    data.verify_timeout = int(defaults.get("verify_timeout", 30))

    # VRF Configuration
    vrf_cfg = SpyTestDict(config.get("vrf", {}))
    data.vrf_name = str(vrf_cfg.get("name") or "Vrf-RED")

    # Interface Configuration
    interfaces_cfg = SpyTestDict(config.get("interfaces", {}))
    d1_cfg = SpyTestDict(interfaces_cfg.get("D1", {}))
    d2_cfg = SpyTestDict(interfaces_cfg.get("D2", {}))

    d1_link = SpyTestDict(d1_cfg.get("link", {}))
    d2_link = SpyTestDict(d2_cfg.get("link", {}))
    d1_loopback = SpyTestDict(d1_cfg.get("loopback", {}))

    d1_link_name = d1_link.get("name") or "Ethernet4"
    d1_link_prefix = d1_link.get("prefix") or "10.0.24.1/31"
    d2_link_name = d2_link.get("name") or "Ethernet4"
    d2_link_prefix = d2_link.get("prefix") or "10.0.24.0/31"
    d1_loopback_name = d1_loopback.get("name") or "Loopback10"
    d1_loopback_prefix = d1_loopback.get("prefix") or "192.0.2.1/32"

    try:
        d1_interface = ip_interface(d1_link_prefix)
    except ValueError as error:
        pytest.fail("Invalid IPv4 prefix '{}' for D1 link: {}".format(d1_link_prefix, error))
    try:
        d2_interface = ip_interface(d2_link_prefix)
    except ValueError as error:
        pytest.fail("Invalid IPv4 prefix '{}' for D2 link: {}".format(d2_link_prefix, error))
    try:
        d1_loopback_interface = ip_interface(d1_loopback_prefix)
    except ValueError as error:
        pytest.fail("Invalid IPv4 prefix '{}' for D1 loopback: {}".format(d1_loopback_prefix, error))

    # Static Route Configuration
    route_cfg = SpyTestDict(config.get("routes", {}).get("primary", {}))
    if not route_cfg:
        pytest.fail("Missing 'routes.primary' definition in YAML")

    destination_prefix = str(route_cfg.get("destination") or "198.51.100.0/24")
    next_hop = str(route_cfg.get("next_hop") or str(d2_interface.ip))

    data.interfaces = SpyTestDict(
        {
            "dut1_link": d1_link_name,
            "dut2_link": d2_link_name,
            "dut1_loopback": d1_loopback_name,
        }
    )

    data.ipv4 = SpyTestDict()
    data.ipv4.dut1_link_ip = str(d1_interface.ip)
    data.ipv4.dut2_link_ip = str(d2_interface.ip)
    data.ipv4.dut1_loopback_ip = str(d1_loopback_interface.ip)
    data.ipv4.link_prefix_len = int(d1_interface.network.prefixlen)
    data.ipv4.loopback_prefix_len = int(d1_loopback_interface.network.prefixlen)
    data.ipv4.destination_prefix = destination_prefix
    data.ipv4.next_hop = next_hop

    # Tracking configured resources
    data.vrf_configured = False
    data.loopback_configured = False
    data.ip_interfaces_configured = []
    data.vrf_bindings = []
    data.static_route_configured = False

    # Ping configuration
    pings = SpyTestDict(config.get("pings", {}))
    data.pings = SpyTestDict(
        {
            "target_ip": str(pings.get("target") or "198.51.100.1"),
            "count": int(pings.get("count") or 4),
            "family": str(pings.get("family") or "ipv4"),
        }
    )


def _deep_update(target: Dict[str, Any], overrides: Mapping[str, Any]) -> None:
    """Recursively update nested dictionary."""
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
    """Load test variables from YAML file."""
    override_path = st.getenv(VAR_FILE_ENV)
    candidate = Path(override_path) if override_path else DEFAULT_VAR_FILE
    if not candidate.is_file():
        raise FileNotFoundError("Static routing VRF variable file not found: {}".format(candidate))
    with candidate.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError("Static routing VRF variable file must contain a mapping: {}".format(candidate))
    return payload


def _cli_type() -> str:
    """Get configured CLI type."""
    value = getattr(data, "cli_type", DEFAULT_CLI_TYPE)
    if isinstance(value, str) and value:
        return value
    return DEFAULT_CLI_TYPE


def _configure_vrf() -> None:
    """Create VRF instance on D1."""
    st.log("Creating VRF {} on {}".format(data.vrf_name, vars.D1))
    result = vrf_api.config_vrf(
        vars.D1,
        vrf_name=data.vrf_name,
        config="yes",
        cli_type=_cli_type()
    )
    if not result:
        st.report_fail("msg", "Failed to create VRF {} on {}".format(data.vrf_name, vars.D1))
    data.vrf_configured = True
    st.wait(2)

    # Verify VRF creation
    if not vrf_api.verify_vrf(vars.D1, vrfname=data.vrf_name, cli_type=_cli_type()):
        st.report_fail("msg", "VRF {} not found after creation on {}".format(data.vrf_name, vars.D1))


def _configure_loopback() -> None:
    """Configure loopback interface on D1."""
    st.log("Configuring loopback interface {} with IP {} on {}".format(
        data.interfaces.dut1_loopback, data.ipv4.dut1_loopback_ip, vars.D1
    ))

    # Configure loopback IP address
    result = ip_api.configure_loopback(
        vars.D1,
        loopback_name=data.interfaces.dut1_loopback,
        config="yes",
        cli_type=_cli_type()
    )
    if not result:
        st.report_fail("msg", "Failed to create loopback interface {} on {}".format(
            data.interfaces.dut1_loopback, vars.D1
        ))

    result = ip_api.config_ip_addr_interface(
        vars.D1,
        interface_name=data.interfaces.dut1_loopback,
        ip_address=data.ipv4.dut1_loopback_ip,
        subnet=data.ipv4.loopback_prefix_len,
        family="ipv4",
        cli_type=_cli_type(),
    )
    if not result:
        st.report_fail("msg", "Failed to configure IP {} on loopback {} on {}".format(
            data.ipv4.dut1_loopback_ip, data.interfaces.dut1_loopback, vars.D1
        ))

    data.loopback_configured = True


def _bind_interface_to_vrf(dut: str, interface: str) -> None:
    """Bind interface to VRF."""
    st.log("Binding interface {} to VRF {} on {}".format(interface, data.vrf_name, dut))
    result = vrf_api.bind_vrf_interface(
        dut,
        vrf_name=data.vrf_name,
        intf_name=interface,
        config="yes",
        cli_type=_cli_type()
    )
    if not result:
        st.report_fail("msg", "Failed to bind interface {} to VRF {} on {}".format(
            interface, data.vrf_name, dut
        ))
    data.vrf_bindings.append((dut, interface))
    st.wait(2)


def _ensure_interfaces_up() -> None:
    """Ensure interfaces are administratively up."""
    st.log("Ensuring interfaces {} on {} and {} on {} are administratively up".format(
        data.interfaces.dut1_link, vars.D1, data.interfaces.dut2_link, vars.D2
    ))
    assert intf_api.interface_noshutdown(
        vars.D1, data.interfaces.dut1_link, cli_type=_cli_type()
    ), "Failed to enable interface {} on {}".format(data.interfaces.dut1_link, vars.D1)

    assert intf_api.interface_noshutdown(
        vars.D2, data.interfaces.dut2_link, cli_type=_cli_type()
    ), "Failed to enable interface {} on {}".format(data.interfaces.dut2_link, vars.D2)


def _configure_ipv4_addresses() -> None:
    """Configure IPv4 addresses on interfaces."""
    st.log("Configuring IPv4 addresses for {}".format(SUITE_BANNER))

    # Configure D1 link interface IP (before VRF binding)
    assert ip_api.config_ip_addr_interface(
        vars.D1,
        interface_name=data.interfaces.dut1_link,
        ip_address=data.ipv4.dut1_link_ip,
        subnet=data.ipv4.link_prefix_len,
        family="ipv4",
        cli_type=_cli_type(),
    ), "Failed to configure {} {}/{} on {}".format(
        data.interfaces.dut1_link, data.ipv4.dut1_link_ip, data.ipv4.link_prefix_len, vars.D1
    )
    data.ip_interfaces_configured.append((vars.D1, data.interfaces.dut1_link, data.ipv4.dut1_link_ip, data.ipv4.link_prefix_len))

    # Configure D2 link interface IP
    assert ip_api.config_ip_addr_interface(
        vars.D2,
        interface_name=data.interfaces.dut2_link,
        ip_address=data.ipv4.dut2_link_ip,
        subnet=data.ipv4.link_prefix_len,
        family="ipv4",
        cli_type=_cli_type(),
    ), "Failed to configure {} {}/{} on {}".format(
        data.interfaces.dut2_link, data.ipv4.dut2_link_ip, data.ipv4.link_prefix_len, vars.D2
    )
    data.ip_interfaces_configured.append((vars.D2, data.interfaces.dut2_link, data.ipv4.dut2_link_ip, data.ipv4.link_prefix_len))

    # Verify basic connectivity before VRF binding
    st.wait(3)
    assert ip_api.ping(
        vars.D1,
        data.ipv4.dut2_link_ip,
        family="ipv4",
        count=3,
        cli_type=_cli_type(),
    ), "Failed to verify reachability on the link between {} and {} before VRF binding".format(vars.D1, vars.D2)


def _configure_static_route_in_vrf() -> None:
    """Configure static route in VRF."""
    st.log("Configuring static route {} via {} in VRF {} on {}".format(
        data.ipv4.destination_prefix, data.ipv4.next_hop, data.vrf_name, vars.D1
    ))
    result = ip_api.create_static_route(
        vars.D1,
        next_hop=data.ipv4.next_hop,
        static_ip=data.ipv4.destination_prefix,
        family="ipv4",
        vrf=data.vrf_name,
        cli_type=_cli_type(),
    )
    if not result:
        st.report_fail("msg", "Failed to create static route {} via {} in VRF {}".format(
            data.ipv4.destination_prefix, data.ipv4.next_hop, data.vrf_name
        ))
    data.static_route_configured = True
    st.wait(2)


def _verify_route_in_vrf() -> bool:
    """Verify static route exists in VRF routing table."""
    st.log("Verifying static route {} in VRF {} routing table".format(
        data.ipv4.destination_prefix, data.vrf_name
    ))
    return ip_api.verify_ip_route(
        vars.D1,
        family="ipv4",
        vrf_name=data.vrf_name,
        ip_address=data.ipv4.destination_prefix,
        nexthop=data.ipv4.next_hop,
        type="S",
        cli_type=_cli_type(),
    )


def _verify_route_not_in_global() -> bool:
    """Verify static route does NOT exist in global routing table (VRF isolation)."""
    st.log("Verifying VRF isolation: route {} should NOT be in global routing table".format(
        data.ipv4.destination_prefix
    ))
    # This should return False, indicating the route is not in global table
    route_in_global = ip_api.verify_ip_route(
        vars.D1,
        family="ipv4",
        vrf_name=None,  # Global routing table
        ip_address=data.ipv4.destination_prefix,
        type="S",
        cli_type=_cli_type(),
    )
    return not route_in_global  # We want this to be False (not in global)


def _remove_static_route(force: bool = False) -> None:
    """Remove static route from VRF."""
    should_attempt = data.static_route_configured
    if not should_attempt and force:
        try:
            should_attempt = _verify_route_in_vrf()
        except Exception as error:  # pylint: disable=broad-except
            st.warn("Cleanup: unable to confirm static route presence -> {}".format(error))
            should_attempt = True
    if not should_attempt:
        return
    try:
        if not ip_api.delete_static_route(
            vars.D1,
            next_hop=data.ipv4.next_hop,
            static_ip=data.ipv4.destination_prefix,
            family="ipv4",
            vrf=data.vrf_name,
            cli_type=_cli_type(),
        ):
            st.warn("Cleanup: failed to delete static route {} in VRF {}".format(
                data.ipv4.destination_prefix, data.vrf_name
            ))
    finally:
        data.static_route_configured = False


def _unbind_vrf_interfaces() -> None:
    """Unbind all interfaces from VRF."""
    while data.vrf_bindings:
        dut, interface = data.vrf_bindings.pop()
        try:
            st.log("Unbinding interface {} from VRF {} on {}".format(interface, data.vrf_name, dut))
            vrf_api.bind_vrf_interface(
                dut,
                vrf_name=data.vrf_name,
                intf_name=interface,
                config="no",
                skip_error=True,
                cli_type=_cli_type()
            )
            st.wait(2)
        except Exception as error:  # pragma: no cover
            st.warn("Cleanup: exception unbinding {} from VRF on {} -> {}".format(
                interface, dut, error
            ))


def _remove_loopback() -> None:
    """Remove loopback interface configuration."""
    if not data.loopback_configured:
        return
    try:
        st.log("Removing loopback interface {} on {}".format(data.interfaces.dut1_loopback, vars.D1))
        ip_api.configure_loopback(
            vars.D1,
            loopback_name=data.interfaces.dut1_loopback,
            config="no",
            cli_type=_cli_type()
        )
    except Exception as error:  # pragma: no cover
        st.warn("Cleanup: exception removing loopback {} -> {}".format(
            data.interfaces.dut1_loopback, error
        ))
    finally:
        data.loopback_configured = False


def _remove_vrf() -> None:
    """Delete VRF instance."""
    if not data.vrf_configured:
        return
    try:
        st.log("Removing VRF {} on {}".format(data.vrf_name, vars.D1))
        vrf_api.config_vrf(
            vars.D1,
            vrf_name=data.vrf_name,
            config="no",
            skip_error=True,
            cli_type=_cli_type()
        )
    except Exception as error:  # pragma: no cover
        st.warn("Cleanup: exception removing VRF {} -> {}".format(data.vrf_name, error))
    finally:
        data.vrf_configured = False


def _remove_configured_addresses() -> None:
    """Remove configured IP addresses."""
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
        except Exception as error:  # pragma: no cover
            st.warn("Cleanup: exception removing {} {}/{} on {} -> {}".format(
                interface, address, prefix_len, dut, error
            ))


@pytest.fixture(scope="class", autouse=True)
def static_route_vrf_class_hook(request):
    """Setup and teardown for VRF static route tests."""
    initialize_data()

    # Check feature support
    if _cli_type() == "klish" and not st.is_feature_supported("klish", vars.D1):
        pytest.skip("klish CLI is not supported on {}".format(vars.D1))

    st.banner("{}: test setup".format(TC_ID))
    try:
        # Configuration sequence
        _ensure_interfaces_up()
        _configure_ipv4_addresses()
        _configure_vrf()
        _configure_loopback()
        _bind_interface_to_vrf(vars.D1, data.interfaces.dut1_link)
        _bind_interface_to_vrf(vars.D1, data.interfaces.dut1_loopback)
        _configure_static_route_in_vrf()
        yield
    finally:
        # Cleanup sequence (reverse order)
        st.banner("{}: cleanup".format(TC_ID))
        _remove_static_route(force=True)
        _unbind_vrf_interfaces()
        _remove_loopback()
        _remove_vrf()
        _remove_configured_addresses()


class TestStaticRouteVrfKlish:
    """Test class for IPv4 static route VRF configuration."""

    @pytest.mark.staticrouting
    @pytest.mark.vrf
    @pytest.mark.inventory(feature="STATIC_ROUTING_VRF", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID])
    @pytest.mark.topology("D1D2")
    def test_static_route_vrf_isolation_klish(self):
        """TC-IP-STATIC-VRF-001: Verify static route in VRF with isolation."""
        st.banner("{}: verify static route in VRF with proper isolation".format(TC_ID))

        # Verify VRF exists
        assert vrf_api.verify_vrf(
            vars.D1, vrfname=data.vrf_name, cli_type=_cli_type()
        ), "VRF {} not found on {}".format(data.vrf_name, vars.D1)

        # Verify loopback is bound to VRF
        assert vrf_api.verify_vrf_verbose(
            vars.D1,
            vrfname=data.vrf_name,
            interface=data.interfaces.dut1_loopback,
            cli_type=_cli_type()
        ), "Loopback {} not bound to VRF {} on {}".format(
            data.interfaces.dut1_loopback, data.vrf_name, vars.D1
        )

        # Verify link interface is bound to VRF
        assert vrf_api.verify_vrf_verbose(
            vars.D1,
            vrfname=data.vrf_name,
            interface=data.interfaces.dut1_link,
            cli_type=_cli_type()
        ), "Interface {} not bound to VRF {} on {}".format(
            data.interfaces.dut1_link, data.vrf_name, vars.D1
        )

        # Verify static route exists in VRF routing table
        assert _verify_route_in_vrf(), "Static route {} via {} not present in VRF {} on {}".format(
            data.ipv4.destination_prefix, data.ipv4.next_hop, data.vrf_name, vars.D1
        )

        # Verify VRF isolation: route should NOT be in global routing table
        assert _verify_route_not_in_global(), "Static route {} found in global routing table - VRF isolation FAILED".format(
            data.ipv4.destination_prefix
        )

        st.log("VRF isolation verified: route {} is only in VRF {}, not in global table".format(
            data.ipv4.destination_prefix, data.vrf_name
        ))

        st.report_pass("test_case_passed")

    @pytest.mark.staticrouting
    @pytest.mark.vrf
    @pytest.mark.inventory(feature="STATIC_ROUTING_VRF", release="Arlo+")
    @pytest.mark.inventory(testcases=[TC_ID + "-REMOVAL"])
    @pytest.mark.topology("D1D2")
    def test_static_route_vrf_removal_klish(self):
        """Verify static route removal from VRF."""
        st.banner("{}: verify static route removal from VRF".format(TC_ID))

        # Verify route exists first
        assert _verify_route_in_vrf(), "Static route {} not present in VRF {} before removal test".format(
            data.ipv4.destination_prefix, data.vrf_name
        )

        # Remove the route
        _remove_static_route()

        # Verify route is removed
        st.wait(3)
        route_exists = _verify_route_in_vrf()
        assert not route_exists, "Static route {} still present in VRF {} after removal".format(
            data.ipv4.destination_prefix, data.vrf_name
        )

        # Re-configure the route for cleanup
        _configure_static_route_in_vrf()

        st.report_pass("test_case_passed")
