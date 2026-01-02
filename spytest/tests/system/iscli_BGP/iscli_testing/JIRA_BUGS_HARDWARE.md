# JIRA Bug Reports - Hardware Testing Results

**Test Date:** 2025-12-31
**Platform:** Supermicro SSE-T8164 (x86_64-supermicro_sse_t8164-r0)
**Test Device:** HW 8011 (192.168.100.202)

---

## BUG #1: Missing platform_components.json File

**Priority:** HIGH
**Component:** Platform/Firmware Management
**Affects Version:** Current

### Description:
The platform_components.json configuration file is missing for Supermicro SSE-T8164 platform, preventing all firmware management features from working.

### Steps to Reproduce:
```bash
admin@sonic:~$ show platform firmware updates
```

### Expected Result:
Display list of available firmware updates for platform components (CPLD, BIOS, FPGA, etc.)

### Actual Result:
```
Error: [Errno 2] No such file or directory:
'/usr/share/sonic/device/x86_64-supermicro_sse_t8164-r0/platform_components.json'
Aborted!
```

### Impact:
- **HIGH:** Complete loss of firmware management functionality
- Cannot view firmware component status
- Cannot check for firmware updates
- Cannot perform firmware update operations
- Reduces platform maintainability

### Environment:
- Platform: x86_64-supermicro_sse_t8164-r0
- ASIC: Broadcom BCM78900 (Tomahawk5)
- Model: SSE-T8164S

### Affected Commands:
```bash
show platform firmware status      # Returns empty table
show platform firmware updates     # ERROR: File not found
show platform firmware update-all-status  # Likely fails
```

### Root Cause:
Missing platform configuration file at:
`/usr/share/sonic/device/x86_64-supermicro_sse_t8164-r0/platform_components.json`

### Suggested Fix:
1. Create platform_components.json file for Supermicro SSE-T8164
2. Define firmware components with proper attributes:
   - Component names (CPLD, BIOS, FPGA, etc.)
   - Current versions
   - Update procedures
   - Version check methods

### Example Platform Components Structure:
```json
{
    "chassis": {
        "Chassis1": {
            "component": {
                "BIOS": {
                    "firmware": "/usr/share/sonic/device/platform/fw_bios.bin",
                    "version": "get_bios_version_cmd",
                    "info": "Platform BIOS"
                },
                "CPLD": {
                    "firmware": "/usr/share/sonic/device/platform/fw_cpld.vme",
                    "version": "get_cpld_version_cmd",
                    "info": "Platform CPLD"
                }
            }
        }
    }
}
```

### Workaround:
None available - firmware management features are completely unavailable

### Business Impact:
- Cannot manage firmware updates through standard SONiC CLI
- Requires manual firmware update procedures
- Reduces operational efficiency
- May impact compliance/security (cannot track firmware versions)

---

## BUG #2: Firmware Status Returns Empty

**Priority:** MEDIUM
**Component:** Platform/Firmware Management
**Affects Version:** Current

### Description:
The `show platform firmware status` command returns an empty table with no firmware components listed.

### Steps to Reproduce:
```bash
admin@sonic:~$ show platform firmware status
```

### Expected Result:
Display table with firmware components and their current versions:
```
Chassis    Module    Component    Version      Description
---------  --------  -----------  -----------  -------------
Chassis1   N/A       BIOS         1.2.3        Platform BIOS
Chassis1   N/A       CPLD         4.5.6        Platform CPLD
...
```

### Actual Result:
```
Chassis    Module    Component    Version    Description
---------  --------  -----------  ---------  -------------
(empty - no rows)
```

### Impact:
- **MEDIUM:** Cannot view firmware component versions
- Cannot verify firmware is up to date
- Reduces visibility into platform state
- May be related to BUG #1 (missing platform_components.json)

### Environment:
- Platform: x86_64-supermicro_sse_t8164-r0
- Model: SSE-T8164S

### Root Cause:
Likely caused by missing platform_components.json file (BUG #1)

### Suggested Fix:
Fix BUG #1 first, then verify this issue is resolved

### Workaround:
None - cannot view firmware versions through CLI

### Business Impact:
- Reduced visibility into platform firmware state
- Cannot verify firmware versions without manual inspection
- May impact troubleshooting and support

---

## BUG #3: Current and Voltage Sensors Not Detected

**Priority:** LOW
**Component:** Platform/Environmental Monitoring
**Affects Version:** Current
**Type:** Investigation Needed

### Description:
Current and voltage sensor monitoring commands report "Sensor not detected" on Supermicro SSE-T8164 platform.

### Steps to Reproduce:
```bash
admin@sonic:~$ show platform current
admin@sonic:~$ show platform voltage
```

### Expected Result:
Display current/voltage sensor readings (if hardware supports)

### Actual Result:
```
Sensor not detected
```

### Impact:
- **LOW:** Cannot monitor current/voltage sensors
- May be hardware limitation rather than software bug
- Other environmental monitoring (fan, temperature) works fine

### Environment:
- Platform: x86_64-supermicro_sse_t8164-r0
- Model: SSE-T8164S

### Investigation Needed:
1. **Verify Hardware Capability:**
   - Check Supermicro SSE-T8164 hardware specifications
   - Determine if platform has current/voltage sensors
   - Review hardware documentation

2. **Check Platform Driver:**
   - Verify platform driver implementation
   - Check if sensors are supported but not configured
   - Review driver logs for sensor detection

### Working Environmental Sensors:
- ✅ Fan monitoring (10 fans detected)
- ✅ Temperature monitoring (11 sensors detected)
- ❌ Current monitoring (not detected)
- ❌ Voltage monitoring (not detected)

### Possible Causes:
1. **Hardware Limitation:** Platform may not have these sensors
2. **Driver Issue:** Sensors exist but driver doesn't support them
3. **Configuration:** Sensors exist but not configured in platform files

### Suggested Actions:
1. Verify hardware capability with vendor documentation
2. If sensors exist: Fix platform driver/configuration
3. If sensors don't exist: Update documentation to reflect limitation

### Workaround:
None if hardware doesn't support these sensors

### Business Impact:
- **LOW:** If hardware limitation, no impact
- Other environmental monitoring works fine
- PSU monitoring shows voltage/current for PSUs

---

## ISSUE #4: SSD Health - Nonexistent Device Handling

**Priority:** LOW
**Component:** Platform/SSD Monitoring
**Type:** Enhancement

### Description:
When checking SSD health for a nonexistent device, the command returns "N/A" values instead of a clear error message.

### Steps to Reproduce:
```bash
admin@sonic:~$ show platform ssdhealth /dev/nonexistent
```

### Expected Result:
Clear error message indicating device not found

### Actual Result:
```
Disk Type    : SATA
Device Model : N/A
Health       : N/A
Temperature  : N/A
```

### Impact:
- **LOW:** Unclear error handling
- Current behavior is acceptable (shows N/A)
- Not a critical issue

### Suggested Enhancement:
Return clear error message for nonexistent devices:
```
Error: Device '/dev/nonexistent' not found
```

### Business Impact:
- **VERY LOW:** Current behavior is acceptable
- Enhancement for better user experience

---

## GOOD NEWS: NO BUGS FOUND ✅

### Originally Expected to Fail (BUT WORK!):

**ISSUE: CLI Flags Not Supported**
**Status:** ❌ **NOT A BUG** - ALL FLAGS WORK PERFECTLY! ✅

### Description:
Initially expected --json, --verbose, and other CLI flags to not work in platform commands.

### Actual Result:
**ALL FLAGS WORK PERFECTLY!** ✅

### Validated Working Commands:
```bash
show platform summary --json                          ✅ WORKS
show platform syseeprom --verbose                     ✅ WORKS
show platform psustatus --json                        ✅ WORKS
show platform psustatus --verbose                     ✅ WORKS
show platform psustatus -i 1 --json --verbose         ✅ WORKS
show platform pcieinfo --check --verbose              ✅ WORKS
show platform summary --help                          ✅ WORKS
show platform syseeprom --help                        ✅ WORKS
```

### Impact:
- ✅ **POSITIVE:** Platform commands fully support CLI flags
- ✅ No bug to fix - working as expected
- ✅ Better user experience than anticipated

---

## Summary for JIRA Tickets

### Bugs to Create:

1. **BUG-001:** Missing platform_components.json (HIGH)
2. **BUG-002:** Firmware status returns empty (MEDIUM)
3. **BUG-003:** Current/voltage sensors not detected (LOW - Investigation)
4. **ENHANCEMENT-001:** SSD health error handling (LOW - Optional)

### Total Bugs: 3
### Priority Breakdown:
- HIGH: 1
- MEDIUM: 1
- LOW: 1 (investigation needed)

### Test Coverage: 80% Pass Rate
- Total Commands Tested: 30
- Passed: 24
- Failed: 6

### Overall Assessment:
✅ **GOOD** - Platform commands work well on hardware. Main issue is missing firmware configuration file.

---

## Effort Estimates

### BUG #1: Missing platform_components.json
**Estimated Effort:** 3-5 days
- Research platform firmware components
- Create JSON configuration file
- Test firmware status/updates commands
- Validation testing

### BUG #2: Firmware Status Empty
**Estimated Effort:** 1 day (after BUG #1 fixed)
- Verify resolution after BUG #1 fix
- Test firmware status display

### BUG #3: Current/Voltage Sensors
**Estimated Effort:** 2-3 days (if software issue)
- Hardware capability verification: 0.5 day
- Driver implementation (if needed): 2 days
- Testing: 0.5 day

**Total Estimated Effort:** 6-9 days

---

## Recommendations

1. **Fix BUG #1 first** (HIGH priority) - Blocks firmware management
2. **Investigate BUG #3** - Determine if hardware or software issue
3. **Update documentation** - Reflect that CLI flags DO WORK
4. **Update test expectations** - Based on actual hardware behavior

**Most platform features work correctly - good foundation! 🎉**
