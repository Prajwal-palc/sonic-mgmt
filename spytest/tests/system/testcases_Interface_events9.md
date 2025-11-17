# Test Cases - Interface Events Validation (Speed Changes)

## Test Case ID: TC_INTF_EVENTS_009

### Test Case Name
Validate Interface Speed Changes

### Test Objective
Validate that interface speed can be changed to various supported values and that the configuration changes are accurately reflected in CLI outputs. Ensure that speed modifications (including auto-negotiation, fixed speeds like 10G, 1G, 100M, etc.) are properly applied, displayed in interface status, and persist across configuration changes. Verify that the interface remains operational after speed changes and that the new speed is correctly negotiated or applied.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Device Under Test (DUT1)**: smic_sonic1 (192.168.100.193)
- **Peer Device (DUT2)**: smic_sonic2 (192.168.100.195)
- **Test Interfaces**:
  - Ethernet0 (Primary test interface)
  - Ethernet4 (Secondary test interface)
- **Connection**:
  - smic_sonic1:Ethernet0 <---> smic_sonic2:Ethernet0
  - smic_sonic1:Ethernet4 <---> smic_sonic2:Ethernet4
- **Topology**: 2 nodes

### Prerequisites
1. Both devices (smic_sonic1 and smic_sonic2) must be accessible via SSH
2. User credentials: admin/YourPaSsWoRd
3. Access to sonic-cli and klish shell
4. Sufficient privileges to configure interfaces
5. Interfaces support multiple speed configurations
6. Understanding of interface capabilities (not all speeds supported on all interfaces)
7. Physical medium (cable) supports intended speeds

---

## Test Procedure

### Step 1: Initial Configuration - Bring Interface to UP State
**Objective**: Ensure test interfaces are in operational "up" state before testing speed changes

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

### Step 2: Baseline Interface Status Check
**Objective**: Capture baseline interface status before changing speeds

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status

# Check specific interface status
show interface status Ethernet0
show interface status Ethernet4

# Check detailed interface information
show interface Ethernet0
show interface Ethernet4
```

**Expected Result**:
- Interfaces display current speed configuration
- Current duplex mode displayed
- Baseline speed configuration captured
- Output stored for comparison

**Sample Output Format**:
```
Interface        Admin    Oper    Speed         Duplex    Type              Description
------------------------------------------------------------------------------------------
Ethernet0        up       up      10G           full      QSFP28            <description>
Ethernet4        up       up      10G           full      QSFP28            <description>
```

**Note**: Record baseline speeds for later restoration

---

### Step 3: Change Speed to Auto on Ethernet0
**Objective**: Configure interface speed to auto-negotiation mode

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Configure speed auto
speed auto

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Speed auto configuration accepted without errors
- Configuration applied successfully
- No error messages

---

### Step 4: Verify Speed Change to Auto on Ethernet0
**Objective**: Verify that speed change to auto is reflected in CLI output

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows speed as "auto"
- Interface operational state maintained
- CLI output accurate and consistent
- Speed change reflected immediately

**Sample Output**:
```
Interface        Admin    Oper    Speed         Duplex    Type              Description
------------------------------------------------------------------------------------------
Ethernet0        up       up      auto          auto      QSFP28            <description>
```

**Validation Points**:
1. Speed field shows "auto" or negotiated speed
2. Interface remains operational
3. Configuration change successful

---

### Step 5: Change Speed to 10G (Fixed) on Ethernet0
**Objective**: Change interface speed to fixed 10G

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Configure speed 10G (10000 Mbps)
speed 10000

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Speed 10G configuration accepted
- Configuration applied successfully
- No errors

**Note**: The speed value 10000 represents 10000 Mbps (10 Gigabit)

---

### Step 6: Verify Speed Change to 10G on Ethernet0
**Objective**: Verify that speed change to 10G is reflected in CLI output

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0

# Wait a few seconds for speed to stabilize
# Check again
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows speed as "10G" or "10000"
- Interface operational state is "up"
- Link establishes at 10G speed
- CLI output accurate

**Sample Output**:
```
Interface        Admin    Oper    Speed         Duplex    Type              Description
------------------------------------------------------------------------------------------
Ethernet0        up       up      10G           full      QSFP28            <description>
```

**Validation Points**:
1. Speed field shows "10G" or "10000"
2. Interface operational after speed change
3. Link stable at new speed

---

### Step 7: Change Speed to 1G on Ethernet0 (If Supported)
**Objective**: Change interface speed to 1G (if interface supports it)

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Configure speed 1G (1000 Mbps)
speed 1000

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Speed 1G configuration accepted (if supported)
- Configuration applied successfully
- OR: Error message if speed not supported (acceptable - document this)

**Note**: Not all interfaces support all speed values. High-speed interfaces (10G+) may not support 1G.

---

### Step 8: Verify Speed Change to 1G on Ethernet0
**Objective**: Verify speed change to 1G (if supported)

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result** (if 1G is supported):
- Interface status shows speed as "1G" or "1000"
- Interface operational state is "up"
- Link establishes at 1G speed

**Expected Result** (if 1G is NOT supported):
- Interface may show error or remain at previous speed
- Document that this speed is not supported for this interface type

**Sample Output** (if supported):
```
Interface        Admin    Oper    Speed         Duplex    Type              Description
------------------------------------------------------------------------------------------
Ethernet0        up       up      1G            full      QSFP28            <description>
```

---

### Step 9: Change Speed to 100M on Ethernet0 (If Supported)
**Objective**: Change interface speed to 100M (if interface supports it)

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Configure speed 100M (100 Mbps)
speed 100

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Speed 100M configuration accepted (if supported)
- Configuration applied successfully
- OR: Error message if speed not supported (acceptable)

**Note**: High-speed interfaces typically do NOT support 100M. This test may fail, which is expected behavior.

---

### Step 10: Verify Speed Change to 100M on Ethernet0
**Objective**: Verify speed change to 100M (if supported) or error handling

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- If supported: Interface shows speed as "100M" or "100"
- If NOT supported: Interface maintains previous speed or shows error
- Document interface speed capabilities

---

### Step 11: Restore Speed to Baseline on Ethernet0
**Objective**: Restore interface to original/default speed configuration

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Restore to original speed (example: 10G)
speed 10000

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Interface restored to baseline/default speed
- Interface operational
- Link re-establishes

---

### Step 12: Test Speed Changes on Ethernet4
**Objective**: Verify speed changes work on multiple interfaces

**Commands (Execute on DUT1)**:
```bash
# Test sequence on Ethernet4
sonic-cli
configure terminal

# Test 1: Change to auto
interface Ethernet4
speed auto
exit
exit

# Verify
show interface status Ethernet4

# Test 2: Change to 10G
configure terminal
interface Ethernet4
speed 10000
exit
exit

# Verify
show interface status Ethernet4
```

**Expected Result**:
- Speed changes apply successfully on Ethernet4
- Each change reflected in CLI output
- Interface remains operational through changes

---

### Step 13: Rapid Speed Changes Test
**Objective**: Test system stability during rapid speed changes

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Rapid speed changes on Ethernet0
configure terminal
interface Ethernet0
speed auto
speed 10000
speed auto
speed 10000
exit
exit

# Verify final state
show interface status Ethernet0
```

**Expected Result**:
- System handles rapid speed changes
- Final speed configuration is correct
- No system instability
- Interface operational

---

### Step 14: Speed Change with Link Flap
**Objective**: Verify speed configuration persists through interface flap

**Commands (Execute on DUT1)**:
```bash
# Configure specific speed
sonic-cli
configure terminal
interface Ethernet0
speed 10000
exit
exit

# Verify speed
show interface status Ethernet0

# Flap the interface
configure terminal
interface Ethernet0
shutdown
no shutdown
exit
exit

# Verify speed persists
show interface status Ethernet0
```

**Expected Result**:
- Speed configuration persists through interface flap
- Interface comes back up with configured speed
- No need to reconfigure speed after flap

---

### Step 15: Verify Multiple Speed Changes in Sequence
**Objective**: Validate that multiple sequential speed changes work correctly

**Test Sequence**:
1. Change to auto
2. Verify auto
3. Change to 10G
4. Verify 10G
5. Change to auto
6. Verify auto
7. Restore to 10G
8. Verify 10G

**Commands (Execute on DUT1)**:
```bash
# Sequence of speed changes
sonic-cli

# Change 1: auto
configure terminal
interface Ethernet0
speed auto
exit
exit
show interface status Ethernet0

# Change 2: 10G
configure terminal
interface Ethernet0
speed 10000
exit
exit
show interface status Ethernet0

# Change 3: auto
configure terminal
interface Ethernet0
speed auto
exit
exit
show interface status Ethernet0

# Change 4: 10G (restore)
configure terminal
interface Ethernet0
speed 10000
exit
exit
show interface status Ethernet0
```

**Expected Result**:
- Each speed change applies successfully
- Each change reflected in CLI output
- Interface operational after each change
- No accumulated errors or instability

---

### Step 16: Verify Configuration Persistence
**Objective**: Verify that speed configuration is saved in running configuration

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check running configuration
show running-configuration interface Ethernet0
show running-configuration interface Ethernet4
```

**Expected Result**:
- Running configuration shows current speed settings
- Configuration accurately reflects applied changes
- No discrepancies between applied and saved configuration

**Sample Output**:
```
interface Ethernet0
 speed 10000
 no shutdown
!
```

---

### Step 17: Test Invalid Speed Value Handling
**Objective**: Verify proper error handling for invalid speed values

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Try invalid speed value
interface Ethernet0
speed 12345  # Invalid speed value
exit
exit

# Verify interface state unchanged
show interface status Ethernet0
```

**Expected Result**:
- Invalid speed value rejected with error message
- Interface maintains previous speed configuration
- System handles error gracefully
- No impact on interface operational status

---

### Step 18: Final State Verification
**Objective**: Verify system is in clean state after all speed change tests

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify final interface status
show interface status

# Check specific interfaces
show interface status Ethernet0
show interface status Ethernet4

# Verify no error conditions
show logging | grep -i error | tail -20

# Verify interfaces operational
show interface Ethernet0
show interface Ethernet4
```

**Expected Result**:
- All interfaces in expected state
- No residual error conditions
- All CLI commands responsive
- System stable after all configuration changes
- Interfaces operational with correct speeds

---

## Validation Points

### CLI Validation (klish mode via sonic-cli)

**Primary Command**: `show interface status`

**Validation Criteria**:

#### 1. Speed Change Reflection
- **After speed change command**:
  - Speed field in `show interface status` matches configured value
  - Change reflected immediately or within seconds
  - CLI output accurate and consistent

#### 2. Supported Speed Values
Common speed values to test:
- `speed auto` - Auto-negotiation
- `speed 10` - 10 Mbps
- `speed 100` - 100 Mbps (Fast Ethernet)
- `speed 1000` - 1 Gbps (Gigabit Ethernet)
- `speed 10000` - 10 Gbps
- `speed 25000` - 25 Gbps
- `speed 40000` - 40 Gbps
- `speed 100000` - 100 Gbps

**Note**: Actual supported speeds depend on interface hardware type

#### 3. Interface Stability After Speed Change
- Interface operational state maintained or quickly recovers
- Link re-establishes at new speed
- No continuous flapping
- Stable operation at new speed

#### 4. Configuration Accuracy
- CLI output matches configured speed
- Running configuration shows speed setting
- No discrepancies between configuration and status
- Configuration persists through interface flaps

#### 5. Error Handling
- Invalid speed values rejected with clear error messages
- Unsupported speeds handled gracefully
- Interface maintains previous configuration on error
- System remains stable after error

---

## Expected Overall Results

### Success Criteria

#### 1. Speed Configuration Success
- Speed change commands execute successfully for supported speeds
- Configuration applies immediately or within seconds
- CLI reflects new speed configuration
- Running configuration shows speed setting

#### 2. Interface Operational Continuity
- Interface remains operational after speed changes
- Link re-establishes at new speed (if different from previous)
- No permanent link loss
- Stable operation at configured speed

#### 3. CLI Accuracy
- `show interface status` accurately displays configured speed
- Speed value matches what was configured
- All interface parameters correctly displayed
- No inconsistencies in CLI output

#### 4. Configuration Persistence
- Speed configuration persists through interface flaps
- Configuration saved in running-config
- Speed maintained across admin state changes
- No need to reconfigure after interface recovery

#### 5. System Stability
- System handles speed changes without issues
- Multiple speed changes don't cause instability
- Rapid speed changes handled gracefully
- No system crashes or hangs
- Resources (CPU, memory) remain stable

#### 6. Error Handling
- Invalid speeds rejected with appropriate errors
- Unsupported speeds handled gracefully
- Clear error messages provided
- System recovers from error conditions

### Performance Criteria

- **Configuration Application Time**: < 2 seconds
- **Link Re-establishment Time**: 5-30 seconds (depends on speed)
- **CLI Response Time**: < 5 seconds for show commands
- **Speed Transition**: Smooth with minimal packet loss
- **Configuration Persistence**: Immediate in running-config

### Failure Indicators

**Test should fail if**:
1. Supported speed commands rejected
2. CLI does not show configured speed
3. Interface fails to come up after speed change
4. Speed configuration does not persist through flaps
5. Multiple speed changes cause system instability
6. Invalid speeds accepted without error
7. Running configuration does not reflect speed changes
8. Interface becomes permanently down after speed change
9. System crashes or becomes unresponsive
10. CLI output is incorrect or inconsistent

---

## Test Execution Summary Template

### Speed Change Verification

| Interface | Initial Speed | Changed To | Verified Speed | Link Status | Result |
|-----------|---------------|------------|----------------|-------------|--------|
| Ethernet0 | 10G | auto | auto/negotiated | up | Pass/Fail |
| Ethernet0 | auto | 10G | 10G | up | Pass/Fail |
| Ethernet0 | 10G | 1G | 1G/error | up/down | Pass/Fail |
| Ethernet0 | 1G | 100M | 100M/error | up/down | Pass/Fail |
| Ethernet4 | 10G | auto | auto/negotiated | up | Pass/Fail |
| Ethernet4 | auto | 10G | 10G | up | Pass/Fail |

### Sequential Speed Changes

| Sequence | Speed Changes | Final Speed | Final Status | Result |
|----------|---------------|-------------|--------------|--------|
| 1 | auto → 10G → auto → 10G | 10G | up | Pass/Fail |
| 2 | 10G → auto → 10G | 10G | up | Pass/Fail |
| Rapid | auto,10G,auto,10G (rapid) | 10G | up | Pass/Fail |

### Persistence Validation

| Test | Speed Config | After Flap | Running Config | Result |
|------|--------------|------------|----------------|--------|
| Interface Flap | 10G | 10G | speed 10000 | Pass/Fail |
| Multiple Changes | auto | auto | speed auto | Pass/Fail |

### Error Handling

| Invalid Speed | Error Displayed | Interface Status | Result |
|---------------|-----------------|------------------|--------|
| 12345 | Yes/No | Unchanged | Pass/Fail |
| 999999 | Yes/No | Unchanged | Pass/Fail |

---

## Cleanup Steps

After test completion, restore interfaces to desired state:

```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Restore Ethernet0 to default/baseline speed
interface Ethernet0
speed 10000  # Or desired default speed
no shutdown
exit

# Restore Ethernet4 to default/baseline speed
interface Ethernet4
speed 10000  # Or desired default speed
no shutdown
exit

# Exit configuration mode
exit

# Verify final state
show interface status

# Exit sonic-cli
exit
```

**Cleanup Verification**:
- Interfaces at desired final speed
- All interfaces operational
- No residual error conditions
- System stable

---

## Test Environment Details

**Command Flow Reference**:
```
1. sonic-cli                    # Enter CLI (klish mode)
2. configure terminal           # Enter config mode
3. interface Ethernet<num>      # Select interface
4. speed <value>                # Change speed (auto, 10000, 1000, 100, etc.)
5. exit                         # Exit interface config
6. exit                         # Exit config mode
7. show interface status        # Verify speed change
8. (repeat for different speed values)
```

**Topology Diagram**:
```
+--------------------+                       +--------------------+
|       DUT1         |                       |       DUT2         |
| (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
| 192.168.100.193    |   (Speed Changes)     | 192.168.100.195    |
|                    |<-----Ethernet4------->|                    |
|                    |   (Speed Changes)     |                    |
+--------------------+                       +--------------------+
```

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **Interface Speed Capabilities**:
   - Not all interfaces support all speed values
   - High-speed interfaces (10G+) may not support low speeds (100M, 1G)
   - Copper interfaces typically support more speed options than optical
   - Check interface datasheet for supported speeds

3. **Speed Values**:
   - Speed configured in Mbps (megabits per second)
   - Common values: 10, 100, 1000, 10000, 25000, 40000, 100000
   - `auto` enables auto-negotiation

4. **Link Re-establishment**:
   - Changing speed may cause brief link down/up
   - Allow 5-30 seconds for link to re-establish
   - Some speed changes require physical medium support

5. **Auto-Negotiation**:
   - `speed auto` enables auto-negotiation
   - Actual negotiated speed depends on peer and cable
   - May take 10-30 seconds to negotiate

6. **Physical Media Constraints**:
   - Cable type affects supported speeds
   - Optical transceivers have specific speed support
   - Copper cables support variable speeds better
   - Long cable runs may limit maximum speed

7. **Peer Device Considerations**:
   - Peer must support configured speed
   - Mismatched speeds may prevent link establishment
   - Auto-negotiation requires both sides to support it

8. **Troubleshooting**:
   - If link doesn't come up: Check peer speed configuration
   - If speed change rejected: Check interface capabilities
   - If invalid speed: Consult interface documentation

9. **Virtual Environment**:
   - Virtual interfaces may have limited speed support
   - Speed changes may be simulated
   - Physical hardware testing recommended

---

## Additional Validation Commands

For comprehensive testing and troubleshooting:

```bash
# Detailed interface information
show interface Ethernet0

# Interface capabilities (if available)
show interface Ethernet0 capabilities

# Transceiver information
show interface transceiver eeprom Ethernet0

# Interface counters (check for errors)
show interface Ethernet0 counters

# Running configuration
show running-configuration interface Ethernet0

# System logs
show logging | grep -i Ethernet0
show logging | grep -i speed
```

---

## Troubleshooting

### Common Issues and Resolution

**Issue 1**: Speed change command rejected
- **Cause**: Interface does not support specified speed
- **Resolution**:
  - Check interface capabilities
  - Try different speed values
  - Verify interface hardware type
  - Consult interface documentation

**Issue 2**: Link does not come up after speed change
- **Cause**: Peer device not configured for same speed or incompatible
- **Resolution**:
  - Configure matching speed on peer device
  - Try auto-negotiation on both sides
  - Check physical cable supports speed
  - Verify transceiver compatibility

**Issue 3**: Speed shows different value than configured
- **Cause**: Auto-negotiation resulted in different speed, or configuration not applied
- **Resolution**:
  - If auto-negotiation: Expected behavior (negotiated speed)
  - If fixed speed: Re-apply configuration
  - Check for error messages
  - Verify command syntax

**Issue 4**: Interface flaps after speed change
- **Cause**: Unstable link, incompatible speed, or cable issues
- **Resolution**:
  - Check cable quality and type
  - Verify peer device speed
  - Try different speed value
  - Check for hardware issues

**Issue 5**: Speed configuration does not persist
- **Cause**: Configuration not saved or software issue
- **Resolution**:
  - Verify running configuration
  - Save configuration if required
  - Re-apply configuration
  - Report potential software bug

**Issue 6**: Invalid speed value accepted
- **Cause**: Software bug or validation issue
- **Resolution**:
  - Verify interface status
  - Check actual applied speed
  - Report issue if invalid speed was applied

---

## Performance Benchmarks

### Expected Behavior

**Configuration Time**:
- Command execution: < 1 second
- Configuration application: 1-2 seconds
- CLI reflection: Immediate to 2 seconds

**Link Re-establishment**:
- After speed change: 5-30 seconds
- Depends on new speed and negotiation
- Auto-negotiation: 10-30 seconds
- Fixed speed: 5-15 seconds

**CLI Response Time**:
- show interface status: 1-3 seconds
- show interface: 2-5 seconds
- show running-configuration: 2-5 seconds

### Acceptable Variations

- Speed change time varies by interface type
- Virtual environments may show different behavior
- Auto-negotiation time varies by protocol
- High-speed interfaces may transition faster
- First speed change may be slower than subsequent changes

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Test ID**: 1.3.9
- **Test Category**: Interface Events - Speed Changes
- **Priority**: Medium
- **Automation**: Recommended for automation
- **Related Test Cases**:
  - TC_INTF_EVENTS_001 (Basic Admin/Link State Changes)
  - TC_INTF_EVENTS_008 (Speed Auto-Negotiation)
- **Related Standards**:
  - IEEE 802.3 (Ethernet standards)
  - IEEE 802.3ab (1000BASE-T)
  - IEEE 802.3an (10GBASE-T)
  - IEEE 802.3ba (40G/100G Ethernet)

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Interface Commands**:
```bash
show interface status                      # Display all interface status
show interface status Ethernet<num>        # Display specific interface status
show interface Ethernet<num>               # Display detailed interface info
show running-configuration interface Ethernet<num>  # Display running config
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**Speed Configuration**:
```bash
configure terminal                         # Enter configuration mode
interface Ethernet<num>                    # Enter interface configuration
speed <value>                              # Set speed (auto, 10, 100, 1000, 10000, etc.)
exit                                       # Exit interface config
exit                                       # Exit configuration mode
```

**Common Speed Values**:
```bash
speed auto                                 # Auto-negotiation
speed 10                                   # 10 Mbps
speed 100                                  # 100 Mbps (Fast Ethernet)
speed 1000                                 # 1 Gbps (Gigabit)
speed 10000                                # 10 Gbps
speed 25000                                # 25 Gbps
speed 40000                                # 40 Gbps
speed 100000                               # 100 Gbps
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.3.9 - Validate if speed changes
