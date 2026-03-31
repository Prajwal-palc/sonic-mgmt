# LLDP Test Case 4.16.6: System Name, Description and Management Address TLVs

## Test Information

**Test ID:** 4.16.6
**Test Name:** system_name_description_mgmt_tlv
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - Management Address TLV missing**

---

## Test Objective

Verify System Name, System Description and Management Address TLVs in LLDP

---

## Test Configuration

### Configuration Steps:

```bash
show lldp neighbor
show lldp neighbor Ethernet 8
```

---

## Expected Result

System Name, Description and Management Address should be visible

---

## Actual Result

System Name and Description visible, but Management Address TLV missing from CLI output

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: Management Address field not shown in show commands


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

**Test Script:** `test_lldp_06_system_name_description_mgmt_tlv.py`
**Documentation:** `test_lldp_06_system_name_description_mgmt_tlv.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
