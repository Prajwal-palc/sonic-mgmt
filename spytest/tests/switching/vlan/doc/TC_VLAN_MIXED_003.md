TC_VLAN_MIXED_003: Native VLAN Behavior on Trunk Port
Objective: Verify that a Trunk port properly identifies and forwards untagged ingress traffic to its configured "Native" VLAN (also known as the Access VLAN on a hybrid port) and successfully isolates it from other allowed tagged VLANs.

1. Device Configuration
Configure Ethernet12 as a mixed port where VLAN 20 is the Native (Access) VLAN, and VLAN 10 is an allowed Trunk (Tagged) VLAN. We will configure Ethernet8 as a monitor for VLAN 20 and Ethernet4 as a monitor for VLAN 10.

Bash
sonic# configure terminal
! Create required VLANs
sonic(config)# vlan 10
sonic(config)# vlan 20

! Configure Ingress Mixed Port (Native: 20, Tagged: 10)
sonic(config)# interface Ethernet 12
sonic(config-if-Ethernet12)# no ip address
sonic(config-if-Ethernet12)# switchport access Vlan 20
sonic(config-if-Ethernet12)# switchport trunk allowed Vlan 10
sonic(config-if-Ethernet12)# no shutdown
sonic(config-if-Ethernet12)# exit

! Configure Native VLAN Monitor (Egress VLAN 20)
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# switchport access Vlan 20
sonic(config-if-Ethernet8)# no shutdown
sonic(config-if-Ethernet8)# exit

! Configure Tagged VLAN Monitor (Egress VLAN 10)
sonic(config)# interface Ethernet 4
sonic(config-if-Ethernet4)# no ip address
sonic(config-if-Ethernet4)# switchport trunk allowed Vlan 10
sonic(config-if-Ethernet4)# no shutdown
sonic(config-if-Ethernet4)# end
State Verification:

Bash
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM        Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10     Up          T  Ethernet4        Enable      No
                       T  Ethernet12                   No
Vlan20     Up          A  Ethernet8        Enable      No
                       A  Ethernet12                   No
Note: Ethernet12 correctly appears as A (Access/Native) in VLAN 20 and T (Tagged) in VLAN 10.

2. Traffic Injection (Scapy)
Inject untagged L2 broadcast frames into the mixed port (Ethernet12). We will use a custom payload and ethertype 0x0806 (ARP) as a recognizable signature.

Python
from scapy.all import Ether, Raw, sendp

# Construct an UNTAGGED broadcast frame
pkt = Ether(src="22:96:d0:c9:67:c8", dst="ff:ff:ff:ff:ff:ff", type=0x0806) / Raw(load="TEST_PKT")

# Send 10 packets into the mixed/trunk port
sendp(pkt, iface="Ethernet12", count=10)
3. Verification & Validation Protocol
Step A: Verify Ingress on Mixed Port (Ethernet12)
Confirm the untagged frames are arriving at the switch interface.

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet12 -e -nn
Expected Result: 10 packets captured.

Output Analysis: ... > ff:ff:ff:ff:ff:ff, ethertype ARP (0x0806), length 22:  [|arp]
The packets are successfully received without an 802.1Q tag.

Step B: Verify Native VLAN Forwarding (Ethernet8)
Since the ingress frame lacked a tag, the switch should assign it to the native VLAN (20) and flood it to all other VLAN 20 members. Monitor the VLAN 20 access port (Ethernet8).

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet8 -e -nn
Expected Result: 10 packets captured.

Output Analysis: ... > ff:ff:ff:ff:ff:ff, ethertype ARP (0x0806), length 22:  [|arp]
The packets successfully flooded to the native VLAN broadcast domain.

Step C: Verify Isolation from Tagged VLAN (Ethernet4)
Ensure the untagged traffic did not leak into the tagged VLAN (10). Monitor the VLAN 10 trunk port (Ethernet4).

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet4 -e -nn
Expected Result: 0 packets captured matching the injected traffic.

Output Analysis: You may see background noise (like ethertype LLDP), but you should not see the ethertype ARP (0x0806) packets originating from 22:96:d0:c9:67:c8. Complete isolation is confirmed.