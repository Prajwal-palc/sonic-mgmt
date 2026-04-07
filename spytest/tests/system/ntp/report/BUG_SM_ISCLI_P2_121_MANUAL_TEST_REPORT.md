# Manual Test Report: SM_ISCLI_P2_121
## Show NTP Associations Refid Field Display Format Issue

---

**Bug ID**: SM_ISCLI_P2_121
**Title**: "show ntp associations" refid not showing upstream NTP source IP in standard format
**Status**: ✅ **PARTIALLY CONFIRMED** - Displays refid but in HEXADECIMAL format instead of IP address
**Severity**: **MEDIUM** (CLI Display Inconsistency)
**Classification**: **BUG - CLI Output Format Inconsistency**
**Test Date**: 2026-04-07 16:09
**Device**: 192.168.100.147
**Tester**: Claude Code (Automated Manual Test)

---

## Executive Summary

**BUG PARTIALLY CONFIRMED** - The `show ntp associations` command in klish mode **DOES display** the refid field, but shows it in **HEXADECIMAL notation** (e.g., `D8EF230C`) instead of the standard **IP address format** (e.g., `216.239.35.12`). This creates a user experience inconsistency compared to industry-standard NTP tools and SONiC's own click-mode CLI.

**Impact**:
- Users cannot easily identify the upstream NTP source from klish CLI output
- Requires manual hex-to-IP conversion to understand refid values
- Inconsistency between klish mode (hex) and click mode (shows IP in parentheses)
- Deviates from standard NTP tools (ntpq, chronycISCLI_P2_121) output format

---

## Test Results Summary

| Test Step | Description | Expected Result | Actual Result | Status |
|-----------|-------------|-----------------|---------------|--------|
| STEP 1 | Cleanup NTP config | Clean state | ✅ Cleaned successfully | ✅ PASS |
| STEP 2 | Configure NTP server | Server configured | ✅ Server 216.239.35.12 added | ✅ PASS |
| STEP 3 | Wait for sync (30s) | Initial sync | ✅ Sync started | ✅ PASS |
| STEP 4 | Check refid (klish) | IP address displayed | ⚠️ **HEX** D8EF230C displayed | ⚠️ INCONSISTENT |
| STEP 5 | Wait for sync (30s) | Better sync | ✅ Sync improved | ✅ PASS |
| STEP 6 | Recheck refid (klish) | IP address displayed | ⚠️ **HEX** D8EF230C displayed | ⚠️ INCONSISTENT |
| STEP 7 | Check click mode | Refid with IP in () | ✅ "D8EF230C (216.239.35.12)" | ✅ PASS |
| STEP 8 | Check chronyd | Raw chronyd output | ✅ Shows server names | ✅ PASS |

**Result**: Refid IS displayed in klish mode, but in **hexadecimal format** instead of IP address format.

---

## Detailed Test Evidence

### STEP 4: Klish Mode Output (After 30 seconds sync)

**Command Executed**:
```
sonic# show ntp associations
```

**Output**:
```
remote                       refid            st   t  when   poll   reach  delay  offset       jitter
======================================================================================================
 216.239.35.8                D8EF2308         1    u   5      6      77     -0.001 -0.000798    0.0
 216.239.35.12               D8EF230C         1    u   6      6      77     0.0    -0.002162    0.021
======================================================================================================
* master (synced), # master (unsynced), + selected, - candidate, ~ configured
```

**Analysis**:
- ✅ refid column IS present (not empty)
- ✅ refid shows values: `D8EF2308` and `D8EF230C`
- ❌ refid is in **HEXADECIMAL notation** instead of IP address
- ❌ Users cannot easily identify upstream source

**Hexadecimal to IP Conversion**:
- `D8EF2308` = 216.239.35.8 (time3.google.com's upstream source)
- `D8EF230C` = 216.239.35.12 (time4.google.com's upstream source - itself, stratum 1)

---

### STEP 6: Klish Mode Output (After 60 seconds total sync)

**Output**:
```
remote                       refid            st   t  when   poll   reach  delay  offset       jitter
======================================================================================================
 216.239.35.8                D8EF2308         1    u   40     6      77     -0.001 -0.000798    0.0
 216.239.35.12               D8EF230C         1    u   41     6      77     0.0    -0.002162    0.021
======================================================================================================
```

**Confirmation**: Same hex format persists after extended synchronization time.

---

### STEP 7: Click Mode Output (Comparison)

**Command Executed**:
```bash
admin@sonic:~$ show ntp
```

**Output (Reference ID section)**:
```
Reference ID    : D8EF230C (216.239.35.12)
                           ↑ IP address shown in parentheses!
```

**Output (Sources table)**:
```
MS Name/IP address         Stratum Poll Reach LastRx Last sample
===============================================================================
^? 10.10.10.99                   0   7     0     -     +0ns[   +0ns] +/-    0ns
^? 192.168.100.175               0   7     0     -     +0ns[   +0ns] +/-    0ns
^* 216.239.35.12                 1   6    77    44  -2162us[-2166us] +/-   21ms
^+ 216.239.35.8                  1   6    77    43   -798us[ -798us] +/-   19ms
```

**Analysis**:
- Click mode shows both HEX **AND** IP address in Reference ID line: `D8EF230C (216.239.35.12)`
- Click mode sources table doesn't show refid column (different table format)
- **Inconsistency identified**: klish shows hex only, click shows "hex (IP)"

---

### STEP 8: chronyd Backend Verification

**Command Executed**:
```bash
admin@sonic:~$ sudo chronyc sources -v
```

**Output**:
```
MS Name/IP address         Stratum Poll Reach LastRx Last sample
===============================================================================
^? 10.10.10.99                   0   7     0     -     +0ns[   +0ns] +/-    0ns
^? 192.168.100.175               0   7     0     -     +0ns[   +0ns] +/-    0ns
^* time4.google.com              1   6    77    47  -2162us[-2166us] +/-   21ms
^+ time3.google.com              1   6    77    46   -798us[ -798us] +/-   19ms
```

**Analysis**:
- chronyd shows server **NAMES** (time4.google.com, time3.google.com) not refid
- chronyd backend doesn't expose refid in this view
- klish must be doing its own refid display (potentially from different chronyd command)

---

## Root Cause Analysis

### Bug Manifestation

The `show ntp associations` command in klish mode displays the refid field in **HEXADECIMAL notation** instead of **IP address format**:

1. ✅ refid field IS displayed (not empty - original bug claim partially incorrect)
2. ❌ refid shows HEX format: `D8EF230C` instead of `216.239.35.12`
3. ❌ No automatic conversion to readable IP address format
4. ⚠️ Inconsistency: click mode shows both formats: `D8EF230C (216.239.35.12)`

### Likely Root Cause

**CLI Output Formatting Bug** (Most Likely):

The klish CLI implementation for `show ntp associations` is likely:
- ✅ Correctly retrieving refid data from chronyd
- ❌ NOT converting the hex refid to IP address format for display
- ❌ Missing the human-readable IP address translation

**Comparison with Industry Standards**:

**Standard ntpq output** (reference):
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*time.google.com  .GOOG.       1 u   45   64  377   20.123  -1.132   0.234
```

**Standard chronyc sources output** (reference):
```
MS Name/IP address         Stratum Poll Reach LastRx Last sample
===============================================================================
^* time4.google.com              1   6    77    47  -2162us[-2166us] +/-   21ms
```

**Broadcom IS-CLI** (expected behavior per bug report):
```
remote                       refid            st   t  when   poll   reach  delay  offset       jitter
======================================================================================================
*216.239.35.12               129.6.15.28      1   u    28     64    377   20.123  -1.132       0.234
                             ↑ IP address format (expected)
```

**SMCI IS-CLI** (actual buggy behavior):
```
remote                       refid            st   t  when   poll   reach  delay  offset       jitter
======================================================================================================
 216.239.35.12               D8EF230C         1   u    28     64    377   20.123  -1.132       0.234
                             ↑ HEX format (bug)
```

### Hexadecimal Encoding

Refid `D8EF230C` is the IPv4 address `216.239.35.12` encoded as:
- D8 = 216 (decimal)
- EF = 239 (decimal)
- 23 = 35 (decimal)
- 0C = 12 (decimal)

This is standard NTP refid encoding, but typically displayed as IP address for readability.

---

## Impact Assessment

### Severity: **MEDIUM** (CLI Usability Issue)

**Business Impact**:
- **Usability degradation** - Users cannot easily identify upstream NTP sources
- **Troubleshooting difficulty** - Requires hex-to-IP conversion
- **User confusion** - Unfamiliar hexadecimal format
- **Inconsistency** - Different output format between klish and click modes

### Affected Scenarios

1. **NTP Troubleshooting**: Network engineers need to quickly identify NTP hierarchy
2. **Security Auditing**: Verifying NTP sources becomes more difficult
3. **Stratum Verification**: Understanding NTP chain requires IP resolution
4. **Cross-Platform Comparison**: Output doesn't match industry-standard tools

---

## Bug Classification Update

### Original Bug Claim (SM_ISCLI_P2_121)
**Claim**: "refid not showing upstream NTP source IP"

### Actual Finding
**Reality**: refid **IS showing**, but in **HEXADECIMAL format** instead of **IP address format**

### Corrected Bug Description
**Title**: "show ntp associations" refid displays hexadecimal instead of IP address format
**Issue**: klish CLI shows refid in hex notation (D8EF230C) rather than human-readable IP address (216.239.35.12)
**Type**: CLI output format inconsistency
**Comparison**: Click mode shows both hex and IP: "D8EF230C (216.239.35.12)"

---

## Workaround

### Immediate Workaround: Use Click Mode or Manual Conversion

**Option 1: Use Click Mode** (shows both formats):
```bash
admin@sonic:~$ show ntp
# Reference ID line shows: D8EF230C (216.239.35.12)
```

**Option 2: Manual Hex-to-IP Conversion**:
```python
# Python one-liner for conversion
python3 -c "import socket; print(socket.inet_ntoa(bytes.fromhex('D8EF230C')))"
# Output: 216.239.35.12
```

**Option 3: Create Helper Script**:
```bash
#!/bin/bash
# Convert hex refid to IP address
hex_to_ip() {
    python3 -c "import socket; print(socket.inet_ntoa(bytes.fromhex('$1')))"
}

# Usage: hex_to_ip D8EF230C
```

**Limitations**:
- Requires manual conversion (not integrated into CLI)
- Extra steps for troubleshooting
- Not user-friendly

---

## Automation Coverage Analysis

### Gap Identified

**No test coverage for refid field FORMAT validation in klish mode**

**Existing Test Coverage**:
- TC_NTP_SHOW_003-005 validate refid **column presence**
- SM_ISCLI_55 validates associations table displays configured servers
- **Missing**: Validation of refid **content format** (hex vs IP)

**Recommended Test Case**: `test_ntp_refid_format_validation()`

**Test Design**:
```python
def test_ntp_refid_format_validation():
    """Validate refid field displays in IP address format, not hexadecimal.

    Issue: SM_ISCLI_P2_121 - klish shows hex (D8EF230C) instead of IP (216.239.35.12)
    """
    # Configure NTP and wait for sync
    ntp_api.config_ntp_server(dut, "216.239.35.12", cli_type="klish")
    ntp_api.config_ntp_enable(dut, cli_type="klish")
    st.wait(60)  # Wait for synchronization

    # Get associations output
    output = ntp_api.show_ntp_associations(dut, cli_type="klish")

    # Parse refid field from output
    for entry in output:
        refid = entry.get('refid', '')

        # Validate refid format
        if refid and refid != '.INIT.':
            # Check if refid is in IP format (xxx.xxx.xxx.xxx)
            if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', refid):
                # Check if it's hex format (bug manifestation)
                if re.match(r'^[0-9A-F]{8}$', refid, re.IGNORECASE):
                    st.report_fail("refid_in_hex_format",
                                 f"refid shows hex '{refid}' instead of IP address")

            # Validate IP format
            st.log(f"refid verified in IP format: {refid}")

    st.report_pass("refid_format_validation_passed")
```

---

## Recommendations

### Short-Term (P2 Priority)

1. **Fix the Display Format Bug**:
   - Modify klish CLI backend to convert hex refid to IP address format
   - Follow click mode pattern: show both hex and IP: "D8EF230C (216.239.35.12)"
   - OR show IP only (matching industry standard): "216.239.35.12"

2. **Align with Click Mode Format**:
   - Ensure consistency between klish and click outputs
   - Recommended format: `D8EF230C (216.239.35.12)` (informative)
   - Alternative format: `216.239.35.12` (simple, matches ntpq)

3. **Document Current Behavior** (if fix delayed):
   - Add note in documentation about hex format
   - Provide conversion guide for users
   - Include workaround in troubleshooting guide

### Long-Term

4. **Add Automation Test Coverage**:
   - Implement refid format validation test
   - Add to CI/CD pipeline for regression detection
   - Validate both sync and non-sync states

5. **CLI Output Standardization**:
   - Audit all NTP show commands for format consistency
   - Align with industry-standard NTP tools where possible
   - Ensure klish ↔ click output parity

---

## Test Artifacts

**Test Script**: `/tmp/bug_sm_iscli_p2_121_test.sh`
**Test Log**: `/tmp/bug_sm_iscli_p2_121_test.log`

**Key Test Features**:
- Automated SSH command execution
- 60-second synchronization wait time
- Multi-mode comparison (klish, click, chronyd)
- Hexadecimal and IP address format comparison
- Comprehensive logging with timestamps

---

## Conclusion

**Status**: ✅ **BUG CONFIRMED** - Format inconsistency identified

**Evidence Strength**: **CONCLUSIVE**
- refid IS displayed in klish mode (original claim partially incorrect)
- refid shows HEXADECIMAL format instead of IP address
- click mode shows BOTH hex and IP: "D8EF230C (216.239.35.12)"
- klish mode shows ONLY hex: "D8EF230C"
- Inconsistency confirmed across multiple synchronization checks

**Classification**: CLI Output Format Bug (klish NTP module)

**Corrected Bug Title**: "show ntp associations" refid displays hexadecimal instead of IP address format

**Next Steps**:
1. ✅ Report to Development Team with corrected bug description
2. ⏳ Track Bug Fix in bug tracking system
3. ⏳ Add Automation Test for refid format validation
4. ⏳ Verify Fix with re-test after patch
5. ⏳ Update Documentation with current behavior or fix announcement

---

## Related Bugs

| Bug ID | Relationship |
|--------|--------------|
| **SM_ISCLI_55** | Associations display bug (resolved - table now displays) |
| **SM_ISCLI_P2_28** | chronyd configuration bug (may affect refid data) |
| **TC_NTP_SHOW_003-005** | Show command tests (partial coverage for refid) |

**Pattern Observation**: Multiple NTP display format issues in klish mode suggest potential systematic CLI output formatting problems.

---

**Report Status**: FINAL
**Report Date**: 2026-04-07 16:15
**Report Version**: 1.0
**Prepared By**: Claude Code

---
