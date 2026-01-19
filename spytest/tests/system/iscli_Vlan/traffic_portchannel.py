#!/usr/bin/env python3
"""
Scapy Traffic Generator for Port-Channel (LAG50) Traffic

This script generates traffic to test Port-Channel load balancing and VLAN20 traffic
over aggregated links. Supports unicast and broadcast traffic patterns.

Usage:
    sudo python3 traffic_portchannel.py --mode unicast --iface eth0 --count 200
    sudo python3 traffic_portchannel.py --mode broadcast --iface eth0 --count 100
    sudo python3 traffic_portchannel.py --mode load-balance --iface eth0 --count 500

Requirements:
    - Scapy library (pip install scapy)
    - Root/sudo privileges for packet sending
    - Network interface connected to Port-Channel member ports
"""

import argparse
import sys
import time
from typing import Optional, List, Tuple

try:
    from scapy.all import (
        Ether,
        Dot1Q,
        IP,
        TCP,
        UDP,
        Raw,
        sendp,
        conf,
        get_if_hwaddr,
    )
except ImportError:
    print("ERROR: Scapy library not found. Install with: pip install scapy")
    sys.exit(1)


class PortChannelTrafficGenerator:
    """Generate traffic for Port-Channel (LAG) testing with VLAN20 tags."""

    def __init__(
        self,
        interface: str,
        vlan_id: int = 20,
        src_mac: Optional[str] = None,
    ):
        """
        Initialize Port-Channel traffic generator.

        Args:
            interface: Network interface to send traffic on
            vlan_id: VLAN ID for tagged traffic (default: 20)
            src_mac: Source MAC address (default: interface MAC)
        """
        self.interface = interface
        self.vlan_id = vlan_id
        self.src_mac = src_mac or get_if_hwaddr(interface)

        # Disable verbose output
        conf.verb = 0

        print(f"[INFO] Initialized Port-Channel Traffic Generator")
        print(f"[INFO] Interface: {self.interface}")
        print(f"[INFO] VLAN ID: {self.vlan_id}")
        print(f"[INFO] Source MAC: {self.src_mac}")

    def generate_unicast_traffic(
        self,
        dst_mac: str,
        packet_count: int = 200,
        packet_size: int = 64,
        interval: float = 0.01,
    ) -> int:
        """
        Generate unicast traffic over Port-Channel.

        Args:
            dst_mac: Destination MAC address
            packet_count: Number of packets to send
            packet_size: Packet size in bytes
            interval: Interval between packets in seconds

        Returns:
            Number of packets sent
        """
        print(f"\n[TRAFFIC] Generating Port-Channel Unicast Traffic")
        print(f"[TRAFFIC] Src MAC: {self.src_mac} -> Dst MAC: {dst_mac}")
        print(f"[TRAFFIC] VLAN ID: {self.vlan_id}")
        print(f"[TRAFFIC] Packets: {packet_count}, Size: {packet_size} bytes")

        payload_size = max(0, packet_size - 46)
        payload = Raw(load="P" * payload_size)

        packets_sent = 0

        for i in range(packet_count):
            # Create tagged packet
            pkt = (
                Ether(src=self.src_mac, dst=dst_mac)
                / Dot1Q(vlan=self.vlan_id)
                / IP(src="20.20.20.1", dst="20.20.20.2")
                / UDP(sport=12345, dport=54321)
                / payload
            )

            sendp(pkt, iface=self.interface, verbose=False)
            packets_sent += 1

            if (i + 1) % 20 == 0:
                print(f"[PROGRESS] Sent {i + 1}/{packet_count} packets")

            time.sleep(interval)

        print(f"[SUCCESS] Sent {packets_sent} unicast packets over Port-Channel")
        return packets_sent

    def generate_broadcast_traffic(
        self,
        packet_count: int = 100,
        packet_size: int = 64,
        interval: float = 0.01,
    ) -> int:
        """
        Generate broadcast traffic over Port-Channel.

        Args:
            packet_count: Number of packets to send
            packet_size: Packet size in bytes
            interval: Interval between packets in seconds

        Returns:
            Number of packets sent
        """
        broadcast_mac = "ff:ff:ff:ff:ff:ff"

        print(f"\n[TRAFFIC] Generating Port-Channel Broadcast Traffic")
        print(f"[TRAFFIC] Src MAC: {self.src_mac} -> Dst MAC: {broadcast_mac}")
        print(f"[TRAFFIC] VLAN ID: {self.vlan_id}")
        print(f"[TRAFFIC] Packets: {packet_count}, Size: {packet_size} bytes")

        payload_size = max(0, packet_size - 46)
        payload = Raw(load="B" * payload_size)

        packets_sent = 0

        for i in range(packet_count):
            pkt = (
                Ether(src=self.src_mac, dst=broadcast_mac)
                / Dot1Q(vlan=self.vlan_id)
                / IP(src="20.20.20.1", dst="255.255.255.255")
                / UDP(sport=12345, dport=54321)
                / payload
            )

            sendp(pkt, iface=self.interface, verbose=False)
            packets_sent += 1

            if (i + 1) % 20 == 0:
                print(f"[PROGRESS] Sent {i + 1}/{packet_count} packets")

            time.sleep(interval)

        print(f"[SUCCESS] Sent {packets_sent} broadcast packets over Port-Channel")
        return packets_sent

    def generate_load_balance_traffic(
        self,
        dst_mac: str,
        packet_count: int = 500,
        packet_size: int = 64,
        interval: float = 0.01,
    ) -> Tuple[int, dict]:
        """
        Generate varied traffic to test load balancing across LAG members.

        Creates traffic with different 5-tuple values to trigger hash-based
        load distribution across Port-Channel member links.

        Args:
            dst_mac: Destination MAC address
            packet_count: Number of packets to send
            packet_size: Packet size in bytes
            interval: Interval between packets in seconds

        Returns:
            Tuple of (packets_sent, flow_distribution)
        """
        print(f"\n[TRAFFIC] Generating Port-Channel Load Balance Traffic")
        print(f"[TRAFFIC] Testing LAG hash distribution")
        print(f"[TRAFFIC] Src MAC: {self.src_mac} -> Dst MAC: {dst_mac}")
        print(f"[TRAFFIC] VLAN ID: {self.vlan_id}")
        print(f"[TRAFFIC] Packets: {packet_count}, Size: {packet_size} bytes")

        payload_size = max(0, packet_size - 46)
        payload = Raw(load="L" * payload_size)

        packets_sent = 0
        flow_stats = {}

        # Generate traffic with varying 5-tuple to test load balancing
        # Vary: src IP, dst IP, src port, dst port, protocol
        for i in range(packet_count):
            # Create varied source/destination parameters
            flow_id = i % 10
            src_ip = f"20.20.{flow_id}.1"
            dst_ip = f"20.20.{flow_id}.2"
            src_port = 10000 + (i % 100)
            dst_port = 20000 + (i % 100)

            # Track flow distribution
            flow_key = f"{src_ip}:{src_port}->{dst_ip}:{dst_port}"
            flow_stats[flow_key] = flow_stats.get(flow_key, 0) + 1

            # Alternate between TCP and UDP for variety
            if i % 2 == 0:
                pkt = (
                    Ether(src=self.src_mac, dst=dst_mac)
                    / Dot1Q(vlan=self.vlan_id)
                    / IP(src=src_ip, dst=dst_ip)
                    / TCP(sport=src_port, dport=dst_port)
                    / payload
                )
            else:
                pkt = (
                    Ether(src=self.src_mac, dst=dst_mac)
                    / Dot1Q(vlan=self.vlan_id)
                    / IP(src=src_ip, dst=dst_ip)
                    / UDP(sport=src_port, dport=dst_port)
                    / payload
                )

            sendp(pkt, iface=self.interface, verbose=False)
            packets_sent += 1

            if (i + 1) % 50 == 0:
                print(f"[PROGRESS] Sent {i + 1}/{packet_count} packets, Unique flows: {len(flow_stats)}")

            time.sleep(interval)

        print(f"[SUCCESS] Sent {packets_sent} load-balance packets")
        print(f"[INFO] Created {len(flow_stats)} unique flows")
        return packets_sent, flow_stats

    def generate_varied_size_traffic(
        self,
        dst_mac: str,
        packet_count: int = 300,
        interval: float = 0.01,
    ) -> int:
        """
        Generate traffic with varying packet sizes to test LAG behavior.

        Args:
            dst_mac: Destination MAC address
            packet_count: Number of packets to send
            interval: Interval between packets

        Returns:
            Number of packets sent
        """
        print(f"\n[TRAFFIC] Generating Varied Size Traffic for Port-Channel")
        print(f"[TRAFFIC] Src MAC: {self.src_mac} -> Dst MAC: {dst_mac}")
        print(f"[TRAFFIC] Packets: {packet_count} with sizes: 64, 128, 256, 512, 1024, 1500 bytes")

        packet_sizes = [64, 128, 256, 512, 1024, 1500]
        packets_sent = 0

        for i in range(packet_count):
            # Select packet size
            size = packet_sizes[i % len(packet_sizes)]
            payload_size = max(0, size - 46)
            payload = Raw(load="V" * payload_size)

            pkt = (
                Ether(src=self.src_mac, dst=dst_mac)
                / Dot1Q(vlan=self.vlan_id)
                / IP(src="20.20.20.1", dst="20.20.20.2")
                / UDP(sport=12345, dport=54321)
                / payload
            )

            sendp(pkt, iface=self.interface, verbose=False)
            packets_sent += 1

            if (i + 1) % 30 == 0:
                print(f"[PROGRESS] Sent {i + 1}/{packet_count} packets")

            time.sleep(interval)

        print(f"[SUCCESS] Sent {packets_sent} varied-size packets")
        return packets_sent

    def run_traffic_test(
        self,
        mode: str,
        dst_mac: Optional[str] = None,
        packet_count: int = 200,
        packet_size: int = 64,
        interval: float = 0.01,
    ) -> bool:
        """
        Run traffic test based on mode.

        Args:
            mode: Traffic mode ('unicast', 'broadcast', 'load-balance', 'varied-size')
            dst_mac: Destination MAC address
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

            elif mode == "load-balance":
                if not dst_mac:
                    print("[ERROR] Destination MAC required for load-balance mode")
                    return False
                self.generate_load_balance_traffic(dst_mac, packet_count, packet_size, interval)

            elif mode == "varied-size":
                if not dst_mac:
                    print("[ERROR] Destination MAC required for varied-size mode")
                    return False
                self.generate_varied_size_traffic(dst_mac, packet_count, interval)

            else:
                print(f"[ERROR] Unknown mode: {mode}")
                return False

            return True

        except Exception as e:
            print(f"[ERROR] Traffic generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point for script."""
    parser = argparse.ArgumentParser(
        description="Port-Channel (LAG) Traffic Generator using Scapy"
    )

    parser.add_argument(
        "--iface",
        "-i",
        required=True,
        help="Network interface to send traffic on",
    )

    parser.add_argument(
        "--mode",
        "-m",
        choices=["unicast", "broadcast", "load-balance", "varied-size"],
        required=True,
        help="Traffic mode: unicast, broadcast, load-balance, or varied-size",
    )

    parser.add_argument(
        "--vlan",
        "-v",
        type=int,
        default=20,
        help="VLAN ID (default: 20)",
    )

    parser.add_argument(
        "--src-mac",
        help="Source MAC address (default: interface MAC)",
    )

    parser.add_argument(
        "--dst-mac",
        help="Destination MAC address (required for unicast/load-balance modes)",
    )

    parser.add_argument(
        "--count",
        "-c",
        type=int,
        default=200,
        help="Number of packets to send (default: 200)",
    )

    parser.add_argument(
        "--size",
        "-s",
        type=int,
        default=64,
        help="Packet size in bytes (default: 64, not used for varied-size mode)",
    )

    parser.add_argument(
        "--interval",
        type=float,
        default=0.01,
        help="Interval between packets in seconds (default: 0.01)",
    )

    args = parser.parse_args()

    # Create traffic generator
    traffic_gen = PortChannelTrafficGenerator(
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
    )

    if success:
        print("\n[COMPLETED] Traffic generation completed successfully")
        sys.exit(0)
    else:
        print("\n[FAILED] Traffic generation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
