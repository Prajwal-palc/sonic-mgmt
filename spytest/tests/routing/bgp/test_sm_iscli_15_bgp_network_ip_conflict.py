"""
BGP Network Statement Blocking Interface IP Configuration - IS-CLI Bug

Author: Athira
Copyright (C) 2026, PALC Networks

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_2vs.yaml \\
  tests/routing/bgp/test_sm_iscli_15_bgp_network_ip_conflict.py \\
  --logs-path ./logs/sm_iscli_15_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test suite validates that BGP network statements in IS-CLI do not
  incorrectly block interface IP address configuration. The bug causes
  IS-CLI to reject interface IP assignments when the IP overlaps with
  an existing BGP network statement, incorrectly treating BGP network
  prefixes as interface IPs in ConfigDB validation.

  Error example: "IP X overlaps with existing configuration
  (BGP_GLOBALS_AF_NETWORK|default|ipv4_unicast|X)"

Pre-requisites:
  - Topology: single-node (D1) | Supported: HW and Virtual
  - SONiC version: 202505-smci-dev-iscli (or later with the bug)
  - CLI type: IS-CLI (klish) - Click CLI does not have this bug
  - Required test variables (YAML): vars/routing/bgp/vars_sm_iscli_15.yaml

Test Cases:
  TC1: BGP network /32 should not block Loopback IP /32
  TC2: BGP network /24 should not block Ethernet IP /24
  TC3: Interface IP configured before BGP network (reversed order)
  TC4: Multiple BGP networks with multiple interface IPs
  TC5: BGP network removal should not affect interface IP
"""

import pytest
import re
from pathlib import Path
import yaml

from spytest import st, SpyTestDict
import apis.routing.ip as ip_api
import apis.routing.bgp as bgp_api

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Default YAML configuration file location
DEFAULT_VAR_FILE = Path(__file__).resolve().parents[3] / "vars/routing/bgp/vars_sm_iscli_15.yaml"

# Test Case IDs
TC_IDS = SpyTestDict({
    "tc1": "SM_ISCLI_15_TC1",
    "tc2": "SM_ISCLI_15_TC2",
    "tc3": "SM_ISCLI_15_TC3",
    "tc4": "SM_ISCLI_15_TC4",
    "tc5": "SM_ISCLI_15_TC5",
})


def initialize_data() -> None:
    """
    Load test configuration from YAML file and initialize topology.
    """
    st.banner("INITIALIZING TEST DATA FROM YAML")

    try:
        with open(DEFAULT_VAR_FILE, "r") as f:
            payload = yaml.safe_load(f)
    except FileNotFoundError as error:
        st.error(f"Test variables file not found: {DEFAULT_VAR_FILE}")
        pytest.skip(str(error))

    global vars, data

    # Get topology variables - use ensure_min_topology like SM_ISCLI_10
    min_topology = payload.get("min_topology", ["D1D2:1"])
    vars = st.ensure_min_topology(*min_topology)

    # Load test configuration
    data.config = SpyTestDict(payload)
    data.cli_type = st.get_ui_type(vars.D1, cli_type="klish")

    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"Topology: D1={vars.D1}")

    # Log D1-D2 link if it exists (for 2-device topology)
    if hasattr(vars, 'D2'):
        st.log(f"D2={vars.D2}")
        if hasattr(vars, 'D1D2P1'):
            st.log(f"D1-D2 Link: {vars.D1D2P1} <-> {vars.D2D1P1}")
            # Store the Ethernet interface from testbed
            data.ethernet_interface = vars.D1D2P1
        else:
            st.log("No D1-D2 link available in testbed")
            data.ethernet_interface = "Ethernet0"
    else:
        # Single device topology
        st.log("Single device topology")
        # Use first available interface or default
        data.ethernet_interface = "Ethernet0"

    st.log(f"Using Ethernet interface: {data.ethernet_interface}")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture.

    Prologue:
      - Initialize test data from YAML
      - Clean up any existing BGP and interface configuration

    Epilogue:
      - Clean up all test configuration
      - Remove BGP, interfaces, and test state
    """
    st.banner("MODULE PROLOGUE: Starting SM_ISCLI_15 Test Suite")

    # Initialize test configuration
    initialize_data()

    # Module prologue: Clean up any existing configuration
    st.log("Cleaning up existing configuration on D1")
    cleanup_all_config()

    yield

    # Module epilogue: Final cleanup
    st.banner("MODULE EPILOGUE: Cleaning up SM_ISCLI_15 Test Suite")
    cleanup_all_config()


def cleanup_all_config():
    """
    Clean up all test configurations including BGP, interfaces, and loopbacks.
    """
    st.log("Performing comprehensive configuration cleanup")

    # Check if data is properly initialized
    if not hasattr(data, 'config') or not hasattr(data, 'cli_type'):
        st.log("Data not fully initialized, skipping cleanup")
        return

    # Remove BGP configuration
    st.config(vars.D1, f"no router bgp",
              type=data.cli_type, conf=True, skip_error_check=True)
    st.wait(data.config.wait_times.bgp_config)

    # Remove Loopback interfaces
    for loopback_key in ['loopback', 'loopback2', 'loopback3', 'loopback4']:
        if loopback_key in data.config.interfaces:
            loopback_name = data.config.interfaces[loopback_key].name
            st.config(vars.D1, f"no interface {loopback_name}",
                     type=data.cli_type, conf=True, skip_error_check=True)

    # Remove Ethernet IP if configured
    if hasattr(data, 'ethernet_interface') and data.ethernet_interface:
        ip_api.delete_ip_interface(vars.D1, data.ethernet_interface,
                                   data.config.interfaces.ethernet.ip,
                                   skip_error=True, cli_type=data.cli_type)

    st.wait(data.config.wait_times.interface_config)


def configure_bgp_router(as_number, router_id):
    """
    Configure BGP router with AS number and router-id using direct commands.
    Avoids buggy BGP API that generates invalid "router-id bgp" command.

    Args:
        as_number: BGP AS number
        router_id: BGP router ID (IP format)

    Returns:
        bool: True if configuration successful
    """
    st.log(f"Configuring BGP AS {as_number} with router-id {router_id}")

    commands = [
        f"router bgp {as_number}",
        f"router-id {router_id}",
        "exit"
    ]

    result = st.config(vars.D1, commands, type=data.cli_type, conf=True, skip_error_check=False)
    st.wait(data.config.wait_times.bgp_config)

    return result


def configure_bgp_network(as_number, network_prefix):
    """
    Configure BGP network statement in IPv4 unicast address family.

    Args:
        as_number: BGP AS number
        network_prefix: Network prefix to advertise (e.g., "10.10.10.1/32")

    Returns:
        bool: True if configuration successful
    """
    st.log(f"Configuring BGP network {network_prefix}")

    commands = [
        f"router bgp {as_number}",
        "address-family ipv4 unicast",
        f"network {network_prefix}",
        "exit",
        "exit"
    ]

    result = st.config(vars.D1, commands, type=data.cli_type, conf=True, skip_error_check=False)
    st.wait(data.config.wait_times.bgp_config)

    return result


def remove_bgp_network(as_number, network_prefix):
    """
    Remove BGP network statement from IPv4 unicast address family.

    Args:
        as_number: BGP AS number
        network_prefix: Network prefix to remove

    Returns:
        bool: True if removal successful
    """
    st.log(f"Removing BGP network {network_prefix}")

    commands = [
        f"router bgp {as_number}",
        "address-family ipv4 unicast",
        f"no network {network_prefix}",
        "exit",
        "exit"
    ]

    result = st.config(vars.D1, commands, type=data.cli_type, conf=True, skip_error_check=False)
    st.wait(data.config.wait_times.bgp_config)

    return result


def configure_loopback_interface(loopback_name, ip_address):
    """
    Configure Loopback interface with IP address.

    Args:
        loopback_name: Loopback interface name (e.g., "Loopback1")
        ip_address: IP address with prefix (e.g., "10.10.10.1/32")

    Returns:
        tuple: (success, error_output) - success is bool, error_output is string or None
    """
    st.log(f"Configuring {loopback_name} with IP {ip_address}")

    commands = [
        f"interface {loopback_name}",
        f"ip address {ip_address}",
        "exit"
    ]

    output = st.config(vars.D1, commands, type=data.cli_type, conf=True, skip_error_check=False)
    st.wait(data.config.wait_times.interface_config)

    # Check for error patterns
    output_str = str(output)
    if data.config.error_patterns.ip_overlap in output_str:
        st.error(f"IP overlap error detected: {output_str}")
        return False, output_str

    return True, None


def configure_ethernet_ip(interface_name, ip_address):
    """
    Configure Ethernet interface with IP address.

    Args:
        interface_name: Ethernet interface name (e.g., "Ethernet0")
        ip_address: IP address with prefix (e.g., "192.168.100.1/24")

    Returns:
        tuple: (success, error_output) - success is bool, error_output is string or None
    """
    st.log(f"Configuring {interface_name} with IP {ip_address}")

    # First, ensure interface is up (no shutdown)
    commands = [
        f"interface {interface_name}",
        "no shutdown",
        "exit"
    ]
    st.config(vars.D1, commands, type=data.cli_type, conf=True, skip_error_check=True)
    st.wait(1)

    # Now configure IP address - use skip_error_check=True to avoid hanging on errors
    commands = [
        f"interface {interface_name}",
        f"ip address {ip_address}",
        "exit"
    ]

    # Use skip_error_check=True to prevent hanging if device shows error without proper prompt
    output = st.config(vars.D1, commands, type=data.cli_type, conf=True, skip_error_check=True)
    st.wait(data.config.wait_times.interface_config)

    # Check for error patterns in output
    output_str = str(output)
    st.log(f"IP configuration output: {output_str}")

    if data.config.error_patterns.ip_overlap in output_str:
        st.error(f"IP overlap error detected: {output_str}")
        return False, output_str

    if data.config.error_patterns.bgp_network_conflict in output_str:
        st.error(f"BGP network conflict error detected: {output_str}")
        return False, output_str

    return True, None


def verify_interface_ip(interface_name, expected_ip):
    """
    Verify that interface has the expected IP address configured.

    Args:
        interface_name: Interface name
        expected_ip: Expected IP address (e.g., "10.10.10.1/32")

    Returns:
        bool: True if IP is configured as expected
    """
    st.log(f"Verifying {interface_name} has IP {expected_ip}")

    # Get interface IP configuration
    output = ip_api.get_interface_ip_address(vars.D1, interface_name, cli_type=data.cli_type)

    if not output:
        st.error(f"Failed to get IP address for {interface_name}")
        return False

    # Extract IP from expected format (remove prefix length for comparison)
    expected_ip_only = expected_ip.split('/')[0]

    # Check if expected IP is in the output
    for entry in output:
        if 'ipaddr' in entry and expected_ip_only in str(entry['ipaddr']):
            st.log(f"✓ Verification PASSED: {interface_name} has IP {expected_ip}")
            return True

    st.error(f"Verification FAILED: {interface_name} does not have IP {expected_ip}")
    st.error(f"Actual output: {output}")
    return False


def verify_bgp_network_in_config(network_prefix):
    """
    Verify that BGP network statement is present in running configuration.

    Args:
        network_prefix: Network prefix to verify (e.g., "10.10.10.1/32")

    Returns:
        bool: True if network statement is present
    """
    st.log(f"Verifying BGP network {network_prefix} in running-config")

    output = st.show(vars.D1, "show running-configuration bgp", type=data.cli_type, skip_tmpl=True)

    if not output:
        st.error("Failed to retrieve BGP running configuration")
        return False

    # Convert output to string if it's a list
    if isinstance(output, list):
        config_text = "\n".join([str(item) for item in output])
    else:
        config_text = str(output)

    # Check for network statement
    pattern = rf'network\s+{re.escape(network_prefix)}'
    if re.search(pattern, config_text, re.IGNORECASE):
        st.log(f"✓ Verification PASSED: BGP network {network_prefix} found in running-config")
        return True

    st.error(f"Verification FAILED: BGP network {network_prefix} not found in running-config")
    return False


def check_for_overlap_error(output):
    """
    Check if command output contains IP overlap error.

    Args:
        output: Command output to check

    Returns:
        bool: True if overlap error detected
    """
    if not output:
        return False

    output_str = str(output)
    return (data.config.error_patterns.ip_overlap in output_str or
            data.config.error_patterns.bgp_network_conflict in output_str)


# ============================================================================
# TEST CASES
# ============================================================================

def test_sm_iscli_15_tc1_loopback_32_not_blocked():
    """
    TC1: Verify BGP network /32 does not block Loopback IP /32

    Steps:
      1. Configure BGP router
      2. Configure BGP network statement for 10.10.10.1/32
      3. Configure Loopback1 with same IP 10.10.10.1/32
      4. Verify Loopback IP is configured successfully (should not be blocked)
      5. Verify BGP network statement is present

    Expected Result:
      - Loopback IP configuration should succeed (BUG: currently fails with overlap error)
      - Both BGP network and interface IP should coexist
    """
    st.banner("TC1: BGP network /32 should not block Loopback IP /32")

    result = True

    # Step 1: Configure BGP router
    st.log("Step 1: Configure BGP router")
    if not configure_bgp_router(data.config.bgp.as_number, data.config.bgp.router_id):
        st.report_tc_fail(TC_IDS.tc1, "bgp_config_failed", "Failed to configure BGP router")
        st.report_fail("test_case_failed")

    # Step 2: Configure BGP network statement
    st.log("Step 2: Configure BGP network statement 10.10.10.1/32")
    if not configure_bgp_network(data.config.bgp.as_number, data.config.bgp.networks.loopback_32):
        st.report_tc_fail(TC_IDS.tc1, "bgp_network_config_failed",
                         "Failed to configure BGP network statement")
        st.report_fail("test_case_failed")

    # Step 3: Configure Loopback interface with same IP
    st.log("Step 3: Configure Loopback1 with IP 10.10.10.1/32")
    success, error_output = configure_loopback_interface(
        data.config.interfaces.loopback.name,
        data.config.interfaces.loopback.ip
    )

    if not success:
        st.error("BUG CONFIRMED: Loopback IP configuration blocked by BGP network statement")
        st.error(f"Error output: {error_output}")
        if check_for_overlap_error(error_output):
            st.report_tc_fail(TC_IDS.tc1, "ip_overlap_error",
                             "BGP network statement incorrectly blocks interface IP (BUG)")
        else:
            st.report_tc_fail(TC_IDS.tc1, "interface_ip_config_failed",
                             "Failed to configure interface IP")
        result = False
    else:
        st.log("Interface IP configuration succeeded (bug not present or fixed)")

    # Step 4: Verify Loopback IP is configured
    st.log("Step 4: Verify Loopback IP configuration")
    if not verify_interface_ip(data.config.interfaces.loopback.name,
                               data.config.interfaces.loopback.ip):
        st.report_tc_fail(TC_IDS.tc1, "interface_ip_verification_failed",
                         "Loopback IP verification failed")
        result = False

    # Step 5: Verify BGP network statement is present
    st.log("Step 5: Verify BGP network statement in running-config")
    if not verify_bgp_network_in_config(data.config.bgp.networks.loopback_32):
        st.report_tc_fail(TC_IDS.tc1, "bgp_network_verification_failed",
                         "BGP network statement verification failed")
        result = False

    # Cleanup
    st.log("Cleanup: Removing test configuration")
    st.config(vars.D1, f"no interface {data.config.interfaces.loopback.name}",
             type=data.cli_type, conf=True, skip_error_check=True)
    st.config(vars.D1, f"no router bgp",
             type=data.cli_type, conf=True, skip_error_check=True)

    if result:
        st.report_tc_pass(TC_IDS.tc1, "test_case_passed",
                         "BGP network /32 does not block Loopback IP /32")
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


def test_sm_iscli_15_tc2_ethernet_24_not_blocked():
    """
    TC2: Verify BGP network /24 does not block Ethernet IP /24

    Steps:
      1. Configure BGP router
      2. Configure BGP network statement for 192.168.100.0/24
      3. Configure Ethernet interface with IP 192.168.100.1/24
      4. Verify Ethernet IP is configured successfully (should not be blocked)
      5. Verify BGP network statement is present

    Expected Result:
      - Ethernet IP configuration should succeed (BUG: currently fails with overlap error)
      - Both BGP network and interface IP should coexist
    """
    st.banner("TC2: BGP network /24 should not block Ethernet IP /24")

    result = True

    # Step 1: Configure BGP router
    st.log("Step 1: Configure BGP router")
    if not configure_bgp_router(data.config.bgp.as_number, data.config.bgp.router_id):
        st.report_tc_fail(TC_IDS.tc2, "bgp_config_failed", "Failed to configure BGP router")
        st.report_fail("test_case_failed")

    # Step 2: Configure BGP network statement
    st.log("Step 2: Configure BGP network statement 192.168.100.0/24")
    if not configure_bgp_network(data.config.bgp.as_number, data.config.bgp.networks.ethernet_24):
        st.report_tc_fail(TC_IDS.tc2, "bgp_network_config_failed",
                         "Failed to configure BGP network statement")
        st.report_fail("test_case_failed")

    # Step 3: Configure Ethernet interface IP
    st.log(f"Step 3: Configure {data.ethernet_interface} with IP 192.168.100.1/24")
    success, error_output = configure_ethernet_ip(
        data.ethernet_interface,
        data.config.interfaces.ethernet.ip
    )

    if not success:
        st.error("BUG CONFIRMED: Ethernet IP configuration blocked by BGP network statement")
        st.error(f"Error output: {error_output}")
        if check_for_overlap_error(error_output):
            st.report_tc_fail(TC_IDS.tc2, "ip_overlap_error",
                             "BGP network statement incorrectly blocks interface IP (BUG)")
        else:
            st.report_tc_fail(TC_IDS.tc2, "interface_ip_config_failed",
                             "Failed to configure interface IP")
        result = False
    else:
        st.log("Interface IP configuration succeeded (bug not present or fixed)")

    # Step 4: Verify Ethernet IP is configured
    st.log("Step 4: Verify Ethernet IP configuration")
    if not verify_interface_ip(data.ethernet_interface, data.config.interfaces.ethernet.ip):
        st.report_tc_fail(TC_IDS.tc2, "interface_ip_verification_failed",
                         "Ethernet IP verification failed")
        result = False

    # Step 5: Verify BGP network statement is present
    st.log("Step 5: Verify BGP network statement in running-config")
    if not verify_bgp_network_in_config(data.config.bgp.networks.ethernet_24):
        st.report_tc_fail(TC_IDS.tc2, "bgp_network_verification_failed",
                         "BGP network statement verification failed")
        result = False

    # Cleanup
    st.log("Cleanup: Removing test configuration")
    ip_api.delete_ip_interface(vars.D1, data.ethernet_interface,
                               data.config.interfaces.ethernet.ip,
                               skip_error=True, cli_type=data.cli_type)
    st.config(vars.D1, f"no router bgp",
             type=data.cli_type, conf=True, skip_error_check=True)

    if result:
        st.report_tc_pass(TC_IDS.tc2, "test_case_passed",
                         "BGP network /24 does not block Ethernet IP /24")
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


def test_sm_iscli_15_tc3_reversed_order():
    """
    TC3: Verify interface IP configured before BGP network statement works correctly

    Steps:
      1. Configure BGP router
      2. Configure Loopback1 with IP 10.10.10.1/32 (interface first)
      3. Configure BGP network statement for 10.10.10.1/32 (BGP network second)
      4. Verify both configurations coexist

    Expected Result:
      - Both configurations should succeed when order is reversed
      - Confirms the bug is specific to BGP→Interface order
    """
    st.banner("TC3: Interface IP configured before BGP network (reversed order)")

    result = True

    # Step 1: Configure BGP router
    st.log("Step 1: Configure BGP router")
    if not configure_bgp_router(data.config.bgp.as_number, data.config.bgp.router_id):
        st.report_tc_fail(TC_IDS.tc3, "bgp_config_failed", "Failed to configure BGP router")
        st.report_fail("test_case_failed")

    # Step 2: Configure Loopback interface FIRST
    st.log("Step 2: Configure Loopback1 with IP 10.10.10.1/32 (interface first)")
    success, error_output = configure_loopback_interface(
        data.config.interfaces.loopback.name,
        data.config.interfaces.loopback.ip
    )

    if not success:
        st.error("Interface IP configuration failed (unexpected)")
        st.report_tc_fail(TC_IDS.tc3, "interface_ip_config_failed",
                         "Failed to configure interface IP")
        st.report_fail("test_case_failed")

    # Step 3: Configure BGP network statement SECOND
    st.log("Step 3: Configure BGP network statement 10.10.10.1/32 (BGP network second)")
    if not configure_bgp_network(data.config.bgp.as_number, data.config.bgp.networks.loopback_32):
        st.report_tc_fail(TC_IDS.tc3, "bgp_network_config_failed",
                         "Failed to configure BGP network statement")
        result = False

    # Step 4: Verify both configurations
    st.log("Step 4: Verify both configurations coexist")
    if not verify_interface_ip(data.config.interfaces.loopback.name,
                               data.config.interfaces.loopback.ip):
        st.report_tc_fail(TC_IDS.tc3, "interface_ip_verification_failed",
                         "Loopback IP verification failed")
        result = False

    if not verify_bgp_network_in_config(data.config.bgp.networks.loopback_32):
        st.report_tc_fail(TC_IDS.tc3, "bgp_network_verification_failed",
                         "BGP network statement verification failed")
        result = False

    # Cleanup
    st.log("Cleanup: Removing test configuration")
    st.config(vars.D1, f"no interface {data.config.interfaces.loopback.name}",
             type=data.cli_type, conf=True, skip_error_check=True)
    st.config(vars.D1, f"no router bgp",
             type=data.cli_type, conf=True, skip_error_check=True)

    if result:
        st.report_tc_pass(TC_IDS.tc3, "test_case_passed",
                         "Reversed order configuration successful")
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


def test_sm_iscli_15_tc4_multiple_networks_multiple_interfaces():
    """
    TC4: Verify multiple BGP networks do not block multiple interface IPs

    Steps:
      1. Configure BGP router
      2. Configure multiple BGP network statements
         - 172.16.1.0/24
         - 172.16.2.0/24
         - 172.16.3.0/32
      3. Configure multiple Loopback interfaces with matching IPs
         - Loopback2: 172.16.1.1/24
         - Loopback3: 172.16.2.1/24
         - Loopback4: 172.16.3.1/32
      4. Verify all interface IPs are configured successfully
      5. Verify all BGP network statements are present

    Expected Result:
      - All interface IP configurations should succeed (BUG: currently fails)
      - All BGP networks and interface IPs should coexist
    """
    st.banner("TC4: Multiple BGP networks with multiple interface IPs")

    result = True
    failed_interfaces = []

    # Step 1: Configure BGP router
    st.log("Step 1: Configure BGP router")
    if not configure_bgp_router(data.config.bgp.as_number, data.config.bgp.router_id):
        st.report_tc_fail(TC_IDS.tc4, "bgp_config_failed", "Failed to configure BGP router")
        st.report_fail("test_case_failed")

    # Step 2: Configure multiple BGP network statements
    st.log("Step 2: Configure multiple BGP network statements")
    networks = [
        data.config.bgp.networks.multiple_net1,
        data.config.bgp.networks.multiple_net2,
        data.config.bgp.networks.multiple_net3,
    ]

    for network in networks:
        if not configure_bgp_network(data.config.bgp.as_number, network):
            st.report_tc_fail(TC_IDS.tc4, "bgp_network_config_failed",
                             f"Failed to configure BGP network {network}")
            st.report_fail("test_case_failed")

    # Step 3: Configure multiple Loopback interfaces
    st.log("Step 3: Configure multiple Loopback interfaces")
    interfaces_to_config = [
        (data.config.interfaces.loopback2.name, data.config.interfaces.loopback2.ip),
        (data.config.interfaces.loopback3.name, data.config.interfaces.loopback3.ip),
        (data.config.interfaces.loopback4.name, data.config.interfaces.loopback4.ip),
    ]

    for intf_name, intf_ip in interfaces_to_config:
        st.log(f"Configuring {intf_name} with IP {intf_ip}")
        success, error_output = configure_loopback_interface(intf_name, intf_ip)

        if not success:
            st.error(f"BUG CONFIRMED: {intf_name} IP configuration blocked by BGP network statement")
            st.error(f"Error output: {error_output}")
            failed_interfaces.append(intf_name)
            result = False

    if failed_interfaces:
        st.report_tc_fail(TC_IDS.tc4, "ip_overlap_error",
                         f"BGP network statements incorrectly block interface IPs (BUG): {failed_interfaces}")

    # Step 4: Verify all interface IPs that were successfully configured
    st.log("Step 4: Verify interface IP configurations")
    for intf_name, intf_ip in interfaces_to_config:
        if intf_name not in failed_interfaces:
            if not verify_interface_ip(intf_name, intf_ip):
                st.error(f"Verification failed for {intf_name}")
                result = False

    # Step 5: Verify all BGP network statements are present
    st.log("Step 5: Verify all BGP network statements in running-config")
    for network in networks:
        if not verify_bgp_network_in_config(network):
            st.error(f"BGP network {network} not found in running-config")
            result = False

    # Cleanup
    st.log("Cleanup: Removing test configuration")
    for intf_name, _ in interfaces_to_config:
        st.config(vars.D1, f"no interface {intf_name}",
                 type=data.cli_type, conf=True, skip_error_check=True)
    st.config(vars.D1, f"no router bgp",
             type=data.cli_type, conf=True, skip_error_check=True)

    if result:
        st.report_tc_pass(TC_IDS.tc4, "test_case_passed",
                         "Multiple BGP networks do not block multiple interface IPs")
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


def test_sm_iscli_15_tc5_bgp_network_removal():
    """
    TC5: Verify BGP network removal does not affect interface IP

    Steps:
      1. Configure BGP router
      2. Configure interface IP first (Loopback1: 10.10.10.1/32)
      3. Configure BGP network statement (10.10.10.1/32)
      4. Verify both coexist
      5. Remove BGP network statement
      6. Verify interface IP remains configured and functional

    Expected Result:
      - BGP network removal should not affect interface IP
      - Interface IP should remain configured after BGP network is removed
    """
    st.banner("TC5: BGP network removal should not affect interface IP")

    result = True

    # Step 1: Configure BGP router
    st.log("Step 1: Configure BGP router")
    if not configure_bgp_router(data.config.bgp.as_number, data.config.bgp.router_id):
        st.report_tc_fail(TC_IDS.tc5, "bgp_config_failed", "Failed to configure BGP router")
        st.report_fail("test_case_failed")

    # Step 2: Configure interface IP first
    st.log("Step 2: Configure Loopback1 with IP 10.10.10.1/32 (interface first)")
    success, error_output = configure_loopback_interface(
        data.config.interfaces.loopback.name,
        data.config.interfaces.loopback.ip
    )

    if not success:
        st.error("Interface IP configuration failed (unexpected)")
        st.report_tc_fail(TC_IDS.tc5, "interface_ip_config_failed",
                         "Failed to configure interface IP")
        st.report_fail("test_case_failed")

    # Step 3: Configure BGP network statement
    st.log("Step 3: Configure BGP network statement 10.10.10.1/32")
    if not configure_bgp_network(data.config.bgp.as_number, data.config.bgp.networks.loopback_32):
        st.report_tc_fail(TC_IDS.tc5, "bgp_network_config_failed",
                         "Failed to configure BGP network statement")
        result = False

    # Step 4: Verify both coexist
    st.log("Step 4: Verify both configurations coexist")
    if not verify_interface_ip(data.config.interfaces.loopback.name,
                               data.config.interfaces.loopback.ip):
        st.report_tc_fail(TC_IDS.tc5, "interface_ip_verification_failed",
                         "Loopback IP verification failed before network removal")
        result = False

    if not verify_bgp_network_in_config(data.config.bgp.networks.loopback_32):
        st.report_tc_fail(TC_IDS.tc5, "bgp_network_verification_failed",
                         "BGP network statement verification failed")
        result = False

    # Step 5: Remove BGP network statement
    st.log("Step 5: Remove BGP network statement")
    if not remove_bgp_network(data.config.bgp.as_number, data.config.bgp.networks.loopback_32):
        st.report_tc_fail(TC_IDS.tc5, "bgp_network_removal_failed",
                         "Failed to remove BGP network statement")
        result = False

    # Step 6: Verify interface IP remains configured
    st.log("Step 6: Verify interface IP remains configured after BGP network removal")
    if not verify_interface_ip(data.config.interfaces.loopback.name,
                               data.config.interfaces.loopback.ip):
        st.report_tc_fail(TC_IDS.tc5, "interface_ip_verification_after_removal_failed",
                         "Loopback IP verification failed after network removal")
        result = False

    # Verify BGP network is removed
    if verify_bgp_network_in_config(data.config.bgp.networks.loopback_32):
        st.error("BGP network statement still present after removal")
        result = False

    # Cleanup
    st.log("Cleanup: Removing test configuration")
    st.config(vars.D1, f"no interface {data.config.interfaces.loopback.name}",
             type=data.cli_type, conf=True, skip_error_check=True)
    st.config(vars.D1, f"no router bgp",
             type=data.cli_type, conf=True, skip_error_check=True)

    if result:
        st.report_tc_pass(TC_IDS.tc5, "test_case_passed",
                         "BGP network removal does not affect interface IP")
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")
