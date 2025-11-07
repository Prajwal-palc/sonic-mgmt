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

### Test Documentation
Each test file should include comprehensive docstring documentation:
```python
"""
FEATURE NAME - TEST SCENARIO

Author: Name
Copyright (C) 2024, Company

How to run:
  ./bin/spytest --tryssh 1 \\
  --testbed ./testbeds/testbed_vs_2d.yaml \\
  tests/feature/test_file.py \\
  --logs-path ./logs/test_$(date +%F_%H%M%S) \\
  --log-level debug --skip-init-config --ifname-type native

Description:
  Detailed description of test scenario and what it validates.

Pre-requisites:
  - Topology: two-node (D1-D2) | Supported: HW and Virtual
  - Feature flags / min SONiC version requirements
  - Required test variables (YAML): path/to/vars_file.yaml
"""
```

### Standard test script pattern:
```python
import pytest
from spytest import st, SpyTestDict
import apis.routing.ip as ip_api

# Module-level variables
vars = SpyTestDict()
data = SpyTestDict()

@pytest.fixture(scope="module", autouse=True)
def module_hooks(request):
    # Module prologue - setup, load vars
    global vars
    vars = st.ensure_min_topology("D1D2:1")  # or st.get_testbed_vars()

    # Initialize test data
    st.banner("MODULE PROLOGUE: Starting")
    # Setup configuration here
    yield

    # Module epilogue - cleanup
    st.banner("MODULE EPILOGUE: Cleanup")

def test_my_feature():
    st.log("Starting test...")
    result = ip_api.configure_ip(vars.D1, vars.D1T1P1, "10.1.1.1/24")
    if not result:
        st.report_fail("ip_config_failed")
    st.report_pass("test_case_passed")
```

Modern test pattern with external YAML configuration:
```python
from pathlib import Path
import yaml

DEFAULT_VAR_FILE = Path(__file__).resolve().parents[3] / "spytest/vars/feature/vars_file.yaml"

def initialize_data() -> None:
    """Load test configuration from YAML file"""
    try:
        with open(DEFAULT_VAR_FILE, "r") as f:
            payload = yaml.safe_load(f)
    except FileNotFoundError as error:
        pytest.skip(str(error))

    global vars, data
    vars = st.ensure_min_topology(*payload.get("min_topology", ["D1D2:1"]))
    data.config = SpyTestDict(payload)
```

### Critical Patterns

1. **Test Variables**: Load from YAML files in `spytest/spytest/vars/`
   ```python
   # Legacy approach
   vars = st.get_testbed_vars()  # Access D1, D2, D1T1P1, etc.

   # Modern approach - specify topology requirements
   vars = st.ensure_min_topology("D1D2:1", "D1T1:1")  # 1 link D1-D2, 1 link D1-TGen
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

5. **Test Case IDs**: Define test case identifiers for tracking
   ```python
   TC_IDS = SpyTestDict({
       "reachability": "TC-IP-STATIC-001",
       "route_absent": "TC-IP-STATIC-002",
   })
   ```

## Feature API Development

Feature APIs are organized by domain in `apis/`:
- `apis/routing/` - Routing protocols (BGP, OSPF, static routes, IP configuration)
- `apis/switching/` - L2 features (VLANs, STP, MAC, port channels)
- `apis/qos/` - QoS features (queues, policers, classifiers)
- `apis/security/` - Security features (ACLs, authentication)
- `apis/system/` - System features (interfaces, logging, basic config)
- `apis/common/` - Common utilities and helpers
- `apis/yang/` - YANG/REST/gNMI utilities

When creating or modifying feature APIs:

1. **Abstract CLI types** - Handle click, klish, REST, gNMI variants
2. **Use TextFSM templates** - For parsing CLI output (`templates/` directory)
3. **Return structured data** - Not raw CLI strings
4. **Handle version differences** - Support multiple SONiC versions
5. **Use st.show() for show commands** - Framework function for CLI execution
6. **Use st.config() for config commands** - Framework function for configuration

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
6. **Working directory** - Commands should be run from the `spytest/` root directory
7. **Module structure** - Core framework in `spytest/`, feature APIs in `apis/`, tests in `tests/`, utilities in `utilities/`

## Debugging and Development Workflow

### Running a Single Test
```bash
# Run single test with debug logging
./bin/spytest --testbed testbeds/testbed_2vs.yaml \
    tests/routing/static/test_static_route_basic.py::test_my_function \
    --logs-path ./logs/debug \
    --log-level debug \
    --skip-init-config
```

### Useful Command-Line Options for Development
- `--tryssh 1` - Enable SSH connection attempts
- `--skip-init-config` - Skip initial device configuration (faster for iterative testing)
- `--ifname-type native` - Use native interface names (Ethernet0, Ethernet4, etc.)
- `--file-mode` - Execute tests in file mode (single device at a time)
- `--logs-level debug` - Enable debug logging

### Viewing Results
After test execution:
1. Check `<logs-path>/dashboard.html` for overview
2. Review `<logs-path>/summary.txt` for quick summary
3. Inspect `<logs-path>/dlog-D1-*.log` for per-device CLI commands/output
4. Search module logs for "Report(" to find test results

### Common Utilities

Framework provides utility functions in `utilities/`:
- `utilities/common.py` - General purpose utilities (IP manipulation, string operations)
- `utilities/parallel.py` - Parallel test execution helpers
- `utilities/utils.py` - Framework-specific utilities

Core framework functions in `spytest/`:
- `spytest/infra.py` - Infrastructure functions (logging, error detection)
- `spytest/framework.py` - Test orchestration lifecycle
- `spytest/net.py` - Device connection and CLI execution

## Documentation

- `Doc/intro.md` - Comprehensive framework introduction (600+ lines)
- `Doc/install.md` - Installation instructions
- `README.md` - Directory overview

## Current Development Focus

Recent work centers on routing protocols:
- Static routing test suite expansion (IPv4/IPv6)
- ECMP (Equal-Cost Multi-Path) test coverage
- BGP feature validation
- Traffic generator dependency removal for certain tests
