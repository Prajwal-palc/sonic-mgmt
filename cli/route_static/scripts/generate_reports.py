"""
Report Generation Module
Generates comprehensive HTML and Markdown reports from pytest results
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import xml.etree.ElementTree as ET

# Add helpers to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from helpers.config_loader import ConfigLoader


class ReportGenerator:
    """Generate comprehensive test reports"""

    def __init__(self, results_dir: str, json_report_path: str = None):
        """
        Initialize Report Generator

        Args:
            results_dir: Directory to store reports
            json_report_path: Path to pytest JSON report
        """
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.json_report_path = json_report_path
        self.test_results = None
        self.config = ConfigLoader()

    def load_json_report(self):
        """Load pytest JSON report"""
        if self.json_report_path and Path(self.json_report_path).exists():
            with open(self.json_report_path, 'r') as f:
                self.test_results = json.load(f)
        else:
            print(f"Warning: JSON report not found at {self.json_report_path}")
            self.test_results = {'tests': [], 'summary': {}}

    def generate_cli_test_report_html(self):
        """Generate route_static_cli_test_report.html"""
        html_content = self._build_cli_test_report_html()
        output_file = self.results_dir / "route_static_cli_test_report.html"

        with open(output_file, 'w') as f:
            f.write(html_content)

        print(f"Generated: {output_file}")
        return str(output_file)

    def generate_summary_html(self):
        """Generate route_static_cli_summary.html"""
        html_content = self._build_summary_html()
        output_file = self.results_dir / "route_static_cli_summary.html"

        with open(output_file, 'w') as f:
            f.write(html_content)

        print(f"Generated: {output_file}")
        return str(output_file)

    def generate_summary_markdown(self):
        """Generate route_static_summary.md"""
        md_content = self._build_summary_markdown()
        output_file = self.results_dir / "route_static_summary.md"

        with open(output_file, 'w') as f:
            f.write(md_content)

        print(f"Generated: {output_file}")
        return str(output_file)

    def generate_execution_summary_markdown(self):
        """Generate route_static_execution_summary.md"""
        md_content = self._build_execution_summary_markdown()
        output_file = self.results_dir / "route_static_execution_summary.md"

        with open(output_file, 'w') as f:
            f.write(md_content)

        print(f"Generated: {output_file}")
        return str(output_file)

    def _build_cli_test_report_html(self) -> str:
        """Build comprehensive CLI test report HTML"""
        summary = self.test_results.get('summary', {})
        tests = self.test_results.get('tests', [])

        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        skipped = summary.get('skipped', 0)
        total = summary.get('total', 0)
        duration = summary.get('duration', 0)

        pass_rate = (passed / total * 100) if total > 0 else 0

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Static Route CLI Test Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
        }}
        .stat-passed {{ color: #27ae60; }}
        .stat-failed {{ color: #e74c3c; }}
        .stat-skipped {{ color: #f39c12; }}
        .stat-total {{ color: #3498db; }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 1.8em;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
        }}
        .test-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .test-table th {{
            background: #34495e;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        .test-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ddd;
        }}
        .test-table tr:hover {{
            background: #f8f9fa;
        }}
        .status-badge {{
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .status-passed {{
            background: #d4edda;
            color: #155724;
        }}
        .status-failed {{
            background: #f8d7da;
            color: #721c24;
        }}
        .status-skipped {{
            background: #fff3cd;
            color: #856404;
        }}
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #ecf0f1;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #27ae60 0%, #2ecc71 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 0.5s ease;
        }}
        .device-section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }}
        .command-box {{
            background: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            font-family: 'Courier New', monospace;
            margin: 10px 0;
            overflow-x: auto;
        }}
        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Static Route CLI Test Report</h1>
            <p>Comprehensive Test Results for SONiC Static Route Configuration</p>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Total Tests</div>
                <div class="stat-value stat-total">{total}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Passed</div>
                <div class="stat-value stat-passed">{passed}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Failed</div>
                <div class="stat-value stat-failed">{failed}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Skipped</div>
                <div class="stat-value stat-skipped">{skipped}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pass Rate</div>
                <div class="stat-value" style="color: {'#27ae60' if pass_rate >= 90 else '#e74c3c'};">{pass_rate:.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Duration</div>
                <div class="stat-value">{duration:.2f}s</div>
            </div>
        </div>

        <div class="content">
            <div class="section">
                <h2 class="section-title">Test Execution Progress</h2>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {pass_rate}%;">
                        {pass_rate:.1f}% Complete
                    </div>
                </div>
            </div>

            <div class="section">
                <h2 class="section-title">Test Results by Category</h2>
"""

        # Group tests by category
        ipv4_tests = [t for t in tests if 'ipv4' in t.get('nodeid', '').lower()]
        ipv6_tests = [t for t in tests if 'ipv6' in t.get('nodeid', '').lower()]
        deletion_tests = [t for t in tests if 'delete' in t.get('nodeid', '').lower()]
        verification_tests = [t for t in tests if 'show' in t.get('nodeid', '').lower() or 'verification' in t.get('nodeid', '').lower()]

        for category_name, category_tests in [
            ("IPv4 Static Routes", ipv4_tests),
            ("IPv6 Static Routes", ipv6_tests),
            ("Route Deletion", deletion_tests),
            ("Route Verification", verification_tests)
        ]:
            if category_tests:
                html += f"""
                <div class="device-section">
                    <h3>{category_name}</h3>
                    <table class="test-table">
                        <thead>
                            <tr>
                                <th>Test Name</th>
                                <th>Device</th>
                                <th>Status</th>
                                <th>Duration</th>
                            </tr>
                        </thead>
                        <tbody>
"""
                for test in category_tests:
                    test_name = test.get('nodeid', '').split('::')[-1]
                    outcome = test.get('outcome', 'unknown')
                    duration = test.get('duration', 0)
                    device = test.get('device_name', 'N/A')

                    status_class = f"status-{outcome}"
                    html += f"""
                            <tr>
                                <td>{test_name}</td>
                                <td>{device}</td>
                                <td><span class="status-badge {status_class}">{outcome.upper()}</span></td>
                                <td>{duration:.2f}s</td>
                            </tr>
"""
                html += """
                        </tbody>
                    </table>
                </div>
"""

        html += """
        </div>

        <div class="section">
            <h2 class="section-title">CLI Commands Tested</h2>
            <div class="device-section">
                <h3>IPv4 Configuration Commands</h3>
                <div class="command-box">ip route &lt;prefix&gt; &lt;next-hop&gt;</div>
                <div class="command-box">ip route &lt;prefix&gt; blackhole</div>
                <div class="command-box">no ip route &lt;prefix&gt; &lt;next-hop&gt;</div>
                <div class="command-box">no ip route &lt;prefix&gt; blackhole</div>
            </div>

            <div class="device-section">
                <h3>IPv6 Configuration Commands</h3>
                <div class="command-box">ipv6 route &lt;prefix&gt; &lt;next-hop&gt;</div>
                <div class="command-box">ipv6 route &lt;prefix&gt; blackhole</div>
                <div class="command-box">no ipv6 route &lt;prefix&gt; &lt;next-hop&gt;</div>
                <div class="command-box">no ipv6 route &lt;prefix&gt; blackhole</div>
            </div>

            <div class="device-section">
                <h3>Verification Commands</h3>
                <div class="command-box">show ip route static</div>
                <div class="command-box">show ipv6 route static</div>
                <div class="command-box">show running-configuration</div>
            </div>
        </div>
    </div>

    <div class="footer">
        <p>Static Route CLI Test Framework v1.0</p>
        <p>Generated by Automated Test System</p>
    </div>
</div>
</body>
</html>"""

        return html

    def _build_summary_html(self) -> str:
        """Build summary HTML report"""
        summary = self.test_results.get('summary', {})

        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        total = summary.get('total', 0)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Static Route CLI Test Summary</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background: #f0f0f0;
        }}
        .summary-container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .summary-stats {{
            display: flex;
            justify-content: space-around;
            margin: 30px 0;
        }}
        .stat-box {{
            text-align: center;
            padding: 20px;
            border-radius: 8px;
        }}
        .stat-box h2 {{
            font-size: 3em;
            margin: 10px 0;
        }}
        .passed {{ background: #d4edda; color: #155724; }}
        .failed {{ background: #f8d7da; color: #721c24; }}
        .total {{ background: #d1ecf1; color: #0c5460; }}
    </style>
</head>
<body>
    <div class="summary-container">
        <h1>Static Route CLI Test Summary</h1>
        <p>Test execution completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary-stats">
            <div class="stat-box total">
                <h3>Total Tests</h3>
                <h2>{total}</h2>
            </div>
            <div class="stat-box passed">
                <h3>Passed</h3>
                <h2>{passed}</h2>
            </div>
            <div class="stat-box failed">
                <h3>Failed</h3>
                <h2>{failed}</h2>
            </div>
        </div>

        <h2>Test Coverage</h2>
        <ul>
            <li>IPv4 Static Route Configuration</li>
            <li>IPv6 Static Route Configuration</li>
            <li>Blackhole Routes (IPv4 and IPv6)</li>
            <li>Route Deletion Commands</li>
            <li>Route Verification Commands</li>
        </ul>
    </div>
</body>
</html>"""

        return html

    def _build_summary_markdown(self) -> str:
        """Build summary markdown report"""
        summary = self.test_results.get('summary', {})
        tests = self.test_results.get('tests', [])

        passed = summary.get('passed', 0)
        failed = summary.get('failed', 0)
        total = summary.get('total', 0)
        duration = summary.get('duration', 0)

        md = f"""# Static Route CLI Test Summary

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This report summarizes the execution of Static Route CLI tests on SONiC devices.

### Test Statistics

| Metric | Value |
|--------|-------|
| Total Tests | {total} |
| Passed | {passed} |
| Failed | {failed} |
| Skipped | {summary.get('skipped', 0)} |
| Pass Rate | {(passed/total*100 if total > 0 else 0):.2f}% |
| Total Duration | {duration:.2f}s |

## Test Coverage

### Commands Tested

#### IPv4 Commands
- `ip route <prefix> <next-hop>`
- `ip route <prefix> blackhole`
- `no ip route <prefix> <next-hop>`
- `no ip route <prefix> blackhole`

#### IPv6 Commands
- `ipv6 route <prefix> <next-hop>`
- `ipv6 route <prefix> blackhole`
- `no ipv6 route <prefix> <next-hop>`
- `no ipv6 route <prefix> blackhole`

#### Verification Commands
- `show ip route static`
- `show ipv6 route static`
- `show running-configuration`

## Test Results by Device

"""

        # Group by device
        devices = {}
        for test in tests:
            device_name = test.get('device_name', 'Unknown')
            if device_name not in devices:
                devices[device_name] = []
            devices[device_name].append(test)

        for device_name, device_tests in devices.items():
            device_passed = sum(1 for t in device_tests if t.get('outcome') == 'passed')
            device_failed = sum(1 for t in device_tests if t.get('outcome') == 'failed')
            device_total = len(device_tests)

            md += f"""### {device_name}

| Status | Count |
|--------|-------|
| Total | {device_total} |
| Passed | {device_passed} |
| Failed | {device_failed} |
| Pass Rate | {(device_passed/device_total*100 if device_total > 0 else 0):.2f}% |

"""

        md += f"""
## Conclusion

The Static Route CLI test execution has been completed with a **{(passed/total*100 if total > 0 else 0):.1f}%** pass rate.

---

*Report generated by Static Route CLI Test Framework*
"""

        return md

    def _build_execution_summary_markdown(self) -> str:
        """Build detailed execution summary markdown"""
        summary = self.test_results.get('summary', {})
        tests = self.test_results.get('tests', [])

        md = f"""# Static Route CLI Test Execution Summary

**Test Execution Date**: {datetime.now().strftime('%Y-%m-%d')}
**Test Execution Time**: {datetime.now().strftime('%H:%M:%S')}
**Framework**: Pytest-based CLI Testing Framework

---

## Overview

This document provides a comprehensive summary of the Static Route CLI test execution performed on SONiC Virtual Switch (VS) instances.

### Test Environment

**Devices Under Test**:
"""

        devices = self.config.get_devices()
        for device in devices:
            md += f"- {device['name']}: {device['host']}\n"

        md += f"""
### Execution Summary

| Metric | Value |
|--------|-------|
| Total Test Cases | {summary.get('total', 0)} |
| Passed | {summary.get('passed', 0)} |
| Failed | {summary.get('failed', 0)} |
| Skipped | {summary.get('skipped', 0)} |
| Errors | {summary.get('error', 0)} |
| Duration | {summary.get('duration', 0):.2f}s |
| Pass Rate | {(summary.get('passed', 0)/summary.get('total', 1)*100):.2f}% |

---

## Detailed Test Results

### Test Cases Executed

"""

        # Group tests by class/category
        test_classes = {}
        for test in tests:
            nodeid = test.get('nodeid', '')
            class_name = nodeid.split('::')[1] if '::' in nodeid else 'Miscellaneous'

            if class_name not in test_classes:
                test_classes[class_name] = []
            test_classes[class_name].append(test)

        for class_name, class_tests in test_classes.items():
            md += f"""### {class_name}

| Test Case | Device | Status | Duration |
|-----------|--------|--------|----------|
"""
            for test in class_tests:
                test_name = test.get('nodeid', '').split('::')[-1]
                device = test.get('device_name', 'N/A')
                outcome = test.get('outcome', 'unknown')
                duration = test.get('duration', 0)

                status_emoji = "✅" if outcome == "passed" else "❌" if outcome == "failed" else "⏸️"

                md += f"| {test_name} | {device} | {status_emoji} {outcome.upper()} | {duration:.2f}s |\n"

            md += "\n"

        md += """
---

## Test Artifacts

### Generated Files

1. **Test Logs**: `/home/adminuser/draksha/cli/route_static/logs/`
2. **CLI Output Logs**: `/home/adminuser/draksha/cli/route_static/logs/cli_output/`
3. **DB Snapshots**: `/home/adminuser/draksha/cli/route_static/logs/db_snapshots/`
4. **Test Reports**: `/home/adminuser/draksha/cli/route_static/results/`

---

## Conclusion

The Static Route CLI testing has been successfully executed using the pytest framework.

**Overall Status**: """ + ("✅ PASSED" if summary.get('failed', 0) == 0 else "⚠️ NEEDS ATTENTION") + f"""

**Pass Rate**: {(summary.get('passed', 0)/summary.get('total', 1)*100):.2f}%

---

*End of Execution Summary*
"""

        return md

    def generate_all_reports(self):
        """Generate all required reports"""
        print("Loading test results...")
        self.load_json_report()

        print("\nGenerating reports...")
        reports = {}

        reports['cli_test_report'] = self.generate_cli_test_report_html()
        reports['summary_html'] = self.generate_summary_html()
        reports['summary_md'] = self.generate_summary_markdown()
        reports['execution_summary_md'] = self.generate_execution_summary_markdown()

        print("\n✅ All reports generated successfully!")
        return reports


def main():
    """Main function to generate reports"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate test reports')
    parser.add_argument('--json-report', help='Path to pytest JSON report')
    parser.add_argument('--results-dir', default='/home/adminuser/draksha/cli/route_static/results',
                        help='Results directory')

    args = parser.parse_args()

    generator = ReportGenerator(args.results_dir, args.json_report)
    generator.generate_all_reports()


if __name__ == '__main__':
    main()
