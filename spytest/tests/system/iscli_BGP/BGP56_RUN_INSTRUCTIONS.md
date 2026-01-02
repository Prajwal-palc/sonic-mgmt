# BGP-56 Run Instructions

## ✅ **Script Ready: test_bgp56_origin_code_selection.py**

**Status:** Production-Ready with Validation Pattern
**Script Lines:** 542 lines (updated from 421)
**Validation Points:** 8
**VM Location:** 192.168.100.87 ✅ Copied

---

## 🚀 **How to Run BGP-56 on Spytest**

### **Option 1: Using bin/spytest (Recommended)**

```bash
# SSH to VM
ssh adminuser@192.168.100.87
# Password: root@123

# Navigate to spytest directory
cd /home/adminuser/draksha/sonic-mgmt/spytest

# Run BGP-56 test
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp56_origin_code_selection.py --logs-path ./logs/bgp56_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

### **Option 2: Single Line Command (from local machine)**

```bash
sshpass -p 'root@123' ssh adminuser@192.168.100.87 "cd /home/adminuser/draksha/sonic-mgmt/spytest && ./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp56_origin_code_selection.py --logs-path ./logs/bgp56_\$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native"
```

---

## 📁 **Log Location After Test Run**

```
/home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp56_<timestamp>/results_<timestamp>_logs.log
```

**Example:**
```
/home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp56_20251226_143000/results_2025_12_26_14_30_01_logs.log
```

---

## ✅ **What to Verify After Test Completes**

### 1. **Check for Cleanup Message:**
```bash
grep "CLEANUP: ALWAYS EXECUTES" /home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp56_<timestamp>/results_<timestamp>_logs.log
```

**Expected:** Should find the cleanup message

### 2. **Check Test Result:**
```bash
grep "Test PASSED\|Test FAILED\|test_case_passed" /home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp56_<timestamp>/results_<timestamp>_logs.log | tail -5
```

**Expected:** Should show "✅ BGP-56 Test PASSED" and "Test case passed @542"

### 3. **Check Validation Summary:**
```bash
grep "All validations passed\|VALIDATION FAILURES" /home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp56_<timestamp>/results_<timestamp>_logs.log
```

**Expected:** Should show "All validations passed successfully" or list of failures

### 4. **Check Cleanup Operations:**
```bash
grep "Cleaning up\|✓ Cleanup completed" /home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp56_<timestamp>/results_<timestamp>_logs.log
```

**Expected:** Should show:
- "Cleaning up route-maps on both DUTs"
- "Cleaning up BGP on DUT1 (AS 65001)"
- "Cleaning up BGP on DUT2 (AS 65002)"
- "Clearing IP configuration on both DUTs"
- "Clearing loopback configuration on both DUTs"
- "✓ Cleanup completed successfully"

---

## 📊 **Test Configuration Details**

### **BGP Origin Code Configuration:**

```
DUT1 (AS 65001) ←→ Ethernet4 ←→ DUT2 (AS 65002)
  10.1.1.1/24                      10.1.1.2/24
  Loopback: 1.1.1.1/32             Loopback: 2.2.2.2/32
  RM_ORIGIN_IGP                    RM_ORIGIN_INCOMPLETE
  Origin: IGP (i)                  Origin: Incomplete (?)
  Advertises: 1.1.1.1/32           Advertises: 2.2.2.2/32
              192.168.100.0/24                 192.168.100.0/24
```

### **Expected Behavior:**
- EBGP session establishes between AS 65001 and AS 65002
- DUT1 advertises routes with origin code IGP (i)
- DUT2 advertises routes with origin code Incomplete (?)
- Both DUTs receive 192.168.100.0/24 with different origin codes
- Origin code preference: IGP (i) > EGP (e) > Incomplete (?)

---

## 🎯 **8 Validation Points**

1. ✅ DUT1 Interface 10.1.1.1/24 configuration
2. ✅ DUT2 Interface 10.1.1.2/24 configuration
3. ✅ DUT1 Loopback 1.1.1.1/32 configuration
4. ✅ DUT2 Loopback 2.2.2.2/32 configuration
5. ✅ DUT1 Route-map RM_ORIGIN_IGP configuration (origin: IGP)
6. ✅ DUT2 Route-map RM_ORIGIN_INCOMPLETE configuration (origin: Incomplete)
7. ✅ DUT1 BGP AS 65001 configuration with neighbor 10.1.1.2
8. ✅ DUT2 BGP AS 65002 configuration with neighbor 10.1.1.1

---

## 🔧 **Cleanup Operations (ALWAYS EXECUTES)**

1. **Route-maps removed:**
   - DUT1: RM_ORIGIN_IGP
   - DUT2: RM_ORIGIN_INCOMPLETE

2. **BGP AS removed:**
   - DUT1: AS 65001
   - DUT2: AS 65002

3. **IP addresses removed:**
   - DUT1: 10.1.1.1/24
   - DUT2: 10.1.1.2/24

4. **Loopbacks removed:**
   - DUT1: Loopback0 (1.1.1.1/32)
   - DUT2: Loopback0 (2.2.2.2/32)

---

## 📋 **Quick Reference**

| Item | Details |
|------| --------|
| **Script Name** | test_bgp56_origin_code_selection.py |
| **Script Lines** | 542 (updated from 421) |
| **Testbed** | testbed_2vs.yaml |
| **VM** | 192.168.100.87 |
| **VM User** | adminuser |
| **VM Password** | root@123 |
| **DUT1 AS** | 65001 |
| **DUT2 AS** | 65002 |
| **Test Prefix** | 192.168.100.0/24 |
| **DUT1 Origin** | IGP (i) - Best |
| **DUT2 Origin** | Incomplete (?) - Worst |
| **Expected Result** | EBGP session with origin codes visible |

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

### **3. Run BGP-56:**
```bash
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_2vs.yaml system/iscli_BGP/test_bgp56_origin_code_selection.py --logs-path ./logs/bgp56_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

### **4. Find latest log:**
```bash
ls -ltr logs/ | grep bgp56 | tail -1
```

### **5. View log:**
```bash
# Replace <timestamp> with actual timestamp from step 4
cat logs/bgp56_<timestamp>/results_<timestamp>_logs.log | grep -A5 "CLEANUP\|Test PASSED\|All validations"
```

---

## 🎉 **After Running, Share Log Path:**

**Format:**
```
/home/adminuser/draksha/sonic-mgmt/spytest/logs/bgp56_YYYYMMDD_HHMMSS/results_YYYY_MM_DD_HH_MM_SS_logs.log
```

I'll verify:
- ✅ Cleanup ALWAYS EXECUTES message
- ✅ All 8 validation points
- ✅ Tech-support generation (if failures)
- ✅ Test PASSED status
- ✅ Origin code configuration (IGP vs Incomplete)

---

## 📖 **BGP Origin Code Background**

### **Origin Code Preference (BGP Best-Path Step 5):**

**Preference Order (Best to Worst):**
1. **IGP (i)** - Highest preference
   - Route learned from IGP and injected into BGP via network command

2. **EGP (e)** - Medium preference
   - Route learned from Exterior Gateway Protocol
   - Rarely used today

3. **Incomplete (?)** - Lowest preference
   - Route learned from redistribution or other means

**This Test:**
- DUT1 uses route-map to set origin to IGP (i) - highest preference
- DUT2 uses route-map to set origin to Incomplete (?) - lowest preference
- Both advertise the same prefix (192.168.100.0/24)
- Each DUT sees the same prefix with different origin codes
- Test verifies origin codes are correctly set and visible in BGP table

---

## Document Metadata

**Document:** BGP-56 Run Instructions
**Version:** 1.0
**Date:** December 26, 2024
**Script:** test_bgp56_origin_code_selection.py (542 lines)
**Status:** ✅ Ready to Run

---

**READY TO RUN!** 🚀
