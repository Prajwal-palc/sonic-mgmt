# test_sflow.py QA Summary

## 1. Topology Type and Inference
- The suite locks down a dual-DUT testbed with one traffic-generator leg on D1, two on D2, and a direct D1–D2 link via `st.ensure_min_topology("D1T1:1", "D2T1:2", "D1D2:1")`, indicating a T1 TG-connected topology for the viewer.【F:spytest/tests/system/test_sflow.py†L77-L93】
- Test docstrings further describe three TG ports (TG1/TG2/TG3) attached through a partner switch to the DUTs, reinforcing the mixed DUT–TG fan-out interpretation.【F:spytest/tests/system/test_sflow.py†L244-L258】【F:spytest/tests/system/test_sflow.py†L378-L392】

## 2. Overall Test Case Purpose
- Validate sFlow functionality on SONiC by checking sampling delivery to IPv6 collectors, ensuring maximum collector combinations are enforceable, and confirming configurations persist across save-and-reboot cycles.【F:spytest/tests/system/test_sflow.py†L244-L372】【F:spytest/tests/system/test_sflow.py†L378-L469】

## 3. Subtestcases and Their Roles
- `test_ft_sflow_sampling_v6_sFlow_collector`: Disables/enables interfaces, directs traffic through TG, and inspects captures, psample counters, and hsflowd status to prove IPv6 collector sampling works and generates adequate statistics.【F:spytest/tests/system/test_sflow.py†L244-L372】
- `test_ft_sflow_max_sflow_collector_config`: Iteratively configures IPv4-only, IPv6-only, and mixed collector sets while verifying `sflow` state after each change to ensure maximum collector constraints are respected.【F:spytest/tests/system/test_sflow.py†L378-L451】
- `test_ft_system_config_mgmt_verifying_config_with_save_reboot_sflow`: Performs `config save`, reboots the DUT, and validates that sFlow collector configuration survives, ensuring persistence of management settings.【F:spytest/tests/system/test_sflow.py†L454-L469】

## 4. Dependencies and Prerequisites
- Module fixture `sflow_module_hooks` (auto-use) provisions topology, gathers port speeds, initializes TG streams, and pushes baseline routing/sFlow configuration, while `sflow_module_epilog` cleans up, so test execution depends on these fixtures succeeding.【F:spytest/tests/system/test_sflow.py†L77-L163】
- Function fixture `sflow_func_hooks` resets per-test sFlow settings, ensuring independence between runs.【F:spytest/tests/system/test_sflow.py†L96-L107】
- Helper routines (`tg_init`, `sflow_module_prolog`, `module_config_retain`, `poch_config_remove`) require working `tgapi` access and SONiC routing/sFlow APIs, implying availability of traffic generator hardware and configured DUT interfaces.【F:spytest/tests/system/test_sflow.py†L120-L238】
- Requires SpyTest’s `vars` inventory (from `ensure_min_topology`) plus TG ports `vars.T1D1P1`, `vars.T1D2P1`, `vars.T1D2P2`; absence would block setup. Topology must support IPv4/IPv6 routing and hsflowd service.【F:spytest/tests/system/test_sflow.py†L77-L210】

## 5. Key Inputs and Their Sources
- Global `data` dictionary seeds collector names, IP/MAC addresses, ports, sampling rates, and expected hex encodings directly in `initialize_variables`, acting as canned test vectors.【F:spytest/tests/system/test_sflow.py†L25-L70】
- Device identifiers, interface names, and TG port mappings derive from SpyTest `vars` populated by the topology fixture, supplying handles such as `vars.D1T1P1` and `vars.T1D2P2`.【F:spytest/tests/system/test_sflow.py†L27-L47】【F:spytest/tests/system/test_sflow.py†L77-L210】
- Runtime values like DUT MAC (`data.dut_rt_int_mac1`) come from API queries (e.g., `get_ifconfig_ether`), while port speeds and routing parameters are computed via interface status and static route helpers during setup.【F:spytest/tests/system/test_sflow.py†L73-L135】
- Traffic generator handles (`tg_ph_1`–`tg_ph_3`) and streams (`tr1`) are acquired via `tgapi.get_handles` and `tg.tg_traffic_config`, binding the scripted traffic patterns to the testbed.【F:spytest/tests/system/test_sflow.py†L188-L209】

## 6. External Libraries and Roles
- `apis.routing.ip`, `apis.routing.arp`, and `apis.system.basic` manage IP interface configuration, ARP inspection, and MAC discovery on the DUTs.【F:spytest/tests/system/test_sflow.py†L8-L11】
- `apis.system.sflow`, `apis.system.logging`, and `apis.system.interface` provide sFlow control, log inspection, and interface counter operations central to validations.【F:spytest/tests/system/test_sflow.py†L11-L13】
- `apis.switching.portchannel` and `apis.switching.vlan` expose L2 constructs for auxiliary setup/cleanup routines.【F:spytest/tests/system/test_sflow.py†L14-L20】【F:spytest/tests/system/test_sflow.py†L224-L483】
- SpyTest utilities (`st`, `tgapi`, `SpyTestDict`, `exec_all`, `exec_foreach`, conversion helpers) supply logging, TG orchestration, data storage, and concurrent execution support used throughout the workflow.【F:spytest/tests/system/test_sflow.py†L6-L21】【F:spytest/tests/system/test_sflow.py†L77-L372】
- `pytest` underpins fixture and marker management for orchestrating the test suite.【F:spytest/tests/system/test_sflow.py†L4-L5】
