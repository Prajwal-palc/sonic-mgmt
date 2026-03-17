# L3 ACL Test Plan — SpyTest-Native 3-SONiC-DUT Architecture

**Status**: ✅ Updated for Phases 1-4 (Refactoring Complete)
**Date**: 2026-03-11
**Architecture**: 3-SONiC-DUT SpyTest-Native Pattern with Tcpdump Verification

---

## Overview

This test plan validates L3 (Layer 3 / IP-level) Access Control Lists on a SONiC Device Under Test using a **SpyTest-native, 3-SONiC-DUT pattern** with DUT-based Scapy traffic generation and tcpdump forensic verification.

**Key Evolution**: From external Scapy hosts to fully integrated 3-SONiC-DUT topology with SpyTest framework control.

---

## Architecture

### Network Topology (3-SONiC-DUT Pattern)

```
┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
│   DUT2       │                    │   DUT1       │                    │   DUT3       │
│  (TX Host)   │                    │ (ACL Device) │                    │  (RX Host)   │
│ 10.0.0.1/24  │                    │              │                    │ 20.0.0.2/24  │
│ Ethernet0 ◄──┼────────────────────┼─ Ethernet0   │                    │              │
│              │   10.0.0.0/24      │              │                    │              │
│              │    (TX subnet)      │ Ethernet4 ──┼────────────────────┼──► Ethernet0 │
│              │                     │              │   20.0.0.0/24      │              │
│              │                     │ [ACL INGRESS]   (RX subnet)       │              │
│              │                     │   on Eth0    │                    │              │
└──────────────┘                    └──────────────┘                    └──────────────┘

Device IDs:
  DUT1: sp-Sonic-106 (192.168.100.125) - ACL Device Under Test
  DUT2: sp-Sonic-107 (192.168.100.248) - TX Traffic Host (Scapy)
  DUT3: sp-Sonic-108 (192.168.100.134) - RX Verification Host (tcpdump)

Traffic Flow:
  DUT2 (Scapy) → DUT1:Ethernet0 [ACL applied] → Routing → DUT1:Ethernet4 → DUT3 (tcpdump)
```

### Key Architecture Decisions (Phase 1-4)

| Aspect | Original | Refactored (Phase 1-4) |
|--------|----------|------------------------|
| **Device Types** | 1 DUT + 2 external TGen | 3 SONiC DUTs (D1D2D3) |
| **Framework** | Manual orchestration | ✅ SpyTest-native integration |
| **Traffic Gen** | External SSH scripts | ✅ DUT-based scapy_traffic API |
| **Verification** | Ephemeral sniff() | ✅ Tcpdump + pcap forensics |
| **Logging** | Scattered | ✅ Centralized st.log/st.report |
| **Cleanup** | Manual, error-prone | ✅ Automatic try/finally blocks |
| **ACL Config** | Manual CLI | ✅ ACL API integration |

---

## Device Configuration

### DUT1 (sp-Sonic-106) - ACL Device Under Test

**Management:**
- IP: 192.168.100.125
- SSH: admin / root@123

**Interfaces (L3 Mode):**
```
DUT1# interface Ethernet0
  IP Address: 10.0.0.254/24
  Link: UP
  Description: "Gateway for TX subnet (facing DUT2)"

DUT1# interface Ethernet4
  IP Address: 20.0.0.254/24
  Link: UP
  Description: "Gateway for RX subnet (facing DUT3)"
```

**L3 Routing:**
- Routing enabled between 10.0.0.0/24 and 20.0.0.0/24
- ACL applied INGRESS on Ethernet0 (where test rules are evaluated)

### DUT2 (sp-Sonic-107) - TX Traffic Host

**Management:**
- IP: 192.168.100.248
- SSH: admin / root@123

**Interfaces (L3 Mode):**
```
DUT2# interface Ethernet0
  IP Address: 10.0.0.1/24
  Link: UP
  Description: "Connected to DUT1:Ethernet0 (TX subnet)"
```

**Role:**
- Scapy traffic generation via `scapy_traffic.send_traffic()`
- Non-blocking script execution
- Configurable source IP, packet count, duration, rate

### DUT3 (sp-Sonic-108) - RX Verification Host

**Management:**
- IP: 192.168.100.134
- SSH: admin / root@123

**Interfaces (L3 Mode):**
```
DUT3# interface Ethernet0
  IP Address: 20.0.0.2/24
  Link: UP
  Description: "Connected to DUT1:Ethernet4 (RX subnet)"
```

**Role:**
- Tcpdump packet capture
- Forensic verification via pcap files
- `rdpcap()` parsing for exact packet counts

---

## Prerequisites & Requirements

### Testbed Configuration

**File**: `testbeds/testbed_acl.yaml`
- 3-node topology (D1D2D3)
- All devices as `device_type: sonic`
- L3 addresses preconfigured (see above)
- Topology connections validated

### Software Requirements (All DUTs)

```bash
# Scapy
sudo pip3 install scapy --break-system-packages

# tcpdump
sudo apt-get install tcpdump

# Python 3.8+
python3 --version
```

### Network Requirements

- **Direct Physical/Virtual Links**:
  - DUT1:Ethernet0 ↔ DUT2:Ethernet0 (10.0.0.0/24)
  - DUT1:Ethernet4 ↔ DUT3:Ethernet0 (20.0.0.0/24)

- **Link Status**: All ports must be UP
  ```bash
  DUT# show interface status | grep -E "Ethernet0|Ethernet4"
  ```

- **L3 Connectivity**: Test baseline connectivity first
  ```bash
  DUT2# ping 10.0.0.254  (should reach DUT1 gateway)
  DUT3# ping 20.0.0.254  (should reach DUT1 gateway)
  ```

---

## Test Execution Framework

### SpyTest Framework Integration

**Test Script**: `tests/routing/l3_acl/test_l3_acl_basic_refactored.py`

**Class Structure**:
```python
@pytest.mark.topology("D1D2D3:1")
class TestL3AclBasic:
    @classmethod
    def setup_class(cls):
        # Initialize 3-DUT topology
        # Configure L3 addresses
        # Load test variables from YAML

    def test_l3_baseline_permit_all(self):
        # Baseline test (no ACL)

    def test_l3_01_deny_source_ip(self):
        # ACL rule: Deny source IP

    def test_l3_02_deny_source_subnet(self):
        # ACL rule: Deny source subnet

    def test_l3_03_deny_dest_ip(self):
        # ACL rule: Deny destination IP

    @classmethod
    def teardown_class(cls):
        # Cleanup ACL configurations
        # Remove pcap files
```

### Test Execution Workflow

For each test case:

```
PHASE 1: Cleanup
  └─ Remove old pcap files on DUT3

PHASE 2: Configure ACL (if applicable)
  ├─ Create ACL table on DUT1
  ├─ Create ACL rules
  └─ Apply to Ethernet0 INGRESS

PHASE 3: Start Verification
  └─ Start tcpdump on DUT3:Ethernet0 (background)

PHASE 4: Generate Traffic
  ├─ Deploy Scapy script to DUT2
  ├─ Execute non-blocking
  ├─ Configurable: source IP, packets, duration, rate
  └─ Return TX count to test

PHASE 5: Stop Verification
  └─ Stop tcpdump (flush buffers, wait 2 sec)

PHASE 6: Analyze Results
  ├─ Parse pcap file on DUT3 using rdpcap()
  ├─ Count received packets (RX_COUNT)
  └─ Return RX count to test

PHASE 7: Validate
  ├─ Check 1: TX > 0 (traffic actually sent)
  ├─ Check 2: RX count verified from pcap
  ├─ Check 3: Loss within acceptable range
  └─ Result: PASS/FAIL
```

### How to Run Tests

#### Run All Tests
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_basic_refactored.py \
    --logs-path ./logs/l3_acl_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native
```

#### Run Baseline Test (No ACL)
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_basic_refactored.py::TestL3AclBasic::test_l3_baseline_permit_all \
    --logs-path ./logs/l3_acl_baseline \
    --log-level debug --skip-init-config
```

#### Run L3-01 (Deny Source IP)
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_basic_refactored.py::TestL3AclBasic::test_l3_01_deny_source_ip \
    --logs-path ./logs/l3_acl_l3_01 \
    --log-level debug --skip-init-config
```

#### Run L3-02 (Deny Source Subnet)
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_basic_refactored.py::TestL3AclBasic::test_l3_02_deny_source_subnet \
    --logs-path ./logs/l3_acl_l3_02 \
    --log-level debug --skip-init-config
```

#### Run L3-03 (Deny Destination IP)
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_basic_refactored.py::TestL3AclBasic::test_l3_03_deny_dest_ip \
    --logs-path ./logs/l3_acl_l3_03 \
    --log-level debug --skip-init-config
```

---

## Test Variables Configuration

**File**: `spytest/vars/routing/l3_acl/vars_l3_acl.yaml`

### Test Case Definition Format

Each test case includes:

```yaml
testcases:
  "L3-01":
    title: "Deny source IP (host level)"
    description: "Test validates ACL rule denying specific source IP..."

    acl:
      tables:
        L3_ACL_TABLE:
          type: "L3"                    # L3 for IPv4, L3V6 for IPv6
          stage: "INGRESS"              # INGRESS or EGRESS
          ports: ["Ethernet0"]          # Applied to which ports

          rules:
            - rule_name: "RULE_1_DENY_SOURCE"
              action: "deny"            # deny or permit
              src_ip: "10.0.0.99/32"    # Source IP (host or subnet)
              dst_ip: "any"             # Destination IP
              protocol: "udp"           # tcp/udp/ip/any

    traffic:
      source_ip: "10.0.0.99"     # TX packet source
      dest_ip: "20.0.0.2"        # RX host destination
      num_packets: 100
      duration: 10
      expected_rx_min_pct: 0      # 0% = all denied

    expected_result: "PASS"
```

---

## Test Coverage — Comprehensive L3 ACL Test Suite (34 Cases)

### Legend

| Tag | Meaning |
|-----|---------|
| B | Both 3-DUT and HW |
| HW | Hardware/ASIC required |
| NEG | Negative/edge case test |
| R | Robustness/persistence test |

---

### 4.1 IP Address Match (9 cases)

#### Functional Test Cases (3 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected RX | Status |
|-------|-------------|-----|---------------|------------|-------------|--------|
| **L3-01** | Deny source IP (host) | B | `IP(src="10.0.0.99")/UDP()` | Deny 10.0.0.99/32 on Ethernet0 INGRESS | 0% | ✅ Ready |
| **L3-02** | Deny source subnet /24 | B | `IP(src="10.0.0.50")/UDP()` from any host in 10.0.0.0/24 | Deny 10.0.0.0/24 on Ethernet0 INGRESS | 0% | ✅ Ready |
| **L3-03** | Deny destination IP (host) | B | `IP(src="10.0.0.1", dst="20.0.0.99")/TCP()` | Deny dst 20.0.0.99/32 on Ethernet0 INGRESS | 0% | ✅ Ready |

#### Negative/Edge Case Tests (3 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected Result | Status |
|-------|-------------|-----|---------------|------------|-----------------|--------|
| **L3-N01** | Overlapping IP subnets (more specific rule) | NEG | `IP(src="10.0.0.0/25")` and `IP(src="10.0.0.0/24")` rules conflict | Define both rules, verify specificity | More specific rule (/25) takes precedence | 📝 Future |
| **L3-N02** | IP broadcast address (255.255.255.255) | NEG | `IP(dst="255.255.255.255")/ICMP()` | Deny broadcast | Dropped or handled per policy | 📝 Future |
| **L3-N03** | Malformed/invalid IP address | NEG | Crafted packet with truncated IP header | Deny invalid IP | Dropped or error handling | 📝 Future |

#### Robustness/Persistence Tests (3 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected Behavior | Status |
|-------|-------------|-----|---------------|------------|------------------|--------|
| **L3-R01** | ACL rule persistence after IP config change | B | Send from 10.0.0.1 (pass), then 10.0.0.99 (drop) by rule | Deny 10.0.0.99 | Rules persist after host IP reconfiguration | 📝 Future |
| **L3-R02** | High-frequency rule updates with live traffic | B | Continuous traffic while rules added/removed 100+ times/sec | Rapid rule updates | No errors, consistent final state | 📝 Future |
| **L3-R03** | Concurrent multiple IP-based ACL rules | B | Multiple overlapping IP rules, varied traffic | Multiple rules simultaneously | All rules evaluated correctly, no interference | 📝 Future |

---

### 4.2 Protocol Match (12 cases)

#### Functional Test Cases (4 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected RX | Status |
|-------|-------------|-----|---------------|------------|-------------|--------|
| **L3-04** | Deny ICMP | B | `IP()/ICMP(type=8)` from DUT2 | Deny ICMP on Ethernet0 INGRESS | 0% | 📝 Ready |
| **L3-05** | Deny UDP, permit TCP | B | `IP()/UDP(dport=53)` vs `IP()/TCP(dport=80)` | Deny UDP, permit TCP | UDP=0%, TCP=≥90% | ✅ Ready |
| **L3-06** | Deny TCP destination port 80 | B | `IP()/TCP(dport=80, flags="S")` from DUT2 | Deny TCP dport 80 on Ethernet0 INGRESS | 0% | 📝 Ready |
| **L3-07** | Deny UDP destination port 53 | B | `IP()/UDP(dport=53)` from DUT2 | Deny UDP dport 53 on Ethernet0 INGRESS | 0% | 📝 Ready |

#### Negative/Edge Case Tests (2 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected Result | Status |
|-------|-------------|-----|---------------|------------|-----------------|--------|
| **L3-N04** | Unknown/reserved protocol number | NEG | `IP(proto=99)/Raw()` - undefined protocol | Deny protocol 99 | Dropped or default action | 📝 Future |
| **L3-N05** | Port range edge cases (0, 65535) | NEG | `IP()/TCP(dport=0)` and `TCP(dport=65535)` | Deny port 0 and 65535 | Correct handling per rule | 📝 Future |

#### Robustness/Persistence Tests (3 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected Behavior | Status |
|-------|-------------|-----|---------------|------------|------------------|--------|
| **L3-R04** | Protocol rule persistence during port config change | B | Protocol-based rules, then modify interface speed/config | Rules persist | Rules unaffected by port config changes | 📝 Future |
| **L3-R05** | ACL rule state consistency under protocol stress | B | Rapid protocol type changes (ICMP→UDP→TCP) | Multiple protocol rules | Rules evaluate correctly each change | 📝 Future |
| **L3-R06** | Deny + Permit protocol rules with same IP | B | Same source IP with conflicting deny/permit rules | Deny protocol X, permit protocol Y from same IP | First matching rule wins | 📝 Future |

---

### 4.3 TCP Flags (7 cases)

#### Functional Test Cases (2 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected RX | Status |
|-------|-------------|-----|---------------|------------|-------------|--------|
| **L3-08** | Deny TCP SYN (new connections) | B | `IP()/TCP(dport=80, flags="S")` from DUT2 | Deny TCP SYN flag on Ethernet0 INGRESS | 0% | 📝 Ready |
| **L3-09** | Permit TCP ACK (established) | B | `IP()/TCP(dport=80, flags="A", seq=100, ack=1)` from DUT2 | Permit TCP ACK flag, deny others | ≥90% | 📝 Ready |

#### Negative/Edge Case Tests (2 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected Result | Status |
|-------|-------------|-----|---------------|------------|-----------------|--------|
| **L3-N06** | TCP flags with invalid combinations (SYN+FIN) | NEG | `IP()/TCP(flags="SF")` | Deny invalid flag combinations | Dropped or flagged invalid | 📝 Future |
| **L3-N07** | TCP flag match with zero flags | NEG | `IP()/TCP(flags=0x00)` | Deny zero flags | Handled per policy (unusual) | 📝 Future |

#### Robustness/Persistence Tests (3 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected Behavior | Status |
|-------|-------------|-----|---------------|------------|------------------|--------|
| **L3-R07** | TCP flag rule persistence across connection resets | B | RST flag, then retransmit, rules persist | TCP flag rules | Rules persist, behavior consistent | 📝 Future |
| **L3-R08** | Stateful TCP flag evaluation under sustained traffic | B | Long-lived TCP stream, 10000+ packets | TCP flag matching | Consistent flag evaluation, no state leak | 📝 Future |
| **L3-R09** | Concurrent TCP SYN and ACK from different flows | B | Two TCP flows (one SYN, one ACK) simultaneously | Multiple TCP rules | Each evaluated correctly, no cross-talk | 📝 Future |

---

### 4.4 Combined & Functional (10 cases)

#### Functional Test Cases (3 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected RX | Status |
|-------|-------------|-----|---------------|------------|-------------|--------|
| **L3-10** | Deny 5-tuple flow | B | `IP(src="10.0.0.99", dst="20.0.0.2")/TCP(dport=80)` | Deny 5-tuple on Ethernet0 INGRESS | 0% | 📝 Ready |
| **L3-11** | Implicit deny-all | B | `IP(src="172.16.0.1")/ICMP()` (no matching permit) | No explicit permit rule | 0% | 📝 Ready |
| **L3-12** | Deny DSCP EF (tos=0xB8) | HW | `IP(tos=0xB8)/UDP()` from DUT2 | Deny DSCP EF on Ethernet0 INGRESS | 0% | 📝 HW-only |

#### Negative/Edge Case Tests (2 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected Result | Status |
|-------|-------------|-----|---------------|------------|-----------------|--------|
| **L3-N08** | 5-tuple with all zeros (no match) | NEG | `IP(src="0.0.0.0", dst="0.0.0.0")/TCP(sport=0, dport=0)` | Deny 5-tuple with zeros | Handled per policy | 📝 Future |
| **L3-N09** | DSCP value edge cases (0, 63) | NEG | `IP(tos=0x00)/UDP()` and `IP(tos=0xFC)/UDP()` | Deny DSCP 0 and 63 | Correct handling | 📝 Future |

#### Robustness/Persistence Tests (5 cases)

| TC ID | Description | Tag | Scapy Traffic | DUT Config | Expected Behavior | Status |
|-------|-------------|-----|---------------|------------|------------------|--------|
| **L3-R10** | ACL rule persistence after DSCP config change | HW | DSCP ACL, then modify QoS policies | DSCP rules with QoS changes | Rules unaffected by QoS config | 📝 Future |
| **L3-R11** | 5-tuple rule accuracy under 100K+ packet streams | B | Long sustained flow, verify rule hit counter | 5-tuple rules | Counter accurate, no packet loss | 📝 Future |
| **L3-R12** | Mixed 5-tuple and subnet-based rules | B | Apply both types simultaneously, varied traffic | Both rule types active | All rules evaluated without interference | 📝 Future |
| **L3-R13** | ACL rule atomicity during rapid reconfig | B | Update 5-tuple rule while traffic active | Rapid rule updates | Atomic update, no intermediate state inconsistency | 📝 Future |
| **L3-R14** | Implicit deny enforcement with permit rules present | B | Permit some traffic, deny others implicitly | Mixed permit/deny rules | Implicit deny works, no false forwards | 📝 Future |

---

### Test Summary

| Suite | Functional | Negative | Robustness | Total |
|-------|------------|----------|------------|-------|
| **L3 ACL** | **12** | **9** | **13** | **34** |

---

### Pass / Fail Criteria

| ACL Action | Pass Condition |
|------------|--------|
| **PERMIT** | RX count ≥ 90% of TX count |
| **DENY** | RX count == 0 (all packets dropped) |
| **Counter** | DUT ACL hit counter == TX packet count |

---

## Key Features (Phase 1-4)

### ✅ SpyTest Framework Integration
- Full framework support (st.log, st.report_pass/fail, cleanup)
- Centralized logging and reporting
- Automatic module/class lifecycle management

### ✅ DUT-Based Scapy Traffic Generation
- Non-blocking execution via `scapy_traffic.send_traffic()`
- Automatic script deployment to DUT2 via SSH
- Configurable parameters: source IP, packets, duration, rate

### ✅ Tcpdump Forensic Verification
- Background packet capture on DUT3:Ethernet0
- UDP port filtering (54321)
- Scapy `rdpcap()` for exact packet counts
- Pcap files preserved for post-test analysis

### ✅ ACL Configuration via API
- `acl_api.create_acl_table()` - Create ACL tables
- `acl_api.create_acl_rule()` - Create rules with flexible matching
- `acl_api.delete_acl_table()` - Automatic cleanup (cascades to rules)

### ✅ Silent Pass Prevention
- Guard 1: TX must be > 0 (traffic actually generated)
- Guard 2: RX must be from pcap (verified reception)
- Guard 3: Loss within acceptable range

### ✅ Professional-Grade Architecture
- Error handling with detailed logging
- Automatic cleanup via try/finally blocks
- Comprehensive docstrings and comments
- Portable to hardware TGen (IxNetwork, Spirent) in future

---

## Comparison: Before & After (Phases 1-4)

### Before (External TGen Pattern)
```
❌ Manual orchestration of external hosts
❌ No SpyTest framework control
❌ Ephemeral verification (sniff() in memory)
❌ Scattered logging across hosts
❌ Error-prone manual cleanup
❌ Hard to extend and maintain
```

### After (3-SONiC-DUT SpyTest-Native, Phases 1-4)
```
✅ Full SpyTest framework integration
✅ Centralized logging and reporting
✅ Tcpdump forensic verification (pcap files)
✅ Non-blocking traffic generation
✅ Automatic cleanup
✅ ACL rules fully configurable
✅ Production-grade test automation
✅ Portable architecture
```

---

## Troubleshooting

### Issue: Traffic Not Flowing

**Check 1: L3 Connectivity**
```bash
# From DUT2
ping 10.0.0.254  # Should reach DUT1 gateway

# From DUT3
ping 20.0.0.254  # Should reach DUT1 gateway
```

**Check 2: Interface Status**
```bash
# On DUT1
show interface status | grep -E "Ethernet0|Ethernet4"
# Both should show "U" (UP)
```

**Check 3: Routing**
```bash
# On DUT1
show ip route
# Should show routes to 10.0.0.0/24 and 20.0.0.0/24
```

### Issue: Pcap File Empty

**Cause**: Tcpdump not capturing properly

**Solution**:
1. Verify tcpdump is running: `ps aux | grep tcpdump`
2. Check filter syntax: `sudo tcpdump -i Ethernet0 udp port 54321 -c 5`
3. Verify traffic is actually arriving: `sudo tcpdump -i Ethernet0 -c 5`

### Issue: ACL Rules Not Applied

**Check**: ACL hit counters
```bash
DUT1# show acl table L3_ACL_TABLE
DUT1# show acl-rule RULE_1_DENY_SOURCE
```

**Verify**: Rule matches expected traffic
```bash
# If hit counter is 0, ACL rule is not matching traffic
# Debug by:
# 1. Check source IP in traffic generation
# 2. Verify ACL rule definition (DSCP, port, protocol)
# 3. Confirm ACL is applied to correct port/direction
```

---

## Test Case Implementation Details

### L3-01: Deny Source IP (Host-Level)

**Purpose**: Verify ACL can deny traffic from a specific source IP address

**Execution Flow**:
1. Configure ACL rule on DUT1:Ethernet0 INGRESS: Deny src=10.0.0.99/32
2. Start tcpdump on DUT3:Ethernet0 listening for UDP port 54321
3. Generate 100 UDP packets from DUT2 with source IP 10.0.0.99
4. Verify RX count from pcap = 0 (all packets dropped by ACL)

**Expected Result**: DENY (RX=0, all packets from source blocked)

---

### L3-02: Deny Source Subnet (/24)

**Purpose**: Verify ACL can deny an entire source subnet, not just individual hosts

**Execution Flow**:
1. Configure ACL rule on DUT1:Ethernet0 INGRESS: Deny src=10.0.0.0/24
2. Start tcpdump on DUT3:Ethernet0
3. Generate 100 UDP packets from DUT2 with source IP anywhere in 10.0.0.0/24 (e.g., 10.0.0.50)
4. Verify RX count from pcap = 0 (all packets from subnet blocked)

**Expected Result**: DENY (RX=0, entire subnet blocked)

---

### L3-03: Deny Destination IP (Host-Level)

**Purpose**: Verify ACL can deny traffic destined to a specific IP address

**Execution Flow**:
1. Configure ACL rule on DUT1:Ethernet0 INGRESS: Deny dst=20.0.0.99/32
2. Start tcpdump on DUT3:Ethernet0
3. Generate 100 TCP packets from DUT2 (10.0.0.1) destined to DUT3's IP (20.0.0.99)
4. Verify RX count from pcap = 0 (all packets to destination dropped)

**Expected Result**: DENY (RX=0, destination blocked)

---

### L3-04: Deny ICMP

**Purpose**: Verify ACL can deny ICMP protocol entirely

**Execution Flow**:
1. Configure ACL rule on DUT1:Ethernet0 INGRESS: Deny protocol=ICMP
2. Start tcpdump on DUT3:Ethernet0
3. Generate 100 ICMP echo-request packets (type=8) from DUT2
4. Verify RX count from pcap = 0

**Expected Result**: DENY (RX=0, ICMP protocol blocked)

---

### L3-05: Deny UDP, Permit TCP

**Purpose**: Verify ACL can selectively block one protocol while permitting another

**Execution Flow**:
1. Configure ACL rules on DUT1:Ethernet0 INGRESS:
   - Rule 1: Deny protocol=UDP
   - Rule 2: Permit protocol=TCP (explicit)
2. Start tcpdump on DUT3:Ethernet0
3. **Test Part A**: Generate 100 UDP packets (dport=53) from DUT2 → RX should be 0
4. **Test Part B**: Generate 100 TCP packets (dport=80) from DUT2 → RX should be ≥90

**Expected Result**: Selective protocol control (UDP=DENY, TCP=PERMIT)

---

### L3-06: Deny TCP Destination Port 80

**Purpose**: Verify ACL can deny specific TCP port (web traffic)

**Execution Flow**:
1. Configure ACL rule on DUT1:Ethernet0 INGRESS: Deny protocol=TCP, dport=80
2. Start tcpdump on DUT3:Ethernet0
3. Generate 100 TCP packets from DUT2 with SYN flag, dport=80
4. Verify RX count from pcap = 0

**Expected Result**: DENY (RX=0, TCP port 80 blocked)

---

### L3-07: Deny UDP Destination Port 53

**Purpose**: Verify ACL can deny specific UDP port (DNS traffic)

**Execution Flow**:
1. Configure ACL rule on DUT1:Ethernet0 INGRESS: Deny protocol=UDP, dport=53
2. Start tcpdump on DUT3:Ethernet0
3. Generate 100 UDP packets from DUT2 with dport=53
4. Verify RX count from pcap = 0

**Expected Result**: DENY (RX=0, UDP port 53 blocked)

---

### L3-08: Deny TCP SYN (New Connections)

**Purpose**: Verify ACL can block TCP SYN flag to prevent new connection establishment

**Execution Flow**:
1. Configure ACL rule on DUT1:Ethernet0 INGRESS: Deny TCP, flags=SYN
2. Start tcpdump on DUT3:Ethernet0
3. Generate 100 TCP packets from DUT2 with SYN flag set (flags="S")
4. Verify RX count from pcap = 0

**Expected Result**: DENY (RX=0, SYN packets blocked)

---

### L3-09: Permit TCP ACK (Established Session)

**Purpose**: Verify ACL can permit TCP ACK flag for established connections

**Important Note**: Packets are **crafted** (not from real TCP handshake):
- Source/dest IPs and ports are static
- TCP ACK flag is set (flags="A")
- seq/ack numbers are predetermined (seq=100, ack=1)
- DUT does NOT verify TCP sequence/acknowledgment numbers

**Execution Flow**:
1. Configure ACL rule on DUT1:Ethernet0 INGRESS: Permit TCP, flags=ACK
2. Start tcpdump on DUT3:Ethernet0
3. Generate 100 TCP packets from DUT2 with ACK flag set (flags="A")
4. Verify RX count from pcap ≥ 90 (packets forwarded)

**Expected Result**: PERMIT (RX=≥90%, ACK packets forwarded)

---

### L3-10: Deny 5-Tuple Flow

**Purpose**: Verify ACL can match and deny complete 5-tuple (src IP, dst IP, protocol, src port, dst port)

**Execution Flow**:
1. Configure ACL rule on DUT1:Ethernet0 INGRESS:
   - Deny: src=10.0.0.99, dst=20.0.0.2, protocol=TCP, dport=80, sport=any
2. Start tcpdump on DUT3:Ethernet0
3. Generate 100 TCP packets from DUT2 with src=10.0.0.99, dst=20.0.0.2, dport=80
4. Verify RX count from pcap = 0

**Expected Result**: DENY (RX=0, 5-tuple flow blocked)

---

### L3-11: Implicit Deny-All

**Purpose**: Verify ACL enforces implicit deny-all for traffic not matching any permit rule

**Execution Flow**:
1. Configure ACL table with NO explicit rules (or only deny rules, no permits)
2. Start tcpdump on DUT3:Ethernet0
3. Generate 100 ICMP packets from DUT2 with src=172.16.0.1 (not in any subnet)
4. Verify RX count from pcap = 0 (implicitly dropped)

**Expected Result**: DENY (RX=0, implicit deny-all enforced)

---

### L3-12: Deny DSCP EF (QoS/ToS Field)

**Status**: **Hardware-only** — SONiC-VS typically does not support DSCP classification in ACL

**Purpose**: Verify ACL can match and deny packets with specific DSCP value (EF = Expedited Forwarding)

**Execution Flow**:
1. Configure ACL rule on DUT1:Ethernet0 INGRESS: Deny DSCP=EF (ToS byte 0xB8)
2. Start tcpdump on DUT3:Ethernet0
3. Generate 100 UDP packets from DUT2 with IP ToS byte = 0xB8
4. Verify RX count from pcap = 0 (DSCP EF packets dropped)

**Note**: DSCP is 6 MSBs of IP ToS byte: 0xB8 = 10111000 binary → DSCP=46 (EF)

**Expected Result**: DENY (RX=0, DSCP EF packets blocked) — HW only

---

### Negative Test Examples

#### L3-N01: Overlapping IP Subnets (More Specific Rule Precedence)

**Purpose**: Verify ACL respects subnet specificity when rules overlap

**Example**:
- Rule 1: Deny 10.0.0.0/24
- Rule 2: Permit 10.0.0.0/25 (more specific)

**Expected**: More specific rule (/25) takes precedence in matching

---

#### L3-N02: IP Broadcast Address

**Purpose**: Verify ACL handling of broadcast packets (255.255.255.255)

**Example**: `IP(dst="255.255.255.255")/ICMP()`

**Expected**: Platform-dependent (may be dropped automatically or per ACL rule)

---

#### L3-N06: Invalid TCP Flag Combinations (SYN+FIN)

**Purpose**: Verify ACL handling of malformed/invalid TCP flags

**Example**: `IP()/TCP(flags="SF")` (SYN and FIN both set, invalid for normal TCP)

**Expected**: Dropped or flagged as invalid (implementation-dependent)

---

### Robustness Test Execution Strategy

#### L3-R01: ACL Rule Persistence After IP Config Change

**Execution**:
1. Configure ACL rule denying 10.0.0.99
2. Send traffic from 10.0.0.1 (should PASS)
3. Send traffic from 10.0.0.99 (should DROP due to rule)
4. **Modify DUT2's IP** from 10.0.0.1 to 10.0.0.100 (change `ip addr` on DUT2:Ethernet0)
5. Send traffic from new IP 10.0.0.100 (should PASS; rule doesn't match)

**Verification**: ACL rule continues to work correctly after host IP reconfiguration

---

#### L3-R02: High-Frequency Rule Updates with Live Traffic

**Execution**:
1. Start continuous traffic from DUT2 (100 pps)
2. Rapidly add/remove ACL rules (100+ operations per sec) via DUT1 CLI
3. Monitor RX on DUT3 for anomalies (sudden drops/passes)
4. Verify final DUT state matches expected rules

**Pass Criteria**: No errors, consistent final state, no unintended packet loss

---

#### L3-R11: 5-Tuple Rule Accuracy Under 100K+ Packet Streams

**Execution**:
1. Configure 5-tuple ACL rules
2. Send sustained high-volume traffic (100K+ packets)
3. Query DUT ACL hit counter: `show acl RULE_NAME`
4. Verify counter matches TX packet count (±1 packet margin)

**Pass Criteria**: Counter accurate, no packet loss, consistent rule evaluation

---

### Traffic Generation Notes

**DUT2 (TX Host) - Scapy Traffic Generation**:
- Non-blocking traffic script execution via SSH
- Configurable: source IP, protocol, port, flags, packet count, duration
- Uses `scapy_traffic.send_traffic()` SpyTest API
- Returns TX count to test for validation

**DUT3 (RX Host) - Tcpdump Verification**:
- Background tcpdump listening on Ethernet0, UDP port 54321
- Captures to pcap file: `/tmp/l3_XX_rx.pcap`
- Scapy `rdpcap()` parses pcap for exact packet counts
- Preserved for post-test manual verification

---

## Important Test Notes

### L3-R02 and High-Frequency Rule Updates

If DUT CLI is too slow for 100+ operations/sec, use **SM_ISCLI batched commands** (SONiC Management CLI batching) for performance.

### L3-12 (DSCP EF) and SONiC-VS

SONiC-VS (virtual switch) typically **does NOT support DSCP classification** in ACL rules. This test:
- ✅ **Passes on hardware devices** (ASIC with TCAM support)
- ❌ **Skipped or fails on SONiC-VS** (expected behavior)

Mark L3-12 with `@pytest.mark.hardware_required` to skip on VS.

### Counter Validation

**Current Implementation Note**: Per-test cleanup fixture removes ACL tables immediately after each test. If counter validation is needed, modify fixture to preserve tables for post-test inspection, then remove.

---

## Related Documentation

- `REFACTORING_COMPLETE.md` - Phase-by-phase completion details
- `REFACTORING_DELIVERY_SUMMARY.md` - Executive summary and roadmap
- `PHASE_4_ACL_INTEGRATION_COMPLETE.md` - ACL API integration details
- `test_l3_acl_basic_refactored.py` - Complete test script with all methods
- `spytest/vars/routing/l3_acl/vars_l3_acl.yaml` - Test case definitions
- `testbeds/testbed_acl.yaml` - Testbed configuration

---

## Key Files

| File | Type | Status | Purpose |
|------|------|--------|---------|
| `testbeds/testbed_acl.yaml` | Config | ✅ Complete | 3-DUT topology, all devices as sonic |
| `test_l3_acl_basic_refactored.py` | Test | ✅ Complete | SpyTest-native test framework |
| `spytest/vars/routing/l3_acl/vars_l3_acl.yaml` | Config | ✅ Complete | ACL and traffic parameters |
| `acl-l3.md` | Doc | ✅ Updated | This testplan (3-DUT SpyTest-native) |
| `apis/common/scapy_traffic_advanced.py` | API | ✅ Complete | Advanced Scapy (DSCP, TCP flags, TTL) |

---

## Project Status

**Current**: ✅ Phases 1, 2, 4 Complete / Phase 3 Complete

**Phases**:
- ✅ Phase 1: Testbed Refactoring (TG→DUT, TGEN→sonic)
- ✅ Phase 2: Test Script Refactoring (SpyTest-native, tcpdump)
- ✅ Phase 3: Advanced Scapy API (DSCP, TCP flags, TTL)
- ✅ Phase 4: ACL Configuration Integration (acl_api)
- ✅ Phase 5: Documentation Update (THIS FILE)
- ⏳ Phase 6: Validation & Testing (when ready)

**Ready for**: Immediate test execution in your environment

---

## Next Steps

1. **Verify Testbed**: Confirm all 3 DUTs are accessible and L3 configured
2. **Run Baseline Test**: `test_l3_baseline_permit_all()` to validate connectivity
3. **Execute ACL Tests**: Run L3-01, L3-02, L3-03 tests
4. **Compare Results**: Validate against original external TGen approach
5. **Document Findings**: Record any discrepancies or observations

---

**Document Version**: 2.0 (Refactored for 3-SONiC-DUT SpyTest-Native)
**Updated**: 2026-03-11
**Status**: ✅ Ready for Testing

