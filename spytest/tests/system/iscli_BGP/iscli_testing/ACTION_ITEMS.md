# Action Items from IS-CLI Testing

**Date**: 29-Dec-2025
**Priority**: Based on testing results

---

## 🔴 CRITICAL - Fix Documentation

### Issue 1: Command Syntax Errors in Documentation

**Problem**: Documentation doesn't match actual command syntax

| Documented | Actual Command | Impact |
|------------|---------------|--------|
| `show ztp status` | `show ztp-status` | Users will get errors |
| `show ntp` | `show ntp server` or `show ntp associations` | Ambiguous command error |

**Action Required**:
- [ ] Update all documentation to use `show ztp-status` (with hyphen)
- [ ] Update NTP documentation to specify subcommands
- [ ] Test all documented commands on actual device
- [ ] Create errata document for current users

**Owner**: Documentation Team
**Due**: Before Drop 1 release

---

## 🟡 HIGH - CLI Mode Clarification

### Issue 2: IS-CLI vs Click CLI Confusion

**Problem**: Some commands only work in specific CLI modes

**Commands Missing from IS-CLI**:
- `show arp` - Available in Click CLI only
- `show ndp` - Available in Click CLI only

**Workarounds**:
```bash
# In IS-CLI mode - WON'T WORK:
sonic# show arp     ❌

# Need to use admin shell:
admin@sonic:~$ ip neigh show     ✓
```

**Action Required**:
- [ ] Document which commands work in which CLI mode
- [ ] Create CLI mode reference guide
- [ ] Consider adding `show arp` and `show ndp` to IS-CLI
- [ ] Update test scripts to use correct CLI mode

**Owner**: Development Team + Documentation Team
**Due**: Drop 2

---

## 🟡 HIGH - Virtual Switch Limitations

### Issue 3: Platform Commands Fail in Virtual Environment

**Problem**: Hardware-dependent commands fail in virtual switch

**Commands Affected**:
- `show platform psustatus` - ERROR: Command failed
- `show platform temperature` - Thermal Not detected
- `show platform fan` - Would fail (no virtual fans)
- `show platform ssdhealth` - Would fail (no virtual SSD)

**Action Required**:
- [ ] Document virtual switch limitations
- [ ] Add graceful error messages for VS environment
- [ ] Test all platform commands on physical hardware
- [ ] Update tests to skip hardware tests in VS environment

**Testing Needed on Physical Hardware**:
```bash
show platform psustatus
show platform psustatus --verbose
show platform psustatus --json
show platform temperature
show platform fan
show platform ssdhealth
show platform pcieinfo
```

**Owner**: QA Team + Hardware Testing
**Due**: Before production release

---

## 🟢 MEDIUM - Test Script Updates

### Issue 4: Test Scripts Need Corrections

**Current Issues**:
- Test scripts use wrong command syntax
- Tests don't account for CLI mode differences
- No virtual switch detection

**Action Required**:
- [ ] Update LLDP tests (use correct commands)
- [ ] Update Hostname tests (verify CLI mode)
- [ ] Update NTP tests (use `show ntp server` not `show ntp`)
- [ ] Update Clear ARP/ND tests (use correct CLI mode)
- [ ] Add virtual switch detection to skip hardware tests

**Files to Update**:
```
lldp/test_lldp_iscli.py
hostname/test_hostname_iscli.py
ntp/test_ntp_iscli.py          ← Priority
clear_arp_nd/test_clear_arp_nd_iscli.py  ← Priority
```

**Owner**: QA/Test Automation Team
**Due**: This week

---

## 🟢 MEDIUM - Additional Testing Required

### Issue 5: Incomplete Test Coverage

**Commands Not Yet Tested**:

**Platform**:
- [ ] `show platform summary --json`
- [ ] `show platform syseeprom`
- [ ] `show platform syseeprom --verbose`
- [ ] `show platform pcieinfo`
- [ ] `show platform firmware status`

**NTP**:
- [ ] `show ntp server` (correct syntax)
- [ ] `show ntp associations`
- [ ] `show ntp global`
- [ ] `sudo config ntp del <ip>`
- [ ] `chronyc sources`
- [ ] CONFIG_DB verification: `redis-cli -n 4 KEYS NTP*`

**ZTP**:
- [ ] `show ztp-status --verbose` (if exists)
- [ ] Configuration persistence after reboot
- [ ] ZTP logs: `/var/log/ztp.log`

**Action Required**:
- [ ] Create test plan for untested commands
- [ ] Execute tests on device
- [ ] Document results
- [ ] Update test coverage report

**Owner**: QA Team
**Due**: End of week

---

## 🟢 LOW - Documentation Improvements

### Issue 6: Missing Command Examples

**Action Required**:
- [ ] Add examples for each command variant
- [ ] Create quick reference card
- [ ] Add troubleshooting section
- [ ] Include expected output samples

**Examples Needed**:
```bash
# Good example:
## Show NTP Configuration

### Show NTP Servers
Command: show ntp server
Output:
  NTP Servers:
  - 10.1.1.1
  - time.google.com

### Show NTP Associations
Command: show ntp associations
Output:
  [example output]
```

**Owner**: Documentation Team
**Due**: Drop 2

---

## 📋 Corrected Command Reference

Based on actual testing, here are the verified commands:

### ✅ VERIFIED WORKING

**ZTP**:
```bash
show ztp-status              # Note: hyphen, not space
sudo config ztp enable
sudo config ztp disable
```

**NTP**:
```bash
sudo config ntp add <ip>
chronyc tracking
# For show commands, need:
show ntp server
show ntp associations
show ntp global
```

**Clear ARP/ND** (from admin shell):
```bash
sonic-clear arp
sonic-clear ndp
```

**Platform** (works in VS):
```bash
show platform summary
```

---

## 📊 Quick Fixes Needed

### Immediate (Today):

1. **Fix NTP Test Script**:
```python
# Change from:
result = subprocess.run(['show', 'ntp'], ...)

# Change to:
result = subprocess.run(['show', 'ntp', 'server'], ...)
```

2. **Fix ZTP Test Script**:
```python
# Change from:
result = subprocess.run(['show', 'ztp', 'status'], ...)

# Change to:
result = subprocess.run(['show', 'ztp-status'], ...)
```

3. **Fix ARP/ND Test Script**:
```python
# Add note that show commands need different CLI or use:
result = subprocess.run(['ip', 'neigh', 'show'], ...)
# Instead of: show arp
```

---

## 🎯 Success Metrics

After fixes, should achieve:
- [ ] 100% command documentation accuracy
- [ ] All test scripts pass on actual device
- [ ] Clear CLI mode reference available
- [ ] Physical hardware test results documented
- [ ] Zero ambiguous command errors

---

## 📅 Timeline

| Task | Priority | Due Date | Owner |
|------|----------|----------|-------|
| Fix command documentation | 🔴 Critical | 30-Dec | Docs Team |
| Update test scripts | 🟡 High | 31-Dec | QA Team |
| Physical HW testing | 🟡 High | 02-Jan | QA Team |
| CLI mode reference | 🟡 High | 31-Dec | Docs Team |
| Complete untested commands | 🟢 Medium | 03-Jan | QA Team |
| Enhanced documentation | 🟢 Low | 05-Jan | Docs Team |

---

## 📝 Notes for Team

### What's Working Well ✓
- sonic-clear arp/ndp work perfectly
- NTP add functionality is solid
- ZTP enable/disable is safe (has warnings)
- Platform summary provides good info

### What Needs Attention ⚠️
- Command syntax documentation has errors
- CLI mode usage not clear to users
- Virtual switch limitations not documented
- Some platform commands untestable without hardware

### Testing Environment Note
Current testing on **virtual switch** (x86_64-kvm_x86_64-r0).
Many platform commands need **physical hardware** for full validation.

---

**Created**: 29-Dec-2025
**Last Updated**: 29-Dec-2025
**Status**: Active - Track progress of action items
