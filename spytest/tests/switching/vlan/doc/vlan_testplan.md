# VLAN Functionality Test Plan

## 1. Overview

This document outlines the comprehensive test plan for validating VLAN (Virtual Local Area Network) functionality in a leaf-spine network topology. The test plan covers all VLAN-related features including VLAN creation, configuration, tagging, untagging, port membership, packet forwarding behavior, and scalability testing. This test plan includes **58 test cases** organized into 11 functional areas.

## 2. Test Objectives

The primary objectives of this test plan are to:

- Validate VLAN creation, modification, and deletion operations
- Verify VLAN port membership (tagged and untagged)
- Test VLAN packet forwarding and isolation
- Validate VLAN configuration persistence
- Test inter-VLAN traffic isolation
- Verify VLAN tagging/untagging behavior
- Validate trunk port functionality
- Test access port functionality
- Verify VLAN configuration using CLI commands
- Validate packet behavior using Scapy-based traffic generation
- Test VLAN scalability with maximum VLANs, ports, and traffic loads
- Verify system performance and stability under scale conditions

## 3. Test Summary

This test plan comprises **58 test cases** organized into **11 functional areas**. The following table provides a breakdown of test cases by functionality:

| # | Functional Area | Test Case IDs | Number of Test Cases | Description |
|---|-----------------|---------------|---------------------|-------------|
| 1 | **VLAN Creation and Deletion** | TC_VLAN_CREATE_001 to 004<br>TC_VLAN_DELETE_001 to 002 | **6** | Basic VLAN lifecycle operations including creation with valid/invalid ranges and deletion scenarios |
| 2 | **Access Port Configuration** | TC_VLAN_ACCESS_001 to 004 | **4** | Untagged port configuration, traffic isolation, same-VLAN communication, and membership changes |
| 3 | **Trunk Port Configuration** | TC_VLAN_TRUNK_001 to 004 | **4** | Tagged port configuration, multi-VLAN traffic handling, VLAN filtering, and dynamic VLAN management |
| 4 | **Mixed Port Configuration** | TC_VLAN_MIXED_001 to 003 | **3** | Ports with both tagged and untagged VLANs, mixed traffic handling, and native VLAN behavior |
| 5 | **VLAN Packet Forwarding** | TC_VLAN_FORWARD_001 to 005 | **5** | Unicast, broadcast, multicast forwarding, inter-VLAN isolation, and unknown unicast flooding |
| 6 | **VLAN Tagging/Untagging** | TC_VLAN_TAG_001 to 004 | **4** | Ingress tagging, egress untagging, trunk port tagging, and double-tagged packet handling |
| 7 | **Configuration Persistence** | TC_VLAN_PERSIST_001 to 002 | **2** | Configuration save/reload and running-config accuracy verification |
| 8 | **VLAN Edge Cases** | TC_VLAN_EDGE_001 to 005 | **5** | Maximum VLANs support, all ports in single VLAN, rapid create/delete, VLAN 1 handling, and port in maximum VLANs |
| 9 | **VLAN Error Handling** | TC_VLAN_ERROR_001 to 003 | **3** | Non-existent VLAN operations, duplicate creation, and invalid VLAN ID handling |
| 10 | **Performance Tests** | TC_VLAN_PERF_001 to 002 | **2** | High traffic rate in single VLAN and multi-VLAN simultaneous traffic |
| 11 | **Scaling Tests** | TC_VLAN_SCALE_001 to 020 | **20** | Comprehensive scalability testing including maximum VLANs (4094), MAC table scale, high packet rates, resource monitoring, long-duration stability, and recovery |
| | **TOTAL** | | **58** | |

### Test Coverage Summary

- **Functional Tests**: 38 test cases covering core VLAN functionality
- **Scalability & Performance Tests**: 22 test cases covering performance, scale, and stress scenarios
- **Configuration Tests**: 8 test cases covering persistence, error handling, and edge cases
- **Traffic Validation**: All 58 test cases include Scapy-based packet generation and verification
- **Total Estimated Execution Time**: 35 hours

### Key Test Metrics

| Metric | Target |
|--------|--------|
| Maximum VLANs Tested | 4094 (full range) |
| Maximum VLANs per Port | 4093 |
| Maximum MAC Addresses per VLAN | 1000+ |
| Maximum Total MAC Addresses | 10,000 |
| Maximum Packet Rate | 10,000 pps |
| Long-Duration Test | 24 hours |
| Acceptable Packet Loss (Functional) | < 5% |
| Acceptable Packet Loss (Scaling) | < 2% |
| CPU Usage Threshold | < 80% |

## 4. Test Topology

### 4.1 Topology Description

The test environment consists of a leaf-spine topology with the following components:

- **1 DUT (Device Under Test)**: Primary switch running SONiC (Leaf)
- **1 SONiC-VS System**: Secondary system running SONiC Virtual Switch image with Scapy for packet generation/capture (Spine/Partner)
- **5 Test Ports**: Connected between the DUT and SONiC-VS system for VLAN testing

### 4.2 Topology Diagram

```
     ┌────────────────────────────────────────────────────┐
     │         Test System (SONiC-VS + Scapy)             │
     │                                                     │
     │  ┌──────────────────────────────────────────────┐  │
     │  │           SONiC-VS (Spine/Partner)           │  │
     │  └──┬────┬────┬────┬────┬──────────────────────┘  │
     │     │    │    │    │    │                          │
     │  ┌──┴─┐ ┌┴───┐ ┌──┴─┐ ┌─┴──┐ ┌──┴─┐               │
     │  │Eth0│ │Eth1│ │Eth2│ │Eth3│ │Eth4│               │
     │  └──┬─┘ └┬───┘ └──┬─┘ └─┬──┘ └──┬─┘               │
     │     │    │       │     │      │                    │
     │  ┌──┴────┴───────┴─────┴──────┴────────────────┐   │
     │  │         Scapy Traffic Generator             │   │
     │  │         (TX/RX on all interfaces)           │   │
     │  └─────────────────────────────────────────────┘   │
     └─────┼────┼───────┼─────┼──────┼────────────────────┘
           │    │       │     │      │
           │    │       │     │      │  Physical/Virtual Links
           │    │       │     │      │
     ┌─────┼────┼───────┼─────┼──────┼────────────────────┐
     │  ┌──┴─┐ ┌┴───┐ ┌─┴──┐ ┌┴───┐ ┌┴───┐               │
     │  │Por1│ │Por2│ │Por3│ │Por4│ │Por5│               │
     │  └──┬─┘ └┬───┘ └──┬─┘ └─┬──┘ └──┬─┘               │
     │     │    │       │     │      │                    │
     │  └──┴────┴───────┴─────┴──────┴────────────────┘   │
     │            DUT (Leaf Switch - SONiC)               │
     │                                                     │
     └────────────────────────────────────────────────────┘
```

### 4.3 Port Configuration Overview

| Port | Purpose | VLAN Configuration (Example) |
|------|---------|------------------------------|
| Port1 | Access Port Testing | Untagged VLAN 10 |
| Port2 | Access Port Testing | Untagged VLAN 20 |
| Port3 | Trunk Port Testing | Tagged VLAN 10, 20, 30 |
| Port4 | Mixed Mode Testing | Tagged VLAN 10, Untagged VLAN 20 |
| Port5 | Trunk Port Testing | Tagged VLAN 10, 20, 30, 40 |

## 5. Test Environment

### 5.1 Hardware Requirements

- **DUT**: SONiC-capable switch/device (Leaf)
- **Test System**: Server/VM running SONiC-VS image (Spine)
- **Network connectivity**: 5 ports connected between DUT and SONiC-VS system

### 5.2 Software Requirements

- **SONiC operating system** on DUT
- **SONiC-VS image** on test system (Spine/Partner)
- **Python with Scapy library** installed on SONiC-VS test system for packet generation and capture
- **SSH access** to both DUT and SONiC-VS test system

### 5.3 Test Tools

- **Scapy**: Packet crafting and transmission (runs on SONiC-VS system)
- **SONiC CLI**: Configuration and verification (both DUT and SONiC-VS)
- **show running-config**: Configuration validation

## 6. Test Methodology

### 6.1 General Test Flow

For each test case, the following methodology will be applied:

1. **Pre-Configuration**: Clear any existing VLAN configurations
2. **Configuration**: Apply VLAN configuration via CLI
3. **Verification**: Validate configuration using `show running-config`
4. **Traffic Generation**: Send test packets using Scapy
5. **Result Validation**: Verify packet forwarding behavior
6. **Cleanup**: Remove test configurations

### 6.2 Validation Criteria

- Configuration commands must execute without errors
- `show running-config` must reflect applied configurations
- Packet forwarding must match expected VLAN behavior
- VLAN isolation must be maintained between different VLANs
- Tagged packets must retain correct VLAN tags
- Untagged packets must be properly tagged/untagged

## 7. Test Case Naming Convention

Test case IDs follow the format: **TC_\<MODULE_NAME\>_\<SUBMODULE_NAME\>_\<THREE_DIGIT_NUMBER\>**

Example: `TC_VLAN_CREATE_001`

## 8. Test Cases

### 8.1 VLAN Creation and Deletion

#### TC_VLAN_CREATE_001: Create Single VLAN
**Objective**: Verify single VLAN creation
**Steps**:
1. Create VLAN 10
2. Execute `show running-config` to verify VLAN 10 exists
3. Verify VLAN appears in VLAN database

**Expected Result**: VLAN 10 is created successfully and appears in configuration

---

#### TC_VLAN_CREATE_002: Create Multiple VLANs
**Objective**: Verify multiple VLAN creation
**Steps**:
1. Create VLANs 10, 20, 30, 40, 50
2. Execute `show running-config` to verify all VLANs exist
3. Verify all VLANs appear in VLAN database

**Expected Result**: All VLANs are created successfully

---

#### TC_VLAN_DELETE_001: Delete Single VLAN
**Objective**: Verify VLAN deletion
**Steps**:
1. Create VLAN 100
2. Verify VLAN 100 exists
3. Delete VLAN 100
4. Execute `show running-config` to verify VLAN 100 is removed

**Expected Result**: VLAN 100 is deleted successfully

---

#### TC_VLAN_DELETE_002: Delete VLAN with Active Members
**Objective**: Verify behavior when deleting VLAN with port members
**Steps**:
1. Create VLAN 100
2. Add Port1 as untagged member
3. Attempt to delete VLAN 100
4. Verify expected behavior (should fail or remove ports first)

**Expected Result**: System handles deletion appropriately

---

#### TC_VLAN_CREATE_003: Create VLAN with Valid Range
**Objective**: Verify VLAN creation with valid VLAN IDs (1-4094)
**Steps**:
1. Create VLAN 1 (default VLAN)
2. Create VLAN 4094 (maximum VLAN ID)
3. Verify both VLANs exist

**Expected Result**: VLANs with valid IDs are created successfully

---

#### TC_VLAN_CREATE_004: Create VLAN with Invalid Range
**Objective**: Verify system rejects invalid VLAN IDs
**Steps**:
1. Attempt to create VLAN 0
2. Attempt to create VLAN 4095
3. Verify error messages

**Expected Result**: System rejects invalid VLAN IDs with appropriate errors

---

### 8.2 Access Port Configuration

#### TC_VLAN_ACCESS_001: Configure Untagged Port
**Objective**: Verify access port configuration
**Steps**:
1. Create VLAN 10
2. Configure Port1 as untagged member of VLAN 10
3. Execute `show running-config` to verify port configuration
4. Send untagged packet from Port1 using Scapy
5. Verify packet is tagged with VLAN 10 tag

**Expected Result**: Port1 is configured as access port in VLAN 10

---

#### TC_VLAN_ACCESS_002: Access Port Traffic Isolation
**Objective**: Verify traffic isolation between different access VLANs
**Steps**:
1. Create VLANs 10 and 20
2. Configure Port1 as untagged member of VLAN 10
3. Configure Port2 as untagged member of VLAN 20
4. Send packet from Port1 to Port2's MAC using Scapy
5. Verify packet is NOT received on Port2

**Expected Result**: Traffic from VLAN 10 does not reach VLAN 20

---

#### TC_VLAN_ACCESS_003: Access Port Same VLAN Communication
**Objective**: Verify communication between ports in same VLAN
**Steps**:
1. Create VLAN 10
2. Configure Port1 and Port2 as untagged members of VLAN 10
3. Send packet from Port1 to Port2's MAC using Scapy
4. Verify packet is received on Port2

**Expected Result**: Ports in same VLAN can communicate

---

#### TC_VLAN_ACCESS_004: Change Access Port VLAN Membership
**Objective**: Verify changing access port VLAN assignment
**Steps**:
1. Create VLANs 10 and 20
2. Configure Port1 as untagged member of VLAN 10
3. Verify Port1 in VLAN 10 using `show running-config`
4. Change Port1 to untagged member of VLAN 20
5. Verify Port1 in VLAN 20 using `show running-config`

**Expected Result**: Port VLAN membership changes successfully

---

### 8.3 Trunk Port Configuration

#### TC_VLAN_TRUNK_001: Configure Tagged Port
**Objective**: Verify trunk port configuration with tagged VLANs
**Steps**:
1. Create VLANs 10, 20, 30
2. Configure Port3 as tagged member of VLANs 10, 20, 30
3. Execute `show running-config` to verify configuration
4. Send VLAN 10 tagged packet from Port3 using Scapy
5. Verify packet forwarding with VLAN 10 tag

**Expected Result**: Port3 configured as trunk with multiple VLANs

---

#### TC_VLAN_TRUNK_002: Trunk Port Multiple VLAN Traffic
**Objective**: Verify trunk port handles multiple VLAN traffic
**Steps**:
1. Create VLANs 10, 20
2. Configure Port3 as tagged member of VLANs 10, 20
3. Configure Port1 as untagged member of VLAN 10
4. Configure Port2 as untagged member of VLAN 20
5. Send VLAN 10 tagged packet from Port3 using Scapy
6. Verify packet received on Port1 (untagged)
7. Send VLAN 20 tagged packet from Port3 using Scapy
8. Verify packet received on Port2 (untagged)

**Expected Result**: Trunk port correctly forwards traffic for multiple VLANs

---

#### TC_VLAN_TRUNK_003: Trunk Port VLAN Filtering
**Objective**: Verify trunk port filters non-member VLAN traffic
**Steps**:
1. Create VLANs 10, 20, 30
2. Configure Port3 as tagged member of VLANs 10, 20 only
3. Send VLAN 30 tagged packet from Port3 using Scapy
4. Verify packet is dropped (VLAN 30 not allowed)

**Expected Result**: Trunk port drops traffic for non-member VLANs

---

#### TC_VLAN_TRUNK_004: Add/Remove VLANs from Trunk
**Objective**: Verify dynamic VLAN addition/removal on trunk
**Steps**:
1. Create VLANs 10, 20, 30
2. Configure Port3 as tagged member of VLAN 10
3. Add VLAN 20 to Port3
4. Verify configuration using `show running-config`
5. Remove VLAN 10 from Port3
6. Verify VLAN 10 removed using `show running-config`

**Expected Result**: VLANs can be added/removed from trunk dynamically

---

### 8.4 Mixed Port Configuration (Tagged + Untagged)

#### TC_VLAN_MIXED_001: Configure Port with Tagged and Untagged VLANs
**Objective**: Verify port with both tagged and untagged VLAN configuration
**Steps**:
1. Create VLANs 10, 20
2. Configure Port4 as untagged member of VLAN 20
3. Configure Port4 as tagged member of VLAN 10
4. Execute `show running-config` to verify configuration

**Expected Result**: Port4 configured with both tagged and untagged VLANs

---

#### TC_VLAN_MIXED_002: Mixed Port Traffic Handling
**Objective**: Verify traffic handling on mixed mode port
**Steps**:
1. Create VLANs 10, 20
2. Configure Port4 as untagged VLAN 20, tagged VLAN 10
3. Send untagged packet from Port4 using Scapy
4. Verify packet tagged with VLAN 20
5. Send VLAN 10 tagged packet from Port4 using Scapy
6. Verify packet forwarded with VLAN 10 tag

**Expected Result**: Mixed port correctly handles tagged and untagged traffic

---

#### TC_VLAN_MIXED_003: Native VLAN Behavior
**Objective**: Verify native VLAN (untagged) behavior on trunk port
**Steps**:
1. Create VLANs 10, 20
2. Configure Port4 as native VLAN 20 with tagged VLANs 10
3. Send untagged packet from Port4
4. Verify packet belongs to native VLAN 20
5. Send VLAN 10 tagged packet from Port4
6. Verify packet forwarded in VLAN 10

**Expected Result**: Native VLAN handles untagged traffic correctly

---

### 8.5 VLAN Packet Forwarding

#### TC_VLAN_FORWARD_001: Intra-VLAN Unicast Forwarding
**Objective**: Verify unicast packet forwarding within VLAN
**Steps**:
1. Create VLAN 10
2. Configure Port1, Port2 as untagged members of VLAN 10
3. Send unicast packet from Port1 to Port2's MAC using Scapy
4. Verify packet received on Port2 only

**Expected Result**: Unicast packet forwarded to destination port in same VLAN

---

#### TC_VLAN_FORWARD_002: Intra-VLAN Broadcast Forwarding
**Objective**: Verify broadcast packet forwarding within VLAN
**Steps**:
1. Create VLAN 10
2. Configure Port1, Port2, Port3 as members of VLAN 10
3. Send broadcast packet from Port1 using Scapy
4. Verify packet received on Port2 and Port3
5. Verify packet NOT received on ports in other VLANs

**Expected Result**: Broadcast forwarded to all ports in VLAN 10 only

---

#### TC_VLAN_FORWARD_003: Intra-VLAN Multicast Forwarding
**Objective**: Verify multicast packet forwarding within VLAN
**Steps**:
1. Create VLAN 10
2. Configure Port1, Port2, Port3 as members of VLAN 10
3. Send multicast packet from Port1 using Scapy
4. Verify packet received on Port2 and Port3
5. Verify packet NOT received on ports in other VLANs

**Expected Result**: Multicast forwarded to all ports in VLAN 10 only

---

#### TC_VLAN_FORWARD_004: Inter-VLAN Isolation
**Objective**: Verify traffic isolation between different VLANs
**Steps**:
1. Create VLANs 10, 20
2. Configure Port1 in VLAN 10
3. Configure Port2 in VLAN 20
4. Send packet from Port1 to Port2's MAC using Scapy
5. Verify packet NOT received on Port2

**Expected Result**: VLANs are properly isolated

---

#### TC_VLAN_FORWARD_005: Unknown Unicast Flooding
**Objective**: Verify unknown unicast flooding behavior within VLAN
**Steps**:
1. Create VLAN 10
2. Configure Port1, Port2, Port3 as members of VLAN 10
3. Send packet to unknown MAC from Port1 using Scapy
4. Verify packet flooded to Port2 and Port3

**Expected Result**: Unknown unicast flooded within VLAN

---

### 8.6 VLAN Tagging/Untagging

#### TC_VLAN_TAG_001: Ingress Untagged Packet Tagging
**Objective**: Verify untagged packet is tagged on ingress
**Steps**:
1. Create VLAN 10
2. Configure Port1 as untagged member of VLAN 10
3. Configure Port3 as tagged member of VLAN 10
4. Send untagged packet from Port1 using Scapy
5. Capture packet on Port3 using Scapy
6. Verify packet has VLAN 10 tag

**Expected Result**: Untagged ingress packet is tagged with port VLAN

---

#### TC_VLAN_TAG_002: Egress Tagged Packet on Access Port
**Objective**: Verify tagged packet is untagged on access port egress
**Steps**:
1. Create VLAN 10
2. Configure Port1 as untagged member of VLAN 10
3. Configure Port3 as tagged member of VLAN 10
4. Send VLAN 10 tagged packet from Port3 using Scapy
5. Capture packet on Port1 using Scapy
6. Verify packet is untagged

**Expected Result**: Tagged packet untagged when egressing access port

---

#### TC_VLAN_TAG_003: Tagged Packet on Trunk Port
**Objective**: Verify tagged packet remains tagged on trunk port
**Steps**:
1. Create VLAN 10
2. Configure Port3 and Port5 as tagged members of VLAN 10
3. Send VLAN 10 tagged packet from Port3 using Scapy
4. Capture packet on Port5 using Scapy
5. Verify packet retains VLAN 10 tag

**Expected Result**: Tagged packet remains tagged on trunk ports

---

#### TC_VLAN_TAG_004: Double Tagged Packet Handling
**Objective**: Verify Q-in-Q (double tagged) packet handling
**Steps**:
1. Create VLAN 10
2. Configure Port3 as tagged member of VLAN 10
3. Send double tagged packet (outer VLAN 10, inner VLAN 20) using Scapy
4. Verify expected behavior based on switch configuration

**Expected Result**: Double tagged packets handled according to switch policy

---

### 8.7 VLAN Configuration Persistence

#### TC_VLAN_PERSIST_001: Configuration Save and Reload
**Objective**: Verify VLAN configuration persists after save
**Steps**:
1. Create VLANs 10, 20, 30
2. Configure port memberships
3. Execute config save command
4. Execute `show running-config` to verify configuration
5. Reload configuration
6. Verify VLAN configuration persists using `show running-config`

**Expected Result**: VLAN configuration persists after reload

---

#### TC_VLAN_PERSIST_002: Running Config Accuracy
**Objective**: Verify `show running-config` accurately reflects VLAN config
**Steps**:
1. Create VLAN 10
2. Add Port1 as untagged member
3. Add Port3 as tagged member
4. Execute `show running-config`
5. Verify all configurations are accurately displayed

**Expected Result**: Running config accurately shows all VLAN settings

---

### 8.8 VLAN Edge Cases

#### TC_VLAN_EDGE_001: Maximum VLANs Support
**Objective**: Verify maximum number of VLANs supported
**Steps**:
1. Create maximum number of VLANs (implementation dependent)
2. Verify all VLANs created successfully
3. Verify system performance remains stable

**Expected Result**: System supports maximum VLANs without issues

---

#### TC_VLAN_EDGE_002: All Ports in Single VLAN
**Objective**: Verify all ports can be assigned to single VLAN
**Steps**:
1. Create VLAN 100
2. Add all 5 ports as members of VLAN 100
3. Verify configuration using `show running-config`
4. Test packet forwarding between all ports

**Expected Result**: All ports function correctly in single VLAN

---

#### TC_VLAN_EDGE_003: Rapid VLAN Create/Delete
**Objective**: Verify system stability with rapid VLAN operations
**Steps**:
1. Create VLAN 100
2. Delete VLAN 100
3. Repeat steps 1-2 rapidly (100 iterations)
4. Verify system remains stable

**Expected Result**: System handles rapid VLAN operations without issues

---

#### TC_VLAN_EDGE_004: VLAN 1 Special Handling
**Objective**: Verify default VLAN 1 behavior
**Steps**:
1. Verify VLAN 1 exists by default
2. Test adding/removing ports from VLAN 1
3. Attempt to delete VLAN 1
4. Verify expected behavior

**Expected Result**: VLAN 1 handled according to specification

---

#### TC_VLAN_EDGE_005: Port in Maximum VLANs
**Objective**: Verify port can be member of maximum VLANs (trunk)
**Steps**:
1. Create multiple VLANs (10, 20, 30, 40, 50, etc.)
2. Configure Port3 as tagged member of all VLANs
3. Verify configuration using `show running-config`
4. Test packet forwarding for different VLANs

**Expected Result**: Port functions correctly with maximum VLAN memberships

---

### 8.9 VLAN Error Handling

#### TC_VLAN_ERROR_001: Add Port to Non-Existent VLAN
**Objective**: Verify error handling when adding port to non-existent VLAN
**Steps**:
1. Attempt to add Port1 to VLAN 999 without creating it
2. Verify appropriate error message
3. Verify Port1 configuration unchanged

**Expected Result**: System rejects operation with clear error message

---

#### TC_VLAN_ERROR_002: Duplicate VLAN Creation
**Objective**: Verify handling of duplicate VLAN creation
**Steps**:
1. Create VLAN 10
2. Attempt to create VLAN 10 again
3. Verify appropriate response (success or informational message)

**Expected Result**: System handles duplicate creation gracefully

---

#### TC_VLAN_ERROR_003: Invalid VLAN ID
**Objective**: Verify rejection of invalid VLAN IDs
**Steps**:
1. Attempt to create VLAN with ID 5000
2. Attempt to create VLAN with ID -1
3. Attempt to create VLAN with non-numeric ID
4. Verify error messages for all attempts

**Expected Result**: All invalid VLAN IDs rejected with errors

---

### 8.10 VLAN Performance Tests

#### TC_VLAN_PERF_001: High Traffic Rate in Single VLAN
**Objective**: Verify VLAN forwarding under high traffic load
**Steps**:
1. Create VLAN 10 with multiple ports
2. Generate high rate traffic (1000 pps) using Scapy
3. Verify packet forwarding accuracy
4. Monitor for packet loss

**Expected Result**: VLAN forwards high-rate traffic without significant loss

---

#### TC_VLAN_PERF_002: Multi-VLAN Simultaneous Traffic
**Objective**: Verify performance with simultaneous multi-VLAN traffic
**Steps**:
1. Create VLANs 10, 20, 30, 40, 50
2. Send simultaneous traffic on all VLANs using Scapy
3. Verify correct forwarding for all VLANs
4. Monitor for packet loss and VLAN mixing

**Expected Result**: All VLAN traffic forwarded correctly without mixing

---

### 8.11 VLAN Scaling Tests

#### TC_VLAN_SCALE_001: Maximum VLAN Creation
**Objective**: Verify system can create and maintain maximum number of VLANs
**Steps**:
1. Determine maximum VLAN limit (typically 4094 VLANs: VLAN 1-4094)
2. Create maximum number of VLANs using automation script
3. Execute `show running-config` to verify all VLANs exist
4. Verify system stability (CPU, memory usage)
5. Test configuration save and reload with maximum VLANs
6. Verify all VLANs persist after reload

**Expected Result**: System creates and maintains maximum VLANs without performance degradation

---

#### TC_VLAN_SCALE_002: Maximum Ports per VLAN
**Objective**: Verify VLAN can handle all available ports as members
**Steps**:
1. Create VLAN 100
2. Add all 5 test ports as members (both tagged and untagged) to VLAN 100
3. Execute `show running-config` to verify all port memberships
4. Send broadcast packet from Port1 using Scapy
5. Verify packet received on all other ports in VLAN 100
6. Monitor system performance metrics

**Expected Result**: VLAN supports all ports without issues

---

#### TC_VLAN_SCALE_003: Maximum VLANs per Port (Trunk)
**Objective**: Verify port can be member of maximum VLANs
**Steps**:
1. Create VLANs 2-4094 (4093 VLANs)
2. Configure Port3 as tagged member of all VLANs
3. Execute `show running-config` to verify configuration
4. Send tagged packets for different VLANs (10, 100, 1000, 2000, 4000) from Port3 using Scapy
5. Verify correct forwarding for all tested VLANs
6. Monitor port performance and system resources

**Expected Result**: Port handles maximum VLAN memberships without errors

---

#### TC_VLAN_SCALE_004: Large MAC Address Table per VLAN
**Objective**: Verify VLAN handles large MAC address table
**Steps**:
1. Create VLAN 10
2. Configure Port1, Port2, Port3 as members of VLAN 10
3. Generate traffic from 1000+ unique source MAC addresses using Scapy on Port1
4. Verify MAC addresses are learned in VLAN 10
5. Send unicast packets to learned MAC addresses
6. Verify correct forwarding based on MAC table
7. Monitor MAC table size and lookup performance

**Expected Result**: VLAN maintains large MAC table with correct forwarding

---

#### TC_VLAN_SCALE_005: High Packet Rate Across Multiple VLANs
**Objective**: Verify system handles high packet rates across many VLANs simultaneously
**Steps**:
1. Create VLANs 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
2. Configure ports across different VLANs
3. Generate simultaneous high-rate traffic (10,000 pps) on all VLANs using Scapy
4. Monitor packet forwarding accuracy for each VLAN
5. Verify VLAN isolation maintained under load
6. Measure packet loss, latency, and throughput per VLAN
7. Monitor CPU and memory usage

**Expected Result**: System handles high packet rates across multiple VLANs with <1% packet loss

---

#### TC_VLAN_SCALE_006: Bulk VLAN Configuration Time
**Objective**: Measure and verify time to configure large number of VLANs
**Steps**:
1. Clear all VLAN configurations
2. Start timer
3. Create 1000 VLANs (VLAN 100-1099) using automation script
4. Stop timer and record configuration time
5. Execute `show running-config` to verify all VLANs created
6. Verify configuration time is within acceptable limits (< 5 minutes)

**Expected Result**: Bulk VLAN configuration completes in reasonable time

---

#### TC_VLAN_SCALE_007: Bulk Port Membership Configuration
**Objective**: Verify time to add ports to large number of VLANs
**Steps**:
1. Create VLANs 10-500 (491 VLANs)
2. Start timer
3. Configure Port3 as tagged member of all VLANs using automation
4. Stop timer and record configuration time
5. Execute `show running-config` to verify all memberships
6. Test packet forwarding for sample VLANs (10, 100, 250, 500)

**Expected Result**: Port membership configuration completes efficiently

---

#### TC_VLAN_SCALE_008: Memory Usage Under VLAN Scale
**Objective**: Verify memory usage remains stable with maximum VLANs
**Steps**:
1. Record baseline memory usage
2. Create 1000 VLANs incrementally (batches of 100)
3. Monitor memory usage after each batch
4. Configure port memberships for all VLANs
5. Monitor memory usage with full configuration
6. Generate traffic on all VLANs
7. Verify no memory leaks or excessive memory consumption

**Expected Result**: Memory usage scales linearly and remains within acceptable limits

---

#### TC_VLAN_SCALE_009: CPU Usage Under VLAN Scale
**Objective**: Verify CPU usage remains stable with scaled VLAN configuration
**Steps**:
1. Record baseline CPU usage
2. Create 1000 VLANs with port memberships
3. Monitor CPU usage during configuration
4. Generate high-rate traffic across all VLANs using Scapy
5. Monitor CPU usage during traffic forwarding
6. Verify CPU usage remains < 80% under load

**Expected Result**: CPU usage remains acceptable during scaled operations

---

#### TC_VLAN_SCALE_010: VLAN Database Consistency at Scale
**Objective**: Verify VLAN database consistency with large configurations
**Steps**:
1. Create 2000 VLANs (VLAN 100-2099)
2. Configure random port memberships across all VLANs
3. Execute `show running-config` and save output
4. Perform configuration save
5. Reload system/configuration
6. Execute `show running-config` and compare with saved output
7. Verify all VLANs and memberships match exactly

**Expected Result**: VLAN database remains consistent at scale

---

#### TC_VLAN_SCALE_011: Broadcast Storm Control at Scale
**Objective**: Verify broadcast handling across many VLANs simultaneously
**Steps**:
1. Create VLANs 10-100 (91 VLANs)
2. Configure multiple ports in each VLAN
3. Send broadcast packets simultaneously on all VLANs using Scapy (100 pps per VLAN)
4. Verify broadcasts contained within respective VLANs
5. Monitor CPU usage and packet forwarding performance
6. Verify no broadcast storms or packet loss

**Expected Result**: System handles broadcast traffic across multiple VLANs without storms

---

#### TC_VLAN_SCALE_012: Rapid VLAN Membership Changes at Scale
**Objective**: Verify system stability during rapid membership changes
**Steps**:
1. Create VLANs 10, 20, 30, 40, 50
2. Perform 1000 iterations of:
   - Add Port1 to random VLAN
   - Remove Port1 from current VLAN
   - Add Port1 to different VLAN
3. Monitor system stability during operations
4. Verify final configuration is accurate
5. Test packet forwarding after changes

**Expected Result**: System handles rapid membership changes without errors

---

#### TC_VLAN_SCALE_013: Mixed Traffic Pattern at Scale
**Objective**: Verify VLAN forwarding with mixed traffic patterns at scale
**Steps**:
1. Create VLANs 10-50 (41 VLANs)
2. Configure mixed port memberships (access, trunk, mixed)
3. Generate mixed traffic using Scapy:
   - Unicast packets (50%)
   - Broadcast packets (30%)
   - Multicast packets (20%)
4. Send traffic simultaneously on all VLANs at high rate (5000 pps total)
5. Verify correct forwarding for all traffic types
6. Monitor packet loss and VLAN isolation

**Expected Result**: Mixed traffic forwarded correctly across all VLANs with <2% loss

---

#### TC_VLAN_SCALE_014: VLAN Forwarding Table Scalability
**Objective**: Verify forwarding table performance with maximum VLANs and MACs
**Steps**:
1. Create 100 VLANs (VLAN 10-109)
2. Generate traffic to populate MAC tables with 100 MACs per VLAN (10,000 total MACs)
3. Verify MAC address learning across all VLANs
4. Send unicast traffic to random learned MACs using Scapy
5. Verify correct L2 forwarding based on MAC and VLAN
6. Measure forwarding lookup performance

**Expected Result**: Forwarding table scales efficiently with correct forwarding

---

#### TC_VLAN_SCALE_015: VLAN Configuration Rollback at Scale
**Objective**: Verify configuration rollback works with large VLAN configurations
**Steps**:
1. Create baseline configuration with 500 VLANs
2. Save configuration as checkpoint
3. Add 500 more VLANs and modify port memberships
4. Execute `show running-config` to verify changes
5. Perform configuration rollback to checkpoint
6. Verify system returns to baseline (500 VLANs)
7. Test packet forwarding after rollback

**Expected Result**: Rollback successfully restores previous VLAN configuration

---

#### TC_VLAN_SCALE_016: Inter-VLAN Routing Scalability (if supported)
**Objective**: Verify inter-VLAN routing performance at scale
**Steps**:
1. Create 50 VLANs with IP interfaces configured
2. Configure routing between all VLANs
3. Generate inter-VLAN routed traffic using Scapy (1000 pps)
4. Verify packets routed correctly between VLANs
5. Monitor routing table size and lookup performance
6. Measure latency and throughput for routed traffic

**Expected Result**: Inter-VLAN routing scales with acceptable performance (if feature supported)

---

#### TC_VLAN_SCALE_017: VLAN Deletion at Scale
**Objective**: Verify bulk VLAN deletion performance
**Steps**:
1. Create 1000 VLANs (VLAN 1000-1999)
2. Configure port memberships for all VLANs
3. Verify all VLANs exist using `show running-config`
4. Start timer
5. Delete all 1000 VLANs using automation
6. Stop timer and record deletion time
7. Verify all VLANs removed from configuration
8. Verify system stability after bulk deletion

**Expected Result**: Bulk VLAN deletion completes efficiently without errors

---

#### TC_VLAN_SCALE_018: Concurrent VLAN Operations at Scale
**Objective**: Verify system handles concurrent VLAN operations
**Steps**:
1. Perform concurrent operations using multiple sessions:
   - Session 1: Create VLANs 100-200
   - Session 2: Create VLANs 300-400
   - Session 3: Configure port memberships for VLANs 100-200
   - Session 4: Send test traffic on existing VLANs
2. Monitor for configuration conflicts or errors
3. Verify all operations complete successfully
4. Execute `show running-config` to verify final state

**Expected Result**: System handles concurrent VLAN operations without conflicts

---

#### TC_VLAN_SCALE_019: Long-Duration Stability Test
**Objective**: Verify VLAN functionality remains stable over extended period
**Steps**:
1. Create 100 VLANs with full port configurations
2. Generate continuous traffic on all VLANs using Scapy (1000 pps)
3. Run test for 24 hours continuously
4. Periodically verify (every hour):
   - Packet forwarding accuracy
   - VLAN isolation
   - Memory and CPU usage
   - No configuration drift
5. Verify system stability after 24 hours

**Expected Result**: System maintains stable VLAN operation for 24+ hours

---

#### TC_VLAN_SCALE_020: Resource Exhaustion Recovery
**Objective**: Verify system recovery when VLAN resources exhausted
**Steps**:
1. Create maximum number of VLANs (4094)
2. Attempt to create one more VLAN
3. Verify appropriate error message
4. Delete 10 VLANs
5. Create 10 new VLANs in freed slots
6. Verify new VLANs created successfully
7. Test packet forwarding on new VLANs

**Expected Result**: System handles resource limits gracefully and recovers

---

## 9. Pass/Fail Criteria

### 9.1 Pass Criteria

A test case passes if:
- Configuration commands execute without errors
- `show running-config` reflects correct configuration
- Packet forwarding behavior matches expected VLAN operation
- VLAN isolation is maintained
- Tagging/untagging behavior is correct
- No packet loss or corruption occurs (< 5% loss for functional tests, < 2% for scaling tests)
- Error handling works as expected
- **For scaling tests specifically:**
  - System remains stable with maximum VLANs configured
  - CPU usage remains below 80% under load
  - Memory usage does not show leaks or excessive consumption
  - Configuration operations complete within expected timeframes
  - Packet forwarding maintains accuracy under high load
  - System recovers gracefully from resource exhaustion

### 9.2 Fail Criteria

A test case fails if:
- Configuration commands fail unexpectedly
- `show running-config` does not reflect applied configuration
- Packets leak between VLANs
- Incorrect VLAN tags applied or removed
- Packet loss exceeds acceptable threshold (5% for functional tests, 2% for scaling tests)
- System crashes or becomes unstable
- Error messages are unclear or misleading
- **For scaling tests specifically:**
  - System fails to create expected number of VLANs
  - CPU usage exceeds 90% during normal operations
  - Memory leaks detected during long-duration tests
  - Packet forwarding accuracy degrades significantly under load
  - Configuration operations timeout or hang
  - System fails to recover from resource limits

## 10. Test Execution Schedule

| Phase | Test Cases | Duration |
|-------|------------|----------|
| Phase 1 | VLAN Creation/Deletion (TC_VLAN_CREATE_*, TC_VLAN_DELETE_*) | 2 hours |
| Phase 2 | Access Port Configuration (TC_VLAN_ACCESS_*) | 3 hours |
| Phase 3 | Trunk Port Configuration (TC_VLAN_TRUNK_*) | 3 hours |
| Phase 4 | Mixed Port Configuration (TC_VLAN_MIXED_*) | 2 hours |
| Phase 5 | Packet Forwarding (TC_VLAN_FORWARD_*) | 4 hours |
| Phase 6 | Tagging/Untagging (TC_VLAN_TAG_*) | 3 hours |
| Phase 7 | Configuration Persistence (TC_VLAN_PERSIST_*) | 2 hours |
| Phase 8 | Edge Cases (TC_VLAN_EDGE_*) | 3 hours |
| Phase 9 | Error Handling (TC_VLAN_ERROR_*) | 2 hours |
| Phase 10 | Performance Tests (TC_VLAN_PERF_*) | 3 hours |
| Phase 11 | Scaling Tests (TC_VLAN_SCALE_*) | 8 hours |
| **Total** | | **35 hours** |

## 11. Test Deliverables

- Test execution results for each test case
- Configuration dumps from `show running-config`
- Scapy packet captures and analysis
- Defect reports for any failures
- Test summary report with pass/fail statistics
- Performance metrics and statistics
- **Scaling test specific deliverables:**
  - Maximum VLAN capacity report
  - CPU and memory usage graphs under various load conditions
  - Packet forwarding throughput and latency measurements
  - Configuration operation timing benchmarks
  - Long-duration stability test logs (24-hour test)
  - Resource utilization trends during scaling tests
  - MAC address table scalability metrics

## 12. Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hardware failure during testing | High | Use redundant equipment; regular backups |
| SONiC-VS instability | Medium | Use stable SONiC-VS version; quick restart procedures |
| Scapy packet timing issues | Low | Implement packet delays; use reliable packet verification |
| Configuration conflicts | Medium | Clear all configs before each test; use isolated test VLANs |
| System resource exhaustion during scale tests | High | Monitor resources closely; implement test checkpoints; use automation for rapid recovery |
| Long-duration test interruption (24hr test) | Medium | Implement test resumption capability; continuous logging |
| Memory leaks during extended testing | Medium | Regular memory monitoring; baseline measurements; system restart between major test phases |
| Performance degradation under scale | Medium | Establish performance baselines; incremental load testing; test rollback procedures |

## 13. Dependencies

- SONiC system must be operational and accessible
- Scapy must be installed and configured on SONiC-VS test system
- Network connectivity between DUT and test ports must be established
- Proper permissions for VLAN configuration and packet capture
- **For scaling tests specifically:**
  - Automation scripts for bulk VLAN creation/deletion
  - System monitoring tools for CPU, memory, and performance metrics
  - Sufficient system resources (RAM, storage) for maximum VLAN configurations
  - Time allocation for long-duration tests (24+ hours)
  - Data collection and graphing tools for performance analysis

## 14. References

- SONiC VLAN Configuration Guide
- IEEE 802.1Q VLAN Tagging Standard
- Scapy Documentation
- SONiC CLI Command Reference

## 15. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-04 | Test Team | Initial test plan creation |

---

**Document Status**: Draft
**Last Updated**: 2026-03-04
