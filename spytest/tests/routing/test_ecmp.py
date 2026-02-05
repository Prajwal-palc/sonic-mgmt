"""ECMP automation derived from the 2.4.1–2.4.8 scenarios.

Each test aligns with the requirements captured in ``testcases.md`` while
adhering to the SPyTest authoring principles documented in the coding
guidelines.
"""

from __future__ import annotations

import ipaddress
from typing import Dict, List, Tuple

import pytest

from spytest import SpyTestDict, st

import apis.routing.ip as ipfeature
import apis.system.interface as interface_api

data = SpyTestDict()
vars = SpyTestDict()


@pytest.fixture(scope="module", autouse=True)
def ecmp_module_setup(request):
    """Prepare IP connectivity that the ECMP tests can reuse."""

    global data, vars
    vars = st.ensure_min_topology("D1D2:2")

    data.dut = vars.D1
    data.peer = vars.D2
    data.vrf = "default"
    data.ecmp_prefix = "198.51.100.0/24"
    data.links = (
        {
            "name": "blue",
            "local": vars.D1D2P1,
            "remote": vars.D2D1P1,
            "local_ip": "192.0.2.1",
            "remote_ip": "192.0.2.2",
            "mask": 24,
            "network": "192.0.2.0/24",
        },
        {
            "name": "green",
            "local": vars.D1D2P2,
            "remote": vars.D2D1P2,
            "local_ip": "192.0.3.1",
            "remote_ip": "192.0.3.2",
            "mask": 24,
            "network": "192.0.3.0/24",
        },
    )
    data.secondary_pool = {link["name"]: [] for link in data.links}

    for link in data.links:
        if not ipfeature.config_ip_addr_interface(
            data.dut,
            link["local"],
            link["local_ip"],
            link["mask"],
        ):
            st.report_fail("ip_config_failure", link["local"], link["local_ip"])
        if not ipfeature.config_ip_addr_interface(
            data.peer,
            link["remote"],
            link["remote_ip"],
            link["mask"],
        ):
            st.report_fail("ip_config_failure", link["remote"], link["remote_ip"])

    yield

    for link in data.links:
        ipfeature.config_ip_addr_interface(
            data.peer,
            link["remote"],
            link["remote_ip"],
            link["mask"],
            config="remove",
            skip_error=True,
        )
        ipfeature.config_ip_addr_interface(
            data.dut,
            link["local"],
            link["local_ip"],
            link["mask"],
            config="remove",
            skip_error=True,
        )
    for entries in data.secondary_pool.values():
        for link_name, ip_addr in entries:
            link = next(item for item in data.links if item["name"] == link_name)
            ipfeature.config_ip_addr_interface(
                data.peer,
                link["remote"],
                ip_addr,
                link["mask"],
                config="remove",
                skip_error=True,
            )


@pytest.fixture(scope="function", autouse=True)
def ecmp_function_setup():
    """Clear the ECMP prefix after each test run."""

    yield

    ipfeature.delete_static_route(
        data.dut,
        static_ip=data.ecmp_prefix,
        family="ipv4",
        cli_type="klish",
        skip_error_check=True,
    )


def _ensure_next_hop_capacity(target_count: int) -> List[str]:
    """Provision secondary IP addresses on peer interfaces to support ECMP."""

    provisioned: List[str] = []
    for link in data.links:
        network = ipaddress.ip_network(link["network"])
        for host in network.hosts():
            host_ip = str(host)
            if host_ip == link["local_ip"]:
                continue
            if host_ip == link["remote_ip"]:
                provisioned.append(host_ip)
            else:
                already = any(ip == host_ip for _, ip in data.secondary_pool[link["name"]])
                if not already:
                    if ipfeature.config_ip_addr_interface(
                        data.peer,
                        link["remote"],
                        host_ip,
                        link["mask"],
                        config="add",
                        is_secondary_ip="yes",
                    ):
                        data.secondary_pool[link["name"]].append((link["name"], host_ip))
                        provisioned.append(host_ip)
                else:
                    provisioned.append(host_ip)
            if len(provisioned) >= target_count:
                return provisioned
    return provisioned


def _program_static_ecmp(next_hops: List[str]) -> None:
    """Program a static ECMP route pointing to the supplied next hops."""

    for nh in next_hops:
        if not ipfeature.create_static_route(
            data.dut,
            next_hop=nh,
            static_ip=data.ecmp_prefix,
            family="ipv4",
            cli_type="klish",
        ):
            st.report_fail("operation_failed")


def _fetch_ecmp_entries() -> List[Dict[str, str]]:
    """Return the current ECMP entries for the configured prefix."""

    return ipfeature.fetch_ip_route(
        data.dut,
        family="ipv4",
        vrf_name=data.vrf,
        match={"ip_address": data.ecmp_prefix},
    ) or []


@pytest.mark.ecmp
@pytest.mark.community
def test_ft_ecmp_static_basic_functionality():
    """Test Case 2.4.1: Static ECMP basic functionality."""

    next_hops = _ensure_next_hop_capacity(2)[:2]
    _program_static_ecmp(next_hops)

    entries = _fetch_ecmp_entries()
    assert len(entries) == 2, "Expected two equal-cost next hops"

    try:
        interface_api.interface_shutdown(data.dut, [data.links[0]["local"]])
        interface_api.interface_shutdown(data.peer, [data.links[0]["remote"]])
        st.wait(5, "Allow route convergence")
        entries = _fetch_ecmp_entries()
        assert len(entries) == 1, "Route should prefer the surviving path"
    finally:
        interface_api.interface_noshutdown(data.dut, [data.links[0]["local"]])
        interface_api.interface_noshutdown(data.peer, [data.links[0]["remote"]])
        st.wait(5, "Restore interface state")

    entries = _fetch_ecmp_entries()
    assert len(entries) == 2, "All ECMP next hops should return"


@pytest.mark.ecmp
@pytest.mark.community
@pytest.mark.parametrize("next_hop_count", [4, 8, 16])
def test_ft_ecmp_static_scaling(next_hop_count):
    """Test Case 2.4.2: Static ECMP scale validation."""

    next_hops = _ensure_next_hop_capacity(next_hop_count)[:next_hop_count]
    if len(next_hops) < next_hop_count:
        st.report_unsupported("test_case_unsupported", "Insufficient next-hop capacity")
        pytest.skip("Insufficient next-hop capacity on the current testbed")

    _program_static_ecmp(next_hops)
    entries = _fetch_ecmp_entries()
    assert len(entries) == next_hop_count, "Not all ECMP next hops were installed"


@pytest.mark.ecmp
@pytest.mark.community
def test_ft_ecmp_static_negative():
    """Test Case 2.4.3: Static ECMP negative coverage."""

    invalid_nh = "203.0.113.254"
    ipfeature.create_static_route(
        data.dut,
        next_hop=invalid_nh,
        static_ip=data.ecmp_prefix,
        family="ipv4",
        cli_type="klish",
        skip_error_check=True,
    )
    entries = _fetch_ecmp_entries()
    assert all(entry["nexthop"] != invalid_nh for entry in entries), "Invalid next-hop accepted"

    next_hops = _ensure_next_hop_capacity(2)[:2]
    _program_static_ecmp(next_hops)
    entries = _fetch_ecmp_entries()
    assert len(entries) == 2

    ipfeature.delete_static_route(
        data.dut,
        next_hop=next_hops[0],
        static_ip=data.ecmp_prefix,
        family="ipv4",
        cli_type="klish",
    )
    entries = _fetch_ecmp_entries()
    assert len(entries) == 1, "Route should remain with the surviving next hop"

    ipfeature.create_static_route(
        data.dut,
        next_hop=next_hops[0],
        static_ip=data.ecmp_prefix,
        family="ipv4",
        cli_type="klish",
    )
    entries = _fetch_ecmp_entries()
    assert len(entries) == 2, "Route should recover after next-hop re-creation"


@pytest.mark.ecmp
@pytest.mark.community
@pytest.mark.skip(reason="OSPF ECMP automation is not yet implemented")
def test_ft_ecmp_ospf_basic_functionality():
    """Test Case 2.4.4: Dynamic ECMP using OSPF."""


@pytest.mark.ecmp
@pytest.mark.community
@pytest.mark.skip(reason="OSPF ECMP scale automation is not yet implemented")
def test_ft_ecmp_ospf_scaling():
    """Test Case 2.4.5: OSPF ECMP scale validation."""


@pytest.mark.ecmp
@pytest.mark.community
@pytest.mark.skip(reason="BGP ECMP automation requires multi-peer harness support")
def test_ft_ecmp_bgp_basic_functionality():
    """Test Case 2.4.6: BGP-learned ECMP basic functionality."""


@pytest.mark.ecmp
@pytest.mark.community
@pytest.mark.skip(reason="BGP ECMP scale automation is not yet implemented")
def test_ft_ecmp_bgp_scaling():
    """Test Case 2.4.7: BGP ECMP scale validation."""


@pytest.mark.ecmp
@pytest.mark.community
@pytest.mark.skip(reason="Dynamic routing negative ECMP automation is not yet implemented")
def test_ft_ecmp_dynamic_negative():
    """Test Case 2.4.8: Dynamic routing negative ECMP scenarios."""
