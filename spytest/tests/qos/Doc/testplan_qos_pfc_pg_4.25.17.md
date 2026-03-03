# Test Plan: PFC-Priority-PG Configuration Persistence After Reboot

## Test Metadata

| Field | Value |
|-------|-------|
| **Test ID** | 4.25.17 |
| **Feature** | QoS (Quality of Service) |
| **Sub-Feature** | PFC (Priority Flow Control) - Configuration Persistence |
| **Test Case** | Verify PFC-Priority-PG configuration persistence after reboot |
| **Test Type** | Functional / Persistence Testing |
| **Test Level** | System |
| **Author** | QoS Test Suite |
| **Date Created** | 2026-03-03 |
| **Known Issue** | SoCCI-110 (Configuration not persisting after reboot) |

---

## Test Objective

Validate that PFC-Priority-PG map configurations and interface bindings persist correctly across device reboot cycles, ensuring:
- PFC-Priority-PG maps are restored from saved configuration
- Interface-to-map bindings are maintained
- Priority-to-PG mappings remain intact
- PFC priorities remain enabled on interfaces
- System functionality is fully operational after reboot

---

## Prerequisites

### Topology Requirements
- **Minimum Topology**: Single DUT (D1) with at least one test interface
- **Supported Platforms**: Hardware and Virtual SONiC devices
- **Required Interfaces**: At least one Ethernet interface (e.g., Ethernet4)

### Software Requirements
- SONiC OS with QoS and PFC support
- CLI Mode: Klish (IS-CLI)
- Configuration persistence support (CONFIG_DB, config save)

### Initial Configuration
- Device accessible via SSH
- Clean initial configuration state
- No pre-existing PFC-Priority-PG maps
- Device reboot capability available

### Time Requirements
- Estimated execution time: 10-15 minutes
- Reboot time: 3-5 minutes (varies by platform)

---

## Test Procedure

### Step 1: Record Initial System State

**Description**: Capture baseline system state before configuration

**Commands**:
```bash
sonic# show version
sonic# show qos map pfc-priority-pg
sonic# show qos interface Ethernet4
sonic# show system status
sonic# show uptime
```

**Expected Result**:
- System version and uptime recorded
- No existing PFC-Priority-PG maps
- Interface in default QoS state
- System status: Running

---

### Step 2: Create PFC-Priority-PG Map

**Description**: Create a new PFC-Priority-PG map with comprehensive priority mappings

**Commands**:
```bash
sonic# configure terminal
sonic(config)# qos map pfc-priority-pg pfcmap
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 0 pg 0
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 1-2 pg 2
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 3,4 pg 4
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 5,6-7 pg 5
sonic(config-pfc-priority-pg-map-pfcmap)# exit
```

**Expected Result**:
- Map "pfcmap" created successfully
- All 8 PFC priorities (0-7) mapped to appropriate PGs:
  - Priority 0 → PG 0
  - Priorities 1-2 → PG 2
  - Priorities 3-4 → PG 4
  - Priorities 5-7 → PG 5
- Configuration mode exits to global config mode

---

### Step 3: Verify Map Creation

**Description**: Verify the PFC-Priority-PG map is created correctly

**Commands**:
```bash
sonic(config)# end
sonic# show qos map pfc-priority-pg
```

**Expected Output**:
```
PFC-Priority-Priority-Group-MAP: pfcmap
----------------------------
    PFC Priority   PG
----------------------------
    0              0
    1              2
    2              2
    3              4
    4              4
    5              5
    6              5
    7              5
----------------------------
```

**Expected Result**:
- Map displays all configured priority-to-PG mappings
- All 8 priorities properly mapped
- Output format is clear and readable

---

### Step 4: Apply Map to Interface

**Description**: Bind the PFC-Priority-PG map to test interface

**Commands**:
```bash
sonic# configure terminal
sonic(config)# interface Ethernet 4
sonic(conf-if-Ethernet4)# qos-map pfc-priority-pg pfcmap
```

**Expected Result**:
- Command executes successfully
- No error messages displayed
- Map applied to interface Ethernet4

---

### Step 5: Enable PFC Priorities on Interface

**Description**: Enable priority-flow-control for specific priorities

**Commands**:
```bash
sonic(conf-if-Ethernet4)# priority-flow-control priority 3
sonic(conf-if-Ethernet4)# priority-flow-control priority 4
sonic(conf-if-Ethernet4)# exit
sonic(config)# end
```

**Expected Result**:
- PFC enabled on priorities 3 and 4
- Commands execute without errors
- Configuration changes applied

---

### Step 6: Verify Interface Configuration

**Description**: Verify complete interface QoS and PFC configuration

**Commands**:
```bash
sonic# show qos interface Ethernet4
```

**Expected Output**:
```
          pfc-priority-pg-map: pfcmap
          PFC Watchdog
            Status            : off
            Action            : N/A
            Detection Time    : 0ms
            Restoration Time  : infinite(0ms)
```

**Additional Verification**:
```bash
sonic# show pfc priority Ethernet4
```

**Expected Output**:
```
Interface Ethernet4 PFC priorities:
  Priority 3: enabled
  Priority 4: enabled
```

**Expected Result**:
- Interface shows "pfc-priority-pg-map: pfcmap"
- PFC priorities 3 and 4 are enabled
- PFC Watchdog status displayed
- Configuration is complete and correct

---

### Step 7: Verify Running Configuration

**Description**: Check that configuration appears in running-config

**Commands**:
```bash
sonic# show running-config | grep -A 20 "qos map pfc-priority-pg pfcmap"
sonic# show running-config interface Ethernet 4
```

**Expected Output**:
```
qos map pfc-priority-pg pfcmap
  pfc-priority 0 pg 0
  pfc-priority 1-2 pg 2
  pfc-priority 3,4 pg 4
  pfc-priority 5,6-7 pg 5
!
interface Ethernet4
  qos-map pfc-priority-pg pfcmap
  priority-flow-control priority 3
  priority-flow-control priority 4
!
```

**Expected Result**:
- PFC map configuration present in running-config
- Interface configuration includes map binding
- PFC priority enablement shown
- Configuration is syntactically correct

---

### Step 8: Save Configuration

**Description**: Save running configuration to startup configuration

**Commands**:
```bash
sonic# write memory
```

**Alternative Command**:
```bash
sonic# copy running-config startup-config
```

**Expected Output**:
```
Building configuration...
[OK]
```

**Verification**:
```bash
sonic# show startup-config | grep -A 20 "qos map pfc-priority-pg pfcmap"
```

**Expected Result**:
- Configuration saved successfully
- "[OK]" message displayed
- Startup-config contains PFC-Priority-PG configuration
- Startup-config matches running-config for QoS settings

---

### Step 9: Record Pre-Reboot State

**Description**: Capture system state before reboot for comparison

**Commands**:
```bash
sonic# show qos map pfc-priority-pg | display json
sonic# show qos interface Ethernet4 | display json
sonic# show pfc counters
sonic# show system status
```

**Expected Result**:
- All configuration details captured
- JSON output saved for comparison
- PFC counters baseline recorded
- System status: Running and healthy

---

### Step 10: Reboot the Device

**Description**: Perform system reboot to test configuration persistence

**Commands**:
```bash
sonic# reload
```

**Confirmation Prompt**:
```
System configuration has been modified. Save? [yes/no/cancel]: yes
Proceed with reload? [confirm]
```

**Expected Behavior**:
- Configuration save prompt appears
- User confirms save and reload
- Device begins reboot sequence
- SSH connection terminates
- Device reboots completely

**Time Required**: 3-5 minutes (varies by platform)

---

### Step 11: Wait for Device to Come Back Online

**Description**: Monitor device boot process and SSH availability

**Verification Steps**:
1. Wait for device to reboot (typically 3-5 minutes)
2. Monitor SSH port availability: `ping <device_ip>`
3. Attempt SSH connection periodically
4. Verify system services are running

**Commands** (from test host):
```bash
# Wait for device to respond
while ! ping -c 1 <device_ip> > /dev/null 2>&1; do
    echo "Waiting for device..."
    sleep 10
done

# Wait for SSH
while ! nc -z <device_ip> 22; do
    echo "Waiting for SSH..."
    sleep 5
done

# Allow system initialization
sleep 30
```

**Expected Result**:
- Device responds to ping
- SSH port (22) becomes available
- System completes initialization
- Device is accessible via SSH

---

### Step 12: Reconnect and Verify System Status

**Description**: Establish SSH connection and verify system health

**Commands**:
```bash
ssh admin@<device_ip>
sonic# show version
sonic# show system status
sonic# show uptime
```

**Expected Result**:
- SSH connection successful
- System version matches pre-reboot
- System status: Running
- Uptime is reset (low value)
- All critical services running

---

### Step 13: Verify PFC-Priority-PG Map Persistence

**Description**: Verify the PFC-Priority-PG map exists after reboot

**Commands**:
```bash
sonic# show qos map pfc-priority-pg
```

**Expected Output**:
```
PFC-Priority-Priority-Group-MAP: pfcmap
----------------------------
    PFC Priority   PG
----------------------------
    0              0
    1              2
    2              2
    3              4
    4              4
    5              5
    6              5
    7              5
----------------------------
```

**Expected Result**:
- Map "pfcmap" exists after reboot
- All priority-to-PG mappings intact:
  - Priority 0 → PG 0
  - Priorities 1-2 → PG 2
  - Priorities 3-4 → PG 4
  - Priorities 5-7 → PG 5
- Configuration exactly matches pre-reboot state

---

### Step 14: Verify Interface Map Binding Persistence

**Description**: Verify the map is still applied to interface after reboot

**Commands**:
```bash
sonic# show qos interface Ethernet4
```

**Expected Output**:
```
          pfc-priority-pg-map: pfcmap
          PFC Watchdog
            Status            : off
            Action            : N/A
            Detection Time    : 0ms
            Restoration Time  : infinite(0ms)
```

**Expected Result**:
- Interface Ethernet4 shows "pfc-priority-pg-map: pfcmap"
- Map binding persisted correctly
- PFC Watchdog configuration maintained
- Interface configuration complete

---

### Step 15: Verify PFC Priority Enablement Persistence

**Description**: Verify PFC priorities remain enabled after reboot

**Commands**:
```bash
sonic# show pfc priority Ethernet4
```

**Expected Output**:
```
Interface Ethernet4 PFC priorities:
  Priority 3: enabled
  Priority 4: enabled
```

**Expected Result**:
- Priority 3 remains enabled
- Priority 4 remains enabled
- PFC priority configuration persisted
- No additional priorities enabled

---

### Step 16: Verify Running Configuration After Reboot

**Description**: Compare running-config to pre-reboot configuration

**Commands**:
```bash
sonic# show running-config | grep -A 20 "qos map pfc-priority-pg pfcmap"
sonic# show running-config interface Ethernet 4
```

**Expected Output**:
```
qos map pfc-priority-pg pfcmap
  pfc-priority 0 pg 0
  pfc-priority 1-2 pg 2
  pfc-priority 3,4 pg 4
  pfc-priority 5,6-7 pg 5
!
interface Ethernet4
  qos-map pfc-priority-pg pfcmap
  priority-flow-control priority 3
  priority-flow-control priority 4
!
```

**Expected Result**:
- Running-config matches pre-reboot state
- All QoS configurations present
- Interface configuration intact
- No configuration loss or corruption

---

### Step 17: Verify PFC Counters Functionality

**Description**: Verify PFC counters are functional after reboot

**Commands**:
```bash
sonic# show pfc counters
sonic# show pfc counters interface Ethernet4
```

**Expected Output**:
```
Interface Ethernet4 PFC Counters:
  Priority  RxPause  TxPause
  --------  -------  -------
  0         0        0
  1         0        0
  2         0        0
  3         0        0
  4         0        0
  5         0        0
  6         0        0
  7         0        0
```

**Expected Result**:
- PFC counters are accessible
- Counters display for all priorities (0-7)
- Counter values start at 0 after reboot
- No errors accessing counter information

---

### Step 18: Test Configuration Modification After Reboot

**Description**: Verify configuration can be modified after reboot

**Commands**:
```bash
sonic# configure terminal
sonic(config)# qos map pfc-priority-pg pfcmap
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 0 pg 1
sonic(config-pfc-priority-pg-map-pfcmap)# exit
sonic(config)# end
sonic# show qos map pfc-priority-pg pfcmap
```

**Expected Result**:
- Configuration changes accepted
- System allows modifications to existing map
- Changes take effect immediately
- No errors or configuration corruption

**Cleanup**:
```bash
sonic# configure terminal
sonic(config)# qos map pfc-priority-pg pfcmap
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 0 pg 0
sonic(config-pfc-priority-pg-map-pfcmap)# exit
sonic(config)# end
```

---

### Step 19: Verify Startup Configuration

**Description**: Verify startup-config still contains saved configuration

**Commands**:
```bash
sonic# show startup-config | grep -A 20 "qos map pfc-priority-pg pfcmap"
```

**Expected Result**:
- Startup-config intact after reboot
- Configuration matches running-config
- No corruption or data loss
- Config file format is correct

---

### Step 20: Complete Post-Reboot Validation Summary

**Description**: Comprehensive validation checklist

**Validation Checklist**:
```
✓ Device rebooted successfully
✓ System services running normally
✓ PFC-Priority-PG map "pfcmap" exists
✓ All priority-to-PG mappings correct (0→0, 1-2→2, 3-4→4, 5-7→5)
✓ Map applied to interface Ethernet4
✓ PFC priorities 3 and 4 enabled on Ethernet4
✓ Running-config matches pre-reboot state
✓ Startup-config intact
✓ PFC counters functional
✓ Configuration can be modified
```

**Expected Result**:
- All validation items pass
- Configuration fully persisted
- System fully operational
- No degradation in functionality

---

## Test Validation Criteria

### Success Criteria

✅ **Configuration Persistence**:
- PFC-Priority-PG map survives reboot
- All priority-to-PG mappings intact
- Map name and structure preserved

✅ **Interface Binding Persistence**:
- Map-to-interface binding maintained
- Interface configuration restored correctly
- QoS settings on interface preserved

✅ **PFC Priority Persistence**:
- Enabled PFC priorities remain enabled
- Priority 3 and 4 status maintained
- No unexpected priority changes

✅ **Configuration Files**:
- Running-config matches pre-reboot state
- Startup-config unchanged after reboot
- Config save/reload cycle successful

✅ **System Functionality**:
- Device boots successfully
- All services operational
- SSH access restored
- CLI commands functional

✅ **Post-Reboot Operations**:
- Configuration can be modified
- Show commands work correctly
- PFC counters accessible
- No errors or warnings

### Failure Criteria

❌ PFC-Priority-PG map missing after reboot
❌ Priority-to-PG mappings lost or corrupted
❌ Interface-to-map binding not restored
❌ PFC priorities disabled after reboot
❌ Running-config does not match pre-reboot state
❌ Startup-config corrupted or empty
❌ Device fails to boot
❌ Services not operational after reboot
❌ Configuration cannot be modified after reboot
❌ PFC counters not functional

---

## Actual Test Results

### Test Execution Summary
- **Status**: ❌ **FAIL**
- **Date Executed**: 2026-03-03
- **Known Issue**: SoCCI-110 (Configuration persistence failure)
- **Execution Environment**: SONiC Platform

### Detailed Failure Analysis

**Pre-Reboot State**: ✅ PASS
- Map "pfcmap" created successfully
- All priority mappings configured correctly
- Map applied to interface Ethernet4
- PFC priorities 3 and 4 enabled
- Configuration saved with "write memory"

**Reboot Process**: ✅ PASS
- Device rebooted successfully
- System came back online
- SSH access restored
- Services started normally

**Post-Reboot Validation**: ❌ FAIL

**Issue 1: Map Configuration Lost**
```bash
sonic# show qos map pfc-priority-pg
# Expected: pfcmap with all mappings
# Actual: Empty output or map not found
```
- PFC-Priority-PG map "pfcmap" not present after reboot
- All priority-to-PG mappings lost

**Issue 2: Interface Binding Lost**
```bash
sonic# show qos interface Ethernet4
# Expected: pfc-priority-pg-map: pfcmap
# Actual: No PFC map shown
```
Output:
```
          PFC Watchdog
            Status            : off
            Action            : N/A
            Detection Time    : 0ms
            Restoration Time  : infinite(0ms)
```
- No "pfc-priority-pg-map: pfcmap" line present
- Interface-to-map binding not restored

**Issue 3: PFC Priority Enablement Lost** (Possibly)
```bash
sonic# show pfc priority Ethernet4
# Status unclear - may also be lost
```

**Root Cause Analysis**:
- Configuration saved to startup-config successfully
- Device boots and loads startup-config
- QoS PFC-Priority-PG map configuration not persisting
- Possible CONFIG_DB schema issue
- Possible service startup order issue
- Known bug: SoCCI-110

---

## Known Issues and Workarounds

### Issue: SoCCI-110

**Description**: PFC-Priority-PG map configurations do not persist across device reboots despite successful configuration save.

**Symptoms**:
- Configuration saves without errors
- Map exists before reboot
- Map missing after reboot
- Interface binding lost

**Affected Versions**: [To be documented]

**Workaround**: None available - requires software fix

**Status**: Open

**Priority**: High (affects production deployments)

---

## Configuration Examples

### Complete Test Configuration

```bash
# Create PFC-Priority-PG map
qos map pfc-priority-pg pfcmap
  pfc-priority 0 pg 0
  pfc-priority 1-2 pg 2
  pfc-priority 3,4 pg 4
  pfc-priority 5,6-7 pg 5
!

# Apply to interface
interface Ethernet4
  qos-map pfc-priority-pg pfcmap
  priority-flow-control priority 3
  priority-flow-control priority 4
!
```

### Minimal Test Configuration

```bash
# Minimal test case
qos map pfc-priority-pg test_persist
  pfc-priority 3 pg 3
!

interface Ethernet4
  qos-map pfc-priority-pg test_persist
!
```

---

## Troubleshooting Guide

### Pre-Reboot Checks

1. **Verify configuration in running-config**:
   ```bash
   show running-config | include pfc-priority
   ```

2. **Verify configuration saved**:
   ```bash
   show startup-config | include pfc-priority
   ```

3. **Check CONFIG_DB**:
   ```bash
   redis-cli -n 4 HGETALL "MAP_PFC_PRIORITY_TO_PRIORITY_GROUP|pfcmap"
   ```

4. **Verify config files on disk**:
   ```bash
   cat /etc/sonic/config_db.json | grep -A 10 PFC_PRIORITY
   ```

### Post-Reboot Checks

1. **Check if configuration was loaded**:
   ```bash
   show running-config | include pfc-priority
   ```

2. **Check CONFIG_DB after boot**:
   ```bash
   redis-cli -n 4 KEYS "*PFC*"
   redis-cli -n 4 HGETALL "MAP_PFC_PRIORITY_TO_PRIORITY_GROUP|pfcmap"
   ```

3. **Check system logs**:
   ```bash
   show logging | include -i pfc
   show logging | include -i config
   ```

4. **Verify config file loaded**:
   ```bash
   ls -la /etc/sonic/config_db.json
   cat /etc/sonic/config_db.json | grep -A 10 PFC_PRIORITY
   ```

### Common Issues

**Issue**: Map exists in startup-config but not loaded
- Check service startup order
- Verify config load logs
- Check for schema validation errors

**Issue**: Config save appears successful but not in startup-config
- Verify write permissions
- Check disk space
- Verify config file not corrupted

---

## Related Test Cases

- **4.25.13**: Verify PFC-Priority-PG map creation via CLI (prerequisite)
- **4.25.14**: Verify CLI rejection for invalid configurations (negative testing)
- **4.25.15**: Delete Active PFC Map testing
- **4.25.16**: Verify PFC Priority to Priority-Group mapping functionality
- **4.25.18**: Configuration backup and restore testing (if exists)

---

## Test Automation

### Test Script Location
```
tests/qos/test_qos_pfc_priority_pg_map_persistence.py
```

### Variables Configuration
```
vars/qos/vars_qos_pfc_pg_map_persistence.yaml
```

### How to Execute
```bash
./bin/spytest --testbed ./testbeds/testbed_vs_1node.yaml \
    tests/qos/test_qos_pfc_priority_pg_map_persistence.py::test_pfc_map_persistence_reboot \
    --logs-path ./logs/qos_persistence_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native
```

### Automation Considerations

**Important**: This test requires device reboot capability
- Test execution time: 10-15 minutes
- Reboot adds 3-5 minutes overhead
- Mark as `@pytest.mark.reboot` for test selection
- Consider impact on CI/CD pipeline duration

---

## References

### SONiC Documentation
- SONiC Configuration Persistence Guide
- CONFIG_DB Schema Reference
- QoS Configuration Guide
- PFC (Priority Flow Control) Architecture

### Standards
- IEEE 802.1Qbb - Priority-based Flow Control
- Data Center Bridging (DCB) Standards

### Configuration Management
- SONiC Config Save/Reload Process
- Config DB Backup and Restore
- Startup Config Processing

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-03 | QoS Test Team | Initial test plan creation |
| 1.1 | 2026-03-03 | QoS Test Team | Added SoCCI-110 issue documentation |

---

## Appendix A: Complete Test Command Sequence

```bash
# === Pre-Reboot Configuration ===

# Step 1-2: Create PFC-Priority-PG map
sonic# configure terminal
sonic(config)# qos map pfc-priority-pg pfcmap
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 0 pg 0
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 1-2 pg 2
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 3,4 pg 4
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 5,6-7 pg 5
sonic(config-pfc-priority-pg-map-pfcmap)# exit

# Step 3: Verify map
sonic(config)# end
sonic# show qos map pfc-priority-pg

# Step 4-5: Apply to interface and enable PFC
sonic# configure terminal
sonic(config)# interface Ethernet 4
sonic(conf-if-Ethernet4)# qos-map pfc-priority-pg pfcmap
sonic(conf-if-Ethernet4)# priority-flow-control priority 3
sonic(conf-if-Ethernet4)# priority-flow-control priority 4
sonic(conf-if-Ethernet4)# exit
sonic(config)# end

# Step 6: Verify interface configuration
sonic# show qos interface Ethernet4
sonic# show pfc priority Ethernet4

# Step 7-8: Save configuration
sonic# show running-config | grep -A 20 "qos map pfc-priority-pg pfcmap"
sonic# write memory

# Step 9: Record state
sonic# show qos map pfc-priority-pg | display json
sonic# show qos interface Ethernet4 | display json

# Step 10: Reboot
sonic# reload
# Confirm save and reload

# === Post-Reboot Validation ===

# Step 11-12: Wait and reconnect
# (Wait for device to reboot - 3-5 minutes)
ssh admin@<device_ip>
sonic# show uptime

# Step 13: Verify map persistence
sonic# show qos map pfc-priority-pg

# Step 14: Verify interface binding
sonic# show qos interface Ethernet4

# Step 15: Verify PFC priorities
sonic# show pfc priority Ethernet4

# Step 16: Verify running-config
sonic# show running-config | grep -A 20 "qos map pfc-priority-pg pfcmap"

# Step 17: Verify PFC counters
sonic# show pfc counters interface Ethernet4

# Step 18: Test modification
sonic# configure terminal
sonic(config)# qos map pfc-priority-pg pfcmap
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 0 pg 1
sonic(config-pfc-priority-pg-map-pfcmap)# exit
sonic(config)# end
sonic# show qos map pfc-priority-pg

# Step 19: Verify startup-config
sonic# show startup-config | grep -A 20 "qos map pfc-priority-pg pfcmap"
```

---

## Appendix B: Expected vs Actual Results

| Step | Configuration Item | Expected After Reboot | Actual Result (SoCCI-110) |
|------|-------------------|----------------------|---------------------------|
| Map Existence | PFC-Priority-PG map "pfcmap" | Present | ❌ Missing |
| Priority Mappings | 0→0, 1-2→2, 3-4→4, 5-7→5 | Intact | ❌ Lost |
| Interface Binding | Ethernet4 → pfcmap | Maintained | ❌ Not restored |
| PFC Priorities | 3, 4 enabled on Ethernet4 | Enabled | ❌ Likely lost |
| Running Config | Full QoS config | Present | ❌ Partial/Missing |
| Startup Config | Saved config | Present | ✅ Present (but not loaded) |

---

## Appendix C: CONFIG_DB Schema Reference

### Expected CONFIG_DB Entries

**MAP_PFC_PRIORITY_TO_PRIORITY_GROUP Table**:
```json
{
  "MAP_PFC_PRIORITY_TO_PRIORITY_GROUP": {
    "pfcmap": {
      "0": "0",
      "1": "2",
      "2": "2",
      "3": "4",
      "4": "4",
      "5": "5",
      "6": "5",
      "7": "5"
    }
  }
}
```

**PORT_QOS_MAP Table**:
```json
{
  "PORT_QOS_MAP": {
    "Ethernet4": {
      "pfc_to_pg_map": "pfcmap"
    }
  }
}
```

---

## Appendix D: Testing Matrix

| Configuration Variant | Reboot Type | Expected Result | Test Priority |
|----------------------|-------------|-----------------|---------------|
| Single map, single interface | Normal reload | Config persists | High |
| Multiple maps, multiple interfaces | Normal reload | Config persists | High |
| Maximum name length (32 chars) | Normal reload | Config persists | Medium |
| All priorities mapped | Normal reload | Config persists | High |
| After config modification | Normal reload | Config persists | Medium |
| Cold boot | Power cycle | Config persists | High |
| Fast reboot | Fast-reboot | Config persists | Medium |
| Warm reboot | Warm-reboot | Config persists | Low |

---
