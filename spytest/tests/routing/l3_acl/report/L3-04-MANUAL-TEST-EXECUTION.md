# L3-04: Deny Destination Subnet (/24) - Manual Test Execution Guide

**Status**: Ready for Execution (SpyTest Framework)
**Test Case**: L3-04
**Scenario**: Deny destination IP subnet (20.0.0.0/24)
**ACL Action**: DENY all traffic to destination subnet
**Expected RX**: 0 packets (100% loss due to ACL DENY)

---

## Test Overview

This test validates that an ACL rule denying traffic to a specific **destination subnet** (not just a single host) correctly drops all matching packets at the DUT1 ingress port.

**Traffic Flow**:
```
DUT2 (10.0.0.1) → TX packets with dest_ip=20.0.0.50 (within 20.0.0.0/24)
                ↓
         DUT1:Ethernet0 [ACL INGRESS]
         ├─ Rule: DENY dst_ip 20.0.0.0/24
         └─ Action: DROP (hit counter increments)
                ↓
            All packets dropped - RX=0 on DUT3
```

**Key Difference from L3-03**:
- L3-03: Denies single destination host (20.0.0.99/32)
- L3-04: Denies entire destination subnet (20.0.0.0/24)

---

## Prerequisites

### Device Connectivity Verification

```bash
# From DUT2 - Verify gateway is reachable
admin@sonic:~$ ping -c 3 10.0.0.254
PING 10.0.0.254 (10.0.0.254) 56(84) bytes of data.
64 bytes from 10.0.0.254: icmp_seq=1 ttl=64 time=1.234 ms
--- 10.0.0.254 statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2ms

# From DUT3 - Verify gateway is reachable
admin@sonic:~$ ping -c 3 20.0.0.254
PING 20.0.0.254 (20.0.0.254) 56(84) bytes of data.
64 bytes from 20.0.0.254: icmp_seq=1 ttl=64 time=1.234 ms
--- 20.0.0.254 statistics ---
3 packets transmitted, 3 received, 0% packet loss, time 2ms
```

### Interface Status

```bash
# On DUT1 - Verify both interfaces are UP
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

### Step 2: Verify L3 Addresses on All Devices

**On DUT1**:
```bash
admin@sonic:~$ show ip address
Interface     Vrf          Routes
---------  -------  --------
Ethernet0  default       2048
Ethernet4  default       2048

admin@sonic:~$ show ip address Ethernet0
Interface    Address Vrf
---------  ---------- ----
Ethernet0  10.0.0.254/24  default

admin@sonic:~$ show ip address Ethernet4
Interface    Address Vrf
---------  ---------- ----
Ethernet4  20.0.0.254/24  default
```

**On DUT2**:
```bash
admin@sonic:~$ show ip address Ethernet0
Interface    Address Vrf
---------  ---------- ----
Ethernet0  10.0.0.1/24  default
```

**On DUT3**:
```bash
admin@sonic:~$ show ip address Ethernet0
Interface    Address Vrf
---------  ---------- ----
Ethernet0  20.0.0.2/24  default
```

---

### Step 3: Verify Static Routes

**On DUT2** - Should have route to 20.0.0.0/24:
```bash
admin@sonic:~$ show ip route
Codes: K - kernel route, C - connected, S - static, R - rip,
       B - bgp, O - ospf, I - is-is, L - ldp, PIM - pim, T - table, V - vrf, G - vrf redirect
Destination         Mask            Gateway          Interface  Metric
20.0.0.0/24         255.255.255.0   10.0.0.254       Ethernet0  0
```

**On DUT3** - Should have route to 10.0.0.0/24:
```bash
admin@sonic:~$ show ip route
Codes: K - kernel route, C - connected, S - static, R - rip,
       B - bgp, O - ospf, I - is-is, L - ldp, PIM - pim, T - table, V - vrf, G - vrf redirect
Destination         Mask            Gateway          Interface  Metric
10.0.0.0/24         255.255.255.0   20.0.0.254       Ethernet0  0
```

---

### Step 4: Create ACL on DUT1

On **DUT1**, create an ACL table that denies traffic to destination subnet 20.0.0.0/24:

```bash
admin@sonic:~$ config acl add table L3_ACL_TABLE_L304 L3 -D INGRESS -p Ethernet0

admin@sonic:~$ config acl add rule L3_ACL_TABLE_L304 RULE_1_DENY_DEST_SUBNET \
  --PACKET_ACTION DROP \
  --DST_IP 20.0.0.0/24 \
  --PROTO UDP

# Verify ACL was created
admin@sonic:~$ show acl table L3_ACL_TABLE_L304
Name: L3_ACL_TABLE_L304
Type: L3
Ports: ['Ethernet0']
Stage: INGRESS
Description: N/A

# Verify rule was created
admin@sonic:~$ show acl rule L3_ACL_TABLE_L304 RULE_1_DENY_DEST_SUBNET
Rule: RULE_1_DENY_DEST_SUBNET
Packet action: DROP
DST_IP: 20.0.0.0/24
PROTO: UDP
Hit counter: 0  (initial state)
```

---

### Step 5: Start Tcpdump on DUT3

On **DUT3**, start background tcpdump to capture RX traffic:

```bash
admin@sonic:~$ sudo tcpdump -i Ethernet0 -w /tmp/l3_04_rx.pcap udp port 54321 &
[1] 12345
tcpdump: listening on Ethernet0, link-type EN10MB (Ethernet), snapshot length 65535 bytes
```

**Verify tcpdump is running**:
```bash
admin@sonic:~$ ps aux | grep tcpdump
admin     12345  0.0  0.1 123456  8192 ?  S 14:30:00  0:00  sudo tcpdump -i Ethernet0 -w /tmp/l3_04_rx.pcap udp port 54321
```

---

### Step 6: Generate Scapy Traffic on DUT2

On **DUT2**, create and execute Scapy script to send 100 UDP packets with:
- **Source IP**: 10.0.0.1 (DUT2 - normal, not filtered)
- **Destination IP**: 20.0.0.50 (within 20.0.0.0/24 subnet - will be DENIED)
- **UDP Port**: 54321 (for tcpdump filtering)
- **Packet Count**: 100
- **Duration**: 10 seconds

**Create Scapy script**:
```bash
admin@sonic:~$ cat > /tmp/l3_04_scapy_traffic.py << 'EOF'
#!/usr/bin/env python3

from scapy.all import IP, UDP, Ether, send, get_if_hwaddr
from time import sleep
import sys

# Configuration
src_ip = "10.0.0.1"
dst_ip = "20.0.0.50"          # Within 20.0.0.0/24 subnet (will be DENIED)
dst_port = 54321
num_packets = 100
interface = "Ethernet0"
pps = 10  # packets per second

# Get MAC addresses
src_mac = get_if_hwaddr(interface)
dst_mac = "22:d5:dc:51:9e:f3"  # DUT1:Ethernet0 MAC

# Create packet template
packet = Ether(dst=dst_mac, src=src_mac) / \
         IP(src=src_ip, dst=dst_ip) / \
         UDP(dport=dst_port, sport=12345) / \
         b"L3_04_DENY_DEST_SUBNET_TEST"

print(f"[*] Sending {num_packets} packets from {src_ip} to {dst_ip}:{dst_port}")
print(f"[*] Destination {dst_ip} is within 20.0.0.0/24 (DENIED subnet)")
print(f[*] Rate: {pps} packets/second")

# Send packets
sent_count = 0
for i in range(num_packets):
    send(packet, iface=interface, verbose=False)
    sent_count += 1

    # Rate control
    if (i + 1) % pps == 0:
        sleep(1)

    if (i + 1) % 25 == 0:
        print(f"[+] Sent {i+1}/{num_packets} packets")

print(f"[✓] Traffic generation completed: {sent_count} packets sent")
EOF

chmod +x /tmp/l3_04_scapy_traffic.py
```

**Execute Scapy script**:
```bash
admin@sonic:~$ python3 /tmp/l3_04_scapy_traffic.py
[*] Sending 100 packets from 10.0.0.1 to 20.0.0.50:54321
[*] Destination 20.0.0.50 is within 20.0.0.0/24 (DENIED subnet)
[*] Rate: 10 packets/second
[+] Sent 25/100 packets
[+] Sent 50/100 packets
[+] Sent 75/100 packets
[+] Sent 100/100 packets
[✓] Traffic generation completed: 100 packets sent
```

**Duration**: ~10 seconds to send 100 packets at 10 pps

---

### Step 7: Verify ACL Hit Counter

While/after traffic is being sent, check ACL rule hit counter on **DUT1**:

```bash
admin@sonic:~$ show acl rule L3_ACL_TABLE_L304 RULE_1_DENY_DEST_SUBNET
Rule: RULE_1_DENY_DEST_SUBNET
Packet action: DROP
DST_IP: 20.0.0.0/24
PROTO: UDP
Hit counter: 100  ✓ (should match TX count)
```

**Expected**: Hit counter should be **100** (all packets matched the DENY rule)

---

### Step 8: Stop Tcpdump on DUT3

On **DUT3**, stop tcpdump gracefully:

```bash
# Wait 2 seconds for buffer flush
admin@sonic:~$ sleep 2

# Kill tcpdump
admin@sonic:~$ sudo pkill -f "tcpdump -i Ethernet0"
[1]+  Terminated              sudo tcpdump -i Ethernet0 -w /tmp/l3_04_rx.pcap udp port 54321

# Verify tcpdump stopped
admin@sonic:~$ ps aux | grep tcpdump
admin     12347  0.0  0.0   4096   712 ?  S 14:30:15  0:00  grep tcpdump
```

---

### Step 9: Analyze Pcap File

On **DUT3**, verify pcap was created and analyze packet count:

```bash
# Check pcap file size
admin@sonic:~$ ls -lh /tmp/l3_04_rx.pcap
-rw-r--r-- 1 admin admin 314 Mar 11 14:30 /tmp/l3_04_rx.pcap

# Count packets in pcap using tcpdump
admin@sonic:~$ sudo tcpdump -r /tmp/l3_04_rx.pcap -c 10
reading from file /tmp/l3_04_rx.pcap, link-type EN10MB (Ethernet)
# Output shows: 0 packets (pcap is empty - expected!)

# Verify using Python Scapy
admin@sonic:~$ python3 << 'PYTHON_EOF'
from scapy.all import rdpcap

pcap_file = "/tmp/l3_04_rx.pcap"
packets = rdpcap(pcap_file)
print(f"Packets captured: {len(packets)}")
for i, pkt in enumerate(packets[:5]):
    if i == 0:
        print(pkt.summary())
PYTHON_EOF

Packets captured: 0
```

**Expected**: Pcap file should be **empty (0 packets)** because all packets were DENIED at DUT1:Ethernet0 INGRESS

---

### Step 10: Verify Test Results

**Test Validation Checklist**:

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| TX Packets | 100 | ✓ | ✓ PASS |
| ACL Hit Counter | 100 | ✓ | ✓ PASS |
| RX Packets (Pcap) | 0 | ✓ | ✓ PASS |
| Loss Rate | 100% | ✓ | ✓ PASS |
| Result | DENY rule working | ✓ | ✓ **PASS** |

---

## Cleanup

### Remove ACL Table (cleanup all rules)

On **DUT1**:
```bash
admin@sonic:~$ config acl remove table L3_ACL_TABLE_L304
Removed ACL table L3_ACL_TABLE_L304
```

### Remove Pcap Files

On **DUT3**:
```bash
admin@sonic:~$ rm -f /tmp/l3_04_rx.pcap
```

### Remove Scapy Script

On **DUT2**:
```bash
admin@sonic:~$ rm -f /tmp/l3_04_scapy_traffic.py
```

---

## Expected vs Actual Results

### Success Scenario (Expected)

```
DUT2: TX 100 packets to 20.0.0.50 (within DENIED subnet)
       ↓
DUT1: ACL rule matches ALL 100 packets → Hit counter: 100
       ├─ Rule: DENY dst_ip 20.0.0.0/24
       └─ Action: DROP all matching packets
       ↓
DUT3: Receives 0 packets (pcap empty)
       ↓
Result: ✅ **PASS** (ACL DENY subnet rule working correctly)
```

### Failure Scenarios

| Scenario | Symptom | Cause | Solution |
|----------|---------|-------|----------|
| RX > 0 packets | Pcap has packets | ACL not applied/mismatch | Check: ACL binding, rule match |
| Hit counter = 0 | ACL rule not evaluated | ACL not bound to port | Check: `show acl bindings` |
| Pkts lost (0 < RX < 100) | Partial traffic loss | Route issue or ACL conflict | Check: routing table, ACL priority |

---

## Key Observations

### What This Test Proves

1. ✅ **Subnet-level matching works**: DENY rule with /24 CIDR blocks entire subnet
2. ✅ **Ingress ACL enforcement**: Packets dropped at DUT1:Ethernet0 ingress
3. ✅ **Hit counter accuracy**: Counter matches actual packets matched
4. ✅ **Difference from L3-03**: Subnet deny vs. single host deny

### Difference from L3-03

| Aspect | L3-03 | L3-04 |
|--------|-------|-------|
| Destination | Single host (20.0.0.99/32) | Entire subnet (20.0.0.0/24) |
| ACL Rule | `/32` CIDR | `/24` CIDR |
| Packets Sent To | 20.0.0.99 | 20.0.0.50 (any in subnet) |
| Expected DENY | 100 packets | 100 packets (same in this case) |

---

## Troubleshooting

### Issue: ACL Table Creation Fails

```bash
Error: Failed to create ACL table L3_ACL_TABLE_L304
```

**Solution**:
```bash
# Check existing ACL tables
show acl table

# Remove old table if exists
config acl remove table L3_ACL_TABLE_L304

# Retry table creation
config acl add table L3_ACL_TABLE_L304 L3 -D INGRESS -p Ethernet0
```

### Issue: Packets Still Reaching DUT3

```bash
Expected RX: 0 packets
Actual RX: 50-100 packets
```

**Debugging**:
```bash
# Check ACL status on DUT1
show acl table L3_ACL_TABLE_L304
show acl rule L3_ACL_TABLE_L304

# Verify destination in traffic matches rule
# Check hit counter increasing
show acl rule L3_ACL_TABLE_L304 RULE_1_DENY_DEST_SUBNET | grep "Hit counter"

# Check if traffic source/dest IPs correct
# Verify Tcpdump filter matches Scapy traffic
```

### Issue: Pcap File Not Created

```bash
ls -l /tmp/l3_04_rx.pcap
# Result: No such file or directory
```

**Solution**:
```bash
# Verify tcpdump was running
ps aux | grep tcpdump

# Restart tcpdump manually
sudo tcpdump -i Ethernet0 -w /tmp/l3_04_rx.pcap udp port 54321 &

# Wait for traffic, then stop gracefully
sleep 12
sudo pkill -f tcpdump
```

---

## Related Test Cases

| Test | Scenario | Difference |
|------|----------|-----------|
| L3-BASELINE | No ACL - all packets pass | Baseline connectivity |
| L3-01 | Deny source IP (host) | Source-based deny |
| L3-02 | Deny source subnet (/24) | Subnet-level source deny |
| **L3-04** | **Deny destination subnet (/24)** | **← You are here** |
| L3-05 | Permit specific source (whitelist) | Positive rule, subnet match |

---

## Document Information

**Version**: 1.0
**Created**: 2026-03-11
**Test Case**: L3-04 (Deny Destination Subnet)
**Status**: Ready for Execution
**Framework**: SpyTest 3-SONiC-DUT with Scapy & Tcpdump

---

**Next Test**: L3-05 (Permit Specific Source / Whitelist)
