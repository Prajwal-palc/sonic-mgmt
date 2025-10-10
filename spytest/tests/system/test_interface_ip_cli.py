import ipaddress

import pytest

from spytest import st, SpyTestDict

from utilities.utils import get_interface_number_from_name

import apis.routing.ip as ip_api


data = SpyTestDict()


@pytest.fixture(scope="module", autouse=True)
def module_setup():
    vars = st.ensure_min_topology("D1")
    data.dut = vars.D1
    data.interface = "Ethernet4"
    data.ip_prefix = "100.2.2.2/24"
    intf_info = get_interface_number_from_name(data.interface)
    if isinstance(intf_info, dict) and {"type", "number"}.issubset(intf_info):
        data.interface_cmd = f"{intf_info['type']} {intf_info['number']}"
    else:
        data.interface_cmd = data.interface
    yield


@pytest.fixture(scope="function", autouse=True)
def interface_ip_cleanup():
    yield
    if data.get("dut") and ip_api.verify_interface_ip_address(
        data.dut, data.interface, data.ip_prefix, cli_type="klish"
    ):
        _configure_ip(enable=False)


def _get_ip_remove_commands(ip_prefix):
    """Return a list of klish commands to remove an IPv4 address."""

    commands = []
    base_command = f"no ip address {ip_prefix}"
    commands.append(base_command)

    try:
        interface = ipaddress.ip_interface(ip_prefix)
    except ValueError:
        return commands

    if interface.version != 4:
        return commands

    ip_addr = str(interface.ip)
    netmask = str(interface.network.netmask)

    for template in (
        f"no ip address {ip_addr} {netmask}",
        f"no ip address {ip_prefix} primary",
        f"no ip address {ip_addr} {netmask} primary",
    ):
        if template not in commands:
            commands.append(template)

    return commands


def _configure_ip(enable=True):
    command_list = [
        "sonic-cli",
        "configure terminal",
        f"interface {data.interface_cmd}",
    ]

    if enable:
        command_list.append(f"ip address {data.ip_prefix}")
    else:
        command_list.extend(_get_ip_remove_commands(data.ip_prefix))

    command_list.extend(["end", "exit"])

    st.apply_script(data.dut, command_list)


@pytest.mark.inventory(feature="Regression")
def test_configure_interface_ip_via_sonic_cli():
    _configure_ip(enable=True)

    if not ip_api.verify_interface_ip_address(
        data.dut, data.interface, data.ip_prefix, cli_type="klish"
    ):
        st.report_fail(
            "msg",
            "Failed to verify IPv4 address {} on {}".format(
                data.ip_prefix, data.interface
            ),
        )

    st.show(data.dut, "show ip interface", type="klish")

    _configure_ip(enable=False)

    if not ip_api.verify_interface_ip_address(
        data.dut,
        data.interface,
        data.ip_prefix,
        cli_type="klish",
        negative=True,
    ):
        st.report_fail(
            "msg",
            "IPv4 address {} still present on {} after removal".format(
                data.ip_prefix, data.interface
            ),
        )

    st.show(data.dut, "show ip interface", type="click")

    st.report_pass("test_case_passed")
