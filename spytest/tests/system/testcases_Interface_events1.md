# Test Cases - Interface Events Validation

## Test Case ID: TC_INTF_EVENTS_001

### Test Case Name
Validate CLI/syslog for Admin/Link State Changes

### Test Objective
Validate that interface administrative state changes (shutdown/no shutdown) are properly reflected in CLI outputs and system logs. Ensure state transitions are accurately captured and displayed through multiple cycles of interface state changes.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Device Under Test**: smic_sonic1 (192.168.100.193)
- **Peer Device**: smic_sonic2 (192.168.100.195)
- **Test Interface**: Ethernet4
- **Connection**: smic_sonic1:Ethernet4 <---> smic_sonic2:Ethernet4

### Prerequisites
1. Both devices (smic_sonic1 and smic_sonic2) must be accessible via SSH
2. User credentials: admin/YourPaSsWoRd
3. Access to sonic-cli and klish shell
4. Sufficient privileges to configure interfaces

---

## Test Procedure

### Step 1: Bring All Interfaces to UP State
**Objective**: Ensure all interfaces in the testbed are in operational "up" state

**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Bring up Ethernet4
interface Ethernet4
no shutdown
exit
```

**Expected Result**:
- All interfaces should show administrative state as "up"
- Operational state should transition to "up"

---

### Step 2: Baseline Interface Status Check
**Objective**: Capture baseline interface status before testing

**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status
```

**Expected Result**:
- Interface Ethernet4 should display:
  - Admin Status: up
  - Oper Status: up
  - Speed and duplex information should be visible
- Output should be captured for comparison

**Sample Output Format**:
```
Interface        Admin    Oper    Speed    Type    Description
-----------------------------------------------------------------
Ethernet4        up       up      <speed>  <type>  <description>
```

---

### Step 3: Validate Syslog Check
**Objective**: Verify syslog command functionality

**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Check system logs
show logging
```

**Note**: This command is currently not working as expected. Execute the command and store output in a variable for future validation when the feature is fixed.

**Expected Result**:
- Command should execute (even if output is not complete)
- Store output for baseline comparison

---

### Step 4: Interface Shutdown Test - Iteration 1
**Objective**: Verify interface transitions to "down" state on shutdown command

**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Shutdown Ethernet4
interface Ethernet4
shutdown
exit

# Verify interface status
show interface status

# Check syslog for shutdown event
show logging
```

**Expected Result**:
- Interface Ethernet4 should show:
  - Admin Status: down
  - Oper Status: down
- Syslog should contain entry indicating interface state change to down
- State transition should be immediate

---

### Step 5: Interface No Shutdown Test - Iteration 1
**Objective**: Verify interface recovers to "up" state on no shutdown command

**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Bring up Ethernet4
interface Ethernet4
no shutdown
exit

# Verify interface status
show interface status

# Check syslog for interface up event
show logging
```

**Expected Result**:
- Interface Ethernet4 should show:
  - Admin Status: up
  - Oper Status: up
- Syslog should contain entry indicating interface state change to up
- State transition should be successful
- Interface should recover to baseline state

---

### Step 6: Repeat Shutdown/No Shutdown Cycle - Iteration 2
**Objective**: Validate consistency of state transitions

**Commands**:
```bash
# Shutdown sequence
sonic-cli
configure terminal
interface Ethernet4
shutdown
exit
show interface status

# No shutdown sequence
configure terminal
interface Ethernet4
no shutdown
exit
show interface status
```

**Expected Result**:
- Interface state changes should be consistent with Iteration 1
- Down state should be achieved after shutdown
- Up state should be recovered after no shutdown

---

### Step 7: Repeat Shutdown/No Shutdown Cycle - Iteration 3
**Objective**: Validate consistency of state transitions

**Commands**: (Same as Step 6)

**Expected Result**:
- Interface state changes should remain consistent
- No anomalies in state transitions

---

### Step 8: Repeat Shutdown/No Shutdown Cycle - Iteration 4
**Objective**: Validate consistency of state transitions

**Commands**: (Same as Step 6)

**Expected Result**:
- Interface state changes should remain consistent across all iterations
- CLI outputs should accurately reflect current interface state
- No errors or unexpected behavior

---

## Validation Points

### CLI Validation
1. **show interface status** should accurately display:
   - Current admin state (up/down)
   - Current operational state (up/down)
   - State changes should be reflected immediately after configuration

2. State transition accuracy:
   - shutdown → Admin: down, Oper: down
   - no shutdown → Admin: up, Oper: up

### Syslog Validation (When feature is available)
1. Each shutdown event should be logged with timestamp
2. Each no shutdown event should be logged with timestamp
3. Log entries should include interface name and state change details

---

## Expected Overall Results

### Success Criteria
- All interfaces can be brought to "up" state successfully
- Shutdown command consistently changes interface state to "down"
- No shutdown command consistently recovers interface state to "up"
- State transitions are consistent across 4 iterations
- CLI commands accurately reflect interface states
- No crashes, errors, or unexpected behavior during state transitions

### Performance Criteria
- State transitions should occur within 2-3 seconds
- CLI commands should respond within acceptable time limits
- No delays or timeouts during configuration

---

## Test Execution Summary Template

| Iteration | Operation   | Admin State | Oper State | CLI Accurate | Syslog Entry | Result |
|-----------|-------------|-------------|------------|--------------|--------------|--------|
| Baseline  | -           | up          | up         | Yes          | -            | Pass   |
| 1         | shutdown    | down        | down       | Yes/No       | Yes/No       | Pass/Fail |
| 1         | no shutdown | up          | up         | Yes/No       | Yes/No       | Pass/Fail |
| 2         | shutdown    | down        | down       | Yes/No       | Yes/No       | Pass/Fail |
| 2         | no shutdown | up          | up         | Yes/No       | Yes/No       | Pass/Fail |
| 3         | shutdown    | down        | down       | Yes/No       | Yes/No       | Pass/Fail |
| 3         | no shutdown | up          | up         | Yes/No       | Yes/No       | Pass/Fail |
| 4         | shutdown    | down        | down       | Yes/No       | Yes/No       | Pass/Fail |
| 4         | no shutdown | up          | up         | Yes/No       | Yes/No       | Pass/Fail |

---

## Cleanup Steps

After test completion, ensure:
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
```

---

## Test Environment Details

**Command Flow Reference**:
```
1. sonic-cli                    # Enter CLI
2. configure terminal           # Enter config mode
3. interface Ethernet<num>      # Select interface
4. shutdown / no shutdown       # Execute command
5. exit                         # Exit interface config
6. show interface status        # Verify state
7. show logging                 # Check logs
```

---

## Notes
1. The "show logging" command is currently not functioning properly - execute anyway for future validation
2. All commands should be executed in klish mode via sonic-cli
3. Ensure both devices in testbed are operational before starting tests
4. Document any anomalies or unexpected behavior
5. Capture screenshots or logs for each iteration if possible

---

## References
- Testbed Configuration: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- Test ID: 1.1.10
- Test Category: Interface Events
- Priority: High
- Automation: Candidate for automation framework

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Author**: Test Engineering Team
**Status**: Ready for Execution
