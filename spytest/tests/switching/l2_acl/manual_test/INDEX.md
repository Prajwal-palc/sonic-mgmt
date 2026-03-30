# L2 ACL Manual Testing Documentation Index

This directory contains comprehensive manual testing documentation for all 19 L2 ACL test cases from the SONiC L2 ACL test plan.

## Documentation Structure

### Master Guide
- **L2_ACL_MANUAL_TEST_GUIDE.md** - Overall testing guide with topology, prerequisites, and general procedures

### Functional Test Cases (8 tests)
1. **L2-01_manual_log.md** - Permit exact source MAC
2. **L2-02_manual_log.md** - Deny exact source MAC
3. **L2-03_manual_log.md** - Deny exact destination MAC
4. **L2-04_manual_log.md** - Deny broadcast destination MAC
5. **L2-05_manual_log.md** - Deny EtherType ARP (0x0806)
6. **L2-06_manual_log.md** - Deny specific VLAN (VLAN 100)
7. **L2-07_manual_log.md** - Permit VLAN 10, deny VLAN 200
8. **L2-08_manual_log.md** - ACL rule priority evaluation

### Negative/Edge Case Tests (3 tests)
1. **L2-N01_manual_log.md** - MAC case sensitivity (uppercase vs lowercase)
2. **L2-N02_manual_log.md** - Multicast destination MAC handling
3. **L2-N03_manual_log.md** - Invalid/corrupt MAC handling

### Robustness/Persistence Tests (8 tests)
1. **L2-R01_manual_log.md** - ACL rule persistence after DUT reboot
2. **L2-R02_manual_log.md** - ACL modification while traffic is active
3. **L2-R03_manual_log.md** - Multiple ACL updates in rapid succession
4. **L2-R04_manual_log.md** - Concurrent traffic on denied/allowed MAC pairs
5. **L2-R05_manual_log.md** - ACL counter accuracy with 1000+ packets
6. **L2-R06_manual_log.md** - VLAN rule persistence across config changes
7. **L2-R07_manual_log.md** - MAC address aging/timeout behavior
8. **L2-R08_manual_log.md** - Mixed permit/deny rules with same match criteria

---

## Test Topology

All tests use the same 3-DUT topology specified in `testbeds/testbed_acl.yaml`:

```
┌────────────────┐                    ┌────────────────┐                    ┌────────────────┐
│     DUT2       │                    │     DUT1       │                    │     DUT3       │
│  (TX Traffic   │                    │  (ACL Device)  │                    │  (RX Receiver) │
│   Generator)   │                    │                │                    │                │
│ 192.168.100.67 │                    │ 192.168.100.190│                    │ 192.168.100.134│
│                │                    │                │                    │                │
│ Ethernet24 ◄───┼────────────────────┼─ Ethernet40    │                    │                │
└────────────────┘                    └────────────────┘                    └────────────────┘
                                                   │
                                         L2 ACL Rules (Ingress)
```

**Device Details:**
- D1 (DUT): 192.168.100.190 - Password: root@123
- D2 (TX): 192.168.100.67  - Password: broadcom
- D3 (RX): 192.168.100.134 - Password: sonic@123

---

## Test Case Structure

Each manual test log file includes:

1. **Test Case Information** - ID, description, category, expected outcome
2. **Topology Diagram** - Visual representation of test connections
3. **Configuration Steps** - Complete device configuration commands
4. **ACL Configuration** - ACL rule creation and verification
5. **RX Device Setup** - tcpdump listener configuration
6. **TX Traffic Generation** - Scapy script for traffic generation
7. **Verification Phase** - Counter checks and packet capture analysis
8. **Cleanup** - ACL removal and configuration cleanup
9. **Test Results** - Pass/fail status with detailed metrics
10. **Conclusion** - Test summary and key findings

---

## Pass/Fail Criteria

| ACL Action | Pass Condition |
|-----------|-----------------|
| **PERMIT** | RX count ≥ 90% of TX count |
| **DENY** | RX count = 0 (all packets dropped) |
| **COUNTER** | DUT ACL hit counter = TX packet count |

---

## How to Run Tests

### Prerequisites (One-Time Setup)

1. **Verify Device Connectivity**
   ```bash
   ping 192.168.100.190    # D1 (DUT)
   ping 192.168.100.67     # D2 (TX)
   ping 192.168.100.134    # D3 (RX)
   ```

2. **Install Scapy on TX/RX Devices**
   ```bash
   ssh admin@192.168.100.67
   sudo python3 -m pip install scapy --break-system-packages

   ssh admin@192.168.100.134
   sudo apt-get install tcpdump
   ```

3. **Configure DUT Interfaces** (see L2_ACL_MANUAL_TEST_GUIDE.md)

### For Each Test Case

1. Read the corresponding manual test log file (e.g., L2-01_manual_log.md)
2. Follow Step 1-2 for DUT and ACL configuration
3. Follow Step 3-4 for RX/TX traffic setup
4. Follow Step 5 for verification
5. Follow Step 6 for cleanup

---

## Files Available

```
├── L2_ACL_MANUAL_TEST_GUIDE.md          [Master testing guide]
├── L2-01_manual_log.md                  [Functional: Permit source MAC]
├── L2-02_manual_log.md                  [Functional: Deny source MAC]
├── L2-03_manual_log.md                  [Functional: Deny dest MAC]
├── L2-04_manual_log.md                  [Functional: Deny broadcast]
├── L2-05_manual_log.md                  [Functional: Deny EtherType ARP]
├── L2-06_manual_log.md                  [Functional: Deny VLAN 100]
├── L2-07_manual_log.md                  [Functional: Multi-VLAN rules]
├── L2-08_manual_log.md                  [Functional: Rule priority]
├── L2-N01_manual_log.md                 [Negative: Case sensitivity]
├── L2-N02_manual_log.md                 [Negative: Multicast MAC]
├── L2-N03_manual_log.md                 [Negative: Invalid MAC]
├── L2-R01_manual_log.md                 [Robustness: Persistence after reboot]
├── L2-R02_manual_log.md                 [Robustness: Modification during traffic]
├── L2-R03_manual_log.md                 [Robustness: Rapid updates]
├── L2-R04_manual_log.md                 [Robustness: Concurrent traffic]
├── L2-R05_manual_log.md                 [Robustness: Counter accuracy 1000+]
├── L2-R06_manual_log.md                 [Robustness: VLAN persistence]
├── L2-R07_manual_log.md                 [Robustness: MAC aging]
├── L2-R08_manual_log.md                 [Robustness: Mixed permit/deny]
└── INDEX.md                             [This file]
```

---

## Platform Support

All tests are designed for both platforms:
- **VS (Virtual SONiC)** - Faster iteration, no hardware dependencies
- **HW (Hardware)** - Real devices, hardware-specific behavior

Platform-specific notes are included in each test case.

---

## Test Execution Summary

| Category | Count | Status |
|----------|-------|--------|
| Functional | 8 | Complete |
| Negative/Edge Cases | 3 | Complete |
| Robustness | 8 | In Progress |
| **Total** | **19** | **Planned** |

---

## Key Testing Tools

- **tcpdump** - Packet capture and verification on RX device
- **Scapy** - Traffic generation on TX device
- **SSH** - Device management and CLI access
- **Python3** - Scripting for traffic generation and analysis

---

## References

- **Test Plan**: `tests/switching/l2_acl/docs/acl-l2.md`
- **Testbed**: `testbeds/testbed_acl.yaml`
- **DUT Setup**: `tests/switching/l2_acl/docs/l2_dut_setup.md`
- **Host Setup**: `tests/switching/l2_acl/docs/l2_host_setup.md`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify device IP, credentials, and network connectivity |
| Scapy import error | Run `pip install scapy --break-system-packages` |
| tcpdump permission denied | Use `sudo` for tcpdump commands |
| No RX packets (no ACL) | Verify port is in switchport mode, VLAN configuration |
| No RX packets (with ACL) | Verify ACL rule syntax, check with `show access-list` |
| MAC address mismatch | Remember that DUT compares MACs case-insensitively |

---

**Documentation Version**: 1.0
**Last Updated**: 2026-03-18
**Status**: Testing Documentation Complete
**Coverage**: 19 Test Cases (Functional, Negative, Robustness)

