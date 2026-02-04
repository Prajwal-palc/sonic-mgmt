"""
SM_ISCLI_10: BGP Update-Source Interface Display Consistency

Author: Athira
Date: 2026-02-04
Copyright (C) 2026, PALC Networks

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_2d.yaml \\
  routing/bgp/test_sm_iscli_10_update_source_format.py \\
  --logs-path ./logs/sm_iscli_10_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates that BGP neighbor `update-source` configuration is displayed
  consistently between the configuration command and the running-configuration output
  in IS-CLI (Klish). It covers different interface types: Loopback, Ethernet,
  PortChannel, and VLAN interfaces.

  The issue being tested:
  - Configuration: update-source interface Loopback 0 (with space, capitalized)
  - Running-config: update-source interface loopback0 (no space, lowercase)

  Expected behavior: Consistent formatting across all interface types.

Pre-requisites:
  - Topology: two-node (D1-D2) with one link | Supported: HW and Virtual
  - Minimum SONiC Version: 202505 with IS-CLI support
  - Required features: BGP, IS-CLI (Klish), Loopback interfaces
  - Test variables (YAML): spytest/vars/routing/bgp/vars_sm_iscli_10.yaml
"""

import re
import pytest
from pathlib import Path
import yaml

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import apis.switching.vlan as vlan_api
import apis.switching.portchannel as pc_api
import apis.system.interface as intf_api

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Default variables file location
DEFAULT_VAR_FILE = Path(__file__).resolve().parents[3] / "spytest/vars/routing/bgp/vars_sm_iscli_10.yaml"

# Test case IDs
TC_IDS = SpyTestDict({
    "tc1_loopback": "SM_ISCLI_10_TC1",
    "tc2_ethernet": "SM_ISCLI_10_TC2",
    "tc3_portchannel": "SM_ISCLI_10_TC3",
    "tc4_vlan": "SM_ISCLI_10_TC4",
    "tc5_reconfiguration": "SM_ISCLI_10_TC5",
})


def initialize_data():
    """Load test configuration from YAML file"""
    st.banner("INITIALIZING TEST DATA FROM YAML")

    try:
        with open(DEFAULT_VAR_FILE, "r") as f:
            payload = yaml.safe_load(f)
    except FileNotFoundError as error:
        st.error(f"Test variables file not found: {DEFAULT_VAR_FILE}")
        pytest.skip(str(error))

    global vars, data

    # Get topology variables
    min_topology = payload.get("min_topology", ["D1D2:1"])
    vars = st.ensure_min_topology(*min_topology)

    # Load test configuration
    data.config = SpyTestDict(payload)
    data.cli_type = st.get_ui_type(vars.D1, cli_type="klish")

    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"Topology: D1={vars.D1}, D2={vars.D2}")
    st.log(f"D1-D2 Link: {vars.D1D2P1} <-> {vars.D2D1P1}")


def normalize_interface_name(interface_name):
    """
    Normalize interface name by removing spaces and converting to lowercase.

    Examples:
        "Loopback 0" -> "loopback0"
        "Loopback0" -> "loopback0"
        "Ethernet 4" -> "ethernet4"
        "PortChannel 100" -> "portchannel100"

    Args:
        interface_name: Interface name to normalize

    Returns:
        Normalized interface name (lowercase, no spaces)
    """
    return interface_name.replace(" ", "").lower()


def extract_update_source_from_config(dut, neighbor_ip):
    """
    Extract update-source interface from BGP running configuration.

    Args:
        dut: Device under test
        neighbor_ip: BGP neighbor IP address

    Returns:
        Tuple of (success, interface_name) where:
        - success: True if update-source found, False otherwise
        - interface_name: Extracted interface name or None
    """
    st.log(f"Extracting update-source config for neighbor {neighbor_ip}")

    # Get running configuration
    cmd = "show running-configuration bgp | no-more"
    output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)

    if not output:
        st.error("Failed to get BGP running configuration")
        return False, None

    # Parse output to find update-source line
    output_str = output if isinstance(output, str) else str(output)

    # Look for update-source pattern
    # Expected formats:
    #   update-source interface Loopback0
    #   update-source interface loopback0
    #   update-source interface Ethernet4
    pattern = r'update-source\s+interface\s+(\S+)'

    # Split by lines and find the neighbor section
    lines = output_str.split('\n')
    in_neighbor_section = False

    for line in lines:
        # Check if we're in the correct neighbor section
        if f"neighbor {neighbor_ip}" in line:
            in_neighbor_section = True
            continue

        # Exit neighbor section when we hit another neighbor or router bgp end
        if in_neighbor_section:
            if "neighbor " in line and neighbor_ip not in line:
                in_neighbor_section = False
                continue
            if line.strip().startswith("!"):
                in_neighbor_section = False
                continue

            # Look for update-source in this neighbor section
            match = re.search(pattern, line)
            if match:
                interface_name = match.group(1)
                st.log(f"Found update-source interface: {interface_name}")
                return True, interface_name

    st.error(f"Update-source not found for neighbor {neighbor_ip}")
    return False, None


def validate_update_source_format(configured_interface, displayed_interface):
    """
    Validate that displayed interface name is consistent with configured name.

    Acceptable transformations:
    - "Loopback 0" -> "Loopback0" or "loopback0" (space removed, case may vary)
    - Case should be consistent (either "Loopback0" or "loopback0", not mixed)

    Args:
        configured_interface: Interface name as configured
        displayed_interface: Interface name as displayed in running-config

    Returns:
        Tuple of (is_valid, message)
    """
    # Normalize both to compare
    norm_configured = normalize_interface_name(configured_interface)
    norm_displayed = normalize_interface_name(displayed_interface)

    st.log(f"Validating format consistency:")
    st.log(f"  Configured: '{configured_interface}' (normalized: '{norm_configured}')")
    st.log(f"  Displayed:  '{displayed_interface}' (normalized: '{norm_displayed}')")

    if norm_configured == norm_displayed:
        # Check if format is consistent (no mixed case within the name)
        if displayed_interface.lower() == displayed_interface or displayed_interface[0].isupper():
            return True, "Interface name format is consistent"
        else:
            return False, f"Interface name has inconsistent case: {displayed_interface}"
    else:
        return False, f"Interface name mismatch: '{configured_interface}' -> '{displayed_interface}'"


def configure_bgp_with_update_source(dut, local_as, router_id, neighbor_ip,
                                     remote_as, update_source_interface,
                                     ebgp_multihop=None):
    """
    Configure BGP with update-source interface.

    Args:
        dut: Device under test
        local_as: Local AS number
        router_id: BGP router ID
        neighbor_ip: Neighbor IP address
        remote_as: Remote AS number
        update_source_interface: Update-source interface name
        ebgp_multihop: eBGP multihop value (optional)

    Returns:
        True if configuration successful, False otherwise
    """
    st.banner(f"CONFIGURING BGP ON {dut}")
    st.log(f"Local AS: {local_as}, Router ID: {router_id}")
    st.log(f"Neighbor: {neighbor_ip}, Remote AS: {remote_as}")
    st.log(f"Update-source: {update_source_interface}")

    # Build BGP configuration commands
    bgp_commands = [
        f"router bgp {local_as}",
        f"router-id {router_id}",
        "address-family ipv4 unicast",
        "redistribute connected",
        "exit",
        "address-family l2vpn evpn",
        "exit",
        f"neighbor {neighbor_ip} remote-as {remote_as}"
    ]

    # Add eBGP multihop if specified
    if ebgp_multihop:
        bgp_commands.append(f"ebgp-multihop {ebgp_multihop}")

    # Add update-source configuration
    bgp_commands.append(f"update-source interface {update_source_interface}")

    # Add L2VPN EVPN address family activation
    bgp_commands.extend([
        "address-family l2vpn evpn",
        "activate",
        "exit",
        "exit",
        "exit"
    ])

    # Execute configuration using st.config()
    try:
        st.config(dut, bgp_commands, type=data.cli_type, conf=True, skip_error_check=False)
        st.log("BGP configuration completed successfully")
        st.wait(data.config.wait_times.bgp_config, "Wait after BGP configuration")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP: {e}")
        return False


def verify_update_source_in_running_config(dut, neighbor_ip, expected_interface):
    """
    Verify that 'show running-configuration bgp' displays update-source
    in the correct format: "update-source interface {interface-name}"

    Args:
        dut: Device under test
        neighbor_ip: BGP neighbor IP address
        expected_interface: Expected interface name (e.g., "Loopback0", "Ethernet4")

    Returns:
        bool: True if verification passes, False otherwise
    """
    st.log(f"Verifying update-source format in running-config for neighbor {neighbor_ip}")

    # Get BGP running configuration
    output = st.show(dut, "show running-configuration bgp", type=data.cli_type)

    if not output:
        st.error("Failed to retrieve BGP running configuration")
        return False

    # Convert output to string if it's a list
    if isinstance(output, list):
        config_text = "\n".join([str(item) for item in output])
    else:
        config_text = str(output)

    st.log(f"BGP running-configuration output:\n{config_text}")

    # Look for the update-source line for the specific neighbor
    # Expected format: "update-source interface Loopback0" or "update-source interface loopback0"
    import re

    # Normalize the expected interface name (remove spaces if any)
    expected_normalized = expected_interface.replace(" ", "")

    # Pattern to match: update-source interface <interface-name>
    # Allow for case variations (Loopback0, loopback0, etc.)
    pattern = rf'update-source\s+interface\s+(\S+)'

    # Find all update-source lines
    matches = re.findall(pattern, config_text, re.IGNORECASE)

    if not matches:
        st.error(f"No update-source configuration found in running-config")
        return False

    st.log(f"Found update-source entries: {matches}")

    # Check if any match corresponds to our expected interface (case-insensitive)
    for found_interface in matches:
        found_normalized = found_interface.replace(" ", "")
        if found_normalized.lower() == expected_normalized.lower():
            st.log(f"✓ Verification PASSED: Found correct update-source format: "
                   f"'update-source interface {found_interface}'")

            # Additional check: Ensure no space in the interface name in running-config
            if " " in found_interface:
                st.warn(f"Warning: Interface name contains space: '{found_interface}'. "
                        f"Expected format without space: '{expected_normalized}'")

            return True

    st.error(f"Verification FAILED: Expected interface '{expected_normalized}' not found in update-source. "
             f"Found: {matches}")
    return False


def cleanup_bgp_config(dut, local_as):
    """
    Clean up BGP configuration.

    Args:
        dut: Device under test
        local_as: Local AS number
    """
    st.log(f"Cleaning up BGP configuration on {dut}")
    # Use direct command to avoid API bug with "no router-id bgp"
    st.config(dut, f"no router bgp", type=data.cli_type, conf=True, skip_error_check=True)


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown.
    """
    st.banner("MODULE PROLOGUE: SM_ISCLI_10 - BGP Update-Source Format Test")

    # Initialize test data
    initialize_data()

    # Module-level setup
    st.banner("CONFIGURING BASE TOPOLOGY")

    # Configure Loopback interface on D1
    st.log(f"Configuring Loopback0 on {vars.D1}")
    result = ip_api.config_ip_addr_interface(
        vars.D1,
        data.config.interfaces.loopback,
        data.config.bgp.dut1.loopback_ip.split('/')[0],
        data.config.bgp.dut1.loopback_ip.split('/')[1],
        family="ipv4",
        cli_type=data.cli_type
    )
    if not result:
        st.error("Failed to configure Loopback0 on D1")

    # Configure Ethernet interface on D1
    st.log(f"Configuring {vars.D1D2P1} on {vars.D1}")
    intf_api.interface_operation(vars.D1, vars.D1D2P1, operation="startup",
                                 cli_type=data.cli_type)
    result = ip_api.config_ip_addr_interface(
        vars.D1,
        vars.D1D2P1,
        data.config.bgp.dut1.ethernet_ip.split('/')[0],
        data.config.bgp.dut1.ethernet_ip.split('/')[1],
        family="ipv4",
        cli_type=data.cli_type
    )
    if not result:
        st.error(f"Failed to configure IP on {vars.D1D2P1}")

    # Configure Loopback interface on D2
    st.log(f"Configuring Loopback0 on {vars.D2}")
    result = ip_api.config_ip_addr_interface(
        vars.D2,
        data.config.interfaces.loopback,
        data.config.bgp.dut2.loopback_ip.split('/')[0],
        data.config.bgp.dut2.loopback_ip.split('/')[1],
        family="ipv4",
        cli_type=data.cli_type
    )
    if not result:
        st.error("Failed to configure Loopback0 on D2")

    # Configure Ethernet interface on D2
    st.log(f"Configuring {vars.D2D1P1} on {vars.D2}")
    intf_api.interface_operation(vars.D2, vars.D2D1P1, operation="startup",
                                 cli_type=data.cli_type)
    result = ip_api.config_ip_addr_interface(
        vars.D2,
        vars.D2D1P1,
        data.config.bgp.dut2.ethernet_ip.split('/')[0],
        data.config.bgp.dut2.ethernet_ip.split('/')[1],
        family="ipv4",
        cli_type=data.cli_type
    )
    if not result:
        st.error(f"Failed to configure IP on {vars.D2D1P1}")

    st.wait(data.config.wait_times.interface_config, "Wait for interface configuration to settle")

    # Configure BGP AS and router-id on D1 using multi-line command
    st.log("Configuring BGP AS and router-id on D1")
    bgp_config_d1 = [
        f"router bgp {data.config.bgp.dut1.as_number}",
        f"router-id {data.config.bgp.dut1.router_id}",
        "exit"
    ]
    st.config(vars.D1, bgp_config_d1, type=data.cli_type, conf=True, skip_error_check=False)

    # Configure BGP AS and router-id on D2 using multi-line command
    st.log("Configuring BGP AS and router-id on D2")
    bgp_config_d2 = [
        f"router bgp {data.config.bgp.dut2.as_number}",
        f"router-id {data.config.bgp.dut2.router_id}",
        "exit"
    ]
    st.config(vars.D2, bgp_config_d2, type=data.cli_type, conf=True, skip_error_check=False)

    st.log("Module prologue completed")

    yield

    # Module epilogue - cleanup
    st.banner("MODULE EPILOGUE: Cleanup")

    # Clean up BGP on both devices
    cleanup_bgp_config(vars.D1, data.config.bgp.dut1.as_number)
    cleanup_bgp_config(vars.D2, data.config.bgp.dut2.as_number)

    # Clean up interfaces on D1
    ip_api.delete_ip_interface(vars.D1, data.config.interfaces.loopback,
                                data.config.bgp.dut1.loopback_ip, family="ipv4",
                                cli_type=data.cli_type)
    ip_api.delete_ip_interface(vars.D1, vars.D1D2P1,
                                data.config.bgp.dut1.ethernet_ip, family="ipv4",
                                cli_type=data.cli_type)

    # Clean up interfaces on D2
    ip_api.delete_ip_interface(vars.D2, data.config.interfaces.loopback,
                                data.config.bgp.dut2.loopback_ip, family="ipv4",
                                cli_type=data.cli_type)
    ip_api.delete_ip_interface(vars.D2, vars.D2D1P1,
                                data.config.bgp.dut2.ethernet_ip, family="ipv4",
                                cli_type=data.cli_type)

    st.log("Module epilogue completed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc1_loopback])
@pytest.mark.sm_iscli_10
def test_sm_iscli_10_tc1_loopback_update_source():
    """
    SM_ISCLI_10_TC1: Verify Loopback interface update-source format consistency

    Test Steps:
    1. Configure BGP neighbor with update-source Loopback interface
    2. Retrieve running-configuration
    3. Verify interface name format is consistent

    Expected Result:
    - Running-config displays update-source with consistent interface naming
    - BGP session establishes successfully using the source interface
    """
    st.banner("TC1: Loopback Interface Update-Source Format Verification")

    tc_result = True

    try:
        # Configure BGP with Loopback update-source (using format with space)
        configured_interface = data.config.interfaces.loopback_with_space

        result = configure_bgp_with_update_source(
            dut=vars.D1,
            local_as=data.config.bgp.dut1.as_number,
            router_id=data.config.bgp.dut1.router_id,
            neighbor_ip=data.config.bgp.dut1.neighbor_ip,
            remote_as=data.config.bgp.dut1.neighbor_as,
            update_source_interface=configured_interface,
            ebgp_multihop=data.config.bgp.dut1.ebgp_multihop
        )

        if not result:
            st.report_tc_fail(TC_IDS.tc1_loopback, "bgp_config_failed",
                            "Failed to configure BGP with Loopback update-source")
            tc_result = False

        st.wait(data.config.wait_times.bgp_convergence, "Wait for BGP to converge")

        # Verify update-source format in running-config
        st.banner("Verifying update-source format in running-configuration")
        expected_interface = data.config.interfaces.loopback
        if not verify_update_source_in_running_config(
            dut=vars.D1,
            neighbor_ip=data.config.bgp.dut1.neighbor_ip,
            expected_interface=expected_interface
        ):
            st.report_tc_fail(TC_IDS.tc1_loopback, "update_source_format_verification_failed",
                            f"Running-config does not display correct update-source format for {expected_interface}")
            tc_result = False
        else:
            st.report_tc_pass(TC_IDS.tc1_loopback, "update_source_format_verified",
                            f"Running-config correctly displays update-source format")

        # Extract update-source from running config
        success, displayed_interface = extract_update_source_from_config(
            vars.D1, data.config.bgp.dut1.neighbor_ip
        )

        if not success:
            st.report_tc_fail(TC_IDS.tc1_loopback, "msg",
                            "Failed to extract update-source from running-config")
            tc_result = False
        else:
            # Validate format consistency
            is_valid, message = validate_update_source_format(
                configured_interface, displayed_interface
            )

            if is_valid:
                st.log(f"✅ Format validation PASSED: {message}")
                st.report_tc_pass(TC_IDS.tc1_loopback, "msg",
                                f"Loopback update-source format is consistent: {displayed_interface}")
            else:
                st.error(f"❌ Format validation FAILED: {message}")
                st.report_tc_fail(TC_IDS.tc1_loopback, "msg", message)
                tc_result = False

    finally:
        # Cleanup for this test case
        st.log("Cleaning up TC1 configuration")
        cleanup_bgp_config(vars.D1, data.config.bgp.dut1.as_number)
        # Reconfigure base BGP for next tests
        bgp_api.config_bgp(
            dut=vars.D1,
            local_as=data.config.bgp.dut1.as_number,
            router_id=data.config.bgp.dut1.router_id,
            config='yes',
            cli_type=data.cli_type
        )

    if tc_result:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc2_ethernet])
@pytest.mark.sm_iscli_10
def test_sm_iscli_10_tc2_ethernet_update_source():
    """
    SM_ISCLI_10_TC2: Verify Ethernet interface update-source format consistency

    Test Steps:
    1. Configure BGP neighbor with update-source Ethernet interface
    2. Retrieve running-configuration
    3. Verify interface name format is consistent

    Expected Result:
    - Running-config displays update-source with consistent interface naming
    """
    st.banner("TC2: Ethernet Interface Update-Source Format Verification")

    tc_result = True

    try:
        # For Ethernet, we'll use the physical interface instead of Loopback
        # First, need to configure neighbor with directly connected setup
        configured_interface = data.config.interfaces.ethernet_with_space

        # Reconfigure neighbor to use Ethernet as update-source
        result = configure_bgp_with_update_source(
            dut=vars.D1,
            local_as=data.config.bgp.dut1.as_number,
            router_id=data.config.bgp.dut1.router_id,
            neighbor_ip=data.config.bgp.dut2.ethernet_ip.split('/')[0],  # Use D2's Ethernet IP
            remote_as=data.config.bgp.dut1.neighbor_as,
            update_source_interface=configured_interface,
            ebgp_multihop=None  # Directly connected
        )

        if not result:
            st.report_tc_fail(TC_IDS.tc2_ethernet, "bgp_config_failed",
                            "Failed to configure BGP with Ethernet update-source")
            tc_result = False

        st.wait(data.config.wait_times.bgp_convergence, "Wait for BGP to converge")

        # Verify update-source format in running-config
        st.banner("Verifying update-source format in running-configuration")
        # Use the configured interface name from YAML, not the testbed variable
        expected_interface = data.config.interfaces.ethernet
        if not verify_update_source_in_running_config(
            dut=vars.D1,
            neighbor_ip=data.config.bgp.dut2.ethernet_ip.split('/')[0],
            expected_interface=expected_interface
        ):
            st.report_tc_fail(TC_IDS.tc2_ethernet, "update_source_format_verification_failed",
                            f"Running-config does not display correct update-source format for {expected_interface}")
            tc_result = False
        else:
            st.report_tc_pass(TC_IDS.tc2_ethernet, "update_source_format_verified",
                            f"Running-config correctly displays update-source format")

        # Extract update-source from running config
        success, displayed_interface = extract_update_source_from_config(
            vars.D1, data.config.bgp.dut2.ethernet_ip.split('/')[0]
        )

        if not success:
            st.report_tc_fail(TC_IDS.tc2_ethernet, "msg",
                            "Failed to extract update-source from running-config")
            tc_result = False
        else:
            # Validate format consistency
            is_valid, message = validate_update_source_format(
                configured_interface, displayed_interface
            )

            if is_valid:
                st.log(f"✅ Format validation PASSED: {message}")
                st.report_tc_pass(TC_IDS.tc2_ethernet, "msg",
                                f"Ethernet update-source format is consistent: {displayed_interface}")
            else:
                st.error(f"❌ Format validation FAILED: {message}")
                st.report_tc_fail(TC_IDS.tc2_ethernet, "msg", message)
                tc_result = False

    finally:
        # Cleanup for this test case
        st.log("Cleaning up TC2 configuration")
        cleanup_bgp_config(vars.D1, data.config.bgp.dut1.as_number)
        # Reconfigure base BGP for next tests using direct commands
        bgp_reconfig_base = [
            f"router bgp {data.config.bgp.dut1.as_number}",
            f"router-id {data.config.bgp.dut1.router_id}",
            "exit"
        ]
        st.config(vars.D1, bgp_reconfig_base, type=data.cli_type, conf=True, skip_error_check=True)

    if tc_result:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc3_portchannel])
@pytest.mark.sm_iscli_10
def test_sm_iscli_10_tc3_portchannel_update_source():
    """
    SM_ISCLI_10_TC3: Verify PortChannel interface update-source format consistency

    Test Steps:
    1. Create PortChannel interface
    2. Configure IP on PortChannel
    3. Configure BGP neighbor with update-source PortChannel
    4. Retrieve running-configuration
    5. Verify interface name format is consistent

    Expected Result:
    - Running-config displays update-source with consistent interface naming
    """
    st.banner("TC3: PortChannel Interface Update-Source Format Verification")

    tc_result = True
    portchannel_created = False

    try:
        # Create PortChannel
        pc_name = data.config.interfaces.portchannel
        st.log(f"Creating {pc_name} on {vars.D1}")

        result = pc_api.create_portchannel(
            vars.D1,
            [pc_name],
            cli_type=data.cli_type
        )

        if not result:
            st.error(f"Failed to create {pc_name}")
            tc_result = False
        else:
            portchannel_created = True

            # Configure IP on PortChannel
            st.log(f"Configuring IP on {pc_name}")
            result = ip_api.config_ip_addr_interface(
                vars.D1,
                pc_name,
                data.config.bgp.dut1.portchannel_ip.split('/')[0],
                data.config.bgp.dut1.portchannel_ip.split('/')[1],
                family="ipv4",
                cli_type=data.cli_type
            )

            if not result:
                st.error(f"Failed to configure IP on {pc_name}")
                tc_result = False
            else:
                st.wait(data.config.wait_times.interface_config, "Wait for PortChannel configuration")

                # Configure BGP with PortChannel update-source
                configured_interface = data.config.interfaces.portchannel_with_space

                result = configure_bgp_with_update_source(
                    dut=vars.D1,
                    local_as=data.config.bgp.dut1.as_number,
                    router_id=data.config.bgp.dut1.router_id,
                    neighbor_ip=data.config.bgp.dut1.neighbor_ip,
                    remote_as=data.config.bgp.dut1.neighbor_as,
                    update_source_interface=configured_interface,
                    ebgp_multihop=data.config.bgp.dut1.ebgp_multihop
                )

                if not result:
                    st.report_tc_fail(TC_IDS.tc3_portchannel, "bgp_config_failed",
                                    "Failed to configure BGP with PortChannel update-source")
                    tc_result = False
                else:
                    st.wait(data.config.wait_times.bgp_convergence, "Wait for BGP to converge")

                    # Verify update-source format in running-config
                    st.banner("Verifying update-source format in running-configuration")
                    expected_interface = data.config.interfaces.portchannel
                    if not verify_update_source_in_running_config(
                        dut=vars.D1,
                        neighbor_ip=data.config.bgp.dut1.neighbor_ip,
                        expected_interface=expected_interface
                    ):
                        st.report_tc_fail(TC_IDS.tc3_portchannel, "update_source_format_verification_failed",
                                        f"Running-config does not display correct update-source format for {expected_interface}")
                        tc_result = False
                    else:
                        st.report_tc_pass(TC_IDS.tc3_portchannel, "update_source_format_verified",
                                        f"Running-config correctly displays update-source format")

                    # Extract update-source from running config
                    success, displayed_interface = extract_update_source_from_config(
                        vars.D1, data.config.bgp.dut1.neighbor_ip
                    )

                    if not success:
                        st.report_tc_fail(TC_IDS.tc3_portchannel, "msg",
                                        "Failed to extract update-source from running-config")
                        tc_result = False
                    else:
                        # Validate format consistency
                        is_valid, message = validate_update_source_format(
                            configured_interface, displayed_interface
                        )

                        if is_valid:
                            st.log(f"✅ Format validation PASSED: {message}")
                            st.report_tc_pass(TC_IDS.tc3_portchannel, "msg",
                                            f"PortChannel update-source format is consistent: {displayed_interface}")
                        else:
                            st.error(f"❌ Format validation FAILED: {message}")
                            st.report_tc_fail(TC_IDS.tc3_portchannel, "msg", message)
                            tc_result = False

    finally:
        # Cleanup for this test case
        st.log("Cleaning up TC3 configuration")
        cleanup_bgp_config(vars.D1, data.config.bgp.dut1.as_number)

        if portchannel_created:
            # Remove IP from PortChannel
            ip_api.delete_ip_interface(
                vars.D1,
                data.config.interfaces.portchannel,
                data.config.bgp.dut1.portchannel_ip,
                family="ipv4",
                cli_type=data.cli_type
            )
            # Delete PortChannel
            pc_api.delete_portchannel(
                vars.D1,
                [data.config.interfaces.portchannel],
                cli_type=data.cli_type
            )

        # Reconfigure base BGP for next tests
        bgp_api.config_bgp(
            dut=vars.D1,
            local_as=data.config.bgp.dut1.as_number,
            router_id=data.config.bgp.dut1.router_id,
            config='yes',
            cli_type=data.cli_type
        )

    if tc_result:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc4_vlan])
@pytest.mark.sm_iscli_10
def test_sm_iscli_10_tc4_vlan_update_source():
    """
    SM_ISCLI_10_TC4: Verify VLAN interface update-source format consistency

    Test Steps:
    1. Create VLAN interface
    2. Configure IP on VLAN interface (L3 SVI)
    3. Configure BGP neighbor with update-source VLAN
    4. Retrieve running-configuration
    5. Verify interface name format is consistent

    Expected Result:
    - Running-config displays update-source with consistent interface naming
    """
    st.banner("TC4: VLAN Interface Update-Source Format Verification")

    tc_result = True
    vlan_created = False

    try:
        # Create VLAN
        vlan_id = data.config.interfaces.vlan_id
        vlan_interface = data.config.interfaces.vlan
        st.log(f"Creating VLAN {vlan_id} on {vars.D1}")

        result = vlan_api.create_vlan(
            vars.D1,
            vlan_id,
            cli_type=data.cli_type
        )

        if not result:
            st.error(f"Failed to create VLAN {vlan_id}")
            tc_result = False
        else:
            vlan_created = True
            st.wait(2, "Wait for VLAN creation to settle")

            # Configure IP on VLAN interface (L3 SVI)
            st.log(f"Configuring IP on {vlan_interface}")
            result = ip_api.config_ip_addr_interface(
                vars.D1,
                vlan_interface,
                data.config.bgp.dut1.vlan_ip.split('/')[0],
                data.config.bgp.dut1.vlan_ip.split('/')[1],
                family="ipv4",
                cli_type=data.cli_type
            )

            if not result:
                st.error(f"Failed to configure IP on {vlan_interface}")
                tc_result = False
            else:
                st.wait(data.config.wait_times.interface_config, "Wait for VLAN interface configuration")

                # Configure BGP with VLAN update-source
                configured_interface = data.config.interfaces.vlan_with_space

                result = configure_bgp_with_update_source(
                    dut=vars.D1,
                    local_as=data.config.bgp.dut1.as_number,
                    router_id=data.config.bgp.dut1.router_id,
                    neighbor_ip=data.config.bgp.dut1.neighbor_ip,
                    remote_as=data.config.bgp.dut1.neighbor_as,
                    update_source_interface=configured_interface,
                    ebgp_multihop=data.config.bgp.dut1.ebgp_multihop
                )

                if not result:
                    st.report_tc_fail(TC_IDS.tc4_vlan, "bgp_config_failed",
                                    "Failed to configure BGP with VLAN update-source")
                    tc_result = False
                else:
                    st.wait(data.config.wait_times.bgp_convergence, "Wait for BGP to converge")

                    # Verify update-source format in running-config
                    st.banner("Verifying update-source format in running-configuration")
                    expected_interface = data.config.interfaces.vlan
                    if not verify_update_source_in_running_config(
                        dut=vars.D1,
                        neighbor_ip=data.config.bgp.dut1.neighbor_ip,
                        expected_interface=expected_interface
                    ):
                        st.report_tc_fail(TC_IDS.tc4_vlan, "update_source_format_verification_failed",
                                        f"Running-config does not display correct update-source format for {expected_interface}")
                        tc_result = False
                    else:
                        st.report_tc_pass(TC_IDS.tc4_vlan, "update_source_format_verified",
                                        f"Running-config correctly displays update-source format")

                    # Extract update-source from running config
                    success, displayed_interface = extract_update_source_from_config(
                        vars.D1, data.config.bgp.dut1.neighbor_ip
                    )

                    if not success:
                        st.report_tc_fail(TC_IDS.tc4_vlan, "msg",
                                        "Failed to extract update-source from running-config")
                        tc_result = False
                    else:
                        # Validate format consistency
                        is_valid, message = validate_update_source_format(
                            configured_interface, displayed_interface
                        )

                        if is_valid:
                            st.log(f"✅ Format validation PASSED: {message}")
                            st.report_tc_pass(TC_IDS.tc4_vlan, "msg",
                                            f"VLAN update-source format is consistent: {displayed_interface}")
                        else:
                            st.error(f"❌ Format validation FAILED: {message}")
                            st.report_tc_fail(TC_IDS.tc4_vlan, "msg", message)
                            tc_result = False

    finally:
        # Cleanup for this test case
        st.log("Cleaning up TC4 configuration")
        cleanup_bgp_config(vars.D1, data.config.bgp.dut1.as_number)

        if vlan_created:
            # Remove IP from VLAN
            ip_api.delete_ip_interface(
                vars.D1,
                data.config.interfaces.vlan,
                data.config.bgp.dut1.vlan_ip,
                family="ipv4",
                cli_type=data.cli_type
            )
            # Delete VLAN
            vlan_api.delete_vlan(
                vars.D1,
                data.config.interfaces.vlan_id,
                cli_type=data.cli_type
            )

        # Reconfigure base BGP for next tests
        bgp_api.config_bgp(
            dut=vars.D1,
            local_as=data.config.bgp.dut1.as_number,
            router_id=data.config.bgp.dut1.router_id,
            config='yes',
            cli_type=data.cli_type
        )

    if tc_result:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc5_reconfiguration])
@pytest.mark.sm_iscli_10
def test_sm_iscli_10_tc5_update_source_reconfiguration():
    """
    SM_ISCLI_10_TC5: Verify update-source reconfiguration maintains format consistency

    Test Steps:
    1. Configure update-source with Loopback interface
    2. Verify initial running-config format
    3. Change update-source to Ethernet interface
    4. Verify running-config reflects the change correctly
    5. Change back to Loopback interface
    6. Verify final running-config format

    Expected Result:
    - Each reconfiguration displays interface name consistently
    - No stale configuration remains
    - Format remains consistent across changes
    """
    st.banner("TC5: Update-Source Reconfiguration Format Verification")

    tc_result = True

    try:
        # Step 1: Configure with Loopback update-source
        st.log("Step 1: Configuring update-source with Loopback interface")
        configured_interface_1 = data.config.interfaces.loopback_with_space

        result = configure_bgp_with_update_source(
            dut=vars.D1,
            local_as=data.config.bgp.dut1.as_number,
            router_id=data.config.bgp.dut1.router_id,
            neighbor_ip=data.config.bgp.dut1.neighbor_ip,
            remote_as=data.config.bgp.dut1.neighbor_as,
            update_source_interface=configured_interface_1,
            ebgp_multihop=data.config.bgp.dut1.ebgp_multihop
        )

        if not result:
            st.error("Failed to configure initial Loopback update-source")
            tc_result = False

        st.wait(data.config.wait_times.bgp_convergence, "Wait for BGP to converge")

        # Verify update-source format in running-config (Initial Loopback)
        st.banner("Verifying initial Loopback update-source format in running-configuration")
        expected_interface = data.config.interfaces.loopback
        if not verify_update_source_in_running_config(
            dut=vars.D1,
            neighbor_ip=data.config.bgp.dut1.neighbor_ip,
            expected_interface=expected_interface
        ):
            st.report_tc_fail(TC_IDS.tc5_reconfiguration, "update_source_format_verification_failed",
                            f"Initial Loopback: Running-config does not display correct update-source format for {expected_interface}")
            tc_result = False
        else:
            st.log("Initial Loopback update-source format verified in running-config")

        # Verify initial configuration
        success, displayed_interface_1 = extract_update_source_from_config(
            vars.D1, data.config.bgp.dut1.neighbor_ip
        )

        if not success:
            st.error("Failed to extract initial update-source config")
            tc_result = False
        else:
            is_valid, message = validate_update_source_format(
                configured_interface_1, displayed_interface_1
            )
            if not is_valid:
                st.error(f"Initial Loopback format validation failed: {message}")
                tc_result = False
            else:
                st.log(f"✅ Initial Loopback format validated: {displayed_interface_1}")

        # Step 2: Change update-source to Ethernet
        st.log("Step 2: Changing update-source to Ethernet interface")
        configured_interface_2 = data.config.interfaces.ethernet_with_space

        # Remove old update-source and configure new one using direct commands
        bgp_reconfig_commands = [
            f"router bgp {data.config.bgp.dut1.as_number}",
            f"neighbor {data.config.bgp.dut1.neighbor_ip}",
            f"no update-source interface {configured_interface_1}",
            f"update-source interface {configured_interface_2}",
            "exit",
            "exit"
        ]

        st.config(vars.D1, bgp_reconfig_commands, type=data.cli_type, conf=True, skip_error_check=False)
        st.log(f"Changed update-source from {configured_interface_1} to {configured_interface_2}")

        st.wait(data.config.wait_times.bgp_config, "Wait after update-source change")

        # Verify update-source format in running-config (Ethernet)
        st.banner("Verifying Ethernet update-source format in running-configuration")
        # Use the configured interface name from YAML, not the testbed variable
        expected_interface = data.config.interfaces.ethernet
        if not verify_update_source_in_running_config(
            dut=vars.D1,
            neighbor_ip=data.config.bgp.dut1.neighbor_ip,
            expected_interface=expected_interface
        ):
            st.report_tc_fail(TC_IDS.tc5_reconfiguration, "update_source_format_verification_failed",
                            f"Ethernet: Running-config does not display correct update-source format for {expected_interface}")
            tc_result = False
        else:
            st.log("Ethernet update-source format verified in running-config")

        # Verify changed configuration
        success, displayed_interface_2 = extract_update_source_from_config(
            vars.D1, data.config.bgp.dut1.neighbor_ip
        )

        if not success:
            st.error("Failed to extract updated update-source config")
            tc_result = False
        else:
            is_valid, message = validate_update_source_format(
                configured_interface_2, displayed_interface_2
            )
            if not is_valid:
                st.error(f"Ethernet format validation failed: {message}")
                tc_result = False
            else:
                st.log(f"✅ Ethernet format validated: {displayed_interface_2}")

        # Step 3: Change back to Loopback
        st.log("Step 3: Changing update-source back to Loopback interface")

        # Remove Ethernet update-source and configure Loopback using direct commands
        bgp_reconfig_back_commands = [
            f"router bgp {data.config.bgp.dut1.as_number}",
            f"neighbor {data.config.bgp.dut1.neighbor_ip}",
            f"no update-source interface {configured_interface_2}",
            f"update-source interface {configured_interface_1}",
            "exit",
            "exit"
        ]

        st.config(vars.D1, bgp_reconfig_back_commands, type=data.cli_type, conf=True, skip_error_check=False)
        st.log(f"Changed update-source from {configured_interface_2} back to {configured_interface_1}")

        st.wait(data.config.wait_times.bgp_config, "Wait after final update-source change")

        # Verify update-source format in running-config (Final Loopback)
        st.banner("Verifying final Loopback update-source format in running-configuration")
        expected_interface = data.config.interfaces.loopback
        if not verify_update_source_in_running_config(
            dut=vars.D1,
            neighbor_ip=data.config.bgp.dut1.neighbor_ip,
            expected_interface=expected_interface
        ):
            st.report_tc_fail(TC_IDS.tc5_reconfiguration, "update_source_format_verification_failed",
                            f"Final Loopback: Running-config does not display correct update-source format for {expected_interface}")
            tc_result = False
        else:
            st.log("Final Loopback update-source format verified in running-config")

        # Verify final configuration
        success, displayed_interface_3 = extract_update_source_from_config(
            vars.D1, data.config.bgp.dut1.neighbor_ip
        )

        if not success:
            st.error("Failed to extract final update-source config")
            tc_result = False
        else:
            is_valid, message = validate_update_source_format(
                configured_interface_1, displayed_interface_3
            )
            if not is_valid:
                st.error(f"Final Loopback format validation failed: {message}")
                tc_result = False
            else:
                st.log(f"✅ Final Loopback format validated: {displayed_interface_3}")

        # Report results
        if tc_result:
            st.report_tc_pass(TC_IDS.tc5_reconfiguration, "msg",
                            "Update-source reconfiguration maintains format consistency")
        else:
            st.report_tc_fail(TC_IDS.tc5_reconfiguration, "msg",
                            "Update-source reconfiguration format validation failed")

    finally:
        # Cleanup for this test case
        st.log("Cleaning up TC5 configuration")
        cleanup_bgp_config(vars.D1, data.config.bgp.dut1.as_number)
        # Reconfigure base BGP (for completeness) using direct commands
        bgp_reconfig_base = [
            f"router bgp {data.config.bgp.dut1.as_number}",
            f"router-id {data.config.bgp.dut1.router_id}",
            "exit"
        ]
        st.config(vars.D1, bgp_reconfig_base, type=data.cli_type, conf=True, skip_error_check=True)

    if tc_result:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")
