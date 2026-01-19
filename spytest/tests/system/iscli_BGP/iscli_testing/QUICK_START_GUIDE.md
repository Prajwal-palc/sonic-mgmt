# IS-CLI Testing - Quick Start Guide

## Overview
This guide helps you quickly test the 4 in-progress IS-CLI features for Drop 1.

---

## Prerequisites

### 1. Install Required Software
```bash
# Install pytest if not already installed
pip3 install pytest

# Verify installation
pytest --version
```

### 2. Verify SONiC Environment
```bash
# Check SONiC version
cat /etc/sonic/sonic_version.yml

# Verify you have sudo access
sudo -v
```

### 3. Check Network Connectivity
```bash
# For NTP testing
ping -c 2 8.8.8.8

# Check interfaces
show interfaces status
```

---

## Quick Test Execution

### Option 1: Run All Tests (Recommended)
```bash
cd /home/hp/draksha/sonic-mgmt/spytest/tests/system/iscli_BGP/iscli_testing
./scripts/run_all_tests.sh
```

### Option 2: Run Individual Feature Tests

#### LLDP Tests
```bash
cd iscli_testing/lldp
pytest test_lldp_iscli.py -v
```

#### Hostname Tests
```bash
cd iscli_testing/hostname
pytest test_hostname_iscli.py -v
```

#### NTP Tests
```bash
cd iscli_testing/ntp
pytest test_ntp_iscli.py -v
```

#### Clear ARP/ND Tests
```bash
cd iscli_testing/clear_arp_nd
pytest test_clear_arp_nd_iscli.py -v
```

---

## Manual Testing Commands

### LLDP Feature Manual Testing

```bash
# 1. Check LLDP status
show feature status | grep lldp

# 2. Enable LLDP
sudo config feature state lldp enabled

# 3. View LLDP neighbors
show lldp table
show lldp neighbors
show lldp neighbors --verbose

# 4. Check LLDP container
docker ps | grep lldp
docker logs lldp --tail 20

# 5. Verify in config
show runningconfiguration all | grep -i lldp
```

**Expected Results:**
- ✓ Feature enables without errors
- ✓ Container starts and runs
- ✓ Commands return data (if neighbors present)
- ✓ No errors in docker logs

---

### Hostname Feature Manual Testing

```bash
# 1. Check current hostname
hostname

# 2. Change hostname
sudo config hostname sonic-test-device

# 3. Verify change
hostname

# 4. Check CONFIG_DB
redis-cli -n 4 HGET 'DEVICE_METADATA|localhost' hostname

# 5. Test invalid hostnames (should fail)
sudo config hostname "invalid hostname with spaces"
sudo config hostname "-invalid-start"
sudo config hostname $(python3 -c "print('a'*64)")  # Too long

# 6. Restore original hostname
sudo config hostname <original-name>
```

**Expected Results:**
- ✓ Valid hostnames accepted
- ✓ Hostname changes immediately
- ✓ Persisted in CONFIG_DB
- ✓ Invalid hostnames rejected with error

---

### NTP Feature Manual Testing

```bash
# 1. Check current NTP status
show ntp

# 2. Add NTP server
sudo config ntp add time.google.com

# 3. Verify addition
show ntp | grep time.google.com

# 4. Check chrony status
chronyc tracking
chronyc sources

# 5. Verify VRF support
sudo ip vrf exec mgmt ping -c 2 time.google.com

# 6. Check CONFIG_DB
redis-cli -n 4 KEYS NTP_SERVER*

# 7. Remove NTP server
sudo config ntp del time.google.com

# 8. Verify removal
show ntp
```

**Expected Results:**
- ✓ Servers add/remove without errors
- ✓ chrony shows configured servers
- ✓ Configuration persisted in CONFIG_DB
- ✓ VRF exec works if mgmt VRF configured

---

### Clear ARP/ND Feature Manual Testing

```bash
# 1. View current ARP table
show arp

# 2. Count ARP entries
show arp | grep -c Ethernet

# 3. Clear ARP
sonic-clear arp

# 4. Verify cleared
show arp

# 5. Generate traffic to repopulate
ping -c 3 <gateway-ip>

# 6. Verify repopulation
show arp

# 7. Test IPv6 NDP (if configured)
show ndp

# 8. Clear NDP
sonic-clear ndp

# 9. Verify cleared
show ndp

# 10. Test system stability
ping -c 5 127.0.0.1  # Should still work
```

**Expected Results:**
- ✓ ARP table clears successfully
- ✓ Entries repopulate after traffic
- ✓ NDP clears (if IPv6 configured)
- ✓ System remains stable
- ✓ Connectivity maintained

---

## Understanding Test Results

### Pytest Output Symbols
- `.` - Test passed
- `F` - Test failed
- `s` - Test skipped
- `E` - Test error

### Exit Codes
- `0` - All tests passed
- `1` - Some tests failed
- `5` - No tests collected

### Example Output
```
test_lldp_iscli.py::TestLLDPBasicCommands::test_lldp_table PASSED    [ 10%]
test_lldp_iscli.py::TestLLDPBasicCommands::test_lldp_neighbors PASSED [ 20%]
...
======================== 25 passed, 2 skipped in 45.23s ========================
```

---

## Troubleshooting

### Issue: "Permission denied"
**Solution:**
```bash
# Ensure you have sudo privileges
sudo -v

# Some tests require sudo for config changes
```

### Issue: "Command not found: show"
**Solution:**
```bash
# Ensure you're on a SONiC system
# Source the environment if needed
source /etc/bash_completion.d/sonic-utilities.bash
```

### Issue: "LLDP container not running"
**Solution:**
```bash
# Enable LLDP feature
sudo config feature state lldp enabled

# Wait for container to start
sleep 5

# Verify
docker ps | grep lldp
```

### Issue: "No module named pytest"
**Solution:**
```bash
# Install pytest
pip3 install pytest

# Or use system package manager
sudo apt-get install python3-pytest
```

### Issue: "redis-cli command not found"
**Solution:**
```bash
# Try from within SONiC database container
docker exec -it database redis-cli -n 4 KEYS '*'
```

---

## Filling Out Test Results

After running tests, document results in:
```
iscli_testing/results/TEST_RESULTS_TEMPLATE.md
```

### Steps:
1. Copy template to new file with date
2. Fill in test execution summary tables
3. Document all failures with details
4. Add screenshots/logs if needed
5. Mark feature status (READY vs NEEDS FIXES)
6. Get sign-off from team lead

---

## Test Artifacts

All test runs produce:

1. **Console Output** - Real-time test progress
2. **Log Files** - `results/test_run_YYYYMMDD_HHMMSS.log`
3. **XML Results** - `results/*_results_YYYYMMDD_HHMMSS.xml` (for CI/CD)
4. **Report** - `results/TEST_REPORT_YYYYMMDD_HHMMSS.md`

---

## Next Steps After Testing

1. **Review Results**
   - Check pass/fail rates
   - Investigate failures
   - Document issues

2. **File Bugs**
   - Create JIRA tickets for failures
   - Include logs and reproducible steps
   - Assign priority

3. **Update Status**
   - Update project tracker
   - Notify team of blockers
   - Update feature status

4. **Retest After Fixes**
   - Run affected tests again
   - Verify fixes work
   - Update results

---

## Contact & Support

- **Documentation**: See `MASTER_TEST_PLAN.md` for detailed test plan
- **Test Scripts**: Located in `lldp/`, `hostname/`, `ntp/`, `clear_arp_nd/` directories
- **Results**: Stored in `results/` directory

---

## Quick Reference: File Locations

```
iscli_testing/
├── MASTER_TEST_PLAN.md              # Overall test strategy
├── QUICK_START_GUIDE.md             # This file
├── lldp/
│   └── test_lldp_iscli.py          # LLDP tests
├── hostname/
│   └── test_hostname_iscli.py      # Hostname tests
├── ntp/
│   └── test_ntp_iscli.py           # NTP tests
├── clear_arp_nd/
│   └── test_clear_arp_nd_iscli.py  # Clear ARP/ND tests
├── scripts/
│   └── run_all_tests.sh            # Automation script
└── results/
    ├── TEST_RESULTS_TEMPLATE.md    # Results template
    └── test_run_*.log              # Generated logs
```

---

**Last Updated**: 29-Dec-2025
**Version**: 1.0
