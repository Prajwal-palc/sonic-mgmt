# BGP-55 Run Instructions

## ✅ **Script Ready: test_bgp55_ibgp_ebgp_selection.py**

**Status:** Production-Ready with Validation Pattern
**Script Lines:** 632 lines (updated from 528)
**Validation Points:** 13
**VM Location:** 192.168.100.87 ✅ Copied

---

## 🚀 **How to Run BGP-55 on Spytest**

### **Option 1: Using bin/spytest (Recommended)**

```bash
# SSH to VM
ssh adminuser@192.168.100.87
# Password: root@123

# Navigate to spytest directory
cd /home/adminuser/draksha/sonic-mgmt/spytest

# Run BGP-55 test
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp55_ibgp_ebgp_selection.py --logs-path ./logs/bgp55_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

### **Option 2: Single Line Command (from local machine)**

```bash
sshpass -p 'root@123' ssh adminuser@192.168.100.87 "cd /home/adminuser/draksha/sonic-mgmt/spytest && ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp55_ibgp_ebgp_selection.py --logs-path ./logs/bgp55_\$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native"
```

---

## 📁 **Log Location After Test Run**

```
/home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp55_<timestamp>/results_<timestamp>_logs.log
```

**Example:**
```
/home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp55_20251226_143000/results_2025_12_26_14_30_01_logs.log
```

---

## ✅ **What to Verify After Test Completes**

### 1. **Check for Cleanup Message:**
```bash
grep "CLEANUP: ALWAYS EXECUTES" /home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp55_<timestamp>/results_<timestamp>_logs.log
```

**Expected:** Should find the cleanup message

### 2. **Check Test Result:**
```bash
grep "Test PASSED\|Test FAILED\|test_case_passed" /home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp55_<timestamp>/results_<timestamp>_logs.log | tail -5
```

**Expected:** Should show "✅ BGP-55 Test PASSED" and "Test case passed @632"

### 3. **Check Validation Summary:**
```bash
grep "All validations passed\|VALIDATION FAILURES" /home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp55_<timestamp>/results_<timestamp>_logs.log
```

**Expected:** Should show "All validations passed successfully" or list of failures

### 4. **Check Cleanup Operations:**
```bash
grep "Cleaning up\|✓ Cleanup completed" /home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp55_<timestamp>/results_<timestamp>_logs.log
```

**Expected:** Should show:
- "Cleaning up route-maps on both DUTs"
- "Cleaning up BGP on DUT1 (AS 65001)"
- "Cleaning up BGP on DUT2 (AS 65001 and AS 65002)"
- "Clearing IP configuration on both DUTs"
- "Clearing loopback configuration on both DUTs"
- "✓ Cleanup completed successfully"

---

## 📊 **Test Configuration Details**

### **Phase 1: IBGP Configuration**
```
DUT1 (AS 65001) ←→ Ethernet4 ←→ DUT2 (AS 65001)
  10.1.1.1/24                      10.1.1.2/24
  Loopback: 1.1.1.1/32             Loopback: 2.2.2.2/32
  RM_IBGP (local-pref 100)         RM_IBGP (local-pref 100)
                                   Advertises: 192.168.100.0/24
```

### **Phase 2: EBGP Configuration**
```
DUT1 (AS 65001) ←→ Ethernet4 ←→ DUT2 (AS 65002)
  10.1.1.1/24                      10.1.1.2/24
  Loopback: 1.1.1.1/32             Loopback: 2.2.2.2/32
  RM_EBGP (local-pref 100)         RM_EBGP (local-pref 100)
  Receives: 192.168.100.0/24       Advertises: 192.168.100.0/24
```

### **Expected Behavior:**
- IBGP session establishes first (both AS 65001)
- DUT2 changes to AS 65002 (becomes EBGP)
- EBGP route is preferred over IBGP route (BGP best-path step 7)
- Both routes have same local-preference (100)
- EBGP wins because it's preferred when all other attributes are equal

---

## 🎯 **13 Validation Points**

1. ✅ DUT1 Interface 10.1.1.1/24 configuration
2. ✅ DUT2 Interface 10.1.1.2/24 configuration
3. ✅ DUT1 Loopback 1.1.1.1/32 configuration
4. ✅ DUT2 Loopback 2.2.2.2/32 configuration
5. ✅ DUT1 Route-map RM_IBGP configuration
6. ✅ DUT1 Route-map RM_EBGP configuration
7. ✅ DUT1 BGP AS 65001 configuration (IBGP phase)
8. ✅ DUT2 BGP AS 65001 configuration (IBGP phase)
9. ✅ DUT1 IBGP neighbor to 10.1.1.2 configuration
10. ✅ DUT2 IBGP neighbor to 10.1.1.1 configuration
11. ✅ DUT2 BGP AS change from 65001 to 65002
12. ✅ DUT2 EBGP neighbor to 10.1.1.1 configuration
13. ✅ DUT1 EBGP neighbor to 10.1.1.2 configuration

---

## 🔧 **Cleanup Operations (ALWAYS EXECUTES)**

1. **Route-maps removed:**
   - DUT1: RM_IBGP, RM_EBGP
   - DUT2: RM_IBGP, RM_EBGP

2. **BGP AS removed:**
   - DUT1: AS 65001
   - DUT2: AS 65001 and AS 65002

3. **IP addresses removed:**
   - DUT1: 10.1.1.1/24
   - DUT2: 10.1.1.2/24

4. **Loopbacks removed:**
   - DUT1: Loopback0 (1.1.1.1/32)
   - DUT2: Loopback0 (2.2.2.2/32)

---

## 📋 **Quick Reference**

| Item | Details |
|------|---------|
| **Script Name** | test_bgp55_ibgp_ebgp_selection.py |
| **Script Lines** | 632 (updated from 528) |
| **Testbed** | testbed_2vs.yaml |
| **VM** | 192.168.100.87 |
| **VM User** | adminuser |
| **VM Password** | root@123 |
| **DUT1 AS** | 65001 |
| **DUT2 AS (Phase 1)** | 65001 (IBGP) |
| **DUT2 AS (Phase 2)** | 65002 (EBGP) |
| **Test Prefix** | 192.168.100.0/24 |
| **Local-pref** | 100 (same for both) |
| **Expected Result** | EBGP route preferred |

---

## ⚡ **Copy-Paste Commands**

### **1. SSH to VM:**
```bash
ssh adminuser@192.168.100.87
```

### **2. Navigate to spytest:**
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest
```

### **3. Run BGP-55:**
```bash
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp55_ibgp_ebgp_selection.py --logs-path ./logs/bgp55_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

### **4. Find latest log:**
```bash
ls -ltr logs/ | grep bgp55 | tail -1
```

### **5. View log:**
```bash
# Replace <timestamp> with actual timestamp from step 4
cat logs/bgp55_<timestamp>/results_<timestamp>_logs.log | grep -A5 "CLEANUP\|Test PASSED\|All validations"
```

---

## 🎉 **After Running, Share Log Path:**

**Format:**
```
/home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp55_YYYYMMDD_HHMMSS/results_YYYY_MM_DD_HH_MM_SS_logs.log
```

I'll verify:
- ✅ Cleanup ALWAYS EXECUTES message
- ✅ All 13 validation points
- ✅ Tech-support generation (if failures)
- ✅ Test PASSED status
- ✅ IBGP → EBGP configuration transition

---

## Document Metadata

**Document:** BGP-55 Run Instructions
**Version:** 1.0
**Date:** December 26, 2024
**Script:** test_bgp55_ibgp_ebgp_selection.py (632 lines)
**Status:** ✅ Ready to Run

---

**READY TO RUN! 🚀**
