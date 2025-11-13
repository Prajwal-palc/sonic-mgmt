"""
Comprehensive Report Generator for NTP CLI Tests
Generates: HTML reports, Markdown summaries, and detailed logs
"""

import json
import os
from datetime import datetime
from typing import List, Dict
from pathlib import Path


class TestCaseResult:
    """Enhanced test case result with detailed tracking"""

    def __init__(self, test_id: str, description: str, vs_instance: str, category: str):
        self.test_id = test_id
        self.description = description
        self.vs_instance = vs_instance
        self.category = category
        self.status = "PENDING"
        self.commands = []
        self.outputs = []
        self.db_snapshots = []
        self.start_time = None
        self.end_time = None
        self.duration = 0
        self.error_message = None
        self.cli_commands_log = []

    def start(self):
        """Mark test as started"""
        self.start_time = datetime.now()
        self.status = "RUNNING"

    def complete(self, status: str, error_message: str = None):
        """Mark test as completed"""
        self.end_time = datetime.now()
        self.status = status
        self.error_message = error_message
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()

    def add_command(self, command: str, output: str, return_code: int = 0):
        """Add command execution details"""
        self.commands.append(command)
        self.outputs.append(output)
        self.cli_commands_log.append({
            "command": command,
            "output": output,
            "return_code": return_code,
            "timestamp": datetime.now().isoformat()
        })

    def add_db_snapshot(self, snapshot: Dict):
        """Add database snapshot"""
        self.db_snapshots.append(snapshot)

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "test_id": self.test_id,
            "description": self.description,
            "vs_instance": self.vs_instance,
            "category": self.category,
            "status": self.status,
            "commands": self.commands,
            "outputs": self.outputs,
            "db_snapshots": self.db_snapshots,
            "cli_commands_log": self.cli_commands_log,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration": self.duration,
            "error_message": self.error_message
        }


class ComprehensiveReportGenerator:
    """Generate all required reports"""

    def __init__(self, results_dir: str):
        self.results_dir = results_dir
        self.results: List[TestCaseResult] = []
        self.start_time = datetime.now()
        self.end_time = None

        # Create results directory
        Path(results_dir).mkdir(parents=True, exist_ok=True)

    def add_result(self, result: TestCaseResult):
        """Add a test result"""
        self.results.append(result)

    def finalize(self):
        """Finalize reporting"""
        self.end_time = datetime.now()

    def get_summary(self) -> Dict:
        """Get test summary statistics"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        skipped = sum(1 for r in self.results if r.status == "SKIP")

        # Group by category
        categories = {}
        for result in self.results:
            cat = result.category
            if cat not in categories:
                categories[cat] = {"total": 0, "passed": 0, "failed": 0}
            categories[cat]["total"] += 1
            if result.status == "PASS":
                categories[cat]["passed"] += 1
            elif result.status == "FAIL":
                categories[cat]["failed"] += 1

        # Group by VS instance
        vs_instances = {}
        for result in self.results:
            vs = result.vs_instance
            if vs not in vs_instances:
                vs_instances[vs] = {"total": 0, "passed": 0, "failed": 0}
            vs_instances[vs]["total"] += 1
            if result.status == "PASS":
                vs_instances[vs]["passed"] += 1
            elif result.status == "FAIL":
                vs_instances[vs]["failed"] += 1

        duration = 0
        if self.end_time and self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "duration": duration,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "categories": categories,
            "vs_instances": vs_instances
        }

    def get_cli_commands_covered(self) -> List[str]:
        """Get list of all CLI commands tested"""
        commands = set()
        for result in self.results:
            for cmd in result.commands:
                # Extract base command
                base_cmd = cmd.split()[0:2] if len(cmd.split()) >= 2 else cmd.split()
                commands.add(" ".join(base_cmd))
        return sorted(list(commands))

    def generate_ntp_cli_test_report_html(self) -> str:
        """Generate ntp_cli_test_report.html"""
        filepath = os.path.join(self.results_dir, "ntp_cli_test_report.html")
        summary = self.get_summary()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NTP CLI Test Report</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}
        .header {{
            text-align: center;
            border-bottom: 4px solid #667eea;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #333;
            margin: 0 0 10px 0;
            font-size: 36px;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 16px;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .summary-card .value {{
            font-size: 42px;
            font-weight: bold;
        }}
        .section {{
            margin: 40px 0;
        }}
        .section h2 {{
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .status {{
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 12px;
            display: inline-block;
        }}
        .status-pass {{ background: #4caf50; color: white; }}
        .status-fail {{ background: #f44336; color: white; }}
        .status-skip {{ background: #ff9800; color: white; }}
        .details {{
            background: #f9f9f9;
            padding: 15px;
            margin: 10px 0;
            border-left: 4px solid #667eea;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 300px;
            overflow-y: auto;
        }}
        .command {{ color: #0066cc; font-weight: bold; }}
        .output {{ color: #333; white-space: pre-wrap; margin-top: 5px; }}
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #ddd;
            color: #666;
        }}
        .expandable {{
            cursor: pointer;
            color: #667eea;
            text-decoration: underline;
        }}
        .hidden {{ display: none; }}
    </style>
    <script>
        function toggleDetails(id) {{
            var element = document.getElementById(id);
            element.classList.toggle('hidden');
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NTP CLI Test Report</h1>
            <div class="subtitle">SONiC Network Operating System - NTP Feature Testing</div>
            <div class="subtitle">Generated: {datetime.now().strftime("%B %d, %Y at %H:%M:%S")}</div>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>Total Tests</h3>
                    <div class="value">{summary['total']}</div>
                </div>
                <div class="summary-card">
                    <h3>Passed</h3>
                    <div class="value">{summary['passed']}</div>
                </div>
                <div class="summary-card">
                    <h3>Failed</h3>
                    <div class="value">{summary['failed']}</div>
                </div>
                <div class="summary-card">
                    <h3>Pass Rate</h3>
                    <div class="value">{summary['pass_rate']:.1f}%</div>
                </div>
                <div class="summary-card">
                    <h3>Duration</h3>
                    <div class="value">{summary['duration']:.0f}s</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Test Results by Category</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Total</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Pass Rate</th>
                    </tr>
                </thead>
                <tbody>
"""

        for category, stats in summary['categories'].items():
            pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            html += f"""
                    <tr>
                        <td><strong>{category}</strong></td>
                        <td>{stats['total']}</td>
                        <td>{stats['passed']}</td>
                        <td>{stats['failed']}</td>
                        <td>{pass_rate:.1f}%</td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Test Results by VS Instance</h2>
            <table>
                <thead>
                    <tr>
                        <th>VS Instance</th>
                        <th>Total</th>
                        <th>Passed</th>
                        <th>Failed</th>
                        <th>Pass Rate</th>
                    </tr>
                </thead>
                <tbody>
"""

        for vs, stats in summary['vs_instances'].items():
            pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            html += f"""
                    <tr>
                        <td><strong>{vs}</strong></td>
                        <td>{stats['total']}</td>
                        <td>{stats['passed']}</td>
                        <td>{stats['failed']}</td>
                        <td>{pass_rate:.1f}%</td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Detailed Test Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test ID</th>
                        <th>Description</th>
                        <th>Category</th>
                        <th>VS Instance</th>
                        <th>Status</th>
                        <th>Duration (s)</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
"""

        for idx, result in enumerate(self.results):
            status_class = f"status-{result.status.lower()}"
            details_id = f"details_{idx}"

            html += f"""
                    <tr>
                        <td><strong>{result.test_id}</strong></td>
                        <td>{result.description}</td>
                        <td>{result.category}</td>
                        <td>{result.vs_instance}</td>
                        <td><span class="status {status_class}">{result.status}</span></td>
                        <td>{result.duration:.2f}</td>
                        <td><span class="expandable" onclick="toggleDetails('{details_id}')">Show/Hide</span></td>
                    </tr>
                    <tr>
                        <td colspan="7">
                            <div id="{details_id}" class="details hidden">
"""

            if result.error_message:
                html += f'<div style="color: red; font-weight: bold;">Error: {result.error_message}</div><hr>'

            for cmd, output in zip(result.commands, result.outputs):
                html += f"""
                                <div class="command">Command: {cmd}</div>
                                <div class="output">{output[:500]}{' ...(truncated)' if len(output) > 500 else ''}</div>
                                <hr>
"""

            html += """
                            </div>
                        </td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p><strong>NTP CLI Automation Test Framework v1.0</strong></p>
            <p>Generated by Claude Code | Professional Test Report</p>
        </div>
    </div>
</body>
</html>
"""

        with open(filepath, 'w') as f:
            f.write(html)

        return filepath

    def generate_pytest_report_final_html(self) -> str:
        """Generate pytest_report_final.html (pytest-style format with detailed errors)"""
        filepath = os.path.join(self.results_dir, "pytest_report_final.html")
        summary = self.get_summary()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Pytest Test Report - NTP CLI Tests</title>
    <style>
        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .summary {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .summary-item {{
            display: inline-block;
            margin: 10px 20px;
            font-size: 18px;
        }}
        .passed {{ color: #27ae60; font-weight: bold; }}
        .failed {{ color: #e74c3c; font-weight: bold; }}
        .test-result {{
            margin: 20px 0;
            padding: 15px;
            border-left: 4px solid #3498db;
            background: #f9f9f9;
        }}
        .test-result.PASS {{ border-left-color: #27ae60; }}
        .test-result.FAIL {{ border-left-color: #e74c3c; background: #fee; }}
        .test-header {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .test-details {{
            margin-top: 10px;
            padding: 10px;
            background: white;
            border: 1px solid #ddd;
            font-family: monospace;
            font-size: 12px;
        }}
        .error-section {{
            background: #ffebee;
            border: 1px solid #ef5350;
            padding: 15px;
            margin: 10px 0;
            border-radius: 5px;
        }}
        .error-title {{
            color: #c62828;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        pre {{
            background: #263238;
            color: #aed581;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        .metadata {{
            color: #666;
            font-size: 12px;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Pytest Test Report - NTP CLI Tests</h1>

        <div class="summary">
            <h2>Test Summary</h2>
            <div class="summary-item">Total: <strong>{summary['total']}</strong></div>
            <div class="summary-item passed">Passed: {summary['passed']}</div>
            <div class="summary-item failed">Failed: {summary['failed']}</div>
            <div class="summary-item">Skipped: {summary['skipped']}</div>
            <div class="summary-item">Duration: {summary['duration']:.2f}s</div>
            <div class="summary-item">Pass Rate: {summary['pass_rate']:.1f}%</div>
        </div>

        <h2>Test Results</h2>
"""

        for result in self.results:
            status_class = result.status
            html += f"""
        <div class="test-result {status_class}">
            <div class="test-header">
                {result.status}: {result.test_id} - {result.description}
            </div>
            <div class="metadata">
                Category: {result.category} | VS Instance: {result.vs_instance} | Duration: {result.duration:.2f}s
            </div>
"""

            if result.status == "FAIL" and result.error_message:
                html += f"""
            <div class="error-section">
                <div class="error-title">Error Details:</div>
                <pre>{result.error_message}</pre>
            </div>
"""

            html += f"""
            <div class="test-details">
                <strong>Commands Executed:</strong><br>
"""

            for i, (cmd, output) in enumerate(zip(result.commands, result.outputs), 1):
                html += f"""
                <div style="margin: 10px 0;">
                    <div><strong>Command {i}:</strong> <code>{cmd}</code></div>
                    <div><strong>Output:</strong></div>
                    <pre>{output[:1000]}{' ...(truncated)' if len(output) > 1000 else ''}</pre>
                </div>
"""

            html += """
            </div>
        </div>
"""

        html += f"""
        <div style="margin-top: 30px; padding-top: 20px; border-top: 2px solid #ddd; text-align: center; color: #666;">
            <p>Report generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>NTP CLI Automation Framework - Pytest Compatible Report</p>
        </div>
    </div>
</body>
</html>
"""

        with open(filepath, 'w') as f:
            f.write(html)

        return filepath

    def generate_ntp_cli_summary_html(self) -> str:
        """Generate ntp_cli_summary.html (CLI commands coverage summary)"""
        filepath = os.path.join(self.results_dir, "ntp_cli_summary.html")
        summary = self.get_summary()
        cli_commands = self.get_cli_commands_covered()

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NTP CLI Summary Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f0f0f0;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
        }}
        .coverage-section {{
            margin: 30px 0;
        }}
        .command-list {{
            list-style: none;
            padding: 0;
        }}
        .command-list li {{
            background: #ecf0f1;
            margin: 5px 0;
            padding: 10px 15px;
            border-left: 4px solid #3498db;
            border-radius: 3px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: #3498db;
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #34495e;
            color: white;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>NTP CLI Commands Coverage Summary</h1>

        <div class="stats">
            <div class="stat-card">
                <h3>Total Tests Executed</h3>
                <div class="value">{summary['total']}</div>
            </div>
            <div class="stat-card">
                <h3>CLI Commands Covered</h3>
                <div class="value">{len(cli_commands)}</div>
            </div>
        </div>

        <div class="coverage-section">
            <h2>CLI Commands Tested</h2>
            <ul class="command-list">
"""

        for cmd in cli_commands:
            html += f"                <li><code>{cmd}</code></li>\n"

        html += """
            </ul>
        </div>

        <div class="coverage-section">
            <h2>Test Coverage by Category</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Tests</th>
                        <th>Commands</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""

        for category, stats in summary['categories'].items():
            # Count unique commands in this category
            cat_commands = set()
            for result in self.results:
                if result.category == category:
                    for cmd in result.commands:
                        cat_commands.add(" ".join(cmd.split()[0:2]) if len(cmd.split()) >= 2 else cmd.split()[0])

            status = "✓ Complete" if stats['failed'] == 0 else "✗ Has Failures"
            html += f"""
                    <tr>
                        <td><strong>{category}</strong></td>
                        <td>{stats['total']}</td>
                        <td>{len(cat_commands)}</td>
                        <td>{status}</td>
                    </tr>
"""

        html += f"""
                </tbody>
            </table>
        </div>

        <div style="margin-top: 30px; text-align: center; color: #7f8c8d;">
            <p>Report generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    </div>
</body>
</html>
"""

        with open(filepath, 'w') as f:
            f.write(html)

        return filepath

    def generate_ntp_test_summary_md(self) -> str:
        """Generate ntp_test_summary.md"""
        filepath = os.path.join(self.results_dir, "ntp_test_summary.md")
        summary = self.get_summary()

        md = f"""# NTP CLI Test Summary

## Overview
**Test Execution Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Duration**: {summary['duration']:.2f} seconds

## Test Statistics

| Metric | Value |
|--------|-------|
| Total Tests | {summary['total']} |
| Passed | {summary['passed']} |
| Failed | {summary['failed']} |
| Skipped | {summary['skipped']} |
| Pass Rate | {summary['pass_rate']:.1f}% |

## Results by Category

| Category | Total | Passed | Failed | Pass Rate |
|----------|-------|--------|--------|-----------|
"""

        for category, stats in summary['categories'].items():
            pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            md += f"| {category} | {stats['total']} | {stats['passed']} | {stats['failed']} | {pass_rate:.1f}% |\n"

        md += f"""

## Results by VS Instance

| VS Instance | Total | Passed | Failed | Pass Rate |
|-------------|-------|--------|--------|-----------|
"""

        for vs, stats in summary['vs_instances'].items():
            pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            md += f"| {vs} | {stats['total']} | {stats['passed']} | {stats['failed']} | {pass_rate:.1f}% |\n"

        md += """

## Test Results Detail

| Test ID | Description | Category | VS Instance | Status | Duration (s) |
|---------|-------------|----------|-------------|--------|--------------|
"""

        for result in self.results:
            md += f"| {result.test_id} | {result.description} | {result.category} | {result.vs_instance} | {result.status} | {result.duration:.2f} |\n"

        md += """

## Conclusion

"""
        if summary['failed'] == 0:
            md += f"✅ **All {summary['total']} tests passed successfully!**\n"
        else:
            md += f"⚠️ **{summary['failed']} test(s) failed out of {summary['total']} total tests.**\n"

        md += f"""
---
*Report generated by NTP CLI Automation Framework v1.0*
"""

        with open(filepath, 'w') as f:
            f.write(md)

        return filepath

    def generate_ntp_execution_summary_md(self) -> str:
        """Generate ntp_execution_summary.md"""
        filepath = os.path.join(self.results_dir, "ntp_execution_summary.md")
        summary = self.get_summary()
        cli_commands = self.get_cli_commands_covered()

        md = f"""# NTP CLI Test Execution Summary

## Execution Information

**Start Time**: {summary['start_time']}
**End Time**: {summary['end_time']}
**Total Duration**: {summary['duration']:.2f} seconds ({summary['duration']/60:.1f} minutes)
**Framework Version**: 1.0

## Test Execution Configuration

### VS Instances Tested
"""

        for vs, stats in summary['vs_instances'].items():
            md += f"- **{vs}**: {stats['total']} tests\n"

        md += f"""

### Test Categories
"""

        for category in summary['categories'].keys():
            md += f"- {category}\n"

        md += f"""

## CLI Commands Coverage

Total CLI commands tested: **{len(cli_commands)}**

### Commands List
"""

        for cmd in sorted(cli_commands):
            md += f"- `{cmd}`\n"

        md += """

## Execution Results

### Overall Results
"""

        md += f"""
- ✅ Passed: **{summary['passed']}** ({summary['pass_rate']:.1f}%)
- ❌ Failed: **{summary['failed']}**
- ⊘ Skipped: **{summary['skipped']}**
- 📊 Total: **{summary['total']}**

### Category-wise Breakdown
"""

        for category, stats in summary['categories'].items():
            pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            md += f"""
#### {category}
- Tests: {stats['total']}
- Passed: {stats['passed']} ({pass_rate:.1f}%)
- Failed: {stats['failed']}
"""

        md += """

## Failed Tests Detail
"""

        failed_tests = [r for r in self.results if r.status == "FAIL"]
        if failed_tests:
            for result in failed_tests:
                md += f"""
### {result.test_id}: {result.description}
- **VS Instance**: {result.vs_instance}
- **Category**: {result.category}
- **Error**: {result.error_message or 'No error message'}
"""
        else:
            md += "\n✅ **No failed tests!**\n"

        md += """

## Logs and Reports

All detailed logs, command outputs, and DB snapshots are available in:
- **Logs Directory**: `/home/adminuser/draksha/cli/ntp/logs/`
- **Results Directory**: `/home/adminuser/draksha/ntp/cli/results/`

### Generated Reports
1. `ntp_cli_test_report.html` - Main test report with detailed results
2. `pytest_report_final.html` - Pytest-style report with error debugging
3. `ntp_cli_summary.html` - CLI commands coverage summary
4. `ntp_test_summary.md` - Test summary in Markdown
5. `ntp_execution_summary.md` - This execution summary

## Recommendations

"""

        if summary['failed'] > 0:
            md += """
⚠️ **Action Required**: Review failed test cases and their error messages in the pytest_report_final.html for debugging.

"""
        else:
            md += """
✅ **All Tests Passed**: The NTP CLI feature is functioning as expected across all test scenarios.

"""

        md += """
---
*Generated by NTP CLI Automation Framework*
*For detailed test logs, refer to the logs directory*
"""

        with open(filepath, 'w') as f:
            f.write(md)

        return filepath

    def generate_consolidated_log(self) -> str:
        """Generate consolidated test.log file"""
        filepath = os.path.join(self.results_dir, "test.log")

        with open(filepath, 'w') as f:
            f.write("="*80 + "\n")
            f.write("NTP CLI TEST EXECUTION LOG\n")
            f.write("="*80 + "\n\n")

            f.write(f"Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Tests: {len(self.results)}\n\n")

            for result in self.results:
                f.write("-"*80 + "\n")
                f.write(f"Test ID: {result.test_id}\n")
                f.write(f"Description: {result.description}\n")
                f.write(f"Category: {result.category}\n")
                f.write(f"VS Instance: {result.vs_instance}\n")
                f.write(f"Status: {result.status}\n")
                f.write(f"Duration: {result.duration:.2f}s\n")

                if result.error_message:
                    f.write(f"Error: {result.error_message}\n")

                f.write("\nCommands Executed:\n")
                for i, (cmd, output) in enumerate(zip(result.commands, result.outputs), 1):
                    f.write(f"\n[Command {i}]: {cmd}\n")
                    f.write(f"[Output {i}]:\n{output}\n")

                if result.db_snapshots:
                    f.write("\nDB Snapshots:\n")
                    for snapshot in result.db_snapshots:
                        f.write(json.dumps(snapshot, indent=2) + "\n")

                f.write("\n")

        return filepath

    def generate_all_reports(self) -> Dict[str, str]:
        """Generate all required reports"""
        self.finalize()

        reports = {
            "ntp_cli_test_report_html": self.generate_ntp_cli_test_report_html(),
            "pytest_report_final_html": self.generate_pytest_report_final_html(),
            "ntp_cli_summary_html": self.generate_ntp_cli_summary_html(),
            "ntp_test_summary_md": self.generate_ntp_test_summary_md(),
            "ntp_execution_summary_md": self.generate_ntp_execution_summary_md(),
            "test_log": self.generate_consolidated_log()
        }

        return reports
