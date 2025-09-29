# test_orchagent_standby_tor_downstream.py Analyzer

## 1. Topology Type
- **Topology:** `t0` dual ToR testbed. This is inferred from the module-level `pytestmark` applying `pytest.mark.topology('t0')`, which indicates the testbed flavor expected by the suite.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L26-L36】
- The repeated use of dual ToR fixtures (e.g., `apply_mock_dual_tor_tables`, `apply_standby_state_to_orchagent`) further confirms that the tests assume a mocked dual ToR environment layered on top of the T0 topology.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L27-L36】

## 2. Overall Test Case Purpose
- The test module validates **downstream traffic handling when the Device Under Test (standby ToR) participates in a dual ToR topology**. Specifically, it ensures:
  - Tunnel traffic destined to the active ToR remains balanced across nexthops.
  - Standby ToR does not leak traffic to servers and recovers correctly from uplink/BGP disturbances.
- Within the SONiC dual ToR validation framework, these scenarios confirm **orchagent resilience and CRM behavior** under link/BGP failure and recovery conditions while using mocked infrastructure helpers (mux simulator, tunnel monitors, CRM checks).【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L92-L150】

## 3. Detailed Breakdown of Sub-Testcases

### `test_standby_tor_downstream`
- **Intent:** Calls `check_tunnel_balance` with dual ToR parameters to verify that, during steady state, encapsulated traffic exiting the standby ToR is evenly balanced towards the active peer and no server-bound leakage occurs.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L92-L99】
- **Logic:** Retrieves testbed parameters via `get_testbed_params()` (encapsulating dualtor info and IPv6 flag) and runs the balance checker.
- **Relevance:** Establishes baseline behavior before injecting failures, ensuring subsequent failure scenarios compare against a known-good traffic distribution.

### `test_standby_tor_downstream_t1_link_recovered`
- **Intent:** Validates recovery after randomly shutting down and restoring a T1 uplink. Ensures tunnel balance returns and CRM nexthop counters do not spuriously increase.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L101-L132】
- **Logic:**
  - Picks a random port channel using `shutdown_random_one_t1_link`, sleeps to allow state convergence, then checks tunnel balance.
  - Restores the link, optionally refreshes static routes for mocked dual ToR topologies, and re-verifies balance.
  - The fixture `verify_crm_nexthop_counter_not_increased` (imported via pytestmark) implicitly checks CRM metrics during the test run.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L33-L36】【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L101-L132】
- **Relevance:** Demonstrates robustness to physical link flaps and guards against control-plane misbehavior (route churn causing new nexthops).

### `test_standby_tor_downstream_bgp_recovered`
- **Intent:** Tests the impact of flapping a random IPv4 BGP session on the standby ToR, confirming traffic shifts correctly and balance is restored after recovery without CRM anomalies.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L134-L160】
- **Logic:**
  - Uses `shutdown_random_one_bgp_session` to suspend an established neighbor, waits for stabilization, and validates tunnel balance.
  - Restarts the session via `startup_bgp_session`, waits again, and repeats the balance verification.
- **Relevance:** Ensures routing control-plane disruptions do not compromise downstream traffic steering or allocate extra nexthops.

### Helper Functions and Fixtures
- `ip_version` parameterizes tests across IPv4 and IPv6 flows, with `setup_testbed_ipv6` enabling additional ARP responder behavior when needed.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L38-L58】
- `get_testbed_params` wraps `dualtor_info` to deliver consistent parameter dictionaries (including active/standby ToR addresses, PTF ports, IPv6 flag) to tests.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L64-L77】
- Uplink/BGP helper utilities (`shutdown_random_one_t1_link`, `no_shutdown_t1_link`, `shutdown_random_one_bgp_session`, `startup_bgp_session`) encapsulate the fault injection and recovery sequences reused across tests.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L79-L118】

## 4. Dependencies and Prerequisites
- **PyTest fixtures:** Module-level fixtures apply mocked dual ToR tables, kernel configs, standby state, GARP/ICMP responders, and IPv6 ARP responder when required, ensuring the DUT operates like a standby ToR within the mock environment.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L27-L36】
- **Per-test fixtures:**
  - `rand_selected_dut`, `rand_unselected_dut`, `ptfhost`, `tbinfo`—supplied by the SONiC test infrastructure—provide access to DUT handles, PTF host, and topology metadata used by helper functions.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L64-L77】【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L92-L160】
  - `verify_crm_nexthop_counter_not_increased` monitors CRM counters during recovery tests (fixture defined elsewhere but applied via `pytest.mark.usefixtures`).【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L33-L36】
- **Topology constraints:** Requires dual ToR-capable T0 topology with mux simulator and controllable T1/BGP interfaces; tests assume ability to toggle mux state and manipulate BGP sessions.

## 5. Key Inputs and Parameters
- `dualtor_info` output provides addresses, tunnel endpoints, and port mappings consumed by `check_tunnel_balance` and route management helpers.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L64-L77】【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L101-L150】
- `params["check_ipv6"]` toggles IPv6 validation path when `ip_version` fixture selects IPv6 traffic.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L69-L77】
- `PAUSE_TIME = 30` ensures sufficient convergence time after link or BGP state changes.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L107-L108】【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L140-L141】
- `tbinfo['topo']['name']` determines when to refresh static routes manually (mocked dual ToR scenarios).【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L123-L129】
- Random selection utilities (`random.choice`) introduce variability in the T1 link or BGP neighbor chosen for failure injection.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L79-L118】

## 6. External Libraries and Modules
- **`pytest`** – core testing framework used for fixtures, marks, and assertions.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L1-L160】
- **`testutils` from PTF** – available for packet-level verifications (imported but not directly used in this file, supporting potential expansions).【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L8-L9】
- **`tests.common.dualtor.*` helpers** – provide dual ToR mocks, mux controls, tunnel checks, traffic monitors, CRM utilities, and failure management crucial for simulating standby/active behavior.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L10-L25】
- **`tests.common.fixtures.ptfhost_utils`** – deliver services on the PTF host (MAC change, GARP, ICMP responder, ARP responder, ptftests copy) necessary for traffic handling in the mocked environment.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L17-L24】【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L33-L36】
- **Standard libraries (`random`, `time`, `logging`, `ipaddress`, `contextlib`)** – support randomness, timing delays, logging, IP version filtering, and context management for helper logic.【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L2-L7】【F:tests/dualtor/test_orchagent_standby_tor_downstream.py†L79-L118】

## 7. Unspecified Items
- Detailed definitions of shared fixtures (`rand_selected_dut`, `verify_crm_nexthop_counter_not_increased`, etc.) and exact CRM thresholds are not specified within this file. Therefore, their behavior is inferred but not explicitly documented here. **Not specified.**
- Testbed inventory specifics (e.g., server count, interface mapping) are provided externally via `tbinfo` and the testbed YAML; the file does not enumerate them. **Not specified.**
