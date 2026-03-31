# LLDP Test Case 4.16.17: LLDP Continuity During MTU Change

## Test Information

**Test ID:** 4.16.17
**Test Name:** mtu_change_continuity
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✓ **PASS**

---

## Test Objective

Verify LLDP continues to work after interface MTU change

---

## Test Configuration

### Configuration Steps:

```bash
interface Ethernet 8
mtu 9100
```

---

## Expected Result

LLDP should continue to function after MTU change

---

## Actual Result

LLDP continued to work normally after MTU change

---

## Test Status

**Status:** PASS

### Notes

LLDP resilient to MTU changes


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

**Test Script:** `test_lldp_17_mtu_change_continuity.py`
**Documentation:** `test_lldp_17_mtu_change_continuity.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
