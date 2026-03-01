# QoS PFC Test Suite - README

## Test Files

### Test Case 4.25.16: PFC Priority-to-PG Mapping

**Test Documentation:** `qos_4.25.16.md`
**Test Script:** `test_qos_pfc_priority_pg_map.py`
**Test Variables:** `../../vars/qos/vars_qos_pfc_priority_pg_map.yaml`

## Prerequisites

1. **Topology:** Two-node setup (D1 ↔ D2) with at least 1 link between them
2. **Requirements:**
   - SONiC with QoS/PFC support
   - VLAN support
   - Interfaces in working condition

## Configuration

### 1. Update Test Variables

Edit `vars/qos/vars_qos_pfc_priority_pg_map.yaml` and update the interface names according to your testbed:

```yaml
# Interface Configuration for DUT1
d1_interfaces:
  - "Ethernet0"   # Update to match your testbed
  - "Ethernet4"   # Optional second interface

# Interface Configuration for DUT2
d2_interfaces:
  - "Ethernet0"   # Update to match your testbed
```

### 2. Update Testbed File

Ensure your testbed file (e.g., `testbeds/testbed_vs_2node.yaml`) has:
- Two devices (D1 and D2) configured
- Proper connectivity between the devices
- SSH access configured

## Running the Tests

### Basic Test Execution

Run the complete test suite:

```bash
./bin/spytest --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/qos/test_qos_pfc_priority_pg_map.py \
  --logs-path ./logs/qos_pfc_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Run Specific Test Function

Run only the configuration test:

```bash
./bin/spytest --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/qos/test_qos_pfc_priority_pg_map.py::test_pfc_priority_pg_map_config \
  --logs-path ./logs/qos_pfc_config_$(date +%F_%H%M%S) \
  --log-level debug
```

Run only the counter verification test:

```bash
./bin/spytest --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/qos/test_qos_pfc_priority_pg_map.py::test_pfc_counters_verification \
  --logs-path ./logs/qos_pfc_counters_$(date +%F_%H%M%S) \
  --log-level debug
```

### Run with PyTest Markers

Run all QoS tests:

```bash
./bin/spytest --testbed ./testbeds/testbed_vs_2node.yaml \
  -m qos \
  --logs-path ./logs/qos_tests_$(date +%F_%H%M%S)
```

Run all PFC tests:

```bash
./bin/spytest --testbed ./testbeds/testbed_vs_2node.yaml \
  -m pfc \
  --logs-path ./logs/pfc_tests_$(date +%F_%H%M%S)
```

## Test Markers

The test uses the following PyTest markers:

- `@pytest.mark.qos` - QoS feature tests
- `@pytest.mark.pfc` - PFC-specific tests
- `@pytest.mark.community` - Community-compatible tests
- `@pytest.mark.pfc_counters` - PFC counter verification tests

## Test Functions

### 1. `test_pfc_priority_pg_map_config()`

**Test ID:** TC-QOS-PFC-001, TC-QOS-PFC-002, TC-QOS-PFC-003

**Description:** Configures and verifies PFC Priority-to-PG mapping

**Test Steps:**
1. Configure PFC-Priority-PG map on both DUTs
2. Apply map to interfaces
3. Enable PFC priorities on interfaces
4. Add interfaces to VLAN (as trunk members)
5. Verify PFC map configuration
6. Verify PFC priorities enabled on interfaces
7. Verify VLAN membership

**Expected Result:**
- PFC map created successfully with correct priority-to-PG mappings
- Map applied to all configured interfaces
- PFC priorities enabled on interfaces
- VLAN membership configured correctly

### 2. `test_pfc_counters_verification()`

**Test ID:** TC-QOS-PFC-004

**Description:** Verifies PFC counter commands work correctly

**Test Steps:**
1. Display PFC counters on both DUTs
2. Display PFC watchdog status
3. Verify commands execute without errors

**Expected Result:**
- PFC counter commands execute successfully
- Counters are displayed for configured interfaces

**Note:** This test does not generate traffic to increment counters. It only verifies that counter commands work. For full counter verification with traffic, additional traffic generator setup is required.

## Viewing Results

After test execution, results are available in the logs directory:

1. **Summary:** `<logs-path>/summary.txt`
2. **HTML Report:** `<logs-path>/results.html`
3. **Module Log:** `<logs-path>/module_test_qos_pfc_priority_pg_map.log`
4. **Device Logs:** `<logs-path>/dlog-D1-<hostname>.log`, `<logs-path>/dlog-D2-<hostname>.log`

### Quick Summary

```bash
cat logs/qos_pfc_*/summary.txt
```

### View HTML Report

```bash
firefox logs/qos_pfc_*/results.html &
```

## Test Configuration Details

### PFC Priority-to-PG Mappings

The test creates the following default mappings:

| PFC Priority | Priority Group |
|--------------|----------------|
| 0, 1, 2      | PG 0           |
| 3            | PG 3           |
| 4            | PG 4           |
| 5, 6, 7      | PG 0           |

### PFC Enabled Priorities

By default, the test enables PFC on:
- **Priority 3**
- **Priority 4**

### VLAN Configuration

- **VLAN ID:** 100 (configurable in YAML)
- **Interface Mode:** Trunk (tagged)
- **Requirement:** Interfaces must be in L2 mode (no IP address)

### PFC Watchdog

- **Status:** Enabled on first DUT1 interface
- **Detect Time:** 100 ms (configurable in YAML)

## Troubleshooting

### Common Issues

1. **Interface not found:**
   - Update `d1_interfaces` and `d2_interfaces` in YAML config
   - Verify interfaces exist: `show interface status`

2. **Cannot add VLAN member:**
   - Error: "Interface is in L3 mode with IP address configured"
   - Solution: Test automatically removes IP addresses, but verify manually if needed
   - Manual fix: `no ip address` under interface configuration

3. **PFC map not found:**
   - Verify QoS/PFC support on your SONiC version
   - Check if PFC feature is enabled

4. **Test skipped due to missing YAML:**
   - Ensure `vars/qos/vars_qos_pfc_priority_pg_map.yaml` exists
   - Check file path is correct

### Debug Commands

Run these commands manually on DUTs to verify configuration:

```bash
# Verify PFC map
show qos map pfc-priority-pg

# Verify PFC priorities on interfaces
show pfc priority

# Verify VLAN membership
show vlan

# Verify PFC counters
show pfc counters

# Verify PFC watchdog
show priority-flow-control watchdog

# Verify interface QoS configuration
show qos interface Ethernet0
```

## Extending the Tests

### Add Traffic Generation

To add actual traffic-based PFC testing:

1. Update YAML to include TGen ports
2. Add TGen stream configuration in module_hooks
3. Generate congestion traffic to trigger PFC frames
4. Verify PFC counters increment

Example traffic addition:

```python
# In module_hooks, after initialize_data():
data.tg1, data.tg_ph_1 = tgapi.get_handle_byname("T1D1P1")
data.tg2, data.tg_ph_2 = tgapi.get_handle_byname("T1D2P1")

# Create congestion traffic
stream = data.tg1.tg_traffic_config(
    port_handle=data.tg_ph_1,
    mode='create',
    rate_percent=100,  # High rate to cause congestion
    l2_encap='ethernet_ii_vlan',
    vlan_id=data.vlan_id,
    vlan_user_priority=3  # Use PFC priority 3
)
```

### Add More Test Cases

Additional test scenarios to consider:

1. **PFC Map Deletion:** Test deletion of active PFC maps (see qos_4.25.15.md)
2. **Multiple Maps:** Test multiple PFC maps on different interfaces
3. **Map Modification:** Test updating existing PFC maps
4. **Negative Tests:** Test invalid priority values, non-existent interfaces
5. **Persistence:** Test configuration after reboot
6. **Scale Tests:** Test with many interfaces and multiple maps

## References

- **Test Documentation:** `qos_4.25.16.md` - Full manual test results
- **Test Documentation:** `qos_4.25.15.md` - PFC map deletion behavior
- **SPyTest Framework:** `../../Doc/intro.md`
- **Project Instructions:** `../../CLAUDE.md`

## Support

For issues or questions:
1. Check logs in `<logs-path>/` directory
2. Review test documentation in `qos_4.25.16.md`
3. Verify testbed configuration
4. Check SONiC version compatibility

---

**Last Updated:** 2026-02-25
**Test Version:** 1.0
**Compatible SONiC Versions:** Enterprise SONiC (verify QoS/PFC support)
