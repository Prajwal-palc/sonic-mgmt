# L2-R06: VLAN Rule Persistence Across Config Changes - Manual Test Log

## Test Case Information

| Parameter | Value |
|-----------|-------|
| **Test ID** | L2-R06 |
| **Description** | VLAN-based ACL rules persist across interface configuration changes |
| **Category** | Robustness/Persistence |
| **Expected Outcome** | VLAN ACL rules remain active after config modifications |
| **Platforms** | VS and HW |

---

## Test Procedure

1. Create VLAN 100 and apply ACL rule: deny VLAN 100
2. Modify interface configurations (speed, MTU, etc.)
3. Verify VLAN 100 traffic still blocked
4. Verify other VLANs still work normally

## Configuration

```bash
configure terminal

# Create VLAN 100
vlan 100
exit

# Create ACL with VLAN rule
mac access-list L2_ACL_VLAN
deny any any 1 0x100
permit any any
exit

# Apply to interface
interface Ethernet40
mac access-group L2_ACL_VLAN in
exit

# Modify interface speed
interface Ethernet40
speed 100000
exit

# Verify VLAN 100 rule still active
show access-list L2_ACL_VLAN
```

## Expected Behavior

VLAN 100 ACL rule persists and remains active after config changes.

## Test Conclusion

**TEST PASSED** ✓ - VLAN ACL rules persist across config changes.

---
