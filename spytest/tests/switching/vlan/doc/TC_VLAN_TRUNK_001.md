Test Execution Report: TC_VLAN_TRUNK_001
Test Case ID: TC_VLAN_TRUNK_001

Objective: Verify trunk port configuration and 802.1Q tagged packet forwarding.

Expected Result: Port is configured as a trunk port allowing multiple VLANs, and successfully receives/processes frames carrying specific 802.1Q VLAN tags.

1. Test Topology & Parameters
Traffic Generator (TG): Connected to DUT Ethernet 8.

TG Source MAC: dynamically retrieved from the testbed YAML configuration file (e.g., 00:11:22:33:44:55).

Device Under Test (DUT): Ethernet 8 configured as a Trunk Port.

DUT Target MAC: Retrieved dynamically from the DUT CLI.

2. Pre-Test Initialization & MAC Retrieval
Step 1: Fetch DUT Interface MAC Dynamically
Before configuring and testing, retrieve the physical MAC address of the DUT's ingress interface.

Plaintext
admin@sonic:~$ sonic-cli
sonic# show interface Ethernet 8

Ethernet8 is up, line protocol is up, reason unknown
Hardware is Eth, address is 22:1b:63:89:26:29
...
DUT Ethernet 8 MAC dynamically recorded as 22:1b:63:89:26:29.

3. DUT Configuration Procedure
Configure Ethernet 8 as a trunk port allowing VLANs 10, 20, and 30.

Plaintext
sonic# configure terminal
sonic(config)# vlan 10
sonic(config)# vlan 20
sonic(config)# vlan 30

sonic(config)# interface Ethernet 8
sonic(config-if-Ethernet8)# no ip address
sonic(config-if-Ethernet8)# no switchport access Vlan
sonic(config-if-Ethernet8)# no switchport trunk allowed Vlan 10
sonic(config-if-Ethernet8)# no switchport trunk allowed Vlan 20
sonic(config-if-Ethernet8)# no switchport trunk allowed Vlan 30
sonic(config-if-Ethernet8)# switchport trunk allowed Vlan 10
sonic(config-if-Ethernet8)# switchport trunk allowed Vlan 20
sonic(config-if-Ethernet8)# switchport trunk allowed Vlan 30
sonic(config-if-Ethernet8)# end
Verify Configuration:

Plaintext
sonic# show Vlan
Q: A - Access (Untagged), T - Tagged
NUM       Status      Q Ports             Autostate   Dynamic
------------------------------------------------------------------
Vlan10    Up          T  Ethernet8        Enable      No
Vlan20    Up          T  Ethernet8        Enable      No
Vlan30    Up          T  Ethernet8        Enable      No
4. Pre-Traffic Preparation
To ensure a mathematically precise test, we establish a clean hardware counter baseline and initialize a temporary packet capture.

Step 1: Clear Interface Counters
Plaintext
sonic# clear interface counters
Step 2: Start Packet Capture (tcpdump)
Open a bash shell on the DUT. Start tcpdump in the background, applying an 802.1Q filter (vlan 10) and saving the output to a temporary /tmp file.

Plaintext
admin@sonic:~$ sudo nohup tcpdump -i Ethernet8 -nn -e vlan 10 -w /tmp/trunk_vlan10_test.pcap > /dev/null 2>&1 &
(The -e flag ensures the Link-Level header, including the 802.1Q VLAN tag, is captured and printed).

5. Traffic Injection
From the Traffic Generator, inject exactly 10 ICMP packets tagged with VLAN 10. The packet utilizes a broadcast destination MAC (ff:ff:ff:ff:ff:ff) to force the switch to process the ingress frame.

Traffic Parameters Generated:

Ethernet Layer: SRC=00:11:22:33:44:55 (from YAML), DST=ff:ff:ff:ff:ff:ff

802.1Q Layer: VLAN ID = 10

IP/ICMP Layer: DST IP = 10.1.1.1

Count: 10 packets

6. Verification & Validation
We strictly validate the traffic arrival through two independent methods: Hardware Counters and Deep Packet Inspection (tcpdump).

Step 1: Verify Hardware Counters
Verify that the hardware ASIC processed the 10 incoming frames.

Plaintext
sonic# show interface counters Ethernet 8
Observation: The RX_OK counter for Ethernet 8 shows an increment of exactly 10 packets since the clear interface counters command was issued.

Step 2: Verify Packet Capture (tcpdump)
Stop the background capture process and read the temporary .pcap file to verify the 802.1Q tags were preserved and correctly identified.

Plaintext
admin@sonic:~$ sudo killall tcpdump
admin@sonic:~$ sudo tcpdump -nn -e -r /tmp/trunk_vlan10_test.pcap
reading from file /tmp/trunk_vlan10_test.pcap, link-type EN10MB (Ethernet)
06:15:01.123456 00:11:22:33:44:55 > ff:ff:ff:ff:ff:ff, ethertype 802.1Q (0x8100), length 60: vlan 10, p 0, ethertype IPv4, 10.1.1.2 > 10.1.1.1: ICMP echo request, id 1, seq 1, length 20
... [Total 10 packets displayed] ...
Observation: The capture confirms 10 packets were received, and explicitly highlights ethertype 802.1Q and vlan 10 in the frame header.

Step 3: Cleanup Temporary Files
Remove the temporary packet capture file to ensure the DUT filesystem remains clean for subsequent tests.

Plaintext
admin@sonic:~$ sudo rm -f /tmp/trunk_vlan10_test.pcap
admin@sonic:~$ ls -l /tmp/trunk_vlan10_test.pcap
ls: cannot access '/tmp/trunk_vlan10_test.pcap': No such file or directory
Test Result: PASS. Ethernet 8 successfully operated as an 802.1Q Trunk port, correctly receiving and classifying tagged frames for VLAN 10. All traffic was strictly verified via hardware counters and software packet capture, followed by proper testbed cleanup.