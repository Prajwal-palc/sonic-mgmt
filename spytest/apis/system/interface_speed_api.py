"""
Interface Speed Configuration API Module
Author: Shiva
2026

This module provides APIs for interface speed configuration and validation,
specifically for testing 'speed auto' functionality, transitions between static
speeds, and stability under various network conditions (BGP, PortChannel, traffic).
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
            # This ensures the command works regardless of current CLI mode
            cmd = "end\nterminal length 0"
            st.config(dut, cmd, type=cli_type, skip_error_check=True, conf=False)
            st.log("✓ Terminal length set to 0 (pagination disabled)")
            return True
        elif cli_type in ["click", "vtysh"]:
            # For Click/vtysh CLI, pagination is typically handled differently
            st.log(f"Terminal length setting for {cli_type} - not required")
            return True
        else:
            st.log(f"Terminal length setting for CLI type {cli_type}")
            return True

    except Exception as e:
        st.warn(f"Could not set terminal length (non-critical): {e}")
        return False


def config_interface_speed(dut, interface, speed, config="add", **kwargs):
    """
    Configure interface speed (static value or 'auto').

    This API configures the speed on a physical interface. Supports static speeds
    (e.g., 10000, 20000, 40000, 100000) or 'auto' for autonegotiation.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet32", "Ethernet16")
    :param speed: Speed value (integer like 20000, or string "auto")
    :param config: "add" to configure, "remove" to reset (default "add")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use (klish, click, etc.)
        - skip_error_check: Skip error checking (default False)
        - no_shutdown: Bring interface up after config (default True)
    :return: True if successful, False otherwise

    Example:
        # Set static speed
        config_interface_speed(dut1, "Ethernet32", 20000, cli_type="klish")

        # Enable speed auto
        config_interface_speed(dut1, "Ethernet32", "auto", cli_type="klish")

        # Remove speed config (revert to default)
        config_interface_speed(dut1, "Ethernet32", 20000, config="remove")
    """
    st.log(f"Configuring speed {speed} on {interface} (DUT: {dut})")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', False)
    no_shutdown = kwargs.get('no_shutdown', True)

    if cli_type == "klish":
        # Build command for IS-CLI (klish)
        cmd = f"interface {interface}\n"

        if config == "add":
            # Configure speed (auto or static value)
            if str(speed).lower() == "auto":
                cmd += "speed auto"
            else:
                cmd += f"speed {speed}"
        else:  # remove
            # Remove speed configuration
            if str(speed).lower() == "auto":
                cmd += "no speed auto"
            else:
                cmd += f"no speed {speed}"

        # Optionally bring interface up
        if no_shutdown and config == "add":
            cmd += "\nno shutdown"

        # Exit interface mode and config mode to return to enable mode
        cmd += "\nexit\nexit"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=True)
        st.log(f"✓ Speed {speed} {'configured' if config == 'add' else 'removed'} on {interface}")
        return True

    elif cli_type == "click":
        # Build command for Click CLI
        if config == "add":
            if str(speed).lower() == "auto":
                cmd = f"config interface speed {interface} auto"
            else:
                cmd = f"config interface speed {interface} {speed}"
        else:
            # Click doesn't have direct 'no speed' - typically set to default
            st.log("Speed removal in Click CLI - setting to default behavior")
            return True

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check)

        # Bring interface up if needed
        if no_shutdown and config == "add":
            cmd_startup = f"config interface startup {interface}"
            st.config(dut, cmd_startup, type=cli_type, skip_error_check=True)

        st.log(f"✓ Speed {speed} configured on {interface} (Click CLI)")
        return True

    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False


def show_running_config_interface(dut, interface, **kwargs):
    """
    Get running configuration for a specific interface.

    This API retrieves the running configuration for an interface, ensuring
    pagination is disabled to avoid '--more--' prompts.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet32")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - skip_tmpl: Skip template parsing (default True for raw output)
    :return: String containing interface running configuration

    Example:
        config = show_running_config_interface(dut1, "Ethernet32", cli_type="klish")
        if "speed 20000" in config:
            st.log("Speed is set to 20000")
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


def verify_interface_speed_in_config(dut, interface, expected_speed, **kwargs):
    """
    Verify interface speed appears correctly in running configuration.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet32")
    :param expected_speed: Expected speed value (integer or "auto")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - should_exist: Speed should exist (True) or not exist (False), default True
    :return: Bool - True if verification passes

    Example:
        # Verify speed is set to 20000
        verify_interface_speed_in_config(dut1, "Ethernet32", 20000)

        # Verify speed auto is configured
        verify_interface_speed_in_config(dut1, "Ethernet32", "auto")

        # Verify speed 40000 is NOT configured
        verify_interface_speed_in_config(dut1, "Ethernet32", 40000, should_exist=False)
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)
    should_exist = kwargs.get('should_exist', True)

    st.log(f"Verifying speed {expected_speed} in running-config for {interface}")

    # Get running configuration for the interface
    output = show_running_config_interface(dut, interface, cli_type=cli_type, skip_tmpl=True)

    if not output:
        st.warn(f"No running-config output for {interface}")
        return not should_exist  # If we expect it not to exist, return True

    st.log(f"Running-config for {interface}:\n{output}")

    # Build search pattern
    if str(expected_speed).lower() == "auto":
        pattern = r'speed\s+auto'
    else:
        pattern = f"speed\\s+{expected_speed}"

    found = re.search(pattern, output, re.IGNORECASE)

    if should_exist:
        if found:
            st.log(f"✓ Speed {expected_speed} found in running-config")
            return True
        else:
            st.error(f"✗ Speed {expected_speed} NOT found in running-config")
            return False
    else:
        if found:
            st.error(f"✗ Speed {expected_speed} found in running-config (should not exist)")
            return False
        else:
            st.log(f"✓ Speed {expected_speed} NOT in running-config (as expected)")
            return True


def show_interface_counters(dut, interface, **kwargs):
    """
    Get interface counters/statistics.

    This API retrieves interface counters including RX/TX packets, bytes, drops, errors.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet32")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - skip_tmpl: Skip template parsing (default False)
    :return: Dictionary or list containing interface statistics

    Example:
        counters = show_interface_counters(dut1, "Ethernet32", cli_type="klish")
        st.log(f"RX Drops: {counters.get('rx_drp', 0)}")
    """
    st.log(f"Retrieving interface counters for {interface}")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_tmpl = kwargs.get('skip_tmpl', False)

    # Build command based on CLI type
    if cli_type == "klish":
        cmd = f"show interface counters {interface}"
    elif cli_type == "click":
        cmd = f"show interfaces counters -i {interface}"
    else:
        cmd = f"show interface counters {interface}"

    # Execute command
    try:
        output = st.show(dut, cmd, type=cli_type, skip_tmpl=skip_tmpl)
        return output if output else ([] if not skip_tmpl else "")

    except Exception as e:
        st.error(f"Error executing show interface counters: {e}")
        return [] if not skip_tmpl else ""


def clear_interface_counters(dut, interface=None, **kwargs):
    """
    Clear interface counters/statistics.

    This API clears interface counters to establish a baseline for monitoring.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet32"), or None to clear all
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - skip_error_check: Skip error checking (default True)
    :return: True if successful, False otherwise

    Example:
        # Clear specific interface
        clear_interface_counters(dut1, "Ethernet32", cli_type="klish")

        # Clear all interfaces
        clear_interface_counters(dut1, cli_type="klish")
    """
    st.log(f"Clearing interface counters{' for ' + interface if interface else ' (all interfaces)'}")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', True)

    # Build command based on CLI type
    if cli_type == "klish":
        if interface:
            cmd = f"clear interface counters {interface}"
        else:
            cmd = "clear interface counters"
    elif cli_type == "click":
        if interface:
            cmd = f"sonic-clear counters -i {interface}"
        else:
            cmd = "sonic-clear counters"
    else:
        cmd = "clear interface counters"

    # Execute command
    try:
        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=False)
        st.log("✓ Interface counters cleared")
        return True

    except Exception as e:
        st.error(f"Error clearing interface counters: {e}")
        return False


def verify_no_packet_drops(dut, interface, **kwargs):
    """
    Verify zero packet drops on an interface.

    This API checks interface counters to ensure there are no RX/TX drops,
    indicating stable operation during speed transitions.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet32")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - tolerance: Number of drops to tolerate (default 0)
        - check_rx: Check RX drops (default True)
        - check_tx: Check TX drops (default True)
    :return: Tuple (success: bool, details: dict)

    Example:
        success, details = verify_no_packet_drops(dut1, "Ethernet32", cli_type="klish")
        if not success:
            st.log(f"Packet drops detected: {details}")
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)
    tolerance = kwargs.get('tolerance', 0)
    check_rx = kwargs.get('check_rx', True)
    check_tx = kwargs.get('check_tx', True)

    st.log(f"Verifying zero packet drops on {interface}")

    # Get interface counters
    counters_output = show_interface_counters(dut, interface, cli_type=cli_type, skip_tmpl=True)

    if not counters_output:
        st.warn(f"No counters output for {interface}")
        return False, {"error": "No counters output"}

    st.log(f"Counters for {interface}:\n{counters_output}")

    # Parse counters for drops
    # Patterns to match RX/TX drops in output
    rx_drop_patterns = [
        r'RX_DRP[:\s]+(\d+)',
        r'RX\s+dropped[:\s]+(\d+)',
        r'rx_drp[:\s]+(\d+)',
        r'RX-DRP[:\s]+(\d+)'
    ]

    tx_drop_patterns = [
        r'TX_DRP[:\s]+(\d+)',
        r'TX\s+dropped[:\s]+(\d+)',
        r'tx_drp[:\s]+(\d+)',
        r'TX-DRP[:\s]+(\d+)'
    ]

    rx_drops = 0
    tx_drops = 0

    # Search for RX drops
    if check_rx:
        for pattern in rx_drop_patterns:
            match = re.search(pattern, counters_output, re.IGNORECASE)
            if match:
                rx_drops = int(match.group(1))
                st.log(f"Found RX drops: {rx_drops}")
                break

    # Search for TX drops
    if check_tx:
        for pattern in tx_drop_patterns:
            match = re.search(pattern, counters_output, re.IGNORECASE)
            if match:
                tx_drops = int(match.group(1))
                st.log(f"Found TX drops: {tx_drops}")
                break

    # Verify drops are within tolerance
    details = {
        "rx_drops": rx_drops,
        "tx_drops": tx_drops,
        "tolerance": tolerance
    }

    if check_rx and rx_drops > tolerance:
        st.error(f"✗ RX drops ({rx_drops}) exceed tolerance ({tolerance})")
        details["error"] = f"RX drops: {rx_drops}"
        return False, details

    if check_tx and tx_drops > tolerance:
        st.error(f"✗ TX drops ({tx_drops}) exceed tolerance ({tolerance})")
        details["error"] = f"TX drops: {tx_drops}"
        return False, details

    st.log(f"✓ No packet drops detected (RX: {rx_drops}, TX: {tx_drops}, tolerance: {tolerance})")
    details["success"] = True
    return True, details


def get_interface_status(dut, interface, **kwargs):
    """
    Get interface operational status (up/down).

    This API retrieves the current operational status of an interface.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet32")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
    :return: String - "up", "down", or "unknown"

    Example:
        status = get_interface_status(dut1, "Ethernet32", cli_type="klish")
        if status == "up":
            st.log("Interface is operational")
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)

    st.log(f"Getting operational status for {interface}")

    # Build command based on CLI type
    if cli_type == "klish":
        cmd = f"show interface status {interface}"
    elif cli_type == "click":
        cmd = f"show interfaces status {interface}"
    else:
        cmd = f"show interface status {interface}"

    # Execute command
    try:
        output = st.show(dut, cmd, type=cli_type, skip_tmpl=True)

        if not output:
            st.warn(f"No status output for {interface}")
            return "unknown"

        output_str = str(output) if not isinstance(output, str) else output

        # Look for "up" or "down" in output
        if re.search(r'\bup\b', output_str, re.IGNORECASE):
            st.log(f"✓ Interface {interface} is UP")
            return "up"
        elif re.search(r'\bdown\b', output_str, re.IGNORECASE):
            st.log(f"Interface {interface} is DOWN")
            return "down"
        else:
            st.warn(f"Could not determine status for {interface}")
            return "unknown"

    except Exception as e:
        st.error(f"Error getting interface status: {e}")
        return "unknown"


def verify_interface_up(dut, interface, **kwargs):
    """
    Verify interface is operationally up.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet32")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - timeout: Polling timeout in seconds (default 30)
    :return: Bool - True if interface is up

    Example:
        if verify_interface_up(dut1, "Ethernet32", timeout=60):
            st.log("Interface is up and ready")
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)
    timeout = kwargs.get('timeout', 30)

    st.log(f"Verifying interface {interface} is UP (timeout: {timeout}s)")

    def _check_interface_up():
        status = get_interface_status(dut, interface, cli_type=cli_type)
        return status == "up"

    if st.poll_wait(_check_interface_up, timeout):
        st.log(f"✓ Interface {interface} is UP")
        return True
    else:
        st.error(f"✗ Interface {interface} is not UP after {timeout}s")
        return False
