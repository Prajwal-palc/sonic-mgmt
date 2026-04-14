# LLDP Test Case 4.16.10: LLDP Configuration Persistence After Save and Reboot

## Test Information

**Test ID:** 4.16.10
**Test Name:** save_reboot_persistence
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✓ **PASS**

---

## Test Objective

Verify LLDP configuration persists after save and reboot

---

## Test Configuration

### Configuration Steps:

```bash
lldp enable
write memory
reload
```

---

## Expected Result

LLDP configuration should persist after reboot

---

## Actual Result

Configuration persisted successfully after reboot

---

## Test Status

**Status:** PASS

### Notes

Configuration persistence working correctly


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

**Test Script:** `test_lldp_10_save_reboot_persistence.py`
**Documentation:** `test_lldp_10_save_reboot_persistence.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
