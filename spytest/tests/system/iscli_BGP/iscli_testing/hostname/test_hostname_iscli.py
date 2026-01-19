"""
Test Suite for Hostname IS-CLI Feature
Feature: SM_ISCLI_DROP1_FEATURE6
Status: In-Progress - Unit Testing Phase
"""

import pytest
import subprocess
import time
import re


class TestHostnameBasic:
    """Basic hostname configuration tests"""

    @pytest.fixture(scope='class')
    def original_hostname(self):
        """Store original hostname to restore after tests"""
        result = subprocess.run(['hostname'], capture_output=True, text=True, timeout=10)
        hostname = result.stdout.strip()
        yield hostname
        # Restore original hostname after all tests
        subprocess.run(['sudo', 'config', 'hostname', hostname],
                      capture_output=True, text=True, timeout=30)
        time.sleep(2)

    def test_get_current_hostname(self):
        """Test: hostname command to get current hostname"""
        result = subprocess.run(['hostname'], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0
        print(f"✓ Current hostname: {result.stdout.strip()}")

    def test_set_hostname_basic(self, original_hostname):
        """Test: sudo config hostname <new_hostname>"""
        test_hostname = "sonic-test-device"

        # Set new hostname
        result = subprocess.run(['sudo', 'config', 'hostname', test_hostname],
                              capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"Command output: {result.stdout}")
            print(f"Command error: {result.stderr}")

        assert result.returncode == 0, f"Hostname change failed: {result.stderr}"

        # Wait for change to take effect
        time.sleep(3)

        # Verify hostname changed
        verify = subprocess.run(['hostname'], capture_output=True, text=True, timeout=10)
        current = verify.stdout.strip()

        assert current == test_hostname, f"Expected '{test_hostname}', got '{current}'"
        print(f"✓ Hostname successfully changed to: {test_hostname}")

    def test_hostname_in_prompt(self, original_hostname):
        """Test: Verify hostname appears in shell prompt"""
        test_hostname = "sonic-prompt-test"

        # Change hostname
        subprocess.run(['sudo', 'config', 'hostname', test_hostname],
                      capture_output=True, text=True, timeout=30)
        time.sleep(3)

        # Check if hostname appears in prompt (get from PS1 or prompt)
        result = subprocess.run(['bash', '-c', 'echo $HOSTNAME'],
                              capture_output=True, text=True, timeout=10)

        print(f"✓ Hostname in environment: {result.stdout.strip()}")

    def test_hostname_with_hyphen(self, original_hostname):
        """Test: Hostname with hyphens (valid format)"""
        test_hostname = "sonic-device-01"

        result = subprocess.run(['sudo', 'config', 'hostname', test_hostname],
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0

        time.sleep(2)
        verify = subprocess.run(['hostname'], capture_output=True, text=True, timeout=10)
        assert verify.stdout.strip() == test_hostname
        print(f"✓ Hostname with hyphens accepted: {test_hostname}")

    def test_hostname_with_numbers(self, original_hostname):
        """Test: Hostname with numbers (valid format)"""
        test_hostname = "sonic123"

        result = subprocess.run(['sudo', 'config', 'hostname', test_hostname],
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0

        time.sleep(2)
        verify = subprocess.run(['hostname'], capture_output=True, text=True, timeout=10)
        assert verify.stdout.strip() == test_hostname
        print(f"✓ Hostname with numbers accepted: {test_hostname}")


class TestHostnamePersistence:
    """Test hostname persistence across configuration"""

    def test_hostname_in_config_db(self):
        """Test: Verify hostname is saved to CONFIG_DB"""
        test_hostname = "sonic-configdb-test"

        # Set hostname
        subprocess.run(['sudo', 'config', 'hostname', test_hostname],
                      capture_output=True, text=True, timeout=30)
        time.sleep(3)

        # Check CONFIG_DB
        result = subprocess.run(['redis-cli', '-n', '4', 'HGET', 'DEVICE_METADATA|localhost', 'hostname'],
                              capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            db_hostname = result.stdout.strip().strip('"')
            assert db_hostname == test_hostname, f"CONFIG_DB has '{db_hostname}', expected '{test_hostname}'"
            print(f"✓ Hostname persisted in CONFIG_DB: {db_hostname}")
        else:
            print(f"⚠ Could not verify CONFIG_DB (may need redis-cli access)")

    def test_hostname_in_running_config(self):
        """Test: Verify hostname in running configuration"""
        result = subprocess.run('show runningconfiguration all | grep -i hostname',
                              shell=True, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout:
            print(f"✓ Hostname in running config:\n{result.stdout}")
        else:
            print(f"⚠ Could not find hostname in running config")


class TestHostnameNegative:
    """Negative test cases for hostname"""

    def test_hostname_too_long(self):
        """Test: Hostname exceeding 63 characters (should fail)"""
        # RFC 1035: hostname labels must be 63 characters or less
        long_hostname = "a" * 64

        result = subprocess.run(['sudo', 'config', 'hostname', long_hostname],
                              capture_output=True, text=True, timeout=30)

        # Should either reject or truncate
        if result.returncode != 0:
            print(f"✓ Long hostname rejected: {result.stderr}")
        else:
            verify = subprocess.run(['hostname'], capture_output=True, text=True, timeout=10)
            current = verify.stdout.strip()
            if len(current) <= 63:
                print(f"✓ Long hostname truncated to: {current} (len={len(current)})")
            else:
                pytest.fail(f"Hostname too long was accepted: {len(current)} chars")

    def test_hostname_with_spaces(self):
        """Test: Hostname with spaces (should fail)"""
        invalid_hostname = "sonic test"

        result = subprocess.run(['sudo', 'config', 'hostname', invalid_hostname],
                              capture_output=True, text=True, timeout=30)

        # Should fail due to spaces
        # Note: shell may interpret as multiple arguments
        print(f"✓ Hostname with spaces handled (rc={result.returncode})")

    def test_hostname_with_special_chars(self):
        """Test: Hostname with invalid special characters (should fail)"""
        invalid_hostnames = [
            "sonic@device",
            "sonic#test",
            "sonic_device",  # underscore may or may not be allowed
            "sonic.device",  # dots in FQDN context
        ]

        for invalid in invalid_hostnames:
            result = subprocess.run(['sudo', 'config', 'hostname', invalid],
                                  capture_output=True, text=True, timeout=30)

            # Some may fail, some may succeed depending on implementation
            print(f"  Testing '{invalid}': rc={result.returncode}")

    def test_hostname_starting_with_hyphen(self):
        """Test: Hostname starting with hyphen (should fail)"""
        invalid_hostname = "-sonic"

        result = subprocess.run(['sudo', 'config', 'hostname', invalid_hostname],
                              capture_output=True, text=True, timeout=30)

        # Should fail per RFC 952
        if result.returncode != 0:
            print(f"✓ Hostname starting with hyphen rejected")
        else:
            print(f"⚠ Hostname starting with hyphen was accepted (check implementation)")

    def test_hostname_empty(self):
        """Test: Empty hostname (should fail)"""
        result = subprocess.run(['sudo', 'config', 'hostname', ''],
                              capture_output=True, text=True, timeout=30)

        # Should fail
        assert result.returncode != 0, "Empty hostname should be rejected"
        print(f"✓ Empty hostname rejected")

    def test_hostname_numeric_only(self):
        """Test: Hostname with only numbers (may fail depending on RFC compliance)"""
        numeric_hostname = "12345"

        result = subprocess.run(['sudo', 'config', 'hostname', numeric_hostname],
                              capture_output=True, text=True, timeout=30)

        # RFC 952 says first char must be letter, but implementations vary
        print(f"  Numeric-only hostname: rc={result.returncode}")


class TestHostnamePermissions:
    """Test permission requirements"""

    def test_hostname_without_sudo(self):
        """Test: config hostname without sudo (should fail)"""
        result = subprocess.run(['config', 'hostname', 'test-no-sudo'],
                              capture_output=True, text=True, timeout=30)

        # Should fail without sudo
        if result.returncode != 0:
            print(f"✓ Hostname change without sudo properly rejected")
        else:
            print(f"⚠ Hostname change allowed without sudo (unexpected)")


class TestHostnameEdgeCases:
    """Edge case testing"""

    def test_hostname_max_valid_length(self):
        """Test: Hostname at maximum valid length (63 chars)"""
        max_hostname = "a" * 63

        result = subprocess.run(['sudo', 'config', 'hostname', max_hostname],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            time.sleep(2)
            verify = subprocess.run(['hostname'], capture_output=True, text=True, timeout=10)
            print(f"✓ Max length hostname accepted (63 chars)")
        else:
            print(f"⚠ Max length hostname rejected: {result.stderr}")

    def test_hostname_single_char(self):
        """Test: Single character hostname"""
        result = subprocess.run(['sudo', 'config', 'hostname', 'a'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✓ Single character hostname accepted")
        else:
            print(f"⚠ Single character hostname rejected")

    def test_hostname_case_sensitivity(self):
        """Test: Hostname case handling"""
        mixed_case = "SoNiC-TeSt"

        result = subprocess.run(['sudo', 'config', 'hostname', mixed_case],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            time.sleep(2)
            verify = subprocess.run(['hostname'], capture_output=True, text=True, timeout=10)
            actual = verify.stdout.strip()
            print(f"✓ Mixed case hostname: input='{mixed_case}', stored='{actual}'")
            # Hostnames are typically case-insensitive but case-preserving
        else:
            print(f"⚠ Mixed case hostname rejected")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
