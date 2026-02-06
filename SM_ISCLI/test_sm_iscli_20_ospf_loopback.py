"""
SM_ISCLI_20: OSPF on Loopback Works Correctly

Test Case ID: SM_ISCLI_20
Bug: OSPF on loopback failed silently (FIXED)
Priority: P1

Author: Network Automation Team
Copyright (C) 2026

Description:
  Test validates that OSPF can be configured on loopback interfaces.

Expected Behavior:
  - OSPF configuration on loopback should work
  - Loopback should appear in "show ip ospf interface"
  - No silent failures
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

import apis.routing.ip as ipapi

vars = SpyTestDict()
data = SpyTestDict()

CONFIG = SpyTestDict({
    "interface": "Ethernet0",
    "dut1_ip": "192.168.1.1/24",
    "dut2_ip": "192.168.1.2/24",
    "dut1_loopback_ip": "1.1.1.1/32",
    "dut2_loopback_ip": "2.2.2.2/32",
    "ospf_area": "0.0.0.0",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    global vars, data
    st.banner("SM_ISCLI_20: MODULE PROLOGUE")
    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"
    yield
    st.banner("SM_ISCLI_20: MODULE EPILOGUE")
    cleanup_all(vars.D1)
    cleanup_all(vars.D2)


def configure_ospf_on_interfaces(dut: str, is_dut1: bool) -> bool:
    try:
        ip = CONFIG.dut1_ip if is_dut1 else CONFIG.dut2_ip
        loopback_ip = CONFIG.dut1_loopback_ip if is_dut1 else CONFIG.dut2_loopback_ip
        
        # Configure loopback
        commands = [
            "interface Loopback0",
            f"ip address {loopback_ip}",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type)
        
        # Configure Ethernet interface
        ipapi.config_ip_addr_interface(dut, CONFIG.interface, ip.split('/')[0],
                                      subnet=ip.split('/')[1], family="ipv4", cli_type=data.cli_type)
        commands = [f"interface {CONFIG.interface}", "no shutdown", "exit"]
        st.config(dut, commands, type=data.cli_type)
        
        # Enable OSPF
        commands = ["router ospf", "exit"]
        st.config(dut, commands, type=data.cli_type)
        
        # Configure OSPF on Ethernet interface
        commands = [
            f"interface {CONFIG.interface}",
            f"ip ospf area {CONFIG.ospf_area}",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type)
        
        # Configure OSPF on Loopback (THIS IS THE BUG TEST)
        commands = [
            "interface Loopback0",
            f"ip ospf area {CONFIG.ospf_area}",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type)
        
        return True
    except Exception as e:
        st.error(f"OSPF config failed: {e}")
        return False


def verify_ospf_on_loopback(dut: str) -> bool:
    try:
        output = st.show(dut, "show ip ospf interface", type=data.cli_type, skip_error_check=True)
        output_str = str(output)
        
        if "Loopback0" in output_str and CONFIG.ospf_area in output_str:
            st.log(f"✅ OSPF configured on Loopback0 on {dut}")
            return True
        else:
            st.log(f"❌ OSPF NOT configured on Loopback0 on {dut}")
            return False
    except Exception as e:
        st.error(f"Verification failed: {e}")
        return False


def cleanup_all(dut: str) -> None:
    try:
        commands = ["no router ospf"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        commands = [f"interface {CONFIG.interface}", "no ip address", "shutdown", "exit"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        commands = ["no interface Loopback0"]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    except:
        pass


def test_sm_iscli_20_ospf_loopback():
    st.banner("TEST: SM_ISCLI_20 - OSPF on Loopback")

    validation_failures = []
    tech_support_generated = False

    try:
        st.log("STEP 1: Configure OSPF on interfaces including loopback")
        if not configure_ospf_on_interfaces(vars.D1, True):
            validation_failures.append(f"OSPF config failed on {vars.D1}")
        if not configure_ospf_on_interfaces(vars.D2, False):
            validation_failures.append(f"OSPF config failed on {vars.D2}")

        st.log("STEP 2: Verify OSPF on loopback")
        st.wait(5)
        if not verify_ospf_on_loopback(vars.D1):
            validation_failures.append(f"OSPF on loopback verification failed on {vars.D1}")
        if not verify_ospf_on_loopback(vars.D2):
            validation_failures.append(f"OSPF on loopback verification failed on {vars.D2}")

        st.log("✅ SM_ISCLI_20 Test execution completed")

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
                st.generate_tech_support([vars.D1, vars.D2], "sm_iscli_20_failures")
                tech_support_generated = True
            except:
                pass

        if validation_failures:
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.report_fail("msg", f"Test completed with {len(validation_failures)} failure(s)")
        else:
            st.log("✅ SM_ISCLI_20 Test PASSED: OSPF works on loopback")
            st.report_pass("test_case_passed")
