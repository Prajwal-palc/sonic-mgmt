# LLDP Test Case 4.16.28: Handling of Malformed LLDP Frames

## Test Information

**Test ID:** 4.16.28
**Test Name:** malformed_lldp_frames
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ⊘ **Not Feasible**

---

## Test Objective

Verify malformed LLDP frames are handled without crashes

---

## Test Configuration

### Configuration Steps:

```bash
Send malformed LLDP frames
```

---

## Expected Result

Malformed frames should be discarded gracefully

---

## Actual Result

Cannot generate malformed frames in current test setup

---

## Test Status

**Status:** NOT FEASIBLE/N/A

### Notes

Requires packet crafting tools


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

**Test Script:** `test_lldp_28_malformed_lldp_frames.py`
**Documentation:** `test_lldp_28_malformed_lldp_frames.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
