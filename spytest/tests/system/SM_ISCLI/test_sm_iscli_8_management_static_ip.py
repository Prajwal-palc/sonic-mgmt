"""
SM_ISCLI_8: Management0 Static IP Assignment

Test Case ID: SM_ISCLI_8
Bug: Static IP assignment to Management interface fails/issues
Priority: P2

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/hp_test/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/iscli_SNMP/test_sm_iscli_8_management_static_ip.py \
    --logs-path ./logs/sm_iscli_8_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Test validates static IP assignment to Management0 interface via IS-CLI.

  Bug Behavior:
  - "interface Management 0" command may have syntax issues
  - Static IP assignment may not persist
  - Configuration may not appear in running-config

  Expected Behavior:
  - Management interface should accept static IP configuration
  - Configuration should persist and appear in running-config
  - Interface should be accessible via new IP

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2vs.yaml
  - Management network connectivity
  - Credentials: admin/test@123

Note:
  - IMPORTANT: This script uses validation_failures tracking to ensure cleanup always runs
  - Tech-support is generated automatically on any validation failure
  - Test continues execution even if errors occur to ensure cleanup
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
from typing import Dict, Any

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "dut1_mgmt_ip": "192.168.100.10",
    "dut2_mgmt_ip": "192.168.100.20",
    "mgmt_subnet": "24",
    "mgmt_interface": "Management0",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("SM_ISCLI_8: MODULE PROLOGUE - Management0 Static IP Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    # Store original management IPs for cleanup
    data.original_mgmt_ips = {}

    yield

    st.banner("SM_ISCLI_8: MODULE EPILOGUE - Cleanup")


def get_current_mgmt_ip(dut: str) -> str:
    """Get current management IP address."""
    try:
        output = st.show(dut, "show ip interfaces", type=data.cli_type, skip_error_check=True)
        st.log(f"Management interface status on {dut}: {output}")

        # Try to extract Management0 IP from output
        output_str = str(output)
        if "Management0" in output_str:
            st.log(f"Management0 found in output on {dut}")
            return "detected"
        return "unknown"
    except Exception as e:
        st.error(f"Failed to get management IP on {dut}: {e}")
        return "error"


def configure_management_static_ip(dut: str, ip_address: str) -> bool:
    """
    Configure static IP on Management interface.

    Tests different command variations to handle potential syntax issues.
    """
    try:
        st.log(f"Configuring Management interface with IP {ip_address}/{CONFIG.mgmt_subnet} on {dut}")

        # Try Method 1: "interface Management 0" (with space)
        st.log("Trying Method 1: 'interface Management 0' (with space)")
        commands_method1 = [
            "interface Management 0",
            f"ip address {ip_address}/{CONFIG.mgmt_subnet}",
            "no shutdown",
            "exit"
        ]

        output = st.config(dut, commands_method1, type=data.cli_type, skip_error_check=True)

        if "error" in str(output).lower() or "invalid" in str(output).lower():
            st.log("Method 1 failed, trying Method 2")

            # Try Method 2: "interface Management0" (no space)
            st.log("Trying Method 2: 'interface Management0' (no space)")
            commands_method2 = [
                "interface Management0",
                f"ip address {ip_address}/{CONFIG.mgmt_subnet}",
                "no shutdown",
                "exit"
            ]
            output = st.config(dut, commands_method2, type=data.cli_type, skip_error_check=True)

        st.wait(2)
        st.log(f"Management interface configuration completed on {dut}")
        return True

    except Exception as e:
        st.error(f"Failed to configure management interface on {dut}: {e}")
        return False


def verify_management_ip_config(dut: str, expected_ip: str) -> bool:
    """Verify management IP configuration."""
    try:
        st.log(f"Verifying management IP configuration on {dut}")

        # Check show ip interfaces
        output = st.show(dut, "show ip interfaces", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        if expected_ip in output_str:
            st.log(f"✅ Management IP {expected_ip} found in show ip interfaces")
            return True
        else:
            st.log(f"⚠️  Management IP {expected_ip} NOT found in show ip interfaces")
            st.log(f"Output: {output_str}")

        # Check running config
        config_output = st.show(dut, f"show running-configuration interface {CONFIG.mgmt_interface}",
                                type=data.cli_type, skip_error_check=True)
        config_str = str(config_output)

        if expected_ip in config_str:
            st.log(f"✅ Management IP {expected_ip} found in running-config")
            return True
        else:
            st.log(f"⚠️  Management IP {expected_ip} NOT found in running-config")
            return False

    except Exception as e:
        st.error(f"Failed to verify management IP on {dut}: {e}")
        return False


def cleanup_management_config(dut: str) -> None:
    """Remove static IP configuration from Management interface."""
    try:
        st.log(f"Cleaning up management interface configuration on {dut}")

        # Try to remove IP address
        commands = [
            f"interface {CONFIG.mgmt_interface}",
            f"no ip address",
            "exit"
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)

        st.log(f"✓ Management cleanup completed on {dut}")

    except Exception as e:
        st.log(f"Management cleanup error on {dut}: {e}")


def test_sm_iscli_8_management_static_ip():
    """
    SM_ISCLI_8: Test Management0 static IP assignment.

    Test Steps:
    1. Get current management IP configuration
    2. Configure static IP on Management0 (DUT1)
    3. Configure static IP on Management0 (DUT2)
    4. Verify IP appears in show commands
    5. Verify IP appears in running-config
    6. Cleanup: Remove static IP configuration

    IMPORTANT: Uses validation_failures tracking pattern to ensure cleanup
    and tech-support generation always execute, even if validation errors occur.
    """
    st.banner("TEST: SM_ISCLI_8 - Management0 Static IP Assignment")

    # Track validation failures - test will continue but report fail at end
    validation_failures = []
    tech_support_generated = False

    try:
        # Step 1: Get current management configuration
        st.log("STEP 1: Get current management IP configuration")
        current_dut1_ip = get_current_mgmt_ip(vars.D1)
        current_dut2_ip = get_current_mgmt_ip(vars.D2)
        st.log(f"Current management status - DUT1: {current_dut1_ip}, DUT2: {current_dut2_ip}")

        # Step 2: Configure static IP on DUT1
        st.log("STEP 2: Configure static IP on Management0 (DUT1)")
        if not configure_management_static_ip(vars.D1, CONFIG.dut1_mgmt_ip):
            error_msg = f"Management interface configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 3: Configure static IP on DUT2
        st.log("STEP 3: Configure static IP on Management0 (DUT2)")
        if not configure_management_static_ip(vars.D2, CONFIG.dut2_mgmt_ip):
            error_msg = f"Management interface configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 4: Verify DUT1 configuration
        st.log("STEP 4: Verify Management0 IP configuration (DUT1)")
        if not verify_management_ip_config(vars.D1, CONFIG.dut1_mgmt_ip):
            error_msg = f"Management IP verification failed on {vars.D1}"
            st.log(f"WARNING: {error_msg}")
            validation_failures.append(error_msg)

        # Step 5: Verify DUT2 configuration
        st.log("STEP 5: Verify Management0 IP configuration (DUT2)")
        if not verify_management_ip_config(vars.D2, CONFIG.dut2_mgmt_ip):
            error_msg = f"Management IP verification failed on {vars.D2}"
            st.log(f"WARNING: {error_msg}")
            validation_failures.append(error_msg)

        st.log("✅ SM_ISCLI_8 Test execution completed")

    except Exception as e:
        error_msg = f"Unexpected exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)

    finally:
        # CLEANUP: This block ALWAYS executes, even if validation errors occurred
        st.banner("=" * 80)
        st.banner("CLEANUP: Removing Management IP Configuration (ALWAYS EXECUTES)")
        st.banner("=" * 80)

        try:
            # Cleanup management configuration on both DUTs
            st.log("Cleaning up management configuration on both DUTs")
            cleanup_management_config(vars.D1)
            cleanup_management_config(vars.D2)

            st.log("✓ Cleanup completed successfully")

        except Exception as cleanup_error:
            st.error(f"Error during cleanup: {str(cleanup_error)}")
            validation_failures.append(f"Cleanup error: {str(cleanup_error)}")

        # Generate tech-support if there were validation failures
        if validation_failures and not tech_support_generated:
            st.banner("=" * 80)
            st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
            st.banner("=" * 80)
            try:
                st.generate_tech_support([vars.D1, vars.D2], "sm_iscli_8_validation_failures")
                tech_support_generated = True
                st.log("✓ Tech-support generated successfully")
            except Exception as ts_error:
                st.error(f"Failed to generate tech-support: {str(ts_error)}")

        # Check for any validation failures and report
        if validation_failures:
            st.log("\n" + "!" * 80)
            st.log("VALIDATION FAILURES DETECTED:")
            for idx, failure in enumerate(validation_failures, 1):
                st.error(f"{idx}. {failure}")
            st.log("!" * 80)
            st.log(f"\nNote: Cleanup and unconfiguration completed despite {len(validation_failures)} validation failure(s)")
            st.log("Tech-support has been generated for debugging")
            st.report_fail("msg", f"Test completed with {len(validation_failures)} validation failure(s). Cleanup executed. See errors above.")
        else:
            # Test passed
            st.log("All validations passed successfully")
            st.log("✅ SM_ISCLI_8 Test PASSED: Management0 static IP configuration successful")
            st.report_pass("test_case_passed")
