# Test Cases - Interface Events Validation (Continuous LAG Flapping)

## Test Case ID: TC_INTF_EVENTS_006

### Test Case Name
Validate CLI/Syslog for Admin/Link State Changes with Continuous LAG Interface Flapping

### Test Objective
Validate that continuous LAG (PortChannel) interface administrative state changes (shutdown/no shutdown) and member interface state changes are accurately reflected in CLI outputs and system logs. Ensure that rapid and repeated state transitions on both the PortChannel and its member interfaces are properly captured, logged, and displayed without loss of events or system instability. Verify that routing table updates correctly reflect PortChannel state changes.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Device Under Test (DUT1)**: smic_sonic1 (192.168.100.193)
- **Peer Device (DUT2)**: smic_sonic2 (192.168.100.195)
- **Test PortChannel**: PortChannel10
- **Member Interfaces**:
  - Ethernet0 (Primary member)
  - Ethernet4 (Secondary member)
- **Connection**:
  - smic_sonic1:Ethernet0 <---> smic_sonic2:Ethernet0
  - smic_sonic1:Ethernet4 <---> smic_sonic2:Ethernet4
- **Topology**: 2 nodes

### Prerequisites
1. Both devices (smic_sonic1 and smic_sonic2) must be accessible via SSH
2. User credentials: admin/YourPaSsWoRd
3. Access to sonic-cli and klish shell
4. Sufficient privileges to configure interfaces and PortChannels
5. System logging enabled and functional
6. No existing PortChannel10 configuration on devices
7. LACP support enabled (if using LACP mode)
8. Sufficient system resources to handle rapid state transitions

---

## Test Procedure

### Step 1: Initial Configuration - Bring Member Interfaces to UP State
**Objective**: Ensure all member interfaces are in operational "up" state before LAG configuration

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
- Ethernet0 and Ethernet4 should show administrative state as "up"
- Operational state should transition to "up"
- No errors during interface activation

---

### Step 2: Create and Configure PortChannel
**Objective**: Create PortChannel10 and add member interfaces

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Create PortChannel10
interface PortChannel10
no shutdown
exit

# Add Ethernet0 to PortChannel10
interface Ethernet0
channel-group 10 mode active
exit

# Add Ethernet4 to PortChannel10
interface Ethernet4
channel-group 10 mode active
exit

# Exit configuration mode
exit
```

**Expected Result**:
- PortChannel10 created successfully
- Ethernet0 and Ethernet4 added as members
- PortChannel10 shows admin state as "up"
- Member interfaces show association with PortChannel10

**Note**: Repeat on DUT2 for LAG to be fully operational

---

### Step 3: Configure IP Address on PortChannel (Optional)
**Objective**: Configure IP addressing on PortChannel for routing validation

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure IP on PortChannel10
interface PortChannel10
ip address 10.0.10.1/24
exit

# Exit configuration mode
exit
```

**Expected Result**:
- IP address configured successfully on PortChannel10
- IP route should appear in routing table

**Note**: Configure corresponding IP on DUT2 (e.g., 10.0.10.2/24)

---

### Step 4: Baseline Status Check
**Objective**: Capture baseline status before flapping tests

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status

# Check PortChannel status
show interface portchannel

# Check PortChannel details
show interface portchannel 10

# Check IP routes
show ip route

# Check syslog
show logging | grep PortChannel
```

**Expected Result**:
- All interfaces show admin=up, oper=up
- PortChannel10 shows admin=up, oper=up
- PortChannel10 shows both members (Ethernet0, Ethernet4) as active
- IP route for PortChannel10 subnet present
- Baseline logs captured

**Sample Output Format**:
```
# show interface portchannel
Interface        Admin    Oper    Members                Protocol
--------------------------------------------------------------------
PortChannel10    up       up      Ethernet0(S),Ethernet4(S)   LACP

# show ip route
Destination      Gateway          Interface        Protocol
------------------------------------------------------------
10.0.10.0/24     0.0.0.0          PortChannel10    connected
```

---

### Step 5: Single PortChannel Shutdown Test
**Objective**: Verify PortChannel shutdown is properly reflected in CLI and affects routing

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Shutdown PortChannel10
interface PortChannel10
shutdown
exit

# Exit configuration mode
exit

# Verify PortChannel status
show interface portchannel 10

# Check interface status
show interface status | grep PortChannel10

# Check IP routes
show ip route

# Check syslog
show logging | grep PortChannel10
```

**Expected Result**:
- PortChannel10 shows:
  - Admin Status: down
  - Oper Status: down
- Member interfaces remain configured but PortChannel is down
- IP route via PortChannel10 should be removed or marked as unreachable
- Syslog contains PortChannel down event
- State transition should be immediate

**Validation Points**:
1. CLI accurately reflects PortChannel admin state = down
2. CLI accurately reflects PortChannel oper state = down
3. Routing table updated (route removed or marked down)
4. Syslog contains PortChannel shutdown event
5. Member interfaces remain in their current state

---

### Step 6: Single PortChannel No Shutdown Test (Recovery)
**Objective**: Verify PortChannel recovery is properly reflected in CLI and routing

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Bring up PortChannel10
interface PortChannel10
no shutdown
exit

# Exit configuration mode
exit

# Verify PortChannel status
show interface portchannel 10

# Check interface status
show interface status | grep PortChannel10

# Check IP routes
show ip route

# Check syslog
show logging | grep PortChannel10
```

**Expected Result**:
- PortChannel10 shows:
  - Admin Status: up
  - Oper Status: up (if members are up)
- Member interfaces resume active participation
- IP route via PortChannel10 restored
- Syslog contains PortChannel up event
- State transition should be successful

**Validation Points**:
1. CLI accurately reflects PortChannel admin state = up
2. CLI accurately reflects PortChannel oper state = up
3. Routing table updated (route restored)
4. Syslog contains PortChannel up event
5. Members show as active/selected

---

### Step 7: Member Interface Shutdown Test
**Objective**: Verify that shutting down a member interface affects PortChannel status

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Shutdown Ethernet0 (member of PortChannel10)
interface Ethernet0
shutdown
exit

# Exit configuration mode
exit

# Verify PortChannel status
show interface portchannel 10

# Check interface status
show interface status

# Check IP routes
show ip route

# Check syslog
show logging | grep -E "PortChannel10|Ethernet0"
```

**Expected Result**:
- Ethernet0 shows admin=down, oper=down
- PortChannel10 status depends on configuration:
  - If min-links not configured: PortChannel10 remains up with one member (Ethernet4)
  - Member list shows Ethernet0 as inactive/down
  - Ethernet4 continues to carry traffic
- IP route via PortChannel10 should remain (traffic uses remaining member)
- Syslog contains events for both Ethernet0 down and PortChannel member change

**Validation Points**:
1. Member interface state change reflected in PortChannel status
2. PortChannel remains operational with remaining member(s)
3. Routing continues via PortChannel (degraded mode)
4. Logs capture both member and PortChannel events

---

### Step 8: Member Interface No Shutdown Test (Recovery)
**Objective**: Verify that bringing up a member interface restores full PortChannel functionality

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

# Exit configuration mode
exit

# Verify PortChannel status
show interface portchannel 10

# Check interface status
show interface status

# Check syslog
show logging | grep -E "PortChannel10|Ethernet0"
```

**Expected Result**:
- Ethernet0 shows admin=up, oper=up
- PortChannel10 shows both members active
- Full redundancy restored
- Syslog contains events for Ethernet0 up and PortChannel member restoration

**Validation Points**:
1. Member interface recovery reflected in PortChannel status
2. PortChannel shows all members active
3. Full LAG functionality restored
4. Logs capture recovery events

---

### Step 9: Continuous PortChannel Flapping - Iteration 1 (10 Cycles)
**Objective**: Validate system behavior during continuous PortChannel shutdown/no shutdown cycles

**Test Procedure**:
Perform 10 rapid PortChannel shutdown/no shutdown cycles

**Commands (Execute on DUT1)**:
```bash
# For each cycle (repeat 10 times):

# Cycle N:
sonic-cli
configure terminal
interface PortChannel10
shutdown
exit
exit

# Verify shutdown state
show interface portchannel 10
show ip route

# Bring PortChannel back up
configure terminal
interface PortChannel10
no shutdown
exit
exit

# Verify up state
show interface portchannel 10
show ip route

# Brief stabilization pause (1-2 seconds)
```

**Expected Result**:
- Each shutdown operation results in:
  - PortChannel10: Admin=down, Oper=down
  - IP route removed/unreachable
  - CLI output accurate

- Each no shutdown operation results in:
  - PortChannel10: Admin=up, Oper=up
  - IP route restored
  - CLI output accurate

- System handles all 10 cycles without:
  - PortChannel state inconsistencies
  - CLI command failures
  - Member interface issues
  - Routing table corruption

**Validation After 10 Cycles**:
```bash
# Check final state
sonic-cli
show interface portchannel 10
show interface status
show ip route
show logging | grep PortChannel10
```

**Expected Validation**:
1. Final PortChannel state = up
2. Both members active
3. IP route present
4. Syslog contains entries for all 20 state transitions (10 down, 10 up)
5. No error messages

---

### Step 10: Continuous Member Interface Flapping - Iteration 1 (10 Cycles)
**Objective**: Validate system behavior during continuous member interface flapping

**Test Procedure**:
Perform 10 rapid shutdown/no shutdown cycles on Ethernet0 (member interface)

**Commands (Execute on DUT1)**:
```bash
# For each cycle (repeat 10 times):

# Cycle N:
sonic-cli
configure terminal
interface Ethernet0
shutdown
exit
exit

# Verify PortChannel status
show interface portchannel 10

# Bring interface back up
configure terminal
interface Ethernet0
no shutdown
exit
exit

# Verify PortChannel status
show interface portchannel 10

# Brief stabilization pause (1-2 seconds)
```

**Expected Result**:
- Each shutdown operation:
  - Ethernet0: Admin=down, Oper=down
  - PortChannel10 continues with Ethernet4 only
  - PortChannel remains operationally up (degraded)

- Each no shutdown operation:
  - Ethernet0: Admin=up, Oper=up
  - PortChannel10 shows both members active
  - Full redundancy restored

**Validation After 10 Cycles**:
1. Final state: both members active in PortChannel
2. PortChannel operational with all members
3. Syslog contains member state change events
4. No PortChannel instability

---

### Step 11: Continuous PortChannel Flapping - Iteration 2 (25 Cycles)
**Objective**: Validate system stability during extended PortChannel flapping

**Test Procedure**:
Perform 25 rapid PortChannel shutdown/no shutdown cycles

**Expected Result**:
- System remains stable throughout all 25 cycles
- CLI continues to respond accurately
- Routing table updates correctly each cycle
- No degradation in response time

**Validation After 25 Cycles**:
1. Final PortChannel state = up
2. All members active
3. IP route present and correct
4. Syslog contains entries for all 50 state transitions
5. No system resource exhaustion

---

### Step 12: Continuous PortChannel Flapping - Iteration 3 (50 Cycles)
**Objective**: Validate system behavior under sustained PortChannel flapping

**Test Procedure**:
Perform 50 rapid PortChannel shutdown/no shutdown cycles

**Expected Result**:
- System handles sustained PortChannel flapping
- CLI commands continue to execute normally
- Routing updates remain accurate
- No memory leaks or resource exhaustion

**Validation After 50 Cycles**:
1. Final PortChannel state = up
2. Routing table correct
3. System CPU and memory within acceptable limits
4. No performance degradation

---

### Step 13: Mixed Flapping Test (PortChannel + Member Interfaces)
**Objective**: Test simultaneous flapping of PortChannel and member interfaces

**Test Procedure**:
Perform mixed flapping operations (10 cycles):
- Cycle 1-3: Flap PortChannel10
- Cycle 4-6: Flap Ethernet0 (member)
- Cycle 7-9: Flap Ethernet4 (member)
- Cycle 10: Flap PortChannel10

**Expected Result**:
- System handles mixed flapping scenarios
- PortChannel state correctly reflects member states
- Routing remains consistent
- No state confusion or corruption

**Validation**:
1. Final state: PortChannel up with all members active
2. All state transitions logged correctly
3. Routing table accurate
4. No system errors

---

### Step 14: Simultaneous Member Shutdown Test
**Objective**: Test behavior when all members are shut down simultaneously

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Shutdown both members
interface Ethernet0
shutdown
exit

interface Ethernet4
shutdown
exit

# Exit configuration mode
exit

# Verify PortChannel status
show interface portchannel 10
show ip route
```

**Expected Result**:
- Both member interfaces down
- PortChannel10 oper status should go down (no active members)
- IP route removed or marked unreachable
- Syslog contains events for all changes

**Recovery**:
```bash
# Bring both members back up
configure terminal
interface Ethernet0
no shutdown
exit
interface Ethernet4
no shutdown
exit
exit

# Verify recovery
show interface portchannel 10
show ip route
```

**Validation**:
1. PortChannel goes down when all members are down
2. PortChannel recovers when members come back up
3. Routing updated correctly
4. All events logged

---

### Step 15: Rapid PortChannel Flapping Stress Test
**Objective**: Test system behavior during rapid PortChannel flapping with minimal delay

**Test Procedure**:
Perform rapid PortChannel shutdown/no shutdown cycles with minimal delay (10 cycles)

**Commands (Execute on DUT1)**:
```bash
# Rapid flapping without stabilization delay
# For each cycle:

sonic-cli
configure terminal
interface PortChannel10
shutdown
no shutdown
exit
exit

# Verify final state
show interface portchannel 10
show ip route
```

**Expected Result**:
- System handles rapid PortChannel commands
- Final PortChannel state deterministic (up)
- Routing table converges to correct state
- No command queue overflows

**Validation**:
1. PortChannel reaches stable "up" state
2. All members active
3. Routing correct
4. No CLI errors or timeouts

---

### Step 16: Final State Verification
**Objective**: Verify system is in clean state after all LAG flapping tests

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify PortChannel status
show interface portchannel

# Check specific PortChannel
show interface portchannel 10

# Verify interface status
show interface status

# Check routing table
show ip route

# Verify no error conditions
show logging | grep -i error | tail -20

# Check system resources
show processes cpu
show processes memory
```

**Expected Result**:
- PortChannel10 is in "up" state (admin and oper)
- All member interfaces active in PortChannel
- IP routes correct and stable
- No residual error conditions
- System resources at normal levels
- All CLI commands responsive

---

## Validation Points

### CLI Validation (klish mode via sonic-cli)

**Primary Commands**:
1. `show interface status` - Verify interface and PortChannel state
2. `show interface portchannel` - Verify PortChannel status and members
3. `show ip route` - Verify routing table updates

**Validation Criteria**:

#### 1. PortChannel State Reflection
- **After PortChannel shutdown**:
  - Admin state = down
  - Oper state = down
  - Change reflected immediately (within 1-2 seconds)

- **After PortChannel no shutdown**:
  - Admin state = up
  - Oper state = up (if members are up)
  - Change reflected immediately (within 1-2 seconds)

#### 2. Member Interface Impact
- **After member shutdown**:
  - Member shows as inactive/down in PortChannel
  - PortChannel remains up if other members are active
  - Member count decreases

- **After member no shutdown**:
  - Member shows as active in PortChannel
  - Member count increases
  - Full redundancy restored

#### 3. Routing Table Updates
- **After PortChannel shutdown**:
  - Routes via PortChannel removed or marked unreachable
  - Routing convergence within seconds

- **After PortChannel recovery**:
  - Routes via PortChannel restored
  - Routing correct and stable

#### 4. State Consistency During Flapping
- CLI output always reflects current PortChannel state
- Member status accurately displayed
- No stale or cached information
- State transitions occur in correct sequence

#### 5. CLI Responsiveness
- Commands execute within normal timeframes
- No degradation during flapping
- No command failures or timeouts
- No CLI hang or freeze conditions

### Syslog Validation (When feature is available)

**Validation Criteria**:

#### 1. PortChannel Event Completeness
- Each PortChannel shutdown logged
- Each PortChannel no shutdown logged
- Member state changes logged
- All events in chronological order

#### 2. Event Accuracy
- Log entries match actual state transitions
- PortChannel and member events clearly identified
- Timestamps correspond to command execution
- State change direction accurate (up/down)

#### 3. Routing Event Logging
- Route additions/deletions logged (if configured)
- Routing protocol updates logged
- Convergence events recorded

---

## Expected Overall Results

### Success Criteria

#### 1. CLI Accuracy
- All show commands accurately reflect PortChannel state at all times
- Member interface status correctly displayed in PortChannel output
- State transitions are immediate and correct
- CLI remains responsive throughout all test iterations
- No CLI errors, hangs, or crashes

#### 2. State Transition Correctness
- PortChannel shutdown → Admin: down, Oper: down (100% of cycles)
- PortChannel no shutdown → Admin: up, Oper: up (100% of cycles)
- Member shutdown → Member inactive, PortChannel degraded
- Member no shutdown → Member active, PortChannel full redundancy
- No incorrect or intermediate states
- No state transition failures

#### 3. Routing Table Accuracy
- Routes via PortChannel added when PortChannel is up
- Routes removed when PortChannel is down
- Routing updates complete within convergence time
- No stale routes or routing loops
- Routing table consistency maintained

#### 4. System Stability
- System handles continuous PortChannel flapping without crashes
- System handles member interface flapping without issues
- No resource exhaustion (CPU, memory, disk)
- All services remain operational
- System recovers to normal state after flapping stops

#### 5. LAG Protocol Integrity
- LACP (if used) continues to function correctly
- Member selection/deselection works properly
- No protocol state machine corruption
- Load balancing resumes after recovery

#### 6. Logging Accuracy (if available)
- All PortChannel state transitions logged
- All member state changes logged
- Routing events logged
- Log entries accurate and complete
- No missing events or log loss

### Performance Criteria

- **CLI Response Time**: < 5 seconds throughout testing
- **PortChannel State Transition Time**: < 2 seconds per transition
- **Member State Transition Time**: < 2 seconds per transition
- **Routing Convergence Time**: < 5 seconds after PortChannel state change
- **System CPU Usage**: Should not exceed 80% during flapping
- **System Memory Usage**: No memory leaks; usage should stabilize
- **LACP Convergence**: < 30 seconds for member selection (if LACP used)

### Failure Indicators

**Test should fail if**:
1. CLI shows incorrect PortChannel state
2. Member interface status not reflected in PortChannel
3. PortChannel state becomes stuck or inconsistent
4. Routing table not updated correctly
5. CLI commands fail or timeout
6. System crashes or becomes unresponsive
7. LACP protocol fails or corrupts
8. Routes persist when PortChannel is down
9. Critical system resources exhausted
10. Multiple consecutive command failures (3+ failures)

---

## Test Execution Summary Template

### PortChannel Configuration Verification

| Component | Status | Members | IP Address | Route Present | Result |
|-----------|--------|---------|------------|---------------|--------|
| PortChannel10 Initial | up/down | Ethernet0,4 | 10.0.10.1/24 | Yes/No | Pass/Fail |

### Single Cycle Verification

| Operation | PortChannel Admin | PortChannel Oper | Members Active | Route Present | Syslog Entry | Result |
|-----------|-------------------|------------------|----------------|---------------|--------------|--------|
| Baseline | up | up | 2 | Yes | - | Pass/Fail |
| PC Shutdown | down | down | N/A | No | Yes/No | Pass/Fail |
| PC No Shutdown | up | up | 2 | Yes | Yes/No | Pass/Fail |
| Member Shutdown | up | up | 1 | Yes | Yes/No | Pass/Fail |
| Member No Shutdown | up | up | 2 | Yes | Yes/No | Pass/Fail |

### Continuous PortChannel Flapping Summary

| Iteration | Cycles | Total Transitions | CLI Accurate | Routing Correct | System Stable | Result |
|-----------|--------|-------------------|--------------|-----------------|---------------|--------|
| 1 (PC) | 10 | 20 | Yes/No | Yes/No | Yes/No | Pass/Fail |
| 2 (PC) | 25 | 50 | Yes/No | Yes/No | Yes/No | Pass/Fail |
| 3 (PC) | 50 | 100 | Yes/No | Yes/No | Yes/No | Pass/Fail |
| 1 (Member) | 10 | 20 | Yes/No | Yes/No | Yes/No | Pass/Fail |
| Mixed | 10 | 20 | Yes/No | Yes/No | Yes/No | Pass/Fail |
| Stress | 10 (rapid) | 20 | Yes/No | Yes/No | Yes/No | Pass/Fail |

### System Resource Monitoring

| Metric | Baseline | After 10 Cycles | After 25 Cycles | After 50 Cycles | Status |
|--------|----------|-----------------|-----------------|-----------------|--------|
| CPU Usage (%) | X% | X% | X% | X% | Normal/High |
| Memory Usage (%) | X% | X% | X% | X% | Normal/High |
| CLI Response (sec) | X | X | X | X | Normal/Slow |
| Routing Entries | X | X | X | X | Correct/Incorrect |

---

## Cleanup Steps

After test completion, ensure proper cleanup:

```bash
# Enter sonic-cli on DUT1
sonic-cli

# Enter configuration mode
configure terminal

# Ensure PortChannel10 is up
interface PortChannel10
no shutdown
exit

# Ensure all member interfaces are up
interface Ethernet0
no shutdown
exit

interface Ethernet4
no shutdown
exit

# Exit configuration mode
exit

# Verify final state
show interface portchannel 10
show interface status
show ip route

# Optional: Remove test configuration
configure terminal

# Remove members from PortChannel
interface Ethernet0
no channel-group 10
exit

interface Ethernet4
no channel-group 10
exit

# Remove PortChannel
no interface PortChannel10

# Exit configuration mode
exit

# Verify cleanup
show interface portchannel

# Exit sonic-cli
exit
```

**Cleanup Verification**:
- All interfaces in admin=up, oper=up state
- PortChannel removed (if cleanup performed)
- No residual LAG configuration
- System resources at normal levels

---

## Test Environment Details

**Command Flow Reference**:
```
1. sonic-cli                           # Enter CLI (klish mode)
2. configure terminal                  # Enter config mode
3. interface PortChannel<num>          # Select PortChannel
4. shutdown / no shutdown              # Change PortChannel state
5. exit                                # Exit PortChannel config
6. interface Ethernet<num>             # Select member interface
7. shutdown / no shutdown              # Change member state
8. exit                                # Exit interface config
9. exit                                # Exit config mode
10. show interface portchannel         # Verify PortChannel state
11. show interface status              # Verify interface state
12. show ip route                      # Verify routing
```

**Topology Diagram**:
```
+--------------------+                       +--------------------+
|       DUT1         |                       |       DUT2         |
| (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
| 192.168.100.193    |        (LAG)          | 192.168.100.195    |
|                    |<-----Ethernet4------->|                    |
|  PortChannel10     |                       |  PortChannel10     |
|  10.0.10.1/24      |                       |  10.0.10.2/24      |
+--------------------+                       +--------------------+
```

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **PortChannel Configuration**:
   - Use LACP mode (active) for dynamic LAG
   - Can also test static LAG mode (on)
   - Ensure min-links configured appropriately for testing

3. **Member Interface Considerations**:
   - Test with 2 members (Ethernet0, Ethernet4)
   - Verify degraded mode operation (1 member)
   - Test complete failure (0 members)

4. **Routing Validation**:
   - Configure IP addresses on PortChannel for route testing
   - Verify route presence/absence correlates with PortChannel state
   - Check routing convergence time

5. **LACP Protocol**:
   - If using LACP, monitor protocol state
   - Verify LACP PDU exchange
   - Check member selection algorithm

6. **Flapping Execution**:
   - Test both PortChannel-level and member-level flapping
   - Include mixed flapping scenarios
   - Monitor for protocol instability

7. **Syslog Considerations**:
   - Look for PortChannel-specific log entries
   - Check for member state change logs
   - Verify routing protocol logs (if applicable)

8. **Performance Impact**:
   - PortChannel flapping may have higher impact than single interface
   - Member flapping tests LAG resilience
   - Monitor for any traffic impact during testing

9. **Expected Variations**:
   - LACP convergence time varies by configuration
   - Virtual environment may show different timing than hardware
   - Some platforms may have different min-links defaults

---

## Additional Validation Commands

For comprehensive testing and troubleshooting:

```bash
# PortChannel detailed information
show interface PortChannel10

# LACP status (if LACP mode)
show lacp interface PortChannel10

# Member interface details
show interface Ethernet0
show interface Ethernet4

# PortChannel counters
show interface PortChannel10 counters

# Routing table verification
show ip route
show ip route 10.0.10.0/24

# System logs
show logging | grep PortChannel
show logging | grep -E "Ethernet0|Ethernet4"
show logging | grep -i lacp

# Running configuration
show running-configuration interface PortChannel10
show running-configuration interface Ethernet0

# System resource monitoring
show processes cpu
show processes memory
```

---

## Troubleshooting

### Common Issues and Resolution

**Issue 1**: PortChannel doesn't come up after member addition
- **Cause**: Member interfaces not in up state, LACP negotiation failure, or config mismatch
- **Resolution**:
  - Verify member interfaces are up: `show interface status`
  - Check LACP status: `show lacp interface`
  - Verify matching configuration on peer device
  - Check for LACP mode mismatch

**Issue 2**: PortChannel state stuck during flapping
- **Cause**: LACP protocol state machine issue or member state confusion
- **Resolution**:
  - Clear PortChannel counters: `clear counters interface PortChannel10`
  - Remove and re-add members
  - Check for hardware or link issues
  - Review system logs for errors

**Issue 3**: Routing table not updating when PortChannel state changes
- **Cause**: Routing daemon not detecting interface state changes
- **Resolution**:
  - Verify routing protocol is running
  - Check interface IP configuration
  - Force routing update if possible
  - Check routing daemon logs

**Issue 4**: Member interface shows as inactive despite being up
- **Cause**: LACP negotiation failure, protocol mismatch, or selection algorithm
- **Resolution**:
  - Check LACP partner information
  - Verify member interface configuration
  - Check for speed/duplex mismatch
  - Review min-links configuration

**Issue 5**: CLI shows inconsistent member count
- **Cause**: State synchronization delay or member state confusion
- **Resolution**:
  - Wait for LACP convergence (up to 30 seconds)
  - Verify actual member interface states
  - Check for race conditions in flapping test
  - Review PortChannel state machine

**Issue 6**: System becomes slow during PortChannel flapping
- **Cause**: Resource-intensive protocol operations or event processing
- **Resolution**:
  - Monitor CPU usage during flapping
  - Reduce flapping rate
  - Check for process crashes or restarts
  - Investigate LACP or routing protocol resource usage

---

## Performance Benchmarks

### Expected Behavior

**CLI Response Time**:
- Normal conditions: 1-3 seconds
- During PortChannel flapping: 2-5 seconds
- During member flapping: 1-4 seconds
- Maximum acceptable: 10 seconds

**PortChannel State Transition Time**:
- Admin state change: < 1 second
- Oper state change: 1-3 seconds
- CLI reflection: 1-2 seconds after actual change

**Member State Transition Time**:
- Member shutdown detection: 1-3 seconds
- Member recovery: 2-5 seconds (LACP convergence)
- PortChannel update: 1-3 seconds after member state change

**Routing Convergence Time**:
- Route addition: 1-3 seconds after PortChannel up
- Route removal: 1-2 seconds after PortChannel down
- Total convergence: < 5 seconds

**LACP Protocol Timing** (if applicable):
- Initial convergence: 10-30 seconds
- Member selection after recovery: 5-15 seconds
- PDU exchange interval: 1 second (fast) or 30 seconds (slow)

**System Resource Usage**:
- CPU: Baseline + 10-20% during flapping
- Memory: No significant increase (< 5% variation)
- Network I/O: Moderate increase due to protocol traffic

### Acceptable Variations

- Virtual environments may show faster state transitions
- LACP slow mode increases convergence time
- First few cycles may be slower due to protocol initialization
- Minor CLI response variations (±2 seconds) acceptable
- Routing convergence may vary with protocol complexity

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Test ID**: 1.3.6
- **Test Category**: Interface Events - Continuous LAG Flapping
- **Priority**: High
- **Automation**: Highly recommended for automation due to repetitive nature
- **Related Test Cases**:
  - TC_INTF_EVENTS_001 (Basic Admin/Link State Changes)
  - TC_INTF_EVENTS_002 (LAG/ECMP Propagation)
  - TC_INTF_EVENTS_005 (Continuous Interface Flapping)
- **Related RFCs**:
  - IEEE 802.3ad (Link Aggregation)
  - IEEE 802.1AX (Link Aggregation Control Protocol)

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Interface Commands**:
```bash
show interface status                      # Display all interface status
show interface status PortChannel<num>     # Display PortChannel status
show interface portchannel                 # Display all PortChannels
show interface portchannel <num>           # Display specific PortChannel
show interface portchannel summary         # Display PortChannel summary
```

**Routing Commands**:
```bash
show ip route                              # Display routing table
show ip route <subnet>                     # Display specific route
```

**LACP Commands**:
```bash
show lacp interface                        # Display LACP status
show lacp interface PortChannel<num>       # Display LACP for specific PC
```

**Logging Commands**:
```bash
show logging                               # Display system logs
show logging | grep PortChannel            # Filter PortChannel logs
show logging | grep -i lacp                # Filter LACP logs
```

**System Monitoring Commands**:
```bash
show processes cpu                         # Display CPU utilization
show processes memory                      # Display memory utilization
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**PortChannel Configuration**:
```bash
configure terminal                         # Enter configuration mode
interface PortChannel<num>                 # Create/enter PortChannel config
shutdown                                   # Shutdown PortChannel
no shutdown                                # Enable PortChannel
ip address <ip>/<mask>                     # Configure IP address
exit                                       # Exit PortChannel config
no interface PortChannel<num>              # Delete PortChannel
```

**Member Interface Configuration**:
```bash
interface Ethernet<num>                    # Enter interface config
channel-group <num> mode <mode>            # Add to PortChannel
no channel-group <num>                     # Remove from PortChannel
shutdown                                   # Shutdown member
no shutdown                                # Enable member
exit                                       # Exit interface config
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.3.6 - Validate CLI/syslog for admin/link state changes continuous LAG interface flapping
