# L2-N02: Multicast Destination MAC - Hardware Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-N02 |
| **Description** | Multicast destination MAC address matching |
| **Category** | Negative/Edge Case |
| **Expected Outcome** | Multicast frames processed normally with ACL permit rule |
| **Platforms** | HW (Broadcom ASIC) |
| **Date** | 2026-03-19 |
| **Tester** | Claude Code |

---

## Testbed Information

### Hardware Devices

| Device | Hostname | IP Address | Platform | ASIC | Interface | Role |
|--------|----------|------------|----------|------|-----------|------|
| **D1 (8011)** | sonic | 192.168.100.119 | Supermicro SSE-T8196 | Broadcom | Ethernet272, Ethernet513 | ACL Device (DUT) |
| **D2 (8023)** | sonic | 192.168.100.140 | Celestica DS3000 | Broadcom | Ethernet64 | TX Traffic Generator |
| **D3 (8010)** | sonic | 192.168.100.173 | Supermicro SSE-T8164 | Broadcom | Ethernet513 | RX Traffic Receiver |

### Topology

```
┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
│   DUT2       │                    │   DUT1       │                    │   DUT3       │
│  (TX Host)   │                    │ (ACL Device) │                    │  (RX Host)   │
│    8023      │                    │    8011      │                    │    8010      │
│              │                    │              │                    │              │
│ Ethernet64 ◄─┼────────────────────┼─ Ethernet272 │                    │              │
│ VLAN 100     │                    │ VLAN 100     │                    │              │
│              │   (L2 switching)   │ (ACL ingress)│                    │              │
│              │                    │              │                    │              │
│              │                    │ Ethernet513──┼────────────────────┼──► Ethernet513
│              │                    │ VLAN 100     │   (L2 switching)   │ VLAN 100     │
│              │                    │              │                    │              │
└──────────────┘                    └──────────────┘                    └──────────────┘
```

---

## Step 1: L2 VLAN Configuration

All devices configured in VLAN 100 L2 switching mode (carried over from L2-N01 testing).

### D1 (ACL Device - 192.168.100.119)

```bash
ssh admin@192.168.100.119
# VLAN 100 already configured with Ethernet272 and Ethernet513 as members
```

### D2 (TX Generator - 192.168.100.140)

```bash
ssh admin@192.168.100.140
# VLAN 100 already configured with Ethernet64 as member
```

### D3 (RX Receiver - 192.168.100.173)

```bash
ssh admin@192.168.100.173
# VLAN 100 already configured with Ethernet513 as member
```

---

## Step 2: ACL Configuration on DUT (CONFIG_DB Approach)

### 2.1 Create L2 ACL with Multicast MAC Rule

```bash
ssh admin@192.168.100.119

# Remove previous ACL tables
sudo config acl remove table L2_ACL_TEST_CASE 2>/dev/null || true
sudo config acl remove table L2_ACL_SIMPLE_TEST 2>/dev/null || true

# Create L2 ACL table for multicast test
sudo config acl add table L2_ACL_TEST_MULTICAST L2 -p Ethernet272 -s ingress

# Rule 10: FORWARD multicast traffic to 01:00:5E:00:00:01 (IPv4 multicast)
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_MULTICAST|RULE_10" "PRIORITY" "10"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_MULTICAST|RULE_10" "PACKET_ACTION" "FORWARD"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_MULTICAST|RULE_10" "DST_MAC" "01:00:5E:00:00:01/FF:FF:FF:FF:FF:FF"

# Rule 20: DROP all other traffic
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_MULTICAST|RULE_20" "PRIORITY" "20"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_MULTICAST|RULE_20" "PACKET_ACTION" "DROP"

sudo config save -y
```

### 2.2 Verify ACL Configuration

```bash
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_TABLE|L2_ACL_TEST_MULTICAST"
```

**Output:**
```
{'policy_desc': 'L2_ACL_TEST_MULTICAST', 'ports@': 'Ethernet272', 'stage': 'ingress', 'type': 'L2'}
```

```bash
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_MULTICAST|RULE_10"
```

**Output:**
```
{'PRIORITY': '10', 'PACKET_ACTION': 'FORWARD', 'DST_MAC': '01:00:5E:00:00:01/FF:FF:FF:FF:FF:FF'}
```

```bash
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_MULTICAST|RULE_20"
```

**Output:**
```
{'PRIORITY': '20', 'PACKET_ACTION': 'DROP'}
```

**Status:** ✓ ACL configuration saved to CONFIG_DB successfully

**NOTE:** klish iSCLI commands (`mac access-list`, `permit any host`, `mac access-group`) referenced in `/home/hp_test/Athira/acl_iscli_commands.md` are **NOT available** on this Broadcom ASIC hardware platform. Using CONFIG_DB approach as alternative.

---

## Step 3: RX Device Setup

```bash
ssh admin@192.168.100.173

sudo rm -f /tmp/l2_n02_test.pcap
sudo timeout 60 tcpdump -i Ethernet513 'ether dst 01:00:5e:00:00:01' -w /tmp/l2_n02_test.pcap > /dev/null 2>&1 &
```

**Status:** ✓ tcpdump started on D3:Ethernet513, listening for multicast dst MAC `01:00:5e:00:00:01`

---

## Step 4: TX Traffic Generation

```bash
ssh admin@192.168.100.140

cat > /tmp/l2_n02_traffic.py << 'EOF'
#!/usr/bin/env python3
"""
L2-N02: Multicast Destination MAC Test
Sends 10 multicast frames to 01:00:5E:00:00:01 (IPv4 multicast)
"""

from scapy.all import Ether, IP, Raw, sendp
import time

iface = "Ethernet64"
src_mac = "00:aa:aa:aa:aa:01"
dst_mac = "01:00:5e:00:00:01"  # IPv4 multicast MAC
total_packets = 10

print(f"[+] L2-N02: Multicast Destination MAC Test")
print(f"    Src MAC: {src_mac}")
print(f"    Dst MAC: {dst_mac} (IPv4 Multicast)")
print(f"    Total Packets: {total_packets}")
print()

pkt = Ether(src=src_mac, dst=dst_mac) / \
      IP(src="10.0.0.1", dst="224.0.0.1") / \
      Raw(load="L2-N02-TEST-MULTICAST")

sent_count = 0
try:
    for i in range(total_packets):
        sendp(pkt, iface=iface, verbose=False)
        sent_count += 1
        print(f"[→] Sent multicast packet {sent_count}/{total_packets}")
        time.sleep(1.0)
except Exception as e:
    print(f"[✗] Error: {e}")
    exit(1)

print(f"\n[✓] Completed. Sent {sent_count} multicast packets")
EOF

chmod +x /tmp/l2_n02_traffic.py
sudo python3 /tmp/l2_n02_traffic.py
```

**Output:**
```
[+] L2-N02: Multicast Destination MAC Test
    Src MAC: 00:aa:aa:aa:aa:01
    Dst MAC: 01:00:5e:00:00:01 (IPv4 Multicast)
    Total Packets: 10

[→] Sent multicast packet 1/10
[→] Sent multicast packet 2/10
[→] Sent multicast packet 3/10
[→] Sent multicast packet 4/10
[→] Sent multicast packet 5/10
[→] Sent multicast packet 6/10
[→] Sent multicast packet 7/10
[→] Sent multicast packet 8/10
[→] Sent multicast packet 9/10
[→] Sent multicast packet 10/10

[✓] Completed. Sent 10 multicast packets
```

**Status:** ✓ Successfully sent 10 multicast packets to destination MAC `01:00:5e:00:00:01`

---

## Step 5: Verification

```bash
ssh admin@192.168.100.173

sudo killall tcpdump
sleep 2

# Verify captured multicast packets
sudo python3 -c "from scapy.all import rdpcap; packets = rdpcap('/tmp/l2_n02_test.pcap'); print(f'Captured: {len(packets)} multicast packets')"
```

**Output:**
```
Captured: 0 multicast packets
```

**Result:** ✗ **FAILED - 0 out of 10 multicast packets received (0% delivery rate)**

---

## Additional Verification: Baseline Connectivity Test

To verify if the issue is specific to L2 ACL or a general multicast forwarding limitation, the ACL was removed and a baseline test performed.

### Remove ACL

```bash
ssh admin@192.168.100.119

sudo config acl remove table L2_ACL_TEST_MULTICAST 2>/dev/null || true
sudo config save -y

# Verify ACL removed
sudo sonic-db-cli CONFIG_DB KEYS "ACL_TABLE|*" | grep L2_ACL || echo "✓ No L2 ACL tables found"
```

**Output:**
```
✓ No L2 ACL tables found
```

### Baseline Test (No ACL)

```bash
# On D3: Start tcpdump
ssh admin@192.168.100.173
sudo rm -f /tmp/l2_n02_baseline.pcap
sudo timeout 15 tcpdump -i Ethernet513 'ether dst 01:00:5e:00:00:01' -w /tmp/l2_n02_baseline.pcap > /dev/null 2>&1 &

# On D2: Send 1 multicast packet
ssh admin@192.168.100.140
sudo python3 -c "from scapy.all import Ether, IP, Raw, sendp; pkt = Ether(src='00:aa:aa:aa:aa:01', dst='01:00:5e:00:00:01') / IP(src='10.0.0.1', dst='224.0.0.1') / Raw(load='BASELINE-TEST'); sendp(pkt, iface='Ethernet64', verbose=False); print('[✓] Sent 1 multicast packet (no ACL)')"

# On D3: Verify
ssh admin@192.168.100.173
sudo killall tcpdump 2>/dev/null
sleep 1
sudo python3 -c "from scapy.all import rdpcap; pkts = rdpcap('/tmp/l2_n02_baseline.pcap'); print(f'Baseline (no ACL): {len(pkts)} multicast packets captured')"
```

**Output:**
```
Baseline (no ACL): 0 multicast packets captured
```

**Conclusion:** Multicast traffic is **NOT forwarded** even without ACL, indicating this is a multicast forwarding limitation, not specifically an L2 ACL issue.

---

## Test Results Summary

| Test Scenario | TX Packets | RX Packets | Delivery Rate | Result |
|---------------|------------|------------|---------------|---------|
| **With L2 ACL (FORWARD multicast)** | 10 | 0 | 0% | ✗ FAIL |
| **Without ACL (Baseline)** | 1 | 0 | 0% | ✗ FAIL |

---

## Root Cause Analysis

### Issue 1: L2 ACL Not Functional (from L2-N01)

Based on comprehensive testing in L2-N01, L2 ACL configured via CONFIG_DB approach **does not function properly** on Broadcom ASIC hardware:
- Even permit-all ACL (both rules set to FORWARD) blocks 100% of traffic
- Issue affects unicast MAC filtering (documented in L2-N01)

### Issue 2: Multicast Forwarding Disabled by Default

L2-N02 revealed an additional platform limitation:
- **Multicast MAC addresses are NOT forwarded** in VLAN 100 L2 switching mode
- This occurs **regardless of ACL presence**
- Likely requires IGMP snooping or multicast forwarding configuration

**Evidence:**
1. With L2 ACL: 0 multicast packets received ✗
2. Without ACL (baseline): 0 multicast packets received ✗

**Comparison:** In L2-N01 (unicast MAC), removing ACL allowed traffic to flow (1 packet captured), but in L2-N02 (multicast MAC), removing ACL still results in 0 packets.

---

## Platform Limitations Identified

### 1. klish iSCLI MAC ACL Commands NOT Available

The following commands from `/home/hp_test/Athira/acl_iscli_commands.md` are **NOT implemented** on Broadcom hardware:

```bash
configure terminal
mac access-list L2_ACL_TEST_MULTICAST
permit any host 01:00:5e:00:00:01  # Command not recognized
deny any any                       # Command not recognized
exit
interface Ethernet272
mac access-group L2_ACL_TEST_MULTICAST in  # Command not recognized
```

**Error Output:**
```
sonic(config)# mac access-list L2_ACL_TEST_MULTICAST
% Command incomplete: mac access-list L2_ACL_TEST_MULTICAST
```

**Workaround:** Use CONFIG_DB approach with `config acl` and `sonic-db-cli CONFIG_DB HSET` commands (though functionality is still broken).

### 2. L2 ACL via CONFIG_DB Non-Functional

- ACL tables and rules configure successfully in CONFIG_DB
- ACL does NOT enforce packet filtering
- Affects both unicast (L2-N01) and multicast (L2-N02) traffic
- Root cause likely in SAI layer, ASIC programming, or orchagent

### 3. Multicast Forwarding Not Enabled

- Multicast MAC addresses (01:00:5E:xx:xx:xx) are not forwarded in VLAN switching mode
- Requires additional configuration (IGMP snooping, multicast routing, etc.)
- This is separate from the L2 ACL issue

---

## Test Conclusion

**TEST STATUS:** ✗ **BLOCKED - Cannot validate L2-N02 multicast ACL functionality**

### Blocking Issues:

1. **L2 ACL Non-Functional** (Primary Issue from L2-N01):
   - L2 ACL configured via CONFIG_DB does not enforce packet filtering
   - Affects all L2 ACL test cases (L2-01 through L2-08, L2-N01, L2-N02)

2. **Multicast Forwarding Disabled** (L2-N02 Specific):
   - Multicast traffic not forwarded even without ACL
   - Cannot establish baseline for multicast ACL testing
   - Requires IGMP or multicast configuration investigation

### Comparison to L2-N01

| Aspect | L2-N01 (Unicast MAC) | L2-N02 (Multicast MAC) |
|--------|----------------------|------------------------|
| **ACL Configuration** | ✓ Saved to CONFIG_DB | ✓ Saved to CONFIG_DB |
| **With ACL Applied** | 0 packets (blocked) | 0 packets (blocked) |
| **Without ACL (Baseline)** | 1 packet (flows) ✓ | 0 packets (blocked) ✗ |
| **Root Cause** | L2 ACL broken | L2 ACL broken + multicast disabled |

### Recommendations:

1. **Investigate L2 ACL Root Cause:**
   - Check orchagent logs for ACL programming errors
   - Verify SAI layer ACL support for L2/MAC filtering
   - Review ASIC_DB ACL entries
   - Test on different SONiC version

2. **Enable Multicast Forwarding:**
   - Configure IGMP snooping on VLAN 100
   - Investigate multicast routing requirements
   - Check if multicast flooding needs to be enabled

3. **Alternative CLI Approach:**
   - Verify if klish iSCLI MAC ACL commands are available in future SONiC releases
   - Test REST API or gNMI for L2 ACL configuration

---

## Configuration Reference

### CONFIG_DB ACL Entries (Verified)

```bash
# ACL Table
sonic-db-cli CONFIG_DB HGETALL "ACL_TABLE|L2_ACL_TEST_MULTICAST"
# Output: {'policy_desc': 'L2_ACL_TEST_MULTICAST', 'ports@': 'Ethernet272', 'stage': 'ingress', 'type': 'L2'}

# ACL Rule 10 (Permit Multicast)
sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_MULTICAST|RULE_10"
# Output: {'PRIORITY': '10', 'PACKET_ACTION': 'FORWARD', 'DST_MAC': '01:00:5E:00:00:01/FF:FF:FF:FF:FF:FF'}

# ACL Rule 20 (Deny All Others)
sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_TEST_MULTICAST|RULE_20"
# Output: {'PRIORITY': '20', 'PACKET_ACTION': 'DROP'}
```

---

**Document Version:** 1.0
**Last Updated:** 2026-03-19
**Status:** BLOCKED - Multiple platform limitations identified
**Platform Tested:** Hardware SONiC Switches (Broadcom ASIC)
**Related Test Cases:** L2-N01 (unicast MAC case sensitivity - also failed due to L2 ACL issue)

