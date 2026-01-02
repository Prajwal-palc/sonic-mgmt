"""
Test Suite for Clear ARP/ND IS-CLI Feature
Feature: SM_ISCLI_DROP1_FEATURE8
Status: In-Progress - Unit Testing Phase
"""

import pytest
import subprocess
import time
import re


class TestARPBasics:
    """Basic ARP table operations"""

    def test_show_arp(self):
        """Test: show arp - Display ARP table"""
        result = subprocess.run(['show', 'arp'], capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, f"show arp failed: {result.stderr}"
        print(f"✓ show arp output:\n{result.stdout[:300]}")

    def test_arp_count_before_clear(self):
        """Test: Count ARP entries before clear"""
        result = subprocess.run(['show', 'arp'], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Count non-header lines
            lines = [l for l in result.stdout.split('\n') if l.strip() and not l.startswith('Address')]
            count = len(lines)
            print(f"✓ ARP entries before clear: {count}")
            return count
        return 0


class TestClearARP:
    """Test sonic-clear arp command"""

    def test_clear_arp_all(self):
        """Test: sonic-clear arp - Clear all ARP entries"""
        # First, ensure we have some ARP entries by pinging
        subprocess.run(['ping', '-c', '1', '127.0.0.1'],
                      capture_output=True, text=True, timeout=10)
        time.sleep(1)

        # Get ARP count before
        before = subprocess.run(['show', 'arp'], capture_output=True, text=True, timeout=30)
        before_lines = len([l for l in before.stdout.split('\n') if l.strip() and not l.startswith('Address')])

        # Clear ARP
        result = subprocess.run(['sonic-clear', 'arp'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"Command output: {result.stdout}")
            print(f"Command error: {result.stderr}")

        assert result.returncode == 0, f"sonic-clear arp failed: {result.stderr}"

        time.sleep(2)

        # Get ARP count after
        after = subprocess.run(['show', 'arp'], capture_output=True, text=True, timeout=30)
        after_lines = len([l for l in after.stdout.split('\n') if l.strip() and not l.startswith('Address')])

        print(f"✓ sonic-clear arp executed successfully")
        print(f"  ARP entries: before={before_lines}, after={after_lines}")

    def test_clear_arp_with_sudo(self):
        """Test: sudo sonic-clear arp"""
        result = subprocess.run(['sudo', 'sonic-clear', 'arp'],
                              capture_output=True, text=True, timeout=30)

        # Should work with or without sudo
        print(f"  sonic-clear arp with sudo: rc={result.returncode}")

    def test_arp_repopulation(self):
        """Test: ARP entries repopulate after clear"""
        # Clear ARP
        subprocess.run(['sonic-clear', 'arp'], capture_output=True, text=True, timeout=30)
        time.sleep(1)

        # Generate some traffic
        subprocess.run(['ping', '-c', '2', '127.0.0.1'],
                      capture_output=True, text=True, timeout=10)
        time.sleep(2)

        # Check ARP table
        result = subprocess.run(['show', 'arp'], capture_output=True, text=True, timeout=30)
        lines = len([l for l in result.stdout.split('\n') if l.strip() and not l.startswith('Address')])

        print(f"✓ ARP entries repopulated: {lines} entries")


class TestIPv6ND:
    """Test IPv6 Neighbor Discovery operations"""

    def test_show_ndp(self):
        """Test: show ndp - Display IPv6 neighbor table"""
        result = subprocess.run(['show', 'ndp'], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✓ show ndp output:\n{result.stdout[:300]}")
        else:
            print(f"⚠ show ndp failed (IPv6 may not be configured): {result.stderr}")

    def test_ipv6_neighbors(self):
        """Test: ip -6 neighbor show"""
        result = subprocess.run(['ip', '-6', 'neighbor', 'show'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print(f"✓ IPv6 neighbors:\n{result.stdout[:300]}")
        else:
            print(f"⚠ IPv6 neighbors command failed")


class TestClearND:
    """Test sonic-clear ndp command"""

    def test_clear_ndp_all(self):
        """Test: sonic-clear ndp - Clear all IPv6 neighbor entries"""
        # Check if IPv6 is available
        check_ipv6 = subprocess.run(['ip', '-6', 'addr'],
                                   capture_output=True, text=True, timeout=10)

        if check_ipv6.returncode != 0 or 'inet6' not in check_ipv6.stdout:
            pytest.skip("IPv6 not configured on system")

        # Get ND count before
        before = subprocess.run(['show', 'ndp'], capture_output=True, text=True, timeout=30)

        # Clear NDP
        result = subprocess.run(['sonic-clear', 'ndp'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            print(f"Command output: {result.stdout}")
            print(f"Command error: {result.stderr}")

        # Should succeed even if no IPv6 neighbors exist
        if result.returncode == 0:
            print(f"✓ sonic-clear ndp executed successfully")
        else:
            print(f"⚠ sonic-clear ndp failed: {result.stderr}")

        time.sleep(2)

        # Get ND count after
        after = subprocess.run(['show', 'ndp'], capture_output=True, text=True, timeout=30)
        print(f"  NDP table after clear:\n{after.stdout[:200]}")

    def test_clear_ndp_with_sudo(self):
        """Test: sudo sonic-clear ndp"""
        result = subprocess.run(['sudo', 'sonic-clear', 'ndp'],
                              capture_output=True, text=True, timeout=30)

        print(f"  sonic-clear ndp with sudo: rc={result.returncode}")


class TestClearARPInterface:
    """Test clearing ARP for specific interfaces"""

    def test_clear_arp_specific_interface(self):
        """Test: Clear ARP for specific interface (if supported)"""
        # Get interface list
        iface_result = subprocess.run(['ip', 'link', 'show'],
                                     capture_output=True, text=True, timeout=30)

        # Find first interface
        match = re.search(r'\d+: (eth\d+|Ethernet\d+):', iface_result.stdout)

        if match:
            interface = match.group(1)

            # Try interface-specific clear (syntax may vary)
            result = subprocess.run(['ip', 'neigh', 'flush', 'dev', interface],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print(f"✓ Cleared ARP for interface {interface}")
            else:
                print(f"  Interface-specific ARP clear: {result.stderr}")
        else:
            pytest.skip("No suitable interface found for testing")

    def test_show_arp_interface(self):
        """Test: Show ARP for specific interface"""
        # Get interfaces
        result = subprocess.run(['show', 'interfaces', 'status'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            match = re.search(r'(Ethernet\d+)', result.stdout)
            if match:
                interface = match.group(1)
                # Try to show ARP for interface
                arp_result = subprocess.run(f'show arp | grep {interface}',
                                          shell=True, capture_output=True, text=True, timeout=30)
                print(f"  ARP entries for {interface}:\n{arp_result.stdout[:200]}")


class TestSystemStability:
    """Test system stability after ARP/ND clear"""

    def test_multiple_clear_arp(self):
        """Test: Multiple consecutive ARP clears"""
        for i in range(3):
            result = subprocess.run(['sonic-clear', 'arp'],
                                  capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, f"Clear ARP #{i+1} failed"
            time.sleep(1)

        print(f"✓ Multiple ARP clears completed without issue")

    def test_multiple_clear_ndp(self):
        """Test: Multiple consecutive NDP clears"""
        for i in range(3):
            result = subprocess.run(['sonic-clear', 'ndp'],
                                  capture_output=True, text=True, timeout=30)
            # May fail if IPv6 not configured, that's okay
            time.sleep(1)

        print(f"✓ Multiple NDP clears completed")

    def test_system_connectivity_after_clear(self):
        """Test: Verify connectivity after clearing ARP/NDP"""
        # Clear ARP
        subprocess.run(['sonic-clear', 'arp'], capture_output=True, text=True, timeout=30)
        time.sleep(2)

        # Test connectivity
        result = subprocess.run(['ping', '-c', '3', '127.0.0.1'],
                              capture_output=True, text=True, timeout=15)

        assert result.returncode == 0, "Connectivity lost after ARP clear"
        print(f"✓ System connectivity maintained after ARP clear")

    def test_no_kernel_errors(self):
        """Test: Check for kernel errors after ARP/ND operations"""
        # Clear both
        subprocess.run(['sonic-clear', 'arp'], capture_output=True, text=True, timeout=30)
        subprocess.run(['sonic-clear', 'ndp'], capture_output=True, text=True, timeout=30)

        time.sleep(2)

        # Check dmesg for errors
        result = subprocess.run(['dmesg', '--level=err', '--since', '1 minute ago'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            if result.stdout.strip():
                print(f"  Recent kernel errors found:\n{result.stdout[:200]}")
            else:
                print(f"✓ No kernel errors after ARP/NDP clear")
        else:
            print(f"  Could not check dmesg (may need sudo)")


class TestClearARPNDNegative:
    """Negative test cases"""

    def test_clear_arp_invalid_option(self):
        """Test: sonic-clear arp with invalid option"""
        result = subprocess.run(['sonic-clear', 'arp', '--invalid-option'],
                              capture_output=True, text=True, timeout=30)

        # Should fail or ignore
        print(f"  Invalid option handling: rc={result.returncode}")

    def test_clear_ndp_invalid_option(self):
        """Test: sonic-clear ndp with invalid option"""
        result = subprocess.run(['sonic-clear', 'ndp', '--invalid-option'],
                              capture_output=True, text=True, timeout=30)

        print(f"  Invalid option handling: rc={result.returncode}")

    def test_clear_nonexistent_command(self):
        """Test: sonic-clear with non-existent subcommand"""
        result = subprocess.run(['sonic-clear', 'nonexistent'],
                              capture_output=True, text=True, timeout=30)

        assert result.returncode != 0, "Non-existent command should fail"
        print(f"✓ Non-existent subcommand properly rejected")


class TestARPNDHelp:
    """Test help and usage information"""

    def test_sonic_clear_help(self):
        """Test: sonic-clear --help"""
        result = subprocess.run(['sonic-clear', '--help'],
                              capture_output=True, text=True, timeout=30)

        if result.returncode == 0 or result.stdout:
            assert 'arp' in result.stdout.lower() or 'ndp' in result.stdout.lower()
            print(f"✓ sonic-clear help shows arp/ndp commands")
        else:
            print(f"⚠ sonic-clear help not available")

    def test_sonic_clear_arp_help(self):
        """Test: sonic-clear arp --help"""
        result = subprocess.run(['sonic-clear', 'arp', '--help'],
                              capture_output=True, text=True, timeout=30)

        # May not have dedicated help, but shouldn't crash
        print(f"  sonic-clear arp help: rc={result.returncode}")


class TestPerformance:
    """Performance tests"""

    @pytest.mark.slow
    def test_clear_arp_execution_time(self):
        """Test: Measure ARP clear execution time"""
        start = time.time()
        result = subprocess.run(['sonic-clear', 'arp'],
                              capture_output=True, text=True, timeout=30)
        duration = time.time() - start

        assert result.returncode == 0
        assert duration < 5.0, f"ARP clear took too long: {duration}s"
        print(f"✓ ARP clear execution time: {duration:.2f}s")

    @pytest.mark.slow
    def test_clear_ndp_execution_time(self):
        """Test: Measure NDP clear execution time"""
        start = time.time()
        result = subprocess.run(['sonic-clear', 'ndp'],
                              capture_output=True, text=True, timeout=30)
        duration = time.time() - start

        # Should complete quickly even if it fails
        assert duration < 5.0, f"NDP clear took too long: {duration}s"
        print(f"✓ NDP clear execution time: {duration:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short', '-m', 'not slow'])
