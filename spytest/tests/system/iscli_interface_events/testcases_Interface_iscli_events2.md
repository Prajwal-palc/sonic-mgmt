# Interface Events Test Cases - MTU Configuration Changes

**Test Suite:** Interface Events - MTU Changes via CLI (klish)
**Author:** Test Engineering Team
**Date:** 2025-11-26
**Copyright:** © 2025, copyrights@SuperMicro

---

## Test Environment

### Topology
- **Type:** 2-node topology
- **Devices:** smic_sonic1 (DUT1), smic_sonic2 (DUT2)
- **Testbed File:** `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
- **Connections:**
  - Ethernet0 (DUT1) ↔ Ethernet0 (DUT2)
  - Ethernet4 (DUT1) ↔ Ethernet4 (DUT2)
  - Ethernet8 (DUT1) ↔ Ethernet8 (DUT2)
  - Ethernet12 (DUT1) ↔ Ethernet12 (DUT2)

### Prerequisites
- Access to sonic-cli (klish mode)
- Minimum 1 interface available for testing
- CLI type: klish
- Support: Hardware and Virtual devices

---

## Test Case Details

### TC_INTF_EVENTS_MTU_001: Validate CLI for MTU Configuration Changes

**Test Case ID:** TC_INTF_EVENTS_MTU_001
**Priority:** High
**Test Type:** Functional, Regression
**Feature:** Interface Configuration - MTU Changes

#### Objective
Validate that interface MTU (Maximum Transmission Unit) configuration changes are accurately reflected in the CLI output via the `show running-configuration interface Ethernet <>` command in klish mode.

#### Test Description
This test validates the complete MTU change cycle for an interface:
1. Baseline verification (default MTU: 9100)
2. Change MTU to 1600
3. Verify MTU change in running-config
4. Change MTU to 2000
5. Verify MTU change in running-config
6. Restore MTU to default 9100
7. Verify MTU restoration in running-config

#### Test Steps

| Step | Action | Command | Expected Result |
|------|--------|---------|-----------------|
| 1 | Setup: Bring all interfaces to admin UP state | `no shutdown` on all test interfaces | All interfaces admin UP |
| 2 | Get test interface from testbed | Parse testbed YAML | Test interface identified (e.g., Ethernet0) |
| 3 | Verify baseline MTU | `show running-configuration interface Ethernet <>` | MTU shown as 9100 (default) |
| 4 | Configure MTU to 1600 | `configure terminal` → `interface Ethernet <>` → `mtu 1600` → `end` | Configuration accepted |
| 5 | Verify MTU changed to 1600 | `show running-configuration interface Ethernet <>` | Output contains `mtu 1600` |
| 6 | Configure MTU to 2000 | `configure terminal` → `interface Ethernet <>` → `mtu 2000` → `end` | Configuration accepted |
| 7 | Verify MTU changed to 2000 | `show running-configuration interface Ethernet <>` | Output contains `mtu 2000` |
| 8 | Restore MTU to default 9100 | `configure terminal` → `interface Ethernet <>` → `mtu 9100` → `end` | Configuration accepted |
| 9 | Verify MTU restored to 9100 | `show running-configuration interface Ethernet <>` | Output contains `mtu 9100` |
| 10 | Final validation | `show running-configuration interface Ethernet <>` | MTU is at baseline value (9100) |

#### CLI Commands Used

**Configuration Commands:**
```
sonic-cli
configure terminal
interface Ethernet <X>
mtu <value>
end
```

**Verification Commands:**
```
show running-configuration interface Ethernet <X>
```

#### Expected Output Format

```
!
interface Ethernet0
 mtu 1600
 speed 40000
 ip address 10.0.0.0/31
```

The output will show the configured MTU value in the interface configuration section.

#### Pass/Fail Criteria

**Pass Criteria:**
- MTU configuration commands execute successfully without errors
- `show running-configuration interface Ethernet <>` displays the correct MTU value after each configuration change
- MTU value in running-config matches the configured value
- MTU can be successfully changed through the sequence: 9100 → 1600 → 2000 → 9100
- System remains stable after all MTU changes

**Fail Criteria:**
- MTU configuration command fails or produces an error
- `show running-configuration interface Ethernet <>` does not reflect the configured MTU value
- MTU value in running-config does not match the configured value
- Any unexpected errors during configuration or verification

#### Automation Details
- **Test Script:** `test_interface_2_iscli_events_mtu_change.py`
- **Test Class:** `TestInterfaceMTUChanges`
- **Test Method:** `test_interface_mtu_change_cycle()`
- **CLI Type:** klish
- **Framework:** SpyTest

#### Notes
- MTU values tested: 1600, 2000, 9100 (default)
- The test uses only ONE interface from the testbed
- MTU changes should be reflected immediately in running-config
- No interface flap required for MTU changes to take effect in configuration
- Uses `show running-configuration interface Ethernet <>` (NOT `show interface status`)

---

## Test Execution

### How to Run
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/system/iscli_interface_events/test_interface_2_iscli_events_mtu_change.py \
  --logs-path ./logs/test_interface_2_iscli_events_mtu_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Test Duration
- **Estimated Time:** 2-3 minutes per test case
- **Total Suite Time:** ~3 minutes

---

## References
- Test Plan: Section 1.1.2 - Validate CLI for MTU changes
- Related Test Cases: TC_INTF_EVENTS_CLI_001 (Admin state changes)
- SONiC Documentation: Interface Configuration Guide
- Testbed: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
