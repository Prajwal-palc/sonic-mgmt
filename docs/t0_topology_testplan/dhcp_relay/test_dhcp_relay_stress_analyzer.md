# DHCP Relay Stress Test Analyzer

## 1. Topology Type
- **Identified Topologies:** `t0` and `m0` are marked in `pytestmark`, indicating support for single ToR (t0) and multi-ASIC/mock (m0) deployments. The primary validations rely on T0 data structures such as VLAN interfaces and uplink/downlink relationships exposed by the `dut_dhcp_relay_data` fixture, which is typical for the SONiC T0 topology used to validate DHCP relay behavior.
- **Inference Method:** Derived from `pytest.mark.topology('t0', 'm0')`, the reliance on ToR-specific fixtures (`dut_dhcp_relay_data`, dual ToR toggles), and the use of VLAN client/server port definitions that mirror T0 wiring.

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate the robustness of SONiC's DHCP relay service when subjected to sustained stress traffic, including verifying correct packet forwarding, service recovery after restarts, and ensuring packet counters remain within tolerance bounds.
- **Framework Context:** These tests exercise the DHCP relay functionality within SONiC's T0-style data plane using PTF-generated traffic. They leverage the SONiC test automation framework's fixtures to manipulate the DUT, control dual ToR mux state, and run PTF stress utilities to ensure DHCP relay resilience and correctness under load and during service restarts.

## 3. Detailed Breakdown of Sub-Testcases
### `test_dhcp_relay_restart_with_stress`
- **Intent & Logic:**
  - Verifies DHCP relay resilience when the service is restarted while high-rate DHCP stress traffic is in flight.
  - Launches `dhcp_relay_stress_test.DHCPContinuousStressTest` on the PTF host to continuously generate DHCP packets against the first VLAN interface.
  - Restarts the DHCP service on the DUT, waits for stabilization, and ensures the stress generator is terminated.
  - Confirms the DUT's socket buffers are drained (`ss -nlpu` check) and then runs the standard DHCP functional test `dhcp_relay_test.DHCPTest` to confirm normal relay behavior post-restart.
- **Relevance:** Ensures that DHCP relay remains functional and free of backlog after disruptive events such as service restarts while under stress, demonstrating robustness.
- **Helper Elements:** Uses helper functions like `restart_dhcp_service`, `wait_until`, and `capture_and_check_packet_on_dut` to orchestrate service control and validation.

### `test_dhcp_relay_stress`
- **Intent & Logic:**
  - Parameterized over DHCP message types (`discover`, `offer`, `request`, `ack`) to validate behavior across the entire DHCP handshake.
  - For each VLAN relay entry, gathers port and addressing metadata from `dut_dhcp_relay_data` and constructs PTF parameters for the stress generator `DHCPStress{Type}Test`.
  - Uses `capture_and_check_packet_on_dut` to sniff DUT interfaces and validate packet counts (`_verify_server_packets`/`_verify_client_packets`) remain within ±10% of expected values, scaling by the number of DHCP servers for client-originated messages.
  - Invokes `check_dhcp_stress_status` to ensure the DUT reports healthy stress status and confirms per-type packet counters written by the PTF script.
- **Relevance:** Demonstrates that DHCP relay handles sustained, high-rate load for each DHCP transaction phase, guaranteeing reliability and capacity of the relay service.
- **Helper/Inner Functions:**
  - `_check_count_file_exists` verifies that the PTF stress script outputs expected packet counts to `/tmp/dhcp_stress_test_<type>.json`.
  - `_verify_server_packets` and `_verify_client_packets` enforce correctness of packet relaying by comparing sniffed packet counts with expected counts from the PTF host.

## 4. Dependencies and Prerequisites
- **Fixtures:** `ptfhost`, `ptfadapter`, `dut_dhcp_relay_data`, `validate_dut_routes_exist`, `testing_config`, `setup_standby_ports_on_rand_unselected_tor`, `toggle_all_simulator_ports_to_rand_selected_tor_m`, `clean_processes_after_stress_test`, `request`.
- **Purpose:**
  - Provide DUT handles, topology metadata, route validation, and ToR mux control necessary for the stress scenarios.
  - Ensure PTF host is prepared (via `copy_ptftests_directory`) and background processes are cleaned after tests.
- **Topology Constraints:** Requires at least one VLAN relay configuration on the DUT (`pytest_require(len(dut_dhcp_relay_data) >= 1)`), indicating the necessity of a T0-style VLAN-based topology.

## 5. Key Inputs and Parameters
- **Stress Control Options:** Command-line options retrieved through `request.config.getoption` (`--stress_restart_duration`, `--stress_restart_pps`, `--stress_restart_round`) dictate duration, packet-per-second rate, and iteration count for restart stress testing.
- **PTF Parameters:** Derived from `dut_dhcp_relay_data` and include client/server port indices, MAC addresses, DHCP server IPs, relay interface addressing, and loopback IPs. These inputs configure the PTF stress scripts to generate accurate DHCP traffic flows matching the DUT configuration.
- **Hardcoded Stress Settings:** `packets_send_duration = 120` seconds and `client_packets_per_sec = 10000` for the per-type stress test, defining sustained load levels.

## 6. External Libraries and Modules
- **`pytest`:** Provides the testing framework, parameterization, fixtures, and assertions.
- **`time`:** Used for delays after restarting services to allow stabilization.
- **`ptf.packet (scapy)`:** Enables packet parsing when validating captured DHCP traffic.
- **SONiC Test Helpers:**
  - `tests.common.fixtures.ptfhost_utils.copy_ptftests_directory`: Ensures PTF test scripts are available on the host.
  - `tests.common.dualtor.mux_simulator_control.toggle_all_simulator_ports_to_rand_selected_tor_m`: Controls dual ToR simulator ports for correct traffic orientation.
  - `tests.dhcp_relay.dhcp_relay_utils` (`restart_dhcp_service`, `check_dhcp_stress_status`): Manages DHCP service lifecycle and status validation.
  - `tests.common.helpers.assertions` (`pytest_assert`, `pytest_require`): SONiC-specific assertion wrappers.
  - `tests.common.utilities` (`wait_until`, `capture_and_check_packet_on_dut`): Utilities for polling conditions and capturing packets on the DUT.
  - `tests.ptf_runner.ptf_runner`: Executes PTF-based traffic generation scripts.

## 7. Unspecified Items
- Any details beyond what is described above (e.g., exact structure of `dut_dhcp_relay_data`, implementation of helper fixtures, or stress PTF scripts) are **Not specified** within this test file.
