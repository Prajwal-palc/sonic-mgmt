# NTP Bug Test Script Fixes Required

**Date**: 2026-04-07
**File**: `test_ntp_iscli_bugs.py`
**Log**: `logs/ntp_iscli_bugs_20260407_193321/results_2026_04_07_19_33_22_logs.log`

## Summary of Issues

1. **NTP server parsing failing** - API returns data but parsing gets 0 results
2. **Show commands run in config mode** - Missing 'exit' before show commands in some tests
3. **test_ntp_p2_24 - Remove unsupported CLIs** - Only test `ntp server enable`
4. **Ethernet0 → Ethernet 0** - Change syntax (with space) throughout
5. **AttributeError: 'vars' not found** - test_ntp_sm_iscli_p2_1 accessing wrong attribute
6. **test_ntp_p2_28 running show in config mode** - Missing exit before show commands

## Fixes Applied

### Fix 1: test_ntp_p2_26_server_deletion_failure (Lines 205-259)
**Issue**: Parsed 0 NTP servers even though they're visible
**Fix Applied**:
- Added `st.config(dut, "exit"` before `show_ntp_server()`
- Enhanced parsing to handle both "remote" and "ntpserver" keys
- Added debugging logs to show parsed server count

### Fix 2: test_ntp_p2_24_server_mode_missing - NEEDS SIMPLIFICATION
**Current Issue**: Tests multiple unsupported commands
**Required Fix**: Only test `ntp server enable` command
**Location**: Lines 255-331

```python
def test_ntp_p2_24_server_mode_missing(self) -> None:
    """BUG SM_ISCLI_P2_24: Verify NTP server mode is not supported."""
    st.banner("TEST: BUG SM_ISCLI_P2_24 - NTP Server Mode Not Supported")

    dut = self.data.dut
    cli_type = self.data.cli_type

    # STEP 1: Test 'ntp server enable' command (only supported command)
    st.log("STEP 1: Test 'ntp server enable' command availability")
    cmd = "ntp server enable"

    try:
        result = st.config(dut, cmd, type=cli_type, skip_error_check=True, max_time=30)

        if "error" in str(result).lower() or "invalid" in str(result).lower():
            st.log("BUG CONFIRMED: 'ntp server enable' command not supported")
            st.log("SONiC does not support NTP server mode")
            st.report_pass("test_case_passed")  # Bug reproduced as expected
        else:
            st.log("Command 'ntp server enable' appears to work")
            st.log("Bug may be fixed or feature implemented")
            st.report_fail("msg", "ntp server enable command unexpectedly worked")

    except Exception as e:
        st.log(f"Command execution error: {e}")
        st.log("BUG CONFIRMED: NTP server mode feature not available")
        st.report_pass("test_case_passed")
```

### Fix 3: test_ntp_p2_28_chronyd_config_generation - MISSING EXIT BEFORE SHOW
**Issue**: Running show commands from config mode
**Location**: Lines 610-650

**Need to add before line 621**:
```python
# Exit config mode before running show command
st.config(dut, "exit", type=cli_type, skip_error_check=True)
chronyd_status = st.show(dut, "sudo systemctl status chronyd", skip_error_check=True)
```

**Need to add before line 640**:
```python
# Exit config mode before running show command
st.config(dut, "exit", type=cli_type, skip_error_check=True)
associations = st.show(dut, "show ntp associations", type=cli_type, skip_error_check=True)
```

### Fix 4: Change Ethernet0 → Ethernet 0 (with space)
**Issue**: Klish mode requires space in interface names
**Locations to fix**:
- test_ntp_p2_135_client_synchronization - Uses test interface from YAML
- test_ntp_sm_iscli_p2_1_source_interface_limitations - Line 810+

**For test_ntp_sm_iscli_p2_1**:
Change line ~810:
```python
test_config = SpyTestDict(testcase)  # Don't use self.vars - use self.data
```

### Fix 5: test_ntp_sm_iscli_p2_1 AttributeError
**Issue**: `AttributeError 'TestNTPISCLIBugs' object has no attribute 'vars'`
**Location**: Line 810

**Current code (WRONG)**:
```python
test_config = SpyTestDict(testcase)
```

**Fixed code (CORRECT)**:
```python
# Access data through self.data, not self.vars
dut = self.data.dut
cli_type = self.data.cli_type
testcase = self.data.testcases.get("sm_iscli_p2_1", {})
test_config = SpyTestDict(testcase)
```

### Fix 6: Add test for Ethernet interface syntax (both Ethernet0 and Ethernet 0)
**New test needed** to verify BOTH syntaxes work:

```python
@pytest.mark.bug_interface_syntax
def test_ntp_ethernet_interface_syntax(self) -> None:
    """Verify both Ethernet0 and 'Ethernet 0' syntax work for NTP source-interface.

    Expected: Both syntaxes should be accepted (currently only 'Ethernet 0' works)
    This is a bug if Ethernet0 (no space) is rejected.
    """
    st.banner("TEST: NTP Source-Interface Ethernet Syntax Validation")

    dut = self.data.dut
    cli_type = self.data.cli_type

    # Test 1: Ethernet0 (no space) - Currently FAILS due to bug
    st.log("Test 1: Trying 'ntp source-interface Ethernet0' (no space)")
    result1 = st.config(dut, "ntp source-interface Ethernet0",
                        type=cli_type, skip_error_check=True)

    syntax_no_space_works = "error" not in str(result1).lower()

    # Cleanup
    st.config(dut, "no ntp source-interface", type=cli_type, skip_error_check=True)

    # Test 2: Ethernet 0 (with space) - Currently WORKS
    st.log("Test 2: Trying 'ntp source-interface Ethernet 0' (with space)")
    result2 = st.config(dut, "ntp source-interface Ethernet 0",
                        type=cli_type, skip_error_check=True)

    syntax_with_space_works = "error" not in str(result2).lower()

    # Report results
    if syntax_no_space_works and syntax_with_space_works:
        st.log("PASS: Both syntaxes work (bug fixed)")
        st.report_pass("test_case_passed")
    elif not syntax_no_space_works and syntax_with_space_works:
        st.error("BUG: Ethernet0 (no space) rejected, only 'Ethernet 0' works")
        st.report_fail("msg", "Ethernet interface syntax inconsistent")
    else:
        st.error("UNEXPECTED: Neither syntax works")
        st.report_fail("msg", "Both Ethernet syntaxes rejected")
```

## Additional Fixes for test_ntp_p2_28

**Line 611** - Currently runs `sudo systemctl status chronyd` via st.config:
```python
# WRONG:
chronyd_status = st.config(dut, "sudo systemctl status chronyd", skip_error_check=True)

# CORRECT:
st.config(dut, "exit", type=cli_type, skip_error_check=True)
chronyd_status = basic_api.service_operations(dut, "chronyd", "status", skip_error_check=True)
```

**Line 621** - Currently runs `sudo chronyc sources` via st.config:
```python
# WRONG:
chronyd_sources = st.config(dut, "sudo chronyc sources", skip_error_check=True)

# CORRECT:
# Already in exec mode from previous exit
cmd = "sudo chronyc sources"
chronyd_sources = st.show(dut, cmd, skip_tmpl=True, skip_error_check=True)
```

## Files Modified

1. `test_ntp_iscli_bugs.py` - Main test file with all bug validation tests
2. THIS FILE (`FIXES_REQUIRED.md`) - Documentation of required fixes

## Testing Status

- ✅ test_ntp_p2_26 - FIXED (exit before show, enhanced parsing)
- ✅ test_ntp_p2_24 - FIXED (simplified to only test `ntp server enable`)
- ✅ test_ntp_p2_28 - FIXED (exit before show commands at lines 640, 650)
- ✅ test_ntp_sm_iscli_p2_1 - FIXED (AttributeError - changed self.vars.D1 to self.data.dut)
- ⏳ test_ntp_ethernet_syntax - NEEDS ADDITION (new test)

## Priority

**HIGH PRIORITY** - ✅ ALL COMPLETED:
1. ✅ Fix test_ntp_p2_24 - Simplified to only test `ntp server enable` (Lines 303-309)
2. ✅ Fix test_ntp_sm_iscli_p2_1 - Fixed AttributeError (Lines 853-857)
3. ✅ Fix test_ntp_p2_28 - Added exit before show commands (Lines 640-642, 652-653)

**MEDIUM PRIORITY**:
4. ⏳ Add test_ntp_ethernet_syntax - Verify both syntaxes work (Pending)

## Notes

- All show commands MUST be run from exec mode, not config mode
- Use `exit` command (not `end`) to exit config mode in this build
- NTP API parsing needs to handle both "remote" and "ntpserver" dictionary keys
- Ethernet interface names require space in klish mode: "Ethernet 0" not "Ethernet0"
