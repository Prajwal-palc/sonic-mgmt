# LLDP Test Cases

## Testcase ID: 1.1.10

### Title
Save and reboot; verify LLDP post-reboot

### Objective
To verify that LLDP configuration persists across device reboots and that LLDP functionality is fully restored after reboot. Ensure that LLDP neighbor discovery works correctly post-reboot, configuration settings are retained, and no stale entries remain in the neighbor table.

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
   - Verify basic LLDP functionality

2. **Enable LLDP globally and on interfaces**
   - Enable LLDP globally on both DUTs
   - Enable LLDP on test interfaces (Ethernet4) on both DUTs
   - Verify LLDP is active and operational
   - Verify neighbor discovery before reboot

3. **Capture pre-reboot configuration and state**
   - Record LLDP global enable state
   - Record LLDP interface enable state
   - Record neighbor information (neighbor name, port, TTL)
   - Capture LLDP table entries
   - Document current configuration

4. **Save configuration**
   - Save configuration using klish: `write memory`
   - Verify save operation success
   - Save configuration using click: `sudo config save -y`
   - Verify configuration file is updated
   - Confirm configuration written to persistent storage

5. **Perform device reboot**
   - Reboot device: `sudo reboot`
   - Wait for device to come back online
   - Verify system is accessible after reboot
   - Allow boot process to complete

6. **Verify LLDP configuration persistence post-reboot**
   - Check LLDP global enable state is retained
   - Check LLDP interface enable state is retained
   - Verify LLDP daemon is running
   - Confirm all LLDP settings match pre-reboot configuration

7. **Verify LLDP functionality post-reboot**
   - Verify LLDP is actively sending/receiving advertisements
   - Check LLDP statistics show activity
   - Confirm LLDP timers are functioning
   - Verify protocol operation is normal

8. **Verify neighbor discovery post-reboot**
   - Wait for neighbor discovery period
   - Verify neighbors are rediscovered
   - Check neighbor information matches pre-reboot data
   - Confirm neighbor table is populated correctly

9. **Verify LLDP table integrity**
   - Check LLDP table for completeness
   - Verify all expected neighbors are present
   - Confirm neighbor information is accurate
   - Validate TTL values are correct

10. **Verify no stale entries**
    - Check for any stale or invalid entries
    - Verify no orphaned neighbor entries
    - Confirm table contains only valid, active neighbors
    - Ensure clean table state post-reboot

11. **Compare pre-reboot and post-reboot state**
    - Compare neighbor counts
    - Compare neighbor details
    - Verify configuration consistency
    - Confirm no configuration loss

12. **Test configuration changes post-reboot**
    - Modify LLDP configuration
    - Verify changes take effect
    - Confirm system responds to configuration updates
    - Validate LLDP control plane is functional

### Show Commands to Validate

#### Klish Mode (sonic-cli)
**Note**: These commands are currently under development and may not produce output yet. Execute inside `sonic-cli`:
1. `show lldp table`
2. `show lldp neighbor`
3. `show lldp neighbor Ethernet4`
4. `show lldp statistics`
5. `write memory` (to save configuration)
6. `show running-config` (to verify configuration)

#### Click Mode (sudo config)
**Note**: These commands work properly and need to be executed outside sonic-cli:
1. `show lldp table`
2. `show lldp neighbor`
3. `sudo config save -y` (to save configuration)
4. `show runningconfiguration all` (to verify configuration)

### Expected Output

1. **Configuration Persistence**
   - LLDP global enable state persists across reboot
   - LLDP interface enable state persists across reboot
   - All LLDP configuration settings are retained
   - No configuration loss or corruption occurs
   - Settings match pre-reboot configuration exactly

2. **LLDP Functionality Restoration**
   - LLDP daemon starts automatically after reboot
   - LLDP protocol operates normally post-reboot
   - LLDP advertisements are sent and received
   - Timers and TTL mechanisms function correctly
   - All LLDP features work as expected

3. **Neighbor Discovery Post-Reboot**
   - Neighbors are rediscovered after reboot
   - Discovery occurs within expected timeframe (typically 30-60 seconds)
   - All expected neighbors appear in the table
   - Neighbor information is complete and accurate
   - TTL values are properly initialized

4. **Neighbor Table Correctness**
   - Table contains all expected neighbor entries
   - Neighbor information matches pre-reboot state
   - No missing neighbors
   - No duplicate entries
   - Table reflects current network topology accurately

5. **No Stale Entries**
   - No stale or invalid neighbor entries exist
   - No orphaned entries from before reboot
   - All entries have valid, current information
   - TTL values are fresh and within expected range
   - Table is clean with only active neighbors

6. **System Stability**
   - System boots successfully
   - No crashes or failures during boot
   - LLDP service starts without errors
   - System logs show normal operation
   - No errors or warnings related to LLDP

7. **Save Operation Success**
   - `write memory` command succeeds in klish
   - `sudo config save -y` command succeeds in click
   - Configuration file is updated
   - No errors during save operation
   - Confirmation message displayed

8. **Reboot Recovery**
   - System comes back online after reboot
   - All services start properly
   - Network connectivity is restored
   - LLDP resumes operation automatically
   - No manual intervention required

### Pass/Fail Criteria

**Pass Criteria:**
- Device reboots successfully and comes back online
- LLDP global enable configuration persists across reboot
- LLDP interface enable configuration persists across reboot
- All LLDP configuration settings are retained exactly as configured
- LLDP daemon starts automatically after reboot
- LLDP functionality is fully restored post-reboot
- Neighbors are rediscovered within expected timeframe (30-90 seconds)
- All expected neighbors appear in the neighbor table
- Neighbor information matches pre-reboot state
- No stale or invalid entries exist in the neighbor table
- LLDP table is clean and accurate post-reboot
- Configuration save commands (write memory, config save) execute successfully
- No errors or warnings in system logs related to LLDP
- System remains stable throughout reboot process
- LLDP statistics show normal activity post-reboot
- All show commands execute without errors in both klish and click modes
- Post-reboot neighbor count matches pre-reboot count (or expected count)

**Fail Criteria:**
- Device fails to reboot or does not come back online
- LLDP configuration is lost after reboot
- LLDP global or interface enable state is not retained
- LLDP daemon fails to start after reboot
- LLDP functionality is not restored post-reboot
- Neighbors are not rediscovered after reboot
- Neighbor table is empty or incomplete post-reboot
- Stale entries persist in the neighbor table after reboot
- Neighbor information is incorrect or corrupted
- Configuration save commands fail
- System crashes or becomes unstable during/after reboot
- LLDP errors or warnings appear in system logs
- LLDP statistics show no activity post-reboot
- Show commands fail or return incorrect data
- Post-reboot configuration differs from pre-reboot configuration
- Manual intervention required to restore LLDP operation
- Excessive delay in neighbor rediscovery (> 5 minutes)

### Additional Notes

- **Reboot Type**: This test uses a standard warm/cold reboot (sudo reboot)
- **Boot Time**: Allow 2-5 minutes for complete system boot and service initialization
- **Discovery Time**: Allow 30-90 seconds after boot for neighbor rediscovery
- **Configuration Persistence**: SONiC uses config_db.json for persistent storage
- **Save Commands**: Both `write memory` (klish) and `config save` (click) should be tested
- **Pre-Reboot Verification**: Ensure baseline LLDP operation before reboot
- **Post-Reboot Wait**: Allow sufficient time for LLDP daemon to initialize and discover neighbors
- **Comparison**: Compare detailed neighbor information, not just counts
- **Multiple Reboots**: Consider testing multiple reboot cycles for robustness
- **Peer State**: Peer device should remain operational during reboot of DUT
- **Logging**: Capture system logs before and after reboot for troubleshooting
- **Timestamps**: Record timestamps for reboot, boot complete, and neighbor discovery

### Configuration File Locations

- **SONiC Config**: `/etc/sonic/config_db.json`
- **Running Config**: Retrieved via show running-configuration
- **Startup Config**: Same as config_db.json after save

### Timing Expectations

- **Reboot Duration**: 2-5 minutes for complete system boot
- **Service Start Time**: < 30 seconds after boot for LLDP daemon
- **Neighbor Discovery**: 30-90 seconds after LLDP daemon start
- **Total Recovery**: < 7 minutes from reboot command to full LLDP operation

### Test Variations

1. **Multiple Reboots**: Reboot device 2-3 times to verify consistency
2. **Different LLDP Configs**: Test with various LLDP settings (timers, TLVs, etc.)
3. **Cold Boot**: Test with power cycle instead of warm reboot
4. **Fast Reboot**: Test with SONiC fast-reboot if supported
5. **Configuration Modifications**: Change LLDP config before reboot and verify both old and new settings persist appropriately
6. **Both Devices Reboot**: Reboot both DUTs simultaneously and verify bidirectional recovery

### Related Test Cases

- **1.1.2**: LLDP neighbor discovery (baseline functionality)
- **1.1.5**: LLDP timers and multiplier (TTL verification post-reboot)
- **1.1.8**: Rapid enable/disable (stress test before reboot)

### Security Considerations

- Verify saved configuration file has appropriate permissions
- Ensure no sensitive information is exposed in configuration
- Validate configuration integrity (no corruption or tampering)
