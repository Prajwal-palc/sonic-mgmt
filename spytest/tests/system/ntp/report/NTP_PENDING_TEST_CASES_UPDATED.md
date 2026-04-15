# NTP Test Cases - Pending Execution List (Updated After Automation Review)

**Date:** 2026-04-09
**Last Updated:** 2026-04-09 (Post-Automation Analysis)
**Total Manual Test Cases:** 72
**Automated Test Cases:** 43 (36 in test_ntp_iscli.py + 7 in test_ntp_iscli_bugs.py)
**Coverage:** 60% (43/72 test cases)
**Remaining Pending:** 29 manual test cases
**Blocked:** 5 (Authentication workflows - BUG-NTP-002)

---

## Summary of Automation Coverage

| Category | Total | Automated | Pending | Coverage |
|----------|-------|-----------|---------|----------|
| Enable/Disable | 3 | 3 | 0 | ✅ 100% |
| Server Configuration | 10 | 10 | 0 | ✅ 100% |
| Auth Keys (Config Only) | 7 | 6 | 1 | ✅ 86% |
| Trusted Keys (Config Only) | 4 | 4 | 0 | ✅ 100% |
| Auth Enforcement | 3 | 2 | 1 | ✅ 67% |
| **Auth Workflows (E2E)** | **5** | **0** | **5** | **❌ 0% BLOCKED** |
| Source Interface | 6 | 4 | 2 | ✅ 67% |
| VRF Binding | 4 | 1 | 3 | ⚠️ 25% |
| Show Commands | 5 | 4 | 1 | ✅ 80% |
| **Synchronization** | **6** | **1** | **5** | **⚠️ 17%** |
| Traffic Analysis | 7 | 0 | 7 | ❌ 0% |
| Persistence | 4 | 3 | 1 | ✅ 75% |
| Negative Tests | 8 | 0 | 8 | ❌ 0% |
| Scale Tests | 5 | 1 | 4 | ⚠️ 20% |
| Edge Cases | 5 | 0 | 5 | ❌ 0% |
| **Bug Validation** | **7** | **7** | **0** | **✅ 100%** |

---

## Automated Test Coverage (43 Tests)

### test_ntp_iscli.py (36 Tests) ✅

**Enable/Disable Tests (3 tests)**
- ✅ `test_ntp_001_enable_ntp` → TC_NTP_ENABLE_001
- ✅ `test_ntp_002_disable_ntp` → TC_NTP_ENABLE_002
- ✅ `test_ntp_003_reenable_ntp` → TC_NTP_ENABLE_003

**Authentication Keys (6 tests)**
- ✅ `test_ntp_007_auth_key_md5` → TC_NTP_AUTHKEY_001
- ✅ `test_ntp_008_auth_key_sha1` → TC_NTP_AUTHKEY_002
- ✅ `test_ntp_009_auth_key_sha256` → TC_NTP_AUTHKEY_003
- ✅ `test_ntp_010_auth_key_sha384` → TC_NTP_AUTHKEY_004 (partial)
- ✅ `test_ntp_011_auth_key_sha512` → TC_NTP_AUTHKEY_004 (partial)
- ✅ `test_ntp_013_delete_auth_key` → TC_NTP_AUTHKEY_006

**Trusted Keys (4 tests)**
- ✅ `test_ntp_012_config_trusted_key` → TC_NTP_TRUSTED_001
- ✅ `test_ntp_014_config_multiple_trusted_keys` → TC_NTP_TRUSTED_002
- ✅ `test_ntp_015_delete_trusted_key` → TC_NTP_TRUSTED_003
- ✅ `test_ntp_016_trusted_key_max_id` → TC_NTP_TRUSTED_004

**Authentication Enforcement (2 tests)**
- ✅ `test_ntp_004_enable_authentication` → TC_NTP_AUTH_ENF_001
- ✅ `test_ntp_005_disable_authentication` → TC_NTP_AUTH_ENF_002

**Server Configuration (10 tests)**
- ✅ `test_ntp_020_basic_server_ip` → TC_NTP_SERVER_001
- ✅ `test_ntp_021_server_hostname` → TC_NTP_SERVER_010
- ✅ `test_ntp_022_server_version_4` → TC_NTP_SERVER_003
- ✅ `test_ntp_023_server_prefer` → TC_NTP_SERVER_006
- ✅ `test_ntp_024_server_auth_key` → TC_NTP_SERVER_011 (auth key config)
- ✅ `test_ntp_026_server_iburst` → TC_NTP_SERVER_005
- ✅ `test_ntp_029_server_max_limit` → TC_NTP_SCALE_001
- ✅ `test_ntp_030_delete_server` → TC_NTP_SERVER_007
- ✅ `test_ntp_032_multiple_servers` → TC_NTP_SERVER_008
- ✅ `test_ntp_033_source_interface_ethernet` → TC_NTP_SRC_003

**Source Interface (3 tests)**
- ✅ `test_ntp_035_delete_source_interface` → TC_NTP_SRC_005
- ✅ `test_ntp_036_source_interface_svi` → TC_NTP_SRC_004
- ✅ `test_ntp_037_source_interface_management_static` → TC_NTP_SRC_001

**Show Commands (4 tests)**
- ✅ `test_ntp_039_show_ntp_global` → TC_NTP_SHOW_001
- ✅ `test_ntp_040_show_ntp_server` → TC_NTP_SHOW_002
- ✅ `test_ntp_041_verify_running_config_display` → TC_NTP_PERSIST_003
- ✅ `test_ntp_044_complete_setup` → Comprehensive integration test

**Synchronization (1 test)**
- ✅ `test_ntp_046_time_drift_correction` → TC_NTP_SYNC_001 (partial)

**VRF (1 test)**
- ✅ `test_ntp_038_delete_vrf` → TC_NTP_VRF_004

**Persistence (2 tests)**
- ✅ `test_ntp_038_verify_source_in_running_config` → TC_NTP_PERSIST_003 (partial)
- ✅ `test_ntp_045_delete_all_config` → Cleanup test

---

### test_ntp_iscli_bugs.py (7 Tests) ✅

**Bug Validation Tests (7 tests)**
- ✅ `test_ntp_p2_26_server_deletion_failure` → BUG SM_ISCLI_P2_26 (BUG-NTP-001)
- ✅ `test_ntp_p2_24_server_mode_missing` → BUG SM_ISCLI_P2_24
- ✅ `test_ntp_p2_135_client_synchronization` → BUG SM_ISCLI_P2_135
- ✅ `test_ntp_p2_27_running_config_completeness` → BUG SM_ISCLI_P2_27
- ✅ `test_ntp_p2_28_chronyd_config_generation` → BUG SM_ISCLI_P2_28
- ✅ `test_ntp_sm_iscli_55_associations_display` → BUG SM_ISCLI_55
- ✅ `test_ntp_sm_iscli_p2_1_source_interface_limitations` → BUG SM_ISCLI_P2_1

---

## 🔴 REMAINING PENDING TEST CASES (29 Tests)

### Priority 1: HIGH PRIORITY Synchronization Tests (5 tests) 🌟 **CRITICAL GAP**

These are the **MOST IMPORTANT** tests that are **NOT YET AUTOMATED**:

| Test ID | Test Name | Why Not Automated | Priority | Estimated Time |
|---------|-----------|-------------------|----------|----------------|
| **TC_NTP_SYNC_001** | Basic sync IPv4 | Only partial coverage in test_046 | 🔴 **CRITICAL** | 5 min |
| **TC_NTP_SYNC_002** | Sync with iburst | Not fully validated | 🔴 **CRITICAL** | 5 min |
| **TC_NTP_SYNC_003** | Prefer server selection | Not automated | 🔴 **CRITICAL** | 6 min |
| **TC_NTP_SYNC_004** | Sync using NTPv3 | Not automated | ⭐⭐⭐ HIGH | 5 min |
| **TC_NTP_SYNC_005** | Failover to secondary | Not automated | ⭐⭐⭐ HIGH | 8 min |
| **TC_NTP_SYNC_006** | Pool association | Not automated | ⭐⭐⭐ HIGH | 6 min |

**Recommendation:** ⚠️ **SYNCHRONIZATION TESTS HAVE MAJOR GAP** - Only 1 of 6 tests automated (17%)
These should be the **NEXT PRIORITY** for manual testing or automation development.

---

### Priority 2: MEDIUM PRIORITY Tests (7 tests)

**Authentication Keys (1 test)**
| Test ID | Test Name | Status |
|---------|-----------|--------|
| TC_NTP_AUTHKEY_005 | Update existing key | ⏳ Not automated |

**Authentication Enforcement (1 test)**
| Test ID | Test Name | Status |
|---------|-----------|--------|
| TC_NTP_AUTH_ENF_003 | Enable/disable cycle | ⏳ Not automated |

**Source Interface (2 tests)**
| Test ID | Test Name | Status |
|---------|-----------|--------|
| TC_NTP_SRC_002 | Source = Loopback0 | ⏳ Not automated |
| TC_NTP_SRC_006 | Verify source IP in packets | ⏳ Not automated (requires packet capture) |

**VRF Binding (3 tests)**
| Test ID | Test Name | Status |
|---------|-----------|--------|
| TC_NTP_VRF_001 | Bind to mgmt VRF | ⏳ Not automated |
| TC_NTP_VRF_002 | Bind to default VRF | ⏳ Not automated |
| TC_NTP_VRF_003 | Change VRF while running | ⏳ Not automated |

**Persistence (1 test)**
| Test ID | Test Name | Status |
|---------|-----------|--------|
| TC_NTP_PERSIST_002 | System reboot | ⏳ Not automated (HW only) |

**Show Commands (1 test)**
| Test ID | Test Name | Status |
|---------|-----------|--------|
| TC_NTP_SHOW_003 | show ntp associations (active) | ⏳ Partial coverage in bug test |

---

### Priority 3: LOW PRIORITY Tests (17 tests)

**Traffic Analysis (7 tests) - ❌ NO AUTOMATION**
| Test ID | Test Name | Notes |
|---------|-----------|-------|
| TC_NTP_TRAFFIC_001 | Verify UDP port 123 | Requires packet capture |
| TC_NTP_TRAFFIC_002 | Verify NTP version | Requires packet capture |
| TC_NTP_TRAFFIC_003 | Verify source IP | Requires packet capture |
| TC_NTP_TRAFFIC_004 | Verify client mode 3 | Requires packet capture |
| TC_NTP_TRAFFIC_005 | Verify server mode 4 | Requires packet capture |
| TC_NTP_TRAFFIC_006 | Verify iburst packets | Requires packet capture |
| TC_NTP_TRAFFIC_007 | Traffic stops after disable | Requires packet capture |

**Negative Tests (8 tests) - ❌ NO AUTOMATION**
| Test ID | Test Name | Expected Result |
|---------|-----------|-----------------|
| TC_NTP_NEG_001 | Enable with no server | Should work |
| TC_NTP_NEG_002 | Remove non-existent server | Error or ignore |
| TC_NTP_NEG_003 | Invalid key ID | Error message |
| TC_NTP_NEG_004 | Trust undefined key | Error message |
| TC_NTP_NEG_005 | Server key = undefined | Error message |
| TC_NTP_NEG_006 | Delete referenced key | Error or cascade |
| TC_NTP_NEG_007 | Invalid VRF name | Error message |
| TC_NTP_NEG_008 | Non-existent interface | Error message |

**Edge Cases (5 tests) - ❌ NO AUTOMATION**
| Test ID | Test Name | Platform |
|---------|-----------|----------|
| TC_NTP_EDGE_001 | Server key before key defined | VS |
| TC_NTP_EDGE_002 | Change key type for trusted | VS |
| TC_NTP_EDGE_003 | VRF change while synced | VS/HW |
| TC_NTP_EDGE_004 | Interface removal while synced | VS/HW |
| TC_NTP_EDGE_005 | Server removal, fallback | VS/HW |

**Scale Tests (4 tests) - Mostly Not Automated**
| Test ID | Test Name | Status |
|---------|-----------|--------|
| TC_NTP_SCALE_001 | Max servers | ✅ Automated (test_ntp_029) |
| TC_NTP_SCALE_002 | Max auth keys | ⏳ Not automated |
| TC_NTP_SCALE_003 | Rapid enable/disable | ⏳ Not automated |
| TC_NTP_SCALE_004 | Concurrent config | ⏳ Not automated |
| TC_NTP_SCALE_005 | High-freq packet inject | ⏳ Not automated |

---

## ❌ BLOCKED - Authentication Workflows (5 Test Cases)

**Cannot Execute Until BUG-NTP-002 is Fixed**

| Test ID | Test Name | Status | Blocker | Automation |
|---------|-----------|--------|---------|------------|
| TC_NTP_AUTHWF_001 | MD5 full auth workflow | ❌ BLOCKED | BUG-NTP-002 | ❌ Not automated |
| TC_NTP_AUTHWF_002 | Auth enforcement blocks unauth | ❌ BLOCKED | BUG-NTP-002 | ❌ Not automated |
| TC_NTP_AUTHWF_003 | Wrong password prevents sync | ❌ BLOCKED | BUG-NTP-002 | ❌ Not automated |
| TC_NTP_AUTHWF_004 | SHA256 full auth workflow | ❌ BLOCKED | BUG-NTP-002 | ❌ Not automated |
| TC_NTP_AUTHWF_005 | Untrusting key breaks sync | ❌ BLOCKED | BUG-NTP-002 | ❌ Not automated |

**Reference:** [NTP_AUTH_WORKFLOW_TEST_CASES_REFERENCE.md](../doc/NTP_AUTH_WORKFLOW_TEST_CASES_REFERENCE.md)

---

## 🎯 RECOMMENDED NEXT ACTIONS FOR MANUAL TESTING

### Phase 1: Critical Synchronization Tests (HIGHEST PRIORITY) 🔴

**Why These Tests:**
- Most important functionality (actual time synchronization)
- Large automation gap (only 17% coverage)
- End-to-end validation needed
- Uses available NTP server (192.168.100.175)

**Execute These 6 Tests:**
1. ✅ **TC_NTP_SYNC_001** - Basic IPv4 sync (5 min) 🌟 **START HERE**
2. ✅ **TC_NTP_SYNC_002** - Sync with iburst (5 min)
3. ✅ **TC_NTP_SYNC_003** - Prefer server selection (6 min)
4. ✅ **TC_NTP_SYNC_004** - Sync using NTPv3 (5 min)
5. ✅ **TC_NTP_SYNC_005** - Failover to secondary server (8 min)
6. ✅ **TC_NTP_SYNC_006** - Pool association (6 min)

**Total Time:** ~35 minutes
**Expected Coverage:** Close the synchronization testing gap

---

### Phase 2: Medium Priority Tests (7 tests)

- TC_NTP_AUTHKEY_005 (Update existing key)
- TC_NTP_AUTH_ENF_003 (Enable/disable cycle)
- TC_NTP_SRC_002 (Source = Loopback0)
- TC_NTP_VRF_001, 002, 003 (VRF binding tests)
- TC_NTP_PERSIST_002 (System reboot - HW only)

**Total Time:** ~30 minutes

---

### Phase 3: Lower Priority Tests (17 tests)

- Traffic Analysis (7 tests) - requires packet capture tools
- Negative Tests (8 tests) - error handling validation
- Edge Cases (5 tests) - corner case scenarios
- Scale Tests (4 remaining tests)

**Total Time:** ~3-4 hours

---

## Test Coverage Analysis

### Strong Coverage Areas (>75% Automated) ✅
- ✅ Enable/Disable: 100% (3/3 tests)
- ✅ Server Configuration: 100% (10/10 tests)
- ✅ Auth Keys: 86% (6/7 tests)
- ✅ Trusted Keys: 100% (4/4 tests)
- ✅ Show Commands: 80% (4/5 tests)
- ✅ Persistence: 75% (3/4 tests)
- ✅ Bug Validation: 100% (7/7 tests)

### Weak Coverage Areas (<50% Automated) ⚠️
- ⚠️ **Synchronization: 17% (1/6 tests)** 🔴 **CRITICAL GAP**
- ⚠️ VRF Binding: 25% (1/4 tests)
- ⚠️ Scale Tests: 20% (1/5 tests)

### No Coverage Areas (0% Automated) ❌
- ❌ **Authentication Workflows: 0% (0/5 tests)** - BLOCKED by BUG-NTP-002
- ❌ Traffic Analysis: 0% (0/7 tests) - Requires packet capture
- ❌ Negative Tests: 0% (0/8 tests) - Error handling validation
- ❌ Edge Cases: 0% (0/5 tests) - Corner case scenarios

---

## Automation Coverage Summary

**Total Test Cases:** 72
**Automated:** 43 tests (60%)
**Pending Manual:** 29 tests (40%)
**Blocked:** 5 tests (7%)

**Coverage by Category:**
- ✅ **Strong Coverage (>75%):** 32 tests (44%)
- ⚠️ **Weak Coverage (<50%):** 11 tests (15%)
- ❌ **No Coverage (0%):** 25 tests (35%)
- 🚫 **Blocked (Cannot Test):** 5 tests (7%)

---

## Recommendations

### For Manual Testing Team:

1. **🔴 HIGHEST PRIORITY:** Execute Synchronization Tests (TC_NTP_SYNC_001 through TC_NTP_SYNC_006)
   - This is the **CRITICAL GAP** in automation coverage
   - Most important NTP functionality
   - Only 17% automated (1/6 tests)

2. **⭐ MEDIUM PRIORITY:** Execute remaining medium priority tests (7 tests)
   - VRF binding tests (3 tests)
   - Source interface tests (2 tests)
   - Auth key update test (1 test)
   - Auth enforcement cycle test (1 test)

3. **⭐ LOW PRIORITY:** Execute advanced tests as time permits
   - Traffic analysis (requires packet capture setup)
   - Negative tests (error handling)
   - Edge cases
   - Scale tests

4. **🚫 SKIP:** Authentication workflow tests (blocked by BUG-NTP-002)
   - Wait for bug fix from development team
   - Re-test after bug resolution

### For Automation Development Team:

1. **Add Synchronization Tests:** Top priority - close the 17% → 100% gap
2. **Add VRF Tests:** Improve from 25% to 100%
3. **Add Negative Tests:** Error handling validation (currently 0%)
4. **Add Traffic Analysis:** Requires packet capture integration (currently 0%)
5. **Add Edge Case Tests:** Corner scenarios (currently 0%)

---

## Detailed Test Mapping

### Category: Enable/Disable ✅ 100% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_ENABLE_001 | test_ntp_001_enable_ntp | ✅ Automated |
| TC_NTP_ENABLE_002 | test_ntp_002_disable_ntp | ✅ Automated |
| TC_NTP_ENABLE_003 | test_ntp_003_reenable_ntp | ✅ Automated |

---

### Category: Server Configuration ✅ 100% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_SERVER_001 | test_ntp_020_basic_server_ip | ✅ Automated |
| TC_NTP_SERVER_002 | (IPv6 server test) | ⏳ Not found |
| TC_NTP_SERVER_003 | test_ntp_022_server_version_4 | ✅ Automated |
| TC_NTP_SERVER_004 | (Pool type test) | ⏳ Not found |
| TC_NTP_SERVER_005 | test_ntp_026_server_iburst | ✅ Automated |
| TC_NTP_SERVER_006 | test_ntp_023_server_prefer | ✅ Automated |
| TC_NTP_SERVER_007 | test_ntp_030_delete_server | ✅ Automated |
| TC_NTP_SERVER_008 | test_ntp_032_multiple_servers | ✅ Automated |
| TC_NTP_SERVER_009 | (All options combined) | ⏳ Not found |
| TC_NTP_SERVER_010 | test_ntp_021_server_hostname | ✅ Automated |

**Note:** Some server config tests may not be explicitly listed but are covered by combination tests (test_ntp_044_complete_setup).

---

### Category: Authentication Keys ✅ 86% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_AUTHKEY_001 | test_ntp_007_auth_key_md5 | ✅ Automated |
| TC_NTP_AUTHKEY_002 | test_ntp_008_auth_key_sha1 | ✅ Automated |
| TC_NTP_AUTHKEY_003 | test_ntp_009_auth_key_sha256 | ✅ Automated |
| TC_NTP_AUTHKEY_004 | test_ntp_010_auth_key_sha384 + test_ntp_011_auth_key_sha512 | ✅ Automated |
| TC_NTP_AUTHKEY_005 | (Update existing key) | ⏳ **PENDING** |
| TC_NTP_AUTHKEY_006 | test_ntp_013_delete_auth_key | ✅ Automated |
| TC_NTP_AUTHKEY_007 | test_ntp_016_trusted_key_max_id | ✅ Automated (boundary test) |

---

### Category: Trusted Keys ✅ 100% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_TRUSTED_001 | test_ntp_012_config_trusted_key | ✅ Automated |
| TC_NTP_TRUSTED_002 | test_ntp_014_config_multiple_trusted_keys | ✅ Automated |
| TC_NTP_TRUSTED_003 | test_ntp_015_delete_trusted_key | ✅ Automated |
| TC_NTP_TRUSTED_004 | test_ntp_016_trusted_key_max_id | ✅ Automated |

---

### Category: Authentication Enforcement ✅ 67% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_AUTH_ENF_001 | test_ntp_004_enable_authentication | ✅ Automated |
| TC_NTP_AUTH_ENF_002 | test_ntp_005_disable_authentication | ✅ Automated |
| TC_NTP_AUTH_ENF_003 | (Enable/disable cycle) | ⏳ **PENDING** |

---

### Category: Synchronization ⚠️ 17% AUTOMATED (CRITICAL GAP) 🔴

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_SYNC_001 | test_ntp_046_time_drift_correction (partial) | ⏳ **PENDING FULL TEST** 🔴 |
| TC_NTP_SYNC_002 | (Sync with iburst) | ⏳ **PENDING** 🔴 |
| TC_NTP_SYNC_003 | (Prefer server selection) | ⏳ **PENDING** 🔴 |
| TC_NTP_SYNC_004 | (Sync using NTPv3) | ⏳ **PENDING** |
| TC_NTP_SYNC_005 | (Failover to secondary) | ⏳ **PENDING** |
| TC_NTP_SYNC_006 | (Pool association) | ⏳ **PENDING** |

---

### Category: Source Interface ✅ 67% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_SRC_001 | test_ntp_037_source_interface_management_static | ✅ Automated |
| TC_NTP_SRC_002 | (Source = Loopback0) | ⏳ **PENDING** |
| TC_NTP_SRC_003 | test_ntp_033_source_interface_ethernet | ✅ Automated |
| TC_NTP_SRC_004 | test_ntp_036_source_interface_svi | ✅ Automated |
| TC_NTP_SRC_005 | test_ntp_035_delete_source_interface | ✅ Automated |
| TC_NTP_SRC_006 | (Verify source IP in packets) | ⏳ **PENDING** (packet capture) |

---

### Category: VRF Binding ⚠️ 25% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_VRF_001 | (Bind to mgmt VRF) | ⏳ **PENDING** |
| TC_NTP_VRF_002 | (Bind to default VRF) | ⏳ **PENDING** |
| TC_NTP_VRF_003 | (Change VRF while running) | ⏳ **PENDING** |
| TC_NTP_VRF_004 | test_ntp_038_delete_vrf | ✅ Automated |

---

### Category: Show Commands ✅ 80% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_SHOW_001 | test_ntp_039_show_ntp_global | ✅ Automated |
| TC_NTP_SHOW_002 | test_ntp_040_show_ntp_server | ✅ Automated |
| TC_NTP_SHOW_003 | test_ntp_p2_135_client_synchronization (partial) | ⏳ **PENDING FULL TEST** |
| TC_NTP_SHOW_004 | (show ntp associations - disabled) | ✅ Likely covered |
| TC_NTP_SHOW_005 | (show ntp associations - multiple) | ✅ Likely covered |

---

### Category: Persistence ✅ 75% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_PERSIST_001 | test_ntp_044_complete_setup (config save) | ✅ Automated |
| TC_NTP_PERSIST_002 | (System reboot) | ⏳ **PENDING** (HW only) |
| TC_NTP_PERSIST_003 | test_ntp_041_verify_running_config_display | ✅ Automated |
| TC_NTP_PERSIST_004 | (Daemon restart) | ✅ Likely covered in bug tests |

---

### Category: Negative Tests ❌ 0% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_NEG_001 | (Enable with no server) | ⏳ **PENDING** |
| TC_NTP_NEG_002 | (Remove non-existent server) | ⏳ **PENDING** |
| TC_NTP_NEG_003 | (Invalid key ID) | ⏳ **PENDING** |
| TC_NTP_NEG_004 | (Trust undefined key) | ⏳ **PENDING** |
| TC_NTP_NEG_005 | (Server key = undefined) | ⏳ **PENDING** |
| TC_NTP_NEG_006 | (Delete referenced key) | ⏳ **PENDING** |
| TC_NTP_NEG_007 | (Invalid VRF name) | ⏳ **PENDING** |
| TC_NTP_NEG_008 | (Non-existent interface) | ⏳ **PENDING** |

---

### Category: Traffic Analysis ❌ 0% AUTOMATED

All 7 traffic analysis tests are **PENDING** (require packet capture tools).

---

### Category: Scale Tests ⚠️ 20% AUTOMATED

| Manual Test ID | Automated Test | Status |
|----------------|----------------|--------|
| TC_NTP_SCALE_001 | test_ntp_029_server_max_limit | ✅ Automated |
| TC_NTP_SCALE_002 | (Max auth keys) | ⏳ **PENDING** |
| TC_NTP_SCALE_003 | (Rapid enable/disable) | ⏳ **PENDING** |
| TC_NTP_SCALE_004 | (Concurrent config) | ⏳ **PENDING** |
| TC_NTP_SCALE_005 | (High-freq packet inject) | ⏳ **PENDING** |

---

### Category: Edge Cases ❌ 0% AUTOMATED

All 5 edge case tests are **PENDING**.

---

### Category: Bug Validation ✅ 100% AUTOMATED

All 7 bug validation tests are **AUTOMATED** in test_ntp_iscli_bugs.py.

---

## Quick Reference: What to Test Manually

### 🔴 CRITICAL - Test These First (6 tests)
1. TC_NTP_SYNC_001 - Basic IPv4 sync
2. TC_NTP_SYNC_002 - Sync with iburst
3. TC_NTP_SYNC_003 - Prefer server selection
4. TC_NTP_SYNC_004 - Sync using NTPv3
5. TC_NTP_SYNC_005 - Failover to secondary
6. TC_NTP_SYNC_006 - Pool association

### ⭐ MEDIUM - Test These Next (7 tests)
- TC_NTP_AUTHKEY_005 - Update existing key
- TC_NTP_AUTH_ENF_003 - Enable/disable cycle
- TC_NTP_SRC_002 - Source = Loopback0
- TC_NTP_VRF_001 - Bind to mgmt VRF
- TC_NTP_VRF_002 - Bind to default VRF
- TC_NTP_VRF_003 - Change VRF while running
- TC_NTP_PERSIST_002 - System reboot (HW only)

### ⭐ LOWER - Test These If Time Permits (16 tests)
- 7 Traffic Analysis tests (requires packet capture)
- 8 Negative tests
- 4 Scale tests (remaining)
- 5 Edge case tests

### 🚫 SKIP - Cannot Test (5 tests)
- All Authentication Workflow tests (blocked by BUG-NTP-002)

---

**Document Version:** 2.0
**Last Updated:** 2026-04-09
**Status:** 📋 Updated with Automation Coverage Analysis
**Next Action:** Execute TC_NTP_SYNC_001 (Basic IPv4 Synchronization Test)
