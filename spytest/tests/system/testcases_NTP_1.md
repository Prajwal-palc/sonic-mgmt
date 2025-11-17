# NTP Test Cases

## Test Case 2.1.1: Ensure device syncs to NTP server and displays accurate status

### Test Case ID
`test_ntp_1_verify_ntp_server_sync_and_status`

### Purpose
Ensure device syncs to NTP server and displays accurate status

### Test Setup
- Topology: Minimum 1 DUT required
- NTP server must be reachable from DUT

### Test Procedure

#### Basic NTP Configuration and Verification

1. Configure NTP server on the device
   ```
   ntp server <ip>
   ```

2. Enable NTP on the device
   ```
   ntp
   ```

3. Verify NTP associations
   ```
   show ntp associations
   ```

4. Verify NTP status
   ```
   show ntp
   ```

5. Verify system clock synchronization
   ```
   show clock
   ```

### Configuration Commands to Test (configure-view)

#### Enable/Disable NTP
```
ntp enable
no ntp enable
```

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
- `ifname`: Interface name (e.g., Ethernet0, Management0)

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

### Expected Output

#### 1. show ntp associations
Expected to display:
- Remote NTP servers configured
- Reference ID
- Stratum level
- Type (unicast/broadcast/multicast)
- Poll interval
- Reach (reachability register)
- Delay
- Offset
- Jitter
- Association status (* indicates system peer, + indicates candidate)

Example format:
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   64   64  377    0.123    0.456   0.789
```

#### 2. show ntp
Expected to display:
- NTP synchronization status
- Current system time
- NTP server status
- Synchronization state (synchronized/unsynchronized)
- Time source
- System time offset

#### 3. show clock
Expected to display:
- Current system date and time
- Timezone information
- Time source (NTP/Local)

Example:
```
Thu Jan 13 10:30:45 UTC 2025
```

### Validation Criteria

1. **NTP Server Configuration**
   - NTP server should be successfully configured
   - Configuration should persist across commands

2. **NTP Synchronization**
   - Device should successfully sync with configured NTP server
   - `show ntp associations` should display the configured server with reachability (reach > 0)
   - System peer should be indicated with `*` in associations output

3. **Status Display**
   - `show ntp` should indicate synchronization status as "synchronized"
   - Time offset should be within acceptable range
   - Stratum level should be appropriate (1-15)

4. **Clock Accuracy**
   - `show clock` should display accurate time synchronized from NTP server
   - Time should be within acceptable offset from NTP server time

5. **Command Functionality (Klish Mode)**
   - All configuration commands should execute without errors
   - Show commands should display appropriate output (once development is complete)
   - Negative commands (no ...) should properly remove configurations

### Test Variations

1. **Single NTP Server**
   - Configure single NTP server and verify synchronization

2. **Multiple NTP Servers**
   - Configure multiple NTP servers
   - Verify device selects appropriate server based on stratum/reach/offset

3. **NTP with Authentication**
   - Configure authentication keys
   - Configure trusted keys
   - Configure NTP server with authentication
   - Verify synchronization with authentication enabled

4. **NTP with Source Interface**
   - Configure source interface for NTP packets
   - Verify NTP packets originate from specified interface

5. **NTP with VRF**
   - Configure NTP in specific VRF
   - Verify NTP operates within specified VRF context

6. **NTP Enable/Disable**
   - Disable NTP and verify synchronization stops
   - Re-enable NTP and verify synchronization resumes

### Notes

- **Klish Mode**: Configuration and show commands listed under "Configuration Commands" and "Show Commands to Validate" sections are executed in klish mode via "sonic-cli"
- **Development Status**: Some klish commands are under development and may not produce output currently
- **Wait Time**: After configuring NTP server, allow sufficient time (typically 1-5 minutes) for initial synchronization
- **Reachability**: The reach value of 377 (octal) indicates 8 consecutive successful polls
- **Stratum**: Stratum 1 = primary time source (GPS, atomic clock), Stratum 2-15 = secondary sources
- **iburst Option**: Recommended for faster initial synchronization

### Cleanup

After test completion:
```
no ntp server <server-addr>
no ntp enable
no ntp authenticate
no ntp authentication-key <key-id>
no ntp trusted-key <key-id>
no ntp source-interface
no ntp vrf
```
