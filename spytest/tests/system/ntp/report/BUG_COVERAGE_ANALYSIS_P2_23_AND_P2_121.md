# NTP Bug Coverage Analysis Report
## SM_ISCLI_P2_23 and SM_ISCLI_P2_121

---

**Report Date**: 2026-04-07
**Prepared By**: Claude Code (Automated Analysis)
**Scope**: Automation coverage analysis for two NTP IS-CLI bugs

---

## Executive Summary

### SM_ISCLI_P2_23: VLAN Interface as NTP Source-Interface
**Status**: ✅ **ALREADY COVERED IN AUTOMATION**
**Test Case**: `test_ntp_036_source_interface_svi()` in `test_ntp_iscli.py` (lines 1184-1375)
**Test Plan Reference**: TC_NTP_SRC_004 (lines 1279-1303 in NTP_TestPlan.md)
**Coverage**: COMPLETE

### SM_ISCLI_P2_121: Show NTP Associations Refid Not Showing Upstream IP
**Status**: ❌ **NOT COVERED IN AUTOMATION**
**Test Case**: None (gap identified)
**Test Plan Reference**: Partial coverage in TC_NTP_SHOW_003-005, but refid field validation missing
**Coverage**: INCOMPLETE - Manual testing required

---

## Bug 1: SM_ISCLI_P2_23 - VLAN Interface as NTP Source-Interface

### Bug Description

**Bug ID**: SM_ISCLI_P2_23
**Jira Reference**: SSE-T8196
**Title**: Cannot configure VLAN interface as NTP source-interface
**Severity**: MEDIUM (Feature Limitation)
**Platform**: SMCI SONiC v1.2

**Issue**:
Ideally, users should be able to configure VLAN (SVI) interfaces as NTP source-interface for NTP packets. However, this configuration is rejected due to missing YANG support for VLAN-based NTP source selection.

**Expected Behavior**:
```bash
sonic(config)# interface vlan 100
sonic(config-if)# ip address 10.1.1.1/24
sonic(config-if)# exit
sonic(config)# ntp source-interface Vlan 100
# Should succeed
```

**Actual Behavior**:
```bash
sonic(config)# ntp source-interface Vlan 100
% Error: Invalid interface or interface type not supported
```

### Automation Coverage Analysis

#### ✅ Test Case Found: `test_ntp_036_source_interface_svi()`

**Location**: `/home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest/tests/system/ntp/test_ntp_iscli.py`
**Lines**: 1184-1375
**Test Type**: Negative test (validates limitation/expected failure)

**Test Implementation**:
```python
def test_ntp_036_source_interface_svi(self) -> None:
    """NTP-036: Attempt to configure VLAN SVI as NTP source-interface (negative test).

    Issue: Customer Report + SSE-T8196 - SVI cannot be configured as NTP source
    even after configuring an IP address on them.

    Steps:
      1. Create VLAN 10
      2. Configure IP address on Vlan 10
      3. Attempt to configure Vlan 10 as NTP source-interface
      4. Verify error is reported (expected behavior)
      5. Cleanup VLAN configuration

    Expected Result: VLAN source-interface configuration should be rejected
    Test Should: PASS when error is properly detected and reported
    """
    # Test validates VLAN SVI cannot be used as NTP source-interface
```

**Test Coverage**:
- ✅ VLAN creation and IP configuration
- ✅ Attempt to configure VLAN as NTP source-interface
- ✅ Error detection and validation
- ✅ Proper cleanup
- ✅ Klish CLI mode validation
- ✅ Negative test case (validates limitation is enforced)

**Test Plan Reference**: TC_NTP_SRC_004

**Lines 1279-1303 in NTP_TestPlan.md**:
```markdown
#### TC_NTP_SRC_004 — Set source interface to Vlan interface `[VS/HW]`

**Objective:** Verify NTP source-interface can be set to a Vlan interface.

**Pre-condition:** Vlan10 exists with IP 10.1.1.1/24

**Steps:**
DUT1(config)# ntp source-interface Vlan 10
DUT1(config)# end
DUT1# show ntp global

**Expected Output:**
NTP source-interface: Vlan10

**Note**: This test case EXPECTS VLAN source to work, but actual implementation rejects it.
The automation test (test_ntp_036) validates the ACTUAL behavior (rejection).
```

### Conclusion for SM_ISCLI_P2_23

**Automation Status**: ✅ **FULLY COVERED**

**Test Details**:
- Test Case ID: NTP-036
- Test Function: `test_ntp_036_source_interface_svi()`
- File: `test_ntp_iscli.py` (lines 1184-1375)
- Test Type: Negative test (validates expected limitation)
- Test Plan: TC_NTP_SRC_004 (documents expected vs actual behavior)

**No Action Required**: Test already exists and can be executed immediately to validate this limitation.

**Execution Command**:
```bash
./bin/spytest --testbed testbeds/testbed_vs_1node_ntp.yaml \
  tests/system/ntp/test_ntp_iscli.py::TestNTPISCLI::test_ntp_036_source_interface_svi \
  --logs-path ./logs/ntp_p2_23 \
  --log-level debug
```

---

## Bug 2: SM_ISCLI_P2_121 - Show NTP Associations Refid Field

### Bug Description

**Bug ID**: SM_ISCLI_P2_121
**Title**: "show ntp associations" refid not showing upstream NTP source IP
**Severity**: MEDIUM (CLI Display Inconsistency)
**Platform**: SMCI IS-CLI

**Issue**:
The `show ntp associations` command in SMCI IS-CLI does not display the upstream NTP source IP address in the refid field, unlike Broadcom IS-CLI and Click-CLI implementations.

**Comparison**:

**Broadcom IS-CLI** (Expected Behavior):
```
remote                       refid            st   t  when   poll   reach  delay  offset       jitter
======================================================================================================
*216.239.35.12               129.6.15.28      1   u    28     64    377   20.123  -1.132       0.234
```
↑ refid shows upstream NTP source IP: 129.6.15.28

**SMCI IS-CLI** (Bug - Current Behavior):
```
remote                       refid            st   t  when   poll   reach  delay  offset       jitter
======================================================================================================
*216.239.35.12               .INIT.           1   u    28     64    377   20.123  -1.132       0.234
```
↑ refid shows `.INIT.` or empty instead of upstream source IP

**Click-CLI** (Reference - Working):
```
MS Name/IP address         Stratum Poll Reach LastRx Last sample
===============================================================================
^* 216.239.35.12                 1   6    77    28  -1132us[-1549us] +/-   20ms
   (refid: 129.6.15.28)
```
↑ Click mode correctly shows refid information

### Automation Coverage Analysis

#### ❌ Test Case NOT Found

**Grep Search Results**:
- Searched `test_ntp_iscli.py` for: "P2_121", "refid", "upstream NTP source"
- **No matches found**
- Test case does NOT exist in automation script

**Test Plan Coverage**:

Lines 1725-1799 in `NTP_TestPlan.md` cover "show ntp associations" but with gaps:

**TC_NTP_SHOW_003** (lines 1725-1749):
```markdown
**Objective:** Verify association table shows `*` prefix, stratum, reach=377,
and valid delay/offset/jitter when fully synchronised.

**Expected Output:**
NTP Associations:
  refid           st t when poll reach  delay  offset  jitter
  =================================================================
 *192.168.100.10  2  u  128 1024  377  10.234 -0.233  1.243

**Verification:**
- `*` prefix present on selected server
- `reach = 377` (octal — all 8 polls received)
- `st` (stratum) is a number 1–15
- `delay`, `offset`, `jitter` are numeric values
```

**Gap Identified**: Test plan validates presence of refid COLUMN but does NOT validate refid CONTENT (upstream IP address).

**SM_ISCLI_55** (lines 1801-1865):
```markdown
**Objective:** Verify that `show ntp associations` displays configured NTP servers
with all fields even before synchronization occurs.

**Expected Output:**
remote                       refid            st   t  when   poll   reach  delay  offset       jitter
======================================================================================================
~192.168.100.10              .INIT.            0   -     -     64     0   0.000   0.000       0.000
```

**Coverage**: Validates refid shows `.INIT.` BEFORE sync (correct), but does NOT validate refid shows UPSTREAM IP AFTER sync.

### Manual Testing Required

Since automation coverage is incomplete, manual testing has been initiated.

**Manual Test Script**: `/tmp/bug_sm_iscli_p2_121_test.sh`
**Test Log**: `/tmp/bug_sm_iscli_p2_121_test.log`
**Report**: Will be saved to `/tests/system/ntp/report/BUG_SM_ISCLI_P2_121_MANUAL_TEST_REPORT.md`

**Test Strategy**:
1. Configure NTP server (216.239.35.12 - time4.google.com)
2. Enable NTP and wait for synchronization
3. Check `show ntp associations` refid field (klish mode) - CRITICAL TEST
4. Compare with click mode `show ntp` output
5. Verify chronyd sources directly (`chronyc sources -v`)
6. Document discrepancies between klish/click/chronyd

**Test Duration**: ~90 seconds (includes 60 seconds wait for synchronization)

### Conclusion for SM_ISCLI_P2_121

**Automation Status**: ❌ **NOT COVERED**

**Gaps Identified**:
1. No test case validates refid field content after synchronization
2. Test plan covers refid column presence but not content validation
3. No comparison between klish/click CLI refid display
4. Missing validation of upstream NTP source IP in refid field

**Actions Required**:
1. ✅ Manual testing in progress (test script created and executing)
2. ⏳ Analyze manual test results
3. ⏳ Create comprehensive test report
4. ⏳ Add test case to NTP_TestPlan.md if bug is confirmed
5. ⏳ Consider adding automation test case to test_ntp_iscli.py

**Proposed Test Case ID**: TC_NTP_SHOW_006 or SM_ISCLI_P2_121

**Proposed Test Case**:
```markdown
#### TC_NTP_SHOW_006 — Verify refid shows upstream NTP source IP `[VS/HW]`

**Objective:** Verify `show ntp associations` refid field displays the upstream
NTP source IP address after synchronization (not .INIT. or empty).

**Pre-condition:** NTP synchronised with public NTP server (216.239.35.12)

**Steps:**
DUT1(config)# ntp server 216.239.35.12
DUT1(config)# ntp enable
DUT1(config)# end
# Wait 60 seconds for synchronization
DUT1# show ntp associations

**Expected Output:**
remote                       refid            st   t  when   poll   reach  delay  offset       jitter
======================================================================================================
*216.239.35.12               <upstream_ip>    1   u    28     64    377   20.123  -1.132       0.234
                             ↑ Should show IP address, not .INIT.

**Verification:**
- refid field contains valid IP address (e.g., 129.6.15.28)
- refid is NOT empty
- refid is NOT ".INIT." for synchronized server
- Compare with click mode: `show ntp` should show same refid

**Comparison Test:**
DUT1# exit
admin@sonic:~$ show ntp
# Verify refid matches between klish and click modes
```

---

## Summary Table

| Bug ID | Bug Title | Automation Status | Test Case | Location | Test Plan | Action Required |
|--------|-----------|-------------------|-----------|----------|-----------|-----------------|
| **SM_ISCLI_P2_23** | VLAN as NTP source-interface | ✅ **COVERED** | `test_ntp_036_source_interface_svi()` | test_ntp_iscli.py:1184-1375 | TC_NTP_SRC_004 | None - Execute existing test |
| **SM_ISCLI_P2_121** | refid not showing upstream IP | ❌ **NOT COVERED** | None (gap) | N/A | Partial (TC_NTP_SHOW_003-005) | Manual test + Add to automation |

---

## Recommendations

### For SM_ISCLI_P2_23
**No action required** - Test coverage is complete.

Execute existing test to validate current behavior:
```bash
./bin/spytest --testbed testbeds/testbed_vs_1node_ntp.yaml \
  tests/system/ntp/test_ntp_iscli.py::TestNTPISCLI::test_ntp_036_source_interface_svi \
  --logs-path ./logs/ntp_svi_test
```

### For SM_ISCLI_P2_121
**Actions Required**:

1. **Complete Manual Testing** (In Progress)
   - Manual test script executing: `/tmp/bug_sm_iscli_p2_121_test.sh`
   - Review test results in: `/tmp/bug_sm_iscli_p2_121_test.log`
   - Create comprehensive report

2. **Update Test Plan**
   - Add TC_NTP_SHOW_006 or SM_ISCLI_P2_121 section
   - Document expected refid behavior after synchronization
   - Include klish vs click CLI comparison

3. **Consider Automation**
   - If bug is confirmed, add test case to `test_ntp_iscli.py`
   - Implement refid field content validation
   - Add comparison between klish and click CLI outputs

4. **Test Data Configuration**
   - Add P2_121 section to `vars_ntp_iscli_bugs.yaml` if automating
   - Include test servers and expected refid values

---

## Test Artifacts

### SM_ISCLI_P2_23
- **Automation Test**: `test_ntp_iscli.py` (existing)
- **Test Plan**: NTP_TestPlan.md, TC_NTP_SRC_004
- **No additional artifacts required**

### SM_ISCLI_P2_121
- **Manual Test Script**: `/tmp/bug_sm_iscli_p2_121_test.sh`
- **Test Log**: `/tmp/bug_sm_iscli_p2_121_test.log`
- **Manual Test Report**: `/tests/system/ntp/report/BUG_SM_ISCLI_P2_121_MANUAL_TEST_REPORT.md` (pending)
- **Coverage Analysis**: This document

---

## Related Bugs and Test Cases

### SM_ISCLI_P2_23 Related
- **SM_ISCLI_P2_1**: NTP source-interface naming issues (Management interface)
- **TC_NTP_SRC_001-003**: Source-interface tests for Ethernet/Loopback

### SM_ISCLI_P2_121 Related
- **SM_ISCLI_55**: Show ntp associations empty table (fixed)
- **TC_NTP_SHOW_003-005**: Associations display tests (partial coverage)
- **SM_ISCLI_P2_28**: chronyd configuration generation (related to backend NTP data)

---

**Report Status**: PRELIMINARY (awaiting P2_121 manual test results)
**Last Updated**: 2026-04-07
**Next Review**: After manual test completion for SM_ISCLI_P2_121

---
