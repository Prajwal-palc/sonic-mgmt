# LLDP Test Cases

## Testcase ID: 1.1.6

### Title
Verify system-name/description and management-address TLV advertised

### Objective
To verify that LLDP system-name, system-description, and management-address TLVs are correctly configured and advertised to neighbors. Ensure that configured values appear in neighbor advertisements and can be properly validated.

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
   - Re-enable LLDP for testing

2. **Configure system-name and system-description**
   - Configure LLDP system-name: `lldp system-name <name>`
   - Configure LLDP system-description: `lldp system-description "<description>"`
   - Test with various system names and descriptions
   - Verify configuration is accepted and stored

3. **Configure management-address TLV**
   - Enable management-address TLV advertisement: `lldp tlv-select management-address`
   - Verify TLV selection is configured correctly

4. **Configure per-interface management address**
   - Configure management address on interface: `lldp tlv-set management-address ipv4 <ip>`
   - Test with valid IPv4 addresses
   - Verify per-interface management address configuration

5. **Verify TLV advertisement to neighbors**
   - Check that configured system-name appears in neighbor output
   - Check that configured system-description appears in neighbor output
   - Check that configured management-address appears in neighbor output
   - Verify all values match the configured settings

### Show Commands to Validate

#### Klish Mode (sonic-cli)
**Note**: These commands are currently under development and may not produce output yet. Execute inside `sonic-cli`:
1. `show lldp neighbor`
2. `show lldp neighbor Ethernet4`

#### Click Mode (sudo config)
**Note**: These commands work properly and need to be executed outside sonic-cli:
1. `show lldp neighbor`

### Expected Output

1. **System-Name Configuration**
   - LLDP system-name is successfully configured
   - System-name persists across LLDP restarts
   - Neighbor shows configured system-name in SysName field

2. **System-Description Configuration**
   - LLDP system-description is successfully configured
   - System-description persists across LLDP restarts
   - Neighbor shows configured system-description in SysDescr field

3. **Management-Address TLV Configuration**
   - Management-address TLV selection is successfully configured
   - TLV selection persists in configuration
   - Management-address is advertised to neighbors

4. **Per-Interface Management Address**
   - Per-interface management address is successfully configured
   - Configuration is applied to the specific interface
   - Neighbor shows configured management address in MgmtIP field

5. **Neighbor Advertisement Validation**
   - Neighbor output displays all configured TLV values:
     - **SysName**: Shows configured system-name
     - **SysDescr**: Shows configured system-description
     - **MgmtIP**: Shows configured management-address
   - All fields match exactly with configured values
   - TLV values are properly formatted and readable

6. **Command Validation**
   - All show commands execute successfully in both klish and click modes
   - Klish commands may not show output (development in progress)
   - Click commands show accurate LLDP neighbor information with TLV details

### Pass/Fail Criteria

**Pass Criteria:**
- LLDP system-name configuration is successfully applied and persists
- LLDP system-description configuration is successfully applied and persists
- Management-address TLV selection is successfully configured
- Per-interface management address is successfully configured
- Neighbor output shows configured SysName field matching configured system-name
- Neighbor output shows configured SysDescr field matching configured system-description
- Neighbor output shows configured MgmtIP field matching configured management-address
- All TLV values are correctly advertised and received by neighbors
- Configuration persists across interface flaps and LLDP restarts
- All show commands execute without errors in both klish and click modes
- TLV fields are properly formatted and contain expected data

**Fail Criteria:**
- System-name or system-description configuration fails or does not persist
- Management-address TLV configuration fails
- Per-interface management address configuration fails
- Neighbor output does not show configured SysName value
- Neighbor output does not show configured SysDescr value
- Neighbor output does not show configured MgmtIP value
- TLV values in neighbor output do not match configured values
- Configuration is lost after interface flap or LLDP restart
- Show commands fail or return incorrect information
- TLV fields are missing, malformed, or contain incorrect data
- System crashes or exhibits unstable behavior when TLVs are configured
