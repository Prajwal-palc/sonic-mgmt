# DHCPv6 Relay Test Analyzer

## 1. Topology Type
- **Supported topologies:** `t0`, `m0`, `mx`, and `t0-2vlans` are declared via `pytestmark`, indicating the test is validated across ToR-based fanout environments and management-plane variants. The inclusion of both single ToR and DualToR behaviors is inferred from conditional logic checking `tbinfo['topo']['name']` for `dualtor` and from the use of fixtures like `toggle_all_simulator_ports_to_rand_selected_tor_m`.
- **Inference method:** The test introspects `tbinfo` and minigraph facts to determine uplink roles (`LeafRouter`, `MgmtLeafRouter`, `MgmtToRRouter`) and to gather VLAN/uplink membership. This reliance on minigraph roles and dual ToR simulators confirms the focus on T0-style topologies with optional dual-homing behavior.

## 2. Overall Test Case Purpose
- **High-level goal:** Validate SONiC's DHCPv6 relay agent across functional, counter, and resiliency dimensions. The tests ensure correct relay forwarding, accurate per-interface counters, robust behavior across link flaps or service restarts, and proper handling when VLANs lack DHCP server configuration.
- **Context within SONiC QA:** These tests align with SONiC's DHCP relay verification for ToR switches by leveraging PTF-host-driven traffic (via `ptf_runner`) and SONiC minigraph configuration. They mirror production workflows where relay agents must maintain accurate state despite topology changes, dual ToR mux behavior, and interface churn.

## 3. Detailed Breakdown of Sub-Testcases
### `test_interface_binding`
- **Intent:** Adds a VLAN without DHCPv6 servers, removes link-local addresses (LLA) from existing VLANs, restarts the relay service, and inspects socket bindings to ensure the relay only binds where servers are configured. Finally, it restores LLAs and confirms sockets return.
- **Logic & Checks:**
  - Uses helper `check_interface_status` to verify `dhcp6relay` sockets exist; reloads configuration if necessary.
  - Deletes LLAs for each VLAN (`duthost.shell_cmds`), restarts the DHCP service, and confirms only wildcard sockets exist (`*:*`), not per-VLAN sockets.
  - Re-adds LLAs and waits for sockets to reappear (`wait_until`).
  - Ensures the newly added VLAN (`Vlan4001`) without servers does not have a dedicated socket.
- **Relevance:** Confirms DHCPv6 relay binds only to VLANs with valid DHCP server configuration, preventing unintended listening on VLANs without servers.

### `test_dhcpv6_relay_counter`
- **Intent:** Validates DHCPv6 per-interface counters for various message types after stimulating traffic via the PTF host.
- **Logic & Checks:**
  - Initializes counters on client interfaces, VLANs, and loopbacks (for DualToR) through `init_counter`.
  - Executes PTF test `dhcpv6_counter_test.DHCPCounterTest` to generate traffic.
  - Uses `check_dhcpv6_relay_counter` to assert expected increments across RX/TX directions for each message type, accommodating dual ToR behavior.
- **Relevance:** Ensures monitoring and diagnostics remain accurate by verifying counter updates for all DHCPv6 message categories.

### `test_dhcp_relay_default`
- **Intent:** Verifies nominal DHCPv6 relay forwarding under standard conditions.
- **Logic & Checks:**
  - For each relay instance, runs PTF script `dhcpv6_relay_test.DHCPTest` using minigraph-derived parameters (client port, uplinks, server addresses, link-local).
- **Relevance:** Core validation that relay agent forwards DHCPv6 packets correctly when the network is stable.

### `test_dhcp_relay_after_link_flap`
- **Intent:** Tests relay resilience after temporarily bringing all uplinks down and back up.
- **Logic & Checks:**
  - Down/up each uplink interface, waits for BGP sessions via `wait_all_bgp_up`, then re-runs the standard DHCP relay PTF test.
- **Relevance:** Validates service continuity after transient link failures, ensuring the relay resumes forwarding once connectivity restores.

### `test_dhcp_relay_start_with_uplinks_down`
- **Intent:** Examines behavior when the relay service restarts while uplinks remain down.
- **Logic & Checks:**
  - Downs uplinks, restarts `dhcp_relay` service (with `reset-failed`), waits for startup, then restores uplinks and reruns relay validation.
- **Relevance:** Verifies robustness of relay initialization in adverse conditions and recovery of functionality.

### `TestDhcpv6RelayWithMultipleVlan.test_dhcp_relay_default`
- **Intent:** Ensures relay sets correct link-layer address when multiple VLANs are configured dynamically.
- **Logic & Checks:**
  - Class fixture restarts relay service after test completion.
  - Parameterized fixture `setup_multiple_vlans_and_teardown` provisions additional VLANs.
  - For each VLAN, ensures reachability via `ensure_client_reachability`, gathers VLAN-specific MAC/LLA, and executes PTF relay test expecting VLAN-specific link address usage.
- **Relevance:** Confirms relay adapts to VLAN configuration changes and applies per-VLAN link-local addresses correctly in relayed packets.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `duthosts`, `rand_one_dut_hostname`, `ptfhost`, `tbinfo` supply device context and topology data.
  - PTF host utilities (`copy_ptftests_directory`, `change_mac_addresses`) prepare PTF environment automatically via fixture imports.
  - Dual ToR utilities (`toggle_all_simulator_ports_to_rand_selected_tor_m`, `config_active_active_dualtor_active_standby`, `validate_active_active_dualtor_setup`, `active_active_ports`) manage mux simulator state when applicable.
  - `setup_multiple_vlans_and_teardown` dynamically creates VLANs for multi-VLAN testing.
  - `setup_and_teardown_no_servers_vlan` temporarily creates a VLAN with no DHCP servers for binding validation.
  - `validate_dut_routes_exist` (module fixture) ensures reachability to DHCP servers prior to traffic tests.
  - `testing_config` ensures DualToR subtype correctness.
- **Topology constraints:** Requires T0/M0/MX-style fabric with VLANs, DHCPv6 servers defined in minigraph, and optionally DualToR mux simulator support.

## 5. Key Inputs and Parameters
- **Minigraph-derived data:** VLAN interfaces, member ports, link-local addresses, DHCPv6 server IPs, loopback interfaces, MAC addresses, and PTF port indices from `mg_facts` drive PTF test parameters.
- **PTF runner parameters:** `client_port_index`, `leaf_port_indices`, `server_ip`, `relay_iface_ip`, `relay_iface_mac`, `relay_link_local`, `uplink_mac`, `loopback_ipv6`, and `is_dualtor` tailor the PTF traffic patterns.
- **Message type list:** `message_types` enumerates DHCPv6 packet categories for counter validation.
- **Service control commands:** `config_reload`, `systemctl reset-failed/restart dhcp_relay`, and raw socket inspection ensure environment readiness.

## 6. External Libraries and Modules
- **Standard libraries:** `ipaddress`, `random`, `time`, `logging` for IP operations, randomness, timing delays, and logging; `netaddr` for IP version checks.
- **PyTest/SONiC utilities:**
  - `pytest`, fixtures, and markers orchestrate test execution and topology scoping.
  - `ptf_runner` drives PTF-based traffic tests.
  - `tests.common` helpers (`config_reload`, `wait_critical_processes`, `wait_until`, `pytest_assert`) provide SONiC-specific orchestration.
  - Dual ToR helpers manage mux simulator state for dual-homed scenarios.
  - `restart_dhcp_service` restarts DHCP relay container cleanly.
  - Process utilities (`wait_critical_processes`) verify daemon health.

## 7. Unspecified Items
- **Source of DHCP server IPs beyond minigraph:** Not specified.
- **Exact PTF test implementations (`dhcpv6_relay_test.DHCPTest`, `dhcpv6_counter_test.DHCPCounterTest`):** Not specified within this file.

