# LLDP Test Case 4.16.2: LLDP Neighbor Discovery

## Test Information

**Test ID:** 4.16.2
**Test Name:** neighbor_discovery
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✓ **PASS**

---

## Test Objective

Verify LLDP neighbor discovery between two DUTs

---

## Test Configuration

### Configuration Steps:

```bash
lldp enable
show lldp neighbor
show lldp neighbor Ethernet 8
```

---

## Expected Result

LLDP neighbors should be discovered and visible in show commands

---

## Actual Result

Neighbors discovered successfully with basic TLV information

---

## Test Status

**Status:** PASS

### Notes

Neighbor discovery working correctly


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

**Test Script:** `test_lldp_02_neighbor_discovery.py`
**Documentation:** `test_lldp_02_neighbor_discovery.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
