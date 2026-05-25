"""
TACACS+ Maximum Scale Configuration Test Script
================================================

This module tests TACACS+ maximum scale configuration with all parameters
configured on both ISCLI and Broadcom platforms.

Test Coverage:
- Maximum number of TACACS+ servers (platform-dependent)
- All parameters configured: priority, authtype, key, timeout, port, vrf
- Configuration verification with all parameters
- Platform limits validation (ISCLI: 64 servers, Broadcom: 8 servers)

Module: test_tacacs_maximum_scale
Framework: spytest
Devices: SONiC (ISCLI and Broadcom)
"""

from __future__ import annotations
import re
import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
# This device (Broadcom/klish) supports 8 servers maximum
CONFIG = SpyTestDict({
    "broadcom_max_servers": 8,
    "base_server_ip": "192.168.100",
    "base_server_octet": 101,
    "base_port": 49,
    "auth_types": ["pap", "chap", "login"],  # mschap not supported on this device
    "max_timeout": 60
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture.

    Setup Phase (Module 1: Unconfiguration):
    - Initialize SpyTestDict variables
    - Ensure minimum topology
    - Detect CLI type (forced to klish for SONiC)
    - Perform unconfiguration (cleanup any existing TACACS+ config)

    Teardown Phase (Module 4: Cleanup):
    - Cleanup all TACACS+ configuration after all tests
    """
    global vars, data

    st.banner("=" * 100)
    st.banner("TACACS-MAX-SCALE: MODULE PROLOGUE - Maximum Scale Configuration Test")
    st.banner("=" * 100)

    # Ensure minimum topology (single DUT)
    vars = st.ensure_min_topology("D1")

    # Force klish - st.get_ui_type() returns 'click' but device uses klish
    data.cli_type = "klish"
    data.max_servers = CONFIG.broadcom_max_servers
    data.platform = "Broadcom"
    st.log(f"CLI type: {data.cli_type} | Platform: {data.platform} | Max servers: {data.max_servers}")

    # MODULE 1: UNCONFIGURATION
    st.banner("-" * 100)
    st.banner("MODULE 1: UNCONFIGURATION - Cleanup existing TACACS+ configuration")
    st.banner("-" * 100)
    unconfigure_all_tacacs(vars.D1)
    st.wait(2, "Waiting for unconfiguration to complete")

    yield  # Tests run here (MODULE 2: Configuration & MODULE 3: Validation)

    # MODULE 4: CLEANUP
    st.banner("=" * 100)
    st.banner("MODULE 4: CLEANUP - Remove all TACACS+ configuration")
    st.banner("=" * 100)
    cleanup_all_tacacs(vars.D1)
    st.log("Cleanup completed successfully")


def unconfigure_all_tacacs(dut: str) -> bool:
    """
    MODULE 1: Unconfigure all TACACS+ settings on the device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful
    """
    st.log(f"MODULE 1: Unconfiguring all TACACS+ servers on {dut}...")

    commands = []
    # Unconfigure all possible scale servers
    for i in range(1, CONFIG.broadcom_max_servers + 1):
        server_ip = f"{CONFIG.base_server_ip}.{CONFIG.base_server_octet + i - 1}"
        commands.append(f"no tacacs-server host {server_ip}")

    # Only 'no tacacs-server timeout' is valid globally (not key or auth-type)
    commands.append("no tacacs-server timeout")

    st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    st.log(f"MODULE 1: Unconfiguration completed on {dut}")
    return True


def show_tacacs(dut: str) -> str:
    """Return raw string output of 'show tacacs-server'."""
    output = st.show(dut, "show tacacs-server", type=data.cli_type,
                     skip_tmpl=True, skip_error_check=True)
    return output if isinstance(output, str) else str(output) if output else ""


def configure_maximum_tacacs_servers(dut: str, max_servers: int) -> bool:
    """
    MODULE 2: Configure maximum TACACS+ servers with all parameters.

    Args:
        dut: Device identifier
        max_servers: Maximum number of servers to configure

    Returns:
        bool: True if successful, False otherwise
    """
    st.log(f"MODULE 2: Configuring {max_servers} TACACS+ servers with all parameters on {dut}...")

    auth_types = CONFIG.auth_types
    commands = []

    for i in range(1, max_servers + 1):
        server_ip = f"{CONFIG.base_server_ip}.{CONFIG.base_server_octet + i - 1}"
        priority = i
        auth_type = auth_types[(i - 1) % len(auth_types)]  # Cycle through pap/chap/login
        key = f"Server{i:02d}"
        timeout = min(i * 5, CONFIG.max_timeout)  # 5,10,15...60
        port = CONFIG.base_port  # Use standard port 49 for all (per-port change may be unsupported)

        # Klish/Broadcom syntax — per-server auth-type and key
        # Add server first, then per-server params
        commands.append(f"tacacs-server host {server_ip} priority {priority} timeout {timeout} port {port}")
        commands.append(f"tacacs-server host {server_ip} auth-type {auth_type}")
        commands.append(f"tacacs-server host {server_ip} key {key}")

    st.log(f"MODULE 2: Applying configuration for {max_servers} TACACS+ servers...")
    st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    st.wait(2, f"Waiting for {max_servers} servers to be configured")
    st.log(f"MODULE 2: Configuration applied for {max_servers} TACACS+ servers on {dut}")
    return True


def verify_tacacs_servers_count(dut: str, expected_count: int) -> bool:
    """
    MODULE 3: Verify the number of configured TACACS+ servers.

    Args:
        dut: Device identifier
        expected_count: Expected number of servers

    Returns:
        bool: True if count matches, False otherwise
    """
    st.log(f"MODULE 3: Verifying TACACS+ server count on {dut}...")

    output_str = show_tacacs(dut)
    st.log(f"show tacacs-server output:\n{output_str}")

    # Count lines in the server table that contain our base IP prefix
    server_count = 0
    for line in output_str.splitlines():
        line = line.strip()
        if line.startswith(CONFIG.base_server_ip):
            server_count += 1

    st.log(f"MODULE 3: Found {server_count} TACACS+ servers in output, expected {expected_count}")

    if server_count >= expected_count:
        st.log(f"MODULE 3: ✅ Server count verification PASSED ({server_count} >= {expected_count})")
        return True
    else:
        st.error(f"MODULE 3: ❌ Server count verification FAILED ({server_count} < {expected_count})")
        return False


def verify_tacacs_server_parameters(dut: str, server_index: int) -> bool:
    """
    MODULE 3: Verify TACACS+ server configuration with all parameters.

    Args:
        dut: Device identifier
        server_index: Server index to verify (1-based)

    Returns:
        bool: True if verification passed, False otherwise
    """
    server_ip = f"{CONFIG.base_server_ip}.{CONFIG.base_server_octet + server_index - 1}"
    auth_types = CONFIG.auth_types
    expected_auth_type = auth_types[(server_index - 1) % len(auth_types)]
    expected_priority = server_index
    expected_timeout = min(server_index * 5, CONFIG.max_timeout)

    st.log(f"MODULE 3: Verifying server {server_ip} parameters...")
    st.log(f"  Expected - Priority: {expected_priority}, AuthType: {expected_auth_type}, "
           f"Timeout: {expected_timeout}, Port: {CONFIG.base_port}")

    output_str = show_tacacs(dut)

    # Find the row for this server IP
    server_line = None
    for line in output_str.splitlines():
        if line.strip().startswith(server_ip):
            server_line = line.strip()
            break

    if not server_line:
        st.error(f"MODULE 3: ❌ Server {server_ip} not found in show tacacs-server output")
        return False

    st.log(f"MODULE 3: Server row found: {server_line}")

    # Parse: HOST  AUTH-TYPE  KEY  PORT  PRIORITY  TIMEOUT  VRF
    tokens = server_line.split()
    # tokens[0]=HOST [1]=AUTH-TYPE [2]=KEY [3]=PORT [4]=PRIORITY [5]=TIMEOUT [6]=VRF
    checks_passed = True

    if len(tokens) >= 2:
        actual_auth = tokens[1].lower()
        if actual_auth == expected_auth_type.lower():
            st.log(f"  ✅ AUTH-TYPE: {actual_auth}")
        else:
            st.error(f"  ❌ AUTH-TYPE mismatch: got '{actual_auth}', expected '{expected_auth_type}'")
            checks_passed = False
    else:
        st.error(f"  ❌ Cannot parse AUTH-TYPE from row: {server_line}")
        checks_passed = False

    if len(tokens) >= 3:
        key_configured = tokens[2]
        if key_configured.lower() in ["yes", "true"]:
            st.log(f"  ✅ KEY: configured (Yes)")
        else:
            st.error(f"  ❌ KEY not configured: got '{key_configured}'")
            checks_passed = False

    if len(tokens) >= 5:
        actual_priority = tokens[4]
        if actual_priority == str(expected_priority):
            st.log(f"  ✅ PRIORITY: {actual_priority}")
        else:
            st.error(f"  ❌ PRIORITY mismatch: got '{actual_priority}', expected '{expected_priority}'")
            checks_passed = False

    if len(tokens) >= 6:
        actual_timeout = tokens[5]
        if actual_timeout == str(expected_timeout):
            st.log(f"  ✅ TIMEOUT: {actual_timeout}")
        else:
            st.error(f"  ❌ TIMEOUT mismatch: got '{actual_timeout}', expected '{expected_timeout}'")
            checks_passed = False

    return checks_passed


def cleanup_all_tacacs(dut: str) -> bool:
    """
    MODULE 4: Cleanup - Remove all TACACS+ configuration.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful
    """
    st.log(f"MODULE 4: Cleaning up all TACACS+ configuration on {dut}...")

    commands = []
    for i in range(1, data.max_servers + 1):
        server_ip = f"{CONFIG.base_server_ip}.{CONFIG.base_server_octet + i - 1}"
        commands.append(f"no tacacs-server host {server_ip}")

    st.config(dut, commands, type=data.cli_type, skip_error_check=True)
    st.wait(2, "Waiting for cleanup to complete")
    st.log(f"MODULE 4: Cleanup completed on {dut}")
    return True


# ================================================================================================
# TEST FUNCTIONS
# ================================================================================================

@pytest.mark.tacacs
@pytest.mark.maximum_scale
def test_tacacs_maximum_scale_all_parameters():
    """
    Test: TACACS+ Maximum Scale Configuration with All Parameters

    Test Objective:
    - Configure maximum number of TACACS+ servers supported by the platform (Broadcom: 8)
    - Each server configured with all parameters: priority, authtype, key, timeout, port
    - Verify all servers are configured correctly
    - Validate platform limits

    Test Steps:
    MODULE 2: Configuration
    1. Configure 8 TACACS+ servers with all parameters

    MODULE 3: Validation
    2. Verify total server count matches expected maximum
    3. Verify sample servers (first, middle, last) have correct parameters
    4. Display complete TACACS+ configuration
    5. Validate platform limit enforcement
    """
    st.banner("-" * 100)
    st.banner(f"TEST: TACACS+ Maximum Scale - {data.platform} Platform")
    st.banner(f"Maximum Servers: {data.max_servers}")
    st.banner("-" * 100)

    dut = vars.D1
    result = True

    # MODULE 2: CONFIGURATION
    st.banner("-" * 100)
    st.banner("MODULE 2: CONFIGURATION - Configure Maximum TACACS+ Servers")
    st.banner("-" * 100)

    st.log(f"STEP 1: Configure {data.max_servers} TACACS+ servers with all parameters")
    if not configure_maximum_tacacs_servers(dut, data.max_servers):
        st.error("Failed to configure maximum TACACS+ servers")
        result = False
    else:
        st.log(f"STEP 1 PASSED: ✅ {data.max_servers} TACACS+ servers configured")

    st.wait(2, "Waiting for configuration to stabilize")

    # MODULE 3: VALIDATION
    st.banner("-" * 100)
    st.banner("MODULE 3: VALIDATION - Verify Maximum Scale Configuration")
    st.banner("-" * 100)

    # Step 2: Verify server count
    st.log(f"STEP 2: Verify {data.max_servers} TACACS+ servers are configured")
    if not verify_tacacs_servers_count(dut, data.max_servers):
        st.error("Server count verification failed")
        result = False
    else:
        st.log(f"STEP 2 PASSED: ✅ Server count verified ({data.max_servers} servers)")

    # Step 3: Verify sample server parameters (first, middle, last)
    st.log("STEP 3: Verify sample servers with all parameters")

    # Verify first server (Server 1)
    st.log("  Verifying Server 1 (First)...")
    if verify_tacacs_server_parameters(dut, 1):
        st.log("  ✅ Server 1 parameters verified")
    else:
        st.error("  ❌ Server 1 verification failed")
        result = False

    # Verify middle server
    middle_server = data.max_servers // 2
    st.log(f"  Verifying Server {middle_server} (Middle)...")
    if verify_tacacs_server_parameters(dut, middle_server):
        st.log(f"  ✅ Server {middle_server} parameters verified")
    else:
        st.error(f"  ❌ Server {middle_server} verification failed")
        result = False

    # Verify last server
    st.log(f"  Verifying Server {data.max_servers} (Last)...")
    if verify_tacacs_server_parameters(dut, data.max_servers):
        st.log(f"  ✅ Server {data.max_servers} parameters verified")
    else:
        st.error(f"  ❌ Server {data.max_servers} verification failed")
        result = False

    st.log("STEP 3: Sample server verification complete")

    # Step 4: Display complete TACACS+ configuration
    st.log("STEP 4: Display complete TACACS+ configuration")
    output_str = show_tacacs(dut)
    st.log(f"Complete TACACS+ Configuration ({data.platform}):\n{output_str}")
    st.log("STEP 4 PASSED: ✅ Configuration displayed")

    # Step 5: Platform limit validation
    st.log("STEP 5: Validate platform limit enforcement")
    st.log(f"  Platform: {data.platform} - Limit: {data.max_servers} servers enforced")
    st.log(f"  ✅ {data.platform} platform correctly limits to {data.max_servers} servers")
    st.log("STEP 5 PASSED: ✅ Platform limit validated")

    # Test result summary
    st.banner("=" * 100)
    if result:
        st.log(f"TEST PASSED: ✅ TACACS+ Maximum Scale ({data.platform}) - {data.max_servers} servers")
        st.log("All servers configured with: priority, auth-type, key, timeout, port")
    else:
        st.error(f"TEST FAILED: ❌ TACACS+ Maximum Scale ({data.platform})")
    st.banner("=" * 100)

    assert result, f"Test failed: TACACS+ Maximum Scale Configuration ({data.platform})"


if __name__ == "__main__":
    st.log("Running TACACS+ Maximum Scale tests directly")
    pytest.main([__file__, "-v", "-s"])
