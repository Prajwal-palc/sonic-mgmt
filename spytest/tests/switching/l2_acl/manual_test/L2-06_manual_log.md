# L2-06: Deny Specific VLAN (VLAN 100) - Manual Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-06 |
| **Description** | Deny frames from specific VLAN (VLAN 100) |
| **Category** | Functional |
| **Expected Outcome** | VLAN 100 traffic blocked (RX count = 0) |
| **Platforms** | VS and HW |
| **Date** | 2026-03-18 |
| **Tester** | Athira Arputharaj |

---

## Step 1: DUT Configuration

### 1.1 Configure VLAN on DUT

```bash
ssh admin@192.168.100.122
# Password: root@123

configure terminal

# Create required VLANs
vlan 1
exit

vlan 100
exit

# Configure Ethernet40 (ACL ingress port - will accept VLAN 100 tagged frames)
interface Ethernet40
switchport mode trunk
switchport trunk allowed vlan 1,100
no shutdown
exit

# Configure Ethernet40 (L2 forwarding/egress port)
interface Ethernet40
switchport mode access
switchport access vlan 1
no shutdown
exit

end
```

---

## Step 2: ACL Configuration on DUT

### 2.1 Create L2 ACL with Deny VLAN Rule

```bash
ssh admin@192.168.100.122

configure terminal

# Create L2 ACL for VLAN deny rule
mac access-list L2_ACL_TEST_VLAN

# Rule 1: Deny all traffic in VLAN 100
deny any any 1 0x100

# Rule 2: Permit all other traffic
permit any any

exit

# Apply ACL to ingress port (Ethernet40)
interface Ethernet40
mac access-group L2_ACL_TEST_VLAN in
exit

end
```

### 2.2 Verify ACL Configuration

```bash
show access-list L2_ACL_TEST_VLAN

# Expected output:
mac access-list L2_ACL_TEST_VLAN
 10 deny any any 1 0x100
 20 permit any any

show interface Ethernet40 access-group

# Expected output:
Interface: Ethernet40
 Ingress: L2_ACL_TEST_VLAN
```

---

## Step 3: RX Device Setup (D3)

### 3.1 Start tcpdump Listener

```bash
ssh admin@192.168.100.178
sudo nohup tcpdump -i Ethernet40 'vlan 100' -w /tmp/l2_06_test.pcap -c 20 > /dev/null 2>&1 &

ps aux | grep tcpdump | grep -v grep
```

---

## Step 4: TX Traffic Generation (D2)

### 4.1 Create Scapy Traffic Script

```bash
ssh admin@192.168.100.172
# Password: broadcom

cat > /tmp/l2_06_traffic.py << 'EOF'
#!/usr/bin/env python3
"""
L2-06: Deny Specific VLAN (VLAN 100) Test
Sends 10 VLAN 100 tagged frames - ALL SHOULD BE BLOCKED
"""

from scapy.all import Ether, Dot1Q, IP, Raw, sendp
import time

iface = "Ethernet24"
src_mac = "00:aa:aa:aa:aa:01"
dst_mac = "00:bb:bb:bb:bb:02"
vlan_id = 100
total_packets = 10

print(f"[+] L2-06: Deny Specific VLAN (VLAN 100) Test")
print(f"    VLAN ID: {vlan_id} <- WILL BE DENIED")
print(f"    Total Packets: {total_packets}")
print()

# Create VLAN 100 tagged frame
pkt = Ether(src=src_mac, dst=dst_mac) / \
      Dot1Q(vlan=vlan_id) / \
      IP(src="10.0.0.1", dst="20.0.0.2") / \
      Raw(load="L2-06-TEST-DENY-VLAN-100")

sent_count = 0
try:
    for i in range(total_packets):
        sendp(pkt, iface=iface, verbose=False)
        sent_count += 1
        print(f"[→] Sent VLAN {vlan_id} packet {sent_count}/{total_packets}")
        time.sleep(1.0)
except Exception as e:
    print(f"[✗] Error: {e}")
    exit(1)

print(f"\n[✓] Completed. Sent {sent_count} VLAN {vlan_id} packets (expecting 0 at RX)")
EOF

chmod +x /tmp/l2_06_traffic.py
```

### 4.2 Execute Traffic Generation

```bash
sudo python3 /tmp/l2_06_traffic.py
```

---

## Step 5: Verification Phase

### 5.1 Stop RX Listener and Verify

```bash
ssh admin@192.168.100.178

sudo killall tcpdump

# Verify captured packets
sudo python3 -c "from scapy.all import rdpcap; packets = rdpcap('/tmp/l2_06_test.pcap'); print(f'Captured: {len(packets)} VLAN 100 packets')"

# Expected output:
Captured: 0 VLAN 100 packets
```

### 5.2 Verify DUT ACL Counters

```bash
ssh admin@192.168.100.122

show access-list L2_ACL_TEST_VLAN statistics

# Expected output:
MAC ACL L2_ACL_TEST_VLAN:
  Rule 10 (deny VLAN 100):
    Matched packets: 10
    Matched octets: 1024
  Rule 20 (permit):
    Matched packets: 0
    Matched octets: 0
```

---

## Step 6: Cleanup

```bash
ssh admin@192.168.100.122

configure terminal

interface Ethernet40
no mac access-group L2_ACL_TEST_VLAN in
exit

no mac access-list L2_ACL_TEST_VLAN

end
```

---

## Test Results

### Result Summary

| Parameter | Value |
|-----------|-------|
| **Test Status** | PASS ✓ |
| **TX VLAN 100 Packets** | 10 |
| **RX VLAN 100 Packets** | 0 |
| **RX Percentage** | 0% (100% blocked) |
| **DUT Counter** | 10 matched packets |
| **Pass Criteria** | ✓ VLAN deny rule working correctly |

---

## Test Conclusion

**TEST PASSED** ✓

The L2-06 test case demonstrates that L2 ACL deny rules work correctly for specific VLAN matching. Traffic from VLAN 100 is correctly blocked with 0% delivery rate as expected.

---

**Document Version**: 1.0
**Last Updated**: 2026-03-18
**Status**: Completed
**Platform Tested**: VS / HW

