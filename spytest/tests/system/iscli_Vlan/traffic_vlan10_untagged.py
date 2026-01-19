#!/usr/bin/env python3
"""
Scapy Traffic Generator for VLAN10 Untagged Traffic

This script generates both unicast and broadcast traffic for VLAN10 (untagged).
Traffic is sent from source MAC to destination MAC on access ports.

Usage:
    sudo python3 traffic_vlan10_untagged.py --mode unicast --iface eth0 --count 100
    sudo python3 traffic_vlan10_untagged.py --mode broadcast --iface eth0 --count 50

Requirements:
    - Scapy library (pip install scapy)
    - Root/sudo privileges for packet sending
    - Network interface with access to VLAN10 ports
"""

import argparse
import sys
import time
from typing import Optional

try:
    from scapy.all import (
        Ether,
        IP,
        UDP,
        Raw,
        sendp,
        conf,
        get_if_hwaddr,
    )
except ImportError:
    print("ERROR: Scapy library not found. Install with: pip install scapy")
    sys.exit(1)


class VLAN10UntaggedTrafficGenerator:
    """Generate untagged traffic for VLAN10 access ports."""

    def __init__(
        self,
        interface: str,
        src_mac: Optional[str] = None,
        dst_mac: Optional[str] = None,
    ):
        """
        Initialize traffic generator.

        Args:
            interface: Network interface to send traffic on
            src_mac: Source MAC address (default: interface MAC)
            dst_mac: Destination MAC address (default: based on mode)
        """
        self.interface = interface
        self.src_mac = src_mac or get_if_hwaddr(interface)
        self.dst_mac = dst_mac

        # Disable verbose output
        conf.verb = 0

        print(f"[INFO] Initialized VLAN10 Untagged Traffic Generator")
        print(f"[INFO] Interface: {self.interface}")
        print(f"[INFO] Source MAC: {self.src_mac}")

    def generate_unicast_traffic(
        self,
        dst_mac: str,
        packet_count: int = 100,
        packet_size: int = 64,
        interval: float = 0.01,
    ) -> int:
        """
        Generate unicast traffic (untagged).

        Args:
            dst_mac: Destination MAC address
            packet_count: Number of packets to send
            packet_size: Packet size in bytes
            interval: Interval between packets in seconds

        Returns:
            Number of packets sent
        """
        print(f"\n[TRAFFIC] Generating VLAN10 Untagged Unicast Traffic")
        print(f"[TRAFFIC] Src MAC: {self.src_mac} -> Dst MAC: {dst_mac}")
        print(f"[TRAFFIC] Packets: {packet_count}, Size: {packet_size} bytes")

        # Calculate payload size (subtract Ethernet + IP + UDP headers)
        payload_size = max(0, packet_size - 42)
        payload = Raw(load="X" * payload_size)

        packets_sent = 0

        for i in range(packet_count):
            # Create untagged Ethernet frame
            pkt = (
                Ether(src=self.src_mac, dst=dst_mac)
                / IP(src="10.10.10.1", dst="10.10.10.2")
                / UDP(sport=12345, dport=54321)
                / payload
            )

            # Send packet
            sendp(pkt, iface=self.interface, verbose=False)
            packets_sent += 1

            if (i + 1) % 10 == 0:
                print(f"[PROGRESS] Sent {i + 1}/{packet_count} packets")

            time.sleep(interval)

        print(f"[SUCCESS] Sent {packets_sent} unicast packets")
        return packets_sent

    def generate_broadcast_traffic(
        self,
        packet_count: int = 50,
        packet_size: int = 64,
        interval: float = 0.01,
    ) -> int:
        """
        Generate broadcast traffic (untagged).

        Args:
            packet_count: Number of packets to send
            packet_size: Packet size in bytes
            interval: Interval between packets in seconds

        Returns:
            Number of packets sent
        """
        broadcast_mac = "ff:ff:ff:ff:ff:ff"

        print(f"\n[TRAFFIC] Generating VLAN10 Untagged Broadcast Traffic")
        print(f"[TRAFFIC] Src MAC: {self.src_mac} -> Dst MAC: {broadcast_mac}")
        print(f"[TRAFFIC] Packets: {packet_count}, Size: {packet_size} bytes")

        # Calculate payload size
        payload_size = max(0, packet_size - 42)
        payload = Raw(load="B" * payload_size)

        packets_sent = 0

        for i in range(packet_count):
            # Create broadcast frame
            pkt = (
                Ether(src=self.src_mac, dst=broadcast_mac)
                / IP(src="10.10.10.1", dst="255.255.255.255")
                / UDP(sport=12345, dport=54321)
                / payload
            )

            # Send packet
            sendp(pkt, iface=self.interface, verbose=False)
            packets_sent += 1

            if (i + 1) % 10 == 0:
                print(f"[PROGRESS] Sent {i + 1}/{packet_count} packets")

            time.sleep(interval)

        print(f"[SUCCESS] Sent {packets_sent} broadcast packets")
        return packets_sent

    def run_traffic_test(
        self,
        mode: str,
        dst_mac: Optional[str] = None,
        packet_count: int = 100,
        packet_size: int = 64,
        interval: float = 0.01,
    ) -> bool:
        """
        Run traffic test based on mode.

        Args:
            mode: Traffic mode ('unicast' or 'broadcast')
            dst_mac: Destination MAC for unicast mode
            packet_count: Number of packets to send
            packet_size: Packet size in bytes
            interval: Interval between packets

        Returns:
            True if test successful, False otherwise
        """
        try:
            if mode == "unicast":
                if not dst_mac:
                    print("[ERROR] Destination MAC required for unicast mode")
                    return False
                self.generate_unicast_traffic(dst_mac, packet_count, packet_size, interval)

            elif mode == "broadcast":
                self.generate_broadcast_traffic(packet_count, packet_size, interval)

            else:
                print(f"[ERROR] Unknown mode: {mode}")
                return False

            return True

        except Exception as e:
            print(f"[ERROR] Traffic generation failed: {e}")
            return False


def main():
    """Main entry point for script."""
    parser = argparse.ArgumentParser(
        description="VLAN10 Untagged Traffic Generator using Scapy"
    )

    parser.add_argument(
        "--iface",
        "-i",
        required=True,
        help="Network interface to send traffic on (e.g., eth0, Ethernet0)",
    )

    parser.add_argument(
        "--mode",
        "-m",
        choices=["unicast", "broadcast"],
        required=True,
        help="Traffic mode: unicast or broadcast",
    )

    parser.add_argument(
        "--src-mac",
        help="Source MAC address (default: interface MAC)",
    )

    parser.add_argument(
        "--dst-mac",
        help="Destination MAC address (required for unicast mode)",
    )

    parser.add_argument(
        "--count",
        "-c",
        type=int,
        default=100,
        help="Number of packets to send (default: 100)",
    )

    parser.add_argument(
        "--size",
        "-s",
        type=int,
        default=64,
        help="Packet size in bytes (default: 64)",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=0.01,
        help="Interval between packets in seconds (default: 0.01)",
    )

    args = parser.parse_args()

    # Create traffic generator
    traffic_gen = VLAN10UntaggedTrafficGenerator(
        interface=args.iface,
        src_mac=args.src_mac,
    )

    # Run traffic test
    success = traffic_gen.run_traffic_test(
        mode=args.mode,
        dst_mac=args.dst_mac,
        packet_count=args.count,
        packet_size=args.size,
        interval=args.interval,
    )

    if success:
        print("\n[COMPLETED] Traffic generation completed successfully")
        sys.exit(0)
    else:
        print("\n[FAILED] Traffic generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
