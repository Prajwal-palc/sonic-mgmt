# ECMP3 Test Suite - Reject Invalid ECMP and Maintain Stability

## Overview

This test suite validates that the SONiC system correctly handles invalid ECMP configurations and maintains stability during various edge cases.

**Test ID**: TC_ECMP_2.4.3
**Feature**: ECMP - Invalid Configuration Rejection and Stability
**CLI Type**: klish (sonic-cli)

## Files Generated

1. **Test Script**: `test_ecmp3_reject_invalid_ecmp.py` (39KB)
   - Complete test implementation with 6 test cases
   - Uses klish CLI type exclusively
   - Simple validation approach with show command outputs stored in variables

2. **Variables File**: `vars_ecmp3.yaml` (4.9KB)
   - Configuration parameters for all test cases
   - Network topology definitions
   - Validation criteria and expected results

3. **Test Plan**: `testcases_ECMP3.md`
   - Detailed test case documentation
   - Step-by-step procedures
   - Validation commands (klish mode)

## Test Cases Included

### TC_ECMP_2.4.3.1: Reject Duplicate Next-Hop
- **Objective**: Verify system rejects duplicate next-hop configuration
- **Validation**: Next-hop count remains 2, no duplicate entries
- **Expected Result**: Duplicate rejected, system stable

### TC_ECMP_2.4.3.2: Reject Unreachable Next-Hop
- **Objective**: Verify system rejects unreachable next-hop
- **Validation**: Only 2 reachable next-hops active, traffic continues
- **Expected Result**: Unreachable not used for forwarding, < 10% packet loss

### TC_ECMP_2.4.3.3: Delete Next-Hop During Traffic
- **Objective**: Verify traffic continues when next-hop deleted during traffic
- **Validation**: Minimal packet loss (< 10%), traffic on remaining path
- **Expected Result**: Traffic continues, < 10% packet loss during transition

### TC_ECMP_2.4.3.4: Re-Add Next-Hop and Verify Recovery
- **Objective**: Verify ECMP recovery when deleted next-hop is re-added
- **Validation**: Next-hop count restored to 2, load distribution balanced
- **Expected Result**: ECMP restored, < 5% packet loss, load balanced

### TC_ECMP_2.4.3.5: Exceed Maximum Next-Hop Limit
- **Objective**: Verify system enforces maximum next-hop limit (64 NH)
- **Validation**: Limit enforced, excess rejected, warning issued
- **Expected Result**: System enforces cap, remains stable
- **Note**: Platform-dependent, typical limit is 64 next-hops

### TC_ECMP_2.4.3.6: Invalid Next-Hop During Traffic
- **Objective**: Verify traffic stability during invalid configuration attempts
- **Validation**: Zero interruption, next-hop count unchanged
- **Expected Result**: Traffic continues, < 5% packet loss, system stable

## Topology Requirements

**3 Nodes**: 1 DUT + 2 Neighbors

```
                    +------------------+
                    |   Destination    |
                    |    Network       |
                    |  200.0.0.0/24    |
                    +------------------+
                            |
         +------------------+------------------+
         |                                     |
    +----+----+                          +-----+-----+
    |Neighbor1|                          |Neighbor2  |
    | 10.0.1.2|                          | 10.0.2.2  |
    +----+----+                          +-----+-----+
         |                                     |
         | Ethernet0                           | Ethernet4
         | 10.0.1.0/30                         | 10.0.2.0/30
         |                                     |
         +------------------+------------------+
                            |
                       +----+----+
                       |   DUT   |
                       | (Router)|
                       +---------+
```

## How to Run

### 1. Run All Test Cases

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_3node_ecmp.yaml \
  tests/routing/ecmp/test_ecmp3_reject_invalid_ecmp.py \
  --logs-path ./logs/test_ecmp3_reject_invalid_ecmp_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### 2. Run Specific Test Case

```bash
# Run only duplicate next-hop test
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_3node_ecmp.yaml \
  tests/routing/ecmp/test_ecmp3_reject_invalid_ecmp.py::TestECMP3RejectInvalidConfig::test_ecmp3_reject_duplicate_nexthop \
  --logs-path ./logs/ecmp3_duplicate_$(date +%F_%H%M%S) \
  --log-level debug

# Run only delete during traffic test
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_3node_ecmp.yaml \
  tests/routing/ecmp/test_ecmp3_reject_invalid_ecmp.py::TestECMP3RejectInvalidConfig::test_ecmp3_delete_nexthop_during_traffic \
  --logs-path ./logs/ecmp3_delete_$(date +%F_%H%M%S) \
  --log-level debug
```

### 3. Run with Custom Variables

```bash
# Set custom variables file
export ECMP3_VAR_FILE=/path/to/custom/vars_ecmp3.yaml

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_3node_ecmp.yaml \
  tests/routing/ecmp/test_ecmp3_reject_invalid_ecmp.py \
  --logs-path ./logs/test_ecmp3_custom_$(date +%F_%H%M%S) \
  --log-level debug
```

## Key Validation Commands (klish mode)

All validation commands are executed inside `sonic-cli` (klish mode):

### Route Verification
```bash
sonic-cli
show ip route 200.0.0.0/24
show ip route static
show ip route
```

### Next-Hop Verification
```bash
show ip next-hop
show arp
```

### Interface Verification
```bash
show interface status Ethernet0
show interface status Ethernet4
show interface counters Ethernet0
show interface counters Ethernet4
clear counters
```

### System Health
```bash
show processes
show system memory
show logging | grep -i route
```

### Platform Capabilities
```bash
show platform capabilities
show ip ecmp
```

## Test Implementation Highlights

### Simple Validation Approach

As per requirements, the test uses a **simple validation approach**:

1. **Store show command outputs in variables**:
   ```python
   output = st.show(
       self.data.dut1,
       f"show ip route {self.data.destination_network}",
       type=self.data.cli_type,
   )
   st.log(f"Route output: {output}")
   ```

2. **Simple string-based validation**:
   ```python
   # Count next-hops by counting 'via' occurrences
   output_str = str(output)
   nexthop_count = output_str.count("via")

   # Check if next-hop exists
   nexthop_exists = nexthop in output_str
   ```

3. **No complex templates** - Direct validation logic:
   ```python
   def _verify_route_nexthop_count(self, expected_count: int) -> bool:
       output = st.show(self.data.dut1, f"show ip route {destination}", type="klish")
       output_str = str(output)
       nexthop_count = output_str.count("via")
       return nexthop_count == expected_count
   ```

### Key Features

- ✅ **Klish CLI Type**: Uses `cli_type="klish"` exclusively
- ✅ **Simple Validation**: Show command outputs stored in variables
- ✅ **Direct Parsing**: String-based validation, no complex templates
- ✅ **Comprehensive Coverage**: All 6 test cases from test plan
- ✅ **Traffic Testing**: Ping-based traffic generation and validation
- ✅ **Counter Monitoring**: Interface counter verification
- ✅ **Error Handling**: Proper cleanup and error management

## Expected Results Summary

| Test Case | Expected Next-Hops | Max Packet Loss | Key Validation |
|-----------|-------------------|-----------------|----------------|
| Duplicate NH | 2 (unchanged) | 0% | Duplicate rejected |
| Unreachable NH | 2 (active) | < 10% | Unreachable not forwarding |
| Delete During Traffic | 1 | < 10% | Traffic continues |
| Re-Add Recovery | 2 (restored) | < 5% | Load balanced |
| Max Limit | ≤ 64 | 0% | Limit enforced |
| Invalid During Traffic | 2 (unchanged) | < 5% | Zero interruption |

## Prerequisites

1. **Topology**: 3 nodes minimum (1 DUT + 2 neighbors)
2. **SONiC Version**: Latest with ECMP support
3. **CLI Access**: sonic-cli (klish) available
4. **Features**: Static routing, ECMP support
5. **Connectivity**: Physical or virtual links between nodes
6. **Tools**: Ping for traffic generation

## Logs and Artifacts

Test logs are stored in the directory specified by `--logs-path`:

```
logs/test_ecmp3_reject_invalid_ecmp_<timestamp>/
├── <testcase_name>.log           # Per-test logs
├── show_commands.log              # All show command outputs
├── config_commands.log            # All configuration commands
└── summary.log                    # Test execution summary
```

## Troubleshooting

### Test Fails - Duplicate Accepted
**Issue**: System accepts duplicate next-hop
**Check**: Verify klish CLI behavior, check SONiC version
**Action**: Review platform-specific duplicate handling

### Test Fails - High Packet Loss
**Issue**: Packet loss > 10% during tests
**Check**: Interface status, connectivity, routing table
**Action**: Verify base topology, check for misconfigurations

### Test Fails - Next-Hop Limit Not Enforced
**Issue**: System accepts more than 64 next-hops
**Check**: Platform capabilities, hardware limits
**Action**: Adjust `max_nexthop_limit` in vars_ecmp3.yaml

### Test Fails - Traffic Interruption
**Issue**: Complete traffic loss during next-hop changes
**Check**: Route convergence time, FIB programming
**Action**: Increase wait times, check system performance

## Customization

### Modify Test Parameters

Edit `vars_ecmp3.yaml` to customize:

```yaml
# Change destination network
network:
  destination_network: "192.168.100.0/24"  # Custom network

# Adjust traffic parameters
traffic:
  ping_count: 200        # More pings
  max_packet_loss: 3.0   # Stricter loss threshold

# Change max limit
network:
  max_nexthop_limit: 128  # Higher limit for capable platforms
```

### Add New Test Cases

Follow the pattern in the test script:

```python
@pytest.mark.inventory(feature="Regression", testcases=["TC_ECMP_2.4.3.X"])
def test_ecmp3_new_test_case(self) -> None:
    """
    TC_ECMP_2.4.3.X: Description of new test.
    """
    st.banner("TC_ECMP_2.4.3.X: Test Case Title")

    # Configure topology
    self._configure_base_topology()

    # Configure routes
    self._configure_baseline_ecmp_routes()

    # Perform test-specific actions
    # ...

    # Validate results
    if not self._verify_route_nexthop_count(expected_count=2):
        st.report_fail("msg", "Validation failed")

    st.report_pass("test_case_passed")
```

## References

- **Test Plan**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testcases_ECMP3.md`
- **Coding Guidelines**: `/home/adminuser/Siddu/sonic-mgmt/spy_test_coding_guideline.md`
- **ECMP Documentation**: SONiC ECMP feature documentation
- **Klish CLI Guide**: SONiC CLI reference documentation

## Support

For issues or questions:
1. Check test logs in `--logs-path` directory
2. Review test plan documentation
3. Verify topology and prerequisites
4. Consult SONiC ECMP documentation

---

**Document Version**: 1.0
**Last Updated**: 2025-11-18
**Author**: Test Engineering Team
**Status**: Ready for Execution
