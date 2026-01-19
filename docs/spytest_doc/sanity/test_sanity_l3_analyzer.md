# test_sanity_l3.py Analyzer

## 1. Topology Type
- **Identified Topology:** Dual DUT with one TGEN link per DUT (`D1D2:1`, `D1T1:1`, `D2T1:1`).
- **Inference:** The module-level fixture `sanity_l3_module_hooks` calls `st.ensure_min_topology("D1D2:1", "D1T1:1", "D2T1:1")`, explicitly requesting one interconnect between the two DUTs and one traffic generator connection to each DUT. This confirms a two-DUT L3 topology where DUT1 and DUT2 are connected to each other and to a traffic generator.【F:spytest/tests/sanity/test_sanity_l3.py†L86-L94】

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate L3 forwarding sanity when transitioning an interface on DUT1 between routed (Layer 3) and switched (Layer 2 VLAN) modes while ensuring both IPv4 and IPv6 connectivity and static routes remain functional.
- **Broader Context:** Within the SONiC/SpyTest regression suite, this test ensures that basic dual-DUT setups can maintain routing reachability through interface role changes, covering L3 forwarding, static routing, ARP/NDP handling, and traffic generator connectivity in mixed IPv4/IPv6 environments.【F:spytest/tests/sanity/test_sanity_l3.py†L41-L161】

## 3. Detailed Breakdown of Sub-Testcases
### `test_l2_to_l3_port`
- **Intent & Logic:**
  - Starts from the module fixture’s baseline where routed links and static routes are configured on both DUTs and TG interfaces are prepared.
  - Converts the inter-DUT link on DUT1 (`vars.D1D2P1`) from a Layer 3 interface into a VLAN access port by deleting IP addresses and static routes, creating VLAN 10, assigning IP (IPv4/IPv6) addresses to the SVI, and re-adding the necessary IPv6 static route.【F:spytest/tests/sanity/test_sanity_l3.py†L109-L135】
  - Waits for SONiC to stabilize (`st.vsonic_wait(30)`), then verifies end-to-end IPv4/IPv6 reachability from DUT1 to DUT2’s TGEN-facing network using the traffic generator handles.【F:spytest/tests/sanity/test_sanity_l3.py†L136-L145】
  - Clears ARP and NDP tables on both DUTs to ensure neighbor discovery is repopulated, then validates connectivity from DUT2 back to DUT1’s interconnect addresses for both protocol families.【F:spytest/tests/sanity/test_sanity_l3.py†L147-L157】
  - Reverts configuration by removing the VLAN membership/SVI and restoring the original routed configuration on `vars.D1D2P1`, then revalidates IPv4 connectivity to confirm the system returns to the L3 baseline.【F:spytest/tests/sanity/test_sanity_l3.py†L159-L173】
  - Reports pass only if all intermediate validations succeed; otherwise fails the sanity test.【F:spytest/tests/sanity/test_sanity_l3.py†L175-L179】
- **Why It Matters:** Ensures that toggling between L2 and L3 roles on a critical inter-DUT link does not break routing, validating configuration resilience and dual-stack reachability—key for SONiC deployments where interfaces may be repurposed dynamically.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `sanity_l3_module_hooks` (module-scoped, autouse) performs topology validation, default configuration cleanup, traffic generator setup, DUT routing configuration, and baseline IPv4 reachability checks. It also ensures post-test cleanup restoring DUT state.【F:spytest/tests/sanity/test_sanity_l3.py†L86-L108】
  - `sanity_l3_func_hooks` (function-scoped, autouse) placeholder fixture currently providing symmetry with the framework requirements (no additional logic).【F:spytest/tests/sanity/test_sanity_l3.py†L118-L121】
- **Helper Functions:**
  - `config_dut1`, `config_dut2`, `pre_test_l3_fwding`, `post_test_l3_fwding`, `tg_config`, and `ping` orchestrate configuration, traffic generator control, and reachability validation leveraged by fixtures and the test.【F:spytest/tests/sanity/test_sanity_l3.py†L41-L115】
- **Topology Constraints:** Requires two DUTs with traffic generator connections per `ensure_min_topology` call and the ability to manipulate VLAN/L3 configurations on the interconnect ports.【F:spytest/tests/sanity/test_sanity_l3.py†L86-L108】

## 5. Key Inputs and Parameters
- **Static Data (`data` object):** Contains IPv4/IPv6 addresses, masks, static route prefixes, traffic generator rates/lengths, and timing parameters controlling waits and thresholds. These values drive interface configuration and traffic generation behavior during the test.【F:spytest/tests/sanity/test_sanity_l3.py†L13-L40】
- **Traffic Generator Handles:** Derived via `tgapi.get_handle_byname("T1D1P1")` and `tgapi.get_handle_byname("T1D2P1")` to configure emulated hosts and bidirectional traffic streams for validation.【F:spytest/tests/sanity/test_sanity_l3.py†L43-L82】
- **Topology Variables (`vars.*`):** Provided by SpyTest’s topology abstraction to reference DUT interfaces such as `vars.D1T1P1`, `vars.D1D2P1`, etc. Precise values depend on `testbed.yaml` but are abstracted in the test—actual mappings are not specified within the file.【F:spytest/tests/sanity/test_sanity_l3.py†L52-L108】

## 6. External Libraries and Modules
- **`pytest`:** Enables fixture definitions, markers, and test discovery for the SpyTest framework.【F:spytest/tests/sanity/test_sanity_l3.py†L1-L3】
- **SpyTest Utilities (`SpyTestDict`, `st`, `tgapi`):** Provide shared data structures, logging, topology management, traffic generator access, and utility functions essential for orchestrating test steps.【F:spytest/tests/sanity/test_sanity_l3.py†L3-L112】
- **`apis.common.wait`, `apis.routing.ip`, `apis.switching.vlan`, `apis.switching.portchannel`, `apis.routing.arp`:** SONiC/SpyTest API wrappers delivering wait helpers, IP interface management, VLAN and port-channel operations, and ARP/NDP table controls. They abstract CLI/REST interactions required for configuring and validating the DUTs.【F:spytest/tests/sanity/test_sanity_l3.py†L5-L10】

## 7. Unspecified Items
- Specific mappings for `vars.*` interfaces, traffic generator port physical details, and exact threshold usage logic beyond the configured constants are **Not specified** in this test file.
