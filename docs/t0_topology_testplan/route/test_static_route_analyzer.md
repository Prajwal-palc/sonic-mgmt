# Static Route Test Plan Analysis

## 1. Topology Type
- **Declared topology markers:** `pytestmark` specifies `topology('t0', 'm0', 'mx')`, meaning the suite is written for T0, mixed (M0), and MX topologies. The generated documentation is placed under the `t0` plan because the repository convention maps the `tests/route` tree to `docs/t0_topology_testplan/...`.
- **Dual ToR awareness:** Helper `is_dualtor(tbinfo)` checks `tbinfo["topo"]["name"]` for `"dualtor"`. Several flows (ARP/NDP cleanup, mux control, config reload handling) branch when the testbed is dual ToR, implying the cases are validated on both single ToR T0 and dual ToR T0/M0/MX variations.
- **Inference sources:** Use of `tbinfo`, `mux_cable_server_ip`, and mux simulator fixtures indicates dependence on testbed metadata and dual ToR emulation consistent with T0-style topologies that connect to servers through VLANs and PortChannels.

## 2. Overall Test Case Purpose
- **High-level goal:** Validate static route programming on SONiC DUTs for both IPv4 and IPv6, ensuring routes can be installed with single or multiple next hops, forward traffic correctly, survive configuration reloads, and are properly withdrawn.
- **Context within SONiC test framework:** Uses SONiC pytests to perform end-to-end forwarding checks via PTF, interacts with CONFIG_DB to install routes, and leverages route flow counters plus BGP advertisement verification to confirm control-plane redistribution. Dual ToR handling ensures active/standby mux states remain consistent.

## 3. Detailed Breakdown of Sub-testcases
### Helper & Support Functions
- **`is_dualtor(tbinfo)`**: Determines whether the topology is dual ToR; influences clean-up, mux handling, and config reload logic.
- **`add_ipaddr` / `del_ipaddr` / `clear_arp_ndp`**: Manage PTF host addressing and neighbor tables (ARP/NDP) to emulate downstream next hops and keep environment clean.
- **`generate_and_verify_traffic`**: Crafts IPv4/IPv6 TCP packets and validates egress via expected ports, using randomly selected upstream interface for ingress; core for data-plane verification.
- **`wait_all_bgp_up`**: Ensures BGP sessions recover after config reload before traffic validation continues.
- **`check_route_redistribution`**: Parses `show bgp` outputs to confirm static routes are or are not advertised to neighbors, depending on context.
- **`check_static_route`**: Reads kernel route table to verify programmed next hops.
- **`check_mux_status`**: Confirms mux cable state on dual ToR post reload.
- **`run_static_route_test`**: Master workflow executing add-route, traffic verification, redistribution check, optional config reload, and cleanup for both IPv4/IPv6 and ECMP variations. Provides shared logic for all test cases.
- **`get_nexthops`**: Derives next-hop IPs, devices, and interfaces from minigraph facts; handles backend VLAN filtering, dual ToR server IP selection, and supports requesting multiple hops or IPv6 addresses.

### Test Functions
1. **`test_static_route`**
   - **Intent:** Validates basic IPv4 static route installation with a single next hop. Runs `run_static_route_test` with prefix `1.1.1.0/24` and dynamically derived next-hop data.
   - **Checks:** Route presence in kernel, traffic forwarding, route advertisement, clean removal.
   - **Relevance:** Baseline functionality for static routing under normal conditions.

2. **`test_static_route_ecmp`** *(loganalyzer disabled)*
   - **Intent:** Exercises IPv4 static route with multiple next hops (`count=3`) to verify ECMP behavior and configuration persistence through reload.
   - **Checks:** Same as baseline plus `config reload` and mux role reassertion for dual ToR. Ensures ECMP survives reload and traffic still balanced (at least one packet forwarded) post reload.
   - **Relevance:** Validates resilience and state persistence for ECMP static routes.

3. **`test_static_route_ipv6`**
   - **Intent:** Tests single next-hop IPv6 static route (`2000:1::/64`).
   - **Checks:** IPv6 route programming, traffic forwarding, BGP redistribution, cleanup.
   - **Relevance:** Confirms IPv6 parity for static routing operations.

4. **`test_static_route_ecmp_ipv6`** *(loganalyzer disabled)*
   - **Intent:** Combines IPv6 static route with ECMP and config reload persistence.
   - **Checks:** Multi-next-hop IPv6 route installation, post-reload validation, mux state enforcement, traffic verification, advertisement.
   - **Relevance:** Ensures dual-stack support and robustness for static routes under complex scenarios.

## 4. Dependencies and Prerequisites
- **Fixtures:** `rand_selected_dut`, `rand_unselected_dut`, `ptfadapter`, `ptfhost`, `tbinfo`, `setup_standby_ports_on_rand_unselected_tor`, `toggle_all_simulator_ports_to_rand_selected_tor_m`, and `is_route_flow_counter_supported`. These supply DUT handles, PTF interfaces, topology metadata, mux preparation, and capability flags.
- **Topology requirements:** Availability of VLAN interfaces with multiple members; dual ToR scenarios require mux simulator access and standby port setup.
- **Services:** BGP sessions must be operational; CONFIG_DB access is required; route flow counters must be supported or gracefully skipped.
- **Prerequisite cleanup:** Ability to clear ARP/NDP tables and manage arp_responder on PTF host.

## 5. Key Inputs and Parameters
- **`tbinfo`**: Provides topology name/type and minigraph data used for topology checks and next-hop derivation.
- **`prefix_len`, `nexthop_addrs`, `nexthop_devs`, `nexthop_interfaces`**: Generated by `get_nexthops` to define route attributes and expected forwarding ports.
- **`is_route_flow_counter_supported`**: Determines whether to engage flow counter context manager for telemetry validation.
- **Static route prefixes**: `1.1.1.0/24`, `2.2.2.0/24`, `2000:1::/64`, `2000:2::/64` configured per test to distinguish scenarios.
- **Config reload flag (`config_reload_test`)**: Controls whether `run_static_route_test` performs configuration save/reload sequence.
- **Dual ToR flags**: Derived via `is_dualtor` and presence of `rand_unselected_dut`; trigger mux handling and double cleanup.

## 6. External Libraries and Modules
- **PyTest (`pytest`, markers, fixtures)**: Test framework for parametrization, assertions, and fixture injection.
- **Standard libraries (`json`, `ipaddress`, `time`, `logging`, `random`, `collections.defaultdict`)**: Used for data manipulation, timing, and logging.
- **Third-party libs (`natsort`, `six`)**: Sorting for interface names; text type compatibility.
- **PTF modules (`ptf.testutils`, `ptf.mask`, `ptf.packet`)**: Packet generation, masking, and verification for traffic testing.
- **SONiC test helpers**: Multiple utilities under `tests.common` (fixtures, mux controls, assertions, constants, config reload, flow counter context, VLAN helpers) providing DUT interaction, mux simulation, configuration management, and telemetry verification.
- **Ansible interaction via `ptfhost.shell/copy/template`**: Leverages Ansible-hosted commands to configure the PTF host's arp_responder and interface addresses.

## 7. Unspecified Items
- Exact hardware models, specific BGP neighbor identities, and route flow counter behavior beyond context manager usage are **Not specified** in this file.
