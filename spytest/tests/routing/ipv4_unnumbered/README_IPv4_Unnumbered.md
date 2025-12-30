# IPv4 Unnumbered Interface Test Suite - Persistence and Platform Stability

## Overview

This test suite validates IPv4 unnumbered interface configuration persistence across various reboot types and correct handling of donor IP dependency.

**Test ID**: TC_IPv4_Unnumbered_1.2.1
**Feature**: IPv4 Unnumbered Interface Persistence and Stability
**CLI Type**: klish (sonic-cli)

## Files Generated

1. **Test Script**: `test_ipv4_unnumbered_1_persistence_and_platform_stability.py`
   - Complete test implementation with 6 test cases
   - Uses klish CLI type exclusively
   - Simple validation approach with show command outputs stored in variables

2. **Variables File**: `vars_ipv4_unnumbered.yaml`
   - Configuration parameters for all test cases
   - Interface definitions (donor and target)
   - Reboot timing parameters
   - Validation criteria and expected results

3. **Test Plan**: `testcases_IPv4_unnumbered_1.md`
   - Detailed test case documentation
   - Step-by-step procedures
   - Validation commands (klish mode)

## Test Cases Included

### TC_IPv4_Unnumbered_1.2.1.1: Configure IPv4 Unnumbered Baseline
- **Objective**: Configure Loopback0 as donor and Ethernet0 as unnumbered interface
- **Validation**: Running-config shows unnumbered, target borrows IP
- **Expected Result**: Configuration successful, IP borrowing functional

### TC_IPv4_Unnumbered_1.2.1.2: Warm Reboot Persistence
- **Objective**: Verify configuration persists across warm reboot
- **Validation**: Config restored, unnumbered functional after reboot
- **Expected Result**: Full persistence, ~5-10 min reboot time

### TC_IPv4_Unnumbered_1.2.1.3: Fast Reboot Persistence
- **Objective**: Verify configuration persists across fast reboot
- **Validation**: Config restored, unnumbered functional after reboot
- **Expected Result**: Full persistence, ~3-8 min reboot time

### TC_IPv4_Unnumbered_1.2.1.4: Cold Reboot Persistence
- **Objective**: Verify configuration persists across cold reboot (full power cycle)
- **Validation**: Config restored, unnumbered functional after reboot
- **Expected Result**: Full persistence, ~5-15 min reboot time

### TC_IPv4_Unnumbered_1.2.1.5: Remove Donor IP - Dependent Failure
- **Objective**: Verify dependent failure when donor IP is removed
- **Validation**: Target has no IP, config persists, system stable
- **Expected Result**: Dependent failure observed, no crash

### TC_IPv4_Unnumbered_1.2.1.6: Restore Donor IP - Automatic Recovery
- **Objective**: Verify automatic recovery when donor IP is restored
- **Validation**: Target automatically recovers IP, no manual intervention
- **Expected Result**: Automatic recovery in < 10 seconds

## Topology Requirements

**1 Node**: Single DUT with Loopback0 (donor) and Ethernet0 (target)

```
+------------------------+
|         DUT            |
|                        |
|  Loopback0 (Donor)     |
|  IP: 10.10.10.1/32     |
|          |             |
|          | (borrows)   |
|          ↓             |
|  Ethernet0 (Target)    |
|  ip unnumbered         |
|  Loopback0             |
+------------------------+
```

## How to Run

### 1. Run All Test Cases

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_1node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_1_persistence_and_platform_stability.py \
  --logs-path ./logs/test_ipv4_unnumbered_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### 2. Run Specific Test Case

```bash
# Run only baseline configuration test
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_1node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_1_persistence_and_platform_stability.py::TestIPv4UnnumberedPersistence::test_ipv4_unnumbered_configure_baseline \
  --logs-path ./logs/ipv4_unnumbered_baseline_$(date +%F_%H%M%S) \
  --log-level debug

# Run only warm reboot test
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_1node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_1_persistence_and_platform_stability.py::TestIPv4UnnumberedPersistence::test_ipv4_unnumbered_warm_reboot_persistence \
  --logs-path ./logs/ipv4_unnumbered_warm_$(date +%F_%H%M%S) \
  --log-level debug

# Run only donor IP removal/restore tests
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_1node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_1_persistence_and_platform_stability.py::TestIPv4UnnumberedPersistence::test_ipv4_unnumbered_remove_donor_ip_failure \
  --logs-path ./logs/ipv4_unnumbered_donor_$(date +%F_%H%M%S) \
  --log-level debug
```

### 3. Run with Custom Variables

```bash
# Set custom variables file
export IPV4_UNNUMBERED_VAR_FILE=/path/to/custom/vars_ipv4_unnumbered.yaml

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_1node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_1_persistence_and_platform_stability.py \
  --logs-path ./logs/test_ipv4_unnumbered_custom_$(date +%F_%H%M%S) \
  --log-level debug
```

## Key Validation Commands (klish mode)

All validation commands are executed inside `sonic-cli` (klish mode):

### Primary Validation Command
```bash
sonic-cli
show running-config interface Ethernet0
```

**Expected Output**:
```
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!
```

### Configuration Verification
```bash
show running-config interface Loopback0
show running-config interface Ethernet0
show startup-config interface Ethernet0
```

### IP Interface Verification
```bash
show ip interface Loopback0
show ip interface Ethernet0
show ip interface brief
```

### Interface Status
```bash
show interface status Loopback0
show interface status Ethernet0
```

### System Health
```bash
show version
show platform summary
show system uptime
show processes
show system memory
```

### Logging
```bash
show logging | grep -i unnumbered
show logging | grep -i error
show reboot-cause
```

## Test Implementation Highlights

### Simple Validation Approach

As per requirements, the test uses a **simple validation approach**:

1. **Store show command outputs in variables**:
   ```python
   output = st.show(
       self.data.dut,
       f"show running-config interface {self.data.target_interface}",
       type=self.data.cli_type,
   )
   st.log(f"Running-config output: {output}")
   ```

2. **Simple string-based validation**:
   ```python
   # Check for unnumbered configuration
   output_str = str(output)
   unnumbered_present = f"ip unnumbered {self.data.donor_interface}" in output_str
   ```

3. **No complex templates** - Direct validation logic:
   ```python
   def _verify_running_config_unnumbered(self) -> bool:
       output = st.show(self.data.dut, f"show running-config interface {interface}", type="klish")
       output_str = str(output)
       return f"ip unnumbered {donor}" in output_str
   ```

### Key Features

- ✅ **Klish CLI Type**: Uses `cli_type="klish"` exclusively
- ✅ **Simple Validation**: Show command outputs stored in variables
- ✅ **Direct Parsing**: String-based validation, no complex templates
- ✅ **Comprehensive Coverage**: All 6 test cases from test plan
- ✅ **Reboot Testing**: Warm, fast, and cold reboot validation
- ✅ **Dependency Testing**: Donor IP removal and restoration
- ✅ **Error Handling**: Proper cleanup and error management

## Expected Results Summary

| Test Case | Expected Behavior | Pass Criteria |
|-----------|------------------|---------------|
| Baseline Config | Unnumbered configured, IP borrowed | Config present, IP = 10.10.10.1/32 |
| Warm Reboot | Config persists, ~5-10 min | Unnumbered functional after reboot |
| Fast Reboot | Config persists, ~3-8 min | Unnumbered functional after reboot |
| Cold Reboot | Config persists, ~5-15 min | Unnumbered functional after reboot |
| Remove Donor IP | Target has no IP (failure) | Dependent failure, system stable |
| Restore Donor IP | Target auto-recovers (< 10s) | Automatic recovery, no manual config |

## Prerequisites

1. **Topology**: 1 node minimum (single DUT)
2. **SONiC Version**: Latest with IPv4 unnumbered support
3. **CLI Access**: sonic-cli (klish) available
4. **Features**: IPv4 unnumbered interface support
5. **Permissions**: Reboot permissions (warm, fast, cold)
6. **Time**: Allow 30-45 minutes for full test suite (includes reboots)

## Test Execution Flow

```
1. Configure Baseline
   ├─ Configure Loopback0 with IP
   ├─ Configure Ethernet0 as unnumbered
   ├─ Verify configuration
   └─ Save config

2. Warm Reboot Test
   ├─ Perform warm reboot (~10 min)
   ├─ Verify config persisted
   └─ Verify unnumbered functional

3. Fast Reboot Test
   ├─ Perform fast reboot (~8 min)
   ├─ Verify config persisted
   └─ Verify unnumbered functional

4. Cold Reboot Test
   ├─ Perform cold reboot (~15 min)
   ├─ Verify config persisted
   └─ Verify unnumbered functional

5. Donor IP Removal Test
   ├─ Remove IP from Loopback0
   ├─ Verify dependent failure
   └─ Verify system stable

6. Donor IP Restore Test
   ├─ Restore IP to Loopback0
   ├─ Verify automatic recovery
   └─ Save final configuration
```

## Logs and Artifacts

Test logs are stored in the directory specified by `--logs-path`:

```
logs/test_ipv4_unnumbered_<timestamp>/
├── <testcase_name>.log           # Per-test logs
├── show_commands.log              # All show command outputs
├── config_commands.log            # All configuration commands
├── reboot_logs.log                # Reboot operation logs
└── summary.log                    # Test execution summary
```

## Troubleshooting

### Test Fails - Configuration Not Persisted
**Issue**: Configuration lost after reboot
**Check**: Verify "write memory" executed before reboot
**Action**: Ensure startup-config matches running-config

### Test Fails - Reboot Timeout
**Issue**: DUT does not come back online after reboot
**Check**: Console access, network connectivity
**Action**: Increase wait time in vars_ipv4_unnumbered.yaml

### Test Fails - No Automatic Recovery
**Issue**: Target doesn't recover IP when donor restored
**Check**: SONiC version, unnumbered feature support
**Action**: Verify feature implementation, check logs

### Test Fails - Donor IP Not Removed
**Issue**: Donor IP removal command fails
**Check**: Interface status, configuration mode
**Action**: Verify klish commands, check permissions

## Customization

### Modify Test Parameters

Edit `vars_ipv4_unnumbered.yaml` to customize:

```yaml
# Change donor interface
interfaces:
  donor:
    name: "Loopback1"        # Use different loopback
    ip: "192.168.1.1/32"     # Different IP

# Change target interface
interfaces:
  target:
    name: "Ethernet4"        # Use different physical interface

# Adjust reboot times
reboot:
  warm:
    max_wait_time: 900       # Increase to 15 minutes
```

### Add New Test Cases

Follow the pattern in the test script:

```python
@pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.1.X"])
def test_ipv4_unnumbered_new_test_case(self) -> None:
    """
    TC_IPv4_Unnumbered_1.2.1.X: Description of new test.
    """
    st.banner("TC_IPv4_Unnumbered_1.2.1.X: Test Case Title")

    # Configure baseline if needed
    if not self.data.unnumbered_configured:
        self._configure_donor_interface()
        self._configure_unnumbered_interface()
        self._save_configuration()

    # Perform test-specific actions
    # ...

    # Validate results
    if not self._verify_running_config_unnumbered():
        st.report_fail("msg", "Validation failed")

    st.report_pass("test_case_passed")
```

## Configuration Examples

### Configure IP Unnumbered (Manual)

```bash
sonic-cli

# Configure donor interface
configure terminal
interface Loopback0
ip address 10.10.10.1/32
no shutdown
exit

# Configure unnumbered interface
interface Ethernet0
no shutdown
ip unnumbered Loopback0
exit
exit

# Save configuration
write memory

# Verify configuration
show running-config interface Ethernet0
show ip interface Ethernet0
```

### Remove IP Unnumbered (Manual)

```bash
sonic-cli

configure terminal
interface Ethernet0
no ip unnumbered Loopback0
exit
exit

write memory
```

## Performance Metrics

### Reboot Times (Expected)
- **Warm Reboot**: 5-10 minutes
- **Fast Reboot**: 3-8 minutes
- **Cold Reboot**: 5-15 minutes

### Recovery Times
- **Auto-recovery after donor IP restore**: < 10 seconds

### System Resources (Normal Operation)
- **CPU Usage**: < 50%
- **Memory Usage**: < 80%

## References

- **Test Plan**: `/home/adminuser/Siddu/sonic-mgmt/spytest/tests/routing/testcases_IPv4_unnumbered_1.md`
- **Coding Guidelines**: `/home/adminuser/Siddu/sonic-mgmt/spy_test_coding_guideline.md`
- **SONiC Documentation**: SONiC IPv4 unnumbered interface feature documentation
- **Klish CLI Guide**: SONiC CLI reference documentation

## Support

For issues or questions:
1. Check test logs in `--logs-path` directory
2. Review test plan documentation
3. Verify topology and prerequisites
4. Consult SONiC IPv4 unnumbered documentation

---

**Document Version**: 1.0
**Last Updated**: 2025-11-18
**Author**: Test Engineering Team
**Status**: Ready for Execution
