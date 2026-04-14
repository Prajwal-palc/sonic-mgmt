# NTP Scalable Test Cases Summary

## Overview

This document tracks the NTP scale/performance test cases that validate SONiC NTP implementation under high load and stress conditions.

## Test Case Status

| Test Case ID | Title | Status | Estimated Duration | Priority |
|-------------|-------|--------|-------------------|----------|
| TC_NTP_SCALE_001 | Max NTP Servers (10) | ✅ **AUTOMATED** | 5 min | P1 |
| TC_NTP_SCALE_002 | Max Authentication Keys | ⏳ **NOT AUTOMATED** | 5 min | P2 |
| TC_NTP_SCALE_003 | Rapid Enable/Disable Cycles | ⏳ **NOT AUTOMATED** | 4 min | P2 |
| TC_NTP_SCALE_004 | Concurrent Configuration | ⏳ **NOT AUTOMATED** | 5 min | P2 |
| TC_NTP_SCALE_005 | High-Frequency Packet Injection | ⏳ **NOT AUTOMATED** | 6 min | P3 |

**Overall Completion**: 1/5 (20%)

---

## Detailed Test Case Descriptions

### TC_NTP_SCALE_001: Max NTP Servers (10) ✅ AUTOMATED

**File**: `test_ntp_functional.py::test_ntp_029_server_max_limit`

**Description**: Verify that DUT can handle maximum number of NTP servers (typically 10 servers).

**Test Steps**:
1. Configure 10 NTP servers sequentially
2. Verify all servers are accepted
3. Attempt to add 11th server
4. Verify appropriate error or rejection
5. Verify all 10 servers remain in configuration
6. Check NTP service stability with 10 servers

**Expected Results**:
- All 10 servers configured successfully
- 11th server rejected with appropriate error
- NTP service remains stable
- `show ntp server` displays all 10 servers

**Platform Support**: VS, HW

**Status**: ✅ **AUTOMATED** and **PASSING**

---

### TC_NTP_SCALE_002: Max Authentication Keys ⏳ NOT AUTOMATED

**Description**: Verify that DUT can handle maximum number of NTP authentication keys.

**Test Steps**:
1. Determine max key limit (typically 65535)
2. Configure large number of authentication keys (e.g., 100-1000)
3. Verify all keys are accepted and stored
4. Mark keys as trusted
5. Bind keys to servers
6. Verify NTP service stability
7. Test memory consumption
8. Attempt to exceed limit

**Expected Results**:
- Large number of keys configured successfully
- Keys properly stored in config_db.json
- NTP service remains stable
- Appropriate error when exceeding limit
- No memory leaks

**Platform Support**: VS, HW

**Estimated Duration**: ~5 minutes

**Priority**: P2

**Automation Needed**: Yes

**Notes**:
- Consider testing with 100, 500, 1000, 5000 keys
- Monitor memory usage during test
- Verify cleanup efficiency

---

### TC_NTP_SCALE_003: Rapid Enable/Disable Cycles ⏳ NOT AUTOMATED

**Description**: Verify NTP service stability under rapid enable/disable cycles.

**Test Steps**:
1. Perform rapid enable/disable cycles (100-1000 iterations)
   - `ntp enable` → wait 1s → `no ntp enable` → repeat
2. Monitor for service crashes or hangs
3. Verify service responds correctly after cycles
4. Check for memory leaks
5. Verify configuration consistency

**Expected Results**:
- Service handles rapid cycles without crashes
- No memory leaks detected
- Service remains responsive
- Configuration remains consistent
- No zombie processes

**Platform Support**: VS, HW

**Estimated Duration**: ~4 minutes (1000 cycles @ ~0.2s each)

**Priority**: P2

**Automation Needed**: Yes

**Notes**:
- Monitor chrony/ntpd process health
- Check system logs for errors
- Measure response time degradation

---

### TC_NTP_SCALE_004: Concurrent Configuration Operations ⏳ NOT AUTOMATED

**Description**: Verify NTP handles concurrent configuration changes gracefully.

**Test Steps**:
1. Perform concurrent operations in parallel:
   - Add/delete servers
   - Add/delete auth keys
   - Enable/disable authentication
   - Change source interface
   - Switch VRF
2. Monitor for race conditions
3. Verify final configuration consistency
4. Check for service stability

**Expected Results**:
- No crashes or hangs
- Configuration remains consistent
- No race conditions observed
- Service recovers gracefully
- Config_db.json remains valid

**Platform Support**: VS, HW

**Estimated Duration**: ~5 minutes

**Priority**: P2

**Automation Needed**: Yes

**Notes**:
- Use threading or multiprocessing
- Test with 5-10 concurrent operations
- Verify locking mechanisms

---

### TC_NTP_SCALE_005: High-Frequency Packet Injection ⏳ NOT AUTOMATED

**Description**: Verify NTP service stability under high-frequency NTP packet injection.

**Test Steps**:
1. Set up packet generator (scapy or similar)
2. Inject NTP packets at high rate (e.g., 1000 packets/sec)
3. Monitor for:
   - Service crashes
   - CPU usage
   - Memory consumption
   - Packet drops
4. Verify legitimate NTP traffic still processed
5. Check for DoS vulnerabilities

**Expected Results**:
- Service remains stable under load
- CPU usage remains reasonable (<80%)
- No memory leaks
- Legitimate traffic still processed
- Rate limiting effective (if implemented)

**Platform Support**: VS (limited), HW (recommended)

**Estimated Duration**: ~6 minutes

**Priority**: P3

**Automation Needed**: Yes

**Notes**:
- Requires packet generation capability
- HW platform recommended for realistic testing
- Monitor system resources
- Check rate limiting mechanisms

---

## Implementation Priority

1. **High Priority (P1)**: TC_NTP_SCALE_001 ✅ (Completed)
2. **Medium Priority (P2)**:
   - TC_NTP_SCALE_002 (Max auth keys)
   - TC_NTP_SCALE_003 (Rapid cycles)
   - TC_NTP_SCALE_004 (Concurrent config)
3. **Low Priority (P3)**:
   - TC_NTP_SCALE_005 (Packet injection - requires special setup)

## Automation Guidelines

### General Requirements

1. **Cleanup**: All scale tests must perform thorough cleanup
2. **Timeouts**: Use generous timeouts for scale operations
3. **Resource Monitoring**: Track CPU, memory during tests
4. **Platform Marking**: Mark appropriately for VS vs HW
5. **Error Handling**: Gracefully handle platform limitations

### Test Pattern

```python
@pytest.mark.scale
@pytest.mark.inventory(feature="NTP", testcase="TC_NTP_SCALE_00X")
def test_ntp_scale_xxx(self):
    """Scale test description"""
    # 1. Setup
    # 2. Execute scale operation
    # 3. Monitor system health
    # 4. Verify functionality maintained
    # 5. Cleanup
```

### Example Implementation (TC_NTP_SCALE_002)

```python
@pytest.mark.scale
@pytest.mark.inventory(feature="NTP", testcase="TC_NTP_SCALE_002")
def test_ntp_max_authentication_keys(self):
    """Verify DUT handles large number of authentication keys"""

    # Test configuration
    num_keys = 100  # Start with 100, increase to 500, 1000

    # Add keys
    for key_id in range(1, num_keys + 1):
        result = ntp_obj.config_ntp_authentication_key(
            dut, key_id, "md5", f"Key{key_id:04d}", cli_type="klish"
        )
        if not result:
            st.report_fail("ntp_auth_key_config_failed", key_id)

    # Verify all keys present
    keys = ntp_obj.get_ntp_authentication_keys(dut, cli_type="klish")
    if len(keys) != num_keys:
        st.report_fail("ntp_auth_key_count_mismatch", num_keys, len(keys))

    # Cleanup
    for key_id in range(1, num_keys + 1):
        ntp_obj.unconfig_ntp_authentication_key(dut, key_id, cli_type="klish")

    st.report_pass("test_case_passed")
```

---

## References

- **Test Plan**: `doc/NTP_TestPlan.md`
- **Pending Cases**: `report/NTP_PENDING_TEST_CASES_UPDATED.md`
- **Tracker**: `doc/NTP_TestPlan_Tracker_README.md`

---

## Notes

- Scale tests may take longer on VS platforms
- Some tests may require special hardware or network setup
- Monitor system resources during testing
- Consider platform-specific limitations

**Last Updated**: 2026-04-10
**Author**: Athira
**Status**: 1/5 automated (20% complete)
