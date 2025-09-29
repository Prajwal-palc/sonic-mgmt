# Snapshot Feature Functional Test – Analyzer

## 1. Topology Type
- **Topology**: `D1T1:4` (one DUT connected to a single test generator with four links).
- **Inference**: The module-level fixture invokes `st.ensure_min_topology('D1T1:4')`, explicitly requiring a topology with DUT `D1` and test generator `T1` with four connected ports. Helper data such as `vars.D1T1P1`…`vars.D1T1P4` and traffic generator handles for four ports further confirm this setup.

## 2. Overall Test Case Purpose
- **High-level goal**: Validate the SONiC snapshot feature across telemetry intervals, snapshot intervals, buffer watermarks, queue counters, buffer pool statistics, and CPU queue counters.
- **Context**: Within the SpyTest framework, the snapshot feature captures instantaneous and persistent watermarks for priority groups, queues, and buffer pools. These tests ensure configuration APIs, telemetry reporting, counter updates under different traffic profiles (unicast, multicast, CPU-directed), persistence through reload, and counter clearing behavior operate correctly.

## 3. Detailed Breakdown of Sub-Testcases
### 3.1 `test_ft_watermark_telemetry_interval`
- Configures a non-default telemetry interval for watermarks via `sfapi.config_snapshot_interval`, verifies the change using `sfapi.verify`, restores the default interval, and confirms the reset.
- Ensures telemetry scheduling can be tuned and reliably returns to default, which is foundational for time-based snapshot reporting.

### 3.2 `test_ft_snapshot_interval`
- Programs the snapshot interval, validates the setting, clears it to revert to the default, and verifies both operations.
- Confirms that snapshot scheduling is configurable and resettable, which underpins all subsequent counter collection tests.

### 3.3 `test_ft_sf_all_buffer_stats_using_unicast_traffic`
- Sets QoS dot1p-to-TC and TC-to-PG maps, binds them to an interface, starts continuous unicast traffic, then verifies:
  - Priority group (PG) user and persistent watermarks through CLI and counter DB views.
  - Queue watermarks (including percentage output) for unicast queues.
  - Proper clearing of PG and queue counters for both user and persistent tables.
- Uses `sf_tg_traffic_start_stop` to drive traffic and `sfapi.verify`/`sfapi.config_snapshot_interval` to query/reset counters.
- Demonstrates that snapshot counters respond to traffic, map configurations, and clear commands—critical for validating unicast buffering telemetry.

### 3.4 `test_ft_sf_all_buffer_stats_using_multicast_traffic`
- Determines the multicast queue index start, generates multicast traffic, and verifies multicast queue user and persistent watermarks.
- Clears multicast queue counters for both user and persistent views and validates the reset.
- Ensures snapshot reporting covers multicast buffering behavior and respects queue indexing differences.

### 3.5 `test_ft_sf_periodic_verify_using_counter_DB`
- Configures the snapshot interval, waits for intervals, and captures two counter DB timestamp samples for a queue to compute the interval difference.
- Fails if the timestamp delta is smaller than the configured snapshot interval, validating that periodic updates follow the schedule.
- Contains additional multi-line string documentation with planned checks for counter and percentage growth/clear steps, indicating future or reference logic.

### 3.6 `test_ft_sf_verify_buffer_pool_counters`
- Gathers platform/hwsku data, renders the buffer configuration template, reloads the DUT to apply it, and waits for stabilization.
- Sends unicast traffic, then checks buffer pool user and persistent watermarks (both via CLI and percentages), counter DB values, and clearing behavior with tolerance checks.
- Validates buffer pool-level visibility and reset functionality, including post-reload persistence of snapshot configuration.

### 3.7 `test_ft_sf_verify_cpu_counters`
- Enables sFlow sampling toward the CPU, drives traffic expected to hit CPU queues, and verifies CPU queue watermarks via CLI and counter DB.
- Ensures the snapshot feature tracks CPU-facing queues, a special case distinct from data plane queues.

### Helper Functions and Fixtures
- **`snapshot_feature_module_hooks`**: Module-scoped autouse fixture initializing topology, global data, module prolog, and epilog clean-up (VLAN creation/deletion).
- **`snapshot_feature_func_hooks`**: Function-scoped autouse fixture clearing interface counters before tests and restoring traffic/interval configuration after specific tests.
- **`global_vars_and_constants_init`**: Populates shared `sf_data` dictionary with ports, intervals, QoS maps, traffic modes, tolerances, and other constants.
- **`sf_module_prolog` / `sf_module_epilog`**: Prepare/tear down VLAN membership and traffic generator streams.
- **Traffic helpers (`sf_tg_stream_config`, `sf_tg_traffic_start_stop`)**: Create and manage traffic generator streams across unicast, multicast, CPU-directed, and periodic profiles.
- **`sf_collecting_debug_logs_when_test_fails`**: Collects interface counters on failure for debugging.
- **`clear_qos_map_config`**: Removes QoS map bindings after unicast tests.

## 4. Dependencies and Prerequisites
- **Fixtures**: `snapshot_feature_module_hooks`, `snapshot_feature_func_hooks` (auto-used to set up topology, VLANs, TG streams, and cleanup).
- **Topology constraint**: Requires D1T1:4 connectivity (one DUT with four traffic generator ports).
- **Traffic generator support**: Uses `tgapi.get_handles` and stream configurations; assumes availability of a capable TG.
- **QoS map configuration capability**: Depends on COS APIs for QoS map creation/binding/clearing.
- **SFlow and buffer configuration access**: Requires sFlow support and ability to load buffer JSON templates, plus reboot capability for applying buffer pools.

## 5. Key Inputs and Parameters
- **Snapshot/Telemetry intervals**: `sf_data.snapshot_interval`, `sf_data.default_snapshot_interval`, `sf_data.telemetry_interval`, `sf_data.default_telemetry_interval` – control scheduling of snapshot collection and telemetry pushes.
- **Traffic profiles**: `sf_data.unicast`, `sf_data.multicast`, `sf_data.cpu`, `sf_data.periodic` – drive different traffic generator modes.
- **QoS mappings**: `sf_data.dot1p_to_tc_map_dict`, `sf_data.tc_to_pg_map_dict`, and associated binding dictionaries – determine queue/PG mapping for traffic classification tests.
- **Buffer configuration artifacts**: `sf_data.config_file`, `sf_data.device_j2_file` – paths for generating and loading buffer pool templates before reload.
- **Tolerance and timings**: `sf_data.buffer_pool_tolerance`, `sf_data.traffic_duration`, `sf_data.reload_interval`, `sf_data.FMT` – govern validation thresholds and wait times.
- **Port identifiers**: `sf_data.port_list`, `sf_data.tg_port_list`, `vars.D1T1P1`…`vars.D1T1P4` – identify DUT and TG interfaces used across checks.

## 6. External Libraries and Modules
- **`pytest`**: Provides fixtures, markers, and test execution framework.
- **`datetime`**: Used to compute timestamp differences for periodic update validation.
- **`spytest` core (`st`, `tgapi`, `SpyTestDict`)**: SpyTest utilities for logging, topology access, traffic generator control, and dictionary helpers.
- **`spytest.utils.random_vlan_list`**: Supplies random VLAN IDs for test setup.
- **`apis.system.snapshot` (`sfapi`)**: Snapshot feature API wrapper for configuration, verification, and data retrieval.
- **`apis.switching.vlan`**: VLAN creation, membership, and clearing utilities used in prolog/epilog.
- **`apis.system.basic`**: Retrieves hardware SKU, interface MAC, and platform summaries for buffer configuration.
- **`apis.system.port`**: Interface counter retrieval/clearing for setup and debug.
- **`apis.system.reboot`**: Provides `config_save_reload` for applying buffer configurations.
- **`apis.qos.cos`**: Configures and clears QoS maps and port bindings.
- **`apis.system.sflow`**: Manages sFlow enablement and sampling attributes needed for CPU counter validation.

## 7. Unspecified Items
- **Testbed file references**: Not specified.
- **Group vars / CLI parameter sources**: Not specified.
- **Exact traffic generator model or speed**: Not specified.
- **Detailed pass/fail criteria beyond described checks**: Not specified.
