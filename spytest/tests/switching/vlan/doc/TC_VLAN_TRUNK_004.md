TC_VLAN_TRUNK_004: Add/Remove VLANs from Trunk
Objective: Verify dynamic VLAN addition and removal on a trunk interface.
Expected Result: VLANs can be seamlessly added or removed from a trunk port dynamically, with the show running-configuration and show Vlan tables reflecting the correct state immediately.

1. Pre-Test Cleanup and Initialization
Clear any existing state on the test interface and create the required VLAN.

Bash
sonic# configure terminal
! Ensure clean state (Ignore errors if VLANs do not exist)
sonic(config)# no vlan 10
sonic(config)# no vlan 20

! Create target VLAN
sonic(config)# vlan 10

! Reset the target trunk interface
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no switchport trunk allowed Vlan 10
sonic(config-if-Ethernet8)# no switchport trunk allowed Vlan 20
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# no shutdown
sonic(config-if-Ethernet8)# end
Initial State Check:

Bash
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10     Down                            Enable      No
2. Dynamic VLAN Addition
Add VLAN 10 to Ethernet 8 as a tagged member.

Bash
sonic# configure terminal
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# switchport trunk allowed Vlan 10
sonic(config-if-Ethernet8)# end
Verification (Addition)
Check both the VLAN database and the running configuration to confirm the ASIC applied the trunk logic.

Bash
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10     Up          T  Ethernet8        Enable      No

sonic# show running-configuration interface Ethernet 8
!
interface Ethernet8
 mtu 9100
 speed auto
 switchport trunk allowed Vlan 10
3. Dynamic VLAN Removal
Remove VLAN 10 from the trunk port on the fly.

Bash
sonic# configure terminal
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no switchport trunk allowed Vlan 10
sonic(config-if-Ethernet8)# end
Verification (Removal)
Confirm the port has been stripped from the VLAN database and the interface configuration is clean.

Bash
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10     Down                            Enable      No

sonic# show running-configuration interface Ethernet 8
!
interface Ethernet8
 mtu 9100
 speed auto