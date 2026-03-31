# LLDP Test Case 4.16.8: Rapid Enable/Disable LLDP

## Test Information

**Test ID:** 4.16.8
**Test Name:** rapid_enable_disable
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ○ **No logs provided - test for stability**

---

## Test Objective

Verify system stability during rapid LLDP enable/disable cycles

---

## Test Configuration

### Configuration Steps:

```bash
lldp enable
no lldp enable
(repeat multiple times)
```

---

## Expected Result

System should remain stable, no crashes or memory leaks

---

## Actual Result

Not tested in manual validation

---

## Test Status

**Status:** OTHER

### Notes

Stability test - requires automated testing


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

**Test Script:** `test_lldp_08_rapid_enable_disable.py`
**Documentation:** `test_lldp_08_rapid_enable_disable.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
