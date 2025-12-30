# Test Cases - IPv4 Unnumbered Interface Across Topologies

## Test Case ID: TC_IPv4_Unnumbered_1.2.3

### Test Case Name
Validate IPv4 Unnumbered Interface Across Multiple Topologies

### Test Objective
Validate that IPv4 unnumbered interfaces function correctly across various network topologies including multiple interfaces sharing a single donor, point-to-point (P2P) connections, multi-hop scenarios, and Link Aggregation Groups (LAG). Verify that ARP/ND (Neighbor Discovery), routing, and forwarding operate correctly. Test includes configuring a single Loopback0 as donor for multiple physical interfaces, establishing P2P connectivity, configuring multi-hop routing paths, creating LAG interfaces with unnumbered configuration, verifying ARP resolution, confirming routing table population, testing packet forwarding, and ensuring all topologies maintain full reachability without issues.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_3node_unnumbered.yaml`
- **Topology**: 3 nodes (DUT1 + DUT2 + DUT3)
- **Device Under Test (DUT1)**: Primary router with multiple unnumbered interfaces
- **Neighbor Device (DUT2)**: Secondary router for P2P and multi-hop testing
- **Neighbor Device (DUT3)**: Tertiary router for multi-hop path verification
- **Test Type**: Topology validation (P2P, multi-hop, LAG, multiple interfaces)

### Topology Diagram

```
                    +------------------------+
                    |         DUT1           |
                    |                        |
                    |  Loopback0 (Donor)     |
                    |  IP: 10.10.10.1/32     |
                    |          |             |
                    |          | (shares to) |
                    |          ↓             |
                    |  Ethernet0             | ----P2P----> DUT2 Ethernet0
                    |  (unnumbered)          |              10.10.10.2/30
                    |                        |
                    |  Ethernet4             | ----P2P----> DUT3 Ethernet0
                    |  (unnumbered)          |              10.10.11.2/30
                    |                        |
                    |  PortChannel1 (LAG)    | ----LAG----> DUT2 PortChannel1
                    |  (unnumbered)          |              10.10.12.2/30
                    |    - Ethernet8         |
                    |    - Ethernet12        |
                    +------------------------+
                             |
                             | Multi-hop path
                             ↓
                    +------------------------+
                    |         DUT2           |
                    |                        |
                    |  Ethernet0             |
                    |  IP: 10.10.10.2/30     | <---P2P---- DUT1 Ethernet0
                    |                        |
                    |  Ethernet4             |
                    |  IP: 10.10.20.1/30     | ----P2P----> DUT3 Ethernet4
                    |                        |              10.10.20.2/30
                    |  PortChannel1 (LAG)    |
                    |  IP: 10.10.12.2/30     | <---LAG---- DUT1 PortChannel1
                    |    - Ethernet8         |
                    |    - Ethernet12        |
                    |                        |
                    |  Loopback0             |
                    |  IP: 20.20.20.1/32     |
                    +------------------------+
                             |
                             | Multi-hop path
                             ↓
                    +------------------------+
                    |         DUT3           |
                    |                        |
                    |  Ethernet0             |
                    |  IP: 10.10.11.2/30     | <---P2P---- DUT1 Ethernet4
                    |                        |
                    |  Ethernet4             |
                    |  IP: 10.10.20.2/30     | <---P2P---- DUT2 Ethernet4
                    |                        |
                    |  Loopback0             |
                    |  IP: 30.30.30.1/32     |
                    +------------------------+
```

### Interface Configuration

**DUT1 Configuration (Multiple Unnumbered Sharing Single Donor)**:
- **Loopback0 (Donor Interface)**:
  - IP Address: 10.10.10.1/32
  - Purpose: Single donor shared by all unnumbered interfaces
  - Type: Virtual interface (always up)

- **Ethernet0 (Unnumbered - P2P to DUT2)**:
  - Configuration: ip unnumbered Loopback0
  - Borrows IP from: Loopback0 (10.10.10.1/32)
  - Purpose: Point-to-point connection to DUT2
  - Connected to: DUT2 Ethernet0

- **Ethernet4 (Unnumbered - P2P to DUT3)**:
  - Configuration: ip unnumbered Loopback0
  - Borrows IP from: Loopback0 (10.10.10.1/32)
  - Purpose: Point-to-point connection to DUT3
  - Connected to: DUT3 Ethernet0

- **PortChannel1 (LAG - Unnumbered)**:
  - Configuration: ip unnumbered Loopback0
  - Borrows IP from: Loopback0 (10.10.10.1/32)
  - Purpose: LAG interface testing with unnumbered
  - Members: Ethernet8, Ethernet12
  - Connected to: DUT2 PortChannel1

**DUT2 Configuration (Numbered Interfaces)**:
- **Ethernet0 (Numbered - P2P to DUT1)**:
  - IP Address: 10.10.10.2/30
  - Purpose: Connected to DUT1 Ethernet0 (unnumbered)
  - Subnet: 10.10.10.0/30

- **Ethernet4 (Numbered - P2P to DUT3)**:
  - IP Address: 10.10.20.1/30
  - Purpose: Multi-hop path to DUT3
  - Subnet: 10.10.20.0/30

- **PortChannel1 (LAG - Numbered)**:
  - IP Address: 10.10.12.2/30
  - Purpose: LAG connection to DUT1
  - Members: Ethernet8, Ethernet12
  - Subnet: 10.10.12.0/30

- **Loopback0 (Destination)**:
  - IP Address: 20.20.20.1/32
  - Purpose: Reachability testing destination

**DUT3 Configuration (Numbered Interfaces)**:
- **Ethernet0 (Numbered - P2P to DUT1)**:
  - IP Address: 10.10.11.2/30
  - Purpose: Connected to DUT1 Ethernet4 (unnumbered)
  - Subnet: 10.10.11.0/30

- **Ethernet4 (Numbered - P2P to DUT2)**:
  - IP Address: 10.10.20.2/30
  - Purpose: Multi-hop path to DUT2
  - Subnet: 10.10.20.0/30

- **Loopback0 (Destination)**:
  - IP Address: 30.30.30.1/32
  - Purpose: Reachability testing destination

### Prerequisites
1. Three DUTs accessible via SSH
2. SONiC OS installed with IPv4 unnumbered support
3. Access to sonic-cli (klish) on all devices
4. Physical connectivity:
   - DUT1 Ethernet0 ↔ DUT2 Ethernet0
   - DUT1 Ethernet4 ↔ DUT3 Ethernet0
   - DUT1 Ethernet8,12 ↔ DUT2 Ethernet8,12 (LAG)
   - DUT2 Ethernet4 ↔ DUT3 Ethernet4
5. LAG (PortChannel) support on DUT1 and DUT2
6. Static routing support
7. ARP protocol support

---

## Test Procedure

### Step 1: Configure Donor Interface on DUT1
**Objective**: Configure single donor interface (Loopback0) that will be shared by multiple unnumbered interfaces

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Loopback0 as shared donor interface
interface Loopback0
ip address 10.10.10.1/32
no shutdown
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify Loopback0 configuration
show ip interface Loopback0

# Verify running configuration
show running-config interface Loopback0

# Verify IP address assignment
show ip interface brief
```

**Expected Result**:
- Loopback0 configured with IP 10.10.10.1/32
- Loopback0 interface status: up/up
- IP address visible in interface output
- No configuration errors

**Sample Output**:
```
# show ip interface Loopback0
Loopback0 is up, line protocol is up
  Internet address is 10.10.10.1/32
  Broadcast address is 255.255.255.255
  MTU is 65536 bytes
  Helper address is not set
  Directed broadcast forwarding is disabled
  Outgoing access list is not set
  Inbound  access list is not set
```

---

### Step 2: Configure Multiple Unnumbered Interfaces on DUT1 (Sharing Single Donor)
**Objective**: Configure multiple physical interfaces as unnumbered, all sharing Loopback0

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0 as unnumbered (P2P to DUT2)
interface Ethernet0
no shutdown
ip unnumbered Loopback0
exit

# Configure Ethernet4 as unnumbered (P2P to DUT3)
interface Ethernet4
no shutdown
ip unnumbered Loopback0
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Primary validation command
show ip interface

# Verify each unnumbered interface
show ip interface Ethernet0
show ip interface Ethernet4

# Verify running configuration
show running-config interface Ethernet0
show running-config interface Ethernet4

# Verify interface status
show interface status Ethernet0
show interface status Ethernet4
```

**Expected Result**:
- Both Ethernet0 and Ethernet4 configured with "ip unnumbered Loopback0"
- Both interfaces borrow IP 10.10.10.1 from Loopback0
- show ip interface shows all interfaces sharing same IP
- All interfaces operational (up/up)

**Sample Output**:
```
# show ip interface Ethernet0
Ethernet0 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes
  Helper address is not set
  Directed broadcast forwarding is disabled
  Outgoing access list is not set
  Inbound  access list is not set

# show ip interface Ethernet4
Ethernet4 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes
  Helper address is not set
  Directed broadcast forwarding is disabled
  Outgoing access list is not set
  Inbound  access list is not set
```

**Validation Points**:
1. Multiple interfaces sharing single donor IP
2. Each shows "(Unnumbered from Loopback0)"
3. All use same IP address (10.10.10.1/32)
4. Interfaces operational

---

### Step 3: Configure DUT2 Interfaces (P2P and Multi-hop)
**Objective**: Configure DUT2 with numbered interfaces for connectivity testing

**Commands (Execute on DUT2)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0 for P2P to DUT1
interface Ethernet0
ip address 10.10.10.2/30
no shutdown
exit

# Configure Ethernet4 for multi-hop to DUT3
interface Ethernet4
ip address 10.10.20.1/30
no shutdown
exit

# Configure Loopback0 for reachability testing
interface Loopback0
ip address 20.20.20.1/32
no shutdown
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify interface configurations
show ip interface Ethernet0
show ip interface Ethernet4
show ip interface Loopback0

# Verify all interfaces
show ip interface

# Verify running configuration
show running-config
```

**Expected Result**:
- DUT2 Ethernet0 has IP 10.10.10.2/30
- DUT2 Ethernet4 has IP 10.10.20.1/30
- DUT2 Loopback0 has IP 20.20.20.1/32
- All interfaces operational (up/up)

---

### Step 4: Configure DUT3 Interfaces (P2P and Multi-hop)
**Objective**: Configure DUT3 for P2P and multi-hop path testing

**Commands (Execute on DUT3)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0 for P2P to DUT1
interface Ethernet0
ip address 10.10.11.2/30
no shutdown
exit

# Configure Ethernet4 for multi-hop to DUT2
interface Ethernet4
ip address 10.10.20.2/30
no shutdown
exit

# Configure Loopback0 for reachability testing
interface Loopback0
ip address 30.30.30.1/32
no shutdown
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify interface configurations
show ip interface Ethernet0
show ip interface Ethernet4
show ip interface Loopback0

# Verify all interfaces
show ip interface

# Verify running configuration
show running-config
```

**Expected Result**:
- DUT3 Ethernet0 has IP 10.10.11.2/30
- DUT3 Ethernet4 has IP 10.10.20.2/30
- DUT3 Loopback0 has IP 30.30.30.1/32
- All interfaces operational (up/up)

---

### Step 5: Save Configuration on All DUTs
**Objective**: Save running configuration to ensure persistence

**Commands (Execute on DUT1, DUT2, DUT3)**:
```bash
# Enter sonic-cli
sonic-cli

# Save configuration
write memory

# Exit
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify configuration saved
show running-config

# Verify startup config
show startup-config
```

**Expected Result**:
- Configuration saved successfully on all DUTs
- "Configuration saved successfully" message displayed
- Startup-config matches running-config

---

### Step 6: Test P2P Connectivity - DUT1 to DUT2 (via Ethernet0)
**Objective**: Verify point-to-point connectivity over unnumbered interface

**Commands (Execute on DUT1)**:
```bash
# Ping DUT2 Ethernet0 from DUT1
ping 10.10.10.2 -c 5

# Ping with source interface
ping 10.10.10.2 -I Ethernet0 -c 5
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On DUT1 - Verify ARP resolution
show arp

# Verify IP ARP table
show ip arp

# Verify interface counters
show interface counters Ethernet0
```

**Expected Result**:
- Ping to 10.10.10.2 succeeds (0% packet loss)
- ARP entry for 10.10.10.2 visible on DUT1
- P2P connectivity established
- Interface counters incrementing

**Sample Output**:
```
# ping 10.10.10.2 -c 5
PING 10.10.10.2 (10.10.10.2) 56(84) bytes of data.
64 bytes from 10.10.10.2: icmp_seq=1 ttl=64 time=0.234 ms
64 bytes from 10.10.10.2: icmp_seq=2 ttl=64 time=0.187 ms
64 bytes from 10.10.10.2: icmp_seq=3 ttl=64 time=0.192 ms
64 bytes from 10.10.10.2: icmp_seq=4 ttl=64 time=0.189 ms
64 bytes from 10.10.10.2: icmp_seq=5 ttl=64 time=0.191 ms

--- 10.10.10.2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4098ms
rtt min/avg/max/mdev = 0.187/0.198/0.234/0.018 ms

# show arp
Address          HWtype  HWaddress           Flags Mask            Iface
10.10.10.2       ether   aa:bb:cc:dd:ee:01   C                     Ethernet0
```

**Validation Points**:
1. 0% packet loss
2. Successful ICMP echo reply
3. ARP resolution successful
4. P2P connectivity confirmed

---

### Step 7: Test P2P Connectivity - DUT1 to DUT3 (via Ethernet4)
**Objective**: Verify second P2P link also works (multiple unnumbered sharing donor)

**Commands (Execute on DUT1)**:
```bash
# Ping DUT3 Ethernet0 from DUT1
ping 10.10.11.2 -c 5

# Ping with source interface
ping 10.10.11.2 -I Ethernet4 -c 5
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On DUT1 - Verify ARP resolution
show arp

# Verify IP ARP table
show ip arp

# Verify interface counters
show interface counters Ethernet4
```

**Expected Result**:
- Ping to 10.10.11.2 succeeds (0% packet loss)
- ARP entry for 10.10.11.2 visible on DUT1
- Second P2P link operational
- Both Ethernet0 and Ethernet4 functioning simultaneously

**Sample Output**:
```
# ping 10.10.11.2 -c 5
PING 10.10.11.2 (10.10.11.2) 56(84) bytes of data.
64 bytes from 10.10.11.2: icmp_seq=1 ttl=64 time=0.245 ms
64 bytes from 10.10.11.2: icmp_seq=2 ttl=64 time=0.193 ms
64 bytes from 10.10.11.2: icmp_seq=3 ttl=64 time=0.198 ms
64 bytes from 10.10.11.2: icmp_seq=4 ttl=64 time=0.195 ms
64 bytes from 10.10.11.2: icmp_seq=5 ttl=64 time=0.197 ms

--- 10.10.11.2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4099ms
rtt min/avg/max/mdev = 0.193/0.205/0.245/0.020 ms

# show arp
Address          HWtype  HWaddress           Flags Mask            Iface
10.10.10.2       ether   aa:bb:cc:dd:ee:01   C                     Ethernet0
10.10.11.2       ether   aa:bb:cc:dd:ee:02   C                     Ethernet4
```

**Validation Points**:
1. Second P2P link works
2. Multiple unnumbered interfaces operational
3. Separate ARP entries for each P2P neighbor
4. All sharing same donor IP

---

### Step 8: Configure Static Routes for Multi-hop Testing
**Objective**: Configure static routes to enable multi-hop reachability testing

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Route to DUT2 Loopback0 via Ethernet0
ip route 20.20.20.1/32 10.10.10.2

# Route to DUT3 Loopback0 via Ethernet4
ip route 30.30.30.1/32 10.10.11.2

# Exit configuration mode
exit
```

**Commands (Execute on DUT2)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Route to DUT1 Loopback0
ip route 10.10.10.1/32 10.10.10.1

# Route to DUT3 Loopback0 via Ethernet4
ip route 30.30.30.1/32 10.10.20.2

# Exit configuration mode
exit
```

**Commands (Execute on DUT3)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Route to DUT1 Loopback0
ip route 10.10.10.1/32 10.10.11.1

# Route to DUT2 Loopback0 via Ethernet4
ip route 20.20.20.1/32 10.10.20.1

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On DUT1
show ip route

# Verify specific routes
show ip route 20.20.20.1
show ip route 30.30.30.1

# On DUT2
show ip route

# On DUT3
show ip route
```

**Expected Result**:
- Static routes installed on all DUTs
- Routes visible in routing table
- Routes marked as selected (>) and in FIB (*)

**Sample Output (on DUT1)**:
```
# show ip route
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, P - PIM, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR, f - OpenFabric,
       > - selected route, * - FIB route

C>* 10.10.10.0/30 is directly connected, Ethernet0, 00:05:32
C>* 10.10.10.1/32 is directly connected, Loopback0, 00:10:15
C>* 10.10.11.0/30 is directly connected, Ethernet4, 00:05:28
S>* 20.20.20.1/32 [1/0] via 10.10.10.2, Ethernet0, 00:00:05
S>* 30.30.30.1/32 [1/0] via 10.10.11.2, Ethernet4, 00:00:03
```

**Validation Points**:
1. All static routes installed
2. Routes selected and in FIB
3. Multiple routes via different unnumbered interfaces
4. Routing table correct

---

### Step 9: Test Multi-hop Connectivity
**Objective**: Verify multi-hop reachability across the topology

**Commands (Execute on DUT1)**:
```bash
# Ping DUT2 Loopback0 (1 hop)
ping 20.20.20.1 -c 5

# Ping DUT3 Loopback0 (1 hop)
ping 30.30.30.1 -c 5
```

**Commands (Execute on DUT2)**:
```bash
# Ping DUT1 Loopback0
ping 10.10.10.1 -c 5

# Ping DUT3 Loopback0 (1 hop)
ping 30.30.30.1 -c 5
```

**Commands (Execute on DUT3)**:
```bash
# Ping DUT1 Loopback0
ping 10.10.10.1 -c 5

# Ping DUT2 Loopback0 (1 hop)
ping 20.20.20.1 -c 5
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On all DUTs - Verify routing
show ip route

# Verify ARP tables
show arp

# Verify forwarding
show ip arp
```

**Expected Result**:
- All pings successful (0% packet loss)
- Multi-hop paths functional
- End-to-end reachability confirmed
- Forwarding working correctly

**Sample Output (from DUT1)**:
```
# ping 20.20.20.1 -c 5
PING 20.20.20.1 (20.20.20.1) 56(84) bytes of data.
64 bytes from 20.20.20.1: icmp_seq=1 ttl=64 time=0.456 ms
64 bytes from 20.20.20.1: icmp_seq=2 ttl=64 time=0.398 ms
64 bytes from 20.20.20.1: icmp_seq=3 ttl=64 time=0.405 ms
64 bytes from 20.20.20.1: icmp_seq=4 ttl=64 time=0.402 ms
64 bytes from 20.20.20.1: icmp_seq=5 ttl=64 time=0.399 ms

--- 20.20.20.1 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4100ms
rtt min/avg/max/mdev = 0.398/0.412/0.456/0.022 ms

# ping 30.30.30.1 -c 5
PING 30.30.30.1 (30.30.30.1) 56(84) bytes of data.
64 bytes from 30.30.30.1: icmp_seq=1 ttl=64 time=0.478 ms
64 bytes from 30.30.30.1: icmp_seq=2 ttl=64 time=0.421 ms
64 bytes from 30.30.30.1: icmp_seq=3 ttl=64 time=0.427 ms
64 bytes from 30.30.30.1: icmp_seq=4 ttl=64 time=0.423 ms
64 bytes from 30.30.30.1: icmp_seq=5 ttl=64 time=0.425 ms

--- 30.30.30.1 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4102ms
rtt min/avg/max/mdev = 0.421/0.434/0.478/0.021 ms
```

**Validation Points**:
1. Multi-hop reachability works
2. 0% packet loss in all directions
3. Routing functional over unnumbered
4. Forwarding correct

---

### Step 10: Configure LAG (PortChannel) on DUT1 and DUT2
**Objective**: Configure Link Aggregation Group with unnumbered configuration

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Create PortChannel1
interface PortChannel1
no shutdown
exit

# Add member interfaces to LAG
interface Ethernet8
channel-group 1 mode active
no shutdown
exit

interface Ethernet12
channel-group 1 mode active
no shutdown
exit

# Configure PortChannel1 as unnumbered
interface PortChannel1
ip unnumbered Loopback0
exit

# Exit configuration mode
exit
```

**Commands (Execute on DUT2)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Create PortChannel1
interface PortChannel1
no shutdown
exit

# Add member interfaces to LAG
interface Ethernet8
channel-group 1 mode active
no shutdown
exit

interface Ethernet12
channel-group 1 mode active
no shutdown
exit

# Configure PortChannel1 with IP
interface PortChannel1
ip address 10.10.12.2/30
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On DUT1
show ip interface PortChannel1
show interface PortChannel1
show running-config interface PortChannel1

# Verify LAG members
show interfaces PortChannel1
show interface status | grep -E "Ethernet8|Ethernet12|PortChannel1"

# On DUT2
show ip interface PortChannel1
show interface PortChannel1
```

**Expected Result**:
- PortChannel1 created on both DUTs
- LAG members (Ethernet8, Ethernet12) added
- DUT1 PortChannel1 configured as unnumbered (borrows from Loopback0)
- DUT2 PortChannel1 configured with IP 10.10.12.2/30
- LAG operational (up/up)

**Sample Output (on DUT1)**:
```
# show ip interface PortChannel1
PortChannel1 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes
  Helper address is not set
  Directed broadcast forwarding is disabled
  Outgoing access list is not set
  Inbound  access list is not set

# show interface PortChannel1
PortChannel1 is up, line protocol is up
  Hardware is Ethernet, address is aa:bb:cc:dd:ee:ff
  MTU 9100 bytes, BW 20000000 Kbit
  Encapsulation ARPA, loopback not set
  Members in this channel: Ethernet8, Ethernet12
```

**Validation Points**:
1. LAG interface created
2. Members added to LAG
3. PortChannel1 configured as unnumbered on DUT1
4. PortChannel1 borrows IP from Loopback0
5. LAG operational

---

### Step 11: Test LAG Connectivity
**Objective**: Verify connectivity over LAG interface with unnumbered configuration

**Commands (Execute on DUT1)**:
```bash
# Ping DUT2 PortChannel1 IP
ping 10.10.12.2 -c 5

# Ping with source interface (LAG)
ping 10.10.12.2 -I PortChannel1 -c 5
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On DUT1
show arp
show ip arp

# Verify LAG counters
show interface counters PortChannel1
show interface counters Ethernet8
show interface counters Ethernet12

# Verify LAG status
show interface PortChannel1
```

**Expected Result**:
- Ping to 10.10.12.2 succeeds (0% packet loss)
- ARP entry for 10.10.12.2 via PortChannel1
- LAG connectivity functional
- Traffic distributed across LAG members

**Sample Output**:
```
# ping 10.10.12.2 -c 5
PING 10.10.12.2 (10.10.12.2) 56(84) bytes of data.
64 bytes from 10.10.12.2: icmp_seq=1 ttl=64 time=0.321 ms
64 bytes from 10.10.12.2: icmp_seq=2 ttl=64 time=0.267 ms
64 bytes from 10.10.12.2: icmp_seq=3 ttl=64 time=0.272 ms
64 bytes from 10.10.12.2: icmp_seq=4 ttl=64 time=0.269 ms
64 bytes from 10.10.12.2: icmp_seq=5 ttl=64 time=0.271 ms

--- 10.10.12.2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4100ms
rtt min/avg/max/mdev = 0.267/0.280/0.321/0.020 ms

# show arp
Address          HWtype  HWaddress           Flags Mask            Iface
10.10.10.2       ether   aa:bb:cc:dd:ee:01   C                     Ethernet0
10.10.11.2       ether   aa:bb:cc:dd:ee:02   C                     Ethernet4
10.10.12.2       ether   aa:bb:cc:dd:ee:03   C                     PortChannel1
```

**Validation Points**:
1. LAG connectivity works
2. Unnumbered LAG functional
3. ARP resolution via LAG
4. 0% packet loss

---

### Step 12: Test LAG Resilience (Remove One Member)
**Objective**: Verify LAG continues to function when one member is removed

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Shutdown one LAG member
interface Ethernet8
shutdown
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify LAG still operational
show interface PortChannel1

# Verify remaining member
show interface Ethernet12

# Test connectivity still works
ping 10.10.12.2 -c 5

# Verify counters on remaining member
show interface counters Ethernet12
```

**Expected Result**:
- PortChannel1 remains up (1 member active)
- Connectivity maintained
- Ping still succeeds (0% packet loss)
- Traffic flows via Ethernet12 only

**Sample Output**:
```
# show interface PortChannel1
PortChannel1 is up, line protocol is up
  Hardware is Ethernet, address is aa:bb:cc:dd:ee:ff
  MTU 9100 bytes, BW 10000000 Kbit
  Encapsulation ARPA, loopback not set
  Members in this channel: Ethernet12
  Down members in this channel: Ethernet8

# ping 10.10.12.2 -c 5
PING 10.10.12.2 (10.10.12.2) 56(84) bytes of data.
64 bytes from 10.10.12.2: icmp_seq=1 ttl=64 time=0.298 ms
64 bytes from 10.10.12.2: icmp_seq=2 ttl=64 time=0.256 ms
64 bytes from 10.10.12.2: icmp_seq=3 ttl=64 time=0.261 ms
64 bytes from 10.10.12.2: icmp_seq=4 ttl=64 time=0.258 ms
64 bytes from 10.10.12.2: icmp_seq=5 ttl=64 time=0.260 ms

--- 10.10.12.2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4101ms
rtt min/avg/max/mdev = 0.256/0.266/0.298/0.016 ms
```

**Validation Points**:
1. LAG resilience confirmed
2. Connectivity maintained with 1 member
3. Unnumbered LAG still functional
4. Traffic failover successful

---

### Step 13: Restore LAG Member
**Objective**: Restore removed LAG member and verify recovery

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Re-enable LAG member
interface Ethernet8
no shutdown
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify LAG fully restored
show interface PortChannel1

# Verify both members active
show interface Ethernet8
show interface Ethernet12

# Test connectivity
ping 10.10.12.2 -c 5

# Verify traffic distribution
show interface counters PortChannel1
show interface counters Ethernet8
show interface counters Ethernet12
```

**Expected Result**:
- PortChannel1 fully restored (2 members active)
- Both Ethernet8 and Ethernet12 operational
- Connectivity maintained
- Traffic distributed across both members

**Sample Output**:
```
# show interface PortChannel1
PortChannel1 is up, line protocol is up
  Hardware is Ethernet, address is aa:bb:cc:dd:ee:ff
  MTU 9100 bytes, BW 20000000 Kbit
  Encapsulation ARPA, loopback not set
  Members in this channel: Ethernet8, Ethernet12
```

**Validation Points**:
1. LAG fully recovered
2. Both members operational
3. Unnumbered configuration intact
4. Full bandwidth restored

---

### Step 14: Comprehensive ARP/ND Observation
**Objective**: Observe and verify ARP behavior across all topologies

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On DUT1 - Verify all ARP entries
show arp

# Detailed ARP information
show ip arp

# ARP per interface
show arp interface Ethernet0
show arp interface Ethernet4
show arp interface PortChannel1

# Verify neighbor discovery
show ip neighbors
```

**Expected Result**:
- ARP entries for all directly connected neighbors
- Separate ARP entries per interface
- ARP resolution via all interface types (physical, LAG)
- No ARP conflicts

**Sample Output (on DUT1)**:
```
# show arp
Address          HWtype  HWaddress           Flags Mask            Iface
10.10.10.2       ether   aa:bb:cc:dd:ee:01   C                     Ethernet0
10.10.11.2       ether   aa:bb:cc:dd:ee:02   C                     Ethernet4
10.10.12.2       ether   aa:bb:cc:dd:ee:03   C                     PortChannel1

# show ip arp
Protocol  Address          Age(min)  Hardware Addr      Type   Interface
Internet  10.10.10.2             5   aa:bb:cc:dd:ee:01  ARPA   Ethernet0
Internet  10.10.11.2             5   aa:bb:cc:dd:ee:02  ARPA   Ethernet4
Internet  10.10.12.2             7   aa:bb:cc:dd:ee:03  ARPA   PortChannel1
```

**Validation Points**:
1. ARP working across all topologies
2. Separate entries per interface
3. ARP via unnumbered interfaces
4. ARP via LAG interface
5. No conflicts or duplicates

---

### Step 15: Comprehensive Routing Verification
**Objective**: Verify routing tables across all DUTs in all topologies

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On DUT1
show ip route

# Verify specific routes
show ip route 20.20.20.1
show ip route 30.30.30.1

# Route summary
show ip route summary

# On DUT2
show ip route

# On DUT3
show ip route
```

**Expected Result**:
- All routes present and correct
- Connected routes for unnumbered interfaces
- Static routes via unnumbered next-hops
- Routes via LAG interface
- All routes selected and in FIB

**Sample Output (on DUT1)**:
```
# show ip route
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, P - PIM, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR, f - OpenFabric,
       > - selected route, * - FIB route

C>* 10.10.10.0/30 is directly connected, Ethernet0, 00:15:32
C>* 10.10.10.1/32 is directly connected, Loopback0, 00:20:15
C>* 10.10.11.0/30 is directly connected, Ethernet4, 00:15:28
C>* 10.10.12.0/30 is directly connected, PortChannel1, 00:10:22
S>* 20.20.20.1/32 [1/0] via 10.10.10.2, Ethernet0, 00:08:15
S>* 30.30.30.1/32 [1/0] via 10.10.11.2, Ethernet4, 00:08:13

# show ip route summary
Route Source         Routes               FIB  (vrf default)
connected                 4                 4
static                    2                 2
------
Totals                    6                 6
```

**Validation Points**:
1. All expected routes present
2. Connected routes for all unnumbered interfaces
3. Connected route for LAG interface
4. Static routes functional
5. Routes in FIB

---

### Step 16: Comprehensive Forwarding Verification
**Objective**: Test packet forwarding across all topology types

**Commands (Execute on DUT1)**:
```bash
# Test forwarding to all destinations
ping 10.10.10.2 -c 3    # P2P via Ethernet0
ping 10.10.11.2 -c 3    # P2P via Ethernet4
ping 10.10.12.2 -c 3    # LAG via PortChannel1
ping 20.20.20.1 -c 3    # Multi-hop to DUT2
ping 30.30.30.1 -c 3    # Multi-hop to DUT3

# Test with different packet sizes
ping 10.10.10.2 -c 3 -s 1400
ping 20.20.20.1 -c 3 -s 1400

# Test with source selection
ping 10.10.10.2 -I 10.10.10.1 -c 3
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify interface counters
show interface counters

# Check for errors
show interface counters errors

# Verify statistics
show interface counters detailed
```

**Expected Result**:
- All pings successful (0% packet loss)
- Forwarding works across all topology types
- No packet errors
- All interface types forward correctly

**Sample Output**:
```
# ping 10.10.10.2 -c 3
3 packets transmitted, 3 received, 0% packet loss

# ping 10.10.11.2 -c 3
3 packets transmitted, 3 received, 0% packet loss

# ping 10.10.12.2 -c 3
3 packets transmitted, 3 received, 0% packet loss

# ping 20.20.20.1 -c 3
3 packets transmitted, 3 received, 0% packet loss

# ping 30.30.30.1 -c 3
3 packets transmitted, 3 received, 0% packet loss
```

**Validation Points**:
1. Forwarding functional across all topologies
2. P2P links forward correctly
3. LAG forwards correctly
4. Multi-hop forwarding works
5. No packet loss or errors

---

### Step 17: Final Comprehensive Validation - show ip interface
**Objective**: Final validation using primary show command across all DUTs

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On DUT1 - Primary validation command
show ip interface

# Detailed view of each interface
show ip interface Loopback0
show ip interface Ethernet0
show ip interface Ethernet4
show ip interface PortChannel1

# Verify all interfaces operational
show ip interface brief

# On DUT2
show ip interface

# On DUT3
show ip interface
```

**Expected Result**:
- DUT1 shows:
  - Loopback0 with IP 10.10.10.1/32
  - Ethernet0 with IP 10.10.10.1/32 (Unnumbered from Loopback0)
  - Ethernet4 with IP 10.10.10.1/32 (Unnumbered from Loopback0)
  - PortChannel1 with IP 10.10.10.1/32 (Unnumbered from Loopback0)
  - All interfaces up/up

- DUT2 shows:
  - All interfaces with correct numbered IPs
  - All interfaces up/up

- DUT3 shows:
  - All interfaces with correct numbered IPs
  - All interfaces up/up

**Sample Output (on DUT1)**:
```
# show ip interface
Loopback0 is up, line protocol is up
  Internet address is 10.10.10.1/32
  Broadcast address is 255.255.255.255
  MTU is 65536 bytes
  Helper address is not set
  Directed broadcast forwarding is disabled
  Outgoing access list is not set
  Inbound  access list is not set

Ethernet0 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes
  Helper address is not set
  Directed broadcast forwarding is disabled
  Outgoing access list is not set
  Inbound  access list is not set

Ethernet4 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes
  Helper address is not set
  Directed broadcast forwarding is disabled
  Outgoing access list is not set
  Inbound  access list is not set

PortChannel1 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes
  Helper address is not set
  Directed broadcast forwarding is disabled
  Outgoing access list is not set
  Inbound  access list is not set
```

**Validation Points**:
1. Single donor shared by multiple interfaces
2. All unnumbered interfaces show borrowed IP
3. "(Unnumbered from Loopback0)" indication present
4. All interfaces operational
5. LAG interface also unnumbered
6. All topologies functional

---

### Step 18: Save Final Configuration
**Objective**: Save all configurations for persistence

**Commands (Execute on DUT1, DUT2, DUT3)**:
```bash
# Enter sonic-cli
sonic-cli

# Save configuration
write memory

# Exit
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify configuration saved
show startup-config | grep -A 5 "interface"
show startup-config | grep "ip route"
```

**Expected Result**:
- Configuration saved successfully on all DUTs
- Startup-config matches running-config
- All configurations persistent across reboots

---

## Validation Points

### IPv4 Unnumbered Topology Validation (klish mode via sonic-cli)

**Primary Command**:
- `show ip interface`

**Validation Criteria**:

#### 1. Multiple Interfaces Sharing Single Donor
- **Single donor**: Loopback0 with 10.10.10.1/32
- **Multiple targets**: Ethernet0, Ethernet4, PortChannel1
- **All share same IP**: 10.10.10.1/32 borrowed from Loopback0
- **Indication**: "(Unnumbered from Loopback0)" shown for each

#### 2. Point-to-Point (P2P) Connectivity
- **P2P Link 1**: DUT1 Ethernet0 ↔ DUT2 Ethernet0
- **P2P Link 2**: DUT1 Ethernet4 ↔ DUT3 Ethernet0
- **Both functional**: 0% packet loss on both links
- **Separate ARP entries**: One per P2P neighbor

#### 3. Multi-hop Routing
- **Routes installed**: Static routes to remote loopbacks
- **End-to-end reach**: DUT1 can reach DUT2 and DUT3 loopbacks
- **Bidirectional**: All DUTs can reach each other
- **Forwarding works**: Multi-hop packets forwarded correctly

#### 4. LAG (Link Aggregation)
- **LAG created**: PortChannel1 on DUT1 and DUT2
- **Members added**: Ethernet8, Ethernet12
- **Unnumbered config**: DUT1 PortChannel1 borrows from Loopback0
- **Functional**: Connectivity via LAG successful
- **Resilient**: LAG works with 1 or 2 members

#### 5. ARP/Neighbor Discovery
- **ARP resolution**: Works on all interface types
- **Per-interface entries**: Separate ARP per neighbor
- **P2P ARP**: Functional over unnumbered
- **LAG ARP**: Functional over unnumbered LAG
- **No conflicts**: No duplicate or conflicting entries

#### 6. Routing Table
- **Connected routes**: All unnumbered interfaces show connected
- **Static routes**: All static routes installed
- **Route selection**: Routes marked as selected (>)
- **FIB installation**: All routes in FIB (*)
- **LAG routes**: Connected route for LAG interface

#### 7. Forwarding
- **P2P forwarding**: Packets forwarded over P2P links
- **LAG forwarding**: Packets forwarded over LAG
- **Multi-hop forwarding**: Packets reach multi-hop destinations
- **No loss**: 0% packet loss across all paths
- **No errors**: No packet errors on any interface

---

## Expected Overall Results

### Success Criteria

#### 1. Configuration Success
- Single Loopback0 donor configured
- Multiple unnumbered interfaces configured (Ethernet0, Ethernet4, PortChannel1)
- All DUT2 and DUT3 interfaces configured
- LAG created and configured
- All configurations saved

#### 2. P2P Connectivity
- P2P link DUT1↔DUT2: **0% loss**
- P2P link DUT1↔DUT3: **0% loss**
- Both P2P links operational simultaneously
- ARP resolution successful on both

#### 3. Multi-hop Reachability
- DUT1 to DUT2 Loopback0: **0% loss**
- DUT1 to DUT3 Loopback0: **0% loss**
- DUT2 to DUT3 Loopback0: **0% loss**
- Bidirectional reachability: **Full**

#### 4. LAG Functionality
- LAG operational with 2 members: **Yes**
- LAG operational with 1 member: **Yes**
- Connectivity via LAG: **0% loss**
- Unnumbered LAG functional: **Yes**

#### 5. ARP/ND Behavior
- ARP via P2P unnumbered: **Works**
- ARP via LAG unnumbered: **Works**
- No ARP conflicts: **Confirmed**
- Separate entries per interface: **Yes**

#### 6. Routing Behavior
- Connected routes for unnumbered: **Present**
- Connected route for LAG: **Present**
- Static routes via unnumbered: **Installed**
- Routes in FIB: **Yes**

#### 7. Forwarding Behavior
- P2P forwarding: **Functional**
- LAG forwarding: **Functional**
- Multi-hop forwarding: **Functional**
- No packet loss: **Confirmed**
- No packet errors: **Confirmed**

#### 8. Topology Coverage
- **Multiple interfaces sharing donor**: ✓ Validated
- **P2P topology**: ✓ Validated
- **Multi-hop topology**: ✓ Validated
- **LAG topology**: ✓ Validated
- **All topologies operate correctly**: ✓ Confirmed
- **No reachability issues**: ✓ Confirmed

### Performance Criteria

- **Ping Response Time**: < 1 ms (local network)
- **Multi-hop Ping Time**: < 2 ms
- **Packet Loss**: 0% for all paths
- **Route Installation**: Immediate
- **LAG Failover**: < 1 second
- **ARP Resolution**: < 1 second

### Failure Indicators

**Test should fail if**:
1. Multiple interfaces cannot share single donor
2. Any unnumbered interface does not borrow IP from Loopback0
3. P2P connectivity fails on any link
4. Multi-hop reachability fails
5. LAG cannot be configured as unnumbered
6. LAG connectivity fails
7. ARP resolution fails on any interface type
8. Routing table missing expected routes
9. Forwarding fails on any topology type
10. Packet loss exceeds 0%
11. Any topology type has reachability issues

---

## Test Execution Summary Template

### Configuration Verification

| Component | Expected | Actual | Result |
|-----------|----------|--------|--------|
| DUT1 Loopback0 IP | 10.10.10.1/32 | ___ | Pass/Fail |
| DUT1 Ethernet0 unnumbered | Yes | ___ | Pass/Fail |
| DUT1 Ethernet4 unnumbered | Yes | ___ | Pass/Fail |
| DUT1 PortChannel1 unnumbered | Yes | ___ | Pass/Fail |
| LAG members configured | Eth8, Eth12 | ___ | Pass/Fail |

### P2P Connectivity Testing

| Link | Source | Destination | Packet Loss | Result |
|------|--------|-------------|-------------|--------|
| P2P 1 | DUT1 Eth0 | 10.10.10.2 | 0% | Pass/Fail |
| P2P 2 | DUT1 Eth4 | 10.10.11.2 | 0% | Pass/Fail |

### Multi-hop Connectivity Testing

| Test | Source | Destination | Packet Loss | Result |
|------|--------|-------------|-------------|--------|
| To DUT2 Loopback | DUT1 | 20.20.20.1 | 0% | Pass/Fail |
| To DUT3 Loopback | DUT1 | 30.30.30.1 | 0% | Pass/Fail |
| To DUT1 Loopback | DUT2 | 10.10.10.1 | 0% | Pass/Fail |
| To DUT3 Loopback | DUT2 | 30.30.30.1 | 0% | Pass/Fail |
| To DUT1 Loopback | DUT3 | 10.10.10.1 | 0% | Pass/Fail |
| To DUT2 Loopback | DUT3 | 20.20.20.1 | 0% | Pass/Fail |

### LAG Testing

| Test | Configuration | Expected | Actual | Result |
|------|--------------|----------|--------|--------|
| LAG created | PortChannel1 | Yes | ___ | Pass/Fail |
| LAG members | 2 members | Yes | ___ | Pass/Fail |
| LAG unnumbered | Yes | Yes | ___ | Pass/Fail |
| LAG connectivity | 0% loss | ___ | ___ | Pass/Fail |
| LAG resilience (1 member) | 0% loss | ___ | ___ | Pass/Fail |

### ARP/ND Verification

| Interface | Neighbor IP | ARP Entry | Result |
|-----------|-------------|-----------|--------|
| Ethernet0 | 10.10.10.2 | Present | Pass/Fail |
| Ethernet4 | 10.10.11.2 | Present | Pass/Fail |
| PortChannel1 | 10.10.12.2 | Present | Pass/Fail |

### Routing Table Verification

| DUT | Route | Type | Present | In FIB | Result |
|-----|-------|------|---------|--------|--------|
| DUT1 | 10.10.10.0/30 | Connected | Yes/No | Yes/No | Pass/Fail |
| DUT1 | 10.10.11.0/30 | Connected | Yes/No | Yes/No | Pass/Fail |
| DUT1 | 10.10.12.0/30 | Connected | Yes/No | Yes/No | Pass/Fail |
| DUT1 | 20.20.20.1/32 | Static | Yes/No | Yes/No | Pass/Fail |
| DUT1 | 30.30.30.1/32 | Static | Yes/No | Yes/No | Pass/Fail |

### Forwarding Verification

| Path | Type | Packet Loss | Errors | Result |
|------|------|-------------|--------|--------|
| P2P Ethernet0 | P2P | 0% | None | Pass/Fail |
| P2P Ethernet4 | P2P | 0% | None | Pass/Fail |
| LAG PortChannel1 | LAG | 0% | None | Pass/Fail |
| Multi-hop to DUT2 | Multi-hop | 0% | None | Pass/Fail |
| Multi-hop to DUT3 | Multi-hop | 0% | None | Pass/Fail |

---

## Cleanup Steps

After test completion, optionally remove test configuration:

```bash
# On DUT1
sonic-cli

configure terminal

# Remove LAG configuration
interface PortChannel1
no ip unnumbered Loopback0
exit

interface Ethernet8
no channel-group 1
exit

interface Ethernet12
no channel-group 1
exit

no interface PortChannel1

# Remove unnumbered from physical interfaces
interface Ethernet0
no ip unnumbered Loopback0
exit

interface Ethernet4
no ip unnumbered Loopback0
exit

# Remove static routes
no ip route 20.20.20.1/32 10.10.10.2
no ip route 30.30.30.1/32 10.10.11.2

# Remove Loopback0 IP
interface Loopback0
no ip address 10.10.10.1/32
exit

exit

write memory
exit
```

```bash
# On DUT2
sonic-cli

configure terminal

# Remove LAG
interface PortChannel1
no ip address 10.10.12.2/30
exit

interface Ethernet8
no channel-group 1
exit

interface Ethernet12
no channel-group 1
exit

no interface PortChannel1

# Remove static routes
no ip route 10.10.10.1/32 10.10.10.1
no ip route 30.30.30.1/32 10.10.20.2

# Remove IPs from interfaces
interface Ethernet0
no ip address 10.10.10.2/30
exit

interface Ethernet4
no ip address 10.10.20.1/30
exit

interface Loopback0
no ip address 20.20.20.1/32
exit

exit

write memory
exit
```

```bash
# On DUT3
sonic-cli

configure terminal

# Remove static routes
no ip route 10.10.10.1/32 10.10.11.1
no ip route 20.20.20.1/32 10.10.20.1

# Remove IPs from interfaces
interface Ethernet0
no ip address 10.10.11.2/30
exit

interface Ethernet4
no ip address 10.10.20.2/30
exit

interface Loopback0
no ip address 30.30.30.1/32
exit

exit

write memory
exit
```

**Cleanup Verification**:
- All unnumbered configurations removed
- LAG removed
- Static routes removed
- IP addresses removed from interfaces
- Configuration saved on all DUTs

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **Multiple Interfaces Sharing Donor**:
   - Single Loopback0 can be shared by unlimited unnumbered interfaces
   - Each interface borrows same IP
   - No conflicts as each has separate L2 domain
   - ARP resolved per interface

3. **P2P Topology**:
   - Point-to-point direct connections
   - One unnumbered interface per P2P link
   - ARP works over P2P with borrowed IP
   - Routing functional over P2P

4. **Multi-hop Topology**:
   - Static routes required for non-connected networks
   - Routes via unnumbered next-hops work
   - Forwarding across multiple hops functional
   - No special configuration needed

5. **LAG (Link Aggregation)**:
   - LAG interface can be unnumbered
   - Borrows IP from donor like physical interface
   - LAG members don't need individual IPs
   - Resilient to member failures

6. **ARP/Neighbor Discovery**:
   - ARP works on all unnumbered interface types
   - Separate ARP entry per interface
   - No broadcast issues with shared IP
   - Neighbor discovery functional

7. **Routing Behavior**:
   - Connected routes created for unnumbered interfaces
   - Static routes via unnumbered next-hops supported
   - Dynamic routing protocols also supported (not tested here)
   - FIB populated correctly

8. **Forwarding Behavior**:
   - Packets forwarded normally over unnumbered
   - No performance degradation
   - All topology types forward correctly
   - No special MTU or fragmentation issues

9. **Common Issues**:
   - LAG members must match on both sides
   - Physical connectivity required for all links
   - Static routes need correct next-hop IPs
   - ARP must resolve on each link

10. **Verification Tips**:
    - Always use "show ip interface" as primary validation
    - Check ARP table for resolution issues
    - Verify routing table has all expected routes
    - Test connectivity on all paths
    - Verify LAG member status

---

## Additional Validation Commands

For comprehensive testing and troubleshooting (klish mode via sonic-cli):

```bash
# Configuration verification
show running-config
show running-config interface Loopback0
show running-config interface Ethernet0
show running-config interface Ethernet4
show running-config interface PortChannel1
show startup-config

# IP interface verification (PRIMARY COMMAND)
show ip interface
show ip interface Loopback0
show ip interface Ethernet0
show ip interface Ethernet4
show ip interface PortChannel1
show ip interface brief

# Routing verification
show ip route
show ip route summary
show ip route 20.20.20.1
show ip route 30.30.30.1

# Interface status
show interface status
show interface status Ethernet0
show interface status Ethernet4
show interface status PortChannel1
show interface counters
show interface counters errors

# LAG verification
show interfaces PortChannel
show interface PortChannel1
show interfaces PortChannel1 summary

# ARP verification (CRITICAL FOR THIS TEST)
show arp
show ip arp
show arp interface Ethernet0
show arp interface Ethernet4
show arp interface PortChannel1
show ip neighbors

# System verification
show version
show platform summary
```

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Primary Validation Command**:
```bash
show ip interface                      # PRIMARY: Display all IP interfaces
```

**Configuration Commands**:
```bash
show running-config                    # Display entire running configuration
show running-config interface <name>   # Display interface configuration
show startup-config                    # Display startup configuration
show ip interface <name>               # Display IP interface details
show ip interface brief                # Display brief IP summary
```

**Routing Commands**:
```bash
show ip route                          # Display routing table
show ip route <prefix>                 # Display specific route
show ip route summary                  # Display route summary
```

**Interface Commands**:
```bash
show interface status                  # Display interface status
show interface counters                # Display interface counters
show interfaces PortChannel            # Display all LAG interfaces
show interface PortChannel1            # Display specific LAG
```

**ARP Commands (CRITICAL FOR THIS TEST)**:
```bash
show arp                               # Display ARP table
show ip arp                            # Display IP ARP table
show arp interface <name>              # Display ARP for specific interface
show ip neighbors                      # Display neighbor table
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**Loopback Configuration**:
```bash
configure terminal
interface Loopback0
ip address 10.10.10.1/32
no shutdown
exit
exit
```

**Unnumbered Configuration (Physical)**:
```bash
configure terminal
interface Ethernet0
no shutdown
ip unnumbered Loopback0
exit
exit
```

**LAG Configuration**:
```bash
configure terminal
interface PortChannel1
no shutdown
exit
interface Ethernet8
channel-group 1 mode active
no shutdown
exit
interface PortChannel1
ip unnumbered Loopback0
exit
exit
```

**Static Route Configuration**:
```bash
configure terminal
ip route 20.20.20.1/32 10.10.10.2
exit
```

**Save Configuration**:
```bash
write memory
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-18
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.2.3 - Validate unnumbered across topologies
