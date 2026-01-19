# `tests/ecmp/test_fgnhg.py` – Test Case Analysis

## 1. Topology Type
- **Topology:** `t0`.
- **Inference:** The module-level `pytestmark` includes `pytest.mark.topology('t0')`, explicitly constraining execution to the T0 leaf-spine topology that provides server-facing VLANs and T1 uplinks.【F:tests/ecmp/test_fgnhg.py†L33-L37】

## 2. Overall Test Case Purpose
- **Goal:** Validate SONiC's fine-grained ECMP (FG-NHG) implementation across both IPv4 and IPv6 traffic on Mellanox ASICs.
- **Scope:** The suite programs FG-NHG groups, neighbors, and routes, then exercises control-plane transitions (link flaps, next-hop withdrawals/additions, bank isolation, and FG ↔ regular ECMP transitions) while verifying data-plane hashing and resilience using PTF tests. This ensures the orchestrator maintains bucket distribution, handles failures gracefully, and keeps other FG-prefixed routes unaffected.
- **Framework Context:** Runs within the SONiC PyTest infrastructure using DUT/PTF fixtures, sonic-cfggen for config injection, and ptf_runner to drive traffic validation from the PTF host.

## 3. Detailed Breakdown of Sub-Testcases and Helpers
### `test_fg_ecmp`
- **Intent:** End-to-end validation of FG-NHG for both IPv4 and IPv6 prefixes.
- **Flow:**
  1. Calls `setup_test_config` to select VLAN member ports, build FG-NHG config, start ARP responder, and prime the PTF host with hashing expectations.【F:tests/ecmp/test_fgnhg.py†L102-L158】【F:tests/ecmp/test_fgnhg.py†L166-L194】
  2. Invokes `validate_packet_flow_without_neighbor_resolution` to ensure traffic can trigger on-demand neighbor resolution before static entries exist.【F:tests/ecmp/test_fgnhg.py†L221-L248】
  3. Programs neighbor entries via `setup_neighbors` and executes `fg_ecmp` to exercise hashing redistribution across down/up events, next-hop withdrawals, and bank failovers.【F:tests/ecmp/test_fgnhg.py†L64-L99】【F:tests/ecmp/test_fgnhg.py†L281-L392】
  4. Runs `fg_ecmp_to_regular_ecmp_transitions` to move prefixes between FG-NHG and traditional ECMP, ensuring unaffected prefixes retain behavior.【F:tests/ecmp/test_fgnhg.py†L402-L478】
  5. Repeats the full workflow for IPv6, demonstrating parity across address families.【F:tests/ecmp/test_fgnhg.py†L496-L516】
- **Relevance:** Confirms FG-NHG resiliency and interoperability for dual-stack deployments on T0 with Mellanox ASICs.

### Helper Functions
- **`configure_interfaces` / `setup_test_config`:** Selects VLAN member interfaces, creates VLAN IPs, partitions ports into FG banks, and orchestrates end-to-end setup (FG-NHG config, ARP responder, PTF parameters). Critical for reproducible topology-specific preparation.【F:tests/ecmp/test_fgnhg.py†L41-L119】【F:tests/ecmp/test_fgnhg.py†L166-L194】
- **`generate_fgnhg_config`, `setup_neighbors`, `setup_arpresponder`:** Program control-plane state (FG-NHG tables, neighbor entries) and emulate remote hosts on the PTF host. Enable the DUT to forward traffic under defined next-hop distributions.【F:tests/ecmp/test_fgnhg.py†L70-L139】
- **`partial_ptf_runner`:** Wrapper to invoke `fg_ecmp_test.FgEcmpTest` PTF cases with dynamic parameters, supporting different phases such as flow creation, hash validation, and next-hop transitions.【F:tests/ecmp/test_fgnhg.py†L199-L219】
- **`fg_ecmp`:** Core traffic validation routine. Exercises link shutdown/startup, next-hop withdrawals/additions, and route flapping while verifying flow redistribution and monitoring orchestrator health.【F:tests/ecmp/test_fgnhg.py†L281-L392】
- **`fg_ecmp_to_regular_ecmp_transitions`:** Tests migration between FG-NHG and traditional ECMP using port-channel neighbors, ensuring flows redistribute correctly and that other FG prefixes are untouched.【F:tests/ecmp/test_fgnhg.py†L402-L478】
- **`validate_packet_flow_without_neighbor_resolution`, `setup_static_neighbor_entry`, `link_startup`:** Ensure neighbor resolution dynamics and link recovery behavior align with FG expectations.【F:tests/ecmp/test_fgnhg.py†L221-L279】
- **`configure_switch_vxlan_cfg`, `cleanup`:** Optional VXLAN port override and DUT reset to maintain clean state between runs.【F:tests/ecmp/test_fgnhg.py†L196-L218】【F:tests/ecmp/test_fgnhg.py†L482-L494】
- **`common_setup_teardown` fixture:** Gathers minigraph/config facts, router MAC, and net port mappings, optionally configures VXLAN hashing, and triggers cleanup afterwards. Supplies shared context to the test.【F:tests/ecmp/test_fgnhg.py†L456-L494】

## 4. Dependencies and Prerequisites
- **Fixtures:** `tbinfo`, `duthosts`, `rand_one_dut_hostname`, and `ptfhost` (PyTest/Ansible integrations) underpin `common_setup_teardown`. Implicit fixtures from `ptfhost_utils` (e.g., `copy_ptftests_directory`) prepare the PTF environment.【F:tests/ecmp/test_fgnhg.py†L15-L18】【F:tests/ecmp/test_fgnhg.py†L456-L494】
- **Topology Constraints:** Requires a T0 testbed with at least eight VLAN member ports to populate FG banks and supporting port-channels for regular ECMP comparison.【F:tests/ecmp/test_fgnhg.py†L41-L96】【F:tests/ecmp/test_fgnhg.py†L436-L470】
- **Platform:** Marked for Mellanox ASICs; assumes `orchagent`, `sonic-cfggen`, and vtysh are available on the DUT.【F:tests/ecmp/test_fgnhg.py†L33-L37】【F:tests/ecmp/test_fgnhg.py†L205-L215】
- **PTF Host:** Needs supervisor-managed `arp_responder`, PTF test directory, and ability to run `fg_ecmp_test.FgEcmpTest` suites.【F:tests/ecmp/test_fgnhg.py†L103-L158】【F:tests/ecmp/test_fgnhg.py†L199-L219】

## 5. Key Inputs and Parameters
- **Constants:** `NUM_NHs`, VLAN IDs/IPs, prefix lists, VXLAN port, flow count, and hashing flags govern FG-NHG sizing, address families, and traffic expectations.【F:tests/ecmp/test_fgnhg.py†L20-L31】
- **Runtime Facts:** `cfg_facts` and `mg_facts` provide VLAN membership, port indices, port-channels, and router MAC information used to map DUT ports to PTF interfaces.【F:tests/ecmp/test_fgnhg.py†L41-L99】【F:tests/ecmp/test_fgnhg.py†L456-L470】
- **PTF Parameters:** `partial_ptf_runner` passes `dst_ip`, expected flow distributions, and bank adjustments to the PTF tests, enabling precise validation scenarios.【F:tests/ecmp/test_fgnhg.py†L199-L219】【F:tests/ecmp/test_fgnhg.py†L321-L392】

## 6. External Libraries and Modules
- **Standard Libraries:** `time`, `logging`, `ipaddress`, `json`, `collections.defaultdict`, and `six` support timing, logging, address manipulation, data serialization, and compatibility utilities.【F:tests/ecmp/test_fgnhg.py†L3-L14】
- **PyTest & SONiC Helpers:**
  - `pytest` for fixtures, parametrization, and assertions.【F:tests/ecmp/test_fgnhg.py†L1-L18】
  - `ptf_runner` to execute PTF-based dataplane tests from the SONiC test framework.【F:tests/ecmp/test_fgnhg.py†L10-L18】
  - `config_reload`, `pytest_assert`, and `DEFAULT_NAMESPACE` provide DUT reset, assertion helpers, and namespace selection for vtysh commands.【F:tests/ecmp/test_fgnhg.py†L11-L18】
  - `ptfhost_utils` fixtures manage PTF host preparation (copying tests, changing MACs, cleaning IPs, provisioning ARP responder).【F:tests/ecmp/test_fgnhg.py†L15-L18】

## 7. Unspecified Items
- Any additional inventory variables, CLI options, or environment overrides beyond those noted above are **Not specified** in this file.
