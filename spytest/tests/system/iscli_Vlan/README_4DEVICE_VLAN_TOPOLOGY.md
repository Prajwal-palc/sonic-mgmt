# 4-Device VLAN Topology Test Suite

Comprehensive test suite for validating VLAN functionality, Port-Channel aggregation, and traffic forwarding across a 4-device SONiC topology.

## Table of Contents

- [Overview](#overview)
- [Topology](#topology)
- [Components](#components)
- [Quick Start](#quick-start)
- [Traffic Generation](#traffic-generation)
- [Test Scenarios](#test-scenarios)
- [Device Configuration](#device-configuration)
- [Troubleshooting](#troubleshooting)

---

## Overview

This test suite validates:

- **VLAN 10**: Untagged/access port traffic
- **VLAN 20**: Tagged/trunk port traffic
- **Port-Channel 50 (LAG)**: Link aggregation between D1-D2 and D3-D4
- **Traffic patterns**: Unicast, broadcast, multicast, and load-balancing

### Technology Stack

- **Framework**: SPyTest (SONiC Python Test Framework)
- **Traffic Generator**: Scapy
- **CLI Types**: Klish (default), Click, REST
- **Languages**: Python 3.8+

---

## Topology

### Device Layout

```
        D1 (.217) ─────────── D2 (.142)
         │                      │
    VLAN10 (untagged)      VLAN10 (untagged)
    VLAN20 (tagged)        VLAN20 (tagged)
    LAG50 (Eth8,12)        LAG50 (Eth24,28)
                                │
                                │
                                D4 (.54)
                                │
                                │
        D3 (.105) ──────────────┘
         │
    VLAN10 (untagged)
    VLAN20 (tagged)
    LAG50 (Eth40,44)
```

### Device Information

| Device | IP Address        | Role                  |
|--------|-------------------|-----------------------|
| D1     | 192.168.100.217   | Source/Edge device    |
| D2     | 192.168.100.142   | Transit device        |
| D3     | 192.168.100.105   | Source/Edge device    |
| D4     | 192.168.100.54    | Central distribution  |

**Credentials**: `admin / YourPaSsWoRd`

### Interface Connections

#### D1 ↔ D2 Links

| D1 Interface | D2 Interface | Type        | VLAN       |
|--------------|--------------|-------------|------------|
| Ethernet0    | Ethernet0    | Access      | VLAN 10    |
| Ethernet4    | Ethernet4    | Trunk       | VLAN 20    |
| Ethernet8    | Ethernet24   | LAG50 Member| VLAN 20    |
| Ethernet12   | Ethernet28   | LAG50 Member| VLAN 20    |

#### D2 ↔ D4 Links

| D2 Interface | D4 Interface | Type        | VLAN       |
|--------------|--------------|-------------|------------|
| Ethernet16   | Ethernet32   | Access      | VLAN 10    |
| Ethernet20   | Ethernet36   | Trunk       | VLAN 20    |

#### D3 ↔ D4 Links

| D3 Interface | D4 Interface | Type        | VLAN       |
|--------------|--------------|-------------|------------|
| Ethernet32   | Ethernet16   | Access      | VLAN 10    |
| Ethernet36   | Ethernet20   | Trunk       | VLAN 20    |
| Ethernet40   | Ethernet24   | LAG50 Member| VLAN 20    |
| Ethernet44   | Ethernet28   | LAG50 Member| VLAN 20    |

---

## Components

### 1. Configuration Files

**`vars_4device_vlan_topology.yaml`**
- Location: `spytest/vars/system/iscli_Vlan/`
- Contains: Device IPs, interface mappings, VLAN config, traffic scenarios

### 2. Main Test Script

**`test_4device_vlan_topology.py`**
- Location: `tests/system/iscli_Vlan/`
- Functions:
  - Module-level setup/teardown
  - VLAN creation and configuration
  - Access/trunk port configuration
  - Port-Channel setup
  - Configuration verification tests

### 3. Scapy Traffic Generators

| Script                       | Purpose                                    |
|------------------------------|--------------------------------------------|
| `traffic_vlan10_untagged.py` | Generate untagged VLAN10 traffic           |
| `traffic_vlan20_tagged.py`   | Generate 802.1Q tagged VLAN20 traffic      |
| `traffic_portchannel.py`     | Generate traffic for LAG load balancing    |

### 4. Orchestration Script

**`run_all_traffic_tests.py`**
- Runs all traffic scenarios in sequence
- Generates summary report
- Saves results to YAML file

---

## Quick Start

### Prerequisites

```bash
# Install Scapy
pip install scapy

# Verify Python version
python3 --version  # Should be 3.8+

# Verify you're in spytest directory
pwd  # Should end with /sonic-mgmt/spytest
```

### Step 1: Run SPyTest Configuration Tests

```bash
cd /home/adminuser/draksha/sonic-mgmt/spytest

# Run full test suite
./bin/spytest --testbed ./testbeds/testbed_4d.yaml \
  tests/system/iscli_Vlan/test_4device_vlan_topology.py \
  --logs-path ./logs/vlan_topo_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native
```

### Step 2: Run Traffic Generation Tests

After configuration tests pass, run traffic generation:

```bash
cd tests/system/iscli_Vlan

# Run all traffic tests
sudo python3 run_all_traffic_tests.py --interface eth0 --scenario all

# Quick test (reduced packet counts)
sudo python3 run_all_traffic_tests.py --interface eth0 --quick-test

# Run specific scenario only
sudo python3 run_all_traffic_tests.py --interface eth0 --scenario vlan10_only
```

---

## Traffic Generation

### Standalone Traffic Scripts

#### VLAN10 Untagged Traffic

```bash
# Unicast traffic
sudo python3 traffic_vlan10_untagged.py \
  --iface eth0 \
  --mode unicast \
  --dst-mac 00:11:22:33:44:02 \
  --count 100

# Broadcast traffic
sudo python3 traffic_vlan10_untagged.py \
  --iface eth0 \
  --mode broadcast \
  --count 50
```

#### VLAN20 Tagged Traffic

```bash
# Unicast tagged
sudo python3 traffic_vlan20_tagged.py \
  --iface eth0 \
  --mode unicast \
  --vlan 20 \
  --dst-mac 00:11:22:33:55:02 \
  --count 100

# Broadcast tagged
sudo python3 traffic_vlan20_tagged.py \
  --iface eth0 \
  --mode broadcast \
  --vlan 20 \
  --count 50

# Multicast tagged
sudo python3 traffic_vlan20_tagged.py \
  --iface eth0 \
  --mode multicast \
  --vlan 20 \
  --dst-mac 01:00:5e:00:00:01 \
  --count 50
```

#### Port-Channel Traffic

```bash
# Unicast via LAG
sudo python3 traffic_portchannel.py \
  --iface eth0 \
  --mode unicast \
  --dst-mac 00:11:22:33:55:02 \
  --count 200

# Load-balance test (500 flows)
sudo python3 traffic_portchannel.py \
  --iface eth0 \
  --mode load-balance \
  --dst-mac 00:11:22:33:55:02 \
  --count 500

# Varied packet sizes
sudo python3 traffic_portchannel.py \
  --iface eth0 \
  --mode varied-size \
  --dst-mac 00:11:22:33:55:02 \
  --count 300
```

### Traffic Script Options

| Option          | Description                              | Default |
|-----------------|------------------------------------------|---------|
| `--iface`       | Network interface to send traffic on     | (required) |
| `--mode`        | Traffic mode (unicast/broadcast/etc)     | (required) |
| `--vlan`        | VLAN ID for tagged traffic               | 20      |
| `--src-mac`     | Source MAC address                       | Interface MAC |
| `--dst-mac`     | Destination MAC address                  | (depends on mode) |
| `--count`       | Number of packets to send                | 100     |
| `--size`        | Packet size in bytes                     | 64      |
| `--interval`    | Interval between packets (seconds)       | 0.01    |
| `--priority`    | 802.1p priority (0-7, tagged only)       | 0       |

---

## Test Scenarios

### Configuration Tests

| Test Case       | Description                                      |
|-----------------|--------------------------------------------------|
| TC_VLAN_TOPO_001 | Verify VLAN10 untagged unicast traffic D1→D2    |
| TC_VLAN_TOPO_002 | Verify VLAN10 untagged broadcast traffic        |
| TC_VLAN_TOPO_003 | Verify VLAN20 tagged unicast traffic D1→D2      |
| TC_VLAN_TOPO_004 | Verify VLAN20 tagged broadcast traffic          |
| TC_VLAN_TOPO_005 | Verify Port-Channel unicast traffic via LAG50   |
| TC_VLAN_TOPO_006 | Verify Port-Channel broadcast traffic via LAG50 |
| TC_VLAN_TOPO_007 | Verify VLAN10 traffic D2→D4                     |
| TC_VLAN_TOPO_008 | Verify VLAN20 traffic D2→D4                     |
| TC_VLAN_TOPO_009 | Verify VLAN10 traffic D3→D4                     |
| TC_VLAN_TOPO_010 | Verify VLAN20 traffic D3→D4 via LAG50           |

### Traffic Tests

| Scenario                  | VLAN  | Type        | Packets | Purpose                    |
|---------------------------|-------|-------------|---------|----------------------------|
| untagged_unicast          | 10    | Unicast     | 100     | L2 forwarding validation   |
| untagged_broadcast        | 10    | Broadcast   | 50      | Flooding validation        |
| tagged_unicast            | 20    | Unicast     | 100     | VLAN tag preservation      |
| tagged_broadcast          | 20    | Broadcast   | 50      | Tagged flooding            |
| portchannel_unicast       | 20    | Unicast     | 200     | LAG forwarding             |
| portchannel_broadcast     | 20    | Broadcast   | 100     | LAG broadcast forwarding   |
| portchannel_load_balance  | 20    | Varied flows| 500     | Hash distribution testing  |

---

## Device Configuration

### VLAN Configuration

The test suite automatically configures:

```bash
# On all devices (D1, D2, D3, D4):

# Create VLANs
config vlan add 10
config vlan add 20

# Configure access ports (example D1-D2 VLAN10):
config vlan member add 10 Ethernet0 -u  # Untagged

# Configure trunk ports (example D1-D2 VLAN20):
config vlan member add 20 Ethernet4  # Tagged
```

### Port-Channel Configuration

```bash
# D1 LAG50 setup:
config portchannel add PortChannel50
config portchannel member add PortChannel50 Ethernet8
config portchannel member add PortChannel50 Ethernet12
config vlan member add 20 PortChannel50  # Tagged

# D2 LAG50 setup:
config portchannel add PortChannel50
config portchannel member add PortChannel50 Ethernet24
config portchannel member add PortChannel50 Ethernet28
config vlan member add 20 PortChannel50  # Tagged

# Similar configuration for D3-D4
```

### Manual Verification Commands

```bash
# Show VLAN configuration
show vlan config

# Show VLAN members
show vlan brief

# Show Port-Channel status
show interfaces portchannel

# Show Port-Channel members
show interfaces portchannel 50

# Show MAC address table
show mac

# Show interface counters
show interfaces counters
```

---

## File Structure

```
sonic-mgmt/spytest/
│
├── tests/system/iscli_Vlan/
│   ├── test_4device_vlan_topology.py       # Main test script
│   ├── traffic_vlan10_untagged.py          # VLAN10 traffic generator
│   ├── traffic_vlan20_tagged.py            # VLAN20 traffic generator
│   ├── traffic_portchannel.py              # Port-Channel traffic generator
│   ├── run_all_traffic_tests.py            # Orchestration script
│   └── README_4DEVICE_VLAN_TOPOLOGY.md     # This file
│
└── vars/system/iscli_Vlan/
    └── vars_4device_vlan_topology.yaml     # Configuration data
```

---

## Troubleshooting

### Common Issues

#### 1. Permission Denied (Scapy)

```bash
# Error: Operation not permitted
# Solution: Run with sudo
sudo python3 traffic_vlan10_untagged.py ...
```

#### 2. Module Not Found

```bash
# Error: ModuleNotFoundError: No module named 'scapy'
# Solution: Install Scapy
pip install scapy
```

#### 3. Interface Not Found

```bash
# Error: Interface eth0 not found
# Solution: List available interfaces and use correct name
ip link show
# Use correct interface name (e.g., eth1, enp0s3, etc.)
```

#### 4. VLAN Already Exists

```bash
# Error: VLAN 10 already exists
# Solution: Delete and recreate, or skip creation
config vlan del 10
config vlan add 10
```

#### 5. Port-Channel Member Add Failed

```bash
# Error: Interface already member of another port-channel
# Solution: Remove from old port-channel first
config portchannel member del PortChannelXX EthernetYY
config portchannel member add PortChannel50 EthernetYY
```

### Verification Steps

1. **Check Device Connectivity**

```bash
# Ping all devices
ping 192.168.100.217  # D1
ping 192.168.100.142  # D2
ping 192.168.100.105  # D3
ping 192.168.100.54   # D4
```

2. **Verify VLAN Creation**

```bash
# On each device
show vlan config | grep -E "10|20"
```

3. **Verify Port-Channel Status**

```bash
# Should show "Up" status
show interfaces portchannel 50
```

4. **Check Traffic Counters**

```bash
# Before traffic
show interfaces counters

# Send traffic
sudo python3 traffic_vlan10_untagged.py --iface eth0 --mode unicast --dst-mac 00:11:22:33:44:02 --count 100

# After traffic (counters should increment)
show interfaces counters
```

### Logs and Results

**SPyTest Logs**: `logs/vlan_topo_<timestamp>/`
- `dlog-D1-*.log` - Device command logs
- `module_test_4device_vlan_topology.log` - Test execution logs
- `results.html` - HTML test report

**Traffic Test Results**: `traffic_test_results_<timestamp>.yaml`
- Contains pass/fail status for each traffic scenario
- Includes timing and error information

---

## Advanced Usage

### Custom MAC Addresses

Edit `vars_4device_vlan_topology.yaml` to customize MAC addresses:

```yaml
interfaces:
  D1_D2_vlan10_untagged:
    D1_mac: "aa:bb:cc:dd:ee:01"
    D2_mac: "aa:bb:cc:dd:ee:02"
```

### Custom Packet Counts

Edit traffic scenarios in YAML:

```yaml
traffic_scenarios:
  untagged_unicast:
    packet_count: 1000  # Increase from 100
```

### Remote Traffic Generation

To run traffic from device D1 directly:

```bash
# SSH to D1
ssh admin@192.168.100.217

# Copy traffic script
scp traffic_vlan10_untagged.py admin@192.168.100.217:/tmp/

# Run traffic on D1
sudo python3 /tmp/traffic_vlan10_untagged.py --iface Ethernet0 --mode unicast --dst-mac <D2_MAC> --count 100
```

---

## References

- [SONiC Documentation](https://github.com/sonic-net/SONiC/wiki)
- [SPyTest Framework Documentation](../../../Doc/intro.md)
- [Scapy Documentation](https://scapy.readthedocs.io/)
- [IEEE 802.1Q VLAN Tagging](https://standards.ieee.org/standard/802_1Q-2018.html)

---

## Support

For issues or questions:

1. Check logs in `logs/vlan_topo_<timestamp>/`
2. Review this README troubleshooting section
3. Verify device configuration manually
4. Check network connectivity between devices

---

**Last Updated**: 2024-12-01
**Version**: 1.0
**Author**: SPyTest Framework / Claude Code
