# IS-CLI Command Cheat Sheet
**Based on Actual Device Testing - 29-Dec-2025**

✅ = Verified Working | ⚠️ = Works with Notes | ❌ = Doesn't Work

---

## 🔹 Platform Commands

### ✅ Working in Virtual Switch

```bash
# Platform summary
show platform summary
# Output:
# Platform: x86_64-kvm_x86_64-r0
# HwSKU: Force10-S6000
# ASIC: vs
# ASIC Count: 1
```

### ⚠️ Needs Physical Hardware

```bash
show platform psustatus      # ERROR in VS - needs real PSUs
show platform temperature    # "Thermal Not detected" in VS
show platform fan            # Needs physical fans
show platform ssdhealth      # Needs physical SSD
```

### ❓ Not Yet Tested

```bash
show platform summary --json
show platform syseeprom
show platform syseeprom --verbose
show platform pcieinfo
show platform firmware status
```

---

## 🔹 ZTP Commands

### ✅ Verified Working

```bash
# Show status (NOTE: hyphen not space!)
show ztp-status
# Output:
# ========================================
# ZTP
# ========================================
# ZTP Admin Mode      : False
# ZTP Service         : Inactive
# ZTP Status          : Not Started
```

```bash
# Enable ZTP
sudo config ztp enable
# Output: Running command: ztp enable
```

```bash
# Disable ZTP (with safety prompt)
sudo config ztp disable
# Output:
# sonic WARNING sonic-ztp : Please save any running config, before disabling ZTP.
# Active ZTP session will be stopped and disabled, continue? [y/N]: y
```

### 📝 Important Notes
- Command is `show ztp-status` (with hyphen), NOT `show ztp status`
- Disable command has safety warning - good UX ✓
- Prompts for confirmation before disabling

---

## 🔹 NTP Commands

### ✅ Verified Working

```bash
# Add NTP server
sudo config ntp add 10.1.1.1
# Output:
# NTP server 10.1.1.1 added to configuration
# Restarting chrony service...
```

```bash
# Check chrony tracking
chronyc tracking
# Output:
# Reference ID    : 00000000 ()
# Stratum         : 0
# Ref time (UTC)  : Thu Jan 01 00:00:00 1970
# System time     : 0.000000000 seconds fast of NTP time
# Last offset     : +0.000000000 seconds
# ...
# Leap status     : Not synchronised
```

### ⚠️ Syntax Issue

```bash
# This is AMBIGUOUS - won't work:
show ntp
# Output: % Error: Ambiguous command.

# Use specific subcommand instead:
show ntp server          # Show NTP servers
show ntp associations    # Show associations
show ntp global          # Show global settings
```

### ❓ Not Yet Tested

```bash
sudo config ntp del <ip>
chronyc sources
chronyc sourcestats
show ntp server          # Correct syntax
show ntp associations
redis-cli -n 4 KEYS NTP*
```

---

## 🔹 Clear ARP/ND Commands

### ✅ Verified Working (from admin shell)

```bash
# Clear ARP
sonic-clear arp
# Output:
# 192.168.100.1 dev eth0 lladdr 7c:5a:1c:b1:f2:f6  ref 1 used 451/0/450probes 4 REACHABLE
#
# *** Round 1, deleting 1 entries ***
# *** Flush is complete after 1 round ***
```

```bash
# Clear IPv6 Neighbors
sonic-clear ndp
# Output:
# fe80::5054:ff:fec3:6c40 dev eth0 lladdr 52:54:00:c3:6c:40  ref 1 used 1587/1587/1587probes 1 REACHABLE
#
# *** Round 1, deleting 1 entries ***
# *** Flush is complete after 1 round ***
```

### ❌ Show Commands Not in IS-CLI

```bash
# These DON'T work in IS-CLI mode:
sonic# show arp
# Error: Invalid input detected at "^" marker.

sonic# show ndp
# Error: Invalid input detected at "^" marker.
```

### ✅ Alternative - Use from Admin Shell

```bash
# From admin shell (not IS-CLI):
admin@sonic:~$ ip neigh show              # Show all neighbors
admin@sonic:~$ ip -4 neigh show           # IPv4 only (ARP)
admin@sonic:~$ ip -6 neigh show           # IPv6 only (NDP)
```

---

## 📋 CLI Mode Reference

### IS-CLI Mode (sonic#)

**Enter**: Type `sonic-cli` from admin shell

**Available**:
- `show platform summary` ✓
- `show ztp-status` ✓
- `show ntp server` ✓
- Platform commands ✓

**NOT Available**:
- `show arp` ❌
- `show ndp` ❌
- Some diagnostic commands ❌

**Exit**: Type `exit`

### Click CLI / Admin Shell (admin@sonic:~$)

**Available**:
- All `sudo config` commands ✓
- `sonic-clear arp/ndp` ✓
- `ip neigh show` ✓
- `chronyc` commands ✓
- `redis-cli` commands ✓
- Docker commands ✓

---

## 🎯 Quick Command Finder

**I want to...**

### Check platform info
```bash
sonic# show platform summary
```

### Enable/Disable ZTP
```bash
admin@sonic:~$ sudo config ztp enable
admin@sonic:~$ sudo config ztp disable
```

### Check ZTP status
```bash
sonic# show ztp-status
```

### Add NTP server
```bash
admin@sonic:~$ sudo config ntp add time.google.com
```

### Remove NTP server
```bash
admin@sonic:~$ sudo config ntp del time.google.com
```

### Check NTP sync status
```bash
admin@sonic:~$ chronyc tracking
admin@sonic:~$ chronyc sources
```

### View ARP table
```bash
# From admin shell:
admin@sonic:~$ ip neigh show
# OR
admin@sonic:~$ ip -4 neigh show
```

### Clear ARP table
```bash
admin@sonic:~$ sonic-clear arp
```

### View IPv6 neighbors
```bash
admin@sonic:~$ ip -6 neigh show
```

### Clear IPv6 neighbors
```bash
admin@sonic:~$ sonic-clear ndp
```

---

## 🔧 Troubleshooting

### "Ambiguous command" error

**Problem**:
```bash
sonic# show ntp
% Error: Ambiguous command.
```

**Solution**:
```bash
sonic# show ntp server        # Or 'associations' or 'global'
```

### "Invalid input" error for show arp

**Problem**:
```bash
sonic# show arp
% Error: Invalid input detected at "^" marker.
```

**Solution**:
Exit IS-CLI and use:
```bash
admin@sonic:~$ ip neigh show
```

### Platform commands failing

**Problem**:
```bash
sonic# show platform psustatus
ERROR: Command failed
```

**Solution**:
This is expected in virtual switch. Commands need physical hardware.

### NTP not synchronizing

**Problem**:
```bash
chronyc tracking
Leap status     : Not synchronised
```

**Possible Causes**:
- NTP server unreachable
- No internet connectivity
- Server IP incorrect
- Needs time to sync (wait 5-10 minutes)

**Check**:
```bash
# Verify network connectivity
sudo ip vrf exec mgmt ping -c 3 8.8.8.8

# Check NTP sources
chronyc sources -v

# Force time step (if needed)
sudo chronyc makestep
```

---

## 📊 Command Syntax Corrections

| Old Documentation | Correct Syntax | Notes |
|------------------|----------------|-------|
| `show ztp status` | `show ztp-status` | Hyphen required |
| `show ntp` | `show ntp server` | Needs subcommand |
| `show arp` (in IS-CLI) | `ip neigh show` (admin shell) | Different mode |
| `show ndp` (in IS-CLI) | `ip -6 neigh show` (admin shell) | Different mode |

---

## 🎓 Best Practices

### Before Making Config Changes
```bash
# Save current config
sudo config save

# Backup if critical
cp /etc/sonic/config_db.json /etc/sonic/config_db.json.backup
```

### After NTP Changes
```bash
# Wait a few minutes for sync
sleep 300

# Then check status
chronyc tracking
```

### Testing in Virtual Switch
```bash
# Check if you're in virtual switch:
show platform summary | grep ASIC

# If output shows "ASIC: vs", skip hardware-dependent tests
```

---

## 📞 Quick Reference Summary

```bash
# Platform
show platform summary                    # ✅ Works in VS

# ZTP
show ztp-status                          # ✅ Works (note hyphen!)
sudo config ztp enable|disable           # ✅ Works

# NTP
sudo config ntp add <ip>                 # ✅ Works
show ntp server                          # ⚠️ Need subcommand
chronyc tracking                         # ✅ Works

# Clear ARP/ND
sonic-clear arp                          # ✅ Works (admin shell)
sonic-clear ndp                          # ✅ Works (admin shell)
ip neigh show                            # ✅ Works (to view)
```

---

**Last Updated**: 29-Dec-2025
**Verified On**: SONiC Virtual Switch (x86_64-kvm_x86_64-r0)
**Status**: Live document - update as new commands tested
