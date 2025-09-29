# DHCP Relay Counter Stress Test Analyzer

## 1. Topology Type
- **Topology:** `t0` (with optional `m0` coverage).
- **Inference:** The module-level `pytestmark` applies `pytest.mark.topology('t0', 'm0')`, meaning the test is designed for a leaf-spine T0 fabric and is also eligible for M0 setups. The fixtures it consumes (e.g., `dut_dhcp_relay_data`, `validate_dut_routes_exist`, `setup_standby_ports_on_rand_unselected_tor`) are part of the T0 dual-TOR testbed tooling, reinforcing that the primary topology target is T0/M0 deployments where DHCP relay behavior is validated.

## 2. Overall Test Case Purpose
- **High-level goal:** Validate that the SONiC DHCP relay process maintains accurate counter accounting when subjected to sustained, high-rate DHCP message floods.
- **Context in SONiC framework:** This stress test exercises the DHCP relay pipeline, including packet forwarding through client and server VLANs, counter synchronization via `dhcpmon`, and resiliency in dual-TOR mode. It ensures telemetry stays consistent while SONiC processes PTF-driven DHCP traffic at scale.

## 3. Detailed Breakdown of Sub-testcases
### `test_dhcpcom_relay_counters_stress`
- **Intent:** Parameterized over four DHCP exchange message types (`discover`, `offer`, `request`, `ack`). For each VLAN client interface described in `dut_dhcp_relay_data`, the test initializes DHCP relay counters, launches a PTF stress generator, and verifies that counter increments and captured packets align within an error margin (0.01%).
- **Logic:**
  - Determines runtime configuration such as dual-TOR mode, target DUT hostname, packet rate limits, and message type.
  - Initializes relay counters on the active DUT (and the standby DUT when in dual-TOR mode).
  - Prepares parameters for the `dhcp_relay_stress_test.DHCPStress{Type}Test` PTF script, including interface indices, MAC/IP details, loopback addresses, and pacing duration (120 seconds).
  - Uses `capture_and_check_packet_on_dut` to monitor DHCP traffic on the DUT, delegating validation to `_verify_packets`, which waits for DHCP monitor database updates and then calls `validate_counters_and_pkts_consistency` plus `validate_dhcpcom_relay_counters` when dual-TOR is enabled.
  - Runs the PTF test asynchronously, checks the stress status via `check_dhcp_stress_status`, waits (up to 10 minutes) for a per-type JSON result file to be produced on the PTF host, and cleans up.
  - Retrieves the interface index mapping with `get_ip_link_result` for packet validation correlation.
- **Relevance:** Confirms that counter telemetry scales with line-rate DHCP workloads across multiple DHCP message types, ensuring customer monitoring systems can rely on the published counters during stress scenarios.

- **Helper functions defined in-line:**
  - `_check_count_file_exists`: polls for the JSON status artifact emitted by the PTF stress test.
  - `_verify_packets`: enforces a delay for `dhcpmon` to update Redis, then cross-checks packet counts and counter state on active (and standby) DUTs.
  - `get_ip_link_result`: converts `ip link` output into a dictionary of interface name-to-index mappings used by packet validation utilities.
- **Parameterized behavior:** The `@pytest.mark.parametrize('dhcp_type', ...)` decorator expands the single test into four sub-runs, each targeting a different DHCP message, ensuring broad coverage of relay paths.

## 4. Dependencies and Prerequisites
- **Fixtures:** `ptfhost`, `ptfadapter`, `dut_dhcp_relay_data`, `validate_dut_routes_exist`, `testing_config`, `setup_standby_ports_on_rand_unselected_tor`, `toggle_all_simulator_ports_to_rand_selected_tor_m`, `clean_processes_after_stress_test`, `rand_unselected_dut`, and the built-in `request`. These fixtures provide access to DUT facts, topology data, route validation, mux simulator control, cleanup routines, and runtime configuration.
- **Topology requirements:** Availability of a T0/M0 fabric with DHCP relay configured, including dual-TOR components when applicable.
- **PTF environment:** Requires the `ptftests` suite to be present on the PTF host and capable of generating DHCP stress traffic.

## 5. Key Inputs and Parameters
- **`PACKET_RATE_PER_SEC_MAP` / `DEFAULT_PACKET_RATE_PER_SEC`:** Governs DHCP packet generation rate per hardware SKU, with overrides via `--max_packets_per_sec` pytest option (`request.config.option.max_packets_per_sec`).
- **`packets_send_duration` (120 seconds) & `error_margin` (0.01):** Define the stress window and acceptable counter deviation.
- **`dut_dhcp_relay_data`:** Supplies per-VLAN interface metadata (indices, aliases, MACs, IPs, server addresses, loopback IP) used to configure PTF traffic and validate counters.
- **`testing_config`:** Indicates whether the DUT operates in dual-TOR mode and provides the active DUT host reference.
- **`count_file`:** `/tmp/dhcp_stress_test_{dhcp_type}.json` on the PTF host signals completion of the stress script.

## 6. External Libraries and Modules
- **`pytest`, `pytest.mark.parametrize`:** Pytest framework for parametrization and fixture orchestration.
- **`logging`, `time`, `re`:** Standard Python modules for logging, timing delays, and regex parsing (`ip link` output).
- **`tests.common.fixtures.ptfhost_utils.copy_ptftests_directory`:** Ensures PTF tests are available on the PTF host.
- **`tests.common.dualtor.mux_simulator_control.toggle_all_simulator_ports_to_rand_selected_tor_m`:** Fixture to set mux simulator state for dual-TOR tests.
- **`tests.common.dhcp_relay_utils` functions:** `init_dhcpcom_relay_counters`, `validate_dhcpcom_relay_counters`, `validate_counters_and_pkts_consistency` handle counter setup and validation logic.
- **`tests.common.utilities.wait_until`, `capture_and_check_packet_on_dut`:** Polling utility and packet capture helper for DUT-side validation.
- **`tests.dhcp_relay.dhcp_relay_utils.check_dhcp_stress_status`:** Confirms the DHCP stress process health.
- **`tests.common.helpers.assertions.pytest_assert`:** Provides enhanced assertion messaging.
- **`tests.ptf_runner.ptf_runner`:** Executes the PTF-based DHCP stress workload.

## 7. Unspecified Items
- **Testbed YAML variables beyond `dut_dhcp_relay_data` contents:** Not specified.
- **Exact implementations of imported helper functions/fixtures:** Not specified in this file.
