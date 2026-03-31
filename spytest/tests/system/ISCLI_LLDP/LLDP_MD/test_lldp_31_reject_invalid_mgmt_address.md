# LLDP Test Case 4.16.31: Reject Invalid Management Address

## Test Information

**Test ID:** 4.16.31
**Test Name:** reject_invalid_mgmt_address
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✓ **PASS**

---

## Test Objective

Verify invalid management addresses are rejected

---

## Test Configuration

### Configuration Steps:

```bash
Configure invalid management IP
```

---

## Expected Result

Invalid IP addresses should be rejected

---

## Actual Result

Invalid addresses properly rejected by CLI

---

## Test Status

**Status:** PASS

### Notes

Input validation working


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

**Test Script:** `test_lldp_31_reject_invalid_mgmt_address.py`
**Documentation:** `test_lldp_31_reject_invalid_mgmt_address.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
