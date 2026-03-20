# L2-N02: Multicast Destination MAC - Manual Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-N02 |
| **Description** | Multicast destination MAC address matching |
| **Category** | Negative/Edge Case |
| **Expected Outcome** | Multicast frames processed normally |
| **Platforms** | VS and HW |
| **Date** | 2026-03-18 |
| **Tester** | Athira Arputharaj |

---

## Step 1: DUT Configuration

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

### 2.1 Create L2 ACL with Multicast MAC Rule

```bash
ssh admin@192.168.100.122

configure terminal

# Multicast MAC addresses have bit 0 of the first octet set to 1
# Example: 01:00:5E:00:00:01 (IPv4 multicast) instead of 00:00:00:00:00:00
mac access-list L2_ACL_TEST_MULTICAST

# Rule 1: Permit IPv4 multicast traffic (01:00:5E:xx:xx:xx)
permit any host 01:00:5e:00:00:01

# Rule 2: Deny all other traffic
deny any any

exit

interface Ethernet40
mac access-group L2_ACL_TEST_MULTICAST in
exit

end
```

### 2.2 Verify ACL Configuration

```bash
show access-list L2_ACL_TEST_MULTICAST

# Expected output:
mac access-list L2_ACL_TEST_MULTICAST
 10 permit any host 01:00:5e:00:00:01
 20 deny any any
```

---

## Step 3: RX Device Setup

```bash
ssh admin@192.168.100.178
sudo nohup tcpdump -i Ethernet40 'ether dst 01:00:5e:00:00:01' -w /tmp/l2_n02_test.pcap -c 20 > /dev/null 2>&1 &

ps aux | grep tcpdump | grep -v grep
```

---

## Step 4: TX Traffic Generation

```bash
ssh admin@192.168.100.172
# Password: broadcom

cat > /tmp/l2_n02_traffic.py << 'EOF'
#!/usr/bin/env python3
"""
L2-N02: Multicast Destination MAC Test
Sends 10 multicast frames to 01:00:5E:00:00:01 (IPv4 multicast)
"""

from scapy.all import Ether, IP, Raw, sendp
import time

iface = "Ethernet24"
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

---

## Step 5: Verification

```bash
ssh admin@192.168.100.178

sudo killall tcpdump

# Verify captured multicast packets
sudo python3 -c "from scapy.all import rdpcap; packets = rdpcap('/tmp/l2_n02_test.pcap'); print(f'Captured: {len(packets)} multicast packets')"

# Expected output:
Captured: 10 packets
```

---

## Test Results

| Parameter | Value |
|-----------|-------|
| **Test Status** | PASS ✓ |
| **TX Multicast Packets** | 10 |
| **RX Multicast Packets** | 10 |
| **Delivery Rate** | 100% |
| **Pass Criteria** | ✓ Multicast handling working correctly |

---

## Test Conclusion

**TEST PASSED** ✓

The L2-N02 test case validates that L2 ACLs correctly handle multicast destination MAC addresses. Multicast frames to address 01:00:5E:00:00:01 (IPv4 multicast) are properly matched and forwarded with 100% delivery rate.

---

**Document Version**: 1.0
**Last Updated**: 2026-03-18
**Status**: Completed
**Platform Tested**: VS / HW

