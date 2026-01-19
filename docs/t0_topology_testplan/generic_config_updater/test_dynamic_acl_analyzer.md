# Dynamic ACL GCU Test Analyzer

## 1. Topology Type
- **Supported topologies:** `t0`, `m0`, `m0_vlan`, and `m0_l3` variations, with awareness of dual-TOR and isolated/storage scenarios.
- **Inference:** The module-level `pytestmark` advertises `topology('t0', 'm0')`. The `setup` fixture inspects `tbinfo` and `topo_scenario` to distinguish between `m0_vlan_scenario`, `m0_l3_scenario`, and other `t0`/dual-TOR variations, while collecting VLAN members, upstream/downstream ports, and PTF indices accordingly. Dual-TOR handling is explicit via `rand_unselected_dut` usage and mux fixtures.【F:tests/generic_config_updater/test_dynamic_acl.py†L24-L199】【F:tests/generic_config_updater/test_dynamic_acl.py†L200-L399】

## 2. Overall Test Case Purpose
- **Goal:** Validate Generic Config Updater (GCU) workflows for dynamic ACL tables and rules on SONiC devices.
- **Context:** The suite ensures that ACL table creation, rule addition, modification, removal, and error handling behave correctly while verifying live traffic behavior through PTF. It covers IPv4/IPv6 unicast forwarding, ARP/NDP, DHCP relay, drop enforcement, priority ordering, scale, and failure cases, ensuring configuration persistence and functional correctness within SONiC’s dynamic ACL framework.【F:tests/generic_config_updater/test_dynamic_acl.py†L732-L1166】【F:tests/generic_config_updater/test_dynamic_acl.py†L1167-L1431】

## 3. Detailed Breakdown of Sub-Testcases
- **`test_gcu_acl_arp_rule_creation`**
  - Creates ARP or NDP forwarding rules (depending on IP type chosen by `prepare_ptf_intf_and_ip`) and an accompanying drop rule, then generates traffic to ensure neighbor entries are learned only for permitted traffic while other packets are blocked.
  - Demonstrates that blanket ARP/NDP allow rules take precedence over default drops, validating neighbor discovery functionality under dynamic ACL control.【F:tests/generic_config_updater/test_dynamic_acl.py†L1150-L1189】
- **`test_gcu_acl_dhcp_rule_creation`**
  - Installs DHCP(v4/v6) forwarding rules via GCU alongside a drop rule, then crafts DHCP solicit/discover traffic to verify relay behavior and confirms other traffic is blocked.
  - Ensures critical control-plane DHCP traffic is preserved when ACLs are dynamically managed.【F:tests/generic_config_updater/test_dynamic_acl.py†L1190-L1210】
- **`test_gcu_acl_drop_rule_creation`**
  - Adds an initial drop rule for a specific ingress port and confirms packets matching it are dropped, while packets sourced from an unblocked port still forward.
  - Validates fundamental drop enforcement for ingress ACLs created through GCU.【F:tests/generic_config_updater/test_dynamic_acl.py†L1211-L1233】
- **`test_gcu_acl_drop_rule_removal`**
  - Programs three drop rules, removes one via GCU, and verifies traffic from the formerly blocked port now forwards.
  - Confirms rule deletion updates datapath behavior immediately and correctly.【F:tests/generic_config_updater/test_dynamic_acl.py†L1234-L1253】
- **`test_gcu_acl_forward_rule_priority_respected`**
  - Installs forwarding rules with higher priority than drop rules, then verifies overlapping traffic follows the intended priority hierarchy.
  - Checks that ACL priority semantics are preserved when mixing forward/drop actions through dynamic updates.【F:tests/generic_config_updater/test_dynamic_acl.py†L1254-L1273】
- **`test_gcu_acl_forward_rule_same_priority`**
  - Adds multiple forward rules sharing the same priority and validates they all function while drop rules still block unrelated traffic.
  - Ensures deterministic behavior even when rule priorities tie, an important edge condition.【F:tests/generic_config_updater/test_dynamic_acl.py†L1274-L1304】
- **`test_gcu_acl_forward_rule_replacement`**
  - Creates forward and drop rules, then replaces the forwarding match criteria and verifies only the new destinations pass while old ones are blocked.
  - Verifies rule replacement operations correctly modify hardware state without leftovers.【F:tests/generic_config_updater/test_dynamic_acl.py†L1305-L1325】
- **`test_gcu_acl_forward_rule_removal`** *(parameterized for IPv4/IPv6)*
  - Removes a selected forward rule, then checks that traffic for that family is dropped while the other family still forwards.
  - Confirms selective rule removal precision and integrity of remaining entries.【F:tests/generic_config_updater/test_dynamic_acl.py†L1326-L1356】
- **`test_gcu_acl_scale_rules`**
  - Applies a large set of forwarding and drop rules (150 forward entries, drop per VLAN port), then ensures forwarding/dropping works for sample destinations and ports.
  - Stress-tests scalability and consistency of dynamic ACL programming.【F:tests/generic_config_updater/test_dynamic_acl.py†L1357-L1385】
- **`test_gcu_acl_nonexistent_rule_replacement`**
  - Attempts to replace a rule that does not exist, expecting failure from GCU.
  - Validates error handling paths for mis-specified updates.【F:tests/generic_config_updater/test_dynamic_acl.py†L1386-L1392】
- **`test_gcu_acl_nonexistent_table_removal`**
  - Tries to remove a non-existent ACL table and asserts failure.
  - Ensures defensive behavior when configurations reference missing objects.【F:tests/generic_config_updater/test_dynamic_acl.py†L1393-L1399】

### Helper Functions and Fixtures
- Numerous helper functions (`dynamic_acl_create_*`, `dynamic_acl_verify_packets`, etc.) abstract repetitive GCU operations and traffic verification, enabling each test to focus on a particular scenario while reusing the same configuration templates and packet checks.【F:tests/generic_config_updater/test_dynamic_acl.py†L400-L934】【F:tests/generic_config_updater/test_dynamic_acl.py†L935-L1149】
- Packet generators (`generate_packets`, `dynamic_acl_send_and_verify_dhcp_packets`, etc.) craft expected traffic for validation, ensuring thorough coverage of protocol-specific cases.

## 4. Dependencies and Prerequisites
- **Fixtures:** `setup`, `setup_env`, `config_facts`, `intfs_for_test`, `prepare_ptf_intf_and_ip`, topology fixtures (`rand_selected_dut`, `rand_unselected_dut`, `tbinfo`, `ptfadapter`, `ptfhost`), dual-TOR control fixtures (`toggle_all_simulator_ports_to_rand_selected_tor`, `setup_standby_ports_on_rand_unselected_tor`). These establish DUT state, PTF environment, and rollback checkpoints.【F:tests/generic_config_updater/test_dynamic_acl.py†L56-L399】【F:tests/generic_config_updater/test_dynamic_acl.py†L400-L731】
- **Topology constraints:** Requires topologies with VLAN members and PTF connectivity; dual-TOR paths rely on mux simulator fixtures. Scale tests need at least three downstream ports for drop-rule scenarios.
- **Prerequisite services:** Ability to stop `garp_service` on PTF for single TOR setups and flush neighbor tables/clear ARP/NDP entries as part of test flow.【F:tests/generic_config_updater/test_dynamic_acl.py†L200-L399】【F:tests/generic_config_updater/test_dynamic_acl.py†L400-L731】

## 5. Key Inputs and Parameters
- **Constants:** Destination IPs (`DST_IP_FORWARDED_ORIGINAL`, etc.), priorities (`MAX_IP_RULE_PRIORITY`, `MAX_DROP_RULE_PRIORITY`), DHCP parameters, and template filenames driving configuration payloads.【F:tests/generic_config_updater/test_dynamic_acl.py†L36-L168】
- **Dynamic values:** Derived from `tbinfo`/`config_facts` to determine VLANs, ports, MACs, and loopback IPs used to bind ACL tables and craft packets. These govern which interfaces participate and the traffic patterns exercised.【F:tests/generic_config_updater/test_dynamic_acl.py†L56-L399】
- **Parameterized input:** `prepare_ptf_intf_and_ip` fixture yields IPv4 or IPv6 contexts; `test_gcu_acl_forward_rule_removal` explicitly parametrizes `ip_type` to cover both families.【F:tests/generic_config_updater/test_dynamic_acl.py†L300-L399】【F:tests/generic_config_updater/test_dynamic_acl.py†L1326-L1356】

## 6. External Libraries and Modules
- **PyTest & Plugins:** `pytest`, custom fixtures from `tests.common` (GU utilities, dual-TOR helpers, PTF host utilities) provide orchestration, checkpointing, and expectations (`expect_op_success`, `expect_acl_rule_match`, etc.).【F:tests/generic_config_updater/test_dynamic_acl.py†L8-L55】
- **Networking & Packet Tools:** `scapy`, `ptf.testutils`, `ptf.mask.Mask`, and `ptf.packet` construct and validate packets. `netaddr`, `ipaddress`, and utility functions handle IP manipulations.
- **System/SONiC Helpers:** `tests.common.utilities` for topology-aware neighbor classification; `tests.generic_config_updater.gu_utils` for templating and applying JSON patches via GCU.【F:tests/generic_config_updater/test_dynamic_acl.py†L8-L55】

## 7. Unspecified Items
- **Testbed hardware specifics:** Not specified.
- **Exact pass/fail criteria thresholds beyond functional checks:** Not specified.
