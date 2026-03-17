# TC_VLAN_ACCESS_004: Change Access Port VLAN Membership

## Objective
Verify that access port VLAN assignment can be successfully changed and that configuration changes are properly reflected in system status and configuration files.

---

## Test Scenario Overview

| Aspect | Details |
|--------|---------|
| **Test Case ID** | TC_VLAN_ACCESS_004 |
| **Objective** | Change access port VLAN membership |
| **Test Interface** | Ethernet12 (Port1) |
| **Source VLAN** | VLAN 10 |
| **Target VLAN** | VLAN 20 |
| **Port Mode** | Access (Untagged) |

---

## Detailed Test Steps

### Step 1: Create VLANs 10 and 20

```bash
admin@sonic:~$ sonic-cli
sonic# configure
sonic(config)# vlan 10
sonic(config-vlan)# exit
sonic(config)# vlan 20
sonic(config-vlan)# exit
sonic(config)#
```

**Verification** - Check VLAN creation:
```bash
sonic# show vlan
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10    Down                            Enable      No
Vlan20    Down                            Enable      No
sonic#
```

**Expected Result**: Both VLAN 10 and VLAN 20 appear in the output with status.

---

### Step 2: Configure Port Ethernet12 as Untagged Member of VLAN 10

```bash
sonic(config)# interface Ethernet12
sonic(config-if-Ethernet12)# switchport mode access
sonic(config-if-Ethernet12)# switchport access vlan 10
sonic(config-if-Ethernet12)# exit
sonic(config)#
```

---

### Step 3: Verify Port Ethernet12 in VLAN 10

#### 3a. Check VLAN membership using `show vlan`:

```bash
sonic# show vlan
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10    Up          A  Ethernet12       Enable      No
Vlan20    Down                            Enable      No
sonic#
```

**Expected Result**: 
- VLAN10 shows "Up" status
- Ethernet12 appears under VLAN10 with "A" (Access/Untagged) designation
- VLAN20 remains "Down" with no ports

#### 3b. Verify running configuration:

```bash
sonic# show running-configuration | no-more
```

**Expected configuration output (relevant sections)**:

```
vlan 10
!
vlan 20
!
interface Ethernet12
 switchport mode access
 switchport access vlan 10
!
```

**Expected Result**: Running configuration shows:
- Both VLANs 10 and 20 are configured
- Interface Ethernet12 is set to access mode
- Interface Ethernet12 is assigned to VLAN 10
- No IP address on Ethernet12

---

### Step 4: Change Port Ethernet12 to Untagged Member of VLAN 20

```bash
sonic(config)# interface Ethernet12
sonic(config-if-Ethernet12)# switchport access vlan 20
sonic(config-if-Ethernet12)# exit
sonic(config)#
```

---

### Step 5: Verify Port Ethernet12 in VLAN 20

#### 5a. Check VLAN membership using `show vlan`:

```bash
sonic# show vlan
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10    Down                            Enable      No
Vlan20    Up          A  Ethernet12       Enable      No
sonic#
```

**Expected Result**: 
- VLAN10 shows "Down" status with no ports
- VLAN20 shows "Up" status
- Ethernet12 now appears under VLAN20 with "A" (Access/Untagged) designation

#### 5b. Verify updated running configuration:

```bash
sonic# show running-configuration | no-more
```

**Expected configuration output (relevant sections)**:

```
vlan 10
!
vlan 20
!
interface Ethernet12
 switchport mode access
 switchport access vlan 20
!
```

**Expected Result**: Running configuration shows:
- Both VLANs 10 and 20 are still configured
- Interface Ethernet12 remains in access mode
- Interface Ethernet12 is now assigned to VLAN 20 (changed from VLAN 10)

---

## Complete Test Execution Flow

```bash
admin@sonic:~$ sonic-cli

# Enter configuration mode
sonic# configure
sonic(config)# 

# Step 1: Create VLANs
sonic(config)# vlan 10
sonic(config-vlan)# exit
sonic(config)# vlan 20
sonic(config-vlan)# exit

# Step 2: Configure Ethernet12 as access port in VLAN 10
sonic(config)# interface Ethernet12
sonic(config-if-Ethernet12)# switchport mode access
sonic(config-if-Ethernet12)# switchport access vlan 10
sonic(config-if-Ethernet12)# exit
sonic(config)# exit

# Step 3: Verify initial configuration
sonic# show vlan
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10    Up          A  Ethernet12       Enable      No
Vlan20    Down                            Enable      No
sonic#

sonic# show running-configuration | no-more
# Review configuration to confirm Ethernet12 in VLAN 10

# Step 4: Change VLAN membership
sonic# configure
sonic(config)# interface Ethernet12
sonic(config-if-Ethernet12)# switchport access vlan 20
sonic(config-if-Ethernet12)# exit
sonic(config)# exit

# Step 5: Verify changed configuration
sonic# show vlan
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10    Down                            Enable      No
Vlan20    Up          A  Ethernet12       Enable      No
sonic#

sonic# show running-configuration | no-more
# Review configuration to confirm Ethernet12 in VLAN 20

sonic# exit
admin@sonic:~$
```

---

## Expected Results Summary

| Checkpoint | Criteria | Status |
|-----------|----------|--------|
| VLAN 10 Created | VLAN 10 appears in `show vlan` output | ? Pass |
| VLAN 20 Created | VLAN 20 appears in `show vlan` output | ? Pass |
| Eth12 in VLAN 10 | Ethernet12 shows "A" under VLAN10 | ? Pass |
| Config shows VLAN 10 | `show running-config` shows `switchport access vlan 10` for Eth12 | ? Pass |
| Eth12 moved to VLAN 20 | Ethernet12 shows "A" under VLAN20, VLAN10 shows Down | ? Pass |
| Config shows VLAN 20 | `show running-config` shows `switchport access vlan 20` for Eth12 | ? Pass |

---

## Key CLI Commands Reference

| Command | Purpose |
|---------|---------|
| `sonic-cli` | Enter SONiC CLI mode |
| `configure` | Enter configuration mode |
| `vlan <id>` | Create or enter VLAN configuration |
| `interface Ethernet<x>` | Enter interface configuration mode |
| `switchport mode access` | Set port to access mode |
| `switchport access vlan <id>` | Assign access port to VLAN |
| `exit` | Exit current configuration mode |
| `show vlan` | Display VLAN membership and status |
| `show running-configuration` | Display active configuration |
| `no-more` | Disable pagination in output |

---

## Notes

- **Access Port Mode**: An access port carries untagged traffic for a single VLAN only
- **Status Transitions**: VLANs transition from "Down" to "Up" when ports are assigned
- **Atomic Changes**: VLAN membership changes take effect immediately
- **Configuration Persistence**: Changes are reflected in running configuration and should be saved with `write memory` if persistence is required

---

## Test Case Result

**Overall Status**: [SELECT: PASS / FAIL]

**Tester Name**: ___________________

**Date**: ___________________

**Notes/Issues**: 

---

## Troubleshooting

If test fails, verify:

1. **Port does not change VLAN**:
   - Confirm port is in access mode: `show running-config interface Ethernet12`
   - Check for port-channel membership that might override configuration
   
2. **VLAN status remains Down after port assignment**:
   - Verify port is physically connected and not shutdown
   - Check for interface errors: `show interface Ethernet12`

3. **Configuration not persisting**:
   - Run `write memory` after making changes
   - Verify with `show startup-configuration`

