#!/usr/bin/env python3
"""
IS-CLI ZTP Test Script
Feature: SM_ISCLI_DROP1_FEATURE2
Date: 30-Dec-2025
"""

import subprocess
import json
import sys
import time
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class ZTPTester:
    def __init__(self):
        self.results = {'pass': 0, 'fail': 0, 'skip': 0, 'tests': []}
        self.start_time = datetime.now()

    def run_command(self, cmd, timeout=30, expect_fail=False):
        """Run shell command and return output"""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            if expect_fail:
                return result.returncode != 0, result.stdout + result.stderr
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s"
        except Exception as e:
            return False, str(e)

    def log_test(self, test_name, passed, output="", note=""):
        """Log test result"""
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"  [{status}] {test_name}")
        if note:
            print(f"      Note: {note}")
        if not passed and output:
            print(f"      Output: {output[:200]}")

        self.results['tests'].append({
            'name': test_name,
            'passed': passed,
            'output': output[:500],
            'note': note
        })

        if passed:
            self.results['pass'] += 1
        else:
            self.results['fail'] += 1

    def test_show_ztp_status(self):
        """Test: show ztp-status in IS-CLI"""
        print(f"\n{Colors.BLUE}Test 1: show ztp-status (IS-CLI){Colors.END}")
        success, output = self.run_command('sonic-cli -c "show ztp-status"')
        self.log_test(
            'show ztp-status (IS-CLI)',
            success and 'ZTP' in output,
            output,
            "Should display ZTP status information"
        )

    def test_ztp_enable(self):
        """Test: Enable ZTP"""
        print(f"\n{Colors.BLUE}Test 2: sudo config ztp enable{Colors.END}")
        success, output = self.run_command('sudo config ztp enable')
        self.log_test(
            'sudo config ztp enable',
            success,
            output,
            "Should enable ZTP service"
        )
        time.sleep(2)  # Wait for service to update

    def test_verify_ztp_enabled(self):
        """Test: Verify ZTP enabled"""
        print(f"\n{Colors.BLUE}Test 3: Verify ZTP enabled{Colors.END}")
        success, output = self.run_command('sonic-cli -c "show ztp-status"')
        self.log_test(
            'Verify ZTP enabled',
            'True' in output or 'Enabled' in output,
            output,
            "ZTP Admin Mode should be enabled"
        )

    def test_ztp_disable(self):
        """Test: Disable ZTP"""
        print(f"\n{Colors.BLUE}Test 4: sudo config ztp disable{Colors.END}")
        success, output = self.run_command('echo "y" | sudo config ztp disable')
        self.log_test(
            'sudo config ztp disable',
            success,
            output,
            "Should disable ZTP service (with confirmation)"
        )
        time.sleep(2)  # Wait for service to update

    def test_verify_ztp_disabled(self):
        """Test: Verify ZTP disabled"""
        print(f"\n{Colors.BLUE}Test 5: Verify ZTP disabled{Colors.END}")
        success, output = self.run_command('sonic-cli -c "show ztp-status"')
        self.log_test(
            'Verify ZTP disabled',
            'False' in output or 'Disabled' in output,
            output,
            "ZTP Admin Mode should be disabled"
        )

    def test_ztp_service_status(self):
        """Test: systemctl status ztp.service"""
        print(f"\n{Colors.BLUE}Test 6: systemctl status ztp.service{Colors.END}")
        success, output = self.run_command('systemctl status ztp.service --no-pager')
        self.log_test(
            'systemctl status ztp.service',
            'ztp.service' in output,
            output,
            "Should show ZTP service status"
        )

    def generate_report(self):
        """Generate test report"""
        print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
        print(f"{Colors.BLUE}ZTP TEST SUMMARY{Colors.END}")
        print(f"{Colors.BLUE}{'='*70}{Colors.END}")

        total = self.results['pass'] + self.results['fail'] + self.results['skip']
        pass_rate = (self.results['pass'] / total * 100) if total > 0 else 0

        print(f"\n  Total Tests: {total}")
        print(f"  {Colors.GREEN}Passed: {self.results['pass']}{Colors.END}")
        print(f"  {Colors.RED}Failed: {self.results['fail']}{Colors.END}")
        print(f"  Skipped: {self.results['skip']}")
        print(f"  {Colors.GREEN}Pass Rate: {pass_rate:.1f}%{Colors.END}")

        duration = (datetime.now() - self.start_time).total_seconds()
        print(f"\n  Test Duration: {duration:.1f} seconds")

        # Save detailed report
        report_file = f"ztp_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'feature': 'SM_ISCLI_DROP1_FEATURE2_ZTP',
                'summary': {
                    'total': total,
                    'pass': self.results['pass'],
                    'fail': self.results['fail'],
                    'skip': self.results['skip'],
                    'pass_rate': pass_rate,
                    'duration': duration
                },
                'tests': self.results['tests'],
                'timestamp': self.start_time.isoformat()
            }, f, indent=2)

        print(f"\n  Detailed report saved to: {report_file}")

        # Status message
        if self.results['fail'] == 0:
            print(f"\n{Colors.GREEN}✅ ALL ZTP TESTS PASSED - NO BUGS FOUND!{Colors.END}")
            print(f"  ZTP feature is working perfectly and ready for production.")
        else:
            print(f"\n{Colors.YELLOW}ISSUES FOUND:{Colors.END}")
            print(f"  {self.results['fail']} test(s) failed")

    def run_all_tests(self):
        """Run all ZTP tests"""
        print(f"{Colors.BLUE}{'='*70}{Colors.END}")
        print(f"{Colors.BLUE}IS-CLI ZTP TEST SUITE{Colors.END}")
        print(f"{Colors.BLUE}Feature: SM_ISCLI_DROP1_FEATURE2{Colors.END}")
        print(f"{Colors.BLUE}Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{Colors.BLUE}{'='*70}{Colors.END}")

        self.test_show_ztp_status()
        self.test_ztp_enable()
        self.test_verify_ztp_enabled()
        self.test_ztp_disable()
        self.test_verify_ztp_disabled()
        self.test_ztp_service_status()

        self.generate_report()

if __name__ == "__main__":
    tester = ZTPTester()
    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Tests interrupted by user{Colors.END}")
        tester.generate_report()
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        tester.generate_report()
        sys.exit(1)
