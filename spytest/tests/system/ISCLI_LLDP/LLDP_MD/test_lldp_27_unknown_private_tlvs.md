# LLDP Test Case 4.16.27: Handling of Unknown/Private TLVs

## Test Information

**Test ID:** 4.16.27
**Test Name:** unknown_private_tlvs
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✓ **PASS - Unknown TLVs ignored**

---

## Test Objective

Verify unknown or private TLVs are handled gracefully

---

## Test Configuration

### Configuration Steps:

```bash
Receive frames with unknown TLVs
```

---

## Expected Result

Unknown TLVs should be ignored without errors

---

## Actual Result

Unknown TLVs handled correctly, no crashes or errors

---

## Test Status

**Status:** PASS

### Notes

Robust TLV handling


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

**Test Script:** `test_lldp_27_unknown_private_tlvs.py`
**Documentation:** `test_lldp_27_unknown_private_tlvs.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
