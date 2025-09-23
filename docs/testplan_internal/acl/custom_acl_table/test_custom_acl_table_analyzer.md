# Test Analyzer: `tests/acl/custom_acl_table/test_custom_acl_table.py`

## 1. Topology Type and Inference
- **Topology:** T0 (single ToR with possible dual ToR variants)
  - The module-level `pytestmark` restricts execution to `t0` topology, and subsequent checks on `tbinfo["topo"]["name"]` handle dual ToR specifics, confirming the T0 family as the intended environment.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L19-L48】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L268-L309】

## 2. Overall Test Case Purpose
- **Goal:** Validate that a custom ACL table type can be defined, populated with rules, and used to match traffic so that packets egress the correct uplink ports and increment the expected ACL counters exactly once per injected flow.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L253-L312】

## 3. Subtestcases and Their Contributions
1. **`setup_counterpoll_interval` fixture:** Lowers the ACL counter polling interval to 1 second (with restoration) so counter increments can be detected promptly during verification.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L34-L48】
2. **`remove_dataacl_table` autouse fixture:** Temporarily removes the `DATAACL` table to free TCAM resources and restores it afterward, preventing interference with the custom table under test.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L75-L108】
3. **`setup_custom_acl_table` fixture:** Copies the custom table type definition to the DUT, applies it via `sonic-cfggen`, creates `CUSTOM_TABLE`, and monitors syslog for successful creation. Tear-down removes both the table and custom type to clean up.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L111-L153】
4. **`setup_acl_rules` fixture:** Loads ACL rules into `CUSTOM_TABLE`, uses LogAnalyzer to detect rule-creation failures, and deletes the rules afterward to leave the switch unchanged.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L156-L187】
5. **Traffic validation loop in `test_custom_acl`:**
   - Collects topology data (`mg_facts`), selects VLAN ingress and uplink egress ports, and handles dual ToR MAC selection so packets traverse the intended interfaces.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L266-L292】
   - Builds rule-specific test packets covering IPv4/IPv6 destination matches, source/destination port matches, and port-range matches (`RULE_2`, `RULE_4`, `RULE_5`, `RULE_6`, `RULE_7`, `RULE_8`). Each packet validates that the corresponding ACL rule is hit.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L190-L234】
   - For each packet, clears counters, sends traffic from the chosen VLAN member, verifies egress on any upstream port, and confirms that the ACL counter increments exactly once (aggregating both ToRs when dual ToR is present).【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L293-L312】

## 4. Dependencies and Prerequisites
- **Fixtures:** `rand_selected_dut`, `rand_unselected_dut`, `tbinfo`, `ptfadapter`, `toggle_all_simulator_ports_to_rand_selected_tor`, `setup_acl_rules`, `setup_counterpoll_interval`, and `remove_dataacl_table` must be available from the common SONiC test framework.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L34-L312】
- **Topology Constraint:** `pytest.mark.topology("t0")` limits execution to T0-based beds; the script also contains dual ToR handling via `tbinfo["topo"]["name"]`.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L19-L309】
- **LogAnalyzer Access:** Requires loganalyzer support on the DUT to monitor ACL table/rule creation.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L122-L187】
- **PTF Connectivity:** Relies on the PTF test adapter to transmit and capture packets on mapped ports.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L293-L306】

## 5. Key Inputs and Their Origins
- **`CUSTOM_ACL_TABLE_TYPE_SRC_FILE` / `ACL_RULE_SRC_FILE`:** JSON definitions under `tests/acl/custom_acl_table/` copied to the DUT for table type and rule provisioning.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L24-L28】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L111-L187】
- **`tbinfo` fixture:** Supplies topology metadata such as name and type for dual ToR handling; the file does not specify its backing data source (likely testbed inventory).【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L268-L291】
- **`mg_facts` / `mg_facts_unselected_dut`:** Retrieved from the DUT via `get_extended_minigraph_facts(tbinfo)` to discover VLAN members and PTF port indices for traffic mapping.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L266-L292】
- **Router MAC selection:** Uses `rand_selected_dut.facts['router_mac']` or VLAN MAC for dual ToR to craft packets with the correct destination MAC.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L268-L275】
- **Destination port list:** Derived from port-channel membership or neighbor types through `get_all_upstream_neigh_type` and `get_neighbor_ptf_port_list`; ultimate data source beyond these helpers is not detailed here.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L288-L291】
- **Counter expectations:** `pytest_assert(acl_counter == 1)` enforces that each sent packet increments its rule counter exactly once, combining counts from both ToRs when applicable.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L299-L312】

## 6. External Libraries and Utilities
- **`pytest`:** Provides fixture management and topology markers controlling test execution.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L3-L22】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L253-L256】
- **`ptf.testutils`, `ptf.mask.Mask`, and `ptf.packet`:** Build test packets, mask expected fields, send traffic, and verify reception across uplink ports.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L6-L7】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L190-L251】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L305-L306】
- **`tests.common.plugins.loganalyzer.LogAnalyzer`:** Monitors DUT logs to ensure ACL table/rule creation success and captures failures for cleanup.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L122-L187】
- **`tests.common.helpers.assertions.pytest_assert`:** Supplies enhanced assertion messaging for ACL counter validation.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L11】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L312】
- **`tests.common.utilities.get_all_upstream_neigh_type` / `get_neighbor_ptf_port_list`:** Determine expected uplink PTF ports for verification, aligning traffic checks with topology knowledge.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L14-L15】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L288-L291】
- **`tests.common.dualtor.mux_simulator_control.toggle_all_simulator_ports_to_rand_selected_tor`:** Fixture hook to force dual ToR MUX simulator ports toward the selected DUT during the test.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L13】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L253-L255】
- **Standard libraries (`logging`, `json`, `time`):** Handle logging, configuration parsing, and counter polling delays required by the setup and verification steps.【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L1-L48】【F:tests/acl/custom_acl_table/test_custom_acl_table.py†L83-L187】

