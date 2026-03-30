# L2-R08: Mixed Permit/Deny Rules with Same Match Criteria - Manual Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-R08 |
| **Description** | Mixed permit/deny rules with overlapping match criteria |
| **Category** | Robustness/Rule Ordering |
| **Expected Outcome** | Rule priority determines outcome, no ambiguity |
| **Platforms** | VS and HW |

---

## Test Configuration

Create ACL with mixed rules:

```bash
mac access-list L2_ACL_MIXED

# Rule 10: Permit specific MAC
permit host 00:aa:aa:aa:aa:01

# Rule 20: Deny source MAC range (overlaps with Rule 10)
deny any any

# Rule 30: Permit alternate MAC
permit host 00:cc:cc:cc:cc:01

exit
```

## Test Traffic

Send packets from three sources:
- 00:aa:aa:aa:aa:01 → Should PERMIT (Rule 10, highest priority match)
- 00:bb:bb:bb:bb:02 → Should DENY (Rule 20)
- 00:cc:cc:cc:cc:01 → Should DENY (Rule 20 matches first)

## Expected Results

| Source MAC | Rule Match | Result |
|-----------|-----------|--------|
| 00:aa:aa:aa:aa:01 | Rule 10 | PERMIT ✓ |
| 00:bb:bb:bb:bb:02 | Rule 20 | DENY ✓ |
| 00:cc:cc:cc:cc:01 | Rule 20 | DENY ✓ |

## Key Learning

First matching rule wins - order matters in ACL evaluation.

## Test Conclusion

**TEST PASSED** ✓ - Rule priority correctly handles overlapping criteria.

---
