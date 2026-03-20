# L2 ACL Manual Testing Guide

## Overview

This guide provides step-by-step instructions for manually testing L2 (Layer 2) Access Control Lists on SONiC switches. The tests follow the topology specified in `testbeds/testbed_acl.yaml` with three DUTs: a TX traffic generator (D2), a DUT with ACL rules (D1), and an RX traffic receiver (D3).

**Test Plan Reference**: `tests/switching/l2_acl/docs/acl-l2.md` (19 test cases total)

---

## Topology Overview

```
┌────────────────┐                    ┌────────────────┐                    ┌────────────────┐
│     DUT2       │                    │     DUT1       │                    │     DUT3       │
│  (TX Traffic   │                    │  (ACL Device)  │                    │  (RX Receiver) │
│   Generator)   │                    │                │                    │                │
│ 192.168.100.67 │                    │ 192.168.100.190│                    │ 192.168.100.134│
│                │                    │                │                    │                │
│ Ethernet24 ◄───┼────────────────────┼─ Ethernet40    │                    │                │
│ (Raw Scapy)    │   L2 Switching     │ (ACL Ingress)  │                    │                │
│                │                    │                │                    │                │
│                │                    │ Ethernet24 ────┼────────────────────┼──► Ethernet24  │
│                │                    │  (L2 Switch)   │   L2 Switching     │  (RX Receiver) │
└────────────────┘                    └────────────────┘                    └────────────────┘

DUT Switching Path: Ethernet24(RX) → L2 ACL → Bridging → Ethernet24(TX)
```

### Device Configuration

| Device | Role | Management IP | Interface | Mode | Notes |
|--------|------|--------------|-----------|------|-------|
| D1 | DUT (ACL Device) | 192.168.100.190 | Ethernet40 | Switchport (L2) | ACL Ingress Port |
| D1 | DUT (ACL Device) | 192.168.100.190 | Ethernet24 | Switchport (L2) | L2 Switch Port |
| D2 | TX Traffic Gen | 192.168.100.67  | Ethernet24 | Switchport (L2) | Traffic Source |
| D3 | RX Traffic Sink | 192.168.100.134 | Ethernet24 | Switchport (L2) | Traffic Sink |

---

## Prerequisites

### Before Testing (One-Time Setup)

#### 1. Verify Device Connectivity
```bash
# Test SSH connectivity to all devices
ping 192.168.100.190    # D1 (DUT)
ping 192.168.100.67     # D2 (TX)
ping 192.168.100.134    # D3 (RX)

# SSH to each device
ssh admin@192.168.100.190   # D1
ssh admin@192.168.100.67    # D2
ssh admin@192.168.100.134   # D3
```

#### 2. Verify Scapy Installation on TX/RX Devices

**On D2 (TX Device):**
```bash
sudo python3 -m pip install scapy --break-system-packages
python3 -c "from scapy.all import *; print(f'Scapy {SCAPY_VERSION} OK')"
```

**On D3 (RX Device):**
```bash
sudo python3 -m pip install scapy --break-system-packages
sudo apt-get install tcpdump
```

#### 3. Configure DUT Interfaces for L2 Switching

**On D1 (DUT):**
```bash
# Connect to DUT
ssh admin@192.168.100.190

# Configure Ethernet40 (TX ingress port)
configure terminal
interface Ethernet40
switchport mode access
switchport access vlan 1
no shutdown
exit

# Configure Ethernet24 (RX egress port)
interface Ethernet24
switchport mode access
switchport access vlan 1
no shutdown
exit

# Create VLAN 1 (if not exists)
vlan 1
exit

# Exit configuration mode
end

# Verify configuration
show interface Ethernet40
show interface Ethernet24
show vlan brief
```

#### 4. Verify Port Status on DUT

```bash
# Verify ports are UP
show interface status

# Expected output:
# Ethernet40    Eth10 routed  up   up   QSFP28
# Ethernet24    Eth6  routed  up   up   SFP28
```

---

## Test Case Categories

### Functional Test Cases (8 cases)
- **L2-01**: Permit exact source MAC
- **L2-02**: Deny exact source MAC
- **L2-03**: Deny exact destination MAC
- **L2-04**: Deny broadcast destination MAC
- **L2-05**: Deny EtherType ARP (0x0806)
- **L2-06**: Deny specific VLAN (VLAN 100)
- **L2-07**: Permit VLAN 10, deny VLAN 200
- **L2-08**: ACL rule priority — permit before deny

### Negative/Edge Case Tests (3 cases)
- **L2-N01**: MAC case sensitivity
- **L2-N02**: Multicast destination MAC
- **L2-N03**: Invalid/corrupt MAC handling

### Robustness/Persistence Tests (8 cases)
- **L2-R01**: ACL rule persistence after DUT reboot
- **L2-R02**: ACL modification while traffic active
- **L2-R03**: Multiple ACL updates in rapid succession
- **L2-R04**: Concurrent traffic on denied/allowed MAC pairs
- **L2-R05**: ACL counter accuracy (1000+ packets)
- **L2-R06**: VLAN rule persistence across config changes
- **L2-R07**: ACL aging/timeout behavior
- **L2-R08**: Mixed permit/deny rules with same match criteria

---

## Manual Testing Workflow

### For Each Test Case:

1. **Preparation Phase**
   - Create/verify ACL configuration
   - Apply ACL rules to DUT Ethernet40 (ingress)
   - Verify configuration with `show access-list` commands

2. **Traffic Generation Phase**
   - Start RX listener on D3 using tcpdump
   - Send traffic from D2 using Scapy script
   - Capture timing and packet counts

3. **Verification Phase**
   - Verify DUT ACL hit counters
   - Verify RX packet count matches expected behavior
   - Check pass/fail criteria

4. **Cleanup Phase**
   - Remove ACL rules from DUT
   - Reset interface configurations
   - Verify baseline connectivity

---

## Pass/Fail Criteria

| ACL Action | Pass Condition |
|-----------|-----------------|
| **PERMIT** | RX count ≥ 90% of TX count |
| **DENY** | RX count = 0 (all packets dropped) |
| **Counter** | DUT ACL hit counter = TX packet count |

---

## Individual Test Case Procedures

Each test has its own detailed markdown file in this directory named:
```
{TEST_CASE_ID}_manual_log.md
```

### Example: L2-01 Test Case
- File: `L2-01_manual_log.md`
- Contains: Configuration, show outputs, traffic results, and pass/fail status

### Available Test Logs:
- `L2-01_manual_log.md` - Permit exact source MAC
- `L2-02_manual_log.md` - Deny exact source MAC
- `L2-03_manual_log.md` - Deny exact destination MAC
- `L2-04_manual_log.md` - Deny broadcast destination MAC
- `L2-05_manual_log.md` - Deny EtherType ARP
- `L2-06_manual_log.md` - Deny specific VLAN
- `L2-07_manual_log.md` - Permit VLAN 10, deny VLAN 200
- `L2-08_manual_log.md` - ACL rule priority
- `L2-N01_manual_log.md` - MAC case sensitivity
- `L2-N02_manual_log.md` - Multicast destination MAC
- `L2-N03_manual_log.md` - Invalid/corrupt MAC
- `L2-R01_manual_log.md` - ACL persistence after reboot
- `L2-R02_manual_log.md` - ACL modification during traffic
- `L2-R03_manual_log.md` - Rapid ACL updates
- `L2-R04_manual_log.md` - Concurrent traffic flows
- `L2-R05_manual_log.md` - Counter accuracy (1000+ packets)
- `L2-R06_manual_log.md` - VLAN rule persistence
- `L2-R07_manual_log.md` - MAC aging behavior
- `L2-R08_manual_log.md` - Mixed permit/deny rules

---

## Testing on VS and Hardware

### Virtual SONiC (VS) Testing
- Use virtual interfaces (veth pairs, namespace bridges)
- Faster iteration and parallel testing
- No hardware dependencies

**VS Topology Preparation:**
```bash
# Create virtual interfaces if using VS
# Connect to VS container/VM
docker exec -it sonic-vs bash  # If using Docker

# Or SSH to VS management IP
ssh admin@<VS_MGMT_IP>
```

### Hardware (HW) Testing
- Use physical hardware switches
- Real-world port configurations
- Hardware-specific quirks and behavior

**HW Topology Preparation:**
- Physically connect devices with Ethernet cables
- Verify link status: `show interface status`
- Same configuration steps as VS

---

## Scapy Traffic Scripts

### Basic L2 Frame Formats

**Untagged Frame (L2-01 to L2-05):**
```python
from scapy.all import Ether, IP, Raw, sendp
import time

# Source and destination MAC addresses
src_mac = "00:AA:AA:AA:AA:01"      # TX host MAC
dst_mac = "00:BB:BB:BB:BB:02"      # RX host MAC or broadcast

# Create L2 frame
pkt = Ether(src=src_mac, dst=dst_mac) / IP(src="10.0.0.1", dst="20.0.0.2") / Raw(load="test")

# Send on TX device interface
for i in range(10):
    sendp(pkt, iface="Ethernet24", verbose=False)
    time.sleep(0.05)
```

**Tagged Frame with VLAN (L2-06, L2-07):**
```python
from scapy.all import Ether, Dot1Q, IP, sendp

# VLAN 100 tagged frame
pkt = Ether(src="00:AA:AA:AA:AA:01", dst="00:BB:BB:BB:BB:02") / \
      Dot1Q(vlan=100) / \
      IP(src="10.0.0.1", dst="20.0.0.2")

sendp(pkt, iface="Ethernet24", verbose=False)
```

**ARP EtherType Frame (L2-05):**
```python
from scapy.all import Ether, ARP, sendp

# ARP packet (EtherType 0x0806)
pkt = Ether(src="00:AA:AA:AA:AA:01", dst="FF:FF:FF:FF:FF:FF") / \
      ARP(psrc="10.0.0.1", pdst="20.0.0.2")

sendp(pkt, iface="Ethernet24", verbose=False)
```

### RX Traffic Verification

**Using tcpdump on RX Device (D3):**
```bash
# Start capture
sudo tcpdump -i Ethernet24 -w /tmp/l2_acl_test.pcap -c 10 &

# Wait for traffic
sleep 2

# Stop capture (background process)
sudo killall tcpdump

# Verify captured packets
sudo tcpdump -r /tmp/l2_acl_test.pcap
```

**Using Scapy for packet analysis:**
```python
from scapy.all import rdpcap

# Read pcap file
packets = rdpcap("/tmp/l2_acl_test.pcap")
print(f"Captured {len(packets)} packets")

# Verify MAC addresses
for pkt in packets:
    print(f"Src: {pkt[Ether].src}, Dst: {pkt[Ether].dst}")
```

---

## Troubleshooting Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Permission denied" on SSH | SSH key not configured | Use `sshpass` or configure SSH keys |
| Scapy import error | Scapy not installed | `sudo pip3 install scapy --break-system-packages` |
| RX sees 0 packets (no ACL) | Port not in switchport mode | Configure: `switchport mode access` |
| RX sees 0 packets (with ACL) | ACL rule incorrect | Verify with `show access-list` |
| Port status DOWN | Cable not connected | Check physical connections |
| MAC address mismatch | Case sensitivity | DUT compares case-insensitively (both uppercase/lowercase OK) |
| VLAN tests fail | VLANs don't exist | Create: `vlan 100`, `vlan 200` |
| Counter mismatch | Timing issue | Increase packet count to 100+ for accuracy |

---

## Documentation Standards

### For Each Test Case Log:

Each `{TEST_CASE_ID}_manual_log.md` file includes:

1. **Test Case Header**
   - Test ID and description
   - Expected outcome
   - Platform: VS / HW / Both

2. **Configuration Section**
   - DUT ACL configuration commands
   - Show output verification

3. **Traffic Generation Section**
   - TX device Scapy script or command
   - RX device listener setup (tcpdump)
   - Timing and packet count

4. **Verification Section**
   - DUT show access-list output
   - RX packet capture results
   - Counter validation

5. **Result Section**
   - Pass/Fail status
   - Packet counts (TX vs RX)
   - Notes/observations

---

## Summary Checklist

- [ ] All three DUTs reachable via SSH
- [ ] Scapy installed on D2 (TX) and D3 (RX)
- [ ] DUT ports configured for L2 switching
- [ ] VLAN 1 configured on DUT
- [ ] VLANs 10, 100, 200 created for L2-06/L2-07 tests
- [ ] Port status shows UP for all involved interfaces
- [ ] Ready to start L2-01 test case

---

## References

- Test Plan: `/tests/switching/l2_acl/docs/acl-l2.md`
- Testbed: `/testbeds/testbed_acl.yaml`
- DUT Setup Guide: `/tests/switching/l2_acl/docs/l2_dut_setup.md`
- Host Setup Guide: `/tests/switching/l2_acl/docs/l2_host_setup.md`

---

**Document Version**: 1.0
**Last Updated**: 2026-03-18
**Status**: Ready for Manual Testing

