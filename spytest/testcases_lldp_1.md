# Test Case LLDP-CLI-001: Configure and Verify LLDP CLI on DUT

- Test Case ID: LLDP-CLI-001
- Feature Area: LLDP
- Testbed Reference: `testbeds/testbed_2vs.yaml`
- Topology Dependencies: `smic_sonic1` connected to `smic_sonic2` via `Ethernet4` <-> `Ethernet4`
- Purpose: Validate LLDP global and interface configuration, TLV settings, timers, and operational statistics on the DUT.

## Preconditions
- Console/SSH access to the DUT (`smic_sonic1`).
- Ability to enter configuration and interface configuration modes.
- LLDP neighbors available on peer device (`smic_sonic2`).
- LLDP service enabled in management framework if required.

## Test Procedure
| Step | Action | CLI Example | Expected Result |
| --- | --- | --- | --- |
| 1 | Capture baseline LLDP operational state. | `show lldp table`<br>`show lldp neighbor`<br>`show lldp neighbor Ethernet4`<br>`show lldp statistics`<br>`show lldp statistics Ethernet4` | Existing entries (if any) recorded for comparison. Statistics counters noted. |
| 2 | Enable LLDP globally, then disable, then re-enable to confirm toggling. | `config`
`lldp enable`
`exit`
`config`
`no lldp enable`
`exit`
`config`
`lldp enable`
`exit` | Global LLDP state toggles as commanded. Running config reflects current state. Neighbor entries reappear once LLDP is enabled. |
| 3 | Enable/disable LLDP on interface `Ethernet4`. | `config`
`interface Ethernet4`
`lldp enable`
`no lldp enable`
`lldp enable`
`exit` | Interface-level LLDP state toggles without affecting other interfaces. Running config tracks `lldp enable` under the interface. |
| 4 | Configure LLDP reception and transmission on `Ethernet4`; toggle to validate. | `config`
`interface Ethernet4`
`lldp receive`
`lldp transmit`
`no lldp receive`
`no lldp transmit`
`lldp receive`
`lldp transmit`
`exit` | Interface updates accept commands; LLDP frames negotiated appropriately. Config displays receive/transmit state accurately. |
| 5 | Configure LLDP timer; restore default. | `config`
`lldp timer 10`
`no lldp timer`
`exit` | LLDP timer shows new value (10 seconds) and returns to default after removal. |
| 6 | Configure LLDP TLVs globally. | `config`
`lldp system-name "SupermicroSonic"`
`lldp system-description "Supermicro Sonic"`
`lldp tlv-select system-capabilities`
`lldp tlv-select management-address`
`exit` | System name/description and TLV selections applied globally. Running config lists TLVs as set. |
| 7 | Configure management address TLV. | `config`
`lldp tlv-set management-address ipv4 10.1.1.1`
`exit` | Management address TLV reflects configured IPv4 address in LLDP neighbor data. |
| 8 | Enable 802.1/802.3 TLVs. | `config`
`lldp tlv-select link-aggregation`
`lldp tlv-select max-frame-size`
`lldp tlv-select port-vlan-id`
`lldp tlv-select power-management`
`lldp tlv-select vlan-name`
`exit` | TLVs appear under running config and in LLDP neighbor information. |
| 9 | Validate show commands in user exec and sudo contexts. | `show lldp neighbor`
`show lldp table`
`sudo vtysh -c "show lldp neighbor"`
`sudo vtysh -c "show lldp table"` | Command outputs identical in both contexts; TLVs and statistics present. |
| 10 | Verify LLDP statistics and neighbor details post-configuration. | `show lldp table`
`show lldp neighbor`
`show lldp neighbor Ethernet4`
`show lldp statistics`
`show lldp statistics Ethernet4` | Neighbors visible (brief & detailed). TLVs (SysName, SysDescr, Mgmt-Addr, capabilities, VLAN, management address) displayed. Statistics counters increment appropriately. |

## Validation Points
- LLDP global and interface enable/disable states match expected configuration.
- System name, system description, and management address TLVs propagate to neighbor output.
- 802.1/802.3 TLVs (link aggregation, max frame size, port VLAN ID, power management, VLAN name) appear in neighbor detail.
- `show lldp statistics` reflects transmit/receive activity on `Ethernet4`.
- `show running-configuration` (or equivalent) records all LLDP CLI commands; removal commands clear entries.

## Post-Test Cleanup
- Revert LLDP settings to production defaults if different from baseline (e.g., remove custom TLVs, timers).
- Confirm LLDP operational state matches original configuration using the show commands listed above.
