# LLDP Test Case 4.16.29: LLDP on VLAN Tagged Interfaces

## Test Information

**Test ID:** 4.16.29
**Test Name:** vlan_tagged_lldp_frames
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ⊘ **Not Feasible - VLAN config failed**

---

## Test Objective

Verify LLDP works on VLAN-tagged interfaces

---

## Test Configuration

### Configuration Steps:

```bash
Create VLAN tagged subinterface
Enable LLDP
```

---

## Expected Result

LLDP should work on VLAN-tagged interfaces

---

## Actual Result

VLAN configuration failed, cannot test

---

## Test Status

**Status:** NOT FEASIBLE/N/A

### Notes

VLAN configuration issues prevented testing


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

**Test Script:** `test_lldp_29_vlan_tagged_lldp_frames.py`
**Documentation:** `test_lldp_29_vlan_tagged_lldp_frames.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
