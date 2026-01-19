# BGP-58 Update Summary - Next-hop Reachability Dependency Test

## Update Details

**Script:** test_bgp58_nexthop_reachability.py
**Updated:** December 26, 2024
**Original Lines:** 494
**Updated Lines:** 628
**Lines Added:** 134

---

## What Was Updated

### 1. **Validation Pattern Implementation** ✅

**Added validation tracking instead of immediate exit:**
```python
# Lines 391-392: Initialize tracking
validation_failures = []
tech_support_generated = False
```

**Replaced 9 st.report_fail() calls with validation tracking:**

| Line | Original Issue | Updated Behavior |
|------|---------------|------------------|
| 385 | `st.report_fail("interface_config_failed", vars.D1)` | Appends error to validation_failures, continues |
| 388 | `st.report_fail("interface_config_failed", vars.D2)` | Appends error to validation_failures, continues |
| 391 | `st.report_fail("loopback_config_failed", vars.D1)` | Appends error to validation_failures, continues |
| 394 | `st.report_fail("loopback_config_failed", vars.D1)` | Appends error to validation_failures, continues |
| 397 | `st.report_fail("loopback_config_failed", vars.D2)` | Appends error to validation_failures, continues |
| 400 | `st.report_fail("loopback_config_failed", vars.D2)` | Appends error to validation_failures, continues |
| 405 | `st.report_fail("routemap_config_failed", vars.D2)` | Appends error to validation_failures, continues |
| 411 | `st.report_fail("bgp_config_failed", vars.D1)` | Appends error to validation_failures, continues |
| 415 | `st.report_fail("bgp_config_failed", vars.D2)` | Appends error to validation_failures, continues |

---

### 2. **Try-Except-Finally Structure** ✅

**Added comprehensive exception handling:**
```python
# Line 399-551: Main test execution in try block
try:
    # All test steps with validation tracking
    # Step 1: Configure interfaces and loopbacks (6 validations)
    # Step 2: Configure route-map with next-hop (1 validation)
    # Step 3: Configure BGP (2 validations)
    # Step 4: Advertise networks
    # Step 5: Wait for BGP convergence
    # PHASE 1: Next-hop reachable (configure static route)
    # PHASE 2: Next-hop unreachable (remove static route)
    # PHASE 3: Next-hop reachable again (restore static route)

# Line 547-551: Catch any exceptions
except Exception as e:
    validation_failures.append(f"Exception: {str(e)}")

# Line 553-595: Cleanup ALWAYS executes
finally:
    # Cleanup wrapped in try-except to catch cleanup errors
```

---

### 3. **Cleanup Always Executes** ✅

**Finally block ensures cleanup runs regardless of test outcome:**
```python
# Lines 553-595: Finally block
finally:
    st.banner("CLEANUP: Unconfiguring Static Route, Route-maps, BGP and IP (ALWAYS EXECUTES)")

    try:
        # Static route cleanup
        cleanup_static_route(vars.D1)

        # Route-maps cleanup
        cleanup_routemaps(vars.D2)

        # BGP cleanup
        cleanup_bgp_config(vars.D1)  # AS 65001
        cleanup_bgp_config(vars.D2)  # AS 65002

        # Interface cleanup
        cleanup_ip_interface(vars.D1, CONFIG.dut1_ip)
        cleanup_ip_interface(vars.D2, CONFIG.dut2_ip)

        # Loopback cleanup (4 loopbacks total)
        cleanup_loopback(vars.D1, "Loopback0")
        cleanup_loopback(vars.D1, "Loopback1")
        cleanup_loopback(vars.D2, "Loopback0")
        cleanup_loopback(vars.D2, "Loopback1")

    except Exception as cleanup_error:
        validation_failures.append(f"Cleanup error: {str(cleanup_error)}")
```

---

### 4. **Tech-Support Generation** ✅

**Auto-generates tech-support when validation failures occur:**
```python
# Lines 588-595: Tech-support generation
if validation_failures and not tech_support_generated:
    st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
    try:
        st.generate_tech_support(dut_list=[vars.D1, vars.D2], name="bgp58_validation_failures")
        tech_support_generated = True
    except Exception as tech_error:
        st.error(f"Failed to generate tech-support: {tech_error}")
```

---

### 5. **Final Reporting** ✅

**Comprehensive final report with all validation results and phase tracking:**
```python
# Lines 597-628: Final reporting
st.banner("BGP-58 TEST FINAL REPORT")

if validation_failures:
    st.error("VALIDATION FAILURES DETECTED:")
    for idx, failure in enumerate(validation_failures, 1):
        st.error(f"ERROR {idx}. {failure}")
    st.log(f"Note: Cleanup completed despite {len(validation_failures)} failures")
    st.log("Tech-support has been generated for debugging")
    st.report_fail("msg", f"Test completed with {len(validation_failures)} failures")
else:
    st.log("All validations passed successfully")
    st.log("✅ BGP-58 Test PASSED: Next-hop Reachability Dependency")
    st.log(f"   - Phase 1 (with static route): Route in RIB = {route_in_rib_phase1}")
    st.log(f"   - Phase 2 (without static route): Route in RIB = {route_in_rib_phase2}")
    st.log(f"   - Phase 3 (restored static route): Route in RIB = {route_in_rib_phase3}")
    st.report_pass("test_case_passed")
```

---

### 6. **Testbed Updated** ✅

**Changed from hardcoded testbed to testbed_2vs.yaml:**
```python
# Line 32: Updated testbed reference
- Testbed: testbed_bgp55.yaml  # OLD
+ Testbed: testbed_2vs.yaml    # NEW
```

**Updated run command in docstring:**
```bash
# Line 9: Updated run command
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  system/iscli_BGP/test_bgp58_nexthop_reachability.py \
  --logs-path ./logs/bgp58_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## Validation Points

### **9 Critical Validation Points:**

1. ✅ **DUT1 Interface Configuration** - 10.1.1.1/24
2. ✅ **DUT2 Interface Configuration** - 10.1.1.2/24
3. ✅ **DUT1 Loopback0 Configuration** - 1.1.1.1/32
4. ✅ **DUT1 Loopback1 Configuration** - 100.1.1.1/32
5. ✅ **DUT2 Loopback0 Configuration** - 2.2.2.2/32
6. ✅ **DUT2 Loopback1 Configuration** - 100.1.1.2/32
7. ✅ **DUT2 Route-map Configuration** - RM_NEXT_HOP (set next-hop 100.1.1.2)
8. ✅ **DUT1 BGP Configuration** - AS 65001
9. ✅ **DUT2 BGP Configuration** - AS 65002 with route-map

---

## Test Configuration

### **3-Phase Next-hop Reachability Testing:**

```
DUT1 (AS 65001) ←→ Ethernet4 ←→ DUT2 (AS 65002)
  10.1.1.1/24                      10.1.1.2/24
  Loopback0: 1.1.1.1/32            Loopback0: 2.2.2.2/32
  Loopback1: 100.1.1.1/32          Loopback1: 100.1.1.2/32
                                   RM_NEXT_HOP: set next-hop 100.1.1.2
                                   Advertises: 192.168.100.0/24
```

**Phase 1: Next-hop REACHABLE**
```
DUT1:
  Static Route: 100.1.1.2/32 via 10.1.1.2  ✅ Configured
  Next-hop: 100.1.1.2  ✅ Reachable
  Route 192.168.100.0/24:  ✅ Installed in RIB
```

**Phase 2: Next-hop UNREACHABLE**
```
DUT1:
  Static Route: 100.1.1.2/32 via 10.1.1.2  ❌ Removed
  Next-hop: 100.1.1.2  ❌ Unreachable
  Route 192.168.100.0/24:  ❌ NOT in RIB (next-hop check failed)
```

**Phase 3: Next-hop REACHABLE AGAIN**
```
DUT1:
  Static Route: 100.1.1.2/32 via 10.1.1.2  ✅ Restored
  Next-hop: 100.1.1.2  ✅ Reachable
  Route 192.168.100.0/24:  ✅ Reinstalled in RIB
```

---

## Expected Behavior

**BGP Next-hop Reachability Rule:**
- BGP routes are **ONLY** installed in the routing table if the next-hop is reachable
- Next-hop reachability is checked via recursive route lookup
- If next-hop becomes unreachable, route is removed from RIB (but stays in BGP table)
- When next-hop becomes reachable again, route is reinstalled in RIB

**Test Validates:**
1. ✅ Routes installed when next-hop reachable (Phase 1)
2. ✅ Routes withdrawn when next-hop unreachable (Phase 2)
3. ✅ Routes reinstalled when next-hop restored (Phase 3)

---

## Cleanup Operations

**Cleanup ALWAYS executes in finally block:**

1. **Static route removed:**
   - DUT1: 100.1.1.2/32 via 10.1.1.2

2. **Route-maps removed:**
   - DUT2: RM_NEXT_HOP

3. **BGP AS removed:**
   - DUT1: AS 65001
   - DUT2: AS 65002

4. **IP addresses removed:**
   - DUT1: 10.1.1.1/24
   - DUT2: 10.1.1.2/24

5. **Loopbacks removed:**
   - DUT1: Loopback0 (1.1.1.1/32), Loopback1 (100.1.1.1/32)
   - DUT2: Loopback0 (2.2.2.2/32), Loopback1 (100.1.1.2/32)

---

## Code Changes Summary

### **Before → After Comparison**

| Aspect | Before | After |
|--------|--------|-------|
| **Lines** | 494 | 628 |
| **Immediate exits** | 9 st.report_fail() | 0 (all tracked) |
| **Validation tracking** | ❌ None | ✅ validation_failures list |
| **Exception handling** | ❌ None | ✅ try-except-finally |
| **Cleanup guarantee** | ⚠️ Module epilogue only | ✅ Finally block |
| **Tech-support** | ❌ Manual | ✅ Auto-generated on failures |
| **Final reporting** | ⚠️ Basic | ✅ Comprehensive with phase tracking |
| **Testbed** | testbed_bgp55.yaml | testbed_2vs.yaml |
| **Phase tracking** | ❌ None | ✅ route_in_rib_phase1/2/3 variables |

---

## How to Run

### **SSH to VM:**
```bash
ssh adminuser@192.168.100.87
# Password: root@123
```

### **Navigate to spytest:**
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest
```

### **Run BGP-58:**
```bash
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml \
  system/iscli_BGP/test_bgp58_nexthop_reachability.py \
  --logs-path ./logs/bgp58_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## Pattern Compliance

| Pattern Element | Required | Implemented | Status |
|----------------|----------|-------------|--------|
| **Validation tracking** | ✅ Yes | ✅ Yes | ✅ PASS |
| **Script continues on errors** | ✅ Yes | ✅ Yes | ✅ PASS |
| **Cleanup always executes** | ✅ Yes | ✅ Yes | ✅ PASS |
| **Tech-support on failures** | ✅ Yes | ✅ Yes | ✅ PASS |
| **Final reporting** | ✅ Yes | ✅ Yes | ✅ PASS |
| **Complete till unconfiguration** | ✅ Yes | ✅ Yes | ✅ PASS |

**Pattern Compliance:** ✅ **100%**

---

## Files Status

| File | Location | Lines | Status |
|------|----------|-------|--------|
| **test_bgp58_nexthop_reachability.py** | Local | 628 | ✅ Updated |
| **test_bgp58_nexthop_reachability.py** | VM (192.168.100.87) | 628 | ✅ Copied |
| **BGP58_UPDATE_SUMMARY.md** | Local | - | ✅ Created |

---

## Document Metadata

**Document:** BGP-58 Update Summary
**Version:** 1.0
**Date:** December 26, 2024
**Script Version:** 628 lines
**Pattern Status:** ✅ 100% Compliant
**VM Status:** ✅ Copied to 192.168.100.87

---

**READY TO RUN!** 🚀

The BGP-58 script is now updated with the complete validation pattern and ready for testing on spytest. This test validates the critical concept that BGP routes are only installed if their next-hop is reachable via recursive route lookup.
