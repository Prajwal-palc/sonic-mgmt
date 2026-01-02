# JIRA Bug Reports - IS-CLI Drop 1 Testing

**Test Date**: 2025-12-30
**Tester**: Anuradha
**Build**: 202505-smci-dev-iscli-2025-12-30T02-57-47
**Platform**: x86_64-kvm_x86_64-r0 (Virtual Switch)
**Test VMs**: 192.168.100.73, 192.168.100.103

---

## BUG #1: IS-CLI Does Not Support Command-Line Flags

**Priority**: 🔴 **HIGH**
**Component**: IS-CLI Core
**Feature**: SM_ISCLI_DROP1_FEATURE1 (Platform Components)
**Affects**: All IS-CLI commands

### Summary
IS-CLI mode does not support any command-line flags (--json, --verbose, --help, etc.) that are available in Click CLI mode, causing syntax errors when users attempt to use documented flags.

### Steps to Reproduce
1. SSH to SONiC device
2. Enter IS-CLI mode: `sonic-cli`
3. Execute: `show platform summary --json`

### Expected Result
```
{
  "platform": "x86_64-kvm_x86_64-r0",
  ...
}
```

### Actual Result
```
sonic# show platform summary --json
                               ^
% Error: Invalid input detected at '^' marker.
```

### Additional Test Cases
All flags fail in IS-CLI mode:
- `show platform summary --verbose` ❌
- `show platform summary --help` ❌
- `show platform psustatus --json` ❌
- Any command with flags ❌

### Environment
- CLI Mode: IS-CLI (sonic#)
- Same command works in Admin Shell with `show` utility
- All standard SONiC Click CLI flags affected

### Impact
- Users familiar with Click CLI will encounter errors
- Documentation may be misleading
- Automation scripts expecting JSON output will fail
- No programmatic access to structured data in IS-CLI mode

### Suggested Fix
1. Implement flag parsing in IS-CLI command processor
2. OR document limitation clearly
3. OR provide alternative commands for structured output

### Workaround
Exit IS-CLI and use Admin Shell commands:
```bash
exit
show platform summary  # Works in admin shell
```

---

## BUG #2: `show ntp` Command is Ambiguous

**Priority**: 🔴 **HIGH**
**Component**: NTP
**Feature**: SM_ISCLI_DROP1_FEATURE7

### Summary
The `show ntp` command returns an ambiguity error instead of defaulting to a sensible subcommand or showing all NTP information.

### Steps to Reproduce
1. Enter IS-CLI: `sonic-cli`
2. Execute: `show ntp`

### Expected Result
Either:
- Show all NTP information (server + associations + global)
- Default to `show ntp server`
- Display helpful message listing available subcommands

### Actual Result
```
sonic# show ntp
% Error: Ambiguous command
```

### Additional Information
Valid subcommands that work:
- `show ntp server` ✅
- `show ntp associations` ✅
- `show ntp global` ✅

### Impact
- Poor user experience
- Inconsistent with other SONiC commands
- Users must guess subcommands
- Documentation unclear

### Suggested Fix
1. Make `show ntp` an alias for `show ntp server` (most common use case)
2. OR display combined output from all subcommands
3. OR provide helpful error: "Usage: show ntp {server|associations|global}"

---

## BUG #3: NTP Hostname Validation Inconsistency

**Priority**: 🟡 **MEDIUM**
**Component**: NTP Configuration
**Feature**: SM_ISCLI_DROP1_FEATURE7

### Summary
The `config ntp add` command rejects hostnames claiming "Invalid IP address" when used without `--association-type`, but accepts hostnames when the flag is provided, creating inconsistent behavior.

### Steps to Reproduce
1. Attempt to add NTP server by hostname:
   ```bash
   sudo config ntp add time.google.com
   ```

### Expected Result
Hostname should be resolved and added as NTP server, OR consistent error for all hostname usage.

### Actual Result
```
Error: Invalid IP address: time.google.com
NTP server time.google.com added to configuration
Restarting ntp-config service...
```

### Working Alternative
```bash
sudo config ntp add --association-type pool pool.ntp.org
```
This works fine with hostname! ✅

### Test Evidence
```bash
# FAILS with hostname
admin@sonic:~$ sudo config ntp add time.google.com
Error: Invalid IP address: time.google.com

# WORKS with IP
admin@sonic:~$ sudo config ntp add 216.239.35.12
NTP server 216.239.35.12 added to configuration

# WORKS with hostname + flag
admin@sonic:~$ sudo config ntp add --association-type pool 1.pool.ntp.org
```

### Impact
- Confusing user experience
- Limits NTP server options
- Documentation doesn't explain this behavior
- Inconsistent validation logic

### Suggested Fix
1. Remove IP-only validation for `config ntp add` command
2. Accept both IP addresses and hostnames consistently
3. OR require `--association-type` for all cases and document clearly
4. Update error message: "Error: Please specify --association-type for hostnames"

---

## BUG #4: `show arp` and `show ndp` Not Available in IS-CLI

**Priority**: 🟡 **MEDIUM**
**Component**: IS-CLI Command Set
**Feature**: SM_ISCLI_DROP1_FEATURE8 (Clear ARP/ND)

### Summary
Users can clear ARP and NDP tables using `sonic-clear arp` and `sonic-clear ndp`, but cannot view ARP/NDP entries using IS-CLI show commands, forcing them to exit to admin shell.

### Steps to Reproduce
1. Enter IS-CLI: `sonic-cli`
2. Execute: `show arp`
3. Execute: `show ndp`

### Expected Result
Display ARP/NDP table similar to Click CLI:
```
Address       MacAddress         Iface    Vlan    Status
----------    -----------------  -------  ------  --------
192.168.1.1   aa:bb:cc:dd:ee:ff  eth0     -       REACHABLE
```

### Actual Result
```
sonic# show arp
         ^
% Error: Invalid input detected at '^' marker.

sonic# show ndp
         ^
% Error: Invalid input detected at '^' marker.
```

### Workaround
Exit to admin shell:
```bash
exit
ip neigh show      # View ARP
ip -6 neigh show   # View NDP
```

### Impact
- Incomplete feature implementation
- User must switch between CLI modes
- Cannot verify results of `sonic-clear arp` in same session
- Asymmetric functionality (clear works, show doesn't)

### Suggested Fix
Implement IS-CLI commands:
- `show arp` → display IPv4 neighbor table
- `show arp <interface>` → filter by interface
- `show ndp` → display IPv6 neighbor table
- `show ndp <interface>` → filter by interface

---

## BUG #5: Missing pcie.yaml Configuration File

**Priority**: 🟢 **LOW**
**Component**: Platform Monitoring
**Feature**: SM_ISCLI_DROP1_FEATURE1

### Summary
The `show platform pcieinfo --check` command reports missing pcie.yaml configuration file, preventing PCIe device validation.

### Steps to Reproduce
```bash
show platform pcieinfo --check
```

### Expected Result
PCIe device validation against configuration file with pass/fail status.

### Actual Result
```
Error: /usr/share/sonic/device/x86_64-kvm_x86_64-r0/pcie.yaml file doesn't exist! Can't verify device.
```

### Additional Information
- `show platform pcieinfo` works fine (displays device list)
- Only `--check` validation fails
- May be expected for Virtual Switch platform

### Impact
- Cannot validate PCIe devices in automated testing
- Platform-specific feature may need hardware config
- Virtual Switch limitation

### Suggested Fix
1. Provide default pcie.yaml for VS platform (even if empty)
2. OR better error message: "PCIe validation not supported on Virtual Switch"
3. OR document as hardware-only feature

---

## BUG #6: Platform Firmware Commands Ambiguous

**Priority**: 🟢 **LOW**
**Component**: Platform Monitoring
**Feature**: SM_ISCLI_DROP1_FEATURE1

### Summary
Platform firmware-related commands return ambiguity errors instead of working or providing clear guidance.

### Steps to Reproduce
```bash
show platform firmware status
```

### Actual Result
```
% Error: Ambiguous command
```

### Impact
- Documentation may reference commands that don't work
- Users cannot check firmware versions in IS-CLI

### Test Status
⚠️ **Requires further investigation** - may be virtual switch limitation

---

## Additional Observations (Not Bugs)

### ✅ Working as Expected

1. **Platform commands in Virtual Switch**
   - `show platform psustatus` → "Failed to get PSU status" ✅ Expected (no PSU in VS)
   - `show platform temperature` → "Not detected" ✅ Expected (no sensors in VS)
   - `show platform fan` → "Not detected" ✅ Expected (no fans in VS)
   - These require physical hardware testing

2. **ZTP Functionality**
   - All ZTP commands work perfectly ✅
   - Enable/disable/status all functional
   - State persistence verified

3. **sonic-clear Performance**
   - `sonic-clear arp` executes in ~0.437 seconds ✅
   - `sonic-clear ndp` works correctly ✅
   - Multiple consecutive clears stable ✅

4. **NTP Functionality**
   - IP-based NTP server add/delete works perfectly ✅
   - chrony integration confirmed ✅
   - CONFIG_DB persistence verified ✅
   - VRF ping successful ✅

---

## Testing Summary

| Feature | Total Tests | Pass | Fail | Bugs Found |
|---------|-------------|------|------|------------|
| Platform Components | 9 | 6 | 3 | 3 |
| ZTP | 6 | 6 | 0 | 0 |
| NTP | 13 | 10 | 3 | 2 |
| Clear ARP/ND | 9 | 7 | 2 | 1 |
| **TOTAL** | **37** | **29** | **8** | **6** |

**Overall Pass Rate**: 78.4% (excluding expected VS limitations)

---

## Recommended Actions

### Immediate (High Priority)
1. ✅ Fix IS-CLI flag support OR document limitation clearly
2. ✅ Resolve `show ntp` ambiguity with default subcommand
3. ✅ Add `show arp` and `show ndp` to IS-CLI command set

### Short Term (Medium Priority)
4. ✅ Standardize NTP hostname validation
5. ✅ Update all IS-CLI documentation with correct syntax

### Long Term (Low Priority)
6. ✅ Provide pcie.yaml for Virtual Switch platform
7. ✅ Investigate firmware command ambiguity
8. 🔬 Schedule physical hardware testing for platform monitoring features

---

## Copy-Paste Ready JIRA Format

### For BUG #1 (IS-CLI Flags)

```
Summary: IS-CLI does not support command-line flags (--json, --verbose, --help)

Description:
IS-CLI mode does not support any command-line flags that are available in Click CLI mode.

Steps to Reproduce:
1. sonic-cli
2. show platform summary --json

Expected: JSON output
Actual: Error: Invalid input detected at '^' marker

Environment:
- Build: 202505-smci-dev-iscli-2025-12-30T02-57-47
- Platform: x86_64-kvm_x86_64-r0
- CLI Mode: IS-CLI

Impact: Users cannot get structured output; automation scripts will fail

Priority: High
Component: IS-CLI Core
```

### For BUG #2 (show ntp ambiguous)

```
Summary: show ntp command returns ambiguous error

Description:
The 'show ntp' command in IS-CLI returns an ambiguity error instead of showing NTP information.

Steps to Reproduce:
1. sonic-cli
2. show ntp

Expected: Display NTP information or helpful subcommand list
Actual: % Error: Ambiguous command

Workaround: Use 'show ntp server', 'show ntp associations', or 'show ntp global'

Environment:
- Build: 202505-smci-dev-iscli-2025-12-30T02-57-47
- Platform: x86_64-kvm_x86_64-r0

Impact: Poor user experience; users must guess valid subcommands

Priority: High
Component: NTP
```

### For BUG #3 (NTP hostname validation)

```
Summary: NTP hostname validation is inconsistent

Description:
'config ntp add' rejects hostnames without --association-type flag but accepts them with the flag.

Steps to Reproduce:
1. sudo config ntp add time.google.com
   Result: Error: Invalid IP address
2. sudo config ntp add --association-type pool time.google.com
   Result: Success

Expected: Consistent behavior for hostname validation

Environment:
- Build: 202505-smci-dev-iscli-2025-12-30T02-57-47
- Platform: x86_64-kvm_x86_64-r0

Impact: Confusing user experience; inconsistent validation logic

Priority: Medium
Component: NTP Configuration
```

### For BUG #4 (show arp/ndp not in IS-CLI)

```
Summary: show arp and show ndp commands not available in IS-CLI

Description:
Users can clear ARP/NDP using sonic-clear commands but cannot view them in IS-CLI mode.

Steps to Reproduce:
1. sonic-cli
2. show arp

Expected: Display ARP table
Actual: Error: Invalid input detected at '^' marker

Workaround: Exit IS-CLI and use 'ip neigh show'

Environment:
- Build: 202505-smci-dev-iscli-2025-12-30T02-57-47
- Platform: x86_64-kvm_x86_64-r0

Impact: Incomplete feature; users must switch CLI modes; asymmetric functionality

Priority: Medium
Component: IS-CLI Command Set
```

### For BUG #5 (pcie.yaml missing)

```
Summary: Missing pcie.yaml configuration file for Virtual Switch

Description:
'show platform pcieinfo --check' reports missing pcie.yaml file.

Steps to Reproduce:
1. show platform pcieinfo --check

Expected: PCIe validation results
Actual: Error: pcie.yaml file doesn't exist

Environment:
- Build: 202505-smci-dev-iscli-2025-12-30T02-57-47
- Platform: x86_64-kvm_x86_64-r0 (Virtual Switch)

Impact: Cannot validate PCIe devices; may be VS platform limitation

Priority: Low
Component: Platform Monitoring
```

### For BUG #6 (firmware commands ambiguous)

```
Summary: Platform firmware commands return ambiguous error

Description:
Platform firmware-related commands are ambiguous in IS-CLI.

Steps to Reproduce:
1. show platform firmware status

Expected: Firmware version information
Actual: % Error: Ambiguous command

Environment:
- Build: 202505-smci-dev-iscli-2025-12-30T02-57-47
- Platform: x86_64-kvm_x86_64-r0

Impact: Users cannot check firmware versions in IS-CLI

Priority: Low
Component: Platform Monitoring

Note: Requires further investigation - may be virtual switch limitation
```

---

## Test Evidence Files

- **Automated Test Script**: `iscli_test_suite.py`
- **Test Execution Report**: `iscli_test_report_YYYYMMDD_HHMMSS.json`
- **Manual Test Output**: Available in conversation history

All bugs verified on both test VMs (192.168.100.73 and 192.168.100.103)
