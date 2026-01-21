import os, json, argparse, datetime

def load_db(db_file):
    if not os.path.exists(db_file):
        return []
    with open(db_file) as f:
        return json.load(f)

def save_db(db_file, data):
    with open(db_file, "w") as f:
        json.dump(data, f, indent=2)

def parse_result(result_file):
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
                if rpath in seen:
                    continue

                result_file = os.path.join(rpath, "results_all.json")
                if not os.path.exists(result_file):
                    continue

                total, passed, failed, skipped = parse_result(result_file)

                db.append({
                    "date": date,
                    "feature": feature,
                    "time": run,
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "skipped": skipped,
                    "log_path": rpath
                })

    save_db(args.db, db)
    print("Result DB updated. Entries:", len(db))

if __name__ == "__main__":
    main()

