# ARP Stress Test Analyzer

## 1. Topology Type
- **Topology:** `t0` leaf-spine topology.
- **Inference:** The module-level `pytestmark` explicitly marks `pytest.mark.topology('t0')`, indicating that the testbed must provide a T0-style fabric with one DUT facing multiple ToRs/leaves and fanout neighbors.【F:tests/arp/test_stress_arp.py†L23-L26】

## 2. Overall Test Case Purpose
- This test module validates the DUT's ability to handle large-scale ARP and IPv6 neighbor discovery activity while maintaining CRM (Critical Resource Monitoring) resource availability and correct forwarding database (FDB) behavior.
- It stresses both IPv4 GARP learning and IPv6 ND handling, including behavior under incomplete neighbor conditions and conntrack tuning. The goal is to ensure SONiC can scale neighbor tables, prevent table overflows, and manage conntrack resources without leaving stale state.
- Within the SONiC pytest infrastructure, these scenarios validate resilience and scale characteristics for L2/L3 neighbor handling on T0 platforms, ensuring interoperability with PTF-host-driven packet injection.

## 3. Detailed Breakdown of Sub-Testcases
### `test_ipv4_arp`
- **Intent:** Flood the DUT with gratuitous ARP announcements from the PTF to verify that IPv4 neighbors and corresponding FDB entries scale up to the available CRM capacity without overshoot or failure.【F:tests/arp/test_stress_arp.py†L66-L138】
- **Logic:**
  - Determines the normalized completeness level (default `debug`) to map to loop iterations via `LOOP_TIMES_LEVEL_MAP` for repeated stress cycles.【F:tests/arp/test_stress_arp.py†L28-L36】【F:tests/arp/test_stress_arp.py†L88-L104】
  - Queries CRM counters for `ipv4_neighbor`, `fdb_entry`, and on Cisco platforms `ipv4_nexthop` to cap the number of injected ARP entries.【F:tests/arp/test_stress_arp.py†L101-L113】
  - Requires the `garp_enabled` fixture to confirm the DUT is configured to accept gratuitous ARP updates.【F:tests/arp/test_stress_arp.py†L114-L116】
  - Generates a contiguous pool of IPv4 hosts from `172.16.0.0/16` using `genrate_ipv4_ip`, then repeatedly calls `add_arp` to send crafted GARP packets through the specified PTF interface.【F:tests/arp/test_stress_arp.py†L54-L79】【F:tests/arp/test_stress_arp.py†L116-L126】
  - After each burst, waits for the FDB dynamic MAC count to converge within tolerance and finally clears ARP/FDB state via helper utilities in a `finally` block.【F:tests/arp/test_stress_arp.py†L126-L138】
- **Contribution:** Ensures IPv4 neighbor scaling is robust, CRM thresholds are respected, and dynamic MAC learning behaves correctly under stress.

### `test_ipv6_nd`
- **Intent:** Stress IPv6 neighbor discovery by generating neighbor solicitation packets and verifying the DUT learns neighbors without exceeding resource availability.【F:tests/arp/test_stress_arp.py†L160-L214】
- **Logic:**
  - Validates that proxy ARP is enabled and an IPv6 VLAN address exists via fixtures before sending traffic.【F:tests/arp/test_stress_arp.py†L161-L169】
  - Maps completeness level to loop iterations similar to the IPv4 case.【F:tests/arp/test_stress_arp.py†L170-L173】
  - Calculates the allowable neighbor count based on CRM metrics (`ipv6_neighbor`, `fdb_entry`, and `ipv6_nexthop` for Cisco ASICs).【F:tests/arp/test_stress_arp.py†L173-L189】
  - Uses helper `add_nd`, which repeatedly crafts IPv6 NS packets via `ipv6_packets_for_test`, to seed the DUT with neighbor entries from randomized MAC/IP pairs derived from `ARP_SRC_MAC`.【F:tests/arp/test_stress_arp.py†L139-L158】【F:tests/arp/test_stress_arp.py†L189-L204】
  - Verifies the FDB count matches expectations and clears state between loops.【F:tests/arp/test_stress_arp.py†L193-L214】
- **Contribution:** Confirms IPv6 neighbor learning scale and resource accounting, complementing the IPv4 ARP stress coverage.

### `test_ipv6_nd_incomplete`
- **Intent:** Evaluate conntrack and neighbor table behavior when large numbers of IPv6 echo requests target non-existent neighbors, leaving entries in `INCOMPLETE` state, while ensuring conntrack resources remain under control.【F:tests/arp/test_stress_arp.py†L216-L288】
- **Logic:**
  - Confirms proxy ARP and IPv6 VLAN address availability before proceeding.【F:tests/arp/test_stress_arp.py†L218-L225】
  - Bounds the number of incomplete neighbors based on CRM availability and a constant `TEST_INCOMPLETE_NEIGHBOR_CNT`.【F:tests/arp/test_stress_arp.py†L226-L231】
  - Reads conntrack system parameters (`nf_conntrack_max`, `nf_conntrack_count`, `nf_conntrack_icmpv6_timeout`) to set baselines and temporarily reduces timeout to a controlled value.【F:tests/arp/test_stress_arp.py†L231-L247】
  - Flushes existing ARP/conntrack state, sends numerous ICMPv6 echo requests with randomized sources via `send_ipv6_echo_request`, and ensures conntrack count growth stays below the targeted threshold while the dying list remains empty.【F:tests/arp/test_stress_arp.py†L247-L271】【F:tests/arp/test_stress_arp.py†L204-L215】
  - Logs the number of neighbors in `INCOMPLETE` state and restores original conntrack timeout plus clears state in a `finally` block.【F:tests/arp/test_stress_arp.py†L271-L288】
- **Contribution:** Validates system resilience to incomplete neighbor scenarios and verifies conntrack tuning, preventing control-plane overload under stress.

### Helper Components
- **`arp_cache_fdb_cleanup` fixture:** Automatically clears ARP cache and FDB before and after each test, shielding tests from residual state and ensuring deterministic behavior even on failure.【F:tests/arp/test_stress_arp.py†L38-L52】
- **Utility functions (`add_arp`, `genrate_ipv4_ip`, `generate_global_addr`, `ipv6_packets_for_test`, `add_nd`, `send_ipv6_echo_request`):** Provide reusable packet generation and traffic injection logic for the tests, encapsulating details around MAC/IP synthesis and packet crafting.【F:tests/arp/test_stress_arp.py†L54-L158】【F:tests/arp/test_stress_arp.py†L204-L214】

## 4. Dependencies and Prerequisites
- **Fixtures:** `duthost`, `garp_enabled`, `ip_and_intf_info`, `intfs_for_test`, `ptfadapter`, `get_function_completeness_level`, `ptfhost`, `config_facts`, `tbinfo`, `proxy_arp_enabled`. These provide DUT access, feature gates, interface details, packet IO handles, configuration context, and topology metadata necessary to drive the tests.【F:tests/arp/test_stress_arp.py†L66-L225】
- **Topology:** Requires T0 infrastructure per `pytestmark` to offer VLAN interfaces and PTF access for traffic injection.【F:tests/arp/test_stress_arp.py†L23-L26】
- **Clean State:** Dependence on `arp_cache_fdb_cleanup` to ensure ARP/FDB tables start clean, preventing stale data from affecting measurements.【F:tests/arp/test_stress_arp.py†L38-L52】
- **CRM Availability:** Tests rely on CRM resource counters being exposed on the DUT to gauge capacity limits before sending traffic.【F:tests/arp/test_stress_arp.py†L96-L111】【F:tests/arp/test_stress_arp.py†L173-L187】

## 5. Key Inputs and Parameters
- **Constants:** `ARP_BASE_IP`, `ARP_SRC_MAC`, `ENTRIES_NUMBERS`, `TEST_CONNTRACK_TIMEOUT`, `TEST_INCOMPLETE_NEIGHBOR_CNT` define address pools, MAC derivation, stress limits, conntrack timeout override, and incomplete neighbor targets respectively.【F:tests/arp/test_stress_arp.py†L16-L21】
- **`LOOP_TIMES_LEVEL_MAP`:** Maps the `get_function_completeness_level` fixture result to loop iterations, tuning stress intensity from debug to diagnose.【F:tests/arp/test_stress_arp.py†L28-L36】
- **CRM Counters:** Values returned by `get_crm_resources` for neighbors, FDB, and nexthops control how many entries are injected to avoid exhausting hardware tables.【F:tests/arp/test_stress_arp.py†L96-L111】【F:tests/arp/test_stress_arp.py†L173-L187】
- **`garp_enabled` / `proxy_arp_enabled`:** Gate whether ARP/ND stress runs, derived from device configuration fixtures.【F:tests/arp/test_stress_arp.py†L114-L116】【F:tests/arp/test_stress_arp.py†L166-L169】
- **Interface indices and addresses** provided by `ip_and_intf_info` and `intfs_for_test` specify PTF ports and VLAN IPs used for packet injection.【F:tests/arp/test_stress_arp.py†L118-L126】【F:tests/arp/test_stress_arp.py†L160-L167】

## 6. External Libraries and Modules
- **`pytest` / `pytest.mark`:** Testing framework providing fixtures, markers, and assertions.【F:tests/arp/test_stress_arp.py†L1-L34】
- **`ptf.testutils`:** Packet Test Framework utilities for crafting and transmitting L2/L3 packets from the PTF host.【F:tests/arp/test_stress_arp.py†L7-L8】【F:tests/arp/test_stress_arp.py†L58-L79】【F:tests/arp/test_stress_arp.py†L204-L214】
- **`tests.common.helpers.assertions` (`pytest_assert`, `pytest_require`):** Custom assertion wrappers integrating with SONiC test reporting.【F:tests/arp/test_stress_arp.py†L8-L10】【F:tests/arp/test_stress_arp.py†L101-L117】
- **`scapy.all`:** Provides packet crafting for IPv6 ND (Ether, IPv6, ICMPv6) and address manipulation helpers (`in6_getnsmac`, `in6_getnsma`, `inet_pton`, `inet_ntop`).【F:tests/arp/test_stress_arp.py†L9-L11】【F:tests/arp/test_stress_arp.py†L148-L158】
- **`ipaddress`:** Used to calculate IPv6 addresses for generated neighbors.【F:tests/arp/test_stress_arp.py†L12-L15】【F:tests/arp/test_stress_arp.py†L139-L150】
- **`tests.common.utilities` (`wait_until`, `increment_ipv6_addr`):** Polling helper ensures FDB counts converge; IPv6 address incrementer supports neighbor generation.【F:tests/arp/test_stress_arp.py†L12-L13】【F:tests/arp/test_stress_arp.py†L123-L137】【F:tests/arp/test_stress_arp.py†L148-L165】
- **`tests.common.errors.RunAnsibleModuleFail`:** Exception class to gracefully handle Ansible module failures when clearing ARP/FDB state.【F:tests/arp/test_stress_arp.py†L13-L50】
- **Local module `.arp_utils`:** Supplies MAC/int conversion, CRM access, FDB cleanup, and ARP cache clearing utilities specific to ARP testing.【F:tests/arp/test_stress_arp.py†L5-L7】【F:tests/arp/test_stress_arp.py†L96-L137】
- **Standard libraries (`logging`, `time`, `random`, `socket`):** Logging, timing delays, random entry selection, and socket operations used throughout packet generation and conntrack handling.【F:tests/arp/test_stress_arp.py†L1-L11】【F:tests/arp/test_stress_arp.py†L54-L214】

## 7. Unspecified Items
- Details about the precise contents of fixtures (`ip_and_intf_info`, `intfs_for_test`, etc.) are **Not specified** in this file.
- Specific CRM thresholds from `testbed.yaml` or inventory files are **Not specified**.
- External configuration enabling `garp_enabled` and `proxy_arp_enabled` is **Not specified** within the test script.
