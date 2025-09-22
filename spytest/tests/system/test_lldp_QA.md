# LLDP System Test Overview

## 1. Topology type used
- The module-level fixture calls `st.ensure_min_topology("D1D2:2")`, which requires a dual-DUT setup (devices D1 and D2) with two interconnect links available for LLDP validation. 【F:spytest/tests/system/test_lldp.py†L10-L91】
- Individual test docstrings reference "D1 --- Mgmt Network" and "D1 <---> D2" layouts, confirming reliance on both the management network and at least one data-plane link between the two devices. 【F:spytest/tests/system/test_lldp.py†L134-L312】

## 2. Overall test case purpose
- The suite validates LLDP functionality and its SNMP exposure by comparing LLDP neighbor data gathered via CLI/API calls with SNMP MIB outputs, exercising default behavior, non-default LLDP configurations, and service resiliency after a docker restart. 【F:spytest/tests/system/test_lldp.py†L49-L400】

## 3. Sub-testcases and their contributions
- `test_ft_lldp_LocManAddrOID`: Walks the `lldpLocManAddrOID` table to confirm SNMP visibility of local management address identifiers, foundational for subsequent SNMP comparisons. 【F:spytest/tests/system/test_lldp.py†L129-L144】
- `test_ft_lldp_LocManAddrLen`: Retrieves the management address length MIB to ensure supporting attributes of the local management address are exposed. 【F:spytest/tests/system/test_lldp.py†L146-L160】
- `test_ft_lldp_LocManAddrlfld`: Verifies the local management address LfId field via SNMP, covering additional metadata required for complete LLDP management address reporting. 【F:spytest/tests/system/test_lldp.py†L163-L177】
- `test_ft_lldp_LocManAddrEntry`: Confirms the composite entry for local management addresses can be walked, ensuring the full table is accessible. 【F:spytest/tests/system/test_lldp.py†L180-L194】
- `test_ft_lldp_ConfigManAddrEntry`: Exercises the configuration management address entry MIB to check LLDP configuration data exposure. 【F:spytest/tests/system/test_lldp.py†L197-L211】
- `test_ft_lldp_lldplocportid`: Compares LLDP CLI neighbor port IDs with SNMP data to validate consistency between operational state and SNMP reporting. 【F:spytest/tests/system/test_lldp.py†L214-L238】
- `test_ft_lldp_lldplocsysname`: Cross-verifies the remote chassis name learned via LLDP against the SNMP `lldpLocSysName` object, ensuring naming alignment. 【F:spytest/tests/system/test_lldp.py†L241-L261】
- `test_ft_lldp_lldplocsysdesc`: Checks that the LLDP chassis description matches between the CLI data and SNMP `lldpLocSysDesc`. 【F:spytest/tests/system/test_lldp.py†L264-L284】
- `test_ft_lldp_lldplocportdesc`: Validates the local port description advertised by LLDP through SNMP, closing the loop on interface metadata synchronization. 【F:spytest/tests/system/test_lldp.py†L286-L303】
- `test_ft_lldp_rem_man_addr_table`: Ensures the remote management address table is populated via SNMP, proving neighbor information is exported. 【F:spytest/tests/system/test_lldp.py†L305-L319】
- `test_ft_lldp_non_default_config`: Applies non-default LLDP settings (interval, hold, advertised capabilities, port disable, hostname) and confirms they take effect, then restores defaults, validating configuration propagation. 【F:spytest/tests/system/test_lldp.py†L322-L370】
- `test_ft_lldp_docker_restart`: Restarts the LLDP docker/service and verifies neighbor data recovers and matches device hostnames, exercising service resiliency. 【F:spytest/tests/system/test_lldp.py†L373-L400】

## 4. Dependencies and prerequisites
- Autouse fixtures establish globals, enforce the required topology, and perform LLDP/SNMP pre- and post-configuration including interface and neighbor polling, so stable connectivity and SNMP access are prerequisites. 【F:spytest/tests/system/test_lldp.py†L10-L127】
- The tests rely on LLDP neighbors being present on interfaces `D1D2P1`/`D2D1P1` (and `D1D2P2` for negative checks) and on the management interface `eth0` having a reachable IP address. 【F:spytest/tests/system/test_lldp.py†L58-L91】【F:spytest/tests/system/test_lldp.py†L331-L358】
- No explicit additional fixtures, inventory files, or topology constraints are defined beyond what `ensure_min_topology` infers; other dependencies are not specified. 【F:spytest/tests/system/test_lldp.py†L10-L17】

## 5. Key inputs and their sources
- `vars` (device handles and link mappings) are populated via `st.ensure_min_topology`, drawing from the active SpyTest testbed definition (e.g., `testbed.yaml`). 【F:spytest/tests/system/test_lldp.py†L10-L17】
- SNMP parameters such as `ro_community`, `location`, and LLDP-related OIDs are initialized in `global_vars()` as hard-coded defaults for the suite. 【F:spytest/tests/system/test_lldp.py†L26-L47】
- Management IPs `data.ipaddress_d1`/`data.ipaddress_d2` and the shared `ipaddress` value are discovered at runtime via `basic_obj.get_ifconfig_inet` on the management interface. 【F:spytest/tests/system/test_lldp.py†L58-L64】
- LLDP neighbor dictionaries (`lldp_value`, `lldp_value_remote`, etc.) are gathered dynamically through `lldp_obj.get_lldp_neighbors` during pre-configuration and test execution. 【F:spytest/tests/system/test_lldp.py†L68-L238】【F:spytest/tests/system/test_lldp.py†L339-L358】【F:spytest/tests/system/test_lldp.py†L390-L399】
- Command-line parameters or additional group variables are not specified. Not specified.

## 6. External libraries and their roles
- `spytest.st`: Provides test utilities (topology enforcement, logging, waiting, reporting). 【F:spytest/tests/system/test_lldp.py†L2-L117】
- `apis.system.lldp`: Supplies LLDP control and query functions used for configuration and neighbor retrieval. 【F:spytest/tests/system/test_lldp.py†L3-L399】
- `apis.system.snmp`: Handles SNMP configuration and polling for the LLDP-related MIBs. 【F:spytest/tests/system/test_lldp.py†L4-L319】
- `apis.system.basic`: Offers system-level helpers for interface status, service control, and hostname retrieval. 【F:spytest/tests/system/test_lldp.py†L5-L398】
- `apis.system.interface`: Provides interface polling utilities to ensure link readiness. 【F:spytest/tests/system/test_lldp.py†L6-L389】
- `spytest.dicts.SpyTestDict`: Used to store shared configuration data within the suite. 【F:spytest/tests/system/test_lldp.py†L7-L47】
- `apis.routing.ip`: Supplies IP reachability checks (e.g., ping polling) during setup. 【F:spytest/tests/system/test_lldp.py†L8-L104】
- Additional third-party libraries beyond these SpyTest APIs are not specified. Not specified.
