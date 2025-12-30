# JIRA Ticket: OSPFv2 Unnumbered Adjacency Not Forming Over Loopback Interfaces

## Priority: High
## Component: Routing - OSPF
## Version: SONiC [version]
## Environment: Hardware/Virtual

---

## Summary
OSPFv2 adjacency fails to form when using unnumbered interfaces with loopback as the donor interface. The `show ip ospf neighbor` command returns empty output, indicating that OSPF neighbors are not being discovered.

---

## Description

### Issue
When configuring OSPFv2 with unnumbered interfaces (using `ip unnumbered Loopback0` on Ethernet interfaces), OSPF adjacencies fail to form between devices. The OSPF neighbor table remains empty despite proper configuration of:
- Loopback interfaces with IP addresses
- Ethernet interfaces configured as unnumbered (borrowing from Loopback)
- OSPF router process with area 0
- Network statements for loopback IPs

### Expected Behavior
- OSPF neighbors should form adjacency and reach **Full** state
- `show ip ospf neighbor` should display all connected OSPF neighbors
- OSPF routes should be exchanged and installed in the routing table
- Ping connectivity should work across the OSPF domain using loopback IPs

### Actual Behavior
- OSPF neighbor table is empty
- No OSPF adjacencies form
- No OSPF routes are learned
- Connectivity fails beyond directly connected neighbors

---

## Topology

### Network Diagram
```
+--------+          +--------+          +--------+          +--------+
|   D1   |          |   D2   |          |   D4   |          |   D3   |
|        |          |        |          |        |          |        |
| Loop0  |          | Loop0  |          | Loop0  |          | Loop0  |
|1.1.1.1 |          |2.2.2.2 |          |4.4.4.4 |          |3.3.3.3 |
|  /32   |          |  /32   |          |  /32   |          |  /32   |
|        |          |        |          |        |          |        |
|  Eth0  |----------|  Eth0  |          |        |          |        |
|(unnum) |  Link1   |(unnum) |          |        |          |        |
|        |          |        |          |        |          |        |
|        |          | Eth16  |----------| Eth16  |          |        |
|        |          |(unnum) |  Link2   |(unnum) |          |        |
|        |          |        |          |        |          |        |
|        |          |        |          | Eth32  |----------| Eth32  |
|        |          |        |          |(unnum) |  Link3   |(unnum) |
|        |          |        |          |        |          |        |
+--------+          +--------+          +--------+          +--------+

   Area 0              Area 0             Area 0             Area 0
```

### Topology Details
- **4 devices** connected in a linear topology
- **D1** ↔ **D2** ↔ **D4** ↔ **D3**
- All interfaces configured as **unnumbered** (borrowing IP from Loopback0)
- All devices in **OSPF Area 0**

### Physical Connections
| Device | Interface  | Connected To | Remote Interface | Link Type   |
|--------|-----------|--------------|------------------|-------------|
| D1     | Ethernet0 | D2           | Ethernet0        | Unnumbered  |
| D2     | Ethernet0 | D1           | Ethernet0        | Unnumbered  |
| D2     | Ethernet16| D4           | Ethernet16       | Unnumbered  |
| D4     | Ethernet16| D2           | Ethernet16       | Unnumbered  |
| D4     | Ethernet32| D3           | Ethernet32       | Unnumbered  |
| D3     | Ethernet32| D4           | Ethernet32       | Unnumbered  |

---

## Configuration Applied

### Device D1 Configuration

#### Step-by-Step Commands
```bash
sonic-cli
configure terminal
terminal length 0

# Configure Loopback0 (Donor interface)
interface Loopback0
 ip address 1.1.1.1/32
 no shutdown
 exit

# Configure Ethernet0 as unnumbered (borrows from Loopback0)
interface Ethernet0
 no shutdown
 no ip address
 ip unnumbered Loopback0
 exit

# Configure OSPF
router ospf
 area 0
 network 1.1.1.1/32 area 0
 exit

# Save configuration
write memory
exit
```

#### Running Configuration
```
!
interface Loopback0
 ip address 1.1.1.1/32
 no shutdown
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!
router ospf
 area 0
 network 1.1.1.1/32 area 0
!
```

---

### Device D2 Configuration

#### Step-by-Step Commands
```bash
sonic-cli
configure terminal
terminal length 0

# Configure Loopback0
interface Loopback0
 ip address 2.2.2.2/32
 no shutdown
 exit

# Configure Ethernet0 as unnumbered
interface Ethernet0
 no shutdown
 no ip address
 ip unnumbered Loopback0
 exit

# Configure Ethernet16 as unnumbered
interface Ethernet16
 no shutdown
 no ip address
 ip unnumbered Loopback0
 exit

# Configure OSPF
router ospf
 area 0
 network 2.2.2.2/32 area 0
 exit

# Save configuration
write memory
exit
```

#### Running Configuration
```
!
interface Loopback0
 ip address 2.2.2.2/32
 no shutdown
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!
interface Ethernet16
 no shutdown
 ip unnumbered Loopback0
!
router ospf
 area 0
 network 2.2.2.2/32 area 0
!
```

---

### Device D4 Configuration

#### Step-by-Step Commands
```bash
sonic-cli
configure terminal
terminal length 0

# Configure Loopback0
interface Loopback0
 ip address 4.4.4.4/32
 no shutdown
 exit

# Configure Ethernet16 as unnumbered
interface Ethernet16
 no shutdown
 no ip address
 ip unnumbered Loopback0
 exit

# Configure Ethernet32 as unnumbered
interface Ethernet32
 no shutdown
 no ip address
 ip unnumbered Loopback0
 exit

# Configure OSPF
router ospf
 area 0
 network 4.4.4.4/32 area 0
 exit

# Save configuration
write memory
exit
```

#### Running Configuration
```
!
interface Loopback0
 ip address 4.4.4.4/32
 no shutdown
!
interface Ethernet16
 no shutdown
 ip unnumbered Loopback0
!
interface Ethernet32
 no shutdown
 ip unnumbered Loopback0
!
router ospf
 area 0
 network 4.4.4.4/32 area 0
!
```

---

### Device D3 Configuration

#### Step-by-Step Commands
```bash
sonic-cli
configure terminal
terminal length 0

# Configure Loopback0
interface Loopback0
 ip address 3.3.3.3/32
 no shutdown
 exit

# Configure Ethernet32 as unnumbered
interface Ethernet32
 no shutdown
 no ip address
 ip unnumbered Loopback0
 exit

# Configure OSPF
router ospf
 area 0
 network 3.3.3.3/32 area 0
 exit

# Save configuration
write memory
exit
```

#### Running Configuration
```
!
interface Loopback0
 ip address 3.3.3.3/32
 no shutdown
!
interface Ethernet32
 no shutdown
 ip unnumbered Loopback0
!
router ospf
 area 0
 network 3.3.3.3/32 area 0
!
```

---

## Verification Commands and Outputs

### Device D1 Verification

#### Command: `show ip interface brief`
```
Interface        IP Address        Admin/Oper    Description
-----------      --------------    -----------   ------------
Loopback0        1.1.1.1/32        up/up         -
Ethernet0        1.1.1.1/32        up/up         - (borrowed from Loopback0)
```

#### Command: `show ip interface Ethernet0`
```
Ethernet0 is up, line protocol is up
  Internet address is 1.1.1.1/32 (Borrowed from Loopback0)
  Broadcast address is 255.255.255.255
  ...
```

#### Command: `show running-config interface Loopback0`
```
!
interface Loopback0
 ip address 1.1.1.1/32
 no shutdown
!
```

#### Command: `show running-config interface Ethernet0`
```
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!
```

#### Command: `show ip ospf neighbor` ❌ **ISSUE**
```
sonic# show ip ospf neighbor

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL

(EMPTY - NO NEIGHBORS)
```

**Expected Output:**
```
Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
2.2.2.2           1 Full/DR         00:05:23        00:00:35  1.1.1.1         Ethernet0:1.1.1.1                  0     0     0
```

#### Command: `show ip ospf interface`
```
[Expected to show Ethernet0 in OSPF, but may show no interfaces or interface without neighbors]
```

#### Command: `show ip route`
```
Codes: K - kernel route, C - connected, S - static, R - RIP,
       O - OSPF, I - IS-IS, B - BGP, P - PIM, E - EIGRP, N - NHRP,
       T - Table, v - VNC, V - VNC-Direct, A - Babel, D - SHARP,
       > - selected route, * - FIB route

C>* 1.1.1.1/32 is directly connected, Loopback0

(NO OSPF ROUTES LEARNED)
```

---

### Device D2 Verification

#### Command: `show ip interface brief`
```
Interface        IP Address        Admin/Oper    Description
-----------      --------------    -----------   ------------
Loopback0        2.2.2.2/32        up/up         -
Ethernet0        2.2.2.2/32        up/up         - (borrowed from Loopback0)
Ethernet16       2.2.2.2/32        up/up         - (borrowed from Loopback0)
```

#### Command: `show ip ospf neighbor` ❌ **ISSUE**
```
sonic# show ip ospf neighbor

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL

(EMPTY - NO NEIGHBORS)
```

**Expected Output:**
```
Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
1.1.1.1           1 Full/BDR        00:05:23        00:00:35  2.2.2.2         Ethernet0:2.2.2.2                  0     0     0
4.4.4.4           1 Full/BDR        00:05:23        00:00:35  2.2.2.2         Ethernet16:2.2.2.2                 0     0     0
```

---

### Device D4 Verification

#### Command: `show ip interface brief`
```
Interface        IP Address        Admin/Oper    Description
-----------      --------------    -----------   ------------
Loopback0        4.4.4.4/32        up/up         -
Ethernet16       4.4.4.4/32        up/up         - (borrowed from Loopback0)
Ethernet32       4.4.4.4/32        up/up         - (borrowed from Loopback0)
```

#### Command: `show ip ospf neighbor` ❌ **ISSUE**
```
sonic# show ip ospf neighbor

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL

(EMPTY - NO NEIGHBORS)
```

**Expected Output:**
```
Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
2.2.2.2           1 Full/DR         00:05:23        00:00:35  4.4.4.4         Ethernet16:4.4.4.4                 0     0     0
3.3.3.3           1 Full/BDR        00:05:23        00:00:35  4.4.4.4         Ethernet32:4.4.4.4                 0     0     0
```

---

### Device D3 Verification

#### Command: `show ip interface brief`
```
Interface        IP Address        Admin/Oper    Description
-----------      --------------    -----------   ------------
Loopback0        3.3.3.3/32        up/up         -
Ethernet32       3.3.3.3/32        up/up         - (borrowed from Loopback0)
```

#### Command: `show ip ospf neighbor` ❌ **ISSUE**
```
sonic# show ip ospf neighbor

Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL

(EMPTY - NO NEIGHBORS)
```

**Expected Output:**
```
Neighbor ID     Pri State           Up Time         Dead Time Address         Interface                        RXmtL RqstL DBsmL
4.4.4.4           1 Full/DR         00:05:23        00:00:35  3.3.3.3         Ethernet32:3.3.3.3                 0     0     0
```

---

## Additional Debugging Information

### Debug Commands to Run

On all devices, please capture the following debug outputs:

```bash
# OSPF General Information
show ip ospf
show ip ospf interface
show ip ospf interface detail
show ip ospf neighbor
show ip ospf neighbor detail
show ip ospf database
show ip ospf route

# Interface Information
show interface status
show ip interface
show ip interface brief
show running-config interface Loopback0
show running-config interface Ethernet0  # Adjust for each device
show running-config interface Ethernet16 # D2 and D4
show running-config interface Ethernet32 # D4 and D3

# OSPF Configuration
show running-config router ospf
show ip protocols

# FRR/BGP Docker Information
docker ps | grep bgp
docker exec -it bgp vtysh -c "show running-config"
docker exec -it bgp vtysh -c "show ip ospf neighbor"
docker exec -it bgp vtysh -c "show ip ospf interface"

# Check if OSPF packets are being sent/received
show ip ospf interface Ethernet0 # On each device
tcpdump -i Ethernet0 -n proto ospf  # If tcpdump is available

# System logs
show logging | grep -i ospf
show logging | grep -i unnumbered
```

---

## Analysis and Root Cause Investigation

### Possible Causes

1. **Unnumbered Interface Support Issue**
   - OSPF may not be recognizing unnumbered interfaces properly
   - FRR routing daemon might not support OSPF over unnumbered interfaces in this SONiC version

2. **Network Statement Issue**
   - The `network 1.1.1.1/32 area 0` statement may not be activating OSPF on unnumbered interfaces
   - May need to explicitly enable OSPF on each physical interface

3. **OSPF Hello Packets Not Being Sent/Received**
   - OSPF hello packets may not be transmitted on unnumbered interfaces
   - Interface may not be added to OSPF process

4. **Neighbor Discovery Mechanism**
   - OSPF neighbor discovery might fail on point-to-point unnumbered links
   - Source IP address for OSPF hellos might be incorrect

5. **Configuration Syntax Issue**
   - The CLI syntax for enabling OSPF on unnumbered interfaces might be different
   - May require interface-level OSPF configuration instead of network statements

---

## Alternative Configuration Attempts

### Attempt 1: Interface-Level OSPF Configuration

Try configuring OSPF directly on interfaces instead of using network statements:

#### On D1:
```bash
configure terminal
interface Ethernet0
 ip ospf area 0
 exit
router ospf
 no network 1.1.1.1/32 area 0
 exit
```

### Attempt 2: Point-to-Point Network Type

Explicitly set OSPF network type to point-to-point:

#### On D1:
```bash
configure terminal
interface Ethernet0
 ip ospf network point-to-point
 ip ospf area 0
 exit
```

### Attempt 3: Use Regular IP Addresses (Workaround)

As a temporary workaround to verify OSPF functionality:

#### On D1:
```bash
configure terminal
interface Ethernet0
 no ip unnumbered Loopback0
 ip address 10.1.1.1/24
 exit
router ospf
 network 10.1.1.1/24 area 0
 exit
```

#### On D2:
```bash
configure terminal
interface Ethernet0
 no ip unnumbered Loopback0
 ip address 10.1.1.2/24
 exit
interface Ethernet16
 no ip unnumbered Loopback0
 ip address 20.1.1.1/24
 exit
router ospf
 network 10.1.1.2/24 area 0
 network 20.1.1.1/24 area 0
 exit
```

**Note:** If OSPF works with regular IP addresses but not with unnumbered interfaces, this confirms the issue is specific to OSPFv2 over unnumbered interfaces.

---

## Feature Requirement

### RFC Reference
- **RFC 2328** - OSPFv2 specification
- **RFC 3630** - Traffic Engineering Extensions to OSPF Version 2
- OSPF over unnumbered point-to-point interfaces is a standard feature supported by major vendors

### Industry Standards
- Cisco IOS supports `ip unnumbered` with OSPF
- Juniper JunOS supports unnumbered interfaces with OSPF
- This is a common deployment scenario for point-to-point links

---

## Impact Assessment

### Severity: **High**

**Business Impact:**
- Cannot deploy OSPF in bandwidth-constrained environments where IP address conservation is critical
- Limits design flexibility for large-scale deployments
- Prevents migration from competitor platforms that support this feature
- Increases operational complexity by requiring IP address management for all transit links

**Technical Impact:**
- OSPF cannot form adjacencies over unnumbered interfaces
- Network design must allocate IP subnets for every point-to-point link
- Wastes IP address space (especially critical for IPv4)

---

## Workaround

**Current Workaround:**
Use regular IP addressing (non-unnumbered) on all OSPF interfaces.

**Limitation:**
- Requires additional IP address allocation
- Increases configuration complexity
- Not scalable for large deployments

---

## Requested Action

1. **Investigate** why OSPF adjacencies fail to form over unnumbered interfaces
2. **Confirm** if OSPFv2 over unnumbered interfaces is a supported feature in the current SONiC version
3. **Provide** correct configuration syntax if the feature is supported
4. **Implement** support for OSPFv2 over unnumbered interfaces if not currently supported
5. **Document** the correct configuration procedure for OSPF with unnumbered interfaces
6. **Update** CLI validation to provide clear error messages if unsupported configurations are attempted

---

## Acceptance Criteria

- OSPF neighbors form **Full** adjacency over unnumbered interfaces
- `show ip ospf neighbor` displays all connected neighbors with state "Full"
- OSPF routes are successfully learned and installed in routing table
- Ping connectivity works end-to-end using loopback IP addresses
- Configuration persists after reboot
- Feature works consistently across hardware and virtual platforms

---

## Test Case for Verification

Once the fix is provided, please verify with the following test case:

### Test Procedure:
1. Configure 4 devices in linear topology (D1-D2-D4-D3)
2. Configure loopback interfaces on all devices with unique IPs
3. Configure physical interfaces as unnumbered (borrowing from loopback)
4. Enable OSPF area 0 on all devices
5. Add loopback networks to OSPF
6. Wait 60 seconds for neighbor discovery
7. Verify OSPF neighbors reach Full state
8. Verify OSPF routes are learned on all devices
9. Verify ping connectivity from D1 to D3 using loopback IPs
10. Perform warm reboot and verify adjacencies reform
11. Save configuration and perform cold reboot - verify persistence

### Expected Results:
- All OSPF neighbors in Full state
- Complete routing table with all loopback IPs
- Successful ping from any device to any other device's loopback
- Configuration persists across reboots

---

## Attachments

### Files to Attach:
1. **Full running-config** from all 4 devices
2. **Output of all verification commands** listed above
3. **System logs** filtered for OSPF and unnumbered keywords
4. **FRR configuration** from bgp docker container
5. **Packet captures** showing OSPF hello packets (if available)

---

## Contact Information

**Reported By:** [Your Name]
**Date:** [Current Date]
**Environment:** [HW/Virtual]
**SONiC Version:** [Version]
**Platform:** [Platform Details]

---

## References

### Related Documentation:
- SONiC OSPF Configuration Guide
- FRRouting (FRR) OSPF Documentation: https://docs.frrouting.org/en/latest/ospf.html
- RFC 2328: OSPF Version 2

### Related JIRA Tickets:
- [List any related tickets if applicable]

---

**END OF JIRA TICKET**
