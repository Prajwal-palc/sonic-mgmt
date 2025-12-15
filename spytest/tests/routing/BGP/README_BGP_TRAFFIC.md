# BGP IPv4 Traffic Validation with Scapy

## Overview

This document describes the BGP IPv4 traffic validation testcase added to `test_bgp_ipv4_basic.py`. The test validates bidirectional traffic forwarding over BGP sessions using Scapy-generated packets.

## Files Modified/Created

### New Files
1. **`apis/common/scapy_traffic.py`** - Reusable Scapy traffic generation API
   - Location: `apis/common/scapy_traffic.py`
   - Purpose: Provides reusable functions for Scapy-based traffic generation and verification
   - Reusability: Can be imported and used in any SPyTest test script

### Modified Files
1. **`tests/routing/BGP/test_bgp_ipv4_basic.py`** - Added traffic testcase
   - Test ID: `BGP_IPv4_002` - `test_bgp_ipv4_traffic_validation()`

2. **`tests/routing/BGP/vars_bgp_ipv4_basic.yaml`** - Added traffic test configuration
   - Test case section: `002`

## Scapy Traffic API

### Location
```
apis/common/scapy_traffic.py
```

### Key Functions

#### 1. `get_interface_mac(dut, interface, cli_type="klish")`
Retrieves MAC address from a specified interface.

**Returns:** MAC address string or None

**Example:**
```python
from apis.common import scapy_traffic

mac = scapy_traffic.get_interface_mac("D1", "Ethernet0")
# Returns: "52:54:00:d3:78:35"
```

#### 2. `send_traffic(dut, interface, src_ip, dst_ip, src_mac, dst_mac, duration=10, pps=1000, payload_size=200, traffic_type="udp")`
High-level function to send Scapy traffic from a device.

**Parameters:**
- `dut`: Device handle
- `interface`: Interface to send traffic on (e.g., "Ethernet0")
- `src_ip`: Source IP address
- `dst_ip`: Destination IP address
- `src_mac`: Source MAC address
- `dst_mac`: Destination MAC address
- `duration`: Traffic duration in seconds (default: 10)
- `pps`: Packets per second (default: 1000)
- `payload_size`: Payload size in bytes (default: 200)
- `traffic_type`: Traffic type - "udp", "icmp", "tcp" (default: "udp")

**Returns:** Dictionary with `success`, `output`, `packets_sent`

**Example:**
```python
result = scapy_traffic.send_traffic(
    dut="D1",
    interface="Ethernet0",
    src_ip="10.1.1.1",
    dst_ip="10.1.1.2",
    src_mac="aa:bb:cc:dd:ee:f1",
    dst_mac="aa:bb:cc:dd:ee:f2",
    duration=15,
    pps=500,
    traffic_type="udp"
)

if result["success"]:
    print(f"Sent {result['packets_sent']} packets")
```

#### 3. `verify_ping(dut, dst_ip, src_ip=None, count=5, timeout=10)`
Verifies connectivity using ping.

**Returns:** True if ping successful, False otherwise

**Example:**
```python
if scapy_traffic.verify_ping("D1", "10.1.1.2", src_ip="10.1.1.1"):
    print("Connectivity verified")
```

#### 4. `cleanup_scapy_script(dut, script_path="/tmp/scapy_traffic_sender.py")`
Removes Scapy script from device.

**Example:**
```python
scapy_traffic.cleanup_scapy_script("D1")
```

#### 5. `start_tcpdump(dut, interface, filter_str="", output_file="/tmp/tcpdump_capture.pcap", max_packets=1000)`
Starts tcpdump packet capture (non-blocking).

**Example:**
```python
scapy_traffic.start_tcpdump("D2", "Ethernet0", filter_str="udp port 54321")
# Send traffic...
scapy_traffic.stop_tcpdump("D2")
```

#### 6. `stop_tcpdump(dut)`
Stops tcpdump packet capture.

#### 7. `verify_tcpdump_capture(dut, capture_file="/tmp/tcpdump_capture.pcap", min_packets=1)`
Verifies tcpdump capture and checks packet count.

**Returns:** Dictionary with `success`, `packet_count`, `output`

### Additional Utility Functions
- `get_default_mac(dut_index)`: Generates default MAC address
- `create_scapy_script(...)`: Creates Scapy script on device

## Test Case: BGP_IPv4_002

### Test ID
`test_bgp_ipv4_traffic_validation`

### Description
Validates BGP IPv4 bidirectional traffic forwarding using Scapy-generated packets.

### Test Steps

1. **Configure Interface IP Addresses**
   - DUT1: Configures IP on interface connected to DUT2
   - DUT2: Configures IP on interface connected to DUT1

2. **Configure BGP Routers**
   - Establishes BGP routers on both DUTs with AS numbers and Router IDs

3. **Configure BGP Neighbors**
   - Configures neighbor relationships between DUT1 and DUT2

4. **Activate BGP Neighbors**
   - Activates neighbors in IPv4 unicast address family

5. **Verify BGP Session Establishment**
   - Verifies BGP sessions reach "Established" state

6. **Verify Basic Connectivity**
   - Uses ping to verify basic IP connectivity

7. **Get MAC Addresses**
   - Retrieves MAC addresses from interfaces on both DUTs
   - Falls back to default MACs if retrieval fails

8. **Send Bidirectional Scapy Traffic**
   - **DUT1 → DUT2**: Sends UDP traffic from DUT1 to DUT2
   - **DUT2 → DUT1**: Sends UDP traffic from DUT2 to DUT1

9. **Verify Traffic Forwarding**
   - Uses post-traffic ping to verify connectivity maintained

10. **Unconfigure BGP**
    - Removes BGP configuration from both DUTs

11. **Unconfigure IP Addresses**
    - Removes IP addresses from interfaces

### Test Configuration (YAML)

The test configuration is defined in `vars_bgp_ipv4_basic.yaml`:

```yaml
"002":
  title: "BGP IPv4 traffic forwarding validation using Scapy"

  dut1:
    ip_address: "192.168.10.1"
    subnet: "24"
    bgp_asn: 65100
    router_id: "1.1.1.1"
    neighbor_ip: "192.168.10.2"
    remote_asn: 65100

  dut2:
    ip_address: "192.168.10.2"
    subnet: "24"
    bgp_asn: 65100
    router_id: "2.2.2.2"
    neighbor_ip: "192.168.10.1"
    remote_asn: 65100

  traffic:
    duration: 10          # Traffic duration in seconds
    pps: 1000             # Packets per second
    payload_size: 200     # Payload size in bytes
    type: "udp"           # Traffic type: udp, icmp, or tcp
```

## Running the Test

### Using testbed_vs_2node.yaml (2-node topology)

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_ipv4_basic.py::TestBgpIpv4Basic::test_bgp_ipv4_traffic_validation \
  --logs-path ./logs/test_bgp_traffic_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

### Run All BGP IPv4 Basic Tests

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_ipv4_basic.py \
  --logs-path ./logs/test_bgp_basic_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

## Topology Requirements

### Minimum Topology
- **2 DUTs** (D1, D2) with **1 link** between them (D1D2:1)
- Both DUTs must support klish CLI mode
- Python3 and Scapy must be installed on both DUTs

### Topology Diagram

```
+--------------------+                       +--------------------+
|        DUT1        |                       |        DUT2        |
|  192.168.10.1/24   |=======================|  192.168.10.2/24   |
| BGP AS 65100       |      D1D2P1-D2D1P1   | BGP AS 65100       |
| Router-ID 1.1.1.1  |                       | Router-ID 2.2.2.2  |
+--------------------+                       +--------------------+
         |                                             |
         |                                             |
         +--------- Scapy Traffic (Bidirectional) -----+
```

## Expected Results

### Success Criteria
1. BGP sessions establish successfully on both DUTs
2. Ping connectivity verified before and after traffic
3. Scapy traffic sent successfully in both directions
4. Minimum expected packet count achieved (configurable in YAML)

### Output Example

```
================================================================================
TEST CASE: BGP IPv4 Traffic Validation with Scapy
================================================================================

Step 1: Configure interface IP addresses
Step 2: Configure BGP routers
Step 3: Configure BGP neighbors
Step 4: Activate neighbors in IPv4 unicast address family
Step 5: Verify BGP session establishment
Step 6: Verify basic connectivity with ping
Step 7: Get MAC addresses from interfaces
Step 8: Send bidirectional Scapy traffic
  - Sending traffic from DUT1 (192.168.10.1) to DUT2 (192.168.10.2)
  - Traffic sent successfully: 10000 packets
  - Sending traffic from DUT2 (192.168.10.2) to DUT1 (192.168.10.1)
  - Traffic sent successfully: 10000 packets
Step 9: Verify traffic forwarding
  - PASS: Traffic forwarding verified successfully

================================================================================
Traffic Test Summary
================================================================================
DUT1 -> DUT2: 10000 packets sent
DUT2 -> DUT1: 10000 packets sent
Total packets: 20000
```

## Customizing Traffic Parameters

You can customize traffic parameters in the YAML file:

```yaml
traffic:
  duration: 15          # Increase duration to 15 seconds
  pps: 500              # Reduce to 500 packets per second
  payload_size: 500     # Increase payload to 500 bytes
  type: "icmp"          # Change to ICMP traffic
```

Supported traffic types:
- **udp**: UDP packets with random payload (default)
- **icmp**: ICMP echo request packets
- **tcp**: TCP packets with random payload

## Reusing Scapy API in Other Tests

The Scapy traffic API is designed to be reusable across different test scripts:

### Example Usage in a New Test

```python
from spytest import st
import apis.common.scapy_traffic as scapy_api

def test_my_feature_with_traffic():
    # Get topology
    vars = st.ensure_min_topology("D1D2:1")

    # Configure IPs (using your feature's API)
    # ...

    # Get MAC addresses
    dut1_mac = scapy_api.get_interface_mac(vars.D1, vars.D1D2P1)
    dut2_mac = scapy_api.get_interface_mac(vars.D2, vars.D2D1P1)

    # Send traffic
    result = scapy_api.send_traffic(
        dut=vars.D1,
        interface=vars.D1D2P1,
        src_ip="10.0.0.1",
        dst_ip="10.0.0.2",
        src_mac=dut1_mac,
        dst_mac=dut2_mac,
        duration=5,
        pps=100
    )

    # Verify
    if result["success"]:
        st.log(f"Traffic test passed: {result['packets_sent']} packets")

    # Cleanup
    scapy_api.cleanup_scapy_script(vars.D1)
```

## Troubleshooting

### Issue: MAC Address Not Retrieved

**Symptom:** Test uses default MAC addresses

**Solution:**
- Check interface is up: `show interface <interface>`
- Verify klish CLI type is supported on device
- Default MACs will be used automatically as fallback

### Issue: Scapy Script Execution Fails

**Symptom:** "Scapy script execution failed" in logs

**Possible Causes:**
1. Python3 not installed on DUT
2. Scapy module not installed on DUT
3. Insufficient permissions (needs sudo)

**Solution:**
```bash
# On DUT:
sudo apt-get install python3-scapy
# or
sudo pip3 install scapy
```

### Issue: Traffic Not Forwarded

**Symptom:** Ping fails after configuration

**Debug Steps:**
1. Check BGP session state: `show ip bgp summary`
2. Check interface status: `show ip interfaces`
3. Check routing table: `show ip route`
4. Verify IP addresses are correctly configured

## Design Principles

### No Hardcoding
- All IPs, MACs, and interfaces are dynamically resolved from topology
- Test parameters configured in YAML file
- MAC addresses retrieved from actual devices (with fallback to defaults)

### Reusability
- Scapy API placed in `apis/common/` for use across all tests
- Functions accept parameters for flexibility
- Clean separation between API and test logic

### Topology Flexibility
- Uses `testbed_vs_2node.yaml` as base topology
- Compatible with any 2-node topology (D1D2:1)
- Supports both virtual and hardware devices

### Clean Separation
- Test logic in test file (`test_bgp_ipv4_basic.py`)
- Traffic API in separate module (`scapy_traffic.py`)
- Configuration in YAML file (`vars_bgp_ipv4_basic.yaml`)

## Future Enhancements

1. **Advanced Traffic Patterns**
   - Support for multiple traffic streams
   - Variable packet sizes
   - Different traffic types in single test

2. **Enhanced Verification**
   - tcpdump-based packet capture and analysis
   - Packet loss calculation
   - Latency measurements

3. **Multi-node Support**
   - Extend to 4-node topology from `testbed_vs_4node.yaml`
   - Support for additional hosts as traffic generators

## References

- Original Scapy implementation: `~/Athira/iscli_Vlan/scapy_traffic_sender.py`
- Reference test: `~/Athira/iscli_Vlan/test_interface_4_scapy_direct_traffic.py`
- SPyTest framework documentation: `Doc/intro.md`
- BGP API: `apis/routing/bgp.py`

## Author

Test Engineering Team
Copyright (C) 2025

---

**Note:** This implementation follows SPyTest coding guidelines and maintains consistency with the existing test framework structure.
