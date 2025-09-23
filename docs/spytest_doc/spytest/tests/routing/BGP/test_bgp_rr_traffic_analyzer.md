# BGP Route Reflector Traffic Test Analyzer

## 1. Topology type
- **Topology:** Leaf–spine fabric with two SONiC DUTs (spine = D1, leaf = D2) and a shared traffic generator. The module-scoped fixture enforces `st.ensure_min_topology('D1D2:1', 'D1T1:1', 'D2T1:1')`, meaning a spine–leaf link plus a TG leg toward each DUT. Supporting helpers such as `bgplib.l3tc_underlay_config_unconfig`, `bgplib.l3tc_vrfipv4v6_address_leafspine_*`, and `bgplib.get_leaf_spine_topology_info()` further confirm a leaf/spine abstraction with RR-capable spine.
- **Inference:** The route-reflector workflow, repeated references to "spine"/"leaf" roles, and dependence on a TG per DUT indicate a standard SpyTest leaf-spine topology tailored for RR validation rather than a ring or single-hop layout.

## 2. Overall test case purpose
- Validate IPv6 BGP route-reflector behavior in a two-tier SONiC fabric. The suite confirms that a spine acting as RR does not leak client routes before RR enablement, correctly reflects iBGP updates once configured, and forwards the reflected routes by driving traffic between leafs through the fabric and traffic generator.
- Within the SONiC/SpyTest regression context, this file supplements broader BGP coverage by exercising RR control-plane state transitions alongside live traffic verification to ensure reflected prefixes are usable.

## 3. Detailed breakdown of sub-testcases
### Common fixtures and helpers
- **`bgp_module_hooks` (module autouse fixture)** – Ensures the minimum topology, derives the SONiC CLI flavor (`bgp_cli_type`), seeds `bgplib` resources from the testbed, and invokes `bgp_pre_config`/`bgp_pre_config_cleanup` to prepare loopbacks, VRF address pools, and traffic generator sessions used across the module.
- **`bgp_pre_config` / `bgp_pre_config_cleanup`** – Module-level setup/teardown that configures loopback interfaces, initializes TG BGP emulation for both IPv4/IPv6, normalizes traffic rates (`rate`, `pkts_per_burst`), and later removes those artifacts.
- **`bgp_rr_traffic_pre_config` / `bgp_rr_traffic_pre_config_cleanup`** – Class-scope helpers that build the leaf–spine underlay, assign IP addresses, run connectivity checks (ping), configure TG and DUT BGP sessions with RR support, verify neighbor establishment, capture topology metadata (`topo`), and clean everything afterward.
- **`bgp_rr_traffic_class_hook`** – PyTest class fixture that wraps the RR-specific pre-configuration and cleanup around the test class so each scenario starts from a known RR-ready baseline.
- **`bgp_func_hooks`** – Placeholder function-scoped fixture (currently a no-op) reserved for per-test adjustments or cleanup should future cases need it.

### `test_ft_bgp6_rr_traffic_check`
- Drives the end-to-end RR verification. The test pulls TG and BGP handles from `topo`, advertises 100 IPv6 routes from one leaf-side TG port, and starts the TG BGP session.
- After a brief wait, it queries `show_bgp_ipv6_summary` on the peer leaf to confirm that—before RR client configuration—RIB entries remain near zero, ensuring no unintended reflection.
- It then enables the route-reflector client on the spine (`create_bgp_route_reflector_client`) plus next-hop-self, waits for propagation, and verifies the peer leaf now learns all 100 IPv6 routes.
- Finally, it configures an IPv6 traffic stream from the other leaf TG port toward the advertised prefixes, clears DUT interface counters, sends a burst at the normalized rate, and checks TG-reported loss before stopping the TG BGP session. Errors are aggregated and reported via `st.report_result`.
- **Relevance:** Confirms both control-plane (RR gating of updates) and data-plane (traffic forwarding for reflected routes) correctness, which is critical for RR deployments in SONiC fabrics.

## 4. Dependencies and prerequisites
- **Fixtures:** Module autouse (`bgp_module_hooks`) and class fixture (`bgp_rr_traffic_class_hook`) must execute to populate topology data, configure interfaces, and bring up BGP sessions. Optional `bgp_func_hooks` exists for future per-test needs.
- **Topology resources:** Requires two DUTs with TG connectivity matching the enforced topology plus support for IPv6 BGP and RR features.
- **Traffic generator:** Relies on SpyTest TG integration for BGP emulation and traffic (`tgapi`, TG handles stored in `topo`).
- **BGP helpers:** Depends on `bgplib` canned procedures and `bgpapi`/`ipapi` for SONiC configuration; the test assumes those libraries know how to access DUTs via the `bgp_cli_type` determined at runtime.

## 5. Key inputs and parameters
- **`bgp_cli_type`** – Derived from `st.get_ui_type()` and normalized to `vtysh` when click is detected; controls how `bgpapi` issues CLI commands.
- **`rate` / `pkts_per_burst`** – Global traffic settings computed via `tgapi.normalize_pps`, reused by TG traffic streams to keep load within lab capabilities.
- **`topo` dictionary** – Populated by `bgplib.get_leaf_spine_topology_info()`, exposing DUT lists, TG objects (`tg_ob`), port handles, and emulation handles necessary for BGP route advertisement and traffic steering.
- **`spine_as`** – Pulled from `bgplib.data['spine_as']`, providing the AS number when enabling RR-client configuration on the spine.
- **TG handles (`bgp_handle`, `emulation_*`)** – Derived from `topo` for the TG's BGP peer and IPv6 interfaces, driving route advertisement and traffic generation.
- **Thresholds & timers** – Explicit waits (`st.wait(10)` / `st.wait(15)`) and acceptance thresholds (rib entries ≤10 before RR, ≥100 after) gate pass/fail conditions.

## 6. External libraries and modules
- **`pytest`** – Supplies fixture mechanisms, test discovery, and markers for regression tracking.
- **`spytest.st`** – SpyTest service API for logging, topology validation, waits, error reporting, and accessing testbed variables.
- **`spytest.tgapi`** – Abstraction over the traffic generator to normalize rates, configure BGP emulation, and send/verify traffic.
- **`apis.routing.ip` (`ipapi`)** – Handles IP address configuration and cleanup on SONiC interfaces.
- **`apis.routing.bgp` (`bgpapi`)** – Provides BGP configuration primitives, summary retrieval, and RR client setup.
- **`apis.system.interface` (`intfapi`)** – Clears interface counters before traffic validation.
- **`BGP.bgplib`** – SpyTest BGP helper module that encapsulates leaf-spine specific configuration flows, TG setup, and topology metadata retrieval.
- **`utilities.utils`** – Offers retry wrappers (`utils.retry_api`) used for ping validation.

## 7. Unspecified items
- Exact values inside `bgplib.data`, specific interface names, and TG port mappings depend on the external testbed definition and are not specified within this file.
- Hardware SKU, SONiC image version, and any additional environmental prerequisites are not specified.
