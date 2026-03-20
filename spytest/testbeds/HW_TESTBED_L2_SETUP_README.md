# Hardware Testbed L2 ACL Setup Guide

## Overview

This guide explains how to configure the hardware testbed (`testbed_acl_hw.yaml`) for L2 ACL testing. The configuration script converts the testbed from L3 routing mode to L2 switching mode (VLAN-based).

## Testbed Information

### Devices

| Device | Hostname | IP Address | Platform | ASIC | Interface | Role |
|--------|----------|------------|----------|------|-----------|------|
| **D1 (8011)** | sonic | 192.168.100.119 | Supermicro SSE-T8196 | Broadcom | Ethernet272, Ethernet513 | ACL Device (DUT) |
| **D2 (8023)** | sonic | 192.168.100.140 | Celestica DS3000 | Broadcom | Ethernet64 | TX Traffic Generator |
| **D3 (8010)** | sonic | 192.168.100.173 | Supermicro SSE-T8164 | Broadcom | Ethernet513 | RX Traffic Receiver |

### Topology

```
┌──────────────┐                    ┌──────────────┐                    ┌──────────────┐
│   DUT2       │                    │   DUT1       │                    │   DUT3       │
│  (TX Host)   │                    │ (ACL Device) │                    │  (RX Host)   │
│    8023      │                    │    8011      │                    │    8010      │
│              │                    │              │                    │              │
│ Ethernet64 ◄─┼────────────────────┼─ Ethernet272 │                    │              │
│ VLAN 100     │                    │ VLAN 100     │                    │              │
│              │   (L2 switching)   │ (ACL ingress)│                    │              │
│              │                    │              │                    │              │
│              │                    │ Ethernet513──┼────────────────────┼──► Ethernet513
│              │                    │ VLAN 100     │   (L2 switching)   │ VLAN 100     │
│              │                    │ (egress)     │                    │              │
└──────────────┘                    └──────────────┘                    └──────────────┘
```

### Physical Connections

- **Link 1 (TX):** D2:Ethernet64 ↔ D1:Ethernet272
- **Link 2 (RX):** D1:Ethernet513 ↔ D3:Ethernet513

## Prerequisites

1. **Access to all devices:**
   - D1: `ssh admin@192.168.100.119` (password: `sonic@123`)
   - D2: `ssh admin@192.168.100.140` (password: `broadcom`)
   - D3: `ssh admin@192.168.100.173` (password: `sonic@123`)

2. **Required tools:**
   ```bash
   sudo apt-get install sshpass
   ```

3. **Current state:**
   - Devices are in L3 routing mode with IP addresses configured
   - Need to convert to L2 switching mode (VLAN 100)

## Configuration Script

### Location

```bash
/home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest/testbeds/configure_hw_testbed_l2.sh
```

### What the Script Does

The script performs the following operations on all three devices:

1. **Backup current configuration** (saved to timestamped directory)
2. **Shutdown interfaces** to prepare for reconfiguration
3. **Remove IP addresses** from interfaces
4. **Remove interfaces from routing mode** (CONFIG_DB INTERFACE table)
5. **Create VLAN 100** on all devices
6. **Add interfaces to VLAN 100** (untagged mode)
7. **Bring interfaces back up**
8. **Save configuration** to persist changes
9. **Verify configuration** and show status

### Device-Specific Configuration

#### D1 (ACL Device - 192.168.100.119)
- Creates VLAN 100
- Adds Ethernet272 (ingress from D2) to VLAN 100
- Adds Ethernet513 (egress to D3) to VLAN 100
- ACL rules will be applied ingress on Ethernet272

#### D2 (TX Generator - 192.168.100.140)
- Creates VLAN 100
- Adds Ethernet64 (connected to D1) to VLAN 100
- Will send Scapy traffic from this interface

#### D3 (RX Receiver - 192.168.100.173)
- Creates VLAN 100
- Adds Ethernet513 (connected to D1) to VLAN 100
- Will capture traffic using tcpdump on this interface

## Usage

### Step 1: Navigate to Testbed Directory

```bash
cd /home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest/testbeds
```

### Step 2: Run Configuration Script

```bash
./configure_hw_testbed_l2.sh
```

### Step 3: Review Output

The script will display:
- ✅ Device connectivity verification
- ✅ Configuration backup location
- ✅ Step-by-step configuration progress
- ✅ VLAN status verification
- ✅ Final topology summary

### Expected Output

```
╔════════════════════════════════════════════════════════════════════╗
║  Hardware Testbed L2 ACL Pre-Configuration Script                  ║
╚════════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════════╗
║  Verifying Device Connectivity                                      ║
╚════════════════════════════════════════════════════════════════════╝

[STEP] Checking D1 (192.168.100.119)...
[INFO] D1 is reachable
[STEP] Checking D2 (192.168.100.140)...
[INFO] D2 is reachable
[STEP] Checking D3 (192.168.100.173)...
[INFO] D3 is reachable

[INFO] All devices are reachable!

╔════════════════════════════════════════════════════════════════════╗
║  Backing Up Current Configuration                                   ║
╚════════════════════════════════════════════════════════════════════╝

[INFO] Configuration backups saved to: ./hw_testbed_backups_20260318_183045

╔════════════════════════════════════════════════════════════════════╗
║  Configuring D1 (ACL Device) - 192.168.100.119                      ║
╚════════════════════════════════════════════════════════════════════╝

[INFO] D1 configured successfully

... (similar for D2 and D3)

╔════════════════════════════════════════════════════════════════════╗
║  Configuration Summary                                               ║
╚════════════════════════════════════════════════════════════════════╝

Hardware Testbed L2 ACL Configuration Complete!
```

## Verification

### Check VLAN Configuration

**On D1:**
```bash
ssh admin@192.168.100.119
show vlan brief
```

Expected output:
```
+-----------+--------------+---------------------+----------------+-------------+
|   VLAN ID | IP Address   | Ports               | Port Tagging   | Proxy ARP   |
+===========+==============+=====================+================+=============+
|       100 |              | Ethernet272         | untagged       | disabled    |
|           |              | Ethernet513         | untagged       | disabled    |
+-----------+--------------+---------------------+----------------+-------------+
```

**On D2:**
```bash
ssh admin@192.168.100.140
show vlan brief
```

Expected output:
```
+-----------+--------------+---------------------+----------------+-------------+
|   VLAN ID | IP Address   | Ports               | Port Tagging   | Proxy ARP   |
+===========+==============+=====================+================+=============+
|       100 |              | Ethernet64          | untagged       | disabled    |
+-----------+--------------+---------------------+----------------+-------------+
```

**On D3:**
```bash
ssh admin@192.168.100.173
show vlan brief
```

Expected output:
```
+-----------+--------------+---------------------+----------------+-------------+
|   VLAN ID | IP Address   | Ports               | Port Tagging   | Proxy ARP   |
+===========+==============+=====================+================+=============+
|       100 |              | Ethernet513         | untagged       | disabled    |
+-----------+--------------+---------------------+----------------+-------------+
```

### Check Interface Status

```bash
# On D1
show interface status Ethernet272
show interface status Ethernet513

# On D2
show interface status Ethernet64

# On D3
show interface status Ethernet513
```

All interfaces should show:
- **Vlan:** 100 (not "routed")
- **Oper:** up
- **Admin:** up

## Running L2 ACL Tests

### Option 1: Run Automated Test Suite

```bash
cd /home/hp_test/Athira/Palc-sonic/sonic-mgmt/spytest

./bin/spytest --testbed testbeds/testbed_acl_hw.yaml \
    tests/switching/l2_acl/test_l2_acl.py \
    --logs-path ./logs/l2_acl_hw_$(date +%F_%H%M%S) \
    --log-level info
```

### Option 2: Run Manual L2-03 Test (Destination MAC Deny)

This test validates that destination MAC ACL filtering works on hardware (unlike Virtual Switch):

1. **Configure ACL on D1:**
   ```bash
   ssh admin@192.168.100.119
   sudo config acl add table L2_ACL_TEST_DEST_DENY L2 -p Ethernet272 -s ingress
   sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_DEST_DENY|RULE_1" "PRIORITY" "10"
   sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_DEST_DENY|RULE_1" "PACKET_ACTION" "DROP"
   sudo sonic-db-cli CONFIG_DB HSET "ACL_RULE|L2_ACL_TEST_DEST_DENY|RULE_1" "DST_MAC" "00:BB:BB:BB:BB:02/FF:FF:FF:FF:FF:FF"
   sudo config save -y
   ```

2. **Start tcpdump on D3:**
   ```bash
   ssh admin@192.168.100.173
   sudo tcpdump -i Ethernet513 'ether dst 00:bb:bb:bb:bb:02' -w /tmp/l2_03_hw_test.pcap -c 20 &
   ```

3. **Send traffic from D2:**
   ```bash
   ssh admin@192.168.100.140
   # Create Scapy script and send 10 packets with destination MAC 00:bb:bb:bb:bb:02
   ```

4. **Verify on D3:**
   ```bash
   ssh admin@192.168.100.173
   sudo killall tcpdump
   sudo python3 -c "from scapy.all import rdpcap; print(f'Captured: {len(rdpcap(\"/tmp/l2_03_hw_test.pcap\"))} packets')"
   ```

   **Expected result on hardware:** `Captured: 0 packets` (100% blocked)
   **Comparison to Virtual Switch:** Virtual Switch captured 10 packets (0% blocked)

## Troubleshooting

### Issue: Interfaces not showing in VLAN

**Solution:** Check if interfaces are still in routed mode
```bash
show interface status | grep -E 'Ethernet272|Ethernet513|Ethernet64'
```

If "Vlan" column shows "routed", the VLAN member addition didn't work. Try:
```bash
sudo sonic-db-cli CONFIG_DB HGETALL "VLAN_MEMBER|Vlan100|Ethernet272"
```

### Issue: Interfaces are down

**Solution:**
```bash
sudo config interface startup Ethernet272
sudo config interface startup Ethernet513
sudo config interface startup Ethernet64  # on respective devices
```

### Issue: Configuration not persisting

**Solution:**
```bash
sudo config save -y
sudo config reload -y
```

## Restoring L3 Configuration

To restore the original L3 routing configuration, configuration backups are saved in timestamped directories:

```bash
ls -lt hw_testbed_backups_*
```

To manually restore L3 mode:

```bash
# Example for D1
ssh admin@192.168.100.119

# Remove VLAN configuration
sudo config vlan member del 100 Ethernet272
sudo config vlan member del 100 Ethernet513
sudo config vlan del 100

# Re-add IP addresses
sudo config interface ip add Ethernet272 10.1.1.2/24
sudo config interface ip add Ethernet513 10.1.2.1/24

# Save configuration
sudo config save -y
```

## Platform Comparison: Hardware vs Virtual Switch

| Feature | Hardware (Broadcom ASIC) | Virtual Switch (vs) |
|---------|-------------------------|---------------------|
| **L2 ACL Table Creation** | ✅ Supported | ✅ Supported |
| **Source MAC Filtering** | ✅ Supported | ✅ Supported |
| **Destination MAC Filtering** | ✅ **Supported** | ❌ **NOT Supported** |
| **Hardware TCAM Enforcement** | ✅ Available | ❌ Not Available |
| **High-Performance Filtering** | ✅ Full Support | ⚠️ Limited |

**Key Difference:** Hardware platforms with Broadcom ASICs support both source and destination MAC ACL filtering, while Virtual Switch only supports source MAC filtering.

## References

- **Testbed File:** `testbeds/testbed_acl_hw.yaml`
- **Configuration Script:** `testbeds/configure_hw_testbed_l2.sh`
- **L2-03 Manual Test:** `tests/switching/l2_acl/manual_test/L2-03_manual_log.md`
- **Virtual Switch Test Results:** `tests/switching/l2_acl/report/l2-01-log.md` (L2-03 on VS - platform limitation documented)

---

**Document Version:** 1.0
**Last Updated:** 2026-03-18
**Status:** Ready for use
**Platform:** Hardware SONiC Switches (Broadcom ASIC)
