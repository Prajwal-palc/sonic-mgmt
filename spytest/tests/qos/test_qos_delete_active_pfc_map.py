"""
QoS Test Case 4.25.15 - Delete Active PFC Map

Test ID: 4.25.15
Feature: QoS
Test Case: Verify deletion behavior of active PFC_PRIORITY maps
Test Objective: Validate system behavior when attempting to delete a PFC-Priority-PG
                map that is actively applied to an interface with priority-flow-control enabled

Author: Automated Test Generation
Copyright (C) 2024, PALC Networks

How to run:
  ./bin/spytest --testbed ./testbeds/testbed_vs_1node.yaml \\
  qos/test_qos_delete_active_pfc_map.py \\
  --logs-path ./logs/qos_delete_pfc_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  This test validates the system behavior when attempting to delete a PFC-Priority-PG
  map that is actively applied to an interface with priority-flow-control enabled.
  The test verifies whether the system properly prevents deletion of in-use QoS maps
  or handles the deletion gracefully without creating inconsistent states.

Test Procedure:
  1. Configure PFC-Priority-PG map with priority-to-PG mappings
  2. Associate map with interface
  3. Enable priority-flow-control on specific priorities
  4. Verify QoS map and interface configuration
  5. Attempt deletion of active QoS map
  6. Verify system behavior (blocked or graceful handling)
  7. Check for inconsistent state (interface referencing non-existent map)
  8. Reconfigure map to validate recovery

Expected Behavior:
  System should either:
  - Block deletion with error message indicating map is in use, OR
  - Gracefully handle deletion by removing interface bindings first, OR
  - Disable PFC on affected interfaces before allowing map deletion

Pre-requisites:
  - Topology: Single DUT | Supported: HW and Virtual
  - PFC/QoS support required
  - Klish CLI mode required
  - Required test variables (YAML): vars/qos/vars_qos_delete_active_pfc_map.yaml
"""

import pytest
from pathlib import Path
import yaml

from spytest import st, SpyTestDict

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test case IDs
TC_IDS = SpyTestDict({
    "pfc_map_create": "TC-QOS-4.25.15-001",
    "pfc_map_apply": "TC-QOS-4.25.15-002",
    "pfc_enable": "TC-QOS-4.25.15-003",
    "delete_active_map": "TC-QOS-4.25.15-004",
    "verify_consistency": "TC-QOS-4.25.15-005",
    "recovery_test": "TC-QOS-4.25.15-006",
})

# Default YAML configuration file path
DEFAULT_VAR_FILE = Path(__file__).resolve().parents[2] / "vars/qos/vars_qos_delete_active_pfc_map.yaml"


def initialize_data() -> None:
    """Load test configuration from YAML file"""
    st.banner("INITIALIZING TEST DATA")

    try:
        with open(DEFAULT_VAR_FILE, "r") as f:
            payload = yaml.safe_load(f)
    except FileNotFoundError as error:
        st.error(f"Configuration file not found: {DEFAULT_VAR_FILE}")
        pytest.skip(str(error))
    except yaml.YAMLError as error:
        st.error(f"Error parsing YAML configuration: {error}")
        pytest.skip(str(error))

    global vars, data

    # Get topology requirements
    min_topology = payload.get("min_topology", ["D1"])
    vars = st.ensure_min_topology(*min_topology)

    # Store all configuration in data object
    data.config = SpyTestDict(payload)

    # Extract commonly used values
    data.pfc_map_name = data.config.get("pfc_map_name", "pfc_pg_map")
    data.pfc_mappings = data.config.get("pfc_mappings", {})
    data.test_interface = data.config.get("test_interface", "Ethernet8")
    data.pfc_priorities = data.config.get("pfc_priorities", [3, 4])
    data.cli_type = data.config.get("cli_type", "klish")
    data.expect_deletion_blocked = data.config.get("expect_deletion_blocked", False)
    data.verify_running_config = data.config.get("verify_running_config", True)

    st.log(f"Test Configuration Loaded:")
    st.log(f"  PFC Map Name: {data.pfc_map_name}")
    st.log(f"  Test Interface: {data.test_interface}")
    st.log(f"  PFC Priorities: {data.pfc_priorities}")
    st.log(f"  PFC Mappings: {data.pfc_mappings}")
    st.log(f"  Expect Deletion Blocked: {data.expect_deletion_blocked}")


def configure_pfc_map(dut, map_name, mappings, cli_type="klish"):
    """
    Configure PFC-Priority-PG map

    Args:
        dut: Device Under Test
        map_name: Name of the PFC map
        mappings: Dictionary of {priorities: pg} mappings
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Configuring PFC-Priority-PG map '{map_name}' on {dut}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            commands = [f"qos map pfc-priority-pg {map_name}"]
            for priorities, pg in mappings.items():
                commands.append(f"pfc-priority {priorities} pg {pg}")
            commands.append("exit")
            st.config(dut, commands, type=cli_type)
            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to configure PFC map: {e}")
        return False


def delete_pfc_map(dut, map_name, cli_type="klish", expect_error=False):
    """
    Delete PFC-Priority-PG map

    Args:
        dut: Device Under Test
        map_name: Name of the PFC map to delete
        cli_type: CLI type (default: klish)
        expect_error: If True, expects deletion to fail (default: False)

    Returns:
        tuple: (success, error_occurred) where:
            - success: True if operation completed as expected
            - error_occurred: True if an error was encountered during deletion
    """
    st.log(f"Attempting to delete PFC-Priority-PG map '{map_name}' on {dut}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            command = f"no qos map pfc-priority-pg {map_name}"

            # Execute command with skip_error_check to capture any errors
            output = st.config(dut, command, type=cli_type, skip_error_check=True)
            output_str = str(output)

            # Check if error occurred
            error_indicators = ["Error", "Failed", "cannot delete", "in use", "not allowed"]
            error_occurred = any(indicator.lower() in output_str.lower() for indicator in error_indicators)

            if error_occurred:
                st.log(f"Deletion encountered error: {output_str}")
                if expect_error:
                    st.log("Error expected and received - PASS")
                    return (True, True)
                else:
                    st.warn(f"Unexpected error during deletion: {output_str}")
                    return (False, True)
            else:
                st.log("Deletion command accepted without error")
                if expect_error:
                    st.warn("Expected error but deletion was accepted")
                    return (False, False)
                else:
                    return (True, False)
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return (False, False)
    except Exception as e:
        st.error(f"Exception during PFC map deletion: {e}")
        if expect_error:
            return (True, True)
        return (False, True)


def apply_pfc_map_to_interface(dut, interface, map_name, cli_type="klish"):
    """
    Apply PFC-Priority-PG map to interface

    Args:
        dut: Device Under Test
        interface: Interface name
        map_name: Name of the PFC map
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Applying PFC map '{map_name}' to interface {interface} on {dut}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            commands = [
                f"interface {interface}",
                f"qos-map pfc-priority-pg {map_name}",
                "exit"
            ]
            st.config(dut, commands, type=cli_type)
            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to apply PFC map to interface: {e}")
        return False


def enable_pfc_priorities(dut, interface, priorities, cli_type="klish"):
    """
    Enable priority-flow-control on specific priorities

    Args:
        dut: Device Under Test
        interface: Interface name
        priorities: List of priorities to enable
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Enabling PFC priorities {priorities} on interface {interface}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            commands = [f"interface {interface}"]

            # Enable PFC for each priority
            priority_str = ",".join(map(str, priorities))
            commands.append(f"priority-flow-control priority {priority_str}")
            commands.append("exit")

            st.config(dut, commands, type=cli_type)
            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to enable PFC priorities: {e}")
        return False


def verify_pfc_map_exists(dut, map_name, cli_type="klish"):
    """
    Verify if PFC-Priority-PG map exists in configuration

    Args:
        dut: Device Under Test
        map_name: Name of the PFC map
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if map exists, False otherwise
    """
    st.log(f"Verifying PFC-Priority-PG map '{map_name}' exists on {dut}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            # Ensure we're in exec mode for show commands
            st.config(dut, "end", type=cli_type, skip_error_check=True, conf=False)

            command = "show qos map pfc-priority-pg"
            output = st.show(dut, command, type=cli_type, skip_error_check=True)
            output_str = str(output)

            # Check if map name appears in output
            map_exists = map_name in output_str
            st.log(f"PFC map '{map_name}' exists: {map_exists}")
            return map_exists
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to verify PFC map: {e}")
        return False


def verify_interface_pfc_map(dut, interface, map_name, cli_type="klish"):
    """
    Verify if interface references the PFC map

    Args:
        dut: Device Under Test
        interface: Interface name
        map_name: Name of the PFC map
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if interface references the map, False otherwise
    """
    st.log(f"Verifying interface {interface} references PFC map '{map_name}'")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            # Ensure we're in exec mode for show commands
            st.config(dut, "end", type=cli_type, skip_error_check=True, conf=False)

            command = f"show qos interface {interface}"
            output = st.show(dut, command, type=cli_type, skip_error_check=True)
            output_str = str(output)

            # Check if map name appears in interface output
            map_referenced = map_name in output_str
            st.log(f"Interface {interface} references '{map_name}': {map_referenced}")
            return map_referenced
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed to verify interface PFC map: {e}")
        return False


def cleanup_pfc_configuration(dut, interface, map_name, priorities, cli_type="klish"):
    """
    Clean up PFC configuration

    Args:
        dut: Device Under Test
        interface: Interface name
        map_name: Name of the PFC map
        priorities: List of priorities to disable
        cli_type: CLI type (default: klish)

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"Cleaning up PFC configuration on {dut}")
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    try:
        if cli_type == "klish":
            commands = [f"interface {interface}"]

            # Disable PFC priorities
            priority_str = ",".join(map(str, priorities))
            commands.append(f"no priority-flow-control priority {priority_str}")

            # Remove QoS map
            commands.append(f"no qos-map pfc-priority-pg {map_name}")
            commands.append("exit")

            st.config(dut, commands, type=cli_type, skip_error_check=True)

            # Delete the map
            delete_command = f"no qos map pfc-priority-pg {map_name}"
            st.config(dut, delete_command, type=cli_type, skip_error_check=True)

            return True
        else:
            st.error(f"Unsupported CLI type: {cli_type}")
            return False
    except Exception as e:
        st.error(f"Failed during cleanup: {e}")
        return False


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level fixture for setup and teardown
    """
    st.banner("MODULE PROLOGUE: Starting QoS Delete Active PFC Map Test")

    # Initialize test data
    initialize_data()

    # Verify DUT is accessible
    st.log(f"Verifying DUT {vars.D1} is accessible")

    # Note: QoS/PFC feature support will be validated through actual CLI commands
    # No explicit feature check needed as unsupported commands will fail naturally

    # Module setup complete
    st.log("Module prologue completed successfully")

    yield

    # Module epilogue - cleanup
    st.banner("MODULE EPILOGUE: Cleaning up QoS Delete Active PFC Map Test")

    try:
        cleanup_pfc_configuration(
            vars.D1,
            data.test_interface,
            data.pfc_map_name,
            data.pfc_priorities,
            data.cli_type
        )
        st.log("Cleanup completed successfully")
    except Exception as e:
        st.warn(f"Cleanup encountered error (non-fatal): {e}")


@pytest.mark.qos
@pytest.mark.pfc
@pytest.mark.community_pass
def test_qos_delete_active_pfc_map():
    """
    Test Case 4.25.15: Verify deletion behavior of active PFC_PRIORITY maps

    This test validates the system behavior when attempting to delete a PFC-Priority-PG
    map that is actively applied to an interface with priority-flow-control enabled.
    """
    st.banner("TEST CASE 4.25.15: Delete Active PFC Map")

    tc_result = True

    try:
        # Step 1: Configure PFC-Priority-PG map
        st.banner("Step 1: Configure PFC-Priority-PG Map")
        st.log(f"Creating PFC map '{data.pfc_map_name}' with mappings: {data.pfc_mappings}")

        if not configure_pfc_map(vars.D1, data.pfc_map_name, data.pfc_mappings, data.cli_type):
            st.error("Failed to configure PFC map")
            st.report_fail("test_case_failed", TC_IDS.pfc_map_create)

        st.report_tc_pass(TC_IDS.pfc_map_create, "msg", "PFC map configured successfully")

        # Step 2: Apply map to interface
        st.banner("Step 2: Apply PFC Map to Interface")
        st.log(f"Applying PFC map '{data.pfc_map_name}' to interface {data.test_interface}")

        if not apply_pfc_map_to_interface(vars.D1, data.test_interface, data.pfc_map_name, data.cli_type):
            st.error("Failed to apply PFC map to interface")
            st.report_fail("test_case_failed", TC_IDS.pfc_map_apply)

        st.report_tc_pass(TC_IDS.pfc_map_apply, "msg", "PFC map applied to interface successfully")

        # Step 3: Enable priority-flow-control
        st.banner("Step 3: Enable Priority-Flow-Control")
        st.log(f"Enabling PFC priorities {data.pfc_priorities} on interface {data.test_interface}")

        if not enable_pfc_priorities(vars.D1, data.test_interface, data.pfc_priorities, data.cli_type):
            st.error("Failed to enable PFC priorities")
            st.report_fail("test_case_failed", TC_IDS.pfc_enable)

        st.report_tc_pass(TC_IDS.pfc_enable, "msg", "PFC priorities enabled successfully")

        # Step 4: Verify configuration before deletion
        st.banner("Step 4: Verify QoS Configuration Before Deletion")

        # Ensure we're in exec mode for show commands
        st.config(vars.D1, "end", type=data.cli_type, skip_error_check=True, conf=False)

        st.log("Displaying PFC map configuration:")
        output = st.show(vars.D1, "show qos map pfc-priority-pg", type=data.cli_type, skip_error_check=True)
        st.log(f"PFC Maps:\n{output}")

        st.log(f"Displaying interface {data.test_interface} QoS configuration:")
        output = st.show(vars.D1, f"show qos interface {data.test_interface}", type=data.cli_type, skip_error_check=True)
        st.log(f"Interface QoS Config:\n{output}")

        # Verify map exists
        if not verify_pfc_map_exists(vars.D1, data.pfc_map_name, data.cli_type):
            st.error("PFC map verification failed before deletion attempt")
            tc_result = False

        # Verify interface references map
        if not verify_interface_pfc_map(vars.D1, data.test_interface, data.pfc_map_name, data.cli_type):
            st.error("Interface PFC map reference verification failed")
            tc_result = False

        # Step 5: Attempt deletion of active QoS map
        st.banner("Step 5: Attempt Deletion of Active QoS Map (CRITICAL TEST)")
        st.log("This is the critical test step to verify deletion behavior")
        st.log(f"Expecting deletion to be blocked: {data.expect_deletion_blocked}")

        success, error_occurred = delete_pfc_map(
            vars.D1,
            data.pfc_map_name,
            data.cli_type,
            expect_error=data.expect_deletion_blocked
        )

        if not success:
            st.warn("Deletion behavior did not match expected behavior")
            st.report_tc_fail(TC_IDS.delete_active_map, "msg", "Deletion behavior unexpected")
            tc_result = False
        else:
            st.report_tc_pass(TC_IDS.delete_active_map, "msg", "Deletion behavior as expected")

        # Step 6: Verify state after deletion attempt
        st.banner("Step 6: Verify System State After Deletion Attempt")

        # Check if map still exists globally
        map_exists_after = verify_pfc_map_exists(vars.D1, data.pfc_map_name, data.cli_type)
        st.log(f"PFC map exists after deletion attempt: {map_exists_after}")

        # Check if interface still references map
        interface_refs_map = verify_interface_pfc_map(vars.D1, data.test_interface, data.pfc_map_name, data.cli_type)
        st.log(f"Interface still references map after deletion: {interface_refs_map}")

        # Analyze consistency
        st.log("Analyzing system consistency:")

        if not map_exists_after and interface_refs_map:
            st.error("INCONSISTENT STATE DETECTED:")
            st.error(f"  - Global PFC map '{data.pfc_map_name}' was deleted")
            st.error(f"  - Interface {data.test_interface} still references the map")
            st.error("  This creates a dangling reference!")
            st.report_tc_fail(TC_IDS.verify_consistency, "msg", "Inconsistent state detected")
            tc_result = False
        elif map_exists_after and interface_refs_map:
            st.log("CONSISTENT STATE: Both map and reference exist (deletion was blocked)")
            st.report_tc_pass(TC_IDS.verify_consistency, "msg", "System state is consistent")
        elif not map_exists_after and not interface_refs_map:
            st.log("CONSISTENT STATE: Both map and reference removed (graceful deletion)")
            st.report_tc_pass(TC_IDS.verify_consistency, "msg", "System state is consistent")
        else:
            st.warn("UNEXPECTED STATE: Map exists but interface doesn't reference it")
            st.report_tc_fail(TC_IDS.verify_consistency, "msg", "Unexpected system state")
            tc_result = False

        # Display current configuration
        st.log("Displaying current configuration after deletion attempt:")
        # Ensure we're in exec mode
        st.config(vars.D1, "end", type=data.cli_type, skip_error_check=True, conf=False)

        output = st.show(vars.D1, "show qos map pfc-priority-pg", type=data.cli_type, skip_error_check=True)
        st.log(f"Current PFC Maps:\n{output}")

        output = st.show(vars.D1, f"show qos interface {data.test_interface}", type=data.cli_type, skip_error_check=True)
        st.log(f"Current Interface Config:\n{output}")

        # Step 7: Test recovery by reconfiguring map
        st.banner("Step 7: Test Recovery - Reconfigure PFC Map")
        st.log("Testing if system can recover by recreating the map with same name")

        if not map_exists_after:
            st.log(f"Reconfiguring PFC map '{data.pfc_map_name}'")

            if not configure_pfc_map(vars.D1, data.pfc_map_name, data.pfc_mappings, data.cli_type):
                st.error("Failed to reconfigure PFC map")
                st.report_tc_fail(TC_IDS.recovery_test, "msg", "Recovery failed")
                tc_result = False
            else:
                # Verify recovery
                map_exists_recovered = verify_pfc_map_exists(vars.D1, data.pfc_map_name, data.cli_type)
                interface_refs_recovered = verify_interface_pfc_map(vars.D1, data.test_interface, data.pfc_map_name, data.cli_type)

                if map_exists_recovered and interface_refs_recovered:
                    st.log("RECOVERY SUCCESSFUL:")
                    st.log("  - PFC map recreated")
                    st.log("  - Interface reference is functional")
                    st.report_tc_pass(TC_IDS.recovery_test, "msg", "Recovery successful")
                else:
                    st.error("Recovery incomplete - configuration not fully functional")
                    st.report_tc_fail(TC_IDS.recovery_test, "msg", "Recovery incomplete")
                    tc_result = False
        else:
            st.log("Map still exists, no recovery needed")
            st.report_tc_pass(TC_IDS.recovery_test, "msg", "No recovery needed")

        # Step 8: Display final configuration
        st.banner("Step 8: Final Configuration Verification")

        # Ensure we're in exec mode for show commands
        st.config(vars.D1, "end", type=data.cli_type, skip_error_check=True, conf=False)

        st.log("Final PFC map configuration:")
        output = st.show(vars.D1, "show qos map pfc-priority-pg", type=data.cli_type, skip_error_check=True)
        st.log(f"Final PFC Maps:\n{output}")

        st.log(f"Final interface {data.test_interface} configuration:")
        output = st.show(vars.D1, f"show qos interface {data.test_interface}", type=data.cli_type, skip_error_check=True)
        st.log(f"Final Interface Config:\n{output}")

        # Optional: Check running configuration
        if data.verify_running_config:
            st.log("Checking running configuration:")
            # Use click mode for show runningconfiguration command
            output = st.show(vars.D1, f"show runningconfiguration interfaces {data.test_interface}",
                           type="click", skip_error_check=True, skip_tmpl=True)
            st.log(f"Running Config:\n{output}")

    except Exception as e:
        st.error(f"Test encountered unexpected exception: {e}")
        import traceback
        st.error(traceback.format_exc())
        tc_result = False

    # Report final test result
    st.banner("TEST RESULT")
    if tc_result:
        st.report_pass("test_case_passed")
    else:
        st.report_fail("test_case_failed")
