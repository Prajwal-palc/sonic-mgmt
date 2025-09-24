# PortChannel Switching Test Analyzer

## 1. Topology Type
- **Required topology:** Dual DUTs with four inter-switch links and individual traffic generator connections (`D1D2:4`, `D1T1:1`, `D2T1:1`).【F:spytest/tests/switching/test_portchannel.py†L26-L59】
- **Inference:** The module-level fixture calls `st.ensure_min_topology` with the above topology string and then maps inter-DUT and test-generator interfaces, confirming a two-box topology with a traffic generator attached to each DUT.【F:spytest/tests/switching/test_portchannel.py†L26-L77】

## 2. Overall Test Case Purpose
- **High-level goal:** Validate SONiC LAG/PortChannel functionality covering Layer-2 forwarding, Layer-3 hashing, VLAN membership sequencing, membership churn, LLDP, and LACP graceful restart behavior across paired DUTs.【F:spytest/tests/switching/test_portchannel.py†L378-L939】
- **Context within SONiC/SpyTest:** The suite orchestrates DUT configuration, traffic generation, and verification through SpyTest helper APIs to ensure port-channel resiliency, protocol correctness, and management plane persistence features in a multi-DUT environment.【F:spytest/tests/switching/test_portchannel.py†L63-L375】【F:spytest/tests/switching/test_portchannel.py†L378-L939】

## 3. Detailed Breakdown of Sub-Testcases
### `test_ft_portchannel_behavior_with_tagged_traffic`
- Exercises twelve Layer-2 LAG scenarios: preventing PortChannel deletion while in a VLAN, ensuring member removal does not drop traffic, confirming hashing and redistribution when members leave/rejoin, validating LLDP across members, enforcing down state on admin shutdown or partner misconfiguration, and ensuring disabled LAGs block traffic.【F:spytest/tests/switching/test_portchannel.py†L378-L637】
- Uses traffic generator streams and interface counters to verify balanced forwarding, monitors LLDP neighbors, and validates administrative state transitions to catch regressions in L2 resiliency.【F:spytest/tests/switching/test_portchannel.py†L395-L637】

### `test_ft_untagged_traffic_on_portchannel`
- Sends untagged traffic bursts over the PortChannel to confirm hashing parity with regular access ports after converting the PortChannel membership to untagged mode during setup hooks.【F:spytest/tests/switching/test_portchannel.py†L102-L220】【F:spytest/tests/switching/test_portchannel.py†L605-L618】
- Ensures that VLAN-mode changes do not impact load-sharing, reinforcing PortChannel transparency for untagged traffic.【F:spytest/tests/switching/test_portchannel.py†L605-L618】

### `test_ft_lag_l3_hash_sip_dip_l4port`
- Configures IPv4 addresses on the PortChannel and connected interfaces, validates ARP learning/removal, programs static routes, and drives L3/TCP traffic with varying SIP/DIP/L4 ports to confirm hashing and lossless forwarding.【F:spytest/tests/switching/test_portchannel.py†L180-L229】【F:spytest/tests/switching/test_portchannel.py†L624-L752】
- Verifies control-plane reactions (ARP cleanup on shutdown) and data-plane distribution, ensuring L3 hashing and routing via PortChannels remain stable.【F:spytest/tests/switching/test_portchannel.py†L624-L752】

### `test_ft_member_state_after_interchanged_the_members_across_portchannels`
- Builds a second PortChannel, swaps members between LAGs, waits for LACP timers, and ensures member states reflect the mismatch until restored, validating detection of asymmetric partner configurations.【F:spytest/tests/switching/test_portchannel.py†L755-L844】
- Reinforces that SONiC correctly reports member states and recovers when memberships are corrected.【F:spytest/tests/switching/test_portchannel.py†L763-L844】

### `test_ft_portchannel_with_vlan_variations`
- Compares two configuration orders: adding VLAN membership before bringing the PortChannel up versus activating first and then tagging, confirming both sequences keep the LAG operational.【F:spytest/tests/switching/test_portchannel.py†L847-L886】
- Validates VLAN configuration resilience and cleans up temporary resources to restore the baseline topology.【F:spytest/tests/switching/test_portchannel.py†L847-L886】

### `test_ft_lacp_graceful_restart_with_cold_boot`
- After preparing two PortChannels, saves config, clears logs, and reboots one DUT to ensure LACP graceful restart logs are generated and both LAGs return to `Up` state without manual intervention.【F:spytest/tests/switching/test_portchannel.py†L889-L913】
- Demonstrates control-plane persistence across cold reboots for LACP.【F:spytest/tests/switching/test_portchannel.py†L889-L913】

### `test_ft_lacp_graceful_restart_with_save_reload`
- Similar to the cold-boot case but triggers `config save`/`config reload` to validate graceful restart signaling and PortChannel recovery after a configuration reload workflow.【F:spytest/tests/switching/test_portchannel.py†L916-L939】
- Ensures graceful restart works for non-reboot maintenance actions.【F:spytest/tests/switching/test_portchannel.py†L916-L939】

### Helper Functions and Hooks
- Module and function fixtures provision baseline PortChannels, VLANs, and traffic-generator interfaces, and execute targeted pre/post cleanup for each scenario.【F:spytest/tests/switching/test_portchannel.py†L26-L220】
- Utility helpers wrap repeated operations (VLAN membership changes, counter collection, LLDP checks, REST verification) to parallelize execution across DUTs and enforce consistent validation criteria.【F:spytest/tests/switching/test_portchannel.py†L139-L375】

## 4. Dependencies and Prerequisites
- **Fixtures:** `portchannel_module_hooks` (module-scope) sets up topology, PortChannels, VLANs, and TG streams; `portchannel_func_hooks` (function-scope) adjusts configuration per test and restores state afterward.【F:spytest/tests/switching/test_portchannel.py†L26-L220】
- **Topology constraints:** Two DUTs with at least four interlinks and traffic-generator connectivity per DUT are mandatory to satisfy `st.ensure_min_topology` and to exercise hashing across multiple members.【F:spytest/tests/switching/test_portchannel.py†L37-L58】
- **Parallel execution utilities:** `exec_all`, `exec_parallel`, and `ensure_no_exception` are required to coordinate simultaneous configuration/verification on both DUTs.【F:spytest/tests/switching/test_portchannel.py†L18-L19】【F:spytest/tests/switching/test_portchannel.py†L59-L375】

## 5. Key Inputs and Parameters
- Random VLAN IDs (`data.vlan`, `data.vid`, `data.vlan_id`) and PortChannel names (`PortChannel7`, `PortChannel8`) define L2 isolation and aggregated interfaces under test.【F:spytest/tests/switching/test_portchannel.py†L31-L35】
- Interface member lists (`data.members_dut1`, `data.members_dut2`) represent inter-DUT links used for LAG membership changes and status checks.【F:spytest/tests/switching/test_portchannel.py†L56-L58】
- Traffic profiles leverage configurable IP addresses, TCP ports, and counters (`data.ip41`, `data.ip42`, `data.tcp_src_port_count`, etc.) to stress hashing logic and verify packet distribution.【F:spytest/tests/switching/test_portchannel.py†L38-L55】【F:spytest/tests/switching/test_portchannel.py†L395-L752】
- Graceful restart flow toggles `data.graceful_restart_config` to avoid repeated setup and reuses stored REST URL for verification when needed.【F:spytest/tests/switching/test_portchannel.py†L51-L59】【F:spytest/tests/switching/test_portchannel.py†L889-L939】

## 6. External Libraries and Modules
- **`spytest` core (`st`, `tgapi`, `SpyTestDict`):** logging, topology discovery, traffic-generator control, and shared state management.【F:spytest/tests/switching/test_portchannel.py†L4-L5】
- **Switching/system APIs (`portchannel_obj`, `vlan_obj`, `intf_obj`, `port_obj`, `rest_obj`):** configure PortChannels, VLANs, interfaces, ports, and REST queries.【F:spytest/tests/switching/test_portchannel.py†L6-L16】
- **Routing/ARP utilities (`ip_obj`, `arp_obj`):** manage IP addressing, routing, and ARP validation for L3 hashing scenarios.【F:spytest/tests/switching/test_portchannel.py†L13-L14】【F:spytest/tests/switching/test_portchannel.py†L624-L752】
- **System helpers (`basic_obj`, `slog`, `lldp_obj`):** fetch MAC/IP/hostname data, parse syslog for graceful restart, and read LLDP neighbors.【F:spytest/tests/switching/test_portchannel.py†L9-L12】【F:spytest/tests/switching/test_portchannel.py†L478-L513】【F:spytest/tests/switching/test_portchannel.py†L889-L939】
- **Utility framework (`ExecAllFunc`, `exec_all`, `exec_parallel`, `poll_wait`, `random_vlan_list`):** provide asynchronous execution, polling, and random data generation used extensively across setup and validation.【F:spytest/tests/switching/test_portchannel.py†L18-L20】【F:spytest/tests/switching/test_portchannel.py†L59-L375】

## 7. Unspecified Items
- Testbed inventory filenames, specific hardware SKUs, and software images are not described in this file. **Not specified.**
- External configuration data sources (e.g., `group_vars` values) beyond the locally generated parameters are **Not specified.**
