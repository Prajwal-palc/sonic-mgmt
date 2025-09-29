# ACL Outer VLAN ID Test Analysis

## 1. Topology Type
- **Topology:** `t0`.
- **Evidence & Reasoning:** The module sets `pytestmark = [pytest.mark.topology('t0'), ...]`, explicitly constraining execution to T0 topologies. The tests also rely on T0 constructs such as `UPSTREAM_NEIGHBOR_MAP[tbinfo["topo"]["type"]]` to derive uplink neighbors for egress validation, reinforcing the requirement for a T0 layout that includes upstream fanout neighbors and both server- and uplink-facing VLAN members.【F:tests/acl/test_acl_outer_vlan.py†L24-L27】【F:tests/acl/test_acl_outer_vlan.py†L664-L700】

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate that ACL rules matching on an *outer VLAN ID* behave correctly for both ingress and egress traffic flows across tagged, untagged, and dual-member (combined) interfaces in SONiC.
- **Context:** Within the SONiC testing framework, ACL functionality is critical for enforcing network policy. This file focuses on verifying that QinQ and single-tag traffic is properly matched by ACL entries that target the *outer* VLAN tag, ensuring correct action (forward or drop) and counter updates on T0 testbeds. It covers both ingress tables (packets arriving on switch-facing interfaces) and egress tables (packets leaving toward access ports), including interoperability with port-channel members and ARP population workflows.【F:tests/acl/test_acl_outer_vlan.py†L1-L11】【F:tests/acl/test_acl_outer_vlan.py†L302-L389】【F:tests/acl/test_acl_outer_vlan.py†L501-L724】

## 3. Detailed Breakdown of Sub-Testcases
### Shared Infrastructure
- **Base Class `AclVlanOuterTest_Base`:** Supplies ACL table/rule lifecycle helpers, packet crafting utilities, and a `_do_verification` routine that drives traffic, checks ACL counters, and abstracts scenario-specific configuration. Each concrete test class implements `setup_cfg`, `pre_running_hook`, and `post_running_hook` to tailor ingress or egress behavior.【F:tests/acl/test_acl_outer_vlan.py†L220-L474】 This foundation ensures all subtests consistently create ACL tables/rules, send packets, and verify both data-plane disposition and counter increments.

### Ingress Test Class `TestAclVlanOuter_Ingress`
Each ingress test sets up an ACL table in the ingress stage, generates QinQ packets where appropriate, and asserts ACL counters increment while packets are forwarded or dropped as expected.
- **`test_tagged_forwarded`**: Verifies that traffic entering on a tagged port-channel member (outer VLAN 100) is forwarded when the ACL rule action is `FORWARD`. Ensures ACL tables correctly match on outer VLAN ID without altering expected delivery to untagged receivers.【F:tests/acl/test_acl_outer_vlan.py†L528-L544】【F:tests/acl/test_acl_outer_vlan.py†L586-L616】
- **`test_tagged_dropped`**: Mirrors the above but programs the ACL to `DROP`, confirming that tagged ingress traffic matching the outer VLAN is suppressed and counters increment for drops.【F:tests/acl/test_acl_outer_vlan.py†L545-L559】【F:tests/acl/test_acl_outer_vlan.py†L586-L616】
- **`test_untagged_forwarded`**: Targets traffic arriving on an access port (outer VLAN 200) while being forwarded out a tagged member, ensuring ACL rules applied to untagged ingress interfaces honor the `FORWARD` action.【F:tests/acl/test_acl_outer_vlan.py†L560-L568】【F:tests/acl/test_acl_outer_vlan.py†L586-L616】
- **`test_untagged_dropped`**: Confirms ACL drops on untagged ingress flows when configured with `DROP` action.【F:tests/acl/test_acl_outer_vlan.py†L569-L577】【F:tests/acl/test_acl_outer_vlan.py†L586-L616】
- **`test_combined_tagged_forwarded`**: Uses a port that belongs to two VLANs (combined mode) and verifies forwarding when ACL matches the outer tag on such multi-VLAN membership.【F:tests/acl/test_acl_outer_vlan.py†L578-L587】【F:tests/acl/test_acl_outer_vlan.py†L602-L634】
- **`test_combined_tagged_dropped`**: Ensures combined tagged members experience enforced drops when ACL action is `DROP`, validating rule precedence in multi-VLAN scenarios.【F:tests/acl/test_acl_outer_vlan.py†L588-L597】【F:tests/acl/test_acl_outer_vlan.py†L602-L634】
- **`test_combined_untagged_forwarded`**: Validates forwarding for combined-mode untagged ports (interface associated with multiple VLANs but egressing untagged) when ACL allows traffic.【F:tests/acl/test_acl_outer_vlan.py†L598-L607】【F:tests/acl/test_acl_outer_vlan.py†L602-L634】
- **`test_combined_untagged_dropped`**: Confirms drop enforcement on combined-mode untagged ingress members.【F:tests/acl/test_acl_outer_vlan.py†L608-L617】【F:tests/acl/test_acl_outer_vlan.py†L602-L634】
  - **Why These Matter:** Together these ingress scenarios demonstrate ACL handling across diverse VLAN tagging modes, ensuring policy consistency regardless of port membership or QinQ encapsulation, which is vital for mixed access/uplink designs in T0 fabrics.

### Egress Test Class `TestAclVlanOuter_Egress`
Egress tests focus on packets leaving the DUT toward access/aggregation ports, leveraging ARP responder support to populate neighbor entries and testing ACL enforcement post-routing.
- **`test_tagged_forwarded` / `test_tagged_dropped`**: Validate that egress ACLs applied to tagged VLAN members (outer VLAN 100) correctly forward or drop routed traffic, with ARP-resolved destinations and proper MAC learning on the fanout.【F:tests/acl/test_acl_outer_vlan.py†L501-L724】【F:tests/acl/test_acl_outer_vlan.py†L528-L559】
- **`test_untagged_forwarded` / `test_untagged_dropped`**: Ensure untagged egress members (outer VLAN 200) obey ACL actions when packets are routed from port-channel ingress to access egress.【F:tests/acl/test_acl_outer_vlan.py†L501-L724】【F:tests/acl/test_acl_outer_vlan.py†L560-L577】
- **`test_combined_tagged_forwarded` / `test_combined_tagged_dropped`**: Confirm ACL behavior for egress ports that are tagged members of multiple VLANs, demonstrating correct policy enforcement in complex membership configurations.【F:tests/acl/test_acl_outer_vlan.py†L501-L724】【F:tests/acl/test_acl_outer_vlan.py†L578-L597】
- **`test_combined_untagged_forwarded` / `test_combined_untagged_dropped`**: Validate that untagged combined members adhere to ACL actions, covering the final permutation of VLAN membership on egress.【F:tests/acl/test_acl_outer_vlan.py†L501-L724】【F:tests/acl/test_acl_outer_vlan.py†L598-L617】
  - **Why These Matter:** Egress ACL support differs across ASICs and requires ARP resolution and MAC learning. These tests ensure that SONiC can enforce policies on outgoing traffic regardless of VLAN tagging while tracking ACL counters, critical for security and compliance validation on T0 TOR switches.

### Helper Fixtures & Functions
- **`vlan_setup_info` & `setup_vlan`**: Provision VLANs 100/200, configure port-channel membership, assign IP addresses, and prepare PTF lag members for traffic generation. This scaffolding enables the various tagging scenarios tested later.【F:tests/acl/test_acl_outer_vlan.py†L89-L210】
- **`vlan_setup_teardown`**: Applies setup/teardown sequences, including removing default VLAN memberships, configuring DUT/PTF LAGs, and restoring state via `config_reload` post-tests.【F:tests/acl/test_acl_outer_vlan.py†L211-L271】
- **`craft_packet`, `send_and_verify_traffic`, `get_acl_counter`, `check_rule_counters`, `check_arp_status`**: Provide reusable utilities for packet crafting (including QinQ), traffic validation, ACL counter retrieval, and ARP checks, ensuring deterministic verification flows.【F:tests/acl/test_acl_outer_vlan.py†L302-L363】【F:tests/acl/test_acl_outer_vlan.py†L272-L301】【F:tests/acl/test_acl_outer_vlan.py†L364-L421】
- **`skip_sonic_leaf_fanout` fixture**: Skips execution when the fanout is an incompatible SONiC version/platform lacking QinQ or VLAN handling support, preventing false failures.【F:tests/acl/test_acl_outer_vlan.py†L618-L650】

## 4. Dependencies and Prerequisites
- **Fixtures:** `rand_selected_dut`, `ptfadapter`, `ptfhost`, `tbinfo`, `fanouthosts`, `toggle_all_simulator_ports_to_rand_selected_tor_m`, and autouse fixtures for VLAN setup and ACL cleanup. These fixtures supply device handles, topology metadata, mux control, and ensure exclusive ACL table availability.【F:tests/acl/test_acl_outer_vlan.py†L52-L149】【F:tests/acl/test_acl_outer_vlan.py†L211-L271】【F:tests/acl/test_acl_outer_vlan.py†L618-L724】
- **Topology Constraints:** Requires at least four VLAN member ports (two for LAG, two access) and upstream neighbors for routed egress, derived from minigraph facts and `UPSTREAM_NEIGHBOR_MAP`. QinQ capability on fanout is also needed unless skipped.【F:tests/acl/test_acl_outer_vlan.py†L103-L174】【F:tests/acl/test_acl_outer_vlan.py†L618-L724】
- **Environmental Setup:** Removal of default `DATAACL` table to free TCAM, creation of temporary ACL tables, and ARP responder service on PTF host for egress flows.【F:tests/acl/test_acl_outer_vlan.py†L56-L149】【F:tests/acl/test_acl_outer_vlan.py†L501-L566】

## 5. Key Inputs and Parameters
- **Constants:** VLAN IDs (`100`, `200`), ACL table naming template (`DATAACL_{stage}_{ip_version}`), action strings (`FORWARD`, `DROP`), tagging mode identifiers, and QinQ flag drive packet generation and ACL configuration.【F:tests/acl/test_acl_outer_vlan.py†L28-L53】
- **Templates & Files:** `acltb_test_rules_outer_vlan.j2` and `acl_rules_del.json` define ACL rule payloads, while ARP responder configuration is generated dynamically for PTF deployment.【F:tests/acl/test_acl_outer_vlan.py†L128-L149】【F:tests/acl/test_acl_outer_vlan.py†L557-L602】
- **`ip_version` Fixture:** Parameterizes tests over IPv4 and IPv6 for ingress (egress limited to IPv4), influencing packet crafting and ACL table types (`L3` vs `L3V6`).【F:tests/acl/test_acl_outer_vlan.py†L46-L76】【F:tests/acl/test_acl_outer_vlan.py†L501-L566】
- **Topology Metadata:** `tbinfo` and minigraph facts inform VLAN membership, port-channel composition, and neighbor port selection for injecting/routing traffic.【F:tests/acl/test_acl_outer_vlan.py†L103-L210】【F:tests/acl/test_acl_outer_vlan.py†L664-L724】

## 6. External Libraries and Modules
- **PyTest (`pytest`)**: Provides fixture management, parametrization, and skip/assert helpers. Marks define topology and custom categories (`po2vlan`).【F:tests/acl/test_acl_outer_vlan.py†L1-L77】【F:tests/acl/test_acl_outer_vlan.py†L528-L617】
- **PTF Utilities (`ptf.testutils`, `ptf.mask`)**: Used to craft QinQ/TCP packets, send/verify traffic, and mask non-deterministic fields in expected packets.【F:tests/acl/test_acl_outer_vlan.py†L9-L11】【F:tests/acl/test_acl_outer_vlan.py†L302-L360】
- **Scapy (`Ether`, `IP`)**: Enables packet field manipulation when masking expected packets.【F:tests/acl/test_acl_outer_vlan.py†L11-L12】【F:tests/acl/test_acl_outer_vlan.py†L341-L360】
- **SONiC Test Utilities:** Various helpers from `tests.common` for waiting, config reloads, assertions, mux control, topology mapping, and log analysis (e.g., `LogAnalyzer` for ACL creation/removal validation). These modules integrate SONiC-specific control plane and telemetry operations required for the ACL lifecycle.【F:tests/acl/test_acl_outer_vlan.py†L13-L25】【F:tests/acl/test_acl_outer_vlan.py†L302-L474】
- **Standard Libraries (`os`, `time`, `json`, `logging`, `abc`)**: Handle file paths, timing, JSON templating, logging, and abstract base class definitions supporting the test structure.【F:tests/acl/test_acl_outer_vlan.py†L5-L23】【F:tests/acl/test_acl_outer_vlan.py†L302-L474】

## 7. Unspecified Items
- **`default_routes_itfs` Fixture Implementation:** Defined but left empty; its exact role or return value is not specified in this file.【F:tests/acl/test_acl_outer_vlan.py†L78-L86】
- **External Data Sources:** Specific contents of `acltb_test_rules_outer_vlan.j2`, `acl_rules_del.json`, and `UPSTREAM_NEIGHBOR_MAP` entries are referenced but not detailed here. Mark as not specified.
- **Testbed Variables Beyond Minigraph Facts:** Any additional parameters from `testbed.yaml` or inventory (beyond those inferred via `tbinfo` and minigraph) are not specified in the file.
