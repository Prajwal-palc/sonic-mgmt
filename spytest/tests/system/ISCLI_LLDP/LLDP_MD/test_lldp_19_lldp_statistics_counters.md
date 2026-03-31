# LLDP Test Case 4.16.19: LLDP Statistics and Counters

## Test Information

**Test ID:** 4.16.19
**Test Name:** lldp_statistics_counters
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - show lldp statistics no output**

---

## Test Objective

Verify LLDP statistics are maintained and displayed

---

## Test Configuration

### Configuration Steps:

```bash
show lldp statistics
show lldp statistics Ethernet 8
```

---

## Expected Result

Statistics should show frames transmitted, received, discarded, etc.

---

## Actual Result

show lldp statistics command produces no output

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: Statistics command not implemented or broken


---

## Test Execution

### Prerequisites:
- Two DUTs connected back-to-back
- LLDP feature available in SONiC
- sonic-cli (ISCLI) access to both DUTs

### Test Steps:

1. Configure LLDP as per configuration steps above
2. Verify configuration using show commands
3. Check LLDP neighbor discovery and TLV information
4. Validate expected behavior against actual behavior

### Verification Commands:

```bash
show lldp neighbor
show lldp neighbor <interface>
show lldp local <interface>
show lldp configuration
show lldp statistics
```

---

## Related Test Cases

- Test 4.16.1: Global and Interface LLDP CLI Configuration
- Test 4.16.2: LLDP Neighbor Discovery
- Test 4.16.10: LLDP Configuration Persistence

---

## References

- IEEE 802.1AB LLDP Standard
- SONiC LLDP Feature Documentation
- OC-1 Manual Testing Document

---

**Test Script:** `test_lldp_19_lldp_statistics_counters.py`
**Documentation:** `test_lldp_19_lldp_statistics_counters.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
