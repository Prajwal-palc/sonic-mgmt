# NTP Negative Test Cases - Correct Mapping

**Date**: 2026-04-10
**Issue**: Current test_ntp_comprehensive.py has WRONG test case IDs
**Action Required**: Fix test case IDs to match manual test reports

---

## Problem Statement

The current implementation in `test_ntp_comprehensive.py::TestNTPNegativeTests` has test case IDs that **DO NOT match** the manual test reports.

---

## Manual Test Reports (CORRECT specification)

From `tests/system/ntp/report/TC_NTP_NEG_*.md`:

| Test ID | Title | Objective |
|---------|-------|-----------|
| **NEG-001** | Enable NTP with No Server Configured | Verify system handles enabling NTP without servers gracefully |
| **NEG-002** | Remove Non-Existent NTP Server | Verify error message when deleting non-existent server |
| **NEG-003** | Configure Authentication Key with Invalid Key ID | Verify rejection of invalid key IDs (0, out of range) |
| **NEG-004** | Trust Key ID with No Authentication-Key Defined | Verify error when marking undefined key as trusted |
| **NEG-005** | Assign Server Key Binding to Undefined Key ID | Verify error when binding server to undefined key |
| **NEG-006** | Delete Auth Key While Referenced by Trusted-Key | Verify proper handling when deleting key in use |
| **NEG-007** | Configure Invalid VRF Name for NTP | Verify rejection of invalid VRF names |
| **NEG-008** | Configure Source Interface That Does Not Exist | Verify rejection of non-existent source interface |

---

## Current Implementation (WRONG IDs)

From `test_ntp_comprehensive.py::TestNTPNegativeTests`:

| Current Test Method | Current TC ID | Actual Behavior | Should Be |
|---------------------|---------------|-----------------|-----------|
| `test_ntp_reject_invalid_key_id_zero` | TC_NTP_NEG_001 | Tests key ID 0 rejection | NEG-003 (partial) |
| `test_ntp_reject_key_id_out_of_range` | TC_NTP_NEG_007 | Tests key ID > 65535 | NEG-003 (partial) |
| `test_ntp_reject_unsupported_auth_algorithm` | TC_NTP_NEG_008 | Tests invalid algorithm | Not in manual reports |
| `test_ntp_reject_duplicate_server` | NEG-002 | Tests duplicate server | Not in manual reports |
| `test_ntp_reject_empty_password` | NEG-003 | Tests empty password | Not in manual reports |
| `test_ntp_reject_invalid_server_address` | NEG-004 | Tests invalid server IP | Not in manual reports |
| `test_ntp_reject_nonexistent_source_interface` | NEG-005 | Tests nonexistent source interface | Matches NEG-008 ✓ |
| `test_ntp_cannot_delete_key_in_use` | NEG-006 | Tests deleting key in use | Matches NEG-006 ✓ |

---

## Correct Mapping Needed

### NEG-001: Enable NTP with No Server Configured ❌ NOT IMPLEMENTED

**Manual Report**: `TC_NTP_NEG_001.md`

**Objective**: Verify system gracefully handles enabling NTP without configured servers

**Test Steps**:
1. Remove all NTP servers
2. Enable NTP service (`ntp enable`)
3. Verify `show ntp associations` displays empty table with headers
4. Verify `show ntp global` shows service as enabled
5. Verify no crashes or errors

**Expected Result**: System displays empty associations table gracefully

**Current Implementation**: NONE - need to create `test_ntp_enable_without_servers()`

---

### NEG-002: Remove Non-Existent NTP Server ❌ NOT IMPLEMENTED

**Manual Report**: `TC_NTP_NEG_002.md`

**Objective**: Verify error handling when deleting non-existent server

**Test Steps**:
1. Verify current server list
2. Attempt: `no ntp server 10.99.99.99` (non-existent)
3. Check for error message

**Expected Result**: Error message like "% NTP server not found"

**Actual Behavior (from manual test)**: **BUG** - Command completes silently without error

**Current Implementation**: `test_ntp_reject_duplicate_server()` tests DIFFERENT scenario

**Need**: Create `test_ntp_remove_nonexistent_server()`

---

### NEG-003: Configure Authentication Key with Invalid Key ID ⚠️ PARTIAL

**Manual Report**: `TC_NTP_NEG_003.md`

**Objective**: Verify rejection of invalid authentication key IDs

**Test Steps**:
1. Test key ID 0: `ntp authentication-key 0 md5 Test` → Should be rejected
2. Test key ID > 65535: `ntp authentication-key 70000 md5 Test` → Should be rejected
3. Verify error messages

**Expected Result**: Both commands rejected with error

**Current Implementation**:
- `test_ntp_reject_invalid_key_id_zero()` ✓ (labeled as NEG-001 - WRONG)
- `test_ntp_reject_key_id_out_of_range()` ✓ (labeled as NEG-007 - WRONG)

**Action**: Combine into ONE test `test_ntp_invalid_authentication_key_id()` with correct ID NEG-003

---

### NEG-004: Trust Key ID with No Authentication-Key Defined ❌ NOT IMPLEMENTED

**Manual Report**: `TC_NTP_NEG_004.md`

**Objective**: Verify error when marking undefined key as trusted

**Test Steps**:
1. Attempt: `ntp trusted-key 999` (key 999 not defined)
2. Verify error message

**Expected Result**: Error like "%Error: Authentication key does not exist"

**Current Implementation**: `test_ntp_reject_invalid_server_address()` tests DIFFERENT scenario

**Need**: Create `test_ntp_trust_undefined_key()`

---

### NEG-005: Assign Server Key Binding to Undefined Key ID ❌ NOT IMPLEMENTED

**Manual Report**: `TC_NTP_NEG_005.md`

**Objective**: Verify error when binding server to undefined authentication key

**Test Steps**:
1. Attempt: `ntp server 192.168.100.10 key 777` (key 777 not defined)
2. Verify error message

**Expected Result**: Error like "%Error: Invalid authentication key configuration"

**Actual Behavior (from manual test)**: **BUG** - Even DEFINED keys are rejected!

**Current Implementation**: NONE matching

**Need**: Create `test_ntp_server_undefined_key_binding()`

---

### NEG-006: Delete Auth Key While Referenced by Trusted-Key ✓ IMPLEMENTED

**Manual Report**: `TC_NTP_NEG_006.md`

**Objective**: Verify proper handling when deleting authentication key in use

**Test Steps**:
1. Configure auth key
2. Mark as trusted
3. Bind to server
4. Attempt to delete key
5. Verify graceful handling

**Current Implementation**: `test_ntp_cannot_delete_key_in_use()` ✓ MATCHES!

**Action**: Just fix test case ID decorator to TC_NTP_NEG_006 (currently correct)

---

### NEG-007: Configure Invalid VRF Name for NTP ❌ NOT IMPLEMENTED

**Manual Report**: `TC_NTP_NEG_007.md`

**Objective**: Verify rejection of invalid VRF names

**Test Steps**:
1. Attempt: `ntp vrf invalid-vrf-name`
2. Verify error message

**Expected Result**: Error like "% VRF invalid-vrf-name does not exist"

**Current Implementation**: NONE matching

**Need**: Create `test_ntp_invalid_vrf_name()`

---

### NEG-008: Configure Source Interface That Does Not Exist ✓ IMPLEMENTED

**Manual Report**: `TC_NTP_NEG_008.md`

**Objective**: Verify rejection of non-existent source interface

**Test Steps**:
1. Attempt: `ntp source Ethernet999` (doesn't exist)
2. Verify error message

**Expected Result**: Error like "% Interface Ethernet999 not found"

**Current Implementation**: `test_ntp_reject_nonexistent_source_interface()` ✓ MATCHES!

**Action**: Fix test case ID decorator (currently labeled as NEG-005 - WRONG)

---

## Summary of Required Actions

### Tests to CREATE (5 new):
1. ✨ **NEG-001**: `test_ntp_enable_without_servers()` - Enable NTP with no servers
2. ✨ **NEG-002**: `test_ntp_remove_nonexistent_server()` - Delete non-existent server
3. ✨ **NEG-004**: `test_ntp_trust_undefined_key()` - Trust undefined key
4. ✨ **NEG-005**: `test_ntp_server_undefined_key_binding()` - Bind server to undefined key
5. ✨ **NEG-007**: `test_ntp_invalid_vrf_name()` - Configure invalid VRF

### Tests to FIX (3 existing):
1. ✏️ **NEG-003**: Combine `test_ntp_reject_invalid_key_id_zero` + `test_ntp_reject_key_id_out_of_range` → `test_ntp_invalid_authentication_key_id()`
2. ✏️ **NEG-006**: `test_ntp_cannot_delete_key_in_use()` - Already correct, just verify TC ID
3. ✏️ **NEG-008**: `test_ntp_reject_nonexistent_source_interface()` - Rename to `test_ntp_nonexistent_source_interface()` and fix TC ID

### Tests to REMOVE (5 obsolete):
1. ❌ `test_ntp_reject_unsupported_auth_algorithm` - Not in manual reports
2. ❌ `test_ntp_reject_duplicate_server` - Not in manual reports
3. ❌ `test_ntp_reject_empty_password` - Not in manual reports
4. ❌ `test_ntp_reject_invalid_server_address` - Not in manual reports
5. ❌ Individual key ID tests (will be combined into NEG-003)

---

## Recommendation

**Option 1**: Update existing `test_ntp_comprehensive.py::TestNTPNegativeTests` class
- Fix existing tests
- Add 5 new tests
- Remove obsolete tests

**Option 2**: Create NEW file `test_ntp_negative.py` with clean implementation
- All 8 NEG tests correctly implemented
- Based on manual test reports
- Keep old file for reference

**Recommended**: **Option 2** - Create clean new file with correct implementation

---

##Next Steps

1. Create `test_ntp_negative.py` with all 8 test cases correctly mapped
2. Implement based on manual test reports specifications
3. Use SpyTest coding guidelines
4. Include proper cleanup and teardown
5. Mark platform support (VS/HW) appropriately

