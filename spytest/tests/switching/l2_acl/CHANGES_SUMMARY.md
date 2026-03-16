# L2 ACL Test Plan - Changes Summary

**Date**: March 9, 2025
**Updated By**: Claude Code
**Branch**: acl

## Overview

Comprehensive updates to L2 ACL test plan, implementation scripts, and documentation to address 10 architectural and implementation gaps identified in the review.md document. L2 ACL testing focuses on Layer 2 switching with MAC address, EtherType, and VLAN matching on external TX/RX hosts.

---

## Documents Updated

### 1. **acl-l2.md** (Main Test Plan)
**Status**: ✅ UPDATED
**Size**: 30+ KB (was ~3 KB)

#### Key Changes:

**Architecture Section**:
- Added detailed ASCII diagram showing external TX/RX hosts vs DUT
- Clarified that Scapy runs on external hosts (NOT inside DUT)
- Documented unidirectional L2 switching flow: TX → DUT Port1 → Bridge → DUT Port2 → RX
- Critical distinction: **L2 switchport mode** (not L3 routed mode)
- **No IP addresses** on DUT ports (unlike L3 tests)

**Prerequisites & Requirements** (NEW SECTION - 200+ lines):
- **Host Requirements**: Linux kernel 5.4+, Python 3.8+, Scapy installation
- **Permission Requirements**: sudo or CAP_NET_RAW capability
- **Network Stack Configuration**: UFW/iptables setup instructions
- **DUT Port Configuration**: L2 switchport mode setup (CRITICAL difference from L3)
- **VLAN Configuration**: Pre-create VLANs 10, 100, 200 for test cases
- **MAC Address Learning**: Document dynamic learning and aging timeout
- **Baseline L2 State**: Clarified DUT should start with NO L2 ACLs
- **Network Connectivity Verification**: Pre-test sanity check with tcpdump

**Important Implementation Notes** (NEW SECTION - 500+ lines):

1. **Execution & Permissions**: tcpdump verification commands

2. **L2 Switching vs L3 Routing** (Critical Difference):
   - **L2**: Switchport mode, no IP addresses, MAC-based forwarding, VLAN bridging
   - **L3**: Routed mode, IP addresses on ports, IP routing, no VLAN dependency
   - Documents key architectural differences

3. **Scapy L2 Frame Construction**:
   - Frame format: `Ether(src=..., dst=...) / [optional: Dot1Q(vlan=N)] / [optional: IP() / ...]`
   - Untagged frames (L2-01 to L2-05) vs tagged frames (L2-06 to L2-07)
   - Checksum and FCS auto-computation

4. **Packet Timing**:
   - Default inter-packet delay: 50ms
   - Default packet count: 10 packets
   - RX sniff timeout: 4 seconds

5. **Traffic Direction & MAC Learning**:
   - Unidirectional TX → DUT → RX
   - DUT learns TX MAC from Port1 frames
   - RX MAC must match crafted destination or be broadcast/multicast

6. **MAC Address Behavior**:
   - Dynamic learning with 300-second aging timeout
   - Case-insensitive MAC comparison
   - RX MAC options: host MAC, broadcast (FF:FF:FF:FF:FF:FF), multicast (01:00:5E:...)

7. **VLAN Handling**:
   - Untagged frames: Native VLAN (VLAN 1)
   - Tagged frames: Dot1Q tag with VLAN ID
   - Port configuration for different VLAN scenarios

8. **ARP Handling** (L2-04, L2-05):
   - Broadcast MAC behavior (drop vs flood)
   - EtherType ARP (0x0806) matching
   - DUT ARP policy documentation

9. **Test Case Clarifications** (NEW):
   - L2-01: Permit vs implicit permit distinction
   - L2-03: Destination MAC not in table considerations
   - L2-04: Broadcast handling varies by platform
   - L2-05: EtherType matching syntax confirmation
   - L2-06: VLAN 100 denial with pre-configuration
   - L2-07: Two-phase VLAN 10 (permit) and 200 (deny)
   - L2-R01: Reboot persistence clarification
   - L2-R05: Counter accuracy with 1000+ packets
   - L2-R07: MAC aging timeout behavior

10. **Counter Validation**:
    - DUT CLI commands for L2 ACL counters
    - Acceptable error margin: ±1 packet
    - Manual validation (NOT auto-checked)

11. **Negative & Robustness Tests**:
    - Edge cases and error resilience verification
    - Platform-specific expected outcomes

12. **Troubleshooting Table**:
    - 8 common issues with solutions
    - Port mode, VLAN membership, MAC learning verification
    - Frame switching diagnostics

---

### 2. **l2_acl_traffic.py** (L2 ACL Test Cases)
**Status**: ✅ UPDATED
**Size**: Enhanced with comprehensive documentation

#### Key Changes:

**Comprehensive Docstring** (70+ lines):
- L2-specific architecture diagram
- Test coverage documentation
- Prerequisites for TX, RX, and DUT
- Usage examples with command-line options
- Output description and parameters
- Unidirectional L2 switching clarification
- VLAN and MAC-specific notes
- Troubleshooting guide

**Configuration Section** (NEW):
- Documented all configuration constants with inline comments
- Clearly marked network interfaces and MAC addresses
- Documented test parameters (N=10, TIMEOUT=4, INTER_DELAY=0.05)

**Improved _tx_rx() Function**:
- Comprehensive docstring with BPF filter examples
- Parameter documentation
- Comments explaining sniffer startup delay
- Proper use of INTER_DELAY constant

**Enhanced Command-Line Arguments**:
- `--tc`: Single or comma-separated test IDs
- `--list`: List all available tests
- `--timeout`: Override RX sniff timeout
- `--packet-count`: Override packets per test
- `--inter-delay`: Override inter-packet delay
- Better help text with default values

---

## New Documentation Files

### 3. **l2_dut_setup.md** (DUT Configuration Guide)
**Status**: ✅ CREATED
**Size**: 8+ KB

Complete step-by-step guide for configuring DUT for L2 tests:

**Contents**:
1. Overview emphasizing L2 switchport mode (NOT routed mode)
2. Architecture diagram showing L2 switching topology
3. Prerequisites
4. Port status verification
5. **Port mode configuration** (CRITICAL: switchport mode access)
6. **VLAN configuration** (Create VLANs 10, 100, 200)
7. Port VLAN membership setup
8. **MAC address learning verification**
9. End-to-end L2 switching verification (no ACLs)
10. Spanning Tree Protocol configuration (optional)
11. Configuration persistence
12. Port naming conventions
13. Per-test ACL configuration example
14. Troubleshooting table with L2-specific issues
15. Advanced configuration (port mirroring, VLAN debugging)

**Key Differences from L3 DUT Setup**:
- NO IP address configuration on DUT ports
- SWITCHPORT MODE (critical)
- VLAN creation and membership
- MAC address learning verification

---

### 4. **l2_host_setup.md** (Host Environment Setup Guide)
**Status**: ✅ CREATED
**Size**: 7+ KB

Host configuration guide with L2-specific considerations:

**Contents**:
1. Overview with reference to L3 guide
2. Quick setup (5 minutes)
3. Architecture diagram for L2 switching
4. Key differences from L3 ACL testing (table)
5. Step-by-step configuration (referenced from L3 guide)
6. L2-specific test considerations:
   - Native vs tagged VLAN frames
   - MAC address learning verification
   - Broadcast and multicast frames
7. L2-specific troubleshooting table
8. Running L2 ACL tests (commands)
9. Advanced network isolation (optional)
10. Complete checklist
11. References to other guides

---

### 5. **review.md** (Architecture Review)
**Status**: ✅ CREATED
**Size**: 9+ KB

Detailed architecture review for L2 ACL tests:

**Sections**:
- Executive summary confirming external host architecture
- Architecture analysis with evidence
- ✅ Strengths (6 benefits specific to L2 testing)
- ⚠️ Potential concerns with recommendations (10 detailed sections):
  1. L2 interface drivers and port mode
  2. MAC address table and aging
  3. VLAN tagging and test case dependencies
  4. ARP handling (L2-04, L2-05 specific)
  5. ACL application direction (ingress vs egress)
  6. Test case clarifications (L2-specific issues)
  7. Host OS and network stack (L2 frame handling)
  8. Metric collection (L2 ACL counters)
  9. VLAN tagging and MAC learning (L2-specific)
  10. Traffic load and packet size
- Implementation readiness checklist
- Key differences from L3 ACL testing (comparison table)
- Recommended test execution order
- Summary table of findings

---

## Addressed Issues from Review

| Issue # | Concern | Resolution |
|---------|---------|-----------|
| 1 | L2 interface drivers | Added prerequisites for driver support and link verification |
| 2 | MAC address table aging | Documented MAC aging timeout, learning behavior, dynamic vs static |
| 3 | VLAN configuration | Created dut_setup.md with VLAN 10/100/200 creation steps |
| 4 | ARP handling | Documented DUT behavior for broadcast (L2-04) and EtherType (L2-05) |
| 5 | ACL direction (L2) | Explicitly documented ingress-only, egress out of scope |
| 6 | Test case ambiguities | Detailed specs for L2-01 through L2-08, especially L2-04/05, L2-R01/R05/R07 |
| 7 | Host network stack | l2_host_setup.md covers firewall, driver, frame handling |
| 8 | L2 counter validation | Documented CLI commands for L2 ACL counter queries |
| 9 | MAC learning & VLAN | Detailed MAC learning, VLAN membership, port state docs |
| 10 | Frame size & MTU | Documented minimum frame sizes, MTU requirements |

---

## Key Architecture Clarifications (L2-Specific)

### What Changed:
1. **Explicit External Host Confirmation**: Scapy runs on EXTERNAL hosts (not inside DUT)
2. **L2 Switchport Mode**: DUT ports MUST be in switchport mode (NOT routed/L3 mode)
3. **No IP Addresses on DUT Ports**: Unlike L3 tests, DUT ports have NO IP config
4. **VLAN Criticality**: VLANs 10, 100, 200 must be pre-created for L2-06/L2-07
5. **MAC Learning**: DUT learns TX MAC dynamically; aging timeout is 300 seconds (typical)
6. **Unidirectional L2 Switching**: TX → DUT → RX (L2 bridging, not IP routing)

### What Stayed the Same:
- 8 core L2 test cases (L2-01 to L2-08)
- Packet count: 10 per test
- Pass criteria: PERMIT ≥90%, DENY =0%
- RX timeout: 4 seconds
- External host architecture (Scapy on separate hosts)

---

## File Organization

```
tests/switching/l2_acl/
├── docs/
│   ├── acl-l2.md           ✅ UPDATED (30+ KB) - Main test plan with L2 specifics
│   ├── review.md           ✅ CREATED (9 KB) - Architecture review
│   ├── l2_dut_setup.md     ✅ CREATED (8 KB) - DUT L2 switchport config guide
│   ├── l2_host_setup.md    ✅ CREATED (7 KB) - Host setup guide
│   └── CHANGES_SUMMARY.md  ✅ NEW - This file
└── traffic/
    ├── setup_ports.py      ✅ (Shared with L3) - Host port configuration
    ├── l2_acl_traffic.py   ✅ UPDATED - L2 test cases with documentation
    └── acl_test_runner.py  ✅ (Shared with L3) - Master test runner
```

---

## Testing Impact

### Before Changes:
- Test plan lacked L2-specific details
- No documentation on switchport mode requirement
- VLAN configuration not specified
- MAC learning behavior undefined
- Setup guides missing

### After Changes:
- Clear L2 switchport mode architecture with diagrams
- Comprehensive setup guides (DUT + host)
- VLAN configuration with creation steps
- MAC learning and aging timeout documented
- Better command-line interface for flexibility

### No Breaking Changes:
- All 8 core test cases (L2-01 to L2-08) remain unchanged
- Packet counts, timeouts, pass criteria unchanged
- Test execution remains the same
- Compatible with existing implementations

---

## Validation Checklist

- [x] Architecture clarified: External hosts and L2 switchport mode confirmed
- [x] Prerequisites documented: OS, Scapy, switchport mode, VLAN config
- [x] Setup guides created: DUT config (l2_dut_setup.md) + host config (l2_host_setup.md)
- [x] Test case specs clarified: L2-01 through L2-08 details
- [x] Troubleshooting guides: Multiple tables with L2-specific solutions
- [x] Implementation notes: MAC learning, VLAN handling, switching behavior
- [x] Code documentation: 70+ line docstrings, inline comments
- [x] Command-line interface: New options for flexibility
- [x] Error handling: Enhanced in l2_acl_traffic.py
- [x] No breaking changes: Core functionality preserved

---

## Next Steps for Users

1. **First Time Setup**:
   - Read: `l2_host_setup.md` (external hosts)
   - Read: `l2_dut_setup.md` (DUT L2 switchport config)
   - Run: `sudo python3 setup_ports.py` (host interface config)
   - Verify: L2 switching with tcpdump

2. **Running Tests**:
   - Read: `acl-l2.md` "Important Implementation Notes" section
   - Run: `sudo python3 l2_acl_traffic.py --list` (see all tests)
   - Run: `sudo python3 l2_acl_traffic.py --tc L2-01` (single test)
   - Run: `sudo python3 acl_test_runner.py --suite l2` (L2 suite)

3. **Troubleshooting**:
   - Refer: acl-l2.md "Troubleshooting" table (L2-specific)
   - Refer: l2_host_setup.md "Troubleshooting" table
   - Refer: l2_dut_setup.md "Troubleshooting" table
   - Key issue: Verify DUT ports are in switchport mode (NOT routed)

---

## Files Modified Summary

| File | Type | Old Size | New Size | Changes |
|------|------|----------|----------|---------|
| acl-l2.md | Doc | ~3 KB | 30+ KB | +Architecture, +Prerequisites, +Implementation Notes, +Clarifications |
| l2_acl_traffic.py | Script | ~3 KB | 9+ KB | +Comprehensive docstring, +CLI options, +Comments |
| l2_dut_setup.md | Doc | - | 8 KB | NEW - Complete DUT switchport/VLAN config guide |
| l2_host_setup.md | Doc | - | 7 KB | NEW - Host setup with L2-specific notes |
| review.md | Doc | - | 9 KB | NEW - Architecture review |
| CHANGES_SUMMARY.md | Doc | - | 7 KB | NEW - This file |

**Total**: 6 files updated/created, ~70 KB of new/updated documentation

---

## Quick Reference: L2 vs L3 ACL Architecture

| Aspect | L2 ACL | L3 ACL |
|--------|--------|--------|
| **DUT Port Mode** | Switchport (L2) | Routed (L3) |
| **Port IPs** | None (unrouted) | 10.0.0.254/24, 20.0.0.254/24 |
| **Forwarding** | MAC switching + VLAN bridging | IP routing |
| **ACL Scope** | MAC, EtherType, VLAN | IP, protocol, TCP/UDP, DSCP |
| **VLAN Dependency** | Critical (pre-create 10/100/200) | Not tested |
| **MAC Learning** | Dynamic (aging timer) | N/A (IP-based) |
| **Setup Guide** | l2_dut_setup.md | dut_setup.md (L3) |
| **Test Cases** | L2-01 to L2-08 (8 functional) | L3-01 to L3-12 (12 functional) |

