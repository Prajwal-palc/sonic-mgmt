# L2 ACL Test Implementation Guide

**Date**: 2026-03-13
**Status**: ✅ IMPLEMENTATION READY
**Test Framework**: SPyTest (3-DUT Native SONiC)
**Test Suite**: 19 L2 ACL Test Cases (8 Functional + 3 Negative + 8 Robustness)

---

## Overview

This guide implements L2 (Layer 2) ACL testing on a SONiC DUT using native SPyTest framework with three SONiC devices:
- **DUT (Device Under Test)**: DUT1 - configured with L2 switchport mode and L2 ACLs
- **TX Host (Traffic Generator)**: DUT2 - sends Scapy-based L2 frames
- **RX Host (Traffic Sink)**: DUT3 - receives and verifies traffic with tcpdump

---

## Network Topology

```
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│   DUT2 (TX)      │          │    DUT1 (ACL)    │          │   DUT3 (RX)      │
│  10.0.0.1/24     │          │                  │          │   20.0.0.2/24    │
│                  │          │  L2 Switchport   │          │                  │
│ Ethernet24 ◄────┼──────────┤ Ethernet40       │          │                  │
│ (Scapy TX)       │ 10.0.0.0/│   ↕ L2 ACL      │          │                  │
│                  │  24      │ Ethernet24       ├──────────┤ Ethernet24       │
│                  │          │                  │ 20.0.0.0/│ (tcpdump RX)     │
│                  │          │                  │  24      │                  │
└──────────────────┘          └──────────────────┘          └──────────────────┘

Traffic Flow: DUT2 (Scapy TX) → DUT1:Ethernet40 (ACL Ingress)
             → L2 Bridging → DUT1:Ethernet24 → DUT3 (tcpdump RX)
```

---

## Test Case Summary

### Functional Tests (8 cases) - `test_l2_acl.py`

| TC ID | Test Name | Description | Expected Result |
|-------|-----------|-------------|-----------------|
| L2-01 | Permit Exact Source MAC | Allow frames from specific source MAC | TX=10, RX≥9 |
| L2-02 | Deny Exact Source MAC | Drop frames from blocked source MAC | TX=10, RX=0 |
| L2-03 | Deny Exact Destination MAC | Drop frames to specific dest MAC | TX=10, RX=0 |
| L2-04 | Deny Broadcast MAC | Drop broadcast frames (FF:FF:FF:FF:FF:FF) | TX=10, RX=0 |
| L2-05 | Deny ARP EtherType | Drop ARP frames (0x0806) | TX=10, RX=0 |
| L2-06 | Deny Specific VLAN | Drop frames tagged with VLAN 100 | TX=10, RX=0 |
| L2-07 | VLAN Permit/Deny Mix | Permit VLAN 10, Deny VLAN 200 | VLAN10 RX≥9, VLAN200 RX=0 |
| L2-08 | ACL Rule Priority | Test permit rule before deny rule | TX=10, RX≥9 |

### Negative/Edge Tests (3 cases) - `test_l2_acl_negative.py`

| TC ID | Test Name | Description | Expected Result |
|-------|-----------|-------------|-----------------|
| L2-N01 | MAC Case Sensitivity | MAC matching (uppercase vs lowercase) | Case-insensitive match |
| L2-N02 | Multicast Destination | Multicast address (01:00:5E:...) | Forwarded (no rule) |
| L2-N03 | Invalid MAC Handling | Malformed MAC addresses | Dropped or handled safely |

### Robustness/Persistence Tests (8 cases) - `test_l2_acl_robust.py`

| TC ID | Test Name | Description | Expected Result |
|-------|-----------|-------------|-----------------|
| L2-R01 | Persistence After Reboot | ACL rules survive config reload | Traffic behavior unchanged |
| L2-R02 | ACL Modify During Traffic | Update rules while traffic active | New packets follow new rule |
| L2-R03 | Rapid Enable/Disable | Multiple ACL config changes (10+ cycles) | No errors, state consistent |
| L2-R04 | Concurrent Flows | Different MAC rules for different flows | Both flows correct, no crosstalk |
| L2-R05 | Counter Accuracy | ACL hit counters with 1000+ packets | Counter accuracy ±1 packet |
| L2-R06 | VLAN Rule Persistence | VLAN rules survive other config changes | Unaffected by other changes |
| L2-R07 | MAC Aging Behavior | Traffic after 5-minute wait | Consistent behavior (no timeout) |
| L2-R08 | Mixed Permit/Deny Rules | Same match criteria in permit/deny | First rule wins (no ambiguity) |

---

## Prerequisites

### DUT1 Configuration (L2 Switchport Mode)

```bash
# Configure ports as L2 switchports (NOT routed L3)
configure terminal
interface Ethernet40
  switchport mode access
  no shutdown
  exit
interface Ethernet24
  switchport mode access
  no shutdown
  exit

# Create VLANs for test cases
vlan 1
  exit
vlan 10
  exit
vlan 100
  exit
vlan 200
  exit

# Assign ports to VLAN 1 (default)
interface Ethernet40
  switchport access vlan 1
  exit
interface Ethernet24
  switchport access vlan 1
  exit
```

### DUT2 Configuration (TX Host - Scapy)

```bash
# Configure interface for Scapy traffic generation
configure terminal
interface Ethernet24
  ip address 10.0.0.1/24
  no shutdown
  exit
```

### DUT3 Configuration (RX Host - tcpdump)

```bash
# Configure interface for traffic reception
configure terminal
interface Ethernet24
  ip address 20.0.0.2/24
  no shutdown
  exit
```

---

## Manual Test Execution

### Test L2-01: Permit Exact Source MAC

**Objective**: Verify explicit permit ACL rule for source MAC

**Steps**:
1. On DUT1, create L2 ACL:
   ```bash
   configure terminal
   access-list L2_TEST permit source 00:11:22:33:44:55
   apply l2-acl L2_TEST ingress Ethernet40
   exit
   ```

2. On DUT2 (TX), send frames:
   ```bash
   python3 << 'EOF'
   from scapy.all import Ether, IP, sendp
   pkt = Ether(src="00:11:22:33:44:55", dst="FF:FF:FF:FF:FF:FF")/IP()
   for i in range(10):
       sendp(pkt, iface="Ethernet24", verbose=False)
   EOF
   ```

3. On DUT3 (RX), verify reception:
   ```bash
   sudo tcpdump -i Ethernet24 -c 10 "ether src 00:11:22:33:44:55"
   # Expected: 10 packets received
   ```

4. Cleanup:
   ```bash
   configure terminal
   no access-list L2_TEST
   exit
   ```

---

### Test L2-02: Deny Exact Source MAC

**Objective**: Verify ACL rule denies traffic from blocked source MAC

**Steps**:
1. On DUT1, create L2 ACL:
   ```bash
   configure terminal
   access-list L2_TEST deny source DE:AD:BE:EF:00:01
   access-list L2_TEST permit any
   apply l2-acl L2_TEST ingress Ethernet40
   exit
   ```

2. On DUT2 (TX), send frames:
   ```bash
   python3 << 'EOF'
   from scapy.all import Ether, IP, sendp
   pkt = Ether(src="DE:AD:BE:EF:00:01", dst="FF:FF:FF:FF:FF:FF")/IP()
   for i in range(10):
       sendp(pkt, iface="Ethernet24", verbose=False)
   EOF
   ```

3. On DUT3 (RX), verify no reception:
   ```bash
   sudo tcpdump -i Ethernet24 -c 1 "ether src DE:AD:BE:EF:00:01" --timeout=3
   # Expected: No packets received
   ```

4. Cleanup:
   ```bash
   configure terminal
   no access-list L2_TEST
   exit
   ```

---

### Test L2-03: Deny Exact Destination MAC

**Objective**: Verify ACL rule denies traffic to specific destination MAC

**Steps**:
1. On DUT1, create L2 ACL:
   ```bash
   configure terminal
   access-list L2_TEST deny destination FE:ED:FA:CE:00:02
   access-list L2_TEST permit any
   apply l2-acl L2_TEST ingress Ethernet40
   exit
   ```

2. On DUT2 (TX), send frames to blocked destination:
   ```bash
   python3 << 'EOF'
   from scapy.all import Ether, IP, sendp
   pkt = Ether(src="00:11:22:33:44:55", dst="FE:ED:FA:CE:00:02")/IP()
   for i in range(10):
       sendp(pkt, iface="Ethernet24", verbose=False)
   EOF
   ```

3. On DUT3 (RX), verify no reception:
   ```bash
   sudo tcpdump -i Ethernet24 -c 1 "ether dst FE:ED:FA:CE:00:02" --timeout=3
   # Expected: No packets received
   ```

4. Cleanup:
   ```bash
   configure terminal
   no access-list L2_TEST
   exit
   ```

---

### Test L2-04: Deny Broadcast MAC

**Objective**: Verify ACL rule denies broadcast frames

**Steps**:
1. On DUT1, create L2 ACL:
   ```bash
   configure terminal
   access-list L2_TEST deny destination FF:FF:FF:FF:FF:FF
   access-list L2_TEST permit any
   apply l2-acl L2_TEST ingress Ethernet40
   exit
   ```

2. On DUT2 (TX), send broadcast frames:
   ```bash
   python3 << 'EOF'
   from scapy.all import Ether, ARP, sendp
   pkt = Ether(src="00:11:22:33:44:55", dst="FF:FF:FF:FF:FF:FF")/ARP()
   for i in range(10):
       sendp(pkt, iface="Ethernet24", verbose=False)
   EOF
   ```

3. On DUT3 (RX), verify no reception:
   ```bash
   sudo tcpdump -i Ethernet24 -c 1 "ether broadcast" --timeout=3
   # Expected: No packets received
   ```

4. Cleanup:
   ```bash
   configure terminal
   no access-list L2_TEST
   exit
   ```

---

### Test L2-05: Deny ARP EtherType

**Objective**: Verify ACL rule denies ARP protocol frames

**Steps**:
1. On DUT1, create L2 ACL:
   ```bash
   configure terminal
   access-list L2_TEST deny ether-type 0x0806
   access-list L2_TEST permit any
   apply l2-acl L2_TEST ingress Ethernet40
   exit
   ```

2. On DUT2 (TX), send ARP frames:
   ```bash
   python3 << 'EOF'
   from scapy.all import Ether, ARP, sendp
   pkt = Ether(src="00:11:22:33:44:55", dst="FF:FF:FF:FF:FF:FF", type=0x0806)/ARP()
   for i in range(10):
       sendp(pkt, iface="Ethernet24", verbose=False)
   EOF
   ```

3. On DUT3 (RX), verify no reception:
   ```bash
   sudo tcpdump -i Ethernet24 "arp" --timeout=3 -c 1
   # Expected: No packets received
   ```

4. Cleanup:
   ```bash
   configure terminal
   no access-list L2_TEST
   exit
   ```

---

### Test L2-06: Deny Specific VLAN

**Objective**: Verify VLAN-based ACL rules

**Steps**:
1. On DUT1, create VLAN-based ACL:
   ```bash
   configure terminal
   access-list L2_TEST deny vlan 100
   access-list L2_TEST permit any
   apply l2-acl L2_TEST ingress Ethernet40
   exit
   ```

2. On DUT2 (TX), send VLAN-tagged frames:
   ```bash
   python3 << 'EOF'
   from scapy.all import Ether, Dot1Q, IP, sendp
   pkt = Ether(src="00:11:22:33:44:55", dst="FF:FF:FF:FF:FF:FF")/Dot1Q(vlan=100)/IP()
   for i in range(10):
       sendp(pkt, iface="Ethernet24", verbose=False)
   EOF
   ```

3. On DUT3 (RX), verify no reception:
   ```bash
   sudo tcpdump -i Ethernet24 "vlan 100" --timeout=3 -c 1
   # Expected: No packets received
   ```

4. Cleanup:
   ```bash
   configure terminal
   no access-list L2_TEST
   exit
   ```

---

### Test L2-07: Permit VLAN 10, Deny VLAN 200

**Objective**: Verify mixed permit/deny VLAN rules

**Phase 1 - Permit VLAN 10**:
1. On DUT1, create ACL:
   ```bash
   configure terminal
   access-list L2_TEST permit vlan 10
   access-list L2_TEST deny vlan 200
   apply l2-acl L2_TEST ingress Ethernet40
   exit
   ```

2. On DUT2 (TX), send VLAN 10 frames:
   ```bash
   python3 << 'EOF'
   from scapy.all import Ether, Dot1Q, IP, sendp
   pkt = Ether(src="00:11:22:33:44:55", dst="FF:FF:FF:FF:FF:FF")/Dot1Q(vlan=10)/IP()
   for i in range(10):
       sendp(pkt, iface="Ethernet24", verbose=False)
   EOF
   ```

3. On DUT3 (RX), verify reception (≥9 packets):
   ```bash
   sudo tcpdump -i Ethernet24 "vlan 10" -c 10 --timeout=3
   # Expected: 10+ packets received
   ```

**Phase 2 - Deny VLAN 200**:
1. On DUT2 (TX), send VLAN 200 frames:
   ```bash
   python3 << 'EOF'
   from scapy.all import Ether, Dot1Q, IP, sendp
   pkt = Ether(src="00:11:22:33:44:55", dst="FF:FF:FF:FF:FF:FF")/Dot1Q(vlan=200)/IP()
   for i in range(10):
       sendp(pkt, iface="Ethernet24", verbose=False)
   EOF
   ```

2. On DUT3 (RX), verify no reception:
   ```bash
   sudo tcpdump -i Ethernet24 "vlan 200" --timeout=3 -c 1
   # Expected: No packets received
   ```

3. Cleanup:
   ```bash
   configure terminal
   no access-list L2_TEST
   exit
   ```

---

### Test L2-R01: ACL Persistence After Reboot

**Objective**: Verify ACL rules survive configuration reload

**Steps**:
1. Configure ACL on DUT1:
   ```bash
   configure terminal
   access-list L2_TEST permit source 00:11:22:33:44:55
   apply l2-acl L2_TEST ingress Ethernet40
   end
   write memory
   ```

2. Send and verify traffic (before reboot):
   ```bash
   # On DUT2: Send traffic
   # On DUT3: Verify reception with tcpdump
   ```

3. Reload configuration:
   ```bash
   sudo reload
   # Wait for device to restart
   ```

4. Send and verify traffic (after reboot):
   ```bash
   # On DUT2: Send same traffic
   # On DUT3: Verify identical reception
   ```

5. Verify ACL still active:
   ```bash
   show access-list L2_TEST
   show acl ingress Ethernet40
   ```

6. Cleanup:
   ```bash
   configure terminal
   no access-list L2_TEST
   exit
   ```

---

### Test L2-R05: Counter Accuracy (1000+ packets)

**Objective**: Verify ACL counter accuracy with high packet volume

**Steps**:
1. On DUT1, create ACL with counter:
   ```bash
   configure terminal
   access-list L2_TEST permit source 00:11:22:33:44:55
   apply l2-acl L2_TEST ingress Ethernet40
   exit
   ```

2. On DUT2 (TX), send 1000 packets:
   ```bash
   python3 << 'EOF'
   from scapy.all import Ether, IP, sendp
   pkt = Ether(src="00:11:22:33:44:55", dst="FF:FF:FF:FF:FF:FF")/IP()
   for i in range(1000):
       sendp(pkt, iface="Ethernet24", verbose=False)
   EOF
   ```

3. On DUT3 (RX), count received packets:
   ```bash
   sudo tcpdump -i Ethernet24 -c 1000 "ether src 00:11:22:33:44:55" --timeout=30
   ```

4. On DUT1, verify counter:
   ```bash
   show access-list L2_TEST
   # Expected counter value: ~1000 (acceptable margin: ±1)
   ```

5. Cleanup:
   ```bash
   configure terminal
   no access-list L2_TEST
   exit
   ```

---

## Pass/Fail Criteria

| Test Type | Pass Condition |
|-----------|----------------|
| **Permit** | RX count ≥ 90% of TX count |
| **Deny** | RX count = 0 (all packets dropped) |
| **Counter** | DUT counter = TX packet count ±1 |
| **Persistence** | Traffic behavior identical before/after reboot |
| **Robustness** | No errors, consistent state across updates |

---

## Test Execution Commands

### Run Functional Tests Only
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/switching/l2_acl/test_l2_acl.py \
    --logs-path ./logs/l2_functional_$(date +%F_%H%M%S) \
    --log-level info --skip-init-config
```

### Run Negative Tests Only
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/switching/l2_acl/test_l2_acl_negative.py \
    --logs-path ./logs/l2_negative_$(date +%F_%H%M%S) \
    --log-level info --skip-init-config
```

### Run Robustness Tests Only
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/switching/l2_acl/test_l2_acl_robust.py \
    --logs-path ./logs/l2_robustness_$(date +%F_%H%M%S) \
    --log-level info --skip-init-config
```

### Run All L2 ACL Tests
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/switching/l2_acl/ \
    --logs-path ./logs/l2_acl_full_$(date +%F_%H%M%S) \
    --log-level info --skip-init-config
```

---

## Key Implementation Notes

### Dynamic Port Discovery
- All scripts use testbed YAML to discover port connections
- NO hardcoded interface names (Ethernet40, Ethernet24, etc.)
- Ports are discovered from `testbeds/testbed_acl.yaml` topology section

### L2 vs L3 Mode
- **L2 Mode**: Switchport configuration (MAC switching, VLAN bridging)
- **L3 Mode**: Routed configuration (IP routing)
- Tests use L2 switchport mode, NOT L3 routed mode

### MAC Address Handling
- Source MAC: 00:11:22:33:44:55 (TX Host = DUT2)
- Destination MAC: FF:FF:FF:FF:FF:FF (broadcast) or RX Host MAC
- Case-insensitive matching (00:AA vs 00:aa)

### VLAN Handling
- Untagged frames: VLAN 1 (native/default)
- Tagged frames: Dot1Q with VLAN ID (10, 100, 200)
- L2-06/L2-07 require VLANs to be created first

### Traffic Generation
- Scapy on DUT2 (TX Host) sends L2 frames
- tcpdump on DUT3 (RX Host) captures and counts packets
- SPyTest framework coordinates test execution

---

## References

- **Test Plan**: `acl-l2.md`
- **Testbed Configuration**: `testbeds/testbed_acl.yaml`
- **Test Implementation**:
  - `test_l2_acl.py` (Functional tests)
  - `test_l2_acl_negative.py` (Negative tests)
  - `test_l2_acl_robust.py` (Robustness tests)

---

**Status**: ✅ Ready for manual and automated testing
