# tests/radv/test_radv_ipv6_ra.py – Analyzer

## 1. Topology type
- **Topology marks:** The module is tagged for the `t0`, `m0`, and `mx` topologies, indicating it is intended to run on any of these multi-access VLAN-based environments, and is marked for the `vs` (virtual switch) device type.【F:tests/radv/test_radv_ipv6_ra.py†L15-L18】
- **Inference:** The tests iterate over VLAN interfaces and their mapped PTF ports discovered from minigraph facts, which are characteristic of TOR-based T0/multi-TOR setups in SONiC (gathered through `get_extended_minigraph_facts`).【F:tests/radv/test_radv_ipv6_ra.py†L34-L70】

## 2. Overall test case purpose
- **Goal:** Validate that the RADV (Router Advertisement Daemon) on the DUT correctly emits IPv6 Router Advertisements (RAs) on every downlink VLAN interface, both unsolicited (periodic) and in response to solicitations, including verifying the Managed (M) flag behavior.【F:tests/radv/test_radv_ipv6_ra.py†L114-L222】
- **Context:** In the SONiC test framework, this ensures IPv6 host configuration via Neighbor Discovery functions as expected on access VLANs, using PTF-host based verification through ptftests runners to emulate host behavior and validate RA properties.【F:tests/radv/test_radv_ipv6_ra.py†L124-L167】【F:tests/radv/test_radv_ipv6_ra.py†L179-L222】

## 3. Detailed breakdown of sub-testcases
- **`test_radv_router_advertisement`:**
  - Iterates through each discovered VLAN/PTF pair, adjusts RA intervals via fixture, and runs the `RadvUnSolicitedRATest` ptftest to check that periodic (unsolicited) RAs are emitted with correct MAC/IP pairing and interval bounds.【F:tests/radv/test_radv_ipv6_ra.py†L114-L139】
  - This confirms baseline RA delivery for IPv6 host bootstrapping, forming the foundation for all subsequent RA validations.
- **`test_solicited_router_advertisement`:**
  - For each VLAN/PTF pair, executes `RadvSolicitedRATest` on the PTF host, supplying both DUT and PTF link-local addresses, to verify the DUT replies correctly to RA solicitations.【F:tests/radv/test_radv_ipv6_ra.py†L142-L167】
  - Ensures the DUT responds to host solicitations, validating robustness of RA exchange beyond periodic announcements.
- **`test_unsolicited_router_advertisement_with_m_flag`:**
  - Runs the M-flag-specific `router_adv_mflag_test.RadvUnSolicitedRATest`, checking that unsolicited RAs advertise DHCPv6-managed addressing via the Managed flag when expected.【F:tests/radv/test_radv_ipv6_ra.py†L170-L195】
  - This verifies policy signaling for address assignment mode in periodic announcements.
- **`test_solicited_router_advertisement_with_m_flag`:**
  - Uses `router_adv_mflag_test.RadvSolicitedRATest` to ensure solicited RAs also carry the proper Managed flag and interface metadata.【F:tests/radv/test_radv_ipv6_ra.py†L197-L222】
  - Confirms consistency of DHCPv6-related signaling in responses to host solicitations.
- **Helper fixtures:**
  - `radv_test_setup` auto-collects VLAN/PTF metadata (names, MACs, link-local IPv6 addresses) used across all tests.【F:tests/radv/test_radv_ipv6_ra.py†L26-L72】
  - `dut_update_radv_periodic_ra_interval` temporarily tunes RA intervals in the radvd container to deterministic values and restores configuration post-test.【F:tests/radv/test_radv_ipv6_ra.py†L84-L111】
  - `dut_update_ra_interval` encapsulates config edits for Min/Max RA intervals within radvd’s configuration file.【F:tests/radv/test_radv_ipv6_ra.py†L75-L81】

## 4. Dependencies and prerequisites
- **Fixtures:** `duthosts`, `rand_one_dut_hostname`, `ptfhost`, `tbinfo`, and dual ToR simulator control are required to select the DUT, access topology data, and ensure mux ports are aligned during testing.【F:tests/radv/test_radv_ipv6_ra.py†L26-L72】【F:tests/radv/test_radv_ipv6_ra.py†L114-L222】
- **Services/configs:** The RADV container/service must be running with an accessible `/etc/radvd.conf`, and the test can back up and restore this file inside the container.【F:tests/radv/test_radv_ipv6_ra.py†L84-L111】
- **PTF environment:** `ptf_runner` invokes ptftests modules on the PTF host; supporting fixtures (copying ptf tests, changing MACs, GARP, ICMP responder) are imported for autouse behavior to prepare the PTF environment.【F:tests/radv/test_radv_ipv6_ra.py†L6-L13】【F:tests/radv/test_radv_ipv6_ra.py†L129-L139】

## 5. Key inputs and parameters
- **RADV configuration paths and intervals:** Constants define config file locations and desired RA intervals (3–4 seconds) used when tuning radvd behavior during tests.【F:tests/radv/test_radv_ipv6_ra.py†L20-L23】【F:tests/radv/test_radv_ipv6_ra.py†L99-L103】
- **Topology-derived data:** VLAN names, MAC addresses, and link-local IPv6 addresses are retrieved from minigraph facts and PTF shell commands, feeding into ptftest parameters such as `downlink_vlan_mac`, `downlink_vlan_ip6`, `ptf_port_index`, and `ptf_port_ip6`.【F:tests/radv/test_radv_ipv6_ra.py†L34-L70】【F:tests/radv/test_radv_ipv6_ra.py†L133-L166】【F:tests/radv/test_radv_ipv6_ra.py†L188-L221】
- **Ptftest parameters:** Each ptf invocation specifies the DUT hostname, RA interval expectations, and KVM support flag to drive the test harness accurately.【F:tests/radv/test_radv_ipv6_ra.py†L129-L139】【F:tests/radv/test_radv_ipv6_ra.py†L157-L167】【F:tests/radv/test_radv_ipv6_ra.py†L185-L222】

## 6. External libraries and modules
- **Standard libs:** `ipaddress` validates link-local IPv6 formats; `logging` records progress; `pytest` provides fixture and marker infrastructure.【F:tests/radv/test_radv_ipv6_ra.py†L1-L4】
- **SONiC utilities:** Imports from `tests.common.fixtures.ptfhost_utils` prepare the PTF host (copy tests, adjust MACs, run support services).【F:tests/radv/test_radv_ipv6_ra.py†L6-L9】
- **Dual ToR helpers:** `mock_server_base_ip_addr` and `toggle_all_simulator_ports_to_rand_selected_tor_m` manage mux simulator behavior to align with the selected TOR during testing.【F:tests/radv/test_radv_ipv6_ra.py†L10-L11】
- **Assertion and runner helpers:** `pytest_assert` standardizes assertions, and `ptf_runner` executes ptftests remotely from pytest.【F:tests/radv/test_radv_ipv6_ra.py†L12-L13】

## 7. Unspecified items
- Specific testbed.yaml variables, inventory groups, or external configuration details beyond what is gathered from minigraph facts are **not specified** in this file.
