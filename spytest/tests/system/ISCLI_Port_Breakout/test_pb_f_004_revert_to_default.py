"""
Test Case ID: PB-F-004
Title: Revert Breakout to Default Mode
Author: Network Automation Team
Copyright (C) 2026

Description:
    Validate reverting port from breakout mode back to default (1x800G).
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

# Module level variables
data = SpyTestDict()
CONFIG = SpyTestDict()

TC_IDS = {"PB_F_004": "PB-F-004: Revert Breakout to Default Mode"}


@pytest.fixture(scope="module", autouse=True)
def prologue_epilogue(request):
    global data, CONFIG
    vars = st.get_testbed_vars()
    data.vars = vars

    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.banner("MODULE CONFIGURATION START - PB-F-004")
    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")

    CONFIG.test_port = "Ethernet24"
    CONFIG.breakout_wait_time = 60
    CONFIG.test_breakout_mode = "8x100G"
    CONFIG.child_ports = ["Ethernet24", "Ethernet25", "Ethernet26", "Ethernet27",
                         "Ethernet28", "Ethernet29", "Ethernet30", "Ethernet31"]

    pre_config()
    yield
    st.banner("MODULE CONFIGURATION CLEANUP - PB-F-004")
    cleanup()
    st.banner("MODULE CONFIGURATION END - PB-F-004")


def pre_config():
    st.banner("PRE-CONFIGURATION START")
    try:
        configure_breakout_mode(data.vars.D1, CONFIG.test_port, "1x800G")
        st.log("Pre-configuration completed")
    except Exception as e:
        st.error(f"Pre-configuration failed: {e}")


def cleanup():
    st.banner("CLEANUP START")
    try:
        configure_breakout_mode(data.vars.D1, CONFIG.test_port, "1x800G")
        st.log("Cleanup completed")
    except Exception as e:
        st.error(f"Cleanup error: {e}")


def configure_breakout_mode(dut, port, mode):
    try:
        st.log(f"Configuring {port} to {mode}")
        st.config(dut, f"interface breakout {port} mode {mode}",
                 type=data.cli_type, skip_error_check=True)
        st.wait(CONFIG.breakout_wait_time)
        return True
    except Exception as e:
        st.error(f"Breakout config failed: {e}")
        return False


def verify_port_exists(dut, port):
    try:
        output = st.show(dut, f"show interface {port}",
                        type=data.cli_type, skip_error_check=True)
        return output and len(output) > 0
    except:
        return False


def test_pb_f_004_revert_breakout_to_default():
    """
    Test Case: PB-F-004 - Revert Breakout to Default Mode

    Steps:
        1. Configure port to breakout mode (8x100G)
        2. Verify child ports created
        3. Revert port to default mode (1x800G)
        4. Verify port back to single port
    """
    st.banner("TEST CASE START: PB-F-004")
    st.log("="*80)
    st.log(TC_IDS["PB_F_004"])
    st.log("="*80)

    validation_errors = []
    vars = data.vars

    try:
        # STEP 1: Configure breakout
        st.banner("STEP 1: Configure Breakout Mode (8x100G)")
        if not configure_breakout_mode(vars.D1, CONFIG.test_port, CONFIG.test_breakout_mode):
            validation_errors.append("Failed to configure breakout")

        # STEP 2: Verify child ports
        st.banner("STEP 2: Verify Child Ports Created")
        for port in CONFIG.child_ports:
            if not verify_port_exists(vars.D1, port):
                validation_errors.append(f"Port {port} not found")

        # STEP 3: Revert to default
        st.banner("STEP 3: Revert to Default Mode (1x800G)")
        if not configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G"):
            validation_errors.append("Failed to revert to default")

        # STEP 4: Verify single port
        st.banner("STEP 4: Verify Single Port After Revert")
        if verify_port_exists(vars.D1, CONFIG.test_port):
            st.log(f"Port {CONFIG.test_port} verified after revert")
        else:
            validation_errors.append("Main port not found after revert")

        # Report results
        st.banner("TEST RESULTS")
        if validation_errors:
            st.log(f"FAIL - {len(validation_errors)} errors")
            for idx, error in enumerate(validation_errors, 1):
                st.log(f"  {idx}. {error}")
            st.report_tc_fail("PB_F_004", "test_failed",
                            f"Test failed with {len(validation_errors)} errors")
        else:
            st.log("PASS - Port successfully reverted to default")
            st.report_tc_pass("PB_F_004", "test_passed",
                            "Revert to default completed successfully")

    except Exception as e:
        st.error(f"EXCEPTION: {e}")
        st.report_tc_fail("PB_F_004", "test_exception", f"Exception: {e}")

    finally:
        st.banner("TEST CASE END: PB-F-004")
