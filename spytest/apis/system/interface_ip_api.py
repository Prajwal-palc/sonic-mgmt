"""
Interface IP Configuration API Module
Author: Shiva
2026

This module provides APIs for interface IP configuration and validation,
specifically for Management interface visibility, Loopback constraints, and
IP address overlap detection.
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
            # For IS-CLI (klish), use "do terminal length 0" to work from any mode
            # The "do" prefix allows the command to work from config mode or enable mode
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


def show_ip_interfaces(dut, interface=None, **kwargs):
    """
    Execute 'show ip interfaces' command and return parsed output.

    This API retrieves IP interface information using the appropriate CLI command
    based on the CLI type. It can show all interfaces or a specific interface.

    :param dut: Device under test
    :param interface: Optional specific interface name (e.g., "Ethernet0", "Management0")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use (klish, click, etc.)
        - skip_tmpl: Skip template parsing (default False)
    :return: List of dictionaries containing interface information, or raw output

    Example:
        # Get all IP interfaces
        interfaces = show_ip_interfaces(dut1, cli_type="klish")

        # Get specific interface
        mgmt_intf = show_ip_interfaces(dut1, interface="Management0", cli_type="klish")
    """
    st.log(f"Retrieving IP interface information{' for ' + interface if interface else ''}")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_tmpl = kwargs.get('skip_tmpl', False)

    # Set terminal length to 0 to avoid pagination
    set_terminal_length_zero(dut, cli_type)

    # Build command based on CLI type
    if cli_type == "klish":
        if interface:
            cmd = f"show ip interfaces {interface}"
        else:
            cmd = "show ip interfaces"
    elif cli_type == "click":
        cmd = "show ip interfaces"
    else:
        cmd = "show ip interfaces"

    # Execute command
    try:
        output = st.show(dut, cmd, type=cli_type, skip_tmpl=skip_tmpl)

        if skip_tmpl:
            # Return raw output
            if isinstance(output, list):
                return "\n".join([str(item) for item in output])
            return str(output)
        else:
            # Return parsed output
            return output if output else []

    except Exception as e:
        st.error(f"Error executing show ip interfaces: {e}")
        return [] if not skip_tmpl else ""


def verify_management_ip_visible(dut, **kwargs):
    """
    Verify that Management interface IP is visible in 'show ip interfaces' output.

    This API checks if the Management interface (Management0, Management 0, or eth0)
    appears in the output and has an IP address configured.

    :param dut: Device under test
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - expected_interface: Expected interface name (default "Management0")
        - verify_ip_format: Verify IP address format (default True)
    :return: Tuple (success: bool, ip_address: str or None, details: dict)

    Example:
        success, ip_addr, details = verify_management_ip_visible(dut1, cli_type="klish")
        if success:
            st.log(f"Management IP found: {ip_addr}")
    """
    st.log("Verifying Management interface IP visibility")

    cli_type = kwargs.get('cli_type', 'klish')
    expected_interface = kwargs.get('expected_interface', 'Management0')
    verify_ip_format = kwargs.get('verify_ip_format', True)

    # Get IP interfaces output (raw text for parsing)
    output = show_ip_interfaces(dut, cli_type=cli_type, skip_tmpl=True)

    if not output:
        st.error("No output from show ip interfaces command")
        return False, None, {"error": "No output from command"}

    st.log(f"Parsing output for Management interface:\n{output}")

    # Pattern to match Management interface variations
    # Matches: "Management0", "Management 0", "eth0"
    mgmt_patterns = [
        r'Management\s*0',
        r'Management0',
        r'eth0'
    ]

    # IP address pattern (x.x.x.x/xx or x.x.x.x)
    ip_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:/(\d{1,2}))?'

    found_interface = False
    found_ip = None
    interface_name = None

    # Search for Management interface in output
    for pattern in mgmt_patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            found_interface = True
            interface_name = match.group(0)
            st.log(f"✓ Found Management interface: {interface_name}")
            break

    if not found_interface:
        st.error("Management interface not found in output")
        return False, None, {"error": "Management interface not found"}

    # Extract IP address near the interface name
    # Look for IP in the same line or nearby lines
    lines = output.split('\n')
    for i, line in enumerate(lines):
        if re.search(r'Management|eth0', line, re.IGNORECASE):
            # Check current line and next few lines for IP
            check_lines = lines[i:i+5]
            for check_line in check_lines:
                ip_match = re.search(ip_pattern, check_line)
                if ip_match:
                    ip_addr = ip_match.group(1)
                    subnet = ip_match.group(2) if ip_match.group(2) else None

                    if subnet:
                        found_ip = f"{ip_addr}/{subnet}"
                    else:
                        found_ip = ip_addr

                    st.log(f"✓ Found Management IP: {found_ip}")
                    break
            if found_ip:
                break

    if not found_ip:
        st.warn("Management interface found but no IP address detected")
        return False, None, {
            "interface": interface_name,
            "error": "No IP address found"
        }

    # Verify IP format if requested
    if verify_ip_format:
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', found_ip):
            st.error(f"Invalid IP format: {found_ip}")
            return False, found_ip, {
                "interface": interface_name,
                "ip": found_ip,
                "error": "Invalid IP format"
            }

    st.log(f"✓✓ Management interface verified: {interface_name} with IP {found_ip}")

    return True, found_ip, {
        "interface": interface_name,
        "ip": found_ip,
        "success": True
    }


def config_loopback_interface(dut, loopback_name, config="add", **kwargs):
    """
    Create or delete a Loopback interface.

    :param dut: Device under test
    :param loopback_name: Loopback interface name (e.g., "Loopback1")
    :param config: "add" to create, "remove" to delete (default "add")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use (klish, click, etc.)
        - skip_error_check: Skip error checking (default False)
    :return: True if successful, False otherwise

    Example:
        # Create Loopback1
        config_loopback_interface(dut1, "Loopback1", config="add", cli_type="klish")

        # Delete Loopback1
        config_loopback_interface(dut1, "Loopback1", config="remove", cli_type="klish")
    """
    st.log(f"{'Creating' if config == 'add' else 'Deleting'} Loopback interface: {loopback_name}")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', False)

    # Normalize loopback name (ensure proper capitalization)
    if not loopback_name.lower().startswith('loopback'):
        loopback_name = f"Loopback{loopback_name}"

    if cli_type == "klish":
        if config == "add":
            # Enter interface mode and exit back to config mode
            cmd = f"interface {loopback_name}\nexit"
        else:  # remove
            cmd = f"no interface {loopback_name}"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=True)
        st.log(f"✓ Loopback interface {loopback_name} {'created' if config == 'add' else 'deleted'}")
        return True

    elif cli_type == "click":
        if config == "add":
            cmd = f"config loopback add {loopback_name}"
        else:
            cmd = f"config loopback del {loopback_name}"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check)
        st.log(f"✓ Loopback interface {loopback_name} {'created' if config == 'add' else 'deleted'}")
        return True

    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False


def config_loopback_ip_address(dut, loopback_name, ip_address, subnet_mask, config="add", **kwargs):
    """
    Configure IP address on a Loopback interface with subnet mask validation.

    This API attempts to configure an IP address on a Loopback interface.
    For negative testing, it can be used to verify that non-/32 masks are rejected.

    :param dut: Device under test
    :param loopback_name: Loopback interface name (e.g., "Loopback1")
    :param ip_address: IP address (e.g., "10.0.0.1")
    :param subnet_mask: Subnet mask as integer (e.g., 32, 24, 30)
    :param config: "add" or "remove" (default "add")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - skip_error_check: Skip error checking (default False for validation)
        - expect_error: Expect command to fail (for negative tests)
    :return: Dict with {'success': bool, 'error': str or None, 'accepted': bool}

    Example:
        # Should succeed - /32 mask
        result = config_loopback_ip_address(dut1, "Loopback1", "10.0.0.1", 32, cli_type="klish")

        # Should fail - /24 mask (negative test)
        result = config_loopback_ip_address(dut1, "Loopback1", "10.0.0.1", 24,
                                            expect_error=True, cli_type="klish")
    """
    st.log(f"Configuring IP {ip_address}/{subnet_mask} on {loopback_name}")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', False)
    expect_error = kwargs.get('expect_error', False)

    # Normalize loopback name
    if not loopback_name.lower().startswith('loopback'):
        loopback_name = f"Loopback{loopback_name}"

    result = {
        'success': False,
        'error': None,
        'accepted': False,
        'command': None
    }

    if cli_type == "klish":
        # Build command with proper exit to return to enable mode
        cmd = f"interface {loopback_name}\n"
        if config == "add":
            cmd += f"ip address {ip_address}/{subnet_mask}"
        else:
            cmd += f"no ip address {ip_address}/{subnet_mask}"
        # Exit interface config mode and then config mode to return to enable mode
        cmd += "\nexit\nexit"

        result['command'] = cmd

        # Execute with error capture
        try:
            output = st.config(dut, cmd, type=cli_type, skip_error_check=True, conf=True)

            # Check output for errors
            output_str = str(output) if output else ""

            # Error patterns for Loopback /32 constraint
            error_patterns = [
                r'Loopback.*only supports /32',
                r'Error.*Loopback.*32',
                r'invalid.*mask.*loopback',
                r'Error',
                r'%Error'
            ]

            error_found = False
            for pattern in error_patterns:
                if re.search(pattern, output_str, re.IGNORECASE):
                    error_found = True
                    result['error'] = output_str
                    st.log(f"Configuration rejected (as expected): {output_str}")
                    break

            if error_found:
                result['accepted'] = False
                if expect_error:
                    result['success'] = True  # Expected error occurred
                else:
                    result['success'] = False  # Unexpected error
            else:
                result['accepted'] = True
                if expect_error:
                    result['success'] = False  # Expected error but command accepted
                else:
                    result['success'] = True  # Command accepted as expected

        except Exception as e:
            st.log(f"Exception during configuration: {e}")
            result['error'] = str(e)
            result['accepted'] = False
            result['success'] = expect_error  # Success if we expected an error

    return result


def verify_interface_ip_in_config(dut, interface, ip_address, subnet_mask=None, **kwargs):
    """
    Verify IP address appears in running configuration for specified interface.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet0", "Loopback1")
    :param ip_address: IP address to verify (e.g., "192.168.100.1")
    :param subnet_mask: Optional subnet mask (e.g., 24 for /24)
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - is_secondary: Check if marked as secondary (default False)
        - should_exist: IP should exist (True) or not exist (False), default True
    :return: Bool - True if verification passes

    Example:
        # Verify primary IP exists
        verify_interface_ip_in_config(dut1, "Ethernet0", "192.168.100.1", 24)

        # Verify IP does NOT exist (negative check)
        verify_interface_ip_in_config(dut1, "Ethernet0", "192.168.100.1", 24,
                                     should_exist=False)
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)
    is_secondary = kwargs.get('is_secondary', False)
    should_exist = kwargs.get('should_exist', True)

    st.log(f"Verifying IP {ip_address} in running-config for {interface}")

    # Set terminal length to 0 to avoid pagination with running-config
    set_terminal_length_zero(dut, cli_type)

    # Get running configuration for the interface
    if cli_type == "klish":
        cmd = f"show running-configuration interface {interface}"
    else:
        cmd = f"show running-config interface {interface}"

    output = st.show(dut, cmd, type=cli_type, skip_tmpl=True)

    if not output:
        st.warn(f"No running-config output for {interface}")
        return not should_exist  # If we expect it not to exist, return True

    output_str = str(output) if not isinstance(output, str) else output
    st.log(f"Running-config for {interface}:\n{output_str}")

    # Build search pattern
    if subnet_mask:
        ip_pattern = f"{re.escape(ip_address)}/{subnet_mask}"
    else:
        ip_pattern = re.escape(ip_address)

    if is_secondary:
        # Look for pattern with "secondary" keyword
        pattern = f"ip address\\s+{ip_pattern}\\s+secondary"
    else:
        # Look for IP address pattern
        pattern = f"ip address\\s+{ip_pattern}"

    found = re.search(pattern, output_str, re.IGNORECASE)

    if should_exist:
        if found:
            st.log(f"✓ IP {ip_address} found in running-config")
            return True
        else:
            st.error(f"✗ IP {ip_address} NOT found in running-config")
            return False
    else:
        if found:
            st.error(f"✗ IP {ip_address} found in running-config (should not exist)")
            return False
        else:
            st.log(f"✓ IP {ip_address} NOT in running-config (as expected)")
            return True


def config_secondary_ip_address(dut, interface, ip_address, subnet_mask, **kwargs):
    """
    Configure a secondary IP address on an interface.

    This API configures a secondary IP address using the 'secondary' keyword.
    It can detect if the CLI rejects duplicate IP addresses.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet0")
    :param ip_address: IP address (e.g., "192.168.100.2")
    :param subnet_mask: Subnet mask as integer (e.g., 24)
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - expect_error: Expect command to fail (for duplicate detection)
    :return: Dict with {'success': bool, 'error': str or None, 'accepted': bool}

    Example:
        # Add valid secondary IP
        result = config_secondary_ip_address(dut1, "Ethernet0", "192.168.100.2", 24)

        # Attempt duplicate (should be rejected)
        result = config_secondary_ip_address(dut1, "Ethernet0", "192.168.100.1", 24,
                                            expect_error=True)
    """
    st.log(f"Configuring secondary IP {ip_address}/{subnet_mask} on {interface}")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    expect_error = kwargs.get('expect_error', False)

    result = {
        'success': False,
        'error': None,
        'accepted': False,
        'command': None
    }

    if cli_type == "klish":
        # Build command with 'secondary' keyword and proper exits
        cmd = f"interface {interface}\n"
        cmd += f"ip address {ip_address}/{subnet_mask} secondary"
        # Exit interface config mode and then config mode to return to enable mode
        cmd += "\nexit\nexit"

        result['command'] = cmd

        try:
            output = st.config(dut, cmd, type=cli_type, skip_error_check=True, conf=True)

            output_str = str(output) if output else ""

            # Error patterns for duplicate IP detection
            error_patterns = [
                r'is already configured as primary',
                r'Error.*already.*primary',
                r'duplicate.*address',
                r'address.*exists',
                r'Error',
                r'%Error'
            ]

            error_found = False
            for pattern in error_patterns:
                if re.search(pattern, output_str, re.IGNORECASE):
                    error_found = True
                    result['error'] = output_str
                    st.log(f"Secondary IP rejected: {output_str}")
                    break

            if error_found:
                result['accepted'] = False
                result['success'] = expect_error  # Success if we expected error
            else:
                result['accepted'] = True
                result['success'] = not expect_error  # Success if we didn't expect error

        except Exception as e:
            st.log(f"Exception during secondary IP configuration: {e}")
            result['error'] = str(e)
            result['accepted'] = False
            result['success'] = expect_error

    return result
