# QA Test Analysis

## 1. Topology Type
* **Type:** Dual DUTs with interlink LAG and traffic generators on edge (D1D2:2, D1T1:1, D2T1:1).
* **Inference:** Determined from `st.ensure_min_topology("D1D2:2", "D1T1:1", "D2T1:1")` inside `get_handles()`, which implies two DUTs interconnected by two links and each connected to a single traffic generator port. The ASCII art in the docstring of `get_handles()` corroborates this layout. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L43-L62】

## 2. Overall Test Case Purpose
* Validate IPv4 and IPv6 ACL-based L3 forwarding behavior across a port-channel between two DUTs when ingress ACLs are applied on interfaces connected to traffic generators, ensuring forwarding/dropping actions and ACL counters operate as expected. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L215-L267】

## 3. Subtestcases
1. **Module Fixture `acl_v4_module_hooks`**
   * Sets up topology, creates port-channels, applies ACL configurations (IPv4 on DUT1 ingress, IPv6 on DUT2 ingress), configures IP/IPv6 addresses, static routes, ARP/NDP, and constructs traffic generator streams. Essential for ensuring consistent environment and traffic definitions for subsequent subtests. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L187-L267】
2. **`test_ft_acl_ingress_ipv4_l3_forwarding`**
   * Sends IPv4 ingress traffic from TG1 through DUT1, verifies packet forwarding to TG2, checks ACL hit counters and rule priority on the IPv4 table. Validates IPv4 ACL forwarding behavior. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L269-L283】
3. **`test_ft_acl_ingress_ipv6_l3_forwarding`**
   * Sends IPv6 ingress traffic from TG2 through DUT2, validates forwarding to TG1, ensures ACL counters increment and higher-priority rules take precedence. Confirms IPv6 ACL forwarding behavior. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L286-L299】

## 4. Dependencies / Prerequisites
* **Fixtures:** Module-scoped `acl_v4_module_hooks` (auto-used) handles setup/teardown. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L187-L267】
* **Topology Constraints:** Requires two DUTs with at least two interconnect links and traffic generator ports as enforced by `st.ensure_min_topology`. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L57-L62】
* **Testbed Resources:** Traffic generator supporting IxNetwork/Ixia or Spirent (`data.tg_type`). Port-channel capability on DUTs. Static routing support (IPv4/IPv6). 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L23-L37】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L104-L267】
* **Libraries/Helpers:** Relies on spytest framework (`st`, `tgapi`), QoS ACL APIs, routing/ARP APIs, and utilities for parallel execution and traffic validation. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L5-L19】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L118-L184】

## 5. Key Inputs
* **Hardcoded Test Data:** IP addresses, prefixes, MAC addresses, ACL type (`data` dictionary). 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L21-L41】
* **Topology Handles:** Derived from `st.ensure_min_topology` using testbed definitions (`vars` populated with DUT/TG port mappings from inventory/testbed). 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L57-L102】
* **ACL Definitions:** Pulled from `tests.qos.acl.acl_json_config` module (`acl_json_config_v4_l3_traffic`, `acl_json_config_v6_l3_traffic`). 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L8-L9】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L205-L214】
* **Traffic Stream Parameters:** Derived from ACL rule attributes via `acl_utils.get_args_l3`, combined with TG port handles. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L126-L167】
* **Not Specified:** No explicit references to `testbed.yaml`, `group_vars`, or CLI parameters beyond implicit topology handles; therefore specific sources for variables other than hardcoded values and ACL configs are not specified.

## 6. External Libraries and Roles
* **`spytest` modules (`st`, `tgapi`, `SpyTestDict`):** Core framework for logging, topology handling, and TG interactions. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L5-L7】
* **`apis.qos.acl`:** Manages ACL configuration, deletion, and counter retrieval. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L8】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L95-L113】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L218-L266】
* **`tests.qos.acl.acl_json_config`:** Supplies predefined ACL table and rule structures used to build JSON config. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L8】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L205-L214】
* **`tests.qos.acl.acl_utils`:** Utility functions for ACL testing (argument translation, reporting). 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L9】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L126-L167】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L283-L299】
* **`apis.switching.portchannel`:** Creates and manages port-channel interfaces. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L10】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L84-L111】
* **`apis.routing.ip`:** Configures IP/IPv6 interfaces and static routes. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L11】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L112-L146】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L229-L252】
* **`apis.routing.arp`:** Handles ARP/NDP entries and table management. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L12】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L147-L180】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L252-L267】
* **`apis.system.basic`:** Retrieves interface MAC addresses for traffic stream configuration. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L13】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L218-L223】
* **`utilities.common` & `utilities.parallel`:** Provide helper utilities for parallel execution and exception handling. 【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L14-L16】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L84-L111】【F:spytest/tests/qos/acl/test_acls_l3_forwarding.py†L101-L113】

