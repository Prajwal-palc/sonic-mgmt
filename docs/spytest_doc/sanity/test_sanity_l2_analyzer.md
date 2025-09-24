# L2 Sanity Test Analyzer

## 1. Topology type
* **Topology requirement:** The module-level fixture enforces a dual-DUT testbed with four inter-DUT links, three traffic-generator connections to D1, and one traffic-generator connection to D2 (`"D1D2:4", "D1T1:3", "D2T1:1"`).【F:spytest/tests/sanity/test_sanity_l2.py†L14-L17】
* **Inference:** Subsequent references to `vars.D1`, `vars.D2`, and TG ports (`vars.T1D1P1`, etc.) confirm that the scenario exercises two SONiC switches aggregated by a test generator, validating port-channel and VLAN behavior end-to-end across the dual-DUT topology.【F:spytest/tests/sanity/test_sanity_l2.py†L75-L132】【F:spytest/tests/sanity/test_sanity_l2.py†L541-L570】

## 2. Overall test case purpose
* The test file validates L2 baseline functionality for SONiC by orchestrating port-channel creation/deletion, VLAN membership, L2 forwarding, MAC learning, and MAC move workflows under various conditions. The main `test_base_line_portchannel_create_delete` and `test_base_line_vlan_create_delete_and_mac_learning_with_bum` routines run multiple gated sub-tests that provision port-channels/VLANs, apply traffic from the TGen, and confirm MAC table and traffic correctness.【F:spytest/tests/sanity/test_sanity_l2.py†L65-L476】【F:spytest/tests/sanity/test_sanity_l2.py†L537-L994】
* These checks ensure SpyTest’s SONiC baseline covers control-plane stability (port oper status, MAC aging), data-plane forwarding (tagged/untagged VLAN traffic, BUM replication), and resilience (link flap, MAC moves) on hardware or virtual topologies before running higher-level suites.【F:spytest/tests/sanity/test_sanity_l2.py†L133-L452】【F:spytest/tests/sanity/test_sanity_l2.py†L580-L971】

## 3. Detailed breakdown of sub-testcases
### `test_base_line_portchannel_create_delete`
This orchestrates five sequential sub-tests whose outcomes are recorded in `base_line_final_result`.
1. **Sub test 1 – Port-channel bring-up, traffic, MAC learning, and create/delete churn:**
   * Brings all member and TG interfaces up, builds port-channels/VLANs on both DUTs, and verifies port-channel state.【F:spytest/tests/sanity/test_sanity_l2.py†L133-L179】
   * Generates bidirectional VLAN-tagged traffic, confirms lossless forwarding, validates MAC learning, then creates/deletes additional port-channels and re-checks traffic to ensure no regressions.【F:spytest/tests/sanity/test_sanity_l2.py†L191-L248】
   * Establishes the golden baseline for later sub-tests; failure halts downstream checks.
2. **Sub test 2 – Random link flap on port-channel members:**
   * Sequentially shuts/no-shuts each D2 member, ensuring the aggregated interface returns to `up` state without error.【F:spytest/tests/sanity/test_sanity_l2.py†L258-L281】
   * Validates resiliency of LAG after disturbances.
3. **Sub test 3 – L2 tagged forwarding:**
   * Re-runs traffic and verifies counters without reconfiguration, confirming sustained forwarding after prior operations.【F:spytest/tests/sanity/test_sanity_l2.py†L293-L313】
4. **Sub test 4 – VLAN/port association refresh:**
   * Clears VLAN config, re-adds tagged members to port-channel and TG ports, validates VLAN programming, then confirms traffic and MAC table entries rebuild correctly.【F:spytest/tests/sanity/test_sanity_l2.py†L322-L380】
5. **Sub test 5 – Move ports between VLANs:**
   * Re-creates VLAN membership as untagged, verifies port-channel/TG status, runs traffic, and checks MAC learning under untagged mode to ensure consistency when migrating ports across VLAN types.【F:spytest/tests/sanity/test_sanity_l2.py†L389-L445】

After all sub-tests, results are logged and cleanup clears IP, VLAN, and port-channel state before reporting overall status.【F:spytest/tests/sanity/test_sanity_l2.py†L454-L476】

### `test_base_line_random_link_flap_portchannel`
* Consumes the stored outcome of Sub test 2 to report pass/fail status, acting as a summary node for dependency chains in larger SpyTest plans.【F:spytest/tests/sanity/test_sanity_l2.py†L479-L491】

### `test_base_line_l2_taggged_forwarding_with_portchannel`
* Mirrors Sub test 3’s result reporting so other suites can depend on tagged forwarding validation without rerunning the full setup.【F:spytest/tests/sanity/test_sanity_l2.py†L494-L506】

### `test_base_line_vlan_port_association`
* Emits the status from Sub test 4, enabling granular gating for VLAN membership sanity across suites.【F:spytest/tests/sanity/test_sanity_l2.py†L509-L521】

### `test_base_line_port_move_from_vlan_a_to_vlan_b`
* Surfaces Sub test 5 outcome so dependent flows know whether VLAN migration succeeded.【F:spytest/tests/sanity/test_sanity_l2.py†L524-L534】

### `test_base_line_vlan_create_delete_and_mac_learning_with_bum`
This routine executes three additional sub-tests on a single DUT topology with multiple TG ports.
1. **Sub test 8 – VLAN creation and BUM forwarding:**
   * Creates a VLAN, attaches three TG ports as tagged members, and drives broadcast/multicast/unknown-unicast traffic to verify flooding and MAC learning on all receivers.【F:spytest/tests/sanity/test_sanity_l2.py†L580-L707】
2. **Sub test 10 – MAC move within a single VLAN:**
   * Clears the MAC table, disables aging, learns a MAC on one port, then sends the same source from a second port to ensure the entry moves; final traffic from a third port checks that only the updated location receives frames.【F:spytest/tests/sanity/test_sanity_l2.py†L718-L818】
3. **Sub test 11 – MAC move across VLANs:**
   * Adds a second VLAN, repeats MAC move workflow where the MAC transitions between VLAN contexts, and validates traffic steering before and after moving the MAC to the alternate VLAN.【F:spytest/tests/sanity/test_sanity_l2.py†L823-L964】

The test prints aggregated results, performs cleanup, and reports the parent status for downstream dependencies.【F:spytest/tests/sanity/test_sanity_l2.py†L973-L994】

### `test_base_line_mac_move_single_vlan`
* Reports Sub test 10 status for dependency tracking in other SpyTest collections.【F:spytest/tests/sanity/test_sanity_l2.py†L997-L1007】

### `test_base_line_mac_move_across_vlans`
* Reports Sub test 11 status for dependency tracking.【F:spytest/tests/sanity/test_sanity_l2.py†L1010-L1020】

### Helper function `debug_cmds`
* Provides troubleshooting support by dumping ASIC VLAN/L2/trunk tables on requested DUTs when traffic validation fails.【F:spytest/tests/sanity/test_sanity_l2.py†L52-L58】

## 4. Dependencies and prerequisites
* **Fixtures:** Module-level `sanity_l2_module_hooks` enforces the minimum topology, while the function-level hook currently acts as a placeholder for per-test setup/teardown.【F:spytest/tests/sanity/test_sanity_l2.py†L14-L21】
* **Shared state:** The global `base_line_final_result` dictionary tracks outcomes across sub-tests so subsequent wrapper tests can report without rerunning heavy setups.【F:spytest/tests/sanity/test_sanity_l2.py†L23-L32】
* **Traffic generator handles:** Each major test acquires TG port handles via `tgapi.get_handle_byname`, requiring those names to exist in `testbed.yaml` / topology configuration.【F:spytest/tests/sanity/test_sanity_l2.py†L81-L116】【F:spytest/tests/sanity/test_sanity_l2.py†L566-L570】
* **Cleanup routines:** IP, VLAN, and port-channel configurations are cleared before and after test blocks to guarantee deterministic starting conditions.【F:spytest/tests/sanity/test_sanity_l2.py†L91-L95】【F:spytest/tests/sanity/test_sanity_l2.py†L454-L468】【F:spytest/tests/sanity/test_sanity_l2.py†L572-L576】【F:spytest/tests/sanity/test_sanity_l2.py†L982-L986】

## 5. Key inputs and parameters
* **Dynamic test data:** `SpyTestDict` `data` stores VLAN IDs, MAC addresses, traffic rates, wait timers, and flags such as `clear_parallel` that influence TG configuration, verification delays, and cleanup concurrency.【F:spytest/tests/sanity/test_sanity_l2.py†L34-L47】
* **Topology-specific members:** During port-channel tests, `data.dut1_lag_members`, `data.dut2_lag_members`, and `topology` structure define the interfaces under test.【F:spytest/tests/sanity/test_sanity_l2.py†L75-L90】
* **BUM and MAC move parameters:** Additional attributes such as `data.tagged_members`, `data.tagged_members_1`, `data.tg_con_interface`, and MAC patterns drive the VLAN/MAC learning scenarios.【F:spytest/tests/sanity/test_sanity_l2.py†L541-L570】
* **Sub-test toggles:** Local flags (`sub_test_1`…`sub_test_5`, `sub_test_8`, `sub_test_10`, `sub_test_11`) allow selective execution when needed.【F:spytest/tests/sanity/test_sanity_l2.py†L68-L73】【F:spytest/tests/sanity/test_sanity_l2.py†L542-L545】

## 6. External libraries and modules
* **`spytest` framework (`st`, `tgapi`, `SpyTestDict`):** Provides logging, DUT/testbed access, traffic-generator abstraction, and shared dict utilities.【F:spytest/tests/sanity/test_sanity_l2.py†L3】
* **Switching APIs:** `apis.switching.portchannel`, `apis.switching.vlan`, `apis.switching.mac` offer helper functions for configuring and verifying SONiC L2 features.【F:spytest/tests/sanity/test_sanity_l2.py†L5-L7】
* **System and routing helpers:** `apis.system.interface` manages interface admin state and counters; `apis.routing.ip` clears IP configuration; `apis.common.asic` exposes ASIC dump utilities for debugging.【F:spytest/tests/sanity/test_sanity_l2.py†L8-L11】【F:spytest/tests/sanity/test_sanity_l2.py†L52-L58】
* **Utility functions:** `utilities.utils` and `utilities.common` modules supply MAC address generation, VLAN randomization, formatting, and list handling utilities used across sub-tests.【F:spytest/tests/sanity/test_sanity_l2.py†L8】【F:spytest/tests/sanity/test_sanity_l2.py†L12】
* **PyTest markers:** Standard `pytest` and SpyTest markers categorize the tests for sanity/community suites and express dependencies (`@pytest.mark.depends`).【F:spytest/tests/sanity/test_sanity_l2.py†L1】【F:spytest/tests/sanity/test_sanity_l2.py†L61-L64】【F:spytest/tests/sanity/test_sanity_l2.py†L479-L535】【F:spytest/tests/sanity/test_sanity_l2.py†L997-L1013】

## 7. Unspecified items
* Mapping of `vars.*` identifiers to physical ports, specific hardware models, and external configuration files are **Not specified** within this test file.
* Any prerequisite services or daemons (e.g., LLDP, spanning-tree state) beyond the enforced topology are **Not specified**.
