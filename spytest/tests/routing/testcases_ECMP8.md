# Test Cases - ECMP Path Qualification and Limits Validation

## Test Case ID: TC_ECMP_2.4.8

### Test Case Name
ECMP Equal-Cost Path Qualification and Limit Enforcement

### Test Objective
Validate that only equal-cost paths qualify for ECMP installation and that invalid paths are correctly rejected. Test the enforcement of ECMP path limits (maximum-paths configuration) and verify proper handling of route flapping scenarios. Ensure that routes with unequal costs (different OSPF metrics or different BGP AS-PATH lengths) are not installed as ECMP, that the system correctly caps the number of ECMP paths at the configured limit, and that no routing loops occur. Verify that error conditions are properly logged when invalid ECMP configurations are attempted.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_4node_ecmp_limits.yaml`
- **Topology**: 4 nodes (1 DUT + 3 routing peers)
- **Device Under Test (DUT)**: Primary router under test
- **Routing Peers**: Peer1, Peer2, Peer3
- **Test Protocols**: OSPF and BGP

### Topology Diagram

```
                    [Peer1]         [Peer2]         [Peer3]
                   OSPF/BGP        OSPF/BGP        OSPF/BGP
                  (Cost/AS-PATH   (Cost/AS-PATH   (Cost/AS-PATH
                   variations)     variations)     variations)
                        |              |               |
                        | Ethernet0    | Ethernet4     | Ethernet8
                        |              |               |
                        +--------------+---------------+
                                       |
                                  +----+----+
                                  |   DUT   |
                                  | (Router)|
                                  +---------+

Purpose: Test ECMP path qualification with:
- Different OSPF metrics (cost variations)
- Different BGP AS-PATH lengths
- Maximum-paths limit enforcement
- Route flapping scenarios
```

### Interface Configuration

**DUT Interfaces**:
- **Ethernet0**: Connected to Peer1 (10.0.0.0/31, IP: 10.0.0.1)
- **Ethernet4**: Connected to Peer2 (10.0.4.0/31, IP: 10.0.4.1)
- **Ethernet8**: Connected to Peer3 (10.0.8.0/31, IP: 10.0.8.1)
- **Loopback0**: 1.1.1.1/32 (Router ID)

**OSPF Configuration**:
- **Area**: 0.0.0.0 (Backbone)
- **Router ID**: 1.1.1.1
- **Network Type**: Point-to-Point
- **Cost Variations**: Different costs on each peer link for testing

**BGP Configuration**:
- **DUT ASN**: 64512
- **Peer1 ASN**: 65001
- **Peer2 ASN**: 65002
- **Peer3 ASN**: 65003
- **AS-PATH Variations**: Different AS-PATH lengths for testing

**Test Scenarios**:
1. **OSPF Different Metrics**: Peer1 (cost 10), Peer2 (cost 20), Peer3 (cost 10)
2. **BGP Different AS-PATH**: Peer1 (1 AS hop), Peer2 (2 AS hops), Peer3 (1 AS hop)
3. **ECMP Limit**: Configure maximum-paths 2, advertise 3 equal-cost paths
4. **Route Flap**: Rapidly change metrics/AS-PATH to induce flapping

### Prerequisites
1. All 4 devices accessible via SSH
2. SONiC OS installed on all devices
3. Access to sonic-cli (klish) on all devices
4. OSPF and BGP routing protocol support
5. All interfaces physically connected
6. Route table and FIB capacity sufficient

---

## Test Procedure

### Step 1: Initial Setup - Configure IP Addresses on DUT
**Objective**: Configure IP addresses on all DUT interfaces

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0 (to Peer1)
interface Ethernet0
ip address 10.0.0.1/31
no shutdown
exit

# Configure Ethernet4 (to Peer2)
interface Ethernet4
ip address 10.0.4.1/31
no shutdown
exit

# Configure Ethernet8 (to Peer3)
interface Ethernet8
ip address 10.0.8.1/31
no shutdown
exit

# Configure Loopback0 (Router ID)
interface Loopback0
ip address 1.1.1.1/32
exit

# Exit configuration mode
exit
```

**Expected Result**:
- All 3 peer-facing interfaces configured
- All interfaces operational (up/up)
- Loopback configured for router ID

---

### Step 2: Test Scenario 1 - OSPF Different Metrics (Unequal Cost)
**Objective**: Verify that only equal-cost OSPF paths are installed in ECMP

#### Step 2.1: Configure OSPF with Different Costs

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure OSPF
router ospf
router-id 1.1.1.1
network 10.0.0.0/31 area 0.0.0.0
network 10.0.4.0/31 area 0.0.0.0
network 10.0.8.0/31 area 0.0.0.0
network 1.1.1.1/32 area 0.0.0.0
exit

# Configure Ethernet0 - Cost 10 (to Peer1)
interface Ethernet0
ip ospf network point-to-point
ip ospf cost 10
exit

# Configure Ethernet4 - Cost 20 (to Peer2) - DIFFERENT COST
interface Ethernet4
ip ospf network point-to-point
ip ospf cost 20
exit

# Configure Ethernet8 - Cost 10 (to Peer3)
interface Ethernet8
ip ospf network point-to-point
ip ospf cost 10
exit

exit
```

**Configure Peers to Advertise Same Destination**:
All three peers should advertise the same destination prefix (e.g., 192.168.100.0/24)
with equal cost from their side.

**Expected Result**:
- Peer1 (cost 10) and Peer3 (cost 10): Equal cost
- Peer2 (cost 20): Different cost
- Only Peer1 and Peer3 should be used for ECMP

#### Step 2.2: Verify OSPF Route Installation

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify OSPF neighbors
show ip ospf neighbor

# Verify OSPF route with different metrics
show ip route ospf

# Check specific destination route
show ip route 192.168.100.0/24

# Verify OSPF database
show ip ospf database
```

**Expected Result**:
```
# show ip route 192.168.100.0/24
O    192.168.100.0/24 [110/20]
       via 10.0.0.0, Ethernet0, weight 1, 00:05:23  (Cost 10)
       via 10.0.8.0, Ethernet8, weight 1, 00:05:23  (Cost 10)

# Peer2 (10.0.4.0) should NOT appear because cost 20 != cost 10
# Only equal-cost paths (cost 10) installed as ECMP
```

**Validation Points**:
1. **Only 2 next-hops** installed (Peer1 and Peer3)
2. Peer2 **NOT** in ECMP (cost 20 is higher)
3. Route metric shows cost 20 (10 + 10 from both equal paths)
4. No routing loops
5. Equal-cost requirement enforced

#### Step 2.3: Verify Logs for Rejected Path

**Commands (Execute on DUT)**:
```bash
# Check system logs for OSPF route calculations
sonic-cli

# View OSPF logs
show logging | grep -i ospf | tail -50

# Check for route selection messages
show logging | grep -i route | tail -50
```

**Expected Result**:
- Logs may show SPF calculation
- Route from Peer2 received but not selected for ECMP due to higher cost
- No error logs (different cost is valid, just not ECMP-eligible)

---

### Step 3: Test Scenario 2 - BGP Different AS-PATH Lengths
**Objective**: Verify that only BGP paths with equal AS-PATH length qualify for ECMP

#### Step 3.1: Configure BGP with Different AS-PATH Lengths

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure BGP
router bgp 64512
bgp router-id 1.1.1.1
maximum-paths 3

# Configure BGP neighbors
neighbor 10.0.0.0 remote-as 65001
neighbor 10.0.0.0 activate

neighbor 10.0.4.0 remote-as 65002
neighbor 10.0.4.0 activate

neighbor 10.0.8.0 remote-as 65003
neighbor 10.0.8.0 activate

exit
exit
```

**Configure Peers to Advertise Routes with Different AS-PATH Lengths**:

**Peer1 (AS 65001)**: Advertise 172.16.0.0/24 with AS-PATH: 65001 (length 1)

**Peer2 (AS 65002)**: Advertise 172.16.0.0/24 with AS-PATH: 65002 65010 (length 2) - PREPENDED

**Peer3 (AS 65003)**: Advertise 172.16.0.0/24 with AS-PATH: 65003 (length 1)

**Example Configuration on Peer2 (to prepend AS)**:
```bash
# On Peer2
sonic-cli
configure terminal

router bgp 65002
neighbor 10.0.4.1 remote-as 64512

# Create route-map to prepend AS
route-map PREPEND-AS permit 10
set as-path prepend 65010
exit

# Apply to neighbor
neighbor 10.0.4.1 route-map PREPEND-AS out
exit
exit
```

#### Step 3.2: Verify BGP Route Installation

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify BGP sessions
show ip bgp summary

# Verify BGP routes with AS-PATH
show ip bgp

# Check specific route with AS-PATH details
show ip bgp 172.16.0.0/24

# Verify installed route
show ip route 172.16.0.0/24
```

**Expected Result**:
```
# show ip bgp 172.16.0.0/24
BGP routing table entry for 172.16.0.0/24
Paths: (3 available, 2 best)
  Multipath: eBGP

  65001
    10.0.0.0 from 10.0.0.0 (2.2.2.2)
      Origin IGP, metric 0, valid, external, multipath, best
      AS-PATH: 65001 (length 1)

  65002 65010
    10.0.4.0 from 10.0.4.0 (3.3.3.3)
      Origin IGP, metric 0, valid, external
      AS-PATH: 65002 65010 (length 2) - NOT MULTIPATH

  65003
    10.0.8.0 from 10.0.8.0 (4.4.4.4)
      Origin IGP, metric 0, valid, external, multipath, best
      AS-PATH: 65003 (length 1)

# show ip route 172.16.0.0/24
B    172.16.0.0/24 [20/0]
       via 10.0.0.0, Ethernet0, weight 1, 00:02:15
       via 10.0.8.0, Ethernet8, weight 1, 00:02:15

# Only Peer1 and Peer3 in ECMP (AS-PATH length 1)
# Peer2 NOT in ECMP (AS-PATH length 2 is longer)
```

**Validation Points**:
1. **Only 2 next-hops** installed (Peer1 and Peer3)
2. Peer2 **NOT** in ECMP (AS-PATH length 2 != 1)
3. Both installed paths have AS-PATH length 1
4. Equal AS-PATH length requirement enforced
5. Route from Peer2 received but not selected for multipath

#### Step 3.3: Verify BGP Multipath Selection Logs

**Commands (Execute on DUT)**:
```bash
# Check BGP logs
sonic-cli

show logging | grep -i bgp | tail -50

# Check route selection
show logging | grep -i multipath | tail -20
```

**Expected Result**:
- Logs show BGP best path selection
- Path from Peer2 not selected for multipath due to different AS-PATH length
- No errors (valid configuration, just not ECMP-eligible)

---

### Step 4: Test Scenario 3 - ECMP Path Limit Enforcement
**Objective**: Verify that maximum-paths limit is enforced and excess paths are rejected

#### Step 4.1: Configure Maximum-Paths Limit

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Set maximum-paths to 2 (less than available equal-cost paths)
configure terminal
router bgp 64512
maximum-paths 2
exit
exit
```

#### Step 4.2: Configure All Peers with Equal AS-PATH

Reconfigure Peer2 to remove AS prepending so all 3 peers have equal AS-PATH length:

**On Peer2**:
```bash
# Remove prepending
sonic-cli
configure terminal
router bgp 65002
no neighbor 10.0.4.1 route-map PREPEND-AS out
exit
exit

# Clear BGP to refresh
clear ip bgp *
```

#### Step 4.3: Verify Path Limit Enforcement

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify BGP configuration
show running-configuration router bgp | grep maximum-paths

# Check BGP routes (should show 3 available paths)
show ip bgp 172.16.0.0/24

# Check installed routes (should show only 2 next-hops due to limit)
show ip route 172.16.0.0/24

# Verify routing table
show ip route bgp
```

**Expected Result**:
```
# show running-configuration router bgp | grep maximum-paths
 maximum-paths 2

# show ip bgp 172.16.0.0/24
BGP routing table entry for 172.16.0.0/24
Paths: (3 available, best #1)
  Note: Only 2 paths installed due to maximum-paths limit

  65001
    10.0.0.0 from 10.0.0.0 (2.2.2.2)
      Origin IGP, valid, external, multipath, best

  65002
    10.0.4.0 from 10.0.4.0 (3.3.3.3)
      Origin IGP, valid, external, multipath

  65003
    10.0.8.0 from 10.0.8.0 (4.4.4.4)
      Origin IGP, valid, external
      (Not installed - exceeds maximum-paths limit)

# show ip route 172.16.0.0/24
B    172.16.0.0/24 [20/0]
       via 10.0.0.0, Ethernet0, weight 1, 00:01:30
       via 10.0.4.0, Ethernet4, weight 1, 00:01:30

# Only 2 next-hops despite 3 equal-cost paths available
# Maximum-paths limit enforced
```

**Validation Points**:
1. **Maximum-paths = 2** configured
2. **3 equal-cost paths** available in BGP table
3. **Only 2 paths installed** in routing table
4. Limit correctly enforced
5. No routing loops
6. Excess path not installed (cap enforced)

#### Step 4.4: Verify Limit Enforcement Logs

**Commands (Execute on DUT)**:
```bash
# Check logs for path limit enforcement
sonic-cli

show logging | grep -i "maximum-paths" | tail -20
show logging | grep -i "multipath" | tail -20
show logging | grep -i "limit" | tail -20
```

**Expected Result**:
- Logs may show BGP multipath calculation
- Indication that not all paths installed due to limit
- System enforces configured maximum-paths value
- Logs show proper handling (not an error, just limit enforcement)

---

### Step 5: Test Scenario 4 - Route Flapping
**Objective**: Induce route flapping and verify system stability and proper handling

#### Step 5.1: Induce Route Flap by Changing OSPF Cost Rapidly

**Commands (Execute on DUT)**:
```bash
# Rapidly change OSPF cost on Ethernet0 multiple times
# This induces route flapping for OSPF routes

# Flap 1: Change cost to 15
sonic-cli
configure terminal
interface Ethernet0
ip ospf cost 15
exit
exit

# Wait 2 seconds

# Flap 2: Change cost back to 10
sonic-cli
configure terminal
interface Ethernet0
ip ospf cost 10
exit
exit

# Wait 2 seconds

# Flap 3: Change cost to 20
sonic-cli
configure terminal
interface Ethernet0
ip ospf cost 20
exit
exit

# Wait 2 seconds

# Flap 4: Change cost back to 10 (stable)
sonic-cli
configure terminal
interface Ethernet0
ip ospf cost 10
exit
exit
```

#### Step 5.2: Monitor Route Flapping

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Monitor OSPF routes during flapping
show ip route ospf

# Check specific route
show ip route 192.168.100.0/24

# Verify OSPF neighbor stability
show ip ospf neighbor

# Check OSPF statistics
show ip ospf statistics
```

**Expected Result During Flapping**:
- Route next-hops change as cost changes
- When cost 15 or 20: Only Peer3 (cost 10) used (single path)
- When cost 10: Peer1 and Peer3 both used (ECMP)
- OSPF neighbors remain stable
- SPF recalculations triggered by cost changes

#### Step 5.3: Induce BGP Route Flap by Session Reset

**Commands (Execute on DUT)**:
```bash
# Rapidly reset BGP session to Peer1

# Flap 1: Shutdown neighbor
sonic-cli
configure terminal
router bgp 64512
neighbor 10.0.0.0 shutdown
exit
exit

# Wait 5 seconds

# Flap 2: Restore neighbor
sonic-cli
configure terminal
router bgp 64512
no neighbor 10.0.0.0 shutdown
exit
exit

# Wait for session to re-establish

# Flap 3: Clear BGP session
clear ip bgp 10.0.0.0

# Wait for reconvergence
```

#### Step 5.4: Verify System Stability After Flapping

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify OSPF routes stable
show ip route ospf

# Verify BGP routes stable
show ip route bgp

# Check for route flapping logs
show logging | grep -i flap | tail -30

# Check for route dampening (if configured)
show ip bgp dampening flap-statistics

# Verify no routing loops
show ip route 192.168.100.0/24
show ip route 172.16.0.0/24

# Check system CPU/memory
show processes
```

**Expected Result**:
- Routes eventually stabilize
- All configured equal-cost paths installed
- No routing loops detected
- Logs show route changes during flapping
- System remains stable (no crashes)
- ECMP correctly reformed after flapping stops

#### Step 5.5: Review Flapping Logs

**Commands (Execute on DUT)**:
```bash
# Check detailed logs for flapping events
sonic-cli

# OSPF logs
show logging | grep -i ospf | grep -i "route" | tail -50

# BGP logs
show logging | grep -i bgp | grep -i "route" | tail -50

# Route change logs
show logging | grep -i "route change" | tail -30

# Check for any error conditions
show logging | grep -i error | tail -30
```

**Expected Result - Logs Show**:
- OSPF SPF recalculations triggered by cost changes
- BGP session state changes (ESTABLISHED -> Idle -> ESTABLISHED)
- Route additions and withdrawals
- ECMP path adjustments
- **Error logs** for invalid conditions (if any)
- System handling flapping gracefully

---

### Step 6: Negative Test - Attempt Invalid ECMP Configuration
**Objective**: Verify that invalid ECMP configurations are rejected with proper error messages

#### Step 6.1: Attempt to Configure Invalid Maximum-Paths Value

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Attempt invalid maximum-paths values
configure terminal
router bgp 64512

# Try 0 (invalid)
maximum-paths 0

# Try negative number (invalid)
maximum-paths -1

# Try excessively large number (may be rejected or capped)
maximum-paths 9999

exit
exit
```

**Expected Result**:
- Invalid values (0, negative) should be **rejected**
- Error messages displayed
- Configuration not applied
- Logs show error attempts

#### Step 6.2: Verify Error Logging

**Commands (Execute on DUT)**:
```bash
# Check logs for configuration errors
sonic-cli

show logging | grep -i error | tail -30
show logging | grep -i "maximum-paths" | tail -20
show logging | grep -i invalid | tail -20
```

**Expected Result - Logs Show Errors**:
- Configuration error messages for invalid maximum-paths
- System rejects invalid configuration
- Previous valid configuration remains active
- Clear error indication in logs

---

### Step 7: Verify Loop Prevention
**Objective**: Ensure no routing loops occur in any scenario

#### Step 7.1: Configure Route Tracing

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Ping destination through ECMP paths
ping 192.168.100.1 -c 5

# Traceroute to verify path
traceroute 192.168.100.1

# Check routing table for loop indicators
show ip route 192.168.100.0/24 detail
```

**Expected Result**:
- Ping successful
- Traceroute shows clean path (no loops)
- Each packet may take different ECMP path
- No packets looping back to DUT

#### Step 7.2: Verify TTL and Forwarding

**Commands (Execute on DUT)**:
```bash
# Check interface forwarding counters
sonic-cli

show interface counters Ethernet0
show interface counters Ethernet4
show interface counters Ethernet8

# Verify no excessive retransmissions (loop indicator)
show interface counters errors

# Check routing protocol convergence
show ip protocols
```

**Expected Result**:
- Normal interface counters
- No excessive TX on receive interfaces (no loops)
- No error counters indicating loops
- Routing protocols converged

---

### Step 8: Final Validation - Comprehensive Check
**Objective**: Verify all test objectives met

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify OSPF routes (only equal-cost paths)
show ip route ospf

# Verify BGP routes (only equal AS-PATH length)
show ip route bgp

# Verify maximum-paths configuration
show running-configuration router bgp | grep maximum
show running-configuration router ospf

# Check for any errors in logs
show logging | grep -i error | tail -50

# Verify system stability
show processes
show system memory

# Final route table check
show ip route
```

**Expected Result - Summary**:
1. ✅ **Only equal-cost OSPF paths installed** (different metrics rejected)
2. ✅ **Only equal AS-PATH length BGP paths installed** (different lengths rejected)
3. ✅ **Maximum-paths limit enforced** (excess paths not installed)
4. ✅ **No routing loops** (verified by traceroute and counters)
5. ✅ **Error logs present** for invalid configurations
6. ✅ **System stable** after route flapping

---

## Validation Points

### ECMP Path Qualification Validation (klish mode via sonic-cli)

**Primary Command**: `show ip route ospf`

**Validation Criteria**:

#### 1. Equal-Cost Path Enforcement (OSPF)
- **Different metrics rejected**: Routes with cost 20 not in ECMP with cost 10
- **Only equal-cost paths**: All ECMP paths have same total cost
- **Proper metric calculation**: Route metric reflects equal paths
- **No unequal-cost ECMP**: System enforces equal-cost requirement

#### 2. Equal AS-PATH Length Enforcement (BGP)
- **Different AS-PATH rejected**: Paths with AS-PATH length 2 not in ECMP with length 1
- **Only equal length paths**: All ECMP paths have same AS-PATH length
- **Multipath indicator**: BGP shows "multipath" only for equal paths
- **Path selection correct**: Best path selection follows BGP rules

#### 3. Maximum-Paths Limit Enforcement
- **Limit configured**: maximum-paths setting applied
- **Limit enforced**: Only configured number of paths installed
- **Excess paths rejected**: Additional equal-cost paths not installed
- **Cap working**: System respects configured ECMP limit

#### 4. No Routing Loops
- **Clean traceroute**: No loops detected in path
- **Proper TTL**: Packets not looping
- **Interface counters**: No loop indicators
- **Forwarding correct**: Traffic flows to destination

#### 5. Error Logging
- **Invalid config rejected**: Error messages for invalid maximum-paths
- **Logs show errors**: System logs contain error entries
- **Clear error messages**: Errors are informative
- **Configuration protected**: Invalid values don't corrupt config

#### 6. Route Flapping Handling
- **System stable**: No crashes during flapping
- **Routes converge**: Routes stabilize after flapping stops
- **ECMP reforms**: Equal-cost paths correctly re-established
- **Graceful handling**: System handles rapid changes

---

## Expected Overall Results

### Key Expected Outputs

This test validates four critical aspects:

#### 1. Only Equal-Cost Paths Installed
- **OSPF**: Only paths with equal metrics installed in ECMP
  - Cost 10 + Cost 10 = ECMP ✓
  - Cost 10 + Cost 20 = No ECMP ✗
- **BGP**: Only paths with equal AS-PATH length installed in ECMP
  - AS-PATH length 1 + length 1 = ECMP ✓
  - AS-PATH length 1 + length 2 = No ECMP ✗
- **Metric verification**: All ECMP paths show same cost/metric
- **Path qualification**: Non-equal paths received but not selected

#### 2. No Loops
- **Traceroute clean**: No routing loops detected
- **TTL normal**: Packets forwarded correctly
- **Interface counters**: No loop indicators in statistics
- **Forwarding correct**: Traffic reaches destination
- **Topology valid**: No forwarding loops in any scenario

#### 3. Cap Enforced
- **Maximum-paths respected**: Configured limit enforced
- **Excess paths rejected**: Paths beyond limit not installed
  - maximum-paths 2 + 3 equal paths = only 2 installed ✓
- **Limit working**: System caps ECMP at configured value
- **No overflow**: Cannot exceed maximum-paths limit
- **Configuration effective**: Limit applies to all ECMP routes

#### 4. Logs Show Errors
- **Invalid configuration logged**: Errors for invalid maximum-paths values
- **Configuration rejected**: Invalid values not applied
- **Error messages clear**: Logs provide useful information
- **System protected**: Invalid configs don't cause instability
- **Audit trail**: All configuration attempts logged

### Success Criteria

#### 1. OSPF Unequal Metric Rejection
- Routes from Peer1 (cost 10) and Peer3 (cost 10): **ECMP installed**
- Route from Peer2 (cost 20): **NOT in ECMP** (rejected due to unequal cost)
- Only 2 next-hops in routing table (equal-cost paths only)
- Metric correctly calculated for installed paths

#### 2. BGP Unequal AS-PATH Rejection
- Routes from Peer1 (AS-PATH length 1) and Peer3 (AS-PATH length 1): **ECMP installed**
- Route from Peer2 (AS-PATH length 2): **NOT in ECMP** (rejected due to different length)
- Only 2 next-hops in routing table (equal AS-PATH length only)
- Multipath attribute set correctly

#### 3. ECMP Limit Enforcement
- maximum-paths 2 configured
- 3 equal-cost paths available
- **Only 2 paths installed** in routing table
- Limit correctly enforced
- Excess path in BGP table but not in routing table

#### 4. No Routing Loops
- Traceroute shows clean path (no loops)
- Ping successful to all destinations
- Interface counters normal (no loop indicators)
- No routing loops in any test scenario

#### 5. Route Flapping Stability
- System handles rapid metric/AS-PATH changes
- Routes converge after flapping stops
- ECMP correctly reformed
- No system crashes or instability
- Logs show route changes

#### 6. Error Logging
- Invalid maximum-paths values rejected
- Error messages in logs
- Configuration errors logged
- System remains stable despite invalid input

### Performance Criteria

- **Path selection time**: < 1 second for ECMP formation
- **Convergence after flap**: < 30 seconds to stabilize
- **CPU during flapping**: < 80% peak
- **Memory stable**: No leaks during flapping
- **Log entries**: Errors properly logged

### Failure Indicators

**Test should fail if**:
1. Unequal-cost OSPF paths installed in ECMP
2. Unequal AS-PATH length BGP paths installed in ECMP
3. More paths installed than maximum-paths limit
4. Routing loops detected
5. Invalid configuration accepted without error
6. No error logs for invalid configurations
7. System crashes during route flapping
8. Routes don't converge after flapping
9. ECMP not reformed after stabilization
10. Excessive CPU/memory usage

---

## Test Execution Summary Template

### OSPF Equal-Cost Validation

| Peer | Cost | Metric | In ECMP? | Expected | Result |
|------|------|--------|----------|----------|--------|
| Peer1 | 10 | 20 | Yes | Yes | Pass/Fail |
| Peer2 | 20 | 30 | No | No | Pass/Fail |
| Peer3 | 10 | 20 | Yes | Yes | Pass/Fail |

### BGP AS-PATH Length Validation

| Peer | AS-PATH | Length | In ECMP? | Expected | Result |
|------|---------|--------|----------|----------|--------|
| Peer1 | 65001 | 1 | Yes | Yes | Pass/Fail |
| Peer2 | 65002 65010 | 2 | No | No | Pass/Fail |
| Peer3 | 65003 | 1 | Yes | Yes | Pass/Fail |

### Maximum-Paths Limit Validation

| Setting | Available Paths | Installed Paths | Expected | Result |
|---------|----------------|-----------------|----------|--------|
| maximum-paths 2 | 3 | 2 | 2 | Pass/Fail |
| maximum-paths 3 | 3 | 3 | 3 | Pass/Fail |

### Loop Detection Validation

| Test | Method | Result | Loop Detected? | Status |
|------|--------|--------|----------------|--------|
| OSPF paths | traceroute | Clean | No | Pass/Fail |
| BGP paths | traceroute | Clean | No | Pass/Fail |
| Interface counters | show counters | Normal | No | Pass/Fail |

### Error Logging Validation

| Invalid Config | Rejected? | Error Logged? | Expected | Result |
|---------------|-----------|---------------|----------|--------|
| maximum-paths 0 | Yes | Yes | Yes | Pass/Fail |
| maximum-paths -1 | Yes | Yes | Yes | Pass/Fail |
| maximum-paths 9999 | Yes/Capped | Yes | Yes | Pass/Fail |

### Route Flapping Validation

| Flap Type | Iterations | Converged? | Time | Result |
|-----------|-----------|------------|------|--------|
| OSPF cost change | 4 | Yes | < 30s | Pass/Fail |
| BGP session reset | 3 | Yes | < 60s | Pass/Fail |

---

## Cleanup Steps

After test completion, remove test configurations:

```bash
# On DUT
sonic-cli
configure terminal

# Remove OSPF
no router ospf

# Remove BGP
no router bgp 64512

# Remove interface configurations
interface Ethernet0
no ip address 10.0.0.1/31
no ip ospf cost
exit

interface Ethernet4
no ip address 10.0.4.1/31
no ip ospf cost
exit

interface Ethernet8
no ip address 10.0.8.1/31
no ip ospf cost
exit

exit

# Verify cleanup
show ip route ospf
show ip route bgp
show ip ospf neighbor
show ip bgp summary

exit
```

**Cleanup Verification**:
- OSPF removed
- BGP removed
- No OSPF routes
- No BGP routes
- Interfaces clean

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **Equal-Cost Path Requirements**:
   - **OSPF**: Paths must have identical total metric
   - **BGP**: Paths must have equal AS-PATH length, equal MED, equal LOCAL_PREF
   - **Multipath must be enabled**: OSPF and BGP multipath configuration required

3. **OSPF Cost Calculation**:
   - Total cost = interface cost + advertised cost
   - For ECMP: total cost must be identical
   - Different interface costs result in different total costs
   - Only equal total costs qualify for ECMP

4. **BGP AS-PATH Length**:
   - Length = number of ASNs in AS-PATH
   - AS-PATH prepending increases length
   - Different lengths disqualify from ECMP
   - Only equal lengths qualify for multipath

5. **Maximum-Paths Configuration**:
   - **BGP**: `maximum-paths <1-64>` (typical range)
   - **OSPF**: May have similar configuration
   - Default varies by platform
   - Excess paths not installed even if equal-cost

6. **Route Flapping Detection**:
   - Rapid route changes trigger SPF/best-path recalculation
   - System should handle gracefully
   - Dampening may be configured to reduce churn
   - Logs show each route change

7. **Loop Prevention Mechanisms**:
   - TTL decrement prevents infinite loops
   - Split horizon (if applicable)
   - Proper ECMP hashing (per-flow consistency)
   - Administrative distance prevents protocol loops

8. **Error Logging**:
   - Invalid configuration attempts logged
   - Route changes logged
   - Protocol state changes logged
   - Check `/var/log/syslog` or equivalent

9. **Testing Best Practices**:
   - Test one scenario at a time
   - Clear configurations between tests
   - Verify logs after each operation
   - Monitor CPU/memory during flapping

10. **Common Issues**:
    - **ECMP not forming**: Check equal cost/AS-PATH, multipath enabled
    - **Too many paths**: Check maximum-paths setting
    - **Loops detected**: Verify topology, check for misconfigurations
    - **Flapping continuous**: May need dampening configuration

---

## Additional Validation Commands

For comprehensive testing:

```bash
# OSPF detailed information
show ip ospf
show ip ospf neighbor detail
show ip ospf interface
show ip ospf database
show ip ospf route

# BGP detailed information
show ip bgp
show ip bgp summary
show ip bgp neighbors
show ip bgp <prefix>

# Route table analysis
show ip route
show ip route detail
show ip route summary

# Configuration verification
show running-configuration router ospf
show running-configuration router bgp

# Logging and debugging
show logging | grep ospf
show logging | grep bgp
show logging | grep route
show logging | grep error

# Loop detection
traceroute <destination>
ping <destination> -c 10

# Interface statistics
show interface counters
show interface counters errors
show interface counters rate

# System health
show processes
show system memory
```

---

## Troubleshooting Guide

### Issue: Unequal-Cost Paths in ECMP

**Symptoms**: Different cost paths appear in ECMP

**Check**:
```bash
show ip route ospf
show ip ospf route
show ip ospf database
```

**Resolution**: Verify OSPF costs match, check for misconfigurations

### Issue: Maximum-Paths Not Enforced

**Symptoms**: More paths installed than configured limit

**Check**:
```bash
show running-configuration router bgp | grep maximum
show ip route bgp
```

**Resolution**: Verify maximum-paths configuration, restart routing daemon if needed

### Issue: Routing Loop Detected

**Symptoms**: Traceroute shows loops, high interface counters

**Check**:
```bash
traceroute <destination>
show interface counters
show ip route
```

**Resolution**: Check for misconfigurations, verify topology, check route redistribution

### Issue: No Error Logs

**Symptoms**: Invalid config accepted or no logs

**Check**:
```bash
show logging
show logging | grep error
```

**Resolution**: Check logging level, verify syslog configuration

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_4node_ecmp_limits.yaml`
- **Test ID**: TC_ECMP_2.4.8
- **Test Category**: ECMP - Path Qualification and Limits
- **Priority**: High
- **Automation**: Recommended
- **Related Test Cases**:
  - TC_ECMP_2.4.1 (Basic ECMP)
  - TC_ECMP_2.4.4 (OSPF ECMP)
  - TC_ECMP_2.4.4 (Large-scale BGP ECMP)
- **Related Standards**:
  - RFC 2328 (OSPF Version 2)
  - RFC 4271 (BGP-4)
  - RFC 2992 (Analysis of ECMP Algorithms)
  - RFC 7908 (OSPF Multi-Instance)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 2.4.8 - Only equal-cost paths qualify; reject invalid; cap limits
