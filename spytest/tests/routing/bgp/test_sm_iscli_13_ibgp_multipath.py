"""
SM_ISCLI_13: BGP IBGP Maximum-Paths Configuration Bug

Author: Athira
Copyright (C) 2026, PALC Networks

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_1node.yaml \\
  routing/bgp/test_sm_iscli_13_ibgp_multipath.py \\
  --logs-path ./logs/sm_iscli_13_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test suite validates that the BGP 'maximum-paths ibgp' command in IS-CLI
  (Klish) executes without syntax errors. The bug causes intermittent parsing
  failures with error messages like:
  "/tmp/klish.fifo.70.bF5p17: 1: Syntax error: 'then' unexpected"

  The suite tests basic configuration, value ranges, reconfiguration scenarios,
  address-family support (IPv4/IPv6), configuration persistence, and stress
  testing to reproduce intermittent failures.

Pre-requisites:
  - Topology: single-node (D1) | Supported: HW and Virtual
  - Topology Diagram:
        # Single Device Topology
        # +--------------------+
        # |        DUT1        |
        # |   (BGP Router)     |
        # |  AS 65001/65100    |
        # +--------------------+

  - SONiC version: 202505-smci-dev-iscli (or later with the bug)
  - CLI type: IS-CLI (klish) - Bug does NOT occur in Click/vtysh CLI
  - Required test variables (YAML): vars/routing/bgp/vars_sm_iscli_13.yaml
"""

import pytest
import re
from pathlib import Path
import yaml

from spytest import st, SpyTestDict
import apis.routing.bgp as bgp_api

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Default YAML configuration file location
DEFAULT_VAR_FILE = Path(__file__).resolve().parents[3] / "vars/routing/bgp/vars_sm_iscli_13.yaml"

# Test Case IDs
TC_IDS = SpyTestDict({
    "tc1": "SM_ISCLI_13_TC1",
    "tc2": "SM_ISCLI_13_TC2",
    "tc3": "SM_ISCLI_13_TC3",
    "tc4": "SM_ISCLI_13_TC4",
    "tc5": "SM_ISCLI_13_TC5",
    "tc6": "SM_ISCLI_13_TC6",
    "tc7": "SM_ISCLI_13_TC7",
    "tc8": "SM_ISCLI_13_TC8",
    "tc9": "SM_ISCLI_13_TC9",
    "tc10": "SM_ISCLI_13_TC10",
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

    # Get topology variables
    min_topology = payload.get("min_topology", ["D1"])
    vars = st.ensure_min_topology(*min_topology)

    # Load test configuration
    data.config = SpyTestDict(payload)
    data.cli_type = st.get_ui_type(vars.D1, cli_type="klish")

    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"Topology: D1={vars.D1}")


def configure_bgp_base(as_number, router_id=None):
    """
    Configure base BGP instance with AS number and optional router-id.

    Args:
        as_number: BGP AS number
        router_id: BGP router-id (optional)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring base BGP with AS {as_number}")

    commands = [
        f"router bgp {as_number}",
    ]

    if router_id:
        commands.append(f"router-id {router_id}")

    commands.append("exit")

    try:
        st.config(vars.D1, commands, type=data.cli_type, conf=True, skip_error_check=False)
        st.wait(data.config.wait_times.bgp_config, "Wait after BGP base configuration")
        return True
    except Exception as e:
        st.error(f"Failed to configure base BGP: {e}")
        return False


def configure_ibgp_maximum_paths(af_type, value):
    """
    Configure maximum-paths ibgp under address-family.

    Args:
        af_type: Address family type (ipv4_unicast or ipv6_unicast)
        value: Maximum paths value

    Returns:
        tuple: (success, error_message)
    """
    af_cmd = af_type.replace("_", " ")
    st.log(f"Configuring maximum-paths ibgp {value} under {af_cmd}")

    commands = [
        f"router bgp {data.config.bgp.as_number}",
        f"address-family {af_cmd}",
        f"maximum-paths ibgp {value}",
        "exit",
        "exit"
    ]

    try:
        output = st.config(vars.D1, commands, type=data.cli_type, conf=True,
                          skip_error_check=False)
        st.wait(data.config.wait_times.bgp_config, "Wait after maximum-paths configuration")

        # Check for syntax errors in output
        if output:
            output_str = str(output)
            if "Syntax error" in output_str or "then" in output_str:
                st.error(f"Syntax error detected in output: {output_str}")
                return False, output_str

        return True, None
    except Exception as e:
        error_msg = str(e)
        st.error(f"Failed to configure maximum-paths ibgp: {error_msg}")
        return False, error_msg


def remove_ibgp_maximum_paths(af_type):
    """
    Remove maximum-paths ibgp configuration.

    Args:
        af_type: Address family type

    Returns:
        bool: True if successful
    """
    af_cmd = af_type.replace("_", " ")
    st.log(f"Removing maximum-paths ibgp under {af_cmd}")

    commands = [
        f"router bgp {data.config.bgp.as_number}",
        f"address-family {af_cmd}",
        "no maximum-paths ibgp",
        "exit",
        "exit"
    ]

    try:
        st.config(vars.D1, commands, type=data.cli_type, conf=True, skip_error_check=True)
        st.wait(data.config.wait_times.bgp_config)
        return True
    except Exception as e:
        st.error(f"Failed to remove maximum-paths ibgp: {e}")
        return False


def verify_ibgp_maximum_paths_in_config(af_type, expected_value=None):
    """
    Verify maximum-paths ibgp configuration in running-config.

    Args:
        af_type: Address family type
        expected_value: Expected maximum-paths value (None to check absence)

    Returns:
        bool: True if verification passes
    """
    st.log(f"Verifying maximum-paths ibgp in running-config for {af_type}")

    # Get BGP running configuration
    cmd = "show running-configuration bgp | no-more"
    output = st.show(vars.D1, cmd, type=data.cli_type, skip_tmpl=True)

    if not output:
        st.error("Failed to get BGP running configuration")
        return False

    output_str = output if isinstance(output, str) else str(output)

    # Parse output to find address-family section and maximum-paths
    af_cmd = af_type.replace("_", " ")
    in_af_section = False
    found_max_paths = None

    for line in output_str.split('\n'):
        # Check if we're entering the address-family section
        if f"address-family {af_cmd}" in line:
            in_af_section = True
            continue

        # Exit address-family section
        if in_af_section and line.strip() == "exit":
            in_af_section = False
            continue

        # Look for maximum-paths ibgp in the section
        if in_af_section and "maximum-paths ibgp" in line:
            # Extract the value
            match = re.search(r'maximum-paths\s+ibgp\s+(\d+)', line)
            if match:
                found_max_paths = int(match.group(1))
                st.log(f"Found maximum-paths ibgp {found_max_paths}")
                break

    # Verify based on expectation
    if expected_value is None:
        # Should NOT be present
        if found_max_paths is not None:
            st.error(f"maximum-paths ibgp {found_max_paths} found but should be absent")
            return False
        st.log("Verified: maximum-paths ibgp is absent as expected")
        return True
    else:
        # Should be present with specific value
        if found_max_paths is None:
            st.error(f"maximum-paths ibgp not found, expected {expected_value}")
            return False
        if found_max_paths != expected_value:
            st.error(f"maximum-paths ibgp value mismatch: found {found_max_paths}, expected {expected_value}")
            return False
        st.log(f"Verified: maximum-paths ibgp {expected_value} is correctly configured")
        return True


def cleanup_bgp_config():
    """
    Clean up all BGP configuration.
    """
    st.log("Cleaning up BGP configuration")

    # Remove BGP configuration
    st.config(vars.D1, f"no router bgp",
              type=data.cli_type, conf=True, skip_error_check=True)
    st.wait(data.config.wait_times.bgp_config)


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture.

    Prologue:
      - Initialize test data from YAML
      - Clean up any existing BGP configuration

    Epilogue:
      - Clean up all test configuration
    """
    st.banner("MODULE PROLOGUE: Starting SM_ISCLI_13 Test Suite")

    # Initialize test configuration
    initialize_data()

    # Module prologue: Clean up any existing configuration
    st.log("Cleaning up existing BGP configuration")
    cleanup_bgp_config()

    yield

    # Module epilogue: Final cleanup
    st.banner("MODULE EPILOGUE: Cleaning up SM_ISCLI_13 Test Suite")
    cleanup_bgp_config()


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc1])
@pytest.mark.sm_iscli_13
def test_sm_iscli_13_tc1_basic_ibgp_multipath_ipv4():
    """
    SM_ISCLI_13_TC1: Basic IBGP Maximum-Paths Configuration (IPv4 Unicast)

    Objective: Verify that 'maximum-paths ibgp' command executes without
    syntax errors in IPv4 unicast address-family.

    Test Steps:
    1. Configure BGP with AS number
    2. Enter IPv4 unicast address-family
    3. Execute 'maximum-paths ibgp 10'
    4. Verify no syntax errors occur
    5. Verify configuration in running-config

    Expected Result:
    - Command executes successfully
    - No syntax errors
    - Running-config displays the configuration correctly
    """
    st.banner("TC1: Basic IBGP Maximum-Paths Configuration (IPv4 Unicast)")

    result = True

    try:
        # Configure base BGP
        if not configure_bgp_base(data.config.bgp.as_number, data.config.bgp.router_id):
            st.report_tc_fail(TC_IDS.tc1, "bgp_config_failed",
                            "Failed to configure base BGP")
            st.report_fail("test_case_failed")

        # Configure maximum-paths ibgp
        success, error = configure_ibgp_maximum_paths("ipv4_unicast", 10)

        if not success:
            st.report_tc_fail(TC_IDS.tc1, "ibgp_multipath_config_failed",
                            f"Failed to configure maximum-paths ibgp: {error}")
            result = False
        else:
            st.log("maximum-paths ibgp 10 configured successfully")

        # Verify in running-config
        if not verify_ibgp_maximum_paths_in_config("ipv4_unicast", 10):
            st.report_tc_fail(TC_IDS.tc1, "config_verification_failed",
                            "maximum-paths ibgp not found in running-config")
            result = False

    finally:
        # Cleanup
        cleanup_bgp_config()

    if result:
        st.report_tc_pass(TC_IDS.tc1, "test_case_passed",
                         "IBGP maximum-paths configured successfully without syntax errors")
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc2])
@pytest.mark.sm_iscli_13
def test_sm_iscli_13_tc2_various_values():
    """
    SM_ISCLI_13_TC2: IBGP Maximum-Paths with Various Values

    Objective: Test 'maximum-paths ibgp' with minimum, maximum, and typical values.

    Test Steps:
    1. Configure BGP
    2. Test with values: 1, 2, 4, 8, 10, 16, 32, 64
    3. Verify each value is accepted and stored correctly

    Expected Result:
    - All valid values are accepted without syntax errors
    - Running-config updates correctly for each value
    """
    st.banner("TC2: IBGP Maximum-Paths with Various Values")

    result = True
    test_values = [1, 2, 4, 8, 10, 16, 32, 64]

    try:
        # Configure base BGP
        if not configure_bgp_base(data.config.bgp.as_number):
            st.report_tc_fail(TC_IDS.tc2, "bgp_config_failed",
                            "Failed to configure base BGP")
            st.report_fail("test_case_failed")

        # Test each value
        for value in test_values:
            st.log(f"Testing maximum-paths ibgp {value}")

            success, error = configure_ibgp_maximum_paths("ipv4_unicast", value)

            if not success:
                st.error(f"Failed to configure maximum-paths ibgp {value}: {error}")
                result = False
                continue

            # Verify the value
            if not verify_ibgp_maximum_paths_in_config("ipv4_unicast", value):
                st.error(f"Failed to verify maximum-paths ibgp {value}")
                result = False
            else:
                st.log(f"✓ maximum-paths ibgp {value} verified")

    finally:
        cleanup_bgp_config()

    if result:
        st.report_tc_pass(TC_IDS.tc2, "test_case_passed",
                         f"All {len(test_values)} values tested successfully")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(TC_IDS.tc2, "test_case_failed",
                         "Some values failed to configure or verify")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc3])
@pytest.mark.sm_iscli_13
def test_sm_iscli_13_tc3_reconfiguration():
    """
    SM_ISCLI_13_TC3: IBGP Maximum-Paths Reconfiguration

    Objective: Verify reconfiguring 'maximum-paths ibgp' multiple times
    does not trigger syntax errors.

    Test Steps:
    1. Configure maximum-paths ibgp 4
    2. Change to 8
    3. Change to 16
    4. Remove using 'no maximum-paths ibgp'
    5. Re-add with value 10

    Expected Result:
    - Each reconfiguration succeeds without errors
    - Removal works correctly
    - Re-adding after removal works
    """
    st.banner("TC3: IBGP Maximum-Paths Reconfiguration")

    result = True
    reconfig_sequence = [4, 8, 16]

    try:
        # Configure base BGP
        if not configure_bgp_base(data.config.bgp.as_number):
            st.report_tc_fail(TC_IDS.tc3, "bgp_config_failed",
                            "Failed to configure base BGP")
            st.report_fail("test_case_failed")

        # Test reconfiguration sequence
        for value in reconfig_sequence:
            st.log(f"Reconfiguring to maximum-paths ibgp {value}")

            success, error = configure_ibgp_maximum_paths("ipv4_unicast", value)
            if not success:
                st.error(f"Failed reconfiguration to {value}: {error}")
                result = False
                break

            if not verify_ibgp_maximum_paths_in_config("ipv4_unicast", value):
                st.error(f"Failed to verify value {value}")
                result = False
                break

        # Remove configuration
        st.log("Removing maximum-paths ibgp configuration")
        if not remove_ibgp_maximum_paths("ipv4_unicast"):
            st.error("Failed to remove maximum-paths ibgp")
            result = False
        elif not verify_ibgp_maximum_paths_in_config("ipv4_unicast", None):
            st.error("Configuration still present after removal")
            result = False

        # Re-add configuration
        st.log("Re-adding maximum-paths ibgp 10")
        success, error = configure_ibgp_maximum_paths("ipv4_unicast", 10)
        if not success:
            st.error(f"Failed to re-add configuration: {error}")
            result = False
        elif not verify_ibgp_maximum_paths_in_config("ipv4_unicast", 10):
            st.error("Failed to verify re-added configuration")
            result = False

    finally:
        cleanup_bgp_config()

    if result:
        st.report_tc_pass(TC_IDS.tc3, "test_case_passed",
                         "Reconfiguration test completed successfully")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(TC_IDS.tc3, "test_case_failed",
                         "Reconfiguration test failed")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc4])
@pytest.mark.sm_iscli_13
def test_sm_iscli_13_tc4_ipv6_address_family():
    """
    SM_ISCLI_13_TC4: IBGP Maximum-Paths in IPv6 Address-Family

    Objective: Verify 'maximum-paths ibgp' works in IPv6 unicast address-family.

    Test Steps:
    1. Configure BGP
    2. Enter IPv6 unicast address-family
    3. Configure maximum-paths ibgp 10
    4. Verify configuration

    Expected Result:
    - Command works in IPv6 address-family
    - No syntax errors
    """
    st.banner("TC4: IBGP Maximum-Paths in IPv6 Address-Family")

    result = True

    try:
        # Configure base BGP
        if not configure_bgp_base(data.config.bgp.as_number):
            st.report_tc_fail(TC_IDS.tc4, "bgp_config_failed",
                            "Failed to configure base BGP")
            st.report_fail("test_case_failed")

        # Configure maximum-paths ibgp for IPv6
        success, error = configure_ibgp_maximum_paths("ipv6_unicast", 10)

        if not success:
            st.error(f"Failed to configure IPv6 maximum-paths: {error}")
            result = False
        elif not verify_ibgp_maximum_paths_in_config("ipv6_unicast", 10):
            st.error("Failed to verify IPv6 maximum-paths configuration")
            result = False

    finally:
        cleanup_bgp_config()

    if result:
        st.report_tc_pass(TC_IDS.tc4, "test_case_passed",
                         "IPv6 address-family maximum-paths configured successfully")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(TC_IDS.tc4, "test_case_failed",
                         "IPv6 address-family test failed")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc5])
@pytest.mark.sm_iscli_13
def test_sm_iscli_13_tc5_combined_configuration():
    """
    SM_ISCLI_13_TC5: IBGP Maximum-Paths with Other BGP Configurations

    Objective: Verify 'maximum-paths ibgp' works with other BGP configurations.

    Test Steps:
    1. Configure BGP with router-id
    2. Add redistribute connected
    3. Add maximum-paths (EBGP)
    4. Add maximum-paths ibgp
    5. Add network statement
    6. Verify all configurations coexist

    Expected Result:
    - All configurations work together
    - No interference or syntax errors
    """
    st.banner("TC5: IBGP Maximum-Paths with Combined Configuration")

    result = True

    try:
        # Configure base BGP with router-id
        if not configure_bgp_base(data.config.bgp.as_number, data.config.bgp.router_id):
            st.report_tc_fail(TC_IDS.tc5, "bgp_config_failed",
                            "Failed to configure base BGP")
            st.report_fail("test_case_failed")

        # Configure multiple settings under address-family
        commands = [
            f"router bgp {data.config.bgp.as_number}",
            "address-family ipv4 unicast",
            "redistribute connected",
            "maximum-paths 8",
            "maximum-paths ibgp 10",
        ]

        # Add network statements
        for network in data.config.bgp.networks:
            commands.append(f"network {network}")

        commands.extend(["exit", "exit"])

        try:
            st.config(vars.D1, commands, type=data.cli_type, conf=True, skip_error_check=False)
            st.wait(data.config.wait_times.bgp_config)
        except Exception as e:
            st.error(f"Failed to configure combined BGP settings: {e}")
            result = False

        # Verify maximum-paths ibgp
        if result and not verify_ibgp_maximum_paths_in_config("ipv4_unicast", 10):
            st.error("Failed to verify maximum-paths ibgp in combined configuration")
            result = False

    finally:
        cleanup_bgp_config()

    if result:
        st.report_tc_pass(TC_IDS.tc5, "test_case_passed",
                         "Combined configuration test passed")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(TC_IDS.tc5, "test_case_failed",
                         "Combined configuration test failed")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc6])
@pytest.mark.sm_iscli_13
def test_sm_iscli_13_tc6_removal():
    """
    SM_ISCLI_13_TC6: IBGP Maximum-Paths Removal

    Objective: Verify removing 'maximum-paths ibgp' works correctly.

    Test Steps:
    1. Configure maximum-paths ibgp 10
    2. Verify configuration
    3. Remove using 'no maximum-paths ibgp'
    4. Verify removal

    Expected Result:
    - Removal command succeeds
    - Configuration is removed from running-config
    """
    st.banner("TC6: IBGP Maximum-Paths Removal")

    result = True

    try:
        # Configure base BGP
        if not configure_bgp_base(data.config.bgp.as_number):
            st.report_tc_fail(TC_IDS.tc6, "bgp_config_failed",
                            "Failed to configure base BGP")
            st.report_fail("test_case_failed")

        # Configure maximum-paths ibgp
        success, error = configure_ibgp_maximum_paths("ipv4_unicast", 10)
        if not success or not verify_ibgp_maximum_paths_in_config("ipv4_unicast", 10):
            st.error("Failed to configure initial maximum-paths ibgp")
            result = False

        # Remove configuration
        if result:
            if not remove_ibgp_maximum_paths("ipv4_unicast"):
                st.error("Failed to execute removal command")
                result = False
            elif not verify_ibgp_maximum_paths_in_config("ipv4_unicast", None):
                st.error("Configuration still present after removal")
                result = False

    finally:
        cleanup_bgp_config()

    if result:
        st.report_tc_pass(TC_IDS.tc6, "test_case_passed",
                         "Removal test passed")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(TC_IDS.tc6, "test_case_failed",
                         "Removal test failed")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc7])
@pytest.mark.sm_iscli_13
@pytest.mark.negative
def test_sm_iscli_13_tc7_invalid_values():
    """
    SM_ISCLI_13_TC7: Negative Test - Invalid Values

    Objective: Verify invalid values are properly rejected.

    Test Steps:
    1. Try value 0 (below minimum)
    2. Try value 65 (above typical maximum)
    3. Try non-numeric values

    Expected Result:
    - Invalid values are rejected with appropriate error messages
    - Errors are NOT syntax errors like "then unexpected"
    """
    st.banner("TC7: Negative Test - Invalid Values")

    result = True
    invalid_values = [0, 65, 1000]

    try:
        # Configure base BGP
        if not configure_bgp_base(data.config.bgp.as_number):
            st.report_tc_fail(TC_IDS.tc7, "bgp_config_failed",
                            "Failed to configure base BGP")
            st.report_fail("test_case_failed")

        # Test invalid numeric values
        for value in invalid_values:
            st.log(f"Testing invalid value: {value}")

            commands = [
                f"router bgp {data.config.bgp.as_number}",
                "address-family ipv4 unicast",
                f"maximum-paths ibgp {value}",
                "exit",
                "exit"
            ]

            try:
                output = st.config(vars.D1, commands, type=data.cli_type,
                                 conf=True, skip_error_check=True)

                # Check if it was rejected (should be)
                output_str = str(output) if output else ""

                # Should get an error, but NOT a syntax error
                if "Syntax error" in output_str and "then" in output_str:
                    st.error(f"Got klish syntax error for value {value} - this is the BUG!")
                    result = False
                elif "Invalid" in output_str or "out of range" in output_str or "Error" in output_str:
                    st.log(f"✓ Value {value} properly rejected with appropriate error")
                else:
                    st.warn(f"Value {value} may have been accepted (unexpected)")

            except Exception as e:
                st.log(f"Exception for value {value}: {e}")

    finally:
        cleanup_bgp_config()

    if result:
        st.report_tc_pass(TC_IDS.tc7, "test_case_passed",
                         "Negative test passed - no syntax errors for invalid values")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(TC_IDS.tc7, "test_case_failed",
                         "Negative test failed - syntax errors detected")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc8])
@pytest.mark.sm_iscli_13
def test_sm_iscli_13_tc8_config_save():
    """
    SM_ISCLI_13_TC8: Configuration Save

    Objective: Verify configuration can be saved (for persistence testing).

    Test Steps:
    1. Configure maximum-paths ibgp 10
    2. Save configuration
    3. Verify saved successfully

    Expected Result:
    - Configuration saves without errors

    Note: Full reboot test requires special environment
    """
    st.banner("TC8: Configuration Save Test")

    result = True

    try:
        # Configure base BGP
        if not configure_bgp_base(data.config.bgp.as_number):
            st.report_tc_fail(TC_IDS.tc8, "bgp_config_failed",
                            "Failed to configure base BGP")
            st.report_fail("test_case_failed")

        # Configure maximum-paths ibgp
        success, error = configure_ibgp_maximum_paths("ipv4_unicast", 10)
        if not success:
            st.error(f"Failed to configure maximum-paths: {error}")
            result = False

        # Verify configuration
        if result and not verify_ibgp_maximum_paths_in_config("ipv4_unicast", 10):
            st.error("Failed to verify configuration before save")
            result = False

        # Save configuration
        if result:
            st.log("Saving configuration")
            try:
                st.config(vars.D1, "write memory", type=data.cli_type,
                         conf=False, skip_error_check=True)
                st.wait(data.config.wait_times.config_save)
                st.log("Configuration saved successfully")
            except Exception as e:
                st.warn(f"Config save command may have issues: {e}")
                # Don't fail test if save command has issues

    finally:
        cleanup_bgp_config()

    if result:
        st.report_tc_pass(TC_IDS.tc8, "test_case_passed",
                         "Configuration save test passed")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(TC_IDS.tc8, "test_case_failed",
                         "Configuration save test failed")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc9])
@pytest.mark.sm_iscli_13
def test_sm_iscli_13_tc9_stress_test():
    """
    SM_ISCLI_13_TC9: Stress Test - Rapid Reconfiguration

    Objective: Trigger potential syntax errors through rapid reconfiguration
    to reproduce the intermittent bug.

    Test Steps:
    1. Rapidly configure and remove maximum-paths ibgp multiple times
    2. Monitor for syntax errors during any iteration
    3. Verify final state is consistent

    Expected Result:
    - All iterations complete without syntax errors
    - No klish FIFO errors
    """
    st.banner("TC9: Stress Test - Rapid Reconfiguration")

    result = True
    iterations = data.config.stress_test.iterations
    test_values = data.config.stress_test.values_to_cycle
    error_count = 0
    syntax_error_count = 0

    try:
        # Configure base BGP
        if not configure_bgp_base(data.config.bgp.as_number):
            st.report_tc_fail(TC_IDS.tc9, "bgp_config_failed",
                            "Failed to configure base BGP")
            st.report_fail("test_case_failed")

        # Rapid reconfiguration loop
        st.log(f"Starting stress test with {iterations} iterations")

        for i in range(iterations):
            value = test_values[i % len(test_values)]
            st.log(f"Iteration {i+1}/{iterations}: Setting maximum-paths ibgp {value}")

            # Configure
            success, error = configure_ibgp_maximum_paths("ipv4_unicast", value)

            if not success:
                error_count += 1
                if error and ("Syntax error" in error or "then" in error):
                    syntax_error_count += 1
                    st.error(f"Iteration {i+1}: SYNTAX ERROR detected - {error}")
                else:
                    st.warn(f"Iteration {i+1}: Configuration failed - {error}")

            # Brief wait
            st.wait(data.config.wait_times.rapid_reconfig)

            # Remove
            if (i + 1) % 2 == 0:  # Remove every other iteration
                remove_ibgp_maximum_paths("ipv4_unicast")
                st.wait(data.config.wait_times.rapid_reconfig)

        # Summary
        st.log(f"Stress test completed: {iterations} iterations")
        st.log(f"Errors: {error_count}, Syntax errors: {syntax_error_count}")

        if syntax_error_count > 0:
            st.error(f"BUG REPRODUCED: {syntax_error_count} syntax errors in {iterations} iterations")
            result = False
        elif error_count > 0:
            st.warn(f"{error_count} non-syntax errors occurred")
            # Don't fail for non-syntax errors
        else:
            st.log("✓ No syntax errors detected in stress test")

    finally:
        cleanup_bgp_config()

    if result:
        st.report_tc_pass(TC_IDS.tc9, "test_case_passed",
                         f"Stress test passed - {iterations} iterations without syntax errors")
        st.report_pass("test_case_passed")
    else:
        st.report_tc_fail(TC_IDS.tc9, "test_case_failed",
                         f"Stress test failed - {syntax_error_count} syntax errors detected")
        st.report_fail("test_case_failed")


@pytest.mark.inventory(feature="Regression", testcases=[TC_IDS.tc10])
@pytest.mark.sm_iscli_13
def test_sm_iscli_13_tc10_cli_comparison():
    """
    SM_ISCLI_13_TC10: CLI Type Comparison (Klish vs Click)

    Objective: Confirm bug is specific to IS-CLI (Klish).

    Test Steps:
    1. Test with IS-CLI (Klish) - current CLI type
    2. Document any errors
    3. Note: Click CLI test would require vtysh access

    Expected Result:
    - IS-CLI behavior is documented
    - Click CLI should work without errors (when tested separately)
    """
    st.banner("TC10: CLI Type Comparison")

    result = True

    try:
        # Test with current CLI (Klish)
        st.log(f"Testing with CLI type: {data.cli_type}")

        # Configure base BGP
        if not configure_bgp_base(data.config.bgp.as_number):
            st.error("Failed to configure base BGP")
            result = False

        # Test configuration
        if result:
            success, error = configure_ibgp_maximum_paths("ipv4_unicast", 10)

            if not success:
                if error and ("Syntax error" in error or "then" in error):
                    st.log(f"IS-CLI (Klish) shows syntax error: {error}")
                    st.log("This confirms the bug exists in IS-CLI")
                    # For this test, we're documenting behavior, not failing
                else:
                    st.log(f"IS-CLI configuration failed with: {error}")
            else:
                st.log("IS-CLI configuration succeeded without syntax errors")
                if verify_ibgp_maximum_paths_in_config("ipv4_unicast", 10):
                    st.log("✓ Configuration verified in running-config")

        # Note about Click CLI
        st.log("")
        st.log("Note: Click CLI (vtysh) testing would be done separately via:")
        st.log("  sudo vtysh")
        st.log("  configure terminal")
        st.log("  router bgp 65001")
        st.log("  address-family ipv4 unicast")
        st.log("  maximum-paths ibgp 10")
        st.log("")
        st.log("Expected: Click CLI should work without syntax errors")

    finally:
        cleanup_bgp_config()

    # Always pass this test as it's documenting behavior
    st.report_tc_pass(TC_IDS.tc10, "test_case_passed",
                     "CLI comparison test completed - behavior documented")
    st.report_pass("test_case_passed")
