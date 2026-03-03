# Test Plan: PFC-Priority to Priority-Group Map Creation via CLI

## Test Metadata

| Field | Value |
|-------|-------|
| **Test ID** | 4.25.13 |
| **Feature** | QoS (Quality of Service) |
| **Sub-Feature** | PFC (Priority Flow Control) - Priority-Group Mapping |
| **Test Case** | Verify PFC-Priority to Priority-Group map creation via CLI |
| **Test Type** | Functional |
| **Test Level** | Component |
| **Author** | QoS Test Suite |
| **Date Created** | 2026-03-03 |

---

## Test Objective

Validate that the CLI allows creation of PFC-Priority-PG map and configuration of valid mappings with proper syntax support including:
- Individual priority mappings
- Range-based priority mappings
- Comma-separated priority lists
- Combined range and list formats

---

## Prerequisites

### Topology Requirements
- **Minimum Topology**: Single DUT (D1)
- **Supported Platforms**: Hardware and Virtual SONiC devices
- **Required Interfaces**: At least one Ethernet interface (e.g., Ethernet4)

### Software Requirements
- SONiC OS with QoS and PFC support
- CLI Mode: Klish (IS-CLI)

### Initial Configuration
- Device accessible via SSH
- No pre-existing PFC-Priority-PG maps with conflicting names

---

## Test Procedure

### Step 1: Create PFC-Priority-PG Map with Valid Name

**Description**: Enter configuration mode and create a new PFC-Priority-PG map named "pfcmap"

**Commands**:
```bash
sonic# configure terminal
sonic(config)# qos map pfc-priority-pg pfcmap
sonic(config-pfc-priority-pg-map-pfcmap)#
```

**Expected Result**:
- CLI accepts the map creation command
- Configuration mode changes to `config-pfc-priority-pg-map-pfcmap`
- No error messages displayed

---

### Step 2: Configure Individual Priority Mapping

**Description**: Configure PFC priority 0 to Priority Group 0

**Commands**:
```bash
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 0 pg 0
```

**Expected Result**:
- Command executes successfully without errors
- Mapping configured: PFC Priority 0 → PG 0

---

### Step 3: Verify CLI Help for Priority Format

**Description**: Test CLI help to understand supported priority formats

**Commands**:
```bash
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority
```

**Expected Output**:
```
    (-) or (,) separated individual PFC Priority and ranges of PFC Priority's;
    for example, 0,2-7
```

**Expected Result**:
- CLI displays helpful syntax information
- Shows support for ranges (-) and comma-separated lists (,)

---

### Step 4: Configure Range-Based Priority Mapping

**Description**: Configure PFC priorities 1-2 to Priority Group 2 using range syntax

**Commands**:
```bash
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 1-2 pg 2
```

**Expected Result**:
- Command executes successfully
- Mapping configured: PFC Priority 1 → PG 2, PFC Priority 2 → PG 2

---

### Step 5: Configure Comma-Separated Priority Mapping

**Description**: Configure PFC priorities 3 and 4 to Priority Group 4 using comma syntax

**Commands**:
```bash
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 3,4 pg 4
```

**Expected Result**:
- Command executes successfully
- Mapping configured: PFC Priority 3 → PG 4, PFC Priority 4 → PG 4

---

### Step 6: Configure Combined Format Priority Mapping

**Description**: Configure PFC priorities 5, 6-7 to Priority Group 5 using combined syntax

**Commands**:
```bash
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 5,6-7 pg 5
sonic(config-pfc-priority-pg-map-pfcmap)# end
```

**Expected Result**:
- Command executes successfully
- Mapping configured: PFC Priority 5 → PG 5, PFC Priority 6 → PG 5, PFC Priority 7 → PG 5
- Configuration mode exits to privileged EXEC mode

---

### Step 7: Apply Map to Interface (Negative Test)

**Description**: Attempt to apply non-existent map to interface (negative validation)

**Commands**:
```bash
sonic# configure terminal
sonic(config)# interface Ethernet 4
sonic(conf-if-Ethernet4)# qos-map pfc-priority-pg test
```

**Expected Result**:
- Command fails with error message
- Error displayed: `%Error: operation failed`
- System prevents application of non-existent map

---

### Step 8: Apply Map to Interface (Positive Test)

**Description**: Apply the created PFC-Priority-PG map to interface Ethernet4

**Commands**:
```bash
sonic(conf-if-Ethernet4)# qos-map pfc-priority-pg pfcmap
```

**Expected Result**:
- Command executes successfully without errors
- Map "pfcmap" applied to interface Ethernet4

---

### Step 9: Enable Priority Flow Control on Interface

**Description**: Enable PFC on specific priorities that have mappings configured

**Commands**:
```bash
sonic(conf-if-Ethernet4)# priority-flow-control priority 3
sonic(conf-if-Ethernet4)# priority-flow-control priority 4
sonic(conf-if-Ethernet4)# exit
```

**Expected Result**:
- Commands execute successfully
- PFC enabled on priorities 3 and 4
- Configuration persisted

---

### Step 10: Verify Global PFC-Priority-PG Map Configuration

**Description**: Display all configured PFC-Priority-PG maps

**Commands**:
```bash
sonic# show qos map pf
```

**Expected Output** (Tab completion):
```
pfc-priority-pg    pfc-priority-queue
```

**Commands** (Full command):
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
- Tab completion shows available map types
- Output displays all 8 PFC priority mappings (0-7)
- Each priority correctly mapped to configured Priority Group:
  - Priority 0 → PG 0 (individual)
  - Priorities 1-2 → PG 2 (range)
  - Priorities 3-4 → PG 4 (comma-separated)
  - Priorities 5-7 → PG 5 (combined format)

---

### Step 11: Verify Interface QoS Configuration

**Description**: Display QoS configuration applied to interface Ethernet4

**Commands**:
```bash
sonic# show qos interface e
```

**Expected Output** (Tab completion):
```
Ethernet Ethernet
```

**Commands** (Full command):
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
- Tab completion works for interface names
- Output confirms map "pfcmap" is applied to interface
- PFC Watchdog status displayed (default: off)
- All configuration parameters visible

---

## Test Validation Criteria

### Success Criteria
✅ **Map Creation**:
- PFC-Priority-PG map "pfcmap" created successfully
- Configuration mode correctly reflects map context

✅ **Priority Mapping Formats**:
- Individual priority syntax works: `pfc-priority 0 pg 0`
- Range syntax works: `pfc-priority 1-2 pg 2`
- Comma-separated syntax works: `pfc-priority 3,4 pg 4`
- Combined syntax works: `pfc-priority 5,6-7 pg 5`

✅ **Error Handling**:
- Non-existent map application fails with appropriate error
- System prevents invalid configurations

✅ **Interface Application**:
- Map successfully applies to interface
- PFC enables on configured priorities
- Configuration persists and displays correctly

✅ **Verification Commands**:
- `show qos map pfc-priority-pg` displays complete map
- `show qos interface` shows applied map on interface
- All 8 priorities (0-7) have valid mappings

### Failure Criteria
❌ Any CLI command returns unexpected error
❌ Priority mappings not saved or displayed incorrectly
❌ Map cannot be applied to interface
❌ Show commands don't reflect configuration
❌ Invalid map names are accepted without error

---

## Actual Test Results

### Test Execution Summary
- **Status**: ✅ **PASS**
- **Date Executed**: 2026-03-03
- **Execution Environment**: SONiC Virtual Platform

### Detailed Results

**Step 1-6: Map Creation and Configuration**
- ✅ All priority mapping formats accepted successfully
- ✅ Individual, range, comma-separated, and combined formats work correctly
- ✅ CLI help displays proper syntax guidance

**Step 7-8: Interface Application**
- ✅ Non-existent map correctly rejected with error
- ✅ Existing map successfully applied to interface
- ✅ Error handling works as expected

**Step 9: PFC Enablement**
- ✅ Priority flow control enabled on priorities 3 and 4
- ✅ Configuration accepted without errors

**Step 10: Global Map Verification**
- ✅ `show qos map pfc-priority-pg` displays complete map configuration
- ✅ All 8 priorities (0-7) correctly mapped to configured PGs:
  - PFC Priority 0 → PG 0
  - PFC Priority 1 → PG 2
  - PFC Priority 2 → PG 2
  - PFC Priority 3 → PG 4
  - PFC Priority 4 → PG 4
  - PFC Priority 5 → PG 5
  - PFC Priority 6 → PG 5
  - PFC Priority 7 → PG 5

**Step 11: Interface Verification**
- ✅ `show qos interface Ethernet4` confirms map application
- ✅ Interface shows "pfc-priority-pg-map: pfcmap"
- ✅ PFC Watchdog status displayed correctly

---

## Notes and Observations

### CLI Behavior
1. **Tab Completion**: CLI provides helpful tab completion for:
   - QoS map types (`pfc-priority-pg`, `pfc-priority-queue`)
   - Interface names (Ethernet)

2. **Syntax Flexibility**: CLI accepts multiple priority specification formats:
   - Single value: `0`
   - Range: `1-2`
   - List: `3,4`
   - Combined: `5,6-7`

3. **Context-Sensitive Prompts**: Configuration mode prompt changes to reflect current context:
   - `sonic(config-pfc-priority-pg-map-pfcmap)#`

### Error Handling
1. **Non-Existent Map**: System properly rejects attempt to apply non-existent map with error:
   - `%Error: operation failed`

2. **Validation**: CLI validates map existence before allowing interface application

### Default Values
1. **PFC Watchdog**: Defaults to "off" state
2. **Detection Time**: Defaults to 0ms
3. **Restoration Time**: Defaults to infinite (0ms)

---

## Related Test Cases

- **4.25.12**: PFC-Priority-PG map boundary value testing
- **4.25.14**: PFC-Priority-PG map modification testing
- **4.25.15**: Delete Active PFC Map testing
- **4.25.16**: PFC-Priority-PG map negative testing (invalid values)

---

## Test Automation

### Test Script Location
```
tests/qos/test_qos_pfc_priority_pg_map.py
```

### How to Execute
```bash
./bin/spytest --testbed ./testbeds/testbed_vs_3rr.yaml \
    tests/qos/test_qos_pfc_priority_pg_map.py::test_pfc_priority_pg_map_config \
    --logs-path ./logs/qos_test_$(date +%F_%H%M%S) \
    --log-level debug --skip-init-config --ifname-type native
```

---

## References

### SONiC Documentation
- QoS Configuration Guide
- PFC (Priority Flow Control) Architecture
- IS-CLI Command Reference

### Standards
- IEEE 802.1Qbb - Priority-based Flow Control
- Data Center Bridging (DCB) Standards

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-03 | QoS Test Team | Initial test plan creation |

---

## Appendix

### Complete CLI Command Sequence

```bash
# Map Creation and Configuration
sonic# configure terminal
sonic(config)# qos map pfc-priority-pg pfcmap
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 0 pg 0
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 1-2 pg 2
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 3,4 pg 4
sonic(config-pfc-priority-pg-map-pfcmap)# pfc-priority 5,6-7 pg 5
sonic(config-pfc-priority-pg-map-pfcmap)# end

# Interface Application
sonic# configure terminal
sonic(config)# interface Ethernet 4
sonic(conf-if-Ethernet4)# qos-map pfc-priority-pg pfcmap
sonic(conf-if-Ethernet4)# priority-flow-control priority 3
sonic(conf-if-Ethernet4)# priority-flow-control priority 4
sonic(conf-if-Ethernet4)# exit

# Verification
sonic# show qos map pfc-priority-pg
sonic# show qos interface Ethernet4
```

### Configuration Cleanup (Optional)

```bash
# Remove PFC from interface
sonic# configure terminal
sonic(config)# interface Ethernet 4
sonic(conf-if-Ethernet4)# no priority-flow-control priority 3
sonic(conf-if-Ethernet4)# no priority-flow-control priority 4
sonic(conf-if-Ethernet4)# no qos-map pfc-priority-pg
sonic(conf-if-Ethernet4)# exit

# Remove map
sonic(config)# no qos map pfc-priority-pg pfcmap
sonic(config)# end
```
