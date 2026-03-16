# L2 ACL Test Plan - Architecture Review

## Executive Summary

The L2 ACL test plan describes a **two-host external traffic generation architecture** where Scapy runs on **separate physical/virtual hosts (not inside the DUT)**, connected to the Device Under Test via two independent ports. This is a **valid and recommended approach** for L2 ACL testing, with architecture similar to L3 ACL testing but focused on Layer 2 (MAC/EtherType/VLAN) matching.

---

## Architecture Analysis

### Current Design

**Topology:**
```
[Host TX with Scapy] ←eth0→ [DUT (VS or HW)] ←eth1→ [Host RX with Scapy]
      10.0.0.1/24          Port1 ↔ Port2           20.0.0.2/24
```

### Key Architecture Questions & Findings

#### ✅ **Q1: Are TX and RX hosts external or inside DUT-VS?**

**Answer: External and separate from DUT**

**Evidence:**
1. Document explicitly states: "Two hosts, two DUT ports"
2. Different IP addresses assigned: 10.0.0.1 (TX) vs 20.0.0.2 (RX)
3. Connected to different DUT ports: Port1 (TX) and Port2 (RX)
4. Script references mention `eth0` and `eth1` as Scapy interface names on TX/RX hosts
5. "All scripts require `sudo` (raw packet socket)" - indicates host-level packet manipulation

**Implication:** The DUT (whether VS or HW) is the **system under test in the middle**, not hosting Scapy.

---

## Architecture Assessment

### ✅ Strengths

| Aspect | Benefit |
|--------|---------|
| **Isolation** | Traffic generation is isolated from DUT, preventing measurement bias |
| **Realism** | Mirrors production topology: external clients send frames toward DUT |
| **Multi-platform Support** | Works with both Virtual (VS) and Hardware (HW) DUT variants |
| **Port-level Testing** | L2 ACL ingress on Port1 can be verified without Port2 interference |
| **Independent Verification** | RX host can independently confirm packet drops via tcpdump |
| **L2 Focus** | Tests MAC, EtherType, and VLAN matching without IP layer complexity |

### ⚠️ Potential Concerns & Recommendations

#### 1. **Network Interface Drivers and L2 Switching**

**Issue:** L2 ACL testing relies on proper L2 frame forwarding through DUT ports.

**Recommendations:**
- [ ] **Verify port mode**: Confirm Port1 and Port2 are in "L2 mode" or "switchport mode"
- [ ] **Document VLAN configuration**: L2-06/L2-07 tests require VLAN support; specify VLAN IDs pre-configured
- [ ] **MAC address learning**: Clarify whether DUT learns MAC addresses from TX/RX hosts or if static MAC entries are needed
- [ ] **Spanning Tree Protocol (STP)**: If STP is enabled, document impact on port states during testing

#### 2. **MAC Address Table and Aging**

**Issue:** Test plan mentions "L2-R07: ACL aging/timeout behavior" but doesn't define baseline.

**Recommendations:**
- [ ] **MAC aging timeout**: Document DUT's MAC aging timeout value (typically 300 seconds)
- [ ] **Dynamic vs Static MACs**: Clarify if TX/RX MAC addresses are learned dynamically or configured statically
- [ ] **MAC table capacity**: Specify max MAC entries; test with 2 MACs to avoid table exhaustion issues
- [ ] **Aging behavior**: Define expected behavior after 5-minute wait (L2-R07) — MACs should NOT age out in typical testing window

#### 3. **VLAN Tagging and Test Case Dependencies**

**Issue:** L2-06 and L2-07 test VLAN ACLs, but VLAN configuration is not documented.

**Recommendations:**
- [ ] **VLAN pre-configuration**: Specify which VLANs must be pre-configured on DUT (VLAN 10, 100, 200 implied)
- [ ] **VLAN assignment**: Clarify if Port1/Port2 are members of these VLANs or if trunking is used
- [ ] **Untagged VLAN**: Document which packets are in native/untagged VLAN (L2-01 through L2-05)
- [ ] **Tagged vs Untagged**: L2-06/L2-07 use `Ether()/Dot1Q()` (tagged); clarify if tests 01-05 are untagged
- [ ] **Tag format**: Document VLAN tag format and priority bits handling

#### 4. **ARP Handling and L2-04/L2-05 Tests**

**Issue:** Test L2-04 (broadcast MAC) and L2-05 (ARP EtherType) have special handling requirements.

**Recommendations:**
- [ ] **ARP policy**: Document DUT's default ARP handling (block, flood, trap to CPU?)
- [ ] **Broadcast flooding**: Clarify if unmatched broadcast frames are flooded to all ports or dropped
- [ ] **EtherType matching**: Confirm DUT ACL supports EtherType matching (some platforms use "ether type" syntax)
- [ ] **ARP replies**: If TX/RX hosts send real ARP requests, document expected behavior

#### 5. **ACL Application Direction and Scope**

**Issue:** Document states "ACL applied IN [ingress on DUT Port1]" but doesn't clarify L2 egress scope.

**Recommendations:**
- [ ] **Ingress vs Egress**: Explicitly state all tests use ingress-only; egress testing is out of scope
- [ ] **Port1/Port2 asymmetry**: Confirm ACL is applied only on Port1, not Port2
- [ ] **All ports vs specific port**: Clarify if ACL applies to all ports or only Port1
- [ ] **Control plane impact**: Document whether ACL affects management traffic (unlikely, but clarify)

#### 6. **Test Case Clarifications**

**Issue:** Several test cases reference undefined or ambiguous behaviors.

| TC ID | Concern | Recommendation |
|-------|---------|-----------------|
| **L2-01** | "Permit exact source MAC" | Clarify if this is a real permit rule or if default is permit-all |
| **L2-03** | Destination MAC matching | Verify DUT supports destination MAC ACL (not all platforms) |
| **L2-04** | Broadcast MAC (FF:FF:FF:FF:FF:FF) | Some DUTs have special handling for broadcast; define expected behavior |
| **L2-05** | EtherType ARP (0x0806) | Confirm DUT supports EtherType ACL matching |
| **L2-N01** | MAC case sensitivity | Verify DUT MAC comparison is case-insensitive (standard but confirm) |
| **L2-N02** | Multicast MAC (01:00:5E) | Document if multicast is permitted, flooded, or treated specially |
| **L2-N03** | Invalid/corrupt MAC | Define what "malformed" means; can Scapy even craft invalid MACs? |
| **L2-R01** | "DUT reboot" persistence | Clarify if reboot means "write memory + reload" or something else |
| **L2-R05** | "1000+ packets" counter accuracy | Baseline test uses 10 packets; 1000+ is 100x higher — ensure no overflow |
| **L2-R07** | "5-minute wait" aging behavior | Define MAC aging timeout and whether 5 minutes is significant |

#### 7. **Host Operating System and Network Stack**

**Issue:** Scapy raw L2 frame transmission has OS-specific requirements.

**Recommendations:**
- [ ] **Linux kernel version**: Document minimum (5.4+) and tested versions
- [ ] **Network driver**: Some drivers (e.g., virtio) may have L2 frame handling quirks
- [ ] **L2 switching**: Confirm TX/RX hosts are not doing local L2 switching (should be direct Ethernet)
- [ ] **Frame validation**: Clarify whether invalid frames (bad CRC, truncated) are auto-dropped by NIC drivers

#### 8. **Metric Collection and Counter Validation**

**Issue:** Plan mentions "DUT ACL hit counter == TX packet count" but doesn't specify per-rule vs per-table counters.

**Recommendations:**
- [ ] **Counter granularity**: Document if counters are per-rule, per-ACL-table, or per-interface
- [ ] **Counter retrieval**: Provide exact DUT CLI command to get L2 ACL counters
- [ ] **Counter reset**: Document how to reset counters between tests
- [ ] **Non-matching behavior**: Define counter behavior for non-matching packets (should increment "drop" counter, not ACL counter)

#### 9. **VLAN Tagging and MAC Address Learning**

**Issue:** Scapy crafted frames may not trigger normal MAC learning if they don't include IP.

**Recommendations:**
- [ ] **MAC learning trigger**: Clarify whether Scapy L2-only frames (no IP) trigger MAC learning
- [ ] **L2 switching vs L3 routing**: L2 tests should use L2 switching, not L3 routing (unlike L3-ACL)
- [ ] **Port state**: Ensure Port1/Port2 are in "learning" or "forwarding" state (not blocked by STP)
- [ ] **Bridging domain**: Confirm Port1 and Port2 are in same VLAN/bridging domain for L2-01 through L2-05

#### 10. **Traffic Load and Packet Size**

**Issue:** Test plan doesn't specify Ethernet frame size or MTU considerations.

**Recommendations:**
- [ ] **Frame size**: Document minimum/maximum frame sizes tested (64 bytes minimum for Ethernet)
- [ ] **MTU mismatch**: Verify all devices have same MTU (default 1500)
- [ ] **Jumbo frames**: Clarify if testing is limited to standard 1500-byte MTU or includes jumbo frames
- [ ] **Padding**: Small frames may be padded; document how DUT handles padding for ACL matching

---

## Implementation Readiness Checklist

- [ ] **Host TX/RX setup**: Document exact steps to configure eth0/eth1 with IPs and MACs
- [ ] **DUT L2 mode**: Confirm Port1/Port2 are in switchport mode (L2) with documented VLAN config
- [ ] **VLAN pre-config**: Specify VLAN 10, 100, 200 creation and port membership
- [ ] **Baseline connectivity test**: Add pre-test sanity check for L2 switching (no ACLs)
- [ ] **Scapy environment**: Document Python version, Scapy version, required libraries
- [ ] **L2 ACL rule syntax**: Provide exact DUT CLI commands for each rule variant
- [ ] **Counter validation**: Document exact commands to fetch L2 ACL hit counters
- [ ] **Cleanup procedures**: Define how to remove ACLs and reset MAC tables
- [ ] **Error scenarios**: Document expected behavior if DUT resets, ACL config fails, port goes down
- [ ] **Negative test expectations**: Define baseline behavior for L2-N01 through L2-N03

---

## Key Differences from L3 ACL Testing

| Aspect | L3 ACL | L2 ACL |
|--------|--------|--------|
| **Layer Focus** | IP addresses, protocols, TCP flags | MAC addresses, EtherType, VLAN tags |
| **Forwarding** | L3 routing decision | L2 switching decision |
| **DUT Port Config** | IP addresses (10.0.0.254/24, 20.0.0.254/24) | VLAN membership (native vs tagged) |
| **Test Case Count** | 12 functional cases | 8 functional cases |
| **Negative Tests** | IP-specific edge cases | MAC/VLAN-specific edge cases |
| **Robustness Tests** | IP/protocol/DSCP persistence | MAC aging, rule updates, counter accuracy |
| **VLAN Dependency** | Not tested | L2-06/L2-07 require VLAN support |

---

## Recommended Test Execution Order

1. **Setup Phase** (one-time):
   - Configure TX/RX host interfaces (eth0, eth1)
   - Configure DUT Port1/Port2 in L2 mode
   - Create VLANs 10, 100, 200
   - Verify baseline L2 switching (no ACLs)

2. **Functional Tests** (L2-01 through L2-08):
   - Test MAC source matching
   - Test MAC destination matching
   - Test EtherType matching
   - Test VLAN matching
   - Test rule priority

3. **Negative Tests** (L2-N01 through L2-N03):
   - Test edge cases (case sensitivity, multicast, malformed)

4. **Robustness Tests** (L2-R01 through L2-R08):
   - Test persistence, updates, counters, concurrent flows

---

## Summary

| Finding | Status | Action |
|---------|--------|--------|
| **Architecture is sound** | ✅ Valid | External hosts confirmed |
| **L2 switching setup** | ⚠️ Needs spec | Document VLAN config and port mode |
| **MAC address learning** | ⚠️ Unclear | Clarify dynamic vs static MACs |
| **VLAN configuration** | ⚠️ Missing | Specify VLANs 10/100/200 pre-creation |
| **ARP handling** | ⚠️ Undefined | Document DUT ARP policy |
| **Test case details** | ⚠️ Incomplete | Expand L2-04, L2-05, L2-R07 specs |
| **Counter validation** | ⚠️ Needs method | Document exact CLI commands |
| **Frame size** | ⚠️ Not specified | Document MTU and frame size handling |
| **MAC table aging** | ⚠️ Unclear | Define aging timeout and L2-R07 expectations |
| **Port state management** | ⚠️ Not documented | Clarify STP/port states during testing |

---

## Next Steps

1. **Update acl-l2.md** with clarifications from sections 1-10 above
2. **Create L2-specific setup guide** (l2_host_setup.md) with VLAN configuration
3. **Create L2 DUT setup guide** (l2_dut_setup.md) with switchport and VLAN config
4. **Validate test case implementations** against each recommendation
5. **Add pre-test sanity checks** to l2_acl_traffic.py
6. **Document expected failures** for platform-specific test cases
7. **Expand negative test definitions** for L2-specific edge cases

