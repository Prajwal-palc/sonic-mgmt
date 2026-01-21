import json, argparse, collections

HTML_HEAD = """
<html>
<head>
<title>SONiC Regression Dashboard</title>
<style>
body { font-family: Arial; margin:20px; }
table { border-collapse: collapse; margin-bottom:30px; }
th,td { border:1px solid #ccc; padding:6px 10px; }
th { background:#eee; }
.pass { color:green; font-weight:bold; }
.fail { color:red; font-weight:bold; }
</style>
</head>
<body>
<h1>SONiC Regression Historical Dashboard</h1>
"""

HTML_TAIL = "</body></html>"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.db) as f:
        db = json.load(f)

    by_feature = collections.defaultdict(list)
    for r in db:
        by_feature[r["feature"]].append(r)

    html = HTML_HEAD

    for feature, runs in sorted(by_feature.items()):
        html += f"<h2>{feature}</h2>\n"
        html += "<table>\n<tr><th>Date</th><th>Time</th><th>Total</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Logs</th></tr>\n"
        for r in sorted(runs, key=lambda x: (x["date"], x["time"]), reverse=True):
            cls = "pass" if r["failed"] == 0 else "fail"
            html += (
                f"<tr>"
                f"<td>{r['date']}</td>"
                f"<td>{r['time']}</td>"
                f"<td>{r['total']}</td>"
                f"<td class='pass'>{r['passed']}</td>"
                f"<td class='{cls}'>{r['failed']}</td>"
                f"<td>{r['skipped']}</td>"
                f"<td><a href='../{r['log_path']}/index.html'>Open</a></td>"
                f"</tr>\n"
            )
        html += "</table>\n"

    html += HTML_TAIL

    with open(args.out, "w") as f:
        f.write(html)

    print("Dashboard generated:", args.out)

if __name__ == "__main__":
    main()

