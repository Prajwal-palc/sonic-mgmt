# Test Cases - Reject Invalid ECMP and Maintain Stability

## Test Case ID: TC_ECMP_2.4.3

### Test Case Name
Reject Invalid ECMP Configurations and Maintain System Stability

### Test Objective
Validate that the system correctly rejects invalid ECMP configurations (duplicate next-hops, unreachable next-hops), maintains traffic forwarding via valid paths when invalid configurations are attempted, handles next-hop deletion during active traffic without complete service disruption, supports recovery when paths are re-added, and enforces the maximum supported next-hop limit (e.g., 64 NH). Verify that invalid inputs are rejected, traffic continues via remaining valid paths, and the next-hop capacity limit is enforced.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_3node_ecmp.yaml`
- **Topology**: 3 nodes (1 DUT + 2 neighbors)
- **Device Under Test (DUT)**: Primary router under test
- **Neighbors**: Neighbor1, Neighbor2
- **Test Network**: Static routing with ECMP configuration

### Topology Diagram

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
                            |
                       Source Network
                      192.168.10.0/24
```

### Interface Configuration

**DUT Interfaces**:
- **Ethernet0**: Connected to Neighbor1 (10.0.1.0/30, IP: 10.0.1.1)
- **Ethernet4**: Connected to Neighbor2 (10.0.2.0/30, IP: 10.0.2.1)
- **Loopback0**: 1.1.1.1/32 (Router ID)

**Neighbor1 Configuration**:
- Interface to DUT: 10.0.1.0/30, IP: 10.0.1.2
- Destination network: 200.0.0.0/24

**Neighbor2 Configuration**:
- Interface to DUT: 10.0.2.0/30, IP: 10.0.2.2
- Destination network: 200.0.0.0/24

### Prerequisites
1. All 3 devices accessible via SSH
2. SONiC OS installed on all devices
3. Access to sonic-cli (klish) on all devices
4. All interfaces physically connected
5. Sufficient routing table capacity
6. Traffic generation tools available (iperf3, ping, or Scapy)

---

## Test Procedure

### Step 1: Initial Setup - Configure DUT Interfaces
**Objective**: Configure IP addresses on all DUT interfaces

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0 (to Neighbor1)
interface Ethernet0
ip address 10.0.1.1/30
no shutdown
exit

# Configure Ethernet4 (to Neighbor2)
interface Ethernet4
ip address 10.0.2.1/30
no shutdown
exit

# Configure Loopback0 (Router ID)
interface Loopback0
ip address 1.1.1.1/32
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify interface status
show interface status Ethernet0
show interface status Ethernet4

# Verify IP addresses
show ip interface
```

**Expected Result**:
- All interfaces configured with IP addresses
- All interfaces operational (up/up)
- No configuration errors

---

### Step 2: Configure Neighbor Interfaces
**Objective**: Configure IP addresses on neighbor devices

**Commands (Execute on Neighbor1)**:
```bash
# Enter sonic-cli
sonic-cli

configure terminal

# Configure interface to DUT
interface Ethernet0
ip address 10.0.1.2/30
no shutdown
exit

# Configure loopback for destination network simulation
interface Loopback0
ip address 200.0.0.1/32
exit

exit
```

**Commands (Execute on Neighbor2)**:
```bash
# Enter sonic-cli
sonic-cli

configure terminal

# Configure interface to DUT
interface Ethernet0
ip address 10.0.2.2/30
no shutdown
exit

# Configure loopback for destination network simulation
interface Loopback0
ip address 200.0.0.2/32
exit

exit
```

**Expected Result**:
- Neighbor interfaces configured
- Connectivity to DUT established

---

### Step 3: Baseline - Configure Valid ECMP Static Routes
**Objective**: Configure valid ECMP routes to establish baseline

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Add static route with 2 equal-cost next-hops
ip route 200.0.0.0/24 10.0.1.2
ip route 200.0.0.0/24 10.0.2.2

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify route installation
show ip route 200.0.0.0/24

# Show all static routes
show ip route static

# Verify ECMP configuration
show ip route
```

**Expected Result**:
- Route to 200.0.0.0/24 present
- **Two next-hops** listed (ECMP)
- Next-hops: 10.0.1.2 (Ethernet0), 10.0.2.2 (Ethernet4)
- Both next-hops active

**Sample Output**:
```
S    200.0.0.0/24 [1/0]
       via 10.0.1.2, Ethernet0, weight 1, 00:00:15
       via 10.0.2.2, Ethernet4, weight 1, 00:00:15
```

---

### Step 4: Test Case 1 - Reject Duplicate Next-Hop
**Objective**: Verify system rejects duplicate next-hop configuration

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to add duplicate next-hop (10.0.1.2 already exists)
ip route 200.0.0.0/24 10.0.1.2

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify route still has only 2 unique next-hops
show ip route 200.0.0.0/24

# Count next-hops in the route
show ip route static

# Check for any warnings/errors
show logging | grep -i "route\|duplicate\|error" | tail -20
```

**Expected Result**:
- System rejects or ignores duplicate next-hop
- Route still has exactly **2 unique next-hops** (not 3)
- No duplicate entries in next-hop list
- Warning or error logged (if applicable)
- Existing ECMP configuration intact

**Validation Points**:
1. Next-hop count remains 2 (not increased to 3)
2. No duplicate 10.0.1.2 entries
3. Traffic forwarding unaffected
4. System remains stable

---

### Step 5: Test Case 2 - Reject Unreachable Next-Hop
**Objective**: Verify system rejects unreachable next-hop configuration

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to add unreachable next-hop (not in connected subnet)
ip route 200.0.0.0/24 192.168.99.99

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify route configuration
show ip route 200.0.0.0/24

# Check route installation status
show ip route static

# Verify only reachable next-hops are active
show ip route 200.0.0.0/24 detail

# Check ARP table (unreachable next-hop should not have ARP entry)
show arp
```

**Expected Result**:
- Unreachable next-hop **not installed** in active routing table
- OR unreachable next-hop shown as inactive/unresolved
- Only 2 reachable next-hops active (10.0.1.2, 10.0.2.2)
- Traffic continues via valid paths
- No traffic blackholing

**Sample Output**:
```
S    200.0.0.0/24 [1/0]
       via 10.0.1.2, Ethernet0, weight 1, 00:02:30
       via 10.0.2.2, Ethernet4, weight 1, 00:02:30
     * via 192.168.99.99, inactive (unresolvable)
```

**Validation Points**:
1. Active next-hop count = 2 (reachable paths only)
2. Unreachable next-hop not used for forwarding
3. Traffic forwarding unaffected
4. No packet loss to destination

---

### Step 6: Test Case 3 - Delete Next-Hop During Traffic
**Objective**: Verify traffic continues on remaining path when one next-hop is deleted

**Step 6.1: Start Traffic Generation**

**Commands (Generate continuous traffic)**:
```bash
# On traffic generator (or DUT loopback)
# Generate continuous ping traffic
ping 200.0.0.1 -i 0.2 -c 100 &

# OR use iperf3 for TCP traffic
# On Neighbor1: iperf3 -s
# On DUT: iperf3 -c 200.0.0.1 -t 60 &
```

**Step 6.2: Monitor Initial Traffic Distribution**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Monitor interface counters before deletion
show interface counters Ethernet0
show interface counters Ethernet4

# Record baseline counters
```

**Step 6.3: Delete One Next-Hop During Traffic**

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Remove one next-hop (Neighbor1)
no ip route 200.0.0.0/24 10.0.1.2

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Immediately verify route updated
show ip route 200.0.0.0/24

# Verify only one next-hop remains
show ip route static

# Check interface counters
show interface counters Ethernet0
show interface counters Ethernet4
```

**Expected Result**:
- Route immediately updated to single next-hop
- Traffic continues via remaining path (10.0.2.2)
- **Minimal packet loss** during transition (< 5 packets)
- No complete service disruption
- All traffic now forwarded via Ethernet4

**Sample Output After Deletion**:
```
S    200.0.0.0/24 [1/0]
       via 10.0.2.2, Ethernet4, weight 1, 00:00:03
```

**Step 6.4: Analyze Traffic Impact**

**Commands**:
```bash
# Check ping statistics (if using ping)
# Expected: 95%+ success rate

# Verify all traffic now on Ethernet4
show interface counters Ethernet4

# Verify Ethernet0 no longer forwarding to destination
show interface counters Ethernet0
```

**Validation Points**:
1. Route updated within 1 second
2. Packet loss < 5% during transition
3. Traffic continues without manual intervention
4. All traffic now on single path (Ethernet4)
5. System remains stable

---

### Step 7: Test Case 4 - Re-Add Next-Hop and Verify Recovery
**Objective**: Verify ECMP recovery when deleted next-hop is re-added

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Re-add the deleted next-hop
ip route 200.0.0.0/24 10.0.1.2

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify route restored to 2 next-hops
show ip route 200.0.0.0/24

# Verify ECMP restored
show ip route static

# Verify both paths active
show ip route 200.0.0.0/24 detail
```

**Expected Result**:
- Route immediately updated to 2 next-hops
- ECMP restored (load balancing across both paths)
- Traffic distribution returns to balanced state
- Smooth recovery without disruption

**Sample Output After Re-Add**:
```
S    200.0.0.0/24 [1/0]
       via 10.0.1.2, Ethernet0, weight 1, 00:00:05
       via 10.0.2.2, Ethernet4, weight 1, 00:03:47
```

**Step 7.1: Verify Load Distribution Recovery**

**Commands**:
```bash
# Clear interface counters
sonic-cli -c "clear counters"

# Generate new traffic
ping 200.0.0.1 -c 1000 -i 0.01

# Check distribution
sonic-cli
show interface counters Ethernet0
show interface counters Ethernet4
```

**Expected Result**:
- Traffic distributed across both paths
- Each path carries ~50% of traffic
- Load balancing restored

**Validation Points**:
1. Next-hop count restored to 2
2. Both next-hops active
3. Load distribution balanced (~50%/50%)
4. No configuration errors
5. ECMP fully functional

---

### Step 8: Test Case 5 - Exceed Maximum Next-Hop Limit
**Objective**: Verify system enforces maximum next-hop limit (e.g., 64 NH)

**Step 8.1: Identify Maximum Next-Hop Limit**

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Check system capabilities
show platform capabilities | grep -i ecmp

# Check maximum ECMP paths supported
show ip ecmp

# Or check documentation/release notes for max NH limit
```

**Note**: Maximum next-hop limit varies by platform:
- Common limits: 32, 64, 128 next-hops
- For this test, assume limit is **64 next-hops**

**Step 8.2: Prepare Test with Multiple Next-Hops**

**Configuration Strategy**:
- Create loopback interfaces to simulate multiple next-hops
- Add static routes with increasing next-hop count
- Monitor when system enforces limit

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Clear previous test routes
no ip route 200.0.0.0/24 10.0.1.2
no ip route 200.0.0.0/24 10.0.2.2

# Create test route with incremental next-hops
# For testing, use multiple IP aliases on Ethernet interfaces
# Or configure static routes with many next-hops

# Example: Configure up to the limit (e.g., 64 next-hops)
# This requires careful setup with multiple interfaces or IP aliases

# For practical testing, configure routes approaching the limit
# Example with 10 next-hops (simplified):
ip route 200.0.0.0/24 10.0.1.2
ip route 200.0.0.0/24 10.0.1.3
ip route 200.0.0.0/24 10.0.1.4
# ... continue up to platform limit

# Attempt to exceed limit (add 65th next-hop if limit is 64)
# ip route 200.0.0.0/24 10.0.1.66

exit
```

**Alternative Approach - Automated Script**:
```python
#!/usr/bin/env python3
"""
Test maximum ECMP next-hop limit
Configures routes up to and beyond the platform limit
"""

def configure_max_nexthops(dut, limit=64):
    """Configure routes up to the maximum next-hop limit"""

    # Configure base next-hops
    for i in range(2, limit + 2):
        cmd = f"sonic-cli -c 'configure terminal; ip route 200.0.0.0/24 10.0.1.{i}; exit'"
        # Execute command

    # Attempt to exceed limit
    cmd = f"sonic-cli -c 'configure terminal; ip route 200.0.0.0/24 10.0.1.{limit + 2}; exit'"
    # Execute and check for error

# Note: This requires multiple IP addresses configured on interfaces
```

**Step 8.3: Verify Limit Enforcement**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify route configuration
show ip route 200.0.0.0/24

# Count next-hops
show ip route static | grep "via" | wc -l

# Check for warnings/errors about exceeding limit
show logging | grep -i "ecmp\|limit\|next-hop\|maximum" | tail -30

# Verify system enforced the cap
show ip route 200.0.0.0/24 detail
```

**Expected Result**:
- System accepts next-hops up to the platform limit (e.g., 64)
- Next-hops beyond the limit are **rejected** or **ignored**
- Warning/error message indicating limit exceeded
- Active next-hop count = platform maximum (e.g., 64)
- System remains stable
- No crash or hang

**Sample Output**:
```
S    200.0.0.0/24 [1/0]
       via 10.0.1.2, Ethernet0, weight 1, 00:00:15
       via 10.0.1.3, Ethernet0, weight 1, 00:00:15
       ... (total 64 next-hops)

Warning: Maximum ECMP next-hop limit (64) reached for route 200.0.0.0/24
```

**Validation Points**:
1. Active next-hop count ≤ platform maximum
2. System rejects attempts to exceed limit
3. Appropriate error/warning message
4. Existing next-hops remain functional
5. No system instability
6. Traffic forwarding continues on valid paths

---

### Step 9: Test Case 6 - Invalid Next-Hop During Traffic
**Objective**: Verify traffic stability when invalid next-hop is added during active traffic

**Step 9.1: Reset to Baseline Configuration**

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Remove all test routes
no ip route 200.0.0.0/24

# Reconfigure baseline ECMP
ip route 200.0.0.0/24 10.0.1.2
ip route 200.0.0.0/24 10.0.2.2

exit
```

**Step 9.2: Start Continuous Traffic**

**Commands**:
```bash
# Generate continuous traffic
ping 200.0.0.1 -i 0.1 &

# Monitor baseline traffic
sonic-cli
show interface counters Ethernet0
show interface counters Ethernet4
```

**Step 9.3: Attempt to Add Invalid Next-Hop During Traffic**

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to add unreachable next-hop during traffic
ip route 200.0.0.0/24 192.168.99.99

# Attempt to add duplicate next-hop during traffic
ip route 200.0.0.0/24 10.0.1.2

exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify route remains stable
show ip route 200.0.0.0/24

# Verify only valid next-hops active
show ip route static

# Check traffic statistics (should show continuous operation)
# ping output should show no interruption

# Verify interface counters still incrementing
show interface counters Ethernet0
show interface counters Ethernet4
```

**Expected Result**:
- Invalid configurations rejected
- Traffic continues uninterrupted
- No packet loss during invalid configuration attempt
- Active next-hops remain 2 (valid paths only)
- System stability maintained

**Validation Points**:
1. Zero packet loss during invalid config attempts
2. Next-hop count remains 2
3. No traffic disruption
4. System responsive to CLI commands
5. No crashes or hangs

---

### Step 10: Comprehensive Validation - System Stability
**Objective**: Verify overall system stability after all invalid configuration attempts

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify final route configuration
show ip route 200.0.0.0/24

# Verify all static routes
show ip route static

# Check interface status
show interface status

# Verify no errors or warnings
show logging | grep -i "error\|warning\|critical" | tail -50

# Check system resources (CPU, memory)
show processes
show system memory

# Verify routing table integrity
show ip route summary

# Check for any routing inconsistencies
show ip route
```

**Expected Result**:
- Route configuration clean and valid
- Only reachable, unique next-hops in routing table
- All interfaces operational
- No critical errors in logs
- System resources normal (CPU < 50%, Memory < 80%)
- Routing table consistent
- System responsive

**Validation Points**:
1. Route count correct
2. Next-hop count within limits
3. All next-hops reachable and unique
4. No system errors
5. Normal resource utilization
6. System stable and responsive

---

### Step 11: Traffic Validation - End-to-End Connectivity
**Objective**: Verify end-to-end traffic forwarding after all tests

**Commands**:
```bash
# Test connectivity with ping
ping 200.0.0.1 -c 100

# Test with different traffic patterns
ping 200.0.0.1 -c 1000 -i 0.01 -s 1400

# Verify load distribution
sonic-cli

# Clear counters
clear counters

# Exit and generate traffic
exit
ping 200.0.0.1 -c 1000 -f

# Check final distribution
sonic-cli
show interface counters Ethernet0
show interface counters Ethernet4
```

**Expected Result**:
- 100% packet delivery (0% loss)
- Load balanced across valid paths (~50%/50%)
- No routing blackholes
- Consistent forwarding behavior

---

## Validation Points

### Invalid ECMP Configuration Rejection (klish mode via sonic-cli)

**Primary Commands**:
- `show ip route 200.0.0.0/24`
- `show ip route static`
- `show logging`

**Validation Criteria**:

#### 1. Duplicate Next-Hop Rejection
- **Duplicate rejected**: System does not add duplicate next-hop
- **Next-hop count**: Remains at original count (not increased)
- **Unique next-hops**: Each next-hop appears only once
- **No impact**: Existing ECMP configuration unchanged

#### 2. Unreachable Next-Hop Handling
- **Unreachable not active**: Unreachable next-hop not installed or marked inactive
- **Reachable only**: Only reachable next-hops active in forwarding table
- **No blackholing**: Traffic not sent to unreachable next-hop
- **Traffic continues**: Forwarding via valid paths unaffected

#### 3. Next-Hop Deletion During Traffic
- **Immediate update**: Route updated within 1 second
- **Minimal loss**: Packet loss < 5% during transition
- **Continued forwarding**: Traffic continues via remaining paths
- **No disruption**: No complete service outage

#### 4. Next-Hop Re-Addition Recovery
- **ECMP restored**: Next-hop count restored to original
- **Load balancing**: Traffic distributed across all paths
- **Smooth recovery**: No disruption during re-addition
- **Automatic**: Recovery without manual intervention

#### 5. Maximum Next-Hop Limit Enforcement
- **Limit enforced**: System caps next-hops at platform maximum
- **Excess rejected**: Next-hops beyond limit rejected
- **Warning issued**: Appropriate error/warning message
- **Stability maintained**: System remains stable at limit

#### 6. Traffic Stability
- **No interruption**: Traffic continues during invalid config attempts
- **Zero packet loss**: No loss during rejection of invalid configs
- **Load distribution**: Balanced across valid paths
- **End-to-end connectivity**: 100% reachability

---

## Expected Overall Results

### Success Criteria

#### 1. Duplicate Next-Hop Rejection
- System rejects or ignores duplicate next-hop configurations
- Next-hop count remains accurate (no duplicate entries)
- Existing ECMP configuration remains intact
- No system instability

#### 2. Unreachable Next-Hop Handling
- Unreachable next-hops not used for active forwarding
- Traffic forwarded only via reachable paths
- No traffic blackholing or loss
- System marks unreachable next-hops as inactive

#### 3. Next-Hop Deletion During Traffic
- Route updated immediately (< 1 second)
- Packet loss minimal (< 5 packets or < 5%)
- Traffic continues via remaining paths automatically
- No manual intervention required
- System remains stable

#### 4. Next-Hop Recovery
- Deleted next-hop successfully re-added
- ECMP load balancing restored
- Smooth transition without disruption
- Load distribution balanced across all paths

#### 5. Maximum Next-Hop Limit
- Platform limit enforced (e.g., 64 next-hops)
- Attempts to exceed limit rejected
- Appropriate warning/error message displayed
- System remains stable at maximum capacity
- No crash or hang when limit reached

#### 6. Overall System Stability
- System responsive throughout all tests
- No crashes, hangs, or reboots
- CPU and memory utilization normal
- No routing table corruption
- End-to-end connectivity maintained

### Performance Criteria

- **Route Update Time**: < 1 second
- **Packet Loss During NH Deletion**: < 5%
- **Recovery Time**: < 2 seconds
- **System CPU**: < 50% during tests
- **System Memory**: < 80% during tests
- **CLI Responsiveness**: All commands execute within 3 seconds

### Failure Indicators

**Test should fail if**:
1. Duplicate next-hops accepted and installed
2. Unreachable next-hops used for active forwarding (blackholing)
3. Packet loss > 10% during next-hop deletion
4. Complete traffic disruption during next-hop changes
5. Failed next-hop cannot be re-added
6. System accepts more next-hops than platform limit
7. System crash, hang, or reboot during tests
8. Routing table corruption
9. End-to-end connectivity loss
10. CLI becomes unresponsive

---

## Test Execution Summary Template

### Invalid Configuration Rejection

| Test Case | Configuration Attempted | Accepted/Rejected | Next-Hop Count | Result |
|-----------|------------------------|-------------------|----------------|--------|
| Duplicate NH | Add 10.0.1.2 (duplicate) | Rejected | 2 (unchanged) | Pass/Fail |
| Unreachable NH | Add 192.168.99.99 | Rejected/Inactive | 2 (active) | Pass/Fail |
| Exceed limit | Add 65th NH (limit 64) | Rejected | 64 (max) | Pass/Fail |

### Traffic Continuity During Changes

| Event | Packet Loss | Downtime | Traffic Recovery | Result |
|-------|-------------|----------|------------------|--------|
| Delete NH during traffic | < 5% | < 1 sec | Immediate | Pass/Fail |
| Add invalid NH during traffic | 0% | 0 sec | N/A | Pass/Fail |
| Re-add NH | < 1% | < 1 sec | Immediate | Pass/Fail |

### System Stability

| Metric | Threshold | Actual | Result |
|--------|-----------|--------|--------|
| CPU Usage | < 50% | ___% | Pass/Fail |
| Memory Usage | < 80% | ___% | Pass/Fail |
| CLI Responsiveness | < 3 sec/command | ___ sec | Pass/Fail |
| System Crashes | 0 | ___ | Pass/Fail |
| Route Table Corruption | No | Yes/No | Pass/Fail |

### Load Distribution After Recovery

| Path | Interface | Next-Hop | Packets | Percentage | Result |
|------|-----------|----------|---------|------------|--------|
| 1 | Ethernet0 | 10.0.1.2 | ~500 | ~50% | Pass/Fail |
| 2 | Ethernet4 | 10.0.2.2 | ~500 | ~50% | Pass/Fail |

---

## Cleanup Steps

After test completion, remove test configuration:

```bash
# Enter sonic-cli on DUT
sonic-cli

# Enter configuration mode
configure terminal

# Remove static routes
no ip route 200.0.0.0/24

# Remove IP addresses from interfaces (optional)
interface Ethernet0
no ip address 10.0.1.1/30
exit

interface Ethernet4
no ip address 10.0.2.1/30
exit

# Exit configuration mode
exit

# Verify cleanup
show ip route static
show ip route

# Exit sonic-cli
exit
```

**Cleanup Verification**:
- No static routes present
- Interfaces in clean state (or retain IPs if needed for other tests)
- Routing table clean

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **Maximum Next-Hop Limit**:
   - Varies by platform and hardware
   - Common limits: 32, 64, 128 next-hops per route
   - Consult platform documentation for exact limit
   - ECMP width may be limited by ASIC capabilities

3. **Duplicate Next-Hop Handling**:
   - Some systems silently ignore duplicates
   - Others may log warnings
   - End result: Only one instance of each next-hop active

4. **Unreachable Next-Hop Behavior**:
   - May be accepted in configuration but marked inactive
   - OR rejected immediately if next-hop resolution fails
   - Should never be used for active forwarding

5. **Traffic Loss Expectations**:
   - Modern systems: < 1 second downtime during route updates
   - Packet loss depends on traffic rate and route convergence
   - Acceptable loss: < 5% during topology changes

6. **Next-Hop Resolution**:
   - Next-hops must be directly connected or recursively resolvable
   - ARP/ND must resolve next-hop MAC address
   - Unresolved next-hops not installed in hardware forwarding table

7. **Testing Maximum Limit**:
   - Practical testing limited by interface availability
   - May require loopback interfaces or IP aliases
   - Can use connected routes or recursive next-hops
   - Ensure sufficient hardware resources

8. **Load Balancing Hash**:
   - Uses packet 5-tuple (src IP, dst IP, src port, dst port, protocol)
   - Per-flow consistency (same flow always same path)
   - Different flows distribute across paths

9. **Platform Considerations**:
   - ECMP support varies by hardware platform
   - Some platforms support weighted ECMP
   - Maximum next-hop limit enforced by ASIC
   - Software may have different limit than hardware

10. **Troubleshooting**:
    - If duplicates accepted: Check software version, may be bug
    - If unreachable NH active: Verify next-hop resolution status
    - If limit not enforced: Check platform capabilities
    - If traffic loss excessive: Check route convergence, hardware FIB programming

---

## Additional Validation Commands

For comprehensive testing and troubleshooting (klish mode via sonic-cli):

```bash
# Route verification
show ip route
show ip route static
show ip route 200.0.0.0/24
show ip route 200.0.0.0/24 detail
show ip route summary

# Next-hop verification
show ip next-hop
show arp

# Interface verification
show interface status
show interface counters
show interface counters Ethernet0
show interface counters Ethernet4
show interface counters rate

# System health
show processes
show system memory
show system cpu
show logging
show logging | grep -i route
show logging | grep -i error

# ECMP capabilities
show platform capabilities
show ip ecmp
```

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Route Validation Commands**:
```bash
show ip route                          # Display entire routing table
show ip route static                   # Display static routes only
show ip route 200.0.0.0/24             # Display specific route
show ip route 200.0.0.0/24 detail      # Detailed route information
show ip route summary                  # Route table summary
```

**Next-Hop Validation Commands**:
```bash
show ip next-hop                       # Display next-hop table
show arp                               # Display ARP table (next-hop resolution)
```

**Interface Commands**:
```bash
show interface status                  # Display interface status
show interface counters                # Display interface packet counters
show interface counters Ethernet0      # Counters for specific interface
show interface counters rate           # Display counter rates
clear counters                         # Clear interface counters
```

**System Health Commands**:
```bash
show processes                         # Display processes and resource usage
show system memory                     # Display memory utilization
show system cpu                        # Display CPU utilization
show logging                           # Display system logs
```

**Platform Capabilities**:
```bash
show platform capabilities             # Display platform capabilities
show ip ecmp                           # Display ECMP configuration and limits
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**Static Route Configuration**:
```bash
configure terminal                     # Enter configuration mode
ip route 200.0.0.0/24 10.0.1.2         # Add static route with next-hop
no ip route 200.0.0.0/24 10.0.1.2      # Remove static route with next-hop
no ip route 200.0.0.0/24               # Remove all routes to destination
exit                                   # Exit configuration mode
```

**Interface Configuration**:
```bash
interface Ethernet0                    # Enter interface configuration
ip address 10.0.1.1/30                 # Configure IP address
no ip address 10.0.1.1/30              # Remove IP address
no shutdown                            # Enable interface
shutdown                               # Disable interface
exit                                   # Exit interface configuration
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-18
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 2.4.3 - Reject invalid ECMP and maintain stability
