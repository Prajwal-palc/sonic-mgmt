"""
sFlow MULTIPLE COLLECTORS CONFIGURATION TEST
Test Case: SM_ISCLI_SFLOW_02

Feature      : sFlow (Sampling Flow) - Multi-Collector
Priority     : P2
Status       : In Development
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_02_collectors.py \
    --logs-path ./logs/sflow_collectors_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Cases for sFlow Multiple Collectors:
  - Test 1: Add multiple collectors
  - Test 2: Verify all collectors configured
  - Test 3: Remove specific collector while keeping others
  - Test 4: Verify removed collector is gone
  - Test 5: Cleanup all collectors

Pre-requisites:
  - 1 SONiC device (DUT1)
  - Testbed: testbed_2vs.yaml or compatible
  - 2 collector IPs available for testing
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# ======================================================================
# Global Variables
# ======================================================================
vars = SpyTestDict()
data = SpyTestDict()

# ======================================================================
# Test Configuration
# ======================================================================
CONFIG = SpyTestDict({
    "collector_ip_1":       "192.168.100.87",
    "collector_ip_2":       "192.168.14.139",
    "collector_port":       "6343",
    "collector_vrf":        "default",
    "sampling_rate":        "2048",
})

# ======================================================================
# Test Case IDs
# ======================================================================
TC_IDS = SpyTestDict({
    "sflow_multi_collector": "TC-SFLOW-02-001",
    "sflow_collector_removal": "TC-SFLOW-02-002",
})


# ======================================================================
# Module Fixture - Setup and Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def sflow_collectors_module_hooks(request):
    """Module-level setup and teardown for sFlow collector tests."""
    global vars, data

    st.banner("=" * 80)
    st.banner("SM_ISCLI_SFLOW_02 - SFLOW MULTIPLE COLLECTORS - MODULE START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}")
    st.log(f"CLI Type: {data.cli_type}")

    # Pre-condition: unconfigure all sFlow before tests
    unconfigure_all_sflow(vars.D1)
    st.wait(2)

    yield

    # Module cleanup
    st.banner("=" * 80)
    st.banner("SM_ISCLI_SFLOW_02 - MODULE CLEANUP")
    st.banner("=" * 80)
    try:
        unconfigure_all_sflow(vars.D1)
        st.wait(1)
    except Exception as e:
        st.log(f"Cleanup error (non-critical): {str(e)}")


# ======================================================================
# Pre-configuration and Cleanup
# ======================================================================
def unconfigure_all_sflow(dut: str):
    """Unconfigure all sFlow settings on DUT."""
    st.log("Unconfiguring all sFlow settings")

    commands = [
        "no sflow enable",
        "end"
    ]
    st.config(dut, commands, type='klish', skip_error_check=True)
    st.wait(1)


# ======================================================================
# Helper Functions - Configuration
# ======================================================================
def enable_sflow(dut: str) -> bool:
    """Enable sFlow globally on DUT."""
    st.log(f"Enabling sFlow on {dut}")

    commands = [
        "sflow enable",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"sFlow enabled on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to enable sFlow on {dut}: {str(e)}")
        return False


def add_collector(dut: str, ip: str, port: str = "6343", vrf: str = "default") -> bool:
    """Add sFlow collector to DUT."""
    st.log(f"Adding sFlow collector {ip}:{port} VRF {vrf} on {dut}")

    commands = [
        f"sflow collector {ip}",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"sFlow collector {ip} added on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to add sFlow collector {ip} on {dut}: {str(e)}")
        return False


def remove_collector(dut: str, ip: str) -> bool:
    """Remove sFlow collector from DUT."""
    st.log(f"Removing sFlow collector {ip} on {dut}")

    commands = [
        f"no sflow collector {ip}",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"sFlow collector {ip} removed on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to remove sFlow collector {ip} on {dut}: {str(e)}")
        return False


def set_sampling_rate(dut: str, rate: str) -> bool:
    """Set global sFlow sampling rate."""
    st.log(f"Setting global sFlow sampling rate to {rate} on {dut}")

    commands = [
        f"sflow sampling-rate {rate}",
        "end"
    ]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"sFlow sampling rate set to {rate} on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to set sampling rate on {dut}: {str(e)}")
        return False


# ======================================================================
# Verification Functions
# ======================================================================
def get_sflow_config(dut: str) -> str:
    """Get sFlow configuration output."""
    st.log(f"Getting sFlow configuration from {dut}")

    output = st.show(
        dut,
        "show sflow",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")
    return output_str


def verify_collector_exists(dut: str, ip: str, expect_exists: bool = True) -> bool:
    """Verify collector IP exists in sFlow configuration."""
    st.log(f"Verifying sFlow collector {ip} exists={expect_exists} on {dut}")

    output = get_sflow_config(dut)

    if expect_exists:
        if ip in output:
            st.log(f"✓ sFlow collector {ip} verified on {dut}")
            return True
        else:
            st.error(f"✗ sFlow collector {ip} NOT found on {dut}")
            return False
    else:
        if ip not in output:
            st.log(f"✓ sFlow collector {ip} successfully removed from {dut}")
            return True
        else:
            st.error(f"✗ sFlow collector {ip} still exists on {dut}")
            return False


def verify_both_collectors_exist(dut: str, ip1: str, ip2: str) -> bool:
    """Verify both collectors exist in configuration."""
    st.log(f"Verifying both collectors {ip1} and {ip2} exist on {dut}")

    output = get_sflow_config(dut)

    if ip1 in output and ip2 in output:
        st.log(f"✓ Both collectors verified on {dut}")
        return True
    else:
        st.error(f"✗ One or both collectors missing on {dut}")
        st.error(f"  Collector {ip1}: {'FOUND' if ip1 in output else 'MISSING'}")
        st.error(f"  Collector {ip2}: {'FOUND' if ip2 in output else 'MISSING'}")
        return False


# ======================================================================
# Test Functions
# ======================================================================

def test_sflow_02_multiple_collectors():
    """
    Test 1: Add Multiple sFlow Collectors
    Verify: Multiple collectors can be configured simultaneously
    """
    st.banner("=" * 80)
    st.banner("TEST 1: ADD MULTIPLE SFLOW COLLECTORS")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        st.log("STEP 1: Enable sFlow")
        if not enable_sflow(dut):
            validation_failures.append("Failed to enable sFlow")

        st.log("STEP 2: Set global sampling rate")
        if not set_sampling_rate(dut, CONFIG.sampling_rate):
            validation_failures.append("Failed to set sampling rate")

        st.log(f"STEP 3: Add first collector {CONFIG.collector_ip_1}")
        if not add_collector(dut, CONFIG.collector_ip_1, CONFIG.collector_port, CONFIG.collector_vrf):
            validation_failures.append(f"Failed to add collector {CONFIG.collector_ip_1}")

        st.log(f"STEP 4: Add second collector {CONFIG.collector_ip_2}")
        if not add_collector(dut, CONFIG.collector_ip_2, CONFIG.collector_port, CONFIG.collector_vrf):
            validation_failures.append(f"Failed to add collector {CONFIG.collector_ip_2}")

        st.wait(1)

        st.log("STEP 5: Verify both collectors are configured")
        if not verify_both_collectors_exist(dut, CONFIG.collector_ip_1, CONFIG.collector_ip_2):
            validation_failures.append("Both collectors verification failed")

        st.log("STEP 6: Verify first collector individually")
        if not verify_collector_exists(dut, CONFIG.collector_ip_1, expect_exists=True):
            validation_failures.append(f"Collector {CONFIG.collector_ip_1} verification failed")

        st.log("STEP 7: Verify second collector individually")
        if not verify_collector_exists(dut, CONFIG.collector_ip_2, expect_exists=True):
            validation_failures.append(f"Collector {CONFIG.collector_ip_2} verification failed")

    except Exception as e:
        st.error(f"Exception in test_sflow_02_multiple_collectors: {str(e)}")
        validation_failures.append(str(e))

    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("TEST 1 VALIDATION FAILURES:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"Test 1 Multiple Collectors: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 1: ADD MULTIPLE SFLOW COLLECTORS - ALL VALIDATIONS PASSED")
        st.log("=" * 80)
        st.report_pass("test_case_passed")


def test_sflow_03_collector_removal():
    """
    Test 2: Remove Specific Collector While Keeping Others
    Verify: Removing one collector doesn't affect the other
    """
    st.banner("=" * 80)
    st.banner("TEST 2: REMOVE SPECIFIC COLLECTOR")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        st.log("STEP 1: Enable sFlow (ensure enabled)")
        enable_sflow(dut)

        st.log("STEP 2: Set global sampling rate")
        set_sampling_rate(dut, CONFIG.sampling_rate)

        st.log(f"STEP 3: Add both collectors")
        add_collector(dut, CONFIG.collector_ip_1, CONFIG.collector_port)
        add_collector(dut, CONFIG.collector_ip_2, CONFIG.collector_port)
        st.wait(1)

        st.log("STEP 4: Verify both collectors exist")
        if not verify_both_collectors_exist(dut, CONFIG.collector_ip_1, CONFIG.collector_ip_2):
            validation_failures.append("Initial both collectors verification failed")

        st.log(f"STEP 5: Remove first collector {CONFIG.collector_ip_1}")
        if not remove_collector(dut, CONFIG.collector_ip_1):
            validation_failures.append(f"Failed to remove collector {CONFIG.collector_ip_1}")

        st.wait(1)

        st.log("STEP 6: Verify first collector is removed")
        if not verify_collector_exists(dut, CONFIG.collector_ip_1, expect_exists=False):
            validation_failures.append(f"Collector {CONFIG.collector_ip_1} removal verification failed")

        st.log("STEP 7: Verify second collector still exists")
        if not verify_collector_exists(dut, CONFIG.collector_ip_2, expect_exists=True):
            validation_failures.append(f"Collector {CONFIG.collector_ip_2} unexpectedly removed")

        st.log(f"STEP 8: Remove second collector {CONFIG.collector_ip_2}")
        if not remove_collector(dut, CONFIG.collector_ip_2):
            validation_failures.append(f"Failed to remove collector {CONFIG.collector_ip_2}")

        st.wait(1)

        st.log("STEP 9: Verify second collector is removed")
        if not verify_collector_exists(dut, CONFIG.collector_ip_2, expect_exists=False):
            validation_failures.append(f"Collector {CONFIG.collector_ip_2} removal verification failed")

    except Exception as e:
        st.error(f"Exception in test_sflow_03_collector_removal: {str(e)}")
        validation_failures.append(str(e))

    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("TEST 2 VALIDATION FAILURES:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"Test 2 Collector Removal: {len(validation_failures)} failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log("✅ TEST 2: REMOVE SPECIFIC COLLECTOR - ALL VALIDATIONS PASSED")
        st.log("=" * 80)
        st.report_pass("test_case_passed")

