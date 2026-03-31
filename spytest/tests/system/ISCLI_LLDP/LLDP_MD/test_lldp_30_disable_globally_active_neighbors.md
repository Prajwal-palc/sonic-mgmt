# LLDP Test Case 4.16.30: Global Disable with Active Neighbors

## Test Information

**Test ID:** 4.16.30
**Test Name:** disable_globally_active_neighbors
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - Neighbors not withdrawn**

---

## Test Objective

Verify global LLDP disable removes all neighbors

---

## Test Configuration

### Configuration Steps:

```bash
no lldp enable
show lldp neighbor
```

---

## Expected Result

All neighbors should be withdrawn immediately

---

## Actual Result

Neighbors remain visible after global disable

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: Global disable does not flush neighbors


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

**Test Script:** `test_lldp_30_disable_globally_active_neighbors.py`
**Documentation:** `test_lldp_30_disable_globally_active_neighbors.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
