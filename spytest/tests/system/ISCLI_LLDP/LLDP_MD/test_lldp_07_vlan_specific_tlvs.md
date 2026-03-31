# LLDP Test Case 4.16.7: VLAN Specific LLDP TLVs

## Test Information

**Test ID:** 4.16.7
**Test Name:** vlan_specific_tlvs
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - VLAN configuration not working in ISCLI**

---

## Test Objective

Verify VLAN Name and Port VLAN ID TLVs in LLDP

---

## Test Configuration

### Configuration Steps:

```bash
vlan 100
lldp tlv-select port-vlan-id
lldp vlan-name-tlv allowed Vlan 100,200
```

---

## Expected Result

VLAN TLVs should be advertised and visible on peer

---

## Actual Result

VLAN configuration failed - Invalid input in ISCLI mode

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: VLAN configuration not supported in sonic-cli (ISCLI)


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

**Test Script:** `test_lldp_07_vlan_specific_tlvs.py`
**Documentation:** `test_lldp_07_vlan_specific_tlvs.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
