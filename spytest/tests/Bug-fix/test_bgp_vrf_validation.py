"""
BGP VRF CONFIGURATION AND VALIDATION
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/bug-fix/test_bgp_vrf_validation.py \
  --logs-path ./logs/test_bgp_vrf_validation_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of BGP configuration with VRF (Virtual Routing and Forwarding)
  using sonic-cli (Klish). This test suite validates:
  - Creating VRF and BGP instance in VRF
  - Configuring BGP neighbors in both default and VRF instances
  - BGP VRF configuration appears in 'show running-configuration bgp'
  - Error handling when trying to delete default BGP with VRF BGP present
  - Correct deletion sequence: VRF BGP first, then default BGP
  - Verification that all BGP config is removed

Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - CLI type: klish (sonic-cli)

Test Steps:
  1. Create VRF (VrfAsdf)
  2. Configure BGP in VRF (router bgp 65001 vrf VrfAsdf)
  3. Configure neighbor in VRF BGP
  4. Configure default BGP (router bgp 65001)
  5. Configure neighbor in default BGP
  6. Verify both BGP instances in 'show running-configuration bgp'
  7. Try to delete default BGP (expect error)
  8. Delete VRF BGP instance
  9. Verify only default BGP remains
  10. Delete default BGP
  11. Verify all BGP config removed
"""

from __future__ import annotations

import pytest
import re

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api


# Test data dictionary
data = SpyTestDict()
data.vrf_name = "VrfAsdf"
data.bgp_asn = "65001"
data.vrf_neighbor_ip = "1.2.3.4"
data.vrf_neighbor_asn = "65002"
data.default_neighbor_ip = "10.2.2.5"
data.default_neighbor_asn = "65001"
data.cli_type = "klish"


@pytest.fixture(scope="module", autouse=True)
def bgp_vrf_validation_module_hooks(request):
    """
    Module-level fixture for BGP VRF validation test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1")

    st.banner("MODULE SETUP: BGP VRF Validation Test")

    # Store DUT handle
    data.dut1 = vars.D1

    st.log(f"DUT1: {data.dut1}")

    # INITIAL CLEANUP - Start with clean state
    st.banner("INITIAL CLEANUP: Removing existing BGP and VRF configuration")
    initial_cleanup()

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up BGP and VRF configuration")
    cleanup_bgp_vrf_config()


@pytest.fixture(scope="function", autouse=True)
def bgp_vrf_validation_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def initial_cleanup():
    """
    Initial cleanup: Remove BGP and VRF configuration.
    """
    st.log("Starting initial cleanup - removing BGP and VRF configuration")

    try:
        bgp_api.enable_docker_routing_config_mode(data.dut1, cli_type=data.cli_type)

        # Try to remove VRF BGP first
        commands = [f"no router bgp {data.bgp_asn} vrf {data.vrf_name}"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove default BGP
        commands = ["no router bgp"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove VRF
        commands = [f"no ip vrf {data.vrf_name}"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        st.log("Initial cleanup completed")
    except Exception as e:
        st.error(f"Error during initial cleanup: {str(e)}")


def create_vrf(dut, vrf_name, cli_type="klish"):
    """
    Create VRF.

    Args:
        dut: Device under test
        vrf_name: VRF name
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Creating VRF {vrf_name} on {dut}")

    try:
        commands = [f"ip vrf {vrf_name}"]
        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully created VRF {vrf_name}")
        return True
    except Exception as e:
        st.error(f"Failed to create VRF {vrf_name}: {str(e)}")
        return False


def configure_bgp_vrf(dut, asn, vrf_name, neighbor_ip, neighbor_asn, cli_type="klish"):
    """
    Configure BGP in VRF with neighbor.

    Args:
        dut: Device under test
        asn: Local BGP AS number
        vrf_name: VRF name
        neighbor_ip: Neighbor IP address
        neighbor_asn: Neighbor AS number
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP {asn} in VRF {vrf_name} with neighbor {neighbor_ip}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {asn} vrf {vrf_name}")
        commands.append(f"neighbor {neighbor_ip} remote-as {neighbor_asn}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP in VRF {vrf_name}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP in VRF: {str(e)}")
        return False


def configure_bgp_default(dut, asn, neighbor_ip, neighbor_asn, cli_type="klish"):
    """
    Configure BGP in default VRF with neighbor and address family.

    Args:
        dut: Device under test
        asn: Local BGP AS number
        neighbor_ip: Neighbor IP address
        neighbor_asn: Neighbor AS number
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring default BGP {asn} with neighbor {neighbor_ip}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {asn}")
        commands.append(f"neighbor {neighbor_ip} remote-as {neighbor_asn}")
        commands.append("address-family ipv4 unicast")
        commands.append(f"activate")
        commands.append("exit")
        commands.append("exit")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log("Successfully configured default BGP")
        return True
    except Exception as e:
        st.error(f"Failed to configure default BGP: {str(e)}")
        return False


def get_show_run_bgp(dut, cli_type="klish"):
    """
    Get BGP running configuration.

    Args:
        dut: Device under test
        cli_type: CLI type (default: klish)

    Returns:
        str: Raw output from show running-configuration bgp
    """
    st.log("Getting BGP running configuration")

    try:
        command = "show running-configuration bgp"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)
        st.log(f"Show running-config bgp output:\n{output}")
        return output
    except Exception as e:
        st.error(f"Failed to get BGP running config: {str(e)}")
        return None


def verify_bgp_vrf_in_config(output, asn, vrf_name, neighbor_ip):
    """
    Verify BGP VRF instance appears in running configuration.

    Expected format:
    router bgp 65001 vrf VrfAsdf
    neighbor 1.2.3.4 remote-as 65002

    Args:
        output: Raw output from show running-configuration bgp
        asn: BGP AS number
        vrf_name: VRF name
        neighbor_ip: Neighbor IP address

    Returns:
        bool: True if BGP VRF found, False otherwise
    """
    st.log(f"Verifying BGP {asn} VRF {vrf_name} in running config")

    if not output or not isinstance(output, str):
        st.error("No output to verify")
        return False

    # Check for BGP VRF instance
    bgp_vrf_pattern = rf'router\s+bgp\s+{asn}\s+vrf\s+{re.escape(vrf_name)}'
    if not re.search(bgp_vrf_pattern, output, re.IGNORECASE):
        st.error(f"BGP VRF instance not found: router bgp {asn} vrf {vrf_name}")
        return False

    st.log(f"Found BGP VRF instance: router bgp {asn} vrf {vrf_name}")

    # Check for neighbor in VRF context
    if neighbor_ip in output:
        st.log(f"Found neighbor {neighbor_ip} in BGP VRF config")
        return True
    else:
        st.error(f"Neighbor {neighbor_ip} not found in BGP VRF config")
        return False


def verify_bgp_default_in_config(output, asn, neighbor_ip):
    """
    Verify default BGP instance appears in running configuration.

    Expected format:
    router bgp 65001
    neighbor 10.2.2.5 remote-as 65001
      address-family ipv4 unicast
       activate

    Args:
        output: Raw output from show running-configuration bgp
        asn: BGP AS number
        neighbor_ip: Neighbor IP address

    Returns:
        bool: True if default BGP found, False otherwise
    """
    st.log(f"Verifying default BGP {asn} in running config")

    if not output or not isinstance(output, str):
        st.error("No output to verify")
        return False

    # Check for default BGP instance (without vrf keyword)
    # Look for "router bgp <asn>" not followed by "vrf"
    bgp_default_pattern = rf'router\s+bgp\s+{asn}(?!\s+vrf)'
    if not re.search(bgp_default_pattern, output, re.IGNORECASE):
        st.error(f"Default BGP instance not found: router bgp {asn}")
        return False

    st.log(f"Found default BGP instance: router bgp {asn}")

    # Check for neighbor
    if neighbor_ip in output:
        st.log(f"Found neighbor {neighbor_ip} in default BGP config")
        return True
    else:
        st.error(f"Neighbor {neighbor_ip} not found in default BGP config")
        return False


def delete_default_bgp_expect_error(dut, cli_type="klish"):
    """
    Try to delete default BGP when VRF BGP exists (expect error).

    Args:
        dut: Device under test
        cli_type: CLI type (default: klish)

    Returns:
        tuple: (bool, str) - (Error occurred, Output message)
    """
    st.log("Attempting to delete default BGP with VRF BGP present (expecting error)")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = ["no router bgp"]
        output = st.config(dut, commands, type=cli_type, skip_error_check=True)

        st.log(f"Delete BGP output:\n{output}")

        # Check if error occurred
        if output and isinstance(output, str):
            error_patterns = [
                r'error',
                r'delete\s+not\s+allowed',
                r'non-default-vrf\s+bgp',
                r'bgp-instance\s+present'
            ]

            for pattern in error_patterns:
                if re.search(pattern, output, re.IGNORECASE):
                    st.log("Expected error occurred: Delete not allowed with VRF BGP present")
                    return True, output

        st.log("No error occurred (unexpected)")
        return False, output

    except Exception as e:
        st.log(f"Exception occurred (may indicate error): {str(e)}")
        return True, str(e)


def delete_bgp_vrf(dut, asn, vrf_name, cli_type="klish"):
    """
    Delete BGP VRF instance.

    Args:
        dut: Device under test
        asn: BGP AS number
        vrf_name: VRF name
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Deleting BGP {asn} VRF {vrf_name}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = [f"no router bgp {asn} vrf {vrf_name}"]
        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully deleted BGP VRF {vrf_name}")
        return True
    except Exception as e:
        st.error(f"Failed to delete BGP VRF: {str(e)}")
        return False


def delete_default_bgp(dut, cli_type="klish"):
    """
    Delete default BGP instance.

    Args:
        dut: Device under test
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log("Deleting default BGP")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = ["no router bgp"]
        st.config(dut, commands, type=cli_type)
        st.log("Successfully deleted default BGP")
        return True
    except Exception as e:
        st.error(f"Failed to delete default BGP: {str(e)}")
        return False


def verify_no_bgp_config(dut, cli_type="klish"):
    """
    Verify no BGP configuration exists.

    Args:
        dut: Device under test
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if no BGP config, False if BGP config still exists
    """
    st.log("Verifying no BGP configuration exists")

    output = get_show_run_bgp(dut, cli_type)

    if not output:
        st.log("No output from show running-config bgp (BGP removed)")
        return True

    if isinstance(output, str):
        # Check if output is empty or contains no BGP config
        if "router bgp" not in output.lower():
            st.log("No BGP configuration found")
            return True
        else:
            st.error("BGP configuration still exists")
            return False

    st.log("BGP configuration may still exist")
    return False


def cleanup_bgp_vrf_config():
    """
    Clean up BGP and VRF configuration.
    """
    st.log("Cleaning up BGP and VRF configuration")

    try:
        bgp_api.enable_docker_routing_config_mode(data.dut1, cli_type=data.cli_type)

        # Remove VRF BGP
        commands = [f"no router bgp {data.bgp_asn} vrf {data.vrf_name}"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove default BGP
        commands = ["no router bgp"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        # Remove VRF
        commands = [f"no ip vrf {data.vrf_name}"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)

        st.log("Cleanup completed")
    except Exception as e:
        st.error(f"Error during cleanup: {str(e)}")


@pytest.mark.topology("any")
class TestBgpVrfValidation:
    """
    Test class for BGP VRF configuration validation.
    """

    @pytest.mark.test_bgp_vrf_config_delete_sequence
    def test_bgp_vrf_config_delete_sequence(self):
        """
        TestCase: test_bgp_vrf_config_delete_sequence

        Test Steps:
        1. Create VRF (VrfAsdf)
        2. Configure BGP in VRF with neighbor
        3. Configure default BGP with neighbor
        4. Verify both BGP instances in running config
        5. Try to delete default BGP (expect error)
        6. Delete VRF BGP instance
        7. Verify only default BGP remains
        8. Delete default BGP
        9. Verify all BGP config removed

        Expected Result:
        - BGP VRF and default BGP configured successfully
        - Error when trying to delete default BGP with VRF BGP present
        - VRF BGP deleted successfully
        - Default BGP deleted successfully
        - All BGP configuration removed
        """
        st.banner("TEST: BGP VRF Configuration and Deletion Sequence")

        # Step 1: Create VRF
        st.log(f"Step 1: Creating VRF {data.vrf_name}")

        if not create_vrf(data.dut1, data.vrf_name, data.cli_type):
            st.report_fail("msg", f"Failed to create VRF {data.vrf_name}")

        # Step 2: Configure BGP in VRF
        st.log(f"Step 2: Configuring BGP {data.bgp_asn} in VRF {data.vrf_name}")

        if not configure_bgp_vrf(
            data.dut1, data.bgp_asn, data.vrf_name,
            data.vrf_neighbor_ip, data.vrf_neighbor_asn, data.cli_type
        ):
            st.report_fail("msg", "Failed to configure BGP in VRF")

        # Step 3: Configure default BGP
        st.log(f"Step 3: Configuring default BGP {data.bgp_asn}")

        if not configure_bgp_default(
            data.dut1, data.bgp_asn, data.default_neighbor_ip,
            data.default_neighbor_asn, data.cli_type
        ):
            st.report_fail("msg", "Failed to configure default BGP")

        st.wait(2, "Waiting for BGP configuration to apply")

        # Step 4: Verify both BGP instances in running config
        st.log("Step 4: Verifying both BGP instances in running config")

        output = get_show_run_bgp(data.dut1, data.cli_type)

        if not output:
            st.report_fail("msg", "Failed to get BGP running configuration")

        # Verify VRF BGP
        if not verify_bgp_vrf_in_config(
            output, data.bgp_asn, data.vrf_name, data.vrf_neighbor_ip
        ):
            st.report_fail("msg", "BGP VRF instance not found in running config")

        # Verify default BGP
        if not verify_bgp_default_in_config(
            output, data.bgp_asn, data.default_neighbor_ip
        ):
            st.report_fail("msg", "Default BGP instance not found in running config")

        # Step 5: Try to delete default BGP (expect error)
        st.log("Step 5: Attempting to delete default BGP (expecting error)")

        error_occurred, error_output = delete_default_bgp_expect_error(data.dut1, data.cli_type)

        if not error_occurred:
            st.report_fail("msg", "Expected error did not occur when deleting default BGP with VRF BGP present")

        st.log("Expected error occurred: Delete not allowed with non-default VRF BGP present")

        # Step 6: Delete VRF BGP instance
        st.log(f"Step 6: Deleting BGP VRF {data.vrf_name}")

        if not delete_bgp_vrf(data.dut1, data.bgp_asn, data.vrf_name, data.cli_type):
            st.report_fail("msg", "Failed to delete BGP VRF instance")

        st.wait(2, "Waiting for VRF BGP deletion")

        # Step 7: Verify only default BGP remains
        st.log("Step 7: Verifying only default BGP remains")

        output = get_show_run_bgp(data.dut1, data.cli_type)

        if not output:
            st.report_fail("msg", "No BGP config found after VRF BGP deletion")

        # Verify default BGP still exists
        if not verify_bgp_default_in_config(output, data.bgp_asn, data.default_neighbor_ip):
            st.report_fail("msg", "Default BGP not found after VRF BGP deletion")

        # Verify VRF BGP is gone
        if f"vrf {data.vrf_name}" in output:
            st.report_fail("msg", "VRF BGP still present after deletion")

        st.log("VRF BGP successfully removed, default BGP remains")

        # Step 8: Delete default BGP
        st.log("Step 8: Deleting default BGP")

        if not delete_default_bgp(data.dut1, data.cli_type):
            st.report_fail("msg", "Failed to delete default BGP")

        st.wait(2, "Waiting for default BGP deletion")

        # Step 9: Verify all BGP config removed
        st.log("Step 9: Verifying all BGP configuration removed")

        if not verify_no_bgp_config(data.dut1, data.cli_type):
            st.report_fail("msg", "BGP configuration still exists after deletion")

        st.log("All BGP configuration successfully removed")
        st.log("BGP VRF configuration and deletion sequence test PASSED")
        st.report_pass("test_case_passed")
