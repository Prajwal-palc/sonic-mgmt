# VRF Test Plan Analyzer

## 1. Topology Type
* **Declared Topology:** The entire module is marked with `pytest.mark.topology('t0')`, indicating it is written for the T0 data-center leaf topology.【F:tests/vrf/test_vrf.py†L39-L41】
* **Inference Details:**
  * The setup fixture loads `../ansible/vars/topo_<name>.yml` based on `tbinfo['topo']['name']`, reinforcing that the testbed metadata aligns with T0 topology descriptors.【F:tests/vrf/test_vrf.py†L485-L547】
  * Helpers and fixtures rely on VLAN1000/2000 and dual-homed PortChannels that are characteristic of the canonical SONiC T0 layout.【F:tests/vrf/test_vrf.py†L275-L343】【F:tests/vrf/test_vrf.py†L716-L812】

## 2. Overall Test Case Purpose
* **Primary Goal:** Validate end-to-end Virtual Routing and Forwarding (VRF) functionality on a SONiC DUT, covering creation, binding, neighbor formation, forwarding, policy enforcement, resilience, scale, and teardown behaviors.【F:tests/vrf/test_vrf.py†L625-L1656】
* **Framework Context:** The suite exercises SONiC VRF orchestration via Ansible-driven configuration templates, PTF-based traffic validation, and system-level checks (databases, kernel, warm reboot, ACL redirect). It ensures that VRFs behave correctly across SONiC control/data plane components (config DB, APP DB, ASIC DB, FRR) within the SONiC PyTest automation framework.【F:tests/vrf/test_vrf.py†L257-L399】【F:tests/vrf/test_vrf.py†L485-L620】

## 3. Detailed Breakdown of Sub-Testcases
### Helper and Fixture Roles
* Utility functions (`get_vlan_members`, `get_intf_ips`, etc.) derive port/IP mappings and configuration facts used across tests.【F:tests/vrf/test_vrf.py†L55-L399】
* `setup_vrf` performs one-time VRF topology provisioning, backing up config DB, generating templates, clearing tables, and preparing peer namespaces on the PTF host.【F:tests/vrf/test_vrf.py†L485-L547】
* `partial_ptf_runner` wraps `ptf_runner` with standard arguments so each traffic test provides only scenario-specific parameters.【F:tests/vrf/test_vrf.py†L549-L564】

### Class `TestVrfCreateAndBind`
* `test_vrf_in_kernel`: Verifies VRF devices and interface bindings exist in the Linux kernel after setup.【F:tests/vrf/test_vrf.py†L625-L646】
* `test_vrf_in_appl_db`: Ensures VRFs and interfaces appear in the APP_DB state.【F:tests/vrf/test_vrf.py†L647-L659】
* `test_vrf_in_asic_db`: Confirms ASIC DB contains the expected number of virtual router entries (VRFs + default).【F:tests/vrf/test_vrf.py†L661-L668】

### Class `TestVrfNeigh`
* `test_ping_lag_neigh`: Pings BGP neighbors bound to VRFs over LAG interfaces to ensure reachability and neighbor resolution.【F:tests/vrf/test_vrf.py†L670-L685】
* `test_ping_vlan_neigh`: Pings dynamically created VLAN peers in each VRF using VRF-aware source interfaces to validate connectivity.【F:tests/vrf/test_vrf.py†L687-L694】
* `test_vrf1_neigh_ip_fwd` & `test_vrf2_neigh_ip_fwd`: Use PTF to send neighbor-based traffic and confirm forwarding within each VRF’s access network.【F:tests/vrf/test_vrf.py†L696-L712】

### Class `TestVrfFib`
* `setup_fib_test`: Generates FIB expectation files for both VRFs using topology metadata (executed once per class).【F:tests/vrf/test_vrf.py†L717-L724】
* `test_show_bgp_summary`: Checks VRF-specific BGP sessions for correct prefix counts derived from topology properties.【F:tests/vrf/test_vrf.py†L725-L746】
* `test_vrf1_fib` & `test_vrf2_fib`: Replay PTF FibTest traffic to verify ECMP forwarding alignment with generated FIBs.【F:tests/vrf/test_vrf.py†L748-L760】

### Class `TestVrfIsolation`
* `setup_vrf_isolation`: Prepares neighbor and FIB files for isolation checks.【F:tests/vrf/test_vrf.py†L763-L776】
* Isolation tests (`test_neigh_isolate_*`, `test_fib_isolate_*`): Verify that traffic sourced in one VRF to destinations of another is dropped, confirming data-plane separation.【F:tests/vrf/test_vrf.py†L777-L811】

### Class `TestVrfAclRedirect`
* `is_redirect_supported`: Skips suite if hardware lacks ACL redirect capability.【F:tests/vrf/test_vrf.py†L814-L827】
* `setup_acl_redirect`: Programs ACL rules redirecting traffic from VRF1 PortChannel1 to alternate destinations, capturing source/destination port lists and neighbor addresses.【F:tests/vrf/test_vrf.py†L829-L895】
* Origin port tests (`test_origin_ports_recv_no_pkts_v4/v6`): Confirm redirected flows no longer reach original LAG members.【F:tests/vrf/test_vrf.py†L896-L918】
* Redirect tests (`test_redirect_to_new_ports_v4/v6`): Validate redirected traffic reaches new destinations and performs load-balancing checks.【F:tests/vrf/test_vrf.py†L920-L946】

### Class `TestVrfLoopbackIntf`
* `setup_vrf_loopback`: Captures loopback/VLAN IPs, configures PTF route namespaces, and enables IPv6 non-local bind to support loopback reachability.【F:tests/vrf/test_vrf.py†L949-L992】
* `test_ping_vrf1_loopback` & `test_ping_vrf2_loopback`: Use PTF and DUT pings to validate loopback reachability per VRF, handling IPv4/IPv6 nuances.【F:tests/vrf/test_vrf.py†L993-L1024】
* `setup_bgp_with_loopback`: Stages ExaBGP speakers and routes to test loopback-based BGP neighbors across VRFs.【F:tests/vrf/test_vrf.py†L1025-L1124】
* `test_bgp_with_loopback`: Confirms BGP sessions established over loopback interfaces with expected prefix counts.【F:tests/vrf/test_vrf.py†L1125-L1141】

### Class `TestVrfWarmReboot`
* `setup_vrf_warm_reboot`: Generates larger FIB datasets for stress during warm reboot tests.【F:tests/vrf/test_vrf.py†L1144-L1158】
* `test_vrf_swss_warm_reboot`: Sends continuous PTF FibTest traffic while restarting SWSS warm-reboot, verifying no traffic loss, reconciled states, and service/interface recovery.【F:tests/vrf/test_vrf.py†L1160-L1209】
* `test_vrf_system_warm_reboot`: Similar to above but triggers full system warm reboot, validating component reconciliation and service restoration.【F:tests/vrf/test_vrf.py†L1211-L1255】

### Class `TestVrfCapacity`
* Defines VRF scale constants and fixtures for configurable VRF counts and random subsets.【F:tests/vrf/test_vrf.py†L1258-L1291】
* `setup_vrf_capacity`: Bulk-creates VRFs, VLANs, RIFs, static routes, and PTF peers to approach VRF capacity limits; includes timing/back-off controls and cleanup strategy.【F:tests/vrf/test_vrf.py†L1292-L1471】
* `test_ping`: Runs scripted pings across randomly selected VRFs to validate neighbor reachability under scale.【F:tests/vrf/test_vrf.py†L1472-L1485】
* `test_ip_fwd`: Executes CapTest traffic to verify forwarding using generated neighbor mapping under large-scale VRF deployment.【F:tests/vrf/test_vrf.py†L1487-L1501】

### Class `TestVrfUnbindIntf`
* `setup_vrf_unbindintf`: Unbinds PortChannel1 from VRF1, allowing verification of cleanup behaviors before optional rebind in teardown.【F:tests/vrf/test_vrf.py†L1504-L1527】
* `rebind_intf` helper and `setup_vrf_rebind_intf` fixture: Reattach interfaces and IPs to VRF1 when required for post-rebind tests.【F:tests/vrf/test_vrf.py†L1529-L1546】
* Tests (`test_pc1_ip_addr_flushed`, `test_pc1_neigh_flushed`, `test_pc1_neigh_flushed_by_traffic`, `test_pc1_routes_flushed`): Confirm IPs, neighbors, and routes tied to the unbound interface are removed and traffic drops as expected.【F:tests/vrf/test_vrf.py†L1548-L1600】
* `test_pc2_neigh` & `test_pc2_fib`: Ensure other interfaces in VRF1 continue forwarding, demonstrating isolation of the unbound interface change.【F:tests/vrf/test_vrf.py†L1601-L1620】
* Post-rebind tests (`test_pc1_neigh_after_rebind`, `test_vrf1_fib_after_rebind`): Verify functionality returns once the interface is rebound.【F:tests/vrf/test_vrf.py†L1621-L1636】

### Class `TestVrfDeletion`
* `setup_vrf_deletion`: Removes Vrf1 after generating neighbor/FIB files, with teardown optionally restoring it.【F:tests/vrf/test_vrf.py†L1638-L1671】
* Restoration helper `restore_vrf` and fixture `setup_vrf_restore` rebuild Vrf1 when needed for post-restore tests.【F:tests/vrf/test_vrf.py†L1632-L1662】
* Flush validation tests (`test_pc1_ip_addr_flushed` through `test_vrf1_routes_flushed`): Assert VRF1-associated IPs, neighbors, and routes are purged after deletion.【F:tests/vrf/test_vrf.py†L1663-L1715】
* `test_vrf2_neigh` & `test_vrf2_fib`: Check that Vrf2 remains operational despite Vrf1 removal.【F:tests/vrf/test_vrf.py†L1716-L1723】
* Post-restore validations (`test_vrf1_neigh_after_restore`, `test_vrf1_fib_after_resotre`): Ensure connectivity returns once Vrf1 is recreated.【F:tests/vrf/test_vrf.py†L1724-L1731】

## 4. Dependencies and Prerequisites
* **Fixtures:** Relies on testbed fixtures (`tbinfo`, `duthosts`, `ptfhost`, `localhost`, `rand_one_dut_hostname`) and module fixtures for configuration facts and minigraph data.【F:tests/vrf/test_vrf.py†L456-L572】
* **Topology Constraints:** Requires T0 resources with VLAN1000/2000, PortChannels, and multiple VMs for VRF fanout, plus ability to manipulate config DB and restart services.【F:tests/vrf/test_vrf.py†L275-L343】【F:tests/vrf/test_vrf.py†L717-L760】
* **PTF Access:** Needs PTF host namespaces/macvlan support, ExaBGP capability, and ability to run shell scripts/templates deployed during setup.【F:tests/vrf/test_vrf.py†L294-L343】【F:tests/vrf/test_vrf.py†L1025-L1095】
* **Warm Reboot Support:** Assumes warm reboot functionality and warm restart control through CLI, plus monitoring of critical services and state DB entries.【F:tests/vrf/test_vrf.py†L189-L245】【F:tests/vrf/test_vrf.py†L1160-L1255】

## 5. Key Inputs and Parameters
* **`g_vars` state:** Stores dynamic topology info (VRF members, interface indices, peer namespaces) used throughout tests.【F:tests/vrf/test_vrf.py†L45-L50】【F:tests/vrf/test_vrf.py†L485-L526】
* **Topology properties (`props`):** Derived from topo YAML and drive expected BGP route counts and template rendering.【F:tests/vrf/test_vrf.py†L515-L518】【F:tests/vrf/test_vrf.py†L725-L746】
* **Template variables:** VRF/VLAN/route definitions fed into Jinja templates for config DB and PTF scripts (`vrf_config_db.j2`, `vrf_fib.j2`, `vrf_acl_redirect.j2`, etc.).【F:tests/vrf/test_vrf.py†L275-L399】【F:tests/vrf/test_vrf.py†L829-L884】【F:tests/vrf/test_vrf.py†L1292-L1471】
* **CLI options:** VRF capacity and test count can be overridden via pytest command-line options (`request.config.option.vrf_capacity`, `vrf_test_count`).【F:tests/vrf/test_vrf.py†L1278-L1290】
* **Traffic parameters:** `partial_ptf_runner` injects `testbed_type`, port maps, and dynamic kwargs for each traffic scenario (e.g., `pkt_action`, `fib_info_files`, `random_vrf_list`).【F:tests/vrf/test_vrf.py†L549-L564】【F:tests/vrf/test_vrf.py†L896-L946】

## 6. External Libraries and Modules
* **Standard/Python Libraries:** `json`, `yaml`, `logging`, `threading`, `tempfile`, `random`, `os`, `traceback` for data manipulation, logging, file handling, concurrency, and debugging.【F:tests/vrf/test_vrf.py†L1-L10】
* **Third-Party Modules:**
  * `natsort.natsorted` for natural ordering of interface lists.【F:tests/vrf/test_vrf.py†L12-L74】
  * `netaddr.IPNetwork` for IP arithmetic and masking.【F:tests/vrf/test_vrf.py†L14-L343】
  * `six.moves.queue` for cross-version queue handling in threaded tests.【F:tests/vrf/test_vrf.py†L15-L186】
* **PyTest:** Core testing framework providing fixtures, markers, and assertions (`pytest`, `pytest_assert`).【F:tests/vrf/test_vrf.py†L17-L25】【F:tests/vrf/test_vrf.py†L643-L646】
* **SONiC Test Utilities:**
  * `tests.ptf_runner.ptf_runner` for invoking PTF traffic scripts.【F:tests/vrf/test_vrf.py†L22-L564】
  * `tests.common.utilities.wait_until` for polling conditions (service recovery, state checks).【F:tests/vrf/test_vrf.py†L23-L24】【F:tests/vrf/test_vrf.py†L643-L645】
  * `tests.common.reboot.reboot` to trigger reboots of various types.【F:tests/vrf/test_vrf.py†L24-L25】【F:tests/vrf/test_vrf.py†L291-L292】
  * `tests.common.helpers.assertions.pytest_assert` for descriptive assertions.【F:tests/vrf/test_vrf.py†L24-L645】
  * PTF host utility fixtures for copying tests and manipulating MACs (imported though not directly used in this file).【F:tests/vrf/test_vrf.py†L19-L20】

## 7. Unspecified Items
* **Testbed Inventory Details:** Specific DUT models, port counts, and VM assignments beyond the generic T0 assumptions are not specified.
* **External Configuration Files:** The contents of referenced Jinja templates (`vrf/*.j2`) and shell scripts are not included in the test file, so exact configuration snippets are not specified.
