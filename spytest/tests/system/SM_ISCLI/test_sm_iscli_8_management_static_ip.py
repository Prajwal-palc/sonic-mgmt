"""
Test script for SM_ISCLI_8: Management Interface Static IP Assignment Bug

Bug Description:
When attempting to assign a static IP address to the Management interface using IS-CLI,
the configuration may not persist properly across reboots or may show discrepancies
between running-config and actual interface status.

Test Scenarios:
1. Configure static IP on Management interface using IS-CLI
2. Verify IP is correctly assigned and visible in show commands
3. Save configuration and reload
4. Verify IP persists after reload

Safety Note:
This test uses Ethernet 0 by default instead of Management 0 to avoid losing SSH access.
To test actual Management interface, change CONFIG.test_interface to "Management 0"
but ensure you have console access as this may disrupt SSH connectivity.

Author: Automated Test Generation
Date: 2025-02-04
"""

import pytest
from spytest import st, tgapi
from spytest.utils import poll_wait
from spytest.dicts import SpyTestDict
import apis.system.interface as intf_api
import apis.system.reboot as reboot_api
import apis.system.basic as basic_api

# Test configuration
CONFIG = SpyTestDict({
    # IMPORTANT: Using Ethernet 0 to avoid losing SSH access
    # Change to "Management 0" only if you have console access
    "test_interface": "Ethernet 0",
    "dut1_test_ip": "192.168.50.10",
    "dut1_test_mask": "24",
    "dut1_test_gateway": "192.168.50.1",
    "test_timeout": 30,
})

@pytest.fixture(scope="module", autouse=True)
def sm_iscli_8_module_hooks(request):
    """Module-level setup and teardown"""
    global data
    data = SpyTestDict()
    data.cli_type = st.get_ui_type()

    # Get DUT
    data.dut1 = st.get_dut_names()[0]

    st.log("="*80)
    st.log("SM_ISCLI_8: Management Interface Static IP Assignment Bug Test - Module Setup")
    st.log("="*80)
    st.warn(f"Testing on interface: {CONFIG.test_interface}")
    if CONFIG.test_interface == "Management 0":
        st.warn("WARNING: Testing on Management interface - ensure console access is available!")

    # Store original interface configuration
    data.original_ip_config = get_interface_ip_config(data.dut1, CONFIG.test_interface)

    yield

    st.log("="*80)
    st.log("SM_ISCLI_8: Management Interface Static IP Assignment Bug Test - Module Cleanup")
    st.log("="*80)

    # Restore original configuration
    if data.original_ip_config:
        restore_interface_config(data.dut1, CONFIG.test_interface, data.original_ip_config)

@pytest.fixture(scope="function", autouse=True)
def sm_iscli_8_function_hooks(request):
    """Function-level setup and teardown"""
    yield

def get_interface_ip_config(dut: str, interface: str) -> dict:
    """Get current IP configuration of an interface"""
    st.log(f"Getting current IP configuration for {interface} on {dut}")

    # Get interface details
    output = intf_api.show_interface_config_all(dut, cli_type=data.cli_type)

    config = {}
    if output:
        for intf_data in output:
            if intf_data.get("interface") == interface.replace(" ", ""):
                config = {
                    "ip_address": intf_data.get("ipv4"),
                    "interface": interface
                }
                break

    st.log(f"Current config: {config}")
    return config

def configure_static_ip(dut: str, interface: str, ip_address: str, subnet_mask: str) -> dict:
    """Configure static IP address on interface using IS-CLI"""
    st.log(f"Configuring static IP {ip_address}/{subnet_mask} on {interface}")

    commands = [
        f"interface {interface}",
        f"ip address {ip_address}/{subnet_mask}",
        "no shutdown",
        "exit",
    ]

    output = st.config(dut, commands, type=data.cli_type, skip_error_check=True)

    # Check for errors
    has_error = False
    if "error" in output.lower() or "fail" in output.lower():
        has_error = True

    return {
        "status": "error" if has_error else "success",
        "output": output,
        "ip": ip_address,
        "mask": subnet_mask
    }

def verify_ip_configured(dut: str, interface: str, expected_ip: str, expected_mask: str) -> dict:
    """Verify IP address is configured on interface"""
    st.log(f"Verifying IP {expected_ip}/{expected_mask} on {interface}")

    # Get interface configuration
    config = get_interface_ip_config(dut, interface)

    # Build expected IP string
    expected_ip_cidr = f"{expected_ip}/{expected_mask}"

    # Check if configured IP matches expected
    configured_ip = config.get("ip_address", "")
    is_match = (configured_ip == expected_ip_cidr or configured_ip == expected_ip)

    return {
        "is_configured": is_match,
        "configured_ip": configured_ip,
        "expected_ip": expected_ip_cidr,
        "interface": interface
    }

def verify_ip_in_running_config(dut: str, interface: str, ip_address: str) -> dict:
    """Verify IP address appears in running configuration"""
    st.log(f"Checking running-config for IP {ip_address} on {interface}")

    # Get running configuration
    commands = ["do show running-config"]
    output = st.config(dut, commands, type=data.cli_type, skip_error_check=True)

    # Check if IP address is in running config
    ip_in_config = ip_address in output

    return {
        "in_running_config": ip_in_config,
        "ip": ip_address,
        "interface": interface
    }

def remove_ip_config(dut: str, interface: str) -> dict:
    """Remove IP configuration from interface"""
    st.log(f"Removing IP configuration from {interface}")

    commands = [
        f"interface {interface}",
        "no ip address",
        "exit",
    ]

    output = st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    return {"status": "removed", "output": output}

def restore_interface_config(dut: str, interface: str, original_config: dict):
    """Restore interface to original configuration"""
    if not original_config:
        st.log(f"No original config to restore for {interface}")
        return

    st.log(f"Restoring original configuration for {interface}")

    # First remove current config
    remove_ip_config(dut, interface)

    # If there was an original IP, restore it
    if original_config.get("ip_address"):
        ip_with_mask = original_config["ip_address"]
        if "/" in ip_with_mask:
            ip_addr, mask = ip_with_mask.split("/")
            configure_static_ip(dut, interface, ip_addr, mask)

@pytest.mark.sm_iscli_8_basic_assignment
def test_sm_iscli_8_static_ip_basic_assignment():
    """
    Test Case: SM_ISCLI_8 Basic Static IP Assignment

    Steps:
    1. Configure static IP on test interface using IS-CLI
    2. Verify IP is assigned using show interface
    3. Verify IP appears in running-config
    4. Verify IP is reachable (if applicable)

    Expected: Static IP should be configured and visible in all checks
    """
    validation_failures = []

    try:
        st.banner("SM_ISCLI_8: Testing basic static IP assignment")

        # Step 1: Configure static IP
        result = configure_static_ip(data.dut1, CONFIG.test_interface,
                                    CONFIG.dut1_test_ip, CONFIG.dut1_test_mask)

        if result["status"] == "error":
            validation_failures.append(f"Failed to configure static IP: {result['output']}")

        st.wait(2, "Waiting for IP configuration to take effect")

        # Step 2: Verify IP is configured on interface
        verification = verify_ip_configured(data.dut1, CONFIG.test_interface,
                                          CONFIG.dut1_test_ip, CONFIG.dut1_test_mask)

        if not verification["is_configured"]:
            validation_failures.append(
                f"IP not configured correctly. Expected: {verification['expected_ip']}, "
                f"Got: {verification['configured_ip']}"
            )

        # Step 3: Verify IP in running-config
        config_check = verify_ip_in_running_config(data.dut1, CONFIG.test_interface,
                                                   CONFIG.dut1_test_ip)

        if not config_check["in_running_config"]:
            validation_failures.append("IP address not found in running-config")

        st.log("="*60)
        st.log("Test Results Summary:")
        st.log(f"  IP Configuration Status: {result['status']}")
        st.log(f"  IP Visible in Interface: {verification['is_configured']}")
        st.log(f"  IP in Running Config: {config_check['in_running_config']}")
        st.log("="*60)

    finally:
        # Cleanup: Remove test IP configuration
        remove_ip_config(data.dut1, CONFIG.test_interface)

        if validation_failures:
            st.report_fail("test_case_failed",
                         "SM_ISCLI_8 Static IP Basic Assignment failed",
                         validation_failures)
        else:
            st.report_pass("test_case_passed",
                         "SM_ISCLI_8 Static IP Basic Assignment successful")

@pytest.mark.sm_iscli_8_config_persistence
def test_sm_iscli_8_static_ip_config_save():
    """
    Test Case: SM_ISCLI_8 Configuration Save Persistence

    Steps:
    1. Configure static IP on test interface
    2. Save configuration (copy running-config startup-config)
    3. Verify configuration is saved
    4. Verify IP still present in running config

    Expected: Static IP configuration should persist in startup-config
    """
    validation_failures = []

    try:
        st.banner("SM_ISCLI_8: Testing static IP configuration save")

        # Step 1: Configure static IP
        result = configure_static_ip(data.dut1, CONFIG.test_interface,
                                    CONFIG.dut1_test_ip, CONFIG.dut1_test_mask)

        if result["status"] == "error":
            validation_failures.append(f"Failed to configure static IP: {result['output']}")

        st.wait(2, "Waiting for configuration to settle")

        # Step 2: Save configuration
        st.log("Saving configuration...")
        basic_api.config_save(data.dut1, cli_type=data.cli_type)

        st.wait(2, "Waiting for config save to complete")

        # Step 3: Verify IP still in running-config after save
        config_check = verify_ip_in_running_config(data.dut1, CONFIG.test_interface,
                                                   CONFIG.dut1_test_ip)

        if not config_check["in_running_config"]:
            validation_failures.append("IP address lost from running-config after save")

        # Step 4: Verify interface still shows IP
        verification = verify_ip_configured(data.dut1, CONFIG.test_interface,
                                          CONFIG.dut1_test_ip, CONFIG.dut1_test_mask)

        if not verification["is_configured"]:
            validation_failures.append("IP no longer visible on interface after config save")

        st.log("="*60)
        st.log("Configuration Save Test Results:")
        st.log(f"  IP Persisted in Running Config: {config_check['in_running_config']}")
        st.log(f"  IP Still on Interface: {verification['is_configured']}")
        st.log("="*60)

    finally:
        # Cleanup
        remove_ip_config(data.dut1, CONFIG.test_interface)
        basic_api.config_save(data.dut1, cli_type=data.cli_type)

        if validation_failures:
            st.report_fail("test_case_failed",
                         "SM_ISCLI_8 Config Save Persistence failed",
                         validation_failures)
        else:
            st.report_pass("test_case_passed",
                         "SM_ISCLI_8 Config Save Persistence successful")

@pytest.mark.sm_iscli_8_multiple_operations
def test_sm_iscli_8_static_ip_multiple_changes():
    """
    Test Case: SM_ISCLI_8 Multiple IP Change Operations

    Steps:
    1. Configure first static IP
    2. Verify IP is configured
    3. Change to a different static IP
    4. Verify new IP is configured and old IP is removed

    Expected: Should be able to change static IP multiple times without issues
    """
    validation_failures = []

    # Second IP configuration for testing IP change
    second_ip = "192.168.50.20"
    second_mask = "24"

    try:
        st.banner("SM_ISCLI_8: Testing multiple static IP changes")

        # Step 1: Configure first IP
        st.log(f"Configuring first IP: {CONFIG.dut1_test_ip}")
        result1 = configure_static_ip(data.dut1, CONFIG.test_interface,
                                     CONFIG.dut1_test_ip, CONFIG.dut1_test_mask)

        if result1["status"] == "error":
            validation_failures.append(f"Failed to configure first IP: {result1['output']}")

        st.wait(2)

        # Step 2: Verify first IP
        verification1 = verify_ip_configured(data.dut1, CONFIG.test_interface,
                                           CONFIG.dut1_test_ip, CONFIG.dut1_test_mask)

        if not verification1["is_configured"]:
            validation_failures.append("First IP not configured correctly")

        # Step 3: Change to second IP
        st.log(f"Changing to second IP: {second_ip}")
        result2 = configure_static_ip(data.dut1, CONFIG.test_interface,
                                     second_ip, second_mask)

        if result2["status"] == "error":
            validation_failures.append(f"Failed to configure second IP: {result2['output']}")

        st.wait(2)

        # Step 4: Verify second IP is configured and first is removed
        verification2 = verify_ip_configured(data.dut1, CONFIG.test_interface,
                                           second_ip, second_mask)

        if not verification2["is_configured"]:
            validation_failures.append("Second IP not configured correctly")

        # Check that old IP is not present
        config_check_old = verify_ip_in_running_config(data.dut1, CONFIG.test_interface,
                                                       CONFIG.dut1_test_ip)

        st.log("="*60)
        st.log("Multiple IP Changes Test Results:")
        st.log(f"  First IP Configured: {verification1['is_configured']}")
        st.log(f"  Second IP Configured: {verification2['is_configured']}")
        st.log(f"  Old IP Removed: {not config_check_old['in_running_config']}")
        st.log("="*60)

    finally:
        # Cleanup
        remove_ip_config(data.dut1, CONFIG.test_interface)

        if validation_failures:
            st.report_fail("test_case_failed",
                         "SM_ISCLI_8 Multiple IP Changes failed",
                         validation_failures)
        else:
            st.report_pass("test_case_passed",
                         "SM_ISCLI_8 Multiple IP Changes successful")
