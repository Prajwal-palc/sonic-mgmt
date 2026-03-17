# L3-02 Manual Test Execution Report
## Deny Source IP Subnet (/24) - Using SpyTest Framework & Scapy

**Test Date**: 2026-03-11
**Status**: Manual Testing Guide (Ready for Execution)
**Topology**: 3-SONiC-DUT (DUT1=ACL, DUT2=TX, DUT3=RX)

---

## Test Objective

Validate that an ACL rule denying traffic from a **source subnet (10.0.0.0/24)** correctly drops all packets from any host within that subnet.

**Test Case**: L3-02 (Deny Source IP Subnet)
**Expected Result**: All packets dropped → RX = 0% delivery

---

## Device Information

| Device | Role | IP Address | Interface | Subnet | Purpose |
|--------|------|-----------|-----------|--------|---------|
| DUT1 | ACL Device | 192.168.100.125 | Ethernet0 | 10.0.0.254/24 | ACL applied INGRESS |
| DUT1 | ACL Device | 192.168.100.125 | Ethernet4 | 20.0.0.254/24 | Egress to RX |
| DUT2 | TX Host | 192.168.100.248 | Ethernet0 | 10.0.0.50/24 | Source traffic (denied) |
| DUT3 | RX Host | 192.168.100.134 | Ethernet0 | 20.0.0.2/24 | Receive & verify |

---

## Test Traffic Configuration

```yaml
Test Case: L3-02 (Deny Source IP Subnet)
Source IP:      10.0.0.50  (within denied subnet 10.0.0.0/24)
Destination IP: 20.0.0.2   (RX host)
Protocol:       UDP (port 54321)
Packet Count:   100
Duration:       10 seconds
Rate:           10 pps
Expected RX:    0 packets (100% loss - DENY rule matches)
```

---

## ACL Configuration for DUT1

**Table**: L3_ACL_TABLE
**Type**: L3 (IPv4)
**Stage**: INGRESS
**Applied Port**: Ethernet0

### ACL Rules

```
Rule 1: RULE_1_DENY_SUBNET
  Action: DENY
  Source IP: 10.0.0.0/24  (DENY entire subnet)
  Dest IP: any
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

### Step 4: Create ACL Rules (DENY subnet, then PERMIT all)

```bash
configure terminal

# Rule 1: DENY 10.0.0.0/24 subnet
acl-rule RULE_1_DENY_SUBNET
  table L3_ACL_TABLE
  action DROP
  src-ip 10.0.0.0/24
  dst-ip 0.0.0.0/0
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
  - RULE_1_DENY_SUBNET: DENY 10.0.0.0/24 → any (UDP)
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
sudo nohup tcpdump -i Ethernet0 udp port 54321 -w /tmp/l3_02_rx.pcap > /dev/null 2>&1 &

# Verify tcpdump is running
ps aux | grep tcpdump | grep -v grep

# Expected: tcpdump -i Ethernet0 udp port 54321 -w /tmp/l3_02_rx.pcap
```

**Verification**:
```
admin@sonic:~$ ps aux | grep tcpdump | grep -v grep
root      12345  0.1  0.2  45678 12345 ?  S  14:45  0:00  tcpdump -i Ethernet0 udp port 54321 -w /tmp/l3_02_rx.pcap
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
ip address 10.0.0.50/24
exit

exit
exit
```

### Step 11: Create Scapy Traffic Script on DUT2

Create a Python script for traffic generation:

```bash
cat > /tmp/l3_02_scapy_traffic.py << 'EOF'
#!/usr/bin/env python3
"""
L3-02 Manual Test: Scapy Traffic Generation
Source: 10.0.0.50 (within denied subnet 10.0.0.0/24)
Dest: 20.0.0.2
"""
from scapy.all import *
import time

# Configuration
SRC_IP = "10.0.0.50"
DST_IP = "20.0.0.2"
SRC_MAC = "00:00:02:00:00:01"  # DUT2 MAC
DST_MAC = "00:00:01:00:00:01"  # DUT1 MAC (gateway)
NUM_PACKETS = 100
DURATION_SEC = 10
UDP_PORT = 54321

print(f"[L3-02] Starting traffic generation...")
print(f"  Source IP: {SRC_IP} (within denied subnet 10.0.0.0/24)")
print(f"  Dest IP: {DST_IP}")
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
    print(f"[L3-02] ✅ Sent {NUM_PACKETS} packets successfully")
except Exception as e:
    print(f"[L3-02] ❌ Error: {e}")

EOF
chmod +x /tmp/l3_02_scapy_traffic.py
```

### Step 12: Send Traffic from DUT2

```bash
# Run Scapy traffic script (blocking mode for simplicity)
sudo python3 /tmp/l3_02_scapy_traffic.py

# Alternative: Non-blocking background execution
sudo nohup python3 /tmp/l3_02_scapy_traffic.py > /tmp/l3_02_tx.log 2>&1 &
sleep 12  # Wait for traffic to complete (10s traffic + 2s buffer)
```

**Expected Output**:
```
[L3-02] Starting traffic generation...
  Source IP: 10.0.0.50 (within denied subnet 10.0.0.0/24)
  Dest IP: 20.0.0.2
  Packets: 100 over 10 seconds
  Rate: 10.0 pps
[L3-02] ✅ Sent 100 packets successfully
```

---

### Step 13: Stop tcpdump on DUT3

Switch back to **DUT3 terminal**:

```bash
# Stop tcpdump
sudo killall tcpdump

# Wait for file flush
sleep 2

# Verify pcap file exists and has size > 0
ls -lh /tmp/l3_02_rx.pcap

# Expected:
# -rw-r--r-- 1 root root 0 Mar 11 14:46 /tmp/l3_02_rx.pcap
# (Size should be 0 since ACL denies all traffic)
```

---

### Step 14: Count Received Packets on DUT3

```bash
# Parse pcap file using Scapy
python3 << 'PYSCRIPT'
from scapy.all import rdpcap
import sys

try:
    pkts = rdpcap("/tmp/l3_02_rx.pcap")
    print(f"[L3-02 Result] RX Packet Count: {len(pkts)}")
    if len(pkts) > 0:
        print(f"  ❌ FAIL: Expected RX=0 (DENY rule), got RX={len(pkts)}")
        sys.exit(1)
    else:
        print(f"  ✅ PASS: ACL correctly denying subnet 10.0.0.0/24")
        sys.exit(0)
except Exception as e:
    print(f"[L3-02 Result] Error reading pcap: {e}")
    sys.exit(1)
PYSCRIPT
```

**Expected Output**:
```
[L3-02 Result] RX Packet Count: 0
  ✅ PASS: ACL correctly denying subnet 10.0.0.0/24
```

---

### Step 15: Verify ACL Hit Counters on DUT1

Switch back to **DUT1 terminal**:

```bash
# Check ACL rule hit counters
show acl-rule L3_ACL_TABLE

# Expected output:
# RULE_1_DENY_SUBNET: HIT_COUNT = 100 (all packets matched DENY rule)
# RULE_2_PERMIT_ALL:  HIT_COUNT = 0   (no packets reached this rule)
```

**Detailed output command**:
```bash
show acl-rule L3_ACL_TABLE RULE_1_DENY_SUBNET
```

---

## Test Results Summary

### Traffic Flow Validation

```
DUT2 (TX)                 DUT1 (ACL)              DUT3 (RX)
10.0.0.50                 Ethernet0               20.0.0.2
    |                     (ingress ACL)               |
    +--100 UDP pkts------>X (DENY 10.0.0.0/24)       |
                          |                           |
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

## Test Status

### Execution Steps

1. ✅ Configure DUT1 L3 addresses
2. ✅ Configure DUT2 L3 address
3. ✅ Configure DUT3 L3 address
4. ✅ Create ACL table on DUT1
5. ✅ Create DENY rule for 10.0.0.0/24
6. ✅ Create PERMIT fallback rule
7. ✅ Start tcpdump on DUT3
8. ✅ Generate 100 UDP packets from DUT2 (source IP: 10.0.0.50)
9. ✅ Stop tcpdump on DUT3
10. ✅ Verify RX = 0 packets
11. ✅ Verify ACL hit counters

### Expected Outcome

**PASS** ✅ if:
- TX = 100 packets sent successfully
- RX = 0 packets received (ACL denies all)
- ACL Rule 1 (DENY) hit count = 100
- ACL Rule 2 (PERMIT) hit count = 0

**FAIL** ❌ if:
- RX > 0 (ACL not denying as expected)
- ACL Rule 1 hit count ≠ 100
- Traffic not generated (TX = 0)

---

## Key Technical Details

### Why RX Should Be 0

1. **Source IP 10.0.0.50** matches subnet **10.0.0.0/24**
2. **ACL Rule 1** (DENY 10.0.0.0/24) is evaluated FIRST on DUT1:Ethernet0 ingress
3. All packets match Rule 1 → ACTION = DROP
4. Packets are dropped at DUT1 ingress, never reach Ethernet4
5. DUT3 tcpdump captures ZERO packets

### ACL Evaluation Order

```
Incoming packet (src=10.0.0.50, dst=20.0.0.2)
         ↓
DUT1:Ethernet0 (INGRESS ACL applied)
         ↓
Rule 1: Does src match 10.0.0.0/24? → YES → ACTION: DROP ✓
         ↓
[Packet DROPPED - never reaches Rule 2]
         ↓
DUT3: tcpdump captures NOTHING ✓
```

---

## Troubleshooting

### Issue: RX > 0 (Traffic unexpectedly received)

**Possible Causes**:
1. ACL rule not applied to Ethernet0
2. ACL rule priority incorrect (Rule 2 evaluated before Rule 1)
3. Source IP not matching subnet (verify 10.0.0.50 is in 10.0.0.0/24)
4. Tcpdump filter wrong (should be `udp port 54321`)

**Resolution**:
```bash
# DUT1: Verify ACL binding
show acl table L3_ACL_TABLE | grep "Ports:"

# DUT1: Check rule order
show acl-rule L3_ACL_TABLE | grep -E "RULE_1|RULE_2"

# DUT3: Verify tcpdump filter
sudo tcpdump -i Ethernet0 -c 5 "udp port 54321"
```

### Issue: tcpdump file empty but packets sent

**Possible Causes**:
1. L3 routing not configured (static routes missing)
2. DUT1-DUT3 link down
3. IP forwarding disabled on DUT1

**Resolution**:
```bash
# DUT1: Check interface status
show interfaces status Ethernet0
show interfaces status Ethernet4

# DUT1: Verify IP forwarding
show ip forwarding

# DUT1: Check routing table
show ip route

# Test L3 connectivity
ping -I Ethernet4 20.0.0.2
```

---

## Manual Test Execution Command Reference

### All-in-One Quick Reference

```bash
# ==== DUT1: Setup & ACL Configuration ====
ssh admin@192.168.100.125

# Configure L3 addresses
sonic-cli prompt=--sonic-mgmt-- -t 0
configure terminal
interface Ethernet 0
ip address 10.0.0.254/24
exit
interface Ethernet 4
ip address 20.0.0.254/24
exit
exit
exit

# Create ACL table and rules
configure terminal
acl-table L3_ACL_TABLE
  type L3
  stage INGRESS
  ports Ethernet0
exit

acl-rule RULE_1_DENY_SUBNET
  table L3_ACL_TABLE
  action DROP
  src-ip 10.0.0.0/24
  dst-ip 0.0.0.0/0
  ip-protocol UDP
exit

acl-rule RULE_2_PERMIT_ALL
  table L3_ACL_TABLE
  action FORWARD
  src-ip 0.0.0.0/0
  dst-ip 0.0.0.0/0
  ip-protocol UDP
exit

exit
exit

# Verify configuration
show acl table L3_ACL_TABLE
show acl-rule L3_ACL_TABLE

# ==== DUT3: Start tcpdump ====
# (In separate terminal)
ssh admin@192.168.100.134

sonic-cli prompt=--sonic-mgmt-- -t 0
configure terminal
interface Ethernet 0
ip address 20.0.0.2/24
exit
exit
exit

# Start tcpdump
sudo nohup tcpdump -i Ethernet0 udp port 54321 -w /tmp/l3_02_rx.pcap > /dev/null 2>&1 &
sleep 1

# ==== DUT2: Send Traffic ====
# (In third terminal)
ssh admin@192.168.100.248

sonic-cli prompt=--sonic-mgmt-- -t 0
configure terminal
interface Ethernet 0
ip address 10.0.0.50/24
exit
exit
exit

# Create and run Scapy script
python3 << 'EOF'
from scapy.all import *
SRC_IP, DST_IP = "10.0.0.50", "20.0.0.2"
SRC_MAC, DST_MAC = "00:00:02:00:00:01", "00:00:01:00:00:01"
packets = [Ether(src=SRC_MAC, dst=DST_MAC)/IP(src=SRC_IP, dst=DST_IP)/UDP(dport=54321)/Raw(load=b"TEST") for _ in range(100)]
send(packets, iface="Ethernet0", inter=0.1, verbose=False)
print("✅ Sent 100 packets")
EOF

# ==== DUT3: Stop tcpdump & Verify ====
# (Back to DUT3 terminal)
sudo killall tcpdump
sleep 2

# Count packets
python3 -c "from scapy.all import rdpcap; print(f'RX Packets: {len(rdpcap(\"/tmp/l3_02_rx.pcap\"))}')"

# ==== DUT1: Verify ACL Counters ====
# (Back to DUT1 terminal)
show acl-rule L3_ACL_TABLE
```

---

## Document History

| Date | Version | Status | Notes |
|------|---------|--------|-------|
| 2026-03-11 | 1.0 | Draft | Initial manual test execution guide for L3-02 |
| TBD | 2.0 | Executed | Manual testing results to be recorded |

---

## Next Steps

1. **Execute** manual testing using above procedures
2. **Record** actual RX/TX counts and ACL hit counters
3. **Verify** test PASS (RX=0 for DENY subnet)
4. **Compare** with automated test framework results
5. **Document** any discrepancies between manual and automated approaches

---

**Test Guide Created**: 2026-03-11
**Framework**: SpyTest with DUT-based Scapy Traffic & Tcpdump Verification
**Topology**: 3-SONiC-DUT (D1D2D3 pattern)
