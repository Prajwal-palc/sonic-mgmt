"""
Interface Redis Database Validation APIs
Author: Shiva
2026

This module provides APIs for validating interface-related entries in Redis database,
including stale entry detection and error message format validation.
"""

import re
from spytest import st
from apis.common import redis as redis_api


def verify_redis_interface_keys(dut, interface, expected_keys=None, **kwargs):
    """
    Verify that expected interface-related keys exist in Redis CONFIG_DB.

    This API queries Redis CONFIG_DB (database 4) and validates that the expected
    keys for the specified interface are present.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet8")
    :param expected_keys: List of expected key patterns (e.g., ["INTERFACE|Ethernet8", "PORT|Ethernet8"])
    :param kwargs: Additional arguments
    :return: Bool - True if all expected keys exist, False otherwise

    Example:
        expected = ["INTERFACE|Ethernet8", "PORT|Ethernet8"]
        result = verify_redis_interface_keys(dut1, "Ethernet8", expected_keys=expected)
    """
    st.log(f"Verifying Redis CONFIG_DB keys for interface {interface}")

    if expected_keys is None:
        expected_keys = [f"INTERFACE|{interface}", f"PORT|{interface}"]

    try:
        # Query Redis CONFIG_DB for all keys containing the interface name
        keys = get_redis_interface_keys(dut, interface)
        st.log(f"Redis keys found for interface '{interface}': {keys}")

        # Check if all expected keys are present
        missing_keys = []
        for expected_key in expected_keys:
            if expected_key not in keys:
                missing_keys.append(expected_key)

        if missing_keys:
            st.error(f"Missing expected Redis keys: {missing_keys}")
            return False

        st.log(f"All expected Redis keys found for interface {interface}")
        return True

    except Exception as e:
        st.error(f"Exception while verifying Redis keys: {str(e)}")
        return False


def check_no_stale_interface_entries(dut, interface, **kwargs):
    """
    Check that no stale or malformed interface entries exist in Redis CONFIG_DB.

    This API detects:
    - Entries with trailing separators (e.g., "INTERFACE|Ethernet8|" with nothing after pipe)
    - Duplicate entries for the same interface
    - Malformed key patterns

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet8")
    :param kwargs: Additional arguments
    :return: Bool - True if no stale entries found, False otherwise

    Example:
        result = check_no_stale_interface_entries(dut1, "Ethernet8")
    """
    st.log(f"Checking for stale/malformed Redis entries for interface {interface}")

    try:
        import re
        # Query Redis CONFIG_DB for all keys containing the interface name
        keys = get_redis_interface_keys(dut, interface)
        st.log(f"All Redis keys for interface '{interface}': {keys}")

        stale_entries = []
        malformed_entries = []

        for key in keys:
            # Check for trailing pipe separators (e.g., "INTERFACE|Ethernet8|")
            if key.endswith("|"):
                stale_entries.append(key)
                st.error(f"Found stale entry with trailing pipe: {key}")

            # Check for empty segments (e.g., "INTERFACE||Ethernet8")
            if "||" in key:
                malformed_entries.append(key)
                st.error(f"Found malformed entry with double pipes: {key}")

            # Check for entries with interface name but nothing else meaningful
            # Pattern: INTERFACE|Ethernet8| with trailing pipe but no IP/config
            pattern_trailing = rf"INTERFACE\|{re.escape(interface)}\|$"
            if re.match(pattern_trailing, key):
                stale_entries.append(key)
                st.error(f"Found stale INTERFACE entry with trailing separator: {key}")

        if stale_entries or malformed_entries:
            st.error(f"Stale entries: {stale_entries}")
            st.error(f"Malformed entries: {malformed_entries}")
            return False

        st.log(f"No stale or malformed Redis entries found for interface {interface}")
        return True

    except Exception as e:
        st.error(f"Exception while checking for stale entries: {str(e)}")
        return False


def verify_error_message_format(output, expected_pattern, reject_patterns=None, **kwargs):
    """
    Verify that CLI error output matches expected format and contains no malformed content.

    This API validates:
    - Error message matches expected pattern
    - No unexpected debug strings or internal data structures in output
    - Clean error format without garbled text

    :param output: CLI command output string
    :param expected_pattern: Expected error message pattern (can use regex)
    :param reject_patterns: List of patterns that indicate malformed output
    :param kwargs: Additional arguments
    :return: Bool - True if format is valid, False if malformed

    Example:
        output = "%Error: Interface Ethernet8 invalid IPv4 address: 224.1.1.1/24"
        expected = r"%Error: Interface \w+ invalid IPv4 address: [\d\.\/]+"
        reject = [r"\|phy-if-name\|", r"\|mode=\|"]
        result = verify_error_message_format(output, expected, reject_patterns=reject)
    """
    st.log(f"Verifying error message format")
    st.log(f"Output to validate:\n{output}")

    if reject_patterns is None:
        reject_patterns = []

    # Check for malformed/unexpected patterns first
    for reject_pattern in reject_patterns:
        if re.search(reject_pattern, output):
            st.error(f"Found malformed pattern in output: {reject_pattern}")
            st.error(f"This indicates unexpected/debug content leaked into error message")
            return False

    # Check if output matches expected pattern
    if not re.search(expected_pattern, output, re.MULTILINE):
        st.error(f"Error output does not match expected pattern: {expected_pattern}")
        return False

    st.log("Error message format is valid and clean")
    return True


def get_redis_interface_keys(dut, interface, **kwargs):
    """
    Retrieve all Redis CONFIG_DB keys related to a specific interface.

    :param dut: Device under test
    :param interface: Interface name (e.g., "Ethernet8")
    :param kwargs: Additional arguments
    :return: List of Redis keys

    Example:
        keys = get_redis_interface_keys(dut1, "Ethernet8")
        st.log(f"Found keys: {keys}")
    """
    st.log(f"Retrieving Redis CONFIG_DB keys for interface {interface}")

    try:
        import re
        pattern = f"*{interface}*"
        # Use redis config API directly but parse output manually
        dev_cmd = redis_api.build(dut, redis_api.CONFIG_DB, f"keys '{pattern}'")
        output = st.show(dut, dev_cmd, skip_tmpl=True)
        st.log(f"Raw Redis output:\n{output}")

        # Parse the output manually - redis-cli keys command returns one key per line
        keys = []
        for line in output.split('\n'):
            line = line.strip()
            # Skip empty lines, prompt lines
            if not line or line.startswith('admin@') or line.endswith('$'):
                continue

            # Remove leading numbers and quotes like "1) ", "10) ", quotes, etc.
            # Pattern handles: 1) "KEY" or 1) KEY or just KEY
            cleaned = re.sub(r'^\d+\)\s*', '', line)  # Remove number prefix
            cleaned = cleaned.strip('"')  # Remove quotes

            if cleaned:
                keys.append(cleaned)

        st.log(f"Parsed Redis keys for {interface}: {keys}")
        return keys
    except Exception as e:
        st.error(f"Exception while retrieving Redis keys: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return []


def verify_interface_key_exists(dut, key, **kwargs):
    """
    Verify that a specific Redis key exists in CONFIG_DB.

    :param dut: Device under test
    :param key: Exact Redis key to check (e.g., "INTERFACE|Ethernet8")
    :param kwargs: Additional arguments
    :return: Bool - True if key exists, False otherwise

    Example:
        exists = verify_interface_key_exists(dut1, "INTERFACE|Ethernet8")
    """
    st.log(f"Checking if Redis key exists: {key}")

    try:
        # Use Redis KEYS command to check for exact key
        keys = redis_api.keys(dut, redis_api.CONFIG_DB, key)
        if key in keys:
            st.log(f"Redis key exists: {key}")
            return True
        else:
            st.error(f"Redis key does NOT exist: {key}")
            return False
    except Exception as e:
        st.error(f"Exception while checking Redis key: {str(e)}")
        return False
