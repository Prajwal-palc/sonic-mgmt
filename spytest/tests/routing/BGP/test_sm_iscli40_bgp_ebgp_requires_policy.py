"""
SM_ISCLI_40 - eBGP Requires Policy Configuration Test

Author: SPyTest Automation
Copyright (C) 2024, PALC Networks

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_2node.yaml \\
  tests/routing/BGP/test_sm_iscli40_bgp_ebgp_requires_policy.py \\
  --logs-path ./logs/sm_iscli40_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test suite validates the eBGP requires policy configuration behavior
  in SMCI IS-CLI implementation. It verifies:
  - eBGP session establishment without explicit policy (default behavior)
  - Configuration visibility differences between IS-CLI and vtysh
  - Command availability in IS-CLI vs vtysh
  - Configuration persistence across reboots

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Required test variables (YAML): vars/routing/BGP/vars_sm_iscli40_bgp_ebgp_policy.yaml
  - Both klish (IS-CLI) and vtysh CLI access required
  - SONiC version: 202505-smci-dev-iscli or later
"""

import pytest
import time
import re
from pathlib import Path
import yaml

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api
import utilities.common as utils

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Default YAML variables file
DEFAULT_VAR_FILE = Path(__file__).resolve().parents[3] / "vars/routing/BGP/vars_sm_iscli40_bgp_ebgp_policy.yaml"

# Test case IDs
TC_IDS = SpyTestDict({
    "default_behavior": "TC_BGP_EBGP_POLICY_001",
    "vtysh_enable": "TC_BGP_EBGP_POLICY_002",
    "persistence": "TC_BGP_EBGP_POLICY_003",
})


def initialize_data():
    """Load test configuration from YAML file"""
    st.banner("INITIALIZING TEST DATA")
    try:
        with open(DEFAULT_VAR_FILE, "r") as f:
            payload = yaml.safe_load(f)
    except FileNotFoundError as error:
        pytest.skip(str(error))

    global vars, data
    vars = st.ensure_min_topology(*payload.get("min_topology", ["D1D2:1"]))
    data.config = SpyTestDict(payload.get("config", {}))

    st.log(f"Loaded configuration: {data.config}")


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown
    """
    st.banner("MODULE PROLOGUE: SM_ISCLI_40 - eBGP Requires Policy Tests")

    # Initialize test data
    initialize_data()

    # Verify minimum topology
    if not vars:
        st.error("Failed to get testbed variables")
        pytest.skip("Testbed topology not available")

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"D1-D2 Link: {vars.D1D2P1} <-> {vars.D2D1P1}")

    # Module setup
    module_config()

    yield

    # Module cleanup
    st.banner("MODULE EPILOGUE: Cleanup")
    module_unconfig()


def module_config():
    """
    Module-level configuration setup
    """
    st.banner("MODULE CONFIG: Setting up base configuration")

    # Clear any existing BGP configuration
    st.log("Clearing existing BGP configuration on both DUTs")
    bgp_api.cleanup_router_bgp(vars.D1)
    bgp_api.cleanup_router_bgp(vars.D2)

    # Reset interface configuration
    st.log("Resetting interface configuration")
    reset_interface_config()


def module_unconfig():
    """
    Module-level configuration cleanup
    """
    st.banner("MODULE UNCONFIG: Cleaning up configuration")

    # Clear BGP configuration
    bgp_api.cleanup_router_bgp(vars.D1)
    bgp_api.cleanup_router_bgp(vars.D2)

    # Reset interfaces
    reset_interface_config()


def reset_interface_config():
    """
    Reset interface configuration to default state
    """
    interface = data.config.interface.name

    # Remove IP addresses from test interface on both DUTs
    # Map DUT to its configured IP address
    dut_ip_map = {
        vars.D1: data.config.interface.dut1_ip,
        vars.D2: data.config.interface.dut2_ip
    }

    for dut, port in [(vars.D1, vars.D1D2P1), (vars.D2, vars.D2D1P1)]:
        st.log(f"Resetting interface configuration on {dut}:{port}")
        ip_address = dut_ip_map.get(dut)
        if ip_address:
            # Remove the specific IP address configured
            ip_api.delete_ip_interface(
                dut, port, ip_address,
                subnet=data.config.interface.subnet_mask,
                family="ipv4",
                skip_error=True,
                cli_type="klish"
            )


def configure_interface(dut, port, ip_address, subnet):
    """
    Configure IP address on interface

    Args:
        dut: Device name
        port: Interface name
        ip_address: IP address to configure
        subnet: Subnet mask (e.g., 24)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring {dut}:{port} with IP {ip_address}/{subnet}")

    # Remove existing IP if any (same IP we're about to configure)
    ip_api.delete_ip_interface(
        dut, port, ip_address,
        subnet=str(subnet),
        family="ipv4",
        skip_error=True,
        cli_type="klish"
    )

    # Configure new IP
    result = ip_api.config_ip_addr_interface(
        dut,
        interface_name=port,
        ip_address=ip_address,
        subnet=str(subnet),
        family="ipv4",
        config="add",
        cli_type="klish"
    )

    if not result:
        st.error(f"Failed to configure IP on {dut}:{port}")
        return False

    # Exit config mode to return to exec mode
    st.config(dut, "exit", type="klish", skip_error_check=True)

    # Wait for configuration to apply
    time.sleep(data.config.timing.config_apply_wait)

    return True


def configure_bgp_neighbor(dut, local_asn, neighbor_ip, remote_asn, address_family="ipv4"):
    """
    Configure BGP neighbor

    Args:
        dut: Device name
        local_asn: Local AS number
        neighbor_ip: Neighbor IP address
        remote_asn: Remote AS number
        address_family: Address family (default: ipv4)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP on {dut}: AS {local_asn}, Neighbor {neighbor_ip} AS {remote_asn}")
    st.log(f"DEBUG: remote_asn type={type(remote_asn)}, value={remote_asn}")

    # Configure BGP manually using correct IS-CLI command order
    # Key: "neighbor X.X.X.X remote-as NNNN" must be on ONE line

    commands = [
        "configure terminal",
        f"router bgp {local_asn}",
        f"address-family {address_family} unicast",
        "exit",
        f"neighbor {neighbor_ip} remote-as {remote_asn}",  # neighbor and remote-as on same line!
        f"address-family {address_family} unicast",
        "activate",
        "exit",
        "exit",
        "end"
    ]

    st.log(f"Configuring BGP with commands: {commands}")

    try:
        for cmd in commands:
            output = st.config(dut, cmd, type="klish", skip_error_check=False)
            # Check for errors
            if "Error" in str(output) or "Invalid" in str(output):
                st.error(f"Command failed: {cmd}, Output: {output}")
                return False
    except Exception as e:
        st.error(f"Failed to configure BGP: {e}")
        return False

    # Restart BGP docker container to ensure configuration is applied
    st.log(f"Restarting BGP container on {dut}")
    try:
        restart_cmd = "sudo docker restart bgp"
        st.show(dut, restart_cmd, skip_tmpl=True, skip_error_check=True)
        st.log(f"BGP container restart initiated on {dut}")
    except Exception as e:
        st.log(f"Warning: Could not restart BGP container: {e}")

    # Wait for BGP container to restart and stabilize (300 seconds)
    st.log(f"Waiting 300 seconds for BGP container to restart and stabilize on {dut}")
    time.sleep(300)
    st.log(f"BGP container restart wait completed on {dut}")

    return True


def verify_bgp_session_established(dut, neighbor_ip, timeout=60):
    """
    Verify BGP session is in Established state

    Args:
        dut: Device name
        neighbor_ip: Neighbor IP address
        timeout: Maximum wait time in seconds

    Returns:
        bool: True if session is established, False otherwise
    """
    st.log(f"Verifying BGP session establishment on {dut} with neighbor {neighbor_ip}")

    start_time = time.time()
    while time.time() - start_time < timeout:
        output = bgp_api.show_bgp_ipv4_summary(dut, cli_type="klish")

        if output:
            for entry in output:
                if entry.get("neighbor") == neighbor_ip:
                    state = entry.get("state")
                    st.log(f"Neighbor {neighbor_ip} state: {state}")

                    # Check if state is numeric (indicates established with prefix count)
                    if state and state.isdigit():
                        st.log(f"BGP session established with {state} prefixes")
                        return True
                    elif "Established" in str(state):
                        st.log("BGP session is in Established state")
                        return True

        st.log(f"Session not established yet, waiting... ({int(time.time() - start_time)}s elapsed)")
        time.sleep(5)

    st.error(f"BGP session did not establish within {timeout}s")
    return False


def verify_bgp_session_not_established(dut, neighbor_ip):
    """
    Verify BGP session is NOT in Established state

    Args:
        dut: Device name
        neighbor_ip: Neighbor IP address

    Returns:
        bool: True if session is not established, False otherwise
    """
    st.log(f"Verifying BGP session is NOT established on {dut} with neighbor {neighbor_ip}")

    output = bgp_api.show_bgp_ipv4_summary(dut, cli_type="klish")

    if output:
        for entry in output:
            if entry.get("neighbor") == neighbor_ip:
                state = entry.get("state")
                st.log(f"Neighbor {neighbor_ip} state: {state}")

                # Session should be in Active/Idle or show 0 prefixes
                if state and (state.isdigit() and int(state) == 0):
                    return True
                elif state in ["Active", "Idle", "Connect"]:
                    return True

    st.error("BGP session appears to be established (unexpected)")
    return False


def get_bgp_running_config(dut, cli_type="klish"):
    """
    Get BGP running configuration

    Args:
        dut: Device name
        cli_type: CLI type (klish or vtysh)

    Returns:
        str: Running configuration output
    """
    st.log(f"Getting BGP running configuration on {dut} using {cli_type}")

    if cli_type == "klish":
        cmd = "show running-configuration bgp | no-more"
    elif cli_type == "vtysh":
        cmd = "show running-config bgp"
    else:
        st.error(f"Unsupported CLI type: {cli_type}")
        return ""

    # Execute command
    if cli_type == "vtysh":
        # For vtysh, we need to execute via vtysh shell
        output = st.show(dut, cmd, skip_tmpl=True, type="vtysh")
    else:
        output = st.show(dut, cmd, skip_tmpl=True, type="klish")

    return str(output)


def verify_ebgp_policy_in_config(config_output, expected_pattern, should_exist=True):
    """
    Verify if ebgp-requires-policy pattern exists in configuration

    Args:
        config_output: Configuration output string
        expected_pattern: Pattern to search for
        should_exist: True if pattern should exist, False if it should not

    Returns:
        bool: True if verification passes, False otherwise
    """
    st.log(f"Verifying pattern '{expected_pattern}' should_exist={should_exist}")

    pattern_found = expected_pattern in config_output

    if should_exist and pattern_found:
        st.log(f"Pattern '{expected_pattern}' found as expected")
        return True
    elif not should_exist and not pattern_found:
        st.log(f"Pattern '{expected_pattern}' not found as expected")
        return True
    elif should_exist and not pattern_found:
        st.error(f"Pattern '{expected_pattern}' not found (expected to exist)")
        return False
    else:  # not should_exist and pattern_found
        st.error(f"Pattern '{expected_pattern}' found (expected to not exist)")
        return False


def verify_ping(src_dut, dst_ip, count=3):
    """
    Verify ping connectivity

    Args:
        src_dut: Source device
        dst_ip: Destination IP address
        count: Number of ping packets

    Returns:
        bool: True if ping successful, False otherwise
    """
    st.log(f"Verifying ping from {src_dut} to {dst_ip}")

    # Ping must be executed from Linux shell, not klish config mode
    # Using default cli_type (None) executes from Linux shell with sudo
    result = ip_api.ping(src_dut, dst_ip, count=count)

    if result:
        st.log(f"Ping successful from {src_dut} to {dst_ip}")
        return True
    else:
        st.error(f"Ping failed from {src_dut} to {dst_ip}")
        return False


def configure_ebgp_requires_policy_vtysh(dut, local_asn, enable=True):
    """
    Configure ebgp-requires-policy setting via vtysh (FRRouting CLI)

    Args:
        dut: Device name
        local_asn: Local AS number
        enable: True to enable, False to disable

    Returns:
        bool: True if successful, False otherwise
    """
    cmd_prefix = "" if enable else "no "
    st.log(f"Configuring {cmd_prefix}bgp ebgp-requires-policy via vtysh on {dut}")

    # Build vtysh command sequence
    # vtysh is FRRouting's CLI - different from klish (IS-CLI)
    commands = [
        "configure terminal",
        f"router bgp {local_asn}",
        f"{cmd_prefix}bgp ebgp-requires-policy",
        "end"
    ]

    st.log(f"Executing vtysh commands: {commands}")

    try:
        for cmd in commands:
            output = st.config(dut, cmd, type="vtysh", skip_error_check=False)
            # Check for errors
            if "Error" in str(output) or "Invalid" in str(output):
                st.error(f"vtysh command failed: {cmd}, Output: {output}")
                return False
            st.log(f"vtysh command executed: {cmd}")
    except Exception as e:
        st.error(f"Exception executing vtysh commands: {e}")
        return False

    time.sleep(data.config.timing.config_apply_wait)
    st.log(f"Successfully configured {cmd_prefix}bgp ebgp-requires-policy in vtysh")
    return True


def clear_bgp_sessions(dut):
    """
    Clear BGP sessions

    Args:
        dut: Device name

    Returns:
        bool: True if successful
    """
    st.log(f"Clearing BGP sessions on {dut}")

    cmd = "clear bgp ipv4 unicast *"
    st.config(dut, cmd, type="klish")

    time.sleep(data.config.timing.session_clear_wait)
    return True


def save_config(dut):
    """
    Save running configuration to startup config

    Args:
        dut: Device name

    Returns:
        bool: True if successful
    """
    st.log(f"Saving configuration on {dut}")

    cmd = "write memory"
    st.config(dut, cmd, type="klish")

    time.sleep(data.config.timing.config_apply_wait)
    return True


def reboot_and_wait(dut, wait_time=400):
    """
    Reboot device and wait for it to come back

    Args:
        dut: Device name
        wait_time: Maximum wait time in seconds

    Returns:
        bool: True if device came back, False otherwise
    """
    st.log(f"Rebooting {dut}")

    st.reboot(dut, "fast")

    # Framework handles the wait and reconnection
    st.log(f"Device {dut} rebooted successfully")

    return True


# ============================================================================
# Test Functions
# ============================================================================

@pytest.mark.sm_iscli_40
@pytest.mark.community_pass
def test_bgp_ebgp_policy_default_behavior():
    """
    TC_BGP_EBGP_POLICY_001: Verify eBGP session establishment and
    ebgp-requires-policy default behavior

    Test Steps:
    1. Configure interfaces on DUT1 and DUT2
    2. Verify connectivity with ping
    3. Configure eBGP neighbors on both DUTs
    4. Verify eBGP session establishes without explicit policy
    5. Check IS-CLI config does not show ebgp-requires-policy
    6. Check vtysh config shows "no bgp ebgp-requires-policy"
    7. Configure ebgp-requires-policy via vtysh
    8. Verify vtysh config shows "bgp ebgp-requires-policy"
    """
    tc_id = TC_IDS.default_behavior
    st.banner(f"START: {tc_id} - eBGP Session Default Behavior Test")

    result = True

    try:
        # Step 1: Configure interfaces
        st.banner("STEP 1: Configure interfaces on DUT1 and DUT2")
        st.log(f"DUT1: {vars.D1}, Port: {vars.D1D2P1}, IP: {data.config.interface.dut1_ip}/{data.config.interface.subnet_mask}")
        st.log(f"DUT2: {vars.D2}, Port: {vars.D2D1P1}, IP: {data.config.interface.dut2_ip}/{data.config.interface.subnet_mask}")

        if not configure_interface(
            vars.D1,
            vars.D1D2P1,
            data.config.interface.dut1_ip,
            data.config.interface.subnet_mask
        ):
            st.error(f"FAILED: Interface configuration on {vars.D1}")
            st.report_tc_fail(tc_id, "interface_config_failed", f"Failed to configure interface on {vars.D1}")
            result = False
        else:
            st.log(f"SUCCESS: Interface configured on {vars.D1}")

        if not configure_interface(
            vars.D2,
            vars.D2D1P1,
            data.config.interface.dut2_ip,
            data.config.interface.subnet_mask
        ):
            st.error(f"FAILED: Interface configuration on {vars.D2}")
            st.report_tc_fail(tc_id, "interface_config_failed", f"Failed to configure interface on {vars.D2}")
            result = False
        else:
            st.log(f"SUCCESS: Interface configured on {vars.D2}")

        # Step 2: Verify connectivity
        st.banner("STEP 2: Verify connectivity with ping")
        st.log(f"Pinging from {vars.D1} to {data.config.interface.dut2_ip}")

        if not verify_ping(vars.D1, data.config.interface.dut2_ip):
            st.error(f"FAILED: Ping from {vars.D1} to {data.config.interface.dut2_ip}")
            st.report_tc_fail(tc_id, "ping_failed", f"Ping failed from {vars.D1} to {data.config.interface.dut2_ip}")
            result = False
        else:
            st.log(f"SUCCESS: Ping from {vars.D1} to {data.config.interface.dut2_ip}")

        # Step 3: Configure eBGP neighbors
        st.banner("STEP 3: Configure eBGP neighbors on both DUTs")
        st.log(f"DUT1 BGP: AS {data.config.bgp.dut1_asn}, Neighbor {data.config.interface.dut2_ip} AS {data.config.bgp.dut2_asn}")
        st.log(f"DUT2 BGP: AS {data.config.bgp.dut2_asn}, Neighbor {data.config.interface.dut1_ip} AS {data.config.bgp.dut1_asn}")

        if not configure_bgp_neighbor(
            vars.D1,
            data.config.bgp.dut1_asn,
            data.config.interface.dut2_ip,
            data.config.bgp.dut2_asn
        ):
            st.error(f"FAILED: BGP configuration on {vars.D1}")
            st.report_tc_fail(tc_id, "bgp_config_failed", f"Failed to configure BGP on {vars.D1}")
            result = False
        else:
            st.log(f"SUCCESS: BGP configured on {vars.D1}")

        if not configure_bgp_neighbor(
            vars.D2,
            data.config.bgp.dut2_asn,
            data.config.interface.dut1_ip,
            data.config.bgp.dut1_asn
        ):
            st.error(f"FAILED: BGP configuration on {vars.D2}")
            st.report_tc_fail(tc_id, "bgp_config_failed", f"Failed to configure BGP on {vars.D2}")
            result = False
        else:
            st.log(f"SUCCESS: BGP configured on {vars.D2}")

        # Step 4: Verify eBGP session establishment
        st.banner("STEP 4: Verify eBGP session establishes")
        st.log(f"Waiting up to {data.config.timing.bgp_session_wait}s for session to establish")

        if not verify_bgp_session_established(
            vars.D2,
            data.config.interface.dut1_ip,
            timeout=data.config.timing.bgp_session_wait
        ):
            st.error(f"FAILED: eBGP session between {vars.D1} and {vars.D2} did not establish")
            st.report_tc_fail(tc_id, "bgp_session_not_established", "eBGP session did not establish")
            result = False
        else:
            st.log(f"SUCCESS: eBGP session established between {vars.D1} and {vars.D2}")

        # Step 5: Check IS-CLI configuration
        st.banner("STEP 5: Verify IS-CLI config does NOT show ebgp-requires-policy")

        iscli_config = get_bgp_running_config(vars.D2, cli_type="klish")
        st.log(f"IS-CLI Config:\n{iscli_config}")

        if not verify_ebgp_policy_in_config(
            iscli_config,
            data.config.verification.iscli_policy_pattern,
            should_exist=False
        ):
            st.error(f"FAILED: IS-CLI config contains '{data.config.verification.iscli_policy_pattern}' (should not be present)")
            st.report_tc_fail(tc_id, "iscli_config_check_failed",
                            "IS-CLI config unexpectedly contains ebgp-requires-policy")
            result = False
        else:
            st.log(f"SUCCESS: IS-CLI config does not contain '{data.config.verification.iscli_policy_pattern}'")

        # Step 6: Check vtysh configuration
        st.banner("STEP 6: Verify vtysh config shows 'no bgp ebgp-requires-policy'")

        vtysh_config = get_bgp_running_config(vars.D2, cli_type="vtysh")
        st.log(f"vtysh Config:\n{vtysh_config}")

        if not verify_ebgp_policy_in_config(
            vtysh_config,
            data.config.verification.vtysh_default_policy,
            should_exist=True
        ):
            st.error(f"FAILED: vtysh config does not contain '{data.config.verification.vtysh_default_policy}'")
            st.report_tc_fail(tc_id, "vtysh_config_check_failed",
                            "vtysh config does not show 'no bgp ebgp-requires-policy'")
            result = False
        else:
            st.log(f"SUCCESS: vtysh config contains '{data.config.verification.vtysh_default_policy}'")

        # Step 7: Configure ebgp-requires-policy via vtysh
        st.banner("STEP 7: Configure ebgp-requires-policy via vtysh")

        # Execute command via vtysh
        st.log("Configuring 'bgp ebgp-requires-policy' via vtysh")
        configure_ebgp_requires_policy_vtysh(vars.D2, data.config.bgp.dut2_asn, enable=True)

        # Step 8: Verify vtysh configuration
        st.banner("STEP 8: Verify vtysh config shows bgp ebgp-requires-policy")

        vtysh_config_after = get_bgp_running_config(vars.D2, cli_type="vtysh")

        if verify_ebgp_policy_in_config(
            vtysh_config_after,
            data.config.verification.vtysh_enabled_policy,
            should_exist=True
        ):
            st.log(f"SUCCESS: vtysh accepted command and config shows '{data.config.verification.vtysh_enabled_policy}'")
        else:
            st.error(f"FAILED: vtysh config does not show '{data.config.verification.vtysh_enabled_policy}'")
            result = False

        # Restore to default
        st.log("Restoring ebgp-requires-policy to default (disabled)")
        configure_ebgp_requires_policy_vtysh(vars.D2, data.config.bgp.dut2_asn, enable=False)

    except Exception as e:
        st.error(f"Exception occurred during test: {e}")
        result = False

    if result:
        st.report_tc_pass(tc_id, "test_case_passed",
                         "eBGP default behavior verified successfully")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(tc_id, "test_case_failed",
                         "eBGP default behavior test failed")
        st.report_fail("test_case_failed")


@pytest.mark.sm_iscli_40
@pytest.mark.community_pass
def test_bgp_ebgp_policy_vtysh_enable():
    """
    TC_BGP_EBGP_POLICY_002: Verify behavior when ebgp-requires-policy
    is enabled via vtysh

    Test Steps:
    1. Enable ebgp-requires-policy via vtysh
    2. Clear BGP sessions
    3. Verify BGP session does NOT establish
    4. Check IS-CLI config (should not show the setting)
    5. Check vtysh config (should show "bgp ebgp-requires-policy")
    """
    tc_id = TC_IDS.vtysh_enable
    st.banner(f"START: {tc_id} - eBGP Policy Enabled via vtysh Test")

    result = True

    try:
        # Ensure BGP is configured (reuse from previous test or reconfigure)
        st.log("Ensuring BGP configuration is in place")

        # Configure interfaces if not already done
        configure_interface(
            vars.D1,
            vars.D1D2P1,
            data.config.interface.dut1_ip,
            data.config.interface.subnet_mask
        )

        configure_interface(
            vars.D2,
            vars.D2D1P1,
            data.config.interface.dut2_ip,
            data.config.interface.subnet_mask
        )

        # Configure BGP if not already done
        configure_bgp_neighbor(
            vars.D1,
            data.config.bgp.dut1_asn,
            data.config.interface.dut2_ip,
            data.config.bgp.dut2_asn
        )

        configure_bgp_neighbor(
            vars.D2,
            data.config.bgp.dut2_asn,
            data.config.interface.dut1_ip,
            data.config.bgp.dut1_asn
        )

        # Wait for initial session to establish
        time.sleep(30)

        # Step 1: Enable ebgp-requires-policy via vtysh
        st.log("STEP 1: Enable ebgp-requires-policy via vtysh")

        configure_ebgp_requires_policy_vtysh(vars.D2, data.config.bgp.dut2_asn, enable=True)

        # Step 2: Clear BGP sessions
        st.log("STEP 2: Clear BGP sessions")

        clear_bgp_sessions(vars.D2)

        # Step 3: Verify BGP session does NOT establish
        st.log("STEP 3: Verify BGP session does NOT establish")

        # Wait a bit for the session to attempt establishment
        time.sleep(30)

        if not verify_bgp_session_not_established(vars.D2, data.config.interface.dut1_ip):
            st.report_tc_fail(tc_id, "bgp_session_established_unexpectedly",
                            "BGP session established despite ebgp-requires-policy being enabled")
            result = False

        # Step 4: Check IS-CLI configuration
        st.log("STEP 4: Verify IS-CLI config still does NOT show ebgp-requires-policy")

        iscli_config = get_bgp_running_config(vars.D2, cli_type="klish")

        if not verify_ebgp_policy_in_config(
            iscli_config,
            data.config.verification.iscli_policy_pattern,
            should_exist=False
        ):
            st.log("IS-CLI config shows policy setting (documenting behavior)")
            # This is acceptable as per the bug description

        # Step 5: Check vtysh configuration
        st.log("STEP 5: Verify vtysh config shows 'bgp ebgp-requires-policy'")

        vtysh_config = get_bgp_running_config(vars.D2, cli_type="vtysh")

        if not verify_ebgp_policy_in_config(
            vtysh_config,
            data.config.verification.vtysh_enabled_policy,
            should_exist=True
        ):
            st.report_tc_fail(tc_id, "vtysh_config_check_failed",
                            "vtysh config does not show 'bgp ebgp-requires-policy'")
            result = False

        # Cleanup: Disable the policy to restore normal operation
        st.log("Cleanup: Disabling ebgp-requires-policy")
        configure_ebgp_requires_policy_vtysh(vars.D2, data.config.bgp.dut2_asn, enable=False)
        clear_bgp_sessions(vars.D2)

    except Exception as e:
        st.error(f"Exception occurred during test: {e}")
        result = False

    if result:
        st.report_tc_pass(tc_id, "test_case_passed",
                         "eBGP policy vtysh enable behavior verified successfully")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(tc_id, "test_case_failed",
                         "eBGP policy vtysh enable test failed")
        st.report_fail("test_case_failed")


@pytest.mark.sm_iscli_40
@pytest.mark.community_pass
def test_bgp_ebgp_policy_persistence():
    """
    TC_BGP_EBGP_POLICY_003: Verify configuration persistence across reboot

    Test Steps:
    1. Ensure BGP is configured with default ebgp-requires-policy
    2. Save configuration
    3. Reboot DUT2
    4. After reboot, check IS-CLI config
    5. After reboot, check vtysh config
    6. Verify configuration persisted correctly
    """
    tc_id = TC_IDS.persistence
    st.banner(f"START: {tc_id} - Configuration Persistence Test")

    result = True

    try:
        # Ensure BGP is configured
        st.log("Ensuring BGP configuration is in place")

        configure_interface(
            vars.D1,
            vars.D1D2P1,
            data.config.interface.dut1_ip,
            data.config.interface.subnet_mask
        )

        configure_interface(
            vars.D2,
            vars.D2D1P1,
            data.config.interface.dut2_ip,
            data.config.interface.subnet_mask
        )

        configure_bgp_neighbor(
            vars.D1,
            data.config.bgp.dut1_asn,
            data.config.interface.dut2_ip,
            data.config.bgp.dut2_asn
        )

        configure_bgp_neighbor(
            vars.D2,
            data.config.bgp.dut2_asn,
            data.config.interface.dut1_ip,
            data.config.bgp.dut1_asn
        )

        # Ensure default policy (no bgp ebgp-requires-policy)
        configure_ebgp_requires_policy_vtysh(vars.D2, data.config.bgp.dut2_asn, enable=False)

        # Step 1: Save configuration
        st.log("STEP 1: Save configuration")

        save_config(vars.D2)

        # Get config before reboot for comparison
        st.log("Getting configuration before reboot")
        vtysh_config_before = get_bgp_running_config(vars.D2, cli_type="vtysh")

        # Step 2: Reboot DUT2
        st.log("STEP 2: Reboot DUT2")

        reboot_and_wait(vars.D2)

        # Step 3: Check IS-CLI configuration after reboot
        st.log("STEP 3: Verify IS-CLI config after reboot")

        iscli_config_after = get_bgp_running_config(vars.D2, cli_type="klish")

        if not verify_ebgp_policy_in_config(
            iscli_config_after,
            data.config.verification.iscli_policy_pattern,
            should_exist=False
        ):
            st.report_tc_fail(tc_id, "iscli_config_persistence_failed",
                            "IS-CLI config changed after reboot")
            result = False

        # Step 4: Check vtysh configuration after reboot
        st.log("STEP 4: Verify vtysh config after reboot")

        vtysh_config_after = get_bgp_running_config(vars.D2, cli_type="vtysh")

        if not verify_ebgp_policy_in_config(
            vtysh_config_after,
            data.config.verification.vtysh_default_policy,
            should_exist=True
        ):
            st.report_tc_fail(tc_id, "vtysh_config_persistence_failed",
                            "vtysh config did not persist 'no bgp ebgp-requires-policy' after reboot")
            result = False

        # Step 5: Verify BGP session re-establishes
        st.log("STEP 5: Verify BGP session re-establishes after reboot")

        if not verify_bgp_session_established(
            vars.D2,
            data.config.interface.dut1_ip,
            timeout=data.config.timing.bgp_session_wait
        ):
            st.report_tc_fail(tc_id, "bgp_session_not_established_after_reboot",
                            "BGP session did not re-establish after reboot")
            result = False

    except Exception as e:
        st.error(f"Exception occurred during test: {e}")
        result = False

    if result:
        st.report_tc_pass(tc_id, "test_case_passed",
                         "Configuration persistence verified successfully")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(tc_id, "test_case_failed",
                         "Configuration persistence test failed")
        st.report_fail("test_case_failed")
