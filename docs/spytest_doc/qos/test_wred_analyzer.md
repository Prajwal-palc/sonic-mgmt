# Test Analyzer: `spytest/tests/qos/test_wred.py`

## 1. Topology type
- The module-level autouse fixture enforces the `"D1T1:3"` topology, which corresponds to a single DUT (D1) connected to a traffic generator (T1) with three test ports; the traffic generator handles `T1D1P1`, `T1D1P2`, and `T1D1P3` confirm three links are consumed.【F:spytest/tests/qos/test_wred.py†L29-L75】
- The fixture also programs a shared traffic generator object (`data.tg`) for all streams, implying a single TGen chassis that fans out to three DUT front-panel interfaces under test.【F:spytest/tests/qos/test_wred.py†L38-L75】

## 2. Overall test case purpose
- The file validates weighted random early detection (WRED) behavior on SONiC by provisioning QoS profiles/maps, driving DSCP-tagged flows, and asserting that WRED green drop counters increment when traffic exceeds thresholds.【F:spytest/tests/qos/test_wred.py†L128-L179】
- In the SpyTest framework, it verifies that WRED configuration persists in the running configuration, integrates correctly with DSCP-to-TC and TC-to-queue mappings, and triggers hardware counter updates under load, providing confidence in SONiC’s QoS pipeline.【F:spytest/tests/qos/test_wred.py†L87-L179】

## 3. Detailed breakdown of sub-testcases
### `test_ft_wred_functionality`
- **Intent & setup:** Uses helper routines to set MAC aging, create a tagged VLAN for all three generator-facing ports, and ensure the WRED profile is resident in the running configuration before traffic is sent.【F:spytest/tests/qos/test_wred.py†L87-L169】
- **Traffic execution:** Learns the destination MAC by running a VLAN-tagged stream from port 3, then transmits two continuous DSCP-tagged flows intended for distinct queues to exercise WRED behavior and gathers interface statistics.【F:spytest/tests/qos/test_wred.py†L153-L177】
- **Assertions:** Polls the MAC table for learning success, binds DSCP/TC/queue maps to every port, and finally checks ASIC counters to ensure `WRED_PKT_GRE.` increased, failing otherwise.【F:spytest/tests/qos/test_wred.py†L161-L179】
- **Relevance:** Demonstrates end-to-end WRED enforcement—successful MAC learning, QoS mapping, and counter validation—covering functional correctness of SONiC’s QoS drop logic under differentiated traffic.【F:spytest/tests/qos/test_wred.py†L128-L179】

#### Supporting helpers
- `wred_running_config()` confirms the WRED profile’s `green_max_threshold` value is present in the running configuration DB before testing proceeds.【F:spytest/tests/qos/test_wred.py†L87-L90】
- `configuring_tc_to_queue_map()` and `configuring_dscp_to_tc_map()` build the QoS lookup tables that steer DSCP 8/24 traffic into traffic classes 3/4 respectively, which then map to queues for WRED enforcement.【F:spytest/tests/qos/test_wred.py†L91-L99】
- `binding_queue_map_to_interfaces()` attaches those maps to all three DUT ports so every ingress interface honors the QoS policies used by the test streams.【F:spytest/tests/qos/test_wred.py†L97-L99】
- `fdb_config()` and `vlan_config()` prepare the switching fabric by tuning MAC aging, creating VLAN 555, and validating membership so learning and forwarding behave predictably.【F:spytest/tests/qos/test_wred.py†L102-L113】
- `cos_counters_checking()` inspects ASIC WRED green packet counters, providing the primary pass/fail signal for the test case.【F:spytest/tests/qos/test_wred.py†L115-L122】

## 4. Dependencies and prerequisites
- Module fixture `wred_module_hooks` is autouse and prepares the DUT/TGen topology, applies the WRED JSON via `apply_wred_ecn_config`, creates traffic streams, and tears down QoS/VLAN state after the module completes.【F:spytest/tests/qos/test_wred.py†L29-L75】
- Function fixture `wred_func_hooks` is autouse but intentionally empty, available for per-test customization if needed.【F:spytest/tests/qos/test_wred.py†L78-L84】
- The test depends on QoS, VLAN, MAC, interface, ASIC counter, and traffic generator APIs supplied by SpyTest’s `apis.*` and `tgapi` libraries to configure DUT state and drive traffic.【F:spytest/tests/qos/test_wred.py†L6-L75】

## 5. Key inputs and parameters
- Global `data` dictionary seeds key parameters such as MAC aging time (600 seconds), VLAN ID 555, DSCP source/destination MACs, QoS profile names, and target queue identifier, steering both configuration and traffic characteristics.【F:spytest/tests/qos/test_wred.py†L17-L27】
- Traffic generator streams use DSCP values 8 and 24 with VLAN tagging, tied back to TC/queue mappings configured earlier to test differentiated treatment.【F:spytest/tests/qos/test_wred.py†L54-L71】
- WRED thresholds are sourced from `wred_config.init_vars`, provisioning a `WRED` profile with explicit min/max thresholds and drop probabilities applied to ports 1–3.【F:spytest/tests/qos/test_wred.py†L33-L36】【F:spytest/tests/qos/wred_ecn_config_json.py†L1-L47】
- The test polls for MAC learning of destination MAC `00:00:00:00:00:03` and relies on VLAN membership for ports `vars.D1T1P1/2/3` to forward traffic correctly.【F:spytest/tests/qos/test_wred.py†L21-L23】【F:spytest/tests/qos/test_wred.py†L107-L165】

## 6. External libraries and modules
- `pytest`: Provides fixture and marker infrastructure for organizing the QoS test module.【F:spytest/tests/qos/test_wred.py†L1-L126】
- `spytest` core (`st`, `tgapi`, `SpyTestDict`): Supplies logging, topology negotiation, and traffic generator abstractions specific to SpyTest.【F:spytest/tests/qos/test_wred.py†L3-L75】
- `spytest.utils.poll_wait`: Offers retry logic for verifying MAC learning before failing the test.【F:spytest/tests/qos/test_wred.py†L4-L165】
- `tests.qos.wred_ecn_config_json`: Delivers canned WRED/ECN profile definitions tailored to this scenario.【F:spytest/tests/qos/test_wred.py†L6-L36】
- `apis.qos.qos`, `apis.qos.cos`, `apis.qos.wred`: Provide QoS configuration primitives, including applying WRED profiles and programming TC/DSCP maps.【F:spytest/tests/qos/test_wred.py†L7-L99】
- `apis.system.switch_configuration`, `apis.system.interface`: Allow verification of running config and manipulation/inspection of interface counters.【F:spytest/tests/qos/test_wred.py†L8-L179】
- `apis.switching.vlan`, `apis.switching.mac`: Handle VLAN creation/membership and MAC table operations required for traffic validation.【F:spytest/tests/qos/test_wred.py†L9-L165】
- `apis.common.asic`: Exposes low-level ASIC counter retrieval used to assert WRED drops.【F:spytest/tests/qos/test_wred.py†L10-L121】
- `utilities.common`: Supplies the `exec_all` helper used to apply configuration in parallel contexts.【F:spytest/tests/qos/test_wred.py†L12-L36】

## 7. Unspecified items
- Details about the physical testbed (platform type, interface speed, ASIC vendor) beyond the single-DUT/three-port topology are not specified in the test file. **Not specified.**
- Any external configuration sources such as `testbed.yaml` or group variables influencing these parameters are not referenced. **Not specified.**
