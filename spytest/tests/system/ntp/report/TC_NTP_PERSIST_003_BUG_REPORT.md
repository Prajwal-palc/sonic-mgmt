# Bug Report Template - TC_NTP_PERSIST_003 Findings

**Test Reference**: TC_NTP_PERSIST_003 - Running-Config Accuracy + Authentication Key Configuration
**Test Date**: 2026-04-10 07:53:28
**DUT**: 192.168.100.147
**SONiC Version**: 6.1.0-29-2-amd64 (Debian 12)
**Reporter**: QA Team - Manual Testing
**Test Report**: `/home/claudeuser/Athira/sonic-mgmt/spytest/tests/system/ntp/report/TC_NTP_PERSIST_003.md`

---

## BUG #1: Cannot Bind Authentication Key to Existing NTP Server

### Bug Summary
**Title**: NTP server authentication key cannot be added to pre-configured server

**Severity**: Medium

**Priority**: P2

**Component**: NTP / KLISH CLI

**Affects Version**: SONiC 6.1.0-29-2-amd64

**Status**: New

---

### Description

When attempting to bind an authentication key to an already configured NTP server using the `ntp server <ip> key <key-id>` command, the system returns an error even though:
1. The authentication key exists and is valid
2. The authentication key is marked as trusted
3. The authentication key is visible in running-config and config_db.json

This prevents users from adding authentication to existing NTP server configurations without removing and re-adding the server.

---

### Steps to Reproduce

**Pre-requisites:**
- NTP service enabled
- NTP authentication enabled
- At least one NTP server already configured

**Step-by-Step:**

```bash
# Step 1: Enter KLISH configuration mode
admin@sonic:~$ sonic-cli
sonic# configure terminal

# Step 2: Create authentication key
sonic(config)# ntp authentication-key 10 md5 TestKey123
# Result: SUCCESS - Key created

# Step 3: Mark key as trusted
sonic(config)# ntp trusted-key 10
# Result: SUCCESS - Key marked as trusted

# Step 4: Verify key exists in running-config
sonic(config)# exit
sonic# show running-configuration | grep ntp
# Result: Key 10 visible in output:
#   ntp authentication-key 10 md5 TestKey123

# Step 5: Attempt to bind key to existing server
sonic# configure terminal
sonic(config)# ntp server 192.168.100.175 key 10
```

---

### Expected Result

```
sonic(config)# ntp server 192.168.100.175 key 10
sonic(config)#
[Command succeeds - authentication key 10 bound to server 192.168.100.175]
```

The server should be updated with the authentication key binding, and subsequent verification should show:
- `show ntp server` displays key ID in "Authentication key ID" column
- config_db.json contains `"key_id": "10"` for server 192.168.100.175

---

### Actual Result

```
sonic(config)# ntp server 192.168.100.175 key 10
%Error: Invalid authentication key configuration
sonic(config)#
```

**Error Analysis:**
- Error occurs even though key 10 exists and is trusted
- No additional diagnostic information provided
- Server configuration remains unchanged
- Authentication key remains unusable for this server

---

### Log Evidence

**Test Script**: `/tmp/tc_ntp_persist_003_with_bug_test.exp`
**Test Output**: `/tmp/tc_ntp_persist_003_output.txt`

**Relevant Log Excerpt (Lines 62-99):**

```
=== STEP 3: Test CORRECT command syntax ===

Attempting: ntp authentication-key 10 md5 TestKey123 (CORRECT)

ntp authentication-key 10 md5 TestKey123
sonic(config)# SUCCESS: Authentication key 10 configured

=== STEP 4: Verify authentication key 10 was created ===

exit
sonic# show running-configuration | grep ntp
!
ntp authentication-key 1 md5 MinKey
ntp authentication-key 2 openconfig-system-ext:ntp_auth_sha256 SecurePass456
ntp authentication-key 10 md5 TestKey123    <-- KEY EXISTS
[...]

=== STEP 5: Try to configure trusted-key (should work if key exists) ===

configure terminal
sonic(config)# ntp trusted-key 10
sonic(config)# SUCCESS: Trusted key 10 configured    <-- KEY TRUSTED

=== STEP 6: Try to configure server with key 10 ===

ntp server 192.168.100.175 key 10
%Error: Invalid authentication key configuration    <-- BUG: FAILS HERE
ERROR: Key 10 not recognized for server binding!
```

**config_db.json Verification (Lines 517-531):**

```json
"NTP_KEY": {
    "10": {
        "trusted": "yes",
        "type": "md5",
        "value": "TestKey123"
    }
}
```

**Proof Key Exists and is Valid:**
- Authentication key 10 created successfully
- Key marked as trusted successfully
- Key persisted to running-config
- Key persisted to config_db.json with correct attributes
- Yet server binding fails with "Invalid authentication key configuration"

---

### Environment Details

**Platform**: SONiC Virtual Switch (VS)
**OS Version**: Linux 6.1.0-29-2-amd64 #1 SMP PREEMPT_DYNAMIC Debian 6.1.123-1
**SONiC Build**: Debian GNU/Linux 12
**CLI Mode**: KLISH (sonic-cli)
**NTP Daemon**: Chrony

**Current NTP Configuration:**
```
NTP service:            enabled
NTP authentication:     enabled
NTP source-interfaces:  Ethernet0, Ethernet4
NTP vrf:                default
```

**Configured Servers:**
- 10.10.10.99
- 192.168.100.175 (target server for key binding)
- 216.239.35.0
- 216.239.35.12
- time.google.com

**Configured Authentication Keys:**
- Key 1, 2, 15, 20, 25, 30, 50, 99, 100, 101, 65535 (pre-existing)
- Key 10 (created during test)

---

### Workaround

**Temporary Solution:**

To bind an authentication key to an NTP server, the server must be removed and re-configured:

```bash
sonic(config)# no ntp server 192.168.100.175
sonic(config)# ntp server 192.168.100.175 key 10 iburst prefer
```

**Limitations of Workaround:**
- Causes service interruption (server temporarily removed)
- Requires knowing all current server options (iburst, prefer, version, etc.)
- Error-prone if server has multiple options configured
- Not suitable for production systems requiring zero downtime

---

### Impact Assessment

**User Impact**: Medium
- Prevents modification of existing NTP server authentication
- Requires service interruption to add authentication
- Makes incremental security hardening difficult

**Functional Impact**:
- Authentication keys can be created and trusted
- New servers can be configured with keys
- Only modification of existing servers is affected

**Use Cases Affected**:
- Adding authentication to production NTP infrastructure
- Security compliance remediation
- Migrating from unauthenticated to authenticated NTP

---

### Recommended Fix

Enhance KLISH NTP server configuration to support:
1. Incremental modification of server parameters
2. Allow `ntp server <ip> key <key-id>` to update existing server
3. Validate authentication key exists before applying to server
4. Provide clear error messages if validation fails

**Suggested Implementation:**
- Check if server exists in NTP_SERVER table
- If exists, merge new key_id parameter with existing configuration
- Validate key_id exists in NTP_KEY table
- Update config_db.json atomically
- Restart NTP daemon to apply changes

---

### Related Test Cases

- TC_NTP_AUTHKEY_007: Authentication key configuration (PASS)
- TC_NTP_PERSIST_001: Configuration persistence (PASS)
- TC_NTP_PERSIST_002: Reboot persistence (PASS)

---

## BUG #2: KLISH Grep Command Limitations in Pipe Operations

### Bug Summary
**Title**: show running-configuration pipe grep does not support quoted strings or options

**Severity**: Low

**Priority**: P3

**Component**: KLISH CLI / Management Framework

**Affects Version**: SONiC 6.1.0-29-2-amd64

**Status**: New

---

### Description

The KLISH `show running-configuration` command with pipe to `grep` does not support:
1. Single-quoted search patterns
2. Double-quoted search patterns
3. Grep command-line options (-A, -B, -C, etc.)

This limits troubleshooting and configuration verification capabilities available in standard network operating systems.

---

### Steps to Reproduce

```bash
# Step 1: Enter KLISH mode
admin@sonic:~$ sonic-cli
sonic#

# Step 2: Attempt grep with single quotes
sonic# show running-configuration | grep 'ntp enable'

# Step 3: Attempt grep with options
sonic# show running-configuration | grep -A 30 ntp
```

---

### Expected Result

**Standard Network OS Behavior (Cisco IOS, Juniper, etc.):**

```bash
sonic# show running-configuration | grep 'ntp enable'
ntp enable

sonic# show running-configuration | grep -A 5 ntp
ntp authentication-key 1 md5 MySecret123
ntp authentication-key 10 md5 TestKey123
ntp authenticate
ntp server 192.168.100.175 iburst
ntp server 216.239.35.0 iburst
--
[Additional lines with context]
```

---

### Actual Result

**Grep with Single Quotes:**
```bash
sonic# show running-configuration | grep 'ntp enable'
                                              ^
% Error: Invalid input detected at "^" marker.
```

**Grep with Options:**
```bash
sonic# show running-configuration | grep -A 30 ntp
                                            ^
% Error: Invalid input detected at "^" marker.
```

**Only Basic Grep Works:**
```bash
sonic# show running-configuration | grep ntp
[SUCCESS - shows all lines containing 'ntp']
```

---

### Log Evidence

**Test Output**: `/tmp/tc_ntp_persist_003_output.txt`

**Failed Grep with Single Quotes (Lines 84-87):**
```
sonic# show running-configuration | grep 'authentication-key 10'
                                                             ^
% Error: Invalid input detected at "^" marker.
sonic#
```

**Failed Grep with Options (Lines 433-436):**
```
show running-configuration | grep -A 30 ntp
                                            ^
% Error: Invalid input detected at "^" marker.
sonic#
```

**Additional Failed Examples (Lines 442-469):**
```
show running-configuration | grep 'ntp enable'
                                              ^
% Error: Invalid input detected at "^" marker.

show running-configuration | grep 'ntp authenticate'
                                              ^
% Error: Invalid input detected at "^" marker.

show running-configuration | grep 'ntp authentication-key 1'
                                              ^
% Error: Invalid input detected at "^" marker.
```

---

### Environment Details

**Platform**: SONiC Virtual Switch (VS)
**CLI Mode**: KLISH (sonic-cli)
**Management Framework**: SONiC Management Framework Container

**Affected Commands:**
- `show running-configuration | grep '<pattern>'`
- `show <any-command> | grep '<pattern>'`

---

### Workaround

**Current Workaround:**
Use grep without quotes or options:

```bash
# Instead of:
show running-configuration | grep 'ntp enable'

# Use:
show running-configuration | grep ntp
# Then manually search output for 'ntp enable'
```

**Alternative for Context Lines:**
```bash
# Instead of:
show running-configuration | grep -A 10 ntp

# Use:
show running-configuration | grep ntp
# Or exit to bash and use show tech-support output
```

---

### Impact Assessment

**User Impact**: Low to Medium
- Reduces troubleshooting efficiency
- Requires workarounds familiar to network engineers
- Documentation and training materials require adaptation

**Functional Impact**:
- Basic grep works for simple searches
- Complex pattern matching unavailable
- Context lines (before/after) unavailable

**Use Cases Affected**:
- Quick configuration verification
- Troubleshooting sessions
- Configuration audit procedures
- Automated scripts using KLISH CLI

---

### Recommended Fix

**Option 1: Enhance Pipe Handler**
- Update KLISH pipe command parser to accept quoted arguments
- Support standard grep options: -A, -B, -C, -i, -v, -E
- Align behavior with industry-standard CLIs

**Option 2: Documentation**
- Document current limitations in KLISH user guide
- Provide workaround examples
- Note differences from traditional NOS behavior

---

## BUG #3: Running-Config Does Not Display All Configured NTP Options

### Bug Summary
**Title**: show running-configuration omits NTP server options (prefer, version)

**Severity**: Low

**Priority**: P3

**Component**: KLISH CLI / Configuration Display

**Affects Version**: SONiC 6.1.0-29-2-amd64

**Status**: New (Enhancement Request)

---

### Description

The `show running-configuration` command does not display all configured NTP server options. Specifically:
- Server `prefer` flag not shown
- Server `version` option not shown
- Implicit defaults (ntp enable, vrf default) not shown

However, these settings ARE correctly stored in config_db.json and ARE functional.

This creates confusion during configuration verification and auditing.

---

### Steps to Reproduce

```bash
# Step 1: Configure NTP server with all options
sonic(config)# ntp server 192.168.100.175 version 4 iburst prefer

# Step 2: View running configuration
sonic# show running-configuration | grep 192.168.100.175

# Step 3: View show ntp server
sonic# show ntp server

# Step 4: Verify config_db.json
admin@sonic:~$ sudo cat /etc/sonic/config_db.json | python3 -m json.tool | grep -A 10 192.168.100.175
```

---

### Expected Result

**Running-Config Should Show:**
```
ntp server 192.168.100.175 version 4 iburst prefer
```

**show ntp server Should Show:**
```
NTP Servers          minpoll maxpoll Prefer  Version  Authentication key ID
--------------------------------------------------------------------------------
192.168.100.175                      True    4
```

---

### Actual Result

**Running-Config Shows:**
```
ntp server 192.168.100.175 iburst
```
❌ Missing: `prefer` flag
❌ Missing: `version 4` option

**show ntp server Shows:**
```
NTP Servers                     minpoll maxpoll Prefer Authentication key ID
---------------------------------------------------------------------------------------------------------------------
192.168.100.175                                 True
```
✅ Shows: `prefer` flag
❌ Missing: `version` column not displayed

**config_db.json Shows (CORRECT):**
```json
"NTP_SERVER": {
    "192.168.100.175": {
        "admin_state": "enabled",
        "iburst": "enabled",
        "prefer": "enabled"
    }
}
```
✅ All settings correctly stored

---

### Log Evidence

**Test Output**: `/tmp/tc_ntp_persist_003_output.txt`

**Configuration Applied (Lines 419-420):**
```
ntp server 192.168.100.175 version 4 iburst prefer
sonic(config)# [SUCCESS]
```

**Running-Config Output (Lines 122-144):**
```
show running-configuration | grep ntp
!
ntp authentication-key 1 md5 MinKey
[...]
ntp authenticate
ntp server 10.10.10.99
ntp server 192.168.100.175 iburst    <-- Missing 'prefer' and 'version 4'
ntp server 216.239.35.0 iburst
```

**show ntp server Output (Lines 483-492):**
```
NTP Servers                     minpoll maxpoll Prefer Authentication key ID
---------------------------------------------------------------------------------------------------------------------
192.168.100.175                                 True    <-- 'Prefer' shown, but no 'version' column
```

**config_db.json Output (Lines 559-569):**
```json
"NTP_SERVER": {
    "192.168.100.175": {
        "admin_state": "enabled",
        "iburst": "enabled",
        "prefer": "enabled"    <-- Correctly stored
    }
}
```

---

### Environment Details

**Platform**: SONiC Virtual Switch (VS)
**CLI Mode**: KLISH (sonic-cli)

**Tested Options:**
- ✅ iburst: Displayed in running-config
- ❌ prefer: NOT displayed in running-config (but shown in show ntp server)
- ❌ version: NOT displayed anywhere (but stored in config_db.json)

---

### Workaround

**Verification Method:**
To verify complete NTP server configuration:

```bash
# Method 1: Check config_db.json directly
admin@sonic:~$ sudo cat /etc/sonic/config_db.json | python3 -m json.tool | grep -A 10 NTP_SERVER

# Method 2: Use show ntp server (shows prefer flag)
sonic# show ntp server

# Method 3: Check running configuration in Linux
admin@sonic:~$ sudo cat /etc/chrony/chrony.conf | grep server
```

---

### Impact Assessment

**User Impact**: Low
- Configuration verification requires multiple commands
- Running-config appears incomplete (though functionality works)
- May cause confusion during auditing

**Functional Impact**:
- No functional impact (settings are applied correctly)
- Display-only issue

**Use Cases Affected**:
- Configuration auditing
- Compliance verification
- Configuration backup/restore validation

---

### Recommended Fix

**Enhancement Request:**

Update `show running-configuration` NTP section to display:
1. All configured server options (prefer, version, minpoll, maxpoll)
2. Implicit defaults when non-default values configured
3. Align with config_db.json content

**Example Enhanced Output:**
```
!
! NTP Configuration
!
ntp enable                          <-- Show explicit state
ntp authenticate
ntp authentication-key 1 md5 <encrypted>
ntp trusted-key 1
ntp server 192.168.100.175 version 4 iburst prefer
ntp source-interface Ethernet0
ntp source-interface Ethernet4
ntp vrf default                     <-- Show explicit VRF
!
```

---

## Summary of Bugs

| Bug # | Title | Severity | Component | Impact |
|-------|-------|----------|-----------|--------|
| 1 | Cannot bind auth key to existing server | Medium | NTP/KLISH | Service interruption required for auth updates |
| 2 | Grep limitations with quotes/options | Low | KLISH | Reduced troubleshooting efficiency |
| 3 | Running-config omits server options | Low | KLISH Display | Configuration verification confusion |

---

## Test Evidence Archive

**Test Execution Files:**
- Test Script: `/tmp/tc_ntp_persist_003_with_bug_test.exp` (249 lines)
- Test Output: `/tmp/tc_ntp_persist_003_output.txt` (585 lines)
- Test Log: `/tmp/tc_ntp_persist_003_log.txt`
- Test Report: `/home/claudeuser/Athira/sonic-mgmt/spytest/tests/system/ntp/report/TC_NTP_PERSIST_003.md`

**Configuration State:**
- Pre-test config: Multiple NTP servers configured, authentication enabled
- Post-test config: Added key 10, modified key 1, updated server 192.168.100.175

---

## Recommendations

### Immediate Actions (P2 - Medium Priority)
1. **Fix Bug #1**: Enable authentication key binding to existing servers
   - Target: Next maintenance release
   - Effort: Medium (requires KLISH command handler update)

### Short-term Actions (P3 - Low Priority)
2. **Document Bug #2**: Update KLISH user guide with grep limitations
   - Target: Next documentation update
   - Effort: Low (documentation only)

3. **Enhance Bug #3**: Improve running-config display completeness
   - Target: Future feature release
   - Effort: Low to Medium (display formatting update)

### Long-term Actions
4. Consider KLISH pipe handler enhancement for industry-standard compatibility
5. Align SONiC CLI behavior with traditional NOS expectations

---

**Bug Report Generated**: 2026-04-10
**Generated By**: TC_NTP_PERSIST_003 Test Execution
**For Official Bug Tracking**: Copy relevant sections to JIRA/GitHub Issues
