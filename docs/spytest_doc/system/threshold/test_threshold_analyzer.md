# Threshold Feature Functional Test Analyzer

## 1. Topology Type
- **Topology:** `D1T1:4` (one DUT connected to one traffic generator with four links).
- **Inference:** Derived from the `st.ensure_min_topology('D1T1:4')` call inside `global_vars_and_constants_init()`, which provisions topology metadata (`vars.D1`, `vars.T1D1P1`-`P4`, etc.) used across the tests.

## 2. Overall Test Case Purpose
- **High-level Goal:** Validate SONiC threshold feature functionality for buffer resources, ensuring correct configuration, breach detection, and clearing behavior across priority-group shared buffers and queue (unicast and multicast) buffers.
- **Framework Context:** The tests leverage SpyTest utilities to configure VLANs, traffic generator streams, and threshold APIs on a single DUT. They exercise configuration, verification, traffic stimulation, breach observation, and cleanup sequences that align with SONiC threshold feature requirements.

## 3. Detailed Breakdown of Sub-Testcases
### `test_ft_tf_pg_thre_con_shared`
- **Intent & Logic:**
  - Configures a VLAN and TG traffic in the module fixture; this test focuses on priority-group shared buffer thresholds.
  - Picks priority-group index (`tf_data.index`) based on platform family and sets a threshold value (`tf_data.threshold = 4`).
  - Iteratively configures the PG shared threshold via `tfapi.config_threshold` and confirms persistence with `tfapi.verify_threshold`.
  - Generates unicast traffic to trigger buffer usage, then validates breach events with `tfapi.verify_threshold_breaches`.
  - Clears breach counters and validates they are removed, then clears the configuration and confirms removal.
  - Retries up to `tf_data.test_max_retries_count` times, invoking debug collection helper if breaches are missing.
- **Relevance:** Demonstrates that PG shared thresholds can be configured, detect breaches under load, and be cleaned up—core coverage for shared buffer monitoring.

### `test_ft_tf_queue_thre_con_unicast`
- **Intent & Logic:**
  - Tests unicast queue threshold configuration on egress port `vars.D1T1P4` with index `0` and threshold `20` cells.
  - Verifies the applied configuration, drives unicast traffic, and checks for queue breach events.
  - Clears breaches and configuration, ensuring both removal actions take effect.
  - Employs the same retry/debug pattern as the PG test.
- **Relevance:** Validates unicast queue threshold handling, ensuring breach alarms fire and reset properly, which is critical for congestion monitoring.

### `test_ft_tf_queue_thre_con_multicast`
- **Intent & Logic:**
  - Configures multicast queue threshold (index `0`, threshold `2`) on the same port.
  - Switches TG streams to multicast mode (longer duration) to induce multicast buffer usage.
  - Confirms threshold breach logging, then clears breaches and configuration to verify cleanup.
  - Utilizes retries and debug capture when breaches do not appear.
- **Relevance:** Completes coverage by validating multicast queue thresholds, ensuring multicast congestion is detected and recoverable.

### Helper Fixtures and Functions
- **`threshold_feature_module_hooks` (module autouse):** Initializes globals, applies module-level configuration (VLAN, TG stream setup, debug state), and performs teardown cleanup.
- **`threshold_feature_func_hooks` (function autouse):** Verifies system map readiness before each test by polling `tfapi.verify_hardware_map_status`.
- **Utility Helpers:** Functions such as `tf_tg_stream_config`, `tf_tg_traffic_start_stop`, `tf_unconfig`, `tf_collecting_debug_logs_when_test_fails`, and `report_result` encapsulate TG setup, traffic control, cleanup, debug logging, and reporting to support each subtest.

## 4. Dependencies and Prerequisites
- **Fixtures:** Module and function autouse fixtures ensure topology preparation, VLAN membership, TG stream provisioning, and system map readiness.
- **APIs & Helpers:** Depend on `tfapi`, `vapi`, `bcapi`, `bsapi`, and `scapi` for threshold configuration, VLAN operations, hardware SKU detection, system checks, and running config retrieval.
- **Topology Constraints:** Requires the `D1T1:4` topology with four front-panel ports tied to traffic generator ports; relies on hardware constants fetched from datastore for platform-specific logic.

## 5. Key Inputs and Parameters
- **Threshold Indices & Values:** `tf_data.index`, `tf_data.threshold` vary per test to target specific buffers.
- **Ports:** `tf_data.port_list`, `vars.D1T1P1`, `vars.D1T1P4` designate ingress/egress interfaces for threshold operations and traffic.
- **Traffic Modes:** `tf_data.unicast`, `tf_data.multicast`, and TG stream handles drive traffic patterns for breach generation.
- **Retry & Timing Controls:** `tf_data.test_max_retries_count`, `tf_data.traffic_duration`, and `tf_data.max_time_to_check_sys_maps` control polling, retries, and traffic run-times.
- **Platform Data:** `tf_data.platform`, `tf_data.pg_headroom_un_supported_platforms`, and `tf_data.th3_platforms` influence index selection and debug behavior.

## 6. External Libraries and Modules
- **`pytest`:** Provides fixture and test orchestration.
- **SpyTest Core (`st`, `tgapi`, `SpyTestDict`):** Supplies topology management, TG handle access, logging, waiting, and data structuring utilities.
- **`random_vlan_list`:** Generates VLAN IDs for module configuration.
- **SONiC API Modules:**
  - `apis.system.threshold` (`tfapi`): threshold configuration, verification, breach handling, debug utilities.
  - `apis.switching.vlan` (`vapi`): VLAN creation/deletion and membership control.
  - `apis.system.basic` (`bcapi`): hardware SKU retrieval.
  - `apis.system.box_services` (`bsapi`): system uptime queries.
  - `apis.system.switch_configuration` (`scapi`): running configuration retrieval.
- **`utilities.utils` (`cutils`):** Logging helper (`banner_log`) for test progress and debug output.

## 7. Unspecified Items
- **Testbed Inventory & Group Vars:** Not specified in the test file.
- **Explicit DUT hardware requirements beyond platform families:** Not specified.
