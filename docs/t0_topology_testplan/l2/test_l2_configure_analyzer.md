# L2 Configuration Test Analyzer

## 1. Topology Type
- **Topology:** `t0`
- **Inference:** The module-level `pytestmark` applies `pytest.mark.topology("t0")`, indicating the test is intended for the T0 topology. No other topology markers are present, and fixtures such as `tbinfo` are used to adjust behavior only when the topology name contains `dualtor`, confirming the base expectation is a single ToR T0 setup.

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate that transitioning a SONiC device into Layer 2 (L2) mode via preset configuration does not reintroduce hardcoded telemetry-related tables into `CONFIG_DB`.
- **Context in SONiC/SpyTest:** Ensures that the L2 configuration workflow maintains a minimal configuration footprint, avoiding legacy RESTAPI or TELEMETRY entries that could affect management services during L2 deployments.

## 3. Detailed Breakdown of Sub-Testcases
### `test_no_hardcoded_tables`
- **Intent & Logic:**
  - Verifies that the `TELEMETRY` and `RESTAPI` tables remain empty after applying an L2 preset configuration.
  - Backs up `CONFIG_DB` and `minigraph.xml`, generates preset L2 configuration files (`init_l2_cfg.json`, management interface overlay, and final `l2_cfg.json`), loads the merged configuration into `CONFIG_DB`, removes the minigraph, and runs `config_reload` to switch the DUT into L2 mode.
  - Retrieves the database version before and after reload for logging visibility and validates that the target tables are empty post-reload using `sonic-db-cli` queries.
- **Relevance:** Ensures L2 conversion keeps the configuration clean from hardcoded telemetry services, supporting reliable minimal L2 deployments.

## 4. Dependencies and Prerequisites
- **Fixtures:**
  - `duthosts`, `rand_one_dut_hostname` – provide access to the selected DUT.
  - `tbinfo` – supplies topology metadata and management interface details.
  - Autouse fixture `setup_env` – handles backing up/restoring `CONFIG_DB` and `minigraph`, adjusts critical services (e.g., removes `mux` on dual ToR) to allow the test to run safely.
- **Utilities:**
  - `config_reload` and `wait_critical_processes` from `tests.common` ensure the DUT reloads configuration and stabilizes critical services.
- **Topology Constraints:** Requires a T0 topology; includes special handling if the testbed name indicates dual ToR to prevent mux container issues.

## 5. Key Inputs and Parameters
- `CONFIG_DB` (`/etc/sonic/config_db.json`) and `MINIGRAPH` (`/etc/sonic/minigraph.xml`) – primary configuration artifacts being backed up and restored.
- `hwsku` – retrieved from DUT facts to generate the L2 preset via `sonic-cfggen`.
- Management interface parameters (`addr`, `prefixlen`, `gwaddr`) from `minigraph_mgmt_interface` – used to craft management configuration overlay.
- Temporary file paths (`/tmp/init_l2_cfg.json`, `/tmp/mgmt_cfg.json`, `/tmp/l2_cfg.json`) – store generated configuration fragments prior to loading.
- `tbinfo["topo"]["name"]` – determines if dual ToR adjustments are needed in the fixture.

## 6. External Libraries and Modules
- **`logging`** – provides module-level logging for debug statements (e.g., database version info).
- **`pytest`** – supplies test and fixture framework, including markers and fixture scoping.
- **`tempfile`** – generates backup file paths for configuration files.
- **`pytest_ansible.errors.AnsibleConnectionFailure`** – handles potential connection drops during `config_reload`.
- **`tests.common.config_reload`** – reloads the SONiC configuration.
- **`tests.common.platform.processes_utils.wait_critical_processes`** – ensures critical SONiC services are running post-reload.
- **`tests.common.helpers.assertions.pytest_assert`** – provides assertion helper for consistent failure messaging.

## 7. Unspecified Items
- Additional topology variations, CLI parameters, or external configuration sources beyond those described above: **Not specified**.
