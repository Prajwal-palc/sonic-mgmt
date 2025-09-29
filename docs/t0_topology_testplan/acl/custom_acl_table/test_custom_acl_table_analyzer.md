# Custom ACL Table Test Case Analyzer

## 1. Topology Type
- **Topology:** `t0`.
- **Inference:** The file-level `pytestmark` applies `pytest.mark.topology("t0")`, constraining execution to T0 topologies. Additional logic branches on `tbinfo["topo"]["name"]` to handle dual ToR (`dualtor`/`dualtor-aa`) variations, confirming the test is designed for a T0 dual-homed leaf-spine environment.

## 2. Overall Test Case Purpose
- **Goal:** Validate that SONiC can create and exercise a custom ACL table type, apply ACL rules sourced from JSON, forward permitted traffic correctly, and update ACL hit counters.
- **Context in SONiC framework:** The test automates configuration through `sonic-cfggen`, `config acl` CLI commands, and log analysis to mimic operational workflows. It verifies control-plane configuration persistence (custom ACL type and rules), data-plane enforcement (packet forwarding via PTF), and observability (ACL counters), aligning with SONiC QA’s focus on feature correctness and monitoring.

## 3. Detailed Breakdown of Sub-Testcases
- **`test_custom_acl`**
  - **Intent:** End-to-end validation of a custom ACL table from creation to traffic verification.
  - **Logic:**
    1. Gathers minigraph facts to determine router MAC, VLAN members, and PTF port mappings.
    2. Collects destination uplink ports either from port-channels or upstream neighbor types for the topology.
    3. Uses helper functions to build traffic patterns covering IPv4/IPv6, L4 ports, and port ranges that correspond to entries in `acl_rules.json`.
    4. For each rule:
       - Clears ACL counters on the selected (and, if applicable, unselected) DUT.
       - Skips forwarding checks on virtual switch ASICs to avoid unsupported scenarios.
       - Sends packets from a VLAN member port with PTF, verifies egress on any uplink, and confirms ACL counters increment exactly once.
  - **Relevance:** Demonstrates that user-defined ACL table types operate correctly across routing fabrics, ensuring both configuration and runtime enforcement meet expectations.

### Helper Fixtures and Functions
- **`setup_counterpoll_interval`** – Temporarily accelerates ACL counter polling to 1 second to observe counter updates promptly.
- **`remove_dataacl_table`** – Frees TCAM resources by removing the default `DATAACL` table before tests and restoring it afterward.
- **`setup_custom_acl_table`** – Loads the custom ACL table type JSON, creates the table, and ensures log analyzer confirmation of successful creation.
- **`setup_acl_rules`** – Loads ACL rules JSON into the custom table while verifying no failure logs appear, and cleans up afterward.
- **`build_testing_pkts` / `build_exp_pkt`** – Provide tailored ingress packets matching rule criteria and masks expected egress frames for flexible verification.
- **`clear_acl_counter` / `read_acl_counter`** – Manage counter state inspection to validate hit counts per rule.

These helpers orchestrate environment prep, configuration, traffic generation, and validation to support the single test case.

## 4. Dependencies and Prerequisites
- **Fixtures:** `rand_selected_dut`, `rand_unselected_dut`, `tbinfo`, `ptfadapter`, `toggle_all_simulator_ports_to_rand_selected_tor`. They supply DUT access, topology metadata, PTF control, and dual ToR port alignment.
- **Topology constraints:** Requires T0 with VLAN1000, potential port-channels, and sufficient TCAM resources (hence removing `DATAACL`). Dual ToR logic expects `dualtor` or `dualtor-aa` naming conventions.
- **Runtime tools:** Access to SONiC CLI utilities (`sonic-cfggen`, `config acl`, `aclshow`, `sonic-db-cli`) and log analyzer capabilities.

## 5. Key Inputs and Parameters
- **JSON sources:** `acl/custom_acl_table/custom_acl_table.json` (defines `CUSTOM_TYPE`) and `acl/custom_acl_table/acl_rules.json` (rule set). These control the ACL table schema and match criteria.
- **Topology facts:** `tbinfo` and `get_extended_minigraph_facts` outputs determine router MAC, VLAN members, and PTF port mappings.
- **ASIC-specific handling:** `rand_selected_dut.facts['asic_type']` triggers skips on virtual switch platforms.
- **Counter polling interval:** Commands `counterpoll acl interval 1000/10000` accelerate and restore counter updates to observe increments during the test window.

## 6. External Libraries and Modules
- **Standard Python:** `logging`, `json`, `time` for diagnostics, configuration parsing, and pacing.
- **PyTest:** `pytest` for fixtures and markers, `pytest_assert` for custom assertions.
- **PTF:** `ptf.packet` (Scapy wrapper), `ptf.mask.Mask`, and `ptf.testutils` to craft, send, and verify network packets.
- **SONiC helpers:** Modules from `tests.common` (log analyzer, mux simulator control, utilities) enabling topology control, log scanning, neighbor discovery, and assertion helpers.

## 7. Unspecified Items
- **Testbed inventory specifics (e.g., exact port counts, hardware SKU):** Not specified.
- **External data sources beyond the referenced JSON files:** Not specified.
