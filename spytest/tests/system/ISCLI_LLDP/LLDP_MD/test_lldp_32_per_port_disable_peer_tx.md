# LLDP Test Case 4.16.32: Per-Port Disable and Peer Transmission

## Test Information

**Test ID:** 4.16.32
**Test Name:** per_port_disable_peer_tx
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - Per-port disable not working**

---

## Test Objective

Verify per-port disable stops LLDP on that port

---

## Test Configuration

### Configuration Steps:

```bash
interface Ethernet 8
no lldp enable
```

---

## Expected Result

LLDP should stop on disabled port only

---

## Actual Result

Per-port disable command has no effect

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: Per-port disable broken


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

**Test Script:** `test_lldp_32_per_port_disable_peer_tx.py`
**Documentation:** `test_lldp_32_per_port_disable_peer_tx.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
