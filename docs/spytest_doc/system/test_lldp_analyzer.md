# LLDP System Test Analyzer

## 1. Topology Type
- **Topology:** Two SONiC DUT topology with at least two interconnect links (D1D2:2) and management network access.
- **Inference:** The module-level fixture `lldp_snmp_module_hooks` invokes `st.ensure_min_topology("D1D2:2")`, requiring two devices (D1 and D2) with two links. Additional references to `vars.D1D2P1`, `vars.D1D2P2`, and management interface `eth0` confirm peer-to-peer connectivity plus management reachability.【F:spytest/tests/system/test_lldp.py†L1-L106】【F:spytest/tests/system/test_lldp.py†L184-L283】

## 2. Overall Test Case Purpose
- **Goal:** Validate LLDP functionality and SNMP MIB exposure on SONiC devices, including data-plane neighbor discovery, SNMP accessibility to LLDP MIB objects, configuration persistence, and service resilience.
- **Context:** Within the SpyTest framework, the tests coordinate LLDP CLI, SNMP operations, and platform services to ensure LLDP information is advertised, retrievable, and consistent after configuration changes or service restarts.【F:spytest/tests/system/test_lldp.py†L1-L395】

## 3. Detailed Breakdown of Sub-Testcases
- **Common Setup:**
  - `lldp_snmp_module_hooks` initializes topology, gathers management IPs, verifies interface and neighbor readiness, configures SNMP credentials, and ensures LLDP neighbor data is cached for subsequent tests (`lldp_value`, `lldp_value_remote`, etc.). `lldp_snmp_func_hooks` refreshes globals for each test.【F:spytest/tests/system/test_lldp.py†L8-L116】

### `test_ft_lldp_LocManAddrOID`
- Performs SNMP walk on the LocManAddr OID to verify data availability (pending full validation due to SONIC-5258). Ensures LLDP MIB response is reachable under test conditions.【F:spytest/tests/system/test_lldp.py†L118-L143】

### `test_ft_lldp_LocManAddrLen`
- Walks the LocManAddrLen OID, confirming LLDP management address length data can be retrieved via SNMP despite known defect. Maintains coverage of MIB exposure.【F:spytest/tests/system/test_lldp.py†L145-L168】

### `test_ft_lldp_LocManAddrlfld`
- Similar SNMP walk focusing on LocManAddrlfld OID, validating retrieval of management address logical field entries.【F:spytest/tests/system/test_lldp.py†L170-L193】

### `test_ft_lldp_LocManAddrEntry`
- Retrieves LocManAddrEntry table through SNMP to ensure LLDP local management address entries are exposed.【F:spytest/tests/system/test_lldp.py†L195-L218】

### `test_ft_lldp_ConfigManAddrEntry`
- Confirms ConfigManAddrEntry table availability via SNMP walk, covering configurable management address entries.【F:spytest/tests/system/test_lldp.py†L220-L240】

### `test_ft_lldp_lldplocportid`
- Compares SNMP-exported local port ID values against LLDP CLI neighbor data to guarantee alignment between SNMP MIB and LLDP operational state.【F:spytest/tests/system/test_lldp.py†L242-L282】

### `test_ft_lldp_lldplocsysname`
- Verifies SNMP-exposed local system name matches LLDP neighbor system name derived from CLI, ensuring consistent identity information.【F:spytest/tests/system/test_lldp.py†L284-L310】

### `test_ft_lldp_lldplocsysdesc`
- Cross-checks SNMP system description with LLDP neighbor CLI description for accuracy of advertised platform details.【F:spytest/tests/system/test_lldp.py†L312-L336】

### `test_ft_lldp_lldplocportdesc`
- Validates LLDP port description alignment between SNMP and CLI using the cached local neighbor data.【F:spytest/tests/system/test_lldp.py†L338-L360】

### `test_ft_lldp_rem_man_addr_table`
- Ensures remote management address table entries are accessible via SNMP, confirming remote LLDP data propagation.【F:spytest/tests/system/test_lldp.py†L362-L381】

### `test_ft_lldp_non_default_config`
- Applies non-default LLDP configurations (timers, capabilities, hostname, interface disable) on D2, waits for propagation, and verifies D1 reflects changes; then restores defaults. Validates configurability and propagation of LLDP settings.【F:spytest/tests/system/test_lldp.py†L383-L435】

### `test_ft_lldp_docker_restart`
- Restarts the LLDP service container on D1 and checks neighbor data/hostname consistency to ensure LLDP resilience after service restarts.【F:spytest/tests/system/test_lldp.py†L437-L466】

## 4. Dependencies and Prerequisites
- **Fixtures:** `lldp_snmp_module_hooks`, `lldp_snmp_func_hooks` provide topology setup, SNMP config, and cleanup.【F:spytest/tests/system/test_lldp.py†L8-L116】
- **Topology Variables:** `vars.D1`, `vars.D2`, `vars.D1D2P1`, `vars.D1D2P2` supplied by SpyTest topology manager; management interface `eth0` assumed configured.【F:spytest/tests/system/test_lldp.py†L12-L116】【F:spytest/tests/system/test_lldp.py†L383-L435】
- **Service Availability:** LLDP daemon and SNMP agent must be running; tests depend on LLDP neighbors forming and SNMP reachable.【F:spytest/tests/system/test_lldp.py†L40-L116】【F:spytest/tests/system/test_lldp.py†L437-L466】

## 5. Key Inputs and Parameters
- **SNMP Credentials:** `data.ro_community`, `data.location` configured for SNMP operations; influence SNMP accessibility.【F:spytest/tests/system/test_lldp.py†L22-L116】
- **MIB OIDs:** Multiple LLDP-related OIDs stored in `data` used to query specific SNMP tables/objects.【F:spytest/tests/system/test_lldp.py†L27-L37】
- **Timing Parameters:** `data.wait_time`, LLDP timer adjustments (txinterval, txhold), polling counts ensuring convergence and TTL expiration.【F:spytest/tests/system/test_lldp.py†L22-L116】【F:spytest/tests/system/test_lldp.py†L383-L435】
- **Interfaces:** Management interface `eth0`, data-plane ports `vars.D1D2P1/P2` selected for LLDP neighbor verification.【F:spytest/tests/system/test_lldp.py†L22-L116】【F:spytest/tests/system/test_lldp.py†L383-L435】

## 6. External Libraries and Modules
- **`pytest`** for test definitions and fixtures.【F:spytest/tests/system/test_lldp.py†L1-L6】
- **`spytest.st`** for logging, reporting, waits, and topology utilities.【F:spytest/tests/system/test_lldp.py†L1-L116】
- **`apis.system.lldp` (`lldp_obj`)** providing LLDP configuration and neighbor query helpers.【F:spytest/tests/system/test_lldp.py†L1-L466】
- **`apis.system.snmp` (`snmp_obj`)** handling SNMP config and query operations.【F:spytest/tests/system/test_lldp.py†L1-L466】
- **`apis.system.basic` (`basic_obj`)** for basic platform interactions (service control, hostname, interface info).【F:spytest/tests/system/test_lldp.py†L1-L466】
- **`apis.system.interface` (`intf_obj`)** to poll interface status ensuring links are up.【F:spytest/tests/system/test_lldp.py†L1-L116】
- **`spytest.dicts.SpyTestDict`** to maintain structured global data.【F:spytest/tests/system/test_lldp.py†L1-L37】
- **`apis.routing.ip` (`ip`)** for reachability checks like ping polling.【F:spytest/tests/system/test_lldp.py†L1-L116】

## 7. Unspecified Items
- Additional environmental requirements beyond the two-DUT topology (e.g., specific hardware models, firmware versions) – **Not specified**.
- Expected SNMP data content for currently skipped validation steps (blocked by SONIC-5258) – **Not specified**.
