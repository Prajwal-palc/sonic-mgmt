"""
Interface CLI Configuration and Verification API Module
Author: Shiva
2026

This module provides APIs for interface CLI operations including:
- IPv6 enable/disable configuration and verification
- CLI help/options verification (e.g., speed options)
- Running configuration verification
"""

import re
from spytest import st
from utilities.utils import get_supported_ui_type_list


def get_cfg_cli_type(dut, **kwargs):
    """
    Get the CLI type for configuration commands.

    :param dut: Device under test
    :param kwargs: Additional arguments
    :return: CLI type string
    """
    cli_type = st.get_ui_type(dut, **kwargs)
    if cli_type in ["click", "vtysh"]:
        cli_type = "vtysh"
    elif cli_type in ["rest-patch", "rest-put"]:
        cli_type = "rest-patch"
    elif cli_type in get_supported_ui_type_list():
        return cli_type
    else:
        cli_type = "klish"
    return cli_type


def set_terminal_length_zero(dut, cli_type=None):
    """
    Set terminal length to 0 to prevent pagination (--more--).

    This prevents "show running-configuration" and other show commands
    from pausing for user input when output exceeds screen length.

    :param dut: Device under test
    :param cli_type: CLI type (default: auto-detect)
    :return: True if successful, False otherwise

    Example:
        set_terminal_length_zero(dut1, cli_type="klish")
    """
    if cli_type is None:
        cli_type = get_cfg_cli_type(dut)

    try:
        if cli_type == "klish":
            # Exit to enable mode first, then set terminal length
            cmd = "end\nterminal length 0"
            st.config(dut, cmd, type=cli_type, skip_error_check=True, conf=False)
            st.log("Terminal length set to 0 (pagination disabled)")
            return True
        elif cli_type in ["click", "vtysh"]:
            st.log(f"Terminal length setting for {cli_type} - not required")
            return True
        else:
            st.log(f"Terminal length setting for CLI type {cli_type}")
            return True

    except Exception as e:
        st.warn(f"Could not set terminal length (non-critical): {e}")
        return False


def show_running_config_interface(dut, interface, **kwargs):
    """
    Get running configuration for a specific interface.

    This API retrieves the running configuration for an interface, ensuring
    pagination is disabled to avoid '--more--' prompts.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet8")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - skip_tmpl: Skip template parsing (default True for raw output)
    :return: String containing interface running configuration

    Example:
        config = show_running_config_interface(dut1, "Ethernet8", cli_type="klish")
        if "ipv6 enable" in config:
            st.log("IPv6 is enabled")
    """
    st.log(f"Retrieving running configuration for {interface}")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_tmpl = kwargs.get('skip_tmpl', True)

    # Set terminal length to 0 to avoid pagination
    set_terminal_length_zero(dut, cli_type)

    # Build command based on CLI type
    if cli_type == "klish":
        cmd = f"show running-configuration interface {interface}"
    elif cli_type == "click":
        cmd = f"show runningconfiguration interface {interface}"
    else:
        cmd = f"show running-configuration interface {interface}"

    # Execute command
    try:
        output = st.show(dut, cmd, type=cli_type, skip_tmpl=skip_tmpl)

        if skip_tmpl:
            # Return raw output as string
            if isinstance(output, list):
                return "\n".join([str(item) for item in output])
            return str(output)
        else:
            # Return parsed output
            return output if output else []

    except Exception as e:
        st.error(f"Error executing show running-configuration: {e}")
        return "" if skip_tmpl else []


def config_ipv6_enable(dut, interface, config="add", **kwargs):
    """
    Enable or disable IPv6 on an interface.

    This API enables or disables IPv6 functionality on a physical interface.
    When IPv6 is enabled, the interface can process IPv6 packets and auto-generate
    link-local addresses.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet8", "Ethernet32")
    :param config: "add" to enable IPv6, "remove" to disable (default "add")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use (klish, click, etc.)
        - skip_error_check: Skip error checking (default False)
    :return: True if successful, False otherwise

    Example:
        # Enable IPv6
        config_ipv6_enable(dut1, "Ethernet8", cli_type="klish")

        # Disable IPv6
        config_ipv6_enable(dut1, "Ethernet8", config="remove", cli_type="klish")
    """
    st.log(f"{'Enabling' if config == 'add' else 'Disabling'} IPv6 on {interface} (DUT: {dut})")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', False)

    if cli_type == "klish":
        # Build command for IS-CLI (klish)
        cmd = f"interface {interface}\n"

        if config == "add":
            # Enable IPv6
            cmd += "ipv6 enable"
        else:  # remove
            # Disable IPv6
            cmd += "no ipv6 enable"

        # Exit interface mode and config mode
        cmd += "\nexit\nexit"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=True)
        st.log(f"IPv6 {'enabled' if config == 'add' else 'disabled'} on {interface}")
        return True

    elif cli_type == "click":
        # Build command for Click CLI
        if config == "add":
            cmd = f"config interface ipv6 enable {interface}"
        else:
            cmd = f"config interface ipv6 disable {interface}"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check)
        st.log(f"IPv6 {'enabled' if config == 'add' else 'disabled'} on {interface} (Click CLI)")
        return True

    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False


def verify_ipv6_enable_in_config(dut, interface, should_exist=True, **kwargs):
    """
    Verify IPv6 enable state appears correctly in running configuration.

    This API checks whether "ipv6 enable" is present or absent in the
    running configuration for the specified interface.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet8")
    :param should_exist: IPv6 enable should be present (True) or absent (False), default True
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
    :return: Bool - True if verification passes

    Example:
        # Verify IPv6 is enabled
        verify_ipv6_enable_in_config(dut1, "Ethernet8", should_exist=True)

        # Verify IPv6 is NOT enabled
        verify_ipv6_enable_in_config(dut1, "Ethernet8", should_exist=False)
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)

    st.log(f"Verifying IPv6 enable {'presence' if should_exist else 'absence'} in running-config for {interface}")

    # Get running configuration for the interface
    output = show_running_config_interface(dut, interface, cli_type=cli_type, skip_tmpl=True)

    if not output:
        st.warn(f"No running-config output for {interface}")
        return not should_exist  # If we expect it not to exist, return True

    st.log(f"Running-config for {interface}:\n{output}")

    # Search for "ipv6 enable" in the output
    pattern = r'ipv6\s+enable'
    found = re.search(pattern, output, re.IGNORECASE)

    if should_exist:
        if found:
            st.log(f"'ipv6 enable' found in running-config")
            return True
        else:
            st.error(f"'ipv6 enable' NOT found in running-config")
            return False
    else:
        if found:
            st.error(f"'ipv6 enable' found in running-config (should not exist)")
            return False
        else:
            st.log(f"'ipv6 enable' NOT in running-config (as expected)")
            return True


def get_interface_speed_options(dut, interface, **kwargs):
    """
    Get available speed options for an interface using CLI help (speed ?).

    This API retrieves the list of supported speed values for an interface
    by executing the "speed ?" command in interface configuration mode.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet8")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
    :return: String containing the speed options help output

    Example:
        options = get_interface_speed_options(dut1, "Ethernet8", cli_type="klish")
        if "auto" in options:
            st.log("Speed auto is supported")
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)

    st.log(f"Retrieving speed options for {interface}")

    if cli_type == "klish":
        # Enter interface config mode and execute "speed ?"
        cmd = f"interface {interface}\nspeed ?\nexit\nexit"

        # Execute with skip_error_check=True since "?" might be treated as incomplete command
        output = st.config(dut, cmd, type=cli_type, skip_error_check=True, conf=True)

        st.log(f"Speed options for {interface}:\n{output}")
        return str(output) if output else ""

    elif cli_type == "click":
        st.log("Click CLI does not support interactive help like klish")
        return ""

    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return ""


def verify_speed_options_available(dut, interface, expected_options, **kwargs):
    """
    Verify that expected speed options are available for an interface.

    This API checks if the interface supports the expected speed options
    by examining the CLI help output.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet8")
    :param expected_options: List of expected options (e.g., ["auto", "10000", "25000"])
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
    :return: Tuple (success: bool, details: dict)

    Example:
        success, details = verify_speed_options_available(
            dut1, "Ethernet8",
            ["auto", "10000", "25000", "40000", "100000"],
            cli_type="klish"
        )
        if not success:
            st.log(f"Missing options: {details['missing']}")
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)

    st.log(f"Verifying speed options for {interface}")

    # Get speed options help output
    output = get_interface_speed_options(dut, interface, cli_type=cli_type)

    if not output:
        st.warn(f"No speed options output for {interface}")
        return False, {"error": "No output retrieved"}

    # Check for each expected option
    missing_options = []
    found_options = []

    for option in expected_options:
        # Create pattern to match the option
        # For "auto", match "auto" as a word
        # For numbers, match the number
        if str(option).lower() == "auto":
            pattern = r'\bauto\b'
        else:
            pattern = f"\\b{option}\\b"

        if re.search(pattern, output, re.IGNORECASE):
            found_options.append(option)
            st.log(f"Speed option '{option}' is available")
        else:
            missing_options.append(option)
            st.warn(f"Speed option '{option}' is NOT available")

    details = {
        "expected": expected_options,
        "found": found_options,
        "missing": missing_options
    }

    if missing_options:
        st.error(f"Missing speed options: {missing_options}")
        return False, details
    else:
        st.log(f"All expected speed options are available: {expected_options}")
        return True, details
