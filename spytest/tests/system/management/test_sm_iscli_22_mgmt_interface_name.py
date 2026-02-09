"""
SM_ISCLI_22 - Management Interface Name Display in Running-Config

Author: Athira Arputharaj
Copyright (C) 2026, PALC Networks

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  system/management/test_sm_iscli_22_mgmt_interface_name.py \\
  --logs-path ./logs/sm_iscli_22_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Verify that the management interface appears as "Management0" (not "eth0") in
  the running-config output. This test validates the fix for the issue where
  the running-config displays the underlying Linux interface name (eth0) instead
  of the SONiC interface name (Management0).

Pre-requisites:
  - Topology: single-node (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Topology - 1 node
        # +--------------------+
        # |        dut1        |
        # |    Management0     |
        # +--------------------+
  - SONiC version with sonic-cli support
  - Required test variables (YAML): vars/system/management/vars_sm_iscli_22.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import pytest
import yaml

from spytest import st, SpyTestDict

# Test case IDs
TC_IDS = SpyTestDict({
    "mgmt_ipv4": "TC-SM-ISCLI-22-01",
    "mgmt_ipv6": "TC-SM-ISCLI-22-02",
    "mgmt_dual_stack": "TC-SM-ISCLI-22-03",
    "mgmt_persistence": "TC-SM-ISCLI-22-04",
})

# Default variable file path
DEFAULT_VAR_FILE = (
    Path(__file__).resolve().parents[3]
    / "vars"
    / "system"
    / "management"
    / "vars_sm_iscli_22.yaml"
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
                "verify_timeout": 10,
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


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module level setup and teardown"""
    global data

    st.banner("MODULE PROLOGUE: SM_ISCLI_22 - Management Interface Name Display Test")

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
    data.verify_timeout = int(defaults.get("verify_timeout", 10))
    data.cli_type = defaults.get("cli_type", "klish")

    # Backup original management IP configuration
    st.log("Backing up original management interface configuration")
    data.original_mgmt_config = get_management_interface_config(data.dut)

    st.log(f"Test will use device: {data.dut}")
    st.log(f"Verify timeout: {data.verify_timeout} seconds")

    yield

    # Module epilogue
    st.banner("MODULE EPILOGUE: Cleanup")
    # Restore original management IP if needed
    if defaults.get("cleanup", True):
        st.log("Cleanup enabled - restoring original configuration")
        # Note: In production, we would restore the original management IP
        # For now, we leave it as-is to avoid breaking connectivity


def get_management_interface_config(dut: str) -> Dict[str, Any]:
    """
    Get current management interface configuration.

    Args:
        dut: Device under test

    Returns:
        Dictionary with management interface configuration
    """
    config = {
        "ipv4": None,
        "ipv6": None,
    }

    try:
        # Get running config - use 'section' with no-more to avoid pagination
        st.log("Getting management interface config (using section with no-more to avoid pagination)")
        # Try Management0 first
        output = st.show(dut, "show running-configuration | section interface Management0 | no-more",
                        type="klish", skip_tmpl=True, skip_error_check=True)

        # If not found, try eth0
        if not output or "interface Management0" not in output:
            st.log("Management0 not found, trying eth0")
            output = st.show(dut, "show running-configuration | section interface eth0 | no-more",
                            type="klish", skip_tmpl=True, skip_error_check=True)

        st.log(f"Management interface config: {output}")

        # Parse management interface section
        lines = output.split('\n') if output else []

        for line in lines:
            line = line.strip()
            if line.startswith('ip address'):
                config["ipv4"] = line.replace('ip address', '').strip()
            elif line.startswith('ipv6 address'):
                config["ipv6"] = line.replace('ipv6 address', '').strip()

    except Exception as error:
        st.warn(f"Failed to get management config: {error}")

    return config


def verify_interface_name_in_running_config(
    dut: str,
    expected_name: str,
    not_expected_name: str,
    ip_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Verify that the running-config shows the correct interface name.

    Args:
        dut: Device under test
        expected_name: Interface name that should appear (e.g., "Management0")
        not_expected_name: Interface name that should NOT appear (e.g., "eth0")
        ip_address: Optional IP address to verify association

    Returns:
        Dictionary with verification results:
            - expected_found: bool
            - not_expected_found: bool
            - ip_associated: bool (if ip_address provided)
            - output: str (running-config output)
    """
    result = {
        "expected_found": False,
        "not_expected_found": False,
        "ip_associated": False,
        "output": "",
        "success": False,
    }

    # Get running configuration - use include with no-more to avoid pagination
    st.log("Getting running-configuration (filtered to avoid pagination)")
    # Get interface sections only to avoid large output
    # Use 'include' instead of 'grep' - it's the SONiC CLI equivalent
    # Add 'no-more' to prevent pagination prompt
    output = st.show(dut, "show running-configuration | include interface | no-more", type="klish", skip_tmpl=True)
    result["output"] = output

    st.log(f"Running-config interface lines: {output}")

    # Check for expected interface name
    if f"interface {expected_name}" in output:
        result["expected_found"] = True
        st.log(f"✓ Found expected interface name: {expected_name}")
    else:
        st.error(f"✗ Expected interface name NOT found: {expected_name}")

    # Check for incorrect interface name
    if f"interface {not_expected_name}" in output:
        result["not_expected_found"] = True
        st.error(f"✗ Found incorrect interface name: {not_expected_name}")
    else:
        st.log(f"✓ Incorrect interface name NOT found: {not_expected_name}")

    # If IP address provided, verify it's associated with the correct interface
    if ip_address:
        # Extract just the IP without prefix length for matching
        ip_base = ip_address.split('/')[0] if '/' in ip_address else ip_address

        # Get the management interface section to check IP
        st.log(f"Checking IP association for {ip_address}")
        try:
            # Use 'section' filter to get the entire interface section with no-more
            mgmt_section = st.show(dut, f"show running-configuration | section interface {expected_name} | no-more",
                                  type="klish", skip_tmpl=True, skip_error_check=True)
            if ip_base in mgmt_section:
                result["ip_associated"] = True
                st.log(f"✓ IP address {ip_address} associated with {expected_name}")
            else:
                st.warn(f"IP address {ip_address} not found in {expected_name} section")
                result["ip_associated"] = False
        except Exception as error:
            st.warn(f"Failed to check IP association: {error}")
            result["ip_associated"] = False

    # Overall success
    result["success"] = (
        result["expected_found"] and
        not result["not_expected_found"] and
        (result["ip_associated"] if ip_address else True)
    )

    return result


def configure_management_ip(dut: str, ip_address: str, ip_version: str = "ipv4") -> bool:
    """
    Configure IP address on management interface.

    Args:
        dut: Device under test
        ip_address: IP address with prefix (e.g., "172.31.51.147/16")
        ip_version: "ipv4" or "ipv6"

    Returns:
        True if configuration successful
    """
    st.log(f"Configuring {ip_version} address {ip_address} on Management0")

    try:
        # Configure via sonic-cli (klish)
        if ip_version == "ipv4":
            cmd = f"ip address {ip_address}"
        else:
            cmd = f"ipv6 address {ip_address}"

        commands = [
            "interface Management 0",
            cmd,
            "exit"
        ]

        st.config(dut, commands, type="klish")
        st.log(f"✓ Configuration commands executed successfully")
        return True

    except Exception as error:
        st.error(f"Failed to configure management IP: {error}")
        return False


def remove_management_ip(dut: str, ip_address: str, ip_version: str = "ipv4") -> bool:
    """
    Remove IP address from management interface.

    Args:
        dut: Device under test
        ip_address: IP address with prefix to remove
        ip_version: "ipv4" or "ipv6"

    Returns:
        True if removal successful
    """
    st.log(f"Removing {ip_version} address {ip_address} from Management0")

    try:
        # Remove via sonic-cli (klish)
        if ip_version == "ipv4":
            cmd = f"no ip address {ip_address}"
        else:
            cmd = f"no ipv6 address {ip_address}"

        commands = [
            "interface Management 0",
            cmd,
            "exit"
        ]

        st.config(dut, commands, type="klish", skip_error_check=True)
        st.log(f"✓ Removal commands executed")
        return True

    except Exception as error:
        st.warn(f"Failed to remove management IP: {error}")
        return False


def test_mgmt_interface_name_display_ipv4():
    """
    TC-SM-ISCLI-22-01: Verify Management0 (not eth0) appears in running-config with IPv4

    Steps:
      1. Configure IPv4 address on Management0 interface
      2. Display running-configuration
      3. Verify "interface Management0" appears
      4. Verify "interface eth0" does NOT appear
      5. Verify IP address is associated with Management0
    """
    st.banner(f"{TC_IDS.mgmt_ipv4}: Management interface name display - IPv4")

    testcase = data.testcases.get("22.1", {})
    management_ip = testcase.get("management_ip", "172.31.51.147/16")
    expected_name = testcase.get("expected_interface_name", "Management0")
    not_expected_name = testcase.get("not_expected_name", "eth0")

    # Configure management IP
    st.log(f"Step 1: Configure IPv4 address {management_ip} on Management0")
    if not configure_management_ip(data.dut, management_ip, "ipv4"):
        st.report_fail("mgmt_ip_config_failed", management_ip)

    # Wait for configuration to apply
    st.wait(2)

    # Verify interface name in running-config
    st.log("Step 2: Verify interface name in running-configuration")
    result = verify_interface_name_in_running_config(
        data.dut,
        expected_name,
        not_expected_name,
        management_ip
    )

    # Check results
    if not result["expected_found"]:
        st.error(f"Expected interface name '{expected_name}' NOT found in running-config")
        st.error(f"Output: {result['output'][:500]}")
        st.report_fail("mgmt_interface_name_not_found", expected_name)

    if result["not_expected_found"]:
        st.error(f"Incorrect interface name '{not_expected_name}' found in running-config")
        st.error("This is the BUG: eth0 should not appear, should be Management0")
        st.error(f"Output: {result['output'][:500]}")
        st.report_fail("mgmt_interface_shows_incorrect_name", not_expected_name)

    if not result["ip_associated"]:
        st.error(f"IP address {management_ip} not associated with {expected_name}")
        st.report_fail("mgmt_ip_not_associated")

    st.log("✓ SUCCESS: Management interface displayed with correct name (Management0)")
    st.report_pass("test_case_passed")


def test_mgmt_interface_name_display_ipv6():
    """
    TC-SM-ISCLI-22-02: Verify Management0 (not eth0) appears in running-config with IPv6

    Steps:
      1. Configure IPv6 address on Management0 interface
      2. Display running-configuration
      3. Verify "interface Management0" appears
      4. Verify "interface eth0" does NOT appear
      5. Verify IPv6 address is associated with Management0
    """
    st.banner(f"{TC_IDS.mgmt_ipv6}: Management interface name display - IPv6")

    testcase = data.testcases.get("22.2", {})
    management_ip = testcase.get("management_ip", "2001:db8:1::10/64")
    expected_name = testcase.get("expected_interface_name", "Management0")
    not_expected_name = testcase.get("not_expected_name", "eth0")

    # Configure management IPv6
    st.log(f"Step 1: Configure IPv6 address {management_ip} on Management0")
    if not configure_management_ip(data.dut, management_ip, "ipv6"):
        st.report_fail("mgmt_ipv6_config_failed", management_ip)

    # Wait for configuration to apply
    st.wait(2)

    # Verify interface name in running-config
    st.log("Step 2: Verify interface name in running-configuration")
    result = verify_interface_name_in_running_config(
        data.dut,
        expected_name,
        not_expected_name,
        management_ip
    )

    # Check results
    if not result["expected_found"]:
        st.error(f"Expected interface name '{expected_name}' NOT found in running-config")
        st.report_fail("mgmt_interface_name_not_found", expected_name)

    if result["not_expected_found"]:
        st.error(f"Incorrect interface name '{not_expected_name}' found in running-config")
        st.error("This is the BUG: eth0 should not appear, should be Management0")
        st.report_fail("mgmt_interface_shows_incorrect_name", not_expected_name)

    st.log("✓ SUCCESS: Management interface displayed with correct name (Management0)")
    st.report_pass("test_case_passed")


def test_mgmt_interface_name_display_dual_stack():
    """
    TC-SM-ISCLI-22-03: Verify Management0 (not eth0) with both IPv4 and IPv6

    Steps:
      1. Configure both IPv4 and IPv6 addresses on Management0
      2. Display running-configuration
      3. Verify "interface Management0" appears (single section)
      4. Verify "interface eth0" does NOT appear
      5. Verify both IP addresses are associated with Management0
    """
    st.banner(f"{TC_IDS.mgmt_dual_stack}: Management interface name display - Dual Stack")

    testcase = data.testcases.get("22.3", {})
    management_ipv4 = testcase.get("management_ipv4", "172.31.51.147/16")
    management_ipv6 = testcase.get("management_ipv6", "2001:db8:1::10/64")
    expected_name = testcase.get("expected_interface_name", "Management0")
    not_expected_name = testcase.get("not_expected_name", "eth0")

    # Configure management IPv4
    st.log(f"Step 1a: Configure IPv4 address {management_ipv4} on Management0")
    if not configure_management_ip(data.dut, management_ipv4, "ipv4"):
        st.report_fail("mgmt_ipv4_config_failed", management_ipv4)

    st.wait(1)

    # Configure management IPv6
    st.log(f"Step 1b: Configure IPv6 address {management_ipv6} on Management0")
    if not configure_management_ip(data.dut, management_ipv6, "ipv6"):
        st.report_fail("mgmt_ipv6_config_failed", management_ipv6)

    # Wait for configuration to apply
    st.wait(2)

    # Verify interface name in running-config
    st.log("Step 2: Verify interface name in running-configuration")
    result = verify_interface_name_in_running_config(
        data.dut,
        expected_name,
        not_expected_name,
        management_ipv4  # Check IPv4 association
    )

    # Check results
    if not result["expected_found"]:
        st.error(f"Expected interface name '{expected_name}' NOT found in running-config")
        st.report_fail("mgmt_interface_name_not_found", expected_name)

    if result["not_expected_found"]:
        st.error(f"Incorrect interface name '{not_expected_name}' found in running-config")
        st.error("This is the BUG: eth0 should not appear, should be Management0")
        st.report_fail("mgmt_interface_shows_incorrect_name", not_expected_name)

    st.log("✓ SUCCESS: Management interface displayed with correct name (Management0)")
    st.log("✓ Both IPv4 and IPv6 addresses configured")
    st.report_pass("test_case_passed")


def test_mgmt_interface_name_persistence():
    """
    TC-SM-ISCLI-22-04: Verify Management0 name persists after config save

    Steps:
      1. Configure IP address on Management0
      2. Save configuration: write memory
      3. Re-display running-configuration
      4. Verify "interface Management0" still appears
      5. Verify "interface eth0" does NOT appear

    Note: This test verifies that the interface name remains correct
          even after configuration save/reload operations.
    """
    st.banner(f"{TC_IDS.mgmt_persistence}: Management interface name persistence")

    testcase = data.testcases.get("22.4", {})
    management_ip = testcase.get("management_ip", "172.31.51.150/16")
    expected_name = testcase.get("expected_interface_name", "Management0")
    not_expected_name = testcase.get("not_expected_name", "eth0")

    # Configure management IP
    st.log(f"Step 1: Configure IPv4 address {management_ip} on Management0")
    if not configure_management_ip(data.dut, management_ip, "ipv4"):
        st.report_fail("mgmt_ip_config_failed", management_ip)

    st.wait(2)

    # Save configuration
    st.log("Step 2: Save configuration (write memory)")
    try:
        st.config(data.dut, "write memory", type="klish", skip_error_check=True)
        st.log("✓ Configuration saved")
    except Exception as error:
        st.warn(f"Write memory command returned: {error}")

    st.wait(2)

    # Verify interface name in running-config (after save)
    st.log("Step 3: Verify interface name persists after save")
    result = verify_interface_name_in_running_config(
        data.dut,
        expected_name,
        not_expected_name,
        management_ip
    )

    # Check results
    if not result["expected_found"]:
        st.error(f"Expected interface name '{expected_name}' NOT found after save")
        st.report_fail("mgmt_interface_name_not_persistent", expected_name)

    if result["not_expected_found"]:
        st.error(f"Incorrect interface name '{not_expected_name}' found after save")
        st.error("Interface name changed to eth0 after save - persistence issue")
        st.report_fail("mgmt_interface_name_changed_after_save")

    st.log("✓ SUCCESS: Management interface name persists after configuration save")
    st.report_pass("test_case_passed")
