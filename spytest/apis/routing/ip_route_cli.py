# This file contains IP route CLI validation helper APIs
# Author: Shiva
# Created: 2026

from spytest import st


def show_ip_route_help(dut, cli_type="klish"):
    """
    Execute 'show ip route ?' and return help output.

    Author: Shiva
    Source: apis/routing/ip_route_cli.py

    :param dut: Device Under Test
    :param cli_type: CLI type (klish/click)
    :return: Help command output

    Example:
        help_output = show_ip_route_help(dut, "klish")
        if "connected" in str(help_output):
            st.log("Connected routes option available")
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type == "klish":
        command = "show ip route ?"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True, skip_error_check=True)
        return output
    elif cli_type == "click":
        command = "show ip route --help"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True, skip_error_check=True)
        return output
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return None


def show_ip_route_connected(dut, cli_type="klish"):
    """
    Execute 'show ip route connected' to display only connected routes.

    Author: Shiva
    Source: apis/routing/ip_route_cli.py

    :param dut: Device Under Test
    :param cli_type: CLI type (klish/click)
    :return: Connected routes output

    Example:
        output = show_ip_route_connected(dut, "klish")
        if "directly connected" in str(output):
            st.log("Connected routes found")
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type == "klish":
        command = "show ip route connected"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True)
        return output
    elif cli_type == "click":
        command = "show ip route"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True)
        # Filter for connected routes in click mode
        return output
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return None


def show_ip_route_bgp_cli(dut, cli_type="klish"):
    """
    Execute 'show ip route bgp' to display only BGP routes.

    Author: Shiva
    Source: apis/routing/ip_route_cli.py

    Note: This executes the CLI command directly for CLI validation.
          Empty output is valid if no BGP routes exist.

    :param dut: Device Under Test
    :param cli_type: CLI type (klish/click)
    :return: BGP routes output (may be empty)

    Example:
        output = show_ip_route_bgp_cli(dut, "klish")
        # Empty output is valid - means no BGP routes configured
        st.log(f"BGP routes output: {output}")
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type == "klish":
        command = "show ip route bgp"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True, skip_error_check=True)
        return output
    elif cli_type == "click":
        command = "show ip route bgp"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True, skip_error_check=True)
        return output
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return None


def show_ip_route_specific_ip(dut, ip_address, cli_type="klish"):
    """
    Execute 'show ip route <IP>' to lookup routing entry for specific IP.

    Author: Shiva
    Source: apis/routing/ip_route_cli.py

    :param dut: Device Under Test
    :param ip_address: IP address to lookup (e.g., "192.168.100.194")
    :param cli_type: CLI type (klish/click)
    :return: Routing entry output for the specific IP

    Example:
        # Lookup DUT's management IP
        mgmt_ip = "192.168.100.194"
        output = show_ip_route_specific_ip(dut, mgmt_ip, "klish")
        if "Routing entry for" in str(output):
            st.log(f"Found routing entry for {mgmt_ip}")
    """
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type == "klish":
        command = f"show ip route {ip_address}"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True)
        return output
    elif cli_type == "click":
        command = f"show ip route {ip_address}"
        output = st.show(dut, command, type=cli_type, skip_tmpl=True)
        return output
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return None


def get_management_ip(dut):
    """
    Get the device's management IP address.

    Author: Shiva
    Source: apis/routing/ip_route_cli.py

    :param dut: Device Under Test
    :return: Management IP address as string, or None if not found

    Example:
        mgmt_ip = get_management_ip(dut)
        if mgmt_ip:
            st.log(f"Management IP: {mgmt_ip}")
    """
    try:
        # Try to get eth0 IP (management interface in SONiC)
        import apis.system.basic as basic_api
        mgmt_ips = basic_api.get_ifconfig_inet(dut, "eth0")
        if mgmt_ips and len(mgmt_ips) > 0:
            st.log(f"Found management IP via eth0: {mgmt_ips[0]}")
            return mgmt_ips[0]

        # Alternative: Try Management0 interface
        command = "show ip interface Management0"
        output = st.show(dut, command, type="klish", skip_tmpl=True, skip_error_check=True)
        output_str = str(output)

        # Parse IP address from output
        import re
        ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)/\d+', output_str)
        if ip_match:
            mgmt_ip = ip_match.group(1)
            st.log(f"Found management IP via Management0: {mgmt_ip}")
            return mgmt_ip

        st.log("Could not determine management IP")
        return None
    except Exception as e:
        st.error(f"Error getting management IP: {str(e)}")
        return None
