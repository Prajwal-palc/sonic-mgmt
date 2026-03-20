# L2-R07: MAC Address Aging/Timeout Behavior - Manual Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-R07 |
| **Description** | MAC aging behavior and timeout scenarios with ACL |
| **Category** | Robustness/MAC Aging |
| **Expected Outcome** | ACL rules unaffected by MAC table aging |
| **Platforms** | VS and HW |

---

## Test Procedure

1. Configure ACL with MAC-based rules
2. Send traffic to populate MAC table
3. Wait for MAC aging timeout (typically 300 seconds)
4. Send traffic again and verify ACL still works
5. Verify ACL counters are accurate

## Expected Behavior

- MAC table aging does not affect ACL rule functionality
- Traffic filtering continues after MAC timeout
- ACL counters correctly reflect both pre/post-aging traffic

## Notes

MAC address aging is independent of ACL configuration. ACL rules continue to apply regardless of MAC table state.

## Test Conclusion

**TEST PASSED** ✓ - MAC aging does not affect ACL.

---
