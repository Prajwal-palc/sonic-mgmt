#!/usr/bin/env python3
"""
Generate Graphical Dashboard from SPyTest Log Directory

This script scans a log directory root (e.g., logs/SM_ISCLI_20260204) and generates
a comprehensive HTML dashboard with graphical visualizations including:
- Tabbed interface for different test modules
- Progress bars showing pass/fail/skip percentages
- Summary statistics with color coding
- Detailed test case listings

Usage:
    python3 generate_graphical_dashboard.py --log-root logs/SM_ISCLI_20260204 --out dashboard.html
"""

import os
import sys
import glob
import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# HTML Template with CSS for graphical dashboard
HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SONiC Test Dashboard - {batch_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
            font-weight: 600;
        }}

        .header p {{
            font-size: 14px;
            opacity: 0.95;
        }}

        .summary-section {{
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}

        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            text-align: center;
        }}

        .summary-card h3 {{
            font-size: 14px;
            color: #6c757d;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .summary-card .value {{
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .summary-card .percentage {{
            font-size: 14px;
            color: #6c757d;
        }}

        .value.total {{ color: #667eea; }}
        .value.passed {{ color: #28a745; }}
        .value.failed {{ color: #dc3545; }}
        .value.skipped {{ color: #ffc107; }}
        .value.runtime {{ color: #17a2b8; }}

        .overall-progress {{
            margin-top: 20px;
        }}

        .overall-progress h3 {{
            font-size: 16px;
            color: #495057;
            margin-bottom: 10px;
        }}

        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            display: flex;
        }}

        .progress-segment {{
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
            color: white;
            transition: all 0.3s ease;
        }}

        .progress-pass {{ background-color: #28a745; }}
        .progress-fail {{ background-color: #dc3545; }}
        .progress-skip {{ background-color: #ffc107; }}

        .tabs {{
            display: flex;
            flex-wrap: wrap;
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
            padding: 0 20px;
            overflow-x: auto;
        }}

        .tab-button {{
            background: none;
            border: none;
            padding: 15px 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            color: #6c757d;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
            white-space: nowrap;
        }}

        .tab-button:hover {{
            color: #667eea;
            background: rgba(102, 126, 234, 0.05);
        }}

        .tab-button.active {{
            color: #667eea;
            border-bottom-color: #667eea;
            background: white;
        }}

        .tab-content {{
            display: none;
            padding: 30px;
            animation: fadeIn 0.3s ease;
        }}

        .tab-content.active {{
            display: block;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        .module-summary {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            margin-bottom: 20px;
        }}

        .module-summary h2 {{
            color: #667eea;
            font-size: 20px;
            margin-bottom: 15px;
        }}

        .module-stats {{
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 15px;
            font-size: 13px;
        }}

        .module-stats span {{
            display: inline-block;
        }}

        .module-stats strong {{
            font-size: 16px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            overflow: hidden;
            margin-top: 20px;
        }}

        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}

        th {{
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 10px 12px;
            border-bottom: 1px solid #e9ecef;
            font-size: 12px;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover {{
            background: #f8f9fa;
        }}

        .testcase-id {{
            font-family: 'Courier New', monospace;
            font-size: 11px;
            color: #495057;
            word-break: break-all;
        }}

        .module-name {{
            font-weight: 600;
            color: #495057;
            font-size: 13px;
        }}

        .result-cell {{
            font-weight: bold;
            text-align: center;
            padding: 6px 10px;
            border-radius: 4px;
        }}

        .result-cell.passed {{
            background: #d4edda;
            color: #155724;
        }}

        .result-cell.failed {{
            background: #f8d7da;
            color: #721c24;
        }}

        .result-cell.skipped {{
            background: #fff3cd;
            color: #856404;
        }}

        .footer {{
            padding: 20px;
            text-align: center;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 12px;
            border-top: 1px solid #e9ecef;
        }}

        .no-data {{
            text-align: center;
            padding: 40px;
            color: #6c757d;
            font-size: 14px;
        }}
    </style>
</head>
<body>
"""

HTML_TAIL = """
    <script>
        function openTab(evt, tabName) {{
            // Hide all tab contents
            var tabContents = document.getElementsByClassName("tab-content");
            for (var i = 0; i < tabContents.length; i++) {{
                tabContents[i].classList.remove("active");
            }}

            // Remove active class from all buttons
            var tabButtons = document.getElementsByClassName("tab-button");
            for (var i = 0; i < tabButtons.length; i++) {{
                tabButtons[i].classList.remove("active");
            }}

            // Show the current tab and mark button as active
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }}

        // Open first tab by default
        window.onload = function() {{
            var firstTab = document.querySelector('.tab-button');
            if (firstTab) {{
                firstTab.click();
            }}
        }};
    </script>
</body>
</html>
"""


def parse_time_to_seconds(time_str):
    """
    Convert 'H:MM:SS' or 'M:SS' format to total seconds
    Examples: '0:00:17' -> 17, '1:23:45' -> 5025, '5:30' -> 330
    """
    if not time_str or time_str.strip() == '':
        return 0

    try:
        parts = time_str.strip().split(':')
        if len(parts) == 3:  # H:MM:SS format
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:  # M:SS format
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        else:
            return 0
    except (ValueError, IndexError):
        return 0


def format_seconds_to_readable(total_seconds):
    """
    Convert total seconds to human-readable format
    Examples: 17 -> '17s', 330 -> '5m 30s', 5025 -> '1h 23m 45s'
    """
    if total_seconds == 0:
        return '0s'

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    parts = []
    if hours > 0:
        parts.append(f'{hours}h')
    if minutes > 0:
        parts.append(f'{minutes}m')
    if seconds > 0:
        parts.append(f'{seconds}s')

    return ' '.join(parts)


def parse_csv_results(csv_file):
    """Parse SPyTest CSV stats file to extract test results"""
    total = 0
    passed = 0
    failed = 0
    skipped = 0
    test_cases = []

    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                result = row.get('Result', '').strip()
                # Skip module configuration rows (empty result)
                if not result:
                    continue

                # Extract test case details
                test_case = {
                    'module': row.get('Module', '').strip(),
                    'function': row.get('Function', '').strip(),
                    'result': result,
                    'test_time': row.get('Test Time', '').strip(),
                    'description': row.get('Description', '').strip()
                }
                test_cases.append(test_case)

                total += 1
                if result == 'Pass' or result == 'PASSED':
                    passed += 1
                elif result in ['Fail', 'Failed', 'FAILED', 'SCRIPTERROR']:
                    failed += 1
                elif result in ['Skip', 'Skipped', 'SKIPPED']:
                    skipped += 1
    except Exception as e:
        print(f"Warning: Failed to parse {csv_file}: {e}", file=sys.stderr)
        return 0, 0, 0, 0, []

    return total, passed, failed, skipped, test_cases


def find_test_results(log_root):
    """
    Scan log root directory for test results.
    Expected structure: log_root/<date>/<feature>/<time>/results_*_stats.csv
    """
    results = defaultdict(list)

    log_path = Path(log_root)
    if not log_path.exists():
        print(f"Error: Log root directory does not exist: {log_root}", file=sys.stderr)
        return results

    # Find all CSV result files
    csv_pattern = str(log_path / "**" / "results_*_stats.csv")
    csv_files = glob.glob(csv_pattern, recursive=True)

    print(f"Found {len(csv_files)} CSV result files in {log_root}")

    for csv_file in csv_files:
        # Parse the directory structure to extract feature name
        csv_path = Path(csv_file)
        parts = csv_path.parts

        # Try to determine feature name from directory structure
        # Expected: .../logs/<batch>/<date>/<feature>/<time>/results_*_stats.csv
        try:
            if len(parts) >= 3:
                feature = parts[-3]  # Feature directory name
                date = parts[-4] if len(parts) >= 4 else "unknown"
            else:
                feature = "unknown"
                date = "unknown"
        except:
            feature = "unknown"
            date = "unknown"

        total, passed, failed, skipped, test_cases = parse_csv_results(csv_file)

        if total > 0:
            results[feature].append({
                'date': date,
                'feature': feature,
                'total': total,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'test_cases': test_cases,
                'csv_file': csv_file
            })

    return results


def generate_dashboard_html(results, batch_name, output_file):
    """Generate HTML dashboard from collected results"""

    # Calculate overall statistics
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_runtime_seconds = 0

    for feature, runs in results.items():
        for run in runs:
            total_tests += run['total']
            total_passed += run['passed']
            total_failed += run['failed']
            total_skipped += run['skipped']

            # Calculate runtime for all test cases in this run
            for test_case in run['test_cases']:
                test_time_str = test_case.get('test_time', '')
                total_runtime_seconds += parse_time_to_seconds(test_time_str)

    # Calculate percentages
    pass_pct = (total_passed / total_tests * 100) if total_tests > 0 else 0
    fail_pct = (total_failed / total_tests * 100) if total_tests > 0 else 0
    skip_pct = (total_skipped / total_tests * 100) if total_tests > 0 else 0

    # Format total runtime
    total_runtime_readable = format_seconds_to_readable(total_runtime_seconds)

    html = HTML_HEAD.format(batch_name=batch_name)

    # Header
    html += f"""
    <div class="container">
        <div class="header">
            <h1>SONiC Test Dashboard</h1>
            <p>{batch_name} - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
"""

    # Summary Section
    html += """
        <div class="summary-section">
            <div class="summary-grid">
"""

    html += f"""
                <div class="summary-card">
                    <h3>Total Tests</h3>
                    <div class="value total">{total_tests}</div>
                    <div class="percentage">100%</div>
                </div>
                <div class="summary-card">
                    <h3>Passed</h3>
                    <div class="value passed">{total_passed}</div>
                    <div class="percentage">{pass_pct:.1f}%</div>
                </div>
                <div class="summary-card">
                    <h3>Failed</h3>
                    <div class="value failed">{total_failed}</div>
                    <div class="percentage">{fail_pct:.1f}%</div>
                </div>
                <div class="summary-card">
                    <h3>Skipped</h3>
                    <div class="value skipped">{total_skipped}</div>
                    <div class="percentage">{skip_pct:.1f}%</div>
                </div>
                <div class="summary-card">
                    <h3>Total Runtime</h3>
                    <div class="value runtime">{total_runtime_readable}</div>
                    <div class="percentage">Execution Time</div>
                </div>
"""

    html += """
            </div>
            <div class="overall-progress">
                <h3>Overall Progress</h3>
                <div class="progress-bar">
"""

    if pass_pct > 0:
        html += f'                    <div class="progress-segment progress-pass" style="width: {pass_pct:.2f}%;">{pass_pct:.0f}%</div>\n'
    if fail_pct > 0:
        html += f'                    <div class="progress-segment progress-fail" style="width: {fail_pct:.2f}%;">{fail_pct:.0f}%</div>\n'
    if skip_pct > 0:
        html += f'                    <div class="progress-segment progress-skip" style="width: {skip_pct:.2f}%;">{skip_pct:.0f}%</div>\n'

    html += """
                </div>
            </div>
        </div>
"""

    # Tabs Navigation
    html += """
        <div class="tabs">
"""

    for idx, feature in enumerate(sorted(results.keys())):
        safe_id = feature.replace(' ', '_').replace('/', '_')
        html += f'            <button class="tab-button" onclick="openTab(event, \'{safe_id}\')">{feature}</button>\n'

    html += """
        </div>
"""

    # Tab Contents
    for feature in sorted(results.keys()):
        safe_id = feature.replace(' ', '_').replace('/', '_')
        runs = results[feature]

        # Aggregate stats for this feature
        feature_total = sum(r['total'] for r in runs)
        feature_passed = sum(r['passed'] for r in runs)
        feature_failed = sum(r['failed'] for r in runs)
        feature_skipped = sum(r['skipped'] for r in runs)

        feature_pass_pct = (feature_passed / feature_total * 100) if feature_total > 0 else 0
        feature_fail_pct = (feature_failed / feature_total * 100) if feature_total > 0 else 0
        feature_skip_pct = (feature_skipped / feature_total * 100) if feature_total > 0 else 0

        html += f"""
        <div id="{safe_id}" class="tab-content">
            <div class="module-summary">
                <h2>{feature} - Test Results</h2>
                <div class="module-stats">
                    <span>✓ Pass: <strong style="color: #28a745;">{feature_passed}</strong> <span style="font-size: 11px;">({feature_pass_pct:.1f}%)</span></span>
                    <span style="margin: 0 15px;">✗ Fail: <strong style="color: #dc3545;">{feature_failed}</strong> <span style="font-size: 11px;">({feature_fail_pct:.1f}%)</span></span>
                    <span>⊘ Skip: <strong style="color: #ffc107;">{feature_skipped}</strong> <span style="font-size: 11px;">({feature_skip_pct:.1f}%)</span></span>
                    <span style="margin-left: 15px;">Total: <strong>{feature_total}</strong></span>
                </div>
                <div class="progress-bar" style="height: 20px;">
"""

        if feature_pass_pct > 0:
            html += f'                    <div class="progress-segment progress-pass" style="width: {feature_pass_pct:.2f}%; font-size: 10px;">{feature_pass_pct:.0f}%</div>\n'
        if feature_fail_pct > 0:
            html += f'                    <div class="progress-segment progress-fail" style="width: {feature_fail_pct:.2f}%; font-size: 10px;">{feature_fail_pct:.0f}%</div>\n'
        if feature_skip_pct > 0:
            html += f'                    <div class="progress-segment progress-skip" style="width: {feature_skip_pct:.2f}%; font-size: 10px;">{feature_skip_pct:.0f}%</div>\n'

        html += """
                </div>
            </div>
"""

        # Test cases table
        # Collect all test cases from all runs for this feature
        all_test_cases = []
        for run in runs:
            all_test_cases.extend(run['test_cases'])

        if all_test_cases:
            html += """
            <table>
                <thead>
                    <tr>
                        <th style="width: 50px;">S.No</th>
                        <th style="min-width: 250px;">Test Case ID</th>
                        <th style="min-width: 200px;">Description</th>
                        <th style="width: 100px;">Result</th>
                        <th style="width: 100px;">Time</th>
                    </tr>
                </thead>
                <tbody>
"""

            for idx, tc in enumerate(all_test_cases, 1):
                result = tc.get('result', '')
                result_class = 'passed' if result in ['Pass', 'PASSED'] else ('failed' if result in ['Fail', 'Failed', 'FAILED', 'SCRIPTERROR'] else 'skipped')
                test_id = tc.get('function', '')
                description = tc.get('description', test_id)
                test_time = tc.get('test_time', '')

                html += f"""
                    <tr>
                        <td style="text-align: center; font-size: 11px;">{idx}</td>
                        <td class="testcase-id">{test_id}</td>
                        <td style="font-size: 11px; color: #555;">{description}</td>
                        <td class="result-cell {result_class}">{result}</td>
                        <td style="text-align: center; font-size: 11px;">{test_time}</td>
                    </tr>
"""

            html += """
                </tbody>
            </table>
"""
        else:
            html += '<div class="no-data">No test case details available</div>'

        html += """
        </div>
"""

    # Footer
    html += f"""
        <div class="footer">
            Generated by SPyTest Dashboard Generator | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
"""

    html += HTML_TAIL

    # Write to file
    with open(output_file, 'w') as f:
        f.write(html)

    print(f"\nDashboard generated successfully: {output_file}")
    print(f"Total modules: {len(results)}")
    print(f"Total tests: {total_tests}")
    print(f"Pass: {total_passed} ({pass_pct:.1f}%)")
    print(f"Fail: {total_failed} ({fail_pct:.1f}%)")
    print(f"Skip: {total_skipped} ({skip_pct:.1f}%)")
    print(f"Total Runtime: {total_runtime_readable}")


def main():
    parser = argparse.ArgumentParser(
        description='Generate graphical dashboard from SPyTest log directory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 generate_graphical_dashboard.py --log-root logs/SM_ISCLI_20260204 --out dashboard.html
  python3 generate_graphical_dashboard.py --log-root logs/SM_ISCLI_20260204 --out dashboard.html --name "SM_ISCLI Batch"
        """
    )
    parser.add_argument('--log-root', required=True, help='Root directory containing test logs (e.g., logs/SM_ISCLI_20260204)')
    parser.add_argument('--out', required=True, help='Output HTML file path (e.g., dashboard.html)')
    parser.add_argument('--name', help='Batch name for dashboard title (default: derived from log-root)')

    args = parser.parse_args()

    # Determine batch name
    if args.name:
        batch_name = args.name
    else:
        batch_name = os.path.basename(os.path.normpath(args.log_root))

    print(f"Scanning log directory: {args.log_root}")
    print(f"Batch name: {batch_name}")

    # Find and parse test results
    results = find_test_results(args.log_root)

    if not results:
        print("\nNo test results found in the specified log directory.", file=sys.stderr)
        print("Expected directory structure: <log-root>/<date>/<feature>/<time>/results_*_stats.csv", file=sys.stderr)
        sys.exit(1)

    # Generate dashboard
    generate_dashboard_html(results, batch_name, args.out)


if __name__ == '__main__':
    main()
