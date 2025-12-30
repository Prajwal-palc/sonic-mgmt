# Test Cases - Interface Events Validation (CLI Admin/Link State Changes)

## Test Case ID: TC_INTF_EVENTS_CLI_001

### Test Case Name
Validate CLI for Admin/Link State Changes

### Test Objective
Validate that interface administrative state changes (shutdown/no shutdown) are accurately reflected in the CLI outputs, specifically in the `show interface status` command. Ensure that state transitions from up to down and down to up are correctly displayed in the Admin column of the interface status output. Verify that the interface responds properly to administrative state configuration commands and that the CLI reflects these changes immediately.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Device Under Test (DUT1)**: smic_sonic1 (192.168.100.107)
- **Peer Device (DUT2)**: smic_sonic2 (192.168.100.54)
- **Test Interfaces**:
  - Ethernet0 (Primary test interface)
  - Ethernet4
  - Ethernet8
  - Ethernet12
- **Connection**:
  - smic_sonic1:Ethernet0 <---> smic_sonic2:Ethernet0
  - smic_sonic1:Ethernet4 <---> smic_sonic2:Ethernet4
  - smic_sonic1:Ethernet8 <---> smic_sonic2:Ethernet8
  - smic_sonic1:Ethernet12 <---> smic_sonic2:Ethernet12
- **Topology**: 2 nodes

### Prerequisites
1. Both devices (smic_sonic1 and smic_sonic2) must be accessible via SSH
2. User credentials: admin/YourPaSsWoRd
3. Access to sonic-cli and klish shell
4. Sufficient privileges to configure interfaces
5. All test interfaces should be physically connected

---

## Test Procedure

### Step 1: Initial Configuration - Bring All Interfaces to UP State
**Objective**: Ensure all testbed interfaces are administratively up before testing state changes

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Set terminal length to prevent pagination
terminal length 0

# Enter configuration mode
configure terminal

# Bring up all interfaces from testbed
interface Ethernet0
no shutdown
exit

interface Ethernet4
no shutdown
exit

interface Ethernet8
no shutdown
exit

interface Ethernet12
no shutdown
exit

# Exit configuration mode
end
```

**Expected Result**:
- All testbed interfaces (Ethernet0, Ethernet4, Ethernet8, Ethernet12) configured with "no shutdown"
- Configuration commands accepted without errors
- Interfaces transition to administrative "up" state

---

### Step 2: Baseline Interface Status Check
**Objective**: Capture baseline interface status showing all interfaces in "up" state

**Commands (Execute on DUT1)**:
```bash
# In sonic-cli mode
show interface status
```

**Expected Result**:
- All testbed interfaces display "Admin" column as "up"
- Interface status output properly formatted
- All configured interfaces visible in the output

**Sample Output Format**:
```
-------------------------------------------------------------------------------------------------------------------------------------------
Name           Alias     Admin     Speed       MTU     Lanes                                   FEC   DHCP RL   Sub
-------------------------------------------------------------------------------------------------------------------------------------------
Ethernet0      fortyGigE0/0up        40000       9100    25,26,27,28                             -     300       -
Ethernet4      fortyGigE0/4up        40000       9100    29,30,31,32                             -     300       -
Ethernet8      fortyGigE0/8up        40000       9100    33,34,35,36                             -     300       -
Ethernet12     fortyGigE0/12up        40000       9100    37,38,39,40                             -     300       -
...
```

**Validation Point**: Admin column should show "up" for all test interfaces

---

### Step 3: Select Test Interface
**Objective**: Choose a single interface for detailed admin state testing

**Test Interface Selection**: Ethernet0 (from smic_sonic1)

**Rationale**:
- Ethernet0 is the first interface in the testbed topology
- Connected to smic_sonic2:Ethernet0
- Representative of interface behavior

---

### Step 4: Verify Interface is UP Before Admin State Change
**Objective**: Confirm test interface (Ethernet0) is administratively up

**Commands (Execute on DUT1)**:
```bash
# In sonic-cli mode
show interface status Ethernet0
```

**Expected Result**:
- Ethernet0 shows "Admin" column as "up"
- Interface operational and ready for testing
- Baseline state confirmed

**Sample Output**:
```
-------------------------------------------------------------------------------------------------------------------------------------------
Name           Alias     Admin     Speed       MTU     Lanes                                   FEC   DHCP RL   Sub
-------------------------------------------------------------------------------------------------------------------------------------------
Ethernet0      fortyGigE0/0up        40000       9100    25,26,27,28                             -     300       -
```

**Validation Point**: Admin = "up"

---

### Step 5: Administratively Shutdown Test Interface
**Objective**: Change interface administrative state from up to down

**Commands (Execute on DUT1)**:
```bash
# In sonic-cli mode
# Enter configuration mode
configure terminal

# Select test interface
interface Ethernet0

# Administratively shutdown the interface
shutdown

# Exit interface configuration
end
```

**Expected Result**:
- "shutdown" command accepted without errors
- Configuration applied successfully
- Interface transitions to administrative "down" state

---

### Step 6: Verify Interface is DOWN in CLI Output
**Objective**: Validate that CLI accurately reflects administrative down state

**Commands (Execute on DUT1)**:
```bash
# In sonic-cli mode
show interface status
```

**Expected Result**:
- Ethernet0 shows "Admin" column as "down"
- Other interfaces remain "up"
- State change reflected accurately in CLI output

**Sample Output**:
```
-------------------------------------------------------------------------------------------------------------------------------------------
Name           Alias     Admin     Speed       MTU     Lanes                                   FEC   DHCP RL   Sub
-------------------------------------------------------------------------------------------------------------------------------------------
Ethernet0      fortyGigE0/0down      40000       9100    25,26,27,28                             -     300       -
Ethernet4      fortyGigE0/4up        40000       9100    29,30,31,32                             -     300       -
Ethernet8      fortyGigE0/8up        40000       9100    33,34,35,36                             -     300       -
Ethernet12     fortyGigE0/12up        40000       9100    37,38,39,40                             -     300       -
...
```

**Validation Points**:
1. Ethernet0 Admin = "down" (changed from "up")
2. Other interfaces Admin = "up" (unchanged)
3. CLI reflects state transition accurately

---

### Step 7: Verify Specific Interface Status
**Objective**: Confirm down state by checking specific interface

**Commands (Execute on DUT1)**:
```bash
# In sonic-cli mode
show interface status Ethernet0
```

**Expected Result**:
- Ethernet0 specifically shows "Admin" as "down"
- State change confirmed in targeted query

**Sample Output**:
```
-------------------------------------------------------------------------------------------------------------------------------------------
Name           Alias     Admin     Speed       MTU     Lanes                                   FEC   DHCP RL   Sub
-------------------------------------------------------------------------------------------------------------------------------------------
Ethernet0      fortyGigE0/0down      40000       9100    25,26,27,28                             -     300       -
```

**Validation Point**: Admin column displays "down"

---

### Step 8: Bring Interface Back UP (No Shutdown)
**Objective**: Change interface administrative state from down back to up

**Commands (Execute on DUT1)**:
```bash
# In sonic-cli mode
# Enter configuration mode
configure terminal

# Select test interface
interface Ethernet0

# Administratively enable the interface
no shutdown

# Exit interface configuration
end
```

**Expected Result**:
- "no shutdown" command accepted without errors
- Configuration applied successfully
- Interface transitions to administrative "up" state

---

### Step 9: Verify Interface is UP Again in CLI Output
**Objective**: Validate that CLI accurately reflects administrative up state after re-enabling

**Commands (Execute on DUT1)**:
```bash
# In sonic-cli mode
show interface status
```

**Expected Result**:
- Ethernet0 shows "Admin" column as "up"
- State restored to original baseline
- CLI reflects up transition accurately

**Sample Output**:
```
-------------------------------------------------------------------------------------------------------------------------------------------
Name           Alias     Admin     Speed       MTU     Lanes                                   FEC   DHCP RL   Sub
-------------------------------------------------------------------------------------------------------------------------------------------
Ethernet0      fortyGigE0/0up        40000       9100    25,26,27,28                             -     300       -
Ethernet4      fortyGigE0/4up        40000       9100    29,30,31,32                             -     300       -
Ethernet8      fortyGigE0/8up        40000       9100    33,34,35,36                             -     300       -
Ethernet12     fortyGigE0/12up        40000       9100    37,38,39,40                             -     300       -
...
```

**Validation Points**:
1. Ethernet0 Admin = "up" (restored from "down")
2. State transition from down to up successful
3. CLI accurately displays current administrative state

---

### Step 10: Verify Specific Interface Status After Re-enable
**Objective**: Confirm up state by checking specific interface

**Commands (Execute on DUT1)**:
```bash
# In sonic-cli mode
show interface status Ethernet0
```

**Expected Result**:
- Ethernet0 specifically shows "Admin" as "up"
- Full state cycle (up → down → up) completed successfully

**Sample Output**:
```
-------------------------------------------------------------------------------------------------------------------------------------------
Name           Alias     Admin     Speed       MTU     Lanes                                   FEC   DHCP RL   Sub
-------------------------------------------------------------------------------------------------------------------------------------------
Ethernet0      fortyGigE0/0up        40000       9100    25,26,27,28                             -     300       -
```

**Validation Point**: Admin column displays "up"

---

### Step 11: Final State Verification - All Interfaces UP
**Objective**: Ensure all testbed interfaces are in administrative up state

**Commands (Execute on DUT1)**:
```bash
# In sonic-cli mode
# Enter configuration mode
configure terminal

# Ensure all testbed interfaces are administratively up
interface Ethernet0
no shutdown
exit

interface Ethernet4
no shutdown
exit

interface Ethernet8
no shutdown
exit

interface Ethernet12
no shutdown
exit

# Exit configuration mode
end

# Verify final state
show interface status
```

**Expected Result**:
- All testbed interfaces display "Admin" as "up"
- System restored to baseline state
- All interfaces operational

**Sample Output**:
```
-------------------------------------------------------------------------------------------------------------------------------------------
Name           Alias     Admin     Speed       MTU     Lanes                                   FEC   DHCP RL   Sub
-------------------------------------------------------------------------------------------------------------------------------------------
Ethernet0      fortyGigE0/0up        40000       9100    25,26,27,28                             -     300       -
Ethernet4      fortyGigE0/4up        40000       9100    29,30,31,32                             -     300       -
Ethernet8      fortyGigE0/8up        40000       9100    33,34,35,36                             -     300       -
Ethernet12     fortyGigE0/12up        40000       9100    37,38,39,40                             -     300       -
...
```

**Validation Points**:
1. All test interfaces Admin = "up"
2. Configuration consistent across all interfaces
3. Test environment ready for subsequent tests

---

## Validation Points

### CLI Validation (klish mode via sonic-cli)

**Primary Command**: `show interface status`

**Validation Criteria**:

#### 1. Admin State Transitions
- **Initial State (Step 2)**:
  - Ethernet0 Admin = "up"
  - Baseline established

- **After Shutdown (Step 6)**:
  - Ethernet0 Admin = "down"
  - State transition reflected in CLI
  - Change happens within seconds

- **After No Shutdown (Step 9)**:
  - Ethernet0 Admin = "up"
  - State restored to up
  - CLI reflects current state accurately

#### 2. CLI Output Accuracy
- Admin column correctly displays "up" or "down"
- State changes reflected immediately or within 1-2 seconds
- Other interface parameters remain unchanged during admin state changes
- Only the targeted interface's admin state changes

#### 3. Configuration Command Success
- "shutdown" command executes without errors
- "no shutdown" command executes without errors
- Configuration mode transitions work properly
- Commands accepted and applied successfully

#### 4. CLI Consistency
- `show interface status` (all interfaces) shows correct state
- `show interface status Ethernet0` (specific interface) shows correct state
- Both commands display consistent information
- Output format remains stable

---

## Expected Overall Results

### Success Criteria

#### 1. Interface State Control
- Interface administrative state can be changed via CLI commands
- "shutdown" transitions interface to admin down
- "no shutdown" transitions interface to admin up
- State changes apply successfully

#### 2. CLI Reflection Accuracy
- `show interface status` accurately displays admin state
- "Admin" column shows "up" when interface has "no shutdown" configured
- "Admin" column shows "down" when interface has "shutdown" configured
- CLI output updates within 1-2 seconds of configuration change

#### 3. State Transition Completeness
- Full cycle tested: up → down → up
- Each transition successful
- No stuck states or transition failures
- Interface responds to all admin commands

#### 4. Configuration Isolation
- Admin state changes affect only targeted interface
- Other interfaces maintain their current state
- No unintended side effects
- Configuration changes are interface-specific

### Performance Criteria

- **Configuration Application Time**: < 1 second
- **CLI Update Time**: 1-2 seconds for state to reflect in show commands
- **Command Response**: Immediate acceptance of shutdown/no shutdown commands
- **State Transition**: Smooth, no errors

### Failure Indicators

**Test should fail if**:
1. "shutdown" command does not change Admin state to "down"
2. "no shutdown" command does not change Admin state to "up"
3. CLI shows incorrect admin state after configuration change
4. State changes take longer than 5 seconds to reflect in CLI
5. Configuration commands are rejected or produce errors
6. Admin state changes affect other interfaces unexpectedly
7. Interface gets stuck in transitional state
8. CLI output is inconsistent between general and specific queries
9. System becomes unresponsive during state changes
10. Configuration changes do not persist

---

## Test Execution Summary Template

### Admin State Transition Verification

| Step | Interface | Command | Expected Admin State | Actual Admin State | Result |
|------|-----------|---------|---------------------|-------------------|--------|
| 2 | Ethernet0 | (initial) | up | | Pass/Fail |
| 5 | Ethernet0 | shutdown | down | | Pass/Fail |
| 9 | Ethernet0 | no shutdown | up | | Pass/Fail |

### CLI Command Validation

| Command | Interface | Executed Successfully | State Reflected in CLI | Response Time | Result |
|---------|-----------|----------------------|----------------------|---------------|--------|
| shutdown | Ethernet0 | Pass/Fail | Pass/Fail | < 5 sec | Pass/Fail |
| no shutdown | Ethernet0 | Pass/Fail | Pass/Fail | < 5 sec | Pass/Fail |

### Interface Isolation Check

| Test Interface | Other Interface | Other Interface State Changed | Result |
|----------------|-----------------|------------------------------|--------|
| Ethernet0 | Ethernet4 | No | Pass/Fail |
| Ethernet0 | Ethernet8 | No | Pass/Fail |
| Ethernet0 | Ethernet12 | No | Pass/Fail |

---

## Cleanup Steps

After test completion, ensure all interfaces are in operational state:

```bash
# Enter sonic-cli
sonic-cli

# Set terminal length
terminal length 0

# Enter configuration mode
configure terminal

# Ensure all testbed interfaces are up
interface Ethernet0
no shutdown
exit

interface Ethernet4
no shutdown
exit

interface Ethernet8
no shutdown
exit

interface Ethernet12
no shutdown
exit

# Exit configuration mode
end

# Verify final state
show interface status

# Exit sonic-cli
exit
```

**Cleanup Verification**:
- All testbed interfaces show Admin = "up"
- No interfaces in shutdown state
- System ready for next test
- Configuration clean

---

## Test Environment Details

**Command Flow Reference**:
```
1. sonic-cli                    # Enter CLI (klish mode)
2. terminal length 0            # Disable pagination
3. configure terminal           # Enter config mode
4. interface Ethernet<num>      # Select interface
5. shutdown / no shutdown       # Change admin state
6. end                          # Exit to exec mode
7. show interface status        # Verify admin state
```

**Topology Diagram**:
```
+--------------------+                       +--------------------+
|       DUT1         |                       |       DUT2         |
| (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
| 192.168.100.107    | (Admin State Tests)   | 192.168.100.54     |
|                    |<-----Ethernet4------->|                    |
|                    |<-----Ethernet8------->|                    |
|                    |<-----Ethernet12------>|                    |
+--------------------+                       +--------------------+
```

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **Admin State vs Operational State**:
   - **Admin State**: Configured state (up/down via shutdown/no shutdown)
   - **Operational State**: Actual link state (depends on physical connection and admin state)
   - This test validates Admin state reflection in CLI
   - Interface must be admin "up" to be operationally "up"

3. **Command Syntax**:
   - `shutdown`: Administratively disables interface
   - `no shutdown`: Administratively enables interface
   - Commands executed in interface configuration mode
   - `end` returns to exec mode, `exit` exits current mode level

4. **CLI Output Columns**:
   - **Name**: Interface name (Ethernet0, Ethernet4, etc.)
   - **Alias**: Port alias (fortyGigE0/0, etc.)
   - **Admin**: Administrative state (up/down) - **THIS IS THE KEY COLUMN FOR THIS TEST**
   - **Speed**: Interface speed in Mbps
   - **MTU**: Maximum Transmission Unit
   - **Lanes**: Physical lanes used
   - **FEC**: Forward Error Correction status
   - **DHCP RL**: DHCP Relay configuration
   - **Sub**: Sub-interface indicator

5. **Test Focus**:
   - Primary focus: **Admin column accuracy**
   - Verify admin state transitions: up ↔ down
   - Ensure CLI reflects configured administrative state
   - Configuration commands execute successfully

6. **Expected Behavior**:
   - Interface admin state is independent of operational state
   - Admin "down" will cause operational "down"
   - Admin "up" allows interface to come operationally "up" (if physical link is good)
   - CLI should immediately reflect admin state changes

7. **Testbed Interface List** (from testbed_2vs.yaml):
   - **smic_sonic1** interfaces: Ethernet0, Ethernet4, Ethernet8, Ethernet12
   - **smic_sonic2** interfaces: Ethernet0, Ethernet4, Ethernet8, Ethernet12
   - **Connections**:
     - smic_sonic1:Ethernet0 ↔ smic_sonic2:Ethernet0
     - smic_sonic1:Ethernet4 ↔ smic_sonic2:Ethernet4
     - smic_sonic1:Ethernet8 ↔ smic_sonic2:Ethernet8
     - smic_sonic1:Ethernet12 ↔ smic_sonic2:Ethernet12

8. **Command Mode Context**:
   ```
   sonic#                          # Exec mode (show commands)
   sonic(config)#                  # Global configuration mode
   sonic(config-if-Ethernet0)#     # Interface configuration mode
   ```

9. **State Transition Timeline**:
   ```
   Initial State:     Ethernet0 Admin = up
   After Shutdown:    Ethernet0 Admin = down
   After No Shutdown: Ethernet0 Admin = up
   Final State:       All interfaces Admin = up
   ```

10. **Testing Philosophy**:
    - Test one interface (Ethernet0) in detail for state transitions
    - Verify other interfaces are not affected
    - Restore all interfaces to "up" state at end
    - Ensure clean test environment for subsequent tests

---

## Additional Validation Commands

For comprehensive verification:

```bash
# View all interfaces
show interface status

# View specific interface
show interface status Ethernet0

# View detailed interface information
show interface Ethernet0

# View running configuration
show running-configuration interface Ethernet0

# View interface counters (verify no unexpected errors)
show interface counters
```

---

## Troubleshooting

### Common Issues and Resolution

**Issue 1**: Admin state doesn't change after shutdown/no shutdown
- **Cause**: Command not applied or syntax error
- **Resolution**:
  - Verify you are in interface configuration mode
  - Re-enter command with correct syntax
  - Check for error messages
  - Verify interface name is correct

**Issue 2**: CLI shows old state after configuration change
- **Cause**: CLI output not refreshed or delay in state propagation
- **Resolution**:
  - Wait 2-3 seconds and re-run show command
  - Check if configuration was actually applied
  - Verify running configuration
  - If persistent, check for software issues

**Issue 3**: Cannot enter interface configuration mode
- **Cause**: Incorrect interface name or insufficient privileges
- **Resolution**:
  - Verify interface name exists: `show interface status`
  - Check user privileges
  - Ensure correct command syntax: `interface Ethernet0`

**Issue 4**: shutdown command rejected
- **Cause**: Interface in use by critical service or syntax error
- **Resolution**:
  - Check for management interface restrictions
  - Verify command syntax
  - Check interface dependencies
  - Review error message for specific cause

**Issue 5**: Other interfaces affected by admin state change
- **Cause**: Incorrect interface selected or port-channel/VLAN configuration
- **Resolution**:
  - Verify correct interface in configuration mode
  - Check for port-channel membership
  - Check for VLAN configuration
  - Review interface dependencies

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Interface Status Commands**:
```bash
show interface status                      # Display all interface status
show interface status Ethernet<num>        # Display specific interface status
show interface Ethernet<num>               # Display detailed interface info
show running-configuration interface Ethernet<num>  # Display interface config
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**Admin State Configuration**:
```bash
sonic-cli                                  # Enter klish mode
terminal length 0                          # Disable pagination
configure terminal                         # Enter configuration mode
interface Ethernet<num>                    # Enter interface configuration

# Admin state commands
shutdown                                   # Administratively disable interface
no shutdown                                # Administratively enable interface

end                                        # Exit to exec mode
exit                                       # Exit current mode level
```

**Complete Command Sequence**:
```bash
# To shutdown interface
sonic-cli
configure terminal
interface Ethernet0
shutdown
end
show interface status Ethernet0

# To enable interface
configure terminal
interface Ethernet0
no shutdown
end
show interface status Ethernet0
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-26
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.1.1 - Validate CLI for admin/link state changes
