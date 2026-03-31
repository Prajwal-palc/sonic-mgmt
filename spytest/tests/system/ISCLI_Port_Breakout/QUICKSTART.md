# Port Breakout Test Suite - Quick Start Guide

Get started with Port Breakout testing in 5 minutes!

---

## Quick Installation (3 Commands)

```bash
# 1. Navigate to spytest directory
cd /home/claudeuser/draksha/sonic-mgmt/spytest

# 2. Run automated setup script
./setup_breakout_tests.sh

# 3. Activate virtual environment
source spytest_venv/bin/activate
```

**Done!** Now you're ready to configure and run tests.

---

## Quick Configuration (Edit 1 File)

### Edit testbed file
```bash
nano testbeds/testbed_breakout.yaml
```

### Minimal configuration
```yaml
---
devices:
  - alias: "D1"
    properties:
      type: "sonic"
      ip: "192.168.1.10"          # ← Change to your device IP
      username: "admin"            # ← Change to your username
      password: "YourPassword"     # ← Change to your password
      protocol: "ssh"
      port: 22

topology:
  - link: ["D1:Ethernet24", "D2:Ethernet24"]
```

**Save and exit** (Ctrl+X, then Y, then Enter)

---

## Quick Test Run (1 Command)

### Run single test
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/test_pb_f_004_revert_to_default.py
```

**That's it!** Your first test is running.

---

## View Results (1 Command)

```bash
# Check latest test results
ls -lht logs/ | head -5

# View test summary
cd logs/<latest-directory>/
cat results.txt
```

---

## Run More Tests

### Run all 20 tests
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/
```

### Run specific test by number
```bash
# Test PB-F-005 (IP Configuration)
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/test_pb_f_005_ip_configuration.py

# Test PB-F-001 (All 11 breakout modes)
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/test_port_breakout_basic_modes.py
```

---

## Common Issues & Quick Fixes

### Issue: "Virtual environment not found"
```bash
# Solution: Run setup script
./setup_breakout_tests.sh
```

### Issue: "Testbed file not found"
```bash
# Solution: Create testbed file
nano testbeds/testbed_breakout.yaml
# Copy template from SETUP_GUIDE.md
```

### Issue: "Cannot connect to device"
```bash
# Solution: Test SSH manually
ssh admin@192.168.1.10
# If fails, check IP address in testbed file
```

### Issue: "Spytest module not found"
```bash
# Solution: Activate virtual environment
source spytest_venv/bin/activate

# Solution 2: Set PYTHONPATH
export PYTHONPATH=/home/claudeuser/draksha/sonic-mgmt/spytest:$PYTHONPATH
```

---

## Quick Reference Card

### Always Do This First
```bash
cd /home/claudeuser/draksha/sonic-mgmt/spytest
source spytest_venv/bin/activate
```

### Run Single Test
```bash
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/<test_file>.py
```

### Run All Tests
```bash
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/
```

### Check Results
```bash
ls -lht logs/ | head -5
cd logs/<directory>/
cat results.txt
```

### Exit Virtual Environment
```bash
deactivate
```

---

## All 20 Test Files (Copy-Paste Ready)

```bash
# Basic Tests
tests/system/ISCLI_Port_Breakout/test_port_breakout_basic_modes.py
tests/system/ISCLI_Port_Breakout/test_port_breakout_stress_test.py
tests/system/ISCLI_Port_Breakout/test_port_breakout_multi_port.py

# Configuration Tests
tests/system/ISCLI_Port_Breakout/test_pb_f_004_revert_to_default.py
tests/system/ISCLI_Port_Breakout/test_pb_f_005_ip_configuration.py
tests/system/ISCLI_Port_Breakout/test_pb_f_006_mtu_configuration.py
tests/system/ISCLI_Port_Breakout/test_pb_f_007_shutdown_operations.py
tests/system/ISCLI_Port_Breakout/test_pb_f_008_multiple_speed_grades.py

# VLAN Tests
tests/system/ISCLI_Port_Breakout/test_pb_f_009_asymmetric_breakout.py
tests/system/ISCLI_Port_Breakout/test_pb_f_010_vlan_configuration.py
tests/system/ISCLI_Port_Breakout/test_pb_f_011_vlan_isolation.py

# Advanced Tests
tests/system/ISCLI_Port_Breakout/test_pb_f_012_portchannel_lag.py
tests/system/ISCLI_Port_Breakout/test_pb_f_013_portchannel_member_flap.py
tests/system/ISCLI_Port_Breakout/test_pb_f_014_lldp_discovery.py
tests/system/ISCLI_Port_Breakout/test_pb_f_015_config_persistence.py
tests/system/ISCLI_Port_Breakout/test_pb_f_016_basic_connectivity.py

# Verification Tests
tests/system/ISCLI_Port_Breakout/test_pb_f_017_traffic_stability.py
tests/system/ISCLI_Port_Breakout/test_pb_f_018_dependencies_check.py
tests/system/ISCLI_Port_Breakout/test_pb_f_019_complete_verification.py
tests/system/ISCLI_Port_Breakout/test_pb_f_020_error_handling.py
```

---

## One-Liner Test Commands

### Test by Feature

```bash
# IP Configuration
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml tests/system/ISCLI_Port_Breakout/test_pb_f_005_ip_configuration.py

# VLAN Configuration
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml tests/system/ISCLI_Port_Breakout/test_pb_f_010_vlan_configuration.py

# PortChannel/LAG
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml tests/system/ISCLI_Port_Breakout/test_pb_f_012_portchannel_lag.py

# Connectivity Test
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml tests/system/ISCLI_Port_Breakout/test_pb_f_016_basic_connectivity.py
```

---

## Complete Workflow Example

```bash
# Step 1: Setup (one time)
cd /home/claudeuser/draksha/sonic-mgmt/spytest
./setup_breakout_tests.sh

# Step 2: Configure testbed (one time)
nano testbeds/testbed_breakout.yaml
# Update IPs, credentials, save and exit

# Step 3: Activate venv (every session)
source spytest_venv/bin/activate

# Step 4: Run test
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/test_pb_f_004_revert_to_default.py

# Step 5: Check results
ls -lht logs/ | head -2
cd logs/<latest>/
cat results.txt

# Step 6: Run more tests as needed
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_breakout.yaml \
  tests/system/ISCLI_Port_Breakout/test_pb_f_005_ip_configuration.py

# Step 7: Deactivate when done
deactivate
```

---

## Next Steps

1. **Read detailed guides:**
   - `SETUP_GUIDE.md` - Complete installation instructions
   - `README.md` - All test case descriptions
   - `PORT_BREAKOUT_DELIVERY_SUMMARY.md` - Full delivery summary

2. **Customize tests:**
   - Edit test scripts for your environment
   - Modify port numbers, IP addresses
   - Adjust wait times if needed

3. **Run tests:**
   - Start with simple tests (PB-F-004, PB-F-005)
   - Progress to complex tests (PB-F-001, PB-F-003)
   - Run full suite for regression testing

---

## Quick Help

```bash
# Get spytest help
./bin/spytest --help

# Get pytest help
pytest --help

# Check installed packages
pip list | grep pytest

# Check Python path
echo $PYTHONPATH

# Verify spytest import
python -c "from spytest import st; print('OK')"
```

---

## Support Files in This Directory

- `QUICKSTART.md` (this file) - Get started in 5 minutes
- `SETUP_GUIDE.md` - Complete setup instructions
- `README.md` - All 20 test cases documented
- `PORT_BREAKOUT_DELIVERY_SUMMARY.md` - Delivery summary
- `requirements_breakout.txt` - Python package list
- `setup_breakout_tests.sh` - Automated setup script

---

**Status:** ✅ READY TO RUN

**Time to First Test:** ~5 minutes

**Support:** See SETUP_GUIDE.md for troubleshooting

---

**Last Updated:** March 31, 2026
