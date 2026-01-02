# Verification Guide for COMPLETED IS-CLI Features

**Status**: Code changes already baselined in SM repository
**Purpose**: Verification and smoke testing of completed features

---

## Feature 1: Platform Components (SM_ISCLI_DROP1_FEATURE1)

**Status**: ✅ Done - Code baselined

### Commands to Verify

#### Platform Identification
```bash
# Basic platform information
show platform summary
show platform summary --json
show platform syseeprom
show platform syseeprom --verbose

# Help commands
show platform --help
show platform summary --help
show platform syseeprom --help
```

#### Hardware Monitoring
```bash
# PSU monitoring
show platform psustatus
show platform psustatus -i 1
show platform psustatus -i 2
show platform psustatus --json
show platform psustatus --verbose
show platform psustatus -i 1 --json --verbose

# SSD health monitoring
show platform ssdhealth
show platform ssdhealth --verbose
show platform ssdhealth --vendor
show platform ssdhealth --verbose --vendor
show platform ssdhealth /dev/sda

# PCIe device information
show platform pcieinfo
show platform pcieinfo --check
show platform pcieinfo --verbose
show platform pcieinfo --check --verbose

# Environmental monitoring
show platform fan
show platform temperature
show platform voltage
show platform current
```

#### Firmware Management
```bash
# Firmware information
show platform firmware --help
show platform firmware status
show platform firmware version
show platform firmware updates
show platform firmware update-all-status
```

### Quick Verification Script
```bash
#!/bin/bash
echo "=== Platform Summary ==="
show platform summary

echo -e "\n=== PSU Status ==="
show platform psustatus

echo -e "\n=== SSD Health ==="
show platform ssdhealth

echo -e "\n=== Temperature ==="
show platform temperature

echo -e "\n=== Fan Status ==="
show platform fan
```

### Expected Results
- ✓ All commands execute without errors
- ✓ JSON output is valid JSON format
- ✓ Verbose modes show additional details
- ✓ Help text displays properly
- ✓ Hardware status accurately reflects system state

---

## Feature 2: ZTP (SM_ISCLI_DROP1_FEATURE2)

**Status**: ✅ Done - Code baselined

### Commands to Verify

```bash
# Show ZTP status
show ztp status
show ztp status --verbose

# Enable ZTP
sudo config ztp enable

# Disable ZTP
sudo config ztp disable

# Run ZTP
sudo config ztp run

# Check ZTP configuration
show runningconfiguration all | grep -i ztp
```

### Configuration Files to Check
```bash
# ZTP configuration file
cat /etc/sonic/ztp_cfg.json

# ZTP state file
cat /var/lib/ztp/ztp.lock

# ZTP logs
tail -50 /var/log/ztp.log
```

### Quick Verification Script
```bash
#!/bin/bash
echo "=== ZTP Status ==="
show ztp status

echo -e "\n=== ZTP in Config ==="
show runningconfiguration all | grep -i ztp

echo -e "\n=== ZTP Service ==="
systemctl status ztp.service
```

### Expected Results
- ✓ `show ztp status` displays current state
- ✓ Enable/disable commands work without errors
- ✓ Configuration persists across reboots
- ✓ Status reflects actual ZTP state

### Test Scenarios
1. **Check Initial State**
   ```bash
   show ztp status
   ```

2. **Disable ZTP**
   ```bash
   sudo config ztp disable
   show ztp status  # Should show disabled
   ```

3. **Enable ZTP**
   ```bash
   sudo config ztp enable
   show ztp status  # Should show enabled
   ```

4. **Verify Persistence**
   ```bash
   # After reboot
   show ztp status  # Should match pre-reboot state
   ```

---

## Feature 3: NTP (SM_ISCLI_DROP1_FEATURE7)

**Status**: 🔄 In-Progress - Testing/Verification ongoing

### Commands to Verify

```bash
# Show NTP status
show ntp

# Add NTP server
sudo config ntp add time.google.com
sudo config ntp add --association-type server 216.239.35.0

# Add NTP pool
sudo config ntp add --association-type pool pool.ntp.org

# Delete NTP server
sudo config ntp del time.google.com

# Show running config
show runningconfiguration all | grep -i ntp
```

### VRF Management
```bash
# Add mgmt VRF (if not exists)
sudo config vrf add mgmt

# Verify mgmt VRF
ip vrf show

# Ping NTP server via VRF
sudo ip vrf exec mgmt ping -c 2 time.google.com
sudo ip vrf exec mgmt ping -c 2 8.8.8.8
```

### Chrony Integration
```bash
# Check chrony tracking
chronyc tracking

# Check NTP sources
chronyc sources
chronyc sources -v

# Check source stats
chronyc sourcestats

# Force sync (if needed)
sudo chronyc makestep
```

### CONFIG_DB Operations
```bash
# Check NTP in CONFIG_DB
redis-cli -n 4 KEYS NTP_SERVER*
redis-cli -n 4 HGETALL "NTP_SERVER|time.google.com"
redis-cli -n 4 HGETALL "NTP|global"

# List all NTP config
redis-cli -n 4 --scan --pattern "NTP*"
```

### Quick Verification Script
```bash
#!/bin/bash
echo "=== Show NTP ==="
show ntp

echo -e "\n=== Chrony Tracking ==="
chronyc tracking

echo -e "\n=== Chrony Sources ==="
chronyc sources

echo -e "\n=== NTP in CONFIG_DB ==="
redis-cli -n 4 KEYS NTP_SERVER*

echo -e "\n=== VRF Connectivity ==="
sudo ip vrf exec mgmt ping -c 2 8.8.8.8
```

### Expected Results
- ✓ Servers can be added/deleted
- ✓ Both server and pool association types work
- ✓ Configuration appears in `show ntp`
- ✓ chrony daemon reflects changes
- ✓ VRF exec works for network connectivity
- ✓ CONFIG_DB contains NTP configuration
- ✓ Time synchronization occurs

### Test Scenarios

**Scenario 1: Add and Verify NTP Server**
```bash
# Add server
sudo config ntp add time.google.com

# Verify
show ntp | grep time.google.com
chronyc sources | grep time.google.com
redis-cli -n 4 HGETALL "NTP_SERVER|time.google.com"
```

**Scenario 2: Test VRF Support**
```bash
# Verify mgmt VRF exists
ip vrf show | grep mgmt

# Test connectivity via VRF
sudo ip vrf exec mgmt ping -c 2 time.google.com
```

**Scenario 3: Verify Synchronization**
```bash
# Check sync status
chronyc tracking

# Should show:
# - Reference ID (not 0.0.0.0)
# - System time offset
# - Last offset value
```

---

## Feature 4: Clear ARP/ND (SM_ISCLI_DROP1_FEATURE8)

**Status**: 🔄 In-Progress - Unit testing ongoing

### Commands to Verify

```bash
# Show ARP table
show arp

# Clear all ARP entries
sonic-clear arp

# Show IPv6 neighbors (NDP)
show ndp

# Clear all NDP entries
sonic-clear ndp
```

### Detailed Verification
```bash
# Show ARP with count
show arp | wc -l

# Show specific interface ARP
show arp | grep Ethernet0

# Show kernel ARP table
ip neigh show
ip -4 neigh show  # IPv4 only
ip -6 neigh show  # IPv6 only

# Clear specific interface (kernel command)
sudo ip neigh flush dev Ethernet0
```

### Quick Verification Script
```bash
#!/bin/bash
echo "=== ARP Before Clear ==="
ARP_BEFORE=$(show arp | grep -c Ethernet)
echo "ARP entries: $ARP_BEFORE"
show arp | head -10

echo -e "\n=== Clearing ARP ==="
sonic-clear arp

echo -e "\n=== ARP After Clear ==="
sleep 2
ARP_AFTER=$(show arp | grep -c Ethernet)
echo "ARP entries: $ARP_AFTER"
show arp | head -10

echo -e "\n=== Generate Traffic ==="
ping -c 3 <gateway-ip>

echo -e "\n=== ARP After Traffic ==="
sleep 2
ARP_FINAL=$(show arp | grep -c Ethernet)
echo "ARP entries: $ARP_FINAL (should be repopulated)"
show arp | head -10
```

### Expected Results
- ✓ `sonic-clear arp` removes ARP entries
- ✓ `sonic-clear ndp` removes IPv6 neighbors
- ✓ Commands complete quickly (< 2 seconds)
- ✓ ARP entries repopulate after traffic
- ✓ System remains stable
- ✓ Network connectivity maintained

### Test Scenarios

**Scenario 1: Basic ARP Clear**
```bash
# 1. View current ARP
show arp

# 2. Count entries
show arp | grep -c Ethernet

# 3. Clear ARP
sonic-clear arp

# 4. Verify cleared
show arp

# 5. Generate traffic
ping -c 5 <gateway-ip>

# 6. Verify repopulation
show arp
```

**Scenario 2: NDP Clear (if IPv6 configured)**
```bash
# 1. Check IPv6 configuration
show ipv6 interface

# 2. View current NDP
show ndp

# 3. Clear NDP
sonic-clear ndp

# 4. Verify cleared
show ndp

# 5. Generate IPv6 traffic
ping6 -c 3 <ipv6-neighbor>

# 6. Verify repopulation
show ndp
```

**Scenario 3: System Stability**
```bash
# 1. Clear ARP multiple times
for i in {1..5}; do
  echo "Clear iteration $i"
  sonic-clear arp
  sleep 1
done

# 2. Verify connectivity still works
ping -c 5 8.8.8.8

# 3. Check for errors
dmesg | tail -20
```

---

## Combined Verification Workflow

### 1. Quick Smoke Test (5 minutes)
```bash
# Platform
show platform summary

# ZTP
show ztp status

# NTP
show ntp

# ARP/ND
show arp
```

### 2. Full Verification (30 minutes)

**Platform (10 min)**
```bash
show platform summary
show platform psustatus
show platform ssdhealth
show platform temperature
show platform fan
```

**ZTP (5 min)**
```bash
show ztp status
sudo config ztp disable
show ztp status
sudo config ztp enable
show ztp status
```

**NTP (10 min)**
```bash
show ntp
sudo config ntp add time.google.com
show ntp
chronyc sources
sudo config ntp del time.google.com
show ntp
```

**Clear ARP/ND (5 min)**
```bash
show arp
sonic-clear arp
show arp
ping -c 3 <gateway>
show arp
```

---

## Checklist for Each Feature

### Platform Components
- [ ] All show commands execute
- [ ] JSON output is valid
- [ ] Verbose flags work
- [ ] Help text displays
- [ ] Hardware status accurate

### ZTP
- [ ] Status command works
- [ ] Enable/disable functional
- [ ] Config persists
- [ ] Service responds correctly

### NTP
- [ ] Show NTP works
- [ ] Add server works
- [ ] Delete server works
- [ ] chrony integration works
- [ ] VRF support functional
- [ ] CONFIG_DB updated

### Clear ARP/ND
- [ ] sonic-clear arp works
- [ ] sonic-clear ndp works
- [ ] Entries clear successfully
- [ ] Repopulation occurs
- [ ] System stays stable
- [ ] No connectivity loss

---

## Issue Reporting Template

If you find issues:

**Feature**: [Platform/ZTP/NTP/Clear ARP/ND]
**Command**: [Exact command that failed]
**Expected**: [What should happen]
**Actual**: [What actually happened]
**Error Output**:
```
[Paste error here]
```
**Steps to Reproduce**:
1.
2.
3.

**Environment**:
- SONiC Version:
- Platform:
- Docker containers running:

---

**Last Updated**: 29-Dec-2025
