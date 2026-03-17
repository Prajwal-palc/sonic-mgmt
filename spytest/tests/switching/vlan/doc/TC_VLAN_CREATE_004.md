Test Execution Report: VLAN Boundary and Deletion Operations
Test Case 1: TC_VLAN_CREATE_004
Test Case ID: TC_VLAN_CREATE_004

Objective: Verify the system rejects invalid VLAN IDs outside the standard 802.1Q boundary (1-4094).

Expected Result: The system explicitly rejects attempts to create VLAN 0 and VLAN 4095 with appropriate error messages.

1. Execution Procedure & Output
Access the SONiC CLI and attempt to instantiate VLANs outside the valid range.

Plaintext
admin@sonic:~$ sonic-cli
sonic# configure terminal

! Attempt to create upper-boundary invalid VLAN (4095)
sonic(config)# vlan 4095
ERROR: VLAN IDs must be in 1-4094 and start <= end

! Attempt to create lower-boundary invalid VLAN (0)
sonic(config)# vlan 0
ERROR: Invalid start VLAN '0'
sonic(config)# exit
2. Verification & Results
Observation (VLAN 4095): The CLI parser caught the out-of-bounds integer and returned a strict syntax error restricting IDs to the 1-4094 range.

Observation (VLAN 0): The CLI parser successfully rejected 0 as an invalid start VLAN.

Test Result: PASS. The switch firmware correctly validates input boundaries and prevents the creation of reserved/invalid 802.1Q VLAN identifiers.

Test Case 2: TC_VLAN_DELETE_002
Test Case ID: TC_VLAN_DELETE_002

Objective: Verify the system's protective behavior when an administrator attempts to delete a VLAN that currently holds active port members.

Expected Result: The system safely handles the deletion attempt, explicitly preventing the deletion and throwing an error advising the user to remove the member ports first to avoid traffic blackholing.

1. Execution Procedure & Output
Step 1: Create the VLAN and Assign a Port

Plaintext
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic(config)# vlan 100

! Assign Ethernet 8 to VLAN 100
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# no switchport access Vlan
sonic(config-if-Ethernet8)# no switchport trunk allowed Vlan 100
sonic(config-if-Ethernet8)# switchport access Vlan 100
sonic(config-if-Ethernet8)# no shutdown
sonic(config-if-Ethernet8)# end
Step 2: Verify Active Membership

Plaintext
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10    Down                            Enable      No
Vlan20    Down                            Enable      No
Vlan30    Down                            Enable      No
Vlan100   Up          A  Ethernet8        Enable      No
Step 3: Attempt to Delete the Active VLAN

Plaintext
sonic# configure terminal
sonic(config)# no vlan 100
Error: Cannot delete VLAN 100. VLAN has member ports configured. Remove all members configured.
2. Verification & Results
Observation: When the no vlan 100 command was issued, the system checked the VLAN database, identified that Ethernet8 was currently bound to it, and actively blocked the execution.

Test Result: PASS. The system gracefully aborted the unsafe deletion. The error message is highly descriptive, guiding the operator on the correct procedure (removing port bindings before deleting the Layer 2 broadcast domain).