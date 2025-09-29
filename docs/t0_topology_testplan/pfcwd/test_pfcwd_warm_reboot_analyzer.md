# `tests/pfcwd/test_pfcwd_warm_reboot.py` Analyzer

## 1. Topology type
- **Topology:** `t0`.
- **Inference:** The module-level `pytestmark` applies `pytest.mark.topology('t0')`, constraining the test to topologies tagged as T0. This is reinforced by the heavy reliance on leaf-spine fanout information and VLAN neighbors that match a T0 testbed layout.

## 2. Overall test case purpose
- **High-level goal:** Validate PFC watchdog (PFCwd) detection and recovery behavior across warm reboot cycles, ensuring service resilience and traffic handling correctness before, during, and after device reboot.
- **Context within SONiC testing:** PFCwd protects lossless queues by detecting PFC storms and applying drop/forward actions. This test stresses the mechanism around warm reboot, confirming SONiC maintains watchdog state, resumes detection, and restores traffic appropriately on T0 chassis with active fanout neighbors.

## 3. Detailed breakdown of sub-testcases
### `test_pfcwd_wb`
- **Intent:** Execute the warm reboot PFCwd regression for three scenarios (`no_storm`, `storm`, `async_storm`) supplied by the `testcase_action` fixture. Each scenario defines a sequence of actions (`detect`, `restore`, `storm_defer`, `warm-reboot`) that the helper walks through.
- **Logic:**
  1. Skips execution when no neighbor device is available (fake storms require Rx ports).
  2. Selects the target DUT via `enum_rand_one_per_hwsku_frontend_hostname` and logs the scenario description from `TESTCASE_INFO`.
  3. Delegates to `pfcwd_wb_helper`, which initializes timers, port mappings, and queue indices from `setup_pfc_test`, configures storm generators (`PFCStorm` instances or fake storm markers), and iterates through the scenario steps. Actions include:
     - Triggering PFC storm detection (`storm_detect_path`) that starts storms, enables background traffic, and verifies syslog via `LogAnalyzer` for expected detect messages.
     - Performing storm restoration (`storm_restore_path`) to ensure storms stop and restore logs appear.
     - Handling deferred storms (`storm_defer_setup`, `defer_fake_storm`) to asynchronously toggle fake storms across warm reboot.
     - Invoking warm reboot (`reboot(..., reboot_type="warm")`) and waiting for `critical_services_fully_started`.
     - Running `SendVerifyTraffic.verify_wd_func` to send ingress/egress PTF traffic and validate drop/forward behavior per watchdog state.
     - Continuously capturing watchdog status via `pfcwd_show_status` for observability.
  4. The helper enforces cleanup through the `pfcwd_wb_test_cleanup` fixture, stopping storms, restoring configuration, and ensuring services recover.
- **Relevance:** Confirms watchdog logic remains functional for different storm lifecycles relative to warm reboot, a critical resilience requirement for lossless traffic.

### Supporting helpers and fixtures
- **`skip_pfcwd_wb_tests` (module autouse fixture):** Skips ASICs where warm reboot is unsupported (Broadcom TD2).
- **`setup_pfcwd` (module autouse fixture):** Ensures default PFCwd configuration is active prior to tests.
- **`PfcCmd`:** Utility for manipulating fake storm state in Redis.
- **`SetupPfcwdFunc`:** Base mixin supplying per-port setup, ARP resolution, storm preparation, and helper methods for deferred storms.
- **`SendVerifyTraffic`:** Encapsulates PTF runner invocations to verify forwarding/drop behavior on ingress and egress during detect/restore phases.
- **`TestPfcwdWb.pfcwd_wb_helper`:** Core orchestrator executing the scenario sequences, invoking storm actions, warm reboot, and traffic verification.
- **`pfcwd_wb_test_cleanup` (class autouse fixture):** Guarantees storms are stopped, watchdog disabled, and configuration reloaded after each test case.
- **`calculate_send_pfc_frame_interval`:** Computes peer-specific PFC frame intervals for certain fanout OSes.

## 4. Dependencies and prerequisites
- **Fixtures:** `duthosts`, `enum_rand_one_per_hwsku_frontend_hostname`, `setup_pfc_test`, `enum_fanout_graph_facts`, `ptfhost`, `localhost`, `fanouthosts`, `fake_storm`, `two_queues`, and module autouse fixtures described above.
- **Topology constraints:** Requires a T0 testbed with active neighbors/fanout ports (validated via `has_neighbor_device`).
- **Services:** Access to Redis, SWSS container commands, and ability to issue `pfcwd` CLI commands on the DUT.
- **Storm generation capability:** Either real fanout-driven PFC storms (`PFCStorm`) or fake storms controlled via Redis OIDs.
- **Logging:** `LogAnalyzer` availability and templates in `templates/ignore_pfc_wd_messages`.

## 5. Key inputs and parameters
- **`TESTCASE_INFO`:** Dictates action sequences and human-readable descriptions per scenario.
- **`ACTIONS` bitmask:** Controls scenario flow inside `pfcwd_wb_helper` (detect, restore, storm_defer flags).
- **`setup_pfc_test` output:** Supplies VLAN data, selected ports, neighbor addressing, timers, and queue configuration essential for traffic generation.
- **`fake_storm` fixture:** Switches between real and fake storm modes, affecting whether `PFCStorm` is deployed or Redis debug flags are toggled.
- **`two_queues` fixture:** Enables testing an additional queue when true, altering queue selection logic.
- **`enum_fanout_graph_facts` / `fanouthosts`:** Provide peer device metadata and fanout control for real storm generation.
- **`critical_services_fully_started`:** Post-reboot gating condition ensuring DUT readiness before proceeding.
- **`calculate_send_pfc_frame_interval`:** Parameterizes PFC frame pacing for Onyx fanouts.

## 6. External libraries and modules
- **Standard library:** `datetime`, `logging`, `os`, `random`, `time`, `traceback` for timing, logging, filesystem paths, and error handling.
- **PyTest:** `pytest` for fixtures, parametrization, marks, and assertions.
- **SONiC test utilities:**
  - `tests.common.broadcom_data.is_broadcom_device` for ASIC detection.
  - `tests.common.fixtures.conn_graph_facts.enum_fanout_graph_facts` fixture providing fanout topology facts.
  - `tests.common.helpers.assertions.pytest_require` for conditional skips.
  - `tests.common.helpers.pfc_storm.PFCStorm` for orchestrating hardware-based storms.
  - `tests.common.plugins.loganalyzer.loganalyzer.LogAnalyzer` for syslog validation.
  - `tests.common.reboot.reboot` and `DUT_ACTIVE` for warm reboot control and synchronization.
  - `tests.common.utilities.InterruptableThread`, `join_all`, `wait_until` for threading and polling.
  - `tests.ptf_runner.ptf_runner` for executing PTF scripts.
  - `tests.common.constants` for VLAN sub-interface constants.
  - `tests.common.helpers.pfcwd_helper` utilities (`EXPECT_PFC_WD_DETECT_RE`, `EXPECT_PFC_WD_RESTORE_RE`, `pfcwd_show_status`, `send_background_traffic`, `has_neighbor_device`).
  - `tests.common.config_reload` for restoring configuration post-test.

## 7. Unspecified items
- **Exact contents of fixtures (`setup_pfc_test`, `fake_storm`, `two_queues`, etc.):** Not specified in this file.
- **Precise testbed YAML variables or inventory paths:** Not specified.
- **External template file contents (`templates/ignore_pfc_wd_messages`):** Not specified.
