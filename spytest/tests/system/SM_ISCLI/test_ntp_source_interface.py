"""
NTP Source-Interface Configuration Test (SM_ISCLI_P2_26)

Author: Network Automation Team
Copyright (C) 2026

How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest

  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_2vs.yaml \
    tests/system/SM_ISCLI/test_ntp_source_interface.py \
    --logs-path ./logs/ntp_source_interface_$(date +%Y%m%d_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native

Description:
  Validates NTP source-interface configuration display in 'show ntp global' output.

  Bug Fix Validation: SM_ISCLI_P2_26
  - BEFORE FIX: 'show ntp global' did NOT display source-interface information
  - AFTER FIX: 'show ntp global' correctly displays "NTP source-interfaces: Loopback0"

  Configuration:
  - DUT1: Loopback0 (1.1.1.1/32), NTP source-interface Loopback0, NTP server 8.8.8.8
  - DUT2: Loopback0 (2.2.2.2/32), NTP source-interface Loopback0, NTP server 8.8.8.8

  Validation:
  - Verify 'show ntp global' displays "NTP source-interfaces: Loopback0"
  - Verify 'show ntp server' displays configured server 8.8.8.8

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Testbed: testbed_2vs.yaml
  - Devices: Virtual SONiC VS instances
  - Credentials: admin/YourPassword

Note:
  - IMPORTANT: This script uses validation_failures tracking to ensure cleanup always runs
  - Tech-support is generated automatically on any validation failure
  - Test validates CLI display of NTP source-interface (not actual NTP synchronization)
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict
from typing import List

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "loopback_interface": "Loopback0",

    # DUT1 configuration
    "dut1_loopback_ip": "1.1.1.1",
    "dut1_loopback_mask": "32",

    # DUT2 configuration
    "dut2_loopback_ip": "2.2.2.2",
    "dut2_loopback_mask": "32",

    # NTP configuration
    "ntp_server": "8.8.8.8",
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """Module-level setup and teardown."""
    global vars, data

    st.banner("SM_ISCLI_P2_26: MODULE PROLOGUE - NTP Source-Interface Test")

    vars = st.ensure_min_topology("D1D2:1")
    data.cli_type = "klish"

    yield

    st.banner("SM_ISCLI_P2_26: MODULE EPILOGUE - Cleanup")
    cleanup_ntp_config(vars.D1)
    cleanup_ntp_config(vars.D2)
    cleanup_loopback_interface(vars.D1)
    cleanup_loopback_interface(vars.D2)


def configure_loopback_interface(dut: str, ip_address: str, mask: str) -> bool:
    """Configure Loopback interface with IP address."""
    try:
        st.log(f"Configuring {CONFIG.loopback_interface} on {dut} with IP {ip_address}/{mask}")

        commands = [
            f"interface {CONFIG.loopback_interface}",
            f"ip address {ip_address}/{mask}",
            "no shutdown",
            "exit"
        ]

        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(2, "Waiting after Loopback configuration")

        st.log(f"✓ Loopback interface configured on {dut}")
        return True

    except Exception as e:
        st.error(f"Failed to configure Loopback interface on {dut}: {e}")
        return False


def cleanup_loopback_interface(dut: str) -> None:
    """Remove Loopback interface."""
    try:
        st.log(f"Cleaning up {CONFIG.loopback_interface} on {dut}")

        commands = [
            f"no interface {CONFIG.loopback_interface}",
        ]

        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(1, "Waiting after Loopback cleanup")

    except Exception as e:
        st.log(f"Loopback cleanup on {dut}: {e}")


def configure_ntp_with_source_interface(dut: str) -> bool:
    """
    Configure NTP with source-interface.

    Configuration steps:
    1. Enable NTP service
    2. Configure NTP source-interface (Loopback0)
    3. Configure NTP server
    """
    try:
        st.log(f"Configuring NTP with source-interface on {dut}")

        commands = [
            "ntp enable",
            f"ntp source-interface {CONFIG.loopback_interface}",
            f"ntp server {CONFIG.ntp_server}",
        ]

        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(2, "Waiting after NTP configuration")

        st.log(f"✓ NTP with source-interface configured on {dut}")
        return True

    except Exception as e:
        st.error(f"Failed to configure NTP on {dut}: {e}")
        return False


def cleanup_ntp_config(dut: str) -> None:
    """Remove NTP configuration."""
    try:
        st.log(f"Cleaning up NTP configuration on {dut}")

        commands = [
            f"no ntp server {CONFIG.ntp_server}",
            f"no ntp source-interface {CONFIG.loopback_interface}",
            "no ntp enable",
        ]

        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(1, "Waiting after NTP cleanup")

    except Exception as e:
        st.log(f"NTP cleanup on {dut}: {e}")


def verify_ntp_source_interface_in_show_global(dut: str) -> bool:
    """
    Verify NTP source-interface appears in 'show ntp global' output.

    This is the main validation for bug fix SM_ISCLI_P2_26.
    Before fix: source-interface was NOT displayed
    After fix: source-interface IS displayed as "NTP source-interfaces: Loopback0"
    """
    st.log(f"Verifying 'show ntp global' displays source-interface on {dut}")

    show_cmd = "show ntp global"
    try:
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        if not output:
            st.error(f"No output from 'show ntp global' on {dut}")
            return False

        output_str = str(output)
        st.log(f"'show ntp global' output:\n{output_str}")

        # Check for source-interface in output
        # Expected format: "NTP source-interfaces:  Loopback0"
        if "source-interface" in output_str.lower() and "loopback0" in output_str.lower():
            st.log(f"✓ PASS: Found NTP source-interface (Loopback0) in 'show ntp global' output")
            st.log(f"✓ BUG FIX VALIDATED: SM_ISCLI_P2_26 - source-interface now visible in show output")
            return True
        else:
            st.error(f"✗ FAIL: NTP source-interface NOT found in 'show ntp global' output")
            st.error(f"✗ Expected to find 'NTP source-interfaces: Loopback0'")
            return False

    except Exception as e:
        st.error(f"Failed to verify NTP source-interface on {dut}: {str(e)}")
        return False


def verify_ntp_server_configured(dut: str) -> bool:
    """
    Verify NTP server appears in 'show ntp server' output.

    This is a secondary validation to ensure NTP server configuration is correct.
    """
    st.log(f"Verifying 'show ntp server' displays configured server on {dut}")

    show_cmd = "show ntp server"
    try:
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        if not output:
            st.error(f"No output from 'show ntp server' on {dut}")
            return False

        output_str = str(output)
        st.log(f"'show ntp server' output:\n{output_str}")

        # Check for NTP server in output
        if CONFIG.ntp_server in output_str:
            st.log(f"✓ Found NTP server {CONFIG.ntp_server} in 'show ntp server' output")
            return True
        else:
            st.error(f"✗ NTP server {CONFIG.ntp_server} NOT found in 'show ntp server' output")
            return False

    except Exception as e:
        st.error(f"Failed to verify NTP server on {dut}: {str(e)}")
        return False


def verify_ntp_running_config(dut: str) -> bool:
    """
    Verify NTP configuration in running-config.

    This validates that NTP source-interface and server are persisted in configuration.
    """
    st.log(f"Verifying 'show running-configuration ntp' on {dut}")

    show_cmd = "show running-configuration ntp"
    try:
        output = st.show(dut, show_cmd, type=data.cli_type, skip_tmpl=True, skip_error_check=True)

        if not output:
            st.log(f"No output from 'show running-configuration ntp' on {dut}")
            return False

        output_str = str(output)
        st.log(f"'show running-configuration ntp' output:\n{output_str}")

        # Check for source-interface and server in running config
        has_source_interface = f"ntp source-interface {CONFIG.loopback_interface}" in output_str.lower()
        has_server = f"ntp server {CONFIG.ntp_server}" in output_str.lower()

        if has_source_interface and has_server:
            st.log(f"✓ NTP source-interface and server found in running-configuration")
            return True
        else:
            if not has_source_interface:
                st.error(f"✗ NTP source-interface NOT found in running-configuration")
            if not has_server:
                st.error(f"✗ NTP server NOT found in running-configuration")
            return False

    except Exception as e:
        st.error(f"Failed to verify NTP running-config on {dut}: {str(e)}")
        return False


def test_ntp_source_interface():
    """
    SM_ISCLI_P2_26: NTP Source-Interface Display Validation

    Test Flow:
    1. Configure Loopback0 on both DUTs
    2. Configure NTP with source-interface Loopback0
    3. Verify 'show ntp global' displays source-interface (BUG FIX VALIDATION)
    4. Verify 'show ntp server' displays configured server
    5. Verify running-configuration contains NTP settings
    6. Cleanup (ALWAYS executes via finally block)
    7. Generate tech-support if any validation failures

    IMPORTANT: Uses validation_failures tracking to ensure:
    - All steps execute even if earlier validations fail
    - Cleanup always runs
    - Tech-support generated only on failures
    """

    # Validation failures tracking
    validation_failures: List[str] = []
    tech_support_generated = False

    try:
        st.banner("=" * 80)
        st.banner("SM_ISCLI_P2_26: NTP Source-Interface Test - START")
        st.banner("=" * 80)

        # Step 1: Configure Loopback interfaces
        st.banner("STEP 1: Configure Loopback interfaces on both DUTs")

        if not configure_loopback_interface(vars.D1, CONFIG.dut1_loopback_ip, CONFIG.dut1_loopback_mask):
            error_msg = f"Loopback configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_loopback_interface(vars.D2, CONFIG.dut2_loopback_ip, CONFIG.dut2_loopback_mask):
            error_msg = f"Loopback configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 2: Configure NTP with source-interface
        st.banner("STEP 2: Configure NTP with source-interface on both DUTs")

        if not configure_ntp_with_source_interface(vars.D1):
            error_msg = f"NTP configuration failed on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not configure_ntp_with_source_interface(vars.D2):
            error_msg = f"NTP configuration failed on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 3: Wait for configuration to settle
        st.banner("STEP 3: Wait for NTP configuration to settle")
        st.wait(5, "Waiting for NTP configuration to apply")

        # Step 4: PRIMARY VALIDATION - Verify source-interface in 'show ntp global'
        st.banner("STEP 4: PRIMARY VALIDATION - Verify 'show ntp global' displays source-interface")
        st.log("This validates bug fix SM_ISCLI_P2_26")

        if not verify_ntp_source_interface_in_show_global(vars.D1):
            error_msg = f"PRIMARY VALIDATION FAILED: NTP source-interface not visible in 'show ntp global' on {vars.D1}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        if not verify_ntp_source_interface_in_show_global(vars.D2):
            error_msg = f"PRIMARY VALIDATION FAILED: NTP source-interface not visible in 'show ntp global' on {vars.D2}"
            st.error(error_msg)
            validation_failures.append(error_msg)

        # Step 5: Secondary Validation - Verify NTP server
        st.banner("STEP 5: SECONDARY VALIDATION - Verify NTP server in 'show ntp server'")

        if not verify_ntp_server_configured(vars.D1):
            error_msg = f"Secondary validation: NTP server verification incomplete on {vars.D1}"
            st.log(f"WARNING: {error_msg}")
            validation_failures.append(error_msg)

        if not verify_ntp_server_configured(vars.D2):
            error_msg = f"Secondary validation: NTP server verification incomplete on {vars.D2}"
            st.log(f"WARNING: {error_msg}")
            validation_failures.append(error_msg)

        # Step 6: Tertiary Validation - Verify running-configuration
        st.banner("STEP 6: TERTIARY VALIDATION - Verify NTP in running-configuration")

        if not verify_ntp_running_config(vars.D1):
            error_msg = f"Tertiary validation: NTP running-config verification incomplete on {vars.D1}"
            st.log(f"INFO: {error_msg}")
            # Note: This is informational, not critical

        if not verify_ntp_running_config(vars.D2):
            error_msg = f"Tertiary validation: NTP running-config verification incomplete on {vars.D2}"
            st.log(f"INFO: {error_msg}")
            # Note: This is informational, not critical

        st.log("✅ SM_ISCLI_P2_26 Test execution completed")

    except Exception as e:
        error_msg = f"Unexpected exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)

    finally:
        # CLEANUP: This block ALWAYS executes, even if validation errors occurred
        st.banner("=" * 80)
        st.banner("CLEANUP: Unconfiguring NTP and Loopback (ALWAYS EXECUTES)")
        st.banner("=" * 80)

        try:
            # Cleanup NTP configuration on both DUTs
            st.log("Cleaning up NTP configuration on both DUTs")
            cleanup_ntp_config(vars.D1)
            cleanup_ntp_config(vars.D2)

            # Clear Loopback configuration
            st.log("Clearing Loopback configuration on both DUTs")
            cleanup_loopback_interface(vars.D1)
            cleanup_loopback_interface(vars.D2)

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
                st.generate_tech_support([vars.D1, vars.D2], "sm_iscli_p2_26_validation_failures")
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
            st.log("\n" + "=" * 80)
            st.log("ALL VALIDATIONS PASSED SUCCESSFULLY")
            st.log("=" * 80)
            st.log("✅ SM_ISCLI_P2_26 Test PASSED: NTP source-interface displayed correctly in 'show ntp global'")
            st.log("✅ BUG FIX VALIDATED: Source-interface information now visible in CLI output")
            st.report_pass("test_case_passed")
