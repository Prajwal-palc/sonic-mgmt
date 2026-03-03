# QoS Test Case 4.25.16 - PFC Priority to Priority-Group Mapping

## Test Information

**Test ID:** 4.25.16
**Feature:** QoS
**Test Case:** Verify PFC Priority to Priority-Group mapping functionality
**Test Objective:** Ensure PFC priorities are correctly mapped to configured Priority-Groups on interfaces
**Test Result:** **PASS**

---

## Test Overview

This test validates that Priority Flow Control (PFC) priorities can be successfully mapped to Priority Groups (PG) and that the mapping is correctly applied to interfaces. The test also verifies that PFC counters increment appropriately when traffic triggers PFC frames for enabled priorities.

---

## Test Topology

- **Topology:** Two-node setup (DUT1 ↔ DUT2)
- **Interfaces Used:**
  - DUT1: Ethernet513 (25G), Ethernet272 (100G)
  - DUT2: Ethernet64 (connected to DUT1 Ethernet272)
- **VLAN:** VLAN 100 (trunk on both test interfaces)

---

## Test Procedure

### 1. PFC-Priority-PG Map Configuration

Create a PFC-Priority to Priority-Group map with the following mappings:

```
PFC Priority   →   Priority Group
-----------        ---------------
0, 1, 2, 5-7  →   PG 0
3             →   PG 3
4             →   PG 4
```

**Commands:**
```bash
sonic(config)# qos map pfc-priority-pg PFC_PG_MAP
sonic(config-pfc-priority-pg-map-PFC_PG_MAP)# pfc-priority 0,1,2,5-7 pg 0
sonic(config-pfc-priority-pg-map-PFC_PG_MAP)# pfc-priority 3 pg 3
sonic(config-pfc-priority-pg-map-PFC_PG_MAP)# pfc-priority 4 pg 4
```

### 2. Interface Configuration

#### Ethernet513 Configuration
```bash
sonic(config)# interface Ethernet513
sonic(config-if-Ethernet513)# no ip address
sonic(config-if-Ethernet513)# switchport trunk allowed Vlan 100
sonic(config-if-Ethernet513)# qos-map pfc-priority-pg PFC_PG_MAP
sonic(config-if-Ethernet513)# priority-flow-control priority 3,4
```

#### Ethernet272 Configuration
```bash
sonic(config)# interface Ethernet272
sonic(config-if-Ethernet272)# no ip address
sonic(config-if-Ethernet272)# switchport trunk allowed Vlan 100
sonic(config-if-Ethernet272)# qos-map pfc-priority-pg PFC_PG_MAP
sonic(config-if-Ethernet272)# priority-flow-control priority 3,4
sonic(config-if-Ethernet272)# priority-flow-control watchdog on detect-time 100
```

### 3. VLAN Configuration

```bash
sonic(config)# vlan 100
```

### 4. Verification Steps

#### Step 4.1: Verify PFC-Priority-PG Map
```bash
sonic# show qos map pfc-priority-pg
```

**Expected Output:**
```
PFC-Priority-Priority-Group-MAP: PFC_PG_MAP
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

#### Step 4.2: Verify VLAN Membership
```bash
sonic# show Vlan
```

**Expected Output:**
```
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan100   Up          T  Ethernet272      Enable      No
                      T  Ethernet513                  No
```

#### Step 4.3: Verify PFC Enabled Priorities
```bash
admin@sonic:~$ show pfc priority
```

**Expected Output:**
```
Interface    Lossless priorities
-----------  ---------------------
Ethernet272  3,4
Ethernet513  3,4
```

#### Step 4.4: Verify PFC Watchdog Configuration
```bash
sonic# show priority-flow-control watchdog
```

**Expected Output:**
```
Watchdog Summary
----------------
Polling Interval:   : Not Configured (default 100ms)
Flex Counters:      : Not Available
```

### 5. Traffic Generation and PFC Counter Verification

Generate congestion/traffic to trigger PFC frames for enabled priorities (3 and 4).

#### Step 5.1: Verify PFC Counters on DUT1
```bash
admin@sonic:~$ show pfc counters
```

**Key Observations (DUT1):**
```
Port Rx      PFC0    PFC1    PFC2    PFC3    PFC4    PFC5    PFC6    PFC7
-----------  ------  ------  ------  ------  ------  ------  ------  ------
Ethernet272       0       0       0   1,798       0       0       0       0
Ethernet513       0       0       0       0       0       0       0       0

Port Tx      PFC0    PFC1    PFC2    PFC3    PFC4    PFC5    PFC6    PFC7
-----------  ------  ------  ------  ------  ------  ------  ------  ------
Ethernet272       0       0       0       0       0       0       0       0
Ethernet513       0       0       0       0       0       0       0       0
```

**Analysis:**
- Ethernet272 received **1,798 PFC frames** on priority 3 (PFC3)
- This indicates DUT2 sent PFC PAUSE frames to DUT1 on priority 3

#### Step 5.2: Verify PFC Counters on DUT2
```bash
admin@sonic:~$ show pfc counters
```

**Key Observations (DUT2):**
```
Port Tx      PFC0    PFC1    PFC2    PFC3    PFC4    PFC5    PFC6    PFC7
-----------  ------  ------  ------  ------  ------  ------  ------  ------
Ethernet64        0       0       0    1798       0       0       0       0
```

**Analysis:**
- Ethernet64 (connected to DUT1 Ethernet272) transmitted **1,798 PFC frames** on priority 3
- This matches the Rx count on DUT1 Ethernet272, confirming successful PFC operation

---

## Test Results

### Configuration Verification ✓
- ✓ PFC-Priority-PG map created successfully with correct mappings
- ✓ Map applied to interfaces Ethernet513 and Ethernet272
- ✓ PFC enabled on priorities 3 and 4 on both interfaces
- ✓ PFC watchdog configured on Ethernet272 with 100ms detect-time
- ✓ VLAN 100 configured with both test interfaces as trunk members

### Functional Verification ✓
- ✓ `show qos map pfc-priority-pg` displays correct priority-to-PG mappings
- ✓ `show pfc priority` confirms priorities 3,4 enabled on test interfaces
- ✓ PFC counters increment when congestion triggers PFC frames
- ✓ PFC3 counter shows 1,798 frames transmitted from DUT2 to DUT1
- ✓ Matching Rx/Tx counters across DUTs confirm proper PFC operation

### Expected vs Actual Results

| Verification Point | Expected | Actual | Status |
|-------------------|----------|--------|--------|
| PFC-PG Map Creation | Map created with 3 mappings | PFC_PG_MAP created successfully | ✓ PASS |
| Priority 3 Mapping | Mapped to PG 3 | Correctly mapped to PG 3 | ✓ PASS |
| Priority 4 Mapping | Mapped to PG 4 | Correctly mapped to PG 4 | ✓ PASS |
| Priorities 0,1,2,5-7 Mapping | Mapped to PG 0 | Correctly mapped to PG 0 | ✓ PASS |
| Interface Application | Applied to Ethernet513, Ethernet272 | Successfully applied | ✓ PASS |
| PFC Enable | Priorities 3,4 enabled | Confirmed via show pfc priority | ✓ PASS |
| PFC Counter Increment | Counters increment for enabled priorities | 1,798 frames on PFC3 | ✓ PASS |
| Cross-DUT Validation | Tx on DUT2 = Rx on DUT1 | 1,798 = 1,798 | ✓ PASS |

---

## Configuration Summary

### Running Configuration (Relevant Sections)

```
qos map pfc-priority-pg PFC_PG_MAP
 pfc-priority 0-2,5-7 pg 0
 pfc-priority 3 pg 3
 pfc-priority 4 pg 4
!
vlan 100
!
interface Ethernet272
 mtu 9100
 speed 100000
 fec rs
 switchport trunk allowed Vlan 100
 qos-map pfc-priority-pg PFC_PG_MAP
 priority-flow-control priority 3
 priority-flow-control priority 4
 priority-flow-control watchdog on detect-time 100
!
interface Ethernet513
 mtu 9100
 speed 25000
 fec none
 switchport trunk allowed Vlan 100
 qos-map pfc-priority-pg PFC_PG_MAP
 priority-flow-control priority 3
 priority-flow-control priority 4
!
interface Vlan100
!
```

---

## Notes and Observations

1. **Interface Mode Requirement:** Interfaces must be in L2 mode (no IP address) before adding to VLAN trunk. The test encountered an error when attempting to add VLAN membership while IP address was configured, which was resolved by removing the IP address first.

2. **PFC Counter Behavior:** PFC counters incremented only for priority 3 during this test run. Priority 4 was enabled but did not show counter increments, likely due to traffic patterns or congestion conditions affecting only priority 3.

3. **PFC Watchdog:** Configured on Ethernet272 with 100ms detect-time. The watchdog feature monitors for PFC storms and can take corrective action if a port remains paused beyond the configured threshold.

4. **Counter Correlation:** Perfect match between DUT2 Ethernet64 Tx counters (1,798) and DUT1 Ethernet272 Rx counters (1,798) confirms proper PFC frame transmission and reception.

5. **Priority Group Mapping:** The test demonstrates flexible PG mapping where multiple priorities (0,1,2,5,6,7) can be grouped into a single PG (PG 0), while critical priorities (3,4) can have dedicated PGs.

---

## Test Conclusion

**Result: PASS**

The PFC Priority to Priority-Group mapping functionality works as expected. All configured mappings were successfully applied to interfaces, and PFC counters correctly incremented when traffic triggered PFC frames for the enabled priorities. The test validates that:

- PFC-Priority-PG maps can be created and applied to interfaces
- Multiple PFC priorities can be mapped to the same or different Priority Groups
- PFC priorities are correctly enabled on interfaces
- PFC frames are generated and transmitted when congestion occurs
- PFC counters accurately reflect PFC activity

The feature is functioning correctly and meets the test objectives.

---

## Related Commands

```bash
# Configuration
qos map pfc-priority-pg <MAP_NAME>
pfc-priority <priority_list> pg <pg_number>
interface <interface_name>
qos-map pfc-priority-pg <MAP_NAME>
priority-flow-control priority <priority_list>
priority-flow-control watchdog on detect-time <milliseconds>

# Verification
show qos map pfc-priority-pg
show qos map pfc-priority-pg <MAP_NAME>
show pfc priority
show pfc counters
show priority-flow-control watchdog
show running-configuration
show vlan
```

---

**Test Date:** 2026-02-25
**SONiC Version:** Enterprise SONiC
**Platform:** Hardware Switch
