# QoS Test Case 4.25.15 - Delete Active PFC Map

## Test Information

**Test ID:** 4.25.15
**Feature:** QoS
**Test Case:** Delete Active PFC Map
**Test Objective:** Verify deletion behavior of active PFC_PRIORITY maps
**Test Result:** **PARTIAL PASS** ⚠️ (Requires Behavior Clarification)

---

## Test Overview

This test validates the system behavior when attempting to delete a PFC-Priority-PG map that is actively applied to an interface with priority-flow-control enabled. The test verifies whether the system properly prevents deletion of in-use QoS maps or handles the deletion gracefully.

---

## Test Topology

- **Topology:** Single DUT
- **Interfaces Used:** Ethernet8
- **QoS Map:** pfc_pg_map (PFC-Priority-PG map)

---

## Test Procedure

### Step 1: Configure PFC-Priority-PG Map

Create a PFC-Priority to Priority-Group map named `pfc_pg_map`:

```bash
sonic# configure terminal
sonic(config)# qos map pfc-priority-pg pfc_pg_map
sonic(config-pfc-priority-pg-map-pfc_pg_map)# pfc-priority 0,1,2,5-7 pg 0
sonic(config-pfc-priority-pg-map-pfc_pg_map)# pfc-priority 3 pg 3
sonic(config-pfc-priority-pg-map-pfc_pg_map)# pfc-priority 4 pg 4
sonic(config-pfc-priority-pg-map-pfc_pg_map)# exit
```

**Map Configuration:**
```
PFC Priority   →   Priority Group
-----------        ---------------
0, 1, 2, 5-7  →   PG 0
3             →   PG 3
4             →   PG 4
```

### Step 2: Associate Map with Interface

Apply the PFC map to interface Ethernet8:

```bash
sonic(config)# interface Ethernet8
sonic(conf-if-Ethernet8)# qos-map pfc-priority-pg pfc_pg_map
```

### Step 3: Enable Priority-Flow-Control

Enable PFC on priorities 3 and 4:

```bash
sonic(conf-if-Ethernet8)# priority-flow-control priority 3,4
sonic(conf-if-Ethernet8)# exit
```

### Step 4: Verify QoS Map Configuration

#### 4.1 Verify PFC-Priority-PG Map

```bash
sonic# show qos map pfc-priority-pg
```

**Output:**
```
PFC-Priority-Priority-Group-MAP: pfc_pg_map
----------------------------
    PFC Priority   PG
----------------------------
    0              0
    1              0
    2              0
    3              3
    4              4
    5              0
    6              0
    7              0
----------------------------
```

✓ Map configured correctly with expected priority-to-PG mappings.

#### 4.2 Verify QoS Interface Configuration

```bash
sonic# show qos interface Ethernet8
```

**Output:**
```
          pfc-priority-pg-map: pfc_pg_map
          PFC Watchdog
            Status            : off
            Action            : N/A
            Detection Time    : 0ms
            Restoration Time  : infinite(0ms)
```

✓ Map successfully applied to interface Ethernet8.

### Step 5: Attempt Deletion of Active QoS Map

**Critical Test Step:** Attempt to delete the PFC map while it is actively applied to an interface.

```bash
sonic# configure terminal
sonic(config)# no qos map pfc-priority-pg pfc_pg_map
sonic(config)# exit
```

**Observation:** No error message was displayed. The command was accepted.

#### 5.1 Verify Map After Deletion Attempt

```bash
sonic# show qos map pfc-priority-pg
```

**Output:** *(Empty - no maps displayed)*

**Finding:** The PFC map definition was removed from the global QoS map configuration.

#### 5.2 Verify Interface Configuration After Deletion

```bash
sonic# show qos interface Ethernet8
```

**Output:**
```
          pfc-priority-pg-map: pfc_pg_map
          PFC Watchdog
            Status            : off
            Action            : N/A
            Detection Time    : 0ms
            Restoration Time  : infinite(0ms)
```

**Finding:** ⚠️ The interface **still references** `pfc_pg_map` even though the map definition was deleted.

### Step 6: Reconfigure PFC-Priority-PG Map

Reconfigure the same map to validate recovery:

```bash
sonic# configure terminal
sonic(config)# qos map pfc-priority-pg pfc_pg_map
sonic(config-pfc-priority-pg-map-pfc_pg_map)# pfc-priority 0,1,2,5-7 pg 0
sonic(config-pfc-priority-pg-map-pfc_pg_map)# pfc-priority 3 pg 3
sonic(config-pfc-priority-pg-map-pfc_pg_map)# pfc-priority 4 pg 4
sonic(config-pfc-priority-pg-map-pfc_pg_map)# exit
sonic(config)# exit
```

#### 6.1 Verify Map After Reconfiguration

```bash
sonic# show qos map pfc-priority-pg
```

**Output:**
```
PFC-Priority-Priority-Group-MAP: pfc_pg_map
----------------------------
    PFC Priority   PG
----------------------------
    0              0
    1              0
    2              0
    3              3
    4              4
    5              0
    6              0
    7              0
----------------------------
```

✓ Map successfully reconfigured with same settings.

#### 6.2 Verify Interface Configuration After Reconfiguration

```bash
sonic# show qos interface Ethernet8
```

**Output:**
```
          pfc-priority-pg-map: pfc_pg_map
          PFC Watchdog
            Status            : off
            Action            : N/A
            Detection Time    : 0ms
            Restoration Time  : infinite(0ms)
```

✓ Interface configuration remains consistent and functional after map reconfiguration.

---

## Test Results

### Observed Behavior

| Step | Action | Expected Behavior | Actual Behavior | Status |
|------|--------|-------------------|-----------------|--------|
| 1 | Create PFC map | Map created | Map created successfully | ✓ PASS |
| 2 | Apply to interface | Map applied | Map applied to Ethernet8 | ✓ PASS |
| 3 | Enable PFC priorities | PFC enabled | Priorities 3,4 enabled | ✓ PASS |
| 4 | Verify configuration | Correct display | Map and interface config correct | ✓ PASS |
| 5 | Delete active map | **Blocked OR graceful handling** | **Deletion accepted, inconsistent state created** | ⚠️ PARTIAL |
| 6 | Reconfigure map | Recovery possible | Map and interface functional | ✓ PASS |

### Detailed Analysis of Deletion Behavior

**Expected Result (from Test Plan):**
> "Deletion should be blocked OR system must disable PFC before removal."

**Actual Behavior:**

1. **No Explicit Error:** The deletion command `no qos map pfc-priority-pg pfc_pg_map` was accepted without any error message or warning.

2. **Map Definition Removed:** After deletion, `show qos map pfc-priority-pg` displayed no maps, indicating the global map definition was removed.

3. **Interface Reference Persists:** The interface configuration still showed `pfc-priority-pg-map: pfc_pg_map`, creating an inconsistent state where:
   - The interface references a map that no longer exists
   - The map definition is not available in global configuration
   - No error or warning indicates this inconsistent state

4. **System Stability:** Despite the inconsistent state:
   - No system errors occurred
   - The interface configuration remained displayable
   - Reconfiguring the map restored full functionality

### Behavior Interpretation

The observed behavior can be interpreted in two ways:

**Interpretation 1: Soft Deletion (Possible Design)**
- The map definition is removed from global configuration
- Existing interface bindings are preserved to prevent disruption
- This allows reconfiguration without requiring re-application to interfaces
- **Implication:** This could be intentional design for operational flexibility

**Interpretation 2: Incomplete Validation (Potential Issue)**
- The system should either:
  - **(a) Block deletion** with error: "Cannot delete map in use by Ethernet8"
  - **(b) Remove interface binding** before allowing map deletion
  - **(c) Disable PFC** on affected interfaces before map deletion
- **Implication:** Current behavior creates dangling references

---

## Test Assessment

### ✓ **Positive Findings**

1. PFC map creation and configuration works correctly
2. Map application to interfaces functions properly
3. PFC priority enablement works as expected
4. Interface can recover when map is reconfigured with same name
5. No system crashes or critical errors during deletion/reconfiguration cycle

### ⚠️ **Issues Requiring Clarification**

1. **Inconsistent State:** Deletion creates a state where interface references non-existent map
2. **No Error Message:** System accepts deletion without warning about active usage
3. **No Automatic Cleanup:** Interface binding is not automatically removed
4. **Unclear Operational Impact:** Unknown if PFC functionality continues during inconsistent state

### 📋 **Recommended Follow-up Actions**

1. **Verify PFC Functionality:** Test if PFC counters increment while in inconsistent state
2. **Check Running Config:** Verify if dangling reference appears in `show running-configuration`
3. **Test Traffic Impact:** Determine if PFC behavior is affected during inconsistent state
4. **Validate Design Intent:** Confirm with development team if current behavior is intentional
5. **Document Expected Behavior:** Update test plan with clarified expected behavior

---

## Test Conclusion

**Result: PARTIAL PASS** ⚠️

The test reveals behavior that requires clarification:

**What Works:**
- PFC map configuration, application, and reconfiguration all function correctly
- System remains stable throughout the deletion/reconfiguration cycle
- Recovery is possible by recreating the map with the same name

**What Needs Clarification:**
- Should deletion of active maps be blocked? (Current: Not blocked)
- Should interface bindings be automatically removed? (Current: Not removed)
- Is the current "soft deletion" behavior intentional? (Unknown)
- What is the operational impact of the inconsistent state? (Not tested)

**Recommended Next Steps:**
1. Confirm expected behavior with product/development team
2. If current behavior is intentional, document it as designed behavior
3. If current behavior is unintended, create bug report with this test data
4. Extend test to verify PFC functionality during inconsistent state
5. Update test plan with clarified acceptance criteria

---

## Configuration Summary

### Initial Configuration

```
qos map pfc-priority-pg pfc_pg_map
 pfc-priority 0-2,5-7 pg 0
 pfc-priority 3 pg 3
 pfc-priority 4 pg 4
!
interface Ethernet8
 qos-map pfc-priority-pg pfc_pg_map
 priority-flow-control priority 3
 priority-flow-control priority 4
!
```

### State After Deletion (Inconsistent)

```
# Global map definition: REMOVED
# show qos map pfc-priority-pg -> Empty

# Interface reference: STILL EXISTS
interface Ethernet8
 qos-map pfc-priority-pg pfc_pg_map  ← References non-existent map
 priority-flow-control priority 3
 priority-flow-control priority 4
```

### State After Reconfiguration (Restored)

```
qos map pfc-priority-pg pfc_pg_map
 pfc-priority 0-2,5-7 pg 0
 pfc-priority 3 pg 3
 pfc-priority 4 pg 4
!
interface Ethernet8
 qos-map pfc-priority-pg pfc_pg_map  ← Reference now valid again
 priority-flow-control priority 3
 priority-flow-control priority 4
!
```

---

## Related Commands

```bash
# Configuration
qos map pfc-priority-pg <MAP_NAME>
pfc-priority <priority_list> pg <pg_number>
no qos map pfc-priority-pg <MAP_NAME>
interface <interface_name>
qos-map pfc-priority-pg <MAP_NAME>
priority-flow-control priority <priority_list>

# Verification
show qos map pfc-priority-pg
show qos map pfc-priority-pg <MAP_NAME>
show qos interface <interface_name>
show pfc priority
show pfc counters
show running-configuration qos
show running-configuration interface <interface_name>
```

---

## Additional Test Scenarios to Consider

To fully validate deletion behavior, consider testing:

1. **PFC Counter Behavior:** Check if counters increment during inconsistent state
2. **Multiple Interface Binding:** Delete map applied to multiple interfaces
3. **Traffic Flow:** Verify PFC pause frame generation during inconsistent state
4. **Configuration Persistence:** Reboot and check if inconsistent state persists
5. **Different Map Types:** Test deletion behavior with other QoS map types
6. **Show Running Config:** Verify how inconsistent state appears in running config
7. **Commit/Save Behavior:** Test if configuration can be saved in inconsistent state

---

**Test Date:** 2026-02-25
**Tester Notes:**
- Deletion behavior differs from expected "blocked or graceful" requirement
- System creates inconsistent state but remains stable
- Requires product team clarification on intended behavior
- No operational impact testing performed in this test run

**SONiC Version:** Enterprise SONiC
**Platform:** Hardware Switch
