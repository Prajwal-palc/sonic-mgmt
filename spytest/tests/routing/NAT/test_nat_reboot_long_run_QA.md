# NAT Long-Run Reboot Test Case QA Notes

## 1. Topology Type in Use
- The setup call `st.ensure_min_topology("D1T1:2")` requires one DUT (D1) connected to a single traffic generator (T1) with two links, revealing a point-to-point test topology with two traffic-generator ports.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L395-L408】
- Traffic generator handles later bind to `vars.T1D1P1` and `vars.T1D1P2`, confirming two traffic-generator interfaces toward the DUT.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L404-L416】

## 2. Overall Test Case Purpose
- The suite validates that SONiC's NAT implementation maintains translation functionality and statistics across disruptive events (cold reboot, config reload, timeout, and warm reboot) while handling both static and dynamic mappings with configured ACLs and pools.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L146-L393】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L417-L466】

## 3. Subtestcases and Their Roles
- `test_ft_nat_save_reboot`: Clears NAT state, saves configuration, cold reboots the DUT, and verifies static and dynamic NAT translations plus statistics recovery to ensure persistence across a full reboot.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L146-L207】
- `test_ft_nat_config_reload`: Performs a `config save`/`config reload`, then replays traffic to ensure translations and stats survive a configuration reload procedure, protecting against control-plane churn.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L209-L268】
- `test_ft_dynamic_nat_timeout`: Adjusts global NAT timeout, modifies pool bindings, generates traffic, and waits for timeout to confirm dynamic entries age out correctly and cleanup restores baseline configuration.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L270-L333】
- `test_ft_dynamic_nat_warmboot`: Scales dynamic NAT entries via continuous traffic, executes warm reboot only on platforms that support it, and verifies traffic continuity and translation recovery, ensuring high-availability behavior.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L336-L393】

## 4. Dependencies and Prerequisites
- Module-scoped autouse fixture `nat_module_config` initializes global data, pre-configures NAT, and later cleans up via `nat_pre_config`/`nat_post_config`, so every subtest assumes that baseline configuration and traffic generator setup exist.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L133-L482】
- `nat_pre_config` checks hardware SKU against constants, skipping unsupported platforms (e.g., TH3) and therefore requires a DUT supporting NAT and warm reboot where relevant.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L395-L405】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L336-L349】
- Traffic generator connectivity must provide two ports mapped in the testbed inventory so handles can be acquired and configured.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L404-L416】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L504-L571】

## 5. Key Inputs and Their Sources
- `nat_reboot_initialize_variables` seeds IP addresses, NAT pools, ACL parameters, timers, and control flags via `SpyTestDict` literals and `random_vlan_list`, making them in-memory test constants for reuse across cases.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L17-L130】
- Topology-specific handles such as `vars.D1`, `vars.D1T1P1`, and `vars.T1D1P1` originate from `st.ensure_min_topology`, reflecting port and device mappings from the active `testbed.yaml` inventory.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L395-L416】
- Platform capability data is pulled from SpyTest datastore constants (`st.get_datastore`), and warm reboot checks rely on `common_constants['WARM_REBOOT_SUPPORTED_PLATFORMS']` values typically populated through group variables.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L395-L405】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L345-L349】
- CLI save/reload behavior is triggered through `reboot_obj` utilities, implying DUT access credentials/config supplied via standard SpyTest fixtures and command-line parameters (Not specified beyond defaults). Not specified.

## 6. External Libraries and Roles
- `spytest` modules (`st`, `tgapi`, `SpyTestDict`) provide logging, topology introspection, traffic generator control, and structured storage used throughout setup and validation.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L3-L5】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L395-L571】
- API helpers (e.g., `apis.routing.nat`, `apis.routing.ip`, `apis.qos.acl`, `apis.system.reboot`, `apis.system.basic`, `apis.system.interface`, `apis.routing.arp`, `apis.switching.vlan`) deliver high-level operations for configuring NAT, IP addresses, ACLs, reboots, platform checks, interface stats, ARP, and VLAN cleanup—each invoked during setup, execution, or debugging.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L6-L610】
- `pytest` supplies the test framework with fixtures and marks like `@pytest.mark.nat_longrun`.【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L1-L147】
