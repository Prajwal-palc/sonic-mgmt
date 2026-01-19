# Automation Test Files - Branch: automation_files_by_athira

## Overview
This branch contains **116 files** necessary for executing BGP and NTP automation test scripts in the SPyTest framework.

Author: Athira
Date: January 2026
Repository: https://github.com/palcnetworks/sonic-mgmt
Branch: `automation_files_by_athira`

## File Summary

### Test Files (14 total)

#### BGP Tests (12 files)
1. `tests/routing/BGP/test_bgp_ipv4_basic_ebgp.py` - BGP IPv4 basic eBGP configuration
2. `tests/routing/BGP/test_bgp_svi_ipv4_ebgp.py` - BGP over SVI (VLAN interface) eBGP
3. `tests/routing/BGP/test_bgp_portchannel_ipv4_ebgp.py` - BGP over PortChannel eBGP
4. `tests/routing/BGP/test_bgp_loopback_ipv4_ebgp.py` - BGP over Loopback interface eBGP
5. `tests/routing/BGP/test_bgp_ipv4_basic.py` - BGP IPv4 basic iBGP configuration
6. `tests/routing/BGP/test_bgp_svi_ipv4.py` - BGP over SVI iBGP
7. `tests/routing/BGP/test_bgp_portchannel_ipv4.py` - BGP over PortChannel iBGP
8. `tests/routing/BGP/test_bgp_loopback_ipv4.py` - BGP over Loopback interface iBGP
9. `tests/routing/BGP/test_bgp_ebgp_connected_static_redistribution.py` - BGP route redistribution
10. `tests/routing/BGP/test_bgp_advanced_features.py` - BGP advanced features
11. `tests/routing/BGP/test_ipv4_bgp_route_reflector.py` - BGP route reflector
12. `tests/routing/BGP/test_bgp_med_weight.py` - BGP MED and weight attributes

#### NTP Tests (2 files)
13. `tests/system/ntp/test_ntp_iscli.py` - NTP IS-CLI automation (38 test cases)
14. `tests/system/ntp/test_ntp_functional.py` - NTP functional tests

### Variable Files (16 YAML files)
- **BGP Variable Files (14)**: Configuration files for each BGP test
  - vars_bgp_ipv4_basic_ebgp.yaml
  - vars_bgp_svi_ipv4_ebgp.yaml
  - vars_bgp_portchannel_ipv4_ebgp.yaml
  - vars_bgp_loopback_ipv4_ebgp.yaml
  - vars_bgp_ipv4_basic.yaml
  - vars_bgp_svi_ipv4.yaml
  - vars_bgp_portchannel_ipv4.yaml
  - vars_bgp_loopback_ipv4.yaml
  - vars_bgp_ebgp_connected_static_redistribution.yaml
  - vars_bgp_advanced_features.yaml
  - vars_ipv4_bgp_route_reflector.yaml
  - vars_bgp_med_weight.yaml

- **NTP Variable Files (2)**:
  - vars_ntp_iscli_local.yaml
  - vars_ntp_functional.yaml

- **Framework Configuration (2)**:
  - reporting/syslogs.yaml
  - testbeds/sonic_errors.yaml

### API Modules (40 files)
Located in `apis/` directory:

#### Common APIs (13 files)
- `apis/common/scapy_traffic.py` - Scapy traffic generation
- `apis/common/sonic_hooks.py`, `sonic_prompts.py`, `sonic_features.py`
- `apis/common/linux_hooks.py`, `linux_prompts.py`
- `apis/common/poe_hooks.py`, `poe_prompts.py`
- `apis/common/support.py`, `instrument.py`, `coverage.py`, `hooks.py`, `init.py`

#### Routing APIs (6 files)
- `apis/routing/bgp.py` - BGP configuration and verification
- `apis/routing/ip.py` - IP address and routing configuration
- `apis/routing/ip_rest.py` - IP REST API operations
- `apis/routing/route_map.py` - Route-map configuration
- `apis/routing/sag.py` - Static anycast gateway
- `apis/routing/vrf.py` - VRF configuration

#### Switching APIs (4 files)
- `apis/switching/vlan.py` - VLAN configuration
- `apis/switching/portchannel.py` - PortChannel/LAG configuration
- `apis/switching/portchannel_rest.py` - PortChannel REST API

#### System APIs (14 files)
- `apis/system/ntp.py` - NTP configuration and verification
- `apis/system/interface.py` - Interface management
- `apis/system/basic.py` - Basic system operations
- `apis/system/reboot.py` - Reboot operations
- `apis/system/port.py`, `port_rest.py` - Port management
- `apis/system/rest.py` - REST API utilities
- `apis/system/boot_up.py`, `connection.py`, `management_vrf.py`
- `apis/system/switch_configuration.py`, `system_server.py`, `ztp.py`

#### YANG/REST Utilities (1 file)
- `apis/yang/utils/query_param.py`

### Utility Modules (8 files)
Located in `utilities/` directory:
- `parallel.py` - Parallel execution utilities
- `common.py` - Common utility functions
- `utils.py` - General utilities
- `exceptions.py` - Custom exceptions
- `cache.py` - Caching mechanisms
- `ctrl_chars.py` - Control character handling
- `tracer.py` - Tracing and debugging

### Framework Files (37 files)
Located in `spytest/` directory:

#### Core Framework
- `framework.py` (6,100+ lines) - Test orchestration and execution lifecycle
- `net.py` (7,200+ lines) - Device connection and CLI execution
- `testbed.py` (3,000+ lines) - Topology management
- `splugin.py` - Custom PyTest plugin
- `infra.py` - Infrastructure functions
- `st_time.py`, `dicts.py`, `ordyaml.py`

#### Access Layer
- `access/connection.py` - Connection management
- `access/linux_connection.py` - Linux device connections
- `access/paramiko_connection.py` - SSH connections via Paramiko
- `access/utils.py` - Access utilities

#### Traffic Generation
- `tgen/__init__.py`, `tgen/tg.py` - Traffic generator abstraction
- `tgen/tg_scapy.py` - Scapy-based traffic generation
- `tgen/tg_stubs.py` - Traffic generator stubs
- `tgen/init.py`
- `tgen_api.py` - Traffic generator API

#### gNMI Support
- `gnmi/__init__.py`, `gnmi/translator.py`, `gnmi/wrapper.py`

#### Additional Modules
- `ansible.py` - Ansible integration
- `rest.py` - REST API support
- `datamap.py` - Data mapping utilities
- `dlog.py`, `logger.py` - Logging infrastructure
- `ftrace.py` - Function tracing
- `monitor.py` - System monitoring
- `result.py`, `suite.py` - Test result management
- `syslog.py` - Syslog handling
- `template.py` - TextFSM template processing
- `termserv.py` - Terminal server support
- `rps.py` - Remote power switch support
- `utils.py`, `version.py`

### Entry Point (1 file)
- `bin/spytest` - Main entry point script

## How to Use

### Prerequisites
```bash
# Install Python 3.8+
python3 --version

# Install dependencies
cd spytest
./bin/upgrade_requirements.sh
```

### Running Tests

#### BGP Tests
```bash
# Run BGP IPv4 basic eBGP test
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_ipv4_basic_ebgp.py \
  --logs-path ./logs/bgp_test_$(date +%F_%H%M%S) \
  --log-level debug --skip-init-config --ifname-type native

# Run BGP over SVI
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_2node.yaml \
  tests/routing/BGP/test_bgp_svi_ipv4_ebgp.py \
  --logs-path ./logs/bgp_svi_$(date +%F_%H%M%S) \
  --log-level debug
```

#### NTP Tests
```bash
# Run NTP IS-CLI tests
./bin/spytest --tryssh 1 \
  --testbed ./testbeds/testbed_vs_1node.yaml \
  tests/system/ntp/test_ntp_iscli.py \
  --logs-path ./logs/ntp_test_$(date +%F_%H%M%S) \
  --log-level debug
```

### Test Coverage

#### BGP Test Features
- iBGP and eBGP neighbor session establishment
- BGP over physical interfaces, SVI (VLAN), PortChannel, and Loopback
- Route advertisement and learning validation
- Traffic forwarding validation using Scapy
- Configuration persistence (save/reboot testing)
- Route redistribution (connected and static routes)
- BGP advanced features (route reflector, MED, weight)
- Multi-hop BGP with update-source configuration

#### NTP Test Features
- Global NTP enable/disable
- NTP server configuration (IPv4/IPv6)
- NTP authentication (MD5, SHA1, SHA256, SHA384, SHA512)
- NTP key management (authentication keys, trusted keys)
- Source interface configuration
- VRF support
- Server options (version, minpoll, maxpoll, iburst, prefer)
- CRUD operations on servers and keys

## File Organization

```
spytest/
├── bin/
│   └── spytest                    # Entry point
├── apis/
│   ├── common/                    # Common APIs (13 files)
│   ├── routing/                   # Routing APIs (6 files)
│   ├── switching/                 # Switching APIs (4 files)
│   ├── system/                    # System APIs (14 files)
│   └── yang/                      # YANG utilities (1 file)
├── utilities/                     # Utility modules (8 files)
├── spytest/                       # Core framework (37 files)
├── tests/
│   ├── routing/BGP/              # BGP tests and vars (26 files)
│   └── system/ntp/               # NTP tests and vars (4 files)
├── reporting/
│   └── syslogs.yaml
├── testbeds/
│   └── sonic_errors.yaml
├── identify_dependencies.py      # Dependency analysis script
└── required_files_list.txt       # Complete file list
```

## Dependency Analysis

The `identify_dependencies.py` script was used to identify all necessary files by:
1. Parsing test files to extract imports
2. Recursively analyzing API module dependencies
3. Identifying YAML variable files referenced in tests
4. Including essential framework files
5. Adding configuration files (syslogs.yaml, sonic_errors.yaml)

To re-run the analysis:
```bash
python3 identify_dependencies.py
```

## Notes

- All test files include comprehensive docstrings with usage instructions
- Tests are designed to work on both hardware and virtual SONiC environments
- Interface names are dynamically resolved from topology files
- Test parameters are externalized in YAML files for easy configuration
- Tests support both klish (sonic-cli) and click CLI types
- Automatic cleanup ensures tests can run repeatedly

## Contact

For questions or issues related to these automation files, please contact:
- Author: Athira
- Repository: https://github.com/palcnetworks/sonic-mgmt
- Branch: automation_files_by_athira
