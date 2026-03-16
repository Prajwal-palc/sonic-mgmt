#!/usr/bin/env python3
"""
setup_ports.py — Configure TX (eth0) and RX (eth1) ports for ACL testing.

This script configures network interfaces on external TX and RX hosts (NOT on the DUT).
It sets up the host interfaces with the required IP addresses and MAC addresses for
Scapy-based ACL traffic generation.

Architecture:
  TX Host (eth0: 10.0.0.1/24) ← → DUT Port1
  RX Host (eth1: 20.0.0.2/24) ← → DUT Port2

Usage:
  sudo python3 setup_ports.py           # configure + verify
  sudo python3 setup_ports.py --verify  # verify only
  sudo python3 setup_ports.py --reset   # reset to DHCP (restore defaults)

Requirements:
  - Must run as root (sudo) for interface configuration
  - Requires Scapy library (pip3 install scapy --break-system-packages)
  - Linux kernel 5.4+ (Ubuntu 20.04+ recommended)
  - Network interfaces eth0 and eth1 must exist

Pre-requisites:
  - DUT Port1 and Port2 must be connected and UP
  - DUT Port1/Port2 must have compatible IPs (e.g., 10.0.0.254/24 and 20.0.0.254/24)
  - Disable local firewall: sudo ufw disable
  - Disable iptables: sudo iptables -P INPUT ACCEPT; sudo iptables -P FORWARD ACCEPT

Troubleshooting:
  - "eth0: No such device" → Use actual interface names (ip link show)
  - "Operation not permitted" → Run with sudo
  - No packets reach RX → Check DUT routing (show ip route on DUT)
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
    """Execute shell command and return result."""
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def configure():
    """Configure TX and RX host interfaces with static IPs and MACs."""
    print("\n[1] Checking available interfaces...")
    available = get_if_list()
    print(f"    Available: {available}")

    for p in PORTS:
        iface = p["iface"]
        if iface not in available:
            print(f"  [WARN] {iface} not found in system. Available interfaces: {available}")
            print(f"         → Edit PORTS list or use correct interface names")
            continue

        try:
            # Bring interface up
            result = run(f"ip link set {iface} up")
            if result.returncode != 0:
                print(f"  [FAIL] {p['name']} ({iface}): Could not bring up interface")
                continue

            # Set MAC address
            result = run(f"ip link set {iface} address {p['mac']}")
            if result.returncode != 0:
                print(f"  [WARN] {p['name']} ({iface}): Could not set MAC address")

            # Flush existing IPs
            run(f"ip addr flush dev {iface}")

            # Add new IP
            result = run(f"ip addr add {p['ip']}/24 dev {iface}")
            if result.returncode != 0:
                print(f"  [FAIL] {p['name']} ({iface}): Could not add IP address")
                continue

            # Enable promiscuous mode for RX (to sniff packets)
            if p["role"] == "receiver":
                run(f"ip link set {iface} promisc on")

            print(f"  [OK] {p['name']:<3} ({iface:<6}) IP={p['ip']:<12} MAC={p['mac']}")

        except Exception as e:
            print(f"  [ERROR] {p['name']} ({iface}): {e}")

def verify():
    """Verify that TX and RX interfaces are properly configured."""
    print("\n[2] Verifying port configuration...")
    ok = True

    for p in PORTS:
        iface = p["iface"]
        exists = iface in get_if_list()
        ip_ok  = False
        mac_ok = False
        link_ok = False

        if exists:
            # Check IP configuration
            result = run(f"ip addr show {iface}")
            ip_ok = p["ip"] in result.stdout

            # Check MAC address
            try:
                actual_mac = get_if_hwaddr(iface).lower()
                expected_mac = p["mac"].lower()
                mac_ok = actual_mac == expected_mac
                if not mac_ok:
                    print(f"    {iface} MAC: expected {expected_mac}, got {actual_mac}")
            except:
                pass

            # Check link status
            result = run(f"ip link show {iface}")
            link_ok = "UP" in result.stdout or "UNKNOWN" in result.stdout

        status = "PASS" if (exists and ip_ok and mac_ok and link_ok) else "FAIL"
        if status == "FAIL":
            ok = False

        print(f"  [{status}] {p['name']:<3} ({iface:<6})  exists={str(exists):<5} " \
              f"link={str(link_ok):<5} ip={str(ip_ok):<5} mac={str(mac_ok):<5}")

    if not ok:
        print("\n  ⚠ Some checks failed. Troubleshooting steps:")
        print("    1. Verify DUT Port1/Port2 are UP: 'show interface status' on DUT")
        print("    2. Check DUT routing: 'show ip route' on DUT")
        print("    3. Verify host firewall is disabled: sudo ufw disable")
        print("    4. Check iptables rules: sudo iptables -L")

    return ok

def reset():
    """Reset interfaces to DHCP configuration (restore defaults)."""
    print("\n[3] Resetting interfaces to DHCP...")
    for p in PORTS:
        iface = p["iface"]
        if iface not in get_if_list():
            continue
        try:
            run(f"ip link set {iface} promisc off")
            run(f"ip addr flush dev {iface}")
            print(f"  [OK] {p['name']} ({iface}) reset to DHCP")
        except Exception as e:
            print(f"  [WARN] {p['name']} ({iface}): {e}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true", help="Verify only (don't configure)")
    ap.add_argument("--reset", action="store_true", help="Reset to DHCP and exit")
    args = ap.parse_args()

    print("\n" + "="*60)
    print("  ACL Test Port Setup (External TX/RX Host Configuration)")
    print("="*60)

    if args.reset:
        reset()
    elif not args.verify:
        configure()
        verify()
    else:
        verify()

    print()
