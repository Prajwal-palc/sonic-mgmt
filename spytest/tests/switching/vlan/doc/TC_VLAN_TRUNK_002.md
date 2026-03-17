TC_VLAN_TRUNK_002: Trunk Port Multiple VLAN Traffic Validation
Objective: Verify that a single 802.1Q trunk port correctly multiplexes and isolates traffic for multiple VLANs, forwarding the payload exclusively to the corresponding untagged access ports.

1. Pre-Test Cleanup
Ensure a clean state on the device to avoid false positives from previous configurations.

Bash
sonic# configure terminal
sonic(config)# no vlan 10
sonic(config)# no vlan 20
sonic(config)# exit
2. Device Configuration
Set up the Trunk port to accept multiple tagged VLANs, and assign the individual access ports to their respective collision domains.

Bash
sonic# configure terminal
! Create VLANs
sonic(config)# vlan 10
sonic(config)# vlan 20

! Configure Trunk Port (Ingress)
sonic(config)# interface Ethernet 12
sonic(config-if-Ethernet12)# no ip address
sonic(config-if-Ethernet12)# switchport trunk allowed Vlan 10
sonic(config-if-Ethernet12)# switchport trunk allowed Vlan 20
sonic(config-if-Ethernet12)# no shutdown
sonic(config-if-Ethernet12)# exit

! Configure Access Port for VLAN 10 (Egress A)
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# switchport access Vlan 10
sonic(config-if-Ethernet8)# no shutdown
sonic(config-if-Ethernet8)# exit

! Configure Access Port for VLAN 20 (Egress B)
sonic(config)# interface Ethernet 4
sonic(config-if-Ethernet4)# no ip address
sonic(config-if-Ethernet4)# switchport access Vlan 20
sonic(config-if-Ethernet4)# no shutdown
sonic(config-if-Ethernet4)# end
State Verification: Run show Vlan to confirm Ethernet12 is marked with T (Tagged) for both VLAN 10 and 20, while Ethernet8 and Ethernet4 are marked with A (Untagged) in their respective VLANs.

3. Traffic Injection Strategy
To validate the ASIC's VLAN steering, inject ICMP Echo Requests wrapped in 802.1Q tags directly into the trunk port.

Note: Use a generalized packet crafter to simulate this behavior from the traffic generator.

Python
# Traffic Generator Configuration (Conceptual Scapy Implementation)
from scapy.all import Ether, Dot1Q, IP, ICMP, sendp

def generate_tagged_icmp(target_iface, target_vlan):
    """
    Constructs and sends a batch of ICMP packets mapped to a specific VLAN.
    """
    frame = (
        Ether(src="00:11:22:33:44:55", dst="ff:ff:ff:ff:ff:ff") /
        Dot1Q(vlan=target_vlan) /
        ICMP(type=8, code=0)
    )
    
    # Fire 20 ICMP packets into the trunk link
    sendp(frame, iface=target_iface, count=20, verbose=False)

# Execute for VLAN 10
generate_tagged_icmp(target_iface="Ethernet12", target_vlan=10)

# Execute for VLAN 20
generate_tagged_icmp(target_iface="Ethernet12", target_vlan=20)
4. Verification & Validation Protocol
Use tcpdump to monitor the data plane in real-time. The test passes if the ICMP traffic strictly follows its tagged VLAN boundary.

Step A: Verify Ingress on Trunk (Ethernet12)
Start a capture on the trunk port to confirm the tagged ICMP packets are physically hitting the switch fabric.

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet12 icmp -n
Expected: You should capture the ingress ICMP echo requests arriving on the interface.

Step B: Validate VLAN 10 Stripping and Forwarding (Ethernet8)
While sending the VLAN 10 tagged packets, monitor the access port mapped to VLAN 10.

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet8 icmp -n
Expected: 20 packets captured. The ASIC successfully identified the vlan=10 tag, stripped it, and forwarded the raw IP/ICMP payload out of Ethernet8.

Step C: Validate VLAN Isolation (Ethernet4)
While sending the VLAN 10 tagged packets, monitor the access port mapped to VLAN 20.

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet4 icmp -n
Expected: 0 packets captured. The ASIC securely isolated the collision domains, preventing VLAN 10 traffic from leaking into the VLAN 20 port.

Step D: Validate VLAN 20 Stripping and Forwarding (Ethernet4)
Repeat the traffic generation, this time injecting VLAN 20 tagged ICMP packets, and monitor Ethernet4.

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet4 icmp -n
Expected: 20 packets captured. The trunk dynamically recognized the new tag and routed the traffic to the secondary access port.