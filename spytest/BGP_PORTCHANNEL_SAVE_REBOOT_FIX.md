# BGP PortChannel Save/Reboot Test Fix

## Problem

Test `test_bgp_portchannel_save_reboot` was failing with prompt detection error:
```
Command 'show interface status | grep "Name|PortChannel10 "' failed to give prompt, recovered using CTRL+C
```

## Root Cause Analysis

1. **Error Location**: The error occurred during the framework's "pre-function-prolog" hook that runs after device reboot
2. **Problematic Code**: `apis/system/port.py:49` in function `_get_klish_portmap()`
3. **Issue**: The function used `show interface status | grep "Name|PortChannel10 "` which triggers pagination (`--more--` prompt) after reboot
4. **Pagination Problem**: After reboot, the device shows paginated output, and the framework cannot detect the command prompt because it's waiting at `--more--` instead of the CLI prompt

## Log Evidence

From `results_2025_11_30_23_37_06_dlog-D1-smic_sonic1.log:1246`:
```
2025-11-30 18:19:26,018 T0000: INFO  FCMD: show interface status | grep "Name|PortChannel10 "
...
2025-11-30 18:22:47,782 T0000: WARN  CMP-OUTPUT: --more--
2025-11-30 18:22:47,766 T0000: WARN  OSError: Prompt Not Detected in DF 2.0: '--sonic-mgmt--#'
```

## Solution

Fixed `apis/system/port.py` function `_get_klish_portmap()` (lines 49-54):

**Before:**
```python
command = "show interface status | grep \"Name|{} \"".format(" |".join(portlist))
output = st.show(dut, command, type="klish")
if not output:
    return retval
```

**After:**
```python
# Set terminal length to avoid pagination issues, especially after reboot
st.config(dut, "terminal length 0", type="klish", skip_error_check=True)
command = "show interface status"
output = st.show(dut, command, type="klish", skip_error_check=True)
if not output:
    return retval
```

## Changes Made

1. **Added `terminal length 0`** before the command to disable pagination globally in klish session
2. **Removed grep pipe** - changed from piped command to direct `show interface status`
3. **Added `skip_error_check=True`** for better resilience after reboot
4. **No functional change** - the function already uses `filter_and_select()` to filter output programmatically

## Impact

- **Scope**: Affects all tests that use interface mapping after device reboot
- **Benefit**: Prevents pagination-related prompt detection failures in klish mode
- **Risk**: Very low - `terminal length 0` is a standard practice, and removing grep doesn't change functionality

## Testing

Running test: `test_bgp_portchannel_save_reboot` to verify the fix resolves the issue.

## File Modified

- `apis/system/port.py` - Function `_get_klish_portmap()` (lines 39-54)
