# NTP Test Cases - Source Interface

## Test Case 2.1.3: Verify NTP packets use configured source interface

### Test Case ID
`test_ntp_3_verify_source_interface`

### Purpose
Verify that NTP packets originate from the configured source interface IP address and that changing the source interface updates the source IP used in NTP packets

### Test Setup
- Topology: Minimum 1 DUT + 1 NTP server required
- NTP server must be reachable from DUT via configured source interface
- Packet capture capability (tcpdump/wireshark) or NTP debug logs
- Multiple interfaces with IP addresses configured on DUT

### Test Procedure

#### Step 1: Configure NTP Server and Enable NTP
```
ntp server <ip>
ntp enable
```
or
```
ntp server <ip>
ntp
```

#### Step 2: Configure NTP Source Interface
```
ntp source-interface <ifname>
```
**Examples:**
- `ntp source-interface Management 0`
- `ntp source-interface Ethernet 0`
- `ntp source-interface Loopback 0`

#### Step 3: Verify NTP Associations
```
show ntp associations
```
**Expected**: NTP server should be reachable and associations established

#### Step 4: Capture NTP Packets and Verify Source IP
Use packet capture or logs to verify the source IP address:

**Method 1: Packet Capture (tcpdump)**
```bash
tcpdump -i <interface> -n udp port 123 -v
```

**Method 2: NTP Debug Logs (if available)**
```
debug ntp packets
show logging | include NTP
```

**Expected**: NTP packets (UDP port 123) should originate from the IP address configured on the source interface

#### Step 5: Verify NTP Status and Clock
```
show ntp
show clock
```
**Expected**: NTP should be synchronized and clock accurate

### Configuration Commands to Test (configure-view)

#### Enable/Disable NTP
```
ntp enable
no ntp enable
```

#### NTP Server Configuration
```
ntp server <server-addr> [version <version-value>] [association <assoc-value>] [iburst] [key <key-value>] [prefer]
no ntp server <server-addr>
```
**Parameters:**
- `server-addr`: NTP server IP address or hostname
- `version-value`: 3 or 4
- `assoc-value`: server or pool
- `iburst`: Send burst of packets at startup
- `key-value`: 1-65535 (authentication key ID)
- `prefer`: Mark this server as preferred

#### Source Interface Configuration
```
ntp source-interface <ifname>
no ntp source-interface
```
**Parameters:**
- `ifname`: Interface name
  - Management interface: `Management 0` or `eth0`
  - Ethernet interface: `Ethernet 0`, `Ethernet 4`, etc.
  - Loopback interface: `Loopback 0`, `Loopback 1`, etc.

**Important Notes:**
- Interface must have a valid IP address configured
- Interface must be in UP state
- Interface must have reachability to NTP server
- Source interface setting affects all configured NTP servers

#### Authentication Configuration
```
ntp authenticate
no ntp authenticate
```

#### Authentication Key Configuration
```
ntp authentication-key <key-id> <auth-type> <password> [encrypted]
no ntp authentication-key <key-id>
```
**Parameters:**
- `key-id`: 1-65535
- `auth-type`: md5, sha1, sha256, sha384, sha512
- `password`: Authentication password
- `encrypted`: Optional flag for encrypted passwords

#### Trusted Key Configuration
```
ntp trusted-key <key-id>
no ntp trusted-key <key-id>
```
**Parameters:**
- `key-id`: 1-65535

#### VRF Configuration
```
ntp vrf <vrf-name>
no ntp vrf
```
**Parameters:**
- `vrf-name`: VRF name for NTP

### Show Commands to Validate (enable-view)

**Note:** The following commands are under development and should be executed inside **"sonic-cli"** using **"klish"** mode. Currently, these commands may not produce output.

```
show ntp global
show ntp server
show ntp associations
```

### Legacy Show Commands (Current)
```
show ntp associations
show ntp
show clock
```

### Packet Capture Commands

#### tcpdump for NTP Packets
```bash
# Capture NTP packets on specific interface
tcpdump -i <interface> -n udp port 123 -v

# Capture with more detail and save to file
tcpdump -i <interface> -n udp port 123 -vv -w /tmp/ntp_capture.pcap

# Read captured packets
tcpdump -r /tmp/ntp_capture.pcap -n -v
```

#### Filtering for Source IP
```bash
# Capture only outgoing NTP packets with specific source IP
tcpdump -i <interface> -n src <source-ip> and udp port 123 -v

# Example: Verify packets from Management interface IP
tcpdump -i eth0 -n src 192.168.1.100 and udp port 123 -v
```

### Expected Output

#### 1. show ntp global (klish)

Expected to display:
- NTP enable/disable status
- Source interface configuration
- VRF configuration (if any)
- Authentication status

Example format:
```
NTP: enabled
Source Interface: Management 0
VRF: default
Authentication: disabled
```

#### 2. show ntp server (klish)

Expected to display:
- Configured NTP servers
- Server options (iburst, prefer, version, etc.)

Example format:
```
Server Address      Version  Association  iburst  prefer  Key
192.168.1.1         4        server       yes     no      -
```

#### 3. show ntp associations

Expected to display:
- Remote NTP servers
- Synchronization status
- Reachability
- Poll interval

Example format:
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   32   64  377    0.123    0.456   0.789
```

**Note:** This output doesn't show source interface directly; source interface must be verified via packet capture

#### 4. show ntp

Expected to display:
- NTP synchronization status
- Configured NTP servers
- Current time source

Example:
```
synchronised to NTP server (192.168.1.1) at stratum 2
   time correct to within 12 ms
   polling server every 64 s

     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   32   64  377    0.123    0.456   0.789
```

#### 5. show clock

Expected to display:
- Current system date and time
- Timezone information

Example:
```
Thu Jan 13 10:30:45 UTC 2025
```

#### 6. Packet Capture Output (tcpdump)

Expected to show NTP packets with source IP matching the configured source interface:

```
10:30:45.123456 IP <source-interface-ip>.123 > <ntp-server-ip>.123: NTPv4, Client, length 48
10:30:45.234567 IP <ntp-server-ip>.123 > <source-interface-ip>.123: NTPv4, Server, length 48
```

**Key validation points:**
- Source IP = IP address of configured source interface
- Source port = 123 (NTP)
- Destination IP = Configured NTP server
- Destination port = 123 (NTP)
- Protocol = UDP

### Validation Criteria

1. **Source Interface Configuration**
   - Source interface should be successfully configured
   - Configuration should appear in `show ntp global` (klish)
   - Command should be accepted without errors

2. **Interface Prerequisites**
   - Source interface must exist on the device
   - Source interface must have a valid IP address
   - Source interface must be in UP/UP state
   - Source interface must have routing to NTP server

3. **NTP Packet Source Verification**
   - Packet capture shows NTP packets originating from source interface IP
   - All outgoing NTP packets use the same source IP
   - Source IP matches the IP configured on the specified interface

4. **NTP Synchronization**
   - Device should successfully sync with NTP server using source interface
   - `show ntp associations` should show reachability (reach > 0)
   - `show ntp` should indicate synchronized status

5. **Source Interface Change**
   - Changing source interface should update the source IP
   - New NTP packets should use the new source interface IP
   - Synchronization should be maintained with new source interface

6. **Source Interface Removal**
   - Removing source interface configuration (`no ntp source-interface`)
   - NTP packets should revert to default source IP selection
   - Default source IP is typically the outgoing interface IP

### Test Variations

1. **Management Interface as Source**
   ```
   ntp source-interface Management 0
   ```
   - Verify NTP packets use Management interface IP
   - Common scenario for out-of-band management

2. **Data Interface as Source (Ethernet)**
   ```
   ntp source-interface Ethernet 0
   ```
   - Verify NTP packets use Ethernet interface IP
   - Useful when NTP server is on data network

3. **Loopback Interface as Source**
   ```
   ntp source-interface Loopback 0
   ```
   - Verify NTP packets use Loopback interface IP
   - Provides stable source IP (loopback never goes down)
   - Common in production deployments

4. **Change Source Interface**
   - Configure `ntp source-interface Management 0`
   - Verify packets use Management IP
   - Change to `ntp source-interface Ethernet 0`
   - Verify packets now use Ethernet IP

5. **Source Interface with VRF**
   ```
   ntp vrf mgmt
   ntp source-interface Management 0
   ```
   - Verify source interface works within VRF context
   - Packets should use source interface in specified VRF

6. **Multiple NTP Servers with Source Interface**
   - Configure multiple NTP servers
   - Configure single source interface
   - Verify all NTP servers are contacted using same source interface IP

7. **Invalid Source Interface**
   - Configure non-existent interface
   - Verify appropriate error message
   - NTP should not function or fall back to default

8. **Source Interface Down Scenario**
   - Configure source interface
   - Verify NTP works
   - Shutdown source interface
   - Verify NTP behavior (may fail or fall back)

### Detailed Validation Steps

#### Pre-Configuration Checks

1. **Verify Interface Exists**
   ```
   show interface status
   show ip interface
   ```

2. **Verify Interface IP Address**
   ```
   show ip interface <ifname>
   ```
   Example output should show:
   ```
   Ethernet0 is up, line protocol is up
     Internet address is 192.168.1.100/24
   ```

3. **Verify Interface State**
   ```
   show interface <ifname>
   ```
   Should show: `up` and `up` (admin up, operational up)

4. **Verify Routing to NTP Server**
   ```
   ping <ntp-server-ip> -I <source-interface-ip>
   traceroute <ntp-server-ip> -s <source-interface-ip>
   ```

#### Post-Configuration Validation

1. **Verify Configuration Applied**
   ```
   show running-config | grep ntp
   show ntp global
   ```
   Should show: `ntp source-interface <ifname>`

2. **Start Packet Capture**
   ```bash
   tcpdump -i any -n udp port 123 -v > /tmp/ntp_packets.log 2>&1 &
   ```

3. **Wait for NTP Traffic**
   - Wait for 1-2 poll intervals (typically 64-128 seconds)
   - Allow NTP to send multiple packets

4. **Stop Packet Capture and Analyze**
   ```bash
   killall tcpdump
   cat /tmp/ntp_packets.log
   ```

5. **Verify Source IP in Capture**
   - Extract source IP from captured packets
   - Compare with configured source interface IP
   - All NTP client packets should match

### Packet Capture Analysis Example

**Scenario:** Source interface configured as `Management 0` with IP `10.10.10.100`

**Expected tcpdump output:**
```
11:15:23.456789 IP 10.10.10.100.123 > 192.168.1.1.123: NTPv4, Client, length 48
11:15:23.567890 IP 192.168.1.1.123 > 10.10.10.100.123: NTPv4, Server, length 48
11:16:27.123456 IP 10.10.10.100.123 > 192.168.1.1.123: NTPv4, Client, length 48
11:16:27.234567 IP 192.168.1.1.123 > 10.10.10.100.123: NTPv4, Server, length 48
```

**Validation:**
- ✅ Source IP = `10.10.10.100` (Management interface IP)
- ✅ Source Port = `123` (NTP)
- ✅ Destination IP = `192.168.1.1` (NTP server)
- ✅ Destination Port = `123` (NTP)
- ✅ Consistent across multiple packets

**If source interface is NOT configured or verification fails:**
```
11:15:23.456789 IP 172.16.0.1.123 > 192.168.1.1.123: NTPv4, Client, length 48
```
- ❌ Source IP = `172.16.0.1` (different interface, not Management)
- This indicates source interface configuration is not working

### Alternative Validation Methods

#### Method 1: NTP Debug Logs (if supported)
```
debug ntp packets
show logging | grep NTP
```
Look for log entries showing source interface or source IP

#### Method 2: show tech-support
```
show tech-support
```
May contain NTP configuration and status including source interface

#### Method 3: Configuration File Inspection
```
show running-config | grep -A 10 ntp
```
Should display:
```
ntp enable
ntp server 192.168.1.1 iburst
ntp source-interface Management 0
```

#### Method 4: Wireshark Analysis
If packet capture saved to .pcap file:
1. Open in Wireshark
2. Filter: `ntp`
3. Select NTP client packet
4. Inspect IP header → Source Address
5. Verify matches source interface IP

### Common Issues and Troubleshooting

#### Issue 1: Source Interface Not Taking Effect

**Symptoms:**
- NTP packets use different source IP
- Packet capture shows wrong source IP

**Possible Causes:**
- Source interface not configured correctly
- Interface is down
- No IP address on interface
- NTP service not restarted after configuration

**Troubleshooting:**
```
show ntp global
show interface <ifname>
show ip interface <ifname>
# Restart NTP (if needed)
systemctl restart ntp
```

#### Issue 2: NTP Not Synchronizing After Source Interface Configuration

**Symptoms:**
- `show ntp associations` shows unreachable (reach = 0)
- No packet capture traffic

**Possible Causes:**
- Source interface has no route to NTP server
- Firewall blocking NTP from source IP
- NTP server restricting source IPs

**Troubleshooting:**
```
ping <ntp-server> -I <source-interface-ip>
traceroute <ntp-server> -s <source-interface-ip>
show ip route <ntp-server>
```

#### Issue 3: Invalid Interface Name

**Symptoms:**
- Configuration command rejected
- Error message displayed

**Troubleshooting:**
```
show interface status
# Use correct interface naming
# Management 0 (not Management0)
# Ethernet 0 (not Ethernet0)
```

### Notes

- **Klish Mode**: Configuration commands are executed in klish mode via "sonic-cli"
- **Development Status**: Some klish show commands are under development and may not produce output
- **Default Behavior**: Without source interface configured, NTP uses the outgoing interface IP as source
- **Loopback Preferred**: In production, loopback interfaces are preferred as source because they never go down
- **Packet Capture Duration**: Capture for at least 2-3 poll intervals (2-5 minutes with default 64s poll)
- **VRF Interaction**: Source interface must be in the same VRF as configured NTP VRF (if VRF is used)
- **Security**: Some environments may have ACLs or firewall rules that restrict NTP source IPs
- **Port Number**: NTP always uses UDP port 123 for both source and destination

### Cleanup

After test completion:
```
no ntp source-interface
no ntp server <server-addr>
no ntp enable
```

Remove packet capture files:
```bash
rm -f /tmp/ntp_capture.pcap
rm -f /tmp/ntp_packets.log
```

### Success Criteria Summary

✅ **Test Passes If:**
- Source interface configured successfully without errors
- Packet capture shows NTP packets with source IP = source interface IP
- All NTP client packets use the configured source interface IP
- NTP synchronization maintained with source interface configured
- Changing source interface updates the source IP in packets
- Removing source interface reverts to default behavior

❌ **Test Fails If:**
- Source interface configuration rejected or errors
- Packet capture shows wrong source IP
- NTP packets use inconsistent source IPs
- NTP fails to synchronize after configuring source interface
- Source interface change doesn't update source IP
- Configuration doesn't persist across NTP restarts

### Additional Test Scenarios

#### Scenario 1: Source Interface with Authentication
```
ntp authenticate
ntp authentication-key 10 md5 MySecret123
ntp trusted-key 10
ntp server 192.168.1.1 key 10
ntp source-interface Management 0
```
Verify source interface works with authenticated NTP

#### Scenario 2: Source Interface Persistence
1. Configure source interface
2. Save configuration
3. Reboot device
4. Verify source interface still configured
5. Verify packets still use source interface IP

#### Scenario 3: Multiple Source Interface Changes
1. Configure `ntp source-interface Management 0`
2. Capture packets, verify Management IP
3. Change to `ntp source-interface Ethernet 0`
4. Capture packets, verify Ethernet IP
5. Change to `ntp source-interface Loopback 0`
6. Capture packets, verify Loopback IP

### Reference Information

**NTP Packet Structure:**
```
UDP Packet:
  Source IP: <source-interface-ip>
  Source Port: 123
  Destination IP: <ntp-server-ip>
  Destination Port: 123
  Payload: NTP packet (48+ bytes)
```

**Interface Name Formats:**
- Management: `Management 0`, `eth0`, `mgmt0`
- Ethernet: `Ethernet 0`, `Ethernet 4`, `Eth0`, `Eth1/1`
- Loopback: `Loopback 0`, `Loopback 1`, `lo0`, `lo1`
- Port Channel: `PortChannel 1`, `Po1`
- VLAN: `Vlan 100`, `Vlan100`

**NTP Port:** UDP 123 (both source and destination)

**Poll Intervals:** Typically 64 seconds (can range from 16 to 1024 seconds)
