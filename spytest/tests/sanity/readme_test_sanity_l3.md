# Test Analysis: `test_sanity_l3`

## 1. Topology Type
* **Topology:** Two-DUT L3 topology with traffic generator connections (D1-D2 interlink, D1-T1, D2-T1).
* **Inference:** The module fixture invokes `st.ensure_min_topology("D1D2:1", "D1T1:1", "D2T1:1")`, requiring one link between DUT1 and DUT2 and one traffic-generator link from each DUT to the TGEN.【F:spytest/tests/sanity/test_sanity_l3.py†L116-L130】

## 2. Overall Test Purpose
* Validates IPv4/IPv6 forwarding continuity when converting a routed inter-DUT interface into an access VLAN member and then restoring it to routed mode, ensuring both directions of traffic and static routes survive the transitions.【F:spytest/tests/sanity/test_sanity_l3.py†L134-L213】

## 3. Subtests and Their Roles
1. **Module setup (`sanity_l3_module_hooks`):**
   * Clears existing L2/L3 configurations, normalizes traffic generator rate, configures DUT interfaces/static routes, and brings up traffic generator streams. Also validates initial TGEN-based IPv4 connectivity from both DUTs. Ensures a clean baseline and functioning L3 paths before the functional test begins.【F:spytest/tests/sanity/test_sanity_l3.py†L41-L130】
2. **Test `test_l2_to_l3_port`:**
   * **a. Convert routed port to VLAN:** Deletes L3 config on D1-D2 link, creates VLAN interface with IPv4/IPv6 addresses, and re-adds static route to verify VLAN-based routing setup.【F:spytest/tests/sanity/test_sanity_l3.py†L144-L166】
   * **b. VLAN membership and verification:** Adds D1D2 physical port into VLAN and confirms VLAN membership to ensure L2 domain established.【F:spytest/tests/sanity/test_sanity_l3.py†L167-L170】
   * **c. Forwarding validation from DUT1:** Runs IPv4 and IPv6 pings from DUT1 toward DUT2/TGEN side to confirm traffic continuity after VLAN conversion.【F:spytest/tests/sanity/test_sanity_l3.py†L174-L186】
   * **d. Clear ARP/NDP caches:** Flushes neighbor tables on both DUTs to remove stale entries, ensuring subsequent tests exercise resolution through the new VLAN path.【F:spytest/tests/sanity/test_sanity_l3.py†L188-L196】
   * **e. Forwarding validation from DUT2:** Pings IPv4/IPv6 back toward DUT1 VLAN interface validating bidirectional reachability post-conversion.【F:spytest/tests/sanity/test_sanity_l3.py†L198-L204】
   * **f. Revert VLAN to routed port:** Removes VLAN membership/configuration and reconfigures routed interface, validating device can return to original state.【F:spytest/tests/sanity/test_sanity_l3.py†L206-L214】
   * **g. Final connectivity check:** Performs final ping from DUT1 to ensure routed restoration succeeded; reports pass/fail based on all validations.【F:spytest/tests/sanity/test_sanity_l3.py†L214-L215】
3. **Module teardown (`post_test_l3_fwding` via fixture):**
   * Reverts DUT configurations back to initial routed state and displays VLAN configuration for sanity; ensures environment is clean post-test.【F:spytest/tests/sanity/test_sanity_l3.py†L85-L114】

## 4. Dependencies and Prerequisites
* **Fixtures:** `sanity_l3_module_hooks` (module-scoped autouse) for setup/teardown; `sanity_l3_func_hooks` (function-scoped autouse) placeholder.【F:spytest/tests/sanity/test_sanity_l3.py†L116-L141】
* **Topology Constraints:** Minimum topology with two DUTs and traffic generator as defined above.【F:spytest/tests/sanity/test_sanity_l3.py†L116-L123】
* **Traffic Generator:** Requires TG handles for ports `T1D1P1` and `T1D2P1` and ability to generate L3 streams.【F:spytest/tests/sanity/test_sanity_l3.py†L12-L83】

## 5. Key Inputs
* **Hardcoded test data:** IPv4/IPv6 addresses, prefixes, thresholds, and TG parameters stored in `data` dictionary within the test module.【F:spytest/tests/sanity/test_sanity_l3.py†L8-L38】
* **Topology variables:** Interface identifiers like `vars.D1T1P1`, `vars.D1D2P1`, etc., obtained from `st.ensure_min_topology(...)` resolving to entries from the loaded testbed (e.g., `testbed.yaml`).【F:spytest/tests/sanity/test_sanity_l3.py†L41-L130】
* **Traffic generator handles:** Retrieved dynamically via `tgapi.get_handle_byname(...)` based on topology definitions.【F:spytest/tests/sanity/test_sanity_l3.py†L40-L61】

## 6. External Libraries and Roles
* `pytest`: test framework and fixtures.【F:spytest/tests/sanity/test_sanity_l3.py†L1-L140】
* `spytest` modules (`SpyTestDict`, `st`, `tgapi`): provide test utilities, topology access, logging, and TG control.【F:spytest/tests/sanity/test_sanity_l3.py†L1-L140】
* `apis.common.wait`: wait helpers for SONiC apply delays.【F:spytest/tests/sanity/test_sanity_l3.py†L3-L213】
* `apis.routing.ip`: IPv4/IPv6 configuration and ping APIs.【F:spytest/tests/sanity/test_sanity_l3.py†L3-L215】
* `apis.switching.vlan`: VLAN configuration/verification helpers.【F:spytest/tests/sanity/test_sanity_l3.py†L3-L213】
* `apis.switching.portchannel`: Port-channel cleanup (used in setup).【F:spytest/tests/sanity/test_sanity_l3.py†L3-L83】
* `apis.routing.arp`: ARP/NDP table manipulation during verification.【F:spytest/tests/sanity/test_sanity_l3.py†L3-L196】

