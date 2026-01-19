# BGP-55 Script Update Requirements

## Current Status

**Script:** test_bgp55_ibgp_ebgp_selection.py
**Current Lines:** 528 lines
**Pattern Compliance:** ❌ NO - Uses st.report_fail() which causes immediate exit
**Needs Update:** YES

---

## Issues Found

### ❌ **Uses st.report_fail() - Immediate Exit on Errors**

The script has **7 st.report_fail()** calls that cause immediate exit:

1. **Line 411:** `st.report_fail("interface_config_failed", vars.D1)` - DUT1 interface
2. **Line 414:** `st.report_fail("interface_config_failed", vars.D2)` - DUT2 interface
3. **Line 417:** `st.report_fail("loopback_config_failed", vars.D1)` - DUT1 loopback
4. **Line 420:** `st.report_fail("loopback_config_failed", vars.D2)` - DUT2 loopback
5. **Line 425:** `st.report_fail("routemap_config_failed", vars.D1)` - Route-map RM_IBGP
6. **Line 428:** `st.report_fail("routemap_config_failed", vars.D1)` - Route-map RM_EBGP
7. **Line 437:** `st.report_fail("bgp_config_failed", vars.D1)` - BGP AS 65001 on DUT1
8. **Line 440:** `st.report_fail("bgp_config_failed", vars.D2)` - BGP AS 65001 on DUT2
9. **Line 446:** `st.report_fail("neighbor_config_failed", vars.D1)` - IBGP neighbor on DUT1
10. **Line 450:** `st.report_fail("neighbor_config_failed", vars.D2)` - IBGP neighbor on DUT2
11. **Line 478:** `st.report_fail("bgp_as_change_failed", vars.D2)` - BGP AS change
12. **Line 484:** `st.report_fail("neighbor_config_failed", vars.D2)` - EBGP neighbor on DUT2
13. **Line 498:** `st.report_fail("neighbor_config_failed", vars.D1)` - EBGP neighbor on DUT1

**Total:** 13 immediate exit points that need conversion

---

## Required Changes

### 1. Update Documentation Header (Lines 1-34)

**Change:**
```python
How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  ./RUN_BGP55.sh
```

**To:**
```python
How to run:
  cd /home/adminuser/draksha/sonic-mgmt/spytest
  ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp55_ibgp_ebgp_selection.py --logs-path ./logs/bgp55_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

**Add:**
```python
Pre-requisites:
  - Testbed: testbed_2vs.yaml
  - Devices: 2-DUT topology with Ethernet4 connectivity
  - CLI Type: Klish

Validation Pattern:
  ✅ Validation errors tracked but don't cause immediate exit
  ✅ Script completes execution till unconfiguration (cleanup in finally block)
  ✅ Tech-support generated after unconfiguration on failures
  ✅ All validations reported at end
```

### 2. Add Validation Tracking (After line 407)

**Add these lines after the banner:**
```python
# Track validation failures - test will continue but report fail at end
validation_failures = []
tech_support_generated = False

try:
```

### 3. Convert All st.report_fail() Calls

**Pattern to follow for each st.report_fail():**

**OLD:**
```python
if not configure_ip_interface(vars.D1, CONFIG.dut1_ip):
    st.report_fail("interface_config_failed", vars.D1)
```

**NEW:**
```python
if not configure_ip_interface(vars.D1, CONFIG.dut1_ip):
    error_msg = f"Interface configuration failed on {vars.D1}"
    st.error(error_msg)
    validation_failures.append(error_msg)
```

### 4. Add Exception Handling

**After line 517 (after verify_ebgp_preference call), add:**
```python
    except Exception as e:
        error_msg = f"Unexpected exception during test execution: {str(e)}"
        st.error(error_msg)
        validation_failures.append(error_msg)
```

### 5. Add Finally Block (Cleanup Always Executes)

**Add after exception block:**
```python
    finally:
        # Cleanup ALWAYS executes - regardless of test success or failure
        st.banner("=" * 80)
        st.banner("CLEANUP: Unconfiguring Route-maps, BGP and IP (ALWAYS EXECUTES)")
        st.banner("=" * 80)

        try:
            # Cleanup route-maps on both DUTs
            st.log("Cleaning up route-maps on both DUTs")
            cleanup_routemaps(vars.D1)
            cleanup_routemaps(vars.D2)

            # Cleanup BGP configuration on both DUTs
            st.log(f"Cleaning up BGP on DUT1 (AS {CONFIG.dut1_asn})")
            cleanup_bgp_config(vars.D1, CONFIG.dut1_asn)

            st.log(f"Cleaning up BGP on DUT2 (AS {CONFIG.dut2_asn_ibgp} and AS {CONFIG.dut2_asn_ebgp})")
            cleanup_bgp_config(vars.D2, CONFIG.dut2_asn_ibgp)
            cleanup_bgp_config(vars.D2, CONFIG.dut2_asn_ebgp)

            # Clear IP configuration
            st.log("Clearing IP configuration on both DUTs")
            cleanup_ip_interface(vars.D1, CONFIG.dut1_ip)
            cleanup_ip_interface(vars.D2, CONFIG.dut2_ip)

            # Clear loopback configuration
            st.log("Clearing loopback configuration on both DUTs")
            cleanup_loopback(vars.D1)
            cleanup_loopback(vars.D2)

            st.log("✓ Cleanup completed successfully")

        except Exception as cleanup_error:
            st.error(f"Error during cleanup: {str(cleanup_error)}")
            validation_failures.append(f"Cleanup error: {str(cleanup_error)}")
```

### 6. Add Tech-Support Generation

**Add after finally block:**
```python
    # Generate tech-support if there were validation failures
    if validation_failures and not tech_support_generated:
        st.banner("=" * 80)
        st.banner("GENERATING TECH-SUPPORT (Validation Failures Detected)")
        st.banner("=" * 80)
        try:
            st.generate_tech_support([vars.D1, vars.D2], "bgp55_validation_failures")
            tech_support_generated = True
            st.log("✓ Tech-support generated successfully")
        except Exception as ts_error:
            st.error(f"Failed to generate tech-support: {str(ts_error)}")
```

### 7. Add Final Reporting

**Replace lines 519-527 with:**
```python
    # Final reporting
    if validation_failures:
        st.log("\n" + "!" * 80)
        st.log("VALIDATION FAILURES DETECTED:")
        for idx, failure in enumerate(validation_failures, 1):
            st.error(f"{idx}. {failure}")
        st.log("!" * 80)
        st.log(f"\nNote: Cleanup and unconfiguration completed despite {len(validation_failures)} validation failure(s)")
        st.log("Tech-support has been generated for debugging")
        st.report_fail("msg", f"Test completed with {len(validation_failures)} validation failure(s). Cleanup executed. See errors above.")
    else:
        st.log("All validations passed successfully")
        st.log("=" * 80)
        st.log("✅ BGP-55 Test PASSED: EBGP vs IBGP Path Selection")
        st.log("   CONFIGURATION:")
        st.log(f"   - DUT1 (AS {CONFIG.dut1_asn}): Receives routes via EBGP")
        st.log(f"   - DUT2 (AS {CONFIG.dut2_asn_ebgp}): Advertises {CONFIG.test_prefix}")
        st.log(f"   - Same local-preference ({CONFIG.local_pref}) for both IBGP and EBGP")
        st.log("   - EBGP route preferred (step 7 in BGP best-path algorithm)")
        st.log("=" * 80)
        st.report_pass("test_case_passed")
```

---

## Detailed Line-by-Line Changes

### **Lines to Change:**

| Current Line | Current Code | New Code | Reason |
|--------------|--------------|----------|--------|
| 411 | `st.report_fail("interface_config_failed", vars.D1)` | `error_msg = f"Interface configuration failed on {vars.D1}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 414 | `st.report_fail("interface_config_failed", vars.D2)` | `error_msg = f"Interface configuration failed on {vars.D2}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 417 | `st.report_fail("loopback_config_failed", vars.D1)` | `error_msg = f"Loopback configuration failed on {vars.D1}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 420 | `st.report_fail("loopback_config_failed", vars.D2)` | `error_msg = f"Loopback configuration failed on {vars.D2}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 425 | `st.report_fail("routemap_config_failed", vars.D1)` | `error_msg = f"Route-map {CONFIG.rm_ibgp} configuration failed on {vars.D1}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 428 | `st.report_fail("routemap_config_failed", vars.D1)` | `error_msg = f"Route-map {CONFIG.rm_ebgp} configuration failed on {vars.D1}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 437 | `st.report_fail("bgp_config_failed", vars.D1)` | `error_msg = f"BGP AS {CONFIG.dut1_asn} configuration failed on {vars.D1}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 440 | `st.report_fail("bgp_config_failed", vars.D2)` | `error_msg = f"BGP AS {CONFIG.dut2_asn_ibgp} configuration failed on {vars.D2}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 446 | `st.report_fail("neighbor_config_failed", vars.D1)` | `error_msg = f"IBGP neighbor configuration failed on {vars.D1}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 450 | `st.report_fail("neighbor_config_failed", vars.D2)` | `error_msg = f"IBGP neighbor configuration failed on {vars.D2}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 478 | `st.report_fail("bgp_as_change_failed", vars.D2)` | `error_msg = f"BGP AS change from {CONFIG.dut2_asn_ibgp} to {CONFIG.dut2_asn_ebgp} failed on {vars.D2}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 484 | `st.report_fail("neighbor_config_failed", vars.D2)` | `error_msg = f"EBGP neighbor configuration failed on {vars.D2}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |
| 498 | `st.report_fail("neighbor_config_failed", vars.D1)` | `error_msg = f"EBGP neighbor configuration failed on {vars.D1}"`<br>`st.error(error_msg)`<br>`validation_failures.append(error_msg)` | Track error, continue |

---

## Expected Result After Update

**New Script Length:** ~680 lines (152 lines added)
**Pattern Compliance:** ✅ YES
**Validation Tracking Points:** 13
**Cleanup:** Always executes in finally block
**Tech-Support:** Generated on failures

---

## Test Configuration (BGP-55)

### **Phase 1: IBGP Configuration**
| Component | DUT1 | DUT2 |
|-----------|------|------|
| **AS Number** | 65001 | 65001 (IBGP) |
| **Router ID** | 1.1.1.1 | 2.2.2.2 |
| **IP Address** | 10.1.1.1/24 | 10.1.1.2/24 |
| **Loopback** | 1.1.1.1/32 | 2.2.2.2/32 |
| **Route-map** | RM_IBGP | RM_IBGP |
| **Local-pref** | 100 | 100 |

### **Phase 2: EBGP Configuration**
| Component | DUT1 | DUT2 |
|-----------|------|------|
| **AS Number** | 65001 | **65002 (EBGP)** |
| **Router ID** | 1.1.1.1 | 2.2.2.2 |
| **IP Address** | 10.1.1.1/24 | 10.1.1.2/24 |
| **Loopback** | 1.1.1.1/32 | 2.2.2.2/32 |
| **Route-map** | RM_EBGP | RM_EBGP |
| **Local-pref** | 100 | 100 |
| **Test Prefix** | - | 192.168.100.0/24 |

### **Expected Behavior:**
- IBGP session establishes first (both AS 65001)
- DUT2 changes to AS 65002 (becomes EBGP)
- EBGP route is preferred over IBGP route (BGP best-path step 7)
- "show bgp ipv4 unicast" shows EBGP route as best path (marked with ">")

---

## Validation Points (13 Total)

1. ✅ DUT1 interface configuration (10.1.1.1/24)
2. ✅ DUT2 interface configuration (10.1.1.2/24)
3. ✅ DUT1 loopback configuration (1.1.1.1/32)
4. ✅ DUT2 loopback configuration (2.2.2.2/32)
5. ✅ DUT1 route-map RM_IBGP configuration
6. ✅ DUT1 route-map RM_EBGP configuration
7. ✅ DUT1 BGP AS 65001 configuration
8. ✅ DUT2 BGP AS 65001 configuration (IBGP phase)
9. ✅ DUT1 IBGP neighbor configuration
10. ✅ DUT2 IBGP neighbor configuration
11. ✅ DUT2 BGP AS change (65001 → 65002)
12. ✅ DUT2 EBGP neighbor configuration
13. ✅ DUT1 EBGP neighbor configuration

---

## Cleanup Operations

### **Cleanup ALWAYS Executes (Finally Block):**

1. **Route-maps:** RM_IBGP, RM_EBGP on both DUTs
2. **BGP AS 65001:** Removed from DUT1
3. **BGP AS 65001 and 65002:** Removed from DUT2
4. **IP Addresses:** 10.1.1.1/24 and 10.1.1.2/24 removed
5. **Loopbacks:** Loopback0 removed from both DUTs

---

## Spytest Run Command

```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp55_ibgp_ebgp_selection.py --logs-path ./logs/bgp55_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

---

## Next Step

**Do you want me to:**
1. ✅ Create the complete corrected BGP-55 script with all changes applied?
2. ✅ Or provide more detailed step-by-step instructions?

The script is complex (528 lines → ~680 lines) with 13 validation points and 2-phase testing (IBGP → EBGP). I recommend creating a clean new version to avoid any syntax errors.

---

## Document Metadata

**Document:** BGP-55 Required Changes
**Version:** 1.0
**Date:** December 26, 2024
**Script:** test_bgp55_ibgp_ebgp_selection.py
**Current Status:** ❌ Needs Update (13 st.report_fail() calls)
**Target Status:** ✅ Validation Pattern Compliant

---

**END OF REQUIRED CHANGES DOCUMENT**
