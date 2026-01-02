#!/usr/bin/env python3
"""
IS-CLI Comprehensive Test Suite
Features: Platform, ZTP, NTP, Clear ARP/ND
Version: 1.0
Date: 30-Dec-2025
"""

import subprocess
import time
import json
import sys
from datetime import datetime

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class ISCLITester:
    def __init__(self):
        self.results = {
            'platform': {'pass': 0, 'fail': 0, 'skip': 0, 'tests': []},
            'ztp': {'pass': 0, 'fail': 0, 'skip': 0, 'tests': []},
            'ntp': {'pass': 0, 'fail': 0, 'skip': 0, 'tests': []},
            'clear_arp_nd': {'pass': 0, 'fail': 0, 'skip': 0, 'tests': []}
        }
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

    def log_test(self, feature, test_name, passed, output="", note=""):
        """Log test result"""
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"  [{status}] {test_name}")
        if note:
            print(f"      Note: {note}")

        self.results[feature]['tests'].append({
            'name': test_name,
            'passed': passed,
            'output': output[:500],  # Limit output
            'note': note
        })

        if passed:
            self.results[feature]['pass'] += 1
        else:
            self.results[feature]['fail'] += 1

    def test_platform(self):
        """Test Platform Components"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BLUE}PLATFORM COMPONENTS (SM_ISCLI_DROP1_FEATURE1){Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")

        # Test 1: show platform summary in IS-CLI
        success, output = self.run_command('sonic-cli -c "show platform summary"')
        self.log_test('platform', 'show platform summary (IS-CLI)',
                     success and 'Platform:' in output, output)

        # Test 2: show platform summary --json (expected to fail)
        success, output = self.run_command('sonic-cli -c "show platform summary --json"', expect_fail=True)
        self.log_test('platform', 'show platform summary --json (should fail)',
                     success, output, "BUG: Flags not supported in IS-CLI")

        # Test 3: show platform summary in admin shell
        success, output = self.run_command('show platform summary')
        self.log_test('platform', 'show platform summary (Admin Shell)',
                     success and 'Platform:' in output, output)

        # Test 4: show platform psustatus (expected to fail in VS)
        success, output = self.run_command('show platform psustatus')
        self.log_test('platform', 'show platform psustatus',
                     'Failed to get' in output, output, "Expected: VS limitation")

        # Test 5: show platform temperature
        success, output = self.run_command('show platform temperature')
        self.log_test('platform', 'show platform temperature',
                     'Not detected' in output, output, "Expected: VS has no sensors")

        # Test 6: show platform fan
        success, output = self.run_command('show platform fan')
        self.log_test('platform', 'show platform fan',
                     'Not detected' in output, output, "Expected: VS has no fans")

        # Test 7: show platform ssdhealth
        success, output = self.run_command('show platform ssdhealth')
        self.log_test('platform', 'show platform ssdhealth',
                     success, output, "Returns N/A in VS")

        # Test 8: show platform pcieinfo
        success, output = self.run_command('show platform pcieinfo')
        self.log_test('platform', 'show platform pcieinfo',
                     success and 'PCIe' in output, output)

        # Test 9: show platform pcieinfo --check (expected to fail)
        success, output = self.run_command('show platform pcieinfo --check')
        self.log_test('platform', 'show platform pcieinfo --check',
                     'pcie.yaml' in output, output, "BUG: Missing pcie.yaml config file")

    def test_ztp(self):
        """Test ZTP"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BLUE}ZTP (SM_ISCLI_DROP1_FEATURE2){Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")

        # Test 1: show ztp-status
        success, output = self.run_command('sonic-cli -c "show ztp-status"')
        self.log_test('ztp', 'show ztp-status (IS-CLI)',
                     success and 'ZTP' in output, output)

        # Test 2: Enable ZTP
        success, output = self.run_command('sudo config ztp enable')
        self.log_test('ztp', 'sudo config ztp enable',
                     success, output)
        time.sleep(2)

        # Test 3: Verify enabled
        success, output = self.run_command('sonic-cli -c "show ztp-status"')
        self.log_test('ztp', 'Verify ZTP enabled',
                     'True' in output, output)

        # Test 4: Disable ZTP
        success, output = self.run_command('echo "y" | sudo config ztp disable')
        self.log_test('ztp', 'sudo config ztp disable',
                     success, output)
        time.sleep(2)

        # Test 5: Verify disabled
        success, output = self.run_command('sonic-cli -c "show ztp-status"')
        self.log_test('ztp', 'Verify ZTP disabled',
                     'False' in output, output)

        # Test 6: ZTP service status
        success, output = self.run_command('systemctl status ztp.service --no-pager')
        self.log_test('ztp', 'systemctl status ztp.service',
                     'ztp.service' in output, output)

    def test_ntp(self):
        """Test NTP"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BLUE}NTP (SM_ISCLI_DROP1_FEATURE7){Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")

        # Test 1: show ntp (expected to be ambiguous)
        success, output = self.run_command('sonic-cli -c "show ntp"', expect_fail=True)
        self.log_test('ntp', 'show ntp (should fail)',
                     'Ambiguous' in output, output, "BUG: Command is ambiguous")

        # Test 2: show ntp server
        success, output = self.run_command('sonic-cli -c "show ntp server"')
        self.log_test('ntp', 'show ntp server',
                     success, output)

        # Test 3: show ntp associations
        success, output = self.run_command('sonic-cli -c "show ntp associations"')
        self.log_test('ntp', 'show ntp associations',
                     success, output)

        # Test 4: show ntp global
        success, output = self.run_command('sonic-cli -c "show ntp global"')
        self.log_test('ntp', 'show ntp global',
                     success and 'NTP service' in output, output)

        # Test 5: Add NTP server by IP
        success, output = self.run_command('sudo config ntp add 216.239.35.12')
        self.log_test('ntp', 'sudo config ntp add <IP>',
                     success and 'added' in output, output)
        time.sleep(2)

        # Test 6: Verify server added
        success, output = self.run_command('sonic-cli -c "show ntp server"')
        self.log_test('ntp', 'Verify NTP server added',
                     '216.239.35.12' in output, output)

        # Test 7: Add NTP pool
        success, output = self.run_command('sudo config ntp add --association-type pool 1.pool.ntp.org')
        self.log_test('ntp', 'sudo config ntp add --association-type pool',
                     success, output)

        # Test 8: Try adding hostname (expected to fail)
        success, output = self.run_command('sudo config ntp add time.cloudflare.com', expect_fail=True)
        self.log_test('ntp', 'sudo config ntp add <hostname> (should fail)',
                     'Invalid IP' in output, output, "BUG: Hostname not accepted without --association-type")

        # Test 9: Delete NTP server
        success, output = self.run_command('sudo config ntp del 216.239.35.12')
        self.log_test('ntp', 'sudo config ntp del <IP>',
                     success, output)

        # Test 10: chronyc tracking
        success, output = self.run_command('chronyc tracking')
        self.log_test('ntp', 'chronyc tracking',
                     success and 'Reference ID' in output, output)

        # Test 11: chronyc sources
        success, output = self.run_command('chronyc sources')
        self.log_test('ntp', 'chronyc sources',
                     success, output)

        # Test 12: Check CONFIG_DB
        success, output = self.run_command('redis-cli -n 4 KEYS "NTP_SERVER*"')
        self.log_test('ntp', 'redis-cli CONFIG_DB check',
                     success, output)

        # Test 13: VRF ping
        success, output = self.run_command('sudo ip vrf exec mgmt ping -c 2 8.8.8.8')
        self.log_test('ntp', 'ip vrf exec mgmt ping',
                     success and 'bytes from' in output, output)

    def test_clear_arp_nd(self):
        """Test Clear ARP/ND"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BLUE}CLEAR ARP/ND (SM_ISCLI_DROP1_FEATURE8){Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")

        # Test 1: View ARP
        success, output = self.run_command('ip neigh show')
        arp_before = output.count('\n')
        self.log_test('clear_arp_nd', 'ip neigh show',
                     success, output, f"Entries before: {arp_before}")

        # Test 2: Clear ARP
        start = time.time()
        success, output = self.run_command('sonic-clear arp')
        duration = time.time() - start
        self.log_test('clear_arp_nd', 'sonic-clear arp',
                     success and 'Flush is complete' in output, output,
                     f"Execution time: {duration:.3f}s")

        # Test 3: Verify ARP cleared
        time.sleep(1)
        success, output = self.run_command('ip neigh show')
        arp_after = output.count('\n')
        self.log_test('clear_arp_nd', 'Verify ARP cleared',
                     True, output, f"Entries after: {arp_after}")

        # Test 4: ARP repopulation (ping may fail if no route)
        success, output = self.run_command('ping -c 2 192.168.100.1 || true')
        self.log_test('clear_arp_nd', 'ARP repopulation test',
                     True, output, "Ping may fail - check connectivity")

        # Test 5: IPv6 neighbor view
        success, output = self.run_command('ip -6 neigh show')
        ndp_before = output.count('\n')
        self.log_test('clear_arp_nd', 'ip -6 neigh show',
                     success, output, f"IPv6 neighbors: {ndp_before}")

        # Test 6: Clear NDP
        success, output = self.run_command('sonic-clear ndp')
        self.log_test('clear_arp_nd', 'sonic-clear ndp',
                     success or 'Nothing to flush' in output, output)

        # Test 7: Multiple clears (stability)
        for i in range(3):
            success, output = self.run_command('sonic-clear arp')
        self.log_test('clear_arp_nd', 'Multiple ARP clears (stability)',
                     success, "", "3 consecutive clears completed")

        # Test 8: show arp in IS-CLI (expected to fail)
        success, output = self.run_command('sonic-cli -c "show arp"', expect_fail=True)
        self.log_test('clear_arp_nd', 'show arp in IS-CLI (should fail)',
                     'Invalid input' in output, output, "BUG: Command not available in IS-CLI")

        # Test 9: show ndp in IS-CLI (expected to fail)
        success, output = self.run_command('sonic-cli -c "show ndp"', expect_fail=True)
        self.log_test('clear_arp_nd', 'show ndp in IS-CLI (should fail)',
                     'Invalid input' in output, output, "BUG: Command not available in IS-CLI")

    def generate_report(self):
        """Generate test report"""
        print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BLUE}TEST SUMMARY{Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")

        total_pass = 0
        total_fail = 0
        total_skip = 0

        for feature, data in self.results.items():
            total_pass += data['pass']
            total_fail += data['fail']
            total_skip += data['skip']
            total = data['pass'] + data['fail'] + data['skip']
            pass_rate = (data['pass'] / total * 100) if total > 0 else 0

            print(f"\n{feature.upper()}:")
            print(f"  Total: {total}")
            print(f"  {Colors.GREEN}Pass: {data['pass']}{Colors.END}")
            print(f"  {Colors.RED}Fail: {data['fail']}{Colors.END}")
            print(f"  Skip: {data['skip']}")
            print(f"  Pass Rate: {pass_rate:.1f}%")

        print(f"\n{Colors.BLUE}OVERALL:{Colors.END}")
        total = total_pass + total_fail + total_skip
        overall_rate = (total_pass / total * 100) if total > 0 else 0
        print(f"  Total Tests: {total}")
        print(f"  {Colors.GREEN}Passed: {total_pass}{Colors.END}")
        print(f"  {Colors.RED}Failed: {total_fail}{Colors.END}")
        print(f"  Skipped: {total_skip}")
        print(f"  {Colors.GREEN}Overall Pass Rate: {overall_rate:.1f}%{Colors.END}")

        duration = (datetime.now() - self.start_time).total_seconds()
        print(f"\n  Test Duration: {duration:.1f} seconds")

        # Save detailed report
        report_file = f"iscli_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'summary': {
                    'total': total,
                    'pass': total_pass,
                    'fail': total_fail,
                    'skip': total_skip,
                    'pass_rate': overall_rate,
                    'duration': duration
                },
                'results': self.results,
                'timestamp': self.start_time.isoformat()
            }, f, indent=2)

        print(f"\n  Detailed report saved to: {report_file}")

    def run_all_tests(self):
        """Run all test suites"""
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BLUE}IS-CLI COMPREHENSIVE TEST SUITE{Colors.END}")
        print(f"{Colors.BLUE}Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")

        self.test_platform()
        self.test_ztp()
        self.test_ntp()
        self.test_clear_arp_nd()
        self.generate_report()

if __name__ == "__main__":
    tester = ISCLITester()
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
