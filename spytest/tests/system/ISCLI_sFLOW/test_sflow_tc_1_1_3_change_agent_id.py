"""
sFlow TEST CASE 1.1.3: CHANGE AGENT-ID INTERFACE
Test Case ID: TC-SFLOW-1.1.3

Feature      : sFlow (Sampling Flow)
Priority     : P1
Status       : Automated
Author       : Automated Testing Suite
Copyright (C) 2024-2026, Sonic-Mgmt

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/ISCLI_sFLOW/test_sflow_tc_1_1_3_change_agent_id.py \
    --logs-path ./logs/sflow_tc_1_1_3_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test Case 1.1.3: Change Agent-ID Interface

  Objective:
    Verify sFlow agent-id can be configured to different interface types:
    - Physical interfaces (Ethernet4, Ethernet8)
    - Loopback interface (Loopback0)
    - Management interface (Management0)
    - VLAN interface (Vlan100)
    - Reset to default

  Test Steps:
    1. Module 1 - Unconfiguration: Clean all existing sFlow config
    2. Module 2 - Configuration: Enable sFlow with base config
    3. Module 3 - Validation:
       - Set agent-id to Ethernet4 and verify
       - Change agent-id to Ethernet8 and verify
       - Reset agent-id to default and verify
       - Configure Loopback0 with IP and set as agent-id
       - Configure Management0 with IP and set as agent-id
       - Configure Vlan100 with IP and set as agent-id
       - Verify running configuration reflects changes
    4. Module 4 - Cleanup: Remove all sFlow and interface configuration

Pre-requisites:
  - 1 SONiC device (DUT1)
  - Testbed: testbed_2vs.yaml or compatible
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
    # Agent-ID interfaces
    "agent_id_eth4":        "Ethernet4",
    "agent_id_eth8":        "Ethernet8",
    "agent_id_loopback":    "Loopback0",
    "agent_id_mgmt":        "Management0",
    "agent_id_vlan":        "Vlan100",

    # Interface IPs
    "loopback_ip":          "10.10.10.1/32",
    "mgmt_ip":              "10.1.1.1/24",
    "vlan_ip":              "10.1.1.1/24",
    "vlan_id":              "100",

    # sFlow parameters
    "polling_interval":     "5",
    "sampling_rate":        "4096",
    "max_header_size":      "256",

    # Collector for testing (optional, based on manual output)
    "collector1_ip":        "192.168.100.87",
    "collector2_ip":        "192.168.100.91",
    "collector_port":       "6343",
})

# ======================================================================
# Test Case ID
# ======================================================================
TC_ID = "TC-SFLOW-1.1.3"


# ======================================================================
# Module Fixture - Setup and Teardown
# ======================================================================
@pytest.fixture(scope="module", autouse=True)
def sflow_tc_1_1_3_module_hooks(request):
    """Module-level setup and teardown for Test Case 1.1.3."""
    global vars, data

    st.banner("=" * 80)
    st.banner(f"{TC_ID} - CHANGE AGENT-ID INTERFACE - MODULE START")
    st.banner("=" * 80)

    vars = st.ensure_min_topology("D1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT1: {vars.D1}")
    st.log(f"CLI Type: {data.cli_type}")

    # Module 1: Pre-condition - Unconfigure all sFlow before tests
    st.banner("MODULE 1: UNCONFIGURATION - Cleaning existing sFlow config")
    module_1_unconfiguration(vars.D1)
    st.wait(2)

    yield

    # Module 4: Cleanup after all tests
    st.banner("MODULE 4: CLEANUP - Removing all sFlow configuration")
    module_4_cleanup(vars.D1)
    st.wait(1)


# ======================================================================
# MODULE 1: UNCONFIGURATION
# ======================================================================
def module_1_unconfiguration(dut: str):
    """
    Module 1: Unconfiguration
    Remove all existing sFlow configuration before starting tests.
    """
    st.log(f"[MODULE 1] Unconfiguring all sFlow settings on {dut}")

    commands = [
        "no sflow agent-id",
        "no sflow polling-interval",
        "no sflow sampling-rate",
        "no sflow max-header-size",
        f"no sflow collector {CONFIG.collector1_ip}",
        f"no sflow collector {CONFIG.collector2_ip}",
        "no sflow enable",
        "end"
    ]

    st.config(dut, commands, type='klish', skip_error_check=True)

    # Also cleanup any interfaces we might create
    interface_cleanup_commands = [
        f"no interface Loopback 0",
        f"no interface Vlan {CONFIG.vlan_id}",
        "end"
    ]
    st.config(dut, interface_cleanup_commands, type='klish', skip_error_check=True)

    st.wait(1)
    st.log(f"[MODULE 1] Unconfiguration completed on {dut}")


# ======================================================================
# MODULE 2: CONFIGURATION
# ======================================================================
def module_2_configuration(dut: str):
    """
    Module 2: Configuration
    Configure sFlow with base settings.
    """
    st.banner("[MODULE 2] Configuring sFlow with base parameters")

    commands = [
        f"sflow polling-interval {CONFIG.polling_interval}",
        f"sflow sampling-rate {CONFIG.sampling_rate}",
        f"sflow max-header-size {CONFIG.max_header_size}",
        f"sflow collector {CONFIG.collector1_ip}",
        f"sflow collector {CONFIG.collector2_ip}",
        "sflow enable",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"[MODULE 2] sFlow base configuration completed on {dut}")
        return True
    except Exception as e:
        st.error(f"[MODULE 2] Failed to configure sFlow on {dut}: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION - Helper Functions
# ======================================================================
def verify_agent_id_in_output(output_str: str, expected_agent_id: str) -> bool:
    """
    Verify agent-id appears in show sflow output.

    Args:
        output_str: Output from show sflow command
        expected_agent_id: Expected agent-id value (e.g., "Ethernet4", "Loopback0", "default")

    Returns:
        bool: True if agent-id matches, False otherwise
    """
    # Look for patterns like "agent-id: Ethernet4" or "agent_id: Ethernet4"
    if expected_agent_id in output_str and "agent" in output_str.lower():
        st.log(f"  ✓ Agent-id '{expected_agent_id}' found in output")
        return True
    else:
        st.error(f"  ✗ Agent-id '{expected_agent_id}' NOT found in output")
        st.log(f"Output was:\n{output_str}")
        return False


def configure_interface_ip(dut: str, interface_type: str, interface_id: str, ip_address: str) -> bool:
    """
    Configure IP address on an interface.

    Args:
        dut: Device identifier
        interface_type: Interface type (Loopback, Management, Vlan)
        interface_id: Interface ID (0, 0, 100, etc.)
        ip_address: IP address with mask (e.g., "10.10.10.1/32")

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[CONFIG] Configuring {interface_type} {interface_id} with IP {ip_address}")

    commands = [
        f"interface {interface_type} {interface_id}",
        f"ip address {ip_address}",
        "exit",
        "end"
    ]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"  ✓ {interface_type}{interface_id} configured with IP {ip_address}")
        return True
    except Exception as e:
        st.error(f"  ✗ Failed to configure {interface_type} {interface_id}: {str(e)}")
        return False


def set_agent_id(dut: str, interface: str) -> bool:
    """
    Set sFlow agent-id to specified interface.

    Args:
        dut: Device identifier
        interface: Interface to set as agent-id (e.g., "Ethernet4", "Loopback0")

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"[CONFIG] Setting agent-id to {interface}")

    commands = [f"sflow agent-id {interface}", "end"]

    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
        st.log(f"  ✓ Agent-id set to {interface}")
        return True
    except Exception as e:
        st.error(f"  ✗ Failed to set agent-id to {interface}: {str(e)}")
        return False


# ======================================================================
# MODULE 3: VALIDATION STEPS
# ======================================================================
def module_3_validation_ethernet4(dut: str) -> bool:
    """Module 3.1: Set agent-id to Ethernet4 and verify"""
    st.log("[MODULE 3.1] Setting agent-id to Ethernet4")

    if not set_agent_id(dut, CONFIG.agent_id_eth4):
        return False

    st.wait(1)

    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    return verify_agent_id_in_output(output_str, CONFIG.agent_id_eth4)


def module_3_validation_ethernet8(dut: str) -> bool:
    """Module 3.2: Change agent-id to Ethernet8 and verify"""
    st.log("[MODULE 3.2] Changing agent-id to Ethernet8")

    if not set_agent_id(dut, CONFIG.agent_id_eth8):
        return False

    st.wait(1)

    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    return verify_agent_id_in_output(output_str, CONFIG.agent_id_eth8)


def module_3_validation_default(dut: str) -> bool:
    """Module 3.3: Reset agent-id to default and verify"""
    st.log("[MODULE 3.3] Resetting agent-id to default")

    commands = ["no sflow agent-id", "end"]
    try:
        st.config(dut, commands, type='klish', skip_error_check=False)
    except Exception as e:
        st.error(f"Failed to reset agent-id: {str(e)}")
        return False

    st.wait(1)

    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    return verify_agent_id_in_output(output_str, "default")


def module_3_validation_loopback(dut: str) -> bool:
    """Module 3.4: Configure Loopback0 and set as agent-id"""
    st.log("[MODULE 3.4] Configuring Loopback0 and setting as agent-id")

    # Configure Loopback interface with IP
    if not configure_interface_ip(dut, "Loopback", "0", CONFIG.loopback_ip):
        return False

    st.wait(1)

    # Set agent-id to Loopback0
    if not set_agent_id(dut, CONFIG.agent_id_loopback):
        return False

    st.wait(1)

    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    return verify_agent_id_in_output(output_str, CONFIG.agent_id_loopback)


def module_3_validation_management(dut: str) -> bool:
    """Module 3.5: Configure Management0 and set as agent-id"""
    st.log("[MODULE 3.5] Configuring Management0 and setting as agent-id")

    # Configure Management interface with IP
    if not configure_interface_ip(dut, "Management", "0", CONFIG.mgmt_ip):
        return False

    st.wait(1)

    # Set agent-id to Management0
    if not set_agent_id(dut, CONFIG.agent_id_mgmt):
        return False

    st.wait(1)

    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    return verify_agent_id_in_output(output_str, CONFIG.agent_id_mgmt)


def module_3_validation_vlan(dut: str) -> bool:
    """Module 3.6: Configure Vlan100 and set as agent-id"""
    st.log("[MODULE 3.6] Configuring Vlan100 and setting as agent-id")

    # Configure VLAN interface with IP
    if not configure_interface_ip(dut, "Vlan", CONFIG.vlan_id, CONFIG.vlan_ip):
        return False

    st.wait(1)

    # Set agent-id to Vlan100
    if not set_agent_id(dut, CONFIG.agent_id_vlan):
        return False

    st.wait(1)

    output = st.show(dut, "show sflow", type='klish', skip_tmpl=True, skip_error_check=True)
    output_str = str(output) if output else ""
    st.log(f"show sflow output:\n{output_str}")

    return verify_agent_id_in_output(output_str, CONFIG.agent_id_vlan)


def module_3_validation_running_config(dut: str) -> bool:
    """Module 3.7: Verify running configuration"""
    st.log("[MODULE 3.7] Verifying running configuration")

    output = st.show(
        dut,
        "show running-configuration | grep sflow",
        type='klish',
        skip_tmpl=True,
        skip_error_check=True
    )
    output_str = str(output) if output else ""

    st.log(f"show running-configuration | grep sflow:\n{output_str}")

    # Verify key sFlow parameters are present
    expected_items = [
        "sflow enable",
        f"sflow agent-id {CONFIG.agent_id_vlan}",  # Should show last configured agent-id
        f"sflow polling-interval {CONFIG.polling_interval}",
        f"sflow sampling-rate {CONFIG.sampling_rate}",
    ]

    missing_items = []
    for item in expected_items:
        if item not in output_str:
            st.log(f"  Looking for: '{item}'")
            missing_items.append(item)

    if missing_items:
        st.error(f"  ✗ Missing items in running config: {missing_items}")
        return False

    st.log(f"  ✓ All expected items found in running configuration")
    return True


# ======================================================================
# MODULE 4: CLEANUP
# ======================================================================
def module_4_cleanup(dut: str):
    """
    Module 4: Cleanup
    Remove all sFlow and interface configuration after test completion.
    """
    st.log(f"[MODULE 4] Cleaning up all sFlow and interface configuration on {dut}")

    # Cleanup sFlow configuration
    sflow_commands = [
        "no sflow enable",
        "no sflow agent-id",
        "no sflow polling-interval",
        "no sflow sampling-rate",
        "no sflow max-header-size",
        f"no sflow collector {CONFIG.collector1_ip}",
        f"no sflow collector {CONFIG.collector2_ip}",
        "end"
    ]
    st.config(dut, sflow_commands, type='klish', skip_error_check=True)

    # Cleanup interfaces
    interface_commands = [
        f"no interface Loopback 0",
        f"no interface Vlan {CONFIG.vlan_id}",
        "end"
    ]
    st.config(dut, interface_commands, type='klish', skip_error_check=True)

    st.wait(1)
    st.log(f"[MODULE 4] Cleanup completed on {dut}")


# ======================================================================
# Test Function - Main Test Case
# ======================================================================
def test_sflow_tc_1_1_3_change_agent_id():
    """
    Test Case 1.1.3: Change Agent-ID Interface

    This test verifies agent-id can be configured to different interface types:
    1. Physical interface (Ethernet4)
    2. Change to another physical interface (Ethernet8)
    3. Reset to default
    4. Loopback interface (Loopback0)
    5. Management interface (Management0)
    6. VLAN interface (Vlan100)
    7. Verify running configuration
    """
    st.banner("=" * 80)
    st.banner(f"TEST CASE {TC_ID}: CHANGE AGENT-ID INTERFACE")
    st.banner("=" * 80)

    dut = vars.D1
    validation_failures = []

    try:
        # ====================================================================
        # Module 2: Configuration
        # ====================================================================
        st.banner("[MODULE 2] CONFIGURATION - Setting up sFlow base config")
        if not module_2_configuration(dut):
            validation_failures.append("[MODULE 2] Failed to configure sFlow")
            st.report_fail("msg", "Configuration failed - cannot proceed with test")
            return

        st.wait(2)

        # ====================================================================
        # Module 3: Validation - Test all agent-id interface types
        # ====================================================================
        st.banner("[MODULE 3] VALIDATION - Testing agent-id with different interfaces")

        # Test 1: Ethernet4
        st.log("STEP 1: Set agent-id to Ethernet4 and verify")
        if not module_3_validation_ethernet4(dut):
            validation_failures.append("STEP 1: Failed to set/verify agent-id Ethernet4")

        st.wait(1)

        # Test 2: Ethernet8
        st.log("STEP 2: Change agent-id to Ethernet8 and verify")
        if not module_3_validation_ethernet8(dut):
            validation_failures.append("STEP 2: Failed to change/verify agent-id Ethernet8")

        st.wait(1)

        # Test 3: Reset to default
        st.log("STEP 3: Reset agent-id to default and verify")
        if not module_3_validation_default(dut):
            validation_failures.append("STEP 3: Failed to reset agent-id to default")

        st.wait(1)

        # Test 4: Loopback0
        st.log("STEP 4: Configure Loopback0 and set as agent-id")
        if not module_3_validation_loopback(dut):
            validation_failures.append("STEP 4: Failed to configure/verify Loopback0 as agent-id")

        st.wait(1)

        # Test 5: Management0
        st.log("STEP 5: Configure Management0 and set as agent-id")
        if not module_3_validation_management(dut):
            validation_failures.append("STEP 5: Failed to configure/verify Management0 as agent-id")

        st.wait(1)

        # Test 6: Vlan100
        st.log("STEP 6: Configure Vlan100 and set as agent-id")
        if not module_3_validation_vlan(dut):
            validation_failures.append("STEP 6: Failed to configure/verify Vlan100 as agent-id")

        st.wait(1)

        # Test 7: Verify running configuration
        st.log("STEP 7: Verify running configuration")
        if not module_3_validation_running_config(dut):
            validation_failures.append("STEP 7: Running configuration validation failed")

    except Exception as e:
        st.error(f"Exception in test_sflow_tc_1_1_3_change_agent_id: {str(e)}")
        validation_failures.append(f"Unexpected exception: {str(e)}")

    # ====================================================================
    # Final Test Result
    # ====================================================================
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log(f"TEST CASE {TC_ID} VALIDATION FAILURES:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"  {idx}. {failure}")
        st.log("!" * 80)
        st.report_fail("msg", f"Test Case {TC_ID}: {len(validation_failures)} validation failure(s)")
    else:
        st.log("\n" + "=" * 80)
        st.log(f"✅ TEST CASE {TC_ID}: CHANGE AGENT-ID INTERFACE - PASSED")
        st.log("   All validations successful:")
        st.log("   ✓ Set agent-id to Ethernet4")
        st.log("   ✓ Changed agent-id to Ethernet8")
        st.log("   ✓ Reset agent-id to default")
        st.log("   ✓ Configured Loopback0 as agent-id")
        st.log("   ✓ Configured Management0 as agent-id")
        st.log("   ✓ Configured Vlan100 as agent-id")
        st.log("   ✓ Verified running configuration")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
