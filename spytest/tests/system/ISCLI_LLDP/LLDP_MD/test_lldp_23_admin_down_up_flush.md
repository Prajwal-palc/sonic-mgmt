# LLDP Test Case 4.16.23: Admin Down/Up and Neighbor Flush

## Test Information

**Test ID:** 4.16.23
**Test Name:** admin_down_up_flush
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✓ **PASS**

---

## Test Objective

Verify neighbors are flushed when interface goes admin down

---

## Test Configuration

### Configuration Steps:

```bash
interface Ethernet 8
shutdown
no shutdown
```

---

## Expected Result

Neighbors should be removed on shutdown and rediscovered on no shutdown

---

## Actual Result

Neighbors properly flushed and rediscovered

---

## Test Status

**Status:** PASS

### Notes

Neighbor flush working correctly


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

**Test Script:** `test_lldp_23_admin_down_up_flush.py`
**Documentation:** `test_lldp_23_admin_down_up_flush.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
