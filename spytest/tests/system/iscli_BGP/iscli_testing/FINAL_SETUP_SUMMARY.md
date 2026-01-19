# IS-CLI Drop 1 - Complete Test Suite Summary

## 🎯 Test Configuration

**Test Devices:**
- **DUT1:** 192.168.100.73 (admin/jira@123)
- **DUT2:** 192.168.100.103 (admin/jira@123)
- **VM1 (Test Runner):** 192.168.100.87 (adminuser/root@123)

---

## 📁 Files Created (Local Machine)

### Testbed Configuration
```
/home/hp/draksha/sonic-mgmt/spytest/testbeds/testbed_iscli_custom.yaml
```
- ✅ Updated with DUT1: 192.168.100.73
- ✅ Updated with DUT2: 192.168.100.103

### Test Files
```
/home/hp/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/iscli_testing/
├── test_iscli_spytest.py              (14 tests - Basic suite)
├── test_iscli_comprehensive.py        (44 tests - COMPREHENSIVE)
├── test_platform_components.py         (9 tests - Standalone)
├── test_ztp.py                         (6 tests - Standalone)
├── test_ntp.py                        (13 tests - Standalone)
├── test_clear_arp_nd.py               (9 tests - Standalone)
├── run_individual_tests.sh            (Automation script)
├── COMPREHENSIVE_TEST_COMMANDS.txt    (📖 Command reference)
├── INDIVIDUAL_TEST_COMMANDS.txt       (📖 Individual test commands)
└── SETUP_VM1_COMPLETE.sh              (🚀 Setup script for VM1)
```

---

## 🚀 Setup on VM1 (192.168.100.87)

### Option 1: Copy Files from Local Machine
```bash
# From your local machine (hp)
scp -r /home/hp/draksha/sonic-mgmt/spytest/testbeds/testbed_iscli_custom.yaml \
  adminuser@192.168.100.87:~/draksha/sonic-mgmt/spytest/testbeds/

scp -r /home/hp/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/iscli_testing/ \
  adminuser@192.168.100.87:~/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/
```

### Option 2: Run Setup Script on VM1
```bash
# On VM1 (192.168.100.87)
# Copy the SETUP_VM1_COMPLETE.sh script content and run it
bash SETUP_VM1_COMPLETE.sh
```

---

## 📊 Test Suites Available

### 1. **Comprehensive Test Suite** ⭐ RECOMMENDED
**File:** `test_iscli_comprehensive.py`
**Total Tests:** 44
**Coverage:** ALL platform commands + ZTP + NTP + Clear ARP/ND

**Test Categories:**
- ✅ Platform Identification (5 tests)
  - show platform summary, syseeprom, help
- ✅ Hardware Monitoring (20 tests)
  - PSU status (5 tests)
  - SSD health (5 tests)
  - PCIe info (4 tests)
  - Environmental (fan, temp, voltage, current) (4 tests)
- ✅ Firmware Management (5 tests)
- ✅ Error Handling (4 tests)
- ✅ ZTP (2 tests)
- ✅ NTP (4 tests)
- ✅ Clear ARP/ND (4 tests)

**Run ALL 44 Tests:**
```bash
cd ~/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py \
  --logs-path ./logs/iscli_comprehensive_$(date +%Y%m%d_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### 2. **Basic Test Suite**
**File:** `test_iscli_spytest.py`
**Total Tests:** 14
**Coverage:** Basic platform + ZTP + NTP + Clear ARP/ND

### 3. **Standalone Test Scripts**
- `test_platform_components.py` (9 tests)
- `test_ztp.py` (6 tests)
- `test_ntp.py` (13 tests)
- `test_clear_arp_nd.py` (9 tests)

---

## 🎯 Quick Start Commands (VM1)

### Test Single Platform Command
```bash
cd ~/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformIdentification::test_platform_summary_basic \
  --logs-path ./logs/test_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Test All Platform Identification
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformIdentification \
  --logs-path ./logs/platform_id_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Test All Hardware Monitoring (20 tests)
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformHardwareMonitoring \
  --logs-path ./logs/hw_monitor_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Test PSU Commands (5 tests)
```bash
# Individual PSU tests
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformHardwareMonitoring::test_platform_psustatus_basic \
  --logs-path ./logs/psu_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

### Test SSD Health Commands (5 tests)
```bash
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformHardwareMonitoring::test_platform_ssdhealth_basic \
  --logs-path ./logs/ssd_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

---

## 📋 Platform Commands Covered

### ✅ Platform Identification
```bash
show platform summary
show platform summary --json          # BUG: flags not supported
show platform syseeprom
show platform syseeprom --verbose
show platform --help
```

### ✅ PSU Monitoring
```bash
show platform psustatus
show platform psustatus -i 1
show platform psustatus --json        # BUG: flags not supported
show platform psustatus --verbose
show platform psustatus -i 1 --json --verbose
```

### ✅ SSD Health
```bash
show platform ssdhealth
show platform ssdhealth --verbose
show platform ssdhealth --vendor
show platform ssdhealth --verbose --vendor
show platform ssdhealth /dev/sda
show platform ssdhealth /dev/nonexistent  # Error test - needs hardware
```

### ✅ PCIe Information
```bash
show platform pcieinfo
show platform pcieinfo --check
show platform pcieinfo --verbose
show platform pcieinfo --check --verbose
```

### ✅ Environmental Monitoring
```bash
show platform fan
show platform temperature
show platform voltage
show platform current
```

### ✅ Firmware Management
```bash
show platform firmware --help
show platform firmware status
show platform firmware version
show platform firmware updates
show platform firmware update-all-status
```

### ✅ Error Testing
```bash
show platform invalid-command         # Expect error
show platform summary --invalid-option # Expect error
show platform psustatus -i 999        # Expect error
```

---

## 🐛 Known Bugs Validated

1. **HIGH:** IS-CLI flags not supported (--json, --verbose, etc.)
   - Tests: `test_platform_summary_json`, `test_platform_psustatus_json`

2. **HIGH:** show ntp command ambiguous
   - Test: `test_show_ntp_ambiguous`

3. **MEDIUM:** show arp/ndp not available in IS-CLI
   - Test: `test_show_arp_iscli_fail`

4. **MEDIUM:** Firmware commands may be ambiguous
   - Test: `test_platform_firmware_status`

---

## 📝 Viewing Test Results

```bash
# HTML Report
firefox ./logs/iscli_comprehensive_*/tc_results.html

# Console Output
cat ./logs/iscli_comprehensive_*/dut.txt

# CSV Results
cat ./logs/iscli_comprehensive_*/tc_results.csv

# Summary
ls -lh ./logs/iscli_comprehensive_*
```

---

## 🔧 Troubleshooting

### Issue: Tests not found
**Solution:** Verify path includes `tests/` prefix
```bash
# WRONG: system/iscli_BGP/...
# RIGHT: tests/system/iscli_BGP/...
```

### Issue: Connection failed to DUT
**Solution:** Verify DUT IPs and credentials in testbed YAML
```bash
vi ~/draksha/sonic-mgmt/spytest/testbeds/testbed_iscli_custom.yaml
# Check: managementip, username, password
```

### Issue: Permission denied on VM1
**Solution:** Ensure directories exist
```bash
mkdir -p ~/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/iscli_testing
mkdir -p ~/draksha/sonic-mgmt/spytest/testbeds
```

---

## ✅ Ready to Test!

**Your comprehensive IS-CLI test suite is ready with:**
- ✅ 44 comprehensive tests covering ALL platform commands
- ✅ Testbed configured for your DUTs (192.168.100.73, 192.168.100.103)
- ✅ Bug validation tests included
- ✅ Hardware-specific tests marked
- ✅ Easy command reference guides

**Start testing now on VM1 (192.168.100.87)!**
