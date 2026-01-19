#!/usr/bin/env python3
"""
Scapy Traffic Generator for VLAN20 Tagged Traffic

This script generates both unicast and broadcast traffic for VLAN20 with 802.1Q tags.
Traffic is sent from source MAC to destination MAC on trunk ports.

Usage:
    sudo python3 traffic_vlan20_tagged.py --mode unicast --iface eth0 --count 100
    sudo python3 traffic_vlan20_tagged.py --mode broadcast --iface eth0 --count 50

Requirements:
    - Scapy library (pip install scapy)
    - Root/sudo privileges for packet sending
    - Network interface with access to VLAN20 trunk ports
"""

import argparse
import sys
import time
from typing import Optional

try:
    from scapy.all import (
        Ether,
        Dot1Q,
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


class VLAN20TaggedTrafficGenerator:
    """Generate 802.1Q tagged traffic for VLAN20 trunk ports."""

    def __init__(
        self,
        interface: str,
        vlan_id: int = 20,
        src_mac: Optional[str] = None,
        dst_mac: Optional[str] = None,
    ):
        """
        Initialize traffic generator.

        Args:
            interface: Network interface to send traffic on
            vlan_id: VLAN ID to tag packets with (default: 20)
            src_mac: Source MAC address (default: interface MAC)
            dst_mac: Destination MAC address (default: based on mode)
        """
        self.interface = interface
        self.vlan_id = vlan_id
        self.src_mac = src_mac or get_if_hwaddr(interface)
        self.dst_mac = dst_mac

        # Disable verbose output
        conf.verb = 0

        print(f"[INFO] Initialized VLAN20 Tagged Traffic Generator")
        print(f"[INFO] Interface: {self.interface}")
        print(f"[INFO] VLAN ID: {self.vlan_id}")
        print(f"[INFO] Source MAC: {self.src_mac}")

    def generate_unicast_traffic(
        self,
        dst_mac: str,
        packet_count: int = 100,
        packet_size: int = 64,
        interval: float = 0.01,
        priority: int = 0,
    ) -> int:
        """
        Generate unicast traffic with VLAN tag.

        Args:
            dst_mac: Destination MAC address
            packet_count: Number of packets to send
            packet_size: Packet size in bytes (including VLAN tag)
            interval: Interval between packets in seconds
            priority: 802.1p priority (0-7)

        Returns:
            Number of packets sent
        """
        print(f"\n[TRAFFIC] Generating VLAN20 Tagged Unicast Traffic")
        print(f"[TRAFFIC] Src MAC: {self.src_mac} -> Dst MAC: {dst_mac}")
        print(f"[TRAFFIC] VLAN ID: {self.vlan_id}, Priority: {priority}")
        print(f"[TRAFFIC] Packets: {packet_count}, Size: {packet_size} bytes")

        # Calculate payload size (subtract Ethernet + VLAN + IP + UDP headers)
        # Ethernet (14) + VLAN tag (4) + IP (20) + UDP (8) = 46 bytes
        payload_size = max(0, packet_size - 46)
        payload = Raw(load="X" * payload_size)

        packets_sent = 0

        for i in range(packet_count):
            # Create tagged Ethernet frame
            pkt = (
                Ether(src=self.src_mac, dst=dst_mac)
                / Dot1Q(vlan=self.vlan_id, prio=priority)
                / IP(src="20.20.20.1", dst="20.20.20.2")
                / UDP(sport=12345, dport=54321)
                / payload
            )

            # Send packet
            sendp(pkt, iface=self.interface, verbose=False)
            packets_sent += 1

            if (i + 1) % 10 == 0:
                print(f"[PROGRESS] Sent {i + 1}/{packet_count} packets")

            time.sleep(interval)

        print(f"[SUCCESS] Sent {packets_sent} tagged unicast packets")
        return packets_sent

    def generate_broadcast_traffic(
        self,
        packet_count: int = 50,
        packet_size: int = 64,
        interval: float = 0.01,
        priority: int = 0,
    ) -> int:
        """
        Generate broadcast traffic with VLAN tag.

        Args:
            packet_count: Number of packets to send
            packet_size: Packet size in bytes (including VLAN tag)
            interval: Interval between packets in seconds
            priority: 802.1p priority (0-7)

        Returns:
            Number of packets sent
        """
        broadcast_mac = "ff:ff:ff:ff:ff:ff"

        print(f"\n[TRAFFIC] Generating VLAN20 Tagged Broadcast Traffic")
        print(f"[TRAFFIC] Src MAC: {self.src_mac} -> Dst MAC: {broadcast_mac}")
        print(f"[TRAFFIC] VLAN ID: {self.vlan_id}, Priority: {priority}")
        print(f"[TRAFFIC] Packets: {packet_count}, Size: {packet_size} bytes")

        # Calculate payload size
        payload_size = max(0, packet_size - 46)
        payload = Raw(load="B" * payload_size)

        packets_sent = 0

        for i in range(packet_count):
            # Create tagged broadcast frame
            pkt = (
                Ether(src=self.src_mac, dst=broadcast_mac)
                / Dot1Q(vlan=self.vlan_id, prio=priority)
                / IP(src="20.20.20.1", dst="255.255.255.255")
                / UDP(sport=12345, dport=54321)
                / payload
            )

            # Send packet
            sendp(pkt, iface=self.interface, verbose=False)
            packets_sent += 1

            if (i + 1) % 10 == 0:
                print(f"[PROGRESS] Sent {i + 1}/{packet_count} packets")

            time.sleep(interval)

        print(f"[SUCCESS] Sent {packets_sent} tagged broadcast packets")
        return packets_sent

    def generate_multicast_traffic(
        self,
        multicast_mac: str = "01:00:5e:00:00:01",
        packet_count: int = 50,
        packet_size: int = 64,
        interval: float = 0.01,
        priority: int = 0,
    ) -> int:
        """
        Generate multicast traffic with VLAN tag.

        Args:
            multicast_mac: Multicast MAC address
            packet_count: Number of packets to send
            packet_size: Packet size in bytes
            interval: Interval between packets in seconds
            priority: 802.1p priority (0-7)

        Returns:
            Number of packets sent
        """
        print(f"\n[TRAFFIC] Generating VLAN20 Tagged Multicast Traffic")
        print(f"[TRAFFIC] Src MAC: {self.src_mac} -> Multicast MAC: {multicast_mac}")
        print(f"[TRAFFIC] VLAN ID: {self.vlan_id}, Priority: {priority}")
        print(f"[TRAFFIC] Packets: {packet_count}, Size: {packet_size} bytes")

        payload_size = max(0, packet_size - 46)
        payload = Raw(load="M" * payload_size)

        packets_sent = 0

        for i in range(packet_count):
            # Create tagged multicast frame
            pkt = (
                Ether(src=self.src_mac, dst=multicast_mac)
                / Dot1Q(vlan=self.vlan_id, prio=priority)
                / IP(src="20.20.20.1", dst="224.0.0.1")
                / UDP(sport=12345, dport=54321)
                / payload
            )

            # Send packet
            sendp(pkt, iface=self.interface, verbose=False)
            packets_sent += 1

            if (i + 1) % 10 == 0:
                print(f"[PROGRESS] Sent {i + 1}/{packet_count} packets")

            time.sleep(interval)

        print(f"[SUCCESS] Sent {packets_sent} tagged multicast packets")
        return packets_sent

    def run_traffic_test(
        self,
        mode: str,
        dst_mac: Optional[str] = None,
        packet_count: int = 100,
        packet_size: int = 64,
        interval: float = 0.01,
        priority: int = 0,
    ) -> bool:
        """
        Run traffic test based on mode.

        Args:
            mode: Traffic mode ('unicast', 'broadcast', or 'multicast')
            dst_mac: Destination MAC for unicast mode
            packet_count: Number of packets to send
            packet_size: Packet size in bytes
            interval: Interval between packets
            priority: 802.1p priority

        Returns:
            True if test successful, False otherwise
        """
        try:
            if mode == "unicast":
                if not dst_mac:
                    print("[ERROR] Destination MAC required for unicast mode")
                    return False
                self.generate_unicast_traffic(
                    dst_mac, packet_count, packet_size, interval, priority
                )

            elif mode == "broadcast":
                self.generate_broadcast_traffic(
                    packet_count, packet_size, interval, priority
                )

            elif mode == "multicast":
                multicast_mac = dst_mac or "01:00:5e:00:00:01"
                self.generate_multicast_traffic(
                    multicast_mac, packet_count, packet_size, interval, priority
                )

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
        description="VLAN20 Tagged Traffic Generator using Scapy"
    )

    parser.add_argument(
        "--iface",
        "-i",
        required=True,
        help="Network interface to send traffic on (e.g., eth0, Ethernet4)",
    )

    parser.add_argument(
        "--mode",
        "-m",
        choices=["unicast", "broadcast", "multicast"],
        required=True,
        help="Traffic mode: unicast, broadcast, or multicast",
    )

    parser.add_argument(
        "--vlan",
        "-v",
        type=int,
        default=20,
        help="VLAN ID to tag packets with (default: 20)",
    )

    parser.add_argument(
        "--src-mac",
        help="Source MAC address (default: interface MAC)",
    )

    parser.add_argument(
        "--dst-mac",
        help="Destination MAC address (required for unicast, optional for multicast)",
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

    parser.add_argument(
        "--priority",
        "-p",
        type=int,
        default=0,
        choices=range(8),
        help="802.1p priority (0-7, default: 0)",
    )

    args = parser.parse_args()

    # Create traffic generator
    traffic_gen = VLAN20TaggedTrafficGenerator(
        interface=args.iface,
        vlan_id=args.vlan,
        src_mac=args.src_mac,
    )

    # Run traffic test
    success = traffic_gen.run_traffic_test(
        mode=args.mode,
        dst_mac=args.dst_mac,
        packet_count=args.count,
        packet_size=args.size,
        interval=args.interval,
        priority=args.priority,
    )

    if success:
        print("\n[COMPLETED] Traffic generation completed successfully")
        sys.exit(0)
    else:
        print("\n[FAILED] Traffic generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
