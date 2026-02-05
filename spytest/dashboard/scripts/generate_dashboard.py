import json, argparse, collections

HTML_HEAD = """
<html>
<head>
<title>SONiC Regression Dashboard - Detailed View</title>
<style>
body { font-family: Arial, sans-serif; margin:20px; background:#f5f5f5; }
h1 { color:#333; border-bottom:3px solid #0066cc; padding-bottom:10px; }
h2 { color:#0066cc; margin-top:30px; border-bottom:2px solid #ccc; padding-bottom:5px; }
.summary-table { border-collapse: collapse; margin-bottom:20px; background:white; box-shadow:0 2px 4px rgba(0,0,0,0.1); }
.summary-table th { background:#0066cc; color:white; padding:10px; text-align:left; }
.summary-table td { border:1px solid #ddd; padding:8px 12px; }
.detail-table { border-collapse: collapse; margin:10px 0 30px 20px; background:white; width:calc(100% - 40px); box-shadow:0 2px 4px rgba(0,0,0,0.1); }
.detail-table th { background:#4CAF50; color:white; padding:8px; text-align:left; font-size:14px; }
.detail-table td { border:1px solid #ddd; padding:6px 10px; font-size:13px; }
.detail-table tr:hover { background:#f9f9f9; }
.pass { color:green; font-weight:bold; }
.fail { color:red; font-weight:bold; }
.skip { color:orange; font-weight:bold; }
.run-header { background:#f0f0f0; padding:10px; margin:10px 0; border-left:4px solid #0066cc; }
.test-function { font-family:monospace; color:#333; }
.test-module { font-size:12px; color:#666; }
</style>
</head>
<body>
<h1>SONiC Regression Dashboard - Detailed Test Results</h1>
<p style="color:#666; font-size:14px;">Comprehensive test results with detailed test case listings</p>
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

        for r in sorted(runs, key=lambda x: (x["date"], x["time"]), reverse=True):
            cls = "pass" if r["failed"] == 0 else "fail"

            # Summary table for this run
            html += f"<div class='run-header'><strong>Run:</strong> {r['date']} at {r['time']}</div>\n"
            html += "<table class='summary-table'>\n"
            html += "<tr><th>Total</th><th>Pass</th><th>Fail</th><th>Skip</th><th>Logs</th></tr>\n"
            html += (
                f"<tr>"
                f"<td>{r['total']}</td>"
                f"<td class='pass'>{r['passed']}</td>"
                f"<td class='{cls}'>{r['failed']}</td>"
                f"<td class='skip'>{r['skipped']}</td>"
                f"<td><a href='../{r['log_path']}/index.html' target='_blank'>Open Logs</a></td>"
                f"</tr>\n"
            )
            html += "</table>\n"

            # Detailed test cases table
            test_cases = r.get("test_cases", [])
            if test_cases:
                html += "<table class='detail-table'>\n"
                html += "<tr><th>Test Function</th><th>Module</th><th>Result</th><th>Time</th><th>Description</th></tr>\n"
                for tc in test_cases:
                    result = tc.get('result', '')
                    result_class = 'pass' if result == 'Pass' else ('fail' if result in ['Fail', 'Failed'] else 'skip')
                    module = tc.get('module', '')
                    function = tc.get('function', '')
                    test_time = tc.get('test_time', '')
                    description = tc.get('description', '')

                    html += (
                        f"<tr>"
                        f"<td class='test-function'>{function}</td>"
                        f"<td class='test-module'>{module}</td>"
                        f"<td class='{result_class}'>{result}</td>"
                        f"<td>{test_time}</td>"
                        f"<td>{description}</td>"
                        f"</tr>\n"
                    )
                html += "</table>\n"

    html += HTML_TAIL

    with open(args.out, "w") as f:
        f.write(html)

    print("Dashboard generated:", args.out)

if __name__ == "__main__":
    main()

