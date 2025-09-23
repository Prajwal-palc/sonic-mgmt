# BGP Fast Reboot Test Analyzer

## 1. Topology type
- **Topology:** Dual-DUT point-to-point with a single traffic generator connected to DUT1 on two ports (IPv4 and IPv6 legs).
- **Inference:** The module autouse fixture calls `st.ensure_min_topology("D1D2:1", "D1T1:2")`, which requires one link between DUT1 and DUT2 and two links between DUT1 and the TG. Subsequent configuration helpers repeatedly reference `vars.D1`, `vars.D2`, `vars.D1D2P1`, `vars.D1T1P1`, and `vars.D1T1P2`, confirming the two-DUT plus TG arrangement.

## 2. Overall test case purpose
- The test suite validates that SONiC retains BGP control-plane resiliency across a fast reboot. It proves that IPv4 and IPv6 eBGP sessions between two DUTs and IPv4/IPv6 iBGP sessions between DUT1 and a traffic generator re-establish after a fast reboot, confirming configuration persistence and neighbor recovery timing within the SpyTest automation framework.

## 3. Detailed breakdown of sub-testcases
### Autouse fixtures and setup helpers
- **`bgp_fast_reboot_module_hooks`** – Automatically provisions the environment before tests run. It secures the required topology, enables global IPv6 on both DUTs, configures IPv4/IPv6 addressing, builds eBGP between the DUTs and iBGP to the TG, brings up TG BGP sessions, and verifies that all neighbors reach Established state. On teardown it removes BGP, IP, VLAN, and port-channel configuration so the lab resets cleanly.
- **`bgp_fast_reboot_func_hooks`** – Function-scope autouse placeholder that currently just yields, giving room for per-test cleanup if future scenarios require it.

### `test_ft_bgp_fast_reboot`
- **Intent & logic:**
  - Enables docker routing configuration mode on both DUTs so FRR/vtysh configuration is accessible from SONiC.
  - Saves the running configuration and triggers a fast reboot on DUT1.
  - After the reboot it re-verifies IPv4 (and optionally IPv6, if `data.ipv6_support` is true) BGP neighborship using the previously defined verification helpers.
  - Reports the test as passed once neighbor sessions recover post-reboot.
- **Relevance:** This is the core validation showing that a SONiC device can withstand a fast reboot without losing BGP peering relationships or requiring manual intervention, directly addressing the high-level goal of control-plane resiliency.

### Supporting helper functions
- **IP configuration helpers (`ipv4_ip_address_config`, `verify_ipv4_address_config`, `ipv6_address_config`, `verify_ipv6_address_config`)** – Program DUT and TG-facing interfaces with static IPv4/IPv6 addressing and validate the assignments before the main test starts, ensuring the underlay is correct.
- **BGP configuration helpers (`ipv4_bgp_config`, `ipv6_bgp_config`)** – Instantiate BGP routers, redistribute connected routes, and create the DUT-to-DUT eBGP and DUT-to-TG iBGP neighbors for both address families.
- **Traffic generator helpers (`tg_bgp_config`, `tg_bgpv6_config`)** – Reset TG ports, configure interfaces, bring up emulated BGP peers with four-byte AS numbers, and advertise 100 prefixes so that neighbor formation and route learning can be exercised.
- **Verification helpers (`verify_v4_bgp_neigborship`, `verify_v6_bgp_neigborship`)** – Wait for the configured amount of time and confirm every IPv4/IPv6 eBGP and iBGP session is in Established state using FRR (`vtysh`) outputs, triggering SpyTest failures if any peer is down.

## 4. Dependencies and prerequisites
- **Fixtures & framework hooks:** Relies on SpyTest’s autouse fixtures to prepare and clean the environment, and on `st.ensure_min_topology` to guarantee the lab has the required connections.
- **Topology constraints:** Requires two SONiC DUTs with at least one routed link between them and two TG-facing links on DUT1, plus IPv6 capability enabled on both devices.
- **Libraries & APIs:** Depends on SpyTest routing/system APIs (`ip_obj`, `bgp_obj`, `reboot_obj`), switching cleanup APIs (`vlan_obj`, `portchannel_obj`), and TG abstractions (`tgapi`) to drive configuration and validation.

## 5. Key inputs and parameters
- **Static addressing and ASNs:** `SpyTestDict data` seeds IPv4/IPv6 interface addresses (`local_ip_addr`, `neigh_ip_addr`, `d1t1_ip_addr`, `d1t1_ip6_addr`, etc.), router IDs, loopbacks, and four-byte ASNs (`local_asn4`, `remote_asn4`) that determine all BGP sessions.
- **Feature flags:** `data.ipv6_support` gates whether IPv6 configuration and checks execute, and `st.is_feature_supported("bgp-neighbotship-performance", vars.D1)` can extend `data.neighborship_wait` from 10 to 30 seconds to accommodate slower platforms.
- **Operational modes:** `data.shell_vtysh` directs verification helpers to use the FRR shell, while `data.shell_sonic` is available if SONiC CLI access were needed. `data.tg_bgp_route_prfix` and the TG route counts influence the emulated route advertisement mix.

## 6. External libraries and modules
- **`pytest`** – Supplies fixture scoping and the test decorator infrastructure.
- **`spytest.st`** – Core SpyTest service used for logging, topology discovery, waiting, reboot orchestration, and reporting pass/fail outcomes.
- **`spytest.tgapi`** – Abstracts traffic generator handle lookup and per-port configuration so TG BGP sessions can be formed.
- **`SpyTestDict`** – Convenience container for shared test data (`data`).
- **`apis.system.reboot`** – Provides `config_save` utilities used before reboot.
- **`apis.routing.ip`** – Offers IP interface configuration and verification routines.
- **`apis.routing.bgp`** – Handles all BGP router, neighbor, and verification operations, including enabling docker routing config mode.
- **`apis.switching.portchannel` / `apis.switching.vlan`** – Used only during teardown to clear residual L2 constructs.

## 7. Unspecified items
- Exact hardware models, SONiC image versions, and the concrete `testbed.yaml` inventory details are not specified in this test file.
- Traffic generator vendor/model specifics, advertised prefix contents beyond their counts, and post-reboot timing expectations other than the wait parameter are not specified.
