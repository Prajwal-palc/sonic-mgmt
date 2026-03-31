# IPv6 Neighbor Discovery (ND) Test Suite

This directory contains automated test scripts for IPv6 Neighbor Discovery (ND) functionality in SONiC.

## Test Files

### 1. test_nd_basic_operations.py
**Test Suite:** Basic ND Operations
**Test Cases:**
- `test_nd_basic_resolution()` - Basic ND resolution via ping
- `test_nd_entry_relearning()` - ND entry re-learning after clear
- `test_static_nd_entry()` - Static ND entry configuration and persistence

**Validates:**
- Basic neighbor discovery works via ICMPv6 ping
- ND entries can be cleared and re-learned
- Static ND entries can be configured
- Static entries persist after clear command
- ND table displays correct information

**Duration:** ~2-3 minutes

### 2. test_nd_interface_behavior.py
**Test Suite:** ND Interface Behavior
**Test Cases:**
- `test_nd_interface_down_behavior()` - ND behavior when interface is shutdown
- `test_nd_interface_flap_recovery()` - ND recovery during interface flap

**Validates:**
- ND entries when interface goes down
- Connectivity fails when interface is down
- ND recovery when interface comes back up
- Quick ND re-learning after interface flap
- Sustained connectivity after recovery

**Duration:** ~2-3 minutes

### 3. test_nd_multi_vlan.py
**Test Suite:** Multiple VLAN ND Operations
**Test Cases:**
- `test_nd_multiple_vlan_independence()` - ND independence across multiple VLANs

**Validates:**
- ND works independently on each VLAN
- ND entries are VLAN-specific (no cross-VLAN pollution)
- ND failures on one VLAN don't affect others
- Multiple VLAN interfaces maintain separate ND tables

**Duration:** ~3-4 minutes

### 4. test_nd_aging_and_state.py
**Test Suite:** ND Aging and State Transitions
**Test Cases:**
- `test_nd_aging_behavior()` - ND entry aging over time

**Validates:**
- ND entry state transitions
- ND entry aging behavior
- ND entry persistence
- ND behavior documentation

**Duration:** ~1-2 minutes

## Running Tests

### Prerequisites
- Topology: Dual-node (D1, D2) for most tests
- Supported platforms: Hardware and Virtual Switch (VS)
- SONiC build with IPv6 support
- Admin credentials: admin/sonic@123

### Run All ND Tests
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_nd.yaml \
  tests/system/ISCLI_ND/ \
  --logs-path ./logs/nd_all_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Run Individual Test Suite
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

# Basic operations
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_nd.yaml \
  tests/system/ISCLI_ND/test_nd_basic_operations.py \
  --logs-path ./logs/nd_basic_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

# Interface behavior
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_nd.yaml \
  tests/system/ISCLI_ND/test_nd_interface_behavior.py \
  --logs-path ./logs/nd_intf_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

# Multi-VLAN
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_nd.yaml \
  tests/system/ISCLI_ND/test_nd_multi_vlan.py \
  --logs-path ./logs/nd_multi_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

# Aging
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_nd.yaml \
  tests/system/ISCLI_ND/test_nd_aging_and_state.py \
  --logs-path ./logs/nd_aging_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Run Specific Test Case
```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_nd.yaml \
  tests/system/ISCLI_ND/test_nd_basic_operations.py::test_nd_basic_resolution \
  --logs-path ./logs/nd_test_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

## Test Configuration

### Default Configuration
All tests use the following default configuration (can be modified in test files):

**VLAN Configuration:**
- VLAN ID: 100, 200, 300 (depending on test)
- IPv6 Subnet: 2001:db8:100::/64, 2001:db8:200::/64, 2001:db8:300::/64

**DUT Addresses:**
- DUT1: 2001:db8:100::1/64, 2001:db8:200::1/64, 2001:db8:300::1/64
- DUT2: 2001:db8:100::2/64, 2001:db8:200::2/64, 2001:db8:300::2/64

**Interfaces:**
- DUT1: Ethernet0, Ethernet4, Ethernet8
- DUT2: Ethernet0, Ethernet4, Ethernet8

## Test Design Principles

### Error Handling
All tests follow proper error handling:
- Configuration errors are caught and logged
- Validation failures are tracked
- Cleanup is performed even on failures
- Tests continue to completion for full reporting

### Cleanup
Each test ensures proper cleanup:
- Static ND entries are removed
- IPv6 addresses are removed
- VLANs are deleted
- Interfaces are restored to default state

### Logging
Tests provide comprehensive logging:
- STEP banners for major operations
- Detailed command output
- Pass/fail status for each validation
- Summary of errors at test completion

## Manual Test Coverage

These automated tests cover the following manual test scenarios:

1. ✅ **Basic ND Resolution** - Testcase 1 (manual logs)
2. ✅ **ND State Transitions/Aging** - Testcase 2 (manual logs)
3. ✅ **ND Entry Re-learning** - Testcase 3 (manual logs)
4. ✅ **Static ND Entry** - Testcase 4 (manual logs)
5. ✅ **Interface Down Behavior** - Testcase 5 (manual logs)
6. ✅ **Interface Flap Recovery** - Testcase 6 (manual logs)
7. ✅ **ND on VLAN Interface** - Testcases 6-7 (manual logs)
8. ⚠️ **ND on Breakout Ports** - Testcase 8 (manual logs) - *Not implemented*
9. ⚠️ **Link-Local ND Resolution** - Testcase 9 (manual logs) - *Not implemented*
10. ✅ **Multiple VLANs with Independent ND** - Testcase 10 (manual logs)

## Known Behaviors

Based on manual testing, the following behaviors are expected and documented:

1. **ND Entry Visibility:** ND entries may not always appear in `show ipv6 neighbors` output, even when connectivity works. This is normal behavior on some platforms.

2. **Aging Timers:** ND aging timers vary by platform. Typical values:
   - REACHABLE timeout: 30 seconds
   - STALE timeout: variable
   - Total aging: 3-5 minutes

3. **Clear Command:** The `clear ipv6 neighbors` command may not always remove all dynamic entries immediately. Static entries persist as expected.

4. **Interface State:** ND entries may or may not be removed when interface goes down, depending on platform behavior.

## Troubleshooting

### Test Failures

**Ping failures:**
- Verify physical connectivity between DUTs
- Check VLAN configuration is correct
- Ensure IPv6 is enabled on interfaces
- Verify no firewall rules blocking ICMPv6

**ND entry not found:**
- This may be expected behavior (see Known Behaviors)
- Check connectivity still works via ping
- Review platform-specific ND behavior

**Configuration failures:**
- Verify device is accessible
- Check credentials are correct
- Ensure CLI type (klish) is supported
- Review device logs for errors

### Logs

Test logs are saved to the specified `--logs-path` directory:
```
./logs/nd_<test>_<timestamp>/
  ├── summary.txt          # Test summary
  ├── results.xml          # JUnit XML results
  ├── devices/             # Device-specific logs
  └── test_*.log           # Individual test logs
```

## Contributing

When adding new ND tests:
1. Follow the existing pattern from reference scripts
2. Include comprehensive error handling
3. Ensure proper cleanup in all cases
4. Add detailed logging and banners
5. Document expected behaviors
6. Update this README

## References

- Manual test logs: Located in test file headers
- SONiC IPv6 ND documentation: https://github.com/sonic-net/SONiC/blob/master/doc/ipv6/ipv6_nd.md
- Spytest documentation: /home/adminuser/draksha/sonic-mgmt/spytest/README.md
