# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SPyTest (SONiC Python Test Framework) is a PyTest-based test automation framework for validating SONiC (Software for Open Networking in the Cloud) network operating systems. The framework provides comprehensive infrastructure for device testing, traffic generation, and feature validation across routing, switching, QoS, and security domains.

## Core Architecture

The framework follows a layered architecture:

1. **Test Scripts** (`tests/`) - Test functions organized by feature area
2. **Feature APIs** (`apis/`) - Abstraction layer for device interactions, handles multiple CLI types (click, klish, REST, gNMI)
3. **Framework Core** (`spytest/`) - Device management, test orchestration, logging, and reporting
4. **Infrastructure** - Device access (SSH/Telnet), traffic generators, TextFSM parsing, Ansible orchestration

Key modules:
- `spytest/framework.py` (6,100+ lines) - Test orchestration and execution lifecycle
- `spytest/net.py` (7,200+ lines) - Device connection and CLI execution
- `spytest/testbed.py` (3,000+ lines) - Topology management
- `spytest/tgen/` - Traffic generator abstractions (Ixia, Spirent, Scapy)

## Development Commands

### Running Tests

Basic test execution:
```bash
./bin/spytest --testbed testbeds/testbed_2vs.yaml \
    tests/routing/static/test_static_route_basic.py \
    --logs-path ./logs/test_run
```

Run by PyTest marker:
```bash
./bin/spytest --testbed testbed_file.yaml -m community_pass --logs-path ./logs
```

Run test suite:
```bash
./bin/spytest --testbed testbed_file.yaml --test-suite dev-sanity --logs-path ./logs
```

Key command-line options:
- `--testbed-file` - Testbed YAML file (required)
- `--logs-path` - Output directory for logs/results
- `--logs-level` - Logging level (info, debug, etc.)
- `--file-mode` - Execute in file mode
- `-n/--numprocesses` - Parallel execution workers
- `--skip-init-config` - Skip initial configuration
- `--ifname-type` - Interface naming (native, standard, alias)

### Static Analysis

Run linting (uses Ruff by default, fallback to PyLint):
```bash
./bin/lint.sh                    # Lint entire codebase
./bin/lint.sh path/to/file.py   # Lint specific file
./bin/lint.sh path/to/dir/      # Lint directory

# Environment variables
LINT_TOOL=ruff ./bin/lint.sh    # Use ruff
LINT_TOOL=pylint ./bin/lint.sh  # Use pylint
```

Lint output files: `lint_errors.log`, `lint_report.log`, `lint_debug.log`

### Installation

Install/update dependencies:
```bash
./bin/upgrade_requirements.sh
```

## Test Script Structure

Standard test script pattern:
```python
import pytest
from spytest import st
import apis.routing.ip as ip_api

@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    # Module prologue - setup, load vars
    global vars
    vars = st.get_testbed_vars()
    yield
    # Module epilogue - cleanup

def test_my_feature():
    st.log("Starting test...")
    result = ip_api.configure_ip(vars.D1, vars.D1T1P1, "10.1.1.1/24")
    if not result:
        st.report_fail("ip_config_failed")
    st.report_pass("test_case_passed")
```

### Critical Patterns

1. **Test Variables**: Load from YAML files in `spytest/vars/`
   ```python
   vars = st.get_testbed_vars()  # Access D1, D2, D1T1P1, etc.
   ```

2. **Multi-CLI Support**: Tests specify and use CLI type
   ```python
   cli_type = st.get_ui_type(dut, cli_type="click")
   # Supports: click, klish, rest-patch, rest-put, gnmi
   ```

3. **Result Reporting**: Always use framework reporting functions
   ```python
   st.report_tc_pass(tcid, msgid, *args)   # Mark test case passed
   st.report_tc_fail(tcid, msgid, *args)   # Mark test case failed
   st.report_pass(msgid, *args)            # Pass and exit
   st.report_fail(msgid, *args)            # Fail and exit
   ```

4. **Logging Hierarchy**:
   ```python
   st.log("General message")      # Standard log
   st.debug("Debug details")      # Debug level
   st.banner("Section Header")    # Visual separator
   st.error("Error occurred")     # Error message
   ```

## Feature API Development

When creating or modifying feature APIs in `apis/`:

1. **Abstract CLI types** - Handle click, klish, REST, gNMI variants
2. **Use TextFSM templates** - For parsing CLI output (`templates/` directory)
3. **Return structured data** - Not raw CLI strings
4. **Handle version differences** - Support multiple SONiC versions

Example API structure:
```python
def show_ip_route(dut, vrf=None, cli_type=""):
    cli_type = st.get_ui_type(dut, cli_type=cli_type)

    if cli_type == "click":
        cmd = "show ip route"
        if vrf: cmd += f" vrf {vrf}"
    elif cli_type == "klish":
        cmd = "show ip route"
        if vrf: cmd += f" vrf {vrf}"

    output = st.show(dut, cmd, type=cli_type)
    return parse_output(output)  # Use TextFSM template
```

## Testbed Files

Located in `testbeds/`, define device topology in YAML:

```yaml
version: 2.0
devices:
  sonic1:
    device_type: sonic
    access: {protocol: ssh, ip: 192.168.1.10, port: 22}
    credentials: {username: admin, password: YourPaSsWoRd}
topology:
  sonic1:
    interfaces:
      Ethernet4: {EndDevice: sonic2, EndPort: Ethernet4}
```

Device naming convention:
- **D1, D2, D3...** or **DUT1, DUT2...** - Devices under test
- **T1, T2...** or **TGen** - Traffic generators
- **D1T1P1** - DUT1's port connected to TGen port 1

## Framework Conventions

### Interface Naming
- **Native**: `Ethernet0`, `Ethernet4` (internal SONiC names)
- **Alias**: `Eth1/1`, `Eth1/2` (user-friendly names)
- Set via `--ifname-type` flag

### Configuration Management
- Module-level configuration saved as "base config"
- Tests restore to base config between modules
- Use `st.apply_module_configuration()` and `st.clear_module_configuration()`

### Error Detection
- CLI output automatically checked against patterns in `testbeds/sonic_errors.yaml`
- Syslogs categorized: red=fail, yellow=report, green=ignore (configured in `reporting/syslogs.yaml`)
- Result types: Pass, Fail, Unsupported, EnvFail, TopoFail, ConfigFail

### Batch Processing
- Tests specify topology requirements in `modules.csv`
- Framework creates "buckets" (1D, 2D, 4D topologies)
- Tests executed in parallel based on available topology

## Log Files

After test execution, logs appear in `--logs-path` directory:

- `dlog-D1-<devicename>.log` - Per-device command/output logs
- `module_<modulename>.log` - Per-module logs
- `results.html` - HTML test report
- `consolidated_report.html` - Aggregated results
- `summary.txt` - Quick summary

## Important Notes

1. **No traditional conftest.py** - Uses custom PyTest plugin (`spytest/splugin.py`)
2. **TextFSM templates** - Located in `templates/`, with `templates/index` mapping commands to templates
3. **Traffic generators** - Requires external libraries (Ixia: /projects/scid/tgen or via SCID_TGEN_PATH)
4. **Python 3 required** - Framework tested with Python 3.8+
5. **Entry point** - Always use `./bin/spytest`, not direct pytest invocation

## Documentation

- `Doc/intro.md` - Comprehensive framework introduction (600 lines)
- `Doc/install.md` - Installation instructions
- `README.md` - Directory overview

## Current Development Focus

Recent work centers on routing protocols:
- Static routing test suite expansion (IPv4/IPv6)
- ECMP (Equal-Cost Multi-Path) test coverage
- BGP feature validation
- Traffic generator dependency removal for certain tests
