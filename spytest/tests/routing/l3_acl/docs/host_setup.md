# Host Environment Setup Guide for L3 ACL Testing

## Overview

This guide provides step-by-step instructions to prepare the TX and RX hosts (external Linux systems) for L3 ACL traffic generation using Scapy. These hosts must be connected to the DUT's Port1 and Port2 respectively.

## Architecture

```
┌─────────────────┐        ┌─────────────────┐
│   TX Host       │        │   RX Host       │
│ (Linux, Scapy)  │        │ (Linux, Scapy)  │
│  eth0 (10.0.0.1)│        │  eth1 (20.0.0.2)│
│ MAC: AA:AA:...01│        │ MAC: BB:BB:...02│
└────────┬────────┘        └────────┬────────┘
         │                          │
         └──────────[ DUT ]─────────┘
              Port1    Port2
```

## Prerequisites

- Ubuntu 20.04 LTS or later (or equivalent Linux distribution)
- Two separate Linux systems (or VMs) with:
  - Python 3.8+
  - Network interfaces eth0 (TX) and eth1 (RX)
  - Root/sudo access
  - Internet access for package installation
- Network cables connecting to DUT Port1 (TX) and Port2 (RX)

## Step 1: System Preparation

### 1.1 Update System Packages

```bash
sudo apt update
sudo apt upgrade -y
```

### 1.2 Install Required Tools

```bash
# Core tools
sudo apt install -y python3-pip python3-dev python3-venv

# Network tools (optional but recommended)
sudo apt install -y net-tools ethtool iputils-ping tcpdump

# Verify Python version
python3 --version  # Should be 3.8+
```

### 1.3 Check Network Interfaces

Identify which interfaces will be used for testing:

```bash
# List all network interfaces
ip link show

# Output example:
# 1: lo: <LOOPBACK,UP,LOWER_UP> ...
# 2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
# 3: eth1: <BROADCAST,MULTICAST,UP,LOWER_UP> ...
```

**Important**: If your system uses different interface names (e.g., `ens3`, `enp0s1`, `veth0`), note them for later use.

Check interface status:

```bash
ethtool eth0
# Output:
# Settings for eth0:
# ...
# Link detected: yes
```

## Step 2: Disable Firewall

ACL testing requires unrestricted network traffic. Disable local firewall rules:

### 2.1 Disable UFW (Ubuntu Firewall)

```bash
# Check UFW status
sudo ufw status

# Disable if enabled
sudo ufw disable

# Verify disabled
sudo ufw status
# Output: Status: inactive
```

### 2.2 Reset iptables Rules

```bash
# Set default policies to ACCEPT
sudo iptables -P INPUT ACCEPT
sudo iptables -P FORWARD ACCEPT
sudo iptables -P OUTPUT ACCEPT

# Clear any existing rules
sudo iptables -F
sudo iptables -X

# Verify rules cleared
sudo iptables -L
# Output should show all policies ACCEPT and empty rules
```

### 2.3 Disable SELinux (if applicable)

```bash
# Check SELinux status
getenforce

# Disable for this session
sudo setenforce 0

# Make permanent (edit /etc/selinux/config if needed)
```

## Step 3: Install Scapy

### 3.1 Install via pip

```bash
# Install Scapy system-wide (requires --break-system-packages for Python 3.10+)
sudo pip3 install scapy --break-system-packages

# Verify installation
python3 -c "from scapy.all import *; print(f'Scapy {SCAPY_VERSION} OK')"
# Output: Scapy 2.5.0 OK
```

### 3.2 Install Optional Scapy Extensions (recommended)

```bash
# For better packet crafting capabilities
sudo pip3 install graphviz pycryptodome --break-system-packages
```

### 3.3 Verify Scapy Version

Scapy 2.4.4 or later is required:

```bash
python3 -c "from scapy import __version__; print(f'Version: {__version__}')"
```

If version is older than 2.4.4, upgrade:

```bash
sudo pip3 install --upgrade scapy --break-system-packages
```

## Step 4: Configure TX Host Network Interface (eth0)

### 4.1 Configure IP Address and MAC

The TX host's eth0 must have IP 10.0.0.1/24 and MAC 00:aa:aa:aa:aa:01:

```bash
# Method 1: Using setup_ports.py (Recommended)
cd /path/to/spytest/tests/routing/l3_acl/traffic/
sudo python3 setup_ports.py

# Output:
# ============================================================
#   ACL Test Port Setup (External TX/RX Host Configuration)
# ============================================================
#
# [1] Checking available interfaces...
#     Available: ['lo', 'eth0', 'eth1']
#   [OK] TX  (eth0  ) IP=10.0.0.1      MAC=00:aa:aa:aa:aa:01
#   [OK] RX  (eth1  ) IP=20.0.0.2      MAC=00:bb:bb:bb:bb:02
#
# [2] Verifying port configuration...
#   [PASS] TX  (eth0  )  exists=True  link=True  ip=True  mac=True
#   [PASS] RX  (eth1  )  exists=True  link=True  ip=True  mac=True
```

### 4.2 Manual Configuration (Alternative)

If setup_ports.py fails, configure manually:

```bash
# Bring interface up
sudo ip link set eth0 up

# Set MAC address
sudo ip link set eth0 address 00:aa:aa:aa:aa:01

# Clear any existing IP addresses
sudo ip addr flush dev eth0

# Add new IP address
sudo ip addr add 10.0.0.1/24 dev eth0

# Verify
ip addr show eth0
ip link show eth0
```

## Step 5: Configure RX Host Network Interface (eth1)

### 5.1 Configure IP Address and MAC

The RX host's eth1 must have IP 20.0.0.2/24 and MAC 00:bb:bb:bb:bb:02, with promiscuous mode enabled:

```bash
# Method 1: Using setup_ports.py (Recommended)
cd /path/to/spytest/tests/routing/l3_acl/traffic/
sudo python3 setup_ports.py

# Verify
ip addr show eth1
ip link show eth1 | grep PROMISC  # Should see PROMISC
```

### 5.2 Manual Configuration (Alternative)

```bash
# Bring interface up
sudo ip link set eth1 up

# Set MAC address
sudo ip link set eth1 address 00:bb:bb:bb:bb:02

# Clear any existing IP addresses
sudo ip addr flush dev eth1

# Add new IP address
sudo ip addr add 20.0.0.2/24 dev eth1

# Enable promiscuous mode (required for packet sniffing)
sudo ip link set eth1 promisc on

# Verify
ip addr show eth1
ip link show eth1 | grep PROMISC
```

## Step 6: Grant Raw Socket Permissions

Scapy requires raw socket permissions. Choose one method:

### Method 1: Use sudo (Simplest)

Always run Scapy scripts with `sudo`:

```bash
sudo python3 l3_acl_traffic.py --list
```

### Method 2: Grant CAP_NET_RAW Capability (Persistent)

```bash
# Grant capability to Python interpreter
sudo setcap cap_net_raw=ep /usr/bin/python3

# Verify
getcap /usr/bin/python3
# Output: /usr/bin/python3 = cap_net_raw+ep

# Now can run without sudo
python3 l3_acl_traffic.py --list
```

**Note**: If there are multiple Python installations, grant capability to all:

```bash
which python3
# /usr/bin/python3

ls -la /usr/bin/python*
# Identify all python symlinks and executables

sudo setcap cap_net_raw=ep /usr/bin/python3.9
sudo setcap cap_net_raw=ep /usr/bin/python3.10
# ... for each version
```

## Step 7: Verify Host Configuration

### 7.1 Run Verification Script

```bash
sudo python3 setup_ports.py --verify

# Expected output:
# [PASS] TX  (eth0  )  exists=True  link=True  ip=True  mac=True
# [PASS] RX  (eth1  )  exists=True  link=True  ip=True  mac=True
```

### 7.2 Manual Verification

```bash
# Check IP addresses
ip addr show eth0  # Should show 10.0.0.1/24
ip addr show eth1  # Should show 20.0.0.2/24

# Check MAC addresses
ip link show eth0  # Should show 00:aa:aa:aa:aa:01
ip link show eth1  # Should show 00:bb:bb:bb:bb:02

# Check promiscuous mode on eth1
ip link show eth1 | grep PROMISC  # Should show PROMISC

# Check Scapy installation
python3 -c "from scapy.all import *; print('OK')"

# Check raw socket permissions
python3 -c "from scapy.all import L3RawSocket; print('OK')"
```

## Step 8: Verify Connectivity to DUT

### 8.1 Ping DUT Port1 (from TX Host)

```bash
# TX Host
ping 10.0.0.254 -c 3
# Expected: 3 packets received

# If ping fails:
# 1. Check DUT Port1 is UP and has IP 10.0.0.254/24 (see dut_setup.md)
# 2. Check physical cable is connected
# 3. Verify no local firewall is blocking ICMP
```

### 8.2 Test Scapy Packet Transmission (from TX Host)

```bash
# TX Host - send a crafted packet
sudo python3 << 'EOF'
from scapy.all import *
pkt = Ether(src='00:aa:aa:aa:aa:01', dst='00:bb:bb:bb:bb:02')/IP(src='10.0.0.1', dst='20.0.0.2')/ICMP()
sendp(pkt, iface='eth0', verbose=True)
print("Packet sent successfully")
EOF
```

### 8.3 Verify Packet Reception (from RX Host)

Run this in parallel with 8.2:

```bash
# RX Host - capture packets
sudo tcpdump -i eth1 'src 10.0.0.1' -c 1
# Expected: "1 packet captured" after ~1 second
```

If RX doesn't see packets:
1. Check DUT routing: `show ip route` (should have routes for both subnets)
2. Verify DUT Port1/Port2 are UP: `show interface status`
3. Check for dropped packets: `show interface counters`
4. Verify MTU is compatible: all devices should have MTU ≥ 1500

## Step 9: Save Configuration (Optional but Recommended)

Make the interface configuration persistent across reboots:

### 9.1 Create netplan Configuration (Ubuntu 18.04+)

Create `/etc/netplan/99-test-acl.yaml`:

```yaml
network:
  version: 2
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 10.0.0.1/24
      match:
        macaddress: 00:aa:aa:aa:aa:01
    eth1:
      dhcp4: no
      addresses:
        - 20.0.0.2/24
      match:
        macaddress: 00:bb:bb:bb:bb:02
```

Apply configuration:

```bash
sudo netplan apply
sudo netplan info  # Verify

# Revert if needed:
# sudo rm /etc/netplan/99-test-acl.yaml
# sudo netplan apply
```

### 9.2 Create /etc/rc.local Script (Alternative)

Create `/etc/rc.local`:

```bash
#!/bin/bash
# Restore ACL test configuration on boot

# TX Host
ip link set eth0 up
ip link set eth0 address 00:aa:aa:aa:aa:01
ip addr flush dev eth0
ip addr add 10.0.0.1/24 dev eth0

# RX Host
ip link set eth1 up
ip link set eth1 address 00:bb:bb:bb:bb:02
ip addr flush dev eth1
ip addr add 20.0.0.2/24 dev eth1
ip link set eth1 promisc on

exit 0
```

Make executable:

```bash
sudo chmod +x /etc/rc.local
sudo systemctl enable rc-local
```

## Troubleshooting

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Interface not found | "No such device eth0" | Run `ip link show` to find actual interface names; edit setup_ports.py or configure manually |
| Permission denied | "Operation not permitted" | Run with `sudo`; or grant CAP_NET_RAW capability |
| Firewall blocks traffic | No packets reach RX | Disable UFW: `sudo ufw disable`; flush iptables: `sudo iptables -F` |
| Scapy not installed | ImportError: scapy | `sudo pip3 install scapy --break-system-packages` |
| Interface has no link | "Link detected: no" | Check physical cable is connected; verify DUT Port1/Port2 are UP |
| RX sees 0 packets | tcpdump captures nothing | Check DUT routing; verify eth0 IP and MAC are correct |
| MTU mismatch | Packets truncated | Set MTU on both hosts: `sudo ip link set eth0 mtu 1500` |

## Quick Setup Checklist

```bash
# 1. Update system
[ ] sudo apt update && sudo apt upgrade -y

# 2. Install tools
[ ] sudo apt install -y python3-pip python3-dev net-tools ethtool tcpdump

# 3. Disable firewall
[ ] sudo ufw disable
[ ] sudo iptables -P INPUT ACCEPT
[ ] sudo iptables -F

# 4. Install Scapy
[ ] sudo pip3 install scapy --break-system-packages
[ ] python3 -c "from scapy.all import *; print('OK')"

# 5. Configure interfaces
[ ] cd /path/to/l3_acl/traffic/
[ ] sudo python3 setup_ports.py

# 6. Verify configuration
[ ] sudo python3 setup_ports.py --verify
[ ] ping 10.0.0.254 -c 3  # From TX Host

# 7. Test end-to-end connectivity
[ ] Run tcpdump on RX, send packet from TX
[ ] Verify packet is received

# All checks passed - ready to run ACL tests!
```

