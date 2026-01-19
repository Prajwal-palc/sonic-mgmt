# VRF Lite Test Case (spytest/tests/routing/VRF/test_vrf.py)

## 1. Topology
- The test initializes a dual-DUT testbed with a traffic generator, requiring four links between DUT1 and DUT2 and two links from each DUT to a shared traffic generator (`D1D2:4`, `D1T1:2`, `D2T1:2`).【F:spytest/tests/routing/VRF/test_vrf.py†L26-L46】
- Traffic generator handles are obtained from `tgen_obj_dict`, confirming the presence of a TG device shared across both DUTs.【F:spytest/tests/routing/VRF/test_vrf.py†L43-L46】
- Optional routed sub-interface mode is inferred via the `routed_sub_intf` argument, which swaps certain physical ports for dot1q subinterfaces when enabled.【F:spytest/tests/routing/VRF/test_vrf.py†L56-L73】

## 2. Overall Purpose
- Validates VRF Lite functionality across multiple VRFs by checking control-plane configuration (VRF bindings, interface addressing, ARP/NDP entries), dynamic routing (BGP sessions for physical, VLAN, and port-channel attachments), static route programming, route leaking, and persistence across reboots.【F:spytest/tests/routing/VRF/test_vrf.py†L89-L492】

## 3. Subtestcases
- **`test_VrfFun001_06`** – Confirms VRF creation, interface bindings, IP assignments, ARP/NDP population, and BGP session establishment across VRFs 101–103, covering base VRF functionality and interface associations.【F:spytest/tests/routing/VRF/test_vrf.py†L88-L179】
- **`test_VrfFun_26_27`** – Reconfigures iBGP/eBGP neighbors in VRF 101 and verifies IPv4 route learning to ensure BGP adjacency recovery after neighbor resets.【F:spytest/tests/routing/VRF/test_vrf.py†L182-L237】
- **`test_VrfFun_10_12_14`** – Disables BGP sessions and programs IPv4/IPv6 static routes with physical, VLAN, and port-channel next hops across VRFs, validating connectivity via ping and cleanup via fixture teardown.【F:spytest/tests/routing/VRF/test_vrf.py†L240-L341】
- **`test_VrfFun_20_24_25_32_33_44_45`** – Configures route-leak policies to import routes between VRFs 101–103 and verifies BGP session health, targeting VRF-to-VRF redistribution scenarios.【F:spytest/tests/routing/VRF/test_vrf.py†L344-L428】
- **`test_VrfFun_05_50`** – Uses retry-based BGP checks before and after a fast reboot to ensure overlapping VRF address spaces and VRF state survive system restart.【F:spytest/tests/routing/VRF/test_vrf.py†L431-L493】
- **Supporting helper `vrf_tc_26_27`** – Restores BGP neighbor configuration if `test_VrfFun_26_27` fails, ensuring subsequent tests have the expected baseline.【F:spytest/tests/routing/VRF/test_vrf.py†L182-L191】【F:spytest/tests/routing/VRF/test_vrf.py†L232-L237】

## 4. Dependencies / Prerequisites
- Module-scoped `prologue_epilogue` fixture automatically calls `initialize_topology()` and `loc_lib.vrf_base_config()` to provision the environment before any tests run.【F:spytest/tests/routing/VRF/test_vrf.py†L76-L81】
- `initialize_topology()` requires access to two DUTs and a traffic generator meeting the link requirements described above, enables BGP Docker routing mode, gathers hardware SKU data, performs RIF support checks, and records DUT/TG port mappings.【F:spytest/tests/routing/VRF/test_vrf.py†L26-L65】
- Per-test fixtures (`vrf_fixture_tc_10_12_14`, `vrf_fixture_tc_20_24_25_32_33_44_45`) perform cleanup such as removing static routes and resetting BGP to avoid cross-test contamination.【F:spytest/tests/routing/VRF/test_vrf.py†L240-L266】【F:spytest/tests/routing/VRF/test_vrf.py†L344-L364】
- Requires VRF helper library `vrf_lib` for baseline setup, BGP verifications, traffic generator configuration, and debug routines invoked throughout the tests.【F:spytest/tests/routing/VRF/test_vrf.py†L12-L14】【F:spytest/tests/routing/VRF/test_vrf.py†L176-L177】【F:spytest/tests/routing/VRF/test_vrf.py†L261-L266】

## 5. Key Inputs
- Static configuration data (VRF names, VLAN IDs, IP addresses, BGP ASNs, traffic parameters) are sourced from `vrf_vars.data`, a `SpyTestDict` populated with per-role lists for DUTs and traffic generators.【F:spytest/tests/routing/VRF/vrf_vars.py†L1-L114】
- Traffic generator handles and port objects come from the topology object returned by `st.ensure_min_topology`, tying into the active testbed definition (testbed.yaml).【F:spytest/tests/routing/VRF/test_vrf.py†L26-L46】
- CLI parameter `routed_sub_intf` toggles sub-interface mode for certain tests, altering interface names and expected bindings when provided at runtime.【F:spytest/tests/routing/VRF/test_vrf.py†L56-L73】

## 6. External Libraries
- SpyTest core utilities (`spytest`, `utilities.common`, `utilities.utils`) provide logging, argument parsing, concurrency helpers, and result reporting.【F:spytest/tests/routing/VRF/test_vrf.py†L9-L23】
- Routing/system API modules (`apis.routing.ip`, `apis.routing.vrf`, `apis.routing.bgp`, `apis.routing.arp`, `apis.system.basic`, `apis.system.reboot`) supply high-level configuration and verification calls for IP interfaces, VRFs, BGP neighbors, ARP/NDP tables, platform discovery, and reboot operations.【F:spytest/tests/routing/VRF/test_vrf.py†L15-L20】【F:spytest/tests/routing/VRF/test_vrf.py†L120-L170】【F:spytest/tests/routing/VRF/test_vrf.py†L206-L420】【F:spytest/tests/routing/VRF/test_vrf.py†L437-L486】
- Traffic generator access comes from `spytest.tgen.tg.tgen_obj_dict`, enabling port-handle retrieval for TG operations within the helper library.【F:spytest/tests/routing/VRF/test_vrf.py†L10-L46】
