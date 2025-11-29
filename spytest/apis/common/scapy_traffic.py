#!/usr/bin/env python3
"""
Scapy Traffic API - Reusable Scapy-based traffic generation for SONiC test automation

This module provides a reusable API for generating and verifying traffic using Scapy
in SONiC test environments. The API abstracts Scapy functionality for use in SPyTest
test scripts, supporting various traffic types and verification methods.

Author: Test Engineering Team
Copyright (C) 2025

Usage:
    from apis.common import scapy_traffic

    # Get MAC addresses
    src_mac = scapy_traffic.get_interface_mac(dut1, "Ethernet0")
    dst_mac = scapy_traffic.get_interface_mac(dut2, "Ethernet0")

    # Deploy and execute Scapy traffic
    result = scapy_traffic.send_traffic(
        dut=dut1,
        interface="Ethernet0",
        src_ip="10.1.1.1",
        dst_ip="10.1.1.2",
        src_mac=src_mac,
        dst_mac=dst_mac,
        duration=10,
        pps=1000
    )

    # Verify connectivity
    success = scapy_traffic.verify_ping(dut1, "10.1.1.2", src_ip="10.1.1.1")
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Any

from spytest import st


# Default traffic parameters
DEFAULT_DURATION = 10  # seconds
DEFAULT_PPS = 1000  # packets per second
DEFAULT_PAYLOAD_SIZE = 200  # bytes
DEFAULT_SCAPY_SCRIPT_PATH = "/tmp/scapy_traffic_sender.py"


def get_interface_mac(dut: str, interface: str, cli_type: str = "klish") -> Optional[str]:
    """
    Retrieve MAC address of a specified interface.

    Args:
        dut: Device handle
        interface: Interface name (e.g., "Ethernet0", "Ethernet4")
        cli_type: CLI type to use (default: "klish")

    Returns:
        MAC address string (e.g., "aa:bb:cc:dd:ee:ff") or None if not found

    Example:
        >>> mac = get_interface_mac("D1", "Ethernet0")
        >>> print(mac)
        '52:54:00:d3:78:35'
    """
    st.log(f"Retrieving MAC address for {interface} on {dut}")

    try:
        output = st.show(dut, f"show interface {interface}", type=cli_type, skip_tmpl=True)
        st.log(f"Interface output:\n{output}")

        # MAC address pattern: XX:XX:XX:XX:XX:XX
        mac_pattern = r'([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})'
        match = re.search(mac_pattern, str(output))

        if match:
            mac = match.group(1).lower()
            st.log(f"Found MAC address: {mac}")
            return mac
        else:
            st.log(f"Could not extract MAC address for {interface} on {dut}")
            return None

    except Exception as e:
        st.error(f"Error retrieving MAC address: {e}")
        return None


def get_default_mac(dut_index: int = 1) -> str:
    """
    Generate a default MAC address for a DUT if actual MAC cannot be retrieved.

    Args:
        dut_index: DUT index (1-based)

    Returns:
        Default MAC address string

    Example:
        >>> mac = get_default_mac(1)
        '52:54:00:00:00:01'
    """
    base_mac = "52:54:00:00:00:"
    return f"{base_mac}{dut_index:02x}"


def create_scapy_script(
    dut: str,
    interface: str,
    src_ip: str,
    dst_ip: str,
    src_mac: str,
    dst_mac: str,
    duration: int = DEFAULT_DURATION,
    pps: int = DEFAULT_PPS,
    payload_size: int = DEFAULT_PAYLOAD_SIZE,
    script_path: str = DEFAULT_SCAPY_SCRIPT_PATH,
    traffic_type: str = "udp"
) -> bool:
    """
    Create Scapy traffic generation script on device.

    Args:
        dut: Device handle
        interface: Interface to send traffic on (e.g., "Ethernet0")
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        duration: Traffic duration in seconds (default: 10)
        pps: Packets per second (default: 1000)
        payload_size: Payload size in bytes (default: 200)
        script_path: Path to save script on device (default: /tmp/scapy_traffic_sender.py)
        traffic_type: Traffic type - "udp", "icmp", "tcp" (default: "udp")

    Returns:
        True if script created successfully, False otherwise

    Example:
        >>> success = create_scapy_script(
        ...     dut="D1",
        ...     interface="Ethernet0",
        ...     src_ip="10.1.1.1",
        ...     dst_ip="10.1.1.2",
        ...     src_mac="aa:bb:cc:dd:ee:f1",
        ...     dst_mac="aa:bb:cc:dd:ee:f2",
        ...     duration=15,
        ...     pps=500
        ... )
    """
    st.log(f"Creating Scapy traffic script on {dut}")
    st.log(f"  Interface: {interface}")
    st.log(f"  Source: {src_ip} ({src_mac})")
    st.log(f"  Destination: {dst_ip} ({dst_mac})")
    st.log(f"  Duration: {duration}s, Rate: {pps} pps")
    st.log(f"  Traffic Type: {traffic_type.upper()}")

    # Build packet construction based on traffic type
    if traffic_type.lower() == "icmp":
        packet_construction = (
            "pkt = Ether(src=src_mac, dst=dst_mac)/"
            "IP(src=src_ip, dst=dst_ip)/"
            "ICMP(type=8, code=0)"
        )
    elif traffic_type.lower() == "tcp":
        packet_construction = (
            "payload = random_payload(payload_size)\n"
            "            pkt = Ether(src=src_mac, dst=dst_mac)/"
            "IP(src=src_ip, dst=dst_ip)/"
            "TCP(sport=12345, dport=54321)/"
            "Raw(load=payload)"
        )
    else:  # Default to UDP
        packet_construction = (
            "payload = random_payload(payload_size)\n"
            "            pkt = Ether(src=src_mac, dst=dst_mac)/"
            "IP(src=src_ip, dst=dst_ip)/"
            "UDP(sport=12345, dport=54321)/"
            "Raw(load=payload)"
        )

    script_content = f'''#!/usr/bin/env python3
"""
Scapy Traffic Generator Script
Auto-generated by SPyTest Scapy Traffic API
"""

from scapy.all import *
import time
import random
import string
import sys

# Configuration
iface = "{interface}"
src_ip = "{src_ip}"
dst_ip = "{dst_ip}"
src_mac = "{src_mac}"
dst_mac = "{dst_mac}"
duration = {duration}
pps = {pps}
payload_size = {payload_size}
traffic_type = "{traffic_type}"

def random_payload(size):
    """Generate random alphanumeric payload."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=size))

def send_traffic():
    """Send traffic using Scapy."""
    interval = 1.0 / pps
    end_time = time.time() + duration
    sent = 0

    print(f"[+] Starting {{traffic_type.upper()}} traffic generation")
    print(f"    Interface:    {{iface}}")
    print(f"    Source:       {{src_ip}} ({{src_mac}})")
    print(f"    Destination:  {{dst_ip}} ({{dst_mac}})")
    print(f"    Duration:     {{duration}} seconds")
    print(f"    Rate:         {{pps}} pps")
    print(f"    Payload:      {{payload_size}} bytes")
    print()

    start_time = time.time()

    try:
        while time.time() < end_time:
            # Build packet
            {packet_construction}

            # Send packet
            sendp(pkt, iface=iface, verbose=False)
            sent += 1

            # Progress indicator
            if sent % 100 == 0:
                elapsed = time.time() - start_time
                print(f"[→] Sent {{sent}} packets ({{elapsed:.1f}}s elapsed)...", end='\\r')

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\\n[!] Interrupted by user")
        return False
    except Exception as e:
        print(f"\\n[✗] Error: {{e}}")
        return False

    elapsed = time.time() - start_time
    actual_pps = sent / elapsed if elapsed > 0 else 0

    print(f"\\n[✓] Completed. Sent {{sent}} packets in {{elapsed:.2f}} seconds ({{actual_pps:.0f}} pps)")
    return True

if __name__ == "__main__":
    success = send_traffic()
    sys.exit(0 if success else 1)
'''

    try:
        # Remove existing script if present
        st.show(dut, f"rm -f {script_path}", skip_tmpl=True, skip_error_check=True)

        # Create script using heredoc
        cmd = f"cat > {script_path} << 'EOFSCAPY'\n{script_content}\nEOFSCAPY"
        st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)

        # Make executable
        st.show(dut, f"chmod +x {script_path}", skip_tmpl=True, skip_error_check=True)

        st.log(f"Scapy script created successfully at {script_path} on {dut}")
        return True

    except Exception as e:
        st.error(f"Failed to create Scapy script on {dut}: {e}")
        return False


def send_traffic(
    dut: str,
    interface: str,
    src_ip: str,
    dst_ip: str,
    src_mac: str,
    dst_mac: str,
    duration: int = DEFAULT_DURATION,
    pps: int = DEFAULT_PPS,
    payload_size: int = DEFAULT_PAYLOAD_SIZE,
    script_path: str = DEFAULT_SCAPY_SCRIPT_PATH,
    traffic_type: str = "udp"
) -> Dict[str, Any]:
    """
    Send traffic using Scapy from specified device.

    This is a high-level function that creates and executes the Scapy script.

    Args:
        dut: Device handle
        interface: Interface to send traffic on
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_mac: Source MAC address
        dst_mac: Destination MAC address
        duration: Traffic duration in seconds (default: 10)
        pps: Packets per second (default: 1000)
        payload_size: Payload size in bytes (default: 200)
        script_path: Path to save script on device (default: /tmp/scapy_traffic_sender.py)
        traffic_type: Traffic type - "udp", "icmp", "tcp" (default: "udp")

    Returns:
        Dictionary with keys:
            - success: bool - True if traffic sent successfully
            - output: str - Command output
            - packets_sent: int - Number of packets sent (if parseable)

    Example:
        >>> result = send_traffic(
        ...     dut="D1",
        ...     interface="Ethernet0",
        ...     src_ip="10.1.1.1",
        ...     dst_ip="10.1.1.2",
        ...     src_mac=src_mac,
        ...     dst_mac=dst_mac
        ... )
        >>> if result["success"]:
        ...     print(f"Sent {result['packets_sent']} packets")
    """
    st.log(f"Sending Scapy traffic from {dut}")

    # Create script
    if not create_scapy_script(
        dut, interface, src_ip, dst_ip, src_mac, dst_mac,
        duration, pps, payload_size, script_path, traffic_type
    ):
        return {"success": False, "output": "Failed to create script", "packets_sent": 0}

    # Execute script
    try:
        output = st.show(dut, f"sudo python3 {script_path}", skip_tmpl=True, skip_error_check=True)
        st.log(f"Scapy traffic output:\n{output}")

        output_str = str(output)

        # Parse packets sent
        packets_sent = 0
        sent_match = re.search(r'Sent (\d+) packets', output_str)
        if sent_match:
            packets_sent = int(sent_match.group(1))

        # Check for success indicators
        success = False
        if "Completed" in output_str or "packets" in output_str.lower():
            if "Error" not in output_str and "Failed" not in output_str:
                success = True
                st.log(f"Traffic sent successfully from {dut}: {packets_sent} packets")
            else:
                st.log(f"Traffic send completed with errors on {dut}")
        else:
            st.log(f"Traffic send status unclear on {dut}")

        return {
            "success": success,
            "output": output_str,
            "packets_sent": packets_sent
        }

    except Exception as e:
        st.error(f"Error executing Scapy script on {dut}: {e}")
        return {"success": False, "output": str(e), "packets_sent": 0}


def cleanup_scapy_script(dut: str, script_path: str = DEFAULT_SCAPY_SCRIPT_PATH) -> None:
    """
    Remove Scapy script from device.

    Args:
        dut: Device handle
        script_path: Path to script on device (default: /tmp/scapy_traffic_sender.py)

    Example:
        >>> cleanup_scapy_script("D1")
    """
    st.log(f"Cleaning up Scapy script on {dut}")
    try:
        st.show(dut, f"rm -f {script_path}", skip_tmpl=True, skip_error_check=True)
        st.log(f"Scapy script removed from {dut}")
    except Exception as e:
        st.log(f"Error cleaning up Scapy script on {dut}: {e}")


def verify_ping(
    dut: str,
    dst_ip: str,
    src_ip: Optional[str] = None,
    count: int = 5,
    timeout: int = 10
) -> bool:
    """
    Verify connectivity using ping.

    Args:
        dut: Device handle
        dst_ip: Destination IP address
        src_ip: Source IP address (optional)
        count: Number of ping packets (default: 5)
        timeout: Ping timeout in seconds (default: 10)

    Returns:
        True if ping successful, False otherwise

    Example:
        >>> if verify_ping("D1", "10.1.1.2", src_ip="10.1.1.1"):
        ...     print("Connectivity verified")
    """
    st.log(f"Verifying connectivity from {dut} to {dst_ip}")

    try:
        if src_ip:
            cmd = f"ping -c {count} -W {timeout} -I {src_ip} {dst_ip}"
        else:
            cmd = f"ping -c {count} -W {timeout} {dst_ip}"

        output = st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
        st.log(f"Ping output:\n{output}")

        output_str = str(output)

        # Check for successful ping indicators
        success_indicators = [
            f"{count} received",
            "0% packet loss",
            "bytes from",
            f"{count} packets transmitted, {count} received"
        ]

        for indicator in success_indicators:
            if indicator in output_str:
                st.log(f"Ping successful: {dut} -> {dst_ip}")
                return True

        st.log(f"Ping failed: {dut} -> {dst_ip}")
        return False

    except Exception as e:
        st.error(f"Error during ping verification: {e}")
        return False


def start_tcpdump(
    dut: str,
    interface: str,
    filter_str: str = "",
    output_file: str = "/tmp/tcpdump_capture.pcap",
    max_packets: int = 1000
) -> bool:
    """
    Start tcpdump packet capture on device (non-blocking).

    Note: This starts tcpdump in the background. Use stop_tcpdump() to terminate.

    Args:
        dut: Device handle
        interface: Interface to capture on
        filter_str: BPF filter string (e.g., "udp port 54321")
        output_file: Path to save capture file (default: /tmp/tcpdump_capture.pcap)
        max_packets: Maximum packets to capture (default: 1000)

    Returns:
        True if tcpdump started successfully

    Example:
        >>> start_tcpdump("D2", "Ethernet0", filter_str="udp port 54321")
        >>> # ... send traffic ...
        >>> stop_tcpdump("D2")
    """
    st.log(f"Starting tcpdump on {dut} interface {interface}")

    try:
        # Stop any existing tcpdump
        st.show(dut, "sudo pkill -9 tcpdump", skip_tmpl=True, skip_error_check=True)

        # Build tcpdump command
        cmd = f"sudo tcpdump -i {interface} -c {max_packets}"
        if filter_str:
            cmd += f" '{filter_str}'"
        cmd += f" -w {output_file} &"

        st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
        st.log(f"tcpdump started on {dut}")
        return True

    except Exception as e:
        st.error(f"Error starting tcpdump on {dut}: {e}")
        return False


def stop_tcpdump(dut: str) -> bool:
    """
    Stop tcpdump packet capture on device.

    Args:
        dut: Device handle

    Returns:
        True if tcpdump stopped successfully

    Example:
        >>> stop_tcpdump("D2")
    """
    st.log(f"Stopping tcpdump on {dut}")

    try:
        st.show(dut, "sudo pkill -2 tcpdump", skip_tmpl=True, skip_error_check=True)
        st.log(f"tcpdump stopped on {dut}")
        return True

    except Exception as e:
        st.error(f"Error stopping tcpdump on {dut}: {e}")
        return False


def verify_tcpdump_capture(
    dut: str,
    capture_file: str = "/tmp/tcpdump_capture.pcap",
    min_packets: int = 1
) -> Dict[str, Any]:
    """
    Verify tcpdump capture and check packet count.

    Args:
        dut: Device handle
        capture_file: Path to capture file on device
        min_packets: Minimum expected packet count (default: 1)

    Returns:
        Dictionary with keys:
            - success: bool - True if capture contains >= min_packets
            - packet_count: int - Number of packets captured
            - output: str - tcpdump read output

    Example:
        >>> result = verify_tcpdump_capture("D2", min_packets=100)
        >>> if result["success"]:
        ...     print(f"Captured {result['packet_count']} packets")
    """
    st.log(f"Verifying tcpdump capture on {dut}: {capture_file}")

    try:
        # Read capture file
        cmd = f"sudo tcpdump -r {capture_file} | wc -l"
        output = st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
        st.log(f"tcpdump verification output:\n{output}")

        output_str = str(output)

        # Parse packet count
        packet_count = 0
        count_match = re.search(r'(\d+)', output_str)
        if count_match:
            packet_count = int(count_match.group(1))

        success = packet_count >= min_packets
        st.log(f"Captured {packet_count} packets (minimum: {min_packets}) - {'PASS' if success else 'FAIL'}")

        return {
            "success": success,
            "packet_count": packet_count,
            "output": output_str
        }

    except Exception as e:
        st.error(f"Error verifying tcpdump capture on {dut}: {e}")
        return {"success": False, "packet_count": 0, "output": str(e)}
