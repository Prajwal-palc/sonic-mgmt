#!/usr/bin/env python3
"""
setup_ports.py — Configure TX (eth0) and RX (eth1) ports for ACL testing.

Usage:
  sudo python3 setup_ports.py           # configure + verify
  sudo python3 setup_ports.py --verify  # verify only
"""
import argparse, subprocess, sys

try:
    from scapy.all import get_if_list, get_if_hwaddr, sendp, Ether, ARP
except ImportError:
    sys.exit("[ERROR] Install scapy: pip3 install scapy --break-system-packages")

PORTS = [
    {"name": "TX", "iface": "eth0", "ip": "10.0.0.1", "mac": "00:aa:aa:aa:aa:01", "role": "sender"},
    {"name": "RX", "iface": "eth1", "ip": "20.0.0.2", "mac": "00:bb:bb:bb:bb:02", "role": "receiver"},
]

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def configure():
    for p in PORTS:
        iface = p["iface"]
        if iface not in get_if_list():
            print(f"  [SKIP] {iface} not found")
            continue
        run(f"ip link set {iface} up")
        run(f"ip link set {iface} address {p['mac']}")
        run(f"ip addr flush dev {iface}")
        run(f"ip addr add {p['ip']}/24 dev {iface}")
        if p["role"] == "receiver":
            run(f"ip link set {iface} promisc on")
        print(f"  [OK] {p['name']} ({iface})  IP={p['ip']}  MAC={p['mac']}")

def verify():
    ok = True
    for p in PORTS:
        iface = p["iface"]
        exists = iface in get_if_list()
        ip_ok  = p["ip"] in run(f"ip addr show {iface}").stdout if exists else False
        mac_ok = False
        if exists:
            try: mac_ok = get_if_hwaddr(iface).lower() == p["mac"].lower()
            except: pass
        status = "PASS" if (exists and ip_ok and mac_ok) else "FAIL"
        if status == "FAIL": ok = False
        print(f"  [{status}] {p['name']} ({iface})  exists={exists}  ip={ip_ok}  mac={mac_ok}")
    return ok

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    print("\n=== ACL Test Port Setup ===")
    if not args.verify:
        print("[1] Configuring ports...")
        configure()
    print("[2] Verifying ports...")
    verify()
    print()
