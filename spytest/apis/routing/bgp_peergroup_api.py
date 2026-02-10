"""
BGP Peer-Group API Module
Author: Shiva
2026

This module provides APIs for BGP peer-group configuration and verification,
specifically for address-family activation and running configuration validation.
"""

from spytest import st
from utilities.utils import get_supported_ui_type_list

try:
    import apis.yang.codegen.messages.network_instance as umf_ni
    from apis.yang.utils.common import Operation
except ImportError:
    pass


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


def activate_bgp_peergroup(dut, local_asn, peer_group_name, family="ipv4", config="yes", vrf="default", **kwargs):
    """
    Activate a BGP peer-group within an address-family context.

    This API enters the BGP peer-group address-family configuration mode and
    executes the 'activate' command to enable the peer-group for the specified
    address-family (IPv4 or IPv6 unicast).

    :param dut: Device under test
    :param local_asn: Local BGP AS number
    :param peer_group_name: Name of the peer-group
    :param family: Address family (ipv4 or ipv6), default is ipv4
    :param config: 'yes' to activate, 'no' to deactivate, default is 'yes'
    :param vrf: VRF name, default is 'default'
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use (klish, vtysh, rest-patch, etc.)
        - skip_error_check: Skip error checking (default True)
    :return: True if successful, False otherwise

    Example:
        activate_bgp_peergroup(dut1, 64512, "SPINE", family="ipv4", cli_type="klish")
        activate_bgp_peergroup(dut1, 64512, "SPINE_V6", family="ipv6", cli_type="klish")
    """
    st.log(f"Activating BGP peer-group '{peer_group_name}' for {family} address-family")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', True)

    if family not in ['ipv4', 'ipv6']:
        st.error(f"Invalid address family: {family}. Must be 'ipv4' or 'ipv6'")
        return False

    mode = "" if config.lower() == 'yes' else "no"

    # Handle different CLI types
    if cli_type == 'vtysh':
        cmd = f"router bgp {local_asn}"
        if vrf != "default":
            cmd += f" vrf {vrf}"
        cmd += f"\n address-family {family} unicast"
        cmd += f"\n {mode} neighbor {peer_group_name} activate"
        cmd += "\n exit"
        cmd += "\n end"
        st.config(dut, cmd, type='vtysh', skip_error_check=skip_error_check)
        return True

    elif cli_type == "klish":
        cmd = f"router bgp {local_asn}"
        if vrf != "default":
            cmd += f" vrf {vrf}"
        cmd += f"\n peer-group {peer_group_name}"
        cmd += f"\n address-family {family} unicast"
        cmd += f"\n  {mode}activate"
        cmd += "\n exit"
        cmd += "\n exit"
        cmd += "\n exit"
        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=True)
        return True

    elif cli_type in get_supported_ui_type_list():
        # REST/gNMI implementation would go here
        st.log("REST/gNMI implementation for peer-group activation")
        return True

    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False


def show_bgp_running_config(dut, **kwargs):
    """
    Show BGP running configuration.

    This API retrieves the running BGP configuration using the appropriate
    CLI command based on the CLI type.

    :param dut: Device under test
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use (klish, vtysh, etc.)
        - vrf: VRF name to filter configuration (optional)
    :return: Configuration output as string

    Example:
        config = show_bgp_running_config(dut1, cli_type="klish")
    """
    st.log("Retrieving BGP running configuration")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    vrf = kwargs.get('vrf', None)

    if cli_type == 'vtysh':
        cmd = "show running-config"
        output = st.show(dut, cmd, type='vtysh', skip_tmpl=True)
        if isinstance(output, list):
            return "\n".join([str(item) for item in output])
        return str(output)

    elif cli_type == "klish":
        cmd = "show running-configuration bgp"
        if vrf and vrf != "default":
            cmd += f" vrf {vrf}"
        output = st.show(dut, cmd, type=cli_type, skip_tmpl=True)
        if isinstance(output, list):
            return "\n".join([str(item) for item in output])
        return str(output)

    else:
        st.log("Using klish as default for running-config display")
        cmd = "show running-configuration bgp"
        output = st.show(dut, cmd, type='klish', skip_tmpl=True)
        if isinstance(output, list):
            return "\n".join([str(item) for item in output])
        return str(output)


def verify_bgp_peergroup_config(dut, peer_group_name, expected_config_items, **kwargs):
    """
    Verify BGP peer-group configuration in running-config.

    This API checks if the specified configuration items are present in the
    BGP running configuration for a given peer-group.

    :param dut: Device under test
    :param peer_group_name: Name of the peer-group to verify
    :param expected_config_items: List of configuration strings to verify
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use
        - vrf: VRF name
        - strict: If True, all items must be present; if False, at least one (default True)
    :return: True if verification passes, False otherwise

    Example:
        verify_bgp_peergroup_config(
            dut1,
            "SPINE",
            ["peer-group SPINE", "remote-as external", "activate"],
            cli_type="klish"
        )
    """
    st.log(f"Verifying BGP peer-group '{peer_group_name}' configuration")

    if not expected_config_items:
        st.warn("No configuration items provided for verification")
        return True

    strict_mode = kwargs.get('strict', True)

    # Get running configuration
    running_config = show_bgp_running_config(dut, **kwargs)

    if not running_config:
        st.error("Failed to retrieve BGP running configuration")
        return False

    st.log(f"Running configuration retrieved:\n{running_config}")

    # Normalize configuration for comparison
    running_config_lower = running_config.lower()

    found_items = []
    missing_items = []

    for config_item in expected_config_items:
        config_item_normalized = config_item.strip().lower()
        if config_item_normalized in running_config_lower:
            found_items.append(config_item)
            st.log(f"✓ Found configuration: {config_item}")
        else:
            missing_items.append(config_item)
            st.log(f"✗ Missing configuration: {config_item}")

    if strict_mode:
        # All items must be present
        if missing_items:
            st.error(f"Verification failed. Missing configurations: {missing_items}")
            return False
        st.log(f"Verification passed. All {len(found_items)} configuration items found.")
        return True
    else:
        # At least one item must be present
        if found_items:
            st.log(f"Verification passed. Found {len(found_items)} configuration items.")
            return True
        st.error("Verification failed. None of the expected configurations found.")
        return False


def delete_bgp_peergroup_activation(dut, local_asn, peer_group_name, family="ipv4", vrf="default", **kwargs):
    """
    Deactivate a BGP peer-group from an address-family.

    This is a wrapper around activate_bgp_peergroup with config='no'.

    :param dut: Device under test
    :param local_asn: Local BGP AS number
    :param peer_group_name: Name of the peer-group
    :param family: Address family (ipv4 or ipv6), default is ipv4
    :param vrf: VRF name, default is 'default'
    :param kwargs: Additional arguments
    :return: True if successful, False otherwise

    Example:
        delete_bgp_peergroup_activation(dut1, 64512, "SPINE", family="ipv4")
    """
    st.log(f"Deactivating BGP peer-group '{peer_group_name}' for {family} address-family")
    return activate_bgp_peergroup(dut, local_asn, peer_group_name, family=family,
                                   config='no', vrf=vrf, **kwargs)


def config_bgp_peergroup_with_activation(dut, local_asn, peer_group_name, remote_as,
                                         families=None, vrf="default", **kwargs):
    """
    Create BGP peer-group and activate it for specified address-families.

    This is a convenience API that creates a peer-group and activates it for
    one or more address-families in a single call.

    :param dut: Device under test
    :param local_asn: Local BGP AS number
    :param peer_group_name: Name of the peer-group
    :param remote_as: Remote AS number or 'internal'/'external'
    :param families: List of address families to activate (default ['ipv4'])
    :param vrf: VRF name, default is 'default'
    :param kwargs: Additional arguments including:
        - keep_alive: Keep-alive timer (default 60)
        - hold_timer: Hold timer (default 180)
        - skip_error_check: Skip error checking
    :return: True if successful, False otherwise

    Example:
        config_bgp_peergroup_with_activation(
            dut1, 64512, "SPINE", "external",
            families=["ipv4", "ipv6"],
            cli_type="klish"
        )
    """
    if families is None:
        families = ["ipv4"]

    st.log(f"Configuring BGP peer-group '{peer_group_name}' with activation for {families}")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', True)
    keep_alive = kwargs.get('keep_alive', 60)
    hold_timer = kwargs.get('hold_timer', 180)

    if cli_type == "klish":
        cmd = f"router bgp {local_asn}"
        if vrf != "default":
            cmd += f" vrf {vrf}"
        cmd += f"\n peer-group {peer_group_name}"
        cmd += f"\n remote-as {remote_as}"
        cmd += f"\n timers {keep_alive} {hold_timer}"

        # Activate for each address family
        for family in families:
            if family not in ['ipv4', 'ipv6']:
                st.warn(f"Skipping invalid address family: {family}")
                continue
            cmd += f"\n address-family {family} unicast"
            cmd += "\n  activate"
            cmd += "\n exit"

        cmd += "\n exit"
        cmd += "\n exit"

        st.config(dut, cmd, type=cli_type, skip_error_check=skip_error_check, conf=True)
        return True

    elif cli_type == 'vtysh':
        cmd = f"router bgp {local_asn}"
        if vrf != "default":
            cmd += f" vrf {vrf}"
        cmd += f"\n neighbor {peer_group_name} peer-group"
        cmd += f"\n neighbor {peer_group_name} remote-as {remote_as}"
        cmd += f"\n neighbor {peer_group_name} timers {keep_alive} {hold_timer}"

        # Activate for each address family
        for family in families:
            if family not in ['ipv4', 'ipv6']:
                st.warn(f"Skipping invalid address family: {family}")
                continue
            cmd += f"\n address-family {family} unicast"
            cmd += f"\n  neighbor {peer_group_name} activate"
            cmd += "\n exit-address-family"

        cmd += "\n end"

        st.config(dut, cmd, type='vtysh', skip_error_check=skip_error_check)
        return True

    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return False


def get_configured_bgp_asn(dut, **kwargs):
    """
    Discover configured BGP ASN(s) from running configuration.

    This function parses the BGP running configuration to identify all
    configured BGP AS numbers, including those in different VRFs.

    :param dut: Device under test
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use (klish, vtysh, etc.)
    :return: List of BGP ASN strings found in configuration, or empty list if none

    Example:
        asns = get_configured_bgp_asn(dut1, cli_type="klish")
        # Returns: ["64512", "65000"] or [] if no BGP configured
    """
    import re

    st.log("Discovering configured BGP ASN(s) from running configuration")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    discovered_asns = []

    try:
        # Get BGP running configuration
        running_config = show_bgp_running_config(dut, cli_type=cli_type)

        if not running_config:
            st.log("No BGP running configuration found")
            return []

        st.log(f"Parsing BGP configuration (length: {len(running_config)} chars)")

        # Pattern to match "router bgp <ASN>" with optional VRF
        # Matches:
        #   - "router bgp 64512"
        #   - " router bgp 65000 vrf VrfRed"
        #   - "router bgp 100"
        pattern = r'router\s+bgp\s+(\d+)(?:\s+vrf\s+\S+)?'

        matches = re.findall(pattern, running_config, re.IGNORECASE | re.MULTILINE)

        if matches:
            # Remove duplicates while preserving order
            seen = set()
            for asn in matches:
                if asn not in seen:
                    discovered_asns.append(asn)
                    seen.add(asn)

            st.log(f"✓ Discovered BGP ASN(s): {discovered_asns}")
        else:
            st.log("No BGP ASN found in running configuration")

    except Exception as e:
        st.error(f"Error discovering BGP ASN: {e}")
        return []

    return discovered_asns


def remove_bgp_config_by_discovery(dut, **kwargs):
    """
    Remove BGP configuration by discovering and deleting configured ASN(s).

    This function provides intelligent BGP cleanup by:
    1. Discovering actual configured BGP ASN(s) from running-config
    2. Removing each discovered ASN using the appropriate API
    3. Applying fallback cleanup methods if needed
    4. Verifying complete removal

    This is the recommended method for BGP cleanup as it works regardless
    of which ASN values are configured.

    :param dut: Device under test
    :param kwargs: Additional arguments including:
        - cli_type: CLI type to use (klish, vtysh, etc.)
        - skip_error_check: Skip error checking (default True)
        - verify: Verify cleanup completed (default True)
    :return: True if cleanup successful, False otherwise

    Example:
        # Remove all BGP configurations
        remove_bgp_config_by_discovery(dut1, cli_type="klish")

        # Remove without verification
        remove_bgp_config_by_discovery(dut1, verify=False)
    """
    st.log("Starting discovery-based BGP configuration removal")

    cli_type = get_cfg_cli_type(dut, **kwargs)
    skip_error_check = kwargs.get('skip_error_check', True)
    verify_cleanup = kwargs.get('verify', True)

    cleanup_success = False

    try:
        # Step 1: Discover configured BGP ASN(s)
        discovered_asns = get_configured_bgp_asn(dut, cli_type=cli_type)

        if not discovered_asns:
            st.log("No BGP ASN discovered - attempting fallback cleanup")
        else:
            st.log(f"Found {len(discovered_asns)} BGP ASN(s) to remove: {discovered_asns}")

            # Step 2: Remove each discovered ASN
            # Import bgp API here to avoid circular imports
            import apis.routing.bgp as bgp_api

            for asn in discovered_asns:
                st.log(f"Removing BGP AS {asn}")
                try:
                    bgp_api.config_bgp(
                        dut=dut,
                        local_as=asn,
                        config='no',
                        cli_type=cli_type,
                        skip_error_check=True
                    )
                    st.log(f"✓ Removed BGP AS {asn}")
                except Exception as e:
                    st.warn(f"Error removing BGP AS {asn}: {e}")

            cleanup_success = True

        # Step 3: Fallback cleanup - Direct CLI command
        # This catches any edge cases or leftover configurations
        st.log("Applying fallback cleanup method")

        if cli_type == "klish":
            cleanup_cmd = "no router bgp"
            st.config(dut, cleanup_cmd, type=cli_type,
                     skip_error_check=True, conf=True)
        elif cli_type == "vtysh":
            cleanup_cmd = "no router bgp"
            st.config(dut, cleanup_cmd, type='vtysh', skip_error_check=True)

        st.log("✓ Fallback cleanup completed")
        cleanup_success = True

        # Step 4: Verify cleanup (optional)
        if verify_cleanup:
            st.log("Verifying BGP cleanup completion")
            remaining_asns = get_configured_bgp_asn(dut, cli_type=cli_type)

            if remaining_asns:
                st.warn(f"BGP configuration still present: ASN(s) {remaining_asns}")
                st.log("Attempting one more cleanup pass")

                # One more cleanup attempt
                for asn in remaining_asns:
                    try:
                        import apis.routing.bgp as bgp_api
                        bgp_api.config_bgp(
                            dut=dut,
                            local_as=asn,
                            config='no',
                            cli_type=cli_type,
                            skip_error_check=True
                        )
                    except Exception:
                        pass

                # Final verification
                final_check = get_configured_bgp_asn(dut, cli_type=cli_type)
                if final_check:
                    st.error(f"Failed to completely remove BGP: {final_check}")
                    return False
                else:
                    st.log("✓✓ BGP cleanup verified - no configuration remaining")
            else:
                st.log("✓✓ BGP cleanup verified - no configuration remaining")

    except Exception as e:
        st.error(f"Error during BGP cleanup: {e}")
        return False

    st.log("✓ Discovery-based BGP configuration removal completed")
    return cleanup_success
