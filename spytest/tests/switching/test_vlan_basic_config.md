# Test Execution Knowledge Base: test_vlan_basic_config.py

**Script**: `tests/switching/test_vlan_basic_config.py`
**Author**: Shiva
**Created**: 2026-02-03
**Purpose**: Track execution history, errors, and resolutions for VLAN basic configuration test

---

## Test Overview

### Scenario
Validates basic VLAN creation and verification in running configuration:
1. Check initial running config (VLAN 200 should not exist)
2. Create VLAN 200 via sonic-cli (klish)
3. Enter interface Vlan 200 configuration
4. Verify VLAN 200 appears in running config (both 'vlan 200' and 'interface Vlan200')

### Topology
- **Type**: Standalone (1 DUT)
- **Testbed**: `testbeds/ztp_standalone.yaml`
- **DUT**: smic_sonic1 (192.168.100.81)

---

## Known Issues and Resolutions

### Issue #1: Pagination in `show running-configuration`

**Problem**:
- `show running-configuration` outputs `--more--` prompts that block script execution
- Script hangs waiting for user input

**Solution**:
```python
# Set terminal length to 0 before any show commands
cmd = "terminal length 0"
st.config(dut, cmd, type="klish", conf=False, skip_error_check=True)
```

**Status**: ✅ IMPLEMENTED in `setup_class()`

---

### Issue #2: XML Parser Errors (if encountered)

**Problem**:
- Some CLI commands may return XML parsing errors in certain SONiC versions
- Error message: `ERROR: XML parser error...`

**Solution**:
- Use `skip_error_check=True` in st.config() or st.show() calls
- Use `skip_tmpl=True` to skip template parsing if raw output is sufficient

**Status**: ⚠️ MONITORED (not yet encountered)

---

### Issue #3: Prompt Timeout Issues

**Problem**:
- sonic-cli may not return prompt after certain commands
- Common with configuration mode transitions

**Solution**:
- Send carriage return (CR) to get prompt back:
  ```python
  st.config(dut, "\r", type="klish", skip_error_check=True)
  ```
- Use `conf=False` parameter for non-config mode commands

**Status**: ⚠️ MONITORED (not yet encountered)

---

## Execution History

### Execution #1 - [DATE TO BE FILLED]

**Command**:
```bash
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/ztp_standalone.yaml \
  tests/switching/test_vlan_basic_config.py \
  --logs-path ./logs/test_vlan_basic_config_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native
```

**Status**: PENDING FIRST RUN

**Results**: N/A

**Errors**: N/A

**Observations**: N/A

**Actions Taken**: N/A

---

## Test Design Decisions

### 1. Terminal Length Handling
- **Decision**: Set terminal length to 0 in class setup
- **Rationale**: Prevents `--more--` pagination in all show commands throughout test execution
- **Alternative Considered**: Handle pagination per command (rejected - too complex)

### 2. Running Config Parsing
- **Decision**: Use regex pattern matching on raw output
- **Rationale**:
  - No TextFSM template available for full running config
  - Regex provides simple, reliable detection of VLAN sections
- **Patterns Used**:
  - `^\s*vlan\s+<id>\s*$` - Matches "vlan 200" definition
  - `^\s*interface\s+Vlan<id>\s*$` - Matches "interface Vlan200" section

### 3. Cleanup Strategy
- **Decision**: Cleanup in both setup_method() and teardown_method()
- **Rationale**: Ensures clean slate before test and cleanup after test
- **Note**: Uses try-except to handle case where VLAN doesn't exist

### 4. CLI Type
- **Decision**: Use "klish" CLI type exclusively
- **Rationale**: Test scenario from vlan.md shows sonic-cli (klish) commands
- **Alternative**: Could parametrize with click/klish (future enhancement)

---

## API Functions Used

### From `apis.switching.vlan`
- `create_vlan(dut, vlan_id, cli_type="klish")` - Create VLAN
- `delete_vlan(dut, vlan_id, cli_type="klish")` - Delete VLAN (cleanup)

### From SpyTest Framework
- `st.config(dut, commands, type="klish")` - Execute configuration commands
- `st.show(dut, command, type="klish", skip_tmpl=True)` - Execute show commands
- `st.get_testbed_vars()` - Get topology information
- `st.get_dut_names()` - Get list of DUTs from testbed
- `st.report_pass()/st.report_fail()` - Test result reporting
- `st.banner()` - Log visual separators
- `st.log()` - Standard logging

---

## Future Enhancements

1. **Multi-VLAN Testing**: Extend to test multiple VLANs (100, 200, 300)
2. **CLI Type Parametrization**: Test with both klish and click CLI types
3. **VLAN Configuration**: Add tests for VLAN member ports, IP addressing
4. **Negative Testing**: Test invalid VLAN IDs, duplicate VLAN creation
5. **Performance**: Measure configuration time for scale testing

---

## References

- **Coding Guidelines**: `guid.md`
- **Test Scenario**: `vlan.md`
- **Testbed File**: `testbeds/ztp_standalone.yaml`
- **VLAN APIs**: `apis/switching/vlan.py`
- **Framework Docs**: `Doc/intro.md`

---

## Notes for Future Executions

- Update this file after each test execution with results and any new errors encountered
- Follow @prequest.md guidance: "Don't repeat previous errors found in this file"
- Add new issues and resolutions as they are discovered
- Keep execution history updated with timestamps and results
