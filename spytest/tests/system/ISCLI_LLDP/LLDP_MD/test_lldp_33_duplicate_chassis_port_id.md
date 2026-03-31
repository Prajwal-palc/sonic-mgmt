# LLDP Test Case 4.16.33: Handling of Duplicate Chassis/Port IDs

## Test Information

**Test ID:** 4.16.33
**Test Name:** duplicate_chassis_port_id
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ⊘ **Not Feasible**

---

## Test Objective

Verify handling of duplicate chassis or port IDs

---

## Test Configuration

### Configuration Steps:

```bash
Configure duplicate IDs on multiple devices
```

---

## Expected Result

System should handle duplicates gracefully

---

## Actual Result

Cannot easily create duplicate ID scenario

---

## Test Status

**Status:** NOT FEASIBLE/N/A

### Notes

Difficult to test in current environment


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

**Test Script:** `test_lldp_33_duplicate_chassis_port_id.py`
**Documentation:** `test_lldp_33_duplicate_chassis_port_id.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
