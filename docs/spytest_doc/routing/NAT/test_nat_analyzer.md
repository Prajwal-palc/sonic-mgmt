# NAT Test Suite Analyzer

## 1. Topology Type
- **Topology:** `D1T1:2` (one DUT with a single traffic generator using two ports).
- **Inference:** The module-level fixture `nat_module_config` calls `st.ensure_min_topology("D1T1:2")`, explicitly requesting a topology with one device under test (D1) connected to a traffic generator (T1) with two links. This aligns with the utility helpers that configure two TG ports (`vars.T1D1P1`, `vars.T1D1P2`) and corresponding DUT interfaces.【F:spytest/tests/routing/NAT/test_nat.py†L88-L114】【F:spytest/tests/routing/NAT/test_nat.py†L140-L158】

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate NAT functionality on a SONiC device, with emphasis on ensuring NAT translation state behaves correctly across service restarts.
- **Context in SONiC/SpyTest:** The suite prepares extensive static and dynamic NAT configurations (including pools, bindings, static entries, and twice NAT) and generates traffic via a traffic generator to populate translation tables. Within SpyTest, this ensures NAT features operate correctly with orchestrated traffic and remain resilient when the NAT container is restarted.【F:spytest/tests/routing/NAT/test_nat.py†L115-L205】

## 3. Detailed Breakdown of Sub-Testcases
### `test_ft_nat_docker_restart`
- **Intent & Logic:**
  - Sends previously defined dynamic NAT traffic from the traffic generator to create UDP NAPT translations.
  - Stops and restarts the NAT service (`systemctl stop/start nat`) on the DUT, waiting for the container to shut down and come back up.
  - After restart, checks that the transient dynamic NAT translation no longer exists, confirming cleanup, while a static NAT translation is restored, confirming persistence of configured entries.
  - On failure, gathers debugging data before failing the test; otherwise, reports success.【F:spytest/tests/routing/NAT/test_nat.py†L120-L139】
- **Relevance:** Ensures NAT resilience during service restarts—dynamic sessions should not survive a restart (avoiding stale translations), whereas static rules should persist. This is critical for validating operational stability of SONiC's NAT feature.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `nat_module_config` (module scope, autouse) provisions topology, initializes data variables, applies DUT and TG configurations, and performs cleanup in `nat_epilog` after tests complete.【F:spytest/tests/routing/NAT/test_nat.py†L85-L119】【F:spytest/tests/routing/NAT/test_nat.py†L169-L205】
  - `nat_func_hooks` (function scope, autouse) clears interface counters and NAT statistics before each test to avoid residue between runs.【F:spytest/tests/routing/NAT/test_nat.py†L119-L124】
- **Topology:** Requires two TG ports linked to the DUT, with NAT zones configured on DUT interfaces (`vars.D1T1P1`, `vars.D1T1P2`).【F:spytest/tests/routing/NAT/test_nat.py†L173-L205】
- **Utilities:** Relies on helper functions (`nat_prolog`, `nat_epilog`, `nat_tg_config`, etc.) to configure traffic generators, static routes, NAT pools, and zones.

## 5. Key Inputs and Parameters
- **Addressing & Ports:** `nat_initialize_variables` populates numerous IPv4 addresses, subnet masks, port ranges, and NAT parameters (static mappings, pool ranges, port lists). These govern TG traffic profiles, NAT static/dynamic configuration, and verification criteria.【F:spytest/tests/routing/NAT/test_nat.py†L21-L83】
- **Behavioral Controls:** Flags such as `data.nat_pkt_cap_enable`, `data.wait_nat_stats`, and `data.wait_time_after_docker_restart` adjust waiting times and packet capture settings based on platform capabilities (`st.is_feature_supported`, `st.is_vsonic`, `st.is_sonicvs`).【F:spytest/tests/routing/NAT/test_nat.py†L74-L83】
- **Service Actions:** `data.config_add/del`, zone IDs, pool/bind names, and twice NAT IDs direct how helper functions add or remove configurations on the DUT.【F:spytest/tests/routing/NAT/test_nat.py†L56-L83】【F:spytest/tests/routing/NAT/test_nat.py†L173-L205】

## 6. External Libraries and Modules
- **`pytest`** – Provides fixture management and test execution framework.【F:spytest/tests/routing/NAT/test_nat.py†L18-L19】
- **SpyTest Core (`st`, `tgapi`, `SpyTestDict`)** – Supplies logging, topology utilities, traffic generator abstraction, and structured data storage for test variables.【F:spytest/tests/routing/NAT/test_nat.py†L21-L25】
- **Routing & System APIs:**
  - `apis.routing.ip` – Configures IP addresses and static routes on the DUT.【F:spytest/tests/routing/NAT/test_nat.py†L27-L29】【F:spytest/tests/routing/NAT/test_nat.py†L156-L185】
  - `apis.routing.nat` – Enables/disables NAT, configures static/dynamic entries, manages NAT statistics and translations.【F:spytest/tests/routing/NAT/test_nat.py†L27-L29】【F:spytest/tests/routing/NAT/test_nat.py†L173-L204】
  - `apis.routing.arp` – Used in debugging to inspect ARP tables.【F:spytest/tests/routing/NAT/test_nat.py†L27-L29】【F:spytest/tests/routing/NAT/test_nat.py†L226-L233】
  - `apis.switching.vlan` – Cleans up VLAN configuration during teardown.【F:spytest/tests/routing/NAT/test_nat.py†L29-L30】【F:spytest/tests/routing/NAT/test_nat.py†L200-L205】
  - `apis.system.basic` – Interacts with system services, retrieves hardware SKU, and interface MAC addresses.【F:spytest/tests/routing/NAT/test_nat.py†L30-L31】【F:spytest/tests/routing/NAT/test_nat.py†L158-L205】
  - `apis.system.interface` – Clears and displays interface counters, supporting test reset and debugging.【F:spytest/tests/routing/NAT/test_nat.py†L31-L32】【F:spytest/tests/routing/NAT/test_nat.py†L119-L124】【F:spytest/tests/routing/NAT/test_nat.py†L226-L231】

## 7. Unspecified Items
- **Testbed YAML References:** Not specified.
- **Group Variables / CLI Parameters:** Not specified beyond values defined within the test file.

