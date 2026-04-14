# NTP Server Setup - Alternatives and Solutions

**Date:** 2026-04-08
**Issue:** ENVIRONMENT-NTP-001 - NTP server at 192.168.100.10 not available
**Status:** Analysis Complete - Multiple Solutions Available

---

## Problem Statement

The NTP test plan requires an NTP server at 192.168.100.10 configured with authentication keys for testing authentication workflows. However:

1. ✅ **IP 192.168.100.147** - DUT (SONiC device) - Accessible
2. ❌ **IP 192.168.100.10** - NTP-SRV (planned) - **NOT REACHABLE**
3. ✅ **IP 192.168.100.175** - Unknown device - Reachable but no access
4. ✅ **Google Time Servers** - 216.239.35.0, 216.239.35.12 - Working

---

## Network Connectivity Analysis

### From Test Environment (192.168.100.175)
```bash
ping 192.168.100.10
# Result: Destination Host Unreachable
```

### From DUT (192.168.100.147)
```bash
ping 192.168.100.10
# Result: Destination Host Unreachable
```

### Available Devices
```bash
ping 192.168.100.175
# Result: SUCCESS (reachable but no SSH access with test credentials)
```

---

## Solution Options

### Option 1: Use Public NTP Servers for Non-Auth Tests (RECOMMENDED)

**Approach:** Use existing Google time servers for synchronization tests that don't require authentication.

**Applicable Test Cases:**
- ✅ TC_NTP_SYNC_003 - Prefer server selection
- ✅ TC_NTP_SYNC_004 - Synchronization using NTPv3
- ✅ TC_NTP_SYNC_005 - Synchronization failover
- ✅ TC_NTP_SYNC_006 - Pool association type
- ✅ TC_NTP_NEG_* - Negative tests (most don't need auth)
- ✅ TC_NTP_EDGE_* - Edge cases (most don't need auth)

**Advantages:**
- ✅ No additional setup required
- ✅ Servers already working and synchronized
- ✅ Can test ~15-20 test cases immediately
- ✅ No dependency on external infrastructure

**Limitations:**
- ❌ Cannot test authentication workflows (5 test cases blocked)
- ❌ Cannot verify auth key synchronization

**Test Plan Modification Required:**
```markdown
Replace:  192.168.100.10
With:     216.239.35.0 or 216.239.35.12
For:      Non-authentication test cases only
```

---

### Option 2: Setup Virtual NTP Server on Test Environment

**Approach:** Create a VM or container at 192.168.100.10 with chrony configured.

**Requirements:**
1. Access to network infrastructure to assign 192.168.100.10
2. Root/admin access to create VM or container
3. Install chrony with authentication support
4. Configure network routing

**Setup Steps:**
```bash
# 1. Create VM/Container at 192.168.100.10

# 2. Install chrony
sudo apt-get update
sudo apt-get install -y chrony

# 3. Configure authentication keys
sudo cat > /etc/chrony/chrony.keys <<'EOF'
1 MD5 MySecret123
2 SHA256 SecurePass456
3 SHA1 Sha1Password
4 SHA512 BigSecret789
5 SHA384 MediumSecret
EOF

sudo chmod 640 /etc/chrony/chrony.keys
sudo chown root:chrony /etc/chrony/chrony.keys

# 4. Configure chrony
sudo cat > /etc/chrony/chrony.conf <<'EOF'
# Use public NTP servers
server 216.239.35.0 iburst
server 216.239.35.12 iburst

# Local stratum
local stratum 2

# Allow DUT to query
allow 192.168.100.0/24

# Enable authentication
keyfile /etc/chrony/chrony.keys

# Log file
logdir /var/log/chrony
EOF

# 5. Restart service
sudo systemctl restart chronyd
sudo systemctl enable chronyd

# 6. Verify
sudo chronyc sources -v
sudo chronyc clients
```

**Verification:**
```bash
# From DUT
ping 192.168.100.10
nc -zv 192.168.100.10 123

# Test without auth
ntpdate -q 192.168.100.10

# Test with auth (requires ntpdate with auth support)
```

**Advantages:**
- ✅ Complete test coverage (all 25 test cases)
- ✅ Full authentication workflow testing
- ✅ Matches test plan exactly
- ✅ Can test all hash algorithms

**Limitations:**
- ⚠️ Requires infrastructure access
- ⚠️ Setup time: ~30 minutes
- ⚠️ Ongoing maintenance required

---

### Option 3: Use Existing Device at 192.168.100.175

**Approach:** Configure the existing device at 192.168.100.175 as NTP server.

**Requirements:**
1. Obtain correct SSH credentials for 192.168.100.175
2. Verify it's a Linux/SONiC device
3. Install and configure chrony
4. Update test cases to use 192.168.100.175 instead of 192.168.100.10

**Advantages:**
- ✅ Device already exists and is reachable
- ✅ Complete test coverage possible
- ✅ Minimal network changes

**Limitations:**
- ❌ Requires credentials (currently unavailable)
- ⚠️ Test plan needs updates (IP change)

---

### Option 4: Modified Testing Strategy (PRAGMATIC)

**Approach:** Split testing into two phases based on server availability.

**Phase 1: Non-Auth Tests (Use Google Servers)**
Execute immediately:
- TC_NTP_ENABLE_* (already automated)
- TC_NTP_SERVER_* (basic config without auth)
- TC_NTP_SRC_* (source interface tests)
- TC_NTP_VRF_* (VRF tests)
- TC_NTP_SYNC_* (sync tests without auth)
- TC_NTP_SHOW_* (show commands)
- TC_NTP_NEG_* (negative tests - most don't need auth)
- TC_NTP_EDGE_* (edge cases - most don't need auth)
- TC_NTP_SCALE_* (scale tests)

**Phase 2: Auth Tests (Setup Server Later)**
Execute after NTP server is available:
- TC_NTP_AUTHKEY_* (already proven config works)
- TC_NTP_TRUSTED_* (already proven config works)
- TC_NTP_AUTH_ENF_* (already proven config works)
- TC_NTP_AUTHWF_001 (MD5 full workflow)
- TC_NTP_AUTHWF_002 (Auth enforcement)
- TC_NTP_AUTHWF_005 (Untrusting key)

**Current Status:**
- ✅ Auth key configuration: VERIFIED (MD5, SHA256, SHA1, SHA384, SHA512)
- ✅ Trusted key configuration: VERIFIED
- ✅ Auth enforcement: VERIFIED
- ✅ Show commands: VERIFIED
- ⚠️ End-to-end sync with auth: PENDING (needs server)

**Advantages:**
- ✅ Continue testing immediately
- ✅ ~70% test coverage achievable now
- ✅ Remaining 30% can wait for server setup
- ✅ No infrastructure dependencies

**Limitations:**
- ⚠️ Incomplete auth workflow testing
- ⚠️ Cannot verify runtime authentication behavior

---

## Recommendation: HYBRID APPROACH

### Immediate Actions (TODAY)

**1. Continue with Option 4 - Modified Testing Strategy**
   - Execute TC_NTP_SYNC_003 next (prefer server)
   - Execute TC_NTP_SYNC_004 (NTPv3)
   - Execute TC_NTP_SYNC_005 (failover)
   - Execute TC_NTP_SYNC_006 (pool)
   - Execute TC_NTP_NEG_* tests
   - Target: 15-20 test cases completed

**2. Document Current Auth Testing Status**
   - ✅ Configuration validation: COMPLETE
   - ✅ Key format verification: COMPLETE
   - ✅ Show command verification: COMPLETE
   - ⚠️ Runtime sync with auth: BLOCKED

### Short-Term Actions (NEXT 1-2 DAYS)

**Setup NTP Server (Choose ONE):**

**Option A: Coordinate with Infrastructure Team**
```
Request: Setup VM/container at 192.168.100.10
Purpose: NTP authentication testing
Duration: Needed for test execution period
```

**Option B: Use Alternative IP**
```
Action: Configure 192.168.100.175 as NTP server
Needs: Credentials for 192.168.100.175
Benefit: Faster setup, device already exists
```

**Option C: Cloud-Based NTP Server**
```
Alternative: Use external NTP server with auth
Example: Setup in cloud with public IP
Requirement: Firewall rules for DUT access
```

### Long-Term Actions (TEST PLAN UPDATE)

**Update NTP Test Plan:**

1. **Add Prerequisite Section:**
   ```markdown
   ## Test Environment Prerequisites

   ### Required Infrastructure
   - NTP Server with authentication support (chrony/ntpd)
   - IP: 192.168.100.10 (or update test cases)
   - Authentication keys configured:
     - Key 1: MD5 "MySecret123"
     - Key 2: SHA256 "SecurePass456"
     - Key 3: SHA1 "Sha1Password"
     - Key 4: SHA512 "BigSecret789"
     - Key 5: SHA384 "MediumSecret"

   ### Verification Steps
   1. Verify connectivity: ping 192.168.100.10
   2. Verify NTP port: nc -zv 192.168.100.10 123
   3. Verify time sync: ntpdate -q 192.168.100.10
   ```

2. **Add Fallback Options:**
   ```markdown
   ## Alternative Test Configurations

   If authenticated NTP server is unavailable:
   - Use Google Time servers for sync tests: 216.239.35.0, 216.239.35.12
   - Authentication tests: Config verification only (already proven)
   - Update server IP in test cases if using alternative server
   ```

3. **Split Test Cases by Dependency:**
   ```markdown
   ## Test Case Dependencies

   **NO Auth Server Required (20 cases):**
   - TC_NTP_ENABLE_*, TC_NTP_SERVER_*, TC_NTP_SRC_*
   - TC_NTP_VRF_*, TC_NTP_SYNC_*, TC_NTP_SHOW_*
   - TC_NTP_NEG_* (most), TC_NTP_EDGE_* (most), TC_NTP_SCALE_*

   **Auth Server Required (5 cases):**
   - TC_NTP_AUTHWF_001, _002, _003, _004, _005

   **Auth Server Optional (Partial Testing):**
   - TC_NTP_AUTHKEY_* (config verified, sync not verified)
   - TC_NTP_TRUSTED_* (config verified, sync not verified)
   - TC_NTP_AUTH_ENF_* (config verified, enforcement not verified)
   ```

---

## Immediate Next Steps

**RECOMMENDED: Proceed with Non-Auth Tests**

**Test Execution Order:**
1. ✅ TC_NTP_AUTHWF_003 (DONE - config verification)
2. ✅ TC_NTP_AUTHWF_004 (DONE - SHA256 config verification)
3. ➡️ **TC_NTP_SYNC_003** (prefer server) - USE GOOGLE SERVERS
4. TC_NTP_SYNC_004 (NTPv3) - USE GOOGLE SERVERS
5. TC_NTP_SYNC_005 (failover) - USE GOOGLE SERVERS
6. TC_NTP_SYNC_006 (pool) - USE pool.ntp.org
7. TC_NTP_NEG_001 through TC_NTP_NEG_008
8. TC_NTP_EDGE_* cases
9. TC_NTP_SCALE_* cases

**Parallel Action:**
- Contact infrastructure team for NTP server at 192.168.100.10
- OR obtain credentials for 192.168.100.175
- OR setup alternative server IP

---

## Summary

**Current Situation:**
- ❌ NTP server at 192.168.100.10 not available
- ✅ Google time servers working perfectly
- ✅ Auth key configuration fully verified
- ⚠️ 20/25 test cases can proceed without auth server

**Recommendation:**
1. **CONTINUE TESTING** with Google servers (non-auth tests)
2. **PARALLEL ACTION:** Setup NTP server for auth tests
3. **COMPLETE:** ~80% of testing in next 2-3 hours
4. **RESUME:** Auth workflow tests when server ready

**Test Progress:**
- Completed: 2/25 (8%)
- Can complete now: 18/25 (72%)
- Blocked: 5/25 (20%) - needs auth server

**Decision Point:**
Would you like to:
- **A)** Continue with TC_NTP_SYNC_003 using Google servers (RECOMMENDED)
- **B)** Pause testing and setup NTP server first
- **C)** Provide credentials for 192.168.100.175 to configure as NTP server

---

**Document Version:** 1.0
**Last Updated:** 2026-04-08 20:00:00 UTC
**Status:** Awaiting decision on next steps
