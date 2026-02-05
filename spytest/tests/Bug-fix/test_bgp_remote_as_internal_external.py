"""
BGP REMOTE-AS INTERNAL AND EXTERNAL KEYWORDS
Author: Prajwal

How to run:
  ./bin/spytest  --tryssh 1  \
  --testbed ./testbeds/testbed_vs_2d.yaml  \
  tests/routing/bgp/test_bgp_remote_as_internal_external.py \
  --logs-path ./logs/test_bgp_remote_as_$(date +%F_%H%M%S) \
  --log-level debug  --skip-init-config  --ifname-type native

Description:
  End-to-end validation of BGP remote-as configuration using 'internal' and 'external'
  keywords instead of numeric AS numbers. This test verifies that:
  - 'remote-as internal' configures neighbor with same AS as local router (iBGP)
  - 'remote-as external' configures neighbor with different AS (eBGP)
  - Configuration appears correctly in 'show running-configuration bgp'

Pre-requisites:
  - Topology: 1-node minimum | Supported: HW and Virtual
  - CLI type: klish (sonic-cli)

Test Steps:
  1. Clean up any existing BGP configuration
  2. Configure BGP router with local AS
  3. Configure neighbor with 'remote-as internal'
  4. Verify 'show running-configuration bgp' shows 'remote-as internal'
  5. Remove neighbor configuration
  6. Configure neighbor with 'remote-as external'
  7. Verify 'show running-configuration bgp' shows 'remote-as external'
  8. Clean up BGP configuration
"""

from __future__ import annotations

import pytest
import re

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api


# Test data dictionary
data = SpyTestDict()
data.bgp_asn = "65001"
data.neighbor_ip = "10.2.2.1"
data.cli_type = "klish"


@pytest.fixture(scope="module", autouse=True)
def bgp_remote_as_module_hooks(request):
    """
    Module-level fixture for BGP remote-as test setup and teardown.
    """
    global vars

    # Ensure minimum topology requirement
    vars = st.ensure_min_topology("D1")

    st.banner("MODULE SETUP: BGP Remote-AS Internal/External Test")

    # Store DUT handle
    data.dut1 = vars.D1

    st.log(f"DUT1: {data.dut1}")

    # INITIAL CLEANUP - Start with clean state
    st.banner("INITIAL CLEANUP: Removing existing BGP configuration")
    initial_cleanup()

    yield

    # Module teardown
    st.banner("MODULE TEARDOWN: Cleaning up BGP configuration")
    cleanup_bgp_config()


@pytest.fixture(scope="function", autouse=True)
def bgp_remote_as_func_hooks(request):
    """
    Function-level fixture for pre and post test operations.
    """
    yield


def initial_cleanup():
    """
    Initial cleanup: Remove any existing BGP configuration.
    """
    st.log("Starting initial cleanup - removing BGP configuration")

    try:
        bgp_api.enable_docker_routing_config_mode(data.dut1, cli_type=data.cli_type)
        commands = ["no router bgp"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
        st.log("Initial cleanup completed")
    except Exception as e:
        st.error(f"Error during initial cleanup: {str(e)}")


def configure_bgp_router(dut, local_asn, cli_type="klish"):
    """
    Configure BGP router with local ASN.

    Args:
        dut: Device under test
        local_asn: Local AS number
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP router with AS {local_asn} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = [f"router bgp {local_asn}", "exit"]
        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP router on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP router on {dut}: {str(e)}")
        return False


def configure_bgp_neighbor_remote_as_keyword(dut, local_asn, neighbor_ip, remote_as_keyword, cli_type="klish"):
    """
    Configure BGP neighbor with remote-as using 'internal' or 'external' keyword.

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbor_ip: Neighbor IP address
        remote_as_keyword: 'internal' or 'external'
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring BGP neighbor {neighbor_ip} with remote-as {remote_as_keyword} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"neighbor {neighbor_ip} remote-as {remote_as_keyword}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type)
        st.log(f"Successfully configured BGP neighbor {neighbor_ip} with remote-as {remote_as_keyword}")
        return True
    except Exception as e:
        st.error(f"Failed to configure BGP neighbor on {dut}: {str(e)}")
        return False


def get_show_run_bgp(dut, cli_type="klish"):
    """
    Get BGP running configuration using 'show running-configuration bgp'.

    Args:
        dut: Device under test
        cli_type: CLI type (default: klish)

    Returns:
        str: Raw output from show running-configuration bgp command
    """
    st.log(f"Getting BGP running configuration on {dut}")

    try:
        command = "show running-configuration bgp"
        output = st.config(dut, command, type=cli_type, skip_error_check=True)
        st.log(f"Show running-config bgp output:\n{output}")
        return output
    except Exception as e:
        st.error(f"Failed to get running config bgp on {dut}: {str(e)}")
        return None


def verify_bgp_neighbor_remote_as_in_config(output, neighbor_ip, expected_remote_as):
    """
    Verify that 'show running-configuration bgp' contains neighbor with expected remote-as.

    Expected format in output:
    router bgp 65001
    neighbor 10.2.2.1 remote-as internal

    or

    router bgp 65001
    neighbor 10.2.2.1 remote-as external

    Args:
        output: Raw output from show running-configuration bgp
        neighbor_ip: Neighbor IP address
        expected_remote_as: Expected remote-as value ('internal' or 'external')

    Returns:
        bool: True if neighbor config found with expected remote-as, False otherwise
    """
    st.log(f"Verifying neighbor {neighbor_ip} remote-as {expected_remote_as} in running config")

    if not output or not isinstance(output, str):
        st.error("No output or invalid output format")
        return False

    # Pattern to match: neighbor 10.2.2.1 remote-as internal/external
    pattern = rf'neighbor\s+{re.escape(neighbor_ip)}\s+remote-as\s+{expected_remote_as}'

    if re.search(pattern, output, re.IGNORECASE):
        st.log(f"Found neighbor {neighbor_ip} with remote-as {expected_remote_as} in running config")
        return True
    else:
        st.error(f"Neighbor {neighbor_ip} with remote-as {expected_remote_as} NOT found in running config")
        st.log(f"Searched pattern: {pattern}")
        return False


def remove_bgp_neighbor(dut, local_asn, neighbor_ip, cli_type="klish"):
    """
    Remove BGP neighbor configuration.

    Args:
        dut: Device under test
        local_asn: Local AS number
        neighbor_ip: Neighbor IP address
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Removing BGP neighbor {neighbor_ip} on {dut}")

    try:
        bgp_api.enable_docker_routing_config_mode(dut, cli_type=cli_type)

        commands = []
        commands.append(f"router bgp {local_asn}")
        commands.append(f"no neighbor {neighbor_ip}")
        commands.append("exit")

        st.config(dut, commands, type=cli_type, skip_error_check=True)
        st.log(f"Successfully removed BGP neighbor {neighbor_ip}")
        return True
    except Exception as e:
        st.error(f"Failed to remove BGP neighbor on {dut}: {str(e)}")
        return False


def cleanup_bgp_config():
    """
    Clean up BGP configuration.
    """
    st.log("Cleaning up BGP configuration")

    try:
        bgp_api.enable_docker_routing_config_mode(data.dut1, cli_type=data.cli_type)
        commands = ["no router bgp"]
        st.config(data.dut1, commands, type=data.cli_type, skip_error_check=True)
        st.log("Cleanup completed")
    except Exception as e:
        st.error(f"Error during cleanup: {str(e)}")


@pytest.mark.topology("any")
class TestBgpRemoteAsInternalExternal:
    """
    Test class for BGP remote-as internal/external keyword validation.
    """

    @pytest.mark.test_bgp_remote_as_internal
    def test_bgp_remote_as_internal(self):
        """
        TestCase: test_bgp_remote_as_internal

        Test Steps:
        1. Configure BGP router with local AS 65001
        2. Configure neighbor with 'remote-as internal'
        3. Verify 'show running-configuration bgp' displays 'remote-as internal'
        4. Clean up neighbor configuration

        Expected Result:
        - Neighbor configured with 'remote-as internal'
        - Running config shows 'neighbor X.X.X.X remote-as internal'
        """
        st.banner("TEST: BGP Remote-AS Internal Keyword")

        # Step 1: Configure BGP router
        st.log(f"Step 1: Configuring BGP router with AS {data.bgp_asn}")

        if not configure_bgp_router(data.dut1, data.bgp_asn, data.cli_type):
            st.report_fail("msg", "Failed to configure BGP router")

        # Step 2: Configure neighbor with remote-as internal
        st.log(f"Step 2: Configuring neighbor {data.neighbor_ip} with remote-as internal")

        if not configure_bgp_neighbor_remote_as_keyword(
            data.dut1, data.bgp_asn, data.neighbor_ip, "internal", data.cli_type
        ):
            st.report_fail("msg", "Failed to configure BGP neighbor with remote-as internal")

        # Wait for configuration to apply
        st.wait(2, "Waiting for configuration to apply")

        # Step 3: Verify running configuration
        st.log("Step 3: Verifying 'show running-configuration bgp' shows remote-as internal")

        output = get_show_run_bgp(data.dut1, data.cli_type)

        if not output:
            st.report_fail("msg", "Failed to get BGP running configuration")

        if not verify_bgp_neighbor_remote_as_in_config(output, data.neighbor_ip, "internal"):
            st.report_fail("msg", "BGP neighbor remote-as internal not found in running config")

        st.log("Successfully verified neighbor configured with remote-as internal")

        # Step 4: Clean up neighbor
        st.log("Step 4: Cleaning up neighbor configuration")

        remove_bgp_neighbor(data.dut1, data.bgp_asn, data.neighbor_ip, data.cli_type)

        st.report_pass("test_case_passed")


    @pytest.mark.test_bgp_remote_as_external
    def test_bgp_remote_as_external(self):
        """
        TestCase: test_bgp_remote_as_external

        Test Steps:
        1. Configure BGP router with local AS 65001 (if not already configured)
        2. Configure neighbor with 'remote-as external'
        3. Verify 'show running-configuration bgp' displays 'remote-as external'
        4. Clean up neighbor configuration

        Expected Result:
        - Neighbor configured with 'remote-as external'
        - Running config shows 'neighbor X.X.X.X remote-as external'
        """
        st.banner("TEST: BGP Remote-AS External Keyword")

        # Step 1: Configure BGP router (may already be configured from previous test)
        st.log(f"Step 1: Configuring BGP router with AS {data.bgp_asn}")

        if not configure_bgp_router(data.dut1, data.bgp_asn, data.cli_type):
            st.report_fail("msg", "Failed to configure BGP router")

        # Step 2: Configure neighbor with remote-as external
        st.log(f"Step 2: Configuring neighbor {data.neighbor_ip} with remote-as external")

        if not configure_bgp_neighbor_remote_as_keyword(
            data.dut1, data.bgp_asn, data.neighbor_ip, "external", data.cli_type
        ):
            st.report_fail("msg", "Failed to configure BGP neighbor with remote-as external")

        # Wait for configuration to apply
        st.wait(2, "Waiting for configuration to apply")

        # Step 3: Verify running configuration
        st.log("Step 3: Verifying 'show running-configuration bgp' shows remote-as external")

        output = get_show_run_bgp(data.dut1, data.cli_type)

        if not output:
            st.report_fail("msg", "Failed to get BGP running configuration")

        if not verify_bgp_neighbor_remote_as_in_config(output, data.neighbor_ip, "external"):
            st.report_fail("msg", "BGP neighbor remote-as external not found in running config")

        st.log("Successfully verified neighbor configured with remote-as external")

        # Step 4: Clean up neighbor
        st.log("Step 4: Cleaning up neighbor configuration")

        remove_bgp_neighbor(data.dut1, data.bgp_asn, data.neighbor_ip, data.cli_type)

        st.report_pass("test_case_passed")


    @pytest.mark.test_bgp_remote_as_internal_to_external
    def test_bgp_remote_as_internal_to_external_change(self):
        """
        TestCase: test_bgp_remote_as_internal_to_external_change

        Test Steps:
        1. Configure BGP router with local AS 65001
        2. Configure neighbor with 'remote-as internal'
        3. Verify running config shows 'remote-as internal'
        4. Change neighbor to 'remote-as external'
        5. Verify running config now shows 'remote-as external'
        6. Clean up configuration

        Expected Result:
        - Can change from internal to external
        - Running config reflects the change
        """
        st.banner("TEST: BGP Remote-AS Change from Internal to External")

        # Step 1: Configure BGP router
        st.log(f"Step 1: Configuring BGP router with AS {data.bgp_asn}")

        if not configure_bgp_router(data.dut1, data.bgp_asn, data.cli_type):
            st.report_fail("msg", "Failed to configure BGP router")

        # Step 2: Configure neighbor with remote-as internal
        st.log(f"Step 2: Configuring neighbor {data.neighbor_ip} with remote-as internal")

        if not configure_bgp_neighbor_remote_as_keyword(
            data.dut1, data.bgp_asn, data.neighbor_ip, "internal", data.cli_type
        ):
            st.report_fail("msg", "Failed to configure BGP neighbor with remote-as internal")

        st.wait(2, "Waiting for configuration to apply")

        # Step 3: Verify running config shows internal
        st.log("Step 3: Verifying running config shows remote-as internal")

        output = get_show_run_bgp(data.dut1, data.cli_type)

        if not output:
            st.report_fail("msg", "Failed to get BGP running configuration")

        if not verify_bgp_neighbor_remote_as_in_config(output, data.neighbor_ip, "internal"):
            st.report_fail("msg", "BGP neighbor remote-as internal not found in running config")

        # Step 4: Change to remote-as external
        st.log(f"Step 4: Changing neighbor {data.neighbor_ip} to remote-as external")

        if not configure_bgp_neighbor_remote_as_keyword(
            data.dut1, data.bgp_asn, data.neighbor_ip, "external", data.cli_type
        ):
            st.report_fail("msg", "Failed to change BGP neighbor to remote-as external")

        st.wait(2, "Waiting for configuration to apply")

        # Step 5: Verify running config shows external
        st.log("Step 5: Verifying running config now shows remote-as external")

        output = get_show_run_bgp(data.dut1, data.cli_type)

        if not output:
            st.report_fail("msg", "Failed to get BGP running configuration after change")

        if not verify_bgp_neighbor_remote_as_in_config(output, data.neighbor_ip, "external"):
            st.report_fail("msg", "BGP neighbor remote-as external not found in running config after change")

        st.log("Successfully verified remote-as changed from internal to external")

        # Step 6: Clean up
        st.log("Step 6: Cleaning up configuration")

        remove_bgp_neighbor(data.dut1, data.bgp_asn, data.neighbor_ip, data.cli_type)

        st.report_pass("test_case_passed")
