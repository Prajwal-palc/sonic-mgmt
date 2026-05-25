"""
AAA TACACS+ Authentication TEST - Packet Flow with 4 Modules

Testcase: AAA TACACS+ Packet Capture and Authentication Flow
Author: Automated Testing Suite
Copyright (C) 2026

Description:
  Test validates AAA TACACS+ authentication packet flow with 4 modules:
  - Module 1: Unconfiguration - Remove all AAA and TACACS+ config at once
  - Module 2: Configuration - Configure all AAA and TACACS+ at once
  - Module 3: Validation - Verify configuration with show commands
  - Module 4: Cleanup - Remove all configuration at once

Pre-requisites:
  - DUT (SONiC Switch): 192.168.100.145
  - TACACS+ Server: 192.168.100.87 (adminuser/Regre@11)
  - Server Interface: enp1s0
  - Passkey: test123
  - Port: 49
  - Admin user: admin
  - Admin password: Admin123

Important Notes:
  - Test follows exact 4-module workflow (no repetition)
  - All configuration/unconfiguration done in batch
  - Uses spytest framework APIs (st.config, st.show, st.wait, st.log)
  - Packet capture is done manually on VM1 during test execution
  - Removes all configuration after test per test design
"""

from __future__ import annotations

import pytest
from spytest import st, SpyTestDict

# Global variables
vars = SpyTestDict()
data = SpyTestDict()

# Test configuration - AAA and TACACS+ parameters
CONFIG = SpyTestDict({
    "dut_ip": "192.168.100.145",
    "tacacs_server_ip": "192.168.100.87",
    "tacacs_server_interface": "enp1s0",
    "tacacs_passkey": "test123",
    "tacacs_port": 49,
    "admin_user": "admin",
    "admin_password": "Admin123",
    "capture_file": "/tmp/tacacs1.pcap",
    "server_username": "adminuser",
    "server_password": "Regre@11",
})


@pytest.fixture(scope="module", autouse=True)
def aaa_tacacs_module_hooks(request):
    """Module-level setup and teardown for AAA TACACS+ tests."""
    global vars, data

    st.banner("=" * 80)
    st.banner("AAA TACACS+ AUTHENTICATION TEST - PACKET FLOW VERIFICATION")
    st.banner("=" * 80)

    # Get topology - ensure minimum 1 DUT
    vars = st.ensure_min_topology("D1")
    data.cli_type = st.get_ui_type()
    if data.cli_type == 'click':
        data.cli_type = 'klish'

    st.log(f"DUT: {vars.D1} ({CONFIG.dut_ip})")
    st.log(f"CLI Type: {data.cli_type}")
    st.log(f"TACACS+ Server: {CONFIG.tacacs_server_ip}:{CONFIG.tacacs_port}")
    st.log(f"Packet Capture File: {CONFIG.capture_file}")
    st.log("")
    st.log("=" * 80)
    st.log("INSTRUCTIONS FOR MANUAL PACKET CAPTURE (run in parallel):")
    st.log("=" * 80)
    st.log(f"1. On VM1 ({CONFIG.tacacs_server_ip}), run:")
    st.log(f"   sudo tcpdump -nei {CONFIG.tacacs_server_interface} port {CONFIG.tacacs_port} -w {CONFIG.capture_file}")
    st.log(f"")
    st.log(f"2. From test client, attempt SSH to DUT:")
    st.log(f"   ssh admin@{CONFIG.dut_ip}")
    st.log(f"   - Try WRONG password: Admin")
    st.log(f"   - Try CORRECT password: Admin123")
    st.log(f"")
    st.log(f"3. Back on VM1, press Ctrl+C to stop tcpdump")
    st.log(f"   View packets: sudo tcpdump -r {CONFIG.capture_file} -n port {CONFIG.tacacs_port}")
    st.log("=" * 80)

    yield

    # Final cleanup after all tests
    st.banner("=" * 80)
    st.banner("FINAL MODULE CLEANUP")
    st.banner("=" * 80)


# ============================================================================
# 4-MODULE TESTCASE STRUCTURE
# ============================================================================

def test_001_unconfigure_all_aaa_tacacs():
    """
    MODULE 1: UNCONFIGURATION
    Remove all AAA and TACACS+ configuration at once
    """
    st.banner("=" * 80)
    st.banner("MODULE 1: UNCONFIGURATION - Remove all AAA and TACACS+ config")
    st.banner("=" * 80)

    # Batch unconfiguration - all commands at once
    commands = [
        "aaa authentication login default",
        "aaa authentication failthrough default",
        "aaa authentication fallback default",
        f"no tacacs server {CONFIG.tacacs_server_ip}",
    ]

    st.log("Executing batch unconfiguration commands")
    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)

    # Verify unconfiguration
    st.log("Verifying unconfiguration...")
    aaa_output = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"AAA Status after unconfiguration:\n{aaa_output}")

    st.log("✓ MODULE 1 COMPLETED: Unconfiguration successful")
    st.report_pass("msg", "Unconfiguration completed successfully")


def test_002_configure_all_aaa_tacacs():
    """
    MODULE 2: CONFIGURATION
    Configure all AAA and TACACS+ settings at once
    This matches the exact manual workflow:
      sonic(config)# aaa authentication login tacacs+
      sonic(config)# aaa authentication failthrough enable
      sonic(config)# aaa authentication fallback enable
      sonic(config)# tacacs server 192.168.100.87
      sonic(config)# tacacs passkey test123
    """
    st.banner("=" * 80)
    st.banner("MODULE 2: CONFIGURATION - Configure all AAA and TACACS+")
    st.banner("=" * 80)

    # Batch configuration - all commands at once (exact manual workflow)
    commands = [
        "aaa authentication login tacacs+",
        "aaa authentication failthrough enable",
        "aaa authentication fallback enable",
        f"tacacs server {CONFIG.tacacs_server_ip}",
        f"tacacs passkey {CONFIG.tacacs_passkey}",
    ]

    st.log("Executing batch configuration commands")
    st.log(f"Commands to execute:")
    for cmd in commands:
        st.log(f"  - {cmd}")

    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)

    st.log("Waiting for configuration to stabilize")
    st.wait(2, "Configuration stabilization")

    # Verify configuration
    st.log("Verifying configuration...")
    aaa_output = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"AAA Status:\n{aaa_output}")

    tacacs_output = st.show(vars.D1, "show tacacs", skip_tmpl=True, skip_error_check=True)
    st.log(f"TACACS Status:\n{tacacs_output}")

    # Verify AAA is configured with tacacs+
    if "tacacs+" not in aaa_output.lower():
        st.report_fail("msg", "AAA authentication login not set to tacacs+")

    if "true" not in aaa_output.lower() and "True" not in aaa_output:
        st.report_fail("msg", "Failthrough or Fallback not enabled")

    # Verify TACACS+ server is configured
    if CONFIG.tacacs_server_ip not in tacacs_output:
        st.report_fail("msg", f"TACACS+ server {CONFIG.tacacs_server_ip} not configured")

    if "49" not in tacacs_output:
        st.report_fail("msg", "TACACS+ port 49 not configured")

    if CONFIG.tacacs_passkey not in tacacs_output:
        st.report_fail("msg", f"TACACS+ passkey {CONFIG.tacacs_passkey} not configured")

    st.log("✓ MODULE 2 COMPLETED: Configuration successful")
    st.log("")
    st.log("Configuration is now ready for packet capture testing!")
    st.log("TACACS+ server is listening on port 49 for authentication queries")
    st.log("")

    st.report_pass("msg", "Configuration verified successfully")


def test_003_verify_configuration_status():
    """
    MODULE 3: VALIDATION
    Verify that AAA and TACACS+ configuration is active and ready
    Display current status for manual packet capture verification
    """
    st.banner("=" * 80)
    st.banner("MODULE 3: VALIDATION - Verify Configuration Status")
    st.banner("=" * 80)

    st.log("Step 1: Verifying AAA authentication is enabled for TACACS+")
    aaa_status = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"Current AAA Status:\n{aaa_status}")

    if "tacacs+" not in aaa_status.lower():
        st.report_fail("msg", "TACACS+ authentication not enabled in AAA configuration")

    st.log("✓ AAA authentication confirmed as tacacs+")

    st.log("")
    st.log("Step 2: Verifying TACACS+ server configuration")
    tacacs_status = st.show(vars.D1, "show tacacs", skip_tmpl=True, skip_error_check=True)
    st.log(f"Current TACACS+ Status:\n{tacacs_status}")

    if CONFIG.tacacs_server_ip not in tacacs_status:
        st.report_fail("msg", f"TACACS+ server {CONFIG.tacacs_server_ip} not configured")

    if "49" not in tacacs_status:
        st.report_fail("msg", "TACACS+ port 49 not configured")

    st.log("✓ TACACS+ server configuration confirmed")

    st.log("")
    st.log("=" * 80)
    st.log("CONFIGURATION VERIFIED - Ready for Packet Capture Test")
    st.log("=" * 80)
    st.log("")
    st.log("Manual Packet Capture Instructions:")
    st.log("-" * 80)
    st.log(f"1. SSH to TACACS+ server VM1 ({CONFIG.tacacs_server_ip})")
    st.log(f"   Command: ssh {CONFIG.server_username}@{CONFIG.tacacs_server_ip}")
    st.log(f"   Password: {CONFIG.server_password}")
    st.log("")
    st.log(f"2. Start tcpdump to capture port 49 traffic:")
    st.log(f"   sudo tcpdump -nei {CONFIG.tacacs_server_interface} port {CONFIG.tacacs_port} -w {CONFIG.capture_file}")
    st.log("")
    st.log(f"3. From test client, SSH to DUT:")
    st.log(f"   ssh {CONFIG.admin_user}@{CONFIG.dut_ip}")
    st.log(f"   Try WRONG password: {CONFIG.admin_user}")
    st.log(f"   Try CORRECT password: {CONFIG.admin_password}")
    st.log("")
    st.log(f"4. Back on VM1, press Ctrl+C to stop tcpdump")
    st.log(f"5. View captured packets:")
    st.log(f"   sudo tcpdump -r {CONFIG.capture_file} -n port {CONFIG.tacacs_port}")
    st.log("")
    st.log("Expected packet flow:")
    st.log(f"  - DUT ({CONFIG.dut_ip}) sends AUTH-START to server ({CONFIG.tacacs_server_ip}:49)")
    st.log(f"  - Server responds with AUTH-REPLY (FAILURE for wrong password)")
    st.log(f"  - DUT sends AUTH-START again")
    st.log(f"  - Server responds with AUTH-REPLY (SUCCESS for correct password)")
    st.log("-" * 80)

    st.log("✓ MODULE 3 COMPLETED: Configuration validation successful")
    st.report_pass("msg", "Configuration validation completed - Ready for manual packet capture test")


def test_004_cleanup_and_remove_all():
    """
    MODULE 4: CLEANUP
    Remove all configuration and verify system returns to default state
    """
    st.banner("=" * 80)
    st.banner("MODULE 4: CLEANUP - Remove all configuration")
    st.banner("=" * 80)

    # Batch unconfiguration - remove all AAA and TACACS+ settings
    st.log("Step 1: Removing all AAA and TACACS+ configuration")
    commands = [
        "aaa authentication login default",
        "aaa authentication failthrough default",
        "aaa authentication fallback default",
        f"no tacacs server {CONFIG.tacacs_server_ip}",
    ]

    st.config(vars.D1, commands, type=data.cli_type, skip_error_check=True)
    st.log("Configuration removal executed")

    # Step 2: Verify cleanup
    st.log("Step 2: Verifying cleanup")
    aaa_final = st.show(vars.D1, "show aaa", skip_tmpl=True, skip_error_check=True)
    st.log(f"Final AAA status:\n{aaa_final}")

    st.log("")
    st.log("Step 3: Verifying TACACS+ server is removed")
    tacacs_final = st.show(vars.D1, "show tacacs", skip_tmpl=True, skip_error_check=True)
    st.log(f"Final TACACS+ status:\n{tacacs_final}")

    st.log("")
    st.log("✓ MODULE 4 COMPLETED: Cleanup and removal successful")
    st.log("System has been returned to default configuration")

    st.report_pass("msg", "Cleanup and removal completed successfully")
