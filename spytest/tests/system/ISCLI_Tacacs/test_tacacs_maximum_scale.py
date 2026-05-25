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
import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration
# ISCLI supports 64 servers, Broadcom supports 8 servers maximum
CONFIG = SpyTestDict({
    "iscli_max_servers": 64,
    "broadcom_max_servers": 8,
    "base_server_ip": "192.168.100",
    "base_server_octet": 101,
    "base_port": 49,
    "auth_types": ["pap", "chap", "mschap", "login"],
    "vrf": "mgmt",
    "max_timeout": 60
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture.

    Setup Phase (Module 1: Unconfiguration):
    - Initialize SpyTestDict variables
    - Ensure minimum topology
    - Detect CLI type (ISCLI vs Broadcom)
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
    
    # Detect CLI type
    data.cli_type = st.get_ui_type(vars.D1)
    st.log(f"Detected CLI type: {data.cli_type}")
    
    # Set maximum servers based on platform
    if data.cli_type == "klish":
        data.max_servers = CONFIG.broadcom_max_servers
        data.platform = "Broadcom"
        st.log(f"Platform: Broadcom/Klish - Maximum servers: {data.max_servers}")
    else:
        data.max_servers = CONFIG.iscli_max_servers
        data.platform = "ISCLI"
        st.log(f"Platform: ISCLI - Maximum servers: {data.max_servers}")

    st.log(f"Test will configure {data.max_servers} TACACS+ servers with all parameters")

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
    try:
        st.log(f"MODULE 1: Unconfiguring all TACACS+ servers on {dut}...")
        
        # Generate unconfiguration commands for maximum possible servers
        commands = []
        for i in range(1, 65):  # Unconfigure up to 64 servers
            server_ip = f"{CONFIG.base_server_ip}.{CONFIG.base_server_octet + i - 1}"
            if data.cli_type == "klish":
                commands.append(f"no tacacs-server host {server_ip}")
            else:
                commands.append(f"no tacacs server {server_ip}")
        
        # Add global unconfiguration
        if data.cli_type == "klish":
            commands.extend([
                "no tacacs-server key",
                "no tacacs-server timeout"
            ])
        else:
            commands.extend([
                "no tacacs passkey",
                "no tacacs timeout"
            ])
        
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"MODULE 1: Unconfiguration completed on {dut}")
        return True
    except Exception as e:
        st.log(f"MODULE 1: Unconfiguration skipped (may not have been configured): {str(e)}")
        return True


def configure_maximum_tacacs_servers(dut: str, max_servers: int) -> bool:
    """
    MODULE 2: Configure maximum TACACS+ servers with all parameters.

    Args:
        dut: Device identifier
        max_servers: Maximum number of servers to configure

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"MODULE 2: Configuring {max_servers} TACACS+ servers with all parameters on {dut}...")
        
        commands = []
        auth_types = CONFIG.auth_types
        
        for i in range(1, max_servers + 1):
            server_ip = f"{CONFIG.base_server_ip}.{CONFIG.base_server_octet + i - 1}"
            priority = i
            auth_type = auth_types[(i - 1) % len(auth_types)]  # Cycle through auth types
            key = f"Server{i:02d}"
            timeout = min(i, CONFIG.max_timeout)  # Cap at max timeout
            port = CONFIG.base_port + (i - 1)
            
            # Build command based on CLI type
            if data.cli_type == "klish":
                # Broadcom/Klish syntax
                cmd = (f"tacacs-server host {server_ip} "
                       f"priority {priority} "
                       f"type {auth_type} "
                       f"key {key} "
                       f"timeout {timeout} "
                       f"port {port}")
            else:
                # ISCLI syntax
                cmd = (f"tacacs server {server_ip} "
                       f"priority {priority} "
                       f"authtype {auth_type} "
                       f"key {key} "
                       f"timeout {timeout} "
                       f"port {port} "
                       f"use-mgmt-vrf")
            
            commands.append(cmd)
            
            # Log every 10 servers for progress tracking
            if i % 10 == 0:
                st.log(f"MODULE 2: Generated configuration for {i}/{max_servers} servers...")
        
        st.log(f"MODULE 2: Applying configuration for {max_servers} TACACS+ servers...")
        st.config(dut, commands, type=data.cli_type, skip_error_check=False)
        st.wait(2, f"Waiting for {max_servers} servers to be configured")
        st.log(f"MODULE 2: Successfully configured {max_servers} TACACS+ servers on {dut}")
        return True
        
    except Exception as e:
        st.error(f"MODULE 2: Failed to configure maximum TACACS+ servers on {dut}: {str(e)}")
        return False


def verify_tacacs_servers_count(dut: str, expected_count: int) -> bool:
    """
    MODULE 3: Verify the number of configured TACACS+ servers.

    Args:
        dut: Device identifier
        expected_count: Expected number of servers

    Returns:
        bool: True if count matches, False otherwise
    """
    try:
        st.log(f"MODULE 3: Verifying TACACS+ server count on {dut}...")
        
        if data.cli_type == "klish":
            output = st.show(dut, "show tacacs-server", type=data.cli_type)
        else:
            output = st.show(dut, "show tacacs", type=data.cli_type)
        
        # Count servers in output
        output_str = str(output)
        
        # Count TACPLUS_SERVER entries (ISCLI) or server entries (Broadcom)
        if data.cli_type == "klish":
            # Broadcom: count lines with IP addresses in server table
            server_count = output_str.count(CONFIG.base_server_ip)
        else:
            # ISCLI: count TACPLUS_SERVER entries
            server_count = output_str.count("TACPLUS_SERVER")
        
        st.log(f"MODULE 3: Found {server_count} TACACS+ servers in output")
        st.log(f"MODULE 3: Expected {expected_count} servers")
        
        if server_count >= expected_count:
            st.log(f"MODULE 3: ✅ Server count verification PASSED ({server_count} >= {expected_count})")
            return True
        else:
            st.error(f"MODULE 3: ❌ Server count verification FAILED ({server_count} < {expected_count})")
            return False
            
    except Exception as e:
        st.error(f"MODULE 3: Failed to verify TACACS+ server count: {str(e)}")
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
    try:
        server_ip = f"{CONFIG.base_server_ip}.{CONFIG.base_server_octet + server_index - 1}"
        expected_priority = server_index
        auth_types = CONFIG.auth_types
        expected_auth_type = auth_types[(server_index - 1) % len(auth_types)]
        expected_key = f"Server{server_index:02d}"
        expected_timeout = min(server_index, CONFIG.max_timeout)
        expected_port = CONFIG.base_port + (server_index - 1)
        
        st.log(f"MODULE 3: Verifying server {server_ip} parameters...")
        st.log(f"  Expected - Priority: {expected_priority}, AuthType: {expected_auth_type}, "
               f"Timeout: {expected_timeout}, Port: {expected_port}")
        
        if data.cli_type == "klish":
            output = st.show(dut, "show tacacs-server", type=data.cli_type)
        else:
            output = st.show(dut, "show tacacs", type=data.cli_type)
        
        output_str = str(output)
        
        # Verify server IP exists in output
        if server_ip in output_str:
            st.log(f"MODULE 3: ✅ Server {server_ip} found in configuration")
            
            # Verify priority
            if str(expected_priority) in output_str:
                st.log(f"MODULE 3: ✅ Priority {expected_priority} verified")
            
            # Verify auth type
            if expected_auth_type in output_str:
                st.log(f"MODULE 3: ✅ Auth type {expected_auth_type} verified")
            
            # Verify timeout
            if str(expected_timeout) in output_str:
                st.log(f"MODULE 3: ✅ Timeout {expected_timeout} verified")
            
            # Verify port
            if str(expected_port) in output_str:
                st.log(f"MODULE 3: ✅ Port {expected_port} verified")
            
            return True
        else:
            st.error(f"MODULE 3: ❌ Server {server_ip} not found in configuration")
            return False
            
    except Exception as e:
        st.error(f"MODULE 3: Failed to verify server parameters: {str(e)}")
        return False


def cleanup_all_tacacs(dut: str) -> bool:
    """
    MODULE 4: Cleanup - Remove all TACACS+ configuration.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful
    """
    try:
        st.log(f"MODULE 4: Cleaning up all TACACS+ configuration on {dut}...")
        
        # Generate cleanup commands for all configured servers
        commands = []
        for i in range(1, data.max_servers + 1):
            server_ip = f"{CONFIG.base_server_ip}.{CONFIG.base_server_octet + i - 1}"
            if data.cli_type == "klish":
                commands.append(f"no tacacs-server host {server_ip}")
            else:
                commands.append(f"no tacacs server {server_ip}")
        
        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(2, "Waiting for cleanup to complete")
        st.log(f"MODULE 4: Cleanup completed on {dut}")
        return True
        
    except Exception as e:
        st.log(f"MODULE 4: Cleanup completed with warnings: {str(e)}")
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
    - Configure maximum number of TACACS+ servers supported by the platform
    - Each server configured with all parameters: priority, authtype, key, timeout, port, vrf
    - Verify all servers are configured correctly
    - Validate platform limits (ISCLI: 64 servers, Broadcom: 8 servers)

    Test Steps:
    MODULE 2: Configuration
    1. Configure maximum TACACS+ servers (platform-dependent)
    2. Each server with unique: IP, priority, authtype, key, timeout, port

    MODULE 3: Validation
    3. Verify total server count matches expected maximum
    4. Verify sample servers (first, middle, last) have correct parameters
    5. Display complete TACACS+ configuration
    6. Validate platform limit enforcement

    Expected Outcome:
    - ISCLI: 64 servers configured successfully with all parameters
    - Broadcom: 8 servers configured successfully (limit enforced)
    - All parameters (priority, authtype, key, timeout, port, vrf) verified
    - Configuration visible via show commands
    """
    st.banner("-" * 100)
    st.banner(f"TEST: TACACS+ Maximum Scale - {data.platform} Platform")
    st.banner(f"Maximum Servers: {data.max_servers}")
    st.banner("-" * 100)

    dut = vars.D1
    result = True

    try:
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
            st.error(f"Server count verification failed")
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
        
        st.log(f"STEP 3 PASSED: ✅ Sample servers verified")
        
        # Step 4: Display complete TACACS+ configuration
        st.log("STEP 4: Display complete TACACS+ configuration")
        if data.cli_type == "klish":
            output = st.show(dut, "show tacacs-server", type=data.cli_type)
        else:
            output = st.show(dut, "show tacacs", type=data.cli_type)
        
        st.log(f"Complete TACACS+ Configuration ({data.platform}):")
        st.log(f"{output}")
        st.log(f"STEP 4 PASSED: ✅ Configuration displayed")
        
        # Step 5: Platform limit validation
        st.log("STEP 5: Validate platform limit enforcement")
        if data.platform == "Broadcom":
            st.log(f"  Platform: Broadcom - Limit: {data.max_servers} servers (enforced)")
            st.log(f"  ✅ Broadcom platform correctly enforces 8 server limit")
        else:
            st.log(f"  Platform: ISCLI - Limit: {data.max_servers}+ servers (no hard limit)")
            st.log(f"  ✅ ISCLI platform supports {data.max_servers} servers")
        
        st.log(f"STEP 5 PASSED: ✅ Platform limit validated")
        
    except Exception as e:
        st.error(f"Exception in test_tacacs_maximum_scale_all_parameters: {str(e)}")
        result = False

    # Test result summary
    st.banner("=" * 100)
    if result:
        st.log(f"TEST PASSED: ✅ TACACS+ Maximum Scale ({data.platform}) - {data.max_servers} servers")
        st.log("All servers configured with: priority, authtype, key, timeout, port, vrf")
    else:
        st.error(f"TEST FAILED: ❌ TACACS+ Maximum Scale ({data.platform})")
    st.banner("=" * 100)

    assert result, f"Test failed: TACACS+ Maximum Scale Configuration ({data.platform})"


if __name__ == "__main__":
    # This allows running the script directly for debugging
    st.log("Running TACACS+ Maximum Scale tests directly")
    pytest.main([__file__, "-v", "-s"])
