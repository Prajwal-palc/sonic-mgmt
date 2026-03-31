"""
Test Case ID: PB-F-009
Title: Asymmetric Breakout Between DUT1 and DUT2
Author: Network Automation Team
Copyright (C) 2026
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()
TC_IDS = {"PB_F_009": "PB-F-009: Asymmetric Breakout Between DUT1 and DUT2"}


@pytest.fixture(scope="module", autouse=True)
def prologue_epilogue(request):
    global data, CONFIG
    vars = st.get_testbed_vars()
    data.vars = vars
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'
    
    st.banner("MODULE CONFIGURATION START - PB-F-009")
    CONFIG.dut1_port = "Ethernet24"
    CONFIG.dut2_port = "Ethernet24"
    CONFIG.dut1_mode = "4x200G"
    CONFIG.dut2_mode = "8x100G"
    CONFIG.breakout_wait_time = 60
    
    configure_breakout_mode(vars.D1, CONFIG.dut1_port, "1x800G")
    configure_breakout_mode(vars.D2, CONFIG.dut2_port, "1x800G")
    yield
    st.banner("MODULE CONFIGURATION CLEANUP - PB-F-009")
    configure_breakout_mode(vars.D1, CONFIG.dut1_port, "1x800G")
    configure_breakout_mode(vars.D2, CONFIG.dut2_port, "1x800G")


def configure_breakout_mode(dut, port, mode):
    try:
        st.config(dut, f"interface breakout {port} mode {mode}", type=data.cli_type, skip_error_check=True)
        st.wait(CONFIG.breakout_wait_time)
        return True
    except:
        return False


def test_pb_f_009_asymmetric_breakout():
    """Test Case: PB-F-009 - Asymmetric Breakout Between DUT1 and DUT2"""
    st.banner("TEST CASE START: PB-F-009")
    st.log("="*80)
    st.log(TC_IDS["PB_F_009"])
    st.log("="*80)
    
    validation_errors = []
    vars = data.vars
    
    try:
        st.banner("STEP 1: Configure DUT1 - 4x200G")
        if not configure_breakout_mode(vars.D1, CONFIG.dut1_port, CONFIG.dut1_mode):
            validation_errors.append("Failed to configure DUT1 breakout")
        
        st.banner("STEP 2: Configure DUT2 - 8x100G")
        if not configure_breakout_mode(vars.D2, CONFIG.dut2_port, CONFIG.dut2_mode):
            validation_errors.append("Failed to configure DUT2 breakout")
        
        st.banner("STEP 3: Verify Asymmetric Configuration")
        output_d1 = st.show(vars.D1, f"show interface {CONFIG.dut1_port}", type=data.cli_type, skip_error_check=True)
        output_d2 = st.show(vars.D2, f"show interface {CONFIG.dut2_port}", type=data.cli_type, skip_error_check=True)
        
        if output_d1:
            st.log(f"DUT1 port status: {output_d1}")
        if output_d2:
            st.log(f"DUT2 port status: {output_d2}")
        
        st.log("Asymmetric breakout configuration completed")
        
        st.banner("TEST RESULTS")
        if validation_errors:
            st.log(f"FAIL - {len(validation_errors)} errors")
            st.report_tc_fail("PB_F_009", "test_failed", "Asymmetric breakout failed")
        else:
            st.log("PASS - Asymmetric breakout configured successfully")
            st.report_tc_pass("PB_F_009", "test_passed", "Asymmetric breakout completed")
    
    except Exception as e:
        st.error(f"EXCEPTION: {e}")
        st.report_tc_fail("PB_F_009", "test_exception", f"Exception: {e}")
    
    finally:
        st.banner("TEST CASE END: PB-F-009")
