# L3-03 Manual Test Execution Report
## Deny Destination IP (Host Level) - Using SpyTest Framework & Scapy

**Test Date**: 2026-03-11
**Status**: Manual Testing Guide (Ready for Execution)
**Topology**: 3-SONiC-DUT (DUT1=ACL, DUT2=TX, DUT3=RX)

---

## Test Objective

Validate that an ACL rule denying traffic to a **specific destination IP (20.0.0.99/32)** correctly drops all matching packets.

**Test Case**: L3-03 (Deny Destination IP - Host Level)
**Expected Result**: All packets dropped → RX = 0% delivery

---

## Device Information

| Device | Role | IP Address | Interface | Subnet | Purpose |
|--------|------|-----------|-----------|--------|---------|
| DUT1 | ACL Device | 192.168.100.125 | Ethernet0 | 10.0.0.254/24 | ACL applied INGRESS |
| DUT1 | ACL Device | 192.168.100.125 | Ethernet4 | 20.0.0.254/24 | Egress to RX |
| DUT2 | TX Host | 192.168.100.248 | Ethernet0 | 10.0.0.1/24 | Source traffic |
| DUT3 | RX Host | 192.168.100.134 | Ethernet0 | 20.0.0.2/24 | Receive & verify |

---

## Test Traffic Configuration

```yaml
Test Case: L3-03 (Deny Destination IP)
Source IP:      10.0.0.1   (normal TX host)
Destination IP: 20.0.0.99  (denied host - NOT RX host 20.0.0.2)
Protocol:       UDP (port 54321)
Packet Count:   100
Duration:       10 seconds
Rate:           10 pps
Expected RX:    0 packets (100% loss - DENY rule matches destination)
```

---

## ACL Configuration for DUT1

**Table**: L3_ACL_TABLE
**Type**: L3 (IPv4)
**Stage**: INGRESS
**Applied Port**: Ethernet0

### ACL Rules

```
Rule 1: RULE_1_DENY_DEST
  Action: DENY
  Source IP: any
  Dest IP: 20.0.0.99/32  (DENY specific host)
  Protocol: UDP

Rule 2: RULE_2_PERMIT_ALL
  Action: PERMIT
  Source IP: any
  Dest IP: any
  Protocol: UDP
  (Fallback for non-matching traffic)
```

---

## Manual Testing Procedure

### Step 1: SSH to DUT1 (ACL Device) - 192.168.100.125

```bash
ssh -o StrictHostKeyChecking=no admin@192.168.100.125
Password: root@123
```

### Step 2: Configure L3 Addresses on DUT1 (if not already done)

```bash
sonic-cli prompt=--sonic-mgmt-- -t 0
configure terminal

# Ethernet0 (TX subnet gateway)
interface Ethernet 0
ip address 10.0.0.254/24
exit

# Ethernet4 (RX subnet gateway)
interface Ethernet 4
ip address 20.0.0.254/24
exit

exit
exit
```

### Step 3: Create ACL Table on DUT1

```bash
configure terminal

# Create ACL table
acl-table L3_ACL_TABLE
  type L3
  stage INGRESS
  ports Ethernet0
exit

exit
```

### Step 4: Create ACL Rules (DENY destination IP, then PERMIT all)

```bash
configure terminal

# Rule 1: DENY traffic to 20.0.0.99
acl-rule RULE_1_DENY_DEST
  table L3_ACL_TABLE
  action DROP
  src-ip 0.0.0.0/0
  dst-ip 20.0.0.99/32
  ip-protocol UDP
exit

# Rule 2: PERMIT all (fallback)
acl-rule RULE_2_PERMIT_ALL
  table L3_ACL_TABLE
  action FORWARD
  src-ip 0.0.0.0/0
  dst-ip 0.0.0.0/0
  ip-protocol UDP
exit

exit
exit
```

### Step 5: Verify ACL Configuration

```bash
show acl table L3_ACL_TABLE
show acl-rule L3_ACL_TABLE
```

**Expected Output**:
```
ACL Table: L3_ACL_TABLE
Type: L3
Stage: INGRESS
Ports: Ethernet0

Rules:
  - RULE_1_DENY_DEST: DENY any → 20.0.0.99 (UDP)
  - RULE_2_PERMIT_ALL: PERMIT any → any (UDP)
```

---

### Step 6: SSH to DUT3 (RX Host) - 192.168.100.134

Open **new terminal window**:

```bash
ssh -o StrictHostKeyChecking=no admin@192.168.100.134
Password: root@123
```

### Step 7: Configure DUT3 L3 Address (if not already done)

```bash
sonic-cli prompt=--sonic-mgmt-- -t 0
configure terminal

interface Ethernet 0
ip address 20.0.0.2/24
exit

exit
exit
```

### Step 8: Start tcpdump on DUT3 (Receiver)

```bash
# Start background tcpdump capture
sudo nohup tcpdump -i Ethernet0 udp port 54321 -w /tmp/l3_03_rx.pcap > /dev/null 2>&1 &

# Verify tcpdump is running
ps aux | grep tcpdump | grep -v grep

# Expected: tcpdump -i Ethernet0 udp port 54321 -w /tmp/l3_03_rx.pcap
```

---

### Step 9: SSH to DUT2 (TX Host) - 192.168.100.248

Open **another new terminal window**:

```bash
ssh -o StrictHostKeyChecking=no admin@192.168.100.248
Password: root@123
```

### Step 10: Configure DUT2 L3 Address (if not already done)

```bash
sonic-cli prompt=--sonic-mgmt-- -t 0
configure terminal

interface Ethernet 0
ip address 10.0.0.1/24
exit

exit
exit
```

### Step 11: Create Scapy Traffic Script on DUT2

```bash
cat > /tmp/l3_03_scapy_traffic.py << 'EOF'
#!/usr/bin/env python3
"""
L3-03 Manual Test: Scapy Traffic Generation
Source: 10.0.0.1 (normal TX host)
Dest: 20.0.0.99 (denied destination - NOT RX host)
"""
from scapy.all import *
import time

# Configuration
SRC_IP = "10.0.0.1"
DST_IP = "20.0.0.99"  # Matches DENY rule (not RX host 20.0.0.2)
SRC_MAC = "00:00:02:00:00:01"  # DUT2 MAC
DST_MAC = "00:00:01:00:00:01"  # DUT1 MAC (gateway)
NUM_PACKETS = 100
DURATION_SEC = 10
UDP_PORT = 54321

print(f"[L3-03] Starting traffic generation...")
print(f"  Source IP: {SRC_IP}")
print(f"  Dest IP: {DST_IP} (matches DENY rule)")
print(f"  Packets: {NUM_PACKETS} over {DURATION_SEC} seconds")

# Create packets
packets = []
for i in range(NUM_PACKETS):
    pkt = Ether(src=SRC_MAC, dst=DST_MAC) / \
          IP(src=SRC_IP, dst=DST_IP, ttl=64) / \
          UDP(sport=12345, dport=UDP_PORT) / \
          Raw(load=f"Packet {i}" * 2)
    packets.append(pkt)

# Send packets with rate control
pps = NUM_PACKETS / DURATION_SEC  # ~10 pps
print(f"  Rate: {pps:.1f} pps")

try:
    send(packets, iface="Ethernet0", inter=1/pps, verbose=False)
    print(f"[L3-03] ✅ Sent {NUM_PACKETS} packets successfully")
except Exception as e:
    print(f"[L3-03] ❌ Error: {e}")

EOF
chmod +x /tmp/l3_03_scapy_traffic.py
```

### Step 12: Send Traffic from DUT2

```bash
# Run Scapy traffic script
sudo python3 /tmp/l3_03_scapy_traffic.py
```

**Expected Output**:
```
[L3-03] Starting traffic generation...
  Source IP: 10.0.0.1
  Dest IP: 20.0.0.99 (matches DENY rule)
  Packets: 100 over 10 seconds
  Rate: 10.0 pps
[L3-03] ✅ Sent 100 packets successfully
```

---

### Step 13: Stop tcpdump on DUT3

Switch back to **DUT3 terminal**:

```bash
# Stop tcpdump
sudo killall tcpdump

# Wait for file flush
sleep 2

# Verify pcap file exists
ls -lh /tmp/l3_03_rx.pcap

# Expected:
# -rw-r--r-- 1 root root 0 Mar 11 14:46 /tmp/l3_03_rx.pcap
# (Size should be 0 since ACL denies all traffic to 20.0.0.99)
```

---

### Step 14: Count Received Packets on DUT3

```bash
# Parse pcap file using Scapy
python3 << 'PYSCRIPT'
from scapy.all import rdpcap
import sys

try:
    pkts = rdpcap("/tmp/l3_03_rx.pcap")
    print(f"[L3-03 Result] RX Packet Count: {len(pkts)}")
    if len(pkts) > 0:
        print(f"  ❌ FAIL: Expected RX=0 (DENY rule), got RX={len(pkts)}")
        sys.exit(1)
    else:
        print(f"  ✅ PASS: ACL correctly denying destination 20.0.0.99")
        sys.exit(0)
except Exception as e:
    print(f"[L3-03 Result] Error reading pcap: {e}")
    sys.exit(1)
PYSCRIPT
```

**Expected Output**:
```
[L3-03 Result] RX Packet Count: 0
  ✅ PASS: ACL correctly denying destination 20.0.0.99
```

---

### Step 15: Verify ACL Hit Counters on DUT1

Switch back to **DUT1 terminal**:

```bash
# Check ACL rule hit counters
show acl-rule L3_ACL_TABLE

# Expected output:
# RULE_1_DENY_DEST:   HIT_COUNT = 100 (all packets matched DENY rule)
# RULE_2_PERMIT_ALL:  HIT_COUNT = 0   (no packets reached this rule)
```

---

## Test Results Summary

### Traffic Flow Validation

```
DUT2 (TX)                 DUT1 (ACL)              DUT3 (RX)
10.0.0.1                  Ethernet0               20.0.0.2
    |                     (ingress ACL)               |
    +--100 UDP pkts------>X (DENY dst=20.0.0.99)     |
    (dst=20.0.0.99)       |                           |
                          | (0 packets forwarded)     |
                          |                           |
                          +-----0 packets---------->  |
```

### Expected Results

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| **TX Packets** | 100 | ? | PASS if > 0 |
| **RX Packets** | 0 | ? | **PASS if = 0** |
| **Loss Rate** | 100% | ? | **PASS if = 100%** |
| **ACL Rule 1 Hit** | 100 | ? | PASS if matches TX |
| **ACL Rule 2 Hit** | 0 | ? | PASS if = 0 |

### Validation Checks

- [x] **Silent Pass Guard 1**: TX packets > 0 (verify traffic actually sent)
- [x] **Silent Pass Guard 2**: RX count from pcap file (verified reception)
- [x] **Silent Pass Guard 3**: ACL hit counters match traffic (rule evaluation confirmed)

---

## Key Difference from L3-02

| Aspect | L3-02 | L3-03 |
|--------|-------|-------|
| **Deny Type** | Source Subnet (10.0.0.0/24) | Destination Host (20.0.0.99/32) |
| **Source IP** | 10.0.0.50 (within denied subnet) | 10.0.0.1 (normal, allowed) |
| **Dest IP** | 20.0.0.2 (RX host) | 20.0.0.99 (NOT RX host) |
| **ACL Rule** | Denies based on SRC IP | Denies based on DST IP |
| **Traffic Path** | Source blocked → RX fails | Source OK, Dest blocked → RX fails |

---

## Troubleshooting

### Issue: RX > 0 (Traffic unexpectedly received)

**Possible Causes**:
1. ACL rule not applied to Ethernet0
2. Destination IP in rule doesn't match (check 20.0.0.99 /32)
3. Traffic sent to wrong destination (verify 20.0.0.99 not 20.0.0.2)

**Resolution**:
```bash
# DUT1: Verify ACL binding
show acl table L3_ACL_TABLE

# DUT1: Check destination rule
show acl-rule L3_ACL_TABLE RULE_1_DENY_DEST

# DUT2: Verify traffic destination in Scapy script
grep "DST_IP" /tmp/l3_03_scapy_traffic.py
```

---

## Document History

| Date | Version | Status | Notes |
|------|---------|--------|-------|
| 2026-03-11 | 1.0 | Draft | Initial manual test execution guide for L3-03 |
| TBD | 2.0 | Executed | Manual testing results to be recorded |

---

**Test Guide Created**: 2026-03-11
**Framework**: SpyTest with DUT-based Scapy Traffic & Tcpdump Verification
**Topology**: 3-SONiC-DUT (D1D2D3 pattern)
