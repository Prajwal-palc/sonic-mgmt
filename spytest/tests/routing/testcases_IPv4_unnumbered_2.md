# Test Cases - IPv4 Unnumbered Interface in L2/L3/ACL Scenarios

## Test Case ID: TC_IPv4_Unnumbered_1.2.2

### Test Case Name
Verify IPv4 Unnumbered Interface Behavior in L2/L3/ACL Scenarios

### Test Objective
Validate that IPv4 unnumbered interfaces function correctly in Layer 2, Layer 3, and ACL scenarios, behaving equivalently to numbered interfaces for routing and access control operations. Verify that unnumbered interfaces support ping with source selection, static routing configurations, ACL enforcement, and maintain proper reachability. Test includes configuring Loopback0 as donor and Ethernet0 as unnumbered target, verifying configuration persistence, testing connectivity with source IP selection, configuring static routes over unnumbered interfaces, applying and enforcing access control lists, and ensuring unnumbered interfaces integrate seamlessly into L2/L3 forwarding and security policies.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2node_unnumbered.yaml`
- **Topology**: 2 nodes (DUT1 + DUT2)
- **Device Under Test (DUT1)**: Primary router with unnumbered configuration
- **Neighbor Device (DUT2)**: Secondary router for connectivity testing
- **Test Type**: L2/L3/ACL functionality validation

### Topology Diagram

```
                    +------------------------+
                    |         DUT1           |
                    |                        |
                    |  Loopback0 (Donor)     |
                    |  IP: 10.10.10.1/32     |
                    |          |             |
                    |          | (borrows)   |
                    |          ↓             |
                    |  Ethernet0 (Target)    |
                    |  ip unnumbered         |
                    |  Loopback0             |
                    +------------------------+
                             |
                             | Ethernet0 (unnumbered)
                             | Uses 10.10.10.1
                             |
                    +------------------------+
                    |         DUT2           |
                    |                        |
                    |  Ethernet0             |
                    |  IP: 10.10.10.2/30     |
                    |                        |
                    |  Loopback0             |
                    |  IP: 20.20.20.1/32     |
                    +------------------------+
```

### Interface Configuration

**DUT1 Configuration**:
- **Loopback0 (Donor Interface)**:
  - IP Address: 10.10.10.1/32
  - Purpose: Provides IP address for unnumbered interfaces
  - Type: Virtual interface (always up)

- **Ethernet0 (Target/Unnumbered Interface)**:
  - Configuration: ip unnumbered Loopback0
  - Borrows IP from: Loopback0 (10.10.10.1/32)
  - Purpose: L2/L3/ACL testing with unnumbered
  - Type: Physical interface
  - Connected to: DUT2 Ethernet0

**DUT2 Configuration**:
- **Ethernet0 (Numbered Interface)**:
  - IP Address: 10.10.10.2/30
  - Purpose: Connected to DUT1 Ethernet0 (unnumbered)
  - Subnet: 10.10.10.0/30

- **Loopback0 (Destination)**:
  - IP Address: 20.20.20.1/32
  - Purpose: Reachability testing destination

### Prerequisites
1. Two DUTs accessible via SSH
2. SONiC OS installed with IPv4 unnumbered support
3. Access to sonic-cli (klish) on all devices
4. Physical connectivity between DUT1 Ethernet0 and DUT2 Ethernet0
5. Static routing support
6. ACL (Access Control List) support
7. Ping utility with source selection capability

---

## Test Procedure

### Step 1: Initial Setup - Configure Loopback0 Donor on DUT1
**Objective**: Configure the donor interface (Loopback0) on DUT1 with an IP address

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Loopback0 as donor interface
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
- IP address visible in interface brief output
- No configuration errors

**Sample Output**:
```
# show ip interface Loopback0
Loopback0 is up, line protocol is up
  Internet address is 10.10.10.1/32
  Broadcast address is 255.255.255.255
  MTU is 65536 bytes
```

---

### Step 2: Configure IP Unnumbered on DUT1 Ethernet0
**Objective**: Configure Ethernet0 to borrow IP address from Loopback0

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0 as unnumbered interface
interface Ethernet0
no shutdown
ip unnumbered Loopback0
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify unnumbered configuration
show running-config interface Ethernet0

# Verify Ethernet0 interface details
show ip interface Ethernet0

# Verify interface status
show interface status Ethernet0

# Verify running configuration
show running-config
```

**Expected Result**:
- Ethernet0 configured with "ip unnumbered Loopback0"
- Ethernet0 borrows IP 10.10.10.1 from Loopback0
- Running-config shows unnumbered configuration
- Interface operational (up/up)

**Sample Output**:
```
# show running-config interface Ethernet0
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!

# show ip interface Ethernet0
Ethernet0 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes
```

**Validation Points**:
1. Running-config contains "ip unnumbered Loopback0"
2. Ethernet0 shows borrowed IP address
3. Unnumbered source indicated as Loopback0
4. Interface operational

---

### Step 3: Configure DUT2 Ethernet0 and Loopback0
**Objective**: Configure DUT2 interfaces for connectivity testing

**Commands (Execute on DUT2)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0 with numbered IP
interface Ethernet0
ip address 10.10.10.2/30
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
# Verify Ethernet0 configuration
show ip interface Ethernet0
show running-config interface Ethernet0

# Verify Loopback0 configuration
show ip interface Loopback0
show running-config interface Loopback0

# Verify all interfaces
show ip interface brief
```

**Expected Result**:
- DUT2 Ethernet0 has IP 10.10.10.2/30
- DUT2 Loopback0 has IP 20.20.20.1/32
- Both interfaces operational (up/up)
- Configuration saved

**Sample Output**:
```
# show ip interface brief
Interface        IP Address       Status    Protocol
-------------------------------------------------------
Ethernet0        10.10.10.2/30    up        up
Loopback0        20.20.20.1/32    up        up
```

---

### Step 4: Save Configuration on Both DUTs
**Objective**: Save running configuration to ensure persistence

**Commands (Execute on DUT1 and DUT2)**:
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

# Verify startup config matches
show startup-config interface Ethernet0
show startup-config interface Loopback0
```

**Expected Result**:
- Configuration saved successfully on both DUTs
- "Configuration saved successfully" message displayed
- Startup-config matches running-config

---

### Step 5: Verify Basic Connectivity - Ping from DUT1 to DUT2
**Objective**: Test basic Layer 3 connectivity using default source

**Commands (Execute on DUT1)**:
```bash
# Ping DUT2 Ethernet0 from DUT1
ping 10.10.10.2 -c 5

# Ping DUT2 Loopback0 from DUT1 (if route exists)
ping 20.20.20.1 -c 5
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify ARP resolution
show arp

# Verify neighbor discovery
show ip arp
```

**Expected Result**:
- Ping to 10.10.10.2 succeeds (DUT2 Ethernet0)
- 5 packets transmitted, 5 received, 0% packet loss
- ARP entry for 10.10.10.2 visible
- Round-trip time displayed

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
```

**Validation Points**:
1. 0% packet loss
2. Successful ICMP echo reply
3. ARP resolution successful
4. Connectivity established

---

### Step 6: Test Ping with Source Selection
**Objective**: Verify ping works with explicit source IP selection (unnumbered IP)

**Commands (Execute on DUT1)**:
```bash
# Ping with source IP specified (borrowed IP from Loopback0)
ping 10.10.10.2 -I 10.10.10.1 -c 5

# OR using interface as source
ping 10.10.10.2 -I Ethernet0 -c 5

# Ping using Loopback0 as source
ping 10.10.10.2 -I Loopback0 -c 5
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify source IP in ping
# Check packet capture on DUT2 if available

# Verify interface status
show interface status Ethernet0
show ip interface Ethernet0
```

**Expected Result**:
- Ping with source 10.10.10.1 succeeds
- Ping with source interface Ethernet0 succeeds
- Ping with source interface Loopback0 succeeds
- All pings show 0% packet loss
- Source IP correctly used in ICMP packets

**Sample Output**:
```
# ping 10.10.10.2 -I 10.10.10.1 -c 5
PING 10.10.10.2 (10.10.10.2) from 10.10.10.1 : 56(84) bytes of data.
64 bytes from 10.10.10.2: icmp_seq=1 ttl=64 time=0.245 ms
64 bytes from 10.10.10.2: icmp_seq=2 ttl=64 time=0.193 ms
64 bytes from 10.10.10.2: icmp_seq=3 ttl=64 time=0.198 ms
64 bytes from 10.10.10.2: icmp_seq=4 ttl=64 time=0.195 ms
64 bytes from 10.10.10.2: icmp_seq=5 ttl=64 time=0.197 ms

--- 10.10.10.2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4099ms
rtt min/avg/max/mdev = 0.193/0.205/0.245/0.020 ms
```

**Validation Points**:
1. Source IP 10.10.10.1 used successfully
2. Ping successful with source selection
3. Unnumbered interface acts as source
4. No routing issues

---

### Step 7: Configure Static Route on DUT1 via Unnumbered Interface
**Objective**: Configure static route to DUT2 Loopback0 using unnumbered interface

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure static route to DUT2 Loopback0 via Ethernet0 (unnumbered)
ip route 20.20.20.1/32 10.10.10.2

# OR using interface-based route
ip route 20.20.20.1/32 Ethernet0

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify static route installed
show ip route

# Verify specific route
show ip route 20.20.20.1

# Verify running configuration
show running-config | grep "ip route"
```

**Expected Result**:
- Static route to 20.20.20.1/32 installed
- Next-hop 10.10.10.2 or interface Ethernet0
- Route visible in routing table
- Route type: Static (S)

**Sample Output**:
```
# show ip route
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, P - PIM, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR, f - OpenFabric,
       > - selected route, * - FIB route

C>* 10.10.10.0/30 is directly connected, Ethernet0, 00:05:32
C>* 10.10.10.1/32 is directly connected, Loopback0, 00:10:15
S>* 20.20.20.1/32 [1/0] via 10.10.10.2, Ethernet0, 00:00:05
```

**Validation Points**:
1. Static route installed (S)
2. Route selected (>)
3. Route in FIB (*)
4. Correct next-hop displayed
5. Static route over unnumbered interface works

---

### Step 8: Configure Static Route on DUT2 for Return Path
**Objective**: Configure static route on DUT2 for return traffic to DUT1 Loopback0

**Commands (Execute on DUT2)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure static route to DUT1 Loopback0
ip route 10.10.10.1/32 10.10.10.1

# OR using interface
ip route 10.10.10.1/32 Ethernet0

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify static route installed
show ip route

# Verify specific route
show ip route 10.10.10.1

# Verify running configuration
show running-config
```

**Expected Result**:
- Static route to 10.10.10.1/32 installed on DUT2
- Route visible in routing table
- Return path established

**Sample Output**:
```
# show ip route
C>* 10.10.10.0/30 is directly connected, Ethernet0, 00:08:45
S>* 10.10.10.1/32 [1/0] via 10.10.10.1, Ethernet0, 00:00:03
C>* 20.20.20.1/32 is directly connected, Loopback0, 00:08:45
```

---

### Step 9: Test End-to-End Connectivity with Static Routes
**Objective**: Verify end-to-end connectivity using static routes over unnumbered

**Commands (Execute on DUT1)**:
```bash
# Ping DUT2 Loopback0 from DUT1 Loopback0
ping 20.20.20.1 -I 10.10.10.1 -c 5

# Ping DUT2 Loopback0 from DUT1 (default source)
ping 20.20.20.1 -c 10
```

**Commands (Execute on DUT2)**:
```bash
# Ping DUT1 Loopback0 from DUT2
ping 10.10.10.1 -c 5

# Ping DUT1 Loopback0 from DUT2 Loopback0
ping 10.10.10.1 -I 20.20.20.1 -c 5
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On DUT1
show ip route 20.20.20.1
show arp

# On DUT2
show ip route 10.10.10.1
show arp
```

**Expected Result**:
- Ping from DUT1 to DUT2 Loopback0 succeeds (0% loss)
- Ping from DUT2 to DUT1 Loopback0 succeeds (0% loss)
- Bidirectional connectivity established
- Static routes working over unnumbered interface

**Sample Output (on DUT1)**:
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
```

**Validation Points**:
1. 0% packet loss in both directions
2. Static routes functional over unnumbered
3. End-to-end reachability confirmed
4. Unnumbered behaves like numbered for routing

---

### Step 10: Configure Access Control List (ACL) on DUT1
**Objective**: Create and configure ACL to control traffic on unnumbered interface

**Step 10.1: Create IP Access List**

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Create IP access list
ip access-list TEST_ACL

# Permit ICMP from DUT2
permit icmp 10.10.10.2/32 any

# Permit all established connections
permit tcp any any established

# Deny all other traffic (implicit, but can be explicit)
deny ip any any

# Exit ACL configuration
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify ACL created
show ip access-lists

# Verify ACL configuration
show ip access-lists TEST_ACL

# Verify running configuration
show running-config | grep -A 10 "ip access-list"
```

**Expected Result**:
- ACL "TEST_ACL" created
- Rules configured correctly
- Permit ICMP from 10.10.10.2
- Permit established TCP connections
- Deny all other traffic

**Sample Output**:
```
# show ip access-lists TEST_ACL
ip access-list TEST_ACL
  permit icmp 10.10.10.2/32 any
  permit tcp any any established
  deny ip any any
```

---

### Step 10.2: Apply ACL to Unnumbered Interface
**Objective**: Apply ACL to Ethernet0 (unnumbered interface)

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Apply ACL to Ethernet0 inbound
interface Ethernet0
ip access-group TEST_ACL in
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify ACL applied to interface
show running-config interface Ethernet0

# Verify ACL bindings
show ip access-lists interface Ethernet0

# Verify interface configuration
show ip interface Ethernet0
```

**Expected Result**:
- ACL "TEST_ACL" applied to Ethernet0 inbound
- Configuration shows "ip access-group TEST_ACL in"
- ACL active on interface

**Sample Output**:
```
# show running-config interface Ethernet0
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
 ip access-group TEST_ACL in
!
```

---

### Step 11: Test ACL Enforcement - Permitted Traffic
**Objective**: Verify ACL permits allowed traffic (ICMP from DUT2)

**Commands (Execute on DUT2)**:
```bash
# Ping DUT1 from DUT2 (should be permitted by ACL)
ping 10.10.10.1 -c 5

# Ping with different packet sizes
ping 10.10.10.1 -c 5 -s 1400
```

**Validation Commands (klish mode via sonic-cli on DUT1)**:
```bash
# Verify ACL hit counters
show ip access-lists TEST_ACL

# Check interface counters
show interface counters Ethernet0
```

**Expected Result**:
- Ping from DUT2 (10.10.10.2) to DUT1 succeeds
- 0% packet loss
- ACL permits ICMP traffic as configured
- ACL counters increment for permit rule

**Sample Output (on DUT2)**:
```
# ping 10.10.10.1 -c 5
PING 10.10.10.1 (10.10.10.1) 56(84) bytes of data.
64 bytes from 10.10.10.1: icmp_seq=1 ttl=64 time=0.421 ms
64 bytes from 10.10.10.1: icmp_seq=2 ttl=64 time=0.387 ms
64 bytes from 10.10.10.1: icmp_seq=3 ttl=64 time=0.392 ms
64 bytes from 10.10.10.1: icmp_seq=4 ttl=64 time=0.389 ms
64 bytes from 10.10.10.1: icmp_seq=5 ttl=64 time=0.395 ms

--- 10.10.10.1 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4101ms
rtt min/avg/max/mdev = 0.387/0.396/0.421/0.012 ms
```

**Validation Points**:
1. ICMP traffic permitted
2. ACL rule matching correctly
3. Unnumbered interface enforces ACL
4. ACL counters increment

---

### Step 12: Test ACL Enforcement - Create Denied Traffic Scenario
**Objective**: Verify ACL denies traffic not explicitly permitted

**Step 12.1: Modify ACL to Deny ICMP from Specific Source**

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Modify ACL to deny ICMP from DUT2
ip access-list TEST_ACL_DENY

# Deny ICMP from DUT2
deny icmp 10.10.10.2/32 any

# Permit all other ICMP (for testing)
permit icmp any any

# Exit ACL configuration
exit

# Apply new ACL to Ethernet0
interface Ethernet0
no ip access-group TEST_ACL in
ip access-group TEST_ACL_DENY in
exit

# Exit configuration mode
exit
```

**Step 12.2: Test Denied Traffic**

**Commands (Execute on DUT2)**:
```bash
# Ping DUT1 from DUT2 (should be denied by ACL)
ping 10.10.10.1 -c 5 -W 2
```

**Validation Commands (klish mode via sonic-cli on DUT1)**:
```bash
# Verify ACL applied
show running-config interface Ethernet0

# Verify ACL hit counters (deny rule should increment)
show ip access-lists TEST_ACL_DENY

# Check interface counters
show interface counters Ethernet0
```

**Expected Result**:
- Ping from DUT2 (10.10.10.2) to DUT1 **fails** (100% packet loss)
- ACL denies ICMP traffic as configured
- ACL deny counter increments
- Other ICMP sources (if tested) would be permitted

**Sample Output (on DUT2)**:
```
# ping 10.10.10.1 -c 5 -W 2
PING 10.10.10.1 (10.10.10.1) 56(84) bytes of data.

--- 10.10.10.1 ping statistics ---
5 packets transmitted, 0 received, 100% packet loss, time 4096ms
```

**Sample ACL Counters (on DUT1)**:
```
# show ip access-lists TEST_ACL_DENY
ip access-list TEST_ACL_DENY
  deny icmp 10.10.10.2/32 any (5 matches)
  permit icmp any any
```

**Validation Points**:
1. ICMP traffic denied as expected
2. ACL deny rule working
3. Unnumbered interface enforces ACL correctly
4. ACL behaves same as on numbered interface

---

### Step 13: Test ACL with Permit Rule Restored
**Objective**: Restore permit ACL and verify traffic resumes

**Commands (Execute on DUT1)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Apply original ACL back
interface Ethernet0
no ip access-group TEST_ACL_DENY in
ip access-group TEST_ACL in
exit

# Exit configuration mode
exit
```

**Commands (Execute on DUT2)**:
```bash
# Ping DUT1 from DUT2 (should succeed again)
ping 10.10.10.1 -c 5
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify ACL applied
show running-config interface Ethernet0

# Verify ACL counters
show ip access-lists TEST_ACL
```

**Expected Result**:
- Original ACL "TEST_ACL" re-applied
- Ping from DUT2 to DUT1 succeeds again (0% loss)
- ACL permit rule functional
- Traffic flows as permitted

---

### Step 14: Comprehensive Configuration Verification
**Objective**: Verify complete running configuration on both DUTs

**Validation Commands (klish mode via sonic-cli on DUT1)**:
```bash
# Verify complete running configuration
show running-config

# Verify interface configurations
show running-config interface Loopback0
show running-config interface Ethernet0

# Verify static routes
show running-config | grep "ip route"

# Verify ACL configuration
show running-config | grep -A 15 "ip access-list"
```

**Validation Commands (klish mode via sonic-cli on DUT2)**:
```bash
# Verify complete running configuration
show running-config

# Verify interface configurations
show running-config interface Loopback0
show running-config interface Ethernet0

# Verify static routes
show running-config | grep "ip route"
```

**Expected Result**:
- DUT1 running-config shows:
  - Loopback0 with IP 10.10.10.1/32
  - Ethernet0 with ip unnumbered Loopback0
  - Static route to 20.20.20.1/32
  - ACL TEST_ACL configured and applied

- DUT2 running-config shows:
  - Loopback0 with IP 20.20.20.1/32
  - Ethernet0 with IP 10.10.10.2/30
  - Static route to 10.10.10.1/32

**Sample Output (DUT1)**:
```
# show running-config
!
interface Loopback0
 ip address 10.10.10.1/32
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
 ip access-group TEST_ACL in
!
ip route 20.20.20.1/32 10.10.10.2
!
ip access-list TEST_ACL
 permit icmp 10.10.10.2/32 any
 permit tcp any any established
 deny ip any any
!
```

---

### Step 15: Routing Table Verification
**Objective**: Verify routing tables on both DUTs show correct routes

**Validation Commands (klish mode via sonic-cli on DUT1)**:
```bash
# Show complete routing table
show ip route

# Show specific routes
show ip route 10.10.10.0/30
show ip route 20.20.20.1
show ip route 10.10.10.1

# Show route summary
show ip route summary
```

**Validation Commands (klish mode via sonic-cli on DUT2)**:
```bash
# Show complete routing table
show ip route

# Show specific routes
show ip route 10.10.10.0/30
show ip route 10.10.10.1
show ip route 20.20.20.1

# Show route summary
show ip route summary
```

**Expected Result**:
- DUT1 routing table shows:
  - Connected route to 10.10.10.0/30 via Ethernet0
  - Connected route to 10.10.10.1/32 via Loopback0
  - Static route to 20.20.20.1/32 via 10.10.10.2

- DUT2 routing table shows:
  - Connected route to 10.10.10.0/30 via Ethernet0
  - Static route to 10.10.10.1/32 via 10.10.10.1
  - Connected route to 20.20.20.1/32 via Loopback0

**Sample Output (DUT1)**:
```
# show ip route
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, P - PIM, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       F - PBR, f - OpenFabric,
       > - selected route, * - FIB route

C>* 10.10.10.0/30 is directly connected, Ethernet0, 00:25:45
C>* 10.10.10.1/32 is directly connected, Loopback0, 00:30:22
S>* 20.20.20.1/32 [1/0] via 10.10.10.2, Ethernet0, 00:15:33
```

**Validation Points**:
1. All expected routes present
2. Routes selected and in FIB
3. Static routes functional
4. Unnumbered interface supports routing

---

### Step 16: Save Final Configuration
**Objective**: Save all configurations for persistence

**Commands (Execute on DUT1 and DUT2)**:
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
show startup-config | grep -A 5 "interface Ethernet0"
show startup-config | grep "ip route"
show startup-config | grep -A 10 "ip access-list"
```

**Expected Result**:
- Configuration saved successfully on both DUTs
- Startup-config matches running-config
- All configurations persistent across reboots

---

### Step 17: Final End-to-End Validation
**Objective**: Final comprehensive validation of all functionality

**Step 17.1: Connectivity Test**

**Commands (Execute on DUT1)**:
```bash
# Test all connectivity paths
ping 10.10.10.2 -c 3     # DUT2 Ethernet0
ping 20.20.20.1 -c 3     # DUT2 Loopback0

# With source selection
ping 10.10.10.2 -I 10.10.10.1 -c 3
ping 20.20.20.1 -I 10.10.10.1 -c 3
```

**Commands (Execute on DUT2)**:
```bash
# Test reverse connectivity
ping 10.10.10.1 -c 3     # DUT1 Loopback0
```

**Step 17.2: Route Verification**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# On DUT1
show ip route
show running-config

# On DUT2
show ip route
show running-config
```

**Step 17.3: ACL Verification**

**Validation Commands (klish mode via sonic-cli on DUT1)**:
```bash
# Verify ACL configuration
show ip access-lists TEST_ACL

# Verify ACL applied to interface
show running-config interface Ethernet0

# Verify ACL counters
show ip access-lists TEST_ACL
```

**Expected Result**:
- All pings successful (0% loss)
- Routes present and correct
- ACLs configured and enforcing correctly
- Unnumbered interface fully functional in L2/L3/ACL scenarios

---

## Validation Points

### IPv4 Unnumbered L2/L3/ACL Validation (klish mode via sonic-cli)

**Primary Commands**:
- `show running-config`
- `show ip route`

**Validation Criteria**:

#### 1. Configuration Persistence
- **Loopback0 donor**: IP 10.10.10.1/32 configured
- **Ethernet0 unnumbered**: "ip unnumbered Loopback0" present
- **ACL configured**: Access list created and applied
- **Static routes**: Routes configured on both DUTs

#### 2. Layer 3 Functionality
- **IP borrowing**: Ethernet0 uses 10.10.10.1 from Loopback0
- **Connectivity**: Ping successful between DUTs
- **Source selection**: Ping with -I option works
- **Routing**: Static routes functional over unnumbered

#### 3. Routing Table
- **Connected routes**: 10.10.10.0/30 and 10.10.10.1/32 on DUT1
- **Static routes**: 20.20.20.1/32 reachable from DUT1
- **Route selection**: Routes marked as selected (>)
- **FIB installation**: Routes in forwarding table (*)

#### 4. ACL Enforcement
- **ACL creation**: Access list successfully configured
- **ACL application**: Applied to unnumbered interface
- **Permit rules**: Allowed traffic passes
- **Deny rules**: Blocked traffic denied
- **Counters**: ACL hit counters increment

#### 5. Unnumbered Behavior
- **Acts like numbered**: Routing works identically
- **ACL support**: ACLs enforce on unnumbered interface
- **Source IP**: Borrowed IP used in packets
- **Reachability**: Full bidirectional connectivity

---

## Expected Overall Results

### Success Criteria

#### 1. Configuration Success
- Loopback0 configured with IP on DUT1
- Ethernet0 configured as unnumbered on DUT1
- DUT2 interfaces configured properly
- All configurations saved

#### 2. Layer 3 Connectivity
- Ping from DUT1 to DUT2 Ethernet0: **0% loss**
- Ping from DUT1 to DUT2 Loopback0: **0% loss**
- Ping from DUT2 to DUT1 Loopback0: **0% loss**
- Ping with source selection: **Works correctly**

#### 3. Static Routing
- Static route to 20.20.20.1/32 installed on DUT1
- Static route to 10.10.10.1/32 installed on DUT2
- Routes in routing table and FIB
- End-to-end reachability via static routes

#### 4. ACL Functionality
- ACL created successfully
- ACL applied to unnumbered interface
- Permit rules allow traffic
- Deny rules block traffic
- ACL counters functional

#### 5. Unnumbered Interface Behavior
- Borrows IP from donor interface
- Supports routing protocols (static shown)
- Supports ACL enforcement
- **Behaves identically to numbered interface**
- No functional differences observed

### Performance Criteria

- **Ping Response Time**: < 1 ms (local network)
- **Packet Loss**: 0% for permitted traffic
- **Packet Loss**: 100% for denied traffic (ACL)
- **Route Installation**: Immediate
- **ACL Enforcement**: Immediate

### Failure Indicators

**Test should fail if**:
1. Unnumbered configuration not applied
2. Ethernet0 does not borrow IP from Loopback0
3. Ping fails between DUTs
4. Source selection (-I) does not work
5. Static routes not installed
6. Static routes over unnumbered fail
7. ACL not created or applied
8. ACL does not enforce permit rules
9. ACL does not enforce deny rules
10. Unnumbered behaves differently from numbered interface

---

## Test Execution Summary Template

### Configuration Verification

| Component | Expected | Actual | Result |
|-----------|----------|--------|--------|
| DUT1 Loopback0 IP | 10.10.10.1/32 | ___ | Pass/Fail |
| DUT1 Ethernet0 unnumbered | Yes | ___ | Pass/Fail |
| DUT2 Ethernet0 IP | 10.10.10.2/30 | ___ | Pass/Fail |
| DUT2 Loopback0 IP | 20.20.20.1/32 | ___ | Pass/Fail |

### Connectivity Testing

| Test | Source | Destination | Packet Loss | Result |
|------|--------|-------------|-------------|--------|
| Basic ping | DUT1 | 10.10.10.2 | 0% | Pass/Fail |
| Source selection | DUT1 (10.10.10.1) | 10.10.10.2 | 0% | Pass/Fail |
| Loopback ping | DUT1 | 20.20.20.1 | 0% | Pass/Fail |
| Reverse ping | DUT2 | 10.10.10.1 | 0% | Pass/Fail |

### Static Routing

| Route | DUT | Next-Hop | Installed | Result |
|-------|-----|----------|-----------|--------|
| 20.20.20.1/32 | DUT1 | 10.10.10.2 | Yes/No | Pass/Fail |
| 10.10.10.1/32 | DUT2 | 10.10.10.1 | Yes/No | Pass/Fail |

### ACL Testing

| Test | ACL Rule | Traffic Type | Expected | Actual | Result |
|------|----------|--------------|----------|--------|--------|
| Permit ICMP | permit icmp | ICMP from DUT2 | Allowed | ___ | Pass/Fail |
| Deny ICMP | deny icmp | ICMP from DUT2 | Blocked | ___ | Pass/Fail |
| ACL counters | N/A | Increment | Yes | ___ | Pass/Fail |

### Routing Table Verification

| DUT | Route | Type | Present | Result |
|-----|-------|------|---------|--------|
| DUT1 | 10.10.10.0/30 | Connected | Yes/No | Pass/Fail |
| DUT1 | 10.10.10.1/32 | Connected | Yes/No | Pass/Fail |
| DUT1 | 20.20.20.1/32 | Static | Yes/No | Pass/Fail |
| DUT2 | 10.10.10.0/30 | Connected | Yes/No | Pass/Fail |
| DUT2 | 10.10.10.1/32 | Static | Yes/No | Pass/Fail |
| DUT2 | 20.20.20.1/32 | Connected | Yes/No | Pass/Fail |

---

## Cleanup Steps

After test completion, optionally remove test configuration:

```bash
# On DUT1
sonic-cli

configure terminal

# Remove ACL from interface
interface Ethernet0
no ip access-group TEST_ACL in
exit

# Remove ACLs
no ip access-list TEST_ACL
no ip access-list TEST_ACL_DENY

# Remove static route
no ip route 20.20.20.1/32 10.10.10.2

# Remove unnumbered configuration
interface Ethernet0
no ip unnumbered Loopback0
exit

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

# Remove static route
no ip route 10.10.10.1/32 10.10.10.1

# Remove Ethernet0 IP
interface Ethernet0
no ip address 10.10.10.2/30
exit

# Remove Loopback0 IP
interface Loopback0
no ip address 20.20.20.1/32
exit

exit

write memory
exit
```

**Cleanup Verification**:
- Unnumbered configuration removed
- ACLs removed
- Static routes removed
- IP addresses removed from interfaces
- Configuration saved

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **IP Unnumbered Behavior**:
   - Borrows IP from donor interface
   - Behaves like numbered interface for routing
   - Supports static routing over unnumbered
   - ACLs enforce correctly on unnumbered interfaces

3. **Source Selection in Ping**:
   - `-I <IP>`: Use specific source IP
   - `-I <interface>`: Use interface's IP as source
   - Works with unnumbered (uses borrowed IP)

4. **Static Routing over Unnumbered**:
   - Can use next-hop IP: `ip route <dest> <nexthop>`
   - Can use interface: `ip route <dest> <interface>`
   - Both methods work with unnumbered

5. **ACL on Unnumbered Interfaces**:
   - ACLs created same as numbered interfaces
   - Applied using `ip access-group <name> <in|out>`
   - Enforcement identical to numbered interfaces
   - Counters track matches

6. **Connectivity Requirements**:
   - Physical connectivity between DUT1 Eth0 and DUT2 Eth0
   - Proper subnet configuration on DUT2
   - ARP resolution required
   - Static routes for remote subnets

7. **ACL Best Practices**:
   - Always have explicit permit/deny rules
   - Test both permit and deny scenarios
   - Verify ACL counters
   - Remove ACL before interface changes

8. **Testing Methodology**:
   - Test connectivity before ACL application
   - Apply ACL and test enforcement
   - Verify counters increment
   - Test both directions if needed

9. **Common Issues**:
   - ARP not resolving: Check physical connectivity
   - Ping fails: Verify routes and ACLs
   - ACL not enforcing: Check application direction
   - Static route not working: Verify next-hop reachability

10. **Verification Tips**:
    - Always verify running-config after changes
    - Check routing table after route changes
    - Verify ACL counters after traffic
    - Save configuration frequently

---

## Additional Validation Commands

For comprehensive testing and troubleshooting (klish mode via sonic-cli):

```bash
# Configuration verification
show running-config
show running-config interface Loopback0
show running-config interface Ethernet0
show startup-config

# IP interface verification
show ip interface
show ip interface brief
show ip interface Loopback0
show ip interface Ethernet0

# Routing verification
show ip route
show ip route summary
show ip route 20.20.20.1
show ip route 10.10.10.1

# ACL verification
show ip access-lists
show ip access-lists TEST_ACL
show ip access-lists TEST_ACL_DENY
show ip access-lists interface Ethernet0

# Interface status
show interface status
show interface status Ethernet0
show interface counters
show interface counters Ethernet0

# ARP verification
show arp
show ip arp
show arp | grep 10.10.10.2

# System verification
show version
show platform summary
```

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Primary Validation Commands**:
```bash
show running-config                    # Display entire running configuration
show ip route                          # Display routing table
```

**Configuration Commands**:
```bash
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

**ACL Commands**:
```bash
show ip access-lists                   # Display all ACLs
show ip access-lists <name>            # Display specific ACL
show ip access-lists interface <name>  # Display ACLs on interface
```

**Interface Commands**:
```bash
show interface status                  # Display interface status
show interface counters                # Display interface counters
show arp                               # Display ARP table
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

**Unnumbered Configuration**:
```bash
configure terminal
interface Ethernet0
no shutdown
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

**ACL Configuration**:
```bash
configure terminal
ip access-list TEST_ACL
permit icmp 10.10.10.2/32 any
permit tcp any any established
deny ip any any
exit
interface Ethernet0
ip access-group TEST_ACL in
exit
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
**Test Plan Reference**: 1.2.2 - Verify unnumbered in L2/L3/ACL scenarios
