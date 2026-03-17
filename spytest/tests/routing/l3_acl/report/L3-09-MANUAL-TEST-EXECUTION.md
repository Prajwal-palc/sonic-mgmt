# L3-09: TCP ACK Flag Matching - Manual Test Execution Guide

**Status**: Ready for Execution (Advanced Scapy API)
**Test Case**: L3-09
**Scenario**: Deny TCP ACK packets (established connections)
**ACL Action**: DENY TCP packets with ACK flag set
**Expected RX**: 0 packets (all ACK packets blocked)

---

## Test Overview

This test validates **TCP ACK flag matching** in ACL rules. The ACL rule denies TCP packets with the **ACK flag** set, which blocks established connections and data transfer.

**Traffic Flow**:
```
DUT2 (Scapy) → TX TCP packets with ACK flag set
               ↓
        DUT1:Ethernet0 [ACL INGRESS]
        ├─ Rule: DENY TCP flags:ACK
        └─ Action: DROP packets with ACK flag
               ↓
           All ACK packets dropped - RX=0 on DUT3
```

**Key Difference from L3-08**:
- **L3-08**: Denies TCP **SYN** (blocks connection initiation)
- **L3-09**: Denies TCP **ACK** (blocks established connections and data)

---

## Quick Setup

### SSH to All DUTs
```bash
# DUT1
ssh admin@192.168.100.125  # root@123

# DUT2
ssh admin@192.168.100.248  # root@123

# DUT3
ssh admin@192.168.100.134  # root@123
```

---

## Step-by-Step Execution

### Step 1: Create ACL on DUT1

```bash
admin@sonic:~$ config acl add table L3_ACL_TABLE_L309 L3 -D INGRESS -p Ethernet0

admin@sonic:~$ config acl add rule L3_ACL_TABLE_L309 RULE_1_DENY_TCP_ACK \
  --PACKET_ACTION DROP \
  --PROTO TCP \
  --TCP_FLAGS ACK

admin@sonic:~$ config acl add rule L3_ACL_TABLE_L309 RULE_2_PERMIT_OTHER_TCP \
  --PACKET_ACTION FORWARD \
  --PROTO TCP

# Verify
admin@sonic:~$ show acl rule L3_ACL_TABLE_L309
Rule: RULE_1_DENY_TCP_ACK
  Packet action: DROP
  PROTO: TCP
  TCP_FLAGS: ACK
  Hit counter: 0

Rule: RULE_2_PERMIT_OTHER_TCP
  Packet action: FORWARD
  PROTO: TCP
  Hit counter: 0
```

---

### Step 2: Start Tcpdump on DUT3

```bash
admin@sonic:~$ sudo tcpdump -i Ethernet0 -w /tmp/l3_09_rx.pcap "tcp port 12345" &
[1] 12345
tcpdump: listening on Ethernet0, link-type EN10MB (Ethernet), snapshot length 65535 bytes
```

---

### Step 3: Generate TCP ACK Packets on DUT2

```bash
admin@sonic:~$ cat > /tmp/l3_09_tcp_ack.py << 'EOF'
#!/usr/bin/env python3

from scapy.all import IP, TCP, Ether, send, get_if_hwaddr
from time import sleep

src_ip = "10.0.0.1"
dst_ip = "20.0.0.2"
src_port = 12345
dst_port = 80
num_packets = 100
interface = "Ethernet0"
pps = 10

src_mac = get_if_hwaddr(interface)
dst_mac = "22:d5:dc:51:9e:f3"  # DUT1:Ethernet0

print(f"[*] Sending {num_packets} TCP ACK packets")
print(f"[*] These represent established connection data transfer")
print(f"[*] ACL rule DENIES TCP ACK packets")

ack_num = 3000
for i in range(num_packets):
    packet = Ether(dst=dst_mac, src=src_mac) / \
             IP(src=src_ip, dst=dst_ip) / \
             TCP(sport=src_port, dport=dst_port,
                 flags='A',      # ACK flag
                 seq=2000,
                 ack=ack_num)

    send(packet, iface=interface, verbose=False)
    ack_num += 1

    if (i + 1) % pps == 0:
        sleep(1)

    if (i + 1) % 25 == 0:
        print(f"[+] Sent {i+1}/{num_packets} ACK packets")

print(f"[✓] Sent {num_packets} TCP ACK packets")
EOF

chmod +x /tmp/l3_09_tcp_ack.py
python3 /tmp/l3_09_tcp_ack.py
```

---

### Step 4: Check ACL Hit Counter on DUT1

```bash
admin@sonic:~$ show acl rule L3_ACL_TABLE_L309
Rule: RULE_1_DENY_TCP_ACK
  Hit counter: 100  ✓

Rule: RULE_2_PERMIT_OTHER_TCP
  Hit counter: 0    ✓
```

---

### Step 5: Stop Tcpdump and Verify Results

```bash
admin@sonic:~$ sleep 2 && sudo pkill -f "tcpdump -i Ethernet0"

# Analyze pcap
admin@sonic:~$ python3 << 'EOF'
from scapy.all import rdpcap

packets = rdpcap("/tmp/l3_09_rx.pcap")
print(f"Packets captured: {len(packets)}")
print(f"Expected: 0 (all ACK packets denied)")
EOF

Packets captured: 0
Expected: 0 (all ACK packets denied)
```

---

### Step 6: Extended Test - Send SYN Packets

To verify that **only ACK** packets are blocked:

```bash
admin@sonic:~$ cat > /tmp/l3_09_tcp_syn.py << 'EOF'
#!/usr/bin/env python3

from scapy.all import IP, TCP, Ether, send, get_if_hwaddr

src_ip = "10.0.0.1"
dst_ip = "20.0.0.2"
src_port = 12345
dst_port = 80
interface = "Ethernet0"

src_mac = get_if_hwaddr(interface)
dst_mac = "22:d5:dc:51:9e:f3"

print("[*] Sending 50 TCP SYN packets (not ACK)")
print("[*] SYN packets should be PERMITTED (rule only denies ACK)")

for i in range(50):
    packet = Ether(dst=dst_mac, src=src_mac) / \
             IP(src=src_ip, dst=dst_ip) / \
             TCP(sport=src_port, dport=dst_port,
                 flags='S')  # SYN only

    send(packet, iface=interface, verbose=False)

print("[✓] Sent 50 TCP SYN packets")
EOF

python3 /tmp/l3_09_tcp_syn.py
```

**Check DUT1 hit counters**:
```bash
admin@sonic:~$ show acl rule L3_ACL_TABLE_L309
Rule: RULE_1_DENY_TCP_ACK
  Hit counter: 100  (unchanged - no new ACK packets)

Rule: RULE_2_PERMIT_OTHER_TCP
  Hit counter: 50   ✓ (SYN packets matched PERMIT rule)
```

**Check DUT3 pcap**:
```bash
admin@sonic:~$ python3 << 'EOF'
from scapy.all import rdpcap

packets = rdpcap("/tmp/l3_09_rx.pcap")
print(f"Total packets now: {len(packets)}")
print(f"Expected: 50 (SYN packets allowed)")

# Verify they are SYN packets
for pkt in packets[:3]:
    if pkt.haslayer("TCP"):
        tcp = pkt["TCP"]
        is_syn = (tcp.flags & 0x02) != 0
        is_ack = (tcp.flags & 0x10) != 0
        print(f"SYN={is_syn}, ACK={is_ack}")
EOF

Total packets now: 50
Expected: 50 (SYN packets allowed)
SYN=True, ACK=False
SYN=True, ACK=False
SYN=True, ACK=False
```

---

## Cleanup

```bash
# DUT1
admin@sonic:~$ config acl remove table L3_ACL_TABLE_L309

# DUT2 & DUT3
admin@sonic:~$ rm -f /tmp/l3_09_*.py /tmp/l3_09_rx.pcap
```

---

## Use Case: Stateless Firewall

**Blocking ACK packets has real-world security applications**:

```
Scenario: Port scanner detection

Traditional approach (port blocked):
Attacker → SYN to port 80 → No response → Port appears closed

With ACK filter on port 80:
Attacker → SYN to port 80 → SYN-ACK sent → Port appears open
But: ACK packets rejected → Connection never established
Result: Can detect which ports have services listening

This is used in some advanced DDoS mitigation strategies
to prevent connection establishment while revealing service presence.
```

---

## Key Comparison: SYN vs ACK Filtering

| Aspect | L3-08 (Deny SYN) | L3-09 (Deny ACK) |
|--------|---|---|
| Blocks | Connection initiation | Connection data transfer |
| Effect | New connections fail | Established connections fail |
| Use Case | Restrict incoming connections | Block specific client behavior |
| Real-world | Inbound firewall | Egress filtering / DDoS |

---

## TCP Flag Combinations Reference

| Flags | Meaning | Phase |
|-------|---------|-------|
| **SYN** | Connection start | 1st handshake |
| **SYN-ACK** | Server responds | 2nd handshake |
| **ACK** | Client confirms | 3rd handshake |
| **ACK-PSH** | Data transfer | After 3-way |
| **FIN** | Close request | Termination |
| **RST** | Connection reset | Abnormal close |

---

## Document Information

**Version**: 1.0
**Created**: 2026-03-11
**Test Case**: L3-09 (TCP ACK Flag Matching)
**Requires**: Advanced Scapy API

---

**Key Insight**: ACL flag matching enables sophisticated stateless firewall rules beyond simple source/destination IP filtering.
