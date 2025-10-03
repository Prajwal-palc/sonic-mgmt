# VNET VxLAN Test Analyzer

## 1. Topology type
- **Topology:** `t0`.
- **Inference:** The module-level `pytestmark` applies `pytest.mark.topology("t0")`, indicating all tests in this file target the T0 topology that features a single TOR with multiple downstream servers. This mark drives testbed selection in the SONiC automation framework.

## 2. Overall test case purpose
- **Goal:** Validate VNET VxLAN functionality on a T0 SONiC device, covering configuration application, dataplane forwarding, neighbor reachability, and cleanup workflows.
- **Context:** The test prepares DUT and PTF hosts with generated VNET configuration, runs PTF traffic via the `vnet_vxlan.VNET` test, and optionally validates route flow counters when VxLAN is enabled. This ensures SONiC VNET overlay behaves correctly across operational states (Disabled, Enabled, WR_ARP, Cleanup) and integrates with the route flow counter feature when available.

## 3. Detailed breakdown of sub-testcases and helpers
### `test_vnet_vxlan`
- **Intent:** Execute the end-to-end VNET VxLAN datapath validation for each parameter supplied by the `vxlan_status` fixture (Disabled, Enabled, WR_ARP, Cleanup).
- **Logic:**
  - Retrieves DUT information and the setup-generated `/tmp/vnet.json` describing interfaces, routes, and neighbors.
  - Builds PTF parameters (credentials, UDP sport configuration, cleanup indicators) and sets up a timestamped log path.
  - For the `Enabled` scenario, wraps the PTF run within `RouteFlowCounterTestContext` to assert expected packet counters on a representative route (`Vnet1|100.1.1.1/32`). Other scenarios run the PTF test without the counter context.
  - Skips cleanup execution when the VNET cleanup feature flag is disabled.
- **Relevance:** This single test orchestrates all scenarios, verifying both steady-state forwarding (Enabled) and control workflows (Disabled/WR_ARP/Cleanup), fulfilling the file’s overall validation objective.

### Helper fixtures and functions
- **`load_minigraph_after_test` (autouse):** Restores the DUT configuration to minigraph defaults after the module completes by calling `config_reload`. Prevents residual test configuration from impacting subsequent runs.
- **`prepare_ptf`:** Generates the PTF-side `vnet.json`, configures the ARP responder, and pushes the rendered configuration to the PTF host. Ensures the traffic generator is aware of DUT interfaces, peers, and routes.
- **`setup`:** Combines minigraph facts with DUT-generated VNET configuration files. Invokes `generate_dut_config_files` to build SONiC-side templates and returns minigraph data and the PTF configuration for later use.
- **`vxlan_status` (parameterized):** Applies scenario-specific DUT configuration:
  - `Disabled`: Leaves VxLAN untouched.
  - `Enabled`: Clears FDB, temporarily removes VLAN tagging mode, applies DUT configs, and waits for neighbor reachability via `is_neigh_reachable`.
  - `Cleanup`: When enabled, restores VLAN tagging, removes routes, VNETs, and VxLAN tunnels.
  - `WR_ARP`: Calls ARP warm-reboot helper (`testWrArp`) with setup/teardown support.
  It also tracks whether VxLAN is active for downstream validation.
- **`is_neigh_reachable`:** Verifies expected neighbors in the Linux ARP table, reapplying neighbor configuration if missing.
- **`get_expected_flow_counter_packets_number`:** Computes the expected packet count per route for flow counter validation based on VNET routes, peers, and local routes extracted from `vnet.json`.

## 4. Dependencies and prerequisites
- **Fixtures:** `duthosts`, `rand_one_dut_hostname`, `ptfhost`, `minigraph_facts`, `vnet_config`, `vnet_test_params`, `creds`, `tbinfo`, and the autouse `load_minigraph_after_test`.
- **Topology constraints:** Requires a T0 topology with accessible PTF host and DUT supporting VNET/VxLAN features.
- **Utilities:** Depends on SONiC helper modules for generating/applying VNET configs (`generate_dut_config_files`, `apply_dut_config_files`), cleanup helpers, ARP utilities, and flow counter support.
- **PTF environment:** Needs the `ptftests/vnet_vxlan.VNET` test module available on the PTF host along with supervisor-managed ARP responder.

## 5. Key inputs and parameters
- **`vnet_test_params`:** Supplies runtime controls such as VxLAN UDP source port, mask, range enable flag, number of routes (`num_routes` from command line), and whether cleanup is allowed (`CLEANUP_KEY`).
- **`vnet_config`:** Template-rendered structure describing VNET interfaces, routes, neighbors, peers, and local routes used to configure both DUT and PTF.
- **`mg_facts` / `minigraph_facts`:** Provide topology facts (VLAN members, port indices) for configuration rendering.
- **`creds`:** Carries SONiC admin credentials passed to the PTF runner for management operations.
- **`request.param` in `vxlan_status`:** Drives scenario selection across Disabled, Enabled, WR_ARP, and Cleanup paths.

## 6. External libraries and modules
- **Standard:** `json`, `logging`, `re`, `datetime` for data manipulation, logging, regex parsing, and timestamps.
- **PyTest:** `pytest`, fixtures, parameterization, and assertions (`pytest_assert`).
- **SONiC helpers:**
  - `tests.common.helpers.assertions.pytest_assert` for custom assertion messaging.
  - `tests.common.utilities.wait_until` for neighbor reachability polling.
  - `tests.ptf_runner.ptf_runner` to launch PTF dataplane tests.
  - VNET utilities (`vnet_constants`, `vnet_utils`) for configuration generation and cleanup.
  - Flow counter utilities (`RouteFlowCounterTestContext`, `is_route_flow_counter_supported`) for conditional counter validation.
  - ARP utilities (`set_up`, `tear_down`, `testWrArp`) for warm-reboot ARP scenario.
  - `tests.common.config_reload.config_reload` to restore minigraph configuration.

## 7. Unspecified items
- **Traffic profiles or packet contents:** Not specified.
- **Exact expectations for PTF test pass/fail criteria:** Not specified.
- **External testbed inventory references beyond the T0 marker:** Not specified.
