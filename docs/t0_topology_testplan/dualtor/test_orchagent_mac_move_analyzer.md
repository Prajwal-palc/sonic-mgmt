# Test Analyzer: `tests/dualtor/test_orchagent_mac_move.py`

## 1. Topology Type
- **Topology:** `t0` dual ToR testbed.
- **Inference:** The module-level `pytestmark` applies `pytest.mark.topology('t0')`, indicating the test is scoped to a T0 topology. Dual ToR behavior is implied by fixtures such as `apply_mock_dual_tor_tables`, `apply_mock_dual_tor_kernel_configs`, and utilities imported from `tests.common.dualtor.*`, which target dual ToR environments.

## 2. Overall Test Case Purpose
- **Goal:** Validate MAC move handling in SONiC dual ToR scenarios, ensuring that newly learned neighbor entries move correctly between active and standby links and that forwarding behavior adheres to expectations after FDB changes.
- **Context:** Within SONiC dual ToR orchestration-agent workflows, the test verifies that neighbor learning, CRM usage, tunnel traffic, and server traffic monitoring remain consistent when MAC addresses migrate between ToR interfaces (active↔standby). This supports resilience and traffic correctness for dual ToR deployments.

## 3. Detailed Breakdown of Sub-Testcases
### `test_mac_move`
- **Intent & Logic:**
  1. Randomly selects a ToR and a T1-facing PTF interface. Uses the `announce_new_neighbor` fixture to generate gratuitous ARP (GARP) packets, learning a new neighbor on an active mux port.
  2. Sends traffic toward the new neighbor, with `crm_neighbor_checker`, `tunnel_traffic_monitor`, and `ServerTrafficMonitor` ensuring proper tunnel behavior and direct server delivery when the neighbor is on the active path.
  3. Announces the neighbor again, switching ToR state to `standby` for that interface via `set_dual_tor_state_to_orchagent`. Confirms traffic now traverses tunnel paths and does not reach the server directly.
  4. Clears FDB entries to validate continued standby forwarding after age-out/flush.
  5. Announces the neighbor on a different active port, verifying that traffic now reaches the server without tunnel forwarding.
  6. Conditionally clears FDB again (skipping Mellanox or Cisco-8000 ASICs) to confirm active forwarding resiliency after FDB loss.
- **Relevance:** Demonstrates the orchestration agent’s ability to react to MAC moves, ensuring correct traffic steering between active and standby paths and maintaining neighbor table integrity under FDB churn, which is critical for dual ToR redundancy and failover.

### Helper Fixtures and Utilities
- `announce_new_neighbor`: Generates GARPs from different mux-connected interfaces, optionally executing callbacks (e.g., to change ToR state) before each announcement.
- `cleanup_arp` (autouse): Clears ARP tables after the test to avoid residue affecting subsequent cases.
- `enable_garp` (autouse): Temporarily enables `arp_accept` to allow GARPs to create ARP entries on VLAN interfaces.
- These helpers orchestrate environment state changes and cleanup required for accurate MAC move testing.

## 4. Dependencies and Prerequisites
- **Fixtures:** `apply_mock_dual_tor_tables`, `apply_mock_dual_tor_kernel_configs`, `run_garp_service`, `run_icmp_responder`, `announce_new_neighbor`, `apply_active_state_to_orchagent`, `conn_graph_facts`, `ptfadapter`, `ptfhost`, `rand_selected_dut`, `set_crm_polling_interval`, `tbinfo`, `tunnel_traffic_monitor`, `vmhost`, `cleanup_arp`, `enable_garp`.
- **Topology Constraints:** Requires dual ToR-capable T0 topology with mux cables and server/T1 connections.
- **Enablement:** Fixtures set mock tables, configure kernel behavior, run auxiliary services (GARP, ICMP responder), and manage state transitions necessary to simulate MAC moves accurately.

## 5. Key Inputs and Parameters
- `NEW_NEIGHBOR_IPV4_ADDR`, `NEW_NEIGHBOR_HWADDR`: Define the synthetic neighbor announced via GARPs.
- `get_t1_ptf_ports(tor, tbinfo)`: Determines T1-facing PTF ports for traffic injection.
- `mux_cable_server_ip(rand_selected_dut)`: Provides mux interface mapping for neighbor announcements.
- `rand_selected_dut`: Chooses the DUT for the test run.
- `set_dual_tor_state_to_orchagent`: Callback used to change ToR state (active/standby) during MAC move steps.

## 6. External Libraries and Modules
- **`logging` / `random`:** Standard Python utilities for logging and random selection.
- **`pytest`:** Testing framework providing fixtures and parametrization.
- **`ptf.testutils`:** Sends and inspects packets via PTF.
- **`tests.common.dualtor.*`:** SONiC dual ToR helpers (mocking ToR state, CRM checking, packet building, mux info).
- **`tests.common.server_traffic_utils.ServerTrafficMonitor`:** Monitors traffic reaching servers.
- **`tests.common.tunnel_traffic_utils.tunnel_traffic_monitor`:** Observes tunnel traffic to validate standby forwarding.
- **`tests.common.fixtures.ptfhost_utils`:** Provides fixtures for running services (ICMP responder, GARP) and modifying MAC addresses.
- **`tests.common.utilities.dump_scapy_packet_show_output`:** Formats packets for logging.

## 7. Unspecified Items
- Any details not explicitly covered above (e.g., exact `testbed.yaml` entries, specific hardware models, CLI parameters outside this file) are **Not specified** in the test file.
