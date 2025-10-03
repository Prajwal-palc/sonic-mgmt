# VLAN Secondary Subnet Test Plan Analyzer

## 1. Topology Type
- **Topology:** Supports both `t0` and `m0` topologies as indicated by `pytestmark = [pytest.mark.topology("t0", "m0")]`.
- **Inference:** The topology markers declare which Sonic testbed layouts the test targets. These markers inform PyTest/SONiC test orchestration to run the suite on devices under either a T0 (leaf-spine with server-facing VLANs) or M0 (modular) setup.

## 2. Overall Test Case Purpose
- **Goal:** Validate that secondary IPv4 subnets configured on VLAN interfaces are correctly applied, reflected in operational state (`show ip interface`), persisted in Redis DB, and cleanly removed.
- **Context:** Within SONiC regression, this ensures Layer-3 interface management preserves secondary address semantics, which is crucial for multi-homed VLAN connectivity and configuration integrity.

## 3. Detailed Breakdown of Sub-Testcases

### `test_existing_secondary_subnet(duthost, tbinfo)`
- **Intent & Logic:**
  1. Uses `get_secondary_subnet` helper to discover pre-configured secondary subnets on the DUT.
  2. Skips the test if none exist, fails if an IPv6 secondary subnet appears (IPv4 expected).
  3. Builds CIDR string from returned address/prefix and invokes `check_secondary_subnet_exist` to validate CLI and Redis state.
- **Relevance:** Confirms that existing static configuration is operational and stateful before manipulating interfaces, ensuring baseline correctness.

### `test_secondary_subnet(duthost)`
- **Intent & Logic:**
  1. Retrieves VLAN interface list via `get_vlan_interface_list` and selects the first interface.
  2. Configures a constant IPv4 secondary address (`SECONDARY_IP`) using `config interface ip add ... --secondary`.
  3. Waits briefly, then calls `check_secondary_subnet_exist` to confirm the new configuration is visible in `show ip interface` and Redis DB.
  4. Removes the secondary address with `config interface ip remove ...` and validates the cleanup through `check_secondary_subnet_not_exist`.
- **Relevance:** Exercises add/remove workflow to ensure SONiC correctly handles dynamic secondary subnet configuration lifecycle.

### Helper Functions
- **`check_secondary_ip_interface`**: Parses structured `show ip interface` output, coalescing rows belonging to the same interface and detecting the secondary CIDR. Enables consistent reuse for presence and absence checks.
- **`check_secondary_subnet_exist`**: High-level validator verifying CLI state and Redis entries, including that the `secondary` attribute is set to `true`. Ensures configuration persistence and metadata correctness.
- **`check_secondary_subnet_not_exist`**: Mirrors the previous helper to confirm removal from both CLI and Redis contexts. Critical for cleanup verification.
- **`get_secondary_subnet` / `get_vlan_interface_list` (imported)**: Provide discovery of secondary subnets and VLAN interfaces from SONiC helpers, abstracting DUT queries.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `duthost`: Provides command execution and state inspection on the DUT.
  - `tbinfo`: Supplies topology-specific metadata used by `get_secondary_subnet`.
- **Topology Constraints:** Requires DUTs set up as `t0` or `m0` with VLANs configured; at least one VLAN interface must exist.
- **Helpers:** Relies on `tests.common.helpers.dut_ports.get_secondary_subnet` and `get_vlan_interface_list` for data gathering.

## 5. Key Inputs and Parameters
- **`SECONDARY_IP`:** Hard-coded `66.66.66.66/23` used to test add/remove operations.
- **Data from `get_secondary_subnet`:** Provides `vlan_interface`, address, prefix length, and IP version—determines validation path.
- **VLAN Interface List:** Drives which interface is exercised for configuration changes.
- **Redis Keys:** `VLAN_INTERFACE|<interface>|<ip>` entries verified to confirm persistence.

## 6. External Libraries and Modules
- **`logging`:** Emits informational logs about findings (e.g., locating secondary IPs).
- **`pytest`:** Provides test framework features, including markers, fixtures, assertion handling, and skip/fail mechanics.
- **`time`:** Introduces short delays (`sleep`) to allow configuration propagation.
- **`tests.common.helpers.assertions.pytest_assert`:** Custom assert wrapper aligning with SONiC reporting expectations.
- **`tests.common.helpers.dut_ports.get_secondary_subnet` / `get_vlan_interface_list`:** SONiC-specific utilities for querying VLAN configuration state.

## 7. Unspecified Items
- Inventory of precise DUT hardware models, exact topology diagram, and any additional environment setup steps are **Not specified** in the test file.
