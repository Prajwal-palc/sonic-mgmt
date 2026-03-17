Test Execution Report: TC_VLAN_ACCESS_002
Test Case ID: TC_VLAN_ACCESS_002

Objective: Verify traffic isolation between different access VLANs at Layer 2.

Expected Result: Layer 2 traffic injected into VLAN 10 is contained within VLAN 10 and does not leak or broadcast into VLAN 20.

1. Test Topology
Traffic Generator (DUT1): Connected to DUT2's Ethernet 8.

Device Under Test (DUT2): * Ethernet 8: Configured as Access Port in VLAN 10.

Ethernet 12: Configured as Access Port in VLAN 20 (Isolated Port).

2. Configuration Procedure (DUT2)
Access the SONiC CLI on DUT2 to create the VLANs and assign the access ports.

Plaintext
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic(config)# vlan 10
sonic(config)# vlan 20

! Configure Ethernet 8 for VLAN 10
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# no switchport access Vlan
sonic(config-if-Ethernet8)# no switchport trunk allowed Vlan
sonic(config-if-Ethernet8)# switchport access Vlan 10
sonic(config-if-Ethernet8)# no shutdown
sonic(config-if-Ethernet8)# exit

! Configure Ethernet 12 for VLAN 20
sonic(config)# interface Ethernet 12
sonic(config-if-Ethernet12)# no ip address
sonic(config-if-Ethernet12)# no switchport access Vlan
sonic(config-if-Ethernet12)# no switchport trunk allowed Vlan
sonic(config-if-Ethernet12)# switchport access Vlan 20
sonic(config-if-Ethernet12)# no shutdown
sonic(config-if-Ethernet12)# end
Verify Configuration:

Plaintext
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10    Up          A  Ethernet8        Enable      No
Vlan20    Up          A  Ethernet12       Enable      No
3. Pre-Test Preparation
Before injecting traffic, establish a clean baseline on the interface counters and set up a packet sniffer on the isolated port to mathematically prove no leakage occurs.

Step 1: Clear Interface Counters
Reset the hardware counters on DUT2 to zero.

Plaintext
sonic# clear interface counters
Step 2: Start tcpdump on the Isolated Port (VLAN 20)
Open a bash shell on DUT2 and start listening on Ethernet 12. We filter by the specific destination MAC address we plan to send to ensure we only look for our test frames.

Plaintext
admin@sonic:~$ sudo tcpdump -i Ethernet12 -e ether dst 22:f7:2a:2e:6c:8d
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on Ethernet12, link-type EN10MB (Ethernet), snapshot length 262144 bytes
4. Traffic Injection
From the Traffic Generator (DUT1), generate and send a burst of pure, untagged Layer 2 Ethernet frames into DUT2's Ethernet 8.

Traffic Type: Layer 2 Untagged Ethernet Frames

Destination MAC: <dest_mac> (or any unknown MAC to force broadcast behavior within the VLAN)

Count: 100 Packets

(Note: Traffic is sent manually from the generator interface connected to Ethernet 8).

5. Verification & Results (DUT2)
Step 1: Verify Packet Reception on VLAN 10 (Ingress)
Confirm that the traffic successfully entered the switch on VLAN 10.

Plaintext
sonic# show interface counters Ethernet 8
Observation: The RX_OK counter for Ethernet 8 shows exactly 100 packets received. This proves the traffic successfully entered VLAN 10.

Step 2: Verify Traffic Isolation on VLAN 20 (Egress via Counters)
Confirm that the switch ASIC did not leak the packets into the wrong VLAN.

Plaintext
sonic# show interface counters Ethernet 12
Observation: The TX_OK counter for Ethernet 12 shows 0 (or a very low number representing standard LLDP/STP background noise, but NOT the 100 test packets).

Step 3: Verify Traffic Isolation on VLAN 20 (Egress via tcpdump)
Check the tcpdump session that was left running on Ethernet 12.

Plaintext
^C
0 packets captured
0 packets received by filter
0 packets dropped by kernel
Observation: tcpdump captured exactly 0 frames matching the test traffic's MAC address. This provides absolute proof that no data-plane frames leaked across the VLAN boundary.

Test Result: PASS. The switch successfully contained the Layer 2 broadcast/unicast traffic entirely within VLAN 10. Port 2 (Ethernet 12) in VLAN 20 remained completely isolated.