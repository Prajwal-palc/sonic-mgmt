# LLDP Test Cases

## Testcase ID: 1.1.4

### Title
Verify LLDP neighbor discovery by enabling LLDP per interface

### Objective
To verify that LLDP neighbor discovery works correctly when LLDP is enabled per interface, and to ensure that per-interface enable/disable functionality properly controls neighbor discovery and removal.

### Test Topology
- **Devices**: smic_sonic1, smic_sonic2
- **Test Interfaces**: Ethernet4 (connected between smic_sonic1 and smic_sonic2)
- **Testbed File**: /home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml

### Test Procedure

1. **Configure and verify LLDP globally and interface level**
   - Fetch Ethernet interface information from testbed: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
   - Enter interface mode for Ethernet4
   - Execute `no shutdown` on Ethernet4 interface to ensure it is up
   - Test LLDP enable/disable in config mode:
     - Execute: `lldp enable` (global config mode)
     - Execute: `no lldp enable` (global config mode)
     - Execute: `lldp enable` again to re-enable globally
   - Test LLDP enable/disable in interface mode:
     - Enter interface configuration mode for Ethernet4
     - Execute: `lldp enable` (interface mode)
     - Execute: `no lldp enable` (interface mode)
     - Execute: `lldp enable` again to re-enable at interface level

2. **Enable LLDP globally and on interface**
   - Ensure LLDP is enabled globally: `lldp enable` in config mode
   - Ensure LLDP is enabled on Ethernet4: `lldp enable` in interface config mode
   - Verify LLDP configuration is applied

3. **Connect to peer**
   - Ensure DUT (smic_sonic1) is connected to peer (smic_sonic2) via Ethernet4
   - Wait for LLDP neighbor discovery to complete

4. **Show LLDP neighbors/detail and verify TLVs**
   - Run `show lldp neighbors` command
   - Run `show lldp neighbors detail` command
   - Verify the following TLVs (Type-Length-Value) are present and correct:
     - Chassis ID TLV: Verify peer's chassis identifier is displayed
     - Port ID TLV: Verify peer's port identifier (Ethernet4) is displayed
     - System Name TLV: Verify peer's hostname (smic_sonic2) is displayed
     - System Capabilities TLV: Verify peer's system capabilities are displayed
     - TTL (Time To Live) TLV: Verify TTL value is present
   - Verify all TLV information is accurate and complete

5. **Disable LLDP on interface**
   - Enter interface configuration mode for Ethernet4
   - Execute: `no lldp enable` (interface mode)
   - Verify LLDP is disabled on the interface

6. **Verify neighbor removal**
   - Wait for LLDP hold time to expire (or TTL timeout)
   - Run `show lldp neighbors` command
   - Verify that the neighbor entry for Ethernet4 is removed from the neighbor table
   - Run `show lldp neighbors detail` command
   - Verify that detailed information for Ethernet4 neighbor is no longer present

### Show Commands to Validate

#### Klish Mode (inside sonic-cli)
**Note**: These commands are currently under development and may not produce output
1. `show lldp table`
2. `show lldp neighbor`
3. `show lldp neighbor Ethernet4`
4. `show lldp statistics`
5. `show lldp statistics Ethernet4`

#### Click Mode (outside sonic-cli)
**Note**: These commands are fully functional
1. `show lldp neighbor`
2. `show lldp table`

### Expected Output

1. **LLDP Enable/Disable Control**
   - LLDP can be enabled/disabled globally in config mode
   - LLDP can be enabled/disabled per interface in interface config mode
   - Configuration changes take effect immediately
   - Interface-level settings override global settings when explicitly configured

2. **Interface Shutdown Handling**
   - `no shutdown` command successfully brings up Ethernet4 interface
   - Interface state transitions are reflected in LLDP neighbor discovery

3. **Per-Interface Enable/Disable Reflects in Neighbor Table**
   - When LLDP is enabled globally AND on interface:
     - Neighbor appears in LLDP neighbor table
     - Neighbor information is complete and accurate
     - All TLVs are present and correct
   - When LLDP is disabled on interface (while still enabled globally):
     - Neighbor entry is removed from LLDP neighbor table
     - Neighbor detail information is no longer available
     - Interface no longer participates in LLDP neighbor discovery

4. **TLV Verification**
   - When LLDP is enabled, all mandatory TLVs are present:
     - **Chassis ID**: Shows the peer's chassis identifier
     - **Port ID**: Shows the peer's port identifier (Ethernet4)
     - **System Name**: Shows the peer's hostname (smic_sonic2)
     - **System Capabilities**: Shows the peer's system capabilities
     - **TTL**: Shows Time To Live value for the LLDP neighbor entry
   - All TLV values are accurate and match the peer device configuration

5. **Neighbor Table Consistency**
   - LLDP neighbor table shows consistent information across different show commands
   - Detail view provides comprehensive TLV information
   - Interface-specific commands show only relevant neighbor information
   - Statistics increment appropriately when LLDP is active on interface

6. **Command Execution**
   - All show commands execute successfully in klish mode (when available)
   - All show commands execute successfully in click mode
   - Output format is consistent and readable
   - Information displayed is accurate and reflects current LLDP state

### Pass/Fail Criteria

**Pass Criteria:**
- LLDP can be successfully enabled and disabled globally in config mode
- LLDP can be successfully enabled and disabled per interface in interface mode
- Interface `no shutdown` command works correctly on Ethernet4
- When LLDP is enabled globally and on Ethernet4:
  - LLDP neighbor is discovered successfully
  - Neighbor appears in LLDP neighbor table
  - All mandatory TLVs (Chassis ID, Port ID, System Name, System Capabilities, TTL) are present and correct
  - TLV information is accurate and complete
- When LLDP is disabled on Ethernet4 interface:
  - Neighbor entry is removed from the neighbor table
  - Neighbor detail information is no longer available
  - Per-interface enable/disable reflects correctly in neighbor table and detail view
- All show commands execute without errors in both klish and click modes (where supported)
- LLDP statistics reflect interface-level LLDP activity accurately
- Configuration changes take effect immediately without requiring service restart

**Fail Criteria:**
- LLDP enable/disable commands fail or do not take effect globally
- LLDP enable/disable commands fail or do not take effect at interface level
- Interface remains in shutdown state after `no shutdown` command
- LLDP neighbor is not discovered when LLDP is enabled both globally and on interface
- Any mandatory TLV is missing or incorrect when neighbor is discovered
- Neighbor entry does not disappear when LLDP is disabled on interface
- Neighbor entry persists after LLDP is disabled on interface
- Per-interface enable/disable does not reflect correctly in neighbor table or detail view
- Show commands fail or return incorrect information
- LLDP statistics do not reflect interface-level activity
- Configuration changes require LLDP service restart to take effect
- Interface-level LLDP disable does not prevent neighbor discovery on that specific interface
