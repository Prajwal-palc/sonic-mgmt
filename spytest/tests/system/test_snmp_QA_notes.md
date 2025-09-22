# SNMP Test Case QA Notes

## 1. Topology type
- The module fixture acquires a `D1T1:2` topology, meaning one DUT (`D1`) connected to one traffic generator (`T1`) with two links; the presence of traffic generator handles and port members (`T1D1P1`, `T1D1P2`) confirms this inference. 【F:spytest/tests/system/test_snmp.py†L21-L193】

## 2. Overall test purpose
- The suite validates SONiC's SNMP implementation end-to-end: it checks read-only community configuration, walks numerous standard and vendor MIB trees, confirms data-plane related tables (interfaces, VLAN/FDB, IPv6, routing), verifies trap delivery for operational events, and confirms SNMP counters/service resilience. 【F:spytest/tests/system/test_snmp.py†L139-L1593】

## 3. Subtestcases and rationale

### Setup routines executed for every module/test
- `snmp_module_hooks` – ensures the correct topology is allocated, initializes test data, provisions SNMP, VLAN, traffic streams, and trap monitoring so subsequent tests can rely on pre-populated counters and trap collection. 【F:spytest/tests/system/test_snmp.py†L21-L234】
- `snmp_func_hooks` – refreshes the DUT management IP before each test to avoid stale address data. 【F:spytest/tests/system/test_snmp.py†L37-L41】
- Helper functions (`snmp_pre_config`, `vlan_preconfig`, `snmp_traffic_config`, `snmp_trap_pre_config`, and respective post configs) manage DUT SNMP configuration, VLAN membership, traffic generation, and remote trap capture cleanup so that each validation starts from a known state. 【F:spytest/tests/system/test_snmp.py†L139-L234】

### System identification and baseline SNMP GET validations
- `test_ft_snmp_sysName` – confirms SNMP returns the DUT hostname, proving basic community/agent access. 【F:spytest/tests/system/test_snmp.py†L265-L278】
- `test_ft_snmp_test_syUpTime` – cross-checks SNMP uptime with CLI uptime to ensure accuracy of operational metrics. 【F:spytest/tests/system/test_snmp.py†L285-L302】
- `test_ft_snmp_sysLocation` – verifies configured SNMP location is retrievable, validating configuration persistence. 【F:spytest/tests/system/test_snmp.py†L309-L323】
- `test_ft_snmp_sysDescr` – parses SNMP description output to match SONiC version/HWSKU, ensuring metadata fidelity. 【F:spytest/tests/system/test_snmp.py†L330-L359】
- `test_ft_snmp_sysContact` – checks sysContact retrieval to confirm user-configurable fields. 【F:spytest/tests/system/test_snmp.py†L366-L381】

### Generic MIB walk coverage
- `test_ft_snmp_mib_2` – ensures a walk of the MIB-2 tree succeeds, covering broad system data. 【F:spytest/tests/system/test_snmp.py†L387-L397】
- `test_ft_snmp_if_mib_all` – validates interface-related tables can be walked. 【F:spytest/tests/system/test_snmp.py†L404-L414】
- `test_ft_snmp_entity_mib_all` – confirms ENTITY-MIB data availability. 【F:spytest/tests/system/test_snmp.py†L421-L431】
- `test_ft_snmp_entity_sensor_mib` – checks sensor readings are accessible. 【F:spytest/tests/system/test_snmp.py†L438-L448】
- `test_ft_snmp_dot1q_dot1db_mib` – walks IEEE bridging MIBs (dot1q/dot1d) to verify layer-2 data exposure. 【F:spytest/tests/system/test_snmp.py†L455-L472】
- `test_ft_snmp_root_node_walk` – walks from the SNMP root to detect traversal issues. 【F:spytest/tests/system/test_snmp.py†L479-L491】

### IPv6 and routing table coverage
- `test_ft_snmp_ipAddressRowStatus_ipv6` – validates IPv6 address row status availability. 【F:spytest/tests/system/test_snmp.py†L497-L507】
- `test_ft_snmp_ipAddressStorageType_ipv6` – confirms IPv6 storage type entries. 【F:spytest/tests/system/test_snmp.py†L514-L524】
- `test_ft_snmp_ipv6_If_Forward_default_HopLimit` – checks forwarding/default hop limit tables for IPv6. 【F:spytest/tests/system/test_snmp.py†L531-L546】
- `test_ft_snmp_ipv6scope_index_table` – ensures scope zone index data is present. 【F:spytest/tests/system/test_snmp.py†L553-L563】
- `test_ft_snmp_ipcidr_route_table` – verifies ipCidrRouteTable entries after polling, covering routing reachability. 【F:spytest/tests/system/test_snmp.py†L569-L581】

### Interface and IP statistics tables
- `test_ft_snmp_ifx_table` – confirms extended interface table accessibility. 【F:spytest/tests/system/test_snmp.py†L585-L595】
- `test_ft_snmp_ip_System_Stats_Table` – validates system-wide IP statistics. 【F:spytest/tests/system/test_snmp.py†L599-L609】
- `test_ft_snmp_ip_IfStats_Table` – ensures per-interface IP statistics are exposed. 【F:spytest/tests/system/test_snmp.py†L613-L623】
- `test_ft_snmp_ip_Address_Table` – checks address table data. 【F:spytest/tests/system/test_snmp.py†L627-L637】
- `test_ft_snmp_ip_NetToPhysical_Table` – verifies IP-to-MAC resolution entries. 【F:spytest/tests/system/test_snmp.py†L641-L651】

### Protocol and SNMP agent MIB validation
- `test_ft_snmp_icmp_Msgs` – walks ICMP statistics. 【F:spytest/tests/system/test_snmp.py†L655-L665】
- `test_ft_snmp_tcp_mib` – validates TCP-MIB retrieval. 【F:spytest/tests/system/test_snmp.py†L669-L679】
- `test_ft_snmp_udp_mib` – checks UDP-MIB data. 【F:spytest/tests/system/test_snmp.py†L683-L693】
- `test_ft_snmp_snmpv2_mib` – confirms SNMPv2-MIB accessibility. 【F:spytest/tests/system/test_snmp.py†L697-L707】
- `test_ft_snmp_host_resource_mib` – validates HOST-RESOURCES-MIB content. 【F:spytest/tests/system/test_snmp.py†L711-L721】
- `test_ft_snmp_framework_mib` – ensures SNMP framework information is exposed. 【F:spytest/tests/system/test_snmp.py†L725-L735】
- `test_ft_snmp_mpd_mib` – checks message processing/distribution MIB data. 【F:spytest/tests/system/test_snmp.py†L739-L749】
- `test_ft_snmp_target_mib` – validates remote target configuration tables. 【F:spytest/tests/system/test_snmp.py†L753-L763】
- `test_ft_snmp_notification_mib` – ensures notification-related configuration is readable. 【F:spytest/tests/system/test_snmp.py†L767-L777】
- `test_ft_snmp_user_based_sm_mib` – verifies user-based security model data. 【F:spytest/tests/system/test_snmp.py†L781-L791】
- `test_ft_snmp_view_based_acm_mib` – confirms VACM view information. 【F:spytest/tests/system/test_snmp.py†L795-L805】
- `test_ft_snmp_ent_physical_table` – checks physical entity inventory data. 【F:spytest/tests/system/test_snmp.py†L809-L819】
- `test_ft_snmp_ent_phy_sensor_table` – validates physical sensor table access. 【F:spytest/tests/system/test_snmp.py†L823-L833】
- `test_ft_snmp_dot3_stats_table` – ensures Ethernet interface statistics retrieval. 【F:spytest/tests/system/test_snmp.py†L837-L847】
- `test_ft_net_snmp_agent_mib` – checks NET-SNMP agent extension MIB data. 【F:spytest/tests/system/test_snmp.py†L851-L861】
- `test_ft_net_snmp_vacm_mib` – validates NET-SNMP VACM extensions. 【F:spytest/tests/system/test_snmp.py†L865-L875】
- `test_ft_snmp_ucd_diskio_mib` – ensures disk I/O statistics availability. 【F:spytest/tests/system/test_snmp.py†L879-L889】
- `test_ft_snmp_ucd_memory` – checks memory utilization tables. 【F:spytest/tests/system/test_snmp.py†L893-L903】
- `test_ft_snmp_ucd_la_table` – validates load average metrics. 【F:spytest/tests/system/test_snmp.py†L907-L917】
- `test_ft_snmp_ucd_system_stats` – confirms CPU-related statistics. 【F:spytest/tests/system/test_snmp.py†L921-L931】

### IEEE 802.1D bridge MIB coverage
- `test_ft_snmp_dot1d_base_bridge_address` – matches bridge MAC address between SNMP and interface output. 【F:spytest/tests/system/test_snmp.py†L935-L946】
- `test_ft_snmp_dot1d_base_num_ports` – ensures bridge reports expected port count. 【F:spytest/tests/system/test_snmp.py†L950-L960】
- `test_ft_snmp_dot1d_base_type` – confirms bridge type retrieval. 【F:spytest/tests/system/test_snmp.py†L964-L974】
- `test_ft_snmp_dot1d_base_port` – validates bridge port indexing aligns with physical ports. 【F:spytest/tests/system/test_snmp.py†L978-L990】
- `test_ft_snmp_dot1d_base_port_ifindex` – checks bridge-port to ifIndex mapping. 【F:spytest/tests/system/test_snmp.py†L994-L1004】
- `test_ft_snmp_dot1d_base_port_delay_exceeded_discards` – ensures discard counters are readable. 【F:spytest/tests/system/test_snmp.py†L1008-L1018】
- `test_ft_snmp_dot1d_base_port_mtu_exceeded_discards` – validates MTU discard counters. 【F:spytest/tests/system/test_snmp.py†L1022-L1032】
- `test_ft_snmp_dot1d_tp_aging_time` – confirms bridge aging timer reporting. 【F:spytest/tests/system/test_snmp.py†L1036-L1046】

### IEEE 802.1Q VLAN/FDB table validation
- `test_ft_snmp_dot1q_fdb_dynamic_count` – compares dynamic FDB count between SNMP and MAC table. 【F:spytest/tests/system/test_snmp.py†L1050-L1061】
- `test_ft_snmp_dot1q_tp_fdb_port` – maps FDB entries to expected port numbers. 【F:spytest/tests/system/test_snmp.py†L1065-L1076】
- `test_ft_snmp_dot1q_tp_fdb_status` – ensures FDB status entries exist. 【F:spytest/tests/system/test_snmp.py†L1080-L1090】
- `test_ft_snmp_dot1q_vlan_current_egress_ports` – checks egress bitmap contains active ports. 【F:spytest/tests/system/test_snmp.py†L1094-L1109】
- `test_ft_snmp_dot1q_vlan_current_untagged_ports` – validates untagged port membership. 【F:spytest/tests/system/test_snmp.py†L1113-L1123】
- `test_ft_snmp_dot1q_vlan_static_untagged_ports` – ensures static untagged bitmap exists. 【F:spytest/tests/system/test_snmp.py†L1127-L1137】
- `test_ft_snmp_dot1q_vlan_static_row_status` – confirms static row status entries. 【F:spytest/tests/system/test_snmp.py†L1141-L1151】
- `test_ft_snmp_dot1q_pvid` – checks default VLAN ID binding via SNMP filter. 【F:spytest/tests/system/test_snmp.py†L1155-L1165】
- `test_ft_snmp_dot1q_vlan_static_name` – matches VLAN names across systems. 【F:spytest/tests/system/test_snmp.py†L1169-L1178】
- `test_ft_snmp_dot1q_vlan_static_egress_ports` – validates static egress bitmaps show membership. 【F:spytest/tests/system/test_snmp.py†L1183-L1197】
- `test_ft_snmp_dot1q_vlan_version_number` – confirms VLAN version number is retrievable. 【F:spytest/tests/system/test_snmp.py†L1201-L1210】
- `test_ft_snmp_dot1q_max_vlanid` – checks max VLAN ID matches platform constants. 【F:spytest/tests/system/test_snmp.py†L1214-L1223】
- `test_ft_snmp_dot1q_max_supported_vlans` – verifies supported VLAN count against constants. 【F:spytest/tests/system/test_snmp.py†L1227-L1236】
- `test_ft_snmp_dot1q_num_vlans` – compares VLAN count with CLI data. 【F:spytest/tests/system/test_snmp.py†L1240-L1250】
- `test_ft_snmp_dot1q_vlan_num_deletes` – ensures delete counter is readable. 【F:spytest/tests/system/test_snmp.py†L1254-L1263】
- `test_ft_snmp_vlan_static_table` – iterates through static VLAN table entries verifying GET/GETNEXT responses. 【F:spytest/tests/system/test_snmp.py†L1267-L1285】
- `test_ft_snmp_dot1q_vlan_index` – performs similar validation for current VLAN table entries. 【F:spytest/tests/system/test_snmp.py†L1289-L1307】
- `test_ft_snmp_dot1q_tp_fdb_address` – polls and validates FDB address table entries. 【F:spytest/tests/system/test_snmp.py†L1311-L1331】
- `test_ft_snmp_dot1q_fdb_table` – verifies dot1q FDB table GET/GETNEXT responses. 【F:spytest/tests/system/test_snmp.py†L1335-L1353】

### Trap generation and monitoring
- `test_ft_snmp_link_down_trap` – induces interface flap and expects linkDown plus vendor config-change traps. 【F:spytest/tests/system/test_snmp.py†L1356-L1395】
- `test_ft_snmp_link_up_trap` – verifies linkUp trap emission on interface recovery. 【F:spytest/tests/system/test_snmp.py†L1398-L1421】
- `test_ft_snmp_coldstart_trap` – reboots the DUT to confirm coldStart trap capture. 【F:spytest/tests/system/test_snmp.py†L1424-L1453】
- `test_ft_snmp_nsnotifyshutdown_trap` – restarts the SNMP container to check for nsNotifyShutdown trap. 【F:spytest/tests/system/test_snmp.py†L1456-L1477】
- `test_ft_snmp_warmstart_trap` – performs warm reboot and expects warmStart trap. 【F:spytest/tests/system/test_snmp.py†L1480-L1510】

### Service resiliency and counters
- `test_ft_snmp_docker_restart` – restarts SNMP service and re-validates sysName to ensure agent recovery. 【F:spytest/tests/system/test_snmp.py†L1513-L1531】
- `test_ft_snmp_basic_counters` – clears counters, stimulates SNMP GETs, and checks standard counter increments. 【F:spytest/tests/system/test_snmp.py†L1535-L1552】
- `test_ft_snmp_trap_counter` – generates trap events and verifies trap PDU counters. 【F:spytest/tests/system/test_snmp.py†L1556-L1571】
- `test_ft_snmp_counter_negative_tests` – executes invalid community/version operations to confirm error counters increment. 【F:spytest/tests/system/test_snmp.py†L1575-L1593】

## 4. Dependencies and prerequisites
- Requires SpyTest framework fixtures and API modules (`st`, `tgapi`, `SpyTestDict`) as well as numerous SONiC API wrappers for SNMP, system, VLAN, MAC, IP, interface, connection, and reboot operations. 【F:spytest/tests/system/test_snmp.py†L4-L17】
- Depends on module-level setup to configure SNMP communities, loopback interface, VLAN members, traffic streams, and trap receivers before tests run. 【F:spytest/tests/system/test_snmp.py†L21-L234】
- Assumes availability of a traffic generator connected on two ports and a reachable SNMP trap server (credentials/IP/path retrieved via `ensure_service_params`). 【F:spytest/tests/system/test_snmp.py†L172-L212】
- Individual tests expect SNMP agent reachability over management network and may require device constants from the SpyTest datastore for VLAN limits. 【F:spytest/tests/system/test_snmp.py†L139-L223】【F:spytest/tests/system/test_snmp.py†L1214-L1236】

## 5. Key inputs and their sources
- SNMP credentials, locations, OIDs, VLAN ID, MAC addresses, trap identifiers, and polling parameters are initialized in `initialize_variables`, giving deterministic input values for most verifications. 【F:spytest/tests/system/test_snmp.py†L44-L137】
- DUT management IP is obtained dynamically per test via `st.get_mgmt_ip`, ensuring alignment with the deployed testbed. 【F:spytest/tests/system/test_snmp.py†L37-L41】【F:spytest/tests/system/test_snmp.py†L251-L258】
- Trap server connection parameters (IP, username, password, capture file path) come from SpyTest service parameters, typically sourced from inventory/group variable files. 【F:spytest/tests/system/test_snmp.py†L196-L212】
- VLAN membership relies on topology handles (`vars.D1T1P1`, `vars.D1T1P2`) derived from the minimum topology reservation. 【F:spytest/tests/system/test_snmp.py†L21-L193】
- Platform constants such as maximum VLAN values are fetched from the SpyTest datastore. 【F:spytest/tests/system/test_snmp.py†L1214-L1236】

## 6. External libraries and their roles
- `pytest` provides fixtures and markers for organizing the suite. 【F:spytest/tests/system/test_snmp.py†L1-L37】
- `re` and `utilities.utils` support parsing and time conversions for uptime verification. 【F:spytest/tests/system/test_snmp.py†L2-L3】【F:spytest/tests/system/test_snmp.py†L285-L301】
- SpyTest core modules (`st`, `tgapi`, `SpyTestDict`) deliver logging, topology context, traffic generator control, and shared state storage. 【F:spytest/tests/system/test_snmp.py†L4-L29】
- SONiC API wrappers (`apis.system.snmp`, `apis.system.basic`, `apis.system.box_services`, `apis.switching.vlan`, `apis.switching.mac`, `apis.routing.ip`, `apis.system.interface`, `apis.system.connection`, `apis.system.reboot`) encapsulate CLI/REST interactions for configuring SNMP, system services, L2/L3 features, interface control, remote command execution, and reboots. 【F:spytest/tests/system/test_snmp.py†L7-L17】
- Traffic generator interactions rely on `tgapi` methods to configure and drive traffic streams supporting MAC/VLAN table population. 【F:spytest/tests/system/test_snmp.py†L172-L193】
