# NTP Test Cases - Pending Execution List

**Date:** 2026-04-09
**Total Test Cases:** 72
**Completed:** 2 (TC_NTP_AUTHWF_003, TC_NTP_AUTHWF_004 - Config validation only)
**Blocked:** 5 (All authentication workflows - BUG-NTP-002)
**Ready to Proceed:** 65

---

## Test Execution Status Summary

| Category | Total | Completed | Blocked | Ready | Priority |
|----------|-------|-----------|---------|-------|----------|
| Enable/Disable | 3 | 0 | 0 | 3 | ⭐⭐⭐ HIGH |
| Server Configuration | 10 | 0 | 0 | 10 | ⭐⭐⭐ HIGH |
| Auth Keys (Config Only) | 7 | 0 | 0 | 7 | ⭐⭐ MEDIUM |
| Trusted Keys (Config Only) | 4 | 0 | 0 | 4 | ⭐⭐ MEDIUM |
| Auth Enforcement | 3 | 0 | 0 | 3 | ⭐⭐ MEDIUM |
| **Auth Workflows (E2E)** | **5** | **0** | **5** | **0** | **❌ BLOCKED** |
| Source Interface | 6 | 0 | 0 | 6 | ⭐⭐ MEDIUM |
| VRF Binding | 4 | 0 | 0 | 4 | ⭐ LOW |
| Show Commands | 5 | 0 | 0 | 5 | ⭐⭐⭐ HIGH |
| **Synchronization** | **6** | **0** | **0** | **6** | **⭐⭐⭐ HIGH** |
| Traffic Analysis | 7 | 0 | 0 | 7 | ⭐ LOW |
| Persistence | 4 | 0 | 0 | 4 | ⭐⭐ MEDIUM |
| Negative Tests | 8 | 0 | 0 | 8 | ⭐⭐ MEDIUM |
| Scale Tests | 5 | 0 | 0 | 5 | ⭐ LOW |
| Edge Cases | 5 | 0 | 0 | 5 | ⭐ LOW |

---

## Priority 1: HIGH PRIORITY - Can Execute Now (24 Test Cases)

These tests are critical and can be executed immediately without authentication.

### Category A: Enable/Disable (3 tests) ⭐⭐⭐

| Test ID | Test Name | Platform | Estimated Time | Notes |
|---------|-----------|----------|----------------|-------|
| **TC_NTP_ENABLE_001** | Enable NTP service | VS | 2 min | Basic functionality |
| **TC_NTP_ENABLE_002** | Disable NTP service | VS | 2 min | Basic functionality |
| **TC_NTP_ENABLE_003** | Re-enable without re-config | VS | 3 min | State persistence |

**Prerequisites:**
- Clean DUT state
- No NTP servers required

**Quick Test Commands:**
```bash
sonic(config)# ntp enable
sonic(config)# end
sonic# show ntp global
# Verify Enabled: True

sonic(config)# no ntp enable
sonic# show ntp global
# Verify Enabled: False
```

---

### Category B: Server Configuration (10 tests) ⭐⭐⭐

| Test ID | Test Name | Platform | Estimated Time | Server Required |
|---------|-----------|----------|----------------|-----------------|
| **TC_NTP_SERVER_001** | Add NTP server (IPv4) | VS | 3 min | 192.168.100.175 or Google |
| **TC_NTP_SERVER_002** | Add NTP server (IPv6) | VS | 3 min | IPv6 server needed |
| **TC_NTP_SERVER_003** | Add server with version 3 | VS | 3 min | Any server |
| **TC_NTP_SERVER_004** | Add server with pool type | VS | 3 min | pool.ntp.org |
| **TC_NTP_SERVER_005** | Add server with iburst | VS | 3 min | Any server |
| **TC_NTP_SERVER_006** | Add server with prefer | VS | 3 min | Any server |
| **TC_NTP_SERVER_007** | Add and remove server | VS | 4 min | ⚠️ BUG-NTP-001 |
| **TC_NTP_SERVER_008** | Multiple servers | VS | 4 min | Multiple servers |
| **TC_NTP_SERVER_009** | All options combined | VS | 4 min | Any server |
| **TC_NTP_SERVER_010** | Server with FQDN | VS/HW | 4 min | time.google.com |

**Recommended Test Servers:**
```
Primary:   192.168.100.175 (our configured server)
Backup:    216.239.35.0 (time1.google.com)
           216.239.35.12 (time2.google.com)
Pool:      pool.ntp.org
FQDN:      time.google.com
```

**Known Issue:** TC_NTP_SERVER_007 will fail at deletion step (BUG-NTP-001)

---

### Category C: Show Commands (5 tests) ⭐⭐⭐

| Test ID | Test Name | Platform | Estimated Time | Prerequisites |
|---------|-----------|----------|----------------|---------------|
| **TC_NTP_SHOW_001** | show ntp global | VS | 2 min | Any NTP config |
| **TC_NTP_SHOW_002** | show ntp server | VS | 2 min | Server configured |
| **TC_NTP_SHOW_003** | show ntp associations (active) | VS/HW | 4 min | Active sync |
| **TC_NTP_SHOW_004** | show ntp associations (disabled) | VS | 2 min | NTP disabled |
| **TC_NTP_SHOW_005** | show ntp associations (multiple) | VS/HW | 4 min | Multiple servers |

**Simple Verification:**
```bash
sonic# show ntp global
sonic# show ntp server
sonic# show ntp associations
sonic# show ntp status
sonic# show ntp authentication-keys
sonic# show ntp trusted-keys
```

---

### Category D: Synchronization Tests (6 tests) ⭐⭐⭐

**RECOMMENDED: START HERE - Most valuable tests**

| Test ID | Test Name | Platform | Estimated Time | Server | Priority |
|---------|-----------|----------|----------------|--------|----------|
| **TC_NTP_SYNC_001** | Basic sync IPv4 | VS/HW | 5 min | 192.168.100.175 | 🌟 **START** |
| **TC_NTP_SYNC_002** | Sync with iburst | VS/HW | 5 min | 192.168.100.175 | 🌟 **START** |
| **TC_NTP_SYNC_003** | Prefer server selection | VS/HW | 6 min | Multiple servers | ⭐⭐⭐ |
| **TC_NTP_SYNC_004** | Sync using NTPv3 | VS/HW | 5 min | 192.168.100.175 | ⭐⭐⭐ |
| **TC_NTP_SYNC_005** | Failover to secondary | VS/HW | 8 min | 2 servers | ⭐⭐⭐ |
| **TC_NTP_SYNC_006** | Pool association | VS/HW | 6 min | pool.ntp.org | ⭐⭐⭐ |

**Why Start Here:**
- Most important functionality (time sync)
- No authentication required
- Uses available NTP server (192.168.100.175)
- Validates end-to-end NTP operation
- Good test coverage (basic to advanced)

**Test Sequence:**
```
1. TC_NTP_SYNC_001: Verify basic sync works
2. TC_NTP_SYNC_002: Verify iburst improves sync speed
3. TC_NTP_SYNC_003: Verify prefer flag works
4. TC_NTP_SYNC_004: Verify NTPv3 compatibility
5. TC_NTP_SYNC_005: Verify failover mechanism
6. TC_NTP_SYNC_006: Verify pool support
```

---

## Priority 2: MEDIUM PRIORITY - Config Validation (27 Test Cases)

These tests verify configuration commands work correctly (without full sync testing).

### Category E: Authentication Keys - Config Only (7 tests) ⭐⭐

| Test ID | Test Name | Platform | Time | Notes |
|---------|-----------|----------|------|-------|
| **TC_NTP_AUTHKEY_001** | Create key MD5 | VS | 2 min | Config verification |
| **TC_NTP_AUTHKEY_002** | Create key SHA1 | VS | 2 min | Already verified ✅ |
| **TC_NTP_AUTHKEY_003** | Create key SHA256 | VS | 2 min | Already verified ✅ |
| **TC_NTP_AUTHKEY_004** | Create key SHA384/512 | VS | 3 min | Config verification |
| **TC_NTP_AUTHKEY_005** | Update existing key | VS | 3 min | Re-configure same ID |
| **TC_NTP_AUTHKEY_006** | Delete auth key | VS | 2 min | Config removal |
| **TC_NTP_AUTHKEY_007** | Boundary key IDs | VS | 3 min | Key ID 1, 65535 |

**Note:** These tests verify CONFIG only (show commands, running-config). Full authentication workflow blocked by BUG-NTP-002.

---

### Category F: Trusted Keys - Config Only (4 tests) ⭐⭐

| Test ID | Test Name | Platform | Time | Notes |
|---------|-----------|----------|------|-------|
| **TC_NTP_TRUSTED_001** | Designate key as trusted | VS | 2 min | Config verification |
| **TC_NTP_TRUSTED_002** | Trust multiple keys | VS | 3 min | Multiple trusted |
| **TC_NTP_TRUSTED_003** | Revoke trust | VS | 2 min | Config removal |
| **TC_NTP_TRUSTED_004** | Boundary key IDs | VS | 3 min | Trust key 1, 65535 |

---

### Category G: Authentication Enforcement (3 tests) ⭐⭐

| Test ID | Test Name | Platform | Time | Notes |
|---------|-----------|----------|------|-------|
| **TC_NTP_AUTH_ENF_001** | Enable auth enforcement | VS | 2 min | Config verification |
| **TC_NTP_AUTH_ENF_002** | Disable auth enforcement | VS | 2 min | Config verification |
| **TC_NTP_AUTH_ENF_003** | Enable/disable cycle | VS | 3 min | State toggle |

---

### Category H: Source Interface (6 tests) ⭐⭐

| Test ID | Test Name | Platform | Time | Prerequisites |
|---------|-----------|----------|------|---------------|
| **TC_NTP_SRC_001** | Source = Management0 | VS/HW | 3 min | Mgmt interface |
| **TC_NTP_SRC_002** | Source = Loopback0 | VS | 3 min | Loopback created |
| **TC_NTP_SRC_003** | Source = Ethernet0 | VS/HW | 3 min | Ethernet interface |
| **TC_NTP_SRC_004** | Source = Vlan | VS | 4 min | VLAN created |
| **TC_NTP_SRC_005** | Remove source interface | VS | 2 min | Config removal |
| **TC_NTP_SRC_006** | Verify source IP in packets | VS/HW | 5 min | Packet capture |

---

### Category I: Persistence (4 tests) ⭐⭐

| Test ID | Test Name | Platform | Time | Notes |
|---------|-----------|----------|------|-------|
| **TC_NTP_PERSIST_001** | Config save + restart | VS/HW | 5 min | Config persistence |
| **TC_NTP_PERSIST_002** | System reboot | HW | 10 min | HW only |
| **TC_NTP_PERSIST_003** | show running-config | VS | 2 min | Config accuracy |
| **TC_NTP_PERSIST_004** | Daemon restart | VS/HW | 4 min | Resume sync |

---

### Category J: Negative Tests (8 tests) ⭐⭐

| Test ID | Test Name | Platform | Time | Expected Result |
|---------|-----------|----------|------|-----------------|
| **TC_NTP_NEG_001** | Enable with no server | VS | 2 min | Should work |
| **TC_NTP_NEG_002** | Remove non-existent server | VS | 2 min | Error or ignore |
| **TC_NTP_NEG_003** | Invalid key ID | VS | 2 min | Error message |
| **TC_NTP_NEG_004** | Trust undefined key | VS | 2 min | Error message |
| **TC_NTP_NEG_005** | Server key = undefined | VS | 2 min | Error message |
| **TC_NTP_NEG_006** | Delete referenced key | VS | 3 min | Error or cascade |
| **TC_NTP_NEG_007** | Invalid VRF name | VS | 2 min | Error message |
| **TC_NTP_NEG_008** | Non-existent interface | VS | 2 min | Error message |

---

## Priority 3: LOW PRIORITY - Advanced Testing (19 Test Cases)

### Category K: VRF Binding (4 tests) ⭐

| Test ID | Test Name | Platform | Time | Notes |
|---------|-----------|----------|------|-------|
| TC_NTP_VRF_001 | Bind to mgmt VRF | VS/HW | 4 min | VRF support |
| TC_NTP_VRF_002 | Bind to default VRF | VS | 3 min | Default VRF |
| TC_NTP_VRF_003 | Change VRF while running | VS/HW | 5 min | Dynamic change |
| TC_NTP_VRF_004 | Remove VRF binding | VS | 3 min | Config removal |

---

### Category L: Traffic Analysis (7 tests) ⭐

Requires packet capture (tcpdump/Wireshark or Scapy)

| Test ID | Test Name | Platform | Time |
|---------|-----------|----------|------|
| TC_NTP_TRAFFIC_001 | Verify UDP port 123 | VS/HW | 4 min |
| TC_NTP_TRAFFIC_002 | Verify NTP version | VS/HW | 4 min |
| TC_NTP_TRAFFIC_003 | Verify source IP | VS/HW | 5 min |
| TC_NTP_TRAFFIC_004 | Verify client mode 3 | VS/HW | 4 min |
| TC_NTP_TRAFFIC_005 | Verify server mode 4 | VS/HW | 4 min |
| TC_NTP_TRAFFIC_006 | Verify iburst packets | VS/HW | 5 min |
| TC_NTP_TRAFFIC_007 | Traffic stops after disable | VS/HW | 4 min |

---

### Category M: Scale Tests (5 tests) ⭐

| Test ID | Test Name | Platform | Time |
|---------|-----------|----------|------|
| TC_NTP_SCALE_001 | Max servers | VS | 5 min |
| TC_NTP_SCALE_002 | Max auth keys | VS | 5 min |
| TC_NTP_SCALE_003 | Rapid enable/disable | VS | 4 min |
| TC_NTP_SCALE_004 | Concurrent config | VS | 5 min |
| TC_NTP_SCALE_005 | High-freq packet inject | VS/HW | 6 min |

---

### Category N: Edge Cases (5 tests) ⭐

| Test ID | Test Name | Platform | Time |
|---------|-----------|----------|------|
| TC_NTP_EDGE_001 | Server key before key defined | VS | 3 min |
| TC_NTP_EDGE_002 | Change key type for trusted | VS | 3 min |
| TC_NTP_EDGE_003 | VRF change while synced | VS/HW | 5 min |
| TC_NTP_EDGE_004 | Interface removal while synced | VS/HW | 5 min |
| TC_NTP_EDGE_005 | Server removal, fallback | VS/HW | 6 min |

---

## ❌ BLOCKED - Authentication Workflows (5 Test Cases)

**Cannot Execute Until BUG-NTP-002 is Fixed**

| Test ID | Test Name | Status | Blocker |
|---------|-----------|--------|---------|
| TC_NTP_AUTHWF_001 | MD5 full auth workflow | ❌ BLOCKED | BUG-NTP-002 |
| TC_NTP_AUTHWF_002 | Auth enforcement blocks unauth | ❌ BLOCKED | BUG-NTP-002 |
| TC_NTP_AUTHWF_003 | Wrong password prevents sync | ❌ BLOCKED | BUG-NTP-002 |
| TC_NTP_AUTHWF_004 | SHA256 full auth workflow | ❌ BLOCKED | BUG-NTP-002 |
| TC_NTP_AUTHWF_005 | Untrusting key breaks sync | ❌ BLOCKED | BUG-NTP-002 |

**Reference:** [NTP_AUTH_WORKFLOW_TEST_CASES_REFERENCE.md](../doc/NTP_AUTH_WORKFLOW_TEST_CASES_REFERENCE.md)

---

## Recommended Test Execution Plan

### Phase 1: Quick Wins (Estimated: 2-3 hours)

**Start with HIGH PRIORITY synchronization tests:**

1. ✅ **TC_NTP_SYNC_001** - Basic IPv4 sync (5 min)
2. ✅ **TC_NTP_SYNC_002** - Sync with iburst (5 min)
3. ✅ **TC_NTP_ENABLE_001** - Enable NTP (2 min)
4. ✅ **TC_NTP_ENABLE_002** - Disable NTP (2 min)
5. ✅ **TC_NTP_SERVER_001** - Add IPv4 server (3 min)
6. ✅ **TC_NTP_SERVER_005** - Add server with iburst (3 min)
7. ✅ **TC_NTP_SHOW_001** - show ntp global (2 min)
8. ✅ **TC_NTP_SHOW_002** - show ntp server (2 min)
9. ✅ **TC_NTP_SHOW_003** - show ntp associations (4 min)
10. ✅ **TC_NTP_SYNC_003** - Prefer server (6 min)

**Total: 10 tests, ~34 minutes**

---

### Phase 2: Server Configuration (Estimated: 1-2 hours)

Complete all server configuration tests:

- TC_NTP_SERVER_002 through TC_NTP_SERVER_010 (9 tests)
- TC_NTP_ENABLE_003 (1 test)

**Total: 10 tests**

---

### Phase 3: Sync & Show Commands (Estimated: 1 hour)

- TC_NTP_SYNC_004, 005, 006 (3 sync tests)
- TC_NTP_SHOW_004, 005 (2 show tests)

**Total: 5 tests**

---

### Phase 4: Configuration Tests (Estimated: 2-3 hours)

- Auth Keys Config (7 tests)
- Trusted Keys Config (4 tests)
- Auth Enforcement (3 tests)
- Negative Tests (8 tests)

**Total: 22 tests**

---

### Phase 5: Advanced Tests (Estimated: 3-4 hours)

- Source Interface (6 tests)
- Persistence (4 tests)
- VRF (4 tests)
- Traffic Analysis (7 tests)
- Scale (5 tests)
- Edge Cases (5 tests)

**Total: 31 tests**

---

## Test Execution Summary

**IMMEDIATE - Can Start Now:**
- 🌟 **Synchronization Tests (6)** - Most valuable, start here
- ⭐ Enable/Disable (3)
- ⭐ Server Configuration (10)
- ⭐ Show Commands (5)

**MEDIUM PRIORITY:**
- Auth Keys Config Only (7)
- Trusted Keys Config Only (4)
- Auth Enforcement (3)
- Source Interface (6)
- Persistence (4)
- Negative Tests (8)

**LOWER PRIORITY:**
- VRF (4)
- Traffic Analysis (7)
- Scale (5)
- Edge Cases (5)

**BLOCKED:**
- ❌ Authentication Workflows (5) - Waiting for BUG-NTP-002 fix

---

## Next Test Recommendation

### 🌟 RECOMMENDED: Start with TC_NTP_SYNC_001

**Why:**
- Most important functionality (time synchronization)
- Uses available NTP server (192.168.100.175)
- No authentication required
- Fast execution (~5 minutes)
- Validates end-to-end operation

**Test Steps:**
```bash
1. Configure NTP server
2. Enable NTP
3. Wait 60 seconds
4. Verify synchronization via show commands
5. Check syslog for "Selected source"
```

**Estimated Time:** 5 minutes
**Success Criteria:** Server shows `*` prefix in associations

Would you like me to:
1. **Execute TC_NTP_SYNC_001** (Basic IPv4 sync) next?
2. **Execute the Quick Wins batch** (10 high-priority tests)?
3. **Create detailed test script** for a specific test case?

---

**Document Version:** 1.0
**Created:** 2026-04-09
**Status:** 📋 Ready for Execution Planning
