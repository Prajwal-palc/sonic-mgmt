# DHCP Relay Test Plan Analyzer

## 1. Topology Type
- **Topology**: T0 primary coverage with optional dual ToR (multi-homing) variants, also marked compatible with `m0` virtual switch setups.【F:tests/dhcp_relay/test_dhcp_relay.py†L23-L38】
- **Inference**: The `pytestmark` includes `pytest.mark.topology('t0', 'm0')`, and numerous fixtures reference dual ToR behavior (`DUAL_TOR_MODE`, `rand_unselected_dut`, `toggle_all_simulator_ports_to_rand_selected_tor_m`) indicating mixed single- and dual-ToR scenarios derived from the testbed metadata (`tbinfo`).【F:tests/dhcp_relay/test_dhcp_relay.py†L23-L199】

## 2. Overall Test Case Purpose
- **Goal**: Validate that SONiC DHCP relay agents operate correctly under standard, resilience, and dual-ToR conditions. The suite stresses packet forwarding, monitoring counters, ACL drops, link resiliency, service restarts, and support for different client behaviors (broadcast/unicast MAC, random source ports, source IP options).【F:tests/dhcp_relay/test_dhcp_relay.py†L115-L674】
- **Context**: These tests run within SONiC's PyTest-based automation, leveraging PTF hosts to emulate DHCP clients/servers and verifying relay functionality and monitoring (dhcpmon counters, ACL behavior) against SONiC networking stacks and orchestration utilities.【F:tests/dhcp_relay/test_dhcp_relay.py†L14-L674】

## 3. Detailed Breakdown of Sub-Testcases
### `test_interface_binding`
- **Intent**: Ensure DHCP relay processes bind to the expected VLAN and uplink interfaces on the DUT by inspecting the relay container socket list; triggers config reload if bindings are missing.【F:tests/dhcp_relay/test_dhcp_relay.py†L115-L127】
- **Importance**: Validates baseline service readiness before traffic tests, confirming relay agents listen on all required interfaces.

### `test_dhcp_relay_default`
- **Intent**: Execute the baseline DHCP relay functional test using PTF to generate DHCP exchanges, optionally capturing dhcpmon debug counters and validating expected uplink/downlink packet counts across single and dual ToR modes.【F:tests/dhcp_relay/test_dhcp_relay.py†L196-L301】
- **Importance**: Confirms end-to-end relay forwarding and monitoring accuracy under normal operation, forming the foundation for resilience scenarios.

### `test_dhcp_relay_with_source_port_ip_in_relay_enabled`
- **Intent**: Repeat the functional flow with the relay configured to supply source port IP (`-si` option) by patching device metadata, then validate packet delivery and counters.【F:tests/dhcp_relay/test_dhcp_relay.py†L304-L411】
- **Importance**: Ensures optional relay enhancements (source IP insertion) do not break packet flow or monitoring in either single or dual ToR deployments.

### `test_dhcp_relay_after_link_flap`
- **Intent**: Flap all uplinks before running the PTF test to verify relay resiliency and route recovery after transient connectivity loss.【F:tests/dhcp_relay/test_dhcp_relay.py†L414-L459】
- **Importance**: Validates relay robustness to link instability and confirms routing convergence prior to DHCP forwarding.

### `test_dhcp_relay_start_with_uplinks_down`
- **Intent**: Shut down uplinks, restart the relay service while links remain down, then bring links back to ensure the relay handles startup in degraded conditions and recovers DHCP functionality.【F:tests/dhcp_relay/test_dhcp_relay.py†L462-L518】
- **Importance**: Checks service resilience to restart conditions and ensures no latent failures when interfaces are unavailable during initialization.

### `test_dhcp_relay_unicast_mac`
- **Intent**: Run DHCP exchanges using a unicast destination MAC (router MAC or VLAN MAC in dual ToR) instead of broadcast to ensure relay processing accepts directed traffic.【F:tests/dhcp_relay/test_dhcp_relay.py†L521-L556】
- **Importance**: Verifies support for DHCP clients using unicast requests, important for certain network designs.

### `test_dhcp_relay_random_sport`
- **Intent**: Randomize the client UDP source port to emulate SNAT scenarios and confirm relay forwarding remains functional.【F:tests/dhcp_relay/test_dhcp_relay.py†L559-L593】
- **Importance**: Ensures relay logic does not depend on well-known client port 68 and can handle non-standard ports.

### `test_dhcp_relay_on_dualtor_standby`
- **Intent**: Target the dual ToR standby switch, sending DHCP server-to-client traffic through standby uplinks and validating dhcpmon counters to ensure traffic properly egresses client ports and active node counters remain zero.【F:tests/dhcp_relay/test_dhcp_relay.py†L595-L674】
- **Importance**: Confirms dual ToR redundancy, verifying standby handling of downlink broadcasts and correct counter accounting.

### Helper Functions & Fixtures
- **`ignore_expected_loganalyzer_exceptions`**: Autouse fixture to ignore known syslog noise during log analysis.【F:tests/dhcp_relay/test_dhcp_relay.py†L43-L54】
- **`check_interface_status`**: Helper verifying dhcrelay sockets are listening (used for readiness checks).【F:tests/dhcp_relay/test_dhcp_relay.py†L57-L63】
- **`enable_source_port_ip_in_relay`**: Fixture that patches `deployment_id` to enable the `-si` flag and ensures cleanup post-test.【F:tests/dhcp_relay/test_dhcp_relay.py†L65-L112】
- **`start_dhcp_monitor_debug_counter`**: Helper restarting `dhcpmon` in debug mode to capture counter logs.【F:tests/dhcp_relay/test_dhcp_relay.py†L130-L156】
- **`get_acl_count_by_mark` & `verify_acl_drop_on_standby_tor`**: Utilities and fixture for validating ACL drop counters on standby ToR during client traffic validation.【F:tests/dhcp_relay/test_dhcp_relay.py†L159-L193】

## 4. Dependencies and Prerequisites
- **Fixtures**: `duthosts`, `rand_one_dut_hostname`, `ptfhost`, `dut_dhcp_relay_data`, `testing_config`, `validate_dut_routes_exist`, `setup_standby_ports_on_rand_unselected_tor`, `rand_unselected_dut`, `toggle_all_simulator_ports_to_rand_selected_tor_m`, `tbinfo`, and optional log analyzer fixtures.【F:tests/dhcp_relay/test_dhcp_relay.py†L43-L674】
- **Topology Constraints**: Requires T0/M0 topologies with DHCP relay services configured, optional dual ToR environment for standby validations.【F:tests/dhcp_relay/test_dhcp_relay.py†L23-L674】
- **Service Requirements**: DHCP relay container, dhcpmon, ACL tables, and ability to reload configuration or restart services on the DUT.【F:tests/dhcp_relay/test_dhcp_relay.py†L90-L193】

## 5. Key Inputs and Parameters
- **`dut_dhcp_relay_data`**: Supplies per-VLAN relay configuration (client interfaces, uplinks, DHCP server IPs, loopback, MACs) used to parameterize PTF runs and counter expectations.【F:tests/dhcp_relay/test_dhcp_relay.py†L123-L290】
- **`testing_config`**: Provides current mode (`single`/`dual`) and active DUT host to adjust expectations and choose standby hosts.【F:tests/dhcp_relay/test_dhcp_relay.py†L204-L647】
- **Constants**: `BROADCAST_MAC`, `DEFAULT_DHCP_CLIENT_PORT`, `CLIENT_SENT_PACKET_COUNT`, and mode tags influence traffic templates and counter deltas.【F:tests/dhcp_relay/test_dhcp_relay.py†L34-L38】【F:tests/dhcp_relay/test_dhcp_relay.py†L186-L193】
- **Runtime Values**: Randomized client port for sport test, derived ACL marks, router MAC facts, and dhcpmon expectations per topology mode.【F:tests/dhcp_relay/test_dhcp_relay.py†L569-L592】【F:tests/dhcp_relay/test_dhcp_relay.py†L175-L193】【F:tests/dhcp_relay/test_dhcp_relay.py†L547-L552】

## 6. External Libraries and Modules
- **PyTest & Fixtures**: `pytest` provides test orchestration and fixture management.【F:tests/dhcp_relay/test_dhcp_relay.py†L1-L68】
- **SONiC Helpers**: Modules for DHCP counters, GCU utilities (checkpoint/rollback), configuration reload, process monitoring, routing validation, and log analysis extend test capabilities.【F:tests/dhcp_relay/test_dhcp_relay.py†L7-L21】【F:tests/dhcp_relay/test_dhcp_relay.py†L65-L193】
- **PTF Runner**: `tests.ptf_runner.ptf_runner` executes packet-based validation scenarios on the PTF host.【F:tests/dhcp_relay/test_dhcp_relay.py†L14-L648】
- **Standard Libraries**: `random`, `time`, `logging`, `re` support timing, logging, randomness, and regex for helper logic.【F:tests/dhcp_relay/test_dhcp_relay.py†L2-L5】【F:tests/dhcp_relay/test_dhcp_relay.py†L130-L193】

## 7. Unspecified Items
- **Testbed Inventory Details**: Exact values for `dut_dhcp_relay_data`, `testing_config`, or ACL marks depend on external inventory/fixtures and are not specified in this file.【F:tests/dhcp_relay/test_dhcp_relay.py†L123-L674】
- **PTF Test Implementation**: The underlying `ptftests` modules (`dhcp_relay_test`) are referenced but not shown here. *Not specified* in this file.【F:tests/dhcp_relay/test_dhcp_relay.py†L241-L648】
