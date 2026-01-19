# test_ssh.py QA Review

## 1. Topology type and inference
- The test module enforces a minimum topology of "D1D2:2" using `st.ensure_min_topology`, meaning two DUTs (D1, D2) with two interconnects available. The subsequent configuration applies IPv4 and IPv6 addresses on paired interfaces `D1D2P1/P2` and `D2D1P1/P2`, confirming a dual-link connection between the two devices.【F:spytest/tests/system/test_ssh.py†L53-L111】

## 2. Overall test purpose
- The suite validates end-to-end SSH service behavior on SONiC, including service enable/disable handling, user authentication, IPv4/IPv6 access control lists tied to SSH/SNMP, persistence across reboots, control-plane ACL behavior for ICMP, and the impact of invoking `config reload` over SSH on container health.【F:spytest/tests/system/test_ssh.py†L130-L452】

## 3. Subtestcases and rationale
- **`test_ft_ssh_service_disable`** – Disables SSH, attempts login, and ensures access is blocked before restoring the service. This confirms that the SSH daemon honors enable/disable state changes.【F:spytest/tests/system/test_ssh.py†L157-L173】
- **`test_ft_ssh_add_user_verify`** – Creates a non-default user, verifies SSH reachability with default and new credentials, applies control-plane ACLs for SSH/SNMP, checks SNMP reachability, validates permitted/denied IPv4 and IPv6 SSH paths, and repeats checks after reboot and ACL adjustments. This comprehensive flow confirms SSH authentication, ACL enforcement, SNMP coexistence, and configuration persistence.【F:spytest/tests/system/test_ssh.py†L175-L361】
- **`test_ft_control_plane_acl_icmp`** – Deploys control-plane ACLs targeting ICMP, verifies traffic drops, modifies rules to permit specific sources, and validates behavior before and after reboot. This ensures ACL sequencing, specificity, and persistence for ICMP alongside the SSH-focused policies.【F:spytest/tests/system/test_ssh.py†L363-L416】
- **`test_ft_ssh_config_reload_docker`** – Runs `config reload` via SSH, forcibly terminates the session, and monitors docker containers for recovery to steady state. This checks that administrative SSH sessions can safely trigger reload operations without leaving services in a failed state.【F:spytest/tests/system/test_ssh.py†L419-L452】

## 4. Dependencies and prerequisites
- Module-scope autouse fixture sets up two-DUT topology, initializes shared data, enables SSH/SSHv6, configures inter-DUT IPv4/IPv6 connectivity, and cleans up ACLs/SNMP state afterward.【F:spytest/tests/system/test_ssh.py†L50-L126】
- Requires SNMP trap service parameters (IP, username, password) to exist in service configuration for `ensure_service_params` calls, enabling remote SNMP validation via an auxiliary host.【F:spytest/tests/system/test_ssh.py†L114-L123】【F:spytest/tests/system/test_ssh.py†L213-L215】
- Depends on ACL definitions sourced from `tests.qos.acl.acl_json_config` for control-plane rules applied throughout the tests.【F:spytest/tests/system/test_ssh.py†L9-L303】
- Uses management connectivity (via `st.get_mgmt_ip`) for both DUTs and expects link-local IPv6 access on `eth0`, as well as the ability to reboot devices and restore state.【F:spytest/tests/system/test_ssh.py†L189-L291】【F:spytest/tests/system/test_ssh.py†L363-L416】
- Relies on SpyTest-provided fixtures/utilities such as `st.exec_ssh`, `st.change_passwd`, `parallel.exec_parallel`, and `poll_wait`, implying the SpyTest automation framework must be available.【F:spytest/tests/system/test_ssh.py†L71-L355】

## 5. Key inputs and their sources
- Default credentials, randomized non-default username/password, and static IPv4/IPv6 addressing used across tests are populated in `initialize_variables`, supplying consistent data during the module setup.【F:spytest/tests/system/test_ssh.py†L23-L47】
- Interface identifiers (e.g., `D1D2P1`) and device handles (`vars.D1`, `vars.D2`) are delivered by `st.ensure_min_topology` based on the active testbed definition.【F:spytest/tests/system/test_ssh.py†L53-L111】
- Management IPs for DUTs and SNMP server details are queried at runtime from the environment/testbed via `st.get_mgmt_ip` and `ensure_service_params`, respectively.【F:spytest/tests/system/test_ssh.py†L189-L215】【F:spytest/tests/system/test_ssh.py†L213-L215】
- ACL rule templates come from the imported JSON configuration module, while updates to specific fields are applied within the test to tailor source networks or hosts.【F:spytest/tests/system/test_ssh.py†L214-L303】
- Docker baseline counts and service status used in the reload test are captured dynamically from the DUT prior to invoking `config reload`.【F:spytest/tests/system/test_ssh.py†L426-L445】

## 6. External libraries and roles
- `pytest` provides fixture and marker support for organizing the test cases.【F:spytest/tests/system/test_ssh.py†L1】
- `spytest` utilities (`st`, `SpyTestDict`, `poll_wait`) furnish logging, SSH execution, topology abstraction, shared storage, and wait/retry helpers critical to SpyTest automation.【F:spytest/tests/system/test_ssh.py†L3-L21】【F:spytest/tests/system/test_ssh.py†L130-L355】
- `apis.system` modules handle SSH/SSHv6 toggling, SNMP configuration, reboot persistence, docker monitoring, device connections, and hostname retrieval used throughout the validations.【F:spytest/tests/system/test_ssh.py†L5-L18】【F:spytest/tests/system/test_ssh.py†L165-L452】
- `utilities` packages supply random credential generators, parallel execution helpers, service parameter lookup, and other support utilities leveraged in setup and verification steps.【F:spytest/tests/system/test_ssh.py†L8-L15】【F:spytest/tests/system/test_ssh.py†L86-L355】
- `tests.qos.acl.acl_json_config` feeds predefined control-plane ACL templates applied and modified within the test scenarios.【F:spytest/tests/system/test_ssh.py†L9-L303】
- Standard Python `random` is used for generating user credentials dynamically, ensuring uniqueness across runs.【F:spytest/tests/system/test_ssh.py†L2-L29】
