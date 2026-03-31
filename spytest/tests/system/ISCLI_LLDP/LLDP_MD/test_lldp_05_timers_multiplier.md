# LLDP Test Case 4.16.5: LLDP Timers and Hold Multiplier

## Test Information

**Test ID:** 4.16.5
**Test Name:** timers_multiplier
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ○ **PARTIAL - Timer configs work, multiplier not fully tested**

---

## Test Objective

Verify LLDP timer (hello-time, multiplier) configuration

---

## Test Configuration

### Configuration Steps:

```bash
lldp timer 10
lldp holdtime-multiplier 5
```

---

## Expected Result

Timer and multiplier should be configurable and affect LLDP behavior

---

## Actual Result

Commands accepted, timer configuration working

---

## Test Status

**Status:** OTHER

### Notes

Basic timer configuration functional


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

**Test Script:** `test_lldp_05_timers_multiplier.py`
**Documentation:** `test_lldp_05_timers_multiplier.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
