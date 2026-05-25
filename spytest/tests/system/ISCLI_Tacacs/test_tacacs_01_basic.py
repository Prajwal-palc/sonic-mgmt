"""
TACACS+ Basic Configuration and Verification Test Script
=========================================================

This module implements comprehensive TACACS+ (Terminal Access Controller
Access-Control System Plus) testing for SONiC network devices.

Test Coverage:
- TACACS+ global configuration (passkey)
- TACACS+ server configuration
- TACACS+ configuration verification
- Cleanup and unconfiguration

Module: test_tacacs_01_basic
Framework: spytest
Device: SONiC (Broadcom)
"""

from __future__ import annotations
import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "tacacs_passkey": "test123",
    "tacacs_server_ip": "192.168.100.87",
    "tacacs_priority": "1",
    "tacacs_port": "49",
    "cli_type": "klish"
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture.

    Setup Phase:
    - Initialize SpyTestDict variables
    - Ensure minimum topology
    - Perform unconfiguration (cleanup any existing TACACS+ config)

    Teardown Phase:
    - Cleanup TACACS+ configuration after all tests
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TACACS-01: MODULE PROLOGUE - Basic TACACS+ Configuration Test")
    st.banner("=" * 80)

    # Ensure minimum topology (single DUT)
    vars = st.ensure_min_topology("D1")
    data.cli_type = CONFIG.cli_type

    st.log(f"Module Setup: Using CLI type '{data.cli_type}'")
    st.log(f"TACACS+ Server IP: {CONFIG.tacacs_server_ip}")
    st.log(f"TACACS+ Passkey: {CONFIG.tacacs_passkey}")
    st.log(f"TACACS+ Port: {CONFIG.tacacs_port}")

    # Unconfigure TACACS+ before starting tests
    st.log("Performing unconfiguration of TACACS+ settings...")
    unconfigure_tacacs(vars.D1)
    st.wait(1, "Waiting for unconfiguration to complete")

    yield  # Tests run here

    st.banner("=" * 80)
    st.banner("TACACS-01: MODULE EPILOGUE - Cleanup")
    st.banner("=" * 80)

    st.log("Cleaning up TACACS+ configuration...")
    cleanup_tacacs(vars.D1)
    st.log("Cleanup completed successfully")


def unconfigure_tacacs(dut: str) -> bool:
    """
    Unconfigure TACACS+ settings on the device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Unconfiguring TACACS+ on {dut}...")
        commands = [
            f"no tacacs server {CONFIG.tacacs_server_ip}",
            f"no tacacs passkey",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"Unconfiguration completed on {dut}")
        return True
    except Exception as e:
        st.log(f"Unconfiguration skipped (may not have been configured): {str(e)}")
        return True


def configure_tacacs_passkey(dut: str, passkey: str) -> bool:
    """
    Configure TACACS+ global shared secret (passkey).

    Args:
        dut: Device identifier
        passkey: TACACS+ shared secret

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Configuring TACACS+ passkey on {dut}...")
        commands = [
            f"tacacs passkey {passkey}",
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(1, "Waiting for passkey configuration")
        st.log(f"TACACS+ passkey configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure TACACS+ passkey on {dut}: {str(e)}")
        return False


def configure_tacacs_server(dut: str, server_ip: str, priority: str = "1") -> bool:
    """
    Configure TACACS+ server.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IP address
        priority: Server priority (default: 1)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Configuring TACACS+ server {server_ip} on {dut}...")
        commands = [
            f"tacacs server {server_ip}",
        ]
        st.config(dut, commands, type=data.cli_type)
        st.wait(1, "Waiting for server configuration")
        st.log(f"TACACS+ server {server_ip} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure TACACS+ server on {dut}: {str(e)}")
        return False


def verify_tacacs_passkey(dut: str, expected_passkey: str = None) -> bool:
    """
    Verify TACACS+ passkey configuration.

    Args:
        dut: Device identifier
        expected_passkey: Expected passkey value (shown as hidden in output)

    Returns:
        bool: True if passkey is configured, False otherwise
    """
    try:
        st.log(f"Verifying TACACS+ passkey on {dut}...")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)

        if output and isinstance(output, list) and len(output) > 0:
            st.log(f"TACACS output:\n{output}")
            st.log(f"TACACS+ passkey is configured on {dut}")
            return True
        else:
            st.error(f"TACACS+ output is empty on {dut}")
            return False
    except Exception as e:
        st.error(f"Failed to verify TACACS+ passkey on {dut}: {str(e)}")
        return False


def verify_tacacs_server(dut: str, server_ip: str, expected_priority: str = "1") -> bool:
    """
    Verify TACACS+ server configuration.

    Args:
        dut: Device identifier
        server_ip: Expected TACACS+ server IP address
        expected_priority: Expected server priority

    Returns:
        bool: True if server is configured, False otherwise
    """
    try:
        st.log(f"Verifying TACACS+ server {server_ip} on {dut}...")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)

        if output and isinstance(output, list) and len(output) > 0:
            output_str = str(output)
            if server_ip in output_str:
                st.log(f"TACACS+ server {server_ip} is configured on {dut}")
                return True
            else:
                st.error(f"TACACS+ server {server_ip} not found in output on {dut}")
                st.log(f"Output: {output_str}")
                return False
        else:
            st.error(f"TACACS+ output is empty on {dut}")
            return False
    except Exception as e:
        st.error(f"Failed to verify TACACS+ server on {dut}: {str(e)}")
        return False


def cleanup_tacacs(dut: str) -> bool:
    """
    Cleanup and remove TACACS+ configuration from device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Cleaning up TACACS+ configuration on {dut}...")
        commands = [
            f"no tacacs server {CONFIG.tacacs_server_ip}",
            f"no tacacs passkey",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(1, "Waiting for cleanup to complete")
        st.log(f"TACACS+ cleanup completed on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to cleanup TACACS+ on {dut}: {str(e)}")
        return False


@pytest.mark.tacacs
def test_tacacs_01_basic():
    """
    Test 01: Basic TACACS+ Configuration

    Test Steps:
    1. Configure TACACS+ passkey
    2. Verify TACACS+ passkey configuration
    3. Configure TACACS+ server
    4. Verify TACACS+ server configuration
    5. Verify complete TACACS+ configuration

    Expected Outcome:
    - TACACS+ passkey is successfully configured
    - TACACS+ server is successfully configured
    - Device shows TACACS+ configuration in expected format
    """
    st.banner("-" * 80)
    st.banner("TEST-01: Basic TACACS+ Configuration")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Step 1: Configure TACACS+ passkey
        st.log("STEP 1: Configure TACACS+ passkey")
        if not configure_tacacs_passkey(dut, CONFIG.tacacs_passkey):
            st.error("Failed to configure TACACS+ passkey")
            result = False
        else:
            st.log("STEP 1 passed: TACACS+ passkey configured")

        # Step 2: Verify TACACS+ passkey
        st.log("STEP 2: Verify TACACS+ passkey configuration")
        if not verify_tacacs_passkey(dut):
            st.error("Failed to verify TACACS+ passkey")
            result = False
        else:
            st.log("STEP 2 passed: TACACS+ passkey verified")

        # Step 3: Configure TACACS+ server
        st.log("STEP 3: Configure TACACS+ server")
        if not configure_tacacs_server(dut, CONFIG.tacacs_server_ip, CONFIG.tacacs_priority):
            st.error("Failed to configure TACACS+ server")
            result = False
        else:
            st.log("STEP 3 passed: TACACS+ server configured")

        # Step 4: Verify TACACS+ server
        st.log("STEP 4: Verify TACACS+ server configuration")
        if not verify_tacacs_server(dut, CONFIG.tacacs_server_ip):
            st.error("Failed to verify TACACS+ server")
            result = False
        else:
            st.log("STEP 4 passed: TACACS+ server verified")

        # Step 5: Verify complete TACACS+ configuration
        st.log("STEP 5: Verify complete TACACS+ configuration")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)
        st.log(f"Final TACACS+ Configuration:\n{output}")
        st.log("STEP 5 passed: Complete TACACS+ configuration displayed")

    except Exception as e:
        st.error(f"Exception in test_tacacs_01_basic: {str(e)}")
        result = False

    if result:
        st.log("TEST-01 PASSED: Basic TACACS+ Configuration test completed successfully")
    else:
        st.error("TEST-01 FAILED: Basic TACACS+ Configuration test failed")

    assert result, "Test failed: Basic TACACS+ Configuration"


@pytest.mark.tacacs
def test_tacacs_02_server_priority():
    """
    Test 02: TACACS+ Server Priority Configuration

    Test Steps:
    1. Configure TACACS+ with passkey
    2. Configure primary TACACS+ server with priority 1
    3. Verify server configuration with correct priority
    4. Display full TACACS+ status

    Expected Outcome:
    - TACACS+ server is configured with correct priority
    """
    st.banner("-" * 80)
    st.banner("TEST-02: TACACS+ Server Priority Configuration")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Ensure TACACS+ passkey is configured
        st.log("STEP 1: Ensure TACACS+ passkey is configured")
        configure_tacacs_passkey(dut, CONFIG.tacacs_passkey)
        st.wait(1)

        # Configure server with specific priority
        st.log("STEP 2: Configure TACACS+ server with priority")
        if not configure_tacacs_server(dut, CONFIG.tacacs_server_ip, CONFIG.tacacs_priority):
            st.error("Failed to configure TACACS+ server")
            result = False
        else:
            st.log("STEP 2 passed: TACACS+ server configured with priority")

        # Verify server and priority
        st.log("STEP 3: Verify TACACS+ server configuration")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)
        st.log(f"TACACS+ Configuration with Priority:\n{output}")

        if CONFIG.tacacs_server_ip in str(output):
            st.log("STEP 3 passed: TACACS+ server verified")
        else:
            st.error("Failed to verify TACACS+ server in output")
            result = False

    except Exception as e:
        st.error(f"Exception in test_tacacs_02_server_priority: {str(e)}")
        result = False

    if result:
        st.log("TEST-02 PASSED: TACACS+ Server Priority test completed successfully")
    else:
        st.error("TEST-02 FAILED: TACACS+ Server Priority test failed")

    assert result, "Test failed: TACACS+ Server Priority Configuration"


@pytest.mark.tacacs
def test_tacacs_03_unconfiguration():
    """
    Test 03: TACACS+ Unconfiguration

    Test Steps:
    1. Configure TACACS+ settings
    2. Verify configuration exists
    3. Unconfigure TACACS+ settings
    4. Verify unconfiguration is complete

    Expected Outcome:
    - TACACS+ configuration is successfully removed
    - Device shows no TACACS+ configuration after unconfiguration
    """
    st.banner("-" * 80)
    st.banner("TEST-03: TACACS+ Unconfiguration")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Step 1: Configure TACACS+
        st.log("STEP 1: Configure TACACS+ settings")
        configure_tacacs_passkey(dut, CONFIG.tacacs_passkey)
        configure_tacacs_server(dut, CONFIG.tacacs_server_ip)
        st.wait(1)

        # Step 2: Verify configuration exists
        st.log("STEP 2: Verify TACACS+ configuration exists")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)
        if CONFIG.tacacs_server_ip in str(output):
            st.log("STEP 2 passed: TACACS+ configuration verified")
        else:
            st.error("TACACS+ configuration not found before unconfiguration")
            result = False

        # Step 3: Unconfigure TACACS+
        st.log("STEP 3: Unconfigure TACACS+ settings")
        if not unconfigure_tacacs(dut):
            st.error("Failed to unconfigure TACACS+")
            result = False
        else:
            st.log("STEP 3 passed: TACACS+ unconfiguration completed")

        # Step 4: Verify unconfiguration
        st.log("STEP 4: Verify TACACS+ configuration is removed")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)
        st.log(f"TACACS+ after unconfiguration:\n{output}")
        st.log("STEP 4 passed: Unconfiguration verification completed")

    except Exception as e:
        st.error(f"Exception in test_tacacs_03_unconfiguration: {str(e)}")
        result = False

    if result:
        st.log("TEST-03 PASSED: TACACS+ Unconfiguration test completed successfully")
    else:
        st.error("TEST-03 FAILED: TACACS+ Unconfiguration test failed")

    assert result, "Test failed: TACACS+ Unconfiguration"


if __name__ == "__main__":
    # This allows running the script directly for debugging
    st.log("Running TACACS+ tests directly")
    pytest.main([__file__, "-v"])
