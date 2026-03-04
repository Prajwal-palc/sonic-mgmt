#!/usr/bin/env python3
"""
l3_acl_traffic.py — L3 ACL traffic tests (L3-01 to L3-12).

Usage:
  sudo python3 l3_acl_traffic.py              # run all
  sudo python3 l3_acl_traffic.py --tc L3-04  # single test
  sudo python3 l3_acl_traffic.py --list
"""
import argparse, threading, time, sys
from dataclasses import dataclass

try:
    from scapy.all import conf, sendp, sniff, get_if_list, Ether, IP, TCP, UDP, ICMP
except ImportError:
    sys.exit("[ERROR] pip3 install scapy --break-system-packages")

TX_IFACE = "eth0"
RX_IFACE = "eth1"
TX_MAC   = "00:aa:aa:aa:aa:01"
RX_MAC   = "00:bb:bb:bb:bb:02"
TX_IP    = "10.0.0.1"
RX_IP    = "20.0.0.2"
BAD_SRC  = "10.0.0.99"    # blocked source
BAD_DST  = "20.0.0.99"    # blocked destination
N        = 10
TIMEOUT  = 4

@dataclass
class Result:
    tc_id: str
    desc: str
    action: str
    sent: int = 0
    recv: int = 0
    passed: bool = False
    note: str = ""

results: list[Result] = []

# ── helpers ───────────────────────────────────────────────────────────────────

def L2(dst=None):
    return Ether(src=TX_MAC, dst=dst or RX_MAC)

def _tx_rx(pkts, bpf="ip") -> tuple[int, int]:
    captured = []
    def _sniff():
        sniff(iface=RX_IFACE, filter=bpf,
              prn=lambda p: captured.append(p),
              timeout=TIMEOUT, store=False)
    t = threading.Thread(target=_sniff, daemon=True)
    t.start(); time.sleep(0.25)
    if TX_IFACE in get_if_list():
        sendp(pkts, iface=TX_IFACE, verbose=False, inter=0.05)
    t.join(timeout=TIMEOUT + 1)
    return len(pkts), len(captured)

def run(tc_id, desc, action, pkts, bpf="ip") -> Result:
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

def L3_01():
    "Deny source IP host 10.0.0.99"
    pkts = [L2()/IP(src=BAD_SRC, dst=RX_IP)/ICMP() for _ in range(N)]
    return run("L3-01", f"Deny source IP {BAD_SRC}", "DENY", pkts, f"src host {BAD_SRC}")

def L3_02():
    "Deny source subnet 10.0.0.0/24"
    pkts = [L2()/IP(src=f"10.0.0.{i+1}", dst=RX_IP)/UDP() for i in range(N)]
    return run("L3-02", "Deny source subnet 10.0.0.0/24", "DENY", pkts, "src net 10.0.0.0/24")

def L3_03():
    "Deny destination IP host 20.0.0.99"
    pkts = [L2()/IP(src=TX_IP, dst=BAD_DST)/TCP() for _ in range(N)]
    return run("L3-03", f"Deny destination IP {BAD_DST}", "DENY", pkts, f"dst host {BAD_DST}")

def L3_04():
    "Deny ICMP (protocol 1)"
    pkts = [L2()/IP(src=TX_IP, dst=RX_IP)/ICMP(type=8) for _ in range(N)]
    return run("L3-04", "Deny ICMP (ping blocked)", "DENY", pkts, "icmp")

def L3_05():
    "Deny UDP / permit TCP (two-phase)"
    pkts_udp = [L2()/IP(src=TX_IP, dst=RX_IP)/UDP(dport=53)  for _ in range(N)]
    pkts_tcp = [L2()/IP(src=TX_IP, dst=RX_IP)/TCP(dport=80)  for _ in range(N)]
    print(f"\n[L3-05] Deny UDP / Permit TCP  (2-phase)")
    s1, r1 = _tx_rx(pkts_udp, "udp")
    s2, r2 = _tx_rx(pkts_tcp, "tcp")
    p1 = r1 == 0          # UDP must be dropped
    p2 = r2 >= s2 * 0.9   # TCP must pass
    passed = p1 and p2
    note = f"UDP: {'OK' if p1 else 'FAIL'}({r1}/{s1})  TCP: {'OK' if p2 else 'FAIL'}({r2}/{s2})"
    r = Result("L3-05", "Deny UDP / Permit TCP", "MIXED", s1+s2, r1+r2, passed, note)
    results.append(r)
    print(f"  {note}  [{'PASS' if passed else 'FAIL'}]")
    return r

def L3_06():
    "Deny TCP destination port 80"
    pkts = [L2()/IP(src=TX_IP, dst=RX_IP)/TCP(dport=80, flags="S") for _ in range(N)]
    return run("L3-06", "Deny TCP dst port 80 (HTTP)", "DENY", pkts, "tcp dst port 80")

def L3_07():
    "Deny UDP destination port 53 (DNS)"
    pkts = [L2()/IP(src=TX_IP, dst=RX_IP)/UDP(dport=53) for _ in range(N)]
    return run("L3-07", "Deny UDP dst port 53 (DNS)", "DENY", pkts, "udp dst port 53")

def L3_08():
    "Deny TCP SYN (new connection initiation)"
    pkts = [L2()/IP(src=TX_IP, dst=RX_IP)/TCP(dport=8080, flags="S") for _ in range(N)]
    return run("L3-08", "Deny TCP SYN-only (flags=S)", "DENY", pkts,
               "tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0")

def L3_09():
    "Permit TCP ACK (established session)"
    pkts = [L2()/IP(src=TX_IP, dst=RX_IP)/TCP(dport=8080, flags="A", seq=100, ack=1)
            for _ in range(N)]
    return run("L3-09", "Permit TCP ACK (established)", "PERMIT", pkts,
               "tcp[tcpflags] & tcp-ack != 0")

def L3_10():
    "Deny 5-tuple: src=10.0.0.99, dst=20.0.0.2, TCP, dport=80"
    pkts = [L2()/IP(src=BAD_SRC, dst=RX_IP)/TCP(dport=80, flags="S") for _ in range(N)]
    return run("L3-10", f"Deny 5-tuple {BAD_SRC}→{RX_IP}:80/TCP", "DENY", pkts,
               f"src host {BAD_SRC} and tcp dst port 80")

def L3_11():
    "Implicit deny-all — non-matching source hits end of ACL"
    pkts = [L2()/IP(src="172.16.0.1", dst=RX_IP)/ICMP() for _ in range(N)]
    return run("L3-11", "Implicit deny-all (src=172.16.0.1, no permit rule)", "DENY", pkts,
               "src host 172.16.0.1")

def L3_12():
    "Deny DSCP EF (tos=0xB8) — HW only"
    pkts = [L2()/IP(src=TX_IP, dst=RX_IP, tos=0xB8)/UDP() for _ in range(N)]
    return run("L3-12", "Deny DSCP EF (tos=0xB8) [HW only]", "DENY", pkts, "ip[1] = 0xb8")

# ── registry ──────────────────────────────────────────────────────────────────

ALL = {
    "L3-01": L3_01, "L3-02": L3_02, "L3-03": L3_03,
    "L3-04": L3_04, "L3-05": L3_05, "L3-06": L3_06, "L3-07": L3_07,
    "L3-08": L3_08, "L3-09": L3_09,
    "L3-10": L3_10, "L3-11": L3_11, "L3-12": L3_12,
}

def report():
    passed = sum(1 for r in results if r.passed)
    print(f"\n{'='*60}")
    print(f"  L3 ACL RESULTS  ({passed}/{len(results)} passed)")
    print(f"{'='*60}")
    for r in results:
        s = "PASS ✓" if r.passed else "FAIL ✗"
        print(f"  {r.tc_id:<7} {s:<8} sent={r.sent:<4} recv={r.recv:<4} {r.note}")
    print()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tc",   help="Single TC, e.g. L3-04")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        [print(f"  {k}  {v.__doc__}") for k, v in ALL.items()]
    elif args.tc:
        if args.tc in ALL: ALL[args.tc](); report()
        else: print(f"Unknown TC: {args.tc}")
    else:
        print("\n[L3 ACL] Running all 12 test cases...")
        for fn in ALL.values(): fn()
        report()
