# L2-08: ACL Rule Priority - Permit Before Deny - Hardware Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-08 |
| **Description** | ACL rule priority evaluation - permit rule before deny rule for same traffic |
| **Category** | Functional |
| **Expected Outcome** | Traffic permitted (earlier permit rule takes precedence over later deny) |
| **Platform** | Hardware (Broadcom ASIC) |
| **Date** | 2026-03-19 |
| **Tester** | AI Assistant |

---

## Topology Used

```
┌────────────────┐                    ┌────────────────┐                    ┌────────────────┐
│     DUT2       │                    │     DUT1       │                    │     DUT3       │
│  (TX Traffic   │                    │  (ACL Device)  │                    │  (RX Receiver) │
│   Generator)   │                    │                │                    │                │
│ 192.168.100.140│                    │ 192.168.100.119│                    │ 192.168.100.173│
│                │                    │                │                    │                │
│ Ethernet64 ────┼────────────────────┼──► Ethernet272 │                    │                │
│                │  (L2 VLAN 100)     │  (ACL ingress) │                    │                │
│                │                    │                │                    │                │
│                │                    │  Ethernet513───┼────────────────────┼──► Ethernet513 │
│                │                    │  (egress)      │  (L2 VLAN 100)     │                │
└────────────────┘                    └────────────────┘                    └────────────────┘
                                                │
                                      L2 ACL Rules (Ingress)
```

---

## Test Objective

Validate that L2 ACL rules are evaluated in priority order:
- **RULE_10** (Priority 10): PERMIT traffic from source MAC 00:aa:aa:aa:aa:01
- **RULE_20** (Priority 20): DENY all other traffic

Expected behavior: Traffic matching RULE_10 should be permitted without evaluating RULE_20 (first match wins).

---

## Step 1: Testbed Pre-Configuration

### 1.1 VLAN Configuration Status

**D1 (ACL Device):**
```
+-----------+--------------+-------------+----------------+-------------+-----------------------+
|   VLAN ID | IP Address   | Ports       | Port Tagging   | Proxy ARP   | DHCP Helper Address   |
+===========+==============+=============+================+=============+=======================+
|       100 |              | Ethernet272 | untagged       | disabled    |                       |
|           |              | Ethernet513 | untagged       |             |                       |
+-----------+--------------+-------------+----------------+-------------+-----------------------+
```

**D2 (TX Generator):**
```
+-----------+--------------+------------+----------------+-----------------------+-------------+
|   VLAN ID | IP Address   | Ports      | Port Tagging   | DHCP Helper Address   | AutoState   |
+===========+==============+============+================+=======================+=============+
|       100 |              | Ethernet64 | untagged       |                       | enable      |
+-----------+--------------+------------+----------------+-----------------------+-------------+
```

**D3 (RX Receiver):**
```
+-----------+--------------+-------------+----------------+-------------+-----------------------+
|   VLAN ID | IP Address   | Ports       | Port Tagging   | Proxy ARP   | DHCP Helper Address   |
+===========+==============+=============+================+=============+=======================+
|       100 |              | Ethernet513 | untagged       | disabled    |                       |
+-----------+--------------+-------------+----------------+-------------+-----------------------+
```

### 1.2 Interface Status

| Device | Interface | Vlan | Oper | Admin |
|--------|-----------|------|------|-------|
| D1 | Ethernet272 | trunk | **up** | up |
| D1 | Ethernet513 | trunk | **up** | up |
| D2 | Ethernet64 | trunk | **up** | up |
| D3 | Ethernet513 | trunk | **up** | up |

### 1.3 MAC Address Learning (D1)

```
  No.    Vlan  MacAddress         Port         Type
-----  ------  -----------------  -----------  -------
    1     100  00:AA:AA:AA:AA:01  Ethernet272  Dynamic
    2     100  90:5A:08:AF:9C:F5  Ethernet513  Dynamic
Total number of entries 2
```

**Note:** 90:5A:08:AF:9C:F5 is D3's Ethernet513 MAC address.

---

## Step 2: ACL Configuration on DUT

### 2.1 klish iSCLI Commands (Attempted)

**Note:** klish iSCLI MAC ACL commands documented in `/home/hp_test/Athira/acl_iscli_commands.md` are **not available** in vtysh on this hardware platform.

Attempted commands:
```bash
ssh admin@192.168.100.119

sudo vtysh << 'EOFKLISH'
configure terminal
mac access-list L2_ACL_TEST_PRIORITY
seq 10 permit host 00:aa:aa:aa:aa:01 any
seq 20 deny any any
exit
interface Ethernet 272
mac access-group L2_ACL_TEST_PRIORITY in
exit
end
EOFKLISH
```

**Error Output:**
```
sonic(config)# mac access-list L2_ACL_TEST_PRIORITY
% Command incomplete: mac access-list L2_ACL_TEST_PRIORITY
sonic(config)# seq 10 permit host 00:aa:aa:aa:aa:01 any
% Unknown command: seq 10 permit host 00:aa:aa:aa:aa:01 any
```

**Root Cause:** The klish iSCLI MAC ACL syntax is not implemented in the vtysh CLI interface on this Broadcom ASIC hardware platform.

### 2.2 Alternative: CONFIG_DB Approach (Successful)

**Create L2 ACL Table:**
```bash
ssh admin@192.168.100.119

# Create L2 ACL table and bind to Ethernet272 ingress
sudo config acl add table L2_ACL_TEST_PRIORITY L2 -p Ethernet272 -s ingress
```

**Add RULE_10 (PERMIT specific source MAC):**
```bash
# Priority 10 - evaluated FIRST (higher priority)
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_PRIORITY|RULE_10" "PRIORITY" "10"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_PRIORITY|RULE_10" "PACKET_ACTION" "FORWARD"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_PRIORITY|RULE_10" "SRC_MAC" "00:aa:aa:aa:aa:01/FF:FF:FF:FF:FF:FF"
```

**Add RULE_20 (DENY all other traffic):**
```bash
# Priority 20 - evaluated SECOND (lower priority)
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_PRIORITY|RULE_20" "PRIORITY" "20"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_PRIORITY|RULE_20" "PACKET_ACTION" "DROP"
```

**Save Configuration:**
```bash
sudo config save -y
```

### 2.3 Verify ACL Configuration

```bash
# Verify ACL Table
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_TABLE|L2_ACL_TEST_PRIORITY"
```

**Output:**
```python
{'policy_desc': 'L2_ACL_TEST_PRIORITY', 'ports@': 'Ethernet272', 'stage': 'ingress', 'type': 'L2'}
```

```bash
# Verify RULE_10
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_PRIORITY|RULE_10"
```

**Output:**
```python
{'PRIORITY': '10', 'PACKET_ACTION': 'FORWARD', 'SRC_MAC': '00:aa:aa:aa:aa:01/FF:FF:FF:FF:FF:FF'}
```

```bash
# Verify RULE_20
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_PRIORITY|RULE_20"
```

**Output:**
```python
{'PRIORITY': '20', 'PACKET_ACTION': 'DROP'}
```

---

## Step 3: Traffic Generation Setup

### 3.1 Create Scapy Traffic Script (D2)

```bash
ssh admin@192.168.100.140

cat > /tmp/l2_08_traffic_v2.py << 'EOF'
#!/usr/bin/env python3
"""
L2-08: ACL Rule Priority Test (Version 2 - with correct destination MAC)
Sends packets from MAC 00:AA:AA:AA:AA:01 to D3's actual MAC
Rule 10 (permit) should match first, allowing traffic despite Rule 20 (deny any)
"""

from scapy.all import Ether, IP, Raw, sendp
import time

iface = "Ethernet64"
src_mac = "00:aa:aa:aa:aa:01"   # Matches Rule 10 (permit)
dst_mac = "90:5a:08:af:9c:f5"   # D3's Ethernet513 actual MAC
total_packets = 10

print(f"[+] L2-08: ACL Rule Priority Test (v2)")
print(f"    Source MAC: {src_mac} (matches Rule 10: PERMIT)")
print(f"    Destination MAC: {dst_mac} (D3's Ethernet513)")
print(f"    Expected: PERMITTED (Rule 10 evaluated before Rule 20)")
print(f"    Total Packets: {total_packets}")
print()

pkt = Ether(src=src_mac, dst=dst_mac) / \
      IP(src="10.0.0.1", dst="20.0.0.2") / \
      Raw(load="L2-08-TEST-PRIORITY-PERMIT-V2")

sent_count = 0
try:
    for i in range(total_packets):
        sendp(pkt, iface=iface, verbose=False)
        sent_count += 1
        print(f"[→] Sent packet {sent_count}/{total_packets} (Rule 10 should permit)")
        time.sleep(1.0)
except Exception as e:
    print(f"[✗] Error: {e}")
    exit(1)

print(f"\n[✓] Completed. Sent {sent_count} packets to D3's real MAC address")
EOF

chmod +x /tmp/l2_08_traffic_v2.py
```

---

## Step 4: Test Execution

### 4.1 Start Packet Capture on D3

```bash
ssh admin@192.168.100.173

sudo nohup tcpdump -i Ethernet513 'ether src 00:aa:aa:aa:aa:01' -w /tmp/l2_08_test.pcap -c 20 > /dev/null 2>&1 &
```

### 4.2 Execute Traffic Generation from D2

```bash
ssh admin@192.168.100.140

sudo python3 /tmp/l2_08_traffic_v2.py
```

**Execution Output:**
```
[+] L2-08: ACL Rule Priority Test (v2)
    Source MAC: 00:aa:aa:aa:aa:01 (matches Rule 10: PERMIT)
    Destination MAC: 90:5a:08:af:9c:f5 (D3's Ethernet513)
    Expected: PERMITTED (Rule 10 evaluated before Rule 20)
    Total Packets: 10

[→] Sent packet 1/10 (Rule 10 should permit)
[→] Sent packet 2/10 (Rule 10 should permit)
[→] Sent packet 3/10 (Rule 10 should permit)
[→] Sent packet 4/10 (Rule 10 should permit)
[→] Sent packet 5/10 (Rule 10 should permit)
[→] Sent packet 6/10 (Rule 10 should permit)
[→] Sent packet 7/10 (Rule 10 should permit)
[→] Sent packet 8/10 (Rule 10 should permit)
[→] Sent packet 9/10 (Rule 10 should permit)
[→] Sent packet 10/10 (Rule 10 should permit)

[✓] Completed. Sent 10 packets to D3's real MAC address
```

### 4.3 Verify Packet Reception on D3

```bash
ssh admin@192.168.100.173

sudo killall tcpdump
sleep 2

# Analyze captured packets
sudo python3 -c "from scapy.all import rdpcap; packets = rdpcap('/tmp/l2_08_test.pcap'); print(f'Captured: {len(packets)} packets')"
```

**Result:**
```
Captured: 0 packets
```

---

## Step 5: Troubleshooting and Root Cause Analysis

### 5.1 Test Without ACL

To determine if the ACL was blocking packets, the ACL was temporarily removed:

```bash
ssh admin@192.168.100.119
sudo config acl remove table L2_ACL_TEST_PRIORITY
```

Test repeated with same traffic script:

**Result:** Still 0 packets captured on D3.

**Conclusion:** The ACL is **NOT** the cause of packet loss.

### 5.2 Check Ingress Traffic on D1

Packet capture on D1's Ethernet272 (ingress from D2):

```bash
ssh admin@192.168.100.119
sudo tcpdump -i Ethernet272 'ether src 00:aa:aa:aa:aa:01' -w /tmp/d1_ingress_test.pcap -c 20
```

Send traffic from D2 again.

**Result:**
```
Captured on D1 Ethernet272: 0 packets
```

**Conclusion:** Packets are **NOT reaching D1 from D2**, despite D2's Scapy script reporting successful transmission.

### 5.3 Root Cause

**Hardware connectivity issue between D2:Ethernet64 and D1:Ethernet272.**

Despite both interfaces showing operational status as "up":
- D2:Ethernet64 (Oper: up, Admin: up)
- D1:Ethernet272 (Oper: up, Admin: up)

Traffic is not flowing over this physical link. This is the same class of issue encountered in test L2-07, where Ethernet513 link between D1 and D3 exhibited similar behavior.

### 5.4 Additional Observations

1. **Interface Counters (D1:Ethernet272):**
   - RX_OK: 118 packets (accumulated over time, not test-specific)
   - RX_DRP: 22 packets dropped
   - TX_OK: 123 packets

2. **Interface Counters (D2:Ethernet64):**
   - TX_OK: 117 packets (accumulated over time, not test-specific)
   - RX_OK: 109 packets

3. **MAC Learning:** Both source and destination MACs were learned correctly in VLAN 100 on D1.

4. **VLAN Configuration:** All devices correctly configured with VLAN 100 untagged members.

---

## Test Results

### Result Summary

| Parameter | Value |
|-----------|-------|
| **Test Status** | INCONCLUSIVE (Hardware Connectivity Issue) |
| **TX Packets (D2)** | 10 (claimed by Scapy) |
| **RX Packets (D1 Ethernet272)** | 0 (tcpdump capture) |
| **RX Packets (D3 Ethernet513)** | 0 (tcpdump capture) |
| **RX Percentage** | 0% |
| **ACL Configuration** | ✓ Correct (CONFIG_DB approach) |
| **VLAN Configuration** | ✓ Correct (untagged VLAN 100) |
| **Pass Criteria** | ✗ Cannot verify due to connectivity issue |

### Detailed Results

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| TX Count (D2) | 10 | 10 (Scapy) | ✓ |
| RX Count (D1 ingress) | 10 | **0** | ✗ **FAIL** |
| RX Count (D3 egress) | 10 | **0** | ✗ **FAIL** |
| ACL Configuration | Valid CONFIG_DB | Valid CONFIG_DB | ✓ PASS |
| RULE_10 (Permit) | Configured | Configured | ✓ PASS |
| RULE_20 (Deny) | Configured | Configured | ✓ PASS |
| klish iSCLI Support | Available | **Not Available** | ✗ Platform Limitation |

---

## Key Findings

### 1. klish iSCLI MAC ACL Commands Not Available

The klish iSCLI commands documented in `/home/hp_test/Athira/acl_iscli_commands.md` for MAC ACLs are **not available** in vtysh on this Broadcom ASIC hardware platform:

```bash
# These commands do NOT work:
mac access-list L2_ACL_TEST_PRIORITY
seq 10 permit host 00:aa:aa:aa:aa:01 any
seq 20 deny any any
```

**Error:** `% Unknown command`

**Workaround:** Use SONiC CONFIG_DB approach with `sonic-db-cli` and `config acl` commands, which successfully created and applied L2 ACL rules.

### 2. Hardware Connectivity Issue

**Critical Issue:** Physical layer 2 connectivity is not working reliably on this hardware testbed despite all interfaces showing operational status as "up".

**Evidence:**
- Packets sent from D2:Ethernet64 (confirmed by Scapy)
- Packets **NOT received** on D1:Ethernet272 (confirmed by tcpdump)
- Link status shows "up" on both ends
- VLAN configuration correct on all devices

**Impact:** Unable to validate ACL rule priority evaluation functionality.

### 3. ACL Configuration Validation

The ACL was correctly configured using CONFIG_DB approach:

```python
# ACL Table
{'policy_desc': 'L2_ACL_TEST_PRIORITY',
 'ports@': 'Ethernet272',
 'stage': 'ingress',
 'type': 'L2'}

# RULE_10 (Priority 10 - Higher priority, evaluated first)
{'PRIORITY': '10',
 'PACKET_ACTION': 'FORWARD',
 'SRC_MAC': '00:aa:aa:aa:aa:01/FF:FF:FF:FF:FF:FF'}

# RULE_20 (Priority 20 - Lower priority, evaluated second)
{'PRIORITY': '20',
 'PACKET_ACTION': 'DROP'}
```

The ACL configuration demonstrates the correct priority-based rule ordering:
- Lower priority number (10) = Higher precedence (evaluated first)
- Higher priority number (20) = Lower precedence (evaluated second)

---

## Test Conclusion

**TEST STATUS: INCONCLUSIVE**

The L2-08 test case **could not be completed** due to hardware connectivity issues between D2 and D1. While the ACL configuration was successfully created using the CONFIG_DB approach (since klish iSCLI commands are not available on this platform), the underlying network connectivity problem prevented validation of ACL rule priority evaluation.

**Configuration Achievements:**
✓ Successfully configured L2 ACL with priority-based rules using CONFIG_DB approach
✓ VLAN 100 correctly configured as untagged on all devices
✓ All interfaces showing operational status as "up"
✓ MAC address learning working correctly on D1

**Blocking Issues:**
✗ Packets not reaching D1 from D2 despite "up" link status
✗ klish iSCLI MAC ACL commands not available on this hardware platform
✗ Similar connectivity issue as observed in L2-07 test

**Recommendations:**
1. **Hardware testbed validation:** Verify physical cabling and port mappings between devices
2. **Alternative CLI investigation:** Document CONFIG_DB approach as the standard method for L2 ACL configuration on Broadcom ASIC platforms
3. **L3 routing mode:** Consider restoring testbed to L3 routing mode using the restoration script (`testbeds/restore_hw_testbed_l3.sh`)
4. **Future testing:** Resolve physical connectivity issues before attempting further L2 ACL tests

---

## Platform-Specific Notes

### klish iSCLI vs CONFIG_DB

| Feature | klish iSCLI | CONFIG_DB Approach |
|---------|-------------|-------------------|
| **MAC ACL Creation** | ❌ Not Available | ✅ Available |
| **Rule Configuration** | ❌ Not Available | ✅ Available |
| **Interface Binding** | ❌ Not Available | ✅ Available |
| **Rule Priority** | ❌ Not Available | ✅ Supported (PRIORITY field) |
| **Verification** | N/A | ✅ sonic-db-cli HGETALL |

**Platform:** Supermicro SSE-T8196 (Broadcom ASIC)
**SONiC Version:** (as detected on hardware)

---

## Cleanup

```bash
# Remove test files
ssh admin@192.168.100.173
sudo rm -f /tmp/l2_08_test.pcap /tmp/l2_08_test_no_acl.pcap

ssh admin@192.168.100.140
sudo rm -f /tmp/l2_08_traffic.py /tmp/l2_08_traffic_v2.py

ssh admin@192.168.100.119
sudo rm -f /tmp/d1_ingress_test.pcap

# ACL already removed during troubleshooting
```

---

**Document Version**: 1.0
**Last Updated**: 2026-03-19
**Status**: Inconclusive - Hardware Connectivity Issue
**Platform Tested**: Hardware (Broadcom ASIC)
**Next Steps**: Restore testbed to L3 routing mode
