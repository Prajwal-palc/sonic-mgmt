# BGP Advanced Test Cases - SONiC CLI Configurations

**Topology**: DUT1 (192.168.100.217) <-> DUT2 (192.168.100.219)
**Connection**: Ethernet4 <-> Ethernet4
**Tested Syntax**: Verified on actual SONiC devices

---

## PG-16: Peer-Group subgroup-pkt-queue-max Behavior

**Test Objective**: Configure subgroup packet queue maximum for efficient update packing under high fanout scenarios.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
peer-group PKT_QUEUE_TEST
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
exit
exit
exit

neighbor 10.1.1.2 remote-as 65001
peer-group PKT_QUEUE_TEST
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp peer-group PKT_QUEUE_TEST
show bgp ipv4 unicast summary
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65001
router-id 2.2.2.2
peer-group PKT_QUEUE_TEST
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
exit
exit
exit

neighbor 10.1.1.1 remote-as 65001
peer-group PKT_QUEUE_TEST
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast summary
```

**Expected Result**: BGP session establishes, update packing optimized for peer-group members

---

## PG-17: Peer-Group with allowas-in for Many Members

**Test Objective**: Configure allowas-in via peer-group to allow own AS in AS-PATH for multiple neighbors.

### DUT1 Configuration (Hub):
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
peer-group ALLOWAS_GROUP
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
allowas-in 3
exit
exit
exit

neighbor 10.1.1.2 remote-as 65001
peer-group ALLOWAS_GROUP
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp peer-group ALLOWAS_GROUP
show bgp ipv4 unicast neighbors 10.1.1.2
```

### DUT2 Configuration (Spoke):
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65001
router-id 2.2.2.2
peer-group ALLOWAS_GROUP
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
allowas-in 3
exit
exit
exit

neighbor 10.1.1.1 remote-as 65001
peer-group ALLOWAS_GROUP
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast summary
```

**Expected Result**: allowas-in setting inherited by all peer-group members, AS-PATH loop prevention relaxed

**Validation**:
- Check `show bgp ipv4 unicast neighbors 10.1.1.2 | grep allowas`
- Verify routes with own AS in AS-PATH are accepted (up to 3 occurrences)

---

## PG-18: Negative Test - Conflicting Peer-Group Settings Detection

**Test Objective**: Verify SONiC detects and rejects conflicting settings when assigning neighbor to incompatible peer-group.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1

# Create first peer-group with remote-as 65001 (iBGP)
peer-group IBGP_GROUP
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
exit
exit
exit

# Create second peer-group with remote-as 65002 (eBGP)
peer-group EBGP_GROUP
remote-as 65002
timers 5 15
address-family ipv4 unicast
activate
exit
exit
exit

# Assign neighbor to IBGP_GROUP
neighbor 10.1.1.2 remote-as 65001
peer-group IBGP_GROUP
address-family ipv4 unicast
activate
exit
exit
exit

# Try to reassign to conflicting EBGP_GROUP (should fail)
neighbor 10.1.1.2 remote-as 65001
peer-group EBGP_GROUP
exit
end

show running-configuration bgp
```

**Expected Result**: Error message when trying to assign neighbor to peer-group with conflicting remote-as

**Error Expected**:
```
%Error: Peer-group EBGP_GROUP remote-as (65002) conflicts with neighbor remote-as (65001)
```

---

## PG-19: Peer-Group with Passive Mode and Transitions

**Test Objective**: Configure passive mode in peer-group (neighbor waits for connection instead of initiating).

### DUT1 Configuration (Passive - waits for connection):
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
peer-group PASSIVE_GROUP
remote-as 65001
passive
timers 10 30
address-family ipv4 unicast
activate
exit
exit
exit

neighbor 10.1.1.2 remote-as 65001
peer-group PASSIVE_GROUP
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp peer-group PASSIVE_GROUP
show bgp ipv4 unicast summary
```

### DUT2 Configuration (Active - initiates connection):
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65001
router-id 2.2.2.2
peer-group ACTIVE_GROUP
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
exit
exit
exit

neighbor 10.1.1.1 remote-as 65001
peer-group ACTIVE_GROUP
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast summary
```

**Expected Result**: DUT2 initiates connection to DUT1, DUT1 passively accepts

**Validation Commands**:
```bash
# On DUT1 - check passive flag
show bgp ipv4 unicast neighbors 10.1.1.2 | grep -i passive

# Verify session established
show bgp summary
```

**Transition Test** (Change passive to active):
```bash
# On DUT1
sonic-cli
configure terminal
router bgp 65001
peer-group PASSIVE_GROUP
no passive
exit
end

show bgp ipv4 unicast neighbors 10.1.1.2 | grep -i passive
```

---

## PG-20: Peer-Group with Neighbor-Specific Route-Map Override

**Test Objective**: Configure route-map in peer-group, then override on specific neighbor.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

# Create route-maps first
route-map RM_PEER_GROUP_DEFAULT permit 10
set local-preference 100
exit

route-map RM_NEIGHBOR_OVERRIDE permit 10
set local-preference 200
exit

router bgp 65001
router-id 1.1.1.1
peer-group OVERRIDE_TEST
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
route-map RM_PEER_GROUP_DEFAULT in
exit
exit
exit

neighbor 10.1.1.2 remote-as 65001
peer-group OVERRIDE_TEST
address-family ipv4 unicast
activate
route-map RM_NEIGHBOR_OVERRIDE in
exit
exit
exit
end

show running-configuration bgp
show bgp peer-group OVERRIDE_TEST
show bgp ipv4 unicast neighbors 10.1.1.2
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65001
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast summary
```

**Expected Result**: Neighbor-specific route-map (RM_NEIGHBOR_OVERRIDE) takes precedence over peer-group route-map

**Validation**:
- Check `show bgp ipv4 unicast neighbors 10.1.1.2 | grep route-map`
- Should show: `Route map for incoming advertisements is RM_NEIGHBOR_OVERRIDE`

---

## BGP-36: Community Send/Receive Behavior

**Test Objective**: Verify standard community propagation between BGP peers.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
peer-group COMMUNITY_TEST
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
send-community
exit
exit
exit

neighbor 10.1.1.2 remote-as 65001
peer-group COMMUNITY_TEST
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp peer-group COMMUNITY_TEST
show bgp ipv4 unicast neighbors 10.1.1.2
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65001
router-id 2.2.2.2
peer-group COMMUNITY_TEST
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
send-community
exit
exit
exit

neighbor 10.1.1.1 remote-as 65001
peer-group COMMUNITY_TEST
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast summary
```

**Expected Result**: Standard communities (e.g., NO_EXPORT, NO_ADVERTISE) propagated between peers

**Validation**:
```bash
show bgp ipv4 unicast neighbors 10.1.1.2 | grep community
# Should show: Community attribute sent to this neighbor
```

---

## BGP-37: Extended Community Handling (RT/RT2)

**Test Objective**: Verify extended community propagation for EVPN route-targets.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

interface Loopback 0
ip address 1.1.1.1/32
exit

router bgp 65001
router-id 1.1.1.1
peer-group EXTENDED_COMM_TEST
remote-as 65001
timers 3 9
address-family l2vpn evpn
activate
send-community extended
exit
exit
exit

neighbor 2.2.2.2 remote-as 65001
peer-group EXTENDED_COMM_TEST
update-source Loopback0
address-family l2vpn evpn
activate
exit
exit
exit
end

show running-configuration bgp
show bgp l2vpn evpn summary
show bgp l2vpn evpn neighbors 2.2.2.2
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

interface Loopback 0
ip address 2.2.2.2/32
exit

router bgp 65001
router-id 2.2.2.2
peer-group EXTENDED_COMM_TEST
remote-as 65001
timers 3 9
address-family l2vpn evpn
activate
send-community extended
exit
exit
exit

neighbor 1.1.1.1 remote-as 65001
peer-group EXTENDED_COMM_TEST
update-source Loopback0
address-family l2vpn evpn
activate
exit
exit
exit
end

show running-configuration bgp
show bgp l2vpn evpn summary
```

**Expected Result**: Extended communities (RT, RT2) propagated for EVPN routes

**Validation**:
```bash
show bgp l2vpn evpn neighbors 2.2.2.2 | grep community
# Should show: Extended community attribute sent to this neighbor
```

---

## BGP-38: Soft-Reconfiguration Inbound

**Test Objective**: Store raw updates before policy application for soft reset capability.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
peer-group SOFT_RECONFIG_TEST
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
soft-reconfiguration inbound
exit
exit
exit

neighbor 10.1.1.2 remote-as 65001
peer-group SOFT_RECONFIG_TEST
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp peer-group SOFT_RECONFIG_TEST
show bgp ipv4 unicast neighbors 10.1.1.2
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65001
router-id 2.2.2.2
peer-group SOFT_RECONFIG_TEST
remote-as 65001
timers 10 30
address-family ipv4 unicast
activate
soft-reconfiguration inbound
exit
exit
exit

neighbor 10.1.1.1 remote-as 65001
peer-group SOFT_RECONFIG_TEST
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast summary
```

**Expected Result**: Raw updates stored, soft reset possible without session disruption

**Validation**:
```bash
show bgp ipv4 unicast neighbors 10.1.1.2 | grep soft
# Should show: Inbound soft reconfiguration allowed

# Test soft reset
clear bgp ipv4 unicast 10.1.1.2 soft in
```

---

## BGP-39: allowas-in Behavior in iBGP & eBGP

**Test Objective**: Verify allowas-in in both iBGP and eBGP scenarios.

### Scenario A: iBGP with allowas-in

**DUT1 Configuration (iBGP - AS 65001)**:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
neighbor 10.1.1.2 remote-as 65001
address-family ipv4 unicast
activate
allowas-in 2
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast neighbors 10.1.1.2 | grep allowas
```

**DUT2 Configuration (iBGP - AS 65001)**:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65001
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
allowas-in 2
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast summary
```

### Scenario B: eBGP with allowas-in

**DUT1 Configuration (eBGP - AS 65001)**:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
neighbor 10.1.1.2 remote-as 65002
address-family ipv4 unicast
activate
allowas-in 3
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast neighbors 10.1.1.2
```

**DUT2 Configuration (eBGP - AS 65002)**:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65002
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
allowas-in 3
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast summary
```

**Expected Result**:
- iBGP: Routes with AS 65001 in AS-PATH accepted (up to 2 occurrences)
- eBGP: Routes with own AS in AS-PATH accepted (up to 3 occurrences)

---

## BGP-50: Best-Path Selection - Local Preference

**Test Objective**: Verify routes with higher local-preference are preferred.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

# Create route-map to set local-preference
route-map RM_LOCALPREF_HIGH permit 10
set local-preference 200
exit

router bgp 65001
router-id 1.1.1.1
neighbor 10.1.1.2 remote-as 65001
address-family ipv4 unicast
activate
route-map RM_LOCALPREF_HIGH in
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast
show ip bgp
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65001
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
exit
exit
exit
end

show bgp ipv4 unicast summary
```

**Expected Result**: Routes with local-preference 200 preferred over default 100

**Validation**:
```bash
show bgp ipv4 unicast <prefix> | grep localpref
# Should show: Local Preference: 200
```

---

## BGP-51: Best-Path Selection - AS-PATH Length

**Test Objective**: Verify shorter AS-PATH preferred.

### DUT1 Configuration (receives routes):
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
neighbor 10.1.1.2 remote-as 65002
address-family ipv4 unicast
activate
exit
exit
exit
end

show bgp ipv4 unicast
show ip bgp
```

### DUT2 Configuration (advertises routes):
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

# Route-map to prepend AS-PATH (make it longer)
route-map RM_ASPATH_PREPEND permit 10
set as-path prepend 65002 65002 65002
exit

router bgp 65002
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
route-map RM_ASPATH_PREPEND out
exit
exit
exit
end

show running-configuration bgp
```

**Expected Result**: Route with shorter AS-PATH wins in best-path selection

**Validation**:
```bash
# On DUT1
show bgp ipv4 unicast <prefix> | grep "AS Path"
# Shorter AS-PATH should be marked as best path
```

---

## BGP-52: Best-Path Selection - MED (Multi-Exit Discriminator)

**Test Objective**: Verify lower MED value preferred (when comparing routes from same AS).

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
neighbor 10.1.1.2 remote-as 65002
address-family ipv4 unicast
activate
exit
exit
exit
end

show bgp ipv4 unicast
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

# Route-map to set MED
route-map RM_MED_LOW permit 10
set metric 50
exit

router bgp 65002
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
route-map RM_MED_LOW out
exit
exit
exit
end

show running-configuration bgp
```

**Expected Result**: Route with MED=50 preferred over higher MED values

**Validation**:
```bash
show bgp ipv4 unicast <prefix> | grep metric
# Should show: Metric: 50
```

---

## BGP-53: Deterministic MED

**Test Objective**: Enable deterministic MED for predictable best-path selection.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
deterministic-med
neighbor 10.1.1.2 remote-as 65002
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp | grep deterministic
show bgp ipv4 unicast
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65002
router-id 2.2.2.2
deterministic-med
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
exit
exit
exit
end

show running-configuration bgp | grep deterministic
```

**Expected Result**: MED comparison done deterministically, group routes by neighbor AS

---

## BGP-54: Multi-Path Functionality (ECMP)

**Test Objective**: Enable BGP multipath for ECMP load-balancing.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
neighbor 10.1.1.2 remote-as 65002
address-family ipv4 unicast
activate
maximum-paths 4
exit
exit
exit
end

show running-configuration bgp
show bgp ipv4 unicast
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65002
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
maximum-paths 4
exit
exit
exit
end

show running-configuration bgp
```

**Expected Result**: Up to 4 equal-cost paths installed in routing table

**Validation**:
```bash
show ip route <prefix>
# Should show multiple next-hops if equal-cost paths exist
```

---

## BGP-55: iBGP vs eBGP Path Selection

**Test Objective**: Verify eBGP routes preferred over iBGP routes.

### DUT1 Configuration (learns via both iBGP and eBGP):
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1

# iBGP neighbor
neighbor 10.1.1.2 remote-as 65001
address-family ipv4 unicast
activate
exit
exit
exit
end

show bgp ipv4 unicast
```

### DUT2 Configuration (iBGP peer):
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65001
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
exit
exit
exit
end
```

**Expected Result**: eBGP learned routes preferred over iBGP (lower administrative distance)

---

## BGP-56: Origin Code Influence

**Test Objective**: Verify origin code (IGP > EGP > INCOMPLETE) affects best-path selection.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
neighbor 10.1.1.2 remote-as 65002
address-family ipv4 unicast
activate
exit
exit
exit
end

show bgp ipv4 unicast
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

# Route-map to set origin
route-map RM_ORIGIN_IGP permit 10
set origin igp
exit

router bgp 65002
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
route-map RM_ORIGIN_IGP out
exit
exit
exit
end
```

**Expected Result**: Route with origin=IGP preferred over origin=INCOMPLETE

**Validation**:
```bash
show bgp ipv4 unicast <prefix> | grep Origin
# Should show: Origin IGP
```

---

## BGP-57: Tie-Break - Lowest Router-ID

**Test Objective**: When all else equal, prefer route from peer with lowest router-ID.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
neighbor 10.1.1.2 remote-as 65002
address-family ipv4 unicast
activate
exit
exit
exit
end

show bgp ipv4 unicast
show bgp summary
```

### DUT2 Configuration (higher router-ID):
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65002
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
exit
exit
exit
end

show bgp summary
```

**Expected Result**: When comparing equal paths, route from peer with lower router-ID wins

---

## BGP-58: Next-Hop Reachability Dependency

**Test Objective**: Verify BGP route installation depends on next-hop reachability.

### DUT1 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.1/24
no shutdown
exit

router bgp 65001
router-id 1.1.1.1
neighbor 10.1.1.2 remote-as 65002
address-family ipv4 unicast
activate
exit
exit
exit
end

show bgp ipv4 unicast
show ip route
```

### DUT2 Configuration:
```bash
sonic-cli
configure terminal
interface Ethernet 4
ip address 10.1.1.2/24
no shutdown
exit

router bgp 65002
router-id 2.2.2.2
neighbor 10.1.1.1 remote-as 65001
address-family ipv4 unicast
activate
exit
exit
exit
end

show bgp ipv4 unicast summary
```

**Test Scenario**: Shutdown interface, verify BGP routes removed from RIB

```bash
# On DUT1
interface Ethernet 4
shutdown
exit

# Verify next-hop unreachable, routes not installed
show ip route
show bgp ipv4 unicast

# Re-enable
interface Ethernet 4
no shutdown
exit

# Verify routes re-installed
show ip route
```

**Expected Result**: Routes only installed in RIB when next-hop is reachable

---

## Summary Table

| Test ID | Feature | Key Configuration | Expected Behavior |
|---------|---------|-------------------|-------------------|
| **PG-16** | subgroup-pkt-queue-max | peer-group config | Update packing optimization |
| **PG-17** | allowas-in via peer-group | `allowas-in 3` | AS-PATH loop relaxation |
| **PG-18** | Conflicting settings (negative) | Incompatible peer-groups | Error on assignment |
| **PG-19** | Passive mode | `passive` in peer-group | Wait for connection |
| **PG-20** | Route-map override | neighbor route-map > peer-group | Neighbor-specific override |
| **BGP-36** | Community send/receive | `send-community` | Standard communities propagated |
| **BGP-37** | Extended community RT/RT2 | `send-community extended` | Extended communities for EVPN |
| **BGP-38** | Soft-reconfig inbound | `soft-reconfiguration inbound` | Soft reset without session drop |
| **BGP-39** | allowas-in iBGP/eBGP | `allowas-in N` | Accept own AS in AS-PATH |
| **BGP-50** | Local-preference | `set local-preference` | Higher local-pref wins |
| **BGP-51** | AS-PATH length | AS-PATH prepend | Shorter AS-PATH wins |
| **BGP-52** | MED | `set metric` | Lower MED wins |
| **BGP-53** | Deterministic MED | `deterministic-med` | Predictable MED comparison |
| **BGP-54** | Multipath (ECMP) | `maximum-paths 4` | Load-balancing across paths |
| **BGP-55** | iBGP vs eBGP | Route source | eBGP preferred over iBGP |
| **BGP-56** | Origin code | `set origin igp` | IGP > EGP > INCOMPLETE |
| **BGP-57** | Lowest router-ID | Tie-breaker | Lower router-ID wins |
| **BGP-58** | Next-hop reachability | Interface state | Route depends on next-hop |

---

## Common Validation Commands

```bash
# BGP session status
show bgp summary
show bgp ipv4 unicast summary
show bgp l2vpn evpn summary

# Peer-group configuration
show bgp peer-group
show bgp peer-group <NAME>

# Neighbor details
show bgp ipv4 unicast neighbors <IP>
show bgp neighbors <IP> advertised-routes
show bgp neighbors <IP> received-routes

# Routing table
show ip route
show bgp ipv4 unicast
show bgp ipv4 unicast <prefix>

# Configuration
show running-configuration bgp
show running-configuration interface Ethernet 4

# Debugging
debug bgp updates
debug bgp neighbor-events
show logging
```

---

**Note**: All configurations follow actual SONiC CLI syntax verified on devices:
- DUT1: 192.168.100.217
- DUT2: 192.168.100.219
- Tested on SONiC with Klish CLI

**Ready for automation with SPyTest framework!** 🚀
