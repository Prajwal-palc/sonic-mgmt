# NAT Reboot Long-Run Test Analyzer

## 1. Topology Type
- **Topology:** `D1T1:2` (single DUT with one traffic generator using two connected ports).
- **Inference:** The `nat_pre_config` fixture invokes `st.ensure_min_topology("D1T1:2")`, which guarantees at least one DUT (`D1`) linked to a traffic generator (`T1`) with two ports (`P1`, `P2`). This is further confirmed by the repeated use of `vars.T1D1P1` and `vars.T1D1P2` when configuring interfaces and traffic streams. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L197-L215】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L231-L238】

## 2. Overall Test Case Purpose
- **Goal:** Validate the resiliency and persistence of dynamic and static NAT/NAPT translations on a SONiC DUT across disruptive events (cold reboot, config reload, warm reboot) and timeout scenarios under long-running traffic.
- **Context:** Within the SONiC SpyTest regression, NAT functionality must maintain translations, statistics, and policy bindings despite reboots or configuration reloads. These tests stress dynamic NAT scaling, confirm that static entries persist, and ensure automatic cleanup after configured timeouts, aligning with service continuity and data-plane correctness expectations for NAT on SONiC. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L102-L189】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L190-L318】

## 3. Detailed Breakdown of Sub-Testcases

### `test_ft_nat_save_reboot`
- **Intent & Logic:**
  - Clears NAT tables, saves configuration in both SONiC and FRR (`vtysh`) contexts, and reboots the DUT.
  - Replays SNAT traffic to recreate dynamic translations, verifies reachability via ping, and confirms static NAT entries remain post reboot.
  - Validates dynamic SNAT/DNAT translation presence and statistics for UDP flows, ensuring packet counts meet an 80% threshold of transmitted traffic.
- **Importance:** Confirms that NAT functionality preserves required entries across a full reboot, demonstrating configuration persistence and data-plane recovery. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L102-L188】

### `test_ft_nat_config_reload`
- **Intent & Logic:**
  - Clears NAT data, performs `config save` and `config reload` workflow without reboot.
  - Runs SNAT traffic, checks that static entries survive reload, and ensures dynamic translations/statistics update correctly for both SNAT and DNAT paths with packet count validation.
- **Importance:** Ensures NAT state integrity through management-plane operations that reload configurations, a common maintenance procedure. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L190-L265】

### `test_ft_dynamic_nat_timeout`
- **Intent & Logic:**
  - Adjusts global NAT timeout to 300s, rebinds NAT pools, and drives dynamic NAT traffic from both directions.
  - Verifies dynamic translations and statistics appear, waits beyond timeout, and confirms entries are aged out.
  - Restores original pool bindings and timeout, reporting failure if entries persist or statistics are missing.
- **Importance:** Validates NAT session lifecycle management and timeout enforcement, critical for resource recycling and preventing stale entries. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L267-L332】

### `test_ft_dynamic_nat_warmboot`
- **Intent & Logic:**
  - Checks platform warm-reboot support before proceeding.
  - Reconfigures NAT bindings to use a scaling pool/ACL, sends continuous traffic to reach the maximum configured dynamic NAT entries, and confirms the count via polling.
  - Initiates warm reboot while traffic flows, evaluates post-reboot traffic integrity, and restores configuration.
- **Importance:** Demonstrates NAT scalability and stability during warm reboot (fast reboot) operations, ensuring hitless maintenance for dynamic NAT deployments. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L334-L404】

### Helper Utilities
- **`nat_pre_config` / `nat_post_config` (module fixture hooks):** Provision and teardown NAT environment—interface IPs, static routes, NAT feature enablement, pools, bindings, ACLs, traffic generator setup, and cleanup. They ensure consistent baseline and avoid configuration leakage between modules. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L197-L273】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L275-L309】
- **Traffic generator helpers (`util_tg_init`, `util_tg_routing_int_config`, `util_tg_stream_config`, `tg2_str_selector`):** Initialize TG handles, configure L3 interfaces, create traffic streams for SNAT/DNAT and scaling scenarios, and select matching response streams based on translation outcomes. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L311-L389】
- **`util_nat_zone_config` / `util_check_nat_translations_count` / `nat_reboot_debug_fun`:** Support functions for zone assignment, translation count polling, and debugging data collection on failure. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L311-L389】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L391-L436】

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `nat_module_config` (module-scoped, autouse) handles environment setup and teardown via `nat_pre_config`/`nat_post_config`.
  - `cmds_func_hooks` (function-scoped placeholder) allows per-test command hooks if needed. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L88-L101】
- **Topology:** Requires `D1T1:2` topology with traffic generator connectivity on two DUT ports. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L197-L205】
- **Platform Constraints:** NAT unsupported on TH3 platforms; warm reboot test requires platform listed under `WARM_REBOOT_SUPPORTED_PLATFORMS`. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L199-L340】
- **Traffic Generator:** Must support APIs used via `tgapi` for configuring streams, controlling traffic, and validating statistics. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L313-L389】

## 5. Key Inputs and Parameters
- **Static/Dynamic IP Data:** Predefined IP addresses, masks, pools, port ranges within `nat_reboot_initialize_variables()` drive interface assignments, NAT pools, and traffic payloads. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L16-L86】
- **Timeouts and Counters:** Variables such as `wait_nat_stats`, `wait_time_after_reboot`, and `max_nat_entries` control pacing for polling NAT tables/statistics and verifying scale. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L59-L86】
- **Traffic Profiles:** Packet counts, rates, MAC addresses, and port numbers shape TG stream configurations for SNAT/DNAT and scaling scenarios. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L52-L85】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L331-L389】
- **Configuration Flags:** `data.config_add`/`data.config_del`, NAT type identifiers, and protocol strings guide CRUD operations for NAT objects and ACLs. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L41-L86】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L218-L265】

## 6. External Libraries and Modules
- **PyTest (`pytest`):** Provides fixtures, marks (`@pytest.mark.nat_longrun`), and test orchestration. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L1-L104】
- **SpyTest Core (`spytest`, `tgapi`, `SpyTestDict`):** Core testing utilities, logging, reboot helpers, topology management, and traffic generator interface wrappers. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L3-L15】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L197-L389】
- **SONiC API Modules:**
  - `apis.routing.ip`, `apis.routing.nat`, `apis.routing.arp`: Manage IP routes, NAT configuration/queries, and ARP tables.
  - `apis.switching.vlan`: Cleanup VLAN configuration during teardown.
  - `apis.system.interface`, `apis.system.basic`, `apis.system.reboot`: Interface counters, platform information, and reboot/config-save operations.
  - `apis.qos.acl`: Create/modify ACL tables and rules for NAT zoning. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L6-L15】【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L197-L309】
- **Utilities:** `spytest.utils.random_vlan_list` generates VLAN IDs for potential interface setup, ensuring non-overlapping VLAN resources. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L4-L52】

## 7. Unspecified Items
- **Testbed Inventory Details:** Specific device models, TG brand/models, and exact interface mappings beyond `vars.*` references are **Not specified** in this file.
- **External Data Sources:** References to `common_constants`, `st.get_datastore`, or testbed variables assume existing inventory/group_vars definitions—actual content is **Not specified** within the test file. 【F:spytest/tests/routing/NAT/test_nat_reboot_long_run.py†L334-L344】

