# Static NAT Test Suite Analyzer (`tests/nat/test_static_nat.py`)

## 1. Topology Type
- **Declared topology:** `t0` via `pytestmark = [pytest.mark.topology('t0')]`.
- **Inference rationale:**
  - The module-level mark constrains the testbed to SONiC T0 topologies.
  - Fixtures such as `setup_test_env` derive interface lists, port-channels, and VRF mappings from `tbinfo` and `duthost` facts that are specific to the multi-TOR/leaf-spine layout of T0 testbeds (e.g., PortChannel members, VLAN1000 gateway, `ARISTA01T1` VM references).
  - Traffic paths iterate over `DIRECTION_PARAMS`, representing host↔TOR and leaf↔TOR flows that exist in the T0 layout.

## 2. Overall Test Case Purpose
- **High-level goal:** Validate the end-to-end behavior of SONiC static NAT/NAPT in a T0 environment.
- **What is covered:**
  - Correctness of static NAT and static NAPT translations for TCP, UDP, and ICMP traffic in both directions.
  - CLI CRUD (create/read/update/delete) operations for static rules, including persistence across reboots and interface changes.
  - Zone configuration enforcement and error handling for misconfigured zones or overlapping rules.
  - Synchronization of NAT configuration and state across control-plane elements (CONFIG_DB, APP_DB, ASIC_DB) and iptables programming.
  - Interaction between static and dynamic NAT rules, ensuring precedence and isolation.
- **Context in SONiC test framework:** These tests sit within the SONiC Pytest automation suite to provide regression coverage for static NAT functionality, exercising both forwarding data paths (via `ptfadapter` traffic) and management-plane operations (CLI, Redis DB, iptables) under the SONiC management test framework.

## 3. Detailed Breakdown of Sub-Testcases
- **`test_nat_static_basic`**
  - Configures a static NAT mapping and verifies bidirectional TCP/UDP translation across all configured directions. Confirms that other internal hosts are not translated. Ensures baseline static NAT functionality.
- **`test_nat_static_basic_icmp`**
  - Mirrors the basic test for ICMP flows, confirming that non-L4 protocols honor static NAT and that unrelated hosts remain untranslated. Validates protocol coverage beyond TCP/UDP.
- **`test_nat_static_napt`**
  - Configures static NAPT with specific port translations, sends bidirectional traffic, and confirms that unmatched ports are dropped. Verifies port-aware translation and enforcement.
- **`test_nat_clear_statistics_static_basic`**
  - After exercising traffic, verifies NAT counter increments, issues a `clear` operation, and checks that counters reset to zero for static NAT. Ensures statistics reporting behaves correctly.
- **`test_nat_clear_statistics_static_napt`**
  - Same as above but for static NAPT counters, covering both SNAT and DNAT directions.
- **`test_nat_clear_translations_static_basic`**
  - Confirms static translations appear in `show nat translations`, survive a `clear translations` operation, and that counters accumulate across additional traffic. Validates that static entries persist while dynamic ones would be removed.
- **`test_nat_clear_translations_static_napt`**
  - NAPT variant verifying persistence of port-based static translations when clearing translations and their continued use.
- **`test_nat_crud_static_nat`**
  - Exercises CLI add/remove for static NAT, inspects CONFIG_DB via `sonic-cfggen`, verifies traffic translation, and ensures deletion stops translation. Re-adds on a secondary port to validate repeatability. Tests CLI CRUD integrity for IP-only static NAT.
- **`test_nat_crud_static_napt`**
  - Extends CRUD verification to static NAPT with protocol/port attributes, ensuring correct CONFIG_DB keys (`GLOBAL_IP|PROTO|PORT`) and removal behavior, including repeated reconfiguration for a second port.
- **`test_nat_reboot_static_basic`**
  - Saves configuration, reboots (cold/fast), then validates that static NAT rules persist, traffic continues to translate, and TCP handshakes succeed. Confirms config persistence across reboots.
- **`test_nat_reboot_static_napt`**
  - Similar to above for static NAPT; includes ARP refresh (`check_peers_by_ping`) to ensure neighbor state after reboot.
- **`test_nat_static_zones_basic_snat`**
  - Intentionally misconfigures NAT zones (all interfaces outer zone) to show translation fails, then restores correct zones and verifies traffic works. Validates zone enforcement for SNAT traffic.
- **`test_nat_static_zones_basic_icmp_snat`**
  - ICMP version of the zone enforcement test to ensure zone checks apply to non-TCP/UDP flows.
- **`test_nat_static_zones_napt_dnat_and_snat`**
  - Misconfigures zones and validates both SNAT and DNAT traffic fail, then corrects zones and ensures NAPT translations succeed. Ensures zone configuration impacts both directions in NAPT scenarios.
- **`test_nat_static_iptables_add_remove`**
  - Verifies iptables programming before and after adding/removing static NAT rules and traffic flow. Ensures kernel rule insertion/removal aligns with CLI operations.
- **`test_nat_static_global_double_add`**
  - Attempts to add overlapping static rules via CLI and asserts that the command fails with the expected error. Validates conflict detection for global IP reuse.
- **`test_nat_static_interface_add_remove_interface_ip`**
  - Tests behavior when an interface IP is removed and re-added: confirms iptables rules disappear and return accordingly, and traffic works after restoration. Covers dependency on interface addressing.
- **`test_nat_static_interface_add_remove_interface`**
  - Similar but toggles the interface admin state (disable/enable) to ensure iptables programming remains and traffic resumes post-recovery. Validates resilience to interface flaps.
- **`test_nat_static_redis_global_pool_binding`**
  - Checks synchronization between APP_DB/CONFIG_DB for global NAT settings, pools, and bindings before and after modifying CLI configuration, including dynamic NAT setup. Ensures control-plane state consistency.
- **`test_nat_static_redis_napt`**
  - Validates that static NAPT entries are consistently reflected in APP_DB/CONFIG_DB and remain accurate after adding additional CLI rules.
- **`test_nat_static_redis_asic`**
  - Compares APP_DB NAPT entries with ASIC_DB `SAI_NAT_ENTRY` attributes to confirm hardware programming matches software state.
- **`test_nat_same_static_and_dynamic_rule`**
  - Configures both static and default dynamic NAT, ensures only static translations remain in `show nat translations`, and verifies traffic uses the static mapping with counters incrementing. Demonstrates precedence of static rules over dynamic ones.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `setup_test_env` provisions PTF interfaces, NAT zones, VRF/IP addressing, and yields interface type (loopback or port-in-LAG) alongside configuration data.
  - `protocol_type` parameterizes tests over TCP and UDP where applicable.
  - `apply_global_nat_config` (module-scope) ensures NAT feature is enabled and default timeouts are configured before tests, with cleanup via config reload.
  - `reload_dut_config`, `enable_nat_docker`, `cleaup_dut_route`, and `enable_outer_interfaces` provide cleanup/recovery hooks for specific scenarios.
  - Standard testbed fixtures (`duthost`, `ptfhost`, `ptfadapter`, `tbinfo`, `localhost`) supply SONiC host handles and traffic generation interfaces.
- **Topology constraints:** Requires a T0 testbed with functional PortChannels, VLAN1000, and ARISTA leaf VMs accessible to configure host and leaf directions.
- **Environmental prerequisites:** NAT feature must be supported in the DUT image; CLI commands (`config nat`, `sonic-cfggen`, `sonic-clear`) must be available; Redis CLI access via helper functions is assumed.

## 5. Key Inputs and Parameters
- **`direction` and `nat_type` strings** control whether flows are host↔TOR or leaf↔TOR and whether IP-only or port-specific translations are used.
- **`network_data` objects** from `get_network_data` encapsulate public/private IPs, expected translated endpoints, and port/channel data for traffic generation.
- **`DIRECTION_PARAMS`** enumerates path descriptors for bidirectional verification loops.
- **`protocol_type` fixture** switches between TCP and UDP to ensure coverage of major transport protocols.
- **Timeout constants** (`GLOBAL_NAT_TIMEOUT`, `GLOBAL_TCP_NAPT_TIMEOUT`, `GLOBAL_UDP_NAPT_TIMEOUT`) provide expected baseline values when validating DB state updates.
- **Port range constants** (`POOL_RANGE_START_PORT`, `POOL_RANGE_END_PORT`) define NAT pool expectations during overlap/error testing.
- **`setup_info` structure** includes NAT zone assignments, VRF definitions, and port-channel members that drive zone and interface manipulation tests.

## 6. External Libraries and Modules
- **Standard Python modules:** `copy`, `time`, `json`, and `re` for data duplication, timing gaps, JSON parsing, and regex validation.
- **`pytest`** for test parametrization, fixtures, and marking.
- **`tests.common.helpers.assertions.pytest_assert`** for assertion handling with descriptive failures.
- **`tests.common.reboot`** utility (`common_reboot`) to perform standardized reboot procedures during persistence tests.
- **`tests.nat.nat_helpers` module** supplies numerous helper functions/constants:
  - Configuration helpers (`apply_static_nat_config`, `configure_nat_over_cli`, `configure_dynamic_nat_rule`, `nat_zones_config`).
  - Traffic generators and verifiers (`generate_and_verify_traffic`, `generate_and_verify_icmp_traffic`, `generate_and_verify_traffic_dropped`, `generate_and_verify_not_translated_*`, `perform_handshake`).
  - State inspection utilities (`nat_statistics`, `nat_translations`, `crud_operations_basic/napt`, `dut_nat_iptables_status`, `get_redis_val`, `get_db_rules`).
  - Environment/utility functions (`get_network_data`, `get_l4_default_ports`, `check_peers_by_ping`, `dut_interface_control`, `exec_command`, `get_public_ip`).
- These helpers abstract SONiC CLI/DB interactions and PTF traffic operations, enabling concise test logic.

## 7. Unspecified Items
- Exact values for `DIRECTION_PARAMS`, NAT zone IDs, and `SETUP_CONF` contents originate from `nat_helpers.py` and are **not specified** within this test file.
- Detailed structure of `network_data` and `setup_info` dictionaries is defined externally in helpers and fixtures; precise schema is **not specified** here.
