Test Execution Report: TC_VLAN_ACCESS_001
Test Case ID: TC_VLAN_ACCESS_001
Objective: Verify access port configuration and untagged packet handling.
Expected Result: Port is configured as an access port in VLAN 10 and successfully receives/processes untagged frames.

1. Test Topology
Traffic Generator (DUT1): Ethernet8 (MAC: )

show interface Ethernet <name> for here take mac dyanmically for source and for vlan "show interface Vlan <id>"

Device Under Test (DUT2): Ethernet8 (VLAN 10 MAC: )

2. Configuration Steps (DUT2)
Step 1: Create VLAN 10 and Configure Access Port
Access the SONiC CLI on DUT2 to create the VLAN and assign Ethernet8 as an untagged member.

Plaintext
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic(config)# vlan 10
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# no switchport access Vlan
sonic(config-if-Ethernet8)# no switchport trunk allowed Vlan 10
sonic(config-if-Ethernet8)# switchport access Vlan 10
sonic(config-if-Ethernet8)# end
Step 2: Verify Port Configuration
Verify the VLAN operational status and the running configuration.

Plaintext
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10    Up          A  Ethernet8        Enable      No

sonic# show running-config interface Ethernet 8
!
interface Ethernet8
 switchport access Vlan 10
3. Pre-Traffic Preparation
Step 3: Clear Interface Counters
Before generating traffic, clear the hardware counters on the Device Under Test to establish a zero baseline for accurate measurement.

Plaintext
sonic# clear interface counters
sonic# show interface counters Ethernet 8
(Verify that the RX and TX packet counters display 0 or near 0 for the current polling interval).

4. Traffic Execution & Verification
Step 4: Start Packet Capture on DUT2
Start tcpdump on DUT2's Ethernet8 interface, filtering for the specific destination MAC address of the VLAN 10 SVI to verify packet arrival.

Plaintext
admin@sonic:~$ sudo tcpdump -i Ethernet8 -e ether dst 22:f7:2a:2e:6c:8d
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on Ethernet8, link-type EN10MB (Ethernet), snapshot length 262144 bytes
Step 5: Send Untagged Packets from DUT1
Execute the Scapy traffic generation script on DUT1 to send exactly 10 untagged Ethernet frames.

Scapy Script (sender.py):

Python
from scapy.all import *

iface = "Ethernet8"
src_mac = "mac_address"
dst_mac = "mac_address"
payload = "VLAN_ACCESS_TEST_PACKET"

packet = Ether(src=src_mac, dst=dst_mac) / Raw(load=payload)
sendp(packet, iface=iface, count=10, inter=1)
print("Packets sent successfully")
Step 6: Verify Packet Reception (DUT2)
1. Tcpdump Verification:
The tcpdump session on DUT2 successfully captures the 10 incoming frames, confirming the untagged payload is received by the port mapped to VLAN 10.

Plaintext
05:59:00.265564 22:35:f2:23:c4:4d (oui Unknown) > 22:f7:2a:2e:6c:8d (oui Unknown), ethertype Loopback (0x9000), length 37: Loopback, skipCount 19542 (bogus) (invalid)
... [8 packets omitted for brevity] ...
05:59:09.279507 22:35:f2:23:c4:4d (oui Unknown) > 22:f7:2a:2e:6c:8d (oui Unknown), ethertype Loopback (0x9000), length 37: Loopback, skipCount 19542 (bogus) (invalid)
^C
10 packets captured
10 packets received by filter
0 packets dropped by kernel
2. Counter Verification:
Validate the hardware counters reflect the injected traffic.

Plaintext
sonic# show interface counters Ethernet 8
(Verify the RX_OK counter has incremented by exactly 10 packets since the clear interface counters command was issued).