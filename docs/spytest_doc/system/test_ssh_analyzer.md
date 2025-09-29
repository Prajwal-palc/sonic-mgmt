# SSH System Test Analyzer

## 1. Topology Type
- **Identified Topology:** `D1D2:2` dual-DUT setup with two interconnected links.
- **Inference Basis:** The module-level autouse fixture calls `st.ensure_min_topology("D1D2:2")`, which explicitly requests a topology containing two DUTs (D1 and D2) with two links between them. Subsequent helper functions reference peer-facing interfaces such as `vars.D1D2P1`, `vars.D2D1P1`, `vars.D1D2P2`, and `vars.D2D1P2`, confirming the dual-device point-to-point topology. 【F:spytest/tests/system/test_ssh.py†L23-L25】【F:spytest/tests/system/test_ssh.py†L52-L86】

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate SSH service behavior and control-plane ACL enforcement on SONiC devices, including user authentication, IPv4/IPv6 reachability, SNMP access, and service resilience across configuration reloads and reboots.
- **Framework Context:** Within the SONiC SpyTest framework, these tests ensure secure remote access policies are enforced, that SSH remains operational for valid clients, is blocked when disabled or denied by ACLs, and that control-plane ACLs properly govern SSH, SNMP, and ICMP traffic before and after device restarts or configuration reloads. 【F:spytest/tests/system/test_ssh.py†L90-L308】

## 3. Detailed Breakdown of Sub-Testcases
### 3.1 `test_ft_ssh_service_disable`
- **Intent & Logic:** Disables SSH on D1, attempts an SSH login using the detected default credentials, and expects the connection to fail. Afterwards re-enables SSH and reports pass/fail based on whether the service correctly blocked access while disabled.
- **Relevance:** Confirms that the SSH service disable feature is enforced, a foundational security requirement for maintenance windows or policy-driven access control. 【F:spytest/tests/system/test_ssh.py†L122-L139】

### 3.2 `test_ft_ssh_add_user_verify`
- **Intent & Logic:**
  - Adds SNMP configuration and a non-default SSH user.
  - Verifies SSH access for default and new users from D1 and remote sessions from D2 over IPv4/IPv6.
  - Applies control-plane ACLs to permit specific SNMP/SSH sources while denying others, checking enforcement via SNMP get operations and SSH attempts.
  - Saves configuration, performs a fast reboot, and validates ACL persistence and functionality post-reboot for SNMP and SSH (IPv4/IPv6) traffic.
  - Tests ACL behavior when source addresses are changed to disallow SNMP and ensures SSH connectivity aligns with ACL intent.
  - Cleans up ACLs and non-default user, reporting pass/fail for each service-specific validation.
- **Relevance:** Provides comprehensive coverage of SSH user management, control-plane ACL enforcement, and service persistence across reboots, ensuring secure management-plane operations. 【F:spytest/tests/system/test_ssh.py†L141-L308】

### 3.3 `test_ft_control_plane_acl_icmp`
- **Intent & Logic:**
  - Retrieves management IPv4/IPv6 addresses for both DUTs and applies ACL rules to drop ICMP traffic.
  - Validates that ICMP is blocked from D2 to D1 over IPv4 and from D1 to its own link-local IPv6 when ACLs are in deny mode.
  - Updates ACL rules to permit traffic from specific sources, re-applies them, and checks that ICMP connectivity is restored, verifying rule ordering/priority.
  - Saves configuration, reboots D1, and ensures ACL behavior (permitting ICMP) persists post-reboot.
- **Relevance:** Extends control-plane ACL validation beyond SSH/SNMP to ICMP, confirming ACL rule correctness, sequencing, and reboot persistence for management protocols. 【F:spytest/tests/system/test_ssh.py†L310-L377】

### 3.4 `test_ft_ssh_config_reload_docker`
- **Intent & Logic:**
  - Captures current docker process state and total count.
  - Initiates an SSH session to D1, issues `sudo config reload -y &`, and forcibly disconnects.
  - Polls for docker services to exit and recover, verifying full restoration to the original container count.
  - On failure, triggers device reboot and reports failure; otherwise reports success.
- **Relevance:** Ensures executing a configuration reload via SSH does not leave SONiC docker services in a failed state, validating manageability and resilience of the platform when remote admins trigger reloads. 【F:spytest/tests/system/test_ssh.py†L381-L414】

### Helper Functions and Fixtures
- **`initialize_variables`, `config_nondefault_user`, `config_ip_address`, `snmp_config`, `ssh_module_prolog`, `change_acl_rules`, `verify_ssh_connection`:** Prepare test data, manage user accounts, configure interface IPs, set up SNMP/ACL parameters, and encapsulate reusable verification logic. They ensure each subtest starts with consistent state and reduce code duplication.
- **Fixtures `ssh_module_hooks` and `ssh_func_hooks`:** Provide module-wide setup/teardown (topology provisioning, IP/ACL prep, SSHv6 enablement, SNMP cleanup) and per-test hooks (currently no per-test actions), guaranteeing a controlled environment for all tests. 【F:spytest/tests/system/test_ssh.py†L23-L120】

## 4. Dependencies and Prerequisites
- **Fixtures:** `ssh_module_hooks` (module scope, autouse) and `ssh_func_hooks` (function scope, autouse) orchestrate environment setup/cleanup. 【F:spytest/tests/system/test_ssh.py†L52-L120】
- **Topology Constraints:** Requires a `D1D2:2` topology with management access to both DUTs and bidirectional interfaces for IPv4/IPv6 configuration. 【F:spytest/tests/system/test_ssh.py†L52-L86】
- **Services:** SSH, SSHv6, SNMP servers, and control-plane ACL capabilities must be present/enabled on the DUT. Tests rely on the ability to reboot devices and execute configuration commands remotely.

## 5. Key Inputs and Parameters
- **User Credentials:** Default (`admin` with detected password) and dynamically generated non-default credentials for SSH authentication coverage. 【F:spytest/tests/system/test_ssh.py†L29-L41】【F:spytest/tests/system/test_ssh.py†L141-L216】
- **IP Addressing:** Hardcoded IPv4/IPv6 addresses for inter-DUT links and SNMP ACL sources drive connectivity and ACL filtering scenarios. 【F:spytest/tests/system/test_ssh.py†L31-L44】【F:spytest/tests/system/test_ssh.py†L185-L239】
- **SNMP Parameters:** Community string, location, contact, system name OID, and SNMP server credentials obtained via `ensure_service_params` govern SNMP access testing. 【F:spytest/tests/system/test_ssh.py†L37-L40】【F:spytest/tests/system/test_ssh.py†L95-L116】【F:spytest/tests/system/test_ssh.py†L185-L247】
- **ACL Definitions:** Imported JSON structures (`acl_json_config_control_plane`, `acl_json_config_control_plane_v2`) supply rule templates that are mutated via `change_acl_rules` to create targeted allow/deny conditions. 【F:spytest/tests/system/test_ssh.py†L10-L12】【F:spytest/tests/system/test_ssh.py†L180-L305】【F:spytest/tests/system/test_ssh.py†L318-L352】
- **Docker State:** Baseline container counts captured by `get_and_match_docker_count` provide the reference for verifying docker recovery after config reload. 【F:spytest/tests/system/test_ssh.py†L389-L406】

## 6. External Libraries and Modules
- **`pytest`:** Test framework providing fixtures, markers, and assertion/reporting infrastructure. 【F:spytest/tests/system/test_ssh.py†L1】
- **`random`:** Generates randomized usernames/passwords for unique non-default user creation. 【F:spytest/tests/system/test_ssh.py†L2】【F:spytest/tests/system/test_ssh.py†L29-L34】
- **SpyTest Modules (`spytest`, `SpyTestDict`, reporting helpers):** Offer topology management (`st.ensure_min_topology`), logging, SSH execution, reporting (`st.report_*`), polling (`poll_wait`), and dictionary utilities for structured data storage. 【F:spytest/tests/system/test_ssh.py†L3-L4】【F:spytest/tests/system/test_ssh.py†L15】
- **APIs (`apis.system.*`, `apis.routing.ip`, `apis.qos.acl`, `apis.security.user`):** Provide SONiC-specific configuration and verification helpers for SSH service control, reboot/config save, user management, IP assignment, ACL operations, SNMP configuration, docker status, and remote command execution. 【F:spytest/tests/system/test_ssh.py†L5-L17】
- **Utility Modules (`utilities.*`):** Supply parallel execution (`parallel.exec_parallel`, `parallel.exec_all`), random credential generators, service parameter retrieval, and generic helper logic leveraged across tests. 【F:spytest/tests/system/test_ssh.py†L9-L14】【F:spytest/tests/system/test_ssh.py†L320-L325】
- **Test Data Module (`tests.qos.acl.acl_json_config`):** Contains predefined ACL JSON structures reused for control-plane ACL validations. 【F:spytest/tests/system/test_ssh.py†L10】【F:spytest/tests/system/test_ssh.py†L178-L305】

## 7. Unspecified Items
- **Additional Environmental Requirements:** Not specified beyond topology and services noted above.
- **Exact CLI Types or Platforms:** Not specified in the test file. Some comments reference pending fixes (e.g., SONIC-32291) but no explicit platform constraints are included. 【F:spytest/tests/system/test_ssh.py†L326-L329】

