# LLDP Test Case 4.16.22: LLDP Over Different Media Types

## Test Information

**Test ID:** 4.16.22
**Test Name:** lldp_over_different_media
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ⊘ **Not Applicable**

---

## Test Objective

Verify LLDP works over different media (copper, fiber)

---

## Test Configuration

### Configuration Steps:

```bash
Test on various interface types
```

---

## Expected Result

LLDP should work on all supported media types

---

## Actual Result

Limited interface types available for testing

---

## Test Status

**Status:** NOT FEASIBLE/N/A

### Notes

Requires hardware with multiple media types


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

**Test Script:** `test_lldp_22_lldp_over_different_media.py`
**Documentation:** `test_lldp_22_lldp_over_different_media.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
