# VRF Attribute Test Plan Analyzer

## 1. Topology Type
- **Topology:** `t0` (leaf-spine fanout with VLANs and routed uplinks).
- **Inference:** The module-level `pytestmark` pins the suite to the `t0` topology, and helpers from `test_vrf` rely on T0-specific configuration facts such as VLAN membership and VRF interface indices populated during the shared VRF setup fixture.【F:tests/vrf/test_vrf_attr.py†L18-L90】【F:tests/vrf/test_vrf.py†L503-L526】

## 2. Overall Test Case Purpose
This file validates that configurable VRF attributes on a SONiC DUT behave as expected for different traffic profiles. The scenarios cover router MAC overrides, TTL actions, IP option handling, and per-protocol forwarding state. Each test class programs the DUT with an attribute-specific configuration, reuses shared VRF topology data, and drives traffic via PTF to ensure forwarding and drop policies match expectations. The coverage complements the broader SONiC VRF regression (in `test_vrf.py`) by focusing on attribute-specific enforcement once the base VRF plumbing is established.【F:tests/vrf/test_vrf_attr.py†L25-L258】【F:tests/vrf/test_vrf.py†L503-L610】

## 3. Detailed Breakdown of Sub-Testcases
### `TestVrfAttrSrcMac`
- **Fixture `setup_vrf_attr_src_mac`:** Overrides `Vrf1`'s router MAC via a rendered Jinja template, generates VRF neighbor info for PTF, and restores the default MAC after tests.【F:tests/vrf/test_vrf_attr.py†L28-L53】 This ensures subsequent traffic checks use the modified MAC.
- **`test_vrf_src_mac_cfg`:** Queries `CONFIG_DB` to confirm the `src_mac` field for `Vrf1` matches the programmed override, ensuring configuration persistence.【F:tests/vrf/test_vrf_attr.py†L54-L59】
- **`test_vrf1_neigh_with_default_router_mac`:** Uses the partial PTF runner without overriding MACs to ensure packets tagged with the previous MAC are dropped, demonstrating enforcement of the new MAC on VRF1 interfaces.【F:tests/vrf/test_vrf_attr.py†L61-L68】
- **`test_vrf1_neigh_with_new_router_mac`:** Invokes the full `ptf_runner` to send traffic using the overridden MAC and expects forwarding, validating acceptance of the new MAC mapping.【F:tests/vrf/test_vrf_attr.py†L70-L83】
- **`test_vrf2_neigh_with_default_router_mac`:** Confirms that VRF2 still accepts the default MAC, ensuring attribute changes remain scoped to the targeted VRF.【F:tests/vrf/test_vrf_attr.py†L85-L91】

### `TestVrfAttrTTL`
- **Fixture `setup_vrf_attr_ttl`:** Loads a configuration that applies TTL-based actions and restores baseline state afterward.【F:tests/vrf/test_vrf_attr.py†L95-L113】
- **`test_vrf1_drop_pkts_with_ttl_1`:** Sends TTL=1 packets into VRF1 expecting drops per policy, verifying ingress TTL policing.【F:tests/vrf/test_vrf_attr.py†L114-L122】
- **`test_vrf1_fwd_pkts_with_ttl_2`:** Confirms packets with TTL=2 are forwarded, ensuring only low-TTL traffic is filtered.【F:tests/vrf/test_vrf_attr.py†L124-L131】
- **`test_vrf2_fwd_pkts_with_ttl_1`:** Validates that TTL enforcement is limited to VRF1 by confirming VRF2 forwards TTL=1 packets.【F:tests/vrf/test_vrf_attr.py†L133-L140】

### `TestVrfAttrIpAction`
- **Fixture `setup_vrf_attr_ip_opt_action`:** Applies ACL-like actions targeting IP options and prepares neighbor files for both VRFs.【F:tests/vrf/test_vrf_attr.py†L143-L162】
- **`test_vrf1_drop_pkts_with_ip_opt`:** Ensures VRF1 drops IPv4 packets containing a Router Alert option, demonstrating attribute-driven filtering.【F:tests/vrf/test_vrf_attr.py†L163-L173】
- **`test_vrf1_fwd_pkts_without_ip_opt`:** Confirms normal IPv4 traffic without options still forwards, proving selectivity of the rule.【F:tests/vrf/test_vrf_attr.py†L175-L184】
- **`test_vrf2_fwd_pkts_with_ip_opt`:** Shows VRF2 forwards packets even with options, confirming the configuration is scoped to VRF1.【F:tests/vrf/test_vrf_attr.py†L186-L195】

### `TestVrfAttrIpState`
- **Fixture `setup_vrf_attr_ip_state`:** Programs IP protocol enable/disable state per VRF and resets after the class finishes.【F:tests/vrf/test_vrf_attr.py†L198-L217】
- **`test_vrf1_drop_v4`:** Verifies IPv4 forwarding is disabled on VRF1 by expecting drops.【F:tests/vrf/test_vrf_attr.py†L218-L227】
- **`test_vrf1_forward_v6`:** Confirms IPv6 remains enabled on VRF1, indicating selective protocol disablement.【F:tests/vrf/test_vrf_attr.py†L229-L237】
- **`test_vrf2_forward_v4`:** Checks VRF2 forwards IPv4, showing the disable action is scoped to VRF1.【F:tests/vrf/test_vrf_attr.py†L239-L247】
- **`test_vrf2_drop_v6`:** Ensures IPv6 is disabled on VRF2, completing coverage of both VRFs’ protocol states.【F:tests/vrf/test_vrf_attr.py†L249-L257】

### Helper Infrastructure
The file relies on reusable fixtures (e.g., `partial_ptf_runner`, `gen_vrf_neigh_file`, `g_vars`, `PTF_TEST_PORT_MAP`) defined in `test_vrf.py` to supply VRF-aware port mappings, topology facts, and traffic-generation helpers that align PTF ports with DUT interfaces on T0 topologies.【F:tests/vrf/test_vrf.py†L503-L610】

## 4. Dependencies and Prerequisites
- **Fixtures:** `setup_vrf` (module-level VRF baseline), `ptf_test_port_map`, `mg_facts`, `vlan_mac`, `partial_ptf_runner`, `dut_facts`, `tbinfo`, `ptfhost`, and DUT host selectors; these seed topology data, configure PTF port mappings, and provide management access to the SONiC device.【F:tests/vrf/test_vrf_attr.py†L3-L15】【F:tests/vrf/test_vrf.py†L503-L610】
- **Topology Constraints:** Requires a single DUT with T0 VRF configuration so VLAN interfaces, PortChannels, and neighbors exist for both VRFs.【F:tests/vrf/test_vrf_attr.py†L18-L91】【F:tests/vrf/test_vrf.py†L503-L526】
- **PTF Environment:** Needs PTF host with copied ptftests and generated neighbor/FIB files for traffic replay.【F:tests/vrf/test_vrf_attr.py†L39-L91】【F:tests/vrf/test_vrf.py†L549-L610】

## 5. Key Inputs and Parameters
- **`new_vrf1_router_mac`:** The override MAC used in source-MAC validation for VRF1.【F:tests/vrf/test_vrf_attr.py†L25-L83】
- **Jinja/JSON templates (`vrf_attr_*.json/j2`):** Provide attribute-specific configuration payloads applied via `config load` to the DUT.【F:tests/vrf/test_vrf_attr.py†L33-L204】
- **`g_vars['vrf_intf_member_port_indices']`:** Mapping from VRF interfaces to PTF port indices generated during global setup; drives which PTF ports send traffic in each test.【F:tests/vrf/test_vrf_attr.py†L67-L257】【F:tests/vrf/test_vrf.py†L523-L526】
- **Neighbor definition files (`/tmp/vrf*_neigh.txt`):** Rendered for each VRF to tell PTF which destinations to probe.【F:tests/vrf/test_vrf_attr.py†L39-L210】
- **Runtime parameters (`pkt_action`, `ttl`, `ip_options`, `ipv4`/`ipv6` flags):** Control expectations and packet composition when invoking PTF traffic tests.【F:tests/vrf/test_vrf_attr.py†L64-L256】

## 6. External Libraries and Modules
- **`pytest`:** Provides fixture and test orchestration, including class-scoped fixtures and topology markers.【F:tests/vrf/test_vrf_attr.py†L1-L20】
- **`tests.ptf_runner.ptf_runner`:** Executes PTF-based packet tests, either directly or via the partial wrapper.【F:tests/vrf/test_vrf_attr.py†L13-L83】【F:tests/vrf/test_vrf.py†L549-L563】
- **`test_vrf` helpers:** Supply shared VRF setup (`setup_vrf`), DUT facts, neighbor file generation, and PTF port map creation tailored for VRF testing on T0 topologies.【F:tests/vrf/test_vrf_attr.py†L3-L15】【F:tests/vrf/test_vrf.py†L503-L610】
- **`tests.common.fixtures.ptfhost_utils.copy_ptftests_directory` & storage backend skip helper:** Imported for compatibility with the parent module, though not invoked directly in this file (remain available if the fixture auto-runs).【F:tests/vrf/test_vrf_attr.py†L14-L15】

## 7. Unspecified Items
- **Testbed inventory specifics (exact DUT model, neighbor counts, linecard details):** Not specified.
- **Exact content of JSON/Jinja templates (`vrf_attr_*.json/j2`):** Not specified in this file.
- **Pass/fail thresholds beyond packet drop/forward expectations:** Not specified.
