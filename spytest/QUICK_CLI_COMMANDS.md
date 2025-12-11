# BGP Peer-Group Tests - Quick CLI Commands

## Quick Reference for Running BGP Peer-Group Tests

---

## Prerequisites

```bash
# Ensure you're in the spytest directory
cd /home/adminuser/draksha/sonic-mgmt/spytest

# Verify testbed file exists
ls -lh testbeds/testbed_bgp_pg01.yaml

# Verify test files exist
ls -lh tests/system/iscli_BGP/test_bgp_pg*.py
```

---

## Run Individual Tests

### PG-01: Basic Peer-Group Creation
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_bgp_pg01.yaml \
  tests/system/iscli_BGP/test_bgp_pg01_peergroup_creation.py \
  --logs-path ./logs/pg01_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### PG-02: Attribute Inheritance (Timers)
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_bgp_pg01.yaml \
  tests/system/iscli_BGP/test_bgp_pg02_attribute_inheritance.py \
  --logs-path ./logs/pg02_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### PG-03: Attribute Override
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_bgp_pg01.yaml \
  tests/system/iscli_BGP/test_bgp_pg03_attribute_override.py \
  --logs-path ./logs/pg03_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### PG-04: AF-Level Settings
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_bgp_pg01.yaml \
  tests/system/iscli_BGP/test_bgp_pg04_af_level_settings.py \
  --logs-path ./logs/pg04_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### PG-05: Route-Map Inheritance
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_bgp_pg01.yaml \
  tests/system/iscli_BGP/test_bgp_pg05_routemap_inheritance.py \
  --logs-path ./logs/pg05_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### PG-06: Password Inheritance
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_bgp_pg01.yaml \
  tests/system/iscli_BGP/test_bgp_pg06_password_inheritance.py \
  --logs-path ./logs/pg06_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## Run All Tests (Complete Suite)

```bash
# Using master run script
./RUN_ALL_BGP_PEERGROUP_TESTS_COMPLETE.sh

# OR manually run all sequentially
for test in pg01 pg02 pg03 pg04 pg05 pg06; do
  ./bin/spytest --tryssh 1 \
    --testbed ./testbeds/testbed_bgp_pg01.yaml \
    tests/system/iscli_BGP/test_bgp_${test}_*.py \
    --logs-path ./logs/${test}_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native
done
```

---

## View Results

### Quick Summary
```bash
# View most recent test summary
cat ./logs/pg01_*/summary.txt

# View all test summaries
ls -lht ./logs/pg*/summary.txt | head -10

# Check for PASS/FAIL
grep "PASS\|FAIL" ./logs/pg01_*/summary.txt
```

### Detailed Logs
```bash
# View device commands (D1)
less ./logs/pg01_*/dlog-D1-smic_sonic1.log

# View device commands (D2)
less ./logs/pg01_*/dlog-D2-smic_sonic2.log

# View test execution log
less ./logs/pg01_*/module_system_iscli_BGP_test_bgp_pg01_peergroup_creation.log

# View HTML dashboard
firefox ./logs/pg01_*/dashboard.html &
```

### Search Logs
```bash
# Find test results
grep "Report(" ./logs/pg01_*/module_*.log

# Find BGP session status
grep -i "established" ./logs/pg01_*/dlog-D1-*.log

# Find errors
grep -i "error\|fail" ./logs/pg01_*/dlog-D1-*.log | grep -v "SKIP"

# Find BGP configuration commands
grep "FCMD.*bgp" ./logs/pg01_*/dlog-D1-*.log
```

---

## Cleanup

### Clean Old Logs
```bash
# Remove logs older than 7 days
find ./logs -name "pg*" -type d -mtime +7 -exec rm -rf {} \;

# Remove all PG test logs
rm -rf ./logs/pg0* ./logs/bgp_peergroup_suite_*
```

### Clean Device Configuration (if needed)
```bash
# SSH to devices and clean BGP
ssh admin@192.168.100.203  # D1
sonic-cli
configure terminal
no router bgp 65001
exit
exit

ssh admin@192.168.100.196  # D2
sonic-cli
configure terminal
no router bgp 65001
exit
exit
```

---

## Troubleshooting

### Check Device Connectivity
```bash
# Ping devices
ping -c 3 192.168.100.203  # D1
ping -c 3 192.168.100.196  # D2

# SSH test
ssh admin@192.168.100.203 "show version"
ssh admin@192.168.100.196 "show version"
```

### Check Port Status
```bash
# View testbed ports
ssh admin@192.168.100.203 "show interface status Ethernet4"
ssh admin@192.168.100.196 "show interface status Ethernet4"

# Expected: Admin: up, Oper: up
```

### Rerun Failed Test
```bash
# Find failed test
grep "FAIL" ./logs/pg*/summary.txt

# Rerun specific test
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_bgp_pg01.yaml \
  tests/system/iscli_BGP/test_bgp_pg01_peergroup_creation.py \
  --logs-path ./logs/pg01_rerun_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## Command-Line Options Explained

| Option | Description |
|--------|-------------|
| `--tryssh 1` | Use SSH connection (required) |
| `--testbed FILE` | Testbed YAML file with topology |
| `--logs-path DIR` | Output directory for logs |
| `--log-level debug` | Enable debug logging |
| `--skip-init-config` | Skip device initialization (faster) |
| `--ifname-type native` | Use native interface names (Ethernet4) |
| `--file-mode` | Sequential execution (not parallel) |

---

## One-Liner Commands

### Run and View Results
```bash
# Run test and immediately view summary
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_bgp_pg01.yaml \
  tests/system/iscli_BGP/test_bgp_pg01_peergroup_creation.py \
  --logs-path ./logs/pg01_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native && \
  cat ./logs/pg01_*/summary.txt
```

### Run and Check for Errors
```bash
# Run test and show any errors
./bin/spytest --tryssh 1 --testbed ./testbeds/testbed_bgp_pg01.yaml \
  tests/system/iscli_BGP/test_bgp_pg01_peergroup_creation.py \
  --logs-path ./logs/pg01_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native && \
  grep -i "error\|fail" ./logs/pg01_*/dlog-D1-*.log | grep -v "SKIP" | head -20
```

---

## Test Execution Times

| Test | Expected Duration |
|------|-------------------|
| PG-01 | ~3-4 minutes |
| PG-02 | ~3-4 minutes |
| PG-03 | ~3-4 minutes |
| PG-04 | ~3-4 minutes |
| PG-05 | ~4-5 minutes |
| PG-06 | ~4-5 minutes |
| **All 6** | **~20-25 minutes** |

---

## Environment Variables (Optional)

```bash
# Set default testbed
export SPYTEST_TESTBED=./testbeds/testbed_bgp_pg01.yaml

# Set default log level
export SPYTEST_LOG_LEVEL=debug

# Set default interface naming
export SPYTEST_IFNAME_TYPE=native

# Run test with env vars
./bin/spytest --tryssh 1 tests/system/iscli_BGP/test_bgp_pg01_peergroup_creation.py
```

---

## Git Operations (For Developers)

### Check Test File Status
```bash
git status tests/system/iscli_BGP/test_bgp_pg*.py
```

### View Test File Changes
```bash
git diff tests/system/iscli_BGP/test_bgp_pg01_peergroup_creation.py
```

### Stage Test Files
```bash
git add tests/system/iscli_BGP/test_bgp_pg*.py
git add testbeds/testbed_bgp_pg01.yaml
```

---

## Quick Help

```bash
# SPyTest help
./bin/spytest --help

# List available options
./bin/spytest --help | grep -- "--"

# Check SPyTest version
./bin/spytest --version
```

---

**Last Updated**: 2025-12-11
**Test Suite**: BGP Peer-Group (6 tests)
**Framework**: SPyTest
