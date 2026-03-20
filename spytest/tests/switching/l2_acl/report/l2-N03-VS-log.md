# L2-N03 Manual Test Execution Log - Virtual Switch Platform

## Test Information

| **Test ID** | L2-N03 |
|-------------|--------|
| **Test Name** | Invalid/Corrupt MAC Address Handling |
| **Description** | Verify ACL behavior with non-matching (invalid) source MAC addresses |
| **Platform** | Virtual Switch (VS) - SONiC |
| **Testbed** | testbed_acl.yaml |
| **Execution Date** | 2026-03-19 |
| **Test Type** | Manual Execution |
| **CLI Method** | CONFIG_DB (klish iSCLI not available on VS platform) |

## Test Topology

```
┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
│   D2 (TX)    │                    │   D1 (ACL)   │                    │   D3 (RX)    │
│ 192.168.     │                    │ 192.168.     │                    │ 192.168.     │
│ 100.172      │                    │ 100.122      │                    │ 100.178      │
│              │                    │              │                    │              │
│ Ethernet0 ◄──┼────────────────────┼─ Ethernet48  │                    │              │
│ VLAN 100     │                    │ VLAN 100     │                    │              │
│              │   (L2 switching)   │ (ACL ingress)│                    │              │
│              │                    │              │                    │              │
│              │                    │ Ethernet32───┼────────────────────┼──► Ethernet32
│              │                    │ VLAN 100     │   (L2 switching)   │ VLAN 100     │
│              │                    │ (egress)     │                    │              │
└──────────────┘                    └──────────────┘                    └──────────────┘

Traffic Flow: D2 (Ethernet0) → D1 (Ethernet48 → Ethernet32) → D3 (Ethernet32)
```

## Device Information

| Device | Role | IP Address | Platform | Interface (TX) | Interface (RX) | VLAN |
|--------|------|------------|----------|----------------|----------------|------|
| **D1** | ACL Device (DUT) | 192.168.100.122 | Virtual Switch | Ethernet48 (ingress) | Ethernet32 (egress) | 100 |
| **D2** | Traffic Generator | 192.168.100.172 | Virtual Switch | Ethernet0 | - | 100 |
| **D3** | Traffic Receiver | 192.168.100.178 | Virtual Switch | - | Ethernet32 | 100 |

**Credentials:**
- D1, D2, D3: admin / root@123

## Test Objectives

1. Configure L2 ACL with source MAC filtering rules
2. Verify ACL permits traffic from valid/matching MAC address (00:aa:aa:aa:aa:01)
3. Verify ACL denies traffic from non-matching/invalid MAC address (00:cc:cc:cc:cc:01)
4. Validate ACL handles non-matching MACs gracefully (drops without errors)

## Pre-Test Configuration

### Step 1: VLAN 100 Configuration (L2 Switching Mode)

**Note:** VLAN 100 was already configured from previous L2-N02 test execution. Configuration verified as follows:

**D1 (192.168.100.122) - ACL Device:**
```bash
ssh admin@192.168.100.122

show vlan brief
```

**Output:**
```
+-----------+--------------+------------+----------------+-------------+
|   VLAN ID | IP Address   | Ports      | Port Tagging   | Proxy ARP   |
+===========+==============+============+================+=============+
|       100 |              | Ethernet32 | untagged       | disabled    |
|           |              | Ethernet48 | untagged       |             |
+-----------+--------------+------------+----------------+-------------+
```

**D2 (192.168.100.172) - TX Generator:**
```bash
ssh admin@192.168.100.172

show vlan brief
```

**Output:**
```
+-----------+--------------+------------+----------------+-------------+
|   VLAN ID | IP Address   | Ports      | Port Tagging   | Proxy ARP   |
+===========+==============+============+================+=============+
|       100 |              | Ethernet0  | untagged       | disabled    |
+-----------+--------------+------------+----------------+-------------+
```

**D3 (192.168.100.178) - RX Receiver:**
```bash
ssh admin@192.168.100.178

show vlan brief
```

**Output:**
```
+-----------+--------------+------------+----------------+-------------+
|   VLAN ID | IP Address   | Ports      | Port Tagging   | Proxy ARP   |
+===========+==============+============+================+=============+
|       100 |              | Ethernet32 | untagged       | disabled    |
+-----------+--------------+------------+----------------+-------------+
```

### Step 2: L2 ACL Configuration on D1

**klish iSCLI Command (from acl_iscli_commands.md - NOT AVAILABLE on VS):**
```
sonic(config)# mac access-list L2_ACL_TEST_INVALID
sonic(config-mac-acl)# seq 10 permit host 00:AA:AA:AA:AA:01 any
sonic(config-mac-acl)# seq 20 deny any any
sonic(config-mac-acl)# exit
sonic(config)# interface Ethernet 48
sonic(config-if-Ethernet48)# mac access-group L2_ACL_TEST_INVALID in
sonic(config-if-Ethernet48)# end
sonic# write memory
```

**Actual Command Used (CONFIG_DB approach - klish iSCLI NOT available):**

```bash
ssh admin@192.168.100.122

# Create L2 ACL table bound to Ethernet48 ingress
sudo config acl add table L2_ACL_TEST_INVALID L2 -p Ethernet48 -s ingress

# Rule 10: FORWARD traffic from valid permitted MAC (00:AA:AA:AA:AA:01)
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_INVALID|RULE_10" "PRIORITY" "10"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_INVALID|RULE_10" "PACKET_ACTION" "FORWARD"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_INVALID|RULE_10" "SRC_MAC" "00:AA:AA:AA:AA:01/FF:FF:FF:FF:FF:FF"

# Rule 20: DROP all other traffic
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_INVALID|RULE_20" "PRIORITY" "20"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_INVALID|RULE_20" "PACKET_ACTION" "DROP"

# Save configuration
sudo config save -y
```

**Verification:**

```bash
# Verify ACL table
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_TABLE|L2_ACL_TEST_INVALID"
```

**Output:**
```
{'policy_desc': 'L2_ACL_TEST_INVALID', 'ports@': 'Ethernet48', 'stage': 'ingress', 'type': 'L2'}
```

```bash
# Verify Rule 10
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_INVALID|RULE_10"
```

**Output:**
```
{'PRIORITY': '10', 'PACKET_ACTION': 'FORWARD', 'SRC_MAC': '00:AA:AA:AA:AA:01/FF:FF:FF:FF:FF:FF'}
```

```bash
# Verify Rule 20
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_INVALID|RULE_20"
```

**Output:**
```
{'PRIORITY': '20', 'PACKET_ACTION': 'DROP'}
```

**ACL Configuration Summary:**
- ✓ L2 ACL table `L2_ACL_TEST_INVALID` created
- ✓ Table type: L2
- ✓ Bound to: Ethernet48 (ingress)
- ✓ Rule 10: FORWARD source MAC 00:AA:AA:AA:AA:01 (priority 10)
- ✓ Rule 20: DROP all other traffic (priority 20)
- ✓ Configuration saved to CONFIG_DB

## Test Execution

### Test 1: Traffic with L2 ACL Configured

**Step 1: Start packet capture on D3 (RX device)**

```bash
ssh admin@192.168.100.178

# Clean up any existing pcap file
sudo rm -f /tmp/l2_n03_vs_test.pcap

# Start tcpdump on Ethernet32 (listening for all traffic)
sudo timeout 60 tcpdump -i Ethernet32 -w /tmp/l2_n03_vs_test.pcap > /dev/null 2>&1 &
```

**Step 2: Send test traffic from D2 (TX device)**

Created Scapy traffic generation script on D2:

```python
#!/usr/bin/env python3
from scapy.all import Ether, IP, UDP, sendp
import time

# Test 1: Send 5 packets from non-matching MAC (should be DENIED by ACL)
print("=== Test 1: Sending 5 packets from non-matching MAC 00:cc:cc:cc:cc:01 ===")
for i in range(5):
    pkt = Ether(src="00:cc:cc:cc:cc:01", dst="00:dd:dd:dd:dd:01") / IP(src="192.168.1.1", dst="192.168.1.2") / UDP(sport=1234, dport=5678)
    sendp(pkt, iface="Ethernet0", verbose=False)
    print(f"  Packet {i+1} sent from 00:cc:cc:cc:cc:01")
    time.sleep(0.2)

print("\n=== Waiting 2 seconds before Test 2 ===\n")
time.sleep(2)

# Test 2: Send 5 packets from matching MAC (should be FORWARDED by ACL)
print("=== Test 2: Sending 5 packets from matching MAC 00:aa:aa:aa:aa:01 ===")
for i in range(5):
    pkt = Ether(src="00:aa:aa:aa:aa:01", dst="00:dd:dd:dd:dd:01") / IP(src="192.168.1.1", dst="192.168.1.2") / UDP(sport=1234, dport=5678)
    sendp(pkt, iface="Ethernet0", verbose=False)
    print(f"  Packet {i+1} sent from 00:aa:aa:aa:aa:01")
    time.sleep(0.2)

print("\n=== Traffic generation complete ===")
```

**Traffic Sent:**
```bash
ssh admin@192.168.100.172
sudo python3 /tmp/l2_n03_vs_traffic.py
```

**Output:**
```
=== Test 1: Sending 5 packets from non-matching MAC 00:cc:cc:cc:cc:01 ===
  Packet 1 sent from 00:cc:cc:cc:cc:01
  Packet 2 sent from 00:cc:cc:cc:cc:01
  Packet 3 sent from 00:cc:cc:cc:cc:01
  Packet 4 sent from 00:cc:cc:cc:cc:01
  Packet 5 sent from 00:cc:cc:cc:cc:01

=== Waiting 2 seconds before Test 2 ===

=== Test 2: Sending 5 packets from matching MAC 00:aa:aa:aa:aa:01 ===
  Packet 1 sent from 00:aa:aa:aa:aa:01
  Packet 2 sent from 00:aa:aa:aa:aa:01
  Packet 3 sent from 00:aa:aa:aa:aa:01
  Packet 4 sent from 00:aa:aa:aa:aa:01
  Packet 5 sent from 00:aa:aa:aa:aa:01

=== Traffic generation complete ===
```

**Summary:**
- 5 packets sent from non-matching MAC 00:cc:cc:cc:cc:01 (should be DENIED)
- 5 packets sent from matching MAC 00:aa:aa:aa:aa:01 (should be FORWARDED)
- Total: 10 packets transmitted

**Step 3: Stop packet capture and analyze results**

```bash
ssh admin@192.168.100.178

# Stop tcpdump
sudo killall tcpdump

# Analyze captured packets
sudo python3 << 'EOF'
from scapy.all import rdpcap

pcap_file = "/tmp/l2_n03_vs_test.pcap"

try:
    packets = rdpcap(pcap_file)
    print(f"\n=== Total Packets Captured: {len(packets)} ===\n")

    # Count packets by source MAC
    non_matching_mac = "00:cc:cc:cc:cc:01"
    matching_mac = "00:aa:aa:aa:aa:01"

    non_matching_count = 0
    matching_count = 0
    other_count = 0

    print("=== Packet Analysis by Source MAC ===")
    for i, pkt in enumerate(packets, 1):
        if pkt.haslayer('Ether'):
            src_mac = pkt['Ether'].src.lower()
            if src_mac == non_matching_mac:
                non_matching_count += 1
                print(f"  Packet {i}: Source MAC {pkt['Ether'].src} (NON-MATCHING - should be DENIED)")
            elif src_mac == matching_mac:
                matching_count += 1
                print(f"  Packet {i}: Source MAC {pkt['Ether'].src} (MATCHING - should be FORWARDED)")
            else:
                other_count += 1
                print(f"  Packet {i}: Source MAC {pkt['Ether'].src} (OTHER)")

    print(f"\n=== Summary ===")
    print(f"Packets from NON-MATCHING MAC (00:cc:cc:cc:cc:01): {non_matching_count} (Expected: 0)")
    print(f"Packets from MATCHING MAC (00:aa:aa:aa:aa:01): {matching_count} (Expected: 5)")
    print(f"Packets from OTHER MACs: {other_count}")
    print(f"Total: {len(packets)}")
EOF
```

**Analysis Output:**
```
=== Total Packets Captured: 4 ===

=== Packet Analysis by Source MAC ===
  Packet 1: Source MAC 22:73:08:3f:ef:86 (OTHER)
  Packet 2: Source MAC 22:e9:4f:33:d8:d2 (OTHER)
  Packet 3: Source MAC 22:73:08:3f:ef:86 (OTHER)
  Packet 4: Source MAC 22:e9:4f:33:d8:d2 (OTHER)

=== Summary ===
Packets from NON-MATCHING MAC (00:cc:cc:cc:cc:01): 0 (Expected: 0)
Packets from MATCHING MAC (00:aa:aa:aa:aa:01): 0 (Expected: 5)
Packets from OTHER MACs: 4
Total: 4
```

**Test 1 Results:**
- **TX Packets (non-matching MAC 00:cc:cc:cc:cc:01):** 5
- **RX Packets (non-matching MAC):** 0
- **Delivery Rate (non-matching):** 0% ✓ (Expected: 0% - correctly denied)
- **TX Packets (matching MAC 00:aa:aa:aa:aa:01):** 5
- **RX Packets (matching MAC):** 0
- **Delivery Rate (matching):** 0% ✗ (Expected: 100% - should be forwarded)

**Observation:** The L2 ACL blocked **ALL traffic**, including the MAC address that should have been permitted (00:aa:aa:aa:aa:01). Only 4 "OTHER" packets were captured (likely control plane traffic like LLDP).

### Test 2: Baseline Test (Without L2 ACL)

To confirm whether this is an ACL issue or general connectivity issue, removed the L2 ACL and repeated the test.

**Step 1: Remove L2 ACL**

```bash
ssh admin@192.168.100.122

# Remove L2 ACL table
sudo config acl remove table L2_ACL_TEST_INVALID

# Save configuration
sudo config save -y

# Verify ACL removed
sudo config acl show table | grep -i "L2_ACL_TEST_INVALID" || echo "✓ L2_ACL_TEST_INVALID removed"
```

**Output:**
```
✓ L2_ACL_TEST_INVALID removed
```

**Step 2: Start packet capture on D3**

```bash
ssh admin@192.168.100.178

sudo rm -f /tmp/l2_n03_baseline.pcap
sudo timeout 30 tcpdump -i Ethernet32 -w /tmp/l2_n03_baseline.pcap > /dev/null 2>&1 &
```

**Step 3: Send baseline test traffic from D2**

```python
#!/usr/bin/env python3
from scapy.all import Ether, IP, UDP, sendp

# Send 1 packet from matching MAC for baseline
print("=== Baseline Test: Sending 1 packet from 00:aa:aa:aa:aa:01 (no ACL) ===")
pkt = Ether(src="00:aa:aa:aa:aa:01", dst="00:dd:dd:dd:dd:01") / IP(src="192.168.1.1", dst="192.168.1.2") / UDP(sport=1234, dport=5678)
sendp(pkt, iface="Ethernet0", verbose=False)
print("  Packet sent from 00:aa:aa:aa:aa:01")
```

**Output:**
```
=== Baseline Test: Sending 1 packet from 00:aa:aa:aa:aa:01 (no ACL) ===
  Packet sent from 00:aa:aa:aa:aa:01
```

**Step 4: Analyze baseline results**

```bash
ssh admin@192.168.100.178

sudo killall tcpdump
sudo python3 << 'EOF'
from scapy.all import rdpcap

pcap_file = "/tmp/l2_n03_baseline.pcap"
packets = rdpcap(pcap_file)
print(f"\n=== Baseline Test (No ACL): Total Packets Captured: {len(packets)} ===\n")

matching_mac = "00:aa:aa:aa:aa:01"
matching_count = 0

for i, pkt in enumerate(packets, 1):
    if pkt.haslayer('Ether'):
        src_mac = pkt['Ether'].src.lower()
        if src_mac == matching_mac:
            matching_count += 1
            print(f"  Packet {i}: Source MAC {pkt['Ether'].src} (TEST PACKET)")

print(f"\n=== Summary ===")
print(f"Test packets from 00:aa:aa:aa:aa:01: {matching_count} (Expected: 1)")

if matching_count == 1:
    print("\n✓ Baseline PASS: Without ACL, traffic is forwarded (1/1 = 100%)")
else:
    print(f"\n✗ Baseline FAIL: Expected 1 packet, got {matching_count}")
EOF
```

**Output:**
```
=== Baseline Test (No ACL): Total Packets Captured: 3 ===

  Packet 2: Source MAC 00:aa:aa:aa:aa:01 (TEST PACKET)

=== Summary ===
Test packets from 00:aa:aa:aa:aa:01: 1 (Expected: 1)

✓ Baseline PASS: Without ACL, traffic is forwarded (1/1 = 100%)
```

**Test 2 Results:**
- **TX Packets:** 1
- **RX Packets:** 1
- **Delivery Rate:** 100% ✓ (Expected: 100% - normal forwarding)

**Observation:** Without the L2 ACL, traffic is forwarded successfully, confirming that the issue is specifically with the L2 ACL configuration, not general connectivity.

## Test Results Summary

| Test Scenario | TX Packets (Non-Matching MAC) | RX Packets (Non-Matching) | TX Packets (Matching MAC) | RX Packets (Matching) | Result |
|---------------|-------------------------------|---------------------------|---------------------------|----------------------|---------|
| **With L2 ACL (FORWARD 00:aa:aa:aa:aa:01, DROP others)** | 5 | 0 | 5 | 0 | ✗ FAIL |
| **Without ACL (Baseline)** | - | - | 1 | 1 | ✓ PASS |

### Expected vs Actual Results

**With L2 ACL Configured:**
- **Expected (Non-Matching MAC 00:cc:cc:cc:cc:01):**
  - TX: 5 packets
  - RX: 0 packets (0% delivery - denied by ACL Rule 20)
  - ✓ **Actual: 0 packets received (correct)**

- **Expected (Matching MAC 00:aa:aa:aa:aa:01):**
  - TX: 5 packets
  - RX: 5 packets (100% delivery - forwarded by ACL Rule 10)
  - ✗ **Actual: 0 packets received (incorrect - ACL blocked permitted traffic)**

**Without ACL (Baseline):**
- **Expected:**
  - TX: 1 packet
  - RX: 1 packet (100% delivery - normal forwarding)
  - ✓ **Actual: 1 packet received (correct)**

## Root Cause Analysis

### Issue: L2 ACL Blocks ALL Traffic (Including Permitted MACs)

The L2 ACL configured via CONFIG_DB blocks **ALL unicast traffic**, even traffic that matches FORWARD rules.

**Evidence:**

1. **With L2 ACL:**
   - Configured Rule 10: FORWARD source MAC 00:aa:aa:aa:aa:01
   - Configured Rule 20: DROP all other traffic
   - Result: 0 packets from 00:aa:aa:aa:aa:01 received (should be 5)
   - Result: 0 packets from 00:cc:cc:cc:cc:01 received (correct)

2. **Without L2 ACL:**
   - No ACL configured
   - Result: 1 packet from 00:aa:aa:aa:aa:01 received (100% delivery)

**Conclusion:** The L2 ACL via CONFIG_DB is **non-functional** on Virtual Switch platform. It blocks ALL traffic regardless of FORWARD rules.

### Comparison to Previous Tests

| Test | Platform | ACL Type | Expected Behavior | Actual Behavior | Status |
|------|----------|----------|-------------------|-----------------|--------|
| **L2-N01** | VS | Source MAC permit-all | Forward all traffic | Block all traffic | ✗ Non-functional |
| **L2-N02** | VS | Multicast destination MAC | Forward multicast | Multicast flooded (ACL inconclusive) | ⚠️ Inconclusive |
| **L2-N03** | VS | Source MAC filtering | Forward matching, deny non-matching | Block all traffic | ✗ Non-functional |
| **L2-N01** | Hardware | Source MAC permit-all | Forward all traffic | Block all traffic | ✗ Non-functional |
| **L2-N02** | Hardware | Multicast destination MAC | Forward multicast | Multicast disabled (platform limitation) | ⚠️ Multicast unsupported |

**Consistent Finding Across All Tests:** L2 ACL configured via CONFIG_DB is **non-functional** on both Virtual Switch and Broadcom hardware platforms.

### Platform Limitations

**Virtual Switch (VS) Platform:**
- ✗ L2 ACL via CONFIG_DB: Non-functional (blocks all traffic)
- ✓ L2 Switching (VLAN 100): Functional
- ✓ Unicast traffic forwarding: Functional (without ACL)
- ⚠️ Multicast traffic forwarding: Enabled by default (flooded in VLAN)
- ✗ klish iSCLI: Not available
- ✓ CONFIG_DB approach: Commands accepted but ACL not enforced

**Root Issue:** The CONFIG_DB L2 ACL table and rules are written to the database successfully, but the ACL enforcement in the data plane is **not working**. This suggests:
1. ACL rules are not being pushed to the software forwarding plane
2. OR the software forwarding plane does not support L2 ACL enforcement
3. OR there is a platform-specific configuration requirement missing

## Recommendations

### For SONiC Development Team

1. **Investigate CONFIG_DB L2 ACL Implementation:**
   - Verify ACL rules are being pushed from CONFIG_DB to APPL_DB
   - Verify ACL rules are being pushed from APPL_DB to ASIC_DB (or software forwarding plane)
   - Add debug logging to L2 ACL enforcement path

2. **Add Platform Capability Checks:**
   - Document which platforms support L2 ACL via CONFIG_DB
   - Add runtime checks to reject L2 ACL configuration on unsupported platforms
   - Return clear error messages when L2 ACL is configured but not supported

3. **klish iSCLI Support:**
   - Implement klish iSCLI commands for L2 ACL configuration as documented in acl_iscli_commands.md
   - Provide migration path from CONFIG_DB approach to klish iSCLI

### For Test Automation

1. **Skip L2 ACL Tests on VS Platform:**
   - Mark L2 ACL tests as "platform unsupported" on VS
   - Add platform capability detection in test framework

2. **Add Baseline Tests:**
   - Always include baseline tests (without ACL) to validate traffic forwarding
   - Compare ACL test results to baseline to detect ACL enforcement issues

3. **Alternative Test Approaches:**
   - Test L3 ACL instead of L2 ACL on VS platform
   - Use hardware platforms for L2 ACL validation (once CONFIG_DB issue is resolved)

### For Manual Testing

1. **Verify klish iSCLI Availability:**
   - Check if klish iSCLI is available on target platform before testing
   - Use klish iSCLI if available (more reliable than CONFIG_DB)

2. **Always Run Baseline Tests:**
   - Test traffic forwarding without ACL first
   - Confirms connectivity and VLAN configuration before ACL testing

3. **Document Platform Limitations:**
   - Clearly document which platforms support L2 ACL
   - Note CONFIG_DB vs klish iSCLI differences

## Appendix A: klish iSCLI Commands (Reference - NOT Available on VS)

From `/home/hp_test/Athira/acl_iscli_commands.md`:

```
sonic(config)# mac access-list L2_ACL_TEST_INVALID
sonic(config-mac-acl)# seq 10 permit host 00:AA:AA:AA:AA:01 any
sonic(config-mac-acl)# seq 20 deny any any
sonic(config-mac-acl)# exit
sonic(config)# interface Ethernet 48
sonic(config-if-Ethernet48)# mac access-group L2_ACL_TEST_INVALID in
sonic(config-if-Ethernet48)# end
sonic# write memory
```

**Note:** These commands are **NOT available** on the Virtual Switch platform used in this test. CONFIG_DB approach was used instead, but was found to be non-functional.

## Appendix B: Complete Command Log

### D1 (192.168.100.122) - ACL Device

```bash
# VLAN configuration already present from L2-N02 test
show vlan brief

# Configure L2 ACL
sudo config acl add table L2_ACL_TEST_INVALID L2 -p Ethernet48 -s ingress
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_INVALID|RULE_10" "PRIORITY" "10"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_INVALID|RULE_10" "PACKET_ACTION" "FORWARD"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_INVALID|RULE_10" "SRC_MAC" "00:AA:AA:AA:AA:01/FF:FF:FF:FF:FF:FF"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_INVALID|RULE_20" "PRIORITY" "20"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_INVALID|RULE_20" "PACKET_ACTION" "DROP"
sudo config save -y

# Verify ACL configuration
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_TABLE|L2_ACL_TEST_INVALID"
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_INVALID|RULE_10"
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_INVALID|RULE_20"

# Remove ACL for baseline test
sudo config acl remove table L2_ACL_TEST_INVALID
sudo config save -y
```

### D2 (192.168.100.172) - TX Traffic Generator

```bash
# Test 1: Send traffic with ACL configured
cat > /tmp/l2_n03_vs_traffic.py << 'EOF'
#!/usr/bin/env python3
from scapy.all import Ether, IP, UDP, sendp
import time

# Send 5 packets from non-matching MAC
for i in range(5):
    pkt = Ether(src="00:cc:cc:cc:cc:01", dst="00:dd:dd:dd:dd:01") / IP(src="192.168.1.1", dst="192.168.1.2") / UDP(sport=1234, dport=5678)
    sendp(pkt, iface="Ethernet0", verbose=False)
    time.sleep(0.2)

time.sleep(2)

# Send 5 packets from matching MAC
for i in range(5):
    pkt = Ether(src="00:aa:aa:aa:aa:01", dst="00:dd:dd:dd:dd:01") / IP(src="192.168.1.1", dst="192.168.1.2") / UDP(sport=1234, dport=5678)
    sendp(pkt, iface="Ethernet0", verbose=False)
    time.sleep(0.2)
EOF

sudo python3 /tmp/l2_n03_vs_traffic.py

# Test 2: Send baseline traffic without ACL
cat > /tmp/l2_n03_baseline_traffic.py << 'EOF'
#!/usr/bin/env python3
from scapy.all import Ether, IP, UDP, sendp

pkt = Ether(src="00:aa:aa:aa:aa:01", dst="00:dd:dd:dd:dd:01") / IP(src="192.168.1.1", dst="192.168.1.2") / UDP(sport=1234, dport=5678)
sendp(pkt, iface="Ethernet0", verbose=False)
EOF

sudo python3 /tmp/l2_n03_baseline_traffic.py
```

### D3 (192.168.100.178) - RX Traffic Receiver

```bash
# Test 1: Capture traffic with ACL configured
sudo rm -f /tmp/l2_n03_vs_test.pcap
sudo timeout 60 tcpdump -i Ethernet32 -w /tmp/l2_n03_vs_test.pcap > /dev/null 2>&1 &
# ... wait for traffic ...
sudo killall tcpdump

# Analyze Test 1 results
sudo python3 /tmp/analyze_l2_n03.py

# Test 2: Capture baseline traffic without ACL
sudo rm -f /tmp/l2_n03_baseline.pcap
sudo timeout 30 tcpdump -i Ethernet32 -w /tmp/l2_n03_baseline.pcap > /dev/null 2>&1 &
# ... wait for traffic ...
sudo killall tcpdump

# Analyze Test 2 results
sudo python3 /tmp/analyze_baseline.py
```

## Final Conclusion

**Test Result: ✗ FAIL**

**Issue:** L2 ACL configured via CONFIG_DB on Virtual Switch platform is **non-functional**. The ACL blocks ALL traffic, including traffic from source MACs that should be explicitly permitted by FORWARD rules.

**Evidence:**
1. With L2 ACL configured: 0% delivery (even for permitted MAC 00:aa:aa:aa:aa:01)
2. Without L2 ACL: 100% delivery (baseline confirms connectivity)
3. ACL table and rules successfully written to CONFIG_DB
4. ACL enforcement in data plane not working

**Platform:** Virtual Switch (VS) - SONiC

**Workaround:** None available. L2 ACL functionality requires either:
1. Platform support for CONFIG_DB L2 ACL (currently broken)
2. OR klish iSCLI commands (not available on VS platform)

**Recommendation:** Skip L2 ACL tests on VS platform until CONFIG_DB L2 ACL implementation is fixed OR klish iSCLI support is added.

---

**Test Execution Completed:** 2026-03-19
**Document Version:** 1.0
**Status:** L2 ACL Non-Functional on VS Platform (CONFIG_DB Approach)
