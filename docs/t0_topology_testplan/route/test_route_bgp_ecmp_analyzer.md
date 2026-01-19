# Test Case Analyzer: `tests/route/test_route_bgp_ecmp.py`

## 1. Topology Type
* **Topology**: `t0`.
* **Inference**: The module-level `pytestmark` applies `pytest.mark.topology("t0")`, explicitly declaring that the test must run on a T0 topology. This marker is the canonical mechanism in SONiC pytest to bind a test module to a topology fixture.

## 2. Overall Test Case Purpose
* **High-Level Goal**: Validate BGP Equal-Cost Multi-Path (ECMP) route programming on a T0 device under test (DUT).
* **Context**: The test exercises interaction between the DUT and the PTF-hosted ExaBGP servers to ensure that multiple eBGP next hops for the same prefix are programmed correctly (announced) and withdrawn cleanly. It focuses on verifying that the DUT installs at least two active next hops (ECMP paths) for an advertised route and removes the route when both peers withdraw it.

## 3. Detailed Breakdown of Sub-Testcases
### `test_route_bgp_ecmp`
* **Intent & Logic**:
  - Retrieves the PTF IP and common topology configuration (including the IPv4 next-hop value) from the `tbinfo` fixture.
  - Optionally adjusts the loganalyzer ignore list to suppress known FRR route-miss errors.
  - Announces the same IPv4 route (`20.0.0.1/32`) twice to the DUT via two ExaBGP instances listening on consecutive TCP ports (5000 and 5001) to emulate multiple eBGP neighbors.
  - Waits for control-plane convergence and then queries FRR on the DUT (`vtysh -c "show ip route ... json"`) to confirm that the route is installed with at least two active internal next hops, indicating ECMP.
  - In the `finally` block, withdraws the route from both ExaBGP instances, waits again, and verifies the route is fully removed from the DUT's routing table.
* **Contribution to Overall Goal**: Directly verifies that BGP ECMP routes are correctly handled across both announcement and withdrawal phases, ensuring SONiC's route programming and cleanup behave as expected.

## Helper Functions and Fixtures
* **`setup_and_teardown` fixture**: Provides logging hooks around the test execution; serves as a module-scoped fixture for setup/teardown structure even though it currently performs logging only.
* **`announce_route`, `withdraw_route`, `change_route`**: Utilities that issue HTTP POST requests to the ExaBGP REST API hosted on the PTF to add or remove routes.
* **`check_route`**: Helper that inspects FRR routing output on the DUT to assert the presence or absence of the tested prefix and the ECMP next-hop count.

## 4. Dependencies and Prerequisites
* **Fixtures**:
  - `duthosts`: Provides access to DUT hosts in the testbed.
  - `tbinfo`: Supplies topology metadata, including PTF IP and configuration properties.
  - `enum_rand_one_per_hwsku_frontend_hostname`: Selects a representative front-end DUT hostname per hardware SKU.
  - `loganalyzer`: Optional fixture that manages log analysis and suppression.
  - `setup_and_teardown`: Module-scoped logging wrapper defined in this file.
* **Topology Constraints**: Requires a T0 topology with a PTF capable of running ExaBGP on ports 5000/5001.
* **External Services**: Expects ExaBGP HTTP servers running on the PTF to accept route change commands.

## 5. Key Inputs and Parameters
* **`tbinfo['ptf_ip']`**: Identifies the PTF host to which route announcements are sent.
* **`tbinfo['topo']['properties']['configuration_properties']['common']['nhipv4']`**: Overrides the default next-hop IP (`NHIPV4`) if provided; controls the IP used in route announcements.
* **Constants**: `EXABGP_BASE_PORT`, `TEST_ROUTE`, `TEST_AS_PATH`, `NHIPV4`, `ANNOUNCE`, `WITHDRAW` define the advertised prefix, AS path, HTTP ports, and command types.

## 6. External Libraries and Modules
* **`requests`**: Sends HTTP POST requests to the ExaBGP REST interface for route manipulation.
* **`json`**: Parses JSON output from the DUT's FRR CLI.
* **`logging`**: Provides logging throughout the test.
* **`time`**: Implements delays to allow routing convergence after announcements/withdrawals.
* **`pytest`**: Supplies the testing framework, fixtures, and markers.

## 7. Unspecified Items
* Any additional configuration sourced from inventory files (`testbed.yaml`, group variables, etc.) beyond the referenced `tbinfo` keys is **Not specified** in this test file.
