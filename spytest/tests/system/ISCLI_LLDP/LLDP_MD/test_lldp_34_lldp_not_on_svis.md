# LLDP Test Case 4.16.34: LLDP Not Supported on SVIs

## Test Information

**Test ID:** 4.16.34
**Test Name:** lldp_not_on_svis
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - VLAN config failed**

---

## Test Objective

Verify LLDP is not enabled on SVI interfaces

---

## Test Configuration

### Configuration Steps:

```bash
Create VLAN interface
Attempt LLDP enable
```

---

## Expected Result

LLDP should not be supported on SVIs

---

## Actual Result

Cannot create VLAN interfaces to test

---

## Test Status

**Status:** FAIL

### Known Issues

VLAN configuration issues


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

**Test Script:** `test_lldp_34_lldp_not_on_svis.py`
**Documentation:** `test_lldp_34_lldp_not_on_svis.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
