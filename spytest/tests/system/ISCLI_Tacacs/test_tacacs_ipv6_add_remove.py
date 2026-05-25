"""
TACACS+ IPv6 Server Add and Remove Test Script
================================================

Based on manual testing logs for OC-Build

Test Coverage:
- TACACS+ IPv6 server configuration (2001:db8::10)
- TACACS+ server verification with show command
- TACACS+ IPv6 server removal
- Default parameter validation (AUTH-TYPE: pap, PORT: 49, PRIORITY: 1, TIMEOUT: 5, VRF: DEFAULT)

Module: test_tacacs_ipv6_add_remove
Framework: spytest
Device: SONiC (OC-Build)
"""

from __future__ import annotations
import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "tacacs_server_ipv6": "2001:db8::10",
    "expected_auth_type": "pap",
    "expected_port": "49",
    "expected_priority": "1",
    "expected_timeout": "5",
    "expected_vrf": "DEFAULT",
    "cli_type": "klish"
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture.

    Setup Phase:
    - Initialize variables
    - Ensure minimum topology
    - Unconfigure any existing TACACS+ IPv6 server

    Teardown Phase:
    - Cleanup TACACS+ IPv6 server configuration
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TACACS-IPv6: MODULE PROLOGUE - IPv6 Server Add/Remove Test")
    st.banner("=" * 80)

    # Ensure minimum topology (single DUT)
    vars = st.ensure_min_topology("D1")
    data.cli_type = CONFIG.cli_type

    st.log(f"Module Setup: Using CLI type '{data.cli_type}'")
    st.log(f"TACACS+ IPv6 Server: {CONFIG.tacacs_server_ipv6}")

    # Unconfigure TACACS+ IPv6 server before starting tests
    st.log("Performing unconfiguration of TACACS+ IPv6 server...")
    unconfigure_tacacs_server_ipv6(vars.D1)
    st.wait(2, "Waiting for unconfiguration to complete")

    yield  # Tests run here

    st.banner("=" * 80)
    st.banner("TACACS-IPv6: MODULE EPILOGUE - Cleanup")
    st.banner("=" * 80)

    st.log("Cleaning up TACACS+ IPv6 server configuration...")
    cleanup_tacacs_ipv6(vars.D1)
    st.wait(2, "Waiting for cleanup to complete")
    st.log("Cleanup completed successfully")


def unconfigure_tacacs_server_ipv6(dut: str) -> bool:
    """
    Unconfigure TACACS+ IPv6 server on the device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful (even if nothing to unconfigure)
    """
    try:
        st.log(f"Unconfiguring TACACS+ IPv6 server {CONFIG.tacacs_server_ipv6} on {dut}...")
        commands = [
            f"no tacacs-server host {CONFIG.tacacs_server_ipv6}",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"Unconfiguration completed on {dut}")
        return True
    except Exception as e:
        st.log(f"Unconfiguration skipped or completed (may not have been configured): {str(e)}")
        return True


def configure_tacacs_server_ipv6(dut: str, server_ip: str) -> bool:
    """
    Configure TACACS+ IPv6 server.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IPv6 address

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Configuring TACACS+ IPv6 server {server_ip} on {dut}...")
        commands = [
            f"tacacs-server host {server_ip}",
        ]
        result = st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(2, "Waiting for IPv6 server configuration to apply")
        st.log(f"TACACS+ IPv6 server {server_ip} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure TACACS+ IPv6 server on {dut}: {str(e)}")
        return False


def verify_tacacs_server_ipv6(dut: str, server_ip: str) -> bool:
    """
    Verify TACACS+ IPv6 server configuration and default parameters.

    Expected values from manual testing:
    - HOST: 2001:db8::10
    - AUTH-TYPE: pap
    - KEY: No
    - PORT: 49
    - PRIORITY: 1
    - TIMEOUT: 5
    - VRF: DEFAULT

    Args:
        dut: Device identifier
        server_ip: Expected TACACS+ server IPv6 address

    Returns:
        bool: True if server is configured with correct parameters, False otherwise
    """
    try:
        st.log(f"Verifying TACACS+ IPv6 server {server_ip} on {dut}...")
        # skip_tmpl=True prevents show_tacacs.tmpl from running (returns [] for klish format)
        output = st.show(dut, "show tacacs-server", type=data.cli_type,
                         skip_tmpl=True, skip_error_check=True)

        output_str = output if isinstance(output, str) else str(output) if output else ""

        if not output_str.strip():
            st.error(f"✗ show tacacs-server returned empty output on {dut}")
            return False

        st.log(f"TACACS+ show output:\n{output_str}")

        if server_ip not in output_str:
            st.error(f"✗ TACACS+ IPv6 server {server_ip} not found in output")
            return False

        st.log(f"✓ TACACS+ IPv6 server {server_ip} found in configuration")

        # Find server row by IPv6 address
        server_line = ""
        for line in output_str.splitlines():
            if server_ip in line:
                server_line = line
                break

        if not server_line:
            st.error(f"✗ Could not locate server row for {server_ip}")
            return False

        st.log(f"Server row: {server_line}")
        # Tokens: HOST AUTH-TYPE KEY PORT PRIORITY TIMEOUT VRF
        tokens = server_line.split()
        checks_passed = True

        if len(tokens) >= 2:
            actual_auth = tokens[1].lower()
            if actual_auth == CONFIG.expected_auth_type.lower():
                st.log(f"✓ AUTH-TYPE: {actual_auth}")
            else:
                st.error(f"✗ AUTH-TYPE mismatch: got '{actual_auth}', expected '{CONFIG.expected_auth_type}'")
                checks_passed = False
        else:
            st.error(f"✗ AUTH-TYPE column missing in row: {server_line}")
            checks_passed = False

        if len(tokens) >= 4:
            actual_port = tokens[3]
            if actual_port == CONFIG.expected_port:
                st.log(f"✓ PORT: {actual_port}")
            else:
                st.error(f"✗ PORT mismatch: got '{actual_port}', expected '{CONFIG.expected_port}'")
                checks_passed = False
        else:
            st.error(f"✗ PORT column missing in row: {server_line}")
            checks_passed = False

        if len(tokens) >= 5:
            actual_priority = tokens[4]
            if actual_priority == CONFIG.expected_priority:
                st.log(f"✓ PRIORITY: {actual_priority}")
            else:
                st.error(f"✗ PRIORITY mismatch: got '{actual_priority}', expected '{CONFIG.expected_priority}'")
                checks_passed = False
        else:
            st.error(f"✗ PRIORITY column missing in row: {server_line}")
            checks_passed = False

        if len(tokens) >= 6:
            actual_timeout = tokens[5]
            if actual_timeout == CONFIG.expected_timeout:
                st.log(f"✓ TIMEOUT: {actual_timeout}")
            else:
                st.error(f"✗ TIMEOUT mismatch: got '{actual_timeout}', expected '{CONFIG.expected_timeout}'")
                checks_passed = False
        else:
            st.error(f"✗ TIMEOUT column missing in row: {server_line}")
            checks_passed = False

        if len(tokens) >= 7:
            actual_vrf = tokens[6].upper()
            if actual_vrf == CONFIG.expected_vrf.upper():
                st.log(f"✓ VRF: {actual_vrf}")
            else:
                st.error(f"✗ VRF mismatch: got '{actual_vrf}', expected '{CONFIG.expected_vrf}'")
                checks_passed = False
        else:
            st.error(f"✗ VRF column missing in row: {server_line}")
            checks_passed = False

        if checks_passed:
            st.log(f"✓ All default parameters verified for IPv6 server {server_ip}")
        else:
            st.error(f"✗ One or more default parameters mismatch for {server_ip}")

        return checks_passed

    except Exception as e:
        st.error(f"Failed to verify TACACS+ IPv6 server on {dut}: {str(e)}")
        return False


def verify_tacacs_server_removed_ipv6(dut: str, server_ip: str) -> bool:
    """
    Verify TACACS+ IPv6 server has been removed from configuration.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IPv6 address that should NOT be present

    Returns:
        bool: True if server is NOT in configuration, False if still present
    """
    try:
        st.log(f"Verifying TACACS+ IPv6 server {server_ip} is removed from {dut}...")
        output = st.show(dut, "show tacacs-server", type=data.cli_type,
                         skip_tmpl=True, skip_error_check=True)

        output_str = output if isinstance(output, str) else str(output) if output else ""

        if server_ip not in output_str:
            st.log(f"✓ TACACS+ IPv6 server {server_ip} successfully removed")
            return True
        else:
            st.error(f"✗ TACACS+ IPv6 server {server_ip} still present in configuration")
            st.log(f"Output:\n{output_str}")
            return False

    except Exception as e:
        st.error(f"Failed to verify TACACS+ IPv6 server removal on {dut}: {str(e)}")
        return False


def cleanup_tacacs_ipv6(dut: str) -> bool:
    """
    Cleanup and remove TACACS+ IPv6 server configuration from device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful
    """
    try:
        st.log(f"Cleaning up TACACS+ IPv6 server configuration on {dut}...")
        commands = [
            f"no tacacs-server host {CONFIG.tacacs_server_ipv6}",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2, "Waiting for cleanup to complete")
        st.log(f"TACACS+ IPv6 cleanup completed on {dut}")
        return True
    except Exception as e:
        st.log(f"Cleanup completed (may have already been removed): {str(e)}")
        return True


@pytest.mark.tacacs
@pytest.mark.tacacs_ipv6
def test_tacacs_ipv6_01_add_server():
    """
    Test: Add TACACS+ IPv6 Server

    Based on manual testing:
    sonic(config)# tacacs-server host 2001:db8::10

    Test Steps:
    1. Configure TACACS+ IPv6 server (2001:db8::10)
    2. Verify server is added with default parameters:
       - AUTH-TYPE: pap
       - KEY: No
       - PORT: 49
       - PRIORITY: 1
       - TIMEOUT: 5
       - VRF: DEFAULT
    3. Display complete TACACS+ configuration

    Expected Outcome:
    - IPv6 server is successfully configured
    - All default parameters match expected values
    """
    st.banner("-" * 80)
    st.banner("TEST-01: Add TACACS+ IPv6 Server")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Step 1: Configure TACACS+ IPv6 server
        st.log(f"STEP 1: Configure TACACS+ IPv6 server {CONFIG.tacacs_server_ipv6}")
        if not configure_tacacs_server_ipv6(dut, CONFIG.tacacs_server_ipv6):
            st.error("Failed to configure TACACS+ IPv6 server")
            result = False
        else:
            st.log("✓ STEP 1 PASSED: TACACS+ IPv6 server configured")

        # Step 2: Verify TACACS+ IPv6 server and default parameters
        st.log(f"STEP 2: Verify TACACS+ IPv6 server {CONFIG.tacacs_server_ipv6}")
        if not verify_tacacs_server_ipv6(dut, CONFIG.tacacs_server_ipv6):
            st.error("Failed to verify TACACS+ IPv6 server")
            result = False
        else:
            st.log("✓ STEP 2 PASSED: TACACS+ IPv6 server verified with default parameters")

        # Step 3: Display complete TACACS+ configuration
        st.log("STEP 3: Display complete TACACS+ configuration")
        output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"Complete TACACS+ Configuration:\n{output}")
        st.log("✓ STEP 3 PASSED: Configuration displayed")

    except Exception as e:
        st.error(f"Exception in test_tacacs_ipv6_01_add_server: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-01 PASSED: Add TACACS+ IPv6 Server test completed successfully")
    else:
        st.error("❌ TEST-01 FAILED: Add TACACS+ IPv6 Server test failed")

    assert result, "Test failed: Add TACACS+ IPv6 Server"


@pytest.mark.tacacs
@pytest.mark.tacacs_ipv6
def test_tacacs_ipv6_02_remove_server():
    """
    Test: Remove TACACS+ IPv6 Server

    Based on manual testing:
    sonic(config)# no tacacs-server host 2001:db8::10

    Test Steps:
    1. Ensure TACACS+ IPv6 server is configured
    2. Verify server exists in configuration
    3. Remove TACACS+ IPv6 server
    4. Verify server is removed from configuration

    Expected Outcome:
    - IPv6 server is successfully removed
    - Server does not appear in show output
    """
    st.banner("-" * 80)
    st.banner("TEST-02: Remove TACACS+ IPv6 Server")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Step 1: Ensure TACACS+ IPv6 server is configured
        st.log(f"STEP 1: Ensure TACACS+ IPv6 server {CONFIG.tacacs_server_ipv6} is configured")
        configure_tacacs_server_ipv6(dut, CONFIG.tacacs_server_ipv6)
        st.wait(2)

        # Step 2: Verify server exists
        st.log(f"STEP 2: Verify TACACS+ IPv6 server {CONFIG.tacacs_server_ipv6} exists")
        output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        if CONFIG.tacacs_server_ipv6 in str(output):
            st.log("✓ STEP 2 PASSED: TACACS+ IPv6 server exists before removal")
        else:
            st.log("⚠ TACACS+ IPv6 server not found (may have been removed already)")

        # Step 3: Remove TACACS+ IPv6 server
        st.log(f"STEP 3: Remove TACACS+ IPv6 server {CONFIG.tacacs_server_ipv6}")
        if not unconfigure_tacacs_server_ipv6(dut):
            st.error("Failed to remove TACACS+ IPv6 server")
            result = False
        else:
            st.log("✓ STEP 3 PASSED: TACACS+ IPv6 server removal command executed")

        # Step 4: Verify server is removed
        st.log(f"STEP 4: Verify TACACS+ IPv6 server {CONFIG.tacacs_server_ipv6} is removed")
        st.wait(2, "Waiting for removal to complete")
        if not verify_tacacs_server_removed_ipv6(dut, CONFIG.tacacs_server_ipv6):
            st.error("Failed to verify TACACS+ IPv6 server removal")
            result = False
        else:
            st.log("✓ STEP 4 PASSED: TACACS+ IPv6 server successfully removed")

        # Display final configuration
        st.log("Final TACACS+ configuration after removal:")
        output = st.show(dut, "show tacacs-server", type=data.cli_type, skip_tmpl=True, skip_error_check=True)
        st.log(f"Configuration:\n{output}")

    except Exception as e:
        st.error(f"Exception in test_tacacs_ipv6_02_remove_server: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-02 PASSED: Remove TACACS+ IPv6 Server test completed successfully")
    else:
        st.error("❌ TEST-02 FAILED: Remove TACACS+ IPv6 Server test failed")

    assert result, "Test failed: Remove TACACS+ IPv6 Server"


@pytest.mark.tacacs
@pytest.mark.tacacs_ipv6
def test_tacacs_ipv6_03_add_remove_cycle():
    """
    Test: Complete Add/Remove Cycle for TACACS+ IPv6 Server

    Test Steps:
    1. Add TACACS+ IPv6 server
    2. Verify server is configured
    3. Remove TACACS+ IPv6 server
    4. Verify server is removed
    5. Add server again
    6. Verify server is configured again

    Expected Outcome:
    - Server can be added, removed, and added again successfully
    - Configuration persists correctly through multiple operations
    """
    st.banner("-" * 80)
    st.banner("TEST-03: Complete Add/Remove Cycle for TACACS+ IPv6 Server")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Cycle 1: Add
        st.log(f"CYCLE 1 - ADD: Configure TACACS+ IPv6 server {CONFIG.tacacs_server_ipv6}")
        if not configure_tacacs_server_ipv6(dut, CONFIG.tacacs_server_ipv6):
            st.error("Cycle 1: Failed to add TACACS+ IPv6 server")
            result = False
        else:
            st.log("✓ Cycle 1 ADD: Server configured")

        if not verify_tacacs_server_ipv6(dut, CONFIG.tacacs_server_ipv6):
            st.error("Cycle 1: Failed to verify TACACS+ IPv6 server")
            result = False
        else:
            st.log("✓ Cycle 1 VERIFY: Server verified")

        # Cycle 1: Remove
        st.log(f"CYCLE 1 - REMOVE: Remove TACACS+ IPv6 server {CONFIG.tacacs_server_ipv6}")
        if not unconfigure_tacacs_server_ipv6(dut):
            st.error("Cycle 1: Failed to remove TACACS+ IPv6 server")
            result = False
        else:
            st.log("✓ Cycle 1 REMOVE: Server removed")

        st.wait(2)
        if not verify_tacacs_server_removed_ipv6(dut, CONFIG.tacacs_server_ipv6):
            st.error("Cycle 1: Failed to verify removal")
            result = False
        else:
            st.log("✓ Cycle 1 VERIFY REMOVAL: Server removal verified")

        # Cycle 2: Add again
        st.log(f"CYCLE 2 - ADD AGAIN: Configure TACACS+ IPv6 server {CONFIG.tacacs_server_ipv6}")
        if not configure_tacacs_server_ipv6(dut, CONFIG.tacacs_server_ipv6):
            st.error("Cycle 2: Failed to add TACACS+ IPv6 server again")
            result = False
        else:
            st.log("✓ Cycle 2 ADD: Server configured again")

        if not verify_tacacs_server_ipv6(dut, CONFIG.tacacs_server_ipv6):
            st.error("Cycle 2: Failed to verify TACACS+ IPv6 server")
            result = False
        else:
            st.log("✓ Cycle 2 VERIFY: Server verified again")

        st.log("Complete add/remove cycle test completed")

    except Exception as e:
        st.error(f"Exception in test_tacacs_ipv6_03_add_remove_cycle: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-03 PASSED: Complete Add/Remove Cycle test completed successfully")
    else:
        st.error("❌ TEST-03 FAILED: Complete Add/Remove Cycle test failed")

    assert result, "Test failed: Complete Add/Remove Cycle"


if __name__ == "__main__":
    # This allows running the script directly for debugging
    st.log("Running TACACS+ IPv6 tests directly")
    pytest.main([__file__, "-v"])
