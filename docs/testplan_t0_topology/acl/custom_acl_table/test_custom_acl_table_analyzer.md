# Test Case Analysis: `tests/acl/custom_acl_table/test_custom_acl_table.py`

## 1. Topology Type in Scope
- **Topology:** T0.
- **Inference:** The module-level `pytestmark` restricts execution to `pytest.mark.topology("t0")`, and the test logic references VLAN members and port channels that are characteristic of SONiC T0 fabrics, with conditional handling for dual ToR variants detected via `tbinfo["topo"]["name"]`.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L19-L31】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L268-L291】


## 2. Manual Tester Understanding
- **Scenario in plain language:** The DUT temporarily frees TCAM by removing the default data ACL, loads a custom ACL table type that watches VLAN 1000 traffic, applies IPv4/IPv6 rules, and then exercises those rules with sample packets to make sure hits are counted and forwarded correctly.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L75-L187】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L266-L312】
- **What a manual tester should take away:**
  - The goal is to prove that SONiC can host a bespoke ACL table without disturbing the default configuration and that the table correctly matches VLAN ingress traffic.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L111-L312】
  - Successful behaviour means the table and rules apply cleanly (no critical syslog entries), packets that match each rule exit via an uplink, and the per-rule counters increment exactly once when traffic is sent.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L293-L312】
  - Failures usually show up as ACL loader errors, packets leaking out the wrong interface, or counters that stay at zero even though traffic is observed.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L111-L312】
- **How fixtures map to concepts (for comprehension, not one-to-one replays):**
  - `remove_dataacl_table`: Highlights the precondition that the stock `DATAACL` must be absent so there is room for the custom definition.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L75-L108】
  - `setup_custom_acl_table`: Encapsulates creating the custom table type, pointing it at `Vlan1000`, and watching the logs for creation failures.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L111-L153】
  - `setup_acl_rules`: Focuses on loading individual rules and guarding against loader errors, reinforcing which traffic patterns will be validated later.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L156-L187】
  - `setup_counterpoll_interval`: Draws attention to timing—counters must refresh quickly so their increments prove rule hits.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L34-L48】
  - `test_custom_acl`: Contains the evidence gathering loop: generate the sample packets, send them through VLAN ingress, and confirm that expected counters rise while the packets take the intended egress path.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L190-L312】

## 3. Overall Test Case Purpose
- Validate that a custom ACL table type can be installed on the DUT, accept ACL rules, match traffic on VLAN ingress, forward matched traffic to uplinks, and update ACL hit counters accordingly.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L253-L312】

## 4. Detailed Subtestcases and Rationale
- **`remove_dataacl_table` fixture:** Temporarily removes the default `DATAACL` table to free TCAM resources, ensuring the custom table can be created; restores it afterward to leave the DUT clean.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L75-L108】
- **`setup_custom_acl_table` fixture:** Copies the custom ACL table type definition to the DUT(s), applies it, creates an ingress table bound to `Vlan1000`, and uses `LogAnalyzer` to confirm successful creation while capturing errors; cleans up table and type after the test.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L111-L153】
- **`setup_acl_rules` fixture:** Loads ACL rule definitions, applies them to the custom table under log monitoring to catch failures, and removes them during teardown. This ensures the traffic matching logic under test is present.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L156-L187】
- **`setup_counterpoll_interval` fixture:** Reduces ACL counter polling interval to speed up counter visibility and restores the default interval afterward, preventing timing issues when verifying counter increments.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L34-L48】
- **`test_custom_acl` main body:**
  - Collects topology facts, identifies router MAC and source/destination PTF ports based on VLAN and port-channel membership (or upstream neighbors when no port-channels exist).【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L266-L292】
  - Builds a suite of packets (RULE_2, RULE_4, RULE_5, RULE_6, RULE_7, RULE_8) covering IPv4/IPv6 destination matches, source/destination ports, and port-range criteria defined in the ACL rules.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L190-L233】
  - Iterates through each packet: clears counters, sends ingress traffic, verifies egress on any uplink port, aggregates counters from both ToRs when needed, and asserts that the matched rule counter increments exactly once. This loop validates that every ACL rule in the custom table behaves as expected.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L293-L312】

## 5. Dependencies and Prerequisites
- **Fixtures:** `rand_selected_dut`, `rand_unselected_dut`, `tbinfo`, `ptfadapter`, `toggle_all_simulator_ports_to_rand_selected_tor`, `setup_acl_rules`, `setup_counterpoll_interval`, `remove_dataacl_table`—all sourced from the SONiC test infrastructure to provide DUT handles, topology metadata, and Dual ToR control.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L34-L312】
- **Platform Constraints:** Requires a T0-based topology with VLAN1000, available TCAM resources after removing `DATAACL`, and (optionally) Dual ToR support when the topology name includes `dualtor` or `dualtor-aa`.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L75-L151】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L266-L309】
- **Tools:** Relies on CLI access to `sonic-cfggen`, `config acl`, `acl-loader`, and `aclshow` on the DUT(s), plus `LogAnalyzer` for log validation.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L83-L186】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L298-L309】

## 6. Key Inputs and Their Origins
- **`CUSTOM_ACL_TABLE_TYPE_SRC_FILE` / `ACL_RULE_SRC_FILE`:** JSON definitions stored under `acl/custom_acl_table/` in the repository, copied to the DUT as `/tmp/custom_acl_table.json` and `/tmp/acl_rules.json` before being applied via `sonic-cfggen`.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L24-L28】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L111-L174】
- **`tbinfo`:** Provides topology metadata (type, name) sourced from the testbed definition (testbed.yaml) and consumed to detect Dual ToR environments and derive neighbor data.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L34-L309】
- **`mg_facts` / `mg_facts_unselected_dut`:** Retrieved via `get_extended_minigraph_facts(tbinfo)` to map VLANs, port-channels, and PTF indices defined in the minigraph/topology files.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L266-L291】
- **`router_mac`:** Either the DUT’s router MAC (`rand_selected_dut.facts['router_mac']`) or the VLAN MAC on Dual ToR setups, ensuring packets use the correct destination MAC.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L268-L275】
- **`src_port` / `dst_port_indices`:** Selected from VLAN members and port-channel memberships (or from neighbor lists via `get_neighbor_ptf_port_list`) to drive PTF traffic paths reflective of the testbed configuration.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L276-L291】
- **`asic_type`:** Pulled from `rand_selected_dut.facts` to optionally skip validation on the virtual switch (VS) platform where ACL counters may be unreliable.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L266-L304】

## 7. External Libraries and Roles
- **`pytest`:** Provides fixtures, parametrization, and assertion integration for the test module.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L3-L312】
- **`ptf.testutils` / `ptf.packet` (Scapy) / `ptf.mask.Mask`:** Used to craft packets, mask dynamic fields, send traffic from the PTF host, and verify egress behavior.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L6-L233】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L293-L307】
- **Standard libraries (`logging`, `json`, `time`):** Handle logging, JSON parsing of ACL tables, and timing adjustments when polling counters.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L1-L187】
- **Not specified:** Any additional third-party dependencies beyond those listed above.
