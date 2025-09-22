# QA Automation Analysis

## 1. Topology in Use
* The module asserts a dual-DUT setup with an Ixia (or Spirent) traffic generator connected to both DUTs, including a port-channel between DUT1 and DUT2. This is inferred from the ASCII art diagram in `get_handles()` and the explicit topology request `st.ensure_min_topology("D1D2:2", "D1T1:2", "D2T1:1")`, which requires two DUT interconnects and test generator links.【F:spytest/tests/qos/acl/test_acls.py†L41-L63】

## 2. Overall Test Purpose
* The suite validates ACL functionality across IPv4, IPv6, and MAC domains on interfaces, VLANs, port-channels, and the entire switch, including management interfaces exposed through config-loader, REST, and gNMI APIs. It checks both forwarding/drop behaviors via traffic validation and counter inspections, ensuring rule priority, redirection, and statistics collection operate correctly under different binding scopes.【F:spytest/tests/qos/acl/test_acls.py†L69-L375】【F:spytest/tests/qos/acl/test_acls.py†L540-L1106】

## 3. Subtestcases and Their Contributions
* **`test_ft_acl_ingress_ipv4`** – Verifies IPv4 ingress ACL enforcement, packet redirection, counter increments, and rule priority on DUT1’s test port.【F:spytest/tests/qos/acl/test_acls.py†L355-L375】
* **`test_ft_acl_egress_ipv4`** – Confirms IPv4 egress ACL behavior on DUT1 by validating packet forwarding and hit counters.【F:spytest/tests/qos/acl/test_acls.py†L379-L389】
* **`test_ft_acl_egress_ipv6`** – Ensures IPv6 egress ACLs on DUT2 operate correctly by resetting counters, generating traffic, and checking statistics.【F:spytest/tests/qos/acl/test_acls.py†L393-L411】
* **`test_ft_acl_ingress_ipv6`** – Validates IPv6 ingress ACLs on DUT2, including priority handling and hit counters after traffic generation.【F:spytest/tests/qos/acl/test_acls.py†L416-L436】
* **`test_ft_mac_acl_port`** – Exercises MAC ACLs bound to DUT1’s port, verifying both ingress and egress rules with traffic and counter checks.【F:spytest/tests/qos/acl/test_acls.py†L440-L469】
* **`test_ft_acl_port_channel_ingress`** – Tests IPv6 ingress ACLs applied to DUT1’s port-channel, confirming drop/forward actions and counters.【F:spytest/tests/qos/acl/test_acls.py†L472-L489】
* **`test_ft_acl_port_channel_egress`** – Evaluates IPv6 egress ACLs on DUT1’s port-channel by applying dedicated tables and validating traffic results.【F:spytest/tests/qos/acl/test_acls.py†L495-L514】
* **`test_ft_acl_port_channel_V4_egress`** – Checks IPv4 egress ACLs on DUT2’s port-channel to ensure correct enforcement.【F:spytest/tests/qos/acl/test_acls.py†L516-L538】
* **`test_ft_acl_vlan_v6_egress`** – Binds IPv6 egress ACLs to a VLAN on DUT2, verifying stats around TG-driven traffic.【F:spytest/tests/qos/acl/test_acls.py†L540-L568】
* **`test_ft_acl_vlan_v6_ingress`** – Validates IPv6 ingress ACLs tied to DUT2 VLAN membership with traffic checks.【F:spytest/tests/qos/acl/test_acls.py†L569-L587】
* **`test_ft_acl_vlan_V4_ingress`** – Confirms IPv4 ingress ACLs on DUT1 VLANs, including packet-action overrides and counter validation.【F:spytest/tests/qos/acl/test_acls.py†L591-L610】
* **`test_ft_acl_vlan_V4_egress`** – Ensures IPv4 egress ACLs on DUT1 VLANs perform as expected.【F:spytest/tests/qos/acl/test_acls.py†L612-L630】
* **`test_ft_acl_port_channel_V4_ingress`** – Exercises IPv4 ingress ACLs bound to DUT2’s port-channel, validating drop outcomes.【F:spytest/tests/qos/acl/test_acls.py†L633-L653】
* **`test_ft_v4_acl_switch`** – Applies IPv4 ACLs globally to the switch (ingress and egress) and confirms enforcement and counter updates in both directions.【F:spytest/tests/qos/acl/test_acls.py†L655-L695】
* **`test_ft_mac_acl_switch`** – Verifies MAC ingress ACLs at the switch scope using traffic validation and hit counters.【F:spytest/tests/qos/acl/test_acls.py†L699-L719】
* **`test_ft_mac_acl_switch_egress`** – Validates MAC egress ACLs applied switch-wide through traffic and counter checks.【F:spytest/tests/qos/acl/test_acls.py†L723-L745】
* **`test_ft_mac_acl_vlan`** – Checks MAC ACLs (ingress/egress) bound to VLAN interfaces with bi-directional traffic inspection.【F:spytest/tests/qos/acl/test_acls.py†L749-L770】
* **`test_ft_mac_acl_portchannel`** – Ensures MAC ingress ACLs on DUT2 port-channel enforce VLAN-specific matches.【F:spytest/tests/qos/acl/test_acls.py†L774-L794】
* **`test_ft_mac_acl_egress_portchannel`** – Confirms MAC egress ACLs on DUT2 port-channel honor VLAN tagging in traffic decisions.【F:spytest/tests/qos/acl/test_acls.py†L798-L817】
* **`test_ft_mac_acl_port_adv`** – Exercises hardware counter mode transitions while validating MAC ingress ACL statistics per-rule.【F:spytest/tests/qos/acl/test_acls.py†L820-L838】
* **`test_ft_acl_ingress_ipv4_adv`** – Mirrors the advanced MAC test for IPv4 ingress ACLs, ensuring per-interface counter mode works.【F:spytest/tests/qos/acl/test_acls.py†L842-L860】
* **`test_ft_acl_loader`** – Validates ACL rule lifecycle using `acl-loader` and `config acl` CLI workflows, checking rule counts after updates and adds.【F:spytest/tests/qos/acl/test_acls.py†L863-L924】
* **`test_ft_acl_icmpv6`** – Performs IPv6 ICMP connectivity after configuring VLAN interfaces, verifying ACL compatibility with routing traffic.【F:spytest/tests/qos/acl/test_acls.py†L925-L952】
* **`test_ft_mac_acl_prioirty_ingress`** – Tests precedence between MAC and IPv4 ingress ACL rules when both apply to a port.【F:spytest/tests/qos/acl/test_acls.py†L953-L982】
* **`test_ft_mac_acl_prioirty_egress`** – Similar priority validation for egress direction mixing MAC and IPv4 ACLs.【F:spytest/tests/qos/acl/test_acls.py†L983-L1009】
* **`test_acl_rest`** – Confirms RESTCONF-based ACL configuration works and enforces the defined IPv4 rules.【F:spytest/tests/qos/acl/test_acls.py†L1014-L1070】
* **`test_ft_acl_gnmi`** – Ensures gNMI-set ACLs are honored by the data plane and retrievable via gNMI get requests.【F:spytest/tests/qos/acl/test_acls.py†L1073-L1106】

## 4. Dependencies and Prerequisites
* **Autouse fixtures** – `acl_v4_module_hooks` initializes the topology, applies base ACL/VLAN/port-channel configuration, creates traffic streams, and cleans up afterward, while `acl_function_hooks` performs targeted ACL table cleanup for specific functions.【F:spytest/tests/qos/acl/test_acls.py†L320-L340】
* **Topology constraints** – Requires two DUTs with at least two interlinks and TG connectivity as defined in `get_handles()`. Traffic generator must support APIs invoked by `tgapi` (Ixia default, Spirent fallback).【F:spytest/tests/qos/acl/test_acls.py†L41-L63】【F:spytest/tests/qos/acl/test_acls.py†L153-L195】
* **Feature readiness** – Tests assume ability to create VLANs, LAGs, and apply ACLs on ports, VLANs, switch scope, and via management interfaces; absence of these features would block execution. Not explicitly documented beyond code usage (implicit requirement).【F:spytest/tests/qos/acl/test_acls.py†L69-L151】【F:spytest/tests/qos/acl/test_acls.py†L540-L1106】

## 5. Key Inputs and Their Sources
* `vars` mapping of DUT/TG interfaces is populated by `st.ensure_min_topology`, leveraging the active testbed definition (from inventory/testbed files).【F:spytest/tests/qos/acl/test_acls.py†L54-L58】
* `data` parameters such as traffic rates, VLAN IDs, LAG member lists, and port-channel name are generated at runtime (e.g., VLAN via `utils.random_vlan_list()`) to drive traffic creation and configuration functions.【F:spytest/tests/qos/acl/test_acls.py†L25-L32】【F:spytest/tests/qos/acl/test_acls.py†L69-L100】
* ACL configuration templates and rule payloads originate from imported helper modules (`tests.qos.acl.acl_json_config`, `tests.qos.acl.acl_rules_data`), which provide pre-defined JSON structures for application and loader tests.【F:spytest/tests/qos/acl/test_acls.py†L8-L11】【F:spytest/tests/qos/acl/test_acls.py†L863-L908】
* API endpoint constants (`YANG_MODEL`) and request payload fields used in REST/gNMI tests are defined locally within the test file, ensuring alignment with SONiC models.【F:spytest/tests/qos/acl/test_acls.py†L21】【F:spytest/tests/qos/acl/test_acls.py†L1014-L1106】
* CLI type (`data.cli_type`) can be overridden externally (e.g., via SpyTest CLI options) and is passed to configuration helpers when available, implying dependency on runtime parameters.【F:spytest/tests/qos/acl/test_acls.py†L30-L32】【F:spytest/tests/qos/acl/test_acls.py†L69-L132】

## 6. External Libraries and Roles
* **`spytest` utilities (`st`, `tgapi`, `SpyTestDict`)** – Provide logging, topology discovery, and traffic generator control abstractions.【F:spytest/tests/qos/acl/test_acls.py†L5-L63】【F:spytest/tests/qos/acl/test_acls.py†L153-L195】
* **`apis.switching` modules (`vlan_obj`, `pc_obj`)** – Create/delete VLANs and port-channels, and manage membership during setup/teardown.【F:spytest/tests/qos/acl/test_acls.py†L69-L133】
* **`apis.qos.acl` (`acl_obj`) and helpers (`acl_utils`)** – Apply ACL configurations, delete tables, check counters, and report results across all tests.【F:spytest/tests/qos/acl/test_acls.py†L69-L1106】
* **`apis.routing.ip` (`ipobj`)** – Configure and remove IPv6 addresses, plus ping validation for ICMPv6 tests.【F:spytest/tests/qos/acl/test_acls.py†L925-L951】
* **`apis.system` modules (`gnmiapi`, interface counters, `rest_status`)** – Support gNMI operations, counter collection, and REST response validation.【F:spytest/tests/qos/acl/test_acls.py†L393-L410】【F:spytest/tests/qos/acl/test_acls.py†L1014-L1106】
* **Utility helpers (`utilities.common`, `utilities.parallel`)** – Execute parallel CLI calls, randomize VLANs, and handle exception aggregation during setup/cleanup.【F:spytest/tests/qos/acl/test_acls.py†L69-L135】【F:spytest/tests/qos/acl/test_acls.py†L393-L407】
* Any additional dependencies outside this list are not specified in the file.
