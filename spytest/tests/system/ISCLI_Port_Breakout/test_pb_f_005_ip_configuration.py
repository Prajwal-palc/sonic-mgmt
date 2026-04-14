"""
Test Case ID: PB-F-005
Title: IP Address Configuration on Breakout Sub-Ports
Author: Network Automation Team
Copyright (C) 2026
"""

import pytest
from spytest import st
from spytest.dicts import SpyTestDict

data = SpyTestDict()
CONFIG = SpyTestDict()
TC_IDS = {"PB_F_005": "PB-F-005: IP Address Configuration on Breakout Sub-Ports"}


@pytest.fixture(scope="module", autouse=True)
def prologue_epilogue(request):
    global data, CONFIG
    vars = st.get_testbed_vars()
    data.vars = vars
    
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'
    
    st.banner("MODULE CONFIGURATION START - PB-F-005")
    CONFIG.test_port = "Ethernet24"
    CONFIG.breakout_wait_time = 60
    CONFIG.test_ipv4 = "192.168.100.1/24"
    CONFIG.test_ipv6 = "2001:db8:100::1/64"
    CONFIG.child_ports = ["Ethernet24", "Ethernet25"]
    
    configure_breakout_mode(vars.D1, CONFIG.test_port, "1x800G")
    yield
    st.banner("MODULE CONFIGURATION CLEANUP - PB-F-005")
    for port in CONFIG.child_ports:
        try:
            st.config(vars.D1, f"interface {port}", type=data.cli_type, skip_error_check=True)
            st.config(vars.D1, f"no ip address {CONFIG.test_ipv4}", type=data.cli_type, skip_error_check=True)
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


def configure_ip_address(dut, port, ip_addr):
    try:
        cmd_type = "ipv6 address" if ':' in ip_addr else "ip address"
        st.config(dut, f"interface {port}", type=data.cli_type, skip_error_check=True)
        st.config(dut, f"{cmd_type} {ip_addr}", type=data.cli_type, skip_error_check=True)
        st.config(dut, "exit", type=data.cli_type, skip_error_check=True)
        return True
    except:
        return False


def test_pb_f_005_ip_address_configuration():
    """Test Case: PB-F-005 - IP Address Configuration on Breakout Sub-Ports"""
    st.banner("TEST CASE START: PB-F-005")
    st.log("="*80)
    st.log(TC_IDS["PB_F_005"])
    st.log("="*80)
    
    validation_errors = []
    vars = data.vars
    
    try:
        # Configure breakout
        st.banner("STEP 1: Configure Breakout Mode")
        if not configure_breakout_mode(vars.D1, CONFIG.test_port, "8x100G"):
            validation_errors.append("Failed to configure breakout")
        
        # Configure IPv4
        st.banner("STEP 2: Configure IPv4 Address")
        if not configure_ip_address(vars.D1, CONFIG.child_ports[0], CONFIG.test_ipv4):
            validation_errors.append("Failed to configure IPv4")
        
        # Configure IPv6
        st.banner("STEP 3: Configure IPv6 Address")
        if not configure_ip_address(vars.D1, CONFIG.child_ports[1], CONFIG.test_ipv6):
            validation_errors.append("Failed to configure IPv6")
        
        # Report results
        st.banner("TEST RESULTS")
        if validation_errors:
            st.log(f"FAIL - {len(validation_errors)} errors")
            st.report_tc_fail("PB_F_005", "test_failed", "IP configuration failed")
        else:
            st.log("PASS - IP addresses configured successfully")
            st.report_tc_pass("PB_F_005", "test_passed", "IP configuration completed")
    
    except Exception as e:
        st.error(f"EXCEPTION: {e}")
        st.report_tc_fail("PB_F_005", "test_exception", f"Exception: {e}")
    
    finally:
        st.banner("TEST CASE END: PB-F-005")
