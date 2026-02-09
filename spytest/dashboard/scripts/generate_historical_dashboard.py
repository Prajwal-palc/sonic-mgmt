#!/usr/bin/env python3
"""
Historical Dashboard Generator for SPyTest Results
Generates a comprehensive dashboard showing test results over time with comparisons and trends.

Usage:
    python3 generate_historical_dashboard.py --log-root ./logs --out ./dashboard_historical.html

Features:
    - Historical trend analysis
    - Comparison with previous two runs
    - Tab-based navigation
    - Interactive charts (Chart.js)
    - Pass rate tracking
    - Test failure analysis
"""

import os
import sys
import glob
import json
import argparse
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import csv

class TestResult:
    """Represents a single test result"""
    def __init__(self, test_name, status, duration=0, module=""):
        self.test_name = test_name
        self.status = status  # Pass, Fail, Skip, etc.
        self.duration = duration
        self.module = module

class TestRun:
    """Represents a complete test run"""
    def __init__(self, date, batch_name, log_path):
        self.date = date
        self.batch_name = batch_name
        self.log_path = log_path
        self.results = []
        self.total_tests = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.duration = 0
        self.build_info = "N/A"

    def add_result(self, result):
        self.results.append(result)
        self.total_tests += 1
        if result.status == "Pass":
            self.passed += 1
        elif result.status == "Fail":
            self.failed += 1
        elif result.status == "Skip":
            self.skipped += 1

    def calculate_pass_rate(self):
        if self.total_tests > 0:
            return (self.passed / self.total_tests) * 100
        return 0.0

def parse_time_duration(time_str):
    """Parse time format H:MM:SS or MM:SS or float to seconds"""
    try:
        # If already a number, return as is
        if isinstance(time_str, (int, float)):
            return float(time_str)

        # Handle string time format
        time_str = str(time_str).strip()
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 3:  # H:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])

        # Try direct float conversion
        return float(time_str)
    except Exception:
        return 0.0

def parse_result_csv(csv_file):
    """Parse CSV result file and extract test results"""
    results = []
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle different CSV formats
                test_name = row.get('Function', row.get('TestCase', 'Unknown'))
                status = row.get('Result', row.get('Status', 'Unknown'))
                duration_str = row.get('TimeTaken', row.get('Duration', '0'))
                duration = parse_time_duration(duration_str)
                module = row.get('Module', row.get('TestModule', ''))

                results.append(TestResult(test_name, status, duration, module))
    except Exception as e:
        print(f"Error parsing {csv_file}: {e}")

    return results

def parse_export_txt(txt_file):
    """Parse export.txt file for test results"""
    results = []
    try:
        with open(txt_file, 'r') as f:
            for line in f:
                # Example line: "test_bgp_basic::test_case_001 Pass 12.34s"
                match = re.match(r'(\S+)\s+(Pass|Fail|Skip)\s+([\d.]+)s?', line.strip())
                if match:
                    test_name, status, duration = match.groups()
                    results.append(TestResult(test_name, status, float(duration)))
    except Exception as e:
        print(f"Error parsing {txt_file}: {e}")

    return results

def find_test_runs(log_root):
    """Scan log directories and collect all test runs"""
    test_runs = []
    log_root = Path(log_root)

    # Find all date directories (format: YYYYMMDD or PREFIX_YYYYMMDD like SM_ISCLI_20260204)
    # Pattern 1: Direct date directories like 20260204
    date_dirs = sorted([d for d in log_root.glob("202*") if d.is_dir() and d.name.isdigit()])

    # Pattern 2: Prefix_date directories like SM_ISCLI_20260204, BGP_V4_20260205, etc.
    prefix_date_dirs = sorted([d for d in log_root.glob("*_202*") if d.is_dir() and any(char.isdigit() for char in d.name)])

    # Combine both patterns
    all_candidate_dirs = date_dirs + prefix_date_dirs

    for date_dir in all_candidate_dirs:
        # Extract date from directory name
        date_str = None
        if date_dir.name.isdigit() and len(date_dir.name) == 8:
            date_str = date_dir.name
        else:
            # Extract YYYYMMDD from names like SM_ISCLI_20260204
            import re
            match = re.search(r'(202\d{5})', date_dir.name)
            if match:
                date_str = match.group(1)

        if not date_str:
            continue

        try:
            date = datetime.strptime(date_str, "%Y%m%d")
        except:
            continue

        # Find all batch directories under this date
        batch_dirs = [d for d in date_dir.iterdir() if d.is_dir()]

        for batch_dir in batch_dirs:
            batch_name = batch_dir.name

            # Find timestamp subdirectories
            time_dirs = [d for d in batch_dir.iterdir() if d.is_dir()]

            for time_dir in time_dirs:
                test_run = TestRun(date, batch_name, str(time_dir))

                # Look for result files
                csv_files = list(time_dir.glob("*_functions.csv"))
                export_files = list(time_dir.glob("*_export.txt"))

                if csv_files:
                    results = parse_result_csv(csv_files[0])
                    for result in results:
                        test_run.add_result(result)
                elif export_files:
                    results = parse_export_txt(export_files[0])
                    for result in results:
                        test_run.add_result(result)

                if test_run.total_tests > 0:
                    test_runs.append(test_run)

    return sorted(test_runs, key=lambda x: x.date)

def get_comparison_data(test_runs, current_idx):
    """Get comparison data for current run vs previous two runs"""
    comparison = {
        "current": None,
        "prev1": None,
        "prev2": None
    }

    if current_idx < len(test_runs):
        comparison["current"] = test_runs[current_idx]
    if current_idx - 1 >= 0:
        comparison["prev1"] = test_runs[current_idx - 1]
    if current_idx - 2 >= 0:
        comparison["prev2"] = test_runs[current_idx - 2]

    return comparison

def collect_test_level_data(log_root):
    """Collect test-level data: {test_name: {date: {batch: {status, duration, module}}}}"""
    test_data = defaultdict(lambda: defaultdict(dict))
    dates = set()

    log_root = Path(log_root)

    # Find all date directories
    date_dirs = sorted([d for d in log_root.glob("202*") if d.is_dir() and d.name.isdigit()])
    prefix_date_dirs = sorted([d for d in log_root.glob("*_202*") if d.is_dir() and any(char.isdigit() for char in d.name)])
    all_candidate_dirs = date_dirs + prefix_date_dirs

    for date_dir in all_candidate_dirs:
        # Extract date from directory name
        date_str = None
        if date_dir.name.isdigit() and len(date_dir.name) == 8:
            date_str = date_dir.name
        else:
            match = re.search(r'(202\d{5})', date_dir.name)
            if match:
                date_str = match.group(1)

        if not date_str:
            continue

        try:
            date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
            dates.add(date)
        except:
            continue

        # Find all batch directories
        batch_dirs = [d for d in date_dir.iterdir() if d.is_dir()]

        for batch_dir in batch_dirs:
            batch_name = batch_dir.name

            # Find timestamp subdirectories
            time_dirs = [d for d in batch_dir.iterdir() if d.is_dir()]

            for time_dir in time_dirs:
                # Look for *_functions.csv files
                csv_files = list(time_dir.glob("*_functions.csv"))

                if csv_files:
                    try:
                        with open(csv_files[0], 'r') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                # Use TestFunction column
                                test_name = row.get('TestFunction', '').strip()

                                # Skip empty test names (Module Prolog/Epilog rows)
                                if not test_name:
                                    continue

                                status = row.get('Result', 'Unknown').strip()

                                # Skip rows with empty status
                                if not status:
                                    continue

                                duration_str = row.get('TimeTaken', '0')
                                duration = parse_time_duration(duration_str)
                                module = row.get('Module', '')

                                # Store test result
                                test_data[test_name][date][batch_name] = {
                                    'status': status,
                                    'duration': duration,
                                    'module': module
                                }
                    except Exception as e:
                        print(f"Error parsing {csv_files[0]}: {e}")

    return test_data, sorted(dates)

def generate_html_dashboard(test_runs, output_file, dashboard_name="Historical Test Dashboard", log_root=None):
    """Generate the HTML dashboard with interactive charts"""

    # Prepare data for charts
    dates = [run.date.strftime("%Y-%m-%d") for run in test_runs]
    pass_rates = [run.calculate_pass_rate() for run in test_runs]
    total_tests = [run.total_tests for run in test_runs]
    passed_tests = [run.passed for run in test_runs]
    failed_tests = [run.failed for run in test_runs]

    # Group by batch name
    batches = defaultdict(list)
    for run in test_runs:
        batches[run.batch_name].append(run)

    # Collect test-level data for the new tab
    test_level_data = {}
    test_dates = []
    if log_root:
        test_level_data, test_dates = collect_test_level_data(log_root)

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dashboard_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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

        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}

        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s;
        }}

        .card:hover {{
            transform: translateY(-5px);
        }}

        .card h3 {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }}

        .card .value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .card .change {{
            font-size: 0.9em;
        }}

        .card.pass .value {{ color: #28a745; }}
        .card.fail .value {{ color: #dc3545; }}
        .card.total .value {{ color: #667eea; }}
        .card.rate .value {{ color: #17a2b8; }}

        .tabs {{
            display: flex;
            background: #f8f9fa;
            padding: 0 30px;
            border-bottom: 2px solid #dee2e6;
        }}

        .tab {{
            padding: 15px 25px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1em;
            color: #666;
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }}

        .tab:hover {{
            color: #667eea;
        }}

        .tab.active {{
            color: #667eea;
            border-bottom-color: #667eea;
            font-weight: bold;
        }}

        .tab-content {{
            display: none;
            padding: 30px;
        }}

        .tab-content.active {{
            display: block;
        }}

        .chart-container {{
            position: relative;
            height: 400px;
            margin-bottom: 30px;
        }}

        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}

        .comparison-table th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
        }}

        .comparison-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #dee2e6;
        }}

        .comparison-table tr:hover {{
            background: #f8f9fa;
        }}

        .trend-up {{
            color: #28a745;
        }}

        .trend-down {{
            color: #dc3545;
        }}

        .batch-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .batch-card {{
            background: white;
            border: 1px solid #dee2e6;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .batch-card h4 {{
            color: #667eea;
            margin-bottom: 15px;
        }}

        .progress-bar {{
            background: #e9ecef;
            height: 25px;
            border-radius: 5px;
            overflow: hidden;
            margin: 10px 0;
        }}

        .progress-fill {{
            height: 100%;
            background: #28a745;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
        }}

        .history-list {{
            list-style: none;
        }}

        .history-item {{
            padding: 15px;
            border-left: 4px solid #667eea;
            margin-bottom: 15px;
            background: #f8f9fa;
            border-radius: 5px;
        }}

        .history-item .date {{
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}

        .history-item .stats {{
            color: #666;
            font-size: 0.9em;
        }}

        /* Test Details Tab Styles */
        .test-details-controls {{
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            align-items: center;
        }}

        .search-box {{
            flex: 1;
            max-width: 400px;
        }}

        .search-box input {{
            width: 100%;
            padding: 10px 15px;
            border: 2px solid #dee2e6;
            border-radius: 5px;
            font-size: 1em;
        }}

        .search-box input:focus {{
            outline: none;
            border-color: #667eea;
        }}

        .test-details-table-container {{
            overflow-x: auto;
            border: 1px solid #dee2e6;
            border-radius: 10px;
        }}

        .test-details-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}

        .test-details-table th {{
            background: #667eea;
            color: white;
            padding: 12px 8px;
            text-align: left;
            position: sticky;
            top: 0;
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}

        .test-details-table th:hover {{
            background: #5568d3;
        }}

        .test-details-table th.sortable::after {{
            content: ' ⇅';
            opacity: 0.5;
        }}

        .test-details-table th.sorted-asc::after {{
            content: ' ↑';
            opacity: 1;
        }}

        .test-details-table th.sorted-desc::after {{
            content: ' ↓';
            opacity: 1;
        }}

        .test-details-table td {{
            padding: 8px;
            border-bottom: 1px solid #dee2e6;
            white-space: nowrap;
        }}

        .test-details-table tbody tr:hover {{
            background: #f8f9fa;
        }}

        .test-details-table .test-name {{
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .test-details-table .module-name {{
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 0.85em;
            color: #666;
        }}

        .status-pass {{
            background: #d4edda;
            color: #155724;
            padding: 4px 8px;
            border-radius: 3px;
            font-weight: bold;
            text-align: center;
        }}

        .status-fail {{
            background: #f8d7da;
            color: #721c24;
            padding: 4px 8px;
            border-radius: 3px;
            font-weight: bold;
            text-align: center;
        }}

        .status-skip {{
            background: #fff3cd;
            color: #856404;
            padding: 4px 8px;
            border-radius: 3px;
            font-weight: bold;
            text-align: center;
        }}

        .status-none {{
            color: #999;
            text-align: center;
        }}

        .status-topofail {{
            background: #e2e3e5;
            color: #383d41;
            padding: 4px 8px;
            border-radius: 3px;
            font-weight: bold;
            text-align: center;
            font-size: 0.8em;
        }}

        .status-configfail {{
            background: #fff3cd;
            color: #856404;
            padding: 4px 8px;
            border-radius: 3px;
            font-weight: bold;
            text-align: center;
            font-size: 0.8em;
        }}

        .pass-rate-high {{
            color: #28a745;
            font-weight: bold;
        }}

        .pass-rate-medium {{
            color: #ffc107;
            font-weight: bold;
        }}

        .pass-rate-low {{
            color: #dc3545;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{dashboard_name}</h1>
            <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>Total Test Runs: {len(test_runs)} | Date Range: {dates[0] if dates else "N/A"} to {dates[-1] if dates else "N/A"}</p>
        </div>

        <div class="summary-cards">
'''

    # Calculate summary statistics from latest run
    if test_runs:
        latest = test_runs[-1]
        prev = test_runs[-2] if len(test_runs) > 1 else None

        pass_change = ""
        fail_change = ""
        if prev:
            pass_diff = latest.passed - prev.passed
            fail_diff = latest.failed - prev.failed
            pass_change = f'<span class="{"trend-up" if pass_diff > 0 else "trend-down"}">{"↑" if pass_diff > 0 else "↓"} {abs(pass_diff)}</span>'
            fail_change = f'<span class="{"trend-down" if fail_diff > 0 else "trend-up"}">{"↑" if fail_diff > 0 else "↓"} {abs(fail_diff)}</span>'

        html_content += f'''
            <div class="card total">
                <h3>Total Tests</h3>
                <div class="value">{latest.total_tests}</div>
                <div class="change">Latest Run</div>
            </div>
            <div class="card pass">
                <h3>Passed</h3>
                <div class="value">{latest.passed}</div>
                <div class="change">{pass_change}</div>
            </div>
            <div class="card fail">
                <h3>Failed</h3>
                <div class="value">{latest.failed}</div>
                <div class="change">{fail_change}</div>
            </div>
            <div class="card rate">
                <h3>Pass Rate</h3>
                <div class="value">{latest.calculate_pass_rate():.1f}%</div>
                <div class="change">Current</div>
            </div>
'''

    html_content += '''
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showTab('overview')">Overview</button>
            <button class="tab" onclick="showTab('trends')">Trends</button>
            <button class="tab" onclick="showTab('comparison')">Comparison</button>
            <button class="tab" onclick="showTab('batches')">By Batch</button>
            <button class="tab" onclick="showTab('history')">History</button>
            <button class="tab" onclick="showTab('testdetails')">Test Details</button>
        </div>

        <div id="overview" class="tab-content active">
            <h2>Test Results Overview</h2>
            <div class="chart-container">
                <canvas id="overviewChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="passRateChart"></canvas>
            </div>
        </div>

        <div id="trends" class="tab-content">
            <h2>Historical Trends</h2>
            <div class="chart-container">
                <canvas id="trendChart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="distributionChart"></canvas>
            </div>
        </div>

        <div id="comparison" class="tab-content">
            <h2>Run Comparison (Latest 3 Runs)</h2>
'''

    # Generate comparison table
    if len(test_runs) >= 1:
        comparison_runs = test_runs[-3:]  # Last 3 runs
        html_content += '''
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Metric</th>
'''
        for i, run in enumerate(reversed(comparison_runs)):
            label = "Current" if i == 0 else f"Previous {i}"
            html_content += f'<th>{label}<br><small>{run.date.strftime("%Y-%m-%d")}</small></th>'

        html_content += '''
                    </tr>
                </thead>
                <tbody>
'''

        # Add comparison rows
        metrics = [
            ("Total Tests", "total_tests"),
            ("Passed", "passed"),
            ("Failed", "failed"),
            ("Skipped", "skipped"),
            ("Pass Rate", "pass_rate")
        ]

        for metric_name, metric_attr in metrics:
            html_content += f'<tr><td><strong>{metric_name}</strong></td>'
            for run in reversed(comparison_runs):
                if metric_attr == "pass_rate":
                    value = f'{run.calculate_pass_rate():.1f}%'
                else:
                    value = getattr(run, metric_attr)
                html_content += f'<td>{value}</td>'
            html_content += '</tr>'

        html_content += '''
                </tbody>
            </table>
'''

    html_content += '''
        </div>

        <div id="batches" class="tab-content">
            <h2>Results by Batch</h2>
            <div class="batch-grid">
'''

    # Generate batch cards
    for batch_name, batch_runs in batches.items():
        latest_batch = batch_runs[-1]
        html_content += f'''
                <div class="batch-card">
                    <h4>{batch_name}</h4>
                    <p><strong>Latest Run:</strong> {latest_batch.date.strftime("%Y-%m-%d")}</p>
                    <p><strong>Total Tests:</strong> {latest_batch.total_tests}</p>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {latest_batch.calculate_pass_rate()}%">
                            {latest_batch.passed}/{latest_batch.total_tests} ({latest_batch.calculate_pass_rate():.1f}%)
                        </div>
                    </div>
                    <p style="margin-top:10px;">
                        <span style="color:#28a745">✓ {latest_batch.passed}</span> |
                        <span style="color:#dc3545">✗ {latest_batch.failed}</span> |
                        <span style="color:#ffc107">○ {latest_batch.skipped}</span>
                    </p>
                </div>
'''

    html_content += '''
            </div>
        </div>

        <div id="history" class="tab-content">
            <h2>Test Execution History</h2>
            <ul class="history-list">
'''

    # Generate history list (reverse chronological)
    for run in reversed(test_runs):
        html_content += f'''
                <li class="history-item">
                    <div class="date">{run.date.strftime("%Y-%m-%d")} - {run.batch_name}</div>
                    <div class="stats">
                        Tests: {run.total_tests} |
                        Pass: {run.passed} ({run.calculate_pass_rate():.1f}%) |
                        Fail: {run.failed} |
                        Skip: {run.skipped}
                    </div>
                </li>
'''

    html_content += '''
            </ul>
        </div>

        <div id="testdetails" class="tab-content">
            <h2>Test Details</h2>
            <div class="test-details-controls">
                <div class="search-box">
                    <input type="text" id="testSearch" placeholder="Search test names..." onkeyup="filterTests()">
                </div>
                <div>
                    <strong>Total Tests: <span id="testCount">0</span></strong>
                </div>
            </div>
            <div class="test-details-table-container">
                <table class="test-details-table" id="testDetailsTable">
                    <thead>
                        <tr>
                            <th class="sortable" onclick="sortTable(0)">Test Name</th>
                            <th class="sortable" onclick="sortTable(1)">Module</th>
'''

    # Add date columns
    col_idx = 2
    for date in test_dates:
        html_content += f'                            <th class="sortable" onclick="sortTable({col_idx})">{date}</th>\n'
        col_idx += 1

    html_content += f'''                            <th class="sortable" onclick="sortTable({col_idx})">Total Runs</th>
                            <th class="sortable" onclick="sortTable({col_idx+1})">Pass Count</th>
                            <th class="sortable" onclick="sortTable({col_idx+2})">Fail Count</th>
                            <th class="sortable" onclick="sortTable({col_idx+3})">Pass Rate %</th>
                        </tr>
                    </thead>
                    <tbody id="testDetailsBody">
'''

    # Generate table rows
    for test_name in sorted(test_level_data.keys()):
        # Get module name from first available result
        module = ''
        for date in test_dates:
            for batch_name, result in test_level_data[test_name].get(date, {}).items():
                module = result.get('module', '')
                break
            if module:
                break

        # Count statistics
        total_runs = 0
        pass_count = 0
        fail_count = 0

        # Build row
        html_content += f'                        <tr>\n'
        html_content += f'                            <td class="test-name" title="{test_name}">{test_name}</td>\n'
        html_content += f'                            <td class="module-name" title="{module}">{module}</td>\n'

        # Add status for each date
        for date in test_dates:
            status = '-'
            status_class = 'status-none'

            # Check all batches for this date
            for batch_name, result in test_level_data[test_name].get(date, {}).items():
                status = result.get('status', '-')
                total_runs += 1

                if status == 'Pass':
                    pass_count += 1
                    status_class = 'status-pass'
                elif status == 'Fail':
                    fail_count += 1
                    status_class = 'status-fail'
                elif status == 'Skip':
                    status_class = 'status-skip'
                elif status == 'TopoFail':
                    status_class = 'status-topofail'
                elif status == 'ConfigFail':
                    status_class = 'status-configfail'
                break  # Use first batch result

            html_content += f'                            <td><span class="{status_class}">{status}</span></td>\n'

        # Calculate pass rate
        pass_rate = (pass_count / total_runs * 100) if total_runs > 0 else 0
        pass_rate_class = 'pass-rate-high' if pass_rate >= 80 else ('pass-rate-medium' if pass_rate >= 50 else 'pass-rate-low')

        html_content += f'                            <td>{total_runs}</td>\n'
        html_content += f'                            <td>{pass_count}</td>\n'
        html_content += f'                            <td>{fail_count}</td>\n'
        html_content += f'                            <td class="{pass_rate_class}">{pass_rate:.1f}%</td>\n'
        html_content += f'                        </tr>\n'

    html_content += '''                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        function showTab(tabName) {
            // Hide all tabs
            const tabs = document.querySelectorAll('.tab-content');
            tabs.forEach(tab => tab.classList.remove('active'));

            const tabButtons = document.querySelectorAll('.tab');
            tabButtons.forEach(btn => btn.classList.remove('active'));

            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }

        // Chart data
        const dates = ''' + json.dumps(dates) + ''';
        const passRates = ''' + json.dumps(pass_rates) + ''';
        const totalTests = ''' + json.dumps(total_tests) + ''';
        const passedTests = ''' + json.dumps(passed_tests) + ''';
        const failedTests = ''' + json.dumps(failed_tests) + ''';

        // Overview Chart - Stacked Bar
        const overviewCtx = document.getElementById('overviewChart').getContext('2d');
        new Chart(overviewCtx, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Passed',
                        data: passedTests,
                        backgroundColor: 'rgba(40, 167, 69, 0.8)',
                    },
                    {
                        label: 'Failed',
                        data: failedTests,
                        backgroundColor: 'rgba(220, 53, 69, 0.8)',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Test Results Over Time',
                        font: { size: 18 }
                    },
                    legend: {
                        position: 'top',
                    }
                },
                scales: {
                    x: { stacked: true },
                    y: { stacked: true, beginAtZero: true }
                }
            }
        });

        // Pass Rate Chart - Line
        const passRateCtx = document.getElementById('passRateChart').getContext('2d');
        new Chart(passRateCtx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Pass Rate (%)',
                    data: passRates,
                    borderColor: 'rgb(102, 126, 234)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Pass Rate Trend',
                        font: { size: 18 }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });

        // Trend Chart - Combined Line
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        new Chart(trendCtx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Total Tests',
                        data: totalTests,
                        borderColor: 'rgb(102, 126, 234)',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    },
                    {
                        label: 'Passed',
                        data: passedTests,
                        borderColor: 'rgb(40, 167, 69)',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    },
                    {
                        label: 'Failed',
                        data: failedTests,
                        borderColor: 'rgb(220, 53, 69)',
                        backgroundColor: 'rgba(220, 53, 69, 0.1)',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Test Execution Trends',
                        font: { size: 18 }
                    }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });

        // Distribution Chart - Latest Run
        if (passedTests.length > 0) {
            const latest = passedTests.length - 1;
            const distributionCtx = document.getElementById('distributionChart').getContext('2d');
            new Chart(distributionCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Passed', 'Failed'],
                    datasets: [{
                        data: [passedTests[latest], failedTests[latest]],
                        backgroundColor: [
                            'rgba(40, 167, 69, 0.8)',
                            'rgba(220, 53, 69, 0.8)'
                        ]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: 'Latest Run Distribution',
                            font: { size: 18 }
                        },
                        legend: {
                            position: 'bottom'
                        }
                    }
                }
            });
        }

        // Test Details Table Functions
        let currentSortColumn = -1;
        let currentSortAscending = true;

        function filterTests() {
            const searchInput = document.getElementById('testSearch').value.toLowerCase();
            const table = document.getElementById('testDetailsTable');
            const tbody = document.getElementById('testDetailsBody');
            const rows = tbody.getElementsByTagName('tr');
            let visibleCount = 0;

            for (let i = 0; i < rows.length; i++) {
                const testName = rows[i].getElementsByTagName('td')[0];
                if (testName) {
                    const txtValue = testName.textContent || testName.innerText;
                    if (txtValue.toLowerCase().indexOf(searchInput) > -1) {
                        rows[i].style.display = '';
                        visibleCount++;
                    } else {
                        rows[i].style.display = 'none';
                    }
                }
            }

            document.getElementById('testCount').textContent = visibleCount;
        }

        function sortTable(columnIndex) {
            const table = document.getElementById('testDetailsTable');
            const tbody = document.getElementById('testDetailsBody');
            const rows = Array.from(tbody.getElementsByTagName('tr'));
            const headers = table.getElementsByTagName('th');

            // Determine sort direction
            if (currentSortColumn === columnIndex) {
                currentSortAscending = !currentSortAscending;
            } else {
                currentSortAscending = true;
                currentSortColumn = columnIndex;
            }

            // Update header classes
            for (let i = 0; i < headers.length; i++) {
                headers[i].classList.remove('sorted-asc', 'sorted-desc');
            }
            headers[columnIndex].classList.add(currentSortAscending ? 'sorted-asc' : 'sorted-desc');

            // Sort rows
            rows.sort((a, b) => {
                let aValue = a.getElementsByTagName('td')[columnIndex].textContent.trim();
                let bValue = b.getElementsByTagName('td')[columnIndex].textContent.trim();

                // Handle numeric columns (Total Runs, Pass Count, Fail Count, Pass Rate)
                const numericColumns = [''' + str(2 + len(test_dates)) + ''', ''' + str(3 + len(test_dates)) + ''', ''' + str(4 + len(test_dates)) + ''', ''' + str(5 + len(test_dates)) + '''];
                if (numericColumns.includes(columnIndex)) {
                    aValue = parseFloat(aValue) || 0;
                    bValue = parseFloat(bValue) || 0;
                    return currentSortAscending ? (aValue - bValue) : (bValue - aValue);
                }

                // String comparison
                if (currentSortAscending) {
                    return aValue.localeCompare(bValue);
                } else {
                    return bValue.localeCompare(aValue);
                }
            });

            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        }

        // Initialize test count on load
        window.addEventListener('DOMContentLoaded', function() {
            const tbody = document.getElementById('testDetailsBody');
            if (tbody) {
                const rowCount = tbody.getElementsByTagName('tr').length;
                document.getElementById('testCount').textContent = rowCount;
            }
        });
    </script>
</body>
</html>
'''

    # Write to file
    with open(output_file, 'w') as f:
        f.write(html_content)

    print(f"Dashboard generated: {output_file}")
    print(f"Total test runs analyzed: {len(test_runs)}")

def main():
    parser = argparse.ArgumentParser(description='Generate historical test dashboard')
    parser.add_argument('--log-root', required=True, help='Root directory containing test logs')
    parser.add_argument('--out', required=True, help='Output HTML file path')
    parser.add_argument('--name', default='Historical Test Dashboard', help='Dashboard name')

    args = parser.parse_args()

    print(f"Scanning log directory: {args.log_root}")
    test_runs = find_test_runs(args.log_root)

    if not test_runs:
        print("No test runs found!")
        return 1

    print(f"Found {len(test_runs)} test runs")
    generate_html_dashboard(test_runs, args.out, args.name, log_root=args.log_root)

    return 0

if __name__ == "__main__":
    sys.exit(main())
