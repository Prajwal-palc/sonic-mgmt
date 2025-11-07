# LLDP Test Cases

## Testcase ID: 1.1.5

### Title
Verify LLDP timers and multiplier

### Objective
To verify that LLDP timers and hold-time multiplier configurations work correctly, and that the TTL (Time To Live) values reflect the configured settings. Ensure neighbors remain stable with custom timer configurations.

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

2. **Configure system-name and description**
   - Configure system-name on both devices
   - Configure system-description on both devices
   - Connect to peer and verify connectivity

3. **Configure timers and multiplier**
   - Configure LLDP timer: `lldp timer <sec>`
   - Configure LLDP multiplier: `lldp multiplier <n>`
   - Test with various timer values (e.g., 5, 10, 30 seconds)
   - Test with various multiplier values (e.g., 2, 4, 6)
   - Calculate expected TTL = timer × multiplier

4. **Verify TTL reflects configured settings**
   - After configuring timers and multiplier, verify TTL in neighbor table
   - Confirm TTL = timer × multiplier
   - Monitor that neighbors remain stable with custom timer configurations

5. **Verify neighbor stability**
   - Monitor LLDP neighbors over time
   - Ensure neighbors are not removed prematurely
   - Verify neighbor entries persist correctly based on timer settings

6. **Verify neighbor removal**
   - Shutdown interface and verify neighbor is removed after TTL expires
   - Re-enable interface and verify neighbor reappears

### Show Commands to Validate

#### Klish Mode (sonic-cli)
**Note**: These commands are currently under development and may not produce output yet. Execute inside `sonic-cli`:
1. `show lldp table`
2. `show lldp neighbor`
3. `show lldp neighbor Ethernet4`
4. `show lldp statistics`
5. `show lldp statistics Ethernet4`

#### Click Mode (sudo config)
**Note**: These commands work properly and need to be executed outside sonic-cli:
1. `show lldp neighbor`
2. `show lldp table`

### Expected Output

1. **Timer and Hold-Multiplier Configuration**
   - LLDP timer configuration is successfully applied
   - LLDP multiplier configuration is successfully applied
   - Configuration changes are reflected immediately

2. **TTL Verification**
   - TTL (Time To Live) value in neighbor table reflects the configured settings
   - TTL = timer × multiplier
   - Example: If timer = 10 seconds and multiplier = 4, then TTL = 40 seconds

3. **Neighbor Stability**
   - LLDP neighbors remain stable with custom timer configurations
   - No premature neighbor removal
   - Neighbor entries are refreshed within the configured timer interval
   - No missing or dropped neighbor entries during normal operation

4. **Neighbor Removal Behavior**
   - When interface is shut down, neighbor entry is removed after TTL expires
   - When interface is brought back up, neighbor entry reappears within the timer interval

5. **Command Validation**
   - All show commands execute successfully in both klish and click modes
   - Klish commands may not show output (development in progress)
   - Click commands show accurate LLDP information
   - TTL values are correctly displayed in neighbor output

### Pass/Fail Criteria

**Pass Criteria:**
- LLDP timer configuration is successfully applied and persists
- LLDP multiplier configuration is successfully applied and persists
- TTL value correctly reflects timer × multiplier calculation
- LLDP neighbors remain stable with custom timer settings
- No premature neighbor removal occurs
- Neighbor entries are refreshed appropriately within timer intervals
- Neighbor removal after interface shutdown happens after TTL expiration
- Neighbor reappears after interface comes back up
- All show commands execute without errors in both klish and click modes
- TTL values displayed in neighbor output match configured values

**Fail Criteria:**
- Timer or multiplier configuration fails or does not persist
- TTL value does not match timer × multiplier calculation
- LLDP neighbors are removed prematurely (before TTL expires)
- LLDP neighbors fail to refresh within the configured timer interval
- Neighbor entries do not reappear after interface is brought back up
- Show commands fail or return incorrect information
- TTL values in output do not reflect the configured settings
- System crashes or exhibits unstable behavior when timers are modified
