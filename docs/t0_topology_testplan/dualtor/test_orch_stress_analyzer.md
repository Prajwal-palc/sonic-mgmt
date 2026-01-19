# Test Case Analyzer: `tests/dualtor/test_orch_stress.py`

## 1. Topology Type
- **Topology:** `t0` dual ToR testbed annotated via `pytest.mark.topology("t0")`.
- **Inference:** The file is under the `dualtor` suite and explicitly marks the topology as `t0`, implying a dual ToR setup with paired DUTs and muxed server links that the fixtures (`tor_mux_intfs`, `mock_server_ip_mac_map`) manipulate.

## 2. Overall Test Case Purpose
- **High-level goal:** Stress the Dual ToR orchagent by repeatedly toggling mux states and flapping neighbor entries, then confirm Control Resource Manager (CRM) counters return to baseline (no leaks).
- **SONiC context:** Validates the robustness of SONiC's orchagent and CRM handling when dual-homed servers undergo continuous role changes (active/standby) and neighbor churn on a T0 dual ToR topology.

## 3. Detailed Breakdown of Sub-Testcases

### `test_change_mux_state`
- **Intent & Logic:**
  - Applies mocked dual ToR tables/kernel configs, loads SWSS mux configurations to alternate all mux interfaces between active and standby states repeatedly (`--mux-stress-count`).
  - Captures initial CRM facts, performs the stress loop, and compares post-loop CRM facts to ensure no leaks.
- **Contribution:** Confirms that repeatedly switching mux states does not leave lingering CRM entries, ensuring state transitions are correctly orchestrated.

### `test_flap_neighbor_entry_active`
- **Intent & Logic:**
  - Forces mux into active state, snapshots CRM counters, then repeatedly removes and re-adds all mocked server neighbors on the VLAN interface.
  - After the flap loop, re-checks CRM facts and asserts equality to detect leaks.
- **Contribution:** Validates CRM stability when neighbor churn occurs while the mux is active, ensuring forwarding entries are correctly cleaned up and reinstated.

### `test_flap_neighbor_entry_standby`
- **Intent & Logic:**
  - Sets mux to standby state, then flaps the neighbor entries identical to the active test.
  - Verifies CRM counters remain stable after repeated flaps while traffic is directed via standby pathways.
- **Contribution:** Extends coverage to the standby role, guaranteeing CRM resilience regardless of mux state.

### Helper Functions & Fixtures
- `mux_state_configs`, `_swss_path`, and `load_swss_config` construct and push SWSS configuration snippets used during state toggling.
- `remove_neighbors` and `add_neighbors` encapsulate neighbor churn commands executed within the looped stress actions.
- Autouse fixtures `swss_config_files` and `config_crm_polling_interval` prepare mock configuration files inside the `swss` container and shrink CRM polling interval for timely updates; they also ensure cleanup.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `apply_mock_dual_tor_tables`, `apply_mock_dual_tor_kernel_configs` (mock the dual ToR control-plane data).
  - `rand_selected_dut` (selects DUT to operate on).
  - `tor_mux_intfs`, `mock_server_ip_mac_map` (provide interface names and neighbor mapping).
  - `tbinfo` (delivers minigraph topology data).
  - Autouse fixtures mentioned above plus the standard PyTest `request` object.
- **Topology Constraints:** Requires a dual ToR-capable T0 testbed with SWSS access for loading mux configs and manipulating neighbors.
- **Libraries:** Access to device shell commands (`dut.shell`, `dut.shell_cmds`, `dut.copy`, `dut.file`) to manipulate CRM and SWSS state.

## 5. Key Inputs and Parameters
- `--mux-stress-count`: CLI option controlling how many times mux states or neighbors are cycled; actual default value **Not specified** in this file.
- `tor_mux_intfs`: List of interfaces connected to the mux; provided by fixtures, specifics **Not specified**.
- `mock_server_ip_mac_map`: Mapping of server IP/MAC addresses to flap; contents **Not specified**.
- `tbinfo`: Supplies VLAN interface names via `get_extended_minigraph_facts`; structure **Not specified**.
- `SWSS_MUX_STATE_*_CONFIG_FILE`: Temporary config file paths created and pushed into the `swss` container for toggling states.

## 6. External Libraries and Modules
- **Standard Library:** `json` (serialize configs, log CRM facts), `logging` (test logging), `os` (path handling).
- **PyTest:** `pytest` for fixtures, marks, config options.
- **SONiC Test Helpers:**
  - `tests.common.utilities.wait`, `compare_crm_facts` (synchronize on CRM updates and diff CRM snapshots).
  - `tests.common.helpers.assertions.pytest_assert` (assertion helper).
  - `tests.common.dualtor.dual_tor_utils.tor_mux_intfs` and `tests.common.dualtor.dual_tor_mock` (provide dual ToR mocks and fixtures).
- These imports enable CRM checks, fixture provisioning, and orchestration of SWSS configuration changes.

## 7. Unspecified Items
- Detailed topology inventory, actual neighbor lists, and the concrete value of `--mux-stress-count` are **Not specified** within this test file.
