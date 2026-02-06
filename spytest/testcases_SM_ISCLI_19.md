# SM_ISCLI_19: Grep Filter Effectiveness in Command Combinations

**Author**: Athira
**Date**: 2026-02-06
**Feature**: IS-CLI Command Pipeline (Grep Filtering)
**Category**: System / CLI
**Priority**: High

---

## Feature Overview

This test suite validates the effectiveness of the `grep` filter when used in command combinations with various `show` commands in IS-CLI (Klish). The bug scenario shows that grep filters are not properly filtering output, instead returning all results regardless of the search pattern.

### Bug Description

**Issue**: When using `grep` in command pipelines (e.g., `show ip interfaces | grep <pattern>`), the grep filter does not effectively filter the output. Instead of showing only matching lines, it displays all output lines.

**Example of Bug**:
```
DVT3# show ip interfaces | grep asdf
Interface                      IP Address/Mask          Status
Ethernet0                      192.168.1.1/24           primary
Ethernet112                    192.168.2.1/24           primary
Loopback0                      10.1.1.1/32              primary
DVT3#
```

**Expected Behavior**: The command should return **no output** (or only lines containing "asdf") since "asdf" does not appear in any interface information.

---

## Test Environment

- **Topology**: Single DUT (D1) | Supported: HW and Virtual
- **CLI Type**: klish (IS-CLI)
- **Min SONiC Version**: Any version with IS-CLI support
- **Prerequisites**:
  - Device accessible via SSH
  - Multiple interfaces configured (at least 3-4)
  - IP addresses configured on interfaces
  - Various interface types available (Ethernet, Loopback, Vlan)

---

## Test Case Coverage

### TC 19.1: Grep with Non-Existent Pattern (Negative Match)
**Objective**: Verify that grep returns no output when pattern does not exist

**Test ID**: `SM_ISCLI_19_TC1`

**Steps**:
1. Execute `show ip interfaces | grep asdf`
2. Execute `show ip interfaces | grep xyz123`
3. Execute `show interfaces status | grep nonexistent`
4. Execute `show running-config | grep invalidkeyword`

**Expected Result**:
- All commands should return **empty output** or proper "no match found" indication
- No interface/configuration lines should be displayed
- Command should complete successfully without errors

**Validation**:
- Output line count should be 0 (excluding headers/prompts)
- Verify no false positives are returned

---

### TC 19.2: Grep with Exact Interface Name Match (Positive Match)
**Objective**: Verify grep correctly filters output for exact interface names

**Test ID**: `SM_ISCLI_19_TC2`

**Steps**:
1. Get list of configured interfaces using `show interfaces status`
2. Execute `show ip interfaces | grep Ethernet0`
3. Execute `show interfaces status | grep Loopback0`
4. Execute `show interfaces status | grep Vlan10`

**Expected Result**:
- Only lines containing the exact search pattern should be returned
- For `grep Ethernet0`: Only Ethernet0 interface should appear (not Ethernet0, Ethernet10, Ethernet100)
- Output should contain only matching interfaces
- No partial matches unless they contain the exact string

**Validation**:
- Count output lines and verify only matching entries
- Verify no entries without the search pattern
- Confirm partial matches are included if they contain the pattern (e.g., "Ethernet0" matches "Ethernet0" but also "Ethernet0:" in descriptions)

---

### TC 19.3: Grep with IP Address Pattern (Positive Match)
**Objective**: Verify grep filters IP addresses correctly

**Test ID**: `SM_ISCLI_19_TC3`

**Steps**:
1. Configure IP addresses on interfaces (e.g., 192.168.1.1/24, 10.0.0.1/30)
2. Execute `show ip interfaces | grep 192.168.1`
3. Execute `show ip interfaces | grep 10.0.0`
4. Execute `show ip interfaces | grep /24`
5. Execute `show ip interfaces | grep /30`

**Expected Result**:
- Only interfaces with matching IP address patterns should be displayed
- For `grep 192.168.1`: Only interfaces with IPs starting with 192.168.1.x
- For `grep /24`: Only interfaces with /24 subnet mask
- Grep should handle IP address octets and CIDR notation correctly

**Validation**:
- Verify each returned line contains the search pattern
- Count results match expected interface count with that pattern
- No interfaces without the pattern should appear

---

### TC 19.4: Grep with Status/State Keywords (Positive Match)
**Objective**: Verify grep filters interface states correctly

**Test ID**: `SM_ISCLI_19_TC4`

**Steps**:
1. Ensure interfaces have different states (up, down, admin-down)
2. Execute `show interfaces status | grep up`
3. Execute `show interfaces status | grep down`
4. Execute `show interfaces status | grep admin`
5. Execute `show ip interfaces | grep primary`

**Expected Result**:
- Only interfaces matching the state keyword should appear
- For `grep up`: Interfaces in "up" state (may include "up" and "admin-up")
- For `grep down`: Interfaces in "down" state
- For `grep primary`: Only primary IP addresses

**Validation**:
- Verify status field matches the grep pattern
- Confirm no interfaces with non-matching status appear
- Handle case sensitivity appropriately

---

### TC 19.5: Grep with Case Sensitivity
**Objective**: Verify grep respects case sensitivity (or behaves consistently)

**Test ID**: `SM_ISCLI_19_TC5`

**Steps**:
1. Execute `show ip interfaces | grep ethernet0` (lowercase)
2. Execute `show ip interfaces | grep Ethernet0` (proper case)
3. Execute `show ip interfaces | grep ETHERNET0` (uppercase)
4. Execute `show interfaces status | grep UP` vs `grep up`

**Expected Result**:
- Grep should be case-sensitive by default (or document if case-insensitive)
- Lowercase "ethernet0" should not match "Ethernet0" if case-sensitive
- Consistent behavior across all commands

**Validation**:
- Compare output of case variations
- Document actual grep behavior (case-sensitive or case-insensitive)
- Verify consistency with Linux grep behavior

---

### TC 19.6: Grep with Special Characters and Regex
**Objective**: Verify grep handles special characters appropriately

**Test ID**: `SM_ISCLI_19_TC6`

**Steps**:
1. Execute `show ip interfaces | grep "192.168."`
2. Execute `show ip interfaces | grep "\.1"`
3. Execute `show running-config | grep "interface Ethernet*"`
4. Execute `show interfaces status | grep "^Ethernet"`
5. Execute `show ip interfaces | grep "primary$"`

**Expected Result**:
- Basic regex patterns should work (if supported)
- Special characters should be handled correctly
- If regex not supported, literal string matching should work
- Anchor patterns (^ and $) should filter appropriately

**Validation**:
- Verify pattern matching behavior
- Document which regex features are supported
- Ensure special characters don't break grep functionality

---

### TC 19.7: Grep with Multiple Commands (Comprehensive)
**Objective**: Verify grep works correctly with various show commands

**Test ID**: `SM_ISCLI_19_TC7`

**Steps**:
1. Execute `show interfaces status | grep Ethernet`
2. Execute `show interfaces description | grep "test"`
3. Execute `show ip route | grep via`
4. Execute `show vlan brief | grep 100`
5. Execute `show mac address-table | grep dynamic`
6. Execute `show arp | grep REACHABLE`

**Expected Result**:
- Grep should work consistently across all show commands
- Each grep should filter output appropriately
- No command should return unfiltered results when pattern doesn't exist

**Validation**:
- Test minimum 5 different show commands with grep
- Verify filtering effectiveness for each command
- Ensure consistent grep behavior across command types

---

### TC 19.8: Grep with Empty Pattern
**Objective**: Verify grep behavior with empty or invalid patterns

**Test ID**: `SM_ISCLI_19_TC8`

**Steps**:
1. Execute `show ip interfaces | grep ""`
2. Execute `show ip interfaces | grep " "` (single space)
3. Execute `show interfaces status | grep`

**Expected Result**:
- Empty pattern should either:
  - Return all output (since everything matches empty string), OR
  - Return error message about invalid pattern
- Behavior should be consistent and documented
- Single space grep should only match lines with spaces

**Validation**:
- Document actual behavior with empty patterns
- Verify no crash or unexpected output
- Ensure error handling is appropriate

---

### TC 19.9: Grep with Long Output (Performance)
**Objective**: Verify grep efficiently filters large output sets

**Test ID**: `SM_ISCLI_19_TC9`

**Steps**:
1. Execute `show running-config | grep interface` (large output)
2. Execute `show mac address-table | grep dynamic` (potentially large output)
3. Execute `show ip route | grep 0.0.0.0` (large routing table)
4. Measure execution time

**Expected Result**:
- Grep should filter large outputs efficiently
- Response time should be reasonable (<5 seconds for typical datasets)
- Memory usage should be acceptable
- No truncation of filtered results

**Validation**:
- Verify all matching entries are returned
- Compare execution time with and without grep
- Ensure no performance degradation or crashes

---

### TC 19.10: Grep Chain (Multiple Greps)
**Objective**: Verify multiple grep filters can be chained

**Test ID**: `SM_ISCLI_19_TC10`

**Steps**:
1. Execute `show interfaces status | grep up | grep Ethernet`
2. Execute `show ip interfaces | grep 192 | grep /24`
3. Execute `show running-config | grep interface | grep Ethernet`

**Expected Result**:
- Chained greps should work as progressive filters
- Each grep should filter output of previous command
- Final output should match all grep criteria

**Validation**:
- Verify output contains only entries matching all grep patterns
- Compare with single grep using combined pattern
- Ensure no false positives from any grep in chain

---

## Test Data Requirements

### Interface Configuration
```yaml
interfaces:
  - name: Ethernet0
    ip: 192.168.1.1/24
    status: up
    description: "Test interface 1"

  - name: Ethernet4
    ip: 192.168.2.1/24
    status: up
    description: "Test interface 2"

  - name: Ethernet8
    ip: 10.0.0.1/30
    status: down
    description: "Test interface 3"

  - name: Loopback0
    ip: 10.1.1.1/32
    status: up
    description: "Loopback interface"

  - name: Vlan10
    ip: 172.16.10.1/24
    status: up
    description: "VLAN interface"
```

### Test Patterns
```yaml
test_patterns:
  non_existent:
    - "asdf"
    - "xyz123"
    - "nonexistent"
    - "invalidkeyword"

  valid_patterns:
    - "Ethernet0"
    - "192.168.1"
    - "/24"
    - "up"
    - "primary"
    - "Loopback"

  special_characters:
    - "192.168."
    - "\.1"
    - "^Ethernet"
    - "primary$"
```

---

## Expected Test Results Summary

| Test Case | Pattern Type | Expected Behavior |
|-----------|-------------|-------------------|
| TC 19.1 | Non-existent | Empty output, no lines displayed |
| TC 19.2 | Exact interface | Only matching interface(s) |
| TC 19.3 | IP pattern | Only IPs matching pattern |
| TC 19.4 | Status/State | Only matching status entries |
| TC 19.5 | Case variations | Case-sensitive filtering |
| TC 19.6 | Special chars | Proper regex/literal handling |
| TC 19.7 | Multiple commands | Consistent filtering across commands |
| TC 19.8 | Empty pattern | Documented behavior (all or error) |
| TC 19.9 | Large output | Efficient filtering, no truncation |
| TC 19.10 | Chained grep | Progressive filtering |

---

## Bug Fix Validation

After fixing the grep bug, the following specific scenarios must pass:

### Critical Validation Points

1. **Bug Scenario Test**:
   ```
   Command: show ip interfaces | grep asdf
   Expected: NO OUTPUT (empty result)
   Bug Behavior: Shows all interfaces
   ```

2. **Positive Match Test**:
   ```
   Command: show ip interfaces | grep Ethernet0
   Expected: Only Ethernet0 interface
   Bug Risk: Shows all interfaces or wrong interface
   ```

3. **Pattern Absence Test**:
   ```
   Command: show interfaces status | grep xyz123
   Expected: NO OUTPUT
   Bug Behavior: Shows all interfaces
   ```

4. **Partial Match Test**:
   ```
   Command: show ip interfaces | grep 192.168
   Expected: Only interfaces with IPs containing "192.168"
   Bug Risk: Shows all interfaces or none
   ```

---

## Test Execution Strategy

### Test Order
1. Execute negative tests first (TC 19.1) to confirm bug fix
2. Execute positive matching tests (TC 19.2-19.4)
3. Execute edge case tests (TC 19.5-19.6)
4. Execute comprehensive tests (TC 19.7-19.10)

### Automation Approach
- Use SPyTest framework with klish CLI type
- Parse command output to count lines
- Compare expected vs actual line counts
- Validate each line contains the search pattern
- Use regex to verify pattern matching

### Pass/Fail Criteria
- **Pass**: Grep returns only lines containing the search pattern
- **Pass**: Non-existent patterns return empty output
- **Fail**: Any line without the pattern appears in grep output
- **Fail**: Grep returns all output regardless of pattern

---

## Related Test Cases

- **SM_ISCLI_12**: Show IP Interface output validation
- **SM_ISCLI_33**: Show running-config interface
- **Interface validation tests**: General interface show commands

---

## Notes

1. **Grep Implementation**: Verify whether IS-CLI uses Linux grep or custom implementation
2. **Regex Support**: Document which regex features are supported (^, $, *, ., [], etc.)
3. **Case Sensitivity**: Confirm default behavior (case-sensitive vs case-insensitive)
4. **Performance**: Monitor grep performance with large datasets (1000+ entries)
5. **Error Handling**: Verify appropriate error messages for invalid grep patterns
6. **Pipe Support**: Confirm other pipe commands work correctly (e.g., `| include`, `| exclude`)

---

## Test Script Location

**Path**: `spytest/tests/system/cli/test_sm_iscli_19_grep_filter.py`
**YAML**: `spytest/vars/system/cli/vars_sm_iscli_19.yaml`

---

## Success Metrics

- **100% of negative tests** must return empty output
- **100% of positive tests** must return only matching lines
- **0 false positives** (lines without pattern in grep output)
- **0 false negatives** (matching lines not appearing in grep output)
- **Consistent behavior** across all show commands

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-06 | Athira | Initial test case document created |

---
