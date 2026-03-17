# L3-08: TCP SYN Flag Matching - Manual Test Execution Guide

**Status**: Ready for Execution (Advanced Scapy API)
**Test Case**: L3-08
**Scenario**: Deny TCP SYN packets (connection initiation)
**ACL Action**: DENY TCP packets with SYN flag set
**Expected RX**: 0 packets (all SYN packets blocked)

---

## Test Overview

This test validates advanced ACL functionality: **TCP flag matching**. The ACL rule specifically matches TCP packets with the **SYN flag** set (connection initiation requests) and denies them.

**Traffic Flow**:
```
DUT2 (Scapy) → TX TCP packets with SYN flag set
               ↓
        DUT1:Ethernet0 [ACL INGRESS]
        ├─ Rule: DENY TCP flags:SYN
        └─ Action: DROP packets with SYN flag
               ↓
           All SYN packets dropped - RX=0 on DUT3
```

**Key Concept**: TCP SYN packets are the first step in TCP connection establishment (3-way handshake). By denying SYN packets, no new connections can be initiated.

**TCP Flags Overview**:
- **SYN (0x02)**: Connection initiation
- **ACK (0x10)**: Acknowledgment
- **RST (0x04)**: Connection reset
- **FIN (0x01)**: Connection termination
- **PSH (0x08)**: Push data
- **URG (0x20)**: Urgent pointer

---

## Prerequisites

### Test Requirements

Before executing this test, ensure:

1. **Scapy version supports TCP flag construction**:
```bash
admin@sonic:~$ python3 -c "from scapy.all import TCP; pkt = TCP(flags='S'); print(f'TCP SYN packet: {pkt}')"
TCP/Sport=20 Dport=80 seq=0 ack=0 flags=S
```

2. **DUT supports TCP flag matching in ACL**:
```bash
# Check if DUT supports TCP flags in ACL rules
admin@sonic:~$ show acl actions
ACL Actions:
  - PACKET_ACTION (forward/drop/copy)
  - TCP_FLAGS    ✓ (supported)
```

---

## Step-by-Step Execution

### Step 1: SSH Access to All DUTs

**Terminal 1 - DUT1**:
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@192.168.100.125
```

**Terminal 2 - DUT2**:
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@192.168.100.248
```

**Terminal 3 - DUT3**:
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@192.168.100.134
```

---

### Step 2: Verify L3 Configuration

```bash
# On DUT1
admin@sonic:~$ show ip address | grep Ethernet0
Ethernet0  10.0.0.254/24  default

# On DUT2
admin@sonic:~$ show ip address | grep Ethernet0
Ethernet0  10.0.0.1/24  default

# On DUT3
admin@sonic:~$ show ip address | grep Ethernet0
Ethernet0  20.0.0.2/24  default
```

---

### Step 3: Create ACL with TCP SYN Filter

On **DUT1**, create ACL rule that denies TCP SYN packets:

```bash
admin@sonic:~$ config acl add table L3_ACL_TABLE_L308 L3 -D INGRESS -p Ethernet0
```

**Add rule to deny TCP SYN packets**:
```bash
admin@sonic:~$ config acl add rule L3_ACL_TABLE_L308 RULE_1_DENY_TCP_SYN \
  --PACKET_ACTION DROP \
  --PROTO TCP \
  --TCP_FLAGS SYN
```

**Add fallback PERMIT rule for non-SYN TCP traffic**:
```bash
admin@sonic:~$ config acl add rule L3_ACL_TABLE_L308 RULE_2_PERMIT_OTHER_TCP \
  --PACKET_ACTION FORWARD \
  --PROTO TCP
```

**Verify ACL**:
```bash
admin@sonic:~$ show acl rule L3_ACL_TABLE_L308
Rule: RULE_1_DENY_TCP_SYN
  Packet action: DROP
  PROTO: TCP
  TCP_FLAGS: SYN
  Hit counter: 0

Rule: RULE_2_PERMIT_OTHER_TCP
  Packet action: FORWARD
  PROTO: TCP
  Hit counter: 0
```

---

### Step 4: Start Tcpdump on DUT3

On **DUT3**:
```bash
admin@sonic:~$ sudo tcpdump -i Ethernet0 -w /tmp/l3_08_rx.pcap "tcp port 12345" &
[1] 12345
tcpdump: listening on Ethernet0, link-type EN10MB (Ethernet), snapshot length 65535 bytes
```

---

### Step 5: Generate TCP SYN Packets on DUT2

Create Scapy script that generates TCP packets with **SYN flag** set:

```bash
admin@sonic:~$ cat > /tmp/l3_08_tcp_syn.py << 'EOF'
#!/usr/bin/env python3

from scapy.all import IP, TCP, Ether, send, get_if_hwaddr
from time import sleep
import sys

# Configuration
src_ip = "10.0.0.1"
dst_ip = "20.0.0.2"
src_port = 12345
dst_port = 80
num_packets = 100
interface = "Ethernet0"
pps = 10

src_mac = get_if_hwaddr(interface)
dst_mac = "22:d5:dc:51:9e:f3"  # DUT1:Ethernet0 MAC

print(f"[*] Generating {num_packets} TCP SYN packets")
print(f"[*] These packets have TCP SYN flag set (connection initiation)")
print(f"[*] ACL rule DENIES TCP SYN packets")
print(f"[*] Expected: RX=0 (all packets blocked)")

# Create TCP SYN packets
seq_num = 1000
for i in range(num_packets):
    # TCP SYN packet (flags='S')
    packet = Ether(dst=dst_mac, src=src_mac) / \
             IP(src=src_ip, dst=dst_ip) / \
             TCP(sport=src_port, dport=dst_port,
                 flags='S',          # SYN flag
                 seq=seq_num)

    send(packet, iface=interface, verbose=False)
    seq_num += 1

    if (i + 1) % pps == 0:
        sleep(1)

    if (i + 1) % 25 == 0:
        print(f"[+] Sent {i+1}/{num_packets} SYN packets")

print(f"[✓] Completed: {num_packets} TCP SYN packets sent")
EOF

chmod +x /tmp/l3_08_tcp_syn.py
python3 /tmp/l3_08_tcp_syn.py
```

**Output**:
```
[*] Generating 100 TCP SYN packets
[*] These packets have TCP SYN flag set (connection initiation)
[*] ACL rule DENIES TCP SYN packets
[*] Expected: RX=0 (all packets blocked)
[+] Sent 25/100 SYN packets
[+] Sent 50/100 SYN packets
[+] Sent 75/100 SYN packets
[+] Sent 100/100 SYN packets
[✓] Completed: 100 TCP SYN packets sent
```

---

### Step 6: Verify ACL Hit Counter

On **DUT1**:
```bash
admin@sonic:~$ show acl rule L3_ACL_TABLE_L308
Rule: RULE_1_DENY_TCP_SYN
  Packet action: DROP
  PROTO: TCP
  TCP_FLAGS: SYN
  Hit counter: 100  ✓ (all SYN packets matched)

Rule: RULE_2_PERMIT_OTHER_TCP
  Packet action: FORWARD
  PROTO: TCP
  Hit counter: 0   ✓ (no non-SYN packets)
```

---

### Step 7: Stop Tcpdump on DUT3

```bash
admin@sonic:~$ sleep 2
admin@sonic:~$ sudo pkill -f "tcpdump -i Ethernet0"
[1]+  Terminated
```

---

### Step 8: Analyze Pcap

On **DUT3**, verify no packets were captured:

```bash
admin@sonic:~$ python3 << 'PYTHON_EOF'
from scapy.all import rdpcap

pcap_file = "/tmp/l3_08_rx.pcap"
packets = rdpcap(pcap_file)
print(f"Packets captured: {len(packets)}")
print(f"Expected: 0 (all SYN packets denied)")

if len(packets) > 0:
    for pkt in packets[:5]:
        print(f"ERROR: Unexpected packet: {pkt.summary()}")
else:
    print("[✓] Confirmed: No TCP SYN packets reached DUT3")
PYTHON_EOF

Packets captured: 0
Expected: 0 (all SYN packets denied)
[✓] Confirmed: No TCP SYN packets reached DUT3
```

---

### Step 9: Extended Test - Send Non-SYN Packets

To verify that **only SYN** packets are blocked (not all TCP), send packets with different flags:

```bash
admin@sony:~$ cat > /tmp/l3_08_tcp_ack.py << 'EOF'
#!/usr/bin/env python3

from scapy.all import IP, TCP, Ether, send, get_if_hwaddr
from time import sleep

src_ip = "10.0.0.1"
dst_ip = "20.0.0.2"
src_port = 12345
dst_port = 80
interface = "Ethernet0"

src_mac = get_if_hwaddr(interface)
dst_mac = "22:d5:dc:51:9e:f3"

print("[*] Sending TCP ACK packets (not SYN)")
print("[*] ACL rule only denies SYN, so ACK should be PERMITTED")
print("[*] Expected: RX > 0 (ACK packets allowed)")

for i in range(50):
    # TCP ACK packet (flags='A')
    packet = Ether(dst=dst_mac, src=src_mac) / \
             IP(src=src_ip, dst=dst_ip) / \
             TCP(sport=src_port, dport=dst_port,
                 flags='A',  # ACK flag only (not SYN)
                 seq=2000+i,
                 ack=3000)

    send(packet, iface=interface, verbose=False)

print("[✓] Sent 50 TCP ACK packets")
EOF

python3 /tmp/l3_08_tcp_ack.py
```

**Check results on DUT1**:
```bash
admin@sonic:~$ show acl rule L3_ACL_TABLE_L308
Rule: RULE_1_DENY_TCP_SYN
  Hit counter: 100  (unchanged - no new SYN packets)

Rule: RULE_2_PERMIT_OTHER_TCP
  Hit counter: 50   ✓ (ACK packets matched PERMIT rule)
```

**Check DUT3 pcap**:
```bash
admin@sonic:~$ python3 << 'EOF'
from scapy.all import rdpcap

packets = rdpcap("/tmp/l3_08_rx.pcap")
print(f"Total packets: {len(packets)}")
for pkt in packets[:5]:
    if pkt.haslayer("TCP"):
        tcp = pkt["TCP"]
        print(f"TCP flags: {tcp.flags} (SYN={tcp.flags & 0x02}, ACK={tcp.flags & 0x10})")
EOF

Total packets: 50
TCP flags: 0x10 (SYN=0, ACK=16)
```

---

## Cleanup

```bash
# DUT1
admin@sonic:~$ config acl remove table L3_ACL_TABLE_L308

# DUT2 and DUT3
admin@sonic:~$ rm -f /tmp/l3_08_*.py /tmp/l3_08_rx.pcap
```

---

## Key Concepts

### TCP Flag Matching in ACLs

**Why it matters**:
- **SYN filtering**: Prevents new connection initiation (stateless DoS protection)
- **FIN filtering**: Prevents graceful connection termination
- **RST filtering**: Prevents connection resets
- **ACK filtering**: Advanced stateless firewall rules

**Example Use Cases**:
- Block connection initiation from untrusted networks (deny SYN)
- Allow only established connections (allow only ACK, PSH, FIN)
- Prevent connection resets (deny RST)
- Port scanning detection (many SYN to different ports)

### Scapy TCP Flag Construction

```python
# SYN only
TCP(flags='S')  # flags=0x02

# ACK only
TCP(flags='A')  # flags=0x10

# SYN-ACK (during 3-way handshake)
TCP(flags='SA')  # flags=0x12

# Multiple flags
TCP(flags='FA')  # FIN-ACK (flags=0x11)
```

---

## Test Comparison: Flag Types

| Test | Flag | Purpose | Expected |
|------|------|---------|----------|
| L3-08 | **SYN** | Connection initiation | RX=0 (DENIED) |
| L3-09 | **ACK** | Connection acknowledgment | RX=0 (DENIED) |
| L3-X | RST | Connection reset | Custom |
| L3-X | FIN | Connection termination | Custom |

---

## Troubleshooting

### Issue: DUT Doesn't Support TCP Flags

```bash
Error: TCP_FLAGS not supported in ACL rules
```

**Solution**: Check SONiC version
```bash
show version | grep "SONiC Software Version"
# TCP flag matching requires SONiC 202205+
```

### Issue: Hit Counter Shows 0

```bash
RULE_1_DENY_TCP_SYN Hit counter: 0
```

**Debugging**:
1. Verify TCP flag in Scapy packet: `TCP(flags='S')`
2. Check ACL rule matches TCP protocol: `--PROTO TCP`
3. Verify rule is applied to correct port: `show acl bindings`

### Issue: Packets Still Reaching DUT3

```bash
Expected RX: 0
Actual RX: 50+ packets
```

**Solution**:
- Verify TCP flag value in Scapy: `pkt['TCP'].flags & 0x02 == 0x02`  # SYN
- Check ACL rule ordering (first-match)
- Confirm no other permits before deny rule

---

## Document Information

**Version**: 1.0
**Created**: 2026-03-11
**Test Case**: L3-08 (TCP SYN Flag Matching)
**Status**: Ready for Execution
**Requires**: Advanced Scapy API with TCP flag support

---

**Next Test**: L3-09 (TCP ACK Flag Matching)
