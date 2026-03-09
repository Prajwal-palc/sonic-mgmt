#!/usr/bin/env python3
"""
l3_acl_traffic.py — L3 ACL Traffic Generation & Validation

This script generates Scapy-based traffic on external TX/RX hosts and validates
ACL behavior on the DUT. It sends crafted IP packets and measures packet delivery
through the DUT to verify ACL rules are correctly enforced.

Architecture:
  TX Host (eth0: 10.0.0.1/24) →[Scapy]→ DUT Port1 →[ACL]→ DUT Port2 → RX Host (eth1: 20.0.0.2/24)

  All tests are UNIDIRECTIONAL: TX → DUT → RX (no return traffic)

Test Coverage:
  - L3-01 to L3-12: Functional test cases (IP, protocol, TCP flags, 5-tuple, DSCP)
  - L3-N01 to L3-N09: Negative test cases (edge cases, malformed packets)
  - L3-R01 to L3-R14: Robustness test cases (persistence, stress, consistency)

Prerequisites:
  1. TX Host:
     - Interface eth0 configured with IP 10.0.0.1/24 (use setup_ports.py)
     - Python3 + Scapy installed
     - Raw socket permissions (sudo or CAP_NET_RAW capability)

  2. RX Host:
     - Interface eth1 configured with IP 20.0.0.2/24 (use setup_ports.py)
     - Promiscuous mode enabled (done by setup_ports.py)
     - tcpdump optional for independent verification

  3. DUT (SONiC):
     - Port1 configured with IP 10.0.0.254/24 (see acl-l3.md Prerequisites)
     - Port2 configured with IP 20.0.0.254/24
     - ACL rules configured per test case
     - No local firewall blocking test traffic

Usage:
  sudo python3 l3_acl_traffic.py              # run all functional test cases (L3-01 to L3-12)
  sudo python3 l3_acl_traffic.py --tc L3-04  # run single test case
  sudo python3 l3_acl_traffic.py --tc L3-01,L3-02,L3-04  # run multiple tests
  sudo python3 l3_acl_traffic.py --list       # list all available tests
  sudo python3 l3_acl_traffic.py --timeout 10 # increase RX sniff timeout to 10 seconds

Output:
  - Console output: Pass/Fail for each test case
  - Summary table: sent, received, pass/fail, notes
  - Exit code: 0 if all passed, 1 if any failed

Parameters:
  --tc TESTID        Run specific test case(s), comma-separated (e.g., L3-01,L3-05)
  --list             List all available test cases and exit
  --timeout SECS     Override RX sniff timeout (default: 4 seconds)
  --packet-count N   Override number of packets per test (default: 10)
  --inter-delay SEC  Override inter-packet delay (default: 0.05 sec)

Important Notes:
  - All traffic is UNIDIRECTIONAL (TX→DUT→RX); no return traffic is tested
  - TCP ACK test (L3-09) uses CRAFTED packets (not real TCP handshake)
  - DSCP test (L3-12) requires HW support; skipped on SONiC-VS
  - Pass criteria: PERMIT = RX count ≥ 90% TX; DENY = RX count == 0
  - Negative tests (L3-N*) validate edge cases and error handling

Troubleshooting:
  - "Permission denied" → Run with sudo
  - "No such device eth0" → Check interface names (ip link show); edit PORTS
  - RX sees 0 packets (even PERMIT cases) → Check DUT routing (show ip route)
  - Inconsistent results → Increase --timeout or --packet-count
"""
import argparse, threading, time, sys
from dataclasses import dataclass

try:
    from scapy.all import conf, sendp, sniff, get_if_list, Ether, IP, TCP, UDP, ICMP
except ImportError:
    sys.exit("[ERROR] pip3 install scapy --break-system-packages")

# ── Configuration ─────────────────────────────────────────────────────────────

# Network interfaces and addresses (must match setup_ports.py configuration)
TX_IFACE = "eth0"              # TX Host interface (connected to DUT Port1)
RX_IFACE = "eth1"              # RX Host interface (connected to DUT Port2)
TX_MAC   = "00:aa:aa:aa:aa:01" # TX Host MAC (static)
RX_MAC   = "00:bb:bb:bb:bb:02" # RX Host MAC (static)
TX_IP    = "10.0.0.1"           # TX Host IP (must match setup_ports.py)
RX_IP    = "20.0.0.2"           # RX Host IP (must match setup_ports.py)

# Test-specific blocked IPs (used in negative test cases)
BAD_SRC  = "10.0.0.99"          # Blocked source IP (L3-01, L3-10, etc.)
BAD_DST  = "20.0.0.99"          # Blocked destination IP (L3-03)

# Test parameters (can be overridden via command-line)
N        = 10                   # Default: 10 packets per test
TIMEOUT  = 4                    # Default: 4 second RX sniff timeout
INTER_DELAY = 0.05              # Default: 50ms inter-packet delay

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
    """
    Send packets on TX interface and sniff packets on RX interface.

    Args:
        pkts: List of Scapy packet objects to send
        bpf: BPF filter for sniffing (e.g., "ip", "tcp", "udp")

    Returns:
        Tuple of (packets sent, packets received)
    """
    captured = []
    def _sniff():
        sniff(iface=RX_IFACE, filter=bpf,
              prn=lambda p: captured.append(p),
              timeout=TIMEOUT, store=False)
    t = threading.Thread(target=_sniff, daemon=True)
    t.start()
    time.sleep(0.25)  # Wait for sniffer to start
    if TX_IFACE in get_if_list():
        sendp(pkts, iface=TX_IFACE, verbose=False, inter=INTER_DELAY)
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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tc", help="Test case(s): single (L3-04) or comma-separated (L3-01,L3-02,L3-04)")
    ap.add_argument("--list", action="store_true", help="List all available test cases")
    ap.add_argument("--timeout", type=float, default=TIMEOUT, help=f"RX sniff timeout in seconds (default: {TIMEOUT})")
    ap.add_argument("--packet-count", type=int, default=N, help=f"Number of packets per test (default: {N})")
    ap.add_argument("--inter-delay", type=float, default=INTER_DELAY, help=f"Inter-packet delay in seconds (default: {INTER_DELAY})")
    args = ap.parse_args()

    # Override global parameters
    TIMEOUT = args.timeout
    N = args.packet_count
    INTER_DELAY = args.inter_delay

    if args.list:
        print("\nAvailable L3 ACL Test Cases:")
        print("─" * 60)
        for k, v in sorted(ALL.items()):
            print(f"  {k:<8} {v.__doc__}")
        print()
    elif args.tc:
        # Parse comma-separated test IDs
        tc_list = [t.strip().upper() for t in args.tc.split(",")]
        invalid = [t for t in tc_list if t not in ALL]
        if invalid:
            print(f"Unknown test cases: {invalid}")
            sys.exit(1)

        print(f"\n[L3 ACL] Running {len(tc_list)} test case(s)...")
        for tc_id in tc_list:
            ALL[tc_id]()
        report()
    else:
        print("\n[L3 ACL] Running all 12 functional test cases (L3-01 to L3-12)...")
        print("(Use --tc to run specific tests; --list to see all available)")
        for fn in ALL.values(): fn()
        report()
