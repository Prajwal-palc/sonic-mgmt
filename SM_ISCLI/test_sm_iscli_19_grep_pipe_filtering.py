"""
SM_ISCLI_19: grep Pipe Filtering Works Correctly

Test Case ID: SM_ISCLI_19  
Bug: grep filtering ineffective (FIXED)
Priority: P2

Author: Network Automation Team
Copyright (C) 2026

Description:
  Test validates that grep filtering works correctly when piped with show commands.

Expected Behavior:
  - grep should filter output correctly
  - Non-matching patterns should return empty
  - Pipe functionality should work properly
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "interfaces": ["Ethernet0", "Ethernet4", "Ethernet8", "Ethernet12"],
    "dut1_ips": ["10.1.1.1/24", "10.2.2.1/24", "10.3.3.1/24", "192.168.100.1/24"],
    "dut2_ips": ["20.1.1.1/24", "20.2.2.1/24", "20.3.3.1/24", "172.16.1.1/24"],
    "loopback_dut1_ip": "1.1.1.1/32",
    "loopback_dut2_ip": "2.2.2.2/32",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    global vars, data
    st.banner("SM_ISCLI_19: MODULE PROLOGUE")
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"
    yield
    st.banner("SM_ISCLI_19: MODULE EPILOGUE")
    cleanup_all(vars.D1)
    cleanup_all(vars.D2)


def configure_interfaces_and_loopback(dut: str, is_dut1: bool) -> bool:
    try:
        ips = CONFIG.dut1_ips if is_dut1 else CONFIG.dut2_ips
        
        # Configure interfaces
        for idx, intf in enumerate(CONFIG.interfaces):
            ipapi.config_ip_addr_interface(dut, intf, ips[idx].split('/')[0],
                                          subnet=ips[idx].split('/')[1], family="ipv4", cli_type=data.cli_type)
            commands = [f"interface {intf}", "no shutdown", "exit"]
            st.config(dut, commands, type=data.cli_type)
        
        # Configure loopback
        loopback_ip = CONFIG.loopback_dut1_ip if is_dut1 else CONFIG.loopback_dut2_ip
        commands = [
            "interface Loopback0",
            f"ip address {loopback_ip}",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type)
        return True
    except Exception as e:
        st.error(f"Config failed: {e}")
        return False


def verify_grep_filtering(dut: str) -> bool:
    try:
        st.log(f"Testing grep filtering on {dut}")
        
        # Test 1: grep with non-existent pattern (should return empty)
        output1 = st.show(dut, "show ip interfaces | grep asdf", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        if output1 and len(str(output1).strip()) > 10:
            st.log("❌ Test 1 FAILED: grep asdf returned output (should be empty)")
            return False
        st.log("✅ Test 1 PASSED: grep asdf returned empty")
        
        # Test 2: grep with specific interface (should show only that interface)
        output2 = st.show(dut, "show ip interfaces | grep Ethernet0", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        output2_str = str(output2)
        if "Ethernet0" in output2_str and "Ethernet4" not in output2_str:
            st.log("✅ Test 2 PASSED: grep Ethernet0 filtered correctly")
        else:
            st.log("❌ Test 2 FAILED: grep Ethernet0 did not filter correctly")
            return False
        
        # Test 3: grep with IP pattern
        output3 = st.show(dut, "show ip interfaces | grep \"10.1.1\"", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        output3_str = str(output3)
        if "10.1.1" in output3_str or len(output3_str.strip()) == 0:
            st.log("✅ Test 3 PASSED: grep IP pattern worked")
        else:
            st.log("❌ Test 3 FAILED: grep IP pattern did not work")
            return False
        
        return True
    except Exception as e:
        st.error(f"grep verification failed: {e}")
        return False


def cleanup_all(dut: str) -> None:
    try:
        for intf in CONFIG.interfaces:
            commands = [f"interface {intf}", "no ip address", "shutdown", "exit"]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        commands = ["no interface Loopback0"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except:
        pass


def test_sm_iscli_19_grep_pipe_filtering():
    st.banner("TEST: SM_ISCLI_19 - grep Pipe Filtering")

    validation_failures = []
    tech_support_generated = False

    try:
        st.log("STEP 1: Configure interfaces and loopback")
        if not configure_interfaces_and_loopback(vars.D1, True):
            validation_failures.append(f"Config failed on {vars.D1}")
        if not configure_interfaces_and_loopback(vars.D2, False):
            validation_failures.append(f"Config failed on {vars.D2}")

        st.log("STEP 2: Test grep filtering")
        st.wait(3)
        if not verify_grep_filtering(vars.D1):
            validation_failures.append(f"grep filtering failed on {vars.D1}")
        if not verify_grep_filtering(vars.D2):
            validation_failures.append(f"grep filtering failed on {vars.D2}")

        st.log("✅ SM_ISCLI_19 Test execution completed")

    except Exception as e:
        validation_failures.append(f"Exception: {str(e)}")

    finally:
        st.banner("CLEANUP (ALWAYS EXECUTES)")
        try:
            cleanup_all(vars.D1)
            cleanup_all(vars.D2)
        except:
            pass

        if validation_failures and not tech_support_generated:
            try:
                st.generate_tech_support([vars.D1, vars.D2], "sm_iscli_19_failures")
                tech_support_generated = True
            except:
                pass

        if validation_failures:
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.report_fail("msg", f"Test completed with {len(validation_failures)} failure(s)")
        else:
            st.log("✅ SM_ISCLI_19 Test PASSED: grep filtering works correctly")
            st.report_pass("test_case_passed")
