"""Test IPv4 connectivity between virtual SONiC devices using CLI variants."""

import re

import pytest

from spytest import st, SpyTestDict

import apis.routing.ip as ip_api
from utilities.utils import get_interface_number_from_name


def _canonical_interface_name(dut, interface):
    """Return the SONiC native interface name for klish commands."""

    if not interface:
        return interface

    if not isinstance(interface, str):
        return interface

    resolved = interface
    if not interface.lower().startswith("ethernet"):
        other_names = st.get_other_names(dut, [interface])
        if other_names and other_names[0] and other_names[0].lower().startswith("ethernet"):
            resolved = other_names[0]

    if resolved.lower().startswith("ethernet"):
        return resolved.replace(" ", "")

    return resolved


def _klish_interface_identifier(interface):
    """Return an interface identifier formatted for klish commands."""

    if not interface:
        return interface

    info = get_interface_number_from_name(interface)
    if isinstance(info, dict):
        iface_type = info.get("type")
        iface_number = info.get("number")
        if iface_type and iface_number is not None:
            return f"{iface_type} {iface_number}"

    if isinstance(info, str):
        match = re.search(r"([A-Za-z\-]+)\s*([0-9\/.]+)", info)
        if match:
            return f"{match.group(1)} {match.group(2)}"

    return interface


data = SpyTestDict()


@pytest.fixture(scope="module", autouse=True)
def module_setup():
    """Initialise topology and shared test data."""
    topology = st.ensure_min_topology("D1D2:1")
    data.dut1 = topology.D1
    data.dut2 = topology.D2
    data.interface_dut1 = _canonical_interface_name(data.dut1, topology.D1D2P1)
    data.interface_dut2 = _canonical_interface_name(data.dut2, topology.D2D1P1)
    data.klish_interface_dut1 = _klish_interface_identifier(data.interface_dut1)
    data.klish_interface_dut2 = _klish_interface_identifier(data.interface_dut2)
    data.ipv4_dut1 = "20.1.1.2"
    data.ipv4_dut2 = "20.1.1.3"
    data.subnet = "24"
    data.ip_prefix_dut1 = f"{data.ipv4_dut1}/{data.subnet}"
    data.ip_prefix_dut2 = f"{data.ipv4_dut2}/{data.subnet}"
    yield


@pytest.fixture(scope="function", autouse=True)
def cleanup_interface_ip():
    """Remove any configured IPv4 addresses after each test."""
    yield
    _configure_ipv4(enable=False)


def _configure_ipv4(enable=True):
    """Configure or remove IPv4 addresses on both DUTs via klish."""
    action = "add" if enable else "remove"
    for dut, interface, klish_interface, ip_addr, ip_prefix in [
        (
            data.dut1,
            data.interface_dut1,
            data.klish_interface_dut1,
            data.ipv4_dut1,
            data.ip_prefix_dut1,
        ),
        (
            data.dut2,
            data.interface_dut2,
            data.klish_interface_dut2,
            data.ipv4_dut2,
            data.ip_prefix_dut2,
        ),
    ]:
        if not enable and not ip_api.verify_interface_ip_address(
            dut,
            interface,
            ip_prefix,
            cli_type="klish",
        ):
            continue
        command_lines = [
            f"interface {klish_interface}",
            (
                f"ip address {ip_addr}/{data.subnet}"
                if enable
                else f"no ip address"
            ),
            "exit",
        ]
        command = "\n".join(command_lines)
        output = st.config(dut, command, type="klish", conf=True)
        output_text = "\n".join(map(str, output)) if isinstance(output, (list, tuple)) else str(output)
        if enable and "Error:" in output_text:
            st.report_fail(
                "msg",
                "Failed to {} IPv4 {} on {}".format(action, ip_addr, interface),
            )
        if not enable and "Error:" in output_text:
            st.error(
                "Failed to {} IPv4 {} on {}".format(action, ip_addr, interface)
            )


def _verify_ipv4_configuration():
    """Validate IPv4 configuration using klish show commands."""
    for dut, interface, ip_prefix in [
        (data.dut1, data.interface_dut1, data.ip_prefix_dut1),
        (data.dut2, data.interface_dut2, data.ip_prefix_dut2),
    ]:
        if not ip_api.verify_interface_ip_address(
            dut,
            interface,
            ip_prefix,
            cli_type="klish",
        ):
            st.report_fail(
                "msg",
                "Failed to verify IPv4 address {} on {}".format(
                    ip_prefix, interface
                ),
            )


@pytest.mark.inventory(feature="Regression")
def test_interface_ipv4_ping_between_vs():
    """Configure IPv4 using klish and validate connectivity using klish ping."""
    _configure_ipv4(enable=True)
    _verify_ipv4_configuration()

    if not ip_api.ping(
        data.dut1,
        data.ipv4_dut2,
        family="ipv4",
        timeout=4,
        cli_type="klish",
    ):
        st.report_fail(
            "ping_fail",
            data.ipv4_dut1,
            data.ipv4_dut2,
        )

    st.report_pass("test_case_passed")
