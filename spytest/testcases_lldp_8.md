# LLDP Test Cases

## Testcase ID: 1.1.8

### Title
Negative testing: Rapid enable/disable of LLDP

### Objective
To verify system stability and correct LLDP table behavior under rapid enable/disable operations. Ensure that LLDP handles rapid state changes gracefully without stale entries, memory leaks, crashes, or table corruption. Validate that the LLDP table converges correctly after rapid churn and that entries are properly aged out according to TTL.

### Test Topology
- **Devices**: smic_sonic1, smic_sonic2
- **Test Interfaces**: Ethernet4 (connected between smic_sonic1 and smic_sonic2)
- **Testbed File**: /home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml

### Test Procedure

1. **Configure and verify LLDP globally and at interface level**
   - Fetch Ethernet interface information from testbed: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
   - Go to interface mode and give "no shut" to all interfaces in the testbed (Ethernet4)
   - Test LLDP enable/disable:
     - Enable LLDP in config mode: `lldp enable`
     - Disable LLDP in config mode: `no lldp enable`
     - Enable LLDP in interface mode: `lldp enable` (on Ethernet4)
     - Disable LLDP in interface mode: `no lldp enable` (on Ethernet4)
   - Establish baseline LLDP operation

2. **Rapid toggle LLDP globally**
   - Enable LLDP globally
   - Immediately disable LLDP globally
   - Repeat enable/disable cycle rapidly (e.g., 10-20 iterations)
   - Minimal delay between operations (e.g., 0-2 seconds)
   - Test system's ability to handle rapid state transitions

3. **Rapid toggle LLDP per interface**
   - Enable LLDP on specific interface (Ethernet4)
   - Immediately disable LLDP on the interface
   - Repeat enable/disable cycle rapidly (e.g., 10-20 iterations)
   - Minimal delay between operations (e.g., 0-2 seconds)
   - Test interface-level rapid state changes

4. **Combined rapid toggle (global and interface)**
   - Rapidly toggle LLDP at both global and interface levels
   - Interleave global and interface enable/disable operations
   - Create maximum churn scenario
   - Test system stability under stress

5. **Establish stable state and observe convergence**
   - Enable LLDP globally and on interfaces
   - Allow sufficient time for LLDP to stabilize
   - Verify neighbors are discovered
   - Monitor LLDP table for convergence

6. **Verify LLDP table integrity**
   - Check for stale entries in LLDP table
   - Verify entries age out properly according to TTL
   - Confirm no entries persist beyond their TTL
   - Validate table updates correctly after churn

7. **Verify system stability**
   - Check system logs for errors, warnings, or crashes
   - Monitor CPU and memory usage
   - Verify no memory leaks
   - Confirm no process restarts or failures

8. **Repeat rapid toggle after stabilization**
   - Perform another round of rapid enable/disable
   - Verify system continues to operate correctly
   - Confirm consistent behavior across multiple cycles

### Show Commands to Validate

#### Klish Mode (sonic-cli)
**Note**: These commands are currently under development and may not produce output yet. Execute inside `sonic-cli`:
1. `show lldp table`
2. `show lldp neighbor`
3. `show lldp statistics`

#### Click Mode (sudo config)
**Note**: These commands work properly and need to be executed outside sonic-cli:
1. `show lldp table`
2. `show lldp neighbor`

### Expected Output

1. **System Stability**
   - System remains stable during rapid enable/disable operations
   - No crashes, panics, or process restarts
   - No kernel errors or warnings in system logs
   - LLDP daemon handles rapid state changes gracefully

2. **No Stale Entries Beyond TTL**
   - LLDP table does not contain stale entries
   - All entries age out properly according to TTL
   - No entries persist after their TTL has expired
   - Table is cleaned up correctly after disable operations

3. **Table Updates Correctly Under Churn**
   - LLDP table updates correctly after rapid enable/disable
   - Neighbor entries appear after LLDP is enabled
   - Neighbor entries disappear after LLDP is disabled
   - Table converges to correct state after stabilization
   - No duplicate or corrupted entries

4. **Proper Convergence**
   - After rapid churn, LLDP converges to a stable state
   - Neighbors are discovered correctly
   - LLDP advertisements are sent and received properly
   - Table reflects current network topology accurately

5. **Resource Management**
   - No memory leaks detected
   - Memory usage returns to normal levels after churn
   - CPU usage remains within acceptable limits
   - No resource exhaustion or allocation failures

6. **Configuration Persistence**
   - LLDP configuration persists correctly
   - Enable/disable state is accurate
   - No configuration corruption
   - Final state matches last configuration command

7. **Timing and TTL Behavior**
   - TTL values are respected
   - Entries age out at the correct time
   - No premature or delayed entry removal
   - Timer mechanisms function correctly under stress

8. **Neighbor Discovery After Stabilization**
   - After rapid churn, neighbors are rediscovered
   - All expected neighbors appear in the table
   - Neighbor information is complete and accurate
   - TLVs are properly exchanged

### Pass/Fail Criteria

**Pass Criteria:**
- System remains stable during all rapid enable/disable operations
- No crashes, kernel panics, or process failures occur
- LLDP daemon continues to function correctly after rapid churn
- No stale entries remain in LLDP table beyond their TTL
- LLDP table updates correctly under churn conditions
- Neighbor entries appear and disappear appropriately with state changes
- After stabilization, LLDP table converges to correct state
- Neighbors are properly discovered after enable operations
- No memory leaks are detected
- Memory and CPU usage remain within acceptable limits
- System logs show no critical errors or warnings
- Configuration state is consistent and accurate
- TTL and aging mechanisms function correctly
- All show commands execute without errors in both klish and click modes
- Table data is consistent across multiple rapid toggle cycles

**Fail Criteria:**
- System crashes, panics, or becomes unresponsive
- LLDP daemon fails or requires restart
- Stale entries persist in LLDP table beyond TTL
- LLDP table becomes corrupted or contains invalid data
- Duplicate or phantom neighbor entries appear
- Neighbors fail to be discovered after enable operations
- Memory leaks are detected
- Memory or CPU usage grows unbounded
- System logs contain critical errors, segfaults, or assertion failures
- Configuration becomes corrupted or inconsistent
- LLDP table fails to converge after stabilization
- Entries do not age out according to TTL
- Show commands fail, hang, or return incorrect data
- Behavior is inconsistent across multiple toggle cycles
- Resource exhaustion occurs (file descriptors, sockets, etc.)
- Network performance degrades significantly

### Additional Notes

- **Rapid Toggle Definition**: Enable/disable operations performed with minimal delay (0-2 seconds) between iterations
- **Iteration Count**: Typically 10-20 rapid toggles per test phase
- **Stabilization Time**: Allow 30-60 seconds after rapid churn for system to stabilize
- **TTL Verification**: Default LLDP TTL is typically 120 seconds (timer × multiplier)
- **Stress Testing**: This test specifically targets system stability under stress conditions
- **Error Recovery**: System should recover gracefully even if transient errors occur during churn
- **Logging**: Capture detailed logs before, during, and after rapid toggle operations
- **Baseline Comparison**: Compare system state before and after rapid toggle to detect anomalies
- **Performance Impact**: Monitor for any performance degradation that persists after stabilization
- **Edge Cases**: Test includes transitions from enabled→disabled→enabled and disabled→enabled→disabled
- **Concurrency**: Rapid operations may trigger race conditions or concurrency issues
- **Resource Cleanup**: Verify proper cleanup of internal data structures during state transitions

### Test Variations

1. **Variable Toggle Intervals**: Test with different delays (0s, 1s, 2s, 5s)
2. **Different Iteration Counts**: Test with 5, 10, 20, 50 iterations
3. **Mixed Operations**: Interleave global and interface toggles
4. **Multi-Interface**: Perform rapid toggles on multiple interfaces simultaneously
5. **During Active Communication**: Perform toggles while LLDP packets are being exchanged
