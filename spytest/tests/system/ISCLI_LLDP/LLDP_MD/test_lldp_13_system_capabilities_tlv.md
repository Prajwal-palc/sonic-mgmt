# LLDP Test Case 4.16.13: System Capabilities TLV

## Test Information

**Test ID:** 4.16.13
**Test Name:** system_capabilities_tlv
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - SysCaps TLV not visible**

---

## Test Objective

Verify System Capabilities TLV is advertised

---

## Test Configuration

### Configuration Steps:

```bash
show lldp neighbor Ethernet 8
```

---

## Expected Result

System Capabilities (Router, Bridge, etc.) should be visible

---

## Actual Result

System Capabilities TLV not displayed in output

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: System Capabilities TLV missing from CLI


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

**Test Script:** `test_lldp_13_system_capabilities_tlv.py`
**Documentation:** `test_lldp_13_system_capabilities_tlv.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
