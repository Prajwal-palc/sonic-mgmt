# NAT Test QA Analysis

## 1. Topology type used in the viewer and inference
- The module-level fixture requests topology `D1T1:2` via `st.ensure_min_topology("D1T1:2")`, meaning one DUT with two traffic-generator ports; this call reveals the topology expected by the viewer and testbed configuration.

## 2. Overall test case purpose
- `test_ft_nat_docker_restart` validates that, after stopping and restarting the NAT Docker service, dynamic NAT translations are cleared while static translations are restored, ensuring NAT resiliency across service restarts.

## 3. Subtestcases and their roles
- **`test_ft_nat_docker_restart`**
  - Starts and stops UDP traffic mapped to a dynamic NAT rule to populate translation entries.
  - Restarts the `nat` Docker container using systemd operations to simulate a control-plane restart event.
  - Checks that the dynamic NAT entry for the generated flow is removed after the restart, confirming stale mappings do not persist.
  - Verifies a static NAT entry still exists after the restart, proving configuration-backed translations recover correctly.

## 4. Dependencies or prerequisites
- **Fixtures**: `nat_module_config` (auto-use) sets the topology, initializes shared data, and runs `nat_prolog()` for DUT/TG provisioning; `nat_func_hooks` clears interface counters and NAT statistics before each test.
- **Platform guard**: `nat_prolog()` blocks execution on TH3 platforms by reading hardware SKU constants, preventing unsupported runs.
- **Topology assets**: requires DUT interface handles (`vars.D1`, `vars.D1T1P1`, `vars.D1T1P2`) and a traffic generator obtained from the shared `vars` testbed object.
- **Cleanup**: `nat_epilog()` removes NAT/zones, clears routes and VLANs, and optionally tears down traffic generator configuration based on module settings.

## 5. Key inputs and their origins
- The `SpyTestDict` `data` is populated in `nat_initialize_variables()` with hard-coded IPv4 addresses, NAT pool definitions, port numbers, protocol strings, and timing parameters used throughout the test.
- Rate/packet counts derive from `tgapi.normalize_pps(10)` and the resulting integer conversion.
- Feature toggles such as CLI mode, packet capture enablement, and stats validation are determined dynamically from `st.is_feature_supported("klish")`, `st.is_vsonic()`, and `st.is_sonicvs()`.
- Testbed-specific handles (device names, ports, configuration flags) are supplied through `vars = st.ensure_min_topology("D1T1:2")`, linking back to `testbed.yaml` definitions.

## 6. External libraries and roles
- **pytest** for fixture and test declaration/marks.
- **spytest core** (`st`, `tgapi`, `SpyTestDict`) providing logging, topology access, traffic generator control, and structured storage.
- **SONiC API wrappers**: `apis.routing.ip`, `apis.routing.nat`, `apis.routing.arp`, `apis.switching.vlan`, `apis.system.basic`, and `apis.system.interface` manage DUT configuration, NAT translation queries, routing, VLAN, system services, and interface counters.
