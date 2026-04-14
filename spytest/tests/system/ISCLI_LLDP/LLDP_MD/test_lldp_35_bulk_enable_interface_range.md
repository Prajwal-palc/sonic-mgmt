# LLDP Test Case 4.16.35: Bulk Enable LLDP on Interface Range

## Test Information

**Test ID:** 4.16.35
**Test Name:** bulk_enable_interface_range
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - Interface range not supported**

---

## Test Objective

Verify LLDP can be enabled on interface ranges

---

## Test Configuration

### Configuration Steps:

```bash
interface range Ethernet 8-16
lldp enable
```

---

## Expected Result

LLDP should be enabled on all interfaces in range

---

## Actual Result

Interface range command not supported in sonic-cli

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: Interface range not implemented


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

**Test Script:** `test_lldp_35_bulk_enable_interface_range.py`
**Documentation:** `test_lldp_35_bulk_enable_interface_range.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
