# L3 ACL Test Plan - Architecture Review

## Executive Summary

The test plan describes a **two-host external traffic generation architecture** where Scapy runs on **separate physical/virtual hosts (not inside the DUT)**, connected to the Device Under Test via two independent ports. This is a **valid and recommended approach** for ACL testing, though several architectural and implementation considerations should be addressed.

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
1. Document explicitly states: "Two hosts connected to a Device Under Test (DUT) with two ports"
2. Different IP addresses assigned: 10.0.0.1 (TX) vs 20.0.0.2 (RX)
3. Connected to different DUT ports: Port1 (TX) and Port2 (RX)
4. Script references mention `eth0` and `eth1` as Scapy interface names on the TX/RX hosts
5. "All scripts require `sudo` (raw packet socket)" - indicates host-level packet manipulation

**Implication:** The DUT (whether VS or HW) is the **system under test in the middle**, not hosting Scapy.

---

## Architecture Assessment

### ✅ Strengths

| Aspect | Benefit |
|--------|---------|
| **Isolation** | Traffic generation is isolated from DUT, preventing measurement bias |
| **Realism** | Mirrors production topology: external clients send traffic toward DUT |
| **Multi-platform Support** | Works with both Virtual (VS) and Hardware (HW) DUT variants |
| **Port-level Testing** | ACL ingress on Port1 can be verified without Port2 interference |
| **Independent Verification** | RX host can independently confirm packet drops via tcpdump |

### ⚠️ Potential Concerns & Recommendations

#### 1. **Network Connectivity Between Hosts and DUT**

**Issue:** The test plan assumes a direct L2 connection (ethernet) between TX/RX hosts and DUT ports.

**Recommendations:**
- [ ] **Specify network interface drivers**: Ensure Host TX/RX have compatible Ethernet drivers for raw packet injection
- [ ] **Document interface speed requirements**: Confirm Port1/Port2 support the expected line rate
- [ ] **MAC address considerations**: Verify static MAC assignment (AA:01 and BB:02) are correctly configured on host interfaces
- [ ] **Network isolation**: Ensure TX→DUT→RX path is isolated from management networks

#### 2. **Host-DUT Link State Dependencies**

**Issue:** Tests depend on Port1 and Port2 being up and operational.

**Recommendations:**
- [ ] **Port readiness checks**: Add pre-test validation that both DUT ports are `up` and operational
- [ ] **Link flapping tolerance**: Define expected behavior if a link drops during test execution
- [ ] **MTU configuration**: Verify MTU is consistent across Host TX, DUT, and Host RX (especially if VLAN/tagged traffic is tested)

#### 3. **Traffic Patterns and Bidirectional vs Unidirectional**

**Issue:** Current description suggests unidirectional flow (TX → DUT → RX), but many ACL scenarios require bidirectional validation.

**Recommendations:**
- [ ] **Clarify traffic direction**: Explicitly state if tests only validate one-way (TX→RX) or expect bidirectional ACL enforcement
- [ ] **Return traffic validation**: Define how to test return traffic (RX→DUT→TX) if needed, especially for TCP ACK testing (L3-09)
- [ ] **Stateful ACL patterns**: For TCP flag tests (L3-08, L3-09), clarify whether the DUT or RX host terminates the connection

#### 4. **Scapy Packet Crafting Assumptions**

**Issue:** Test cases assume specific packet structures can be crafted on Host TX.

**Recommendations:**
- [ ] **Scapy version compatibility**: Document minimum Scapy version required for all packet types (especially TCP flags, DSCP fields)
- [ ] **Checksum handling**: Verify Scapy auto-computes IP/TCP/UDP checksums correctly to avoid DUT discard of malformed packets
- [ ] **Raw packet socket permissions**: Confirm Host TX/RX have sufficient privileges for raw socket operations
- [ ] **Packet validation at RX**: Document whether RX validates packet contents or just counts arrivals

#### 5. **DUT Configuration and Baseline State**

**Issue:** Test plan doesn't specify DUT initial configuration.

**Recommendations:**
- [ ] **Port configuration**: Specify how Port1 and Port2 are configured (IP, routing, VRF, L3 vs L2 mode)
- [ ] **L3 forwarding**: Verify DUT has a route between 10.0.0.0/24 and 20.0.0.0/24 so packets can be routed (not just L2 switched)
- [ ] **Baseline ACL state**: Clarify whether DUT starts with no ACLs, default-deny, or default-permit
- [ ] **Interface IP configuration**: Are Port1/Port2 assigned IP addresses or are they L2-only interfaces?

#### 6. **ACL Application and Direction Mismatch**

**Issue:** Document states "ACL applied IN [ingress on DUT Port1]" but doesn't clarify the full policy.

**Recommendations:**
- [ ] **Egress ACL validation**: Some test cases might need egress ACL testing on Port2—clarify scope
- [ ] **ACL order/priority**: Specify rule order and priority to handle overlapping IP subnets (e.g., L3-N01)
- [ ] **Default action**: Explicitly define default deny vs. default permit when no rules match

#### 7. **Test Case Implementation Gaps**

**Issue:** Several test cases reference network behaviors that may not be supported in current implementation.

| TC ID | Concern | Recommendation |
|-------|---------|-----------------|
| **L3-R01** | "Change TX/RX IP" during test | Clarify if this means modifying host IPs live (potential L2 flapping) or changing payload IPs in crafted packets |
| **L3-R02** | "Modify rule 100+ times/sec" | Confirm DUT CLI can sustain this rate; may require batched `config` commands (SM_ISCLI) |
| **L3-N02** | Broadcast handling (255.255.255.255) | Clarify expected behavior—are broadcasts dropped by default, permitted, or platform-specific? |
| **L3-N03** | "Malformed/invalid IP" | Define what constitutes "malformed"—truncated header, bad checksum, invalid options? |
| **L3-12** | DSCP QoS tag (HW only) | Ensure QoS classification is configured on DUT before DSCP tests |
| **L3-09** | TCP ACK with seq/ack numbers | Clarify: Does RX host respond with SYN-ACK, or is it unidirectional? |

#### 8. **Host Operating System and Network Stack**

**Issue:** Scapy behavior varies across Linux kernels and network stacks.

**Recommendations:**
- [ ] **Linux kernel version**: Document minimum/tested kernel versions on TX/RX hosts
- [ ] **Network stack configuration**: Verify TX/RX hosts don't have local firewall rules (iptables, nftables) blocking test traffic
- [ ] **ARP and neighbor discovery**: Clarify how ARP is handled when crafting packets with Scapy (e.g., raw sockets bypass ARP; ensure DUT ARP entries are pre-populated if needed)
- [ ] **ICMP redirect handling**: Clarify if DUT sends ICMP redirects and how TX/RX hosts handle them

#### 9. **Metric Collection and Counter Validation**

**Issue:** Plan mentions "ACL hit counter == TX packet count" but doesn't specify counter retrieval mechanism.

**Recommendations:**
- [ ] **Counter query method**: Specify CLI command to retrieve ACL counters (click, klish, REST, gNMI)
- [ ] **Counter granularity**: Define if counters are per-rule, per-ACL table, or per-interface
- [ ] **Counter accuracy**: Document acceptable error margin (e.g., ±1% of packets due to out-of-order processing)
- [ ] **Non-integer counters**: Handle cases where RX packet loss is 1-3 packets (≥90% threshold for PERMIT)

#### 10. **Traffic Load and Timing**

**Issue:** Test cases don't specify packet rates or timing requirements.

**Recommendations:**
- [ ] **Packet rate**: Define default packet rate (pps) and whether variable rates are tested
- [ ] **Test duration**: Specify minimum test duration (e.g., 5 sec minimum for statistical significance)
- [ ] **Burst handling**: Clarify whether burst traffic (line-rate floods) is tested or only steady-state rates
- [ ] **Timeout handling**: Define maximum wait time for RX to receive packets before declaring "dropped"

---

## Implementation Readiness Checklist

- [ ] **Host TX/RX setup**: Document exact steps to configure eth0/eth1 with IPs 10.0.0.1 and 20.0.0.2
- [ ] **DUT port configuration**: Provide playbook to configure Port1/Port2 for L3 forwarding between TX/RX subnets
- [ ] **Baseline connectivity test**: Add pre-test sanity check (ICMP without ACLs) to verify path works
- [ ] **Scapy environment**: Document Python version, Scapy version, required Linux kernel modules
- [ ] **ACL rule syntax**: Provide exact DUT CLI commands for each rule variant (click, klish, REST)
- [ ] **Counter validation**: Document exact commands to fetch ACL hit counters
- [ ] **Cleanup procedures**: Define how to remove ACLs, reset counters, and restore to baseline state
- [ ] **Error scenarios**: Document expected behavior if DUT resets, ACL config fails, or port goes down mid-test

---

## Recommended Topology Enhancements (Optional)

### Alternative Architecture: DUT-to-DUT (Advanced)

If host-based Scapy proves problematic, consider **DUT-to-DUT topology**:
```
[DUT1 (Traffic Gen)] ←→ [DUT2 (ACL Under Test)]
```

**Pros:**
- Uses built-in SONiC traffic generator capabilities
- No external host dependencies
- Easier to replicate in CI/CD environments

**Cons:**
- Requires two DUT instances
- May not reflect single-device production scenarios

---

## Summary

| Finding | Status | Action |
|---------|--------|--------|
| **Architecture is sound** | ✅ Valid | Proceed with external hosts |
| **Host-DUT connectivity** | ⚠️ Needs spec | Document interface/driver requirements |
| **Bidirectional traffic** | ⚠️ Unclear | Clarify unidirectional vs. bidirectional tests |
| **DUT baseline config** | ⚠️ Missing | Add pre-test DUT configuration playbook |
| **Scapy assumptions** | ⚠️ Needs validation | Document version/kernel requirements |
| **Test case details** | ⚠️ Incomplete | Expand L3-R01, L3-R02, L3-09, L3-12 scenarios |
| **Counter validation** | ⚠️ Needs method | Document exact CLI commands for each UI type |

---

## Next Steps

1. **Update acl-l3.md** with clarifications from sections 1-10 above
2. **Create setup guide** (setup_guide.md) for Host TX/RX provisioning
3. **Create DUT config guide** (dut_config.md) for Port1/Port2 baseline setup
4. **Validate test case implementations** against each recommendation
5. **Add pre-test sanity checks** to l3_acl_traffic.py
6. **Document expected failures** for platform-specific test cases (e.g., L3-12 DSCP on VS)

