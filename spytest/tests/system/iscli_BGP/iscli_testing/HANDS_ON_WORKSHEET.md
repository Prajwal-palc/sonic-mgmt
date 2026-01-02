# IS-CLI Hands-On Testing Worksheet

**Your Name**: _________________
**Date**: _________________
**SONiC Device**: _________________

---

## 🎯 Purpose
Use this worksheet to manually test the 4 completed features while VM is updating.
Check off each item as you complete it.

---

## Feature 1: Platform Components

### Basic Commands (5 minutes)

**Test 1.1: Platform Summary**
```bash
show platform summary
```
- [ ] Command executed successfully
- [ ] Shows platform name: _________________
- [ ] Shows hardware SKU: _________________
- [ ] No errors displayed

**Test 1.2: Platform Summary JSON**
```bash
show platform summary --json
```
- [ ] Command executed successfully
- [ ] Valid JSON output (can paste into JSON validator)
- [ ] Contains same info as regular summary

**Test 1.3: System EEPROM**
```bash
show platform syseeprom
```
- [ ] Command executed successfully
- [ ] Shows serial number: _________________
- [ ] Shows MAC address: _________________
- [ ] Shows model: _________________

**Test 1.4: PSU Status**
```bash
show platform psustatus
```
- [ ] Command executed successfully
- [ ] Number of PSUs shown: _________________
- [ ] PSU 1 status: _________________
- [ ] PSU 2 status: _________________

**Test 1.5: Temperature**
```bash
show platform temperature
```
- [ ] Command executed successfully
- [ ] Temperature readings displayed
- [ ] All sensors within normal range
- [ ] Highest temp reading: _______°C

**Test 1.6: Fan Status**
```bash
show platform fan
```
- [ ] Command executed successfully
- [ ] Number of fans: _________________
- [ ] All fans operational: [ ] Yes [ ] No
- [ ] Fan speeds displayed

**Test 1.7: SSD Health**
```bash
show platform ssdhealth
```
- [ ] Command executed successfully
- [ ] SSD health percentage: _______%
- [ ] Temperature shown: _______°C
- [ ] No warnings/errors

### Advanced Commands (5 minutes)

**Test 1.8: Help Commands**
```bash
show platform --help
```
- [ ] Help text displayed
- [ ] Lists all subcommands
- [ ] Shows usage examples

**Test 1.9: Verbose Mode**
```bash
show platform psustatus --verbose
```
- [ ] More details than normal mode
- [ ] Additional fields shown

**Test 1.10: PCIe Info**
```bash
show platform pcieinfo
```
- [ ] Command executed successfully
- [ ] PCIe devices listed

### Issues Found
```
[Note any errors, unexpected behavior, or missing features]




```

---

## Feature 2: ZTP (Zero Touch Provisioning)

### Basic Commands (5 minutes)

**Test 2.1: Check ZTP Status**
```bash
show ztp status
```
- [ ] Command executed successfully
- [ ] Current ZTP state: [ ] Enabled [ ] Disabled
- [ ] Shows ZTP configuration

**Test 2.2: Check ZTP in Config**
```bash
show runningconfiguration all | grep -i ztp
```
- [ ] ZTP configuration found
- [ ] Settings match status command

### Configuration Changes (10 minutes)

**Test 2.3: Disable ZTP**
```bash
# Record current state first
show ztp status

# Disable ZTP
sudo config ztp disable

# Verify
show ztp status
```
- [ ] Command executed without errors
- [ ] ZTP now shows disabled
- [ ] Configuration updated

**Test 2.4: Enable ZTP**
```bash
sudo config ztp enable
show ztp status
```
- [ ] Command executed without errors
- [ ] ZTP now shows enabled
- [ ] Configuration updated

**Test 2.5: Check ZTP Service**
```bash
systemctl status ztp.service
```
- [ ] Service status shown
- [ ] Service state: _________________

### Advanced Testing (Optional)

**Test 2.6: ZTP Logs**
```bash
tail -20 /var/log/ztp.log
```
- [ ] Log file accessible
- [ ] Recent entries shown

**Test 2.7: ZTP Configuration File**
```bash
cat /etc/sonic/ztp_cfg.json
```
- [ ] File exists
- [ ] Valid JSON format

### Issues Found
```




```

---

## Feature 3: NTP

### Basic Commands (5 minutes)

**Test 3.1: Show NTP**
```bash
show ntp
```
- [ ] Command executed successfully
- [ ] Shows NTP servers (if configured)
- [ ] Number of servers: _________________

**Test 3.2: Chrony Tracking**
```bash
chronyc tracking
```
- [ ] Command executed successfully
- [ ] Shows reference ID
- [ ] System time offset shown: _________________
- [ ] Leap status: _________________

**Test 3.3: Chrony Sources**
```bash
chronyc sources
```
- [ ] Command executed successfully
- [ ] Lists NTP sources
- [ ] Shows reach and offset values

### Add NTP Server (10 minutes)

**Test 3.4: Add Google Time Server**
```bash
# Add server
sudo config ntp add time.google.com

# Verify
show ntp
```
- [ ] Command executed successfully
- [ ] time.google.com appears in `show ntp`
- [ ] No error messages

**Test 3.5: Verify in Chrony**
```bash
chronyc sources | grep -i google
```
- [ ] Google NTP server appears
- [ ] Shows polling status

**Test 3.6: Check CONFIG_DB**
```bash
redis-cli -n 4 KEYS NTP_SERVER*
```
- [ ] NTP_SERVER keys exist
- [ ] time.google.com key found

**Test 3.7: Detailed Server Info**
```bash
redis-cli -n 4 HGETALL "NTP_SERVER|time.google.com"
```
- [ ] Shows association type
- [ ] Configuration details displayed

### VRF Testing (10 minutes)

**Test 3.8: Check VRF**
```bash
ip vrf show
```
- [ ] mgmt VRF exists: [ ] Yes [ ] No
- [ ] VRF list shown

**Test 3.9: Ping via VRF**
```bash
sudo ip vrf exec mgmt ping -c 3 time.google.com
```
- [ ] Ping successful: [ ] Yes [ ] No
- [ ] Packet loss: _______%
- [ ] Average RTT: _______ms

**Test 3.10: Ping DNS via VRF**
```bash
sudo ip vrf exec mgmt ping -c 3 8.8.8.8
```
- [ ] Ping successful
- [ ] Network connectivity confirmed

### Delete NTP Server (5 minutes)

**Test 3.11: Remove Server**
```bash
# Delete
sudo config ntp del time.google.com

# Verify
show ntp
```
- [ ] Command executed successfully
- [ ] Server removed from list
- [ ] No errors

**Test 3.12: Verify Removal**
```bash
redis-cli -n 4 KEYS NTP_SERVER*
```
- [ ] time.google.com key no longer present

### Add NTP Pool (Optional)

**Test 3.13: Add Pool**
```bash
sudo config ntp add --association-type pool pool.ntp.org
show ntp
```
- [ ] Command executed successfully
- [ ] Pool appears in output

### Issues Found
```




```

---

## Feature 4: Clear ARP/ND

### ARP Testing (10 minutes)

**Test 4.1: View ARP Table**
```bash
show arp
```
- [ ] Command executed successfully
- [ ] ARP entries displayed
- [ ] Number of entries: _________________

**Test 4.2: Count ARP Entries**
```bash
show arp | wc -l
```
- [ ] Total lines: _________________
- [ ] (Subtract 2-3 for headers)
- [ ] Actual entries: _________________

**Test 4.3: Clear ARP**
```bash
# Before
ARP_BEFORE=$(show arp | grep -c Ethernet)
echo "Before: $ARP_BEFORE entries"

# Clear
sonic-clear arp

# After
sleep 2
ARP_AFTER=$(show arp | grep -c Ethernet)
echo "After: $ARP_AFTER entries"
```
- [ ] sonic-clear arp executed successfully
- [ ] Entries before: _________________
- [ ] Entries after: _________________
- [ ] Reduction in entries observed

**Test 4.4: ARP Repopulation**
```bash
# Generate traffic (replace with your gateway IP)
ping -c 5 <gateway-ip>

# Check ARP again
sleep 2
show arp
```
- [ ] Ping successful
- [ ] ARP entries repopulated
- [ ] New entry count: _________________

**Test 4.5: System Stability After Clear**
```bash
# Test connectivity
ping -c 5 127.0.0.1
ping -c 5 <gateway-ip>
```
- [ ] Localhost ping works
- [ ] Gateway ping works
- [ ] No packet loss
- [ ] System stable

### NDP Testing (10 minutes)

**Test 4.6: Check IPv6 Configuration**
```bash
show ipv6 interface
```
- [ ] IPv6 configured: [ ] Yes [ ] No
- [ ] If No, skip to Test 4.10

**Test 4.7: View NDP Table**
```bash
show ndp
```
- [ ] Command executed successfully
- [ ] IPv6 neighbors displayed
- [ ] Number of entries: _________________

**Test 4.8: Clear NDP**
```bash
# Before
show ndp | wc -l

# Clear
sonic-clear ndp

# After
sleep 2
show ndp
```
- [ ] sonic-clear ndp executed successfully
- [ ] Entries cleared or reduced

**Test 4.9: NDP Repopulation**
```bash
# Generate IPv6 traffic (if you have IPv6 neighbor)
ping6 -c 3 <ipv6-neighbor>

# Check NDP
show ndp
```
- [ ] IPv6 ping successful (if neighbor exists)
- [ ] NDP entries repopulated

### Multiple Clears (Stress Test) (5 minutes)

**Test 4.10: Multiple ARP Clears**
```bash
for i in {1..5}; do
  echo "Clear iteration $i"
  sonic-clear arp
  sleep 1
done

# Verify system still works
ping -c 3 127.0.0.1
```
- [ ] All 5 clears completed
- [ ] No errors or crashes
- [ ] System still responsive
- [ ] Connectivity maintained

**Test 4.11: Check for Kernel Errors**
```bash
dmesg | tail -30
```
- [ ] No errors related to ARP/neighbor
- [ ] No kernel panics or warnings

### Performance Testing (Optional)

**Test 4.12: Measure Clear Time**
```bash
time sonic-clear arp
```
- [ ] Execution time: _______seconds
- [ ] Under 5 seconds: [ ] Yes [ ] No

### Issues Found
```




```

---

## Summary & Sign-off

### Overall Results

| Feature | Tests Passed | Tests Failed | Ready? |
|---------|--------------|--------------|--------|
| Platform Components | _____ / 10 | _____ | [ ] Yes [ ] No |
| ZTP | _____ / 7 | _____ | [ ] Yes [ ] No |
| NTP | _____ / 13 | _____ | [ ] Yes [ ] No |
| Clear ARP/ND | _____ / 12 | _____ | [ ] Yes [ ] No |

### Critical Issues Found

Priority | Feature | Issue | Impact |
|----------|---------|-------|--------|
| P1 | | | |
| P2 | | | |
| P3 | | | |

### Notes & Observations
```




```

### Environment Details

**Platform**: _________________
**SONiC Version**: _________________
**Kernel Version**: _________________
**Docker Version**: _________________

**Network Configuration**:
- Management IP: _________________
- Gateway: _________________
- VRF Configured: [ ] Yes [ ] No

### Time Spent

- Platform Components: _______minutes
- ZTP: _______minutes
- NTP: _______minutes
- Clear ARP/ND: _______minutes
- **Total**: _______minutes

### Next Steps

- [ ] Document issues in JIRA
- [ ] Share results with team
- [ ] Retest failed items
- [ ] Update project tracker

---

**Tested By**: _________________
**Date Completed**: _________________
**Sign-off**: _________________
