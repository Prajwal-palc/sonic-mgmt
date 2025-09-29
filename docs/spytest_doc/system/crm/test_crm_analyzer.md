# CRM Functional Tests Analyzer

## 1. Topology Type
- **Topology**: `D1T1:2` — one DUT connected to a traffic generator with two ports.
- **Inference**: The module-level fixture `ft_crm_module_hooks` calls `st.ensure_min_topology("D1T1:2")`, which provisions a single device-under-test with one traffic generator and two links. This is reinforced by subsequent usage of `vars.D1T1P1`, `vars.D1T1P2`, and traffic generator handles derived from `tgapi.get_handles` for two ports. 【F:spytest/tests/system/crm/test_crm.py†L29-L214】【F:spytest/tests/system/crm/test_crm.py†L585-L608】

## 2. Overall Test Case Purpose
- **Goal**: Validate SONiC CRM (Critical Resource Monitoring) threshold logging across multiple resource families (FDB, routes, neighbors, nexthops, ACL objects, etc.).
- **Scope in SONiC/SpyTest**: The test orchestrates resource consumption (via MAC entries, BGP routes, ECMP paths, ACL tables) and manipulates CRM thresholds to provoke `THRESHOLD_EXCEEDED` and `THRESHOLD_CLEAR` syslog events for each tracked resource family, ensuring CRM monitors and reports usage accurately. This aligns with SpyTest's system-level verification of SONiC control-plane monitoring and logging behavior. 【F:spytest/tests/system/crm/test_crm.py†L337-L500】【F:spytest/tests/system/crm/test_crm.py†L530-L617】

## 3. Detailed Breakdown of Sub-Testcases
### Helper and Setup Functions
- **`ft_crm_module_hooks` / `ft_crm_func_hooks`**: Module and function fixtures that prepare topology, clear IP configurations, and provide hooks for per-test customization. They ensure the DUT starts from a clean networking state. 【F:spytest/tests/system/crm/test_crm.py†L29-L47】
- **`crm_ft_test_all`**: Main orchestration routine. Configures CRM polling, collects resource baselines, sets up VLAN, ACLs, BGP sessions (v4/v6), ECMP routes, and invokes `verify_thresholds`. Establishes the environment needed for all subsequent verifications. 【F:spytest/tests/system/crm/test_crm.py†L530-L617】
- **Resource configuration helpers** (`crm_fdb_config`, `crm_bgp_config_v4/v6`, `crm_ecmp_config`, `crm_acl_config`, etc.): Drive the DUT and traffic generator to create load on specific CRM resource pools so thresholds can be exercised. 【F:spytest/tests/system/crm/test_crm.py†L174-L335】
- **`verify_thresholds`**: Core logic to manipulate CRM threshold modes (used, percentage, free), toggle interfaces, clear MACs, and wait for syslog generation. It aggregates CRM counters and confirms syslog messages via `check_logging_result`. 【F:spytest/tests/system/crm/test_crm.py†L340-L500】
- **`check_logging_result` / `check_test_status`**: Parse syslog output and record pass/fail status per resource family by ensuring both exceed and clear events occur for used, percentage, and free thresholds. 【F:spytest/tests/system/crm/test_crm.py†L462-L523】

### Test Functions
Each `test_ft_crm_*` function simply requests verification for a specific CRM family by delegating to `crm_ft_verify`. This wrapper triggers the full test run once (via `crm_ft_test_all`) and then inspects the recorded status for the requested family.

- **`test_ft_crm_fdb`**: Validates threshold logging for FDB entries, ensuring MAC learning and clearing drive CRM alerts. 【F:spytest/tests/system/crm/test_crm.py†L639-L641】
- **`test_ft_crm_route_v4`**: Checks IPv4 route resource thresholds using BGP-advertised routes and static ECMP entries. 【F:spytest/tests/system/crm/test_crm.py†L643-L646】
- **`test_ft_crm_route_v6`**: Ensures IPv6 route thresholds trigger correctly when IPv6 BGP load is applied (if supported). 【F:spytest/tests/system/crm/test_crm.py†L647-L650】
- **`test_ft_crm_neighbor_v4`**: Confirms IPv4 neighbor table monitoring via ARP adjacency creation. 【F:spytest/tests/system/crm/test_crm.py†L651-L654】
- **`test_ft_crm_neighbor_v6`**: Confirms IPv6 neighbor threshold logging, leveraging IPv6 BGP adjacency. 【F:spytest/tests/system/crm/test_crm.py†L655-L658】
- **`test_ft_crm_nexthop_v4`**: Verifies IPv4 next-hop resource alerts, primarily driven by ECMP/static route configuration. 【F:spytest/tests/system/crm/test_crm.py†L659-L662】
- **`test_ft_crm_nexthop_v6`**: Verifies IPv6 next-hop resource monitoring (if IPv6 features enabled). 【F:spytest/tests/system/crm/test_crm.py†L663-L666】
- **`test_ft_crm_nhop_group_member`**: Targets CRM counters for nexthop group members, leveraging ECMP setup. 【F:spytest/tests/system/crm/test_crm.py†L667-L670】
- **`test_ft_crm_nhop_group`**: Validates nexthop group object thresholds. 【F:spytest/tests/system/crm/test_crm.py†L671-L674】
- **`test_ft_crm_acl_table`**: Ensures ACL table resource thresholds are monitored when ACL tables are created/removed. 【F:spytest/tests/system/crm/test_crm.py†L675-L678】
- **`test_ft_crm_acl_entry`**: Checks ACL entry/resource usage reporting via applied ACL JSON configuration. 【F:spytest/tests/system/crm/test_crm.py†L679-L682】
- **`test_ft_crm_acl_counter`**: Monitors ACL counter resource thresholds. 【F:spytest/tests/system/crm/test_crm.py†L683-L686】
- **`test_ft_crm_acl_group`**: Validates ACL group threshold logging. 【F:spytest/tests/system/crm/test_crm.py†L687-L689】

These sub-tests matter because CRM exposes per-resource alerts; each test ensures a different resource pool correctly produces syslog events, collectively verifying CRM coverage across the DUT.

## 4. Dependencies and Prerequisites
- **Fixtures**: `ft_crm_module_hooks` (module-wide topology setup and IP cleanup) and `ft_crm_func_hooks` (per-test hook). 【F:spytest/tests/system/crm/test_crm.py†L29-L47】
- **Topology**: Requires a D1T1 testbed with two traffic generator ports to emulate neighbors and BGP peers. 【F:spytest/tests/system/crm/test_crm.py†L29-L214】【F:spytest/tests/system/crm/test_crm.py†L585-L608】
- **CRM-ready DUT**: DUT must support CRM features, syslog access, BGP, ACLs, and ECMP configuration.
- **Traffic Generator**: Needed for BGP route advertisement and neighbor simulation via `tgapi`. 【F:spytest/tests/system/crm/test_crm.py†L200-L223】【F:spytest/tests/system/crm/test_crm.py†L245-L271】

## 5. Key Inputs and Parameters
- **Topology variables**: `vars.D1`, `vars.T1D1P1`, `vars.D1T1P1`, etc., derived from SpyTest environment, map DUT interfaces to TG ports. 【F:spytest/tests/system/crm/test_crm.py†L585-L608】
- **CRM configuration**: Polling interval set to 1 second via `crm_obj.set_crm_polling_interval`; thresholds manipulated per family for used, percentage, and free modes. 【F:spytest/tests/system/crm/test_crm.py†L538-L571】
- **BGP Parameters**: Local/remote ASNs, router IDs, advertised route counts/prefixes defined in `crm_ft_test_all` to stress routing resources. 【F:spytest/tests/system/crm/test_crm.py†L541-L599】
- **ACL Configuration**: JSON template `acl_data.acl_json_config_crm` with ports injected before applying to DUT, influencing ACL resource usage. 【F:spytest/tests/system/crm/test_crm.py†L326-L335】
- **Threshold manipulation values**: Computed from current resource usage (e.g., `used_counter`, `free_counter`) and constants like `max_threshold`, `opt_delay`, etc., controlling how aggressively thresholds are triggered. 【F:spytest/tests/system/crm/test_crm.py†L340-L456】

## 6. External Libraries and Modules
- **`spytest.st`, `tgapi`, `SpyTestDict`**: Core SpyTest utilities for DUT interaction, traffic generator control, and structured data storage. 【F:spytest/tests/system/crm/test_crm.py†L4-L5】【F:spytest/tests/system/crm/test_crm.py†L530-L555】
- **`spytest.utils.poll_wait`**: Utility for polling operations (used for syslog verification). 【F:spytest/tests/system/crm/test_crm.py†L5】【F:spytest/tests/system/crm/test_crm.py†L456-L505】
- **`tests.system.crm.acl_json_crm_config`**: Provides ACL configuration templates to stress ACL-related CRM resources. 【F:spytest/tests/system/crm/test_crm.py†L6】【F:spytest/tests/system/crm/test_crm.py†L326-L335】
- **`apis.system.crm`**: CRM API for configuring thresholds, polling intervals, and retrieving resource counters. Central to driving CRM behavior. 【F:spytest/tests/system/crm/test_crm.py†L7】【F:spytest/tests/system/crm/test_crm.py†L337-L522】
- **`apis.switching.vlan`, `apis.switching.mac`**: VLAN and MAC APIs to generate FDB entries. 【F:spytest/tests/system/crm/test_crm.py†L8-L9】【F:spytest/tests/system/crm/test_crm.py†L174-L195】
- **`apis.system.logging`**: Interfaces with syslog to clear and read log entries. 【F:spytest/tests/system/crm/test_crm.py†L10】【F:spytest/tests/system/crm/test_crm.py†L103-L169】【F:spytest/tests/system/crm/test_crm.py†L462-L500】
- **`apis.routing.ip`, `apis.routing.bgp`**: Configure IP addresses and BGP sessions for route/neighbor load. 【F:spytest/tests/system/crm/test_crm.py†L11-L12】【F:spytest/tests/system/crm/test_crm.py†L200-L299】
- **`apis.system.interface`**: Manage interface state to affect neighbor and nexthop tables. 【F:spytest/tests/system/crm/test_crm.py†L13】【F:spytest/tests/system/crm/test_crm.py†L388-L455】
- **`apis.qos.acl`**: Apply ACL tables and entries to drive ACL resource usage. 【F:spytest/tests/system/crm/test_crm.py†L14】【F:spytest/tests/system/crm/test_crm.py†L318-L335】
- **`apis.system.basic`**: Supplies hardware SKU info used to skip unsupported families (e.g., DNAT/SNAT on certain platforms). 【F:spytest/tests/system/crm/test_crm.py†L15】【F:spytest/tests/system/crm/test_crm.py†L563-L567】
- **Standard libraries**: `pytest` for test structure and markers; `re` for IP manipulation utilities. 【F:spytest/tests/system/crm/test_crm.py†L1-L2】【F:spytest/tests/system/crm/test_crm.py†L53-L95】

## 7. Unspecified Items
- Any details not explicitly present in the test file (e.g., precise `testbed.yaml` mappings, actual ACL JSON contents, external traffic generator topology diagrams) are **Not specified**.
