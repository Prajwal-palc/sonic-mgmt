# IS-CLI Automated Test Suite - Usage Guide

## Quick Start

### 1. Copy the test script to your SONiC device
```bash
scp iscli_test_suite.py admin@192.168.100.73:~/
```

### 2. SSH into your SONiC device
```bash
ssh admin@192.168.100.73
# Password: jira@123
```

### 3. Run the test suite
```bash
sudo python3 iscli_test_suite.py
```

## What the Script Tests

### ✅ Platform Components (SM_ISCLI_DROP1_FEATURE1)
- show platform summary (IS-CLI vs Admin Shell)
- Flags validation (--json should fail)
- PSU status, temperature, fan, SSD health
- PCIe info and configuration

### ✅ ZTP (SM_ISCLI_DROP1_FEATURE2)
- show ztp-status
- Enable/disable ZTP
- Service status verification
- State persistence checks

### ✅ NTP (SM_ISCLI_DROP1_FEATURE7)
- show ntp commands (ambiguity test)
- Add/delete NTP servers (IP vs hostname)
- Pool associations
- chrony integration
- CONFIG_DB verification
- VRF ping tests

### ✅ Clear ARP/ND (SM_ISCLI_DROP1_FEATURE8)
- ARP/NDP viewing
- Clear operations with timing
- Repopulation tests
- Multiple clear stability
- IS-CLI mode limitations

## Expected Output

```
============================================================
IS-CLI COMPREHENSIVE TEST SUITE
Started: 2025-12-30 HH:MM:SS
============================================================

============================================================
PLATFORM COMPONENTS (SM_ISCLI_DROP1_FEATURE1)
============================================================
  [✓ PASS] show platform summary (IS-CLI)
  [✓ PASS] show platform summary --json (should fail)
      Note: BUG: Flags not supported in IS-CLI
  ...

============================================================
TEST SUMMARY
============================================================

PLATFORM:
  Total: 9
  Pass: 9
  Fail: 0
  Skip: 0
  Pass Rate: 100.0%

...

OVERALL:
  Total Tests: 37
  Passed: 35
  Failed: 2
  Skipped: 0
  Overall Pass Rate: 94.6%

  Test Duration: 45.2 seconds
  Detailed report saved to: iscli_test_report_20251230_HHMMSS.json
```

## Output Files

1. **Console output**: Real-time colored test results
2. **JSON report**: `iscli_test_report_YYYYMMDD_HHMMSS.json`
   - Summary statistics
   - Per-feature results
   - Individual test details
   - Execution notes and bugs found

## Known Bugs Tested

The script validates these known issues:

1. **IS-CLI flags not supported** - Tests that --json, --verbose fail
2. **Ambiguous commands** - Tests that bare `show ntp` fails appropriately
3. **Hostname validation** - Tests NTP hostname without --association-type fails
4. **Missing IS-CLI commands** - Tests that `show arp`/`show ndp` aren't available
5. **Missing config files** - Tests for pcie.yaml warning

## Customization

Edit the script to:
- Add new test cases to each `test_*()` function
- Adjust timeout values in `run_command(timeout=30)`
- Modify expected output strings
- Change test target IPs/hostnames

## Troubleshooting

### Permission denied
```bash
sudo python3 iscli_test_suite.py  # Run with sudo
```

### Module not found
```bash
# All modules are Python3 standard library
python3 --version  # Ensure Python 3.6+
```

### Tests hang
- Check network connectivity
- Verify SONiC services are running: `systemctl status`
- Increase timeout in script if needed

## Test Environment

- **Platform**: x86_64-kvm_x86_64-r0 (Virtual Switch)
- **SONiC Build**: 202505-smci-dev-iscli-2025-12-30T02-57-47
- **Python**: 3.x (standard library only, no dependencies)
- **Privileges**: sudo required for config commands

## Next Steps

1. ✅ Run automated tests
2. 📊 Review JSON report
3. 🐛 Create JIRA tickets for failures (see JIRA_BUGS_TEMPLATE.md)
4. 🔄 Test on second VM (192.168.100.103) for consistency
5. 🖥️ Schedule physical hardware testing for platform features
