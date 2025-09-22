# SpyTest `test_vlan.py` QA Summary

## 1. Topology Type Used in the Viewer
- The module-level autouse fixture calls `st.ensure_min_topology("D1D2:2", "D1T1:2", "D2T1:2")`, indicating a topology with two DUTs (D1, D2) interconnected by two links and a traffic generator (T1) dual-homed to both DUTs with two links each. This implies a dual-DUT, dual-TG-port topology in the viewer. In the syslog-specific test, a minimal single-DUT topology (`st.ensure_min_topology("D1")`) is sufficient, showing the primary requirement still revolves around the dual-DUT setup for most scenarios.

## 2. Overall Test Case Purpose
- The suite validates VLAN lifecycle operations (creation, deletion, membership), MAC learning, trunk tagging behavior, syslog reporting, storm-control enforcement (including edge cases, incremental policing, and reboot persistence), configuration resilience across fast/warm reboots, and SNMP BRIDGE-MIB access when the device is scaled to the maximum VLAN count.

## 3. Subtestcases and Contributions
- `test_ft_add_unknownvlan_interface`: Ensures that interfaces cannot join non-existent VLANs and that tagged membership behaves correctly, guarding against misconfigurations that could break VLAN isolation.
- `test_ft_vlan_delete_with_member`: Confirms VLAN deletion protections when members are still attached, verifying platform safeguards and CLI differences (click vs. other UI types).
- `test_ft_vlan_trunk_tagged`: Verifies traffic forwarding and MAC learning across a VLAN trunk with analyzer filters, ensuring VLAN-tagged traffic passes end-to-end.
- `test_ft_vlan_syslog_verify`: Checks syslog NOTICE entries for VLAN add/remove events, validating operational logging.
- `test_ft_stormcontrol_verification`: Exercises BUM (broadcast, unknown unicast/multicast) policing accuracy, configuration independence, and selective removal impacts to confirm storm-control efficacy.
- `test_ft_stormcontrol_portchannel_intf`: Tests negative/positive scenarios involving port-channel membership to ensure storm-control cannot be misapplied to unsupported interfaces and that traffic policing persists through interface reconfigurations.
- `test_ft_stormcontrol_incremental_bps_max_vlan`: Sweeps storm-control bit rates and validates traffic conformity at each level to verify rate-limiter scaling.
- `test_ft_stormcontrol_fast_reboot`: Verifies configuration persistence and traffic enforcement through a fast reboot cycle.
- `test_ft_stormcontrol_warm_reboot`: Similar to fast reboot, but for warm reboot, also mapping to multiple functional test case IDs for regression coverage.
- `test_ft_vlan_save_config_warm_and_fast_reboot`: Stresses max VLAN count creation, persistence across regular, fast, and warm reboots, MAC learning retention, and post-reboot traffic continuity.
- `test_ft_snmp_max_vlan_scale`: Validates SNMP BRIDGE-MIB responses after scaling VLANs to maximum and configuring SNMP community details.

## 4. Dependencies and Prerequisites
- Autouse module fixture (`vlan_module_hooks`) requires the dual-DUT + TG topology, captures DUT version info, computes VLAN/test data, and preconfigures VLAN and storm-control state while ensuring traffic generator streams exist. It also skips unsupported platforms via `platform_check` for specific tests.
- Function-level autouse fixture (`vlan_func_hooks`) enforces platform capability checks for storm-control tests and resets VLAN/port-channel state before the SNMP scale test.
- Relies on hardware constants retrieved via `st.get_datastore` (e.g., TH3 platform exclusions, warm reboot support) and feature flags (`st.is_feature_supported`).
- Traffic generator access through `tgapi.get_handles_byname` assumes named ports (`T1D1P1`, etc.) exist in the topology description.
- Requires ability to perform device reboots (normal, fast, warm) and save configuration, so platform must permit disruptive actions.

## 5. Key Inputs and Their Sources
- VLAN IDs: Generated via `random_vlan_list`, with fallback constraints (`sc_data.max_vlan = 100` when the `vlan-range` feature is absent).
- Interface references: Pulled from `vars` returned by `st.ensure_min_topology`, including DUT-to-DUT, DUT-to-TG, and TG port identifiers; additional free ports obtained via `st.get_free_ports`.
- Storm-control parameters: Static values in `sc_data` (e.g., `kbps`, frame size, rate) set within `vlan_variables` and adjusted dynamically during tests.
- Traffic generator handles and stream IDs: Provided by `tgapi.get_handles_byname` and stored in `tg_info` for reuse.
- Hardware/platform metadata: Gathered via `basic_obj.show_version`, `basic_obj.get_hwsku`, and datastore constants to drive conditional logic.
- SNMP credentials and OIDs: Hard-coded within `vlan_variables` (`ro_community`, `oid_sysName`, `oid_dot1qBase`, etc.) and populated before SNMP validation; management IP read with `basic_obj.get_ifconfig_inet`.

## 6. External Libraries and Their Roles
- `pytest`: Test harness providing fixtures and markers.
- `spytest` toolkit (`st`, `tgapi`, `SpyTestDict`): Core SpyTest APIs for topology management, logging, reporting, and traffic generator abstractions.
- `spytest.utils.random_vlan_list`: Supplies random VLAN IDs.
- `apis.switching.vlan`: VLAN configuration and verification APIs.
- `apis.system.logging`: Accesses and manages syslog entries.
- `apis.switching.mac`: Retrieves MAC learning information and counts.
- `apis.system.storm_control`: Configures and validates storm-control settings.
- `apis.system.interface`: Handles interface counter operations.
- `apis.switching.portchannel`: Manages port-channel configuration.
- `apis.system.reboot`: Saves configuration and triggers device reboots.
- `apis.common.wait`: Provides wait helpers (e.g., `vsonic_mac_learn`).
- `apis.system.basic`: Supplies generic device information and interface queries.
- `apis.system.snmp`: Manages SNMP configuration and polling.
- `utilities.utils`, `utilities.common.poll_wait`, `utilities.parallel.exec_all/ensure_no_exception`: Utility helpers for logging, polling conditions, and parallel execution management.
