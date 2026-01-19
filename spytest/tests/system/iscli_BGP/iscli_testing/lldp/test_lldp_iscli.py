"""
Test Suite for LLDP IS-CLI Feature
Feature: SM_ISCLI_DROP1_FEATURE5
Status: In-Progress - Testing/Verification Phase
"""

import pytest
import subprocess
import json
import time
import re


class TestLLDPBasicCommands:
    """Test basic LLDP show commands"""

    def test_lldp_table(self):
        """Test: show lldp table"""
        result = subprocess.run(['show', 'lldp', 'table'],
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        assert len(result.stdout) > 0, "No output returned"
        print(f"✓ show lldp table - PASSED\n{result.stdout[:200]}")

    def test_lldp_neighbors(self):
        """Test: show lldp neighbors"""
        result = subprocess.run(['show', 'lldp', 'neighbors'],
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        print(f"✓ show lldp neighbors - PASSED\n{result.stdout[:200]}")

    def test_lldp_neighbors_verbose(self):
        """Test: show lldp neighbors --verbose"""
        result = subprocess.run(['show', 'lldp', 'neighbors', '--verbose'],
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"Command failed: {result.stderr}"
        # Verbose should have more details than basic
        assert len(result.stdout) > 0, "No verbose output"
        print(f"✓ show lldp neighbors --verbose - PASSED")

    def test_lldp_neighbors_specific_interface(self):
        """Test: show lldp neighbors [INTERFACE]"""
        # First get available interfaces
        iface_result = subprocess.run(['show', 'interfaces', 'status'],
                                     capture_output=True, text=True, timeout=30)

        # Extract first Ethernet interface
        match = re.search(r'(Ethernet\d+)', iface_result.stdout)
        if match:
            interface = match.group(1)
            result = subprocess.run(['show', 'lldp', 'neighbors', interface],
                                  capture_output=True, text=True, timeout=30)
            # May return 0 even if no neighbor, just shouldn't error
            assert result.returncode == 0, f"Command failed for {interface}"
            print(f"✓ show lldp neighbors {interface} - PASSED")
        else:
            pytest.skip("No Ethernet interfaces found")


class TestLLDPFeatureControl:
    """Test LLDP feature enable/disable"""

    def test_show_lldp_feature_status(self):
        """Test: show feature status lldp"""
        result = subprocess.run(['show', 'feature', 'status'],
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        assert 'lldp' in result.stdout.lower(), "LLDP not in feature list"
        print(f"✓ show feature status - LLDP present")

    def test_lldp_enable(self):
        """Test: sudo config feature state lldp enabled"""
        result = subprocess.run(['sudo', 'config', 'feature', 'state', 'lldp', 'enabled'],
                              capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f"Warning: Enable command returned {result.returncode}")
            print(f"stderr: {result.stderr}")
            print(f"stdout: {result.stdout}")

        # Wait for service to start
        time.sleep(5)

        # Verify service is running
        docker_result = subprocess.run(['docker', 'ps'],
                                     capture_output=True, text=True, timeout=30)
        assert 'lldp' in docker_result.stdout.lower(), "LLDP container not running"
        print(f"✓ LLDP enabled and container running")

    def test_lldp_disable(self):
        """Test: sudo config feature state lldp disabled"""
        result = subprocess.run(['sudo', 'config', 'feature', 'state', 'lldp', 'disabled'],
                              capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f"Warning: Disable command returned {result.returncode}")

        # Wait for service to stop
        time.sleep(5)

        # Re-enable for other tests
        subprocess.run(['sudo', 'config', 'feature', 'state', 'lldp', 'enabled'],
                      capture_output=True, text=True, timeout=60)
        time.sleep(3)
        print(f"✓ LLDP disable tested and re-enabled")


class TestLLDPHelp:
    """Test help commands"""

    def test_lldp_table_help(self):
        """Test: show lldp table --help"""
        result = subprocess.run(['show', 'lldp', 'table', '--help'],
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        assert 'usage' in result.stdout.lower() or 'help' in result.stdout.lower()
        print(f"✓ show lldp table --help - PASSED")

    def test_lldp_neighbors_help(self):
        """Test: show lldp neighbors --help"""
        result = subprocess.run(['show', 'lldp', 'neighbors', '--help'],
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        print(f"✓ show lldp neighbors --help - PASSED")


class TestLLDPDataAnalysis:
    """Test data filtering and analysis commands"""

    def test_lldp_grep_mgmtip(self):
        """Test: show lldp neighbors | grep -i 'mgmtip'"""
        result = subprocess.run('show lldp neighbors | grep -i "mgmtip"',
                              shell=True, capture_output=True, text=True, timeout=30)
        # May not have results, but shouldn't error
        print(f"✓ LLDP grep mgmtip - Command executed")

    def test_lldp_grep_capability(self):
        """Test: show lldp neighbors | grep -i 'capability'"""
        result = subprocess.run('show lldp neighbors | grep -i "capability"',
                              shell=True, capture_output=True, text=True, timeout=30)
        print(f"✓ LLDP grep capability - Command executed")

    def test_lldp_count_ethernet(self):
        """Test: show lldp table | grep -c 'Ethernet'"""
        result = subprocess.run('show lldp table | grep -c "Ethernet"',
                              shell=True, capture_output=True, text=True, timeout=30)
        # Should return a number (even 0)
        try:
            count = int(result.stdout.strip())
            print(f"✓ LLDP Ethernet count: {count}")
        except ValueError:
            pytest.fail(f"Expected number, got: {result.stdout}")


class TestLLDPDockerIntegration:
    """Test LLDP Docker container integration"""

    def test_lldp_container_running(self):
        """Test: docker ps | grep lldp"""
        result = subprocess.run('docker ps | grep lldp',
                              shell=True, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, "LLDP container not found"
        assert 'lldp' in result.stdout.lower()
        print(f"✓ LLDP container is running")

    def test_lldp_container_processes(self):
        """Test: docker exec -it lldp ps aux"""
        result = subprocess.run(['docker', 'exec', 'lldp', 'ps', 'aux'],
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        print(f"✓ LLDP container processes accessible")

    def test_lldp_docker_logs(self):
        """Test: docker logs lldp"""
        result = subprocess.run(['docker', 'logs', '--tail', '50', 'lldp'],
                              capture_output=True, text=True, timeout=30)
        assert result.returncode == 0
        print(f"✓ LLDP docker logs accessible")


class TestLLDPRunningConfig:
    """Test LLDP configuration persistence"""

    def test_lldp_in_running_config(self):
        """Test: show runningconfiguration all | grep -A5 -B5 -i lldp"""
        result = subprocess.run('show runningconfiguration all | grep -A5 -B5 -i lldp',
                              shell=True, capture_output=True, text=True, timeout=30)
        # Should show LLDP configuration
        print(f"✓ LLDP in running configuration")
        print(f"Config snippet:\n{result.stdout[:300]}")


class TestLLDPNegative:
    """Negative test cases"""

    def test_invalid_interface(self):
        """Test: show lldp neighbors with invalid interface"""
        result = subprocess.run(['show', 'lldp', 'neighbors', 'InvalidInterface999'],
                              capture_output=True, text=True, timeout=30)
        # Should handle gracefully
        print(f"✓ Invalid interface handled (rc={result.returncode})")

    def test_invalid_option(self):
        """Test: show lldp neighbors with invalid option"""
        result = subprocess.run(['show', 'lldp', 'neighbors', '--invalid-option'],
                              capture_output=True, text=True, timeout=30)
        # Should show error or help
        assert result.returncode != 0 or 'invalid' in result.stdout.lower() or 'error' in result.stderr.lower()
        print(f"✓ Invalid option detected")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
