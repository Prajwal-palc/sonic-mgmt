# Test Cases - Static Route Plan 2.1.2: Management VRF Static Route

## Overview
This document describes test cases for validating IPv4 static routes in Management VRF on SONiC devices.

**Test Plan Reference**: 2.1.2 - Configure and verify Management VRF Static Route – IPv4 Static Route CLI on DUT

**Testbed File**: `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`

**Topology**: Two-node topology (D1-D2) with management interfaces

---

## Test Case: TC-IP-STATIC-MGMT-001

**Test Case ID**: TC-IP-STATIC-MGMT-001

**Title**: Configure and Verify Management VRF IPv4 Static Route

**Description**:
Validate that IPv4 static routes configured in the management VRF are used exclusively for management traffic and do not leak into the default VRF.

**Test Objective**:
- Configure management VRF static routes
- Verify route isolation between management VRF and default VRF
- Validate management traffic routing via eth0 interface
- Verify reachability to destination via management VRF

**Topology Requirements**:
- Minimum: D1D2:1 (Two DUTs connected with at least 1 link)
- Management interface (eth0) connectivity required on both DUTs

**Pre-requisites**:
1. Management VRF must be configured and enabled on the DUT
2. Management interface (eth0) must be configured with IP address
3. Testbed configuration available at specified path
4. SSH/console access to DUTs established

---

## Test Procedure

### Step 1: Initial Configuration and Validation

**Test Case ID**: TC-IP-STATIC-MGMT-001-01

**Test Steps**:
1. Read testbed configuration from `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
2. Extract Ethernet interface information from testbed
3. Extract management interface IP addresses for D1 and D2
4. Verify management VRF exists on both DUTs
5. Verify management interface (eth0) is UP and configured

**Show Commands**:
```bash
show mgmt-vrf
show interface Management 0
show ip interface
ip addr show eth0
```

**Expected Results**:
- Management VRF is present and enabled
- Management interface eth0 is UP
- Management IP addresses are configured
- Management interface is bound to management VRF

---

### Step 2: Enable Management VRF in Config Mode

**Test Case ID**: TC-IP-STATIC-MGMT-001-02

**Test Steps**:
1. Enter config mode: `sudo config vrf add mgmt` (if not already present)
2. Enable management VRF globally
3. Verify management VRF is enabled

**CLI Commands**:
```bash
# Config mode commands
sudo config vrf add mgmt
```

**Show Commands**:
```bash
show mgmt-vrf
show vrf
```

**Expected Results**:
- Management VRF is enabled globally
- Management VRF appears in VRF list

---

### Step 3: Enable Management VRF on Interface

**Test Case ID**: TC-IP-STATIC-MGMT-001-03

**Test Steps**:
1. Bind management interface to management VRF (if not bound)
2. Verify interface VRF binding

**CLI Commands**:
```bash
# Verify/configure interface binding
sudo config interface vrf bind eth0 mgmt
```

**Show Commands**:
```bash
show interface Management 0
ip link show eth0
```

**Expected Results**:
- Management interface is bound to management VRF
- Interface is in UP state

---

### Step 4: Verify Next-Hop Reachability

**Test Case ID**: TC-IP-STATIC-MGMT-001-04

**Test Steps**:
1. Identify next-hop IP address from management network
2. Ping next-hop from DUT1 management interface
3. Verify ICMP echo replies received

**CLI Commands**:
```bash
# Ping next-hop via management interface
ping -I eth0 <next-hop-ip> -c 4
```

**Expected Results**:
- Next-hop is reachable via eth0
- 100% packet success rate (0% packet loss)
- Round-trip time (RTT) values displayed

---

### Step 5: Configure Management VRF Static Route

**Test Case ID**: TC-IP-STATIC-MGMT-001-05

**Test Steps**:
1. Define destination network for testing (e.g., 192.168.100.0/24)
2. Configure static route in management VRF pointing to next-hop
3. Verify route is added to management VRF routing table

**CLI Commands**:
```bash
# Configure static route in management VRF
sudo config route add prefix <destination-network> nexthop vrf mgmt <next-hop-ip>

# Example:
sudo config route add prefix 192.168.100.0/24 nexthop vrf mgmt 192.168.1.1
```

**Show Commands**:
```bash
show ip route vrf mgmt
sudo vtysh -c "show ip route vrf mgmt"
```

**Expected Results**:
- Static route appears in management VRF routing table
- Route shows correct next-hop and VRF association
- Route is marked as static (S) in routing table

---

### Step 6: Verify Route in Management VRF Only

**Test Case ID**: TC-IP-STATIC-MGMT-001-06

**Test Steps**:
1. Display routing table for default VRF
2. Display routing table for management VRF
3. Verify destination network appears ONLY in management VRF
4. Verify no route leakage between VRFs

**Show Commands**:
```bash
# Check default VRF routing table
show ip route

# Check management VRF routing table
show ip route vrf mgmt

# Verify via vtysh
sudo vtysh -c "show ip route"
sudo vtysh -c "show ip route vrf mgmt"
```

**Expected Results**:
- Destination network appears in `show ip route vrf mgmt`
- Destination network does NOT appear in `show ip route` (default VRF)
- No route leakage between management VRF and default VRF
- Route shows correct interface binding (eth0/Management 0)

**Sample Output**:
```
admin@sonic:~$ show ip route vrf mgmt
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR, f - OpenFabric,
       > - selected route, * - FIB route, q - queued route, r - rejected route

VRF mgmt:
S>* 192.168.100.0/24 [1/0] via 192.168.1.1, eth0, 00:00:05
```

---

### Step 7: Verify Destination Reachability via Management VRF

**Test Case ID**: TC-IP-STATIC-MGMT-001-07

**Test Steps**:
1. Ping destination network from DUT1
2. Use management interface explicitly with `-I eth0` option
3. Verify ICMP echo replies received
4. Confirm traffic uses management VRF routing table

**CLI Commands**:
```bash
# Ping destination via management interface
ping -I eth0 <destination-ip> -c 4

# Example:
ping -I eth0 192.168.100.10 -c 4

# Alternative: use VRF context
sudo ip vrf exec mgmt ping <destination-ip> -c 4
```

**Expected Results**:
- Destination is reachable via eth0 interface
- 100% packet success rate
- Traffic uses management VRF routing table
- Packets egress via eth0 (management interface)

---

### Step 8: Verify Route Isolation - No Default VRF Access

**Test Case ID**: TC-IP-STATIC-MGMT-001-08

**Test Steps**:
1. Attempt to ping destination WITHOUT specifying management interface
2. Verify ping fails (no route in default VRF)
3. Confirm route isolation is working correctly

**CLI Commands**:
```bash
# Ping without specifying interface (uses default VRF)
ping <destination-ip> -c 4
```

**Expected Results**:
- Ping fails with "Network is unreachable" or 100% packet loss
- Demonstrates route is isolated to management VRF
- Default VRF does not have route to destination network

---

### Step 9: Validate Management Traffic Exclusivity

**Test Case ID**: TC-IP-STATIC-MGMT-001-09

**Test Steps**:
1. Generate management traffic to destination
2. Verify traffic uses only management VRF
3. Verify data plane interfaces are not used for this traffic
4. Monitor traffic counters on eth0

**CLI Commands**:
```bash
# Monitor interface counters
show interface counters Management 0
ip -s link show eth0

# Generate test traffic
ping -I eth0 <destination-ip> -c 100
```

**Expected Results**:
- Traffic counters increment on eth0/Management 0
- Data plane interface counters do not increment
- All management traffic uses management VRF exclusively

---

### Step 10: Disable Management VRF in Interface Mode

**Test Case ID**: TC-IP-STATIC-MGMT-001-10

**Test Steps**:
1. Unbind management interface from management VRF
2. Verify interface is no longer in management VRF
3. Verify management VRF routes become unreachable

**CLI Commands**:
```bash
# Unbind interface from management VRF
sudo config interface vrf unbind eth0

# Attempt to use route
ping -I eth0 <destination-ip> -c 4
```

**Show Commands**:
```bash
show interface Management 0
show ip route vrf mgmt
```

**Expected Results**:
- Interface is unbound from management VRF
- Management VRF routes show as unreachable/down
- Ping to destination fails

---

### Step 11: Re-enable Management VRF on Interface

**Test Case ID**: TC-IP-STATIC-MGMT-001-11

**Test Steps**:
1. Re-bind management interface to management VRF
2. Verify routes become active again
3. Verify reachability is restored

**CLI Commands**:
```bash
# Re-bind interface to management VRF
sudo config interface vrf bind eth0 mgmt

# Test reachability
ping -I eth0 <destination-ip> -c 4
```

**Show Commands**:
```bash
show interface Management 0
show ip route vrf mgmt
```

**Expected Results**:
- Interface is bound to management VRF
- Routes in management VRF become active
- Destination is reachable again via eth0

---

### Step 12: Disable Management VRF in Config Mode

**Test Case ID**: TC-IP-STATIC-MGMT-001-12

**Test Steps**:
1. Disable management VRF globally
2. Verify management VRF is disabled
3. Verify routes are removed

**CLI Commands**:
```bash
# Disable management VRF
sudo config vrf del mgmt

# Verify VRF status
show mgmt-vrf
```

**Expected Results**:
- Management VRF is disabled
- Management VRF routes are removed
- Destination becomes unreachable

---

### Step 13: Re-enable Management VRF and Restore Configuration

**Test Case ID**: TC-IP-STATIC-MGMT-001-13

**Test Steps**:
1. Re-enable management VRF globally
2. Re-bind interface to management VRF
3. Re-add static route
4. Verify full functionality restored

**CLI Commands**:
```bash
# Re-enable management VRF
sudo config vrf add mgmt

# Re-bind interface
sudo config interface vrf bind eth0 mgmt

# Re-add static route
sudo config route add prefix <destination-network> nexthop vrf mgmt <next-hop-ip>

# Test reachability
ping -I eth0 <destination-ip> -c 4
```

**Show Commands**:
```bash
show mgmt-vrf
show ip route vrf mgmt
sudo vtysh -c "show ip route vrf mgmt"
```

**Expected Results**:
- Management VRF is enabled
- Interface is bound to management VRF
- Static route is present in management VRF routing table
- Destination is reachable via management interface

---

## Validation Summary

### Show Commands Checklist

All of the following commands must be validated during test execution:

**Standard CLI Mode**:
1. `show ip route` - Verify destination is NOT present in default VRF
2. `show ip route vrf mgmt` - Verify destination IS present in management VRF
3. `show mgmt-vrf` - Verify management VRF status
4. `show interface Management 0` - Verify management interface status
5. `show vrf` - List all VRFs

**Vtysh Mode (BGP/FRR)**:
1. `sudo vtysh -c "show ip route"` - Verify default VRF routing table
2. `sudo vtysh -c "show ip route vrf mgmt"` - Verify management VRF routing table

**Linux Commands**:
1. `ip addr show eth0` - Management interface IP configuration
2. `ip link show eth0` - Management interface status
3. `ip route show table mgmt` - Management VRF routing table (Linux view)
4. `ip vrf show` - List VRFs from Linux perspective

---

## Expected Test Results

### 1. Route Presence in Management VRF
✅ The configured static route appears under `show ip route vrf mgmt`
✅ The route displays correct next-hop IP address
✅ The route displays correct outgoing interface (eth0)
✅ The route is marked as static (S) in the routing table

### 2. Management Interface Reachability
✅ The destination network is reachable only via the management interface (eth0)
✅ Ping using `-I eth0` option succeeds with 0% packet loss
✅ Ping using `ip vrf exec mgmt ping` succeeds
✅ Next-hop is reachable from management interface

### 3. VRF Isolation
✅ The route is not leaked into the default VRF
✅ `show ip route` (default VRF) does NOT contain the destination network
✅ Ping without `-I eth0` fails (network unreachable)
✅ No cross-VRF route leakage observed

### 4. Management Traffic Exclusivity
✅ Management traffic uses only the management VRF routing table
✅ Data plane interfaces do not carry management VRF traffic
✅ Traffic counters increment only on eth0/Management 0
✅ Route isolation maintained under all test conditions

### 5. Enable/Disable Functionality
✅ Management VRF can be disabled and re-enabled in config mode
✅ Interface can be unbound and re-bound to management VRF
✅ Configuration persists after disable/enable cycles
✅ Routes become inactive when VRF/interface is disabled
✅ Routes become active again when VRF/interface is re-enabled

---

## Test Data

### Sample Configuration

**DUT1 Management Configuration**:
```
Management IP: 192.168.1.10/24 (from testbed_2vs.yaml)
Management Interface: eth0
Management VRF: mgmt
Next-hop: 192.168.1.1
Destination Network: 192.168.100.0/24
Test Destination IP: 192.168.100.10
```

**DUT2 Management Configuration**:
```
Management IP: 192.168.1.20/24 (from testbed_2vs.yaml)
Management Interface: eth0
Management VRF: mgmt
```

### Sample Routing Table Output

**show ip route vrf mgmt** (Expected):
```
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR, f - OpenFabric,
       > - selected route, * - FIB route

VRF mgmt:
K>* 0.0.0.0/0 [0/0] via 192.168.1.1, eth0, 1d00h00m
C>* 192.168.1.0/24 is directly connected, eth0, 1d00h00m
S>* 192.168.100.0/24 [1/0] via 192.168.1.1, eth0, 00:01:23
```

**show ip route** (Expected - destination NOT present):
```
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR, f - OpenFabric,
       > - selected route, * - FIB route

C>* 10.0.0.0/24 is directly connected, Ethernet0, 1d00h00m
C>* 20.1.1.0/24 is directly connected, Ethernet32, 00:10:00
# Note: 192.168.100.0/24 should NOT appear here
```

---

## Pass/Fail Criteria

### Pass Criteria
- All test steps complete successfully
- All show commands display expected output
- Route appears only in management VRF, not in default VRF
- Destination is reachable via management interface
- Destination is NOT reachable via default VRF
- Enable/disable functionality works correctly
- No route leakage between VRFs
- All validation commands execute without errors

### Fail Criteria
- Route appears in default VRF (route leakage detected)
- Destination is not reachable via management interface
- Destination is reachable via default VRF (incorrect behavior)
- Management VRF cannot be disabled/enabled
- Interface cannot be unbound/bound to management VRF
- Show commands return errors or unexpected output
- Traffic uses data plane interfaces instead of management interface

---

## Cleanup Procedure

After test completion, perform cleanup:

```bash
# Remove static route from management VRF
sudo config route del prefix 192.168.100.0/24 nexthop vrf mgmt 192.168.1.1

# Verify route is removed
show ip route vrf mgmt

# Optionally restore management VRF to default state
# (Usually management VRF should remain enabled)
```

---

## Notes

1. **Testbed Dependency**: This test requires access to testbed file at `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`

2. **Management Network**: Ensure management network connectivity exists between test infrastructure and DUTs

3. **Destination Network**: The destination network (192.168.100.0/24) used in examples should be replaced with an actual reachable network in your test environment

4. **VRF Support**: Verify that the SONiC image under test supports Management VRF feature

5. **Test Duration**: Estimated test execution time: 10-15 minutes

6. **CLI Type**: This test uses standard SONiC CLI (config commands) and vtysh for FRR validation

---

## References

- Test Plan: 2.1.2 - Configure and verify Management VRF Static Route
- SONiC Management VRF HLD: https://github.com/sonic-net/SONiC/blob/master/doc/mgmt/Management%20VRF%20Design.md
- Testbed File: `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
