"""
SM_ISCLI_12: Management Port Visible in show ip interface

Test Case ID: SM_ISCLI_12
Bug: Management port not shown in IS-CLI (FIXED)
Priority: P0

Author: Network Automation Team
Copyright (C) 2026

Description:
  Test validates that Management0 interface appears in "show ip interface" output.

Expected Behavior:
  - Management0 should be visible in IS-CLI output
  - Management IP address should be displayed
  - Behavior should match Click CLI
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "test_interfaces": ["Ethernet0", "Ethernet4", "Ethernet8"],
    "dut1_ips": ["192.168.1.1/24", "192.168.2.1/24", "192.168.3.1/24"],
    "dut2_ips": ["192.168.10.1/24", "192.168.20.1/24", "192.168.30.1/24"],
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    global vars, data
    st.banner("SM_ISCLI_12: MODULE PROLOGUE")
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"
    yield
    st.banner("SM_ISCLI_12: MODULE EPILOGUE")
    cleanup_interfaces(vars.D1)
    cleanup_interfaces(vars.D2)


def configure_test_interfaces(dut: str, is_dut1: bool) -> bool:
    try:
        ips = CONFIG.dut1_ips if is_dut1 else CONFIG.dut2_ips
        for idx, intf in enumerate(CONFIG.test_interfaces):
            ipapi.config_ip_addr_interface(dut, intf, ips[idx].split('/')[0],
                                          subnet=ips[idx].split('/')[1], family="ipv4", cli_type=data.cli_type)
            commands = [f"interface {intf}", "no shutdown", "exit"]
            st.config(dut, commands, type=data.cli_type)
        return True
    except Exception as e:
        st.error(f"Interface config failed: {e}")
        return False


def verify_management_visible(dut: str) -> bool:
    try:
        output = st.show(dut, "show ip interfaces", type=data.cli_type)
        output_str = str(output)
        
        if "Management0" in output_str or "eth0" in output_str:
            st.log(f"✅ Management interface visible on {dut}")
            return True
        else:
            st.log(f"❌ Management interface NOT visible on {dut}")
            return False
    except Exception as e:
        st.error(f"Verification failed: {e}")
        return False


def cleanup_interfaces(dut: str) -> None:
    try:
        for intf in CONFIG.test_interfaces:
            commands = [f"interface {intf}", "no ip address", "shutdown", "exit"]
            st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except:
        pass


def test_sm_iscli_12_management_port_visible():
    st.banner("TEST: SM_ISCLI_12 - Management Port Visibility")

    validation_failures = []
    tech_support_generated = False

    try:
        st.log("STEP 1: Configure test interfaces")
        if not configure_test_interfaces(vars.D1, True):
            validation_failures.append(f"Interface config failed on {vars.D1}")
        if not configure_test_interfaces(vars.D2, False):
            validation_failures.append(f"Interface config failed on {vars.D2}")

        st.log("STEP 2: Verify Management0 visible")
        st.wait(3)
        if not verify_management_visible(vars.D1):
            validation_failures.append(f"Management not visible on {vars.D1}")
        if not verify_management_visible(vars.D2):
            validation_failures.append(f"Management not visible on {vars.D2}")

        st.log("✅ SM_ISCLI_12 Test execution completed")

    except Exception as e:
        validation_failures.append(f"Exception: {str(e)}")

    finally:
        st.banner("CLEANUP (ALWAYS EXECUTES)")
        try:
            cleanup_interfaces(vars.D1)
            cleanup_interfaces(vars.D2)
        except:
            pass

        if validation_failures and not tech_support_generated:
            try:
                st.generate_tech_support([vars.D1, vars.D2], "sm_iscli_12_failures")
                tech_support_generated = True
            except:
                pass

        if validation_failures:
            st.log("!" * 80)
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.report_fail("msg", f"Test completed with {len(validation_failures)} failure(s)")
        else:
            st.log("✅ SM_ISCLI_12 Test PASSED")
            st.report_pass("test_case_passed")
