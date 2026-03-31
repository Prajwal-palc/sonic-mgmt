# LLDP Test Case 4.16.1: Global and Interface LLDP CLI Configuration

## Test Information

**Test ID:** 4.16.1
**Test Name:** global_interface_cli
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✓ **PASS**

---

## Test Objective

Verify LLDP can be enabled globally and per-interface using sonic-cli commands

---

## Test Configuration

### Configuration Steps:

```bash
configure terminal
lldp enable
interface Ethernet 8
lldp enable
lldp transmit
lldp receive
```

---

## Expected Result

LLDP should be enabled globally and per-interface, neighbors should be discovered

---

## Actual Result

LLDP enabled successfully, neighbors discovered

---

## Test Status

**Status:** PASS

### Notes

Basic LLDP functionality working as expected


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

**Test Script:** `test_lldp_01_global_interface_cli.py`
**Documentation:** `test_lldp_01_global_interface_cli.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
