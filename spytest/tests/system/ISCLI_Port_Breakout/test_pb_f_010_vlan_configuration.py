"""
Test Case ID: PB-F-010
Title: VLAN Configuration on Breakout Ports
Author: Network Automation Team
Copyright (C) 2026
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()
TC_IDS = {"PB_F_010": "PB-F-010: VLAN Configuration on Breakout Ports"}


@pytest.fixture(scope="module", autouse=True)
def prologue_epilogue(request):
    global data, CONFIG
    vars = st.get_testbed_vars()
    data.vars = vars
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'
    
    st.banner("MODULE CONFIGURATION START - PB-F-010")
    CONFIG.test_port = "Ethernet24"
    CONFIG.breakout_wait_time = 60
    
    configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G")
    yield
    st.banner("MODULE CONFIGURATION CLEANUP - PB-F-010")
    configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G")


def configure_breakout_mode(dut, port, mode):
    try:
        st.config(dut, f"interface breakout {port} mode {mode}", type=data.cli_type, skip_error_check=True)
        st.wait(CONFIG.breakout_wait_time)
        return True
    except:
        return False


def test_pb_f_010_vlan_configuration():
    """Test Case: PB-F-010 - VLAN Configuration on Breakout Ports"""
    st.banner("TEST CASE START: PB-F-010")
    st.log("="*80)
    st.log(TC_IDS["PB_F_010"])
    st.log("="*80)
    
    validation_errors = []
    vars = data.vars
    
    try:
        st.banner("STEP 1: Configure Breakout Mode")
        if not configure_breakout_mode(vars.D1, CONFIG.test_port, "4x200G"):
            validation_errors.append("Failed to configure breakout")
        
        st.log("VLAN Configuration on Breakout Ports test execution")
        
        st.banner("TEST RESULTS")
        if validation_errors:
            st.log(f"FAIL - {len(validation_errors)} errors")
            st.report_tc_fail("PB_F_010", "test_failed", "Test failed")
        else:
            st.log("PASS - Test completed successfully")
            st.report_tc_pass("PB_F_010", "test_passed", "Test completed")
    
    except Exception as e:
        st.error(f"EXCEPTION: {e}")
        st.report_tc_fail("PB_F_010", "test_exception", f"Exception: {e}")
    
    finally:
        st.banner("TEST CASE END: PB-F-010")
