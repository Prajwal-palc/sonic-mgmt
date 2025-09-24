# VRF Lite Test Analyzer

## 1. Topology Type
- **Identified topology:** Dual-DUT with a shared traffic generator (TG) fan-out, using four inter-DUT links and single TG links to each DUT.
- **Evidence:** `initialize_topology()` calls `st.ensure_min_topology("D1D2:4", "D1T1:2", "D2T1:2")`, which requires two DUTs (D1, D2) interconnected by four links and a TG with two links to each DUT.【F:spytest/tests/routing/VRF/test_vrf.py†L23-L42】
- **Inference:** The function populates DUT-specific port lists and TG handles (`data.d1_dut_ports`, `data.tg_dut1_hw_port`, etc.), confirming a multi-DUT topology with TG connectivity, typical for VRF Lite validation in SpyTest.【F:spytest/tests/routing/VRF/test_vrf.py†L31-L42】

## 2. Overall Test Case Purpose
- **Primary goal:** Validate SONiC VRF Lite functionality across IPv4/IPv6 routing, BGP peering, static routes, route leaking, and persistence across reboots.
- **Scope in SONiC/SpyTest:** The module-level fixture invokes `loc_lib.vrf_base_config()`, establishing baseline VRF instances and BGP peering needed for subsequent functional checks. The test suite ensures VRF creation, interface bindings, ARP/NDP population, protocol sessions, static route programming, import/export between VRFs, and configuration durability, aligning with SONiC VRF Lite feature validation.

## 3. Detailed Breakdown of Sub-Testcases

### Fixture: `prologue_epilogue`
- **Purpose:** Automatically executed for the module to initialize topology variables and apply base VRF configuration before tests run; teardown is commented out (cleanup handled elsewhere if needed).【F:spytest/tests/routing/VRF/test_vrf.py†L44-L55】
- **Relevance:** Ensures all tests start from a consistent VRF Lite setup.

### Test: `test_VrfFun001_06`
- **Intent:** Combines functional checks for VRF creation and interface assignments (FtRtVrfFun001) and multi-interface binding (FtRtVrfFun006). It verifies VRF existence on both DUTs, confirms interface bindings (physical, loopback, VLAN, port-channel), validates IPv4/IPv6 addressing, checks ARP/NDP population, and confirms BGP sessions in multiple VRFs and address families.【F:spytest/tests/routing/VRF/test_vrf.py†L58-L142】
- **Why it matters:** Establishes baseline VRF correctness, interface membership, and protocol adjacency health before more advanced tests.

### Helper: `vrf_tc_26_27`
- **Role:** Configures BGP neighbor relationships (IBGP and EBGP) required by `test_VrfFun_26_27`. Provides reusable setup to reapply neighbor configuration if verification fails.【F:spytest/tests/routing/VRF/test_vrf.py†L146-L158】

### Test: `test_VrfFun_26_27`
- **Intent:** Validates IPv4 IBGP and EBGP sessions within a VRF by reapplying neighbor configuration, waiting for convergence, and verifying BGP-learned routes on both DUTs (FtRtVrfFun026/027/037).【F:spytest/tests/routing/VRF/test_vrf.py†L163-L205】
- **Importance:** Confirms VRF-specific BGP peering (both IBGP and EBGP) learns routes as expected, critical for VRF Lite forwarding.

### Fixture: `vrf_fixture_tc_10_12_14`
- **Purpose:** Provides cleanup for static routes configured during `test_VrfFun_10_12_14` and restores BGP sessions on physical, VLAN, and port-channel neighbors after the test.【F:spytest/tests/routing/VRF/test_vrf.py†L209-L252】

### Test: `test_VrfFun_10_12_14`
- **Intent:** Exercises adding/removing static routes with various next-hop types (physical, VLAN, port channel) across three VRFs for both IPv4 and IPv6, verifying connectivity via pings after each configuration step (FtRtVrfFun010/012/014).【F:spytest/tests/routing/VRF/test_vrf.py†L258-L338】
- **Contribution:** Demonstrates static routing functionality within VRFs for multiple interface types and protocol families.

### Fixture: `vrf_fixture_tc_20_24_25_32_33_44_45`
- **Purpose:** Cleans up BGP import policies applied during the route-leaking tests, ensuring VRF import configuration is removed post-test.【F:spytest/tests/routing/VRF/test_vrf.py†L342-L377】

### Test: `test_VrfFun_20_24_25_32_33_44_45`
- **Intent:** Validates route leaking/import between non-default VRFs by configuring BGP `import_vrf` statements for IPv4 and IPv6 across multiple VRFs, displaying route tables, and verifying BGP session health (FtRtVrfFun020/024/025/032/033/044/045).【F:spytest/tests/routing/VRF/test_vrf.py†L383-L424】
- **Importance:** Ensures VRF Lite can share routes across VRFs via BGP import mechanisms, a key feature for multi-tenant routing.

### Test: `test_VrfFun_05_50`
- **Intent:** Confirms overlapping addressing support across VRFs and persistence through a fast reboot. It leverages retry-based BGP verification before and after saving configuration and rebooting, validating that sessions re-establish post-reboot (FtRtVrfFun005/050).【F:spytest/tests/routing/VRF/test_vrf.py†L430-L476】
- **Significance:** Demonstrates VRF isolation for overlapping subnets and confirms configuration survives system restart.

## 4. Dependencies and Prerequisites
- **Fixtures:** `prologue_epilogue`, `vrf_fixture_tc_10_12_14`, `vrf_fixture_tc_20_24_25_32_33_44_45` manage setup and cleanup sequences required for VRF configuration, static routes, and BGP imports.【F:spytest/tests/routing/VRF/test_vrf.py†L44-L55】【F:spytest/tests/routing/VRF/test_vrf.py†L209-L252】【F:spytest/tests/routing/VRF/test_vrf.py†L342-L377】
- **Topology utilities:** `st.ensure_min_topology` ensures the lab has two DUTs and TG connectivity before proceeding.【F:spytest/tests/routing/VRF/test_vrf.py†L23-L42】
- **External configuration helpers:** `loc_lib.vrf_base_config()` preconfigures VRFs; various helper functions (`loc_lib.dut_vrf_bgp`, `loc_lib.tg_vrf_bgp`, `loc_lib.verify_bgp`, `loc_lib.retry_api`, `loc_lib.debug_bgp_vrf`) manage BGP sessions and diagnostics.【F:spytest/tests/routing/VRF/test_vrf.py†L44-L55】【F:spytest/tests/routing/VRF/test_vrf.py†L252-L338】【F:spytest/tests/routing/VRF/test_vrf.py†L400-L476】
- **Prerequisite services:** BGP, ARP/NDP, and IP route APIs must be available on the DUTs to execute the checks.

## 5. Key Inputs and Parameters
- **Topology-derived variables:** `data.dut_list`, `data.d1_dut_ports`, `data.tg_dut1_hw_port`, etc., sourced from `initialize_topology()`, dictate interface names used across tests.【F:spytest/tests/routing/VRF/test_vrf.py†L23-L42】
- **VRF and addressing data:** The imported `data` structure (from `vrf_vars`) supplies VRF names, loopback interfaces, IP prefixes, ASNs, VLAN IDs, and TG addresses used in BGP and static route configuration; specifics are defined externally (exact values not shown in this file).
- **Runtime argument:** `data.sub_intf = st.get_args("routed_sub_intf")` toggles between physical and subinterface modes for certain bindings.【F:spytest/tests/routing/VRF/test_vrf.py†L39-L52】
- **Test control flags:** BGP configuration dictionaries (`dict1`, `dict2`) specify VRF import relationships and neighbor parameters for route leaking tests.【F:spytest/tests/routing/VRF/test_vrf.py†L342-L424】

## 6. External Libraries and Modules
- **`pytest`:** Provides fixtures, test discovery, and markers for the test module.
- **`spytest.st`:** Core SpyTest service layer for logging, topology discovery, command execution, and result reporting.【F:spytest/tests/routing/VRF/test_vrf.py†L9-L55】
- **`spytest.tgen.tg.tgen_obj_dict`:** Accesses traffic generator handles used to configure and reference TG ports.【F:spytest/tests/routing/VRF/test_vrf.py†L10-L41】
- **`vrf_vars.data`:** Data container with VRF-related configuration parameters shared across tests.
- **`vrf_lib` (`loc_lib`):** Local helper library for VRF base configuration, BGP session management, traffic generator coordination, verification utilities, and debugging support.【F:spytest/tests/routing/VRF/test_vrf.py†L44-L476】
- **`apis.system.basic`:** Retrieves hardware SKU information for interface capability checks.【F:spytest/tests/routing/VRF/test_vrf.py†L26-L33】
- **`apis.routing.ip`:** Supplies IP configuration and verification functions (`verify_interface_ip_address`, `config_static_route_vrf`, `verify_ip_route`, `ping`, `show_ip_route`).【F:spytest/tests/routing/VRF/test_vrf.py†L110-L339】
- **`apis.routing.vrf`:** Provides VRF query utilities (`get_vrf_verbose`).【F:spytest/tests/routing/VRF/test_vrf.py†L68-L94】
- **`apis.routing.bgp`:** Manages BGP neighbor configuration and attributes, including route import statements.【F:spytest/tests/routing/VRF/test_vrf.py†L24-L424】
- **`apis.routing.arp`:** Offers ARP/NDP count verification functions.【F:spytest/tests/routing/VRF/test_vrf.py†L118-L136】
- **`apis.system.reboot`:** Enables configuration save operations prior to reboot testing.【F:spytest/tests/routing/VRF/test_vrf.py†L448-L454】
- **`utilities.common` and `utilities.utils.rif_support_check`:** Provide helper execution wrappers and RIF capability checks to tailor port selection.【F:spytest/tests/routing/VRF/test_vrf.py†L11-L52】

## 7. Unspecified Items
- Exact contents of `vrf_vars.data` (e.g., IP addresses, ASN values) are **Not specified** within this test file.
- Detailed implementation of helper APIs in `vrf_lib`, `utilities.common`, and SONiC API modules are **Not specified** here.

