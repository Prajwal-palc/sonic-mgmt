# Test Cases - Interface Events Validation (Speed Auto-Negotiation)

## Test Case ID: TC_INTF_EVENTS_008

### Test Case Name
Validate Interface Speed Auto-Negotiation Configuration

### Test Objective
Validate that interface speed auto-negotiation can be configured successfully and is accurately reflected in CLI outputs. Ensure that the "speed auto" configuration is properly applied, displayed in interface status, and enables proper link negotiation between connected devices. Verify that auto-negotiation works correctly for various interface types and successfully establishes optimal speed and duplex settings.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Device Under Test (DUT1)**: smic_sonic1 (192.168.100.193)
- **Peer Device (DUT2)**: smic_sonic2 (192.168.100.195)
- **Test Interfaces**:
  - Ethernet0
  - Ethernet4
  - Ethernet8 (optional - for multiple interface testing)
- **Connection**:
  - smic_sonic1:Ethernet0 <---> smic_sonic2:Ethernet0
  - smic_sonic1:Ethernet4 <---> smic_sonic2:Ethernet4
- **Topology**: 2 nodes

### Prerequisites
1. Both devices (smic_sonic1 and smic_sonic2) must be accessible via SSH
2. User credentials: admin/YourPaSsWoRd
3. Access to sonic-cli and klish shell
4. Sufficient privileges to configure interfaces
5. Interfaces support auto-negotiation (not all interfaces support auto-negotiation)
6. Physical links are capable of auto-negotiation
7. Peer device configured to support auto-negotiation

---

## Test Procedure

### Step 1: Initial Configuration - Bring Interface to UP State
**Objective**: Ensure test interfaces are in operational "up" state before testing auto-negotiation

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

### Step 2: Baseline Interface Status Check (Before Auto-Negotiation)
**Objective**: Capture baseline interface status before configuring auto-negotiation

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
- Interfaces display current speed configuration (e.g., 10G, 1G, 100M)
- Current duplex mode displayed (full/half)
- Current auto-negotiation status captured
- Output captured for baseline comparison

**Sample Output Format**:
```
Interface        Admin    Oper    Speed         Duplex    Type              Description
------------------------------------------------------------------------------------------
Ethernet0        up       up      10G           full      QSFP28            <description>
Ethernet4        up       up      10G           full      QSFP28            <description>
```

**Note**: Initial speed configuration may vary depending on interface type and previous configuration

---

### Step 3: Configure Speed Auto-Negotiation on Ethernet0
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
- No error messages during configuration
- Configuration applied successfully

**Note**: Some interface types may not support auto-negotiation. If the command fails, note the interface type and error message for documentation.

---

### Step 4: Verify Speed Auto Configuration on Ethernet0
**Objective**: Verify that speed auto configuration is reflected in CLI output

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0

# Check detailed interface information
show interface Ethernet0
```

**Expected Result**:
- Interface status shows speed as "auto"
- Auto-negotiation status shows as "enabled" or "on"
- Interface operational state remains "up"
- No errors or inconsistencies in displayed information

**Sample Output Format**:
```
Interface        Admin    Oper    Speed         Duplex    Type              Description
------------------------------------------------------------------------------------------
Ethernet0        up       up      auto          auto      QSFP28            <description>
```

**Validation Points**:
1. Speed field shows "auto"
2. Duplex may also show "auto" (depending on implementation)
3. Interface remains operational
4. CLI output is consistent and accurate

---

### Step 5: Verify Link Negotiation on Ethernet0
**Objective**: Verify that auto-negotiation successfully negotiates speed and duplex with peer

**Wait Time**: Allow 10-15 seconds for negotiation to complete

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0

# Check detailed interface information
show interface Ethernet0
```

**Expected Result**:
- Auto-negotiation completes successfully
- Interface shows negotiated speed (e.g., 10G, 1G, 100M, etc.)
- Interface shows negotiated duplex (typically "full")
- Operational state is "up"
- Link is stable and operational

**Sample Output After Negotiation**:
```
Interface        Admin    Oper    Speed         Duplex    Type              Description
------------------------------------------------------------------------------------------
Ethernet0        up       up      10G           full      QSFP28            <description>
```

**Note**: The actual negotiated speed depends on:
- Interface capabilities
- Cable type and quality
- Peer device capabilities
- Common supported speeds between devices

**Validation Points**:
1. Link successfully negotiates (oper status = up)
2. Negotiated speed is one of the supported speeds
3. Duplex is typically "full" for modern interfaces
4. No link flapping or instability

---

### Step 6: Configure Speed Auto-Negotiation on Ethernet4
**Objective**: Configure auto-negotiation on second test interface

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet4
interface Ethernet4

# Configure speed auto
speed auto

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Speed auto configuration accepted
- Configuration applied successfully
- No errors

---

### Step 7: Verify Speed Auto Configuration on Ethernet4
**Objective**: Verify auto-negotiation configuration on second interface

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet4

# Check all interfaces
show interface status
```

**Expected Result**:
- Ethernet4 shows speed as "auto"
- Both Ethernet0 and Ethernet4 show auto-negotiation enabled
- All CLI commands execute successfully
- Output is consistent and accurate

---

### Step 8: Verify Multiple Interfaces with Auto-Negotiation
**Objective**: Verify that multiple interfaces can simultaneously use auto-negotiation

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check status of all interfaces
show interface status

# Verify both test interfaces
show interface status Ethernet0
show interface status Ethernet4
```

**Expected Result**:
- Both Ethernet0 and Ethernet4 show speed auto configuration
- Both interfaces negotiate successfully with their peers
- Operational state is "up" for both interfaces
- No conflicts or issues with multiple interfaces using auto-negotiation
- System handles multiple concurrent auto-negotiations

**Sample Output**:
```
Interface        Admin    Oper    Speed         Duplex    Type              Description
------------------------------------------------------------------------------------------
Ethernet0        up       up      10G           full      QSFP28            <description>
Ethernet4        up       up      10G           full      QSFP28            <description>
```

---

### Step 9: Test Link Flap with Auto-Negotiation Enabled
**Objective**: Verify that auto-negotiation works correctly after link flap

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Flap Ethernet0
interface Ethernet0
shutdown
exit
exit

# Wait 2-3 seconds
# (In automated test, add sleep)

# Bring interface back up
configure terminal
interface Ethernet0
no shutdown
exit
exit

# Wait for negotiation (10-15 seconds)

# Verify interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface goes down on shutdown
- Interface comes back up on no shutdown
- Auto-negotiation re-runs successfully
- Link re-establishes with negotiated speed
- Speed configuration remains as "auto"
- No issues with re-negotiation after link flap

**Validation Points**:
1. Auto-negotiation configuration persists through link flap
2. Re-negotiation completes successfully
3. Link comes up with appropriate speed and duplex
4. No manual intervention required

---

### Step 10: Test Configuration Persistence
**Objective**: Verify that speed auto configuration persists in running configuration

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check running configuration for Ethernet0
show running-configuration interface Ethernet0

# Check running configuration for Ethernet4
show running-configuration interface Ethernet4
```

**Expected Result**:
- Running configuration shows "speed auto" for both interfaces
- Configuration is properly saved in running-config
- No discrepancies between applied configuration and running-config

**Sample Output**:
```
interface Ethernet0
 speed auto
 no shutdown
!
```

---

### Step 11: Test Speed Auto Configuration on Peer Device (DUT2)
**Objective**: Verify that both sides can use auto-negotiation simultaneously

**Commands (Execute on DUT2)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure speed auto on Ethernet0
interface Ethernet0
speed auto
exit

# Configure speed auto on Ethernet4
interface Ethernet4
speed auto
exit

# Exit configuration mode
exit

# Verify configuration
show interface status Ethernet0
show interface status Ethernet4
```

**Expected Result**:
- Both DUT1 and DUT2 can use auto-negotiation
- Links negotiate successfully when both sides use auto
- Negotiated speeds are consistent and optimal
- No link instability or negotiation failures

---

### Step 12: Verify Negotiation with Different Speed Capabilities
**Objective**: Test auto-negotiation behavior with varying peer capabilities (if applicable)

**Note**: This step is optional and depends on available hardware/interfaces

**Scenarios to Test** (if hardware supports):
1. Both sides auto - should negotiate to highest common speed
2. One side fixed speed, other side auto - should match the fixed speed
3. Mismatched fixed speeds - link should fail or operate at lower speed

**Commands**: (Example for scenario testing)
```bash
# DUT1: Set to auto
sonic-cli
configure terminal
interface Ethernet0
speed auto
exit
exit

# DUT2: Set to specific speed (if testing mismatch scenarios)
sonic-cli
configure terminal
interface Ethernet0
speed 1000  # Example: force 1G
exit
exit

# Verify link status and negotiated speed on both devices
show interface status Ethernet0
```

**Expected Result**:
- Auto-negotiation adapts to peer capabilities
- Link establishes at mutually supported speed
- No link failures with compatible configurations
- Appropriate error handling for incompatible configurations

---

### Step 13: Restore Default Configuration (Optional)
**Objective**: Restore interfaces to default or specific speed configuration

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Restore Ethernet0 to specific speed (example: 10G)
interface Ethernet0
speed 10000
exit

# Restore Ethernet4 to specific speed
interface Ethernet4
speed 10000
exit

# Exit configuration mode
exit

# Verify restored configuration
show interface status
```

**Expected Result**:
- Interfaces can be restored to fixed speed settings
- Configuration change applies successfully
- Links re-establish with fixed speeds
- No issues reverting from auto to fixed speed

---

### Step 14: Final State Verification
**Objective**: Verify system is in clean state after all tests

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
```

**Expected Result**:
- All interfaces in expected state (up/down as configured)
- No residual error conditions
- All CLI commands responsive
- System stable after all configuration changes

---

## Validation Points

### CLI Validation (klish mode via sonic-cli)

**Primary Command**: `show interface status`

**Validation Criteria**:

#### 1. Speed Auto Configuration Reflection
- **After "speed auto" command**:
  - Speed field shows "auto" in `show interface status`
  - Configuration accepted without errors
  - Change reflected immediately (within 1-2 seconds)

#### 2. Auto-Negotiation Behavior
- **During negotiation**:
  - Link may briefly go down/up (acceptable)
  - Negotiation typically completes within 10-15 seconds
  - No continuous flapping or instability

- **After negotiation**:
  - Interface operational state = "up"
  - Negotiated speed displayed (e.g., 10G, 1G, 100M)
  - Negotiated duplex displayed (typically "full")

#### 3. Configuration Accuracy
- CLI output matches configured state
- Running configuration shows "speed auto"
- No discrepancies between configuration and status
- Configuration persists through interface flaps

#### 4. Multi-Interface Support
- Multiple interfaces can use auto-negotiation simultaneously
- No conflicts or resource issues
- Each interface negotiates independently
- System handles concurrent negotiations

#### 5. Output Format Consistency
- Interface status output format remains consistent
- All fields populated correctly
- No corrupted or malformed output
- Column alignment maintained

### Auto-Negotiation Specific Validation

**Validation Checks**:

#### 1. Supported Speed Detection
- Auto-negotiation selects speed from supported speeds list
- Negotiated speed is within interface capabilities
- Speed is compatible with physical medium (cable type)
- No negotiation to unsupported speeds

#### 2. Duplex Negotiation
- Duplex typically negotiates to "full" for modern interfaces
- Duplex setting compatible with negotiated speed
- No half-duplex at high speeds (10G, 40G, etc.)

#### 3. Link Stability
- Link remains stable after negotiation completes
- No continuous re-negotiation or flapping
- Link quality indicators normal
- No excessive errors or packet loss

#### 4. Peer Compatibility
- Successful negotiation with peer device
- Both sides agree on speed and duplex
- No mismatched negotiation results
- Bi-directional communication established

---

## Expected Overall Results

### Success Criteria

#### 1. Configuration Success
- "speed auto" command executes without errors
- Configuration applies successfully
- CLI reflects auto-negotiation configuration
- Running configuration shows "speed auto"

#### 2. Negotiation Success
- Auto-negotiation completes successfully
- Link establishes with negotiated parameters
- Interface operational state = "up"
- No negotiation failures or timeouts

#### 3. CLI Accuracy
- `show interface status` accurately displays "auto" during configuration
- After negotiation, displays actual negotiated speed
- All interface parameters correctly displayed
- No inconsistencies in CLI output

#### 4. System Stability
- System handles auto-negotiation without issues
- Multiple interfaces can use auto simultaneously
- No system crashes or hangs
- Resources (CPU, memory) remain stable

#### 5. Persistence and Reliability
- Configuration persists through interface flaps
- Re-negotiation works correctly after link down/up
- Configuration saved in running-config
- Behavior consistent across multiple test cycles

### Performance Criteria

- **Configuration Application Time**: < 1 second
- **Negotiation Completion Time**: 5-15 seconds (typical)
- **Link Up Time**: < 30 seconds from "no shutdown" to operational
- **CLI Response Time**: < 5 seconds for show commands
- **Re-negotiation Time**: < 15 seconds after link flap

### Failure Indicators

**Test should fail if**:
1. "speed auto" command rejected or generates errors
2. CLI does not show "auto" after configuration
3. Auto-negotiation fails to complete
4. Link does not come up after negotiation
5. Negotiated speed is invalid or unsupported
6. Multiple interfaces cannot use auto simultaneously
7. Configuration does not persist through link flaps
8. System becomes unstable during testing
9. CLI output is incorrect or inconsistent
10. Running configuration does not reflect "speed auto"

---

## Test Execution Summary Template

### Configuration Verification

| Interface | Speed Before | Speed Configured | Speed After Negotiation | Duplex | Oper Status | Result |
|-----------|--------------|------------------|-------------------------|--------|-------------|--------|
| Ethernet0 | 10G | auto | 10G | full | up | Pass/Fail |
| Ethernet4 | 10G | auto | 10G | full | up | Pass/Fail |

### Auto-Negotiation Validation

| Test Case | Interface | Peer Config | Negotiation Time | Final Speed | Final Duplex | Result |
|-----------|-----------|-------------|------------------|-------------|--------------|--------|
| Single Interface | Ethernet0 | auto | X sec | 10G | full | Pass/Fail |
| Multiple Interfaces | Ethernet0,4 | auto | X sec | 10G | full | Pass/Fail |
| Link Flap Recovery | Ethernet0 | auto | X sec | 10G | full | Pass/Fail |
| Peer Auto | Ethernet0 | auto | X sec | 10G | full | Pass/Fail |

### CLI Validation

| Command | Output Correct | Speed Shows Auto | Negotiated Speed | Result |
|---------|----------------|------------------|------------------|--------|
| show interface status | Yes/No | Yes/No | Correct/Incorrect | Pass/Fail |
| show interface Ethernet0 | Yes/No | Yes/No | Correct/Incorrect | Pass/Fail |
| show running-configuration | Yes/No | Yes/No | N/A | Pass/Fail |

---

## Cleanup Steps

After test completion, ensure proper cleanup (optional - depends on requirements):

```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Option 1: Restore to specific speed (if required)
interface Ethernet0
speed 10000  # Example: restore to 10G
exit

interface Ethernet4
speed 10000
exit

# Option 2: Leave as auto (if that's the desired state)
# No changes needed

# Ensure interfaces are up
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

# Exit sonic-cli
exit
```

**Cleanup Verification**:
- Interfaces in desired final state (auto or fixed speed)
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
4. speed auto                   # Configure auto-negotiation
5. exit                         # Exit interface config
6. exit                         # Exit config mode
7. show interface status        # Verify configuration
8. (wait for negotiation to complete)
9. show interface status        # Verify negotiated speed
```

**Topology Diagram**:
```
+--------------------+                       +--------------------+
|       DUT1         |                       |       DUT2         |
| (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
| 192.168.100.193    |    (Auto-Neg)         | 192.168.100.195    |
|                    |<-----Ethernet4------->|                    |
|                    |    (Auto-Neg)         |                    |
+--------------------+                       +--------------------+
```

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **Interface Type Considerations**:
   - Not all interface types support auto-negotiation
   - High-speed interfaces (40G, 100G, 400G) may have limited auto-negotiation support
   - Copper interfaces typically have better auto-negotiation support than optical
   - Check interface capabilities before testing

3. **Auto-Negotiation Timing**:
   - Initial negotiation: 5-15 seconds (typical)
   - Re-negotiation after link flap: 5-15 seconds
   - Some interfaces may take up to 30 seconds
   - Negotiation time depends on interface type and capabilities

4. **Physical Media Considerations**:
   - Cable type affects auto-negotiation capabilities
   - Optical transceivers may have limited or no auto-negotiation
   - Copper cables typically support full auto-negotiation
   - Cable quality can affect negotiation success

5. **Peer Device Requirements**:
   - Peer must support auto-negotiation for full functionality
   - Both sides using auto-negotiation is ideal
   - One side fixed, one side auto can work but may limit speeds
   - Mismatched configurations may cause link issues

6. **Common Auto-Negotiation Speeds**:
   - 10M, 100M, 1G (common for copper)
   - 10G, 25G, 40G, 100G (higher speeds, limited auto-negotiation)
   - Actual supported speeds depend on interface hardware

7. **Troubleshooting Tips**:
   - If auto-negotiation fails: Check cable, peer config, interface capabilities
   - If link flaps continuously: May indicate negotiation mismatch
   - If negotiated speed is low: Check cable quality and peer capabilities
   - If command fails: Interface may not support auto-negotiation

8. **Virtual Environment Considerations**:
   - Virtual interfaces may have different behavior
   - Auto-negotiation may be simulated or not fully supported
   - Physical hardware testing recommended for complete validation

---

## Additional Validation Commands

For comprehensive testing and troubleshooting:

```bash
# Detailed interface information
show interface Ethernet0

# Interface capabilities (if available)
show interface Ethernet0 capabilities

# Transceiver information (for optical interfaces)
show interface transceiver eeprom Ethernet0

# Interface counters (check for errors)
show interface Ethernet0 counters

# Running configuration
show running-configuration interface Ethernet0

# System logs (check for negotiation issues)
show logging | grep -i Ethernet0
show logging | grep -i "auto-neg"
show logging | grep -i negotiation
```

---

## Troubleshooting

### Common Issues and Resolution

**Issue 1**: "speed auto" command rejected with error
- **Cause**: Interface does not support auto-negotiation
- **Resolution**:
  - Check interface type and capabilities
  - Verify interface hardware supports auto-negotiation
  - Try with different interface if available
  - Document which interface types do not support auto

**Issue 2**: Auto-negotiation configured but link does not come up
- **Cause**: Peer device not configured for auto-negotiation or incompatible
- **Resolution**:
  - Configure peer device for auto-negotiation
  - Check physical cable connection
  - Verify cable supports auto-negotiation
  - Check for hardware issues

**Issue 3**: Link flaps continuously after configuring auto-negotiation
- **Cause**: Negotiation mismatch or unstable link
- **Resolution**:
  - Check cable quality and connections
  - Verify peer device configuration
  - Check for duplex mismatch
  - Review system logs for error messages

**Issue 4**: Negotiated speed is lower than expected
- **Cause**: Cable limitations, peer limitations, or hardware issues
- **Resolution**:
  - Check cable type and quality
  - Verify peer device capabilities
  - Test with different cable
  - Check for interface hardware issues

**Issue 5**: CLI shows "auto" but negotiation never completes
- **Cause**: Negotiation timeout, peer not responding, or hardware issue
- **Resolution**:
  - Wait longer (up to 30 seconds)
  - Check peer device status
  - Verify physical connectivity
  - Check system logs for negotiation failures

**Issue 6**: Configuration does not persist through link flap
- **Cause**: Configuration not properly saved or software issue
- **Resolution**:
  - Verify running configuration
  - Save configuration if required
  - Re-apply configuration
  - Report potential software bug

---

## Performance Benchmarks

### Expected Behavior

**Configuration Time**:
- Command execution: < 1 second
- Configuration application: Immediate
- CLI reflection: 1-2 seconds

**Negotiation Time**:
- Initial negotiation: 5-15 seconds (typical)
- Maximum negotiation time: 30 seconds
- Re-negotiation after flap: 5-15 seconds

**Link Establishment**:
- From "no shutdown" to link up: 5-30 seconds
- From configuration to operational: 10-45 seconds
- Stable state achieved: Within 60 seconds

**CLI Response Time**:
- show interface status: 1-3 seconds
- show interface Ethernet<num>: 2-5 seconds
- show running-configuration: 2-5 seconds

### Acceptable Variations

- Negotiation time may vary by interface type (1G vs 10G vs 40G)
- Virtual environments may show different timing
- First negotiation may be slower than re-negotiations
- High-speed interfaces may have faster negotiation
- Optical interfaces may have different behavior than copper

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Test ID**: 1.3.8
- **Test Category**: Interface Events - Speed Auto-Negotiation
- **Priority**: Medium
- **Automation**: Recommended for automation
- **Related Test Cases**:
  - TC_INTF_EVENTS_001 (Basic Admin/Link State Changes)
  - TC_INTF_EVENTS_005 (Continuous Interface Flapping)
- **Related Standards**:
  - IEEE 802.3 (Ethernet standards)
  - IEEE 802.3ab (1000BASE-T)
  - IEEE 802.3an (10GBASE-T)

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Interface Commands**:
```bash
show interface status                      # Display all interface status
show interface status Ethernet<num>        # Display specific interface status
show interface Ethernet<num>               # Display detailed interface info
show interface Ethernet<num> capabilities  # Display interface capabilities (if available)
```

**Configuration Commands**:
```bash
show running-configuration interface Ethernet<num>  # Display running config
```

**Logging Commands**:
```bash
show logging                               # Display system logs
show logging | grep Ethernet               # Filter interface-related logs
show logging | grep -i negotiation         # Filter negotiation logs
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**Speed Auto-Negotiation Configuration**:
```bash
configure terminal                         # Enter configuration mode
interface Ethernet<num>                    # Enter interface configuration
speed auto                                 # Configure auto-negotiation
exit                                       # Exit interface config
exit                                       # Exit configuration mode
```

**Speed Fixed Configuration** (for restoring):
```bash
configure terminal                         # Enter configuration mode
interface Ethernet<num>                    # Enter interface configuration
speed <value>                              # Set specific speed (e.g., 1000, 10000)
exit                                       # Exit interface config
exit                                       # Exit configuration mode
```

**Common Speed Values**:
- `speed 10` - 10 Mbps
- `speed 100` - 100 Mbps
- `speed 1000` - 1 Gbps
- `speed 10000` - 10 Gbps
- `speed 25000` - 25 Gbps
- `speed 40000` - 40 Gbps
- `speed 100000` - 100 Gbps
- `speed auto` - Auto-negotiation

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.3.8 - Validate if interface speed auto-negotiation works
