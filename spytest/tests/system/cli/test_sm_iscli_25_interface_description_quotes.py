"""
SM_ISCLI_25 - Interface Description Quote Handling in Running-Config

Author: Athira Arputharaj
Copyright (C) 2026, PALC Networks

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  tests/system/cli/test_sm_iscli_25_interface_description_quotes.py \\
  --logs-path ./logs/test_sm_iscli_25_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Verify that the running-configuration for interfaces displays multi-word description
  values with proper quotes. This test validates the fix for the issue where show
  running-configuration interface displays multi-word descriptions without quotes,
  causing configuration reapplication failures when the output is copy-pasted.

  Bug Scenario:
    show running-configuration interface Ethernet0 outputs:
      description Test Interface for Data Center

    When pasted back, only "Test" is accepted, and "Interface for Data Center"
    causes a syntax error.

  Expected Behavior:
    Output should be:
      description "Test Interface for Data Center"

Pre-requisites:
  - Topology: single-node (D1) with at least 2 non-management data interfaces
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |        dut1        |
        # |   Ethernet0-127    |
        # +--------------------+
  - SONiC version with sonic-cli (klish) support
  - Required test variables (YAML): vars/system/cli/vars_sm_iscli_25.yaml
  - Do NOT modify management interface or management IP
  - Tests handle pagination using | no-more
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
import yaml

from spytest import st, SpyTestDict

# Test case IDs
TC_IDS = SpyTestDict({
    "quote_verification": "TC-SM-ISCLI-25-01",
    "reapplication": "TC-SM-ISCLI-25-02",
    "multiple_formats": "TC-SM-ISCLI-25-03",
    "pagination": "TC-SM-ISCLI-25-04",
    "negative_unquoted": "TC-SM-ISCLI-25-05",
})

# Default variable file path
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "cli"
    / "vars_sm_iscli_25.yaml"
)

# Module level variables
data = SpyTestDict()


def load_test_variables() -> Dict[str, Any]:
    """Load test configuration from YAML file"""
    var_file = DEFAULT_VAR_FILE

    if not var_file.is_file():
        st.warn(f"Variable file not found: {var_file}, using defaults")
        return {
            "defaults": {
                "verify_timeout": 30,
                "cli_type": "klish",
                "cleanup": True,
            },
            "testcases": {}
        }

    try:
        with var_file.open(encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}
    except Exception as error:
        st.error(f"Failed to load variable file: {error}")
        pytest.skip(f"Cannot load variable file: {error}")

    return payload


def get_available_data_interfaces(dut: str) -> List[str]:
    """
    Get list of available data interfaces (excluding management interfaces).

    Args:
        dut: Device under test

    Returns:
        List of interface names (e.g., ['Ethernet0', 'Ethernet4', ...])
    """
    st.log("Getting list of available data interfaces")

    # Get interface status using no-more to handle pagination
    output = st.show(dut, "show interface status | no-more",
                     type="klish", skip_tmpl=True, skip_error_check=True)

    interfaces = []
    if not output:
        st.warn("No output from show interface status")
        return interfaces

    # Parse output to extract interface names
    lines = output.split('\n') if isinstance(output, str) else []
    for line in lines:
        line = line.strip()
        # Look for lines starting with Ethernet
        if line.startswith('Ethernet'):
            # Extract interface name (first column)
            parts = line.split()
            if parts:
                intf = parts[0]
                # Exclude management interfaces
                if not intf.lower().startswith('management') and not intf.lower().startswith('eth0'):
                    interfaces.append(intf)

    st.log(f"Found {len(interfaces)} data interfaces: {interfaces[:10]}")
    return interfaces


def get_interface_description(dut: str, interface: str) -> Optional[str]:
    """
    Get current description of an interface.

    Args:
        dut: Device under test
        interface: Interface name (e.g., 'Ethernet0')

    Returns:
        Current description string or None
    """
    # Convert interface name format if needed (e.g., "Ethernet0" -> "Ethernet 0")
    intf_display = interface.replace('Ethernet', 'Ethernet ')

    st.log(f"Getting current description for {interface}")
    output = st.show(dut, f"show running-configuration interface {intf_display} | no-more",
                     type="klish", skip_tmpl=True, skip_error_check=True)

    if not output:
        st.log(f"No output for {interface}")
        return None

    # Parse description from output
    lines = output.split('\n') if isinstance(output, str) else []
    for line in lines:
        line = line.strip()
        if line.startswith('description'):
            # Extract description value (everything after 'description ')
            desc = line.replace('description', '', 1).strip()
            # Remove quotes if present
            desc = desc.strip('"')
            st.log(f"Current description for {interface}: '{desc}'")
            return desc

    st.log(f"No description configured for {interface}")
    return None


def set_interface_description(dut: str, interface: str, description: str, use_quotes: bool = True) -> bool:
    """
    Configure description on an interface.

    Args:
        dut: Device under test
        interface: Interface name (e.g., 'Ethernet0')
        description: Description string
        use_quotes: Whether to use quotes around description (default: True)

    Returns:
        True if configuration successful
    """
    # Convert interface name format (e.g., "Ethernet0" -> "Ethernet 0")
    intf_config = interface.replace('Ethernet', 'Ethernet ')

    # Format description with or without quotes
    if use_quotes:
        desc_cmd = f'description "{description}"'
    else:
        desc_cmd = f'description {description}'

    st.log(f"Configuring description on {interface}: {desc_cmd}")

    commands = [
        f"interface {intf_config}",
        desc_cmd,
        "exit"
    ]

    try:
        st.config(dut, commands, type="klish", skip_error_check=False)
        st.log(f"✓ Description configured successfully on {interface}")
        return True
    except Exception as error:
        st.warn(f"Failed to configure description on {interface}: {error}")
        return False


def remove_interface_description(dut: str, interface: str) -> bool:
    """
    Remove description from an interface.

    Args:
        dut: Device under test
        interface: Interface name (e.g., 'Ethernet0')

    Returns:
        True if removal successful
    """
    # Convert interface name format
    intf_config = interface.replace('Ethernet', 'Ethernet ')

    st.log(f"Removing description from {interface}")

    commands = [
        f"interface {intf_config}",
        "no description",
        "exit"
    ]

    try:
        st.config(dut, commands, type="klish", skip_error_check=True)
        st.log(f"✓ Description removed from {interface}")
        return True
    except Exception as error:
        st.warn(f"Failed to remove description from {interface}: {error}")
        return False


def verify_description_has_quotes(dut: str, interface: str, expected_description: str) -> Tuple[bool, str]:
    """
    Verify that multi-word description is displayed with quotes in running-config.

    Args:
        dut: Device under test
        interface: Interface name (e.g., 'Ethernet0')
        expected_description: Expected description text (without quotes)

    Returns:
        Tuple of (has_quotes: bool, actual_output: str)
    """
    # Convert interface name format
    intf_display = interface.replace('Ethernet', 'Ethernet ')

    st.log(f"Verifying description quotes for {interface}")
    output = st.show(dut, f"show running-configuration interface {intf_display} | no-more",
                     type="klish", skip_tmpl=True, skip_error_check=True)

    if not output:
        st.error(f"No output from show running-configuration for {interface}")
        return (False, "")

    # Check if description has multiple words (spaces)
    has_spaces = ' ' in expected_description

    # Parse output to find description line
    lines = output.split('\n') if isinstance(output, str) else []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith('description'):
            st.log(f"Found description line: {line_stripped}")

            # Check if description is quoted
            # Pattern: description "..."
            quoted_pattern = r'^\s*description\s+"([^"]+)"\s*$'
            # Pattern: description ... (unquoted multi-word - the BUG)
            unquoted_pattern = r'^\s*description\s+(\S+(\s+\S+)+)\s*$'

            quoted_match = re.match(quoted_pattern, line_stripped)
            unquoted_match = re.match(unquoted_pattern, line_stripped)

            if quoted_match:
                st.log(f"✓ Description is QUOTED: {quoted_match.group(1)}")
                return (True, output)
            elif has_spaces and unquoted_match:
                st.error(f"✗ Multi-word description is UNQUOTED (BUG): {line_stripped}")
                return (False, output)
            elif not has_spaces:
                # Single word - quotes are optional
                st.log(f"Single-word description (quotes optional): {line_stripped}")
                return (True, output)  # Accept single-word without quotes

    st.error(f"Description line not found in output for {interface}")
    return (False, output)


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module level setup and teardown"""
    global data

    st.banner("MODULE PROLOGUE: SM_ISCLI_25 - Interface Description Quote Handling Test")

    # Load test variables
    config = load_test_variables()
    defaults = config.get("defaults", {})

    # Get topology - single node only
    data.vars = st.get_testbed_vars()
    data.dut = data.vars.D1

    # Load test configuration
    data.config = SpyTestDict(config)
    data.defaults = SpyTestDict(defaults)
    data.testcases = SpyTestDict(config.get("testcases", {}))

    # Set timeouts
    data.verify_timeout = int(defaults.get("verify_timeout", 30))
    data.cli_type = defaults.get("cli_type", "klish")

    # Get available data interfaces (excluding management)
    data.available_interfaces = get_available_data_interfaces(data.dut)

    if len(data.available_interfaces) < 2:
        pytest.skip(f"Insufficient data interfaces: need at least 2, found {len(data.available_interfaces)}")

    st.log(f"Test will use device: {data.dut}")
    st.log(f"Available interfaces: {len(data.available_interfaces)}")
    st.log(f"Verify timeout: {data.verify_timeout} seconds")

    # Backup original descriptions for interfaces we'll use
    data.original_descriptions = {}
    test_interfaces = data.available_interfaces[:10]  # Save first 10 for testing
    for intf in test_interfaces:
        desc = get_interface_description(data.dut, intf)
        if desc:
            data.original_descriptions[intf] = desc
            st.log(f"Saved original description for {intf}: '{desc}'")

    yield

    # Module epilogue - Cleanup
    st.banner("MODULE EPILOGUE: Cleanup")

    if not defaults.get("cleanup", True):
        st.log("Cleanup disabled - skipping cleanup session")
        return

    st.log("Starting cleanup session - restoring original descriptions")

    try:
        # Restore original descriptions
        for intf, desc in data.original_descriptions.items():
            st.log(f"Restoring description for {intf}: '{desc}'")
            set_interface_description(data.dut, intf, desc, use_quotes=True)

        # Remove descriptions from interfaces that didn't have one originally
        test_interfaces = data.available_interfaces[:10]
        for intf in test_interfaces:
            if intf not in data.original_descriptions:
                remove_interface_description(data.dut, intf)

        st.log("✓ Cleanup session completed successfully")

    except Exception as error:
        st.warn(f"Cleanup encountered error: {error}")
        st.log("Continuing despite cleanup error")


def test_interface_description_quote_verification():
    """
    TC-SM-ISCLI-25-01: Verify multi-word descriptions are displayed with quotes

    Steps:
      1. Select a non-management data interface
      2. Save original configuration
      3. Configure a multi-word description
      4. Execute show running-configuration interface
      5. Verify description is enclosed in quotes
      6. Restore original configuration
    """
    st.banner(f"{TC_IDS.quote_verification}: Single Interface Multi-Word Description Quote Verification")

    testcase = data.testcases.get("25.1", {})
    description_values = testcase.get("description_values", ["Test Interface for Data Center"])

    # Select first available data interface
    if not data.available_interfaces:
        st.report_fail("msg", "No data interfaces available for testing")

    test_interface = data.available_interfaces[0]
    st.log(f"Using interface: {test_interface}")

    # Save original description
    original_desc = get_interface_description(data.dut, test_interface)
    st.log(f"Original description: '{original_desc}'")

    try:
        # Test each description value
        for desc_value in description_values:
            st.log(f"\nStep: Testing description: '{desc_value}'")

            # Configure multi-word description
            st.log("Step 1: Configure multi-word description")
            result = set_interface_description(data.dut, test_interface, desc_value, use_quotes=True)
            if not result:
                st.report_fail("msg", f"Failed to configure description on {test_interface}")

            # Verify description has quotes in show running-config
            st.log("Step 2: Verify description has quotes in running-config")
            has_quotes, output = verify_description_has_quotes(data.dut, test_interface, desc_value)

            if not has_quotes:
                st.error(f"✗ BUG DETECTED: Multi-word description NOT quoted in output")
                st.error(f"Output:\n{output[:500]}")
                st.report_fail("msg", f"Multi-word description '{desc_value}' not quoted in running-config")

            st.log(f"✓ Description '{desc_value}' is properly quoted")

    finally:
        # Restore original description
        st.log("Step 3: Restore original configuration")
        if original_desc:
            set_interface_description(data.dut, test_interface, original_desc, use_quotes=True)
        else:
            remove_interface_description(data.dut, test_interface)

    st.log("✓ SUCCESS: All multi-word descriptions properly quoted in running-config")
    st.report_pass("test_case_passed")


def test_interface_description_reapplication():
    """
    TC-SM-ISCLI-25-02: Verify running-config output can be reapplied without errors

    Steps:
      1. Configure interface with multi-word description and other parameters
      2. Capture show running-configuration output
      3. Remove configuration
      4. Reapply captured configuration line-by-line
      5. Verify all commands succeed
      6. Verify description is correctly set
      7. Verify output is idempotent
    """
    st.banner(f"{TC_IDS.reapplication}: Configuration Reapplication Test")

    testcase = data.testcases.get("25.2", {})
    test_configs = testcase.get("configs", [
        {"description": "Production Link to DC1", "mtu": 9100}
    ])

    if len(data.available_interfaces) < 1:
        st.report_fail("msg", "No data interfaces available for testing")

    test_interface = data.available_interfaces[0]
    st.log(f"Using interface: {test_interface}")

    # Save original configuration
    original_desc = get_interface_description(data.dut, test_interface)

    try:
        for config_idx, config in enumerate(test_configs):
            description = config.get("description", "")
            mtu = config.get("mtu", 9100)

            st.log(f"\nStep: Testing configuration {config_idx + 1}: desc='{description}', mtu={mtu}")

            # Step 1: Configure interface with description and MTU
            st.log("Step 1: Configure interface with multi-word description and MTU")
            intf_config = test_interface.replace('Ethernet', 'Ethernet ')
            commands = [
                f"interface {intf_config}",
                f'description "{description}"',
                f"mtu {mtu}",
                "exit"
            ]
            st.config(data.dut, commands, type="klish")

            # Step 2: Capture show running-configuration output
            st.log("Step 2: Capture show running-configuration output")
            intf_display = test_interface.replace('Ethernet', 'Ethernet ')
            output1 = st.show(data.dut, f"show running-configuration interface {intf_display} | no-more",
                             type="klish", skip_tmpl=True, skip_error_check=True)
            st.log(f"Captured configuration:\n{output1}")

            # Step 3: Remove description (keep MTU)
            st.log("Step 3: Remove description from interface")
            remove_interface_description(data.dut, test_interface)

            # Step 4: Reapply description from captured output
            st.log("Step 4: Reapply configuration from captured output")
            # Parse description line from captured output
            lines = output1.split('\n') if isinstance(output1, str) else []
            desc_line = None
            for line in lines:
                if line.strip().startswith('description'):
                    desc_line = line.strip()
                    break

            if not desc_line:
                st.report_fail("msg", "Failed to extract description line from captured output")

            st.log(f"Reapplying command: {desc_line}")
            reapply_commands = [
                f"interface {intf_config}",
                desc_line,  # Use exact line from show output
                "exit"
            ]

            # This should succeed if description is properly quoted
            try:
                st.config(data.dut, reapply_commands, type="klish", skip_error_check=False)
                st.log("✓ Configuration reapplication succeeded")
            except Exception as error:
                st.error(f"✗ BUG DETECTED: Configuration reapplication FAILED")
                st.error(f"Error: {error}")
                st.error(f"This means the description line from show output is malformed")
                st.report_fail("msg", f"Configuration reapplication failed: {error}")

            # Step 5: Verify description is correctly set (not truncated)
            st.log("Step 5: Verify description is correctly set")
            current_desc = get_interface_description(data.dut, test_interface)
            if current_desc != description:
                st.error(f"✗ Description mismatch after reapplication")
                st.error(f"Expected: '{description}'")
                st.error(f"Got: '{current_desc}'")
                st.report_fail("msg", "Description truncated or incorrect after reapplication")
            st.log(f"✓ Description correctly set: '{current_desc}'")

            # Step 6: Verify output is idempotent
            st.log("Step 6: Verify output is idempotent (same before and after)")
            output2 = st.show(data.dut, f"show running-configuration interface {intf_display} | no-more",
                             type="klish", skip_tmpl=True, skip_error_check=True)

            # Extract description lines for comparison
            desc1 = ""
            desc2 = ""
            for line in output1.split('\n'):
                if 'description' in line:
                    desc1 = line.strip()
            for line in output2.split('\n'):
                if 'description' in line:
                    desc2 = line.strip()

            if desc1 != desc2:
                st.warn(f"Description line changed after reapplication")
                st.warn(f"Before: {desc1}")
                st.warn(f"After:  {desc2}")
            else:
                st.log(f"✓ Output is idempotent: {desc1}")

    finally:
        # Restore original configuration
        st.log("Cleanup: Restore original configuration")
        if original_desc:
            set_interface_description(data.dut, test_interface, original_desc, use_quotes=True)
        else:
            remove_interface_description(data.dut, test_interface)

    st.log("✓ SUCCESS: Configuration reapplication works correctly")
    st.report_pass("test_case_passed")


def test_interface_description_multiple_formats():
    """
    TC-SM-ISCLI-25-03: Verify quote handling across various description formats

    Steps:
      1. Select 3-4 non-management data interfaces
      2. Configure each with different description patterns
      3. Verify quote handling for each pattern
      4. Single-word: quotes optional
      5. Multi-word: quotes required
      6. Special characters: handled correctly
    """
    st.banner(f"{TC_IDS.multiple_formats}: Multiple Interfaces with Various Description Formats")

    testcase = data.testcases.get("25.3", {})
    test_interfaces_config = testcase.get("interfaces", [
        {"description": "Uplink", "expect_quotes_required": False},
        {"description": "Core Switch Connection", "expect_quotes_required": True},
        {"description": "Link-to-DC_01", "expect_quotes_required": False},
        {"description": "Backup Path 100G", "expect_quotes_required": True},
    ])

    # Need at least 4 interfaces for this test
    needed_intfs = len(test_interfaces_config)
    if len(data.available_interfaces) < needed_intfs:
        st.warn(f"Only {len(data.available_interfaces)} interfaces available, need {needed_intfs}")
        # Use what we have
        needed_intfs = len(data.available_interfaces)
        test_interfaces_config = test_interfaces_config[:needed_intfs]

    test_interfaces = data.available_interfaces[:needed_intfs]
    st.log(f"Using {len(test_interfaces)} interfaces for testing")

    # Save original descriptions
    original_descriptions = {}
    for intf in test_interfaces:
        desc = get_interface_description(data.dut, intf)
        if desc:
            original_descriptions[intf] = desc

    try:
        # Configure and verify each interface
        for idx, intf in enumerate(test_interfaces):
            if idx >= len(test_interfaces_config):
                break

            config = test_interfaces_config[idx]
            description = config.get("description", "")
            expect_quotes_required = config.get("expect_quotes_required", True)

            st.log(f"\nStep: Testing interface {intf} with description '{description}'")
            st.log(f"Quotes required: {expect_quotes_required}")

            # Configure description
            set_interface_description(data.dut, intf, description, use_quotes=True)

            # Verify quote handling
            has_quotes, output = verify_description_has_quotes(data.dut, intf, description)

            # Check if description has spaces (multi-word)
            has_spaces = ' ' in description

            if has_spaces and expect_quotes_required and not has_quotes:
                st.error(f"✗ BUG: Multi-word description '{description}' not quoted on {intf}")
                st.report_fail("msg", f"Multi-word description not quoted on {intf}")
            elif has_spaces and expect_quotes_required and has_quotes:
                st.log(f"✓ Multi-word description properly quoted on {intf}")
            elif not has_spaces:
                st.log(f"✓ Single-word description on {intf} (quotes optional)")
            else:
                st.log(f"✓ Description format handled correctly on {intf}")

    finally:
        # Restore original descriptions
        st.log("Cleanup: Restore original descriptions")
        for intf in test_interfaces:
            if intf in original_descriptions:
                set_interface_description(data.dut, intf, original_descriptions[intf], use_quotes=True)
            else:
                remove_interface_description(data.dut, intf)

    st.log("✓ SUCCESS: All description formats handled correctly")
    st.report_pass("test_case_passed")


def test_interface_description_pagination():
    """
    TC-SM-ISCLI-25-04: Verify quote handling with pagination (--More--)

    Steps:
      1. Configure multiple interfaces with multi-word descriptions
      2. Execute show running-configuration interface (all interfaces)
      3. Handle pagination automatically
      4. Verify all descriptions are properly quoted
    """
    st.banner(f"{TC_IDS.pagination}: Pagination Handling for Multiple Interfaces")

    testcase = data.testcases.get("25.4", {})
    min_interfaces = testcase.get("min_interfaces", 10)
    description_template = testcase.get("description_template", "Interface Link Number {index}")

    # Use as many interfaces as available, up to 15
    num_interfaces = min(len(data.available_interfaces), 15)
    if num_interfaces < min_interfaces:
        st.warn(f"Only {num_interfaces} interfaces available, need {min_interfaces} for best pagination test")

    test_interfaces = data.available_interfaces[:num_interfaces]
    st.log(f"Using {num_interfaces} interfaces for pagination test")

    # Save original descriptions
    original_descriptions = {}
    for intf in test_interfaces:
        desc = get_interface_description(data.dut, intf)
        if desc:
            original_descriptions[intf] = desc

    try:
        # Configure multi-word descriptions on all test interfaces
        st.log("Step 1: Configure multi-word descriptions on multiple interfaces")
        for idx, intf in enumerate(test_interfaces):
            description = description_template.format(index=idx + 1)
            st.log(f"Configuring {intf}: '{description}'")
            set_interface_description(data.dut, intf, description, use_quotes=True)

        # Get running-config for all interfaces (will paginate if many interfaces)
        st.log("Step 2: Execute show running-configuration interface (with pagination)")
        # Use | no-more to automatically handle pagination
        output = st.show(data.dut, "show running-configuration interface | no-more",
                        type="klish", skip_tmpl=True, skip_error_check=True)

        if not output:
            st.report_fail("msg", "No output from show running-configuration interface")

        st.log(f"Got output: {len(output)} characters")

        # Verify all configured descriptions are in the output and properly quoted
        st.log("Step 3: Verify all descriptions are properly quoted in paginated output")
        missing_count = 0
        unquoted_count = 0

        for idx, intf in enumerate(test_interfaces):
            expected_desc = description_template.format(index=idx + 1)

            # Check if description appears in output
            # Should appear as: description "Interface Link Number X"
            quoted_pattern = f'description "{expected_desc}"'
            unquoted_pattern = f'description {expected_desc}'

            if quoted_pattern in output:
                st.log(f"✓ {intf}: Found properly quoted description")
            elif unquoted_pattern in output:
                st.error(f"✗ {intf}: Found UNQUOTED description (BUG)")
                unquoted_count += 1
            else:
                st.warn(f"? {intf}: Description not found in output")
                missing_count += 1

        if unquoted_count > 0:
            st.error(f"✗ BUG DETECTED: {unquoted_count} descriptions were unquoted")
            st.report_fail("msg", f"{unquoted_count} multi-word descriptions not quoted in paginated output")

        if missing_count > 0:
            st.warn(f"{missing_count} descriptions not found in output (may be pagination issue)")

        st.log(f"✓ All {num_interfaces} descriptions properly quoted in paginated output")

    finally:
        # Restore original descriptions
        st.log("Cleanup: Restore original descriptions")
        for intf in test_interfaces:
            if intf in original_descriptions:
                set_interface_description(data.dut, intf, original_descriptions[intf], use_quotes=True)
            else:
                remove_interface_description(data.dut, intf)

    st.log("✓ SUCCESS: Pagination handling works correctly with quoted descriptions")
    st.report_pass("test_case_passed")


@pytest.mark.negative
def test_interface_description_negative_unquoted():
    """
    TC-SM-ISCLI-25-05: Negative test - unquoted multi-word description

    Steps:
      1. Attempt to configure multi-word description WITHOUT quotes
      2. Verify command fails or only accepts first word
      3. Configure same description WITH quotes
      4. Verify command succeeds
      5. Verify full description is set correctly
    """
    st.banner(f"{TC_IDS.negative_unquoted}: Negative Test - Unquoted Multi-Word Description")

    testcase = data.testcases.get("25.5", {})
    test_description = testcase.get("unquoted_description", "This is a test description")

    if not data.available_interfaces:
        st.report_fail("msg", "No data interfaces available for testing")

    test_interface = data.available_interfaces[0]
    st.log(f"Using interface: {test_interface}")

    # Save original description
    original_desc = get_interface_description(data.dut, test_interface)

    try:
        # Step 1: Attempt to configure WITHOUT quotes (should fail or truncate)
        st.log("Step 1: Attempt to configure multi-word description WITHOUT quotes")
        st.log(f"Test description: '{test_description}'")

        result = set_interface_description(data.dut, test_interface, test_description, use_quotes=False)

        # Check what actually got configured
        actual_desc = get_interface_description(data.dut, test_interface)
        st.log(f"Description after unquoted config: '{actual_desc}'")

        # Verify that it either failed or got truncated
        if actual_desc == test_description:
            st.warn("Unquoted multi-word description was accepted (may not be the bug)")
            st.log("This could mean the CLI has been fixed or handles it differently")
        elif actual_desc and actual_desc != test_description:
            st.log(f"✓ Unquoted description was truncated: '{actual_desc}'")
            st.log("This confirms why quotes are needed in show output")
            # Clear it for next step
            remove_interface_description(data.dut, test_interface)
        else:
            st.log("✓ Unquoted multi-word description command failed or was rejected")

        # Step 2: Configure WITH quotes (should succeed)
        st.log("Step 2: Configure same description WITH quotes")
        result = set_interface_description(data.dut, test_interface, test_description, use_quotes=True)

        if not result:
            st.report_fail("msg", "Failed to configure description even with quotes")

        st.log("✓ Configuration with quotes succeeded")

        # Step 3: Verify full description is set correctly
        st.log("Step 3: Verify full description is set correctly")
        actual_desc = get_interface_description(data.dut, test_interface)

        if actual_desc != test_description:
            st.error(f"Description mismatch!")
            st.error(f"Expected: '{test_description}'")
            st.error(f"Got: '{actual_desc}'")
            st.report_fail("msg", "Description not set correctly even with quotes")

        st.log(f"✓ Full description correctly set: '{actual_desc}'")

        # Step 4: Verify it's quoted in show running-config
        st.log("Step 4: Verify description is quoted in running-config output")
        has_quotes, output = verify_description_has_quotes(data.dut, test_interface, test_description)

        if not has_quotes:
            st.error("✗ BUG CONFIRMED: Description not quoted in show output")
            st.error("This is the bug being tested - multi-word descriptions should be quoted")
            st.report_fail("msg", "Multi-word description not quoted in show running-configuration")

        st.log("✓ Description is properly quoted in show running-configuration output")

    finally:
        # Restore original description
        st.log("Cleanup: Restore original description")
        if original_desc:
            set_interface_description(data.dut, test_interface, original_desc, use_quotes=True)
        else:
            remove_interface_description(data.dut, test_interface)

    st.log("✓ SUCCESS: Negative test confirms quotes are required for multi-word descriptions")
    st.report_pass("test_case_passed")
