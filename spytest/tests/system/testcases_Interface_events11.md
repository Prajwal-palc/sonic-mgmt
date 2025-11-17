# Test Cases - Interface Events Validation (MTU Changes - Negative Scenarios)

## Test Case ID: TC_INTF_EVENTS_011

### Test Case Name
Validate Interface MTU Does NOT Change with Invalid Values (Negative Scenarios)

### Test Objective
Validate that interface MTU configuration properly rejects invalid values that fall outside the allowed range (less than 1312 or greater than 9216 bytes). Ensure that the system provides appropriate error messages when invalid MTU values are configured and that the interface MTU remains unchanged at its previous valid value. Verify that interface operational status is not negatively impacted by invalid MTU configuration attempts and that the system handles errors gracefully without crashes or unexpected behavior.

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
5. Understanding of MTU valid range: **1312-9216 bytes**
6. Interfaces should be in operational state with known valid MTU

---

## Valid MTU Range

**VALID RANGE**: 1312 ≤ MTU ≤ 9216

### Invalid MTU Categories

1. **Below Minimum**: MTU < 1312
   - Examples: 1311, 1000, 576, 100, 0

2. **Above Maximum**: MTU > 9216
   - Examples: 9217, 10000, 16000, 65535

3. **Non-Numeric Values**: Invalid data types
   - Examples: "invalid", "auto", "max", special characters

4. **Negative Values**: Negative numbers
   - Examples: -1, -100, -9999

---

## Test Procedure

### Step 1: Initial Setup - Configure Valid MTU
**Objective**: Establish baseline with known valid MTU before testing invalid values

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Ensure Ethernet0 is up with valid MTU
interface Ethernet0
no shutdown
mtu 9100
exit

# Ensure Ethernet4 is up with valid MTU
interface Ethernet4
no shutdown
mtu 9100
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Both interfaces operational with MTU 9100
- Baseline established for negative testing
- No errors during initial configuration

---

### Step 2: Baseline MTU Verification
**Objective**: Capture and verify baseline MTU values before negative tests

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status with MTU column
show interface status

# Check specific interface status
show interface status Ethernet0
show interface status Ethernet4
```

**Expected Result**:
- Ethernet0 shows MTU: 9100
- Ethernet4 shows MTU: 9100
- Both interfaces operational
- Baseline MTU documented

**Sample Output Format**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            9100
Ethernet4           -                   up             up             10G            9100
```

**Note**: Record baseline MTU (9100) to verify it remains unchanged after invalid attempts

---

### Step 3: Test Invalid MTU - Below Minimum (1311)
**Objective**: Verify MTU value 1 below minimum (1311) is rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure invalid MTU (1 below minimum)
interface Ethernet0
mtu 1311
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected** with error message indicating valid range
- **MTU remains unchanged** at 9100
- Error message states valid range: 1312-9216
- Interface operational status unaffected

**Expected Error Message** (may vary):
```
Error: MTU value must be between 1312 and 9216
% Invalid input detected
Value out of range
```

**Validation**:
- MTU still shows 9100 (unchanged)
- No configuration change applied
- System handles error gracefully

---

### Step 4: Test Invalid MTU - Below Minimum (1000)
**Objective**: Verify MTU value significantly below minimum (1000) is rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure invalid MTU (far below minimum)
interface Ethernet0
mtu 1000
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected** with error message
- **MTU remains unchanged** at 9100
- Clear error indication
- Interface operational

---

### Step 5: Test Invalid MTU - Below Minimum (576)
**Objective**: Verify standard IP minimum MTU (576) is rejected (below SONiC minimum)

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure MTU 576 (standard IP minimum, but below SONiC minimum)
interface Ethernet0
mtu 576
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected** - 576 is below SONiC minimum (1312)
- **MTU remains unchanged** at 9100
- Error message displayed
- Interface operational

**Note**: Although 576 is the minimum IP MTU per RFC 791, SONiC requires minimum 1312

---

### Step 6: Test Invalid MTU - Below Minimum (100)
**Objective**: Verify extremely small MTU value (100) is rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure very small MTU
interface Ethernet0
mtu 100
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected**
- **MTU remains unchanged** at 9100
- Error message displayed
- Interface operational

---

### Step 7: Test Invalid MTU - Zero Value
**Objective**: Verify MTU value of 0 is rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure MTU 0
interface Ethernet0
mtu 0
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected**
- **MTU remains unchanged** at 9100
- Error message displayed
- Zero MTU not allowed

---

### Step 8: Test Invalid MTU - Above Maximum (9217)
**Objective**: Verify MTU value 1 above maximum (9217) is rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure invalid MTU (1 above maximum)
interface Ethernet0
mtu 9217
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected** with error message
- **MTU remains unchanged** at 9100
- Error message indicates valid range: 1312-9216
- Interface operational

**Expected Error Message**:
```
Error: MTU value must be between 1312 and 9216
% Invalid input detected
Value out of range
```

---

### Step 9: Test Invalid MTU - Above Maximum (10000)
**Objective**: Verify MTU value significantly above maximum (10000) is rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure MTU far above maximum
interface Ethernet0
mtu 10000
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected**
- **MTU remains unchanged** at 9100
- Error message displayed
- Interface operational

---

### Step 10: Test Invalid MTU - Above Maximum (16000)
**Objective**: Verify extremely large MTU value (16000) is rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure very large MTU
interface Ethernet0
mtu 16000
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected**
- **MTU remains unchanged** at 9100
- Error message displayed
- Interface operational

---

### Step 11: Test Invalid MTU - Above Maximum (65535)
**Objective**: Verify maximum 16-bit value (65535) is rejected as MTU

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure MTU with max 16-bit value
interface Ethernet0
mtu 65535
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected**
- **MTU remains unchanged** at 9100
- 65535 exceeds maximum allowed MTU (9216)
- Error message displayed

---

### Step 12: Test Invalid MTU - Negative Value (-1)
**Objective**: Verify negative MTU values are rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure negative MTU
interface Ethernet0
mtu -1
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected** - negative values not allowed
- **MTU remains unchanged** at 9100
- Error message or syntax error displayed
- Interface operational

---

### Step 13: Test Invalid MTU - Negative Value (-100)
**Objective**: Verify larger negative MTU values are rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure negative MTU
interface Ethernet0
mtu -100
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected**
- **MTU remains unchanged** at 9100
- Negative values not allowed
- Error message displayed

---

### Step 14: Test Invalid MTU - Non-Numeric Value ("invalid")
**Objective**: Verify non-numeric string values are rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure non-numeric MTU
interface Ethernet0
mtu invalid
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected** - syntax error
- **MTU remains unchanged** at 9100
- Error indicates invalid parameter type
- Interface operational

**Expected Error**:
```
% Invalid input detected
Expecting numeric value
```

---

### Step 15: Test Invalid MTU - Non-Numeric Value ("auto")
**Objective**: Verify "auto" keyword is rejected for MTU (unlike speed)

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure MTU auto
interface Ethernet0
mtu auto
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected** - "auto" not valid for MTU
- **MTU remains unchanged** at 9100
- Syntax or parameter error
- Interface operational

**Note**: Unlike speed which supports "auto", MTU does not have auto-negotiation

---

### Step 16: Test Invalid MTU - Non-Numeric Value ("max")
**Objective**: Verify keyword "max" is rejected for MTU

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure MTU max
interface Ethernet0
mtu max
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected** - "max" not a valid parameter
- **MTU remains unchanged** at 9100
- Syntax error displayed
- Interface operational

---

### Step 17: Test Invalid MTU - Special Characters
**Objective**: Verify special characters are rejected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Attempt to configure MTU with special characters
interface Ethernet0
mtu @#$%
exit
exit

# Verify MTU unchanged
show interface status Ethernet0
```

**Expected Result**:
- **Command rejected** - invalid characters
- **MTU remains unchanged** at 9100
- Syntax error
- Interface operational

---

### Step 18: Test Invalid MTU on Ethernet4
**Objective**: Verify invalid MTU rejection works on multiple interfaces

**Commands (Execute on DUT1)**:
```bash
# Test invalid MTU on Ethernet4
sonic-cli

# Test 1: Below minimum
configure terminal
interface Ethernet4
mtu 1311
exit
exit
show interface status Ethernet4

# Test 2: Above maximum
configure terminal
interface Ethernet4
mtu 9217
exit
exit
show interface status Ethernet4

# Test 3: Far out of range
configure terminal
interface Ethernet4
mtu 10000
exit
exit
show interface status Ethernet4
```

**Expected Result**:
- All invalid MTU values rejected on Ethernet4
- MTU remains at baseline value (9100)
- Consistent error handling across interfaces
- Interface operational

---

### Step 19: Test Boundary Values - Just Below Minimum (1311)
**Objective**: Verify boundary validation at lower limit

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Capture current MTU
show interface status Ethernet0

# Attempt MTU 1311 (1 below minimum 1312)
configure terminal
interface Ethernet0
mtu 1311
exit
exit

# Verify MTU unchanged
show interface status Ethernet0

# Attempt MTU 1312 (minimum - should succeed)
configure terminal
interface Ethernet0
mtu 1312
exit
exit

# Verify MTU changed to 1312
show interface status Ethernet0
```

**Expected Result**:
- **1311 rejected** - below minimum
- **1312 accepted** - exactly at minimum
- Clear boundary between valid/invalid
- Interface operational

**Sample Output After 1312**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            1312
```

---

### Step 20: Test Boundary Values - Just Above Maximum (9217)
**Objective**: Verify boundary validation at upper limit

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Restore to baseline
configure terminal
interface Ethernet0
mtu 9100
exit
exit

# Attempt MTU 9217 (1 above maximum 9216)
configure terminal
interface Ethernet0
mtu 9217
exit
exit

# Verify MTU unchanged at 9100
show interface status Ethernet0

# Attempt MTU 9216 (maximum - should succeed)
configure terminal
interface Ethernet0
mtu 9216
exit
exit

# Verify MTU changed to 9216
show interface status Ethernet0
```

**Expected Result**:
- **9217 rejected** - above maximum
- **9216 accepted** - exactly at maximum
- Clear boundary between valid/invalid
- Interface operational

**Sample Output After 9216**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            9216
```

---

### Step 21: Test Rapid Invalid MTU Attempts
**Objective**: Verify system stability with rapid invalid MTU configuration attempts

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Rapid invalid MTU attempts
configure terminal
interface Ethernet0
mtu 1000
mtu 10000
mtu 0
mtu 65535
mtu 1311
mtu 9217
exit
exit

# Verify MTU unchanged and system stable
show interface status Ethernet0
```

**Expected Result**:
- All invalid values rejected
- MTU remains at previous valid value
- System handles rapid errors gracefully
- No system instability
- Interface operational

---

### Step 22: Test Invalid MTU with Interface Flap
**Objective**: Verify invalid MTU doesn't affect interface through flap

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Ensure valid MTU
configure terminal
interface Ethernet0
mtu 9100
exit
exit

# Verify baseline
show interface status Ethernet0

# Attempt invalid MTU
configure terminal
interface Ethernet0
mtu 10000
exit
exit

# Flap interface
configure terminal
interface Ethernet0
shutdown
no shutdown
exit
exit

# Verify MTU still at valid value after flap
show interface status Ethernet0
```

**Expected Result**:
- Invalid MTU rejected before flap
- MTU remains 9100 through flap
- Interface comes up normally
- No corruption of valid configuration

---

### Step 23: Verify Running Configuration After Invalid Attempts
**Objective**: Verify invalid MTU attempts don't corrupt running configuration

**Commands (Execute on DUT1)**:
```bash
# After multiple invalid MTU attempts
sonic-cli

# Check running configuration
show running-configuration interface Ethernet0
show running-configuration interface Ethernet4

# Verify configuration clean and valid
show interface status Ethernet0
show interface status Ethernet4
```

**Expected Result**:
- Running configuration shows only valid MTU values
- No invalid entries in configuration
- Configuration file not corrupted
- Both interfaces show valid MTU

**Sample Running Config**:
```
interface Ethernet0
 mtu 9100
 no shutdown
!
```

---

### Step 24: Test Error Message Consistency
**Objective**: Verify consistent error messages for different invalid values

**Commands (Execute on DUT1)**:
```bash
# Test various invalid values and capture error messages
sonic-cli
configure terminal
interface Ethernet0

# Test below minimum
mtu 1311

# Test above maximum
mtu 9217

# Test far below
mtu 100

# Test far above
mtu 20000

# Test non-numeric
mtu invalid

exit
exit
```

**Expected Result**:
- Consistent error message format
- Clear indication of valid range (1312-9216)
- User-friendly error descriptions
- All errors properly reported

**Expected Error Message Pattern**:
```
Error: MTU value must be between 1312 and 9216
% Invalid input detected
Valid range: 1312-9216
```

---

### Step 25: Final State Verification
**Objective**: Verify system in clean state after all negative tests

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify all interfaces have valid MTU
show interface status

# Check specific test interfaces
show interface status Ethernet0
show interface status Ethernet4

# Verify no error conditions
show logging | grep -i error | grep -i mtu | tail -20

# Verify interfaces operational
show interface Ethernet0
show interface Ethernet4

# Check running configuration is clean
show running-configuration interface Ethernet0
show running-configuration interface Ethernet4
```

**Expected Result**:
- All interfaces show valid MTU values
- No invalid MTU entries in configuration
- Interfaces operational
- System stable after negative testing
- No residual errors or warnings

**Sample Final Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            9100
Ethernet4           -                   up             up             10G            9100
```

---

## Validation Points

### CLI Validation (klish mode via sonic-cli)

**Primary Command**: `show interface status`

**Validation Criteria for Negative Tests**:

#### 1. Invalid MTU Rejection
- **Invalid values MUST be rejected**:
  - Below 1312: Rejected with error
  - Above 9216: Rejected with error
  - Non-numeric: Rejected with syntax error
  - Negative: Rejected with error

#### 2. MTU Preservation
- **After invalid attempt**:
  - MTU remains at previous valid value
  - No partial updates
  - Configuration unchanged
  - Running config clean

#### 3. Error Message Quality
- **Clear error messages** indicating:
  - Value out of range
  - Valid range: 1312-9216
  - Syntax error for non-numeric
  - Helpful guidance for user

#### 4. Interface Stability
- **Interface remains operational**:
  - No link flap from invalid attempt
  - Admin/Oper status unchanged
  - No service interruption
  - Stable after error

#### 5. System Stability
- **System handles errors gracefully**:
  - No crashes or hangs
  - No configuration corruption
  - Rapid errors handled properly
  - Resources stable

#### 6. Boundary Validation
- **Precise boundary checking**:
  - 1311: Rejected (below minimum)
  - 1312: Accepted (at minimum)
  - 9216: Accepted (at maximum)
  - 9217: Rejected (above maximum)

---

## Expected Overall Results

### Success Criteria (Negative Tests)

#### 1. Invalid MTU Rejection
- All MTU values < 1312 REJECTED
- All MTU values > 9216 REJECTED
- Non-numeric values REJECTED
- Negative values REJECTED
- Clear error messages provided

#### 2. Configuration Protection
- Invalid values never applied
- MTU remains at previous valid value
- Running configuration not corrupted
- No partial or incomplete updates

#### 3. Error Handling
- Appropriate error messages displayed
- Error messages indicate valid range
- Syntax errors for non-numeric values
- Consistent error format

#### 4. Interface Stability
- Interface operational status unaffected
- No link flaps from invalid attempts
- Service continues normally
- Admin/Oper states stable

#### 5. System Stability
- No system crashes or hangs
- Rapid invalid attempts handled gracefully
- Configuration database not corrupted
- Memory/CPU stable

#### 6. Boundary Precision
- Exact boundary enforcement (1312 min, 9216 max)
- Values at boundary accepted
- Values 1 outside boundary rejected
- No off-by-one errors

### Performance Criteria

- **Error Response Time**: < 1 second
- **Configuration Validation**: Immediate
- **Error Message Display**: < 1 second
- **System Recovery**: Immediate (no recovery needed)
- **Interface Stability**: No impact from errors

### Failure Indicators

**Test should fail if**:
1. Invalid MTU value accepted (< 1312 or > 9216)
2. Invalid MTU partially applied
3. No error message displayed for invalid value
4. Interface goes down due to invalid attempt
5. Configuration corrupted by invalid value
6. System crashes or hangs on invalid value
7. Boundary values incorrectly handled (1311 accepted, 1312 rejected, etc.)
8. Error messages unclear or missing
9. Running configuration shows invalid MTU
10. Multiple invalid attempts cause system instability

---

## Test Execution Summary Template

### Invalid MTU Below Minimum - Rejection Verification

| Invalid MTU | Expected Result | Actual Result | Error Message | MTU Unchanged | Result |
|-------------|-----------------|---------------|---------------|---------------|--------|
| 1311 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| 1000 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| 576 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| 100 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| 0 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| -1 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| -100 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |

### Invalid MTU Above Maximum - Rejection Verification

| Invalid MTU | Expected Result | Actual Result | Error Message | MTU Unchanged | Result |
|-------------|-----------------|---------------|---------------|---------------|--------|
| 9217 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| 10000 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| 16000 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| 65535 | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |

### Invalid MTU Non-Numeric - Rejection Verification

| Invalid MTU | Expected Result | Actual Result | Error Message | MTU Unchanged | Result |
|-------------|-----------------|---------------|---------------|---------------|--------|
| "invalid" | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| "auto" | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| "max" | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |
| "@#$%" | Rejected | Pass/Fail | Yes/No | Yes/No | Pass/Fail |

### Boundary Value Validation

| MTU Value | Within Range? | Expected Result | Actual Result | Result |
|-----------|---------------|-----------------|---------------|--------|
| 1311 | No (below) | Rejected | Pass/Fail | Pass/Fail |
| 1312 | Yes (min) | Accepted | Pass/Fail | Pass/Fail |
| 9216 | Yes (max) | Accepted | Pass/Fail | Pass/Fail |
| 9217 | No (above) | Rejected | Pass/Fail | Pass/Fail |

### System Stability After Invalid Attempts

| Test | Invalid Values Attempted | System Stable | Config Clean | Result |
|------|--------------------------|---------------|--------------|--------|
| Rapid Invalid | Multiple | Yes/No | Yes/No | Pass/Fail |
| With Flap | 10000 | Yes/No | Yes/No | Pass/Fail |
| Multiple Interfaces | Various | Yes/No | Yes/No | Pass/Fail |

---

## Cleanup Steps

After test completion, restore interfaces to stable state:

```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Restore Ethernet0 to standard jumbo MTU
interface Ethernet0
mtu 9100
no shutdown
exit

# Restore Ethernet4 to standard jumbo MTU
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
- Both interfaces at valid MTU (9100)
- All interfaces operational
- No residual errors
- System stable

---

## Test Environment Details

**Command Flow Reference**:
```
1. sonic-cli                    # Enter CLI (klish mode)
2. configure terminal           # Enter config mode
3. interface Ethernet<num>      # Select interface
4. mtu <INVALID_VALUE>          # Attempt invalid MTU
5. # Expected: ERROR MESSAGE
6. exit                         # Exit interface config
7. exit                         # Exit config mode
8. show interface status        # Verify MTU UNCHANGED
```

**Topology Diagram**:
```
+--------------------+                       +--------------------+
|       DUT1         |                       |       DUT2         |
| (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
| 192.168.100.193    | (Invalid MTU Tests)   | 192.168.100.195    |
|                    |<-----Ethernet4------->|                    |
|                    | (Invalid MTU Tests)   |                    |
+--------------------+                       +--------------------+
```

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **Valid MTU Range** (CRITICAL):
   - **Minimum: 1312 bytes**
   - **Maximum: 9216 bytes**
   - Any value outside this range MUST be rejected

3. **Negative Testing Purpose**:
   - Verify input validation works correctly
   - Ensure invalid values cannot corrupt configuration
   - Confirm system stability with invalid input
   - Validate error messages are helpful

4. **Invalid Value Categories**:
   - **Below minimum**: < 1312
   - **Above maximum**: > 9216
   - **Non-numeric**: Strings, keywords, special characters
   - **Negative**: < 0
   - **Zero**: 0 (special case)

5. **Expected Behavior**:
   - Invalid values rejected IMMEDIATELY
   - Clear error message displayed
   - MTU remains at previous valid value
   - Interface remains operational
   - No system instability

6. **Error Message Expectations**:
   - Should indicate valid range (1312-9216)
   - Should be user-friendly
   - Should be consistent across different invalid values
   - Should guide user to correct syntax

7. **Boundary Testing Importance**:
   - 1311 vs 1312: Critical boundary
   - 9216 vs 9217: Critical boundary
   - Validates no off-by-one errors
   - Confirms exact range enforcement

8. **Configuration Integrity**:
   - Running config must never contain invalid MTU
   - Invalid attempts should not corrupt config database
   - System should recover immediately from errors

9. **Common Invalid Values to Test**:
   - **0**: Edge case, zero MTU
   - **576**: Standard IP minimum (but below SONiC minimum)
   - **1311**: Just below minimum
   - **1500**: Actually valid, but good to verify
   - **9217**: Just above maximum
   - **10000**: Common invalid attempt
   - **65535**: Maximum 16-bit value
   - **Negative values**: -1, -100
   - **Non-numeric**: "invalid", "auto", "max"

10. **Testing Best Practices**:
    - Always verify MTU before invalid attempt
    - Always verify MTU after invalid attempt
    - Check error messages for quality
    - Verify interface stability
    - Test multiple interfaces
    - Test rapid invalid attempts
    - Verify configuration file integrity

---

## Additional Validation Commands

For comprehensive negative testing:

```bash
# Before invalid attempt - capture baseline
show interface status Ethernet0
show running-configuration interface Ethernet0

# After invalid attempt - verify unchanged
show interface status Ethernet0
show running-configuration interface Ethernet0

# Check for errors in logs
show logging | grep -i mtu
show logging | grep -i error

# Verify interface operational
show interface Ethernet0

# Check system resources (stability)
show processes cpu
show memory
```

---

## Troubleshooting

### Common Issues and Resolution

**Issue 1**: Invalid MTU value accepted
- **Cause**: Bug in input validation
- **Severity**: CRITICAL
- **Resolution**:
  - Document the issue
  - Report as software bug
  - Verify with vendor
  - Update firmware if fix available

**Issue 2**: No error message displayed
- **Cause**: Silent failure or missing validation
- **Severity**: HIGH
- **Resolution**:
  - Check CLI version
  - Report usability issue
  - Document expected error message

**Issue 3**: Interface goes down after invalid MTU attempt
- **Cause**: Improper error handling
- **Severity**: CRITICAL
- **Resolution**:
  - Bring interface up
  - Report bug
  - Avoid triggering condition

**Issue 4**: Configuration corrupted by invalid value
- **Cause**: Config validation failure
- **Severity**: CRITICAL
- **Resolution**:
  - Restore configuration backup
  - Reload configuration
  - Report critical bug

**Issue 5**: System crash on invalid MTU
- **Cause**: Input validation bug, buffer overflow
- **Severity**: CRITICAL
- **Resolution**:
  - Reboot system
  - Report critical security/stability bug
  - Upgrade firmware

**Issue 6**: Boundary value incorrect (1312 rejected or 1311 accepted)
- **Cause**: Off-by-one error in validation
- **Severity**: MEDIUM to HIGH
- **Resolution**:
  - Document exact boundary behavior
  - Report validation bug
  - Update test expectations if documented behavior

---

## Expected Error Messages Reference

### For MTU Below Minimum (< 1312)

```
Error: MTU value 1311 is below minimum allowed value of 1312
Valid range: 1312-9216
% Invalid input detected
```

### For MTU Above Maximum (> 9216)

```
Error: MTU value 9217 exceeds maximum allowed value of 9216
Valid range: 1312-9216
% Invalid input detected
```

### For Non-Numeric Values

```
% Invalid input detected at '^' marker
Expecting numeric value for MTU
```

### For Negative Values

```
% Invalid input detected
MTU value must be positive
Valid range: 1312-9216
```

**Note**: Exact error messages may vary by SONiC version and CLI implementation

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Test ID**: 1.3.11
- **Test Category**: Interface Events - MTU Changes (Negative Scenarios)
- **Priority**: HIGH (input validation critical)
- **Automation**: Highly recommended for regression
- **Related Test Cases**:
  - TC_INTF_EVENTS_010 (Valid MTU Changes)
  - TC_INTF_EVENTS_001 (Basic Interface Operations)
- **Related Standards**:
  - RFC 791 (IP minimum MTU: 576 bytes)
  - RFC 1122 (Host requirements)
  - RFC 8200 (IPv6 minimum MTU: 1280 bytes)

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Verification Commands**:
```bash
show interface status                      # Display all interface status with MTU
show interface status Ethernet<num>        # Display specific interface status
show interface Ethernet<num>               # Display detailed interface info
show running-configuration interface Ethernet<num>  # Display running config
show logging | grep -i mtu                 # Check MTU-related logs
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**Invalid MTU Attempts** (All should be REJECTED):
```bash
configure terminal                         # Enter configuration mode
interface Ethernet<num>                    # Enter interface configuration

# Below minimum (ALL REJECTED)
mtu 1311                                   # REJECTED - below 1312
mtu 1000                                   # REJECTED - below 1312
mtu 576                                    # REJECTED - below 1312
mtu 100                                    # REJECTED - below 1312
mtu 0                                      # REJECTED - zero

# Above maximum (ALL REJECTED)
mtu 9217                                   # REJECTED - above 9216
mtu 10000                                  # REJECTED - above 9216
mtu 16000                                  # REJECTED - above 9216
mtu 65535                                  # REJECTED - above 9216

# Negative values (ALL REJECTED)
mtu -1                                     # REJECTED - negative
mtu -100                                   # REJECTED - negative

# Non-numeric (ALL REJECTED)
mtu invalid                                # REJECTED - non-numeric
mtu auto                                   # REJECTED - non-numeric
mtu max                                    # REJECTED - non-numeric

exit                                       # Exit interface config
exit                                       # Exit configuration mode
```

**Valid MTU Range**: 1312 ≤ MTU ≤ 9216

**Boundary Values**:
- `mtu 1312` - VALID (minimum)
- `mtu 1311` - INVALID (below minimum)
- `mtu 9216` - VALID (maximum)
- `mtu 9217` - INVALID (above maximum)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.3.11 - Validate if MTU not changes (negative scenario)
