# TACACS Test Overview

## 1. Topology Type
- **Topology**: Single DUT topology (`D1`).
- **Inference**: The module-scoped fixture calls `st.ensure_min_topology("D1")`, indicating the tests require only one device under test labeled `D1`. 【F:spytest/tests/security/test_tacacs.py†L20-L21】

## 2. Overall Test Case Purpose
- Validates TACACS+ authentication, failthrough behavior, and server priority handling on the SONiC device, including PAM file creation and SSH access outcomes for local and TACACS credentials. 【F:spytest/tests/security/test_tacacs.py†L85-L163】

## 3. Subtestcases
- **`test_ft_tacacs_ssh_login_with_tacacs_operations`**: Confirms TACACS+ setup creates required PAM files and supports default login scenarios after adding a TACACS server. Ensures foundational TACACS functionality before advanced behaviors are tested. 【F:spytest/tests/security/test_tacacs.py†L85-L114】
- **`test_ft_tacacs_enable_disable_failthrough`**: Exercises login outcomes with TACACS/local authentication order changes and toggling failthrough, verifying correct access control when servers and credentials vary. Establishes confidence in failover behavior across authentication sequences. 【F:spytest/tests/security/test_tacacs.py†L116-L163】
- **`test_ft_tacacs_ssh_login_highest_priorityserver`**: Checks that SSH logins honor TACACS server priorities and failover to the next server upon removal, ensuring multi-server TACACS configurations operate as intended. 【F:spytest/tests/security/test_tacacs.py†L165-L181】

## 4. Dependencies / Prerequisites
- **Fixtures**: `tacacs_module_hooks` (module autouse) provisions topology, loads TACACS service parameters, configures servers, and cleans up. `tacacs_func_hooks` (function autouse) provides per-test hooks. 【F:spytest/tests/security/test_tacacs.py†L17-L83】
- **Utilities**: Relies on helper functions `ensure_device_ipaddress`, `config_default_tacacs_properties`, `verify_tacacs_server_reachability`, and `debug_info` defined within the module. 【F:spytest/tests/security/test_tacacs.py†L52-L82】
- **Topology Constraints**: Requires reachable TACACS servers defined in the testbed, multiple server entries for priority testing, and local admin credentials. 【F:spytest/tests/security/test_tacacs.py†L23-L49】【F:spytest/tests/security/test_tacacs.py†L126-L161】

## 5. Key Inputs
- TACACS host details (IP, port, passkey, priority, timeout, auth type) retrieved via `ensure_service_params` from the testbed service definitions. 【F:spytest/tests/security/test_tacacs.py†L23-L35】
- Local admin credentials (`admin`/`YourPaSsWoRd`, alternate password, etc.) and TACACS test users defined inside the fixture or fetched from service params (e.g., read-only user from `radius` service). 【F:spytest/tests/security/test_tacacs.py†L36-L47】
- Device management IP discovered at runtime through `basic_obj.get_ifconfig_inet`. 【F:spytest/tests/security/test_tacacs.py†L55-L59】

## 6. External Libraries / Modules
- **`spytest`** core (`st`, `SpyTestDict`) for topology management, logging, and data storage. 【F:spytest/tests/security/test_tacacs.py†L2-L4】
- **`apis.security.tacacs`** for TACACS server configuration and AAA property management. 【F:spytest/tests/security/test_tacacs.py†L5】【F:spytest/tests/security/test_tacacs.py†L61-L64】【F:spytest/tests/security/test_tacacs.py†L122-L151】
- **`apis.system.connection`** for SSH connectivity checks. 【F:spytest/tests/security/test_tacacs.py†L6】【F:spytest/tests/security/test_tacacs.py†L128-L160】
- **`apis.routing.ip`** for ping reachability. 【F:spytest/tests/security/test_tacacs.py†L7】【F:spytest/tests/security/test_tacacs.py†L69-L72】
- **`apis.system.basic`** for file verification and interface IP retrieval. 【F:spytest/tests/security/test_tacacs.py†L8】【F:spytest/tests/security/test_tacacs.py†L55-L58】【F:spytest/tests/security/test_tacacs.py†L100-L103】
- **`apis.security.rbac` (`ssh_call`)** and `apis.switching.vlan` for additional TACACS operations and cleanup, though `ssh_call` is imported but not used. 【F:spytest/tests/security/test_tacacs.py†L9-L10】【F:spytest/tests/security/test_tacacs.py†L43-L44】
- **`utilities.utils.ensure_service_params`** and **`utilities.common.poll_wait`** for service parameter retrieval and potential polling (unused). 【F:spytest/tests/security/test_tacacs.py†L11-L12】【F:spytest/tests/security/test_tacacs.py†L23-L35】

