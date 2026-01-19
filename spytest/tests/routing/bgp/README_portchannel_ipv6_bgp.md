# PortChannel IPv6 BGP Test Suite

## Overview
This test suite validates IPv6 BGP peering over PortChannel (Link Aggregation) interfaces on SONiC devices using Klish CLI.

## Test Description
The test creates a PortChannel interface (PortChannel10) on two SONiC devices, adds a physical interface (Ethernet32) as a member, configures IPv6 addresses on the PortChannel interfaces, establishes iBGP sessions, and validates:
- PortChannel creation and member addition
- IPv6 configuration on PortChannel
- BGP session establishment over PortChannel
- IPv6 connectivity via ping (both click and klish CLI)
- Configuration persistence across reboots
- BGP session re-establishment after reboot

## Topology

```
+-------------------------+                       +-------------------------+
|      smic_sonic1        |                       |      smic_sonic2        |
| PC10 2001:db8:20::1/64  |=======================| PC10 2001:db8:20::2/64  |
|  └─ Ethernet32          |                       |  └─ Ethernet32          |
| (192.168.100.243)       |                       | (192.168.100.57)        |
+-------------------------+                       +-------------------------+
    BGP AS 65001                                      BGP AS 65001
    Router-ID: 1.1.1.1                                Router-ID: 2.2.2.2
```

## Configuration Details

### DUT1 (smic_sonic1)
```
interface PortChannel10
 no shutdown

interface Ethernet32
 channel-group 10
 no shutdown

interface PortChannel10
 ipv6 address 2001:db8:20::1/64
 no shutdown

router bgp 65001
 router-id 1.1.1.1
 neighbor 2001:db8:20::2 remote-as 65001
 address-family ipv6 unicast
  neighbor 2001:db8:20::2 activate
```

### DUT2 (smic_sonic2)
```
interface PortChannel10
 no shutdown

interface Ethernet32
 channel-group 10
 no shutdown

interface PortChannel10
 ipv6 address 2001:db8:20::2/64
 no shutdown

router bgp 65001
 router-id 2.2.2.2
 neighbor 2001:db8:20::1 remote-as 65001
 address-family ipv6 unicast
  neighbor 2001:db8:20::1 activate
```

## Verification Commands

### PortChannel Status
```
sonic# show interface PortChannel 10
PortChannel10 is up, line protocol is up, reason none, mode LACP
Hardware is PortChannel, address is
Minimum number of links to bring PortChannel up is 1
Mode of IPV4 address assignment: not-set
IPV6 address is 2001:db8:20::1/64
Mode of IPV6 address assignment: MANUAL
Fallback: Disabled
Graceful shutdown: Disabled
LACP individual: Disabled
LACP individual timeout in seconds: 3
MTU 9100
```

**Note**: The command format requires a space between "PortChannel" and the ID number (e.g., `show interface PortChannel 10`). This command displays both the PortChannel status and IPv6 configuration.

### IPv6 Interfaces
```
sonic# show ipv6 interfaces
---------------------------------------------------------------------------
Interface            IP address/mask                              Admin/Oper
---------------------------------------------------------------------------
PortChannel10        2001:db8:20::1/64                            up/up
```

### BGP Session
```
sonic# show bgp ipv6 unicast summary
BGP router identifier 1.1.1.1, local AS number 65001 vrf-id 0
BGP table version 1
RIB entries 1, using 192 bytes of memory
Peers 1, using 21 KiB of memory

Neighbor        V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd
2001:db8:20::2  4      65001        10        10        0    0    0 00:05:00            0
```

### BGP Neighbor Details
```
sonic# show bgp ipv6 unicast neighbors 2001:db8:20::2
BGP neighbor is 2001:db8:20::2, remote AS 65001, local AS 65001, internal link
  BGP version 4, remote router ID 2.2.2.2, local router ID 1.1.1.1
  BGP state = Established, up for 00:05:00
  Last read 00:00:30, Last write 00:00:30
  Hold time is 180, keepalive interval is 60 seconds
  Configured hold time is 180, keepalive interval is 60 seconds

  For address family: IPv6 Unicast
  Community attribute sent to this neighbor(all)
  0 accepted prefixes
```

### Ping Test
```
# Click CLI
admin@sonic:~$ ping6 2001:db8:20::2 -c 5
PING 2001:db8:20::2(2001:db8:20::2) 56 data bytes
64 bytes from 2001:db8:20::2: icmp_seq=1 ttl=64 time=0.5 ms
...
--- 2001:db8:20::2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss, time 4ms

# Klish CLI
sonic# ping 2001:db8:20::2 ipv6
PING 2001:db8:20::2(2001:db8:20::2) 56 data bytes
64 bytes from 2001:db8:20::2: icmp_seq=1 ttl=64 time=0.5 ms
...
--- 2001:db8:20::2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss
```

## Prerequisites
- Topology: 2-node setup (smic_sonic1, smic_sonic2)
- Physical connection: Ethernet32 <-> Ethernet32
- SONiC OS with LACP support
- Klish CLI enabled
- FRRouting BGP daemon running

## Test Files
- **Test Script**: `tests/routing/bgp/test_portchannel_ipv6_bgp.py`
- **Test Variables**: `tests/routing/bgp/vars_portchannel_ipv6_bgp.yaml`
- **Test Cases**: `testcases_portchannel_ipv6_bgp.md`
- **Testbed**: `testbeds/testbed_vs_2d.yaml`

## How to Run

### Run Complete Test Suite
```bash
cd /home/adminuser/sonic-mgmt/spytest

./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_portchannel_ipv6_bgp.py \
  --logs-path ./logs/test_portchannel_ipv6_bgp_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Run Specific Test
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_portchannel_ipv6_bgp.py::TestPortchannelIpv6Bgp::test_portchannel_ipv6_bgp_config_verify \
  --logs-path ./logs/test_portchannel_ipv6_bgp_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

## Test Flow
1. **Setup Phase**:
   - Create PortChannel10 on both DUTs
   - Add Ethernet32 as member to PortChannel10
   - Bring up PortChannel and member interfaces

2. **IPv6 Configuration**:
   - Configure IPv6 address on PortChannel10 (2001:db8:20::1/64 and 2001:db8:20::2/64)
   - Verify IPv6 configuration
   - Test IPv6 connectivity via ping (both click and klish CLI)

3. **BGP Configuration**:
   - Configure BGP router with AS 65001 and router-id
   - Configure BGP neighbors with IPv6 addresses
   - Activate neighbors in IPv6 unicast address family

4. **BGP Verification**:
   - Verify BGP session establishment
   - Check BGP neighbor details
   - Verify BGP routes
   - Test IPv6 traffic after BGP session (both click and klish CLI)

5. **Persistence Testing**:
   - Save configuration on both DUTs
   - Reboot both DUTs
   - Verify PortChannel, IPv6, and BGP configuration after reboot
   - Verify BGP session re-establishes
   - Test IPv6 connectivity after reboot (both click and klish CLI)

6. **Cleanup Phase**:
   - Remove BGP configuration
   - Remove IPv6 from PortChannel
   - Remove PortChannel members
   - Delete PortChannel

## Expected Results
- PortChannel10 created successfully with Ethernet32 as member
- IPv6 addresses configured on PortChannel interfaces
- BGP sessions establish successfully over PortChannel
- IPv6 ping successful using both click and klish CLI
- All configurations persist after reboot
- BGP sessions re-establish after reboot
- IPv6 connectivity restored after reboot

## Key Features Tested
- **PortChannel (LACP)**:
  - PortChannel interface creation
  - Adding physical interface to PortChannel
  - PortChannel status verification
  - LACP mode operation

- **IPv6 on PortChannel**:
  - IPv6 address configuration on PortChannel
  - IPv6 interface verification
  - IPv6 connectivity over PortChannel

- **BGP over PortChannel**:
  - iBGP session establishment
  - IPv6 unicast address family
  - BGP neighbor state verification
  - BGP route exchange

- **CLI Support**:
  - Klish CLI for all configuration and show commands
  - Both click and klish CLI for ping operations

- **Configuration Persistence**:
  - Configuration save in both vtysh and sonic shells
  - Reboot persistence
  - Automatic service recovery

## Notes
- The test uses Klish CLI for all configuration and show commands
- Ping testing is performed using both click CLI (ping6) and klish CLI (ping ipv6)
- BGP session establishment may take up to 90 seconds
- After reboot, additional wait time is provided for services to stabilize
- The test performs cleanup in module teardown to ensure clean state

## Troubleshooting

### PortChannel Not Coming Up
- Check if Ethernet32 is physically connected
- Verify LACP configuration on both sides
- Check member interface status: `show interface Ethernet32`
- Verify PortChannel members: `show interface PortChannel 10`

### BGP Session Not Establishing
- Verify IPv6 connectivity: `ping6 2001:db8:20::2`
- Check BGP configuration: `show running-config bgp`
- Check BGP process status: `show ip bgp summary`
- Verify router-id configuration

### Configuration Not Persisting After Reboot
- Ensure config save completed successfully
- Check both vtysh and sonic configuration saves
- Verify startup-config exists

## References
- SpyTest Framework Documentation
- SONiC Klish CLI Guide
- FRRouting BGP Documentation
- IEEE 802.3ad LACP Standard
