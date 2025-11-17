# Test Cases - Interface Events Validation (Continuous Flapping)

## Test Case ID: TC_INTF_EVENTS_005

### Test Case Name
Validate CLI/Syslog for Admin/Link State Changes with Continuous Interface Flapping

### Test Objective
Validate that continuous interface administrative state changes (shutdown/no shutdown) are accurately reflected in CLI outputs and system logs. Ensure that rapid and repeated state transitions are properly captured, logged, and displayed without loss of events or system instability during sustained interface flapping operations.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Device Under Test (DUT1)**: smic_sonic1 (192.168.100.193)
- **Peer Device (DUT2)**: smic_sonic2 (192.168.100.195)
- **Test Interface**: Ethernet4
- **Connection**: smic_sonic1:Ethernet4 <---> smic_sonic2:Ethernet4
- **Topology**: 2 nodes

### Prerequisites
1. Both devices (smic_sonic1 and smic_sonic2) must be accessible via SSH
2. User credentials: admin/YourPaSsWoRd
3. Access to sonic-cli and klish shell
4. Sufficient privileges to configure interfaces
5. System logging enabled and functional
6. Sufficient system resources to handle rapid state transitions

---

## Test Procedure

### Step 1: Initial Configuration - Bring Interface to UP State
**Objective**: Ensure the test interface is in operational "up" state before testing

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Bring up Ethernet4
interface Ethernet4
no shutdown
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Ethernet4 should show administrative state as "up"
- Operational state should transition to "up"
- No errors during interface activation

---

### Step 2: Baseline Interface Status Check
**Objective**: Capture baseline interface status before continuous flapping test

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status

# Optionally check specific interface
show interface status Ethernet4
```

**Expected Result**:
- Interface Ethernet4 should display:
  - Admin Status: up
  - Oper Status: up
  - Speed and duplex information should be visible
- Output should be captured for baseline comparison

**Sample Output Format**:
```
Interface        Admin    Oper    Speed         Type              Description
--------------------------------------------------------------------------------------
Ethernet4        up       up      <speed>       <type>            <description>
```

---

### Step 3: Baseline Syslog Check
**Objective**: Capture baseline system logs before testing

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check system logs
show logging

# Optionally filter for interface-related logs
show logging | grep Ethernet4
```

**Expected Result**:
- Command should execute successfully
- Baseline logs captured for comparison
- Note any existing interface-related log entries

**Note**: If `show logging` command has issues, document the behavior and proceed with the test. The primary validation will be on `show interface status` command.

---

### Step 4: Single Interface Shutdown Test
**Objective**: Verify single interface shutdown is properly reflected in CLI and syslog

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Shutdown Ethernet4
interface Ethernet4
shutdown
exit

# Exit configuration mode
exit

# Verify interface status immediately
show interface status Ethernet4

# Check syslog for shutdown event
show logging | grep Ethernet4
```

**Expected Result**:
- Interface Ethernet4 should show:
  - Admin Status: down
  - Oper Status: down
- Syslog should contain entry indicating interface state change to down (if logging is functional)
- State transition should be immediate and accurate
- Timestamp in logs should correspond to shutdown action

**Validation Points**:
1. CLI accurately reflects admin state = down
2. CLI accurately reflects oper state = down
3. Syslog contains interface down event (with timestamp)
4. No errors or exceptions during shutdown

---

### Step 5: Single Interface No Shutdown Test (Recovery)
**Objective**: Verify interface recovery is properly reflected in CLI and syslog

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Bring up Ethernet4
interface Ethernet4
no shutdown
exit

# Exit configuration mode
exit

# Verify interface status immediately
show interface status Ethernet4

# Check syslog for interface up event
show logging | grep Ethernet4
```

**Expected Result**:
- Interface Ethernet4 should show:
  - Admin Status: up
  - Oper Status: up
- Syslog should contain entry indicating interface state change to up
- State transition should be successful
- Interface should recover to baseline operational state
- Timestamp in logs should correspond to no shutdown action

**Validation Points**:
1. CLI accurately reflects admin state = up
2. CLI accurately reflects oper state = up
3. Syslog contains interface up event (with timestamp)
4. No errors or exceptions during recovery

---

### Step 6: Continuous Interface Flapping - Iteration 1 (10 Cycles)
**Objective**: Validate system behavior during continuous rapid shutdown/no shutdown cycles

**Test Procedure**:
Perform 10 rapid shutdown/no shutdown cycles and verify each transition

**Commands (Execute on DUT1)**:
```bash
# For each cycle (repeat 10 times):

# Cycle N (where N = 1 to 10):
sonic-cli
configure terminal
interface Ethernet4
shutdown
exit
exit

# Verify shutdown state
show interface status Ethernet4

# Bring interface back up
configure terminal
interface Ethernet4
no shutdown
exit
exit

# Verify up state
show interface status Ethernet4

# Brief stabilization pause (1-2 seconds)
```

**Expected Result**:
- Each shutdown operation should result in:
  - Admin Status: down
  - Oper Status: down
  - CLI output accurately reflects state

- Each no shutdown operation should result in:
  - Admin Status: up
  - Oper Status: up
  - CLI output accurately reflects state

- System should handle all 10 cycles without:
  - Interface state inconsistencies
  - CLI command failures
  - System crashes or hangs
  - Log overflow or loss

**Validation After 10 Cycles**:
```bash
# Check final interface status
sonic-cli
show interface status Ethernet4

# Check syslog for all events
show logging | grep Ethernet4
```

**Expected Validation**:
1. Final interface state should be "up" (last command was no shutdown)
2. Syslog should contain entries for all 20 state transitions (10 down, 10 up)
3. No missing or duplicated log entries
4. All timestamps should be in chronological order
5. No error messages in logs

---

### Step 7: Continuous Interface Flapping - Iteration 2 (25 Cycles)
**Objective**: Validate system stability during extended continuous flapping

**Test Procedure**:
Perform 25 rapid shutdown/no shutdown cycles

**Commands**: (Same pattern as Step 6, repeated 25 times)

**Expected Result**:
- System remains stable throughout all 25 cycles
- CLI continues to respond accurately
- No degradation in response time
- All state transitions properly recorded

**Validation After 25 Cycles**:
```bash
# Check interface status
sonic-cli
show interface status Ethernet4

# Check syslog for events
show logging | grep Ethernet4
```

**Expected Validation**:
1. Final interface state = up
2. Syslog contains entries for all 50 state transitions (25 down, 25 up)
3. No system resource exhaustion
4. No CLI degradation or timeouts
5. Log entries remain consistent and accurate

---

### Step 8: Continuous Interface Flapping - Iteration 3 (50 Cycles)
**Objective**: Validate system behavior under sustained high-frequency flapping

**Test Procedure**:
Perform 50 rapid shutdown/no shutdown cycles

**Commands**: (Same pattern as Step 6, repeated 50 times)

**Expected Result**:
- System handles sustained flapping without failures
- CLI commands continue to execute normally
- Interface state transitions remain accurate
- No memory leaks or resource exhaustion

**Validation After 50 Cycles**:
```bash
# Check interface status
sonic-cli
show interface status Ethernet4

# Check syslog for events (may need to check log size)
show logging | grep Ethernet4

# Check system resources
show processes cpu
show processes memory
```

**Expected Validation**:
1. Final interface state = up
2. Syslog contains entries for all 100 state transitions (50 down, 50 up)
3. System CPU and memory within acceptable limits
4. No performance degradation
5. All CLI commands respond within normal timeframes

---

### Step 9: Continuous Interface Flapping - Iteration 4 (100 Cycles)
**Objective**: Validate maximum sustained flapping capability and system robustness

**Test Procedure**:
Perform 100 rapid shutdown/no shutdown cycles

**Commands**: (Same pattern as Step 6, repeated 100 times)

**Expected Result**:
- System demonstrates robustness under extreme flapping conditions
- All state transitions are handled correctly
- No system instability or crashes
- Logging system continues to function properly

**Validation After 100 Cycles**:
```bash
# Check interface status
sonic-cli
show interface status Ethernet4

# Check recent syslog entries
show logging | grep Ethernet4

# Verify system stability
show processes cpu
show processes memory

# Check for any system errors
show logging | grep -i error
show logging | grep -i fail
```

**Expected Validation**:
1. Final interface state = up
2. Syslog contains entries for all 200 state transitions (100 down, 100 up)
   - Note: Depending on log buffer size, oldest entries may be rotated out
   - Verify most recent entries are present and accurate
3. System remains stable and responsive
4. No error messages related to interface flapping
5. CPU and memory usage return to normal levels
6. No indication of resource leaks or exhaustion

---

### Step 10: Rapid Flapping Without Delay (Stress Test)
**Objective**: Test system behavior during rapid flapping with minimal delay

**Test Procedure**:
Perform rapid shutdown/no shutdown cycles with minimal delay between commands (10 cycles)

**Commands (Execute on DUT1)**:
```bash
# Rapid flapping without stabilization delay
# For each cycle (repeat 10 times with minimal delay):

sonic-cli
configure terminal
interface Ethernet4
shutdown
no shutdown
exit
exit

# Verify final state
show interface status Ethernet4
```

**Expected Result**:
- System should handle rapid commands without errors
- Final interface state should be deterministic (up)
- CLI should remain responsive
- No command queue overflows or failures

**Validation**:
1. Interface reaches stable "up" state
2. No CLI errors or timeouts
3. System remains stable
4. Syslog may show compressed or merged events (acceptable)

---

### Step 11: Final State Verification
**Objective**: Verify system is in clean state after all flapping tests

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify final interface status
show interface status Ethernet4

# Check overall system status
show interface status

# Verify no error conditions
show logging | grep -i error | tail -20

# Check system resources
show processes cpu
show processes memory
```

**Expected Result**:
- Interface Ethernet4 is in "up" state (admin and oper)
- No residual error conditions
- System resources at normal levels
- All CLI commands responsive
- No system instability indicators

---

## Validation Points

### CLI Validation (klish mode via sonic-cli)

**Primary Command**: `show interface status`

**Validation Criteria**:

#### 1. Immediate State Reflection
- **After shutdown command**:
  - Admin state = down
  - Oper state = down
  - Change reflected immediately (within 1-2 seconds)

- **After no shutdown command**:
  - Admin state = up
  - Oper state = up
  - Change reflected immediately (within 1-2 seconds)

#### 2. State Consistency During Flapping
- CLI output always reflects current interface state
- No stale or cached information displayed
- State transitions occur in correct sequence
- No state confusion or intermediate states persisting

#### 3. CLI Responsiveness
- Commands execute within normal timeframes throughout testing
- No degradation in response time during flapping
- No command failures or timeouts
- No CLI hang or freeze conditions

#### 4. Output Format Consistency
- Interface status output format remains consistent
- All fields populated correctly
- No corrupted or malformed output
- Column alignment maintained

### Syslog Validation (When feature is available)

**Command**: `show logging` or `show logging | grep Ethernet4`

**Validation Criteria**:

#### 1. Event Completeness
- Each shutdown event logged with timestamp
- Each no shutdown event logged with timestamp
- No missing events during continuous flapping
- Events logged in chronological order

#### 2. Event Accuracy
- Log entries match actual state transitions
- Timestamps correspond to command execution times
- Interface name correctly identified in logs
- State change direction accurately reported (up/down)

#### 3. Log System Robustness
- Logging system handles high event rate during flapping
- No log buffer overflows causing event loss
- No log corruption or malformed entries
- Log rotation (if applicable) functions correctly

#### 4. Event Details
- Each log entry includes:
  - Timestamp (date and time)
  - Interface name (Ethernet4)
  - State change (admin up/down, oper up/down)
  - Severity level (info/notice)
  - Process/service generating the log

---

## Expected Overall Results

### Success Criteria

#### 1. CLI Accuracy
- `show interface status` command accurately reflects interface state at all times
- State transitions are immediate and correct
- CLI remains responsive throughout all test iterations
- No CLI errors, hangs, or crashes
- Output format remains consistent

#### 2. State Transition Correctness
- shutdown → Admin: down, Oper: down (100% of cycles)
- no shutdown → Admin: up, Oper: up (100% of cycles)
- No incorrect or intermediate states
- No state transition failures

#### 3. System Stability
- System handles continuous flapping without crashes
- No resource exhaustion (CPU, memory, disk)
- All services remain operational
- No system reboots or failures
- System recovers to normal state after flapping stops

#### 4. Logging Accuracy (if available)
- All state transitions logged correctly
- Log entries contain accurate information
- No missing events or log loss
- Timestamps are accurate and sequential
- No log corruption

#### 5. Performance Consistency
- CLI response time remains consistent across all iterations
- No degradation during extended flapping (100 cycles)
- System resources return to normal after testing
- No performance anomalies or outliers

### Performance Criteria

- **CLI Response Time**: < 5 seconds throughout testing
- **State Transition Time**: < 2 seconds per transition
- **System CPU Usage**: Should not exceed 80% during flapping
- **System Memory Usage**: No memory leaks; usage should stabilize
- **Log Processing**: All events logged within 5 seconds of occurrence

### Failure Indicators

**Test should fail if**:
1. CLI shows incorrect interface state at any point
2. Interface state becomes stuck or inconsistent
3. CLI commands fail or timeout during testing
4. System crashes or becomes unresponsive
5. State transitions are not reflected in CLI output
6. Critical system resources exhausted
7. Multiple consecutive command failures (3+ failures)

---

## Test Execution Summary Template

### Single Cycle Verification

| Operation | Admin State | Oper State | CLI Accurate | Syslog Entry | Result |
|-----------|-------------|------------|--------------|--------------|--------|
| Baseline | up | up | Yes/No | - | Pass/Fail |
| Shutdown (Step 4) | down | down | Yes/No | Yes/No | Pass/Fail |
| No Shutdown (Step 5) | up | up | Yes/No | Yes/No | Pass/Fail |

### Continuous Flapping Summary

| Iteration | Cycles | Total Transitions | CLI Accurate | System Stable | Logs Complete | Result |
|-----------|--------|-------------------|--------------|---------------|---------------|--------|
| 1 | 10 | 20 | Yes/No | Yes/No | Yes/No | Pass/Fail |
| 2 | 25 | 50 | Yes/No | Yes/No | Yes/No | Pass/Fail |
| 3 | 50 | 100 | Yes/No | Yes/No | Yes/No | Pass/Fail |
| 4 | 100 | 200 | Yes/No | Yes/No | Yes/No | Pass/Fail |
| Stress | 10 (rapid) | 20 | Yes/No | Yes/No | Yes/No | Pass/Fail |

### System Resource Monitoring

| Metric | Baseline | After 10 Cycles | After 25 Cycles | After 50 Cycles | After 100 Cycles | Status |
|--------|----------|-----------------|-----------------|-----------------|------------------|--------|
| CPU Usage (%) | X% | X% | X% | X% | X% | Normal/High |
| Memory Usage (%) | X% | X% | X% | X% | X% | Normal/High |
| CLI Response (sec) | X | X | X | X | X | Normal/Slow |
| Log Entries Count | X | X | X | X | X | Complete/Partial |

---

## Cleanup Steps

After test completion, ensure proper cleanup:

```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Restore Ethernet4 to up state
interface Ethernet4
no shutdown
exit

# Exit configuration mode
exit

# Verify final state
show interface status Ethernet4

# Exit sonic-cli
exit
```

**Cleanup Verification**:
- Ethernet4 should be in admin=up, oper=up state
- No residual error conditions
- System resources at normal levels
- All services functioning normally

---

## Test Environment Details

**Command Flow Reference**:
```
1. sonic-cli                    # Enter CLI (klish mode)
2. configure terminal           # Enter config mode
3. interface Ethernet<num>      # Select interface
4. shutdown                     # Administratively disable
5. exit                         # Exit interface config
6. exit                         # Exit config mode
7. show interface status        # Verify state
8. (repeat steps 2-7 for no shutdown)
9. (repeat entire cycle N times for continuous flapping)
```

**Topology Diagram**:
```
+--------------------+                       +--------------------+
|       DUT1         |                       |       DUT2         |
| (smic_sonic1)      |<-----Ethernet4------->| (smic_sonic2)      |
| 192.168.100.193    |                       | 192.168.100.195    |
+--------------------+                       +--------------------+
```

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **Flapping Execution Considerations**:
   - For manual testing: Execute cycles with brief pauses for observation
   - For automated testing: Can execute cycles rapidly but with verification checkpoints
   - Monitor system resources during extended flapping (50+ cycles)

3. **Syslog Considerations**:
   - If `show logging` command is not fully functional, focus validation on CLI accuracy
   - Document syslog behavior for future reference
   - Note any log rotation or buffer limitations

4. **Resource Monitoring**:
   - Monitor CPU usage during extended flapping
   - Monitor memory usage for potential leaks
   - Check for any process crashes or restarts
   - Verify no disk space issues from excessive logging

5. **Timing Considerations**:
   - Brief stabilization pause (1-2 seconds) recommended between cycles
   - For stress testing, minimal or no delay acceptable
   - Monitor for any timing-related issues or race conditions

6. **Automation Recommendations**:
   - Use scripting/automation for 50+ cycle iterations
   - Implement automatic verification after each cycle
   - Log all results for post-test analysis
   - Include checkpoints for system health verification

7. **Expected Variations**:
   - Virtual environment may show faster state transitions than hardware
   - Log buffer size may vary between platforms
   - Some platforms may implement event throttling or aggregation
   - CLI response time may vary based on system load

8. **Troubleshooting Tips**:
   - If CLI becomes slow: Check CPU usage, reduce flapping rate
   - If states are inconsistent: Verify interface is properly connected
   - If logs are missing: Check log buffer size and rotation settings
   - If system becomes unstable: Reduce cycle count or add delays

---

## Additional Validation Commands

For comprehensive testing and troubleshooting:

```bash
# Detailed interface information
show interface Ethernet4

# Interface statistics
show interface Ethernet4 counters

# System logs with different filters
show logging | grep -i interface
show logging | grep -i admin
show logging | grep -i oper

# System health checks
show processes cpu
show processes memory
show platform summary

# Running configuration
show running-configuration interface Ethernet4
```

---

## Troubleshooting

### Common Issues and Resolution

**Issue 1**: CLI shows stale interface state
- **Cause**: Cache or state synchronization delay
- **Resolution**:
  - Wait 2-3 seconds and re-query
  - Check if backend process is responsive
  - Verify interface module is functioning

**Issue 2**: Interface state becomes stuck
- **Cause**: Command execution failure or hardware issue
- **Resolution**:
  - Check command output for errors
  - Verify peer interface is functioning
  - Try manual interface reset
  - Check system logs for errors

**Issue 3**: CLI becomes slow or unresponsive during flapping
- **Cause**: System resource exhaustion or command queue backlog
- **Resolution**:
  - Check CPU and memory usage
  - Reduce flapping rate
  - Add stabilization delays between cycles
  - Investigate high CPU processes

**Issue 4**: Syslog entries missing or incomplete
- **Cause**: Log buffer overflow, logging disabled, or event throttling
- **Resolution**:
  - Check log buffer size configuration
  - Verify logging service is running
  - Check for event rate limiting or throttling
  - Increase log buffer size if needed

**Issue 5**: System crashes during extended flapping
- **Cause**: Software bug, resource exhaustion, or hardware issue
- **Resolution**:
  - Collect crash logs and core dumps
  - Check system messages before crash
  - Reduce cycle count for incremental testing
  - Report bug with reproduction steps

**Issue 6**: Memory usage increases during flapping
- **Cause**: Potential memory leak in interface management
- **Resolution**:
  - Monitor memory usage over time
  - Check if memory is released after flapping stops
  - Document memory growth rate
  - Report potential memory leak

---

## Performance Benchmarks

### Expected Behavior

**CLI Response Time**:
- Normal conditions: 1-3 seconds
- During light flapping (10 cycles): 1-4 seconds
- During heavy flapping (100 cycles): 2-5 seconds
- Maximum acceptable: 10 seconds

**State Transition Time**:
- Admin state change: < 1 second
- Oper state change: 1-3 seconds (depends on link detection)
- CLI reflection: 1-2 seconds after actual state change

**System Resource Usage**:
- CPU: Baseline + 5-15% during flapping
- Memory: No significant increase (< 5% variation)
- Disk I/O: Moderate increase due to logging

**Logging Performance**:
- Event logging delay: < 5 seconds
- Log buffer capacity: Typically 1000-10000 entries
- Log rotation: May occur during extended testing

### Acceptable Variations

- Virtual environments may show faster transitions
- First few cycles may be slower due to caching
- Some event aggregation in logs is acceptable for rapid flapping
- Minor CLI response variations (±2 seconds) acceptable

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Test ID**: 1.3.5
- **Test Category**: Interface Events - Continuous Flapping
- **Priority**: High
- **Automation**: Highly recommended for automation due to repetitive nature
- **Related Test Cases**:
  - TC_INTF_EVENTS_001 (Basic Admin/Link State Changes)
  - TC_INTF_EVENTS_002 (LAG/ECMP Propagation)
  - TC_INTF_EVENTS_004 (Detection/Recovery Latency Under Load)

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Interface Commands**:
```bash
show interface status                # Display all interface status
show interface status Ethernet<num>  # Display specific interface status
show interface Ethernet<num>         # Display detailed interface info
show interface counters              # Display interface counters
```

**Logging Commands**:
```bash
show logging                         # Display system logs
show logging | grep Ethernet         # Filter interface-related logs
show logging | grep -i admin         # Filter admin state changes
show logging | grep -i error         # Filter error messages
show logging | tail -50              # Show last 50 log entries
```

**System Monitoring Commands**:
```bash
show processes cpu                   # Display CPU utilization
show processes memory                # Display memory utilization
show platform summary                # Display platform information
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**Interface Configuration**:
```bash
configure terminal                   # Enter configuration mode
interface Ethernet<num>              # Enter interface configuration
shutdown                             # Administratively disable interface
no shutdown                          # Administratively enable interface
exit                                 # Exit interface configuration
exit                                 # Exit configuration mode
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.3.5 - Validate CLI/syslog for admin/link state changes continuous interface flapping
