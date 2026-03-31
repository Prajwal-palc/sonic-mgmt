# LLDP Test Case 4.16.12: Port Description TLV

## Test Information

**Test ID:** 4.16.12
**Test Name:** port_description_tlv
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - Port description not advertised**

---

## Test Objective

Verify Port Description TLV is advertised in LLDP

---

## Test Configuration

### Configuration Steps:

```bash
interface Ethernet 8
description TEST_PORT
```

---

## Expected Result

Port description should be visible in LLDP neighbor output

---

## Actual Result

Port description TLV not advertised or not visible

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: Port Description TLV not working


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

**Test Script:** `test_lldp_12_port_description_tlv.py`
**Documentation:** `test_lldp_12_port_description_tlv.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
