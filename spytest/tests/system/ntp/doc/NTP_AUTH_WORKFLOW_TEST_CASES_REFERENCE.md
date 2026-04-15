# NTP Authentication Workflow Test Cases - Reference Documentation

**Document Version:** 1.0
**Created:** 2026-04-09
**Purpose:** Comprehensive reference for NTP authentication workflow test case automation
**Status:** ❌ **BLOCKED BY BUG-NTP-002** - See [Analysis Document](../report/NTP_AUTHENTICATION_TESTING_ANALYSIS.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Prerequisites](#prerequisites)
4. [Test Cases](#test-cases)
   - [TC_NTP_AUTHWF_001](#tc_ntp_authwf_001---md5-full-authentication-workflow)
   - [TC_NTP_AUTHWF_002](#tc_ntp_authwf_002---auth-enforcement-blocks-unauthenticated-server)
   - [TC_NTP_AUTHWF_003](#tc_ntp_authwf_003---wrong-password-prevents-synchronization)
   - [TC_NTP_AUTHWF_004](#tc_ntp_authwf_004---sha256-full-authentication-workflow)
   - [TC_NTP_AUTHWF_005](#tc_ntp_authwf_005---untrusting-key-breaks-synchronization)
5. [Common Verification Steps](#common-verification-steps)
6. [Known Issues and Workarounds](#known-issues-and-workarounds)
7. [Script Generation Guidelines](#script-generation-guidelines)

---

## Overview

This document provides detailed specifications for the 5 NTP authentication workflow test cases (TC_NTP_AUTHWF_001 through TC_NTP_AUTHWF_005). These test cases verify the end-to-end authentication functionality of NTP in SONiC IS-CLI (KLISH mode).

### Test Category
- **Category:** Authentication Workflows
- **CLI Mode:** IS-CLI (KLISH)
- **Test Type:** Functional, End-to-End
- **Topology:** Single DUT + NTP Server
- **Platform Support:** VS/HW (Virtual Switch and Hardware)

### Current Status
🔴 **ALL 5 TEST CASES BLOCKED** by BUG-NTP-002

**Issue:** IS-CLI rejects server configuration with authentication key, even when credentials are correct.

**Error Message:**
```
sonic(config)# ntp server 192.168.100.175 iburst key 1
%Error: Invalid authentication key configuration
```

**See:** [NTP_AUTHENTICATION_TESTING_ANALYSIS.md](../report/NTP_AUTHENTICATION_TESTING_ANALYSIS.md) for detailed analysis.

---

## Test Environment Setup

### Topology

```
┌─────────────────────────────────────────────────────────┐
│                   TEST TOPOLOGY                         │
│                                                         │
│   ┌──────────────┐                  ┌──────────────┐   │
│   │    DUT1      │                  │   NTP-SRV    │   │
│   │  (SONiC)     │                  │  (Linux VM)  │   │
│   │              │  Management      │              │   │
│   │  IP:         │  Network         │  IP:         │   │
│   │  192.168.    ├──────────────────┤  192.168.    │   │
│   │  100.147     │                  │  100.175     │   │
│   │              │                  │              │   │
│   │  NTP Client  │                  │  chrony 4.5  │   │
│   │  chrony 4.3  │                  │  + Auth Keys │   │
│   └──────────────┘                  └──────────────┘   │
│                                                         │
│  Management Network: 192.168.100.0/24                   │
└─────────────────────────────────────────────────────────┘
```

### Device Details

**DUT (Device Under Test):**
- IP Address: 192.168.100.147
- Hostname: sonic
- SONiC Version: SONiC.oc-integration.0-30c3d7ed7
- OS: Debian 12.13
- Platform: x86_64-kvm_x86_64-r0
- NTP Implementation: chrony 4.3
- CLI Mode: IS-CLI (KLISH)

**NTP Server:**
- IP Address: 192.168.100.175
- Hostname: PalC-SONic
- OS: Ubuntu 24.04 LTS
- Chrony Version: 4.5
- Stratum: 2
- Time Accuracy: ~79 nanoseconds

---

## Prerequisites

### NTP Server Configuration

**File:** `/etc/chrony/chrony.conf` on 192.168.100.175

```bash
# Upstream NTP sources
pool ntp.ubuntu.com iburst maxsources 4
server 216.239.35.0 iburst
server 216.239.35.12 iburst

# Authentication keys file
keyfile /etc/chrony/chrony.keys

# Allow client access
allow 192.168.100.0/24
allow 192.168.0.0/16

# Local stratum
local stratum 3

# Bind to all interfaces
bindaddress 0.0.0.0
bindaddress ::
```

**File:** `/etc/chrony/chrony.keys` on 192.168.100.175

```bash
# NTP Authentication Keys for Testing
# Format: <key-id> <hash-type> <password>
1 MD5 MySecret123
2 SHA256 SecurePass456
3 SHA1 Sha1Password
4 SHA512 BigSecret789
5 SHA384 MediumSecret
```

**Permissions:**
```bash
sudo chmod 640 /etc/chrony/chrony.keys
sudo chown root:_chrony /etc/chrony/chrony.keys
```

### NTP Server Verification

Before running tests, verify NTP server status:

```bash
# Check service status
sudo systemctl status chrony

# Verify sources
sudo chronyc sources

# Check authentication keys loaded
sudo journalctl -u chrony | grep "symmetric keys"
# Expected: "Loaded 5 symmetric keys"

# Verify port listening
sudo ss -unl | grep :123
# Expected: UNCONN 0 0 0.0.0.0:123
```

### DUT Prerequisites

**Network Connectivity:**
```bash
# From DUT, verify server is reachable
admin@sonic:~$ ping -c 4 192.168.100.175
# Expected: 0% packet loss
```

**NTP Service:**
```bash
# Verify chrony is running
admin@sonic:~$ ps aux | grep chronyd
# Expected: _chrony processes running
```

**CLI Access:**
```bash
# Verify KLISH mode access
admin@sonic:~$ sonic-cli
sonic#
# Should enter KLISH enable mode
```

---

## Test Cases

---

### TC_NTP_AUTHWF_001 - MD5 Full Authentication Workflow

**Test ID:** TC_NTP_AUTHWF_001
**Priority:** High
**Test Type:** Positive, End-to-End
**Platform:** VS/HW
**Status:** ❌ **BLOCKED BY BUG-NTP-002**

#### Objective

Verify end-to-end NTP authentication workflow using MD5 hash algorithm:
1. Configure authentication key on DUT
2. Mark key as trusted
3. Enable authentication enforcement
4. Associate key with NTP server
5. Verify successful synchronization with authenticated server

#### Pre-conditions

1. NTP server (192.168.100.175) is running and accessible
2. NTP server has authentication key configured:
   - Key ID: 1
   - Algorithm: MD5
   - Password: `MySecret123`
3. DUT has no existing NTP configuration
4. DUT can ping NTP server (0% packet loss)

#### Test Steps

**Step 1: Enter KLISH Configuration Mode**
```bash
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic(config)#
```

**Step 2: Enable NTP Service**
```bash
sonic(config)# ntp enable
```

**Step 3: Configure MD5 Authentication Key**
```bash
sonic(config)# ntp authentication-key 1 md5 MySecret123
```
- Key ID: 1
- Algorithm: MD5
- Password: MySecret123 (must match server)

**Step 4: Mark Key as Trusted**
```bash
sonic(config)# ntp trusted-key 1
```

**Step 5: Enable NTP Authentication Enforcement**
```bash
sonic(config)# ntp authenticate
```

**Step 6: Configure NTP Server with Key Binding**
```bash
sonic(config)# ntp server 192.168.100.175 iburst key 1
```
⚠️ **KNOWN ISSUE:** This command currently fails with BUG-NTP-002:
```
%Error: Invalid authentication key configuration
```

**Step 7: Exit Configuration Mode**
```bash
sonic(config)# end
sonic#
```
⚠️ **KNOWN ISSUE:** May show BUG-NTP-003:
```
%Error: Internal error.
```

**Step 8: Wait for Synchronization**
```bash
# Wait 60 seconds for NTP to synchronize
sonic# ! Waiting 60 seconds...
```

**Step 9: Verify NTP Global Configuration**
```bash
sonic# show ntp global
```

**Step 10: Verify NTP Server Configuration**
```bash
sonic# show ntp server
```

**Step 11: Verify NTP Associations**
```bash
sonic# show ntp associations
```

**Step 12: Verify Authentication Keys**
```bash
sonic# show ntp authentication-keys
```

**Step 13: Verify Trusted Keys**
```bash
sonic# show ntp trusted-keys
```

#### Expected Results

**After Step 2 (ntp enable):**
- No error message
- NTP service enabled

**After Step 3 (authentication-key):**
- No error message
- Key stored in CONFIG_DB

**After Step 4 (trusted-key):**
- No error message
- Key marked as trusted

**After Step 5 (ntp authenticate):**
- No error message
- Authentication enforcement enabled

**After Step 6 (ntp server with key):**
- **EXPECTED:** No error message, server added ✅
- **ACTUAL (BUG):** `%Error: Invalid authentication key configuration` ❌

**Step 9 - show ntp global:**
```
NTP Configuration:
  Enabled:             True
  Authentication:      True
  Vrf:                 default
  Source Interface:    -
```
- Enabled: True
- Authentication: True

**Step 10 - show ntp server:**
```
Address            Version  Association  Iburst   Prefer  Key
192.168.100.175    4        server       enabled  False   1
```
- Server IP: 192.168.100.175
- Key: 1 (authentication key bound)

**Step 11 - show ntp associations (after 60s):**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.100.175  time4.google.   3 u   32   64  377    0.500    0.120   0.050
```
- `*` prefix indicates selected, synchronized source
- Stratum: 3 (server is stratum 2, DUT becomes stratum 3)
- Reach: 377 (octal, all 8 polls successful)

**Step 12 - show ntp authentication-keys:**
```
Key ID  Type    Trusted
1       md5     yes
```

**Step 13 - show ntp trusted-keys:**
```
Trusted Keys: 1
```

#### Verification Points

✅ **Authentication key configured:** Key 1 with MD5 appears in show commands
✅ **Key marked as trusted:** Trusted keys list shows key 1
✅ **Authentication enabled:** Global config shows Authentication: True
✅ **Server accepts key binding:** Server configured with `key 1` parameter
✅ **Synchronization successful:** `*` prefix on server in associations
✅ **Time offset acceptable:** Offset < 1 second
✅ **Reach count normal:** 377 (all polls successful)

#### Cleanup Steps

```bash
sonic# configure terminal
sonic(config)# no ntp server 192.168.100.175
sonic(config)# no ntp authenticate
sonic(config)# no ntp trusted-key 1
sonic(config)# no ntp authentication-key 1
sonic(config)# no ntp enable
sonic(config)# end
sonic#
```

⚠️ **KNOWN ISSUE (BUG-NTP-001):** Server deletion may not work. Verify with:
```bash
sonic# show ntp server
# If server still appears, manual CONFIG_DB cleanup required
```

#### Success Criteria

- ✅ All configuration commands execute without error
- ✅ NTP server synchronizes with `*` prefix in associations
- ✅ Authentication key is used (verified via syslog or chrony authdata)
- ✅ Time offset is acceptable (< 1 second)
- ✅ Configuration persists in running-config

#### Failure Scenarios

❌ **Configuration rejected:** `%Error: Invalid authentication key configuration` (BUG-NTP-002)
❌ **No synchronization:** Server lacks `*` prefix after 60s
❌ **Stratum 16:** Server shows as unreachable
❌ **Reach 0:** No successful polls

#### Alternative Verification (Workaround for BUG-NTP-003)

If CLI shows errors but you suspect config applied, verify via backend:

```bash
# SSH to DUT
admin@sonic:~$ sudo tail -f /var/log/syslog | grep -i ntp

# Expected logs when config applies:
# hostcfgd: NtpCfg: Server/key configuration update
# chronyd: Selected source 192.168.100.175

# Check chrony sources
admin@sonic:~$ chronyc sources
```

---

### TC_NTP_AUTHWF_002 - Auth Enforcement Blocks Unauthenticated Server

**Test ID:** TC_NTP_AUTHWF_002
**Priority:** High
**Test Type:** Negative, Security
**Platform:** VS/HW
**Status:** ❌ **BLOCKED BY BUG-NTP-002**

#### Objective

Verify that when NTP authentication enforcement is enabled (`ntp authenticate`), the NTP daemon **rejects** synchronization with servers that are configured **without** an authentication key binding.

This ensures that authentication enforcement properly protects against unauthenticated time sources.

#### Pre-conditions

1. NTP server (192.168.100.175) is running and accessible
2. NTP server has authentication keys configured
3. DUT has no existing NTP configuration
4. DUT can ping NTP server

#### Test Steps

**Step 1-2: Enter Configuration Mode and Enable NTP**
```bash
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic(config)# ntp enable
```

**Step 3: Configure Authentication Key (but don't bind to server)**
```bash
sonic(config)# ntp authentication-key 1 md5 MySecret123
```

**Step 4: Mark Key as Trusted**
```bash
sonic(config)# ntp trusted-key 1
```

**Step 5: Enable Authentication Enforcement**
```bash
sonic(config)# ntp authenticate
```
⚠️ **KEY STEP:** Authentication is enabled globally

**Step 6: Add Server WITHOUT Key Binding**
```bash
sonic(config)# ntp server 192.168.100.175 iburst
```
⚠️ **NOTE:** No `key 1` parameter - server is unauthenticated

**Step 7: Commit Configuration**
```bash
sonic(config)# end
sonic#
```

**Step 8: Wait for Synchronization Attempt**
```bash
# Wait 90 seconds (longer than typical poll interval)
sonic# ! Waiting 90 seconds...
```

**Step 9: Check NTP Associations**
```bash
sonic# show ntp associations
```

#### Expected Results

**Step 6 (add server without key):**
- **Option A:** Command accepted, but server won't sync (runtime enforcement)
- **Option B:** Command rejected (config-time enforcement)

**Step 9 (show ntp associations):**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.100.175  .INIT.         16 u    -   64    0    0.000    0.000   0.000
```

**Key Indicators of Rejection:**
- ❌ **NO `*` prefix** - Server not selected as time source
- ❌ **Stratum 16** - Indicates unreachable/rejected server
- ❌ **Reach: 0** - No successful authentication
- ❌ **refid: .INIT.** - Not synchronized

#### Verification Points

✅ **Authentication enforcement active:** `show ntp global` shows Authentication: True
✅ **Server added without key:** `show ntp server` shows no key binding
✅ **Server rejected for sync:** No `*` prefix in associations
✅ **Stratum indicates rejection:** Stratum 16 or unreachable state
✅ **Reach count zero:** No successful polls

#### Negative Test - What Should NOT Happen

❌ Server should **NOT** synchronize (no `*` prefix)
❌ Server should **NOT** show stratum 2-3 (actual server stratum)
❌ Reach should **NOT** be 377 (successful)
❌ Time offset should **NOT** stabilize

#### Alternative Test Scenario

To verify enforcement works correctly, follow with:

**Add key binding to same server:**
```bash
sonic(config)# no ntp server 192.168.100.175
sonic(config)# ntp server 192.168.100.175 iburst key 1
sonic(config)# end
sonic# ! Wait 60 seconds
sonic# show ntp associations
```

**Expected:** Now server should sync with `*` prefix (proves enforcement was the blocker)

#### Cleanup

```bash
sonic(config)# no ntp server 192.168.100.175
sonic(config)# no ntp authenticate
sonic(config)# no ntp trusted-key 1
sonic(config)# no ntp authentication-key 1
sonic(config)# no ntp enable
```

#### Success Criteria

- ✅ Unauthenticated server is rejected for synchronization
- ✅ Server shows stratum 16 or reach 0
- ✅ No `*` prefix in associations
- ✅ Authentication enforcement prevents sync

#### Known Issues

⚠️ **BUG-NTP-002:** May not be able to add authenticated server for comparison test
⚠️ **BUG-NTP-003:** May see "Internal error" on commit

---

### TC_NTP_AUTHWF_003 - Wrong Password Prevents Synchronization

**Test ID:** TC_NTP_AUTHWF_003
**Priority:** High
**Test Type:** Negative, Security
**Platform:** VS/HW
**Status:** ❌ **BLOCKED BY BUG-NTP-002**

#### Objective

Verify that configuring an NTP authentication key with an **incorrect password** (mismatched from server) prevents the DUT from synchronizing with that server.

This ensures that authentication properly validates credentials and rejects mismatched passwords.

#### Pre-conditions

1. NTP server (192.168.100.175) is running with key 1 = `MySecret123` (correct password)
2. DUT has no existing NTP configuration
3. Network connectivity verified

#### Test Steps

**Step 1-2: Enter Configuration and Enable NTP**
```bash
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic(config)# ntp enable
```

**Step 3: Configure Authentication Key with WRONG Password**
```bash
sonic(config)# ntp authentication-key 1 md5 WrongPassword999
```
⚠️ **CRITICAL:** Password is `WrongPassword999` but server expects `MySecret123`

**Step 4: Mark Key as Trusted**
```bash
sonic(config)# ntp trusted-key 1
```

**Step 5: Enable Authentication Enforcement**
```bash
sonic(config)# ntp authenticate
```

**Step 6: Add Server with Key Binding**
```bash
sonic(config)# ntp server 192.168.100.175 iburst key 1
```
⚠️ **KNOWN ISSUE (BUG-NTP-002):** This command fails:
```
%Error: Invalid authentication key configuration
```

**Alternative Approach (If BUG-NTP-002 blocks):**

IS-CLI may perform config-time validation that detects password mismatch. If so:

```bash
# Error indicates validation happened at config time
# Test becomes: "Wrong password rejected at configuration"
# rather than: "Wrong password rejected at synchronization"
```

**Step 7: Wait and Check (If server was added)**
```bash
sonic(config)# end
sonic# ! Wait 90 seconds
sonic# show ntp associations
```

#### Expected Results

**Scenario A: Config-Time Rejection (Current Behavior - BEHAVIOR-NTP-001)**

```bash
sonic(config)# ntp server 192.168.100.175 iburst key 1
%Error: Invalid authentication key configuration
```
- Server configuration is **rejected**
- Error indicates auth validation failed
- Server is NOT added to running config

**Scenario B: Runtime Rejection (Traditional NTP Behavior)**

If server configuration is accepted:

```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.100.175  .AUTH.         16 u   32   64    0    0.000    0.000   0.000
```
- Server added but **not synchronized**
- Stratum 16 or refid `.AUTH.` indicates auth failure
- Reach: 0 (no successful polls)
- No `*` prefix

#### Verification Points

**Config-Time Validation:**
✅ Wrong password detected during `ntp server` command
✅ Error message indicates auth key issue
✅ Server NOT in `show ntp server` output

**Runtime Validation:**
✅ Server in `show ntp server` with key binding
✅ Server in associations but NO `*` prefix
✅ Stratum 16 or reach 0
✅ Authentication failure logged in syslog

#### Follow-up Test: Correct Password Should Work

After demonstrating wrong password fails, verify correct password succeeds:

```bash
sonic(config)# no ntp authentication-key 1
sonic(config)# ntp authentication-key 1 md5 MySecret123
sonic(config)# ntp server 192.168.100.175 iburst key 1
sonic(config)# end
sonic# ! Wait 60 seconds
sonic# show ntp associations
```

**Expected:** Server now shows `*` prefix (synchronized)

#### Cleanup

```bash
sonic(config)# no ntp server 192.168.100.175
sonic(config)# no ntp authenticate
sonic(config)# no ntp trusted-key 1
sonic(config)# no ntp authentication-key 1
sonic(config)# no ntp enable
```

#### Success Criteria

- ✅ Wrong password is detected and rejected
- ✅ Server does not synchronize with mismatched credentials
- ✅ Correct password (follow-up test) allows synchronization
- ✅ Security is maintained (no sync with wrong credentials)

#### Known Issues

⚠️ **BUG-NTP-002:** Config-time validation rejects even CORRECT passwords
⚠️ **BEHAVIOR-NTP-001:** IS-CLI validates at config time (non-standard NTP behavior)

#### Test Variations

**Variation 1: Change password while synchronized**
1. Start with correct password and sync
2. Change to wrong password
3. Verify sync breaks

**Variation 2: Different hash algorithms**
- Test with SHA256, SHA512, etc.
- Verify wrong password rejected for all algorithms

---

### TC_NTP_AUTHWF_004 - SHA256 Full Authentication Workflow

**Test ID:** TC_NTP_AUTHWF_004
**Priority:** High
**Test Type:** Positive, Algorithm Validation
**Platform:** VS/HW
**Status:** ❌ **BLOCKED BY BUG-NTP-002**

#### Objective

Verify end-to-end NTP authentication workflow using **SHA256** hash algorithm (stronger than MD5). This test is identical to TC_NTP_AUTHWF_001 but uses SHA256 instead of MD5 to verify support for modern hash algorithms.

#### Pre-conditions

1. NTP server (192.168.100.175) has authentication key configured:
   - Key ID: 2
   - Algorithm: SHA256
   - Password: `SecurePass456`
2. DUT has no existing NTP configuration
3. Network connectivity verified

#### Test Steps

**Step 1-2: Enter Configuration and Enable NTP**
```bash
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic(config)# ntp enable
```

**Step 3: Configure SHA256 Authentication Key**
```bash
sonic(config)# ntp authentication-key 2 sha256 SecurePass456
```
⚠️ **IMPORTANT:**
- Key ID: 2 (different from MD5 test)
- Algorithm: **sha256** (not md5)
- Password: SecurePass456 (must match server)

**OpenConfig Format Check:**
When stored in CONFIG_DB, SHA256 keys use OpenConfig format:
```
ntp_auth_sha256
```

**Step 4: Mark Key as Trusted**
```bash
sonic(config)# ntp trusted-key 2
```

**Step 5: Enable Authentication Enforcement**
```bash
sonic(config)# ntp authenticate
```

**Step 6: Configure Server with SHA256 Key**
```bash
sonic(config)# ntp server 192.168.100.175 iburst key 2
```
⚠️ **KNOWN ISSUE (BUG-NTP-002):** This fails with:
```
%Error: Invalid authentication key configuration
```

**Step 7: Verify Configuration**
```bash
sonic(config)# end
sonic# show ntp authentication-keys
```

**Expected Output:**
```
Key ID  Type     Trusted
2       sha256   yes
```

**Step 8: Wait and Check Synchronization**
```bash
sonic# ! Wait 60 seconds
sonic# show ntp associations
```

#### Expected Results

**show ntp global:**
```
NTP Configuration:
  Enabled:             True
  Authentication:      True
```

**show ntp authentication-keys:**
```
Key ID  Type     Trusted
2       sha256   yes
```
✅ Type shows **sha256** (not md5)

**show ntp server:**
```
Address            Version  Association  Iburst   Prefer  Key
192.168.100.175    4        server       enabled  False   2
```
✅ Key: 2 (SHA256 key)

**show ntp associations (after 60s):**
```
*192.168.100.175  time4.google.   3 u   32   64  377    0.500    0.120   0.050
```
✅ `*` prefix indicates synchronized with SHA256 authentication

**show running-config ntp:**
```
ntp enable
ntp authentication-key 2 sha256 SecurePass456
ntp trusted-key 2
ntp authenticate
ntp server 192.168.100.175 iburst key 2
```

#### Verification Points

✅ **SHA256 algorithm supported:** Key type shows `sha256` in show commands
✅ **OpenConfig format used:** CONFIG_DB stores as `ntp_auth_sha256`
✅ **Key configured correctly:** Password `SecurePass456` accepted
✅ **Server synchronizes:** `*` prefix in associations
✅ **Authentication functional:** SHA256 hash validation works

#### Comparison with MD5 (TC_NTP_AUTHWF_001)

| Aspect | MD5 (Test 001) | SHA256 (Test 004) |
|--------|----------------|-------------------|
| Key ID | 1 | 2 |
| Algorithm | md5 | sha256 |
| Password | MySecret123 | SecurePass456 |
| Hash Strength | Weak (128-bit) | Strong (256-bit) |
| OpenConfig Format | `md5` | `openconfig-system-ext:ntp_auth_sha256` |

#### Supported Hash Algorithms

Based on testing, SONiC IS-CLI supports all these algorithms:

| Algorithm | CLI Keyword | OpenConfig Format | Key Length | Status |
|-----------|-------------|-------------------|------------|--------|
| MD5 | `md5` | `md5` | 128-bit | ✅ Supported |
| SHA-1 | `sha1` | `openconfig-system-ext:ntp_auth_sha1` | 160-bit | ✅ Supported |
| **SHA-256** | **`sha256`** | **`openconfig-system-ext:ntp_auth_sha256`** | **256-bit** | **✅ Supported** |
| SHA-384 | `sha384` | `openconfig-system-ext:ntp_auth_sha384` | 384-bit | ✅ Supported |
| SHA-512 | `sha512` | `openconfig-system-ext:ntp_auth_sha512` | 512-bit | ✅ Supported |

#### Cleanup

```bash
sonic(config)# no ntp server 192.168.100.175
sonic(config)# no ntp authenticate
sonic(config)# no ntp trusted-key 2
sonic(config)# no ntp authentication-key 2
sonic(config)# no ntp enable
```

#### Success Criteria

- ✅ SHA256 authentication key configured successfully
- ✅ OpenConfig format used in CONFIG_DB
- ✅ Server synchronizes with SHA256 authentication
- ✅ All show commands display correct algorithm type
- ✅ Configuration persists in running-config

#### Known Issues

⚠️ **BUG-NTP-002:** Server configuration with key fails (same as MD5 test)
⚠️ **BUG-NTP-003:** Internal error on commit

#### Test Variations

**Variation 1: Multiple algorithms simultaneously**
```bash
sonic(config)# ntp authentication-key 1 md5 Pass1
sonic(config)# ntp authentication-key 2 sha256 Pass2
sonic(config)# ntp authentication-key 3 sha512 Pass3
```
Verify all can coexist.

**Variation 2: Algorithm comparison**
- Configure same server with MD5 key
- Reconfigure with SHA256 key
- Verify SHA256 works correctly

---

### TC_NTP_AUTHWF_005 - Untrusting Key Breaks Synchronization

**Test ID:** TC_NTP_AUTHWF_005
**Priority:** High
**Test Type:** Negative, Dynamic Configuration
**Platform:** VS/HW
**Status:** ❌ **BLOCKED BY BUG-NTP-002**

#### Objective

Verify that **removing** the trusted designation from an authentication key (`no ntp trusted-key <id>`) causes the NTP daemon to **stop synchronizing** with servers using that key.

This test validates the dynamic nature of trusted-key configuration and its impact on runtime synchronization.

#### Pre-conditions

1. NTP server (192.168.100.175) configured with key 1 / MD5 / `MySecret123`
2. DUT is **already synchronized** with the server using authenticated key 1
3. DUT shows `*` prefix on server in associations (confirmed sync)

#### Test Steps

**Phase 1: Establish Authenticated Synchronization**

**Step 1-6: Configure Full Authentication (Same as TC_NTP_AUTHWF_001)**
```bash
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic(config)# ntp enable
sonic(config)# ntp authentication-key 1 md5 MySecret123
sonic(config)# ntp trusted-key 1
sonic(config)# ntp authenticate
sonic(config)# ntp server 192.168.100.175 iburst key 1
sonic(config)# end
```

**Step 7: Wait for Synchronization**
```bash
sonic# ! Wait 60 seconds for sync
```

**Step 8: Verify Synchronization Established**
```bash
sonic# show ntp associations
```

**Expected Output (Pre-condition verification):**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.100.175  time4.google.   3 u   32   64  377    0.500    0.120   0.050
```
✅ **Prerequisite:** `*` prefix confirms sync is working

**Phase 2: Remove Trusted-Key Designation**

**Step 9: Untrust the Authentication Key**
```bash
sonic# configure terminal
sonic(config)# no ntp trusted-key 1
sonic(config)# end
```

⚠️ **CRITICAL ACTION:** Key 1 is no longer trusted but still exists

**Step 10: Wait for Effect to Take Place**
```bash
sonic# ! Wait 30-60 seconds for chronyd to re-evaluate trust
```

**Step 11: Check Synchronization Status**
```bash
sonic# show ntp associations
```

**Step 12: Verify Trusted Keys List**
```bash
sonic# show ntp trusted-keys
```

**Step 13: Verify Auth Key Still Exists**
```bash
sonic# show ntp authentication-keys
```

#### Expected Results

**After Step 8 (initial sync):**
```
*192.168.100.175  time4.google.   3 u   32   64  377    0.500    0.120   0.050
```
✅ Server synchronized (baseline)

**After Step 11 (untrusted key):**
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.100.175  .INIT.         16 u    8   64  377    0.000    0.000   0.000
```

**Key Changes:**
- ❌ **`*` prefix removed** - Server no longer selected
- ❌ **Stratum 16** - Server now unreachable/rejected
- ⚠️ **Reach may still be 377** - Recent polls succeeded but new polls fail
- ❌ **refid: .INIT.** - Not synchronized

**After Step 12 (show trusted-keys):**
```
Trusted Keys: (none)
```
✅ Key 1 no longer in trusted list

**After Step 13 (show auth-keys):**
```
Key ID  Type  Trusted
1       md5   no
```
✅ Key still exists but Trusted column shows "no"

#### Verification Points

✅ **Initial sync successful:** Baseline with `*` prefix established
✅ **Untrust removes sync:** `*` prefix disappears after `no ntp trusted-key`
✅ **Key still exists:** Authentication key remains in config
✅ **Only trust status changed:** Key definition unchanged
✅ **Server becomes unreachable:** Stratum 16 or similar rejection state

#### Sequence Verification

**State 1: Fully Authenticated (Before)**
```
Authentication Key: ✅ Configured
Trusted Key:        ✅ Trusted
Authentication:     ✅ Enabled
Server Sync:        ✅ Synchronized (*)
```

**State 2: After Untrusting Key**
```
Authentication Key: ✅ Still Configured
Trusted Key:        ❌ NOT Trusted
Authentication:     ✅ Still Enabled
Server Sync:        ❌ NOT Synchronized
```

#### Follow-up Test: Re-trusting Key Restores Sync

**Step 14: Re-trust the Key**
```bash
sonic(config)# ntp trusted-key 1
sonic(config)# end
sonic# ! Wait 30-60 seconds
sonic# show ntp associations
```

**Expected:** Server should resync and show `*` prefix again

This proves:
1. Untrusting broke sync (not other factors)
2. Trust designation is dynamically evaluated
3. Configuration is reversible

#### Cleanup

```bash
sonic(config)# no ntp server 192.168.100.175
sonic(config)# no ntp authenticate
sonic(config)# no ntp trusted-key 1  # May already be removed
sonic(config)# no ntp authentication-key 1
sonic(config)# no ntp enable
```

#### Success Criteria

- ✅ Initial synchronization with trusted key works
- ✅ Removing trusted designation breaks synchronization
- ✅ Server shows stratum 16 or no `*` prefix
- ✅ Authentication key still exists (only trust status changed)
- ✅ Re-trusting key restores synchronization

#### Timing Considerations

**NTP Poll Intervals:**
- Initial poll: 64 seconds (typical)
- Minimum poll: 16 seconds
- Maximum poll: 1024 seconds

**Expected Timeline:**
- Untrust key: Immediate config change
- Effect visible: 30-120 seconds (depends on poll cycle)
- Full convergence: 2-3 minutes

**Recommendation:** Wait at least 60 seconds between untrusting and checking associations.

#### Known Issues

⚠️ **BUG-NTP-002:** Cannot establish initial sync (test prerequisite blocked)
⚠️ **BUG-NTP-001:** Cannot remove server for cleanup

#### Test Variations

**Variation 1: Untrust while authentication disabled**
```bash
sonic(config)# no ntp authenticate
sonic(config)# no ntp trusted-key 1
```
Verify sync continues (authentication not enforced)

**Variation 2: Multiple keys**
```bash
sonic(config)# ntp trusted-key 1
sonic(config)# ntp trusted-key 2
sonic(config)# ntp server 192.168.100.10 key 1
sonic(config)# ntp server 192.168.100.20 key 2
sonic(config)# no ntp trusted-key 1
```
Verify only server 1 loses sync, server 2 continues.

---

## Common Verification Steps

These verification steps apply to all authentication workflow test cases.

### Verify NTP Service Running

```bash
# Check chronyd process
admin@sonic:~$ ps aux | grep chronyd
_chrony   12345  0.0  0.0  18896  3240 ?  S  10:00  0:00 /usr/sbin/chronyd -F 1

# Check service status
admin@sonic:~$ sudo systemctl status chrony
● chrony.service - chrony, an NTP client/server
   Active: active (running)
```

### Verify Network Connectivity

```bash
# Ping NTP server
admin@sonic:~$ ping -c 4 192.168.100.175
4 packets transmitted, 4 received, 0% packet loss

# Check port 123 reachable (if nc available)
admin@sonic:~$ nc -zv 192.168.100.175 123
Connection to 192.168.100.175 123 port [udp/ntp] succeeded!
```

### Verify Configuration in CONFIG_DB

```bash
# Check NTP configuration in Redis
admin@sonic:~$ redis-cli -n 4 KEYS "NTP*"
1) "NTP|global"
2) "NTP_SERVER|192.168.100.175"
3) "NTP_KEY|1"

# Get server details
admin@sonic:~$ redis-cli -n 4 HGETALL "NTP_SERVER|192.168.100.175"
1) "iburst"
2) "on"
3) "key"
4) "1"
5) "admin_state"
6) "enabled"

# Get key details
admin@sonic:~$ redis-cli -n 4 HGETALL "NTP_KEY|1"
1) "type"
2) "md5"
3) "password"
4) "MySecret123"
5) "trusted"
6) "yes"
```

### Verify via Syslog

```bash
# Monitor NTP configuration changes
admin@sonic:~$ sudo tail -f /var/log/syslog | grep -i ntp

# Expected log entries:
# hostcfgd: NtpCfg: Server/key configuration update
# chronyd: Selected source 192.168.100.175
# mgmt-framework#klish: User "admin" command "ntp server..." status - success
```

### Verify Chrony Configuration Files

```bash
# Check chrony.conf
admin@sonic:~$ sudo cat /etc/chrony/chrony.conf | grep -A 5 "server\|key"

# Check chrony.keys (if created)
admin@sonic:~$ sudo cat /etc/chrony/chrony.keys
# May not be used for client auth in current implementation
```

### Check Chrony Sources Directly

```bash
# Query chrony daemon
admin@sonic:~$ chronyc sources -v

# Check authentication data
admin@sonic:~$ sudo chronyc authdata
```

---

## Known Issues and Workarounds

### BUG-NTP-002: Authentication Key Validation Blocks Server Configuration (CRITICAL)

**Issue:** `ntp server <ip> key <id>` fails with `%Error: Invalid authentication key configuration` even with correct password.

**Impact:** ❌ **BLOCKS ALL 5 AUTHENTICATION WORKFLOW TESTS**

**Error Message:**
```
sonic(config)# ntp server 192.168.100.175 iburst key 1
%Error: Invalid authentication key configuration
```

**Root Cause:** IS-CLI attempts real-time authentication validation against NTP server during configuration. Validation fails due to:
- Protocol mismatch (NTPv4 vs chrony handshake)
- Timeout during validation
- Incorrect validation logic

**Workaround:** None for IS-CLI. Alternative approaches:
1. **Backend Testing:** Configure directly in CONFIG_DB
2. **Bug Fix:** Wait for development team to fix
3. **Non-Auth Tests:** Proceed with tests that don't require auth keys

**Status:** OPEN - Escalate to development team

**Detailed Analysis:** [NTP_AUTHENTICATION_TESTING_ANALYSIS.md](../report/NTP_AUTHENTICATION_TESTING_ANALYSIS.md)

---

### BUG-NTP-003: Internal Error on Configuration Commit (MEDIUM)

**Issue:** `end` command shows `%Error: Internal error` but configuration actually applies.

**Impact:** ⚠️ Confusing UX, but not a functional blocker

**Error Message:**
```
sonic(config)# end
%Error: Internal error.
sonic(config)#  ← Still in config mode
```

**Evidence Configuration Works:**
```bash
# Syslog shows success
2026 Apr  9 06:36:16 sonic INFO hostcfgd: NtpCfg: Server/key configuration update
2026 Apr  9 06:36:22 sonic INFO chronyd: Selected source 192.168.100.175
```

**Workaround:**
1. Ignore the error message
2. Verify via syslog or backend
3. Type `end` multiple times or exit CLI and reconnect
4. Check `show ntp` commands from enable mode

**Verification:**
```bash
# Exit and reconnect
sonic(config)# exit
sonic# show ntp server
# Config should be present despite error
```

**Status:** OPEN - Should be fixed for better UX

---

### BUG-NTP-001: Server Deletion Not Working (HIGH)

**Issue:** `no ntp server <ip>` does not remove servers from configuration.

**Impact:** ❌ Cannot clean up test servers

**Evidence:**
```bash
sonic(config)# no ntp server 192.168.100.175
sonic(config)# end
sonic# show ntp server
# Server still appears ❌
```

**Workaround:**
```bash
# Manual CONFIG_DB cleanup
admin@sonic:~$ redis-cli -n 4 DEL "NTP_SERVER|192.168.100.175"
admin@sonic:~$ sudo systemctl restart chrony
```

**Status:** OPEN - Confirmed in 3 test cases

---

### BEHAVIOR-NTP-001: Config-Time Auth Validation (Reclassified as BUG-NTP-002)

**Previous Understanding:** "IS-CLI validates authentication at config time (feature)"

**Actual Understanding:** "IS-CLI validation is broken and blocks valid configs (bug)"

**See:** BUG-NTP-002 for details

---

## Script Generation Guidelines

When generating automated test scripts (Python/Expect/Bash) for these test cases:

### Script Structure

```python
# Recommended structure for each test case

def test_ntp_authwf_001():
    """TC_NTP_AUTHWF_001: MD5 Full Authentication Workflow"""

    # 1. Test Setup
    - Connect to DUT
    - Verify prerequisites
    - Clean up existing config

    # 2. Test Execution
    - Execute configuration steps
    - Capture all outputs
    - Handle known issues (BUG-NTP-002, BUG-NTP-003)

    # 3. Verification
    - Check show commands
    - Verify syslog entries
    - Validate synchronization

    # 4. Cleanup
    - Remove configuration
    - Restore initial state
    - Handle cleanup bugs (BUG-NTP-001)

    # 5. Reporting
    - Log all steps
    - Capture screenshots/outputs
    - Generate test report
```

### Handling Known Issues in Scripts

```python
# Example: Handle BUG-NTP-002
def configure_auth_server(dut, server_ip, key_id):
    """Configure NTP server with authentication key"""

    cmd = f"ntp server {server_ip} iburst key {key_id}"
    output = dut.send_command(cmd)

    if "Invalid authentication key configuration" in output:
        # BUG-NTP-002 detected
        log.warning("BUG-NTP-002: Auth key validation failed")

        # Check if config applied anyway via backend
        if check_syslog_for_success(dut):
            log.info("Config applied despite error (BUG-NTP-003 workaround)")
            return True
        else:
            log.error("Server configuration blocked by BUG-NTP-002")
            return False

    return True

# Example: Verify via syslog instead of CLI
def verify_synchronization(dut, server_ip):
    """Verify NTP synchronization via syslog"""

    # Primary method: show ntp associations
    output = dut.send_command("show ntp associations")
    if f"*{server_ip}" in output:
        return True

    # Fallback: Check syslog for sync
    syslog = dut.send_command("sudo tail -100 /var/log/syslog | grep chronyd")
    if f"Selected source {server_ip}" in syslog:
        log.info("Syslog confirms sync despite CLI issues")
        return True

    return False
```

### Test Result Classification

```python
# Classify test results considering known issues

class TestResult:
    PASS = "PASS"                    # Test passed completely
    CONDITIONAL_PASS = "COND_PASS"   # Config works but CLI shows errors
    FAIL = "FAIL"                    # Actual failure
    BLOCKED = "BLOCKED"              # Blocked by known bug
    SKIP = "SKIP"                    # Skipped due to prerequisites

def evaluate_test_result(test_case, outputs, known_bugs):
    """Determine test result considering known issues"""

    if "BUG-NTP-002" in known_bugs and test_case.requires_auth:
        return TestResult.BLOCKED

    if outputs.get("cli_error") and outputs.get("backend_success"):
        # BUG-NTP-003: Error shown but works
        return TestResult.CONDITIONAL_PASS

    if outputs.get("sync_successful"):
        return TestResult.PASS

    return TestResult.FAIL
```

### Timeouts and Waits

```python
# Recommended wait times for NTP operations

TIMEOUTS = {
    "config_apply": 5,        # Seconds to wait after config command
    "service_restart": 10,     # Seconds for chronyd to restart
    "initial_sync": 60,        # Seconds for first synchronization
    "sync_verify": 90,         # Seconds for sync verification
    "untrust_effect": 60,      # Seconds for untrust to take effect
}

# Example usage
def wait_for_sync(dut, timeout=TIMEOUTS["initial_sync"]):
    """Wait for NTP synchronization with polling"""

    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_sync_status(dut):
            return True
        time.sleep(10)  # Poll every 10 seconds

    return False
```

### Logging and Reporting

```python
# Comprehensive logging for debugging

import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'ntp_test_{test_case_id}.log'),
        logging.StreamHandler()
    ]
)

def log_command_execution(command, output, expected):
    """Log command execution details"""

    logging.info(f"Command: {command}")
    logging.debug(f"Output:\n{output}")

    if expected in output:
        logging.info("✓ Expected output found")
    else:
        logging.warning("✗ Expected output not found")
        logging.debug(f"Expected: {expected}")
```

### Expect Script Template

```tcl
#!/usr/bin/expect -f
#
# Test Case: TC_NTP_AUTHWF_001
# Description: MD5 Full Authentication Workflow
#

set timeout 60
log_file -a /tmp/tc_ntp_authwf_001_log.txt

# Variables
set dut_ip "192.168.100.147"
set ntp_server "192.168.100.175"
set auth_key_id "1"
set auth_pass "MySecret123"

# Connect
spawn ssh admin@$dut_ip
expect "password:"
send "admin_password\r"
expect -re "admin@sonic.*\\$"

# Enter KLISH
send "sonic-cli\r"
expect -re "sonic#"

send "configure terminal\r"
expect -re "sonic\\(config\\)#"

# Configure (with error handling)
send "ntp authentication-key $auth_key_id md5 $auth_pass\r"
expect {
    -re "sonic\\(config\\)#" {
        puts "✓ Auth key configured"
    }
    -re "Error" {
        puts "✗ Error configuring auth key"
        exit 1
    }
}

# ... rest of test steps ...

# Cleanup
send "no ntp enable\r"
expect -re "sonic\\(config\\)#"

send "exit\r"
expect eof

puts "\n=== Test Complete ===\n"
```

---

## Test Execution Checklist

Before running any authentication workflow test:

### Pre-Test Checklist

- [ ] NTP server (192.168.100.175) is running
- [ ] NTP server has correct authentication keys configured
- [ ] Chrony service on server shows "Loaded 5 symmetric keys"
- [ ] Network connectivity from DUT to server verified (0% packet loss)
- [ ] Port 123 is listening on NTP server
- [ ] DUT has no existing NTP configuration (clean state)
- [ ] SSH access to DUT working
- [ ] KLISH mode access verified
- [ ] Test logging/capture tools ready

### Post-Test Checklist

- [ ] All test steps executed
- [ ] All show command outputs captured
- [ ] Syslog entries reviewed
- [ ] Synchronization status verified
- [ ] Configuration cleanup attempted
- [ ] Any errors documented
- [ ] Test report generated
- [ ] Known issues noted

### Known Issues Checklist

When test fails, verify which known issue applies:

- [ ] **BUG-NTP-002:** Server with key rejected? → Test BLOCKED
- [ ] **BUG-NTP-003:** Internal error on commit? → Check syslog for actual status
- [ ] **BUG-NTP-001:** Cannot delete server? → Manual cleanup required
- [ ] **Other:** New issue discovered? → Document and report

---

## References

### Related Documents

- [NTP Test Plan](./NTP_TestPlan.md) - Complete test plan (72 test cases)
- [NTP Authentication Analysis](../report/NTP_AUTHENTICATION_TESTING_ANALYSIS.md) - Detailed bug analysis
- [NTP Server Setup Guide](../report/NTP_SERVER_SETUP_192.168.100.175.md) - Server configuration
- [Test Report README](../report/README.md) - Test execution summary

### NTP Server Details

**Server:** 192.168.100.175

**Authentication Keys:**
```
Key 1: MD5 MySecret123      (TC_NTP_AUTHWF_001, 003, 005)
Key 2: SHA256 SecurePass456 (TC_NTP_AUTHWF_004)
Key 3: SHA1 Sha1Password    (Additional testing)
Key 4: SHA512 BigSecret789  (Additional testing)
Key 5: SHA384 MediumSecret  (Additional testing)
```

**Access:**
```
SSH: claudeuser@192.168.100.175
Password: P@lC@2026
```

### Bug Tracking

| Bug ID | Title | Severity | Status | Blocker For |
|--------|-------|----------|--------|-------------|
| BUG-NTP-002 | Auth key validation blocks server config | 🔴 CRITICAL | OPEN | All 5 auth tests |
| BUG-NTP-003 | Internal error on commit | 🟡 MEDIUM | OPEN | All tests (cosmetic) |
| BUG-NTP-001 | Server deletion not working | 🔴 HIGH | OPEN | Cleanup |

---

## Document Control

**Version:** 1.0
**Created:** 2026-04-09
**Last Updated:** 2026-04-09
**Author:** Test Automation Team
**Status:** 📋 Reference Documentation - Ready for Script Generation

**Change Log:**
- 2026-04-09: Initial version with all 5 test cases documented

---

**END OF DOCUMENT**
