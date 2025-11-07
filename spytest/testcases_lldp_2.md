# LLDP Test Cases

## Testcase ID: 1.1.2

### Title
Verify LLDP neighbor discovery by enabling LLDP, connecting a peer

### Objective
To verify that LLDP neighbor discovery works correctly when LLDP is enabled globally and on interfaces, and to ensure that neighbor information is properly updated when links change state.

### Test Topology
- **Devices**: smic_sonic1, smic_sonic2
- **Test Interfaces**: Ethernet4 (connected between smic_sonic1 and smic_sonic2)
- **Testbed File**: /home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml

### Test Procedure

1. **Enable LLDP globally and on test interfaces**
   - Fetch Ethernet interface information from testbed: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
   - Enable LLDP globally on DUT
   - Enable LLDP on Ethernet4 interface

2. **Connect DUT to peer**
   - Ensure DUT (smic_sonic1) is connected to peer (smic_sonic2) via Ethernet4

3. **Verify LLDP neighbor discovery**
   - Run `show lldp neighbors`
   - Run `show lldp neighbors detail`

4. **Verify TLVs (Type-Length-Value)**
   - Verify Chassis ID TLV is present and correct
   - Verify Port ID TLV is present and correct
   - Verify System Name TLV is present and correct
   - Verify System Capabilities TLV is present and correct

5. **Test link state changes**
   - Disconnect peer by shutting down the interface: `shutdown` interface Ethernet4
   - Verify neighbor entry is removed
   - Reconnect peer by bringing up the interface: `no shutdown` interface Ethernet4
   - Verify neighbor entry reappears

### Show Commands to Validate

#### Regular Mode
1. `show lldp table`
2. `show lldp neighbor`
3. `show lldp neighbor Ethernet4`
4. `show lldp statistics`
5. `show lldp statistics Ethernet4`

#### Config Mode (sudo config)
1. `show lldp neighbor`
2. `show lldp table`

### Expected Output

1. **Neighbor Discovery**
   - Neighbor appears in LLDP neighbor table when link is up
   - Neighbor disappears from LLDP neighbor table when link is down (after shutdown)
   - Neighbor reappears when link is brought back up (after no shutdown)

2. **TLV Verification**
   - All mandatory TLVs are present:
     - Chassis ID: Should show the peer's chassis identifier
     - Port ID: Should show the peer's port identifier (Ethernet4)
     - System Name: Should show the peer's hostname (smic_sonic2)
     - System Capabilities: Should show the peer's system capabilities

3. **Statistics**
   - LLDP statistics increment appropriately:
     - Frame counters increase as LLDP frames are exchanged
     - No errors in frame reception/transmission
     - TLV counters reflect received TLV information

4. **Command Validation**
   - All show commands execute successfully in both regular and config modes
   - Output format is consistent and readable
   - Information displayed is accurate and complete

### Pass/Fail Criteria

**Pass Criteria:**
- LLDP neighbor is discovered successfully after enabling LLDP
- All mandatory TLVs (Chassis ID, Port ID, System Name, System Capabilities) are present and correct
- Neighbor entry disappears when interface is shut down
- Neighbor entry reappears when interface is brought back up
- All show commands execute without errors in both regular and config modes
- LLDP statistics increment correctly

**Fail Criteria:**
- LLDP neighbor is not discovered
- Any mandatory TLV is missing or incorrect
- Neighbor entry does not update correctly with link state changes
- Show commands fail or return incorrect information
- LLDP statistics do not increment or show errors
