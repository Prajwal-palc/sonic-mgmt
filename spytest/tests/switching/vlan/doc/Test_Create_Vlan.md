#### TC_VLAN_CREATE_001: Create Single VLAN
**Objective**: Verify single VLAN creation
**Steps**:
1. Create VLAN 10
2. Execute `show running-config` to verify VLAN 10 exists
3. Verify VLAN appears in VLAN database

**Expected Result**: VLAN 10 is created successfully and appears in configuration
sonic#
sonic# configure
sonic(config)# vlan 100
sonic(config)# exit
sonic# show v
version Vlan    vrrp
sonic# show Vlan 100
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan100   Down                            Enable      No
sonic# show running-configuration | grep Vlan100
interface Vlan100
sonic#
sonic# show Vlan count
sonic# show interface brief
sonic# show interface status | no-more




#### TC_VLAN_DELETE_001: Delete Single VLAN
**Objective**: Verify VLAN deletion
**Steps**:
1. Create VLAN 100
2. Verify VLAN 100 exists
3. Delete VLAN 100
4. Execute `show running-config` to verify VLAN 100 is removed

**Expected Result**: VLAN 100 is deleted successfully
sonic#
sonic# configure
sonic(config)# no vlan 100
sonic(config)# exit
sonic# show v
version Vlan    vrrp
sonic# show Vlan 100
VLAN Vlan100 not found
sonic# show running-configuration | grep Vlan100
sonic#
sonic# show Vlan count
sonic# show interface brief
sonic# show interface status | no-more

#### TC_VLAN_CREATE_003: Create VLAN with Valid Range
**Objective**: Verify VLAN creation with valid VLAN IDs (1-4094)
**Steps**:
1. Create VLAN 1 (default VLAN)
2. Create VLAN 4094 (maximum VLAN ID)
3. Verify both VLANs exist

**Expected Result**: VLANs with valid IDs are created successfully

sonic(config)# vlan 1-4094
sonic# show Vlan count
sonic# show interface brief
sonic# show interface status | no-more
sonic# show Vlan
sonic# show running-configuration | grep Vlan 1-4094

sonic(config)# no vlan 1-4094
sonic# show Vlan count
sonic# show interface brief
sonic# show interface status | no-more
sonic# show Vlan
sonic# show running-configuration | grep Vlan 1-4094