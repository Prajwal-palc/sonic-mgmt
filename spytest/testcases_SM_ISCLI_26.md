# SM_ISCLI_26: Platform and Interface CLI Validation

**Author:** Athira
**Date:** 2026-02-11
**Feature Category:** System CLI
**Test Directory:** `spytest/tests/system/cli/`
**Test File:** `test_sm_iscli_26_platform_interface_cli.py`
**Vars File:** `spytest/vars/system/cli/vars_sm_iscli_26.yaml`

---

## Overview

Validate platform and interface CLI commands for completeness, correctness, and consistency between click and klish (IS-CLI) modes. Focus on identifying missing options, incomplete help text, and non-functional subcommands.

---

## Test Scope

### Commands Under Test

1. **Platform Commands:**
   - `show platform ssdhealth`

2. **Ping Utility:**
   - Ping behavior with packet loss
   - Ping help text completeness

3. **Traceroute:**
   - Traceroute availability and functionality

4. **Interface Transceiver Commands:**
   - `show interface transceiver pm`
   - `show interface transceiver lpmode`
   - `show interface transceiver error-status verbose`

---

## Test Cases

### TC_26.1: Platform SSD Health Disk Option

**Objective:** Verify `show platform ssdhealth` supports disk specification parameter in klish mode (parity with click).

**Steps:**
1. Execute `show platform ssdhealth` in klish mode
2. Check if disk parameter option exists (e.g., `show platform ssdhealth <disk>`)
3. Compare with click mode: `show platform ssdhealth <disk>`

**Expected Result:**
- Klish mode should support disk parameter option matching click CLI behavior
- OR document as known limitation if intentionally unsupported

**Priority:** Medium
**Type:** Feature Parity

---

### TC_26.4: Ping Help Text Completeness

**Objective:** Verify ping command displays actual options instead of generic "normal options" text.

**Steps:**
1. Execute `ping ?` or `ping --help`
2. Check if actual ping options are displayed
3. Verify options include: count, interval, timeout, packet size, etc.

**Expected Result:**
- Help text should display comprehensive list of available ping options
- Should NOT display generic "normal options" placeholder text

**Priority:** Medium
**Type:** Usability

---

### TC_26.5: Traceroute Command Availability

**Objective:** Confirm traceroute command is available and functional in klish mode.

**Steps:**
1. Execute `traceroute <destination>` in klish mode
2. Verify command executes successfully
3. Validate output shows hop-by-hop route trace

**Expected Result:**
- Traceroute command is available
- Output displays network path with hop latencies

**Priority:** Medium
**Type:** Functional

---

### TC_26.6: Interface Transceiver PM Subcommand

**Objective:** Verify `show interface transceiver pm` displays performance monitoring data or appropriate message.

**Steps:**
1. Execute `show interface transceiver pm`
2. Check if command returns meaningful data
3. If not supported, verify appropriate error/unsupported message

**Expected Result:**
- Command displays PM data for transceivers
- OR returns clear "not supported" / "not implemented" message
- **Recommendation:** Remove command if permanently non-functional

**Priority:** Low
**Type:** Cleanup

---

### TC_26.7: Interface Transceiver LPMode Subcommand

**Objective:** Verify `show interface transceiver lpmode` displays low-power mode status or appropriate message.

**Steps:**
1. Execute `show interface transceiver lpmode`
2. Check if command returns meaningful data
3. If not supported, verify appropriate error/unsupported message

**Expected Result:**
- Command displays LP mode status for transceivers
- OR returns clear "not supported" / "not implemented" message
- **Recommendation:** Remove command if permanently non-functional

**Priority:** Low
**Type:** Cleanup

---

### TC_26.8: Interface Transceiver Error-Status Verbose

**Objective:** Verify `show interface transceiver error-status verbose` displays verbose error information.

**Steps:**
1. Execute `show interface transceiver error-status verbose`
2. Check if verbose output differs from non-verbose mode
3. Verify if "not implemented" message is displayed

**Expected Result:**
- Command displays verbose error status details
- OR returns clear "not implemented" message
- **Recommendation:** Remove `verbose` option if not implemented

**Priority:** Low
**Type:** Cleanup

---

## Topology Requirements

- **Min Topology:** Single DUT (`D1`)
- **Device Type:** Hardware or Virtual (both supported)
- **Transceivers:** At least one SFP/QSFP interface with transceiver present (for TC_26.6-26.8)

**Topology Diagram:**
```
# Topology - 1 node
# +--------------------+
# |        DUT1        |
# |   (Platform CLI)   |
# +--------------------+
```

---

## Pre-requisites

- SONiC device with platform support
- At least one interface with transceiver installed (for interface tests)
- Network connectivity for ping/traceroute tests (optional for basic CLI validation)

---

## CLI Types Tested

- **klish (IS-CLI):** Primary focus
- **click:** For parity comparison (TC_26.1)

---

## Test Variables (YAML)

```yaml
defaults:
  cli_type: klish
  min_topology:
    - "D1"

testcases:
  "26.1":
    title: "Platform SSD Health Disk Option"
    commands:
      klish: "show platform ssdhealth"
      click: "show platform ssdhealth"

  "26.4":
    title: "Ping Help Text Completeness"
    command: "ping"
    help_flags: ["?", "--help", "-h"]

  "26.5":
    title: "Traceroute Command Availability"
    test_destination: "8.8.8.8"

  "26.6":
    title: "Interface Transceiver PM Subcommand"
    command: "show interface transceiver pm"

  "26.7":
    title: "Interface Transceiver LPMode Subcommand"
    command: "show interface transceiver lpmode"

  "26.8":
    title: "Interface Transceiver Error-Status Verbose"
    command: "show interface transceiver error-status verbose"
```

---

## Implementation Notes

1. **Negative Testing:** Test cases 26.6-26.8 are candidates for negative testing (verify graceful handling of unsupported features)

2. **Command Cleanup:** If commands consistently return "not implemented" or no data, recommend removal from CLI to avoid user confusion

3. **Feature Parity:** TC_26.1 specifically checks click vs klish parity for platform commands

4. **Optional Enhancements:** TC_26.3 and TC_26.4 are lower priority improvements

---

## Expected Test Runtime

- **Per Test Case:** 5-15 seconds
- **Total Suite:** < 2 minutes

---

## Markers

```python
@pytest.mark.topology("D1")
@pytest.mark.system
@pytest.mark.cli_validation
@pytest.mark.negative  # For TC_26.6-26.8
```

---

## Success Criteria

- All functional commands (TC_26.5) execute successfully
- Non-functional commands (TC_26.6-26.8) return clear error messages
- Help text is informative and complete (TC_26.4)
- Feature parity documented or implemented (TC_26.1)

---

## Known Issues / Observations

From manual testing on SONiC.202505-smci-dev-iscli-2026-01-24:

1. ✅ `show platform ssdhealth` - Works, displays disk health
2. ⚠️ `ping` help - Shows "normal options" placeholder
3. ✅ `traceroute` - Works correctly
4. ⚠️ `show interface transceiver pm` - Returns no data
5. ⚠️ `show interface transceiver lpmode` - Returns no data
6. ⚠️ `show interface transceiver error-status verbose` - "Not implemented" message
7. ✅ Other transceiver commands work: `eeprom`, `info`, `presence`, `status`, `error-status`

---

## Recommendations

### Medium Priority
1. Enhance ping help text to show actual options
2. Verify platform ssdhealth disk parameter support

### Low Priority (Cleanup)
3. Remove non-functional transceiver subcommands:
   - `show interface transceiver pm`
   - `show interface transceiver lpmode`
   - `show interface transceiver error-status verbose`
4. Consider ping packet loss auto-termination feature

---

## How to Run

```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/system/cli/test_sm_iscli_26_platform_interface_cli.py \
  --logs-path ./logs/sm_iscli_26_$(date +%F_%H%M%S) \
  --log-level debug \
  --skip-init-config \
  --ifname-type native \
  --port-init-wait 0
```

---

## References

- Manual test log from SONiC device (2026-01-25)
- SONiC CLI documentation
- SPyTest coding guideline: `spy_test_coding_guideline.md`
