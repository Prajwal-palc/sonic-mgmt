# TC_VLAN_PERSIST_001: Configuration Save and Reload

## Objective
Verify that VLAN configuration persists after save command execution and system reboot, ensuring configuration data is properly stored and restored.

---

## Test Scenario Overview

| Aspect | Details |
|--------|---------|
| **Test Case ID** | TC_VLAN_PERSIST_001 |
| **Objective** | Verify VLAN configuration persists after save and reload |
| **VLANs to Create** | VLAN 10, VLAN 20, VLAN 30 |
| **Configuration Method** | SONiC CLI (Click Mode) |
| **Persistence Method** | `write memory` command |
| **Reload Method** | `sudo reboot` system command |

---

## Detailed Test Steps

### Step 1: Enter SONiC CLI and Configure VLANs 10, 20, 30

```bash
admin@sonic:~$ sonic-cli
sonic# configure
sonic(config)# vlan 10
sonic(config-vlan)# exit
sonic(config)# vlan 20
sonic(config-vlan)# exit
sonic(config)# vlan 30
sonic(config-vlan)# exit
sonic(config)# exit
sonic#
```

**Expected Result**: All three VLANs are created without errors.

---

### Step 2: Verify VLAN Configuration Before Save

```bash
sonic# show running-configuration interface Vlan
!
interface Vlan10
!
interface Vlan20
!
interface Vlan30
sonic#
```

**Expected Result**: 
- All three VLAN interfaces (Vlan10, Vlan20, Vlan30) are visible in running configuration
- Output shows proper interface formatting with exclamation marks (!)

---

### Step 3: Execute Configuration Save Command

```bash
sonic# write memory
Write memory completed
sonic#
```

**Expected Result**: 
- Command executes successfully
- System displays "Write memory completed" message
- Configuration is written to startup configuration file

---

### Step 4: Exit CLI and Prepare for System Reboot

```bash
sonic# exit
admin@sonic:~$
```

**Expected Result**: User is returned to admin shell prompt.

---

### Step 5: Execute System Reboot

```bash
admin@sonic:~$ sudo reboot
requested COLD shutdown
/var/log: 231.9 MiB (243118080 bytes) trimmed on /dev/loop1
/host: 319.2 MiB (334680064 bytes) trimmed on /dev/vda3
```

**Expected Result**: 
- Reboot command is executed
- System begins shutdown sequence
- Log files and host files are trimmed during shutdown
- System performs COLD shutdown
- Watchdog utility messages may appear (expected during shutdown)

**Boot Sequence** (System will display):

```
GNU GRUB version 2.02

 +----------------------------------------------------------------------------+
 |*SONiC-OS-dev-update.0-dirty-20260310.105627                                |
 | ONIE                                                                       |
 |                                                                            |
 |                                                                            |
 +----------------------------------------------------------------------------+

      Use the ^ and v keys to select which entry is highlighted.
      Press enter to boot the selected OS, `e' to edit the commands
      before booting or `c' for a command-line.
   The highlighted entry will be executed automatically in 0s.
  Booting `SONiC-OS-dev-update.0-dirty-20260310.105627'

Loading SONiC-OS OS kernel ...
Loading SONiC-OS OS initial ramdisk ...
tune2fs 1.47.0 (5-Feb-2023)
Setting reserved blocks percentage to 0% (0 blocks)
Setting reserved blocks count to 0
```

---

### Step 6: System Boot and Configuration Restoration

The system will proceed through boot initialization:

```bash
[    9.512785] rc.local[593]: + cat /etc/sonic/sonic_version.yml
[    9.525513] rc.local[594]: +
[    9.555306] rc.local[596]: + sed -e s/build_version: //g;s/'//g
[    9.637059] rc.local[594]: grep build_version
[    9.700246] rc.local[583]: + SONIC_VERSION=dev-update.0-dirty-20260310.105627
[    9.737086] rc.local[583]: + FIRST_BOOT_FILE=/host/image-dev-update.0-dirty-20260310.105627/platform/firsttime
[    9.791478] rc.local[583]: + SONIC_CONFIG_DIR=/host/image-dev-update.0-dirty-20260310.105627/sonic-config
[    9.832891] rc.local[583]: + SONIC_ENV_FILE=/host/image-dev-update.0-dirty-20260310.105627/sonic-config/sonic-environment
```

**During Boot**:
- Kernel loading
- Initial ramdisk mounting
- Platform initialization
- Configuration loading from `/host/image-*/sonic-config`
- Version detection and setup

---

### Step 7: Login After Reboot

```bash
Debian GNU/Linux 12 sonic ttyS0

sonic login: admin
Password:
Linux sonic 6.1.0-29-2-amd64 #1 SMP PREEMPT_DYNAMIC Debian 6.1.123-1 (2025-01-02) x86_64
You are on
  ____   ___  _   _ _  ____
 / ___| / _ \| \ | (_)/ ___|
 \___ \| | | |  \| | | |
  ___) | |_| | |\  | | |___
 |____/ \___/|_| \_|_|\____|

-- Software for Open Networking in the Cloud --

Unauthorized access and/or use are prohibited.
All access and/or use are subject to monitoring.

Help:    https://sonic-net.github.io/SONiC/

Last login: Thu Mar 12 08:10:29 UTC 2026 on ttyS0
admin@sonic:~$
```

**Expected Result**: 
- System successfully boots
- Login prompt appears
- User logs in with admin credentials
- Bash prompt is displayed

---

### Step 8: Verify VLAN Configuration Persistence After Reboot

```bash
admin@sonic:~$ sonic-cli
sonic# show running-configuration interface Vlan
!
interface Vlan10
!
interface Vlan20
!
interface Vlan30
sonic#
```

**Expected Result**: 
- All three VLANs (10, 20, 30) persist after reboot
- Running configuration shows identical VLAN interfaces as pre-reboot configuration
- No loss of configuration data during reboot process

---

## Complete Test Execution Flow

```bash
# Pre-Reboot Phase
admin@sonic:~$ sonic-cli
sonic# configure
sonic(config)# vlan 10
sonic(config-vlan)# exit
sonic(config)# vlan 20
sonic(config-vlan)# exit
sonic(config)# vlan 30
sonic(config-vlan)# exit
sonic(config)# exit

# Verify configuration
sonic# show running-configuration interface Vlan
!
interface Vlan10
!
interface Vlan20
!
interface Vlan30
sonic#

# Save configuration
sonic# write memory
Write memory completed
sonic# exit
admin@sonic:~$

# System Reboot
admin@sonic:~$ sudo reboot
[System reboots...]

# Post-Reboot Phase - Login
sonic login: admin
Password: [enter password]
admin@sonic:~$

# Verify configuration persistence
admin@sonic:~$ sonic-cli
sonic# show running-configuration interface Vlan
!
interface Vlan10
!
interface Vlan20
!
interface Vlan30
sonic#
```

---

## Expected Results Summary

| Checkpoint | Criteria | Status |
|-----------|----------|--------|
| VLAN 10 Created | VLAN 10 appears in running config | ? Pass |
| VLAN 20 Created | VLAN 20 appears in running config | ? Pass |
| VLAN 30 Created | VLAN 30 appears in running config | ? Pass |
| Config Saved | `write memory` completes successfully | ? Pass |
| System Reboot | System initiates COLD shutdown and reboots | ? Pass |
| Boot Completes | System boots successfully to login prompt | ? Pass |
| Post-Reboot Login | Admin user logs in successfully | ? Pass |
| VLAN 10 Persists | VLAN 10 in running config after reboot | ? Pass |
| VLAN 20 Persists | VLAN 20 in running config after reboot | ? Pass |
| VLAN 30 Persists | VLAN 30 in running config after reboot | ? Pass |

---

## Key CLI Commands Reference

| Command | Purpose | Mode |
|---------|---------|------|
| `sonic-cli` | Enter SONiC CLI (Click Mode) | Bash |
| `configure` | Enter configuration mode | Click Mode |
| `vlan <id>` | Create or enter VLAN configuration | Config Mode |
| `exit` | Exit current configuration mode | Config Mode |
| `show running-configuration interface Vlan` | Display all VLAN interfaces | Click Mode |
| `write memory` | Save configuration to persistent storage | Click Mode |
| `sudo reboot` | Reboot the system (COLD shutdown) | Bash |

---

## Configuration Files and Locations

| Item | Location | Purpose |
|------|----------|---------|
| **Startup Configuration** | `/host/image-*/sonic-config/` | Persistent configuration loaded on boot |
| **Running Configuration** | In-memory | Active configuration during runtime |
| **Version File** | `/etc/sonic/sonic_version.yml` | SONiC OS version information |
| **Environment File** | `/host/image-*/sonic-config/sonic-environment` | Environment variables for SONiC |

---

## Important Notes

### Configuration Persistence
- **`write memory`** saves the running configuration to the startup configuration file
- Without `write memory`, configuration changes are lost after reboot
- The command must complete successfully before reboot to ensure persistence

### Reboot Behavior
- **COLD Shutdown**: Complete power cycle simulation, flushes caches
- **Log Trimming**: System trims log files (`/var/log`) and host files during shutdown
- **Boot Sequence**: System performs full initialization including configuration restoration

### VLAN Interface Behavior
- VLANs are created as virtual Layer 3 interfaces
- Interface names follow format: `Vlan<VLAN_ID>`
- VLANs created without port assignments remain in configuration but may show as "Down" in operational status

### Post-Boot Verification
- After reboot, always verify configuration using `show running-configuration`
- Check operational status with `show vlan` to ensure VLANs are active
- Verify port memberships if ports were assigned before reboot

---

## Troubleshooting Guide

### Issue: Configuration Lost After Reboot

**Root Cause**: `write memory` command was not executed before reboot

**Solution**:
1. Reconfigure VLANs
2. Execute `write memory` and wait for "Write memory completed" message
3. Verify with `show running-configuration interface Vlan`
4. Then proceed with reboot

### Issue: System Does Not Boot After Reboot

**Root Cause**: Possible corruption of startup configuration file

**Solution**:
1. Use GRUB boot menu to select ONIE mode
2. Restore SONiC from backup or reinstall
3. Manually restore configuration from backup if available

### Issue: Partial Configuration Lost

**Root Cause**: Configuration file was partially written or corrupted

**Solution**:
1. Reconfigure missing VLANs
2. Execute `write memory` again
3. Verify complete configuration: `show running-configuration`
4. Test with another reboot cycle

---

## Test Case Validation Checklist

Before declaring the test as PASS:

- [ ] All three VLANs (10, 20, 30) created successfully
- [ ] Running configuration shows all VLANs before reboot
- [ ] `write memory` completes with success message
- [ ] System initiates reboot without errors
- [ ] Boot sequence completes normally
- [ ] System reaches login prompt successfully
- [ ] User can log in with admin credentials
- [ ] `show running-configuration interface Vlan` shows all three VLANs
- [ ] VLAN configuration is identical before and after reboot
- [ ] No configuration loss or corruption detected

---

## Test Case Result

**Overall Status**: [SELECT: PASS / FAIL]

**Tester Name**: ___________________

**Date**: ___________________

**Start Time**: ___________________

**End Time**: ___________________

**Reboot Duration**: ___________________

**Notes/Issues**: 

---

## Success Criteria

? **Test PASSES if**:
- All three VLANs are created and visible in running configuration
- Configuration is saved with `write memory` command completing successfully
- System reboots without errors
- After reboot, all three VLANs remain in running configuration
- No data loss or corruption occurs during the process

? **Test FAILS if**:
- Any VLAN configuration is lost after reboot
- `write memory` command fails or does not complete
- System does not boot successfully
- Configuration is corrupted or modified unexpectedly