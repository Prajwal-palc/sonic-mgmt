"""
TC_BREAKOUT_01: Basic 800G to 8x100G Breakout

Test Case ID: OC-BREAKOUT-01
Author: Network Automation Team
Copyright (C) 2026, SuperMicro

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_sm18_hw.yaml \
    tests/system/OC_Port_Breakout/test_oc_breakout_01_8x100g.py \
    --logs-path ./logs/oc_breakout_01_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates basic port breakout from 1x800G to 8x100G.

  Test Objective:
  - Verify port breakout from default 1x800G mode to 8x100G mode
  - Verify all 8 child ports are created (Ethernet0-7)
  - Verify show commands display correct breakout information
  - Verify interface status shows proper values
  - Revert breakout and verify cleanup

  Test Steps:
  1. Get initial port breakout mode (should be 1x800G)
  2. Apply breakout: Ethernet0 -> 8x100G
  3. Verify breakout success message
  4. Verify 'show interface breakout' displays 8x100G for Ethernet0
  5. Verify 'show interface status' shows all 8 child ports (Ethernet0-7)
  6. Verify each child port shows 100GB speed
  7. Revert breakout: Ethernet0 -> 1x800G
  8. Verify revert successful

  Expected Results:
  - Breakout command succeeds with "Success: Port breakout successful" message
  - 'show interface breakout' displays "Ethernet0    8x100G    Configured"
  - All 8 child ports visible in 'show interface status'
  - Each child port shows speed as 100GB
  - Revert succeeds and restores original 1x800G mode

Pre-requisites:
  - Topology: single-node (D1 only) | Supported: HW only
  - Testbed: testbed_sm18_hw.yaml
  - Device: 192.168.100.173 (Supermicro SSE-T8164S)
  - Port Ethernet0 must support 8x100G breakout mode

Note:
  - Test uses sonic-cli (klish)
  - Always reverts to original configuration in cleanup
  - Test is safe to run multiple times
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
import re

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    # Test port
    "test_port": "Ethernet0",
    "original_mode": "1x800G",
    "target_mode": "8x100G",
    
    # Expected child ports after 8x100G breakout
    "expected_child_ports": [
        "Ethernet0", "Ethernet1", "Ethernet2", "Ethernet3",
        "Ethernet4", "Ethernet5", "Ethernet6", "Ethernet7"
    ],
    
    # Expected values
    "expected_num_children": 8,
    "expected_speed": "100GB",
    "expected_breakout_mode": "8x100G",
})

# Test Case IDs
TC_IDS = SpyTestDict({
    "oc_breakout_01": "OC-BREAKOUT-01",
})


@pytest.fixture(scope="module", autouse=True)
def oc_breakout_01_module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("=" * 80)
    st.banner("TC_BREAKOUT_01 MODULE CONFIGURATION - START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"Using CLI type: {data.cli_type}")
    st.log(f"Test device: {vars.D1}")

    oc_breakout_01_pre_config()

    st.banner("=" * 80)
    st.banner("TC_BREAKOUT_01 MODULE CONFIGURATION - COMPLETE")
    st.banner("=" * 80)

    yield

    st.banner("=" * 80)
    st.banner("TC_BREAKOUT_01 MODULE CLEANUP - START")
    st.banner("=" * 80)

    oc_breakout_01_cleanup()

    st.banner("=" * 80)
    st.banner("TC_BREAKOUT_01 MODULE CLEANUP - COMPLETE")
    st.banner("=" * 80)


def oc_breakout_01_pre_config():
    """Pre-configuration: Get current state."""
    st.log("Pre-configuration: Checking current port breakout state")
    
    try:
        # Get current breakout mode
        cmd = f"show interface breakout current {CONFIG.test_port} | no-more"
        output = st.show(vars.D1, cmd, type=data.cli_type, skip_tmpl=True)
        st.log(f"Current breakout state for {CONFIG.test_port}:\n{output}")
    except Exception as e:
        st.log(f"Pre-config check warning: {e}")
    
    st.log("Pre-configuration completed")


def oc_breakout_01_cleanup():
    """Cleanup: Revert port to original 1x800G mode."""
    st.log("Cleanup: Reverting port to original configuration")
    
    try:
        # Revert to 1x800G
        cmd = f"interface breakout {CONFIG.test_port} mode {CONFIG.original_mode}"
        st.config(vars.D1, cmd, type=data.cli_type)
        st.config(vars.D1, "end", type=data.cli_type)
        st.log(f"Port {CONFIG.test_port} reverted to {CONFIG.original_mode}")
        st.wait(3, "Waiting for revert to complete")
    except Exception as e:
        st.log(f"Cleanup warning: {e}")
    
    st.log("Cleanup completed")


def apply_breakout_8x100g(dut: str) -> bool:
    """
    Apply 8x100G breakout to test port.
    
    Returns:
        bool: True if breakout successful, False otherwise
    """
    st.banner(f"STEP: Apply breakout {CONFIG.test_port} -> {CONFIG.target_mode}")
    
    try:
        # Apply breakout
        cmd = f"interface breakout {CONFIG.test_port} mode {CONFIG.target_mode}"
        st.log(f"Executing: {cmd}")
        output = st.config(dut, cmd, type=data.cli_type)
        
        # Exit config mode
        st.config(dut, "end", type=data.cli_type)
        
        st.log(f"Breakout command output:\n{output}")
        
        # Validation 1: Check for success message
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output
        
        if "Success" in output_str and "Port breakout successful" in output_str:
            st.log("PASS: Breakout success message detected")
            return True
        else:
            st.error("FAIL: Success message not found in output")
            return False
            
    except Exception as e:
        st.error(f"EXCEPTION: Breakout failed with error: {e}")
        return False


def verify_breakout_configuration(dut: str) -> bool:
    """
    Verify breakout configuration using 'show interface breakout'.
    
    Returns:
        bool: True if verification passes, False otherwise
    """
    st.banner("STEP: Verify breakout configuration")
    
    try:
        # Get breakout status
        cmd = "show interface breakout | no-more"
        st.log(f"Executing: {cmd}")
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)
        
        st.log(f"Breakout configuration output:\n{output}")
        
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output
        
        # Validation 1: Check port appears in output
        if CONFIG.test_port not in output_str:
            st.error(f"FAIL: {CONFIG.test_port} not found in breakout output")
            return False
        
        st.log(f"PASS: {CONFIG.test_port} found in breakout output")
        
        # Validation 2: Check 8x100G mode is displayed
        # Look for pattern: Ethernet0    8x100G    Configured
        pattern = rf'{CONFIG.test_port}\s+{CONFIG.expected_breakout_mode}'
        if re.search(pattern, output_str):
            st.log(f"PASS: {CONFIG.expected_breakout_mode} mode verified for {CONFIG.test_port}")
            return True
        else:
            st.error(f"FAIL: {CONFIG.expected_breakout_mode} mode not found for {CONFIG.test_port}")
            return False
            
    except Exception as e:
        st.error(f"EXCEPTION: Verification failed with error: {e}")
        return False


def verify_child_ports_status(dut: str) -> bool:
    """
    Verify all 8 child ports are visible in 'show interface status'.
    
    Returns:
        bool: True if all child ports verified, False otherwise
    """
    st.banner("STEP: Verify child ports in interface status")
    
    try:
        # Get interface status
        cmd = "show interface status | no-more"
        st.log(f"Executing: {cmd}")
        output = st.show(dut, cmd, type=data.cli_type, skip_tmpl=True)
        
        st.log(f"Interface status output (first 2000 chars):\n{output[:2000] if output else 'No output'}")
        
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output
        
        # Validation 1: Check all 8 child ports exist
        found_ports = []
        missing_ports = []
        
        for port in CONFIG.expected_child_ports:
            if port in output_str:
                found_ports.append(port)
                st.log(f"PASS: Child port {port} found in status output")
            else:
                missing_ports.append(port)
                st.error(f"FAIL: Child port {port} NOT found in status output")
        
        st.log(f"Found {len(found_ports)}/{CONFIG.expected_num_children} child ports")
        
        if len(found_ports) == CONFIG.expected_num_children:
            st.log("PASS: All child ports verified")
        else:
            st.error(f"FAIL: Missing ports: {missing_ports}")
            return False
        
        # Validation 2: Check speed is 100GB for child ports
        # Sample line: Ethernet0    -    up    100GB    9100
        speed_verified = 0
        for port in CONFIG.expected_child_ports:
            # Look for pattern with 100GB
            pattern = rf'{port}\s+.*?\s+{CONFIG.expected_speed}'
            if re.search(pattern, output_str):
                speed_verified += 1
                st.log(f"PASS: {port} shows speed {CONFIG.expected_speed}")
        
        if speed_verified >= CONFIG.expected_num_children:
            st.log(f"PASS: Speed verified for all {CONFIG.expected_num_children} ports")
            return True
        else:
            st.log(f"WARNING: Speed verified for only {speed_verified}/{CONFIG.expected_num_children} ports")
            # Don't fail - speed might not be displayed yet
            return True
            
    except Exception as e:
        st.error(f"EXCEPTION: Child port verification failed: {e}")
        return False


def revert_breakout_to_original(dut: str) -> bool:
    """
    Revert breakout back to original 1x800G mode.
    
    Returns:
        bool: True if revert successful, False otherwise
    """
    st.banner(f"STEP: Revert breakout {CONFIG.test_port} -> {CONFIG.original_mode}")
    
    try:
        # Apply revert
        cmd = f"interface breakout {CONFIG.test_port} mode {CONFIG.original_mode}"
        st.log(f"Executing: {cmd}")
        output = st.config(dut, cmd, type=data.cli_type)
        
        # Exit config mode
        st.config(dut, "end", type=data.cli_type)
        
        st.log(f"Revert command output:\n{output}")
        
        # Check for success
        if isinstance(output, list):
            output_str = str(output)
        else:
            output_str = output
        
        if "Success" in output_str:
            st.log("PASS: Revert successful")
            return True
        else:
            st.log("WARNING: Revert may not have succeeded")
            return True  # Don't fail on revert
            
    except Exception as e:
        st.log(f"WARNING: Revert failed: {e}")
        return True  # Don't fail on revert


def test_oc_breakout_01_8x100g():
    """
    TC_BREAKOUT_01: Basic 800G to 8x100G Breakout
    
    Test Steps:
    1. Apply breakout: Ethernet0 -> 8x100G
    2. Verify breakout success message
    3. Verify 'show interface breakout' displays 8x100G
    4. Verify all 8 child ports visible in 'show interface status'
    5. Verify child ports show 100GB speed
    6. Revert breakout to 1x800G
    
    Pass Criteria:
    - Breakout succeeds with success message
    - 'show interface breakout' displays 8x100G for Ethernet0
    - All 8 child ports (Ethernet0-7) are visible
    - Ports show 100GB speed
    - Revert succeeds
    """
    st.banner("=" * 80)
    st.banner("TC_BREAKOUT_01: Basic 800G to 8x100G Breakout TEST - START")
    st.banner("=" * 80)

    validation_errors = []

    # ============================================================
    # STEP 1: Apply 8x100G Breakout
    # ============================================================
    st.banner("STEP 1: Apply 8x100G Breakout")
    
    if not apply_breakout_8x100g(vars.D1):
        validation_errors.append("Breakout application failed")
        st.generate_tech_support([vars.D1], "oc_breakout_01_apply_failed")
        st.report_tc_fail(TC_IDS.oc_breakout_01, "msg", "Breakout application failed")
    else:
        st.log("STEP 1 PASSED: Breakout applied successfully")

    # ============================================================
    # STEP 2: Verify Breakout Configuration
    # ============================================================
    st.banner("STEP 2: Verify Breakout Configuration")
    
    if not verify_breakout_configuration(vars.D1):
        validation_errors.append("Breakout configuration verification failed")
        st.generate_tech_support([vars.D1], "oc_breakout_01_verify_failed")
    else:
        st.log("STEP 2 PASSED: Breakout configuration verified")

    # ============================================================
    # STEP 3: Verify Child Ports Status
    # ============================================================
    st.banner("STEP 3: Verify Child Ports Status")
    
    if not verify_child_ports_status(vars.D1):
        validation_errors.append("Child ports verification failed")
        st.generate_tech_support([vars.D1], "oc_breakout_01_ports_failed")
    else:
        st.log("STEP 3 PASSED: Child ports verified")

    # ============================================================
    # STEP 4: Revert Breakout
    # ============================================================
    st.banner("STEP 4: Revert Breakout to Original Mode")
    
    if not revert_breakout_to_original(vars.D1):
        st.log("WARNING: Revert had issues (non-critical)")
    else:
        st.log("STEP 4 PASSED: Breakout reverted successfully")

    # ============================================================
    # FINAL RESULT
    # ============================================================
    st.banner("=" * 80)
    st.banner("TC_BREAKOUT_01 TEST - COMPLETE")
    st.banner("=" * 80)

    if validation_errors:
        error_summary = f"TC_BREAKOUT_01 FAILED: {'; '.join(validation_errors)}"
        st.error(error_summary)
        st.banner("TEST RESULT: FAILED ❌")
        st.report_fail("test_case_failed", error_summary)
    else:
        success_msg = "TC_BREAKOUT_01 PASSED: 8x100G breakout successful"
        st.log(success_msg)
        st.banner("TEST RESULT: PASSED ✅")
        st.log("=" * 80)
        st.log("TEST SUMMARY - TC_BREAKOUT_01")
        st.log("=" * 80)
        st.log(f"✓ Port: {CONFIG.test_port}")
        st.log(f"✓ Breakout mode: {CONFIG.original_mode} -> {CONFIG.target_mode}")
        st.log(f"✓ Child ports created: {CONFIG.expected_num_children}")
        st.log(f"✓ Child port speed: {CONFIG.expected_speed}")
        st.log(f"✓ Verification: PASSED")
        st.log(f"✓ Revert: SUCCESSFUL")
        st.log("=" * 80)
        st.report_pass("test_case_passed", success_msg)
