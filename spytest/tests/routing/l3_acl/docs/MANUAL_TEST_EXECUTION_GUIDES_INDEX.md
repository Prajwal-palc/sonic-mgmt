# L3 ACL Manual Test Execution Guides - Complete Index

**Date**: 2026-03-11
**Framework**: SpyTest 3-SONiC-DUT Architecture with Scapy & Tcpdump
**Status**: ✅ All Guides Ready for Execution

---

## Overview

This document provides a comprehensive index of all manual testing guides for L3 ACL validation. Each guide follows the SpyTest-native 3-SONiC-DUT pattern with DUT-based Scapy traffic generation and tcpdump forensic verification.

### Topology Reference

```
DUT2 (TX Host)           DUT1 (ACL Device)         DUT3 (RX Host)
10.0.0.1/24              Gateway                   20.0.0.2/24
  |                      (no ACL)                   |
  +--Ethernet0---------->Ethernet0 [INGRESS]        |
                         |                          |
                         +--Ethernet4------------>Ethernet0
                         (routing + ACL)
```

---

## Test Cases - Quick Reference

| Test Case | Title | ACL Rule | Expected RX | Guide File | Status |
|-----------|-------|----------|-------------|------------|--------|
| **Baseline** | L3 Connectivity (No ACL) | None | ≥90% | `baseline-manual-test-execution.md` | ✅ Ready |
| **L3-01** | Deny source IP (10.0.0.99/32) | DENY source | 0% | `L3-01-MANUAL-TEST-EXECUTION.md` | ✅ Ready |
| **L3-02** | Deny source subnet (10.0.0.0/24) | DENY subnet | 0% | `l3-02-manual-test-execution.md` | ✅ Ready |
| **L3-03** | Deny destination IP (20.0.0.99/32) | DENY dest | 0% | `l3-03-manual-test-execution.md` | ✅ Ready |

---

## Guide Descriptions

### 1. Baseline Test - L3 Connectivity Validation

**File**: `baseline-manual-test-execution.md`

**Purpose**: Establish baseline L3 connectivity before applying any ACL rules.

**Key Characteristics**:
- No ACL configuration
- Validates pure L3 routing between subnets
- Expected delivery: ≥90% (100 packets)
- Success criteria: All devices communicating via DUT1 gateway

**When to Run**: First - before any ACL tests

**Steps Overview**:
1. Configure L3 addresses on DUT1 (Ethernet0: 10.0.0.254, Ethernet4: 20.0.0.254)
2. Configure DUT2 interface (Ethernet0: 10.0.0.1)
3. Configure DUT3 interface (Ethernet0: 20.0.0.2)
4. Start tcpdump on DUT3 (UDP port 54321)
5. Generate 100 UDP packets from DUT2 to DUT3
6. Verify ≥90 packets received on DUT3
7. Document results

**Expected Result**: `✅ PASS: Baseline connectivity verified (100/100 packets = 100% delivery)`

---

### 2. L3-01 Test - Deny Source IP (Host Level)

**File**: `L3-01-MANUAL-TEST-EXECUTION.md`

**Purpose**: Validate ACL rule denying a specific source IP address.

**ACL Configuration**:
```
Table: L3_ACL_TABLE (Type: L3, Stage: INGRESS, Port: Ethernet0)

Rule 1: RULE_1_DENY_SOURCE
  Action: DENY
  Source IP: 10.0.0.99/32 (specific host)
  Destination IP: any
  Protocol: UDP

Rule 2: RULE_2_PERMIT_ALL
  Action: PERMIT
  Source IP: any
  Destination IP: any
  Protocol: UDP (fallback)
```

**Traffic Configuration**:
- Source IP: 10.0.0.99 (matches DENY rule)
- Destination IP: 20.0.0.2 (RX host)
- Packets: 100 UDP packets

**Expected Result**: `✅ PASS: ACL correctly denying source 10.0.0.99 (RX = 0 packets)`

---

### 3. L3-02 Test - Deny Source Subnet

**File**: `l3-02-manual-test-execution.md`

**Purpose**: Validate ACL rule denying an entire source subnet.

**ACL Configuration**:
```
Table: L3_ACL_TABLE (Type: L3, Stage: INGRESS, Port: Ethernet0)

Rule 1: RULE_1_DENY_SUBNET
  Action: DENY
  Source IP: 10.0.0.0/24 (entire subnet)
  Destination IP: any
  Protocol: UDP

Rule 2: RULE_2_PERMIT_ALL
  Action: PERMIT
  Source IP: any
  Destination IP: any
  Protocol: UDP (fallback)
```

**Traffic Configuration**:
- Source IP: 10.0.0.50 (within denied subnet)
- Destination IP: 20.0.0.2 (RX host)
- Packets: 100 UDP packets

**Expected Result**: `✅ PASS: ACL correctly denying source subnet 10.0.0.0/24 (RX = 0 packets)`

**Key Difference from L3-01**:
- L3-01 denies a specific host (/32)
- L3-02 denies an entire subnet (/24)
- L3-02 blocks all traffic from 10.0.0.0 to 10.0.0.255

---

### 4. L3-03 Test - Deny Destination IP (Host Level)

**File**: `l3-03-manual-test-execution.md`

**Purpose**: Validate ACL rule denying a specific destination IP address.

**ACL Configuration**:
```
Table: L3_ACL_TABLE (Type: L3, Stage: INGRESS, Port: Ethernet0)

Rule 1: RULE_1_DENY_DEST
  Action: DENY
  Source IP: any
  Destination IP: 20.0.0.99/32 (specific host)
  Protocol: UDP

Rule 2: RULE_2_PERMIT_ALL
  Action: PERMIT
  Source IP: any
  Destination IP: any
  Protocol: UDP (fallback)
```

**Traffic Configuration**:
- Source IP: 10.0.0.1 (normal, allowed)
- Destination IP: 20.0.0.99 (NOT the RX host 20.0.0.2)
- Packets: 100 UDP packets

**Expected Result**: `✅ PASS: ACL correctly denying destination 20.0.0.99 (RX = 0 packets)`

**Key Difference from L3-02**:
- L3-02 denies based on **SOURCE** IP
- L3-03 denies based on **DESTINATION** IP
- L3-03 traffic sent to 20.0.0.99 (not the actual RX host)

---

## Recommended Test Execution Order

For comprehensive validation, execute tests in this order:

1. **Baseline** - Verify L3 connectivity works
2. **L3-01** - Test host-level source IP filtering
3. **L3-02** - Test subnet-level source IP filtering
4. **L3-03** - Test host-level destination IP filtering

This sequence validates:
- ✅ Pure connectivity (no ACL interference)
- ✅ Source IP filtering at host granularity
- ✅ Source IP filtering at subnet granularity
- ✅ Destination IP filtering at host granularity

---

## Manual Testing Procedure - General Steps

Each guide follows this standardized 13-15 step procedure:

1. SSH to DUT1 and configure L3 addresses
2. SSH to DUT2 and configure L3 addresses
3. SSH to DUT3 and configure L3 addresses
4. **(ACL tests only)** Create ACL table on DUT1
5. **(ACL tests only)** Create ACL rules on DUT1
6. **(ACL tests only)** Verify ACL configuration
7. Start tcpdump on DUT3 (background capture)
8. Create Scapy traffic script on DUT2
9. Generate traffic from DUT2 to DUT3
10. Stop tcpdump on DUT3
11. Count received packets using `rdpcap()`
12. **(ACL tests only)** Verify ACL hit counters
13. Document results

---

## Common Elements in All Guides

### Device Configuration

All guides configure the same 3-SONiC-DUT topology:

**DUT1 (sp-Sonic-106 / 192.168.100.125)**:
- Ethernet0: 10.0.0.254/24 (gateway to TX subnet)
- Ethernet4: 20.0.0.254/24 (gateway to RX subnet)

**DUT2 (sp-Sonic-107 / 192.168.100.248)**:
- Ethernet0: 10.0.0.1/24 (TX host)

**DUT3 (sp-Sonic-108 / 192.168.100.134)**:
- Ethernet0: 20.0.0.2/24 (RX host)

### Traffic Generation Pattern

All guides use the same Scapy script pattern:
```python
from scapy.all import *

packets = [
    Ether(src=SRC_MAC, dst=DST_MAC) /
    IP(src=SRC_IP, dst=DST_IP, ttl=64) /
    UDP(sport=12345, dport=54321) /
    Raw(load=f"Packet {i}" * 2)
    for i in range(NUM_PACKETS)
]
send(packets, iface="Ethernet0", inter=1/pps, verbose=False)
```

### Verification Pattern

All guides use identical verification approach:
```bash
# 1. Start tcpdump on DUT3
sudo tcpdump -i Ethernet0 udp port 54321 -w /tmp/<test_name>_rx.pcap

# 2. Generate traffic on DUT2
sudo python3 /tmp/<test_name>_scapy_traffic.py

# 3. Stop tcpdump and analyze
python3 << 'PYSCRIPT'
from scapy.all import rdpcap
pkts = rdpcap("/tmp/<test_name>_rx.pcap")
print(f"RX Packet Count: {len(pkts)}")
PYSCRIPT
```

---

## Silent Pass Prevention

All guides implement three validation guards:

**Guard 1: TX > 0**
- Verifies traffic was actually generated
- Prevents false pass from no traffic sent

**Guard 2: RX from pcap**
- Counts packets from tcpdump pcap file
- Ensures reception was actually verified (not assumed)

**Guard 3: ACL hit counters** (ACL tests only)
- Verifies ACL rules evaluated traffic
- Confirms rule matching logic worked

---

## Device SSH Information

### Credentials (All DUTs)
- **Username**: admin
- **Password**: root@123

### Device IP Addresses
| Device | IP Address | Role |
|--------|-----------|------|
| DUT1 | 192.168.100.125 | ACL Device (Gateway) |
| DUT2 | 192.168.100.248 | TX Host (Traffic Generator) |
| DUT3 | 192.168.100.134 | RX Host (Packet Receiver) |

### SSH Command Template
```bash
ssh -o StrictHostKeyChecking=no admin@<device_ip>
Password: root@123
```

---

## Troubleshooting Quick Reference

### Issue: RX = 0 packets (all tests)

**Possible Causes**:
1. Devices not configured (missing IP addresses)
2. Tcpdump not running
3. Traffic not reaching DUT1
4. ACL incorrectly configured

**Quick Checks**:
```bash
# DUT1: Verify L3 interfaces
show interface status | grep -E "Ethernet0|Ethernet4"

# DUT2: Verify can reach gateway
ping 10.0.0.254

# DUT3: Check tcpdump is running
ps aux | grep tcpdump | grep -v grep
```

### Issue: Baseline RX < 90 packets

**Possible Causes**:
1. Link drops or flapping
2. Routing loops
3. Interface errors

**Quick Check**:
```bash
# Check interface counters
show interface counters
show interface counters error
```

### Issue: ACL rules not matching

**Possible Causes**:
1. ACL rule not created correctly
2. ACL not applied to Ethernet0
3. Traffic parameters don't match rule

**Quick Check**:
```bash
# Verify ACL configuration
show acl table L3_ACL_TABLE
show acl-rule L3_ACL_TABLE

# Check hit counters
show acl-rule L3_ACL_TABLE | grep "hit_count"
```

---

## Files Generated During Testing

Each test generates the following files on DUT3:

| Filename | Purpose | Expected Size |
|----------|---------|----------------|
| `/tmp/baseline_rx.pcap` | Baseline test capture | >5000 bytes |
| `/tmp/l3_01_rx.pcap` | L3-01 test capture | ~200 bytes (empty) |
| `/tmp/l3_02_rx.pcap` | L3-02 test capture | ~200 bytes (empty) |
| `/tmp/l3_03_rx.pcap` | L3-03 test capture | ~200 bytes (empty) |

### Cleanup (Optional)

```bash
# On DUT3, remove old pcap files before running tests
rm -f /tmp/*_rx.pcap
```

---

## Integration with SpyTest Automated Tests

These manual testing guides correspond to automated test methods in:

**File**: `tests/routing/l3_acl/test_l3_acl_basic_refactored.py`

**Test Methods**:
- `test_l3_baseline_permit_all()` → Baseline guide
- `test_l3_01_deny_source_ip()` → L3-01 guide
- `test_l3_02_deny_source_subnet()` → L3-02 guide
- `test_l3_03_deny_dest_ip()` → L3-03 guide

**How to Run Automated Tests**:
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_basic_refactored.py \
    --logs-path ./logs/l3_acl_$(date +%F_%H%M%S) \
    --log-level info --skip-init-config
```

---

## Test Results Documentation

After executing each manual test, record results in the test guide:

**Template for Each Test**:
```markdown
## Manual Execution Results - [DATE]

### Device Status
- DUT1 Interfaces: [UP/DOWN]
- DUT2 Connectivity: [PASS/FAIL]
- DUT3 Tcpdump: [Running/Failed]

### Traffic Results
- TX Packets Sent: [N]
- RX Packets Received: [N]
- Delivery Rate: [N%]

### ACL Status (if applicable)
- Rule 1 Hit Count: [N]
- Rule 2 Hit Count: [N]

### Overall Result: [PASS/FAIL]

### Notes
[Any observations or issues]
```

---

## Summary

✅ **All 4 manual testing guides are complete and ready for execution:**

1. **baseline-manual-test-execution.md** - L3 connectivity validation
2. **L3-01-MANUAL-TEST-EXECUTION.md** - Source IP host-level denial
3. **l3-02-manual-test-execution.md** - Source subnet-level denial
4. **l3-03-manual-test-execution.md** - Destination IP host-level denial

Each guide provides:
- ✅ Step-by-step device configuration
- ✅ ACL setup instructions (where applicable)
- ✅ Scapy traffic generation scripts
- ✅ Tcpdump verification procedures
- ✅ Packet counting and validation
- ✅ Troubleshooting guidance
- ✅ Expected results and pass/fail criteria

**Ready for**: Immediate manual execution following the guides in order (Baseline → L3-01 → L3-02 → L3-03)

---

**Documentation Version**: 1.0
**Created**: 2026-03-11
**Status**: ✅ Complete and Ready for Testing
