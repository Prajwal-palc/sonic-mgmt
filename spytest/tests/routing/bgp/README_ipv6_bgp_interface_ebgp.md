# IPv6 eBGP Interface Test Suite

## Overview
This test suite validates IPv6 eBGP (External BGP) peering over physical interfaces on SONiC devices using Klish CLI.

## Files
- **Test Script**: `test_ipv6_bgp_interface_ebgp.py`
- **Variables**: `vars_ipv6_bgp_interface_ebgp.yaml`
- **README**: `README_ipv6_bgp_interface_ebgp.md`

## Test Description
End-to-end validation of IPv6 BGP peering between two SONiC devices with different AS numbers (eBGP). The test:
1. Automatically cleans up existing IPv4/IPv6 addresses on test interfaces
2. Configures IPv6 addresses on physical interfaces
3. Establishes eBGP sessions (DUT1: AS 65001, DUT2: AS 65002)
4. Validates BGP neighborship and IPv6 connectivity
5. Saves configuration using `write memory` command
6. Performs reboot and validates persistence

## Topology

```
+-------------------------+                       +-------------------------+
|      DUT1 (AS 65001)    |                       |      DUT2 (AS 65002)    |
| Ethernet32              |                       | Ethernet32              |
| 2001:db8:1::1/64        |=======================| 2001:db8:1::2/64        |
| Router-ID: 1.1.1.1      |                       | Router-ID: 2.2.2.2      |
+-------------------------+                       +-------------------------+
```

## Configuration

### DUT1 (AS 65001)
```
interface Ethernet32
  ipv6 address 2001:db8:1::1/64
  no shutdown
  mtu 9100
  speed 40000

router bgp 65001
  neighbor 2001:db8:1::2 remote-as 65002
  address-family ipv6 unicast
    activate
```

### DUT2 (AS 65002)
```
interface Ethernet32
  ipv6 address 2001:db8:1::2/64
  no shutdown
  mtu 9100
  speed 40000

router bgp 65002
  neighbor 2001:db8:1::1 remote-as 65001
  address-family ipv6 unicast
    activate
```

## Prerequisites
- **Topology**: 2-node (D1D2:1)
- **Platform**: SONiC hardware or virtual switches
- **Testbed**: `testbed_vs_2d.yaml`
- **CLI Type**: Klish (sonic-cli)

## Variables (vars_ipv6_bgp_interface_ebgp.yaml)

### DUT Configuration
| Parameter | DUT1 | DUT2 | Description |
|-----------|------|------|-------------|
| IPv6 Address | 2001:db8:1::1 | 2001:db8:1::2 | Interface IPv6 |
| BGP ASN | 65001 | 65002 | BGP AS Number (eBGP) |
| Router ID | 1.1.1.1 | 2.2.2.2 | BGP Router ID |

### Network Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| IPv6 Subnet | 2001:db8:1::/64 | Test subnet |
| IPv6 Mask | 64 | Subnet mask |
| MTU | 9100 | Interface MTU |
| Speed | 40000 | Interface speed (Mbps) |

### Test Parameters
| Parameter | Value | Description |
|-----------|-------|-------------|
| CLI Type | klish | CLI mode (sonic-cli) |
| Ping Count | 5 | Number of ping packets |
| BGP Wait Time | 90 | Seconds to wait for BGP |
| Reboot Wait Time | 60 | Seconds to wait post-reboot |

## How to Run

### Basic Execution
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_ipv6_bgp_interface_ebgp.py \
  --logs-path ./logs/test_ipv6_bgp_interface_ebgp_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Run Specific Test
```bash
# Run only basic config test
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_ipv6_bgp_interface_ebgp.py::TestIpv6EbgpInterface::test_ipv6_ebgp_interface_config_verify \
  --logs-path ./logs/test_ebgp_basic_$(date +%F_%H%M%S) \
  --log-level debug

# Run only save/reboot test
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2d.yaml \
  tests/routing/bgp/test_ipv6_bgp_interface_ebgp.py::TestIpv6EbgpInterface::test_ipv6_ebgp_save_reboot \
  --logs-path ./logs/test_ebgp_reboot_$(date +%F_%H%M%S) \
  --log-level debug
```

## Test Cases

### 1. test_ipv6_ebgp_interface_config_verify
**Purpose**: Validate IPv6 eBGP configuration and neighbor establishment

**Steps**:
1. Clean up existing IPv4/IPv6 addresses on test interfaces
2. Configure MTU and speed on interfaces
3. Configure IPv6 addresses on both DUTs
4. Verify IPv6 address configuration
5. Test IPv6 connectivity via ping (click and klish)
6. Configure eBGP router and neighbors (different AS numbers)
7. Verify eBGP session establishment
8. Verify BGP neighbor details

**Expected Result**:
- ✓ All existing IPs removed before test
- ✓ IPv6 addresses configured successfully
- ✓ IPv6 ping successful in both directions
- ✓ eBGP sessions established (DUT1 AS 65001 ↔ DUT2 AS 65002)
- ✓ BGP neighbor state shows "Established"

### 2. test_ipv6_ebgp_save_reboot
**Purpose**: Validate configuration persistence after reboot

**Steps**:
1. Run basic configuration test
2. Verify eBGP session is established (pre-check)
3. Verify IPv6 connectivity via ping
4. Check BGP routes
5. Save configuration using `write memory` (sonic-cli only)
6. Reboot all DUTs
7. Verify eBGP sessions after reboot
8. Verify IPv6 connectivity after reboot

**Expected Result**:
- ✓ Configuration persists after reboot
- ✓ eBGP sessions re-establish automatically
- ✓ IPv6 connectivity restored
- ✓ BGP routes maintained

## Key Features

### 1. Pre-Test Cleanup
The test automatically removes any existing IPv4/IPv6 addresses on test interfaces before starting:
- Checks both IPv4 and IPv6 addresses
- Removes using `no ip address` and `no ipv6 address`
- Ensures clean starting state

### 2. Configuration Save
Uses `write memory` command in sonic-cli (klish) to save configuration:
```bash
sonic-cli
write memory
```
This saves both interface and BGP configurations.

### 3. eBGP Peering
Establishes external BGP peering with different AS numbers:
- DUT1: AS 65001
- DUT2: AS 65002
- Different from iBGP where both devices use same ASN

## Validation

### BGP Session Verification
```bash
show bgp ipv6 unicast summary
show bgp ipv6 unicast neighbors <neighbor-ip>
```

### IPv6 Connectivity
```bash
# Click CLI
ping6 <ipv6-address> -c 5

# Klish CLI
ping <ipv6-address> count 5
```

### Interface Status
```bash
show ipv6 interfaces
show interface status
```

## Troubleshooting

### BGP Session Not Establishing
1. Verify IPv6 connectivity: `ping6 <neighbor-ip>`
2. Check BGP configuration: `show running-config bgp`
3. Check interface status: `show interface status`
4. Review BGP logs: `show logging | grep bgp`

### Configuration Not Persisting After Reboot
1. Verify `write memory` executed successfully
2. Check saved config: `show running-config`
3. Enable docker routing config mode if needed

### IPv6 Address Already Exists
The test automatically handles this by removing existing addresses during pre-test cleanup.

## Log Files
Logs are stored in the specified logs path with timestamp:
```
./logs/test_ipv6_bgp_interface_ebgp_<date>_<time>/
```

## Author
Athira
© 2025, copyrights@SuperMicro

## Related Tests
- `test_ipv6_bgp_interface.py` - iBGP with same ASN
- `test_ipv6_bgp_interface_physical.py` - Physical interface variant
- `test_ipv6_vlan_bgp_interface.py` - VLAN interface iBGP
- `test_portchannel_ipv6_bgp.py` - PortChannel interface iBGP
