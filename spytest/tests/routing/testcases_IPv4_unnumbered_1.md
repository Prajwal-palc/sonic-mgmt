# Test Cases - IPv4 Unnumbered Interface Persistence and Stability

## Test Case ID: TC_IPv4_Unnumbered_1.2.1

### Test Case Name
Validate IPv4 Unnumbered Interface Persistence and Platform Stability Across Reboots

### Test Objective
Validate that IPv4 unnumbered interface configuration persists across various reboot types (warm, fast, cold), maintains system stability, and correctly handles donor IP dependency. Verify that when the donor IP is removed, dependent unnumbered interfaces fail appropriately, and when the donor IP is restored, the unnumbered configuration recovers automatically. Test includes configuration of IP unnumbered on Ethernet0 borrowing from Loopback0, performing multiple reboot cycles, verifying running-config persistence, testing donor IP removal/restore scenarios, and ensuring system stability throughout.

---

## Test Configuration

### Testbed Information
- **Testbed File**: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_1node_unnumbered.yaml`
- **Topology**: 1 node (single DUT)
- **Device Under Test (DUT)**: Primary router under test
- **Test Type**: Configuration persistence and stability validation

### Topology Diagram

```
                    +------------------------+
                    |         DUT            |
                    |                        |
                    |  Loopback0 (Donor)     |
                    |  IP: 10.10.10.1/32     |
                    |          |             |
                    |          | (borrows)   |
                    |          ↓             |
                    |  Ethernet0 (Target)    |
                    |  ip unnumbered         |
                    |  Loopback0             |
                    +------------------------+
                             |
                             | Ethernet0
                             | (unnumbered)
                             |
                        External Network
```

### Interface Configuration

**DUT Configuration**:
- **Loopback0 (Donor Interface)**:
  - IP Address: 10.10.10.1/32
  - Purpose: Provides IP address for unnumbered interfaces
  - Type: Virtual interface (always up)

- **Ethernet0 (Target/Unnumbered Interface)**:
  - Configuration: ip unnumbered Loopback0
  - Borrows IP from: Loopback0 (10.10.10.1/32)
  - Purpose: Demonstrate IP unnumbered functionality
  - Type: Physical interface

### Prerequisites
1. Single DUT accessible via SSH
2. SONiC OS installed with IPv4 unnumbered support
3. Access to sonic-cli (klish) on DUT
4. Reboot permissions (warm, fast, cold)
5. Configuration save/restore capability
6. Sufficient time for reboot cycles (10-15 minutes per reboot)
7. Console access recommended for cold reboot verification

---

## Test Procedure

### Step 1: Initial Setup - Configure Loopback0 Donor Interface
**Objective**: Configure the donor interface (Loopback0) with an IP address

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Loopback0 as donor interface
interface Loopback0
ip address 10.10.10.1/32
no shutdown
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify Loopback0 configuration
show ip interface Loopback0

# Verify Loopback0 is up
show interface status Loopback0

# Verify IP address assignment
show ip interface brief
```

**Expected Result**:
- Loopback0 configured with IP 10.10.10.1/32
- Loopback0 interface status: up/up
- IP address visible in interface brief output
- No configuration errors

**Sample Output**:
```
# show ip interface Loopback0
Loopback0 is up, line protocol is up
  Internet address is 10.10.10.1/32
  Broadcast address is 255.255.255.255
  MTU is 65536 bytes
```

---

### Step 2: Configure IP Unnumbered on Ethernet0
**Objective**: Configure Ethernet0 to borrow IP address from Loopback0

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Configure Ethernet0 as unnumbered interface
interface Ethernet0
no shutdown
ip unnumbered Loopback0
exit

# Exit configuration mode
exit
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify unnumbered configuration
show running-config interface Ethernet0

# Verify Ethernet0 interface details
show ip interface Ethernet0

# Verify interface status
show interface status Ethernet0

# Verify IP configuration
show ip interface brief
```

**Expected Result**:
- Ethernet0 configured with "ip unnumbered Loopback0"
- Ethernet0 borrows IP 10.10.10.1 from Loopback0
- Running-config shows unnumbered configuration
- Interface operational (up/up)

**Sample Output**:
```
# show running-config interface Ethernet0
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!

# show ip interface Ethernet0
Ethernet0 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes
```

**Validation Points**:
1. Running-config contains "ip unnumbered Loopback0"
2. Ethernet0 shows borrowed IP address
3. Unnumbered source indicated as Loopback0
4. Interface operational

---

### Step 3: Save Configuration Before Reboot Testing
**Objective**: Save running configuration to ensure persistence testing

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Save configuration
write memory

# Verify configuration saved
exit
```

**Alternative save command**:
```bash
# Using config save command
sudo config save -y
```

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify startup config matches running config
show running-config interface Ethernet0
show startup-config interface Ethernet0

# Check configuration database
show running-config | grep -A 5 "interface Ethernet0"
```

**Expected Result**:
- Configuration saved successfully
- "Configuration saved successfully" message displayed
- Startup-config matches running-config
- No save errors

**Sample Output**:
```
# write memory
Building configuration...
Configuration saved successfully.

# show startup-config interface Ethernet0
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!
```

---

### Step 4: Warm Reboot - Test Configuration Persistence
**Objective**: Perform warm reboot and verify configuration persists

**Step 4.1: Record Pre-Reboot State**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Record current configuration
show running-config interface Ethernet0

# Record interface status
show interface status Ethernet0

# Record IP configuration
show ip interface Ethernet0

# Record uptime
show version
show system uptime
```

**Step 4.2: Initiate Warm Reboot**

**Commands (Execute on DUT)**:
```bash
# Exit sonic-cli if inside
exit

# Initiate warm reboot
sudo warm-reboot

# OR via sonic-cli
sonic-cli
warm-reboot
```

**Expected Behavior**:
- Warm reboot initiated
- System displays warm reboot progress
- Services gracefully stopped
- System reboots without full power cycle

**Step 4.3: Wait for System to Come Back Online**

**Wait Time**: Approximately 5-10 minutes for warm reboot

**Verification**:
- SSH connection re-established
- System fully booted
- All services running

**Step 4.4: Verify Configuration Persistence After Warm Reboot**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify Ethernet0 unnumbered configuration persisted
show running-config interface Ethernet0

# Verify Loopback0 donor IP persisted
show running-config interface Loopback0

# Verify interface operational status
show interface status Ethernet0
show interface status Loopback0

# Verify IP unnumbered operational
show ip interface Ethernet0
show ip interface Loopback0

# Verify system uptime (should be recent)
show system uptime
```

**Expected Result**:
- Running-config shows "ip unnumbered Loopback0" on Ethernet0
- Loopback0 still has IP 10.10.10.1/32
- Ethernet0 borrows IP from Loopback0
- Both interfaces operational (up/up)
- System uptime reset (recent boot time)
- Configuration identical to pre-reboot state

**Sample Output After Warm Reboot**:
```
# show running-config interface Ethernet0
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!

# show ip interface Ethernet0
Ethernet0 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes
```

**Validation Points**:
1. ✓ Configuration persisted across warm reboot
2. ✓ Unnumbered configuration intact
3. ✓ IP borrowing functional
4. ✓ Interfaces operational
5. ✓ No configuration loss

---

### Step 5: Fast Reboot - Test Configuration Persistence
**Objective**: Perform fast reboot and verify configuration persists

**Step 5.1: Record Pre-Reboot State**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Record current configuration
show running-config interface Ethernet0

# Record interface status
show interface status Ethernet0

# Record uptime before reboot
show system uptime
```

**Step 5.2: Initiate Fast Reboot**

**Commands (Execute on DUT)**:
```bash
# Exit sonic-cli
exit

# Initiate fast reboot
sudo fast-reboot

# OR via sonic-cli
sonic-cli
fast-reboot
```

**Expected Behavior**:
- Fast reboot initiated
- Minimal service disruption
- Hardware not fully reset
- Faster than cold reboot, similar to warm reboot

**Step 5.3: Wait for System to Come Back Online**

**Wait Time**: Approximately 3-8 minutes for fast reboot

**Verification**:
- SSH connection re-established
- System fully booted
- All services running

**Step 5.4: Verify Configuration Persistence After Fast Reboot**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify Ethernet0 unnumbered configuration persisted
show running-config interface Ethernet0

# Verify interface operational status
show interface status Ethernet0
show interface status Loopback0

# Verify IP unnumbered operational
show ip interface Ethernet0

# Verify system uptime (should be recent)
show system uptime
```

**Expected Result**:
- Running-config shows "ip unnumbered Loopback0" on Ethernet0
- Configuration identical to pre-reboot state
- Both interfaces operational
- System uptime reset
- Fast reboot completed successfully

**Sample Output After Fast Reboot**:
```
# show running-config interface Ethernet0
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!

# show interface status Ethernet0
Interface    Status    Speed    Duplex    MTU     Type
---------------------------------------------------------
Ethernet0    up        100G     full      9100    QSFP28
```

**Validation Points**:
1. ✓ Configuration persisted across fast reboot
2. ✓ Unnumbered configuration intact
3. ✓ Interfaces operational
4. ✓ System stable after fast reboot

---

### Step 6: Cold Reboot - Test Configuration Persistence
**Objective**: Perform cold reboot (full power cycle) and verify configuration persists

**Step 6.1: Record Pre-Reboot State**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Record current configuration
show running-config interface Ethernet0
show running-config interface Loopback0

# Record interface status
show interface status

# Record uptime before reboot
show system uptime

# Save configuration (if not already saved)
write memory
```

**Step 6.2: Initiate Cold Reboot**

**Commands (Execute on DUT)**:
```bash
# Exit sonic-cli
exit

# Initiate cold reboot (full system reboot)
sudo reboot

# OR via sonic-cli
sonic-cli
reboot
```

**Alternative - Power Cycle**:
```bash
# If physical access available, can perform power cycle
# Power off, wait 30 seconds, power on
```

**Expected Behavior**:
- Cold reboot initiated
- Full system shutdown
- Complete hardware reset
- BIOS/UEFI initialization
- Full SONiC boot sequence

**Step 6.3: Wait for System to Come Back Online**

**Wait Time**: Approximately 5-15 minutes for cold reboot (depends on hardware)

**Verification**:
- System completes POST (Power-On Self-Test)
- BIOS/UEFI initialization
- SONiC OS boots
- All services started
- SSH connection re-established

**Step 6.4: Verify Configuration Persistence After Cold Reboot**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Enter sonic-cli
sonic-cli

# Verify Ethernet0 unnumbered configuration persisted
show running-config interface Ethernet0

# Verify Loopback0 donor IP persisted
show running-config interface Loopback0

# Verify interface operational status
show interface status Ethernet0
show interface status Loopback0

# Verify IP unnumbered operational
show ip interface Ethernet0
show ip interface Loopback0

# Verify system uptime (should be recent)
show system uptime

# Verify overall system health
show version
show platform summary
```

**Expected Result**:
- Running-config shows "ip unnumbered Loopback0" on Ethernet0
- Loopback0 still has IP 10.10.10.1/32
- Configuration identical to pre-reboot state
- Both interfaces operational
- System uptime reset
- System fully functional after cold reboot

**Sample Output After Cold Reboot**:
```
# show running-config interface Ethernet0
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!

# show running-config interface Loopback0
!
interface Loopback0
 ip address 10.10.10.1/32
!

# show ip interface Ethernet0
Ethernet0 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes

# show system uptime
System uptime: 5 minutes
```

**Validation Points**:
1. ✓ Configuration persisted across cold reboot
2. ✓ Unnumbered configuration intact
3. ✓ Donor IP preserved
4. ✓ IP borrowing functional
5. ✓ Interfaces operational
6. ✓ System stable after full power cycle

---

### Step 7: Remove Donor IP - Verify Dependent Failure
**Objective**: Remove IP from Loopback0 (donor) and verify Ethernet0 (dependent) fails appropriately

**Step 7.1: Record State Before Donor IP Removal**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Record current working state
show running-config interface Ethernet0
show running-config interface Loopback0

# Record operational status
show ip interface Ethernet0
show ip interface Loopback0

# Record interface status
show interface status Ethernet0
```

**Step 7.2: Remove IP Address from Loopback0 (Donor Interface)**

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Remove IP address from Loopback0
interface Loopback0
no ip address 10.10.10.1/32
exit

# Exit configuration mode
exit
```

**Step 7.3: Verify Dependent Interface Failure**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify Loopback0 has no IP address
show ip interface Loopback0
show running-config interface Loopback0

# Verify Ethernet0 unnumbered configuration still present but non-functional
show running-config interface Ethernet0

# Verify Ethernet0 has no IP address (cannot borrow from empty donor)
show ip interface Ethernet0

# Verify interface status
show interface status Ethernet0

# Check for error messages or warnings
show logging | grep -i "unnumbered\|loopback0\|ethernet0" | tail -20
```

**Expected Result**:
- Loopback0 has no IP address configured
- Ethernet0 still has "ip unnumbered Loopback0" in running-config
- **Ethernet0 has no operational IP address** (borrowing failed)
- Ethernet0 interface may be up physically but has no IP
- Warning/error messages about unnumbered interface failure
- Dependent behavior correctly observed

**Sample Output After Donor IP Removal**:
```
# show running-config interface Loopback0
!
interface Loopback0
!
# (No IP address configured)

# show running-config interface Ethernet0
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!
# (Unnumbered config still present)

# show ip interface Loopback0
Loopback0 is up, line protocol is up
  Internet address is not set
  MTU is 65536 bytes

# show ip interface Ethernet0
Ethernet0 is up, line protocol is up
  Internet address is not set (Unnumbered from Loopback0 - donor has no IP)
  MTU is 9100 bytes
```

**Validation Points**:
1. ✓ Donor IP removed successfully
2. ✓ Unnumbered configuration still present in config
3. ✓ **Ethernet0 has no operational IP** (dependent failure)
4. ✓ System correctly handles missing donor IP
5. ✓ No system crash or instability
6. ✓ Appropriate error/warning logged

---

### Step 8: Restore Donor IP - Verify Automatic Recovery
**Objective**: Restore IP address to Loopback0 and verify Ethernet0 automatically recovers

**Step 8.1: Restore IP Address to Loopback0**

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Enter configuration mode
configure terminal

# Restore IP address to Loopback0
interface Loopback0
ip address 10.10.10.1/32
exit

# Exit configuration mode
exit
```

**Step 8.2: Verify Automatic Recovery of Unnumbered Interface**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify Loopback0 IP restored
show ip interface Loopback0
show running-config interface Loopback0

# Verify Ethernet0 automatically recovered
show running-config interface Ethernet0

# Verify Ethernet0 now has IP address (borrowed from Loopback0)
show ip interface Ethernet0

# Verify interface status
show interface status Ethernet0
show interface status Loopback0

# Verify overall IP configuration
show ip interface brief
```

**Expected Result**:
- Loopback0 has IP 10.10.10.1/32 restored
- Ethernet0 still has "ip unnumbered Loopback0" in running-config
- **Ethernet0 automatically borrows IP from Loopback0** (10.10.10.1/32)
- Ethernet0 operational with borrowed IP
- **Automatic recovery without manual intervention**
- System stable

**Sample Output After Donor IP Restoration**:
```
# show running-config interface Loopback0
!
interface Loopback0
 ip address 10.10.10.1/32
!

# show running-config interface Ethernet0
!
interface Ethernet0
 no shutdown
 ip unnumbered Loopback0
!

# show ip interface Loopback0
Loopback0 is up, line protocol is up
  Internet address is 10.10.10.1/32
  Broadcast address is 255.255.255.255
  MTU is 65536 bytes

# show ip interface Ethernet0
Ethernet0 is up, line protocol is up
  Internet address is 10.10.10.1/32 (Unnumbered from Loopback0)
  Broadcast address is 255.255.255.255
  MTU is 9100 bytes
```

**Validation Points**:
1. ✓ Donor IP restored successfully
2. ✓ Ethernet0 **automatically recovered** IP borrowing
3. ✓ Ethernet0 operational with borrowed IP
4. ✓ No manual reconfiguration required
5. ✓ Dependent interface recovered correctly
6. ✓ System stable after recovery

---

### Step 9: Final Configuration Persistence Verification
**Objective**: Final verification that all configurations are persistent and saved

**Step 9.1: Save Final Configuration**

**Commands (Execute on DUT)**:
```bash
# Enter sonic-cli
sonic-cli

# Save configuration
write memory

# Exit
exit
```

**Step 9.2: Verify Configuration Persistence**

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify running-config matches expected state
show running-config interface Loopback0
show running-config interface Ethernet0

# Verify startup-config matches running-config
show startup-config interface Loopback0
show startup-config interface Ethernet0

# Compare running and startup configs
show running-config | grep -A 5 "interface Loopback0"
show startup-config | grep -A 5 "interface Loopback0"
show running-config | grep -A 5 "interface Ethernet0"
show startup-config | grep -A 5 "interface Ethernet0"
```

**Expected Result**:
- Running-config contains all expected configurations
- Startup-config matches running-config
- Configuration saved successfully
- Loopback0 has IP 10.10.10.1/32
- Ethernet0 has "ip unnumbered Loopback0"

**Validation Points**:
1. ✓ Running-config correct
2. ✓ Startup-config matches running-config
3. ✓ Configuration will persist across future reboots
4. ✓ All test configurations intact

---

### Step 10: System Stability Verification
**Objective**: Verify overall system stability after all test operations

**Validation Commands (klish mode via sonic-cli)**:
```bash
# Verify system health
show version
show platform summary
show system uptime

# Verify interface health
show interface status
show ip interface brief

# Check for errors in logs
show logging | grep -i error | tail -50
show logging | grep -i critical | tail -20

# Verify no memory leaks or resource issues
show processes
show system memory

# Verify database consistency
show running-config
```

**Expected Result**:
- System version information correct
- Platform summary shows all components healthy
- No critical errors in logs
- Interfaces operational
- Memory and CPU usage normal
- System stable and responsive

**Sample Output**:
```
# show system uptime
System uptime: 45 minutes

# show platform summary
Platform: x86_64-supermicro_sse_t7132s-r0
ASIC: broadcom
Hardware Revision: N/A
Serial Number: XXXXXXXXXXXXX
Model: SSE-T7132S
All components operational: Yes

# show ip interface brief
Interface        IP Address       Status    Protocol
-------------------------------------------------------
Loopback0        10.10.10.1/32    up        up
Ethernet0        10.10.10.1/32*   up        up
                 (* Unnumbered)
```

**Validation Points**:
1. ✓ System stable after all reboot cycles
2. ✓ No critical errors
3. ✓ All interfaces operational
4. ✓ Resource usage normal
5. ✓ Configuration consistent
6. ✓ Platform healthy

---

## Validation Points

### IPv4 Unnumbered Persistence Validation (klish mode via sonic-cli)

**Primary Command**: `show running-config interface Ethernet0`

**Validation Criteria**:

#### 1. Configuration Persistence
- **After each reboot** (warm/fast/cold):
  - Running-config shows "ip unnumbered Loopback0"
  - Startup-config matches running-config
  - Configuration automatically restored
  - No manual reconfiguration required

#### 2. Operational Status
- **Loopback0 (Donor)**:
  - IP address: 10.10.10.1/32
  - Status: up/up
  - Always operational

- **Ethernet0 (Unnumbered)**:
  - Configuration: ip unnumbered Loopback0
  - Borrowed IP: 10.10.10.1/32 (from Loopback0)
  - Status: up/up
  - Indicates "(Unnumbered from Loopback0)"

#### 3. Reboot Resilience
- **Warm Reboot**:
  - Configuration persists: ✓
  - Time: ~5-10 minutes
  - Services gracefully restarted
  - Unnumbered config functional

- **Fast Reboot**:
  - Configuration persists: ✓
  - Time: ~3-8 minutes
  - Minimal disruption
  - Unnumbered config functional

- **Cold Reboot**:
  - Configuration persists: ✓
  - Time: ~5-15 minutes
  - Full power cycle
  - Unnumbered config functional

#### 4. Donor Dependency Behavior
- **Donor IP Removed**:
  - Ethernet0 config still present
  - Ethernet0 has no operational IP
  - Dependent failure observed
  - No system crash
  - Error/warning logged

- **Donor IP Restored**:
  - Ethernet0 **automatically recovers**
  - IP borrowing functional
  - No manual intervention needed
  - System stable

#### 5. System Stability
- **No crashes** during reboot cycles
- **No memory leaks** after multiple reboots
- **No configuration corruption**
- **Interfaces operational** after all tests
- **Logs clean** (no critical errors)
- **Platform healthy**

---

## Expected Overall Results

### Success Criteria

#### 1. Configuration Persistence (All Reboot Types)
- Unnumbered configuration persists across **warm reboot**
- Unnumbered configuration persists across **fast reboot**
- Unnumbered configuration persists across **cold reboot**
- Startup-config matches running-config after each reboot
- Configuration automatically applied on boot
- No configuration loss or corruption

#### 2. Operational Functionality
- Ethernet0 successfully borrows IP from Loopback0
- IP address shown as "10.10.10.1/32 (Unnumbered from Loopback0)"
- Both interfaces operational (up/up)
- Interface communication functional
- IP unnumbered feature working as designed

#### 3. Reboot Performance
- **Warm Reboot**: Completed in ~5-10 minutes
- **Fast Reboot**: Completed in ~3-8 minutes
- **Cold Reboot**: Completed in ~5-15 minutes
- System fully operational after each reboot
- All services started correctly
- No post-reboot issues

#### 4. Dependent Behavior (Donor IP Management)
- **Donor IP Removal**: Ethernet0 has no operational IP (dependent failure)
- **Donor IP Restore**: Ethernet0 **automatically recovers** IP borrowing
- Unnumbered config remains in running-config throughout
- No manual intervention required for recovery
- System handles dependency correctly

#### 5. System Stability
- No system crashes during any reboot type
- No service failures
- No memory leaks observed
- CPU and memory usage normal
- Platform components healthy
- No database corruption
- Logs show no critical errors

#### 6. Configuration Consistency
- Running-config consistent across reboots
- Startup-config synchronized
- Configuration database intact
- No configuration drift
- CLI commands functional

### Performance Criteria

- **Reboot Time**:
  - Warm: < 10 minutes
  - Fast: < 8 minutes
  - Cold: < 15 minutes

- **Recovery Time** (after donor IP restore):
  - IP borrowing functional: < 5 seconds
  - Interface operational: < 10 seconds

- **System Resources**:
  - CPU usage: < 50% steady state
  - Memory usage: < 80% steady state
  - No resource exhaustion

### Failure Indicators

**Test should fail if**:
1. Unnumbered configuration lost after any reboot type
2. Ethernet0 does not borrow IP from Loopback0 after reboot
3. System crash during reboot
4. Configuration corruption observed
5. Donor IP removal does NOT cause dependent failure
6. Donor IP restoration does NOT cause automatic recovery
7. Manual intervention required to restore unnumbered functionality
8. Running-config and startup-config mismatch after save
9. Critical errors in logs
10. Interfaces fail to come up after reboot
11. Reboot time exceeds maximum thresholds
12. System instability or performance degradation

---

## Test Execution Summary Template

### Reboot Testing Results

| Reboot Type | Config Persisted | Reboot Time | Interfaces Up | Result |
|-------------|------------------|-------------|---------------|--------|
| Warm Reboot | Yes/No | ___ min | Yes/No | Pass/Fail |
| Fast Reboot | Yes/No | ___ min | Yes/No | Pass/Fail |
| Cold Reboot | Yes/No | ___ min | Yes/No | Pass/Fail |

### Configuration Persistence Verification

| Check Point | Expected | Actual | Result |
|-------------|----------|--------|--------|
| Loopback0 IP (10.10.10.1/32) | Present | ___ | Pass/Fail |
| Ethernet0 unnumbered config | Present | ___ | Pass/Fail |
| Ethernet0 borrowed IP | 10.10.10.1/32 | ___ | Pass/Fail |
| Running-config = Startup-config | Yes | ___ | Pass/Fail |

### Donor Dependency Testing

| Test | Expected Behavior | Actual Behavior | Result |
|------|------------------|-----------------|--------|
| Remove Donor IP | Ethernet0 has no IP | ___ | Pass/Fail |
| Unnumbered config present | Yes | ___ | Pass/Fail |
| Restore Donor IP | Ethernet0 auto-recovers | ___ | Pass/Fail |
| Recovery time | < 10 seconds | ___ sec | Pass/Fail |

### System Stability Metrics

| Metric | Threshold | Actual | Result |
|--------|-----------|--------|--------|
| System crashes | 0 | ___ | Pass/Fail |
| Critical errors | 0 | ___ | Pass/Fail |
| Memory usage | < 80% | ___% | Pass/Fail |
| CPU usage | < 50% | ___% | Pass/Fail |
| Config corruption | No | Yes/No | Pass/Fail |

---

## Cleanup Steps

After test completion, optionally remove test configuration:

```bash
# Enter sonic-cli on DUT
sonic-cli

# Enter configuration mode
configure terminal

# Remove unnumbered configuration from Ethernet0
interface Ethernet0
no ip unnumbered Loopback0
exit

# Optional: Remove IP from Loopback0 (if not used elsewhere)
interface Loopback0
no ip address 10.10.10.1/32
exit

# Exit configuration mode
exit

# Save configuration
write memory

# Verify cleanup
show running-config interface Ethernet0
show running-config interface Loopback0

# Exit sonic-cli
exit
```

**Cleanup Verification**:
- Ethernet0 has no unnumbered configuration
- Loopback0 IP removed (if desired)
- Configuration saved
- Interfaces in clean state

---

## Notes

1. **All commands must be executed in klish mode via sonic-cli**

2. **Reboot Types**:
   - **Warm Reboot**: Graceful restart with service preservation
   - **Fast Reboot**: Quick restart with minimal disruption
   - **Cold Reboot**: Full power cycle (complete hardware reset)

3. **Configuration Persistence**:
   - Always use `write memory` or `config save` to persist changes
   - Verify startup-config matches running-config
   - Configuration stored in config_db.json

4. **Donor Interface Requirements**:
   - Must have valid IP address
   - Must be operational (up)
   - Typically uses loopback interfaces (always up)
   - Can use physical interfaces if always available

5. **Unnumbered Interface Behavior**:
   - Borrows IP from donor interface
   - Does not have its own IP address
   - IP address shared with donor
   - Configuration persists independently of donor IP

6. **Dependent Failure Expected Behavior**:
   - When donor IP removed, unnumbered interface has no IP
   - Configuration remains but is non-functional
   - No system crash (graceful degradation)
   - Automatic recovery when donor IP restored

7. **Reboot Time Variations**:
   - Depends on hardware platform
   - Fast reboot generally fastest
   - Cold reboot includes POST/BIOS time
   - Virtual platforms may be faster

8. **Testing Best Practices**:
   - Always save configuration before reboot
   - Wait for complete boot before validation
   - Check logs for errors after each reboot
   - Verify all services running
   - Allow stabilization time (1-2 minutes) after boot

9. **Console Access**:
   - Recommended for cold reboot testing
   - Useful for boot process monitoring
   - Helps diagnose boot failures

10. **ONIE Reinstall** (Optional Extended Test):
    - Complete OS reinstall via ONIE
    - Configuration must be backed up and restored
    - Tests ultimate persistence
    - Time-consuming (30-60 minutes)
    - Not typically part of regular regression

---

## Additional Validation Commands

For comprehensive testing and troubleshooting (klish mode via sonic-cli):

```bash
# Configuration verification
show running-config
show startup-config
show running-config interface Loopback0
show running-config interface Ethernet0

# Interface status verification
show interface status
show interface status Loopback0
show interface status Ethernet0

# IP configuration verification
show ip interface
show ip interface brief
show ip interface Loopback0
show ip interface Ethernet0

# System health verification
show version
show platform summary
show system uptime
show processes
show system memory

# Logging and diagnostics
show logging
show logging | grep -i unnumbered
show logging | grep -i loopback
show logging | grep -i ethernet
show logging | grep -i error
show logging | grep -i critical

# Reboot history
show reboot-cause
show boot-log

# Configuration database
show running-config | grep -i unnumbered
```

---

## Command Reference Summary

### Show Commands (klish mode - execute inside sonic-cli)

**Primary Validation Command**:
```bash
show running-config interface Ethernet0
```

**Configuration Commands**:
```bash
show running-config                    # Display entire running configuration
show running-config interface <name>   # Display interface configuration
show startup-config                    # Display startup configuration
show startup-config interface <name>   # Display saved interface configuration
```

**Interface Commands**:
```bash
show interface status                  # Display all interface status
show interface status <name>           # Display specific interface status
show ip interface                      # Display all IP interface details
show ip interface <name>               # Display specific IP interface details
show ip interface brief                # Display brief IP interface summary
```

**System Commands**:
```bash
show version                           # Display SONiC version information
show platform summary                  # Display platform hardware summary
show system uptime                     # Display system uptime
show processes                         # Display running processes
show system memory                     # Display memory utilization
```

**Logging Commands**:
```bash
show logging                           # Display system logs
show logging | grep -i <keyword>       # Filter logs by keyword
show reboot-cause                      # Display last reboot reason
```

**Configuration Save**:
```bash
write memory                           # Save running-config to startup-config
```

### Configuration Commands (klish mode - execute inside sonic-cli)

**Loopback Interface Configuration**:
```bash
configure terminal                     # Enter configuration mode
interface Loopback0                    # Enter Loopback0 configuration
ip address 10.10.10.1/32               # Configure IP address
no shutdown                            # Enable interface
exit                                   # Exit interface configuration
exit                                   # Exit configuration mode
```

**Unnumbered Interface Configuration**:
```bash
configure terminal                     # Enter configuration mode
interface Ethernet0                    # Enter Ethernet0 configuration
no shutdown                            # Enable interface
ip unnumbered Loopback0                # Configure IP unnumbered
exit                                   # Exit interface configuration
exit                                   # Exit configuration mode
```

**Remove Configuration**:
```bash
configure terminal                     # Enter configuration mode
interface Loopback0                    # Enter Loopback0 configuration
no ip address 10.10.10.1/32            # Remove IP address
exit                                   # Exit interface configuration
exit                                   # Exit configuration mode
```

### Reboot Commands

**Warm Reboot**:
```bash
# From bash
sudo warm-reboot

# OR from sonic-cli
sonic-cli
warm-reboot
```

**Fast Reboot**:
```bash
# From bash
sudo fast-reboot

# OR from sonic-cli
sonic-cli
fast-reboot
```

**Cold Reboot**:
```bash
# From bash
sudo reboot

# OR from sonic-cli
sonic-cli
reboot
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-18
**Author**: Test Engineering Team
**Status**: Ready for Execution
**Test Plan Reference**: 1.2.1 - Validate persistence and platform stability across reboots/ONIE reinstall
