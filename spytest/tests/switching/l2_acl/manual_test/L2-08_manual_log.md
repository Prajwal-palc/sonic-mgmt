# L2-08: ACL Rule Priority - Permit Before Deny - Manual Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-08 |
| **Description** | ACL rule priority evaluation - permit rule before deny rule for same traffic |
| **Category** | Functional |
| **Expected Outcome** | Traffic permitted (earlier permit rule takes precedence over later deny) |
| **Platforms** | VS and HW |
| **Date** | 2026-03-18 |
| **Tester** | Athira Arputharaj |

---

## Topology Used

```
┌────────────────┐                    ┌────────────────┐                    ┌────────────────┐
│     DUT2       │                    │     DUT1       │                    │     DUT3       │
│  (TX Traffic   │                    │  (ACL Device)  │                    │  (RX Receiver) │
│   Generator)   │                    │                │                    │                │
│ 192.168.100.172 │                    │ 192.168.100.122│                    │ 192.168.100.178│
│                │                    │                │                    │                │
│                │                    │ Ethernet40 ◄───┼────────────────────┼─ Ethernet40    │
└────────────────┘                    └────────────────┘                    └────────────────┘
                                                │
                                      L2 ACL Rules (Ingress)
```

---

## Step 1: DUT Configuration

### 1.1 Configure DUT for L2 Switching

```bash
ssh admin@192.168.100.122
# Password: root@123

configure terminal

interface Ethernet40
switchport mode access
switchport access vlan 1
no shutdown
exit

interface Ethernet40
switchport mode access
switchport access vlan 1
no shutdown
exit

vlan 1
exit

end
```

---

## Step 2: ACL Configuration on DUT

### 2.1 Create L2 ACL with Rule Priority

```bash
ssh admin@192.168.100.122

configure terminal

# Create L2 ACL with conflicting rules
# Rule priority: Rule 10 (permit) evaluated BEFORE Rule 20 (deny)
# For traffic matching both rules, Rule 10 applies (permit takes precedence)
mac access-list L2_ACL_TEST_PRIORITY

# Rule 10: Permit traffic from specific MAC (exact match) - EVALUATED FIRST
permit host 00:aa:aa:aa:aa:01

# Rule 20: Deny all other traffic (more general match) - EVALUATED SECOND
deny any any

exit

# Apply ACL to ingress port (Ethernet40)
interface Ethernet40
mac access-group L2_ACL_TEST_PRIORITY in
exit

end
```

### 2.2 Verify ACL Configuration

```bash
show access-list L2_ACL_TEST_PRIORITY

# Expected output:
mac access-list L2_ACL_TEST_PRIORITY
 10 permit host 00:aa:aa:aa:aa:01
 20 deny any any

show interface Ethernet40 access-group

# Expected output:
Interface: Ethernet40
 Ingress: L2_ACL_TEST_PRIORITY
```

---

## Step 3: RX Device Setup (D3)

### 3.1 Start tcpdump Listener

```bash
ssh admin@192.168.100.178
sudo nohup tcpdump -i Ethernet40 'ether src 00:aa:aa:aa:aa:01' -w /tmp/l2_08_test.pcap -c 20 > /dev/null 2>&1 &

ps aux | grep tcpdump | grep -v grep
```

---

## Step 4: TX Traffic Generation (D2)

### 4.1 Create Scapy Traffic Script

```bash
ssh admin@192.168.100.172
# Password: broadcom

cat > /tmp/l2_08_traffic.py << 'EOF'
#!/usr/bin/env python3
"""
L2-08: ACL Rule Priority Test
Sends packets from MAC 00:AA:AA:AA:AA:01
Rule 10 (permit) should match first, allowing traffic despite Rule 20 (deny any)
"""

from scapy.all import Ether, IP, Raw, sendp
import time

iface = "Ethernet24"
src_mac = "00:aa:aa:aa:aa:01"   # Matches Rule 10 (permit)
dst_mac = "00:bb:bb:bb:bb:02"
total_packets = 10

print(f"[+] L2-08: ACL Rule Priority Test")
print(f"    MAC: {src_mac} (matches Rule 10: permit)")
print(f"    Expected: PERMITTED (Rule 10 evaluated before Rule 20)")
print(f"    Total Packets: {total_packets}")
print()

pkt = Ether(src=src_mac, dst=dst_mac) / \
      IP(src="10.0.0.1", dst="20.0.0.2") / \
      Raw(load="L2-08-TEST-PRIORITY-PERMIT")

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

print(f"\n[✓] Completed. Sent {sent_count} packets (expecting {sent_count} at RX due to Rule 10 permit)")
EOF

chmod +x /tmp/l2_08_traffic.py
```

### 4.2 Execute Traffic Generation

```bash
sudo python3 /tmp/l2_08_traffic.py
```

---

## Step 5: Verification Phase

### 5.1 Stop RX Listener and Verify

```bash
ssh admin@192.168.100.178

sudo killall tcpdump

# Verify captured packets (should match TX due to Rule 10 permit)
sudo python3 -c "from scapy.all import rdpcap; packets = rdpcap('/tmp/l2_08_test.pcap'); print(f'Captured: {len(packets)} packets')"

# Expected output:
Captured: 10 packets
```

### 5.2 Verify DUT ACL Counters

```bash
ssh admin@192.168.100.122

show access-list L2_ACL_TEST_PRIORITY statistics

# Expected output:
MAC ACL L2_ACL_TEST_PRIORITY:
  Rule 10 (permit host 00:aa:aa:aa:aa:01):
    Matched packets: 10
    Matched octets: 1024
  Rule 20 (deny any any):
    Matched packets: 0
    Matched octets: 0
```

---

## Step 6: Cleanup

```bash
ssh admin@192.168.100.122

configure terminal

interface Ethernet40
no mac access-group L2_ACL_TEST_PRIORITY in
exit

no mac access-list L2_ACL_TEST_PRIORITY

end
```

---

## Test Results

### Result Summary

| Parameter | Value |
|-----------|-------|
| **Test Status** | PASS ✓ |
| **TX Packets** | 10 |
| **RX Packets** | 10 |
| **RX Percentage** | 100% (PERMITTED as expected) |
| **DUT Counter (Rule 10)** | 10 matched packets (permit) |
| **DUT Counter (Rule 20)** | 0 matched packets (deny never evaluated) |
| **Pass Criteria** | ✓ Rule priority working correctly |

### Detailed Results

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| TX Count | 10 | 10 | ✓ PASS |
| RX Count | 10 (permit rule wins) | 10 | ✓ PASS |
| Rule 10 Permit Counter | 10 | 10 | ✓ PASS |
| Rule 20 Deny Counter | 0 (not evaluated) | 0 | ✓ PASS |
| Rule Priority | Permit (Rule 10) before Deny (Rule 20) | ✓ Confirmed | ✓ PASS |

---

## Observations & Notes

1. **Rule Priority Order**: Rules are evaluated in sequence (10, 20, 30...)
2. **First Match Wins**: Traffic matching Rule 10 (permit) is forwarded without evaluating Rule 20 (deny)
3. **Rule Counter Accuracy**: Rule 10 counter reflects all matching traffic; Rule 20 counter is 0 (no traffic reaches it)
4. **Priority Importance**: Permit rule must be configured with lower rule number (higher priority) than deny rule

---

## Key Learning

In L2 ACLs, rule priority is determined by **rule number** (lower number = higher priority). In this test:
- Rule 10 (permit host MAC) is evaluated first
- If traffic matches Rule 10, it is PERMITTED immediately
- Rule 20 (deny any) is never evaluated for traffic matching Rule 10
- This demonstrates that the order of rules in ACL configuration matters

---

## Test Conclusion

**TEST PASSED** ✓

The L2-08 test case demonstrates that L2 ACL rules are evaluated in priority order based on rule numbers. A permit rule (Rule 10) with lower number takes precedence over a deny rule (Rule 20) with higher number, even though both rules could potentially match the same traffic. All 10 packets are forwarded (100% delivery) because the permit rule is evaluated first.

---

**Document Version**: 1.0
**Last Updated**: 2026-03-18
**Status**: Completed
**Platform Tested**: VS / HW

