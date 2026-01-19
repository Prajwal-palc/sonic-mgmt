# IPv6 VLAN BGP Interface Test Suite

## Overview

This test suite validates IPv6 BGP peering over VLAN interfaces in SONiC devices. It tests VLAN creation, switchport configuration, VLAN interface configuration with IPv6 addressing, BGP session establishment over VLAN, configuration persistence across reboots, and IPv6 connectivity.

## Test Files

- **test_ipv6_vlan_bgp_interface.py**: Main test script
- **vars_ipv6_vlan_bgp_interface.yaml**: Test variables and configuration parameters
- **README_ipv6_vlan_bgp_interface.md**: This documentation file

## Test Coverage

### Test Case 1: test_ipv6_vlan_bgp_interface_config_verify

**Purpose**: Validate IPv6 BGP configuration and session establishment over VLAN interface

**Steps**:
1. Create VLAN 100 on both DUTs
2. Configure Ethernet32 as access port for VLAN 100
3. Configure IPv6 addresses on VLAN interfaces (Vlan100)
4. Verify IPv6 address configuration
5. Test IPv6 connectivity via ping (click CLI)
6. Configure BGP router with router-id on both DUTs
7. Configure BGP neighbors on both DUTs
8. Verify BGP session establishment
9. Verify BGP neighbor details

**Expected Result**:
- All configuration steps succeed
- IPv6 connectivity verified via ping over VLAN
- BGP sessions establish successfully
- BGP state shows "Established"

### Test Case 2: test_ipv6_vlan_bgp_save_reboot

**Purpose**: Validate configuration persistence across reboot

**Steps**:
1. Verify BGP session is established (pre-check)
2. Verify IPv6 connectivity via ping over VLAN
3. Check BGP routes
4. Save configuration on all DUTs
5. Reboot all DUTs
6. Verify BGP sessions after reboot
7. Verify IPv6 connectivity after reboot

**Expected Result**:
- Configuration persists after reboot
- BGP sessions re-establish automatically
- IPv6 connectivity restored over VLAN

## Topology

```
        DUT1 (smic_sonic1)                  DUT2 (smic_sonic2)
        ┌─────────────────────┐             ┌─────────────────────┐
        │                     │             │                     │
        │  Vlan100            │             │  Vlan100            │
        │  2001:db8:100::1/64 │             │  2001:db8:100::2/64 │
        │        │            │             │        │            │
        │        │            │             │        │            │
        │  ┌─────▼────────┐   │             │  ┌─────▼────────┐   │
        │  │   VLAN 100   │   │             │  │   VLAN 100   │   │
        │  │  (untagged)  │   │             │  │  (untagged)  │   │
        │  └─────┬────────┘   │             │  └─────┬────────┘   │
        │        │            │             │        │            │
        │  ┌─────▼────────┐   │             │  ┌─────▼────────┐   │
        │  │ Ethernet32   │───┼─────────────┼──│ Ethernet32   │   │
        │  │ (Access)     │   │ Layer 2 Link│  │ (Access)     │   │
        │  └──────────────┘   │             │  └──────────────┘   │
        │                     │             │                     │
        │  BGP AS 65001       │             │  BGP AS 65001       │
        │  Router-ID 1.1.1.1  │             │  Router-ID 1.1.1.1  │
        └─────────────────────┘             └─────────────────────┘
                     │                                 │
                     │      iBGP Session over          │
                     └──────────VLAN 100───────────────┘
                            IPv6 Unicast AFI
```

## Configuration Details

### DUT1 (smic_sonic1)
```
vlan 100

interface Ethernet32
 switchport access vlan 100
 no shutdown

interface Vlan100
 ipv6 address 2001:db8:100::1/64
 no shutdown

router bgp 65001
 router-id 1.1.1.1
 neighbor 2001:db8:100::2 remote-as 65001
 address-family ipv6 unicast
  neighbor 2001:db8:100::2 activate
```

### DUT2 (smic_sonic2)
```
vlan 100

interface Ethernet32
 switchport access vlan 100
 no shutdown

interface Vlan100
 ipv6 address 2001:db8:100::2/64
 no shutdown

router bgp 65001
 router-id 1.1.1.1
 neighbor 2001:db8:100::1 remote-as 65001
 address-family ipv6 unicast
  neighbor 2001:db8:100::1 activate
```

## How to Run

### Run All Tests

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_ipv6_vlan_bgp_interface.py \
  --logs-path ./logs/test_ipv6_vlan_bgp_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Run Specific Test

**Run only the config/verify test:**
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_ipv6_vlan_bgp_interface.py::TestIpv6VlanBgpInterface::test_ipv6_vlan_bgp_interface_config_verify \
  --logs-path ./logs/test_ipv6_vlan_bgp_config_$(date +%F_%H%M%S) \
  --log-level debug
```

**Run only the save/reboot test:**
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_ipv6_vlan_bgp_interface.py::TestIpv6VlanBgpInterface::test_ipv6_vlan_bgp_save_reboot \
  --logs-path ./logs/test_ipv6_vlan_bgp_reboot_$(date +%F_%H%M%S) \
  --log-level debug
```

## Prerequisites

### Minimum Requirements
- Topology: 2-node setup with direct connection
- SONiC version: Any version supporting IPv6, VLAN, and BGP
- Connection: One physical link between DUT1 and DUT2

### Testbed Configuration
The test uses the testbed defined in `./testbeds/testbed_vs_2d.yaml`:
- DUT1: smic_sonic1 (192.168.100.57)
- DUT2: smic_sonic2 (192.168.100.172)
- Connection: Ethernet32 to Ethernet32

### Feature Requirements
- VLAN support enabled
- IPv6 support enabled
- BGP (FRRouting) enabled
- Klish CLI support

## Test Variables

Variables are defined in `vars_ipv6_vlan_bgp_interface.yaml` and can be overridden:

```yaml
vlan:
  vlan_id: 100
  vlan_name: "Vlan100"

bgp:
  asn: 65001
  neighbor_wait_time: 90
  router_id_dut1: "1.1.1.1"
  router_id_dut2: "1.1.1.1"

ipv6:
  subnet: "2001:db8:100::/64"
  ping_count: 5
```

## Expected Output

### VLAN Configuration
```
sonic# show vlan brief

VLAN   Type      Member          Mode        Tagging       Status
100    Static    Ethernet32      Access      Untagged      Active
```

### VLAN Interface Status
```
sonic# show ipv6 interfaces Vlan100

Vlan100 is up, line protocol is up
  IPv6 is enabled, link-local address is fe80::xxxx:xxxx:xxxx:xxxx
  Global unicast address(es):
    2001:db8:100::1, subnet is 2001:db8:100::/64
```

### BGP Session Established
```
sonic# show bgp ipv6 unicast summary

IPv6 Unicast Summary:
BGP router identifier 1.1.1.1, local AS number 65001
BGP table version 0
RIB entries 0, using 0 bytes of memory
Peers 1, using 24 KiB of memory

Neighbor          V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd
2001:db8:100::2   4      65001        23        23        0    0    0 00:20:31            0

Total number of neighbors 1
```

### IPv6 Connectivity
```
admin@sonic:~$ ping6 2001:db8:100::2 -c 5
PING 2001:db8:100::2(2001:db8:100::2) 56 data bytes
64 bytes from 2001:db8:100::2: icmp_seq=1 ttl=64 time=0.123 ms
64 bytes from 2001:db8:100::2: icmp_seq=2 ttl=64 time=0.098 ms
64 bytes from 2001:db8:100::2: icmp_seq=3 ttl=64 time=0.105 ms
64 bytes from 2001:db8:100::2: icmp_seq=4 ttl=64 time=0.102 ms
64 bytes from 2001:db8:100::2: icmp_seq=5 ttl=64 time=0.099 ms

--- 2001:db8:100::2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss
```

## Troubleshooting

### VLAN Not Created

1. **Check VLAN support:**
   ```bash
   show vlan config
   ```

2. **Verify VLAN creation:**
   ```bash
   show vlan brief
   ```

3. **Check interface is not part of another VLAN:**
   ```bash
   show vlan brief | grep Ethernet32
   ```

### Switchport Configuration Fails

1. **Check if interface is in routed mode:**
   ```bash
   show interfaces Ethernet32
   ```

2. **Ensure interface is not configured as L3:**
   ```bash
   show ip interfaces | grep Ethernet32
   ```

### IPv6 Connectivity Over VLAN Fails

1. **Check VLAN interface status:**
   ```bash
   show interfaces Vlan100
   ```

2. **Check IPv6 address on VLAN interface:**
   ```bash
   show ipv6 interfaces Vlan100
   ```

3. **Check VLAN membership:**
   ```bash
   show vlan brief
   ```

4. **Ping using VLAN interface:**
   ```bash
   ping6 2001:db8:100::2 -c 5
   ```

### BGP Session Not Establishing Over VLAN

1. **Check VLAN interface is up:**
   ```bash
   show interfaces Vlan100
   ```

2. **Check BGP configuration:**
   ```bash
   show running-configuration bgp
   ```

3. **Check BGP neighbor status:**
   ```bash
   show bgp ipv6 unicast neighbors 2001:db8:100::2
   ```

4. **Check IPv6 neighbor table:**
   ```bash
   show ipv6 neighbors
   ```

### Configuration Not Persisting After Reboot

1. **Verify config save:**
   ```bash
   # In vtysh
   config save -y

   # In SONiC
   config save -y
   ```

2. **Check docker routing config mode:**
   ```bash
   show running-configuration | grep docker_routing_config_mode
   ```

3. **Verify VLAN configuration after reboot:**
   ```bash
   show vlan brief
   show interfaces Vlan100
   ```

## Test Framework Details

- **Framework**: SpyTest
- **CLI Types**: Klish (for config and show), Click (for ping)
- **Parallel Execution**: Module setup runs in parallel where possible
- **Cleanup**: Automatic cleanup in module teardown
- **Error Handling**: Comprehensive error reporting with detailed logs

## Differences from Physical Interface Test

| Aspect | Physical Interface | VLAN Interface |
|--------|-------------------|----------------|
| **Interface Type** | Ethernet32 (routed L3) | Vlan100 (SVI - Switched Virtual Interface) |
| **L2 Configuration** | Not required | VLAN creation + switchport config required |
| **Physical Port Role** | Routed L3 interface | Access port (L2) in VLAN 100 |
| **IPv6 Address Location** | Ethernet32 | Vlan100 |
| **BGP Router-ID** | Not explicitly set | Explicitly set to 1.1.1.1 |
| **Additional Config Steps** | None | VLAN creation, switchport configuration |
| **Cleanup Steps** | Simpler | More complex (remove IP, VLAN iface, switchport, VLAN) |
| **STP Considerations** | Not applicable | VLAN participates in STP |

## Notes

- **Test Environment**: This test assumes SONiC devices running Klish CLI with FRRouting BGP daemon
- **VLAN Interface**: Uses VLAN 100 as Layer 3 SVI for IPv6 addressing
- **Switchport Mode**: Ethernet32 configured as access port (not trunk)
- **IPv6 Link-Local**: VLAN interfaces automatically have link-local addresses (fe80::)
- **BGP Router Identifier**: Both DUTs use 1.1.1.1 as router-id (typically should be unique for different routers)
- **Timing**: BGP session establishment typically takes 5-30 seconds; allow sufficient time before validation
- **iBGP Session**: This test uses internal BGP (iBGP) with same AS on both sides (65001)
- **No Routes Advertised**: In this baseline test, no IPv6 routes are advertised, so State/PfxRcd shows 0
- **Keepalive Timer**: Default 60 seconds with 180-second hold time (3:1 ratio)
- **Graceful Restart**: Both peers advertise GR capability
- **Session Stability**: For production readiness, monitor session stability over extended period
- **Configuration Persistence**: Uses `config save -y` for persistent configuration across reboots
- **VLAN Membership**: Ensure Ethernet32 is not part of any other VLAN before configuration
- **STP Considerations**: VLAN 100 will participate in STP; ensure no loops in topology
- **Ping CLI**: IPv6 ping is tested using Click CLI only (not Klish) for better compatibility
- **Show Commands**: All BGP show commands use sonic-cli (Klish) for consistency

## Author

Athira
© 2025, copyrights@SuperMicro

## References

- [SONiC BGP Documentation](https://github.com/Azure/SONiC/wiki/BGP)
- [SONiC VLAN Documentation](https://github.com/Azure/SONiC/wiki/VLAN)
- [SpyTest Framework Guide](https://github.com/Azure/sonic-mgmt/tree/master/spytest)
- [Test Plan Document](../../../testcases_ipv6_vlan_interface_bgp.md)
- [Physical Interface Test](./test_ipv6_bgp_interface.py)
