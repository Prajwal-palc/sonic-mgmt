# FDB MAC Learning Test Analyzer

## 1. Topology Type
- **Topology:** `t0`.
- **Inference:** The module-level `pytestmark` applies `pytest.mark.topology('t0')`, constraining the test to run on T0-based SONiC topologies.

## 2. Overall Test Case Purpose
- This test module validates **Forwarding Database (FDB) MAC learning behavior** and associated **ARP functionality** on a SONiC DUT.
- It ensures that stale MAC entries are removed after topology churn and explicit `sonic-clear fdb all`, and that dynamic FDB population via PTF traffic functions as expected.
- The tests operate within SONiC's pytest infrastructure, coordinating DUT control through Ansible hosts and leveraging PTF for traffic generation to mimic real network events.

## 3. Detailed Breakdown of Sub-Testcases
### `testFdbMacLearning`
- **Intent & Logic:**
  - Obtains four operational trunk ports, maps them to PTF interfaces, and reinitializes DUT state.
  - Sequentially brings up interfaces, triggers PTF traffic to populate FDB entries using a dummy MAC prefix, and confirms dynamic entries appear for each active port.
  - Shuts down three ports to simulate link flaps, waits, and verifies the corresponding MAC entries are removed from the table.
  - Issues `sonic-clear fdb all`, repopulates the FDB via PTF on the remaining active port, and confirms no stale entries persist for downed ports.
- **Why It Matters:** Confirms SONiC's MAC learning and cleanup processes are resilient to interface state changes and explicit FDB flush commands, preventing stale forwarding state that could cause traffic blackholes.

### `testARPCompleted`
- **Intent & Logic:**
  - Selects a DUT/PTF port pair, ensures the DUT interface is active and not part of a VLAN for the test, assigns IP addresses to both sides, and performs ICMP ping from PTF to DUT.
  - Validates that the DUT's ARP table contains a complete entry (with correct interface) for the PTF host following the ping exchange.
- **Why It Matters:** Verifies Layer 3 neighbor discovery remains functional after port manipulations, ensuring that MAC learning at L2 aligns with ARP resolution at L3 for the selected interfaces.

### Helper Fixtures and Functions
- `prepare_test` (class-scoped, autouse): Selects four trunk ports, builds DUT-to-PTF mappings, shuts down all ports pre-test, and reloads configuration post-test.
- `cleanup_arp_fdb` (autouse): Clears ARP and FDB tables before and after each test to remove residue from prior runs.
- `dynamic_fdb_oper`: Invokes PTF tests (`fdb_mac_learning_test.FdbMacLearningTest`) to generate traffic that learns MACs.
- `wait_for_interfaces_ready`: Provides a stabilization delay after port state changes.
- `configureInterfaceIp` / `configureNeighborIp`: Helper methods to add/remove IP configuration on DUT and PTF.
- `ignore_expected_loganalyzer_exception`: Adds known noisy log entries to LogAnalyzer ignore lists.

## 4. Dependencies and Prerequisites
- **Fixtures:** `ptfadapter`, `duthosts`, `rand_one_dut_hostname`, `ptfhost`, `tbinfo`, `request`, `prepare_test`, `cleanup_arp_fdb`, `toggle_all_simulator_ports_to_rand_selected_tor_m`, and the `loganalyzer` fixture accessed via `ignore_expected_loganalyzer_exception`.
- **Topology Constraints:** Requires a T0 testbed with at least four operational trunk interfaces and corresponding PTF port mappings.
- **Environment:** Access to PTF host with `ptftests` package, DUT command access via Ansible, and dual ToR mux simulator control when applicable.

## 5. Key Inputs and Parameters
- `tbinfo["topo"]["name"]`: Identifies topology type passed to PTF test.
- `duthost.facts["router_mac"]`: DUT router MAC used in PTF parameters.
- `target_ports_to_ptf_mapping`: Derived mapping of DUT interfaces to PTF port indices for traffic injection.
- Hard-coded IP settings (`DUT_INTF_IP`, `PTF_HOST_IP`, netmasks) guide ARP validation.
- Dummy MAC prefix (`DUMMY_MAC_PREFIX`) defines expected learned entries.

## 6. External Libraries and Modules
- **Standard Library:** `logging`, `time` for logging and timing controls.
- **PyTest:** `pytest` for fixtures and test orchestration.
- **SONiC Test Utilities:**
  - `tests.common.config_reload` for restoring DUT configuration.
  - `tests.common.utilities.wait_until` for polling conditions.
  - `tests.common.helpers.assertions.pytest_assert` for descriptive assertions.
  - `tests.common.fixtures.ptfhost_utils.copy_ptftests_directory` to ensure PTF tests are available.
  - `tests.ptf_runner.ptf_runner` to execute PTF-based traffic tests.
  - `.utils.fdb_table_has_dummy_mac_for_interface` to inspect FDB entries.
  - `tests.common.dualtor.mux_simulator_control.toggle_all_simulator_ports_to_rand_selected_tor_m` fixture for dual ToR environments.

## 7. Unspecified Items
- Any additional configuration sources (e.g., testbed.yaml specifics, group variables beyond those referenced) are **Not specified** in this file.
- Expected traffic patterns within the invoked PTF test (`fdb_mac_learning_test.FdbMacLearningTest`) are **Not specified** in this module.
