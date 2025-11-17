# Test Cases - Interface Events Validation (MTU Changes)

## Test Case ID: TC_INTF_EVENTS_010

### Test Case Name
Validate Interface MTU Changes

### Test Objective
Validate that interface MTU (Maximum Transmission Unit) can be changed to various supported values within the allowed range (1312-9216 bytes) and that the configuration changes are accurately reflected in CLI outputs. Ensure that MTU modifications are properly applied, displayed in interface status, and persist across configuration changes. Verify that the interface remains operational after MTU changes and that the new MTU value is correctly configured and displayed.

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
5. Understanding of MTU size constraints and valid range (1312-9216 bytes)
6. Interfaces should be in operational state

---

## Test Procedure

### Step 1: Initial Configuration - Bring Interface to UP State
**Objective**: Ensure test interfaces are in operational "up" state before testing MTU changes

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
**Objective**: Capture baseline interface MTU values before making changes

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status with MTU column
show interface status

# Check specific interface status
show interface status Ethernet0
show interface status Ethernet4

# Check detailed interface information
show interface Ethernet0
show interface Ethernet4
```

**Expected Result**:
- Interfaces display current MTU configuration
- Baseline MTU values captured (typically 9100 or default value)
- Output stored for comparison

**Sample Output Format**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            9100
Ethernet4           -                   up             up             10G            9100
```

**Note**: Record baseline MTU values for later restoration

---

### Step 3: Change MTU to Minimum Value (1312) on Ethernet0
**Objective**: Configure interface MTU to minimum allowed value

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Configure MTU to minimum value
mtu 1312

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- MTU 1312 configuration accepted without errors
- Configuration applied successfully
- No error messages

---

### Step 4: Verify MTU Change to 1312 on Ethernet0
**Objective**: Verify that MTU change to 1312 is reflected in CLI output

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
- Interface status shows MTU as "1312"
- MTU value accurately displayed in show commands
- Interface operational state maintained
- Configuration change reflected immediately

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            1312
```

**Validation Points**:
1. MTU field shows "1312"
2. Interface remains operational
3. Configuration change successful

---

### Step 5: Change MTU to Maximum Value (9216) on Ethernet0
**Objective**: Configure interface MTU to maximum allowed value

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Configure MTU to maximum value
mtu 9216

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- MTU 9216 configuration accepted
- Configuration applied successfully
- No errors

---

### Step 6: Verify MTU Change to 9216 on Ethernet0
**Objective**: Verify that MTU change to 9216 is reflected in CLI output

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows MTU as "9216"
- Interface operational state is "up"
- CLI output accurate

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            9216
```

**Validation Points**:
1. MTU field shows "9216"
2. Interface operational after MTU change
3. Maximum MTU value supported

---

### Step 7: Change MTU to Standard Value (1500) on Ethernet0
**Objective**: Configure interface MTU to standard Ethernet MTU value

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Configure MTU to standard value
mtu 1500

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- MTU 1500 configuration accepted
- Configuration applied successfully
- No errors

**Note**: 1500 is the standard Ethernet MTU size

---

### Step 8: Verify MTU Change to 1500 on Ethernet0
**Objective**: Verify standard MTU value is configured correctly

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows MTU as "1500"
- Interface operational state is "up"
- Standard MTU value applied correctly

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            1500
```

---

### Step 9: Change MTU to Jumbo Frame Size (9100) on Ethernet0
**Objective**: Configure interface MTU to common jumbo frame size

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Configure MTU to jumbo frame size
mtu 9100

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- MTU 9100 configuration accepted
- Configuration applied successfully
- Jumbo frames enabled

**Note**: 9100 is a common jumbo frame MTU size

---

### Step 10: Verify MTU Change to 9100 on Ethernet0
**Objective**: Verify jumbo frame MTU configuration

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows MTU as "9100"
- Interface operational
- Jumbo frames configured

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            9100
```

---

### Step 11: Test MTU Value at Mid-Range (5000) on Ethernet0
**Objective**: Verify MTU can be set to arbitrary value within valid range

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Configure MTU to mid-range value
mtu 5000

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- MTU 5000 configuration accepted
- Configuration applied successfully
- Arbitrary value within range works

---

### Step 12: Verify MTU Change to 5000 on Ethernet0
**Objective**: Verify arbitrary MTU value is configured

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows MTU as "5000"
- Interface operational
- Mid-range MTU value supported

---

### Step 13: Test MTU Changes on Ethernet4
**Objective**: Verify MTU changes work on multiple interfaces

**Commands (Execute on DUT1)**:
```bash
# Test sequence on Ethernet4
sonic-cli
configure terminal

# Test 1: Change to 1312
interface Ethernet4
mtu 1312
exit
exit

# Verify
show interface status Ethernet4

# Test 2: Change to 9216
configure terminal
interface Ethernet4
mtu 9216
exit
exit

# Verify
show interface status Ethernet4

# Test 3: Change to 9100 (standard jumbo)
configure terminal
interface Ethernet4
mtu 9100
exit
exit

# Verify
show interface status Ethernet4
```

**Expected Result**:
- MTU changes apply successfully on Ethernet4
- Each change reflected in CLI output
- Interface remains operational through changes

---

### Step 14: Rapid MTU Changes Test
**Objective**: Test system stability during rapid MTU changes

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Rapid MTU changes on Ethernet0
configure terminal
interface Ethernet0
mtu 1500
mtu 9100
mtu 1500
mtu 9100
exit
exit

# Verify final state
show interface status Ethernet0
```

**Expected Result**:
- System handles rapid MTU changes
- Final MTU configuration is correct (9100)
- No system instability
- Interface operational

---

### Step 15: MTU Change with Link Flap
**Objective**: Verify MTU configuration persists through interface flap

**Commands (Execute on DUT1)**:
```bash
# Configure specific MTU
sonic-cli
configure terminal
interface Ethernet0
mtu 9100
exit
exit

# Verify MTU
show interface status Ethernet0

# Flap the interface
configure terminal
interface Ethernet0
shutdown
no shutdown
exit
exit

# Wait a few seconds
# Verify MTU persists
show interface status Ethernet0
```

**Expected Result**:
- MTU configuration persists through interface flap
- Interface comes back up with configured MTU
- No need to reconfigure MTU after flap

---

### Step 16: Verify Multiple MTU Changes in Sequence
**Objective**: Validate that multiple sequential MTU changes work correctly

**Test Sequence**:
1. Change to 1500, verify
2. Change to 9100, verify
3. Change to 1312, verify
4. Change to 9216, verify
5. Change to 9100, verify

**Commands (Execute on DUT1)**:
```bash
# Sequence of MTU changes
sonic-cli

# Change 1: 1500
configure terminal
interface Ethernet0
mtu 1500
exit
exit
show interface status Ethernet0

# Change 2: 9100
configure terminal
interface Ethernet0
mtu 9100
exit
exit
show interface status Ethernet0

# Change 3: 1312
configure terminal
interface Ethernet0
mtu 1312
exit
exit
show interface status Ethernet0

# Change 4: 9216
configure terminal
interface Ethernet0
mtu 9216
exit
exit
show interface status Ethernet0

# Change 5: 9100 (restore to common value)
configure terminal
interface Ethernet0
mtu 9100
exit
exit
show interface status Ethernet0
```

**Expected Result**:
- Each MTU change applies successfully
- Each change reflected in CLI output
- Interface operational after each change
- No accumulated errors or instability

---

### Step 17: Verify Configuration Persistence
**Objective**: Verify that MTU configuration is saved in running configuration

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check running configuration
show running-configuration interface Ethernet0
show running-configuration interface Ethernet4
```

**Expected Result**:
- Running configuration shows current MTU settings
- Configuration accurately reflects applied changes
- No discrepancies between applied and saved configuration

**Sample Output**:
```
interface Ethernet0
 mtu 9100
 no shutdown
!
```

---

### Step 18: Test Invalid MTU Value Handling (Below Minimum)
**Objective**: Verify proper error handling for MTU values below minimum

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Try MTU below minimum (1311 is below 1312)
interface Ethernet0
mtu 1311
exit
exit

# Verify interface state unchanged
show interface status Ethernet0
```

**Expected Result**:
- MTU value below 1312 rejected with error message
- Interface maintains previous MTU configuration
- System handles error gracefully
- Error message indicates valid range: 1312-9216

---

### Step 19: Test Invalid MTU Value Handling (Above Maximum)
**Objective**: Verify proper error handling for MTU values above maximum

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Try MTU above maximum (9217 is above 9216)
interface Ethernet0
mtu 9217
exit
exit

# Verify interface state unchanged
show interface status Ethernet0
```

**Expected Result**:
- MTU value above 9216 rejected with error message
- Interface maintains previous MTU configuration
- System handles error gracefully
- Error message indicates valid range: 1312-9216

---

### Step 20: Test Invalid MTU Value Handling (Non-numeric)
**Objective**: Verify proper error handling for non-numeric MTU values

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Try invalid non-numeric MTU value
interface Ethernet0
mtu invalid
exit
exit

# Verify interface state unchanged
show interface status Ethernet0
```

**Expected Result**:
- Non-numeric MTU value rejected with error message
- Interface maintains previous MTU configuration
- System handles error gracefully
- No impact on interface operational status

---

### Step 21: Verify MTU on Multiple Interfaces Simultaneously
**Objective**: Test MTU configuration on multiple interfaces at once

**Commands (Execute on DUT1)**:
```bash
# Configure both interfaces
sonic-cli
configure terminal

# Configure Ethernet0
interface Ethernet0
mtu 9100
exit

# Configure Ethernet4
interface Ethernet4
mtu 9100
exit

# Exit configuration mode
exit

# Verify both interfaces
show interface status
```

**Expected Result**:
- Both interfaces show MTU 9100
- Both interfaces operational
- Configuration applied to multiple interfaces successfully

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            9100
Ethernet4           -                   up             up             10G            9100
```

---

### Step 22: Final State Verification
**Objective**: Verify system is in clean state after all MTU change tests

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

# Check running configuration
show running-configuration interface Ethernet0
show running-configuration interface Ethernet4
```

**Expected Result**:
- All interfaces in expected state
- No residual error conditions
- All CLI commands responsive
- System stable after all configuration changes
- Interfaces operational with correct MTU values

---

## Validation Points

### CLI Validation (klish mode via sonic-cli)

**Primary Command**: `show interface status`

**Validation Criteria**:

#### 1. MTU Change Reflection
- **After MTU change command**:
  - MTU field in `show interface status` matches configured value
  - Change reflected immediately or within seconds
  - CLI output accurate and consistent

#### 2. Supported MTU Values
**Valid Range**: 1312 - 9216 bytes

Common MTU values to test:
- `mtu 1312` - Minimum allowed value
- `mtu 1500` - Standard Ethernet MTU
- `mtu 9100` - Common jumbo frame size
- `mtu 9216` - Maximum allowed value
- `mtu 5000` - Arbitrary mid-range value

**Invalid values** (should be rejected):
- Below 1312 (e.g., 1311, 1000, 576)
- Above 9216 (e.g., 9217, 10000, 16000)
- Non-numeric values

#### 3. Interface Stability After MTU Change
- Interface operational state maintained
- Link remains up (typically no link flap for MTU change)
- No continuous flapping
- Stable operation at new MTU

#### 4. Configuration Accuracy
- CLI output matches configured MTU
- Running configuration shows MTU setting
- No discrepancies between configuration and status
- Configuration persists through interface flaps

#### 5. Error Handling
- Invalid MTU values rejected with clear error messages
- Out-of-range values handled gracefully
- Interface maintains previous configuration on error
- System remains stable after error

---

## Expected Overall Results

### Success Criteria

#### 1. MTU Configuration Success
- MTU change commands execute successfully for values in range 1312-9216
- Configuration applies immediately or within seconds
- CLI reflects new MTU configuration
- Running configuration shows MTU setting

#### 2. Interface Operational Continuity
- Interface remains operational after MTU changes
- No permanent link loss (MTU changes typically don't cause link flap)
- Stable operation at configured MTU
- Traffic can flow at new MTU size

#### 3. CLI Accuracy
- `show interface status` accurately displays configured MTU
- MTU value matches what was configured
- All interface parameters correctly displayed
- No inconsistencies in CLI output

#### 4. Configuration Persistence
- MTU configuration persists through interface flaps
- Configuration saved in running-config
- MTU maintained across admin state changes
- No need to reconfigure after interface recovery

#### 5. System Stability
- System handles MTU changes without issues
- Multiple MTU changes don't cause instability
- Rapid MTU changes handled gracefully
- No system crashes or hangs
- Resources (CPU, memory) remain stable

#### 6. Error Handling
- Out-of-range MTU values rejected with appropriate errors
- Below minimum (< 1312) rejected
- Above maximum (> 9216) rejected
- Clear error messages provided
- System recovers from error conditions

### Performance Criteria

- **Configuration Application Time**: < 2 seconds
- **CLI Response Time**: < 5 seconds for show commands
- **MTU Change Impact**: Minimal to no packet loss
- **Configuration Persistence**: Immediate in running-config
- **Link Stability**: No link flap during MTU change

### Failure Indicators

**Test should fail if**:
1. Valid MTU values (1312-9216) rejected
2. CLI does not show configured MTU
3. Invalid MTU values accepted without error
4. MTU configuration does not persist through flaps
5. Multiple MTU changes cause system instability
6. Running configuration does not reflect MTU changes
7. Interface becomes down after MTU change
8. System crashes or becomes unresponsive
9. CLI output is incorrect or inconsistent
10. MTU values outside range (< 1312 or > 9216) accepted

---

## Test Execution Summary Template

### MTU Change Verification

| Interface | Initial MTU | Changed To | Verified MTU | Link Status | Result |
|-----------|-------------|------------|--------------|-------------|--------|
| Ethernet0 | 9100 | 1312 | 1312 | up | Pass/Fail |
| Ethernet0 | 1312 | 9216 | 9216 | up | Pass/Fail |
| Ethernet0 | 9216 | 1500 | 1500 | up | Pass/Fail |
| Ethernet0 | 1500 | 9100 | 9100 | up | Pass/Fail |
| Ethernet0 | 9100 | 5000 | 5000 | up | Pass/Fail |
| Ethernet4 | 9100 | 1312 | 1312 | up | Pass/Fail |
| Ethernet4 | 1312 | 9216 | 9216 | up | Pass/Fail |

### Sequential MTU Changes

| Sequence | MTU Changes | Final MTU | Final Status | Result |
|----------|-------------|-----------|--------------|--------|
| 1 | 1500 → 9100 → 1312 → 9216 → 9100 | 9100 | up | Pass/Fail |
| Rapid | 1500,9100,1500,9100 (rapid) | 9100 | up | Pass/Fail |

### Persistence Validation

| Test | MTU Config | After Flap | Running Config | Result |
|------|------------|------------|----------------|--------|
| Interface Flap | 9100 | 9100 | mtu 9100 | Pass/Fail |
| Multiple Changes | 5000 | 5000 | mtu 5000 | Pass/Fail |

### Error Handling

| Invalid MTU | Error Displayed | Interface MTU | Result |
|-------------|-----------------|---------------|--------|
| 1311 (below min) | Yes/No | Unchanged | Pass/Fail |
| 9217 (above max) | Yes/No | Unchanged | Pass/Fail |
| 10000 (above max) | Yes/No | Unchanged | Pass/Fail |
| invalid (non-numeric) | Yes/No | Unchanged | Pass/Fail |

---

## Cleanup Steps

After test completion, restore interfaces to desired state:

```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Restore Ethernet0 to default MTU (typically 9100)
interface Ethernet0
mtu 9100
no shutdown
exit

# Restore Ethernet4 to default MTU
interface Ethernet4
mtu 9100
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
- Interfaces at desired final MTU (typically 9100)
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
4. mtu <value>                  # Change MTU (1312-9216)
5. exit                         # Exit interface config
6. exit                         # Exit config mode
7. show interface status        # Verify MTU change
8. (repeat for different MTU values)
```

**Topology Diagram**:
```
+--------------------+                       +--------------------+
|       DUT1         |                       |       DUT2         |
| (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
| 192.168.100.193    |   (MTU Changes)       | 192.168.100.195    |
|                    |<-----Ethernet4------->|                    |
|                    |   (MTU Changes)       |                    |
+--------------------+                       +--------------------+
```

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **MTU Valid Range**:
   - Minimum: 1312 bytes
   - Maximum: 9216 bytes
   - Any value outside this range should be rejected

3. **Common MTU Values**:
   - 1500: Standard Ethernet MTU
   - 9100: Common jumbo frame size
   - 9216: Maximum jumbo frame size

4. **MTU and Packet Size**:
   - MTU defines maximum packet size (Layer 3)
   - Does not include Ethernet header and trailer
   - Jumbo frames allow larger packets for better efficiency

5. **MTU Change Behavior**:
   - MTU changes typically don't cause link flap
   - Configuration applies immediately
   - Both ends of link should have compatible MTU settings

6. **Peer Device Considerations**:
   - Peer device should support same or higher MTU
   - Mismatched MTU can cause packet fragmentation or drops
   - For jumbo frames, both sides should be configured

7. **Path MTU**:
   - Entire path must support configured MTU
   - Intermediate devices (switches) must support jumbo frames
   - Path MTU discovery helps avoid fragmentation

8. **MTU and Performance**:
   - Larger MTU (jumbo frames) can improve throughput
   - Reduces overhead for bulk transfers
   - Standard 1500 ensures compatibility

9. **Virtual Environment**:
   - Virtual interfaces may have different MTU constraints
   - Check virtual platform documentation
   - Physical hardware testing recommended

10. **Application Impact**:
    - Applications may need to be aware of MTU
    - TCP MSS negotiation adjusts to MTU
    - UDP applications need manual MTU consideration

---

## Additional Validation Commands

For comprehensive testing and troubleshooting:

```bash
# Detailed interface information
show interface Ethernet0

# Interface counters (check for MTU-related errors)
show interface Ethernet0 counters

# Check for MTU mismatch errors
show interface Ethernet0 counters | grep -i error

# Running configuration
show running-configuration interface Ethernet0

# System logs
show logging | grep -i Ethernet0
show logging | grep -i mtu

# All interfaces status
show interface status

# Specific interface details
show interface Ethernet0
```

---

## Troubleshooting

### Common Issues and Resolution

**Issue 1**: MTU change command rejected
- **Cause**: Value outside valid range (1312-9216)
- **Resolution**:
  - Verify MTU value is within 1312-9216
  - Check command syntax: `mtu <value>`
  - Use numeric value only
  - Review error message for guidance

**Issue 2**: Interface shows different MTU than configured
- **Cause**: Configuration not applied or read incorrectly
- **Resolution**:
  - Re-apply MTU configuration
  - Check running configuration
  - Verify no conflicting policies
  - Check interface status carefully

**Issue 3**: Packet loss after MTU change
- **Cause**: Peer device or path doesn't support new MTU
- **Resolution**:
  - Configure matching MTU on peer device
  - Verify intermediate switches support jumbo frames
  - Check for MTU mismatch in path
  - Use standard MTU (1500) if issues persist

**Issue 4**: MTU configuration does not persist
- **Cause**: Configuration not saved or software issue
- **Resolution**:
  - Verify running configuration
  - Save configuration if required
  - Re-apply configuration
  - Report potential software bug

**Issue 5**: Invalid MTU value accepted
- **Cause**: Software bug or validation issue
- **Resolution**:
  - Verify actual applied MTU value
  - Check interface behavior
  - Report issue if invalid MTU was applied
  - Restore to known good value

**Issue 6**: Cannot configure jumbo frames (> 1500)
- **Cause**: Platform or interface limitation
- **Resolution**:
  - Check interface capabilities
  - Verify platform supports jumbo frames
  - Review hardware documentation
  - Use standard MTU if jumbo not supported

---

## Performance Benchmarks

### Expected Behavior

**Configuration Time**:
- Command execution: < 1 second
- Configuration application: Immediate
- CLI reflection: Immediate to 2 seconds

**Impact on Traffic**:
- Packet loss during change: None to minimal
- Link flap: Typically no flap
- Service interruption: None expected

**CLI Response Time**:
- show interface status: 1-3 seconds
- show interface: 2-5 seconds
- show running-configuration: 2-5 seconds

### Acceptable Variations

- Configuration time may vary by platform
- Virtual environments may show different behavior
- First MTU change may be slower than subsequent changes
- Some platforms may require brief link flap

---

## MTU Size Reference

### Standard and Common MTU Values

| MTU Size | Description | Use Case |
|----------|-------------|----------|
| 1312 | Minimum allowed | Minimum for this platform |
| 1500 | Standard Ethernet | Default for most networks |
| 4096 | Large MTU | Some specialized applications |
| 9000 | Jumbo frames | Storage networks |
| 9100 | Common jumbo | Data center networks |
| 9216 | Maximum allowed | Maximum for this platform |

### MTU Calculation

```
Ethernet Frame = MTU + Ethernet Header (14) + CRC (4) + VLAN tags (if any)

Example for MTU 9100:
- Layer 3 payload: 9100 bytes (MTU)
- Ethernet header: 14 bytes
- CRC: 4 bytes
- Total frame: 9118 bytes (without VLAN)
```

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Test ID**: 1.3.10
- **Test Category**: Interface Events - MTU Changes
- **Priority**: Medium
- **Automation**: Recommended for automation
- **Related Test Cases**:
  - TC_INTF_EVENTS_001 (Basic Admin/Link State Changes)
  - TC_INTF_EVENTS_009 (Speed Changes)
- **Related Standards**:
  - IEEE 802.3 (Ethernet standards)
  - RFC 1191 (Path MTU Discovery)
  - RFC 8200 (IPv6 and MTU)

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Interface Commands**:
```bash
show interface status                      # Display all interface status with MTU
show interface status Ethernet<num>        # Display specific interface status
show interface Ethernet<num>               # Display detailed interface info
show running-configuration interface Ethernet<num>  # Display running config
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**MTU Configuration**:
```bash
configure terminal                         # Enter configuration mode
interface Ethernet<num>                    # Enter interface configuration
mtu <value>                                # Set MTU (1312-9216)
exit                                       # Exit interface config
exit                                       # Exit configuration mode
```

**MTU Value Examples**:
```bash
mtu 1312                                   # Minimum MTU
mtu 1500                                   # Standard Ethernet MTU
mtu 9100                                   # Common jumbo frame
mtu 9216                                   # Maximum MTU
```

**Valid Range**: 1312 ≤ MTU ≤ 9216

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.3.10 - Validate if MTU changes
