# Manual Test Report: SM_ISCLI_P2_26
## NTP Server Deletion Failure in Klish Mode

---

**Bug ID**: SM_ISCLI_P2_26
**Title**: Cannot delete NTP server configuration by using ip/hostname in klish mode
**Status**: ✅ **CONFIRMED**
**Severity**: **HIGH** (P2)
**Classification**: **BUG - Configuration Management Failure**
**Test Date**: 2026-04-07 15:02
**Device**: 192.168.100.147
**Tester**: Claude Code (Automated Manual Test)

---

## Executive Summary

**BUG CONFIRMED** - The `no ntp server <ip/hostname>` command in klish mode **silently fails** to delete NTP server configurations. The command is accepted without error, but the NTP server remains configured. This prevents users from removing unwanted NTP servers via the klish CLI.

**Impact**:
- Users cannot manage NTP server lists effectively via klish mode
- Misconfigured or obsolete NTP servers cannot be removed
- Only workaround is to use click mode backend commands (`sudo config ntp del <server>`)
- Silent failure creates confusion - users believe deletion succeeded when it didn't

---

## Test Results Summary

| Test Step | Command | Expected Result | Actual Result | Status |
|-----------|---------|-----------------|---------------|--------|
| STEP 1 | Configure 3 servers | Servers added | ✅ 3 servers added | ✅ PASS |
| STEP 2 | Delete 192.168.100.175 | Server removed | ❌ Server still present | ❌ FAIL |
| STEP 3 | Delete time.google.com | Server removed | ❌ Server still present | ❌ FAIL |
| STEP 4 | Delete 10.10.10.99 | Server removed | ❌ Server still present | ❌ FAIL |
| STEP 5 | Verify final state | Empty server list | ❌ All servers present | ❌ FAIL |

**Failure Rate**: **100%** (0 out of 3 deletion attempts succeeded)

---

## Detailed Test Evidence

### STEP 2: Deletion by IP Failed

**Command Executed**:
```
sonic# configure terminal
sonic(config)# no ntp server 192.168.100.175
sonic(config)# exit
```

**Verification**:
```
sonic# show ntp server
---------------------------------------------------------------------------------------------------------------------
NTP Servers                     minpoll maxpoll Prefer Authentication key ID
---------------------------------------------------------------------------------------------------------------------
10.10.10.99                                     False
192.168.100.175                                 False  ⬅️ STILL PRESENT!
216.239.35.12                                   False
time.google.com                                 False
```

**Result**: ❌ Server 192.168.100.175 NOT deleted (command silently failed)

---

### STEP 3: Deletion by Hostname Failed

**Command Executed**:
```
sonic(config)# no ntp server time.google.com
```

**Result**: ❌ Server time.google.com NOT deleted (still present in show output)

---

### STEP 4: Deletion by IP (Second Server) Failed

**Command Executed**:
```
sonic(config)# no ntp server 10.10.10.99
```

**Result**: ❌ Server 10.10.10.99 NOT deleted (still present in show output)

---

### Backend Verification

**chronyd Sources** (from `show ntp`):
```
MS Name/IP address         Stratum Poll Reach LastRx Last sample
===============================================================================
^? 10.10.10.99                   0   7     0     -     +0ns[   +0ns] +/-    0ns
^? 192.168.100.175               0   7     0     -     +0ns[   +0ns] +/-    0ns
^* 216.239.35.12                 1   6    77    28  -1132us[-1549us] +/-   20ms
```

**Conclusion**: Backend confirms deletion did NOT propagate to chronyd configuration

---

## Root Cause Analysis

### Bug Manifestation

The `no ntp server <ip/hostname>` command exhibits **silent failure**:

1. ✅ Command parser accepts the command (no syntax error)
2. ❌ Backend does NOT remove server from Config DB
3. ❌ No error message or warning displayed to user
4. ❌ Deletion does NOT propagate to chronyd

### Likely Root Cause

**Command Translation Bug** (Most Likely):
- Klish CLI command `no ntp server <address>` not correctly translated to Config DB operation
- Backend handler for NTP server deletion may be missing or broken
- Positive command (`ntp server <address>`) works → suggests asymmetric implementation

---

## Impact Assessment

### Severity: **HIGH (P2)**

**Business Impact**:
- Configuration management failure - users cannot remove misconfigured NTP servers
- Operational risk - obsolete/unreachable NTP servers accumulate
- Troubleshooting difficulty - silent failure creates user confusion
- Workaround exists but requires backend access and knowledge

### Affected Scenarios

1. **NTP Server Migration**: Cannot replace old server with new via klish
2. **Troubleshooting**: Cannot remove unreachable server temporarily
3. **Security Hardening**: Cannot remove public NTP servers
4. **Error Correction**: Cannot fix typo in NTP server IP/hostname

---

## Workaround

### Immediate Workaround: Use Click Mode

**Steps**:
```bash
admin@sonic:~$ sudo config ntp del 192.168.100.175
admin@sonic:~$ sudo config ntp del time.google.com
admin@sonic:~$ show ntp  # Verify deletion
```

**Limitations**:
- Requires backend shell access
- Requires knowledge of click mode commands
- Not available in restricted environments

---

## Automation Coverage Analysis

### Gap Identified

**No test coverage for NTP server deletion via klish**

**Recommended Test Case**: `test_ntp_XXX_delete_ntp_server_klish()`

**Test Design**:
```python
def test_ntp_XXX_delete_ntp_server_klish():
    # Configure NTP servers
    ntp_api.config_ntp_server(dut, "192.168.100.175", cli_type="klish")
    
    # Verify configured
    servers = ntp_api.verify_ntp_server_details(dut, cli_type="klish")
    if "192.168.100.175" not in servers:
        st.report_fail("ntp_server_config_failed")
    
    # Delete NTP server
    ntp_api.config_ntp_server(dut, "192.168.100.175", 
                               config="no", cli_type="klish")
    
    # Verify deletion (BUG MANIFESTS HERE)
    servers_after = ntp_api.verify_ntp_server_details(dut, cli_type="klish")
    if "192.168.100.175" in servers_after:
        st.report_fail("ntp_server_deletion_failed")
    
    st.report_pass("ntp_server_deletion_successful")
```

---

## Recommendations

### Short-Term (P2 Priority)

1. **Fix the Bug**:
   - Investigate klish backend handler for `no ntp server` command
   - Ensure correct Config DB deletion operation
   - Add error handling and user feedback

2. **Add Error Messaging** (if fix delayed):
   ```
   %Error: NTP server deletion not supported in klish mode.
   Use click mode: 'sudo config ntp del <server>'
   ```

3. **Document Workaround**:
   - Add to SONiC documentation
   - Include in troubleshooting guide

### Long-Term

4. **Add Automation Test Coverage**:
   - Implement deletion test as regression check
   - Add to CI/CD pipeline and nightly test suite

5. **Audit All NTP "no" Commands**:
   - Verify `no ntp source-interface`, `no ntp enable` work correctly
   - Ensure symmetric implementation (if `ntp X` works, `no ntp X` should too)

---

## Test Artifacts

**Test Script**: `/tmp/bug_sm_iscli_p2_26_test_v2.sh`
**Test Log**: `/tmp/bug_sm_iscli_p2_26_test.log`

**Key Test Features**:
- Automated SSH command execution
- Step-by-step logging with timestamps
- Comprehensive verification at each step
- Workaround for SM_ISCLI_P2_27 bug (uses `exit` instead of `end`)

---

## Conclusion

**Status**: ✅ **CONFIRMED** - Bug is reproducible and verified

**Evidence Strength**: **CONCLUSIVE**
- 3 out of 3 deletion attempts failed (100% failure rate)
- Both IP and hostname deletion failed equally
- Backend verification confirms no propagation
- Silent failure (no error message)

**Classification**: Configuration Management Bug (klish CLI NTP module)

**Next Steps**:
1. ✅ Report to Development Team
2. ⏳ Track Bug Fix in bug tracking system
3. ⏳ Add Automation Test to prevent regression
4. ⏳ Verify Fix with re-test after patch
5. ⏳ Update Documentation with workaround

---

## Related Bugs

| Bug ID | Relationship |
|--------|--------------|
| **SM_ISCLI_P2_27** | Internal error with `end` command (blocks testing, workaround used) |
| **SM_ISCLI_P2_22** | Source-interface deletion failure (similar pattern) |

**Pattern Observation**: Both P2_26 (server deletion) and P2_22 (source-interface deletion) show deletion command failures, suggesting potential systemic issue with NTP "no" commands in klish.

---

**Report Status**: FINAL
**Report Date**: 2026-04-07 15:05
**Report Version**: 1.0
**Prepared By**: Claude Code

---
