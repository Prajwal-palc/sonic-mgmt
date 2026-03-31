# LLDP Test Case 4.16.16: LLDP on LAG Member Interfaces

## Test Information

**Test ID:** 4.16.16
**Test Name:** lag_member_interfaces
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ⊘ **Not Applicable - LAG config failed**

---

## Test Objective

Verify LLDP works on LAG (Port-Channel) member interfaces

---

## Test Configuration

### Configuration Steps:

```bash
interface PortChannel 1
interface Ethernet 8
channel-group 1 mode active
```

---

## Expected Result

LLDP should work on LAG member interfaces

---

## Actual Result

LAG configuration failed, cannot test

---

## Test Status

**Status:** NOT FEASIBLE/N/A

### Notes

LAG configuration issues prevented testing


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

**Test Script:** `test_lldp_16_lag_member_interfaces.py`
**Documentation:** `test_lldp_16_lag_member_interfaces.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
