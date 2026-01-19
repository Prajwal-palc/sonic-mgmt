# sFlow Test Plan Analyzer

## 1. Topology Type
- **Topology markers:** `pytestmark = [pytest.mark.topology('t0', 'm0', 'mx')]` shows the suite supports T0, M0, and MX lab layouts.【F:tests/sflow/test_sflow.py†L24-L28】
- **Inference details:**
  - The autouse `setup` fixture pulls minigraph facts and VLAN1000 members, which are standard on T0-style SONiC topologies, to derive test ports and upstream neighbors.【F:tests/sflow/test_sflow.py†L33-L90】
  - When no port-channels exist (typical of certain M0/MX variants), the test consults `tbinfo['topo']['type']` and helper utilities to discover upstream neighbors dynamically, confirming support for those topologies as well.【F:tests/sflow/test_sflow.py†L62-L77】

## 2. Overall Test Case Purpose
- **Primary goal:** Validate SONiC's sFlow feature end-to-end, covering configuration, operational status, sampling behavior, collector interactions, and persistence across reboots.【F:tests/sflow/test_sflow.py†L33-L683】
- **Context in SONiC automation:**
  - Exercises CLI-based sFlow management (`config sflow`, interface enablement, collector operations) and verifies telemetry data plane via PTF traffic generator (`ptf_runner`).【F:tests/sflow/test_sflow.py†L191-L290】【F:tests/sflow/test_sflow.py†L360-L545】
  - Ensures sFlow state survives warm, fast, and cold reboots, aligning with SONiC's high-availability requirements.【F:tests/sflow/test_sflow.py†L591-L683】

## 3. Detailed Breakdown of Sub-Testcases
### Helper Fixtures and Functions
- `setup` (module autouse): Prepares DUT and PTF hosts, validates sFlow feature presence, configures interface IPs, builds port metadata, and deploys collectors; tears down with config reload. Foundation for all tests.【F:tests/sflow/test_sflow.py†L33-L95】
- `config_sflow_feature`: Optionally enables the sFlow feature if the command-line flag is provided, ensuring coverage when devices ship with the feature disabled.【F:tests/sflow/test_sflow.py†L197-L204】
- `sflowbase_config`: Baseline configuration enabling sFlow globally, adding two collectors, setting polling, and enabling interfaces with default sampling. Used by multiple classes to avoid duplication.【F:tests/sflow/test_sflow.py†L297-L312】
- `partial_ptf_runner`: Wraps `ptf_runner` with default arguments so subtests can easily trigger packet sampling validation with dynamic parameters.【F:tests/sflow/test_sflow.py†L272-L291】
- `selected_portchannel_members` / `restore_sflow_interface_status_and_rate`: Discover multi-member port-channels for interface testing and ensure cleanup after manipulating sampling rates/status.【F:tests/sflow/test_sflow.py†L316-L355】

### `TestSflowCollector`
1. `test_sflow_config`: Enables sFlow globally, configures a single collector, enables all discovered interfaces, validates CLI state, and runs traffic to confirm samples reach the collector via PTF.【F:tests/sflow/test_sflow.py†L365-L381】 Importance: Baseline coverage ensuring core sFlow sampling works with one collector.
2. `test_collector_del_add`: Removes the collector to confirm samples stop, then re-adds it to ensure functionality returns.【F:tests/sflow/test_sflow.py†L383-L399】 Ensures proper collector lifecycle management.
3. `test_two_collectors`: Uses the base config with two collectors to validate simultaneous sampling, removal, and re-addition workflows, enforces the two-collector limit, and verifies non-default UDP ports.【F:tests/sflow/test_sflow.py†L401-L439】 Confirms multi-collector support and CLI guardrails.

### `TestSflowPolling` (uses `sflowbase_config`, `config_sflow_agent`)
1. `testPolling`: Sets polling interval to 20 seconds, verifies CLI state, and ensures counter samples align via PTF validation.【F:tests/sflow/test_sflow.py†L452-L457】 Validates configurable polling.
2. `testDisablePolling`: Disables polling by setting interval to 0 and verifies counters stop flowing.【F:tests/sflow/test_sflow.py†L459-L465】 Checks ability to disable counter sampling.
3. `testDifferentPollingInt`: Sets polling to 60 seconds and reconfirms behavior.【F:tests/sflow/test_sflow.py†L467-L473】 Ensures multiple interval values apply correctly.

### `TestSflowInterface`
1. `testIntfRemoval`: Disables sFlow on one port-channel member group while leaving others enabled and validates only enabled interfaces produce samples.【F:tests/sflow/test_sflow.py†L484-L501】 Ensures per-interface control.
2. `testIntfSamplingRate`: Assigns different sampling rates to two port-channel groups, verifies CLI reflects new rates, runs traffic, then restores defaults.【F:tests/sflow/test_sflow.py†L503-L545】 Confirms sampling rate programmability and cleanup.

### `TestAgentId`
1. `testNonDefaultAgent`: Forces agent-id to Loopback0, verifies CLI state, and checks that samples use the loopback IP.【F:tests/sflow/test_sflow.py†L550-L566】 Validates custom agent configuration.
2. `testDelAgent`: Removes agent-id to fall back to default (autodiscovered) and confirms samples still flow using the determined agent IP.【F:tests/sflow/test_sflow.py†L568-L577】 Checks graceful fallback behavior.
3. `testAddAgent`: Sets agent-id to management interface (eth0) and ensures samples use management IP.【F:tests/sflow/test_sflow.py†L579-L586】 Validates switching to another interface.

### `TestReboot`
1. `testRebootSflowEnable`: With sFlow enabled and polling interval set, performs a cold reboot, waits for services, confirms redis-state application, revalidates collectors/interfaces, and reruns traffic and polling checks.【F:tests/sflow/test_sflow.py†L591-L618】 Ensures configuration persistence after cold reboot.
2. `testRebootSflowDisable`: Disables sFlow before reboot and verifies it remains disabled afterwards, including traffic validation.【F:tests/sflow/test_sflow.py†L620-L639】 Ensures disabled state persists.
3. `testFastreboot`: Executes fast reboot and ensures collectors/interfaces remain operational.【F:tests/sflow/test_sflow.py†L641-L661】 Validates fast reboot resilience.
4. `testWarmreboot`: Executes warm reboot with similar verifications.【F:tests/sflow/test_sflow.py†L663-L683】 Confirms warm reboot resilience.

## 4. Dependencies and Prerequisites
- **Fixtures:** `duthosts`, `rand_one_dut_hostname`, `ptfhost`, `tbinfo`, `localhost`, and optional `config_sflow_agent`, `sflowbase_config`, and topology-specific fixtures provide device control, topology metadata, and traffic generation capabilities.【F:tests/sflow/test_sflow.py†L33-L355】【F:tests/sflow/test_sflow.py†L443-L586】【F:tests/sflow/test_sflow.py†L591-L683】
- **Topology constraints:** Requires at least three VLAN1000 member ports for collectors and downstream traffic, plus at least two port-channels with multiple members for interface sampling tests; skips otherwise.【F:tests/sflow/test_sflow.py†L50-L77】【F:tests/sflow/test_sflow.py†L335-L339】
- **Services:** sFlow feature must be enabled (handled via fixtures) and hsflowd container accessible for agent checks.【F:tests/sflow/test_sflow.py†L39-L204】【F:tests/sflow/test_sflow.py†L131-L148】
- **PTF preparation:** Copies ARP responder config, assigns collector IPs, and pushes sFlow port map to `/tmp/sflow_ports.json`.【F:tests/sflow/test_sflow.py†L100-L111】

## 5. Key Inputs and Parameters
- **Command-line option:** `--enable_sflow_feature` triggers the fixture to enable sFlow if disabled.【F:tests/sflow/test_sflow.py†L1-L6】【F:tests/sflow/test_sflow.py†L197-L204】
- **Dynamic variables (`var` dict):** Stores router MAC, interface indices, collector definitions, sampling rates, and topology-derived data used across tests and passed to PTF scripts.【F:tests/sflow/test_sflow.py†L35-L111】【F:tests/sflow/test_sflow.py†L272-L290】
- **Collector IP/port assignments:** Two collectors preconfigured with incremental UDP ports starting at 6343 to validate multi-collector scenarios.【F:tests/sflow/test_sflow.py†L82-L89】【F:tests/sflow/test_sflow.py†L401-L439】
- **Polling intervals and sampling rates:** Tests manipulate `config sflow polling-interval` and per-interface `sample-rate` to validate telemetry frequency control.【F:tests/sflow/test_sflow.py†L303-L473】【F:tests/sflow/test_sflow.py†L503-L545】

## 6. External Libraries and Modules
- **PyTest (`pytest`):** Manages fixtures, topology markers, and test organization.【F:tests/sflow/test_sflow.py†L8-L28】
- **Logging/Time/JSON/RE:** Standard Python libs for debug output, waits, serialization, and CLI output parsing.【F:tests/sflow/test_sflow.py†L9-L12】【F:tests/sflow/test_sflow.py†L230-L267】
- **`tests.common` utilities:**
  - `reboot`, `config_reload`: Control DUT state transitions and cleanup.【F:tests/sflow/test_sflow.py†L17-L18】【F:tests/sflow/test_sflow.py†L95】
  - `wait_until`, `get_upstream_neigh_type`, `get_neighbor_port_list`: Synchronization and topology discovery helpers.【F:tests/sflow/test_sflow.py†L19-L21】
  - `pytest_assert`: Provides SONiC-specific assertion helper.【F:tests/sflow/test_sflow.py†L22】
- **PTF tooling:**
  - `ptf_runner` launches PTF-based packet sampling verification scripts.【F:tests/sflow/test_sflow.py†L16】【F:tests/sflow/test_sflow.py†L272-L290】
  - `copy_ptftests_directory` & `copy_arp_responder_py` fixtures ensure necessary PTF test assets exist (implicitly consumed via autouse behavior).【F:tests/sflow/test_sflow.py†L14-L15】
- **System commands via `duthost.shell` / `duthost.command`:** Interact with SONiC CLI, Docker containers, and system files to configure and validate sFlow settings.【F:tests/sflow/test_sflow.py†L121-L683】

## 7. Unspecified Items
- **Testbed inventory specifics (exact device models, speed, ASIC type):** Not specified.
- **Traffic pattern details within `ptftests/sflow_test`:** Not specified in this file; logic resides in external PTF test scripts.
- **Exact pass/fail criteria inside PTF test:** Not specified (handled by `sflow_test`).
