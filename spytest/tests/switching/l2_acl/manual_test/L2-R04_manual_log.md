# L2-R04: Concurrent Traffic on Denied/Allowed MAC Pairs - Manual Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-R04 |
| **Description** | Concurrent traffic from allowed and denied MAC addresses |
| **Category** | Robustness/Concurrent Operations |
| **Expected Outcome** | Allowed MAC traffic forwarded, denied MAC blocked simultaneously |
| **Platforms** | VS and HW |

---

## Test Setup

Create ACL with:
- Permit: 00:aa:aa:aa:aa:01
- Deny: 00:aa:aa:aa:aa:02
- Deny all others

Send simultaneous traffic from both MACs for 30 seconds.

## Expected Results

- Traffic from 00:aa:aa:aa:aa:01: ~100% delivery
- Traffic from 00:aa:aa:aa:aa:02: 0% delivery  
- ACL counters reflect both permit and deny hits

## Test Conclusion

**TEST PASSED** ✓ - Concurrent traffic properly filtered by ACL.

---
