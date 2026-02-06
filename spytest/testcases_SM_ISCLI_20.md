# SM_ISCLI_20: OSPF Configuration on Loopback Interface Without IP Address

**Author**: Athira
**Date**: 2026-02-06
**Feature**: OSPFv2 on Loopback Interfaces
**Category**: Routing / OSPF
**Priority**: High

---

## Feature Overview

This test suite validates OSPF configuration behavior on loopback interfaces, specifically addressing the bug where OSPF configuration on a loopback interface without an IP address fails silently. The configuration is accepted but does not take effect until an IP address is assigned to the loopback interface.

### Bug Description

**Issue**: When configuring OSPF (`ip ospf area X.X.X.X`) on a loopback interface that has no IP address configured, the CLI accepts the configuration without error, but OSPF does not actually activate on the interface. The interface does not appear in `show ip ospf interface` output.

**Example of Bug**:
```
sonic(config)# interface Loopback0
sonic(config-if-lo0)# no ip address
sonic(config-if-lo0)# ip ospf area 0.0.0.0
sonic(config-if-lo0)# end
sonic# show ip ospf interface
[Loopback0 does NOT appear - silent failure]

sonic(config)# interface Loopback0
sonic(config-if-lo0)# ip address 30.1.1.2/32
sonic(config-if-lo0)# end
sonic# show ip ospf interface
Loopback0 is up
  ifindex 112, MTU 65536 bytes, BW 0 Mbit <UP,LOWER_UP,BROADCAST,RUNNING,NOARP>
  This interface is UNNUMBERED, Area 0.0.0.0
  [Now Loopback0 appears]
```

**Expected Behavior**: The system should:
1. **Option A**: Reject OSPF configuration on loopback without IP address with clear error message
2. **Option B**: Accept configuration and automatically activate OSPF when IP is later assigned
3. **Option C**: Show warning that IP address is required for OSPF to activate

Currently, the CLI silently accepts the configuration but doesn't activate OSPF, causing confusion and potential misconfigurations.

---

## Test Environment

- **Topology**: Single DUT (D1) | Supported: HW and Virtual
- **CLI Type**: klish (IS-CLI)
- **Min SONiC Version**: Any version with OSPFv2 and IS-CLI support
- **Prerequisites**:
  - Device accessible via SSH
  - OSPF feature enabled
  - Ability to create loopback interfaces
  - Ability to configure and unconfigure IP addresses

---

## Test Case Coverage

### TC 20.1: OSPF on Loopback WITH IP Address (Positive Baseline)
**Objective**: Verify that OSPF configuration on loopback with IP address works correctly

**Test ID**: `SM_ISCLI_20_TC1`

**Steps**:
1. Configure OSPF router instance with area 0
2. Create loopback interface (Loopback0)
3. Assign IP address to loopback (e.g., 10.1.1.1/32)
4. Configure `ip ospf area 0.0.0.0` on loopback
5. Verify loopback appears in `show ip ospf interface`
6. Verify OSPF is active on the loopback

**Expected Result**:
- OSPF configuration succeeds
- Loopback0 appears in `show ip ospf interface` output
- Interface shows correct area (0.0.0.0)
- OSPF state is active

**Validation**:
- Parse `show ip ospf interface` output
- Verify Loopback0 is present
- Verify area matches configured value
- Verify interface state is "up"

---

### TC 20.2: OSPF on Loopback WITHOUT IP Address (Bug Scenario)
**Objective**: Verify behavior when OSPF is configured on loopback without IP address

**Test ID**: `SM_ISCLI_20_TC2`

**Steps**:
1. Configure OSPF router instance with area 0
2. Create loopback interface (Loopback0)
3. Ensure NO IP address is configured on loopback
4. Attempt to configure `ip ospf area 0.0.0.0` on loopback
5. Check if configuration was accepted or rejected
6. Verify loopback status in `show ip ospf interface`

**Expected Result** (After Bug Fix):
- **Option A**: CLI rejects configuration with error: "IP address required for OSPF on loopback"
- **Option B**: CLI accepts but shows warning, OSPF remains inactive until IP assigned
- **Option C**: Configuration is pending until IP address is configured

**Current Buggy Behavior**:
- CLI accepts configuration without error
- No warning or indication
- Loopback does NOT appear in `show ip ospf interface`
- Silent failure - admin thinks OSPF is configured but it's not active

**Validation**:
- Capture CLI output for error/warning messages
- Verify loopback is NOT in `show ip ospf interface` (bug validation)
- Document actual vs expected behavior

---

### TC 20.3: Add IP Address After OSPF Configuration (Recovery Scenario)
**Objective**: Verify OSPF activates when IP is added after OSPF config

**Test ID**: `SM_ISCLI_20_TC3`

**Steps**:
1. Configure OSPF router instance with area 0
2. Create loopback interface (Loopback0)
3. Configure `ip ospf area 0.0.0.0` on loopback (no IP yet)
4. Verify loopback NOT in `show ip ospf interface`
5. Add IP address to loopback (e.g., 10.2.2.2/32)
6. Verify loopback NOW appears in `show ip ospf interface`
7. Verify OSPF is active with correct configuration

**Expected Result**:
- OSPF activates automatically when IP is added
- Loopback0 appears in `show ip ospf interface` after IP assignment
- OSPF area configuration is preserved
- Interface shows correct area and state

**Validation**:
- Parse `show ip ospf interface` before and after IP assignment
- Verify loopback is absent before, present after
- Verify OSPF parameters (area, router ID, cost, etc.) are correct

---

### TC 20.4: Remove IP Address from Active OSPF Loopback
**Objective**: Verify OSPF deactivates when IP is removed from loopback

**Test ID**: `SM_ISCLI_20_TC4`

**Steps**:
1. Configure OSPF router instance with area 0
2. Create loopback with IP address (10.3.3.3/32)
3. Configure `ip ospf area 0.0.0.0` on loopback
4. Verify OSPF is active (loopback in `show ip ospf interface`)
5. Remove IP address from loopback (`no ip address`)
6. Verify loopback removed from `show ip ospf interface`
7. Verify OSPF configuration is still present (but inactive)

**Expected Result**:
- OSPF deactivates when IP is removed
- Loopback disappears from `show ip ospf interface` output
- OSPF configuration remains (can be seen in `show running-configuration`)
- No errors or warnings during removal

**Validation**:
- Parse `show ip ospf interface` before and after IP removal
- Verify loopback disappears from OSPF interface list
- Verify `show running-configuration interface Loopback0` still shows OSPF config

---

### TC 20.5: OSPF Loopback Full Lifecycle
**Objective**: Verify complete lifecycle of OSPF on loopback with IP changes

**Test ID**: `SM_ISCLI_20_TC5`

**Steps**:
1. Configure OSPF router instance with area 0
2. Create loopback with IP address A (10.4.4.4/32)
3. Configure `ip ospf area 0.0.0.0` on loopback
4. Verify OSPF is active
5. Remove IP address A
6. Verify OSPF deactivates
7. Add different IP address B (10.5.5.5/32)
8. Verify OSPF reactivates with new IP
9. Change OSPF area to 0.0.0.1
10. Verify area change takes effect

**Expected Result**:
- OSPF activates with first IP
- OSPF deactivates when IP removed
- OSPF reactivates with second IP
- Area changes are applied correctly
- No configuration corruption or state issues

**Validation**:
- Track OSPF state through all transitions
- Verify correct IP address in OSPF interface output
- Verify area changes are reflected
- Ensure no memory leaks or zombie configurations

---

### TC 20.6: Multiple Loopbacks with OSPF
**Objective**: Verify OSPF behavior across multiple loopback interfaces

**Test ID**: `SM_ISCLI_20_TC6`

**Steps**:
1. Configure OSPF router instance with area 0
2. Create Loopback0 with IP (10.10.0.1/32) and configure OSPF area 0.0.0.0
3. Create Loopback1 WITHOUT IP and configure OSPF area 0.0.0.0
4. Create Loopback2 with IP (10.10.0.2/32) and configure OSPF area 0.0.0.1
5. Verify `show ip ospf interface` shows only Loopback0 and Loopback2
6. Add IP to Loopback1 (10.10.0.3/32)
7. Verify all three loopbacks now appear in OSPF

**Expected Result**:
- Only loopbacks with IP addresses are active in OSPF
- Loopback1 without IP does not appear initially
- After adding IP to Loopback1, it appears in OSPF
- Different areas are handled correctly
- No interference between loopback configurations

**Validation**:
- Parse `show ip ospf interface` and count loopbacks
- Verify each loopback has correct area
- Verify only loopbacks with IP are active

---

### TC 20.7: OSPF Config Order Variations
**Objective**: Verify different configuration orders produce same result

**Test ID**: `SM_ISCLI_20_TC7`

**Steps**:
Test three configuration orders:

**Order 1** (IP first, then OSPF):
1. Create loopback and assign IP
2. Configure OSPF on loopback
3. Verify OSPF active

**Order 2** (OSPF first, then IP):
1. Create loopback without IP
2. Configure OSPF on loopback
3. Assign IP address
4. Verify OSPF active

**Order 3** (Simultaneous):
1. Create loopback
2. Assign IP and configure OSPF in same session
3. Verify OSPF active

**Expected Result**:
- All three orders should result in active OSPF on loopback
- No difference in final state regardless of order
- All configurations persist across config save/reload

**Validation**:
- Compare final OSPF state across all three methods
- Verify no differences in OSPF parameters
- Verify configuration persistence

---

### TC 20.8: OSPF on Loopback with Invalid Area
**Objective**: Verify error handling for invalid OSPF area values

**Test ID**: `SM_ISCLI_20_TC8`

**Steps**:
1. Create loopback with IP address (10.8.8.8/32)
2. Attempt invalid OSPF area configurations:
   - Invalid format: `ip ospf area 999.999.999.999`
   - Out of range: `ip ospf area 4294967296`
   - Invalid syntax: `ip ospf area invalid`
3. Verify appropriate error messages
4. Verify loopback NOT in `show ip ospf interface` after failed configs
5. Configure valid area (0.0.0.0)
6. Verify OSPF now active

**Expected Result**:
- Invalid area configurations are rejected with clear error
- Error messages indicate what's wrong
- Failed configs don't corrupt OSPF state
- Valid config works after failed attempts

**Validation**:
- Capture and verify error messages
- Ensure loopback doesn't appear in OSPF after invalid configs
- Verify successful config after failures

---

### TC 20.9: OSPF Priority and Cost on Loopback
**Objective**: Verify OSPF parameters can be configured on loopback

**Test ID**: `SM_ISCLI_20_TC9`

**Steps**:
1. Configure OSPF router instance
2. Create loopback with IP (10.9.9.9/32)
3. Configure OSPF area 0.0.0.0 on loopback
4. Configure OSPF priority on loopback
5. Configure OSPF cost on loopback
6. Verify parameters in `show ip ospf interface`
7. Remove IP address
8. Add IP address back
9. Verify OSPF parameters are preserved

**Expected Result**:
- OSPF priority and cost can be configured on loopback
- Parameters appear correctly in show commands
- Parameters persist through IP removal/addition cycle
- Configuration saved correctly

**Validation**:
- Parse `show ip ospf interface` for priority and cost
- Verify values match configured values
- Verify persistence across IP address changes

---

### TC 20.10: Cleanup and Unconfiguration
**Objective**: Verify clean removal of OSPF from loopback

**Test ID**: `SM_ISCLI_20_TC10`

**Steps**:
1. Configure multiple loopbacks with OSPF
2. Remove OSPF from loopback: `no ip ospf area`
3. Verify loopback removed from `show ip ospf interface`
4. Verify loopback interface still exists
5. Remove loopback interface entirely
6. Verify no OSPF residue or errors

**Expected Result**:
- `no ip ospf area` removes OSPF from loopback cleanly
- Loopback interface remains functional
- No OSPF errors in syslog
- Clean state for next test

**Validation**:
- Verify loopback absent from OSPF but interface still exists
- Check syslog for errors
- Verify configuration cleanup

---

## Test Data Requirements

### Loopback Configuration
```yaml
loopbacks:
  - name: Loopback0
    ip_addresses:
      - "10.1.1.1/32"
      - "10.2.2.2/32"
    ospf_area: "0.0.0.0"

  - name: Loopback1
    ip_addresses:
      - "10.10.0.3/32"
    ospf_area: "0.0.0.0"

  - name: Loopback2
    ip_addresses:
      - "10.10.0.2/32"
    ospf_area: "0.0.0.1"
```

### OSPF Configuration
```yaml
ospf:
  router_id: "1.1.1.1"
  areas:
    - "0.0.0.0"
    - "0.0.0.1"
  default_cost: 10
  default_priority: 1
```

### Test Patterns
```yaml
test_patterns:
  valid_areas:
    - "0.0.0.0"
    - "0.0.0.1"
    - "1.1.1.1"
    - "255.255.255.255"

  invalid_areas:
    - "999.999.999.999"
    - "4294967296"
    - "invalid"
    - "-1"

  valid_ips:
    - "10.1.1.1/32"
    - "192.168.1.1/32"
    - "172.16.0.1/32"
```

---

## Expected Test Results Summary

| Test Case | Scenario | Expected Behavior |
|-----------|----------|-------------------|
| TC 20.1 | OSPF on loopback WITH IP | OSPF activates, appears in show output |
| TC 20.2 | OSPF on loopback WITHOUT IP | Error/warning OR silent pending state |
| TC 20.3 | Add IP after OSPF config | OSPF activates automatically |
| TC 20.4 | Remove IP from active OSPF | OSPF deactivates, config preserved |
| TC 20.5 | Full lifecycle with IP changes | OSPF follows IP state correctly |
| TC 20.6 | Multiple loopbacks | Independent OSPF state per loopback |
| TC 20.7 | Configuration order variations | Same result regardless of order |
| TC 20.8 | Invalid OSPF area | Clear error message, no corruption |
| TC 20.9 | OSPF parameters on loopback | Priority/cost work correctly |
| TC 20.10 | Cleanup and removal | Clean unconfiguration |

---

## Bug Fix Validation

After fixing the bug, the following specific scenarios must pass:

### Critical Validation Points

1. **Bug Scenario Test**:
   ```
   Loopback without IP + OSPF config
   Expected: Error OR warning OR pending state (documented)
   Bug Behavior: Silent acceptance, no activation
   ```

2. **Recovery Test**:
   ```
   OSPF config → Add IP
   Expected: OSPF activates automatically
   Current: Works (good)
   ```

3. **Removal Test**:
   ```
   Active OSPF → Remove IP
   Expected: OSPF deactivates cleanly
   Must verify: No errors, config preserved
   ```

4. **Order Independence Test**:
   ```
   IP then OSPF === OSPF then IP
   Expected: Same final state
   Must verify: Both paths work identically
   ```

---

## Test Execution Strategy

### Test Order
1. Execute positive baseline test first (TC 20.1)
2. Execute bug scenario test (TC 20.2) to document current behavior
3. Execute recovery scenarios (TC 20.3-20.5)
4. Execute multi-loopback tests (TC 20.6)
5. Execute edge cases (TC 20.7-20.9)
6. Execute cleanup test last (TC 20.10)

### Automation Approach
- Use SPyTest framework with klish CLI type
- Parse `show ip ospf interface` output to verify interface presence
- Use OSPF APIs from `spytest/apis/routing/ospf.py`
- Validate OSPF state after each configuration change
- Track configuration through `show running-configuration`

### Pass/Fail Criteria
- **Pass**: OSPF state matches expected state for given configuration
- **Pass**: Appropriate errors/warnings for invalid configurations
- **Pass**: Clean activation/deactivation based on IP presence
- **Fail**: Silent failures (config accepted but not working)
- **Fail**: OSPF state corruption
- **Fail**: Inconsistent behavior across configuration orders

---

## Related Test Cases

- **SM_ISCLI_7**: Static routing tests (interface configuration patterns)
- **SM_ISCLI_12**: Show IP interface validation
- **OSPF basic tests**: Neighbor formation, area configuration
- **Interface tests**: Loopback creation and management

---

## Notes

1. **OSPF Implementation**: Verify whether using FRR or native SONiC OSPF
2. **Loopback Behavior**: Document if loopbacks are treated differently than physical interfaces
3. **Area Format**: Test both dotted-decimal (0.0.0.0) and integer (0) formats
4. **Router ID**: Verify OSPF router ID selection with loopback IPs
5. **Syslog Monitoring**: Check for OSPF syslog messages during state changes
6. **Performance**: Ensure no delays when activating OSPF on loopback after IP addition

---

## Test Script Location

**Path**: `spytest/tests/routing/ospf/test_sm_iscli_20_ospf_loopback_no_ip.py`
**YAML**: `spytest/vars/routing/ospf/vars_sm_iscli_20.yaml`

---

## Success Metrics

- **100% of positive tests** must show OSPF active with IP
- **100% of negative tests** must show appropriate error/warning
- **0 silent failures** (config accepted but not working)
- **0 state corruption** across all lifecycle tests
- **Consistent behavior** across all configuration orders
- **Clean cleanup** with no residue after unconfiguration

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-06 | Athira | Initial test case document created |

---
