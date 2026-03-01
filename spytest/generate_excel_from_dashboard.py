#!/usr/bin/env python3
"""
Generate Excel from batch_full_run.sh with Dashboard Results

Combines:
1. Test inventory from batch_full_run.sh
2. Latest test results from dashboard HTML
3. Generates comprehensive Excel report

Usage:
    python3 generate_excel_from_dashboard.py
    python3 generate_excel_from_dashboard.py --dashboard /path/to/dashboard.html
"""

import re
import sys
from pathlib import Path

# Add parent directory to import the original generator
sys.path.insert(0, str(Path(__file__).parent))

from generate_test_inventory_excel import (
    BatchFileParser, TestScriptAnalyzer, ExcelGenerator
)

import argparse


class DashboardParser:
    """Parses HTML dashboard to extract test results"""

    def __init__(self, dashboard_file: Path):
        self.dashboard_file = dashboard_file
        self.results = {}

        if dashboard_file and dashboard_file.exists():
            self.parse()

    def parse(self):
        """Parse dashboard HTML for test results"""
        print(f"Parsing dashboard: {self.dashboard_file}")

        with open(self.dashboard_file, 'r') as f:
            content = f.read()

        # Try historical dashboard format first (Test Details table)
        if self._parse_historical_dashboard(content):
            return

        # Fall back to consolidated dashboard format
        self._parse_consolidated_dashboard(content)

    def _parse_historical_dashboard(self, content: str) -> bool:
        """
        Parse historical dashboard with test details table

        Format:
        <tr>
            <td class="test-name">TestClass.test_function</td>
            <td class="module-name">path/to/test.py</td>
            <td><span class="status-*">...</span></td>  (date columns)
            ...
            <td>Total Runs</td>
            <td>Pass Count</td>
            <td>Fail Count</td>
            <td>Pass Rate %</td>
        </tr>
        """
        # Pattern to match test detail rows
        # Extract: test name, module path, pass count, fail count
        pattern = r'<td class="test-name"[^>]*>([^<]+)</td>\s*' \
                  r'<td class="module-name"[^>]*>([^<]+)</td>\s*' \
                  r'.*?' \
                  r'<td>(\d+)</td>\s*' \
                  r'<td>(\d+)</td>\s*' \
                  r'<td>(\d+)</td>'

        matches = re.findall(pattern, content, re.DOTALL)

        if not matches:
            print("  Historical dashboard format not detected")
            return False

        print(f"  Detected historical dashboard format")
        print(f"  Found {len(matches)} test entries")

        # Group by script
        for test_name, module_path, total_runs, pass_count, fail_count in matches:
            script_name = Path(module_path).name

            if script_name not in self.results:
                self.results[script_name] = {
                    'total': 0,
                    'passed': 0,
                    'failed': 0,
                    'skipped': 0,
                    'tests': {}
                }

            pass_count = int(pass_count)
            fail_count = int(fail_count)
            total_runs = int(total_runs)

            # Count test functions
            self.results[script_name]['total'] += 1

            # Count test functions that have passes (regardless of how many runs)
            if pass_count > 0 and fail_count == 0:
                self.results[script_name]['passed'] += 1
            # Count test functions that have failures
            elif fail_count > 0:
                self.results[script_name]['failed'] += 1
            # If no runs, count as skipped
            elif total_runs == 0:
                self.results[script_name]['skipped'] += 1

            self.results[script_name]['tests'][test_name] = f"{pass_count}P/{fail_count}F ({total_runs} runs)"

        print(f"  Found results for {len(self.results)} test scripts")
        return True

    def _parse_consolidated_dashboard(self, content: str):
        """
        Parse consolidated dashboard format

        Format:
        <td class="testcase-id">path/to/test.py::TestClass.test_function</td>
        <td>...</td>
        <td class="result-cell status">RESULT</td>
        """
        pattern = r'<td class="testcase-id">([^<]+)</td>\s*<td[^>]*>[^<]*</td>\s*<td class="result-cell\s+(\w+)">([^<]+)</td>'

        matches = re.findall(pattern, content, re.DOTALL)

        if not matches:
            print("  Consolidated dashboard format not detected")
            return

        print(f"  Detected consolidated dashboard format")
        print(f"  Found {len(matches)} test entries")

        # Group by script
        for test_path, status_class, status_text in matches:
            if '::' in test_path:
                script_path, test_func = test_path.split('::', 1)
                script_name = Path(script_path).name

                if script_name not in self.results:
                    self.results[script_name] = {
                        'total': 0,
                        'passed': 0,
                        'failed': 0,
                        'skipped': 0,
                        'tests': {}
                    }

                self.results[script_name]['total'] += 1
                self.results[script_name]['tests'][test_func] = status_text

                if status_text == 'PASSED':
                    self.results[script_name]['passed'] += 1
                elif status_text == 'FAILED':
                    self.results[script_name]['failed'] += 1
                elif status_text in ('SKIP', 'SKIPPED', 'NE', 'NA'):
                    self.results[script_name]['skipped'] += 1

        print(f"  Found results for {len(self.results)} test scripts")


def main():
    parser = argparse.ArgumentParser(description="Generate Excel from batch + dashboard")
    parser.add_argument('--batch-file', default='./batch_full_run.sh')
    parser.add_argument('--dashboard', default='/home/hp_test/Athira/consolidated_dashboard_Feb_26.html')
    parser.add_argument('--tests-dir', default='./tests')
    parser.add_argument('--output', default='test_inventory_with_results.xlsx')

    args = parser.parse_args()

    batch_file = Path(args.batch_file)
    dashboard_file = Path(args.dashboard) if args.dashboard else None
    tests_dir = Path(args.tests_dir)

    print("=" * 70)
    print(" Excel Generator with Dashboard Results")
    print("=" * 70)
    print(f"Batch file : {batch_file}")
    print(f"Dashboard  : {dashboard_file}")
    print(f"Tests dir  : {tests_dir}")
    print(f"Output     : {args.output}")
    print("=" * 70)

    # Parse batch file
    print("\n[1/4] Parsing batch_full_run.sh...")
    batch_parser = BatchFileParser(batch_file)
    print(f"      Found {len(batch_parser.batches)} batches")

    # Parse dashboard
    print("\n[2/4] Parsing dashboard...")
    dashboard_parser = DashboardParser(dashboard_file)

    # Analyze scripts and build Excel
    print("\n[3/4] Analyzing test scripts...")
    excel = ExcelGenerator(Path(args.output))
    excel.write_headers()

    row_num = 2
    batch_summary = {}

    for batch_name, batch_info in sorted(batch_parser.batches.items()):
        if batch_name not in batch_summary:
            batch_summary[batch_name] = {
                'scripts': 0,
                'total': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 0
            }

        for test_file in batch_info['tests']:
            test_file = test_file.strip()
            script_name = Path(test_file).name
            script_path = tests_dir / test_file

            # Analyze script
            analyzer = TestScriptAnalyzer(script_path)
            cli_type = analyzer.get_cli_type()
            feature = analyzer.get_feature_from_docstring()

            if not feature:
                parts = test_file.split('/')
                if len(parts) > 1:
                    feature = parts[0].upper()
                else:
                    feature = "Unknown"

            # Get static count
            total_tests = analyzer.count_test_functions()

            # Get results from dashboard
            passed = 0
            failed = 0
            skipped = 0

            if script_name in dashboard_parser.results:
                dashboard_data = dashboard_parser.results[script_name]
                total_tests = dashboard_data['total']  # Use actual count
                passed = dashboard_data['passed']
                failed = dashboard_data['failed']
                skipped = dashboard_data['skipped']

            # Calculate pass rate
            pass_rate = ""
            if total_tests > 0 and (passed + failed) > 0:
                pass_rate = f"{(passed / (passed + failed)) * 100:.1f}%"

            # Update batch summary
            batch_summary[batch_name]['scripts'] += 1
            batch_summary[batch_name]['total'] += total_tests
            batch_summary[batch_name]['passed'] += passed
            batch_summary[batch_name]['failed'] += failed
            batch_summary[batch_name]['skipped'] += skipped

            # Add row
            row_data = {
                'batch': batch_name,
                'script_name': script_name,
                'script_location': test_file,
                'feature': feature,
                'cli_type': cli_type,
                'total': total_tests,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'pass_rate': pass_rate,
                'defect_id': '',
                'notes': ''
            }

            excel.add_test_row(row_num, row_data)
            row_num += 1

    print(f"\n[4/4] Generating Excel...")
    excel.add_summary_sheet(batch_summary)
    excel.adjust_column_widths()
    excel.save()

    print("\n" + "=" * 70)
    print(" Summary")
    print("=" * 70)
    print(f"Total Batches : {len(batch_parser.batches)}")
    print(f"Total Scripts : {row_num - 2}")
    print(f"Scripts with Results: {len(dashboard_parser.results)}")
    print(f"Output File   : {args.output}")
    print("=" * 70)

    # Batch summary
    print("\nBatch Summary:")
    print("-" * 80)
    print(f"{'Batch':<30} {'Scripts':>8} {'Tests':>8} {'Passed':>8} {'Failed':>8}")
    print("-" * 80)
    total_scripts = 0
    total_tests = 0
    total_passed = 0
    total_failed = 0
    for batch, stats in sorted(batch_summary.items()):
        print(f"{batch:<30} {stats['scripts']:>8} {stats['total']:>8} "
              f"{stats['passed']:>8} {stats['failed']:>8}")
        total_scripts += stats['scripts']
        total_tests += stats['total']
        total_passed += stats['passed']
        total_failed += stats['failed']
    print("-" * 80)
    print(f"{'TOTAL':<30} {total_scripts:>8} {total_tests:>8} "
          f"{total_passed:>8} {total_failed:>8}")
    print("-" * 80)

    if total_tests > 0:
        overall_pass_rate = (total_passed / total_tests) * 100
        print(f"\nOverall Pass Rate: {overall_pass_rate:.1f}%")

    print("\nDone!")


if __name__ == '__main__':
    main()
