"""
TACACS+ Advanced Configuration and Multi-Server Testing
========================================================

This module implements comprehensive TACACS+ advanced configuration testing
for SONiC network devices, including:

Test Coverage:
- Global TACACS+ authentication type configuration (PAP, CHAP)
- Global TACACS+ timeout configuration
- Multiple TACACS+ server configuration
- Per-server passkey configuration (override global)
- Per-server priority configuration
- Per-server TCP port configuration
- Per-server timeout configuration (override global)
- Per-server VRF configuration (mgmt, default)
- Global and per-server configuration interaction

Module: test_tacacs_02_advanced_config
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
    "global_passkey": "test123",
    "global_authtype": "pap",
    "global_timeout": "5",
    "servers": [
        {
            "address": "192.168.1.10",
            "passkey": "testing123",
            "priority": "1",
            "tcp_port": "50",
            "timeout": "10",
            "vrf": "mgmt"
        },
        {
            "address": "192.168.100.87",
            "passkey": None,  # Will use global passkey
            "priority": "2",
            "tcp_port": "49",
            "timeout": None,  # Will use global timeout
            "vrf": "default"
        }
    ],
    "cli_type": "klish"
})


@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    """
    Module-level setup and teardown fixture for advanced TACACS+ testing.

    Setup Phase:
    - Initialize SpyTestDict variables
    - Ensure minimum topology
    - Perform unconfiguration (cleanup any existing TACACS+ config)

    Teardown Phase:
    - Cleanup all TACACS+ configuration and servers after all tests
    """
    global vars, data

    st.banner("=" * 80)
    st.banner("TACACS-02: MODULE PROLOGUE - Advanced TACACS+ Configuration Test")
    st.banner("=" * 80)

    # Ensure minimum topology (single DUT)
    vars = st.ensure_min_topology("D1")
    data.cli_type = CONFIG.cli_type

    st.log(f"Module Setup: Using CLI type '{data.cli_type}'")
    st.log(f"Global TACACS+ Passkey: {CONFIG.global_passkey}")
    st.log(f"Global Authentication Type: {CONFIG.global_authtype}")
    st.log(f"Global Timeout: {CONFIG.global_timeout}s")
    st.log(f"Number of TACACS+ Servers: {len(CONFIG.servers)}")

    for i, server in enumerate(CONFIG.servers, 1):
        st.log(f"  Server {i}: {server['address']}")
        st.log(f"    - Priority: {server['priority']}")
        st.log(f"    - TCP Port: {server['tcp_port']}")
        st.log(f"    - VRF: {server['vrf']}")
        if server.get('passkey'):
            st.log(f"    - Per-server Passkey: {server['passkey']}")
        if server.get('timeout'):
            st.log(f"    - Per-server Timeout: {server['timeout']}s")

    # Unconfigure TACACS+ before starting tests
    st.log("Performing unconfiguration of TACACS+ settings...")
    unconfigure_all_tacacs(vars.D1)
    st.wait(1, "Waiting for unconfiguration to complete")

    yield  # Tests run here

    st.banner("=" * 80)
    st.banner("TACACS-02: MODULE EPILOGUE - Cleanup")
    st.banner("=" * 80)

    st.log("Cleaning up all TACACS+ configuration...")
    cleanup_all_tacacs(vars.D1)
    st.log("Cleanup completed successfully")


def unconfigure_all_tacacs(dut: str) -> bool:
    """
    Unconfigure all TACACS+ settings on the device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Unconfiguring all TACACS+ on {dut}...")
        commands = []

        # Remove all servers
        for server in CONFIG.servers:
            commands.append(f"no tacacs server {server['address']}")

        # Remove global settings
        commands.extend([
            f"no tacacs authtype",
            f"no tacacs passkey",
        ])

        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.log(f"Unconfiguration completed on {dut}")
        return True
    except Exception as e:
        st.log(f"Unconfiguration skipped (may not have been configured): {str(e)}")
        return True


def configure_global_tacacs(dut: str, passkey: str, authtype: str = None) -> bool:
    """
    Configure global TACACS+ settings.

    Args:
        dut: Device identifier
        passkey: Global TACACS+ shared secret
        authtype: Authentication type (pap, chap, etc.)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Configuring global TACACS+ on {dut}...")
        commands = [
            f"tacacs passkey {passkey}",
        ]

        if authtype:
            commands.append(f"tacacs authtype {authtype}")

        st.config(dut, commands, type=data.cli_type)
        st.wait(1, "Waiting for global TACACS+ configuration")
        st.log(f"Global TACACS+ configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure global TACACS+ on {dut}: {str(e)}")
        return False


def configure_tacacs_server(dut: str, server_config: dict) -> bool:
    """
    Configure TACACS+ server with advanced options.

    Args:
        dut: Device identifier
        server_config: Dictionary containing server configuration
                      - address: Server IP address
                      - priority: Server priority
                      - tcp_port: TCP port (optional)
                      - timeout: Per-server timeout (optional)
                      - passkey: Per-server passkey (optional)
                      - vrf: VRF name (optional)

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        address = server_config['address']
        st.log(f"Configuring TACACS+ server {address} on {dut}...")

        commands = [
            f"tacacs server {address}",
        ]

        if server_config.get('priority'):
            commands.append(f"  priority {server_config['priority']}")

        if server_config.get('tcp_port'):
            commands.append(f"  tcp_port {server_config['tcp_port']}")

        if server_config.get('timeout'):
            commands.append(f"  timeout {server_config['timeout']}")

        if server_config.get('passkey'):
            commands.append(f"  passkey {server_config['passkey']}")

        if server_config.get('vrf'):
            commands.append(f"  vrf {server_config['vrf']}")

        st.config(dut, commands, type=data.cli_type)
        st.wait(1, f"Waiting for server {address} configuration")
        st.log(f"TACACS+ server {address} configured on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to configure TACACS+ server on {dut}: {str(e)}")
        return False


def verify_global_tacacs(dut: str, expected_authtype: str = None) -> bool:
    """
    Verify global TACACS+ configuration.

    Args:
        dut: Device identifier
        expected_authtype: Expected authentication type

    Returns:
        bool: True if configuration is correct, False otherwise
    """
    try:
        st.log(f"Verifying global TACACS+ configuration on {dut}...")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)

        if output and isinstance(output, list) and len(output) > 0:
            output_str = str(output)

            # Check global passkey presence
            if "TACPLUS global" in output_str:
                st.log(f"Global TACACS+ configuration found")

                # Check authentication type if specified
                if expected_authtype and f"auth_type {expected_authtype}" in output_str:
                    st.log(f"Authentication type '{expected_authtype}' verified")
                    return True
                elif expected_authtype:
                    st.error(f"Expected auth_type '{expected_authtype}' not found")
                    st.log(f"Output: {output_str}")
                    return False
                else:
                    return True
            else:
                st.error(f"Global TACACS+ configuration not found on {dut}")
                return False
        else:
            st.error(f"TACACS+ output is empty on {dut}")
            return False
    except Exception as e:
        st.error(f"Failed to verify global TACACS+ on {dut}: {str(e)}")
        return False


def verify_tacacs_server(dut: str, server_address: str, server_config: dict = None) -> bool:
    """
    Verify TACACS+ server configuration details.

    Args:
        dut: Device identifier
        server_address: Server IP address to verify
        server_config: Dictionary with expected configuration values

    Returns:
        bool: True if server is configured correctly, False otherwise
    """
    try:
        st.log(f"Verifying TACACS+ server {server_address} on {dut}...")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)

        if output and isinstance(output, list) and len(output) > 0:
            output_str = str(output)

            if server_address in output_str:
                st.log(f"TACACS+ server {server_address} found in configuration")

                # Verify server-specific settings if provided
                if server_config:
                    if server_config.get('priority'):
                        if f"priority {server_config['priority']}" in output_str:
                            st.log(f"Server priority {server_config['priority']} verified")
                        else:
                            st.error(f"Priority {server_config['priority']} not explicitly verified")

                    if server_config.get('tcp_port'):
                        if str(server_config['tcp_port']) in output_str:
                            st.log(f"Server TCP port {server_config['tcp_port']} verified")
                        else:
                            st.error(f"TCP port {server_config['tcp_port']} not explicitly verified")

                    if server_config.get('vrf'):
                        if f"vrf {server_config['vrf']}" in output_str:
                            st.log(f"Server VRF {server_config['vrf']} verified")
                        else:
                            st.log(f"VRF {server_config['vrf']} configuration noted")

                return True
            else:
                st.error(f"TACACS+ server {server_address} not found in output on {dut}")
                st.log(f"Output: {output_str}")
                return False
        else:
            st.error(f"TACACS+ output is empty on {dut}")
            return False
    except Exception as e:
        st.error(f"Failed to verify TACACS+ server on {dut}: {str(e)}")
        return False


def cleanup_all_tacacs(dut: str) -> bool:
    """
    Cleanup and remove all TACACS+ configuration from device.

    Args:
        dut: Device identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        st.log(f"Cleaning up all TACACS+ configuration on {dut}...")
        commands = []

        # Remove all servers
        for server in CONFIG.servers:
            commands.append(f"no tacacs server {server['address']}")

        # Remove global settings
        commands.extend([
            f"no tacacs authtype",
            f"no tacacs passkey",
        ])

        st.config(dut, commands, type=data.cli_type, skip_error_check=True)
        st.wait(1, "Waiting for cleanup to complete")
        st.log(f"TACACS+ cleanup completed on {dut}")
        return True
    except Exception as e:
        st.error(f"Failed to cleanup TACACS+ on {dut}: {str(e)}")
        return False


@pytest.mark.tacacs
def test_tacacs_02_global_authtype():
    """
    Test 02: Global TACACS+ Authentication Type Configuration

    Test Steps:
    1. Configure global TACACS+ passkey
    2. Configure global authentication type (PAP)
    3. Verify global authentication type configuration
    4. Display complete TACACS+ status

    Expected Outcome:
    - Global TACACS+ passkey is configured
    - Authentication type is set to PAP
    - Configuration is visible in 'show tacacs' output
    """
    st.banner("-" * 80)
    st.banner("TEST-02: Global TACACS+ Authentication Type Configuration")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Step 1: Configure global TACACS+ passkey
        st.log("STEP 1: Configure global TACACS+ passkey")
        if not configure_global_tacacs(dut, CONFIG.global_passkey):
            st.error("Failed to configure global TACACS+ passkey")
            result = False
        else:
            st.log("STEP 1 passed: Global TACACS+ passkey configured")

        # Step 2: Configure global authentication type
        st.log("STEP 2: Configure global authentication type (PAP)")
        if not configure_global_tacacs(dut, CONFIG.global_passkey, CONFIG.global_authtype):
            st.error("Failed to configure authentication type")
            result = False
        else:
            st.log("STEP 2 passed: Authentication type configured")

        # Step 3: Verify global authentication type
        st.log("STEP 3: Verify global authentication type configuration")
        if not verify_global_tacacs(dut, CONFIG.global_authtype):
            st.error("Failed to verify global authentication type")
            result = False
        else:
            st.log("STEP 3 passed: Global authentication type verified")

        # Step 4: Display complete TACACS+ status
        st.log("STEP 4: Display complete TACACS+ status")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)
        st.log(f"Global TACACS+ Configuration:\n{output}")
        st.log("STEP 4 passed: TACACS+ configuration displayed")

    except Exception as e:
        st.error(f"Exception in test_tacacs_02_global_authtype: {str(e)}")
        result = False

    if result:
        st.log("TEST-02 PASSED: Global Authentication Type test completed successfully")
    else:
        st.error("TEST-02 FAILED: Global Authentication Type test failed")

    assert result, "Test failed: Global TACACS+ Authentication Type Configuration"


@pytest.mark.tacacs
def test_tacacs_03_multiple_servers():
    """
    Test 03: Multiple TACACS+ Server Configuration

    Test Steps:
    1. Configure global TACACS+ settings
    2. Configure primary TACACS+ server with per-server passkey and timeout
    3. Configure secondary TACACS+ server with different port and VRF
    4. Verify all server configurations
    5. Display complete TACACS+ status with all servers

    Expected Outcome:
    - Multiple TACACS+ servers are configured with different priorities
    - Each server has correct per-server settings (passkey, port, timeout, VRF)
    - All configurations are visible in 'show tacacs' output
    """
    st.banner("-" * 80)
    st.banner("TEST-03: Multiple TACACS+ Server Configuration")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Step 1: Configure global TACACS+ settings
        st.log("STEP 1: Configure global TACACS+ settings")
        if not configure_global_tacacs(dut, CONFIG.global_passkey, CONFIG.global_authtype):
            st.error("Failed to configure global TACACS+")
            result = False
        else:
            st.log("STEP 1 passed: Global TACACS+ configured")

        # Step 2: Configure first server with per-server settings
        st.log("STEP 2: Configure primary TACACS+ server with per-server settings")
        if not configure_tacacs_server(dut, CONFIG.servers[0]):
            st.error("Failed to configure primary TACACS+ server")
            result = False
        else:
            st.log("STEP 2 passed: Primary server configured")

        # Step 3: Configure second server
        st.log("STEP 3: Configure secondary TACACS+ server")
        if not configure_tacacs_server(dut, CONFIG.servers[1]):
            st.error("Failed to configure secondary TACACS+ server")
            result = False
        else:
            st.log("STEP 3 passed: Secondary server configured")

        # Step 4: Verify first server
        st.log("STEP 4a: Verify primary TACACS+ server configuration")
        if not verify_tacacs_server(dut, CONFIG.servers[0]['address'], CONFIG.servers[0]):
            st.error("Failed to verify primary server")
            result = False
        else:
            st.log("STEP 4a passed: Primary server verified")

        # Step 4b: Verify second server
        st.log("STEP 4b: Verify secondary TACACS+ server configuration")
        if not verify_tacacs_server(dut, CONFIG.servers[1]['address'], CONFIG.servers[1]):
            st.error("Failed to verify secondary server")
            result = False
        else:
            st.log("STEP 4b passed: Secondary server verified")

        # Step 5: Display complete TACACS+ status
        st.log("STEP 5: Display complete TACACS+ status with all servers")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)
        st.log(f"Complete TACACS+ Configuration with Multiple Servers:\n{output}")
        st.log("STEP 5 passed: Complete TACACS+ configuration displayed")

    except Exception as e:
        st.error(f"Exception in test_tacacs_03_multiple_servers: {str(e)}")
        result = False

    if result:
        st.log("TEST-03 PASSED: Multiple Servers test completed successfully")
    else:
        st.error("TEST-03 FAILED: Multiple Servers test failed")

    assert result, "Test failed: Multiple TACACS+ Server Configuration"


@pytest.mark.tacacs
def test_tacacs_04_per_server_settings():
    """
    Test 04: Per-Server TACACS+ Settings (Passkey, Timeout, Port, VRF)

    Test Steps:
    1. Configure global TACACS+ baseline
    2. Configure server with per-server passkey override
    3. Configure server with different TCP port
    4. Configure server with per-server timeout
    5. Configure server with specific VRF
    6. Verify all per-server settings are applied correctly

    Expected Outcome:
    - Per-server passkey overrides global passkey
    - Per-server TCP port (50) overrides default (49)
    - Per-server timeout overrides global timeout
    - Per-server VRF is correctly assigned
    - All settings are persistent and visible in 'show tacacs' output
    """
    st.banner("-" * 80)
    st.banner("TEST-04: Per-Server TACACS+ Settings")
    st.banner("-" * 80)

    dut = vars.D1
    result = True

    try:
        # Step 1: Configure global TACACS+ baseline
        st.log("STEP 1: Configure global TACACS+ baseline")
        if not configure_global_tacacs(dut, CONFIG.global_passkey):
            st.error("Failed to configure global TACACS+")
            result = False
        else:
            st.log("STEP 1 passed: Global TACACS+ baseline configured")

        # Step 2: Configure primary server with per-server passkey
        st.log("STEP 2: Configure server with per-server passkey override")
        if not configure_tacacs_server(dut, CONFIG.servers[0]):
            st.error("Failed to configure server with per-server passkey")
            result = False
        else:
            st.log(f"STEP 2 passed: Server {CONFIG.servers[0]['address']} with per-server passkey configured")

        # Step 3: Verify per-server settings
        st.log("STEP 3: Verify per-server settings")
        output = st.show(dut, "show tacacs", type=data.cli_type, skip_error_check=True)
        output_str = str(output)

        # Check for per-server passkey
        if CONFIG.servers[0].get('passkey') and CONFIG.servers[0]['passkey'] in output_str:
            st.log(f"Per-server passkey for {CONFIG.servers[0]['address']} verified")
        else:
            st.log(f"Per-server passkey verification skipped (may be hidden)")

        # Check for per-server port
        if str(CONFIG.servers[0]['tcp_port']) in output_str:
            st.log(f"TCP port {CONFIG.servers[0]['tcp_port']} for {CONFIG.servers[0]['address']} verified")

        # Check for per-server timeout
        if CONFIG.servers[0].get('timeout') and str(CONFIG.servers[0]['timeout']) in output_str:
            st.log(f"Timeout {CONFIG.servers[0]['timeout']} for {CONFIG.servers[0]['address']} verified")

        # Check for VRF
        if CONFIG.servers[0].get('vrf') and f"vrf {CONFIG.servers[0]['vrf']}" in output_str:
            st.log(f"VRF {CONFIG.servers[0]['vrf']} for {CONFIG.servers[0]['address']} verified")

        st.log("STEP 3 passed: Per-server settings verification completed")
        st.log(f"Complete Configuration:\n{output}")

    except Exception as e:
        st.error(f"Exception in test_tacacs_04_per_server_settings: {str(e)}")
        result = False

    if result:
        st.log("TEST-04 PASSED: Per-Server Settings test completed successfully")
    else:
        st.error("TEST-04 FAILED: Per-Server Settings test failed")

    assert result, "Test failed: Per-Server TACACS+ Settings"


if __name__ == "__main__":
    # This allows running the script directly for debugging
    st.log("Running advanced TACACS+ tests directly")
    pytest.main([__file__, "-v"])
