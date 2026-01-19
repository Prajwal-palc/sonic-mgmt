# test_arp_static_route_long_run QA Summary

## 1. Topology type used in the viewer and inference
- The test enforces a minimum topology of `D1T1:2`, indicating one DUT connected to a traffic generator with two links. This is inferred from the `st.ensure_min_topology("D1T1:2")` call during initialization and the subsequent retrieval of traffic-generator handles `T1D1P1` and `T1D1P2`.
  - Evidence: topology setup via `st.ensure_min_topology("D1T1:2")` and traffic-generator handle lookup for `T1D1P1`/`T1D1P2`.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L13-L44】

## 2. Overall test case purpose
- Validate that static route and ARP (both dynamic and static) configurations survive configuration save operations and persist correctly across warm, fast, and cold reboots of the DUT.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L44-L186】

## 3. Subtestcases and their contributions
- **Module setup via `arp_static_route_reboot_module_hooks`** – Establishes baseline configuration by programming a static route, generating a dynamic ARP entry through traffic generator traffic, adding a static ARP entry, and validating both before running reboot scenarios. This ensures each reboot test starts with known-good state and that configuration save has been executed.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L33-L123】
- **`test_ft_arp_static_route_config_mgmt_verifying_config_with_warm_reboot`** – Performs a warm reboot (when supported) and revalidates static route plus dynamic/static ARP entries to confirm persistence across warm reboot workflows.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L124-L149】
- **`test_ft_arp_static_route_config_mgmt_verifying_config_with_save_fast_reboot`** – Executes a fast reboot, replays dynamic ARP learning, and verifies that static route and ARP state remain correct, covering the fast reboot recovery path.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L151-L167】
- **`test_ft_arp_static_route_config_mgmt_verifying_config_with_save_reboot`** – Performs a standard cold reboot, refreshes the dynamic ARP entry, and confirms static route and ARP state, ensuring configuration durability through full device restarts.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L170-L186】

## 4. Dependencies or prerequisites
- Requires SpyTest topology variables (`vars`) populated via `st.ensure_min_topology`, including DUT and traffic generator port identifiers (`vars.D1`, `vars.D1T1P1`, `vars.D1T1P2`).【F:spytest/tests/routing/test_arp_static_route_long_run.py†L13-L52】
- Depends on traffic generator connectivity and named handles `T1D1P1`/`T1D1P2` to drive ARP learning via `tgapi` APIs.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L40-L123】
- Requires ability to save configuration (`rb_obj.config_save`) and perform different reboot types via `st.reboot`. Warm reboot test additionally depends on platform support retrieved from datastore constants.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L63-L149】
- Cleans up by clearing IP addresses, static routes, and static ARP entries post-module, so environment must permit these cleanup operations.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L67-L73】

## 5. Key inputs and their sources
- Static ARP MAC/IP, dynamic ARP MAC/IP, interface IPs, route network, and masks are hardcoded into the `SpyTestDict` during initialization.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L17-L27】
- Platform SKU and datastore constants (including supported warm reboot platforms) are retrieved at runtime via `basic_obj.get_hwsku` and `st.get_datastore`, implying dependency on inventory metadata/configuration files (e.g., `testbed.yaml` or group vars).【F:spytest/tests/routing/test_arp_static_route_long_run.py†L29-L132】
- Traffic generator handles and dynamic host configuration (`data.h1`) originate from the configured topology and the `tgapi` library, which uses testbed definitions for port naming and connectivity.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L40-L123】
- DUT interface identifiers (`vars.D1T1P1`, `vars.D1T1P2`) are obtained from the ensured topology context, binding to entries defined in testbed files; explicit external file names are not specified.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L13-L52】

## 6. External libraries and their roles
- `apis.routing.arp` (`arp_obj`) – Manage and verify static/dynamic ARP entries on the DUT.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L5-L123】
- `apis.system.reboot` (`rb_obj`) – Save configuration and trigger device reboots of different types.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L6-L186】
- `apis.system.basic` (`basic_obj`) – Retrieve hardware SKU information used for capability checks.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L7-L132】
- `apis.routing.ip` (`ip_obj`) – Configure IP addresses and static routes, and verify routing entries on the DUT.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L8-L123】
- `apis.routing.bgp` (`bgp_obj`) – Enable docker routing configuration mode prior to static route configuration.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L9-L123】
- `spytest.tgapi` (`tgapi`) – Provision traffic generator interfaces, drive ping for ARP learning, and verify connectivity.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L3-L123】
- `utilities.common.poll_wait` – Poll helper for verifying interface IP and static route state within timeouts.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L11-L106】
- `pytest` fixtures – Provide module- and function-level setup/teardown scaffolding for the test sequence.【F:spytest/tests/routing/test_arp_static_route_long_run.py†L1-L84】

