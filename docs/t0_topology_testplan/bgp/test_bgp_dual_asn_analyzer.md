# Test Plan Analysis: `tests/bgp/test_bgp_dual_asn.py`

## 1. Topology Type
- **Topology:** `t0`.
- **Evidence & Reasoning:** The module-level `pytestmark` decorates the test with `@pytest.mark.topology("t0")`, explicitly constraining execution to the T0 topology. No other topology hints (e.g., dual ToR markers) override this setting.

## 2. Overall Test Case Purpose
- **Goal:** Validate SONiC's BGP speaker behavior when multiple peer ranges with different autonomous system numbers (ASNs) are configured on a T0 device.
- **Scope in SONiC Test Framework:** The test verifies that
  - only peers defined within configured `BGP_PEER_RANGE` objects can establish sessions,
  - sessions honor their designated peer ASN values,
  - IPv4 route advertisement and persistence across peer-range modifications remain correct, and
  - removal of a peer range tears down the corresponding sessions while preserving others.
- **Context:** Ensures dual-ASN support for BGP speaker functionality, covering configuration CRUD flows via the `CONFIG_DB`, ExaBGP-driven neighbor emulation on the PTF host, and route validation on the DUT.

## 3. Detailed Breakdown of Sub-Testcases
### `test_bgp_dual_asn_v4`
- **Intent:** End-to-end validation of dual-ASN peer range handling over IPv4.
- **Workflow:**
  1. **Environment Preparation:**
     - Instantiate `BgpDualAsn` helper to gather DUT loopback addresses, VLAN interfaces, and derive two peer subnets and specific peer IPs per subnet.
     - Configure PTF interfaces with generated addresses, ensure reachability (ARP/ND priming), and clean any existing BGP peer range configuration.
  2. **First Peer Range Provisioning:**
     - Add an initial `BGP_PEER_RANGE` entry (IPv4+IPv6) tied to the DUT loopbacks and ASN `NEIGHBOR_ASN_LIST[0]`.
     - Launch an ExaBGP session using the first peer address/ASN pair; wait until the BGP session is established and record uptime.
     - Announce prefix `PREFIX` and verify it is programmed on the DUT.
  3. **Negative Control:**
     - Start a second ExaBGP session using a peer address outside the configured range/ASN, expecting the session to remain down and therefore blocking unauthorized neighbors.
  4. **Second Peer Range Addition:**
     - Extend `BGP_PEER_RANGE` with an additional IPv4-only entry using the second subnet and ASN `NEIGHBOR_ASN_LIST[1]`.
     - Confirm the first neighbor remains established and that its route persists.
     - Bring up the second peer; once established, announce `PREFIX_2` and verify both advertised routes exist.
     - Confirm no flapping by comparing stored uptime deltas against wall-clock time.
  5. **Cleanup Validation:**
     - Remove the original peer-range entry and ensure the corresponding first neighbor session goes down while the second remains unaffected.
  6. **Teardown:** Ensured by `dual_asn_teardown`, stopping ExaBGP instances, flushing PTF/DUT state, and restoring configuration checkpoints.
- **Relevance:** Demonstrates correct dual-ASN peer range management, session gating, route propagation, and cleanup—core requirements for multitenant BGP speaker deployments.

### Helper Structures & Functions
- **`BgpDualAsn` Class:** Encapsulates setup/teardown logic, peer subnet generation, PTF port/address configuration, and route priming. Central to maintaining deterministic test state.
- **`bgp_peer_range_add_config` / `bgp_peer_range_delete_config`:** Apply JSON patches to `CONFIG_DB` to create or remove `BGP_PEER_RANGE` objects using generic utility helpers (`apply_patch`, `format_json_patch_for_multiasic`, etc.). Ensure configuration operations succeed and reflect in `show runningconfiguration bgp` output.
- **`start_peer_ipv4_bgp_session`:** Wrapper around PTF ExaBGP control to instantiate peers with provided ASN/port parameters, including readiness checks via `wait_tcp_connection`.
- **`verify_bgp_session`, `get_bgp_uptime`, `check_bgp_routes_exist`, `announce_route`:** Provide assertions for session establishment, uptime tracking, route presence, and advertisement, supporting the core validation steps above.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `duthosts`, `rand_one_dut_hostname`: provide access to the targeted DUT in multi-DUT testbeds.
  - `ptfhost`: control-plane for ExaBGP neighbor emulation and interface configuration.
  - `localhost`: used for TCP readiness checks against ExaBGP's HTTP API.
  - `tbinfo`: supplies topology metadata (VLANs, PTF port mappings, topology name).
  - `setup_env` (module autouse): creates configuration checkpoints and restores BGP speaker settings post-test.
  - `check_image_version` (module autouse): guards against running on unsupported SONiC releases.
  - `toggle_all_simulator_ports_to_rand_selected_tor_m`: imported fixture (dual ToR support) though not directly invoked in logic beyond ensuring proper simulator state.
- **Topology Constraints:** Requires a T0 topology with at least one VLAN interface, accessible loopback addresses, and PTF connectivity.
- **PTF Requirements:** Ability to run ExaBGP instances and configure sub-interfaces.

## 5. Key Inputs and Parameters
- **Static Constants:**
  - Peer group names (`BGPSLB*`), prefixes (`PREFIX`, `PREFIX_2`, `PREFIX_V6*`), neighbor ASNs (`NEIGHBOR_ASN_LIST`), and ExaBGP control ports (`NEIGHBOR_PORT_LIST`). These control naming, route verification targets, and ExaBGP API connectivity.
- **Dynamic Inputs:**
  - Loopback and VLAN interface data extracted from `mg_facts` via `duthost.get_extended_minigraph_facts(tbinfo)` and helper functions. Determine peer IP ranges, PTF port bindings, and next-hop configuration.
  - Randomized peer IP selection within derived subnets ensures coverage across valid address space.
  - Runtime timestamps for uptime comparison detect session flaps.
- **Configuration Data Sources:** `CONFIG_DB` patches define `BGP_PEER_RANGE` objects; `show runningconfiguration bgp` outputs validate applied changes.

## 6. External Libraries and Modules
- **Standard Library:** `time`, `logging`, `ipaddress`, `random`, `re`, `datetime`, `timedelta` for timing, logging, IP calculations, and regex validation.
- **PyTest:** `pytest`, fixtures, marks, and assertion helpers for structured test execution.
- **SONiC Test Utilities:**
  - `tests.common.constants`, `tests.common.utilities` (skip logic, wait helpers),
  - `tests.common.helpers.assertions.pytest_assert` for consistent assertion messages,
  - `tests.common.gu_utils` for configuration checkpoints, patch application, and temporary file management,
  - `tests.common.helpers.dut_ports` for VLAN interface introspection,
  - `tests.common.dualtor.mux_simulator_control` fixture for dual-tor port toggling.
- **ExaBGP Helpers:** `bgp_helpers.update_routes` to program routes via ExaBGP HTTP API.

## 7. Unspecified Items
- Authentication details for DUT/PTF access: **Not specified**.
- Explicit cleanup expectations for non-BGP state (e.g., VLAN members beyond first two): **Not specified**.
- IPv6 dual-ASN validation (beyond IPv4 flows) within this file: **Not specified**.
