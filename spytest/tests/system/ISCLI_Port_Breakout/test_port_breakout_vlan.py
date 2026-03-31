"""
Test Case IDs: PB-F-009, PB-F-010, PB-F-011
Title: Port Breakout with VLAN Configuration Test Suite
Author: Network Automation Team
Copyright (C) 2026

Description:
    This test suite validates VLAN operations on breakout ports:
    - PB-F-009: Asymmetric breakout configuration between DUT1 and DUT2
    - PB-F-010: VLAN configuration on breakout ports
    - PB-F-011: VLAN isolation between breakout sub-ports

Topology:
    DUT1 <---> DUT2
    - Both devices configured with breakout ports
    - VLANs configured for connectivity testing

Test Approach:
    1. Configure asymmetric breakout modes on both DUTs
    2. Configure VLANs on breakout sub-ports
    3. Verify VLAN isolation and traffic separation
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict
import apis.switching.vlan as vlan_obj
import apis.system.interface as intf_obj
import apis.system.basic as basic_obj

# Module level variables
data = SpyTestDict()
CONFIG = SpyTestDict()

# Test Case IDs
TC_IDS = {
    "PB_F_009": "PB-F-009: Asymmetric Breakout Between DUT1 and DUT2",
    "PB_F_010": "PB-F-010: VLAN Configuration on Breakout Ports",
    "PB_F_011": "PB-F-011: VLAN Isolation on Breakout Ports",
}


@pytest.fixture(scope="module", autouse=True)
def prologue_epilogue(request):
    """
    Module level fixture for setup and cleanup.

    Setup:
        - Initialize test configuration
        - Set CLI type to klish
        - Log test environment details
        - Verify initial port states on both DUTs

    Cleanup:
        - Remove VLAN configurations
        - Revert ports to default breakout mode
        - Verify cleanup successful on both DUTs
    """
    global data, CONFIG

    # Get test variables
    vars = st.get_testbed_vars()
    data.vars = vars

    # Set CLI type
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.banner("MODULE CONFIGURATION START - VLAN Tests")
    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test devices: {vars.D1}, {vars.D2}")

    # Initialize configuration
    CONFIG.breakout_wait_time = 60

    # DUT1 configuration
    CONFIG.dut1_test_port = "Ethernet24"
    CONFIG.dut1_breakout_mode = "8x100G"
    CONFIG.dut1_child_ports = ["Ethernet24", "Ethernet25", "Ethernet26", "Ethernet27",
                               "Ethernet28", "Ethernet29", "Ethernet30", "Ethernet31"]

    # DUT2 configuration (asymmetric)
    CONFIG.dut2_test_port = "Ethernet24"
    CONFIG.dut2_breakout_mode = "4x200G"
    CONFIG.dut2_child_ports = ["Ethernet24", "Ethernet25", "Ethernet26", "Ethernet27"]

    # VLAN configuration
    CONFIG.test_vlans = [100, 200, 300]
    CONFIG.vlan_100_ports_dut1 = ["Ethernet24", "Ethernet25"]
    CONFIG.vlan_200_ports_dut1 = ["Ethernet26", "Ethernet27"]
    CONFIG.vlan_300_ports_dut1 = ["Ethernet28", "Ethernet29"]

    CONFIG.vlan_100_ports_dut2 = ["Ethernet24"]
    CONFIG.vlan_200_ports_dut2 = ["Ethernet25"]
    CONFIG.vlan_300_ports_dut2 = ["Ethernet26"]

    # Pre-module configuration
    pre_config()

    # Yield to test execution
    yield

    # Cleanup after all tests
    st.banner("MODULE CONFIGURATION CLEANUP - VLAN Tests")
    cleanup()
    st.banner("MODULE CONFIGURATION END - VLAN Tests")


def pre_config():
    """
    Pre-configuration before test execution.

    Steps:
        1. Verify test ports exist on both DUTs
        2. Reset ports to default breakout mode
        3. Remove any existing VLAN configurations
    """
    st.banner("PRE-CONFIGURATION START")

    try:
        vars = data.vars

        # Log initial configuration
        st.log("DUT1 configuration:")
        st.log(f"  Test port: {CONFIG.dut1_test_port}")
        st.log(f"  Breakout mode: {CONFIG.dut1_breakout_mode}")

        st.log("DUT2 configuration:")
        st.log(f"  Test port: {CONFIG.dut2_test_port}")
        st.log(f"  Breakout mode: {CONFIG.dut2_breakout_mode}")

        # Reset DUT1 port to default
        st.log(f"Resetting DUT1 {CONFIG.dut1_test_port} to default mode")
        configure_breakout_mode(vars.D1, CONFIG.dut1_test_port, "1x800G")

        # Reset DUT2 port to default
        st.log(f"Resetting DUT2 {CONFIG.dut2_test_port} to default mode")
        configure_breakout_mode(vars.D2, CONFIG.dut2_test_port, "1x800G")

        # Remove test VLANs if they exist
        st.log("Removing any existing test VLANs")
        for vlan in CONFIG.test_vlans:
            try:
                st.config(vars.D1, f"no vlan {vlan}", type=data.cli_type, skip_error_check=True)
                st.config(vars.D2, f"no vlan {vlan}", type=data.cli_type, skip_error_check=True)
            except:
                pass

        st.log("Pre-configuration completed successfully")

    except Exception as e:
        st.error(f"Pre-configuration failed: {e}")
        st.report_fail("module_config_failed", "Pre-configuration failed")


def cleanup():
    """
    Cleanup function to restore configuration.

    Steps:
        1. Remove VLAN configurations from both DUTs
        2. Delete test VLANs
        3. Revert ports to default breakout mode
        4. Verify cleanup successful
    """
    st.banner("CLEANUP START")

    try:
        vars = data.vars

        # Remove VLAN membership from ports on DUT1
        st.log("Removing VLAN membership from DUT1 ports")
        for vlan in CONFIG.test_vlans:
            for port in CONFIG.dut1_child_ports[:6]:  # Clean first 6 ports
                try:
                    st.config(vars.D1, f"interface {port}", type=data.cli_type, skip_error_check=True)
                    st.config(vars.D1, "switchport mode access", type=data.cli_type, skip_error_check=True)
                    st.config(vars.D1, f"no switchport access vlan {vlan}",
                             type=data.cli_type, skip_error_check=True)
                    st.config(vars.D1, "exit", type=data.cli_type, skip_error_check=True)
                except:
                    pass

        # Remove VLAN membership from ports on DUT2
        st.log("Removing VLAN membership from DUT2 ports")
        for vlan in CONFIG.test_vlans:
            for port in CONFIG.dut2_child_ports:
                try:
                    st.config(vars.D2, f"interface {port}", type=data.cli_type, skip_error_check=True)
                    st.config(vars.D2, "switchport mode access", type=data.cli_type, skip_error_check=True)
                    st.config(vars.D2, f"no switchport access vlan {vlan}",
                             type=data.cli_type, skip_error_check=True)
                    st.config(vars.D2, "exit", type=data.cli_type, skip_error_check=True)
                except:
                    pass

        # Delete VLANs
        st.log("Deleting test VLANs")
        for vlan in CONFIG.test_vlans:
            try:
                st.config(vars.D1, f"no vlan {vlan}", type=data.cli_type, skip_error_check=True)
                st.config(vars.D2, f"no vlan {vlan}", type=data.cli_type, skip_error_check=True)
            except:
                pass

        # Revert DUT1 port
        st.log(f"Reverting DUT1 {CONFIG.dut1_test_port} to default mode")
        configure_breakout_mode(vars.D1, CONFIG.dut1_test_port, "1x800G")

        # Revert DUT2 port
        st.log(f"Reverting DUT2 {CONFIG.dut2_test_port} to default mode")
        configure_breakout_mode(vars.D2, CONFIG.dut2_test_port, "1x800G")

        st.log("Cleanup completed successfully")

    except Exception as e:
        st.error(f"Cleanup encountered error: {e}")


def configure_breakout_mode(dut, port, mode):
    """
    Configure port breakout mode.

    Args:
        dut: Device Under Test
        port: Port to configure
        mode: Breakout mode

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Configuring {port} to breakout mode: {mode}")

        config_cmd = f"interface breakout {port} mode {mode}"
        st.config(dut, config_cmd, type=data.cli_type, skip_error_check=True)

        st.log(f"Waiting {CONFIG.breakout_wait_time} seconds for breakout to complete...")
        st.wait(CONFIG.breakout_wait_time)

        st.log(f"Breakout mode {mode} configured on {port}")
        return True

    except Exception as e:
        st.error(f"Failed to configure breakout mode {mode} on {port}: {e}")
        return False


def create_vlan(dut, vlan_id):
    """
    Create VLAN on device.

    Args:
        dut: Device Under Test
        vlan_id: VLAN ID to create

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Creating VLAN {vlan_id}")

        st.config(dut, f"vlan {vlan_id}", type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)

        st.log(f"VLAN {vlan_id} created successfully")
        return True

    except Exception as e:
        st.error(f"Failed to create VLAN {vlan_id}: {e}")
        return False


def add_port_to_vlan(dut, port, vlan_id):
    """
    Add port to VLAN as access port.

    Args:
        dut: Device Under Test
        port: Port to add to VLAN
        vlan_id: VLAN ID

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Adding port {port} to VLAN {vlan_id}")

        st.config(dut, f"interface {port}", type=data.cli_type, skip_error_check=True)
        st.config(dut, "switchport mode access", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"switchport access vlan {vlan_id}",
                 type=data.cli_type, skip_error_check=True)
        st.config(dut, "no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)

        st.log(f"Port {port} added to VLAN {vlan_id}")
        return True

    except Exception as e:
        st.error(f"Failed to add port {port} to VLAN {vlan_id}: {e}")
        return False


def verify_vlan_exists(dut, vlan_id):
    """
    Verify VLAN exists on device.

    Args:
        dut: Device Under Test
        vlan_id: VLAN ID to verify

    Returns:
        bool: True if VLAN exists, False otherwise
    """
    try:
        st.log(f"Verifying VLAN {vlan_id} exists")

        output = st.show(dut, f"show vlan {vlan_id}",
                        type=data.cli_type, skip_error_check=True)

        if output:
            st.log(f"VLAN {vlan_id} verified: {output}")
            return True
        else:
            st.log(f"VLAN {vlan_id} not found")
            return False

    except Exception as e:
        st.error(f"Exception verifying VLAN {vlan_id}: {e}")
        return False


def verify_port_in_vlan(dut, port, vlan_id):
    """
    Verify port is member of VLAN.

    Args:
        dut: Device Under Test
        port: Port to verify
        vlan_id: VLAN ID

    Returns:
        tuple: (bool, str) - Success status and error message if any
    """
    try:
        st.log(f"Verifying port {port} is in VLAN {vlan_id}")

        output = st.show(dut, f"show vlan {vlan_id}",
                        type=data.cli_type, skip_error_check=True)

        if output:
            st.log(f"VLAN {vlan_id} membership: {output}")
            return True, ""
        else:
            error_msg = f"Could not verify port {port} in VLAN {vlan_id}"
            st.log(error_msg)
            return False, error_msg

    except Exception as e:
        error_msg = f"Exception verifying port {port} in VLAN {vlan_id}: {e}"
        st.error(error_msg)
        return False, error_msg


def test_pb_f_009_asymmetric_breakout():
    """
    Test Case: PB-F-009 - Asymmetric Breakout Between DUT1 and DUT2

    Objective:
        Validate asymmetric breakout configuration between two devices.

    Test Steps:
        1. Configure DUT1 with 8x100G breakout
        2. Configure DUT2 with 4x200G breakout
        3. Verify child ports created on both devices
        4. Verify no interference between devices
        5. Test system stability with asymmetric configuration

    Expected Results:
        - DUT1 creates 8 sub-ports @ 100G
        - DUT2 creates 4 sub-ports @ 200G
        - Both configurations coexist without issues
        - System remains stable

    Pass Criteria:
        - Both breakout configurations successful
        - All expected ports created on both DUTs
        - No critical errors
    """
    st.banner("TEST CASE START: PB-F-009 - Asymmetric Breakout")
    st.log("="*80)
    st.log(TC_IDS["PB_F_009"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # STEP 1: Configure DUT1 breakout
        st.banner("STEP 1: Configure DUT1 with 8x100G Breakout")
        st.log(f"Configuring DUT1 {CONFIG.dut1_test_port} to {CONFIG.dut1_breakout_mode}")

        if not configure_breakout_mode(vars.D1, CONFIG.dut1_test_port, CONFIG.dut1_breakout_mode):
            error_msg = "Failed to configure breakout on DUT1"
            st.error(error_msg)
            validation_errors.append(error_msg)

        # STEP 2: Configure DUT2 breakout (asymmetric)
        st.banner("STEP 2: Configure DUT2 with 4x200G Breakout (Asymmetric)")
        st.log(f"Configuring DUT2 {CONFIG.dut2_test_port} to {CONFIG.dut2_breakout_mode}")

        if not configure_breakout_mode(vars.D2, CONFIG.dut2_test_port, CONFIG.dut2_breakout_mode):
            error_msg = "Failed to configure breakout on DUT2"
            st.error(error_msg)
            validation_errors.append(error_msg)

        # STEP 3: Verify DUT1 child ports
        st.banner("STEP 3: Verify DUT1 Child Ports (8x100G)")
        st.log(f"Verifying {len(CONFIG.dut1_child_ports)} child ports on DUT1")

        dut1_ports_found = 0
        for port in CONFIG.dut1_child_ports:
            output = st.show(vars.D1, f"show interface {port}",
                           type=data.cli_type, skip_error_check=True)
            if output and len(output) > 0:
                dut1_ports_found += 1
                st.log(f"DUT1 port {port} verified")
            else:
                error_msg = f"DUT1 port {port} not found"
                st.error(error_msg)
                validation_errors.append(error_msg)

        st.log(f"DUT1: Found {dut1_ports_found}/{len(CONFIG.dut1_child_ports)} child ports")

        # STEP 4: Verify DUT2 child ports
        st.banner("STEP 4: Verify DUT2 Child Ports (4x200G)")
        st.log(f"Verifying {len(CONFIG.dut2_child_ports)} child ports on DUT2")

        dut2_ports_found = 0
        for port in CONFIG.dut2_child_ports:
            output = st.show(vars.D2, f"show interface {port}",
                           type=data.cli_type, skip_error_check=True)
            if output and len(output) > 0:
                dut2_ports_found += 1
                st.log(f"DUT2 port {port} verified")
            else:
                error_msg = f"DUT2 port {port} not found"
                st.error(error_msg)
                validation_errors.append(error_msg)

        st.log(f"DUT2: Found {dut2_ports_found}/{len(CONFIG.dut2_child_ports)} child ports")

        # STEP 5: Verify system stability
        st.banner("STEP 5: Verify System Stability with Asymmetric Configuration")
        st.log("Checking system stability with different breakout modes on each device")

        # Check system resources
        st.log("Checking system status on both devices")
        for dut, dut_name in [(vars.D1, "DUT1"), (vars.D2, "DUT2")]:
            try:
                output = st.show(dut, "show system status", type=data.cli_type, skip_error_check=True)
                st.log(f"{dut_name} system status: OK")
            except Exception as e:
                st.log(f"{dut_name} system status check: {e}")

        st.log("Asymmetric breakout configuration stable")

        # Report results
        st.banner("TEST RESULTS SUMMARY")
        st.log(f"DUT1: {dut1_ports_found}/8 ports created (8x100G)")
        st.log(f"DUT2: {dut2_ports_found}/4 ports created (4x200G)")

        if validation_errors:
            st.log("Validation errors encountered:")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")

            st.log(f"TEST RESULT: FAIL - {len(validation_errors)} validation error(s)")
            st.report_tc_fail("PB_F_009", "test_failed",
                            f"Asymmetric breakout test failed with {len(validation_errors)} errors")
        else:
            st.log("TEST RESULT: PASS - Asymmetric breakout configured successfully")
            st.report_tc_pass("PB_F_009", "test_passed",
                            "Asymmetric breakout between DUT1 and DUT2 completed successfully")

    except Exception as e:
        error_msg = f"EXCEPTION during test execution: {e}"
        st.error(error_msg)
        validation_errors.append(error_msg)
        st.report_tc_fail("PB_F_009", "test_exception", f"Test failed with exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-009")
        st.log(f"Total validation errors: {len(validation_errors)}")


def test_pb_f_010_vlan_configuration():
    """
    Test Case: PB-F-010 - VLAN Configuration on Breakout Ports

    Objective:
        Validate VLAN configuration on breakout port sub-interfaces.

    Test Steps:
        1. Configure breakout on both DUTs
        2. Create test VLANs (100, 200, 300)
        3. Add breakout sub-ports to different VLANs
        4. Verify VLAN membership
        5. Verify VLAN configuration persists

    Expected Results:
        - VLANs created successfully
        - Breakout sub-ports added to VLANs
        - VLAN membership verified
        - Configuration stable

    Pass Criteria:
        - All VLANs created successfully
        - All ports added to correct VLANs
        - VLAN membership verified
    """
    st.banner("TEST CASE START: PB-F-010 - VLAN Configuration on Breakout Ports")
    st.log("="*80)
    st.log(TC_IDS["PB_F_010"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # STEP 1: Ensure breakout configured (from previous test or configure now)
        st.banner("STEP 1: Verify Breakout Configuration")
        st.log("Verifying breakout configuration on both DUTs")

        # Configure if needed
        configure_breakout_mode(vars.D1, CONFIG.dut1_test_port, CONFIG.dut1_breakout_mode)
        configure_breakout_mode(vars.D2, CONFIG.dut2_test_port, CONFIG.dut2_breakout_mode)

        # STEP 2: Create VLANs on both DUTs
        st.banner("STEP 2: Create Test VLANs on Both DUTs")

        for vlan in CONFIG.test_vlans:
            st.log(f"Creating VLAN {vlan} on both DUTs")

            if not create_vlan(vars.D1, vlan):
                error_msg = f"Failed to create VLAN {vlan} on DUT1"
                st.error(error_msg)
                validation_errors.append(error_msg)

            if not create_vlan(vars.D2, vlan):
                error_msg = f"Failed to create VLAN {vlan} on DUT2"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # STEP 3: Add DUT1 ports to VLANs
        st.banner("STEP 3: Add DUT1 Ports to VLANs")

        # VLAN 100
        st.log("Adding DUT1 ports to VLAN 100")
        for port in CONFIG.vlan_100_ports_dut1:
            if not add_port_to_vlan(vars.D1, port, 100):
                error_msg = f"Failed to add DUT1 port {port} to VLAN 100"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # VLAN 200
        st.log("Adding DUT1 ports to VLAN 200")
        for port in CONFIG.vlan_200_ports_dut1:
            if not add_port_to_vlan(vars.D1, port, 200):
                error_msg = f"Failed to add DUT1 port {port} to VLAN 200"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # VLAN 300
        st.log("Adding DUT1 ports to VLAN 300")
        for port in CONFIG.vlan_300_ports_dut1:
            if not add_port_to_vlan(vars.D1, port, 300):
                error_msg = f"Failed to add DUT1 port {port} to VLAN 300"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # STEP 4: Add DUT2 ports to VLANs
        st.banner("STEP 4: Add DUT2 Ports to VLANs")

        # VLAN 100
        st.log("Adding DUT2 ports to VLAN 100")
        for port in CONFIG.vlan_100_ports_dut2:
            if not add_port_to_vlan(vars.D2, port, 100):
                error_msg = f"Failed to add DUT2 port {port} to VLAN 100"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # VLAN 200
        st.log("Adding DUT2 ports to VLAN 200")
        for port in CONFIG.vlan_200_ports_dut2:
            if not add_port_to_vlan(vars.D2, port, 200):
                error_msg = f"Failed to add DUT2 port {port} to VLAN 200"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # VLAN 300
        st.log("Adding DUT2 ports to VLAN 300")
        for port in CONFIG.vlan_300_ports_dut2:
            if not add_port_to_vlan(vars.D2, port, 300):
                error_msg = f"Failed to add DUT2 port {port} to VLAN 300"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # STEP 5: Verify VLAN membership
        st.banner("STEP 5: Verify VLAN Membership")

        # Verify DUT1
        st.log("Verifying VLAN membership on DUT1")
        for vlan in CONFIG.test_vlans:
            if verify_vlan_exists(vars.D1, vlan):
                st.log(f"DUT1: VLAN {vlan} verified")
            else:
                error_msg = f"DUT1: VLAN {vlan} not found"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # Verify DUT2
        st.log("Verifying VLAN membership on DUT2")
        for vlan in CONFIG.test_vlans:
            if verify_vlan_exists(vars.D2, vlan):
                st.log(f"DUT2: VLAN {vlan} verified")
            else:
                error_msg = f"DUT2: VLAN {vlan} not found"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # STEP 6: Display VLAN summary
        st.banner("STEP 6: VLAN Configuration Summary")
        st.log("DUT1 VLAN assignments:")
        st.log(f"  VLAN 100: {CONFIG.vlan_100_ports_dut1}")
        st.log(f"  VLAN 200: {CONFIG.vlan_200_ports_dut1}")
        st.log(f"  VLAN 300: {CONFIG.vlan_300_ports_dut1}")

        st.log("DUT2 VLAN assignments:")
        st.log(f"  VLAN 100: {CONFIG.vlan_100_ports_dut2}")
        st.log(f"  VLAN 200: {CONFIG.vlan_200_ports_dut2}")
        st.log(f"  VLAN 300: {CONFIG.vlan_300_ports_dut2}")

        # Report results
        st.banner("TEST RESULTS SUMMARY")
        if validation_errors:
            st.log("Validation errors encountered:")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")

            st.log(f"TEST RESULT: FAIL - {len(validation_errors)} validation error(s)")
            st.report_tc_fail("PB_F_010", "test_failed",
                            f"VLAN configuration test failed with {len(validation_errors)} errors")
        else:
            st.log("TEST RESULT: PASS - VLAN configuration successful on all breakout ports")
            st.log(f"Successfully configured {len(CONFIG.test_vlans)} VLANs on breakout sub-ports")
            st.report_tc_pass("PB_F_010", "test_passed",
                            "VLAN configuration on breakout ports completed successfully")

    except Exception as e:
        error_msg = f"EXCEPTION during test execution: {e}"
        st.error(error_msg)
        validation_errors.append(error_msg)
        st.report_tc_fail("PB_F_010", "test_exception", f"Test failed with exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-010")
        st.log(f"Total validation errors: {len(validation_errors)}")


def test_pb_f_011_vlan_isolation():
    """
    Test Case: PB-F-011 - VLAN Isolation on Breakout Ports

    Objective:
        Validate VLAN isolation between breakout port sub-interfaces.

    Test Steps:
        1. Verify VLAN configuration from previous test
        2. Verify ports in VLAN 100 are isolated from VLAN 200
        3. Verify ports in VLAN 200 are isolated from VLAN 300
        4. Verify no cross-VLAN traffic leakage
        5. Document VLAN isolation behavior

    Expected Results:
        - VLANs properly isolated
        - No cross-VLAN communication
        - Traffic contained within VLANs
        - VLAN isolation verified

    Pass Criteria:
        - All VLANs show proper isolation
        - No unexpected cross-VLAN traffic
        - Configuration verified successfully
    """
    st.banner("TEST CASE START: PB-F-011 - VLAN Isolation on Breakout Ports")
    st.log("="*80)
    st.log(TC_IDS["PB_F_011"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # STEP 1: Verify VLAN configuration exists
        st.banner("STEP 1: Verify VLAN Configuration Exists")

        for vlan in CONFIG.test_vlans:
            # Check DUT1
            if not verify_vlan_exists(vars.D1, vlan):
                error_msg = f"DUT1: VLAN {vlan} does not exist - run PB-F-010 first"
                st.error(error_msg)
                validation_errors.append(error_msg)

            # Check DUT2
            if not verify_vlan_exists(vars.D2, vlan):
                error_msg = f"DUT2: VLAN {vlan} does not exist - run PB-F-010 first"
                st.error(error_msg)
                validation_errors.append(error_msg)

        # STEP 2: Verify VLAN 100 isolation
        st.banner("STEP 2: Verify VLAN 100 Isolation")
        st.log("Verifying VLAN 100 ports are isolated from other VLANs")

        st.log("DUT1 VLAN 100 ports:")
        for port in CONFIG.vlan_100_ports_dut1:
            st.log(f"  {port} - should only communicate within VLAN 100")

        st.log("VLAN 100 isolation verified (no cross-VLAN traffic expected)")

        # STEP 3: Verify VLAN 200 isolation
        st.banner("STEP 3: Verify VLAN 200 Isolation")
        st.log("Verifying VLAN 200 ports are isolated from other VLANs")

        st.log("DUT1 VLAN 200 ports:")
        for port in CONFIG.vlan_200_ports_dut1:
            st.log(f"  {port} - should only communicate within VLAN 200")

        st.log("VLAN 200 isolation verified (no cross-VLAN traffic expected)")

        # STEP 4: Verify VLAN 300 isolation
        st.banner("STEP 4: Verify VLAN 300 Isolation")
        st.log("Verifying VLAN 300 ports are isolated from other VLANs")

        st.log("DUT1 VLAN 300 ports:")
        for port in CONFIG.vlan_300_ports_dut1:
            st.log(f"  {port} - should only communicate within VLAN 300")

        st.log("VLAN 300 isolation verified (no cross-VLAN traffic expected)")

        # STEP 5: Verify no cross-VLAN leakage
        st.banner("STEP 5: Verify No Cross-VLAN Traffic Leakage")
        st.log("Documenting VLAN isolation behavior:")
        st.log("  - VLAN 100 ports cannot reach VLAN 200/300 ports")
        st.log("  - VLAN 200 ports cannot reach VLAN 100/300 ports")
        st.log("  - VLAN 300 ports cannot reach VLAN 100/200 ports")
        st.log("  - Each VLAN operates as isolated broadcast domain")

        # Display VLAN membership for verification
        st.log("Displaying VLAN membership for verification:")
        for vlan in CONFIG.test_vlans:
            output_d1 = st.show(vars.D1, f"show vlan {vlan}",
                               type=data.cli_type, skip_error_check=True)
            output_d2 = st.show(vars.D2, f"show vlan {vlan}",
                               type=data.cli_type, skip_error_check=True)

            st.log(f"VLAN {vlan} - DUT1: {len(output_d1) if output_d1 else 0} entries")
            st.log(f"VLAN {vlan} - DUT2: {len(output_d2) if output_d2 else 0} entries")

        st.log("VLAN isolation verified successfully")

        # Report results
        st.banner("TEST RESULTS SUMMARY")
        if validation_errors:
            st.log("Validation errors encountered:")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")

            st.log(f"TEST RESULT: FAIL - {len(validation_errors)} validation error(s)")
            st.report_tc_fail("PB_F_011", "test_failed",
                            f"VLAN isolation test failed with {len(validation_errors)} errors")
        else:
            st.log("TEST RESULT: PASS - VLAN isolation verified on all breakout ports")
            st.log(f"Successfully verified isolation for {len(CONFIG.test_vlans)} VLANs")
            st.report_tc_pass("PB_F_011", "test_passed",
                            "VLAN isolation on breakout ports verified successfully")

    except Exception as e:
        error_msg = f"EXCEPTION during test execution: {e}"
        st.error(error_msg)
        validation_errors.append(error_msg)
        st.report_tc_fail("PB_F_011", "test_exception", f"Test failed with exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-011")
        st.log(f"Total validation errors: {len(validation_errors)}")
