# Interface Bugs Verification Test Plan

**Test Suite**: Interface IS-CLI Bug Verification and Automation
**Branch**: interface_bugs_verification_and_automation
**Created**: 2026-01-29
**Target Platform**: SMCI SONiC IS-CLI

## Overview

This test plan covers verification of 13 interface-related bugs found in SMCI SONiC IS-CLI implementation. Tests will be executed interactively first for verification, then automated using the SPyTest framework.

---

## Test Case Index

| Bug ID | Category | Test Case ID | Priority | Automation Status |
|--------|----------|--------------|----------|-------------------|
| SM_ISCLI_1 | Interface | test_interface_001_show_run_ordering | High | Pending |
| SM_ISCLI_8 | Interface | test_interface_008_mgmt_static_ip | Critical | Pending |
| SM_ISCLI_12 | Interface | test_interface_012_show_ip_interface_mgmt | High | Pending |
| SM_ISCLI_22 | Interface | test_interface_022_mgmt_naming_consistency | Medium | Pending |
| SM_ISCLI_25 | Interface | test_interface_025_description_quotes | Medium | Pending |
| SM_ISCLI_31 | Interface | test_interface_031_show_ip_interfaces_mgmt | High | Pending |
| SM_ISCLI_32 | Interface | test_interface_032_loopback_subnet_validation | Medium | Pending |
| SM_ISCLI_33 | Interface | test_interface_033_show_interface_details | High | Pending |
| SM_ISCLI_34 | Interface | test_interface_034_duplicate_ip_validation | Medium | Pending |
| SM_ISCLI_35 | Interface | test_interface_035_speed_auto_command | Low | Pending |
| SM_ISCLI_36 | Interface | test_interface_036_standalone_link_training | Medium | Pending |
| SM_ISCLI_59 | Interface | test_interface_059_mgmt_ip_routing_display | High | Pending |
| SM_ISCLI_61 | Interface | test_interface_061_show_interface_mgmt_syntax | Medium | Pending |
| SM_ISCLI_62 | Interface | test_interface_062_ipv6_autoconfig_default | Medium | Pending |

---

## Test Case Details

### TC-001: Show Running-Config Interface Ordering
**Bug ID**: SM_ISCLI_1
**Description**: Ordering of interfaces in show running-configuration is incorrect
**Priority**: High
**Test Type**: Functional

**Preconditions**:
- Device accessible via IS-CLI
- Multiple interfaces configured with IP addresses
- At least one Loopback, Management, and Ethernet interface configured

**Test Steps**:
1. Configure IP addresses on multiple interfaces:
   - Ethernet0: 192.168.1.1/24
   - Ethernet4: 192.168.2.1/24
   - Loopback0: 1.1.1.1/32
   - Loopback1: 2.2.2.2/32
   - Management0: 10.10.10.1/24
2. Execute `show running-configuration`
3. Verify interface ordering in output

**Expected Result**:
- Interfaces should be ordered logically:
  - Loopback interfaces (numerical order)
  - Management interfaces
  - Ethernet interfaces (numerical order)
- Or alphabetically by interface type and number

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: Interfaces appear in consistent, logical order
- FAIL: Interfaces appear in random or inconsistent order

**Automation Notes**:
- Parse show running-config output
- Extract interface section order
- Verify ordering matches expected pattern

---

### TC-008: Management Interface Static IP Assignment
**Bug ID**: SM_ISCLI_8
**Description**: Management0 can't be assigned a static IP address
**Priority**: Critical
**Test Type**: Functional

**Preconditions**:
- Device accessible via IS-CLI
- Management interface exists
- No IP address currently configured on Management0

**Test Steps**:
1. Enter configuration mode: `configure terminal`
2. Enter interface mode: `interface Management 0`
3. Configure static IP: `ip address 10.250.0.100/24`
4. Exit configuration mode: `end`
5. Verify configuration: `show running-configuration interface Management 0`
6. Verify IP is applied: `show ip interface Management 0`
7. Verify connectivity: `ping 10.250.0.1` from Linux shell

**Expected Result**:
- IP address configuration command succeeds without error
- Configuration appears in running-config
- IP address is applied to eth0/Management0
- Network connectivity works with new IP

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: Static IP can be assigned and persists
- FAIL: Command fails or IP doesn't apply

**Automation Notes**:
- Save original management IP configuration
- Configure test IP address
- Verify via show commands and Linux shell
- Restore original configuration
- **WARNING**: Use caution - changing management IP can break SSH connection

---

### TC-012: Show IP Interface Management Port Display
**Bug ID**: SM_ISCLI_12
**Description**: "show ip interface" doesn't show management port on IS-CLI, while it does on Click CLI
**Priority**: High
**Test Type**: Functional

**Preconditions**:
- Device accessible via both IS-CLI and Click CLI
- Management interface has IP address configured

**Test Steps**:
1. From Click CLI, execute: `show ip interfaces`
2. Verify Management/eth0 interface is listed with IP
3. Enter IS-CLI: `sonic-cli`
4. Execute: `show ip interface`
5. Check if Management0 interface is listed

**Expected Result**:
- IS-CLI `show ip interface` should display Management0/eth0
- Output should include IP address, status, and interface name
- Parity with Click CLI output

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: Management interface visible in IS-CLI show ip interface
- FAIL: Management interface missing from IS-CLI output

**Automation Notes**:
- Execute both Click and IS-CLI commands
- Parse output from both
- Verify Management interface present in both
- Compare IP addresses match

---

### TC-022: Management Interface Naming Consistency
**Bug ID**: SM_ISCLI_22
**Description**: After assigning IP to Management0, running-config shows it as eth0
**Priority**: Medium
**Test Type**: Functional

**Preconditions**:
- Device accessible via IS-CLI
- Management interface exists

**Test Steps**:
1. Configure IP on Management0:
   ```
   configure terminal
   interface Management 0
   ip address 172.31.51.147/16
   end
   ```
2. Check running-config: `show running-configuration`
3. Verify interface name in output

**Expected Result**:
- Running-config should show: `interface Management0`
- Not: `interface eth0`
- Consistent naming throughout configuration

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: Interface name is "Management0" in running-config
- FAIL: Interface name is "eth0" in running-config

**Automation Notes**:
- Configure Management0 IP
- Parse running-config output
- Verify interface name matches "Management0" (case-insensitive)
- Check no "interface eth0" entries exist

---

### TC-025: Description with Quotes in Show Running-Config
**Bug ID**: SM_ISCLI_25
**Description**: show running-config interface shows description without quotes for multi-word values
**Priority**: Medium
**Test Type**: Functional

**Preconditions**:
- Device accessible via IS-CLI
- Interface exists (Ethernet0)

**Test Steps**:
1. Configure multi-word description:
   ```
   configure terminal
   interface Ethernet 0
   description Ethernet interface to DC
   end
   ```
2. Execute: `show running-configuration interface Ethernet 0`
3. Note format of description line
4. Copy description line from output
5. Attempt to paste and execute in config mode

**Expected Result**:
- Description should appear with quotes: `description "Ethernet interface to DC"`
- Or description should be parseable when copy/pasted
- Configuration should succeed when applied

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: Description quoted or copy/paste works
- FAIL: Description unquoted and copy/paste fails

**Automation Notes**:
- Configure multi-word description
- Extract description from show running-config
- Attempt to re-apply extracted description
- Verify no error occurs

---

### TC-031: Show IP Interfaces Management IP Display
**Bug ID**: SM_ISCLI_31
**Description**: "show ip interfaces" not showing mgmt IP, whereas Click CLI shows it
**Priority**: High
**Test Type**: Functional

**Preconditions**:
- Device accessible via IS-CLI and Click CLI
- Management interface configured with IP: 172.31.35.138/16

**Test Steps**:
1. From Linux shell, execute: `show ip interfaces`
2. Verify output shows eth0 with IP 172.31.35.138/16
3. Enter IS-CLI: `sonic-cli`
4. Execute: `show ip interfaces`
5. Verify Management0 is listed

**Expected Result**:
- IS-CLI should show Management0 interface
- IP address should match: 172.31.35.138/16
- Status should be displayed
- Parity with Click CLI

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: Management IP visible in IS-CLI show ip interfaces
- FAIL: Management IP missing or incorrect in IS-CLI

**Automation Notes**:
- Execute show ip interfaces in both CLIs
- Parse and compare output
- Verify management IP present in both
- Verify IP addresses match

---

### TC-032: Loopback Non-/32 Subnet Validation
**Bug ID**: SM_ISCLI_32
**Description**: Able to configure non-/32 addresses on Loopback interfaces
**Priority**: Medium
**Test Type**: Negative Testing

**Preconditions**:
- Device accessible via IS-CLI
- Loopback interface available

**Test Steps**:
1. Configure Loopback with non-/32 subnet:
   ```
   configure terminal
   interface Loopback 1
   ip address 10.0.0.1/24
   end
   ```
2. Verify if command succeeds
3. Check running-config: `show running-configuration interface Loopback 1`
4. Check interface status: `show ip interface Loopback 1`

**Expected Result**:
- Command should FAIL with error message
- Error should indicate: "Loopback interface requires /32 prefix"
- Configuration should not be applied
- Compare with Broadcom SONiC behavior

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: Command rejected with appropriate error
- FAIL: Non-/32 subnet accepted on Loopback

**Automation Notes**:
- Attempt to configure /24, /30, /31 subnets on Loopback
- Verify all are rejected
- Verify only /32 is accepted
- Check error message content

---

### TC-033: Show Interface Detailed Information
**Bug ID**: SM_ISCLI_33
**Description**: show interface [interface] has incorrect/incomplete information
**Priority**: High
**Test Type**: Functional

**Preconditions**:
- Device accessible via IS-CLI
- Interface connected with DAC cable to another switch
- Interface link is UP

**Test Steps**:
1. Connect Ethernet interface to another device
2. Execute: `show interface Ethernet 0`
3. Verify output contains:
   - Line protocol status (up/down)
   - Reason for status
   - MAC address
   - Line Speed (actual speed, not "auto")
   - Events (link up/down history)
   - Last clearing counters timestamp

**Expected Result (Broadcom IS-CLI standard)**:
```
Line protocol is up
Hardware is Ethernet, address is xx:xx:xx:xx:xx:xx
Line speed is 800000 Mb/s
Last clearing of "show interface" counters: 5 days 10:25:30
Events:
  2025-12-22 10:15:30 - Link Up
```

**Actual Result**: (To be documented during interactive testing)
- Line protocol: (blank/unknown)
- MAC address: (missing)
- Line Speed: auto (should show actual speed)
- Events: (blank)
- Last clearing: units only, no values

**Pass/Fail Criteria**:
- PASS: All fields populated with correct data
- FAIL: Any field blank or incorrect

**Automation Notes**:
- Parse show interface output
- Verify all mandatory fields present
- Validate MAC address format
- Verify speed is numeric (not "auto")
- Check events section exists

---

### TC-034: Duplicate IP Address Validation (Primary/Secondary)
**Bug ID**: SM_ISCLI_34
**Description**: Allows same IP address for primary and secondary address
**Priority**: Medium
**Test Type**: Negative Testing

**Preconditions**:
- Device accessible via IS-CLI
- Interface available for testing (Ethernet0)

**Test Steps**:
1. Configure primary IP:
   ```
   configure terminal
   interface Ethernet 0
   ip address 10.0.0.1/24
   ```
2. Attempt to configure same IP as secondary:
   ```
   ip address 10.0.0.1/24 secondary
   end
   ```
3. Check if error is displayed

**Expected Result**:
- Command should FAIL with error
- Error message: `%Error: IPv4 address: 10.0.0.1/24 is already configured as primary for interface: Ethernet0`
- Secondary IP should not be configured

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: Duplicate IP rejected with error
- FAIL: Duplicate IP accepted

**Automation Notes**:
- Configure primary IP
- Attempt secondary with same IP
- Verify error message content
- Verify only one IP in running-config
- Test with different subnets of same IP (e.g., /24 vs /30)

---

### TC-035: Speed Auto Command Availability
**Bug ID**: SM_ISCLI_35
**Description**: Interface config mode missing "speed auto" command
**Priority**: Low
**Test Type**: Functional

**Preconditions**:
- Device accessible via IS-CLI
- Ethernet interface supports auto-negotiation

**Test Steps**:
1. Enter interface configuration mode:
   ```
   configure terminal
   interface Ethernet 0
   ```
2. Check available speed commands: `speed ?`
3. Look for "auto" option
4. Attempt to configure: `speed auto`

**Expected Result**:
- "auto" should be listed in help output
- `speed auto` command should succeed
- Interface should enable auto-negotiation

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: "speed auto" command available and functional
- FAIL: "speed auto" command missing

**Automation Notes**:
- Parse help output from "speed ?"
- Verify "auto" is an option
- Configure speed auto
- Verify in running-config
- Check interface negotiation status

---

### TC-036: Standalone Link Training Command
**Bug ID**: SM_ISCLI_36
**Description**: Interface config mode missing "standalone-link-training" command
**Priority**: Medium
**Test Type**: Functional

**Preconditions**:
- Device accessible via IS-CLI
- Testing with 2M+ DAC cable connection

**Test Steps**:
1. Enter interface configuration mode:
   ```
   configure terminal
   interface Ethernet 0
   ```
2. Check available commands: `?`
3. Look for "standalone-link-training" command
4. Attempt to configure: `standalone-link-training`

**Expected Result**:
- "standalone-link-training" should be available
- Command should succeed
- Interface with 2M+ DAC cable should link up

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: Command available and functional
- FAIL: Command missing

**Automation Notes**:
- Parse interface config mode help
- Search for standalone-link-training
- Configure if available
- Test link status with long DAC cable

---

### TC-059: Management IP and Routing Display Issues
**Bug ID**: SM_ISCLI_59
**Description**: Multiple issues with management IP and route display
**Priority**: High
**Test Type**: Functional

**Issues to Verify**:
1. IS-CLI not showing management IP address
2. Sending docker IP for both IPv4 and IPv6
3. Duplicate connected routes showing as kernel routes
4. docker0 showing as kernel route
5. Management interface shown as eth0

**Preconditions**:
- Device accessible via IS-CLI
- Management interface configured
- Routing enabled

**Test Steps**:
1. Execute: `show ip interface`
   - Verify Management0 IP is displayed
   - Verify no docker0 IP listed
2. Execute: `show ipv6 interface`
   - Verify Management0 IPv6 (if configured)
   - Verify no docker IPs listed
3. Execute: `show ip route`
   - Verify connected routes not duplicated as kernel
   - Verify docker0 not shown as kernel route
   - Verify Management interface name consistency

**Expected Result**:
- Management IP shown correctly in show ip interface
- Docker IPs not displayed
- Routes properly categorized (connected vs kernel)
- Consistent interface naming (Management0, not eth0)

**Actual Result**: (To be documented during interactive testing)

**Pass/Fail Criteria**:
- PASS: All 5 issues resolved
- FAIL: Any issue still present

**Automation Notes**:
- Multiple show command outputs to parse
- Check for absence of docker IPs
- Verify route categorization
- Validate interface naming consistency

---

### TC-061: Show Interface Management Syntax
**Bug ID**: SM_ISCLI_61
**Description**: No "show ip interface management/Management0" command
**Priority**: Medium
**Test Type**: Functional

**Preconditions**:
- Device accessible via IS-CLI
- Management interface configured

**Test Steps**:
1. Attempt: `show interface Management 0`
2. Note error message
3. Attempt: `show interface Management`
4. Note error message
5. Attempt: `show ip interface Management 0`
6. Try variations: `show interface Management0` (no space)

**Expected Result**:
- At least one syntax should work:
  - `show interface Management 0`
  - `show interface Management0`
  - `show ip interface Management 0`
- Should display Management interface details

**Actual Result**: (To be documented during interactive testing)
- Current error: `% Error: Invalid input detected at "^" marker.`

**Pass/Fail Criteria**:
- PASS: Management interface can be queried
- FAIL: All syntax variations fail

**Automation Notes**:
- Test multiple command variations
- Verify at least one succeeds
- Parse output if successful
- Document working syntax

---

### TC-062: IPv6 Autoconfig Default and Control
**Bug ID**: SM_ISCLI_62
**Description**: IPv6 autoconfig enabled by default and can't be disabled
**Priority**: Medium
**Test Type**: Functional

**Preconditions**:
- Device accessible via IS-CLI and Linux shell
- Management interface exists

**Test Steps**:
1. Check default state:
   ```bash
   sudo cat /proc/sys/net/ipv6/conf/eth0/autoconf
   ```
   Expected: 0 (disabled)
2. Enable autoconfig via IS-CLI:
   ```
   configure terminal
   interface Management 0
   ipv6 address autoconfig
   end
   ```
3. Verify enabled:
   ```bash
   sudo cat /proc/sys/net/ipv6/conf/eth0/autoconf
   ```
   Expected: 1 (enabled)
4. Disable autoconfig:
   ```
   configure terminal
   interface Management 0
   no ipv6 address autoconfig
   end
   ```
5. Verify disabled:
   ```bash
   sudo cat /proc/sys/net/ipv6/conf/eth0/autoconf
   ```
   Expected: 0 (disabled)

**Expected Result**:
- Default state: disabled (0)
- Enable command: sets to 1
- Disable command: sets to 0
- Running-config reflects state

**Actual Result**: (To be documented during interactive testing)
- Default: 1 (enabled) - WRONG
- Disable command: doesn't change value - WRONG

**Pass/Fail Criteria**:
- PASS: Default disabled, commands work correctly
- FAIL: Default enabled or commands don't work

**Automation Notes**:
- Check /proc filesystem via Linux shell
- Configure via IS-CLI
- Verify kernel settings change
- Test enable/disable toggle

---

## Test Execution Plan

### Phase 1: Interactive Testing (Week 1)
1. Execute each test case manually
2. Document actual results
3. Capture screenshots/logs
4. Identify reproducibility
5. Update test cases with findings

### Phase 2: Automation Development (Week 2-3)
1. Create SPyTest test module structure
2. Implement test functions
3. Add helper functions for common operations
4. Implement result validation
5. Add error handling

### Phase 3: Automation Testing (Week 4)
1. Run automated tests
2. Debug failures
3. Refine test logic
4. Create test report

### Phase 4: CI/CD Integration (Week 5)
1. Add to regression suite
2. Configure test triggers
3. Setup reporting
4. Document known issues

---

## Test Environment

### Hardware Requirements
- SMCI SONiC device (T8164 or compatible)
- Connected interfaces (DAC cables)
- Network connectivity for management

### Software Requirements
- SONiC IS-CLI build: 202505-smci-dev-iscli or later
- SPyTest framework
- Python 3.8+

### Testbed Configuration
- 1-node testbed minimum
- Management network access
- Test VLAN capability

---

## Success Criteria

- All test cases executed successfully
- Results documented
- Automation coverage: 100%
- Pass rate: TBD (based on bug fixes)
- Execution time: < 30 minutes for full suite

---

## Notes for Automation

### Common Patterns
1. **IS-CLI Access**: Use `st.config()` with `type='klish'`
2. **Configuration Blocks**: Use multi-line strings with `end` command
3. **Verification**: Parse show command output with TextFSM templates
4. **Linux Shell**: Use `st.show()` with `type='click'` or direct shell commands
5. **State Management**: Save/restore configurations

### Error Handling
- Catch IS-CLI syntax errors
- Handle SSH disconnection for management IP tests
- Timeout management for slow commands
- Rollback capability for failed tests

### Reporting
- Capture before/after states
- Screenshot critical errors
- Log all command output
- Track bug IDs in test results
