# VLAN Autostate Disabled Test Analyzer

## 1. Topology Type
- **Topology**: `t0`, `m0`, or `mx` (frontend topologies). The `pytestmark` applies `pytest.mark.topology("t0", "m0", "mx")`, indicating the test is valid for any of these three topologies.
- **Inference**: The mark is defined at the module level, so PyTest will only schedule this test when the testbed YAML specifies one of these topologies.

## 2. Overall Test Case Purpose
- **Goal**: Validate that VLAN interface autostate behavior is disabled in SONiC. Even if all VLAN member ports go down, the VLAN SVI should remain operationally up because SONiC binds VLANs to a single bridge interface that should not flap.
- **Context**: Within SONiC system testing, this ensures Layer 3 reachability does not depend on the oper-state of individual Layer 2 members once the VLAN has been created, confirming SONiC diverges from legacy autostate semantics.

## 3. Detailed Breakdown of Sub-Testcases
- **`test_autostate_disabled`**
  - **Intent**: Picks a VLAN whose SVI and at least one member are initially up. Shuts down all member ports in that VLAN, then verifies the VLAN interface still reports `oper_state` as `up`.
  - **Logic**:
    1. Collects running configuration facts (`get_running_config_facts`) to obtain VLAN memberships.
    2. Checks interface status and IP interface facts to find VLANs with SVI and any member up; skips if none.
    3. Chooses one VLAN, records original interface admin states.
    4. Calls `shutdown_multiple_with_confirm` to administratively disable all member ports, waiting until their oper state reads down and cleaning up running config overrides.
    5. Refreshes IP interface facts and asserts the VLAN SVI remains up via `pytest_assert`.
    6. Uses `restore_interface_admin_state` in a `finally` block to revert all interfaces to pre-test admin state (starting or shutting interfaces as needed).
  - **Relevance**: Demonstrates that disabling autostate keeps SVIs functional regardless of access port link status, preventing unexpected routing outages.

- **Helper Methods within `TestAutostateDisabled`**
  - **`restore_interface_admin_state`**: Splits interfaces by prior admin state and re-applies `shutdown`/`startup` to ensure the DUT returns to baseline after the test.
  - **`check_interface_oper_state`**: Convenience method to verify all specified interfaces report the expected operational state via `get_interfaces_status`.
  - **`shutdown_multiple_with_confirm`**: Wraps `duthost.shutdown_multiple`, waits for oper state transition to down using `wait_until`, and cleans up by deleting temporary running-config entries with `delete_running_config`.
  - **`startup_multiple_with_confirm`**: Inverse of the shutdown helper, leveraging `duthost.no_shutdown_multiple` and `wait_until` to confirm interfaces return to up state.
  - These helpers are essential for deterministic interface state control and verification, ensuring the main test can focus on SVI status validation.

## 4. Dependencies and Prerequisites
- **Fixtures**:
  - `duthosts`, `enum_frontend_dut_hostname`: Provide access to each DUT and select a frontend device in multi-DUT setups.
  - `loganalyzer`: Used in the autouse fixture to suppress expected log noise on specific platforms.
  - `ignore_expected_loganalyzer_exceptions`: Autouse fixture that extends log analyzer ignore patterns for platforms reporting unsupported autonegotiation errors when ports are shut.
- **Topology Constraints**: Requires a topology with VLANs configured (t0/m0/mx). Skips if no VLANs meet criteria.
- **DUT Capabilities**: The DUT must support `shutdown_multiple`/`no_shutdown_multiple` Ansible modules and expose `get_running_config_facts`, `get_interfaces_status`, and `show_ip_interface` helpers.

## 5. Key Inputs and Parameters
- `vlan_members_facts`: Derived from running config; enumerates VLANs and their member ports, used to select candidate VLANs.
- `ifs_status`: Captures interface admin/oper status to identify members that can be toggled and to restore state later.
- `ip_ifs`: IP interface facts, providing the VLAN SVI operational state for validation.
- `vlan_available`: Locally constructed list of VLANs satisfying the initial state criteria.
- Timing parameters for `wait_until` (60s timeout, 5s interval) ensure transitions complete before assertions.

## 6. External Libraries and Modules
- `logging`: Provides logging for interface state transition waits and error reporting.
- `pytest`: Supplies the testing framework, fixtures, marks, and skip/fixture functionality.
- `tests.common.helpers.assertions.pytest_assert`: Custom assertion helper that integrates with SONiC test utilities.
- `tests.common.utilities.wait_until`: Utility to poll until a condition is met when checking interface state transitions.
- `tests.common.utilities.delete_running_config`: Removes temporary configuration changes introduced during shutdown operations.

## 7. Unspecified Items
- References to specific testbed YAML entries, host inventory details, or CLI parameters are **not specified** within this file.
