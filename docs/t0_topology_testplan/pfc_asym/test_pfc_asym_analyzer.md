# PFC Asymmetric Mode Test Plan Analyzer

## 1. Topology Type
- **Topology:** T0 leaf-spine topology.
- **Inference:** The module-level `pytestmark` enforces `pytest.mark.topology('t0')`, and the shared `setup` fixture explicitly skips the suite unless `tbinfo['topo']['name'] == "t0"`. This combination confirms the test is designed for the T0 topology where the DUT connects to server-facing and portchannel uplinks used in the PFC asymmetric validation.

## 2. Overall Test Case Purpose
- **Goal:** Validate Priority Flow Control (PFC) asymmetric mode behavior on a SONiC DUT. The tests ensure that when asymmetric PFC is disabled or enabled, the DUT correctly generates and reacts to PFC pause frames across lossless and lossy priorities.
- **Context:** Within SONiC's QoS verification, these tests confirm that configuring asymmetric PFC does not violate expected congestion-handling semantics. The suite orchestrates traffic via PTF-hosted SAITests to simulate congestion and validates DUT behavior using SONiC CLI and Redis DB state, integrating with the SpyTest/pytest infrastructure for topology-aware execution.

## 3. Detailed Breakdown of Sub-Testcases
### `test_pfc_asym_off_tx_pfc`
- **Intent:** With asymmetric PFC disabled, verify the DUT only sends PFC frames on lossless priorities when congestion is induced on a non-server (uplink) port.
- **Logic:** The shared `pfc_storm_runner` fixture is configured to target the non-server port (`non_server_port = True`) before starting the fanout-based PFC generator. After inducing congestion, the test runs the SAITest `pfc_asym.PfcAsymOffOnTxTest` on the PTF host with parameters built by the `setup` fixture to verify DUT transmission behavior.
- **Relevance:** Confirms baseline behavior (asymmetric PFC off) and provides the control scenario against which asymmetric mode is compared.

### `test_pfc_asym_off_rx_pause_frames`
- **Intent:** With asymmetric PFC disabled, confirm the DUT reacts to received PFC frames by pausing only lossless queues when both RX and TX buffers fill.
- **Logic:** The storm runner is configured to exercise server-facing ports (`server_ports = True`) to generate PFC frames from the fanout switch. The PTF executes `pfc_asym.PfcAsymOffRxTest`, validating that queues mapped to lossless priorities drop traffic while lossy queues remain unaffected.
- **Relevance:** Ensures proper PFC pause behavior when asymmetric mode is not active, validating RX-side handling for the control case.

### `test_pfc_asym_on_tx_pfc`
- **Intent:** With asymmetric PFC enabled (via the `enable_pfc_asym` fixture), ensure the DUT still emits PFC frames only on configured lossless priorities during congestion on a non-server port.
- **Logic:** Enables asymmetric PFC across server interfaces before running the same Tx-focused SAITest (`pfc_asym.PfcAsymOffOnTxTest`). Congestion is induced on the uplink (`non_server_port = True`), and SAITest verifies that enabling asymmetric mode does not inadvertently pause lossy priorities on transmit.
- **Relevance:** Verifies asymmetric configuration does not alter transmit pause behavior, maintaining deterministic QoS guarantees.

### `test_pfc_asym_on_handle_pfc_all_prio`
- **Intent:** With asymmetric PFC enabled, validate that the DUT honors received PFC frames on all priorities, as asymmetric mode should map all priorities to RX pause while keeping TX limited to lossless.
- **Logic:** The storm runner targets server ports (`server_ports = True`) to send PFC frames across priorities. The PTF executes `pfc_asym.PfcAsymOnRxTest`, checking that the DUT responds appropriately, including lossy priorities on the RX side when required by asymmetric mode.
- **Relevance:** Demonstrates the expected change in RX behavior once asymmetric mode is enabled, completing the comparison between symmetric and asymmetric modes.

### Helper Fixtures and Utilities
- **`prepare_syncdrpc` (autouse module fixture):** Declares dependency on `swapSyncd` fixture to ensure syncd RPC mode is prepared before tests; implementation is a placeholder because the preparation occurs in `swapSyncd`.
- **`setup` fixture:** Orchestrates environment preparation—validates topology, discovers DUT/port metadata, copies necessary scripts/templates to the PTF host, sets up ARP responder, and builds dictionaries with port/pfc mappings passed to SAITests.
- **`pfc_storm_runner` fixture:** Provides a callable object that starts/stops the fanout-based PFC generator with context-aware interface targeting.
- **`enable_pfc_asym` fixture:** Toggles asymmetric PFC on the DUT via CLI and validates Redis state, restoring defaults after tests finish.
- **`tests/pfc_asym/conftest.py` fixtures:** Provide fanout connection facts, copy PTF/SAI test suites, and flush DUT ARP tables before each test run to ensure clean neighbor learning.

## 4. Dependencies and Prerequisites
- **Fixtures:** `ptfhost`, `setup`, `pfc_storm_runner`, `enable_pfc_asym`, `swapSyncd`, `fanouthosts`, `fanout_graph_facts`, `duthosts`, `rand_one_dut_hostname`, `tbinfo`, `ansible_facts`, `minigraph_facts`.
- **Resources:** Fanout switch with supported HWSKU (MLNX-OS or Arista) for PFC generation templates; access to PTF host for SAITest execution; inventory-provided `--fanout_inventory` and optional `--server_ports_num` CLI parameters.
- **Topology Constraint:** T0 topology with server-facing VLAN members and at least one portchannel member uplink, required by `setup` for deriving server and non-server ports.
- **Preparation Tasks:** Deployment of helper scripts (`pfc_gen.py`, `arp_responder.py`), copying SAITests/PTF tests, generating port maps, and ensuring ARP responder is running on the PTF host.

## 5. Key Inputs and Parameters
- **`setup["ptf_test_params"]`:** Includes port map path, server/non-server port metadata, router MAC, PFC-to-DSCP mappings, and priority lists. Passed into SAITests to drive traffic generation/verification.
- **`setup["pfc_bitmask"]`:** Precomputed bitmasks for default, RX, and TX PFC priorities used by fixtures (e.g., `enable_pfc_asym`) to validate Redis state.
- **`setup["server_ports_oids"]`:** SAI object IDs for server-facing ports used when enabling/disabling asymmetric mode.
- **CLI Options:** `--fanout_inventory` identifies the Ansible inventory for fanout automation; `--server_ports_num` optionally limits server ports used in the test.
- **Fanout Interface Lists:** Derived inside `pfc_storm_runner` from connection graph facts to target either server or non-server interfaces when generating PFC storms.

## 6. External Libraries and Modules
- **`pytest`:** Provides test discovery, fixtures, and marking for topology selection.
- **`tests.ptf_runner.ptf_runner`:** Helper to execute PTF-based SAITests from pytest.
- **`tests.common.fixtures.pfc_asym`:** Supplies preparation fixtures and utilities described above.
- **`tests.common.fixtures.conn_graph_facts.fanout_graph_facts`:** Exposes topology connection data for locating relevant fanout devices and ports.
- **`tests.common.fixtures.ptfhost_utils`:** Copy helper directories (`ptftests`, `saitests`) to the PTF host.
- **Standard modules (`os`, `time`, `netaddr.IPAddress`):** Used inside fixtures for filesystem operations, timing, and IP address generation supporting test setup.

## 7. Unspecified Items
- Details about the underlying implementation of `swapSyncd`, low-level SAITest assertions within `pfc_asym.*`, and exact hardware prerequisites beyond supported fanout HWSKUs are **not specified** in the provided test file.
