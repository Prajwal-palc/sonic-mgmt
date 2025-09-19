# QA Notes for `test_bgp_4node.py`

## 1. Topology type used in the viewer and inference
- The module setup enforces a minimum topology containing links D1-D2, D2-D3, D2-D4, D3-D4, and D3-D1 before any tests run, which implies a four-DUT partial mesh/ladder style layout connecting all devices for confederation scenarios.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L56-L69】
- After validating reachability, the setup retrieves detailed confederation topology information via `bgp4nodelib.get_confed_topology_info()`, confirming that the test logic relies on a BGP confederation-specific four-node topology description for subsequent steps.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L56-L69】

## 2. Overall test case purpose
- The suite validates IPv4/IPv6 BGP behavior across a four-node confederation: initial module hooks establish connectivity, and individual tests check confederation route advertisement, route-reflector policies, route-map filtering, iBGP route-reflector cluster loop handling, and eBGP community attribute manipulation.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L56-L387】【F:spytest/tests/routing/BGP/test_bgp_4node.py†L400-L578】

## 3. Sub-testcases and their roles
- `test_ipv6_confed_route_distribution`: Advertises IPv4/IPv6 networks from DUT1 and ensures confederation peer DUT3 learns them, proving baseline advertisement and propagation within the confed fabric.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L119-L155】
- `test_ipv6_confed_with_rr`: Demonstrates that DUT4 initially cannot learn routes without a route-reflector, then validates learning once DUT3 is configured as RR, confirming RR control within the confederation iBGP AS.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L157-L214】
- `test_confed_route_distribution_with_rmap`: Builds ACLs and a route-map on DUT1 to apply AS-path prepends and permit/deny policies, then verifies DUT2’s routing table reflects those policies, covering policy-based filtering across confederation peers.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L216-L307】
- `test_ft_bgp_ibgp_RR_Loop`: Creates additional interfaces, forms iBGP peering among DUT1/DUT2/DUT3, establishes RR clients, and confirms advertised routes do not loop back, validating RR cluster loop prevention.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L313-L387】
- `test_ft_bgp_ebgp_community_map`: Configures IPv4/IPv6 eBGP sessions among all four DUTs and exercises community lists/route-maps in both directions to verify community tagging, subset removal, and community clearing behavior.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L400-L578】

## 4. Dependencies or prerequisites
- `bgp_module_hooks` (module autouse) obtains optional CLI argument `routed_sub_intf`, pushes base IPv4/IPv6 addressing (regular or sub-interface), verifies ping connectivity, and captures topology metadata before tests; it also handles cleanup.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L45-L81】
- `bgp_confed_class_hook` (class scope) configures and tears down the confederation BGP baseline used by `TestBGPConfed` subtests.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L93-L214】
- Function-scoped fixtures (`bgp_func_hooks`, `hooks_test_ft_bgp_ibgp_RR_Loop`, `hooks_test_ft_bgp_ebgp_community_map`) provide per-test cleanup for generic tests or for the RR loop/community map scenarios, including BGP deconfiguration and interface address removal.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L84-L396】【F:spytest/tests/routing/BGP/test_bgp_4node.py†L581-L593】
- The tests rely on BGP/IP API helpers and topology data supplied by `bgp4nodelib`, so a testbed meeting the enforced link requirements is assumed.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L56-L69】【F:spytest/tests/routing/BGP/test_bgp_4node.py†L95-L107】

## 5. Key inputs and their sources
- Static defaults (ASNs, networks, loopbacks, wait timers) are stored in the `bgp_4node_data` `SpyTestDict` defined at module level.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L12-L42】
- `sub_intf` is read from command-line/test invocation arguments via `st.get_args("routed_sub_intf")` to determine whether to configure sub-interfaces.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L45-L63】
- Topology-specific dictionaries (`topo[...]`) originate from `bgp4nodelib.get_confed_topology_info()` during module setup and from `st.get_testbed_vars()` in individual tests when extra interface identifiers are required.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L56-L69】【F:spytest/tests/routing/BGP/test_bgp_4node.py†L321-L327】【F:spytest/tests/routing/BGP/test_bgp_4node.py†L408-L416】
- Some tests define additional literals such as `test_case_id` for reporting or inline network prefixes/AS paths to drive specific validations.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L133-L170】【F:spytest/tests/routing/BGP/test_bgp_4node.py†L226-L233】【F:spytest/tests/routing/BGP/test_bgp_4node.py†L406-L487】

## 6. External libraries used and their roles
- `apis.routing.bgp` provides functions to configure BGP sessions, advertise routes, manage route-reflector clients, query BGP tables, and manipulate communities throughout the tests.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L6-L7】【F:spytest/tests/routing/BGP/test_bgp_4node.py†L138-L578】
- `apis.routing.ip` offers ACL, route-map, and interface IP configuration helpers needed for policy application and interface setup/cleanup.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L7-L8】【F:spytest/tests/routing/BGP/test_bgp_4node.py†L234-L593】
- `BGP.bgp4nodelib` centralizes topology-aware configuration, ping checks, and confederation helpers used during setup/cleanup and to retrieve topology context.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L8-L107】
- `utilities.common.ExecAllFunc` is used to batch asynchronous API calls (e.g., simultaneous BGP configuration and polling).【F:spytest/tests/routing/BGP/test_bgp_4node.py†L10-L448】
- `pytest` and `spytest` (`st`) supply the testing framework, fixtures, logging, reporting, and argument access functions used throughout the module.【F:spytest/tests/routing/BGP/test_bgp_4node.py†L2-L155】【F:spytest/tests/routing/BGP/test_bgp_4node.py†L313-L593】

