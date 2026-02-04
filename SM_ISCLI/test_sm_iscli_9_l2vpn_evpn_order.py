"""
Test script for SM_ISCLI_9: L2VPN EVPN Configuration Order Bug

Bug Description:
When configuring BGP L2VPN EVPN address-family, if 'address-family l2vpn evpn' and 'activate'
commands are issued BEFORE the 'update-source' command, the L2VPN EVPN configuration may be lost
or not properly applied. The correct order should be: configure update-source first, then
configure the address-family.

Test Scenarios:
1. Wrong order (Bug scenario): Configure address-family before update-source
2. Correct order (Fix scenario): Configure update-source before address-family

Expected Results:
- Wrong order: L2VPN EVPN configuration may be lost after update-source is configured
- Correct order: L2VPN EVPN configuration persists and is properly applied

Author: Automated Test Generation
Date: 2025-02-04
"""

import pytest
from spytest import st, tgapi
from spytest.utils import poll_wait
from spytest.dicts import SpyTestDict
import apis.routing.bgp as bgp_api
import apis.routing.ip as ip_api

# Test configuration
CONFIG = SpyTestDict({
    "dut1_asn": "65001",
    "dut1_router_id": "1.1.1.1",
    "dut1_neighbor_ip": "10.0.0.2",
    "loopback_interface": "Loopback 0",
    "loopback_ip": "1.1.1.1/32",
})

@pytest.fixture(scope="module", autouse=True)
def sm_iscli_9_module_hooks(request):
    """Module-level setup and teardown"""
    global data
    data = SpyTestDict()
    data.cli_type = st.get_ui_type()

    # Get DUT
    data.dut1 = st.get_dut_names()[0]

    st.log("="*80)
    st.log("SM_ISCLI_9: L2VPN EVPN Configuration Order Bug Test - Module Setup")
    st.log("="*80)

    yield

    st.log("="*80)
    st.log("SM_ISCLI_9: L2VPN EVPN Configuration Order Bug Test - Module Cleanup")
    st.log("="*80)

@pytest.fixture(scope="function", autouse=True)
def sm_iscli_9_function_hooks(request):
    """Function-level setup and teardown"""
    yield

    # Cleanup after each test
    cleanup_bgp_config(data.dut1)

def cleanup_bgp_config(dut: str):
    """Clean up BGP configuration"""
    st.log(f"Cleaning up BGP configuration on {dut}")

    # Remove BGP instance
    commands = [
        f"no router bgp {CONFIG.dut1_asn}",
    ]
    st.config(dut, commands, type=data.cli_type, skip_error_check=True)

    # Remove loopback interface
    commands = [
        f"no interface {CONFIG.loopback_interface}",
    ]
    st.config(dut, commands, type=data.cli_type, skip_error_check=True)

def configure_loopback(dut: str) -> dict:
    """Configure loopback interface"""
    st.log(f"Configuring loopback interface on {dut}")

    commands = [
        f"interface {CONFIG.loopback_interface}",
        f"ip address {CONFIG.loopback_ip}",
        "exit",
    ]

    output = st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    return {"status": "success", "output": output}

def configure_bgp_wrong_order(dut: str, asn: str, router_id: str, neighbor_ip: str) -> dict:
    """
    Configure BGP with L2VPN EVPN in WRONG order (bug scenario)
    address-family BEFORE update-source
    """
    st.log(f"Configuring BGP with WRONG order (address-family before update-source) on {dut}")

    commands = [
        f"router bgp {asn}",
        f"bgp router-id {router_id}",
        f"neighbor {neighbor_ip} remote-as {asn}",
        # BUG: Configure address-family BEFORE update-source
        "address-family l2vpn evpn",
        f"neighbor {neighbor_ip} activate",
        "exit",
        # Update-source comes TOO LATE - may cause L2VPN config loss
        f"neighbor {neighbor_ip} update-source interface {CONFIG.loopback_interface}",
        "exit",
    ]

    output = st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    return {"status": "configured", "output": output, "order": "wrong"}

def configure_bgp_correct_order(dut: str, asn: str, router_id: str, neighbor_ip: str) -> dict:
    """
    Configure BGP with L2VPN EVPN in CORRECT order (fix scenario)
    update-source BEFORE address-family
    """
    st.log(f"Configuring BGP with CORRECT order (update-source before address-family) on {dut}")

    commands = [
        f"router bgp {asn}",
        f"bgp router-id {router_id}",
        f"neighbor {neighbor_ip} remote-as {asn}",
        # CORRECT: Configure update-source FIRST
        f"neighbor {neighbor_ip} update-source interface {CONFIG.loopback_interface}",
        # Then configure address-family
        "address-family l2vpn evpn",
        f"neighbor {neighbor_ip} activate",
        "exit",
        "exit",
    ]

    output = st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    return {"status": "configured", "output": output, "order": "correct"}

def verify_l2vpn_evpn_config(dut: str, neighbor_ip: str) -> dict:
    """Verify L2VPN EVPN configuration is present"""
    st.log(f"Verifying L2VPN EVPN configuration for neighbor {neighbor_ip} on {dut}")

    # Get BGP L2VPN EVPN neighbor status
    output = bgp_api.show_bgp_ipvx_neighbor_vtysh(dut, neighbor=neighbor_ip, family="l2vpn",
                                                    subtype="evpn", cli_type=data.cli_type)

    # Check if neighbor is activated in L2VPN EVPN address-family
    is_activated = False
    if output:
        for entry in output:
            if "activated" in str(entry).lower() or "evpn" in str(entry).lower():
                is_activated = True
                break

    return {
        "is_configured": is_activated,
        "neighbor": neighbor_ip,
        "output": output
    }

@pytest.mark.sm_iscli_9_wrong_order
def test_sm_iscli_9_wrong_order():
    """
    Test Case: SM_ISCLI_9 Wrong Configuration Order (Bug Scenario)

    Steps:
    1. Configure loopback interface
    2. Configure BGP with address-family BEFORE update-source
    3. Verify L2VPN EVPN configuration (may be lost)

    Expected: Configuration may be lost or inconsistent
    """
    validation_failures = []

    try:
        st.banner("SM_ISCLI_9: Testing WRONG configuration order (address-family before update-source)")

        # Step 1: Configure loopback
        result = configure_loopback(data.dut1)
        if "error" in result.get("output", "").lower():
            validation_failures.append("Failed to configure loopback interface")

        # Step 2: Configure BGP in wrong order
        result = configure_bgp_wrong_order(data.dut1, CONFIG.dut1_asn,
                                          CONFIG.dut1_router_id, CONFIG.dut1_neighbor_ip)

        st.wait(2, "Waiting for BGP configuration to settle")

        # Step 3: Verify L2VPN EVPN configuration
        verification = verify_l2vpn_evpn_config(data.dut1, CONFIG.dut1_neighbor_ip)

        st.log(f"L2VPN EVPN configuration status (wrong order): {verification['is_configured']}")
        st.log("Note: With wrong order, configuration may be lost or inconsistent")

        # Document the bug behavior
        if not verification['is_configured']:
            st.warn("BUG CONFIRMED: L2VPN EVPN configuration lost with wrong order")

    finally:
        if validation_failures:
            st.report_fail("test_case_failed", "SM_ISCLI_9 Wrong Order Test failed",
                         validation_failures)
        else:
            st.report_pass("test_case_passed", "SM_ISCLI_9 Wrong Order Test completed")

@pytest.mark.sm_iscli_9_correct_order
def test_sm_iscli_9_correct_order():
    """
    Test Case: SM_ISCLI_9 Correct Configuration Order (Fix Scenario)

    Steps:
    1. Configure loopback interface
    2. Configure BGP with update-source BEFORE address-family
    3. Verify L2VPN EVPN configuration persists

    Expected: Configuration should be properly applied and persist
    """
    validation_failures = []

    try:
        st.banner("SM_ISCLI_9: Testing CORRECT configuration order (update-source before address-family)")

        # Step 1: Configure loopback
        result = configure_loopback(data.dut1)
        if "error" in result.get("output", "").lower():
            validation_failures.append("Failed to configure loopback interface")

        # Step 2: Configure BGP in correct order
        result = configure_bgp_correct_order(data.dut1, CONFIG.dut1_asn,
                                            CONFIG.dut1_router_id, CONFIG.dut1_neighbor_ip)

        st.wait(2, "Waiting for BGP configuration to settle")

        # Step 3: Verify L2VPN EVPN configuration
        verification = verify_l2vpn_evpn_config(data.dut1, CONFIG.dut1_neighbor_ip)

        st.log(f"L2VPN EVPN configuration status (correct order): {verification['is_configured']}")

        if not verification['is_configured']:
            validation_failures.append("L2VPN EVPN configuration not found even with correct order")

    finally:
        if validation_failures:
            st.report_fail("test_case_failed", "SM_ISCLI_9 Correct Order Test failed",
                         validation_failures)
        else:
            st.report_pass("test_case_passed", "SM_ISCLI_9 Correct Order Test completed - L2VPN EVPN config persisted")
