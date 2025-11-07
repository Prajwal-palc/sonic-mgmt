# LLDP Test Cases

## Testcase ID: 1.1.3

### Title
Verify LLDP with transmit-only, receive-only and both modes

### Objective
To verify that LLDP operates correctly in different transmission modes (transmit-only, receive-only, and both transmit/receive) and that mode enforcement behaves as expected at both global and interface levels.

### Test Topology
- **Devices**: smic_sonic1, smic_sonic2
- **Test Interfaces**: Ethernet4 (connected between smic_sonic1 and smic_sonic2)
- **Testbed File**: /home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml

### Test Procedure

1. **Configure LLDP globally and at interface level**
   - Fetch Ethernet interface information from testbed: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
   - Enter interface mode for Ethernet4
   - Execute `no shutdown` on Ethernet4 interface to ensure it is up
   - Enable LLDP globally: `lldp enable`
   - Disable LLDP globally: `no lldp enable`
   - Re-enable LLDP globally: `lldp enable`
   - Enter interface configuration mode and enable LLDP at interface level
   - Verify LLDP configuration is applied

2. **Enable transmit-only mode globally**
   - Execute: `lldp transmit`
   - Confirm that receive mode is deactivated automatically
   - Verify transmit-only mode via show commands
   - Verify that LLDP frames are being transmitted
   - Verify that neighbor information is NOT being received/updated

3. **Verify receive-only mode**
   - Disable transmit mode: `no lldp transmit`
   - Execute: `lldp receive`
   - Confirm that transmit mode is deactivated automatically when receive is enabled
   - Verify receive-only mode via show commands
   - Verify that LLDP frames are being received
   - Verify that LLDP frames are NOT being transmitted

4. **Enable both transmit and receive modes**
   - Execute: `no lldp receive`
   - Execute: `no lldp transmit`
   - Verify that both transmit and receive are now active (default behavior)
   - Verify bidirectional LLDP operation

5. **Validate with show commands**
   - Run all show commands in klish mode (inside sonic-cli)
   - Run all show commands in click mode (outside sonic-cli, using sudo config)
   - Verify output consistency and accuracy

### Show Commands to Validate

#### Klish Mode (inside sonic-cli)
**Note**: These commands are currently under development and may not produce output
1. `show lldp table`
2. `show lldp neighbor`
3. `show lldp neighbor Ethernet4`
4. `show lldp statistics`
5. `show lldp statistics Ethernet4`

#### Click Mode (outside sonic-cli, using sudo config)
**Note**: These commands are fully functional
1. `show lldp neighbor`
2. `show lldp table`

### Expected Output

1. **LLDP Enable/Disable**
   - LLDP can be enabled/disabled globally in config mode
   - LLDP can be enabled/disabled at interface level
   - Configuration changes are reflected immediately

2. **Transmit-Only Mode**
   - When `lldp transmit` is configured:
     - DUT sends LLDP frames on Ethernet4
     - DUT does NOT process received LLDP frames
     - Neighbor table remains empty or stale (no updates from received frames)
     - Statistics show transmitted frames incrementing
     - Statistics show received frames NOT being processed

3. **Receive-Only Mode**
   - When `lldp receive` is configured:
     - DUT processes received LLDP frames from peer
     - DUT does NOT send LLDP frames
     - Neighbor table is populated with peer information
     - Statistics show received frames incrementing
     - Statistics show transmitted frames NOT incrementing

4. **Both Modes Active**
   - When both transmit and receive are active (after `no lldp receive` and `no lldp transmit`):
     - DUT sends LLDP frames on Ethernet4
     - DUT processes received LLDP frames from peer
     - Neighbor table is populated and updated
     - Statistics show both transmitted and received frames incrementing
     - Bidirectional LLDP communication is fully functional

5. **Mode Enforcement**
   - Modes are mutually exclusive when explicitly configured:
     - Enabling `lldp transmit` disables receive functionality
     - Enabling `lldp receive` disables transmit functionality
   - Disabling both explicit modes (`no lldp transmit` and `no lldp receive`) enables both directions (default behavior)

6. **Statistics Alignment**
   - Frame counters align with the configured mode:
     - Transmit-only: TX counters increment, RX counters do not
     - Receive-only: RX counters increment, TX counters do not
     - Both active: Both TX and RX counters increment
   - No errors in frame transmission/reception for active modes

7. **Neighbor Visibility**
   - Neighbors are visible in the LLDP table only when receive mode is active:
     - Transmit-only: No neighbors visible
     - Receive-only: Neighbors visible and updated
     - Both active: Neighbors visible and updated

### Pass/Fail Criteria

**Pass Criteria:**
- LLDP can be successfully enabled and disabled globally and at interface level
- Interface `no shutdown` command works correctly on Ethernet4
- Transmit-only mode enforces correctly:
  - LLDP frames are transmitted
  - LLDP frames are not processed when received
  - Neighbor table is empty or not updated
- Receive-only mode enforces correctly:
  - LLDP frames are received and processed
  - LLDP frames are not transmitted
  - Neighbor table is populated with peer information
- Both modes active (default behavior) works correctly:
  - Bidirectional LLDP communication is functional
  - Neighbor table is populated and updated
- Mode transitions work smoothly without requiring LLDP restart
- Statistics accurately reflect the active mode (TX/RX counters align with mode)
- All show commands execute without errors in both klish and click modes
- Command output is accurate and consistent with the configured mode

**Fail Criteria:**
- LLDP enable/disable commands fail or do not take effect
- Interface remains in shutdown state after `no shutdown` command
- Transmit-only mode allows received frames to be processed
- Receive-only mode transmits LLDP frames
- Both modes cannot be activated simultaneously (default behavior fails)
- Mode enforcement is not respected (e.g., both TX and RX active when only one should be)
- Statistics do not align with the configured mode
- Neighbor table shows entries when in transmit-only mode
- Neighbor table is empty when in receive-only or both modes with peer connected
- Show commands fail or return incorrect/inconsistent information
- Mode changes require LLDP service restart to take effect
