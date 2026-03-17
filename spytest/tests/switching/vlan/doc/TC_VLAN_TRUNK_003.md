TC_VLAN_TRUNK_003: Trunk Port VLAN Filtering Validation
Objective: Verify that a trunk port strictly filters and drops ingress traffic tagged with a VLAN ID that is not explicitly allowed on the trunk interface.

In this scenario, we will send VLAN 30 traffic into a trunk port that only allows VLAN 10 and 20. The switch ASIC should drop the packet at the ingress port, ensuring it never reaches the VLAN 30 access port.

1. Pre-Test Cleanup
Ensure the switch is in a clean state by removing legacy configurations.

Bash
sonic# configure terminal
sonic(config)# no vlan 10
sonic(config)# no vlan 20
sonic(config)# no vlan 30
sonic(config)# exit
2. Device Configuration
Configure the Trunk port to allow only VLANs 10 and 20, and configure an Access port for VLAN 30 to serve as our egress monitor.

Bash
sonic# configure terminal

! Create VLANs
sonic(config)# vlan 10
sonic(config)# vlan 20
sonic(config)# vlan 30

! Configure Trunk Port (Allowed: 10, 20 only)
sonic(config)# interface Ethernet 12
sonic(config-if-Ethernet12)# no ip address
sonic(config-if-Ethernet12)# no switchport access Vlan
sonic(config-if-Ethernet12)# switchport trunk allowed Vlan 10
sonic(config-if-Ethernet12)# switchport trunk allowed Vlan 20
sonic(config-if-Ethernet12)# no shutdown
sonic(config-if-Ethernet12)# exit

! Configure Access Port (VLAN 30 Egress Monitor)
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# switchport access Vlan 30
sonic(config-if-Ethernet8)# no shutdown
sonic(config-if-Ethernet8)# end
State Verification:
Run show Vlan to confirm the topology.

Vlan10 & Vlan20: Ethernet12 is marked T (Tagged).

Vlan30: Ethernet12 is absent, and Ethernet8 is marked A (Untagged).

3. Traffic Injection Strategy
Using your Scapy traffic generator, construct and inject a packet tagged with VLAN 30 into Ethernet12.

Python
from scapy.all import Ether, Dot1Q, IP, ICMP, sendp

# Construct ICMP Packet Tagged with Unauthorized VLAN 30
pkt = (
    Ether(src="22:44:64:9a:34:bb", dst="ff:ff:ff:ff:ff:ff") /
    Dot1Q(vlan=30) /
    IP(src="192.168.30.10", dst="192.168.30.20") /
    ICMP(type=8, code=0)
)

# Inject 20 packets into the Trunk port
sendp(pkt, iface="Ethernet12", count=20, verbose=False)
4. Verification & Validation Protocol
Step A: Verify Ingress on Trunk (Ethernet12)
Confirm the traffic generator is successfully pushing the unauthorized packets onto the wire and reaching the switch.

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet12 icmp -n
Expected Result: 20 packets captured. The packets are arriving at the switch.

Step B: Verify VLAN 30 Drop (Ethernet8)
Check the VLAN 30 access port. Since VLAN 30 is not allowed on Ethernet12, the ASIC must drop the traffic before it crosses the fabric.

Bash
admin@sonic:~$ sudo tcpdump -i Ethernet8 icmp -n
Expected Result: 0 packets captured. Complete isolation is confirmed.

Step C: Verify Hardware Counters
To double-check the ASIC logic without relying solely on tcpdump, verify the hardware egress counters on the access port.

Bash
sonic# clear interface counters
sonic# show interface counters Ethernet 8
Expected Result: The TX_OK (Transmit) column for Ethernet8 must remain exactly 0.