#!/usr/bin/env python3
"""
acl_test_runner.py — Master Test Runner for L2 and L3 ACL Test Suites

This script orchestrates the execution of both L2 and L3 ACL test cases, providing
consolidated reporting and filtering capabilities.

Architecture:
  - Executes test cases in l2_acl_traffic.py and l3_acl_traffic.py
  - Runs on external TX/RX hosts (not on DUT)
  - Generates summary report with pass/fail counts

Test Suites:
  - L2 ACL: 8 test cases (MAC address, EtherType, VLAN matching)
  - L3 ACL: 12 test cases (IP address, protocol, TCP flags, 5-tuple, DSCP)

Prerequisites:
  1. External TX and RX hosts configured (see host_setup.md)
  2. DUT Port1 and Port2 configured with L3 addressing (see dut_setup.md)
  3. Scapy installed: sudo pip3 install scapy --break-system-packages
  4. Raw socket permissions: run with sudo or grant CAP_NET_RAW

Usage Examples:
  # Run all tests (L2 + L3)
  sudo python3 acl_test_runner.py

  # Run L3 tests only
  sudo python3 acl_test_runner.py --suite l3

  # Skip hardware-only tests
  sudo python3 acl_test_runner.py --skip-hw

  # Run specific test cases
  sudo python3 acl_test_runner.py --tc L3-01,L3-04,L2-02

  # Preview tests without running
  sudo python3 acl_test_runner.py --dry-run

Output:
  - Console report with per-test status (PASS/FAIL/SKIP)
  - Summary statistics: total, passed, failed, skipped
  - List of failed tests for quick troubleshooting

Test Metadata:
  - Tags: VS (Virtual SONiC-VS), HW (Hardware ASIC), B (Both)
  - HW-only tests (tagged HW) can be skipped with --skip-hw for VS testing

Important Notes:
  - All tests are UNIDIRECTIONAL: TX → DUT → RX
  - Pass criteria: PERMIT tests require ≥90% packet delivery; DENY tests require 0% delivery
  - Each test configures its own ACL rules; DUT ACL state restored between tests
  - Negative (NEG) and Robustness (R) test variants available (run individual suites for full coverage)
"""
import argparse, subprocess, sys, time
from datetime import datetime

# ── test metadata ─────────────────────────────────────────────────────────────
META = {
    "L2-01": {"suite":"l2","hw":False,"desc":"Permit exact source MAC"},
    "L2-02": {"suite":"l2","hw":False,"desc":"Deny exact source MAC"},
    "L2-03": {"suite":"l2","hw":False,"desc":"Deny exact destination MAC"},
    "L2-04": {"suite":"l2","hw":False,"desc":"Deny broadcast MAC"},
    "L2-05": {"suite":"l2","hw":False,"desc":"Deny EtherType ARP (0x0806)"},
    "L2-06": {"suite":"l2","hw":False,"desc":"Deny VLAN 100"},
    "L2-07": {"suite":"l2","hw":False,"desc":"Permit VLAN 10 / deny VLAN 200"},
    "L2-08": {"suite":"l2","hw":False,"desc":"ACL rule priority (permit before deny)"},
    "L3-01": {"suite":"l3","hw":False,"desc":"Deny source IP host"},
    "L3-02": {"suite":"l3","hw":False,"desc":"Deny source subnet /24"},
    "L3-03": {"suite":"l3","hw":False,"desc":"Deny destination IP host"},
    "L3-04": {"suite":"l3","hw":False,"desc":"Deny ICMP"},
    "L3-05": {"suite":"l3","hw":False,"desc":"Deny UDP / permit TCP"},
    "L3-06": {"suite":"l3","hw":False,"desc":"Deny TCP dst port 80"},
    "L3-07": {"suite":"l3","hw":False,"desc":"Deny UDP dst port 53 (DNS)"},
    "L3-08": {"suite":"l3","hw":False,"desc":"Deny TCP SYN"},
    "L3-09": {"suite":"l3","hw":False,"desc":"Permit TCP ACK (established)"},
    "L3-10": {"suite":"l3","hw":False,"desc":"Deny 5-tuple flow"},
    "L3-11": {"suite":"l3","hw":False,"desc":"Implicit deny-all"},
    "L3-12": {"suite":"l3","hw":True, "desc":"Deny DSCP EF (HW only)"},
}

SCRIPT = {"l2": "l2_acl_traffic.py", "l3": "l3_acl_traffic.py"}

# ── filter ────────────────────────────────────────────────────────────────────

def select(suite="all", skip_hw=False, tc_list=None):
    out = []
    for tc, m in META.items():
        if tc_list and tc not in tc_list: continue
        if suite != "all" and m["suite"] != suite: continue
        if skip_hw and m["hw"]: continue
        out.append(tc)
    return out

# ── run ───────────────────────────────────────────────────────────────────────

def run_tc(tc_id):
    m = META[tc_id]
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, SCRIPT[m["suite"]], "--tc", tc_id],
        capture_output=True, text=True
    )
    elapsed = time.time() - t0
    out = proc.stdout + proc.stderr
    passed  = "PASS" in out and "FAIL" not in out.split("PASS")[0]
    # More reliable: look for the result line
    passed = "[PASS]" in out or "PASS ✓" in out
    failed = "[FAIL]" in out or "FAIL ✗" in out
    if failed: passed = False
    skipped = "SKIP" in out
    return {"tc": tc_id, "passed": passed, "skipped": skipped,
            "elapsed": elapsed, "out": out}

# ── report ────────────────────────────────────────────────────────────────────

def report(results, suite, skip_hw):
    total   = len(results)
    passed  = sum(1 for r in results if r["passed"] and not r["skipped"])
    failed  = sum(1 for r in results if not r["passed"] and not r["skipped"])
    skipped = sum(1 for r in results if r["skipped"])

    print(f"\n{'='*65}")
    print(f"  ACL TEST REPORT  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Suite: {suite.upper():<5}  Skip-HW: {skip_hw}")
    print(f"{'='*65}")
    print(f"  {'TC':<8} {'TAG':<5} {'RESULT':<8} {'TIME':<6} DESCRIPTION")
    print(f"  {'-'*8} {'-'*5} {'-'*8} {'-'*6} {'-'*32}")
    for r in results:
        m  = META[r["tc"]]
        tag = "HW" if m["hw"] else "VS"
        if r["skipped"]: st = "SKIP  "
        elif r["passed"]: st = "PASS ✓"
        else: st = "FAIL ✗"
        print(f"  {r['tc']:<8} {tag:<5} {st:<8} {r['elapsed']:.1f}s  {m['desc']}")

    print(f"\n  Total={total}  Passed={passed}  Failed={failed}  Skipped={skipped}")
    if failed:
        print("\n  Failed:")
        for r in results:
            if not r["passed"] and not r["skipped"]:
                print(f"    ✗ {r['tc']}  {META[r['tc']]['desc']}")
    print()

# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite",   default="all", choices=["all","l2","l3"])
    ap.add_argument("--skip-hw", action="store_true", help="Skip HW-only cases")
    ap.add_argument("--tc",      help="Comma-separated TC IDs")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tc_list  = [t.strip() for t in args.tc.split(",")] if args.tc else None
    selected = select(args.suite, args.skip_hw, tc_list)

    if not selected:
        print("No tests matched."); sys.exit(0)

    if args.dry_run:
        print(f"\nDry run — {len(selected)} tests selected:")
        for tc in selected:
            m = META[tc]
            print(f"  {tc:<8} {'HW' if m['hw'] else 'VS':<3} {m['desc']}")
        print(); sys.exit(0)

    print(f"\n[ACL RUNNER] {len(selected)} tests  suite={args.suite}  skip_hw={args.skip_hw}")
    print("─" * 50)

    all_results = []
    for tc in selected:
        m = META[tc]
        result = run_tc(tc)
        all_results.append(result)
        st = "SKIP" if result["skipped"] else ("PASS" if result["passed"] else "FAIL")
        print(f"  [{st}] {tc:<8} {m['desc']}")

    report(all_results, args.suite, args.skip_hw)
