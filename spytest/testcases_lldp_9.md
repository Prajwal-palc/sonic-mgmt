# LLDP Test Cases

## Testcase ID: 1.1.9

### Title
Negative testing: Verify LLDP during rapid link failure

### Objective
To verify LLDP behavior and neighbor table integrity during rapid interface link flaps. Ensure that LLDP handles rapid link up/down events gracefully with timely neighbor withdrawal and appearance, proper TTL-based aging, and no stale entries. Validate system stability under rapid link failure conditions.

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

2. **Enable LLDP globally and on interfaces**
   - Enable LLDP globally on both DUTs
   - Enable LLDP on test interfaces (Ethernet4) on both DUTs
   - Verify LLDP is active and operational
   - Verify baseline neighbor discovery

3. **Verify baseline neighbor table**
   - Verify neighbors are discovered on both devices
   - Record baseline neighbor information
   - Capture baseline TTL and timing values
   - Ensure stable operation before stress testing

4. **Perform rapid interface flapping**
   - Shutdown interface: `shutdown` on Ethernet4
   - Immediately bring up interface: `no shutdown` on Ethernet4
   - Repeat shutdown/no-shutdown cycle rapidly (e.g., 15-20 iterations)
   - Minimal delay between operations (e.g., 1-3 seconds)
   - Test system's ability to handle rapid link state changes

5. **Monitor neighbor table during flapping**
   - Continuously check neighbor table state during flaps
   - Observe neighbor withdrawal when link goes down
   - Observe neighbor appearance when link comes up
   - Track timing of withdrawals and appearances

6. **Verify timely neighbor withdrawal**
   - When interface goes down, neighbor should be removed promptly
   - Withdrawal should occur within reasonable time (e.g., within TTL)
   - No delayed or stuck entries
   - Proper cleanup of neighbor information

7. **Verify timely neighbor appearance**
   - When interface comes up, neighbor should appear promptly
   - Appearance should occur within LLDP advertisement interval
   - Neighbor information should be complete and accurate
   - TTL should be reset to initial value

8. **Verify no stale neighbors beyond TTL**
   - Check that no stale neighbor entries persist
   - All entries should age out properly according to TTL
   - No orphaned or zombie entries
   - Table should be clean after link stabilization

9. **Establish stable state after flapping**
   - Ensure interface is up and stable
   - Allow sufficient time for LLDP to stabilize
   - Verify neighbor table converges to correct state
   - Compare final state with baseline

10. **Verify neighbor table on both devices**
    - Check neighbor table on DUT
    - Check neighbor table on peer DUT
    - Verify bidirectional neighbor discovery
    - Ensure consistency across both devices

11. **Verify system stability**
    - Check system logs for errors or warnings
    - Verify no crashes or process restarts
    - Monitor resource usage (CPU, memory)
    - Confirm system remains responsive

12. **Repeat rapid flapping for consistency**
    - Perform additional rounds of rapid interface flapping
    - Verify consistent behavior across multiple cycles
    - Confirm no degradation over time

### Show Commands to Validate

#### Klish Mode (sonic-cli)
**Note**: These commands are currently under development and may not produce output yet. Execute inside `sonic-cli`:
1. `show lldp table`
2. `show lldp neighbor`
3. `show lldp neighbor Ethernet4`
4. `show lldp statistics`

#### Click Mode (sudo config)
**Note**: These commands work properly and need to be executed outside sonic-cli:
1. `show lldp table`
2. `show lldp neighbor`
3. `show lldp neighbor Ethernet4`

### Expected Output

1. **Timely Withdrawal of Neighbors**
   - When interface is shut down, neighbor entry is removed promptly
   - Withdrawal occurs within expected timeframe (typically within seconds to TTL)
   - No excessive delay in neighbor removal
   - Table is cleaned up properly after link down

2. **Timely Appearance of Neighbors**
   - When interface comes up, neighbor is discovered promptly
   - Appearance occurs within LLDP advertisement interval (typically 30 seconds)
   - Neighbor information is complete and accurate
   - TTL is properly initialized

3. **No Stale Neighbors Beyond TTL**
   - No neighbor entries persist beyond their TTL
   - All entries age out properly when link is down
   - No orphaned entries remain in the table
   - Table accurately reflects current network state

4. **System Stability**
   - System remains stable during rapid interface flapping
   - No crashes, panics, or process restarts
   - No kernel errors or warnings in system logs
   - LLDP daemon handles rapid link events gracefully

5. **Table Consistency**
   - Neighbor table is consistent across multiple flap cycles
   - No duplicate entries
   - No corrupted or malformed entries
   - Table state matches interface state

6. **Bidirectional Verification**
   - Both DUTs show consistent neighbor information
   - Neighbor discovery works in both directions
   - No asymmetric behavior between devices
   - Both devices handle link flaps similarly

7. **Resource Management**
   - No memory leaks during rapid flapping
   - Memory usage returns to normal after stabilization
   - CPU usage remains within acceptable limits
   - No resource exhaustion

8. **Timing Accuracy**
   - TTL values are accurate and properly maintained
   - Aging timers function correctly under stress
   - No premature or delayed entry removal
   - Timestamps are accurate

9. **Configuration Persistence**
   - LLDP configuration persists through link flaps
   - Enable state remains consistent
   - No configuration corruption
   - Settings remain intact after stress test

### Pass/Fail Criteria

**Pass Criteria:**
- System remains stable during all rapid interface flapping operations
- No crashes, kernel panics, or process failures occur
- LLDP daemon continues to function correctly after rapid link flaps
- Neighbors are withdrawn promptly when interface goes down
- Neighbors appear promptly when interface comes up
- No stale entries remain in neighbor table beyond TTL
- Neighbor table converges to correct state after stabilization
- Both DUTs show consistent neighbor information
- Bidirectional neighbor discovery works correctly
- No memory leaks are detected
- Memory and CPU usage remain within acceptable limits
- System logs show no critical errors or warnings
- TTL and aging mechanisms function correctly
- All show commands execute without errors in both klish and click modes
- Behavior is consistent across multiple flap cycles
- Interface state changes are properly detected and handled

**Fail Criteria:**
- System crashes, panics, or becomes unresponsive during flapping
- LLDP daemon fails or requires restart
- Neighbors fail to be withdrawn when interface goes down
- Neighbors fail to appear when interface comes up
- Excessive delay in neighbor withdrawal (beyond TTL + tolerance)
- Excessive delay in neighbor appearance (beyond 2× advertisement interval)
- Stale entries persist in neighbor table beyond TTL
- Neighbor table becomes corrupted or contains invalid data
- Duplicate or phantom neighbor entries appear
- Asymmetric behavior between DUTs
- Memory leaks are detected
- Memory or CPU usage grows unbounded
- System logs contain critical errors, segfaults, or assertion failures
- Neighbor table fails to converge after stabilization
- Show commands fail, hang, or return incorrect data
- Behavior is inconsistent across multiple flap cycles
- Resource exhaustion occurs
- Network performance degrades significantly

### Additional Notes

- **Rapid Flapping Definition**: Interface shutdown/no-shutdown operations performed with minimal delay (1-3 seconds) between iterations
- **Iteration Count**: Typically 15-20 rapid flaps per test phase
- **Link Detection Time**: Consider link detection delay in timing expectations
- **TTL Consideration**: Default LLDP TTL is typically 120 seconds (30s timer × 4 multiplier)
- **Advertisement Interval**: Default is typically 30 seconds
- **Stress Testing Focus**: This test specifically targets LLDP behavior under link instability
- **Physical vs Logical**: Interface shutdown is a logical operation but simulates physical link failure
- **Bidirectional Testing**: Both devices must be monitored for complete validation
- **Timing Windows**:
  - Neighbor withdrawal: Should occur within 1-5 seconds of interface down
  - Neighbor appearance: Should occur within 30-60 seconds of interface up (1-2 advertisement intervals)
- **Link State Detection**: System should detect link state changes quickly (typically < 1 second)
- **LLDP PDU Behavior**: PDUs should stop being sent/received when link is down
- **Recovery Verification**: System should fully recover to normal operation after flapping stops

### Test Variations

1. **Variable Flap Intervals**: Test with different delays (0s, 1s, 2s, 5s)
2. **Different Iteration Counts**: Test with 5, 10, 20, 50 iterations
3. **Asymmetric Flapping**: Flap interface on one side only
4. **Simultaneous Flapping**: Flap interfaces on both devices simultaneously
5. **Random Flap Patterns**: Vary the up/down times randomly
6. **Extended Down Time**: Test with longer down periods between flaps
7. **During High LLDP Traffic**: Perform flaps during active LLDP communication

### Related Test Cases

- **1.1.8**: Rapid enable/disable of LLDP (tests LLDP state changes)
- **1.1.5**: LLDP timers and multiplier (tests TTL behavior)
- **1.1.2**: LLDP neighbor discovery (tests basic neighbor functionality)

### Performance Expectations

- **Withdrawal Time**: < 5 seconds after interface down
- **Appearance Time**: 30-60 seconds after interface up (1-2 advertisement cycles)
- **TTL Expiry**: Exactly at configured TTL (with ±5 second tolerance)
- **System Response**: < 1 second for interface state change detection
- **Table Update**: < 2 seconds for table updates to reflect changes
