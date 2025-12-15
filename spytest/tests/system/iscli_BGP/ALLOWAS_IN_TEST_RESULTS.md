# allowas-in Command Testing Results - SONiC CLI

**Devices Tested**: DUT1 (192.168.100.217), DUT2 (192.168.100.219)
**SONiC CLI**: Klish interface
**Date**: December 16, 2025

---

## Test Summary

| Context | Command | Result | Status |
|---------|---------|--------|--------|
| **Peer-Group Address-Family** | `allowas-in 3` | ❌ Syntax Error | **NOT WORKING** |
| **Neighbor Address-Family** | `allowas-in 3` | ⚠️ Converts to `origin` | **PARTIALLY WORKING** |
| **Neighbor Address-Family** | `allowas-in origin` | ✅ Applied correctly | **WORKING** |

---

## ❌ WHERE IT IS **NOT WORKING**

### 1. Peer-Group Address-Family Context (FAILED)

**Command Path**:
```bash
router bgp 65001
  peer-group 1
    address-family ipv4 unicast
      allowas-in 3  # ← FAILS HERE
```

**Error Received**:
```
/tmp/klish.fifo.1956.3IHSLX: 1: Syntax error: "then" unexpected
```

**Result**:
- ❌ Command **NOT accepted**
- ❌ Configuration **NOT applied**
- ❌ Does **NOT appear** in `show running-configuration bgp`

**Verification**:
```bash
show running-configuration bgp
# Output shows NO allowas-in under peer-group:
peer-group 1
  address-family ipv4 unicast
    activate
    # ← NO allowas-in here
```

**Conclusion**:
> **`allowas-in` is NOT supported at peer-group level in SONiC Klish CLI**

---

## ⚠️ WHERE IT IS **PARTIALLY WORKING** (Bug Suspected)

### 2. Neighbor Address-Family Context with Numeric Parameter

**Command Path**:
```bash
router bgp 65001
  neighbor 10.1.1.2 remote-as 65001
    address-family ipv4 unicast
      allowas-in 3  # ← Accepts but converts
```

**What Happens**:
1. ✅ Command **accepted** (no error)
2. ⚠️ Parameter **changed** from `3` to `origin`
3. ⚠️ Configuration **applied incorrectly**

**Expected Configuration**:
```
neighbor 10.1.1.2 remote-as 65001
  address-family ipv4 unicast
    allowas-in 3  # ← Should show numeric value
```

**Actual Configuration** (from `show running-configuration bgp`):
```
neighbor 10.1.1.2 remote-as 65001
  address-family ipv4 unicast
    allowas-in origin  # ← Shows "origin" instead of "3"
```

**CLI Help Shows** (from your test):
```bash
sonic(-router-bgp-neighbor-af)# allowas-in ?
  <1..10>  AS number
  origin   Only accept my AS in the as-path if the route was originated in my AS
  <cr>
```

**Conclusion**:
> **Numeric parameter (1-10) is advertised in help but gets converted to `origin`**
>
> This appears to be a **SONiC CLI bug or limitation**

---

## ✅ WHERE IT IS **WORKING**

### 3. Neighbor Address-Family Context with "origin" Keyword

**Command Path**:
```bash
router bgp 65001
  neighbor 10.1.1.2 remote-as 65001
    address-family ipv4 unicast
      allowas-in origin  # ← Works correctly
```

**Result**:
- ✅ Command **accepted**
- ✅ Configuration **applied correctly**
- ✅ Appears in `show running-configuration bgp`

**Verification**:
```bash
show running-configuration bgp
# Output shows:
neighbor 10.1.1.2 remote-as 65001
  address-family ipv4 unicast
    allowas-in origin  # ← Correctly applied
```

**Conclusion**:
> **`allowas-in origin` works correctly at neighbor level**

---

## 🔬 Detailed Test Results

### Test 1: Peer-Group Level (DUT1 & DUT2)

**DUT1 Attempt**:
```bash
sonic(-router-bgp-pg-af)# allowas-in 3
/tmp/klish.fifo.1956.3IHSLX: 1: Syntax error: "then" unexpected
```

**DUT2 Attempt**:
```bash
sonic(-router-bgp-pg-af)# allowas-in 3
/tmp/klish.fifo.1644.2s4SyT: 1: Syntax error: "then" unexpected
```

**Configuration Check**:
```bash
# DUT1
show running-configuration bgp
peer-group 1
  address-family ipv4 unicast
    activate
    route-map RM_IN in
    route-reflector-client
    # NO allowas-in present

# DUT2
show running-configuration bgp
peer-group 1
  address-family ipv4 unicast
    activate
    route-map RM_IN in
    route-reflector-client
    # NO allowas-in present
```

**Result**: ❌ **FAILED - Not supported**

---

### Test 2: Neighbor Level with Numeric Parameter (DUT1)

**Command Entered**:
```bash
sonic(-router-bgp-neighbor-af)# allowas-in 3
sonic(-router-bgp-neighbor-af)# end
```

**No Error Displayed**: ✅ (Command accepted)

**Configuration Check**:
```bash
sonic# show running-configuration bgp
neighbor 10.1.1.2 remote-as 65001
  peer-group 1
  address-family ipv4 unicast
    activate
    allowas-in origin  # ← Changed from "3" to "origin"
```

**Result**: ⚠️ **PARTIAL - Parameter converted incorrectly**

---

### Test 3: Help Command (DUT1)

**Command**:
```bash
sonic(-router-bgp-neighbor-af)# allowas-in ?
```

**Output**:
```
  <1..10>  AS number
  origin   Only accept my AS in the as-path if the route was originated in my AS
  <cr>
```

**Analysis**:
- Help suggests `<1..10>` numeric parameter is supported
- Help shows `origin` as alternative keyword
- But numeric parameter doesn't work as advertised

**Result**: ⚠️ **Documentation mismatch with implementation**

---

## 🎯 Impact on Test Cases

### PG-17: Peer-Group with allowas-in for Many Members

**Original Test Objective**:
> Configure `allowas-in` via peer-group to allow own AS in AS-PATH for multiple neighbors

**Test Status**: ❌ **CANNOT BE IMPLEMENTED AS DESIGNED**

**Reason**:
- `allowas-in` is NOT supported at peer-group level
- Must be configured individually on each neighbor
- Defeats the purpose of peer-group inheritance

**Possible Workaround**:
```bash
# Create peer-group for other settings
router bgp 65001
peer-group ALLOWAS_GROUP
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
exit
exit
exit

# Configure allowas-in on EACH neighbor individually
neighbor 10.1.1.2 remote-as 65001
peer-group ALLOWAS_GROUP
address-family ipv4 unicast
activate
allowas-in origin  # ← Must use "origin", not numeric
exit
exit

neighbor 192.168.1.1 remote-as 65001
peer-group ALLOWAS_GROUP
address-family ipv4 unicast
activate
allowas-in origin  # ← Must repeat for EACH neighbor
exit
exit

neighbor 192.168.1.2 remote-as 65001
peer-group ALLOWAS_GROUP
address-family ipv4 unicast
activate
allowas-in origin  # ← Must repeat for EACH neighbor
exit
exit
```

**Limitations of Workaround**:
1. ❌ Must configure on each neighbor individually (tedious for many members)
2. ❌ Can only use `allowas-in origin`, not numeric count (1-10)
3. ❌ Loses peer-group inheritance benefit

---

## 🔍 Root Cause Analysis

### Why Numeric Parameter Fails

**Hypothesis 1**: Parser Bug in Klish CLI
- CLI help advertises `<1..10>` parameter
- But parser doesn't recognize numeric input
- Falls back to default keyword `origin`

**Hypothesis 2**: FRR Backend Translation Issue
- Klish CLI accepts numeric input
- Translation layer converts it to `origin` keyword
- FRR backend may only support `origin` variant

**Hypothesis 3**: Feature Not Fully Implemented
- Numeric parameter feature exists in FRR
- But not fully implemented in SONiC Klish CLI
- Help text copied from FRR but functionality missing

### How to Verify Root Cause

**Check FRR Backend Configuration**:
```bash
# On device shell (not sonic-cli)
sudo vtysh -c "show running-config" | grep -A 50 "router bgp"
```

**Expected FRR Syntax**:
```
router bgp 65001
 neighbor 10.1.1.2 remote-as 65001
 neighbor 10.1.1.2 allowas-in 3  # ← Should show numeric if working
```

**If FRR shows `origin`**: Issue is in Klish → FRR translation
**If FRR shows `3`**: Issue is only in Klish display

---

## 📊 Feature Availability Matrix

| Feature | Peer-Group | Neighbor | Works Correctly? |
|---------|------------|----------|------------------|
| `allowas-in origin` | ❌ Not Supported | ✅ Supported | ✅ YES |
| `allowas-in <1-10>` | ❌ Not Supported | ⚠️ Converts to origin | ❌ NO |
| `allowas-in` (default) | ❌ Not Supported | ❓ Not Tested | ❓ Unknown |

---

## 🧪 Recommended Tests

### Test 1: Verify FRR Backend
```bash
# Configure via Klish
sonic-cli
configure terminal
router bgp 65001
neighbor 10.1.1.2 remote-as 65001
address-family ipv4 unicast
allowas-in 3
end
exit

# Check FRR directly
sudo vtysh -c "show running-config bgp" | grep allowas
```

**Expected**: See if FRR shows `allowas-in 3` or `allowas-in origin`

---

### Test 2: Try Default (No Parameter)
```bash
sonic-cli
configure terminal
router bgp 65001
neighbor 10.1.1.2 remote-as 65001
address-family ipv4 unicast
allowas-in
end
show running-configuration bgp | grep -A 5 "neighbor 10.1.1.2"
```

**Expected**: See what default value is applied

---

### Test 3: Try Different Numeric Values
```bash
# Test with 1
allowas-in 1

# Test with 10
allowas-in 10

# Check each time
show running-configuration bgp | grep allowas
```

**Expected**: Determine if all numerics convert to `origin` or if specific values work

---

## 🎯 Summary & Conclusions

### What Works:
✅ **`allowas-in origin`** at **neighbor address-family** level
- Can be configured on individual neighbors
- Appears correctly in running-configuration
- Should function as intended (accept AS if originated locally)

### What Doesn't Work:
❌ **`allowas-in` at peer-group level** - Syntax error, not supported
❌ **`allowas-in <1-10>` numeric parameter** - Converts to `origin` instead

### Impact on Testing:
- **PG-17 test case** cannot be implemented as originally designed
- Workaround requires per-neighbor configuration (defeats inheritance purpose)
- Only `origin` variant is reliable, not numeric count

### Recommendations:
1. **Update test design** to use `allowas-in origin` at neighbor level
2. **Document limitation** in test case specification
3. **Report bug** to SONiC community about numeric parameter conversion
4. **Consider alternative test** that validates what IS supported

---

## 🐛 Potential SONiC Bug Report

**Title**: `allowas-in <1-10>` numeric parameter converts to `origin` in Klish CLI

**Description**:
When configuring `allowas-in 3` in neighbor address-family context, the command is accepted without error, but the running configuration shows `allowas-in origin` instead of `allowas-in 3`.

**Steps to Reproduce**:
1. `sonic-cli`
2. `configure terminal`
3. `router bgp 65001`
4. `neighbor 10.1.1.2 remote-as 65001`
5. `address-family ipv4 unicast`
6. `allowas-in 3`
7. `end`
8. `show running-configuration bgp`

**Expected**: `allowas-in 3`
**Actual**: `allowas-in origin`

**CLI Help Shows**: `<1..10>  AS number` is available option
**Version**: [Your SONiC version]
**Build**: [Your SONiC build]

---

**End of Analysis**
