import os, json, argparse, datetime, csv, glob

def load_db(db_file):
    if not os.path.exists(db_file):
        return []
    with open(db_file) as f:
        return json.load(f)

def save_db(db_file, data):
    with open(db_file, "w") as f:
        json.dump(data, f, indent=2)

def parse_csv_result(csv_file):
    """Parse SPyTest CSV stats file to extract test results and test case details"""
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
                if result == 'Pass':
                    passed += 1
                elif result in ['Fail', 'Failed']:
                    failed += 1
                elif result in ['Skip', 'Skipped']:
                    skipped += 1
    except Exception as e:
        print(f"Warning: Failed to parse {csv_file}: {e}")
        return 0, 0, 0, 0, []

    return total, passed, failed, skipped, test_cases

def parse_result(result_file):
    """Legacy JSON parser - kept for backward compatibility"""
    with open(result_file) as f:
        data = json.load(f)
    total = data.get("summary", {}).get("total", 0)
    passed = data.get("summary", {}).get("pass", 0)
    failed = data.get("summary", {}).get("fail", 0)
    skipped = data.get("summary", {}).get("skip", 0)
    return total, passed, failed, skipped

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logs", required=True)
    ap.add_argument("--db", required=True)
    args = ap.parse_args()

    db = load_db(args.db)
    seen = {(e["log_path"]) for e in db}

    for date in os.listdir(args.logs):
        dpath = os.path.join(args.logs, date)
        if not os.path.isdir(dpath):
            continue

        for feature in os.listdir(dpath):
            fpath = os.path.join(dpath, feature)
            if not os.path.isdir(fpath):
                continue

            for run in os.listdir(fpath):
                rpath = os.path.join(fpath, run)
                if not os.path.isdir(rpath):
                    continue
                if rpath in seen:
                    continue

                # Try to find SPyTest CSV stats file first
                csv_files = glob.glob(os.path.join(rpath, "results_*_stats.csv"))
                test_cases = []
                if csv_files:
                    # Use the first CSV file found
                    csv_file = csv_files[0]
                    total, passed, failed, skipped, test_cases = parse_csv_result(csv_file)
                else:
                    # Fall back to JSON format (legacy)
                    result_file = os.path.join(rpath, "results_all.json")
                    if not os.path.exists(result_file):
                        continue
                    total, passed, failed, skipped = parse_result(result_file)

                # Only add if we found some test results
                if total > 0:
                    db.append({
                        "date": date,
                        "feature": feature,
                        "time": run,
                        "total": total,
                        "passed": passed,
                        "failed": failed,
                        "skipped": skipped,
                        "log_path": rpath,
                        "test_cases": test_cases
                    })

    save_db(args.db, db)
    print("Result DB updated. Entries:", len(db))

if __name__ == "__main__":
    main()

