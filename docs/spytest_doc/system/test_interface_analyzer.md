# Interface System Tests Analyzer

## 1. Topology type
- **Topology**: Dual DUT with a traffic generator fan-out — specifically two inter-DUT links (`D1D2:2`) and two DUT-to-TGen links (`D1T1:2`).
- **Evidence & Inference**:
  - The module-level autouse fixture invokes `st.ensure_min_topology("D1D2:2", "D1T1:2")`, explicitly requesting this arrangement.
  - Subsequent usage of handles such as `vars.D1D2P1`, `vars.D1D2P2`, `vars.D1T1P1`, `vars.T1D1P1`, etc., confirms that the tests drive two links between the DUTs and connect both DUT1 access ports to traffic generator ports for VLAN-based traffic.
  - The traffic generator configuration for streams between `T1D1P1` and `T1D1P2` further substantiates the presence of an external TG connected to DUT1.

## 2. Overall test case purpose
- **Primary Goal**: Validate SONiC interface feature functionality and resilience across multiple operational dimensions — jumbo frame forwarding, FEC negotiation, administrative flap handling, configuration persistence, and statistics accuracy under stress.
- **Context in SONiC/SpyTest**:
  - These scenarios cover foundational L2/L3 behaviors that SONiC must uphold for stable deployments.
  - SpyTest orchestrates device interactions (configuration, verifications, TG control) to emulate real-world operational workflows such as VLAN traffic forwarding, inter-DUT connectivity, and error counter monitoring.
  - Ensuring reliability of interface operations is critical before higher-layer protocol suites (BGP, routing resiliency, etc.) are validated.

## 3. Detailed breakdown of sub-testcases

### `test_ft_port_frame_fwd_diff_mtu`
- **Intent & Flow**:
  1. Retrieves current MTU for two DUT1 access interfaces to ensure baseline knowledge.
  2. Raises MTU on both ports to `4096` using `intfapi.interface_properties_set`.
  3. Runs traffic generator streams of `4096` and `9216` byte frames (pre-created during setup) across the VLAN, then stops them after a brief run.
  4. Validates packet counts with `tgapi.validate_tgen_traffic`, expecting lossless forwarding between TGen ports.
- **Why it matters**: Verifies that the DUT preserves forwarding capability for jumbo frames after MTU adjustments, preventing unexpected drops for oversized payloads in production VLAN scenarios.

### `test_ft_port_fec_nofec`
- **Intent & Flow**:
  1. Reads negotiated speed on the inter-DUT link (`vars.D1D2P1`).
  2. Depending on speed, selects relevant FEC pairs (`none` with either `fc` or `rs`).
  3. Calls helper `port_fec_no_fec` to deliberately mismatch FEC on DUT1, expecting both sides to detect mismatch and drive links down, then restore matching FEC, expecting links to recover.
  4. Helper logic performs platform-aware handling for TH3 hardware and polls interface status on both DUTs for up/down transitions.
- **Why it matters**: Confirms FEC settings are enforced consistently, guaranteeing interoperability with adjacent devices and validating platform-specific expectations.

### `test_ft_port_fn_verify_shut_noshut`
- **Intent & Flow**:
  1. Configures IPv4 addresses on the inter-DUT link and verifies bidirectional connectivity via ping.
  2. Performs three admin `shutdown`/`noshutdown` cycles on DUT1 interface without immediate verification to simulate real operations under flapping conditions.
  3. Re-verifies pings to ensure data-plane connectivity survives the flaps.
  4. Executes `rbapi.config_save_reload(vars.D1)` to persist configuration, then removes IPs on both ends to leave device clean.
  5. Runs additional shut/no-shut cycles and polls interface operational status to confirm they return to `up` state on both DUTs.
- **Why it matters**: Exercises interface resiliency and configuration persistence, validating that repeated administrative actions and config reloads do not leave ports stuck or connectivity broken.

### `test_ft_ovr_counters`
- **Intent & Flow**:
  1. Clears interface counters and TG stats, then runs continuous jumbo traffic on both DUT1 access ports expecting no overflow increments (`rx_ovr`, `tx_ovr`).
  2. Collects counter snapshots; any non-zero overflow value triggers an error path.
  3. Resets counters, lowers MTU on one port (`vars.D1T1P1`) to `2000`, and replays traffic exceeding the new MTU.
  4. Reads `rx_err` to ensure error counters increment for oversized frames while overflow counters stay at zero; failure to see errors results in test failure.
  5. Fixture `interface_func_hooks` restores default MTU afterward.
- **Why it matters**: Ensures operational counters correctly differentiate between overflow and MTU violation events, enabling accurate monitoring and troubleshooting.

### Helper & Fixture Components
- **`interface_module_hooks` (module-scoped autouse)**:
  - Ensures minimum topology, initializes shared `intf_data`, creates VLAN, attaches access members, obtains TG handles, clears TG stats, and creates multiple traffic streams (`mtu1`, `mtu2`, `traffic_tg1`, `traffic_tg2`).
  - Handles teardown by clearing VLAN configuration and resetting TG ports.
- **`interface_func_hooks` (function-scoped autouse)**:
  - Provides post-test cleanup to restore MTU defaults when `test_ft_ovr_counters` modifies them, preventing cross-test contamination.
- **`initialize_variables` helper**:
  - Populates all reusable parameters (IPs, masks, MTUs, MACs, VLAN ID, wait intervals) and records the default MTU to support cleanup.
- **`port_fec_no_fec` helper**:
  - Abstracts FEC toggling logic, including validation for expected link state changes, platform-specific checks for TH3 hardware, and error reporting.

## 4. Dependencies and prerequisites
- **Fixtures**: `interface_module_hooks` and `interface_func_hooks` must execute for environment setup and cleanup; both rely on SpyTest fixture injection.
- **Topology Requirements**: Needs two SONiC DUTs with at least two interconnect links and a traffic generator with two ports connected to DUT1. VLAN functionality and FEC configuration support on involved interfaces are prerequisites.
- **TG Capability**: Access to a supported traffic generator (through `tgapi`) capable of VLAN-tagged streams and counter collection.
- **Platform Knowledge**: `base_obj.get_hwsku` is used to detect TH3 platforms; corresponding constants must exist in `vars.constants` for conditional FEC handling.

## 5. Key inputs and parameters
- **`vars` Topology Handles**: Provide DUT identifiers (`vars.D1`, `vars.D2`), TG ports (`vars.T1D1P1`, `vars.T1D1P2`), and interconnect ports (`vars.D1D2P1`, `vars.D1D2P2`) used across tests and helpers.
- **Interface MTU Values**: `intf_data.mtu1` (`4096`), `intf_data.mtu2` (`9216`), `intf_data.mtu` (`2000`), and `intf_data.mtu_default` (queried from DUT) dictate frame sizes and cleanup targets.
- **VLAN ID & MACs**: `intf_data.vlan_id` (randomly chosen) and `source_mac`/`destination_mac` feed traffic generator configuration.
- **IP Addressing**: `intf_data.ip_address` and `intf_data.ip_address1` with `/24` mask enable ping validation over the inter-DUT link.
- **Traffic Generator Streams**: Identifiers cached in `intf_data.streams` control which streams run in each test (`mtu1`, `mtu2`, `traffic_tg1`, `traffic_tg2`).
- **FEC Parameters**: `fec` lists (`["none", "fc"]` or `["none", "rs"]`) influence expected link behavior during `port_fec_no_fec` execution.
- **Timing Controls**: `intf_data.wait_sec` (10 seconds) determines traffic run durations before counter sampling.

## 6. External libraries and modules
- **`pytest`**: Supplies fixture and marker functionality enabling structured setup/teardown and test categorization.
- **`spytest` modules (`st`, `tgapi`, `SpyTestDict`)**: Provide logging, topology provisioning, shared dict storage, and traffic generator interfaces.
- **`apis.switching.vlan` (`vlanapi`)**: Handles VLAN creation, membership addition, and cleanup on DUTs.
- **`apis.system.interface` (`intfapi`)**: Core interface management API — configuring properties (MTU, FEC), clearing counters, verifying operational status, and executing shut/no-shut actions.
- **`apis.routing.ip` (`ipapi`)**: Manages IP configuration on interfaces and executes ping diagnostics.
- **`apis.system.reboot` (`rbapi`)**: Provides `config_save_reload` to validate persistence across warm reboots/config reloads.
- **`apis.system.basic` (`base_obj`)**: Offers platform metadata (e.g., hardware SKU) driving conditional logic in FEC tests.
- **`utilities.common.random_vlan_list`**: Supplies non-conflicting VLAN IDs for setup.

## 7. Unspecified items
- **Exact hardware models, ASICs, or SKU inventory**: Not specified (beyond TH3 conditional logic).
- **Traffic generator vendor/model and licensing details**: Not specified.
- **External configuration sources (testbed.yaml, group_vars) beyond topology handles**: Not specified.
- **Failure handling procedures after `report_fail` invocations**: Not specified in this module.
