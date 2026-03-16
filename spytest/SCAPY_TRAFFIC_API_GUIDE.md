# Scapy Traffic API Usage Guide

**Author:** Test Engineering Team
**Date:** 2026-03-09
**Purpose:** Comprehensive guide for using `apis.common.scapy_traffic` module in SPyTest tests

---

## Table of Contents

1. [Overview](#overview)
2. [Module Structure](#module-structure)
3. [Import Statements](#import-statements)
4. [API Functions](#api-functions)
5. [Workflow](#workflow)
6. [Usage Examples](#usage-examples)
7. [Log Files and Debugging](#log-files-and-debugging)
8. [Best Practices](#best-practices)
9. [Common Patterns](#common-patterns)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What is scapy_traffic API?

The `apis.common.scapy_traffic` module provides a **Layer 2 traffic generation** framework using Scapy for SONiC test automation. It abstracts Scapy functionality into reusable APIs that generate traffic with:

- ✅ **Ethernet headers** (Layer 2)
- ✅ **MAC addresses** (source and destination)
- ✅ **IP headers** (Layer 3)
- ✅ **Protocol support** (UDP, TCP, ICMP)
- ✅ **Physical interface** specification
- ✅ **Packet capture** capabilities (tcpdump integration)

### Why Use This API?

**Problem:** Direct Scapy scripting in tests leads to:
- Code duplication
- Inconsistent traffic generation
- No MAC address automation
- No logging/verification integration

**Solution:** `scapy_traffic` API provides:
- Centralized, tested traffic generation
- Automatic MAC address retrieval from interfaces
- Integration with SPyTest logging framework
- Standardized verification methods

### Key Difference: Layer 2 vs Layer 3

| Aspect | Layer 3 (send()) | Layer 2 (sendp()) - scapy_traffic API |
|--------|------------------|--------------------------------------|
| Function | `send(pkt)` | `sendp(pkt, iface=interface)` |
| Headers | IP only | **Ether + IP** |
| MAC addresses | ❌ Not included | ✅ **Included** |
| Interface | ❌ Not specified | ✅ **Specified** |
| VLAN support | Limited | ✅ **Full support** |
| Works with access ports | ❌ No | ✅ **Yes** |

---

## Module Structure

### File Location
```
spytest/
└── apis/
    └── common/
        └── scapy_traffic.py      # Main API module
```

### Module Components

```python
# apis/common/scapy_traffic.py

# 1. Helper Functions
get_interface_mac(dut, interface, cli_type="klish")
get_default_mac(dut_index=1)

# 2. Script Generation
create_scapy_script(dut, interface, src_ip, dst_ip, src_mac, dst_mac, ...)

# 3. Traffic Generation
send_traffic(dut, interface, src_ip, dst_ip, src_mac, dst_mac, ...)

# 4. Verification
verify_ping(dut, dst_ip, src_ip=None, count=5, timeout=10)

# 5. Packet Capture
start_tcpdump(dut, interface, filter_str="", output_file="/tmp/tcpdump_capture.pcap")
stop_tcpdump(dut)
verify_tcpdump_capture(dut, capture_file="/tmp/tcpdump_capture.pcap", min_packets=1)

# 6. Cleanup
cleanup_scapy_script(dut, script_path="/tmp/scapy_traffic_sender.py")
```

---

## Import Statements

### In Your Test File

```python
# Full import for all functions
import apis.common.scapy_traffic as scapy_traffic

# OR selective import
from apis.common.scapy_traffic import (
    get_interface_mac,
    send_traffic,
    verify_ping,
    start_tcpdump,
    stop_tcpdump,
    verify_tcpdump_capture,
)

# Standard SPyTest imports
from spytest import st, SpyTestDict
import apis.switching.vlan as vlan_api
import apis.system.interface as intf_api
import apis.routing.ip as ip_api
```

### Module Dependencies (Internal)

The `scapy_traffic.py` module internally imports:

```python
# Python standard library
from __future__ import annotations
import re
from typing import Dict, Optional, Any

# SPyTest framework
from spytest import st
```

### What Gets Imported by Tests

When you use `import apis.common.scapy_traffic as scapy_traffic`, you get access to:

```python
scapy_traffic.get_interface_mac()          # MAC retrieval
scapy_traffic.get_default_mac()            # Default MAC generator
scapy_traffic.create_scapy_script()        # Script creation
scapy_traffic.send_traffic()               # High-level traffic send
scapy_traffic.verify_ping()                # Connectivity verification
scapy_traffic.start_tcpdump()              # Start packet capture
scapy_traffic.stop_tcpdump()               # Stop packet capture
scapy_traffic.verify_tcpdump_capture()     # Verify captured packets
scapy_traffic.cleanup_scapy_script()       # Cleanup temporary files

# Constants
scapy_traffic.DEFAULT_DURATION             # 10 seconds
scapy_traffic.DEFAULT_PPS                  # 1000 packets/sec
scapy_traffic.DEFAULT_PAYLOAD_SIZE         # 200 bytes
scapy_traffic.DEFAULT_SCAPY_SCRIPT_PATH    # /tmp/scapy_traffic_sender.py
```

---

## API Functions

### 1. `get_interface_mac()`

**Purpose:** Retrieve MAC address from a device interface

**Signature:**
```python
def get_interface_mac(dut: str, interface: str, cli_type: str = "klish") -> Optional[str]
```

**Parameters:**
- `dut` (str): Device handle (e.g., "D1", "D2")
- `interface` (str): Interface name (e.g., "Ethernet0", "Vlan10")
- `cli_type` (str): CLI type - "klish" (default), "click", "rest-patch"

**Returns:**
- `str`: MAC address in format "aa:bb:cc:dd:ee:ff" (lowercase)
- `None`: If MAC address cannot be retrieved

**Example:**
```python
# Get MAC from physical interface
mac = scapy_traffic.get_interface_mac("D1", "Ethernet8", cli_type="klish")
# Returns: "52:54:00:d3:78:35"

# Get MAC from VLAN SVI
svi_mac = scapy_traffic.get_interface_mac("D1", "Vlan10", cli_type="klish")
# Returns: "52:54:00:aa:bb:01"
```

**How It Works:**
1. Executes `show interface <interface>` command using `st.show()`
2. Parses output with regex pattern: `([0-9a-fA-F]{2}:[0-9a-fA-F]{2}:...)`
3. Returns MAC in lowercase format
4. Returns `None` if not found or error occurs

**Common Use Cases:**
- Get source MAC for traffic generation
- Get destination MAC for L2 forwarding
- Verify MAC address assignment

---

### 2. `get_default_mac()`

**Purpose:** Generate a default MAC address for fallback scenarios

**Signature:**
```python
def get_default_mac(dut_index: int = 1) -> str
```

**Parameters:**
- `dut_index` (int): DUT index (1-based), used to generate unique MAC

**Returns:**
- `str`: MAC address in format "52:54:00:00:00:XX"

**Example:**
```python
# DUT1 default MAC
mac1 = scapy_traffic.get_default_mac(1)  # "52:54:00:00:00:01"

# DUT2 default MAC
mac2 = scapy_traffic.get_default_mac(2)  # "52:54:00:00:00:02"
```

**When to Use:**
- Fallback when `get_interface_mac()` fails
- Testing scenarios with dummy MAC addresses
- Simulated traffic without real device MACs

---

### 3. `create_scapy_script()`

**Purpose:** Create a Scapy traffic generation script on the device

**Signature:**
```python
def create_scapy_script(
    dut: str,
    interface: str,
    src_ip: str,
    dst_ip: str,
    src_mac: str,
    dst_mac: str,
    duration: int = DEFAULT_DURATION,           # 10
    pps: int = DEFAULT_PPS,                     # 1000
    payload_size: int = DEFAULT_PAYLOAD_SIZE,   # 200
    script_path: str = DEFAULT_SCAPY_SCRIPT_PATH,
    traffic_type: str = "udp"
) -> bool
```

**Parameters:**
- `dut` (str): Device handle
- `interface` (str): Interface to send traffic on (e.g., "Ethernet0")
- `src_ip` (str): Source IP address
- `dst_ip` (str): Destination IP address
- `src_mac` (str): Source MAC address
- `dst_mac` (str): Destination MAC address
- `duration` (int): Traffic duration in seconds (default: 10)
- `pps` (int): Packets per second (default: 1000)
- `payload_size` (int): Payload size in bytes (default: 200)
- `script_path` (str): Path to save script (default: /tmp/scapy_traffic_sender.py)
- `traffic_type` (str): "udp" (default), "icmp", or "tcp"

**Returns:**
- `bool`: True if script created successfully, False otherwise

**Generated Script Structure:**
```python
#!/usr/bin/env python3
from scapy.all import *
import time

# Configuration (parameters injected)
iface = "Ethernet0"
src_ip = "10.1.1.1"
dst_ip = "10.1.1.2"
src_mac = "52:54:00:aa:bb:01"
dst_mac = "52:54:00:aa:bb:02"
duration = 10
pps = 1000
payload_size = 200

def send_traffic():
    interval = 1.0 / pps
    end_time = time.time() + duration
    sent = 0

    while time.time() < end_time:
        # Build packet - LAYER 2 (Ether) + LAYER 3 (IP) + LAYER 4 (UDP)
        pkt = Ether(src=src_mac, dst=dst_mac) / \
              IP(src=src_ip, dst=dst_ip) / \
              UDP(sport=12345, dport=54321) / \
              Raw(load=random_payload(payload_size))

        # Send using sendp() - Layer 2 transmission
        sendp(pkt, iface=iface, verbose=False)
        sent += 1
        time.sleep(interval)

    print(f"[✓] Completed. Sent {sent} packets")
    return True
```

**Traffic Types:**

1. **UDP (default):**
   ```python
   pkt = Ether(src=src_mac, dst=dst_mac) / \
         IP(src=src_ip, dst=dst_ip) / \
         UDP(sport=12345, dport=54321) / \
         Raw(load=payload)
   ```

2. **ICMP:**
   ```python
   pkt = Ether(src=src_mac, dst=dst_mac) / \
         IP(src=src_ip, dst=dst_ip) / \
         ICMP(type=8, code=0)
   ```

3. **TCP:**
   ```python
   pkt = Ether(src=src_mac, dst=dst_mac) / \
         IP(src=src_ip, dst=dst_ip) / \
         TCP(sport=12345, dport=54321) / \
         Raw(load=payload)
   ```

**Example:**
```python
success = scapy_traffic.create_scapy_script(
    dut="D1",
    interface="Ethernet8",
    src_ip="10.1.1.1",
    dst_ip="10.1.1.2",
    src_mac="52:54:00:aa:bb:01",
    dst_mac="52:54:00:aa:bb:02",
    duration=15,
    pps=500,
    traffic_type="udp"
)
```

---

### 4. `send_traffic()` ⭐ **Most Used Function**

**Purpose:** High-level function to create and execute Scapy traffic script

**Signature:**
```python
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
) -> Dict[str, Any]
```

**Parameters:** Same as `create_scapy_script()`

**Returns:**
```python
{
    "success": bool,           # True if traffic sent successfully
    "output": str,            # Command output
    "packets_sent": int       # Number of packets sent (parsed from output)
}
```

**Example:**
```python
result = scapy_traffic.send_traffic(
    dut="D1",
    interface="Ethernet8",
    src_ip="10.1.1.1",
    dst_ip="10.1.1.2",
    src_mac=src_mac,  # Retrieved using get_interface_mac()
    dst_mac=dst_mac,  # Retrieved using get_interface_mac()
    duration=10,
    pps=1000,
    payload_size=200,
    traffic_type="udp"
)

if result["success"]:
    st.log(f"✅ Sent {result['packets_sent']} packets")
else:
    st.error(f"❌ Traffic failed: {result['output']}")
```

**Success Indicators:**
- Output contains "Completed" or "Sent X packets"
- No "Error" or "Failed" in output
- `packets_sent` > 0

---

### 5. `verify_ping()`

**Purpose:** Verify connectivity using ping

**Signature:**
```python
def verify_ping(
    dut: str,
    dst_ip: str,
    src_ip: Optional[str] = None,
    count: int = 5,
    timeout: int = 10
) -> bool
```

**Parameters:**
- `dut` (str): Device handle
- `dst_ip` (str): Destination IP to ping
- `src_ip` (str, optional): Source IP for ping
- `count` (int): Number of ping packets (default: 5)
- `timeout` (int): Ping timeout in seconds (default: 10)

**Returns:**
- `bool`: True if ping successful, False otherwise

**Example:**
```python
# Simple ping
if scapy_traffic.verify_ping("D1", "10.1.1.2"):
    st.log("✅ Connectivity verified")

# Ping with source IP
if scapy_traffic.verify_ping("D1", "10.1.1.2", src_ip="10.1.1.1", count=10):
    st.log("✅ Connectivity from 10.1.1.1 to 10.1.1.2 verified")
```

---

### 6. Packet Capture Functions

#### `start_tcpdump()`

**Purpose:** Start background packet capture on device

**Signature:**
```python
def start_tcpdump(
    dut: str,
    interface: str,
    filter_str: str = "",
    output_file: str = "/tmp/tcpdump_capture.pcap",
    max_packets: int = 1000
) -> bool
```

**Example:**
```python
# Start capture on Ethernet8, filter UDP port 54321
scapy_traffic.start_tcpdump(
    dut="D2",
    interface="Ethernet8",
    filter_str="udp port 54321",
    output_file="/tmp/vlan10_traffic.pcap",
    max_packets=1000
)
```

#### `stop_tcpdump()`

**Purpose:** Stop packet capture

**Signature:**
```python
def stop_tcpdump(dut: str) -> bool
```

**Example:**
```python
scapy_traffic.stop_tcpdump("D2")
```

#### `verify_tcpdump_capture()`

**Purpose:** Verify captured packets meet minimum threshold

**Signature:**
```python
def verify_tcpdump_capture(
    dut: str,
    capture_file: str = "/tmp/tcpdump_capture.pcap",
    min_packets: int = 1
) -> Dict[str, Any]
```

**Returns:**
```python
{
    "success": bool,         # True if packet_count >= min_packets
    "packet_count": int,     # Number of packets captured
    "output": str           # tcpdump output
}
```

**Example:**
```python
result = scapy_traffic.verify_tcpdump_capture(
    dut="D2",
    capture_file="/tmp/vlan10_traffic.pcap",
    min_packets=100
)

if result["success"]:
    st.log(f"✅ Captured {result['packet_count']} packets")
else:
    st.error(f"❌ Only {result['packet_count']} packets captured (expected >= 100)")
```

---

## Workflow

### Complete Traffic Generation Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: SETUP & CONFIGURATION                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Configure VLANs and SVI IP addresses                          │
│     vlan_api.create_vlan(dut1, vlan_id)                           │
│     ip_api.config_ip_addr_interface(dut1, "Vlan10", "10.1.1.1/24")│
│                                                                     │
│  2. Configure access ports (physical interfaces)                   │
│     vlan_api.add_vlan_member(dut1, vlan_id, "Ethernet8",          │
│                              tagging_mode=False)                   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 2: MAC ADDRESS RETRIEVAL                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  3. Get MAC addresses from VLAN SVI interfaces                     │
│     src_mac = scapy_traffic.get_interface_mac("D1", "Vlan10")     │
│     dst_mac = scapy_traffic.get_interface_mac("D2", "Vlan10")     │
│                                                                     │
│     If retrieval fails:                                            │
│     src_mac = scapy_traffic.get_default_mac(1)  # Fallback        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 3: PRE-TRAFFIC PREPARATION                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  4. Clear interface counters                                       │
│     intf_api.clear_interface_counters(dut1, interface_name="...")  │
│                                                                     │
│  5. (Optional) Start packet capture on destination                 │
│     scapy_traffic.start_tcpdump("D2", "Ethernet8",                │
│                                  filter_str="udp port 54321")      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 4: TRAFFIC GENERATION                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  6. Send traffic using scapy_traffic API                           │
│     result = scapy_traffic.send_traffic(                          │
│         dut="D1",                                                  │
│         interface="Ethernet8",      # Physical access port         │
│         src_ip="10.1.1.1",                                         │
│         dst_ip="10.1.1.2",                                         │
│         src_mac=src_mac,            # From Step 3                  │
│         dst_mac=dst_mac,            # From Step 3                  │
│         duration=10,                # 10 seconds                   │
│         pps=1000,                   # 1000 packets/sec             │
│         traffic_type="udp"                                         │
│     )                                                              │
│                                                                     │
│  Generated packet structure:                                       │
│  ┌──────────────────────────────────────────────────┐             │
│  │ Ether(src=src_mac, dst=dst_mac)                 │             │
│  │   ↓                                              │             │
│  │ IP(src="10.1.1.1", dst="10.1.1.2")              │             │
│  │   ↓                                              │             │
│  │ UDP(sport=12345, dport=54321)                   │             │
│  │   ↓                                              │             │
│  │ Raw(load=random_payload)                        │             │
│  └──────────────────────────────────────────────────┘             │
│                                                                     │
│  sendp(pkt, iface="Ethernet8", verbose=False)                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 5: VERIFICATION                                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  7. Check traffic generation success                               │
│     if result["success"]:                                          │
│         packets_sent = result["packets_sent"]                      │
│                                                                     │
│  8. (Optional) Stop packet capture and verify                      │
│     scapy_traffic.stop_tcpdump("D2")                              │
│     cap_result = scapy_traffic.verify_tcpdump_capture(            │
│         "D2", min_packets=100)                                     │
│                                                                     │
│  9. Verify interface counters                                      │
│     counters = intf_api.show_interface_counters_all("D2")         │
│     rx_packets = counters[0]["rx_ok"]                             │
│     if rx_packets >= packets_sent:                                 │
│         st.log("✅ Traffic verified")                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 6: CLEANUP                                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  10. Clean up temporary files                                      │
│      scapy_traffic.cleanup_scapy_script("D1")                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Usage Examples

### Example 1: Basic Unidirectional Traffic

```python
import pytest
from spytest import st, SpyTestDict
import apis.switching.vlan as vlan_api
import apis.routing.ip as ip_api
import apis.system.interface as intf_api
import apis.common.scapy_traffic as scapy_traffic

class TestVlanTraffic:

    def test_basic_l2_traffic(self):
        """Send basic Layer 2 traffic between two DUTs"""

        # Configuration
        dut1 = "D1"
        dut2 = "D2"
        vlan_id = 10
        dut1_ip = "10.1.1.1"
        dut2_ip = "10.1.1.2"
        dut1_port = "Ethernet8"
        dut2_port = "Ethernet8"

        # Step 1: Configure VLANs
        vlan_api.create_vlan(dut1, vlan_id)
        vlan_api.create_vlan(dut2, vlan_id)

        # Step 2: Add access ports
        vlan_api.add_vlan_member(dut1, vlan_id, dut1_port, tagging_mode=False)
        vlan_api.add_vlan_member(dut2, vlan_id, dut2_port, tagging_mode=False)

        # Step 3: Configure SVI IPs
        ip_api.config_ip_addr_interface(dut1, f"Vlan{vlan_id}", dut1_ip, subnet=24)
        ip_api.config_ip_addr_interface(dut2, f"Vlan{vlan_id}", dut2_ip, subnet=24)

        st.wait(3, "Wait for configuration to apply")

        # Step 4: Get MAC addresses
        src_mac = scapy_traffic.get_interface_mac(dut1, f"Vlan{vlan_id}")
        dst_mac = scapy_traffic.get_interface_mac(dut2, f"Vlan{vlan_id}")

        if not src_mac:
            src_mac = scapy_traffic.get_default_mac(1)
        if not dst_mac:
            dst_mac = scapy_traffic.get_default_mac(2)

        st.log(f"Source MAC: {src_mac}, Destination MAC: {dst_mac}")

        # Step 5: Clear counters
        intf_api.clear_interface_counters(dut1, interface_name=dut1_port)
        intf_api.clear_interface_counters(dut2, interface_name=dut2_port)

        # Step 6: Send traffic
        result = scapy_traffic.send_traffic(
            dut=dut1,
            interface=dut1_port,
            src_ip=dut1_ip,
            dst_ip=dut2_ip,
            src_mac=src_mac,
            dst_mac=dst_mac,
            duration=10,
            pps=1000,
            payload_size=200,
            traffic_type="udp"
        )

        # Step 7: Verify traffic sent
        if not result["success"]:
            st.report_fail("msg", f"Traffic generation failed: {result['output']}")

        packets_sent = result["packets_sent"]
        st.log(f"✅ Sent {packets_sent} packets")

        # Step 8: Verify counters
        st.wait(2, "Wait for counters to update")
        counters = intf_api.show_interface_counters_all(dut2)

        for entry in counters:
            if entry.get("iface") == dut2_port:
                rx_ok = int(str(entry.get("rx_ok", "0")).replace(",", ""))
                st.log(f"Received {rx_ok} packets on {dut2_port}")

                if rx_ok >= packets_sent:
                    st.report_pass("msg", f"Traffic verified: {rx_ok} packets received")
                else:
                    st.report_fail("msg", f"Insufficient packets: {rx_ok} < {packets_sent}")

        st.report_fail("msg", "Could not find counter for destination port")
```

---

### Example 2: Bidirectional Traffic with Packet Capture

```python
def test_bidirectional_traffic_with_capture(self):
    """Send bidirectional traffic and verify with tcpdump"""

    dut1 = "D1"
    dut2 = "D2"
    dut1_ip = "10.1.1.1"
    dut2_ip = "10.1.1.2"
    dut1_port = "Ethernet8"
    dut2_port = "Ethernet8"

    # Assume VLANs and IPs already configured (see Example 1)

    # Get MACs
    src_mac1 = scapy_traffic.get_interface_mac(dut1, "Vlan10") or \
               scapy_traffic.get_default_mac(1)
    src_mac2 = scapy_traffic.get_interface_mac(dut2, "Vlan10") or \
               scapy_traffic.get_default_mac(2)

    # Start packet capture on both DUTs
    st.banner("Starting packet capture")
    scapy_traffic.start_tcpdump(dut1, dut1_port, filter_str="udp port 54321")
    scapy_traffic.start_tcpdump(dut2, dut2_port, filter_str="udp port 54321")

    st.wait(1, "Wait for tcpdump to start")

    # Send traffic DUT1 → DUT2
    st.banner("Sending traffic DUT1 → DUT2")
    result1 = scapy_traffic.send_traffic(
        dut=dut1,
        interface=dut1_port,
        src_ip=dut1_ip,
        dst_ip=dut2_ip,
        src_mac=src_mac1,
        dst_mac=src_mac2,
        duration=5,
        pps=500
    )

    # Send traffic DUT2 → DUT1
    st.banner("Sending traffic DUT2 → DUT1")
    result2 = scapy_traffic.send_traffic(
        dut=dut2,
        interface=dut2_port,
        src_ip=dut2_ip,
        dst_ip=dut1_ip,
        src_mac=src_mac2,
        dst_mac=src_mac1,
        duration=5,
        pps=500
    )

    # Stop captures
    st.wait(2, "Wait for all packets to arrive")
    scapy_traffic.stop_tcpdump(dut1)
    scapy_traffic.stop_tcpdump(dut2)

    # Verify captures
    st.banner("Verifying packet captures")

    # DUT1 should have received packets from DUT2
    cap1 = scapy_traffic.verify_tcpdump_capture(
        dut1,
        capture_file="/tmp/tcpdump_capture.pcap",
        min_packets=100
    )

    # DUT2 should have received packets from DUT1
    cap2 = scapy_traffic.verify_tcpdump_capture(
        dut2,
        capture_file="/tmp/tcpdump_capture.pcap",
        min_packets=100
    )

    if cap1["success"] and cap2["success"]:
        st.log(f"✅ DUT1 captured {cap1['packet_count']} packets")
        st.log(f"✅ DUT2 captured {cap2['packet_count']} packets")
        st.report_pass("msg", "Bidirectional traffic verified with packet capture")
    else:
        st.report_fail("msg", "Packet capture verification failed")
```

---

### Example 3: Multiple Traffic Scenarios

```python
def test_multiple_packet_sizes(self):
    """Test traffic with different packet sizes"""

    packet_sizes = [64, 128, 256, 512, 1024, 1500]

    for packet_size in packet_sizes:
        st.banner(f"Testing with packet size: {packet_size} bytes")

        result = scapy_traffic.send_traffic(
            dut="D1",
            interface="Ethernet8",
            src_ip="10.1.1.1",
            dst_ip="10.1.1.2",
            src_mac="52:54:00:aa:bb:01",
            dst_mac="52:54:00:aa:bb:02",
            duration=5,
            pps=500,
            payload_size=packet_size - 42,  # Subtract headers
            traffic_type="udp"
        )

        if result["success"]:
            st.log(f"✅ {packet_size}B packets: {result['packets_sent']} sent")
        else:
            st.error(f"❌ {packet_size}B packets: Failed")
            st.report_fail("msg", f"Traffic failed for packet size {packet_size}")

    st.report_pass("msg", "All packet sizes tested successfully")
```

---

## Log Files and Debugging

### Where to Find Logs

#### 1. SPyTest Test Logs
```
<logs-path>/
├── dlog-D1-<devicename>.log     # DUT1 device logs (commands + output)
├── dlog-D2-<devicename>.log     # DUT2 device logs
├── module_<modulename>.log      # Per-module test logs
├── result.log                   # Test execution log
└── results.html                 # HTML report
```

#### 2. Scapy Traffic Script Logs

**Script Location on Device:**
```
/tmp/scapy_traffic_sender.py     # Generated Scapy script
```

**To view script on device:**
```bash
# Via SPyTest
st.show(dut, "cat /tmp/scapy_traffic_sender.py", skip_tmpl=True)

# Manually on device
cat /tmp/scapy_traffic_sender.py
```

#### 3. Packet Capture Files

**Default Location:**
```
/tmp/tcpdump_capture.pcap        # Packet capture file on device
```

**To analyze capture:**
```bash
# On device
tcpdump -r /tmp/tcpdump_capture.pcap

# Read capture with detailed output
tcpdump -r /tmp/tcpdump_capture.pcap -vv -X
```

### Log Analysis Patterns

#### Finding Scapy Traffic Generation in Logs

**Search Pattern:**
```bash
# In dlog-D1-*.log
grep -A 20 "Scapy traffic" dlog-D1-*.log
grep -A 10 "send_traffic" dlog-D1-*.log
grep -A 5 "Layer 2 traffic" dlog-D1-*.log
```

**Example Log Output:**
```
2026-03-09 10:15:23,456 INFO  Generating Layer 2 Scapy traffic: src=10.1.1.1 dst=10.1.1.2 packet_size=64B duration=10s packets=1000
2026-03-09 10:15:23,457 INFO  Retrieving source MAC from Vlan10 on D1
2026-03-09 10:15:23,501 INFO  Found MAC address: 52:54:00:d3:78:35
2026-03-09 10:15:23,502 INFO  Source MAC: 52:54:00:d3:78:35
2026-03-09 10:15:23,503 INFO  Retrieving destination MAC from Vlan10 on D2
2026-03-09 10:15:23,548 INFO  Found MAC address: 52:54:00:d3:78:36
2026-03-09 10:15:23,549 INFO  Destination MAC: 52:54:00:d3:78:36
2026-03-09 10:15:23,550 BANNER ==================== Sending Layer 2 traffic via Ethernet8 ====================
2026-03-09 10:15:23,551 INFO    Source: 10.1.1.1 (52:54:00:d3:78:35)
2026-03-09 10:15:23,552 INFO    Destination: 10.1.1.2 (52:54:00:d3:78:36)
2026-03-09 10:15:23,553 INFO    Interface: Ethernet8
2026-03-09 10:15:23,554 INFO    Rate: 100 pps, Duration: 10s, Total: 1000 packets
2026-03-09 10:15:35,123 INFO  Scapy traffic output:
[+] Starting UDP traffic generation
    Interface:    Ethernet8
    Source:       10.1.1.1 (52:54:00:d3:78:35)
    Destination:  10.1.1.2 (52:54:00:d3:78:36)
    Duration:     10 seconds
    Rate:         100 pps
    Payload:      200 bytes

[→] Sent 100 packets (1.0s elapsed)...
[→] Sent 200 packets (2.0s elapsed)...
[→] Sent 300 packets (3.0s elapsed)...
...
[✓] Completed. Sent 1000 packets in 10.02 seconds (100 pps)
2026-03-09 10:15:35,124 INFO  ✅ Layer 2 traffic generation successful: 1000 packets sent
```

#### Finding Counter Verification in Logs

**Search Pattern:**
```bash
grep -A 5 "RX_OK\|rx_ok\|Received.*packets" dlog-D2-*.log
```

**Example Log Output:**
```
2026-03-09 10:15:37,234 INFO  Getting RX counters for Ethernet8
2026-03-09 10:15:37,456 INFO  Interface Ethernet8 RX_OK: 1000
2026-03-09 10:15:37,457 INFO  Received 1000 packets on Ethernet8
2026-03-09 10:15:37,458 INFO  📊 Packets received: 1000 (Baseline: 0, Current: 1000)
2026-03-09 10:15:37,459 INFO  ✅ SUCCESS: Received 1000 packets (expected minimum: 100)
```

### Debugging Failed Traffic

**Common Issues and Log Patterns:**

#### Issue 1: MAC Address Retrieval Failed
```
ERROR  Could not extract MAC address for Ethernet8 on D1
WARN   Could not retrieve MAC for Vlan10 on D1, using default
INFO   Source MAC: 52:54:00:00:00:01
```
**Solution:** Check interface status, verify VLAN configuration

#### Issue 2: Script Creation Failed
```
ERROR  Failed to create Scapy script on D1: Permission denied
```
**Solution:** Check write permissions on /tmp directory

#### Issue 3: No Traffic Sent
```
ERROR  ❌ Layer 2 traffic generation failed: Error: [Errno 19] No such device
```
**Solution:** Verify interface name is correct and interface is up

#### Issue 4: Zero Packets Received
```
INFO   Interface Ethernet8 RX_OK: 0
ERROR  ❌ FAILED: Only 0 packets received (expected minimum: 100)
```
**Solution:** Check VLAN membership, verify routing, check ARP resolution

---

## Best Practices

### 1. Always Retrieve Real MACs

✅ **Good:**
```python
src_mac = scapy_traffic.get_interface_mac(dut1, "Vlan10")
if not src_mac:
    src_mac = scapy_traffic.get_default_mac(1)
```

❌ **Bad:**
```python
src_mac = "52:54:00:00:00:01"  # Hardcoded - may not work
```

### 2. Use Access Ports (Untagged)

For simple L3 SVI traffic, use **access ports** (untagged VLAN members):

✅ **Good:**
```python
vlan_api.add_vlan_member(dut, vlan_id, port, tagging_mode=False)  # Access port
```

❌ **Avoid (unless needed):**
```python
vlan_api.add_vlan_member(dut, vlan_id, port, tagging_mode=True)   # Trunk port
# Requires VLAN tagging in packets
```

### 3. Clear Counters Before Traffic

✅ **Good:**
```python
intf_api.clear_interface_counters(dut, interface_name=port)
st.wait(1)  # Wait for clear to complete
# Send traffic
# Verify counters
```

### 4. Use Appropriate Traffic Type

- **UDP**: Best for most tests (stateless, no handshake)
- **ICMP**: Good for connectivity tests, but may be rate-limited
- **TCP**: Use for protocol-specific tests (requires handshake)

### 5. Calculate Payload Size Correctly

```python
# For 64-byte packets:
# Ethernet header: 14 bytes
# IP header: 20 bytes
# UDP header: 8 bytes
# Total headers: 42 bytes
# Payload: 64 - 42 = 22 bytes

result = scapy_traffic.send_traffic(
    ...
    payload_size=64 - 42  # 22 bytes payload
)
```

### 6. Add Wait Time After Configuration

```python
vlan_api.create_vlan(dut, vlan_id)
ip_api.config_ip_addr_interface(dut, "Vlan10", "10.1.1.1/24")
st.wait(3, "Wait for configuration to apply")  # Important!
```

### 7. Verify Traffic Generation Success

✅ **Good:**
```python
result = scapy_traffic.send_traffic(...)
if not result["success"]:
    st.report_fail("msg", f"Traffic failed: {result['output']}")
packets_sent = result["packets_sent"]
```

❌ **Bad:**
```python
result = scapy_traffic.send_traffic(...)
# Assume it worked without checking
```

### 8. Use Realistic Traffic Rates

```python
# For 10-second test:
duration = 10
pps = 100  # 100 packets/sec = 1000 total packets (realistic)

# Avoid:
pps = 10000  # May overwhelm virtual devices
```

### 9. Log Important Information

```python
st.log(f"Source MAC: {src_mac}")
st.log(f"Destination MAC: {dst_mac}")
st.log(f"Sending {total_packets} packets at {pps} pps")
st.log(f"Traffic sent: {result['packets_sent']} packets")
```

### 10. Clean Up Temporary Files

```python
# At end of test or in epilogue
scapy_traffic.cleanup_scapy_script(dut)
```

---

## Common Patterns

### Pattern 1: Wrapper Function for Traffic Generation

```python
def send_l2_traffic(self, source_dut, dest_dut, source_ip, dest_ip,
                     source_port, vlan_name="Vlan10", duration=10, pps=1000):
    """Reusable wrapper for Layer 2 traffic generation"""

    # Get MACs
    src_mac = scapy_traffic.get_interface_mac(source_dut, vlan_name)
    dst_mac = scapy_traffic.get_interface_mac(dest_dut, vlan_name)

    if not src_mac:
        src_mac = scapy_traffic.get_default_mac(1)
    if not dst_mac:
        dst_mac = scapy_traffic.get_default_mac(2)

    # Send traffic
    result = scapy_traffic.send_traffic(
        dut=source_dut,
        interface=source_port,
        src_ip=source_ip,
        dst_ip=dest_ip,
        src_mac=src_mac,
        dst_mac=dst_mac,
        duration=duration,
        pps=pps,
        traffic_type="udp"
    )

    return result
```

### Pattern 2: Traffic with Verification

```python
def send_and_verify_traffic(self, source_dut, dest_dut, dest_port, **traffic_params):
    """Send traffic and verify counters"""

    # Clear counters
    intf_api.clear_interface_counters(dest_dut, interface_name=dest_port)
    st.wait(1)

    # Send traffic
    result = self.send_l2_traffic(**traffic_params)

    if not result["success"]:
        return False

    # Verify counters
    st.wait(2)
    counters = intf_api.show_interface_counters_all(dest_dut)

    for entry in counters:
        if entry.get("iface") == dest_port:
            rx_ok = int(str(entry.get("rx_ok", "0")).replace(",", ""))
            packets_sent = result["packets_sent"]

            if rx_ok >= packets_sent:
                st.log(f"✅ Verified: {rx_ok} packets received")
                return True

    return False
```

### Pattern 3: Bidirectional Traffic Loop

```python
def test_bidirectional_traffic(self):
    """Send traffic in both directions"""

    scenarios = [
        {"src": "D1", "dst": "D2", "src_ip": "10.1.1.1", "dst_ip": "10.1.1.2"},
        {"src": "D2", "dst": "D1", "src_ip": "10.1.1.2", "dst_ip": "10.1.1.1"}
    ]

    for scenario in scenarios:
        st.banner(f"Traffic: {scenario['src']} → {scenario['dst']}")

        success = self.send_and_verify_traffic(
            source_dut=scenario["src"],
            dest_dut=scenario["dst"],
            source_ip=scenario["src_ip"],
            dest_ip=scenario["dst_ip"],
            source_port="Ethernet8",
            dest_port="Ethernet8",
            duration=10,
            pps=1000
        )

        if not success:
            st.report_fail("msg", f"Traffic failed: {scenario['src']} → {scenario['dst']}")

    st.report_pass("msg", "Bidirectional traffic verified")
```

---

## Troubleshooting

### Problem: "No such device" Error

**Symptom:**
```
ERROR  Error: [Errno 19] No such device
```

**Cause:** Interface name incorrect or interface down

**Solution:**
```python
# Verify interface exists
output = st.show(dut, "show interfaces status", type="click")
st.log(f"Available interfaces: {output}")

# Verify interface is up
intf_api.interface_operation(dut, interface, operation="startup")
st.wait(2)
```

---

### Problem: Zero Packets Received

**Symptom:**
```
INFO  Interface Ethernet8 RX_OK: 0
```

**Possible Causes:**
1. Interface not in same VLAN
2. Wrong MAC addresses
3. ARP not resolved
4. Interface counters not updating

**Debug Steps:**
```python
# 1. Verify VLAN membership
vlan_config = vlan_api.show_vlan_config(dut)
st.log(f"VLAN config: {vlan_config}")

# 2. Check ARP table
arp_output = st.show(dut, "show ip arp", type="klish")
st.log(f"ARP table: {arp_output}")

# 3. Check interface status
intf_status = st.show(dut, f"show interface {interface}", type="klish", skip_tmpl=True)
st.log(f"Interface status: {intf_status}")

# 4. Use tcpdump to verify packets
scapy_traffic.start_tcpdump(dest_dut, dest_port)
# Send traffic
scapy_traffic.stop_tcpdump(dest_dut)
result = scapy_traffic.verify_tcpdump_capture(dest_dut, min_packets=1)
st.log(f"Captured packets: {result['packet_count']}")
```

---

### Problem: MAC Address Not Retrieved

**Symptom:**
```
WARN  Could not retrieve MAC for Vlan10 on D1, using default
```

**Possible Causes:**
1. VLAN interface not created
2. Interface not up
3. CLI type mismatch

**Solution:**
```python
# Try different CLI types
for cli_type in ["klish", "click"]:
    mac = scapy_traffic.get_interface_mac(dut, interface, cli_type=cli_type)
    if mac:
        st.log(f"✅ Got MAC using {cli_type}: {mac}")
        break

# Manually check
output = st.show(dut, f"show interface {interface}", type="klish", skip_tmpl=True)
st.log(f"Manual check: {output}")
```

---

### Problem: Script Execution Timeout

**Symptom:**
```
ERROR  Command timeout after 120 seconds
```

**Cause:** Traffic duration too long or PPS too high

**Solution:**
```python
# Reduce duration or PPS
result = scapy_traffic.send_traffic(
    ...
    duration=5,   # Shorter duration
    pps=100       # Lower rate
)
```

---

## Summary

### Quick Reference Card

```python
# Import
import apis.common.scapy_traffic as scapy_traffic

# Get MAC
mac = scapy_traffic.get_interface_mac(dut, "Vlan10", cli_type="klish")

# Send traffic (most common)
result = scapy_traffic.send_traffic(
    dut="D1",
    interface="Ethernet8",
    src_ip="10.1.1.1",
    dst_ip="10.1.1.2",
    src_mac=src_mac,
    dst_mac=dst_mac,
    duration=10,
    pps=1000,
    traffic_type="udp"
)

# Verify ping
success = scapy_traffic.verify_ping("D1", "10.1.1.2", src_ip="10.1.1.1")

# Packet capture
scapy_traffic.start_tcpdump("D2", "Ethernet8", filter_str="udp port 54321")
# ... send traffic ...
scapy_traffic.stop_tcpdump("D2")
result = scapy_traffic.verify_tcpdump_capture("D2", min_packets=100)

# Cleanup
scapy_traffic.cleanup_scapy_script("D1")
```

### Key Concepts

1. **Layer 2 = Ethernet headers + MAC addresses**
2. **Use sendp() not send()**
3. **Specify physical interface**
4. **Get MACs from VLAN SVIs for L3 forwarding**
5. **Access ports = no VLAN tag needed**
6. **Always verify result["success"]**
7. **Clear counters before traffic**
8. **Log files: dlog-D1-*.log, module_*.log**

---

## Related Documentation

- **SPyTest Framework Guide:** `Doc/intro.md`
- **VLAN API Reference:** `apis/switching/vlan.py`
- **Interface API Reference:** `apis/system/interface.py`
- **Project Instructions:** `CLAUDE.md`

---

**End of Guide**
