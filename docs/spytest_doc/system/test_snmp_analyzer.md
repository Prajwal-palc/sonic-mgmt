# SNMP System Test Analyzer

## Topology Type
- **Topology:** Single DUT with a two-port traffic generator (D1T1:2).
- **Inference:** The module-level fixture enforces `st.ensure_min_topology("D1T1:2")`, allocating one device under test (D1) with two traffic generator links (T1P1/T1P2). Subsequent configuration helpers reference `vars.D1T1P1` and `vars.D1T1P2`, confirming the single-DUT two-link layout.【F:spytest/tests/system/test_snmp.py†L21-L27】【F:spytest/tests/system/test_snmp.py†L94-L111】

## Overall Test Case Purpose
- **Goal:** Validate SONiC's SNMP agent comprehensively across read-only community access, interface/VLAN instrumentation, IPv4/IPv6/IP-MIB coverage, entity and environmental MIBs, VLAN dot1q tables, trap generation, service resilience, and SNMP counter accounting.
- **Context:** The suite exercises SNMP get/walk operations, trap verification, and counter inspection through SpyTest abstractions (`st`, `snmp_obj`, traffic generator APIs) to ensure SONiC platforms expose expected MIB data and respond to topology events. It extends SONiC SNMP regression coverage by checking default telemetry availability, correctness after service interruptions, and trap compliance with operational events like interface flaps and reboots.【F:spytest/tests/system/test_snmp.py†L21-L151】【F:spytest/tests/system/test_snmp.py†L592-L1523】

## Detailed Breakdown of Sub-Testcases
Each test is executed after module-level hooks provision SNMP community configuration, VLAN membership, traffic generation, and trap listener connectivity.

### test_ft_snmp_sysName
- **Logic:** Fetches hostname via CLI and compares it to SNMP GET on `sysName` OID to verify identity exposure.【F:spytest/tests/system/test_snmp.py†L164-L179】
- **Relevance:** Confirms management tools receive accurate device naming through SNMP.

### test_ft_snmp_test_syUpTime
- **Logic:** Compares CLI-reported uptime in seconds with SNMP `sysUpTime`, accepting small drift.【F:spytest/tests/system/test_snmp.py†L181-L199】
- **Relevance:** Validates timekeeping accuracy between local instrumentation and SNMP.

### test_ft_snmp_sysLocation
- **Logic:** Retrieves configured SNMP location via CLI helper and ensures SNMP `sysLocation` matches.【F:spytest/tests/system/test_snmp.py†L201-L216】
- **Relevance:** Checks SNMP configuration persistence is reflected in responses.

### test_ft_snmp_sysDescr
- **Logic:** Parses SNMP `sysDescr` output to confirm SONiC version and hwsku align with CLI `show version` data.【F:spytest/tests/system/test_snmp.py†L218-L245】
- **Relevance:** Verifies descriptive metadata for inventory management.

### test_ft_snmp_sysContact
- **Logic:** Confirms SNMP `sysContact` value (expected empty string) aligns with device state.【F:spytest/tests/system/test_snmp.py†L247-L262】
- **Relevance:** Ensures contact field reports correctly when unset or defaulted.

### test_ft_snmp_mib_2
- **Logic:** Performs SNMP walk across MIB-2 tree to ensure data is retrievable.【F:spytest/tests/system/test_snmp.py†L264-L274】
- **Relevance:** Baseline validation of core SNMP instrumentation.

### test_ft_snmp_if_mib_all
- **Logic:** Walks IF-MIB tree to verify interface counters are accessible.【F:spytest/tests/system/test_snmp.py†L276-L287】
- **Relevance:** Confirms network interface observability.

### test_ft_snmp_entity_mib_all
- **Logic:** Walks ENTITY-MIB to ensure chassis/component records exist.【F:spytest/tests/system/test_snmp.py†L289-L301】
- **Relevance:** Validates hardware inventory data exposure.

### test_ft_snmp_entity_sensor_mib
- **Logic:** Walks ENTITY-SENSOR-MIB to gather environmental sensor data.【F:spytest/tests/system/test_snmp.py†L303-L314】
- **Relevance:** Ensures temperature/voltage sensors publish telemetry.

### test_ft_snmp_dot1q_dot1db_mib
- **Logic:** Polls and walks dot1q and dot1d bridging MIBs for VLAN/FDB info.【F:spytest/tests/system/test_snmp.py†L316-L338】
- **Relevance:** Confirms L2 bridging data is available via SNMP.

### test_ft_snmp_root_node_walk
- **Logic:** Performs SNMP walk from root `.` OID to test general agent responsiveness.【F:spytest/tests/system/test_snmp.py†L340-L353】
- **Relevance:** Stress-tests SNMP agent navigation across whole tree.

### test_ft_snmp_ipAddressRowStatus_ipv6
- **Logic:** Walks IPv6 address row status table to ensure IPv6 addresses are reported.【F:spytest/tests/system/test_snmp.py†L355-L366】
- **Relevance:** Validates IPv6 addressing instrumentation.

### test_ft_snmp_ipAddressStorageType_ipv6
- **Logic:** Walks IPv6 storage type entries for addresses.【F:spytest/tests/system/test_snmp.py†L368-L379】
- **Relevance:** Confirms SNMP reports address persistence attributes.

### test_ft_snmp_ipv6_If_Forward_default_HopLimit
- **Logic:** Walks IPv6 forwarding and default hop-limit OIDs and ensures outputs exist.【F:spytest/tests/system/test_snmp.py†L381-L399】
- **Relevance:** Checks IPv6 routing/global parameters.

### test_ft_snmp_ipv6scope_index_table
- **Logic:** Walks IPv6 scope zone index table.【F:spytest/tests/system/test_snmp.py†L401-L412】
- **Relevance:** Validates zone index mapping availability.

### test_ft_snmp_ipcidr_route_table
- **Logic:** Polls and walks the IP-CIDR route table for entries.【F:spytest/tests/system/test_snmp.py†L414-L428】
- **Relevance:** Confirms SNMP reflects routing table contents.

### test_ft_snmp_ifx_table
- **Logic:** Walks IF-MIB ifXTable for extended interface stats.【F:spytest/tests/system/test_snmp.py†L430-L441】
- **Relevance:** Ensures high-capacity counters are exposed.

### test_ft_snmp_ip_System_Stats_Table
- **Logic:** Walks IP system stats table for per-protocol totals.【F:spytest/tests/system/test_snmp.py†L443-L454】
- **Relevance:** Checks IP stack telemetry presence.

### test_ft_snmp_ip_IfStats_Table
- **Logic:** Walks per-interface IP statistics table.【F:spytest/tests/system/test_snmp.py†L456-L467】
- **Relevance:** Validates per-interface IP instrumentation.

### test_ft_snmp_ip_Address_Table
- **Logic:** Walks IP address table for interface addresses.【F:spytest/tests/system/test_snmp.py†L469-L480】
- **Relevance:** Confirms IP addressing data is accessible.

### test_ft_snmp_ip_NetToPhysical_Table
- **Logic:** Walks ARP/neighbor mapping table.【F:spytest/tests/system/test_snmp.py†L482-L493】
- **Relevance:** Validates L3-to-L2 mappings.

### test_ft_snmp_icmp_Msgs
- **Logic:** Walks ICMP messages subtree.【F:spytest/tests/system/test_snmp.py†L495-L506】
- **Relevance:** Ensures ICMP stats available for troubleshooting.

### test_ft_snmp_tcp_mib
- **Logic:** Walks TCP-MIB subtree.【F:spytest/tests/system/test_snmp.py†L508-L519】
- **Relevance:** Confirms TCP counters accessible.

### test_ft_snmp_udp_mib
- **Logic:** Walks UDP-MIB subtree.【F:spytest/tests/system/test_snmp.py†L521-L532】
- **Relevance:** Validates UDP statistics reporting.

### test_ft_snmp_snmpv2_mib
- **Logic:** Walks SNMPv2-MIB subtree.【F:spytest/tests/system/test_snmp.py†L534-L545】
- **Relevance:** Confirms agent introspection metrics accessible.

### test_ft_snmp_host_resource_mib
- **Logic:** Walks HOST-RESOURCES-MIB for host inventory.【F:spytest/tests/system/test_snmp.py†L547-L558】
- **Relevance:** Validates system resource reporting.

### test_ft_snmp_framework_mib
- **Logic:** Walks SNMP-FRAMEWORK-MIB for architecture info.【F:spytest/tests/system/test_snmp.py†L560-L571】
- **Relevance:** Ensures compliance with SNMPv3 framework instrumentation.

### test_ft_snmp_mpd_mib
- **Logic:** Walks SNMP-MPD-MIB for message processing compliance data.【F:spytest/tests/system/test_snmp.py†L573-L584】
- **Relevance:** Validates message processing module instrumentation.

### test_ft_snmp_target_mib
- **Logic:** Walks SNMP-TARGET-MIB for notification target configs.【F:spytest/tests/system/test_snmp.py†L586-L598】
- **Relevance:** Confirms trap destination configuration is visible.

### test_ft_snmp_notification_mib
- **Logic:** Walks SNMP-NOTIFICATION-MIB for notification profile details.【F:spytest/tests/system/test_snmp.py†L600-L612】
- **Relevance:** Ensures notification settings accessible.

### test_ft_snmp_user_based_sm_mib
- **Logic:** Walks SNMP-USER-BASED-SM-MIB for USM entries.【F:spytest/tests/system/test_snmp.py†L614-L626】
- **Relevance:** Confirms SNMPv3 USM security data present.

### test_ft_snmp_view_based_acm_mib
- **Logic:** Walks SNMP-VACM view tables for access control configuration.【F:spytest/tests/system/test_snmp.py†L628-L640】
- **Relevance:** Validates SNMP view-based access control instrumentation.

### test_ft_snmp_ent_physical_table
- **Logic:** Walks entPhysicalTable for physical components.【F:spytest/tests/system/test_snmp.py†L642-L653】
- **Relevance:** Provides hardware inventory verification.

### test_ft_snmp_ent_phy_sensor_table
- **Logic:** Walks entPhySensorTable for sensor metadata.【F:spytest/tests/system/test_snmp.py†L655-L666】
- **Relevance:** Ensures sensor types/units reported.

### test_ft_snmp_dot3_stats_table
- **Logic:** Walks dot3StatsTable for Ethernet stats.【F:spytest/tests/system/test_snmp.py†L668-L679】
- **Relevance:** Validates Ethernet PHY telemetry.

### test_ft_net_snmp_agent_mib
- **Logic:** Walks NET-SNMP-AGENT-MIB extension.【F:spytest/tests/system/test_snmp.py†L681-L692】
- **Relevance:** Confirms Net-SNMP agent extension tables exist.

### test_ft_net_snmp_vacm_mib
- **Logic:** Walks NET-SNMP-VACM-MIB for extended VACM data.【F:spytest/tests/system/test_snmp.py†L694-L705】
- **Relevance:** Ensures vendor VACM extensions accessible.

### test_ft_snmp_ucd_diskio_mib
- **Logic:** Walks UCD-DISKIO-MIB for disk statistics.【F:spytest/tests/system/test_snmp.py†L707-L718】
- **Relevance:** Verifies legacy UCD SNMP support for disk IO.

### test_ft_snmp_ucd_memory
- **Logic:** Walks UCD-MEMORY-MIB for memory stats.【F:spytest/tests/system/test_snmp.py†L720-L731】
- **Relevance:** Confirms memory telemetry provided.

### test_ft_snmp_ucd_la_table
- **Logic:** Walks UCD-LaTable for load averages.【F:spytest/tests/system/test_snmp.py†L733-L744】
- **Relevance:** Validates CPU load telemetry.

### test_ft_snmp_ucd_system_stats
- **Logic:** Walks UCD-SystemStats for CPU details.【F:spytest/tests/system/test_snmp.py†L746-L757】
- **Relevance:** Ensures CPU metrics accessible.

### test_ft_snmp_dot1d_base_bridge_address
- **Logic:** Compares SNMP dot1d bridge MAC address with management interface MAC.【F:spytest/tests/system/test_snmp.py†L759-L773】
- **Relevance:** Validates bridge identity.

### test_ft_snmp_dot1d_base_num_ports
- **Logic:** Verifies reported bridge port count equals two active ports.【F:spytest/tests/system/test_snmp.py†L775-L785】
- **Relevance:** Confirms topology membership reflected.

### test_ft_snmp_dot1d_base_type
- **Logic:** Ensures dot1dBaseType walk returns data.【F:spytest/tests/system/test_snmp.py†L787-L797】
- **Relevance:** Checks bridging mode exposure.

### test_ft_snmp_dot1d_base_port
- **Logic:** Validates dot1dBasePort entries include physical port numbers derived from interface names.【F:spytest/tests/system/test_snmp.py†L799-L814】
- **Relevance:** Ensures port indexing is correct.

### test_ft_snmp_dot1d_base_port_ifindex
- **Logic:** Confirms dot1dBasePortIfIndex entries exist.【F:spytest/tests/system/test_snmp.py†L816-L826】
- **Relevance:** Maps bridge ports to ifIndex values for correlation.

### test_ft_snmp_dot1d_base_port_delay_exceeded_discards
- **Logic:** Walks delay exceeded discard counters.【F:spytest/tests/system/test_snmp.py†L828-L838】
- **Relevance:** Ensures congestion counters are exposed.

### test_ft_snmp_dot1d_base_port_mtu_exceeded_discards
- **Logic:** Walks MTU exceeded discard counters.【F:spytest/tests/system/test_snmp.py†L840-L850】
- **Relevance:** Verifies oversize frame counters are accessible.

### test_ft_snmp_dot1d_tp_aging_time
- **Logic:** Walks aging time parameter.【F:spytest/tests/system/test_snmp.py†L852-L862】
- **Relevance:** Confirms bridge aging timer is reported.

### test_ft_snmp_dot1q_fdb_dynamic_count
- **Logic:** Compares SNMP dynamic FDB count with MAC table size minus learned MAC entry.【F:spytest/tests/system/test_snmp.py†L864-L876】
- **Relevance:** Validates FDB statistics accuracy.

### test_ft_snmp_dot1q_tp_fdb_port
- **Logic:** Ensures FDB port mapping matches expected interface index.【F:spytest/tests/system/test_snmp.py†L878-L889】
- **Relevance:** Confirms MAC-to-port reporting.

### test_ft_snmp_dot1q_tp_fdb_status
- **Logic:** Validates FDB status entries exist.【F:spytest/tests/system/test_snmp.py†L891-L900】
- **Relevance:** Checks per-MAC status instrumentation.

### test_ft_snmp_dot1q_vlan_current_egress_ports
- **Logic:** Ensures at least one byte in reported bitmap is non-zero for VLAN egress ports.【F:spytest/tests/system/test_snmp.py†L902-L914】
- **Relevance:** Validates VLAN membership data encoding.

### test_ft_snmp_dot1q_vlan_current_untagged_ports
- **Logic:** Confirms untagged membership entries exist.【F:spytest/tests/system/test_snmp.py†L916-L925】
- **Relevance:** Ensures VLAN untagged port list accessible.

### test_ft_snmp_dot1q_vlan_static_untagged_ports
- **Logic:** Walks static untagged port table.【F:spytest/tests/system/test_snmp.py†L927-L936】
- **Relevance:** Validates configured untagged set reporting.

### test_ft_snmp_dot1q_vlan_static_row_status
- **Logic:** Verifies row status entries present.【F:spytest/tests/system/test_snmp.py†L938-L947】
- **Relevance:** Confirms row lifecycle states accessible.

### test_ft_snmp_dot1q_pvid
- **Logic:** Checks port VLAN ID walk includes created VLAN.【F:spytest/tests/system/test_snmp.py†L949-L958】
- **Relevance:** Validates port VLAN assignment visibility.

### test_ft_snmp_dot1q_vlan_static_name
- **Logic:** Ensures VLAN static name entry includes VLAN ID.【F:spytest/tests/system/test_snmp.py†L960-L969】
- **Relevance:** Provides VLAN labeling verification.

### test_ft_snmp_dot1q_vlan_static_egress_ports
- **Logic:** Confirms static egress bitmap shows active membership.【F:spytest/tests/system/test_snmp.py†L971-L982】
- **Relevance:** Ensures static VLAN membership exported.

### test_ft_snmp_dot1q_vlan_version_number
- **Logic:** Walks VLAN version number OID.【F:spytest/tests/system/test_snmp.py†L984-L993】
- **Relevance:** Validates VLAN configuration revision instrumentation.

### test_ft_snmp_dot1q_max_vlanid
- **Logic:** Confirms reported max VLAN ID equals platform constant.【F:spytest/tests/system/test_snmp.py†L995-L1004】
- **Relevance:** Ensures platform capability is exposed.

### test_ft_snmp_dot1q_max_supported_vlans
- **Logic:** Verifies reported supported VLAN count matches datastore value.【F:spytest/tests/system/test_snmp.py†L1006-L1015】
- **Relevance:** Confirms capacity reporting.

### test_ft_snmp_dot1q_num_vlans
- **Logic:** Matches VLAN count via API to SNMP-reported value.【F:spytest/tests/system/test_snmp.py†L1017-L1026】
- **Relevance:** Validates VLAN table population metrics.

### test_ft_snmp_dot1q_vlan_num_deletes
- **Logic:** Ensures VLAN delete counter accessible.【F:spytest/tests/system/test_snmp.py†L1028-L1036】
- **Relevance:** Provides change-tracking instrumentation.

### test_ft_snmp_vlan_static_table
- **Logic:** Iterates through static VLAN table OIDs, performing GET and GETNEXT to validate entries.【F:spytest/tests/system/test_snmp.py†L1038-L1058】
- **Relevance:** Ensures table navigation works for VLAN static entries.

### test_ft_snmp_dot1q_vlan_index
- **Logic:** Similar iteration for VLAN current table to verify OID traversal.【F:spytest/tests/system/test_snmp.py†L1060-L1080】
- **Relevance:** Confirms VLAN index table is accessible sequentially.

### test_ft_snmp_dot1q_tp_fdb_address
- **Logic:** Polls FDB table, then iterates OIDs validating GET/GETNEXT responses.【F:spytest/tests/system/test_snmp.py†L1082-L1104】
- **Relevance:** Ensures MAC entries are readable via SNMP.

### test_ft_snmp_dot1q_fdb_table
- **Logic:** Iterates dot1q FDB table verifying sequential access.【F:spytest/tests/system/test_snmp.py†L1106-L1126】
- **Relevance:** Confirms bridging database instrumentation completeness.

### test_ft_snmp_link_down_trap
- **Logic:** Clears trap log, flaps interface, and checks for `brcmSonicConfigChange` and `linkDown` traps.【F:spytest/tests/system/test_snmp.py†L1128-L1170】
- **Relevance:** Validates trap emission on link failure and configuration change.

### test_ft_snmp_link_up_trap
- **Logic:** Flaps interface and verifies `linkUp` trap captured.【F:spytest/tests/system/test_snmp.py†L1172-L1190】
- **Relevance:** Ensures recovery events emit traps.

### test_ft_snmp_coldstart_trap
- **Logic:** Reboots device (cold) and searches capture for `coldStart` trap.【F:spytest/tests/system/test_snmp.py†L1192-L1216】
- **Relevance:** Confirms SNMP agent notifies on cold reboot.

### test_ft_snmp_nsnotifyshutdown_trap
- **Logic:** Restarts SNMP docker and verifies `nsNotifyShutdown` trap.【F:spytest/tests/system/test_snmp.py†L1218-L1240】
- **Relevance:** Ensures agent lifecycle events generate traps.

### test_ft_snmp_warmstart_trap
- **Logic:** Saves config, warm reboots, and confirms `warmStart` trap emission.【F:spytest/tests/system/test_snmp.py†L1242-L1268】
- **Relevance:** Validates warm reboot trap compliance.

### test_ft_snmp_docker_restart
- **Logic:** Restarts SNMP service via systemd and revalidates sysName OID response.【F:spytest/tests/system/test_snmp.py†L1270-L1292】
- **Relevance:** Checks SNMP service resiliency post-restart.

### test_ft_snmp_basic_counters
- **Logic:** Clears counters, runs SNMP walk, and verifies agent counters increment for requests/responses.【F:spytest/tests/system/test_snmp.py†L1294-L1310】
- **Relevance:** Ensures SNMP statistics update correctly for normal traffic.

### test_ft_snmp_trap_counter
- **Logic:** Flaps interface to generate trap PDUs and confirms trap counter increments.【F:spytest/tests/system/test_snmp.py†L1312-L1326】
- **Relevance:** Validates counter tracking for trap emissions.

### test_ft_snmp_counter_negative_tests
- **Logic:** Sends SNMP queries with bad community and unsupported version, then checks counters for errors.【F:spytest/tests/system/test_snmp.py†L1328-L1344】
- **Relevance:** Confirms agent logs authentication/version errors.

## Helper Functions and Fixtures
- **snmp_module_hooks:** Autouse module fixture orchestrating topology reservation, variable initialization, SNMP/VLAN/traffic/trap pre-configuration, and teardown cleanup (SNMP config restore, VLAN deletion, trap disable).【F:spytest/tests/system/test_snmp.py†L21-L71】【F:spytest/tests/system/test_snmp.py†L88-L120】
- **snmp_func_hooks:** Function fixture capturing management IP before each test.【F:spytest/tests/system/test_snmp.py†L73-L80】
- **initialize_variables:** Populates shared `data` dictionary with community string, location/contact defaults, VLAN ID, MACs, and extensive OID constants used across tests.【F:spytest/tests/system/test_snmp.py†L82-L160】
- **snmp_pre_config/vlan_preconfig/snmp_traffic_config/snmp_trap_pre_config:** Prepare DUT configuration, loopback reachability, VLAN membership, traffic generator streams, and trap listener connectivity to ensure SNMP instrumentation has active data and traps can be captured.【F:spytest/tests/system/test_snmp.py†L122-L197】
- **Cleanup helpers:** Restore SNMP settings, remove VLAN/MAC config, clear trap subscriptions and logs.【F:spytest/tests/system/test_snmp.py†L199-L236】
- **Utility routines:** `snmptrapd_checking`, `device_eth0_ip_addr` assist trap verification and post-reboot reachability.【F:spytest/tests/system/test_snmp.py†L238-L262】

## Dependencies and Prerequisites
- **Fixtures:** Autouse fixtures require SpyTest testbed with SNMP access, traffic generator integration, and trap listener credentials via `utilities.utils.ensure_service_params` for `snmptrap` service.【F:spytest/tests/system/test_snmp.py†L21-L120】
- **Topology:** One SONiC DUT with two traffic generator ports capable of VLAN tagging/untagging to populate MAC/VLAN tables.【F:spytest/tests/system/test_snmp.py†L94-L111】
- **Services:** Reachable management network, SNMP agent enabled, external Linux host running snmptrapd with SSH access.【F:spytest/tests/system/test_snmp.py†L112-L150】【F:spytest/tests/system/test_snmp.py†L1128-L1170】
- **Traffic Generator:** Must support creation of streams for MAC learning and counter population via `tgapi` handles.【F:spytest/tests/system/test_snmp.py†L94-L111】

## Key Inputs and Parameters
- **SNMP Credentials:** Read-only community `test_123` and location/contact fields from `initialize_variables`. Control SNMP GET/Walk access.【F:spytest/tests/system/test_snmp.py†L86-L160】
- **OIDs:** Extensive OID map stored in `data` dictionary drives each SNMP query; altering OIDs changes verification scope.【F:spytest/tests/system/test_snmp.py†L92-L160】
- **VLAN/MAC Settings:** Dynamically chosen VLAN ID and source MAC addresses seed switching tables for dot1q/dot1d tests.【F:spytest/tests/system/test_snmp.py†L150-L159】【F:spytest/tests/system/test_snmp.py†L94-L111】
- **Trap Server Params:** IP/credentials/path from service parameters determine where traps are collected and read.【F:spytest/tests/system/test_snmp.py†L112-L150】
- **Wait Timers and Filters:** `data.wait_time`, `data.filter`, `data.filter_cli` tune SNMP polling tolerance and CLI filtering logic.【F:spytest/tests/system/test_snmp.py†L86-L111】

## External Libraries and Modules
- **pytest:** Provides fixture and marker infrastructure.【F:spytest/tests/system/test_snmp.py†L1-L3】
- **SpyTest APIs (`st`, `tgapi`, `SpyTestDict`):** Offer logging, topology control, traffic generator access, and shared data container.【F:spytest/tests/system/test_snmp.py†L5-L33】
- **SpyTest utilities:** `random_vlan_list`, `utilities.utils` supply helper functions for VLAN selection and service parameter retrieval.【F:spytest/tests/system/test_snmp.py†L6-L12】
- **SONiC API wrappers:** `apis.system.snmp`, `apis.system.basic`, `apis.system.box_services`, `apis.switching.vlan`, `apis.switching.mac`, `apis.routing.ip`, `apis.system.interface`, and `apis.system.reboot` wrap CLI/REST interactions for configuration and verification.【F:spytest/tests/system/test_snmp.py†L8-L20】
- **Connection helpers:** `apis.system.connection.execute_command` and `connect_to_device` provide SSH execution for trap server interaction.【F:spytest/tests/system/test_snmp.py†L14-L17】【F:spytest/tests/system/test_snmp.py†L112-L150】

## Unspecified Items
- **Testbed YAML References:** Not specified.
- **Exact Traffic Generator model/version:** Not specified.
- **Trap server operating system details beyond SSH availability:** Not specified.
