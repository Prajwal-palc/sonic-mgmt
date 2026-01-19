# Test Case: IPv6 Static Route Scale & Performance Testing

**Test Case ID:** TC-IP-STATIC-IPV6-011
**Feature:** IPv6 Static Routing
**Sub-feature:** Scale and Performance Validation
**Test Plan Section:** 2.1.11

---

## Test Objective

Configure and verify IPv6 static route scale and performance on DUT. Validate that the system can handle large numbers of static routes (up to 1M entries where supported by platform) while maintaining acceptable CPU and memory utilization, consistent route addition/deletion performance, stable packet forwarding, and configuration persistence across system reboots. Test both global configuration mode and interface-level operations to ensure routing processes remain stable under high-scale scenarios.

---

## Topology Requirements

**Topology:** Two-node (D1-D2) with Traffic Generator or Peer
**Testbed File:** `/home/adminuser/draksha/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
**Supported Platforms:** Hardware and Virtual (scale limits may vary)

```
# Topology - Scale and Performance Testing
# +--------------------------------+                       +--------------------------------+
# |        smic_sonic1 (D1)        |                       |        smic_sonic2 (D2)        |
# |            (DUT)               |                       |     (Peer/TG Device)           |
# |                                |      Ethernet4        |                                |
# | IPv6: 2001:db8:10::1/64        |=======================| IPv6: 2001:db8:10::2/64        |
# |                                |                       |                                |
# | Static Routes: 1M (scalable)   |                       | Traffic destination networks   |
# | Performance monitoring:        |                       |                                |
# |   - CPU utilization            |                       |                                |
# |   - Memory utilization         |                       |                                |
# |   - Route add/delete time      |                       |                                |
# |   - Forwarding verification    |                       |                                |
# +--------------------------------+                       +--------------------------------+
#
# Test scenarios:
#   1. Baseline resource measurement (CPU/Memory)
#   2. Large-scale route addition (up to 1M routes)
#   3. Route lookup and forwarding validation
#   4. Route deletion performance
#   5. Persistence after reboot
#   6. Interface enable/disable under scale
```

**Device Details from Testbed:**
- **D1 (smic_sonic1):** Management IP: 192.168.100.142
- **D2 (smic_sonic2):** Management IP: 192.168.100.97
- **Data Plane Link:** Ethernet4 (between D1 and D2)

---

## Pre-requisites

1. SONiC devices with IPv6 routing enabled
2. FRR routing daemon running
3. Klish CLI and Click CLI access
4. Admin/sudo privileges for privileged commands
5. Sufficient system resources (RAM, CPU) for scale testing
6. Clean routing table state before test execution
7. System logging and monitoring enabled
8. Platform documentation reviewed for maximum route scale limits
9. Time synchronization (NTP) for accurate performance measurement

---

## Test Variables

Variables should be loaded from: `spytest/vars/routing/static/vars_static_ipv6_scale.yaml`

**Recommended variable file structure:**
```yaml
min_topology: ["D1D2:1"]  # Single link between D1 and D2

# Baseline configuration
baseline:
  D1_interface: Ethernet4
  D1_ipv6: "2001:db8:10::1/64"
  D2_interface: Ethernet4
  D2_ipv6: "2001:db8:10::2/64"
  nexthop: "2001:db8:10::2"

# Scale test parameters
scale_config:
  # Route scale targets (adjust based on platform capability)
  small_scale: 1000        # Initial scale test
  medium_scale: 10000      # Medium scale test
  large_scale: 100000      # Large scale test
  max_scale: 1000000       # Maximum scale test (1M routes)

  # Performance thresholds
  max_cpu_percent: 80      # Maximum acceptable CPU usage
  max_memory_mb: 4096      # Maximum acceptable memory usage (MB)
  max_add_time_ms: 100     # Max time to add single route (ms)
  max_delete_time_ms: 50   # Max time to delete single route (ms)

  # Route prefix configuration
  base_prefix: "2001:db8:1000::"
  prefix_length: 64

  # Traffic validation
  test_prefixes:
    - "2001:db8:1000:100::/64"
    - "2001:db8:1000:500::/64"
    - "2001:db8:1000:1000::/64"
    - "2001:db8:1000:5000::/64"

  # Timing parameters
  measurement_interval: 10    # Seconds between measurements
  stabilization_wait: 30      # Wait time for system stabilization
  reboot_wait: 120           # Wait time after reboot
```

---

## Test Procedure

### Setup Phase

#### Step 1: Baseline System Resource Measurement
**Action:**
```bash
# On D1 - Configure baseline IPv6 connectivity
configure terminal
interface Ethernet4
ipv6 address 2001:db8:10::1/64
no shutdown
exit

# On D2 - Configure peer interface
configure terminal
interface Ethernet4
ipv6 address 2001:db8:10::2/64
no shutdown
exit

# Verify baseline connectivity
ping ipv6 2001:db8:10::2 count 5

# On D1 - Record baseline resource usage
show processes cpu sorted
show process memory
show system memory
show ipv6 route summary
```

**Expected Result:**
- Interfaces configured successfully
- IPv6 connectivity verified between D1 and D2
- Baseline CPU and memory metrics recorded

**Baseline Metrics to Record:**
```bash
# CPU usage
show processes cpu sorted | head -20

# Memory usage
show process memory | grep -E "total|used|free"

# Route table state
show ipv6 route summary
# Expected: Minimal routes (connected, link-local)

# System uptime
show system uptime
```

---

### Test Case 1: Small Scale Route Addition (1K Routes)

#### Test Case 1.1: Add 1,000 IPv6 Static Routes
**Test Case ID:** TC-IP-STATIC-SCALE-001

**Action:**
```bash
# On D1 - Klish CLI
# Record start time
configure terminal

# Add 1,000 routes programmatically
# Route format: ipv6 route 2001:db8:1000:X::/64 2001:db8:10::2
# Where X ranges from 0 to 999

# Example commands:
ipv6 route 2001:db8:1000:0::/64 2001:db8:10::2
ipv6 route 2001:db8:1000:1::/64 2001:db8:10::2
ipv6 route 2001:db8:1000:2::/64 2001:db8:10::2
...
ipv6 route 2001:db8:1000:999::/64 2001:db8:10::2
exit

# Record end time and calculate duration
```

**Expected Result:**
- All 1,000 routes successfully configured
- Route addition completed within expected timeframe
- System remains responsive
- No error messages or warnings

**Performance Metrics:**
```bash
# Total time to add 1,000 routes
# Expected: < 2 minutes

# Average time per route
# Expected: < 120ms per route
```

**Validation:**
```bash
show ipv6 route summary
# Expected: Total routes ≥ 1,000 (plus connected/link-local)

show ipv6 route 2001:db8:1000:100::/64
# Verify specific route is present and active

show ipv6 route 2001:db8:1000:500::/64
show ipv6 route 2001:db8:1000:999::/64
```

#### Test Case 1.2: Resource Monitoring After 1K Routes
**Test Case ID:** TC-IP-STATIC-SCALE-002

**Action:**
```bash
# On D1 - Monitor system resources
show processes cpu sorted
show process memory
show system memory

# Check routing processes
show process | grep zebra
show process | grep staticd
show process | grep bgp
```

**Expected Result:**
- CPU usage increase moderate (< 30% above baseline)
- Memory usage increase proportional to route count
- All routing processes running normally
- No process restarts or errors

**Performance Thresholds:**
```
CPU Usage: < 40% total
Memory Usage: < 500 MB increase from baseline
Routing Process Status: All active and stable
```

---

### Test Case 2: Medium Scale Route Addition (10K Routes)

#### Test Case 2.1: Add 10,000 IPv6 Static Routes
**Test Case ID:** TC-IP-STATIC-SCALE-003

**Action:**
```bash
# On D1 - Clear previous routes first
configure terminal
# Remove 1K routes from Test Case 1
no ipv6 route 2001:db8:1000:0::/64 2001:db8:10::2
...
# (or save config and reload for clean state)

# Add 10,000 routes
# Route format: ipv6 route 2001:db8:1000:X::/64 2001:db8:10::2
# Where X ranges from 0 to 9,999

ipv6 route 2001:db8:1000:0::/64 2001:db8:10::2
ipv6 route 2001:db8:1000:1::/64 2001:db8:10::2
...
ipv6 route 2001:db8:1000:9999::/64 2001:db8:10::2
exit
```

**Expected Result:**
- All 10,000 routes successfully configured
- System remains responsive during configuration
- No routing process crashes or restarts

**Performance Metrics:**
```bash
# Total time to add 10,000 routes
# Expected: < 15 minutes

# Average time per route
# Expected: < 90ms per route

# System responsiveness
# CLI commands respond within 2 seconds
```

**Validation:**
```bash
show ipv6 route summary
# Expected: Total routes ≥ 10,000

# Verify sample routes at different positions
show ipv6 route 2001:db8:1000:100::/64
show ipv6 route 2001:db8:1000:1000::/64
show ipv6 route 2001:db8:1000:5000::/64
show ipv6 route 2001:db8:1000:9999::/64
```

#### Test Case 2.2: Forwarding Verification with 10K Routes
**Test Case ID:** TC-IP-STATIC-SCALE-004

**Action:**
```bash
# On D1 - Verify forwarding functionality
# Configure loopback on D2 for reachability testing
# On D2:
configure terminal
interface Loopback 100
ipv6 address 2001:db8:1000:100::1/128
exit
interface Loopback 500
ipv6 address 2001:db8:1000:500::1/128
exit

# On D1 - Test reachability to various destinations
ping ipv6 2001:db8:1000:100::1 count 10
ping ipv6 2001:db8:1000:500::1 count 10

# Check traffic statistics
show ipv6 traffic
```

**Expected Result:**
- Ping successful to all test destinations
- No packet loss
- Forwarding remains stable under route scale
- Traffic counters incrementing correctly

**Validation:**
```bash
show ipv6 traffic
# Verify IPv6 forwarding counters

show ipv6 route 2001:db8:1000:100::/64
# Verify route shows correct next-hop and interface

# Check hardware forwarding (if applicable)
show platform forwarding ipv6
```

#### Test Case 2.3: Resource Monitoring After 10K Routes
**Test Case ID:** TC-IP-STATIC-SCALE-005

**Action:**
```bash
# On D1
show processes cpu sorted
show process memory
show system memory

# Detailed process monitoring
show process | grep -E "zebra|staticd|bgp"
```

**Expected Result:**
- CPU usage acceptable (< 50% total)
- Memory usage proportional to 10K routes
- No memory leaks detected
- All routing processes stable

**Performance Thresholds:**
```
CPU Usage: < 50% total
Memory Usage: < 1.5 GB increase from baseline
Process Stability: No restarts, normal uptime
System Responsiveness: CLI responsive
```

---

### Test Case 3: Large Scale Route Addition (100K Routes)

#### Test Case 3.1: Add 100,000 IPv6 Static Routes
**Test Case ID:** TC-IP-STATIC-SCALE-006

**Action:**
```bash
# On D1 - Clear routing table or reload for clean state
# Recommended: Save config and reload

# Add 100,000 routes
# Route format: ipv6 route 2001:db8:X:Y::/64 2001:db8:10::2
# Where X ranges from 1000 to 2600 (approx)
# And Y ranges from 0 to FFFF

configure terminal
ipv6 route 2001:db8:1000:0::/64 2001:db8:10::2
ipv6 route 2001:db8:1000:1::/64 2001:db8:10::2
...
# Continue until 100,000 routes added
exit
```

**Expected Result:**
- Routes successfully added up to platform limit
- If platform limit < 100K, graceful handling of limit
- System remains stable
- Routing processes do not crash

**Performance Metrics:**
```bash
# Total time to add 100,000 routes
# Expected: < 2 hours (platform dependent)

# Average time per route
# Expected: < 70ms per route

# Monitor during addition:
# - CPU usage trends
# - Memory usage trends
# - Process health
```

**Validation:**
```bash
show ipv6 route summary
# Expected: Total routes reflects added count

# Sample route verification
show ipv6 route 2001:db8:1000:1000::/64
show ipv6 route 2001:db8:1500:5000::/64
show ipv6 route 2001:db8:2000:9000::/64
```

#### Test Case 3.2: Performance Under Scale
**Test Case ID:** TC-IP-STATIC-SCALE-007

**Action:**
```bash
# On D1 - Continuous monitoring during scale test
# Run these commands periodically (every 60 seconds)

show processes cpu sorted
show process memory
show ipv6 route summary

# Monitor system stability
show logging | tail -50
show process | grep -E "zebra|staticd"
```

**Expected Result:**
- CPU usage within acceptable limits (< 70%)
- Memory usage scaling linearly with route count
- No process crashes or restarts
- No error messages in syslog
- System remains responsive to CLI commands

**Performance Thresholds:**
```
CPU Usage: < 70% sustained
Memory Usage: < 3 GB increase from baseline
Route Lookup Time: < 100ms for random route
CLI Responsiveness: < 5 seconds per command
Process Stability: No unexpected restarts
```

#### Test Case 3.3: Route Lookup Performance
**Test Case ID:** TC-IP-STATIC-SCALE-008

**Action:**
```bash
# On D1 - Test route lookup performance with 100K routes
# Time various show commands

# Measure time for specific route lookup
time show ipv6 route 2001:db8:1500:5000::/64

# Measure time for route summary
time show ipv6 route summary

# Measure time for full route table display (with limit)
time show ipv6 route | head -100
```

**Expected Result:**
- Specific route lookup: < 2 seconds
- Route summary: < 3 seconds
- Route table display: < 5 seconds
- No timeouts or command failures

---

### Test Case 4: Maximum Scale Testing (1M Routes - Platform Dependent)

#### Test Case 4.1: Attempt 1 Million IPv6 Static Routes
**Test Case ID:** TC-IP-STATIC-SCALE-009

**Action:**
```bash
# On D1 - WARNING: This test may take several hours
# Ensure adequate system resources and monitoring

# Add routes up to 1,000,000 or platform limit
# Use automated script or configuration file

configure terminal
# Batch configuration recommended
# ipv6 route 2001:db8:X:Y::/64 2001:db8:10::2
# Continue adding until platform limit reached
exit
```

**Expected Result:**
- Routes added successfully up to platform maximum
- System provides clear feedback when limit reached
- Graceful handling of resource exhaustion
- System remains stable and recoverable
- No routing process crashes

**Platform-Specific Handling:**
```
If platform limit < 1M:
  - Verify maximum routes accepted
  - Confirm error message when limit reached
  - Ensure no system instability

If platform supports 1M:
  - All routes successfully installed
  - System performance within bounds
  - Memory usage acceptable
```

**Validation:**
```bash
show ipv6 route summary
# Verify total route count

show processes cpu sorted
show process memory

# Verify random sample routes
show ipv6 route 2001:db8:5000:1234::/64
show ipv6 route 2001:db8:10000:5678::/64
```

#### Test Case 4.2: System Resource Validation at Maximum Scale
**Test Case ID:** TC-IP-STATIC-SCALE-010

**Action:**
```bash
# On D1 - Comprehensive resource monitoring
show system memory
show processes cpu sorted
show process memory

# Process health check
show process | grep -E "PID|zebra|staticd|bgp"

# System stability indicators
show logging | grep -iE "error|crash|restart|oom"
show system uptime
```

**Expected Result:**
- CPU usage: < 80% sustained
- Memory usage: Within platform specifications
- No OOM (Out of Memory) errors
- All routing processes running
- System uptime stable (no unexpected reboots)

**Critical Metrics:**
```
Total Memory Usage: < Platform max - 1GB (safety margin)
CPU Usage: < 80% average
Swap Usage: Minimal or none
Process Count: All expected processes running
Error Rate: No critical errors in logs
```

---

### Test Case 5: Route Deletion Performance

#### Test Case 5.1: Delete Routes from Large Scale Table
**Test Case ID:** TC-IP-STATIC-SCALE-011

**Action:**
```bash
# On D1 - Delete a subset of routes (e.g., 10K routes)
# Measure deletion performance

configure terminal
# Time the deletion process
no ipv6 route 2001:db8:1000:0::/64 2001:db8:10::2
no ipv6 route 2001:db8:1000:1::/64 2001:db8:10::2
...
# Delete 10,000 routes
exit
```

**Expected Result:**
- Routes successfully deleted
- Deletion time consistent with addition time
- Memory freed appropriately
- System remains stable during deletion

**Performance Metrics:**
```bash
# Average deletion time per route
# Expected: < 50ms per route

# Memory reclamation
# Verify memory usage decreases proportionally

# Show commands during deletion
show ipv6 route summary
# Route count should decrease as routes removed
```

#### Test Case 5.2: Clear All Static Routes
**Test Case ID:** TC-IP-STATIC-SCALE-012

**Action:**
```bash
# On D1 - Remove all static routes
configure terminal
# Use bulk delete or configuration reload

# Option 1: Individual deletion
# (time-consuming for large scale)

# Option 2: Configuration reload
write memory
reload
# Skip startup configuration for static routes

# Option 3: Clear all IPv6 routes (if available)
clear ipv6 route *
```

**Expected Result:**
- All static routes removed successfully
- Memory usage returns near baseline
- CPU usage returns to normal
- No residual routes in table

**Validation:**
```bash
show ipv6 route summary
# Expected: Only connected and link-local routes

show process memory
# Memory usage should be near baseline

show processes cpu sorted
# CPU usage should be near baseline
```

---

### Test Case 6: Persistence Validation

#### Test Case 6.1: Save Configuration with Scale Routes
**Test Case ID:** TC-IP-STATIC-SCALE-013

**Action:**
```bash
# On D1 - After adding large number of routes (e.g., 10K)
# Save configuration

write memory
# or
copy running-config startup-config
```

**Expected Result:**
- Configuration saved successfully
- No timeout or errors during save operation
- Configuration file size appropriate for route count

**Validation:**
```bash
# Verify configuration file
show startup-config | grep "ipv6 route" | wc -l
# Count should match number of static routes added

# Check configuration file size
dir
# Look for config file and verify size
```

#### Test Case 6.2: Reboot and Verify Route Persistence
**Test Case ID:** TC-IP-STATIC-SCALE-014

**Action:**
```bash
# On D1 - Reboot system
reload

# Wait for system to fully boot
# Expected wait: 2-5 minutes

# After reboot, verify routes restored
show ipv6 route summary
```

**Expected Result:**
- System reboots successfully
- All static routes restored from startup-config
- Route count matches pre-reboot count
- Forwarding restored
- No route corruption

**Validation:**
```bash
show ipv6 route summary
# Verify total route count matches expected

# Verify sample routes
show ipv6 route 2001:db8:1000:100::/64
show ipv6 route 2001:db8:1000:500::/64
show ipv6 route 2001:db8:1000:1000::/64

# Verify connectivity
ping ipv6 2001:db8:10::2 count 5

# Check process uptime (should be recent after reboot)
show process | grep zebra
show system uptime
```

#### Test Case 6.3: Compare Pre/Post Reboot Configuration
**Test Case ID:** TC-IP-STATIC-SCALE-015

**Action:**
```bash
# On D1 - Compare configurations
show running-config | grep "ipv6 route" > /tmp/routes_post_reboot.txt
# Compare with pre-reboot configuration

# Verify specific routes
show ipv6 route 2001:db8:1000:0::/64
show ipv6 route 2001:db8:1000:9999::/64
```

**Expected Result:**
- All routes present in both pre and post-reboot configs
- No route corruption or data loss
- Route parameters (next-hop, distance) preserved
- Configuration consistency maintained

---

### Test Case 7: Interface Operations Under Scale

#### Test Case 7.1: Interface Shutdown with Scale Routes (Config Mode)
**Test Case ID:** TC-IP-STATIC-SCALE-016

**Action:**
```bash
# On D1 - With large number of routes configured
# Shutdown next-hop interface in config mode

configure terminal
interface Ethernet4
shutdown
exit
```

**Expected Result:**
- Interface goes down cleanly
- All static routes using this next-hop become inactive
- No routing process crashes
- System remains responsive
- Routes remain in configuration

**Validation:**
```bash
show ipv6 interface brief
# Ethernet4 should show as down

show ipv6 route summary
# Active route count should decrease

show ipv6 route 2001:db8:1000:100::/64
# Route should be present but inactive

show running-config | grep "ipv6 route" | wc -l
# Route count in config unchanged
```

#### Test Case 7.2: Interface No Shutdown (Restore)
**Test Case ID:** TC-IP-STATIC-SCALE-017

**Action:**
```bash
# On D1 - Re-enable interface
configure terminal
interface Ethernet4
no shutdown
exit

# Wait for interface to come up and stabilize
sleep 10
```

**Expected Result:**
- Interface comes up successfully
- All static routes become active again
- Forwarding restored
- No route loss
- Performance metrics return to normal

**Validation:**
```bash
show ipv6 interface brief
# Ethernet4 should show as up

show ipv6 route summary
# Active route count should match pre-shutdown count

# Verify connectivity
ping ipv6 2001:db8:10::2 count 5

# Verify sample routes active
show ipv6 route 2001:db8:1000:100::/64
show ipv6 route 2001:db8:1000:500::/64
```

#### Test Case 7.3: Interface Enable/Disable in Interface Mode
**Test Case ID:** TC-IP-STATIC-SCALE-018

**Action:**
```bash
# On D1 - Test interface mode operations
# From interface configuration mode

configure terminal
interface Ethernet4
# Disable
shutdown
# Wait 5 seconds
sleep 5
# Re-enable
no shutdown
exit
```

**Expected Result:**
- Interface operations complete without errors
- Routes transition inactive → active smoothly
- No memory leaks or process issues
- System remains stable throughout operations

**Validation:**
```bash
show ipv6 interface Ethernet4
show ipv6 route summary
show processes cpu sorted
show process memory
```

---

### Test Case 8: Show Command Validation Under Scale

#### Test Case 8.1: Standard Show Commands with Large Route Table
**Test Case ID:** TC-IP-STATIC-SCALE-019

**Action:**
```bash
# On D1 - Execute various show commands with large route table

# 1. Route summary
show ipv6 route summary

# 2. Specific route lookup
show ipv6 route 2001:db8:1000:1234::/64

# 3. All routes (use with caution on large scale)
show ipv6 route | head -100

# 4. IPv6 traffic statistics
show ipv6 traffic

# 5. Process monitoring
show processes cpu sorted
show process memory
show process | grep -E "zebra|staticd"

# 6. Interface status
show ipv6 interface brief

# 7. System logging
show logging | tail -50
```

**Expected Result:**
- All show commands complete successfully
- No timeouts or command failures
- Output format correct and readable
- Response times acceptable (< 10 seconds)

**Performance Benchmarks:**
```
show ipv6 route summary: < 3 seconds
show ipv6 route <specific>: < 2 seconds
show processes cpu sorted: < 5 seconds
show process memory: < 5 seconds
show ipv6 interface brief: < 2 seconds
```

#### Test Case 8.2: Verify Route Summary Accuracy
**Test Case ID:** TC-IP-STATIC-SCALE-020

**Action:**
```bash
# On D1 - Verify route summary statistics
show ipv6 route summary

# Expected output format:
# IPv6 Routing Table Summary
# Total Routes: XXXXX
# Connected: XX
# Static: XXXXX
# ...
```

**Expected Result:**
- Total route count accurate
- Route type breakdown correct
- Static route count matches configured routes
- No discrepancies between summary and actual count

**Validation:**
```bash
# Cross-verify with configuration
show running-config | grep "ipv6 route" | wc -l

# Should match static route count in summary
```

---

### Test Case 9: Privileged Command Validation (sudo/vtysh)

#### Test Case 9.1: vtysh Route Addition
**Test Case ID:** TC-IP-STATIC-SCALE-021

**Action:**
```bash
# On D1 - Use vtysh to add routes
sudo vtysh -c "configure terminal" -c "ipv6 route 2001:db8:9000:100::/64 2001:db8:10::2"
```

**Expected Result:**
- Route added successfully via vtysh
- Route visible in routing table
- Consistent with Klish CLI behavior

**Validation:**
```bash
sudo vtysh -c "show ipv6 route 2001:db8:9000:100::/64"
show ipv6 route 2001:db8:9000:100::/64
# Both should show the route
```

#### Test Case 9.2: Kernel Route Table Verification
**Test Case ID:** TC-IP-STATIC-SCALE-022

**Action:**
```bash
# On D1 - Check kernel routing table
sudo ip -6 route show | wc -l

# View specific routes
sudo ip -6 route show | grep 2001:db8:1000:100
sudo ip -6 route show | grep 2001:db8:1000:500
```

**Expected Result:**
- Kernel route count matches SONiC route count
- All static routes present in kernel table
- Next-hop information correct
- No orphaned routes

**Validation:**
```bash
# Compare counts
sonic_count=$(show ipv6 route summary | grep "Total Routes" | awk '{print $3}')
kernel_count=$(sudo ip -6 route show | wc -l)

# Counts should match (allowing for link-local differences)
```

#### Test Case 9.3: Ping via Specific Interface
**Test Case ID:** TC-IP-STATIC-SCALE-023

**Action:**
```bash
# On D1 - Test connectivity via vtysh
sudo vtysh -c "ping6 2001:db8:10::2 count 5"

# Ping with interface specification
sudo ping6 -I Ethernet4 2001:db8:10::2 -c 5
```

**Expected Result:**
- Ping successful via vtysh
- Ping successful via Linux command
- No packet loss
- Response times reasonable

---

### Test Case 10: Performance Metrics Collection

#### Test Case 10.1: Route Addition Time Measurement
**Test Case ID:** TC-IP-STATIC-SCALE-024

**Action:**
```bash
# On D1 - Measure time to add batches of routes

# Batch 1: 100 routes
start_time=$(date +%s%N)
configure terminal
# Add 100 routes
ipv6 route 2001:db8:8000:0::/64 2001:db8:10::2
ipv6 route 2001:db8:8000:1::/64 2001:db8:10::2
...
ipv6 route 2001:db8:8000:99::/64 2001:db8:10::2
exit
end_time=$(date +%s%N)

# Calculate elapsed time
elapsed=$((end_time - start_time))
avg_time=$((elapsed / 100))
```

**Expected Result:**
- Average route addition time: < 100ms per route
- Consistent performance across batches
- No degradation with increased route count

**Performance Targets:**
```
1-1,000 routes: < 100ms per route
1,001-10,000 routes: < 100ms per route
10,001-100,000 routes: < 120ms per route
100,001+ routes: < 150ms per route (platform dependent)
```

#### Test Case 10.2: CPU Utilization Profile
**Test Case ID:** TC-IP-STATIC-SCALE-025

**Action:**
```bash
# On D1 - Monitor CPU during route operations
# Sample CPU every 10 seconds during route addition

while adding_routes; do
  show processes cpu sorted | head -10
  sleep 10
done
```

**Expected Result:**
- CPU usage peaks during route addition
- Returns to baseline after completion
- No sustained high CPU (> 80%)
- No process starvation

**CPU Thresholds:**
```
Baseline (idle): 5-15%
During route addition: 30-70%
After route addition: 10-25%
Maximum acceptable: 80%
```

#### Test Case 10.3: Memory Utilization Profile
**Test Case ID:** TC-IP-STATIC-SCALE-026

**Action:**
```bash
# On D1 - Monitor memory during scale test
show system memory
show process memory | grep -E "zebra|staticd"

# Track over time
# Record at: 0, 1K, 10K, 100K, 1M routes (if applicable)
```

**Expected Result:**
- Memory usage scales linearly with route count
- No memory leaks detected
- Memory freed upon route deletion
- System maintains adequate free memory

**Memory Thresholds:**
```
Per 1K routes: ~10-50 MB (platform dependent)
Total system usage: < 80% of available RAM
Free memory maintained: > 1GB
Swap usage: Minimal or none
```

---

### Cleanup Phase

**Action:**
```bash
# On D1 - Remove all test configurations

# Option 1: Remove routes individually (small scale)
configure terminal
no ipv6 route 2001:db8:1000:0::/64 2001:db8:10::2
no ipv6 route 2001:db8:1000:1::/64 2001:db8:10::2
...
exit

# Option 2: Reload with clean configuration (recommended)
write erase
reload

# Option 3: Remove specific test routes only
configure terminal
# Remove test routes added during scale testing
# Keep baseline configuration
exit

# Re-enable interfaces if disabled
configure terminal
interface Ethernet4
no shutdown
exit

# Verify clean state
show ipv6 route summary
show running-config | grep "ipv6 route"
```

**Expected Result:**
- All test routes removed
- System returned to baseline state
- Interfaces operational
- Normal resource utilization restored

---

## Complete Show Command Reference

### Regular Klish CLI Commands
```bash
# Route commands
show ipv6 route
show ipv6 route summary
show ipv6 route <prefix>
show ipv6 route | grep <pattern>
show ipv6 route | wc -l

# Interface commands
show ipv6 interface brief
show ipv6 interface Ethernet4
show interface status

# System resource commands
show processes cpu sorted
show process
show process memory
show system memory
show system uptime

# Traffic statistics
show ipv6 traffic
show ipv6 neighbor

# Configuration commands
show running-config
show running-config | grep "ipv6 route"
show running-config | grep "ipv6 route" | wc -l
show startup-config

# Logging commands
show logging
show logging | grep -i error
show logging | tail -50

# Platform commands (if available)
show platform summary
show platform forwarding ipv6
```

### Privileged Commands (sudo/vtysh)
```bash
# vtysh commands
sudo vtysh -c "show ipv6 route"
sudo vtysh -c "show ipv6 route summary"
sudo vtysh -c "show running-config"
sudo vtysh -c "configure terminal" -c "ipv6 route <prefix> <nexthop>"
sudo vtysh -c "ping6 <address> count 5"

# Linux kernel commands
sudo ip -6 route show
sudo ip -6 route show | wc -l
sudo ip -6 route show | grep <prefix>
sudo ping6 -I <interface> <address> -c 5

# Process commands
sudo ps aux | grep -E "zebra|staticd|bgp"
sudo top -b -n 1 | head -20

# System resource commands
free -h
cat /proc/meminfo
vmstat 1 5
iostat -x 1 5
```

---

## Expected Results Summary

### Route Addition and Scale
1. **Small Scale (1K routes):**
   - Successfully configured without errors
   - Addition time: < 2 minutes
   - CPU usage: < 40%
   - Memory usage: < 500 MB increase

2. **Medium Scale (10K routes):**
   - Successfully configured
   - Addition time: < 15 minutes
   - CPU usage: < 50%
   - Memory usage: < 1.5 GB increase
   - Forwarding verified and stable

3. **Large Scale (100K routes):**
   - Successfully configured up to platform limit
   - Addition time: < 2 hours (platform dependent)
   - CPU usage: < 70%
   - Memory usage: < 3 GB increase
   - System remains responsive

4. **Maximum Scale (1M routes):**
   - Routes accepted up to platform maximum
   - Graceful handling when limit reached
   - System stability maintained
   - No crashes or data corruption

### Performance Metrics
1. **Route Addition:**
   - Average time: < 100ms per route (small/medium scale)
   - Consistent performance across scale levels
   - No exponential degradation

2. **Route Deletion:**
   - Average time: < 50ms per route
   - Memory properly reclaimed
   - No lingering entries

3. **Resource Utilization:**
   - CPU: < 80% sustained maximum
   - Memory: Within platform specifications
   - No resource leaks or exhaustion

### System Stability
1. **Process Health:**
   - All routing processes (zebra, staticd) remain running
   - No unexpected restarts or crashes
   - Process memory stable

2. **Forwarding:**
   - Packet forwarding remains operational
   - No packet loss under normal conditions
   - Traffic statistics accurate

3. **Persistence:**
   - Configuration saves successfully
   - All routes restored after reboot
   - No data corruption or loss

### Interface Operations
1. **Interface Shutdown/No Shutdown:**
   - Routes transition properly between active/inactive states
   - No route loss during interface operations
   - Configuration preserved
   - No memory leaks

---

## Performance Benchmarks Summary

| Metric | Small (1K) | Medium (10K) | Large (100K) | Max (1M) |
|--------|------------|--------------|--------------|----------|
| **Add Time (total)** | < 2 min | < 15 min | < 2 hrs | < 20 hrs |
| **Avg Add Time/Route** | < 120ms | < 90ms | < 70ms | < 70ms |
| **CPU Usage** | < 40% | < 50% | < 70% | < 80% |
| **Memory Increase** | < 500 MB | < 1.5 GB | < 3 GB | Platform dependent |
| **Route Summary Time** | < 1 sec | < 2 sec | < 3 sec | < 5 sec |
| **Specific Route Lookup** | < 1 sec | < 1 sec | < 2 sec | < 3 sec |

---

## Test Execution Notes

### Test Duration
- **Estimated Time:** Variable based on scale target
  - Small Scale (1K): 30 minutes
  - Medium Scale (10K): 2 hours
  - Large Scale (100K): 6-8 hours
  - Maximum Scale (1M): 24-48 hours (platform dependent)

### Dependencies
- Platform documentation for maximum route limits
- Sufficient system resources (RAM, CPU)
- Monitoring tools for performance data collection
- Clean system state before each major scale test
- Time synchronization for accurate measurements

### Automation Considerations
- Test highly suitable for automation using SPyTest framework
- Route configuration can be generated programmatically
- Performance data collection automated via polling
- Metrics stored for historical analysis and trending
- Reboot and persistence tests require framework retry logic

### Risk Assessment
- **Risk Level:** Medium (large-scale configuration changes)
- **Rollback:** Configuration backup before each test phase
- **Safety:** Monitor system resources; abort if limits approached
- **Platform Impact:** May temporarily affect system performance

### Platform-Specific Considerations
- Virtual platforms may have lower scale limits than hardware
- Memory-constrained platforms may not support maximum scale
- Some platforms may have optimized route storage mechanisms
- Consult platform documentation for supported limits

---

## Pass/Fail Criteria

### PASS Criteria
✓ DUT handles configured static routes up to supported platform scale
✓ CPU utilization remains < 80% sustained
✓ Memory utilization within platform specifications
✓ No memory leaks detected (memory freed after route deletion)
✓ Forwarding remains stable with no packet loss
✓ Route addition time meets performance targets (< 100ms avg per route)
✓ Route deletion time meets performance targets (< 50ms avg per route)
✓ All show commands complete successfully without timeouts
✓ Static routes persist after system reboot
✓ Configuration saves successfully at all scale levels
✓ No routing process crashes or unexpected restarts
✓ Interface enable/disable operations work correctly under scale
✓ System remains responsive to CLI commands
✓ Kernel routing table consistent with SONiC routing table
✓ No system instability or error messages

### FAIL Criteria
✗ System unable to reach claimed route scale
✗ CPU usage sustained > 80% or process starvation
✗ Memory exhaustion or OOM errors
✗ Memory leaks (memory not freed after route deletion)
✗ Packet loss during forwarding verification
✗ Route addition/deletion time exceeds thresholds significantly
✗ Show commands timeout or fail
✗ Routes not restored after reboot
✗ Route corruption or data loss
✗ Routing process crashes or restarts
✗ System becomes unresponsive
✗ Configuration save failures
✗ Kernel routing table inconsistent with SONiC table
✗ Interface operations cause route loss or system instability

---

## References

- **Test Plan:** Static Routing Test Plan Section 2.1.11
- **Feature:** IPv6 Static Routing
- **CLI Type:** Klish (primary), Click/vtysh (validation)
- **Variable File:** `spytest/vars/routing/static/vars_static_ipv6_scale.yaml`
- **Related Test Cases:** TC-IP-STATIC-IPV6-001 through TC-IP-STATIC-IPV6-010
- **Platform Documentation:** Consult vendor docs for route scale limits

---

## Revision History

| Version | Date       | Author | Description                              |
|---------|------------|--------|------------------------------------------|
| 1.0     | 2025-01-10 | Claude | Initial test case creation               |

---

## Test Execution Command

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_2vs.yaml \
  tests/routing/static/test_static_ipv6_scale.py \
  --logs-path ./logs/test_ipv6_scale_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

---

## Additional Notes

### Performance Data Collection
For comprehensive performance analysis, consider collecting the following metrics at regular intervals during testing:

1. **Route Metrics:**
   - Total route count
   - Active vs. inactive routes
   - Route addition/deletion rate

2. **System Metrics:**
   - CPU utilization (overall and per-process)
   - Memory utilization (total, used, free, cached)
   - Swap usage
   - I/O statistics

3. **Network Metrics:**
   - Interface statistics
   - Packet forwarding rates
   - Error counters

4. **Process Metrics:**
   - Process CPU and memory usage
   - Process restart count
   - Process uptime

### Troubleshooting Guide

**If route addition fails:**
- Check available system memory
- Verify platform route limits
- Review syslog for error messages
- Check routing process health

**If performance degrades:**
- Monitor CPU and memory usage trends
- Check for memory leaks
- Review process priorities
- Consider platform limitations

**If routes don't persist after reboot:**
- Verify configuration saved correctly
- Check startup-config file integrity
- Review boot logs for errors
- Ensure sufficient boot time allowed

**If system becomes unresponsive:**
- Monitor resource utilization
- Check for process hangs
- Review kernel messages
- Consider reducing scale target

---

**End of Test Case Document**
