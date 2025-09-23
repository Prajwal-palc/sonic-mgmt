# Test Case Analysis: `spytest/tests/qos/test_qos_save_reboot.py`

## 1. Topology Type
- **Declared topology:** The module-level autouse fixture calls `st.ensure_min_topology("D1T1:1")`, which requires one DUT (`D1`) connected to a single traffic generator/Test port (`T1`) with at least one link (`:1`).
- **Inference:** The returned `vars` handle is later used as `vars.D1` for the device and `vars.D1T1P1` for the connected port when applying ACLs, confirming the single-DUT, single-link testbed requirement.

## 2. Overall Test Case Purpose
- **High-level validation:** The test verifies that a collection of QoS-related configurations—WRED/ECN profiles, IPv4 and IPv6 ACLs, and class-of-service (COS) queue mappings—persist correctly after issuing a `config save` followed by a device reboot.
- **Context in SONiC/SpyTest:** Within SpyTest's QoS regression coverage, this scenario ensures that QoS control-plane settings survive across reboots by synchronizing from `config_db.json` back into the running configuration, validating SONiC's configuration management resilience for QoS features.

## 3. Detailed Breakdown of Sub-Testcases
- **Fixture `qos_save_reboot_module_hooks`:**
  - Autouse, runs once per module. Establishes the minimum topology, seeds the device with WRED+ECN JSON configuration (via `apply_wred_ecn_config`), creates IPv4/IPv6 ACL tables and rules, and programs COS mappings. Each configuration block is immediately verified in the running config before any test executes.
  - Teardown clears QoS and ACL configurations to return the DUT to a clean state.
  - Importance: Provides the baseline QoS state whose persistence the main test later evaluates.
- **Fixture `qos_save_reboot_func_hooks`:**
  - Autouse, function scope. Currently acts as a placeholder without additional logic.
  - Importance: Offers an extension point for future per-test setup/teardown without affecting current behavior.
- **Helper functions:**
  - `cos_config` / `cos_config_verify`: Program and validate `TC_TO_QUEUE_MAP` entries.
  - `ipv4_acl_config` / `ipv4_acl_verify`, `ipv6_acl_config` / `ipv6_acl_verify`: Manage ACL tables and rules for IPv4/IPv6 traffic.
  - `apply_wred_ecn_config`, `wred_verify`, `ecn_verify`: Push WRED/ECN JSON and ensure correct running-config reflection.
  - `pfc_PriorityQueue_Map`, `dot1p_to_tc_map`, `tc_to_dot1p_map`, `dscp_to_tc_map`, `tc_to_dscp_map`, `tc_to_queue_map`, `tc_to_pg_map`: Utility wrappers around UMF QoS YANG models for CRUD operations on various QoS mapping tables. Although unused in the current test, they provide reusable building blocks for other QoS persistence scenarios.
- **Test `test_ft_qos_config_mgmt_verifying_config_with_save_reboot`:**
  - Executes `config save` on the DUT, triggers a reboot, and then re-runs the verification helpers to confirm that all previously configured QoS objects reappear in the running configuration after the device returns.
  - Reports test success through `st.report_pass` upon completing all verifications.
  - Importance: Directly validates that saved QoS configurations are restored post-reboot, fulfilling the module’s persistence objective.

## 4. Dependencies and Prerequisites
- **Fixtures:** Autouse fixtures `qos_save_reboot_module_hooks` and `qos_save_reboot_func_hooks` must execute to prepare and clean up the environment.
- **Topology constraint:** Requires the `D1T1:1` topology, ensuring at least one SONiC DUT with a connected port used for ACL binding.
- **Libraries/Modules:** Relies on SpyTest core (`st`), SpyTestDict, and multiple QoS/ACL/system API modules for configuration, verification, and reboot handling.
- **YANG support:** The optional `umf_qos` import enables the helper functions for QoS map manipulation; if unavailable, those helpers would need alternative implementations.

## 5. Key Inputs and Parameters
- **Static data dictionary (`data`):** Contains QoS object names, ACL identifiers, IP addresses/masks, actions, and priority values used consistently across setup and verification steps.
- **Topology handle (`vars`):** Derived from `st.ensure_min_topology`, providing device identifiers (`vars.D1`) and port aliases (`vars.D1T1P1`).
- **WRED/ECN configuration (`wred_config.init_vars` output):** Supplies JSON payloads required to program WRED and ECN profiles.
- **PyTest marks:** `@pytest.mark.savereboot`, `@pytest.mark.community`, and inventory annotations categorize the scenario for regression selection, although they do not alter runtime behavior.

## 6. External Libraries and Modules
- **`pytest`:** Supplies the fixture and marking framework.
- **`json`:** Used to serialize the WRED/ECN configuration payload prior to applying it through SpyTest.
- **`spytest.st` and `SpyTestDict`:** Core SpyTest utilities for logging, topology management, configuration application, and reporting.
- **`apis.system.reboot` (`rb_obj`):** Provides the `config_save` helper invoked before reboot.
- **`apis.qos.cos` (`cos_obj`), `apis.qos.qos` (`qos_obj`), `apis.qos.acl` (`acl_obj`):** Encapsulate SONiC QoS and ACL configuration APIs used throughout setup and teardown.
- **`apis.system.switch_configuration` (`sconf_obj`):** Enables running-config verification checks for QoS objects.
- **`utilities.common` (`utils`):** Supplies `exec_all` for parallel execution when applying JSON configuration.
- **`tests.qos.wred_ecn_config_json` (`wred_config`):** Module containing canned WRED/ECN JSON templates.
- **`apis.yang.codegen.messages.qos` (`umf_qos`):** Optional UMF YANG client enabling helper functions for QoS map CRUD operations.

## 7. Unspecified Items
- **Exact testbed hardware details beyond the D1T1:1 abstraction:** Not specified.
- **Specific config_db entries generated by the helper functions beyond the verified keys:** Not specified.
- **Traffic validation or data-plane checks:** Not specified within this file.
