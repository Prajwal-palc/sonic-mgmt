# LLDP Test Case 4.16.36: Bulk TLV Toggle on Interface Range

## Test Information

**Test ID:** 4.16.36
**Test Name:** bulk_tlv_toggle_range
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ○ **No logs provided**

---

## Test Objective

Verify TLVs can be toggled on interface ranges

---

## Test Configuration

### Configuration Steps:

```bash
interface range Ethernet 8-16
no lldp tlv-select management-address
```

---

## Expected Result

TLV should be disabled on all interfaces in range

---

## Actual Result

Not tested in manual validation

---

## Test Status

**Status:** OTHER

### Notes

Requires interface range support


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

**Test Script:** `test_lldp_36_bulk_tlv_toggle_range.py`
**Documentation:** `test_lldp_36_bulk_tlv_toggle_range.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
