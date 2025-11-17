# Test Cases - Interface Events Validation (LAG/ECMP)

## Test Case ID: TC_INTF_EVENTS_002

### Test Case Name
Validate Propagation and Recovery in LAG/ECMP

### Test Objective
Validate that PortChannel (LAG) interface creation, member addition, and state changes are properly reflected in CLI outputs. Ensure that interface state transitions are accurately captured and displayed when interfaces are added to PortChannel groups.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Device Under Test**: smic_sonic1 (192.168.100.193)
- **Peer Device**: smic_sonic2 (192.168.100.195)
- **Test Interfaces**:
  - Ethernet0 (Primary test interface for PortChannel)
  - Ethernet4
  - Ethernet8
  - Ethernet12
- **PortChannel Interface**: PortChannel10
- **Connection Topology**:
  - smic_sonic1:Ethernet0 <---> smic_sonic2:Ethernet0
  - smic_sonic1:Ethernet4 <---> smic_sonic2:Ethernet4
  - smic_sonic1:Ethernet8 <---> smic_sonic2:Ethernet8
  - smic_sonic1:Ethernet12 <---> smic_sonic2:Ethernet12

### Prerequisites
1. Both devices (smic_sonic1 and smic_sonic2) must be accessible via SSH
2. User credentials: admin/YourPaSsWoRd
3. Access to sonic-cli and klish shell
4. Sufficient privileges to configure interfaces and PortChannels
5. No existing PortChannel10 configuration on the device

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

# Bring up Ethernet0
interface Ethernet0
no shutdown
exit

# Bring up Ethernet4
interface Ethernet4
no shutdown
exit

# Bring up Ethernet8
interface Ethernet8
no shutdown
exit

# Bring up Ethernet12
interface Ethernet12
no shutdown
exit

# Exit configuration mode
exit
```

**Expected Result**:
- All interfaces (Ethernet0, Ethernet4, Ethernet8, Ethernet12) should show administrative state as "up"
- Operational state should transition to "up" for all interfaces
- No errors during interface activation

---

### Step 2: Baseline Interface Status Check
**Objective**: Capture baseline interface status before PortChannel configuration

**Commands**:
```bash
# Enter sonic-cli (if not already in)
sonic-cli

# Check interface status
show interface status
```

**Expected Result**:
- All interfaces should display:
  - Admin Status: up
  - Oper Status: up
  - Speed and duplex information should be visible
- Output should be captured for baseline comparison

**Sample Output Format**:
```
Interface        Admin    Oper    Speed         Type              Description
--------------------------------------------------------------------------------------
Ethernet0        up       up      <speed>       <type>            <description>
Ethernet4        up       up      <speed>       <type>            <description>
Ethernet8        up       up      <speed>       <type>            <description>
Ethernet12       up       up      <speed>       <type>            <description>
```

---

### Step 3: Create PortChannel Interface
**Objective**: Create a PortChannel interface (PortChannel10) for LAG configuration

**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Create PortChannel10
interface PortChannel10
no shutdown
exit

# Exit configuration mode
exit

# Verify PortChannel creation
show interface PortChannel
```

**Expected Result**:
- PortChannel10 should be created successfully
- PortChannel10 should appear in the interface list
- Admin state should be "up"
- Oper state may be "down" initially (no members added yet)

**Sample Output Format**:
```
Interface        Admin    Oper    Members
-------------------------------------------------
PortChannel10    up       down    -
```

---

### Step 4: Add First Interface to PortChannel
**Objective**: Add Ethernet0 (first interface from testbed) as a member of PortChannel10

**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0 and add to PortChannel10
interface Ethernet0
channel-group 10 mode active
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Ethernet0 should be successfully added to PortChannel10
- No errors during channel-group configuration
- Interface should show association with PortChannel10

---

### Step 5: Validate PortChannel Status
**Objective**: Verify PortChannel status and member information after adding Ethernet0

**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Display PortChannel status
show interface PortChannel
```

**Expected Result**:
- PortChannel10 should show:
  - Admin Status: up
  - Oper Status: up (if peer is configured) or down (if peer is not configured)
  - Members: Ethernet0 should be listed as a member
- State transitions should be accurately reflected in the CLI output

**Sample Output Format**:
```
Interface        Admin    Oper    Members         Protocol
------------------------------------------------------------
PortChannel10    up       up      Ethernet0(S)    LACP
```

**Output Storage**:
- Store the output of "show interface PortChannel" command in a variable
- Display the stored output for validation
- Capture the following details:
  - PortChannel10 interface name
  - Admin state
  - Operational state
  - Member interface list
  - Protocol mode (LACP)

---

### Step 6: Detailed PortChannel Verification
**Objective**: Verify detailed PortChannel configuration and status

**Commands**:
```bash
# Enter sonic-cli
sonic-cli

# Display detailed PortChannel information
show interface PortChannel 10

# Display PortChannel summary
show interface PortChannel summary

# Verify interface status of member interface
show interface status Ethernet0
```

**Expected Result**:
- PortChannel10 details should show:
  - Interface configuration
  - Member interface status
  - LACP status (if applicable)
- Ethernet0 should show association with PortChannel10
- All CLI commands should execute without errors

---

## Validation Points

### CLI Validation (klish mode via sonic-cli)

**Primary Command**: `show interface PortChannel`

**Validation Criteria**:
1. **Interface Creation**:
   - PortChannel10 should be listed in the output
   - Interface should show correct naming convention

2. **State Transitions**:
   - Admin state should reflect configuration (up after "no shutdown")
   - Operational state should transition based on:
     - No members: down
     - With active members: up
     - Member link down: down/degraded

3. **Member Information**:
   - Ethernet0 should be listed as a member of PortChannel10
   - Member state should be indicated (e.g., Selected, Standby)
   - Member count should be accurate

4. **Protocol Information**:
   - Protocol mode should be displayed (LACP/Static)
   - LACP status should be shown if applicable

### State Transition Accuracy

**Expected State Transitions**:
```
1. Initial State (before member addition):
   - PortChannel10: Admin=up, Oper=down, Members=[]

2. After adding Ethernet0:
   - PortChannel10: Admin=up, Oper=up/down, Members=[Ethernet0]
   - Ethernet0: Admin=up, Oper=up, PortChannel=10

3. CLI Output Accuracy:
   - Immediate reflection of state changes
   - Consistent output across multiple queries
   - No stale or cached information
```

---

## Expected Overall Results

### Success Criteria
- All interfaces in testbed can be brought to "up" state successfully
- PortChannel10 is created without errors
- Ethernet0 is successfully added to PortChannel10 as a member
- CLI command "show interface PortChannel" accurately displays:
  - PortChannel interface status
  - Admin and operational states
  - Member interface information
- State transitions are reflected accurately and immediately in CLI output
- No crashes, errors, or unexpected behavior during configuration

### Performance Criteria
- PortChannel creation should complete within 2-3 seconds
- Member addition should complete within 2-3 seconds
- State transitions should be reflected in CLI within 1-2 seconds
- CLI commands should respond within acceptable time limits (< 5 seconds)
- No delays or timeouts during configuration operations

### Output Validation Criteria
- Output should be properly formatted and readable
- All required fields should be present (Interface, Admin, Oper, Members)
- State information should be consistent across multiple show commands
- Member list should accurately reflect configured members

---

## Test Execution Summary Template

| Step | Operation | Interface | Expected Admin | Expected Oper | CLI Accurate | Result |
|------|-----------|-----------|----------------|---------------|--------------|--------|
| 1    | Bring up all interfaces | Ethernet0,4,8,12 | up | up | Yes/No | Pass/Fail |
| 2    | Baseline check | All | up | up | Yes/No | Pass/Fail |
| 3    | Create PortChannel10 | PortChannel10 | up | down | Yes/No | Pass/Fail |
| 4    | Add Ethernet0 to PC10 | Ethernet0 | up | up | Yes/No | Pass/Fail |
| 5    | Verify PortChannel | PortChannel10 | up | up/down | Yes/No | Pass/Fail |
| 6    | Detailed verification | PortChannel10 | up | up/down | Yes/No | Pass/Fail |

---

## Cleanup Steps

After test completion, ensure proper cleanup:

```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Remove Ethernet0 from PortChannel10
interface Ethernet0
no channel-group 10
exit

# Delete PortChannel10
no interface PortChannel10

# Verify Ethernet0 is restored to standalone operation
exit

# Verify cleanup
show interface PortChannel
show interface status Ethernet0

# Exit sonic-cli
exit
```

**Cleanup Verification**:
- PortChannel10 should no longer appear in "show interface PortChannel"
- Ethernet0 should be operational as a standalone interface
- No residual PortChannel configuration should remain

---

## Test Environment Details

**Command Flow Reference**:
```
1. sonic-cli                          # Enter CLI (klish mode)
2. configure terminal                 # Enter config mode
3. interface Ethernet<num>            # Select interface
4. no shutdown                        # Activate interface
5. interface PortChannel<num>         # Create/select PortChannel
6. interface Ethernet<num>            # Select member interface
7. channel-group <num> mode <mode>    # Add to PortChannel
8. exit                               # Exit interface config
9. show interface PortChannel         # Verify PortChannel status
10. show interface status             # Verify interface status
```

**Testbed Interface Mapping** (from testbed_2vs.yaml):
```
smic_sonic1 Interfaces:
  - Ethernet0  → Connected to smic_sonic2:Ethernet0
  - Ethernet4  → Connected to smic_sonic2:Ethernet4
  - Ethernet8  → Connected to smic_sonic2:Ethernet8
  - Ethernet12 → Connected to smic_sonic2:Ethernet12
```

---

## Notes

1. All commands must be executed in **klish mode** via **sonic-cli**
2. The test uses **Ethernet0** as the first interface from the testbed for PortChannel member addition
3. PortChannel operational state depends on:
   - Member interface states
   - Peer device configuration (if LACP is used)
   - Link connectivity
4. If peer device (smic_sonic2) is not configured with corresponding PortChannel, the operational state may remain "down"
5. Store output of "show interface PortChannel" in a variable for detailed analysis
6. Document any anomalies, warnings, or unexpected behavior
7. Capture command outputs and logs for each step

---

## Additional Validation Commands

For comprehensive testing, consider executing these additional commands:

```bash
# LACP status (if LACP mode is used)
show lacp interface PortChannel10

# Detailed interface counters
show interface PortChannel 10 counters

# Interface description
show interface PortChannel 10 description

# Running configuration
show running-configuration interface PortChannel10
show running-configuration interface Ethernet0
```

---

## Troubleshooting

### Common Issues and Resolution

**Issue 1**: PortChannel10 operational state remains "down" after adding member
- **Cause**: Peer device not configured or link down
- **Resolution**: Verify peer device configuration and link connectivity

**Issue 2**: Cannot add Ethernet0 to PortChannel10
- **Cause**: Interface may already be part of another PortChannel or have conflicting configuration
- **Resolution**: Check existing channel-group configuration and remove if necessary

**Issue 3**: CLI commands not responding or timing out
- **Cause**: System resource issues or CLI session problems
- **Resolution**: Re-establish CLI session and retry commands

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Test ID**: 1.3.1
- **Test Category**: Interface Events - LAG/ECMP
- **Priority**: High
- **Automation**: Candidate for automation framework
- **Related Test Cases**: TC_INTF_EVENTS_001 (Admin/Link State Changes)

---

## Command Reference Summary

### Show Commands (klish mode)
```bash
show interface PortChannel              # Display all PortChannel interfaces
show interface PortChannel <num>        # Display specific PortChannel details
show interface PortChannel summary      # Display PortChannel summary
show interface status                   # Display all interface status
show interface status <interface>       # Display specific interface status
show lacp interface                     # Display LACP status (if applicable)
```

### Configuration Commands (klish mode)
```bash
interface PortChannel<num>              # Create/enter PortChannel config
interface Ethernet<num>                 # Enter interface config
channel-group <num> mode <mode>         # Add interface to PortChannel
no channel-group <num>                  # Remove interface from PortChannel
no interface PortChannel<num>           # Delete PortChannel
shutdown / no shutdown                  # Admin down/up interface
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-12
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.3.1 - Validate propagation and recovery in LAG/ECMP
