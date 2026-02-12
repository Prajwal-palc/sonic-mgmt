# Full Regression Batch Test Suite

## Overview

`batch_full_run.sh` is a comprehensive test automation script for running SPyTest regression tests in feature-based batches. It supports both full regression testing (all features) and selective execution of specific feature batches.

## Features

- **13 Feature Batches** (A-M) covering BGP, OSPF, switching, and system features
- **Selective Execution** - Run only the batches you need
- **Special Keywords** - Group batches by category (BGP, OSPF, SYSTEM)
- **Flexible Input** - Use batch letters (A-M), full names, or keywords
- **Automated Dashboard** - Generates graphical test results dashboard
- **BGP Docker Restart** - Automatic BGP container cleanup between tests (Batch B)
- **NTP Server Setup** - Automated NTP server configuration for NTP tests (Batch M)

## Available Batches

| Letter | Batch Name | Description | Testbed Required |
|--------|------------|-------------|------------------|
| **A** | `BGP_NEG_FLAP_RR` | BGP Negative/Flap/RR/Restart tests | testbed_vs_3rr.yaml |
| **B** | `BGP_IPV4_FEATURES` | BGP IPv4 iBGP/eBGP feature tests | testbed_vs_2node.yaml |
| **C** | `BGP_ISCLI_BESTPATH` | BGP IS-CLI Best Path selection | testbed_2vs.yaml |
| **D** | `BGP_ISCLI_CAPABILITY` | BGP IS-CLI Capability tests | testbed_2vs.yaml |
| **E** | `BGP_ISCLI_EVPN` | BGP IS-CLI EVPN tests | testbed_2vs.yaml |
| **F** | `BGP_ISCLI_PG_ADV` | BGP IS-CLI Peer Group Advanced | testbed_2vs.yaml |
| **G** | `OSPF_ISCLI_MASTER` | OSPF IS-CLI comprehensive tests | testbed_4node.yaml |
| **H** | `PORTCHANNEL_ISCLI` | PortChannel IS-CLI tests | testbed_2node.yaml |
| **I** | `VLAN_ISCLI` | VLAN IS-CLI tests | testbed_2node.yaml |
| **J** | `HW_INTERFACE_EVENTS` | Hardware interface event tests | testbed_hw.yaml |
| **K** | `SYS_INTERFACE_EVENTS` | System interface event tests | testbed_2node.yaml |
| **L** | `SYS_AAA` | System AAA authentication tests | testbed_vs_1node.yaml |
| **M** | `SYS_NTP` | System NTP tests (requires setup) | testbed_vs_1node.yaml |
| **N** | `STATIC_ROUTING` | Static route tests (IPv4/IPv6, basic, VRF, blackhole, ECMP) | testbed_vs_1node.yaml |

## Special Keywords

Convenient shortcuts for running multiple related batches:

| Keyword | Batches Included | Description |
|---------|------------------|-------------|
| `BGP` | A, B, C, D, E, F | All BGP-related tests |
| `OSPF` | G | OSPF tests |
| `ROUTING` | A, B, C, D, E, F, G, N | All routing tests (BGP, OSPF, Static) |
| `SYSTEM` | L, M | System-level tests (AAA, NTP) |
| `ALL` | A-N | All batches (same as no arguments) |

## Usage

### Basic Commands

```bash
# Show help and all options
./batch_full_run.sh --help

# List all available batches
./batch_full_run.sh --list

# Run all batches (full regression)
./batch_full_run.sh
```

### Selective Execution Examples

#### 1. Run specific batches by letter
```bash
# Run batches A, B, and C only
./batch_full_run.sh --features A,B,C
```

#### 2. Run batches by full name
```bash
# Run BGP negative tests and NTP tests
./batch_full_run.sh --features BGP_NEG_FLAP_RR,SYS_NTP
```

#### 3. Use special keywords
```bash
# Run all BGP tests (batches A-F)
./batch_full_run.sh --features BGP

# Run all routing tests (BGP, OSPF, Static - batches A-G, N)
./batch_full_run.sh --features ROUTING

# Run all system tests (batches L-M)
./batch_full_run.sh --features SYSTEM

# Run OSPF tests only
./batch_full_run.sh --features OSPF

# Run static routing tests only
./batch_full_run.sh --features N
```

#### 4. Mix letters, names, and keywords
```bash
# Run BGP batch A, all OSPF tests, and NTP
./batch_full_run.sh --features A,OSPF,M

# Run all BGP tests + system tests
./batch_full_run.sh --features BGP,SYSTEM
```

## Output and Logs

### Log Directory Structure
```
./logs/
└── YYYYMMDD/                    # Date directory (e.g., 20260212)
    ├── BGP_NEG_FLAP_RR/
    │   └── HHMMSS/              # Time directory with test results
    │       ├── results_*.csv
    │       ├── summary.txt
    │       ├── dlog-*.log
    │       └── ...
    ├── BGP_IPV4_FEATURES/
    │   └── HHMMSS/
    ├── SYS_NTP/
    │   └── HHMMSS/
    └── dashboard/
        └── full_regression_dashboard_YYYYMMDD_HHMMSS.html
```

### Dashboard

After completion, a graphical dashboard is automatically generated:

**Location:**
- `./logs/YYYYMMDD/dashboard/full_regression_dashboard_YYYYMMDD_HHMMSS.html`
- `~/Dashboard/FULL_REGRESSION/full_regression_dashboard_YYYYMMDD_HHMMSS.html` (copy)

**Dashboard Features:**
- Pass/Fail summary per batch
- Test execution times
- Historical trend tracking
- Interactive charts

## Pre-requisites

### Required Testbeds

Ensure the following testbed files exist before running batches:

- `./testbeds/testbed_vs_3rr.yaml` (for Batch A)
- `./testbeds/testbed_vs_2node.yaml` (for Batch B)
- `./testbeds/testbed_2vs.yaml` (for Batches C, D, E, F)
- `./testbeds/testbed_4node.yaml` (for Batch G)
- `./testbeds/testbed_2node.yaml` (for Batches H, I, K)
- `./testbeds/testbed_hw.yaml` (for Batch J - hardware tests)
- `./testbeds/testbed_vs_1node.yaml` (for Batches L, M)

### Special Requirements

**Batch B (BGP_IPV4_FEATURES):**
- Requires `restart_bgp_docker.py` script in current directory
- BGP docker is automatically restarted between test files

**Batch M (SYS_NTP):**
- Requires sudo access for NTP server setup
- NTP setup scripts must exist:
  - `./tests/system/ntp/setup_ntp_server.sh`
  - `./tests/system/ntp/verify_ntp_server.sh`
  - `./tests/system/ntp/fix_ntp_server.sh`
  - `./tests/system/ntp/vars_ntp_iscli_local.yaml`

## Common Use Cases

### Development Testing

Run only the feature you're working on:

```bash
# Testing BGP feature
./batch_full_run.sh --features A

# Testing VLAN changes
./batch_full_run.sh --features I
```

### Pre-Release Verification

Run all BGP and OSPF tests:

```bash
./batch_full_run.sh --features BGP,OSPF
```

### Quick Sanity Check

Run fastest batches for smoke testing:

```bash
./batch_full_run.sh --features L,M
```

### Full Nightly Regression

Run everything:

```bash
./batch_full_run.sh
# OR
./batch_full_run.sh --features ALL
```

## Execution Behavior

### Batch Execution Flow

1. **Argument Parsing** - Process command-line flags
2. **Batch Selection** - Determine which batches to run
3. **Sequential Execution** - Run selected batches in order (A→M)
4. **Error Handling** - Continue to next batch even if one fails
5. **Dashboard Generation** - Create comprehensive HTML report
6. **Completion Summary** - Display log locations and dashboard links

### Skipped Batches

When using selective mode, skipped batches are clearly indicated:

```
Skipping Batch C (BGP_ISCLI_BESTPATH) - not selected
Skipping Batch D (BGP_ISCLI_CAPABILITY) - not selected
...
```

### Failure Handling

- If a batch fails (non-zero exit code), a warning is displayed
- Execution continues to next batch
- Dashboard will show failed batches in red

## Advanced Options

### Modifying Test Parameters

All `run_batch` calls use these default parameters:
- `--tryssh 1` - Enable SSH connection attempts
- `--log-level debug` - Debug logging level
- `--skip-init-config` - Skip initial device configuration
- `--ifname-type native` - Use native interface names

To modify these, edit the `run_batch()` function in `batch_full_run.sh`.

### Custom Log Directory

Default: `./logs/YYYYMMDD/`

To change, modify the `BASE_LOG` variable at the top of the script:

```bash
BASE_LOG="./logs/${DATE_DIR}"  # Change this line
```

## Troubleshooting

### Common Issues

**1. Permission Denied**
```bash
chmod +x batch_full_run.sh
```

**2. Testbed Not Found**
```
ERROR: testbed file not found
```
**Solution:** Ensure all required testbed YAML files exist in `./testbeds/`

**3. NTP Setup Fails (Batch M)**
```bash
sudo ./tests/system/ntp/setup_ntp_server.sh
```
**Solution:** Run NTP setup manually first, or skip batch M

**4. BGP Docker Restart Fails (Batch B)**
**Solution:** Ensure `restart_bgp_docker.py` exists and is executable

### Viewing Results

Check individual batch results:
```bash
# View summary
cat ./logs/YYYYMMDD/BGP_NEG_FLAP_RR/HHMMSS/summary.txt

# View detailed CSV results
cat ./logs/YYYYMMDD/BGP_NEG_FLAP_RR/HHMMSS/results_*.csv

# View device logs
less ./logs/YYYYMMDD/BGP_NEG_FLAP_RR/HHMMSS/dlog-D1-*.log
```

## Performance Tips

1. **Run batches in parallel** - Not currently supported by this script, but you can run multiple instances with different `--features` selections in separate terminal sessions

2. **Skip hardware tests** when running on virtual topology:
   ```bash
   # Exclude Batch J (requires hardware)
   ./batch_full_run.sh --features A,B,C,D,E,F,G,H,I,K,L,M
   ```

3. **Use targeted selection** for faster iteration during development

## Integration with CI/CD

Example Jenkins/GitLab CI usage:

```bash
#!/bin/bash
# Run BGP and system tests in CI pipeline

./batch_full_run.sh --features BGP,SYSTEM

# Check exit code
if [ $? -ne 0 ]; then
    echo "Some tests failed - check dashboard"
    exit 1
fi

# Archive dashboard
cp ./logs/*/dashboard/*.html $WORKSPACE/artifacts/
```

## Related Scripts

- `batch_sm_iscli.sh` - SM_ISCLI specific test batches
- `dashboard/scripts/generate_graphical_dashboard.py` - Dashboard generator
- `dashboard/scripts/generate_historical_dashboard.py` - Historical trends

## Support

For issues or questions:
1. Check this README
2. Run `./batch_full_run.sh --help`
3. Review test logs in `./logs/YYYYMMDD/`
4. Check SPyTest documentation in `Doc/intro.md`

## Version History

- **v2.1** (2026-02-12) - Added BATCH-N (STATIC_ROUTING) with 13 static route tests, added ROUTING keyword
- **v2.0** (2026-02-12) - Added selective batch execution, special keywords, improved help
- **v1.0** - Initial full regression script

---

**Last Updated:** 2026-02-12
**Maintained By:** Test Automation Team

## Batch N Details - Static Routing Tests

The STATIC_ROUTING batch (N) includes comprehensive static route testing:

**IPv4 Tests:**
- `test_sm_iscli_7.py` - SM_ISCLI_7 static route validation
- `test_static_route_basic.py` - Basic static route functionality
- `test_static_route_basic_klish.py` - Basic static routes (Klish CLI)
- `test_static_route_blackhole.py` - Blackhole route testing
- `test_static_route_mgmt_vrf_klish.py` - Management VRF static routes
- `test_static_route_vrf_klish.py` - VRF static routes

**IPv6 Tests:**
- `test_static_ipv6_route_basic_1.py` - Basic IPv6 static routes
- `test_static_ipv6_negative.py` - IPv6 negative test scenarios
- `test_static_ipv6_blackhole.py` - IPv6 blackhole routes
- `test_static_ipv6_ecmp.py` - IPv6 ECMP (Equal-Cost Multi-Path)
- `test_static_ipv6_scale.py` - IPv6 route scaling tests
- `test_static_ipv6_vrf.py` - IPv6 VRF static routes
- `test_static_ipv6_mgmt_vrf.py` - IPv6 management VRF static routes

**Test Coverage:**
- Basic static route CRUD operations
- VRF (Virtual Routing and Forwarding) support
- Management VRF isolation
- Blackhole route functionality
- ECMP load balancing
- Negative test scenarios
- Scale testing
- Both IPv4 and IPv6 protocols
- Klish (IS-CLI) interface validation
