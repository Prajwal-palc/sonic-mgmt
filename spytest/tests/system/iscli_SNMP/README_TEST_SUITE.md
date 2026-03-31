# SONiC CLI Test Suite - iscli_SNMP

## Overview
This directory contains automated test scripts for SONiC CLI features including SNMP, OSPF, Ping/Traceroute, and Configuration Management.

**Test Environment:**
- VM1: 192.168.100.87 (adminuser/root@123)
- DUT1: 192.168.100.234 (admin/Ospf@123)
- DUT2: 192.168.100.185 (admin/Ospf@123)

## Test Categories

### 1. SNMP Tests (Simple Diagnostic Pattern)
These tests validate SNMP functionality without config reload/replace.

| Test File | Description | Duration |
|-----------|-------------|----------|
| `test_snmp_01_basic.py` | SNMP service enable/disable | ~5 min |
| `test_snmp_02_community.py` | SNMP community configuration | ~5 min |
| `test_snmp_03_v1_v2_v3.py` | SNMP v1/v2c/v3 with IPv4/IPv6 | ~10 min |
| `test_snmp_04_trap.py` | SNMP trap configuration | ~5 min |

**Run all SNMP tests:**
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./tests/system/iscli_SNMP/testbed_2vs.yaml \
  tests/system/iscli_SNMP/test_snmp_*.py \
  --logs-path ./logs/snmp_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### 2. Ping & Traceroute Tests (Simple Diagnostic Pattern)
These tests validate ping and traceroute commands.

| Test File | Description | Duration |
|-----------|-------------|----------|
| `test_ping_traceroute_simple.py` | Ping/Traceroute IPv4 & IPv6 | ~5 min |
| `test_ping_01_ipv4.py` | IPv4 ping all scenarios | ~5 min |
| `test_ping_02_ipv6.py` | IPv6 ping all scenarios | ~5 min |
| `test_traceroute_01_ipv4.py` | IPv4 traceroute all scenarios | ~5 min |
| `test_traceroute_02_ipv6.py` | IPv6 traceroute all scenarios | ~5 min |

**Run all Ping/Traceroute tests:**
```bash
./bin/spytest --tryssh 1 \
  --testbed ./tests/system/iscli_SNMP/testbed_2vs.yaml \
  tests/system/iscli_SNMP/test_ping_*.py tests/system/iscli_SNMP/test_traceroute_*.py \
  --logs-path ./logs/ping_trace_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### 3. OSPFv2 Tests (Simple Diagnostic Pattern)
These tests validate OSPFv2 functionality without config reload/replace.

| Test File | Description | Duration |
|-----------|-------------|----------|
| `test_ospfv2_01_basic.py` | Basic OSPF neighbor establishment | ~5 min |
| `test_ospfv2_02_passive_interface.py` | OSPF passive interface | ~5 min |
| `test_ospfv2_03_stub_area.py` | OSPF stub area | ~5 min |
| `test_ospfv2_04_nssa_area.py` | OSPF NSSA area | ~5 min |
| `test_ospfv2_05_md5_authentication.py` | OSPF MD5 authentication | ~5 min |
| `test_ospfv2_06_graceful_restart.py` | OSPF Graceful Restart | ~10 min |
| `test_ospfv2_07_cost_priority.py` | OSPF cost and priority | ~5 min |

**Run all OSPFv2 tests:**
```bash
./bin/spytest --tryssh 1 \
  --testbed ./tests/system/iscli_SNMP/testbed_2vs.yaml \
  tests/system/iscli_SNMP/test_ospfv2_*.py \
  --logs-path ./logs/ospfv2_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### 4. OSPFv3 Tests (Simple Diagnostic Pattern)
These tests validate OSPFv3 (IPv6) functionality.

| Test File | Description | Duration |
|-----------|-------------|----------|
| `test_ospfv3_01_basic.py` | Basic OSPFv3 neighbor establishment | ~5 min |
| `test_ospfv3_02_passive_interface.py` | OSPFv3 passive interface | ~5 min |
| `test_ospfv3_03_stub_area.py` | OSPFv3 stub area | ~5 min |
| `test_ospfv3_04_nssa_area.py` | OSPFv3 NSSA area | ~5 min |

**Run all OSPFv3 tests:**
```bash
./bin/spytest --tryssh 1 \
  --testbed ./tests/system/iscli_SNMP/testbed_2vs.yaml \
  tests/system/iscli_SNMP/test_ospfv3_*.py \
  --logs-path ./logs/ospfv3_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### 5. Config Reload/Replace Tests (BGP Pattern)
These tests validate configuration persistence for features that require it.

| Test File | Description | Duration |
|-----------|-------------|----------|
| `test_config_reload_replace_bgp.py` | BGP config reload/replace | ~15 min |
| `test_config_reload_replace_aaa.py` | AAA config reload/replace | ~15 min |

**Note:** Ping/Traceroute and OSPF do NOT need config reload/replace testing as they are diagnostic/routing protocol tests.

## Test Patterns

### Pattern 1: Simple Diagnostic Pattern
Used for: SNMP, Ping, Traceroute, OSPF, Diagnostic tools

**Structure:**
```python
def test_feature():
    validation_failures = []
    tech_support_generated = False

    try:
        # Configure feature
        # Test feature functionality
        # Verify results
    except Exception as e:
        validation_failures.append(str(e))
    finally:
        # CLEANUP: Always executes
        cleanup_config()

        # TECH-SUPPORT: Generate if failures
        if validation_failures and not tech_support_generated:
            st.generate_tech_support([D1, D2], "test_failures")

        # REPORT
        if validation_failures:
            st.report_fail("msg", f"Test completed with {len(validation_failures)} failure(s)")
        else:
            st.report_pass("test_case_passed")
```

### Pattern 2: Config Reload/Replace Pattern
Used for: BGP, AAA, and other features requiring persistence testing

**Structure:**
```python
def test_feature_config_reload():
    validation_failures = []
    tech_support_generated = False

    try:
        # Save baseline config
        # Configure feature (State 1)
        # Save State 1
        # Test config reload (persistence)
        # Configure feature (State 2)
        # Test config replace (rollback to State 1)
    except Exception as e:
        validation_failures.append(str(e))
    finally:
        # CLEANUP: Always executes
        cleanup_config()

        # TECH-SUPPORT & REPORT
```

## Running Tests

### Run a single test:
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./tests/system/iscli_SNMP/testbed_2vs.yaml \
  tests/system/iscli_SNMP/test_ospfv2_01_basic.py \
  --logs-path ./logs/test_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Run all tests in a category:
```bash
# All OSPF tests
./bin/spytest --tryssh 1 \
  --testbed ./tests/system/iscli_SNMP/testbed_2vs.yaml \
  tests/system/iscli_SNMP/test_ospf*.py \
  --logs-path ./logs/ospf_all_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

# All SNMP tests
./bin/spytest --tryssh 1 \
  --testbed ./tests/system/iscli_SNMP/testbed_2vs.yaml \
  tests/system/iscli_SNMP/test_snmp_*.py \
  --logs-path ./logs/snmp_all_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Run ALL tests:
```bash
./bin/spytest --tryssh 1 \
  --testbed ./tests/system/iscli_SNMP/testbed_2vs.yaml \
  tests/system/iscli_SNMP/ \
  --logs-path ./logs/full_suite_$(date +%Y%m%d_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

## Checking Results

### Log location:
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest
ls -ltr logs/
```

### View latest test results:
```bash
cd logs/
cd $(ls -1td */ | head -1)  # Go to latest test directory
cat result.html  # View HTML report
tail -100 dut.log  # View device logs
```

### Check for failures:
```bash
grep -i "FAIL\|ERROR" result.txt
grep -i "validation_failures" *.log
```

## Troubleshooting

### Issue 1: Test fails with "config save/reload failed"
**Solution:** This means you're running a config reload/replace test on a feature that doesn't need it. Use the simple diagnostic pattern instead.

### Issue 2: Connection timeout
**Solution:** Check testbed YAML has correct IPs and credentials:
```bash
cat tests/system/iscli_SNMP/testbed_2vs.yaml
```

### Issue 3: Import errors
**Solution:** Install missing Python packages:
```bash
source ~/spytest_venv/bin/activate
pip install tabulate prettytable jinja2 textfsm==1.1.3 netmiko==3.4.0 requests jsonpatch netaddr psutil rpyc pyfiglet
```

## Test Development Guidelines

### When to use Simple Diagnostic Pattern:
- SNMP tests
- Ping/Traceroute tests
- OSPF/BGP functionality tests
- Any test that validates feature functionality

### When to use Config Reload/Replace Pattern:
- BGP configuration persistence
- AAA configuration persistence
- Features that MUST survive a reboot
- Only when explicitly testing configuration persistence

### Key Principles:
1. **Always use validation_failures list** - Don't stop on first error
2. **Always use try-finally for cleanup** - Cleanup must execute
3. **Generate tech-support on failures** - For debugging
4. **Use skip_error_check=True** - Let script handle errors
5. **Follow naming convention**: `test_<feature>_<number>_<description>.py`

## Contact

For issues or questions, check:
- SpyTest Logs: `logs/`
- Test Scripts: `tests/system/iscli_SNMP/`
- Testbed Config: `tests/system/iscli_SNMP/testbed_2vs.yaml`
