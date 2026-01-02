# IS-CLI Separate Test Scripts - README

**Created**: 30-Dec-2025
**Purpose**: Individual test scripts for each IS-CLI Drop 1 feature

---

## 📦 Individual Test Scripts Created

### 1. **test_platform_components.py** - Platform Components
**Feature**: SM_ISCLI_DROP1_FEATURE1
**Tests**: 9
**File Size**: ~9KB

**What it tests**:
- ✓ show platform summary (IS-CLI)
- ✓ show platform summary --json (expect failure - BUG)
- ✓ show platform summary (Admin Shell)
- ✓ show platform psustatus
- ✓ show platform temperature
- ✓ show platform fan
- ✓ show platform ssdhealth
- ✓ show platform pcieinfo
- ✓ show platform pcieinfo --check

**Bugs Found**: 2 (IS-CLI flags, missing pcie.yaml)

---

### 2. **test_ztp.py** - ZTP (Zero Touch Provisioning)
**Feature**: SM_ISCLI_DROP1_FEATURE2
**Tests**: 6
**File Size**: ~7KB

**What it tests**:
- ✓ show ztp-status (IS-CLI)
- ✓ sudo config ztp enable
- ✓ Verify ZTP enabled
- ✓ sudo config ztp disable
- ✓ Verify ZTP disabled
- ✓ systemctl status ztp.service

**Bugs Found**: 0 (✅ ALL TESTS PASS - Perfect!)

---

### 3. **test_ntp.py** - NTP (Network Time Protocol)
**Feature**: SM_ISCLI_DROP1_FEATURE7
**Tests**: 13
**File Size**: ~10KB

**What it tests**:
- ✓ show ntp (expect ambiguous - BUG)
- ✓ show ntp server
- ✓ show ntp associations
- ✓ show ntp global
- ✓ sudo config ntp add <IP>
- ✓ Verify NTP server added
- ✓ sudo config ntp add --association-type pool
- ✓ sudo config ntp add <hostname> (expect failure - BUG)
- ✓ sudo config ntp del <IP>
- ✓ chronyc tracking
- ✓ chronyc sources
- ✓ redis-cli CONFIG_DB check
- ✓ ip vrf exec mgmt ping

**Bugs Found**: 2 (show ntp ambiguous, hostname validation)

---

### 4. **test_clear_arp_nd.py** - Clear ARP/ND
**Feature**: SM_ISCLI_DROP1_FEATURE8
**Tests**: 9
**File Size**: ~9KB

**What it tests**:
- ✓ ip neigh show
- ✓ sonic-clear arp (with timing)
- ✓ Verify ARP cleared
- ✓ ARP repopulation test
- ✓ ip -6 neigh show
- ✓ sonic-clear ndp
- ✓ Multiple ARP clears (stability)
- ✓ show arp in IS-CLI (expect failure - BUG)
- ✓ show ndp in IS-CLI (expect failure - BUG)

**Bugs Found**: 1 (show arp/ndp not in IS-CLI)

---

## 🚀 How to Use

### Run Individual Scripts

```bash
# On your local machine
cd /home/hp/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/iscli_testing/

# Copy to VM
scp test_platform_components.py admin@192.168.100.87:~/
scp test_ztp.py admin@192.168.100.87:~/
scp test_ntp.py admin@192.168.100.87:~/
scp test_clear_arp_nd.py admin@192.168.100.87:~/

# SSH to VM and run
ssh admin@192.168.100.87

# Run individual tests
sudo python3 test_platform_components.py
sudo python3 test_ztp.py
sudo python3 test_ntp.py
sudo python3 test_clear_arp_nd.py
```

### Run All Scripts in Sequence

```bash
# On VM
sudo python3 test_platform_components.py
sudo python3 test_ztp.py
sudo python3 test_ntp.py
sudo python3 test_clear_arp_nd.py
```

---

## 📊 Expected Output

Each script provides:

### Console Output (Colored)
```
======================================================================
IS-CLI PLATFORM COMPONENTS TEST SUITE
Feature: SM_ISCLI_DROP1_FEATURE1
Started: 2025-12-30 HH:MM:SS
======================================================================

Test 1: show platform summary (IS-CLI)
  [✓ PASS] show platform summary (IS-CLI)
      Note: Should display platform information in IS-CLI mode

Test 2: show platform summary --json (expect failure)
  [✓ PASS] show platform summary --json (should fail)
      Note: BUG: Flags not supported in IS-CLI

...

======================================================================
PLATFORM COMPONENTS TEST SUMMARY
======================================================================

  Total Tests: 9
  Passed: 9
  Failed: 0
  Skipped: 0
  Pass Rate: 100.0%

  Test Duration: 12.3 seconds

  Detailed report saved to: platform_test_report_20251230_HHMMSS.json

BUGS FOUND:
  1. IS-CLI flags not supported (--json, --verbose)
  2. Missing pcie.yaml configuration file

  See JIRA_BUGS_TEMPLATE.md for details
```

### JSON Report Files Generated

Each script creates its own JSON report:
- `platform_test_report_YYYYMMDD_HHMMSS.json`
- `ztp_test_report_YYYYMMDD_HHMMSS.json`
- `ntp_test_report_YYYYMMDD_HHMMSS.json`
- `clear_arp_nd_test_report_YYYYMMDD_HHMMSS.json`

---

## 📋 Comparison: Combined vs Separate Scripts

### Combined Script (iscli_test_suite.py)
**Pros:**
- ✓ One file to manage
- ✓ One execution for all tests
- ✓ Single comprehensive report

**Cons:**
- ✗ Must run all tests even if only one feature changed
- ✗ Longer execution time (~45 seconds)
- ✗ Harder to debug specific feature issues

### Separate Scripts
**Pros:**
- ✓ Test individual features in isolation
- ✓ Faster execution for single feature (~10-15 seconds each)
- ✓ Easy to debug specific feature
- ✓ Can run in parallel on different VMs
- ✓ Individual JSON reports

**Cons:**
- ✗ Multiple files to manage
- ✗ Need to run 4 scripts for complete testing

---

## 🎯 When to Use Which

### Use Combined Script (iscli_test_suite.py) when:
- Running complete regression testing
- Testing new SONiC build
- Creating comprehensive test report
- Need single execution command

### Use Separate Scripts when:
- Testing specific feature after bug fix
- Debugging feature-specific issues
- Developing/modifying specific feature
- Running parallel tests on multiple VMs
- Time-constrained (only test what changed)

---

## 📈 Test Matrix

| Script | Feature | Tests | Execution Time | Bugs | Status |
|--------|---------|-------|----------------|------|--------|
| test_platform_components.py | Platform | 9 | ~12s | 2 | ⚠️ Partial |
| test_ztp.py | ZTP | 6 | ~10s | 0 | ✅ Perfect |
| test_ntp.py | NTP | 13 | ~15s | 2 | ⚠️ Partial |
| test_clear_arp_nd.py | Clear ARP/ND | 9 | ~8s | 1 | ⚠️ Partial |
| **TOTAL** | **4 Features** | **37** | **~45s** | **5** | **78.4%** |

---

## 🐛 Bugs by Script

### test_platform_components.py (2 bugs)
1. 🔴 HIGH: IS-CLI flags not supported
2. 🟢 LOW: Missing pcie.yaml file

### test_ztp.py (0 bugs)
✅ NO BUGS - All tests passing!

### test_ntp.py (2 bugs)
1. 🔴 HIGH: show ntp command ambiguous
2. 🟡 MEDIUM: NTP hostname validation inconsistent

### test_clear_arp_nd.py (1 bug)
1. 🟡 MEDIUM: show arp/ndp not in IS-CLI

---

## 💡 Quick Tips

### Run Only Failed Features
```bash
# If ZTP is working (0 bugs), skip it
sudo python3 test_platform_components.py  # Has bugs
# Skip: sudo python3 test_ztp.py
sudo python3 test_ntp.py                  # Has bugs
sudo python3 test_clear_arp_nd.py         # Has bugs
```

### Run Tests in Background
```bash
# Run all tests in background, redirect output
nohup sudo python3 test_platform_components.py > platform.log 2>&1 &
nohup sudo python3 test_ztp.py > ztp.log 2>&1 &
nohup sudo python3 test_ntp.py > ntp.log 2>&1 &
nohup sudo python3 test_clear_arp_nd.py > clear_arp.log 2>&1 &

# Check progress
tail -f platform.log
tail -f ntp.log
```

### Compare Results Before/After Fix
```bash
# Before fix
sudo python3 test_ntp.py > before_fix.txt

# Apply bug fix...

# After fix
sudo python3 test_ntp.py > after_fix.txt

# Compare
diff before_fix.txt after_fix.txt
```

---

## 📁 File Structure

```
iscli_testing/
├── test_platform_components.py  ← Individual script for Platform
├── test_ztp.py                  ← Individual script for ZTP
├── test_ntp.py                  ← Individual script for NTP
├── test_clear_arp_nd.py         ← Individual script for Clear ARP/ND
│
├── iscli_test_suite.py          ← Combined script (all features)
├── SEPARATE_SCRIPTS_README.md   ← This file
│
├── JIRA_BUGS_TEMPLATE.md        ← Bug reports
├── RUN_TESTS.md                 ← General usage guide
└── DEPLOY_INSTRUCTIONS.md       ← Deployment guide
```

---

## ✅ Summary

**Created**: 4 separate test scripts
**Total Tests**: 37 (same as combined script)
**Execution Time**: ~45s total (or 8-15s per script)
**Bugs Found**: 5 total across all features
**Status**: ✅ Ready to use

**Recommendation**:
- Use **separate scripts** for feature-specific testing and debugging
- Use **combined script** for complete regression testing
- Both produce equivalent results - choose based on your needs

---

**All scripts are executable and ready to deploy to VMs!**

Run from: `/home/hp/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/iscli_testing/`
