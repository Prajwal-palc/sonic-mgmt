# LLDP Test Case 4.16.3: LLDP Transmit and Receive Modes

## Test Information

**Test ID:** 4.16.3
**Test Name:** transmit_receive_modes
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - TX/RX mode commands ineffective**

---

## Test Objective

Verify per-interface LLDP transmit-only and receive-only modes

---

## Test Configuration

### Configuration Steps:

```bash
interface Ethernet 8
no lldp transmit
no lldp receive
```

---

## Expected Result

Interface should stop transmitting/receiving LLDP frames based on mode

---

## Actual Result

Commands accepted but have no effect - neighbors still visible after disabling transmit/receive

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: no lldp transmit/receive commands do not work


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

**Test Script:** `test_lldp_03_transmit_receive_modes.py`
**Documentation:** `test_lldp_03_transmit_receive_modes.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
