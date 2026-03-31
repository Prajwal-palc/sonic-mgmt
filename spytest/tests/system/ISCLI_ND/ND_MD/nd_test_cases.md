# IPv6 Neighbor Discovery (ND) Test Case Documentation

## Test Suite Overview

This document provides detailed test case documentation for IPv6 Neighbor Discovery (ND) functionality in SONiC.

---

## TC-ND-BASIC-01: Basic ND Operations Test Suite

### TC-ND-BASIC-01.1: Basic ND Resolution

**Test Case ID:** ND-BASIC-01.1
**Priority:** P0 (Critical)
**Category:** Functional
**Author:** Network Automation Team

**Objective:**
Validate basic IPv6 Neighbor Discovery resolution via ICMPv6 ping.

**Test Steps:**
1. Clear existing IPv6 neighbor entries on DUT1
2. Send ICMPv6 ping from DUT1 to DUT2
3. Verify ping succeeds (0% packet loss)
4. Check ND table for learned entry

**Expected Results:**
- Ping succeeds with 0% packet loss
- ND entry may appear in neighbor table (platform-dependent)
- IPv6 connectivity is established

**Pass/Fail Criteria:**
- PASS: Ping succeeds
- FAIL: Ping fails with 100% packet loss

**Notes:**
- Based on manual testing, ND entries may not always be visible in `show ipv6 neighbors` even when connectivity works
- This is documented behavior for some platforms

---

### TC-ND-BASIC-01.2: ND Entry Re-learning

**Test Case ID:** ND-BASIC-01.2
**Priority:** P1 (High)
**Category:** Functional

**Objective:**
Validate ND entries can be cleared and re-learned.

**Test Steps:**
1. Establish ND entry via ping
2. Clear IPv6 neighbor table using `clear ipv6 neighbors`
3. Verify entry is cleared (or attempt to verify)
4. Send ping again
5. Verify entry is re-learned

**Expected Results:**
- ND table can be cleared
- Ping triggers ND re-learning
- Connectivity is re-established

**Pass/Fail Criteria:**
- PASS: Connectivity works after clear
- FAIL: Connectivity fails after clear

---

### TC-ND-BASIC-01.3: Static ND Entry

**Test Case ID:** ND-BASIC-01.3
**Priority:** P1 (High)
**Category:** Configuration

**Objective:**
Validate static IPv6 neighbor entry configuration and persistence.

**Test Steps:**
1. Clear existing ND entries
2. Configure static ND entry: `ipv6 neighbor <ipv6-addr> <mac-addr>`
3. Verify static entry appears in ND table
4. Verify entry is marked as "Static" or "PERMANENT"
5. Issue `clear ipv6 neighbors` command
6. Verify static entry persists after clear
7. Test connectivity using static entry

**Expected Results:**
- Static ND entry is configured successfully
- Entry appears in ND table with correct MAC address
- Entry is marked as Static/PERMANENT
- Entry persists after clear command
- Connectivity works with static entry

**Pass/Fail Criteria:**
- PASS: Static entry persists after clear and connectivity works
- FAIL: Static entry is removed by clear command

---

## TC-ND-INTF-01: ND Interface Behavior Test Suite

### TC-ND-INTF-01.1: ND Interface Down Behavior

**Test Case ID:** ND-INTF-01.1
**Priority:** P1 (High)
**Category:** Functional

**Objective:**
Validate ND behavior when interface is administratively shut down.

**Test Steps:**
1. Establish baseline connectivity via ping
2. Check initial ND entries
3. Shutdown VLAN interface: `interface Vlan100` → `shutdown`
4. Verify interface status is down
5. Attempt ping (should fail)
6. Check ND table after shutdown
7. Bring interface back up: `no shutdown`
8. Wait for interface to come up (5 seconds)
9. Verify connectivity is restored
10. Check ND table after recovery

**Expected Results:**
- Ping fails when interface is down
- Ping succeeds after interface comes back up
- ND entries are re-learned after interface recovery

**Pass/Fail Criteria:**
- PASS: Ping fails when down, succeeds when up
- FAIL: Behavior is inconsistent

---

### TC-ND-INTF-01.2: ND Interface Flap Recovery

**Test Case ID:** ND-INTF-01.2
**Priority:** P1 (High)
**Category:** Functional

**Objective:**
Validate ND recovery during interface flap (quick shutdown/no shutdown).

**Test Steps:**
1. Establish baseline connectivity
2. Perform interface flap (shutdown immediately followed by no shutdown)
3. Wait for interface recovery (5 seconds)
4. Verify interface comes back up
5. Verify connectivity is restored quickly
6. Test sustained connectivity (10 pings)

**Expected Results:**
- Interface recovers after flap
- ND entries are re-learned quickly
- Sustained connectivity after recovery

**Pass/Fail Criteria:**
- PASS: Connectivity restored within 10 seconds after flap
- FAIL: Connectivity does not recover

---

## TC-ND-MULTI-VLAN-01: Multiple VLAN ND Operations Test Suite

### TC-ND-MULTI-VLAN-01.1: ND Independence Across VLANs

**Test Case ID:** ND-MULTI-VLAN-01.1
**Priority:** P1 (High)
**Category:** Functional

**Objective:**
Validate ND operates independently on multiple VLANs without cross-contamination.

**Test Configuration:**
- VLAN 100: Configured on both DUT1 and DUT2
  - DUT1: 2001:db8:100::1/64
  - DUT2: 2001:db8:100::2/64
- VLAN 200: Configured only on DUT1 (DUT2 NOT configured)
  - DUT1: 2001:db8:200::1/64
- VLAN 300: Configured only on DUT1 (DUT2 NOT configured)
  - DUT1: 2001:db8:300::1/64

**Test Steps:**
1. Clear all IPv6 neighbors
2. Ping VLAN 100 target (should succeed)
3. Check ND entries for VLAN 100
4. Ping VLAN 200 target (should fail - no peer)
5. Check ND entries for VLAN 200
6. Ping VLAN 300 target (should fail - no peer)
7. Check ND entries for VLAN 300
8. Display all ND entries to verify VLAN isolation
9. Re-verify VLAN 100 still works

**Expected Results:**
- VLAN 100: Ping succeeds, ND entry learned
- VLAN 200: Ping fails, ND entry shows as failed/incomplete
- VLAN 300: Ping fails, ND entry shows as failed/incomplete
- ND entries are isolated per VLAN (no cross-VLAN pollution)
- VLAN 100 continues to work despite failures on other VLANs

**Pass/Fail Criteria:**
- PASS: VLAN 100 works, VLANs 200/300 fail as expected, isolation maintained
- FAIL: Cross-VLAN contamination or VLAN 100 affected by other VLAN failures

---

## TC-ND-AGING-01: ND Aging and State Transitions Test Suite

### TC-ND-AGING-01.1: ND Aging Behavior

**Test Case ID:** ND-AGING-01.1
**Priority:** P2 (Medium)
**Category:** Functional

**Objective:**
Document ND entry aging behavior and state transitions over time.

**Test Steps:**
1. Clear ND table
2. Generate traffic to create ND entry (ping)
3. Check ND table immediately after traffic
4. Wait 10 seconds and check ND table
5. Wait additional 10 seconds and check ND table
6. Verify connectivity still works
7. Document observations

**Expected Results:**
- ND entry is created after traffic
- ND entry may or may not be visible over time
- Connectivity continues to work

**Pass/Fail Criteria:**
- PASS: Behavior is documented, connectivity works throughout
- FAIL: Critical failures in connectivity

**Notes:**
- ND aging timers are platform-specific
- Typical aging: 3-5 minutes total
- State transitions: REACHABLE → STALE → DELAY → PROBE
- Some platforms may not show ND entries in CLI output

---

## Test Configuration Summary

### Network Topology

```
DUT1 (2001:db8:100::1/64) <---> DUT2 (2001:db8:100::2/64)
     Ethernet0                    Ethernet0
         |                            |
      Vlan100                      Vlan100
```

### Multi-VLAN Topology

```
DUT1                                DUT2
-----                               -----
Vlan100: 2001:db8:100::1/64  <--->  Vlan100: 2001:db8:100::2/64
Vlan200: 2001:db8:200::1/64         (not configured)
Vlan300: 2001:db8:300::1/64         (not configured)
```

### Common Configuration

**VLAN Setup:**
```
vlan 100
interface Vlan100
  ipv6 address 2001:db8:100::1/64
  ipv6 enable
  no shutdown

interface Ethernet0
  switchport access Vlan 100
  no shutdown
```

**Static ND Entry:**
```
interface Vlan100
  ipv6 neighbor 2001:db8:100::2 52:54:00:ab:cd:ef
```

**Clear ND Entries:**
```
clear ipv6 neighbors
```

---

## Test Execution Matrix

| Test Case | Topology | Duration | Priority | Automation Status |
|-----------|----------|----------|----------|-------------------|
| ND-BASIC-01.1 | D1D2 | 2 min | P0 | ✅ Automated |
| ND-BASIC-01.2 | D1D2 | 2 min | P1 | ✅ Automated |
| ND-BASIC-01.3 | D1D2 | 3 min | P1 | ✅ Automated |
| ND-INTF-01.1 | D1D2 | 2 min | P1 | ✅ Automated |
| ND-INTF-01.2 | D1D2 | 2 min | P1 | ✅ Automated |
| ND-MULTI-VLAN-01.1 | D1D2 | 3 min | P1 | ✅ Automated |
| ND-AGING-01.1 | D1D2 | 2 min | P2 | ✅ Automated |

---

## Known Platform Behaviors

### ND Entry Visibility

**Observation:** On some platforms, ND entries may not appear in `show ipv6 neighbors` output even when connectivity works perfectly.

**Platforms Affected:** Hardware and VS devices

**Expected Behavior:**
- Ping succeeds with 0% packet loss
- ND resolution happens correctly at kernel level
- CLI may not display the entry

**Verification:**
- Use `ip -6 neigh show` command to check kernel ND table
- Use Redis CLI to check NEIGH_TABLE entries
- Verify connectivity via ping

### Static ND Entry Persistence

**Observation:** Static ND entries persist after `clear ipv6 neighbors` command.

**Expected Behavior:**
- Dynamic entries: Cleared by command
- Static entries: Persist after clear
- Entry type shown as "Static" or "PERMANENT"

**Verification:**
```
show ipv6 neighbors
# Static entries remain after clear
```

### Interface State Impact

**Observation:** ND behavior when interface goes down varies by platform.

**Expected Behaviors:**
- Some platforms: ND entries removed immediately
- Other platforms: ND entries marked as stale but remain
- All platforms: Ping fails when interface is down

---

## Troubleshooting Guide

### Issue: Ping Fails

**Symptoms:**
- 100% packet loss
- "Destination unreachable" messages

**Checks:**
1. Verify interface is up: `show interface Vlan100`
2. Check IPv6 configuration: `show ipv6 interfaces`
3. Verify VLAN membership: `show vlan 100`
4. Check physical connectivity
5. Verify IPv6 is enabled: `show running-config interface Vlan100`

**Resolution:**
- Ensure `ipv6 enable` is configured
- Verify `no shutdown` on interface
- Check physical link status

### Issue: ND Entry Not Found

**Symptoms:**
- `show ipv6 neighbors` shows "No entries found"
- Ping works but entry not visible

**Checks:**
1. Check kernel ND table: `ip -6 neigh show`
2. Check Redis: `redis-cli -n 0 HGETALL "NEIGH_TABLE:Vlan100:<ipv6-addr>"`
3. Verify connectivity with ping

**Resolution:**
- This may be expected behavior
- Document actual behavior
- Verify connectivity works

### Issue: Static Entry Removed

**Symptoms:**
- Static ND entry disappears after reboot or clear

**Checks:**
1. Verify configuration is saved: `show running-config | grep "ipv6 neighbor"`
2. Check configuration syntax
3. Verify interface exists

**Resolution:**
- Re-configure static entry
- Save configuration: `write memory`
- Verify with `show ipv6 neighbors`

---

## Test Maintenance

### Adding New Test Cases

When adding new ND test cases:

1. **Follow Pattern:** Use existing tests as templates
2. **Error Handling:** Implement try/except blocks
3. **Cleanup:** Ensure cleanup runs even on failures
4. **Logging:** Add STEP banners and detailed logs
5. **Documentation:** Update this document and README

### Updating Test Cases

When modifying tests:

1. Update test documentation
2. Update expected results
3. Add notes for behavior changes
4. Update test matrix
5. Re-run full suite to verify

---

## References

### Manual Test Logs

The automated tests are based on the following manual test scenarios:

1. **Testcase 1:** Basic ND Resolution
2. **Testcase 2:** ND State Transitions - Aging
3. **Testcase 3:** ND Entry Re-learning
4. **Testcase 4:** Static ND Entry
5. **Testcase 5:** Interface Down Behavior
6. **Testcase 6:** Interface Flap Recovery
7. **Testcase 7:** ND on VLAN Interface
8. **Testcase 10:** Multiple VLANs with Independent ND

### Commands Reference

**Show Commands:**
```bash
show ipv6 neighbors
show ipv6 interfaces
show interface Vlan100
show vlan 100
```

**Configuration Commands:**
```bash
configure terminal
vlan 100
interface Vlan100
ipv6 address 2001:db8:100::1/64
ipv6 enable
no shutdown
ipv6 neighbor 2001:db8:100::2 52:54:00:ab:cd:ef
```

**Clear Commands:**
```bash
clear ipv6 neighbors
```

**Linux Commands:**
```bash
ip -6 neigh show
ip -6 neigh show dev Vlan100
redis-cli -n 0 HGETALL "NEIGH_TABLE:Vlan100:2001:db8:100::2"
```

---

## Test Execution Recommendations

### Recommended Order

Execute tests in this order for best coverage:

1. Basic ND Resolution (foundation)
2. ND on VLAN Interface (verify VLAN support)
3. ND Entry Re-learning (test clear functionality)
4. Static ND Entry (test static configuration)
5. ND State Transitions (monitor aging)
6. Interface Down Behavior (test failure handling)
7. Interface Flap Recovery (test recovery)
8. Multiple VLANs (comprehensive test)

### Resource Requirements

- **Time:** 15-20 minutes for full suite
- **Devices:** 2 SONiC devices (DUT1, DUT2)
- **Connectivity:** Direct Ethernet connection or switch between DUTs
- **Interfaces:** Minimum 3 free Ethernet ports per device

### Pre-test Verification

Before running tests:

1. Verify both devices are accessible
2. Check IPv6 is supported and enabled
3. Ensure test VLANs are not in use
4. Verify test interfaces are available
5. Check no conflicting configuration exists

---

**Document Version:** 1.0
**Last Updated:** 2026-03-31
**Author:** Network Automation Team
