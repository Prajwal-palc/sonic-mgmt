# CRM Test Case Analysis

## 1. Topology
- The module-level autouse fixture calls `st.ensure_min_topology("D1T1:2")`, indicating the test expects a topology with one DUT (D1) connected to one traffic generator (T1) with two participant links. This call also seeds the shared `vars` object used throughout the module.【F:spytest/tests/system/crm/test_crm.py†L29-L36】

## 2. Overall Test Purpose
- The shared workflow `crm_ft_test_all()` prepares routing, switching, ACL, and ECMP state on the DUT, then invokes `verify_thresholds()` to drive SONiC's CRM (Critical Resource Monitoring) subsystem across "used", "percentage", and "free" thresholds for every supported resource family. Threshold crossings are validated via syslog parsing, ensuring CRM raises and clears warnings when table usage changes under different traffic and configuration conditions.【F:spytest/tests/system/crm/test_crm.py†L530-L618】【F:spytest/tests/system/crm/test_crm.py†L340-L460】

## 3. Subtestcases and Rationale
- **Module setup (`ft_crm_module_hooks`)** – Establishes the minimum D1T1:2 topology context and clears residual IP configuration so subsequent CRM checks start from a clean baseline.【F:spytest/tests/system/crm/test_crm.py†L29-L35】
- **Shared executor (`crm_ft_test_all`)** – Lazily executed before any verification test; it identifies DUTs, programs CRM polling, collects initial resource counters, sets up VLAN/MAC tables, applies ACL templates, establishes IPv4/IPv6 BGP neighbors via both DUT and traffic generator, provisions ECMP static routes, and finally calls `verify_thresholds` to exercise CRM telemetry.【F:spytest/tests/system/crm/test_crm.py†L530-L618】【F:spytest/tests/system/crm/test_crm.py†L174-L314】
- **`verify_thresholds` – used thresholds** – Captures baseline usage, programs low/high "used" thresholds (handling ACL families specially), forces table drain by shutting interfaces and clearing MAC/FDB data, then restores interfaces to ensure CRM logs both exceed and clear events for absolute usage values.【F:spytest/tests/system/crm/test_crm.py†L340-L399】
- **`verify_thresholds` – percentage thresholds** – Resets limits, repopulates MAC entries, excludes unsupported families (SNAT/DNAT/IPMC), and toggles ACL/FDB state plus interface shutdowns to trigger percentage-based exceed/clear syslogs, validating CRM's relative usage monitoring.【F:spytest/tests/system/crm/test_crm.py†L401-L428】
- **`verify_thresholds` – free thresholds** – Configures "free" resource thresholds, re-enables interfaces, replays traffic, and waits for CRM to log free resource alarms; failure to observe logs is reported, ensuring CRM tracks remaining capacity transitions.【F:spytest/tests/system/crm/test_crm.py†L430-L460】
- **`check_logging_result`** – Aggregates WARNING-level syslogs looking for THRESHOLD_EXCEEDED and THRESHOLD_CLEAR messages across used, percentage, and free categories for each resource, updating `crm_test_result`. This gating step determines whether downstream subtests can pass.【F:spytest/tests/system/crm/test_crm.py†L462-L505】
- **Individual verification tests (`test_ft_crm_*`)** – Each pytest function calls `crm_ft_verify()` with a specific resource family (e.g., FDB, IPv4 route, ACL table). `crm_ft_verify` ensures the shared workflow has executed, then checks whether `check_test_status` recorded all six expected threshold events for that family, asserting pass/fail accordingly. This decomposes the CRM validation into per-resource subtests while reusing the common setup.【F:spytest/tests/system/crm/test_crm.py†L624-L689】

## 4. Dependencies and Prerequisites
- Requires the SpyTest topology utilities, particularly a D1T1:2 layout, and the ability to clear IP configuration at module start.【F:spytest/tests/system/crm/test_crm.py†L29-L35】
- Expects traffic generator access via `tgapi.get_handles` for BGP emulation, and DUT capabilities for VLAN, MAC, ACL, static routing, and BGP configuration through the imported API modules.【F:spytest/tests/system/crm/test_crm.py†L198-L314】
- Relies on platform constants to optionally skip SNAT/DNAT families on specific TH3 hardware, implying hardware SKU awareness via `base_obj.get_hwsku` and `vars.constants` seeded from the testbed definition.【F:spytest/tests/system/crm/test_crm.py†L563-L567】
- Optional IPv6 CRM coverage depends on the DUT supporting the "config-ipv6-command" feature flag.【F:spytest/tests/system/crm/test_crm.py†L609-L610】

## 5. Key Inputs and Their Sources
- Topology-derived identifiers such as `vars.D1`, `vars.D1T1P1`, and `vars.T1D1P1` come from `st.ensure_min_topology` and map to testbed.yaml definitions for the DUT and traffic generator ports.【F:spytest/tests/system/crm/test_crm.py†L33-L35】【F:spytest/tests/system/crm/test_crm.py†L585-L599】
- CRM configuration parameters (polling interval, resource counters, threshold dictionaries) and routing attributes (ASN, router IDs, neighbor counts, route prefixes) are instantiated within `crm_ft_test_all`, making them script-controlled constants for reproducible threshold exercises.【F:spytest/tests/system/crm/test_crm.py†L538-L606】
- VLAN ID 777, MAC population counts, and ECMP routes are defined in the script, while ACL tables are sourced from the imported JSON template `acl_data.acl_json_config_crm`, which is augmented with topology-specific ports before application.【F:spytest/tests/system/crm/test_crm.py†L174-L335】
- Syslog filtering relies on literal strings like "THRESHOLD_EXCEEDED" and the `resource_str` mapping that pairs logical resource names with CRM syslog tokens.【F:spytest/tests/system/crm/test_crm.py†L19-L25】【F:spytest/tests/system/crm/test_crm.py†L462-L505】

## 6. External Libraries and Roles
- `spytest` core (`st`, `tgapi`, `SpyTestDict`) supplies logging, topology discovery, traffic generator access, and structured data storage for the test.【F:spytest/tests/system/crm/test_crm.py†L4】
- `spytest.utils.poll_wait` provides polling utilities used to wait for CRM log generation.【F:spytest/tests/system/crm/test_crm.py†L5】【F:spytest/tests/system/crm/test_crm.py†L457-L459】
- `apis.system.crm`, `apis.system.logging`, `apis.system.interface`, `apis.system.basic`, `apis.switching.vlan`, `apis.switching.mac`, `apis.routing.ip`, `apis.routing.bgp`, and `apis.qos.acl` encapsulate SONiC management operations for CRM counters, syslog access, interface control, platform data, VLAN/MAC programming, IP/BGP configuration, and ACL application respectively.【F:spytest/tests/system/crm/test_crm.py†L7-L15】【F:spytest/tests/system/crm/test_crm.py†L174-L335】【F:spytest/tests/system/crm/test_crm.py†L340-L460】
- `tests.system.crm.acl_json_crm_config` supplies reusable ACL configuration templates tailored for CRM validation.【F:spytest/tests/system/crm/test_crm.py†L6】【F:spytest/tests/system/crm/test_crm.py†L330-L335】
- Python's standard `pytest` and `re` modules underpin test structure and IP manipulation helper logic.【F:spytest/tests/system/crm/test_crm.py†L1-L2】【F:spytest/tests/system/crm/test_crm.py†L53-L99】
