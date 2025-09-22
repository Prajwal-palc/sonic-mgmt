# spytest/tests/sanity/test_sanity_l2.py – QA Readout

## 1. Topology
- **Required topology:** The module-level autouse fixture enforces at least four links between DUT1 and DUT2, three traffic-generator links to DUT1, and one traffic-generator link to DUT2 (`D1D2:4`, `D1T1:3`, `D2T1:1`).【F:spytest/tests/sanity/test_sanity_l2.py†L14-L17】
- **Inference method:** `st.ensure_min_topology` validates the inventory against these patterns before the tests execute, so the scenario assumes a dual-DUT setup with a traffic generator connected to both devices.

## 2. Overall Purpose
- The suite builds a Layer-2 baseline by verifying port-channel creation/deletion, VLAN membership behavior, L2 forwarding (tagged and untagged), and MAC learning/mobility both within and across VLANs on a two-DUT topology with connected traffic generators.【F:spytest/tests/sanity/test_sanity_l2.py†L23-L32】【F:spytest/tests/sanity/test_sanity_l2.py†L65-L200】【F:spytest/tests/sanity/test_sanity_l2.py†L480-L985】

## 3. Subtests and Rationale
### Within `test_base_line_portchannel_create_delete`
1. **Sub test 1 – Port-channel create/delete workflow:** Establishes LAGs/VLANs, verifies interface/link health, validates traffic and MAC learning over the new port-channel, and ensures extra port-channels can be created and removed without impacting traffic.【F:spytest/tests/sanity/test_sanity_l2.py†L133-L246】 This confirms baseline resiliency of port-channel provisioning.
2. **Sub test 2 – Random link flap:** Flaps individual member links and confirms the port-channel and member states remain up.【F:spytest/tests/sanity/test_sanity_l2.py†L247-L284】 Validates LAG stability under member disruptions.
3. **Sub test 3 – Tagged forwarding on port-channel:** Re-runs tagged traffic and validates counters after the setup to confirm data-plane forwarding across the LAG.【F:spytest/tests/sanity/test_sanity_l2.py†L285-L314】 Ensures no regression post-initial configuration.
4. **Sub test 4 – VLAN port association:** Clears VLANs, recreates tagged membership on port-channel and TG ports, then validates traffic and MAC learning.【F:spytest/tests/sanity/test_sanity_l2.py†L316-L375】 Checks VLAN membership persistence and traffic forwarding.
5. **Sub test 5 – Port move between VLANs:** Configures untagged VLAN membership on the port-channel and verifies traffic/MAC learning, demonstrating untagged access operation across the LAG.【F:spytest/tests/sanity/test_sanity_l2.py†L377-L439】

### Within `test_base_line_vlan_create_delete_and_mac_learning_with_bum`
6. **Sub test 8 – VLAN create/delete with BUM learning:** Builds tagged VLAN membership on multiple TG ports, sends broadcast/unknown/multicast traffic, verifies MAC learning and traffic distribution.【F:spytest/tests/sanity/test_sanity_l2.py†L512-L664】 Establishes baseline BUM forwarding behavior.
7. **Sub test 10 – MAC move within a VLAN:** Clears MACs, sets aging time, learns a MAC on one port, then re-learns it on another and verifies forwarding, demonstrating intra-VLAN MAC mobility handling.【F:spytest/tests/sanity/test_sanity_l2.py†L666-L812】
8. **Sub test 11 – MAC move across VLANs:** After success of prior subtests, learns a MAC in one VLAN and moves it to another VLAN/port, validating cross-VLAN MAC re-learning and forwarding expectations.【F:spytest/tests/sanity/test_sanity_l2.py†L814-L960】

## 4. Dependencies / Prerequisites
- **Fixtures:** Module-level `sanity_l2_module_hooks` (enforces topology) and function-level `sanity_l2_func_hooks` (placeholder for per-test setup/teardown).【F:spytest/tests/sanity/test_sanity_l2.py†L14-L21】
- **Topology constraints:** Dual-DUT with required link counts to traffic generators as enforced by `st.ensure_min_topology`.【F:spytest/tests/sanity/test_sanity_l2.py†L14-L17】
- **Stored state:** Shared `base_line_final_result` dict persists outcomes across dependent tests.【F:spytest/tests/sanity/test_sanity_l2.py†L23-L32】
- **Test completion wrappers:** Standalone test functions at the end report pass/fail based on stored results, enforcing dependency ordering via `pytest.mark.depends`.【F:spytest/tests/sanity/test_sanity_l2.py†L480-L548】【F:spytest/tests/sanity/test_sanity_l2.py†L987-L1018】

## 5. Key Inputs
- **Testbed-driven variables:** `st.get_testbed_vars()` supplies DUT/TG interface identifiers defined in the testbed inventory (e.g., `vars.D1D2P1`, `vars.T1D1P1`).【F:spytest/tests/sanity/test_sanity_l2.py†L67-L89】【F:spytest/tests/sanity/test_sanity_l2.py†L528-L546】
- **Randomized VLAN IDs:** `random_vlan_list()` populates VLAN identifiers for isolation between runs.【F:spytest/tests/sanity/test_sanity_l2.py†L35-L36】【F:spytest/tests/sanity/test_sanity_l2.py†L548-L556】
- **Traffic generator handles:** `tgapi.get_handle_byname` retrieves TG ports defined in the testbed configuration.【F:spytest/tests/sanity/test_sanity_l2.py†L81-L84】【F:spytest/tests/sanity/test_sanity_l2.py†L558-L565】
- **Static defaults:** `data` structure holds default MAC addresses, traffic rates, timers, and control flags initialized at module scope and overridden per subtest as needed.【F:spytest/tests/sanity/test_sanity_l2.py†L34-L47】【F:spytest/tests/sanity/test_sanity_l2.py†L521-L564】
- **Not specified:** No explicit references to group_vars or CLI parameters were found.

## 6. External Libraries / APIs
- **`spytest` core:** `st`, `tgapi`, `SpyTestDict` for logging, topology utilities, traffic generator control, and shared data structures.【F:spytest/tests/sanity/test_sanity_l2.py†L3】【F:spytest/tests/sanity/test_sanity_l2.py†L52-L58】
- **Switching/VLAN/MAC APIs:** Modules under `apis.switching` and `apis.system.interface` provide configuration and verification helpers for port-channels, VLANs, MAC tables, and interfaces.【F:spytest/tests/sanity/test_sanity_l2.py†L5-L10】
- **Routing/IP helpers:** `apis.routing.ip` for IP cleanup used during setup/teardown.【F:spytest/tests/sanity/test_sanity_l2.py†L11】【F:spytest/tests/sanity/test_sanity_l2.py†L91-L95】【F:spytest/tests/sanity/test_sanity_l2.py†L972-L1000】
- **Utilities:** `utilities.utils` and `utilities.common` for MAC list generation, table printing, VLAN selection, and list handling.【F:spytest/tests/sanity/test_sanity_l2.py†L8】【F:spytest/tests/sanity/test_sanity_l2.py†L12】【F:spytest/tests/sanity/test_sanity_l2.py†L204-L210】
- **ASIC debugging:** `apis.common.asic` used in `debug_cmds` to dump hardware tables when traffic validation fails.【F:spytest/tests/sanity/test_sanity_l2.py†L10】【F:spytest/tests/sanity/test_sanity_l2.py†L52-L58】
