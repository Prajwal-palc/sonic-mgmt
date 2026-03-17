# L3-05: Permit Specific Source (Whitelist) - Manual Test Execution Guide

**Status**: Ready for Execution (SpyTest Framework)
**Test Case**: L3-05
**Scenario**: Permit only traffic from specific source IP (whitelist)
**ACL Action**: PERMIT whitelisted source, DENY all others
**Expected RX**: 100 packets (traffic from whitelisted source permitted)

---

## Test Overview

This test validates that an ACL rule using **PERMIT action** can be used to create a **source IP whitelist** - allowing traffic only from specific sources and denying all others.

**Traffic Flow**:
```
DUT2 (10.0.0.1) → TX packets with src_ip=10.0.0.88 (whitelisted)
                ↓
         DUT1:Ethernet0 [ACL INGRESS]
         ├─ Rule 1: PERMIT src_ip 10.0.0.88/32 (whitelist)
         ├─ Rule 2: DENY src_ip any (implicit deny-all)
         └─ Action: Allow whitelisted source only
                ↓
            All packets from 10.0.0.88 → RX=100 on DUT3
```

**Key Feature**: PERMIT rules enable **positive security** (whitelist) instead of **negative security** (blacklist)

---

## Prerequisites

### Device Connectivity Verification

```bash
# From DUT2
admin@sonic:~$ ping -c 3 10.0.0.254
PING 10.0.0.254 (10.0.0.254) 56(84) bytes of data.
64 bytes from 10.0.0.254: icmp_seq=1 ttl=64 time=1.234 ms
--- 10.0.0.254 statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2ms

# From DUT3
admin@sonic:~$ ping -c 3 20.0.0.254
PING 20.0.0.254 (20.0.0.254) 56(84) bytes of data.
64 bytes from 20.0.0.254: icmp_seq=1 ttl=64 time=1.234 ms
--- 20.0.0.254 statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2ms
```

### Interface Status

```bash
# On DUT1
admin@sonic:~$ show interface status | grep -E "Ethernet0|Ethernet4"
Interface         Lanes    Speed    MTU    FEC           Alias    Vlan    Oper    Admin    Type    Asym PFC
-----------  ------------  -------  -----  -----  --------------  ------  ------  -------  ------  ----------
Ethernet0    0,1,2,3         40G   9100    N/A        fortyGigE0/1  routed      up       up     N/A         N/A
Ethernet4    4,5,6,7         40G   9100    N/A        fortyGigE0/5  routed      up       up     N/A         N/A
```

---

## Step-by-Step Execution

### Step 1: SSH Access to All Three DUTs

**Terminal 1 - DUT1 (ACL Device)**:
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@192.168.100.125
# Password: root@123
```

**Terminal 2 - DUT2 (TX Host)**:
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@192.168.100.248
# Password: root@123
```

**Terminal 3 - DUT3 (RX Host)**:
```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null admin@192.168.100.134
# Password: root@123
```

---

### Step 2: Verify L3 Configuration

**On DUT1**:
```bash
admin@sonic:~$ show ip address | grep Ethernet
Ethernet0  10.0.0.254/24  default
Ethernet4  20.0.0.254/24  default
```

**On DUT2**:
```bash
admin@sonic:~$ show ip address | grep Ethernet
Ethernet0  10.0.0.1/24  default
```

**On DUT3**:
```bash
admin@sonic:~$ show ip address | grep Ethernet
Ethernet0  20.0.0.2/24  default
```

---

### Step 3: Create ACL with Whitelist Rules

On **DUT1**, create an ACL table with PERMIT whitelist rule:

**Rule 1: PERMIT whitelisted source**
```bash
admin@sonic:~$ config acl add table L3_ACL_TABLE_L305 L3 -D INGRESS -p Ethernet0
```

**Add PERMIT rule for whitelisted source IP (10.0.0.88)**:
```bash
admin@sonic:~$ config acl add rule L3_ACL_TABLE_L305 RULE_1_PERMIT_WHITELIST \
  --PACKET_ACTION FORWARD \
  --SRC_IP 10.0.0.88/32 \
  --PROTO UDP
```

**Add implicit DENY-ALL (deny any other source)**:
```bash
admin@sonic:~$ config acl add rule L3_ACL_TABLE_L305 RULE_2_DENY_ALL \
  --PACKET_ACTION DROP \
  --PROTO UDP
```

**Verify ACL configuration**:
```bash
admin@sonic:~$ show acl table L3_ACL_TABLE_L305
Name: L3_ACL_TABLE_L305
Type: L3
Ports: ['Ethernet0']
Stage: INGRESS
Description: N/A

admin@sonic:~$ show acl rule L3_ACL_TABLE_L305
Rule: RULE_1_PERMIT_WHITELIST
  Packet action: FORWARD
  SRC_IP: 10.0.0.88/32
  PROTO: UDP
  Hit counter: 0

Rule: RULE_2_DENY_ALL
  Packet action: DROP
  SRC_IP: any
  PROTO: UDP
  Hit counter: 0
```

---

### Step 4: Start Tcpdump on DUT3

On **DUT3**, start tcpdump to capture RX traffic:

```bash
admin@sonic:~$ sudo tcpdump -i Ethernet0 -w /tmp/l3_05_rx.pcap udp port 54321 &
[1] 12345
tcpdump: listening on Ethernet0, link-type EN10MB (Ethernet), snapshot length 65535 bytes
```

---

### Step 5: Generate Scapy Traffic on DUT2

On **DUT2**, create Scapy script to send packets with **whitelisted source IP** (10.0.0.88):

```bash
admin@sonic:~$ cat > /tmp/l3_05_scapy_traffic.py << 'EOF'
#!/usr/bin/env python3

from scapy.all import IP, UDP, Ether, send, get_if_hwaddr
from time import sleep
import sys

# Configuration
src_ip = "10.0.0.88"          # WHITELISTED source IP
dst_ip = "20.0.0.2"           # RX host (DUT3)
dst_port = 54321
num_packets = 100
interface = "Ethernet0"
pps = 10

# Get MAC addresses
src_mac = get_if_hwaddr(interface)
dst_mac = "22:d5:dc:51:9e:f3"  # DUT1:Ethernet0 MAC

# Create packet template
packet = Ether(dst=dst_mac, src=src_mac) / \
         IP(src=src_ip, dst=dst_ip) / \
         UDP(dport=dst_port, sport=12345) / \
         b"L3_05_PERMIT_WHITELIST_TEST"

print(f"[*] Sending {num_packets} packets from {src_ip} (WHITELISTED) to {dst_ip}:{dst_port}")
print(f"[*] Source {src_ip} is in whitelist → packets should be PERMITTED")
print(f"[*] Rate: {pps} packets/second")

# Send packets
sent_count = 0
for i in range(num_packets):
    send(packet, iface=interface, verbose=False)
    sent_count += 1

    if (i + 1) % pps == 0:
        sleep(1)

    if (i + 1) % 25 == 0:
        print(f"[+] Sent {i+1}/{num_packets} packets")

print(f"[✓] Traffic generation completed: {sent_count} packets sent")
EOF

chmod +x /tmp/l3_05_scapy_traffic.py
```

**Execute Scapy script**:
```bash
admin@sonic:~$ python3 /tmp/l3_05_scapy_traffic.py
[*] Sending 100 packets from 10.0.0.88 (WHITELISTED) to 20.0.0.2:54321
[*] Source 10.0.0.88 is in whitelist → packets should be PERMITTED
[*] Rate: 10 packets/second
[+] Sent 25/100 packets
[+] Sent 50/100 packets
[+] Sent 75/100 packets
[+] Sent 100/100 packets
[✓] Traffic generation completed: 100 packets sent
```

---

### Step 6: Verify ACL Hit Counters

On **DUT1**, check which ACL rules matched:

```bash
admin@sonic:~$ show acl rule L3_ACL_TABLE_L305
Rule: RULE_1_PERMIT_WHITELIST
  Packet action: FORWARD
  SRC_IP: 10.0.0.88/32
  PROTO: UDP
  Hit counter: 100  ✓ (packets matched whitelist rule)

Rule: RULE_2_DENY_ALL
  Packet action: DROP
  SRC_IP: any
  PROTO: UDP
  Hit counter: 0   ✓ (no packets matched deny-all)
```

**Expected Results**:
- `RULE_1_PERMIT_WHITELIST`: Hit counter = **100** (all packets matched and PERMITTED)
- `RULE_2_DENY_ALL`: Hit counter = **0** (no packets reached this rule)

---

### Step 7: Stop Tcpdump on DUT3

On **DUT3**, stop tcpdump:

```bash
admin@sonic:~$ sleep 2
admin@sonic:~$ sudo pkill -f "tcpdump -i Ethernet0"
[1]+  Terminated              sudo tcpdump -i Ethernet0 -w /tmp/l3_05_rx.pcap udp port 54321
```

---

### Step 8: Analyze Pcap File

On **DUT3**, verify all packets were received:

```bash
# Check pcap file size (should be larger than L3-03/L3-04)
admin@sonic:~$ ls -lh /tmp/l3_05_rx.pcap
-rw-r--r-- 1 admin admin 8192 Mar 11 14:35 /tmp/l3_05_rx.pcap

# Count packets using Scapy
admin@sonic:~$ python3 << 'PYTHON_EOF'
from scapy.all import rdpcap

pcap_file = "/tmp/l3_05_rx.pcap"
packets = rdpcap(pcap_file)
print(f"Packets captured (RX): {len(packets)}")
print(f"Expected RX: 100")
print(f"Loss rate: {100 * (100 - len(packets)) / 100}%")

if len(packets) > 0:
    pkt = packets[0]
    print(f"\nFirst packet:")
    print(f"  Source IP: {pkt[0][1].src}")
    print(f"  Dest IP: {pkt[0][1].dst}")
    print(f"  Dest Port: {pkt[0][2].dport}")
PYTHON_EOF

Packets captured (RX): 100
Expected RX: 100
Loss rate: 0.0%

First packet:
  Source IP: 10.0.0.88
  Dest IP: 20.0.0.2
  Dest Port: 54321
```

**Expected**: Pcap should contain **100 packets** (all permitted through whitelist rule)

---

### Step 9: Verify Test Results

**Test Validation Checklist**:

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| TX Packets | 100 | ✓ | ✓ PASS |
| PERMIT Rule Hit | 100 | ✓ | ✓ PASS |
| DENY Rule Hit | 0 | ✓ | ✓ PASS |
| RX Packets (Pcap) | 100 | ✓ | ✓ PASS |
| Loss Rate | 0% | ✓ | ✓ PASS |
| Result | Whitelist working | ✓ | ✓ **PASS** |

---

## Extended Test: Non-Whitelisted Source

To further validate the whitelist, test traffic from a **non-whitelisted source**:

### Alternative Step 5b: Send from Non-Whitelisted Source

```bash
admin@sonic:~$ cat > /tmp/l3_05_non_whitelist.py << 'EOF'
#!/usr/bin/env python3

from scapy.all import IP, UDP, Ether, send, get_if_hwaddr
from time import sleep

# Configuration
src_ip = "10.0.0.99"          # NOT WHITELISTED
dst_ip = "20.0.0.2"
dst_port = 54321
num_packets = 50
interface = "Ethernet0"

src_mac = get_if_hwaddr(interface)
dst_mac = "22:d5:dc:51:9e:f3"

packet = Ether(dst=dst_mac, src=src_mac) / \
         IP(src=src_ip, dst=dst_ip) / \
         UDP(dport=dst_port, sport=12345) / \
         b"NON_WHITELISTED"

print(f"[*] Sending {num_packets} packets from {src_ip} (NOT WHITELISTED)")
print(f"[*] These should be DENIED by RULE_2_DENY_ALL")

for i in range(num_packets):
    send(packet, iface=interface, verbose=False)

print(f"[✓] Sent {num_packets} non-whitelisted packets")
EOF

chmod +x /tmp/l3_05_non_whitelist.py
python3 /tmp/l3_05_non_whitelist.py
```

### Verify Non-Whitelisted Packets Denied

```bash
# After running non-whitelisted traffic
admin@sonic:~$ show acl rule L3_ACL_TABLE_L305
Rule: RULE_1_PERMIT_WHITELIST
  Hit counter: 100  ✓ (unchanged from whitelisted traffic)

Rule: RULE_2_DENY_ALL
  Hit counter: 50   ✓ (increased by 50 from non-whitelisted packets)
```

**On DUT3**, check that non-whitelisted packets were NOT captured:
```bash
# Pcap should still have 100 packets (only whitelisted)
# Non-whitelisted packets were DROPPED at DUT1
```

---

## Cleanup

### Remove ACL

On **DUT1**:
```bash
admin@sonic:~$ config acl remove table L3_ACL_TABLE_L305
Removed ACL table L3_ACL_TABLE_L305
```

### Remove Pcap and Scripts

On **DUT2** and **DUT3**:
```bash
admin@sonic:~$ rm -f /tmp/l3_05_rx.pcap /tmp/l3_05_*.py
```

---

## Key Differences from Previous Tests

| Aspect | DENY Tests (L3-01 to L3-04) | PERMIT/Whitelist (L3-05) |
|--------|---|---|
| Action | DENY (drop packets) | PERMIT (forward packets) |
| Security Model | Blacklist | **Whitelist** |
| Rules | Single DENY rule | PERMIT + implicit DENY-ALL |
| Expected RX | 0 packets | 100 packets |
| Use Case | Block specific traffic | Allow only trusted sources |

---

## Important Notes

### Why ACL Rules Require Proper Order

In **L3-05**, rule order is critical:

```
Rule 1: PERMIT 10.0.0.88/32   ← Check specific whitelisted source first
Rule 2: DENY all others        ← Implicit deny-all as fallback
```

**If order reversed** (deny-all first), it would:
1. DENY all packets immediately
2. Never reach PERMIT rule
3. Result in 0 packets received (whitelist would be ineffective)

### ACL Rule Evaluation

SONiC ACLs use **first-match** evaluation:
- Packet is evaluated against rules in order
- First matching rule is applied
- Subsequent rules are not evaluated
- If no rules match, implicit deny applies

---

## Troubleshooting

### Issue: All Packets Denied Despite Whitelist

```bash
RX Packets: 0 (expected 100)
RULE_2_DENY_ALL Hit counter: 100
```

**Cause**: Rule order is reversed (deny-all evaluated before permit)

**Solution**:
```bash
# Check rule order
show acl rule L3_ACL_TABLE_L305

# Recreate table with correct order
config acl remove table L3_ACL_TABLE_L305
config acl add table L3_ACL_TABLE_L305 L3 -D INGRESS -p Ethernet0

# Add PERMIT rule FIRST
config acl add rule L3_ACL_TABLE_L305 RULE_1_PERMIT_WHITELIST \
  --PACKET_ACTION FORWARD \
  --SRC_IP 10.0.0.88/32 \
  --PROTO UDP

# Then add DENY-ALL
config acl add rule L3_ACL_TABLE_L305 RULE_2_DENY_ALL \
  --PACKET_ACTION DROP \
  --PROTO UDP
```

### Issue: Source IP in Traffic Doesn't Match Rule

```bash
PERMIT Rule Hit counter: 0
DENY Rule Hit counter: 100
```

**Solution**:
- Verify source IP in Scapy script matches whitelist rule (10.0.0.88)
- Check that script IP is not being modified by intermediate systems
- Test with baseline (no ACL) to verify traffic is actually flowing

---

## Extended Testing

### Test Multiple Whitelisted Sources

To permit multiple sources, add multiple PERMIT rules:

```bash
# Add another whitelisted source
admin@sonic:~$ config acl add rule L3_ACL_TABLE_L305 RULE_1b_PERMIT_WHITELIST_2 \
  --PACKET_ACTION FORWARD \
  --SRC_IP 10.0.0.77/32 \
  --PROTO UDP
```

Now traffic from both 10.0.0.88 and 10.0.0.77 will be permitted.

### Test Whitelist with Subnets

For subnet-level whitelists:

```bash
# Permit entire subnet (not just single host)
admin@sonic:~$ config acl add rule L3_ACL_TABLE_L305 RULE_1_PERMIT_SUBNET \
  --PACKET_ACTION FORWARD \
  --SRC_IP 10.0.0.0/25 \
  --PROTO UDP
```

This permits all sources in 10.0.0.0-10.0.0.127 subnet.

---

## Document Information

**Version**: 1.0
**Created**: 2026-03-11
**Test Case**: L3-05 (Permit Specific Source / Whitelist)
**Status**: Ready for Execution
**Framework**: SpyTest 3-SONiC-DUT with Scapy & Tcpdump

---

**Key Concept**: PERMIT rules enable **positive security** (whitelist) in addition to DENY rules (blacklist)
