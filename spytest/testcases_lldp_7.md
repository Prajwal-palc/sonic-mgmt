# LLDP Test Cases

## Testcase ID: 1.1.7

### Title
Verify VLAN specific LLDP functionality (VLAN Name TLV allowlist and max count)

### Objective
To verify that LLDP VLAN Name TLV allowlist and maximum TLV count configurations work correctly. Ensure that only VLANs from the configured allowlist are advertised in LLDP packets, and the number of advertised VLAN Name TLVs does not exceed the configured maximum count.

### Test Topology
- **Devices**: smic_sonic1, smic_sonic2
- **Test Interfaces**: Ethernet4 (connected between smic_sonic1 and smic_sonic2)
- **Testbed File**: /home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml

### Test Procedure

1. **Configure and verify LLDP globally and at interface level**
   - Fetch Ethernet interface information from testbed: `/home/adminuser/Siddu/sonic-mgmt/spytest/testbeds/testbed_2vs.yaml`
   - Go to interface mode and give "no shut" to all interfaces in the testbed (Ethernet4)
   - Test LLDP enable/disable:
     - Enable LLDP in config mode: `lldp enable`
     - Disable LLDP in config mode: `no lldp enable`
     - Enable LLDP in interface mode: `lldp enable` (on Ethernet4)
     - Disable LLDP in interface mode: `no lldp enable` (on Ethernet4)
   - Re-enable LLDP for testing

2. **Enable LLDP globally and on interfaces**
   - Enable LLDP globally on both DUTs
   - Enable LLDP on test interfaces (Ethernet4) on both DUTs
   - Verify LLDP is active and neighbors are discovered

3. **Configure VLANs on the system**
   - Create multiple VLANs for testing (e.g., VLAN 10, 20, 21, 22, 23, 24, 25, 30, 40)
   - Assign meaningful names to VLANs
   - Add interfaces to VLANs as needed

4. **Configure allowed VLAN list for LLDP VLAN Name TLV**
   - Enter configuration terminal mode
   - Configure allowed VLAN list: `lldp vlan-name-tlv allowed vlan 10,20-25`
   - Verify configuration is accepted and stored
   - Test various VLAN range formats (individual VLANs, ranges, combinations)

5. **Configure maximum TLV count**
   - Configure maximum VLAN Name TLV count: `lldp vlan-name-tlv max-tlv-count 5`
   - Verify configuration is accepted and stored
   - Test various count values (e.g., 3, 5, 10)

6. **Verify VLAN Name TLVs on neighbor**
   - Capture LLDP packets or use detailed neighbor show commands
   - Parse VLAN Name TLVs from neighbor advertisements
   - Count the number of VLAN Name TLVs received
   - Verify VLAN IDs match the configured allowlist
   - Verify count does not exceed configured maximum

7. **Test with VLANs outside allowlist**
   - Configure additional VLANs not in the allowlist (e.g., VLAN 30, 40)
   - Verify these VLANs are NOT advertised in LLDP packets
   - Confirm only allowlist VLANs appear in neighbor output

8. **Test maximum count enforcement**
   - Configure allowlist with more VLANs than max-tlv-count
   - Verify only max-tlv-count number of VLANs are advertised
   - Confirm strict enforcement of the limit

### Show Commands to Validate

#### Klish Mode (sonic-cli)
**Note**: These commands are currently under development and may not produce output yet. Execute inside `sonic-cli`:
1. `show lldp neighbor` (detail if supported)
2. Packet capture analysis for LLDP frames

#### Click Mode (sudo config)
**Note**: These commands work properly and need to be executed outside sonic-cli:
1. `show lldp neighbor` (detail if supported)
2. Packet capture analysis for LLDP frames

### Expected Output

1. **VLAN Allowlist Configuration**
   - `lldp vlan-name-tlv allowed vlan 10,20-25` is successfully configured
   - Configuration accepts individual VLANs (10) and ranges (20-25)
   - Configuration persists across LLDP restarts
   - Only VLANs 10, 20, 21, 22, 23, 24, 25 are eligible for advertisement

2. **Maximum TLV Count Configuration**
   - `lldp vlan-name-tlv max-tlv-count 5` is successfully configured
   - Configuration persists across LLDP restarts
   - Maximum count limit is enforced

3. **VLAN Name TLV Advertisement**
   - Neighbor receives VLAN Name TLVs in LLDP packets
   - Only VLANs from the allowlist (10, 20-25) are advertised
   - VLANs outside the allowlist (e.g., 30, 40) are NOT advertised
   - Number of advertised VLAN Name TLVs ≤ configured max-tlv-count (5)

4. **VLAN Name TLV Format**
   - VLAN Name TLVs are properly formatted
   - Each TLV contains:
     - VLAN ID (correct value from allowlist)
     - VLAN Name (if configured)
     - Proper TLV structure and encoding
   - TLVs are readable and parseable

5. **Allowlist Filtering**
   - If allowlist contains 7 VLANs (10, 20, 21, 22, 23, 24, 25) but max-tlv-count is 5:
     - Only 5 VLAN Name TLVs are advertised
     - All 5 advertised VLANs are from the allowlist
     - No VLANs outside allowlist are included

6. **Packet Capture Validation**
   - LLDP packets can be captured on the interface
   - Captured packets contain VLAN Name TLVs
   - TLV structure matches LLDP specification
   - VLAN IDs and names are correctly encoded

7. **Command Validation**
   - Show commands execute successfully in both klish and click modes
   - Klish commands may not show output (development in progress)
   - Click commands or packet capture show accurate VLAN Name TLV information

### Pass/Fail Criteria

**Pass Criteria:**
- LLDP VLAN Name TLV allowlist configuration is successfully applied and persists
- Maximum TLV count configuration is successfully applied and persists
- Only VLANs from the configured allowlist are advertised in LLDP packets
- VLANs outside the allowlist are NOT advertised
- Number of advertised VLAN Name TLVs never exceeds the configured max-tlv-count
- When allowlist size > max-tlv-count, only max-tlv-count VLANs are advertised
- All advertised VLAN Name TLVs are properly formatted
- VLAN IDs in TLVs match the allowlist configuration
- VLAN Names (if configured) are correctly included in TLVs
- Packet capture or show commands successfully display VLAN Name TLVs
- Configuration persists across LLDP restarts and interface flaps
- All show commands execute without errors in both klish and click modes

**Fail Criteria:**
- VLAN allowlist or max-tlv-count configuration fails or does not persist
- VLANs outside the allowlist appear in LLDP advertisements
- Number of advertised VLAN Name TLVs exceeds the configured max-tlv-count
- VLAN Name TLVs are missing, malformed, or incorrectly formatted
- VLAN IDs in TLVs do not match the allowlist
- VLAN Names are missing or incorrect in TLVs
- Packet capture fails or does not show VLAN Name TLVs
- Configuration is lost after LLDP restart or interface flap
- Show commands fail or return incorrect information
- TLV structure does not conform to LLDP specification
- System crashes or exhibits unstable behavior when VLAN TLVs are configured
- Memory leaks or resource exhaustion occurs with large VLAN lists

### Additional Notes

- **VLAN Configuration Prerequisite**: VLANs must be created and configured on the system before they can be advertised via LLDP
- **Allowlist Format**: Supports individual VLANs (10), ranges (20-25), and combinations (10,20-25)
- **Max-TLV-Count**: Typical values are 3-10; test with values at boundaries
- **Priority**: When allowlist > max-tlv-count, lower VLAN IDs typically have priority
- **TLV Structure**: VLAN Name TLV is an IEEE 802.1Q organizationally specific TLV
- **Packet Capture**: Use tcpdump or similar tools to capture LLDP multicast frames (destination MAC 01:80:c2:00:00:0e)
- **Performance**: Large VLAN lists should not impact LLDP performance or increase packet size beyond MTU limits
