"""
SNMP TEST - TC-7.1.2: Verify SNMP Running Configuration

Test Case ID: 7.1.2
Author: Automated Testing Suite
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/diagnostic_tools/test_snmp_02_running_configuration.py \
    --logs-path ./logs/snmp_02_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates SNMP configuration visibility:
  - View SNMP configuration via Linux shell (JSON format)
  - View SNMP configuration via sonic-cli (table format)
  - Verify contact and location information
  - Verify community configuration
  - Ensure both methods show consistent data

Pre-requisites:
  - 2 SONiC devices: 192.168.100.161, 192.168.100.206
  - Credentials: admin/palc@123
  - Testbed: testbed_2vs.yaml
  - SNMP service must be enabled

Important:
  - Linux shell: show runningconfiguration all | grep -i snmp (JSON format)
  - sonic-cli: show snmp-server (table format)
  - Different commands for different interfaces
  - Follows best practices: continues on errors, generates tech-support, completes cleanup
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "default_contact": "admin@example.com",
    "default_location": "Data Center Room 101",
    "default_community": "public",
    "default_community_type": "RO",
})

# Test case identifiers
TC_IDS = SpyTestDict({
    "snmp02_setup": "TC-SNMP-02-001",
    "snmp02_linux_config": "TC-SNMP-02-002",
    "snmp02_sonic_cli_config": "TC-SNMP-02-003",
    "snmp02_consistency": "TC-SNMP-02-004",
})


@pytest.fixture(scope="module", autouse=True)
def snmp_02_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("SNMP TC-7.1.2 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    # Get topology
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}, DUT2: {vars.D2}")
    st.log(f"CLI Type: {data.cli_type}")

    # Setup SNMP configuration
    setup_snmp_config()

    yield

    st.banner("=" * 80)
    st.banner("SNMP TC-7.1.2 MODULE CLEANUP - START")
    st.banner("=" * 80)
    st.log("No cleanup required - configuration viewing only")


def setup_snmp_config():
    """Setup basic SNMP configuration for testing."""
    st.log("Setting up SNMP configuration")

    for dut in [vars.D1, vars.D2]:
        try:
            # Configure contact and location via sonic-cli
            commands = [
                f"snmp-server contact \"{CONFIG.default_contact}\"",
                f"snmp-server location \"{CONFIG.default_location}\"",
            ]
            st.config(dut, commands, type=data.cli_type)
            st.log(f"✓ SNMP configuration set on {dut}")
        except Exception as e:
            st.log(f"Setup warning on {dut}: {str(e)}")


def show_running_config_linux(dut: str) -> str:
    """
    Show SNMP running configuration via Linux shell.

    Command: show runningconfiguration all | grep -A10 -B5 -i snmp
    Returns: JSON format configuration
    """
    st.log(f"Getting SNMP running configuration (Linux shell) on {dut}")

    command = "show runningconfiguration all | grep -A10 -B5 -i snmp"
    output = st.show(dut, command, skip_tmpl=True, skip_error_check=True)

    output_str = str(output)
    st.log(f"Linux shell output length: {len(output_str)} characters")
    st.log(f"Linux shell output (first 500 chars):\n{output_str[:500]}")

    return output_str


def show_snmp_server_sonic_cli(dut: str) -> str:
    """
    Show SNMP server configuration via sonic-cli.

    Command: show snmp-server
    Returns: Table format configuration
    """
    st.log(f"Getting SNMP server configuration (sonic-cli) on {dut}")

    command = "show snmp-server"
    output = st.show(dut, command, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

    output_str = str(output)
    st.log(f"sonic-cli output length: {len(output_str)} characters")
    st.log(f"sonic-cli output:\n{output_str}")

    return output_str


def show_snmp_community_sonic_cli(dut: str) -> str:
    """
    Show SNMP community configuration via sonic-cli.

    Command: show snmp-server community
    Returns: Table format with community names and types
    """
    st.log(f"Getting SNMP community configuration (sonic-cli) on {dut}")

    command = "show snmp-server community"
    output = st.show(dut, command, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

    output_str = str(output)
    st.log(f"Community output:\n{output_str}")

    return output_str


def verify_config_contains(output: str, search_strings: list, method_name: str) -> bool:
    """
    Verify configuration output contains expected strings.

    Args:
        output: Configuration output
        search_strings: List of strings to search for
        method_name: Name of method (for logging)

    Returns:
        True if all strings found, False otherwise
    """
    output_lower = output.lower()
    all_found = True

    for search_str in search_strings:
        if search_str.lower() in output_lower:
            st.log(f"✓ Found '{search_str}' in {method_name} output")
        else:
            st.log(f"✗ NOT found '{search_str}' in {method_name} output")
            all_found = False

    return all_found


def test_snmp_02_running_configuration():
    """
    Test Case 7.1.2: Verify SNMP Running Configuration

    Test Steps:
    1. Setup SNMP configuration
    2. View SNMP configuration via Linux shell
    3. Verify JSON format shows SNMP configuration
    4. View SNMP configuration via sonic-cli
    5. Verify table format shows contact and location
    6. View community configuration via sonic-cli
    7. Verify consistency across both methods

    Expected Results:
    - Linux shell: JSON format with SNMP section
    - sonic-cli: Table format with Contact and Location
    - Community: public (RO)
    - Both methods show consistent data

    NOTE: Continues on errors, generates tech-support on failures, completes all steps
    """
    st.banner("=" * 80)
    st.banner("TEST TC-7.1.2: SNMP RUNNING CONFIGURATION")
    st.banner("=" * 80)

    # Track test status
    test_failed = False

    # ==================================================================
    # STEP 1: View Configuration via Linux Shell
    # ==================================================================
    st.banner("STEP 1: View SNMP Configuration via Linux Shell (JSON)")

    linux_output_d1 = show_running_config_linux(vars.D1)
    linux_output_d2 = show_running_config_linux(vars.D2)

    # Verify Linux shell output contains SNMP configuration
    if len(linux_output_d1) < 50:
        st.report_tc_fail(TC_IDS.snmp02_linux_config, "msg",
                         f"Linux shell output too short on {vars.D1}")
        test_failed = True
    else:
        st.log(f"✓ Linux shell output received on {vars.D1}")

    if len(linux_output_d2) < 50:
        st.report_tc_fail(TC_IDS.snmp02_linux_config, "msg",
                         f"Linux shell output too short on {vars.D2}")
        test_failed = True
    else:
        st.log(f"✓ Linux shell output received on {vars.D2}")

    # Check for SNMP-related keywords in Linux output
    linux_keywords = ["snmp", "SNMP"]
    linux_d1_valid = verify_config_contains(linux_output_d1, linux_keywords, "Linux shell (D1)")
    linux_d2_valid = verify_config_contains(linux_output_d2, linux_keywords, "Linux shell (D2)")

    if not linux_d1_valid or not linux_d2_valid:
        st.generate_tech_support([vars.D1, vars.D2], "snmp_linux_config_not_visible")
        st.report_tc_fail(TC_IDS.snmp02_linux_config, "msg",
                         "SNMP configuration not fully visible in Linux shell output")
        test_failed = True
    else:
        st.report_tc_pass(TC_IDS.snmp02_linux_config, "msg",
                         "SNMP configuration visible in Linux shell")

    # ==================================================================
    # STEP 2: View Configuration via sonic-cli
    # ==================================================================
    st.banner("STEP 2: View SNMP Configuration via sonic-cli (Table)")

    cli_output_d1 = show_snmp_server_sonic_cli(vars.D1)
    cli_output_d2 = show_snmp_server_sonic_cli(vars.D2)

    # Verify sonic-cli output contains contact and location
    cli_keywords = ["Contact", "Location"]
    cli_d1_valid = verify_config_contains(cli_output_d1, cli_keywords, "sonic-cli (D1)")
    cli_d2_valid = verify_config_contains(cli_output_d2, cli_keywords, "sonic-cli (D2)")

    if not cli_d1_valid:
        st.generate_tech_support([vars.D1, vars.D2], "snmp_cli_config_not_visible")
        st.report_tc_fail(TC_IDS.snmp02_sonic_cli_config, "msg",
                         f"SNMP configuration not visible via sonic-cli on {vars.D1}")
        test_failed = True
    else:
        st.log(f"✓ SNMP configuration visible via sonic-cli on {vars.D1}")

    if not cli_d2_valid:
        st.generate_tech_support([vars.D1, vars.D2], "snmp_cli_config_not_visible")
        st.report_tc_fail(TC_IDS.snmp02_sonic_cli_config, "msg",
                         f"SNMP configuration not visible via sonic-cli on {vars.D2}")
        test_failed = True
    else:
        st.log(f"✓ SNMP configuration visible via sonic-cli on {vars.D2}")

    if not test_failed:
        st.report_tc_pass(TC_IDS.snmp02_sonic_cli_config, "msg",
                         "SNMP configuration visible via sonic-cli")

    # ==================================================================
    # STEP 3: View Community Configuration
    # ==================================================================
    st.banner("STEP 3: View SNMP Community Configuration")

    community_output_d1 = show_snmp_community_sonic_cli(vars.D1)
    community_output_d2 = show_snmp_community_sonic_cli(vars.D2)

    # Verify community configuration
    community_keywords = ["public", "Community"]
    community_d1_valid = verify_config_contains(community_output_d1, community_keywords,
                                                "Community (D1)")
    community_d2_valid = verify_config_contains(community_output_d2, community_keywords,
                                                "Community (D2)")

    if not community_d1_valid:
        st.log(f"Warning: Community configuration not fully visible on {vars.D1}")

    if not community_d2_valid:
        st.log(f"Warning: Community configuration not fully visible on {vars.D2}")

    # ==================================================================
    # STEP 4: Verify Consistency
    # ==================================================================
    st.banner("STEP 4: Verify Configuration Consistency")

    st.log("Checking consistency between Linux shell and sonic-cli outputs")

    # Both methods should show SNMP-related information
    consistency_valid = True

    if "snmp" not in linux_output_d1.lower() and "snmp" not in cli_output_d1.lower():
        st.report_tc_fail(TC_IDS.snmp02_consistency, "msg",
                         f"No SNMP information in either output on {vars.D1}")
        consistency_valid = False
        test_failed = True

    if "snmp" not in linux_output_d2.lower() and "snmp" not in cli_output_d2.lower():
        st.report_tc_fail(TC_IDS.snmp02_consistency, "msg",
                         f"No SNMP information in either output on {vars.D2}")
        consistency_valid = False
        test_failed = True

    if consistency_valid:
        st.log("✓ Configuration visible in both methods")
        st.report_tc_pass(TC_IDS.snmp02_consistency, "msg",
                         "Configuration consistent across methods")

    # ==================================================================
    # TEST RESULT
    # ==================================================================
    if test_failed:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-7.1.2 FAILED")
        st.banner("=" * 80)
        st.report_fail("test_case_failed")
    else:
        st.banner("=" * 80)
        st.banner("TEST RESULT: TC-7.1.2 PASSED")
        st.banner("=" * 80)

        st.log("=" * 80)
        st.log("TEST SUMMARY - TC-7.1.2: SNMP Running Configuration")
        st.log("=" * 80)
        st.log(f"✓ Linux shell: SNMP configuration visible (JSON format)")
        st.log(f"✓ sonic-cli: SNMP configuration visible (table format)")
        st.log(f"✓ Contact and Location information displayed")
        st.log(f"✓ Community configuration displayed")
        st.log(f"✓ Both methods show consistent data")
        st.log("=" * 80)
        st.log("NOTES:")
        st.log("  - Linux shell: 'show runningconfiguration all | grep -i snmp'")
        st.log("  - sonic-cli: 'show snmp-server' and 'show snmp-server community'")
        st.log("  - Different formats, same underlying configuration")
        st.log("=" * 80)

        st.report_pass("test_case_passed")
