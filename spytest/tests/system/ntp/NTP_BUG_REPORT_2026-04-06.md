# NTP Test Failures - Bug Report
## Date: 2026-04-06
## Test Run: NTP_OC_Run2026-04-06_152726
## Device: 192.168.100.147

---

## EXECUTIVE SUMMARY

Manual CLI testing on device 192.168.100.147 has confirmed **2 CRITICAL BUGS** affecting NTP functionality in SONiC IS-CLI (klish mode). These bugs cause multiple test failures in the NTP test suite.

**Total Test Failures Analyzed**: 10 test cases
**Confirmed Bugs**: 2
**Root Cause**: Device firmware CLI parser issues

---

## BUG #1: NTP SERVER DELETION NOT FUNCTIONAL
### Priority: CRITICAL
### Status: CONFIRMED

### Affected Test Cases
- **test_ntp_030_delete_server** - Primary failure
- test_ntp_041_verify_running_config_display - Cascading failure
- test_ntp_044_complete_setup - Cascading failure
- test_ntp_046_time_drift_correction - Cascading failure

### Description
The `no ntp server <address>` command executes without errors but **DOES NOT actually delete the NTP server** from the configuration. The server remains present in the configuration after the deletion command.

### Root Cause
Device firmware bug in klish CLI parser - the deletion command is accepted but not processed by the backend configuration system.

### Evidence from Manual Testing

#### Test Execution on Device 192.168.100.147
```bash
sonic# show ntp server
---------------------------------------------------------------------------------------------------------------------
NTP Servers                     minpoll maxpoll Prefer Authentication key ID
---------------------------------------------------------------------------------------------------------------------
1.1.1.1                                         False
2.2.2.2                                         False
3.3.3.3                                         False
4.4.4.4                                         False
10.10.10.99                                     False  ← Server to be deleted
10.10.10.251                                    False
172.16.1.1                                      False
192.168.100.175                                 True
enable                                          False
time.google.com                                 False

sonic# configure terminal
sonic(config)# no ntp server 10.10.10.99
sonic(config)# exit

sonic# show ntp server
---------------------------------------------------------------------------------------------------------------------
NTP Servers                     minpoll maxpoll Prefer Authentication key ID
---------------------------------------------------------------------------------------------------------------------
1.1.1.1                                         False
2.2.2.2                                         False
3.3.3.3                                         False
4.4.4.4                                         False
10.10.10.99                                     False  ← STILL PRESENT AFTER DELETION!
10.10.10.251                                    False
172.16.1.1                                      False
192.168.100.175                                 True
enable                                          False
time.google.com                                 False
```

### Reproduction Steps
1. SSH to device: `ssh admin@192.168.100.147` (password: root@123)
2. Enter sonic-cli: `sonic-cli`
3. Check current servers: `show ntp server`
4. Note a server to delete (e.g., 10.10.10.99)
5. Enter config mode: `configure terminal`
6. Delete the server: `no ntp server 10.10.10.99`
7. Exit config mode: `exit`
8. Verify deletion: `show ntp server`
9. **OBSERVED**: Server 10.10.10.99 still appears in the list
10. **EXPECTED**: Server 10.10.10.99 should be removed from the list

### Impact
- **Severity**: HIGH - Cannot remove NTP servers from configuration
- **Workaround**: None identified
- **Scope**: Affects all NTP server deletion operations (both IP addresses and hostnames)

### Test Log Evidence
From `logs/NTP_OC_Run2026-04-06_152726/results_2026_04_06_15_27_29_logs.log`:
```
test_ntp_030_delete_server FAILED
AssertionError: Failed to delete NTP server 192.168.100.175: Server still exists after deletion
```

---

## BUG #2: SOURCE INTERFACE SYNTAX MISMATCH
### Priority: CRITICAL
### Status: CONFIRMED

### Affected Test Cases
- **test_ntp_033_source_interface_ethernet** - Primary failure
- test_ntp_038_verify_source_in_running_config - Cascading failure
- test_ntp_024_server_auth_key - Cascading failure (source config dependency)

### Description
The NTP API sends source interface configuration as `ntp source-interface Ethernet0` (no space), but the device CLI parser **requires a space** between interface type and number: `ntp source-interface Ethernet 0`.

### Root Cause
**API Bug** in `apis/system/ntp.py` line 812:
```python
commands.append('{}ntp source-interface {}'.format(config_string, src_intf))
```

The code receives interface name as "Ethernet0" from the framework and sends it directly to the device without inserting a space. The device CLI parser expects "Ethernet 0" format.

**Incorrect comment in code** (line 811):
```python
# Use interface name directly without splitting (e.g., Ethernet0, not Ethernet 0)
```
This comment is WRONG - the device actually requires "Ethernet 0" with space!

### Evidence from Manual Testing

#### Test Execution on Device 192.168.100.147
```bash
sonic# configure terminal

# ATTEMPT 1: Without space (API sends this format)
sonic(config)# ntp source-interface Ethernet0
                                            ^
% Error: Invalid input detected at "^" marker.

# ATTEMPT 2: With space (correct format)
sonic(config)# ntp source-interface Ethernet 0
sonic(config)# exit

sonic# show ntp global
----------------------------------------------
NTP Global Configuration
----------------------------------------------
NTP service:            disabled
NTP source-interfaces:  Ethernet0  ← Successfully configured!
NTP vrf:                default
NTP authentication:     disabled
```

**Key Finding**: Device accepts "Ethernet 0" (with space) and displays it as "Ethernet0" in output.

### Reproduction Steps
1. SSH to device: `ssh admin@192.168.100.147` (password: root@123)
2. Enter sonic-cli: `sonic-cli`
3. Enter config mode: `configure terminal`
4. Try API format (no space): `ntp source-interface Ethernet0`
5. **OBSERVED**: Error: "Invalid input detected at '^' marker"
6. **EXPECTED**: Command should be accepted
7. Try correct format: `ntp source-interface Ethernet 0`
8. **OBSERVED**: Command accepted successfully
9. Exit and verify: `exit` then `show ntp global`
10. **OBSERVED**: Shows "NTP source-interfaces: Ethernet0"

### Impact
- **Severity**: HIGH - Cannot configure source interface for NTP
- **Workaround**: Modify API code to insert space between interface type and number
- **Scope**: Affects all Ethernet interface configurations (Ethernet0-N)

### Test Log Evidence
From `logs/NTP_OC_Run2026-04-06_152726/results_2026_04_06_15_27_29_logs.log`:
```
2026-04-06 10:17:38,707 T0000: INFO  [D1-smic_sonic1] FCMD: ntp source-interface Ethernet0
2026-04-06 10:17:38,971 T0000: INFO  [D1-smic_sonic1] % Error: Invalid input detected at "^" marker.

test_ntp_033_source_interface_ethernet FAILED
AssertionError: Failed to configure source interface Ethernet0: Invalid input
```

### Proposed Fix
Modify `apis/system/ntp.py` line 812 to insert space for Ethernet interfaces:

**Before:**
```python
commands.append('{}ntp source-interface {}'.format(config_string, src_intf))
```

**After:**
```python
# Insert space between interface type and number for klish CLI
# e.g., "Ethernet0" → "Ethernet 0"
if src_intf.startswith('Ethernet') and src_intf[8:].isdigit():
    intf_formatted = src_intf[:8] + ' ' + src_intf[8:]
else:
    intf_formatted = src_intf
commands.append('{}ntp source-interface {}'.format(config_string, intf_formatted))
```

---

## OTHER TEST FAILURES - INVESTIGATION NEEDED

### test_ntp_014_config_multiple_trusted_keys
**Status**: Requires further investigation
**Initial Testing**: Manual test shows `ntp trusted-key 15` command is **ACCEPTED** without error
**Possible Cause**: Test logic issue or verification method problem, not a device bug

### test_ntp_016_trusted_key_max_id
**Status**: Requires further investigation
**Failure**: Max key ID 65535 configuration failed
**Possible Cause**: Device may have lower max key ID limit than expected by test

### test_ntp_036_source_interface_svi
**Status**: Requires further investigation
**Failure**: VLAN creation failed
**Possible Cause**: Pre-requisite configuration issue, not NTP-specific

---

## PRIORITY RECOMMENDATIONS

### Immediate Actions Required

1. **Fix BUG #2 (Source Interface Syntax)** in `apis/system/ntp.py`
   - **Priority**: CRITICAL
   - **Effort**: LOW (simple code change)
   - **Impact**: Will fix 3+ test failures immediately
   - **Action**: Modify line 812 to insert space for Ethernet interfaces

2. **Report BUG #1 (Server Deletion)** to device firmware team
   - **Priority**: CRITICAL
   - **Effort**: N/A (firmware bug)
   - **Impact**: Requires firmware fix
   - **Workaround**: None available

### Follow-up Actions

3. **Re-run NTP test suite** after applying BUG #2 fix
   - Verify if cascading failures are resolved
   - Identify any remaining true bugs vs test issues

4. **Investigate authentication key failures** (test_ntp_014, test_ntp_016)
   - Manual testing shows basic auth key commands work
   - May be test logic issues rather than device bugs

---

## TEST ENVIRONMENT

**Device**: 192.168.100.147
**Access**: ssh admin@192.168.100.147 (password: root@123)
**CLI Mode**: sonic-cli (klish)
**Test Run**: logs/NTP_OC_Run2026-04-06_152726/results_2026_04_06_15_27_29_logs.log
**Framework**: SPyTest
**Date**: 2026-04-06

---

## APPENDIX: COMPLETE TEST FAILURE LIST

| Test Case ID | Test Name | Status | Root Cause |
|--------------|-----------|--------|------------|
| test_ntp_030 | delete_server | FAILED | BUG #1: Server deletion not functional |
| test_ntp_033 | source_interface_ethernet | FAILED | BUG #2: Source interface syntax mismatch |
| test_ntp_038 | verify_source_in_running_config | FAILED | BUG #2: Cascading from source interface |
| test_ntp_024 | server_auth_key | FAILED | BUG #2: Cascading from source interface |
| test_ntp_041 | verify_running_config_display | FAILED | BUG #1: Cascading from server deletion |
| test_ntp_044 | complete_setup | FAILED | BUG #1/#2: Cascading failures |
| test_ntp_046 | time_drift_correction | FAILED | BUG #1: Cascading from server deletion |
| test_ntp_014 | config_multiple_trusted_keys | FAILED | Needs investigation |
| test_ntp_016 | trusted_key_max_id | FAILED | Needs investigation |
| test_ntp_036 | source_interface_svi | FAILED | Needs investigation |

---

## VERIFICATION COMMANDS

### Check NTP Servers
```bash
sonic-cli
show ntp server
exit
```

### Check NTP Global Configuration
```bash
sonic-cli
show ntp global
exit
```

### Test Server Deletion (Bug #1)
```bash
sonic-cli
configure terminal
no ntp server <server_address>
exit
show ntp server
# Verify server is removed (currently FAILS)
exit
```

### Test Source Interface Configuration (Bug #2)
```bash
sonic-cli
configure terminal
ntp source-interface Ethernet0    # FAILS - Invalid input
ntp source-interface Ethernet 0   # WORKS - Space required
exit
show ntp global
# Verify source interface is set
exit
```

---

**Report Prepared By**: Automated Testing & Manual Verification
**Report Date**: 2026-04-06
**Next Review**: After BUG #2 fix is applied and tests are re-run
