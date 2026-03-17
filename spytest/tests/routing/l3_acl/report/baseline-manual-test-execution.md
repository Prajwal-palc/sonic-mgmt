# L3 Baseline Manual Test Execution Report

## Baseline Test (No ACL) - L3 Connectivity Validation Using SpyTest Framework & Scapy

**Test Date**: 2026-03-11
**Status**: Manual Testing Guide (Ready for Execution)
**Topology**: 3-SONiC-DUT (DUT1=Gateway, DUT2=TX, DUT3=RX)

---

## Test Objective

Validate that **L3 traffic flows correctly** between DUT2 (TX) and DUT3 (RX) through DUT1 (gateway) **WITHOUT any ACL rules applied**. This baseline test establishes connectivity validation before deploying ACL rules.

**Test Case**: L3-Baseline (No ACL)
**Expected Result**: All packets forwarded → RX ≥ 90% delivery

---

## Device Information

| Device | Role | IP Address | Interface | Subnet | Purpose |
|--------|------|-----------|-----------|--------|---------|
| DUT1 | Gateway Device | 192.168.100.125 | Ethernet0 | 10.0.0.254/24 | L3 Router (no ACL) |
| DUT1 | Gateway Device | 192.168.100.125 | Ethernet4 | 20.0.0.254/24 | Gateway to RX |
| DUT2 | TX Host | 192.168.100.248 | Ethernet0 | 10.0.0.1/24 | Source traffic |
| DUT3 | RX Host | 192.168.100.134 | Ethernet0 | 20.0.0.2/24 | Receive & verify |

---

## Test Traffic Configuration

```yaml
Test Case: L3-Baseline (No ACL)
Source IP:      10.0.0.1   (TX host)
Destination IP: 20.0.0.2   (RX host)
Protocol:       UDP (port 54321)
Packet Count:   100
Duration:       10 seconds
Rate:           10 pps
Expected RX:    ≥90 packets (≥90% delivery - baseline connectivity)
```

---

## Manual Testing Procedure

### Step 1: SSH to DUT1 (Gateway Device) - 192.168.100.125

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

**Expected Output**:
```
DUT1# show interface status | grep -E "Ethernet0|Ethernet4"
Ethernet0       up      up      UP
Ethernet4       up      up      UP
```

### Step 3: Verify L3 Routing Status (DUT1)

```bash
# Check that routing is working between the two subnets
show ip route

# Expected output (should show connected routes):
# 10.0.0.0/24 is directly connected via Ethernet0
# 20.0.0.0/24 is directly connected via Ethernet4
```

### Step 4: SSH to DUT3 (RX Host) - 192.168.100.134

Open **new terminal window**:

```bash
ssh -o StrictHostKeyChecking=no admin@192.168.100.134
Password: root@123
```

### Step 5: Configure DUT3 L3 Address (if not already done)

```bash
sonic-cli prompt=--sonic-mgmt-- -t 0
configure terminal

interface Ethernet 0
ip address 20.0.0.2/24
exit

exit
exit
```

### Step 6: Start tcpdump on DUT3 (Receiver)

```bash
# Start background tcpdump capture
sudo nohup tcpdump -i Ethernet0 udp port 54321 -w /tmp/baseline_rx.pcap > /dev/null 2>&1 &

# Verify tcpdump is running
ps aux | grep tcpdump | grep -v grep

# Expected: tcpdump -i Ethernet0 udp port 54321 -w /tmp/baseline_rx.pcap
```

---

### Step 7: SSH to DUT2 (TX Host) - 192.168.100.248

Open **another new terminal window**:

```bash
ssh -o StrictHostKeyChecking=no admin@192.168.100.248
Password: root@123
```

### Step 8: Configure DUT2 L3 Address (if not already done)

```bash
sonic-cli prompt=--sonic-mgmt-- -t 0
configure terminal

interface Ethernet 0
ip address 10.0.0.1/24
exit

exit
exit
```

### Step 9: Create Scapy Traffic Script on DUT2

```bash
cat > /tmp/baseline_scapy_traffic.py << 'EOF'
#!/usr/bin/env python3
"""
Baseline Test: Scapy Traffic Generation
Source: 10.0.0.1 (TX host)
Dest: 20.0.0.2 (RX host)
No ACL filtering - testing pure L3 connectivity
"""
from scapy.all import *
import time

# Configuration
SRC_IP = "10.0.0.1"
DST_IP = "20.0.0.2"    # RX host (actual receiver)
SRC_MAC = "00:00:02:00:00:01"  # DUT2 MAC
DST_MAC = "00:00:01:00:00:01"  # DUT1 MAC (gateway)
NUM_PACKETS = 100
DURATION_SEC = 10
UDP_PORT = 54321

print(f"[Baseline] Starting traffic generation...")
print(f"  Source IP: {SRC_IP}")
print(f"  Dest IP: {DST_IP} (RX host)")
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
    print(f"[Baseline] ✅ Sent {NUM_PACKETS} packets successfully")
except Exception as e:
    print(f"[Baseline] ❌ Error: {e}")

EOF
chmod +x /tmp/baseline_scapy_traffic.py
```

### Step 10: Send Traffic from DUT2

```bash
# Run Scapy traffic script
sudo python3 /tmp/baseline_scapy_traffic.py
```

**Expected Output**:
```
[Baseline] Starting traffic generation...
  Source IP: 10.0.0.1
  Dest IP: 20.0.0.2 (RX host)
  Packets: 100 over 10 seconds
  Rate: 10.0 pps
[Baseline] ✅ Sent 100 packets successfully
```

---

### Step 11: Stop tcpdump on DUT3

Switch back to **DUT3 terminal**:

```bash
# Stop tcpdump
sudo killall tcpdump

# Wait for file flush
sleep 2

# Verify pcap file exists
ls -lh /tmp/baseline_rx.pcap

# Expected:
# -rw-r--r-- 1 root root 5400 Mar 11 14:46 /tmp/baseline_rx.pcap
# (Size should be > 0 since NO ACL is blocking traffic - all 100 packets should be received)
```

---

### Step 12: Count Received Packets on DUT3

```bash
# Parse pcap file using Scapy
python3 << 'PYSCRIPT'
from scapy.all import rdpcap
import sys

try:
    pkts = rdpcap("/tmp/baseline_rx.pcap")
    print(f"[Baseline Result] RX Packet Count: {len(pkts)}")
    if len(pkts) >= 90:
        print(f"  ✅ PASS: Baseline connectivity verified ({len(pkts)}/100 packets = {len(pkts)}% delivery)")
        sys.exit(0)
    elif len(pkts) > 0:
        print(f"  ⚠️  WARNING: Partial delivery ({len(pkts)}/100 packets = {len(pkts)}%)")
        print(f"       Expected ≥90 packets for baseline. Check L3 routing.")
        sys.exit(1)
    else:
        print(f"  ❌ FAIL: No packets received - L3 connectivity broken")
        sys.exit(1)
except Exception as e:
    print(f"[Baseline Result] Error reading pcap: {e}")
    sys.exit(1)
PYSCRIPT
```

**Expected Output** (Baseline Success):
```
[Baseline Result] RX Packet Count: 100
  ✅ PASS: Baseline connectivity verified (100/100 packets = 100% delivery)
```

**Expected Output** (Baseline Warning):
```
[Baseline Result] RX Packet Count: 95
  ⚠️  WARNING: Partial delivery (95/100 packets = 95% delivery)
       Expected ≥90 packets for baseline. Check L3 routing.
```

**Expected Output** (Baseline Failure):
```
[Baseline Result] RX Packet Count: 0
  ❌ FAIL: No packets received - L3 connectivity broken
```

---

### Step 13: Verify Routing on DUT1 (Optional)

Switch back to **DUT1 terminal**:

```bash
# Check routing table to confirm connected routes
show ip route

# Expected output:
# 10.0.0.0/24 is directly connected via Ethernet0
# 20.0.0.0/24 is directly connected via Ethernet4

# Check interface counters (optional)
show interface counters | grep -E "Ethernet0|Ethernet4"
```

---

## Test Results Summary

### Traffic Flow Validation

```
DUT2 (TX)                 DUT1 (Gateway)          DUT3 (RX)
10.0.0.1                  (No ACL)                20.0.0.2
    |                                             |
    +--100 UDP pkts----->Ethernet0               |
                         (FORWARDED)             |
                         |                       |
                         Ethernet4 ------>Ethernet0 -->
                         (100 pkts forward)      ^
                                                 |
                                             (RX verified)
```

### Expected Results

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| **TX Packets** | 100 | ? | PASS if = 100 |
| **RX Packets** | ≥90 | ? | **PASS if ≥ 90** |
| **Delivery Rate** | ≥90% | ? | **PASS if ≥ 90%** |
| **L3 Routing** | Connected | ? | PASS if routes exist |

### Validation Checks

- [x] **Connectivity Guard 1**: TX packets = 100 (traffic actually sent)
- [x] **Connectivity Guard 2**: RX count from pcap file (verified reception)
- [x] **Connectivity Guard 3**: Delivery rate ≥90% (acceptable baseline)

---

## Baseline Success Criteria

This baseline test validates **pure L3 connectivity** without any ACL filtering:

### PASS Condition
- **Minimum 90 packets received** (≥90% delivery)
- **L3 routing working** between 10.0.0.0/24 and 20.0.0.0/24
- **Tcpdump captures valid UDP packets** on DUT3

### FAIL Condition
- **Less than 90 packets received** (< 90% delivery)
- **0 packets received** (complete connectivity failure)
- **L3 routing not established** on DUT1
- **Interface links DOWN** on any device

---

## Troubleshooting

### Issue: RX = 0 (No packets received)

**Possible Causes**:
1. DUT1 interfaces not configured
2. L3 routing not enabled on DUT1
3. DUT3 not listening on correct port
4. Tcpdump filter too restrictive

**Resolution**:
```bash
# DUT1: Verify interfaces are UP and have IPs
show interface status | grep -E "Ethernet0|Ethernet4"
show interface | grep -E "Ethernet0|Ethernet4" | grep "ip address"

# DUT3: Verify tcpdump is capturing
sudo tcpdump -i Ethernet0 -c 5

# DUT2: Verify traffic actually sent
sudo tcpdump -i Ethernet0 -c 5 "udp port 54321"
```

### Issue: RX < 90 (Partial delivery)

**Possible Causes**:
1. Link flapping on one of the interfaces
2. Buffer drops at DUT1 during forwarding
3. MTU mismatch between interfaces
4. Traffic rate too high for device

**Resolution**:
```bash
# Check interface status on all DUTs
show interface status

# Check interface errors
show interface counters error | grep -E "Ethernet0|Ethernet4"

# Check routing table
show ip route
```

### Issue: Tcpdump capture file too small

**Possible Causes**:
1. Scapy traffic script failed silently
2. Tcpdump not running properly
3. Port filter blocking traffic

**Resolution**:
```bash
# DUT3: Verify tcpdump is running
ps aux | grep tcpdump

# Check tcpdump capture without port filter
sudo tcpdump -i Ethernet0 -w /tmp/baseline_test_nofilter.pcap -c 100

# Verify raw traffic on interface
sudo tcpdump -i Ethernet0 -c 10
```

---

## Document History

| Date | Version | Status | Notes |
|------|---------|--------|-------|
| 2026-03-11 | 1.0 | Draft | Initial baseline manual test execution guide |
| TBD | 2.0 | Executed | Manual testing results to be recorded |

---

**Test Guide Created**: 2026-03-11
**Framework**: SpyTest with DUT-based Scapy Traffic & Tcpdump Verification
**Topology**: 3-SONiC-DUT (D1D2D3 pattern)
**Purpose**: Validate L3 connectivity baseline before ACL testing
