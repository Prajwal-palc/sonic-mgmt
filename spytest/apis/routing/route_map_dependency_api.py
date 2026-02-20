"""
Route-Map Dependency Validation API Module
Author: ShivaKumar.M
2026

This module provides APIs for route-map dependency validation and management:
- Delete route-map with dependency checking
- Verify error messages when deleting in-use route-maps
- BGP neighbor route-map configuration and validation
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


def delete_route_map(dut, route_map_name, **kwargs):
    """
    Delete a route-map globally.

    This API attempts to delete a route-map. If the route-map is in use,
    the deletion will fail with an error message indicating dependencies.

    :param dut: Device under test
    :param route_map_name: Name of the route-map to delete
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use (klish, vtysh, etc.)
        - skip_error_check: Skip error checking (default False to catch errors)
    :return: Tuple (success: bool, output: str)

    Example:
        success, output = delete_route_map(dut1, "asdf", cli_type="klish")
        if not success and "in use" in output:
            st.log("Route-map is in use, cannot delete")
    """
    st.log(f"Attempting to delete route-map '{route_map_name}'")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', False)

    if cli_type == "klish":
        # Add exit to return to config mode after deletion
        cmd = f"no route-map {route_map_name}\nexit"
        output = st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=True)
    elif cli_type == "vtysh":
        cmd = f"no route-map {route_map_name}"
        output = st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check)
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False, ""

    # Check if output contains error messages
    output_str = str(output) if output else ""

    # Check for common error patterns
    error_patterns = [
        r'%Error',
        r'ERROR',
        r'in use',
        r'Cannot delete',
        r'failed',
    ]

    has_error = False
    for pattern in error_patterns:
        if re.search(pattern, output_str, re.IGNORECASE):
            has_error = True
            break

    if has_error:
        st.log(f"Route-map deletion failed with error: {output_str}")
        return False, output_str
    else:
        st.log(f"Route-map '{route_map_name}' deleted successfully")
        return True, output_str


def verify_route_map_delete_error(dut, route_map_name, expected_error_contains, **kwargs):
    """
    Verify that deleting a route-map produces expected error message.

    This API attempts to delete a route-map and verifies that the error
    message contains expected text (e.g., dependency information).

    :param dut: Device under test
    :param route_map_name: Name of the route-map to delete
    :param expected_error_contains: List of strings that should appear in error message
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
    :return: Tuple (success: bool, details: dict)

    Example:
        success, details = verify_route_map_delete_error(
            dut1, "asdf",
            ["Cannot delete", "in use", "BGP neighbor 10.1.2.5"],
            cli_type="klish"
        )
        if success:
            st.log("Got expected error message")
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)

    st.log(f"Verifying route-map delete error for '{route_map_name}'")

    # Attempt to delete the route-map (expect failure)
    success, output = delete_route_map(
        dut, route_map_name, cli_type=cli_type, skip_error_check=True
    )

    details = {
        "route_map": route_map_name,
        "expected_strings": expected_error_contains,
        "output": output,
        "found_strings": [],
        "missing_strings": []
    }

    # If deletion succeeded when it should have failed
    if success:
        st.error(f"Route-map '{route_map_name}' was deleted (expected to fail)")
        details["error"] = "Deletion succeeded when failure was expected"
        return False, details

    # Verify expected error strings are present
    for expected_str in expected_error_contains:
        if expected_str in output:
            details["found_strings"].append(expected_str)
            st.log(f"Found expected string: '{expected_str}'")
        else:
            details["missing_strings"].append(expected_str)
            st.warn(f"Missing expected string: '{expected_str}'")

    # Check if all expected strings were found
    if details["missing_strings"]:
        st.error(f"Missing expected error strings: {details['missing_strings']}")
        return False, details
    else:
        st.log(f"All expected error strings found in output")
        return True, details


def delete_bgp_router(dut, local_asn=None, vrf="default", **kwargs):
    """
    Delete BGP router configuration globally.

    This API removes the entire BGP router configuration. If local_asn is not
    provided, it attempts to remove BGP without specifying AS number (cleanup mode).

    :param dut: Device under test
    :param local_asn: Local BGP AS number (optional for cleanup)
    :param vrf: VRF name (default: "default")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - skip_error_check: Skip error checking (default True)
    :return: True if successful, False otherwise

    Example:
        delete_bgp_router(dut1, 65001, cli_type="klish")
        delete_bgp_router(dut1, cli_type="klish")  # Cleanup mode
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', True)

    if local_asn:
        st.log(f"Deleting BGP router AS {local_asn} (VRF: {vrf})")
    else:
        st.log(f"Deleting BGP router configuration (cleanup mode)")

    if cli_type == "klish":
        if local_asn:
            if vrf != "default":
                cmd = f"no router bgp {local_asn} vrf {vrf}\nexit"
            else:
                cmd = f"no router bgp {local_asn}\nexit"
        else:
            # Cleanup mode - try to remove BGP without AS number
            cmd = "no router bgp\nexit"

        st.config(dut, cmd, type=cli_type, skip_error_check=True, conf=True)
    elif cli_type == "vtysh":
        if local_asn:
            if vrf != "default":
                cmd = f"no router bgp {local_asn} vrf {vrf}"
            else:
                cmd = f"no router bgp {local_asn}"
        else:
            # Cleanup mode
            cmd = "no router bgp"

        st.config(dut, cmd, type=cli_type, skip_error_check=True)
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False

    st.log(f"BGP router deletion attempted")
    return True


def config_bgp_router(dut, local_asn, neighbor_ip, remote_asn, vrf="default", **kwargs):
    """
    Configure basic BGP router with a single neighbor.

    This API creates a BGP router instance and configures a neighbor with
    address family activation. Simplified version without extra options.

    :param dut: Device under test
    :param local_asn: Local BGP AS number
    :param neighbor_ip: BGP neighbor IP address
    :param remote_asn: Remote BGP AS number
    :param vrf: VRF name (default: "default")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - skip_error_check: Skip error checking (default False)
    :return: True if successful, False otherwise

    Example:
        config_bgp_router(dut1, 65001, "10.1.2.5", 65001, cli_type="klish")
    """
    st.log(f"Configuring BGP AS {local_asn} with neighbor {neighbor_ip} (remote AS {remote_asn})")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', False)

    if cli_type == "klish":
        cmd = f"router bgp {local_asn}\n"
        cmd += f"neighbor {neighbor_ip} remote-as {remote_asn}\n"
        cmd += "address-family ipv4 unicast\n"
        cmd += "activate\n"
        cmd += "exit\nexit\nexit"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=True)

    elif cli_type == "vtysh":
        cmd = f"router bgp {local_asn}\n"
        cmd += f"neighbor {neighbor_ip} remote-as {remote_asn}\n"
        cmd += "address-family ipv4 unicast\n"
        cmd += f"neighbor {neighbor_ip} activate\n"
        cmd += "exit\nexit"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check)

    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False

    st.log(f"BGP router configured successfully")
    return True


def config_bgp_neighbor_route_map(dut, local_asn, neighbor_ip, route_map_name,
                                   direction="in", family="ipv4", config="add",
                                   vrf="default", **kwargs):
    """
    Configure or remove route-map on a BGP neighbor for a specific direction.

    This API applies or removes a route-map to/from a BGP neighbor in the
    specified direction (in/out) within an address family.

    :param dut: Device under test
    :param local_asn: Local BGP AS number
    :param neighbor_ip: BGP neighbor IP address
    :param route_map_name: Name of the route-map to apply
    :param direction: Direction - "in" or "out" (default: "in")
    :param family: Address family - "ipv4" or "ipv6" (default: "ipv4")
    :param config: "add" to apply, "remove" to delete (default: "add")
    :param vrf: VRF name (default: "default")
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - skip_error_check: Skip error checking (default False)
    :return: True if successful, False otherwise

    Example:
        # Apply route-map inbound
        config_bgp_neighbor_route_map(
            dut1, 65001, "10.1.2.5", "asdf", direction="in", cli_type="klish"
        )

        # Apply route-map outbound
        config_bgp_neighbor_route_map(
            dut1, 65001, "10.1.2.5", "asdf", direction="out", cli_type="klish"
        )

        # Remove route-map
        config_bgp_neighbor_route_map(
            dut1, 65001, "10.1.2.5", "asdf", direction="in",
            config="remove", cli_type="klish"
        )
    """
    st.log(f"{'Applying' if config == 'add' else 'Removing'} route-map '{route_map_name}' "
           f"{direction} on neighbor {neighbor_ip}")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', False)

    # Build command based on CLI type
    if cli_type == "klish":
        cmd = f"router bgp {local_asn}\n"
        cmd += f"neighbor {neighbor_ip}\n"
        cmd += "address-family ipv4 unicast\n"

        # Apply or remove route-map
        if config == "add":
            cmd += f"route-map {route_map_name} {direction}\n"
        else:
            cmd += f"no route-map {route_map_name} {direction}\n"

        # Exit all modes
        cmd += "exit\nexit\nexit\nexit"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=True)

    elif cli_type == "vtysh":
        cmd = f"router bgp {local_asn}\n"
        cmd += "address-family ipv4 unicast\n"

        # Apply or remove route-map
        if config == "add":
            cmd += f"neighbor {neighbor_ip} route-map {route_map_name} {direction}\n"
        else:
            cmd += f"no neighbor {neighbor_ip} route-map {route_map_name} {direction}\n"

        cmd += "exit\nexit"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check)

    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False

    st.log(f"Route-map '{route_map_name}' {'applied' if config == 'add' else 'removed'}")
    return True


def create_route_map_with_sets(dut, route_map_name, sequence, action="permit",
                                as_path_prepend=None, community=None,
                                local_preference=None, **kwargs):
    """
    Create a route-map with set statements using direct CLI commands.

    This is a simplified wrapper to create route-maps with common set statements
    without using the RouteMap class, ensuring proper CLI syntax for klish.

    :param dut: Device under test
    :param route_map_name: Name of the route-map
    :param sequence: Sequence number
    :param action: "permit" or "deny" (default: "permit")
    :param as_path_prepend: Comma-separated AS path list (e.g., "1,2,3,4")
    :param community: Community value (e.g., "11:22")
    :param local_preference: Local preference value (e.g., "567")
    :param kwargs: Additional arguments including cli_type
    :return: True if successful, False otherwise

    Example:
        create_route_map_with_sets(
            dut1, "asdf", "10", action="permit",
            as_path_prepend="1,2,3,4",
            community="11:22",
            local_preference="567",
            cli_type="klish"
        )
    """
    st.log(f"Creating route-map '{route_map_name}' sequence {sequence} {action}")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', False)

    # Build command
    cmd = f"route-map {route_map_name} {action} {sequence}\n"

    if as_path_prepend:
        # For klish, use comma-separated without spaces
        cmd += f"set as-path prepend {as_path_prepend}\n"
        st.log(f"Adding AS-path prepend: {as_path_prepend}")

    if community:
        cmd += f"set community {community}\n"
        st.log(f"Adding community: {community}")

    if local_preference:
        cmd += f"set local-preference {local_preference}\n"
        st.log(f"Adding local-preference: {local_preference}")

    # Exit route-map mode
    cmd += "exit\nexit"

    if cli_type == "klish":
        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=True)
    elif cli_type == "vtysh":
        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check)
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False

    st.log(f"Route-map '{route_map_name}' created successfully")
    return True


def verify_route_map_not_deleted(dut, route_map_name, **kwargs):
    """
    Verify that a route-map still exists after failed deletion attempt.

    This API checks the running configuration to ensure the route-map
    still exists (useful after dependency-blocked deletion).

    :param dut: Device under test
    :param route_map_name: Name of the route-map to verify
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
    :return: True if route-map exists, False otherwise

    Example:
        if verify_route_map_not_deleted(dut1, "asdf"):
            st.log("Route-map still exists (as expected)")
    """
    cli_type = get_cfg_cli_type(dut, **kwargs)

    st.log(f"Verifying route-map '{route_map_name}' still exists")

    # Show running configuration for route-map
    if cli_type == "klish":
        cmd = f"show running-configuration route-map {route_map_name}"
    elif cli_type == "vtysh":
        cmd = f"show running-config | section route-map {route_map_name}"
    else:
        cmd = f"show running-configuration route-map {route_map_name}"

    try:
        output = st.show(dut, cmd, type=cli_type, skip_tmpl=True)

        if not output:
            st.error(f"Route-map '{route_map_name}' does not exist")
            return False

        output_str = str(output) if not isinstance(output, str) else output

        # Check if route-map name appears in output
        if route_map_name in output_str:
            st.log(f"Route-map '{route_map_name}' exists")
            return True
        else:
            st.error(f"Route-map '{route_map_name}' not found in output")
            return False

    except Exception as e:
        st.error(f"Error verifying route-map: {e}")
        return False
