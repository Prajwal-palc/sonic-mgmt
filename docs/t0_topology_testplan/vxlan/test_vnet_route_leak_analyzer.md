# VNET Route Leak Test Analysis

## 1. Topology Type
- **Topology:** `t0`.
- **Inference:** The module-wide `pytestmark` decorates the test with `pytest.mark.topology("t0")`, indicating the DUT is orchestrated in a T0 (leaf-spine with servers) topology. No other topology markers are present, so this mark defines the testbed expectation. 【F:tests/vxlan/test_vnet_route_leak.py†L15-L27】

## 2. Overall Test Case Purpose
- **Goal:** Validate that VNET routes programmed on the DUT are not leaked to external BGP neighbors, even after disruptive operations.
- **Scope in SONiC testing:** Ensures VxLAN/EVPN-based virtual networks maintain tenant route isolation. The test checks the steady state, resilience to BGP service restart, and persistence across `config reload`, aligning with SONiC regression for control-plane correctness in overlay networking. 【F:tests/vxlan/test_vnet_route_leak.py†L105-L186】

## 3. Detailed Breakdown of Sub-Testcases
### `test_vnet_route_leak`
- **Intent & Flow:**
  1. Uses the `configure_dut` fixture to pre-provision VNET/VxLAN configuration and clean up afterward if requested.
  2. Calls `get_leaked_routes` to collect all VNET route prefixes and ensure none are advertised to any BGP neighbor (`pytest_assert` expects an empty leak map).
  3. Restarts the BGP service and waits (via `wait_until` + `bgp_connected`) for all BGP sessions to re-establish, then re-checks for leaked routes.
  4. Saves `CONFIG_DB`, performs `config_reload`, waits for BGP to converge again, and performs a final leak check.
- **Why it matters:** Validates isolation of VNET routing information at multiple lifecycle stages, assuring that configuration persistence and control-plane restarts do not introduce route leakage to upstream peers. 【F:tests/vxlan/test_vnet_route_leak.py†L105-L186】

### Helper Functions & Fixtures
- **`configure_dut` fixture:** Creates VNET/VxLAN environment (clears FDB, generates/applies configs) before tests and optionally restores configuration, cleans routes, removes tunnels, and restarts BGP afterward. Critical for setting up the testbed state and guaranteeing cleanup. 【F:tests/vxlan/test_vnet_route_leak.py†L29-L86】
- **`get_bgp_neighbors`:** Parses `show ip bgp summary` output to list neighbor IPs, forming the basis for subsequent state checks. 【F:tests/vxlan/test_vnet_route_leak.py†L88-L117】
- **`bgp_connected`:** Verifies all BGP sessions are established by cross-referencing neighbors from `get_bgp_neighbors` with `duthost.check_bgp_session_state`. Used in post-restart convergence waits. 【F:tests/vxlan/test_vnet_route_leak.py†L119-L137】
- **`get_leaked_routes`:** Retrieves VNET route prefixes and inspects each neighbor’s advertised routes to detect leaks, returning a defaultdict keyed by neighbor. Central to validating isolation. 【F:tests/vxlan/test_vnet_route_leak.py†L139-L171】

## 4. Dependencies and Prerequisites
- **Fixtures:** `configure_dut`, `minigraph_facts`, `duthosts`, `rand_one_dut_hostname`, `vnet_config`, `vnet_test_params` (injected via fixture stack). These provide device access, topology facts, and VNET parameters essential for configuration and validation. 【F:tests/vxlan/test_vnet_route_leak.py†L29-L86】【F:tests/vxlan/test_vnet_route_leak.py†L173-L186】
- **Topology Constraint:** Marked for Mellanox ASICs via `pytest.mark.asic("mellanox")`, indicating the test is scoped to platforms supporting required VxLAN features. 【F:tests/vxlan/test_vnet_route_leak.py†L15-L27】
- **Utilities:** Relies on SONiC test utilities (`wait_until`, `config_reload`, VNET helpers) for orchestration.

## 5. Key Inputs and Parameters
- **`request.config.option.num_routes`:** CLI-provided route count controlling how many VNET routes are programmed during setup. 【F:tests/vxlan/test_vnet_route_leak.py†L49-L55】
- **`vnet_test_params` & `vnet_config`:** Fixture-driven dictionaries that define VNET topology, cleanup behavior (e.g., `CLEANUP_KEY`), and tunnel configuration. They determine how the DUT is configured and whether teardown occurs. 【F:tests/vxlan/test_vnet_route_leak.py†L29-L86】
- **Command constants:** Strings for operational commands (`show vnet routes all`, `show ip bgp summary`, service restarts, config save/reload) guiding device interactions. 【F:tests/vxlan/test_vnet_route_leak.py†L19-L44】

## 6. External Libraries and Modules
- **`logging`:** Provides logging for setup, teardown, and validation steps.
- **`pytest`:** Supplies fixture and assertion framework, plus topology/asic markers.
- **`re`:** Used for regex matching neighbor IPs in CLI output.
- **`collections.defaultdict`:** Stores leaked routes keyed by neighbor IPs.
- **`tests.common.helpers.assertions.pytest_assert`:** Enhanced assertion wrapper for consistent failure messaging.
- **`tests.common.utilities.wait_until`:** Polling utility to wait for BGP convergence.
- **`.vnet_utils` helpers:** Generate/apply VNET configs and perform cleanup of routes, VNets, and tunnels.
- **`tests.common.config_reload.config_reload`:** Executes SONiC config reload to validate persistence.

## 7. Unspecified Items
- Source fixtures for `vnet_config`, `vnet_test_params`, and default values for `num_routes` are declared elsewhere; their concrete definitions are **Not specified** within this file.
- Detailed topology diagram or DUT neighbor inventory is **Not specified** in the test case.
