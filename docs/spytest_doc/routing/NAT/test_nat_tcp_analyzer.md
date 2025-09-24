# NAT TCP Test Analyzer

## 1. Topology Type
- **Identified Topology:** D1–D2–D3 linear topology with single links `D1D2:1` and `D2D3:1`.
- **Inference Basis:** The `nat_pre_config()` helper calls `st.ensure_min_topology("D1D2:1", "D2D3:1")`, which provisions a minimum topology consisting of three DUTs (D1, D2, D3) connected in a chain with one link each between D1–D2 and D2–D3. This fixture supplies interface handles such as `vars.D1D2P1` and `vars.D2D3P1`, confirming the topology shape.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L38-L41】

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate that dynamic NAT (Network Address Translation) with TCP/UDP traceroute traffic performs correctly, ensuring that translations are created and tracked in the NAT table on the middle device (D2).
- **SONiC/SpyTest Context:** The test leverages SpyTest automation APIs (`st`, `ip_obj`, `nat_obj`) to configure interfaces, static routes, NAT zones, pools, and bindings on SONiC devices. It focuses on verifying NAT functionality and translation table updates as part of the NAT regression suite (`@pytest.mark.nat_regression1`).【F:spytest/tests/routing/NAT/test_nat_tcp.py†L14-L97】

## 3. Detailed Breakdown of Sub-Testcases
### `test_ft_dynamic_napt_traceroute`
- **Intent and Logic:**
  - Clears existing NAT translations and statistics to start from a clean state.
  - Initiates connectivity checks (`ping`) and a `traceroute` from D3 towards D1's address to trigger NAT traversal through D2.
  - Retrieves NAT translation entries on D2 for expected UDP destination ports produced by traceroute (`2000`, `2001`, `2002`) and validates that entries exist. If missing, it performs additional pings to stimulate traffic and marks the test as failed.
  - Reports success only when all expected translations are observed, proving that traceroute through NAT correctly updates the translation table.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L73-L103】
- **Relevance:** Demonstrates that traceroute traffic crossing the NAT boundary results in proper dynamic translation records, ensuring NAT handling of multi-probe traceroute sequences.

### Helper Functions
- **`nat_pre_config()`**
  - Sets up the testbed topology, validates platform support, configures IP addresses and static routes across D1–D3, enables NAT, assigns zones, creates NAT pool and binding, and verifies routing tables. This establishes the environment required for the traceroute NAT test.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L38-L71】
- **`nat_post_config()`**
  - Reverts configurations: removes zone settings, clears NAT configuration, disables the NAT feature, deletes static routes, and clears interface IP configuration, ensuring no side effects for subsequent tests.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L105-L113】
- **`util_nat_zone_config()`**
  - Utility to add or remove NAT zone assignments on interfaces, called during setup and teardown to manage interface-to-zone mapping.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L116-L126】

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `nat_module_config` (module scope, autouse) invokes `nat_pre_config()` before tests and `nat_post_config()` after, ensuring environment setup/cleanup.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L32-L37】
  - `cmds_func_hooks` (function scope) placeholder fixture for per-test hooks (currently no additional actions).【F:spytest/tests/routing/NAT/test_nat_tcp.py†L40-L45】
- **Topology Constraints:** Requires access to three DUTs with links D1–D2 and D2–D3 (`st.ensure_min_topology`).【F:spytest/tests/routing/NAT/test_nat_tcp.py†L38-L41】
- **Platform Constraints:** Uses `basic_obj.get_hwsku` and datastore `constants` to skip unsupported platforms (TH3).【F:spytest/tests/routing/NAT/test_nat_tcp.py†L41-L47】

## 5. Key Inputs and Parameters
- **Static Data Values:** IP addresses, masks, zones, protocol names, pool/binding names, global port range, and shell types defined in the `SpyTestDict` (`data`). These govern interface configuration, routing, NAT pool creation, and translation validation targets.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L13-L31】
- **NAT Pool and Binding:** `pool_tr`, `bind_tr`, and `global_port_range` specify the NAT resources on D2 used during testing.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L25-L31】【F:spytest/tests/routing/NAT/test_nat_tcp.py†L57-L69】
- **Protocol Selection:** `data.proto_udp` guides translation lookup for traceroute’s UDP probes.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L23-L24】【F:spytest/tests/routing/NAT/test_nat_tcp.py†L84-L102】

## 6. External Libraries and Modules
- **`pytest`** – Provides the testing framework, fixtures, and markers used to structure the test case.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L1-L2】
- **`spytest` (`st`)** – Core SpyTest utility for topology management, logging, datastore access, and result reporting.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L3-L5】【F:spytest/tests/routing/NAT/test_nat_tcp.py†L38-L71】
- **`SpyTestDict`** – Structured dictionary for storing test constants and parameters.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L5-L13】
- **`utilities.common` (`utils`)** – Supplies `exec_all` to run show commands in parallel for verification.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L7-L8】【F:spytest/tests/routing/NAT/test_nat_tcp.py†L64-L71】
- **`apis.routing.ip` (`ip_obj`)** – Provides IP configuration, routing, ping, and traceroute helpers for DUTs.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L9-L10】【F:spytest/tests/routing/NAT/test_nat_tcp.py†L48-L90】
- **`apis.routing.nat` (`nat_obj`)** – Enables NAT feature configuration, pool/binding management, translation queries, and clear commands.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L10-L11】【F:spytest/tests/routing/NAT/test_nat_tcp.py†L56-L104】
- **`apis.system.basic` (`basic_obj`)** – Used to gather hardware SKU information to validate platform support for NAT.【F:spytest/tests/routing/NAT/test_nat_tcp.py†L11-L47】

## 7. Unspecified Items
- Additional inputs from `testbed.yaml`, inventory files, or CLI parameters are **Not specified** within this test file.
- Any other topology viewers or diagrams are **Not specified**.
