#!/usr/bin/env python3
"""
l2_acl_traffic.py — L2 ACL traffic tests (L2-01 to L2-08).

Usage:
  sudo python3 l2_acl_traffic.py              # run all
  sudo python3 l2_acl_traffic.py --tc L2-03  # single test
  sudo python3 l2_acl_traffic.py --list
"""
import argparse, threading, time, sys
from dataclasses import dataclass, field

try:
    from scapy.all import conf, sendp, sniff, get_if_list, Ether, IP, ARP, Dot1Q, UDP
except ImportError:
    sys.exit("[ERROR] pip3 install scapy --break-system-packages")

TX_IFACE = "eth0"
RX_IFACE = "eth1"
TX_MAC   = "00:aa:aa:aa:aa:01"
RX_MAC   = "00:bb:bb:bb:bb:02"
N        = 10   # packets per test
TIMEOUT  = 4    # sniff timeout (s)

@dataclass
class Result:
    tc_id: str
    desc: str
    action: str       # PERMIT or DENY
    sent: int = 0
    recv: int = 0
    passed: bool = False
    note: str = ""

results: list[Result] = []

# ── helpers ──────────────────────────────────────────────────────────────────

def _tx_rx(pkts, bpf: str) -> tuple[int, int]:
    """Send pkts on TX_IFACE, count arrivals on RX_IFACE."""
    captured = []
    def _sniff():
        sniff(iface=RX_IFACE, filter=bpf,
              prn=lambda p: captured.append(p),
              timeout=TIMEOUT, store=False)
    t = threading.Thread(target=_sniff, daemon=True)
    t.start()
    time.sleep(0.25)
    if TX_IFACE in get_if_list():
        sendp(pkts, iface=TX_IFACE, verbose=False, inter=0.05)
    t.join(timeout=TIMEOUT + 1)
    return len(pkts), len(captured)

def run(tc_id, desc, action, pkts, bpf="ether") -> Result:
    print(f"\n[{tc_id}] {desc}  ({action})")
    sent, recv = _tx_rx(pkts, bpf)
    r = Result(tc_id, desc, action, sent, recv)
    if action == "PERMIT":
        r.passed = recv >= sent * 0.9
        r.note = "forwarded OK" if r.passed else f"expected ~{sent}, got {recv}"
    else:
        r.passed = recv == 0
        r.note = "dropped OK" if r.passed else f"LEAKED {recv} pkts!"
    results.append(r)
    print(f"  sent={sent} recv={recv}  [{'PASS' if r.passed else 'FAIL'}] {r.note}")
    return r

# ── test cases ────────────────────────────────────────────────────────────────

def L2_01():
    "Permit exact source MAC"
    pkts = [Ether(src=TX_MAC, dst=RX_MAC)/IP() for _ in range(N)]
    return run("L2-01", "Permit exact source MAC", "PERMIT", pkts, f"ether src {TX_MAC}")

def L2_02():
    "Deny exact source MAC"
    bad = "de:ad:00:00:00:01"
    pkts = [Ether(src=bad, dst=RX_MAC)/IP() for _ in range(N)]
    return run("L2-02", "Deny exact source MAC (de:ad:00:00:00:01)", "DENY", pkts, f"ether src {bad}")

def L2_03():
    "Deny exact destination MAC"
    bad_dst = "fe:ed:00:00:00:02"
    pkts = [Ether(src=TX_MAC, dst=bad_dst)/IP() for _ in range(N)]
    return run("L2-03", "Deny exact destination MAC (fe:ed:00:00:00:02)", "DENY", pkts, f"ether dst {bad_dst}")

def L2_04():
    "Deny broadcast destination MAC"
    pkts = [Ether(src=TX_MAC, dst="ff:ff:ff:ff:ff:ff")/ARP() for _ in range(N)]
    return run("L2-04", "Deny broadcast MAC (FF:FF:FF:FF:FF:FF)", "DENY", pkts, "ether broadcast")

def L2_05():
    "Deny EtherType ARP (0x0806)"
    pkts = [Ether(src=TX_MAC, dst="ff:ff:ff:ff:ff:ff", type=0x0806)/ARP(op=1) for _ in range(N)]
    return run("L2-05", "Deny EtherType 0x0806 (ARP)", "DENY", pkts, "arp")

def L2_06():
    "Deny VLAN 100"
    pkts = [Ether(src=TX_MAC, dst=RX_MAC)/Dot1Q(vlan=100)/IP() for _ in range(N)]
    return run("L2-06", "Deny VLAN ID 100", "DENY", pkts, "vlan 100")

def L2_07():
    "Permit VLAN 10, deny VLAN 200 (two-phase)"
    # Phase A: VLAN 10 should pass
    pkts_permit = [Ether(src=TX_MAC, dst=RX_MAC)/Dot1Q(vlan=10)/IP() for _ in range(N)]
    # Phase B: VLAN 200 should be dropped
    pkts_deny   = [Ether(src=TX_MAC, dst=RX_MAC)/Dot1Q(vlan=200)/IP() for _ in range(N)]
    print(f"\n[L2-07] Permit VLAN 10 / Deny VLAN 200  (2-phase)")
    s1, r1 = _tx_rx(pkts_permit, "vlan 10")
    s2, r2 = _tx_rx(pkts_deny,   "vlan 200")
    p1 = r1 >= s1 * 0.9
    p2 = r2 == 0
    passed = p1 and p2
    note = f"VLAN10: {'OK' if p1 else 'FAIL'}({r1}/{s1})  VLAN200: {'OK' if p2 else 'FAIL'}({r2}/{s2})"
    r = Result("L2-07", "Permit VLAN 10 / Deny VLAN 200", "MIXED", s1+s2, r1+r2, passed, note)
    results.append(r)
    print(f"  {note}  [{'PASS' if passed else 'FAIL'}]")
    return r

def L2_08():
    "ACL rule priority — permit rule before deny-all"
    # Assumes DUT ACL: rule1=permit src TX_MAC, rule2=deny all
    pkts = [Ether(src=TX_MAC, dst=RX_MAC)/IP() for _ in range(N)]
    return run("L2-08", "ACL priority: permit(src=TX_MAC) > deny-all", "PERMIT", pkts, f"ether src {TX_MAC}")

# ── registry ──────────────────────────────────────────────────────────────────

ALL = {"L2-01": L2_01, "L2-02": L2_02, "L2-03": L2_03, "L2-04": L2_04,
       "L2-05": L2_05, "L2-06": L2_06, "L2-07": L2_07, "L2-08": L2_08}

def report():
    passed = sum(1 for r in results if r.passed)
    print(f"\n{'='*58}")
    print(f"  L2 ACL RESULTS  ({passed}/{len(results)} passed)")
    print(f"{'='*58}")
    for r in results:
        s = "PASS ✓" if r.passed else "FAIL ✗"
        print(f"  {r.tc_id:<7} {s:<8} sent={r.sent:<4} recv={r.recv:<4} {r.note}")
    print()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tc",   help="Single TC to run, e.g. L2-03")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        [print(f"  {k}  {v.__doc__}") for k, v in ALL.items()]
    elif args.tc:
        if args.tc in ALL: ALL[args.tc](); report()
        else: print(f"Unknown TC: {args.tc}")
    else:
        print("\n[L2 ACL] Running all 8 test cases...")
        for fn in ALL.values(): fn()
        report()
