# L3-12: DSCP EF (Expedited Forwarding) Matching - Manual Test Execution Guide

**Status**: Ready for Execution (Advanced Scapy API)
**Test Case**: L3-12
**Scenario**: Deny traffic with DSCP EF (Expedited Forwarding) marking
**ACL Action**: DENY traffic with DSCP=46 (EF marking)
**Expected RX**: 0 packets (all EF-marked packets blocked)

---

## Test Overview

This test validates **DSCP/ToS byte matching** in ACL rules. The ACL rule denies IP packets marked with **DSCP EF (Expedited Forwarding)**, which is used in QoS to prioritize voice, video, and real-time applications.

**What is DSCP?**
- **DSCP**: Differentiated Services Code Point (6 bits in IP header)
- **ToS**: Type of Service byte (older term, same location in IP header)
- **EF**: Expedited Forwarding - highest priority (DSCP value = 46 = 0xB8)

**DSCP Value Reference**:
```
Default Forwarding (DF):     0 (0x00)
Class Selector 1:            8 (0x08)
Assured Forwarding 11:      10 (0x0A)
Expedited Forwarding (EF):  46 (0x2E) ← This test
Voice Admit:                44 (0x2C)
```

**Traffic Flow**:
```
DUT2 (Scapy) → TX IP packets with DSCP=46 (EF marking)
               ↓
        DUT1:Ethernet0 [ACL INGRESS]
        ├─ Rule: DENY DSCP=46
        └─ Action: DROP EF-marked packets
               ↓
           All EF packets dropped - RX=0 on DUT3
```

**Real-World Use Case**:
- Block voice/video traffic in certain network zones
- Prevent QoS marking bypass attempts
- Enforce security policies on latency-sensitive applications

---

## Prerequisites

### Verify Scapy Supports DSCP

```bash
admin@sonic:~$ python3 << 'EOF'
from scapy.all import IP

# Test DSCP construction
pkt = IP(dst="20.0.0.2", tos=0xB8)  # DSCP EF = tos 0xB8
dscp_value = (pkt.tos >> 2) & 0x3F  # Extract DSCP (6 bits)
print(f"IP ToS byte: 0x{pkt.tos:02X}")
print(f"DSCP value: {dscp_value}")
print(f"Expected DSCP for EF: 46")
print(f"Match: {dscp_value == 46}")
EOF

IP ToS byte: 0xB8
DSCP value: 46
Expected DSCP for EF: 46
Match: True
```

---

## Step-by-Step Execution

### Step 1: SSH to All DUTs

```bash
# DUT1 - ACL Device
ssh admin@192.168.100.125

# DUT2 - TX Host
ssh admin@192.168.100.248

# DUT3 - RX Host
ssh admin@192.168.100.134
```

---

### Step 2: Create ACL with DSCP Filter on DUT1

```bash
admin@sonic:~$ config acl add table L3_ACL_TABLE_L312 L3 -D INGRESS -p Ethernet0
```

**Add rule to deny DSCP=46 (EF)**:
```bash
admin@sonic:~$ config acl add rule L3_ACL_TABLE_L312 RULE_1_DENY_DSCP_EF \
  --PACKET_ACTION DROP \
  --DSCP 46
```

**Add permit rule for non-EF traffic**:
```bash
admin@sonic:~$ config acl add rule L3_ACL_TABLE_L312 RULE_2_PERMIT_OTHER \
  --PACKET_ACTION FORWARD
```

**Verify ACL**:
```bash
admin@sonic:~$ show acl rule L3_ACL_TABLE_L312
Rule: RULE_1_DENY_DSCP_EF
  Packet action: DROP
  DSCP: 46
  Hit counter: 0

Rule: RULE_2_PERMIT_OTHER
  Packet action: FORWARD
  Hit counter: 0
```

---

### Step 3: Start Tcpdump on DUT3

```bash
admin@sonic:~$ sudo tcpdump -i Ethernet0 -w /tmp/l3_12_rx.pcap "udp port 54321" &
[1] 12345
tcpdump: listening on Ethernet0, link-type EN10MB (Ethernet), snapshot length 65535 bytes
```

---

### Step 4: Generate EF-Marked Packets on DUT2

Create Scapy script that generates IP packets with DSCP=46 (EF):

```bash
admin@sonic:~$ cat > /tmp/l3_12_dscp_ef.py << 'EOF'
#!/usr/bin/env python3

from scapy.all import IP, UDP, Ether, send, get_if_hwaddr
from time import sleep

src_ip = "10.0.0.1"
dst_ip = "20.0.0.2"
src_port = 12345
dst_port = 54321
num_packets = 100
interface = "Ethernet0"
pps = 10

src_mac = get_if_hwaddr(interface)
dst_mac = "22:d5:dc:51:9e:f3"  # DUT1:Ethernet0

print(f"[*] Sending {num_packets} IP packets with DSCP=46 (EF - Expedited Forwarding)")
print(f"[*] These packets are marked for QoS priority (voice/video)")
print(f"[*] ACL rule DENIES packets with DSCP=46")
print(f"[*] Expected: RX=0 (all EF packets blocked)")

# DSCP EF = 46, which maps to ToS byte
# ToS byte calculation: (DSCP << 2) | (ECN)
# For DSCP=46, ECN=0: ToS = 46 << 2 = 184 (0xB8)
dscp_ef_tos = 46 << 2  # Convert DSCP to ToS byte

for i in range(num_packets):
    packet = Ether(dst=dst_mac, src=src_mac) / \
             IP(src=src_ip, dst=dst_ip, tos=dscp_ef_tos) / \
             UDP(sport=src_port, dport=dst_port) / \
             b"L3_12_DSCP_EF_EXPEDITED_FORWARDING"

    send(packet, iface=interface, verbose=False)

    if (i + 1) % pps == 0:
        sleep(1)

    if (i + 1) % 25 == 0:
        print(f"[+] Sent {i+1}/{num_packets} EF-marked packets")

print(f"[✓] Sent {num_packets} packets with DSCP=46 (EF)")
EOF

chmod +x /tmp/l3_12_dscp_ef.py
python3 /tmp/l3_12_dscp_ef.py
```

**Output**:
```
[*] Sending 100 IP packets with DSCP=46 (EF - Expedited Forwarding)
[*] These packets are marked for QoS priority (voice/video)
[*] ACL rule DENIES packets with DSCP=46
[*] Expected: RX=0 (all EF packets blocked)
[+] Sent 25/100 EF-marked packets
[+] Sent 50/100 EF-marked packets
[+] Sent 75/100 EF-marked packets
[+] Sent 100/100 EF-marked packets
[✓] Sent 100 packets with DSCP=46 (EF)
```

---

### Step 5: Verify ACL Hit Counter on DUT1

```bash
admin@sonic:~$ show acl rule L3_ACL_TABLE_L312
Rule: RULE_1_DENY_DSCP_EF
  Packet action: DROP
  DSCP: 46
  Hit counter: 100  ✓ (all EF packets matched)

Rule: RULE_2_PERMIT_OTHER
  Packet action: FORWARD
  Hit counter: 0    ✓ (no non-EF packets)
```

---

### Step 6: Stop Tcpdump and Verify

On **DUT3**:
```bash
admin@sonic:~$ sleep 2 && sudo pkill -f "tcpdump"

# Analyze pcap
admin@sonic:~$ python3 << 'EOF'
from scapy.all import rdpcap, IP

pcap_file = "/tmp/l3_12_rx.pcap"
packets = rdpcap(pcap_file)
print(f"Packets captured: {len(packets)}")
print(f"Expected: 0 (all EF packets denied)")

if len(packets) > 0:
    for pkt in packets[:3]:
        if pkt.haslayer(IP):
            dscp = (pkt[IP].tos >> 2) & 0x3F
            print(f"ERROR: Unexpected packet with DSCP={dscp}")
EOF

Packets captured: 0
Expected: 0 (all EF packets denied)
```

---

### Step 7: Extended Test - Send Non-EF Packets

To verify **only EF** packets are blocked:

```bash
admin@sony:~$ cat > /tmp/l3_12_non_ef.py << 'EOF'
#!/usr/bin/env python3

from scapy.all import IP, UDP, Ether, send, get_if_hwaddr
from time import sleep

src_ip = "10.0.0.1"
dst_ip = "20.0.0.2"
src_port = 12345
dst_port = 54321
interface = "Ethernet0"

src_mac = get_if_hwaddr(interface)
dst_mac = "22:d5:dc:51:9e:f3"

print("[*] Sending 50 IP packets with DSCP=10 (NOT EF)")
print("[*] These packets should be PERMITTED (rule only denies DSCP=46)")

# Different DSCP values to test
dscp_values = {
    0: "Default (DF)",
    10: "AF11",
    18: "AF12",
    26: "AF13",
}

for dscp in dscp_values.keys():
    tos = dscp << 2
    packet = Ether(dst=dst_mac, src=src_mac) / \
             IP(src=src_ip, dst=dst_ip, tos=tos) / \
             UDP(sport=src_port, dport=dst_port) / \
             b"NON_EF_TRAFFIC"

    for _ in range(10):
        send(packet, iface=interface, verbose=False)

print("[✓] Sent 50 non-EF packets (various DSCP values)")
EOF

python3 /tmp/l3_12_non_ef.py
```

**Check DUT1 hit counters**:
```bash
admin@sonic:~$ show acl rule L3_ACL_TABLE_L312
Rule: RULE_1_DENY_DSCP_EF
  Hit counter: 100  (unchanged - no new EF packets)

Rule: RULE_2_PERMIT_OTHER
  Hit counter: 50   ✓ (non-EF packets matched PERMIT)
```

**Check DUT3 pcap**:
```bash
admin@sonic:~$ python3 << 'EOF'
from scapy.all import rdpcap, IP

packets = rdpcap("/tmp/l3_12_rx.pcap")
print(f"Total packets: {len(packets)}")
print(f"Expected: 50 (non-EF packets allowed)")

# Verify no EF packets
has_ef = False
for pkt in packets:
    if pkt.haslayer(IP):
        dscp = (pkt[IP].tos >> 2) & 0x3F
        if dscp == 46:
            has_ef = True

print(f"Contains DSCP=46 (EF): {has_ef}")
EOF

Total packets: 50
Expected: 50 (non-EF packets allowed)
Contains DSCP=46 (EF): False
```

---

## Cleanup

```bash
# DUT1
admin@sonic:~$ config acl remove table L3_ACL_TABLE_L312

# DUT2 & DUT3
admin@sonic:~$ rm -f /tmp/l3_12_*.py /tmp/l3_12_rx.pcap
```

---

## DSCP Values Reference

**Common DSCP Values**:
```
AF (Assured Forwarding):
  AF11: 10  (0x28)
  AF12: 12  (0x30)
  AF13: 14  (0x38)
  AF21: 18  (0x48)
  AF22: 20  (0x50)
  AF23: 22  (0x58)
  ... (CS1-CS7 variants)

EF (Expedited Forwarding):
  EF:   46  (0xB8)  ← This test

Class Selector (Legacy):
  CS0: 0    (0x00)  - Default
  CS1: 8    (0x20)
  CS2: 16   (0x40)
  ... CS7
```

---

## Real-World Use Cases

### Scenario 1: Block Voice/Video Across DMZ

```
Policy: Prevent VoIP/Video from escaping corporate network
Rule: DENY DSCP=46 (EF) on DMZ interface
Effect: No voice/video traffic to internet
```

### Scenario 2: Enforce QoS Policies

```
Policy: Only allow EF marking for authenticated VoIP
Rule: PERMIT DSCP=46 only from specific server IP
Effect: Prevents QoS spoofing attacks
```

### Scenario 3: Capacity Protection

```
Policy: Limit EF traffic to 20Mbps
Rule 1: DENY DSCP=46 if rate > 20Mbps (requires rate-based ACL)
Effect: Prevents EF traffic exhaustion
```

---

## Key Concepts

### IP Header ToS Byte Layout

```
Bit:     0   1   2   3   4   5   6   7
      [  DSCP (6 bits)  ] [ECN (2 bits)]

DSCP value extracted as: (tos_byte >> 2) & 0x3F
```

### DSCP vs ToS

| Aspect | ToS | DSCP |
|--------|-----|------|
| Age | Legacy (RFC 791) | Modern (RFC 2474) |
| Purpose | Type of Service | QoS marking |
| Bits | 8 bits | 6 bits (DSCP) + 2 bits (ECN) |
| Scope | Original IPv4 | Modern QoS networks |

---

## Document Information

**Version**: 1.0
**Created**: 2026-03-11
**Test Case**: L3-12 (DSCP EF Matching)
**Requires**: Advanced Scapy with IP ToS support
**Domain**: QoS/DiffServ ACLing

---

**Key Insight**: DSCP matching enables QoS-aware security policies, crucial for networks with voice, video, and real-time applications.
