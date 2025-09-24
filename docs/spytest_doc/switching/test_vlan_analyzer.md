# Test File Analyzer: `spytest/tests/switching/test_vlan.py`

## 1. Topology type
- **Identified topology**: Dual-DUT with a shared traffic generator (TG) fanout. `st.ensure_min_topology("D1D2:2", "D1T1:2", "D2T1:2")` requires two DUTs interconnected with two links and each DUT connected to the TG with two ports, which drives most VLAN and storm-control checks. 【F:spytest/tests/switching/test_vlan.py†L24-L35】
- **Additional inference**: VLAN syslog validation reuses a reduced single-DUT management topology via `st.ensure_min_topology("D1")`, indicating flexibility but still rooted in the same inventory definitions. 【F:spytest/tests/switching/test_vlan.py†L328-L346】

## 2. Overall test case purpose
- The module validates SONiC VLAN behavior under the SpyTest framework, emphasizing VLAN membership rules, trunk forwarding, syslog logging, storm-control policing, and configuration resilience across reboots.
- It exercises both control-plane and data-plane aspects (traffic generator verification, MAC learning, SNMP queries) to ensure VLAN correctness, storm-control functionality, and configuration persistence across reboots (fast/warm) and system save operations. 【F:spytest/tests/switching/test_vlan.py†L96-L823】

## 3. Detailed breakdown of sub-testcases
- **`test_ft_add_unknownvlan_interface`**: Negative test ensuring an interface cannot be assigned as untagged to a non-existent VLAN while verifying tagged additions/removals succeed. Guards against unintended PVID creation. 【F:spytest/tests/switching/test_vlan.py†L209-L224】
- **`test_ft_vlan_delete_with_member`**: Validates feature flag–controlled protection preventing VLAN deletion while members remain, including CLI variations; confirms cleanup requirements before removal. 【F:spytest/tests/switching/test_vlan.py†L230-L255】
- **`test_ft_vlan_trunk_tagged`**: Runs bidirectional TG traffic over a VLAN trunk, checks MAC learning, aggregate throughput, and analyzer filters to confirm tagging behavior on trunk ports. Critical for data-plane validation. 【F:spytest/tests/switching/test_vlan.py†L261-L323】
- **`test_ft_vlan_syslog_verify`**: Creates and deletes VLANs to ensure NOTICE-level syslog entries are generated, validating observability/instrumentation aspects. 【F:spytest/tests/switching/test_vlan.py†L328-L359】
- **`test_ft_stormcontrol_verification`**: Core storm-control regression covering broadcast/unknown-multicast/unicast policing, KPI thresholds, configuration overrides, and ensuring unrelated traffic unaffected. Uses helper `verify_bum_traffic_mode`. 【F:spytest/tests/switching/test_vlan.py†L362-L422】
- **`test_ft_stormcontrol_portchannel_intf`**: Checks storm-control behavior with port-channels—ensuring config rejection on LAG interface, validating enforcement when member ports used, and exercising negative cases (missing BPS, improper delete). 【F:spytest/tests/switching/test_vlan.py†L425-L518】
- **`test_ft_stormcontrol_incremental_bps_max_vlan`**: Sweeps storm-control rates across interfaces, verifying enforcement ranges and counters relative to recalculated thresholds, ensuring scalability with multiple VLANs. 【F:spytest/tests/switching/test_vlan.py†L521-L572】
- **`test_ft_stormcontrol_fast_reboot`**: Confirms storm-control configurations survive fast reboot and continue to regulate traffic. Includes config-save, reboot, post-boot verification, and traffic validation. 【F:spytest/tests/switching/test_vlan.py†L575-L613】
- **`test_ft_stormcontrol_warm_reboot`**: Mirrors fast reboot scenario for warm reboot, also logging SpyTest test case IDs for coverage. 【F:spytest/tests/switching/test_vlan.py†L616-L662】
- **`test_ft_vlan_save_config_warm_and_fast_reboot`**: Exercises maximum VLAN scale workflow, including creation, member assignments, MAC learning, traffic continuity, fast/warm reboot survivability, and throughput checks post-reboot. Relies on helper routines (`vlan_module_config`, `max_vlan_verify`, `mac_verify`). 【F:spytest/tests/switching/test_vlan.py†L706-L793】
- **`test_ft_snmp_max_vlan_scale`**: Validates SNMP BRIDGE-MIB accessibility after scaling VLANs to max count, ensuring management-plane observability with custom community/location. 【F:spytest/tests/switching/test_vlan.py†L795-L823】

### Helper utilities & fixtures
- **Fixtures**: `vlan_module_hooks` (module scope) initializes topology, platform data, VLAN defaults, TG streams, and base configuration; ensures teardown by clearing VLANs. `vlan_func_hooks` performs per-test platform gating and targeted cleanup for SNMP scaling. 【F:spytest/tests/switching/test_vlan.py†L24-L48】
- **Helper functions**: `platform_check`, `vlan_variables`, `vlan_module_prolog/epilog`, `config_tg_stream`, `verify_bum_traffic_mode`, `report_result`, plus max-VLAN helpers support repeated setups, parameter derivation, traffic verification, and result reporting. 【F:spytest/tests/switching/test_vlan.py†L51-L703】

## 4. Dependencies and prerequisites
- **SpyTest fixtures**: `st.ensure_min_topology` ensures required DUT/TG connectivity. 【F:spytest/tests/switching/test_vlan.py†L24-L35】
- **Traffic Generator integration** via `tgapi.get_handles_byname` retrieving TG ports; `config_tg_stream` pre-configures bidirectional VLAN streams. 【F:spytest/tests/switching/test_vlan.py†L79-L132】
- **Platform data**: `basic_obj.show_version`, `st.get_datastore` supply hardware constants (e.g., TH3 unsupported for BUM). 【F:spytest/tests/switching/test_vlan.py†L28-L88】
- **Feature flags**: Repeated `st.is_feature_supported` checks (storm control, prevent-delete). Testing requires DUT features enabled. 【F:spytest/tests/switching/test_vlan.py†L30-L142】【F:spytest/tests/switching/test_vlan.py†L241-L255】
- **Reboot capability**: Tests rely on `st.reboot` for cold/fast/warm reboot sequences and `reboot.config_save`. 【F:spytest/tests/switching/test_vlan.py†L575-L793】

## 5. Key inputs and parameters
- `sc_data` dictionary collects runtime parameters: VLAN IDs (`vlan_list`, `vlan`, `vlan_id`), traffic profile (`kbps`, `frame_size`, `rate_pps`), thresholds (`lower_pkt_count`, `higher_pkt_count`), max VLAN scale, MAC addresses, community strings, etc. Controls behavior across tests. 【F:spytest/tests/switching/test_vlan.py†L57-L93】
- `tg_info` stores TG stream handles and VLAN context for traffic validation. 【F:spytest/tests/switching/test_vlan.py†L79-L132】
- Feature toggles, such as `sc_data.cli_type`, `sc_data.max_vlan`, adjust flows based on platform support. 【F:spytest/tests/switching/test_vlan.py†L60-L87】

## 6. External libraries and modules
- **SpyTest APIs**: `st`, `tgapi`, and utility modules provide logging, topology introspection, traffic management, and reporting. 【F:spytest/tests/switching/test_vlan.py†L3-L19】
- **SONiC API wrappers**: `apis.switching.vlan`, `apis.system.storm_control`, `apis.system.interface`, `apis.switching.portchannel`, `apis.system.reboot`, `apis.system.basic`, `apis.system.snmp`, `apis.switching.mac` expose configuration and show commands. 【F:spytest/tests/switching/test_vlan.py†L6-L15】
- **Support libraries**: `apis.common.wait`, `utilities.utils`, `utilities.common.poll_wait`, `utilities.parallel.exec_all`/`ensure_no_exception` handle waits, helper utilities, polling loops, and parallel execution. 【F:spytest/tests/switching/test_vlan.py†L13-L19】

## 7. Unspecified items
- Specific `testbed.yaml` inventory names beyond symbolic handles (e.g., actual port numbers) – **Not specified** in the file.
- External configuration data such as group_vars or CLI parameters enabling features – **Not specified**.
