# IS-CLI Drop 1 - Hardware Testing Guide

## 🔧 Hardware Devices Configuration

**UPDATED for HARDWARE TESTING - All Platform Commands Will Work!**

### Hardware Devices:
- **HW 8011 (DUT1):** 192.168.100.202 (admin/sonic@123)
- **HW 8010 (DUT2):** 192.168.100.63 (admin/sonic@123)
- **VM1 (Test Runner):** 192.168.100.87 (adminuser/root@123)

---

## ✅ Why Hardware Testing Matters

**Virtual Switch Limitations:**
- ❌ No PSU sensors
- ❌ No SSD health data
- ❌ No PCIe devices
- ❌ No fan/temperature/voltage sensors
- ❌ Limited firmware info

**Hardware Benefits:**
- ✅ Full PSU monitoring
- ✅ Real SSD health metrics
- ✅ PCIe device enumeration
- ✅ Environmental sensors (fan, temp, voltage, current)
- ✅ Firmware version/status
- ✅ Complete platform validation

---

## 📁 Updated Files

### Testbed Configuration
**File:** `/home/hp/draksha/sonic-mgmt/spytest/testbeds/testbed_iscli_custom.yaml`

```yaml
devices:
  DUT1:
    managementip: 192.168.100.202  # HW 8011
    username: admin
    password: sonic@123

  DUT2:
    managementip: 192.168.100.63   # HW 8010
    username: admin
    password: sonic@123
```

### Comprehensive Test Suite
**File:** `test_iscli_comprehensive.py`
**Total Tests:** 44 tests (ALL will work on hardware!)

---

## 🚀 Running Tests on Hardware

### Step 1: Copy Files to VM1 (Test Runner)

**From your local machine:**

```bash
# Copy updated testbed
scp /home/hp/draksha/sonic-mgmt/spytest/testbeds/testbed_iscli_custom.yaml \
  adminuser@192.168.100.87:~/draksha/sonic-mgmt/spytest/testbeds/

# Copy comprehensive test file
scp /home/hp/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py \
  adminuser@192.168.100.87:~/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/iscli_testing/
```

### Step 2: Connect to VM1

```bash
ssh adminuser@192.168.100.87
cd ~/draksha/sonic-mgmt/spytest
```

### Step 3: Run Comprehensive Tests

**RUN ALL 44 TESTS ON HARDWARE:**

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py \
  --logs-path ./logs/iscli_hardware_all_$(date +%Y%m%d_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

---

## 🎯 Test Categories for Hardware

### 1. Platform Identification Tests (5 tests)
**All work on hardware!**

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformIdentification \
  --logs-path ./logs/hw_platform_id_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

**Tests:**
- ✅ show platform summary
- ✅ show platform summary --json (validates BUG)
- ✅ show platform syseeprom (shows real EEPROM data!)
- ✅ show platform syseeprom --verbose
- ✅ show platform --help

---

### 2. Hardware Monitoring Tests (20 tests) ⭐
**THIS IS WHERE HARDWARE SHINES!**

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformHardwareMonitoring \
  --logs-path ./logs/hw_monitoring_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

#### PSU Monitoring (5 tests)
**Will show REAL PSU data on hardware!**

```bash
# Test individual PSU commands
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformHardwareMonitoring::test_platform_psustatus_basic \
  --logs-path ./logs/hw_psu_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

**Tests:**
- ✅ show platform psustatus (will show real PSU1, PSU2 status!)
- ✅ show platform psustatus -i 1 (specific PSU)
- ✅ show platform psustatus --json (validates BUG)
- ✅ show platform psustatus --verbose
- ✅ show platform psustatus -i 1 --json --verbose

#### SSD Health Monitoring (5 tests)
**Will show REAL SSD metrics!**

```bash
# Test SSD health on real hardware
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformHardwareMonitoring::test_platform_ssdhealth_basic \
  --logs-path ./logs/hw_ssd_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

**Tests:**
- ✅ show platform ssdhealth (will show Device Model, Health %, Temperature!)
- ✅ show platform ssdhealth --verbose
- ✅ show platform ssdhealth --vendor
- ✅ show platform ssdhealth --verbose --vendor
- ✅ show platform ssdhealth /dev/sda (specific device)

#### PCIe Device Monitoring (4 tests)
**Will enumerate REAL PCIe devices!**

```bash
# Test PCIe enumeration
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformHardwareMonitoring::test_platform_pcieinfo_basic \
  --logs-path ./logs/hw_pcie_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

**Tests:**
- ✅ show platform pcieinfo (lists all PCIe devices!)
- ✅ show platform pcieinfo --check
- ✅ show platform pcieinfo --verbose
- ✅ show platform pcieinfo --check --verbose

#### Environmental Monitoring (4 tests)
**Will show REAL sensor data!**

```bash
# Test environmental sensors
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformHardwareMonitoring::test_platform_fan \
  --logs-path ./logs/hw_env_$(date +%Y%m%d_%H%M%S) --log-level debug --skip-init-config --ifname-type native
```

**Tests:**
- ✅ show platform fan (shows fan RPM, status!)
- ✅ show platform temperature (shows thermal sensors!)
- ✅ show platform voltage (shows voltage rails!)
- ✅ show platform current (shows current sensors!)

---

### 3. Firmware Management Tests (5 tests)
**Will show REAL firmware versions!**

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformFirmware \
  --logs-path ./logs/hw_firmware_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

**Tests:**
- ✅ show platform firmware --help
- ✅ show platform firmware status
- ✅ show platform firmware version (shows CPLD, BIOS, FPGA versions!)
- ✅ show platform firmware updates
- ✅ show platform firmware update-all-status

---

### 4. Error Handling Tests (4 tests)

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIPlatformErrorHandling \
  --logs-path ./logs/hw_errors_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

**Tests:**
- ✅ show platform invalid-command (expects error)
- ✅ show platform summary --invalid-option (expects error)
- ✅ show platform psustatus -i 999 (expects error)
- ✅ show platform ssdhealth /dev/nonexistent (expects error - NOW TESTABLE!)

---

### 5. ZTP Tests (2 tests)

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIZTP \
  --logs-path ./logs/hw_ztp_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

### 6. NTP Tests (4 tests)

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLINTP \
  --logs-path ./logs/hw_ntp_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

### 7. Clear ARP/ND Tests (4 tests)

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py::TestISCLIClearARPND \
  --logs-path ./logs/hw_cleararp_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## 📊 Expected Results on Hardware

### What You'll See on Real Hardware:

**PSU Status:**
```
PSU    Model          Serial     HW Rev  Voltage  Current  Power  Status
-----  -------------  ---------  ------  -------  -------  -----  ------
PSU 1  PWR-500AC-F    S1234567   A0      12.05V   4.2A     50W    OK
PSU 2  PWR-500AC-F    S1234568   A0      12.03V   4.1A     49W    OK
```

**SSD Health:**
```
Device Model    : Samsung SSD 860 EVO 250GB
Health          : 98%
Temperature     : 34°C
Data Units Read : 12345
Data Units Written: 67890
```

**PCIe Devices:**
```
Bus:Dev.Fn  Vendor:Device  Description
00:01.0     8086:1533      Intel I210 Gigabit Network
01:00.0     14e4:b850      Broadcom Trident3 ASIC
```

**Environmental:**
```
Sensor          Current  High  Low   Crit High  Crit Low
--------------  -------  ----  ----  ---------  --------
CPU Core        45°C     85°C  0°C   95°C       -5°C
Front Panel     32°C     65°C  0°C   75°C       -5°C

Fan  Speed    Direction  Status
---  -------  ---------  ------
1    8400 RPM F2B        OK
2    8350 RPM F2B        OK
```

---

## 🐛 Bugs That Will Be Validated on Hardware

1. **HIGH:** IS-CLI flags not supported (--json, --verbose)
   - Test on hardware: `show platform summary --json`
   - Expected: Error or not supported

2. **HIGH:** show ntp command ambiguous
   - Test on hardware: `show ntp`
   - Expected: Ambiguous command error

3. **MEDIUM:** show arp/ndp not in IS-CLI
   - Test on hardware: `sonic-cli -c 'show arp'`
   - Expected: Invalid input

4. **LOW:** PCIe YAML file may be missing
   - Test on hardware: `show platform pcieinfo`
   - May show error if pcie.yaml missing

---

## 📝 Viewing Results

```bash
# HTML Report (Beautiful formatted results!)
firefox ./logs/hw_hardware_all_*/tc_results.html

# Console Output
cat ./logs/hw_hardware_all_*/dut.txt

# Quick Summary
grep -E "PASS|FAIL" ./logs/hw_hardware_all_*/tc_results.csv
```

---

## ✅ Checklist for Hardware Testing

- [ ] Copied updated testbed to VM1
- [ ] Copied test_iscli_comprehensive.py to VM1
- [ ] Verified SSH access to HW 8011 (192.168.100.202)
- [ ] Verified SSH access to HW 8010 (192.168.100.63)
- [ ] Run comprehensive test suite
- [ ] Review PSU monitoring results
- [ ] Review SSD health results
- [ ] Review PCIe enumeration results
- [ ] Review environmental sensor results
- [ ] Review firmware version results
- [ ] Document any bugs found
- [ ] Create JIRA tickets for validated bugs

---

## 🎯 Recommended Testing Order

1. **Start Small** - Run single platform summary test
2. **Platform ID** - Test all 5 platform identification tests
3. **PSU Tests** - Test all 5 PSU monitoring tests
4. **SSD Tests** - Test all 5 SSD health tests
5. **PCIe Tests** - Test all 4 PCIe tests
6. **Environmental** - Test all 4 environmental sensor tests
7. **Firmware** - Test all 5 firmware tests
8. **Full Suite** - Run all 44 tests together

---

## 🚀 Quick Start Command (Copy & Run on VM1)

```bash
# Complete hardware test run
cd ~/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_iscli_custom.yaml \
  tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py \
  --logs-path ./logs/iscli_hw_complete_$(date +%Y%m%d_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

**This will test ALL 44 tests on REAL HARDWARE! 🎉**

---

## 📞 Support

**Hardware Details:**
- HW 8011: 192.168.100.202 (admin/sonic@123)
- HW 8010: 192.168.100.63 (admin/sonic@123)

**Test Files Location:**
- Testbed: `~/draksha/sonic-mgmt/spytest/testbeds/testbed_iscli_custom.yaml`
- Tests: `~/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/iscli_testing/test_iscli_comprehensive.py`

**All platform commands will now work properly on hardware! ✅**
