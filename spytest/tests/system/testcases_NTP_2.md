# NTP Test Cases - Failover

## Test Case 2.1.2: Fail over between multiple NTP servers and maintain sync

### Test Case ID
`test_ntp_2_failover_multiple_servers_maintain_sync`

### Purpose
Verify NTP failover functionality when primary NTP server becomes unavailable and ensure device maintains synchronization by failing over to secondary NTP server

### Test Setup
- Topology: 1 DUT + 2 NTP servers required
- Both NTP servers must be initially reachable from DUT
- Ability to disable/block primary NTP server during test

### Test Procedure

#### Step 1: Configure Primary and Secondary NTP Servers
```
ntp server <primary>
ntp server <secondary>
```

#### Step 2: Enable NTP
```
ntp enable
```
or
```
ntp
```

#### Step 3: Verify Primary Server is Selected
```
show ntp associations
```
**Expected**: Primary server should be marked with `*` (system peer)

#### Step 4: Disable Primary NTP Server
- Block/disable connectivity to primary NTP server
- This can be achieved by:
  - Applying ACL to block primary server IP
  - Removing primary server temporarily
  - Shutting down primary NTP server (if under test control)

#### Step 5: Observe Failover to Secondary
```
show ntp associations
```
**Expected**: Secondary server should now be marked with `*` (system peer)

#### Step 6: Verify Continued Synchronization
```
show ntp
show clock
```
**Expected**: Device should remain synchronized using secondary server

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
- `iburst`: Send burst of packets at startup (recommended for faster convergence)
- `key-value`: 1-65535 (authentication key ID)
- `prefer`: Mark this server as preferred

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

#### 1. show ntp associations (Initial State - Primary Active)

Expected to display:
- Primary server marked with `*` (selected as system peer)
- Secondary server marked with `+` (candidate) or no marker (unselected)
- Both servers should show reachability (reach > 0)

Example format:
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
*192.168.1.1     .GPS.            1 u   32   64  377    0.123    0.456   0.789
+192.168.1.2     .GPS.            1 u   45   64  377    0.234    0.567   0.890
```

**Legend:**
- `*` = System peer (currently synchronized to this server)
- `+` = Candidate (acceptable for synchronization)
- `-` = Outlier (not considered for synchronization)
- `x` = False ticker (not synchronized)
- `.` = Culled from sync algorithm

#### 2. show ntp associations (After Primary Failure - Secondary Active)

Expected to display:
- Primary server showing reduced or zero reachability (reach decreasing)
- Secondary server now marked with `*` (selected as system peer)
- Failover should complete within 2-5 poll intervals

Example format:
```
     remote           refid      st t when poll reach   delay   offset  jitter
==============================================================================
 192.168.1.1     .INIT.          16 u    -   64  000    0.000    0.000   0.000
*192.168.1.2     .GPS.            1 u   15   64  377    0.234    0.567   0.890
```

**Indicators of failover:**
- Primary reach changes from 377 (octal) to 000
- Primary stratum may show 16 (unreachable)
- Primary refid may show `.INIT.` or similar
- Secondary server promoted to system peer (`*`)

#### 3. show ntp

Expected to display before failover:
- Synchronization status: synchronized
- Time source: primary server IP
- Current offset from time source

Expected to display after failover:
- Synchronization status: synchronized (maintained)
- Time source: secondary server IP (changed)
- Current offset from new time source
- May show brief unsynchronized state during transition

#### 4. show clock

Expected to display:
- Current system date and time
- Should remain accurate before and after failover
- Time should continue to advance normally

Example:
```
Thu Jan 13 10:30:45 UTC 2025
```

### Validation Criteria

1. **Initial Configuration**
   - Both primary and secondary NTP servers should be successfully configured
   - Configuration should appear in `show ntp server` output

2. **Initial Synchronization**
   - Device should sync with primary server initially
   - Primary server should be marked with `*` in `show ntp associations`
   - Reachability (reach) should be 377 for primary server

3. **Failover Detection**
   - When primary server becomes unavailable:
     - Primary server reach should decrease over time (376, 374, 370, ..., 000)
     - System should detect primary server failure within 2-5 poll intervals
     - Typical failover time: 2-10 minutes depending on poll interval

4. **Failover Completion**
   - Secondary server should be promoted to system peer (`*`)
   - Secondary server reachability should remain high (377)
   - `show ntp` should indicate synchronization with secondary server

5. **Continued Synchronization**
   - Device should maintain synchronized state after failover
   - Clock should remain accurate
   - Time offset should be within acceptable range for secondary server

6. **Reachability Values**
   - Reach value is an 8-bit octal shift register (377 octal = all 8 polls successful)
   - Each bit represents the success/failure of the last 8 poll attempts
   - 377 = 11111111 (binary) = all successful
   - 000 = 00000000 (binary) = all failed
   - Decreasing reach indicates progressive failures

### Test Variations

1. **Primary with Prefer Option**
   - Configure primary server with `prefer` option
   - Configure secondary server without `prefer`
   - Verify primary is selected initially
   - Verify failover to secondary when primary fails
   - Verify fail-back to primary when it recovers (if prefer is configured)

2. **Multiple Secondary Servers**
   - Configure one primary and multiple secondary servers
   - Disable primary
   - Verify device selects best secondary based on stratum, offset, jitter

3. **Failover with Authentication**
   - Configure NTP authentication on both servers
   - Verify failover works correctly with authentication enabled

4. **Failover in Specific VRF**
   - Configure NTP servers in non-default VRF
   - Verify failover works within VRF context

5. **Different Stratum Levels**
   - Configure primary as stratum 1
   - Configure secondary as stratum 2
   - Verify device prefers lower stratum (primary)
   - Verify failover accepts higher stratum when primary unavailable

6. **Poll Interval Impact**
   - Test with different poll intervals
   - Verify failover time correlates with poll interval
   - Shorter poll = faster failover detection

### Detailed Failover Timeline

**Typical Failover Sequence (with 64-second poll interval):**

| Time | Event | Primary Reach | Secondary Reach | System Peer |
|------|-------|---------------|-----------------|-------------|
| T+0  | Primary server blocked | 377 | 377 | Primary (*) |
| T+64s | First poll fails | 376 | 377 | Primary (*) |
| T+128s | Second poll fails | 374 | 377 | Primary (*) |
| T+192s | Third poll fails | 370 | 377 | Primary (*) |
| T+256s | Fourth poll fails | 360 | 377 | Secondary (*) |
| T+320s | Fifth poll fails | 340 | 377 | Secondary (*) |
| T+512s | Eighth poll fails | 000 | 377 | Secondary (*) |

**Note:** Failover typically occurs after 3-4 consecutive failures, not necessarily waiting for reach = 000.

### Failover Methods

Choose one of the following methods to disable the primary NTP server:

#### Method 1: Remove Primary Server Configuration
```
no ntp server <primary>
```
**Note:** This is the simplest method but doesn't test true network failure

#### Method 2: ACL to Block Primary Server
```
ip access-list <acl-name>
  deny udp any host <primary> eq ntp
  permit ip any any
interface <interface>
  ip access-group <acl-name> out
```

#### Method 3: Firewall/iptables (if accessible)
```
iptables -A OUTPUT -p udp -d <primary> --dport 123 -j DROP
```

#### Method 4: Shutdown Primary NTP Server
- If primary NTP server is under test control (e.g., another DUT or test VM)
- Stop NTP service on primary server

### Recovery Test (Optional)

After successful failover to secondary:

1. **Re-enable Primary Server**
   - Remove block/ACL
   - Or re-add primary server configuration

2. **Observe Behavior**
   - If primary configured with `prefer`: should fail-back to primary
   - If no `prefer`: may stay with secondary (stable selection)
   - Monitor with `show ntp associations`

3. **Verify Stable Operation**
   - After failback (if applicable), verify synchronization remains stable
   - Both servers should show good reachability

### Notes

- **Klish Mode**: Configuration and show commands are executed in klish mode via "sonic-cli"
- **Development Status**: Some klish commands are under development and may not produce output currently
- **Failover Time**: Typical failover time is 2-10 minutes depending on poll interval (default 64s)
- **Poll Interval**: Can be adjusted with `ntp timer` command for faster failover detection in testing
- **iburst Option**: Recommended for faster initial synchronization and potentially faster failover
- **Prefer Option**: Use `prefer` on primary server if you want automatic fail-back when primary recovers
- **Reachability**: Takes 8 polls to completely fill or empty the reach register
- **System Stability**: NTP algorithm prefers stable time sources; frequent changes are avoided

### Cleanup

After test completion:
```
no ntp server <primary>
no ntp server <secondary>
no ntp enable
```

If ACLs were used:
```
no ip access-list <acl-name>
interface <interface>
  no ip access-group <acl-name> out
```

### Troubleshooting

If failover doesn't occur:

1. **Check Poll Interval**: Failover requires multiple poll failures
   ```
   show ntp associations
   ```
   Look at `poll` column - this is the interval in seconds

2. **Check Secondary Server Health**: Ensure secondary server is reachable and synchronized
   ```
   show ntp associations
   ```
   Secondary `reach` should be 377

3. **Check Secondary Stratum**: Stratum must be < 16 (valid time source)

4. **Wait Longer**: Full failover can take 5-10 minutes with default settings

5. **Enable NTP Debug** (if available):
   ```
   debug ntp
   ```

### Success Criteria Summary

✅ **Test Passes If:**
- Primary server initially selected as system peer (*)
- After disabling primary, its reachability decreases
- Secondary server is promoted to system peer (*) after primary failure
- Device maintains synchronized state throughout failover
- Clock remains accurate after failover
- `show ntp` indicates synchronization with secondary server

❌ **Test Fails If:**
- Failover doesn't occur within expected time (10-15 minutes)
- Device loses synchronization during failover
- Secondary server not promoted to system peer
- Clock stops or becomes significantly inaccurate
- NTP service crashes or becomes unresponsive
