# Test Cases - Interface Events Validation (Interface Description Updates)

## Test Case ID: TC_INTF_EVENTS_012

### Test Case Name
Validate Interface Description Updates

### Test Objective
Validate that interface description can be configured, modified, and removed successfully and that the description changes are accurately reflected in CLI outputs. Ensure that description configurations are properly applied, displayed in interface status, and persist across configuration changes and interface flaps. Verify that the interface remains operational after description changes and that various description formats (alphanumeric, special characters, spaces) are properly handled.

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
5. Interfaces should be in operational state

---

## Test Procedure

### Step 1: Initial Configuration - Bring Interface to UP State
**Objective**: Ensure test interfaces are in operational "up" state before testing description changes

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
**Objective**: Capture baseline interface status before adding descriptions

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status

# Check specific interface status
show interface status Ethernet0
show interface status Ethernet4
```

**Expected Result**:
- Interfaces display current state (description may be empty or "-")
- Baseline status captured
- Output stored for comparison

**Sample Output Format**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            9100
Ethernet4           -                   up             up             10G            9100
```

**Note**: Description field may show "-" or be empty initially

---

### Step 3: Add Simple Description to Ethernet0
**Objective**: Configure a simple alphanumeric description

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Add description
description TestPort1

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Description configuration accepted without errors
- Configuration applied successfully
- No error messages

---

### Step 4: Verify Description on Ethernet0
**Objective**: Verify that description is reflected in CLI output

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
- Interface status shows description as "TestPort1"
- Description accurately displayed in show commands
- Configuration change reflected immediately

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           TestPort1           up             up             10G            9100
```

**Validation Points**:
1. Description field shows "TestPort1"
2. Interface remains operational
3. Configuration change successful

---

### Step 5: Add Description with Spaces to Ethernet0
**Objective**: Configure a description containing spaces

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Add description with spaces
description Test Port One

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Description with spaces accepted
- Configuration applied successfully
- Full description preserved

---

### Step 6: Verify Description with Spaces
**Objective**: Verify description with spaces is displayed correctly

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows description as "Test Port One"
- Spaces preserved in description
- Complete description displayed

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           Test Port One       up             up             10G            9100
```

---

### Step 7: Add Description with Special Characters
**Objective**: Configure a description containing special characters

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Add description with special characters (underscores, hyphens)
description Server_Port-01

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Description with special characters accepted
- Configuration applied successfully
- Special characters preserved

---

### Step 8: Verify Description with Special Characters
**Objective**: Verify special characters are displayed correctly

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows description as "Server_Port-01"
- Special characters (underscore, hyphen) preserved
- Complete description displayed

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           Server_Port-01      up             up             10G            9100
```

---

### Step 9: Add Long Description to Ethernet0
**Objective**: Configure a longer description to test length handling

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Add longer description
description Connection to Server Room Rack 01 Port 24

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Long description accepted (subject to platform limits)
- Configuration applied successfully
- Description may be truncated in display if exceeds field width

---

### Step 10: Verify Long Description
**Objective**: Verify long description handling

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0

# Check running configuration (shows full description)
show running-configuration interface Ethernet0
```

**Expected Result**:
- Interface status shows description (may be truncated for display)
- Running configuration shows full description
- No data loss in configuration

**Sample Output**:
```
Name                Description              Admin          Oper           Speed          MTU
-------------------------------------------------------------------------------------------------
Ethernet0           Connection to Server...  up             up             10G            9100
```

**Running Configuration**:
```
interface Ethernet0
 description Connection to Server Room Rack 01 Port 24
 no shutdown
!
```

---

### Step 11: Modify Existing Description
**Objective**: Change description from one value to another

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Change description to new value
description Uplink Port

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Description modified successfully
- Old description replaced with new one
- Configuration applied

---

### Step 12: Verify Modified Description
**Objective**: Verify description change is reflected

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows new description "Uplink Port"
- Old description no longer displayed
- Change applied successfully

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           Uplink Port         up             up             10G            9100
```

---

### Step 13: Remove Description from Ethernet0
**Objective**: Remove description configuration

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Remove description using "no" command
no description

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Description removed successfully
- Configuration cleared
- No errors

---

### Step 14: Verify Description Removal
**Objective**: Verify description is removed from interface

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows description as "-" or empty
- Description field cleared
- Interface remains operational

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           -                   up             up             10G            9100
```

---

### Step 15: Add Descriptions to Multiple Interfaces
**Objective**: Configure descriptions on multiple interfaces

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0
interface Ethernet0
description Port to DUT2 Eth0
exit

# Configure Ethernet4
interface Ethernet4
description Port to DUT2 Eth4
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Descriptions configured on both interfaces
- Each interface has unique description
- Configuration applied successfully

---

### Step 16: Verify Multiple Interface Descriptions
**Objective**: Verify descriptions on multiple interfaces

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check all interface status
show interface status

# Check specific interfaces
show interface status Ethernet0
show interface status Ethernet4
```

**Expected Result**:
- Both interfaces show their respective descriptions
- Each description unique and correct
- All interface parameters displayed correctly

**Sample Output**:
```
Name                Description              Admin          Oper           Speed          MTU
-------------------------------------------------------------------------------------------------
Ethernet0           Port to DUT2 Eth0        up             up             10G            9100
Ethernet4           Port to DUT2 Eth4        up             up             10G            9100
```

---

### Step 17: Description Persistence Through Interface Flap
**Objective**: Verify description persists through interface shutdown/no shutdown

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Configure description
configure terminal
interface Ethernet0
description Persistent Port
exit
exit

# Verify description
show interface status Ethernet0

# Flap interface
configure terminal
interface Ethernet0
shutdown
no shutdown
exit
exit

# Verify description persists
show interface status Ethernet0
```

**Expected Result**:
- Description persists through interface flap
- Interface comes back up with same description
- No need to reconfigure description

**Sample Output After Flap**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           Persistent Port     up             up             10G            9100
```

---

### Step 18: Description with Numeric Characters
**Objective**: Configure description containing numbers

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Add description with numbers
description Port123

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Description with numbers accepted
- Configuration applied successfully
- Numeric characters preserved

---

### Step 19: Verify Numeric Description
**Objective**: Verify numeric characters in description

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0
```

**Expected Result**:
- Interface status shows description as "Port123"
- Numbers preserved in description
- Complete description displayed

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           Port123             up             up             10G            9100
```

---

### Step 20: Description with Mixed Case
**Objective**: Configure description with mixed upper and lower case

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Select Ethernet0
interface Ethernet0

# Add mixed case description
description UplinkToCore

# Exit interface configuration
exit

# Exit configuration mode
exit
```

**Expected Result**:
- Mixed case description accepted
- Case preserved in configuration
- Configuration applied successfully

---

### Step 21: Verify Mixed Case Description
**Objective**: Verify case sensitivity in description

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Check interface status
show interface status Ethernet0

# Check running configuration
show running-configuration interface Ethernet0
```

**Expected Result**:
- Description shows with original case: "UplinkToCore"
- Case preserved in both display and configuration
- No case conversion

**Sample Output**:
```
Name                Description         Admin          Oper           Speed          MTU
------------------------------------------------------------------------------------------
Ethernet0           UplinkToCore        up             up             10G            9100
```

---

### Step 22: Sequential Description Changes
**Objective**: Validate multiple sequential description changes

**Commands (Execute on DUT1)**:
```bash
# Sequence of description changes
sonic-cli

# Change 1
configure terminal
interface Ethernet0
description First Description
exit
exit
show interface status Ethernet0

# Change 2
configure terminal
interface Ethernet0
description Second Description
exit
exit
show interface status Ethernet0

# Change 3
configure terminal
interface Ethernet0
description Third Description
exit
exit
show interface status Ethernet0

# Change 4 (final)
configure terminal
interface Ethernet0
description Final Description
exit
exit
show interface status Ethernet0
```

**Expected Result**:
- Each description change applied successfully
- Each change reflected in CLI output immediately
- Latest description always displayed
- No accumulation of old descriptions

---

### Step 23: Verify Running Configuration
**Objective**: Verify description is saved in running configuration

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Configure a description
configure terminal
interface Ethernet0
description Production Port
exit
exit

# Check running configuration
show running-configuration interface Ethernet0
```

**Expected Result**:
- Running configuration shows description line
- Configuration accurately reflects applied description
- Format: `description Production Port`

**Sample Output**:
```
interface Ethernet0
 description Production Port
 no shutdown
!
```

---

### Step 24: Description on Interface with Other Configurations
**Objective**: Verify description works alongside other interface configurations

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Configure multiple parameters including description
configure terminal
interface Ethernet0
description Test Interface
mtu 9100
no shutdown
exit
exit

# Verify all configurations
show interface status Ethernet0
show running-configuration interface Ethernet0
```

**Expected Result**:
- Description applied alongside other configurations
- All configurations coexist properly
- No conflicts between parameters

**Sample Running Config**:
```
interface Ethernet0
 description Test Interface
 mtu 9100
 no shutdown
!
```

---

### Step 25: Empty Description Test
**Objective**: Test behavior with empty description

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Configure description
configure terminal
interface Ethernet0
description Test
exit
exit

# Verify description exists
show interface status Ethernet0

# Remove description
configure terminal
interface Ethernet0
no description
exit
exit

# Verify description removed
show interface status Ethernet0
```

**Expected Result**:
- After "no description", field shows "-" or empty
- Description properly cleared
- Interface operational

---

### Step 26: Final State Verification
**Objective**: Verify system is in clean state after all description tests

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify all interfaces
show interface status

# Check specific test interfaces
show interface status Ethernet0
show interface status Ethernet4

# Verify no error conditions
show logging | grep -i error | tail -20

# Check running configuration
show running-configuration interface Ethernet0
show running-configuration interface Ethernet4
```

**Expected Result**:
- All interfaces display correct descriptions (or no description)
- No residual error conditions
- All CLI commands responsive
- System stable after all configuration changes
- Interfaces operational

---

## Validation Points

### CLI Validation (klish mode via sonic-cli)

**Primary Command**: `show interface status`

**Validation Criteria**:

#### 1. Description Display
- **After description configuration**:
  - Description field in `show interface status` matches configured value
  - Change reflected immediately or within seconds
  - CLI output accurate and consistent

#### 2. Supported Description Formats
Common description patterns to test:
- **Simple**: `description Port1`
- **With spaces**: `description Test Port`
- **With numbers**: `description Port123`
- **With special chars**: `description Server_Port-01`
- **Mixed case**: `description UplinkToCore`
- **Long text**: `description Connection to Server Room Rack 01`

#### 3. Interface Stability
- Interface operational state maintained after description changes
- No link flap from description configuration
- Description changes don't affect traffic

#### 4. Configuration Accuracy
- CLI output matches configured description
- Running configuration shows description
- No discrepancies between configuration and status
- Configuration persists through interface flaps

#### 5. Description Removal
- "no description" command clears description
- Field shows "-" or empty after removal
- Interface remains operational after removal

---

## Expected Overall Results

### Success Criteria

#### 1. Description Configuration Success
- Description commands execute successfully
- Configuration applies immediately or within seconds
- CLI reflects new description
- Running configuration shows description

#### 2. Interface Operational Continuity
- Interface remains operational after description changes
- No link flaps from description configuration
- No service interruption
- Description purely cosmetic (no functional impact)

#### 3. CLI Accuracy
- `show interface status` accurately displays configured description
- Description matches what was configured
- All interface parameters correctly displayed
- No truncation unless exceeds display width

#### 4. Configuration Persistence
- Description persists through interface flaps
- Configuration saved in running-config
- Description maintained across admin state changes
- No need to reconfigure after interface recovery

#### 5. Character Support
- Alphanumeric characters supported
- Spaces preserved in descriptions
- Special characters (underscore, hyphen) supported
- Mixed case preserved
- Numbers supported

#### 6. Modification and Removal
- Description can be changed multiple times
- Latest description always displayed
- "no description" removes description
- Interface operational after removal

### Performance Criteria

- **Configuration Application Time**: < 1 second
- **CLI Response Time**: < 3 seconds for show commands
- **Description Change**: Immediate, no delay
- **Configuration Persistence**: Immediate in running-config
- **No Impact on Traffic**: Zero packet loss

### Failure Indicators

**Test should fail if**:
1. Description command rejected
2. CLI does not show configured description
3. Description not preserved through interface flap
4. Running configuration does not reflect description
5. Description changes cause interface to go down
6. Special characters or spaces not preserved
7. Description changes cause system instability
8. "no description" doesn't clear description
9. CLI output is incorrect or inconsistent
10. System crashes or becomes unresponsive

---

## Test Execution Summary Template

### Description Configuration Verification

| Interface | Description Set | Verified in Status | Verified in Config | Result |
|-----------|-----------------|--------------------|--------------------|--------|
| Ethernet0 | TestPort1 | Pass/Fail | Pass/Fail | Pass/Fail |
| Ethernet0 | Test Port One | Pass/Fail | Pass/Fail | Pass/Fail |
| Ethernet0 | Server_Port-01 | Pass/Fail | Pass/Fail | Pass/Fail |
| Ethernet0 | Port123 | Pass/Fail | Pass/Fail | Pass/Fail |
| Ethernet4 | Port to DUT2 Eth4 | Pass/Fail | Pass/Fail | Pass/Fail |

### Description Modification Tests

| Test | Initial Description | Modified To | Verified | Result |
|------|---------------------|-------------|----------|--------|
| Modify | First Description | Second Description | Pass/Fail | Pass/Fail |
| Remove | Production Port | (empty) | Pass/Fail | Pass/Fail |

### Persistence Validation

| Test | Description | After Flap | Running Config | Result |
|------|-------------|------------|----------------|--------|
| Flap Test | Persistent Port | Persistent Port | Present | Pass/Fail |
| Sequential | Third Description | Third Description | Present | Pass/Fail |

---

## Cleanup Steps

After test completion, clean up interface descriptions:

```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Remove description from Ethernet0
interface Ethernet0
no description
no shutdown
exit

# Remove description from Ethernet4
interface Ethernet4
no description
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
- Interfaces show no description (or "-")
- All interfaces operational
- No residual configuration
- System stable

---

## Test Environment Details

**Command Flow Reference**:
```
1. sonic-cli                    # Enter CLI (klish mode)
2. configure terminal           # Enter config mode
3. interface Ethernet<num>      # Select interface
4. description <text>           # Set description
5. exit                         # Exit interface config
6. exit                         # Exit config mode
7. show interface status        # Verify description
8. (to remove: "no description")
```

**Topology Diagram**:
```
+--------------------+                       +--------------------+
|       DUT1         |                       |       DUT2         |
| (smic_sonic1)      |<-----Ethernet0------->| (smic_sonic2)      |
| 192.168.100.193    |  (Description Tests)  | 192.168.100.195    |
|                    |<-----Ethernet4------->|                    |
|                    |  (Description Tests)  |                    |
+--------------------+                       +--------------------+
```

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **Description Characteristics**:
   - Cosmetic field (does not affect interface operation)
   - Helps identify interface purpose/connection
   - Displayed in `show interface status`
   - Stored in running and startup configuration

3. **Supported Characters**:
   - Letters: A-Z, a-z
   - Numbers: 0-9
   - Spaces: Allowed
   - Special characters: Underscore (_), hyphen (-), period (.)
   - Mixed case: Preserved

4. **Description Length**:
   - Maximum length varies by platform (typically 64-255 characters)
   - Display may truncate long descriptions in `show interface status`
   - Full description always in `show running-configuration`

5. **Best Practices**:
   - Use meaningful descriptions
   - Include connection endpoint information
   - Keep descriptions concise for better display
   - Use consistent naming convention
   - Document VLAN or network information if relevant

6. **Common Description Patterns**:
   ```
   description Uplink to Core Switch
   description Server VLAN 100
   description Port to Building A Floor 2
   description Backup Link
   description Management Interface
   ```

7. **Description vs. Interface Name**:
   - Interface name (e.g., Ethernet0) is fixed
   - Description is user-configurable text
   - Description helps identify interface purpose

8. **Configuration Persistence**:
   - Description saved in running configuration
   - Persists through interface flaps
   - Saved to startup-config with "write memory" or equivalent
   - Survives reboots if configuration saved

9. **Display Formatting**:
   - `show interface status`: May truncate long descriptions
   - `show interface <name>`: May show full description
   - `show running-configuration`: Always shows full description

10. **Operational Impact**:
    - Description changes have ZERO impact on:
      - Interface operational status
      - Traffic forwarding
      - Protocol operation
      - Performance
    - Purely administrative/documentation field

---

## Additional Validation Commands

For comprehensive testing:

```bash
# View description in different contexts
show interface status Ethernet0
show interface Ethernet0
show running-configuration interface Ethernet0

# View all interface descriptions
show interface status

# Search for specific description
show interface status | grep "Server"

# Detailed interface view
show interface Ethernet0
```

---

## Troubleshooting

### Common Issues and Resolution

**Issue 1**: Description not displayed in show interface status
- **Cause**: Description not configured or cleared
- **Resolution**:
  - Verify configuration: `show running-configuration interface`
  - Reconfigure description
  - Check for syntax errors

**Issue 2**: Description truncated in display
- **Cause**: Description too long for display column width
- **Resolution**:
  - View running configuration for full description
  - Use shorter description if full display needed
  - This is expected behavior for long descriptions

**Issue 3**: Description disappears after interface flap
- **Cause**: Configuration not saved or software issue
- **Resolution**:
  - Verify running configuration
  - Reconfigure if needed
  - Save configuration
  - Report potential bug if reproducible

**Issue 4**: Special characters not accepted
- **Cause**: Unsupported special characters
- **Resolution**:
  - Use supported characters: letters, numbers, space, underscore, hyphen
  - Avoid: quotes, brackets, pipes, etc.
  - Check platform documentation

**Issue 5**: "no description" doesn't work
- **Cause**: Syntax error or software issue
- **Resolution**:
  - Verify command syntax: `no description`
  - Check CLI mode (must be in interface config mode)
  - Try reconfiguring empty description if "no" fails

---

## Description Format Examples

### Good Description Examples

```bash
# Simple and clear
description Uplink Port

# With connection information
description To Core-Switch-01 Port 1/0/24

# With VLAN information
description Access Port VLAN 100

# With location
description Server Room Rack 5 U24

# With purpose
description Internet Gateway Link

# With device information
description Connected to FW-01 eth0

# With service information
description Management Interface

# With redundancy information
description Primary Link to DC2
```

### Description Best Practices

1. **Be Descriptive**: Clearly indicate port purpose
2. **Include Endpoint**: Show what device/port is connected
3. **Keep Concise**: Avoid overly long descriptions
4. **Use Consistent Format**: Maintain naming convention
5. **Include Key Info**: VLAN, service, location as needed
6. **Avoid Sensitive Data**: Don't include passwords or sensitive info

---

## References

- **Testbed Configuration**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Test ID**: 1.3.12
- **Test Category**: Interface Events - Description Updates
- **Priority**: Medium
- **Automation**: Recommended for automation
- **Related Test Cases**:
  - TC_INTF_EVENTS_001 (Basic Admin/Link State Changes)
  - TC_INTF_EVENTS_009 (Speed Changes)
  - TC_INTF_EVENTS_010 (MTU Changes)

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Interface Commands**:
```bash
show interface status                      # Display all interface status with descriptions
show interface status Ethernet<num>        # Display specific interface status
show interface Ethernet<num>               # Display detailed interface info
show running-configuration interface Ethernet<num>  # Display running config
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**Description Configuration**:
```bash
configure terminal                         # Enter configuration mode
interface Ethernet<num>                    # Enter interface configuration

# Set description (various formats)
description <text>                         # Simple description
description Text with spaces               # Description with spaces
description Server_Port-01                 # With special characters
description Port123                        # With numbers

# Remove description
no description                             # Clear description

exit                                       # Exit interface config
exit                                       # Exit configuration mode
```

**Description Examples**:
```bash
description Uplink                         # Simple
description Test Port One                  # With spaces
description Server_Port-01                 # With special chars
description Port123                        # With numbers
description UplinkToCore                   # Mixed case
no description                             # Remove description
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-17
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.3.12 - Validate if description updates
