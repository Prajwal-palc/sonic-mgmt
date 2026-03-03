# QoS Save & Reboot Test Overview

## 1. Topology
* **Topology type:** Single DUT with one traffic-generator link (D1T1:1).
* **Inference:** The module-level fixture calls `st.ensure_min_topology("D1T1:1")`, explicitly requiring one device-under-test with a single connected traffic generator port before configuring QoS features.

## 2. Overall Purpose
* Validates that a suite of QoS configurations (CoS queue mapping, IPv4/IPv6 ACLs, WRED, and ECN profiles) persist across a `config save` followed by a device reboot, confirming that settings stored in `config_db` are restored into the running configuration after reboot.

## 3. Subtests and Their Roles
* **Module setup (`qos_save_reboot_module_hooks`):**
  * Ensures the minimum topology is present and seeds all QoS features prior to validation.
  * Applies WRED and ECN configuration via `apply_wred_ecn_config` and verifies them (`wred_verify`, `ecn_verify`) so that pre- and post-reboot state can be compared.
  * Programs IPv4 and IPv6 ACL tables/rules (`ipv4_acl_config`, `ipv6_acl_config`) and verifies them in running config (`ipv4_acl_verify`, `ipv6_acl_verify`) to establish baseline expectations.
  * Configures the CoS TC-to-queue map (`cos_config`) and confirms it with `cos_config_verify`.
* **Test case `test_ft_qos_config_mgmt_verifying_config_with_save_reboot`:**
  * Executes `config save`, reboots the DUT, and re-runs all QoS verification helpers to ensure each feature survives the reboot.
  * Reports pass only when all QoS features (ACLs, CoS, WRED, ECN) remain present.
* **Helper UMF-based mapping functions (`pfc_PriorityQueue_Map`, `dot1p_to_tc_map`, `tc_to_dot1p_map`, `dscp_to_tc_map`, `tc_to_dscp_map`, `tc_to_queue_map`, `tc_to_pg_map`):**
  * Provide reusable utilities for configuring QoS maps through YANG/UMF APIs. Although not invoked directly in this test flow, they are part of the module and support extended scenarios involving QoS mapping persistence.

## 4. Dependencies & Prerequisites
* **Fixtures:** Autouse module fixture (`qos_save_reboot_module_hooks`) for pre/post configuration and cleanup; function-level fixture (`qos_save_reboot_func_hooks`) reserved for per-test customizations (currently no-ops).
* **Libraries/Modules:**
  * `spytest.st`, `SpyTestDict` for logging, topology discovery, and shared state.
  * QoS/ACL/system API modules (`apis.qos.cos`, `apis.qos.qos`, `apis.qos.acl`, `apis.system.reboot`, `apis.system.switch_configuration`).
  * `tests.qos.wred_ecn_config_json` for canned WRED/ECN data.
  * `utilities.common.utils` for concurrent execution helpers.
  * Optional YANG UMF bindings (`apis.yang.codegen.messages.qos`) for advanced QoS map manipulation.
* **Topology constraints:** One SONiC DUT with at least one front-panel port connected to a traffic generator (ensured by `D1T1:1`). Device must support QoS, ACL, WRED, and ECN features and allow config-save/reboot operations.

## 5. Key Inputs
* **Static defaults:** QoS identifiers, ACL names/rules, IP prefixes, priorities, and CoS mappings defined in the local `data = SpyTestDict()` block.
* **Topology-derived values:** DUT alias (`vars.D1`) and port (`vars.D1T1P1`) returned from `st.ensure_min_topology`.
* **WRED/ECN profiles:** Pulled from `tests.qos.wred_ecn_config_json.init_vars(vars)` and applied to the DUT.
* **Other sources:** No additional testbed YAML, group_vars, or CLI parameters are referenced beyond the topology lookup.

## 6. External Libraries & Roles
* **`pytest`:** Provides fixture and test orchestration.
* **`json`:** Used to serialize QoS profile dictionaries before pushing them with `st.apply_json2`.
* **SpyTest framework modules (`spytest`, `utilities.common.utils`):** Handle logging, topology management, and concurrent execution.
* **SONiC QoS API modules (`apis.*`):** Abstract the device configuration and verification steps for QoS, ACL, and system reboot features.
* **UMF QoS models (`apis.yang.codegen.messages.qos`):** Supply typed YANG objects for configuring QoS mapping tables via management interfaces when invoked.
