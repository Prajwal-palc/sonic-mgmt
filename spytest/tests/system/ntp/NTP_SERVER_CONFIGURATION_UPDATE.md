# NTP Server Configuration Update

**Date**: 2026-04-10
**Author**: Athira
**Issue**: NTP tests failing due to unreachable NTP server (192.168.100.175)
**Solution**: Updated to use Google Public NTP server (216.239.35.0)

---

## Problem Summary

Your comprehensive NTP test run was failing with errors like:
```
Failed to configure NTP server 192.168.100.175
```

**Root Cause**: The NTP server IP `192.168.100.175` configured in the test variables was not reachable from the DUT, causing all authentication and server configuration tests to fail.

---

## Changes Made

### 1. Updated NTP Server Configuration

#### File: `vars_ntp_comprehensive.yaml`

**Before**:
```yaml
servers:
  test_server_1: "192.168.100.175"
  test_server_2: "216.239.35.0"
```

**After**:
```yaml
servers:
  # Primary test server: Google Public NTP (always reachable)
  test_server_1: "216.239.35.0"  # time.google.com - Google Public NTP
  test_server_2: "216.239.35.4"  # time2.google.com - Google Public NTP
  # Local test server (may not be reachable in all environments)
  local_test_server: "192.168.100.175"  # Use only if local NTP server is set up
```

#### File: `vars_ntp_persistence.yaml`

**Before**:
```yaml
defaults:
  test_server: "192.168.100.175"  # Replace with actual NTP server
```

**After**:
```yaml
defaults:
  # Test NTP server - Google Public NTP (always reachable)
  test_server: "216.239.35.0"  # time.google.com - Google Public NTP

  # Alternative public NTP servers (for fallback)
  fallback_servers:
    - "0.pool.ntp.org"
    - "time.google.com"
    - "216.239.35.4"  # time2.google.com

  # Local test server (use only if you have local NTP server set up)
  local_test_server: "192.168.100.175"  # Optional local NTP server
```

#### File: `verify_ntp_server.sh`

**Before**:
```bash
NTP_SERVER="192.168.100.175"
```

**After**:
```bash
NTP_SERVER="${NTP_SERVER:-216.239.35.0}"  # Default to Google Public NTP (time.google.com)
NTP_SERVER_ALT="216.239.35.4"  # Alternative Google NTP (time2.google.com)
```

Now supports environment variable override:
```bash
# Use default (Google NTP)
./verify_ntp_server.sh

# Use custom NTP server
NTP_SERVER=192.168.100.175 ./verify_ntp_server.sh
```

---

### 2. Created New Validation Script

**File**: `validate_ntp_server.sh` ✨ NEW

A comprehensive NTP server validation script that tests:
1. Network reachability (ICMP ping)
2. NTP port accessibility (UDP 123)
3. NTP protocol query (actual NTP request)

**Usage**:
```bash
# Validate default Google NTP server
./validate_ntp_server.sh

# Validate custom NTP server
./validate_ntp_server.sh 192.168.100.175

# Validate and exit with status code
if ./validate_ntp_server.sh 216.239.35.0; then
    echo "Server is valid!"
else
    echo "Server is invalid!"
fi
```

**Output Example**:
```
=========================================
NTP Server Validation
=========================================
NTP Server: 216.239.35.0
Timeout: 5s

[Test 1/3] Testing network reachability...
✓ NTP server 216.239.35.0 is reachable via ICMP

[Test 2/3] Testing NTP port accessibility...
✓ NTP port 123 is accessible on 216.239.35.0

[Test 3/3] Testing NTP protocol query...
✓ NTP server 216.239.35.0 responds to NTP queries

=========================================
Validation Summary
=========================================
NTP Server: 216.239.35.0
Status: ✓ VALID - Server is reachable and responding
```

---

### 3. Documented Scalable Test Cases

**File**: `NTP_SCALE_TEST_CASES.md` ✨ NEW

Created comprehensive documentation for NTP scale test cases:

| Test Case | Status | Priority |
|-----------|--------|----------|
| TC_NTP_SCALE_001: Max servers (10) | ✅ Automated | P1 |
| TC_NTP_SCALE_002: Max auth keys | ⏳ Pending | P2 |
| TC_NTP_SCALE_003: Rapid enable/disable | ⏳ Pending | P2 |
| TC_NTP_SCALE_004: Concurrent config | ⏳ Pending | P2 |
| TC_NTP_SCALE_005: High-freq packet inject | ⏳ Pending | P3 |

**Completion**: 1/5 (20%)

The document includes:
- Detailed test descriptions
- Implementation guidelines
- Example code for automation
- Platform support notes

---

## Google Public NTP Servers

Google provides free, globally distributed NTP servers:

| IP Address | Hostname | Notes |
|------------|----------|-------|
| 216.239.35.0 | time.google.com | Primary (used in tests) |
| 216.239.35.4 | time2.google.com | Secondary |
| 216.239.35.8 | time3.google.com | Tertiary |
| 216.239.35.12 | time4.google.com | Quaternary |

**Benefits**:
- ✅ Always reachable (global Anycast)
- ✅ Highly accurate (Google's atomic clocks)
- ✅ High availability (99.99%+ uptime)
- ✅ Low latency (distributed worldwide)
- ✅ Free to use
- ✅ Supports NTS (NTP over TLS) for secure time sync

**Documentation**: https://developers.google.com/time

---

## How to Use Local NTP Server (Optional)

If you prefer to use a local NTP server (192.168.100.175), follow these steps:

### 1. Set Up Local NTP Server

```bash
# On the NTP server machine (192.168.100.175)
cd tests/system/ntp
sudo ./setup_ntp_server.sh
```

This script will:
- Install chrony NTP server
- Configure it to serve time
- Allow connections from DUT network (192.168.100.0/24)
- Set up authentication keys for testing

### 2. Verify NTP Server

```bash
# Verify server is working
./verify_ntp_server.sh

# Or validate specific server
./validate_ntp_server.sh 192.168.100.175
```

### 3. Update Test Variables

If using local server, update vars files:

```yaml
# vars_ntp_comprehensive.yaml
servers:
  test_server_1: "192.168.100.175"  # Your local server
  test_server_2: "216.239.35.0"     # Fallback to Google
```

### 4. Fix Issues (If Any)

```bash
# If server has issues, run fix script
sudo ./fix_ntp_server.sh
```

---

## Running Tests with New Configuration

### Run All Comprehensive Tests

```bash
./bin/spytest --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
  system/ntp/test_ntp_comprehensive.py \
  --logs-path ./logs/NTP_Comprehensive_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Run Specific Test Classes

```bash
# Run only authentication tests
./bin/spytest --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
  system/ntp/test_ntp_comprehensive.py::TestNTPAuthentication \
  --logs-path ./logs/NTP_Auth_$(date +%F_%H%M%S)

# Run only negative tests (faster, ~2 hours)
./bin/spytest --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
  system/ntp/test_ntp_comprehensive.py::TestNTPNegativeTests \
  --logs-path ./logs/NTP_Neg_$(date +%F_%H%M%S)
```

### Run Traffic Tests

```bash
./bin/spytest --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
  system/ntp/test_ntp_traffic.py \
  --logs-path ./logs/NTP_Traffic_$(date +%F_%H%M%S)
```

### Run Persistence Tests

```bash
./bin/spytest --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
  system/ntp/test_ntp_persistence.py \
  --logs-path ./logs/NTP_Persist_$(date +%F_%H%M%S)
```

---

## Expected Test Results After Update

With the new Google NTP server (216.239.35.0), tests should now:

### ✅ Should PASS:
- All negative tests (NEG_001-008)
- Show command tests (SHOW_003)
- Traffic validation tests (TRAFFIC_001-007)
- Most authentication tests (if auth is supported)
- Persistence tests (PERSIST_001-003)

### ⚠ May Still FAIL:
- **VRF tests**: If mgmt VRF is not properly configured
  - `test_ntp_vrf_mgmt_configuration`
  - `test_ntp_vrf_switch_mgmt_to_default`

- **Authentication tests with key binding**: Known limitation - servers must be deleted and re-added to bind auth keys
  - `test_ntp_auth_enforcement_without_trusted_key`
  - `test_ntp_complete_auth_workflow_md5`
  - `test_ntp_delete_auth_key_with_active_server`

### 🔧 Workaround for Authentication Tests

If authentication tests fail with "Failed to configure NTP server", the test code already handles this by:
1. Attempting to configure server with auth key
2. If fails, delete server
3. Re-add server without auth key first
4. Then configure auth key binding separately

---

## Test Execution Time Estimates

| Test Suite | Number of Tests | Estimated Time (HW) | Estimated Time (VS) |
|------------|-----------------|---------------------|---------------------|
| Comprehensive | 21 tests | 6-8 hours | 4-6 hours |
| Traffic | 7 tests | 2-3 hours | 1.5-2 hours |
| Persistence | 3 tests | 30-45 min | 20-30 min |
| Negative Tests Only | 8 tests | 2-3 hours | 1.5-2 hours |

**Why so long?**
- Each test includes comprehensive setup/teardown
- Cleanup deletes all NTP config (30+ auth keys × 2-3s each)
- Tests wait for NTP operations (sync attempts, config propagation)
- Authentication tests may timeout waiting for sync

---

## Troubleshooting

### Issue: Tests still failing with "Failed to configure NTP server"

**Possible Causes**:
1. DUT cannot reach Internet (no default route)
2. Firewall blocking UDP port 123
3. DNS not working (if using hostname)

**Solutions**:
```bash
# Test from DUT
ping 216.239.35.0
ping time.google.com

# Test NTP query from DUT
ntpdate -q 216.239.35.0
chronyc sources

# Check firewall
sudo iptables -L -n | grep 123
```

### Issue: VRF tests failing

**Cause**: mgmt VRF may not be configured on DUT

**Solution**:
```bash
# On DUT, check if mgmt VRF exists
show vrf

# If mgmt VRF doesn't exist, create it (if supported)
config vrf add mgmt
```

---

## Files Modified

1. ✏️ `vars_ntp_comprehensive.yaml` - Updated NTP server IPs
2. ✏️ `vars_ntp_persistence.yaml` - Updated NTP server IPs
3. ✏️ `verify_ntp_server.sh` - Added environment variable support
4. ✨ `validate_ntp_server.sh` - NEW validation script
5. ✨ `NTP_SCALE_TEST_CASES.md` - NEW scale test documentation
6. ✨ `NTP_SERVER_CONFIGURATION_UPDATE.md` - THIS document

---

## Next Steps

1. ✅ **NTP server updated** to Google Public NTP (216.239.35.0)
2. ✅ **Validation script** created for testing server reachability
3. ✅ **Scale test cases** documented (4 pending automation)
4. ⏳ **Re-run comprehensive tests** with new configuration:
   ```bash
   ./bin/spytest --testbed ./testbeds/testbed_vs_1node_ntp.yaml \
     system/ntp/test_ntp_comprehensive.py \
     --logs-path ./logs/NTP_RETEST_$(date +%F_%H%M%S) \
     --log-level debug
   ```

5. ⏳ **Automate remaining scale tests** (TC_NTP_SCALE_002-005)

---

## References

- **Google Public NTP**: https://developers.google.com/time
- **NTP Protocol**: RFC 5905
- **Chrony Documentation**: https://chrony.tuxfamily.org/
- **Scale Test Cases**: `NTP_SCALE_TEST_CASES.md`
- **Test Plan**: `doc/NTP_TestPlan.md`

---

**Status**: ✅ **READY FOR TESTING**

The NTP test suite is now configured to use publicly accessible Google NTP servers. Re-run your tests and they should no longer fail due to unreachable NTP server.
