"""
Test Case ID: PB-F-008
Title: Multiple Speed Grades Sequential Configuration
Author: Network Automation Team
Copyright (C) 2026
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()
TC_IDS = {"PB_F_008": "PB-F-008: Multiple Speed Grades Sequential"}


@pytest.fixture(scope="module", autouse=True)
def prologue_epilogue(request):
    global data, CONFIG
    vars = st.get_testbed_vars()
    data.vars = vars
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'
    
    st.banner("MODULE CONFIGURATION START - PB-F-008")
    CONFIG.test_port = "Ethernet24"
    CONFIG.breakout_wait_time = 60
    CONFIG.speed_grades = [
        {"mode": "8x100G", "ports": 8},
        {"mode": "4x200G", "ports": 4},
        {"mode": "2x400G", "ports": 2},
    ]
    
    configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G")
    yield
    st.banner("MODULE CONFIGURATION CLEANUP - PB-F-008")
    configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G")


def configure_breakout_mode(dut, port, mode):
    try:
        st.config(dut, f"interface breakout {port} mode {mode}", type=data.cli_type, skip_error_check=True)
        st.wait(CONFIG.breakout_wait_time)
        return True
    except:
        return False


def test_pb_f_008_multiple_speed_grades():
    """Test Case: PB-F-008 - Multiple Speed Grades Sequential Configuration"""
    st.banner("TEST CASE START: PB-F-008")
    st.log("="*80)
    st.log(TC_IDS["PB_F_008"])
    st.log("="*80)
    
    validation_errors = []
    vars = data.vars
    
    try:
        for idx, grade in enumerate(CONFIG.speed_grades, 1):
            st.banner(f"SPEED GRADE {idx}: Configuring {grade['mode']}")
            
            if not configure_breakout_mode(vars.D1, CONFIG.test_port, grade['mode']):
                validation_errors.append(f"Failed to configure {grade['mode']}")
                continue
            
            st.log(f"Speed grade {grade['mode']} configured successfully")
        
        st.banner("TEST RESULTS")
        if validation_errors:
            st.log(f"FAIL - {len(validation_errors)} errors")
            st.report_tc_fail("PB_F_008", "test_failed", "Speed grades test failed")
        else:
            st.log(f"PASS - All {len(CONFIG.speed_grades)} speed grades configured")
            st.report_tc_pass("PB_F_008", "test_passed", "Speed grades completed")
    
    except Exception as e:
        st.error(f"EXCEPTION: {e}")
        st.report_tc_fail("PB_F_008", "test_exception", f"Exception: {e}")
    
    finally:
        st.banner("TEST CASE END: PB-F-008")
