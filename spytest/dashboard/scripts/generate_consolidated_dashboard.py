#!/usr/bin/env python3
"""
Generate Consolidated Dashboard for SM_ISCLI Tests
Creates a tabbed dashboard showing test results across multiple dates/runs
Similar to consolidated_dashboard_Feb_26.html format
"""

import os
import sys
import glob
import argparse
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            font-size: 12px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 26px;
            margin-bottom: 8px;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 13px;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 15px;
        }}
        .tabs {{
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 15px;
        }}
        .tab-nav {{
            display: flex;
            flex-wrap: wrap;
            background: #f8f9fa;
            border-bottom: 2px solid #e0e0e0;
            overflow-x: auto;
            max-height: 120px;
            overflow-y: auto;
        }}
        .tab-button {{
            padding: 10px 18px;
            border: none;
            background: transparent;
            cursor: pointer;
            font-size: 11px;
            font-weight: 600;
            color: #666;
            transition: all 0.3s ease;
            border-bottom: 2px solid transparent;
            white-space: nowrap;
        }}
        .tab-button:hover {{
            background: #e9ecef;
            color: #667eea;
        }}
        .tab-button.active {{
            color: #667eea;
            background: white;
            border-bottom-color: #667eea;
        }}
        .tab-content {{
            display: none;
            padding: 15px;
            max-height: calc(100vh - 200px);
            overflow-y: auto;
        }}
        .tab-content.active {{
            display: block;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 6px;
            overflow: hidden;
            font-size: 11px;
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 8px;
            text-align: left;
            font-weight: 600;
            position: sticky;
            top: 0;
            z-index: 10;
        }}
        td {{
            padding: 8px;
            border-bottom: 1px solid #f0f0f0;
        }}
        tr:hover {{
            background: #f8f9ff;
        }}
        .pass {{
            color: #28a745;
            font-weight: bold;
        }}
        .fail {{
            color: #dc3545;
            font-weight: bold;
        }}
        .skip {{
            color: #ffc107;
            font-weight: bold;
        }}
        .summary-box {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .summary-box h3 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 14px;
        }}
        .summary-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
        }}
        .stat-card {{
            padding: 10px;
            border-radius: 4px;
            text-align: center;
        }}
        .stat-card.pass-card {{
            background: #d4edda;
            color: #155724;
        }}
        .stat-card.fail-card {{
            background: #f8d7da;
            color: #721c24;
        }}
        .stat-card.skip-card {{
            background: #fff3cd;
            color: #856404;
        }}
        .stat-card .count {{
            font-size: 24px;
            font-weight: bold;
        }}
        .stat-card .label {{
            font-size: 10px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <p>{subtitle}</p>
    </div>
    <div class="container">
        <div class="tabs">
            <div class="tab-nav">
{tab_buttons}
            </div>
{tab_contents}
        </div>
    </div>
    <script>
        function openTab(evt, tabName) {{
            var i, tabcontent, tabbuttons;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].classList.remove("active");
            }}
            tabbuttons = document.getElementsByClassName("tab-button");
            for (i = 0; i < tabbuttons.length; i++) {{
                tabbuttons[i].classList.remove("active");
            }}
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }}
        // Activate first tab
        document.addEventListener('DOMContentLoaded', function() {{
            var firstButton = document.querySelector('.tab-button');
            if (firstButton) {{
                firstButton.click();
            }}
        }});
    </script>
</body>
</html>
"""


def parse_results_summary(summary_file):
    """Parse SPyTest summary.txt file"""
    try:
        results = {}
        with open(summary_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key in ['PASS', 'FAIL', 'SKIPPED']:
                        results[key.lower()] = int(value)
                    elif key == 'Execution Time':
                        results['execution_time'] = value
        return results if results else None
    except Exception as e:
        print(f"Error parsing {summary_file}: {e}")
        return None


def collect_test_runs(log_root):
    """
    Collect all test runs from SM_ISCLI_Report directory
    Structure: ./logs/SM_ISCLI_Report/SM_ISCLI_YYYYMMDD/BATCH_NAME/HHMMSS/results_*_summary.txt
    """
    runs_by_date = defaultdict(lambda: defaultdict(list))

    # Find all date directories
    sm_iscli_pattern = os.path.join(log_root, "SM_ISCLI_*")
    date_dirs = sorted(glob.glob(sm_iscli_pattern))

    for date_dir in date_dirs:
        if not os.path.isdir(date_dir):
            continue

        date_name = os.path.basename(date_dir)  # SM_ISCLI_20260301
        date_str = date_name.replace("SM_ISCLI_", "")  # 20260301

        # Find all batch directories
        batch_dirs = glob.glob(os.path.join(date_dir, "*"))
        for batch_dir in batch_dirs:
            if not os.path.isdir(batch_dir):
                continue

            batch_name = os.path.basename(batch_dir)

            # Find all time-stamped run directories
            time_dirs = glob.glob(os.path.join(batch_dir, "*"))
            for time_dir in time_dirs:
                if not os.path.isdir(time_dir):
                    continue

                # Look for results_*_summary.txt files
                summary_files = glob.glob(os.path.join(time_dir, "results_*_summary.txt"))
                if summary_files:
                    # Use the first summary file found
                    results = parse_results_summary(summary_files[0])
                    if results:
                        runs_by_date[date_str][batch_name].append({
                            'time': os.path.basename(time_dir),
                            'results': results,
                            'path': time_dir
                        })

    return runs_by_date


def generate_summary_stats(batch_runs):
    """Generate summary statistics for a batch"""
    total_pass = 0
    total_fail = 0
    total_skip = 0

    for run in batch_runs:
        results = run['results']
        total_pass += results.get('pass', 0)
        total_fail += results.get('fail', 0)
        total_skip += results.get('skip', 0)

    return total_pass, total_fail, total_skip


def generate_tab_content(date_str, batches_data):
    """Generate HTML content for a single date tab"""
    content = f'            <div id="tab-{date_str}" class="tab-content">\n'

    # Summary for this date
    date_total_pass = 0
    date_total_fail = 0
    date_total_skip = 0

    for batch_name, runs in batches_data.items():
        p, f, s = generate_summary_stats(runs)
        date_total_pass += p
        date_total_fail += f
        date_total_skip += s

    # Summary box
    content += '                <div class="summary-box">\n'
    content += f'                    <h3>Test Summary for {date_str}</h3>\n'
    content += '                    <div class="summary-stats">\n'
    content += f'                        <div class="stat-card pass-card"><div class="count">{date_total_pass}</div><div class="label">PASSED</div></div>\n'
    content += f'                        <div class="stat-card fail-card"><div class="count">{date_total_fail}</div><div class="label">FAILED</div></div>\n'
    content += f'                        <div class="stat-card skip-card"><div class="count">{date_total_skip}</div><div class="label">SKIPPED</div></div>\n'
    content += '                    </div>\n'
    content += '                </div>\n'

    # Table for all batches
    content += '                <table>\n'
    content += '                    <thead>\n'
    content += '                        <tr>\n'
    content += '                            <th>Batch Name</th>\n'
    content += '                            <th>Time</th>\n'
    content += '                            <th>Pass</th>\n'
    content += '                            <th>Fail</th>\n'
    content += '                            <th>Skip</th>\n'
    content += '                            <th>Total</th>\n'
    content += '                            <th>Duration</th>\n'
    content += '                            <th>Pass Rate</th>\n'
    content += '                        </tr>\n'
    content += '                    </thead>\n'
    content += '                    <tbody>\n'

    for batch_name in sorted(batches_data.keys()):
        runs = batches_data[batch_name]
        for run in runs:
            results = run['results']
            passed = results.get('pass', 0)
            failed = results.get('fail', 0)
            skipped = results.get('skip', 0)
            total = passed + failed + skipped
            duration = results.get('execution_time', 'N/A')

            pass_rate = f"{(passed / total * 100):.1f}%" if total > 0 else "N/A"

            content += '                        <tr>\n'
            content += f'                            <td><strong>{batch_name}</strong></td>\n'
            content += f'                            <td>{run["time"]}</td>\n'
            content += f'                            <td class="pass">{passed}</td>\n'
            content += f'                            <td class="fail">{failed}</td>\n'
            content += f'                            <td class="skip">{skipped}</td>\n'
            content += f'                            <td>{total}</td>\n'
            content += f'                            <td>{duration}</td>\n'
            content += f'                            <td>{pass_rate}</td>\n'
            content += '                        </tr>\n'

    content += '                    </tbody>\n'
    content += '                </table>\n'
    content += '            </div>\n'

    return content


def main():
    parser = argparse.ArgumentParser(
        description='Generate Consolidated Dashboard for SM_ISCLI Tests'
    )
    parser.add_argument('--log-root', required=True,
                        help='Root directory containing SM_ISCLI logs (e.g., logs/SM_ISCLI_Report)')
    parser.add_argument('--out', required=True,
                        help='Output HTML file path')
    parser.add_argument('--name', default='SM_ISCLI Consolidated Dashboard',
                        help='Dashboard title')

    args = parser.parse_args()

    print(f"Collecting test runs from: {args.log_root}")
    runs_by_date = collect_test_runs(args.log_root)

    if not runs_by_date:
        print("No test runs found!")
        return 1

    print(f"Found {len(runs_by_date)} test dates")

    # Generate tab buttons
    tab_buttons = ""
    for date_str in sorted(runs_by_date.keys(), reverse=True):
        batch_count = len(runs_by_date[date_str])
        tab_buttons += f'                <button class="tab-button" onclick="openTab(event, \'tab-{date_str}\')">{date_str} ({batch_count} batches)</button>\n'

    # Generate tab contents
    tab_contents = ""
    for date_str in sorted(runs_by_date.keys(), reverse=True):
        batches_data = runs_by_date[date_str]
        tab_contents += generate_tab_content(date_str, batches_data)

    # Generate final HTML
    total_runs = sum(len(batches) for batches in runs_by_date.values())
    subtitle = f"Consolidated view of {total_runs} test batches across {len(runs_by_date)} dates"

    html = HTML_TEMPLATE.format(
        title=args.name,
        subtitle=subtitle,
        tab_buttons=tab_buttons,
        tab_contents=tab_contents
    )

    # Write output
    os.makedirs(os.path.dirname(args.out) if os.path.dirname(args.out) else '.', exist_ok=True)
    with open(args.out, 'w') as f:
        f.write(html)

    print(f"Dashboard generated: {args.out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
