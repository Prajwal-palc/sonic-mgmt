"""
ACL CLI Validation API Module
Author: Shiva
2026

This module provides APIs for ACL CLI validation, including:
- CLI help string verification
- CLI prompt detection and mode verification
- Mode navigation validation

These APIs are specifically designed for validating IS-CLI (klish) behavior
and ensuring industry-standard CLI patterns.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from spytest import st


def execute_cli_command(dut: str, command: str, cli_type: str = "klish", **kwargs) -> str:
    """
    Execute a CLI command in current mode and return raw output.

    For help commands (?), must use conf=True to stay in config mode.
    The framework auto-exits config mode when conf=False.

    :param dut: Device under test
    :param command: CLI command to execute (e.g., "ip access?")
    :param cli_type: CLI type (default: klish)
    :param kwargs: Additional arguments
    :return: Raw CLI output as string

    Example:
        output = execute_cli_command(dut, "ip access?", cli_type="klish")
    """
    skip_error_check = kwargs.get('skip_error_check', True)

    st.log(f"Executing CLI command: {command}")

    # Use conf=True to stay in config mode (framework won't auto-exit)
    output = st.config(dut, command, type=cli_type, skip_error_check=skip_error_check, conf=True)

    st.log(f"CLI output received (length: {len(str(output))} chars)")
    return output


def verify_cli_help_contains(
    dut: str,
    command: str,
    expected_strings: List[str],
    cli_type: str = "klish",
    **kwargs
) -> tuple[bool, Dict[str, Any]]:
    """
    Verify CLI help output contains expected strings.

    :param dut: Device under test
    :param command: Help command (e.g., "ip access?")
    :param expected_strings: List of strings that should be present
    :param cli_type: CLI type (default: klish)
    :param kwargs: Additional arguments
    :return: (success, details) tuple
        - success: True if all strings found, False otherwise
        - details: Dict with 'found', 'missing', and 'output' keys

    Example:
        success, details = verify_cli_help_contains(
            dut, "ip access?",
            ["access-group", "access-list"],
            cli_type="klish"
        )
    """
    st.log(f"Verifying CLI help command: {command}")
    st.log(f"Expected strings: {expected_strings}")

    output = execute_cli_command(dut, command, cli_type=cli_type, **kwargs)

    found = []
    missing = []

    for expected in expected_strings:
        if expected.lower() in output.lower():
            found.append(expected)
            st.log(f"✓ Found expected string: {expected}")
        else:
            missing.append(expected)
            st.log(f"✗ Missing expected string: {expected}")

    success = len(missing) == 0

    details = {
        "found": found,
        "missing": missing,
        "output": output,
        "total_expected": len(expected_strings),
        "total_found": len(found)
    }

    return success, details


def get_current_cli_prompt(dut: str, cli_type: str = "klish") -> Optional[str]:
    """
    Get the current CLI prompt string.

    This function attempts to detect the current CLI prompt by sending
    a newline and capturing the response.

    :param dut: Device under test
    :param cli_type: CLI type (default: klish)
    :return: Current prompt string or None if detection failed

    Example:
        prompt = get_current_cli_prompt(dut, cli_type="klish")
        # Returns: "sonic(config)#" or "sonic#" or "sonic(config-ipv4-acl)#"
    """
    st.log("Detecting current CLI prompt")

    try:
        # Add small wait for prompt to stabilize after mode changes
        import time
        time.sleep(0.5)

        # Send empty command to get prompt
        output = st.config(dut, "", type=cli_type, skip_error_check=True, conf=False)

        # Extract prompt from output
        # Match any hostname format: sonic#, sonic-mgmt#, smic_sonic1#, etc.
        # Including config modes: (config)#, (config-ipv4-acl)#
        prompt_pattern = r'([a-zA-Z0-9_-]+(?:\([^)]+\))?#)'
        match = re.search(prompt_pattern, output)

        if match:
            prompt = match.group(1)
            st.log(f"Detected prompt: {prompt}")
            return prompt
        else:
            st.warn(f"Could not detect CLI prompt. Output: {output}")
            return None

    except Exception as e:
        st.error(f"Error detecting CLI prompt: {e}")
        return None


def verify_cli_mode(
    dut: str,
    expected_mode: str,
    cli_type: str = "klish",
    **kwargs
) -> bool:
    """
    Verify current CLI mode matches expected mode.

    Modes:
    - "privileged" or "exec": sonic#
    - "config" or "global": sonic(config)#
    - "acl" or "config-ipv4-acl": sonic(config-ipv4-acl)#

    :param dut: Device under test
    :param expected_mode: Expected mode string
    :param cli_type: CLI type (default: klish)
    :param kwargs: Additional arguments
    :return: True if current mode matches expected, False otherwise

    Example:
        if verify_cli_mode(dut, "config", cli_type="klish"):
            st.log("Currently in config mode")
    """
    st.log(f"Verifying CLI mode: {expected_mode}")

    prompt = get_current_cli_prompt(dut, cli_type=cli_type)

    if not prompt:
        st.error("Could not detect current CLI prompt")
        return False

    # Normalize expected mode
    # Updated patterns to match any hostname (sonic, sonic-mgmt, smic_sonic1, etc.)
    mode_patterns = {
        "privileged": r'[a-zA-Z0-9_-]+#$',
        "exec": r'[a-zA-Z0-9_-]+#$',
        "config": r'[a-zA-Z0-9_-]+\(config\)#$',
        "global": r'[a-zA-Z0-9_-]+\(config\)#$',
        "acl": r'[a-zA-Z0-9_-]+\(config-ipv4-acl\)#$',
        "config-ipv4-acl": r'[a-zA-Z0-9_-]+\(config-ipv4-acl\)#$',
    }

    pattern = mode_patterns.get(expected_mode.lower())

    if not pattern:
        # Try direct string match
        if expected_mode in prompt:
            st.log(f"✓ Current mode matches expected: {prompt}")
            return True
        else:
            st.log(f"✗ Current mode does not match. Expected: {expected_mode}, Got: {prompt}")
            return False

    if re.search(pattern, prompt):
        st.log(f"✓ Current mode matches expected: {prompt}")
        return True
    else:
        st.log(f"✗ Current mode does not match. Expected pattern: {pattern}, Got: {prompt}")
        return False


def enter_config_mode(dut: str, cli_type: str = "klish") -> bool:
    """
    Enter global configuration mode.

    Note: This function trusts the SpyTest framework to handle mode changes.
    Manual prompt verification is not needed - the framework tracks prompts internally.

    :param dut: Device under test
    :param cli_type: CLI type (default: klish)
    :return: True (always, as framework handles mode changes)

    Example:
        enter_config_mode(dut, cli_type="klish")
    """
    st.log("Entering global configuration mode")

    cmd = "configure terminal"
    st.config(dut, cmd, type=cli_type, conf=True)

    st.log("Entered configuration mode (framework-managed)")
    return True


def enter_ipv4_acl_mode(dut: str, acl_name: str, cli_type: str = "klish") -> bool:
    """
    Enter IPv4 ACL configuration mode.

    This assumes you are already in global configuration mode.
    Trusts the SpyTest framework to handle mode changes internally.

    :param dut: Device under test
    :param acl_name: Name of the ACL to configure
    :param cli_type: CLI type (default: klish)
    :return: True (always, as framework handles mode changes)

    Example:
        enter_config_mode(dut)
        enter_ipv4_acl_mode(dut, "test", cli_type="klish")
    """
    st.log(f"Entering IPv4 ACL configuration mode: {acl_name}")

    cmd = f"ip access-list {acl_name}"
    st.config(dut, cmd, type=cli_type, conf=True)

    st.log(f"Entered ACL configuration mode for {acl_name} (framework-managed)")
    return True


def exit_current_mode(dut: str, cli_type: str = "klish") -> bool:
    """
    Execute exit command from current mode.

    The framework automatically handles mode transitions. When exiting from
    sub-config modes (like ACL config), the framework transitions to the
    parent config mode (global config), not privileged exec mode.

    :param dut: Device under test
    :param cli_type: CLI type (default: klish)
    :return: True (always, as framework handles mode changes)

    Example:
        exit_current_mode(dut, cli_type="klish")
    """
    st.log("Executing exit command")

    cmd = "exit"

    # Framework handles exit: sub-config -> parent config -> privileged exec
    st.config(dut, cmd, type=cli_type, conf=False, skip_error_check=True)

    st.log("Exit command executed (framework handled mode transition)")
    return True


def delete_ipv4_acl(dut: str, acl_name: str, cli_type: str = "klish", **kwargs) -> bool:
    """
    Remove IPv4 ACL configuration.

    :param dut: Device under test
    :param acl_name: Name of the ACL to remove
    :param cli_type: CLI type (default: klish)
    :param kwargs: Additional arguments
    :return: True if successful, False otherwise

    Example:
        delete_ipv4_acl(dut, "test", cli_type="klish")
    """
    st.log(f"Deleting IPv4 ACL: {acl_name}")

    skip_error_check = kwargs.get('skip_error_check', True)

    # Ensure we're in config mode
    enter_config_mode(dut, cli_type=cli_type)

    cmd = f"""no ip access-list {acl_name}"""

    st.config(dut, cmd, type=cli_type, conf=True, skip_error_check=skip_error_check)

    st.log(f"✓ IPv4 ACL deleted: {acl_name}")
    return True


def verify_acl_exists(dut: str, acl_name: str, cli_type: str = "klish") -> bool:
    """
    Verify if an IPv4 ACL exists in configuration.

    :param dut: Device under test
    :param acl_name: Name of the ACL to check
    :param cli_type: CLI type (default: klish)
    :return: True if ACL exists, False otherwise

    Example:
        if verify_acl_exists(dut, "test", cli_type="klish"):
            st.log("ACL exists")
    """
    st.log(f"Verifying ACL exists: {acl_name}")

    if cli_type == "klish":
        cmd = "show running-configuration | grep access-list"
    else:
        cmd = "show acl table"

    output = st.show(dut, cmd, type=cli_type, skip_error_check=True)

    if acl_name in output:
        st.log(f"✓ ACL found: {acl_name}")
        return True
    else:
        st.log(f"✗ ACL not found: {acl_name}")
        return False


def verify_acl_rule_protocol_options(
    dut: str,
    acl_name: str,
    seq_number: int,
    action: str,
    expected_protocols: List[str],
    cli_type: str = "klish",
    **kwargs
) -> tuple[bool, Dict[str, Any]]:
    """
    Verify ACL rule protocol help output contains expected protocol options.

    This function enters ACL configuration mode, executes a partial ACL rule
    command followed by '?', and verifies the help output contains all expected
    protocol options (icmp, ip, tcp, udp, <0..255>).

    :param dut: Device under test
    :param acl_name: Name of the ACL
    :param seq_number: Sequence number for the rule
    :param action: Action (permit/deny)
    :param expected_protocols: List of expected protocol strings in help output
    :param cli_type: CLI type (default: klish)
    :param kwargs: Additional arguments
    :return: (success, details) tuple
        - success: True if all protocol options found, False otherwise
        - details: Dict with 'found', 'missing', and 'output' keys

    Example:
        success, details = verify_acl_rule_protocol_options(
            dut, "test_acl", 1, "permit",
            ["icmp", "ip", "tcp", "udp", "<0..255>"],
            cli_type="klish"
        )
    """
    st.log(f"Verifying ACL rule protocol options for: {acl_name} seq {seq_number} {action}")
    st.log(f"Expected protocol options: {expected_protocols}")

    # Enter ACL configuration mode
    enter_ipv4_acl_mode(dut, acl_name, cli_type=cli_type)

    # Execute partial command with '?' to get help
    help_cmd = f"seq {seq_number} {action} ?"

    st.log(f"Executing help command: {help_cmd}")
    output = execute_cli_command(dut, help_cmd, cli_type=cli_type, **kwargs)

    # Verify expected protocol options
    found = []
    missing = []

    for protocol in expected_protocols:
        if protocol.lower() in output.lower():
            found.append(protocol)
            st.log(f"✓ Found protocol option: {protocol}")
        else:
            missing.append(protocol)
            st.log(f"✗ Missing protocol option: {protocol}")

    success = len(missing) == 0

    details = {
        "found": found,
        "missing": missing,
        "output": output,
        "total_expected": len(expected_protocols),
        "total_found": len(found)
    }

    # Exit ACL config mode back to global config
    exit_current_mode(dut, cli_type=cli_type)

    return success, details
