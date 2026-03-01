# QoS Test Case 4.25.15 - Delete Active PFC Map

## Test Overview

**Test ID:** 4.25.15
**Feature:** QoS (Quality of Service)
**Test Case:** Verify deletion behavior of active PFC_PRIORITY maps
**Test Script:** `test_qos_delete_active_pfc_map.py`
**Configuration:** `vars/qos/vars_qos_delete_active_pfc_map.yaml`

This automated test validates the system behavior when attempting to delete a PFC-Priority-PG map that is actively applied to an interface with priority-flow-control enabled.

## Test Objective

Verify whether the system properly:
1. **Blocks deletion** of in-use QoS maps with appropriate error messages, OR
2. **Handles deletion gracefully** by automatically removing interface bindings, OR
3. **Disables PFC** on affected interfaces before allowing map deletion

The test specifically checks for **inconsistent states** where:
- The global PFC map definition is deleted
- Interface configuration still references the deleted map (dangling reference)

## Test Topology

```
┌─────────────────┐
│   DUT (D1)      │
│  ┌──────────┐   │
│  │Ethernet8 │   │  ← PFC map applied to this interface
│  └──────────┘   │
└─────────────────┘

Topology Requirements:
- Single DUT
- Interface: Ethernet8 (configurable via YAML)
- No external connections required
```

## Test Procedure

### Step 1: Configure PFC-Priority-PG Map
Creates a PFC map with priority-to-PG mappings:
```
PFC Priority → Priority Group
0,1,2,5-7    → PG 0
3            → PG 3
4            → PG 4
```

### Step 2: Apply Map to Interface
Associates the PFC map with interface Ethernet8:
```bash
interface Ethernet8
  qos-map pfc-priority-pg pfc_pg_map
```

### Step 3: Enable Priority-Flow-Control
Enables PFC on specific priorities (3 and 4):
```bash
interface Ethernet8
  priority-flow-control priority 3,4
```

### Step 4: Verify Configuration
Verifies:
- PFC map exists in global configuration
- Interface correctly references the map
- PFC priorities are enabled

### Step 5: Attempt Deletion (Critical Step)
Attempts to delete the active PFC map:
```bash
no qos map pfc-priority-pg pfc_pg_map
```

**Expected Behaviors:**
- **Option A:** Command is rejected with error (map is in use)
- **Option B:** Command succeeds and interface binding is removed
- **Option C:** Command succeeds and PFC is disabled automatically

**Undesired Behavior:**
- Command succeeds but creates inconsistent state (dangling reference)

### Step 6: Verify System Consistency
Checks for consistency issues:
- Does global PFC map still exist?
- Does interface still reference the map?
- Is the system in a consistent state?

**Consistency Analysis:**
| Map Exists | Interface References | State | Assessment |
|-----------|---------------------|-------|------------|
| Yes | Yes | Consistent | Deletion was blocked ✓ |
| No | No | Consistent | Graceful deletion ✓ |
| No | Yes | **INCONSISTENT** | Dangling reference ✗ |
| Yes | No | Unexpected | Interface binding removed only |

### Step 7: Test Recovery
If map was deleted, attempts to reconfigure it to verify:
- System allows recreation with same name
- Interface binding becomes functional again
- No permanent damage to configuration

### Step 8: Final Verification
Displays final configuration state and validates recovery

## Test Configuration (YAML)

**File:** `vars/qos/vars_qos_delete_active_pfc_map.yaml`

```yaml
# Minimum topology
min_topology:
  - "D1"  # Single DUT required

# PFC Map Configuration
pfc_map_name: "pfc_pg_map"

# Priority-to-PG mappings
pfc_mappings:
  "0,1,2,5-7": 0  # Multiple priorities to PG 0
  "3": 3          # Priority 3 to PG 3
  "4": 4          # Priority 4 to PG 4

# Test interface
test_interface: "Ethernet8"

# PFC priorities to enable
pfc_priorities:
  - 3
  - 4

# Expected behavior flags
expect_deletion_blocked: false  # Set true if deletion should be blocked
verify_running_config: true     # Verify running-config after deletion
```

## Running the Test

### Basic Execution

```bash
./bin/spytest --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/qos/test_qos_delete_active_pfc_map.py \
  --logs-path ./logs/qos_delete_pfc_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### On Hardware Switch

```bash
./bin/spytest --testbed ./testbeds/testbed_hw_1node.yaml \
  tests/qos/test_qos_delete_active_pfc_map.py \
  --logs-path ./logs/qos_delete_pfc_hw_$(date +%F_%H%M%S) \
  --log-level debug \
  --ifname-type native
```

### With Custom Interface

Edit `vars/qos/vars_qos_delete_active_pfc_map.yaml`:
```yaml
test_interface: "Ethernet16"  # Use different interface
```

## Expected Results

### Test Case IDs

| Test Case ID | Description | Pass Criteria |
|-------------|-------------|---------------|
| TC-QOS-4.25.15-001 | PFC map creation | Map created successfully |
| TC-QOS-4.25.15-002 | Map applied to interface | Map applied successfully |
| TC-QOS-4.25.15-003 | PFC priorities enabled | Priorities enabled successfully |
| TC-QOS-4.25.15-004 | Delete active map | Behavior matches expected (blocked or graceful) |
| TC-QOS-4.25.15-005 | Verify consistency | No inconsistent state created |
| TC-QOS-4.25.15-006 | Recovery test | System recovers after reconfiguration |

### Pass Criteria

**Overall Test PASSES if:**
1. PFC map configuration works correctly
2. Deletion behavior is consistent (either blocked OR gracefully handled)
3. No dangling references are created
4. System can recover through reconfiguration

**Overall Test FAILS if:**
1. Inconsistent state is created (map deleted, interface still references it)
2. System becomes unstable after deletion attempt
3. Recovery is not possible

## Known Issues / Observations

Based on manual testing (see `tests/qos/qos_4.25.15.md`):

### Observed Behavior
- Deletion command is **accepted without error**
- Global map definition is **removed**
- Interface reference **persists** (creates inconsistent state)
- No warning or error message is shown
- System remains stable despite inconsistency
- Recovery is possible by recreating the map

### Assessment
This behavior requires clarification from the development team:
- Is this "soft deletion" intentional design?
- Should deletion be blocked when map is in use?
- Should interface bindings be automatically removed?

## Test Markers

```python
@pytest.mark.qos           # QoS feature tests
@pytest.mark.pfc           # PFC-specific tests
@pytest.mark.community_pass # Community regression suite
```

Run by marker:
```bash
./bin/spytest --testbed <testbed> -m pfc
```

## Pre-requisites

### System Requirements
- SONiC device with QoS support
- PFC (Priority Flow Control) support
- Klish CLI mode enabled

### Feature Support
- `qos map pfc-priority-pg` command available
- `priority-flow-control priority` command available
- `show qos map pfc-priority-pg` command available
- `show qos interface` command available

### Topology
- Minimum: 1 DUT (D1)
- Interface: Ethernet8 or as configured in YAML
- No external connectivity required

## Output Files

After test execution:
- **Module log:** `module_test_qos_delete_active_pfc_map.log`
- **Device log:** `dlog-D1-<devicename>.log`
- **Results:** `results.html`
- **Summary:** `summary.txt`

## Debugging

### Enable Debug Logging
```bash
./bin/spytest ... --log-level debug
```

### Check Device Commands
Review `dlog-D1-*.log` for actual CLI commands executed

### Manual Verification
If test fails, manually verify:
```bash
# Check PFC maps
show qos map pfc-priority-pg

# Check interface configuration
show qos interface Ethernet8

# Check running configuration
show running-configuration qos
show running-configuration interface Ethernet8

# Check PFC priorities
show pfc priority
```

## Extending the Test

### Test Additional Scenarios

Edit YAML to enable additional tests:

```yaml
# Test if PFC functionality continues during inconsistent state
test_traffic_impact: true

# Test if inconsistent state persists after reboot
test_reboot_persistence: true
```

### Test Multiple Interfaces

Modify test to apply map to multiple interfaces and verify:
- Deletion blocked if ANY interface uses the map
- All interface bindings removed if graceful deletion

### Test Different Map Types

Extend test to other QoS maps:
- DSCP-to-TC maps
- TC-to-Queue maps
- Scheduler maps

## Related Tests

- `test_qos_pfc_priority_pg_map.py` - Basic PFC configuration
- Other QoS map deletion tests (if available)

## References

- Manual test results: `tests/qos/qos_4.25.15.md`
- PFC test variables: `vars/qos/vars_qos_pfc_priority_pg_map.yaml`
- Framework guide: `Doc/intro.md`

## Support

For issues or questions:
1. Check test logs in `--logs-path` directory
2. Review device logs for CLI errors
3. Verify feature support on device
4. Check SONiC version compatibility

## Version History

- **v1.0** - Initial automated test based on manual test case 4.25.15
- Test generation date: 2026-02-26
- Based on manual test findings from 2026-02-25
