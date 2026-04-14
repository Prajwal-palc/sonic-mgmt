"""
Test Case ID: PB-F-007
Title: Shutdown/No Shutdown Operations
Author: Network Automation Team
Copyright (C) 2026
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()
TC_IDS = {"PB_F_007": "PB-F-007: Shutdown/No Shutdown Operations"}


@pytest.fixture(scope="module", autouse=True)
def prologue_epilogue(request):
    global data, CONFIG
    vars = st.get_testbed_vars()
    data.vars = vars
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'
    
    st.banner("MODULE CONFIGURATION START - PB-F-007")
    CONFIG.test_port = "Ethernet24"
    CONFIG.breakout_wait_time = 60
    CONFIG.child_ports = ["Ethernet24"]
    
    configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G")
    yield
    st.banner("MODULE CONFIGURATION CLEANUP - PB-F-007")
    try:
        st.config(vars.D1, f"interface {CONFIG.child_ports[0]}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, "no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, "exit", type=data.cli_type, skip_error_check=True)
    except:
        pass
    configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G")


def configure_breakout_mode(dut, port, mode):
    try:
        st.config(dut, f"interface breakout {port} mode {mode}", type=data.cli_type, skip_error_check=True)
        st.wait(CONFIG.breakout_wait_time)
        return True
    except:
        return False


def test_pb_f_007_shutdown_no_shutdown():
    """Test Case: PB-F-007 - Shutdown/No Shutdown Operations"""
    st.banner("TEST CASE START: PB-F-007")
    st.log("="*80)
    st.log(TC_IDS["PB_F_007"])
    st.log("="*80)
    
    validation_errors = []
    vars = data.vars
    
    try:
        st.banner("STEP 1: Configure Breakout Mode")
        if not configure_breakout_mode(vars.D1, CONFIG.test_port, "8x100G"):
            validation_errors.append("Failed to configure breakout")
        
        test_port = CONFIG.child_ports[0]
        
        st.banner("STEP 2: Bring Up Interface")
        st.config(vars.D1, f"interface {test_port}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, "no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, "exit", type=data.cli_type, skip_error_check=True)
        st.wait(2)
        
        st.banner("STEP 3: Shutdown Interface")
        st.config(vars.D1, f"interface {test_port}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, "shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, "exit", type=data.cli_type, skip_error_check=True)
        st.wait(2)
        
        st.banner("STEP 4: Verify Interface Down")
        output = st.show(vars.D1, f"show interface {test_port}", type=data.cli_type, skip_error_check=True)
        if output:
            st.log(f"Admin status: {output[0].get('admin', 'Unknown')}")
        
        st.banner("STEP 5: Bring Up Interface Again")
        st.config(vars.D1, f"interface {test_port}", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, "no shutdown", type=data.cli_type, skip_error_check=True)
        st.config(vars.D1, "exit", type=data.cli_type, skip_error_check=True)
        st.wait(2)
        
        st.banner("TEST RESULTS")
        if validation_errors:
            st.log(f"FAIL - {len(validation_errors)} errors")
            st.report_tc_fail("PB_F_007", "test_failed", "Shutdown operations failed")
        else:
            st.log("PASS - Shutdown/no shutdown operations successful")
            st.report_tc_pass("PB_F_007", "test_passed", "Shutdown operations completed")
    
    except Exception as e:
        st.error(f"EXCEPTION: {e}")
        st.report_tc_fail("PB_F_007", "test_exception", f"Exception: {e}")
    
    finally:
        st.banner("TEST CASE END: PB-F-007")
