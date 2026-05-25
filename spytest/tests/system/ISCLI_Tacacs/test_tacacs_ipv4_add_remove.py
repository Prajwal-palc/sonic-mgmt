"""
TACACS+ IPv4 Server Add and Remove Test Script
================================================

Based on manual testing logs for OC-Build

Test Coverage:
- TACACS+ IPv4 server configuration (192.168.100.87)
- TACACS+ server verification with show command
- TACACS+ IPv4 server removal
- Default parameter validation (AUTH-TYPE: pap, PORT: 49, PRIORITY: 1, TIMEOUT: 5, VRF: DEFAULT)

Module: test_tacacs_ipv4_add_remove
Framework: spytest
Device: SONiC (OC-Build)
"""

from __future__ import annotations
import re
import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
CONFIG = SpyTestDict({
    "tacacs_server_ipv4": "192.168.100.87",
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
    - Unconfigure any existing TACACS+ IPv4 server

    Teardown Phase:
    - Cleanup TACACS+ IPv4 server configuration
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TACACS-IPv4: MODULE PROLOGUE - IPv4 Server Add/Remove Test")
    st.banner("=" * 80)

    # Ensure minimum topology (single DUT)
    vars = st.ensure_min_topology("D1")
    data.cli_type = CONFIG.cli_type

    st.log(f"Module Setup: Using CLI type '{data.cli_type}'")
    st.log(f"TACACS+ IPv4 Server: {CONFIG.tacacs_server_ipv4}")

    # Unconfigure TACACS+ IPv4 server before starting tests
    st.log("Performing unconfiguration of TACACS+ IPv4 server...")
    unconfigure_tacacs_server_ipv4(vars.D1)
    st.wait(2, "Waiting for unconfiguration to complete")

    yield  # Tests run here

    st.banner("=" * 80)
    st.banner("TACACS-IPv4: MODULE EPILOGUE - Cleanup")
    st.banner("=" * 80)

    st.log("Cleaning up TACACS+ IPv4 server configuration...")
    cleanup_tacacs_ipv4(vars.D1)
    st.wait(2, "Waiting for cleanup to complete")
    st.log("Cleanup completed successfully")


def unconfigure_tacacs_server_ipv4(dut: str) -> bool:
    """
    Unconfigure TACACS+ IPv4 server on the device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful (even if nothing to unconfigure)
    """
    try:
        st.log(f"Unconfiguring TACACS+ IPv4 server {CONFIG.tacacs_server_ipv4} on {dut}...")
        commands = [
            f"no tacacs-server host {CONFIG.tacacs_server_ipv4}",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"Unconfiguration completed on {dut}")
        return True
    except Exception as e:
        st.log(f"Unconfiguration skipped or completed (may not have been configured): {str(e)}")
        return True


def configure_tacacs_server_ipv4(dut: str, server_ip: str) -> bool:
    """
    Configure TACACS+ IPv4 server.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IPv4 address

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Configuring TACACS+ IPv4 server {server_ip} on {dut}...")
        commands = [
            f"tacacs-server host {server_ip}",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(2, "Waiting for IPv4 server configuration to apply")
        st.log(f"TACACS+ IPv4 server {server_ip} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure TACACS+ IPv4 server on {dut}: {str(e)}")
        return False


def verify_tacacs_server_ipv4(dut: str, server_ip: str) -> bool:
    """
    Verify TACACS+ IPv4 server configuration and default parameters.

    Klish show tacacs-server output format:
    -----------------------------------------------------------------------
    TACACS+ Global Configuration
    -----------------------------------------------------------------------
    ...
    -----------------------------------------------------------------------
    TACACS+ Servers
    -----------------------------------------------------------------------
    HOST                 AUTH-TYPE  KEY   PORT  PRIORITY  TIMEOUT  VRF
    -----------------------------------------------------------------------
    192.168.100.87       pap        No    49    1         5        DEFAULT

    Expected defaults:
    - AUTH-TYPE : pap
    - PORT      : 49
    - PRIORITY  : 1
    - TIMEOUT   : 5
    - VRF       : DEFAULT

    Args:
        dut: Device identifier
        server_ip: Expected TACACS+ server IPv4 address

    Returns:
        bool: True if server is configured with all correct default parameters
    """
    try:
        st.log(f"Verifying TACACS+ IPv4 server {server_ip} on {dut}...")
        # Use skip_tmpl=True to get raw string — templates may return [] for klish
        output = st.show(dut, "show tacacs-server", type=data.cli_type,
                         skip_tmpl=True, skip_error_check=True)

        output_str = output if isinstance(output, str) else str(output) if output else ""

        if not output_str.strip():
            st.error(f"✗ show tacacs-server returned empty output on {dut}")
            return False

        st.log(f"TACACS+ show output:\n{output_str}")

        # Check server IP is present
        if server_ip not in output_str:
            st.error(f"✗ TACACS+ IPv4 server {server_ip} not found in output")
            return False

        st.log(f"✓ TACACS+ IPv4 server {server_ip} found in configuration")

        # Parse the server row — find line containing the server IP
        server_line = ""
        for line in output_str.splitlines():
            if server_ip in line:
                server_line = line
                break

        if not server_line:
            st.error(f"✗ Could not locate server row for {server_ip} in output")
            return False

        st.log(f"Server row: {server_line}")

        # Tokenize the row — columns: HOST AUTH-TYPE KEY PORT PRIORITY TIMEOUT VRF
        tokens = server_line.split()
        # tokens[0]=HOST, [1]=AUTH-TYPE, [2]=KEY, [3]=PORT, [4]=PRIORITY, [5]=TIMEOUT, [6]=VRF
        checks_passed = True

        if len(tokens) >= 2:
            actual_auth = tokens[1].lower()
            if actual_auth == CONFIG.expected_auth_type.lower():
                st.log(f"✓ AUTH-TYPE: {actual_auth} (expected: {CONFIG.expected_auth_type})")
            else:
                st.error(f"✗ AUTH-TYPE mismatch: got '{actual_auth}', expected '{CONFIG.expected_auth_type}'")
                checks_passed = False
        else:
            st.error(f"✗ AUTH-TYPE column missing in server row: {server_line}")
            checks_passed = False

        if len(tokens) >= 4:
            actual_port = tokens[3]
            if actual_port == CONFIG.expected_port:
                st.log(f"✓ PORT: {actual_port} (expected: {CONFIG.expected_port})")
            else:
                st.error(f"✗ PORT mismatch: got '{actual_port}', expected '{CONFIG.expected_port}'")
                checks_passed = False
        else:
            st.error(f"✗ PORT column missing in server row: {server_line}")
            checks_passed = False

        if len(tokens) >= 5:
            actual_priority = tokens[4]
            if actual_priority == CONFIG.expected_priority:
                st.log(f"✓ PRIORITY: {actual_priority} (expected: {CONFIG.expected_priority})")
            else:
                st.error(f"✗ PRIORITY mismatch: got '{actual_priority}', expected '{CONFIG.expected_priority}'")
                checks_passed = False
        else:
            st.error(f"✗ PRIORITY column missing in server row: {server_line}")
            checks_passed = False

        if len(tokens) >= 6:
            actual_timeout = tokens[5]
            if actual_timeout == CONFIG.expected_timeout:
                st.log(f"✓ TIMEOUT: {actual_timeout} (expected: {CONFIG.expected_timeout})")
            else:
                st.error(f"✗ TIMEOUT mismatch: got '{actual_timeout}', expected '{CONFIG.expected_timeout}'")
                checks_passed = False
        else:
            st.error(f"✗ TIMEOUT column missing in server row: {server_line}")
            checks_passed = False

        if len(tokens) >= 7:
            actual_vrf = tokens[6].upper()
            if actual_vrf == CONFIG.expected_vrf.upper():
                st.log(f"✓ VRF: {actual_vrf} (expected: {CONFIG.expected_vrf})")
            else:
                st.error(f"✗ VRF mismatch: got '{actual_vrf}', expected '{CONFIG.expected_vrf}'")
                checks_passed = False
        else:
            st.error(f"✗ VRF column missing in server row: {server_line}")
            checks_passed = False

        if checks_passed:
            st.log(f"✓ TACACS+ IPv4 server {server_ip} — all default parameters verified")
        else:
            st.error(f"✗ TACACS+ IPv4 server {server_ip} — one or more default parameters mismatch")

        return checks_passed

    except Exception as e:
        st.error(f"Failed to verify TACACS+ IPv4 server on {dut}: {str(e)}")
        return False


def verify_tacacs_server_removed_ipv4(dut: str, server_ip: str) -> bool:
    """
    Verify TACACS+ IPv4 server has been removed from configuration.

    Args:
        dut: Device identifier
        server_ip: TACACS+ server IPv4 address that should NOT be present

    Returns:
        bool: True if server is NOT in configuration, False if still present
    """
    try:
        st.log(f"Verifying TACACS+ IPv4 server {server_ip} is removed from {dut}...")
        output = st.show(dut, "show tacacs-server", type=data.cli_type,
                         skip_tmpl=True, skip_error_check=True)

        output_str = output if isinstance(output, str) else str(output) if output else ""

        if server_ip not in output_str:
            st.log(f"✓ TACACS+ IPv4 server {server_ip} successfully removed")
            return True
        else:
            st.error(f"✗ TACACS+ IPv4 server {server_ip} still present in configuration")
            st.log(f"Output:\n{output_str}")
            return False

    except Exception as e:
        st.error(f"Failed to verify TACACS+ IPv4 server removal on {dut}: {str(e)}")
        return False


def cleanup_tacacs_ipv4(dut: str) -> bool:
    """
    Cleanup and remove TACACS+ IPv4 server configuration from device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful
    """
    try:
        st.log(f"Cleaning up TACACS+ IPv4 server configuration on {dut}...")
        commands = [
            f"no tacacs-server host {CONFIG.tacacs_server_ipv4}",
        ]
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2, "Waiting for cleanup to complete")
        st.log(f"TACACS+ IPv4 cleanup completed on {dut}")
        return True
    except Exception as e:
        st.log(f"Cleanup completed (may have already been removed): {str(e)}")
        return True


@pytest.mark.tacacs
@pytest.mark.tacacs_ipv4
def test_tacacs_ipv4_01_add_server():
    """
    Test: Add TACACS+ IPv4 Server

    Based on manual testing:
    sonic(config)# tacacs-server host 192.168.100.87

    Test Steps:
    1. Configure TACACS+ IPv4 server (192.168.100.87)
    2. Verify server is added with correct default parameters:
       - AUTH-TYPE: pap
       - KEY: No
       - PORT: 49
       - PRIORITY: 1
       - TIMEOUT: 5
       - VRF: DEFAULT
    3. Display complete TACACS+ configuration

    Expected Outcome:
    - IPv4 server is successfully configured
    - All default parameters match expected values (FAIL on mismatch)
    """
    st.banner("-" * 80)
    st.banner("TEST-01: Add TACACS+ IPv4 Server")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Step 1: Configure TACACS+ IPv4 server
        st.log(f"STEP 1: Configure TACACS+ IPv4 server {CONFIG.tacacs_server_ipv4}")
        if not configure_tacacs_server_ipv4(dut, CONFIG.tacacs_server_ipv4):
            st.error("Failed to configure TACACS+ IPv4 server")
            result = False
        else:
            st.log("✓ STEP 1 PASSED: TACACS+ IPv4 server configured")

        # Step 2: Verify TACACS+ IPv4 server and default parameters
        st.log(f"STEP 2: Verify TACACS+ IPv4 server {CONFIG.tacacs_server_ipv4} defaults")
        if not verify_tacacs_server_ipv4(dut, CONFIG.tacacs_server_ipv4):
            st.error("Failed to verify TACACS+ IPv4 server — one or more defaults mismatch")
            result = False
        else:
            st.log("✓ STEP 2 PASSED: TACACS+ IPv4 server verified with all default parameters")

        # Step 3: Display complete TACACS+ configuration
        st.log("STEP 3: Display complete TACACS+ configuration")
        output = st.show(dut, "show tacacs-server", type=data.cli_type,
                         skip_tmpl=True, skip_error_check=True)
        st.log(f"Complete TACACS+ Configuration:\n{output}")
        st.log("✓ STEP 3 PASSED: Configuration displayed")

    except Exception as e:
        st.error(f"Exception in test_tacacs_ipv4_01_add_server: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-01 PASSED: Add TACACS+ IPv4 Server test completed successfully")
    else:
        st.error("❌ TEST-01 FAILED: Add TACACS+ IPv4 Server test failed")

    assert result, "Test failed: Add TACACS+ IPv4 Server"


@pytest.mark.tacacs
@pytest.mark.tacacs_ipv4
def test_tacacs_ipv4_02_remove_server():
    """
    Test: Remove TACACS+ IPv4 Server

    Based on manual testing:
    sonic(config)# no tacacs-server host 192.168.100.87

    Test Steps:
    1. Ensure TACACS+ IPv4 server is configured
    2. Verify server exists in configuration
    3. Remove TACACS+ IPv4 server
    4. Verify server is removed from configuration

    Expected Outcome:
    - IPv4 server is successfully removed
    - Server does not appear in show output
    """
    st.banner("-" * 80)
    st.banner("TEST-02: Remove TACACS+ IPv4 Server")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Step 1: Ensure TACACS+ IPv4 server is configured
        st.log(f"STEP 1: Ensure TACACS+ IPv4 server {CONFIG.tacacs_server_ipv4} is configured")
        configure_tacacs_server_ipv4(dut, CONFIG.tacacs_server_ipv4)
        st.wait(2)

        # Step 2: Verify server exists before removal
        st.log(f"STEP 2: Verify TACACS+ IPv4 server {CONFIG.tacacs_server_ipv4} exists")
        output = st.show(dut, "show tacacs-server", type=data.cli_type,
                         skip_tmpl=True, skip_error_check=True)
        output_str = output if isinstance(output, str) else str(output)
        if CONFIG.tacacs_server_ipv4 in output_str:
            st.log("✓ STEP 2 PASSED: TACACS+ IPv4 server exists before removal")
        else:
            st.error("✗ STEP 2: TACACS+ IPv4 server not found before removal — precondition failed")
            result = False

        # Step 3: Remove TACACS+ IPv4 server
        st.log(f"STEP 3: Remove TACACS+ IPv4 server {CONFIG.tacacs_server_ipv4}")
        if not unconfigure_tacacs_server_ipv4(dut):
            st.error("Failed to remove TACACS+ IPv4 server")
            result = False
        else:
            st.log("✓ STEP 3 PASSED: TACACS+ IPv4 server removal command executed")

        # Step 4: Verify server is removed
        st.log(f"STEP 4: Verify TACACS+ IPv4 server {CONFIG.tacacs_server_ipv4} is removed")
        st.wait(2, "Waiting for removal to complete")
        if not verify_tacacs_server_removed_ipv4(dut, CONFIG.tacacs_server_ipv4):
            st.error("Failed to verify TACACS+ IPv4 server removal")
            result = False
        else:
            st.log("✓ STEP 4 PASSED: TACACS+ IPv4 server successfully removed")

        # Display final configuration
        st.log("Final TACACS+ configuration after removal:")
        output = st.show(dut, "show tacacs-server", type=data.cli_type,
                         skip_tmpl=True, skip_error_check=True)
        st.log(f"Configuration:\n{output}")

    except Exception as e:
        st.error(f"Exception in test_tacacs_ipv4_02_remove_server: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-02 PASSED: Remove TACACS+ IPv4 Server test completed successfully")
    else:
        st.error("❌ TEST-02 FAILED: Remove TACACS+ IPv4 Server test failed")

    assert result, "Test failed: Remove TACACS+ IPv4 Server"


@pytest.mark.tacacs
@pytest.mark.tacacs_ipv4
def test_tacacs_ipv4_03_add_remove_cycle():
    """
    Test: Complete Add/Remove Cycle for TACACS+ IPv4 Server

    Test Steps:
    1. Add TACACS+ IPv4 server
    2. Verify server is configured with correct defaults
    3. Remove TACACS+ IPv4 server
    4. Verify server is removed
    5. Add server again
    6. Verify server is configured again with correct defaults

    Expected Outcome:
    - Server can be added, removed, and added again successfully
    - Default parameters are correct on each add (FAIL on mismatch)
    """
    st.banner("-" * 80)
    st.banner("TEST-03: Complete Add/Remove Cycle for TACACS+ IPv4 Server")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Cycle 1: Add
        st.log(f"CYCLE 1 - ADD: Configure TACACS+ IPv4 server {CONFIG.tacacs_server_ipv4}")
        if not configure_tacacs_server_ipv4(dut, CONFIG.tacacs_server_ipv4):
            st.error("Cycle 1: Failed to add TACACS+ IPv4 server")
            result = False
        else:
            st.log("✓ Cycle 1 ADD: Server configured")

        if not verify_tacacs_server_ipv4(dut, CONFIG.tacacs_server_ipv4):
            st.error("Cycle 1: Default parameter verification failed")
            result = False
        else:
            st.log("✓ Cycle 1 VERIFY: Server defaults verified")

        # Cycle 1: Remove
        st.log(f"CYCLE 1 - REMOVE: Remove TACACS+ IPv4 server {CONFIG.tacacs_server_ipv4}")
        if not unconfigure_tacacs_server_ipv4(dut):
            st.error("Cycle 1: Failed to remove TACACS+ IPv4 server")
            result = False
        else:
            st.log("✓ Cycle 1 REMOVE: Server removed")

        st.wait(2)
        if not verify_tacacs_server_removed_ipv4(dut, CONFIG.tacacs_server_ipv4):
            st.error("Cycle 1: Failed to verify removal")
            result = False
        else:
            st.log("✓ Cycle 1 VERIFY REMOVAL: Server removal verified")

        # Cycle 2: Add again
        st.log(f"CYCLE 2 - ADD AGAIN: Configure TACACS+ IPv4 server {CONFIG.tacacs_server_ipv4}")
        if not configure_tacacs_server_ipv4(dut, CONFIG.tacacs_server_ipv4):
            st.error("Cycle 2: Failed to add TACACS+ IPv4 server again")
            result = False
        else:
            st.log("✓ Cycle 2 ADD: Server configured again")

        if not verify_tacacs_server_ipv4(dut, CONFIG.tacacs_server_ipv4):
            st.error("Cycle 2: Default parameter verification failed on re-add")
            result = False
        else:
            st.log("✓ Cycle 2 VERIFY: Server defaults verified again")

        st.log("Complete add/remove cycle test completed")

    except Exception as e:
        st.error(f"Exception in test_tacacs_ipv4_03_add_remove_cycle: {str(e)}")
        result = False

    if result:
        st.log("✅ TEST-03 PASSED: Complete Add/Remove Cycle test completed successfully")
    else:
        st.error("❌ TEST-03 FAILED: Complete Add/Remove Cycle test failed")

    assert result, "Test failed: Complete Add/Remove Cycle"


if __name__ == "__main__":
    st.log("Running TACACS+ IPv4 tests directly")
    pytest.main([__file__, "-v"])
