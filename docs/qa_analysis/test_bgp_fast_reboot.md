# BGP Fast Reboot Test Case QA Notes

## 1. Topology Used in Viewer
- **Type:** Dual-DUT topology with a traffic generator that has two ports (one per AF).【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L42-L72】
- **Inference:** The module fixture requests `st.ensure_min_topology("D1D2:1", "D1T1:2")`, meaning the test needs one link between DUT1 and DUT2 and two links between DUT1 and a TGEN device (T1). That combination indicates a viewer topology showing two DUTs and a traffic generator with two test ports.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L42-L72】

## 2. Overall Test Case Purpose
- Validate that IPv4 and IPv6 BGP peering recovers after a fast reboot on the primary DUT. The flow configures eBGP between the two DUTs, iBGP sessions with the traffic generator, saves configuration, performs a fast reboot on DUT1, and confirms neighbor sessions return to Established state post-reboot.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L50-L300】

## 3. Subtestcases and Rationale
- **Module Autouse Fixture – Environment Preparation and Validation**: Sets the topology handles, enables IPv6 globally, programs IPv4/IPv6 interface addresses, creates both eBGP and iBGP relationships (including traffic generator emulation), and verifies neighbor establishment before any reboot. Ensuring adjacency stability prior to reboot is essential to prove that any subsequent loss of peering is due to the fast reboot step being exercised.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L42-L282】
  - IPv4 address configuration and verification guarantee the underlay connectivity required for BGPv4 sessions.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L50-L127】
  - IPv6 address configuration and verification (when enabled) prepare the DUTs for BGPv6 testing.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L56-L159】
  - BGP neighbor setup covers eBGP between DUTs and iBGP with traffic generator peers for both address families, so the reboot scenario exercises real routing adjacencies.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L61-L198】
  - Traffic-generator configuration creates emulated peers and advertised routes, ensuring TG participation in the BGP control plane.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L200-L239】
  - Pre-check functions `verify_v4_bgp_neigborship` and `verify_v6_bgp_neigborship` assert that all BGP sessions are Established before the reboot test runs.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L242-L282】
- **Test `test_ft_bgp_fast_reboot` – Fast Reboot Validation**: Enables Docker routing config mode, saves the running configuration, triggers a fast reboot on DUT1, and re-runs IPv4/IPv6 neighbor verification to prove that control plane recovery occurs as expected. Passing this subtest demonstrates that the fast reboot procedure preserves BGP functionality.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L285-L300】
- **Module Teardown (Fixture Yield Post-Section)**: Cleans up BGP, IP, VLAN, and port-channel configuration after the test, preventing residual state for subsequent suites.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L83-L90】

## 4. Dependencies and Prerequisites
- **Topology Constraints:** Requires two DUTs with at least one interconnection and two links from DUT1 to a traffic generator (T1) to satisfy `D1D2:1` and `D1T1:2` requirements.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L42-L72】
- **Fixtures:** Autouse module fixture `bgp_fast_reboot_module_hooks` handles setup/teardown; autouse function fixture placeholder exists (currently only yields).【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L39-L96】
- **Feature Check:** Wait timer extends if the DUT lacks `bgp-neighbotship-performance` feature support, implying compatibility considerations for platforms without the optimization.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L43-L44】
- **Traffic Generator Access:** Relies on `tgapi.get_handle_byname` for ports `T1D1P1` and `T1D1P2`, so those handles must be defined in the testbed inventory.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L200-L239】
- **IPv6 Support Flag:** `data.ipv6_support` toggles IPv6-related steps; defaults to True but could be overridden externally if needed.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L36-L79】

## 5. Key Inputs and Their Sources
- **Static Test Parameters:** Hard-coded in the module-level `SpyTestDict` (IP addresses, router IDs, ASNs, wait timers, TG route prefix). These constants drive all configuration commands.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L11-L37】
- **Topology Handles (`vars`):** Populated by `st.ensure_min_topology` using the active `testbed.yaml` inventory; provide device names, interface IDs, and traffic-generator port mappings consumed throughout the setup and verification helpers.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L42-L198】
- **Traffic Generator Handles:** Retrieved dynamically from `tgapi`, relying on matching names in the TG configuration section of the testbed definition.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L200-L239】
- **IPv6 Support Flag:** Could be influenced by CLI or group vars if set outside the test, determining whether IPv6 blocks execute; default remains True within the script.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L36-L79】
- **CLI/Group Vars:** No explicit parsing in this file; any overrides would have to come from the `SpyTestDict` or fixtures—otherwise not specified. Not specified.

## 6. External Libraries and Roles
- **`pytest`:** Provides fixture and marker annotations to structure setup, teardown, and the main test case.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L1-L95】
- **`spytest` utilities (`st`, `tgapi`, `SpyTestDict`):** `st` handles logging, topology discovery, command execution, waits, and reboot orchestration; `tgapi` supplies handles for traffic generator control; `SpyTestDict` stores shared test data.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L3-L300】
- **`apis.system.reboot`:** Used for saving configuration prior to reboot via `config_save`.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L5-L294】
- **`apis.routing.ip`:** Manages interface IP configuration, IPv6 mode toggles, and validation of assigned addresses.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L6-L159】
- **`apis.routing.bgp`:** Creates BGP routers/neighbors, verifies neighborship state, enables Docker routing mode, and performs cleanup.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L7-L300】
- **`apis.switching.portchannel` and `apis.switching.vlan`:** Support environment cleanup after the test by removing any L2 constructs that might have been altered during the run.【F:spytest/tests/routing/BGP/test_bgp_fast_reboot.py†L8-L90】

