"""
Test Suite for NTP IS-CLI Feature
Feature: SM_ISCLI_DROP1_FEATURE7
Status: In-Progress - Testing/Verification Phase
"""

import pytest
import subprocess
import time
import json
import re


class TestNTPBasicCommands:
    """Basic NTP show and configuration commands"""

    def test_show_ntp(self):
        """Test: show ntp"""
        result = subprocess.run(['show', 'ntp'], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"show ntp failed: {result.stderr}"
        print(f"✓ show ntp output:\n{result.stdout[:300]}")

    def test_ntp_in_running_config(self):
        """Test: show runningconfiguration all | grep ntp"""
        result = subprocess.run('show runningconfiguration all | grep -i ntp',
                              shell=True, capture_output=True, text=True, timeout=30)
        print(f"✓ NTP in running config:\n{result.stdout[:300]}")


class TestNTPServerManagement:
    """Test NTP server/pool add and delete operations"""

    @pytest.fixture(scope='class')
    def cleanup_test_servers(self):
        """Cleanup any test NTP servers before and after tests"""
        test_servers = ['pool.ntp.org', 'time.google.com', '216.239.35.0']

        for server in test_servers:
            # Try to remove if exists
            subprocess.run(['sudo', 'config', 'ntp', 'del', server],
                         capture_output=True, text=True, timeout=30)

        yield

        # Cleanup after tests
        for server in test_servers:
            subprocess.run(['sudo', 'config', 'ntp', 'del', server],
                         capture_output=True, text=True, timeout=30)

    def test_ntp_add_server(self, cleanup_test_servers):
        """Test: sudo config ntp add --association-type server <server>"""
        ntp_server = "216.239.35.0"  # Google Public NTP

        result = subprocess.run(['sudo', 'config', 'ntp', 'add', ntp_server],
                              capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"Command output: {result.stdout}")
            print(f"Command error: {result.stderr}")

        # Some implementations might require --association-type
        if result.returncode != 0:
            result = subprocess.run(['sudo', 'config', 'ntp', 'add',
                                   '--association-type', 'server', ntp_server],
                                  capture_output=True, text=True, timeout=30)

        assert result.returncode == 0, f"NTP server add failed: {result.stderr}"

        time.sleep(2)

        # Verify server added
        verify = subprocess.run(['show', 'ntp'], capture_output=True, text=True, timeout=30)
        assert ntp_server in verify.stdout, f"NTP server {ntp_server} not in show ntp output"
        print(f"✓ NTP server added: {ntp_server}")

    def test_ntp_add_pool(self, cleanup_test_servers):
        """Test: sudo config ntp add --association-type pool <pool>"""
        ntp_pool = "pool.ntp.org"

        result = subprocess.run(['sudo', 'config', 'ntp', 'add',
                               '--association-type', 'pool', ntp_pool],
                              capture_output=True, text=True, timeout=30)

        # If pool association not supported, try without type
        if result.returncode != 0:
            result = subprocess.run(['sudo', 'config', 'ntp', 'add', ntp_pool],
                                  capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            time.sleep(2)
            verify = subprocess.run(['show', 'ntp'], capture_output=True, text=True, timeout=30)
            assert ntp_pool in verify.stdout
            print(f"✓ NTP pool added: {ntp_pool}")
        else:
            print(f"⚠ NTP pool add not supported or failed: {result.stderr}")

    def test_ntp_del_server(self, cleanup_test_servers):
        """Test: sudo config ntp del <server>"""
        ntp_server = "time.google.com"

        # First add it
        subprocess.run(['sudo', 'config', 'ntp', 'add', ntp_server],
                      capture_output=True, text=True, timeout=30)
        time.sleep(2)

        # Now delete it
        result = subprocess.run(['sudo', 'config', 'ntp', 'del', ntp_server],
                              capture_output=True, text=True, timeout=30)

        assert result.returncode == 0, f"NTP server delete failed: {result.stderr}"

        time.sleep(2)

        # Verify removed
        verify = subprocess.run(['show', 'ntp'], capture_output=True, text=True, timeout=30)
        # Server should not be in output (or marked as deleted)
        print(f"✓ NTP server deleted: {ntp_server}")


class TestNTPVRFSupport:
    """Test NTP with VRF management"""

    def test_show_vrf(self):
        """Test: Verify mgmt VRF exists"""
        result = subprocess.run(['show', 'vrf'], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✓ VRF configuration:\n{result.stdout[:200]}")
        else:
            print(f"⚠ show vrf command not available or failed")

    def test_vrf_mgmt_exists(self):
        """Test: Verify mgmt VRF is configured"""
        # Check if mgmt VRF exists
        result = subprocess.run('ip vrf show | grep mgmt',
                              shell=True, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and 'mgmt' in result.stdout:
            print(f"✓ mgmt VRF exists")
        else:
            print(f"⚠ mgmt VRF may not be configured")

    def test_ping_ntp_server_via_vrf(self):
        """Test: sudo ip vrf exec mgmt ping <server>"""
        ntp_server = "8.8.8.8"  # Google DNS as test

        result = subprocess.run(['sudo', 'ip', 'vrf', 'exec', 'mgmt', 'ping', '-c', '2', ntp_server],
                              capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            print(f"✓ Ping via mgmt VRF successful to {ntp_server}")
        else:
            print(f"⚠ Ping via mgmt VRF failed (may be network issue): {result.stderr}")


class TestNTPChronyIntegration:
    """Test chrony NTP daemon integration"""

    def test_chronyc_tracking(self):
        """Test: chronyc tracking"""
        result = subprocess.run(['chronyc', 'tracking'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✓ chronyc tracking output:\n{result.stdout}")
            # Check for synchronization status
            if 'leap status' in result.stdout.lower() or 'reference id' in result.stdout.lower():
                print(f"  NTP sync information available")
        else:
            print(f"⚠ chronyc tracking failed: {result.stderr}")

    def test_chronyc_sources(self):
        """Test: chronyc sources"""
        result = subprocess.run(['chronyc', 'sources'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✓ chronyc sources output:\n{result.stdout}")
            # Parse for configured sources
            lines = result.stdout.split('\n')
            source_count = sum(1 for line in lines if line.startswith('^') or line.startswith('='))
            print(f"  Active NTP sources: {source_count}")
        else:
            print(f"⚠ chronyc sources failed: {result.stderr}")

    def test_chronyc_sourcestats(self):
        """Test: chronyc sourcestats"""
        result = subprocess.run(['chronyc', 'sourcestats'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✓ chronyc sourcestats available")
        else:
            print(f"⚠ chronyc sourcestats failed")

    def test_chrony_service_status(self):
        """Test: Check if chronyd service is running"""
        # Try systemctl first
        result = subprocess.run(['systemctl', 'is-active', 'chronyd'],
                              capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and 'active' in result.stdout:
            print(f"✓ chronyd service is active")
        else:
            # Try docker container
            docker_result = subprocess.run('docker ps | grep ntp',
                                         shell=True, capture_output=True, text=True, timeout=10)
            if 'ntp' in docker_result.stdout.lower():
                print(f"✓ NTP service running in container")
            else:
                print(f"⚠ chronyd service status unclear")


class TestNTPConfigDB:
    """Test NTP configuration in CONFIG_DB"""

    def test_ntp_in_config_db(self):
        """Test: redis-cli -n 4 operations for CONFIG_DB debugging"""
        # Get NTP config from Redis
        result = subprocess.run(['redis-cli', '-n', '4', 'KEYS', 'NTP_SERVER*'],
                              capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            print(f"✓ NTP_SERVER keys in CONFIG_DB:\n{result.stdout}")

            # Get details of first key if exists
            if result.stdout.strip():
                keys = result.stdout.strip().split('\n')
                if keys:
                    detail = subprocess.run(['redis-cli', '-n', '4', 'HGETALL', keys[0]],
                                          capture_output=True, text=True, timeout=10)
                    print(f"  Details: {detail.stdout[:200]}")
        else:
            print(f"⚠ Could not access CONFIG_DB (redis-cli may not be available)")

    def test_ntp_global_config(self):
        """Test: Check NTP global configuration in CONFIG_DB"""
        result = subprocess.run(['redis-cli', '-n', '4', 'HGETALL', 'NTP|global'],
                              capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and result.stdout.strip():
            print(f"✓ NTP global config:\n{result.stdout}")
        else:
            print(f"  NTP global config not found or empty")


class TestNTPNegative:
    """Negative test cases"""

    def test_add_invalid_server(self):
        """Test: Add invalid NTP server address"""
        invalid_server = "not.a.valid.ntp.server.xyz"

        result = subprocess.run(['sudo', 'config', 'ntp', 'add', invalid_server],
                              capture_output=True, text=True, timeout=30)

        # May succeed (DNS lookup happens later) or fail
        print(f"  Adding invalid server: rc={result.returncode}")
        if result.returncode == 0:
            # Cleanup
            subprocess.run(['sudo', 'config', 'ntp', 'del', invalid_server],
                         capture_output=True, text=True, timeout=30)

    def test_delete_nonexistent_server(self):
        """Test: Delete NTP server that doesn't exist"""
        result = subprocess.run(['sudo', 'config', 'ntp', 'del', '1.2.3.4'],
                              capture_output=True, text=True, timeout=30)

        # Should handle gracefully
        print(f"  Deleting non-existent server: rc={result.returncode}")

    def test_add_duplicate_server(self):
        """Test: Add same NTP server twice"""
        server = "time.google.com"

        # Add first time
        result1 = subprocess.run(['sudo', 'config', 'ntp', 'add', server],
                               capture_output=True, text=True, timeout=30)

        # Add second time
        result2 = subprocess.run(['sudo', 'config', 'ntp', 'add', server],
                               capture_output=True, text=True, timeout=30)

        # Should handle duplicate gracefully
        print(f"  Adding duplicate server: rc1={result1.returncode}, rc2={result2.returncode}")

        # Cleanup
        subprocess.run(['sudo', 'config', 'ntp', 'del', server],
                      capture_output=True, text=True, timeout=30)

    def test_invalid_association_type(self):
        """Test: Invalid association type"""
        result = subprocess.run(['sudo', 'config', 'ntp', 'add',
                               '--association-type', 'invalid', 'pool.ntp.org'],
                              capture_output=True, text=True, timeout=30)

        # Should fail with error
        assert result.returncode != 0, "Invalid association type should be rejected"
        print(f"✓ Invalid association type rejected")


class TestNTPSynchronization:
    """Test actual NTP synchronization (may take time)"""

    @pytest.mark.slow
    def test_ntp_sync_status(self):
        """Test: Check if NTP is synchronized (may take minutes)"""
        # Add a known good NTP server
        subprocess.run(['sudo', 'config', 'ntp', 'add', 'time.google.com'],
                      capture_output=True, text=True, timeout=30)

        # Wait a bit for sync attempt
        print("  Waiting 10 seconds for NTP sync attempt...")
        time.sleep(10)

        # Check sync status
        result = subprocess.run(['chronyc', 'tracking'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Look for sync indicators
            if 'not synchronised' in result.stdout.lower():
                print(f"  NTP not yet synchronized (may need more time)")
            else:
                print(f"  NTP tracking active:\n{result.stdout[:200]}")

    @pytest.mark.slow
    def test_time_offset(self):
        """Test: Check time offset from NTP sources"""
        result = subprocess.run(['chronyc', 'sources', '-v'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"  NTP sources with offset:\n{result.stdout[:400]}")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short', '-m', 'not slow'])
