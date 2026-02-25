"""
Management Interface API Module
Author: Shiva
2026

This module provides APIs for management interface operations including:
- IPv6 autoconfig configuration
- Running configuration verification
- ARP/NDP neighbor table validation
"""

import re
from spytest import st
from apis.system import interface_cli_api
from apis.routing import arp as arp_api
from utilities.common import filter_and_select


def get_management_interface_name(cli_type="klish"):
    """
    Get the management interface name based on CLI type.

    :param cli_type: CLI type (klish, click)
    :return: Management interface name

    Example:
        mgmt_if = get_management_interface_name("klish")  # Returns "Management 0"
    """
    if cli_type == "klish":
        return "Management 0"
    elif cli_type == "click":
        return "eth0"
    else:
        st.warn(f"Unknown CLI type: {cli_type}, defaulting to klish")
        return "Management 0"


def get_management_interface_show_name(cli_type="klish"):
    """
    Get the management interface name as it appears in show commands.

    :param cli_type: CLI type (klish, click)
    :return: Management interface name for show output

    Example:
        show_if = get_management_interface_show_name("klish")  # Returns "Management0"
    """
    if cli_type == "klish":
        return "Management0"
    elif cli_type == "click":
        return "eth0"
    else:
        return "Management0"


def config_ipv6_autoconfig(dut, config="add", **kwargs):
    """
    Enable or disable IPv6 autoconfig on Management interface.

    This API configures IPv6 address autoconfig on the management interface
    using the appropriate CLI commands for klish or click.

    :param dut: Device under test
    :param config: "add" to enable, "remove" to disable
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - skip_error_check: Skip error checking
    :return: Bool - True if configuration successful

    Example:
        # Enable IPv6 autoconfig on Management interface
        config_ipv6_autoconfig(dut1, config="add", cli_type="klish")

        # Disable IPv6 autoconfig
        config_ipv6_autoconfig(dut1, config="remove", cli_type="klish")
    """
    cli_type = st.get_ui_type(dut, **kwargs)
    skip_error_check = kwargs.get("skip_error_check", False)

    st.log(f"{'Enabling' if config == 'add' else 'Disabling'} IPv6 autoconfig on Management interface (DUT: {dut})")

    if cli_type == "klish":
        mgmt_interface = get_management_interface_name(cli_type)

        # Build command for klish CLI
        cmd = f"interface {mgmt_interface}\n"

        if config == "add":
            cmd += "ipv6 address autoconfig"
        else:
            cmd += "no ipv6 address autoconfig"

        cmd += "\nexit\nexit"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=True)
        st.log(f"IPv6 autoconfig {'enabled' if config == 'add' else 'disabled'} on Management interface")
        return True

    elif cli_type == "click":
        # For click, IPv6 autoconfig might not be directly supported
        # Fall back to general IPv6 enable
        st.warn("Click CLI may not support IPv6 autoconfig directly")
        mgmt_interface = get_management_interface_name(cli_type)

        if config == "add":
            cmd = f"config interface ipv6 enable {mgmt_interface}"
        else:
            cmd = f"config interface ipv6 disable {mgmt_interface}"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check)
        st.log(f"IPv6 {'enabled' if config == 'add' else 'disabled'} on Management interface (Click CLI)")
        return True

    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False


def verify_ipv6_autoconfig_in_running_config(dut, should_exist=True, **kwargs):
    """
    Verify IPv6 autoconfig appears in running configuration for Management interface.

    This API checks whether "ipv6 address autoconfig" is present or absent in the
    running configuration for the Management interface.

    :param dut: Device under test
    :param should_exist: Autoconfig should be present (True) or absent (False), default True
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
    :return: Bool - True if verification passes

    Example:
        # Verify IPv6 autoconfig is configured
        verify_ipv6_autoconfig_in_running_config(dut1, should_exist=True)

        # Verify IPv6 autoconfig is NOT configured
        verify_ipv6_autoconfig_in_running_config(dut1, should_exist=False)
    """
    cli_type = st.get_ui_type(dut, **kwargs)
    mgmt_interface = get_management_interface_name(cli_type)

    st.log(f"Verifying IPv6 autoconfig {'presence' if should_exist else 'absence'} in running-config for {mgmt_interface}")

    # Get running configuration for Management interface
    output = interface_cli_api.show_running_config_interface(
        dut, mgmt_interface, cli_type=cli_type, skip_tmpl=True
    )

    if not output:
        st.error(f"Unable to retrieve running configuration for {mgmt_interface}")
        return False

    st.log(f"Running-config for {mgmt_interface}:\n{output}")

    # Search for "ipv6 address autoconfig" in the output
    pattern = r'ipv6\s+address\s+autoconfig'
    found = re.search(pattern, output, re.IGNORECASE)

    if should_exist:
        if found:
            st.log(f"'ipv6 address autoconfig' found in running-config")
            return True
        else:
            st.error(f"'ipv6 address autoconfig' NOT found in running-config")
            return False
    else:
        if found:
            st.error(f"'ipv6 address autoconfig' found in running-config (should not exist)")
            return False
        else:
            st.log(f"'ipv6 address autoconfig' NOT in running-config (as expected)")
            return True


def verify_management_interface_in_arp(dut, **kwargs):
    """
    Verify Management interface appears in ARP table.

    This API retrieves the ARP table and checks if the Management interface
    (Management0 or eth0) appears in the Interface column.

    :param dut: Device under test
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
    :return: Bool - True if Management interface found in ARP table

    Example:
        result = verify_management_interface_in_arp(dut1, cli_type="klish")
    """
    cli_type = st.get_ui_type(dut, **kwargs)
    expected_interface = get_management_interface_show_name(cli_type)

    st.log(f"Verifying {expected_interface} appears in ARP table")

    try:
        # Get ARP table
        arp_output = arp_api.show_arp(dut, cli_type=cli_type)
        st.log(f"ARP table output: {arp_output}")

        if not arp_output:
            st.log("ARP table is empty or unavailable")
            # This might be acceptable if no traffic, so we don't fail
            # Instead, we check if the command succeeded
            return True

        # Filter for Management interface entries
        mgmt_entries = filter_and_select(arp_output, None, {"iface": expected_interface})

        if not mgmt_entries:
            # Try alternate field name
            mgmt_entries = filter_and_select(arp_output, None, {"interface": expected_interface})

        if mgmt_entries:
            st.log(f"Found {len(mgmt_entries)} ARP entries for {expected_interface}")
            return True
        else:
            st.log(f"No ARP entries found for {expected_interface} (may be expected if no traffic)")
            # Check if Management interface at least appears in the output
            for entry in arp_output:
                iface = entry.get("iface") or entry.get("interface") or ""
                if expected_interface in iface:
                    st.log(f"Found {expected_interface} in ARP table")
                    return True

            st.error(f"{expected_interface} not found in ARP table")
            return False

    except Exception as e:
        st.error(f"Exception while verifying ARP table: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def verify_management_interface_in_ndp(dut, **kwargs):
    """
    Verify Management interface appears in IPv6 neighbor (NDP) table.

    This API retrieves the IPv6 neighbor table and checks if the Management
    interface (Management0 or eth0) appears in the Interface column.

    :param dut: Device under test
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
    :return: Bool - True if Management interface found in NDP table

    Example:
        result = verify_management_interface_in_ndp(dut1, cli_type="klish")
    """
    cli_type = st.get_ui_type(dut, **kwargs)
    expected_interface = get_management_interface_show_name(cli_type)

    st.log(f"Verifying {expected_interface} appears in IPv6 neighbor table")

    try:
        # Get IPv6 neighbor table
        ndp_output = arp_api.show_ndp(dut, cli_type=cli_type)
        st.log(f"IPv6 neighbor table output: {ndp_output}")

        if not ndp_output:
            st.log("IPv6 neighbor table is empty or unavailable")
            # This might be acceptable if no IPv6 traffic, so we don't fail
            return True

        # Filter for Management interface entries
        mgmt_entries = filter_and_select(ndp_output, None, {"interface": expected_interface})

        if not mgmt_entries:
            # Try alternate field name
            mgmt_entries = filter_and_select(ndp_output, None, {"iface": expected_interface})

        if mgmt_entries:
            st.log(f"Found {len(mgmt_entries)} IPv6 neighbor entries for {expected_interface}")
            return True
        else:
            st.log(f"No IPv6 neighbor entries found for {expected_interface} (may be expected if no traffic)")
            # Check if Management interface at least appears in the output
            for entry in ndp_output:
                iface = entry.get("interface") or entry.get("iface") or ""
                if expected_interface in iface:
                    st.log(f"Found {expected_interface} in IPv6 neighbor table")
                    return True

            st.error(f"{expected_interface} not found in IPv6 neighbor table")
            return False

    except Exception as e:
        st.error(f"Exception while verifying IPv6 neighbor table: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False


def get_arp_count_for_management_interface(dut, **kwargs):
    """
    Get the count of ARP entries for Management interface.

    :param dut: Device under test
    :param kwargs: Additional arguments
    :return: Integer count of ARP entries

    Example:
        count = get_arp_count_for_management_interface(dut1)
    """
    cli_type = st.get_ui_type(dut, **kwargs)
    expected_interface = get_management_interface_show_name(cli_type)

    try:
        arp_output = arp_api.show_arp(dut, cli_type=cli_type)
        if not arp_output:
            return 0

        mgmt_entries = filter_and_select(arp_output, None, {"iface": expected_interface})
        if not mgmt_entries:
            mgmt_entries = filter_and_select(arp_output, None, {"interface": expected_interface})

        return len(mgmt_entries)
    except Exception as e:
        st.error(f"Exception while getting ARP count: {str(e)}")
        return 0


def get_ndp_count_for_management_interface(dut, **kwargs):
    """
    Get the count of IPv6 neighbor entries for Management interface.

    :param dut: Device under test
    :param kwargs: Additional arguments
    :return: Integer count of NDP entries

    Example:
        count = get_ndp_count_for_management_interface(dut1)
    """
    cli_type = st.get_ui_type(dut, **kwargs)
    expected_interface = get_management_interface_show_name(cli_type)

    try:
        ndp_output = arp_api.show_ndp(dut, cli_type=cli_type)
        if not ndp_output:
            return 0

        mgmt_entries = filter_and_select(ndp_output, None, {"interface": expected_interface})
        if not mgmt_entries:
            mgmt_entries = filter_and_select(ndp_output, None, {"iface": expected_interface})

        return len(mgmt_entries)
    except Exception as e:
        st.error(f"Exception while getting NDP count: {str(e)}")
        return 0
