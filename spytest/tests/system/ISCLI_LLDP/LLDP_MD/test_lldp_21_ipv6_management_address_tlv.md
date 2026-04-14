# LLDP Test Case 4.16.21: IPv6 Management Address TLV

## Test Information

**Test ID:** 4.16.21
**Test Name:** ipv6_management_address_tlv
**Feature:** LLDP (Link Layer Discovery Protocol)
**Test Result:** ✗ **FAIL - IPv6 mgmt field not visible**

---

## Test Objective

Verify IPv6 Management Address is advertised in LLDP

---

## Test Configuration

### Configuration Steps:

```bash
Configure IPv6 management address
show lldp neighbor Ethernet 8
```

---

## Expected Result

IPv6 management address should be visible in neighbor details

---

## Actual Result

IPv6 management address field not displayed

---

## Test Status

**Status:** FAIL

### Known Issues

BUG: IPv6 Management Address TLV not shown


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

**Test Script:** `test_lldp_21_ipv6_management_address_tlv.py`
**Documentation:** `test_lldp_21_ipv6_management_address_tlv.md`
**Test Suite:** iscli_LLDP
**Framework:** spytest
