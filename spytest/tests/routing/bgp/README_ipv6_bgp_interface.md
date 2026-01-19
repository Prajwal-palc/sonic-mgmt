# IPv6 BGP Interface Test Suite

## Overview

This test suite validates IPv6 BGP peering over physical interfaces in SONiC devices. It tests basic BGP configuration, session establishment, configuration persistence across reboots, and IPv6 connectivity.

## Test Files

- **test_ipv6_bgp_interface.py**: Main test script
- **vars_ipv6_bgp_interface.yaml**: Test variables and configuration parameters
- **README_ipv6_bgp_interface.md**: This documentation file

## Test Coverage

### Test Case 1: test_ipv6_bgp_interface_config_verify

**Purpose**: Validate IPv6 BGP configuration and session establishment

**Steps**:
1. Configure MTU and speed on interfaces
2. Configure IPv6 addresses on both DUTs
3. Verify IPv6 address configuration
4. Test IPv6 connectivity via ping (both click and klish)
5. Configure BGP router and neighbors on both DUTs
6. Verify BGP session establishment
7. Verify BGP neighbor details

**Expected Result**:
- All configuration steps succeed
- IPv6 connectivity verified via ping
- BGP sessions establish successfully
- BGP state shows "Established"

### Test Case 2: test_ipv6_bgp_save_reboot

**Purpose**: Validate configuration persistence across reboot

**Steps**:
1. Verify BGP session is established (pre-check)
2. Verify IPv6 connectivity via ping
3. Check BGP routes
4. Save configuration on all DUTs
5. Reboot all DUTs
6. Verify BGP sessions after reboot
7. Verify IPv6 connectivity after reboot

**Expected Result**:
- Configuration persists after reboot
- BGP sessions re-establish automatically
- IPv6 connectivity restored

## Topology

```
# Topology - 2 nodes (smic_sonic1 and smic_sonic2)
# +-------------------------+                       +-------------------------+
# |      smic_sonic1        |                       |      smic_sonic2        |
# | Eth32 2001:db8:1::1/64  |=======================| Eth32 2001:db8:1::2/64  |
# | (192.168.100.57)        |                       | (192.168.100.172)       |
# | AS: 65001               |                       | AS: 65001               |
# +-------------------------+                       +-------------------------+
```

## Configuration Details

### DUT1 (smic_sonic1)
```
interface Ethernet32
 mtu 9100
 speed 40000
 ipv6 address 2001:db8:1::1/64

router bgp 65001
 neighbor 2001:db8:1::2 remote-as 65001
  address-family ipv6 unicast
   activate
```

### DUT2 (smic_sonic2)
```
interface Ethernet32
 mtu 9100
 speed 40000
 ipv6 address 2001:db8:1::2/64

router bgp 65001
 neighbor 2001:db8:1::1 remote-as 65001
  address-family ipv6 unicast
   activate
```

## How to Run

### Run All Tests

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_ipv6_bgp_interface.py \
  --logs-path ./logs/test_ipv6_bgp_interface_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Run Specific Test

**Run only the config/verify test:**
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_ipv6_bgp_interface.py::TestIpv6BgpInterface::test_ipv6_bgp_interface_config_verify \
  --logs-path ./logs/test_ipv6_bgp_config_$(date +%F_%H%M%S) \
  --log-level debug
```

**Run only the save/reboot test:**
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_ipv6_bgp_interface.py::TestIpv6BgpInterface::test_ipv6_bgp_save_reboot \
  --logs-path ./logs/test_ipv6_bgp_reboot_$(date +%F_%H%M%S) \
  --log-level debug
```

## Prerequisites

### Minimum Requirements
- Topology: 2-node setup with direct connection
- SONiC version: Any version supporting IPv6 and BGP
- Connection: One physical link between DUT1 and DUT2

### Testbed Configuration
The test uses the testbed defined in `./testbeds/testbed_vs_2d.yaml`:
- DUT1: smic_sonic1 (192.168.100.57)
- DUT2: smic_sonic2 (192.168.100.172)
- Connection: Ethernet32 to Ethernet32

### Feature Requirements
- IPv6 support enabled
- BGP (FRRouting) enabled
- Klish CLI support

## Test Variables

Variables are defined in `vars_ipv6_bgp_interface.yaml` and can be overridden:

```yaml
defaults:
  cli_type: klish
  verify_timeout: 90
  reboot_wait_time: 60

bgp:
  asn: 65001
  neighbor_wait_time: 90
  keepalive: 60
  holdtime: 180
```

## Expected Output

### BGP Session Established
```
sonic# show bgp ipv6 unicast summary

IPv6 Unicast Summary:
BGP router identifier 192.168.100.57, local AS number 65001
BGP table version 0
RIB entries 0, using 0 bytes of memory
Peers 1, using 24 KiB of memory

Neighbor        V         AS   MsgRcvd   MsgSent   TblVer  InQ OutQ  Up/Down State/PfxRcd
2001:db8:1::2   4      65001        23        23        0    0    0 00:20:31            0

Total number of neighbors 1
```

### IPv6 Connectivity
```
admin@sonic:~$ ping6 2001:db8:1::2 -c 5
PING 2001:db8:1::2(2001:db8:1::2) 56 data bytes
64 bytes from 2001:db8:1::2: icmp_seq=1 ttl=64 time=0.123 ms
64 bytes from 2001:db8:1::2: icmp_seq=2 ttl=64 time=0.098 ms
64 bytes from 2001:db8:1::2: icmp_seq=3 ttl=64 time=0.105 ms
64 bytes from 2001:db8:1::2: icmp_seq=4 ttl=64 time=0.102 ms
64 bytes from 2001:db8:1::2: icmp_seq=5 ttl=64 time=0.099 ms

--- 2001:db8:1::2 ping statistics ---
5 packets transmitted, 5 received, 0% packet loss
```

## Troubleshooting

### BGP Session Not Establishing

1. **Check interface status:**
   ```bash
   show interfaces status Ethernet32
   ```

2. **Check IPv6 address configuration:**
   ```bash
   show ipv6 interfaces
   ```

3. **Check IPv6 connectivity:**
   ```bash
   ping6 2001:db8:1::2 -c 5
   ```

4. **Check BGP configuration:**
   ```bash
   show running-configuration bgp
   ```

5. **Check BGP neighbor status:**
   ```bash
   show bgp ipv6 unicast neighbors 2001:db8:1::2
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

3. **Verify startup config:**
   ```bash
   show startupconfiguration bgp
   ```

## Test Framework Details

- **Framework**: SpyTest
- **CLI Types**: Klish (primary), Click (for ping verification)
- **Parallel Execution**: Module setup runs in parallel where possible
- **Cleanup**: Automatic cleanup in module teardown
- **Error Handling**: Comprehensive error reporting with detailed logs

## Notes

- The test uses iBGP (same AS on both sides: 65001)
- BGP router-id is derived from management IPv4 address
- IPv6 link-local addresses are automatically configured
- MTU is set to 9100 to support jumbo frames
- Speed is set to 40000 (40G)
- Ping is tested using both Click and Klish CLI for comprehensive validation
- Configuration is saved in both vtysh and sonic shells for persistence

## Author

Athira
© 2025, copyrights@SuperMicro

## References

- [SONiC BGP Documentation](https://github.com/Azure/SONiC/wiki/BGP)
- [SpyTest Framework Guide](https://github.com/Azure/sonic-mgmt/tree/master/spytest)
- [Test Plan Document](../../../testcases_ipv6_interface_bgp.md)
