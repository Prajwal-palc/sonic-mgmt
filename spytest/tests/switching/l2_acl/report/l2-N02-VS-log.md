# L2-N02: Multicast Destination MAC - Virtual Switch Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-N02 |
| **Description** | Multicast destination MAC address matching |
| **Category** | Negative/Edge Case |
| **Expected Outcome** | Multicast frames processed normally with ACL permit rule |
| **Platforms** | VS (Virtual Switch) |
| **Date** | 2026-03-19 |
| **Tester** | Claude Code |

---

## Testbed Information

### Virtual Switch Devices

| Device | Hostname | IP Address | Platform | Interface | Role |
|--------|----------|------------|----------|-----------|------|
| **D1** | sonic | 192.168.100.122 | VS (Virtual Switch) | Ethernet48, Ethernet32 | ACL Device (DUT) |
| **D2** | sonic | 192.168.100.172 | VS (Virtual Switch) | Ethernet0 | TX Traffic Generator |
| **D3** | sonic | 192.168.100.178 | VS (Virtual Switch) | Ethernet32 | RX Traffic Receiver |

### Topology

```
┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
│   DUT2       │                    │   DUT1       │                    │   DUT3       │
│  (TX Host)   │                    │ (ACL Device) │                    │  (RX Host)   │
│      VS      │                    │      VS      │                    │      VS      │
│              │                    │              │                    │              │
│ Ethernet0 ◄──┼────────────────────┼─ Ethernet48  │                    │              │
│ VLAN 100     │                    │ VLAN 100     │                    │              │
│              │   (L2 switching)   │ (ACL ingress)│                    │              │
│              │                    │              │                    │              │
│              │                    │ Ethernet32───┼────────────────────┼──► Ethernet32
│              │                    │ VLAN 100     │   (L2 switching)   │ VLAN 100     │
│              │                    │              │                    │              │
└──────────────┘                    └──────────────┘                    └──────────────┘
```

---

## Step 1: L2 VLAN Configuration

### D1 (ACL Device - 192.168.100.122)

```bash
ssh admin@192.168.100.122
# Password: root@123

# Remove any existing L3 configuration
sudo config interface ip remove Ethernet48 10.0.0.254/24 2>/dev/null || true
sudo config interface ip remove Ethernet32 20.0.0.254/24 2>/dev/null || true

# Create VLAN 100
sudo config vlan add 100

# Add interfaces to VLAN 100
sudo config vlan member add 100 Ethernet48 -u
sudo config vlan member add 100 Ethernet32 -u

# Bring interfaces up
sudo config interface startup Ethernet48
sudo config interface startup Ethernet32

sudo config save -y
```

**Verification:**
```bash
show vlan brief
```

**Output:**
```
+-----------+--------------+------------+----------------+-------------+-----------------------+
|   VLAN ID | IP Address   | Ports      | Port Tagging   | Proxy ARP   | DHCP Helper Address   |
+===========+==============+============+================+=============+=======================+
|       100 |              | Ethernet32 | untagged       | disabled    |                       |
|           |              | Ethernet48 | untagged       |             |                       |
+-----------+--------------+------------+----------------+-------------+-----------------------+
```

```bash
show interface status Ethernet48
show interface status Ethernet32
```

**Output:**
```
  Interface        Lanes       Speed    MTU    FEC          Alias    Vlan    Oper    Admin
-----------  -----------  ----------  -----  -----  -------------  ------  ------  -------
 Ethernet48  53,54,55,56  4294967.3G   9100    N/A  fortyGigE0/48   trunk      up       up

 Ethernet32  13,14,15,16  4294967.3G   9100    N/A  fortyGigE0/32   trunk      up       up
```

**Status:** ✓ VS D1 configured for L2 VLAN 100 mode

### D2 (TX Generator - 192.168.100.172)

```bash
ssh admin@192.168.100.172
# Password: root@123

# Remove any existing L3 configuration
sudo config interface ip remove Ethernet0 10.0.0.1/24 2>/dev/null || true

# Create VLAN 100
sudo config vlan add 100

# Add interface to VLAN 100
sudo config vlan member add 100 Ethernet0 -u

# Bring interface up
sudo config interface startup Ethernet0

sudo config save -y
```

**Verification:**
```
+-----------+--------------+-----------+----------------+-------------+-----------------------+
|   VLAN ID | IP Address   | Ports     | Port Tagging   | Proxy ARP   | DHCP Helper Address   |
+===========+==============+===========+================+=============+=======================+
|       100 |              | Ethernet0 | untagged       | disabled    |                       |
+-----------+--------------+-----------+----------------+-------------+-----------------------+

  Interface        Lanes       Speed    MTU    FEC         Alias    Vlan    Oper    Admin
-----------  -----------  ----------  -----  -----  ------------  ------  ------  -------
  Ethernet0  25,26,27,28  4294967.3G   9100    N/A  fortyGigE0/0   trunk      up       up
```

**Status:** ✓ VS D2 configured for L2 VLAN 100 mode

### D3 (RX Receiver - 192.168.100.178)

```bash
ssh admin@192.168.100.178
# Password: root@123

# Remove any existing L3 configuration
sudo config interface ip remove Ethernet32 20.0.0.2/24 2>/dev/null || true

# Create VLAN 100
sudo config vlan add 100

# Add interface to VLAN 100
sudo config vlan member add 100 Ethernet32 -u

# Bring interface up
sudo config interface startup Ethernet32

sudo config save -y
```

**Verification:**
```
+-----------+--------------+------------+----------------+-------------+-----------------------+
|   VLAN ID | IP Address   | Ports      | Port Tagging   | Proxy ARP   | DHCP Helper Address   |
+===========+==============+============+================+=============+=======================+
|       100 |              | Ethernet32 | untagged       | disabled    |                       |
+-----------+--------------+------------+----------------+-------------+-----------------------+

  Interface        Lanes       Speed    MTU    FEC          Alias    Vlan    Oper    Admin
-----------  -----------  ----------  -----  -----  -------------  ------  ------  -------
 Ethernet32  13,14,15,16  4294967.3G   9100    N/A  fortyGigE0/32   trunk      up       up
```

**Status:** ✓ VS D3 configured for L2 VLAN 100 mode

---

## Step 2: ACL Configuration on DUT (CONFIG_DB Approach)

### 2.1 Create L2 ACL with Multicast MAC Rule

```bash
ssh admin@192.168.100.122

# Remove any previous ACL tables
sudo config acl remove table L2_ACL_VS_TEST 2>/dev/null || true
sudo config acl remove table L2_ACL_TEST_MULTICAST 2>/dev/null || true

# Create L2 ACL table for multicast test
sudo config acl add table L2_ACL_MULTICAST_VS L2 -p Ethernet48 -s ingress

# Rule 10: FORWARD multicast traffic to 01:00:5E:00:00:01 (IPv4 multicast)
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_MULTICAST_VS|RULE_10" "PRIORITY" "10"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_MULTICAST_VS|RULE_10" "PACKET_ACTION" "FORWARD"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_MULTICAST_VS|RULE_10" "DST_MAC" "01:00:5E:00:00:01/FF:FF:FF:FF:FF:FF"

# Rule 20: DROP all other traffic
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_MULTICAST_VS|RULE_20" "PRIORITY" "20"
sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_MULTICAST_VS|RULE_20" "PACKET_ACTION" "DROP"

sudo config save -y
```

### 2.2 Verify ACL Configuration

```bash
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_TABLE|L2_ACL_MULTICAST_VS"
```

**Output:**
```
{'policy_desc': 'L2_ACL_MULTICAST_VS', 'ports@': 'Ethernet48', 'stage': 'ingress', 'type': 'L2'}
```

```bash
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_MULTICAST_VS|RULE_10"
```

**Output:**
```
{'PRIORITY': '10', 'PACKET_ACTION': 'FORWARD', 'DST_MAC': '01:00:5E:00:00:01/FF:FF:FF:FF:FF:FF'}
```

```bash
sudo sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_MULTICAST_VS|RULE_20"
```

**Output:**
```
{'PRIORITY': '20', 'PACKET_ACTION': 'DROP'}
```

**Status:** ✓ ACL configuration saved to CONFIG_DB successfully

**NOTE:** klish iSCLI commands (`mac access-list`, `permit any host`, `mac access-group`) referenced in `/home/hp_test/Athira/acl_iscli_commands.md` are **NOT available** on this platform. Using CONFIG_DB approach as alternative.

---

## Step 3: RX Device Setup

```bash
ssh admin@192.168.100.178

sudo rm -f /tmp/l2_n02_vs_test.pcap
sudo timeout 60 tcpdump -i Ethernet32 'ether dst 01:00:5e:00:00:01' -w /tmp/l2_n02_vs_test.pcap > /dev/null 2>&1 &
```

**Status:** ✓ tcpdump started on VS D3:Ethernet32, listening for multicast dst MAC `01:00:5e:00:00:01`

---

## Step 4: TX Traffic Generation

```bash
ssh admin@192.168.100.172

cat > /tmp/l2_n02_vs_traffic.py << 'EOF'
#!/usr/bin/env python3
"""
L2-N02 VS: Multicast Destination MAC Test
Sends 10 multicast frames to 01:00:5E:00:00:01 (IPv4 multicast)
"""

from scapy.all import Ether, IP, Raw, sendp
import time

iface = "Ethernet0"
src_mac = "00:aa:aa:aa:aa:01"
dst_mac = "01:00:5e:00:00:01"  # IPv4 multicast MAC
total_packets = 10

print(f"[+] L2-N02 VS: Multicast Destination MAC Test")
print(f"    Src MAC: {src_mac}")
print(f"    Dst MAC: {dst_mac} (IPv4 Multicast)")
print(f"    Interface: {iface}")
print(f"    Total Packets: {total_packets}")
print()

pkt = Ether(src=src_mac, dst=dst_mac) / \
      IP(src="10.0.0.1", dst="224.0.0.1") / \
      Raw(load="L2-N02-VS-TEST-MULTICAST")

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

chmod +x /tmp/l2_n02_vs_traffic.py
sudo python3 /tmp/l2_n02_vs_traffic.py
```

**Output:**
```
[+] L2-N02 VS: Multicast Destination MAC Test
    Src MAC: 00:aa:aa:aa:aa:01
    Dst MAC: 01:00:5e:00:00:01 (IPv4 Multicast)
    Interface: Ethernet0
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
ssh admin@192.168.100.178

sudo killall tcpdump
sleep 2

# Verify captured multicast packets
sudo python3 -c "from scapy.all import rdpcap; packets = rdpcap('/tmp/l2_n02_vs_test.pcap'); print(f'Captured: {len(packets)} multicast packets')"

# Packet details
sudo python3 << 'EOF'
from scapy.all import rdpcap, Ether
try:
    packets = rdpcap('/tmp/l2_n02_vs_test.pcap')
    print(f"Total packets captured: {len(packets)}")
    if packets:
        for i, pkt in enumerate(packets[:5], 1):
            if Ether in pkt:
                print(f"  Packet {i}: src={pkt[Ether].src}, dst={pkt[Ether].dst}")
except Exception as e:
    print(f"Error: {e}")
EOF
```

**Output:**
```
Captured: 10 multicast packets

Total packets captured: 10
  Packet 1: src=00:aa:aa:aa:aa:01, dst=01:00:5e:00:00:01
  Packet 2: src=00:aa:aa:aa:aa:01, dst=01:00:5e:00:00:01
  Packet 3: src=00:aa:aa:aa:aa:01, dst=01:00:5e:00:00:01
  Packet 4: src=00:aa:aa:aa:aa:01, dst=01:00:5e:00:00:01
  Packet 5: src=00:aa:aa:aa:aa:01, dst=01:00:5e:00:00:01
```

**Result:** ✓ **SUCCESS - 10 out of 10 multicast packets received (100% delivery rate)**

---

## Additional Verification: Baseline Connectivity Test

To verify if multicast forwarding is enabled by default on VS (independent of ACL), the ACL was removed and a baseline test performed.

### Remove ACL

```bash
ssh admin@192.168.100.122

sudo config acl remove table L2_ACL_MULTICAST_VS 2>/dev/null || true
sudo config acl remove table L2_ACL_TEST_PERMIT 2>/dev/null || true
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
ssh admin@192.168.100.178
sudo timeout 15 tcpdump -i Ethernet32 'ether dst 01:00:5e:00:00:01' -w /tmp/l2_n02_vs_baseline.pcap > /dev/null 2>&1 &

# On D2: Send 1 multicast packet
ssh admin@192.168.100.172
sudo python3 -c "from scapy.all import Ether, IP, Raw, sendp; pkt = Ether(src='00:aa:aa:aa:aa:01', dst='01:00:5e:00:00:01') / IP(src='10.0.0.1', dst='224.0.0.1') / Raw(load='BASELINE-TEST'); sendp(pkt, iface='Ethernet0', verbose=False); print('[✓] Sent 1 multicast packet (no ACL)')"

# On D3: Verify
ssh admin@192.168.100.178
sudo killall tcpdump 2>/dev/null
sleep 1
sudo python3 -c "from scapy.all import rdpcap; pkts = rdpcap('/tmp/l2_n02_vs_baseline.pcap'); print(f'Baseline VS (no ACL): {len(pkts)} multicast packets captured')"
```

**Output:**
```
[✓] Sent 1 multicast packet (no ACL)
Baseline VS (no ACL): 1 multicast packets captured
```

**Conclusion:** Multicast traffic is forwarded on VS platform **both with and without ACL**, indicating multicast forwarding is enabled by default.

---

## Test Results Summary

| Test Scenario | TX Packets | RX Packets | Delivery Rate | Result |
|---------------|------------|------------|---------------|---------|
| **With L2 ACL (FORWARD multicast)** | 10 | 10 | 100% | ✓ PASS |
| **Without ACL (Baseline)** | 1 | 1 | 100% | ✓ PASS |

---

## Analysis and Conclusions

### Test Result: ✓ **PASS with Caveats**

The L2-N02 test on VS platform shows 100% multicast packet delivery, but the underlying reason requires further analysis:

### Scenario 1: L2 ACL is Working on VS

If the L2 ACL FORWARD rule for multicast MAC `01:00:5E:00:00:01` is functioning properly:
- ✓ Rule 10 (FORWARD specific multicast) is being enforced
- ✓ Multicast packets matching the rule are permitted
- ✓ This would indicate L2 ACL functionality on VS platform

### Scenario 2: Multicast Flooding Enabled by Default

If multicast forwarding is enabled by default on VS (independent of ACL):
- Multicast traffic would pass through regardless of ACL rules
- The 100% delivery rate would be due to platform behavior, not ACL enforcement
- **Evidence supporting this**: Baseline test (no ACL) also shows 100% delivery rate

### Most Likely Conclusion: Multicast Flooding Enabled on VS

**Evidence:**
1. **With L2 ACL**: 10 multicast packets received (100%) ✓
2. **Without ACL (baseline)**: 1 multicast packet received (100%) ✓

Since the baseline test (without ACL) also achieves 100% delivery, this indicates that **multicast forwarding is enabled by default on the VS platform**, independent of L2 ACL configuration.

**This differs significantly from hardware behavior** where multicast was blocked regardless of ACL configuration (see L2-N02 hardware log).

### Platform Comparison: VS vs Hardware

| Aspect | VS (Virtual Switch) | Hardware (Broadcom ASIC) |
|--------|---------------------|--------------------------|
| **Multicast Forwarding** | ✓ Enabled by default | ✗ Disabled by default |
| **With L2 ACL (FORWARD)** | 10/10 packets (100%) | 0/10 packets (0%) |
| **Without ACL (Baseline)** | 1/1 packets (100%) | 0/1 packets (0%) |
| **Root Cause** | Multicast flooding enabled | Multicast + L2 ACL both broken |

---

## Key Findings

### 1. Multicast Forwarding on VS

- **VS platform forwards multicast traffic by default** in VLAN 100 L2 switching mode
- This behavior differs from hardware platforms where multicast requires additional IGMP/multicast configuration
- Multicast MAC addresses (01:00:5E:xx:xx:xx) are flooded across VLAN 100 members

### 2. L2 ACL Configuration Successful

- L2 ACL table and rules configured successfully in CONFIG_DB on VS
- ACL bound to Ethernet48 ingress without errors
- Rule structure: Rule 10 FORWARD multicast, Rule 20 DROP others

### 3. Test Inconclusiveness

Due to VS platform's default multicast forwarding behavior, **this test cannot definitively prove whether L2 ACL functionality is working** on VS. The 100% delivery rate could be due to:
- L2 ACL FORWARD rule working correctly (desired)
- Default multicast flooding bypassing ACL (actual behavior observed)

**Recommendation:** To properly test L2 ACL on VS, use **unicast MAC filtering** (L2-01, L2-N01) where baseline traffic is blocked without explicit ACL permit rules.

### 4. Platform Limitations Identified

**klish iSCLI MAC ACL Commands NOT Available:**

The following commands from `/home/hp_test/Athira/acl_iscli_commands.md` are **NOT implemented** on VS platform:

```bash
configure terminal
mac access-list L2_ACL_TEST_MULTICAST
permit any host 01:00:5e:00:00:01  # Command not recognized
deny any any                       # Command not recognized
exit
interface Ethernet48
mac access-group L2_ACL_TEST_MULTICAST in  # Command not recognized
```

**Workaround:** Use CONFIG_DB approach with `config acl` and `sonic-db-cli CONFIG_DB HSET` commands.

---

## Hardware vs VS Comparison Summary

### Test Execution

| Aspect | Hardware (Broadcom ASIC) | VS (Virtual Switch) |
|--------|--------------------------|---------------------|
| **VLAN Configuration** | ✓ Successful | ✓ Successful |
| **ACL Configuration** | ✓ CONFIG_DB successful | ✓ CONFIG_DB successful |
| **Traffic Generation** | ✓ 10 packets sent | ✓ 10 packets sent |
| **With ACL Result** | ✗ 0 packets received (0%) | ✓ 10 packets received (100%) |
| **Without ACL Result** | ✗ 0 packets received (0%) | ✓ 1 packet received (100%) |

### Root Causes

| Platform | Primary Issue | Secondary Issue |
|----------|---------------|-----------------|
| **Hardware** | L2 ACL non-functional via CONFIG_DB | Multicast forwarding disabled |
| **VS** | Test inconclusive (multicast always forwarded) | Cannot verify L2 ACL functionality |

---

## Recommendations

### For L2 ACL Validation on VS

1. **Test unicast MAC filtering instead** (L2-01, L2-02, L2-N01):
   - Unicast traffic is not flooded by default
   - Can properly validate ACL FORWARD vs DROP behavior
   - More reliable for L2 ACL functionality testing

2. **Disable multicast flooding** (if possible):
   - Configure IGMP snooping to control multicast behavior
   - Re-run L2-N02 test after disabling default multicast flooding
   - This would provide definitive L2 ACL validation

### For Hardware Platform

1. **Investigate L2 ACL root cause:**
   - Check orchagent logs for ACL programming errors
   - Verify SAI layer ACL support for L2/MAC filtering
   - Review ASIC_DB ACL entries

2. **Enable multicast forwarding:**
   - Configure IGMP snooping on VLAN 100
   - Investigate multicast routing requirements
   - Check if multicast flooding needs to be enabled

---

## Configuration Reference

### CONFIG_DB ACL Entries (Verified on VS)

```bash
# ACL Table
sonic-db-cli CONFIG_DB HGETALL "ACL_TABLE|L2_ACL_MULTICAST_VS"
# Output: {'policy_desc': 'L2_ACL_MULTICAST_VS', 'ports@': 'Ethernet48', 'stage': 'ingress', 'type': 'L2'}

# ACL Rule 10 (Permit Multicast)
sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_MULTICAST_VS|RULE_10"
# Output: {'PRIORITY': '10', 'PACKET_ACTION': 'FORWARD', 'DST_MAC': '01:00:5E:00:00:01/FF:FF:FF:FF:FF:FF'}

# ACL Rule 20 (Deny All Others)
sonic-db-cli CONFIG_DB HGETALL "ACL_RULE|L2_ACL_MULTICAST_VS|RULE_20"
# Output: {'PRIORITY': '20', 'PACKET_ACTION': 'DROP'}
```

---

**Document Version:** 1.0
**Last Updated:** 2026-03-19
**Status:** Test PASS (100% delivery) but inconclusive for L2 ACL validation due to default multicast forwarding
**Platform Tested:** VS (Virtual Switch) SONiC
**Related Test Cases:**
- L2-N02 Hardware Test (BLOCKED - multicast + L2 ACL both non-functional)
- L2-N01 (unicast MAC case sensitivity - better for L2 ACL validation)

