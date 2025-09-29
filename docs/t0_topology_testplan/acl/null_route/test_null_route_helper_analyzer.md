# Null Route Helper Test Analyzer

## 1. Topology Type
- **Identified Topologies:** `t0`, `m0`, `mx`, `m1` (declared via `pytestmark`).
- **Inference:** The test is marked with `pytest.mark.topology("t0", "m0", "mx", "m1")`, indicating it is valid for any of these datacenter and metro-style SONiC topologies. Within fixtures like `create_acl_table` and `test_null_route_helper`, the test dynamically checks `tbinfo["topo"]["type"]` to adjust behavior (e.g., how to choose neighbor ports) for the active topology, confirming multi-topology awareness.

## 2. Overall Test Case Purpose
- **Primary Goal:** Validate the `null_route_helper` utility script's ability to block and unblock IP prefixes via ACL manipulation while ensuring traffic is forwarded or dropped according to the configured rules.
- **Context in SONiC:** In SONiC ACL workflows, null route helper scripts automate installation of null-route ACL entries. This test exercises production-like ACL table creation, rule application, and traffic verification to confirm correct enforcement and resource handling across supported topologies.

## 3. Detailed Breakdown of Sub-Testcases
- **Fixture `remove_data_everflow_acl_table` (module, autouse):**
  - Cleans up pre-existing `DATAACL` and `EVERFLOWV6` tables to free TCAM resources before tests. Restores them afterward if removed. Ensures the DUT has capacity for temporary ACL tables used in the test.
  - Relevance: Prevents resource exhaustion that would cause false failures when creating the test ACL tables.

- **Helper `remove_acl_table(duthost)`:**
  - Issues CLI commands to remove the v4 and v6 null-route ACL tables created for the test.
  - Relevance: Supports teardown and error handling in ACL table setup.

- **Fixture `create_acl_table` (module scope):**
  - Gathers topology facts to determine appropriate port lists (LAG members or uplink neighbors) and creates IPv4 and IPv6 ACL tables. Uses `LogAnalyzer` to detect `SAI_STATUS_INSUFFICIENT_RESOURCES` errors and skips the test if ACL creation fails. Tears down tables afterward.
  - Relevance: Provides the ACL infrastructure required for applying null-route rules.

- **Fixture `apply_pre_defined_rules` (module scope):**
  - Loads a predefined ACL JSON payload that mirrors production rules, waits for rule creation, and cleans the ACL rules after the test.
  - Relevance: Establishes baseline ACL entries so the helper script operates in a realistic environment.

- **Fixture `setup_ptf` (module scope):**
  - Discovers a VLAN interface with both IPv4 and IPv6 addresses, programs corresponding addresses on the PTF port, and returns the port/IP mapping. Cleans up PTF configuration afterward.
  - Relevance: Prepares PTF host to send dual-stack traffic for forwarding/dropping validation.

- **Helper `generate_packet(src_ip, dst_ip, dst_mac)`:**
  - Builds IPv4 or IPv6 packets (and expected masked packets) according to the source IP version.
  - Relevance: Supplies traffic patterns used by the main test loop.

- **Helper `send_and_verify_packet(...)`:**
  - Sends packets via PTF, verifying whether they are forwarded or dropped based on expected action.
  - Relevance: Encapsulates packet transmission and verification logic.

- **Test `test_null_route_helper(...)`:**
  - Uses fixtures to configure DUT/PTF, determines router MAC and egress interfaces, iterates through `TEST_DATA` scenarios to optionally run `null_route_helper` commands (block/unblock for IPv4 and IPv6), and verifies forwarding behavior with random uplink ports and the VLAN RX port. Ensures helper script properly enforces null routes, including idempotent double block/unblock operations.
  - Relevance: Central validation that the null-route helper script manipulates ACL rules correctly and traffic observes expected outcomes.

## 4. Dependencies and Prerequisites
- **Fixtures:** `rand_selected_dut`, `duthosts`, `tbinfo`, `ptfadapter`, `ptfhost`, `remove_ip_addresses` (imported), plus custom fixtures defined in this file (`create_acl_table`, `apply_pre_defined_rules`, `setup_ptf`).
- **Platform Requirements:** DUT must support creating additional ACL tables; topology must provide VLANs with dual-stack interfaces. PTF host access is required for traffic injection.
- **Tools:** `LogAnalyzer` with `LOG_ERROR_INSUFFICIENT_RESOURCES` pattern must be available to detect ACL resource issues.

## 5. Key Inputs and Parameters
- **`TEST_DATA`:** Defines source IPs, CLI actions (`block`/`unblock` commands), and expected packet handling results for both IPv4 and IPv6 scenarios.
- **Topology Facts (`tbinfo`, `mg_facts`):** Determine port lists for ACL tables and PTF transmit interfaces depending on active topology.
- **ACL Table Names (`ACL_TABLE_NAME_V4`, `ACL_TABLE_NAME_V6`):** Used in configuration commands and rule cleanups.
- **ACL JSON File Paths (`ACL_JSON_FILE_SRC`, `ACL_JSON_FILE_DEST`):** Control which predefined rules are loaded onto the DUT.
- **Router MAC (`rand_selected_dut.facts["router_mac"]`):** Needed to craft correct expected packets.

## 6. External Libraries and Modules
- **Standard Libraries:** `ipaddress`, `logging`, `random`, `os`, `time`, `json` for address manipulation, logging, randomness, file paths, timing, and JSON parsing.
- **PyTest:** `pytest` for fixtures and marking topology scope.
- **PTF Modules:** `ptf.mask.Mask`, `ptf.packet` (aliased as `scapy`), and `ptf.testutils` provide packet crafting, masking, and transmission utilities.
- **SONiC Test Common Helpers:**
  - `tests.common.fixtures.ptfhost_utils.remove_ip_addresses` (fixture import for PTF cleanup, though not directly used in file scope).
  - `tests.common.helpers.assertions.pytest_require` for assertions.
  - `tests.common.plugins.loganalyzer.LogAnalyzer` and `LogAnalyzerError` for log monitoring.
  - `tests.common.utilities` (`get_upstream_neigh_type`, `get_neighbor_ptf_port_list`, `get_neighbor_port_list`) for topology-aware neighbor selection.

## 7. Unspecified Items
- Testbed inventory specifics (exact device counts, interface maps) – **Not specified**.
- CLI invocation parameters outside the file (e.g., command-line options to pytest) – **Not specified**.
- Behavior of `null_route_helper` script implementation beyond observed commands – **Not specified**.
