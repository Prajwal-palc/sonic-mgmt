# LLDP Test Case 4.16.20: SNMP LLDP MIB Parity with CLI

## Test Information

**Test ID:** 4.16.20
**Test Name:** snmp_lldp_mib_parity
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ⊘ **Not Feasible**

---

## Test Objective

Verify LLDP information via SNMP matches CLI output

---

## Test Configuration

### Configuration Steps:

```bash
snmpwalk for LLDP-MIB
```

---

## Expected Result

SNMP LLDP MIB data should match CLI data

---

## Actual Result

SNMP testing not feasible in current test environment

---

## Test Status

**Status:** NOT FEASIBLE/N/A

### Notes

Requires SNMP configuration and tools


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

**Test Script:** `test_lldp_20_snmp_lldp_mib_parity.py`
**Documentation:** `test_lldp_20_snmp_lldp_mib_parity.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
