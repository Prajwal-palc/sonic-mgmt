# LLDP Test Case 4.16.14: Management Address Selection

## Test Information

**Test ID:** 4.16.14
**Test Name:** management_address_selection
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - Mgmt address not advertised**

---

## Test Objective

Verify Management Address TLV is advertised with correct IP

---

## Test Configuration

### Configuration Steps:

```bash
show lldp neighbor Ethernet 8
```

---

## Expected Result

Management Address should be visible in neighbor details

---

## Actual Result

Management Address field not shown in CLI output

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: Management Address TLV not displayed


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

**Test Script:** `test_lldp_14_management_address_selection.py`
**Documentation:** `test_lldp_14_management_address_selection.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
