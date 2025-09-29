# Test Plan Analysis: `tests/bgp/test_bgp_slb.py`

## 1. Topology Type
- **Declared Topology:** `t0` via `pytestmark = [pytest.mark.topology("t0"), ...]`.
- **Inference Rationale:**
  - The `pytestmark` list explicitly marks the file for `t0` topologies, indicating a single ToR-facing PTF environment typical for basic SONiC regression. The test leverages `enum_rand_one_per_hwsku_frontend_hostname` and other frontend-related fixtures that are standard for T0 front-panel devices.

## 2. Overall Test Case Purpose
- **High-Level Goal:** Validate that a dynamic SLB (Server Load Balancer) BGP neighbor remains established across advanced reboot procedures (warm and fast reboots).
- **SONiC Context:** Ensures resilience of dynamically configured BGP neighbors created through SLB integrations, especially when SONiC performs non-cold reboots. The test leverages common SONiC pytest infrastructure (`tests.common.*`) to start an ExaBGP session, reboot the DUT, and confirm protocol stability.

## 3. Detailed Breakdown of Sub-Testcases
### `test_bgp_slb_neighbor_persistence_across_advanced_reboot`
- **Intent & Flow:**
  1. Use the `bgp_slb_neighbor` fixture to instantiate a `BGPNeighbor` ExaBGP session toward the DUT with passive dynamic configuration.
  2. Start the neighbor session and wait (retry loop with `wait_until`) until the session enters the `established` state according to `duthost.bgp_facts()`.
  3. Trigger an advanced reboot (`warm` or `fast` depending on the parametrized `reboot_type` fixture) via `tests.common.reboot.reboot` with the warm boot finalizer enabled.
  4. After reboot, again verify that the dynamic BGP session re-establishes within the wait window.
  5. Finally, stop the ExaBGP session and clean any SLB-related running config snippets.
- **Importance:** Confirms that SLB-introduced dynamic neighbors are persistent and recover automatically after non-cold reboots, ensuring service continuity in production scenarios.

### Helper Fixtures & Utilities
- **`reboot_type` fixture:** Parameterizes the test over `"warm"` and `"fast"` reboot modes, while guarding against unsupported `fast` reboots on DualToR setups using `pytest_require`.
- **`slb_neighbor_asn` fixture:** Retrieves the external ASN for SLB dynamic neighbors from `/etc/sonic/constants.yml` or `/etc/sonic/deployment_id_asn_map.yml`, failing the test if not configured.
- **`bgp_slb_neighbor` fixture:** Builds a `BGPNeighbor` object based on DUT minigraph facts and interface setup data, configuring ExaBGP to act as a passive dynamic neighbor on port `11000` with the retrieved SLB ASN.
- **`toggle_all_simulator_ports_to_enum_rand_one_per_hwsku_frontend_host_m` fixture:** Imported to ensure mux simulator ports are toggled appropriately for DualToR environments, guaranteeing correct traffic flow during the test.
- **Utility Functions:** `wait_until`, `delete_running_config`, and `pytest_require` provide retry logic, configuration cleanup, and runtime skipping respectively.

## 4. Dependencies and Prerequisites
- **Fixtures:** `duthosts`, `enum_rand_one_per_hwsku_frontend_hostname`, `setup_interfaces`, `ptfhost`, `tbinfo`, `localhost`, and the fixtures listed above must be available from the SONiC pytest framework.
- **Topology Constraints:** Requires a T0 testbed with accessible minigraph data and, when applicable, mux simulator control for DualToR frontends.
- **External Services:** ExaBGP on the PTF host must be available to emulate the dynamic SLB neighbor.

## 5. Key Inputs and Parameters
- **`reboot_type`:** Determines whether a warm or fast reboot is executed.
- **`slb_neighbor_asn`:** ASN value mapped from deployment ID for the SLB neighbor; controls BGP session parameters.
- **`NEIGHBOR_EXABGP_PORT` (11000):** TCP port used by ExaBGP to establish the neighbor session.
- **Interface Details (`setup_interfaces`):** Supplies local and neighbor IPs to configure the BGP neighbor.
- **Minigraph ASN (`minigraph_bgp_asn`):** DUT ASN extracted from minigraph facts for session configuration.

## 6. External Libraries and Modules
- **`pytest`:** Test framework used for fixtures, parametrization, and assertions.
- **`tests.common.reboot`:** Provides `reboot` helper to trigger advanced reboots with consistent options.
- **`tests.common.helpers.bgp.BGPNeighbor`:** Utility class to manage ExaBGP sessions against the DUT.
- **`tests.common.dualtor.mux_simulator_control`:** Supplies fixtures to control DualToR mux simulator behavior.
- **`tests.common.utilities`:** Offers `wait_until` retry helper and `delete_running_config` for config cleanup.
- **`tests.common.helpers.assertions`:** Delivers `pytest_require` for conditional skipping.

## 7. Unspecified Items
- Additional inventory variables or external configuration files beyond those referenced above: **Not specified**.
