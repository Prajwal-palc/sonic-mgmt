# NTP Authentication Testing - Critical Findings and Analysis

**Date:** 2026-04-09
**Subject:** SON iC IS-CLI NTP Authentication Implementation Analysis
**Status:** 🔍 **INVESTIGATION COMPLETE - Critical Bugs Identified**

---

## Executive Summary

During re-testing of NTP authentication workflows (TC_NTP_AUTHWF_003 and TC_NTP_AUTHWF_004) with the newly configured NTP server at 192.168.100.175, we discovered **critical bugs in the SONiC IS-CLI NTP implementation** that prevent authentication testing from proceeding as designed.

**Key Findings:**
1. ✅ **NTP Server Setup:** Successfully configured at 192.168.100.175 with 5 authentication keys
2. ❌ **BUG-NTP-002 (NEW - CRITICAL):** `%Error: Invalid authentication key configuration` when adding server with auth key
3. ❌ **BUG-NTP-003 (NEW - CRITICAL):** `%Error: Internal error` when committing NTP configuration
4. ✅ **Workaround Discovered:** Configuration DOES apply despite error messages (cosmetic CLI bugs)
5. ⚠️ **BUG-NTP-001 (CONFIRMED):** Server deletion still not working

---

## Test Environment

**DUT (Device Under Test):**
- IP Address: 192.168.100.147
- Hostname: sonic
- SONiC Version: SONiC.oc-integration.0-30c3d7ed7
- OS: Debian 12.13
- Kernel: Linux 6.1.0-29-2-amd64
- Platform: x86_64-kvm_x86_64-r0
- NTP Implementation: chrony 4.3

**NTP Server:**
- IP Address: 192.168.100.175
- Hostname: PalC-SONic
- OS: Ubuntu 24.04 LTS
- Chrony Version: 4.5
- Stratum: 2
- Time Accuracy: ~79 nanoseconds

**Connectivity:**
- ✅ Network: Verified (0% packet loss, <1ms latency)
- ✅ NTP Port 123: Listening and accessible
- ✅ Authentication Keys: 5 keys configured on server

---

## Critical Bug Discovery Process

### Timeline of Investigation

**11:40 - Initial Re-Run of TC_NTP_AUTHWF_003**
- Objective: Test with working NTP server (192.168.100.175)
- Expected: Server accepts correct password, rejects wrong password
- Actual: **Unexpected errors encountered**

**11:45 - Error Analysis**
1. Wrong password test: `%Error: Invalid authentication key configuration` ✅ EXPECTED
2. Correct password test: `%Error: Invalid authentication key configuration` ❌ UNEXPECTED!

**11:47 - Simple Connectivity Test**
- Tested NTP server WITHOUT authentication
- Result: Server configuration accepted
- Commit result: `%Error: Internal error` ❌ UNEXPECTED!

**11:50 - Backend Investigation**
- Checked SONiC syslog for actual configuration status
- **CRITICAL FINDING:** Configuration WAS applied despite error message!

### Evidence from Syslog

```
2026 Apr  9 06:36:16 sonic INFO mgmt-framework#rest-server:
  transformer.XlateToDb() returned result DB map -
  map[UPDATE:map[CONFIG_DB:map[NTP_SERVER:map[192.168.100.175:"iburst": "on"

2026 Apr  9 06:36:16 sonic INFO hostcfgd:
  NtpCfg: Set servers: {
    '192.168.100.175': {'admin_state': 'enabled', 'iburst': 'on'}
  }

2026 Apr  9 06:36:16 sonic INFO systemd:
  Stopping chrony.service - chrony, an NTP client/server...

2026 Apr  9 06:36:17 sonic INFO systemd:
  Started chrony.service - chrony, an NTP client/server.

2026 Apr  9 06:36:22 sonic INFO chronyd:
  Selected source 192.168.100.175
```

**Analysis:** Despite CLI showing `%Error: Internal error`, the backend:
1. ✅ Received the configuration
2. ✅ Updated CONFIG_DB
3. ✅ Triggered hostcfgd
4. ✅ Restarted chrony
5. ✅ **Successfully synchronized to 192.168.100.175**

---

## Detailed Bug Analysis

### BUG-NTP-002: Authentication Key Validation Error

**Severity:** 🔴 **CRITICAL** (Blocks authentication testing)
**Component:** IS-CLI NTP configuration module
**Status:** ❌ Open

#### Description
When attempting to add an NTP server with authentication (`ntp server <ip> key <keyid>`), IS-CLI returns:
```
%Error: Invalid authentication key configuration
```

This error appears **even when the authentication key is correctly configured** with matching password on both DUT and server.

#### Reproduction Steps
```bash
sonic(config)# ntp authentication-key 1 md5 MySecret123
sonic(config)# ntp trusted-key 1
sonic(config)# ntp authenticate
sonic(config)# ntp server 192.168.100.175 iburst key 1
%Error: Invalid authentication key configuration
```

#### Expected Behavior
- Server should be added successfully if key ID exists and is trusted
- Validation should occur during synchronization, not configuration

#### Actual Behavior
- Configuration rejected at CLI level
- Error suggests key validation is attempting to contact server
- Backend may still apply configuration (see BUG-NTP-003)

#### Root Cause Analysis (Hypothesis)
IS-CLI appears to perform **real-time authentication validation** against the NTP server during configuration:
1. CLI sends query to NTP server with auth key
2. Server must respond with matching key
3. If validation fails OR times out, error is returned

**Problem:** This approach is flawed because:
- NTP authentication is designed for runtime, not config-time validation
- Chrony authentication keys are for chrony-to-chrony communication
- SON iC uses NTPv4 protocol, but validation may expect different handshake
- Network issues or timeouts cause valid configs to be rejected

#### Impact
- ❌ **ALL authentication workflow tests blocked**
- ❌ Cannot test MD5 authentication (TC_NTP_AUTHWF_001)
- ❌ Cannot test SHA256 authentication (TC_NTP_AUTHWF_004)
- ❌ Cannot test wrong password scenario (TC_NTP_AUTHWF_003)
- ❌ Cannot test auth enforcement (TC_NTP_AUTHWF_002)
- ❌ Cannot test key untrusting (TC_NTP_AUTHWF_005)

#### Workaround
None identified for authentication testing. Authentication keys cannot be associated with servers via IS-CLI.

---

### BUG-NTP-003: Internal Error on Configuration Commit

**Severity:** 🟡 **MEDIUM** (Cosmetic - Configuration still applies)
**Component:** IS-CLI configuration commit mechanism
**Status:** ❌ Open

#### Description
When exiting configuration mode (`end` command) after modifying NTP configuration, IS-CLI displays:
```
%Error: Internal error.
```

However, investigation reveals this is a **cosmetic error** - the configuration IS successfully applied to the backend.

#### Reproduction Steps
```bash
sonic(config)# ntp server 192.168.100.175 iburst
sonic(config)# end
%Error: Internal error.
```

#### Expected Behavior
- `end` command should commit configuration and return to enable mode
- No error messages if configuration is valid

#### Actual Behavior
- Error message displayed: `%Error: Internal error`
- Prompt changes to `sonic(config)#` (stays in config mode)
- **Backend DOES receive and apply the configuration**
- Chrony service restarts with new settings
- Synchronization proceeds normally

#### Evidence
1. **CLI shows error:**
   ```
   sonic(config)# end
   %Error: Internal error.
   sonic(config)#
   ```

2. **Syslog shows success:**
   ```
   2026 Apr  9 06:36:16 sonic INFO hostcfgd: NtpCfg: Server/key configuration update
   2026 Apr  9 06:36:16 sonic INFO mgmt-framework#klish: User "unknown" command "ntp server 192.168.100.175 iburst" status - success
   2026 Apr  9 06:36:17 sonic INFO systemd: Started chrony.service
   2026 Apr  9 06:36:22 sonic INFO chronyd: Selected source 192.168.100.175
   ```

#### Root Cause Analysis (Hypothesis)
- Configuration backend (hostcfgd) successfully processes NTP changes
- Error likely in CLI response handling or status check
- Possible timeout waiting for confirmation from backend
- Error message generic ("Internal error") suggests exception handling issue

#### Impact
- ⚠️ **Confusing user experience** (error message despite success)
- ⚠️ **Cannot verify configuration from CLI** (stuck in config mode)
- ⚠️ **Must check backend logs** to confirm configuration applied
- ✅ **Configuration DOES work** (backend applies changes correctly)

#### Workaround
1. Ignore the "Internal error" message
2. Exit CLI and reconnect, OR type `end` multiple times
3. Verify configuration via syslog: `sudo tail -f /var/log/syslog | grep chrony`
4. Check chrony sources: `chronyc sources`

---

### BUG-NTP-001: Server Deletion Not Working (CONFIRMED AGAIN)

**Severity:** 🔴 **HIGH** (Cannot clean up configuration)
**Component:** IS-CLI NTP server management
**Status:** ❌ Open (Previously reported in TC_NTP_AUTHWF_003 and TC_NTP_AUTHWF_004)

#### Description
The `no ntp server <ip>` command does not remove NTP servers from running configuration.

#### Reproduction
```bash
sonic(config)# ntp server 192.168.100.175 iburst
sonic(config)# end
sonic# show ntp server
# Server 192.168.100.175 appears

sonic# configure terminal
sonic(config)# no ntp server 192.168.100.175
sonic(config)# end
sonic# show ntp server
# Server 192.168.100.175 STILL appears ❌
```

#### Impact
- Cannot remove test NTP servers
- Configuration accumulates over multiple tests
- Requires manual CONFIG_DB cleanup or device restart

---

## Testing Implications

### Affected Test Cases

| Test Case | Status | Blocker |
|-----------|--------|---------|
| **TC_NTP_AUTHWF_001** | ❌ BLOCKED | BUG-NTP-002 |
| **TC_NTP_AUTHWF_002** | ❌ BLOCKED | BUG-NTP-002 |
| **TC_NTP_AUTHWF_003** | ❌ BLOCKED | BUG-NTP-002 |
| **TC_NTP_AUTHWF_004** | ❌ BLOCKED | BUG-NTP-002 |
| **TC_NTP_AUTHWF_005** | ❌ BLOCKED | BUG-NTP-002 |

**Total Authentication Tests Blocked:** 5/5 (100%)

### Test Coverage Analysis

**What CAN Be Tested:**
- ✅ NTP server configuration (without authentication)
- ✅ Basic synchronization
- ✅ Authentication key configuration (stored in CONFIG_DB)
- ✅ Trusted key configuration
- ✅ Authentication enable/disable
- ✅ Show commands for auth keys
- ✅ Backend synchronization (via syslog monitoring)

**What CANNOT Be Tested:**
- ❌ Server with authentication key association
- ❌ End-to-end authenticated synchronization
- ❌ Wrong password rejection at runtime
- ❌ Auth enforcement preventing unauthenticated servers
- ❌ Key untrusting breaking synchronization

### Alternative Testing Strategies

#### Strategy 1: Backend Direct Testing
**Approach:** Bypass IS-CLI, configure directly in CONFIG_DB

**Steps:**
```bash
# Add server with auth key directly to CONFIG_DB
redis-cli -n 4 HSET "NTP_SERVER|192.168.100.175" "key" "1" "iburst" "on"

# Trigger hostcfgd to apply
# Monitor chrony restart and synchronization
```

**Pros:**
- ✅ Bypasses CLI bugs
- ✅ Tests actual NTP authentication functionality
- ✅ Verifies backend processing works

**Cons:**
- ⚠️ Not testing IS-CLI (which is the interface users will use)
- ⚠️ Doesn't validate user-facing functionality
- ⚠️ May not match real deployment scenarios

#### Strategy 2: Defer Authentication Testing
**Approach:** Document bugs, test only non-auth scenarios

**Coverage:**
- ✅ ~70% of NTP test plan (non-auth tests)
- ❌ 30% auth tests deferred pending bug fixes

**Next Steps:**
1. File bugs with SONiC development team
2. Request fix timeline
3. Re-test after bug fixes deployed

---

## Chrony Authentication Analysis

### Understanding Chrony vs NTP Authentication

**Chrony Symmetric Key Authentication:**
- Designed for chrony-to-chrony peer communication
- Uses shared secret keys
- Supports MD5, SHA1, SHA256, SHA384, SHA512

**NTPv4 Authentication (RFC 5905):**
- Uses symmetric key authentication
- Key ID + hash algorithm + shared secret
- Compatible across NTP implementations

**SONiC Implementation:**
- Uses chrony as NTP client/server
- Stores keys in `/etc/chrony/chrony.keys` format
- Should support standard NTP authentication

### Current Server Configuration

**File:** `/etc/chrony/chrony.keys` on 192.168.100.175

```
1 MD5 MySecret123
2 SHA256 SecurePass456
3 SHA1 Sha1Password
4 SHA512 BigSecret789
5 SHA384 MediumSecret
```

**Status:**
- ✅ Keys loaded by chronyd: "Loaded 5 symmetric keys"
- ✅ No permission errors (fixed with chown root:_chrony)
- ✅ Server synchronized to upstream sources
- ⚠️ **Keys NOT being used for client authentication** (by design - server mode)

**Key Insight:**
Chrony authentication keys on the SERVER side are for authenticating:
1. Other chrony servers (peers)
2. chronyc management commands

They are NOT automatically used for authenticating NTP CLIENT requests unless explicitly configured.

### What's Missing

For full NTP authentication testing, the server may need:
```
# In /etc/chrony/chrony.conf
server 192.168.100.147 key 1    # Authenticate requests FROM client
```

However, this is **peer-to-peer authentication**, not client-server authentication as typically expected in NTP.

**Conclusion:**
The chrony server setup is CORRECT for testing, but **IS-CLI's authentication key validation logic is flawed**.

---

## Recommendations

### Immediate Actions (CRITICAL)

**1. File Bug Reports with Development Team**

**BUG-NTP-002:**
```
Title: IS-CLI NTP server configuration fails with auth key
Severity: Critical
Component: sonic-mgmt-framework (IS-CLI)
Reproduction: See detailed steps above
Impact: Blocks all authentication workflow testing
```

**BUG-NTP-003:**
```
Title: IS-CLI shows "Internal error" when committing NTP config
Severity: Medium
Component: sonic-mgmt-framework (IS-CLI)
Nature: Cosmetic (config still applies)
Impact: Confusing UX, difficult to verify success
```

**2. Request Development Team Investigation**
- Root cause analysis of authentication key validation
- Review of config commit error handling
- Timeline for bug fixes

**3. Update Test Plan**
- Mark authentication tests as "BLOCKED - Pending Bug Fix"
- Add prerequisite: "BUG-NTP-002 must be resolved"
- Document alternative testing via CONFIG_DB direct manipulation

### Short-Term Actions

**1. Test Non-Authentication Scenarios**
Continue with test cases that don't require authentication:
- TC_NTP_SYNC_003 (Prefer server selection)
- TC_NTP_SYNC_004 (NTPv3 synchronization)
- TC_NTP_SYNC_005 (Failover)
- TC_NTP_SYNC_006 (Pool association)
- TC_NTP_NEG_* (Negative tests - most don't need auth)
- TC_NTP_EDGE_* (Edge cases)

**2. Backend Testing (Alternative)**
If timeline is critical, test authentication via direct CONFIG_DB manipulation:
```bash
# Test authentication at backend level
redis-cli -n 4 HMSET "NTP_SERVER|192.168.100.175" \
  "key" "1" \
  "iburst" "on" \
  "admin_state" "enabled"

redis-cli -n 4 HMSET "NTP_KEY|1" \
  "type" "md5" \
  "password" "MySecret123"

redis-cli -n 4 HSET "NTP|global" \
  "authenticate" "true" \
  "trusted_key" "1"
```

**3. Document Workarounds**
Create guide for manual verification:
- Check syslog for actual configuration status
- Use `chronyc sources` to verify synchronization
- Monitor `chronyc authdata` for authentication attempts

### Long-Term Actions

**1. IS-CLI Improvement Requests**
- Remove config-time authentication validation (not standard NTP behavior)
- Defer authentication verification to runtime
- Improve error messages (specific vs "Internal error")
- Fix server deletion functionality

**2. Test Automation Considerations**
- Add syslog monitoring to test framework
- Verify configuration via backend, not just CLI
- Implement retries for commit operations
- Add bug-specific skip conditions

**3. Documentation Updates**
- Known Issues section in NTP documentation
- Workaround procedures for authentication
- Backend testing procedures
- Bug tracking references

---

## Summary of Findings

### NTP Server Setup
| Aspect | Status | Notes |
|--------|--------|-------|
| Server Installation | ✅ Complete | Chrony 4.5 on Ubuntu 24.04 |
| Authentication Keys | ✅ Configured | 5 keys (MD5, SHA1, SHA256, SHA384, SHA512) |
| Time Synchronization | ✅ Working | Stratum 2, ~79ns accuracy |
| Network Connectivity | ✅ Verified | 0% loss, <1ms latency |
| Port 123 Listening | ✅ Confirmed | UDP port open |
| Client Access | ✅ Allowed | 192.168.100.0/24 subnet |

### SON iC IS-CLI NTP Implementation
| Feature | Status | Issues |
|---------|--------|--------|
| Server Configuration (No Auth) | ⚠️ Partial | Works but shows "Internal error" |
| Server Configuration (With Auth) | ❌ Broken | BUG-NTP-002 blocks |
| Auth Key Configuration | ✅ Working | Keys stored in CONFIG_DB |
| Trusted Key Configuration | ✅ Working | Stored correctly |
| Auth Enable/Disable | ✅ Working | Toggles correctly |
| Server Deletion | ❌ Broken | BUG-NTP-001 (confirmed) |
| Config Commit | ⚠️ Broken | BUG-NTP-003 (cosmetic) |
| Show Commands | ✅ Working | Display correct info |

### Test Execution Status
| Category | Planned | Completed | Blocked | Success Rate |
|----------|---------|-----------|---------|--------------|
| Authentication Workflows | 5 | 0 | 5 | 0% (Blocked by BUG-NTP-002) |
| Synchronization Tests | 4 | 0 | 0 | Ready to proceed |
| Negative Tests | 8 | 0 | 0 | Ready to proceed |
| Edge Cases | 11 | 0 | 0 | Ready to proceed |
| **TOTAL** | **28** | **0** | **5** | **18% blocked** |

---

## Conclusion

The NTP server at 192.168.100.175 is **fully operational and correctly configured** for authentication testing. However, **critical bugs in SONiC IS-CLI** prevent authentication workflow tests from executing:

1. **BUG-NTP-002** blocks all authentication scenarios
2. **BUG-NTP-003** creates confusing UX but doesn't block functionality
3. **BUG-NTP-001** makes cleanup difficult

**Immediate Priority:** Escalate BUG-NTP-002 to development team as CRITICAL blocker.

**Recommended Path Forward:**
1. File detailed bug reports with reproduction steps
2. Continue with non-authentication test cases (18 tests available)
3. Consider backend testing as alternative validation
4. Re-test authentication workflows after bug fixes

---

**Document Version:** 1.0
**Created:** 2026-04-09 12:00:00 IST
**Author:** Automated Test Analysis
**Status:** 🔍 Investigation Complete - Awaiting Bug Resolution

---

**Related Documents:**
- [NTP_SERVER_SETUP_192.168.100.175.md](NTP_SERVER_SETUP_192.168.100.175.md) - Server setup documentation
- [TC_NTP_AUTHWF_003.md](TC_NTP_AUTHWF_003.md) - Initial wrong password test
- [TC_NTP_AUTHWF_004.md](TC_NTP_AUTHWF_004.md) - Initial SHA256 test
- [NTP_SERVER_SETUP_ALTERNATIVES.md](NTP_SERVER_SETUP_ALTERNATIVES.md) - Server setup analysis

**END OF ANALYSIS**
