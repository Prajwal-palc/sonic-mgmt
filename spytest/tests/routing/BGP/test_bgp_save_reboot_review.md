# Test Case Review: `test_bgp_save_reboot.py`

## 1. Topology Type in Viewer
- The module-level fixture requests a minimum topology of one link between DUT1 and DUT2 and two links between DUT1 and a traffic generator (T1), implying a dual-DUT setup with a TG that has separate IPv4/IPv6 connectivity. The topology viewer should therefore display two DUTs (D1, D2) with a single interconnect and two TG links toward D1.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L37-L73】

## 2. Overall Test Purpose
- Validates that eBGP and iBGP sessions (IPv4 and IPv6) remain established after saving the configuration via `vtysh` and rebooting both DUT1 and DUT2. Each DUT performs a config save, reboots, waits for neighbor restoration, and checks session establishment with its peer and traffic generators.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L235-L312】

## 3. Subtestcases and Their Roles
- **Module autouse fixture `bgp_save_reboot_module_hooks`** – Prepares the environment: enforces the topology, adjusts UI shell type, enables IPv6 globally, configures IPv4/IPv6 interfaces, establishes eBGP/iBGP sessions between DUTs and TGs, and programs TG emulation. This setup is critical so that post-reboot verification occurs on fully formed BGP adjacencies.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L37-L233】
- **Helper routines (`ipv4_ip_address_config`, `verify_ipv4_address_config`, `ipv6_address_config`, `verify_ipv6_address_config`, `ipv4_bgp_config`, `ipv6_bgp_config`, `tg_bgp_config`, `tg_bgpv6_config`)** – These encapsulate repeated interface/BGP/TG configuration and validation steps. They provide modularity and explicit checks that the routing environment is correct before reboots, ensuring failures are caught early.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L91-L233】
- **`config_dut1_verify`** – Saves BGP configuration on DUT1, reboots it, and ensures IPv4 and IPv6 neighbor sessions with DUT2 and TGs re-establish. Demonstrates persistence and recovery of BGP on the first DUT.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L235-L278】
- **`config_dut2_verify`** – Performs the same save, reboot, and post-check sequence on DUT2, validating configuration resiliency for the second DUT.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L281-L306】
- **Test method `test_ft_bgp_save_reboot`** – Executes both DUT verification routines in parallel to reduce runtime and mimic simultaneous operations, then reports the aggregated result.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L309-L312】

## 4. Dependencies and Prerequisites
- Requires the autouse module fixture and function fixture to run automatically before tests.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L37-L88】
- Depends on SpyTest topology metadata (`vars`) produced by `st.ensure_min_topology`, which presumes a testbed providing DUT-to-DUT and DUT-to-TG connectivity as defined.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L37-L73】
- Conditional wait tuning relies on the "bgp-neighbotship-performance" feature flag, so feature support information must be available on DUT1.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L41-L45】
- Uses traffic generator handles resolved via `tgapi.get_handle_byname`, implying TG port definitions exist in the testbed inventory.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L197-L233】

## 5. Key Inputs and Their Sources
- Static addressing, ASNs, and other parameters are defined locally in the SpyTestDict at the top of the file (e.g., IP addresses, router IDs, ASNs, IPv6 toggle, neighbor wait timer).【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L10-L35】
- Runtime values such as UI shell type, feature support flags, and device/port identifiers come from SpyTest APIs (`st.get_ui_type`, `st.is_feature_supported`, and the `vars` object returned by `ensure_min_topology`), drawing on the active testbed and DUT capabilities.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L37-L73】

## 6. External Libraries and Roles
- **`pytest`** – Provides fixture management and test markers.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L1】
- **`spytest` core (`st`, `tgapi`, `SpyTestDict`)** – Supplies logging, execution utilities, traffic-generator handles, and shared data storage.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L2】
- **`apis.system.reboot`** – Offers `config_save` helper for persisting configuration prior to reboot.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L3】【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L239-L244】
- **`apis.routing.ip`** – Handles IPv4/IPv6 interface configuration and verification routines.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L4】【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L91-L151】
- **`apis.routing.bgp`** – Manages BGP router/neighbor configuration, verification, and cleanup.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L5】【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L155-L306】【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L76-L83】
- **`apis.switching.portchannel` and `apis.switching.vlan`** – Used for teardown to ensure no residual L2 configuration remains after the module completes.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L6-L7】【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L76-L83】
- **`utilities.parallel.exec_all`** – Enables concurrent execution of the DUT verification routines to simulate simultaneous reboots and reduce test duration.【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L8】【F:spytest/tests/routing/BGP/test_bgp_save_reboot.py†L309-L312】

