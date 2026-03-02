# QoS Test Case 4.25.15 - Automated Test Generation Summary

## Overview

Automated test script generated for **Test Case 4.25.15: Delete Active PFC Map** based on the manual test results documented in `tests/qos/qos_4.25.15.md`.

**Generation Date:** 2026-02-26
**Test Purpose:** Validate system behavior when deleting an active PFC-Priority-PG map

## Files Created

### 1. Test Script
**Location:** `tests/qos/test_qos_delete_active_pfc_map.py`
**Size:** 25.9 KB
**Lines:** 666 lines

**Features:**
- Complete test implementation with 8 test steps
- Automated verification of deletion behavior
- Consistency checking for dangling references
- Recovery testing through reconfiguration
- Comprehensive logging and error handling
- PyTest integration with markers

**Functions Implemented:**
- `initialize_data()` - Load YAML configuration
- `configure_pfc_map()` - Create PFC-Priority-PG maps
- `delete_pfc_map()` - Delete PFC maps with error detection
- `apply_pfc_map_to_interface()` - Apply maps to interfaces
- `enable_pfc_priorities()` - Enable PFC on priorities
- `verify_pfc_map_exists()` - Verify map existence
- `verify_interface_pfc_map()` - Verify interface references
- `cleanup_pfc_configuration()` - Cleanup after test
- `test_qos_delete_active_pfc_map()` - Main test function

### 2. Configuration File
**Location:** `vars/qos/vars_qos_delete_active_pfc_map.yaml`
**Size:** 900 bytes

**Configuration Parameters:**
```yaml
min_topology: ["D1"]
pfc_map_name: "pfc_pg_map"
test_interface: "Ethernet8"
pfc_priorities: [3, 4]
pfc_mappings:
  "0,1,2,5-7": 0
  "3": 3
  "4": 4
expect_deletion_blocked: false
verify_running_config: true
cli_type: "klish"
```

### 3. Documentation
**Location:** `tests/qos/README_QoS_4.25.15.md`
**Size:** 10.5 KB
**Lines:** 332 lines

**Documentation Sections:**
- Test Overview
- Test Objective
- Test Topology
- Detailed Test Procedure (8 steps)
- Configuration Guide
- Running the Test
- Expected Results
- Known Issues/Observations
- Debugging Guide
- Extension Guide

## Test Execution

### Quick Start

```bash
cd /home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest

# On virtual switch
./bin/spytest --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/qos/test_qos_delete_active_pfc_map.py \
  --logs-path ./logs/qos_delete_pfc_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Test Flow

```
┌─────────────────────────────────────────┐
│ Step 1: Configure PFC-Priority-PG Map  │
│   - Create map: pfc_pg_map             │
│   - Map priorities 0,1,2,5-7 → PG 0    │
│   - Map priority 3 → PG 3              │
│   - Map priority 4 → PG 4              │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 2: Apply Map to Interface         │
│   - Apply pfc_pg_map to Ethernet8      │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 3: Enable Priority-Flow-Control   │
│   - Enable PFC priority 3              │
│   - Enable PFC priority 4              │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 4: Verify Configuration           │
│   - Verify map exists globally         │
│   - Verify interface references map    │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 5: Attempt Deletion (CRITICAL)    │
│   - Execute: no qos map pfc-priority-pg│
│   - Capture any error messages         │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 6: Verify System Consistency      │
│   - Check if map still exists          │
│   - Check if interface still refs map  │
│   - Detect dangling references         │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 7: Test Recovery                  │
│   - Reconfigure map with same name     │
│   - Verify recovery successful         │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Step 8: Final Verification             │
│   - Display final configuration        │
│   - Check running-config               │
└─────────────────────────────────────────┘
```

## Test Case IDs

| TC ID | Test Step | Pass Criteria |
|-------|-----------|---------------|
| TC-QOS-4.25.15-001 | PFC map creation | Map created successfully |
| TC-QOS-4.25.15-002 | Map applied to interface | Applied without error |
| TC-QOS-4.25.15-003 | PFC priorities enabled | Enabled successfully |
| TC-QOS-4.25.15-004 | Delete active map | Behavior matches expectation |
| TC-QOS-4.25.15-005 | Verify consistency | No dangling references |
| TC-QOS-4.25.15-006 | Recovery test | System recovers successfully |

## Key Test Validations

### 1. Deletion Behavior Validation
The test validates one of these expected behaviors:

**Option A: Deletion Blocked (Preferred)**
```
Command: no qos map pfc-priority-pg pfc_pg_map
Error: Cannot delete map - in use by interface Ethernet8
Result: Map exists ✓, Interface refs map ✓ → CONSISTENT STATE
```

**Option B: Graceful Deletion**
```
Command: no qos map pfc-priority-pg pfc_pg_map
Action: System automatically removes interface binding
Result: Map deleted ✓, Interface binding removed ✓ → CONSISTENT STATE
```

**Option C: Inconsistent State (Bug)**
```
Command: no qos map pfc-priority-pg pfc_pg_map
Action: Map deleted but interface binding persists
Result: Map deleted ✓, Interface still refs map ✗ → INCONSISTENT STATE ✗
```

### 2. Consistency Checking

The test performs comprehensive consistency verification:

```python
# Check global map existence
map_exists = verify_pfc_map_exists(dut, "pfc_pg_map")

# Check interface reference
interface_refs = verify_interface_pfc_map(dut, "Ethernet8", "pfc_pg_map")

# Consistency matrix
if not map_exists and interface_refs:
    # INCONSISTENT STATE - Dangling reference detected
    FAIL: "Interface references non-existent map"
elif map_exists and interface_refs:
    # CONSISTENT - Deletion was blocked
    PASS: "Deletion blocked, state consistent"
elif not map_exists and not interface_refs:
    # CONSISTENT - Graceful deletion
    PASS: "Graceful deletion, state consistent"
```

### 3. Recovery Testing

Validates system can recover from any state:
- Recreate map with same name
- Verify interface binding becomes functional
- Ensure no permanent configuration damage

## Known Behavior (from Manual Testing)

Based on manual test results in `tests/qos/qos_4.25.15.md`:

**Current Behavior (Requires Clarification):**
1. ✓ Deletion command accepted without error
2. ✗ Global map definition removed
3. ✗ Interface reference persists (dangling reference)
4. ✗ No warning or error message
5. ✓ System remains stable
6. ✓ Recovery possible by recreating map

**Status:** PARTIAL PASS ⚠️
- Functionality works but creates inconsistent state
- Requires product team clarification on intended behavior

## PyTest Markers

```python
@pytest.mark.qos           # QoS feature tests
@pytest.mark.pfc           # PFC-specific tests
@pytest.mark.community_pass # Community regression suite
```

Run tests by marker:
```bash
# Run all QoS tests
./bin/spytest --testbed <testbed> -m qos

# Run all PFC tests
./bin/spytest --testbed <testbed> -m pfc

# Run community pass suite
./bin/spytest --testbed <testbed> -m community_pass
```

## Integration with Existing Tests

This test complements the existing PFC test suite:

```
tests/qos/
├── test_qos_pfc_priority_pg_map.py      # Basic PFC configuration (4.25.16)
├── test_qos_delete_active_pfc_map.py    # Deletion behavior (4.25.15) ← NEW
├── qos_4.25.15.md                       # Manual test results
├── qos_4.25.16.md                       # Manual test results (if exists)
├── README_QoS_4.25.15.md                # Test documentation ← NEW
└── README_QoS_PFC.md                    # General PFC documentation
```

## Customization

### Change Test Interface
Edit `vars/qos/vars_qos_delete_active_pfc_map.yaml`:
```yaml
test_interface: "Ethernet16"  # Use different interface
```

### Change PFC Priorities
```yaml
pfc_priorities:
  - 0
  - 7
```

### Change Priority-to-PG Mappings
```yaml
pfc_mappings:
  "0,1": 0
  "2,3": 1
  "4,5": 2
  "6,7": 3
```

### Enable Additional Tests
```yaml
test_traffic_impact: true      # Test PFC during inconsistent state
test_reboot_persistence: true  # Test if state persists after reboot
```

## Syntax Validation

✓ Python syntax validated with `python3 -m py_compile`
✓ YAML syntax validated
✓ All imports verified against existing test structure
✓ Function signatures match SPyTest framework conventions

## Next Steps

### 1. Execute Test on Virtual Switch
```bash
./bin/spytest --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/qos/test_qos_delete_active_pfc_map.py \
  --logs-path ./logs/qos_delete_test_vs
```

### 2. Execute Test on Hardware
```bash
./bin/spytest --testbed ./testbeds/testbed_hw_1node.yaml \
  tests/qos/test_qos_delete_active_pfc_map.py \
  --logs-path ./logs/qos_delete_test_hw
```

### 3. Review Results
- Check `logs/qos_delete_test_*/summary.txt`
- Review `logs/qos_delete_test_*/results.html`
- Analyze device commands in `logs/qos_delete_test_*/dlog-D1-*.log`

### 4. Report Findings
Based on test results:
- If deletion is blocked: Document as expected behavior
- If graceful deletion: Document as expected behavior
- If inconsistent state: Create bug report with test logs

## Troubleshooting

### Test Fails to Load Configuration
```
Error: Configuration file not found
```
**Solution:** Verify YAML file exists at correct path:
```bash
ls -la vars/qos/vars_qos_delete_active_pfc_map.yaml
```

### Interface Not Available
```
Error: Interface Ethernet8 not found
```
**Solution:** Change interface in YAML to available interface

### QoS Commands Not Supported
```
Error: Unknown command "qos map"
```
**Solution:**
- Verify device supports QoS
- Check if klish mode is enabled
- Try different testbed with QoS support

## Related Files

- **Manual test:** `tests/qos/qos_4.25.15.md`
- **Related test:** `tests/qos/test_qos_pfc_priority_pg_map.py`
- **PFC vars:** `vars/qos/vars_qos_pfc_priority_pg_map.yaml`
- **Framework:** `spytest/framework.py`

## Version Information

- **Test Script Version:** 1.0
- **Generated:** 2026-02-26
- **Based On:** Manual test results from qos_4.25.15.md
- **Framework:** SPyTest (SONiC Python Test Framework)
- **Python:** 3.8+
- **Test Framework:** PyTest

## Contact

For questions or issues with this test:
1. Review test documentation in README_QoS_4.25.15.md
2. Check test logs for detailed error messages
3. Verify device/platform support for PFC features
4. Consult SPyTest framework documentation in `Doc/intro.md`
