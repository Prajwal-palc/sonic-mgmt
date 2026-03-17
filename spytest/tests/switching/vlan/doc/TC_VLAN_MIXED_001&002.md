TC_VLAN_MIXED_001: Mixed Port Configuration (Tagged + Untagged)
Objective: Verify that a single physical interface can simultaneously act as an untagged member (Access) for one VLAN and a tagged member (Trunk) for another. This is often referred to as a "Hybrid" port configuration.

1. Pre-Test Initialization
Ensure the switch is in a clean state with no existing VLANs to prevent configuration conflicts.

Bash
sonic# show Vlan
No VLANs configured
sonic# configure terminal
2. Device Configuration
Create the required VLANs and apply the mixed configuration to the target interface (Ethernet 8).

Step A: Create VLANs
Bash
sonic(config)# vlan 10
sonic(config)# vlan 20
Step B: Configure Untagged (Access) Membership
Assign the port as an access port for VLAN 10.

Bash
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# switchport access Vlan 10
Intermediate Verification:

Bash
sonic(config-if-Ethernet8)# do show Vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10     Up          A  Ethernet8        Enable      No
Vlan20     Down                            Enable      No
Step C: Configure Tagged (Trunk) Membership
While the port is already an access port for VLAN 10, add VLAN 20 as an allowed tagged VLAN.

Bash
sonic(config-if-Ethernet8)# switchport trunk allowed Vlan 20
sonic(config-if-Ethernet8)# end
3. Final Verification & Expected Results
Verify that the ASIC has successfully applied both configurations to the same port.

Bash
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10     Up          A  Ethernet8        Enable      No
Vlan20     Up          T  Ethernet8        Enable      No
Expected Result:
The table correctly displays Ethernet 8 with an A (Access/Untagged) status for VLAN 10, and a T (Trunk/Tagged) status for VLAN 20. This confirms the port will strip tags for VLAN 10 traffic and require/preserve 802.1Q tags for VLAN 20 traffic.

TC_VLAN_MIXED_002: Mixed Port Traffic Handling (Pure L2)
Objective: Verify the traffic handling capabilities of a mixed-mode (Hybrid) port using pure Layer 2 traffic (MAC addressing only). The port must accept untagged frames (assigning them to the native Access VLAN) and tagged frames (routing them to the allowed Trunk VLAN).

1. Topology & Pre-Requisites
To properly verify that the ASIC assigns or preserves the correct tags, we need an ingress mixed port and two egress monitor ports.

Ingress (Mixed Port): Ethernet4 (Access: VLAN 20, Trunk: VLAN 10)

Egress Monitor 1: Ethernet8 (Trunk: VLAN 20) -> Used to prove the switch assigned VLAN 20 to the untagged frame.

Egress Monitor 2: Ethernet12 (Trunk: VLAN 10) -> Used to prove the switch preserved the VLAN 10 tag.

Device Configuration
Bash
sonic# configure terminal
! Create VLANs
sonic(config)# vlan 10
sonic(config)# vlan 20

! Configure Ingress Mixed Port
sonic(config)# interface Ethernet 4
sonic(config-if-Ethernet4)# no ip address
sonic(config-if-Ethernet4)# switchport access Vlan 20
sonic(config-if-Ethernet4)# switchport trunk allowed Vlan 10
sonic(config-if-Ethernet4)# no shutdown
sonic(config-if-Ethernet4)# exit

! Configure Monitor Port for VLAN 20 Verification
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# switchport trunk allowed Vlan 20
sonic(config-if-Ethernet8)# no shutdown
sonic(config-if-Ethernet8)# exit

! Configure Monitor Port for VLAN 10 Verification
sonic(config)# interface Ethernet 12
sonic(config-if-Ethernet12)# no ip address
sonic(config-if-Ethernet12)# switchport trunk allowed Vlan 10
sonic(config-if-Ethernet12)# no shutdown
sonic(config-if-Ethernet12)# end
2. Traffic Injection (Scapy Pure L2)
Using the Traffic Generator connected to Ethernet4, send pure Layer 2 frames using the Broadcast MAC address (ff:ff:ff:ff:ff:ff) to force the switch to flood the frames to all other ports in the respective VLAN.

Python
from scapy.all import Ether, Dot1Q, Raw, sendp

target_iface = "Ethernet4"

# ---------------------------------------------------------
# Test A: Send UNTAGGED packet (Expected to map to VLAN 20)
# ---------------------------------------------------------
untagged_pkt = (
    Ether(src="mac", dst="ff:ff:ff:ff:ff:ff") /
    Raw(load="MIXED_PORT_UNTAGGED_PAYLOAD")
)
sendp(untagged_pkt, iface=target_iface, count=20, verbose=False)


# ---------------------------------------------------------
# Test B: Send TAGGED packet (Expected to map to VLAN 10)
# ---------------------------------------------------------
tagged_pkt = (
    Ether(src="mac", dst="ff:ff:ff:ff:ff:ff") /
    Dot1Q(vlan=10) /
    Raw(load="MIXED_PORT_TAGGED_PAYLOAD")
)
sendp(tagged_pkt, iface=target_iface, count=20, verbose=False)
3. Verification & Validation Protocol
Step A: Verify Untagged Ingress -> Tagged Egress (VLAN 20)
While sending the Untagged packet into Ethernet4, monitor the VLAN 20 trunk port (Ethernet8).

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet8 -e vlan 20
Expected Result: 20 packets captured.

Analysis: The tcpdump output will show the 802.1Q tag for VLAN 20. This proves the mixed port successfully received the untagged frame and internally assigned it to its Access VLAN (20) before forwarding it.

Step B: Verify Tagged Ingress -> Tagged Egress (VLAN 10)
While sending the VLAN 10 Tagged packet into Ethernet4, monitor the VLAN 10 trunk port (Ethernet12).

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet12 -e vlan 10
Expected Result: 20 packets captured.

Analysis: The tcpdump output will show the 802.1Q tag for VLAN 10. This proves the mixed port successfully accepted the explicitly tagged frame and forwarded it strictly within the allowed Trunk VLAN (10).

Step C: Negative Verification (Isolation Check)
To guarantee the mixed port isn't leaking traffic:

Run sudo tcpdump -i Ethernet12 while sending the Untagged packet. (Expected: 0 packets).

Run sudo tcpdump -i Ethernet8 while sending the VLAN 10 Tagged packet. (Expected: 0 packets).