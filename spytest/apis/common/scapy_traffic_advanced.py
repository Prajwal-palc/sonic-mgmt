#!/usr/bin/env python3
"""
Advanced Scapy Traffic API - Extended packet field manipulation for SONiC testing

This module extends the basic scapy_traffic.py API with advanced packet field
manipulation capabilities, including DSCP/ToS byte, TCP flags, TTL manipulation,
and malformed packet generation.

Author: Test Engineering Team
Copyright (C) 2025

Usage:
    from apis.common import scapy_traffic_advanced

    # Send traffic with DSCP EF (L3-12 test case)
    result = scapy_traffic_advanced.send_traffic_with_dscp(
        dut=dut1,
        interface="Ethernet0",
        src_ip="10.1.1.1",
        dst_ip="10.1.1.2",
        dscp_value=46,  # DSCP EF = 46 (0xB8 >> 2)
        duration=10
    )

    # Send TCP SYN packets (L3-08 test case)
    result = scapy_traffic_advanced.send_traffic_with_tcp_flags(
        dut=dut1,
        interface="Ethernet0",
        src_ip="10.1.1.1",
        dst_ip="10.1.1.2",
        tcp_flags="S",  # SYN flag
        dst_port=80,
        duration=10
    )

    # Send packets with custom TTL (TTL manipulation tests)
    result = scapy_traffic_advanced.send_traffic_with_ttl(
        dut=dut1,
        interface="Ethernet0",
        src_ip="10.1.1.1",
        dst_ip="10.1.1.2",
        ttl=1,  # TTL=1 (hop-limited traffic)
        duration=10
    )
"""

from __future__ import annotations

import re
from typing import Dict, Optional, Any

from spytest import st

# Import basic scapy_traffic functions
import apis.common.scapy_traffic as scapy_traffic

# Default parameters
DEFAULT_DURATION = 10
DEFAULT_PPS = 1000
DEFAULT_PAYLOAD_SIZE = 200
DEFAULT_UDP_PORT = 54321
DEFAULT_TCP_PORT = 80
DEFAULT_TTL = 64
DEFAULT_DSCP = 0


def send_traffic_with_dscp(
    dut: str,
    interface: str,
    src_ip: str,
    dst_ip: str,
    src_mac: Optional[str] = None,
    dst_mac: Optional[str] = None,
    dscp_value: int = DEFAULT_DSCP,
    dst_port: int = DEFAULT_UDP_PORT,
    duration: int = DEFAULT_DURATION,
    pps: int = DEFAULT_PPS,
    payload_size: int = DEFAULT_PAYLOAD_SIZE,
    traffic_type: str = "udp"
) -> Dict[str, Any]:
    """
    Send traffic with specific DSCP value (ToS byte manipulation).

    This function creates and executes a Scapy script that sends packets
    with a specific DSCP (Differentiated Services Code Point) value.
    Used for testing ACL rules that match on DSCP/QoS fields.

    Args:
        dut: Device handle
        interface: Interface to send traffic on (e.g., "Ethernet0")
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_mac: Source MAC address (auto-retrieved if None)
        dst_mac: Destination MAC address (auto-retrieved if None)
        dscp_value: DSCP value (0-63, RFC 2474)
                   Examples: 0=BE, 8=CS1, 16=CS2, 24=CS3, 32=CS4, 40=CS5, 46=EF, 48=CS6, 56=CS7
        dst_port: Destination UDP port (default: 54321)
        duration: Traffic duration in seconds (default: 10)
        pps: Packets per second (default: 1000)
        payload_size: Payload size in bytes (default: 200)
        traffic_type: Traffic type ("udp" or "icmp", default: "udp")

    Returns:
        Dictionary with keys:
            - success: bool - True if traffic sent successfully
            - output: str - Command output
            - packets_sent: int - Number of packets sent

    Example:
        >>> # Send EF traffic (DSCP=46)
        >>> result = send_traffic_with_dscp(
        ...     dut="D1",
        ...     interface="Ethernet0",
        ...     src_ip="10.1.1.1",
        ...     dst_ip="10.1.1.2",
        ...     dscp_value=46,
        ...     duration=10
        ... )
        >>> if result["success"]:
        ...     print(f"Sent {result['packets_sent']} EF traffic packets")
    """
    st.log(f"Sending traffic with DSCP={dscp_value} from {dut}")

    # Get MAC addresses if not provided
    if not src_mac:
        src_mac = scapy_traffic.get_interface_mac(dut, interface) or scapy_traffic.get_default_mac(1)
    if not dst_mac:
        dst_mac = scapy_traffic.get_default_mac(2)

    # Validate DSCP value
    if not (0 <= dscp_value <= 63):
        st.error(f"Invalid DSCP value {dscp_value} (must be 0-63)")
        return {"success": False, "output": "Invalid DSCP value", "packets_sent": 0}

    # Convert DSCP to ToS byte (DSCP is upper 6 bits, ECN is lower 2 bits)
    # ToS = DSCP << 2 (shift left 2 bits to get upper 6 bits)
    tos_byte = dscp_value << 2

    # Create Scapy script with DSCP/ToS field
    scapy_script = f"""#!/usr/bin/env python3
from scapy.all import IP, UDP, ICMP, Ether, sendp
import time

# Traffic parameters
src_ip = "{src_ip}"
dst_ip = "{dst_ip}"
src_mac = "{src_mac}"
dst_mac = "{dst_mac}"
interface = "{interface}"
dst_port = {dst_port}
duration = {duration}
pps = {pps}
payload_size = {payload_size}
dscp_value = {dscp_value}
tos_byte = {tos_byte}

# Calculate timing
packet_count = pps * duration
inter_packet_delay = 1.0 / pps if pps > 0 else 0.1

try:
    print(f"Starting DSCP traffic: src={{src_ip}} dst={{dst_ip}} DSCP={{dscp_value}}")
    print(f"Total packets: {{packet_count}}, Duration: {{duration}}s, PPS: {{pps}}")

    start_time = time.time()
    packets_sent = 0

    for i in range(packet_count):
        # Build packet with DSCP in ToS field
        eth = Ether(src=src_mac, dst=dst_mac)

        if "{traffic_type}" == "icmp":
            # ICMP packet with DSCP
            ip = IP(src=src_ip, dst=dst_ip, tos=tos_byte)
            icmp = ICMP(type=8, code=0)  # Echo request
            pkt = eth / ip / icmp
        else:
            # UDP packet with DSCP
            ip = IP(src=src_ip, dst=dst_ip, tos=tos_byte)
            udp = UDP(sport=54321, dport=dst_port)
            payload = b"X" * payload_size
            pkt = eth / ip / udp / payload

        # Send packet
        sendp(pkt, iface=interface, verbose=False)
        packets_sent += 1

        # Maintain consistent packet rate
        if inter_packet_delay > 0 and (i + 1) < packet_count:
            time.sleep(inter_packet_delay)

    elapsed = time.time() - start_time
    actual_pps = packets_sent / elapsed if elapsed > 0 else 0

    print(f"Completed sending {{packets_sent}} packets in {{elapsed:.2f}}s ({{actual_pps:.0f}} pps)")
    print(f"DSCP field (ToS={{tos_byte}}) applied to all packets")

except Exception as e:
    print(f"Error sending DSCP traffic: {{e}}")
    import traceback
    traceback.print_exc()
"""

    # Write script to device
    script_path = "/tmp/scapy_dscp_traffic.py"
    try:
        # Write script to device via st.show with echo
        cmd = f"cat > {script_path} << 'SCAPY_EOF'\n{scapy_script}\nSCADY_EOF"
        st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)

        # Make script executable
        st.show(dut, f"chmod +x {script_path}", skip_tmpl=True, skip_error_check=True)

        # Execute script
        output = st.show(dut, f"sudo python3 {script_path}", skip_tmpl=True, skip_error_check=True)
        st.log(f"DSCP traffic output:\n{output}")

        output_str = str(output)

        # Parse packets sent
        packets_sent = 0
        sent_match = re.search(r'Completed sending (\d+) packets', output_str)
        if sent_match:
            packets_sent = int(sent_match.group(1))

        success = "Completed" in output_str and "Error" not in output_str

        return {
            "success": success,
            "output": output_str,
            "packets_sent": packets_sent
        }

    except Exception as e:
        st.error(f"Error sending DSCP traffic: {e}")
        return {"success": False, "output": str(e), "packets_sent": 0}


def send_traffic_with_tcp_flags(
    dut: str,
    interface: str,
    src_ip: str,
    dst_ip: str,
    src_mac: Optional[str] = None,
    dst_mac: Optional[str] = None,
    tcp_flags: str = "S",
    src_port: int = 54321,
    dst_port: int = DEFAULT_TCP_PORT,
    duration: int = DEFAULT_DURATION,
    pps: int = DEFAULT_PPS,
    payload_size: int = DEFAULT_PAYLOAD_SIZE
) -> Dict[str, Any]:
    """
    Send TCP traffic with specific flags.

    This function creates and executes a Scapy script that sends TCP packets
    with specific control flags (SYN, ACK, FIN, RST, etc.).
    Used for testing ACL rules that match on TCP flags.

    Args:
        dut: Device handle
        interface: Interface to send traffic on
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_mac: Source MAC address (auto-retrieved if None)
        dst_mac: Destination MAC address (auto-retrieved if None)
        tcp_flags: TCP flags as string
                  "S"=SYN, "A"=ACK, "F"=FIN, "R"=RST, "P"=PSH, "U"=URG
                  Combinations: "SA"=SYN+ACK, "AR"=ACK+RST, etc.
        src_port: Source TCP port (default: 54321)
        dst_port: Destination TCP port (default: 80)
        duration: Traffic duration in seconds (default: 10)
        pps: Packets per second (default: 1000)
        payload_size: Payload size in bytes (default: 200)

    Returns:
        Dictionary with keys:
            - success: bool
            - output: str
            - packets_sent: int

    Example:
        >>> # Send SYN packets (for SYN scanning or SYN flood tests)
        >>> result = send_traffic_with_tcp_flags(
        ...     dut="D1",
        ...     interface="Ethernet0",
        ...     src_ip="10.1.1.1",
        ...     dst_ip="10.1.1.2",
        ...     tcp_flags="S",  # SYN only
        ...     dst_port=80,
        ...     duration=10
        ... )
    """
    st.log(f"Sending TCP traffic with flags '{tcp_flags}' from {dut}")

    # Get MAC addresses if not provided
    if not src_mac:
        src_mac = scapy_traffic.get_interface_mac(dut, interface) or scapy_traffic.get_default_mac(1)
    if not dst_mac:
        dst_mac = scapy_traffic.get_default_mac(2)

    # Validate TCP flags
    valid_flags = set("SAFPRU")
    if not all(f in valid_flags for f in tcp_flags):
        st.error(f"Invalid TCP flags '{tcp_flags}' (valid: S, A, F, P, R, U)")
        return {"success": False, "output": "Invalid TCP flags", "packets_sent": 0}

    # Create Scapy script with TCP flags
    scapy_script = f"""#!/usr/bin/env python3
from scapy.all import IP, TCP, Ether, sendp
import time

# Traffic parameters
src_ip = "{src_ip}"
dst_ip = "{dst_ip}"
src_mac = "{src_mac}"
dst_mac = "{dst_mac}"
interface = "{interface}"
src_port = {src_port}
dst_port = {dst_port}
duration = {duration}
pps = {pps}
payload_size = {payload_size}
tcp_flags = "{tcp_flags}"

# Calculate timing
packet_count = pps * duration
inter_packet_delay = 1.0 / pps if pps > 0 else 0.1

try:
    print(f"Starting TCP traffic with flags '{{tcp_flags}}': {{src_ip}}:{{src_port}} -> {{dst_ip}}:{{dst_port}}")
    print(f"Total packets: {{packet_count}}, Duration: {{duration}}s, PPS: {{pps}}")

    start_time = time.time()
    packets_sent = 0

    for i in range(packet_count):
        # Build TCP packet with specified flags
        eth = Ether(src=src_mac, dst=dst_mac)
        ip = IP(src=src_ip, dst=dst_ip)
        tcp = TCP(sport=src_port, dport=dst_port, flags=tcp_flags)
        payload = b"X" * payload_size
        pkt = eth / ip / tcp / payload

        # Send packet
        sendp(pkt, iface=interface, verbose=False)
        packets_sent += 1

        # Maintain consistent packet rate
        if inter_packet_delay > 0 and (i + 1) < packet_count:
            time.sleep(inter_packet_delay)

    elapsed = time.time() - start_time
    actual_pps = packets_sent / elapsed if elapsed > 0 else 0

    print(f"Completed sending {{packets_sent}} packets in {{elapsed:.2f}}s ({{actual_pps:.0f}} pps)")
    print(f"TCP flags '{{tcp_flags}}' applied to all packets")

except Exception as e:
    print(f"Error sending TCP traffic: {{e}}")
    import traceback
    traceback.print_exc()
"""

    # Write and execute script
    script_path = "/tmp/scapy_tcp_flags_traffic.py"
    try:
        cmd = f"cat > {script_path} << 'SCAPY_EOF'\n{scapy_script}\nSCADY_EOF"
        st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
        st.show(dut, f"chmod +x {script_path}", skip_tmpl=True, skip_error_check=True)

        output = st.show(dut, f"sudo python3 {script_path}", skip_tmpl=True, skip_error_check=True)
        st.log(f"TCP flags traffic output:\n{output}")

        output_str = str(output)

        packets_sent = 0
        sent_match = re.search(r'Completed sending (\d+) packets', output_str)
        if sent_match:
            packets_sent = int(sent_match.group(1))

        success = "Completed" in output_str and "Error" not in output_str

        return {
            "success": success,
            "output": output_str,
            "packets_sent": packets_sent
        }

    except Exception as e:
        st.error(f"Error sending TCP flags traffic: {e}")
        return {"success": False, "output": str(e), "packets_sent": 0}


def send_traffic_with_ttl(
    dut: str,
    interface: str,
    src_ip: str,
    dst_ip: str,
    src_mac: Optional[str] = None,
    dst_mac: Optional[str] = None,
    ttl: int = DEFAULT_TTL,
    dst_port: int = DEFAULT_UDP_PORT,
    duration: int = DEFAULT_DURATION,
    pps: int = DEFAULT_PPS,
    payload_size: int = DEFAULT_PAYLOAD_SIZE,
    traffic_type: str = "udp"
) -> Dict[str, Any]:
    """
    Send traffic with specific TTL (Time To Live) value.

    This function creates and executes a Scapy script that sends packets
    with a specific TTL value. Used for testing hop-limit filtering or
    traceroute-like behavior.

    Args:
        dut: Device handle
        interface: Interface to send traffic on
        src_ip: Source IP address
        dst_ip: Destination IP address
        src_mac: Source MAC address (auto-retrieved if None)
        dst_mac: Destination MAC address (auto-retrieved if None)
        ttl: TTL value (1-255, default: 64)
        dst_port: Destination UDP port (default: 54321)
        duration: Traffic duration in seconds (default: 10)
        pps: Packets per second (default: 1000)
        payload_size: Payload size in bytes (default: 200)
        traffic_type: Traffic type ("udp" or "icmp", default: "udp")

    Returns:
        Dictionary with keys:
            - success: bool
            - output: str
            - packets_sent: int

    Example:
        >>> # Send packets with TTL=1 (single hop)
        >>> result = send_traffic_with_ttl(
        ...     dut="D1",
        ...     interface="Ethernet0",
        ...     src_ip="10.1.1.1",
        ...     dst_ip="10.1.1.2",
        ...     ttl=1,
        ...     duration=10
        ... )
    """
    st.log(f"Sending traffic with TTL={ttl} from {dut}")

    # Get MAC addresses if not provided
    if not src_mac:
        src_mac = scapy_traffic.get_interface_mac(dut, interface) or scapy_traffic.get_default_mac(1)
    if not dst_mac:
        dst_mac = scapy_traffic.get_default_mac(2)

    # Validate TTL value
    if not (1 <= ttl <= 255):
        st.error(f"Invalid TTL value {ttl} (must be 1-255)")
        return {"success": False, "output": "Invalid TTL value", "packets_sent": 0}

    # Create Scapy script with TTL
    scapy_script = f"""#!/usr/bin/env python3
from scapy.all import IP, UDP, ICMP, Ether, sendp
import time

# Traffic parameters
src_ip = "{src_ip}"
dst_ip = "{dst_ip}"
src_mac = "{src_mac}"
dst_mac = "{dst_mac}"
interface = "{interface}"
dst_port = {dst_port}
duration = {duration}
pps = {pps}
payload_size = {payload_size}
ttl = {ttl}

# Calculate timing
packet_count = pps * duration
inter_packet_delay = 1.0 / pps if pps > 0 else 0.1

try:
    print(f"Starting TTL traffic: src={{src_ip}} dst={{dst_ip}} TTL={{ttl}}")
    print(f"Total packets: {{packet_count}}, Duration: {{duration}}s, PPS: {{pps}}")

    start_time = time.time()
    packets_sent = 0

    for i in range(packet_count):
        # Build packet with TTL
        eth = Ether(src=src_mac, dst=dst_mac)

        if "{traffic_type}" == "icmp":
            # ICMP packet with TTL
            ip = IP(src=src_ip, dst=dst_ip, ttl=ttl)
            icmp = ICMP(type=8, code=0)  # Echo request
            pkt = eth / ip / icmp
        else:
            # UDP packet with TTL
            ip = IP(src=src_ip, dst=dst_ip, ttl=ttl)
            udp = UDP(sport=54321, dport=dst_port)
            payload = b"X" * payload_size
            pkt = eth / ip / udp / payload

        # Send packet
        sendp(pkt, iface=interface, verbose=False)
        packets_sent += 1

        # Maintain consistent packet rate
        if inter_packet_delay > 0 and (i + 1) < packet_count:
            time.sleep(inter_packet_delay)

    elapsed = time.time() - start_time
    actual_pps = packets_sent / elapsed if elapsed > 0 else 0

    print(f"Completed sending {{packets_sent}} packets in {{elapsed:.2f}}s ({{actual_pps:.0f}} pps)")
    print(f"TTL={{ttl}} applied to all packets")

except Exception as e:
    print(f"Error sending TTL traffic: {{e}}")
    import traceback
    traceback.print_exc()
"""

    # Write and execute script
    script_path = "/tmp/scapy_ttl_traffic.py"
    try:
        cmd = f"cat > {script_path} << 'SCAPY_EOF'\n{scapy_script}\nSCADY_EOF"
        st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
        st.show(dut, f"chmod +x {script_path}", skip_tmpl=True, skip_error_check=True)

        output = st.show(dut, f"sudo python3 {script_path}", skip_tmpl=True, skip_error_check=True)
        st.log(f"TTL traffic output:\n{output}")

        output_str = str(output)

        packets_sent = 0
        sent_match = re.search(r'Completed sending (\d+) packets', output_str)
        if sent_match:
            packets_sent = int(sent_match.group(1))

        success = "Completed" in output_str and "Error" not in output_str

        return {
            "success": success,
            "output": output_str,
            "packets_sent": packets_sent
        }

    except Exception as e:
        st.error(f"Error sending TTL traffic: {e}")
        return {"success": False, "output": str(e), "packets_sent": 0}


# Additional helper functions for specific test cases

def send_ef_traffic(
    dut: str,
    interface: str,
    src_ip: str,
    dst_ip: str,
    duration: int = DEFAULT_DURATION,
    pps: int = DEFAULT_PPS,
    **kwargs
) -> Dict[str, Any]:
    """
    Send traffic with DSCP EF (Expedited Forwarding) marking.

    DSCP EF = 46 (Binary: 101110, ToS = 0xB8 = 184)
    Useful for L3-12 test case.

    Args:
        dut: Device handle
        interface: Interface name
        src_ip: Source IP
        dst_ip: Destination IP
        duration: Traffic duration (seconds)
        pps: Packets per second
        **kwargs: Additional arguments passed to send_traffic_with_dscp

    Returns:
        Dictionary with success, output, packets_sent
    """
    return send_traffic_with_dscp(
        dut=dut,
        interface=interface,
        src_ip=src_ip,
        dst_ip=dst_ip,
        dscp_value=46,  # EF
        duration=duration,
        pps=pps,
        **kwargs
    )


def send_syn_traffic(
    dut: str,
    interface: str,
    src_ip: str,
    dst_ip: str,
    dst_port: int = 80,
    duration: int = DEFAULT_DURATION,
    pps: int = DEFAULT_PPS,
    **kwargs
) -> Dict[str, Any]:
    """
    Send TCP SYN packets.

    Useful for L3-08 test case (TCP SYN flag matching).

    Args:
        dut: Device handle
        interface: Interface name
        src_ip: Source IP
        dst_ip: Destination IP
        dst_port: Destination TCP port
        duration: Traffic duration
        pps: Packets per second
        **kwargs: Additional arguments

    Returns:
        Dictionary with success, output, packets_sent
    """
    return send_traffic_with_tcp_flags(
        dut=dut,
        interface=interface,
        src_ip=src_ip,
        dst_ip=dst_ip,
        tcp_flags="S",  # SYN only
        dst_port=dst_port,
        duration=duration,
        pps=pps,
        **kwargs
    )


def send_ack_traffic(
    dut: str,
    interface: str,
    src_ip: str,
    dst_ip: str,
    dst_port: int = 80,
    duration: int = DEFAULT_DURATION,
    pps: int = DEFAULT_PPS,
    **kwargs
) -> Dict[str, Any]:
    """
    Send TCP ACK packets.

    Useful for L3-09 test case (TCP ACK flag matching).

    Args:
        dut: Device handle
        interface: Interface name
        src_ip: Source IP
        dst_ip: Destination IP
        dst_port: Destination TCP port
        duration: Traffic duration
        pps: Packets per second
        **kwargs: Additional arguments

    Returns:
        Dictionary with success, output, packets_sent
    """
    return send_traffic_with_tcp_flags(
        dut=dut,
        interface=interface,
        src_ip=src_ip,
        dst_ip=dst_ip,
        tcp_flags="A",  # ACK only
        dst_port=dst_port,
        duration=duration,
        pps=pps,
        **kwargs
    )

