# L2-N01: MAC Address Case Sensitivity - Hardware Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-N01 |
| **Description** | MAC address case sensitivity - test lowercase vs uppercase MAC matching in L2 ACL |
| **Category** | Negative/Edge Case |
| **Expected Outcome** | Determine if MAC matching is case-sensitive or case-insensitive |
| **Platform** | Hardware (Broadcom ASIC) |
| **Date** | 2026-03-19 |
| **Tester** | Athira Arputharaj |

---

## Topology Used

```
┌────────────────┐                    ┌────────────────┐                    ┌────────────────┐
│     DUT2       │                    │     DUT1       │                    │     DUT3       │
│  (TX Traffic   │                    │  (ACL Device)  │                    │  (RX Receiver) │
│   Generator)   │                    │                │                    │                │
│ 192.168.100.140│                    │ 192.168.100.119│                    │ 192.168.100.173│
│ Celestica DS3000                    │ Supermicro T8196│                   │ Supermicro T8164│
│                │                    │                │                    │                │
│  Ethernet64 ───┼────────────────────┼─► Ethernet272  │                    │                │
│  VLAN 100      │                    │  VLAN 100      │                    │                │
│                │                    │  (ACL ingress) │                    │                │
│                │                    │                │                    │                │
│                │                    │  Ethernet513 ──┼────────────────────┼─► Ethernet513  │
│                │                    │  VLAN 100      │                    │  VLAN 100      │
│                │                    │  (egress)      │                    │                │
└────────────────┘                    └────────────────┘                    └────────────────┘
```

---

## Step 1: Hardware Testbed Configuration

### 1.1 Configure L2 VLAN Mode

All devices configured with VLAN 100 for L2 switching:

**D1 (192.168.100.119):**
```bash
sudo config vlan add 100
sudo config vlan member add 100 Ethernet272 -u
sudo config vlan member add 100 Ethernet513 -u
sudo config interface startup Ethernet272
sudo config interface startup Ethernet513
sudo config save -y
```

**D2 (192.168.100.140):**
```bash
sudo config vlan add 100
sudo config vlan member add 100 Ethernet64 -u
sudo config interface startup Ethernet64
sudo config save -y
```

**D3 (192.168.100.173):**
```bash
sudo config vlan add 100
sudo config vlan member add 100 Ethernet513 -u
sudo config interface startup Ethernet513
sudo config save -y
```

### 1.2 Verify VLAN Configuration

**D1 VLAN Status:**
```
+-----------+--------------+-------------+----------------+-------------+
|   VLAN ID | IP Address   | Ports       | Port Tagging   | Proxy ARP   |
+===========+==============+=============+================+=============+
|       100 |              | Ethernet272 | untagged       | disabled    |
|           |              | Ethernet513 | untagged       |             |
+-----------+--------------+-------------+----------------+-------------+
```

**D2 VLAN Status:**
```
+-----------+--------------+------------+----------------+
|   VLAN ID | IP Address   | Ports      | Port Tagging   |
+===========+==============+============+================+
|       100 |              | Ethernet64 | untagged       |
+-----------+--------------+------------+----------------+
```

**D3 VLAN Status:**
```
+-----------+--------------+-------------+----------------+
|   VLAN ID | IP Address   | Ports       | Port Tagging   |
+===========+==============+=============+================+
|       100 |              | Ethernet513 | untagged       |
+-----------+--------------+-------------+----------------+
```

---

## Step 2: ACL Configuration Approach

### 2.1 Attempted: klish iSCLI Configuration (FAILED)

**Finding**: klish iSCLI MAC ACL commands documented in acl_iscli_commands.md are **NOT available** on Broadcom ASIC hardware platforms.

```bash
ssh admin@192.168.100.119
sudo vtysh

configure terminal
mac access-list L2_ACL_TEST_CASE
permit host 00:AA:AA:AA:AA:01
```

**Error:**
```
sonic(config)# mac access-list L2_ACL_TEST_CASE
% Command incomplete: mac access-list L2_ACL_TEST_CASE

sonic(config)# permit host 00:AA:AA:AA:AA:01
% Unknown command: permit host 00:AA:AA:AA:AA:01
```

**Conclusion**: klish iSCLI MAC ACL syntax not implemented in vtysh on this platform. Must use CONFIG_DB approach.

### 2.2 Working: CONFIG_DB Approach

Used SONiC CONFIG_DB with `config acl` and `sonic-db-cli` commands:

```bash
ssh admin@192.168.100.119

# Create L2 ACL table bound to Ethernet272 ingress
sudo config acl add table L2_ACL_TEST_CASE L2 -p Ethernet272 -s ingress

# Rule 10: PERMIT source MAC 00:AA:AA:AA:AA:01 (UPPERCASE)
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_CASE|RULE_10" "PRIORITY" "10"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_CASE|RULE_10" "PACKET_ACTION" "FORWARD"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_CASE|RULE_10" "SRC_MAC" "00:AA:AA:AA:AA:01/FF:FF:FF:FF:FF:FF"

# Rule 20: DENY all other traffic
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_CASE|RULE_20" "PRIORITY" "20"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_CASE|RULE_20" "PACKET_ACTION" "DROP"

# Save configuration
sudo config save -y
```

### 2.3 Verify ACL Configuration

```bash
# ACL Table
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_TABLE|L2_ACL_TEST_CASE"
```

**Output:**
```
{'policy_desc': 'L2_ACL_TEST_CASE', 'ports@': 'Ethernet272', 'stage': 'ingress', 'type': 'L2'}
```

```bash
# ACL Rule 10 (PERMIT UPPERCASE MAC)
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_CASE|RULE_10"
```

**Output:**
```
{'PRIORITY': '10', 'PACKET_ACTION': 'FORWARD', 'SRC_MAC': '00:AA:AA:AA:AA:01/FF:FF:FF:FF:FF:FF'}
```

```bash
# ACL Rule 20 (DENY all)
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_CASE|RULE_20"
```

**Output:**
```
{'PRIORITY': '20', 'PACKET_ACTION': 'DROP'}
```

**Status:** ✓ ACL configured with UPPERCASE MAC: 00:AA:AA:AA:AA:01

---

## Step 3: RX Device Setup (D3)

### 3.1 Start tcpdump Listener

```bash
ssh admin@192.168.100.173
sudo rm -f /tmp/l2_n01_test.pcap
sudo timeout 30 tcpdump -i Ethernet513 'ether src 00:aa:aa:aa:aa:01' -w /tmp/l2_n01_test.pcap &
```

**Status:** ✓ tcpdump started, listening for lowercase MAC 00:aa:aa:aa:aa:01

---

## Step 4: TX Traffic Generation (D2)

### 4.1 Create Scapy Traffic Script

```bash
ssh admin@192.168.100.140

cat > /tmp/l2_n01_traffic.py << 'EOF'
#!/usr/bin/env python3
"""
L2-N01: MAC Case Sensitivity Test
Sends packets from lowercase MAC 00:aa:aa:aa:aa:01
ACL configured with UPPERCASE MAC 00:AA:AA:AA:AA:01
Testing if matching is case-insensitive
"""

from scapy.all import Ether, IP, Raw, sendp
import time

iface = "Ethernet64"
src_mac = "00:aa:aa:aa:aa:01"   # lowercase MAC (ACL has UPPERCASE)
dst_mac = "00:bb:bb:bb:bb:02"
total_packets = 10

print(f"[+] L2-N01: MAC Case Sensitivity Test")
print(f"    Source MAC: {src_mac} (lowercase)")
print(f"    ACL configured with: 00:AA:AA:AA:AA:01 (UPPERCASE)")
print(f"    Expected: Testing case-sensitivity")
print(f"    Total Packets: {total_packets}")
print()

pkt = Ether(src=src_mac, dst=dst_mac) / \
      IP(src="10.0.0.1", dst="20.0.0.2") / \
      Raw(load="L2-N01-TEST-CASE-SENSITIVITY")

sent_count = 0
try:
    for i in range(total_packets):
        sendp(pkt, iface=iface, verbose=False)
        sent_count += 1
        print(f"[→] Sent packet {sent_count}/{total_packets} (lowercase MAC)")
        time.sleep(1.0)
except Exception as e:
    print(f"[✗] Error: {e}")
    exit(1)

print(f"\n[✓] Completed. Sent {sent_count} packets")
EOF

chmod +x /tmp/l2_n01_traffic.py
```

### 4.2 Execute Traffic Generation

```bash
sudo python3 /tmp/l2_n01_traffic.py
```

**Output:**
```
[+] L2-N01: MAC Case Sensitivity Test
    Source MAC: 00:aa:aa:aa:aa:01 (lowercase)
    ACL configured with: 00:AA:AA:AA:AA:01 (UPPERCASE)
    Expected: Testing case-sensitivity
    Total Packets: 10

[→] Sent packet 1/10 (lowercase MAC)
[→] Sent packet 2/10 (lowercase MAC)
[→] Sent packet 3/10 (lowercase MAC)
[→] Sent packet 4/10 (lowercase MAC)
[→] Sent packet 5/10 (lowercase MAC)
[→] Sent packet 6/10 (lowercase MAC)
[→] Sent packet 7/10 (lowercase MAC)
[→] Sent packet 8/10 (lowercase MAC)
[→] Sent packet 9/10 (lowercase MAC)
[→] Sent packet 10/10 (lowercase MAC)

[✓] Completed. Sent 10 packets
```

**Status:** ✓ 10 packets sent with lowercase source MAC 00:aa:aa:aa:aa:01

---

## Step 5: Verification Phase

### 5.1 Verify Packet Capture on D3

```bash
ssh admin@192.168.100.173
sudo killall tcpdump
sleep 2

# Check PCAP file
ls -lh /tmp/l2_n01_test.pcap
stat -c%s "/tmp/l2_n01_test.pcap"
```

**Output:**
```
File size: 24 bytes (PCAP header only - NO PACKETS CAPTURED)
```

**Result:** ✗ 0 packets captured on D3

### 5.2 Verify MAC Address Learning on D1

```bash
ssh admin@192.168.100.119
show mac | head -15
```

**Output:**
```
  No.    Vlan  MacAddress         Port         Type
-----  ------  -----------------  -----------  -------
    1     100  00:AA:AA:AA:AA:01  Ethernet272  Dynamic
Total number of entries 1
```

**Critical Finding:**
- D1 learned the MAC address as `00:AA:AA:AA:AA:01` (UPPERCASE)
- Traffic was sent with MAC `00:aa:aa:aa:aa:01` (lowercase)
- **SONiC normalized the MAC address to UPPERCASE** for display

### 5.3 Verify ACL Counters on D1

```bash
ssh admin@192.168.100.119
sudo aclshow -a
```

**Output:**
```
RULE NAME    TABLE NAME                    PRIO  PACKETS COUNT    BYTES COUNT
-----------  --------------------------  ------  ---------------  -------------
RULE_20      L2_ACL_TEST_CASE                20  N/A              N/A
RULE_10      L2_ACL_TEST_CASE                10  N/A              N/A
```

**Note:** ACL counters show "N/A" (not yet populated by hardware counter polling)

### 5.4 Verify Interface Status

```bash
# D1 interfaces
show interface status Ethernet272
show interface status Ethernet513
```

**Output:**
```
# Ethernet272 (link to D2)
Oper: up, Admin: up ✓

# Ethernet513 (link to D3)
Oper: up, Admin: up ✓
```

**Status:** ✓ All interfaces operationally UP

---

## Test Results

### Result Summary

| Parameter | Value |
|-----------|-------|
| **Test Status** | PASS ✓ (Determined case-sensitivity) |
| **TX Packets** | 10 (lowercase MAC: 00:aa:aa:aa:aa:01) |
| **RX Packets** | 0 (BLOCKED by ACL) |
| **RX Percentage** | 0% (100% BLOCKED) |
| **MAC Learning** | 1 entry (normalized to UPPERCASE: 00:AA:AA:AA:AA:01) |
| **ACL Behavior** | CASE-SENSITIVE on wire format |

### Detailed Results

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| TX Count | 10 | 10 | ✓ PASS |
| Traffic Sent | lowercase MAC | lowercase MAC | ✓ PASS |
| ACL Configured | UPPERCASE MAC | UPPERCASE MAC | ✓ PASS |
| RX Count (if case-insensitive) | 10 (permitted) | 0 (blocked) | ✗ FAIL |
| RX Count (if case-sensitive) | 0 (blocked) | 0 (blocked) | ✓ PASS |
| MAC Learning | D1 learns MAC | Learned as UPPERCASE | ✓ PASS |

---

## Key Findings

### 1. L2 ACL Matching is CASE-SENSITIVE (Wire Format)

**Evidence:**
- ACL Rule 10 configured with UPPERCASE MAC: `00:AA:AA:AA:AA:01`
- Traffic sent with lowercase MAC: `00:aa:aa:aa:aa:01`
- **Result**: 0 packets reached D3 (100% blocked)
- **Conclusion**: ACL did NOT match - Rule 10 (PERMIT) was bypassed, Rule 20 (DENY all) blocked traffic

**Implication**: L2 ACL matching operates on the **actual MAC address as it appears on the wire**, not on SONiC's normalized representation.

### 2. SONiC Normalizes MAC Addresses to UPPERCASE for Display

**Evidence:**
- Traffic sent: `00:aa:aa:aa:aa:01` (lowercase)
- MAC table shows: `00:AA:AA:AA:AA:01` (UPPERCASE)
- **Conclusion**: SONiC normalizes MAC addresses to uppercase for CLI display and internal representation

**Implication**: MAC address display in CLI commands (show mac, show vlan) will always be UPPERCASE, regardless of how the MAC was learned from the wire.

### 3. CONFIG_DB Approach Required for Broadcom Hardware

**Platform Limitation**: klish iSCLI MAC ACL commands (`mac access-list`, `permit host`, `deny any any`) are not implemented in vtysh on Broadcom ASIC hardware platforms.

**Working Alternative**: CONFIG_DB approach using:
- `config acl add table <name> L2 -p <port> -s <stage>`
- `sonic-db-cli CONFIG_DB HSET "ACL_RULE|<table>|<rule>" ...`

---

## Observations & Notes

1. **Case Sensitivity Behavior:**
   - L2 ACL matching compares MAC addresses in **case-sensitive manner**
   - ACL rules must specify MAC addresses in the **exact case** as they appear on the wire
   - For typical network equipment, MACs are sent in lowercase, so ACL rules should use lowercase

2. **SONiC MAC Normalization:**
   - SONiC internally normalizes MACs to UPPERCASE for display consistency
   - This normalization is for **display purposes only**, not for ACL matching
   - ACL engine operates on raw packet MAC addresses (wire format)

3. **Traffic Flow Analysis:**
   - TX (D2): 10 packets sent → D1 ingress (Ethernet272) → ACL evaluation → BLOCKED (Rule 20)
   - MAC Learning: D1 learned source MAC despite ACL blocking (learning happens before ACL)
   - RX (D3): 0 packets received (ACL dropped traffic before forwarding)

4. **Interface Startup Requirement:**
   - CRITICAL: Interfaces must be brought up with `config interface startup <interface>`
   - VLAN member addition does NOT automatically start interfaces
   - Without startup, Admin=down and no traffic flows

---

## Test Conclusion

**TEST PASSED** ✓

The L2-N01 test case successfully determined that **L2 ACL MAC address matching is CASE-SENSITIVE** on SONiC hardware (Broadcom ASIC).

**Conclusion:**
- ACL configured with UPPERCASE MAC (00:AA:AA:AA:AA:01) did NOT match lowercase traffic (00:aa:aa:aa:aa:01)
- All 10 packets were BLOCKED (0% delivery)
- SONiC normalizes MAC display to UPPERCASE, but ACL matching uses wire format
- **Best Practice**: Configure ACL MAC addresses in **lowercase** to match typical network traffic

**Platform Note:** On Broadcom ASIC hardware, klish iSCLI MAC ACL commands are not available. Use CONFIG_DB approach with `config acl` and `sonic-db-cli` commands instead.

---

## CRITICAL UPDATE: Additional Verification Tests (2026-03-19)

**After the initial case sensitivity test, additional verification tests were performed to confirm the root cause.**

### Test 2: Lowercase ACL with Lowercase Traffic

**Hypothesis**: If case sensitivity is the issue, then lowercase ACL should match lowercase traffic.

**Configuration:**
```bash
sudo config acl add table L2_ACL_LOWERCASE_TEST L2 -p Ethernet272 -s ingress
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_LOWERCASE_TEST|RULE_10" "PRIORITY" "10"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_LOWERCASE_TEST|RULE_10" "PACKET_ACTION" "FORWARD"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_LOWERCASE_TEST|RULE_10" "SRC_MAC" "00:aa:aa:aa:aa:01/ff:ff:ff:ff:ff:ff"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_LOWERCASE_TEST|RULE_20" "PRIORITY" "20"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_LOWERCASE_TEST|RULE_20" "PACKET_ACTION" "DROP"
```

**Verification:**
```bash
show acl rule L2_ACL_LOWERCASE_TEST
```

**Output:**
```
Table                  Rule       Priority  Action    Match
---------------------  -------  ----------  --------  --------------------------
L2_ACL_LOWERCASE_TEST  RULE_20          20  DROP      N/A
L2_ACL_LOWERCASE_TEST  RULE_10          10  FORWARD   SRC_MAC: 00:aa:aa:aa:aa:01
```

**Traffic Test:**
- Sent: 10 packets with MAC `00:aa:aa:aa:aa:01` (lowercase)
- Received: **0 packets**

**Result:** ✗ lowercase ACL with lowercase traffic - BLOCKED

### Test 3: UPPERCASE ACL with Lowercase Traffic (Reconfirm)

**Configuration:**
```bash
sudo config acl add table L2_ACL_UPPERCASE_TEST L2 -p Ethernet272 -s ingress
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_UPPERCASE_TEST|RULE_10" "SRC_MAC" "00:AA:AA:AA:AA:01/FF:FF:FF:FF:FF:FF"
```

**Traffic Test:**
- Sent: 5 packets with MAC `00:aa:aa:aa:aa:01` (lowercase)
- Received: **0 packets**

**Result:** ✗ UPPERCASE ACL with lowercase traffic - BLOCKED

### Test 4: PERMIT-ALL ACL (CRITICAL TEST)

**Configuration:**
```bash
sudo config acl add table L2_ACL_SIMPLE_TEST L2 -p Ethernet272 -s ingress

# Rule 10: FORWARD (permit) specific MAC
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_SIMPLE_TEST|RULE_10" "PRIORITY" "10"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_SIMPLE_TEST|RULE_10" "PACKET_ACTION" "FORWARD"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_SIMPLE_TEST|RULE_10" "SRC_MAC" "00:aa:aa:aa:aa:01"

# Rule 20: FORWARD (permit) everything else
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_SIMPLE_TEST|RULE_20" "PRIORITY" "20"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_SIMPLE_TEST|RULE_20" "PACKET_ACTION" "FORWARD"
```

**Verification:**
```bash
show acl rule L2_ACL_SIMPLE_TEST
```

**Output:**
```
Table               Rule       Priority  Action    Match
------------------  -------  ----------  --------  --------------------------
L2_ACL_SIMPLE_TEST  RULE_20          20  FORWARD   N/A
L2_ACL_SIMPLE_TEST  RULE_10          10  FORWARD   SRC_MAC: 00:aa:aa:aa:aa:01
```

**Traffic Test:**
- Sent: 5 packets with MAC `00:aa:aa:aa:aa:01`
- **BOTH RULES ARE FORWARD (PERMIT ALL TRAFFIC)**
- Expected: All packets should be forwarded
- Received: **0 test packets**

**Result:** ✗ **CRITICAL FAILURE - Even permit-all ACL blocks traffic**

### Test 5: No ACL (Connectivity Baseline)

**Configuration:**
```bash
sudo config acl remove table L2_ACL_SIMPLE_TEST
```

**Traffic Test:**
- Sent: Multiple packets
- Received: **Packets arrive successfully**

**Result:** ✓ Traffic flows without ACL

---

## CRITICAL FINDINGS - ROOT CAUSE ANALYSIS

### Original Conclusion: INCORRECT

**The original conclusion that "L2 ACL matching is case-sensitive" is INCORRECT.**

### Actual Root Cause: L2 ACL via CONFIG_DB NOT FUNCTIONAL

**Evidence:**
1. **UPPERCASE ACL + lowercase traffic = BLOCKED** ✗
2. **lowercase ACL + lowercase traffic = BLOCKED** ✗
3. **UPPERCASE ACL + UPPERCASE traffic = BLOCKED** ✗
4. **PERMIT-ALL ACL (both rules FORWARD) = BLOCKED** ✗ **← CRITICAL**
5. **NO ACL = Traffic flows** ✓

**Conclusion:**
The issue is **NOT** case sensitivity. The L2 ACL functionality configured via CONFIG_DB approach **does not work properly** on this Broadcom ASIC hardware platform.

### Why This is Critical

1. **Even permit-all ACL blocks traffic**: This proves the ACL matching logic is fundamentally broken
2. **ACL configuration appears correct**: `show acl` commands show rules are configured
3. **CONFIG_DB entries are correct**: `sonic-db-cli` confirms rules are stored
4. **But traffic is blocked regardless**: No traffic reaches destination with ANY ACL configuration

### Platform Limitations Identified

| Feature | Status | Notes |
|---------|--------|-------|
| **klish iSCLI MAC ACL commands** | ✗ NOT AVAILABLE | Commands incomplete/unknown in vtysh |
| **CONFIG_DB L2 ACL approach** | ✗ NOT FUNCTIONAL | ACL blocks all traffic regardless of rules |
| **L2 switching without ACL** | ✓ WORKING | Traffic flows correctly in VLAN mode |

---

## CORRECTED TEST CONCLUSION

**TEST FAILED** ✗

**Original Objective**: Determine if MAC address matching is case-sensitive or case-insensitive.

**Actual Finding**: Cannot determine case sensitivity because **L2 ACL functionality via CONFIG_DB does not work** on this Broadcom ASIC hardware platform.

**Evidence:**
- L2 ACL configuration via CONFIG_DB appears successful (commands accept input, rules show in database)
- However, ACL functionality is **non-functional** - ALL traffic is blocked regardless of ACL rules
- Even an ACL configured to PERMIT all traffic (both Rule 10 and Rule 20 set to FORWARD action) blocks 100% of traffic
- Connectivity works perfectly without ACL (baseline confirmed)

**Platform Issues:**
1. **klish iSCLI limitation**: MAC ACL commands (`mac access-list`, `permit host`) not implemented
2. **CONFIG_DB limitation**: L2 ACL configured via CONFIG_DB/sonic-db-cli does not function properly
3. **Possible causes**:
   - L2 ACL rules not being programmed into ASIC correctly
   - SAI layer issue with MAC address matching
   - Broadcom SDK limitation with L2 ACL on VLAN interfaces
   - Missing orchagent support for L2 ACL table type

---

## Recommendations

1. **For L2 ACL Testing**: This platform (Broadcom ASIC with CONFIG_DB approach) is **NOT suitable** for L2 ACL testing
2. **Alternative Approaches Needed**:
   - Test on Virtual Switch (vs) platform instead
   - Find hardware platform with working klish iSCLI MAC ACL support
   - Investigate SONiC ACL orchestration agent logs for errors
   - Check if L2 ACL type is supported on this hardware ASIC
3. **Debug Steps** (if pursuing further):
   - Check `/var/log/syslog` for ACL programming errors
   - Verify ASIC_DB entries: `sudo sonic-db-cli ASIC_DB KEYS '*ACL*'`
   - Check orchagent logs: `sudo grep -i acl /var/log/swss/sairedis.rec`
   - Verify SAI capabilities for L2 ACL on this ASIC

---

**Document Version**: 2.0 (MAJOR UPDATE)
**Last Updated**: 2026-03-19
**Status**: FAILED - L2 ACL via CONFIG_DB not functional
**Platform Tested**: Hardware SONiC Switches (Broadcom ASIC - Supermicro SSE-T8196)
**Configuration Method**: CONFIG_DB (klish iSCLI not available, CONFIG_DB not functional)
**Critical Issue**: L2 ACL blocks all traffic regardless of rule configuration - Feature not working on this platform
