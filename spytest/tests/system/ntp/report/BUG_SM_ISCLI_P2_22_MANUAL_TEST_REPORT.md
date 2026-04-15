# Bug SM_ISCLI_P2_22 - Manual Test Report
## Multiple NTP Source-Interface and Individual Deletion

**Date**: 2026-04-07
**Tester**: Claude Code (Automated Analysis)
**Device**: 192.168.100.147 (smic_sonic1)
**Testbed**: testbed_vs_1node_ntp.yaml
**CLI Mode**: SONiC IS-CLI (klish)

---

## BUG DETAILS

**Bug ID**: SM_ISCLI_P2_22
**Priority**: P2
**Status**: Requires Verification
**Description**: "It does not support multiple NTP source-interface, nor does it support deleting source-interface individually"

### Bug Claims (from bug report):
1. **Claim 1**: Device does NOT support configuring multiple NTP source-interfaces
2. **Claim 2**: Device does NOT support deleting source-interface individually by interface name
3. **Implied Expectation**: Only generic deletion (`no ntp source-interface`) should work

---

## TEST PLAN COVERAGE ANALYSIS

### Existing Test Cases in NTP_TestPlan.md:

| Test Case ID | Description | Coverage Status |
|--------------|-------------|-----------------|
| TC_NTP_SRC_005 | Delete NTP source-interface using `no ntp source-interface` | ✅ Covers generic deletion only |

**Coverage Conclusion**: **PARTIALLY COVERED** in test plan

**Missing Test Scenarios**:
- Multiple source-interface configuration behavior
- Individual deletion by interface name (e.g., `no ntp source-interface Ethernet 0`)

---

## AUTOMATION COVERAGE ANALYSIS

### Existing Automation in test_ntp_iscli.py:

| Test Function | Line Number | Coverage Status |
|---------------|-------------|-----------------|
| `test_ntp_035_delete_source_interface` | Lines 1161-1181 | ✅ Covers generic deletion only |

**Code Analysis**:
```python
def test_ntp_035_delete_source_interface(self) -> None:
    # Configures source interface
    ntp_api.config_ntp_source_interface(
        dut, interface=interface, config="yes", cli_type=cli_type
    )

    # Deletes using GENERIC deletion (empty interface parameter)
    result = ntp_api.config_ntp_source_interface(
        dut, interface="", config="no", cli_type=cli_type
    )
```

**Coverage Conclusion**: **PARTIALLY COVERED** in automation

**Missing Automation Scenarios**:
- Multiple source-interface configuration attempt
- Individual deletion by specifying interface name

---

## MANUAL TEST EXECUTION

### Test Environment:
- **Device IP**: 192.168.100.147
- **Access**: ssh admin@192.168.100.147 (password: root@123)
- **CLI**: sonic-cli (klish mode)
- **NTP Daemon**: chronyd (chrony.service)

### Pre-Test State:
```
NTP service: enabled
NTP source-interfaces: (to be configured during test)
```

---

## TEST PART A: Multiple Source-Interface Configuration

### Test Objective:
Verify if device supports configuring multiple NTP source-interfaces simultaneously.

**Bug Claim**: "It does not support multiple NTP source-interface"

---

### TEST STEP A1: Configure First Source-Interface (Ethernet 0)

**Commands**:
```
sonic# configure terminal
sonic(config)# ntp source-interface Ethernet 0
sonic(config)# exit
sonic# show ntp global
```

**Expected** (based on normal behavior): Source-interface configured as Ethernet0

**Observed**:
```
sonic# show ntp global
----------------------------------------------
NTP Global Configuration
----------------------------------------------
NTP service:            enabled
NTP source-interfaces:  Ethernet0
NTP vrf:                default
NTP authentication:     disabled
```

**Result**: ✅ **PASS** - First source-interface configured successfully

---

### TEST STEP A2: Configure Second Source-Interface (Management 0)

**Commands**:
```
sonic# configure terminal
sonic(config)# ntp source-interface Management 0
sonic(config)# exit
sonic# show ntp global
```

**Expected** (based on bug claim): Should either:
- **Option 1**: Replace Ethernet0 with Management0 (only one allowed)
- **Option 2**: Reject command with error message (multiple not supported)

**Observed**:
```
sonic# show ntp global
----------------------------------------------
NTP Global Configuration
----------------------------------------------
NTP service:            enabled
NTP source-interfaces:  Ethernet0, Management0
NTP vrf:                default
NTP authentication:     disabled
```

**Result**: ❌ **BUG CLAIM INCORRECT**

### TEST PART A FINDINGS:

**CRITICAL FINDING**: Device **DOES** support multiple NTP source-interfaces!

**Evidence**:
- `show ntp global` displays: `NTP source-interfaces: Ethernet0, Management0`
- Both interfaces are listed together
- No error message was displayed
- Both interfaces accepted by configuration system

**Contradiction with Bug Report**:
- Bug claims: "It does not support multiple NTP source-interface"
- Manual testing shows: Device accepts and displays multiple source-interfaces

**Status**: ✅ **FEATURE WORKS** - Multiple source-interfaces ARE supported

---

## TEST PART B: Individual Deletion by Interface Name

### Test Objective:
Verify if device supports deleting a specific source-interface by name.

**Bug Claim**: "does not support deleting source-interface individually"

---

### TEST STEP B1: Setup - Configure Ethernet 0

**Commands**:
```
sonic# configure terminal
sonic(config)# ntp source-interface Ethernet 0
sonic(config)# exit
```

**Pre-condition State**:
From previous test, we have both Ethernet0 and Management0 configured.

---

### TEST STEP B2: Attempt Individual Deletion by Name

**Commands**:
```
sonic# configure terminal
sonic(config)# no ntp source-interface Ethernet 0
sonic(config)# exit
```

**Expected** (based on bug claim): Should reject with error message like:
```
% Error: Invalid command
% Error: Use 'no ntp source-interface' without interface name
```

**Observed**:
```
sonic(config)# no ntp source-interface Ethernet 0
sonic(config)# exit
```
(Command executed without error)

**Result**: Command accepted without error ⚠️

---

### TEST STEP B3: Verify Individual Deletion Result

**Commands**:
```
sonic# show ntp global
```

**Expected** (if bug claim is correct): Both interfaces should still be present

**Observed**:
```
sonic# show ntp global
----------------------------------------------
NTP Global Configuration
----------------------------------------------
NTP service:            enabled
NTP source-interfaces:  Management0
NTP vrf:                default
NTP authentication:     disabled
```

**Result**: ❌ **BUG CLAIM INCORRECT**

### TEST PART B FINDINGS:

**CRITICAL FINDING**: Device **DOES** support individual deletion by interface name!

**Evidence**:
- Command `no ntp source-interface Ethernet 0` executed successfully
- Ethernet0 was REMOVED from configuration
- Management0 REMAINS in configuration
- `show ntp global` displays only: `NTP source-interfaces: Management0`

**Contradiction with Bug Report**:
- Bug claims: "does not support deleting source-interface individually"
- Manual testing shows: Individual deletion by name WORKS correctly
- Ethernet0 was specifically deleted while Management0 remained

**Status**: ✅ **FEATURE WORKS** - Individual deletion by name IS supported

---

## TEST PART C: Generic Deletion (Positive Test)

### Test Objective:
Verify generic deletion works correctly (this should work per bug report).

---

### TEST STEP C1: Generic Deletion Without Interface Name

**Commands**:
```
sonic# configure terminal
sonic(config)# no ntp source-interface
sonic(config)# exit
sonic# show ntp global
```

**Expected**: All source-interfaces should be removed

**Observed**:
```
sonic# show ntp global
----------------------------------------------
NTP Global Configuration
----------------------------------------------
NTP service:            enabled
NTP vrf:                default
NTP authentication:     disabled
```

**Result**: ✅ **PASS** - Generic deletion works as expected

### TEST PART C FINDINGS:

**Finding**: Generic deletion (`no ntp source-interface`) works correctly

**Evidence**:
- Source-interfaces field is empty (no interfaces shown)
- Management0 that was previously configured is now removed
- Command executed without error

**Status**: ✅ **WORKS AS EXPECTED** - Generic deletion functions properly

---

## BUG VERIFICATION SUMMARY

| Bug Claim | Manual Test Finding | Status |
|-----------|---------------------|--------|
| "Does not support multiple NTP source-interface" | Device accepts and displays multiple source-interfaces (Ethernet0, Management0) | ❌ **CLAIM INCORRECT** |
| "Does not support deleting source-interface individually" | Individual deletion by name works (`no ntp source-interface Ethernet 0` successfully removed only Ethernet0) | ❌ **CLAIM INCORRECT** |
| Generic deletion should work (implied) | Generic deletion works correctly | ✅ **CONFIRMED** |

**Overall Bug Status**: ❌ **BUG CLAIMS ARE INCORRECT**

---

## ROOT CAUSE ANALYSIS

### Why Bug Report May Be Incorrect:

**Possible Explanations**:

1. **Software Version Difference**:
   - Bug may have been reported on older SONiC version
   - Feature may have been added/fixed in current version
   - Current device (192.168.100.147) may be running newer code

2. **Misunderstanding of Feature Behavior**:
   - Reporter may have expected error but device silently accepts multiple interfaces
   - Reporter may not have tested individual deletion properly

3. **Documentation vs Implementation Gap**:
   - Documentation may state "single source-interface only"
   - Implementation actually supports multiple interfaces
   - Bug report based on documentation, not actual testing

4. **Test Environment Difference**:
   - Different platform/ASIC may behave differently
   - Virtual vs hardware platform differences

---

## EVIDENCE CHAIN

### Evidence 1: Multiple Source-Interface Support

**Command Sequence**:
```
sonic(config)# ntp source-interface Ethernet 0
sonic(config)# exit
sonic# show ntp global
  → Result: NTP source-interfaces: Ethernet0

sonic(config)# ntp source-interface Management 0
sonic(config)# exit
sonic# show ntp global
  → Result: NTP source-interfaces: Ethernet0, Management0
```

**Proof**: Device maintains BOTH interfaces in configuration

---

### Evidence 2: Individual Deletion by Name Support

**Command Sequence**:
```
Before: NTP source-interfaces: Ethernet0, Management0

sonic(config)# no ntp source-interface Ethernet 0
sonic(config)# exit
sonic# show ntp global
  → Result: NTP source-interfaces: Management0

(Ethernet0 removed, Management0 remains)
```

**Proof**: Specific interface deletion works correctly

---

### Evidence 3: Generic Deletion Works

**Command Sequence**:
```
Before: NTP source-interfaces: Management0

sonic(config)# no ntp source-interface
sonic(config)# exit
sonic# show ntp global
  → Result: NTP source-interfaces: (empty)
```

**Proof**: Generic deletion clears all source-interfaces

---

## COMPARISON WITH BUG REPORT

| Bug Report Statement | Manual Test Finding | Match? |
|---------------------|---------------------|--------|
| "It does not support multiple NTP source-interface" | Device accepts both Ethernet0 and Management0 simultaneously | ❌ **NO** - Feature works |
| "nor does it support deleting source-interface individually" | Individual deletion by name successfully removed only Ethernet0 | ❌ **NO** - Feature works |

**Conclusion**: Bug report claims are contradicted by actual device behavior

---

## REPRODUCTION STEPS (for Verification)

### To Reproduce Testing:

1. **Test Multiple Source-Interface**:
   ```
   sonic(config)# ntp source-interface Ethernet 0
   sonic(config)# exit
   sonic# show ntp global
   # Should show: Ethernet0

   sonic(config)# ntp source-interface Management 0
   sonic(config)# exit
   sonic# show ntp global
   # Should show: Ethernet0, Management0 (both interfaces)
   ```

2. **Test Individual Deletion**:
   ```
   sonic(config)# no ntp source-interface Ethernet 0
   sonic(config)# exit
   sonic# show ntp global
   # Should show: Management0 only (Ethernet0 removed)
   ```

3. **Test Generic Deletion**:
   ```
   sonic(config)# no ntp source-interface
   sonic(config)# exit
   sonic# show ntp global
   # Should show: (empty/no source-interfaces)
   ```

---

## EXPECTED vs ACTUAL BEHAVIOR

### Expected Behavior (per bug report):

**Multiple Source-Interface**:
```
sonic(config)# ntp source-interface Ethernet 0
sonic(config)# ntp source-interface Management 0
  → Should show error OR replace Ethernet0 with Management0
  → Should NOT show both interfaces
```

**Individual Deletion**:
```
sonic(config)# no ntp source-interface Ethernet 0
  → Should show error message
  → Should require generic deletion only
```

### Actual Behavior (from testing):

**Multiple Source-Interface**:
```
sonic(config)# ntp source-interface Ethernet 0
sonic(config)# ntp source-interface Management 0
  → Both interfaces accepted
  → show ntp global displays: "Ethernet0, Management0"
  → No error message
```

**Individual Deletion**:
```
sonic(config)# no ntp source-interface Ethernet 0
  → Command accepted without error
  → Specific interface removed
  → Other interfaces remain configured
```

---

## TEST COVERAGE UPDATE

### Test Plan Addition:

✅ **Added Test Case SM_ISCLI_P2_22** to NTP_TestPlan.md (lines 1454-1568)

**Test Case Structure**:
- **Part A**: Multiple source-interface configuration (negative test)
- **Part B**: Individual deletion by interface name (negative test)
- **Part C**: Generic deletion (positive test)

**Note**: Test case was designed to verify bug claims but testing showed claims are incorrect. Test case may need revision to reflect actual behavior.

---

## RECOMMENDATIONS

### Immediate Actions:

1. **Verify Bug Report Context**:
   - Check which SONiC version bug was reported against
   - Verify if bug was specific to certain platform/ASIC
   - Contact bug reporter for clarification

2. **Verify on Different Platforms**:
   - Test on hardware platform (current test was virtual testbed)
   - Test on different SONiC versions
   - Test on different ASIC types (Broadcom, Mellanox, etc.)

3. **Check SONiC Documentation**:
   - Review official SONiC NTP documentation
   - Check if documentation states "single source-interface only"
   - Verify if multiple source-interfaces is intentional feature

4. **Update Bug Status**:
   - If feature works on all platforms: **Close bug as invalid**
   - If feature works on some platforms only: **Update bug description**
   - If feature was fixed: **Update bug status to "Fixed, needs verification"**

### Bug Disposition Recommendations:

**Option 1: Close as Invalid** (if feature works everywhere)
- Reason: Manual testing shows both features work correctly
- Evidence: Multiple source-interfaces and individual deletion both functional
- Action: Mark bug as "Cannot Reproduce" or "Invalid"

**Option 2: Update Bug Description** (if version/platform specific)
- Reason: Bug may be valid for specific older versions/platforms
- Evidence: May work on newer versions but not older ones
- Action: Update bug to specify affected versions/platforms

**Option 3: Convert to Documentation Bug** (if docs are wrong)
- Reason: Documentation may incorrectly state limitations
- Evidence: Implementation supports features but docs say it doesn't
- Action: Create documentation update request

---

## RELATED TESTING

### Functional Verification Needed:

1. **Runtime Behavior**:
   - Verify NTP actually uses both source-interfaces when configured
   - Check chronyd configuration file to see if both interfaces written
   - Test NTP synchronization with multiple source-interfaces

2. **Edge Cases**:
   - Configure 3+ source-interfaces (find maximum limit)
   - Delete non-existent interface (error handling)
   - Configure same interface twice (idempotency)

3. **Integration Testing**:
   - Multiple source-interfaces with VRF configuration
   - Multiple source-interfaces with authentication
   - Source-interface deletion while NTP servers are actively syncing

---

## AUTOMATION RECOMMENDATIONS

### Suggested Automation Updates:

1. **Add Test Case for Multiple Source-Interface**:
   ```python
   def test_ntp_multiple_source_interface(self) -> None:
       """Verify multiple NTP source-interfaces can be configured."""
       # Configure Ethernet0
       ntp_api.config_ntp_source_interface(dut, "Ethernet0", config="yes")

       # Configure Management0
       ntp_api.config_ntp_source_interface(dut, "Management0", config="yes")

       # Verify both shown in output
       result = ntp_api.verify_ntp_source_interface(dut, ["Ethernet0", "Management0"])
       if not result:
           st.report_fail("msg", "Multiple source-interfaces not supported")
   ```

2. **Add Test Case for Individual Deletion**:
   ```python
   def test_ntp_individual_source_interface_deletion(self) -> None:
       """Verify individual NTP source-interface deletion by name."""
       # Configure multiple interfaces
       ntp_api.config_ntp_source_interface(dut, "Ethernet0", config="yes")
       ntp_api.config_ntp_source_interface(dut, "Management0", config="yes")

       # Delete specific interface
       ntp_api.config_ntp_source_interface(dut, "Ethernet0", config="no")

       # Verify only Management0 remains
       result = ntp_api.verify_ntp_source_interface(dut, ["Management0"])
       if not result:
           st.report_fail("msg", "Individual deletion failed")
   ```

3. **Update Existing Test**:
   - Enhance `test_ntp_035_delete_source_interface` to test both generic and individual deletion

---

## TEST EVIDENCE FILES

All test execution logs and evidence saved to:
- **Raw Test Log**: `/tmp/bug_sm_iscli_p2_22_test.log`
- **This Report**: `tests/system/ntp/report/BUG_SM_ISCLI_P2_22_MANUAL_TEST_REPORT.md`

---

## CONCLUSION

### Bug Verification Summary:

| Item | Status |
|------|--------|
| Bug SM_ISCLI_P2_22 Status | ❌ **BUG CLAIMS INCORRECT** |
| Multiple Source-Interface Support | ✅ **WORKS** - Device accepts multiple interfaces |
| Individual Deletion Support | ✅ **WORKS** - Device supports deletion by name |
| Generic Deletion Support | ✅ **WORKS** - Device supports generic deletion |
| Test Plan Coverage | ✅ **ADDED** - Test case SM_ISCLI_P2_22 added |
| Automation Coverage | ⚠️ **PARTIAL** - test_ntp_035 covers generic deletion only |

### Key Findings:

1. ❌ **Bug Report Incorrect**: Both claimed limitations do NOT exist
2. ✅ **Multiple Source-Interface Works**: Device accepts and maintains multiple source-interfaces (Ethernet0, Management0)
3. ✅ **Individual Deletion Works**: Command `no ntp source-interface Ethernet 0` successfully removes specific interface
4. ✅ **Generic Deletion Works**: Command `no ntp source-interface` removes all source-interfaces
5. ⚠️ **Version/Platform Dependent**: Bug may be valid for specific versions/platforms not tested
6. ✅ **Test Case Added**: SM_ISCLI_P2_22 added to test plan (may need revision based on findings)

### Unique Case:

This bug is different from previous bugs (SM_ISCLI_55, SM_ISCLI_P2_1):
- **SM_ISCLI_55**: Bug confirmed, root cause identified (Jinja2 error)
- **SM_ISCLI_P2_1**: Bug confirmed, interface naming inconsistency validated
- **SM_ISCLI_P2_22**: Bug claims contradicted by testing - features WORK correctly

### Recommended Actions:

1. **Verify Bug Context** - Check SONiC version and platform from original bug report
2. **Cross-Platform Testing** - Test on hardware platforms and different SONiC versions
3. **Update Bug Status** - Mark as "Cannot Reproduce" or "Invalid" if confirmed across platforms
4. **Revise Test Case** - Update SM_ISCLI_P2_22 test case to reflect actual feature behavior
5. **Add Automation** - Create automated tests for multiple source-interface and individual deletion

---

**Test Completion Date**: 2026-04-07
**Report Status**: COMPLETE
**Next Action**: Verify bug report context and update bug status based on cross-platform testing

