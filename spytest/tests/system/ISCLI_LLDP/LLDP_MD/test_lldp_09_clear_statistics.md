# LLDP Test Case 4.16.9: LLDP Statistics Clear

## Test Information

**Test ID:** 4.16.9
**Test Name:** clear_statistics
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ○ **Not detailed in logs - functionality test**

---

## Test Objective

Verify LLDP statistics can be cleared

---

## Test Configuration

### Configuration Steps:

```bash
clear lldp counters
show lldp statistics
```

---

## Expected Result

LLDP statistics should be cleared and reset to zero

---

## Actual Result

Not fully tested in manual validation

---

## Test Status

**Status:** OTHER

### Notes

Basic functionality test


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

**Test Script:** `test_lldp_09_clear_statistics.py`
**Documentation:** `test_lldp_09_clear_statistics.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
