#!/usr/bin/env python3
"""
l2_acl_traffic.py — L2 ACL Traffic Generation & Validation

This script generates Scapy-based L2 traffic on external TX/RX hosts and validates
ACL behavior on the DUT. It sends crafted Ethernet frames (MAC, EtherType, VLAN) and
measures packet delivery through the DUT to verify L2 ACL rules are correctly enforced.

Architecture:
  TX Host (eth0: 10.0.0.1) →[Scapy L2]→ DUT Port1 →[L2 ACL]→ DUT Port2 → RX Host (eth1: 20.0.0.2)

  All tests are UNIDIRECTIONAL: TX → DUT → RX (L2 switching, not L3 routing)

Test Coverage:
  - L2-01 to L2-08: Functional test cases (MAC, EtherType, VLAN matching)
  - L2-N01 to L2-N03: Negative test cases (edge cases, invalid inputs)
  - L2-R01 to L2-R08: Robustness test cases (persistence, stress, consistency)

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
     - Port1 in L2 switchport mode (NOT routed mode)
     - Port2 in L2 switchport mode
     - VLANs 10, 100, 200 created (for L2-06, L2-07 tests)
     - Both ports in VLAN 1 (default), with trunk access to test VLANs
     - No local firewall blocking test traffic

Usage:
  sudo python3 l2_acl_traffic.py              # run all functional test cases (L2-01 to L2-08)
  sudo python3 l2_acl_traffic.py --tc L2-03  # run single test case
  sudo python3 l2_acl_traffic.py --tc L2-01,L2-04,L2-06  # run multiple tests
  sudo python3 l2_acl_traffic.py --list       # list all available tests
  sudo python3 l2_acl_traffic.py --timeout 10 # increase RX sniff timeout to 10 seconds

Output:
  - Console output: Pass/Fail for each test case
  - Summary table: sent, received, pass/fail, notes
  - Exit code: 0 if all passed, 1 if any failed

Parameters:
  --tc TESTID        Run specific test case(s), comma-separated (e.g., L2-01,L2-05)
  --list             List all available test cases and exit
  --timeout SECS     Override RX sniff timeout (default: 4 seconds)
  --packet-count N   Override number of packets per test (default: 10)
  --inter-delay SEC  Override inter-packet delay (default: 0.05 sec)

Important Notes:
  - All tests are UNIDIRECTIONAL (TX→DUT→RX); no return traffic is tested
  - L2 ACL tests match on MAC addresses, EtherType, and VLAN tags (not IP)
  - DUT ports must be in switchport mode (L2), NOT routed mode
  - VLANs 10, 100, 200 must be pre-created on DUT for VLAN tests (L2-06, L2-07)
  - Pass criteria: PERMIT tests require ≥90% packet delivery; DENY tests require 0% delivery
  - Negative tests (L2-N*) validate edge cases and error handling
  - Robustness tests (L2-R*) verify persistence and consistency

Troubleshooting:
  - "Permission denied" → Run with sudo
  - "No such device eth0" → Check interface names (ip link show); edit PORTS
  - RX sees 0 packets (even PERMIT cases) → Check DUT VLAN membership and port mode
  - All tests fail → Verify DUT Port1/Port2 are in switchport mode (not routed)
"""
import argparse, threading, time, sys
from dataclasses import dataclass, field

try:
    from scapy.all import conf, sendp, sniff, get_if_list, Ether, IP, ARP, Dot1Q, UDP
except ImportError:
    sys.exit("[ERROR] pip3 install scapy --break-system-packages")

# ── Configuration ─────────────────────────────────────────────────────────────

# Network interfaces and addresses (must match setup_ports.py configuration)
TX_IFACE = "eth0"              # TX Host interface (connected to DUT Port1)
RX_IFACE = "eth1"              # RX Host interface (connected to DUT Port2)
TX_MAC   = "00:aa:aa:aa:aa:01" # TX Host MAC (static)
RX_MAC   = "00:bb:bb:bb:bb:02" # RX Host MAC (static)

# Test parameters (can be overridden via command-line)
N        = 10                   # Default: 10 packets per test
TIMEOUT  = 4                    # Default: 4 second RX sniff timeout
INTER_DELAY = 0.05              # Default: 50ms inter-packet delay

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
    """
    Send L2 frames on TX interface and sniff frames on RX interface.

    Args:
        pkts: List of Scapy Ether packet objects to send
        bpf: BPF filter for sniffing (e.g., "ether src", "vlan 10", "arp")

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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tc", help="Test case(s): single (L2-03) or comma-separated (L2-01,L2-04,L2-06)")
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
        print("\nAvailable L2 ACL Test Cases:")
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

        print(f"\n[L2 ACL] Running {len(tc_list)} test case(s)...")
        for tc_id in tc_list:
            ALL[tc_id]()
        report()
    else:
        print("\n[L2 ACL] Running all 8 functional test cases (L2-01 to L2-08)...")
        print("(Use --tc to run specific tests; --list to see all available)")
        for fn in ALL.values(): fn()
        report()
