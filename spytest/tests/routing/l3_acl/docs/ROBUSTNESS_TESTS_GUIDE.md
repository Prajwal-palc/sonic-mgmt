# L3 ACL Robustness Tests - Execution Guide

## Overview

The L3 ACL Robustness Test Suite (L3-R01 through L3-R14) validates the persistence, stability, and correctness of ACL rules under various stress conditions and configuration changes.

**Test File**: `tests/routing/l3_acl/test_l3_acl_robustness.py`

**Framework**: SpyTest (SONiC Python Test Framework)

**Topology**: 3-SONiC-DUT (DUT1=ACL device, DUT2=TX host, DUT3=RX host)

---

## Test Coverage

### Category 1: IP-Based Rule Persistence (3 tests)

| Test ID | Name | Purpose | Status |
|---------|------|---------|--------|
| **L3-R01** | ACL rule persistence after IP config change | Verify ACL rules work after host IP reconfiguration | ✅ Implemented |
| **L3-R02** | High-frequency rule updates with live traffic | Verify rapid rule changes don't corrupt state | 📝 Stub |
| **L3-R03** | Concurrent multiple IP-based ACL rules | Verify overlapping rules don't interfere | 📝 Stub |

### Category 2: Protocol Rule Stability (6 tests)

| Test ID | Name | Purpose | Status |
|---------|------|---------|--------|
| **L3-R04** | Protocol rule persistence during port config change | Verify protocol rules survive interface reconfig | 📝 Stub |
| **L3-R05** | ACL rule state consistency under protocol stress | Verify rules with rapid protocol changes | 📝 Stub |
| **L3-R06** | Deny + Permit protocol rules with same IP | Verify rule precedence with mixed actions | 📝 Stub |
| **L3-R07** | TCP flag rule persistence across connection resets | Verify TCP flag rules survive RST packets | 📝 Stub |
| **L3-R08** | Stateful TCP flag evaluation under sustained traffic | Verify TCP flags with 10000+ packet streams | 📝 Stub |
| **L3-R09** | Concurrent TCP SYN and ACK from different flows | Verify concurrent TCP rule evaluation | 📝 Stub |

### Category 3: Advanced Rule Accuracy (5 tests)

| Test ID | Name | Purpose | Status |
|---------|------|---------|--------|
| **L3-R10** | ACL rule persistence after DSCP config change | Verify DSCP rules survive QoS changes (HW-only) | 📝 Stub |
| **L3-R11** | 5-tuple rule accuracy under 100K+ packet streams | Verify hit counters with high-volume traffic | 📝 Stub |
| **L3-R12** | Mixed 5-tuple and subnet-based rules | Verify different rule types coexist | 📝 Stub |
| **L3-R13** | ACL rule atomicity during rapid reconfig | Verify atomic rule updates | 📝 Stub |
| **L3-R14** | Implicit deny enforcement with permit rules present | Verify implicit deny works with permits | 📝 Stub |

---

## Running the Tests

### Prerequisites

```bash
# Ensure testbed is accessible
ping -c 1 192.168.100.190  # DUT1
ping -c 1 192.168.100.67   # DUT2
ping -c 1 192.168.100.134  # DUT3

# Verify required packages on DUTs
# - Python 3.8+
# - Scapy
# - tcpdump
```

### Run All Robustness Tests

```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_robustness.py \
    --logs-path ./logs/l3_acl_robustness_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native
```

### Run Single Test (e.g., L3-R01)

```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_robustness.py::TestL3AclRobustness::test_l3_r01_acl_persistence_after_ip_change \
    --logs-path ./logs/l3_acl_r01_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config
```

### Run Tests Matching Pattern

```bash
# Run persistence tests only (L3-R01, R04, R10, R13)
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_robustness.py \
    -k "persistence" \
    --logs-path ./logs/l3_acl_persistence \
    --log-level info --skip-init-config

# Run TCP-related tests only (L3-R07, R08, R09)
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_robustness.py \
    -k "tcp" \
    --logs-path ./logs/l3_acl_tcp \
    --log-level info --skip-init-config
```

---

## Test Structure

Each robustness test follows a standard execution pattern:

### Test Execution Phases

```
PHASE 1: Cleanup
  └─ Remove old pcap files

PHASE 2: Configure ACL (if applicable)
  ├─ Create ACL table
  └─ Create ACL rules

PHASE 3: Preparation/Configuration Change
  ├─ Start tcpdump listener
  └─ Apply test-specific configuration (e.g., IP change)

PHASE 4: Generate Traffic
  └─ Send Scapy-based traffic from DUT2

PHASE 5: Stop Verification
  └─ Stop tcpdump and flush packets

PHASE 6: Verify Results
  ├─ Count received packets from pcap
  └─ Validate against expected behavior

PHASE 7: Validate
  └─ Pass/Fail based on criteria
```

---

## Test Details

### L3-R01: ACL Rule Persistence After IP Config Change

**What it tests:**
- ACL rules continue to function correctly when the source host's IP address changes
- Rules are not invalidated by IP reconfiguration

**Execution:**
1. Configure ACL rule denying 10.0.0.99/32
2. Send traffic from 10.0.0.1 (should PASS - ≥90%)
3. Send traffic from 10.0.0.99 (should DROP - 0%)
4. Change DUT2's IP from 10.0.0.1 to 10.0.0.100
5. Send traffic from new IP 10.0.0.100 (should PASS - ≥90%)

**Expected Result:**
- Before IP change: RX ≥ 90% of TX
- Blocked IP traffic: RX = 0 (all denied)
- After IP change: RX ≥ 90% of TX
- Test PASSES if all expectations met

**Example Run:**
```bash
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_robustness.py::TestL3AclRobustness::test_l3_r01_acl_persistence_after_ip_change \
    --logs-path ./logs/l3_r01 --log-level debug --skip-init-config
```

---

### L3-R02: High-Frequency Rule Updates with Live Traffic

**Status:** Currently a stub test (requires SM_ISCLI batch command support)

**What it will test:**
- ACL rule updates (add/delete) while traffic is actively flowing
- DUT handles rapid configuration changes without errors
- No packet loss or rule state inconsistency

**Prerequisites for full implementation:**
- SM_ISCLI batch command API for high-speed CLI operations (100+/sec)
- Background traffic generation with pps monitoring
- Real-time rule update orchestration

---

### L3-R03: Concurrent Multiple IP-Based ACL Rules

**Status:** Currently a stub test

**What it will test:**
- Multiple overlapping IP-based rules can coexist
- Rule specificity (more specific rules take precedence)
- No rule interference or unexpected behavior

**Example configuration:**
- Rule 1: Deny 10.0.0.0/25 (more specific)
- Rule 2: Deny 10.0.0.0/24 (less specific)
- Rule 3: Permit 10.0.0.1/32 (specific permit)

---

## Interpreting Results

### Log Output

After test execution, check the logs:

```bash
# View test results
cat logs/l3_acl_robustness_<timestamp>/summary.txt

# View detailed test logs
cat logs/l3_acl_robustness_<timestamp>/dlog-D1-<hostname>.log

# View HTML report
open logs/l3_acl_robustness_<timestamp>/dashboard.html
```

### Pass/Fail Criteria

| Test Type | Pass Condition | Fail Condition |
|-----------|---|---|
| **PERMIT rule** | RX ≥ 90% of TX | RX < 90% of TX |
| **DENY rule** | RX = 0 (all dropped) | RX > 0 (some passed) |
| **Persistence** | Rule works after config change | Rule fails after change |
| **Concurrent rules** | All rules evaluated correctly | Rules interfere or conflict |

### Common Issues

#### Issue: "tcpdump failed to start on DUT3"
- **Cause**: tcpdump not installed or permissions issue
- **Solution**: `sudo apt-get install tcpdump` on DUT3

#### Issue: "Traffic generation failed"
- **Cause**: Scapy not installed on DUT2
- **Solution**: `pip3 install scapy --break-system-packages` on DUT2

#### Issue: "RX = 0 but expecting traffic"
- **Cause**: Routing not configured or ACL incorrectly applied
- **Solution**: Verify `ping 20.0.0.2` from DUT2 works (baseline connectivity)

#### Issue: "Pcap file not found"
- **Cause**: tcpdump didn't capture or permission issue
- **Solution**: Check `/tmp/l3_r0X_rx.pcap` exists and is readable

---

## Implementation Status

### Completed

- ✅ **L3-R01**: Full implementation with IP reconfiguration validation
- ✅ **Test framework**: Complete setup_class(), teardown_class(), cleanup fixtures
- ✅ **Helper methods**: All traffic generation, tcpdump, and packet counting functions
- ✅ **Dynamic port discovery**: From testbed topology (no hardcoded ports)
- ✅ **Error handling**: Comprehensive with fallback strategies
- ✅ **Pytest discovery**: All 14 tests discoverable

### In Progress / Stubs

- 📝 **L3-R02 to L3-R14**: Placeholder implementations ready for expansion

---

## Configuration

### Test Variables (YAML)

Test parameters are loaded from:
```
spytest/vars/routing/l3_acl/vars_l3_acl.yaml
```

Structure:
```yaml
defaults:
  min_topology: ["D1D2:1", "D1D3:1"]
  cli_type: klish
  verify_timeout: 30
  cleanup: true

dut_l3_config:
  dut1:
    eth0_ip: "10.0.0.254"
    eth4_ip: "20.0.0.254"
  dut2:
    eth0_ip: "10.0.0.1"
  dut3:
    eth0_ip: "20.0.0.2"

testcases:
  "L3-R01":
    title: "ACL rule persistence after IP config change"
    acl:
      tables:
        L3_ACL_TABLE_R01:
          type: "L3"
          stage: "INGRESS"
          ports: ["Ethernet40"]
          rules:
            - rule_name: "RULE_R01_DENY_99"
              action: "deny"
              src_ip: "10.0.0.99/32"
              protocol: "udp"
    traffic:
      source_ip: "10.0.0.1"
      new_source_ip: "10.0.0.100"
      blocked_source_ip: "10.0.0.99"
      dest_ip: "20.0.0.2"
      num_packets: 100
      duration: 10
```

### Environment Variables

```bash
# Override default YAML file location
export L3_ACL_VAR_FILE="/path/to/custom/vars_l3_acl.yaml"

# Run test with custom variables
./bin/spytest --testbed ./testbeds/testbed_acl.yaml \
    tests/routing/l3_acl/test_l3_acl_robustness.py \
    --logs-path ./logs/custom \
    --log-level debug --skip-init-config
```

---

## Advanced Features

### Dynamic Port Discovery

Tests automatically discover port connections from the testbed topology:

```python
# From testbeds/testbed_acl.yaml
topology:
  DUT1:
    interfaces:
      Ethernet40: {EndDevice: DUT2, EndPort: Ethernet24}
      Ethernet24: {EndDevice: DUT3, EndPort: Ethernet24}
```

No hardcoded ports needed - all tests use discovered values.

### Automatic Cleanup

Each test has automatic ACL cleanup via pytest fixture:

```python
@pytest.fixture(autouse=True)
def cleanup_acl_after_each_test(self):
    yield  # Test runs here
    # Cleanup runs automatically after test completes
```

### Traffic Generation

Uses SPyTest's `scapy_traffic` API:

```python
result = scapy_traffic.send_traffic(
    dut=self.data.dut2,
    interface=dut2_tx_port,
    src_ip=source_ip,
    dst_ip=dest_ip,
    src_mac=dut2_mac,
    dst_mac=dut1_mac,
    duration=duration,
    pps=pps,
    traffic_type="udp"
)
```

### Packet Verification

Uses Scapy's `rdpcap()` for forensic analysis:

```python
cmd = f'sudo python3 -c "from scapy.all import rdpcap; print(len(rdpcap(\\"{pcap_path}\\")))"'
output = st.show(dut, cmd, skip_tmpl=True)
packet_count = int(output.strip().split('\n')[-1])
```

---

## Extending the Test Suite

### Adding a New Robustness Test

1. **Define the test method**:
   ```python
   @pytest.mark.inventory(feature="L3_ACL_ROBUSTNESS", testcases=["test_l3_rXX_description"])
   @pytest.mark.skip_module_config_save
   def test_l3_rXX_description(self) -> None:
       """Test description and expected behavior"""
       st.banner("Test L3-RXX: Description")
       # Implementation
       st.report_pass("test_case_passed")
   ```

2. **Add YAML configuration** (if needed):
   ```yaml
   testcases:
     "L3-RXX":
       title: "Test title"
       acl: { ... }
       traffic: { ... }
   ```

3. **Implement test logic** following the 7-phase pattern

4. **Add to cleanup fixture** (if new ACL table created):
   ```python
   test_acl_tables = [
       # ... existing tables ...
       "L3_ACL_TABLE_RXX",  # New table name
   ]
   ```

---

## Related Documentation

- **Test Plan**: `tests/routing/l3_acl/docs/acl-l3.md`
- **Functional Tests**: `tests/routing/l3_acl/test_l3_acl_basic_refactored.py`
- **Negative Tests**: `tests/routing/l3_acl/test_l3_acl_basic.py`
- **Framework Guide**: `CLAUDE.md`

---

## Support

For issues or questions:
1. Check test logs in `--logs-path` directory
2. Review test docstring for expected behavior
3. Verify prerequisite connectivity with ping tests
4. Check DUT logs: `show acl table`, `show acl-rule`

---

**Document Version**: 1.0
**Updated**: 2026-03-13
**Status**: ✅ Ready for Testing

