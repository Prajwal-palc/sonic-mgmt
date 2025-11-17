# Test Cases - Interface Events Validation (Latency Under Load)

## Test Case ID: TC_INTF_EVENTS_004

### Test Case Name
Measure Detection/Recovery Latency Under Load

### Test Objective
Validate interface failure detection and recovery latency under continuous traffic load conditions. Measure control-plane reconvergence time for OSPF neighbor relationships when link flaps and administrative state changes occur. Ensure that reconvergence time meets target thresholds while continuous traffic is being generated.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Device Under Test (DUT1)**: smic_sonic1 (192.168.100.193)
- **Peer Device (DUT2)**: smic_sonic2 (192.168.100.195)
- **Traffic Generator**: TG (Traffic Generator port connected to testbed)
- **Test Interfaces**:
  - Ethernet0 (DUT1 <-> DUT2 link for OSPF)
  - Ethernet4 (DUT1 <-> DUT2 link for OSPF)
  - TG ports for traffic generation
- **Topology**: 2 nodes (smic_sonic1 <-> smic_sonic2) + TG
- **Routing Protocol**: OSPF (Open Shortest Path First)

### Prerequisites
1. Both devices (smic_sonic1 and smic_sonic2) must be accessible via SSH
2. User credentials: admin/YourPaSsWoRd
3. Access to sonic-cli and klish shell
4. Sufficient privileges to configure interfaces and OSPF
5. Traffic Generator (TG) must be connected and operational
6. OSPF must be configured and neighbors established between DUT1 and DUT2
7. Network timing/latency measurement tools available
8. Baseline traffic flow established

---

## Test Procedure

### Step 1: Initial Configuration - Bring All Interfaces to UP State
**Objective**: Ensure all interfaces in the testbed are in operational "up" state

**Commands (Execute on both DUT1 and DUT2)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Bring up Ethernet0
interface Ethernet0
no shutdown
exit

# Bring up Ethernet4
interface Ethernet4
no shutdown
exit

# Exit configuration mode
exit
```

**Expected Result**:
- All interfaces (Ethernet0, Ethernet4) should show administrative state as "up"
- Operational state should transition to "up"
- No errors during interface activation

---

### Step 2: Configure OSPF on Both Devices
**Objective**: Establish OSPF neighbor relationship between DUT1 and DUT2

**Commands (Execute on both DUT1 and DUT2)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure OSPF router ID and process
router ospf
router-id <device-specific-router-id>
exit

# Configure OSPF on Ethernet0
interface Ethernet0
ip ospf network point-to-point
ip ospf area 0.0.0.0
exit

# Configure OSPF on Ethernet4
interface Ethernet4
ip ospf network point-to-point
ip ospf area 0.0.0.0
exit

# Exit configuration mode
exit
```

**Expected Result**:
- OSPF configuration should be applied successfully
- No configuration errors
- OSPF process should be running

**Note**:
- For DUT1 (smic_sonic1): Use router-id 1.1.1.1 (example)
- For DUT2 (smic_sonic2): Use router-id 2.2.2.2 (example)
- Configure IP addresses on interfaces before OSPF configuration

---

### Step 3: Verify OSPF Neighbor Establishment
**Objective**: Confirm OSPF neighbors are established before testing

**Commands (Execute on both devices)**:
```bash
# Enter sonic-cli
sonic-cli

# Check OSPF neighbor status
show ip ospf neighbor

# Check interface status
show interface status
```

**Expected Result**:
- OSPF neighbors should be in "Full" state
- Neighbor adjacency should be established on both Ethernet0 and Ethernet4
- All interfaces should show admin and oper status as "up"

**Sample Output Format**:
```
Neighbor ID     Pri   State      Dead Time   Address         Interface
-------------------------------------------------------------------------
2.2.2.2         1     Full/DR    00:00:35    <neighbor-ip>   Ethernet0
2.2.2.2         1     Full/DR    00:00:38    <neighbor-ip>   Ethernet4
```

---

### Step 4: Configure and Start Continuous Traffic Generation
**Objective**: Generate continuous traffic through the DUT devices to simulate production load

**TG Configuration**:
1. Configure traffic streams from TG to traverse through DUT1 -> DUT2
2. Traffic parameters:
   - Frame size: 64 bytes, 512 bytes, 1518 bytes (mixed)
   - Traffic rate: Line rate or configurable percentage (e.g., 50% line rate)
   - Traffic pattern: Continuous bidirectional traffic
   - Protocol: IPv4/IPv6 packets
   - Duration: Continuous (throughout test execution)

**Commands (TG specific)**:
```bash
# Configure traffic stream
# Start continuous traffic generation
# Monitor traffic statistics
```

**Expected Result**:
- Traffic should be flowing continuously through both devices
- Packet loss should be minimal (< 0.01%) under normal conditions
- Traffic counters should be incrementing on both DUT devices

**Verification on DUTs**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface counters to verify traffic flow
show interface counters

# Check specific interface statistics
show interface Ethernet0 counters
show interface Ethernet4 counters
```

---

### Step 5: Baseline Measurement - Record Initial State
**Objective**: Capture baseline measurements before triggering events

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Record current OSPF neighbor state
show ip ospf neighbor

# Record interface status
show interface status

# Record timestamp
# Note: Record system time for baseline
```

**Expected Result**:
- All OSPF neighbors in "Full" state
- All interfaces operational
- Traffic flowing without issues
- Baseline timestamp recorded

**Metrics to Record**:
1. OSPF neighbor establishment time (already established)
2. Interface up time
3. Traffic throughput and packet loss
4. Control-plane CPU utilization

---

### Step 6: Test Iteration 1 - Interface Administrative Shutdown/No Shutdown
**Objective**: Measure recovery latency when interface is administratively shut down and brought back up under load

#### 6.1: Record Pre-Event Timestamp
**Commands**:
```bash
# Record timestamp before shutdown
# T1 = Current system time
```

#### 6.2: Trigger Administrative Shutdown
**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Shutdown Ethernet0
interface Ethernet0
shutdown
exit

# Record timestamp immediately after shutdown
# T2 = Shutdown command execution time

# Exit configuration mode
exit
```

**Expected Immediate Result**:
- Ethernet0 admin state: down
- Ethernet0 oper state: down
- OSPF neighbor on Ethernet0 should start timing out

#### 6.3: Monitor OSPF Neighbor State During Shutdown
**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Check OSPF neighbor status (execute multiple times)
show ip ospf neighbor

# Check interface status
show interface status

# Record timestamp when OSPF neighbor is detected as down
# T3 = OSPF neighbor down detection time
```

**Expected Result**:
- OSPF neighbor adjacency on Ethernet0 should transition to "Down" state
- OSPF should detect neighbor loss
- Traffic should failover to alternate path (Ethernet4) if available

**Detection Latency Calculation**:
```
Detection Latency = T3 - T2
Expected: Within OSPF dead interval (typically 40 seconds for default settings)
Target: < 1 second for fast convergence (if fast-hello configured)
```

#### 6.4: Trigger Administrative No Shutdown (Recovery)
**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Bring up Ethernet0
interface Ethernet0
no shutdown
exit

# Record timestamp immediately after no shutdown
# T4 = No shutdown command execution time

# Exit configuration mode
exit
```

#### 6.5: Monitor OSPF Neighbor Recovery
**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Check OSPF neighbor status (execute multiple times)
show ip ospf neighbor

# Check interface status
show interface status

# Record timestamp when OSPF neighbor returns to "Full" state
# T5 = OSPF neighbor full state re-establishment time
```

**Expected Result**:
- Interface Ethernet0 should transition to admin=up, oper=up
- OSPF neighbor adjacency should be re-established
- OSPF neighbor should transition through: Down -> Init -> ExStart -> Exchange -> Loading -> Full
- Traffic should resume on Ethernet0

**Recovery Latency Calculation**:
```
Recovery Latency = T5 - T4
Expected: OSPF neighbor re-establishment time (typically 10-40 seconds)
Target: < 10 seconds for optimized configurations
```

**Total Reconvergence Time**:
```
Total Reconvergence = T5 - T2
This includes: Shutdown -> Detection -> Recovery -> Full adjacency
```

---

### Step 7: Test Iteration 2 - Link Flap Simulation
**Objective**: Measure recovery latency when physical link flap occurs under load

**Note**: Link flap can be simulated by rapid shutdown/no shutdown sequence or by physically disconnecting/reconnecting cable (if possible in virtual environment, use shutdown sequence)

#### 7.1: Simulate Link Flap
**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Record timestamp before link flap
# T6 = Pre-flap timestamp

# Simulate link flap (rapid shutdown and no shutdown)
interface Ethernet4
shutdown
# Wait 1-2 seconds
no shutdown
exit

# Record timestamp after link flap
# T7 = Post-flap timestamp

# Exit configuration mode
exit
```

#### 7.2: Monitor Link Flap Recovery
**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status

# Check OSPF neighbor status (execute multiple times)
show ip ospf neighbor

# Record timestamp when OSPF neighbor returns to "Full" state
# T8 = OSPF neighbor full state after flap
```

**Expected Result**:
- Interface should transition: up -> down -> up
- OSPF neighbor may or may not go down depending on flap duration and OSPF timers
- If OSPF neighbor goes down, it should recover to "Full" state
- Traffic should experience minimal interruption

**Link Flap Recovery Calculation**:
```
Link Flap Recovery = T8 - T6
Expected: Faster than full shutdown/startup sequence
Target: < 5 seconds for fast reconvergence
```

---

### Step 8: Test Iteration 3 - Simultaneous Link Flap on Multiple Interfaces
**Objective**: Measure recovery latency when multiple links flap simultaneously under load

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Record timestamp before multiple link flaps
# T9 = Pre-multi-flap timestamp

# Shutdown both interfaces simultaneously
interface Ethernet0
shutdown
exit

interface Ethernet4
shutdown
exit

# Wait 2-3 seconds

# Bring both interfaces back up
interface Ethernet0
no shutdown
exit

interface Ethernet4
no shutdown
exit

# Record timestamp after recovery commands
# T10 = Post-multi-flap recovery timestamp

# Exit configuration mode
exit
```

**Commands (Monitor)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status

# Check OSPF neighbor status
show ip ospf neighbor

# Record timestamp when all OSPF neighbors return to "Full" state
# T11 = All neighbors full state timestamp
```

**Expected Result**:
- All interfaces should go down and come back up
- All OSPF neighbors should recover to "Full" state
- Control-plane should handle multiple simultaneous events
- Traffic should resume once links and OSPF recover

**Multi-Link Recovery Calculation**:
```
Multi-Link Recovery = T11 - T9
Expected: Slightly longer than single link recovery
Target: < 15 seconds for complete recovery
```

---

### Step 9: Test Iteration 4 - Repeated Shutdown/No Shutdown Cycles
**Objective**: Validate consistency of latency measurements across multiple iterations

**Commands (Execute on DUT1)**:
```bash
# Repeat the shutdown/no shutdown cycle 5 times
# For each iteration:
#   1. Record pre-shutdown timestamp
#   2. Execute shutdown on Ethernet0
#   3. Monitor OSPF neighbor down detection
#   4. Execute no shutdown on Ethernet0
#   5. Monitor OSPF neighbor recovery to Full state
#   6. Record recovery timestamp
#   7. Calculate detection and recovery latency
#   8. Wait 30 seconds for stabilization before next iteration
```

**Expected Result**:
- Latency measurements should be consistent across iterations
- Standard deviation of latency measurements should be minimal
- No degradation in performance over iterations
- No memory leaks or resource exhaustion

---

## Validation Points

### CLI Validation (klish mode via sonic-cli)

**Primary Commands**:
1. `show interface status` - Verify interface state transitions
2. `show ip ospf neighbor` - Verify OSPF neighbor state and reconvergence

**Validation Criteria**:

#### 1. Interface Status Validation
- **Command**: `show interface status`
- **Checks**:
  - Admin state reflects configuration (up/down)
  - Oper state reflects actual link state
  - State transitions occur within expected timeframes
  - Interface counters increment during traffic flow

#### 2. OSPF Neighbor Validation
- **Command**: `show ip ospf neighbor`
- **Checks**:
  - Neighbor state transitions: Full -> Down (on failure)
  - Neighbor state transitions: Down -> Init -> ExStart -> Exchange -> Loading -> Full (on recovery)
  - Neighbor ID correctly displayed
  - Dead time resets properly after recovery
  - All expected neighbors present after recovery

### Latency Threshold Validation

**Target Thresholds** (example values, adjust based on requirements):

| Event Type | Detection Latency | Recovery Latency | Total Reconvergence | Status |
|------------|-------------------|------------------|---------------------|--------|
| Admin Shutdown | < 1 second | < 10 seconds | < 15 seconds | Pass/Fail |
| Admin No Shutdown | N/A | < 10 seconds | < 10 seconds | Pass/Fail |
| Link Flap | < 1 second | < 5 seconds | < 10 seconds | Pass/Fail |
| Multi-Link Flap | < 2 seconds | < 15 seconds | < 20 seconds | Pass/Fail |

**Notes**:
- Detection latency: Time from event to control-plane detection (OSPF neighbor down)
- Recovery latency: Time from recovery action to full OSPF adjacency
- Total reconvergence: End-to-end time from failure to full recovery

### Traffic Impact Validation

**Metrics to Monitor**:
1. **Packet Loss**:
   - During failure: Expected (traffic blackhole until failover)
   - During recovery: Minimal (< 100 packets lost)
   - After recovery: Zero packet loss

2. **Traffic Failover**:
   - Traffic should failover to alternate path if available
   - Failover time should be within target threshold

3. **Throughput**:
   - Throughput should return to baseline after recovery
   - No permanent degradation

---

## Expected Overall Results

### Success Criteria
1. **Interface State Transitions**:
   - All interfaces can be brought to "up" state successfully
   - Shutdown/no shutdown commands execute without errors
   - Interface states are accurately reflected in CLI output

2. **OSPF Neighbor Convergence**:
   - OSPF neighbors establish successfully during initial setup
   - OSPF neighbors detect failures within target threshold
   - OSPF neighbors recover to "Full" state within target threshold
   - No OSPF neighbor flapping or instability

3. **Latency Measurements**:
   - Detection latency within target threshold (< 1 second)
   - Recovery latency within target threshold (< 10 seconds)
   - Total reconvergence within target threshold (< 15 seconds)
   - Consistent measurements across multiple iterations

4. **Traffic Continuity**:
   - Continuous traffic flow maintained during testing
   - Traffic failover occurs during link failures (if alternate path exists)
   - Traffic resumes after recovery with minimal packet loss
   - No traffic blackholes after recovery

5. **System Stability**:
   - No crashes, errors, or unexpected behavior
   - Control-plane CPU within acceptable limits
   - No memory leaks or resource exhaustion
   - Logs contain accurate event records

### Performance Criteria
- Interface state transitions: < 2 seconds
- OSPF neighbor detection of failure: < 1 second (with optimized timers)
- OSPF neighbor recovery to Full state: < 10 seconds
- Traffic failover time: < 1 second (if alternate path configured)
- CLI command response time: < 5 seconds
- Consistent performance across 5+ iterations

---

## Test Execution Summary Template

### Iteration 1: Admin Shutdown/No Shutdown

| Metric | Timestamp | Value | Threshold | Status |
|--------|-----------|-------|-----------|--------|
| Pre-shutdown | T1 | - | - | - |
| Shutdown executed | T2 | - | - | - |
| OSPF neighbor down detected | T3 | - | - | - |
| Detection latency | T3-T2 | X seconds | < 1 second | Pass/Fail |
| No shutdown executed | T4 | - | - | - |
| OSPF neighbor Full state | T5 | - | - | - |
| Recovery latency | T5-T4 | Y seconds | < 10 seconds | Pass/Fail |
| Total reconvergence | T5-T2 | Z seconds | < 15 seconds | Pass/Fail |

### Iteration 2: Link Flap

| Metric | Timestamp | Value | Threshold | Status |
|--------|-----------|-------|-----------|--------|
| Pre-flap | T6 | - | - | - |
| Link flap executed | T7 | - | - | - |
| OSPF neighbor Full state | T8 | - | - | - |
| Link flap recovery | T8-T6 | X seconds | < 5 seconds | Pass/Fail |

### Iteration 3: Multi-Link Flap

| Metric | Timestamp | Value | Threshold | Status |
|--------|-----------|-------|-----------|--------|
| Pre-multi-flap | T9 | - | - | - |
| Multi-flap executed | T10 | - | - | - |
| All neighbors Full state | T11 | - | - | - |
| Multi-link recovery | T11-T9 | X seconds | < 15 seconds | Pass/Fail |

### Traffic Impact Summary

| Event Type | Packet Loss | Traffic Failover Time | Throughput After Recovery | Status |
|------------|-------------|----------------------|---------------------------|--------|
| Admin Shutdown | X packets | Y seconds | Z% of baseline | Pass/Fail |
| Link Flap | X packets | Y seconds | Z% of baseline | Pass/Fail |
| Multi-Link Flap | X packets | Y seconds | Z% of baseline | Pass/Fail |

---

## Cleanup Steps

After test completion, ensure proper cleanup:

```bash
# Stop traffic generation on TG
# Stop all traffic streams

# Enter sonic-cli on both DUT1 and DUT2
sonic-cli

# Enter configuration mode
configure terminal

# Ensure all interfaces are in up state
interface Ethernet0
no shutdown
exit

interface Ethernet4
no shutdown
exit

# Exit configuration mode
exit

# Verify final state
show interface status
show ip ospf neighbor

# Exit sonic-cli
exit
```

**Cleanup Verification**:
- All interfaces should be in admin=up, oper=up state
- All OSPF neighbors should be in "Full" state
- No residual configuration or state issues
- Traffic stopped on TG

**Optional**: Remove OSPF configuration if required:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Remove OSPF from interfaces
interface Ethernet0
no ip ospf area 0.0.0.0
no ip ospf network point-to-point
exit

interface Ethernet4
no ip ospf area 0.0.0.0
no ip ospf network point-to-point
exit

# Remove OSPF router configuration
no router ospf

# Exit configuration mode
exit
```

---

## Test Environment Details

**Command Flow Reference**:
```
1. sonic-cli                           # Enter CLI (klish mode)
2. configure terminal                  # Enter config mode
3. interface Ethernet<num>             # Select interface
4. shutdown / no shutdown              # Trigger state change
5. exit                                # Exit interface config
6. show interface status               # Verify interface state
7. show ip ospf neighbor               # Verify OSPF neighbor state
8. Record timestamps                   # Measure latency
9. Calculate latency metrics           # Detection, recovery, reconvergence
```

**Topology Diagram**:
```
    +-------+                +-------+
    |  TG   |                |  TG   |
    +---+---+                +---+---+
        |                        |
        |                        |
   +----+----+              +----+----+
   |  DUT1   |<--Ethernet0->|  DUT2   |
   | (sonic1)|              | (sonic2)|
   |         |<--Ethernet4->|         |
   +---------+              +---------+

   OSPF configured on Ethernet0 and Ethernet4
   Continuous traffic from TG through DUT1 <-> DUT2
```

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **OSPF Timer Optimization** (Optional for faster convergence):
   ```bash
   # Configure OSPF fast hellos for faster detection
   interface Ethernet0
   ip ospf dead-interval minimal hello-multiplier 3
   exit
   ```
   - Default dead interval: 40 seconds
   - Default hello interval: 10 seconds
   - Fast hello can reduce detection to < 1 second

3. **Timestamp Recording**:
   - Use high-resolution timers (millisecond accuracy)
   - Record timestamps immediately before and after events
   - Consider clock synchronization between devices (NTP)

4. **Traffic Generator Configuration**:
   - Ensure traffic is bidirectional
   - Use multiple traffic streams for realistic load
   - Monitor traffic statistics continuously
   - Configure traffic to allow failover testing

5. **Latency Measurement Tools**:
   - System clock: `date +%s.%N` (nanosecond precision)
   - OSPF debug logs: May contain transition timestamps
   - Interface event logs: Check syslog for event timestamps

6. **Considerations for Virtual Environment**:
   - Virtual links may have different behavior than physical links
   - Link flap simulation may differ from physical cable disconnect
   - CPU resource contention may affect timing measurements

7. **Document all observations**:
   - Record exact timestamps for all events
   - Capture CLI outputs for each step
   - Note any anomalies or unexpected behavior
   - Save logs for post-test analysis

8. **Repeat measurements for statistical significance**:
   - Perform at least 5 iterations per test type
   - Calculate average, min, max, and standard deviation
   - Identify outliers and investigate root causes

---

## Additional Validation Commands

For comprehensive testing and troubleshooting:

```bash
# OSPF detailed information
show ip ospf interface
show ip ospf interface Ethernet0
show ip ospf database

# Interface detailed statistics
show interface Ethernet0
show interface Ethernet0 counters
show interface Ethernet0 description

# System logs for events
show logging | grep OSPF
show logging | grep Ethernet

# Running configuration
show running-configuration interface Ethernet0
show running-configuration | grep ospf

# System resource monitoring
show processes cpu
show processes memory

# Routing table verification
show ip route
show ip route ospf
```

---

## Troubleshooting

### Common Issues and Resolution

**Issue 1**: OSPF neighbors not establishing
- **Cause**: Interface IP configuration missing, OSPF area mismatch, or authentication failure
- **Resolution**:
  - Verify IP addressing: `show ip interface brief`
  - Verify OSPF configuration: `show running-configuration | grep ospf`
  - Check OSPF logs: `show logging | grep OSPF`

**Issue 2**: Recovery latency exceeds threshold
- **Cause**: Default OSPF timers too conservative, CPU overload, or control-plane issues
- **Resolution**:
  - Optimize OSPF timers (fast hello, reduced dead interval)
  - Check CPU utilization: `show processes cpu`
  - Reduce background load if necessary

**Issue 3**: Traffic not failing over during link failure
- **Cause**: No alternate path configured, routing table not updated, or TG configuration issue
- **Resolution**:
  - Verify alternate paths exist: `show ip route`
  - Check TG routing configuration
  - Verify both links are in OSPF: `show ip ospf interface`

**Issue 4**: Inconsistent latency measurements
- **Cause**: Background processes, control-plane load, or timing measurement errors
- **Resolution**:
  - Ensure baseline system state before each iteration
  - Wait for stabilization between iterations (30-60 seconds)
  - Use multiple measurement points for averaging

**Issue 5**: Interface doesn't come up after no shutdown
- **Cause**: Link layer issues, peer interface down, or configuration errors
- **Resolution**:
  - Verify peer interface is up: Check on DUT2
  - Check interface errors: `show interface Ethernet0`
  - Verify cabling and physical connectivity (if applicable)

---

## Performance Benchmarks

### Expected Latency Ranges

**Detection Latency** (Time to detect failure):
- With default OSPF timers (40s dead interval): 30-40 seconds
- With fast hello (3x hello in 1s): < 1 second
- With BFD integration: < 100 milliseconds

**Recovery Latency** (Time from recovery action to full adjacency):
- OSPF neighbor establishment: 5-10 seconds
- With pre-convergence optimization: 2-5 seconds

**Total Reconvergence** (End-to-end failure to recovery):
- With default timers: 40-50 seconds
- With optimized timers: 5-15 seconds
- With BFD and optimization: 1-5 seconds

### Traffic Impact Benchmarks

**Packet Loss During Events**:
- Link failure (no alternate path): All packets lost until recovery
- Link failure (with alternate path): < 100 packets lost during failover
- Link recovery: < 50 packets lost during reconvergence

**Traffic Failover Time**:
- With alternate path available: < 1 second
- OSPF reconvergence: Depends on OSPF timers (see above)

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Test ID**: 1.3.4
- **Test Category**: Interface Events - Latency Under Load
- **Priority**: High
- **Automation**: Candidate for automation framework
- **Related Test Cases**:
  - TC_INTF_EVENTS_001 (Admin/Link State Changes)
  - TC_INTF_EVENTS_002 (LAG/ECMP Propagation)
  - TC_INTF_EVENTS_003 (Bulk Event Processing)
- **Related RFCs**:
  - RFC 2328: OSPF Version 2
  - RFC 5340: OSPF for IPv6
  - RFC 5880: Bidirectional Forwarding Detection (BFD)

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Interface Commands**:
```bash
show interface status                # Display all interface status
show interface status Ethernet<num>  # Display specific interface status
show interface Ethernet<num>         # Display detailed interface info
show interface counters              # Display interface traffic counters
show interface Ethernet<num> counters # Display specific interface counters
```

**OSPF Commands**:
```bash
show ip ospf neighbor                # Display OSPF neighbor status
show ip ospf neighbor detail         # Display detailed neighbor information
show ip ospf interface               # Display OSPF interface configuration
show ip ospf interface Ethernet<num> # Display specific interface OSPF info
show ip ospf database                # Display OSPF link-state database
show ip route ospf                   # Display OSPF routes in routing table
```

**System and Logging Commands**:
```bash
show logging                         # Display system logs
show logging | grep OSPF             # Filter OSPF-related logs
show logging | grep Ethernet         # Filter interface-related logs
show processes cpu                   # Display CPU utilization
show processes memory                # Display memory utilization
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**Interface Configuration**:
```bash
configure terminal                   # Enter configuration mode
interface Ethernet<num>              # Enter interface configuration
shutdown                             # Administratively disable interface
no shutdown                          # Administratively enable interface
exit                                 # Exit interface configuration
```

**OSPF Configuration**:
```bash
router ospf                          # Enter OSPF configuration mode
router-id <router-id>                # Configure OSPF router ID
exit                                 # Exit OSPF configuration

interface Ethernet<num>              # Enter interface configuration
ip ospf area <area-id>               # Assign interface to OSPF area
ip ospf network point-to-point       # Configure OSPF network type
ip ospf dead-interval <seconds>      # Configure OSPF dead interval
ip ospf hello-interval <seconds>     # Configure OSPF hello interval
ip ospf dead-interval minimal hello-multiplier <multiplier>  # Fast hello
exit                                 # Exit interface configuration
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.3.4 - Measure detection/recovery latency under load
