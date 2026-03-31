# LLDP Test Case 4.16.25: Reject Invalid Timer Values

## Test Information

**Test ID:** 4.16.25
**Test Name:** reject_invalid_timers
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✓ **PASS**

---

## Test Objective

Verify invalid timer values are rejected by CLI

---

## Test Configuration

### Configuration Steps:

```bash
lldp timer 0
lldp timer 65536
lldp holdtime-multiplier 0
```

---

## Expected Result

Invalid values should be rejected with error message

---

## Actual Result

Invalid timer values properly rejected

---

## Test Status

**Status:** PASS

### Notes

Input validation working correctly


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

**Test Script:** `test_lldp_25_reject_invalid_timers.py`
**Documentation:** `test_lldp_25_reject_invalid_timers.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
