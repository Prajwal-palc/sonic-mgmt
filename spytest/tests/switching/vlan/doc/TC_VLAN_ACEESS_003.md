Test Execution Report: TC_VLAN_ACCESS_003
Test Case ID: TC_VLAN_ACCESS_003

Objective: Verify Layer 2 communication between multiple access ports assigned to the same VLAN using both interface counters and packet capture (tcpdump) verification.

Expected Result: Unicast traffic injected into one access port correctly switches and egresses out of the other access port in the same VLAN.

1. Test Topology
Device Under Test (DUT): * Ethernet 8: Configured as Access Port in VLAN 10 (Ingress Port).

Ethernet 12: Configured as Access Port in VLAN 10 (Egress Port).

External Traffic Generator: Connected to both Ethernet 8 and Ethernet 12 on the DUT.

2. DUT Configuration Procedure
Configure both Ethernet 8 and Ethernet 12 into VLAN 10 as untagged access ports.

Plaintext
admin@sonic:~$ sonic-cli
sonic# configure terminal
sonic(config)# vlan 10

! Configure Ingress Port
sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# no switchport access Vlan
sonic(config-if-Ethernet8)# no switchport trunk allowed Vlan
sonic(config-if-Ethernet8)# switchport access Vlan 10
sonic(config-if-Ethernet8)# no shutdown
sonic(config-if-Ethernet8)# exit

! Configure Egress Port
sonic(config)# interface Ethernet 12
sonic(config-if-Ethernet12)# no ip address
sonic(config-if-Ethernet12)# no switchport access Vlan
sonic(config-if-Ethernet12)# no switchport trunk allowed Vlan
sonic(config-if-Ethernet12)# switchport access Vlan 10
sonic(config-if-Ethernet12)# end
Verify VLAN Status:

Plaintext
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10    Up          A  Ethernet8        Enable      No
                      A  Ethernet12                   No
3. Pre-Test Preparation
Step 1: Dynamically Retrieve the Destination MAC Address
To perform a targeted unicast test, fetch the physical MAC address of the egress interface (Ethernet 12).

Plaintext
sonic# show interface Ethernet <mac>
Ethernet12 is up, line protocol is up, reason unknown
Hardware is Eth, address is <mac>
...
Target Destination MAC is noted as <mac>.

Step 2: Clear Interface Counters
Reset the hardware counters to zero to establish a clean baseline for traffic measurement.

Plaintext
sonic# clear interface counters
Step 3: Start tcpdump on the Egress Port
Open a bash shell on the DUT (or the receiving side of the traffic generator) and start listening on Ethernet <name>. Apply a strict filter to capture only packets destined for Ethernet <name>'s MAC address.

Plaintext
admin@sonic:~$ sudo tcpdump -i Ethernet<name> -e ether dst <mac>
tcpdump: verbose output suppressed, use -v[v]... for full protocol decode
listening on Ethernet<name>, link-type EN10MB (Ethernet), snapshot length 262144 bytes
4. Traffic Injection
Using the external traffic generator tool, inject pure untagged Layer 2 traffic into Ethernet 8.

Ingress Port: Ethernet 

Traffic Type: Layer 2 Untagged Ethernet Frames

Destination MAC: mac_address (The exact MAC of Ethernet fetched in Step 1)

Packet Count: 10 Packets

5. Verification & Results
Step 1: Verify Ingress Counters (Ethernet )
Confirm that the switch received the injected traffic on the source port.

Plaintext
sonic# show interface counters Ethernet 
Observation: The RX_OK counter for Ethernet  increments by exactly 10 packets.

Step 2: Verify Egress Counters (Ethernet )
Confirm that the switch successfully switched the unicast traffic at Layer 2 and forwarded it out the correct member port.

Plaintext
sonic# show interface counters Ethernet 
Observation: The TX_OK counter for Ethernet  increments by 10 packets, confirming intra-VLAN forwarding worked.

Step 3: Verify Packet Arrival via tcpdump
Stop the tcpdump process on Ethernet (using Ctrl+C) to check the final capture statistics.

Plaintext
^C
10 packets captured
10 packets received by filter
0 packets dropped by kernel
Observation: tcpdump captured exactly 10 frames matching the destination MAC address of Ethernet 12. This provides absolute proof that the data-plane frames were successfully switched within VLAN 10 and arrived intact.

Test Result: PASS. Ports assigned to the same VLAN successfully communicate. Traffic addressed to a specific port's MAC within the VLAN is accurately forwarded and validated by both hardware counters and software packet capture.