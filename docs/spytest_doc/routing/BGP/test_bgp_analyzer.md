# BGP Functional Test Analyzer

## 1. Topology type
- **Topology:** Leaf-spine setup with two DUTs (spine = D1, leaf = D2) and a traffic generator leg per DUT. The module autouse fixture calls `st.ensure_min_topology('D1D2:1', 'D1T1:1', 'D2T1:1')`, which requires a DUT-to-DUT link and one TG connection per DUT, and subsequent helpers such as `bgplib.get_leaf_spine_topology_info()` and `bgplib.l3tc_vrfipv4v6_address_leafspine_*` configure spine/leaf roles.
- **Inference:** Repeated references to "spine" and "leaf" in `bgplib` helpers, `topo.spine_list`/`topo.leaf_list`, and the expectation of TG-facing ports reveal the classic two-tier fabric assumption rather than a simple point-to-point link or ring.

## 2. Overall test case purpose
- The file validates SONiC's BGP control-plane and data-plane behavior across IPv4/IPv6, covering neighbor formation, resilience (clear/reboot/update-delay), policy features (route-maps, prefix/AS-path/distribute/filter lists), redistribution (connected/static/blackhole), aggregation (including AS_SET and 4-byte ASNs), graceful restart, confederations, authentication, and traffic forwarding.
- SpyTest orchestrates configuration on DUTs and traffic generators, exercising SONiC CLI layers (`vtysh`, `klish`) via `bgpapi`, `ipapi`, `tgapi`, and `bgplib` to emulate end-to-end workflows expected in SONiC regression suites.

## 3. Detailed breakdown of sub-testcases
### Common infrastructure and helpers
- **`bgp_module_hooks` (module autouse fixture)** – Normalizes traffic generator rates, derives the UI type (`bgp_cli_type`), ensures topology availability, pre-configures loopbacks, VLANs, port-channels, and TG BGP sessions through `bgp_pre_config`, and performs clean-up post-module.
- **`bgp_pre_config` / `bgp_pre_config_cleanup`** – Provide module-wide base configuration and teardown for DUT interfaces, loopbacks, and traffic generator sessions.
- **`TestBGPCommon` utility methods** – Offer reusable flows for BGP clearing, traffic tests, graceful restart, and aggregation checks. Derived classes invoke these for specific topologies.

### `TestBGPRif`
- **`test_ft_bgp_v6_link_local_bgp`** – Enables BGP neighbor sessions over IPv6 link-local interfaces on both leaf and spine, confirms update counters, and verifies adjacency formation, proving SONiC can peer using link-local addresses and log activity.
- **`test_ft_bgp_clear`** – Uses the common `ft_bgp_clear` helper to issue both SONiC and FRR BGP clear commands and ensure sessions recover, validating operational resiliency.
- **`test_ft_bgp_peer_traffic_check`** – Leverages the common traffic procedure to advertise 100 IPv4 routes, manipulate update-delay timer behavior, verify RIB population timing, test ping reachability, and send TG-driven traffic to confirm data-plane forwarding under delayed updates.
- **`test_ft_bgp_graceful_restart_and_aware_routers`** – Applies the graceful-restart preserve-forwarding-state knob on a leaf router and ensures adjacency with a GR-aware spine, demonstrating support for GR compatibility.
- **`test_ft_bgp_ipv4_no_route_aggregation_for_exact_prefix_match`** – Configures an aggregate on the leaf, advertises component routes from the TG, and checks the spine retains the specific prefix when an exact match is present, preventing unwanted summarization.
- **`test_ft_bgp_ipv4_route_aggregation_atomic_aggregate_without_as_set`** – Validates that when an aggregate is marked summary-only without AS_SET, the neighbor sees the summarized prefix (with aggregator/atomic attributes) and no longer sees individual routes; also enables zebra logging to inspect updates.
- **`test_bgp_route_aggregation_4byteASN`** – Similar to the IPv4 aggregation test but ensures AS_SET preserves the full AS-path for an aggregate containing a 4-byte ASN, confirming large ASNs propagate correctly.
- **`test_ft_bgp_ipv6_route_aggregation_with_as_set`** – Mirrors aggregation logic for IPv6 with AS_SET to ensure the aggregated IPv6 prefix carries full AS-path data.
- **`test_ft_bgp_v4_dyn_nbr`** – Uses dynamic neighbor listen ranges with 4-byte AS numbers, configures per-peer listen ranges on leaf and static peers on spine, and ensures dynamic peering forms and cleans up.
- **`test_ft_bgp_v6_dyn_nbr`** – Performs IPv6 dynamic neighbor peering by configuring listen ranges and static neighbors, verifying adjacency, and cleaning the IP/listen configuration.
- **`test_ft_bgp_v4_max_dyn_nbr`** – Iterates through a limit of five listen ranges, configuring multiple dynamic neighbors simultaneously and verifying each neighbor reaches Established state, stressing scaling.
- **`test_ft_bgp_rmap`** – Advertises a network, applies an access list + route-map to deny it, and confirms the peer no longer learns the route, testing outbound policy application after routes exist.
- **`test_ft_bgp_rmap_out`** – Builds a multi-sequence route-map with various match/set clauses (including AS-path prepends), validates the correct networks are permitted or denied and attributes modified accordingly.
- **`test_ft_bgp_ebgp_confed`** – Configures BGP confederation peers, ties an outbound route-map on the spine, advertises matching and non-matching routes via TG, and ensures only permitted prefixes reach the leaf, validating policy within confederations.

### `TestBGPIPvxRouteAdvertisementFilter`
- **`test_redistribute_connected_ipv4`** – Enables redistribution of connected IPv4 routes from DUT1 and checks DUT2 learns all connected prefixes, validating redistribution controls.
- **`test_redistribute_static_ipv4`** – Installs static routes and ensures they are redistributed when enabled, confirming policy for static routes.
- **`test_distribute_list_in_ipv4`** – Applies an inbound distribute-list ACL on DUT2 and checks suppression of a specific prefix, verifying access-list-based filtering (skipped for unsupported UI types).
- **`test_filter_list_in_ipv4`** – Uses an AS-path filter-list inbound on DUT2 to block routes sourced from DUT1's AS, confirming AS-path filtering.
- **`test_prefix_list_out_ipv4`** – Applies outbound prefix-lists on DUT2 to suppress advertising a particular IPv4 prefix to DUT1, covering export policies.
- **`test_default_originate_ipv4`** – Enables default-originate (with route-map) toward DUT1 and confirms a 0.0.0.0/0 route is advertised, ensuring default route injection works.
- **`test_route_map_in_ipv4`** – Applies inbound route-map `SETPROPS` on DUT2 to change metrics and local-pref for specified networks, verifying attribute manipulation.
- **`test_redistribute_connected_ipv6`** – Mirrors the connected redistribution test for IPv6, filtering out link-local addresses and confirming receipt on DUT2.
- **`test_redistribute_static_ipv6`** – Adds IPv6 static routes and ensures redistribution yields the expected learned routes on DUT2.
- **`test_distribute_list_in_ipv6`** – Applies an inbound distribute-list on IPv6 neighbors to suppress a prefix, verifying IPv6 ACL-based filtering (skips unsupported UI types).
- **`test_filter_list_in_ipv6`** – Uses inbound IPv6 AS-path filter-lists to block routes from DUT1's AS.
- **`test_prefix_list_out_ipv6`** – Enforces an outbound IPv6 prefix-list to prevent advertising a specific prefix while permitting others.
- **`test_filter_list_out_ipv6`** – Applies an outbound filter-list to block routes based on AS_PATH before export.
- **`test_default_originate_ipv6`** – Enables IPv6 default-originate toward DUT1 and verifies `::/0` propagation.
- **`test_route_map_in_ipv6`** – Uses inbound IPv6 route-map `SETPROPS6` to adjust metric and local-pref for targeted prefixes.
- **`test_bgp_route_map_with_community`** – Configures a route-map matching on community and ensures only routes tagged with `100:100` are accepted, verifying community-based filtering.
- **`test_bgp_ebgp4_nbr_update_source`** – Configures eBGP neighbors with explicit update-source interfaces and ebgp-multi-hop on both peers, clears sessions, and confirms adjacency recovers, validating update-source support.
- **`test_bgp_ebgp4_nbr_authentication`** – Applies BGP passwords on both IPv4 neighbors, clears sessions, reboots DUT1, and ensures adjacency survives, confirming MD5 auth persistence.
- **`test_bgp_ebgp6_traffic`** – Advertises 500 IPv6 routes from TG toward each DUT, verifies RIB counts, runs IPv6 traffic flows in both directions, reboots DUT1, and ensures routes persist/recover, validating large-scale IPv6 eBGP forwarding and resiliency.
- **`test_route_aggregate_ipv6`** – Aggregates multiple IPv6 static blackhole routes into a summary and confirms only the aggregate is redistributed, proving summarization works.
- **`test_static_blackhole_rt_redistribute_with_routemap_ipv6`** – Redistributes an IPv6 blackhole static route with a route-map metric and verifies the downstream AS receives the metric value, ensuring policy application on blackhole redistribution.

### `TestBGPVeLag`
- **`test_ft_bgp_clear`** – Reuses the common clear test but under the VE-over-LAG topology created by `bgp_ve_lag_class_hook`, validating the same resiliency when neighbors run over virtual Ethernet LAGs.
- **`test_ft_bgp_peer_traffic_check`** – Executes the common traffic/update-delay scenario in the VE-over-LAG environment to ensure forwarding survives bundled interfaces.

### `TestBGPL3Lag`
- **`test_ft_bgp_l3lag_peer_traffic_check`** – Runs the traffic/update-delay procedure with L3-over-LAG connectivity, confirming BGP sessions and traffic forwarding across routed port-channels.

### Additional fixtures
- **`bgp_rif_class_hook`, `bgp_ve_lag_class_hook`, `bgp_l3_lag_class_hook`** – Prepare respective underlay configurations (physical interfaces, VE LAGs, L3 LAGs) using `bgp_type_pre_config` and clean up after class execution.
- **`bgp_rif_func_hook`, `bgp_ve_lag_func_hook`, `bgp_ipvx_route_adv_func_hook`, `bgp_ipvx_route_advt_func_hook`** – Provide per-test clean-up or additional configuration toggles (e.g., revert route-maps, remove update-delay, undo update-source settings).

## 4. Dependencies and prerequisites
- **Fixtures:** Module-level `bgp_module_hooks`; class fixtures (`bgp_rif_class_hook`, `bgp_ipvx_route_adv_filter_fixture`, `bgp_ve_lag_class_hook`, `bgp_l3_lag_class_hook`); function fixtures for targeted cleanup/toggles.
- **Topology:** Requires at least two SONiC DUTs with TG connectivity and capabilities to form IPv4/IPv6 BGP sessions, including support for VE/L3 LAG variations.
- **Stateful data:** Uses global `topo`/`bgplib.data` for interface names, ASNs, and TG handles.
- **Traffic generator:** Relies on SpyTest TG APIs (`tgapi`) for BGP emulation and traffic streams.

## 5. Key inputs and parameters
- **AS numbers & neighbors:** Pulled from `bgplib.data` (e.g., `spine_as`, `leaf_as`) and topology dictionaries (`info['D1_as']`, `topo['T1D1P1_ipv4']`).
- **Traffic shaping:** Module-scoped `rate_pps` and derived `pkts_per_burst` drive TG flows; `tgapi.normalize_pps` adjusts them to lab capacity.
- **Policy names:** Route-maps (`test-rmap`, `SETPROPS`, `rmap1`, `UseGlobal`, etc.), prefix-lists (`PREFIXOUT`, `PREFIXOUT6`), distribute/filter lists (`11`, `FILTER`, `FILTER6`), communities (`100:100`), and peer-groups (`leaf_spine`, `spine_leaf`).
- **Prefixes:** Numerous IPv4/IPv6 networks for testing aggregation, redistribution, and filtering (e.g., `122.1.1.0/24`, `123.1.0.0/16`, `6002:1::/64`, `2018:3::/32`).
- **Timers & thresholds:** Update-delay timer (`60` seconds) and listen limits (`limit = 5`) define stress scenarios; traffic verification expects ≥95% success ratios.

## 6. External libraries and modules
- **`pytest`** – Provides fixtures, parametrization, and test structure.
- **`spytest.st`** – SpyTest service wrapper for logging, assertions, topology helpers, and CLI execution.
- **`spytest.tgapi`** – Traffic generator abstraction for emulated BGP sessions and traffic control.
- **`apis.routing.ip`, `apis.routing.bgp`** – SONiC API layers for IP/BGP configuration, verification, and show commands.
- **`apis.switching.vlan`, `apis.switching.portchannel`** – Used during pre-configuration to reset switching constructs.
- **`apis.system.logging`, `apis.system.reboot`** – Inspect syslogs and handle device reboots/config saves.
- **`BGP.bgplib`** – SpyTest BGP topology helper providing canned configuration flows, route advertisement utilities, and topology metadata.
- **`utilities.common`** – Utility helpers like `exec_foreach` and error handling.

## 7. Unspecified items
- Exact hardware SKU, ASIC type, or SONiC image build are not specified.
- Detailed contents of `bgplib.data` (e.g., actual ASNs/IPs) and underlying `testbed.yaml` inventory are not included in this file.
- Traffic generator model, licensing, or port mappings beyond logical handles are not described.
