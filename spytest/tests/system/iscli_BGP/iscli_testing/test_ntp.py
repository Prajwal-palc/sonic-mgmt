#!/usr/bin/env python3
"""
IS-CLI NTP Test Script
Feature: SM_ISCLI_DROP1_FEATURE7
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

class NTPTester:
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

    def test_show_ntp_ambiguous(self):
        """Test: show ntp (should be ambiguous)"""
        print(f"\n{Colors.BLUE}Test 1: show ntp (expect ambiguous error){Colors.END}")
        success, output = self.run_command('sonic-cli -c "show ntp"', expect_fail=True)
        self.log_test(
            'show ntp (should fail)',
            'Ambiguous' in output,
            output,
            "BUG: Command is ambiguous"
        )

    def test_show_ntp_server(self):
        """Test: show ntp server"""
        print(f"\n{Colors.BLUE}Test 2: show ntp server{Colors.END}")
        success, output = self.run_command('sonic-cli -c "show ntp server"')
        self.log_test(
            'show ntp server',
            success,
            output,
            "Should display NTP server configuration"
        )

    def test_show_ntp_associations(self):
        """Test: show ntp associations"""
        print(f"\n{Colors.BLUE}Test 3: show ntp associations{Colors.END}")
        success, output = self.run_command('sonic-cli -c "show ntp associations"')
        self.log_test(
            'show ntp associations',
            success,
            output,
            "Should display NTP associations"
        )

    def test_show_ntp_global(self):
        """Test: show ntp global"""
        print(f"\n{Colors.BLUE}Test 4: show ntp global{Colors.END}")
        success, output = self.run_command('sonic-cli -c "show ntp global"')
        self.log_test(
            'show ntp global',
            success and 'NTP service' in output,
            output,
            "Should display NTP global configuration"
        )

    def test_ntp_add_by_ip(self):
        """Test: Add NTP server by IP"""
        print(f"\n{Colors.BLUE}Test 5: sudo config ntp add <IP>{Colors.END}")
        success, output = self.run_command('sudo config ntp add 216.239.35.12')
        self.log_test(
            'sudo config ntp add <IP>',
            success and 'added' in output,
            output,
            "Should add NTP server by IP address"
        )
        time.sleep(2)

    def test_verify_ntp_server_added(self):
        """Test: Verify NTP server added"""
        print(f"\n{Colors.BLUE}Test 6: Verify NTP server added{Colors.END}")
        success, output = self.run_command('sonic-cli -c "show ntp server"')
        self.log_test(
            'Verify NTP server added',
            '216.239.35.12' in output,
            output,
            "Should show newly added NTP server"
        )

    def test_ntp_add_pool(self):
        """Test: Add NTP pool"""
        print(f"\n{Colors.BLUE}Test 7: sudo config ntp add --association-type pool{Colors.END}")
        success, output = self.run_command('sudo config ntp add --association-type pool 1.pool.ntp.org')
        self.log_test(
            'sudo config ntp add --association-type pool',
            success,
            output,
            "Should add NTP pool with association type"
        )

    def test_ntp_add_hostname_fail(self):
        """Test: Add NTP by hostname without flag (should fail)"""
        print(f"\n{Colors.BLUE}Test 8: sudo config ntp add <hostname> (expect failure){Colors.END}")
        success, output = self.run_command('sudo config ntp add time.cloudflare.com', expect_fail=True)
        self.log_test(
            'sudo config ntp add <hostname> (should fail)',
            'Invalid IP' in output,
            output,
            "BUG: Hostname not accepted without --association-type"
        )

    def test_ntp_delete(self):
        """Test: Delete NTP server"""
        print(f"\n{Colors.BLUE}Test 9: sudo config ntp del <IP>{Colors.END}")
        success, output = self.run_command('sudo config ntp del 216.239.35.12')
        self.log_test(
            'sudo config ntp del <IP>',
            success,
            output,
            "Should delete NTP server"
        )

    def test_chronyc_tracking(self):
        """Test: chronyc tracking"""
        print(f"\n{Colors.BLUE}Test 10: chronyc tracking{Colors.END}")
        success, output = self.run_command('chronyc tracking')
        self.log_test(
            'chronyc tracking',
            success and 'Reference ID' in output,
            output,
            "Should show chrony tracking information"
        )

    def test_chronyc_sources(self):
        """Test: chronyc sources"""
        print(f"\n{Colors.BLUE}Test 11: chronyc sources{Colors.END}")
        success, output = self.run_command('chronyc sources')
        self.log_test(
            'chronyc sources',
            success,
            output,
            "Should show chrony NTP sources"
        )

    def test_config_db_check(self):
        """Test: Check CONFIG_DB for NTP entries"""
        print(f"\n{Colors.BLUE}Test 12: redis-cli CONFIG_DB check{Colors.END}")
        success, output = self.run_command('redis-cli -n 4 KEYS "NTP_SERVER*"')
        self.log_test(
            'redis-cli CONFIG_DB check',
            success,
            output,
            "Should query NTP server entries in CONFIG_DB"
        )

    def test_vrf_ping(self):
        """Test: VRF ping"""
        print(f"\n{Colors.BLUE}Test 13: ip vrf exec mgmt ping{Colors.END}")
        success, output = self.run_command('sudo ip vrf exec mgmt ping -c 2 8.8.8.8')
        self.log_test(
            'ip vrf exec mgmt ping',
            success and 'bytes from' in output,
            output,
            "Should ping via mgmt VRF"
        )

    def generate_report(self):
        """Generate test report"""
        print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
        print(f"{Colors.BLUE}NTP TEST SUMMARY{Colors.END}")
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
        report_file = f"ntp_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'feature': 'SM_ISCLI_DROP1_FEATURE7_NTP',
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

        # Print bugs found
        print(f"\n{Colors.YELLOW}BUGS FOUND:{Colors.END}")
        print(f"  1. 'show ntp' command is ambiguous")
        print(f"  2. NTP hostname validation inconsistency")
        print(f"\n  See JIRA_BUGS_TEMPLATE.md for details")

    def run_all_tests(self):
        """Run all NTP tests"""
        print(f"{Colors.BLUE}{'='*70}{Colors.END}")
        print(f"{Colors.BLUE}IS-CLI NTP TEST SUITE{Colors.END}")
        print(f"{Colors.BLUE}Feature: SM_ISCLI_DROP1_FEATURE7{Colors.END}")
        print(f"{Colors.BLUE}Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{Colors.BLUE}{'='*70}{Colors.END}")

        self.test_show_ntp_ambiguous()
        self.test_show_ntp_server()
        self.test_show_ntp_associations()
        self.test_show_ntp_global()
        self.test_ntp_add_by_ip()
        self.test_verify_ntp_server_added()
        self.test_ntp_add_pool()
        self.test_ntp_add_hostname_fail()
        self.test_ntp_delete()
        self.test_chronyc_tracking()
        self.test_chronyc_sources()
        self.test_config_db_check()
        self.test_vrf_ping()

        self.generate_report()

if __name__ == "__main__":
    tester = NTPTester()
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
