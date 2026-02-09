#!/usr/bin/env python3
"""
Test Details Report Generator
Generates a detailed CSV report showing which tests passed/failed on each date
"""

import os
import sys
import glob
import argparse
import re
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def parse_time_duration(time_str):
    """Parse time format H:MM:SS or MM:SS to seconds"""
    try:
        if isinstance(time_str, (int, float)):
            return float(time_str)
        parts = str(time_str).split(':')
        if len(parts) == 3:  # H:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        else:
            return float(time_str)
    except:
        return 0.0

def find_test_runs(log_root):
    """Scan log directories and collect all test runs with test details"""
    test_data = defaultdict(lambda: defaultdict(dict))  # {test_name: {date: {batch: result}}}
    dates = set()
    batches = set()

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
            batches.add(batch_name)

            # Find timestamp subdirectories
            time_dirs = [d for d in batch_dir.iterdir() if d.is_dir()]

            for time_dir in time_dirs:
                # Look for result CSV files
                csv_files = list(time_dir.glob("*_functions.csv"))

                if csv_files:
                    try:
                        with open(csv_files[0], 'r') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                test_name = row.get('TestFunction', row.get('Function', row.get('TestCase', '')))

                                # Skip empty test names (Module Prolog/Epilog rows)
                                if not test_name or test_name.strip() == '':
                                    continue

                                status = row.get('Result', row.get('Status', 'Unknown'))

                                # Skip rows with empty status
                                if not status or status.strip() == '':
                                    continue

                                duration_str = row.get('TimeTaken', row.get('Duration', '0'))
                                duration = parse_time_duration(duration_str)
                                module = row.get('Module', row.get('TestModule', ''))

                                # Store test result
                                test_data[test_name][date][batch_name] = {
                                    'status': status,
                                    'duration': duration,
                                    'module': module
                                }
                    except Exception as e:
                        print(f"Error parsing {csv_files[0]}: {e}")

    return test_data, sorted(dates), sorted(batches)

def generate_detailed_report(log_root, output_file):
    """Generate detailed CSV report of test results"""
    print(f"Scanning log directory: {log_root}")
    test_data, dates, batches = find_test_runs(log_root)

    print(f"Found {len(test_data)} unique tests across {len(dates)} dates")

    # Generate CSV report
    with open(output_file, 'w', newline='') as csvfile:
        # Create header
        fieldnames = ['Test Name', 'Module'] + [f"{date}" for date in dates] + ['Total Runs', 'Pass Count', 'Fail Count', 'Pass Rate (%)']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        # Write test data
        for test_name in sorted(test_data.keys()):
            row = {'Test Name': test_name}

            # Get module name from first available result
            module = ''
            for date in dates:
                for batch in batches:
                    if date in test_data[test_name] and batch in test_data[test_name][date]:
                        module = test_data[test_name][date][batch].get('module', '')
                        break
                if module:
                    break
            row['Module'] = module

            # Count statistics
            total_runs = 0
            pass_count = 0
            fail_count = 0

            # Fill in results for each date
            for date in dates:
                result_str = '-'
                for batch in batches:
                    if date in test_data[test_name] and batch in test_data[test_name][date]:
                        status = test_data[test_name][date][batch]['status']
                        result_str = status
                        total_runs += 1
                        if status == 'Pass':
                            pass_count += 1
                        elif status == 'Fail':
                            fail_count += 1
                        break

                row[f"{date}"] = result_str

            # Calculate pass rate
            pass_rate = (pass_count / total_runs * 100) if total_runs > 0 else 0

            row['Total Runs'] = total_runs
            row['Pass Count'] = pass_count
            row['Fail Count'] = fail_count
            row['Pass Rate (%)'] = f"{pass_rate:.1f}"

            writer.writerow(row)

    print(f"\nDetailed report generated: {output_file}")
    print(f"Total unique tests: {len(test_data)}")
    print(f"Date range: {dates[0] if dates else 'N/A'} to {dates[-1] if dates else 'N/A'}")

def main():
    parser = argparse.ArgumentParser(description='Generate detailed test results report')
    parser.add_argument('--log-root', required=True, help='Root directory containing test logs')
    parser.add_argument('--out', required=True, help='Output CSV file path')

    args = parser.parse_args()

    generate_detailed_report(args.log_root, args.out)

if __name__ == '__main__':
    main()
