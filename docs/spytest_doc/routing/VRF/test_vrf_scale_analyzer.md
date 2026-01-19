# VRF Scale Test Analyzer

## 1. Topology Type
- **Identified Topology:** Dual DUT with shared traffic generator (D1-D2 interconnected, each linked to TG T1).
- **Inference Details:** The `initialize_topology` helper enforces `st.ensure_min_topology("D1D2:4", "D1T1:2", "D2T1:2")`, which requires two DUTs interconnected by four links and each connected to the traffic generator by two links. Test data such as `data.d1_dut_ports`, `data.d2_dut_ports`, and `data.tg_dut1_hw_port` confirm this two-DUT, one-TG layout.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L29-L58】

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate large-scale VRF Lite deployments on dual SONiC DUTs, covering VRF creation, static route leaking, BGP peering across VRFs, traffic forwarding, and configuration resilience after reboot.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L1-L214】
- **Context in SONiC/SpyTest:** The suite exercises VRF scale limits driven by platform capabilities (TH3, campus, default) and uses SpyTest infrastructure (fixtures, traffic generator APIs) to verify SONiC control-plane and data-plane behavior under large VRF counts.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L29-L175】

## 3. Detailed Breakdown of Sub-Testcases
### `test_vrf_scale`
- **Intent & Logic:** Confirms all VRFs from the preloaded config exist on both DUTs, including after flapping the inter-DUT interface. Uses `vrf_api.verify_vrf` and port shutdown/no-shutdown to ensure bindings persist.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L214-L244】
- **Relevance:** Ensures basic VRF provisioning and interface bindings are stable, forming the foundation for subsequent traffic and routing scale tests.

### `test_vrf_route_leak`
- **Intent & Logic:** Programs static routes across VRFs in two phases (lower and upper subnet groups) using `vrf_static_route`, then sends TG traffic to verify route leaking effectiveness via aggregate traffic statistics.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L246-L296】
- **Relevance:** Validates data-plane forwarding across numerous VRFs when static route leaking is applied, demonstrating reachability at scale.

### `test_vrf_bgp`
- **Intent & Logic:** Configures BGP neighbors per VRF over inter-DUT links, activates sessions, and checks adjacency establishment for boundary VRFs. Also clears BGP to confirm sessions recover. Uses helper `bgp_api.config_bgp` and `ip_bgp.verify_bgp_neighbor` polling.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L298-L345】
- **Relevance:** Ensures control-plane scalability by proving that many VRF-specific BGP sessions can be established and survive resets.

### `test_vrf_reload`
- **Intent & Logic:** Saves configuration, triggers fast reboot, and verifies VRF bindings remain post-reboot.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L347-L363】
- **Relevance:** Checks configuration persistence and system resilience for large VRF deployments.

### Helper Functions / Fixtures
- `prologue_epilogue` fixture performs topology initialization and base configuration before tests, ensuring consistent state.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L87-L103】
- `base_config` and `host_config` set up device configs, VLANs, IP interfaces, and traffic generator streams used by all tests.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L105-L197】【F:spytest/tests/routing/VRF/test_vrf_scale.py†L399-L415】
- `base_unconfig` (not invoked automatically) provides cleanup logic for static routes, interfaces, and reboot recovery.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L199-L236】
- Utility helpers (`ip_range`, `vrf_static_route`, etc.) generate addressing and apply bulk configuration supporting scale scenarios.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L365-L415】

## 4. Dependencies and Prerequisites
- **Fixtures:** Module-level `prologue_epilogue` sets up VRFs, VLANs, TG hosts, and traffic streams before tests run.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L87-L197】
- **Topology Constraints:** Requires two SONiC DUTs with interconnect and TG connectivity as defined in `st.ensure_min_topology`. Platform checks determine VRF scale limits (e.g., TH3 vs. campus).【F:spytest/tests/routing/VRF/test_vrf_scale.py†L29-L86】
- **Traffic Generator:** Relies on SpyTest traffic generator integration (`tgen_obj_dict`, `tgapi`) for traffic configuration and validation.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L11-L16】【F:spytest/tests/routing/VRF/test_vrf_scale.py†L151-L197】

## 5. Key Inputs and Parameters
- **Platform-Based Parameters:** `max_vrfs`, `static_lower`, `static_upper`, `bgp_vrfs_start`, `bgp_vrfs_end`, and config DB filenames vary based on detected hardware SKU or campus build, dictating scale levels and configuration templates.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L43-L84】
- **Address Pools:** Generated via `ip_range` for DUT interconnects and TG hosts (`data.dut1_dut2_ip_list`, `data.tg_dut1_stream_start`, etc.) determining route and traffic endpoints.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L70-L84】【F:spytest/tests/routing/VRF/test_vrf_scale.py†L365-L397】
- **Traffic Settings:** Stream attributes such as `rate_pps`, source/destination IPs, and VRF bindings are defined in `base_config` to exercise traffic across all VRFs.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L159-L197】

## 6. External Libraries and Modules
- **SpyTest Core:** `st`, `utils`, `tgapi` provide logging, utility execution, and traffic generator control.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L11-L16】
- **Traffic Generator:** `tgen_obj_dict` maps topology handles to TG sessions.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L13-L16】
- **VRF/Test Data Modules:** `vrf_vars` supplies shared data storage; `vrf_lib` offers test-specific helper routines like traffic clearing.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L15-L16】【F:spytest/tests/routing/VRF/test_vrf_scale.py†L258-L262】
- **API Modules:** Importing from `apis.switching`, `apis.routing`, and `apis.system` exposes configuration and verification commands (VLANs, IPs, VRFs, BGP, ports, reboot, hardware queries). These modules enable programmatic SONiC control and validation within tests.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L17-L26】
- **Standard Library:** `pytest`, `os`, and `ipaddress` support test structuring, file path manipulation, and IP calculations.【F:spytest/tests/routing/VRF/test_vrf_scale.py†L8-L10】

## 7. Unspecified Items
- **Testbed YAML References:** Not specified in the test file.
- **Group Vars / CLI Overrides:** Not specified.
- **Cleanup Invocation:** `base_unconfig` is defined but its execution trigger is not specified within this file.
