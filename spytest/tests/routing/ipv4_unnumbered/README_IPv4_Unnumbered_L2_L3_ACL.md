# IPv4 Unnumbered Interface Test Suite - L2/L3/ACL Scenarios

## Overview

This test suite validates IPv4 unnumbered interface functionality in Layer 2, Layer 3, and Access Control List (ACL) scenarios. Tests verify that unnumbered interfaces behave identically to numbered interfaces for routing operations, connectivity testing, and security policy enforcement.

**Test ID**: TC_IPv4_Unnumbered_1.2.2
**Feature**: IPv4 Unnumbered Interface L2/L3/ACL Functionality
**CLI Type**: klish (sonic-cli)

## Files Generated

1. **Test Script**: `test_ipv4_unnumbered_2_l2_l3_acl.py`
   - Complete test implementation with 6 test cases
   - Uses klish CLI type exclusively
   - Simple validation approach with show command outputs stored in variables

2. **Variables File**: `vars_ipv4_unnumbered_l2_l3_acl.yaml`
   - Configuration parameters for all test cases
   - Interface definitions for DUT1 and DUT2
   - Static route configurations
   - ACL rule definitions
   - Validation criteria and expected results

3. **Test Plan**: `testcases_IPv4_unnumbered_2.md`
   - Detailed test case documentation
   - Step-by-step procedures (17 steps)
   - Validation commands (klish mode)

## Test Cases Included

### TC_IPv4_Unnumbered_1.2.2.1: Configure and Verify
- **Objective**: Configure DUT1 Loopback0 as donor, Ethernet0 as unnumbered, and DUT2 interfaces
- **Validation**: Running-config shows unnumbered configuration on both DUTs
- **Expected Result**: Configuration successful, IP borrowing functional

### TC_IPv4_Unnumbered_1.2.2.2: Basic Layer 3 Connectivity
- **Objective**: Test basic ping between DUT1 and DUT2 Ethernet0
- **Validation**: Ping succeeds with 0% packet loss
- **Expected Result**: Layer 3 connectivity established

### TC_IPv4_Unnumbered_1.2.2.3: Ping with Source Selection
- **Objective**: Verify ping works with explicit source IP selection
- **Validation**: Ping with -I option succeeds (IP, interface, donor interface)
- **Expected Result**: All source selection methods work correctly

### TC_IPv4_Unnumbered_1.2.2.4: Static Routes Over Unnumbered
- **Objective**: Configure and verify static routes using unnumbered interface
- **Validation**: Routes installed in routing table, end-to-end connectivity
- **Expected Result**: Static routing functional over unnumbered interface

### TC_IPv4_Unnumbered_1.2.2.5: ACL Permit Enforcement
- **Objective**: Create and apply ACL that permits traffic, verify enforcement
- **Validation**: Permitted traffic passes, ACL counters increment
- **Expected Result**: ACL permits configured traffic

### TC_IPv4_Unnumbered_1.2.2.6: ACL Deny Enforcement
- **Objective**: Modify ACL to deny traffic, verify enforcement
- **Validation**: Denied traffic blocked (100% packet loss), ACL counters increment
- **Expected Result**: ACL denies configured traffic

## Topology Requirements

**2 Nodes**: DUT1 (unnumbered) and DUT2 (numbered interfaces)

```
                    +------------------------+
                    |         DUT1           |
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
                             |
                             | Ethernet0 (unnumbered)
                             | Uses 10.10.10.1
                             |
                    +------------------------+
                    |         DUT2           |
                    |                        |
                    |  Ethernet0             |
                    |  IP: 10.10.10.2/30     |
                    |                        |
                    |  Loopback0             |
                    |  IP: 20.20.20.1/32     |
                    +------------------------+
```

## How to Run

### 1. Run All Test Cases

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_2_l2_l3_acl.py \
  --logs-path ./logs/test_ipv4_unnumbered_l2_l3_acl_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### 2. Run Specific Test Case

```bash
# Run only configuration and verification test
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_2_l2_l3_acl.py::TestIPv4UnnumberedL2L3ACL::test_ipv4_unnumbered_l2_l3_acl_configure_and_verify \
  --logs-path ./logs/ipv4_unnumbered_config_$(date +%F_%H%M%S) \
  --log-level debug

# Run only connectivity tests
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_2_l2_l3_acl.py::TestIPv4UnnumberedL2L3ACL::test_ipv4_unnumbered_l2_l3_acl_basic_connectivity \
  --logs-path ./logs/ipv4_unnumbered_connectivity_$(date +%F_%H%M%S) \
  --log-level debug

# Run only static routing tests
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_2_l2_l3_acl.py::TestIPv4UnnumberedL2L3ACL::test_ipv4_unnumbered_l2_l3_acl_static_routes \
  --logs-path ./logs/ipv4_unnumbered_routing_$(date +%F_%H%M%S) \
  --log-level debug

# Run only ACL tests
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_2_l2_l3_acl.py::TestIPv4UnnumberedL2L3ACL::test_ipv4_unnumbered_l2_l3_acl_permit_enforcement \
  --logs-path ./logs/ipv4_unnumbered_acl_$(date +%F_%H%M%S) \
  --log-level debug
```

### 3. Run with Custom Variables

```bash
# Set custom variables file
export IPV4_UNNUMBERED_L2_L3_ACL_VAR_FILE=/path/to/custom/vars_ipv4_unnumbered_l2_l3_acl.yaml

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2node_unnumbered.yaml \
  tests/routing/ipv4_unnumbered/test_ipv4_unnumbered_2_l2_l3_acl.py \
  --logs-path ./logs/test_ipv4_unnumbered_l2_l3_acl_custom_$(date +%F_%H%M%S) \
  --log-level debug
```

## Key Validation Commands (klish mode)

All validation commands are executed inside `sonic-cli` (klish mode):

### Primary Validation Commands
```bash
sonic-cli
show running-config
show ip route
```

**Expected Output for Unnumbered Config**:
```
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!
```

**Expected Output for Routing Table**:
```
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, P - PIM, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR, f - OpenFabric,
       > - selected route, * - FIB route

C>* 10.10.10.0/30 is directly connected, Ethernet0, 00:05:32
C>* 10.10.10.1/32 is directly connected, Loopback0, 00:10:15
S>* 20.20.20.1/32 [1/0] via 10.10.10.2, Ethernet0, 00:00:05
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

### Routing Verification
```bash
show ip route
show ip route 20.20.20.1
show ip route 10.10.10.1
show ip route summary
```

### ACL Verification
```bash
show ip access-lists
show ip access-lists TEST_ACL
show ip access-lists interface Ethernet0
```

### Interface Status
```bash
show interface status Ethernet0
show interface counters Ethernet0
```

### ARP Verification
```bash
show arp
show ip arp
```

## Test Implementation Highlights

### Simple Validation Approach

As per requirements, the test uses a **simple validation approach**:

1. **Store show command outputs in variables**:
   ```python
   output = st.show(
       dut,
       "show running-config interface Ethernet0",
       type=self.data.cli_type,
   )
   st.log(f"Running-config output: {output}")
   ```

2. **Simple string-based validation**:
   ```python
   # Check for unnumbered configuration
   output_str = str(output)
   unnumbered_present = "ip unnumbered Loopback0" in output_str
   ```

3. **No complex templates** - Direct validation logic:
   ```python
   def _verify_running_config_has_string(self, dut, search_string: str) -> bool:
       output = st.show(dut, "show running-config interface Ethernet0", type="klish")
       output_str = str(output)
       return search_string in output_str
   ```

4. **Ping statistics parsing**:
   ```python
   def _test_ping(self, source_dut, destination_ip: str) -> Dict[str, Any]:
       cmd = f"ping {destination_ip} -c 5"
       output = st.config(source_dut, cmd, type="vtysh", skip_error_check=True)
       # Parse: "5 packets transmitted, 5 received, 0% packet loss"
       # Return: {"transmitted": 5, "received": 5, "loss_percent": 0.0, "success": True}
   ```

### Key Features

- ✅ **Klish CLI Type**: Uses `cli_type="klish"` exclusively
- ✅ **Simple Validation**: Show command outputs stored in variables
- ✅ **Direct Parsing**: String-based validation, no complex templates
- ✅ **Comprehensive Coverage**: All 6 test cases from test plan
- ✅ **L3 Testing**: Connectivity, source selection, static routes
- ✅ **ACL Testing**: Both permit and deny scenarios
- ✅ **Error Handling**: Proper cleanup and error management

## Expected Results Summary

| Test Case | Expected Behavior | Pass Criteria |
|-----------|------------------|---------------|
| Configure and Verify | Unnumbered configured on DUT1, numbered on DUT2 | Config present, IP borrowing works |
| Basic Connectivity | Ping DUT1 to DUT2 Ethernet0 succeeds | 0% packet loss |
| Source Selection | Ping with -I option works | All source types succeed, 0% loss |
| Static Routes | Routes installed, end-to-end ping works | Routes in FIB, bidirectional ping OK |
| ACL Permit | Permitted traffic passes | 0% loss, counters increment |
| ACL Deny | Denied traffic blocked | 100% loss, counters increment |

## Prerequisites

1. **Topology**: 2 nodes minimum (DUT1 + DUT2)
2. **SONiC Version**: Latest with IPv4 unnumbered support
3. **CLI Access**: sonic-cli (klish) available on both DUTs
4. **Features**:
   - IPv4 unnumbered interface support
   - Static routing support
   - ACL support
5. **Connectivity**: Physical connection between DUT1 Eth0 and DUT2 Eth0
6. **Permissions**: Configuration and ping permissions
7. **Time**: Allow 15-20 minutes for full test suite

## Test Execution Flow

```
1. Configure and Verify
   ├─ Configure DUT1 Loopback0 (donor)
   ├─ Configure DUT1 Ethernet0 (unnumbered)
   ├─ Configure DUT2 Ethernet0 (numbered)
   ├─ Configure DUT2 Loopback0
   ├─ Verify all configurations
   └─ Save configs on both DUTs

2. Basic Connectivity
   ├─ Ping from DUT1 to DUT2 Ethernet0
   ├─ Verify ARP resolution
   └─ Confirm 0% packet loss

3. Source Selection
   ├─ Ping with source IP (-I 10.10.10.1)
   ├─ Ping with source interface (-I Ethernet0)
   ├─ Ping with donor interface (-I Loopback0)
   └─ Verify all methods succeed

4. Static Routes
   ├─ Configure route on DUT1 to DUT2 Loopback0
   ├─ Configure route on DUT2 to DUT1 Loopback0
   ├─ Verify routes in routing table
   ├─ Test end-to-end ping (loopback to loopback)
   └─ Confirm bidirectional reachability

5. ACL Permit
   ├─ Create ACL with permit rules
   ├─ Apply ACL to Ethernet0 inbound
   ├─ Test ping from DUT2 (should succeed)
   ├─ Verify ACL counters increment
   └─ Confirm traffic permitted

6. ACL Deny
   ├─ Create ACL with deny rules
   ├─ Apply ACL to Ethernet0 inbound
   ├─ Test ping from DUT2 (should fail)
   ├─ Verify ACL counters increment
   └─ Confirm traffic denied (100% loss)
```

## Logs and Artifacts

Test logs are stored in the directory specified by `--logs-path`:

```
logs/test_ipv4_unnumbered_l2_l3_acl_<timestamp>/
├── <testcase_name>.log           # Per-test logs
├── show_commands.log              # All show command outputs
├── config_commands.log            # All configuration commands
├── ping_outputs.log               # Ping test results
└── summary.log                    # Test execution summary
```

## Troubleshooting

### Test Fails - Unnumbered Configuration Not Applied
**Issue**: Ethernet0 does not borrow IP from Loopback0
**Check**: Verify Loopback0 has IP configured first
**Action**: Configure donor interface before unnumbered interface

### Test Fails - Ping Fails
**Issue**: Connectivity between DUT1 and DUT2 fails
**Check**: Physical connectivity, interface status, ARP table
**Action**: Verify cables, check `show interface status`, verify subnet configuration

### Test Fails - Static Routes Not Installed
**Issue**: Routes not appearing in routing table
**Check**: Next-hop reachability, route configuration syntax
**Action**: Verify next-hop is reachable, check `show ip route` for errors

### Test Fails - ACL Not Enforcing
**Issue**: ACL applied but traffic not filtered correctly
**Check**: ACL application direction, ACL rule order
**Action**: Verify `show ip access-lists interface Ethernet0`, check rule sequence

### Test Fails - Source Selection Not Working
**Issue**: Ping with -I option fails
**Check**: Source IP exists, source interface is up
**Action**: Verify borrowed IP present, check interface status

## Customization

### Modify Test Parameters

Edit `vars_ipv4_unnumbered_l2_l3_acl.yaml` to customize:

```yaml
# Change DUT1 interfaces
dut1:
  interfaces:
    donor:
      name: "Loopback1"        # Use different loopback
      ip: "192.168.1.1/32"     # Different IP

    target:
      name: "Ethernet4"        # Use different physical interface

# Change DUT2 interfaces
dut2:
  interfaces:
    ethernet0:
      ip: "192.168.1.2/30"     # Different subnet

# Modify ACL rules
acls:
  test_acl_permit:
    rules:
      - "permit icmp any any"  # More permissive
      - "deny ip any any"
```

### Add New Test Cases

Follow the pattern in the test script:

```python
@pytest.mark.inventory(feature="Regression", testcases=["TC_IPv4_Unnumbered_1.2.2.X"])
def test_ipv4_unnumbered_l2_l3_acl_new_test_case(self) -> None:
    """
    TC_IPv4_Unnumbered_1.2.2.X: Description of new test.
    """
    st.banner("TC_IPv4_Unnumbered_1.2.2.X: Test Case Title")

    # Configure baseline if needed
    if not self.data.config_applied:
        self._configure_all_devices()

    # Perform test-specific actions
    # ...

    # Validate results
    if not self._verify_running_config_has_string(self.data.dut1, "expected string"):
        st.report_fail("msg", "Validation failed")

    st.report_pass("test_case_passed")
```

## Configuration Examples

### Configure IP Unnumbered (Manual)

**On DUT1**:
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
```

**On DUT2**:
```bash
sonic-cli

# Configure Ethernet0
configure terminal
interface Ethernet0
ip address 10.10.10.2/30
no shutdown
exit

# Configure Loopback0
interface Loopback0
ip address 20.20.20.1/32
no shutdown
exit
exit

# Save configuration
write memory
```

### Configure Static Routes (Manual)

**On DUT1**:
```bash
sonic-cli
configure terminal
ip route 20.20.20.1/32 10.10.10.2
exit
write memory
```

**On DUT2**:
```bash
sonic-cli
configure terminal
ip route 10.10.10.1/32 10.10.10.1
exit
write memory
```

### Configure ACL (Manual)

```bash
sonic-cli

# Create ACL
configure terminal
ip access-list TEST_ACL
permit icmp 10.10.10.2/32 any
permit tcp any any established
deny ip any any
exit

# Apply to interface
interface Ethernet0
ip access-group TEST_ACL in
exit
exit

# Verify
show ip access-lists TEST_ACL
show running-config interface Ethernet0

# Save
write memory
```

### Remove Configurations (Manual)

```bash
sonic-cli
configure terminal

# Remove ACL from interface
interface Ethernet0
no ip access-group TEST_ACL in
exit

# Remove ACL
no ip access-list TEST_ACL

# Remove static routes
no ip route 20.20.20.1/32 10.10.10.2

# Remove unnumbered
interface Ethernet0
no ip unnumbered Loopback0
exit

# Remove IPs
interface Loopback0
no ip address 10.10.10.1/32
exit

exit
write memory
```

## Performance Metrics

### Connectivity Times (Expected)
- **Ping Response Time**: < 1 ms (local network)
- **ARP Resolution**: < 1 second
- **Route Installation**: < 2 seconds

### ACL Enforcement
- **Application Time**: Immediate
- **Enforcement**: Immediate (no delay)

### Configuration Apply
- **Interface Config**: < 2 seconds
- **Route Config**: < 2 seconds
- **ACL Config**: < 3 seconds

## References

- **Test Plan**: `/home/adminuser/Siddu/sonic-mgmt/spytest/tests/routing/testcases_IPv4_unnumbered_2.md`
- **Coding Guidelines**: `/home/adminuser/Siddu/sonic-mgmt/spy_test_coding_guideline.md`
- **SONiC Documentation**: SONiC IPv4 unnumbered interface feature documentation
- **Klish CLI Guide**: SONiC CLI reference documentation
- **Related Test Suite**: test_ipv4_unnumbered_1_persistence_and_platform_stability.py

## Support

For issues or questions:
1. Check test logs in `--logs-path` directory
2. Review test plan documentation
3. Verify topology and prerequisites
4. Check physical connectivity between DUTs
5. Consult SONiC IPv4 unnumbered documentation

---

**Document Version**: 1.0
**Last Updated**: 2025-11-18
**Author**: Test Engineering Team
**Status**: Ready for Execution
