# `test_arp.py` QA Overview

## 1. Topology type and inference
- The test enforces a minimum topology of `D1T1:2`, meaning one DUT (D1) connected to a single traffic generator (T1) with two links/ports. This is derived from the module fixture that calls `st.ensure_min_topology("D1T1:2")`.【F:spytest/tests/routing/test_arp.py†L34-L56】
- Traffic generator handles `T1D1P1` and `T1D1P2` are requested immediately afterward, reinforcing that the setup expects two TG ports attached to the DUT.【F:spytest/tests/routing/test_arp.py†L37-L68】

## 2. Overall test case purpose
- Validate that dynamic ARP entries form successfully and that data traffic continues without loss during ARP refresh/age-out conditions. This objective is explicitly documented in the test body comments and exercised by generating traffic before and after the ARP aging period.【F:spytest/tests/routing/test_arp.py†L98-L162】

## 3. Subtestcases and their contributions
- **Module fixture `arp_module_hooks`**: Performs DUT and traffic-generator setup—verifies topology, configures DUT interfaces and VLAN membership, and brings up TG interfaces. This preparation ensures the environment is ready for ARP learning and traffic validation, directly supporting the dynamic ARP test scenario.【F:spytest/tests/routing/test_arp.py†L34-L74】
- **Function fixture `arp_func_hooks`**: Placeholder autouse fixture for per-test hooks. Although it currently contains no actions, it provides a consistent pattern for inserting per-test setup/teardown logic if needed, maintaining framework expectations.【F:spytest/tests/routing/test_arp.py†L77-L82】
- **Fixture `fixture_ft_arp_dynamic_renew_traffic_test`**: Ensures the ARP age-out timer is restored to 60 seconds after the test, preventing side effects on subsequent tests and maintaining consistent device state.【F:spytest/tests/routing/test_arp.py†L84-L88】
- **Test `test_ft_arp_dynamic_renew_traffic_test`**:
  - Sets the DUT ARP age-out to 75 seconds to control the refresh window under test.【F:spytest/tests/routing/test_arp.py†L104-L107】
  - Sends pings from both TG ports to their respective DUT gateways, forcing dynamic ARP entry creation and validating reachability from both sides.【F:spytest/tests/routing/test_arp.py†L108-L121】
  - Clears TG statistics and creates a continuous VLAN-tagged IPv4 traffic stream, then runs it while waiting beyond the ARP age-out to observe renewal behavior.【F:spytest/tests/routing/test_arp.py†L123-L138】
  - Stops traffic, allows additional settling time, and validates transmit/receive counters to confirm no packet loss during the ARP refresh cycle before reporting test status.【F:spytest/tests/routing/test_arp.py†L140-L162】

## 4. Dependencies and prerequisites
- Requires pytest with SpyTest fixtures, including module-level autouse configuration and traffic-generator integration.【F:spytest/tests/routing/test_arp.py†L30-L74】
- Depends on SpyTest infrastructure functions (`st.ensure_min_topology`, `tgapi.get_handles_byname`, etc.) and assumes the testbed defines TG port aliases `T1D1P1`/`T1D1P2` corresponding to the enforced D1T1:2 topology.【F:spytest/tests/routing/test_arp.py†L34-L68】
- Necessitates device support for VLAN creation and interface IP configuration as executed during setup.【F:spytest/tests/routing/test_arp.py†L48-L53】

## 5. Key inputs and their sources
- Test parameter defaults (IP addresses, MAC addresses, VLAN ID, mask, queue mapping, ARP timers) are hard-coded in the `data` dictionary at the top of the file, making the scenario self-contained.【F:spytest/tests/routing/test_arp.py†L11-L27】
- Topology-dependent variables such as `vars.D1T1P1`, `vars.D1T1P2`, and traffic generator port handles come from SpyTest topology discovery (`st.ensure_min_topology`) and the testbed definitions resolved through `tgapi.get_handles_byname`.【F:spytest/tests/routing/test_arp.py†L34-L68】
- DUT selection leverages `st.get_dut_names()`, relying on the testbed inventory to provide the available device list.【F:spytest/tests/routing/test_arp.py†L41-L43】

## 6. External libraries and their roles
- `apis.routing.arp`: Provides functions to manipulate ARP settings, such as setting the age-out timer used in setup and teardown.【F:spytest/tests/routing/test_arp.py†L5-L7】【F:spytest/tests/routing/test_arp.py†L84-L107】
- `apis.routing.ip`: Configures IP addresses on DUT interfaces during setup to establish routing endpoints.【F:spytest/tests/routing/test_arp.py†L6-L53】
- `apis.system.interface`: Handles interface counters and diagnostics, ensuring counters are cleared before traffic runs and aiding failure troubleshooting.【F:spytest/tests/routing/test_arp.py†L7-L8】【F:spytest/tests/routing/test_arp.py†L132-L158】
- `apis.switching.vlan`: Manages VLAN creation and membership needed for the tagged traffic path.【F:spytest/tests/routing/test_arp.py†L8-L53】
- `apis.switching.mac`: Retrieves the DUT interface MAC address required for traffic generation.【F:spytest/tests/routing/test_arp.py†L9-L47】
- `spytest.tgapi`: Supplies traffic generator control primitives for ping verification, stream configuration, and traffic validation throughout the test.【F:spytest/tests/routing/test_arp.py†L3-L156】
